// Highlight words on the page and act on them: Define | Translate | Search | Peek | Step In.
//
//   pinch on the text and drag the ray across words    highlight (a quick pinch still turns the page)
//   pinch and hold still on a word (half a second)      highlight that word
//   release                                             the menu opens around the end of the highlight
//   point at a petal and pinch                          do it; pinch anywhere else to close
//
// Define looks the word up in Webster 1913 (offline). Search lists the sentences already read that contain the
// highlight. Peek shows a low-fi model beside the page: a library model first (a prop of the loaded room or a shipped
// clay model), else a clay model from the interpreter when it is reachable. Step In stages the passage from the
// highlight's sentence. Spoiler rule: only text up to the end of the highlight leaves the device, library entries
// are offered only once the reader has reached them, and Search never looks past the furthest page read.
using System.Collections;
using System.Collections.Generic;
using System.Text;
using Newtonsoft.Json;
using TMPro;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.UI;

namespace Fable
{
    public class Highlighter : MonoBehaviour
    {
        public FlowController Flow;
        public BookReader Reader;
        public PagePointer Pointer;
        public ReaderController Input;
        public SceneDirector Director;

        public float HoldToSelect = 0.5f, DragClaimSeconds = 0.18f;
        public float PeekWaitSeconds = 30f;

        public enum Mode { Idle, Pending, Selecting, Menu, Card }
        public Mode Current { get; private set; } = Mode.Idle;
        public string Phrase { get; private set; } = "";
        public string FirstSentence { get; private set; }
        public string LastSentence { get; private set; }
        public string CardText => cardBody ? cardBody.text : "";
        public string PeekStatus { get; private set; } = "";
        public int PeekTriangles { get; private set; }
        public string LastTimings { get; private set; } = "";

        /// Editor tests: stands in for the right pinch (null = live input).
        public bool? TestPinch;

        Webster dict; PeekLibrary library; bool loading;
        int startWord = -1, endWord = -1; float pinchAt; bool wasPinching;
        readonly List<Rect> rects = new(); readonly List<Image> bars = new();
        RectTransform menu; readonly List<(RectTransform rt, string action, TMP_Text label)> petals = new();
        RectTransform card; TMP_Text cardTitle, cardBody; RectTransform cardClose;
        readonly List<(RectTransform rt, string sentence)> resultRows = new();
        Transform peekRoot; readonly Dictionary<string, Transform> peekParts = new(); readonly List<(TextMeshPro text, LineRenderer line, Transform target)> peekLabels = new();
        Material lineMat; Coroutine peekJob;

        public static readonly string[] Actions = { "define", "translate", "search", "peek", "stepin" };
        static readonly string[] ActionNames = { "Define", "Translate", "Search", "Peek", "Step in" };

        public void Init(FlowController flow, BookReader reader, PagePointer pointer, ReaderController input, SceneDirector director)
        {
            Flow = flow; Reader = reader; Pointer = pointer; Input = input; Director = director;
            Build();
            if (!loading) StartCoroutine(LoadData());
        }

        IEnumerator LoadData()
        {
            loading = true; var t0 = Time.realtimeSinceStartup;
            string json = null;
            yield return Streaming.Text("dictionary/webster1913.json", s => json = s);
            if (json != null) yield return Streaming.Parse<Webster>(json, d => dict = d);
            float tDict = (Time.realtimeSinceStartup - t0) * 1000;
            json = null;
            yield return Streaming.Text("library/peek-library.json", s => json = s);
            if (json != null) yield return Streaming.Parse<PeekLibrary>(json, l => library = l);
            Debug.Log($"[Fable] highlight data: dictionary {(dict != null ? dict.Entries.Count + " headwords" : "missing")} in {tDict:F0} ms, library {(library != null ? library.Entries.Count + " entries" : "missing")}; {(Time.realtimeSinceStartup - t0) * 1000:F0} ms in all (parsed off the main thread)");
        }

        bool Pinching => TestPinch ?? Input.RightPinching;
        bool OnText => Flow && Flow.Current == FlowController.State.Reading && Reader && Reader.ShowsText;

        // ---------------------------------------------------------------- selecting

