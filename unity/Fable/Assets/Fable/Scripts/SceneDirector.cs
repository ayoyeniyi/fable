// Executes validated SceneScripts beat by beat. Going back replays from the start instantly, so the
// room is always a pure function of the beat index: no drift, no stuck state.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;

namespace Fable
{
    public class SceneDirector : MonoBehaviour
    {
        public SceneRegistry Registry;
        public ClipPlayer Clips;
        public SpatialAudio Audio;
        public Transform ReaderHead;          // centre eye
        [Tooltip("Optional interpreter URL, e.g. http://192.168.1.20:8787. Empty = bundled baseline only.")]
        public string InterpreterUrl = "";

        public SceneScript Script { get; private set; }
        public Passage.Scene PassageScene { get; private set; }
        public int BeatIndex { get; private set; } = -1;
        public event Action<int, Beat> BeatChanged;

        readonly Dictionary<string, Vector3> assetHome = new();
        readonly Dictionary<string, Quaternion> assetHomeRot = new();
        readonly Dictionary<string, Vector3> assetHomeScale = new();
        readonly Dictionary<string, float> lightHome = new();
        Coroutine scaleRoutine;
        float baseScale = 1f;   // the room's scale before any readerScale action (1 immersive, ~0.09 miniature)

        public IEnumerator Load(string sceneId, Passage book)
        {
            PassageScene = book.Scenes.First(s => s.Id == sceneId);
            var manifest = JsonConvert.DeserializeObject<SceneManifest>(ReadStreaming($"scripts/manifest.{sceneId}.json"));
            var ids = PassageScene.Sentences().Select(s => s.Id).ToList();
            SceneScript candidate = null;
            if (!string.IsNullOrEmpty(InterpreterUrl))
            {
                using var req = new UnityWebRequest(InterpreterUrl.TrimEnd('/') + "/interpret", "POST");
                req.uploadHandler = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes($"{{\"sceneId\":\"{sceneId}\"}}"));
                req.downloadHandler = new DownloadHandlerBuffer(); req.SetRequestHeader("Content-Type", "application/json"); req.timeout = 120;
                yield return req.SendWebRequest();
                if (req.result == UnityWebRequest.Result.Success)
                {
                    try { candidate = ScriptValidator.Parse(req.downloadHandler.text); }
                    catch (Exception e) { Debug.LogWarning($"[Fable] interpreter JSON rejected: {e.Message}"); }
                    if (candidate != null)
                    {
                        var errs = ScriptValidator.Validate(candidate, manifest, ids);
                        if (errs.Count > 0) { Debug.LogWarning("[Fable] interpreter script failed validation:\n" + string.Join("\n", errs)); candidate = null; }
                        else Debug.Log("[Fable] using interpreter script");
                    }
                }
                else Debug.LogWarning($"[Fable] interpreter unreachable: {req.error}");
            }
            if (candidate != null) ProgressStore.CacheScript(sceneId, JsonConvert.SerializeObject(candidate));
            if (candidate == null)
            {
                var cached = ProgressStore.LoadCachedScript(sceneId);
                if (cached != null)
                {
                    try { var cs = ScriptValidator.Parse(cached); if (ScriptValidator.Validate(cs, manifest, ids).Count == 0) { candidate = cs; Debug.Log("[Fable] using cached interpreter script"); } }
                    catch (Exception e) { Debug.LogWarning($"[Fable] cache unreadable: {e.Message}"); }
                }
            }
            if (candidate == null)
            {
                candidate = ScriptValidator.Parse(ReadStreaming($"scripts/{sceneId}.baseline.json"));
                var errs = ScriptValidator.Validate(candidate, manifest, ids);
                if (errs.Count > 0) throw new Exception("baseline script invalid:\n" + string.Join("\n", errs));
                Debug.Log("[Fable] using bundled baseline script");
            }
            Script = candidate;
            if (Clips) Clips.Init(Registry);
            if (Audio) Audio.Init(Registry);
            CaptureHomes();
            ResetRoom();
        }

        static string ReadStreaming(string rel)
        {
            var path = Path.Combine(Application.streamingAssetsPath, rel);
#if UNITY_ANDROID && !UNITY_EDITOR
            using var req = UnityWebRequest.Get(path); req.SendWebRequest();
            while (!req.isDone) { }
            return req.downloadHandler.text;
#else
            return File.ReadAllText(path);
#endif
        }

        void CaptureHomes()
        {
            foreach (var id in Registry.AssetIds)
            {
                var t = Registry.Asset(id);
                assetHome[id] = t.localPosition; assetHomeRot[id] = t.localRotation; assetHomeScale[id] = t.localScale;
            }
            foreach (var g in new[] { "lamp.row", "light.garden", "light.fill" })
            {
                var ls = Registry.Lights(g); if (ls == null) continue;
                foreach (var l in ls) lightHome[l.name] = l.intensity;
            }
        }

