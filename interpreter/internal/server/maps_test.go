package server

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func TestMapsServesMapJSONAndImages(t *testing.T) {
	s := newServer(t, &fake{})
	dir := filepath.Join(s.Root, "content", "maps", "treasure")
	os.MkdirAll(dir, 0o755)
	os.WriteFile(filepath.Join(dir, "map.json"), []byte(`{"version":1,"book":"treasure"}`), 0o644)
	os.WriteFile(filepath.Join(dir, "island.jpg"), []byte("\xff\xd8\xff\xe0jpeg"), 0o644)
	os.WriteFile(filepath.Join(s.Root, "content", "secret.txt"), []byte("no"), 0o644)
	h := s.Handler()
	get := func(p string) *httptest.ResponseRecorder {
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, httptest.NewRequest("GET", p, nil))
		return rec
	}
	rec := get("/maps/treasure")
	if rec.Code != http.StatusOK || rec.Body.String() != `{"version":1,"book":"treasure"}` {
		t.Fatalf("map.json: %d %q", rec.Code, rec.Body.String())
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("content type %q", ct)
	}
	if rec := get("/maps/treasure/island.jpg"); rec.Code != http.StatusOK || rec.Header().Get("Content-Type") != "image/jpeg" {
		t.Errorf("image: %d %q", rec.Code, rec.Header().Get("Content-Type"))
	}
	for _, p := range []string{"/maps/nosuchbook", "/maps/treasure/missing.jpg", "/maps/../secret.txt", "/maps/treasure/../../secret.txt", "/maps/treasure/"} {
		if rec := get(p); rec.Code == http.StatusOK {
			t.Errorf("%s: want an error, got 200 %q", p, rec.Body.String())
		}
	}
}

func TestMapsRepoContentIsServed(t *testing.T) {
	// The real content tree: every committed map.json must be reachable.
	s := newServer(t, &fake{})
	s.Root = "../../.."
	entries, _ := os.ReadDir("../../../content/maps")
	h := s.Handler()
	for _, e := range entries {
		if !e.IsDir() || e.Name()[0] == '_' {
			continue
		}
		if _, err := os.Stat(filepath.Join("../../../content/maps", e.Name(), "map.json")); err != nil {
			continue
		}
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, httptest.NewRequest("GET", "/maps/"+e.Name(), nil))
		if rec.Code != http.StatusOK {
			t.Errorf("/maps/%s: %d", e.Name(), rec.Code)
		}
	}
}
