// Chapter experiences on the headset: what the reader has finished, what is being prepared, and what they may enter.
//
// Two separate records per chapter, never mixed:
//   completion   set only when the reader finishes the chapter (Continue at the chapter's end, or "mark as read")
//   preparation  a job on the preparation service (fable-interpreter, internal/chapters), started when the reader
//                enters the chapter, fetched into a sealed folder once built, checked here, then "ready"
// What the reader sees follows from both (State):
//   Locked       not completed (whatever preparation has done: a lock and the chapter's number, nothing else)
//   Preparing    completed, not ready yet (the stage is shown; entry is not offered)
//   Available    completed and ready
//   Failed       completed, preparation failed (a short reason and Retry)
//   Unavailable  completed, and no built place fits the chapter (said plainly; nothing unrelated is substituted)
// A finished job never unlocks an unread chapter, and finishing a chapter never makes an unfinished job "ready".
// The access check is here, at the loading boundary (Title, Thumbnail, OpenPackage), not only in the menus.
//
// The queue: one job per chapter, never cancelled by entering another; at most MaxInFlight with the service at
// once (the rest wait on the headset), completed chapters first. All of it is saved (experiences/state.json) and
// resumes after a restart; with no connection the jobs wait and say so, and reading goes on untouched.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.Networking;

namespace Fable
{
    [Serializable, UnityEngine.Scripting.Preserve]
    public class ChapterRecord
    {
        public string Book, Chapter;
        public bool Completed; public string CompletedUtc, CompletedHow;   // "finished" | "marked"
        /// none | queued (on the headset) | requested | waiting (no connection) | building | ready | failed | unavailable
        public string Job = "none";
        public string ServerState, Stage, Error;
        public string RequestedUtc, ReadyUtc;
        public float HeadsetSeconds;      // from the first request to the package checked and stored here
        public int Attempts;
        [UnityEngine.Scripting.Preserve] public ChapterRecord() { }
    }

    [Serializable, UnityEngine.Scripting.Preserve]
    public class ExperienceState { public List<ChapterRecord> Chapters = new(); [UnityEngine.Scripting.Preserve] public ExperienceState() { } }

    /// The package the service builds (interpreter/internal/chapters.Package).
    [UnityEngine.Scripting.Preserve]
    public class ChapterPackage
    {
        public class Range { [JsonProperty("from")] public string From; [JsonProperty("to")] public string To; }
        public class Thumb { [JsonProperty("file")] public string File; [JsonProperty("sha256")] public string Sha256; [JsonProperty("width")] public int Width; [JsonProperty("height")] public int Height; }
        [JsonProperty("version")] public int Version;
        [JsonProperty("book")] public string Book;
        [JsonProperty("chapter")] public string Chapter;
        [JsonProperty("chapterName")] public string ChapterName;
        [JsonProperty("title")] public string Title;
        [JsonProperty("place")] public string Place;
        [JsonProperty("environment")] public string Environment;
        [JsonProperty("unityScene")] public string UnityScene;
        [JsonProperty("staging")] public string Staging;   // scripted | place
        [JsonProperty("passage")] public string Passage;
        [JsonProperty("moment")] public Range Moment;
        [JsonProperty("mood")] public string Mood;
        [JsonProperty("fog")] public float Fog;
        [JsonProperty("script")] public SceneScript Script;
        [JsonProperty("thumbnail")] public Thumb Thumbnail;
        [JsonProperty("triangles")] public int Triangles;
        [JsonProperty("timings")] public Dictionary<string, float> Timings;
        [UnityEngine.Scripting.Preserve] public ChapterPackage() { }
    }

    public class ChapterExperiences : MonoBehaviour
    {
        public enum State { Locked, Preparing, Available, Failed, Unavailable }
        public const int MaxInFlight = 6;
        /// Books whose text the preparation service holds (the four bundled ones). Imported books: not yet.
        public static readonly HashSet<string> Supported = new() { "alice", "oz", "odyssey", "gulliver" };

        static ChapterExperiences instance;
        public static ChapterExperiences Instance
        {
            get
            {
                if (instance) return instance;
                var go = new GameObject("ChapterExperiences"); DontDestroyOnLoad(go);
                instance = go.AddComponent<ChapterExperiences>(); instance.Load();
                return instance;
            }
        }

