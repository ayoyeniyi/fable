// Three generated reading rooms for each book the reader uploads (docs/GENERATED_ROOMS.md).
//
// The preparation service (interpreter/internal/rooms) chooses three places from the book's opening and builds each
// one in Blender. This side sends the book's text once, follows the three jobs, and fetches each finished room into
// persistentDataPath/library/<book>/rooms/r<N>/: every file is checked against the package's SHA-256 in a staging
// folder and swapped in whole, so a room on the headset is always complete. GeneratedRoomView loads one at runtime.
//
// Some of Fable's own books (Pride and Prejudice, Moby-Dick, The War of the Worlds, Treasure Island) have no
// hand-built rooms: their three rooms are packages made by the same service and bundled in the app
// (content/rooms -> StreamingAssets/rooms, indexed in Resources/BundledRooms.json by FableBuild.SyncData). They are
// always ready; the first time one is opened it is copied out of the APK into persistentDataPath/bundled-rooms with
// the same checks (Unpack), because StreamingAssets on Android are inside the APK and glTFast needs files.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.Networking;

namespace Fable
{
    public class GeneratedRooms : MonoBehaviour
    {
        static GeneratedRooms instance;
        public static GeneratedRooms Instance
        {
            get
            {
                if (instance) return instance;
                var go = new GameObject("GeneratedRooms"); DontDestroyOnLoad(go);
                instance = go.AddComponent<GeneratedRooms>();
                return instance;
            }
        }

        public const int PerBook = 3;
        public class Room
        {
            public int N; public string State = "none", Stage, Title, Place, Error;
            /// Fetched, checked and on the headset.
            public bool Ready;
        }

        class Tracked { public string Slug; public bool Sent; public Room[] Rooms; public float NextPoll; public string LastNote; }
        readonly Dictionary<string, Tracked> books = new();
        /// Raised on the main thread when any room's state changes.
        public event Action Changed;
        bool busy;

        string ServiceUrl => ChapterExperiences.Instance.ServiceUrl;
        public static string Dir(string slug, int n)
        {
            if (IsBundled(slug)) return Path.Combine(Application.persistentDataPath, "bundled-rooms", slug, "r" + n);
            if (!Library.Exists) { var _ = Library.Instance; }   // sets Library.Root (opened straight into a room, not via the lobby)
            return Path.Combine(Library.BookDir(slug), "rooms", "r" + n);
        }

        /// The three rooms of an uploaded book (ready ones are on the headset; the rest say how far they have got).
        public Room[] Rooms(string slug)
        {
            if (!books.TryGetValue(slug, out var t)) t = Track(slug);
            return t.Rooms;
        }

        Tracked Track(string slug)
        {
            var t = new Tracked { Slug = slug, Rooms = new Room[PerBook] };
            if (IsBundled(slug))
            {
                // bundled in the app: ready from the start (copied out of the APK when first opened)
                var list = BundledIndex[slug].Where(r => r.N >= 1 && r.N <= PerBook).OrderBy(r => r.N).ToArray();
                t.Rooms = list.Select(r => new Room { N = r.N, State = "done", Ready = true, Title = r.Title, Place = r.Place }).ToArray();
                books[slug] = t;
                return t;
            }
            for (int n = 1; n <= PerBook; n++)
            {
                var r = t.Rooms[n - 1] = new Room { N = n };
                var pj = Path.Combine(Dir(slug, n), "package.json");
                if (File.Exists(pj))
                    try { var m = JObject.Parse(File.ReadAllText(pj)); r.Ready = true; r.State = "done"; r.Title = (string)m["title"]; r.Place = (string)m["place"]; }
                    catch (Exception e) { Debug.LogWarning($"[Fable] rooms: {slug} r{n} unreadable ({e.Message}); fetching again"); }
            }
            books[slug] = t;
            return t;
        }

        /// Start (or keep) preparing an uploaded book's rooms. Cheap to call again.
        public void Request(string slug)
        {
            if (!Library.IsImported(slug)) return;
            var t = books.TryGetValue(slug, out var x) ? x : Track(slug);
            if (t.Rooms.All(r => r.Ready)) return;
            t.NextPoll = 0;
            if (!busy) StartCoroutine(Loop());
        }

