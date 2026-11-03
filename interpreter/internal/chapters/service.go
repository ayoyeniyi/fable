package chapters

import (
	"bufio"
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"image"
	"image/jpeg"
	"image/png"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/Thabhelo/fable/interpreter/internal/book"
	"github.com/Thabhelo/fable/interpreter/internal/books"
	"github.com/Thabhelo/fable/interpreter/internal/script"
)

// Job states. "unavailable" is a finished job whose chapter no built environment can honestly stand for.
const (
	Queued      = "queued"
	Planning    = "planning"
	Scripting   = "scripting"
	Rendering   = "rendering"
	Validating  = "validating"
	Packaging   = "packaging"
	Done        = "done"
	Failed      = "failed"
	Unavailable = "unavailable"
)

// Stage names shown to the reader, per state.
var StageText = map[string]string{
	Queued: "waiting its turn", Planning: "choosing the place in the chapter", Scripting: "staging the scene",
	Rendering: "building the view in Blender", Validating: "checking the scene", Packaging: "packaging for the headset",
	Done: "built, waiting for the headset to fetch it", Failed: "preparation failed", Unavailable: "no place built for this chapter yet",
}

type Job struct {
	Book      string             `json:"book"`
	Chapter   string             `json:"chapter"`
	Completed bool               `json:"completed"` // the reader has finished the chapter: goes ahead of the others
	State     string             `json:"state"`
	Error     string             `json:"error,omitempty"`
	Attempts  int                `json:"attempts"`
	Queued    time.Time          `json:"queued"`
	Started   time.Time          `json:"started,omitempty"`
	Finished  time.Time          `json:"finished,omitempty"`
	Timings   map[string]float64 `json:"timings"` // seconds per stage, plus queueWait and total
	Delivered float64            `json:"deliveredSeconds,omitempty"`
}

func (j *Job) Key() string { return j.Chapter }
func (j *Job) Active() bool {
	return j.State == Planning || j.State == Scripting || j.State == Rendering || j.State == Validating || j.State == Packaging
}

// Asker is the planning call (llm.Director.Ask); Scripter stages a passage (llm.Director.Interpret).
type Asker interface {
	Ask(ctx context.Context, system, user string, maxTokens int64) (string, error)
}
type Scripter interface {
	Interpret(ctx context.Context, sc *book.Scene, m *script.Manifest, readingPosition string, variant int) (*script.SceneScript, []string, error)
}

// RenderResult is what the Blender stage reports.
type RenderResult struct {
	OK       bool    `json:"ok"`
	Seconds  float64 `json:"seconds"`
	MeanLuma float64 `json:"meanLuma"`
	Exposure float64 `json:"exposure"`
}

type Renderer func(ctx context.Context, root string, e Env, mood string, fog float64, out string) (RenderResult, error)

type Service struct {
	Root     string
	Catalog  *Catalog
	Passages *book.Book // Alice's cut passages (book/passages.json): the scripted environments' text
	Planner  Asker
	Script   Scripter
	Render   Renderer
	Model    string
	MaxQueue int           // jobs waiting or running at once; more are refused (the headset retries)
	Timeout  time.Duration // per job

	mu    sync.Mutex
	jobs  map[string]*Job
	books map[string]*books.Book
	wake  chan struct{}
}

func NewService(root string, cat *Catalog, passages *book.Book, planner Asker, scr Scripter, render Renderer) *Service {
	s := &Service{Root: root, Catalog: cat, Passages: passages, Planner: planner, Script: scr, Render: render, MaxQueue: 12, Timeout: 12 * time.Minute,
		jobs: map[string]*Job{}, books: map[string]*books.Book{}, wake: make(chan struct{}, 1)}
	s.load()
	return s
}

func (s *Service) dir() string      { return filepath.Join(s.Root, "out", "chapters") }
func (s *Service) jobsPath() string { return filepath.Join(s.dir(), "jobs.json") }
func (s *Service) pkgDir(chapter string) string {
	return filepath.Join(s.dir(), strings.ReplaceAll(chapter, ":", "_"))
}

