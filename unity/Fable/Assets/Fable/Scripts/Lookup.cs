// Offline data behind the highlight menu: the dictionary for Define (Webster 1913, content/dictionary) and the Peek
// library index (content/library). Both ship in StreamingAssets and parse off the main thread.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading.Tasks;
using Newtonsoft.Json;
using UnityEngine;

namespace Fable
{
    public static class Streaming
    {
        /// Read a StreamingAssets file (a jar URL on Android, a plain file elsewhere). done(null) if it is missing.
        public static IEnumerator Text(string relative, Action<string> done)
        {
            var path = System.IO.Path.Combine(Application.streamingAssetsPath, relative);
#if UNITY_ANDROID && !UNITY_EDITOR
            using var req = UnityEngine.Networking.UnityWebRequest.Get(path);
            yield return req.SendWebRequest();
            done(req.result == UnityEngine.Networking.UnityWebRequest.Result.Success ? req.downloadHandler.text : null);
#else
            yield return null;
            done(System.IO.File.Exists(path) ? System.IO.File.ReadAllText(path) : null);
#endif
        }

        /// Parse JSON on a worker thread and wait for it without blocking the frame.
        public static IEnumerator Parse<T>(string json, Action<T> done)
        {
            var task = Task.Run(() => JsonConvert.DeserializeObject<T>(json));
            while (!task.IsCompleted) yield return null;
            if (task.IsFaulted) { Debug.LogError($"[Fable] parse {typeof(T).Name}: {task.Exception?.GetBaseException().Message}"); done(default); }
            else done(task.Result);
        }
    }

    public class Webster
    {
        public class Entry { [JsonProperty("pos")] public string Pos; [JsonProperty("senses")] public List<string> Senses; }
        [JsonProperty("entries")] public Dictionary<string, List<Entry>> Entries = new();
        [JsonProperty("forms")] public Dictionary<string, string> Forms = new();

        /// Mirrors lemmas() in tools/ingest_dictionary.py.
        static IEnumerable<string> Lemmas(string w)
        {
            yield return w;
            if (w.EndsWith("'s")) yield return w.Substring(0, w.Length - 2);
            string[,] rules = { { "ies", "y" }, { "ied", "y" }, { "ier", "y" }, { "iest", "y" }, { "ily", "y" }, { "ves", "f" }, { "ves", "fe" }, { "sses", "ss" }, { "ches", "ch" }, { "shes", "sh" }, { "xes", "x" }, { "es", "" }, { "s", "" }, { "ing", "" }, { "ing", "e" }, { "ed", "" }, { "ed", "e" }, { "d", "" }, { "ly", "" }, { "er", "" }, { "est", "" }, { "ness", "" } };
            for (int i = 0; i < rules.GetLength(0); i++)
            {
                string suf = rules[i, 0], rep = rules[i, 1];
                if (!w.EndsWith(suf) || w.Length - suf.Length < 2) continue;
                var stem = w.Substring(0, w.Length - suf.Length) + rep;
                yield return stem;
                if ((suf == "ing" || suf == "ed" || suf == "er" || suf == "est") && stem.Length > 2 && stem[^1] == stem[^2]) yield return stem.Substring(0, stem.Length - 1);
            }
            if (w.Contains("-")) yield return w.Replace("-", "");
        }

        public static string Clean(string word)
        {
            var w = word.ToLowerInvariant().Replace('’', '\'').Replace('‘', '\'');
            return w.Trim(' ', '\'', '"', '“', '”', '.', ',', ';', ':', '!', '?', '(', ')', '—', '-');
        }

        public bool Lookup(string word, out string head, out List<Entry> entries)
        {
            head = null; entries = null;
            var w = Clean(word); if (w.Length == 0) return false;
            if (Forms.TryGetValue(w, out var f) && Entries.TryGetValue(f, out entries)) { head = f; return true; }
            foreach (var l in Lemmas(w)) if (Entries.TryGetValue(l, out entries)) { head = l; return true; }
            return false;
        }
    }

    public class PeekLibrary
    {
        public class Label { [JsonProperty("text")] public string Text; [JsonProperty("at")] public float[] At; [JsonProperty("part")] public string Part; [JsonProperty("quote")] public bool Quote; }
        public class Entry
        {
            [JsonProperty("id")] public string Id;
            [JsonProperty("book")] public string Book;
            [JsonProperty("kind")] public string Kind;          // prefab | clay
            [JsonProperty("scene")] public string Scene;
            [JsonProperty("asset")] public string Asset;
            [JsonProperty("mock")] public string Mock;
            [JsonProperty("title")] public string Title;
            [JsonProperty("aliases")] public List<string> Aliases = new();
            [JsonProperty("notBefore")] public string NotBefore;
            [JsonProperty("heightMetres")] public float HeightMetres = 0.25f;
            [JsonProperty("realHeight")] public string RealHeight;
            [JsonProperty("labels")] public List<Label> Labels = new();
            [JsonProperty("licence")] public string Licence;
        }
        [JsonProperty("entries")] public List<Entry> Entries = new();

        static readonly HashSet<string> Stop = new() { "a", "an", "the", "of", "and", "her", "his", "its", "my", "your", "their", "this", "that", "little", "large", "great", "old", "some", "two", "three" };

        static string[] Words(string s) => Webster.Clean(s).Replace('-', ' ').Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);

        /// The best entry for a highlight, or null. Only entries of this book the reader has reached (notBefore at or
        /// before the highlight's last sentence). Scores: the whole highlight is an alias 1.0; an alias appears whole in the
        /// highlight 0.9 less 0.05 per extra word; the highlight's head word (last content word) ends an alias 0.7.
        public Entry Match(string book, string phrase, int highlightEnd, Func<string, int> ordinal, out float score)
        {
            score = 0; Entry best = null;
            var hw = Words(phrase); if (hw.Length == 0) return null;
            string joined = " " + string.Join(" ", hw) + " ";
            string head = null; for (int i = hw.Length - 1; i >= 0 && head == null; i--) if (!Stop.Contains(hw[i])) head = Singular(hw[i]);
            foreach (var e in Entries)
            {
                if (e.Book != book) continue;
                int nb = ordinal(e.NotBefore); if (nb < 0 || nb > highlightEnd) continue;
                foreach (var alias in e.Aliases)
                {
                    var aw = Words(alias); if (aw.Length == 0) continue;
                    var a = " " + string.Join(" ", aw) + " ";
                    float s = 0;
                    if (a == joined) s = 1f;
                    else if (joined.Contains(a)) s = 0.9f - 0.05f * (hw.Length - aw.Length);
                    else if (head != null && Singular(aw[^1]) == head) s = 0.7f;
                    if (s > score || (s == score && best != null && s > 0 && ordinal(e.NotBefore) > ordinal(best.NotBefore))) { score = s; best = e; }
                }
            }
            return score >= 0.6f ? best : null;
        }

        static string Singular(string w) => w.EndsWith("ies") ? w[..^3] + "y" : w.EndsWith("ses") || w.EndsWith("xes") ? w[..^2] : w.EndsWith("s") && !w.EndsWith("ss") && w.Length > 3 ? w[..^1] : w;
    }
}
