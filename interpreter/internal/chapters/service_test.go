package chapters

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/Thabhelo/fable/interpreter/internal/books"
)

// the repo root, two levels up from interpreter/internal/chapters
func repoRoot(t *testing.T) string {
	wd, _ := os.Getwd()
	return filepath.Clean(filepath.Join(wd, "..", "..", ".."))
}

// fakePlanner answers with a plan for the first sentences of whichever chapter the prompt holds, and records prompts.
type fakePlanner struct {
	mu      sync.Mutex
	prompts []string
	env     string
	fail    bool
}

func (f *fakePlanner) Ask(ctx context.Context, system, user string, maxTokens int64) (string, error) {
	f.mu.Lock()
	f.prompts = append(f.prompts, user)
	fail := f.fail
	f.mu.Unlock()
	if fail {
		return "", errors.New("no connection")
	}
	// the chapter's first and third sentence ids, from the prompt's "[id] text" lines after THIS CHAPTER
	body := user[strings.Index(user, "THIS CHAPTER:"):]
	var ids []string
	for _, line := range strings.Split(body, "\n") {
		if strings.HasPrefix(line, "[") {
			ids = append(ids, line[1:strings.Index(line, "]")])
		}
	}
	env, fit := f.env, "same"
	if env == "none" {
		fit = "none"
	}
	p := Plan{Title: "A test place", Place: "Somewhere in the chapter.", Environment: env, Fit: fit, Why: "Because.", Moment: Range{ids[0], ids[2]}, Mood: "dusk", Fog: 0.1}
	b, _ := json.Marshal(p)
	return string(b), nil
}

func fakeRender(ctx context.Context, root string, e Env, mood string, fog float64, out string) (RenderResult, error) {
	img := image.NewRGBA(image.Rect(0, 0, 640, 400))
	for y := 0; y < 400; y++ {
		for x := 0; x < 640; x++ {
			img.Set(x, y, color.RGBA{90, 80, 70, 255})
		}
	}
	f, _ := os.Create(out)
	defer f.Close()
	png.Encode(f, img)
	return RenderResult{OK: true, Seconds: 0.01, MeanLuma: 0.3}, nil
}

func newTestService(t *testing.T, planner Asker) (*Service, string) {
	root := repoRoot(t)
	tmp := t.TempDir()
	// a scratch root that reads the real books and catalogue but writes its queue to a temp dir
	for _, d := range []string{"content", "schema", "blender"} {
		os.Symlink(filepath.Join(root, d), filepath.Join(tmp, d))
	}
	cat, err := LoadCatalog(tmp)
	if err != nil {
		t.Fatal(err)
	}
	s := NewService(tmp, cat, nil, planner, nil, fakeRender)
	return s, tmp
}

func waitFor(t *testing.T, s *Service, ch string, states ...string) *Job {
	t.Helper()
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		if j := s.Status(ch); j != nil {
			for _, st := range states {
				if j.State == st {
					return j
				}
			}
		}
		time.Sleep(10 * time.Millisecond)
	}
	j := s.Status(ch)
	t.Fatalf("%s never reached %v (now %+v)", ch, states, j)
	return nil
}

func TestLifecycleOneJobPerChapterAndPackage(t *testing.T) {
	fp := &fakePlanner{env: "kansas-farmhouse"}
	s, tmp := newTestService(t, fp)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	for i := 0; i < 3; i++ { // entering the same chapter again does not add a job
		if _, err := s.Prepare("oz", "oz:c01", false); err != nil {
			t.Fatal(err)
		}
	}
	j := waitFor(t, s, "oz:c01", Done)
	if len(fp.prompts) != 1 {
		t.Fatalf("planner called %d times for one chapter, want 1", len(fp.prompts))
	}
	for _, k := range []string{"queueWait", Planning, Rendering, Validating, Packaging, "total"} {
		if _, ok := j.Timings[k]; !ok {
			t.Errorf("timing %s not measured", k)
		}
	}
	data, err := os.ReadFile(filepath.Join(tmp, "out", "chapters", "oz_c01", "package.json"))
	if err != nil {
		t.Fatal(err)
	}
	var p Package
	json.Unmarshal(data, &p)
	if p.UnityScene != "KansasFarmhouse" || p.Thumbnail.SHA256 == "" || p.Mood != "dusk" {
		t.Errorf("package incomplete: %+v", p)
	}
	// a finished chapter is reused, not regenerated
	s.Prepare("oz", "oz:c01", true)
	time.Sleep(100 * time.Millisecond)
	if len(fp.prompts) != 1 || s.Status("oz:c01").State != Done {
		t.Fatalf("a done chapter was regenerated")
	}
}

