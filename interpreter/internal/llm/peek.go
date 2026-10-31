package llm

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/anthropics/anthropic-sdk-go/v2"

	"github.com/Thabhelo/fable/interpreter/internal/books"
	"github.com/Thabhelo/fable/interpreter/internal/mock"
)

const peekPrompt = `You make Peek models for Fable, a VR reader on Meta Quest. A reader has highlighted a phrase in a
public-domain book. You get the book's text up to the end of the highlight, and nothing after it. Build a small,
low-fi "clay" model of the thing the phrase names, made of primitives, that the reader can turn in their hand
beside the page, with 2 to 5 short labels.

Produce one JSON object and nothing else: no prose, no code fences. The exact shape (these keys only):
{"version":1,"title":"<the thing, 1-60 chars, e.g. 'the golden key'>","book":"<slug>","phrase":"<the highlight>",
 "sentenceId":"<the sentence id you were given>","heightMetres":0.25,"realHeight":"<its size in the story, optional>",
 "source":"clay",
 "parts":[{"id":"<a-z0-9->","parent":"<earlier part id, optional>","shape":"box|sphere|hemisphere|cylinder|cone|capsule|torus",
           "size":[x,y,z],"position":[x,y,z],"rotation":[xDeg,yDeg,zDeg],"color":"#rrggbb","material":"matte|gloss|metal|glass|emissive"}],
 "labels":[{"text":"<1-70 chars>","part":"<part id>","quote":false}]}
Rules:
- Units are your own; the model is scaled so its tallest extent is heightMetres (0.03-0.6). Y is up, the model
  stands on y=0 and faces +z. A child's position and rotation are relative to its parent.
- size is the full extent along x, y, z (a sphere of size [1,1,1] has radius 0.5). Torus: x and z are the outer
  diameter, y the thickness of the ring. Cylinders, cones and capsules stand along y.
- At most 48 parts and 15000 triangles. Costs: box 12, cone 32, cylinder 64, hemisphere 256, torus 384,
  sphere 448, capsule 448. Most good models need 6-20 parts.
- Show only what the text so far supports. Never show, label or hint at anything the book has not reached:
  the reader has not read past the last sentence you are given. Where the text is silent, choose modest,
  period-appropriate details and do not label them as fact.
- Labels point at the part they describe. Prefer the book's own words: a label that quotes the text exactly
  sets "quote": true, and must then appear word for word in the text you were given. Other labels are brief notes
  ("brass, worn smooth"). No spoilers in labels either.
- Match the text literally, not film or illustrated adaptations. People and creatures are allowed but keep them
  simple figures; no faces beyond eyes.`

// Peek asks for a clay model of phrase as read up to sentenceID, validates it, and repairs once.
func (d *Director) Peek(ctx context.Context, b *books.Book, sentenceID, phrase string) (*mock.Model, []string, error) {
	read, err := b.TextUpTo(sentenceID, 7000)
	if err != nil {
		return nil, nil, err
	}
	by := b.Author
	if b.Translator != "" {
		by += ", translated by " + b.Translator
	}
	user := fmt.Sprintf("BOOK: %s (slug %q), %s, %d\nCHAPTER: %s\nTEXT READ SO FAR (it ends with the highlight's sentence, id %s):\n%s\n\nHIGHLIGHT: %q\nReturn the mock model JSON.",
		b.Title, b.Slug, by, b.Year, b.ChapterTitle(sentenceID), sentenceID, read, phrase)
	msgs := []anthropic.MessageParam{anthropic.NewUserMessage(anthropic.NewTextBlock(user))}
	var attempts []string
	for round := 0; round < 2; round++ {
		raw, err := d.askWith(ctx, peekPrompt, msgs, 6000)
		if err != nil {
			return nil, attempts, err
		}
		attempts = append(attempts, raw)
		m, perr := mock.Parse([]byte(raw))
		var problems []string
		if perr != nil {
			problems = append([]string{perr.Error()}, mock.UnknownFields([]byte(raw))...)
		} else {
			// the model is about this highlight, whatever it wrote
			m.Book, m.SentenceID, m.Source = b.Slug, sentenceID, "clay"
			if m.Phrase == "" {
				m.Phrase = phrase
			}
			problems = mock.Validate(m, read)
		}
		if len(problems) == 0 {
			return m, attempts, nil
		}
		if round == 1 {
			return nil, attempts, fmt.Errorf("mock model still invalid after repair: %s", strings.Join(problems, "; "))
		}
		msgs = append(msgs,
			anthropic.NewAssistantMessage(anthropic.NewTextBlock(raw)),
			anthropic.NewUserMessage(anthropic.NewTextBlock("The builder rejected that model:\n- "+strings.Join(problems, "\n- ")+"\nReturn the corrected full JSON only.")))
	}
	return nil, attempts, fmt.Errorf("unreachable")
}

// MarshalModel is the indented form written to caches and stdout.
func MarshalModel(m *mock.Model) []byte { js, _ := json.MarshalIndent(m, "", "  "); return js }
