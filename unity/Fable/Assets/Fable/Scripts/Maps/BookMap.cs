// The book's map (docs/MAPS.md, docs/MAPS_HEADSET.md): map.json for the open book, the matching rule Peek uses to
// decide whether a highlight names a place, and the map images, loaded once per book and released when it closes.
//
//   map.json   StreamingAssets/maps/<slug>/map.json (FableBuild.SyncData copies content/maps). A book without one has
//              no map, and Peek makes its clay model as before.
//   images     Resources/Maps/<path after "maps/"> (also SyncData), imported as ASTC with mipmaps; the Earth is shared.
//
// Hosted maps (GET <interpreter>/maps/<slug>, docs/MAPS.md) are not fetched yet. The hook is FetchHosted below: an
// uploaded book would set it, and an image missing from Resources would then be fetched with UnityWebRequestTexture
// from the same server (LoadTexture). Neither is needed for the bundled books.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using Newtonsoft.Json;
using UnityEngine;

namespace Fable
{
    public class MapDoc
    {
        public class LatLon { [JsonProperty("lat")] public float Lat; [JsonProperty("lon")] public float Lon; }
        public class View
        {
            [JsonProperty("id")] public string Id;
            [JsonProperty("kind")] public string Kind;            // globe | scroll
            [JsonProperty("title")] public string Title;
            [JsonProperty("texture")] public string Texture;      // globe
            [JsonProperty("focus")] public LatLon Focus;          // globe, optional
            [JsonProperty("image")] public string Image;          // scroll
            [JsonProperty("aspect")] public float Aspect = 1.4f;  // scroll: width / height
            [JsonProperty("parent")] public string Parent;
            [JsonProperty("anchor")] public string Anchor;
            [JsonProperty("attribution")] public string Attribution;
            public bool Globe => Kind == "globe";
            public string ImagePath => Globe ? Texture : Image;
        }
        public class Place
        {
            [JsonProperty("id")] public string Id;
            [JsonProperty("name")] public string Name;
            /// What the headset shows for the place when it should read better than name; never matched.
            [JsonProperty("label")] public string Label;
            public string Display => string.IsNullOrEmpty(Label) ? Name : Label;
            [JsonProperty("aliases")] public List<string> Aliases = new();
            [JsonProperty("kind")] public string Kind;
            [JsonProperty("view")] public string View;
            [JsonProperty("lat")] public float Lat;
            [JsonProperty("lon")] public float Lon;
            [JsonProperty("u")] public float U;
            [JsonProperty("v")] public float V;
            [JsonProperty("firstSentence")] public string FirstSentence;
            [JsonProperty("note")] public string Note;
            /// Reading order of firstSentence in the open book (-1: not in the book, so never revealed).
            [JsonIgnore] public int Ordinal = -1;
            /// name and aliases, normalised (BookMap.Normalise), longest first.
            [JsonIgnore] public List<string> Phrases = new();
            public bool Area => Kind == "region" || Kind == "country" || Kind == "sea";
        }
        [JsonProperty("version")] public int Version;
        [JsonProperty("book")] public string Book;
        [JsonProperty("views")] public List<View> Views = new();
        [JsonProperty("places")] public List<Place> Places = new();

        public View FindView(string id) { foreach (var v in Views) if (v.Id == id) return v; return null; }
        public Place FindPlace(string id) { foreach (var p in Places) if (p.Id == id) return p; return null; }
    }

    public class BookMap : MonoBehaviour
    {
        /// The book whose map is loaded (or loading); null when none.
        public string Slug { get; private set; }
        public MapDoc Doc { get; private set; }
        public bool Loading { get; private set; }

        /// Hook for hosted maps: given a slug, a coroutine that yields the map.json text (or null). Not set for the
        /// bundled books; an uploaded book's reader would point it at GET <interpreter>/maps/<slug>.
        public static Func<string, Action<string>, IEnumerator> FetchHosted;

        readonly Dictionary<string, Texture2D> textures = new();
        readonly Dictionary<string, ResourceRequest> pending = new();
        Book book;

        /// Load the map of this book if it is not the one loaded; release the last book's images. Cheap when unchanged.
        public void Ensure(Book b)
        {
            if (b == book) return;
            Release(); book = b;
            if (b == null) return;
            Slug = b.Slug; StartCoroutine(Load(b));
        }

        /// Forget the map and unload its images (the book closed, or another opened).
        public void Release()
        {
            StopAllCoroutines(); Loading = false;
            foreach (var t in textures.Values) if (t) Resources.UnloadAsset(t);
            textures.Clear(); pending.Clear();
            Doc = null; Slug = null; book = null;
        }

        void OnDestroy() => Release();

