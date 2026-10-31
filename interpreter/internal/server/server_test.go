package server

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/Thabhelo/fable/interpreter/internal/book"
	"github.com/Thabhelo/fable/interpreter/internal/script"
)

// fake answers with the hall baseline after a delay, or fails.
type fake struct {
	delay time.Duration
	fail  bool
	calls int
}

func (f *fake) Interpret(ctx context.Context, sc *book.Scene, m *script.Manifest, pos string) (*script.SceneScript, []string, error) {
	f.calls++
	select {
	case <-time.After(f.delay):
	case <-ctx.Done():
		return nil, nil, ctx.Err()
	}
	if f.fail {
		return nil, []string{"garbage"}, context.DeadlineExceeded
	}
	data, err := os.ReadFile("../../../scripts/hall-of-doors.baseline.json")
	if err != nil {
		return nil, nil, err
	}
	s, err := script.Parse(data)
	return s, []string{string(data)}, err
}

// newServer points Root at a temp copy of schema/ and book/ so the cache lands in a scratch dir.
func newServer(t *testing.T, f *fake) *Server {
	t.Helper()
	root := t.TempDir()
	for _, d := range []string{"schema", "book"} {
		os.MkdirAll(filepath.Join(root, d), 0o755)
		entries, _ := os.ReadDir(filepath.Join("../../..", d))
		for _, e := range entries {
			b, _ := os.ReadFile(filepath.Join("../../..", d, e.Name()))
			os.WriteFile(filepath.Join(root, d, e.Name()), b, 0o644)
		}
	}
	bk, err := book.Load(filepath.Join(root, "book", "passages.json"))
	if err != nil {
		t.Fatal(err)
	}
	s := New(root, bk, f)
	s.DefaultWait = 50 * time.Millisecond
	return s
}

func post(t *testing.T, h http.Handler, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest("POST", "/interpret", bytes.NewBufferString(body))
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	return rr
}

func TestSlowGenerationSurvivesTheClient(t *testing.T) {
	f := &fake{delay: 200 * time.Millisecond}
	s := newServer(t, f)
	h := s.Handler()

	rr := post(t, h, `{"sceneId":"hall-of-doors","readingPosition":"hall-of-doors:003"}`)
	if rr.Code != http.StatusAccepted || rr.Header().Get("X-Fable-Cache") != "pending" {
		t.Fatalf("first call: want 202 pending, got %d %q", rr.Code, rr.Header().Get("X-Fable-Cache"))
	}
	// a second impatient client joins the same job instead of starting another
	post(t, h, `{"sceneId":"hall-of-doors"}`)
	if f.calls != 1 {
		t.Fatalf("single-flight broken: %d generations", f.calls)
	}
	// a patient client waits and gets the fresh script
	rr = post(t, h, `{"sceneId":"hall-of-doors","waitSeconds":2}`)
	if rr.Code != 200 || rr.Header().Get("X-Fable-Cache") != "miss" {
		t.Fatalf("patient call: want 200 miss, got %d %q %s", rr.Code, rr.Header().Get("X-Fable-Cache"), rr.Body.String())
	}
	var out script.SceneScript
	if err := json.Unmarshal(rr.Body.Bytes(), &out); err != nil || len(out.Beats) == 0 {
		t.Fatalf("body is not a script: %v", err)
	}
	// and from now on the cache answers instantly
	rr = post(t, h, `{"sceneId":"hall-of-doors"}`)
	if rr.Code != 200 || rr.Header().Get("X-Fable-Cache") != "hit" {
		t.Fatalf("cached call: want 200 hit, got %d %q", rr.Code, rr.Header().Get("X-Fable-Cache"))
	}
	if f.calls != 1 {
		t.Fatalf("cache ignored: %d generations", f.calls)
	}
}

func TestFailureIsReportedAndRetried(t *testing.T) {
	f := &fake{fail: true}
	s := newServer(t, f)
	h := s.Handler()
	rr := post(t, h, `{"sceneId":"hall-of-doors","waitSeconds":2}`)
	if rr.Code != http.StatusBadGateway {
		t.Fatalf("want 502, got %d %s", rr.Code, rr.Body.String())
	}
	rr = post(t, h, `{"sceneId":"hall-of-doors","waitSeconds":2}`)
	if rr.Code != http.StatusBadGateway || f.calls != 2 {
		t.Fatalf("failed job should be retried: code %d, calls %d", rr.Code, f.calls)
	}
	if _, err := os.Stat(s.cachePath("hall-of-doors")); err == nil {
		t.Fatal("a failed generation must not be cached")
	}
}

func TestUnknownSceneAndBadBody(t *testing.T) {
	s := newServer(t, &fake{})
	h := s.Handler()
	if rr := post(t, h, `{"sceneId":"cheshire-cat"}`); rr.Code != 404 {
		t.Fatalf("want 404, got %d", rr.Code)
	}
	if rr := post(t, h, `not json`); rr.Code != 400 {
		t.Fatalf("want 400, got %d", rr.Code)
	}
	req := httptest.NewRequest("GET", "/jobs", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != 200 {
		t.Fatalf("jobs: %d", rr.Code)
	}
}
