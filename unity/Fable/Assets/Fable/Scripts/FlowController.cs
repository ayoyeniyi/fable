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
        public static bool IsBackdrop(string n) => n.Contains("SkyDome") || n.Contains("Sky_Dome") || n.StartsWith("far.") || n.Contains("Distant") || n.Contains("TreeLine") || n.Contains("Treeline");
        readonly List<Renderer> backdrop = new();
        void ShowBackdrop(bool on) { foreach (var r in backdrop) if (r) r.enabled = on; }

        IEnumerator Start()
        {
            book = JsonConvert.DeserializeObject<Passage>(System.IO.File.ReadAllText(System.IO.Path.Combine(Application.streamingAssetsPath, "book/passages.json")));
            env = Director.Registry.EnvironmentRoot;
            if (!UnityEngine.XR.XRSettings.isDeviceActive && Head && Head.localPosition.y < 0.5f) Head.localPosition = new Vector3(0, 1.25f, 0);
            Director.Flow = this; Director.Panel = Panel; Director.Reader = Input;
            yield return Director.Load(SceneId, book);
            env.gameObject.SetActive(false);
            foreach (var r in env.GetComponentsInChildren<Renderer>(true)) if (IsBackdrop(r.name)) backdrop.Add(r);
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
            Panel.Show(p, saved.SentenceId, pick + open);
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
        public string Describe() => $"state={Current} beat={Director.BeatIndex + 1}/{(Director.Script != null ? Director.Script.Beats.Count : 0)} envScale={(env != null ? env.localScale.x.ToString("F2") : "n/a")} active={(env != null && env.gameObject.activeSelf)} playing={Application.isPlaying}";

        /// The diorama grows out of the table in front of the reader; its hall centre sits at chest height, a little below the page.
        IEnumerator Grow()
        {
            busy = true; Current = State.Growing; Director.Immersive = false;
            Director.ResetRoom();
            var fwd = Vector3.ProjectOnPlane(Head.forward, Vector3.up).normalized; if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            var centre = Director.Registry.Centre;
            var target = Head.position + fwd * 0.95f + Vector3.down * 0.55f;   // where the scene's centre point should sit, in world space
            env.localScale = Vector3.one * 0.001f;
            env.position = Vector3.zero;
            env.gameObject.SetActive(true); ShowBackdrop(false);
            // place so that the scaled hall centre lands on the target
            env.position = target - (centre.position - env.position);
            miniaturePivot = target;
            Panel.transform.localScale = Vector3.one * 0.7f; Panel.Distance = 1.0f; Panel.Height = 0.28f;
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
            var standAnchor = Director.Registry.ReaderStand; ShowBackdrop(true);
            // at full scale we want standAnchor under the reader: compute the final env position, then blend
            var startPos = env.position; var startScale = env.localScale.x;
            var endScale = Director.ReaderFactor;   // 1, or 4 once Alice has drunk
            var endPos = feet - (standAnchor.position - env.position) / startScale * endScale;
            Panel.transform.localScale = Vector3.one * 0.55f; Panel.Distance = 0.9f; Panel.Height = -0.32f;
            Director.Audio.PlayAmbience(Director.Script.Environment.Ambience, 0.6f);
            for (float e = 0; e < ExpandSeconds; e += Time.deltaTime)
            {
                float x = Mathf.SmoothStep(0, 1, e / ExpandSeconds);
                env.localScale = Vector3.one * Mathf.Lerp(startScale, endScale, x);
                env.position = Vector3.Lerp(startPos, endPos, x);
                yield return null;
            }
            env.localScale = Vector3.one * endScale; env.position = endPos;
            Current = State.Scene; busy = false; Director.Immersive = true;
            Panel.Show(Director.PassageScene, Director.Script.Beats[Mathf.Max(0, Director.BeatIndex)].SentenceId, Hint());
        }

        /// Back to the diorama on the table.
        IEnumerator Shrink()
        {
            busy = true; Current = State.Shrinking; Director.Immersive = false; Director.StopScaling();
            ReadingRoom.SetActive(true);
            var fwd = Vector3.ProjectOnPlane(Head.forward, Vector3.up).normalized; if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            var target = Head.position + fwd * 0.95f + Vector3.down * 0.55f;
            var centre = Director.Registry.Centre; ShowBackdrop(false);
            var startPos = env.position; var startScale = env.localScale.x;
            var endPos = target - (centre.position - env.position) / startScale * MiniatureScale;
            Panel.transform.localScale = Vector3.one * 0.7f; Panel.Distance = 1.0f; Panel.Height = 0.28f;
            Director.Audio.PlayAmbience(Director.Script.Environment.Ambience, 0.25f);
            for (float e = 0; e < ExpandSeconds; e += Time.deltaTime)
            {
                float x = Mathf.SmoothStep(0, 1, e / ExpandSeconds);
                env.localScale = Vector3.one * Mathf.Lerp(startScale, MiniatureScale, x);
                env.position = Vector3.Lerp(startPos, endPos, x);
                yield return null;
            }
            env.localScale = Vector3.one * MiniatureScale; env.position = endPos; miniaturePivot = target;
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
                Panel.transform.localScale = Vector3.one * Mathf.Lerp(0.7f, 1f, x);
                yield return null;
            }
            env.gameObject.SetActive(false);
            Director.Audio.StopAmbience();
            Panel.Distance = 1.15f; Panel.Height = -0.08f; Panel.transform.localScale = Vector3.one;
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
