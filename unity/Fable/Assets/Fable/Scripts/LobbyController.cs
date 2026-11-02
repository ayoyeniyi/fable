// The lobby: a panelled reading room where Fable opens, with the four books standing face out on a bookcase
// (blender/build_lobby.py). Point at a book with either hand (or the mouse in the editor) and it slides forward;
// pinch to open it. A small card in front of each book says how far the reader has got. The page's "shelf" control
// comes back here.
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Fable
{
    public class LobbyController : MonoBehaviour
    {
        public const string SceneName = "Lobby";
        public ReaderController Input;
        public Transform Head, Env;
        public TMP_FontAsset Font;
        public Color Ink = new(0.16f, 0.11f, 0.06f), CardDim = new(0.52f, 0.47f, 0.38f), CardLit = new(0.90f, 0.84f, 0.70f), RayColour = new(0.85f, 0.62f, 0.22f);
        public float SlideMetres = 0.06f, MaxRay = 6f;

        /// Where each book is read: its own P0 room. A room missing from the build falls back to the Hall of Doors scene's
        /// quiet reading space.
        public static readonly Dictionary<string, string> ReadingScene = new()
        {
            ["alice"] = "HallOfDoors", ["oz"] = "KansasFarmhouse", ["odyssey"] = "CalypsosCave", ["gulliver"] = "GlumdalclitchsRoom",
        };
        const string FallbackScene = "HallOfDoors";
        /// Where the reader's own books are read: the library room itself, with the page in front of the shelves.
        public const string ImportedScene = "LibraryRoom";

        class Shelved
        {
            public string Slug; public Transform T; public Vector3 Home, Out, CoverNormal; public BoxCollider Box;
            public TextMeshPro Label; public Material CardMat; public float Hover;
        }
        readonly List<Shelved> books = new();
        LineRenderer ray; Transform dot; Material rayMat;
        Shelved hovered; bool opening;
        BooksIndex index;

        /// Editor tests: a right-hand ray to use instead of the hand or mouse (null = live input).
        public Ray? TestRay;
        public string Hovered => hovered?.Slug;
        /// When the last book was pinched (realtime), so the reading scene can log how long the book took to reach the page.
        public static float OpenedAt = -1;

        class BooksIndex
        {
            public class Chapter { [JsonProperty("id")] public string Id; [JsonProperty("heading")] public string Heading; [JsonProperty("name")] public string Name; [JsonProperty("first")] public int First; [JsonProperty("sentences")] public int Sentences; [JsonProperty("paragraphs")] public int Paragraphs; }
            public class Entry { [JsonProperty("slug")] public string Slug; [JsonProperty("title")] public string Title; [JsonProperty("author")] public string Author; [JsonProperty("sentences")] public int Sentences; [JsonProperty("chapters")] public List<Chapter> Chapters = new(); }
            [JsonProperty("books")] public List<Entry> Books = new();
        }

        IEnumerator Start()
        {
            if (!Env) Env = transform;
            if (!UnityEngine.XR.XRSettings.isDeviceActive && Head && Head.localPosition.y < 0.5f) Head.localPosition = new Vector3(0, 1.62f, 0);
            foreach (var t in Env.GetComponentsInChildren<Transform>(true))
            {
                if (!t.name.StartsWith("book.")) continue;
                var b = new Shelved { Slug = t.name.Substring(5), T = t, Home = t.localPosition };
                // a collider fitted to the book in its own (leaning) frame, a little generous: a hand is never steady
                var bounds = new Bounds(); bool any = false;
                foreach (var r in t.GetComponentsInChildren<Renderer>())
                {
                    var lb = r.localBounds; var m = t.worldToLocalMatrix * r.transform.localToWorldMatrix;
                    foreach (var c in Corners(lb)) { var p = m.MultiplyPoint3x4(c); if (!any) { bounds = new Bounds(p, Vector3.zero); any = true; } else bounds.Encapsulate(p); }
                }
                b.Box = t.gameObject.AddComponent<BoxCollider>(); b.Box.center = bounds.center; b.Box.size = bounds.size + new Vector3(0.03f, 0.03f, 0.03f);
                // "out": level, from the book towards the room (the cover side)
                var toRoom = (Head ? Head.position : Vector3.zero) - t.position; toRoom.y = 0;
                b.Out = toRoom.sqrMagnitude > 1e-4f ? toRoom.normalized : -t.forward;
                // the way the cover faces (from the cover plane's mesh), so the book can turn its cover to the reader
                var cover = t.GetComponentsInChildren<MeshFilter>().FirstOrDefault(f => f.name.StartsWith("Cover_"));
                b.CoverNormal = cover && cover.sharedMesh && cover.sharedMesh.normals.Length > 0 ? cover.transform.TransformDirection(cover.sharedMesh.normals[0]).normalized : b.Out;
                if (Vector3.Dot(b.CoverNormal, b.Out) < 0) b.CoverNormal = -b.CoverNormal;
                b.Label = MakeLabel(b);
                books.Add(b);
            }
            Debug.Log($"[Fable] lobby: {books.Count} books on the shelf");
            MakeRay();
            if (Input) Input.PinchBegan += OnPinch;
            // the view toolbar: turn to see the room, and "recentre" faces the shelf again
            View = GetComponent<ViewControls>() ? GetComponent<ViewControls>() : gameObject.AddComponent<ViewControls>();
            // the library board: every book, bundled and imported, at lectern height in front of the reader
            Board = GetComponent<LibraryPanel>() ? GetComponent<LibraryPanel>() : gameObject.AddComponent<LibraryPanel>();
            Board.Init(Input, Head, Font, this);
            View.Init(Input, Head, RigRoot(), Board.Root, Font);
            View.Recentred += () => Board.Recentre();
            View.SetActions(("face the shelf", FaceShelf));
            View.Tip("library", "Your books are on the board below the shelf. \u201c+ add a book\u201d sends one from your phone or computer.");
            string json = null; yield return Streaming.Text("books/index.json", s => json = s);
            if (json != null) yield return Streaming.Parse<BooksIndex>(json, i => index = i);
            RefreshLabels();
            // the board's bundled tiles: titles and authors from the index, covers from the books on the shelf
            foreach (var b in books)
            {
                var e = index?.Books.Find(x => x.Slug == b.Slug);
                Texture cover = null;
                foreach (var r in b.T.GetComponentsInChildren<Renderer>()) if (r.name.StartsWith("Cover_") && r.sharedMaterial) { var m = r.sharedMaterial; cover = m.HasProperty("baseColorTexture") ? m.GetTexture("baseColorTexture") : m.mainTexture; break; }
                Board.Bundled[b.Slug] = (e?.Title ?? b.Slug, e?.Author, cover);
            }
            Board.Recentre(true); Board.Refresh();
        }

        void OnDestroy() { if (Input) Input.PinchBegan -= OnPinch; }

        public ViewControls View { get; private set; }
        public LibraryPanel Board { get; private set; }

        Transform RigRoot()
        {
            Transform rig = Head ? Head.parent : null;
#if FABLE_META_XR
            var ovr = Head ? Head.GetComponentInParent<OVRCameraRig>() : null; if (ovr) rig = ovr.transform;
#endif
            return rig;
        }

        /// Turn the view (about the head) so the reader faces the bookcase again.
        public void FaceShelf()
        {
            var rig = RigRoot(); if (!rig || !Head || books.Count == 0) return;
            var c = Vector3.zero; foreach (var b in books) c += b.T.position; c /= books.Count;
            var want = Vector3.ProjectOnPlane(c - Head.position, Vector3.up); var have = Vector3.ProjectOnPlane(Head.forward, Vector3.up);
            if (want.sqrMagnitude < 1e-4f || have.sqrMagnitude < 1e-4f) return;
            rig.RotateAround(Head.position, Vector3.up, Vector3.SignedAngle(have, want, Vector3.up));
        }

        static IEnumerable<Vector3> Corners(Bounds b)
        {
            for (int i = 0; i < 8; i++) yield return b.center + Vector3.Scale(b.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
        }

        /// A small cream card clipped to the front edge of the ledge under the book, tilted back towards the reader, like
        /// a library shelf label: the chapter reached on the first line, its name and how far through the book on the second.
        TextMeshPro MakeLabel(Shelved b)
        {
            var go = new GameObject("ProgressCard." + b.Slug);
            go.transform.SetParent(Env, true);
            go.transform.position = b.T.position + b.Out * 0.30f + Vector3.up * 0.012f;   // clipped to the ledge's front edge (the book's pivot is the middle of its bottom edge)
            go.transform.rotation = Quaternion.LookRotation(-b.Out, Vector3.up) * Quaternion.Euler(40f, 0, 0);   // tilted back, readable from standing height
            var card = GameObject.CreatePrimitive(PrimitiveType.Quad); card.name = "Card"; Destroy(card.GetComponent<Collider>());
            card.transform.SetParent(go.transform, false); card.transform.localPosition = new Vector3(0, 0, 0.001f); card.transform.localScale = new Vector3(0.33f, 0.074f, 1);
            card.transform.localRotation = Quaternion.identity;
            b.CardMat = new Material(Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color")) { color = CardDim };
            card.GetComponent<Renderer>().sharedMaterial = b.CardMat; card.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            var t = new GameObject("Text").AddComponent<TextMeshPro>(); t.transform.SetParent(go.transform, false);
            if (Font) t.font = Font;
            t.rectTransform.sizeDelta = new Vector2(0.31f, 0.068f);
            t.enableAutoSizing = true; t.fontSizeMin = 0.12f; t.fontSizeMax = 0.2f; t.alignment = TextAlignmentOptions.Center; t.color = Ink; t.textWrappingMode = TextWrappingModes.NoWrap; t.overflowMode = TextOverflowModes.Ellipsis;
            t.lineSpacing = -8f; t.text = "";
            return t;
        }

        /// "Chapter II\nThe Pool of Tears · 9%" for a book in progress, "not opened yet" otherwise.
        public string ProgressLine(string slug)
        {
            var p = ProgressStore.LoadBook(slug);
            var at = p != null ? p.SentenceId : null;
            var e = index?.Books.Find(x => x.Slug == slug);
            if (string.IsNullOrEmpty(at)) return "<b>not opened yet</b>";
            if (e == null) return "in progress";
            var chId = at.Contains('.') ? at.Substring(0, at.IndexOf('.')) : at;
            var ch = e.Chapters.Find(c => c.Id == chId);
            if (ch == null) return "in progress";
            float para = 0; var parts = at.Split('.');
            if (parts.Length > 1 && parts[1].StartsWith("p") && int.TryParse(parts[1].Substring(1), out var pn) && ch.Paragraphs > 0) para = Mathf.Clamp01((pn - 1f) / ch.Paragraphs);
            int pct = e.Sentences > 0 ? Mathf.Clamp(Mathf.RoundToInt(100f * (ch.First + ch.Sentences * para) / e.Sentences), 0, 100) : 0;
            var how = pct < 1 ? "just begun" : pct + "% read";
            return string.IsNullOrEmpty(ch.Name) ? $"<b>{ch.Heading}</b>\n{how}" : $"<b>{ch.Heading}</b>\n{ch.Name} \u00b7 {how}";
        }

        void RefreshLabels() { foreach (var b in books) if (b.Label) b.Label.text = ProgressLine(b.Slug); }

        void MakeRay()
        {
            rayMat = new Material(Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color")) { color = RayColour };
            var lg = new GameObject("LobbyRay"); lg.transform.SetParent(transform, false);
            ray = lg.AddComponent<LineRenderer>(); ray.material = rayMat; ray.positionCount = 2; ray.useWorldSpace = true; ray.widthMultiplier = 0.005f; ray.numCapVertices = 2;
            ray.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; ray.receiveShadows = false; ray.enabled = false;
            var d = GameObject.CreatePrimitive(PrimitiveType.Sphere); d.name = "LobbyRayDot"; Destroy(d.GetComponent<Collider>());
            d.GetComponent<Renderer>().sharedMaterial = rayMat; d.transform.localScale = Vector3.one * 0.018f; dot = d.transform; d.SetActive(false);
        }

        bool PointRay(bool right, out Ray r)
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

        Shelved Hit(Ray r, out Vector3 point)
        {
            point = r.GetPoint(MaxRay); Shelved best = null; float bestD = MaxRay;
            foreach (var b in books)
                if (b.Box.Raycast(r, out var h, bestD)) { bestD = h.distance; point = h.point; best = b; }
            return best;
        }

        void Update()
        {
            if (opening) return;
            Shelved over = null; bool shown = false;
            foreach (var right in new[] { true, false })
            {
                if (!PointRay(right, out var r)) continue;
                if (View && View.RayOnBar(right)) continue;   // the toolbar draws its own ray
                if (Board && Board.OnBoard(right, out var bp)) { ray.enabled = true; ray.SetPosition(0, r.origin + r.direction * 0.05f); ray.SetPosition(1, bp); dot.gameObject.SetActive(true); dot.position = bp; shown = true; break; }
                var h = Hit(r, out var p);
                if (h != null || !shown)
                {
                    shown = true;
                    ray.enabled = true; ray.SetPosition(0, r.origin + r.direction * 0.05f); ray.SetPosition(1, p);
                    dot.gameObject.SetActive(h != null); dot.position = p;
                }
                if (h != null) { over = h; break; }
            }
            if (!shown) { ray.enabled = false; dot.gameObject.SetActive(false); }
            hovered = over;
            foreach (var b in books)
            {
                b.Hover = Mathf.MoveTowards(b.Hover, b == hovered ? 1f : 0f, Time.deltaTime * 6f);
                var e = b.Hover * b.Hover * (3 - 2 * b.Hover);
                b.T.localPosition = b.Home + (b.T.parent ? b.T.parent.InverseTransformVector(b.Out) : b.Out) * (SlideMetres * e);
                if (b.CardMat) b.CardMat.color = Color.Lerp(CardDim, CardLit, e);
            }
        }

        void OnPinch(bool right)
        {
            if (opening || hovered == null) return;
            // the pinch must be from a hand that is pointing at the book (either hand may hover, either may open)
            if (!PointRay(right, out var r) || Hit(r, out _) != hovered) return;
            if (Board) Board.ShowBookMenu(hovered.Slug); else Open(hovered.Slug);   // the book's menu first, then a room
        }

        /// Open a book: it leaves the shelf towards the reader, then its reading scene loads with it on the page.
        public void Open(string slug, string scene = null)
        {
            if (opening) return;
            if (Library.IsImported(slug)) { StartCoroutine(OpenImported(slug)); return; }
            var b = books.Find(x => x.Slug == slug);
            if (b == null || (scene == null && !ReadingScene.TryGetValue(slug, out scene))) { Debug.LogWarning($"[Fable] lobby: no book {slug}"); return; }
            StartCoroutine(OpenRoutine(b, scene));
        }

        IEnumerator OpenRoutine(Shelved b, string scene)
        {
            opening = true; ray.enabled = false; dot.gameObject.SetActive(false);
            Debug.Log($"[Fable] lobby: opening {b.Slug} in {scene}"); OpenedAt = Time.realtimeSinceStartup;
            FlowController.PendingBook = b.Slug;
            if (!Application.CanStreamedLevelBeLoaded(scene)) { Debug.LogWarning($"[Fable] lobby: {scene} is not in the build; reading {b.Slug} in {FallbackScene}"); scene = FallbackScene; }
            var load = Application.CanStreamedLevelBeLoaded(scene) ? SceneManager.LoadSceneAsync(scene) : null;
            if (load != null) load.allowSceneActivation = false;
            // the book comes off the shelf and up in front of the eyes, opening a little as it comes
            Vector3 from = b.T.position; Quaternion rotFrom = b.T.rotation;
            var head = Head ? Head : (Camera.main ? Camera.main.transform : null);
            Vector3 fwd = head ? Vector3.ProjectOnPlane(head.forward, Vector3.up).normalized : -b.Out;
            if (fwd.sqrMagnitude < 0.01f) fwd = -b.Out;
            Vector3 to = head ? head.position + fwd * 0.55f + Vector3.down * 0.42f : from + b.Out * 0.6f;
            Quaternion rotTo = Quaternion.FromToRotation(b.CoverNormal, -fwd) * rotFrom;   // cover upright, facing the reader
            for (float t = 0; t < 1f; t += Time.deltaTime / 0.7f)
            {
                float e = t * t * (3 - 2 * t);
                b.T.position = Vector3.Lerp(from, to, e) + Vector3.up * Mathf.Sin(e * Mathf.PI) * 0.08f;
                b.T.rotation = Quaternion.Slerp(rotFrom, rotTo, e);
                yield return null;
            }
            if (load == null) { Debug.LogError($"[Fable] lobby: scene {scene} is not in the build"); opening = false; b.T.SetPositionAndRotation(from, rotFrom); yield break; }
            while (load.progress < 0.9f) yield return null;
            load.allowSceneActivation = true;
        }

        /// One of the reader's own books: no shelf to fly from, so the board gives way and the library room loads with it on the page.
        IEnumerator OpenImported(string slug)
        {
            opening = true; ray.enabled = false; dot.gameObject.SetActive(false);
            var scene = Application.CanStreamedLevelBeLoaded(ImportedScene) ? ImportedScene : FallbackScene;
            Debug.Log($"[Fable] lobby: opening {slug} (imported) in {scene}"); OpenedAt = Time.realtimeSinceStartup;
            FlowController.PendingBook = slug;
            var load = SceneManager.LoadSceneAsync(scene); load.allowSceneActivation = false;
            if (Board) for (float t = 0; t < 0.35f; t += Time.deltaTime) { Board.Root.localScale = Vector3.one * 0.001f * (1f - t / 0.35f * 0.4f); yield return null; }
            while (load.progress < 0.9f) yield return null;
            load.allowSceneActivation = true;
        }

        /// Test hook: point the right-hand ray from the eyes at a book (or clear it with null).
        public void AimAt(string slug)
        {
            var b = books.Find(x => x.Slug == slug); var cam = Camera.main;
            TestRay = b != null && cam ? new Ray(cam.transform.position, (b.T.TransformPoint(b.Box.center) - cam.transform.position).normalized) : null;
        }

        public string Describe() => $"lobby books={books.Count} hovered={Hovered ?? "-"} opening={opening} " + string.Join(" | ", books.ConvertAll(b => $"{b.Slug}: {(b.Label ? b.Label.text.Replace("\n", " / ") : "")}"));
    }
}
