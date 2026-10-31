package script

import (
	"encoding/json"
	"os"
	"strings"
	"testing"

	"github.com/Thabhelo/fable/interpreter/internal/book"
)

func load(t *testing.T) (*Manifest, []string) {
	t.Helper()
	data, err := os.ReadFile("../../../schema/manifest.hall-of-doors.json")
	if err != nil {
		t.Fatal(err)
	}
	var m Manifest
	if err := json.Unmarshal(data, &m); err != nil {
		t.Fatal(err)
	}
	bk, err := book.Load("../../../book/passages.json")
	if err != nil {
		t.Fatal(err)
	}
	sc, _ := bk.Scene("hall-of-doors")
	return &m, sc.SentenceIDs()
}

func TestBaselineValid(t *testing.T) {
	m, ids := load(t)
	data, err := os.ReadFile("../../../scripts/hall-of-doors.baseline.json")
	if err != nil {
		t.Fatal(err)
	}
	s, err := Parse(data)
	if err != nil {
		t.Fatal(err)
	}
	if errs := Validate(s, m, ids); len(errs) > 0 {
		t.Fatalf("baseline invalid: %v", errs)
	}
}

func TestRejects(t *testing.T) {
	m, ids := load(t)
	cases := map[string]string{
		"unknown field":   `{"version":1,"sceneId":"hall-of-doors","environment":{"prefab":"env.hall-of-doors","ambience":"amb.hall-lamps"},"beats":[],"evil":true}`,
		"invented asset":  `{"version":1,"sceneId":"hall-of-doors","environment":{"prefab":"env.hall-of-doors","ambience":"amb.hall-lamps"},"beats":[{"sentenceId":"hall-of-doors:000","actions":[{"type":"place","asset":"prop.cheshire-cat","anchor":"table.top"}]}]}`,
		"bad clip":        `{"version":1,"sceneId":"hall-of-doors","environment":{"prefab":"env.hall-of-doors","ambience":"amb.hall-lamps"},"beats":[{"sentenceId":"hall-of-doors:000","actions":[{"type":"animate","target":"door.little","clip":"door.explode"}]}]}`,
		"wrong sentence":  `{"version":1,"sceneId":"hall-of-doors","environment":{"prefab":"env.hall-of-doors","ambience":"amb.hall-lamps"},"beats":[{"sentenceId":"hall-of-doors:099","actions":[]}]}`,
		"out of order":    `{"version":1,"sceneId":"hall-of-doors","environment":{"prefab":"env.hall-of-doors","ambience":"amb.hall-lamps"},"beats":[{"sentenceId":"hall-of-doors:003","actions":[]},{"sentenceId":"hall-of-doors:001","actions":[]}]}`,
		"too fast scale":  `{"version":1,"sceneId":"hall-of-doors","environment":{"prefab":"env.hall-of-doors","ambience":"amb.hall-lamps"},"beats":[{"sentenceId":"hall-of-doors:000","actions":[{"type":"readerScale","anchor":"reader.table","scale":4,"durationSeconds":0.1}]}]}`,
	}
	for name, js := range cases {
		s, err := Parse([]byte(js))
		if err != nil {
			if name == "unknown field" && strings.Contains(err.Error(), "unknown field") {
				continue
			}
			t.Fatalf("%s: unexpected parse error %v", name, err)
		}
		if errs := Validate(s, m, ids); len(errs) == 0 {
			t.Errorf("%s: expected rejection", name)
		}
	}
}
