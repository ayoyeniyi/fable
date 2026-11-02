// Package chapters prepares chapter experiences in the background while the reader reads: a persistent, bounded
// queue of one job per chapter, each taken through the whole pipeline before it is called ready:
//
//	planning    Claude reads the book only up to the end of the target chapter and picks the chapter's
//	            significant place or moment, an environment that can honestly stand for it (or none), a mood
//	scripting   for scripted environments (Alice's rooms, which have manifests), a SceneScript for the chapter's
//	            passage, validated against the manifest
//	rendering   Blender renders the adapted environment from the reader's place (blender/render_experience_thumb.py)
//	validating  plan, script, environment budgets and the render are checked again
//	packaging   package.json + thumb.jpg, hashed and size-checked, ready for the headset to fetch
//
// The headset then downloads, validates again and holds the package sealed until the reader finishes the chapter
// (Unity: ChapterExperiences.cs). Status answers carry stages only: no titles, places or images leave the server
// until the headset asks for the package, and the headset never shows them before the chapter is complete.
package chapters

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

type Env struct {
	ID         string   `json:"id"`
	UnityScene string   `json:"unityScene"`
	Staging    string   `json:"staging"` // scripted | place
	Books      []string `json:"books"`
	Place      string   `json:"place"`
	GLTF       string   `json:"gltf"`
	Eye        string   `json:"eye"`
	Look       string   `json:"look"`
	Triangles  int      `json:"triangles"`
	Meshes     int      `json:"meshes"`
}

type Budget struct {
	TargetTriangles int `json:"targetTriangles"`
	MaxTriangles    int `json:"maxTriangles"`
	MaxMeshes       int `json:"maxMeshes"`
}

type Catalog struct {
	Budget       Budget   `json:"budget"`
	Moods        []string `json:"moods"`
	Environments []Env    `json:"environments"`
}

func LoadCatalog(root string) (*Catalog, error) {
	data, err := os.ReadFile(filepath.Join(root, "schema", "environments.json"))
	if err != nil {
		return nil, err
	}
	var c Catalog
	if err := json.Unmarshal(data, &c); err != nil {
		return nil, fmt.Errorf("environments.json: %w", err)
	}
	return &c, nil
}

func (c *Catalog) Env(id string) (Env, bool) {
	for _, e := range c.Environments {
		if e.ID == id {
			return e, true
		}
	}
	return Env{}, false
}

// ForBook lists the environments built for a book.
func (c *Catalog) ForBook(slug string) []Env {
	var out []Env
	for _, e := range c.Environments {
		for _, b := range e.Books {
			if b == slug {
				out = append(out, e)
			}
		}
	}
	return out
}

func (c *Catalog) MoodOK(m string) bool {
	for _, x := range c.Moods {
		if x == m {
			return true
		}
	}
	return false
}

// BudgetProblems: an adapted environment adds no geometry, so its budget is the built room's.
func (c *Catalog) BudgetProblems(e Env) []string {
	var p []string
	if e.Triangles <= 0 || e.Meshes <= 0 {
		p = append(p, fmt.Sprintf("%s has no measured triangle and mesh counts", e.ID))
	}
	if c.Budget.MaxTriangles > 0 && e.Triangles > c.Budget.MaxTriangles {
		p = append(p, fmt.Sprintf("%s is %d triangles, over the %d limit", e.ID, e.Triangles, c.Budget.MaxTriangles))
	}
	if c.Budget.MaxMeshes > 0 && e.Meshes > c.Budget.MaxMeshes {
		p = append(p, fmt.Sprintf("%s is %d meshes, over the %d limit", e.ID, e.Meshes, c.Budget.MaxMeshes))
	}
	return p
}