// load restores the queue: a job that was mid-pipeline when the server stopped goes back to the queue.
func (s *Service) load() {
	data, err := os.ReadFile(s.jobsPath())
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
			log.Printf("chapters %s: resumed after restart", j.Chapter)
		}
		if j.State == Done {
			if _, err := os.Stat(filepath.Join(s.pkgDir(j.Chapter), "package.json")); err != nil {
				j.State = Queued // its package is gone: build it again
			}
		}
		// "no place built yet" was a verdict on the rooms that existed then: when rooms have been added since, plan again
		if j.State == Unavailable {
			if fi, err := os.Stat(filepath.Join(s.Root, "schema", "environments.json")); err == nil && fi.ModTime().After(j.Queued) {
				j.State, j.Error = Queued, ""
				log.Printf("chapters %s: rooms were added since it was found to have none; planning again", j.Chapter)
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
	tmp := s.jobsPath() + ".tmp"
	if os.WriteFile(tmp, data, 0o644) == nil {
		os.Rename(tmp, s.jobsPath())
	}
}

func (s *Service) book(slug string) (*books.Book, error) {
	s.mu.Lock()
	b := s.books[slug]
	s.mu.Unlock()
	if b != nil {
		return b, nil
	}
	b, err := books.Load(s.Root, slug)
	if err != nil {
		return nil, err
	}
	s.mu.Lock()
	s.books[slug] = b
	s.mu.Unlock()
	return b, nil
}

var ErrFull = errors.New("the preparation queue is full")

// Prepare queues a chapter (idempotent). A chapter the reader has completed moves ahead of the others; a failed job
// is queued again (the reader's retry). Starting one chapter never cancels another.
func (s *Service) Prepare(slug, chapter string, completed bool) (*Job, error) {
	b, err := s.book(slug)
	if err != nil {
		return nil, fmt.Errorf("unknown book %q", slug)
	}
	if !strings.HasPrefix(chapter, slug+":") {
		return nil, fmt.Errorf("chapter %q is not in %s", chapter, slug)
	}
	if _, err := chapterIndex(b, chapter); err != nil {
		return nil, err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if j, ok := s.jobs[chapter]; ok {
		changed := false
		if completed && !j.Completed {
			j.Completed, changed = true, true
		}
		if j.State == Failed {
			j.State, j.Error, j.Queued, changed = Queued, "", time.Now(), true
		}
		if changed {
			s.saveLocked()
			s.poke()
		}
		return j, nil
	}
	waiting := 0
	for _, j := range s.jobs {
		if j.State == Queued || j.Active() {
			waiting++
		}
	}
	if waiting >= s.MaxQueue {
		return nil, ErrFull
	}
	j := &Job{Book: slug, Chapter: chapter, Completed: completed, State: Queued, Queued: time.Now(), Timings: map[string]float64{}}
	s.jobs[chapter] = j
	s.saveLocked()
	s.poke()
	log.Printf("chapters %s: queued (completed=%v)", chapter, completed)
	return j, nil
}

func (s *Service) poke() {
	select {
	case s.wake <- struct{}{}:
	default:
	}
}

// Status returns a copy of a job, or nil.
func (s *Service) Status(chapter string) *Job {
	s.mu.Lock()
	defer s.mu.Unlock()
	if j, ok := s.jobs[chapter]; ok {
		c := *j
		c.Timings = map[string]float64{}
		for k, v := range j.Timings {
			c.Timings[k] = v
		}
		return &c
	}
	return nil
}

// next picks the job to run: completed chapters first, then the oldest.
func (s *Service) next() *Job {
	s.mu.Lock()
	defer s.mu.Unlock()
	var best *Job
	for _, j := range s.jobs {
		if j.State != Queued {
			continue
		}
		if best == nil || (j.Completed && !best.Completed) || (j.Completed == best.Completed && j.Queued.Before(best.Queued)) {
			best = j
		}
	}
	return best
}

// Run works the queue, one job at a time, until ctx ends.
func (s *Service) Run(ctx context.Context) {
	for {
		j := s.next()
		if j == nil {
			select {
			case <-ctx.Done():
				return
			case <-s.wake:
				continue
			case <-time.After(5 * time.Second):
				continue
			}
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

func (s *Service) runJob(parent context.Context, j *Job) {
	ctx, cancel := context.WithTimeout(parent, s.Timeout)
	defer cancel()
	s.mu.Lock()
	j.Started = time.Now()
	j.Attempts++
	j.Timings = map[string]float64{"queueWait": j.Started.Sub(j.Queued).Seconds()}
	s.mu.Unlock()
	timed := func(stage string, f func() error) error {
		s.set(j, stage)
		t := time.Now()
		err := f()
		s.mu.Lock()
		j.Timings[stage] = time.Since(t).Seconds()
		s.mu.Unlock()
		return err
	}
	err := s.pipeline(ctx, j, timed)
	s.mu.Lock()
	j.Finished = time.Now()
	j.Timings["total"] = j.Finished.Sub(j.Queued).Seconds()
	var un *unavailableErr
	switch {
	case errors.As(err, &un):
		j.State, j.Error = Unavailable, un.why
	case err != nil:
		j.State, j.Error = Failed, err.Error()
	default:
		j.State, j.Error = Done, ""
	}
	s.saveLocked()
	s.mu.Unlock()
	log.Printf("chapters %s: %s after %.1f s (%s) %s", j.Chapter, j.State, j.Timings["total"], fmtTimings(j.Timings), j.Error)
}

func fmtTimings(t map[string]float64) string {
	var parts []string
	for _, k := range []string{"queueWait", Planning, Scripting, Rendering, Validating, Packaging} {
		if v, ok := t[k]; ok {
			parts = append(parts, fmt.Sprintf("%s %.1fs", k, v))
		}
	}
	return strings.Join(parts, ", ")
}

type unavailableErr struct{ why string }

func (u *unavailableErr) Error() string { return u.why }

// Package is the headset's contract (Unity: ChapterExperiencePackage).
type Package struct {
	Version     int                 `json:"version"`
	Book        string              `json:"book"`
	Chapter     string              `json:"chapter"`
	ChapterName string              `json:"chapterName"`
	Title       string              `json:"title"`
	Place       string              `json:"place"`
	Environment string              `json:"environment"`
	UnityScene  string              `json:"unityScene"`
	Staging     string              `json:"staging"`
	Passage     string              `json:"passage,omitempty"`
	Moment      Range               `json:"moment"`
	Mood        string              `json:"mood"`
	Fog         float64             `json:"fog"`
	Script      *script.SceneScript `json:"script,omitempty"`
	Thumbnail   Thumb               `json:"thumbnail"`
	Triangles   int                 `json:"triangles"`
	Meshes      int                 `json:"meshes"`
	OverTarget  bool                `json:"overTriangleTarget"`
	Timings     map[string]float64  `json:"timings"`
	CreatedUTC  string              `json:"createdUtc"`
	Model       string              `json:"model"`
}

type Thumb struct {
	File   string `json:"file"`
	SHA256 string `json:"sha256"`
	Width  int    `json:"width"`
	Height int    `json:"height"`
	Bytes  int    `json:"bytes"`
}

const maxPackageBytes = 1 << 20

func (s *Service) passageFor(chapter string) *book.Scene {
	if s.Passages == nil {
		return nil
	}
	for i := range s.Passages.Scenes {
		sc := &s.Passages.Scenes[i]
		if sc.BookFrom != "" && strings.HasPrefix(sc.BookFrom, chapter+".") {
			return sc
		}
	}
	return nil
}

func (s *Service) manifest(id string) (*script.Manifest, error) {
	data, err := os.ReadFile(filepath.Join(s.Root, "schema", "manifest."+id+".json"))
	if err != nil {
		return nil, err
	}
	var m script.Manifest
	return &m, json.Unmarshal(data, &m)
}

// earlier lists the finished experiences of chapters before this one, for continuity.
func (s *Service) earlier(b *books.Book, ci int) []Earlier {
	var out []Earlier
	for i := 0; i < ci; i++ {
		data, err := os.ReadFile(filepath.Join(s.pkgDir(b.Chapters[i].ID), "package.json"))
		if err != nil {
			continue
		}
		var p Package
		if json.Unmarshal(data, &p) == nil {
			out = append(out, Earlier{Chapter: b.Chapters[i].Title, Title: p.Title, Place: p.Place, Environment: p.Environment, Mood: p.Mood})
		}
	}
	return out
}

func (s *Service) pipeline(ctx context.Context, j *Job, timed func(string, func() error) error) error {
	b, err := s.book(j.Book)
	if err != nil {
		return err
	}
	ci, err := chapterIndex(b, j.Chapter)
	if err != nil {
		return err
	}
	// a book with no built place at all (Fable's later books, whose reading rooms are generated): nothing to plan
	// with, so the chapter is unavailable at once, without asking Claude; a new environment for the book re-plans it
	if len(s.Catalog.ForBook(j.Book)) == 0 && s.passageFor(j.Chapter) == nil {
		return &unavailableErr{why: "no place has been built for this book's chapters yet"}
	}
	dir := s.pkgDir(j.Chapter)
	work := dir + ".work"
	os.RemoveAll(work)
	if err := os.MkdirAll(work, 0o755); err != nil {
		return err
	}
	defer os.RemoveAll(work)

	// scripted environments: the chapter's cut passage fixes the room
	passage := s.passageFor(j.Chapter)
	fixed := ""
	allowed := s.Catalog.ForBook(j.Book)
	if passage != nil {
		fixed = passage.Room
		if fixed == "" {
			fixed = passage.ID
		}
	}

	// 1. planning
	var plan *Plan
	if err := timed(Planning, func() error {
		if s.Planner == nil {
			return errors.New("the preparation service has no Claude key")
		}
		user := PlanPrompt(b, ci, allowed, s.Catalog.Moods, s.earlier(b, ci), fixed)
		raw, err := s.Planner.Ask(ctx, planSystem, user, 2000)
		if err != nil {
			return fmt.Errorf("planning: %w", err)
		}
		p, probs := ParsePlan(raw, b, ci, s.Catalog, allowed, fixed)
		if len(probs) > 0 {
			raw2, err := s.Planner.Ask(ctx, planSystem, user+"\n\nYour previous answer was:\n"+raw+"\nIt was rejected:\n- "+strings.Join(probs, "\n- ")+"\nReturn the corrected JSON object only.", 2000)
			if err != nil {
				return fmt.Errorf("planning repair: %w", err)
			}
			p, probs = ParsePlan(raw2, b, ci, s.Catalog, allowed, fixed)
			if len(probs) > 0 {
				return fmt.Errorf("plan still invalid after repair: %s", strings.Join(probs, "; "))
			}
		}
		plan = p
		pj, _ := json.MarshalIndent(plan, "", "  ")
		return os.WriteFile(filepath.Join(work, "plan.json"), pj, 0o644)
	}); err != nil {
		return err
	}
	if plan.Environment == "none" {
		os.MkdirAll(dir, 0o755)
		os.Rename(filepath.Join(work, "plan.json"), filepath.Join(dir, "plan.json"))
		return &unavailableErr{why: "none of Fable's built places fits this chapter; it needs a new environment (" + plan.Why + ")"}
	}
	env, _ := s.Catalog.Env(plan.Environment)

	// 2. scripting (scripted environments only)
	var sc *script.SceneScript
	if env.Staging == "scripted" && passage != nil {
		if err := timed(Scripting, func() error {
			m, err := s.manifest(passage.ID)
			if err != nil {
				return fmt.Errorf("manifest for %s: %w", passage.ID, err)
			}
			ids := passage.SentenceIDs()
			out, _, err := s.Script.Interpret(ctx, passage, m, ids[len(ids)-1], 0)
			if err != nil {
				return fmt.Errorf("staging: %w", err)
			}
			sc = out
			return nil
		}); err != nil {
			return err
		}
	}

	// 3. rendering
	var rr RenderResult
	png := filepath.Join(work, "thumb.png")
	if err := timed(Rendering, func() error {
		r, err := s.Render(ctx, s.Root, env, plan.Mood, plan.Fog, png)
		rr = r
		return err
	}); err != nil {
		return fmt.Errorf("Blender: %w", err)
	}

	// 4. validating
	var img image.Image
	if err := timed(Validating, func() error {
		var probs []string
		probs = append(probs, s.Catalog.BudgetProblems(env)...)
		if sc != nil {
			m, _ := s.manifest(passage.ID)
			probs = append(probs, script.Validate(sc, m, passage.SentenceIDs())...)
		}
		f, err := os.Open(png)
		if err != nil {
			return fmt.Errorf("the render is missing: %w", err)
		}
		defer f.Close()
		img, _, err = image.Decode(bufio.NewReader(f))
		if err != nil {
			return fmt.Errorf("the render is not a readable image: %w", err)
		}
		if bd := img.Bounds(); bd.Dx() < 320 || bd.Dy() < 200 {
			probs = append(probs, fmt.Sprintf("the render is %dx%d, smaller than 320x200", bd.Dx(), bd.Dy()))
		}
		if rr.MeanLuma < 0.02 || rr.MeanLuma > 0.9 {
			probs = append(probs, fmt.Sprintf("the render is %s (mean brightness %.3f)", map[bool]string{true: "nearly black", false: "washed out"}[rr.MeanLuma < 0.02], rr.MeanLuma))
		}
		if len(probs) > 0 {
			return fmt.Errorf("validation: %s", strings.Join(probs, "; "))
		}
		return nil
	}); err != nil {
		return err
	}

	// 5. packaging
	return timed(Packaging, func() error {
		var jb bytes.Buffer
		if err := jpeg.Encode(&jb, img, &jpeg.Options{Quality: 84}); err != nil {
			return err
		}
		sum := sha256.Sum256(jb.Bytes())
		if err := os.WriteFile(filepath.Join(work, "thumb.jpg"), jb.Bytes(), 0o644); err != nil {
			return err
		}
		os.Remove(png)
		p := Package{Version: 1, Book: j.Book, Chapter: j.Chapter, ChapterName: b.Chapters[ci].Title, Title: plan.Title, Place: plan.Place,
			Environment: env.ID, UnityScene: env.UnityScene, Staging: env.Staging, Moment: plan.Moment, Mood: plan.Mood, Fog: plan.Fog, Script: sc,
			Thumbnail: Thumb{File: "thumb.jpg", SHA256: hex.EncodeToString(sum[:]), Width: img.Bounds().Dx(), Height: img.Bounds().Dy(), Bytes: jb.Len()},
			Triangles: env.Triangles, Meshes: env.Meshes, OverTarget: env.Triangles > s.Catalog.Budget.TargetTriangles,
			CreatedUTC: time.Now().UTC().Format(time.RFC3339), Model: s.Model, Timings: map[string]float64{}}
		if passage != nil && env.Staging == "scripted" {
			p.Passage = passage.ID
		}
		s.mu.Lock()
		for k, v := range j.Timings {
			p.Timings[k] = v
		}
		s.mu.Unlock()
		p.Timings["blenderRender"] = rr.Seconds
		pj, _ := json.MarshalIndent(p, "", "  ")
		if len(pj)+jb.Len() > maxPackageBytes {
			return fmt.Errorf("the package is %d KB, over the 1 MB limit", (len(pj)+jb.Len())/1024)
		}
		if err := os.WriteFile(filepath.Join(work, "package.json"), pj, 0o644); err != nil {
			return err
		}
		// swap in: the old package (a retry) goes only once the new one is complete
		os.RemoveAll(dir)
		return os.Rename(work, dir)
	})
}

// BlenderRenderer runs blender/render_experience_thumb.py headless.
func BlenderRenderer(blender string) Renderer {
	return func(ctx context.Context, root string, e Env, mood string, fog float64, out string) (RenderResult, error) {
		cmd := exec.CommandContext(ctx, blender, "-b", "-P", filepath.Join(root, "blender", "render_experience_thumb.py"), "--",
			filepath.Join(root, e.GLTF), out, "--mood", mood, "--fog", fmt.Sprint(fog), "--eye", e.Eye, "--look", e.Look)
		data, err := cmd.CombinedOutput()
		for _, line := range strings.Split(string(data), "\n") {
			if strings.HasPrefix(line, "FABLE_THUMB ") {
				var r RenderResult
				if json.Unmarshal([]byte(strings.TrimPrefix(line, "FABLE_THUMB ")), &r) == nil && r.OK {
					return r, nil
				}
			}
		}
		tail := string(data)
		if len(tail) > 400 {
			tail = tail[len(tail)-400:]
		}
		if err == nil {
			err = errors.New("no result line")
		}
		return RenderResult{}, fmt.Errorf("render failed: %v: %s", err, tail)
	}
}

// ---------------------------------------------------------------- HTTP

type statusOut struct {
	Chapter   string             `json:"chapter"`
	State     string             `json:"state"`
	Stage     string             `json:"stage"`
	Error     string             `json:"error,omitempty"`
	Attempts  int                `json:"attempts"`
	Position  int                `json:"position,omitempty"` // place in the queue (1 = next)
	Timings   map[string]float64 `json:"timings,omitempty"`
	Completed bool               `json:"completed"`
}

// statusFor never carries a title, place or image: only how far the job has got.
func (s *Service) statusFor(j *Job) statusOut {
	out := statusOut{Chapter: j.Chapter, State: j.State, Stage: StageText[j.State], Error: j.Error, Attempts: j.Attempts, Timings: j.Timings, Completed: j.Completed}
	if j.State == Queued {
		s.mu.Lock()
		n := 1
		for _, o := range s.jobs {
			if o != j && o.State == Queued && ((o.Completed && !j.Completed) || (o.Completed == j.Completed && o.Queued.Before(j.Queued))) {
				n++
			}
			if o.Active() {
				n++
			}
		}
		s.mu.Unlock()
		out.Position = n
	}
	return out
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func (s *Service) Register(mux *http.ServeMux) {
	mux.HandleFunc("POST /chapters/prepare", func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			Book      string `json:"book"`
			Chapter   string `json:"chapter"`
			Completed bool   `json:"completed"`
		}
		if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 4096)).Decode(&req); err != nil {
			writeJSON(w, 400, map[string]string{"error": err.Error()})
			return
		}
		j, err := s.Prepare(req.Book, req.Chapter, req.Completed)
		if errors.Is(err, ErrFull) {
			w.Header().Set("Retry-After", "60")
			writeJSON(w, 429, map[string]string{"error": err.Error()})
			return
		}
		if err != nil {
			writeJSON(w, 404, map[string]string{"error": err.Error()})
			return
		}
		writeJSON(w, 200, s.statusFor(s.Status(j.Chapter)))
	})
	mux.HandleFunc("GET /chapters/status", func(w http.ResponseWriter, r *http.Request) {
		j := s.Status(r.URL.Query().Get("chapter"))
		if j == nil {
			writeJSON(w, 404, map[string]string{"error": "not queued"})
			return
		}
		writeJSON(w, 200, s.statusFor(j))
	})
	mux.HandleFunc("GET /chapters/package", func(w http.ResponseWriter, r *http.Request) {
		ch := r.URL.Query().Get("chapter")
		if j := s.Status(ch); j == nil || j.State != Done {
			writeJSON(w, 409, map[string]string{"error": "not built"})
			return
		}
		http.ServeFile(w, r, filepath.Join(s.pkgDir(ch), "package.json"))
	})
	mux.HandleFunc("GET /chapters/thumb", func(w http.ResponseWriter, r *http.Request) {
		ch := r.URL.Query().Get("chapter")
		if j := s.Status(ch); j == nil || j.State != Done {
			writeJSON(w, 409, map[string]string{"error": "not built"})
			return
		}
		w.Header().Set("Content-Type", "image/jpeg")
		http.ServeFile(w, r, filepath.Join(s.pkgDir(ch), "thumb.jpg"))
	})
	// the headset says it has the package, checked and stored: end-to-end time, measured on the headset
	mux.HandleFunc("POST /chapters/delivered", func(w http.ResponseWriter, r *http.Request) {
		var req struct {
			Chapter        string  `json:"chapter"`
			HeadsetSeconds float64 `json:"headsetSeconds"`
		}
		json.NewDecoder(http.MaxBytesReader(w, r.Body, 4096)).Decode(&req)
		s.mu.Lock()
		if j, ok := s.jobs[req.Chapter]; ok {
			j.Delivered = req.HeadsetSeconds
			s.saveLocked()
		}
		s.mu.Unlock()
		log.Printf("chapters %s: on the headset, %.1f s after the headset asked", req.Chapter, req.HeadsetSeconds)
		writeJSON(w, 200, map[string]bool{"ok": true})
	})
	mux.HandleFunc("GET /chapters/jobs", func(w http.ResponseWriter, r *http.Request) {
		s.mu.Lock()
		list := make([]*Job, 0, len(s.jobs))
		for _, j := range s.jobs {
			list = append(list, j)
		}
		s.mu.Unlock()
		sort.Slice(list, func(a, b int) bool { return list[a].Queued.Before(list[b].Queued) })
		out := make([]statusOut, 0, len(list))
		for _, j := range list {
			out = append(out, s.statusFor(j))
		}
		writeJSON(w, 200, out)
	})
}

var _ = png.Decode // registers the PNG decoder for image.Decode