        IEnumerator Loop()
        {
            busy = true;
            try
            {
                while (books.Values.Any(t => !t.Rooms.All(r => r.Ready || r.State == "unavailable" || r.State == "failed")))
                {
                    foreach (var t in books.Values.ToList())
                    {
                        if (Time.time < t.NextPoll || t.Rooms.All(r => r.Ready || r.State is "unavailable" or "failed")) continue;
                        yield return Poll(t);
                        t.NextPoll = Time.time + 8f;
                    }
                    yield return new WaitForSeconds(1f);
                }
            }
            finally { busy = false; }
        }

        IEnumerator Poll(Tracked t)
        {
            if (string.IsNullOrEmpty(ServiceUrl)) { Note(t, "no connection", "the preparation service is not set up"); yield break; }
            using (var req = UnityWebRequest.Get($"{ServiceUrl}/rooms/status?book={UnityWebRequest.EscapeURL(t.Slug)}"))
            {
                req.timeout = 8;
                yield return req.SendWebRequest();
                if (req.result == UnityWebRequest.Result.ConnectionError) { Note(t, "waiting", "waiting to resume: the preparation service can’t be reached"); yield break; }
                if (req.responseCode == 404 || !t.Sent && req.responseCode != 200) { yield return Send(t); yield break; }
                if (req.result != UnityWebRequest.Result.Success) yield break;
                JArray arr; try { arr = JArray.Parse(req.downloadHandler.text); } catch { yield break; }
                bool changed = false;
                foreach (var s in arr)
                {
                    int n = (int)s["room"]; if (n < 1 || n > PerBook) continue;
                    var r = t.Rooms[n - 1]; if (r.Ready) continue;
                    var st = (string)s["state"]; var stage = (string)s["stage"]; var title = (string)s["title"];
                    if (st != r.State || stage != r.Stage || title != r.Title) changed = true;
                    r.State = st; r.Stage = stage; r.Title = title; r.Error = (string)s["error"];
                }
                if (changed) Changed?.Invoke();
            }
            foreach (var r in t.Rooms.Where(r => r.State == "done" && !r.Ready).ToList()) yield return Fetch(t.Slug, r);
        }

        void Note(Tracked t, string state, string stage)
        {
            bool changed = false;
            foreach (var r in t.Rooms) if (!r.Ready && r.State != state) { r.State = state; r.Stage = stage; changed = true; }
            if (changed) Changed?.Invoke();
        }

