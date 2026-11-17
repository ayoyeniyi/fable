// Downloadable scene rooms on the headset (docs/SCENE_ROOMS_PIPELINE.md): chapter rooms that are not in the APK.
//
// The service publishes each room as one zip (content/scene-rooms/<id>/room-<version>.zip, GET /scene-rooms/...). A
// chapter package names the zip it needs (ChapterPackage.SceneRoom: id, version, file, bytes, sha256). Here the zip is
// downloaded into persistentDataPath/scene-rooms/<id>.zip.part with progress, checked against its SHA-256, unpacked
// into a staging folder (every entry confined to it) and swapped in whole as scene-rooms/<id>/ with its ref saved
// beside it, so a room on the headset is always complete and of the version asked for. The cache is capped
// (CapBytes); the least recently used rooms go first, never the one in use or being fetched.
// Prefetch: when the reader enters a chapter, the rooms the service's index names for that chapter and the next one are
// fetched quietly, one at a time, so stepping in rarely waits.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using Newtonsoft.Json;
using UnityEngine;
using UnityEngine.Networking;

namespace Fable
{
    [UnityEngine.Scripting.Preserve]
    public class SceneRoomRef
    {
        [JsonProperty("id")] public string Id; [JsonProperty("version")] public string Version; [JsonProperty("file")] public string File;
        [JsonProperty("bytes")] public long Bytes; [JsonProperty("sha256")] public string Sha256;
        [UnityEngine.Scripting.Preserve] public SceneRoomRef() { }
        public bool Valid => !string.IsNullOrEmpty(Id) && Id.All(c => c is >= 'a' and <= 'z' or >= '0' and <= '9' or '-') && Sha256 is { Length: 64 }
                             && !string.IsNullOrEmpty(File) && !File.Contains("/") && !File.Contains("..") && File.EndsWith(".zip") && Bytes > 0;
    }

    public class SceneRooms : MonoBehaviour
    {
        static SceneRooms instance;
        public static SceneRooms Instance
        {
            get
            {
                if (instance) return instance;
                var go = new GameObject("SceneRooms"); DontDestroyOnLoad(go);
                instance = go.AddComponent<SceneRooms>(); instance.Init();
                return instance;
            }
        }

        /// The most the cache may hold on the headset (a room is ~5-15 MB unpacked to 6-20 MB).
        public static long CapBytes = 600L * 1024 * 1024;

        public class Progress
        {
            public long Done, Total; public float Started, BytesPerSecond; public string Error; public bool Finished;
            public float Fraction => Total > 0 ? Mathf.Clamp01((float)Done / Total) : 0f;
            /// "4.2 of 12.6 MB", for the card.
            public string Amount => $"{Done / 1e6:F1} of {Total / 1e6:F1} MB";
            /// Seconds left at the rate so far (0 when unknown).
            public float EtaSeconds => BytesPerSecond > 1 ? (Total - Done) / BytesPerSecond : 0f;
        }

        class Entry { public SceneRoomRef Ref; public long Bytes; public string LastUsedUtc; }
        class CacheIndex { public Dictionary<string, Entry> Rooms = new(); }

        string root, indexPath; CacheIndex cache = new();
        readonly Dictionary<string, Progress> active = new();
        readonly Queue<SceneRoomRef> prefetch = new();
        bool prefetching;
        List<IndexRoom> serviceIndex; float indexAt = -999;
        /// Raised on the main thread while a download moves on and when it ends.
        public event Action<string> Changed;
        public string InUse;   // the room shown now: never evicted

        string ServiceUrl => FableService.Url;

        void Init()
        {
            root = Path.Combine(Application.persistentDataPath, "scene-rooms"); Directory.CreateDirectory(root);
            indexPath = Path.Combine(root, "cache.json");
            try { if (File.Exists(indexPath)) cache = JsonConvert.DeserializeObject<CacheIndex>(File.ReadAllText(indexPath)) ?? new CacheIndex(); }
            catch (Exception e) { Debug.LogWarning($"[Fable] scene rooms: cache index unreadable ({e.Message}); starting empty"); }
            // leftovers of an interrupted download or swap
            foreach (var d in Directory.GetDirectories(root).Where(d => d.EndsWith(".part"))) try { Directory.Delete(d, true); } catch { }
            foreach (var id in cache.Rooms.Keys.ToList()) if (!File.Exists(Path.Combine(Dir(id), "room.gltf"))) cache.Rooms.Remove(id);
            Debug.Log($"[Fable] scene rooms: {cache.Rooms.Count} on the headset ({cache.Rooms.Values.Sum(e => e.Bytes) / 1e6:F0} MB, cap {CapBytes / 1e6:F0} MB)");
        }

        public string Dir(string id) => Path.Combine(root, id);
        public string Gltf(string id) => Path.Combine(Dir(id), "room.gltf");

