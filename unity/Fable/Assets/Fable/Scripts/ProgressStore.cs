// Reading progress and the scene cache live in persistentDataPath, so a reader comes back to the
// sentence they left and the headset works offline with the last good interpretation.
using System;
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

    public static class ProgressStore
    {
        static string Dir => Application.persistentDataPath;
        static string ProgressPath => Path.Combine(Dir, "progress.json");
        static string CachePath(string sceneId) => Path.Combine(Dir, "cache", sceneId + ".json");

        public static Progress Load()
        {
            try { if (File.Exists(ProgressPath)) return JsonConvert.DeserializeObject<Progress>(File.ReadAllText(ProgressPath)); }
            catch (Exception e) { Debug.LogWarning($"[Fable] progress unreadable: {e.Message}"); }
            return new Progress();
        }

        public static void Save(string sceneId, int beatIndex, string sentenceId)
        {
            try
            {
                var p = new Progress { SceneId = sceneId, BeatIndex = beatIndex, SentenceId = sentenceId, SavedAtUtc = DateTime.UtcNow.ToString("o") };
                File.WriteAllText(ProgressPath, JsonConvert.SerializeObject(p, Formatting.Indented));
            }
            catch (Exception e) { Debug.LogWarning($"[Fable] progress not saved: {e.Message}"); }
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
