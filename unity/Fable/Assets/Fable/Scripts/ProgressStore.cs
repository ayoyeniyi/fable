// Reading progress and the scene cache live in persistentDataPath, so a reader comes back to the
// sentence they left (in every passage, not just the last one) and the headset works offline with the
// last good interpretation.
using System;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json;
using UnityEngine;

namespace Fable
{
    [Serializable]
    public class Progress
    {
        public string SceneId;
        public int BeatIndex = -1;
        public string SentenceId;
        public string SavedAtUtc;
    }

    /// Where the reader is in a whole book: the first sentence of the page they were on, their bookmarks
    /// (page-start sentence ids) and the text size they chose.
    [Serializable]
    public class BookProgress
    {
        public string Slug;
        public string SentenceId;
        public List<string> Bookmarks = new();
        public int TextSize = 1;
        public string SavedAtUtc;
    }

    /// progress.json: the passage read last, and where the reader is in each passage.
    /// Older files held a single Progress at the top level; they are read as that passage's entry.
    [Serializable]
    public class ProgressFile
    {
        public string LastSceneId;
        public Dictionary<string, Progress> Scenes = new();
        public string LastBook;
        public Dictionary<string, BookProgress> Books = new();
        // legacy single-passage fields
        public string SceneId; public int BeatIndex = -1; public string SentenceId; public string SavedAtUtc;
    }

    public static class ProgressStore
    {
        static string Dir => Application.persistentDataPath;
        static string ProgressPath => Path.Combine(Dir, "progress.json");
        static string CachePath(string sceneId) => Path.Combine(Dir, "cache", sceneId + ".json");

        static ProgressFile ReadFile()
        {
            try
            {
                if (File.Exists(ProgressPath))
                {
                    var f = JsonConvert.DeserializeObject<ProgressFile>(File.ReadAllText(ProgressPath)) ?? new ProgressFile();
                    f.Scenes ??= new Dictionary<string, Progress>();
                    f.Books ??= new Dictionary<string, BookProgress>();
                    if (!string.IsNullOrEmpty(f.SceneId) && !f.Scenes.ContainsKey(f.SceneId))
                    {
                        f.Scenes[f.SceneId] = new Progress { SceneId = f.SceneId, BeatIndex = f.BeatIndex, SentenceId = f.SentenceId, SavedAtUtc = f.SavedAtUtc };
                        f.LastSceneId ??= f.SceneId;
                    }
                    return f;
                }
            }
            catch (Exception e) { Debug.LogWarning($"[Fable] progress unreadable: {e.Message}"); }
            return new ProgressFile();
        }

        /// Where the reader is in one passage (BeatIndex -1 if never opened).
        public static Progress Load(string sceneId) =>
            ReadFile().Scenes.TryGetValue(sceneId, out var p) && p != null ? p : new Progress { SceneId = sceneId };

        /// The passage read most recently, or null.
        public static string LastSceneId() => ReadFile().LastSceneId;

        public static void Save(string sceneId, int beatIndex, string sentenceId)
        {
            try
            {
                var f = ReadFile();
                f.Scenes[sceneId] = new Progress { SceneId = sceneId, BeatIndex = beatIndex, SentenceId = sentenceId, SavedAtUtc = DateTime.UtcNow.ToString("o") };
                f.LastSceneId = sceneId;
                f.SceneId = null; f.BeatIndex = -1; f.SentenceId = null; f.SavedAtUtc = null;
                File.WriteAllText(ProgressPath, JsonConvert.SerializeObject(f, Formatting.Indented, new JsonSerializerSettings { NullValueHandling = NullValueHandling.Ignore }));
            }
            catch (Exception e) { Debug.LogWarning($"[Fable] progress not saved: {e.Message}"); }
        }

        static void WriteFile(ProgressFile f)
        {
            try { File.WriteAllText(ProgressPath, JsonConvert.SerializeObject(f, Formatting.Indented, new JsonSerializerSettings { NullValueHandling = NullValueHandling.Ignore })); }
            catch (Exception e) { Debug.LogWarning($"[Fable] progress not saved: {e.Message}"); }
        }

        /// Where the reader is in a book (SentenceId null if never opened).
        public static BookProgress LoadBook(string slug)
        {
            var b = ReadFile().Books.TryGetValue(slug, out var p) && p != null ? p : new BookProgress { Slug = slug };
            b.Bookmarks ??= new List<string>();
            return b;
        }

        public static string LastBook() => ReadFile().LastBook;

        public static void SaveBook(BookProgress b)
        {
            var f = ReadFile();
            b.SavedAtUtc = DateTime.UtcNow.ToString("o");
            f.Books[b.Slug] = b; f.LastBook = b.Slug;
            WriteFile(f);
        }

        public static string LoadCachedScript(string sceneId)
        {
            try { var p = CachePath(sceneId); return File.Exists(p) ? File.ReadAllText(p) : null; }
            catch { return null; }
        }

        public static void CacheScript(string sceneId, string json)
        {
            try { Directory.CreateDirectory(Path.Combine(Dir, "cache")); File.WriteAllText(CachePath(sceneId), json); }
            catch (Exception e) { Debug.LogWarning($"[Fable] cache not written: {e.Message}"); }
        }
    }
}