        IEnumerator Load(Book b)
        {
            Loading = true; var t0 = Time.realtimeSinceStartup;
            string json = null;
            yield return Streaming.Text($"maps/{b.Slug}/map.json", s => json = s);
            if (json == null && FetchHosted != null) yield return FetchHosted(b.Slug, s => json = s);
            if (json == null) { Loading = false; yield break; }   // no map for this book: Peek stays clay
            MapDoc doc = null;
            yield return Streaming.Parse<MapDoc>(json, d => doc = d);
            if (doc == null || b != book) { Loading = false; yield break; }
            foreach (var p in doc.Places)
            {
                p.Ordinal = b.Ordinal(p.FirstSentence);
                p.Phrases.Clear();
                void Add(string s) { var n = Normalise(s); if (n.Length > 0 && !p.Phrases.Contains(n)) p.Phrases.Add(n); }
                Add(p.Name); if (p.Aliases != null) foreach (var a in p.Aliases) Add(a);
                p.Phrases.Sort((x, y) => y.Length.CompareTo(x.Length));
                if (p.Ordinal < 0) Debug.LogWarning($"[Fable] map {b.Slug}: place {p.Id} has firstSentence {p.FirstSentence}, which is not in the book; it is never shown");
            }
            Doc = doc; Loading = false;
            Debug.Log($"[Fable] map {b.Slug}: {doc.Views.Count} view(s), {doc.Places.Count} places ({(Time.realtimeSinceStartup - t0) * 1000:F0} ms)");
        }

        // ---------------------------------------------------------------- matching (docs/MAPS.md "Matching a highlight")

        /// The revealed place the highlight names, or null. revealedUpTo is the reading-order ordinal of the sentence
        /// holding the highlight: a place counts once its firstSentence is at or before it. Several matches: the longest
        /// matched phrase wins, then the first in the file.
        public MapDoc.Place Match(string phrase, int revealedUpTo, out string matched)
        {
            matched = null;
            if (Doc == null) return null;
            var h = Normalise(phrase); if (h.Length == 0) return null;
            var padded = " " + h + " ";
            MapDoc.Place best = null; int bestLen = 0;
            foreach (var p in Doc.Places)
            {
                if (p.Ordinal < 0 || p.Ordinal > revealedUpTo) continue;
                foreach (var a in p.Phrases)   // longest first: the first hit is this place's best
                {
                    if (a.Length <= bestLen) break;
                    if (a == h || padded.Contains(" " + a + " ")) { best = p; bestLen = a.Length; matched = a; break; }
                }
            }
            return best;
        }

        public bool Revealed(MapDoc.Place p, int upTo) => p != null && p.Ordinal >= 0 && p.Ordinal <= upTo;

        /// docs/MAPS.md step 1: NFKC; curly quotes straight; figure/en/em dashes (U+2012-2015) to a space and the hyphens
        /// U+2010/2011 to '-'; anything not a letter, digit, apostrophe, hyphen or space to a space; whitespace collapsed,
        /// trimmed, lower-cased; one leading "the " dropped. One addition (the reading of "trim punctuation" in the
        /// interpreter's NormalisePhrase): apostrophes and hyphens at the ends of a word are dropped, so a highlight
        /// taken from inside quotation marks ('Woking') still matches. Place phrases go through the same function.
        public static string Normalise(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            try { s = s.Normalize(NormalizationForm.FormKC); } catch (ArgumentException) { }
            var sb = new StringBuilder(s.Length);
            foreach (var ch0 in s)
            {
                char ch = ch0;
                if (ch == '‘' || ch == '’' || ch == '‛' || ch == 'ʼ') ch = '\'';
                else if (ch >= '‒' && ch <= '―') ch = ' ';
                else if (ch == '‐' || ch == '‑') ch = '-';
                if (!(char.IsLetterOrDigit(ch) || ch == '\'' || ch == '-')) ch = ' ';
                sb.Append(char.ToLowerInvariant(ch));
            }
            var words = sb.ToString().Split(' ', StringSplitOptions.RemoveEmptyEntries);
            sb.Clear();
            foreach (var w0 in words)
            {
                var w = w0.Trim('\'', '-'); if (w.Length == 0) continue;
                if (sb.Length > 0) sb.Append(' ');
                sb.Append(w);
            }
            var r = sb.ToString();
            return r.StartsWith("the ") ? r.Substring(4) : r;
        }

        // ---------------------------------------------------------------- images

        /// The view's image, loading it (asynchronously, once per book) if needed. done(null) if it is missing.
        public IEnumerator LoadTexture(MapDoc.View v, Action<Texture2D> done)
        {
            var path = v?.ImagePath;
            if (string.IsNullOrEmpty(path) || !path.StartsWith("maps/")) { done(null); yield break; }
            if (textures.TryGetValue(path, out var hit) && hit) { done(hit); yield break; }
            var res = "Maps/" + System.IO.Path.ChangeExtension(path.Substring(5), null);
            if (!pending.TryGetValue(path, out var req)) pending[path] = req = Resources.LoadAsync<Texture2D>(res);
            while (!req.isDone) yield return null;
            pending.Remove(path);
            var tex = req.asset as Texture2D;
            if (!tex) Debug.LogWarning($"[Fable] map image {path} is not in this build (Resources/{res}); run FableBuild.SyncData");
            else textures[path] = tex;
            done(tex);
        }

        /// Texture memory of the images loaded now (for the report and Describe()).
        public long TextureBytes()
        {
            long n = 0;
            foreach (var t in textures.Values) if (t) n += UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(t);
            return n;
        }

        public string Describe() => Doc == null ? (Loading ? $"map={Slug}(loading)" : "map=none") : $"map={Slug} views={Doc.Views.Count} places={Doc.Places.Count} textures={textures.Count}({TextureBytes() / 1e6:F1} MB)";
    }
}
