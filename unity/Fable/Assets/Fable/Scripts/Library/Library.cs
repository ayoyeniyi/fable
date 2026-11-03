// The reader's personal library: the four bundled books plus whatever they import. One instance lives for the whole
// app run (it survives scene loads), so a book keeps importing while the reader reads something else.
//
// On the headset, under persistentDataPath/library/:
//   library.json             the imported books (title, author, format, size, hash, what the import found)
//   <slug>/book.json         the book in Fable's shape (chapters -> paragraphs -> sentences with stable ids)
//   <slug>/cover.jpg|png     the cover: the EPUB's own, or page 1 of a PDF; absent when there is none
//   <slug>/source.pdf        a PDF, kept as it is, for the page view
//   .incoming/, .staging/    a transfer in progress and an import being assembled; never read as books
// An import is assembled in .staging and moved into place in one step only when it is complete, and library.json is
// written beside and swapped in, so a failed or interrupted import never touches the books already there.
// Reading positions, bookmarks and preferences live with the bundled books' in progress.json (ProgressStore).
//
// Limits (documented in docs/LIBRARY.md): 150 MB a file, 2 GB for all imported books, 300 books, and at least
// 300 MB left free on the headset after an import.
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Newtonsoft.Json;
using UnityEngine;

namespace Fable
{
    [Serializable, UnityEngine.Scripting.Preserve]
    public class LibraryEntry
    {
        public string Slug, Title, Author, Format, FileName, Sha256, Cover, AddedUtc, Note;
        public long Bytes;
        public int Chapters, Sentences, PdfPages, TextPages;
        [JsonIgnore] public bool Bundled;
        /// Text features (highlight, Define, Search, the text view) are possible: false for a scanned PDF.
        [JsonIgnore] public bool HasText => Format != "pdf" || TextPages > 0;
        [UnityEngine.Scripting.Preserve] public LibraryEntry() { }
    }

    [Serializable, UnityEngine.Scripting.Preserve]
    public class LibraryIndex { public List<LibraryEntry> Books = new(); [UnityEngine.Scripting.Preserve] public LibraryIndex() { } }

    /// One upload and import, from the first byte to a book on the shelf (or a reason it is not there).
    public class LibraryJob
    {
        public string Id, FileName, Slug, Title;
        public long Expected, Received;
        /// receiving | importing | ready | failed | duplicate
        public volatile string Status = "receiving";
        public string Stage = "receiving";
        public float Progress = -1;            // 0..1 where it can be measured, -1 where it cannot
        public string Message, Recovery;
        public DateTime Started = DateTime.UtcNow, Ended;
        public bool Done => Status == "ready" || Status == "failed" || Status == "duplicate";
    }

    public class Library : MonoBehaviour
    {
        public const long MaxFileBytes = 150L << 20, MaxLibraryBytes = 2L << 30, MinFreeBytes = 300L << 20;
        public const int MaxBooks = 300;
        public static readonly string[] Formats = { "EPUB (DRM-free)", "PDF" };

        static Library instance;
        public static Library Instance
        {
            get
            {
                if (instance) return instance;
                var go = new GameObject("Library"); DontDestroyOnLoad(go);
                instance = go.AddComponent<Library>(); instance.Load();
                return instance;
            }
        }
        public static bool Exists => instance;

        /// Set on the main thread when the library loads: Unity's persistentDataPath cannot be read from the server's threads.
        public static string Root { get; private set; }
        static string IndexPath => Path.Combine(Root, "library.json");
        public static string BookDir(string slug) => Path.Combine(Root, slug);
        public static bool IsImported(string slug) => slug != null && slug.StartsWith("u-");

        public readonly List<LibraryEntry> Imported = new();
        public readonly List<LibraryJob> Jobs = new();
        /// Raised on the main thread whenever a book or job changes.
        public event Action Changed;
        /// Raised on the main thread when a book becomes ready (for a note wherever the reader is).
        public event Action<LibraryEntry> BookReady;