        /// The book's text, sent once: the service keeps it and plans from its opening only.
        IEnumerator Send(Tracked t)
        {
            var path = Path.Combine(Library.BookDir(t.Slug), "book.json");
            if (!File.Exists(path)) { Note(t, "failed", "the book’s text is missing"); yield break; }
            string body = null; string why = null;
            var job = System.Threading.Tasks.Task.Run(() =>
            {
                var b = Book.Parse(File.ReadAllText(path));
                var chapters = new JArray();
                foreach (var c in b.Chapters)
                {
                    var sb = new StringBuilder();
                    foreach (var p in c.Paragraphs) { foreach (var s in p.Sentences) sb.Append(s.Text).Append(' '); sb.Append('\n'); }
                    if (sb.Length > 0) chapters.Add(new JObject { ["id"] = c.Id, ["title"] = c.Title ?? "", ["text"] = sb.ToString() });
                }
                if (chapters.Count == 0) { why = "this book has no text to read places from (a scanned PDF?)"; return; }
                body = new JObject { ["slug"] = t.Slug, ["title"] = b.Title ?? "", ["author"] = b.Author ?? "", ["chapters"] = chapters }.ToString(Formatting.None);
            });
            while (!job.IsCompleted) yield return null;
            if (job.IsFaulted || body == null) { Note(t, "unavailable", why ?? "the book could not be read"); yield break; }
            using var req = new UnityWebRequest(ServiceUrl + "/rooms/prepare", "POST");
            req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body)); req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json"); req.timeout = 30;
            yield return req.SendWebRequest();
            if (req.result == UnityWebRequest.Result.Success) { t.Sent = true; Debug.Log($"[Fable] rooms: {t.Slug} sent ({body.Length / 1024} kB of text); three rooms queued"); }
            else if (req.result == UnityWebRequest.Result.ConnectionError || req.responseCode == 429) Note(t, "waiting", req.responseCode == 429 ? "the service is busy; trying again" : "waiting to resume: the preparation service can’t be reached");
            else Note(t, "failed", req.downloadHandler.text.Trim());
        }

        IEnumerator Fetch(string slug, Room r)
        {
            var t0 = Time.realtimeSinceStartup;
            var dir = Dir(slug, r.N); var part = dir + ".part";
            string q = $"book={UnityWebRequest.EscapeURL(slug)}&room={r.N}";
            string manifest;
            using (var req = UnityWebRequest.Get($"{ServiceUrl}/rooms/package?{q}"))
            {
                req.timeout = 10; yield return req.SendWebRequest();
                if (req.result != UnityWebRequest.Result.Success) yield break;
                manifest = req.downloadHandler.text;
            }
            JObject m; try { m = JObject.Parse(manifest); } catch { yield break; }
            try { if (Directory.Exists(part)) Directory.Delete(part, true); Directory.CreateDirectory(part); } catch (Exception e) { Debug.LogWarning($"[Fable] rooms: {e.Message}"); yield break; }
            foreach (var f in (JArray)m["files"])
            {
                var rel = (string)f["path"]; var sha = (string)f["sha256"];
                if (string.IsNullOrEmpty(rel) || rel.Contains("..") || Path.IsPathRooted(rel)) { Debug.LogWarning($"[Fable] rooms: refused path {rel}"); yield break; }
                var dst = Path.Combine(part, rel); Directory.CreateDirectory(Path.GetDirectoryName(dst));
                using var req = UnityWebRequest.Get($"{ServiceUrl}/rooms/file?{q}&path={UnityWebRequest.EscapeURL(rel)}");
                req.downloadHandler = new DownloadHandlerFile(dst) { removeFileOnAbort = true }; req.timeout = 60;
                yield return req.SendWebRequest();
                if (req.result != UnityWebRequest.Result.Success) { Debug.LogWarning($"[Fable] rooms: {slug} r{r.N} {rel}: {req.error}"); yield break; }
                if (Sha256(dst) != sha) { Debug.LogWarning($"[Fable] rooms: {slug} r{r.N} {rel} failed its checksum"); yield break; }
            }
            File.WriteAllText(Path.Combine(part, "package.json"), manifest);
            try { if (Directory.Exists(dir)) Directory.Delete(dir, true); Directory.Move(part, dir); }
            catch (Exception e) { Debug.LogWarning($"[Fable] rooms: swap failed: {e.Message}"); yield break; }
            r.Ready = true; r.Title = (string)m["title"]; r.Place = (string)m["place"];
            Debug.Log($"[Fable] rooms: {slug} r{r.N} “{r.Title}” on the headset ({(long)m["bytes"] / 1024} kB, {Time.realtimeSinceStartup - t0:F1} s to fetch)");
            Changed?.Invoke();
        }

        static string Sha256(string path)
        {
            using var s = File.OpenRead(path); using var h = SHA256.Create();
            return BitConverter.ToString(h.ComputeHash(s)).Replace("-", "").ToLowerInvariant();
        }

        // ---------------------------------------------------------------- rooms bundled in the app

        class BundledRoom
        {
            [JsonProperty("room")] public int N; [JsonProperty("title")] public string Title; [JsonProperty("place")] public string Place;
            /// SHA-256 of the room's package.json: an extracted copy with another one is from an older build and is replaced.
            [JsonProperty("package")] public string PackageSha;
        }
        static Dictionary<string, BundledRoom[]> bundled;
        static Dictionary<string, BundledRoom[]> BundledIndex
        {
            get
            {
                if (bundled != null) return bundled;
                bundled = new Dictionary<string, BundledRoom[]>();
                var ta = Resources.Load<TextAsset>("BundledRooms");
                if (ta)
                    try { bundled = JsonConvert.DeserializeObject<Dictionary<string, BundledRoom[]>>(ta.text) ?? bundled; }
                    catch (Exception e) { Debug.LogWarning($"[Fable] rooms: bundled index unreadable ({e.Message})"); }
                return bundled;
            }
        }

        /// A Fable book whose reading rooms are generated packages shipped in the app.
        public static bool IsBundled(string slug) => slug != null && BundledIndex.ContainsKey(slug);

        /// Make sure a bundled room is on the device as plain files (copied once from StreamingAssets, every file checked
        /// against its SHA-256, swapped in whole). done(null) when it is there, or done(why).
        public static IEnumerator Unpack(string slug, int n, Action<string> done)
        {
            var room = IsBundled(slug) ? BundledIndex[slug].FirstOrDefault(r => r.N == n) : null;
            if (room == null) { done("there is no such room in the app"); yield break; }
            var dir = Dir(slug, n); var pj = Path.Combine(dir, "package.json");
            if (File.Exists(pj) && Sha256(pj) == room.PackageSha) { done(null); yield break; }
            var t0 = Time.realtimeSinceStartup; var part = dir + ".part"; var rel = $"rooms/{slug}/r{n}/";
            try { if (Directory.Exists(part)) Directory.Delete(part, true); Directory.CreateDirectory(part); }
            catch (Exception e) { done("no room on the device to unpack it: " + e.Message); yield break; }
            string err = null;
            yield return CopyOut(rel + "package.json", Path.Combine(part, "package.json"), room.PackageSha, e => err = e);
            if (err != null) { done(err); yield break; }
            JObject m; try { m = JObject.Parse(File.ReadAllText(Path.Combine(part, "package.json"))); } catch (Exception e) { done("its package is unreadable: " + e.Message); yield break; }
            long bytes = 0;
            foreach (var f in (JArray)m["files"])
            {
                var p = (string)f["path"];
                if (string.IsNullOrEmpty(p) || p.Contains("..") || Path.IsPathRooted(p)) { done($"refused path {p}"); yield break; }
                var dst = Path.Combine(part, p); Directory.CreateDirectory(Path.GetDirectoryName(dst));
                yield return CopyOut(rel + p, dst, (string)f["sha256"], e => err = e);
                if (err != null) { done(err); yield break; }
                bytes += (long?)f["size"] ?? 0;
            }
            try { if (Directory.Exists(dir)) Directory.Delete(dir, true); Directory.Move(part, dir); }
            catch (Exception e) { done("could not be put in place: " + e.Message); yield break; }
            Debug.Log($"[Fable] rooms: {slug} r{n} unpacked from the app ({bytes / 1024} kB in {(Time.realtimeSinceStartup - t0) * 1000:F0} ms)");
            done(null);
        }

        /// One StreamingAssets file to a plain file, checked. Read with UnityWebRequest: a jar: URL inside the APK on
        /// Android, a file: URL elsewhere. Bundled file names are plain ASCII (tools/bundle_rooms.py), so nothing is escaped.
        static IEnumerator CopyOut(string relative, string dst, string sha, Action<string> fail)
        {
            var root = Application.streamingAssetsPath;
            var url = root.Contains("://") ? root + "/" + relative : new Uri(Path.Combine(root, relative)).AbsoluteUri;
            using var req = UnityWebRequest.Get(url);
            req.downloadHandler = new DownloadHandlerFile(dst) { removeFileOnAbort = true };
            yield return req.SendWebRequest();
            if (req.result != UnityWebRequest.Result.Success) { fail($"{relative} is missing from the app ({req.error})"); yield break; }
            if (Sha256(dst) != sha) fail($"{relative} failed its checksum");
        }

        /// The room's preview picture (the check render from the reader's eyes), or null.
        public static Texture2D Thumbnail(string slug, int n)
        {
            var p = Path.Combine(Dir(slug, n), "thumb.png");
            if (!File.Exists(p)) return null;
            var tex = new Texture2D(2, 2); tex.LoadImage(File.ReadAllBytes(p)); return tex;
        }
    }
}