func TestPlannerSeesNothingAfterTheChapter(t *testing.T) {
	fp := &fakePlanner{env: "kansas-farmhouse"}
	s, tmp := newTestService(t, fp)
	b, _ := books.Load(tmp, "oz")
	ci, _ := chapterIndex(b, "oz:c03")
	prompt := PlanPrompt(b, ci, s.Catalog.ForBook("oz"), s.Catalog.Moods, nil, "")
	last := chapterSentences(b.Chapters[ci])
	if !strings.Contains(prompt, last[len(last)-1]) {
		t.Fatal("the chapter's last sentence is missing from the prompt")
	}
	for _, later := range b.Chapters[ci+1:] {
		for _, id := range chapterSentences(later) {
			if strings.Contains(prompt, id) || strings.Contains(prompt, b.Text(id)) && len(b.Text(id)) > 40 {
				t.Fatalf("the prompt holds %s, from after the chapter", id)
			}
		}
	}
}

func TestCompletedChaptersGoFirstAndRestartResumes(t *testing.T) {
	fp := &fakePlanner{env: "kansas-farmhouse"}
	s, tmp := newTestService(t, fp)
	s.Prepare("oz", "oz:c02", false)
	time.Sleep(5 * time.Millisecond)
	s.Prepare("oz", "oz:c03", false)
	s.Prepare("oz", "oz:c02", true) // the reader finishes chapter 2 while it waits
	s.Prepare("oz", "oz:c04", true)
	if n := s.next(); n.Chapter != "oz:c02" {
		t.Fatalf("next job %s, want the completed, older oz:c02", n.Chapter)
	}
	// simulate a crash mid-pipeline: the job is "planning" on disk
	s.mu.Lock()
	s.jobs["oz:c02"].State = Planning
	s.saveLocked()
	s.mu.Unlock()
	s2 := NewService(tmp, s.Catalog, nil, fp, nil, fakeRender)
	if st := s2.Status("oz:c02"); st == nil || st.State != Queued {
		t.Fatalf("after restart oz:c02 is %+v, want queued again", st)
	}
	if len(s2.jobs) != 3 {
		t.Fatalf("restart kept %d jobs, want 3", len(s2.jobs))
	}
}

func TestNoFittingPlaceIsUnavailableNotSubstituted(t *testing.T) {
	fp := &fakePlanner{env: "none"}
	s, tmp := newTestService(t, fp)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	s.Prepare("oz", "oz:c05", true)
	j := waitFor(t, s, "oz:c05", Unavailable, Done, Failed)
	if j.State != Unavailable {
		t.Fatalf("state %s, want unavailable", j.State)
	}
	if _, err := os.Stat(filepath.Join(tmp, "out", "chapters", "oz_c05", "package.json")); err == nil {
		t.Fatal("a package was built for a chapter with no fitting place")
	}
}

func TestBookWithNoPlacesIsUnavailableWithoutAsking(t *testing.T) {
	fp := &fakePlanner{env: "kansas-farmhouse"}
	s, _ := newTestService(t, fp)
	// every one of Fable's books has places now, so this test takes one book's places out of the loaded catalogue
	// (a book whose rooms are not built yet looks like this): the real books and catalogue stay as they are
	const placeless = "eighty"
	var kept []Env
	for _, e := range s.Catalog.Environments {
		if !containsString(e.Books, placeless) {
			kept = append(kept, e)
		}
	}
	if len(kept) == len(s.Catalog.Environments) {
		t.Fatalf("%s has no places in schema/environments.json to take out", placeless)
	}
	s.Catalog.Environments = kept
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	if _, err := s.Prepare(placeless, placeless+":c01", true); err != nil {
		t.Fatal(err)
	}
	j := waitFor(t, s, placeless+":c01", Unavailable, Done, Failed)
	if j.State != Unavailable || !strings.Contains(j.Error, "no place") {
		t.Fatalf("%s: state %s (%s), want unavailable: no place", placeless, j.State, j.Error)
	}
	fp.mu.Lock()
	defer fp.mu.Unlock()
	if len(fp.prompts) != 0 {
		t.Fatalf("asked Claude %d times for a book with no places", len(fp.prompts))
	}
}

