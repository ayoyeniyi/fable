package server

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"
)

type fakeTranslator struct {
	calls  int
	fail   bool
	titles []string
}

func (f *fakeTranslator) Translate(ctx context.Context, text, language, title string) (string, error) {
	f.calls++
	f.titles = append(f.titles, title)
	if f.fail {
		return "", errors.New("model down")
	}
	return "[" + language + "] " + text, nil
}

func translateReq(t *testing.T, h http.Handler, body string) *httptest.ResponseRecorder {
	t.Helper()
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, httptest.NewRequest("POST", "/translate", bytes.NewBufferString(body)))
	return rr
}

// The same text in the same language is translated once; another language is its own entry.
func TestTranslateCachesByTextAndLanguage(t *testing.T) {
	ft := &fakeTranslator{}
	s := New(t.TempDir(), nil, nil)
	s.Translator = ft
	s.Model = "fake"
	s.DefaultWait = 5 * time.Second
	h := s.Handler()
	rr := translateReq(t, h, `{"text":"  the little   golden key ","language":"es","bookTitle":"Alice"}`)
	if rr.Code != 200 || rr.Header().Get("X-Fable-Cache") != "miss" {
		t.Fatalf("first: %d %s %s", rr.Code, rr.Header().Get("X-Fable-Cache"), rr.Body)
	}
	var out translateResponse
	if err := json.Unmarshal(rr.Body.Bytes(), &out); err != nil || out.Translation != "[Spanish] the little golden key" || out.Language != "Spanish" || out.Model != "fake" {
		t.Fatalf("body: %v %s", err, rr.Body)
	}
	// whitespace and the language's spelling do not matter to the cache
	rr = translateReq(t, h, `{"text":"the little golden key","language":"Spanish"}`)
	if rr.Header().Get("X-Fable-Cache") != "hit" || ft.calls != 1 {
		t.Fatalf("repeat should hit the cache: %s calls=%d", rr.Header().Get("X-Fable-Cache"), ft.calls)
	}
	rr = translateReq(t, h, `{"text":"the little golden key","language":"fr"}`)
	if rr.Header().Get("X-Fable-Cache") != "miss" || ft.calls != 2 {
		t.Fatalf("another language is another translation: %s calls=%d", rr.Header().Get("X-Fable-Cache"), ft.calls)
	}
	if _, err := os.Stat(s.translatePath("the little golden key", "French")); err != nil {
		t.Fatalf("not cached on disk: %v", err)
	}
	if ft.titles[0] != "Alice" {
		t.Fatalf("the book's title should reach the model for register, got %q", ft.titles[0])
	}
}

// A bundled slug resolves to its title; the translator never sees any of the book's text.
func TestTranslateSendsOnlyTheHighlight(t *testing.T) {
	root := t.TempDir()
	if err := linkBooks(root); err != nil {
		t.Fatal(err)
	}
	ft := &fakeTranslator{}
	s := New(root, nil, nil)
	s.Translator = ft
	s.DefaultWait = 5 * time.Second
	rr := translateReq(t, s.Handler(), `{"text":"Curiouser and curiouser!","language":"de","bookId":"alice","sentenceId":"alice:c02.p001.s01"}`)
	if rr.Code != 200 {
		t.Fatalf("%d %s", rr.Code, rr.Body)
	}
	if ft.titles[0] != "Alice’s Adventures in Wonderland" && ft.titles[0] != "Alice's Adventures in Wonderland" {
		t.Fatalf("title: %q", ft.titles[0])
	}
}

func TestTranslateRefusals(t *testing.T) {
	ft := &fakeTranslator{fail: true}
	s := New(t.TempDir(), nil, nil)
	s.Translator = ft
	s.DefaultWait = 5 * time.Second
	h := s.Handler()
	if rr := translateReq(t, h, `not json`); rr.Code != 400 {
		t.Fatalf("bad body: want 400, got %d", rr.Code)
	}
	if rr := translateReq(t, h, `{"text":"   ","language":"es"}`); rr.Code != 400 {
		t.Fatalf("empty text: want 400, got %d", rr.Code)
	}
	if rr := translateReq(t, h, `{"text":"key","language":"klingon"}`); rr.Code != 400 {
		t.Fatalf("unknown language: want 400, got %d", rr.Code)
	}
	if rr := translateReq(t, h, `{"text":"key","language":"es"}`); rr.Code != http.StatusBadGateway {
		t.Fatalf("model failure: want 502, got %d %s", rr.Code, rr.Body)
	}
	if _, err := os.Stat(s.translatePath("key", "Spanish")); err == nil {
		t.Fatal("a failed translation must not be cached")
	}
	s.Translator = nil
	if rr := translateReq(t, h, `{"text":"key","language":"es"}`); rr.Code != http.StatusServiceUnavailable {
		t.Fatalf("no translator: want 503, got %d", rr.Code)
	}
}

// A slow model answers 202 within the client's wait, and the finished translation is served afterwards.
func TestTranslateSlowModelAnswersPending(t *testing.T) {
	s := New(t.TempDir(), nil, nil)
	s.Translator = slowTranslator(150 * time.Millisecond)
	s.DefaultWait = 20 * time.Millisecond
	h := s.Handler()
	if rr := translateReq(t, h, `{"text":"key","language":"es"}`); rr.Code != http.StatusAccepted {
		t.Fatalf("want 202, got %d %s", rr.Code, rr.Body)
	}
	if rr := translateReq(t, h, `{"text":"key","language":"es","waitSeconds":2}`); rr.Code != 200 || rr.Header().Get("X-Fable-Cache") != "miss" {
		t.Fatalf("patient client: want 200 miss, got %d %s", rr.Code, rr.Header().Get("X-Fable-Cache"))
	}
}

type slowTranslator time.Duration

func (d slowTranslator) Translate(ctx context.Context, text, language, title string) (string, error) {
	select {
	case <-time.After(time.Duration(d)):
		return "llave", nil
	case <-ctx.Done():
		return "", ctx.Err()
	}
}
