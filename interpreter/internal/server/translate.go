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
	"strings"
	"sync"
	"time"
)

// Translator is what llm.Director implements for Translate; tests substitute a fake.
type Translator interface {
	Translate(ctx context.Context, text, language, bookTitle string) (string, error)
}

// translates holds Translate's in-flight jobs. The result depends on the text and the language only, so there is no
// reading position to respect: the highlight is all that ever leaves the headset.
type translates struct {
	mu   sync.Mutex
	jobs map[string]*translateJob
}

type translateJob struct {
	done chan struct{}
	data []byte
	err  error
}

type translateRequest struct {
	Text        string  `json:"text"`
	Language    string  `json:"language"`            // a name from Languages, or its code ("es")
	BookID      string  `json:"bookId,omitempty"`    // a bundled slug: its title is sent for register
	BookTitle   string  `json:"bookTitle,omitempty"` // an imported book's title, when there is no slug the server knows
	SentenceID  string  `json:"sentenceId,omitempty"`
	NoCache     bool    `json:"noCache"`
	WaitSeconds float64 `json:"waitSeconds"`
}

type translateResponse struct {
	Translation string `json:"translation"`
	Language    string `json:"language"`
	Model       string `json:"model"`
}

// Languages are the names Translate accepts, by code. The headset keeps the same list (Highlighter.cs) and sends names.
var Languages = map[string]string{
	"es": "Spanish", "fr": "French", "pt": "Portuguese", "de": "German", "it": "Italian", "sn": "Shona",
	"nd": "isiNdebele", "sw": "Swahili", "zh": "Chinese (Simplified)", "hi": "Hindi", "ar": "Arabic",
}

// LanguageName resolves a code or a name (case-insensitively) to the list's spelling; "" when it is not in the list.
func LanguageName(s string) string {
	s = strings.TrimSpace(s)
	if n, ok := Languages[strings.ToLower(s)]; ok {
		return n
	}
	for _, n := range Languages {
		if strings.EqualFold(n, s) {
			return n
		}
	}
	return ""
}

// NormaliseText is the cache key's form of a highlight: single spaces, trimmed. Case is kept (names translate differently).
func NormaliseText(t string) string { return strings.Join(strings.Fields(t), " ") }

func (s *Server) translatePath(text, language string) string {
	h := sha256.Sum256([]byte(NormaliseText(text)))
	lang := strings.ToLower(strings.Fields(language)[0])
	return filepath.Join(s.Root, "out", "cache", "translate", lang, hex.EncodeToString(h[:8])+".json")
}

func (s *Server) cachedTranslation(text, language string) []byte {
	data, err := os.ReadFile(s.translatePath(text, language))
	if err != nil {
		return nil
	}
	var r translateResponse
	if json.Unmarshal(data, &r) != nil || r.Translation == "" {
		return nil
	}
	return data
}

// bookTitle is what the model is told about the book, for register: a bundled slug's title, else the title given.
func (s *Server) bookTitle(req translateRequest) string {
	if req.BookID != "" {
		if b, err := s.book(req.BookID); err == nil {
			return b.Title
		}
	}
	return strings.TrimSpace(req.BookTitle)
}

func (s *Server) handleTranslate(w http.ResponseWriter, r *http.Request) {
	var req translateRequest
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<14)).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	text := NormaliseText(req.Text)
	if text == "" || len(text) > 1200 {
		http.Error(w, "text must be 1-1200 characters", http.StatusBadRequest)
		return
	}
	lang := LanguageName(req.Language)
	if lang == "" {
		http.Error(w, fmt.Sprintf("language %q is not one Translate knows", req.Language), http.StatusBadRequest)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	if !req.NoCache {
		if data := s.cachedTranslation(text, lang); data != nil {
			w.Header().Set("X-Fable-Cache", "hit")
			w.Write(data)
			return
		}
	}
	if s.Translator == nil {
		http.Error(w, "no translator configured", http.StatusServiceUnavailable)
		return
	}
	key := lang + "|" + text
	s.translate.mu.Lock()
	if s.translate.jobs == nil {
		s.translate.jobs = map[string]*translateJob{}
	}
	j, ok := s.translate.jobs[key]
	if !ok {
		j = &translateJob{done: make(chan struct{})}
		s.translate.jobs[key] = j
		go s.runTranslate(key, j, text, lang, s.bookTitle(req))
	}
	s.translate.mu.Unlock()
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

func (s *Server) runTranslate(key string, j *translateJob, text, lang, title string) {
	defer func() {
		close(j.done)
		s.translate.mu.Lock()
		delete(s.translate.jobs, key) // on disk now (or failed); the next request reads the cache or retries
		s.translate.mu.Unlock()
	}()
	// a translation is a few seconds' work, but the client's wait is bounded on its own, so give the model peek's room
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	t0 := time.Now()
	out, err := s.Translator.Translate(ctx, text, lang, title)
	if err != nil {
		log.Printf("translate %s %q: failed in %s: %v", lang, text, time.Since(t0).Round(time.Millisecond), err)
		j.err = err
		return
	}
	j.data, _ = json.MarshalIndent(translateResponse{Translation: out, Language: lang, Model: s.Model}, "", "  ")
	p := s.translatePath(text, lang)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err == nil {
		os.WriteFile(p, j.data, 0o644)
	}
	log.Printf("translate %s %q: %d chars in %s", lang, text, len(out), time.Since(t0).Round(time.Millisecond))
}
