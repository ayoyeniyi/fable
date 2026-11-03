// Package rooms makes three reading rooms for each book the reader uploads (docs/GENERATED_ROOMS.md).
//
// The headset sends the book's text once (POST /rooms/prepare). One planning call chooses three distinct places
// from the book's opening, the only text it is shown, so a room never spoils what comes later. For each place
// Claude writes a short room script against blender/roomkit.py; blender/roomgen.py checks the script, runs it in a
// restricted scope, checks the result (budget, reader position, brightness), bakes the light into textures and
// exports an unlit glTF. Problems go back to Claude for a corrected script, up to three attempts. The package (glTF,
// textures, a thumbnail and package.json with SHA-256 for every file) is fetched by the headset, which loads it at
// runtime. Jobs persist in out/rooms/jobs.json and resume after a restart.
package rooms

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	Queued    = "queued"
	Planning  = "planning"
	Scripting = "scripting"
	Building  = "building"
	Packaging = "packaging"
	Done      = "done"
	Failed    = "failed"
	Unavail   = "unavailable" // the book's opening offers fewer than three distinct places

	RoomsPerBook = 3
)

var StageText = map[string]string{
	Queued: "waiting its turn", Planning: "choosing the book's places", Scripting: "designing the room",
	Building: "building and lighting the room", Packaging: "packaging", Done: "built", Failed: "could not be built",
	Unavail: "the book's opening has no third place",
}

type Chapter struct {
	ID    string `json:"id"`
	Title string `json:"title"`
	Text  string `json:"text"`
}

type Book struct {
	Slug     string    `json:"slug"`
	Title    string    `json:"title"`
	Author   string    `json:"author"`
	Chapters []Chapter `json:"chapters"`
}

// Setting is one planned room.
type Setting struct {
	Title    string   `json:"title"`    // "The river meadow"
	Place    string   `json:"place"`    // what the reader stands in, for the builder
	Why      string   `json:"why"`      // why it belongs to this book
	Chapter  string   `json:"chapter"`  // where it first appears
	Kind     string   `json:"kind"`     // interior | exterior
	Time     string   `json:"time"`     // time of day
	Weather  string   `json:"weather"`  // one condition
	Excerpts []string `json:"excerpts"` // the book's own words about the place (short, from the opening only)
}

type Job struct {
	Book     string             `json:"book"`
	Room     int                `json:"room"`
	State    string             `json:"state"`
	Error    string             `json:"error,omitempty"`
	Title    string             `json:"title,omitempty"`
	Attempts int                `json:"attempts"`
	Queued   time.Time          `json:"queued"`
	Timings  map[string]float64 `json:"timings"`
}

func (j *Job) Key() string { return fmt.Sprintf("%s:r%d", j.Book, j.Room) }
func (j *Job) Active() bool {
	return j.State == Planning || j.State == Scripting || j.State == Building || j.State == Packaging
}

type Asker interface {
	Ask(ctx context.Context, system, user string, maxTokens int64) (string, error)
}

// BuildResult is roomgen's FABLE_ROOM line.
type BuildResult struct {
	OK        bool               `json:"ok"`
	Problems  []string           `json:"problems"`
	Triangles int                `json:"triangles"`
	Meshes    int                `json:"meshes"`
	Luma      map[string]float64 `json:"luma"`
	Entrance  []float64          `json:"entrance"`
	Look      []float64          `json:"look"`
	Seconds   map[string]float64 `json:"seconds"`
}

// Builder runs roomgen on a script into out (a fake in tests).
type Builder func(ctx context.Context, root, script, out string) (BuildResult, error)

type Service struct {
	Root       string
	Planner    Asker
	Build      Builder
	MaxBooks   int
	Attempts   int
	OpeningMax int // characters of the opening shown to the planner

	mu   sync.Mutex
	jobs map[string]*Job
	wake chan struct{}
}

