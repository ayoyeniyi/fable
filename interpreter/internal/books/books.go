// Package books loads whole books (content/books/<slug>/book.json, written by tools/ingest_book.py) and hands out
// the text a reader has reached. The spoiler rule lives here: TextUpTo never returns a word after the given sentence.
package books

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type Sentence struct {
	ID         string `json:"id"`
	Text       string `json:"text"`
	LineBefore bool   `json:"lineBefore,omitempty"`
}

type Paragraph struct {
	ID        string     `json:"id"`
	Style     string     `json:"style"`
	Sentences []Sentence `json:"sentences"`
}

type Chapter struct {
	ID         string      `json:"id"`
	Kind       string      `json:"kind"`
	Label      string      `json:"label"`
	Title      string      `json:"title"`
	Paragraphs []Paragraph `json:"paragraphs"`
}

type Book struct {
	Slug       string    `json:"slug"`
	Title      string    `json:"title"`
	Author     string    `json:"author"`
	Translator string    `json:"translator"`
	Year       int       `json:"year"`
	Chapters   []Chapter `json:"chapters"`

	flat  []loc
	where map[string]int
}

type loc struct{ c, p, s int }

// Slugs are the books Fable ships: the first four have hand-built rooms, the last four bundled generated rooms.
var Slugs = []string{"alice", "oz", "odyssey", "gulliver", "pride", "mobydick", "worlds", "treasure"}

func Load(root, slug string) (*Book, error) {
	data, err := os.ReadFile(filepath.Join(root, "content", "books", slug, "book.json"))
	if err != nil {
		return nil, err
	}
	var b Book
	if err := json.Unmarshal(data, &b); err != nil {
		return nil, fmt.Errorf("book %s: %w", slug, err)
	}
	b.where = map[string]int{}
	for c, ch := range b.Chapters {
		for p, pa := range ch.Paragraphs {
			for s, se := range pa.Sentences {
				b.where[se.ID] = len(b.flat)
				b.flat = append(b.flat, loc{c, p, s})
			}
		}
	}
	return &b, nil
}

// Ordinal is the sentence's position in the whole book, or -1.
func (b *Book) Ordinal(id string) int {
	if i, ok := b.where[id]; ok {
		return i
	}
	return -1
}

func (b *Book) sentence(i int) (Sentence, Chapter) {
	l := b.flat[i]
	ch := b.Chapters[l.c]
	return ch.Paragraphs[l.p].Sentences[l.s], ch
}

// Text of one sentence.
func (b *Book) Text(id string) string {
	i := b.Ordinal(id)
	if i < 0 {
		return ""
	}
	s, _ := b.sentence(i)
	return s.Text
}

// ChapterTitle names the chapter a sentence is in.
func (b *Book) ChapterTitle(id string) string {
	i := b.Ordinal(id)
	if i < 0 {
		return ""
	}
	_, ch := b.sentence(i)
	return ch.Title
}

// TextUpTo returns about maxChars of the book ending exactly at sentence id (inclusive), paragraphs separated by
// blank lines. Nothing after id is ever included: this is everything the reader has seen up to their highlight.
func (b *Book) TextUpTo(id string, maxChars int) (string, error) {
	end := b.Ordinal(id)
	if end < 0 {
		return "", fmt.Errorf("sentence %q is not in %s", id, b.Slug)
	}
	var parts []string
	n := 0
	lastPara := -1
	lastChap := -1
	for i := end; i >= 0 && n < maxChars; i-- {
		s, _ := b.sentence(i)
		l := b.flat[i]
		sep := " "
		if lastPara >= 0 && (l.p != lastPara || l.c != lastChap) {
			sep = "\n\n"
		}
		if len(parts) > 0 {
			parts = append(parts, sep)
		}
		parts = append(parts, s.Text)
		lastPara, lastChap = l.p, l.c
		n += len(s.Text) + 1
	}
	for i, j := 0, len(parts)-1; i < j; i, j = i+1, j-1 {
		parts[i], parts[j] = parts[j], parts[i]
	}
	return strings.Join(parts, ""), nil
}

// Find returns the id of the last sentence at or before `before` that contains phrase (case-insensitive), or "".
// Used by the CLI so a test can name a phrase instead of a sentence id.
func (b *Book) Find(phrase string, before string) string {
	end := len(b.flat) - 1
	if before != "" {
		if e := b.Ordinal(before); e >= 0 {
			end = e
		}
	}
	p := strings.ToLower(phrase)
	for i := 0; i <= end; i++ {
		if s, _ := b.sentence(i); strings.Contains(strings.ToLower(s.Text), p) {
			return s.ID
		}
	}
	return ""
}
