package rooms

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

func repoRoot() string {
	wd, _ := os.Getwd()
	return filepath.Clean(filepath.Join(wd, "..", "..", ".."))
}

// fakeClaude plans three places and writes a script; it records every prompt.
type fakeClaude struct {
	mu      sync.Mutex
	prompts []string
	places  int
}

func (f *fakeClaude) Ask(ctx context.Context, system, user string, max int64) (string, error) {
	f.mu.Lock()
	f.prompts = append(f.prompts, user)
	f.mu.Unlock()
	if strings.Contains(system, "You choose reading rooms") {
		var st []Setting
		for i := 0; i < f.places; i++ {
			st = append(st, Setting{Title: "Place " + string(rune('A'+i)), Place: "a place", Kind: "exterior"})
		}
		b, _ := json.Marshal(map[string]any{"settings": st})
		return string(b), nil
	}
	return "Here it is.\n```python\nkit.sky((0.4,0.5,0.7),(0.8,0.8,0.7))\n```", nil
}

func testBook() *Book {
	b := &Book{Slug: "u-test", Title: "A Test", Author: "Someone"}
	for i := 1; i <= 9; i++ {
		b.Chapters = append(b.Chapters, Chapter{ID: "c0" + string(rune('0'+i)), Title: "Chapter", Text: strings.Repeat("opening words ", 300) + "SECRET" + string(rune('0'+i))})
	}
	return b
}

func fakeBuild(fails int) (Builder, *int) {
	calls := 0
	return func(ctx context.Context, root, script, out string) (BuildResult, error) {
		calls++
		if calls <= fails {
			return BuildResult{OK: false, Problems: []string{"no reader position"}}, nil
		}
		os.MkdirAll(filepath.Join(out, "textures"), 0o755)
		os.MkdirAll(filepath.Join(out, "views"), 0o755)
		for _, f := range []string{"room.gltf", "room.bin", "textures/T_a.jpg", "views/thumb.png"} {
			os.WriteFile(filepath.Join(out, f), []byte("x"), 0o644)
		}
		return BuildResult{OK: true, Triangles: 1000, Entrance: []float64{0, 0, 0}, Look: []float64{0, 5, 1.5}}, nil
	}, &calls
}

func newSvc(t *testing.T, fc *fakeClaude, b Builder) *Service {
	tmp := t.TempDir()
	os.Symlink(filepath.Join(repoRoot(), "blender"), filepath.Join(tmp, "blender"))
	return NewService(tmp, fc, b)
}

func wait(t *testing.T, s *Service, book string, room int, states ...string) statusOut {
	t.Helper()
	end := time.Now().Add(5 * time.Second)
	for time.Now().Before(end) {
		for _, st := range s.Status(book) {
			if st.Room == room {
				for _, want := range states {
					if st.State == want {
						return st
					}
				}
			}
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("room %d never reached %v: %+v", room, states, s.Status(book))
	return statusOut{}
}

func TestThreeRoomsOnePlanPackagedWithChecksums(t *testing.T) {
	fc := &fakeClaude{places: 3}
	b, _ := fakeBuild(0)
	s := newSvc(t, fc, b)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	s.Prepare(testBook())
	s.Prepare(testBook()) // again: no new jobs
	for n := 1; n <= 3; n++ {
		wait(t, s, "u-test", n, Done)
	}
	plans := 0
	for _, p := range fc.prompts {
		if strings.Contains(p, "THE OPENING") {
			plans++
		}
	}
	if plans != 1 {
		t.Fatalf("planned %d times, want once per book", plans)
	}
	data, err := os.ReadFile(filepath.Join(s.pkgDir("u-test", 2), "package.json"))
	if err != nil {
		t.Fatal(err)
	}
	var m struct {
		Title string `json:"title"`
		Files []struct{ Path, SHA256 string }
	}
	json.Unmarshal(data, &m)
	if m.Title != "Place B" || len(m.Files) != 4 || m.Files[0].SHA256 == "" {
		t.Fatalf("package incomplete: %s", data)
	}
}

func TestPlannerSeesOnlyTheOpening(t *testing.T) {
	o := Opening(testBook(), 90000)
	if !strings.Contains(o, "SECRET1") {
		t.Fatal("the first chapter is missing")
	}
	for _, later := range []string{"SECRET5", "SECRET9"} {
		if strings.Contains(o, later) {
			t.Fatalf("the opening includes %s, from later in the book", later)
		}
	}
}

func TestRejectedScriptIsRepairedWithTheProblems(t *testing.T) {
	fc := &fakeClaude{places: 1}
	b, calls := fakeBuild(1)
	s := newSvc(t, fc, b)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	s.Prepare(testBook())
	wait(t, s, "u-test", 1, Done)
	if *calls != 2 {
		t.Fatalf("built %d times, want 2 (one rejected, one repaired)", *calls)
	}
	repaired := false
	for _, p := range fc.prompts {
		if strings.Contains(p, "rejected by the checks") && strings.Contains(p, "no reader position") {
			repaired = true
		}
	}
	if !repaired {
		t.Fatal("the problems were not sent back")
	}
	// a book with one place: the other rooms say so instead of failing or repeating the place
	wait(t, s, "u-test", 2, Unavail)
	wait(t, s, "u-test", 3, Unavail)
}

func TestBadIDsAndRestartResume(t *testing.T) {
	fc := &fakeClaude{places: 3}
	b, _ := fakeBuild(0)
	s := newSvc(t, fc, b)
	if _, err := s.Prepare(&Book{Slug: "../etc", Chapters: []Chapter{{Text: "x"}}}); err == nil {
		t.Fatal("a path-like book id was accepted")
	}
	s.Prepare(testBook())
	s.mu.Lock()
	s.jobs["u-test:r1"].State = Building
	s.saveLocked()
	s.mu.Unlock()
	s2 := NewService(s.Root, fc, b)
	if st := s2.Status("u-test"); len(st) != 3 || st[0].State != Queued {
		t.Fatalf("after a restart: %+v", st)
	}
	s2.MaxBooks = 1
	other := testBook()
	other.Slug = "u-other"
	if _, err := s2.Prepare(other); !errors.Is(err, ErrFull) {
		t.Fatalf("queue not bounded: %v", err)
	}
}

func TestKitAPIListsTheKit(t *testing.T) {
	src, _ := os.ReadFile(filepath.Join(repoRoot(), "blender", "roomkit.py"))
	api := KitAPI(string(src))
	for _, fn := range []string{"kit.terrain(", "kit.room(", "kit.reader(", "kit.sky(", "kit.groundcover("} {
		if !strings.Contains(api, fn) {
			t.Fatalf("the API given to Claude lacks %s", fn)
		}
	}
}
