package rooms

// The review: Claude looks at a built room the way the reader will see it and improves it.
//
// A generated room passes roomgen's checks when it is sound (lit, in budget, nothing in the reader's face), not when
// it is good. Hand-built rooms get good by being looked at and fixed, round after round. This is a short version of
// that loop: Claude is shown the five views from the reader's eyes, rendered exactly as the headset draws them
// (preview_room.py: unlit, baked textures only), says what most hurts the place's believability, and either
// approves it or writes a revised script. A revision replaces the room only if it builds and passes the same checks,
// so a review can make a room better but never lose it.

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/Thabhelo/fable/interpreter/internal/llm"
)

// The views preview_room.py renders, in the order Claude sees them, with what each shows.
var reviewViews = []struct{ File, Label string }{
	{"reading.png", "View 1, from the reader's eyes toward where they read (the page floats about 0.6 m ahead, lower middle of this view):"},
	{"left.png", "View 2, the reader turns 90 degrees to their left:"},
	{"right.png", "View 3, the reader turns 90 degrees to their right:"},
	{"behind.png", "View 4, the reader turns round:"},
	{"down.png", "View 5, the reader looks down at their feet and the near ground or floor:"},
}

const reviewSystem = `You are the art director for Fable's generated reading rooms. You are shown a room exactly as the VR headset will draw it (all light baked into the textures, rendered from the reader's eyes, 90 degree field of view) together with the script that built it. Judge it against the place it is meant to be and the standards below, then improve it.

Judge like someone standing there for twenty minutes: does it read as that real place, at that time and weather? Look hardest for what breaks believability: wrong scale, floating or intersecting objects, faceted or blobby shapes where real ones would be irregular and layered, large plain areas (bare walls, empty floors, featureless ground), everything evenly spaced, missing the things that make this place itself, things blocking or cluttering the reading direction, lighting that is flat, too dark or blown out, colours that are oversaturated or wrong for the weather. Do not ask for things the kit cannot do (moving water, people, animals, transparent glass).

Answer in this form:
CRITIQUE:
- the most damaging problem first, each one line, at most six, each naming what you see in which view
VERDICT: GOOD   (only if nothing above is worth a rebuild)
or
VERDICT: REVISE
followed by the complete revised script in one python block. Fix the top problems; keep what works; keep the reader's position and the reading direction unless they are the problem; stay within the budgets. The script must be complete, not a diff.

` + "THE KIT AND THE RULES THE SCRIPT FOLLOWS:\n\n"

var verdictRe = regexp.MustCompile(`VERDICT:\s*(GOOD|REVISE)`)