        void Update()
        {
            if (!OnText) { if (Current != Mode.Idle) Clear(); wasPinching = Pinching; return; }
            bool p = Pinching, down = p && !wasPinching, up = !p && wasPinching; wasPinching = p;
            switch (Current)
            {
                case Mode.Idle:
                    if (down && Pointer.OnPage(true, out var at) && Reader.WordAt(at, out var w) && !OverControl())
                    { startWord = endWord = w; pinchAt = Time.time; Current = Mode.Pending; }
                    break;
                case Mode.Pending:
                    if (up) { Current = Mode.Idle; break; }   // a quick pinch: the page turn happens as before
                    if (Pointer.OnPage(true, out var a2) && Reader.WordAt(a2, out var w2, nearest: true)) endWord = w2;
                    float held = Time.time - pinchAt; int moved = Mathf.Abs(endWord - startWord);
                    if ((moved >= 1 && held > DragClaimSeconds) || moved >= 3 || held > HoldToSelect)
                    {
                        Current = Mode.Selecting;
                        if (TestPinch == null) Input.SuppressCurrentPinch();   // this pinch is a highlight: no page turn, scrub or hold
                        Draw();
                    }
                    break;
                case Mode.Selecting:
                    if (Pointer.OnPage(true, out var a3) && Reader.WordAt(a3, out var w3, nearest: true) && w3 != endWord) { endWord = w3; Draw(); }
                    if (up) Finish();
                    break;
            }
            if (Current == Mode.Menu || Current == Mode.Card) Hover();
            if (peekRoot) TurnPeek();
        }

        bool OverControl() => Reader.PressAt(true, dryRun: true);

        void Draw()
        {
            Reader.SelectionRects(startWord, endWord, rects);
            var body = Reader.Panel.Body.rectTransform;
            while (bars.Count < rects.Count)
            {
                var img = new GameObject("Highlight", typeof(RectTransform)).AddComponent<Image>();
                img.transform.SetParent(body, false); img.raycastTarget = false; img.color = new Color(0.98f, 0.80f, 0.25f, 0.38f);
                var rt = img.rectTransform; rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f); rt.pivot = new Vector2(0.5f, 0.5f);
                bars.Add(img);
            }
            for (int i = 0; i < bars.Count; i++)
            {
                bool on = i < rects.Count; bars[i].gameObject.SetActive(on); if (!on) continue;
                var r = rects[i]; var rt = bars[i].rectTransform;
                // body-local rect -> anchored position relative to the body's centre
                var c = body.rect.center; rt.anchoredPosition = r.center - c; rt.sizeDelta = r.size;
            }
            Phrase = Reader.Selection(startWord, endWord, out var f, out var l); FirstSentence = f; LastSentence = l;
        }

        void Finish()
        {
            var t0 = Time.realtimeSinceStartup;
            Draw();
            ShowMenu(Reader.WordCentre(Mathf.Max(startWord, endWord)));
            LastTimings = $"menu {(Time.realtimeSinceStartup - t0) * 1000:F1} ms";
        }

        /// Test hook: highlight a phrase on the page (as a drag over it would) and open the menu. Returns Describe().
        public string Select(string phrase)
        {
            if (!OnText) return "not on the text";
            int a = Reader.FindWord(phrase, out int b); if (a < 0) return $"\"{phrase}\" is not on this page";
            Clear(); startWord = a; endWord = b; Current = Mode.Selecting; Finish();
            return Describe();
        }

        /// Test hook: the word index of a phrase on the page and its centre in page pixels (to aim a test ray at).
        public Vector3 WordWorld(string phrase, bool last = false)
        {
            int a = Reader.FindWord(phrase, out int b); if (a < 0) return Vector3.zero;
            return Pointer.Page.TransformPoint(Reader.WordCentre(last ? b : a));
        }

        // ---------------------------------------------------------------- menu

        void ShowMenu(Vector2 at)
        {
            Current = Mode.Menu;
            // a ring of petals around the end of the highlight, wide enough to leave the highlighted words in view;
            // each petal is kept on the page on its own, so the ring stays centred on the words even near an edge
            menu.anchoredPosition = Vector2.zero; menu.gameObject.SetActive(true); menu.SetAsLastSibling();
            var half = Pointer.Page.rect.size / 2f;
            for (int i = 0; i < petals.Count; i++)
            {
                float ang = Mathf.PI / 2 - i * 2 * Mathf.PI / petals.Count;   // Define at the top, clockwise
                var pos = at + new Vector2(Mathf.Cos(ang) * 150f, Mathf.Sin(ang) * 100f);
                pos.x = Mathf.Clamp(pos.x, -half.x + 64, half.x - 64); pos.y = Mathf.Clamp(pos.y, -half.y + 26, half.y - 26);
                petals[i].rt.anchoredPosition = pos;
                bool enabled = Enabled(petals[i].action);
                petals[i].label.color = enabled ? new Color(0.20f, 0.14f, 0.08f) : new Color(0.20f, 0.14f, 0.08f, 0.35f);
                petals[i].label.text = ActionNames[i] + (petals[i].action == "translate" ? "\n<size=60%>coming later</size>" : "");
            }
        }

