// Reading -> Unfolding -> Scene -> Returning. The room grows out of the page and folds back into it.
using System.Collections;
using System.Linq;
using Newtonsoft.Json;
using UnityEngine;

namespace Fable
{
    public class FlowController : MonoBehaviour
    {
        public enum State { Reading, Unfolding, Scene, Returning }
        public State Current { get; private set; } = State.Reading;

        public SceneDirector Director;
        public ReaderController Input;
        public ReadingPanel Panel;
        public Transform Head;
        public GameObject ReadingRoom;          // the quiet void with the page (soft light, dark floor disc)
        public string SceneId = "hall-of-doors";
        public float UnfoldSeconds = 2.8f;

        Passage book;
        Transform env;

        IEnumerator Start()
        {
            book = JsonConvert.DeserializeObject<Passage>(System.IO.File.ReadAllText(System.IO.Path.Combine(Application.streamingAssetsPath, "book/passages.json")));
            env = Director.Registry.EnvironmentRoot;
            // desktop preview without a headset: lift the eye to seated height so captures and editor tests are representative
            if (!UnityEngine.XR.XRSettings.isDeviceActive && Head && Head.localPosition.y < 0.5f) Head.localPosition = new Vector3(0, 1.25f, 0);
            yield return Director.Load(SceneId, book);
            env.gameObject.SetActive(false);
            Input.Select += OnSelect; Input.Next += OnNext; Input.Previous += OnPrev; Input.ReturnToReading += OnReturn;
            Director.BeatChanged += (i, b) => Panel.Show(Director.PassageScene, b.SentenceId, $"{i + 1} / {Director.Script.Beats.Count}   pinch right to continue, left to go back, both hands to return");
            Panel.Show(Director.PassageScene, null, "pinch to step into the hall");
        }

        // test hooks: the same paths the hands take, callable from the editor CLI
        public void StepInto() => OnSelect();
        public void StepNext() => OnNext();
        public void StepBack() => OnPrev();
        public void StepReturn() => OnReturn();
        public string Describe() => $"state={Current} beat={Director.BeatIndex + 1}/{(Director.Script != null ? Director.Script.Beats.Count : 0)} envScale={(env != null ? env.localScale.x.ToString("F2") : "n/a")} active={(env != null && env.gameObject.activeSelf)} playing={Application.isPlaying}";

        void OnSelect() { if (Current == State.Reading) StartCoroutine(Unfold()); }
        void OnNext() { if (Current == State.Scene && !Director.Next()) StartCoroutine(Return()); }
        void OnPrev() { if (Current == State.Scene) Director.Previous(); }
        void OnReturn() { if (Current == State.Scene) StartCoroutine(Return()); }

        IEnumerator Unfold()
        {
            Current = State.Unfolding;
            Director.ResetRoom();
            var pivot = new Vector3(Head.position.x, env.position.y, Head.position.z);
            env.gameObject.SetActive(true);
            Director.Audio.PlayAmbience(Director.Script.Environment.Ambience, 0f);
            for (float e = 0; e < UnfoldSeconds; e += Time.deltaTime)
            {
                float x = Mathf.SmoothStep(0, 1, e / UnfoldSeconds);
                ScaleAbout(env, pivot, Mathf.Lerp(0.04f, 1f, x));
                Panel.transform.localScale = Vector3.one * Mathf.Lerp(1f, 0.001f, x);
                yield return null;
            }
            ScaleAbout(env, pivot, 1f);
            ReadingRoom.SetActive(false);
            Panel.transform.localScale = Vector3.one * 0.55f;   // the page stays as a small caption at the reader's side
            Panel.Distance = 0.9f; Panel.Height = -0.32f;
            Current = State.Scene;
            Director.Next();
        }

        IEnumerator Return()
        {
            Current = State.Returning;
            var pivot = new Vector3(Head.position.x, env.position.y, Head.position.z);
            float from = env.localScale.x;
            ReadingRoom.SetActive(true);
            for (float e = 0; e < UnfoldSeconds; e += Time.deltaTime)
            {
                float x = Mathf.SmoothStep(0, 1, e / UnfoldSeconds);
                ScaleAbout(env, pivot, Mathf.Lerp(from, 0.04f, x));
                Panel.transform.localScale = Vector3.one * Mathf.Lerp(0.55f, 1f, x);
                yield return null;
            }
            env.gameObject.SetActive(false);
            Director.Audio.StopAmbience();
            Panel.Distance = 1.15f; Panel.Height = -0.08f; Panel.transform.localScale = Vector3.one;
            Panel.Show(Director.PassageScene, null, "pinch to step into the hall again");
            Current = State.Reading;
        }

        static void ScaleAbout(Transform t, Vector3 pivot, float s)
        {
            var prev = t.localScale.x; if (Mathf.Approximately(prev, 0)) prev = 1;
            t.position = pivot + (t.position - pivot) * (s / prev);
            t.localScale = Vector3.one * s;
        }
    }
}