        public string ServiceUrl { get; private set; }
        /// Raised on the main thread when any record changes.
        public event Action Changed;
        /// Raised when an experience becomes enterable (completed and ready) or a completed chapter's job fails.
        public event Action<ChapterRecord> BecameAvailable;

        string Root, StatePath;
        ExperienceState state = new();
        readonly Dictionary<string, Texture2D> thumbs = new();
        bool busy;

        void Load()
        {
            Root = Path.Combine(Application.persistentDataPath, "experiences");
            StatePath = Path.Combine(Root, "state.json");
            Directory.CreateDirectory(Root);
            try { if (File.Exists(StatePath)) state = JsonConvert.DeserializeObject<ExperienceState>(File.ReadAllText(StatePath)) ?? new ExperienceState(); }
            catch (Exception e) { Debug.LogWarning($"[Fable] experiences: state unreadable ({e.Message}); starting empty, completion kept in progress where possible"); }
            state.Chapters ??= new List<ChapterRecord>();
            // a package that went missing (storage cleared) is fetched again rather than claimed
            foreach (var r in state.Chapters) if (r.Job == "ready" && !File.Exists(PackagePath(r))) { r.Job = "requested"; r.Stage = null; }
            ServiceUrl = FindServiceUrl();
            int open = state.Chapters.Count(r => r.Job is "queued" or "requested" or "waiting" or "building");
            Debug.Log($"[Fable] experiences: {state.Chapters.Count(r => r.Completed)} chapters completed, {state.Chapters.Count(r => r.Job == "ready")} prepared, {open} jobs to resume; service {ServiceUrl ?? "none"}");
            StartCoroutine(Loop());
        }

        static string FindServiceUrl()
        {
            var f = Path.Combine(Application.persistentDataPath, "interpreter.txt");
            if (File.Exists(f)) return File.ReadAllText(f).Trim().TrimEnd('/');
            return "http://127.0.0.1:8787";   // the Mac over `adb reverse` on the headset; the local service in the editor
        }

        void Save()
        {
            try { var tmp = StatePath + ".tmp"; File.WriteAllText(tmp, JsonConvert.SerializeObject(state, Formatting.Indented)); ProgressStore.Swap(tmp, StatePath); }
            catch (Exception e) { Debug.LogWarning($"[Fable] experiences: state not saved: {e.Message}"); }
            Changed?.Invoke();
        }

        ChapterRecord Rec(string book, string chapter, bool create)
        {
            var r = state.Chapters.Find(x => x.Chapter == chapter);
            if (r == null && create) { r = new ChapterRecord { Book = book, Chapter = chapter }; state.Chapters.Add(r); }
            return r;
        }
        public ChapterRecord Record(string chapter) => state.Chapters.Find(x => x.Chapter == chapter);
        public IEnumerable<ChapterRecord> Records(string book) => state.Chapters.Where(r => r.Book == book).ToList();

        string Dir(ChapterRecord r) => Path.Combine(Root, r.Chapter.Replace(':', '_'));
        string PackagePath(ChapterRecord r) => Path.Combine(Dir(r), "package.json");

        // ---------------------------------------------------------------- what the reader does

        /// The reader has entered a chapter: prepare its experience (once).
        public void Enter(string book, string chapter)
        {
            if (!Supported.Contains(book) || chapter == null) return;
            var r = Rec(book, chapter, true);
            if (r.Job != "none") return;
            r.Job = "queued"; r.RequestedUtc = DateTime.UtcNow.ToString("o"); r.Stage = "waiting its turn";
            Debug.Log($"[Fable] experiences: {chapter} entered, preparation queued");
            Save();
        }

        /// The reader finished the chapter (or marked it read). Unlocks access; does not make anything ready.
        public void Complete(string book, string chapter, string how)
        {
            var r = Rec(book, chapter, true);
            if (r.Completed) return;
            r.Completed = true; r.CompletedUtc = DateTime.UtcNow.ToString("o"); r.CompletedHow = how;
            if (Supported.Contains(book) && r.Job == "none") { r.Job = "queued"; r.RequestedUtc = r.CompletedUtc; }   // marked as read without entering it
            if (r.Job is "requested" or "building" or "waiting") r.Job = "requested";   // tell the service: it goes first now
            Debug.Log($"[Fable] experiences: {chapter} completed ({how}); preparation is {r.Job}");
            Save();
            if (r.Job == "ready") BecameAvailable?.Invoke(r);
        }

