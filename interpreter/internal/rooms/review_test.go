package rooms

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/Thabhelo/fable/interpreter/internal/llm"
)

// reviewer is fakeClaude that can also look at pictures: it asks for one revision, then approves.
type reviewer struct {
	fakeClaude
	rmu     sync.Mutex
	reviews int
	images  int
}

func (r *reviewer) AskImagesRaw(ctx context.Context, system, user string, images []llm.Image, max int64) (string, string, error) {
	r.rmu.Lock()
	defer r.rmu.Unlock()
	r.reviews++
	r.images += len(images)
	if r.reviews == 1 {
		return "CRITIQUE:\n- the hedge is a blob (view 2)\nVERDICT: REVISE\n```python\nkit.sky((0.4,0.5,0.7),(0.8,0.8,0.7))\n# revised\n```", "end_turn", nil
	}
	return "CRITIQUE:\n- fine\nVERDICT: GOOD", "end_turn", nil
}

// previewBuild is fakeBuild that also writes the headset-look previews the review needs; builds whose script
// contains failMark fail their checks.
func previewBuild(failMark string) (Builder, *[]string) {
	var scripts []string
	return func(ctx context.Context, root, script, out string) (BuildResult, error) {
		src, _ := os.ReadFile(script)
		scripts = append(scripts, string(src))
		if failMark != "" && strings.Contains(string(src), failMark) {
			return BuildResult{OK: false, Problems: []string{"too dark"}}, nil
		}
		for _, d := range []string{"textures", "views", "preview"} {
			os.MkdirAll(filepath.Join(out, d), 0o755)
		}
		for _, f := range []string{"room.gltf", "room.bin", "textures/T_a.jpg", "views/thumb.png"} {
			os.WriteFile(filepath.Join(out, f), src, 0o644)
		}
		for _, v := range reviewViews {
			os.WriteFile(filepath.Join(out, "preview", v.File), []byte("png"), 0o644)
		}
		return BuildResult{OK: true, Triangles: 1000 + len(scripts), Entrance: []float64{0, 0, 0}, Look: []float64{0, 5, 1.5}}, nil
	}, &scripts
}

func TestReviewRevisesThenApprovesAndPackagesTheRevision(t *testing.T) {
	rc := &reviewer{fakeClaude: fakeClaude{places: 1}}
	b, scripts := previewBuild("")
	tmp := t.TempDir()
	os.Symlink(filepath.Join(repoRoot(), "blender"), filepath.Join(tmp, "blender"))
	s := NewService(tmp, rc, b)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	s.Prepare(testBook())
	wait(t, s, "u-test", 1, Done)
	if rc.reviews != 2 || rc.images != 2*len(reviewViews) {
		t.Fatalf("reviews %d images %d, want 2 reviews of %d views", rc.reviews, rc.images, len(reviewViews))
	}
	if len(*scripts) != 2 {
		t.Fatalf("built %d times, want the first script and one revision", len(*scripts))
	}
	gl, _ := os.ReadFile(filepath.Join(s.pkgDir("u-test", 1), "room.gltf"))
	if !strings.Contains(string(gl), "# revised") {
		t.Fatal("the package is not the revised room")
	}
}

func TestFailedRevisionKeepsTheRoomThatPassed(t *testing.T) {
	rc := &reviewer{fakeClaude: fakeClaude{places: 1}}
	b, _ := previewBuild("# revised")
	tmp := t.TempDir()
	os.Symlink(filepath.Join(repoRoot(), "blender"), filepath.Join(tmp, "blender"))
	s := NewService(tmp, rc, b)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go s.Run(ctx)
	s.Prepare(testBook())
	wait(t, s, "u-test", 1, Done)
	gl, _ := os.ReadFile(filepath.Join(s.pkgDir("u-test", 1), "room.gltf"))
	if strings.Contains(string(gl), "# revised") || len(gl) == 0 {
		t.Fatal("a revision that failed its checks replaced the room")
	}
}