        /// Everything the script can place starts hidden; the environment shell itself is always there.
        public void ResetRoom()
        {
            Clips.StopAll();
            foreach (var id in Registry.AssetIds)
            {
                var t = Registry.Asset(id);
                t.localPosition = assetHome[id]; t.localRotation = assetHomeRot[id]; t.localScale = assetHomeScale[id];
                t.gameObject.SetActive(false);
            }
            foreach (var kv in lightHome) { }
            var garden = Registry.Lights("light.garden"); if (garden != null) foreach (var l in garden) l.intensity = 0;
            var lamps = Registry.Lights("lamp.row"); if (lamps != null) foreach (var l in lamps) l.intensity = lightHome[l.name] * 0.2f;
            baseScale = Registry.EnvironmentRoot.localScale.x;
            BeatIndex = -1;
        }

        public bool Next()
        {
            if (Script == null || BeatIndex + 1 >= Script.Beats.Count) return false;
            BeatIndex++;
            Apply(Script.Beats[BeatIndex], instant: false);
            BeatChanged?.Invoke(BeatIndex, Script.Beats[BeatIndex]);
            return true;
        }

        /// Jump straight to a beat (resume): everything before it instant, the beat itself animated.
        public void JumpTo(int index)
        {
            if (Script == null) return;
            index = Mathf.Clamp(index, 0, Script.Beats.Count - 1);
            ResetRoom();
            for (int i = 0; i <= index; i++) Apply(Script.Beats[i], instant: i < index);
            BeatIndex = index;
            BeatChanged?.Invoke(BeatIndex, Script.Beats[BeatIndex]);
        }

        public bool Previous()
        {
            if (Script == null || BeatIndex <= 0) return false;
            int target = BeatIndex - 1;
            ResetRoom();
            for (int i = 0; i <= target; i++) Apply(Script.Beats[i], instant: i < target);
            BeatIndex = target;
            BeatChanged?.Invoke(BeatIndex, Script.Beats[BeatIndex]);
            return true;
        }

        void Apply(Beat b, bool instant)
        {
            foreach (var a in b.Actions)
            {
                switch (a.Type)
                {
                    case "place": Place(a, instant); break;
                    case "move": Move(a, instant); break;
                    case "remove": Remove(a, instant); break;
                    case "animate":
                        if (instant) Clips.Play(a.Target, a.Clip, 0.01f, false);
                        else Clips.Play(a.Target, a.Clip, a.DurationSeconds ?? 1.5f, a.Loop ?? false);
                        break;
                    case "light": StartCoroutine(FadeLights(a, instant ? 0 : a.DurationSeconds ?? 1f)); break;
                    case "sound": if (!instant) Audio.Play(a.Sound, a.Anchor, a.Volume ?? 0.8f); break;
                    case "readerScale": ReaderScale(a.Scale ?? 1f, a.Anchor, instant ? 0 : a.DurationSeconds ?? 5f); break;
                }
            }
        }

        void Place(ScriptAction a, bool instant)
        {
            var t = Registry.Asset(a.Asset); var anchor = Registry.Anchor(a.Anchor);
            if (!t || !anchor) return;
            // Props exported from Blender already sit where the text puts them; an anchor other than their
            // home moves them there, keeping the authored offset inside the group.
            var pos = anchor.position;
            if (a.Offset != null) pos += anchor.TransformVector(new Vector3(a.Offset[0], a.Offset[1], a.Offset[2]));
            bool atHome = a.Anchor == DefaultAnchorFor(a.Asset);
            if (!atHome) t.position = pos;
            if (a.YawDegrees != null) t.rotation = Quaternion.Euler(0, a.YawDegrees.Value, 0) * t.rotation;
            var scale = assetHomeScale[a.Asset] * (a.Scale ?? 1f);
            t.gameObject.SetActive(true);
            if (instant || a.Appear == "instant") { t.localScale = scale; SetAlpha(t, 1); return; }
            StartCoroutine(Appear(t, scale, a.Appear ?? "fade"));
        }

        static string DefaultAnchorFor(string asset) => asset switch
        {
            "prop.golden-key" => "table.top", "prop.drink-me-bottle" => "table.top", "prop.glass-table" => "hall.centre",
            "prop.curtain" => "curtain.front", "fx.garden-glow" => "door.little", "door.little" => "door.little", _ => ""
        };

        IEnumerator Appear(Transform t, Vector3 scale, string mode)
        {
            float dur = mode == "settle" ? 0.9f : 1.2f;
            var start = mode == "grow" ? scale * 0.05f : scale;
            for (float e = 0; e < dur; e += Time.deltaTime)
            {
                float x = Mathf.SmoothStep(0, 1, e / dur);
                if (mode == "grow") t.localScale = Vector3.Lerp(start, scale, x);
                if (mode == "settle") t.localPosition += Vector3.down * (0.0004f * Mathf.Sin(x * Mathf.PI));
                SetAlpha(t, mode == "fade" ? x : 1);
                yield return null;
            }
            t.localScale = scale; SetAlpha(t, 1);
        }