        public void Retry(string chapter)
        {
            var r = Record(chapter); if (r == null || r.Job != "failed") return;
            r.Job = "requested"; r.Error = null; r.Stage = "asked again"; Save();
        }

        public bool IsCompleted(string chapter) => Record(chapter)?.Completed == true;

        public State StateOf(string chapter)
        {
            var r = Record(chapter);
            if (r == null || !r.Completed) return State.Locked;
            return r.Job switch { "ready" => State.Available, "failed" => State.Failed, "unavailable" => State.Unavailable, _ => State.Preparing };
        }

        /// The preparation stage in plain words ("choosing the place in the chapter"). Carries no content of the chapter.
        public string StageOf(string chapter)
        {
            var r = Record(chapter); if (r == null || r.Job == "none") return "not started";
            return r.Job switch
            {
                "queued" => "waiting its turn on the headset",
                "waiting" => "waiting to resume: the preparation service can't be reached",
                "ready" => "ready",
                "failed" => "preparation failed" + (string.IsNullOrEmpty(r.Error) ? "" : ": " + Short(r.Error)),
                "unavailable" => "no place has been built for this chapter yet",
                _ => r.Stage ?? "preparing",
            };
        }

        static string Short(string s) => s.Length > 110 ? s.Substring(0, 109) + "…" : s;

        // ---------------------------------------------------------------- the access boundary

        /// The experience's title, only once the chapter is completed and the experience ready.
        public string Title(string chapter) => StateOf(chapter) == State.Available ? OpenPackage(chapter)?.Title : null;

        /// The thumbnail, under the same rule.
        public Texture2D Thumbnail(string chapter)
        {
            if (StateOf(chapter) != State.Available) return null;
            if (thumbs.TryGetValue(chapter, out var t) && t) return t;
            var r = Record(chapter); var p = Path.Combine(Dir(r), "thumb.jpg");
            if (!File.Exists(p)) return null;
            t = new Texture2D(2, 2, TextureFormat.RGB24, true) { name = "experience " + chapter };
            t.LoadImage(File.ReadAllBytes(p), true); thumbs[chapter] = t; return t;
        }

        /// The package, to enter the experience. Refused (null) for a chapter that is not completed: the scene, its
        /// script and its labels stay unread on the headset until then.
        public ChapterPackage OpenPackage(string chapter)
        {
            var r = Record(chapter);
            if (r == null || !r.Completed) { Debug.LogWarning($"[Fable] experiences: {chapter} is locked; its package was not opened"); return null; }
            if (r.Job != "ready" || !File.Exists(PackagePath(r))) return null;
            try { return JsonConvert.DeserializeObject<ChapterPackage>(File.ReadAllText(PackagePath(r))); }
            catch (Exception e) { Debug.LogWarning($"[Fable] experiences: {chapter} package unreadable: {e.Message}"); r.Job = "requested"; Save(); return null; }
        }

        // ---------------------------------------------------------------- the queue

        IEnumerator Loop()
        {
            var wait = new WaitForSecondsRealtime(3f);
            while (true)
            {
                if (!busy) StartCoroutine(Tick());
                yield return wait;
            }
        }

        IEnumerator Tick()
        {
            busy = true;
            try
            {
                // admit queued jobs while there is room, completed chapters first
                int inFlight = state.Chapters.Count(r => r.Job is "requested" or "building" or "waiting");
                foreach (var r in state.Chapters.Where(r => r.Job == "queued").OrderByDescending(r => r.Completed).ThenBy(r => r.RequestedUtc).ToList())
                    if (inFlight < MaxInFlight) { r.Job = "requested"; inFlight++; }
                foreach (var r in state.Chapters.Where(r => r.Job is "requested" or "waiting" or "building").OrderByDescending(r => r.Completed).ToList())
                {
                    if (r.Job == "building") yield return Poll(r); else yield return Request(r);
                }
            }
            finally { busy = false; }
        }