        public UploadServer Server { get; private set; }
        /// The four digits shown in the headset that the upload page asks for.
        public string Code { get; private set; }
        /// Uploads are accepted while the "Add a book" card is open (and a transfer under way may always finish).
        public bool Accepting { get; set; }
        /// Usable space on the headset's storage, refreshed every few seconds on the main thread.
        public long FreeBytes { get; private set; } = long.MaxValue;
        public long UsedBytes { get; private set; }
        public string StartupNote { get; private set; }

        readonly ConcurrentQueue<Action> main = new();
        readonly object gate = new();
        float nextFree;

        void Load()
        {
            Root = Path.Combine(Application.persistentDataPath, "library");
            Directory.CreateDirectory(Root);
            try
            {
                if (File.Exists(IndexPath))
                {
                    var idx = JsonConvert.DeserializeObject<LibraryIndex>(File.ReadAllText(IndexPath)) ?? new LibraryIndex();
                    foreach (var e in idx.Books ?? new List<LibraryEntry>())
                        if (e != null && IsImported(e.Slug) && File.Exists(Path.Combine(BookDir(e.Slug), "book.json"))) Imported.Add(e);
                        else Debug.LogWarning($"[Fable] library: {e?.Slug} is listed but its files are missing; dropped from the shelf");
                }
            }
            catch (Exception ex) { Debug.LogWarning($"[Fable] library index unreadable ({ex.Message}); keeping the books found on disk"); Rescan(); }
            // leftovers from a run that stopped mid-transfer or mid-import: nothing of them reached the library
            int leftovers = 0;
            foreach (var d in new[] { ".incoming", ".staging" })
            {
                var p = Path.Combine(Root, d);
                if (Directory.Exists(p)) { leftovers += Directory.GetFileSystemEntries(p).Length; try { Directory.Delete(p, true); } catch { } }
            }
            if (leftovers > 0) StartupNote = "An import was interrupted when Fable last closed. Nothing from it was added; send the file again.";
            UsedBytes = Imported.Sum(e => e.Bytes);
            Code = NewCode();
            RefreshFree();
            Debug.Log($"[Fable] library: {Imported.Count} imported books, {UsedBytes / 1048576f:F1} MB; {(leftovers > 0 ? leftovers + " unfinished imports cleared" : "nothing unfinished")}");
        }

        /// The index was lost: list the complete book folders instead (their book.json carries title and author).
        void Rescan()
        {
            Imported.Clear();
            foreach (var dir in Directory.GetDirectories(Root))
            {
                var slug = Path.GetFileName(dir); var bj = Path.Combine(dir, "book.json");
                if (!IsImported(slug) || !File.Exists(bj)) continue;
                try
                {
                    var b = Book.Parse(File.ReadAllText(bj));
                    var cover = Directory.GetFiles(dir, "cover.*").Select(Path.GetFileName).FirstOrDefault();
                    Imported.Add(new LibraryEntry { Slug = slug, Title = b.Title, Author = b.Author, Format = b.Format, Cover = cover, Chapters = b.Chapters.Count, Sentences = b.SentenceCount, PdfPages = b.PdfPages, TextPages = b.IsPdf ? b.Chapters.Count : 0, Bytes = DirBytes(dir), AddedUtc = Directory.GetCreationTimeUtc(dir).ToString("o") });
                }
                catch { }
            }
            SaveIndex();
        }

        static string NewCode() => UnityEngine.Random.Range(1000, 10000).ToString();
        /// A new code (after repeated wrong guesses on the upload page).
        public void RotateCode() { main.Enqueue(() => { Code = NewCode(); Changed?.Invoke(); Debug.Log("[Fable] library: upload code changed after repeated wrong codes"); }); }

