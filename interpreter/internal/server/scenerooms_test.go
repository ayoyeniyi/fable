package server

import (
	"encoding/json"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSceneRoomsServesIndexManifestAndZip(t *testing.T) {
	s := newServer(t, &fake{})
	dir := filepath.Join(s.Root, "content", "scene-rooms", "pool-bank")
	os.MkdirAll(dir, 0o755)
	sha := strings.Repeat("ab", 32)
	os.WriteFile(filepath.Join(dir, "manifest.json"), []byte(`{"id":"pool-bank","version":"abababab","zip":"room-abababab.zip","bytes":4,"sha256":"`+sha+`","view":"view.jpg"}`), 0o644)
	os.WriteFile(filepath.Join(dir, "room-abababab.zip"), []byte("PK.."), 0o644)
	os.WriteFile(filepath.Join(dir, "view.jpg"), []byte("\xff\xd8\xff\xe0jpeg"), 0o644)
	os.WriteFile(filepath.Join(dir, "secret.txt"), []byte("no"), 0o644)
	// an unfinished publish (no zip) is not listed
	os.MkdirAll(filepath.Join(s.Root, "content", "scene-rooms", "half"), 0o755)
	os.WriteFile(filepath.Join(s.Root, "content", "scene-rooms", "half", "manifest.json"), []byte(`{"id":"half"}`), 0o644)
	h := s.Handler()
	get := func(p string) *httptest.ResponseRecorder {
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, httptest.NewRequest("GET", p, nil))
		return rec
	}
	rec := get("/scene-rooms/index.json")
	var idx struct {
		Rooms []struct {
			ID string `json:"id"`
		} `json:"rooms"`
	}
	if rec.Code != 200 || json.Unmarshal(rec.Body.Bytes(), &idx) != nil || len(idx.Rooms) != 1 || idx.Rooms[0].ID != "pool-bank" {
		t.Fatalf("index: %d %s", rec.Code, rec.Body.String())
	}
	if rec := get("/scene-rooms/pool-bank/room-abababab.zip"); rec.Code != 200 || rec.Body.String() != "PK.." || rec.Header().Get("Content-Type") != "application/zip" {
		t.Fatalf("zip: %d %q", rec.Code, rec.Header().Get("Content-Type"))
	}
	if rec := get("/scene-rooms/pool-bank/manifest.json"); rec.Code != 200 {
		t.Fatalf("manifest: %d", rec.Code)
	}
	for _, p := range []string{"/scene-rooms/pool-bank/secret.txt", "/scene-rooms/../maps/x.json", "/scene-rooms/pool-bank/../half/manifest.json/x", "/scene-rooms/nosuch/view.jpg", "/scene-rooms/pool-bank"} {
		if rec := get(p); rec.Code == 200 {
			t.Errorf("%s: want an error, got 200", p)
		}
	}
}
