package llm

import (
	"context"
	"fmt"
	"strings"
)

const translatePrompt = `You translate short highlights for Fable, a VR reader on Meta Quest. A reader has highlighted a few words or
sentences of a book and wants them in another language. You are given only the highlight and the book's title: nothing
before or after it, so translate what is there and do not guess at the rest of the scene.

Return the translation and nothing else: no quotation marks around it, no notes, no alternatives, no transliteration,
no code fences. Keep the register of the original (an old novel reads as an old novel), keep names as names, and keep
the highlight's own punctuation and line breaks. A single word gets a single word or short phrase; where the word has
several senses, give the one a reader of that book most likely means. If the highlight is already in the target
language, return it unchanged.`

// Translate renders text in the named language, sending Claude only the highlight and the book's title (register).
func (d *Director) Translate(ctx context.Context, text, language, bookTitle string) (string, error) {
	user := fmt.Sprintf("TARGET LANGUAGE: %s\n", language)
	if bookTitle != "" {
		user += fmt.Sprintf("BOOK: %s\n", bookTitle)
	}
	user += fmt.Sprintf("HIGHLIGHT:\n%s\n\nReturn the translation only.", text)
	out, err := d.Ask(ctx, translatePrompt, user, 1500)
	if err != nil {
		return "", err
	}
	out = strings.TrimSpace(out)
	if out == "" {
		return "", fmt.Errorf("model returned an empty translation")
	}
	return out, nil
}
