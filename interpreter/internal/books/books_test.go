package books

import (
	"strings"
	"testing"
)

func TestTextUpToStopsAtTheHighlight(t *testing.T) {
	b, err := Load("../../..", "alice")
	if err != nil {
		t.Fatal(err)
	}
	key := b.Find("little golden key", "")
	if key == "" {
		t.Fatal("no sentence mentions the little golden key")
	}
	txt, err := b.TextUpTo(key, 3000)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasSuffix(txt, b.Text(key)) {
		t.Fatalf("text does not end with the highlight's sentence:\n...%s", txt[len(txt)-200:])
	}
	// the next sentence of the book must not be there
	next := b.flat[b.Ordinal(key)+1]
	ns := b.Chapters[next.c].Paragraphs[next.p].Sentences[next.s].Text
	if strings.Contains(txt, ns) {
		t.Fatalf("text includes the sentence after the highlight: %q", ns)
	}
	if len(txt) > 3000+len(b.Text(key))+400 {
		t.Fatalf("text is %d chars, asked for about 3000", len(txt))
	}
}

func TestEveryBookLoads(t *testing.T) {
	for _, s := range Slugs {
		b, err := Load("../../..", s)
		if err != nil {
			t.Fatal(err)
		}
		if len(b.flat) < 1000 {
			t.Fatalf("%s: only %d sentences", s, len(b.flat))
		}
	}
}
