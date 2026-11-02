package chapters

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/Thabhelo/fable/interpreter/internal/books"
)

// Plan is what the planning stage decides for one chapter.
type Plan struct {
	Title       string  `json:"title"`
	Place       string  `json:"place"`
	Environment string  `json:"environment"` // a catalogue id, or "none"
	Fit         string  `json:"fit"`         // same | adapted | none
	Why         string  `json:"why"`
	Moment      Range   `json:"moment"`
	Mood        string  `json:"mood"`
	Fog         float64 `json:"fog"`
}

type Range struct {
	From string `json:"from"`
	To   string `json:"to"`
}

// Earlier is what an earlier chapter's experience settled, given to the planner for continuity. It was derived from
// earlier text only, so it can never carry something from later in the book.
type Earlier struct {
	Chapter     string `json:"chapter"`
	Title       string `json:"title"`
	Place       string `json:"place"`
	Environment string `json:"environment"`
	Mood        string `json:"mood"`
}

const planSystem = `You prepare one "chapter experience" for Fable, a VR reader on Meta Quest. After a reader finishes a
chapter they may step into a place from it: a convincing location they can stand in and look around, with modest
staging. It is not a full animated reenactment.

You are given the book only up to the end of this chapter. Never use knowledge of later chapters, of the rest of the
book, of adaptations or of summaries: if something has not happened by the end of this chapter, it does not exist yet.

Choose:
- the chapter's single most significant place or moment that a reader would want to stand inside;
- the environment, from the list given, that can honestly stand for that place. Reuse an environment when the
  chapter is set where it is set (adapting mood and haze). If none of them is that place, or a close kin of it, answer
  "none": a reader must never be put somewhere unrelated to the chapter;
- a contiguous stretch of this chapter's sentences (by id) where that moment happens, 3 to 40 sentences;
- a mood (time of day / weather) the chapter's text supports at that moment, and a haze from 0 to 1 (0 unless the text
  gives a reason: storm, mist, smoke, dusk).

Return one JSON object and nothing else (no prose, no code fences), with exactly these keys:
{"title":"<2 to 6 words, grounded in this chapter, no names or events from later>",
 "place":"<one sentence: where the reader stands and what is around them>",
 "environment":"<an id from the list, or none>",
 "fit":"same|adapted|none",
 "why":"<one sentence: why this place and environment>",
 "moment":{"from":"<sentence id>","to":"<sentence id>"},
 "mood":"<one of the moods>",
 "fog":0.0}`

// chapterIndex finds a chapter by id; only real chapters (not front matter) have experiences.
func chapterIndex(b *books.Book, id string) (int, error) {
	for i, c := range b.Chapters {
		if c.ID == id {
			if c.Kind != "chapter" {
				return -1, fmt.Errorf("%s is %s, not a chapter", id, c.Kind)
			}
			return i, nil
		}
	}
	return -1, fmt.Errorf("no chapter %s in %s", id, b.Slug)
}

func chapterSentences(c books.Chapter) []string {
	var ids []string
	for _, p := range c.Paragraphs {
		for _, s := range p.Sentences {
			ids = append(ids, s.ID)
		}
	}
	return ids
}