        bool Enabled(string action) => action switch
        {
            "translate" => false,                                    // P1
            "stepin" => Reader.StepInPassage != null,
            _ => Phrase.Trim().Length > 0,
        };

        /// A right pinch (tap) while the menu or a card is up. Returns true when it was used here (no page turn).
        public bool HandleTap(bool right)
        {
            if (Current == Mode.Menu)
            {
                foreach (var p in petals) if (Pointer.Over(right, p.rt)) { if (Enabled(p.action)) Choose(p.action); return true; }
                Clear(); return true;   // a pinch away from the ring closes it
            }
            if (Current == Mode.Card)
            {
                if (Pointer.Over(right, cardClose)) { Clear(); return true; }
                foreach (var r in resultRows) if (r.rt.gameObject.activeSelf && Pointer.Over(right, r.rt)) { var s = r.sentence; Clear(); Reader.GoToSentence(s); return true; }
                if (Pointer.Over(right, card)) return true;   // a pinch on the card itself does nothing
                Clear(); return false;                         // elsewhere on the page: close it, and the page turns as usual
            }
            return false;
        }

        public bool Busy => Current != Mode.Idle;

        /// Do one of the menu's actions on the current highlight. Returns Describe().
        public string Choose(string action)
        {
            if (Current != Mode.Menu && Current != Mode.Card) return "no highlight";
            if (!Enabled(action)) return action + " is not available here";
            menu.gameObject.SetActive(false);
            var t0 = Time.realtimeSinceStartup;
            switch (action)
            {
                case "define": ShowCard("Define", Define(Phrase)); LastTimings = $"define {(Time.realtimeSinceStartup - t0) * 1000:F1} ms"; break;
                case "search": SearchCard(); LastTimings = $"search {(Time.realtimeSinceStartup - t0) * 1000:F1} ms"; break;
                case "peek": Peek(); break;
                case "stepin": { var from = FirstSentence; Clear(); Flow.StepInAt(from); break; }
            }
            return Describe();
        }

        // ---------------------------------------------------------------- Define

        static readonly HashSet<string> Stop = new() { "a", "an", "the", "of", "and", "or", "to", "in", "on", "at", "by", "for", "with", "as", "it", "its", "his", "her", "their", "my", "your", "our", "is", "was", "be", "she", "he", "they", "that", "this", "but", "not" };

        string Define(string phrase)
        {
            if (dict == null) return "The dictionary has not loaded.";
            var words = new List<string>();
            foreach (var raw in phrase.Split(new[] { ' ', '—' }, System.StringSplitOptions.RemoveEmptyEntries)) { var w = Webster.Clean(raw); if (w.Length > 0) words.Add(w); }
            if (words.Count == 0) return "";
            var sb = new StringBuilder(); var tried = new List<string>();
            // the whole phrase first (a compound like "rabbit-hole"), then its content words, at most two
            var order = new List<string>();
            if (words.Count > 1) order.Add(string.Join("-", words));
            var content = words.FindAll(w => !Stop.Contains(w)); if (content.Count == 0) content = words;
            // the head word of an English phrase comes last ("golden key" is a key): define it first
            for (int i = content.Count - 1; i >= 0; i--) order.Add(content[i]);
            int shown = 0;
            foreach (var w in order)
            {
                if (shown >= 2) break;
                if (!dict.Lookup(w, out var head, out var entries)) { if (!w.Contains("-")) tried.Add(w); continue; }
                if (sb.Length > 0) sb.Append("\n\n");
                sb.Append($"<b>{head}</b>");
                int n = 0;
                foreach (var e in entries)
                {
                    if (n >= (words.Count > 1 ? 1 : 2)) break;   // a phrase: the main entry of each word
                    if (!string.IsNullOrEmpty(e.Pos)) sb.Append($"  <i>{e.Pos}</i>");
                    for (int i = 0; i < e.Senses.Count && i < 2; i++) sb.Append($"\n{(e.Senses.Count > 1 ? (i + 1) + ". " : "")}{e.Senses[i]}");
                    n++;
                    if (n < entries.Count && n < (words.Count > 1 ? 1 : 2)) sb.Append("\n");
                }
                shown++;
                if (words.Count > 1 && w.Contains("-")) break;   // the compound answered for the whole phrase
            }
            if (shown == 0) return $"No entry in Webster's 1913 for “{phrase.Trim()}”." + (char.IsUpper(phrase.Trim()[0]) ? "\nNames and coinages are not in the dictionary: try Search to see where it comes up." : "");
            sb.Append("\n\n<size=80%><i>Webster's Unabridged Dictionary, 1913.</i></size>");
            return sb.ToString();
        }

