// Package mock is the Peek clay model (schema/mock-model.schema.json): a tree of primitives with 2-5 labels,
// built on the headset by ClayBuilder.cs. Validate enforces what the schema cannot say on its own: parents exist and
// come first, labels point at real parts, the triangle budget, and that quoted labels come from text already read.
package mock

import (
	"bytes"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
)

// Triangles per shape: must match ClayBuilder.cs (and the "triangles" block of the schema).
var Triangles = map[string]int{"box": 12, "sphere": 448, "hemisphere": 256, "cylinder": 64, "cone": 32, "capsule": 448, "torus": 384}

const Budget = 15000

type Part struct {
	ID       string    `json:"id"`
	Parent   string    `json:"parent,omitempty"`
	Shape    string    `json:"shape"`
	Size     []float64 `json:"size"`
	Position []float64 `json:"position,omitempty"`
	Rotation []float64 `json:"rotation,omitempty"`
	Color    string    `json:"color"`
	Material string    `json:"material,omitempty"`
}

type Label struct {
	Text  string `json:"text"`
	Part  string `json:"part"`
	Quote bool   `json:"quote,omitempty"`
}

type Model struct {
	Version      int     `json:"version"`
	ID           string  `json:"id,omitempty"`
	Title        string  `json:"title"`
	Book         string  `json:"book"`
	Phrase       string  `json:"phrase"`
	SentenceID   string  `json:"sentenceId"`
	HeightMetres float64 `json:"heightMetres"`
	RealHeight   string  `json:"realHeight,omitempty"`
	Source       string  `json:"source,omitempty"`
	Author       string  `json:"author,omitempty"`
	Parts        []Part  `json:"parts"`
	Labels       []Label `json:"labels"`
}

// Parse decodes strictly: an unknown key is an error, so a renamed field never silently drops.
func Parse(data []byte) (*Model, error) {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.DisallowUnknownFields()
	var m Model
	if err := dec.Decode(&m); err != nil {
		return nil, err
	}
	return &m, nil
}

func (m *Model) TriangleCount() int {
	n := 0
	for _, p := range m.Parts {
		n += Triangles[p.Shape]
	}
	return n
}

var (
	idRe       = regexp.MustCompile(`^[a-z0-9][a-z0-9\-]*$`)
	colorRe    = regexp.MustCompile(`^#[0-9a-fA-F]{6}$`)
	sentenceRe = regexp.MustCompile(`^[a-z]+:c[0-9]{2}\.p[0-9]{3}\.s[0-9]{2}$`)
	materials  = map[string]bool{"": true, "matte": true, "gloss": true, "metal": true, "glass": true, "emissive": true}
	bookSlugs  = map[string]bool{"alice": true, "oz": true, "odyssey": true, "gulliver": true}
)

// Validate returns every problem found. readText, when not nil, is everything the reader has read up to and
// including SentenceID: a label marked as a quote must appear in it.
func Validate(m *Model, readText string) []string {
	var errs []string
	add := func(f string, a ...any) { errs = append(errs, fmt.Sprintf(f, a...)) }
	if m.Version != 1 {
		add("version must be 1")
	}
	if strings.TrimSpace(m.Title) == "" || len(m.Title) > 60 {
		add("title must be 1-60 characters")
	}
	if !bookSlugs[m.Book] {
		add("book %q is not one of alice, oz, odyssey, gulliver", m.Book)
	}
	if strings.TrimSpace(m.Phrase) == "" {
		add("phrase is empty")
	}
	if !sentenceRe.MatchString(m.SentenceID) || (m.Book != "" && !strings.HasPrefix(m.SentenceID, m.Book+":")) {
		add("sentenceId %q is not a sentence of %s", m.SentenceID, m.Book)
	}
	if m.HeightMetres < 0.03 || m.HeightMetres > 0.6 {
		add("heightMetres %.3f must be 0.03-0.6", m.HeightMetres)
	}
	if m.Source != "" && m.Source != "clay" && m.Source != "fixture" {
		add("source must be clay or fixture")
	}
	if len(m.Parts) == 0 || len(m.Parts) > 48 {
		add("parts: %d, need 1-48", len(m.Parts))
	}
	seen := map[string]bool{}
	for i, p := range m.Parts {
		where := fmt.Sprintf("parts[%d] %q", i, p.ID)
		if !idRe.MatchString(p.ID) {
			add("%s: id must be lower-case letters, digits and hyphens", where)
		}
		if seen[p.ID] {
			add("%s: duplicate id", where)
		}
		if _, ok := Triangles[p.Shape]; !ok {
			add("%s: shape %q is not box, sphere, hemisphere, cylinder, cone, capsule or torus", where, p.Shape)
		}
		if len(p.Size) != 3 {
			add("%s: size needs 3 numbers", where)
		} else {
			for _, v := range p.Size {
				if v <= 0 || v > 100 {
					add("%s: size values must be in (0, 100]", where)
					break
				}
			}
		}
		if p.Position != nil && len(p.Position) != 3 {
			add("%s: position needs 3 numbers", where)
		}
		for _, v := range p.Position {
			if v < -100 || v > 100 {
				add("%s: position values must be within ±100", where)
				break
			}
		}
		if p.Rotation != nil && len(p.Rotation) != 3 {
			add("%s: rotation needs 3 numbers", where)
		}
		if !colorRe.MatchString(p.Color) {
			add("%s: color %q must be #rrggbb", where, p.Color)
		}
		if !materials[p.Material] {
			add("%s: material %q must be matte, gloss, metal, glass or emissive", where, p.Material)
		}
		if p.Parent != "" && !seen[p.Parent] {
			add("%s: parent %q must be an earlier part", where, p.Parent)
		}
		seen[p.ID] = true
	}
	if t := m.TriangleCount(); t > Budget {
		add("%d triangles, over the %d budget: use fewer or cheaper parts (box 12, cone 32, cylinder 64)", t, Budget)
	}
	if len(m.Labels) < 2 || len(m.Labels) > 5 {
		add("labels: %d, need 2-5", len(m.Labels))
	}
	low := strings.ToLower(norm(readText))
	for i, l := range m.Labels {
		if strings.TrimSpace(l.Text) == "" || len(l.Text) > 70 {
			add("labels[%d]: text must be 1-70 characters", i)
		}
		if !seen[l.Part] {
			add("labels[%d]: part %q is not a part id", i, l.Part)
		}
		if l.Quote && readText != "" && !strings.Contains(low, strings.ToLower(norm(strings.Trim(l.Text, `"“”‘’ `)))) {
			add("labels[%d]: marked as a quote but %q is not in the text read so far", i, l.Text)
		}
	}
	return errs
}

func norm(s string) string {
	r := strings.NewReplacer("’", "'", "‘", "'", "“", `"`, "”", `"`, "—", "-", "\n", " ")
	return strings.Join(strings.Fields(r.Replace(s)), " ")
}

// UnknownFields lists keys a reply used that the schema does not know (for the repair round).
func UnknownFields(data []byte) []string {
	var raw map[string]json.RawMessage
	if json.Unmarshal(data, &raw) != nil {
		return nil
	}
	known := map[string]bool{"version": true, "id": true, "title": true, "book": true, "phrase": true, "sentenceId": true, "heightMetres": true, "realHeight": true, "source": true, "author": true, "parts": true, "labels": true}
	var out []string
	for k := range raw {
		if !known[k] {
			out = append(out, fmt.Sprintf("unknown key %q", k))
		}
	}
	return out
}
