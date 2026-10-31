// Reading -> Miniature -> Scene -> back. The room first appears as a diorama on the reading table,
// then grows around the reader. Closing returns to the page at the sentence the reader reached.
using System.Collections;
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

        IEnumerator Start()
        {
            book = JsonConvert.DeserializeObject<Passage>(System.IO.File.ReadAllText(System.IO.Path.Combine(Application.streamingAssetsPath, "book/passages.json")));
            env = Director.Registry.EnvironmentRoot;
            if (!UnityEngine.XR.XRSettings.isDeviceActive && Head && Head.localPosition.y < 0.5f) Head.localPosition = new Vector3(0, 1.25f, 0);
            yield return Director.Load(SceneId, book);
            env.gameObject.SetActive(false);
            Input.Select += OnSelect; Input.Next += OnNext; Input.Previous += OnPrev; Input.ReturnToReading += OnReturn; Input.ToggleView += OnToggle; Input.Scrub += OnScrub;
            Director.BeatChanged += (i, b) =>
            {
                Panel.Show(Director.PassageScene, b.SentenceId, Hint());
                ProgressStore.Save(SceneId, i, b.SentenceId);
            };
            var saved = ProgressStore.Load();
            string resumeAt = saved.SceneId == SceneId ? saved.SentenceId : null;
            Panel.Show(Director.PassageScene, resumeAt, resumeAt != null ? "welcome back. pinch to open the hall where you left it" : "pinch to open the hall");
        }

        string Hint() => Current == State.Scene
            ? $"{Director.BeatIndex + 1} / {Director.Script.Beats.Count}   tap right to continue, left to go back, drag to scrub, both hands: miniature, hold: page"
            : $"{Director.BeatIndex + 1} / {Director.Script.Beats.Count}   tap right to continue, drag to scrub, both hands: step inside, hold: page";

        void OnSelect() { if (Current == State.Reading && !busy) StartCoroutine(Grow()); }
        void OnNext() { if ((Current == State.Scene || Current == State.Miniature) && !busy && !Director.Next()) StartCoroutine(Current == State.Scene ? Shrink() : Return()); }
        void OnPrev() { if ((Current == State.Scene || Current == State.Miniature) && !busy) Director.Previous(); }
        void OnScrub(int dir) { if ((Current == State.Scene || Current == State.Miniature) && !busy) { if (dir > 0) Director.Next(); else Director.Previous(); } }
        void OnToggle()
        {
            if (busy) return;
            if (Current == State.Miniature) StartCoroutine(Expand());
            else if (Current == State.Scene) StartCoroutine(Shrink());
            else if (Current == State.Reading) StartCoroutine(Grow());
        }
        void OnReturn() { if ((Current == State.Scene || Current == State.Miniature) && !busy) StartCoroutine(Return()); }

        // test hooks: the same paths the hands take, callable from the editor CLI
        public void StepInto() => OnSelect();
        public void StepNext() => OnNext();
        public void StepBack() => OnPrev();
        public void StepToggle() => OnToggle();
        public void StepReturn() => OnReturn();
        public string Describe() => $"state={Current} beat={Director.BeatIndex + 1}/{(Director.Script != null ? Director.Script.Beats.Count : 0)} envScale={(env != null ? env.localScale.x.ToString("F2") : "n/a")} active={(env != null && env.gameObject.activeSelf)} playing={Application.isPlaying}";

        /// The diorama grows out of the table in front of the reader; its hall centre sits at chest height, a little below the page.
        IEnumerator Grow()
        {
            busy = true; Current = State.Growing;
            Director.ResetRoom();
            var fwd = Vector3.ProjectOnPlane(Head.forward, Vector3.up).normalized; if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            var centre = Director.Registry.Anchor("hall.centre");
            var target = Head.position + fwd * 0.95f + Vector3.down * 0.55f;   // where the hall's centre point should sit, in world space
            env.localScale = Vector3.one * 0.001f;
            env.position = Vector3.zero;
            env.gameObject.SetActive(true);
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
            var saved = ProgressStore.Load();
            if (saved.SceneId == SceneId && saved.BeatIndex >= 0) Director.JumpTo(saved.BeatIndex); else Director.Next();
        }

        /// From diorama to full scale around the reader. The pivot moves from the table to the reader's feet so the floor arrives under them.
        IEnumerator Expand()
        {
            busy = true; Current = State.Expanding;
            ReadingRoom.SetActive(false);
            var feet = new Vector3(Head.position.x, 0f, Head.position.z);
            var standAnchor = Director.Registry.Anchor("reader.table") ?? Director.Registry.Anchor("reader.entrance");
            // at full scale we want standAnchor under the reader: compute the final env position, then blend
            var startPos = env.position; var startScale = env.localScale.x;
            var endScale = 1f;
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
            env.localScale = Vector3.one; env.position = endPos;
            Current = State.Scene; busy = false;
            Panel.Show(Director.PassageScene, Director.Script.Beats[Mathf.Max(0, Director.BeatIndex)].SentenceId, Hint());
        }

        /// Back to the diorama on the table.
        IEnumerator Shrink()
        {
            busy = true; Current = State.Shrinking;
            ReadingRoom.SetActive(true);
            var fwd = Vector3.ProjectOnPlane(Head.forward, Vector3.up).normalized; if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            var target = Head.position + fwd * 0.95f + Vector3.down * 0.55f;
            var centre = Director.Registry.Anchor("hall.centre");
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
            busy = true; Current = State.Returning;
            ReadingRoom.SetActive(true);
            var pivot = Current == State.Scene ? new Vector3(Head.position.x, env.position.y, Head.position.z) : miniaturePivot;
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
            var at = Director.BeatIndex >= 0 ? Director.Script.Beats[Director.BeatIndex].SentenceId : null;
            Panel.Show(Director.PassageScene, at, "pinch to open the hall again");
            Current = State.Reading; busy = false;
        }

        static void ScaleAbout(Transform t, Vector3 pivot, float s)
        {
            var prev = t.localScale.x; if (Mathf.Approximately(prev, 0)) prev = 1;
            t.position = pivot + (t.position - pivot) * (s / prev);
            t.localScale = Vector3.one * s;
        }
    }
}