        void SaveIndex()
        {
            try
            {
                var tmp = IndexPath + ".tmp";
                File.WriteAllText(tmp, JsonConvert.SerializeObject(new LibraryIndex { Books = Imported }, Formatting.Indented));
                ProgressStore.Swap(tmp, IndexPath);
            }
            catch (Exception e) { Debug.LogError($"[Fable] library index not saved: {e.Message}"); }
        }

        static long DirBytes(string dir) { try { return new DirectoryInfo(dir).GetFiles("*", SearchOption.AllDirectories).Sum(f => f.Length); } catch { return 0; } }

        void RefreshFree()
        {
            try
            {
#if UNITY_ANDROID && !UNITY_EDITOR
                using var f = new AndroidJavaObject("java.io.File", Application.persistentDataPath); FreeBytes = f.Call<long>("getUsableSpace");
#else
                FreeBytes = new DriveInfo(Path.GetPathRoot(Application.persistentDataPath)).AvailableFreeSpace;
#endif
            }
            catch { FreeBytes = long.MaxValue; }
        }

        void Update()
        {
            while (main.TryDequeue(out var a)) { try { a(); } catch (Exception e) { Debug.LogException(e); } }
            if (Time.unscaledTime > nextFree) { nextFree = Time.unscaledTime + 3f; RefreshFree(); }
        }

        void OnApplicationQuit() { Server?.Stop(); }
        void OnDestroy() { Server?.Stop(); if (instance == this) instance = null; }

        void Notify() => main.Enqueue(() => Changed?.Invoke());

        // ---------------------------------------------------------------- the upload server

        /// Start listening for the upload page (idempotent). Returns the address to type, or null with Server.Error.
        public string StartServer()
        {
            Server ??= new UploadServer(this);
            if (!Server.Running) Server.Start(8642);
            return Server.Running ? Server.Url : null;
        }

        // ---------------------------------------------------------------- transfers (called from the server's threads)

        /// Whether a transfer of this size may start: the reason it may not, in plain words, or null.
        public string CanAccept(string fileName, long bytes, out string recovery)
        {
            recovery = null;
            var ext = Path.GetExtension(fileName ?? "").ToLowerInvariant();
            var kind = KindFromExtension(ext);
            if (kind != null) { recovery = UnsupportedRecovery(kind); return $"{Path.GetFileName(fileName)} is a {kind} file. Fable reads EPUB and PDF books."; }
            if (ext != ".epub" && ext != ".pdf") { recovery = "Choose an .epub or .pdf file."; return $"Fable reads EPUB and PDF books; {Path.GetFileName(fileName)} is neither."; }
            if (bytes <= 0) { recovery = "Choose the file again; the browser did not say how big it is."; return "The file arrived empty."; }
            if (bytes > MaxFileBytes) { recovery = "Choose a smaller edition, or split the PDF into parts."; return $"The file is {bytes / 1048576f:F0} MB; the limit is {MaxFileBytes / 1048576} MB."; }
            lock (gate)
            {
                if (Imported.Count >= MaxBooks) { recovery = "Remove a few imported books on the headset (point at a book's “remove”)."; return $"Your library is full ({MaxBooks} imported books)."; }
                if (UsedBytes + bytes > MaxLibraryBytes) { recovery = "Remove a few imported books on the headset to make room."; return $"Your imported books would take more than {MaxLibraryBytes >> 30} GB."; }
            }
            if (FreeBytes - bytes * 3 < MinFreeBytes) { recovery = "Free some space on the headset (uninstall an app or delete videos), then try again."; return $"The headset is nearly full: {FreeBytes / 1048576f:F0} MB free, and this import needs about {bytes * 3 / 1048576f + MinFreeBytes / 1048576f:F0} MB."; }
            return null;
        }

