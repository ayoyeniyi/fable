package server

import (
	"io/fs"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strings"
)

// handleMaps serves the book maps (docs/MAPS.md) from content/maps: GET /maps/<slug> answers that book's
// map.json; GET /maps/<path> answers any other file under content/maps (the images a map.json names as
// "maps/<path>"). Read-only and confined to that directory; fs.ValidPath rejects "..".
func (s *Server) handleMaps(w http.ResponseWriter, r *http.Request) {
	p := r.PathValue("path")
	if p != "" && !strings.Contains(p, "/") && path.Ext(p) == "" {
		p = path.Join(p, "map.json")
	}
	if !fs.ValidPath(p) || p == "." || strings.HasPrefix(path.Base(p), ".") {
		http.NotFound(w, r)
		return
	}
	root := os.DirFS(filepath.Join(s.Root, "content", "maps"))
	if st, err := fs.Stat(root, p); err != nil || st.IsDir() {
		http.NotFound(w, r)
		return
	}
	if path.Ext(p) == ".json" {
		w.Header().Set("Content-Type", "application/json")
	}
	w.Header().Set("Cache-Control", "public, max-age=300")
	http.ServeFileFS(w, r, root, p)
}
