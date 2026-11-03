// Package llm turns a passage plus manifest into a SceneScript using Claude,
// with one repair round driven by validator output.
package llm

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/anthropics/anthropic-sdk-go/v2"

	"github.com/Thabhelo/fable/interpreter/internal/book"
	"github.com/Thabhelo/fable/interpreter/internal/script"
)

const systemPrompt = `You are the scene director for Fable, a VR reading experience on Meta Quest.
You receive one passage of a public-domain novel, split into numbered sentences, and a manifest
listing the only assets, anchors, animation clips, lights and sounds the engine can execute.

Produce a SceneScript JSON object and nothing else: no prose, no code fences.
Rules:
- "version": 1. "sceneId" and "environment.prefab" exactly as the manifest gives them.
- One beat per sentence that changes the room, in reading order. Sentences that change nothing may be skipped.
- Use only ids that appear in the manifest. Never invent an asset, anchor, clip, light or sound.
- Keep the reader's comfort: at most one readerScale action per beat, duration 3 to 8 seconds,
  and never scale faster than that. No camera motion exists; the reader stands still.
- Prefer small, legible changes: a lamp flicker, a door rattle, a bottle appearing on the table.
- Sound actions are spatial; give each an anchor.
- Match the text literally. The passage is the authority, not the film adaptations.
- Keep characters and places consistent with the previously read context you are given, and never
  show anything the reader has not reached yet: the reading position marks how far they have read.
- Details the text leaves open (colours, exact sizes, where a thing stands) are your interpretation;
  keep them modest and period-appropriate.

The exact shape. Use these keys and no others; optional keys may be left out but never renamed:
{"version":1,"sceneId":"<manifest sceneId>","title":"<short title>",
 "environment":{"prefab":"<manifest environment>","ambience":"<one of manifest ambiences>","exposure":-0.2,"fog":0.2},
 "beats":[{"sentenceId":"<scene>:<nnn>","focus":"<anchor id>","actions":[...]}]}
Actions (durations are always "durationSeconds", in seconds):
 {"type":"place","asset":"<asset id>","anchor":"<anchor id>","offset":[x,y,z],"yawDegrees":0,"scale":1,"appear":"instant|fade|grow|settle"}
 {"type":"move","asset":"<asset id>","anchor":"<anchor id>","durationSeconds":1.5,"ease":"smooth|linear|settle"}
 {"type":"remove","asset":"<asset id>","vanish":"instant|fade|shrink"}
 {"type":"animate","target":"<a key of manifest clips>","clip":"<one of that key's clips>","durationSeconds":2,"loop":false}
 {"type":"light","light":"<light id>","intensity":0.0-4.0,"kelvin":1500-8000,"durationSeconds":0-20}
 {"type":"sound","sound":"<sound id>","anchor":"<anchor id>","volume":0.0-1.0}
 {"type":"readerScale","anchor":"<anchor id>","scale":0.1-10,"durationSeconds":3-12}
Beats cite sentence ids in reading order, each at most once, at most 8 actions per beat.`

type Director struct {
	client anthropic.Client
	model  string
}

func New(model string) *Director {
	if model == "" {
		model = "claude-opus-5-5"
	}
	return &Director{client: anthropic.NewClient(), model: model}
}

// Ask sends one user message under the given system prompt and returns the text, code fences stripped.
func (d *Director) Ask(ctx context.Context, system, user string, maxTokens int64) (string, error) {
	return d.askWith(ctx, system, []anthropic.MessageParam{anthropic.NewUserMessage(anthropic.NewTextBlock(user))}, maxTokens)
}

// AskRaw is Ask without fence stripping, reporting why the answer stopped ("end_turn", "max_tokens", ...).
func (d *Director) AskRaw(ctx context.Context, system, user string, maxTokens int64) (string, string, error) {
	stream := d.client.Messages.NewStreaming(ctx, anthropic.MessageNewParams{
		Model:     anthropic.Model(d.model),
		MaxTokens: maxTokens,
		System:    []anthropic.TextBlockParam{{Text: system}},
		Messages:  []anthropic.MessageParam{anthropic.NewUserMessage(anthropic.NewTextBlock(user))},
	})
	msg := anthropic.Message{}
	for stream.Next() {
		if err := msg.Accumulate(stream.Current()); err != nil {
			return "", "", err
		}
	}
	if err := stream.Err(); err != nil {
		return "", "", err
	}
	var sb strings.Builder
	for _, block := range msg.Content {
		if t, ok := block.AsAny().(anthropic.TextBlock); ok {
			sb.WriteString(t.Text)
		}
	}
	return sb.String(), string(msg.StopReason), nil
}

func (d *Director) ask(ctx context.Context, msgs []anthropic.MessageParam) (string, error) {
	return d.askWith(ctx, systemPrompt, msgs, 16000)
}

