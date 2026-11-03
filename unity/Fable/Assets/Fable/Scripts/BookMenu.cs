// The book's menu, opened from the bar under the page ("chapters", "rooms", "sound"): a card over the page.
//
//   chapters   one tile per chapter. Before a chapter is finished its tile is a padlock and "Chapter 3", nothing
//              else, whatever preparation has done. After: the experience's picture and title once it is ready;
//              "unlocked, preparing: <stage>" while it is not; the reason and "pinch to retry" if it failed; "no place
//              built for this chapter yet" if none fits. A locked chapter before the one being read can be marked
//              as already read (it asks first), for a reader resuming a book read elsewhere.
//   rooms      where this book can be read: its own room, the library
//   sound      music on or off, room sound off / quiet / normal, and the language Translate uses (saved in the
//              reader's preferences)
// Titles and pictures come only through ChapterExperiences.Title / Thumbnail, which refuse them for unfinished chapters.
using System;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Fable
{
    public class BookMenu : MonoBehaviour
    {
        public FlowController Flow;
        public string Tab { get; private set; }
        public bool IsOpen => card && card.gameObject.activeSelf;

        RectTransform page, card, body;
        readonly List<(RectTransform rt, Action act, string key)> targets = new();
        readonly List<GameObject> built = new();
        int chapterPage; string confirmKey; float confirmUntil;
        static Sprite lockSprite, openSprite;
        const int Cols = 3, Rows = 3, Per = Cols * Rows;
        static readonly Color Paper = new(0.985f, 0.96f, 0.90f, 0.99f), Ink = new(0.16f, 0.12f, 0.08f), Soft = new(0.42f, 0.34f, 0.24f), Accent = new(0.55f, 0.36f, 0.08f), Tile = new(1f, 0.985f, 0.95f, 1f), Lit = new(0.99f, 0.88f, 0.60f, 1f);
        TMP_FontAsset Font => Flow && Flow.Panel && Flow.Panel.Body ? Flow.Panel.Body.font : null;

        public void Init(FlowController flow)
        {
            Flow = flow; page = (RectTransform)flow.Panel.transform;
            card = new GameObject("BookMenu", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>(); card.SetParent(page, false);
            card.anchorMin = card.anchorMax = card.pivot = new Vector2(0.5f, 1); card.anchoredPosition = new Vector2(0, -40); card.sizeDelta = new Vector2(590, 700);
            card.localPosition += new Vector3(0, 0, -3f);
            var bg = card.GetComponent<Image>(); bg.color = Paper; bg.raycastTarget = false;
            var o = card.gameObject.AddComponent<Outline>(); o.effectColor = new Color(0.45f, 0.33f, 0.18f, 0.9f); o.effectDistance = new Vector2(2, -2);
            body = new GameObject("Body", typeof(RectTransform)).GetComponent<RectTransform>(); body.SetParent(card, false);
            body.anchorMin = Vector2.zero; body.anchorMax = Vector2.one; body.offsetMin = Vector2.zero; body.offsetMax = Vector2.zero;
            card.gameObject.SetActive(false);
            if (flow.Input && !flow.Input.Claimers.Contains(Claim)) flow.Input.Claimers.Insert(0, Claim);
            ChapterExperiences.Instance.Changed += OnChanged;
            GeneratedRooms.Instance.Changed += OnChanged;
        }

        void OnDestroy() { if (Flow && Flow.Input) Flow.Input.Claimers.Remove(Claim); if (ChapterExperiences.Instance) ChapterExperiences.Instance.Changed -= OnChanged; GeneratedRooms.Instance.Changed -= OnChanged; }
        void OnChanged() { if (IsOpen) Rebuild(); }

        public void Open(string tab)
        {
            Tab = tab; card.gameObject.SetActive(true); card.SetAsLastSibling();
            if (tab == "chapters" && Flow.Reader && Flow.Reader.Book != null) chapterPage = Mathf.Max(0, ChapterNumbers().FindIndex(c => c.index >= Flow.Reader.ChapterIndex)) / Per;
            Rebuild();
            Debug.Log($"[Fable] book menu: {tab}");
        }

        public void Close() { card.gameObject.SetActive(false); Tab = null; }

        // ---------------------------------------------------------------- building

        void Clear() { foreach (var g in built) if (g) Destroy(g); built.Clear(); targets.Clear(); }

        void Rebuild()
        {
            Clear();
            Text(body, Tab == "chapters" ? "Chapter experiences" : Tab == "rooms" ? "Reading rooms" : "Sound and translation", 26, FontStyles.SmallCaps, Accent, TextAlignmentOptions.Left, new Vector2(-60, 316), new Vector2(430, 40));
            Button(body, "close ×", new Vector2(230, 316), new Vector2(100, 40), 17, "close", Close);
            float x = -190;
            foreach (var t in new[] { "chapters", "rooms", "sound" })
            { var tt = t; var b = Button(body, t, new Vector2(x, 268), new Vector2(170, 38), 17, "tab:" + t, () => { Tab = tt; Rebuild(); }); if (t == Tab) b.GetComponent<Image>().color = Lit; x += 190; }
            if (Tab == "chapters") Chapters(); else if (Tab == "rooms") Rooms(); else Sound();
        }

        List<(int index, int number, Book.Chapter ch)> ChapterNumbers()
        {
            var list = new List<(int, int, Book.Chapter)>(); int n = 0;
            var b = Flow.Reader.Book;
            for (int i = 0; i < b.Chapters.Count; i++) if (b.Chapters[i].Kind == "chapter") list.Add((i, ++n, b.Chapters[i]));
            return list;
        }

        void Chapters()
        {
            var book = Flow.Reader.Book; var ce = ChapterExperiences.Instance;
            if (!ChapterExperiences.Supported.Contains(book.Slug))
            {
                Text(body, "Chapter experiences are prepared for Fable’s own four books. They are not available yet for books you add.\n\nYour progress through the chapters is still kept.", 19, FontStyles.Normal, Ink, TextAlignmentOptions.TopLeft, new Vector2(0, 120), new Vector2(520, 200));
                return;
            }
            var all = ChapterNumbers(); int pages = Mathf.Max(1, Mathf.CeilToInt(all.Count / (float)Per));
            chapterPage = Mathf.Clamp(chapterPage, 0, pages - 1);
            int ready = all.Count(c => ce.StateOf(c.ch.Id) == ChapterExperiences.State.Available);
            int locked = all.Count(c => ce.StateOf(c.ch.Id) == ChapterExperiences.State.Locked);
            Text(body, $"{ready} to step into · {all.Count - ready - locked} finished, not ready · {locked} locked until you finish them", 14, FontStyles.Italic, Soft, TextAlignmentOptions.Left, new Vector2(0, 228), new Vector2(530, 24));
            const float tw = 172, th = 150, gap = 10;
            for (int k = 0; k < Per; k++)
            {
                int i = chapterPage * Per + k; if (i >= all.Count) break;
                var (index, number, ch) = all[i];
                int c = k % Cols, r = k / Cols;
                var pos = new Vector2(-(tw + gap) + c * (tw + gap), 120 - r * (th + gap));
                ChapterTile(ch, number, index, pos, new Vector2(tw, th));
            }
            if (pages > 1)
            {
                if (chapterPage > 0) Button(body, "‹ earlier", new Vector2(-200, -318), new Vector2(150, 38), 16, "prev", () => { chapterPage--; Rebuild(); });
                if (chapterPage < pages - 1) Button(body, "later ›", new Vector2(200, -318), new Vector2(150, 38), 16, "next", () => { chapterPage++; Rebuild(); });
                Text(body, $"{chapterPage + 1} of {pages}", 15, FontStyles.SmallCaps, Soft, TextAlignmentOptions.Center, new Vector2(0, -318), new Vector2(120, 30));
            }
        }

        void ChapterTile(Book.Chapter ch, int number, int index, Vector2 pos, Vector2 size)
        {
            var ce = ChapterExperiences.Instance; var st = ce.StateOf(ch.Id);
            var key = "ch:" + ch.Id; Action act = null;
            var tile = Img(body, "Tile " + number, pos, size, Tile);
            var o = tile.gameObject.AddComponent<Outline>(); o.effectColor = new Color(0.55f, 0.45f, 0.30f, 0.6f); o.effectDistance = new Vector2(1.5f, -1.5f);
            var pic = new Vector2(pos.x, pos.y + 22); var picSize = new Vector2(size.x - 12, 92);
            string line2 = "";
            switch (st)
            {
                case ChapterExperiences.State.Locked:
                    Img(body, "Dark", pic, picSize, new Color(0.22f, 0.19f, 0.16f));
                    var l = Img(body, "Lock", pic, new Vector2(48, 48), new Color(0.93f, 0.86f, 0.70f)); l.sprite = LockSprite(false);
                    bool before = index < Flow.Reader.ChapterIndex;
                    if (before)
                    {
                        bool asking = confirmKey == key && Time.time < confirmUntil;
                        line2 = asking ? "pinch again to mark it read" : "read already? pinch to mark it read";
                        act = () =>
                        {
                            if (confirmKey == key && Time.time < confirmUntil) { confirmKey = null; ce.Complete(Flow.Reader.Book.Slug, ch.Id, "marked"); }
                            else { confirmKey = key; confirmUntil = Time.time + 5f; Rebuild(); }
                        };
                    }
                    break;
                case ChapterExperiences.State.Preparing:
                    Img(body, "Dark", pic, picSize, new Color(0.30f, 0.27f, 0.22f));
                    var u = Img(body, "Open", pic, new Vector2(48, 48), new Color(0.93f, 0.86f, 0.70f, 0.85f)); u.sprite = LockSprite(true);
                    line2 = "unlocked · " + ce.StageOf(ch.Id);
                    break;
                case ChapterExperiences.State.Available:
                    var tex = ce.Thumbnail(ch.Id);
                    var ri = new GameObject("Thumb", typeof(RectTransform)).AddComponent<RawImage>(); ri.transform.SetParent(body, false); built.Add(ri.gameObject);
                    ri.rectTransform.anchoredPosition = pic; ri.rectTransform.sizeDelta = picSize; ri.texture = tex; ri.raycastTarget = false;
                    line2 = $"<b>{ce.Title(ch.Id)}</b>";
                    act = () => { Close(); Flow.EnterExperience(ch.Id); };
                    break;
                case ChapterExperiences.State.Failed:
                    Img(body, "Dark", pic, picSize, new Color(0.35f, 0.22f, 0.18f));
                    line2 = "couldn’t be prepared · pinch to try again";
                    act = () => ce.Retry(ch.Id);
                    break;
                case ChapterExperiences.State.Unavailable:
                    Img(body, "Dark", pic, picSize, new Color(0.30f, 0.28f, 0.26f));
                    line2 = "no place built for this chapter yet";
                    break;
            }
            Text(body, $"Chapter {number}", 15, FontStyles.SmallCaps, Accent, TextAlignmentOptions.Left, new Vector2(pos.x, pos.y - 38), new Vector2(size.x - 12, 20));
            var t2 = Text(body, line2, 12.5f, FontStyles.Normal, Ink, TextAlignmentOptions.TopLeft, new Vector2(pos.x, pos.y - 60), new Vector2(size.x - 12, 32));
            t2.overflowMode = TextOverflowModes.Ellipsis; t2.lineSpacing = -12;
            if (act != null) targets.Add((tile.rectTransform, act, key));
        }

        void Rooms()
        {
            var slug = Flow.Reader.Book.Slug; var here = UnityEngine.SceneManagement.SceneManager.GetActiveScene().name;
            float y = 200;
            foreach (var e in ReadingRooms.For(slug))
            {
                bool isHere = e.Generated > 0 ? Flow.GeneratedRoom == e.Generated : e.Scene == here && Flow.GeneratedRoom == 0;
                if (!e.Ready)
                {
                    Text(body, e.Label, 18, FontStyles.Normal, Soft, TextAlignmentOptions.Left, new Vector2(0, y + 8), new Vector2(500, 26));
                    Text(body, e.Note ?? "", 14, FontStyles.Italic, Soft, TextAlignmentOptions.Left, new Vector2(0, y - 14), new Vector2(500, 22));
                    y -= 62; continue;
                }
                var en = e;
                Button(body, e.Label + (isHere ? "  \u00b7  you are here" : ""), new Vector2(0, y), new Vector2(500, 50), 18, "room:" + (e.Generated > 0 ? "g" + e.Generated : e.Scene), () =>
                {
                    if (isHere) return;
                    Close();
                    if (en.Generated > 0) Flow.GoToGeneratedRoom(en.Generated); else Flow.GoToRoom(en.Scene);
                });
                y -= 62;
            }
            if (Library.IsImported(slug)) Text(body, "Your book\u2019s three rooms are made from places in its opening chapters.", 14, FontStyles.Italic, Soft, TextAlignmentOptions.Center, new Vector2(0, y - 4), new Vector2(520, 40));
            Text(body, "Your place in the book comes with you.", 15, FontStyles.Italic, Soft, TextAlignmentOptions.Center, new Vector2(0, y - 40), new Vector2(500, 30));
        }

        void Sound()
        {
            var p = ProgressStore.LoadPrefs();
            Text(body, "Music", 19, FontStyles.SmallCaps, Ink, TextAlignmentOptions.Left, new Vector2(-150, 190), new Vector2(200, 40));
            Button(body, p.MusicOn ? "on" : "off", new Vector2(120, 190), new Vector2(160, 46), 19, "music", () => { var q = ProgressStore.LoadPrefs(); q.MusicOn = !q.MusicOn; ProgressStore.SavePrefs(q); RoomSound.NotifySettings(); Rebuild(); });
            Text(body, "Room sound", 19, FontStyles.SmallCaps, Ink, TextAlignmentOptions.Left, new Vector2(-150, 120), new Vector2(200, 40));
            string[] names = { "off", "quiet", "normal" };
            for (int i = 0; i < 3; i++)
            {
                int lv = i; var b = Button(body, names[i], new Vector2(20 + i * 110, 120), new Vector2(100, 46), 17, "amb:" + i, () => { var q = ProgressStore.LoadPrefs(); q.AmbienceLevel = lv; ProgressStore.SavePrefs(q); RoomSound.NotifySettings(); Rebuild(); });
                if (p.AmbienceLevel == i) b.GetComponent<Image>().color = Lit;
            }
            // Translate's language: one row that cycles through TranslateLanguages.Names on each pinch
            Text(body, "Translate to", 19, FontStyles.SmallCaps, Ink, TextAlignmentOptions.Left, new Vector2(-150, 50), new Vector2(200, 40));
            Button(body, TranslateLanguages.Current() + "  ›", new Vector2(120, 50), new Vector2(240, 46), 19, "translate", () => { var q = ProgressStore.LoadPrefs(); q.TranslateTo = TranslateLanguages.Next(TranslateLanguages.Current()); ProgressStore.SavePrefs(q); Rebuild(); });
            Text(body, "Pinch to change. The highlight ring’s Translate petal uses it (with the interpreter).", 14, FontStyles.Italic, Soft, TextAlignmentOptions.Center, new Vector2(0, 8), new Vector2(520, 24));
            Text(body, "Saved for every room and every book.", 15, FontStyles.Italic, Soft, TextAlignmentOptions.Center, new Vector2(0, -24), new Vector2(500, 30));
        }

        // ---------------------------------------------------------------- pointing

        /// A pinch while the menu is open: on a control it acts; anywhere on the card it is the card's; off the card it
        /// closes the menu. Never a page turn or a highlight.
        bool Claim(bool right)
        {
            if (!IsOpen || !Flow.Pointer) return false;
            foreach (var (rt, act, key) in targets.ToList()) if (Flow.Pointer.Over(right, rt)) { Debug.Log($"[Fable] book menu: {key}"); act?.Invoke(); return true; }
            if (!Flow.Pointer.OnPage(right, out var at)) return false;   // the bar or the room: theirs
            if (!Over(right, card)) Close();
            return true;
        }

        bool Over(bool right, RectTransform rt) => Flow.Pointer.Over(right, rt);

        /// Test hook: press a control by its key ("close", "tab:rooms", "ch:alice:c02", "music", "amb:1", "translate", "room:LibraryRoom", "next").
        public string Press(string key)
        {
            var t = targets.Find(x => x.key == key); if (t.rt == null) return "no control " + key + "; have: " + string.Join(", ", targets.Select(x => x.key));
            t.act?.Invoke(); return Describe();
        }

        public string Describe()
        {
            if (!IsOpen) return "book menu closed";
            var b = Flow.Reader.Book; var ce = ChapterExperiences.Instance;
            return $"book menu {Tab}: " + (Tab == "chapters" ? string.Join(" | ", ChapterNumbers().Skip(chapterPage * Per).Take(Per).Select(c => $"{c.number}:{ce.StateOf(c.ch.Id)}{(ce.Title(c.ch.Id) is string s ? "=" + s : "")}")) : string.Join(", ", targets.Select(x => x.key)));
        }

        void Update()
        {
            if (!IsOpen || !Flow.Pointer) return;
            foreach (var (rt, _, key) in targets)
            {
                if (!rt) continue; var img = rt.GetComponent<Image>(); if (!img) continue;
                bool lit = Flow.Pointer.Over(true, rt) || Flow.Pointer.Over(false, rt);
                bool selected = key == "tab:" + Tab || (key.StartsWith("amb:") && key == "amb:" + ProgressStore.LoadPrefs().AmbienceLevel);
                var c = lit ? Lit : selected ? Lit : key.StartsWith("ch:") ? Tile : new Color(0.99f, 0.96f, 0.89f, 1f);
                if (img.color != c) img.color = c;
            }
        }

        // ---------------------------------------------------------------- small builders

        Image Img(RectTransform parent, string name, Vector2 pos, Vector2 size, Color c)
        {
            var im = new GameObject(name, typeof(RectTransform)).AddComponent<Image>(); im.transform.SetParent(parent, false); im.color = c; im.raycastTarget = false;
            im.rectTransform.anchoredPosition = pos; im.rectTransform.sizeDelta = size; built.Add(im.gameObject); return im;
        }

        TMP_Text Text(RectTransform parent, string s, float size, FontStyles style, Color c, TextAlignmentOptions align, Vector2 pos, Vector2 box)
        {
            var t = new GameObject("Text", typeof(RectTransform)).AddComponent<TextMeshProUGUI>(); t.transform.SetParent(parent, false);
            if (Font) t.font = Font; t.text = s; t.fontSize = size; t.fontStyle = style; t.color = c; t.alignment = align; t.raycastTarget = false; t.richText = true;
            t.textWrappingMode = TextWrappingModes.Normal; t.rectTransform.anchoredPosition = pos; t.rectTransform.sizeDelta = box; built.Add(t.gameObject); return t;
        }

        RectTransform Button(RectTransform parent, string label, Vector2 pos, Vector2 size, float fs, string key, Action act)
        {
            var img = Img(parent, "Btn " + label, pos, size, new Color(0.99f, 0.96f, 0.89f, 1f));
            var o = img.gameObject.AddComponent<Outline>(); o.effectColor = new Color(0.45f, 0.33f, 0.18f, 0.9f); o.effectDistance = new Vector2(1.5f, -1.5f);
            var t = Text(img.rectTransform, label, fs, FontStyles.SmallCaps, Ink, TextAlignmentOptions.Center, Vector2.zero, size);
            built.Remove(t.gameObject);
            targets.Add((img.rectTransform, act, key));
            return img.rectTransform;
        }

        /// A padlock, closed or with its shackle swung open, drawn once.
        public static Sprite LockSprite(bool open)
        {
            if (!open && lockSprite) return lockSprite; if (open && openSprite) return openSprite;
            const int n = 64; var tex = new Texture2D(n, n, TextureFormat.RGBA32, false); var px = new Color32[n * n];
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                bool body = x >= 12 && x < 52 && y >= 6 && y < 34 && !((x < 15 || x > 48) && (y < 9 || y > 30));
                bool hole = (x - 32) * (x - 32) + (y - 23) * (y - 23) < 18 || (x >= 30 && x < 34 && y >= 12 && y < 22);
                float cx = open ? 44 : 32, d = Mathf.Sqrt((x - cx) * (x - cx) + (y - 40) * (y - 40));
                bool arc = y >= 34 && y < 60 && d > 10 && d < 16 && y >= 40 - (open ? -6 : 0);
                bool legs = (Mathf.Abs(x - (cx - 13)) < 3 || Mathf.Abs(x - (cx + 13)) < 3) && y >= (open ? 40 : 34) && y < 41;
                if (open) arc = arc && y >= 40;
                bool on = (body && !hole) || arc || legs;
                px[y * n + x] = on ? new Color32(255, 255, 255, 255) : new Color32(255, 255, 255, 0);
            }
            tex.SetPixels32(px); tex.Apply();
            var sp = Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
            if (open) openSprite = sp; else lockSprite = sp;
            return sp;
        }
    }
}
