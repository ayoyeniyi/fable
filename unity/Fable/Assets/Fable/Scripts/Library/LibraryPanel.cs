// The library board in the lobby: every book the reader has, bundled and imported, on one lectern-height panel in
// front of them, so nobody has to read tiny spines on a far shelf or walk anywhere.
//
//   header      "Your library", the counts, "continue: <the book read last> ›" and "+ add a book"
//   tiles       six to a page: the cover (or a plain one drawn with the title when the book has none), the title,
//               the author, where it came from ("Fable edition, with its own room" or "your EPUB" / "your PDF"), and
//               how far the reader has got. A book still arriving shows its stage and real progress; one that failed
//               says why and can be dismissed. Imported books have "remove" (pinch twice: it asks first).
//   footer      ‹ previous · shelf 1 of 2 · next ›, and how much of the 2 GB the imported books use
//
// "+ add a book" turns the board into instructions with the headset's address and code (Library / UploadServer) and
// follows the transfer and import live. Point and pinch, as everywhere; the board claims its pinches, so pointing at
// it never opens a book on the shelf behind it.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Fable
{
    public class LibraryPanel : MonoBehaviour
    {
        public ReaderController Input;
        public Transform Head;
        public TMP_FontAsset Font;
        public LobbyController Lobby;
        /// Bundled books: slug -> (title, author, cover texture from the shelf).
        public readonly Dictionary<string, (string title, string author, Texture cover)> Bundled = new();
        public float Forward = 0.92f, Drop = 0.46f;

        public Ray? TestRay;
        public RectTransform Root => root;
        public string Describe() => $"library board: {(adding ? "adding" : menuSlug != null ? "menu " + menuSlug + " [" + (menuChapters ? menuChapters.text : "") + "]" : "shelf")} page {page + 1}/{Pages} tiles=[{string.Join(" | ", shown.Select(t => t.Key + (t.State != null ? ":" + t.State : "")))}] hovered={hoveredKey ?? "-"} status=\"{(statusText ? statusText.text.Replace("\n", " / ") : "")}\"";

        const int Cols = 3, Rows = 2, PerPage = Cols * Rows;
        const float W = 790, H = 470, TileW = 250, TileH = 160, Gap = 10;
        static readonly Color Paper = new(0.97f, 0.94f, 0.87f, 0.98f), Ink = new(0.16f, 0.12f, 0.08f), Soft = new(0.42f, 0.34f, 0.24f), Accent = new(0.62f, 0.38f, 0.08f),
            Lit = new(0.99f, 0.88f, 0.60f, 1f), TileBg = new(1f, 0.985f, 0.95f, 1f), Bad = new(0.62f, 0.18f, 0.12f);

        class Tile
        {
            public string Key, State; public RectTransform Rt; public Image Bg, Cover, Bar, BarBack; public RawImage CoverTex; public TMP_Text CoverTitle, Title, Author, Badge, Status;
            public RectTransform Remove; public TMP_Text RemoveLbl; public float ConfirmUntil; public Action Act; public Action RemoveAct;
        }
        readonly List<Tile> tiles = new(); readonly List<Tile> shown = new();
        RectTransform root, header, grid, addCard, footer, prevBtn, nextBtn, addBtn, continueBtn, backBtn;
        TMP_Text headerCount, pageLbl, storageLbl, continueLbl, addTitle, addBody, addAddress, addCode, statusText, addStep1, addStep2, addStep3, addStep4;
        Image statusBar, statusBarBack;
        readonly Dictionary<string, Texture2D> covers = new();
        int page; bool adding; string menuSlug; string hoveredKey;
        RectTransform bookMenu, resumeBtn, ownRoomBtn, libraryRoomBtn, chaptersBtn, menuBackBtn; TMP_Text menuTitle, menuAuthor, menuChapters, ownRoomLbl; RectTransform hoveredRt; LibraryJob watching;
        Library lib;

        int Pages => Mathf.Max(1, Mathf.CeilToInt(Entries().Count / (float)PerPage));

        public void Init(ReaderController input, Transform head, TMP_FontAsset font, LobbyController lobby)
        {
            Input = input; Head = head; Font = font; Lobby = lobby;
            lib = Library.Instance;
            Build();
            lib.Changed += Refresh;
            if (Input && !Input.Claimers.Contains(Claim)) Input.Claimers.Insert(0, Claim);
            Recentre(true);
            Refresh();
            if (lib.StartupNote != null) Status(lib.StartupNote, false);
        }

        void OnDestroy()
        {
            if (lib) { lib.Changed -= Refresh; lib.Accepting = false; }
            if (Input) Input.Claimers.Remove(Claim);
            foreach (var t in covers.Values) if (t) Destroy(t);
        }

        /// Bring the board in front of the reader, at lectern height, tilted to face them.
        public void Recentre(bool snap = false)
        {
            if (!Head) return;
            var fwd = Vector3.ProjectOnPlane(Head.forward, Vector3.up).normalized; if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            target = Head.position + fwd * Forward + Vector3.down * Drop;
            targetRot = Quaternion.LookRotation(target - Head.position, Vector3.up);
            if (snap) { root.position = target; root.rotation = targetRot; }
            gliding = true;
        }
        Vector3 target; Quaternion targetRot; bool gliding;

        // ---------------------------------------------------------------- entries

        class Entry { public string Key, Slug, Title, Author, Badge, Progress; public bool Bundled, Ready = true, HasCover; public LibraryJob Job; public LibraryEntry Lib; }

        List<Entry> Entries()
        {
            var list = new List<Entry>();
            // books still arriving or that failed come first, so the reader sees them at once
            foreach (var j in lib.ActiveJobs())
                if (j.Status != "ready") list.Add(new Entry { Key = "job:" + j.Id, Title = j.Title ?? BookText.TitleFromFileName(j.FileName), Job = j, Ready = false });
            foreach (var kv in Bundled)
                list.Add(new Entry { Key = kv.Key, Slug = kv.Key, Title = kv.Value.title, Author = kv.Value.author, Bundled = true, Badge = "Fable edition · own room", Progress = ProgressText(kv.Key, null) });
            foreach (var e in lib.Imported.OrderByDescending(e => e.AddedUtc))
                list.Add(new Entry { Key = e.Slug, Slug = e.Slug, Title = e.Title, Author = e.Author, Lib = e, HasCover = e.Cover != null, Badge = e.Format == "pdf" ? (e.HasText ? $"your PDF · {e.PdfPages} pages" : $"your PDF · pages only") : "your EPUB", Progress = ProgressText(e.Slug, e) });
            return list;
        }

        /// "Chapter III · 24%", "page 12 of 230", or "not opened yet".
        string ProgressText(string slug, LibraryEntry e)
        {
            var p = ProgressStore.LoadBook(slug);
            if (e != null && e.Format == "pdf") return string.IsNullOrEmpty(p.SavedAtUtc) ? "not opened yet" : $"page {Mathf.Max(1, p.PdfPage)} of {e.PdfPages}";
            if (string.IsNullOrEmpty(p.SentenceId)) return "not opened yet";
            if (e == null && Lobby) { var line = Lobby.ProgressLine(slug); return line.Replace("<b>", "").Replace("</b>", "").Replace("\n", " · "); }
            // imported EPUB: the chapter number from the sentence id, the share of sentences from the index entry
            var chap = p.SentenceId.Contains('.') ? p.SentenceId.Substring(p.SentenceId.IndexOf(':') + 1, p.SentenceId.IndexOf('.') - p.SentenceId.IndexOf(':') - 1) : "";
            return chap.StartsWith("c") && int.TryParse(chap.Substring(1), out var n) && e != null && e.Chapters > 0 ? $"section {n} of {e.Chapters}" : "in progress";
        }

        // ---------------------------------------------------------------- building

        void Build()
        {
            var go = new GameObject("LibraryBoard", typeof(RectTransform)); go.transform.SetParent(transform, false);
            var canvas = go.AddComponent<Canvas>(); canvas.renderMode = RenderMode.WorldSpace; canvas.sortingOrder = 3;
            root = (RectTransform)go.transform; root.sizeDelta = new Vector2(W, H); root.localScale = Vector3.one * 0.001f;
            Img(root, "Paper", Vector2.zero, new Vector2(W, H), Paper, stretch: true);
            var edge = Img(root, "Edge", new Vector2(0, -H / 2 + 2), new Vector2(W, 4), new Color(0.45f, 0.30f, 0.12f, 0.9f));

            header = Rect(root, "Header", new Vector2(0, H / 2 - 34), new Vector2(W - 32, 56));
            var title = Text(header, "Your library", 28, FontStyles.SmallCaps, Ink, TextAlignmentOptions.Left); Place(title.rectTransform, new Vector2(-W / 2 + 16 + 120, 6), new Vector2(240, 36));
            headerCount = Text(header, "", 14, FontStyles.Italic, Soft, TextAlignmentOptions.Left); Place(headerCount.rectTransform, new Vector2(-W / 2 + 16 + 120, -18), new Vector2(240, 20));
            (addBtn, _) = Button(header, "+ add a book", new Vector2(W / 2 - 16 - 92, 0), new Vector2(184, 46), 20, () => OpenAdd());
            (continueBtn, continueLbl) = Button(header, "continue ›", new Vector2(W / 2 - 16 - 184 - 12 - 130, 0), new Vector2(260, 46), 17, ContinueReading);

            grid = Rect(root, "Grid", new Vector2(0, H / 2 - 66 - (Rows * TileH + (Rows - 1) * Gap) / 2), new Vector2(Cols * TileW + (Cols - 1) * Gap, Rows * TileH + (Rows - 1) * Gap));
            for (int i = 0; i < PerPage; i++) tiles.Add(MakeTile(i));

            footer = Rect(root, "Footer", new Vector2(0, -H / 2 + 30), new Vector2(W - 32, 44));
            (prevBtn, _) = Button(footer, "‹ previous", new Vector2(-W / 2 + 16 + 70, 0), new Vector2(140, 40), 17, () => { page = Mathf.Max(0, page - 1); Refresh(); });
            (nextBtn, _) = Button(footer, "next ›", new Vector2(W / 2 - 16 - 70, 0), new Vector2(140, 40), 17, () => { page = Mathf.Min(Pages - 1, page + 1); Refresh(); });
            pageLbl = Text(footer, "", 15, FontStyles.SmallCaps, Soft, TextAlignmentOptions.Center); Place(pageLbl.rectTransform, new Vector2(0, 8), new Vector2(360, 20));
            storageLbl = Text(footer, "", 12, FontStyles.Italic, Soft, TextAlignmentOptions.Center); Place(storageLbl.rectTransform, new Vector2(0, -11), new Vector2(420, 18));

            // the add-a-book card: in place of the grid while it is open
            addCard = Rect(root, "AddBook", new Vector2(0, -14), new Vector2(W - 40, H - 100));
            Img(addCard, "Bg", Vector2.zero, addCard.sizeDelta, TileBg, stretch: true);
            float ct = addCard.sizeDelta.y / 2, cw = addCard.sizeDelta.x - 40;
            addTitle = Text(addCard, "Add a book from your phone or computer", 22, FontStyles.SmallCaps, Accent, TextAlignmentOptions.Left); Place(addTitle.rectTransform, new Vector2(-60, ct - 26), new Vector2(cw - 120, 30));
            addStep1 = Text(addCard, "", 17, FontStyles.Normal, Ink, TextAlignmentOptions.Left); Place(addStep1.rectTransform, new Vector2(0, ct - 66), new Vector2(cw, 26));
            addStep2 = Text(addCard, "", 17, FontStyles.Normal, Ink, TextAlignmentOptions.Left); Place(addStep2.rectTransform, new Vector2(0, ct - 98), new Vector2(cw, 26));
            addAddress = Text(addCard, "", 27, FontStyles.Bold, Ink, TextAlignmentOptions.Left); Place(addAddress.rectTransform, new Vector2(24, ct - 134), new Vector2(cw - 48, 38));
            addStep3 = Text(addCard, "", 17, FontStyles.Normal, Ink, TextAlignmentOptions.Left); Place(addStep3.rectTransform, new Vector2(0, ct - 176), new Vector2(cw, 26));
            addCode = Text(addCard, "", 30, FontStyles.Bold, Accent, TextAlignmentOptions.Left); Place(addCode.rectTransform, new Vector2(24 + 150, ct - 176), new Vector2(cw - 200, 40));
            addCode.characterSpacing = 30;
            addStep4 = Text(addCard, "", 17, FontStyles.Normal, Ink, TextAlignmentOptions.Left); Place(addStep4.rectTransform, new Vector2(0, ct - 216), new Vector2(cw, 26));
            addBody = Text(addCard, "", 13.5f, FontStyles.Italic, Soft, TextAlignmentOptions.TopLeft); Place(addBody.rectTransform, new Vector2(0, ct - 256), new Vector2(cw, 40));
            statusBarBack = Img(addCard, "BarBack", new Vector2(0, -addCard.sizeDelta.y / 2 + 82), new Vector2(addCard.sizeDelta.x - 40, 10), new Color(0.85f, 0.80f, 0.70f));
            statusBar = Img(addCard, "Bar", new Vector2(0, -addCard.sizeDelta.y / 2 + 82), new Vector2(addCard.sizeDelta.x - 40, 10), Accent);
            statusBar.type = Image.Type.Filled; statusBar.fillMethod = Image.FillMethod.Horizontal; statusBar.sprite = WhiteSprite();
            statusText = Text(addCard, "", 16, FontStyles.Normal, Ink, TextAlignmentOptions.TopLeft); Place(statusText.rectTransform, new Vector2(0, -addCard.sizeDelta.y / 2 + 40), new Vector2(addCard.sizeDelta.x - 40, 56));
            (backBtn, _) = Button(addCard, "‹ back to the shelf", new Vector2(-addCard.sizeDelta.x / 2 + 20 + 110, addCard.sizeDelta.y / 2 - 24), new Vector2(220, 40), 17, CloseAdd);
            backBtn.anchoredPosition = new Vector2(addCard.sizeDelta.x / 2 - 20 - 110, addCard.sizeDelta.y / 2 - 26);
            addCard.gameObject.SetActive(false);

            // a book's menu: in place of the grid once a book is chosen, before any room loads
            bookMenu = Rect(root, "BookMenu", new Vector2(0, -14), new Vector2(W - 40, H - 100));
            Img(bookMenu, "Bg", Vector2.zero, bookMenu.sizeDelta, TileBg, stretch: true);
            float mt = bookMenu.sizeDelta.y / 2;
            menuTitle = Text(bookMenu, "", 26, FontStyles.Bold, Ink, TextAlignmentOptions.Left); Place(menuTitle.rectTransform, new Vector2(-70, mt - 30), new Vector2(560, 36));
            menuAuthor = Text(bookMenu, "", 16, FontStyles.Italic, Soft, TextAlignmentOptions.Left); Place(menuAuthor.rectTransform, new Vector2(-70, mt - 60), new Vector2(560, 24));
            (menuBackBtn, _) = Button(bookMenu, "\u2039 shelf", new Vector2(bookMenu.sizeDelta.x / 2 - 80, mt - 30), new Vector2(130, 40), 17, CloseMenu);
            (resumeBtn, _) = Button(bookMenu, "resume reading \u203a", new Vector2(0, mt - 120), new Vector2(420, 58), 22, () => Open(menuSlug));
            var roomsLbl = Text(bookMenu, "Reading rooms", 16, FontStyles.SmallCaps, Accent, TextAlignmentOptions.Left); Place(roomsLbl.rectTransform, new Vector2(0, mt - 172), new Vector2(660, 24));
            (ownRoomBtn, ownRoomLbl) = Button(bookMenu, "", new Vector2(-165, mt - 210), new Vector2(320, 46), 17, () => { if (Lobby) Lobby.Open(menuSlug, LobbyController.ReadingScene[menuSlug]); });
            (libraryRoomBtn, _) = Button(bookMenu, "the library", new Vector2(165, mt - 210), new Vector2(320, 46), 17, () => { if (Lobby) Lobby.Open(menuSlug, LobbyController.ImportedScene); });
            var expLbl = Text(bookMenu, "Chapter experiences", 16, FontStyles.SmallCaps, Accent, TextAlignmentOptions.Left); Place(expLbl.rectTransform, new Vector2(0, mt - 262), new Vector2(660, 24));
            menuChapters = Text(bookMenu, "", 15, FontStyles.Normal, Ink, TextAlignmentOptions.TopLeft); Place(menuChapters.rectTransform, new Vector2(-110, mt - 300), new Vector2(440, 50));
            (chaptersBtn, _) = Button(bookMenu, "chapter experiences \u203a", new Vector2(220, mt - 296), new Vector2(240, 46), 17, () => { FlowController.PendingMenu = "chapters"; Open(menuSlug); });
            bookMenu.gameObject.SetActive(false);
        }

        /// A book was chosen (a tile, or a book on the shelf): its menu, before any room loads.
        public void ShowBookMenu(string slug)
        {
            menuSlug = slug; adding = false; addCard.gameObject.SetActive(false);
            var e = Entries().FirstOrDefault(x => x.Slug == slug);
            menuTitle.text = e?.Title ?? slug; menuAuthor.text = (e?.Author ?? "") + (e != null && e.Bundled ? "  \u00b7  Fable edition" : "  \u00b7  your book");
            bool own = LobbyController.ReadingScene.TryGetValue(slug, out var ownScene) && Application.CanStreamedLevelBeLoaded(ownScene);
            ownRoomBtn.gameObject.SetActive(own);
            if (own) ownRoomLbl.text = ownScene switch { "HallOfDoors" => "the Hall of Doors", "KansasFarmhouse" => "the Kansas farmhouse", "CalypsosCave" => "Calypso\u2019s cave", "GlumdalclitchsRoom" => "Glumdalclitch\u2019s room", _ => ownScene };
            bool supported = ChapterExperiences.Supported.Contains(slug);
            chaptersBtn.gameObject.SetActive(supported);
            menuChapters.text = supported ? ChapterSummary(slug) : "Prepared for Fable\u2019s own four books; not yet for books you add.";
            bookMenu.gameObject.SetActive(true); grid.gameObject.SetActive(false);
            Debug.Log($"[Fable] library board: menu for {slug}");
            Refresh();
        }

        void CloseMenu() { menuSlug = null; bookMenu.gameObject.SetActive(false); Refresh(); }

        /// How many of the book's experiences can be entered and how many are being prepared. Nothing about unfinished chapters.
        static string ChapterSummary(string slug)
        {
            var ce = ChapterExperiences.Instance; int ready = 0, prep = 0, failed = 0;
            foreach (var r in ce.Records(slug))
            {
                if (!r.Completed) continue;
                var st = ce.StateOf(r.Chapter);
                if (st == ChapterExperiences.State.Available) ready++; else if (st == ChapterExperiences.State.Preparing) prep++; else if (st == ChapterExperiences.State.Failed) failed++;
            }
            if (ready + prep + failed == 0) return "Finish a chapter to unlock its experience. Each one is prepared while you read it.";
            return $"{ready} ready to step into" + (prep > 0 ? $" \u00b7 {prep} being prepared" : "") + (failed > 0 ? $" \u00b7 {failed} to retry" : "");
        }

        Tile MakeTile(int i)
        {
            int c = i % Cols, r = i / Cols;
            var t = new Tile();
            t.Rt = Rect(grid, "Tile" + i, new Vector2(-grid.sizeDelta.x / 2 + TileW / 2 + c * (TileW + Gap), grid.sizeDelta.y / 2 - TileH / 2 - r * (TileH + Gap)), new Vector2(TileW, TileH));
            t.Bg = Img(t.Rt, "Bg", Vector2.zero, new Vector2(TileW, TileH), TileBg, stretch: true);
            var o = t.Bg.gameObject.AddComponent<Outline>(); o.effectColor = new Color(0.55f, 0.45f, 0.30f, 0.6f); o.effectDistance = new Vector2(1.5f, -1.5f);
            // cover on the left, 2:3
            t.Cover = Img(t.Rt, "CoverBg", new Vector2(-TileW / 2 + 8 + 38, 16), new Vector2(76, 114), new Color(0.3f, 0.25f, 0.2f));
            t.CoverTex = new GameObject("Cover", typeof(RectTransform)).AddComponent<RawImage>(); t.CoverTex.transform.SetParent(t.Cover.rectTransform, false); t.CoverTex.raycastTarget = false;
            t.CoverTex.rectTransform.anchorMin = Vector2.zero; t.CoverTex.rectTransform.anchorMax = Vector2.one; t.CoverTex.rectTransform.offsetMin = t.CoverTex.rectTransform.offsetMax = Vector2.zero;
            t.CoverTitle = Text(t.Cover.rectTransform, "", 11, FontStyles.Bold, new Color(0.97f, 0.93f, 0.84f), TextAlignmentOptions.Center); Place(t.CoverTitle.rectTransform, Vector2.zero, new Vector2(68, 104));
            t.CoverTitle.enableAutoSizing = true; t.CoverTitle.fontSizeMin = 8; t.CoverTitle.fontSizeMax = 13; t.CoverTitle.textWrappingMode = TextWrappingModes.Normal;
            float tx = -TileW / 2 + 8 + 76 + 8, tw = TileW - 8 - 76 - 8 - 8;
            t.Title = Text(t.Rt, "", 17f, FontStyles.Bold, Ink, TextAlignmentOptions.TopLeft); PlaceTL(t.Title.rectTransform, new Vector2(tx, TileH / 2 - 8), new Vector2(tw, 62));
            t.Title.textWrappingMode = TextWrappingModes.Normal; t.Title.overflowMode = TextOverflowModes.Ellipsis; t.Title.lineSpacing = -14;
            t.Author = Text(t.Rt, "", 13.5f, FontStyles.Italic, Soft, TextAlignmentOptions.TopLeft); PlaceTL(t.Author.rectTransform, new Vector2(tx, TileH / 2 - 70), new Vector2(tw, 34));
            t.Author.textWrappingMode = TextWrappingModes.Normal; t.Author.overflowMode = TextOverflowModes.Ellipsis; t.Author.lineSpacing = -18;
            t.Badge = Text(t.Rt, "", 12, FontStyles.SmallCaps, Accent, TextAlignmentOptions.TopLeft); PlaceTL(t.Badge.rectTransform, new Vector2(tx, TileH / 2 - 106), new Vector2(tw, 20));
            t.Badge.overflowMode = TextOverflowModes.Ellipsis;
            t.Status = Text(t.Rt, "", 13, FontStyles.Normal, Ink, TextAlignmentOptions.TopLeft); PlaceTL(t.Status.rectTransform, new Vector2(-TileW / 2 + 8, -TileH / 2 + 26), new Vector2(TileW - 16 - 64, 20));
            t.Status.overflowMode = TextOverflowModes.Ellipsis;
            t.BarBack = Img(t.Rt, "BarBack", new Vector2(0, -TileH / 2 + 6), new Vector2(TileW - 16, 5), new Color(0.85f, 0.80f, 0.70f));
            t.Bar = Img(t.Rt, "Bar", new Vector2(0, -TileH / 2 + 6), new Vector2(TileW - 16, 5), Accent); t.Bar.type = Image.Type.Filled; t.Bar.fillMethod = Image.FillMethod.Horizontal; t.Bar.sprite = WhiteSprite();
            (t.Remove, t.RemoveLbl) = Button(t.Rt, "remove", new Vector2(TileW / 2 - 6 - 32, -TileH / 2 + 18), new Vector2(64, 26), 12.5f, null);
            return t;
        }

        // ---------------------------------------------------------------- refreshing

        float nextRefresh;
        public void Refresh()
        {
            if (!root) return;
            var all = Entries();
            int bundled = all.Count(e => e.Bundled), imported = all.Count(e => e.Lib != null);
            headerCount.text = $"{bundled} Fable editions · {imported} of your own" + (all.Any(e => e.Job != null && !e.Job.Done) ? " · one arriving" : "");
            var last = ProgressStore.LastBook(); var lastEntry = all.FirstOrDefault(e => e.Slug == last);
            continueBtn.gameObject.SetActive(lastEntry != null && !adding);
            if (lastEntry != null) continueLbl.text = $"continue: <i>{Shorten(lastEntry.Title, 22)}</i> ›";
            addBtn.gameObject.SetActive(!adding);
            page = Mathf.Clamp(page, 0, Pages - 1);
            shown.Clear();
            for (int i = 0; i < PerPage; i++)
            {
                var t = tiles[i]; int k = page * PerPage + i;
                bool on = !adding && menuSlug == null && k < all.Count; t.Rt.gameObject.SetActive(on); if (!on) continue;
                Fill(t, all[k]); shown.Add(t);
            }
            grid.gameObject.SetActive(!adding && menuSlug == null);
            if (menuSlug != null) { addBtn.gameObject.SetActive(false); continueBtn.gameObject.SetActive(false); }
            prevBtn.gameObject.SetActive(!adding && menuSlug == null && page > 0); nextBtn.gameObject.SetActive(!adding && menuSlug == null && page < Pages - 1);
            pageLbl.text = adding || menuSlug != null ? "" : Pages > 1 ? $"shelf {page + 1} of {Pages}" : "";
            storageLbl.text = adding || menuSlug != null ? "" : $"your books use {lib.UsedBytes / 1048576f:F1} MB of {Library.MaxLibraryBytes >> 30} GB" + (lib.FreeBytes < long.MaxValue ? $" · {lib.FreeBytes / 1073741824f:F1} GB free on the headset" : "");
            if (adding) FillAdd();
        }

        void Fill(Tile t, Entry e)
        {
            t.Key = e.Key; t.State = e.Job != null ? e.Job.Status : null;
            t.Title.text = e.Title ?? "Untitled";
            t.Author.text = e.Author ?? (e.Job != null ? "" : "author not given");
            var tex = CoverFor(e);
            t.CoverTex.texture = tex; t.CoverTex.gameObject.SetActive(tex);
            t.CoverTitle.text = tex ? "" : $"{e.Title}" + (e.Author != null ? $"\n<size=75%><i>{e.Author}</i></size>" : "");
            t.Cover.color = tex ? Color.black : Hue(e.Title ?? e.Key);
            t.Remove.gameObject.SetActive(false); t.Act = null; t.RemoveAct = null;
            t.Bar.gameObject.SetActive(false); t.BarBack.gameObject.SetActive(false);
            if (e.Job != null)
            {
                var j = e.Job;
                if (j.Status == "failed" || j.Status == "duplicate")
                {
                    t.Badge.text = j.Status == "duplicate" ? "already on your shelf" : "could not be added"; t.Badge.color = j.Status == "duplicate" ? Accent : Bad;
                    t.Status.text = "pinch for details"; t.Status.color = Ink;
                    t.Act = () => { if (!adding) OpenAdd(); watching = j; FillAdd(); };
                    t.RemoveAct = () => lib.Dismiss(j); t.Remove.gameObject.SetActive(true); t.RemoveLbl.text = "dismiss";
                }
                else
                {
                    t.Badge.text = j.Status == "receiving" ? "arriving" : "importing"; t.Badge.color = Accent;
                    t.Status.text = StageLine(j); t.Status.color = Ink;
                    t.BarBack.gameObject.SetActive(true); t.Bar.gameObject.SetActive(true);
                    t.Bar.fillAmount = j.Progress >= 0 ? j.Progress : Mathf.PingPong(Time.time * 0.6f, 1f);
                    t.Bar.fillOrigin = 0;
                }
                t.Author.text = j.FileName;
                return;
            }
            t.Badge.text = e.Badge; t.Badge.color = e.Bundled ? Accent : Soft;
            t.Status.text = e.Progress; t.Status.color = Ink;
            var slug = e.Slug;
            t.Act = () => ShowBookMenu(slug);
            if (e.Lib != null)
            {
                t.Remove.gameObject.SetActive(hoveredKey == e.Key || Time.time < t.ConfirmUntil);
                t.RemoveLbl.text = Time.time < t.ConfirmUntil ? "sure?" : "remove";
                t.RemoveAct = () =>
                {
                    if (Time.time < t.ConfirmUntil) { t.ConfirmUntil = 0; lib.Remove(slug); }
                    else { t.ConfirmUntil = Time.time + 4f; Refresh(); }
                };
            }
        }

        static string StageLine(LibraryJob j) =>
            j.Status == "receiving" ? (j.Expected > 0 ? $"{j.Received / 1048576f:F1} of {j.Expected / 1048576f:F1} MB" : "receiving") :
            j.Progress >= 0 ? $"{j.Stage} · {j.Progress * 100:F0}%" : j.Stage;

        Texture CoverFor(Entry e)
        {
            if (e.Bundled) return Bundled.TryGetValue(e.Slug, out var b) ? b.cover : null;
            if (e.Lib == null || e.Lib.Cover == null) return null;
            if (covers.TryGetValue(e.Slug, out var t)) return t;
            var path = Path.Combine(Library.BookDir(e.Slug), e.Lib.Cover);
            Texture2D tex = null;
            try { if (File.Exists(path)) { tex = new Texture2D(2, 2, TextureFormat.RGBA32, true) { name = "cover " + e.Slug }; if (!tex.LoadImage(File.ReadAllBytes(path), true)) { Destroy(tex); tex = null; } } }
            catch (Exception ex) { Debug.LogWarning($"[Fable] cover for {e.Slug} unreadable: {ex.Message}"); }
            covers[e.Slug] = tex;
            return tex;
        }

        /// A muted cloth colour from the title, for books with no cover image.
        static Color Hue(string s)
        {
            int h = 17; foreach (var c in s) h = h * 31 + c;
            return Color.HSVToRGB(Mathf.Abs(h % 360) / 360f, 0.42f, 0.38f);
        }

        // ---------------------------------------------------------------- adding a book

        void OpenAdd()
        {
            adding = true; lib.Accepting = true;
            var url = lib.StartServer();
            addCard.gameObject.SetActive(true);
            Debug.Log($"[Fable] library: add a book at {url ?? lib.Server?.Error} code {lib.Code}");
            Refresh();
        }

        void CloseAdd() { adding = false; lib.Accepting = false; watching = null; addCard.gameObject.SetActive(false); Refresh(); }

        void FillAdd()
        {
            var url = lib.Server != null && lib.Server.Running ? lib.Server.Url : null;
            if (url == null)
            {
                addStep1.text = "<b>The upload page could not start.</b>"; addStep2.text = lib.Server?.Error ?? "Unknown problem.";
                addStep3.text = "Check that the headset is on Wi-Fi (Settings, Wi-Fi),"; addStep4.text = "then go ‹ back to the shelf and open “+ add a book” again.";
                addAddress.text = ""; addCode.text = "";
            }
            else
            {
                addStep1.text = "1.  Connect your phone or computer to the <b>same Wi-Fi</b> as this headset.";
                addStep2.text = "2.  In its web browser, open this address:";
                addStep3.text = "3.  Type the code";
                addStep4.text = "4.  Choose an EPUB or PDF and press <b>Send to headset</b>. You can read meanwhile.";
                addAddress.text = url; addCode.text = lib.Code;
            }
            addBody.text = $"Fable reads EPUB books without DRM, and PDFs, up to {Library.MaxFileBytes >> 20} MB each. Not yet: Kindle files (MOBI, AZW, KFX), DRM-protected books, Word documents, plain text.";
            // the transfer to follow: the one being watched, else the newest
            var jobs = lib.ActiveJobs();
            var j = watching != null && jobs.Contains(watching) ? watching : jobs.OrderByDescending(x => x.Started).FirstOrDefault();
            if (j == null)
            {
                var v = lib.Server?.LastVisitor;
                Status(v != null && (DateTime.UtcNow - lib.Server.LastVisit).TotalMinutes < 10 ? $"Connected: the page is open on {v}. Waiting for a book…" : "Waiting for your phone or computer to open the page…", false);
                statusBar.gameObject.SetActive(false); statusBarBack.gameObject.SetActive(false);
                return;
            }
            statusBar.gameObject.SetActive(true); statusBarBack.gameObject.SetActive(true);
            switch (j.Status)
            {
                case "receiving": Status($"Receiving <b>{j.FileName}</b>: {j.Received / 1048576f:F1} of {j.Expected / 1048576f:F1} MB", false); statusBar.fillAmount = Mathf.Max(0, j.Progress); break;
                case "importing": Status($"Importing <b>{j.FileName}</b>: {StageLine(j)}", false); statusBar.fillAmount = j.Progress >= 0 ? j.Progress : Mathf.PingPong(Time.time * 0.6f, 1f); break;
                case "ready": Status($"<b>“{j.Title}”</b> is on your shelf. Send another, or go ‹ back to the shelf to open it.", false); statusBar.fillAmount = 1; break;
                case "duplicate": Status(j.Message, false); statusBar.gameObject.SetActive(false); statusBarBack.gameObject.SetActive(false); break;
                default: Status($"<b>{j.FileName} was not added.</b> {j.Message} <i>{j.Recovery}</i>", true); statusBar.gameObject.SetActive(false); statusBarBack.gameObject.SetActive(false); break;
            }
        }

        void Status(string s, bool bad) { if (!statusText) return; statusText.text = s; statusText.color = bad ? Bad : Ink; }

        // ---------------------------------------------------------------- opening

        void Open(string slug) { if (Lobby) Lobby.Open(slug); }

        void ContinueReading()
        {
            var slug = ProgressStore.LastBook();
            if (slug != null && (Bundled.ContainsKey(slug) || lib.Find(slug) != null)) ShowBookMenu(slug);
        }

        /// Test hook: what a pinch on a control or tile would do, by its key ("add", "back", "next", "prev", "continue", a slug, "remove:<slug>").
        public string Press(string key)
        {
            if (key.StartsWith("menu:")) { var tg = Targets().FirstOrDefault(x => x.key == key); if (tg.act == null) return "no " + key; tg.act(); return Describe(); }
            if (key == "add") OpenAdd(); else if (key == "back") CloseAdd(); else if (key == "next") { page = Mathf.Min(Pages - 1, page + 1); Refresh(); }
            else if (key == "prev") { page = Mathf.Max(0, page - 1); Refresh(); } else if (key == "continue") ContinueReading();
            else if (key.StartsWith("remove:")) { var t = shown.FirstOrDefault(x => x.Key == key.Substring(7)); t?.RemoveAct?.Invoke(); }
            else
            {
                // a tile on another shelf page: turn to it first, as a reader would
                int at = Entries().FindIndex(e => e.Key == key); if (at >= 0 && at / PerPage != page) { page = at / PerPage; Refresh(); }
                var t = shown.FirstOrDefault(x => x.Key == key); if (t?.Act == null) return "no tile " + key; t.Act();
            }
            return Describe();
        }

        // ---------------------------------------------------------------- pointing

        bool Ray(bool right, out Ray r)
        {
            r = default;
            if (right && TestRay.HasValue) { r = TestRay.Value; return true; }
#if FABLE_META_XR
            if (Input && Input.PointRay(right, out r)) return true;
#endif
#if UNITY_EDITOR || UNITY_STANDALONE
            if (right && !UnityEngine.XR.XRSettings.isDeviceActive && Camera.main && UnityEngine.InputSystem.Mouse.current != null)
            { r = Camera.main.ScreenPointToRay(UnityEngine.InputSystem.Mouse.current.position.ReadValue()); return true; }
#endif
            return false;
        }

        /// Where a hand's ray meets the board, in world space, if it does.
        public bool OnBoard(bool right, out Vector3 world)
        {
            world = default;
            if (!root || !Ray(right, out var r)) return false;
            var plane = new Plane(-root.forward, root.position);
            if (!plane.Raycast(r, out float d) || d < 0 || d > 4f || Vector3.Dot(r.direction, root.forward) <= 0) return false;
            world = r.GetPoint(d);
            var local = root.InverseTransformPoint(world);
            return root.rect.Contains(local);
        }

        static bool Over(RectTransform rt, Vector3 world, float pad = 6)
        {
            if (!rt || !rt.gameObject.activeInHierarchy) return false;
            var r = rt.rect; r.xMin -= pad; r.xMax += pad; r.yMin -= pad; r.yMax += pad;
            return r.Contains(rt.InverseTransformPoint(world));
        }

        /// Everything on the board a pinch can press, in order of priority, with what it does.
        IEnumerable<(RectTransform rt, string key, Action act)> Targets()
        {
            if (adding) { yield return (backBtn, "back", CloseAdd); yield break; }
            if (menuSlug != null)
            {
                yield return (menuBackBtn, "menu:back", CloseMenu); yield return (resumeBtn, "menu:resume", () => Open(menuSlug));
                yield return (ownRoomBtn, "menu:own-room", () => { if (Lobby) Lobby.Open(menuSlug, LobbyController.ReadingScene[menuSlug]); });
                yield return (libraryRoomBtn, "menu:library-room", () => { if (Lobby) Lobby.Open(menuSlug, LobbyController.ImportedScene); });
                yield return (chaptersBtn, "menu:chapters", () => { FlowController.PendingMenu = "chapters"; Open(menuSlug); });
                yield break;
            }
            yield return (addBtn, "add", OpenAdd);
            yield return (continueBtn, "continue", ContinueReading);
            yield return (prevBtn, "prev", () => { page = Mathf.Max(0, page - 1); Refresh(); });
            yield return (nextBtn, "next", () => { page = Mathf.Min(Pages - 1, page + 1); Refresh(); });
            foreach (var t in shown) { var tt = t; if (t.Remove.gameObject.activeSelf) yield return (t.Remove, "remove:" + t.Key, () => tt.RemoveAct?.Invoke()); }
            foreach (var t in shown) yield return (t.Rt, t.Key, t.Act);
        }

        bool Claim(bool right)
        {
            if (!OnBoard(right, out var w)) return false;
            foreach (var (rt, key, act) in Targets()) if (Over(rt, w)) { Debug.Log($"[Fable] library board: {key}"); act?.Invoke(); return true; }
            return true;   // on the board, between things: still not the shelf behind it
        }

        void Update()
        {
            if (!root) return;
            if (gliding)
            {
                float k = 1f - Mathf.Exp(-Time.deltaTime * 6f);
                root.position = Vector3.Lerp(root.position, target, k); root.rotation = Quaternion.Slerp(root.rotation, targetRot, k);
                if ((root.position - target).sqrMagnitude < 1e-6f) gliding = false;
            }
            // hover
            string key = null; RectTransform rtOver = null;
            foreach (var right in new[] { true, false })
                if (OnBoard(right, out var w)) { foreach (var (rt, k2, _) in Targets()) if (Over(rt, w)) { key = k2; rtOver = rt; break; } break; }
            if (key != hoveredKey) { var before = hoveredKey; hoveredKey = key; hoveredRt = rtOver; if ((before ?? "").StartsWith("u-") || (key ?? "").StartsWith("u-") || (before ?? "").StartsWith("remove:") || (key ?? "").StartsWith("remove:")) Refresh(); }
            foreach (var t in shown) { var lit = hoveredKey == t.Key; var c = lit ? Lit : TileBg; if (t.Bg.color != c) t.Bg.color = c; t.Rt.localScale = Vector3.one * (lit ? 1.035f : 1f); }
            foreach (var b in new[] { addBtn, continueBtn, prevBtn, nextBtn, backBtn, resumeBtn, ownRoomBtn, libraryRoomBtn, chaptersBtn, menuBackBtn }) Light(b, hoveredRt == b);
            foreach (var t in shown) Light(t.Remove, hoveredRt == t.Remove);
            // live jobs: progress a few times a second
            if (Time.time > nextRefresh && (adding || lib.ActiveJobs().Any(j => !j.Done))) { nextRefresh = Time.time + 0.25f; Refresh(); }
        }

        static void Light(RectTransform b, bool on)
        {
            if (!b) return; var img = b.GetComponent<Image>(); var c = on ? Lit : new Color(0.99f, 0.96f, 0.89f, 1f);
            if (img && img.color != c) img.color = c;
        }

        // ---------------------------------------------------------------- small builders

        static Sprite white;
        static Sprite WhiteSprite() { if (white) return white; var t = new Texture2D(4, 4); var px = new Color[16]; for (int i = 0; i < 16; i++) px[i] = Color.white; t.SetPixels(px); t.Apply(); return white = Sprite.Create(t, new Rect(0, 0, 4, 4), new Vector2(0.5f, 0.5f)); }

        static RectTransform Rect(RectTransform parent, string name, Vector2 pos, Vector2 size)
        {
            var rt = new GameObject(name, typeof(RectTransform)).GetComponent<RectTransform>(); rt.SetParent(parent, false);
            rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(0.5f, 0.5f); rt.anchoredPosition = pos; rt.sizeDelta = size; return rt;
        }

        static Image Img(RectTransform parent, string name, Vector2 pos, Vector2 size, Color c, bool stretch = false)
        {
            var im = new GameObject(name, typeof(RectTransform)).AddComponent<Image>(); im.transform.SetParent(parent, false); im.color = c; im.raycastTarget = false;
            var rt = im.rectTransform;
            if (stretch) { rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one; rt.offsetMin = rt.offsetMax = Vector2.zero; }
            else { rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(0.5f, 0.5f); rt.anchoredPosition = pos; rt.sizeDelta = size; }
            return im;
        }

        TMP_Text Text(RectTransform parent, string s, float size, FontStyles style, Color c, TextAlignmentOptions align)
        {
            var t = new GameObject("Text", typeof(RectTransform)).AddComponent<TextMeshProUGUI>(); t.transform.SetParent(parent, false);
            if (Font) t.font = Font; t.text = s; t.fontSize = size; t.fontStyle = style; t.color = c; t.alignment = align; t.raycastTarget = false; t.richText = true;
            t.textWrappingMode = TextWrappingModes.Normal;
            return t;
        }

        static void Place(RectTransform rt, Vector2 pos, Vector2 size) { rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(0.5f, 0.5f); rt.anchoredPosition = pos; rt.sizeDelta = size; }
        static void PlaceTL(RectTransform rt, Vector2 topLeft, Vector2 size) { rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f); rt.pivot = new Vector2(0, 1); rt.anchoredPosition = topLeft; rt.sizeDelta = size; }

        (RectTransform, TMP_Text) Button(RectTransform parent, string label, Vector2 pos, Vector2 size, float fontSize, Action act)
        {
            var rt = Rect(parent, "Btn " + label, pos, size);
            var img = rt.gameObject.AddComponent<Image>(); img.color = new Color(0.99f, 0.96f, 0.89f, 1f); img.raycastTarget = false;
            var o = rt.gameObject.AddComponent<Outline>(); o.effectColor = new Color(0.45f, 0.33f, 0.18f, 0.9f); o.effectDistance = new Vector2(1.5f, -1.5f);
            var t = Text(rt, label, fontSize, FontStyles.SmallCaps, Ink, TextAlignmentOptions.Center); t.textWrappingMode = TextWrappingModes.NoWrap; t.overflowMode = TextOverflowModes.Ellipsis;
            t.rectTransform.anchorMin = Vector2.zero; t.rectTransform.anchorMax = Vector2.one; t.rectTransform.offsetMin = new Vector2(6, 0); t.rectTransform.offsetMax = new Vector2(-6, 0);
            return (rt, t);
        }

        static string Shorten(string s, int n) => s == null ? "" : s.Length <= n ? s : s.Substring(0, n - 1) + "…";
    }
}