func (d *Director) askWith(ctx context.Context, system string, msgs []anthropic.MessageParam, maxTokens int64) (string, error) {
	resp, err := d.client.Messages.New(ctx, anthropic.MessageNewParams{
		Model:     anthropic.Model(d.model),
		MaxTokens: maxTokens,
		System:    []anthropic.TextBlockParam{{Text: system}},
		Messages:  msgs,
	})
	if err != nil {
		return "", err
	}
	if resp.StopReason == "refusal" {
		return "", fmt.Errorf("model declined the request (stop_reason=refusal)")
	}
	var sb strings.Builder
	for _, block := range resp.Content {
		if t, ok := block.AsAny().(anthropic.TextBlock); ok {
			sb.WriteString(t.Text)
		}
	}
	return stripFences(sb.String()), nil
}

func stripFences(s string) string {
	s = strings.TrimSpace(s)
	if strings.HasPrefix(s, "```") {
		s = strings.TrimPrefix(s, "```json")
		s = strings.TrimPrefix(s, "```")
		if i := strings.LastIndex(s, "```"); i >= 0 {
			s = s[:i]
		}
	}
	return strings.TrimSpace(s)
}

// Readings are the alternative interpretations of one passage ("parallel universes"): the same text and the same
// vocabulary, staged with a different emphasis. Variant 0 is the plain reading; the others are cached separately.
var Readings = []string{
	"",
	"This is a second reading of the passage. Emphasise scale and the body: how large the hall feels, how small the reader is, how objects loom or shrink. Favour slow, physical changes and let silence do work.",
	"This is a third reading of the passage. Theatrical and lively: give characters and props more motion, stage each sentence like a beat on a small stage, and use the sound vocabulary generously, while keeping every action tied to the sentence that earns it.",
	"This is a fourth reading of the passage. Spare and literal: the fewest actions that make the text visible, nothing decorative, sound only where the text names one.",
}

// Interpret asks for a script, validates it, and sends the validator's findings back once.
// variant selects one of Readings (out of range falls back to the plain reading).
func (d *Director) Interpret(ctx context.Context, sc *book.Scene, m *script.Manifest, readingPosition string, variant int) (*script.SceneScript, []string, error) {
	mj, _ := json.MarshalIndent(m, "", "  ")
	pos := readingPosition
	if pos == "" {
		pos = "the start of the passage"
	}
	direction := ""
	if variant > 0 && variant < len(Readings) {
		direction = "\nDIRECTION: " + Readings[variant] + "\n"
	}
	staging := ""
	if sc.Room != "" && sc.Room != sc.ID {
		staging = fmt.Sprintf("\nSTAGING: this chapter is deliberately played in the %q set, a borrowed stage, the way a theatre stages a scene on whatever set is standing: its anchors, props, characters, lights, clips and sounds stand in for what the text describes. The mismatch is intended; do not flag it, refuse, or leave beats out because the set is not literal. Suggest rather than match (a lamp dims for dusk, a door rattles for a knock, a character asset speaks for whoever is talking, a prop grows for anything that grows). Give EVERY sentence its own beat, in order, each with one to four actions, so the reader sees the room answer each line.\n", sc.Room)
	}
	user := fmt.Sprintf("MANIFEST:\n%s\n\nPREVIOUSLY READ (context only, already happened):\n%s\nREADING POSITION: %s\n%s%s\nPASSAGE (%s, %s):\n%s\nReturn the SceneScript JSON.", mj, sc.Context(6000), pos, direction, staging, sc.Title, sc.Chapter, sc.Numbered())
	msgs := []anthropic.MessageParam{anthropic.NewUserMessage(anthropic.NewTextBlock(user))}
	var attempts []string
	for round := 0; round < 2; round++ {
		raw, err := d.ask(ctx, msgs)
		if err != nil {
			return nil, attempts, err
		}
		attempts = append(attempts, raw)
		s, perr := script.Parse([]byte(raw))
		var problems []string
		if perr != nil {
			problems = append([]string{perr.Error()}, script.UnknownFields([]byte(raw))...)
		} else {
			problems = script.Validate(s, m, sc.SentenceIDs())
		}
		if len(problems) == 0 {
			return s, attempts, nil
		}
		if round == 1 {
			return nil, attempts, fmt.Errorf("script still invalid after repair: %s", strings.Join(problems, "; "))
		}
		msgs = append(msgs,
			anthropic.NewAssistantMessage(anthropic.NewTextBlock(raw)),
			anthropic.NewUserMessage(anthropic.NewTextBlock("The engine rejected that script:\n- "+strings.Join(problems, "\n- ")+"\nReturn the corrected full SceneScript JSON only.")))
	}
	return nil, attempts, fmt.Errorf("unreachable")
}

// Model reports the model id in use, for /health.
func (d *Director) Model() string { return d.model }
