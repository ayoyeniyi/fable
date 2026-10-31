// "Do what Alice does." Each sentence can hand the reader a small task in the room: try a door, pick up the key, carry it
// to the little door, kneel and look through, drink. The target glows softly, the page says what to do, and finishing the
// task moves the story to the next sentence (a pinch still works; the task is an invitation, never a lock). After the
// last sentence of the hall the little door becomes a real door: small enough now, the reader goes through into the garden.
using System.Collections.Generic;
using UnityEngine;

namespace Fable
{
    public class StoryTasks : MonoBehaviour
    {
        public enum Verb { Touch, Grab, BringTo, LookAt, GoThrough }

        public class Task
        {
            public string Sentence;      // active while this sentence is the current beat
            public Verb Verb;
            public string Target;        // asset id, or "doors" for any of the hall's big doors
            public string Dest;          // BringTo: anchor id, or "head"
            public string Prompt;
            public float Radius = 0.18f; // metres at full scale (scaled with the room)
            public string Passage;       // GoThrough: the passage to open
        }

        static readonly Dictionary<string, Task[]> Tables = new()
        {
            ["hall-of-doors"] = new[]
            {
                new Task { Sentence = "hall-of-doors:002", Verb = Verb.Touch, Target = "doors", Prompt = "Alice tried every door. Reach out and try one.", Radius = 0.22f },
                new Task { Sentence = "hall-of-doors:004", Verb = Verb.Grab, Target = "prop.golden-key", Prompt = "Pick up the tiny golden key." },
                new Task { Sentence = "hall-of-doors:005", Verb = Verb.BringTo, Target = "prop.golden-key", Dest = "door.little", Prompt = "Take the key to the little door.", Radius = 0.28f },
                new Task { Sentence = "hall-of-doors:006", Verb = Verb.LookAt, Target = "door.little", Prompt = "Kneel and look through the little door.", Radius = 1.1f },
                new Task { Sentence = "hall-of-doors:009", Verb = Verb.Grab, Target = "prop.drink-me-bottle", Prompt = "Pick up the little bottle." },
                new Task { Sentence = "hall-of-doors:011", Verb = Verb.BringTo, Target = "prop.drink-me-bottle", Dest = "head", Prompt = "DRINK ME: bring the bottle to your lips.", Radius = 0.26f },
                new Task { Sentence = "hall-of-doors:012", Verb = Verb.GoThrough, Target = "door.little", Passage = "queens-croquet-ground", Prompt = "You are small enough now. Go through the little door into the garden.", Radius = 0.7f },
            },
            ["mad-tea-party"] = new[]
            {
                new Task { Sentence = "mad-tea-party:000", Verb = Verb.LookAt, Target = "char.dormouse", Prompt = "Look at the Dormouse, fast asleep between them.", Radius = 3.5f },
                new Task { Sentence = "mad-tea-party:002", Verb = Verb.LookAt, Target = "prop.armchair", Prompt = "\"There's plenty of room!\" Find the big armchair at the end of the table.", Radius = 4f },
                new Task { Sentence = "mad-tea-party:004", Verb = Verb.Touch, Target = "char.march-hare", Prompt = "The March Hare offers you wine. Reach out to him.", Radius = 0.3f },
                new Task { Sentence = "mad-tea-party:005", Verb = Verb.Touch, Target = "prop.tea-service", Prompt = "Look all round the table: touch the tea things. There is nothing but tea.", Radius = 0.25f },
                new Task { Sentence = "mad-tea-party:011", Verb = Verb.LookAt, Target = "char.hatter", Prompt = "The Hatter is staring at you. Look back at him.", Radius = 3.5f },
                new Task { Sentence = "mad-tea-party:014", Verb = Verb.Touch, Target = "prop.tea-service", Prompt = "A riddle! Pick up your cup while you think.", Radius = 0.25f },
            },
            ["queens-croquet-ground"] = new[]
            {
                new Task { Sentence = "queens-croquet-ground:000", Verb = Verb.LookAt, Target = "prop.rose-tree", Prompt = "Three gardeners are painting the roses. Go nearer and watch.", Radius = 2.6f },
                new Task { Sentence = "queens-croquet-ground:001", Verb = Verb.Touch, Target = "prop.paint-pot", Prompt = "Red paint, for white roses. Touch the pot.", Radius = 0.25f },
                new Task { Sentence = "queens-croquet-ground:009", Verb = Verb.LookAt, Target = "char.seven", Prompt = "Seven has seen you. Look at him.", Radius = 4f },
                new Task { Sentence = "queens-croquet-ground:011", Verb = Verb.LookAt, Target = "char.two", Prompt = "They all look at Two. So do you.", Radius = 4f },
                new Task { Sentence = "queens-croquet-ground:012", Verb = Verb.Touch, Target = "prop.rose-tree", Prompt = "Touch a painted rose. The red comes off on your fingers.", Radius = 0.3f },
            },
        };

        SceneDirector director; FlowController flow; ReaderController reader; Transform head;
        Task active; float activeSince; bool done;
        readonly List<Renderer> glowing = new(); Color glowBase = new(1f, 0.78f, 0.35f);
        readonly MaterialPropertyBlock block = new();

        public string Prompt => active != null && !done ? active.Prompt : "";

        public void Init(SceneDirector d, FlowController f, ReaderController r, Transform h)
        {
            director = d; flow = f; reader = r; head = h;
            director.BeatChanged += OnBeat;
        }