// improve runs up to s.Review rounds of review on a room that has passed its checks and returns the best build.
func (s *Service) improve(ctx context.Context, j *Job, b *Book, st Setting, work, script, out string, res BuildResult) (string, string, BuildResult) {
	ia, ok := s.Planner.(ImageAsker)
	if !ok || s.Review <= 0 {
		return script, out, res
	}
	var notes []string
	for round := 1; round <= s.Review; round++ {
		t := time.Now()
		s.set(j, Reviewing)
		critique, revised, err := s.review(ctx, ia, b, st, script, out, filepath.Join(work, fmt.Sprintf("review-%d.txt", round)))
		j.Timings[Reviewing] += time.Since(t).Seconds()
		notes = append(notes, fmt.Sprintf("round %d:\n%s", round, critique))
		if err != nil {
			log.Printf("rooms %s: review %d: %v; keeping the room as it is", j.Key(), round, err)
			break
		}
		if revised == "" {
			log.Printf("rooms %s: review %d: approved", j.Key(), round)
			break
		}
		sp := filepath.Join(work, fmt.Sprintf("room-review-%d.py", round))
		os.WriteFile(sp, []byte(revised), 0o644)
		t = time.Now()
		s.set(j, Building)
		nout := filepath.Join(work, fmt.Sprintf("build-review-%d", round))
		nres, err := s.Build(ctx, s.Root, sp, nout)
		j.Timings[Building] += time.Since(t).Seconds()
		if why := buildProblem(nres, err); why != "" {
			// one repair, as for a first build: the revision is usually close (over budget, an object in the way)
			log.Printf("rooms %s: review %d's revision failed its checks (%s); repairing it", j.Key(), round, why)
			t = time.Now()
			s.set(j, Scripting)
			fixed, ferr := s.writeScript(ctx, b, st, revised, why, filepath.Join(work, fmt.Sprintf("answer-review-%d-repair.txt", round)))
			j.Timings[Scripting] += time.Since(t).Seconds()
			if ferr == nil {
				sp = filepath.Join(work, fmt.Sprintf("room-review-%d-repair.py", round))
				os.WriteFile(sp, []byte(fixed), 0o644)
				t = time.Now()
				s.set(j, Building)
				nout = filepath.Join(work, fmt.Sprintf("build-review-%d-repair", round))
				nres, err = s.Build(ctx, s.Root, sp, nout)
				j.Timings[Building] += time.Since(t).Seconds()
				why = buildProblem(nres, err)
				revised = fixed
			} else {
				why = ferr.Error()
			}
			if why != "" {
				log.Printf("rooms %s: review %d's repaired revision failed too (%s); keeping the previous room", j.Key(), round, why)
				notes = append(notes, "  (this revision failed its checks and was not used: "+why+")")
				break
			}
		}
		os.WriteFile(filepath.Join(nout, "script.py"), []byte(revised), 0o644)
		log.Printf("rooms %s: review %d: revised (%d -> %d triangles)", j.Key(), round, res.Triangles, nres.Triangles)
		script, out, res = revised, nout, nres
	}
	os.WriteFile(filepath.Join(out, "review.txt"), []byte(strings.Join(notes, "\n\n")), 0o644)
	return script, out, res
}

// review shows Claude the built room and returns its critique and a revised script ("" when it approves).
func (s *Service) review(ctx context.Context, ia ImageAsker, b *Book, st Setting, script, out, keep string) (string, string, error) {
	var images []llm.Image
	for _, v := range reviewViews {
		data, err := os.ReadFile(filepath.Join(out, "preview", v.File))
		if err != nil {
			return "", "", fmt.Errorf("no preview to review: %w", err)
		}
		images = append(images, llm.Image{Label: v.Label, MediaType: "image/png", Data: data})
	}
	sys, err := s.scriptSystem()
	if err != nil {
		return "", "", err
	}
	spec, _ := json.MarshalIndent(st, "", "  ")
	user := fmt.Sprintf("BOOK: %s by %s\n\nTHE PLACE:\n%s\n\nTHE SCRIPT THAT BUILT IT:\n```python\n%s\n```\n\nReview the room and answer in the form given.", b.Title, b.Author, spec, script)
	ans, stop, err := ia.AskImagesRaw(ctx, reviewSystem+sys, user, images, 32000)
	if err != nil {
		return "", "", err
	}
	os.WriteFile(keep, []byte(fmt.Sprintf("stop_reason: %s\n\n%s", stop, ans)), 0o644)
	critique := ans
	if i := strings.Index(ans, "VERDICT:"); i >= 0 {
		critique = strings.TrimSpace(ans[:i])
	}
	m := verdictRe.FindStringSubmatch(ans)
	if m == nil {
		return critique, "", fmt.Errorf("the review gave no verdict")
	}
	if m[1] == "GOOD" {
		return critique, "", nil
	}
	if stop == "max_tokens" {
		return critique, "", errCutOff
	}
	revised := ExtractCode(ans[strings.Index(ans, m[0]):])
	if strings.TrimSpace(revised) == "" || !strings.Contains(revised, "kit.") {
		return critique, "", fmt.Errorf("the review asked for a revision but gave no script")
	}
	return critique, revised, nil
}

func buildProblem(res BuildResult, err error) string {
	if err != nil {
		return err.Error()
	}
	if !res.OK {
		return strings.Join(res.Problems, "; ")
	}
	return ""
}
