// Package server is the HTTP face of the interpreter. Generation runs detached from the
// request that asked for it: a headset that gives up after a few seconds must not cancel a
// 40-second Claude call, or the cache would never fill and the live path could never be seen.
// Each scene has at most one generation in flight (single-flight); callers wait a bounded time
// and otherwise get 202 and come back later.
package server

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"sync"
	"time"

	"github.com/Thabhelo/fable/interpreter/internal/book"
	"github.com/Thabhelo/fable/interpreter/internal/llm"
	"github.com/Thabhelo/fable/interpreter/internal/script"
)

// Interpreter is what llm.Director implements; tests substitute a fake.
type Interpreter interface {
	Interpret(ctx context.Context, sc *book.Scene, m *script.Manifest, readingPosition string, variant int) (*script.SceneScript, []string, error)
}

type job struct {
	scene    string
	variant  int
	position string
	started  time.Time
	done     chan struct{}
	script   []byte // validated, indented JSON
	err      error
	attempts int
}

type Server struct {
	Root        string // repo root: schema/, book/, out/cache
	Book        *book.Book
	Interp      Interpreter
	GenTimeout  time.Duration // per generation; default 8 min
	DefaultWait time.Duration // how long a request waits for a fresh script before 202; default 3 s
	MaxWait     time.Duration // cap on the client's waitSeconds; default 120 s
	Model       string
	Peeker      Peeker                                // Peek clay models; nil answers 503 unless the cache has one
	Chapters    interface{ Register(*http.ServeMux) } // chapter experiences (internal/chapters); nil = off
	Rooms       interface{ Register(*http.ServeMux) } // generated reading rooms for uploaded books (internal/rooms); nil = off

	peek peeks
	mu   sync.Mutex
	jobs map[string]*job
}

func New(root string, bk *book.Book, in Interpreter) *Server {
	return &Server{Root: root, Book: bk, Interp: in, GenTimeout: 8 * time.Minute, DefaultWait: 3 * time.Second, MaxWait: 120 * time.Second, jobs: map[string]*job{}}
}

func (s *Server) manifest(sceneID string) (*script.Manifest, error) {
	data, err := os.ReadFile(filepath.Join(s.Root, "schema", "manifest."+sceneID+".json"))
	if err != nil {
		return nil, err
	}
	var m script.Manifest
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, err
	}
	return &m, nil
}

// cachePath keeps variant 0 at the old name so existing caches stay valid.
func (s *Server) cachePath(sceneID string, variant int) string {
	if variant <= 0 {
		return filepath.Join(s.Root, "out", "cache", sceneID+".json")
	}
	return filepath.Join(s.Root, "out", "cache", fmt.Sprintf("%s.v%d.json", sceneID, variant))
}

func jobKey(sceneID string, variant int) string { return fmt.Sprintf("%s#%d", sceneID, variant) }

// cached returns the on-disk script if it still validates against today's manifest and passage.
func (s *Server) cached(sceneID string, variant int, m *script.Manifest, sc *book.Scene) []byte {
	data, err := os.ReadFile(s.cachePath(sceneID, variant))
	if err != nil {
		return nil
	}
	cs, err := script.Parse(data)
	if err != nil || len(script.Validate(cs, m, sc.SentenceIDs())) > 0 {
		return nil
	}
	return data
}

// ensureJob returns the running generation for a scene, starting one if none is in flight.
func (s *Server) ensureJob(sceneID string, variant int, position string, sc *book.Scene, m *script.Manifest) (*job, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	key := jobKey(sceneID, variant)
	if j, ok := s.jobs[key]; ok {
		return j, false
	}
	j := &job{scene: sceneID, variant: variant, position: position, started: time.Now(), done: make(chan struct{})}
	s.jobs[key] = j
	go s.run(j, sc, m)
	return j, true
}

func (s *Server) run(j *job, sc *book.Scene, m *script.Manifest) {
	ctx, cancel := context.WithTimeout(context.Background(), s.GenTimeout)
	defer cancel()
	log.Printf("interpret %s v%d: generating (position %q)", j.scene, j.variant, j.position)
	out, attempts, err := s.Interp.Interpret(ctx, sc, m, j.position, j.variant)
	j.attempts = len(attempts)
	if err == nil {
		// the interpreter validated already; validate again here so the cache can never hold a bad script
		if errs := script.Validate(out, m, sc.SentenceIDs()); len(errs) > 0 {
			err = fmt.Errorf("script failed server-side validation: %v", errs)
		}
	}
	if err != nil {
		j.err = err
		log.Printf("interpret %s: failed after %s, %d attempt(s): %v", j.scene, time.Since(j.started).Round(time.Millisecond), j.attempts, err)
	} else {
		js, _ := json.MarshalIndent(out, "", "  ")
		p := s.cachePath(j.scene, j.variant)
		os.MkdirAll(filepath.Dir(p), 0o755)
		if werr := os.WriteFile(p, js, 0o644); werr != nil {
			log.Printf("interpret %s: cache write failed: %v", j.scene, werr)
		}
		j.script = js
		log.Printf("interpret %s: %d beats in %s, %d attempt(s)", j.scene, len(out.Beats), time.Since(j.started).Round(time.Millisecond), j.attempts)
	}
	close(j.done)
	// a failed job is forgotten so the next request retries; a successful one is served from the cache
	s.mu.Lock()
	if s.jobs[jobKey(j.scene, j.variant)] == j {
		delete(s.jobs, jobKey(j.scene, j.variant))
	}
	s.mu.Unlock()
}