func NewService(root string, planner Asker, build Builder) *Service {
	s := &Service{Root: root, Planner: planner, Build: build, MaxBooks: 20, Attempts: 3, OpeningMax: 90000,
		jobs: map[string]*Job{}, wake: make(chan struct{}, 1)}
	s.load()
	return s
}

var slugRe = regexp.MustCompile(`^[a-z0-9][a-z0-9-]{0,63}$`)

func (s *Service) dir() string                { return filepath.Join(s.Root, "out", "rooms") }
func (s *Service) bookDir(slug string) string { return filepath.Join(s.dir(), slug) }
func (s *Service) pkgDir(slug string, n int) string {
	return filepath.Join(s.bookDir(slug), fmt.Sprintf("r%d", n))
}

func (s *Service) load() {
	data, err := os.ReadFile(filepath.Join(s.dir(), "jobs.json"))
	if err != nil {
		return
	}
	var list []*Job
	if json.Unmarshal(data, &list) != nil {
		return
	}
	for _, j := range list {
		if j.Active() {
			j.State = Queued
		}
		if j.State == Done {
			if _, err := os.Stat(filepath.Join(s.pkgDir(j.Book, j.Room), "package.json")); err != nil {
				j.State = Queued
			}
		}
		if j.Timings == nil {
			j.Timings = map[string]float64{}
		}
		s.jobs[j.Key()] = j
	}
}

func (s *Service) saveLocked() {
	list := make([]*Job, 0, len(s.jobs))
	for _, j := range s.jobs {
		list = append(list, j)
	}
	sort.Slice(list, func(a, b int) bool { return list[a].Queued.Before(list[b].Queued) })
	os.MkdirAll(s.dir(), 0o755)
	data, _ := json.MarshalIndent(list, "", "  ")
	tmp := filepath.Join(s.dir(), "jobs.json.tmp")
	if os.WriteFile(tmp, data, 0o644) == nil {
		os.Rename(tmp, filepath.Join(s.dir(), "jobs.json"))
	}
}

var ErrFull = errors.New("too many books waiting for rooms")

