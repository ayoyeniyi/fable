// Package textimg draws text the headset's TextMeshPro cannot: scripts that need shaping (Devanagari and the other
// Indic scripts, Arabic, Urdu's Nastaliq, Thai, Khmer, Myanmar), right-to-left order (Arabic, Hebrew, Persian, Urdu)
// and very large character sets (Chinese, Japanese, Korean). It shapes with go-text's HarfBuzz port, wraps with UAX#14
// line breaking and the bidi algorithm, and rasterises the outlines to a PNG with transparent paper, so the card on the
// headset shows exactly what a browser would. The fonts are Noto (SIL OFL), kept in content/fonts (tools/fetch_fonts.py).
package textimg

import (
	"bytes"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"os"
	"path/filepath"
	"sync"

	"github.com/go-text/render"
	"github.com/go-text/typesetting/di"
	"github.com/go-text/typesetting/font"
	"github.com/go-text/typesetting/language"
	"github.com/go-text/typesetting/shaping"
	"golang.org/x/image/math/fixed"
)

// Fallback draws what the script's own font has no glyph for (Latin words, digits, most punctuation).
const Fallback = "NotoSerif-Regular.ttf"

// Options for one drawing.
type Options struct {
	Font     string      // file in the font directory, e.g. NotoSerifDevanagari-Regular.ttf
	Lang     string      // BCP 47 tag for the shaper ("hi", "ur", "ja"): it picks localised forms
	RTL      bool        // the paragraph direction (Arabic, Hebrew, Persian, Urdu)
	Width    int         // pixels; lines wrap to it
	Size     float32     // pixels per em
	Leading  float32     // line height as a multiple of the font's own (0: 1.15)
	MaxLines int         // 0: no limit
	Ink      color.NRGBA // the text colour; the paper is transparent
}

// Renderer holds parsed fonts. Safe for concurrent use (drawing is serialised: go-text faces keep caches).
type Renderer struct {
	Dir   string
	mu    sync.Mutex
	faces map[string]*font.Face
}

func New(dir string) *Renderer { return &Renderer{Dir: dir, faces: map[string]*font.Face{}} }

// Has reports whether a font file is present (a language whose font is missing is drawn as text by the headset instead).
func (r *Renderer) Has(file string) bool {
	_, err := os.Stat(filepath.Join(r.Dir, file))
	return err == nil
}

func (r *Renderer) face(file string) (*font.Face, error) {
	if f, ok := r.faces[file]; ok {
		return f, nil
	}
	fh, err := os.Open(filepath.Join(r.Dir, file))
	if err != nil {
		return nil, err
	}
	defer fh.Close()
	f, err := font.ParseTTF(fh)
	if err != nil {
		return nil, fmt.Errorf("%s: %w", file, err)
	}
	r.faces[file] = f
	return f, nil
}

type fontmap struct{ main, fallback *font.Face }

func (m fontmap) ResolveFace(r rune) *font.Face {
	if _, ok := m.main.NominalGlyph(r); ok || m.fallback == nil {
		return m.main
	}
	if _, ok := m.fallback.NominalGlyph(r); ok {
		return m.fallback
	}
	return m.main
}

