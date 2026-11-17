package server

import (
	"encoding/json"
	"io/fs"
	"net/http"
	"os"
	"path"
	"sort"
	"strings"

	"github.com/Thabhelo/fable/interpreter/internal/chapters"
)

// handleSceneRooms serves the published downloadable scene rooms (docs/SCENE_ROOMS_PIPELINE.md) from
// content/scene-rooms, read-only, in the style of /maps:
//
//	GET /scene-rooms/index.json        every published room's manifest (id, version, chapters, zip size and SHA-256)
//	GET /scene-rooms/<id>/manifest.json
//	GET /scene-rooms/<id>/<room-xxxx>.zip   the package the headset downloads (Range requests resume it)
//	GET /scene-rooms/<id>/view.jpg     the reader's view rendered in Blender
func (s *Server) handleSceneRooms(w http.ResponseWriter, r *http.Request) {
	p := r.PathValue("path")
	dir := chapters.SceneRoomsDir(s.Root)
	if p == "index.json" || p == "" {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-cache")
		json.NewEncoder(w).Encode(map[string]any{"rooms": sceneRoomIndex(s.Root)})
		return
	}
	parts := strings.Split(p, "/")
	if !fs.ValidPath(p) || len(parts) != 2 || strings.HasPrefix(parts[1], ".") {
		http.NotFound(w, r)
		return
	}
	name := parts[1]
	ext := path.Ext(name)
	if name != "manifest.json" && name != "view.jpg" && ext != ".zip" {
		http.NotFound(w, r)
		return
	}
	root := os.DirFS(dir)
	if st, err := fs.Stat(root, p); err != nil || st.IsDir() {
		http.NotFound(w, r)
		return
	}
	switch ext {
	case ".json":
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-cache")
	case ".zip":
		w.Header().Set("Content-Type", "application/zip")
		w.Header().Set("Cache-Control", "public, max-age=31536000, immutable") // the name carries the version
	default:
		w.Header().Set("Cache-Control", "public, max-age=300")
	}
	http.ServeFileFS(w, r, root, p)
}

// sceneRoomIndex lists the complete published rooms, sorted by id.
func sceneRoomIndex(root string) []*chapters.SceneRoomManifest {
	out := []*chapters.SceneRoomManifest{}
	ents, _ := os.ReadDir(chapters.SceneRoomsDir(root))
	for _, e := range ents {
		if !e.IsDir() {
			continue
		}
		if m, err := chapters.LoadSceneRoom(root, e.Name()); err == nil {
			out = append(out, m)
		}
	}
	sort.Slice(out, func(a, b int) bool { return out[a].ID < out[b].ID })
	return out
}