        // ---------------------------------------------------------------- Search

        void SearchCard()
        {
            var hits = Reader.Search(Phrase, resultRows.Count, out int total);
            ShowCard("Search", total == 0 ? $"“{Phrase.Trim()}” does not come up in what you have read so far." : $"“{Phrase.Trim()}” comes up in {total} sentence{(total == 1 ? "" : "s")} of what you have read{(total > hits.Count ? $" (the first {hits.Count} below)" : "")}. Pinch one to go there.\n<size=80%><i>Only pages you have reached are searched.</i></size>");
            for (int i = 0; i < resultRows.Count; i++)
            {
                bool on = i < hits.Count; var row = resultRows[i]; row.rt.gameObject.SetActive(on);
                if (!on) continue;
                resultRows[i] = (row.rt, hits[i].id);
                row.rt.GetComponentInChildren<TMP_Text>(true).text = $"<smallcaps>{hits[i].chapter}</smallcaps>  {hits[i].snippet}";
            }
        }

        // ---------------------------------------------------------------- Peek

        void Peek()
        {
            var t0 = Time.realtimeSinceStartup;
            ClosePeek();
            int end = Reader.Book.Ordinal(LastSentence);
            var e = library?.Match(Reader.Book.Slug, Phrase, end, Reader.Book.Ordinal, out _);
            float tMatch = (Time.realtimeSinceStartup - t0) * 1000;
            if (e != null && e.Kind == "prefab")
            {
                var src = Director && Director.Registry ? Director.Registry.Asset(e.Asset) : null;
                if (src) { ShowPrefab(e, src); LastTimings = $"match {tMatch:F1} ms, build {(Time.realtimeSinceStartup - t0) * 1000 - tMatch:F1} ms (library prefab)"; return; }
                e = null;   // the prop's room is not loaded: try clay instead
            }
            if (e != null && e.Kind == "clay") { peekJob = StartCoroutine(PeekClayFile(e, t0, tMatch)); return; }
            peekJob = StartCoroutine(PeekFromInterpreter(t0, tMatch));
        }

        IEnumerator PeekClayFile(PeekLibrary.Entry e, float t0, float tMatch)
        {
            ShowCard("Peek", "Opening the model…");
            string json = null;
            yield return Streaming.Text("library/" + e.Mock, s => json = s);
            MockModel m = null;
            if (json != null) m = JsonConvert.DeserializeObject<MockModel>(json);
            if (m == null) { ShowCard("Peek", $"The library model for “{e.Title}” is missing from this build."); yield break; }
            ShowClay(m, "from the library");
            LastTimings = $"match {tMatch:F1} ms, load+build {(Time.realtimeSinceStartup - t0) * 1000 - tMatch:F0} ms (library clay)";
        }