        void OnDestroy() { if (director) director.BeatChanged -= OnBeat; }

        void OnBeat(int index, Beat beat)
        {
            ClearGlow(); active = null; done = false;
            if (director.PassageScene == null || !Tables.TryGetValue(director.PassageScene.Id, out var tasks)) return;
            foreach (var t in tasks) if (t.Sentence == beat.SentenceId) { active = t; activeSince = Time.time; break; }
            if (active != null && active.Target != "doors") Glow(director.Registry.Asset(active.Target));
        }

        void Update()
        {
            if (active == null || done || !director || director.Registry == null) return;
            // tasks need a room the hands can reach: the diorama or the full-scale scene, never the bare page
            if (flow && flow.Current != FlowController.State.Scene && flow.Current != FlowController.State.Miniature) return;
            if (Time.time - activeSince < 0.6f) return;   // let the sentence land before judging a hand that was already there
            Pulse();
            float scale = director.Registry.EnvironmentRoot ? director.Registry.EnvironmentRoot.lossyScale.x : 1f;
            float radius = active.Radius * scale;
            bool ok = active.Verb switch
            {
                Verb.Touch => active.Target == "doors" ? Touching(radius) : TouchingAsset(director.Registry.Asset(active.Target), radius),
                Verb.Grab => Holding(active.Target),
                Verb.BringTo => Holding(active.Target) && Near(director.Registry.Asset(active.Target), DestPoint(), radius),
                Verb.LookAt => LookingAt(director.Registry.Anchor(active.Target) ?? director.Registry.Asset(active.Target), radius),
                Verb.GoThrough => flow && flow.Current == FlowController.State.Scene && Near(head, (director.Registry.Anchor(active.Target) ?? director.Registry.Asset(active.Target))?.position ?? Vector3.positiveInfinity, radius),
                _ => false
            };
            if (!ok) return;
            done = true; ClearGlow();
            Debug.Log($"[Fable] task done: {active.Verb} {active.Target} on {active.Sentence}");
            if (active.Verb == Verb.GoThrough) { if (flow) flow.OpenPassage(active.Passage); }
            else director.Next();
        }

        Vector3 DestPoint()
        {
            if (active.Dest == "head") return head ? head.position + head.forward * 0.08f - Vector3.up * 0.08f : Vector3.positiveInfinity;   // the mouth, roughly
            var a = director.Registry.Anchor(active.Dest) ?? director.Registry.Asset(active.Dest);
            return a ? a.position : Vector3.positiveInfinity;
        }

        bool Holding(string assetId)
        {
            foreach (var g in FindObjectsByType<StoryGrabbable>(FindObjectsSortMode.None)) if (g.AssetId == assetId && g.Held) return true;
            return false;
        }

        static bool Near(Transform t, Vector3 p, float r) => t && !float.IsInfinity(p.x) && Vector3.Distance(t.position, p) < r;

        bool LookingAt(Transform t, float radius)
        {
            if (!t || !head) return false;
            var to = t.position - head.position;
            return to.magnitude < radius && Vector3.Dot(head.forward, to.normalized) > 0.82f;
        }

        IEnumerable<Vector3> Hands()
        {
#if FABLE_META_XR
            if (reader)
            {
                if (reader.LeftPointer && (reader.LeftHand == null || reader.LeftHand.IsTracked || OVRInput.IsControllerConnected(OVRInput.Controller.LTouch))) yield return reader.LeftPointer.position;
                if (reader.RightPointer && (reader.RightHand == null || reader.RightHand.IsTracked || OVRInput.IsControllerConnected(OVRInput.Controller.RTouch))) yield return reader.RightPointer.position;
            }
#else
            yield break;
#endif
        }

        /// A hand within reach of any big door (the hall's doors are merged meshes named MESH_Door*).
        bool Touching(float radius)
        {
            var root = director.Registry.EnvironmentRoot; if (!root) return false;
            foreach (var h in Hands())
                foreach (var r in root.GetComponentsInChildren<Renderer>())
                    if (r.name.StartsWith("MESH_Door") && !r.name.Contains("Little") && Vector3.Distance(r.bounds.ClosestPoint(h), h) < radius) return true;
            return false;
        }

        bool TouchingAsset(Transform t, float radius)
        {
            if (!t) return false;
            var rends = t.GetComponentsInChildren<Renderer>();
            foreach (var h in Hands())
            {
                if (rends.Length == 0 && Vector3.Distance(t.position, h) < radius) return true;
                foreach (var r in rends) if (Vector3.Distance(r.bounds.ClosestPoint(h), h) < radius) return true;
            }
            return false;
        }

        void Glow(Transform target)
        {
            if (!target) return;
            foreach (var r in target.GetComponentsInChildren<Renderer>())
                if (r.sharedMaterial && r.sharedMaterial.HasProperty("_EmissionColor")) { r.material.EnableKeyword("_EMISSION"); glowing.Add(r); }   // imported props have emission off
        }

        void Pulse()
        {
            if (glowing.Count == 0) return;
            float k = 0.25f + 0.75f * (0.5f + 0.5f * Mathf.Sin(Time.time * 3.2f));
            foreach (var r in glowing) { if (!r) continue; r.GetPropertyBlock(block); block.SetColor("_EmissionColor", glowBase * k * 0.6f); r.SetPropertyBlock(block); }
        }

        void ClearGlow()
        {
            foreach (var r in glowing) if (r) r.SetPropertyBlock(null);
            glowing.Clear();
        }
    }
}
