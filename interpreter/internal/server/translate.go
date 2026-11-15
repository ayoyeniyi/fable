package server

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"image/color"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/Thabhelo/fable/interpreter/internal/textimg"
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
	Language    string  `json:"language"`            // a code from Languages ("es", "zh-Hant") or its English name
	BookID      string  `json:"bookId,omitempty"`    // a bundled slug: its title is sent for register
	BookTitle   string  `json:"bookTitle,omitempty"` // an imported book's title, when there is no slug the server knows
	SentenceID  string  `json:"sentenceId,omitempty"`
	NoCache     bool    `json:"noCache"`
	WaitSeconds float64 `json:"waitSeconds"`
	// Render asks for the translation drawn as a picture as well, for languages the headset cannot show as text
	// (Language.Font), or for any language with Force (the headset found a glyph its font lacks).
	Render *renderRequest `json:"render,omitempty"`
}

type renderRequest struct {
	Width int     `json:"width"` // pixels, 64-2048
	Size  float32 `json:"size"`  // pixels per em, 8-128
	Ink   string  `json:"ink"`   // "#rrggbb"; default a dark brown
	Force bool    `json:"force"`
}

type translateResponse struct {
	Translation string `json:"translation"`
	Language    string `json:"language"`
	Model       string `json:"model"`
	// set when a picture was asked for and the language needs one: PNG, transparent paper
	Code        string `json:"code,omitempty"`
	RTL         bool   `json:"rtl,omitempty"`
	Image       []byte `json:"image,omitempty"` // base64 in JSON
	ImageWidth  int    `json:"imageWidth,omitempty"`
	ImageHeight int    `json:"imageHeight,omitempty"`
}

// NormaliseText is the cache key's form of a highlight: single spaces, trimmed. Case is kept (names translate differently).
func NormaliseText(t string) string { return strings.Join(strings.Fields(t), " ") }

// translatePath is the cache file: one folder per language code (zh and zh-Hant apart).
func (s *Server) translatePath(text string, l Language) string {
	h := sha256.Sum256([]byte(NormaliseText(text)))
	return filepath.Join(s.Root, "out", "cache", "translate", strings.ToLower(l.Code), hex.EncodeToString(h[:8])+".json")
}

func (s *Server) cachedTranslation(text string, l Language) []byte {
	data, err := os.ReadFile(s.translatePath(text, l))
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
	lang, ok := FindLanguage(req.Language)
	if !ok {
		http.Error(w, fmt.Sprintf("language %q is not one Translate knows", req.Language), http.StatusBadRequest)
		return
	}
	if r := req.Render; r != nil && (r.Width < 64 || r.Width > 2048 || r.Size < 8 || r.Size > 128) {
		http.Error(w, "render: width must be 64-2048 and size 8-128", http.StatusBadRequest)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	if !req.NoCache {
		if data := s.cachedTranslation(text, lang); data != nil {
			w.Header().Set("X-Fable-Cache", "hit")
			w.Write(s.withPicture(data, lang, req.Render))
			return
		}
	}
	if s.Translator == nil {
		http.Error(w, "no translator configured", http.StatusServiceUnavailable)
		return
	}
	key := lang.Code + "|" + text
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
		w.Write(s.withPicture(j.data, lang, req.Render))
	case <-timer.C:
		w.WriteHeader(http.StatusAccepted)
		fmt.Fprintf(w, `{"status":"generating"}`)
	}
}

func (s *Server) runTranslate(key string, j *translateJob, text string, lang Language, title string) {
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
	out, err := s.Translator.Translate(ctx, text, lang.ForModel(), title)
	if err != nil {
		log.Printf("translate %s %q: failed in %s: %v", lang.Code, text, time.Since(t0).Round(time.Millisecond), err)
		j.err = err
		return
	}
	j.data, _ = json.MarshalIndent(translateResponse{Translation: out, Language: lang.Name, Model: s.Model}, "", "  ")
	p := s.translatePath(text, lang)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err == nil {
		os.WriteFile(p, j.data, 0o644)
	}
	log.Printf("translate %s %q: %d chars in %s", lang.Code, text, len(out), time.Since(t0).Round(time.Millisecond))
}

// withPicture adds the drawn translation to a cached or fresh answer when one was asked for and the language needs it
// (or Force). The cache keeps text only: drawing takes milliseconds. A missing font leaves the answer as text, and the
// headset then says it cannot show this script.
func (s *Server) withPicture(data []byte, lang Language, r *renderRequest) []byte {
	if r == nil || (lang.Font == "" && !r.Force) || s.Fonts == nil {
		return data
	}
	var resp translateResponse
	if json.Unmarshal(data, &resp) != nil {
		return data
	}
	font := lang.Font
	if font == "" {
		font = textimg.Fallback
	}
	if !s.Fonts.Has(font) {
		log.Printf("translate %s: font %s is missing from content/fonts (python3 tools/fetch_fonts.py)", lang.Code, font)
		return data
	}
	img, err := s.Fonts.Draw(resp.Translation, textimg.Options{Font: font, Lang: lang.Code, RTL: lang.RTL, Width: r.Width, Size: r.Size, Ink: parseInk(r.Ink), MaxLines: 40})
	if err != nil {
		log.Printf("translate %s: drawing failed: %v", lang.Code, err)
		return data
	}
	png, err := textimg.PNG(img)
	if err != nil {
		return data
	}
	resp.Code, resp.RTL, resp.Image, resp.ImageWidth, resp.ImageHeight = lang.Code, lang.RTL, png, img.Bounds().Dx(), img.Bounds().Dy()
	out, err := json.Marshal(resp)
	if err != nil {
		return data
	}
	return out
}

func parseInk(s string) color.NRGBA {
	c := color.NRGBA{41, 31, 20, 255}
	var r, g, b uint8
	if n, _ := fmt.Sscanf(strings.TrimPrefix(s, "#"), "%02x%02x%02x", &r, &g, &b); n == 3 {
		c.R, c.G, c.B = r, g, b
	}
	return c
}