        IEnumerator PeekFromInterpreter(float t0, float tMatch)
        {
            var url = Director ? Director.InterpreterUrl : "";
            if (string.IsNullOrEmpty(url)) { ShowCard("Peek", $"No model for “{Phrase.Trim()}” in the library, and the interpreter is not set up, so one cannot be made now."); PeekStatus = "no-match-offline"; yield break; }
            ShowCard("Peek", $"Making a clay model of “{Phrase.Trim()}”…\n<size=80%><i>Claude is shown the book up to the end of your highlight, and nothing after it.</i></size>");
            PeekStatus = "generating";
            var body = JsonConvert.SerializeObject(new { book = Reader.Book.Slug, sentenceId = LastSentence, phrase = Phrase.Trim(), waitSeconds = 8 });
            while (Time.realtimeSinceStartup - t0 < PeekWaitSeconds)
            {
                using var req = new UnityWebRequest(url.TrimEnd('/') + "/peek", "POST");
                req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body)); req.downloadHandler = new DownloadHandlerBuffer();
                req.SetRequestHeader("Content-Type", "application/json"); req.timeout = 12;
                yield return req.SendWebRequest();
                if (Current != Mode.Card) yield break;   // closed meanwhile
                if (req.result == UnityWebRequest.Result.Success && req.responseCode == 200)
                {
                    var m = JsonConvert.DeserializeObject<MockModel>(req.downloadHandler.text);
                    var cache = req.GetResponseHeader("X-Fable-Cache");
                    ShowClay(m, cache == "hit" ? "made earlier by Claude" : "made just now by Claude");
                    LastTimings = $"match {tMatch:F1} ms, interpreter {(Time.realtimeSinceStartup - t0) * 1000 - tMatch:F0} ms ({cache})";
                    yield break;
                }
                if (req.result == UnityWebRequest.Result.Success && req.responseCode == 202) continue;   // still generating
                var why = (req.result == UnityWebRequest.Result.Success || req.responseCode > 0 ? req.downloadHandler.text : req.error) ?? "";
                why = why.Trim().Split('\n')[0]; if (why.Length > 160) why = why.Substring(0, 159) + "…";
                Debug.LogWarning($"[Fable] peek \"{Phrase.Trim()}\": {req.responseCode} {req.error} {req.downloadHandler.text}");
                ShowCard("Peek", $"Could not make a model of “{Phrase.Trim()}” right now.\n<size=80%><i>The interpreter said: {why}</i></size>");
                PeekStatus = "failed"; yield break;
            }
            ShowCard("Peek", $"The model of “{Phrase.Trim()}” is taking too long ({PeekWaitSeconds:F0} s), so Peek has given up for now. Try again in a minute: it may be ready.");
            PeekStatus = "timeout";
        }

        /// Shown no taller than this, so the model sits under the card's caption (the card is 42 cm tall).
        const float PeekMaxHeight = 0.2f;

        Transform NewPeekRoot()
        {
            var page = Pointer.Page;
            peekRoot = new GameObject("Peek").transform;
            // in front of the card, on its left, standing on its lower edge: the model and its labels read with the card
            var bottom = card.TransformPoint(new Vector3(card.rect.center.x, card.rect.yMin, 0));
            peekRoot.position = bottom + page.up * 0.05f - page.right * 0.13f - page.forward * 0.12f;
            peekRoot.rotation = Quaternion.LookRotation(Vector3.ProjectOnPlane(page.forward, Vector3.up).normalized, Vector3.up);
            // the room's lights are off while reading: the model brings a small one of its own
            var lamp = new GameObject("PeekLight").AddComponent<Light>(); lamp.transform.SetParent(peekRoot, false);
            lamp.type = LightType.Point; lamp.range = 1.6f; lamp.intensity = 3.2f; lamp.color = new Color(1f, 0.93f, 0.82f); lamp.shadows = LightShadows.None;
            lamp.transform.localPosition = new Vector3(-0.1f, 0.3f, -0.35f);
            return peekRoot;
        }

        void ShowClay(MockModel m, string from)
        {
            var root = NewPeekRoot();
            m.HeightMetres = Mathf.Min(m.HeightMetres, PeekMaxHeight);
            int tris = ClayBuilder.Build(m, root, peekParts);
            if (tris < 0) { ClosePeek(); ShowCard("Peek", "That model is over the triangle budget, so it is not shown."); PeekStatus = "over-budget"; return; }
            PeekTriangles = tris; PeekStatus = "clay";
            foreach (var l in m.Labels) if (peekParts.TryGetValue(l.Part, out var t)) AddLabel(l.Text, l.Quote, t);
            ShowCard("Peek", $"<b>{m.Title}</b>{(string.IsNullOrEmpty(m.RealHeight) ? "" : $"  ·  {m.RealHeight}")}\n<size=80%><i>A clay model {from}: {tris} triangles. It turns slowly beside the page.</i></size>");
            LayoutLabels();
        }

        void ShowPrefab(PeekLibrary.Entry e, Transform src)
        {
            var root = NewPeekRoot();
            bool was = src.gameObject.activeSelf;
            var copy = Instantiate(src.gameObject, root); copy.SetActive(true); copy.name = "Peek " + e.Asset;
            // a picture of the prop, not the prop: no physics, scripts or animation come with it
            foreach (var c in copy.GetComponentsInChildren<Component>(true))
                if (!(c is Transform || c is MeshFilter || c is MeshRenderer || c is SkinnedMeshRenderer)) Destroy(c);
            copy.transform.localPosition = Vector3.zero; copy.transform.localRotation = Quaternion.identity; copy.transform.localScale = src.lossyScale;
            // with the room hidden there is nothing for metal to reflect, and fully metallic props render black:
            // the copy gets its own materials with the metalness capped (destroyed with it)
            foreach (var mr in copy.GetComponentsInChildren<Renderer>(true))
            {
                var ms = mr.materials;   // instances
                foreach (var m in ms) { if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", Mathf.Min(m.GetFloat("_Metallic"), 0.35f)); if (m.HasProperty("metallicFactor")) m.SetFloat("metallicFactor", Mathf.Min(m.GetFloat("metallicFactor"), 0.35f)); m.name = "Clay peek " + m.name; }
                mr.materials = ms;
            }
            var b = ClayBuilder.Bounds(copy.transform, root);
            float tallest = Mathf.Max(b.size.x, b.size.y, b.size.z), k = tallest > 1e-5f ? Mathf.Min(e.HeightMetres, PeekMaxHeight) / tallest : 1f;
            copy.transform.localScale *= k;
            copy.transform.localPosition = new Vector3(-b.center.x * k, -b.min.y * k, -b.center.z * k);
            int tris = 0; foreach (var mf in copy.GetComponentsInChildren<MeshFilter>(true)) if (mf.sharedMesh) for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) tris += (int)mf.sharedMesh.GetIndexCount(s) / 3;
            PeekTriangles = tris; PeekStatus = "prefab";
            b = ClayBuilder.Bounds(copy.transform, root);
            foreach (var l in e.Labels)
            {
                var at = l.At != null && l.At.Length == 3 ? new Vector3(l.At[0], l.At[1], l.At[2]) : Vector3.zero;
                var anchor = new GameObject("label-at").transform; anchor.SetParent(copy.transform, false);
                anchor.position = root.TransformPoint(b.center + Vector3.Scale(b.size, at));
                AddLabel(l.Text, l.Quote, anchor);
            }
            ShowCard("Peek", $"<b>{e.Title}</b>{(string.IsNullOrEmpty(e.RealHeight) ? "" : $"  ·  {e.RealHeight}")}\n<size=80%><i>The model from this room: {tris} triangles. It turns slowly beside the page.</i></size>");
            LayoutLabels();
        }

        void AddLabel(string text, bool quote, Transform target)
        {
            var go = new GameObject("PeekLabel"); go.transform.SetParent(peekRoot, false);
            var t = go.AddComponent<TextMeshPro>();
            t.font = Reader.Panel.Body.font; t.fontSize = 0.16f; t.color = new Color(0.20f, 0.14f, 0.08f);
            t.text = quote ? $"“{text.Trim('“', '”', '"')}”" : text; t.fontStyle = quote ? FontStyles.Italic : FontStyles.Normal;
            t.rectTransform.sizeDelta = new Vector2(0.2f, 0.04f); t.alignment = TextAlignmentOptions.MidlineLeft; t.textWrappingMode = TextWrappingModes.Normal;
            var line = go.AddComponent<LineRenderer>();
            if (!lineMat) { var sh = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color"); lineMat = new Material(sh); lineMat.color = new Color(0.45f, 0.30f, 0.12f, 1f); }
            line.sharedMaterial = lineMat; line.positionCount = 2; line.widthMultiplier = 0.0015f; line.useWorldSpace = true;
            line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; line.receiveShadows = false;
            peekLabels.Add((t, line, target));
        }

        /// Labels stand in a column to the right of the model, ordered by the height of what they point at.
        void LayoutLabels()
        {
            peekLabels.Sort((a, b) => b.target.position.y.CompareTo(a.target.position.y));
            var b0 = ClayBuilder.Bounds(PeekModel, peekRoot);
            float x = Mathf.Max(b0.max.x, 0.06f) + 0.04f, top = Mathf.Max(b0.max.y, 0.14f), step = Mathf.Max(0.035f, top / Mathf.Max(1, peekLabels.Count));
            for (int i = 0; i < peekLabels.Count; i++)
            {
                var tr = peekLabels[i].text.rectTransform;
                tr.pivot = new Vector2(0, 0.5f);
                tr.localPosition = new Vector3(x, top - i * step, 0);
                tr.localRotation = Quaternion.identity;   // the root looks away from the reader, so the text faces them
            }
        }

        void TurnPeek()
        {
            // the model turns; the labels stay put and their lines follow the parts
            var model = PeekModel;
            if (model) model.Rotate(Vector3.up, 14f * Time.deltaTime, Space.World);
            foreach (var (text, line, target) in peekLabels)
            {
                if (!target) continue;
                var start = text.rectTransform.TransformPoint(new Vector3(-0.006f, 0, 0));
                line.SetPosition(0, start); line.SetPosition(1, target.position);
            }
        }

        Transform PeekModel
        {
            get { if (!peekRoot) return null; foreach (Transform c in peekRoot) if (c.name.StartsWith("Clay ") || c.name.StartsWith("Peek ")) return c; return null; }
        }

        void ClosePeek()
        {
            if (peekJob != null) { StopCoroutine(peekJob); peekJob = null; }
            if (peekRoot)
            {
                var model = PeekModel;
                if (model) { model.SetParent(null); ClayBuilder.DestroyModel(model); }   // clay or a prefab copy: its materials go too
                Destroy(peekRoot.gameObject);
            }
            peekRoot = null; peekParts.Clear(); peekLabels.Clear(); PeekTriangles = 0;
        }

        // ---------------------------------------------------------------- card

        void ShowCard(string title, string text)
        {
            Current = Mode.Card;
            menu.gameObject.SetActive(false);
            card.gameObject.SetActive(true); card.SetAsLastSibling();
            // keep the highlight in view: the card takes the half of the page the highlight is not in
            bool low = startWord >= 0 && Reader.WordCentre(Mathf.Min(startWord, endWord)).y < 0;
            var anchor = new Vector2(0.5f, low ? 1 : 0); card.anchorMin = card.anchorMax = card.pivot = anchor;
            card.anchoredPosition = new Vector2(0, low ? -52 : 52);
            cardTitle.text = title + "  ·  <i>" + Shorten(Phrase.Trim(), 48) + "</i>";
            cardBody.text = text;
            foreach (var r in resultRows) r.rt.gameObject.SetActive(false);
        }

        static string Shorten(string s, int n) => s.Length <= n ? s : s.Substring(0, n - 1) + "…";

        /// Close everything: highlight, menu, card and model.
        public void Clear()
        {
            Current = Mode.Idle; startWord = endWord = -1; Phrase = ""; FirstSentence = LastSentence = null;
            foreach (var b in bars) if (b) b.gameObject.SetActive(false);
            if (menu) menu.gameObject.SetActive(false);
            if (card) card.gameObject.SetActive(false);
            ClosePeek(); PeekStatus = "";
        }

        void Hover()
        {
            void H(RectTransform rt, Color hover)
            {
                if (!rt || !rt.gameObject.activeInHierarchy) return;
                var img = rt.GetComponent<Image>(); var c = Pointer.Over(true, rt) || Pointer.Over(false, rt) ? hover : baseColor[rt];
                if (img.color != c) img.color = c;
            }
            if (Current == Mode.Menu) foreach (var p in petals) H(p.rt, new Color(0.99f, 0.86f, 0.52f, 1f));
            if (Current == Mode.Card) { H(cardClose, new Color(0.45f, 0.36f, 0.24f, 0.25f)); foreach (var r in resultRows) H(r.rt, new Color(0.45f, 0.36f, 0.24f, 0.16f)); }
        }
        readonly Dictionary<RectTransform, Color> baseColor = new();

        // ---------------------------------------------------------------- widgets

        void Build()
        {
            if (menu) return;
            var page = Pointer.Page; var font = Reader.Panel.Body.font;
            RectTransform Box(string name, Transform parent, Vector2 size, Color c)
            {
                var go = new GameObject(name, typeof(RectTransform), typeof(Image)); var rt = go.GetComponent<RectTransform>(); rt.SetParent(parent, false);
                rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(0.5f, 0.5f); rt.sizeDelta = size;
                var img = go.GetComponent<Image>(); img.color = c; img.raycastTarget = false; baseColor[rt] = c;
                return rt;
            }
            TMP_Text Text(Transform parent, float size, TextAlignmentOptions align, Vector2 inset)
            {
                var t = new GameObject("Text", typeof(RectTransform)).AddComponent<TextMeshProUGUI>(); t.transform.SetParent(parent, false);
                t.rectTransform.anchorMin = Vector2.zero; t.rectTransform.anchorMax = Vector2.one; t.rectTransform.offsetMin = inset; t.rectTransform.offsetMax = -inset;
                t.font = font; t.fontSize = size; t.color = new Color(0.16f, 0.12f, 0.08f); t.alignment = align; t.raycastTarget = false; t.richText = true;
                return t;
            }
            menu = new GameObject("HighlightMenu", typeof(RectTransform)).GetComponent<RectTransform>(); menu.SetParent(page, false);
            menu.anchorMin = menu.anchorMax = new Vector2(0.5f, 0.5f); menu.sizeDelta = Vector2.zero; menu.localPosition += new Vector3(0, 0, -2f);
            var paper = new Color(0.97f, 0.93f, 0.84f, 0.97f);
            for (int i = 0; i < Actions.Length; i++)
            {
                var rt = Box("Petal " + Actions[i], menu, new Vector2(118, 44), paper);
                var edge = rt.gameObject.AddComponent<Outline>(); edge.effectColor = new Color(0.45f, 0.33f, 0.18f, 0.9f); edge.effectDistance = new Vector2(2, -2);
                var lbl = Text(rt, 19, TextAlignmentOptions.Center, new Vector2(4, 2)); lbl.fontStyle = FontStyles.SmallCaps; lbl.lineSpacing = -20;
                petals.Add((rt, Actions[i], lbl));
            }
            menu.gameObject.SetActive(false);

            card = Box("HighlightCard", page, new Vector2(560, 420), new Color(0.985f, 0.96f, 0.90f, 0.99f));
            card.anchorMin = card.anchorMax = card.pivot = new Vector2(0.5f, 0); card.anchoredPosition = new Vector2(0, 52); card.localPosition += new Vector3(0, 0, -2f);
            var rule = Box("Rule", card, new Vector2(560, 3), new Color(0.55f, 0.36f, 0.08f, 0.9f)); rule.anchorMin = rule.anchorMax = rule.pivot = new Vector2(0.5f, 1); rule.anchoredPosition = Vector2.zero;
            var titleRt = new GameObject("Title", typeof(RectTransform)).GetComponent<RectTransform>(); titleRt.SetParent(card, false);
            titleRt.anchorMin = new Vector2(0, 1); titleRt.anchorMax = new Vector2(1, 1); titleRt.pivot = new Vector2(0.5f, 1); titleRt.sizeDelta = new Vector2(-90, 40); titleRt.anchoredPosition = new Vector2(-30, -10);
            cardTitle = Text(titleRt, 20, TextAlignmentOptions.Left, new Vector2(4, 0)); cardTitle.fontStyle = FontStyles.SmallCaps; cardTitle.color = new Color(0.45f, 0.29f, 0.07f); cardTitle.overflowMode = TextOverflowModes.Ellipsis; cardTitle.textWrappingMode = TextWrappingModes.NoWrap;
            cardClose = Box("Close", card, new Vector2(84, 36), new Color(0.45f, 0.36f, 0.24f, 0f)); cardClose.anchorMin = cardClose.anchorMax = cardClose.pivot = new Vector2(1, 1); cardClose.anchoredPosition = new Vector2(-10, -10);
            var closeLbl = Text(cardClose, 17, TextAlignmentOptions.Right, new Vector2(6, 0)); closeLbl.text = "close ×"; closeLbl.fontStyle = FontStyles.SmallCaps;
            var bodyRt = new GameObject("Body", typeof(RectTransform)).GetComponent<RectTransform>(); bodyRt.SetParent(card, false);
            bodyRt.anchorMin = new Vector2(0, 0); bodyRt.anchorMax = new Vector2(1, 1); bodyRt.offsetMin = new Vector2(22, 16); bodyRt.offsetMax = new Vector2(-22, -56);
            cardBody = Text(bodyRt, 18.5f, TextAlignmentOptions.TopLeft, Vector2.zero); cardBody.overflowMode = TextOverflowModes.Ellipsis; cardBody.lineSpacing = 4;
            for (int r = 0; r < 6; r++)
            {
                var row = Box("Result" + r, card, new Vector2(530, 44), new Color(0.45f, 0.36f, 0.24f, 0f)); row.anchorMin = row.anchorMax = row.pivot = new Vector2(0.5f, 1);
                row.anchoredPosition = new Vector2(0, -126 - r * 47);
                var t = Text(row, 15.5f, TextAlignmentOptions.MidlineLeft, new Vector2(8, 2)); t.overflowMode = TextOverflowModes.Ellipsis; t.lineSpacing = -8;
                resultRows.Add((row, null)); row.gameObject.SetActive(false);
            }
            card.gameObject.SetActive(false);
        }

        public string Describe() => $"highlight={Current} phrase=\"{Phrase.Trim()}\" from={FirstSentence ?? "-"} to={LastSentence ?? "-"} peek={PeekStatus} tris={PeekTriangles} timings=[{LastTimings}] dict={(dict != null)} library={(library != null)}";
    }
}
