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

	"github.com/Thabhelo/fable/interpreter/internal/books"
	"github.com/Thabhelo/fable/interpreter/internal/mock"
)

type fakePeeker struct{ calls int }

func (f *fakePeeker) Peek(ctx context.Context, b *books.Book, sid, phrase string) (*mock.Model, []string, error) {
	f.calls++
	m := &mock.Model{Version: 1, Title: "the golden key", Book: b.Slug, Phrase: phrase, SentenceID: sid, HeightMetres: 0.2, Source: "clay",
		Parts:  []mock.Part{{ID: "shaft", Shape: "cylinder", Size: []float64{0.4, 4, 0.4}, Color: "#d4a832"}, {ID: "bow", Shape: "torus", Size: []float64{2, 0.4, 2}, Color: "#d4a832"}},
		Labels: []mock.Label{{Text: "golden", Part: "bow"}, {Text: "small", Part: "shaft"}}}
	return m, []string{"{}"}, nil
}

func peekReq(t *testing.T, h http.Handler, sid string) *httptest.ResponseRecorder {
	body, _ := json.Marshal(peekRequest{Book: "alice", SentenceID: sid, Phrase: "Golden key", WaitSeconds: 5})
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, httptest.NewRequest("POST", "/peek", bytes.NewReader(body)))
	return rr
}

// A model made from text further on must never reach a reader who has not got there; one made earlier may.
func TestPeekCacheIsSpoilerSafe(t *testing.T) {
	root := t.TempDir()
	// the server reads books from <root>/content/books: point it at the repo's copy
	if err := linkBooks(root); err != nil {
		t.Fatal(err)
	}
	fp := &fakePeeker{}
	s := New(root, nil, nil)
	s.Peeker = fp
	s.DefaultWait = 5 * time.Second
	h := s.Handler()
	b, _ := books.Load(root, "alice")
	later := b.Find("little golden key", "")
	earlier := b.Find("rabbit-hole", "") // chapter one, well before the key
	if later == "" || earlier == "" || b.Ordinal(earlier) >= b.Ordinal(later) {
		t.Fatalf("fixture sentences: %q %q", earlier, later)
	}
	if rr := peekReq(t, h, later); rr.Code != 200 || rr.Header().Get("X-Fable-Cache") != "miss" {
		t.Fatalf("first: %d %s %s", rr.Code, rr.Header().Get("X-Fable-Cache"), rr.Body)
	}
	if rr := peekReq(t, h, later); rr.Header().Get("X-Fable-Cache") != "hit" || fp.calls != 1 {
		t.Fatalf("same place should hit the cache: %s calls=%d", rr.Header().Get("X-Fable-Cache"), fp.calls)
	}
	if rr := peekReq(t, h, earlier); rr.Header().Get("X-Fable-Cache") == "hit" || fp.calls != 2 {
		t.Fatalf("a reader earlier in the book got the later model: %s calls=%d", rr.Header().Get("X-Fable-Cache"), fp.calls)
	}
	// a reader further on than both may use the latest one made at or before them
	further := b.Find("Drink me", "")
	if rr := peekReq(t, h, further); rr.Header().Get("X-Fable-Cache") != "hit" {
		t.Fatalf("further on should reuse: %s", rr.Header().Get("X-Fable-Cache"))
	}
	var m mock.Model
	json.Unmarshal(peekReq(t, h, further).Body.Bytes(), &m)
	if m.SentenceID != later {
		t.Fatalf("served the model from %s, want the latest at or before the reader (%s)", m.SentenceID, later)
	}
}

func linkBooks(root string) error {
	abs, err := filepath.Abs("../../../content")
	if err != nil {
		return err
	}
	return os.Symlink(abs, filepath.Join(root, "content"))
}