        public LibraryJob BeginTransfer(string fileName, long bytes)
        {
            var job = new LibraryJob { Id = Guid.NewGuid().ToString("N").Substring(0, 12), FileName = Path.GetFileName(fileName), Expected = bytes, Stage = "receiving", Progress = 0 };
            lock (gate) { Jobs.Add(job); if (Jobs.Count > 20) Jobs.RemoveAll(j => j.Done && (DateTime.UtcNow - j.Ended).TotalMinutes > 30); }
            Debug.Log($"[Fable] library: receiving {job.FileName} ({bytes / 1048576f:F1} MB)");
            Notify(); return job;
        }

        public string IncomingPath(LibraryJob job) { var d = Path.Combine(Root, ".incoming"); Directory.CreateDirectory(d); return Path.Combine(d, job.Id + ".part"); }

        public void TransferProgress(LibraryJob job, long received)
        {
            job.Received = received; job.Progress = job.Expected > 0 ? Mathf.Clamp01(received / (float)job.Expected) : -1;
            Notify();
        }

        public void TransferFailed(LibraryJob job, string why)
        {
            Fail(job, $"The transfer of {job.FileName} stopped after {job.Received / 1048576f:F1} of {job.Expected / 1048576f:F1} MB ({why}). Nothing was added to your library.", "Keep the phone or computer awake and on the same Wi-Fi, and send the file again.");
            try { File.Delete(IncomingPath(job)); } catch { }
        }

        public void TransferDone(LibraryJob job)
        {
            job.Received = job.Expected; job.Status = "importing"; job.Stage = "checking the file"; job.Progress = -1;
            Debug.Log($"[Fable] library: received {job.FileName}, importing");
            Notify();
            var path = IncomingPath(job);
            Task.Run(() => ImportWorker(job, path));
        }

        void Fail(LibraryJob job, string message, string recovery)
        {
            job.Message = message; job.Recovery = recovery; job.Status = "failed"; job.Ended = DateTime.UtcNow; job.Progress = -1;
            Debug.LogWarning($"[Fable] library: {job.FileName}: {message}");
            Notify();
        }

        // ---------------------------------------------------------------- importing (a worker thread, then the main thread)

        void ImportWorker(LibraryJob job, string path)
        {
            string staging = null;
            try
            {
                void Stage(string s, float p) { job.Stage = s; job.Progress = p; Notify(); }
                Stage("checking the file", -1);
                var kind = Sniff(path);
                if (kind != "epub" && kind != "pdf") throw new ImportException(kind == "empty" ? "The file arrived empty." : $"This file is not an EPUB or a PDF{(kind != null ? $" (it looks like {kind})" : "")}.", UnsupportedRecovery(kind));
                var sha = BookText.Sha256(path);
                LibraryEntry dup; lock (gate) dup = Imported.FirstOrDefault(e => e.Sha256 == sha);
                if (dup != null)
                {
                    job.Slug = dup.Slug; job.Title = dup.Title; job.Status = "duplicate"; job.Ended = DateTime.UtcNow;
                    job.Message = $"“{dup.Title}” is already in your library, so it was not added twice.";
                    try { File.Delete(path); } catch { }
                    Debug.Log($"[Fable] library: {job.FileName} is a copy of {dup.Slug}; not added"); Notify(); return;
                }
                var slug = "u-" + sha.Substring(0, 12);
                staging = Path.Combine(Root, ".staging", slug);
                if (Directory.Exists(staging)) Directory.Delete(staging, true);
                Directory.CreateDirectory(staging);
                var entry = new LibraryEntry { Slug = slug, Format = kind, FileName = job.FileName, Sha256 = sha, AddedUtc = DateTime.UtcNow.ToString("o") };
                Book book;
                if (kind == "epub")
                {
                    var r = EpubImport.Read(path, slug, Stage);
                    book = r.Book;
                    if (r.Cover != null) { entry.Cover = "cover" + r.CoverExt; File.WriteAllBytes(Path.Combine(staging, entry.Cover), r.Cover); }
                    entry.Note = r.Note;
                    try { File.Delete(path); } catch { }
                }
                else
                {
                    var r = PdfImport.Read(path, slug, job.FileName, Stage);
                    book = r.Book; entry.PdfPages = r.Pages; entry.TextPages = r.TextPages; entry.Note = r.Note;
                    File.Move(path, Path.Combine(staging, "source.pdf"));
                }
                Stage("saving", -1);
                File.WriteAllText(Path.Combine(staging, "book.json"), JsonConvert.SerializeObject(book, new JsonSerializerSettings { NullValueHandling = NullValueHandling.Ignore, DefaultValueHandling = DefaultValueHandling.Ignore }));
                entry.Title = book.Title; entry.Author = book.Author; entry.Chapters = book.Chapters.Count; entry.Sentences = book.SentenceCount;
                job.Title = book.Title; job.Slug = slug;
                var st = staging;
                main.Enqueue(() => Finish(job, entry, st));
            }
            catch (ImportException e)
            {
                Cleanup(staging, path);
                Fail(job, e.Message, e.Recovery);
            }
            catch (Exception e)
            {
                Cleanup(staging, path);
                Debug.LogException(e);
                Fail(job, $"Fable could not import {job.FileName} ({e.GetType().Name}: {e.Message}).", "Try sending it again. If it still fails, the file may be damaged or unusual; try another copy.");
            }
        }

