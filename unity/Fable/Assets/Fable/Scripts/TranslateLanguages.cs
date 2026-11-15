// The languages Translate offers, in one place on the headset. The preparation service keeps the same list in
// interpreter/internal/server/languages.go (its test TestLanguagesMatchHeadset reads this file and fails if they differ).
//
// drawn: the headset cannot show this script as text (it needs shaping or right-to-left order, which TextMeshPro does
// not do, or a CJK font of tens of megabytes), so the service sends the translation drawn as a picture
// (interpreter/internal/textimg) and the picker shows the native name from LanguageNames.png. Every other language is
// shown in the book's typeface, EB Garamond, which covers Latin (Vietnamese, Hausa and Igbo included), Cyrillic and
// Greek. The reader's choice is Prefs.TranslateTo (a code); the last few are Prefs.TranslateRecent.
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Fable
{
    public static class TranslateLanguages
    {
        public class Language
        {
            public string Code, Name, Native; public bool Drawn, Rtl;
            public override string ToString() => Name;
        }

        static Language L(string code, string name, string native, bool drawn = false, bool rtl = false) => new() { Code = code, Name = name, Native = native, Drawn = drawn, Rtl = rtl };

        /// Ordered by English name; the picker puts the reader's likely choices first (Ordered).
        public static readonly Language[] All =
        {
            L("af", "Afrikaans", "Afrikaans"),
            L("am", "Amharic", "አማርኛ", drawn: true),
            L("ar", "Arabic", "العربية", drawn: true, rtl: true),
            L("bn", "Bengali", "বাংলা", drawn: true),
            L("ny", "Chichewa", "Chicheŵa"),
            L("zh", "Chinese (Simplified)", "简体中文", drawn: true),
            L("zh-Hant", "Chinese (Traditional)", "繁體中文", drawn: true),
            L("cs", "Czech", "Čeština"),
            L("da", "Danish", "Dansk"),
            L("nl", "Dutch", "Nederlands"),
            L("fil", "Filipino", "Filipino"),
            L("fi", "Finnish", "Suomi"),
            L("fr", "French", "Français"),
            L("de", "German", "Deutsch"),
            L("el", "Greek", "Ελληνικά"),
            L("gu", "Gujarati", "ગુજરાતી", drawn: true),
            L("ha", "Hausa", "Hausa"),
            L("he", "Hebrew", "עברית", drawn: true, rtl: true),
            L("hi", "Hindi", "हिन्दी", drawn: true),
            L("hu", "Hungarian", "Magyar"),
            L("ig", "Igbo", "Asụsụ Igbo"),
            L("id", "Indonesian", "Bahasa Indonesia"),
            L("nd", "isiNdebele", "isiNdebele"),
            L("xh", "isiXhosa", "isiXhosa"),
            L("zu", "isiZulu", "isiZulu"),
            L("it", "Italian", "Italiano"),
            L("ja", "Japanese", "日本語", drawn: true),
            L("kn", "Kannada", "ಕನ್ನಡ", drawn: true),
            L("rw", "Kinyarwanda", "Ikinyarwanda"),
            L("ko", "Korean", "한국어", drawn: true),
            L("ms", "Malay", "Bahasa Melayu"),
            L("ml", "Malayalam", "മലയാളം", drawn: true),
            L("mr", "Marathi", "मराठी", drawn: true),
            L("ne", "Nepali", "नेपाली", drawn: true),
            L("no", "Norwegian", "Norsk"),
            L("fa", "Persian", "فارسی", drawn: true, rtl: true),
            L("pl", "Polish", "Polski"),
            L("pt", "Portuguese", "Português"),
            L("pa", "Punjabi", "ਪੰਜਾਬੀ", drawn: true),
            L("ro", "Romanian", "Română"),
            L("ru", "Russian", "Русский"),
            L("sn", "Shona", "chiShona"),
            L("so", "Somali", "Soomaali"),
            L("es", "Spanish", "Español"),
            L("sw", "Swahili", "Kiswahili"),
            L("sv", "Swedish", "Svenska"),
            L("ta", "Tamil", "தமிழ்", drawn: true),
            L("te", "Telugu", "తెలుగు", drawn: true),
            L("th", "Thai", "ไทย", drawn: true),
            L("tr", "Turkish", "Türkçe"),
            L("uk", "Ukrainian", "Українська"),
            L("ur", "Urdu", "اردو", drawn: true, rtl: true),
            L("vi", "Vietnamese", "Tiếng Việt"),
            L("yo", "Yoruba", "Èdè Yorùbá", drawn: true),
        };

        public static Language Find(string codeOrName)
        {
            if (string.IsNullOrEmpty(codeOrName)) return null;
            foreach (var l in All) if (string.Equals(l.Code, codeOrName, StringComparison.OrdinalIgnoreCase) || string.Equals(l.Name, codeOrName, StringComparison.OrdinalIgnoreCase)) return l;
            return null;
        }

        /// The headset's own language, when Translate offers it and it is not English; else null.
        public static Language System()
        {
            string code = null;
#if UNITY_ANDROID && !UNITY_EDITOR
            // the Quest's locale names more languages than Application.systemLanguage does
            try { using var locale = new AndroidJavaClass("java.util.Locale"); using var d = locale.CallStatic<AndroidJavaObject>("getDefault"); code = d.Call<string>("getLanguage"); if (code == "zh") code = d.Call<string>("getScript") == "Hant" || d.Call<string>("getCountry") is "TW" or "HK" or "MO" ? "zh-Hant" : "zh"; if (code == "nb" || code == "nn") code = "no"; if (code == "tl") code = "fil"; }
            catch (Exception) { code = null; }
#endif
            code ??= Application.systemLanguage switch
            {
                SystemLanguage.Afrikaans => "af", SystemLanguage.Arabic => "ar", SystemLanguage.Chinese or SystemLanguage.ChineseSimplified => "zh",
                SystemLanguage.ChineseTraditional => "zh-Hant", SystemLanguage.Czech => "cs", SystemLanguage.Danish => "da", SystemLanguage.Dutch => "nl",
                SystemLanguage.Finnish => "fi", SystemLanguage.French => "fr", SystemLanguage.German => "de", SystemLanguage.Greek => "el",
                SystemLanguage.Hebrew => "he", SystemLanguage.Hindi => "hi", SystemLanguage.Hungarian => "hu", SystemLanguage.Indonesian => "id",
                SystemLanguage.Italian => "it", SystemLanguage.Japanese => "ja", SystemLanguage.Korean => "ko", SystemLanguage.Norwegian => "no",
                SystemLanguage.Polish => "pl", SystemLanguage.Portuguese => "pt", SystemLanguage.Romanian => "ro", SystemLanguage.Russian => "ru",
                SystemLanguage.Spanish => "es", SystemLanguage.Swedish => "sv", SystemLanguage.Thai => "th", SystemLanguage.Turkish => "tr",
                SystemLanguage.Ukrainian => "uk", SystemLanguage.Vietnamese => "vi",
                _ => null,
            };
            return Find(code);
        }

        /// The headset's language when it is on the list and not English; otherwise Spanish.
        public static Language Default() => System() ?? Find("es");

        /// The reader's choice (a code, or an English name from before codes), or Default() while they have not made one.
        public static Language Current() => Find(ProgressStore.LoadPrefs().TranslateTo) ?? Default();

        /// Choose a language: saved, and put at the front of the recent ones (at most four kept).
        public static void Choose(string code)
        {
            var l = Find(code); if (l == null) return;
            var p = ProgressStore.LoadPrefs();
            p.TranslateTo = l.Code;
            p.TranslateRecent ??= new List<string>();
            p.TranslateRecent.Remove(l.Code); p.TranslateRecent.Insert(0, l.Code);
            if (p.TranslateRecent.Count > 4) p.TranslateRecent.RemoveRange(4, p.TranslateRecent.Count - 4);
            ProgressStore.SavePrefs(p);
            Debug.Log($"[Fable] translate: language {l.Name} ({l.Code})");
        }

        /// Why a language is near the top of the picker: "on this headset", "recent", or null.
        public static string Why(Language l)
        {
            if (l == System()) return "this headset’s language";
            var p = ProgressStore.LoadPrefs();
            return p.TranslateRecent != null && p.TranslateRecent.Contains(l.Code) ? "used recently" : null;
        }

        /// The picker's order: the current choice, the headset's language, the recent ones, then every other one A to Z.
        public static List<Language> Ordered()
        {
            var p = ProgressStore.LoadPrefs();
            var first = new List<Language> { Current(), System() };
            if (p.TranslateRecent != null) foreach (var c in p.TranslateRecent) first.Add(Find(c));
            var list = first.Where(l => l != null).Distinct().ToList();
            list.AddRange(All.Where(l => !list.Contains(l)));
            return list;
        }

        /// How many of Ordered() are the reader's likely choices (shown first, apart from the A to Z).
        public static int SuggestedCount() { var o = Ordered(); int n = 0; var p = ProgressStore.LoadPrefs(); foreach (var l in o) { if (l == Current() || l == System() || (p.TranslateRecent != null && p.TranslateRecent.Contains(l.Code))) n++; else break; } return n; }
    }
}
