// Reading -> Miniature -> Scene -> back. The room first appears as a diorama on the reading table,
// then grows around the reader. Closing returns to the page at the sentence the reader reached.
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using UnityEngine;

namespace Fable
{
    public class FlowController : MonoBehaviour
    {
        public enum State { Reading, Growing, Miniature, Expanding, Scene, Shrinking, Returning }
        public State Current { get; private set; } = State.Reading;

        public SceneDirector Director;
        public ReaderController Input;
        public ReadingPanel Panel;
        public Transform Head;
        public GameObject ReadingRoom;          // the quiet void with the page (soft light, dark floor disc)
        public string SceneId = "hall-of-doors";
        public float MiniatureScale = 0.09f;    // the 14 m hall becomes a 1.3 m diorama
        public float GrowSeconds = 1.8f, ExpandSeconds = 3.2f;
        /// Diorama placement from the eye: about 43 degrees down, so the reader looks into the dollhouse over its near wall.
        public float DioramaForward = 0.75f, DioramaDrop = 0.7f;

        Passage book;
        Transform env;
        Vector3 miniaturePivot;
        bool busy;

        // passage picker: every passage of the book whose Unity scene is in the build
        public static readonly Dictionary<string, string> UnityScenes = new()
        {
            ["hall-of-doors"] = "HallOfDoors", ["mad-tea-party"] = "MadTeaParty", ["queens-croquet-ground"] = "QueensCroquetGround"
        };
        static readonly Dictionary<string, string> Places = new()
        {
            ["hall-of-doors"] = "the hall", ["mad-tea-party"] = "the tea-party", ["queens-croquet-ground"] = "the rose garden"
        };
        /// set before loading another passage's scene so it opens straight into the miniature
        static bool openOnLoad;
        List<Passage.Scene> passages = new();
        int chosen;
        Passage.Scene Chosen => passages.Count > 0 ? passages[chosen] : Director.PassageScene;
        string Place(string id) => Places.TryGetValue(id, out var p) ? p : "the scene";

        /// Sky dome and distant scenery: shown only at full scale (a 45 m dome at diorama scale would still enclose the reader).
        public static bool IsBackdrop(string n) => n.Contains("SkyDome") || n.Contains("Sky_Dome") || n.StartsWith("far.") || n.Contains("Distant") || n.Contains("TreeLine") || n.Contains("Treeline") || n.Contains("FarTrees");
        /// The dollhouse cut: what roofs the scene over (the hall's ceiling, the tea-party tree's canopy) is lifted off
        /// while it sits on the table as a diorama, so the reader looks down into it rather than at its top.
        public static bool IsMiniatureCut(string n) => n == "MESH_Ceiling" || n == "MESH_Leaves";
        readonly List<Renderer> backdrop = new(), roof = new();
        GameObject plinth;   // outdoor diorama base: a lawn disc standing in for ground that would overhang the table
        void ShowBackdrop(bool on)
        {
            foreach (var r in backdrop) if (r) r.enabled = on;
            foreach (var r in roof) if (r) r.enabled = on;
            if (plinth) plinth.SetActive(!on);
        }

        /// Anything wider than this (metres at full scale) would hang off the 1.5 m diorama table at MiniatureScale:
        /// outdoor lawns, hedge rings, tree belts. It is cut from the diorama, which stands on a lawn plinth instead.
        const float DioramaReach = 16f;

        void PrepareDiorama()
        {
            Renderer ground = null; float groundArea = 0;
            foreach (var r in env.GetComponentsInChildren<Renderer>(true))
            {
                if (IsBackdrop(r.name)) { backdrop.Add(r); continue; }
                if (IsMiniatureCut(r.name)) { roof.Add(r); continue; }
                if (SceneRegistry.IsAssetName(r.name) || (r.transform.parent && SceneRegistry.IsAssetName(r.transform.parent.name))) continue;
                var s = r.bounds.size;
                if (Mathf.Max(s.x, s.z) <= DioramaReach) continue;
                roof.Add(r);
                if (s.y < 1.5f && s.x * s.z > groundArea) { ground = r; groundArea = s.x * s.z; }
            }
            if (ground) plinth = MakePlinth(ground);
        }