        /// The room is on the headset at exactly this version.
        public bool IsReady(SceneRoomRef r) => r != null && cache.Rooms.TryGetValue(r.Id, out var e) && e.Ref?.Sha256 == r.Sha256 && File.Exists(Gltf(r.Id));
        public Progress ProgressOf(string id) => id != null && active.TryGetValue(id, out var p) ? p : null;

        public void Touch(string id)
        {
            if (!cache.Rooms.TryGetValue(id, out var e)) return;
            e.LastUsedUtc = DateTime.UtcNow.ToString("o"); Save();
        }

        void Save()
        {
            try { var tmp = indexPath + ".tmp"; File.WriteAllText(tmp, JsonConvert.SerializeObject(cache, Formatting.Indented)); ProgressStore.Swap(tmp, indexPath); }
            catch (Exception e) { Debug.LogWarning($"[Fable] scene rooms: cache index not saved: {e.Message}"); }
        }

        /// Download, check and unpack a room (or wait for the download already running). done(null) when it is on the
        /// headset, else done(why). Progress is readable meanwhile (ProgressOf) and Changed is raised as it moves.
        public IEnumerator Fetch(SceneRoomRef r, Action<string> done)
        {
            if (r == null || !r.Valid) { done?.Invoke("the room's reference is not valid"); yield break; }
            if (IsReady(r)) { Touch(r.Id); done?.Invoke(null); yield break; }
            if (active.TryGetValue(r.Id, out var running))
            {
                while (!running.Finished) yield return null;
                done?.Invoke(IsReady(r) ? null : running.Error ?? "the download failed"); yield break;
            }
            var p = new Progress { Total = r.Bytes, Started = Time.realtimeSinceStartup }; active[r.Id] = p;
            string why = null;
            try { yield return Download(r, p, w => why = w); }
            finally { p.Finished = true; p.Error = why; active.Remove(r.Id); Changed?.Invoke(r.Id); }
            done?.Invoke(why);
        }

        IEnumerator Download(SceneRoomRef r, Progress p, Action<string> fail)
        {
            if (string.IsNullOrEmpty(ServiceUrl)) { fail("the preparation service is not set up"); yield break; }
            MakeRoom(r.Bytes * 2 + (r.Bytes / 2), r.Id);
            var zip = Path.Combine(root, r.Id + ".zip.part");
            var url = $"{ServiceUrl}/scene-rooms/{r.Id}/{r.File}";
            float t0 = Time.realtimeSinceStartup;
            using (var req = UnityWebRequest.Get(url))
            {
                req.downloadHandler = new DownloadHandlerFile(zip) { removeFileOnAbort = true }; req.timeout = 600;
                var op = req.SendWebRequest(); float lastNote = 0;
                while (!op.isDone)
                {
                    p.Done = (long)req.downloadedBytes; float el = Time.realtimeSinceStartup - t0;
                    if (el > 0.5f) p.BytesPerSecond = p.Done / el;
                    if (Time.realtimeSinceStartup - lastNote > 0.5f) { lastNote = Time.realtimeSinceStartup; Changed?.Invoke(r.Id); }
                    yield return null;
                }
                if (req.result != UnityWebRequest.Result.Success) { fail(req.result == UnityWebRequest.Result.ConnectionError ? "no connection" : $"the download failed ({req.responseCode} {req.error})"); TryDelete(zip); yield break; }
                p.Done = (long)req.downloadedBytes;
            }
            Debug.Log($"[Fable] scene rooms: {r.Id} downloaded ({p.Done / 1e6:F1} MB in {Time.realtimeSinceStartup - t0:F1} s)");
            // check and unpack off the main thread
            string err = null; long unpacked = 0; var dir = Dir(r.Id); var part = dir + ".part";
            var job = System.Threading.Tasks.Task.Run(() =>
            {
                try
                {
                    var fi = new FileInfo(zip);
                    if (fi.Length != r.Bytes) { err = $"the download is {fi.Length} bytes, not {r.Bytes}"; return; }
                    if (Sha256(zip) != r.Sha256) { err = "the download failed its checksum"; return; }
                    if (Directory.Exists(part)) Directory.Delete(part, true);
                    Directory.CreateDirectory(part); var full = Path.GetFullPath(part) + Path.DirectorySeparatorChar;
                    using (var za = ZipFile.OpenRead(zip))
                        foreach (var en in za.Entries)
                        {
                            if (string.IsNullOrEmpty(en.Name)) continue;   // a folder
                            var dst = Path.GetFullPath(Path.Combine(part, en.FullName));
                            if (!dst.StartsWith(full, StringComparison.Ordinal)) { err = $"refused path {en.FullName}"; return; }
                            Directory.CreateDirectory(Path.GetDirectoryName(dst));
                            en.ExtractToFile(dst, true); unpacked += en.Length;
                        }
                    if (!File.Exists(Path.Combine(part, "room.gltf"))) { err = "the package has no room.gltf"; return; }
                    if (Directory.Exists(dir)) Directory.Delete(dir, true);
                    Directory.Move(part, dir);
                }
                catch (Exception e) { err = e.Message; }
                finally { TryDelete(zip); try { if (Directory.Exists(part)) Directory.Delete(part, true); } catch { } }
            });
            while (!job.IsCompleted) yield return null;
            if (err != null) { Debug.LogWarning($"[Fable] scene rooms: {r.Id}: {err}"); fail(err); yield break; }
            cache.Rooms[r.Id] = new Entry { Ref = r, Bytes = unpacked, LastUsedUtc = DateTime.UtcNow.ToString("o") }; Save();
            Debug.Log($"[Fable] scene rooms: {r.Id} {r.Version} on the headset ({unpacked / 1e6:F1} MB unpacked, {Time.realtimeSinceStartup - t0:F1} s in all)");
        }

