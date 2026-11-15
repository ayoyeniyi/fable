package server

import "strings"

// Language is one language Translate offers. The headset keeps the same list, in the same order, in
// unity/Fable/Assets/Fable/Scripts/TranslateLanguages.cs (TestLanguagesMatchHeadset checks the two agree).
//
// Font says how the headset shows a translation. Empty: as text in the book's typeface (EB Garamond, through
// TextMeshPro), which covers Latin, Cyrillic and Greek. Otherwise the server draws the translation with that Noto font
// (internal/textimg) and the card shows the picture: scripts that need shaping or right-to-left order, which
// TextMeshPro cannot do, and the CJK scripts, whose fonts would add tens of megabytes to the app.
type Language struct {
	Code   string // BCP 47; also the cache folder
	Name   string // English name, shown on the headset and accepted in requests
	Native string // the language's own name for itself, shown under the English one in the picker
	Prompt string // how the model is told the language, when the name alone is ambiguous
	Font   string // file in content/fonts for languages drawn by the server; "" = shown as text
	RTL    bool
}

// Languages are Translate's languages: widely spoken ones, and those Fable's first readers asked for (Shona,
// isiNdebele, Swahili). Ordered by English name; the picker puts the reader's likely choices first.
var Languages = []Language{
	{Code: "af", Name: "Afrikaans", Native: "Afrikaans"},
	{Code: "am", Name: "Amharic", Native: "አማርኛ", Font: "NotoSerifEthiopic-Regular.ttf"},
	{Code: "ar", Name: "Arabic", Native: "العربية", Prompt: "Arabic (Modern Standard)", Font: "NotoNaskhArabic-Regular.ttf", RTL: true},
	{Code: "bn", Name: "Bengali", Native: "বাংলা", Font: "NotoSerifBengali-Regular.ttf"},
	{Code: "ny", Name: "Chichewa", Native: "Chicheŵa", Prompt: "Chichewa (Nyanja, as written in Malawi)"},
	{Code: "zh", Name: "Chinese (Simplified)", Native: "简体中文", Prompt: "Chinese (Mandarin, written in Simplified characters)", Font: "NotoSerifSC-Regular.otf"},
	{Code: "zh-Hant", Name: "Chinese (Traditional)", Native: "繁體中文", Prompt: "Chinese (Mandarin, written in Traditional characters)", Font: "NotoSerifTC-Regular.otf"},
	{Code: "cs", Name: "Czech", Native: "Čeština"},
	{Code: "da", Name: "Danish", Native: "Dansk"},
	{Code: "nl", Name: "Dutch", Native: "Nederlands"},
	{Code: "fil", Name: "Filipino", Native: "Filipino", Prompt: "Filipino (Tagalog)"},
	{Code: "fi", Name: "Finnish", Native: "Suomi"},
	{Code: "fr", Name: "French", Native: "Français"},
	{Code: "de", Name: "German", Native: "Deutsch"},
	{Code: "el", Name: "Greek", Native: "Ελληνικά", Prompt: "Greek (Modern)"},
	{Code: "gu", Name: "Gujarati", Native: "ગુજરાતી", Font: "NotoSerifGujarati-Regular.ttf"},
	{Code: "ha", Name: "Hausa", Native: "Hausa", Prompt: "Hausa (in Latin script, with ɓ ɗ ƙ)"},
	{Code: "he", Name: "Hebrew", Native: "עברית", Font: "NotoSerifHebrew-Regular.ttf", RTL: true},
	{Code: "hi", Name: "Hindi", Native: "हिन्दी", Font: "NotoSerifDevanagari-Regular.ttf"},
	{Code: "hu", Name: "Hungarian", Native: "Magyar"},
	{Code: "ig", Name: "Igbo", Native: "Asụsụ Igbo"},
	{Code: "id", Name: "Indonesian", Native: "Bahasa Indonesia"},
	{Code: "nd", Name: "isiNdebele", Native: "isiNdebele", Prompt: "isiNdebele (Northern Ndebele, as spoken in Zimbabwe)"},
	{Code: "xh", Name: "isiXhosa", Native: "isiXhosa"},
	{Code: "zu", Name: "isiZulu", Native: "isiZulu"},
	{Code: "it", Name: "Italian", Native: "Italiano"},
	{Code: "ja", Name: "Japanese", Native: "日本語", Font: "NotoSerifJP-Regular.otf"},
	{Code: "kn", Name: "Kannada", Native: "ಕನ್ನಡ", Font: "NotoSerifKannada-Regular.ttf"},
	{Code: "rw", Name: "Kinyarwanda", Native: "Ikinyarwanda"},
	{Code: "ko", Name: "Korean", Native: "한국어", Font: "NotoSerifKR-Regular.otf"},
	{Code: "ms", Name: "Malay", Native: "Bahasa Melayu"},
	{Code: "ml", Name: "Malayalam", Native: "മലയാളം", Font: "NotoSerifMalayalam-Regular.ttf"},
	{Code: "mr", Name: "Marathi", Native: "मराठी", Font: "NotoSerifDevanagari-Regular.ttf"},
	{Code: "ne", Name: "Nepali", Native: "नेपाली", Font: "NotoSerifDevanagari-Regular.ttf"},
	{Code: "no", Name: "Norwegian", Native: "Norsk", Prompt: "Norwegian (Bokmål)"},
	{Code: "fa", Name: "Persian", Native: "فارسی", Prompt: "Persian (Farsi, as written in Iran)", Font: "NotoNaskhArabic-Regular.ttf", RTL: true},
	{Code: "pl", Name: "Polish", Native: "Polski"},
	{Code: "pt", Name: "Portuguese", Native: "Português"},
	{Code: "pa", Name: "Punjabi", Native: "ਪੰਜਾਬੀ", Prompt: "Punjabi (in Gurmukhi script)", Font: "NotoSerifGurmukhi-Regular.ttf"},
	{Code: "ro", Name: "Romanian", Native: "Română"},
	{Code: "ru", Name: "Russian", Native: "Русский"},
	{Code: "sn", Name: "Shona", Native: "chiShona"},
	{Code: "so", Name: "Somali", Native: "Soomaali"},
	{Code: "es", Name: "Spanish", Native: "Español"},
	{Code: "sw", Name: "Swahili", Native: "Kiswahili"},
	{Code: "sv", Name: "Swedish", Native: "Svenska"},
	{Code: "ta", Name: "Tamil", Native: "தமிழ்", Font: "NotoSerifTamil-Regular.ttf"},
	{Code: "te", Name: "Telugu", Native: "తెలుగు", Font: "NotoSerifTelugu-Regular.ttf"},
	{Code: "th", Name: "Thai", Native: "ไทย", Font: "NotoSerifThai-Regular.ttf"},
	{Code: "tr", Name: "Turkish", Native: "Türkçe"},
	{Code: "uk", Name: "Ukrainian", Native: "Українська"},
	{Code: "ur", Name: "Urdu", Native: "اردو", Font: "NotoNastaliqUrdu-Regular.ttf", RTL: true},
	{Code: "vi", Name: "Vietnamese", Native: "Tiếng Việt"},
	// Yoruba's tone marks stack over dotted vowels (ẹ́): combining marks TextMeshPro does not place reliably
	{Code: "yo", Name: "Yoruba", Native: "Èdè Yorùbá", Font: "NotoSerif-Regular.ttf"},
}

// FindLanguage resolves a code or an English name (case-insensitively); ok is false when it is not on the list.
func FindLanguage(s string) (Language, bool) {
	s = strings.TrimSpace(s)
	for _, l := range Languages {
		if strings.EqualFold(l.Code, s) || strings.EqualFold(l.Name, s) {
			return l, true
		}
	}
	return Language{}, false
}

// LanguageName resolves a code or a name to the list's English name; "" when it is not on the list.
func LanguageName(s string) string {
	if l, ok := FindLanguage(s); ok {
		return l.Name
	}
	return ""
}

// ForModel is how the language is named to Claude.
func (l Language) ForModel() string {
	if l.Prompt != "" {
		return l.Prompt
	}
	return l.Name
}