        static void Cleanup(string staging, string incoming)
        {
            try { if (staging != null && Directory.Exists(staging)) Directory.Delete(staging, true); } catch { }
            try { if (incoming != null && File.Exists(incoming)) File.Delete(incoming); } catch { }
        }

        /// The last steps need the main thread: a PDF must open in the platform's renderer (and gives its first page as
        /// the cover); then the folder moves into the library in one step and the index is written.
        void Finish(LibraryJob job, LibraryEntry entry, string staging)
        {
            try
            {
                if (entry.Format == "pdf")
                {
                    job.Stage = "drawing the first page"; Notify();
                    using var pages = PdfPages.Open(Path.Combine(staging, "source.pdf"));
                    if (pages.Error != null) throw new ImportException($"The headset's PDF reader could not open this file ({pages.Error}).", "The PDF may be damaged or protected. Try exporting it again from the app that made it.");
                    if (pages.Count != entry.PdfPages) Debug.Log($"[Fable] library: {entry.Slug}: {pages.Count} pages drawn, {entry.PdfPages} found by the text reader");
                    entry.PdfPages = pages.Count;
                    var tex = pages.RenderReadable(0, 420);
                    if (tex) { entry.Cover = "cover.png"; File.WriteAllBytes(Path.Combine(staging, entry.Cover), tex.EncodeToPNG()); Destroy(tex); }
                }
                entry.Bytes = DirBytes(staging);
                var dest = BookDir(entry.Slug);
                if (Directory.Exists(dest)) Directory.Delete(dest, true);   // a half-removed earlier copy
                Directory.Move(staging, dest);
                lock (gate) { Imported.RemoveAll(e => e.Slug == entry.Slug); Imported.Add(entry); UsedBytes = Imported.Sum(e => e.Bytes); }
                SaveIndex();
                job.Status = "ready"; job.Stage = "ready"; job.Progress = 1; job.Ended = DateTime.UtcNow;
                Debug.Log($"[Fable] library: {entry.Slug} “{entry.Title}” ready: {entry.Format}, {entry.Chapters} chapters, {entry.Sentences} sentences{(entry.Format == "pdf" ? $", {entry.PdfPages} pages ({entry.TextPages} with text)" : "")}, {entry.Bytes / 1048576f:F1} MB, {(DateTime.UtcNow - job.Started).TotalSeconds:F1} s from the first byte");
                Changed?.Invoke(); BookReady?.Invoke(entry);
                GeneratedRooms.Instance.Request(entry.Slug);   // its three reading rooms start now, in the background
            }
            catch (ImportException e) { Cleanup(staging, null); Fail(job, e.Message, e.Recovery); }
            catch (Exception e) { Cleanup(staging, null); Debug.LogException(e); Fail(job, $"Fable could not finish importing {job.FileName} ({e.Message}).", "Try sending it again."); }
        }

