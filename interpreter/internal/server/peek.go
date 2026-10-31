package server

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/Thabhelo/fable/interpreter/internal/books"
	"github.com/Thabhelo/fable/interpreter/internal/llm"
	"github.com/Thabhelo/fable/interpreter/internal/mock"
)

// Peeker is what llm.Director implements for Peek; tests substitute a fake.
type Peeker interface {
	Peek(ctx context.Context, b *books.Book, sentenceID, phrase string) (*mock.Model, []string, error)
}

// peeks holds the whole books and the Peek generator. Kept apart from the scene interpreter's state.
type peeks struct {
	once  sync.Once
	books map[string]*books.Book
	err   error
	mu    sync.Mutex
	jobs  map[string]*peekJob
}

type peekJob struct {
	done chan struct{}
	data []byte
	err  error
}

type peekRequest struct {
	Book        string  `json:"book"`
	SentenceID  string  `json:"sentenceId"` // the last sentence of the highlight
	Phrase      string  `json:"phrase"`
	NoCache     bool    `json:"noCache"`
	WaitSeconds float64 `json:"waitSeconds"`
}

func (s *Server) book(slug string) (*books.Book, error) {
	s.peek.once.Do(func() {
		s.peek.books = map[string]*books.Book{}
		for _, sl := range books.Slugs {
			b, err := books.Load(s.Root, sl)
			if err != nil {
				s.peek.err = err
				return
			}
			s.peek.books[sl] = b
		}
	})
	if s.peek.err != nil {
		return nil, s.peek.err
	}
	b, ok := s.peek.books[slug]
	if !ok {
		return nil, fmt.Errorf("book %q is not one of %s", slug, strings.Join(books.Slugs, ", "))
	}
	return b, nil
}

// NormalisePhrase is the cache key's form of a highlight: lower case, single spaces, no edge punctuation.
func NormalisePhrase(p string) string {
	p = strings.ToLower(strings.Join(strings.Fields(p), " "))
	return strings.Trim(p, " .,;:!?\"'“”‘’()—-")
}

func (s *Server) peekDir(slug, phrase string) string {
	h := sha256.Sum256([]byte(NormalisePhrase(phrase)))
	return filepath.Join(s.Root, "out", "cache", "peek", slug, hex.EncodeToString(h[:8]))
}

// cachedPeek returns the model generated for this phrase from the most text that does not go past the reader's
// highlight. A model made from further on in the book is never served to a reader who has not got there.
func (s *Server) cachedPeek(b *books.Book, sentenceID, phrase string) []byte {
	at := b.Ordinal(sentenceID)
	ents, _ := os.ReadDir(s.peekDir(b.Slug, phrase))
	type cand struct {
		ord  int
		path string
	}
	var cands []cand
	for _, e := range ents {
		id := strings.TrimSuffix(e.Name(), ".json")
		if o := b.Ordinal(id); o >= 0 && o <= at {
			cands = append(cands, cand{o, filepath.Join(s.peekDir(b.Slug, phrase), e.Name())})
		}
	}
	sort.Slice(cands, func(i, j int) bool { return cands[i].ord > cands[j].ord })
	for _, c := range cands {
		data, err := os.ReadFile(c.path)
		if err != nil {
			continue
		}
		if m, err := mock.Parse(data); err == nil && len(mock.Validate(m, "")) == 0 {
			return data
		}
	}
	return nil
}

func (s *Server) handlePeek(w http.ResponseWriter, r *http.Request) {
	var req peekRequest
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<14)).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	b, err := s.book(req.Book)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}
	if b.Ordinal(req.SentenceID) < 0 {
		http.Error(w, fmt.Sprintf("sentence %q is not in %s", req.SentenceID, req.Book), http.StatusNotFound)
		return
	}
	if NormalisePhrase(req.Phrase) == "" || len(req.Phrase) > 120 {
		http.Error(w, "phrase must be 1-120 characters", http.StatusBadRequest)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	if !req.NoCache {
		if data := s.cachedPeek(b, req.SentenceID, req.Phrase); data != nil {
			w.Header().Set("X-Fable-Cache", "hit")
			w.Write(data)
			return
		}
	}
	if s.Peeker == nil {
		http.Error(w, "no Peek generator configured", http.StatusServiceUnavailable)
		return
	}
	key := req.Book + "|" + req.SentenceID + "|" + NormalisePhrase(req.Phrase)
	s.peek.mu.Lock()
	if s.peek.jobs == nil {
		s.peek.jobs = map[string]*peekJob{}
	}
	j, ok := s.peek.jobs[key]
	if !ok {
		j = &peekJob{done: make(chan struct{})}
		s.peek.jobs[key] = j
		go s.runPeek(key, j, b, req.SentenceID, req.Phrase)
	}
	s.peek.mu.Unlock()
	wait := s.DefaultWait
	if req.WaitSeconds > 0 {
		wait = time.Duration(req.WaitSeconds * float64(time.Second))
	}
	if wait > s.MaxWait {
		wait = s.MaxWait
	}
	timer := time.NewTimer(wait)
	defer timer.Stop()
	select {
	case <-j.done:
		if j.err != nil {
			http.Error(w, j.err.Error(), http.StatusBadGateway)
			return
		}
		w.Header().Set("X-Fable-Cache", "miss")
		w.Write(j.data)
	case <-timer.C:
		w.WriteHeader(http.StatusAccepted)
		fmt.Fprintf(w, `{"status":"generating"}`)
	}
}

func (s *Server) runPeek(key string, j *peekJob, b *books.Book, sentenceID, phrase string) {
	defer func() {
		close(j.done)
		s.peek.mu.Lock()
		delete(s.peek.jobs, key) // the result is on disk now (or failed); the next request reads the cache or retries
		s.peek.mu.Unlock()
	}()
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	t0 := time.Now()
	m, attempts, err := s.Peeker.Peek(ctx, b, sentenceID, phrase)
	if err == nil {
		read, _ := b.TextUpTo(sentenceID, 7000)
		if errs := mock.Validate(m, read); len(errs) > 0 {
			err = fmt.Errorf("model failed server-side validation: %v", errs)
		}
	}
	if err != nil {
		log.Printf("peek %s: failed after %d attempt(s) in %s: %v", key, len(attempts), time.Since(t0).Round(time.Millisecond), err)
		j.err = err
		return
	}
	j.data = llm.MarshalModel(m)
	dir := s.peekDir(b.Slug, phrase)
	if err := os.MkdirAll(dir, 0o755); err == nil {
		os.WriteFile(filepath.Join(dir, sentenceID+".json"), j.data, 0o644)
	}
	log.Printf("peek %s: %d parts, %d triangles, %d attempt(s), %s", key, len(m.Parts), m.TriangleCount(), len(attempts), time.Since(t0).Round(time.Millisecond))
}
