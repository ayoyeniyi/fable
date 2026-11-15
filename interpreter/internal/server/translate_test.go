package server

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
	"time"

	"github.com/Thabhelo/fable/interpreter/internal/textimg"
)

type fakeTranslator struct {
	calls  int
	fail   bool
	titles []string
	langs  []string
}

func (f *fakeTranslator) Translate(ctx context.Context, text, language, title string) (string, error) {
	f.calls++
	f.titles = append(f.titles, title)
	f.langs = append(f.langs, language)
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
	if _, err := os.Stat(s.translatePath("the little golden key", Languages[indexOf("fr")])); err != nil {
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
	if _, err := os.Stat(s.translatePath("key", Languages[indexOf("es")])); err == nil {
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

func indexOf(code string) int {
	for i, l := range Languages {
		if l.Code == code {
			return i
		}
	}
	return -1
}

// A script the headset cannot show as text comes back drawn; a Latin one does not, unless forced. The model is told
// the language by its precise name (isiNdebele as Zimbabwe's Northern Ndebele), and the answer names it in English.
func TestTranslatePicture(t *testing.T) {
	if _, err := os.Stat(filepath.Join("..", "..", "..", "content", "fonts", "NotoSerifDevanagari-Regular.ttf")); err != nil {
		t.Skip("fonts not fetched (python3 tools/fetch_fonts.py)")
	}
	ft := &fakeTranslator{}
	s := New(t.TempDir(), nil, nil)
	s.Translator, s.Model, s.DefaultWait = ft, "fake", 5*time.Second
	s.Fonts = textimg.New(filepath.Join("..", "..", "..", "content", "fonts"))
	h := s.Handler()
	var got translateResponse
	rr := translateReq(t, h, `{"text":"key","language":"hi","render":{"width":500,"size":36}}`)
	if rr.Code != 200 || json.Unmarshal(rr.Body.Bytes(), &got) != nil || len(got.Image) < 100 || got.ImageWidth != 500 || got.ImageHeight < 20 || got.Code != "hi" {
		t.Fatalf("Hindi should come back drawn: %d %dx%d %s", rr.Code, got.ImageWidth, got.ImageHeight, got.Code)
	}
	// from the cache, still drawn
	got = translateResponse{}
	rr = translateReq(t, h, `{"text":"key","language":"Hindi","render":{"width":500,"size":36}}`)
	if rr.Header().Get("X-Fable-Cache") != "hit" || json.Unmarshal(rr.Body.Bytes(), &got) != nil || len(got.Image) == 0 {
		t.Fatalf("a cached Hindi translation should be drawn too")
	}
	got = translateResponse{}
	rr = translateReq(t, h, `{"text":"key","language":"ar","render":{"width":500,"size":36}}`)
	if json.Unmarshal(rr.Body.Bytes(), &got) != nil || !got.RTL || len(got.Image) == 0 {
		t.Fatalf("Arabic should come back drawn, right to left")
	}
	got = translateResponse{}
	rr = translateReq(t, h, `{"text":"key","language":"es","render":{"width":500,"size":36}}`)
	if json.Unmarshal(rr.Body.Bytes(), &got) != nil || len(got.Image) != 0 || got.Translation == "" {
		t.Fatalf("Spanish is shown as text by the headset: no picture")
	}
	got = translateResponse{}
	rr = translateReq(t, h, `{"text":"key","language":"es","render":{"width":500,"size":36,"force":true}}`)
	if json.Unmarshal(rr.Body.Bytes(), &got) != nil || len(got.Image) == 0 {
		t.Fatalf("force should draw any language")
	}
	if rr := translateReq(t, h, `{"text":"key","language":"es","render":{"width":5000,"size":36}}`); rr.Code != 400 {
		t.Fatalf("an oversized picture should be refused, got %d", rr.Code)
	}
	translateReq(t, h, `{"text":"key","language":"nd"}`)
	if last := ft.langs[len(ft.langs)-1]; !strings.Contains(last, "Northern Ndebele") {
		t.Fatalf("the model should be told which Ndebele, got %q", last)
	}
	got = translateResponse{}
	rr = translateReq(t, h, `{"text":"key","language":"zh-hant"}`)
	if json.Unmarshal(rr.Body.Bytes(), &got) != nil || got.Language != "Chinese (Traditional)" {
		t.Fatalf("codes match case-insensitively and the answer names the language in English: %q", got.Language)
	}
}

// Every language has a distinct code and name, a native name, and (when drawn) a font that is fetched.
func TestLanguageList(t *testing.T) {
	if len(Languages) < 40 {
		t.Fatalf("Translate should offer at least 40 languages, has %d", len(Languages))
	}
	seen := map[string]bool{}
	for _, l := range Languages {
		for _, k := range []string{strings.ToLower(l.Code), strings.ToLower(l.Name)} {
			if seen[k] {
				t.Errorf("%q twice", k)
			}
			seen[k] = true
		}
		if l.Native == "" {
			t.Errorf("%s has no native name", l.Name)
		}
		if l.RTL && l.Font == "" {
			t.Errorf("%s is right to left: the headset cannot show it as text", l.Name)
		}
	}
	for _, need := range []string{"sn", "nd", "sw", "es", "zh", "hi", "ar"} {
		if indexOf(need) < 0 {
			t.Errorf("%s dropped from the list", need)
		}
	}
}

// The headset's list (TranslateLanguages.cs) and this one are the same languages, in the same order, with the same
// names, native names, and way of being shown (drawn by the server, right to left).
func TestLanguagesMatchHeadset(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("..", "..", "..", "unity", "Fable", "Assets", "Fable", "Scripts", "TranslateLanguages.cs"))
	if err != nil {
		t.Skip("no Unity project beside the interpreter")
	}
	re := regexp.MustCompile(`L\("([^"]+)", "([^"]+)", "([^"]+)"((?:, (?:drawn|rtl): true)*)\)`)
	rows := re.FindAllStringSubmatch(string(data), -1)
	if len(rows) != len(Languages) {
		t.Fatalf("the headset has %d languages, the server %d", len(rows), len(Languages))
	}
	for i, m := range rows {
		l := Languages[i]
		drawn, rtl := strings.Contains(m[4], "drawn: true"), strings.Contains(m[4], "rtl: true")
		if m[1] != l.Code || m[2] != l.Name || m[3] != l.Native || drawn != (l.Font != "") || rtl != l.RTL {
			t.Errorf("row %d: headset %s/%s/%s drawn=%v rtl=%v, server %s/%s/%s font=%q rtl=%v", i, m[1], m[2], m[3], drawn, rtl, l.Code, l.Name, l.Native, l.Font, l.RTL)
		}
	}
}