// Prepare stores the book's text (once) and queues its three rooms; failed rooms are queued again.
func (s *Service) Prepare(b *Book) ([]*Job, error) {
	if !slugRe.MatchString(b.Slug) {
		return nil, fmt.Errorf("bad book id %q", b.Slug)
	}
	if len(b.Chapters) == 0 {
		return nil, errors.New("the book has no text")
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	books := map[string]bool{}
	for _, j := range s.jobs {
		if j.State != Done && j.State != Failed && j.State != Unavail {
			books[j.Book] = true
		}
	}
	if _, ok := s.jobs[b.Slug+":r1"]; !ok && len(books) >= s.MaxBooks {
		return nil, ErrFull
	}
	os.MkdirAll(s.bookDir(b.Slug), 0o755)
	bp := filepath.Join(s.bookDir(b.Slug), "book.json")
	if _, err := os.Stat(bp); err != nil {
		data, _ := json.Marshal(b)
		if err := os.WriteFile(bp, data, 0o644); err != nil {
			return nil, err
		}
	}
	var out []*Job
	for n := 1; n <= RoomsPerBook; n++ {
		k := fmt.Sprintf("%s:r%d", b.Slug, n)
		j := s.jobs[k]
		if j == nil {
			j = &Job{Book: b.Slug, Room: n, State: Queued, Queued: time.Now(), Timings: map[string]float64{}}
			s.jobs[k] = j
			log.Printf("rooms %s: queued", k)
		} else if j.State == Failed {
			j.State, j.Error = Queued, ""
			log.Printf("rooms %s: queued again after a failure", k)
		}
		out = append(out, j)
	}
	s.saveLocked()
	select {
	case s.wake <- struct{}{}:
	default:
	}
	return out, nil
}

func (s *Service) next() *Job {
	s.mu.Lock()
	defer s.mu.Unlock()
	var best *Job
	for _, j := range s.jobs {
		if j.State == Queued && (best == nil || j.Queued.Before(best.Queued) || (j.Queued.Equal(best.Queued) && j.Room < best.Room)) {
			best = j
		}
	}
	return best
}

func (s *Service) Run(ctx context.Context) {
	for {
		j := s.next()
		if j == nil {
			select {
			case <-ctx.Done():
				return
			case <-s.wake:
			case <-time.After(5 * time.Second):
			}
			continue
		}
		s.runJob(ctx, j)
	}
}

func (s *Service) set(j *Job, state string) {
	s.mu.Lock()
	j.State = state
	s.saveLocked()
	s.mu.Unlock()
}

func (s *Service) fail(j *Job, state string, err error) {
	s.mu.Lock()
	j.State, j.Error = state, err.Error()
	s.saveLocked()
	s.mu.Unlock()
	log.Printf("rooms %s: %s: %v", j.Key(), state, err)
}

func (s *Service) runJob(parent context.Context, j *Job) {
	ctx, cancel := context.WithTimeout(parent, 30*time.Minute)
	defer cancel()
	start := time.Now()
	s.mu.Lock()
	j.Attempts++
	j.Timings["queueWait"] = time.Since(j.Queued).Seconds()
	s.mu.Unlock()
	if s.Planner == nil {
		s.fail(j, Failed, errors.New("the preparation service has no Claude key"))
		return
	}
	b, err := s.loadBook(j.Book)
	if err != nil {
		s.fail(j, Failed, err)
		return
	}
	t := time.Now()
	s.set(j, Planning)
	plan, err := s.plan(ctx, b)
	if err != nil {
		s.fail(j, Failed, fmt.Errorf("planning: %w", err))
		return
	}
	j.Timings[Planning] = time.Since(t).Seconds()
	if j.Room > len(plan) {
		s.fail(j, Unavail, fmt.Errorf("the opening of the book has only %d distinct places", len(plan)))
		return
	}
	st := plan[j.Room-1]
	s.mu.Lock()
	j.Title = st.Title
	s.mu.Unlock()
	work := filepath.Join(s.bookDir(j.Book), fmt.Sprintf("work-r%d", j.Room))
	os.RemoveAll(work)
	os.MkdirAll(work, 0o755)
	var res BuildResult
	var script, problems string
	for attempt := 1; attempt <= s.Attempts; attempt++ {
		t = time.Now()
		s.set(j, Scripting)
		script, err = s.writeScript(ctx, b, st, script, problems)
		j.Timings[Scripting] += time.Since(t).Seconds()
		if err != nil {
			s.fail(j, Failed, fmt.Errorf("scripting: %w", err))
			return
		}
		sp := filepath.Join(work, fmt.Sprintf("room-%d.py", attempt))
		os.WriteFile(sp, []byte(script), 0o644)
		t = time.Now()
		s.set(j, Building)
		out := filepath.Join(work, fmt.Sprintf("build-%d", attempt))
		res, err = s.Build(ctx, s.Root, sp, out)
		j.Timings[Building] += time.Since(t).Seconds()
		if err == nil && res.OK {
			if err := s.pack(j, st, out, res); err != nil {
				s.fail(j, Failed, fmt.Errorf("packaging: %w", err))
				return
			}
			j.Timings["total"] = time.Since(start).Seconds()
			s.set(j, Done)
			log.Printf("rooms %s: %q built in %.0f s (attempt %d, %d triangles)", j.Key(), st.Title, j.Timings["total"], attempt, res.Triangles)
			os.RemoveAll(work)
			return
		}
		if err != nil {
			problems = err.Error()
		} else {
			problems = strings.Join(res.Problems, "\n")
		}
		log.Printf("rooms %s: attempt %d rejected: %s", j.Key(), attempt, strings.ReplaceAll(problems, "\n", "; "))
	}
	s.fail(j, Failed, fmt.Errorf("the room did not pass its checks after %d attempts: %s", s.Attempts, problems))
}

func (s *Service) loadBook(slug string) (*Book, error) {
	data, err := os.ReadFile(filepath.Join(s.bookDir(slug), "book.json"))
	if err != nil {
		return nil, fmt.Errorf("the book's text is missing: %w", err)
	}
	var b Book
	return &b, json.Unmarshal(data, &b)
}

// Opening is what the planner may read: whole chapters from the start until about a third of the book (at least
// the first chapter), capped at max characters.
func Opening(b *Book, max int) string {
	total := 0
	for _, c := range b.Chapters {
		total += len(c.Text)
	}
	limit := total / 3
	var sb strings.Builder
	for i, c := range b.Chapters {
		if i > 0 && sb.Len()+len(c.Text) > limit {
			break
		}
		fmt.Fprintf(&sb, "\n\n[%s] %s\n%s", c.ID, c.Title, c.Text)
		if sb.Len() >= max {
			break
		}
	}
	o := sb.String()
	if len(o) > max {
		o = o[:max]
	}
	return o
}

const planSystem = `You choose reading rooms for Fable, a VR book reader. A reader stands in a room drawn from the book and reads a floating page there for twenty minutes or more. You are given the opening of a book the reader uploaded, and nothing after it. Choose up to three distinct places from this text for the reader to stand in.

Rules:
- Each place must be described or clearly implied in the text you are given. Never use knowledge of the book beyond this text, even if you recognise it: the reader has not read further.
- Places a person could stand in comfortably and calmly: a room, a garden, a shore, a street, a deck, a clearing. Not mid-air, underwater, inside a crowd or a moving vehicle's chaos.
- Three places that differ from each other (ideally one interior and one exterior, different light). Fewer than three only if the text truly has fewer.
- No characters: the place is shown empty. Pick a quiet moment, one time of day and one weather.
- Excerpts: up to four short quotations (under 40 words each) from the text that describe the place.

Answer with JSON only: {"settings":[{"title":"The river meadow","place":"what stands where, materials, era, scale, what the reader sees in front of them and around","why":"one sentence","chapter":"chapter id","kind":"interior|exterior","time":"late afternoon","weather":"clear","excerpts":["..."]}]}`

func (s *Service) plan(ctx context.Context, b *Book) ([]Setting, error) {
	pp := filepath.Join(s.bookDir(b.Slug), "plan.json")
	if data, err := os.ReadFile(pp); err == nil {
		var p []Setting
		if json.Unmarshal(data, &p) == nil && len(p) > 0 {
			return p, nil
		}
	}
	user := fmt.Sprintf("BOOK: %s by %s\n\nTHE OPENING (all you may use):%s", b.Title, b.Author, Opening(b, s.OpeningMax))
	var lastErr error
	for i := 0; i < 2; i++ {
		ans, err := s.Planner.Ask(ctx, planSystem, user, 4000)
		if err != nil {
			return nil, err
		}
		var out struct {
			Settings []Setting `json:"settings"`
		}
		if err := json.Unmarshal([]byte(jsonPart(ans)), &out); err != nil {
			lastErr = err
			continue
		}
		var p []Setting
		for _, st := range out.Settings {
			if strings.TrimSpace(st.Title) != "" && strings.TrimSpace(st.Place) != "" && len(p) < RoomsPerBook {
				p = append(p, st)
			}
		}
		if len(p) == 0 {
			lastErr = errors.New("no places chosen")
			continue
		}
		data, _ := json.MarshalIndent(p, "", "  ")
		os.WriteFile(pp, data, 0o644)
		return p, nil
	}
	return nil, lastErr
}

func jsonPart(s string) string {
	a, b := strings.Index(s, "{"), strings.LastIndex(s, "}")
	if a < 0 || b < a {
		return s
	}
	return s[a : b+1]
}

var codeRe = regexp.MustCompile("(?s)```(?:python)?\\s*\\n(.*?)```")

func (s *Service) writeScript(ctx context.Context, b *Book, st Setting, previous, problems string) (string, error) {
	sys, err := s.scriptSystem()
	if err != nil {
		return "", err
	}
	spec, _ := json.MarshalIndent(st, "", "  ")
	user := fmt.Sprintf("BOOK: %s by %s\n\nTHE PLACE:\n%s\n\nWrite the room script.", b.Title, b.Author, spec)
	if previous != "" {
		user += "\n\nYour previous script was rejected by the checks:\n" + problems + "\n\nPREVIOUS SCRIPT:\n```python\n" + previous + "\n```\nWrite the corrected complete script."
	}
	ans, err := s.Planner.Ask(ctx, sys, user, 16000)
	if err != nil {
		return "", err
	}
	if m := codeRe.FindStringSubmatch(ans); m != nil {
		return m[1], nil
	}
	return ans, nil
}

// scriptSystem: the builder's instructions with the kit's API, read from roomkit.py so it never drifts.
func (s *Service) scriptSystem() (string, error) {
	kit, err := os.ReadFile(filepath.Join(s.Root, "blender", "roomkit.py"))
	if err != nil {
		return "", err
	}
	example, _ := os.ReadFile(filepath.Join(s.Root, "blender", "roomkit_example.py"))
	return fmt.Sprintf(scriptSystem, KitAPI(string(kit)), string(example)), nil
}

var defRe = regexp.MustCompile(`(?ms)^def ([a-z]\w*)\((.*?)\):\n\s+"""(.*?)"""`)

// KitAPI lists roomkit's public functions with their signatures and docstrings.
func KitAPI(src string) string {
	var sb strings.Builder
	for _, m := range defRe.FindAllStringSubmatch(src, -1) {
		if m[1] == "begin" {
			continue
		}
		fmt.Fprintf(&sb, "kit.%s(%s)\n    %s\n\n", m[1], strings.Join(strings.Fields(m[2]), " "), strings.Join(strings.Fields(m[3]), " "))
	}
	return sb.String()
}

const scriptSystem = `You build one reading room for Fable, a VR book reader, as a short Python script for Blender. The reader stands in the room and reads a floating page for twenty minutes, so the place must feel like a quietly observed real location: physically plausible scale (metres), one coherent time of day and light direction, structure in the land (a rise, a bank, a shore) rather than even noise, objects grounded and varied rather than evenly scattered, plants varying in size and lean, materials with believable colours (sRGB 0-1, not oversaturated), and calm, low-contrast surroundings in the direction the reader faces, where the page floats about 0.6 m in front of their eyes. Detail goes near the reader; distance can be simple. No people or animals.

Your script runs with these names already in scope (no imports allowed, none needed): kit (below), bpy, bmesh, math, random, Vector, Euler, Matrix, noise. Not allowed: import, names or attributes starting with "_", open/exec/eval/getattr and similar, try/with/class/global, and bpy.ops/bpy.data areas that touch files. Prefer the kit; use bpy/bmesh directly only for shapes the kit lacks.

Required in every script: kit.sky(...) once; kit.sun(...) for daylight (and/or kit.lamp/kit.area_light for interiors: put a light where the light comes from: windows, a fire, lamps); kit.reader(entrance, look) once, with the entrance on open floor or ground and the look point a few metres or more away at about eye height. Keep within about 35,000 triangles (hard limit 65,000) and at most 40 distinct materials (each material becomes one mesh). Interiors: use kit.room(...) with real window and door openings and light coming in through them, and put the reader 1.5 m or more from walls and furniture in the facing direction. The checks reject: a missing reader, sky or light; something solid within 1.2 m in front of the reader's eyes; standing inside an object; a reading view almost black or washed out; budget overruns; script errors.

THE KIT (roomkit.py):
%s
AN EXAMPLE OF A GOOD SCRIPT:
` + "```python\n%s\n```" + `

Answer with the complete script in one python code block, preceded by at most three sentences about your choices.`

// pack copies the build into the room's package folder with a manifest, swapping it in whole.
func (s *Service) pack(j *Job, st Setting, build string, res BuildResult) error {
	s.set(j, Packaging)
	dst := s.pkgDir(j.Book, j.Room)
	stage := dst + ".part"
	os.RemoveAll(stage)
	type file struct {
		Path   string `json:"path"`
		Size   int64  `json:"size"`
		SHA256 string `json:"sha256"`
	}
	var files []file
	var total int64
	copyFile := func(rel, from string) error {
		in, err := os.Open(from)
		if err != nil {
			return err
		}
		defer in.Close()
		p := filepath.Join(stage, rel)
		os.MkdirAll(filepath.Dir(p), 0o755)
		out, err := os.Create(p)
		if err != nil {
			return err
		}
		h := sha256.New()
		n, err := io.Copy(io.MultiWriter(out, h), in)
		out.Close()
		if err != nil {
			return err
		}
		total += n
		files = append(files, file{rel, n, hex.EncodeToString(h.Sum(nil))})
		return nil
	}
	if err := copyFile("room.gltf", filepath.Join(build, "room.gltf")); err != nil {
		return err
	}
	if err := copyFile("room.bin", filepath.Join(build, "room.bin")); err != nil {
		return err
	}
	texs, _ := filepath.Glob(filepath.Join(build, "textures", "*.jpg"))
	for _, t := range texs {
		if err := copyFile("textures/"+filepath.Base(t), t); err != nil {
			return err
		}
	}
	if err := copyFile("thumb.png", filepath.Join(build, "views", "thumb.png")); err != nil {
		return err
	}
	if total > 40<<20 {
		return fmt.Errorf("package is %d MB, over 40 MB", total>>20)
	}
	manifest := map[string]any{"version": 1, "book": j.Book, "room": j.Room, "title": st.Title, "place": st.Place, "why": st.Why,
		"chapter": st.Chapter, "files": files, "entrance": res.Entrance, "look": res.Look, "triangles": res.Triangles, "meshes": res.Meshes,
		"bytes": total}
	data, _ := json.MarshalIndent(manifest, "", "  ")
	if err := os.WriteFile(filepath.Join(stage, "package.json"), data, 0o644); err != nil {
		return err
	}
	os.RemoveAll(dst)
	return os.Rename(stage, dst)
}

// RoomgenBuilder runs blender/roomgen.py in a fresh Blender with no user settings or add-ons.
func RoomgenBuilder(blender string) Builder {
	return func(ctx context.Context, root, script, out string) (BuildResult, error) {
		root, _ = filepath.Abs(root)
		script, _ = filepath.Abs(script)
		out, _ = filepath.Abs(out)
		cmd := exec.CommandContext(ctx, blender, "-b", "--factory-startup", "-noaudio", "-P", filepath.Join(root, "blender", "roomgen.py"), "--",
			"--script", script, "--out", out, "--tex", "1024", "--samples", "40")
		cmd.Dir = filepath.Dir(script)
		// the normal environment (Cycles keeps its GPU kernel cache under HOME; a fresh HOME crashed Metal), minus
		// anything secret: the room script must never be able to see the Claude key
		for _, kv := range os.Environ() {
			if k, _, _ := strings.Cut(kv, "="); !strings.Contains(strings.ToUpper(k), "KEY") && !strings.Contains(strings.ToUpper(k), "TOKEN") && !strings.Contains(strings.ToUpper(k), "SECRET") {
				cmd.Env = append(cmd.Env, kv)
			}
		}
		data, err := cmd.CombinedOutput()
		for _, line := range strings.Split(string(data), "\n") {
			if strings.HasPrefix(line, "FABLE_ROOM ") {
				var r BuildResult
				if json.Unmarshal([]byte(strings.TrimPrefix(line, "FABLE_ROOM ")), &r) == nil {
					return r, nil
				}
			}
		}
		tail := string(data)
		if len(tail) > 600 {
			tail = tail[len(tail)-600:]
		}
		if err == nil {
			err = errors.New("no result line")
		}
		return BuildResult{}, fmt.Errorf("Blender failed: %v: %s", err, tail)
	}
}

// ---------------------------------------------------------------- HTTP

type statusOut struct {
	Room     int                `json:"room"`
	State    string             `json:"state"`
	Stage    string             `json:"stage"`
	Title    string             `json:"title,omitempty"`
	Error    string             `json:"error,omitempty"`
	Attempts int                `json:"attempts"`
	Timings  map[string]float64 `json:"timings,omitempty"`
}

func (s *Service) Status(book string) []statusOut {
	s.mu.Lock()
	defer s.mu.Unlock()
	var out []statusOut
	for n := 1; n <= RoomsPerBook; n++ {
		if j := s.jobs[fmt.Sprintf("%s:r%d", book, n)]; j != nil {
			out = append(out, statusOut{j.Room, j.State, StageText[j.State], j.Title, j.Error, j.Attempts, j.Timings})
		}
	}
	return out
}

func (s *Service) Register(mux *http.ServeMux) {
	mux.HandleFunc("POST /rooms/prepare", func(w http.ResponseWriter, r *http.Request) {
		var b Book
		if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 12<<20)).Decode(&b); err != nil {
			http.Error(w, "bad book: "+err.Error(), http.StatusBadRequest)
			return
		}
		if _, err := s.Prepare(&b); err != nil {
			code := http.StatusBadRequest
			if errors.Is(err, ErrFull) {
				code = http.StatusTooManyRequests
			}
			http.Error(w, err.Error(), code)
			return
		}
		writeJSON(w, s.Status(b.Slug))
	})
	mux.HandleFunc("GET /rooms/status", func(w http.ResponseWriter, r *http.Request) {
		st := s.Status(r.URL.Query().Get("book"))
		if st == nil {
			http.Error(w, "no rooms for that book", http.StatusNotFound)
			return
		}
		writeJSON(w, st)
	})
	mux.HandleFunc("GET /rooms/package", func(w http.ResponseWriter, r *http.Request) {
		dir, ok := s.doneDir(w, r)
		if ok {
			http.ServeFile(w, r, filepath.Join(dir, "package.json"))
		}
	})
	mux.HandleFunc("GET /rooms/file", func(w http.ResponseWriter, r *http.Request) {
		dir, ok := s.doneDir(w, r)
		if !ok {
			return
		}
		rel := r.URL.Query().Get("path")
		var m struct {
			Files []struct {
				Path string `json:"path"`
			} `json:"files"`
		}
		data, _ := os.ReadFile(filepath.Join(dir, "package.json"))
		json.Unmarshal(data, &m)
		for _, f := range m.Files {
			if f.Path == rel { // only files the manifest lists
				http.ServeFile(w, r, filepath.Join(dir, filepath.FromSlash(rel)))
				return
			}
		}
		http.Error(w, "no such file in the package", http.StatusNotFound)
	})
}

func (s *Service) doneDir(w http.ResponseWriter, r *http.Request) (string, bool) {
	book := r.URL.Query().Get("book")
	n, _ := strconv.Atoi(r.URL.Query().Get("room"))
	s.mu.Lock()
	j := s.jobs[fmt.Sprintf("%s:r%d", book, n)]
	s.mu.Unlock()
	if j == nil || !slugRe.MatchString(book) {
		http.Error(w, "no such room", http.StatusNotFound)
		return "", false
	}
	if j.State != Done {
		http.Error(w, "the room is not built yet", http.StatusConflict)
		return "", false
	}
	return s.pkgDir(book, n), true
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(v)
}
