// Package script defines the SceneScript contract shared with Unity and validates
// instances against the scene manifest vocabulary. It mirrors schema/scene-script.schema.json.
package script

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
)

type Vec3 [3]float64

type Environment struct {
	Prefab   string   `json:"prefab"`
	Ambience string   `json:"ambience"`
	Exposure *float64 `json:"exposure,omitempty"`
	Fog      *float64 `json:"fog,omitempty"`
}

// Action is a tagged union; unused fields stay nil so output is compact.
type Action struct {
	Type            string   `json:"type"`
	Asset           string   `json:"asset,omitempty"`
	Anchor          string   `json:"anchor,omitempty"`
	Offset          *Vec3    `json:"offset,omitempty"`
	YawDegrees      *float64 `json:"yawDegrees,omitempty"`
	Scale           *float64 `json:"scale,omitempty"`
	Appear          string   `json:"appear,omitempty"`
	Ease            string   `json:"ease,omitempty"`
	Vanish          string   `json:"vanish,omitempty"`
	Target          string   `json:"target,omitempty"`
	Clip            string   `json:"clip,omitempty"`
	DurationSeconds *float64 `json:"durationSeconds,omitempty"`
	Loop            *bool    `json:"loop,omitempty"`
	Light           string   `json:"light,omitempty"`
	Intensity       *float64 `json:"intensity,omitempty"`
	Kelvin          *int     `json:"kelvin,omitempty"`
	Sound           string   `json:"sound,omitempty"`
	Volume          *float64 `json:"volume,omitempty"`
}

type Beat struct {
	SentenceID string   `json:"sentenceId"`
	Focus      string   `json:"focus,omitempty"`
	Actions    []Action `json:"actions"`
}

type SceneScript struct {
	Version     int         `json:"version"`
	SceneID     string      `json:"sceneId"`
	Title       string      `json:"title,omitempty"`
	Environment Environment `json:"environment"`
	Beats       []Beat      `json:"beats"`
}

// Manifest is the per-scene vocabulary (schema/manifest.<scene>.json).
type Manifest struct {
	SceneID     string              `json:"sceneId"`
	Environment string              `json:"environment"`
	Ambiences   []string            `json:"ambiences"`
	Anchors     map[string]string   `json:"anchors"`
	Assets      map[string]string   `json:"assets"`
	Clips       map[string][]string `json:"clips"`
	Lights      []string            `json:"lights"`
	Sounds      []string            `json:"sounds"`
	// IntroducedBy maps an asset to the sentence that first brings it into the story. An action that
	// shows, moves or animates the asset on an earlier beat would show the reader something they have
	// not read yet, so it is rejected.
	IntroducedBy map[string]string `json:"introducedBy,omitempty"`
	// ReaderScaleFrom is the first sentence on which the reader may change size (scale != 1).
	ReaderScaleFrom string `json:"readerScaleFrom,omitempty"`
}

// tooEarly reports whether asset is used on sentence before the text introduces it.
// Sentence ids are zero-padded within one passage, so string order is reading order.
func (m *Manifest) tooEarly(asset, sentence string) (string, bool) {
	at, ok := m.IntroducedBy[asset]
	return at, ok && sentence < at
}

var sentenceIDRe = regexp.MustCompile(`^[a-z-]+:[0-9]{3}$`)

// Parse decodes strictly: unknown fields are errors so the model cannot smuggle instructions.
func Parse(data []byte) (*SceneScript, error) {
	dec := json.NewDecoder(strings.NewReader(string(data)))
	dec.DisallowUnknownFields()
	var s SceneScript
	if err := dec.Decode(&s); err != nil {
		return nil, fmt.Errorf("decode: %w", err)
	}
	return &s, nil
}

func contains(list []string, v string) bool {
	for _, x := range list {
		if x == v {
			return true
		}
	}
	return false
}

func inRange(v *float64, lo, hi float64) bool { return v == nil || (*v >= lo && *v <= hi) }