        /// Take an imported book off the shelf: its files, its entry, its place and bookmarks.
        public void Remove(string slug)
        {
            if (!IsImported(slug)) return;
            lock (gate) { Imported.RemoveAll(e => e.Slug == slug); UsedBytes = Imported.Sum(e => e.Bytes); }
            SaveIndex();
            try { var d = BookDir(slug); if (Directory.Exists(d)) Directory.Delete(d, true); } catch (Exception e) { Debug.LogWarning($"[Fable] library: {slug} folder not removed: {e.Message}"); }
            ProgressStore.ForgetBook(slug);
            Debug.Log($"[Fable] library: removed {slug}");
            Changed?.Invoke();
        }

        public void Dismiss(LibraryJob job) { lock (gate) Jobs.Remove(job); Changed?.Invoke(); }

        public LibraryEntry Find(string slug) { lock (gate) return Imported.FirstOrDefault(e => e.Slug == slug); }
        public LibraryJob FindJob(string id) { lock (gate) return Jobs.FirstOrDefault(j => j.Id == id); }
        public List<LibraryJob> ActiveJobs() { lock (gate) return Jobs.ToList(); }

        // ---------------------------------------------------------------- telling formats apart

        /// "epub", "pdf", "empty", or a description of what else it is (or null when unknown).
        static string Sniff(string path)
        {
            var head = new byte[96]; int n;
            using (var f = File.OpenRead(path)) n = f.Read(head, 0, head.Length);
            if (n == 0) return "empty";
            string ascii = System.Text.Encoding.ASCII.GetString(head, 0, n);
            if (ascii.Contains("%PDF-")) return "pdf";
            if (n >= 68 && (ascii.Substring(60, 8) == "BOOKMOBI" || ascii.Substring(60, 8) == "TEXtREAd")) return "a Kindle (MOBI/AZW) book";
            if (ascii.StartsWith("PK\u0003\u0004"))
            {
                if (ascii.Contains("application/epub+zip")) return "epub";   // an EPUB's first entry, even if the rest is damaged
                if (EpubImport.LooksLikeEpub(path)) return "epub";
                try
                {
                    using var z = System.IO.Compression.ZipFile.OpenRead(path);
                    if (z.GetEntry("word/document.xml") != null) return "a Word document";
                    if (z.Entries.Any(e => e.FullName.EndsWith(".jpg") || e.FullName.EndsWith(".png"))) return "a comic or image archive";
                }
                catch { }
                return "a zip archive";
            }
            if (ascii.StartsWith("CONT") || ascii.Contains("DRMION")) return "a Kindle (KFX) book";
            if (ascii.StartsWith("{\\rtf")) return "an RTF document";
            if (ascii.TrimStart().StartsWith("<")) return "a web page";
            return null;
        }

        static string KindFromExtension(string ext) => ext switch
        {
            ".mobi" or ".azw" or ".azw3" or ".kfx" or ".prc" => "Kindle",
            ".doc" or ".docx" or ".odt" or ".rtf" => "word-processor",
            ".txt" => "plain-text",
            ".cbz" or ".cbr" => "comic",
            ".djvu" or ".fb2" or ".lit" or ".lrf" or ".pdb" => ext.TrimStart('.').ToUpperInvariant(),
            ".html" or ".htm" => "web page",
            _ => null,
        };

        static string UnsupportedRecovery(string kind) =>
            kind != null && kind.Contains("Kindle") ? "Kindle books are usually DRM-protected. If yours is DRM-free, convert it to EPUB (for example with Calibre) and send the EPUB." :
            kind != null && (kind.Contains("Word") || kind.Contains("word") || kind.Contains("RTF")) ? "Save or export it as a PDF and send that." :
            "Send an EPUB or a PDF.";
    }
}