type interpretRequest struct {
	SceneID         string  `json:"sceneId"`
	ReadingPosition string  `json:"readingPosition"` // sentence id the reader has reached
	NoCache         bool    `json:"noCache"`
	WaitSeconds     float64 `json:"waitSeconds"` // 0 = server default
	Variant         int     `json:"variant"`     // 0 = the plain reading; 1.. = alternative readings of the same passage
}

type pending struct {
	Status         string  `json:"status"`
	SceneID        string  `json:"sceneId"`
	Variant        int     `json:"variant"`
	ElapsedSeconds float64 `json:"elapsedSeconds"`
	RetryAfter     int     `json:"retryAfterSeconds"`
}

func (s *Server) handleInterpret(w http.ResponseWriter, r *http.Request) {
	var req interpretRequest
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<16)).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	sc, err := s.Book.Scene(req.SceneID)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}
	m, err := s.manifest(req.SceneID)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}
	if req.Variant < 0 || req.Variant >= s.Variants() {
		http.Error(w, fmt.Sprintf("variant must be 0..%d", s.Variants()-1), http.StatusBadRequest)
		return
	}
	w.Header().Set("X-Fable-Variant", fmt.Sprint(req.Variant))
	w.Header().Set("X-Fable-Variants", fmt.Sprint(s.Variants()))
	if !req.NoCache {
		if data := s.cached(req.SceneID, req.Variant, m, sc); data != nil {
			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("X-Fable-Cache", "hit")
			w.Write(data)
			return
		}
	}
	j, started := s.ensureJob(req.SceneID, req.Variant, req.ReadingPosition, sc, m)
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
			http.Error(w, fmt.Sprintf("%v (attempts=%d)", j.err, j.attempts), http.StatusBadGateway)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("X-Fable-Cache", "miss")
		w.Write(j.script)
	case <-timer.C:
		elapsed := time.Since(j.started)
		if started {
			log.Printf("interpret %s v%d: client waited %s, generation continues in the background", req.SceneID, req.Variant, wait)
		}
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("X-Fable-Cache", "pending")
		w.Header().Set("Retry-After", "15")
		w.WriteHeader(http.StatusAccepted)
		json.NewEncoder(w).Encode(pending{Status: "generating", SceneID: req.SceneID, Variant: req.Variant, ElapsedSeconds: elapsed.Seconds(), RetryAfter: 15})
	case <-r.Context().Done():
		// the client left; the job keeps running and will fill the cache
	}
}

type jobStatus struct {
	SceneID        string  `json:"sceneId"`
	Variant        int     `json:"variant"`
	Position       string  `json:"readingPosition,omitempty"`
	ElapsedSeconds float64 `json:"elapsedSeconds"`
}

func (s *Server) handleJobs(w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	list := make([]jobStatus, 0, len(s.jobs))
	for _, j := range s.jobs {
		list = append(list, jobStatus{SceneID: j.scene, Variant: j.variant, Position: j.position, ElapsedSeconds: time.Since(j.started).Seconds()})
	}
	s.mu.Unlock()
	cached := []string{}
	for _, sc := range s.Book.Scenes {
		m, err := s.manifest(sc.ID)
		if err != nil {
			continue
		}
		for v := 0; v < s.Variants(); v++ {
			if s.cached(sc.ID, v, m, &sc) != nil {
				cached = append(cached, jobKey(sc.ID, v))
			}
		}
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{"generating": list, "cached": cached, "variants": s.Variants()})
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	var ms runtime.MemStats
	runtime.ReadMemStats(&ms)
	s.mu.Lock()
	n := len(s.jobs)
	s.mu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"ok": true, "heapMB": float64(ms.HeapAlloc) / 1e6, "scenes": len(s.Book.Scenes),
		"model": s.Model, "apiKey": os.Getenv("ANTHROPIC_API_KEY") != "", "generating": n, "variants": s.Variants(),
	})
}

// Variants is how many readings a passage has (the plain one plus the alternatives).
func (s *Server) Variants() int { return len(llm.Readings) }

// Warm starts a generation for every scene whose cache is missing or stale. Call it only when a
// key is present; without one every job would fail and log noise.
func (s *Server) Warm() int {
	n := 0
	for i := range s.Book.Scenes {
		sc := &s.Book.Scenes[i]
		m, err := s.manifest(sc.ID)
		if err != nil || s.cached(sc.ID, 0, m, sc) != nil {
			continue
		}
		s.ensureJob(sc.ID, 0, "", sc, m)
		n++
	}
	return n
}

// Handler wires the routes. Logging wraps every request with method, path, status and duration.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("GET /jobs", s.handleJobs)
	mux.HandleFunc("GET /passages", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(s.Book)
	})
	mux.HandleFunc("POST /interpret", s.handleInterpret)
	mux.HandleFunc("POST /peek", s.handlePeek)
	if s.Rooms != nil {
		s.Rooms.Register(mux)
	}
	if s.Chapters != nil {
		s.Chapters.Register(mux)
	}
	return logging(mux)
}

type statusWriter struct {
	http.ResponseWriter
	code int
}

func (w *statusWriter) WriteHeader(c int) { w.code = c; w.ResponseWriter.WriteHeader(c) }

func logging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		sw := &statusWriter{ResponseWriter: w, code: 200}
		t := time.Now()
		next.ServeHTTP(sw, r)
		log.Printf("%s %s %d %s %s", r.Method, r.URL.Path, sw.code, time.Since(t).Round(time.Millisecond), r.RemoteAddr)
	})
}