        GameObject MakePlinth(Renderer ground)
        {
            const int seg = 48; float radius = DioramaReach * 0.5f;
            var centre = Director.Registry.Centre; var gb = ground.bounds;
            var go = new GameObject("DioramaPlinth"); go.transform.SetParent(env, false);
            go.transform.position = new Vector3(centre.position.x, gb.max.y + 0.01f, centre.position.z);
            var v = new Vector3[seg + 1]; var uv = new Vector2[seg + 1]; var tri = new int[seg * 3];
            v[0] = Vector3.zero;
            for (int i = 0; i < seg; i++) { float a = i * Mathf.PI * 2 / seg; v[i + 1] = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a)) * radius; }
            for (int i = 0; i <= seg; i++) uv[i] = new Vector2(v[i].x, v[i].z) / (radius * 2) + new Vector2(0.5f, 0.5f);
            for (int i = 0; i < seg; i++) { tri[i * 3] = 0; tri[i * 3 + 1] = (i + 1) % seg + 1; tri[i * 3 + 2] = i + 1; }
            var mesh = new Mesh { name = "DioramaPlinth", vertices = v, uv = uv, triangles = tri }; mesh.RecalculateNormals(); mesh.RecalculateBounds();
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            // the lawn's baked texture is an atlas with its own unwrap, so the plinth takes the lawn's average colour instead
            var mat = new Material(ground.sharedMaterial.shader) { name = "DioramaPlinth" };
            mat.CopyPropertiesFromMaterial(ground.sharedMaterial);
            foreach (var n in mat.GetTexturePropertyNames()) mat.SetTexture(n, null);
            var gm = ground.sharedMaterial; var avg = AverageColour(gm.HasProperty("baseColorTexture") ? gm.GetTexture("baseColorTexture") : gm.HasProperty("_BaseMap") ? gm.GetTexture("_BaseMap") : gm.mainTexture);
            foreach (var n in new[] { "_BaseColor", "baseColorFactor", "_Color" }) if (mat.HasProperty(n)) mat.SetColor(n, avg);
            var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = mat; mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            go.SetActive(false);
            return go;
        }

        /// Mean colour of a (non-readable, compressed) texture: a 16x16 GPU downsample, ignoring empty atlas space.
        static Color AverageColour(Texture tex)
        {
            if (!tex) return new Color(0.32f, 0.46f, 0.2f);
            var rt = RenderTexture.GetTemporary(16, 16, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            Graphics.Blit(tex, rt);
            var prev = RenderTexture.active; RenderTexture.active = rt;
            var small = new Texture2D(16, 16, TextureFormat.RGBA32, false); small.ReadPixels(new Rect(0, 0, 16, 16), 0, 0); small.Apply();
            RenderTexture.active = prev; RenderTexture.ReleaseTemporary(rt);
            Color sum = Color.black; int n = 0;
            foreach (var c in small.GetPixels()) if (c.grayscale > 0.06f) { sum += c; n++; }
            Destroy(small);
            return n > 0 ? sum / n : new Color(0.32f, 0.46f, 0.2f);
        }

        /// The diorama table follows the diorama: its top always meets the diorama floor, whatever the reader's height.
        void PlaceDioramaTable(Vector3 floorPoint)
        {
            var table = ReadingRoom ? ReadingRoom.transform.Find("DioramaTable") : null; if (!table) return;
            float floorY = ReadingRoom.transform.position.y;   // the reading room sits on the real floor
            float h = Mathf.Max(0.2f, floorPoint.y - floorY - 0.005f);
            table.position = new Vector3(floorPoint.x, floorY + h / 2, floorPoint.z);
            table.localScale = new Vector3(table.localScale.x, h / 2, table.localScale.z);
        }

        // reading panel placements: on its own, beside the diorama (to the left, out of the line of sight), and inside the scene
        void PanelAlone() { Panel.Distance = 1.15f; Panel.Height = -0.08f; Panel.Side = 0f; Panel.Scale = 1f; }
        void PanelBesideDiorama() { Panel.Distance = 0.95f; Panel.Height = -0.12f; Panel.Side = -0.62f; Panel.Scale = 0.6f; }
        void PanelInScene() { Panel.Distance = 0.9f; Panel.Height = -0.32f; Panel.Side = 0f; Panel.Scale = 0.55f; }

        IEnumerator Start()
        {
            // StreamingAssets live inside the APK on Android, so a plain file read throws there; fetch through UnityWebRequest instead.
            var bookPath = System.IO.Path.Combine(Application.streamingAssetsPath, "book/passages.json");
            string bookJson;
#if UNITY_ANDROID && !UNITY_EDITOR
            // Quest: shade the periphery at lower density; the page sits in the centre of view where density stays full.
            OVRManager.foveatedRenderingLevel = OVRManager.FoveatedRenderingLevel.Medium;
            OVRManager.useDynamicFoveatedRendering = true;
            using (var req = UnityEngine.Networking.UnityWebRequest.Get(bookPath))
            {
                yield return req.SendWebRequest();
                if (req.result != UnityEngine.Networking.UnityWebRequest.Result.Success) { Debug.LogError($"[Fable] book missing from StreamingAssets: {req.error}"); yield break; }
                bookJson = req.downloadHandler.text;
            }
#else
            bookJson = System.IO.File.ReadAllText(bookPath);
#endif
            book = JsonConvert.DeserializeObject<Passage>(bookJson);
            env = Director.Registry.EnvironmentRoot;
            if (!UnityEngine.XR.XRSettings.isDeviceActive && Head && Head.localPosition.y < 0.5f) Head.localPosition = new Vector3(0, 1.25f, 0);
            Director.Flow = this; Director.Panel = Panel; Director.Reader = Input;
            yield return Director.Load(SceneId, book);
            env.gameObject.SetActive(false);
            env.gameObject.SetActive(true); PrepareDiorama(); env.gameObject.SetActive(false);
            passages = book.Scenes.Where(p => p.Id == SceneId || (UnityScenes.TryGetValue(p.Id, out var n) && Application.CanStreamedLevelBeLoaded(n))).ToList();
            Input.Select += OnSelect; Input.Next += OnNext; Input.Previous += OnPrev; Input.ReturnToReading += OnReturn; Input.ToggleView += OnToggle; Input.Scrub += OnScrub;
            Director.BeatChanged += (i, b) =>
            {
                Panel.Show(Director.PassageScene, b.SentenceId, Hint());
                ProgressStore.Save(SceneId, i, b.SentenceId);
            };
            // the picker starts on the passage read last (the APK always boots into the hall's scene)
            var last = ProgressStore.LastSceneId();
            chosen = Mathf.Max(0, passages.FindIndex(p => p.Id == (openOnLoad || last == null ? SceneId : last)));
            if (chosen < 0 || chosen >= passages.Count) chosen = Mathf.Max(0, passages.FindIndex(p => p.Id == SceneId));
            if (openOnLoad) { openOnLoad = false; StartCoroutine(Grow()); }
            else ShowPicker(welcome: true);
        }

        /// The reading page in its quiet state: the chosen passage, where the reader left it, and how to choose another.
        void ShowPicker(bool welcome = false)
        {
            var p = Chosen; var saved = ProgressStore.Load(p.Id);
            string pick = passages.Count > 1 ? $"\u2039 {chosen + 1} of {passages.Count} \u203a   drag or tap left for another passage.   " : "";
            string open = saved.SentenceId != null ? (welcome ? $"welcome back. pinch to open {Place(p.Id)} where you left it" : $"pinch to open {Place(p.Id)} where you left it") : $"pinch to open {Place(p.Id)}";
            string source = p.Id == SceneId && Director.ScriptSource != "" ? $"   (scene: {Director.ScriptSource})" : "";
            Panel.Show(p, saved.SentenceId, pick + open + source);
        }

        void ChoosePassage(int dir)
        {
            if (passages.Count < 2) return;
            chosen = (chosen + dir + passages.Count) % passages.Count;
            ShowPicker();
        }

        void OpenChosen()
        {
            if (Chosen.Id == SceneId) { StartCoroutine(Grow()); return; }
            busy = true; openOnLoad = true;
            Director.Audio.StopAmbience();
            UnityEngine.SceneManagement.SceneManager.LoadScene(UnityScenes[Chosen.Id]);
        }

        string Hint() => Current == State.Scene
            ? $"{Director.BeatIndex + 1} / {Director.Script.Beats.Count}   tap right to continue, left to go back, drag to scrub, both hands: miniature, hold: page"
            : $"{Director.BeatIndex + 1} / {Director.Script.Beats.Count}   tap right to continue, drag to scrub, both hands: step inside, hold: page";

        void OnSelect() { if (Current == State.Reading && !busy) OpenChosen(); }
        void OnNext() { if ((Current == State.Scene || Current == State.Miniature) && !busy && !Director.Next()) StartCoroutine(Current == State.Scene ? Shrink() : Return()); }
        void OnPrev()
        {
            if (busy) return;
            if (Current == State.Scene || Current == State.Miniature) Director.Previous();
            else if (Current == State.Reading) ChoosePassage(-1);
        }
        void OnScrub(int dir)
        {
            if (busy) return;
            if (Current == State.Scene || Current == State.Miniature) { if (dir > 0) Director.Next(); else Director.Previous(); }
            else if (Current == State.Reading) ChoosePassage(dir);
        }
        void OnToggle()
        {
            if (busy) return;
            if (Current == State.Miniature) StartCoroutine(Expand());
            else if (Current == State.Scene) StartCoroutine(Shrink());
            else if (Current == State.Reading) OpenChosen();
        }
        void OnReturn() { if ((Current == State.Scene || Current == State.Miniature) && !busy) StartCoroutine(Return()); }

        /// Back to the passage at the current beat (after a held prop is put down, for instance).
        public void RefreshPanel()
        {
            if (Director.Script == null) return;
            var at = Director.BeatIndex >= 0 ? Director.Script.Beats[Director.BeatIndex].SentenceId : null;
            if (Current == State.Reading) { ShowPicker(); return; }
            Panel.Show(Director.PassageScene, at, Hint());
        }

        // test hooks: the same paths the hands take, callable from the editor CLI
        public void StepInto() => OnSelect();
        public void StepNext() => OnNext();
        public void StepBack() => OnPrev();
        public void StepToggle() => OnToggle();
        public void StepReturn() => OnReturn();
        public void StepChoose(int dir) => OnScrub(dir);
        public string ChosenId => Chosen?.Id;
        public string Describe() => $"state={Current} beat={Director.BeatIndex + 1}/{(Director.Script != null ? Director.Script.Beats.Count : 0)} envScale={(env != null ? env.localScale.x.ToString("F2") : "n/a")} active={(env != null && env.gameObject.activeSelf)} playing={Application.isPlaying} source={Director.ScriptSource}";

        /// The diorama grows out of the table in front of the reader; its hall centre sits at chest height, a little below the page.
        IEnumerator Grow()
        {
            busy = true; Current = State.Growing; Director.Immersive = false;
            Director.ResetRoom();
            var fwd = Vector3.ProjectOnPlane(Head.forward, Vector3.up).normalized; if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            var centre = Director.Registry.Centre;
            var target = Head.position + fwd * DioramaForward + Vector3.down * DioramaDrop;   // where the scene's centre point should sit, in world space
            env.localScale = Vector3.one * 0.001f;
            env.position = Vector3.zero;
            env.gameObject.SetActive(true); ShowBackdrop(false);
            // place so that the scaled hall centre lands on the target
            env.position = target - (centre.position - env.position);
            miniaturePivot = target; PlaceDioramaTable(target);
            PanelBesideDiorama();
            Director.Audio.PlayAmbience(Director.Script.Environment.Ambience, 0.25f);
            for (float e = 0; e < GrowSeconds; e += Time.deltaTime)
            {
                ScaleAbout(env, miniaturePivot, Mathf.Lerp(0.001f, MiniatureScale, Mathf.SmoothStep(0, 1, e / GrowSeconds)));
                yield return null;
            }
            ScaleAbout(env, miniaturePivot, MiniatureScale);
            Current = State.Miniature; busy = false;
            var saved = ProgressStore.Load(SceneId);
            if (saved.BeatIndex >= 0) Director.JumpTo(saved.BeatIndex); else Director.Next();
        }

        /// From diorama to full scale around the reader. The pivot moves from the table to the reader's feet so the floor arrives under them.
        IEnumerator Expand()
        {
            busy = true; Current = State.Expanding;
            ReadingRoom.SetActive(false);
            var feet = new Vector3(Head.position.x, 0f, Head.position.z);
            var standAnchor = Director.Registry.ReaderStand;
            // at full scale we want standAnchor under the reader: compute the final env position, then blend
            var startPos = env.position; var startScale = env.localScale.x;
            var endScale = Director.ReaderFactor;   // 1, or 4 once Alice has drunk
            var endPos = feet - (standAnchor.position - env.position) / startScale * endScale;
            PanelInScene();
            Director.Audio.PlayAmbience(Director.Script.Environment.Ambience, 0.6f);
            for (float e = 0; e < ExpandSeconds; e += Time.deltaTime)
            {
                float x = Mathf.SmoothStep(0, 1, e / ExpandSeconds);
                env.localScale = Vector3.one * Mathf.Lerp(startScale, endScale, x);
                env.position = Vector3.Lerp(startPos, endPos, x);
                yield return null;
            }
            env.localScale = Vector3.one * endScale; env.position = endPos; ShowBackdrop(true);   // ground, roof and sky return once the floor is under the reader
            Current = State.Scene; busy = false; Director.Immersive = true;
            Panel.Show(Director.PassageScene, Director.Script.Beats[Mathf.Max(0, Director.BeatIndex)].SentenceId, Hint());
        }

        /// Back to the diorama on the table.
        IEnumerator Shrink()
        {
            busy = true; Current = State.Shrinking; Director.Immersive = false; Director.StopScaling();
            ReadingRoom.SetActive(true);
            var fwd = Vector3.ProjectOnPlane(Head.forward, Vector3.up).normalized; if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            var target = Head.position + fwd * DioramaForward + Vector3.down * DioramaDrop;
            var centre = Director.Registry.Centre; ShowBackdrop(false);
            var startPos = env.position; var startScale = env.localScale.x;
            var endPos = target - (centre.position - env.position) / startScale * MiniatureScale;
            PanelBesideDiorama();
            Director.Audio.PlayAmbience(Director.Script.Environment.Ambience, 0.25f);
            for (float e = 0; e < ExpandSeconds; e += Time.deltaTime)
            {
                float x = Mathf.SmoothStep(0, 1, e / ExpandSeconds);
                env.localScale = Vector3.one * Mathf.Lerp(startScale, MiniatureScale, x);
                env.position = Vector3.Lerp(startPos, endPos, x);
                yield return null;
            }
            env.localScale = Vector3.one * MiniatureScale; env.position = endPos; miniaturePivot = target; PlaceDioramaTable(target);
            Current = State.Miniature; busy = false;
            Panel.Show(Director.PassageScene, Director.Script.Beats[Mathf.Max(0, Director.BeatIndex)].SentenceId, Hint());
        }

        /// Close: the room folds into the page; the page shows the sentence the reader reached.
        IEnumerator Return()
        {
            bool fromScene = Current == State.Scene;
            busy = true; Current = State.Returning; Director.Immersive = false; Director.StopScaling();
            ReadingRoom.SetActive(true);
            var pivot = fromScene ? new Vector3(Head.position.x, env.position.y, Head.position.z) : miniaturePivot;
            float from = env.localScale.x;
            for (float e = 0; e < GrowSeconds; e += Time.deltaTime)
            {
                float x = Mathf.SmoothStep(0, 1, e / GrowSeconds);
                ScaleAbout(env, pivot, Mathf.Lerp(from, 0.001f, x));
                Panel.Scale = Mathf.Lerp(0.6f, 1f, x);
                yield return null;
            }
            env.gameObject.SetActive(false);
            Director.Audio.StopAmbience();
            PanelAlone();
            Current = State.Reading; busy = false;
            chosen = Mathf.Max(0, passages.FindIndex(p => p.Id == SceneId));
            ShowPicker();
        }

        static void ScaleAbout(Transform t, Vector3 pivot, float s)
        {
            var prev = t.localScale.x; if (Mathf.Approximately(prev, 0)) prev = 1;
            t.position = pivot + (t.position - pivot) * (s / prev);
            t.localScale = Vector3.one * s;
        }
    }
}
