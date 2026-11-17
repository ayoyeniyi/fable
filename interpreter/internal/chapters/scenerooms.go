package chapters

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Downloadable scene rooms (docs/SCENE_ROOMS_PIPELINE.md): chapter rooms that are not in the APK. An environment with
// Delivery "download" names a published package in content/scene-rooms/<SceneRoom>/ (manifest.json, the zip, view.jpg,
// written by tools/publish_scene_room.py); the headset downloads the zip and shows it in its UnityScene (LibraryRoom).

// ScenePlan is schema/scene_rooms.json: for the first ten chapters of each book, the place of the chapter's
// predominant scene, an existing environment or a new room to be built. It decides the place for those chapters.
type ScenePlan struct {
	Chapters []struct {
		ID    string `json:"id"`
		Place string `json:"place"`
	} `json:"chapters"`
	Places []PlannedPlace `json:"places"`
}

type PlannedPlace struct {
	ID       string   `json:"id"`
	Book     string   `json:"book"`
	Name     string   `json:"name"`
	Chapters []string `json:"chapters"`
	Existing string   `json:"existing,omitempty"`
}

func loadScenePlan(root string) (*ScenePlan, error) {
	data, err := os.ReadFile(filepath.Join(root, "schema", "scene_rooms.json"))
	if errors.Is(err, os.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var p ScenePlan
	if err := json.Unmarshal(data, &p); err != nil {
		return nil, fmt.Errorf("scene_rooms.json: %w", err)
	}
	return &p, nil
}

// Planned is the planned place of a chapter in schema/scene_rooms.json (ok false: the plan does not cover it).
func (c *Catalog) Planned(chapter string) (PlannedPlace, bool) {
	if c.Plan == nil {
		return PlannedPlace{}, false
	}
	for _, ch := range c.Plan.Chapters {
		if ch.ID != chapter {
			continue
		}
		for _, p := range c.Plan.Places {
			if p.ID == ch.Place {
				return p, true
			}
		}
	}
	return PlannedPlace{}, false
}

// PlannedEnv is the environment that stands for a planned place: the existing room it names, else the downloadable
// scene room built for it (if one is in the catalogue).
func (c *Catalog) PlannedEnv(p PlannedPlace) (Env, bool) {
	if p.Existing != "" {
		return c.Env(p.Existing)
	}
	for _, e := range c.Environments {
		if e.Delivery == "download" && e.SceneRoom == p.ID {
			return e, true
		}
	}
	return Env{}, false
}

// SceneRoomRef is what a chapter package tells the headset to download (Unity: ChapterPackage.SceneRoomRef).
type SceneRoomRef struct {
	ID      string `json:"id"`
	Version string `json:"version"` // the zip's SHA-256 prefix: a new publish is a new version
	File    string `json:"file"`    // GET /scene-rooms/<id>/<file>
	Bytes   int64  `json:"bytes"`
	SHA256  string `json:"sha256"`
}

// SceneRoomManifest is content/scene-rooms/<id>/manifest.json (tools/publish_scene_room.py).
type SceneRoomManifest struct {
	ID        string   `json:"id"`
	Version   string   `json:"version"`
	Title     string   `json:"title"`
	Book      string   `json:"book"`
	Chapters  []string `json:"chapters"`
	Zip       string   `json:"zip"`
	Bytes     int64    `json:"bytes"`
	SHA256    string   `json:"sha256"`
	View      string   `json:"view"`
	Triangles int      `json:"triangles"`
	Meshes    int      `json:"meshes"`
}

// SceneRoomsDir is where published scene rooms live under the service's root.
func SceneRoomsDir(root string) string { return filepath.Join(root, "content", "scene-rooms") }

// LoadSceneRoom reads a published room's manifest and checks its files are there.
func LoadSceneRoom(root, id string) (*SceneRoomManifest, error) {
	if id == "" || strings.ContainsAny(id, `/\.`) {
		return nil, fmt.Errorf("bad scene room id %q", id)
	}
	dir := filepath.Join(SceneRoomsDir(root), id)
	data, err := os.ReadFile(filepath.Join(dir, "manifest.json"))
	if err != nil {
		return nil, fmt.Errorf("scene room %s is not published on this server", id)
	}
	var m SceneRoomManifest
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, fmt.Errorf("scene room %s: manifest: %w", id, err)
	}
	if m.ID != id || m.Zip == "" || len(m.SHA256) != 64 || m.Bytes <= 0 {
		return nil, fmt.Errorf("scene room %s: incomplete manifest", id)
	}
	for _, f := range []string{m.Zip, m.View} {
		if f == "" || strings.Contains(f, "/") {
			return nil, fmt.Errorf("scene room %s: bad file name %q", id, f)
		}
		if st, err := os.Stat(filepath.Join(dir, f)); err != nil || st.IsDir() {
			return nil, fmt.Errorf("scene room %s: %s is missing", id, f)
		}
	}
	return &m, nil
}

func (m *SceneRoomManifest) Ref() *SceneRoomRef {
	return &SceneRoomRef{ID: m.ID, Version: m.Version, File: m.Zip, Bytes: m.Bytes, SHA256: m.SHA256}
}