        /// Evict least recently used rooms until `need` more bytes fit under the cap.
        void MakeRoom(long need, string keep)
        {
            long used = cache.Rooms.Values.Sum(e => e.Bytes);
            foreach (var kv in cache.Rooms.OrderBy(kv => kv.Value.LastUsedUtc ?? "").ToList())
            {
                if (used + need <= CapBytes) break;
                if (kv.Key == keep || kv.Key == InUse || active.ContainsKey(kv.Key)) continue;
                try { if (Directory.Exists(Dir(kv.Key))) Directory.Delete(Dir(kv.Key), true); } catch (Exception e) { Debug.LogWarning($"[Fable] scene rooms: {e.Message}"); continue; }
                used -= kv.Value.Bytes; cache.Rooms.Remove(kv.Key);
                Debug.Log($"[Fable] scene rooms: {kv.Key} removed from the headset (least recently used; cache cap {CapBytes / 1e6:F0} MB)");
            }
            Save();
        }

        static void TryDelete(string p) { try { if (File.Exists(p)) File.Delete(p); } catch { } }

        static string Sha256(string path)
        {
            using var s = File.OpenRead(path); using var h = SHA256.Create();
            return BitConverter.ToString(h.ComputeHash(s)).Replace("-", "").ToLowerInvariant();
        }

        // ---------------------------------------------------------------- prefetch

        [UnityEngine.Scripting.Preserve]
        class IndexRoom
        {
            [JsonProperty("id")] public string Id; [JsonProperty("version")] public string Version; [JsonProperty("zip")] public string Zip;
            [JsonProperty("bytes")] public long Bytes; [JsonProperty("sha256")] public string Sha256; [JsonProperty("chapters")] public List<string> Chapters;
            [UnityEngine.Scripting.Preserve] public IndexRoom() { }
        }
        [UnityEngine.Scripting.Preserve] class IndexAnswer { [JsonProperty("rooms")] public List<IndexRoom> Rooms; [UnityEngine.Scripting.Preserve] public IndexAnswer() { } }

        /// Fetch quietly the rooms published for these chapters (the one entered and the next). Cheap to call again.
        public void Prefetch(params string[] chapters)
        {
            if (chapters == null || chapters.Length == 0 || string.IsNullOrEmpty(ServiceUrl)) return;
            StartCoroutine(PrefetchFor(chapters.Where(c => c != null).ToArray()));
        }

        IEnumerator PrefetchFor(string[] chapters)
        {
            if (serviceIndex == null || Time.realtimeSinceStartup - indexAt > 600)
            {
                using var req = UnityWebRequest.Get(ServiceUrl + "/scene-rooms/index.json"); req.timeout = 8;
                yield return req.SendWebRequest();
                if (req.result != UnityWebRequest.Result.Success) yield break;
                try { serviceIndex = JsonConvert.DeserializeObject<IndexAnswer>(req.downloadHandler.text)?.Rooms ?? new List<IndexRoom>(); indexAt = Time.realtimeSinceStartup; }
                catch { yield break; }
            }
            foreach (var room in serviceIndex.Where(x => x.Chapters != null && x.Chapters.Any(chapters.Contains)))
            {
                var r = new SceneRoomRef { Id = room.Id, Version = room.Version, File = room.Zip, Bytes = room.Bytes, Sha256 = room.Sha256 };
                if (r.Valid && !IsReady(r) && !active.ContainsKey(r.Id) && !prefetch.Any(q => q.Id == r.Id)) { prefetch.Enqueue(r); Debug.Log($"[Fable] scene rooms: prefetching {r.Id} for {string.Join(", ", chapters)}"); }
            }
            if (prefetching) yield break;
            prefetching = true;
            try { while (prefetch.Count > 0) { var r = prefetch.Dequeue(); yield return Fetch(r, null); } }
            finally { prefetching = false; }
        }

        public string Describe() => $"scene rooms: {cache.Rooms.Count} cached [{string.Join(", ", cache.Rooms.Keys)}], {active.Count} downloading, {prefetch.Count} queued";
    }
}
