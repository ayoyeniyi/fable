// The whole book on the reading page, cover to cover: real pages laid out by TextMeshPro at the chosen text size,
// a running head, a contents list, bookmarks, and the place the reader stopped, saved per book.
//
// Pages are measured, not estimated: a hidden copy of the body text lays out the next stretch of the chapter and
// the first line that does not fit starts the next page. A chapter is paginated as far as the page being shown at
// once; after that only the next page is measured, at most one a frame, so a Quest never spends frames laying out
// pages the reader has not reached (the footer estimates the pages left until it knows). Positions are (paragraph,
// character) inside a chapter, and every page knows which sentences it holds, so progress, bookmarks and Step In
// all speak in the book's sentence ids.
using System.Collections;
using System.Collections.Generic;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Fable
{
    public class BookReader : MonoBehaviour
    {
        public ReadingPanel Panel;
        public PagePointer Pointer;
        public ReaderController Input;

        /// Body text sizes the reader can cycle through (points on the 0.001-scale page, so mm at the page).
        public static readonly float[] TextSizes = { 17f, 19.5f, 22.5f, 26f };
        public static readonly string[] TextSizeNames = { "small", "medium", "large", "largest" };

        public Book Book { get; private set; }
        public bool Active { get; private set; }
        public bool InContents { get; private set; }
        public int ChapterIndex { get; private set; }
        public int PageIndex { get; private set; }
        public int ChapterPageCount => pages.Count;
        public bool ChapterPaginated { get; private set; }
        public BookProgress Progress { get; private set; }

        /// Fired when the page changes (for the flow: Step In availability, the gesture row).
        public event System.Action PageChanged;

        // ---------------------------------------------------------------- layout (page pixels, 620 wide)
        const float TopRow = 14, TopRowH = 30, HeadY = 50, HeadH = 26, TitleY = 80, TitleH = 56, BodyTopFirst = 150, BodyTopRest = 94, BodyBottom = 716, FootY = 724, FootH = 40, Margin = 48;

        struct Pos { public int P, C; public Pos(int p, int c) { P = p; C = c; } public bool Before(Pos o) => P < o.P || (P == o.P && C < o.C); }
        struct Page { public Pos Start, End; }
        struct Run { public int Rich, P, C, Len; }

        // per chapter
        readonly List<string> paraText = new();
        readonly List<int[]> sentStart = new();
        readonly List<Page> pages = new();
        readonly List<int> paraOffset = new();   // characters before each paragraph, for page estimates
        readonly List<Run> shownRuns = new();    // rich-text runs of the page on show (for word hit-testing)
        int chapterChars;

        // page widgets built at runtime
        TMP_Text measure;
        RectTransform contentsBtn, sizeBtn, markBtn, stepBtn, shelfBtn;
        /// The page's "shelf" control: back to the lobby. Shown only when the flow sets ShelfAvailable (a lobby is in the build).
        public event System.Action ShelfPressed;
        public bool ShelfAvailable;
        TMP_Text contentsLbl, sizeLbl, markLbl, stepLbl;
        Image ribbon;
        readonly List<(RectTransform rt, int target)> contentsRows = new();
        int contentsPage;
        const int ContentsPerPage = 14;

        // the panel's layout outside the book (the passage view in the miniature and the scene), restored on Deactivate
        struct Saved { public Vector2 pos, size; public float font; public TextAlignmentOptions align; public bool on; }
        Saved bodySaved, hintSaved, titleSaved, chapterSaved;

        /// Step In: the passages that can be staged, and the one whose text is on this page (or null).
        public List<Passage.Scene> StagePassages = new();
        public string StepInPassage { get; private set; }
        public string StepInLabel = "Step in";

        // ---------------------------------------------------------------- loading

        public IEnumerator Load(string slug)
        {
            var path = System.IO.Path.Combine(Application.streamingAssetsPath, "books", slug, "book.json");
            string json;
#if UNITY_ANDROID && !UNITY_EDITOR
            using (var req = UnityEngine.Networking.UnityWebRequest.Get(path))
            {
                yield return req.SendWebRequest();
                if (req.result != UnityEngine.Networking.UnityWebRequest.Result.Success) { Debug.LogError($"[Fable] book {slug} missing from StreamingAssets: {req.error}"); yield break; }
                json = req.downloadHandler.text;
            }
#else
            if (!System.IO.File.Exists(path)) { Debug.LogError($"[Fable] book {slug} missing: {path} (run Fable > Sync Data)"); yield break; }
            json = System.IO.File.ReadAllText(path);
            yield return null;
#endif
            var t0 = Time.realtimeSinceStartup;
            Book = Book.Parse(json);
            Progress = ProgressStore.LoadBook(slug);
            Progress.TextSize = Mathf.Clamp(Progress.TextSize, 0, TextSizes.Length - 1);
            Debug.Log($"[Fable] book {slug}: {Book.Chapters.Count} chapters, {Book.SentenceCount} sentences, parsed in {(Time.realtimeSinceStartup - t0) * 1000:F0} ms");
            BuildWidgets();
            // Search's index: every sentence lower-cased and stripped of punctuation, built off the main thread
            var book = Book; searchText = null;
            System.Threading.Tasks.Task.Run(() =>
            {
                var arr = new string[book.SentenceCount]; int i = 0;
                foreach (var ch in book.Chapters) foreach (var p in ch.Paragraphs) foreach (var se in p.Sentences) arr[i++] = Normal(se.Text);
                return arr;
            }).ContinueWith(t => { if (!t.IsFaulted && Book == book) searchText = t.Result; });
        }

        string[] searchText;   // by ordinal; null until built

        // ---------------------------------------------------------------- activation

        /// Turn the panel into the book page, at the saved place (or at a given sentence).
        public void Activate(string atSentence = null)
        {
            if (Book == null) return;
            if (!Active) { SaveLayout(); Active = true; }
            SetWidgets(true);
            ApplyLayout();
            InContents = false;
            var at = atSentence ?? Progress.SentenceId ?? FirstSentence();
            OpenAt(at);
        }

        /// Hand the panel back to the passage view (miniature and immersive states).
        public void Deactivate()
        {
            if (!Active) return;
            Active = false;
            SetWidgets(false);
            RestoreLayout();
        }

        string FirstSentence()
        {
            foreach (var c in Book.Chapters) foreach (var p in c.Paragraphs) if (p.Sentences.Count > 0) return p.Sentences[0].Id;
            return null;
        }

        void SaveLayout()
        {
            Saved S(TMP_Text t) => t ? new Saved { pos = t.rectTransform.anchoredPosition, size = t.rectTransform.sizeDelta, font = t.fontSize, align = t.alignment, on = t.gameObject.activeSelf } : default;
            bodySaved = S(Panel.Body); hintSaved = S(Panel.Hint); titleSaved = S(Panel.Title); chapterSaved = S(Panel.Chapter);
        }

        void RestoreLayout()
        {
            void R(TMP_Text t, Saved s) { if (!t) return; t.rectTransform.anchoredPosition = s.pos; t.rectTransform.sizeDelta = s.size; t.fontSize = s.font; t.alignment = s.align; t.gameObject.SetActive(s.on); }
            R(Panel.Body, bodySaved); R(Panel.Hint, hintSaved); R(Panel.Title, titleSaved); R(Panel.Chapter, chapterSaved);
            if (Panel.Body) Panel.Body.overflowMode = TextOverflowModes.Truncate;
        }

        void Place(TMP_Text t, float y, float h, float inset = 0)
        {
            var r = t.rectTransform; r.anchorMin = new Vector2(0, 1); r.anchorMax = new Vector2(1, 1); r.pivot = new Vector2(0.5f, 1);
            r.anchoredPosition = new Vector2(0, -y); r.sizeDelta = new Vector2(-2 * Margin - inset, h);
        }

        void ApplyLayout()
        {
            Place(Panel.Chapter, HeadY, HeadH); Panel.Chapter.alignment = TextAlignmentOptions.Center;
            Place(Panel.Title, TitleY, TitleH); Panel.Title.alignment = TextAlignmentOptions.Center;
            Place(Panel.Hint, FootY, FootH, 150); Panel.Hint.alignment = TextAlignmentOptions.Left;
            Panel.Hint.rectTransform.anchoredPosition = new Vector2(-75, -FootY);
            Panel.Body.fontSize = TextSizes[Progress.TextSize];
            Panel.Body.overflowMode = TextOverflowModes.Overflow;
            Panel.Body.alignment = TextAlignmentOptions.TopLeft;   // ragged right: no hyphenation, so justified lines open rivers at this measure
            CopyStyle(Panel.Body, measure);
        }

        static void CopyStyle(TMP_Text from, TMP_Text to)
        {
            to.font = from.font; to.fontSize = from.fontSize; to.fontStyle = from.fontStyle; to.alignment = from.alignment;
            to.lineSpacing = from.lineSpacing; to.paragraphSpacing = from.paragraphSpacing; to.textWrappingMode = from.textWrappingMode;
            to.richText = true; to.margin = from.margin; to.characterSpacing = from.characterSpacing; to.wordSpacing = from.wordSpacing;
            to.overflowMode = TextOverflowModes.Overflow;
        }

        // ---------------------------------------------------------------- chapters and pages

        int CharIndex(Pos p) => p.P >= paraOffset.Count ? chapterChars : paraOffset[p.P] + p.C;

        void LoadChapter(int c)
        {
            ChapterIndex = Mathf.Clamp(c, 0, Book.Chapters.Count - 1);
            paraText.Clear(); sentStart.Clear(); pages.Clear(); paraOffset.Clear(); ChapterPaginated = false; chapterChars = 0;
            foreach (var p in Book.Chapters[ChapterIndex].Paragraphs)
            {
                var starts = new int[p.Sentences.Count]; var sb = new StringBuilder();
                for (int i = 0; i < p.Sentences.Count; i++) { if (i > 0) sb.Append(p.Sentences[i].LineBefore ? '\n' : ' '); starts[i] = sb.Length; sb.Append(p.Sentences[i].Text); }
                paraText.Add(sb.ToString()); sentStart.Add(starts);
                paraOffset.Add(chapterChars); chapterChars += sb.Length;
            }
        }

        Pos ChapterEnd => new(paraText.Count, 0);

        Pos Normalise(Pos p)
        {
            while (p.P < paraText.Count && p.C >= paraText[p.P].Length) { p.P++; p.C = 0; }
            while (p.P < paraText.Count && p.C < paraText[p.P].Length && (paraText[p.P][p.C] == ' ' || paraText[p.P][p.C] == '\n')) p.C++;
            return p;
        }

        /// Rich text for the stretch [from, to) of the chapter (to = null: until about `window` characters).
        string Render(Pos from, Pos? to, int window, List<Run> runs, out Pos reached)
        {
            var sb = new StringBuilder(); runs?.Clear();
            var paras = Book.Chapters[ChapterIndex].Paragraphs;
            int used = 0; reached = from;
            for (int p = from.P; p < paraText.Count; p++)
            {
                if (to.HasValue && !(new Pos(p, 0)).Before(to.Value) && !(p == to.Value.P && to.Value.C > 0)) break;
                int c0 = p == from.P ? from.C : 0;
                int c1 = to.HasValue && to.Value.P == p ? to.Value.C : paraText[p].Length;
                if (c1 <= c0) { reached = new Pos(p + 1, 0); continue; }
                if (sb.Length > 0) sb.Append('\n');
                var style = paras[p].Style;
                string open = style == "verse" ? "<indent=7%>" : style == "heading" ? "<align=center><smallcaps>" : "";
                string close = style == "verse" ? "</indent>" : style == "heading" ? "</smallcaps></align>" : "";
                sb.Append(open);
                runs?.Add(new Run { Rich = sb.Length, P = p, C = c0, Len = c1 - c0 });
                // line breaks inside a paragraph (verse) break without paragraph spacing: TMP treats a vertical tab
                // as a line break inside the paragraph
                var seg = paraText[p].Substring(c0, c1 - c0).Replace('\n', '\v');
                sb.Append(Escape(seg));
                sb.Append(close);
                used += c1 - c0; reached = new Pos(p, c1);
                if (!to.HasValue && used >= window) break;
            }
            return sb.ToString();
        }

        /// The book's text never contains TMP tags, but a stray "<" would open one: escape it (same length, so runs stay valid).
        static string Escape(string s) => s.IndexOf('<') < 0 ? s : s.Replace('<', '‹');

        Pos FromRich(List<Run> runs, int rich)
        {
            for (int i = 0; i < runs.Count; i++)
            {
                var r = runs[i];
                if (rich < r.Rich) return new Pos(r.P, r.C);                       // inside a tag or separator: the next run
                if (rich < r.Rich + r.Len) return new Pos(r.P, r.C + (rich - r.Rich));
            }
            return ChapterEnd;
        }

        float BodyHeight(int pageIndex) => BodyBottom - (pageIndex == 0 ? BodyTopFirst : BodyTopRest);

        /// Measure one page starting at `start`.
        Page MeasurePage(Pos start, int pageIndex)
        {
            start = Normalise(start);
            var runs = new List<Run>();
            measure.rectTransform.sizeDelta = new Vector2(Panel.Body.rectTransform.rect.width, BodyHeight(pageIndex));
            for (int window = 2400; ; window *= 2)
            {
                measure.text = Render(start, null, window, runs, out var reached);
                measure.ForceMeshUpdate(true, true);
                bool atEnd = !Normalise(reached).Before(ChapterEnd);
                if (!measure.isTextOverflowing)
                {
                    if (atEnd || window > 64000) return new Page { Start = start, End = atEnd ? ChapterEnd : reached };
                    continue;   // the window ran out before the page did: take a longer stretch
                }
                int ci = measure.firstOverflowCharacterIndex;
                var info = measure.textInfo.characterInfo;
                if (ci <= 0 || ci >= measure.textInfo.characterCount) return new Page { Start = start, End = reached };
                var end = FromRich(runs, info[ci].index);
                if (!start.Before(end)) end = new Pos(start.P, start.C + 1);   // never an empty page
                return new Page { Start = start, End = end };
            }
        }

        /// Paginate the current chapter until `until` returns true for a page (or to the end).
        void PaginateUntil(System.Func<Page, bool> until)
        {
            var t0 = Time.realtimeSinceStartup;
            Pos at = pages.Count > 0 ? pages[^1].End : new Pos(0, 0);
            while (!ChapterPaginated)
            {
                if (pages.Count > 0 && until != null && until(pages[^1])) break;
                at = Normalise(at);
                if (!at.Before(ChapterEnd)) { ChapterPaginated = true; break; }
                var pg = MeasurePage(at, pages.Count); pages.Add(pg); at = pg.End;
            }
            measure.text = "";   // the measuring copy holds no text between layouts
            Debug.Log($"[Fable] paginated {Book.Chapters[ChapterIndex].Id} to page {pages.Count}{(ChapterPaginated ? " (all)" : "")} in {(Time.realtimeSinceStartup - t0) * 1000:F0} ms");
        }

        int PageOf(Pos p)
        {
            for (int i = 0; i < pages.Count; i++) if (!p.Before(pages[i].Start) && p.Before(pages[i].End)) return i;
            return -1;
        }

        void OpenAt(string sentenceId)
        {
            if (!Book.TryFind(sentenceId, out var l)) { l = default; }
            LoadChapter(l.Chapter);
            var target = new Pos(l.Paragraph, l.Paragraph < sentStart.Count && l.Sentence < sentStart[l.Paragraph].Length ? sentStart[l.Paragraph][l.Sentence] : 0);
            PaginateUntil(pg => target.Before(pg.End));
            int i = PageOf(Normalise(target)); if (i < 0) i = Mathf.Max(0, pages.Count - 1);
            ShowPage(i, keep: sentenceId);
        }

        void OpenChapter(int c, bool atEnd = false)
        {
            LoadChapter(c);
            if (atEnd) { PaginateUntil(null); ShowPage(pages.Count - 1); }
            else { PaginateUntil(pg => true); ShowPage(0); }
        }

        // ---------------------------------------------------------------- showing

        /// keep: a sentence to stay anchored to if it starts on this page (re-layouts must not drift backwards).
        void ShowPage(int i, string keep = null)
        {
            InContents = false; SetContentsRows(false);
            if (contentsLbl) contentsLbl.text = "contents";
            if (markBtn) markBtn.gameObject.SetActive(true);
            PageIndex = Mathf.Clamp(i, 0, Mathf.Max(0, pages.Count - 1));
            if (pages.Count == 0) return;
            var pg = pages[PageIndex];
            var ch = Book.Chapters[ChapterIndex];
            float top = PageIndex == 0 ? BodyTopFirst : BodyTopRest;
            Place(Panel.Body, top, BodyBottom - top);
            Panel.Body.text = Render(pg.Start, pg.End, 0, shownRuns, out _);
            Panel.Body.ForceMeshUpdate();   // word hit-testing reads this page's layout
            Panel.Title.gameObject.SetActive(PageIndex == 0);
            Panel.Title.fontSize = 30;
            Panel.Title.text = PageIndex == 0 ? (ch.Name ?? ch.Heading) + (ch.Subtitle != null && ch.Subtitle.Length < 90 ? $"\n<size=55%><i>{ch.Subtitle}</i></size>" : "") : "";
            Panel.Chapter.text = RunningHead(ch);
            Progress.SentenceId = keep != null && StartsOn(keep, pg) ? keep : AnchorSentence(pg);
            var lastSeen = LastVisibleSentence;
            if (Book.Ordinal(lastSeen) > Book.Ordinal(Progress.Furthest)) Progress.Furthest = lastSeen;
            ProgressStore.SaveBook(Progress);
            UpdateStepIn(pg);
            ShowFooter();
            PageChanged?.Invoke();
        }

        string RunningHead(Book.Chapter ch)
        {
            var parts = new List<string> { Book.Title };
            if (!string.IsNullOrEmpty(ch.Part)) parts.Add(ch.Part);
            parts.Add(ch.Heading);
            return string.Join("  ·  ", parts);
        }

        void ShowFooter()
        {
            if (pages.Count == 0) return;
            float pct = Book.SentenceCount > 0 ? 100f * Mathf.Max(0, Book.Ordinal(Progress.SentenceId)) / Book.SentenceCount : 0;
            Panel.Hint.text = $"page {PageIndex + 1}  ·  {PagesLeftText()}  ·  {pct:F0}% of the book";
            bool marked = Progress.Bookmarks.Contains(Progress.SentenceId);
            if (markLbl) markLbl.text = marked ? "bookmarked" : "bookmark";
            if (ribbon) ribbon.gameObject.SetActive(marked);
            if (sizeLbl) sizeLbl.text = "text: " + TextSizeNames[Progress.TextSize];
            if (stepBtn) stepBtn.gameObject.SetActive(StepInPassage != null);
            if (stepLbl) stepLbl.text = StepInLabel + " ›";
        }

        bool StartsOn(string sentenceId, Page pg)
        {
            if (!Book.TryFind(sentenceId, out var l) || l.Chapter != ChapterIndex) return false;
            var at = Normalise(new Pos(l.Paragraph, sentStart[l.Paragraph][l.Sentence]));
            return !at.Before(pg.Start) && at.Before(pg.End);
        }

        /// "4 pages left in the chapter": exact once the chapter is laid out, else estimated from the pages measured so far.
        string PagesLeftText()
        {
            int left;
            if (ChapterPaginated) left = pages.Count - 1 - PageIndex;
            else
            {
                int measured = CharIndex(pages[^1].End), perPage = Mathf.Max(1, measured / pages.Count);
                left = (pages.Count - 1 - PageIndex) + Mathf.CeilToInt((chapterChars - measured) / (float)perPage);
            }
            string about = ChapterPaginated ? "" : "about ";
            return left <= 0 ? "last page of the chapter" : left == 1 ? $"{about}1 page left in the chapter" : $"{about}{left} pages left in the chapter";
        }

        /// The first sentence that starts on the page (or the one it opens in the middle of).
        string AnchorSentence(Page pg)
        {
            var paras = Book.Chapters[ChapterIndex].Paragraphs;
            for (int p = pg.Start.P; p < paraText.Count && (p < pg.End.P || (p == pg.End.P && pg.End.C > 0)); p++)
                for (int s = 0; s < sentStart[p].Length; s++)
                {
                    var at = new Pos(p, sentStart[p][s]);
                    if (!at.Before(pg.Start) && at.Before(pg.End)) return paras[p].Sentences[s].Id;
                }
            return SentenceAt(pg.Start);
        }

        string SentenceAt(Pos pos)
        {
            var paras = Book.Chapters[ChapterIndex].Paragraphs;
            int p = Mathf.Clamp(pos.P, 0, paras.Count - 1); int idx = 0;
            for (int s = 0; s < sentStart[p].Length; s++) if (sentStart[p][s] <= pos.C) idx = s;
            return paras[p].Sentences[idx].Id;
        }

        /// The last sentence the reader can see on this page: nothing past it may be staged (the spoiler rule).
        public string LastVisibleSentence
        {
            get
            {
                if (pages.Count == 0) return null;
                var e = pages[PageIndex].End;
                var last = e.C > 0 ? new Pos(e.P, e.C - 1) : new Pos(e.P - 1, Mathf.Max(0, paraText[Mathf.Max(0, e.P - 1)].Length - 1));
                if (last.P < 0) last = new Pos(0, 0);
                return SentenceAt(last);
            }
        }
        public string FirstVisibleSentence => pages.Count == 0 ? null : SentenceAt(pages[PageIndex].Start);

        void UpdateStepIn(Page pg)
        {
            StepInPassage = null;
            int a = Book.Ordinal(SentenceAt(pg.Start)), b = Book.Ordinal(LastVisibleSentence);
            foreach (var s in StagePassages)
            {
                if (s.Book != Book.Slug) continue;
                int f = Book.Ordinal(s.BookFrom), t = Book.Ordinal(s.BookTo);
                if (f < 0 || t < 0) continue;
                if (f <= b && t >= a) { StepInPassage = s.Id; break; }
            }
        }

        // ---------------------------------------------------------------- reader actions

        public void NextPage()
        {
            if (InContents) { ContentsTurn(+1); return; }
            if (PageIndex + 1 < pages.Count) { ShowPage(PageIndex + 1); return; }
            if (!ChapterPaginated) { PaginateUntil(pg => pages.Count > PageIndex + 1); if (PageIndex + 1 < pages.Count) { ShowPage(PageIndex + 1); return; } }
            if (ChapterIndex + 1 < Book.Chapters.Count) OpenChapter(ChapterIndex + 1);
        }

        public void PreviousPage()
        {
            if (InContents) { ContentsTurn(-1); return; }
            if (PageIndex > 0) { ShowPage(PageIndex - 1); return; }
            if (ChapterIndex > 0) OpenChapter(ChapterIndex - 1, atEnd: true);
        }

        public void CycleTextSize()
        {
            var anchor = Progress.SentenceId;
            Progress.TextSize = (Progress.TextSize + 1) % TextSizes.Length;
            ApplyLayout();
            OpenAt(anchor);
        }

        public void ToggleBookmark()
        {
            var id = Progress.SentenceId; if (id == null) return;
            if (!Progress.Bookmarks.Remove(id)) Progress.Bookmarks.Add(id);
            Progress.Bookmarks.Sort((x, y) => Book.Ordinal(x).CompareTo(Book.Ordinal(y)));
            ProgressStore.SaveBook(Progress);
            ShowFooter();
        }

        public void GoToSentence(string id) { if (Book.TryFind(id, out _)) OpenAt(id); }

        // ---------------------------------------------------------------- contents

        public void ShowContents()
        {
            InContents = true;
            if (contentsLbl) contentsLbl.text = "\u2039 back to the page";
            if (markBtn) markBtn.gameObject.SetActive(false);
            int perPage = ContentsPerPage;
            var entries = ContentsEntries();
            int current = entries.FindIndex(e => e.target == ChapterIndex);
            contentsPage = Mathf.Max(0, current) / perPage;
            RenderContents();
        }

        List<(string text, int target, string sentence)> ContentsEntries()
        {
            var list = new List<(string, int, string)>();
            for (int i = 0; i < Book.Chapters.Count; i++)
            {
                var c = Book.Chapters[i];
                list.Add((c.Name != null ? $"{c.Heading}  ·  {c.Name}" : (c.Part != null && (i == 0 || Book.Chapters[i - 1].Part != c.Part) ? $"{c.Part}  ·  {c.Heading}" : c.Heading), i, null));
            }
            foreach (var b in Progress.Bookmarks)
                if (Book.TryFind(b, out var l))
                {
                    var t = Book.Chapters[l.Chapter].Paragraphs[l.Paragraph].Sentences[l.Sentence].Text;
                    list.Add(($"bookmark  ·  {Book.Chapters[l.Chapter].Heading}: “{(t.Length > 40 ? t.Substring(0, 40) + "…" : t)}”", -1, b));
                }
            return list;
        }

        void RenderContents()
        {
            var entries = ContentsEntries();
            int pagesN = Mathf.Max(1, (entries.Count + ContentsPerPage - 1) / ContentsPerPage);
            contentsPage = Mathf.Clamp(contentsPage, 0, pagesN - 1);
            Panel.Title.gameObject.SetActive(true); Panel.Title.fontSize = 30; Panel.Title.text = "Contents";
            Panel.Chapter.text = Book.Title + (Book.Translator != null ? $"  ·  translated by {Book.Translator}" : $"  ·  {Book.Author}");
            Panel.Body.text = "";
            Place(Panel.Body, BodyTopFirst, BodyBottom - BodyTopFirst);
            SetContentsRows(true);
            for (int r = 0; r < contentsRows.Count; r++)
            {
                int k = contentsPage * ContentsPerPage + r;
                var row = contentsRows[r]; var lbl = row.rt.GetComponentInChildren<TMP_Text>(true);
                bool has = k < entries.Count;
                row.rt.gameObject.SetActive(has);
                if (!has) continue;
                var e = entries[k];
                contentsRows[r] = (row.rt, k);
                lbl.text = e.text;
                lbl.fontStyle = e.target == ChapterIndex ? FontStyles.Bold : FontStyles.Normal;
            }
            Panel.Hint.text = $"contents {contentsPage + 1} of {pagesN}  ·  point at a chapter and pinch";
            if (stepBtn) stepBtn.gameObject.SetActive(false);
            PageChanged?.Invoke();
        }

        void ContentsTurn(int dir) { contentsPage += dir; RenderContents(); }

        void OpenEntry(int k)
        {
            var entries = ContentsEntries(); if (k < 0 || k >= entries.Count) return;
            var e = entries[k];
            if (e.sentence != null) OpenAt(e.sentence); else OpenChapter(e.target);
        }

        // ---------------------------------------------------------------- pointing and pinching at controls

        /// A right pinch: press the control under the right hand's ray, if any. Returns true if one was pressed.
        public bool PressAt(bool right, bool dryRun = false)
        {
            if (!Active || !Pointer) return false;
            if (dryRun) return Pointer.Over(right, contentsBtn) || Pointer.Over(right, sizeBtn) || Pointer.Over(right, markBtn) || Pointer.Over(right, stepBtn) || (ShelfAvailable && Pointer.Over(right, shelfBtn));
            if (ShelfAvailable && Pointer.Over(right, shelfBtn)) { ShelfPressed?.Invoke(); return true; }
            if (Pointer.Over(right, contentsBtn)) { if (InContents) ShowPage(PageIndex, keep: Progress.SentenceId); else ShowContents(); return true; }
            if (Pointer.Over(right, sizeBtn)) { CycleTextSize(); return true; }
            if (Pointer.Over(right, markBtn) && !InContents) { ToggleBookmark(); return true; }
            if (InContents)
                foreach (var row in contentsRows) if (Pointer.Over(right, row.rt)) { OpenEntry(row.target); return true; }
            return false;
        }

        /// True when the pinch would land on the Step In control (the flow stages the passage).
        public bool OverStepIn(bool right) => Active && !InContents && StepInPassage != null && Pointer && Pointer.Over(right, stepBtn);

        /// Test hook: press a control by name, as a pinch on it would.
        public string Press(string control)
        {
            switch (control)
            {
                case "contents": if (InContents) ShowPage(PageIndex, keep: Progress.SentenceId); else ShowContents(); break;
                case "size": CycleTextSize(); break;
                case "bookmark": ToggleBookmark(); break;
                case "shelf": ShelfPressed?.Invoke(); break;
                default:
                    if (control.StartsWith("entry:") && int.TryParse(control.Substring(6), out var k)) OpenEntry(k);
                    else return "unknown control " + control;
                    break;
            }
            return Describe();
        }

        /// Test and measurement: paginate every chapter at the current size; returns pages per chapter and timings.
        /// Restores the page the reader was on.
        public string PageCensus()
        {
            var keep = Progress.SentenceId; var sb = new StringBuilder(); int total = 0; float worst = 0, sum = 0; string worstId = "";
            for (int c = 0; c < Book.Chapters.Count; c++)
            {
                LoadChapter(c);
                var t0 = Time.realtimeSinceStartup;
                var at = new Pos(0, 0);
                while (true) { at = Normalise(at); if (!at.Before(ChapterEnd)) break; var pg = MeasurePage(at, pages.Count); pages.Add(pg); at = pg.End; }
                ChapterPaginated = true;
                float ms = (Time.realtimeSinceStartup - t0) * 1000; sum += ms; total += pages.Count;
                float per = pages.Count > 0 ? ms / pages.Count : 0; if (per > worst) { worst = per; worstId = Book.Chapters[c].Id; }
                sb.Append($"{Book.Chapters[c].Id}:{pages.Count} ");
            }
            measure.text = "";
            OpenAt(keep);
            return $"{Book.Slug} size={TextSizeNames[Progress.TextSize]} pages={total} layout={sum:F0}ms worst={worst:F1}ms/page ({worstId})\n{sb}";
        }

        public string Describe()
        {
            if (Book == null) return "book=none";
            var ch = Book.Chapters[ChapterIndex];
            return $"book={Book.Slug} chapter={ch.Id} page={PageIndex + 1}/{(ChapterPaginated ? pages.Count.ToString() : pages.Count + "+")} anchor={Progress.SentenceId} last={LastVisibleSentence} size={TextSizeNames[Progress.TextSize]} marks={Progress.Bookmarks.Count} contents={InContents} stepIn={StepInPassage ?? "-"}";
        }

        // ---------------------------------------------------------------- words on the page (highlighting)

        /// True when the page shows the book's text (not the contents list): words can be highlighted.
        public bool ShowsText => Active && !InContents && pages.Count > 0;

        /// The word under a point on the page (page-local pixels): its index in the body's layout. Points between
        /// lines or past a line's end take the nearest word on the nearest line, so a drag never drops out.
        public bool WordAt(Vector2 pageLocal, out int word, bool nearest = false)
        {
            word = -1;
            if (!ShowsText) return false;
            var body = Panel.Body; var ti = body.textInfo;
            if (ti == null || ti.wordCount == 0) return false;
            Vector2 p = body.rectTransform.InverseTransformPoint(Pointer.Page.TransformPoint(pageLocal));
            var r = body.rectTransform.rect;
            if (!nearest && (p.x < r.xMin - 12 || p.x > r.xMax + 12 || p.y > r.yMax + 8 || p.y < r.yMin - 8)) return false;
            // the line: the one whose band (ascender to descender) holds the point, else the closest
            int line = -1; float best = float.MaxValue;
            for (int l = 0; l < ti.lineCount; l++)
            {
                var li = ti.lineInfo[l]; if (li.characterCount == 0) continue;
                float top = li.ascender, bot = li.descender;
                float d = p.y > top ? p.y - top : p.y < bot ? bot - p.y : 0;
                if (d < best) { best = d; line = l; }
            }
            if (line < 0 || (!nearest && best > 14)) return false;
            best = float.MaxValue;
            for (int w = 0; w < ti.wordCount; w++)
            {
                var wi = ti.wordInfo[w]; if (wi.characterCount == 0) continue;
                var c0 = ti.characterInfo[wi.firstCharacterIndex]; var c1 = ti.characterInfo[wi.lastCharacterIndex];
                if (c0.lineNumber != line) continue;
                float d = p.x < c0.bottomLeft.x ? c0.bottomLeft.x - p.x : p.x > c1.topRight.x ? p.x - c1.topRight.x : 0;
                if (d < best) { best = d; word = w; }
            }
            return word >= 0;
        }

        public int WordCount => Panel.Body.textInfo != null ? Panel.Body.textInfo.wordCount : 0;

        Pos CharPos(int ci) => FromRich(shownRuns, Panel.Body.textInfo.characterInfo[ci].index);

        /// The text from word a to word b (inclusive, either order), as the book has it, with its first and last sentence ids.
        public string Selection(int a, int b, out string firstSentence, out string lastSentence)
        {
            firstSentence = lastSentence = null;
            var ti = Panel.Body.textInfo; if (ti == null || a < 0 || b < 0 || a >= ti.wordCount || b >= ti.wordCount) return "";
            if (b < a) (a, b) = (b, a);
            var s = CharPos(ti.wordInfo[a].firstCharacterIndex);
            var eLast = CharPos(ti.wordInfo[b].lastCharacterIndex); var e = new Pos(eLast.P, eLast.C + 1);
            firstSentence = SentenceAt(s); lastSentence = SentenceAt(eLast);
            var sb = new StringBuilder();
            for (int p = s.P; p <= e.P && p < paraText.Count; p++)
            {
                int c0 = p == s.P ? s.C : 0, c1 = p == e.P ? Mathf.Min(e.C, paraText[p].Length) : paraText[p].Length;
                if (c1 <= c0) continue;
                if (sb.Length > 0) sb.Append(' ');
                sb.Append(paraText[p], c0, c1 - c0);
            }
            return sb.ToString().Replace('\n', ' ');
        }

        /// One rectangle per line covered by words a..b, in the body's local space (for the highlight bars).
        public void SelectionRects(int a, int b, List<Rect> into)
        {
            into.Clear();
            var ti = Panel.Body.textInfo; if (ti == null || a < 0 || b < 0 || a >= ti.wordCount || b >= ti.wordCount) return;
            if (b < a) (a, b) = (b, a);
            int c0 = ti.wordInfo[a].firstCharacterIndex, c1 = ti.wordInfo[b].lastCharacterIndex;
            int line = -1; float x0 = 0, x1 = 0;
            for (int c = c0; c <= c1; c++)
            {
                var ci = ti.characterInfo[c];
                if (!ci.isVisible) continue;
                if (ci.lineNumber != line)
                {
                    if (line >= 0) into.Add(LineRect(ti, line, x0, x1));
                    line = ci.lineNumber; x0 = ci.bottomLeft.x; x1 = ci.topRight.x;
                }
                else { x0 = Mathf.Min(x0, ci.bottomLeft.x); x1 = Mathf.Max(x1, ci.topRight.x); }
            }
            if (line >= 0) into.Add(LineRect(ti, line, x0, x1));
        }

        static Rect LineRect(TMP_TextInfo ti, int line, float x0, float x1)
        {
            var li = ti.lineInfo[line];
            return Rect.MinMaxRect(x0 - 2, li.descender - 1, x1 + 2, li.ascender + 1);
        }

        /// The centre of word w in page-local pixels (for placing the menu, and for tests to aim at).
        public Vector2 WordCentre(int w)
        {
            var ti = Panel.Body.textInfo; var wi = ti.wordInfo[w];
            var a = ti.characterInfo[wi.firstCharacterIndex]; var b = ti.characterInfo[wi.lastCharacterIndex];
            var mid = (a.bottomLeft + b.topRight) / 2f;
            return Pointer.Page.InverseTransformPoint(Panel.Body.rectTransform.TransformPoint(mid));
        }

        /// The index of the first word on the page whose text starts a match for phrase (case-insensitive), or -1. Tests use it.
        public int FindWord(string phrase, out int lastWord)
        {
            lastWord = -1;
            var ti = Panel.Body.textInfo; if (ti == null) return -1;
            var want = phrase.ToLowerInvariant().Split(new[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);
            for (int w = 0; w + want.Length <= ti.wordCount; w++)
            {
                bool ok = true;
                for (int k = 0; k < want.Length && ok; k++) ok = ti.wordInfo[w + k].GetWord().ToLowerInvariant().Trim('’', '\'') == want[k].Trim('’', '\'');
                if (ok) { lastWord = w + want.Length - 1; return w; }
            }
            return -1;
        }

        /// Search: every sentence the reader has reached that contains the phrase (case-insensitive, whole words).
        /// Never looks past Progress.Furthest: later matches are neither shown nor counted.
        public List<(string id, string chapter, string snippet)> Search(string phrase, int max, out int total)
        {
            var hits = new List<(string, string, string)>(); total = 0;
            var q = Normal(phrase); if (q.Length == 0) return hits;
            int limit = Mathf.Max(Book.Ordinal(Progress.Furthest), Book.Ordinal(Progress.SentenceId));
            int n = 0; var index = searchText;
            foreach (var ch in Book.Chapters)
                foreach (var p in ch.Paragraphs)
                    foreach (var s in p.Sentences)
                    {
                        var t = index != null ? index[n] : Normal(s.Text);
                        if (n++ > limit) return hits;
                        int at = WholeWord(t, q);
                        if (at < 0) continue;
                        total++;
                        if (hits.Count < max) hits.Add((s.Id, ch.Heading, Snippet(s.Text, phrase)));
                    }
            return hits;
        }

        static string Normal(string s)
        {
            var sb = new StringBuilder(s.Length);
            foreach (var ch in s) sb.Append(ch == '’' || ch == '‘' ? '\'' : char.IsLetterOrDigit(ch) || ch == '\'' ? char.ToLowerInvariant(ch) : ' ');
            return " " + System.Text.RegularExpressions.Regex.Replace(sb.ToString(), @"\s+", " ").Trim() + " ";
        }
        static int WholeWord(string text, string q) => text.IndexOf(q, System.StringComparison.Ordinal);   // q is " word word " already

        static string Snippet(string text, string phrase)
        {
            int i = text.IndexOf(phrase, System.StringComparison.OrdinalIgnoreCase);
            if (i < 0) i = 0;
            int a = Mathf.Max(0, i - 40), b = Mathf.Min(text.Length, i + phrase.Length + 50);
            while (a > 0 && text[a] != ' ') a--;
            while (b < text.Length && text[b] != ' ') b++;
            var pre = text.Substring(a, i - a).TrimStart(); var hit = text.Substring(i, Mathf.Min(phrase.Length, text.Length - i)); var post = text.Substring(i + hit.Length, b - i - hit.Length);
            return (a > 0 ? "…" : "") + Escape(pre) + "<b>" + Escape(hit) + "</b>" + Escape(post) + (b < text.Length ? "…" : "");
        }

        /// The ordinal of the furthest sentence the reader has reached (for spoiler checks outside the reader).
        public int ReachedOrdinal => Mathf.Max(Book.Ordinal(Progress.Furthest), Book.Ordinal(Progress.SentenceId));

        // ---------------------------------------------------------------- widgets

        void BuildWidgets()
        {
            if (measure) return;
            var page = (RectTransform)Panel.transform;
            var m = new GameObject("PageMeasure", typeof(RectTransform)).AddComponent<TextMeshProUGUI>();
            m.transform.SetParent(page, false); m.raycastTarget = false;
            m.rectTransform.anchorMin = m.rectTransform.anchorMax = new Vector2(0.5f, 0.5f);
            m.rectTransform.anchoredPosition = new Vector2(0, -5000);   // laid out but never in view
            m.color = new Color(0, 0, 0, 0);
            measure = m;

            var font = Panel.Body.font;
            (RectTransform, TMP_Text) Button(string name, Vector2 anchor, Vector2 pos, Vector2 size, TextAlignmentOptions align)
            {
                var go = new GameObject(name, typeof(RectTransform), typeof(Image));
                var rt = go.GetComponent<RectTransform>(); rt.SetParent(page, false);
                rt.anchorMin = rt.anchorMax = anchor; rt.pivot = anchor; rt.anchoredPosition = pos; rt.sizeDelta = size;
                var bg = go.GetComponent<Image>(); bg.color = new Color(0.45f, 0.36f, 0.24f, 0.0f); bg.raycastTarget = false;
                var t = new GameObject("Label", typeof(RectTransform)).AddComponent<TextMeshProUGUI>(); t.transform.SetParent(rt, false);
                t.rectTransform.anchorMin = Vector2.zero; t.rectTransform.anchorMax = Vector2.one; t.rectTransform.offsetMin = new Vector2(8, 0); t.rectTransform.offsetMax = new Vector2(-8, 0);
                t.font = font; t.fontSize = 15; t.fontStyle = FontStyles.SmallCaps; t.color = new Color(0.36f, 0.29f, 0.21f); t.alignment = align; t.raycastTarget = false;
                t.textWrappingMode = TextWrappingModes.NoWrap;
                go.SetActive(false);
                return (rt, t);
            }
            (contentsBtn, contentsLbl) = Button("BtnContents", new Vector2(0, 1), new Vector2(Margin - 8, -TopRow), new Vector2(130, TopRowH), TextAlignmentOptions.Left);
            contentsLbl.text = "contents";
            TMP_Text shelfLbl; (shelfBtn, shelfLbl) = Button("BtnShelf", new Vector2(0, 1), new Vector2(Margin - 8 + 132, -TopRow), new Vector2(100, TopRowH), TextAlignmentOptions.Left);
            shelfLbl.text = "\u2039 shelf";
            (sizeBtn, sizeLbl) = Button("BtnTextSize", new Vector2(1, 1), new Vector2(-Margin - 132, -TopRow), new Vector2(150, TopRowH), TextAlignmentOptions.Right);
            (markBtn, markLbl) = Button("BtnBookmark", new Vector2(1, 1), new Vector2(-Margin + 8, -TopRow), new Vector2(124, TopRowH), TextAlignmentOptions.Right);
            (stepBtn, stepLbl) = Button("BtnStepIn", new Vector2(1, 1), new Vector2(-Margin + 8, -FootY + 2), new Vector2(150, FootH - 4), TextAlignmentOptions.Right);
            stepLbl.fontSize = 18; stepLbl.color = new Color(0.55f, 0.36f, 0.08f); stepLbl.fontStyle = FontStyles.SmallCaps | FontStyles.Bold;

            var rib = new GameObject("Ribbon", typeof(RectTransform)).AddComponent<Image>(); rib.transform.SetParent(page, false);
            rib.rectTransform.anchorMin = rib.rectTransform.anchorMax = rib.rectTransform.pivot = new Vector2(1, 1);
            rib.rectTransform.anchoredPosition = new Vector2(-18, 0); rib.rectTransform.sizeDelta = new Vector2(16, 64);
            rib.color = new Color(0.55f, 0.12f, 0.10f, 0.9f); rib.raycastTarget = false; rib.gameObject.SetActive(false);
            ribbon = rib;

            for (int r = 0; r < ContentsPerPage; r++)
            {
                var (rt, t) = Button("ContentsRow" + r, new Vector2(0.5f, 1), new Vector2(0, -BodyTopFirst - r * 39), new Vector2(620 - 2 * Margin + 16, 37), TextAlignmentOptions.Left);
                rt.pivot = new Vector2(0.5f, 1);
                t.fontSize = 18.5f; t.fontStyle = FontStyles.Normal; t.color = new Color(0.13f, 0.11f, 0.09f); t.overflowMode = TextOverflowModes.Ellipsis;
                contentsRows.Add((rt, r));
            }
        }

        void SetWidgets(bool on)
        {
            foreach (var rt in new[] { contentsBtn, sizeBtn, markBtn }) if (rt) rt.gameObject.SetActive(on);
            if (shelfBtn) shelfBtn.gameObject.SetActive(on && ShelfAvailable);
            if (stepBtn) stepBtn.gameObject.SetActive(on && StepInPassage != null);
            if (ribbon && !on) ribbon.gameObject.SetActive(false);
            if (!on) SetContentsRows(false);
        }

        void SetContentsRows(bool on) { foreach (var r in contentsRows) if (r.rt) r.rt.gameObject.SetActive(on); }

        void Update()
        {
            if (!Active) return;
            // keep exactly one page ready ahead of the reader: at most one layout a frame, none while they read on
            if (!InContents && !ChapterPaginated && pages.Count > 0 && pages.Count <= PageIndex + 1)
            {
                var at = Normalise(pages[^1].End);
                if (at.Before(ChapterEnd)) { pages.Add(MeasurePage(at, pages.Count)); measure.text = ""; }
                if (!Normalise(pages[^1].End).Before(ChapterEnd)) ChapterPaginated = true;
                ShowFooter();
            }
            if (!Pointer) return;
            // hover: the control a pinch would press glows faintly
            void Hover(RectTransform rt) { if (!rt || !rt.gameObject.activeSelf) return; var img = rt.GetComponent<Image>(); var a = Pointer.Over(true, rt) || Pointer.Over(false, rt) ? 0.16f : 0f; if (!Mathf.Approximately(img.color.a, a)) img.color = new Color(img.color.r, img.color.g, img.color.b, a); }
            Hover(contentsBtn); Hover(sizeBtn); Hover(markBtn); Hover(stepBtn); Hover(shelfBtn);
            if (InContents) foreach (var r in contentsRows) Hover(r.rt);
        }
    }
}