// PlanPrompt builds the planner's message: the catalogue, earlier chapters' experiences, some text before the
// chapter for context, and the chapter itself with sentence ids. Nothing after the chapter's last sentence.
func PlanPrompt(b *books.Book, ci int, envs []Env, moods []string, earlier []Earlier, fixedEnv string) string {
	ch := b.Chapters[ci]
	var sb strings.Builder
	fmt.Fprintf(&sb, "BOOK: %s by %s\n", b.Title, b.Author)
	if b.Translator != "" {
		fmt.Fprintf(&sb, "(translated by %s)\n", b.Translator)
	}
	sb.WriteString("\nENVIRONMENTS:\n")
	for _, e := range envs {
		fmt.Fprintf(&sb, "- %s: %s\n", e.ID, e.Place)
	}
	if fixedEnv != "" {
		fmt.Fprintf(&sb, "This chapter's experience is staged in %q (its passage is already cut and scripted for that room); choose it, with fit \"same\" or \"adapted\".\n", fixedEnv)
	}
	fmt.Fprintf(&sb, "\nMOODS: %s\n", strings.Join(moods, ", "))
	if len(earlier) > 0 {
		ej, _ := json.Marshal(earlier)
		fmt.Fprintf(&sb, "\nEARLIER CHAPTERS' EXPERIENCES (keep continuity with these):\n%s\n", ej)
	}
	if ci > 0 {
		// the end of the previous chapter, for context only
		prev := b.Chapters[ci-1]
		if ids := chapterSentences(prev); len(ids) > 0 {
			if t, err := b.TextUpTo(ids[len(ids)-1], 3000); err == nil {
				fmt.Fprintf(&sb, "\nBEFORE THIS CHAPTER (context, already read):\n%s\n", t)
			}
		}
	}
	fmt.Fprintf(&sb, "\nTHIS CHAPTER: %s\n", ch.Title)
	for _, p := range ch.Paragraphs {
		for _, s := range p.Sentences {
			fmt.Fprintf(&sb, "[%s] %s\n", s.ID, s.Text)
		}
	}
	sb.WriteString("\nThe text above ends at the end of this chapter. Return the JSON object.")
	return sb.String()
}

// ParsePlan decodes and checks a plan against the chapter and catalogue. Problems are phrased for a repair round.
func ParsePlan(raw string, b *books.Book, ci int, cat *Catalog, allowed []Env, fixedEnv string) (*Plan, []string) {
	var p Plan
	dec := json.NewDecoder(strings.NewReader(raw))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&p); err != nil {
		return nil, []string{"not a single JSON object with exactly the given keys: " + err.Error()}
	}
	var probs []string
	if n := len(strings.Fields(p.Title)); n < 1 || n > 8 || len(p.Title) > 60 {
		probs = append(probs, "title must be 2 to 6 words (at most 60 characters)")
	}
	if strings.TrimSpace(p.Place) == "" || strings.TrimSpace(p.Why) == "" {
		probs = append(probs, "place and why must be given")
	}
	envOK := p.Environment == "none"
	for _, e := range allowed {
		if e.ID == p.Environment {
			envOK = true
		}
	}
	if !envOK {
		probs = append(probs, fmt.Sprintf("environment %q is not in the list (or none)", p.Environment))
	}
	if fixedEnv != "" && p.Environment != fixedEnv {
		probs = append(probs, fmt.Sprintf("environment must be %q for this chapter", fixedEnv))
	}
	if (p.Environment == "none") != (p.Fit == "none") || (p.Fit != "same" && p.Fit != "adapted" && p.Fit != "none") {
		probs = append(probs, `fit must be "same" or "adapted" for an environment, and "none" exactly when environment is none`)
	}
	if !cat.MoodOK(p.Mood) {
		probs = append(probs, fmt.Sprintf("mood %q is not one of %v", p.Mood, cat.Moods))
	}
	if p.Fog < 0 || p.Fog > 1 {
		probs = append(probs, "fog must be between 0 and 1")
	}
	ids := chapterSentences(b.Chapters[ci])
	pos := map[string]int{}
	for i, id := range ids {
		pos[id] = i
	}
	f, okF := pos[p.Moment.From]
	t, okT := pos[p.Moment.To]
	switch {
	case !okF || !okT:
		probs = append(probs, "moment.from and moment.to must be sentence ids from THIS chapter")
	case t < f:
		probs = append(probs, "moment.to must not come before moment.from")
	case t-f+1 > 60:
		probs = append(probs, "moment must be at most 40 sentences")
	}
	if len(probs) > 0 {
		return nil, probs
	}
	return &p, nil
}
