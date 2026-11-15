// The language picker: a card over the page with every language Translate offers, as large targets for a pointing
// hand. Opened from the translation card ("to Spanish ▼") and from the bar's settings ("translate to").
//
//   the reader's likely choices first   the current one (marked), the headset's own language, the recent ones
//   then every other language A to Z    English name, and the language's own name under it
//   ‹ earlier / later ›                 pages of 18; no scrolling to aim at
//   pinch a language                    chosen, saved, and the card closes; pinch off the card, or close ×, to keep
//                                       the language as it was
// Native names in scripts the page's font cannot show (Arabic, Hindi, Japanese, ...) are pictures cut from
// Resources/LanguageNames.png, drawn once by `fable-interpreter render-names` with the Noto fonts.
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Fable
{
    public class LanguagePicker : MonoBehaviour
    {
        public const int Cols = 3, Rows = 6, Per = Cols * Rows;
        static readonly Color Paper = new(0.985f, 0.96f, 0.90f, 0.995f), Ink = new(0.16f, 0.12f, 0.08f), Soft = new(0.42f, 0.34f, 0.24f), Accent = new(0.55f, 0.36f, 0.08f),
            TileC = new(1f, 0.985f, 0.95f, 1f), Lit = new(0.99f, 0.88f, 0.60f, 1f), Chosen = new(0.96f, 0.80f, 0.45f, 1f);

        RectTransform page, card, body; PagePointer pointer; ReaderController input; TMP_FontAsset font;
        readonly List<(RectTransform rt, Action act, string key)> targets = new();
        readonly List<GameObject> built = new();
        Action<TranslateLanguages.Language> onChosen; Action onClosed;
        List<TranslateLanguages.Language> order; int pageIndex, suggested;
        string chosenCode;

        public bool IsOpen => card && card.gameObject.activeSelf;
        public int Page => pageIndex;
        public int Pages => order == null ? 1 : Mathf.Max(1, Mathf.CeilToInt(order.Count / (float)Per));

        /// The page's picker (one per page panel), made on first use.
        public static LanguagePicker For(RectTransform page, PagePointer pointer, ReaderController input, TMP_FontAsset font)
        {
            var p = page.GetComponent<LanguagePicker>() ? page.GetComponent<LanguagePicker>() : page.gameObject.AddComponent<LanguagePicker>();
            p.page = page; p.pointer = pointer; p.input = input; p.font = font;
            return p;
        }

        void Build()
        {
            if (card) return;
            card = new GameObject("LanguagePicker", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>(); card.SetParent(page, false);
            card.anchorMin = card.anchorMax = card.pivot = new Vector2(0.5f, 1); card.anchoredPosition = new Vector2(0, -40); card.sizeDelta = new Vector2(590, 700);
            card.localPosition += new Vector3(0, 0, -4f);   // in front of the book menu and the highlight card
            var bg = card.GetComponent<Image>(); bg.color = Paper; bg.raycastTarget = false;
            var o = card.gameObject.AddComponent<Outline>(); o.effectColor = new Color(0.45f, 0.33f, 0.18f, 0.9f); o.effectDistance = new Vector2(2, -2);
            body = new GameObject("Body", typeof(RectTransform)).GetComponent<RectTransform>(); body.SetParent(card, false);
            body.anchorMin = Vector2.zero; body.anchorMax = Vector2.one; body.offsetMin = body.offsetMax = Vector2.zero;
            card.gameObject.SetActive(false);
        }

        /// Show the picker. chosen gets the language pinched (already saved as the reader's choice); closed runs when the
        /// card is closed without a choice.
        public void Open(Action<TranslateLanguages.Language> chosen, Action closed = null)
        {
            Build();
            onChosen = chosen; onClosed = closed;
            order = TranslateLanguages.Ordered(); suggested = TranslateLanguages.SuggestedCount();
            chosenCode = TranslateLanguages.Current().Code; pageIndex = 0;
            card.gameObject.SetActive(true); card.SetAsLastSibling();
            if (input && !input.Claimers.Contains(Claim)) input.Claimers.Insert(0, Claim);
            Rebuild();
            Debug.Log($"[Fable] language picker: open ({order.Count} languages, {suggested} suggested, current {chosenCode})");
        }

        public void Close() { Close(true); }

        void Close(bool cancelled)
        {
            if (!IsOpen) return;
            card.gameObject.SetActive(false);
            if (input) input.Claimers.Remove(Claim);
            var c = onClosed; onChosen = null; onClosed = null;
            if (cancelled) c?.Invoke();
        }

        void OnDestroy() { if (input) input.Claimers.Remove(Claim); }

        // ---------------------------------------------------------------- building

        void Rebuild()
        {
            foreach (var g in built) if (g) Destroy(g); built.Clear(); targets.Clear();
            Text("Translate into", 26, FontStyles.SmallCaps, Accent, TextAlignmentOptions.Left, new Vector2(-60, 316), new Vector2(430, 40));
            Button("close ×", new Vector2(230, 316), new Vector2(100, 40), 17, "close", Close);
            Text(pageIndex == 0 && suggested > 0 ? "Your likely choices first, then every language A to Z. Pinch one." : "Pinch a language.", 15, FontStyles.Italic, Soft, TextAlignmentOptions.Left, new Vector2(0, 276), new Vector2(530, 26));
            const float tw = 176, th = 76, gap = 8;
            for (int k = 0; k < Per; k++)
            {
                int i = pageIndex * Per + k; if (i >= order.Count) break;
                int c = k % Cols, r = k / Cols;
                Tile(order[i], i < suggested, new Vector2(-(tw + gap) + c * (tw + gap), 222 - r * (th + gap)), new Vector2(tw, th));
            }
            int pages = Pages;
            if (pageIndex > 0) Button("‹ earlier", new Vector2(-200, -318), new Vector2(150, 44), 17, "prev", () => { pageIndex--; Rebuild(); });
            if (pageIndex < pages - 1) Button("later ›", new Vector2(200, -318), new Vector2(150, 44), 17, "next", () => { pageIndex++; Rebuild(); });
            int a = pageIndex * Per, b = Mathf.Min(order.Count, a + Per) - 1;
            var from = order[Mathf.Max(a, pageIndex == 0 ? suggested : a)].Name; var to = order[b].Name;
            Text($"{pageIndex + 1} of {pages}\n<size=80%>{(from == to ? from : from.Substring(0, 1) + " to " + to.Substring(0, 1))}</size>", 15, FontStyles.SmallCaps, Soft, TextAlignmentOptions.Center, new Vector2(0, -318), new Vector2(160, 44)).lineSpacing = -18;
        }

        void Tile(TranslateLanguages.Language l, bool isSuggested, Vector2 pos, Vector2 size)
        {
            bool current = l.Code == chosenCode;
            var tile = Img("Lang " + l.Code, pos, size, current ? Chosen : TileC);
            var o = tile.gameObject.AddComponent<Outline>(); o.effectColor = current ? new Color(0.55f, 0.36f, 0.08f, 1f) : new Color(0.55f, 0.45f, 0.30f, 0.6f); o.effectDistance = current ? new Vector2(2.5f, -2.5f) : new Vector2(1.5f, -1.5f);
            var name = Text(l.Name, l.Name.Length > 16 ? 15.5f : 18, FontStyles.Normal, Ink, TextAlignmentOptions.Center, new Vector2(pos.x, pos.y + 18), new Vector2(size.x - 8, 26));
            name.textWrappingMode = TextWrappingModes.NoWrap; name.overflowMode = TextOverflowModes.Ellipsis;
            var native = new Vector2(pos.x, pos.y - 6); var nativeBox = new Vector2(size.x - 16, 26);
            var sprite = l.Drawn ? NativeSprite(l.Code) : null;
            if (sprite)
            {
                // drawn white, tinted like the italic native names beside it; a little smaller, as Noto's scripts run large
                var im = Img("Native " + l.Code, native, new Vector2(size.x - 36, 22), Soft); im.sprite = sprite; im.preserveAspect = true;
            }
            else if (l.Native != l.Name)
            {
                var t = Text(l.Native, 16, FontStyles.Italic, Soft, TextAlignmentOptions.Center, native, nativeBox); t.textWrappingMode = TextWrappingModes.NoWrap; t.overflowMode = TextOverflowModes.Ellipsis;
            }
            string note = current ? "• chosen •" : isSuggested ? TranslateLanguages.Why(l) : null;
            if (note != null) Text(note, 12.5f, FontStyles.SmallCaps, Accent, TextAlignmentOptions.Center, new Vector2(pos.x, pos.y - 28), new Vector2(size.x - 8, 18));
            var code = l.Code;
            targets.Add((tile.rectTransform, () => Pick(code), "lang:" + code));
        }

        void Pick(string code)
        {
            var l = TranslateLanguages.Find(code); if (l == null) return;
            TranslateLanguages.Choose(code);
            var cb = onChosen;
            Close(false);
            cb?.Invoke(l);
        }

        // ---------------------------------------------------------------- the native names atlas

        static Texture2D atlas; static Dictionary<string, Rect> rects; static readonly Dictionary<string, Sprite> sprites = new();

        static Sprite NativeSprite(string code)
        {
            if (sprites.TryGetValue(code, out var s)) return s;
            if (rects == null)
            {
                rects = new Dictionary<string, Rect>();
                atlas = Resources.Load<Texture2D>("LanguageNames");
                var js = Resources.Load<TextAsset>("LanguageNames");
                if (atlas && js)
                    try
                    {
                        var j = JObject.Parse(js.text); int h = (int)j["height"];
                        foreach (var p in (JObject)j["names"])
                        {
                            var r = p.Value; int x = (int)r["X"], y = (int)r["Y"], w = (int)r["W"], hh = (int)r["H"];
                            rects[p.Key] = new Rect(x, h - y - hh, w, hh);   // the atlas's rows count from the top; Unity's from the bottom
                        }
                    }
                    catch (Exception e) { Debug.LogWarning($"[Fable] language names atlas unreadable: {e.Message}"); }
                else Debug.LogWarning("[Fable] Resources/LanguageNames.png or .json is missing (fable-interpreter render-names)");
            }
            s = rects.TryGetValue(code, out var rc) ? Sprite.Create(atlas, rc, new Vector2(0.5f, 0.5f), 100f) : null;
            sprites[code] = s;
            return s;
        }

        // ---------------------------------------------------------------- pointing

        bool Claim(bool right)
        {
            if (!IsOpen || !pointer) return false;
            foreach (var (rt, act, key) in targets.ToList()) if (pointer.Over(right, rt)) { Debug.Log($"[Fable] language picker: {key}"); act?.Invoke(); return true; }
            if (!pointer.OnPage(right, out _)) return false;   // the bar or the room: theirs
            if (!pointer.Over(right, card)) Close();
            return true;
        }

        void Update()
        {
            if (!IsOpen || !pointer) return;
            foreach (var (rt, _, key) in targets)
            {
                if (!rt) continue; var img = rt.GetComponent<Image>(); if (!img) continue;
                bool lit = pointer.Over(true, rt) || pointer.Over(false, rt);
                var c = lit ? Lit : key == "lang:" + chosenCode ? Chosen : key.StartsWith("lang:") ? TileC : new Color(0.99f, 0.96f, 0.89f, 1f);
                if (img.color != c) img.color = c;
            }
        }

        /// Test hook: press a control by its key ("lang:fr", "next", "prev", "close").
        public string Press(string key)
        {
            var t = targets.Find(x => x.key == key);
            if (t.rt == null) return "no control " + key + "; have: " + string.Join(", ", targets.Select(x => x.key));
            t.act?.Invoke(); return Describe();
        }

        /// Test hook: the screen-space centre of a control, to aim a test ray at.
        public Vector3 World(string key) { var t = targets.Find(x => x.key == key); return t.rt ? t.rt.TransformPoint(t.rt.rect.center) : Vector3.zero; }

        public string Describe() => !IsOpen ? "language picker closed" : $"language picker page {pageIndex + 1}/{Pages}, current {chosenCode}: " + string.Join(", ", targets.Where(t => t.key.StartsWith("lang:")).Select(t => t.key.Substring(5)));

        // ---------------------------------------------------------------- small builders

        Image Img(string name, Vector2 pos, Vector2 size, Color c)
        {
            var im = new GameObject(name, typeof(RectTransform)).AddComponent<Image>(); im.transform.SetParent(body, false); im.color = c; im.raycastTarget = false;
            im.rectTransform.anchoredPosition = pos; im.rectTransform.sizeDelta = size; built.Add(im.gameObject); return im;
        }

        TMP_Text Text(string s, float size, FontStyles style, Color c, TextAlignmentOptions align, Vector2 pos, Vector2 box)
        {
            var t = new GameObject("Text", typeof(RectTransform)).AddComponent<TextMeshProUGUI>(); t.transform.SetParent(body, false);
            if (font) t.font = font; t.text = s; t.fontSize = size; t.fontStyle = style; t.color = c; t.alignment = align; t.raycastTarget = false; t.richText = true;
            t.textWrappingMode = TextWrappingModes.Normal; t.rectTransform.anchoredPosition = pos; t.rectTransform.sizeDelta = box; built.Add(t.gameObject); return t;
        }

        RectTransform Button(string label, Vector2 pos, Vector2 size, float fs, string key, Action act)
        {
            var img = Img("Btn " + label, pos, size, new Color(0.99f, 0.96f, 0.89f, 1f));
            var o = img.gameObject.AddComponent<Outline>(); o.effectColor = new Color(0.45f, 0.33f, 0.18f, 0.9f); o.effectDistance = new Vector2(1.5f, -1.5f);
            var t = new GameObject("Text", typeof(RectTransform)).AddComponent<TextMeshProUGUI>(); t.transform.SetParent(img.transform, false);
            if (font) t.font = font; t.text = label; t.fontSize = fs; t.fontStyle = FontStyles.SmallCaps; t.color = Ink; t.alignment = TextAlignmentOptions.Center; t.raycastTarget = false;
            t.rectTransform.anchorMin = Vector2.zero; t.rectTransform.anchorMax = Vector2.one; t.rectTransform.offsetMin = t.rectTransform.offsetMax = Vector2.zero;
            targets.Add((img.rectTransform, act, key));
            return img.rectTransform;
        }
    }
}
