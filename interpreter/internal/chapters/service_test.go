package chapters

import (
	"context"
	"encoding/json"
	"errors"
	"image"
	"image/color"
	"image/png"
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