        IEnumerator Request(ChapterRecord r)
        {
            var body = JsonConvert.SerializeObject(new { book = r.Book, chapter = r.Chapter, completed = r.Completed });
            using var req = new UnityWebRequest(ServiceUrl + "/chapters/prepare", "POST");
            req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body)); req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json"); req.timeout = 6;
            yield return req.SendWebRequest();
            if (req.result == UnityWebRequest.Result.ConnectionError || req.result == UnityWebRequest.Result.ProtocolError && req.responseCode == 429)
            {
                if (r.Job != "waiting") { r.Job = "waiting"; r.Stage = req.responseCode == 429 ? "the service is busy" : "no connection"; Save(); }
                yield break;
            }
            if (req.result != UnityWebRequest.Result.Success) { Fail(r, Error(req)); yield break; }
            Apply(r, req.downloadHandler.text);
        }

        IEnumerator Poll(ChapterRecord r)
        {
            using var req = UnityWebRequest.Get(ServiceUrl + "/chapters/status?chapter=" + UnityWebRequest.EscapeURL(r.Chapter)); req.timeout = 6;
            yield return req.SendWebRequest();
            if (req.result == UnityWebRequest.Result.ConnectionError) { r.Job = "waiting"; r.Stage = "no connection"; Save(); yield break; }
            if (req.responseCode == 404) { r.Job = "requested"; yield break; }   // the service lost it: ask again
            if (req.result != UnityWebRequest.Result.Success) yield break;
            if (Apply(r, req.downloadHandler.text)) yield return Fetch(r);
        }

        class Status { public string state, stage, error; public int attempts; }

        /// Take a status answer. Returns true when the package is built and should be fetched.
        bool Apply(ChapterRecord r, string json)
        {
            Status s; try { s = JsonConvert.DeserializeObject<Status>(json); } catch { return false; }
            var before = r.Job + r.ServerState + r.Stage;
            r.ServerState = s.state; r.Stage = s.stage; r.Attempts = s.attempts;
            switch (s.state)
            {
                case "done": r.Job = "building"; break;
                case "failed": Fail(r, s.error ?? "unknown error"); return false;
                case "unavailable": r.Job = "unavailable"; r.Error = s.error; break;
                default: r.Job = "building"; break;
            }
            if (before != r.Job + r.ServerState + r.Stage) Save();
            return s.state == "done";
        }

        void Fail(ChapterRecord r, string why)
        {
            r.Job = "failed"; r.Error = why; Save();
            Debug.LogWarning($"[Fable] experiences: {r.Chapter} preparation failed: {why}");
            if (r.Completed) BecameAvailable?.Invoke(r);
        }

        static string Error(UnityWebRequest req) { var t = req.downloadHandler?.text ?? ""; return (string.IsNullOrEmpty(t) ? req.error : t).Trim(); }

        /// Delivery: fetch the package and its thumbnail into a staging folder, check them, then swap them in. Only then ready.
        IEnumerator Fetch(ChapterRecord r)
        {
            r.Stage = "fetching to the headset"; Save();
            var stage = Dir(r) + ".part"; if (Directory.Exists(stage)) Directory.Delete(stage, true); Directory.CreateDirectory(stage);
            string pkgJson = null; byte[] thumb = null;
            using (var a = UnityWebRequest.Get(ServiceUrl + "/chapters/package?chapter=" + UnityWebRequest.EscapeURL(r.Chapter)))
            { a.timeout = 20; yield return a.SendWebRequest(); if (a.result == UnityWebRequest.Result.Success) pkgJson = a.downloadHandler.text; }
            using (var b = UnityWebRequest.Get(ServiceUrl + "/chapters/thumb?chapter=" + UnityWebRequest.EscapeURL(r.Chapter)))
            { b.timeout = 20; yield return b.SendWebRequest(); if (b.result == UnityWebRequest.Result.Success) thumb = b.downloadHandler.data; }
            if (pkgJson == null || thumb == null) { r.Job = "waiting"; r.Stage = "the download was interrupted; it will resume"; Save(); yield break; }
            string problem = null; ChapterPackage p = null;
            try { p = JsonConvert.DeserializeObject<ChapterPackage>(pkgJson); } catch (Exception e) { problem = "the package is not readable: " + e.Message; }
            if (problem == null) problem = Check(p, thumb, r);
            if (problem != null) { Directory.Delete(stage, true); Fail(r, "the headset rejected the package: " + problem); yield break; }
            File.WriteAllText(Path.Combine(stage, "package.json"), pkgJson); File.WriteAllBytes(Path.Combine(stage, "thumb.jpg"), thumb);
            if (Directory.Exists(Dir(r))) Directory.Delete(Dir(r), true);
            Directory.Move(stage, Dir(r));
            r.Job = "ready"; r.ReadyUtc = DateTime.UtcNow.ToString("o"); r.Stage = "ready"; r.Error = null;
            if (DateTime.TryParse(r.RequestedUtc, null, System.Globalization.DateTimeStyles.RoundtripKind, out var t0)) r.HeadsetSeconds = (float)(DateTime.UtcNow - t0).TotalSeconds;
            Debug.Log($"[Fable] experiences: {r.Chapter} ready on the headset {r.HeadsetSeconds:F0} s after it was first asked for (chapter {(r.Completed ? "completed" : "still locked")})");
            Save();
            if (r.Completed) BecameAvailable?.Invoke(r);
            var body = JsonConvert.SerializeObject(new { chapter = r.Chapter, headsetSeconds = r.HeadsetSeconds });
            using var d = new UnityWebRequest(ServiceUrl + "/chapters/delivered", "POST") { uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body)), downloadHandler = new DownloadHandlerBuffer() };
            d.SetRequestHeader("Content-Type", "application/json"); d.timeout = 5; yield return d.SendWebRequest();
        }

        /// The headset's own checks before a package may ever be loaded: the right chapter, a scene in this build, a
        /// script that passes the same validator as every other script, a moment inside the chapter, an intact image.
        string Check(ChapterPackage p, byte[] thumb, ChapterRecord r)
        {
            if (p == null || p.Version != 1) return "unknown package version";
            if (p.Chapter != r.Chapter || p.Book != r.Book) return "it is for another chapter";
            if (string.IsNullOrEmpty(p.UnityScene) || !Application.CanStreamedLevelBeLoaded(p.UnityScene)) return $"its environment ({p.UnityScene}) is not in this build";
            if (p.Moment == null || !(p.Moment.From ?? "").StartsWith(r.Chapter + ".") || !(p.Moment.To ?? "").StartsWith(r.Chapter + ".")) return "its moment is not inside the chapter";
            using (var h = SHA256.Create()) { var sb = new StringBuilder(); foreach (var x in h.ComputeHash(thumb)) sb.Append(x.ToString("x2")); if (p.Thumbnail == null || sb.ToString() != p.Thumbnail.Sha256) return "the image does not match its checksum"; }
            if (p.Staging == "scripted")
            {
                if (p.Script == null || string.IsNullOrEmpty(p.Passage)) return "a scripted scene without its script";
                var mpath = Path.Combine(Application.streamingAssetsPath, "scripts", $"manifest.{p.Passage}.json");
                string mjson = ReadStreamingSync(mpath); if (mjson == null) return $"no manifest for {p.Passage} in this build";
                var manifest = JsonConvert.DeserializeObject<SceneManifest>(mjson);
                var passages = JsonConvert.DeserializeObject<Passage>(ReadStreamingSync(Path.Combine(Application.streamingAssetsPath, "book", "passages.json")) ?? "{}");
                var scene = passages?.Scenes?.Find(s => s.Id == p.Passage); if (scene == null) return $"no passage {p.Passage} in this build";
                var ids = scene.Sentences().Select(s => s.Id).ToList();
                var errs = ScriptValidator.Validate(p.Script, manifest, ids);
                if (errs.Count > 0) return "its script failed validation: " + errs[0];
            }
            return null;
        }

        static string ReadStreamingSync(string path)
        {
#if UNITY_ANDROID && !UNITY_EDITOR
            using var req = UnityWebRequest.Get(path); var op = req.SendWebRequest(); while (!op.isDone) { }
            return req.result == UnityWebRequest.Result.Success ? req.downloadHandler.text : null;
#else
            return File.Exists(path) ? File.ReadAllText(path) : null;
#endif
        }

        public string Describe(string book) => string.Join(" | ", state.Chapters.Where(r => r.Book == book).OrderBy(r => r.Chapter).Select(r => $"{r.Chapter}:{(r.Completed ? "done" : "unread")}/{r.Job}{(r.Job == "building" ? "(" + r.ServerState + ")" : "")}"));
    }
}
