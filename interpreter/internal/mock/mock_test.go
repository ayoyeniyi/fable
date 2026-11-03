package mock

import (
	"strings"
	"testing"
)

func good() *Model {
	return &Model{Version: 1, Title: "the golden key", Book: "alice", Phrase: "golden key", SentenceID: "alice:c01.p013.s01", HeightMetres: 0.2,
		Parts: []Part{
			{ID: "bow", Shape: "torus", Size: []float64{2, 0.4, 2}, Position: []float64{0, 5, 0}, Color: "#d4a832", Material: "metal"},
			{ID: "shaft", Shape: "cylinder", Size: []float64{0.4, 4, 0.4}, Position: []float64{0, 2, 0}, Color: "#d4a832", Material: "metal"},
			{ID: "bit", Parent: "shaft", Shape: "box", Size: []float64{1, 0.8, 0.3}, Position: []float64{0.5, -1.6, 0}, Color: "#d4a832"},
		},
		Labels: []Label{{Text: "a tiny golden key", Part: "bow", Quote: true}, {Text: "too small for the large locks", Part: "bit"}}}
}

func TestValidModel(t *testing.T) {
	m := good()
	if errs := Validate(m, "There was nothing on it except a tiny golden key, and Alice's first thought was..."); len(errs) > 0 {
		t.Fatal(errs)
	}
	if m.TriangleCount() != 384+64+12 {
		t.Fatalf("triangles %d", m.TriangleCount())
	}
}

func TestRejects(t *testing.T) {
	cases := map[string]func(m *Model){
		"labels: 1":          func(m *Model) { m.Labels = m.Labels[:1] },
		"must be an earlier": func(m *Model) { m.Parts[2].Parent = "nowhere" },
		"is not a part id":   func(m *Model) { m.Labels[1].Part = "handle" },
		"over the 15000": func(m *Model) {
			for i := 0; i < 40; i++ {
				m.Parts = append(m.Parts, Part{ID: "s" + string(rune('a'+i%26)) + string(rune('a'+i/26)), Shape: "sphere", Size: []float64{1, 1, 1}, Color: "#ffffff"})
			}
		},
		"not in the text read": func(m *Model) { m.Labels[0].Text = "the key to the rose garden" },
		"shape \"pyramid\"":    func(m *Model) { m.Parts[0].Shape = "pyramid" },
		"must be #rrggbb":      func(m *Model) { m.Parts[0].Color = "gold" },
		"heightMetres":         func(m *Model) { m.HeightMetres = 2 },
		"not a sentence of":    func(m *Model) { m.SentenceID = "oz:c01.p001.s01" },
	}
	for want, mut := range cases {
		m := good()
		mut(m)
		errs := Validate(m, "There was nothing on it except a tiny golden key")
		if !strings.Contains(strings.Join(errs, "|"), want) {
			t.Errorf("%s: got %v", want, errs)
		}
	}
}

func TestParseRejectsUnknownKeys(t *testing.T) {
	if _, err := Parse([]byte(`{"version":1,"colour":"red"}`)); err == nil {
		t.Fatal("unknown key accepted")
	}
}

// Peek works in front matter too (Gulliver's letter, Alice's poem), whose sentence ids start with f.
func TestFrontMatterSentenceIDsAreSentences(t *testing.T) {
	if !sentenceRe.MatchString("alice:f01.p006.s01") || !sentenceRe.MatchString("gulliver:c29.p001.s02") || sentenceRe.MatchString("alice:x01.p006.s01") {
		t.Fatal("sentence id pattern wrong")
	}
}