// Validate returns every problem found (not just the first) so a repair round can fix them all.
func Validate(s *SceneScript, m *Manifest, sentenceIDs []string) []string {
	var errs []string
	add := func(f string, a ...any) { errs = append(errs, fmt.Sprintf(f, a...)) }
	if s.Version != 1 {
		add("version must be 1")
	}
	if s.SceneID != m.SceneID {
		add("sceneId %q must be %q", s.SceneID, m.SceneID)
	}
	if len(s.Title) > 80 {
		add("title longer than 80 chars")
	}
	if s.Environment.Prefab != m.Environment {
		add("environment.prefab %q must be %q", s.Environment.Prefab, m.Environment)
	}
	if !contains(m.Ambiences, s.Environment.Ambience) {
		add("environment.ambience %q not in %v", s.Environment.Ambience, m.Ambiences)
	}
	if !inRange(s.Environment.Exposure, -2, 2) {
		add("environment.exposure out of [-2,2]")
	}
	if !inRange(s.Environment.Fog, 0, 1) {
		add("environment.fog out of [0,1]")
	}
	if len(s.Beats) == 0 || len(s.Beats) > 40 {
		add("beats must have 1..40 items, got %d", len(s.Beats))
	}
	seen := map[string]bool{}
	for i, b := range s.Beats {
		p := fmt.Sprintf("beats[%d]", i)
		if !sentenceIDRe.MatchString(b.SentenceID) {
			add("%s.sentenceId %q malformed", p, b.SentenceID)
		} else if !contains(sentenceIDs, b.SentenceID) {
			add("%s.sentenceId %q is not a sentence of this passage", p, b.SentenceID)
		}
		if seen[b.SentenceID] {
			add("%s.sentenceId %q repeated", p, b.SentenceID)
		}
		seen[b.SentenceID] = true
		if i > 0 && b.SentenceID < s.Beats[i-1].SentenceID {
			add("%s out of reading order", p)
		}
		if b.Focus != "" {
			if _, ok := m.Anchors[b.Focus]; !ok {
				add("%s.focus %q unknown anchor", p, b.Focus)
			}
		}
		if len(b.Actions) > 8 {
			add("%s has more than 8 actions", p)
		}
		for j, a := range b.Actions {
			q := fmt.Sprintf("%s.actions[%d]", p, j)
			subject := a.Asset
			if a.Type == "animate" {
				subject = a.Target
			}
			if at, early := m.tooEarly(subject, b.SentenceID); early && a.Type != "remove" {
				add("%s uses %q on %s, before the text introduces it at %s", q, subject, b.SentenceID, at)
			}
			switch a.Type {
			case "place":
				if _, ok := m.Assets[a.Asset]; !ok {
					add("%s.asset %q unknown", q, a.Asset)
				}
				if _, ok := m.Anchors[a.Anchor]; !ok {
					add("%s.anchor %q unknown", q, a.Anchor)
				}
				if a.Offset != nil {
					for _, c := range a.Offset {
						if c < -20 || c > 20 {
							add("%s.offset component out of [-20,20]", q)
							break
						}
					}
				}
				if !inRange(a.YawDegrees, -180, 180) {
					add("%s.yawDegrees out of range", q)
				}
				if !inRange(a.Scale, 0.05, 20) {
					add("%s.scale out of range", q)
				}
				if a.Appear != "" && !contains([]string{"instant", "fade", "grow", "settle"}, a.Appear) {
					add("%s.appear %q invalid", q, a.Appear)
				}
				if a.Target != "" || a.Clip != "" || a.Light != "" || a.Sound != "" || a.Vanish != "" {
					add("%s has fields that do not belong to place", q)
				}
			case "move":
				if _, ok := m.Assets[a.Asset]; !ok {
					add("%s.asset %q unknown", q, a.Asset)
				}
				if _, ok := m.Anchors[a.Anchor]; !ok {
					add("%s.anchor %q unknown", q, a.Anchor)
				}
				if !inRange(a.DurationSeconds, 0.1, 20) {
					add("%s.durationSeconds out of range", q)
				}
				if a.Ease != "" && !contains([]string{"smooth", "linear", "settle"}, a.Ease) {
					add("%s.ease %q invalid", q, a.Ease)
				}
			case "remove":
				if _, ok := m.Assets[a.Asset]; !ok {
					add("%s.asset %q unknown", q, a.Asset)
				}
				if a.Vanish != "" && !contains([]string{"instant", "fade", "shrink"}, a.Vanish) {
					add("%s.vanish %q invalid", q, a.Vanish)
				}
			case "animate":
				clips, ok := m.Clips[a.Target]
				if !ok {
					add("%s.target %q has no clips", q, a.Target)
				} else if !contains(clips, a.Clip) {
					add("%s.clip %q not supported for %q (supported: %v)", q, a.Clip, a.Target, clips)
				}
				if !inRange(a.DurationSeconds, 0.1, 20) {
					add("%s.durationSeconds out of range", q)
				}
			case "light":
				if !contains(m.Lights, a.Light) {
					add("%s.light %q unknown", q, a.Light)
				}
				if !inRange(a.Intensity, 0, 4) {
					add("%s.intensity out of [0,4]", q)
				}
				if a.Kelvin != nil && (*a.Kelvin < 1500 || *a.Kelvin > 8000) {
					add("%s.kelvin out of range", q)
				}
				if !inRange(a.DurationSeconds, 0, 20) {
					add("%s.durationSeconds out of range", q)
				}
			case "sound":
				if !contains(m.Sounds, a.Sound) {
					add("%s.sound %q unknown", q, a.Sound)
				}
				if a.Anchor != "" {
					if _, ok := m.Anchors[a.Anchor]; !ok {
						add("%s.anchor %q unknown", q, a.Anchor)
					}
				}
				if !inRange(a.Volume, 0, 1) {
					add("%s.volume out of [0,1]", q)
				}
			case "readerScale":
				if _, ok := m.Anchors[a.Anchor]; !ok {
					add("%s.anchor %q unknown", q, a.Anchor)
				}
				if a.Scale == nil || *a.Scale < 0.1 || *a.Scale > 10 {
					add("%s.scale required in [0.1,10]", q)
				}
				if a.DurationSeconds == nil || *a.DurationSeconds < 3 || *a.DurationSeconds > 12 {
					add("%s.durationSeconds required in [3,12]: slower size changes keep the reader comfortable", q)
				}
				if a.Scale != nil && *a.Scale != 1 && m.ReaderScaleFrom != "" && b.SentenceID < m.ReaderScaleFrom {
					add("%s changes the reader's size on %s, before the text does at %s", q, b.SentenceID, m.ReaderScaleFrom)
				}
			default:
				add("%s.type %q unknown", q, a.Type)
			}
		}
	}
	return errs
}
