// "Do what Alice does." Each sentence can hand the reader a small task in the room: try a door, pick up the key, carry it
// to the little door, kneel and look through, drink. The target glows softly, the page says what to do, and finishing the
// task moves the story to the next sentence (a pinch still works; the task is an invitation, never a lock). After the
// last sentence of the hall the little door becomes a real door: small enough now, the reader goes through into the garden.
using System.Collections.Generic;
using TMPro;
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
                new Task { Sentence = "hall-of-doors:002", Verb = Verb.Touch, Target = "doors", Prompt = "Alice tried every door. Point at one and pinch to try it.", Radius = 0.22f },
                new Task { Sentence = "hall-of-doors:004", Verb = Verb.Grab, Target = "prop.golden-key", Prompt = "Pick up the tiny golden key." },
                new Task { Sentence = "hall-of-doors:005", Verb = Verb.BringTo, Target = "prop.golden-key", Dest = "door.little", Prompt = "Hold the key and aim it at the little door.", Radius = 0.28f },
                new Task { Sentence = "hall-of-doors:006", Verb = Verb.LookAt, Target = "door.little", Prompt = "Look through the little door into the garden.", Radius = 30f },
                new Task { Sentence = "hall-of-doors:009", Verb = Verb.Grab, Target = "prop.drink-me-bottle", Prompt = "Pick up the little bottle." },
                new Task { Sentence = "hall-of-doors:011", Verb = Verb.BringTo, Target = "prop.drink-me-bottle", Dest = "head", Prompt = "DRINK ME: bring the bottle to your lips.", Radius = 0.26f },
                new Task { Sentence = "hall-of-doors:012", Verb = Verb.GoThrough, Target = "door.little", Passage = "queens-croquet-ground", Prompt = "You are small enough now. Keep your eyes on the little door to go through into the garden.", Radius = 30f },
            },
            ["mad-tea-party"] = new[]
            {
                new Task { Sentence = "mad-tea-party:000", Verb = Verb.LookAt, Target = "char.dormouse", Prompt = "Look at the Dormouse, fast asleep between them.", Radius = 3.5f },
                new Task { Sentence = "mad-tea-party:002", Verb = Verb.LookAt, Target = "prop.armchair", Prompt = "\"There's plenty of room!\" Find the big armchair at the end of the table.", Radius = 4f },
                new Task { Sentence = "mad-tea-party:004", Verb = Verb.Touch, Target = "char.march-hare", Prompt = "The March Hare offers you wine. Point at him and pinch.", Radius = 0.3f },
                new Task { Sentence = "mad-tea-party:005", Verb = Verb.Touch, Target = "prop.tea-service", Prompt = "Look all round the table: point at the tea things and pinch. Nothing but tea.", Radius = 0.25f },
                new Task { Sentence = "mad-tea-party:011", Verb = Verb.LookAt, Target = "char.hatter", Prompt = "The Hatter is staring at you. Look back at him.", Radius = 3.5f },
                new Task { Sentence = "mad-tea-party:014", Verb = Verb.Touch, Target = "prop.tea-service", Prompt = "A riddle! Point at your cup and pinch while you think.", Radius = 0.25f },
            },
            ["queens-croquet-ground"] = new[]
            {
                new Task { Sentence = "queens-croquet-ground:000", Verb = Verb.LookAt, Target = "prop.rose-tree", Prompt = "Three gardeners are painting the roses. Go nearer and watch.", Radius = 2.6f },
                new Task { Sentence = "queens-croquet-ground:001", Verb = Verb.Touch, Target = "prop.paint-pot", Prompt = "Red paint, for white roses. Point at the pot and pinch.", Radius = 0.25f },
                new Task { Sentence = "queens-croquet-ground:009", Verb = Verb.LookAt, Target = "char.seven", Prompt = "Seven has seen you. Look at him.", Radius = 4f },
                new Task { Sentence = "queens-croquet-ground:011", Verb = Verb.LookAt, Target = "char.two", Prompt = "They all look at Two. So do you.", Radius = 4f },
                new Task { Sentence = "queens-croquet-ground:012", Verb = Verb.Touch, Target = "prop.rose-tree", Prompt = "Point at a painted rose and pinch. The red comes off on your fingers.", Radius = 0.3f },
            },
        };

        SceneDirector director; FlowController flow; ReaderController reader; Transform head;
        Task active; float activeSince; bool done;
        readonly List<Renderer> glowing = new(); Color glowBase = new(1f, 0.78f, 0.35f);
        MaterialPropertyBlock block;   // made in Awake: Unity forbids creating one in a field initializer

        public string Prompt => active != null && !done ? active.Prompt : "";

        void Awake() { block ??= new MaterialPropertyBlock(); }

        public void Init(SceneDirector d, FlowController f, ReaderController r, Transform h)
        {
            director = d; flow = f; reader = r; head = h;
            director.BeatChanged += OnBeat;
            var panel = FindFirstObjectByType<ReadingPanel>(); if (panel && panel.Hint) font = panel.Hint.font;
        }

        // A sign above whatever the task is about, for a first-time reader who does not know where to look: a brass orb
        // bobbing over the target with a small paper tag saying what to do. It scales with the room (diorama or full size)
        // and always faces the reader.
        Transform beacon, orb, card; TextMeshPro tag; TMP_FontAsset font; float bobPhase;
        public Color Brass = new(0.85f, 0.62f, 0.22f), Paper = new(0.96f, 0.93f, 0.86f), InkColour = new(0.13f, 0.11f, 0.09f);

        void EnsureBeacon()
        {
            if (beacon) return;
            beacon = new GameObject("TaskBeacon").transform; beacon.SetParent(transform, false);
            var shader = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
            var o = GameObject.CreatePrimitive(PrimitiveType.Sphere); Destroy(o.GetComponent<Collider>()); o.name = "Orb"; o.transform.SetParent(beacon, false);
            var om = new Material(shader) { color = Brass }; o.GetComponent<Renderer>().material = om; o.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; orb = o.transform;
            var c = GameObject.CreatePrimitive(PrimitiveType.Quad); Destroy(c.GetComponent<Collider>()); c.name = "Card"; c.transform.SetParent(beacon, false);
            var cm = new Material(shader) { color = Paper }; c.GetComponent<Renderer>().material = cm; c.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; card = c.transform;
            var tg = new GameObject("Tag"); tg.transform.SetParent(beacon, false);
            tag = tg.AddComponent<TextMeshPro>(); if (font) tag.font = font; tag.color = InkColour; tag.alignment = TextAlignmentOptions.Center; tag.textWrappingMode = TextWrappingModes.Normal;
            tag.enableAutoSizing = true; tag.fontSizeMin = 0.4f; tag.fontSizeMax = 2.6f; tag.rectTransform.sizeDelta = new Vector2(11f, 2.4f); tag.transform.localScale = Vector3.one * 0.1f;
            beacon.gameObject.SetActive(false);
        }

        /// The instruction inside a prompt: the sentence that tells the hands what to do, else the whole prompt.
        static string Instruction(string prompt)
        {
            var parts = prompt.Split(new[] { ". ", "! ", "? " }, System.StringSplitOptions.RemoveEmptyEntries);
            string[] verbs = { "point", "pick", "look", "hold", "bring", "find", "keep", "go ", "touch", "drink" };
            foreach (var p in parts) { var l = p.ToLowerInvariant(); foreach (var v in verbs) if (l.Contains(v)) return p.TrimEnd('.').Trim(); }
            return prompt.TrimEnd('.');
        }

        /// Where the sign hangs: above the target asset, or above whichever big door is nearest the reader.
        bool TargetTop(out Vector3 top, out float scale)
        {
            top = Vector3.zero; scale = director.Registry.EnvironmentRoot ? director.Registry.EnvironmentRoot.lossyScale.x : 1f;
            Renderer[] rends = active.Target == "doors" ? DoorRenderers() : Renderers(director.Registry.Anchor(active.Target) ?? director.Registry.Asset(active.Target));
            if (rends.Length == 0) { var a = director.Registry.Anchor(active.Target) ?? director.Registry.Asset(active.Target); if (!a) return false; top = a.position + Vector3.up * 0.2f * scale; return true; }
            Renderer best = null; float bd = float.PositiveInfinity;
            foreach (var r in rends) { if (!r) continue; float d = head ? Vector3.Distance(r.bounds.center, head.position) : 0; if (d < bd) { bd = d; best = r; } }
            if (!best) return false;
            var b = best.bounds; top = new Vector3(b.center.x, b.max.y, b.center.z);
            if (active.Target == "doors") top = new Vector3(b.center.x, Mathf.Min(b.max.y, b.min.y + 2.2f * scale), b.center.z);   // door tops are high; hang the sign at eye-ish height
            return true;
        }

        void UpdateBeacon(bool show)
        {
            EnsureBeacon();
            if (!show || !TargetTop(out var top, out float scale)) { beacon.gameObject.SetActive(false); return; }
            beacon.gameObject.SetActive(true);
            bobPhase += Time.deltaTime * 2.4f;
            float s = Mathf.Clamp(scale, 0.04f, 3f);
            var pos = top + Vector3.up * (0.22f + 0.03f * Mathf.Sin(bobPhase)) * s;
            beacon.position = pos;
            if (head) { var to = pos - head.position; to.y *= 0.3f; if (to.sqrMagnitude > 0.0001f) beacon.rotation = Quaternion.LookRotation(to.normalized, Vector3.up); }
            orb.localPosition = Vector3.zero; orb.localScale = Vector3.one * 0.07f * s;
            card.localPosition = new Vector3(0, 0.2f * s, 0.002f * s); card.localScale = new Vector3(1.15f * s, 0.26f * s, 1);
            tag.transform.localPosition = new Vector3(0, 0.2f * s, 0); tag.transform.localScale = Vector3.one * 0.1f * s;
            tag.text = Instruction(active.Prompt);
        }

        void OnDestroy() { if (director) director.BeatChanged -= OnBeat; }

        void OnBeat(int index, Beat beat)
        {
            ClearGlow(); active = null; done = false; dwell = 0;
            if (director.PassageScene == null || !Tables.TryGetValue(director.PassageScene.Id, out var tasks)) return;
            foreach (var t in tasks) if (t.Sentence == beat.SentenceId) { active = t; activeSince = Time.time; break; }
            if (active != null && active.Target != "doors") Glow(director.Registry.Asset(active.Target));
        }

        void Update()
        {
            bool inRoom = flow && (flow.Current == FlowController.State.Scene || flow.Current == FlowController.State.Miniature);
            UpdateBeacon(active != null && !done && director && director.Registry != null && inRoom);
            if (active == null || done || !director || director.Registry == null) return;
            // tasks need a room the hands can reach: the diorama or the full-scale scene, never the bare page
            if (!inRoom) return;
            if (Time.time - activeSince < 0.6f) return;   // let the sentence land before judging a hand that was already there
            Pulse();
            float scale = director.Registry.EnvironmentRoot ? director.Registry.EnvironmentRoot.lossyScale.x : 1f;
            float radius = active.Radius * scale;
            bool ok = active.Verb switch
            {
                Verb.Touch => active.Target == "doors" ? (Touching(radius) || PointingAt(DoorRenderers())) : (TouchingAsset(director.Registry.Asset(active.Target), radius) || PointingAt(Renderers(director.Registry.Asset(active.Target)))),
                Verb.Grab => Holding(active.Target),
                Verb.BringTo => Holding(active.Target) && (Near(director.Registry.Asset(active.Target), DestPoint(), radius) || (active.Dest != "head" && Aiming(director.Registry.Asset(active.Target), Renderers(director.Registry.Anchor(active.Dest) ?? director.Registry.Asset(active.Dest))))),
                Verb.LookAt => LookingAt(director.Registry.Anchor(active.Target) ?? director.Registry.Asset(active.Target), radius),
                Verb.GoThrough => flow && flow.Current == FlowController.State.Scene && Dwell(LookingAt(director.Registry.Anchor(active.Target) ?? director.Registry.Asset(active.Target), radius), 1.4f),
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
            return to.magnitude < radius && Vector3.Dot(head.forward, to.normalized) > 0.94f;   // about 20 degrees
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

        /// Seated readers cannot walk to things, so a hand that points at the target while pinching counts as touching it.
        Renderer[] Renderers(Transform t) => t ? t.GetComponentsInChildren<Renderer>() : new Renderer[0];
        Renderer[] DoorRenderers()
        {
            var root = director.Registry.EnvironmentRoot; if (!root) return new Renderer[0];
            var list = new List<Renderer>();
            foreach (var r in root.GetComponentsInChildren<Renderer>()) if (r.name.StartsWith("MESH_Door") && !r.name.Contains("Little")) list.Add(r);
            return list.ToArray();
        }
        bool PointingAt(Renderer[] targets)
        {
            if (!head || targets.Length == 0 || !reader || !(reader.LeftPinching || reader.RightPinching)) return false;
            foreach (var h in Hands())
            {
                var ray = new Ray(head.position, (h - head.position).normalized);
                foreach (var r in targets) if (r && r.bounds.IntersectRay(ray, out float d) && d < 40f) return true;
            }
            return false;
        }
        /// Aim a held object at a destination: the line from the head through the object meets the destination.
        bool Aiming(Transform held, Renderer[] dest)
        {
            if (!held || !head || dest.Length == 0) return false;
            var ray = new Ray(head.position, (held.position - head.position).normalized);
            foreach (var r in dest) if (r && r.bounds.IntersectRay(ray, out float d) && d < 40f) return true;
            var a = director.Registry.Anchor(active.Dest) ?? director.Registry.Asset(active.Dest);
            return a && Vector3.Dot(ray.direction, (a.position - head.position).normalized) > 0.995f;
        }
        float dwell;
        bool Dwell(bool condition, float seconds)
        {
            dwell = condition ? dwell + Time.deltaTime : Mathf.Max(0, dwell - Time.deltaTime * 2f);
            return dwell >= seconds;
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
            block ??= new MaterialPropertyBlock();
            foreach (var r in glowing) { if (!r) continue; r.GetPropertyBlock(block); block.SetColor("_EmissionColor", glowBase * k * 0.6f); r.SetPropertyBlock(block); }
        }

        void ClearGlow()
        {
            foreach (var r in glowing) if (r) r.SetPropertyBlock(null);
            glowing.Clear();
        }
    }
}