func TestFailureIsRetriedOnRequestAndQueueIsBounded(t *testing.T) {
	fp := &fakePlanner{env: "kansas-farmhouse", fail: true}
	s, _ := newTestService(t, fp)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	s.Prepare("oz", "oz:c01", true)
	j := waitFor(t, s, "oz:c01", Failed)
	if j.Error == "" {
		t.Fatal("a failure without a reason")
	}
	fp.mu.Lock()
	fp.fail = false
	fp.mu.Unlock()
	s.Prepare("oz", "oz:c01", true) // the reader's retry
	waitFor(t, s, "oz:c01", Done)

	cancel()
	time.Sleep(20 * time.Millisecond)
	s.MaxQueue = 3
	var err error
	for i := 2; i <= 6 && err == nil; i++ {
		_, err = s.Prepare("oz", "oz:c0"+string(rune('0'+i)), false)
	}
	if !errors.Is(err, ErrFull) {
		t.Fatalf("queue not bounded: %v", err)
	}
}

// Status answers estimate the wait from this server's recent runs: the seed before any, then the median run, with a
// queued job waiting for the running one and every job ahead of it.
func TestStatusEstimatesTheWait(t *testing.T) {
	s, _ := newTestService(t, &fakePlanner{env: "kansas-farmhouse"})
	s.Prepare("oz", "oz:c02", false)
	time.Sleep(5 * time.Millisecond)
	s.Prepare("oz", "oz:c03", false)
	if st := s.statusFor(s.Status("oz:c02")); st.ETA != SeedRunSeconds {
		t.Fatalf("first in an idle queue with no history: the seed, got %v", st.ETA)
	}
	s.mu.Lock()
	for i, run := range []float64{40, 60, 50} {
		ch := fmt.Sprintf("oz:c%02d", 10+i)
		s.jobs[ch] = &Job{Book: "oz", Chapter: ch, State: Done, Finished: time.Now().Add(time.Duration(i) * time.Second), Timings: map[string]float64{"queueWait": 5, "total": run + 5}}
	}
	j := s.jobs["oz:c02"]
	j.State, j.Started = Rendering, time.Now().Add(-20*time.Second)
	s.mu.Unlock()
	if st := s.statusFor(s.Status("oz:c02")); st.ETA < 29 || st.ETA > 31 {
		t.Fatalf("running for 20 s of a typical 50: about 30 left, got %v", st.ETA)
	}
	if st := s.statusFor(s.Status("oz:c03")); st.ETA < 79 || st.ETA > 81 || st.Position != 2 {
		t.Fatalf("queued behind it: its 30 s and a run of 50, got %v (position %d)", st.ETA, st.Position)
	}
	if st := s.statusFor(s.Status("oz:c10")); st.ETA != 0 {
		t.Fatalf("a built experience has no estimate, got %v", st.ETA)
	}
}

func containsString(xs []string, x string) bool {
	for _, y := range xs {
		if y == x {
			return true
		}
	}
	return false
}

// A book whose places name their chapters: an unnamed chapter is unavailable without asking Claude, and a named one
// is planned among the places that name it only.
func TestNamedChaptersLimitThePlaces(t *testing.T) {
	fp := &fakePlanner{env: "reform-club"}
	s, _ := newTestService(t, fp)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	// (a chapter after the tenth: the scene-room plan covers the first ten)
	s.Prepare("eighty", "eighty:c20", true)
	j := waitFor(t, s, "eighty:c20", Unavailable, Done, Failed)
	if j.State != Unavailable || !strings.Contains(j.Error, "no place") {
		t.Fatalf("eighty:c20: state %s (%s), want unavailable: no place", j.State, j.Error)
	}
	fp.mu.Lock()
	asked := len(fp.prompts)
	fp.mu.Unlock()
	if asked != 0 {
		t.Fatalf("asked Claude %d times for a chapter no place names", asked)
	}
	s.Prepare("eighty", "eighty:c03", true)
	j = waitFor(t, s, "eighty:c03", Done, Failed, Unavailable)
	if j.State != Done {
		t.Fatalf("eighty:c03: state %s (%s), want done", j.State, j.Error)
	}
	fp.mu.Lock()
	defer fp.mu.Unlock()
	if len(fp.prompts) == 0 || !strings.Contains(fp.prompts[0], "reform-club") || strings.Contains(fp.prompts[0], "mongolia-deck") {
		t.Fatal("the plan for chapter 3 was not limited to the Reform Club")
	}
}

