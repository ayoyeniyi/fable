// Package book loads book/passages.json (sentence-indexed passages).
package book

import (
	"encoding/json"
	"fmt"
	"os"
)

type Sentence struct {
	ID   string `json:"id"`
	Text string `json:"text"`
}

type Scene struct {
	ID            string       `json:"id"`
	Title         string       `json:"title"`
	Chapter       string       `json:"chapter"`
	Paragraphs    [][]Sentence `json:"paragraphs"`
	SentenceCount int          `json:"sentenceCount"`
	ContextBefore []string     `json:"contextBefore"`
	// Room is the built environment this passage is staged in when it is not its own (several chapters share a room).
	Room string `json:"room,omitempty"`
	// BookSlug, BookFrom, BookTo: the whole book this passage is cut from and the book sentence ids it covers.
	BookSlug string `json:"book,omitempty"`
	BookFrom string `json:"bookFrom,omitempty"`
	BookTo   string `json:"bookTo,omitempty"`
}

type Book struct {
	Book struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Year   int    `json:"year"`
		Source string `json:"source"`
	} `json:"book"`
	Scenes []Scene `json:"scenes"`
}

func Load(path string) (*Book, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var b Book
	if err := json.Unmarshal(data, &b); err != nil {
		return nil, fmt.Errorf("passages: %w", err)
	}
	return &b, nil
}

func (b *Book) Scene(id string) (*Scene, error) {
	for i := range b.Scenes {
		if b.Scenes[i].ID == id {
			return &b.Scenes[i], nil
		}
	}
	return nil, fmt.Errorf("scene %q not in book", id)
}

func (s *Scene) SentenceIDs() []string {
	var ids []string
	for _, p := range s.Paragraphs {
		for _, se := range p {
			ids = append(ids, se.ID)
		}
	}
	return ids
}

// Context returns the previously read text, trimmed to the last maxChars characters.
// Only text before the passage is ever sent: the model must not learn future events from us.
func (s *Scene) Context(maxChars int) string {
	out := ""
	for _, p := range s.ContextBefore {
		out += p + "\n\n"
	}
	if len(out) > maxChars {
		out = "..." + out[len(out)-maxChars:]
	}
	return out
}

// Numbered renders the passage with ids so the model can cite sentences exactly.
func (s *Scene) Numbered() string {
	out := ""
	for _, p := range s.Paragraphs {
		for _, se := range p {
			out += "[" + se.ID + "] " + se.Text + "\n"
		}
		out += "\n"
	}
	return out
}