        void Move(ScriptAction a, bool instant)
        {
            var t = Registry.Asset(a.Asset); var anchor = Registry.Anchor(a.Anchor); if (!t || !anchor) return;
            var target = anchor.position;
            if (a.Offset != null) target += anchor.TransformVector(new Vector3(a.Offset[0], a.Offset[1], a.Offset[2]));
            if (instant) { t.position = target; return; }
            StartCoroutine(Glide(t, target, a.DurationSeconds ?? 1.5f, a.Ease ?? "smooth"));
        }

        IEnumerator Glide(Transform t, Vector3 to, float dur, string ease)
        {
            var from = t.position;
            for (float e = 0; e < dur; e += Time.deltaTime)
            {
                float x = e / dur;
                x = ease == "linear" ? x : ease == "settle" ? 1 - Mathf.Pow(1 - x, 3) : Mathf.SmoothStep(0, 1, x);
                t.position = Vector3.Lerp(from, to, x); yield return null;
            }
            t.position = to;
        }

        void Remove(ScriptAction a, bool instant)
        {
            var t = Registry.Asset(a.Asset); if (!t) return;
            if (instant || a.Vanish == "instant") { t.gameObject.SetActive(false); return; }
            StartCoroutine(Vanish(t, a.Vanish ?? "fade"));
        }

        IEnumerator Vanish(Transform t, string mode)
        {
            var s = t.localScale;
            for (float e = 0; e < 0.8f; e += Time.deltaTime)
            {
                float x = e / 0.8f;
                if (mode == "shrink") t.localScale = s * (1 - x);
                SetAlpha(t, 1 - x); yield return null;
            }
            t.gameObject.SetActive(false); t.localScale = s; SetAlpha(t, 1);
        }

        static void SetAlpha(Transform t, float a)
        {
            // URP Lit materials from glTFast are opaque; we drive a global fade property the FableFade shader
            // keyword reads. Opaque props snap at 50 percent, which reads as "settling in" at VR frame rates.
            foreach (var r in t.GetComponentsInChildren<Renderer>()) r.enabled = a > 0.5f || a >= 1f;
        }

        IEnumerator FadeLights(ScriptAction a, float dur)
        {
            var ls = Registry.Lights(a.Light); if (ls == null) yield break;
            var from = ls.Select(l => l.intensity).ToList();
            var to = ls.Select(l => lightHome.GetValueOrDefault(l.name, l.intensity) * (a.Intensity ?? 1f)).ToList();
            Color? col = a.Kelvin != null ? Mathf.CorrelatedColorTemperatureToRGB(a.Kelvin.Value) : null;
            if (dur <= 0) { for (int i = 0; i < ls.Count; i++) { ls[i].intensity = to[i]; if (col != null) ls[i].color = col.Value; } yield break; }
            for (float e = 0; e < dur; e += Time.deltaTime)
            {
                float x = Mathf.SmoothStep(0, 1, e / dur);
                for (int i = 0; i < ls.Count; i++) { ls[i].intensity = Mathf.Lerp(from[i], to[i], x); if (col != null) ls[i].color = Color.Lerp(ls[i].color, col.Value, x); }
                yield return null;
            }
        }

        /// Scaling the world up around the reader's feet is how Alice shrinks. The pivot is the floor point
        /// under the head so the floor never moves under the reader; vection is kept gentle by the long duration.
        void ReaderScale(float worldScale, string anchorId, float dur)
        {
            if (scaleRoutine != null) StopCoroutine(scaleRoutine);
            scaleRoutine = StartCoroutine(ScaleRoutine(worldScale, dur));
        }

        IEnumerator ScaleRoutine(float target, float dur)
        {
            var root = Registry.EnvironmentRoot;
            var pivot = ReaderHead ? new Vector3(ReaderHead.position.x, root.position.y, ReaderHead.position.z) : root.position;
            float from = root.localScale.x; target *= baseScale;
            if (Mathf.Abs(baseScale - 1f) > 0.01f) pivot = root.TransformPoint(Registry.Anchor("hall.centre") ? root.InverseTransformPoint(Registry.Anchor("hall.centre").position) : Vector3.zero);
            for (float e = 0; e < dur; e += Time.deltaTime)
            {
                float s = Mathf.Lerp(from, target, Mathf.SmoothStep(0, 1, e / Mathf.Max(dur, 0.001f)));
                ScaleAbout(root, pivot, s); yield return null;
            }
            ScaleAbout(root, pivot, target);
        }

        static void ScaleAbout(Transform t, Vector3 pivot, float s)
        {
            var prev = t.localScale.x; if (Mathf.Approximately(prev, 0)) prev = 1;
            var dir = t.position - pivot;
            t.position = pivot + dir * (s / prev);
            t.localScale = Vector3.one * s;
        }
    }
}
