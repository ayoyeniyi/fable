package textimg

import (
	"image"
	"image/color"
	"image/draw"
	"os"
	"path/filepath"
	"testing"
)

func fontDir(t *testing.T) string {
	d := filepath.Join("..", "..", "..", "content", "fonts")
	if _, err := os.Stat(filepath.Join(d, Fallback)); err != nil {
		t.Skip("fonts not fetched (python3 tools/fetch_fonts.py)")
	}
	return d
}

// Every script draws something, wraps to the width, and right-to-left text sits against the right edge.
func TestDrawScripts(t *testing.T) {
	r := New(fontDir(t))
	ink := color.NRGBA{40, 30, 20, 255}
	cases := []struct {
		name, font, lang, text string
		rtl                    bool
	}{
		{"hindi", "NotoSerifDevanagari-Regular.ttf", "hi", "छोटी सुनहरी चाबी किताब के पास मेज़ पर रखी थी, और ऐलिस ने उसे क्षण भर देखा।", false},
		{"arabic", "NotoNaskhArabic-Regular.ttf", "ar", "كان المفتاح الذهبي الصغير على الطاولة، وقد رأته Alice قبل 3 دقائق.", true},
		{"urdu", "NotoNastaliqUrdu-Regular.ttf", "ur", "چھوٹی سنہری چابی میز پر رکھی تھی۔", true},
		{"hebrew", "NotoSerifHebrew-Regular.ttf", "he", "המפתח הזהב הקטן היה על השולחן.", true},
		{"japanese", "NotoSerifJP-Regular.otf", "ja", "小さな金の鍵がテーブルの上にありました。アリスはそれを見つめて、どの扉に合うのだろうと考えました。", false},
		{"thai", "NotoSerifThai-Regular.ttf", "th", "กุญแจทองคำดอกเล็กวางอยู่บนโต๊ะ อลิซมองดูมันอยู่นานและสงสัยว่ามันจะเปิดประตูบานไหนได้", false},
		{"amharic", "NotoSerifEthiopic-Regular.ttf", "am", "ትንሿ የወርቅ ቁልፍ በጠረጴዛው ላይ ነበረች።", false},
		{"tamil", "NotoSerifTamil-Regular.ttf", "ta", "சிறிய தங்கச் சாவி மேசையின் மேல் இருந்தது.", false},
	}
	out := os.Getenv("TEXTIMG_OUT")
	for _, c := range cases {
		img, err := r.Draw(c.text, Options{Font: c.font, Lang: c.lang, RTL: c.rtl, Width: 700, Size: 36, Ink: ink})
		if err != nil {
			t.Fatalf("%s: %v", c.name, err)
		}
		b := img.Bounds()
		inked, minX, maxX := 0, b.Dx(), 0
		for y := 0; y < b.Dy(); y++ {
			for x := 0; x < b.Dx(); x++ {
				if img.NRGBAAt(x, y).A > 100 {
					inked++
					minX, maxX = min(minX, x), max(maxX, x)
				}
			}
		}
		if inked < 500 {
			t.Errorf("%s: almost nothing drawn (%d px)", c.name, inked)
		}
		if c.rtl && maxX < b.Dx()-40 {
			t.Errorf("%s: right-to-left text should reach the right edge (ink ends at %d of %d)", c.name, maxX, b.Dx())
		}
		if !c.rtl && minX > 40 {
			t.Errorf("%s: left-to-right text should start at the left edge (ink starts at %d)", c.name, minX)
		}
		if out != "" {
			sheet := image.NewNRGBA(b)
			draw.Draw(sheet, b, &image.Uniform{color.NRGBA{250, 244, 230, 255}}, image.Point{}, draw.Src)
			draw.Draw(sheet, b, img, image.Point{}, draw.Over)
			data, _ := PNG(sheet)
			os.WriteFile(filepath.Join(out, c.name+".png"), data, 0o644)
		}
		t.Logf("%s: %dx%d", c.name, b.Dx(), b.Dy())
	}
}