// Draw returns the text as an image exactly as tall as its lines (and as wide as Width).
func (r *Renderer) Draw(text string, o Options) (*image.NRGBA, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	main, err := r.face(o.Font)
	if err != nil {
		return nil, err
	}
	fb, _ := r.face(Fallback)
	fm := fontmap{main, fb}
	if o.Width <= 0 || o.Size <= 0 {
		return nil, fmt.Errorf("width and size must be positive")
	}
	if o.Leading == 0 {
		o.Leading = 1.15
	}
	dir := di.DirectionLTR
	if o.RTL {
		dir = di.DirectionRTL
	}
	size := fixed.Int26_6(o.Size * 64)
	var shaper shaping.HarfbuzzShaper
	var seg shaping.Segmenter
	var wrapper shaping.LineWrapper
	type laid struct {
		runs          shaping.Line
		width         int
		ascent, depth int
	}
	var lines []laid
	for _, para := range splitLines(text) {
		runes := []rune(para)
		if len(runes) == 0 {
			lines = append(lines, laid{ascent: int(o.Size * 0.8), depth: int(o.Size * 0.3)})
			continue
		}
		in := shaping.Input{Text: runes, RunStart: 0, RunEnd: len(runes), Direction: dir, Face: main, Size: size, Language: language.NewLanguage(o.Lang)}
		var outs []shaping.Output
		for _, run := range seg.Split(in, fm) {
			outs = append(outs, shaper.Shape(run))
		}
		wrapped, _ := wrapper.WrapParagraph(shaping.WrapConfig{Direction: dir, BreakPolicy: shaping.WhenNecessary}, o.Width, runes, shaping.NewSliceIterator(outs))
		for _, ln := range wrapped {
			l := laid{runs: append(shaping.Line(nil), ln...)}
			sortVisual(l.runs)
			for _, run := range l.runs {
				l.width += run.Advance.Round()
				if a := run.LineBounds.Ascent.Ceil(); a > l.ascent {
					l.ascent = a
				}
				if d := (-run.LineBounds.Descent).Ceil(); d > l.depth {
					l.depth = d
				}
			}
			lines = append(lines, l)
			if o.MaxLines > 0 && len(lines) >= o.MaxLines {
				break
			}
		}
		if o.MaxLines > 0 && len(lines) >= o.MaxLines {
			break
		}
	}
	h := 0
	for _, l := range lines {
		h += int(float32(l.ascent+l.depth) * o.Leading)
	}
	if h == 0 {
		h = 1
	}
	img := image.NewNRGBA(image.Rect(0, 0, o.Width, h))
	pen := &render.Renderer{FontSize: o.Size, PixScale: 1, Color: o.Ink}
	y := 0
	for _, l := range lines {
		lh := int(float32(l.ascent+l.depth) * o.Leading)
		base := y + (lh-(l.ascent+l.depth))/2 + l.ascent
		x := 0
		if o.RTL {
			x = o.Width - l.width
			if x < 0 {
				x = 0
			}
		}
		for _, run := range l.runs {
			x = pen.DrawShapedRunAt(run, img, x, base)
		}
		y += lh
	}
	return img, nil
}

// PNG encodes an image (best compression: these go over the network to the headset).
func PNG(img image.Image) ([]byte, error) {
	var b bytes.Buffer
	enc := png.Encoder{CompressionLevel: png.BestCompression}
	if err := enc.Encode(&b, img); err != nil {
		return nil, err
	}
	return b.Bytes(), nil
}

func splitLines(s string) []string {
	var out []string
	start := 0
	for i, c := range s {
		if c == '\n' {
			out = append(out, s[start:i])
			start = i + 1
		}
	}
	return append(out, s[start:])
}

func sortVisual(l shaping.Line) {
	for i := 1; i < len(l); i++ {
		for j := i; j > 0 && l[j].VisualIndex < l[j-1].VisualIndex; j-- {
			l[j], l[j-1] = l[j-1], l[j]
		}
	}
}

// Crop trims an image to its ink, with pad pixels of paper kept round it.
func Crop(img *image.NRGBA, pad int) *image.NRGBA {
	b := img.Bounds()
	minX, minY, maxX, maxY := b.Max.X, b.Max.Y, b.Min.X-1, b.Min.Y-1
	for y := b.Min.Y; y < b.Max.Y; y++ {
		for x := b.Min.X; x < b.Max.X; x++ {
			if img.NRGBAAt(x, y).A > 0 {
				minX, minY, maxX, maxY = min(minX, x), min(minY, y), max(maxX, x), max(maxY, y)
			}
		}
	}
	if maxX < minX {
		return image.NewNRGBA(image.Rect(0, 0, 1, 1))
	}
	r := image.Rect(max(b.Min.X, minX-pad), max(b.Min.Y, minY-pad), min(b.Max.X, maxX+pad+1), min(b.Max.Y, maxY+pad+1))
	out := image.NewNRGBA(image.Rect(0, 0, r.Dx(), r.Dy()))
	for y := 0; y < r.Dy(); y++ {
		copy(out.Pix[y*out.Stride:y*out.Stride+r.Dx()*4], img.Pix[(r.Min.Y+y)*img.Stride+r.Min.X*4:(r.Min.Y+y)*img.Stride+r.Max.X*4])
	}
	return out
}