// The scene-room plan decides the first ten chapters: a chapter whose new room is not published waits for it
// without asking Claude; once the room is published as a download environment, the package names its zip and
// the thumbnail is the room's own view.
func TestPlannedSceneRoomIsDownloadedOncePublished(t *testing.T) {
	root := repoRoot(t)
	tmp := t.TempDir()
	os.Symlink(filepath.Join(root, "blender"), filepath.Join(tmp, "blender"))
	os.MkdirAll(filepath.Join(tmp, "content"), 0o755)
	ents, _ := os.ReadDir(filepath.Join(root, "content"))
	for _, e := range ents {
		if e.Name() != "scene-rooms" {
			os.Symlink(filepath.Join(root, "content", e.Name()), filepath.Join(tmp, "content", e.Name()))
		}
	}
	os.MkdirAll(filepath.Join(tmp, "schema"), 0o755)
	for _, f := range []string{"scene_rooms.json", "environments.json"} {
		b, _ := os.ReadFile(filepath.Join(root, "schema", f))
		os.WriteFile(filepath.Join(tmp, "schema", f), b, 0o644)
	}
	cat, err := LoadCatalog(tmp)
	if err != nil {
		t.Fatal(err)
	}
	pl, ok := cat.Planned("treasure:c01")
	if !ok || pl.Existing != "" {
		t.Fatalf("treasure:c01 should be planned for a new room, got %+v", pl)
	}
	fp := &fakePlanner{env: "sr-" + pl.ID}
	s := NewService(tmp, cat, nil, fp, nil, func(ctx context.Context, root string, e Env, mood string, fog float64, out string) (RenderResult, error) {
		t.Errorf("a scene room was rendered in Blender (%s)", e.ID)
		return fakeRender(ctx, root, e, mood, fog, out)
	})
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	s.Prepare("treasure", "treasure:c01", true)
	j := waitFor(t, s, "treasure:c01", Unavailable, Done, Failed)
	if j.State != Unavailable || !strings.Contains(j.Error, "still being built") || len(fp.prompts) != 0 {
		t.Fatalf("unpublished: %s (%s), %d prompts", j.State, j.Error, len(fp.prompts))
	}
	// publish it
	dir := filepath.Join(tmp, "content", "scene-rooms", pl.ID)
	os.MkdirAll(dir, 0o755)
	sha := strings.Repeat("cd", 32)
	os.WriteFile(filepath.Join(dir, "manifest.json"), []byte(`{"id":"`+pl.ID+`","version":"cdcdcdcd","zip":"room-cdcdcdcd.zip","bytes":4,"sha256":"`+sha+`","view":"view.jpg"}`), 0o644)
	os.WriteFile(filepath.Join(dir, "room-cdcdcdcd.zip"), []byte("PK.."), 0o644)
	vf, _ := os.Create(filepath.Join(dir, "view.jpg"))
	img := image.NewRGBA(image.Rect(0, 0, 640, 360))
	for i := range img.Pix {
		img.Pix[i] = 110
	}
	png.Encode(vf, img)
	vf.Close()
	cat.Environments = append(cat.Environments, Env{ID: "sr-" + pl.ID, UnityScene: "LibraryRoom", Staging: "place", Books: []string{"treasure"}, Place: pl.Name,
		Triangles: 30000, Meshes: 20, Chapters: pl.Chapters, Delivery: "download", SceneRoom: pl.ID})
	s.Prepare("treasure", "treasure:c01", true)
	j = waitFor(t, s, "treasure:c01", Done, Failed)
	if j.State != Done {
		t.Fatalf("published: %s (%s)", j.State, j.Error)
	}
	var p Package
	b, _ := os.ReadFile(filepath.Join(s.pkgDir("treasure:c01"), "package.json"))
	json.Unmarshal(b, &p)
	if p.SceneRoom == nil || p.SceneRoom.SHA256 != sha || p.SceneRoom.File != "room-cdcdcdcd.zip" || p.UnityScene != "LibraryRoom" {
		t.Fatalf("package scene room: %+v (%s)", p.SceneRoom, p.UnityScene)
	}
	// republished: the package served points at the new zip
	sha2 := strings.Repeat("ef", 32)
	os.WriteFile(filepath.Join(dir, "room-efefefef.zip"), []byte("PK.."), 0o644)
	os.WriteFile(filepath.Join(dir, "manifest.json"), []byte(`{"id":"`+pl.ID+`","version":"efefefef","zip":"room-efefefef.zip","bytes":4,"sha256":"`+sha2+`","view":"view.jpg"}`), 0o644)
	mux := http.NewServeMux()
	s.Register(mux)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, httptest.NewRequest("GET", "/chapters/package?chapter=treasure:c01", nil))
	var served Package
	if json.Unmarshal(rec.Body.Bytes(), &served) != nil || served.SceneRoom == nil || served.SceneRoom.SHA256 != sha2 {
		t.Fatalf("republished room not served: %d %s", rec.Code, rec.Body.String())
	}
}
