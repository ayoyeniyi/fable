// A prop the reader can pick up in the full-size room (the golden key, the DRINK ME bottle). Picking up is hands-first
// and seated-friendly: point the ray at the prop and pinch, and it flies into the hand and stays there while the pinch
// is held; or close a pinching hand on it directly. Letting go returns it to where the script placed it, so the room
// stays a pure function of the beat index. Holding it brings back the sentence that first introduces it.
// Grabbing is done by Locomotion (which owns the pointing ray and the pinch events); this component is the prop side.
using UnityEngine;

namespace Fable
{
    public class StoryGrabbable : MonoBehaviour
    {
        public string AssetId;
        public FlowController Flow;
        public SceneDirector Director;
        public ReadingPanel Panel;
        public ReaderController Reader;
        public float ReturnSeconds = 0.6f, FlySeconds = 0.18f;

        bool held; Transform hand; Quaternion relRot; float flying;
        Vector3 restPos; Quaternion restRot;
        float returning = -1; Vector3 releasePos; Quaternion releaseRot;
        Renderer[] renderers;

        public bool Held => held;
        public Transform HeldBy => held ? hand : null;
        /// Only in the full-size room: in the diorama the props are a few millimetres across.
        public bool CanGrab => Flow && Flow.Current == FlowController.State.Scene && !held;

        void Awake() { renderers = GetComponentsInChildren<Renderer>(true); }

        /// World bounds of the prop's meshes (its rest pose moves with the beat, so this is read live).
        public bool WorldBounds(out Bounds b)
        {
            b = default; bool any = false;
            foreach (var r in renderers) { if (!r) continue; if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds); }
            if (!any) { b = new Bounds(transform.position, Vector3.one * 0.08f); any = true; }
            return any;
        }

        public void Grab(Transform by)
        {
            if (held || !by) return;
            held = true; hand = by; returning = -1; flying = 0;
            restPos = transform.localPosition; restRot = transform.localRotation;
            relRot = Quaternion.Inverse(hand.rotation) * transform.rotation;
            if (Reader) Reader.SuppressCurrentPinch();
            var at = Director ? Director.IntroducedBy(AssetId) : null;
            if (Panel && Director && at != null) Panel.Show(Director.PassageScene, at, $"{Describe()}, as the story first gives it. let go to put it back");
            Debug.Log($"[Fable] grab {AssetId}");
        }

        public void Release()
        {
            if (!held) return;
            held = false; hand = null;
            releasePos = transform.localPosition; releaseRot = transform.localRotation; returning = 0;
            if (Reader) Reader.SuppressCurrentPinch();
            if (Flow) Flow.RefreshPanel();
            Debug.Log($"[Fable] release {AssetId}");
        }

        string Describe() => AssetId switch
        {
            "prop.golden-key" => "the tiny golden key",
            "prop.drink-me-bottle" => "the little bottle",
            _ => "this"
        };

        void LateUpdate()
        {
            if (held)
            {
                if (!hand) { Release(); return; }
                // fly to the pinch, then ride with the hand
                flying = Mathf.Min(1f, flying + Time.deltaTime / FlySeconds);
                var target = hand.position + hand.forward * 0.02f;
                float k = flying < 1f ? Mathf.SmoothStep(0, 1, flying) : 1f;
                transform.position = flying < 1f ? Vector3.Lerp(transform.position, target, k) : target;
                transform.rotation = Quaternion.Slerp(transform.rotation, hand.rotation * relRot, flying < 1f ? k : 1f);
                return;
            }
            if (returning >= 0)
            {
                returning += Time.deltaTime / ReturnSeconds;
                float x = Mathf.SmoothStep(0, 1, Mathf.Clamp01(returning));
                transform.localPosition = Vector3.Lerp(releasePos, restPos, x);
                transform.localRotation = Quaternion.Slerp(releaseRot, restRot, x);
                if (returning >= 1) returning = -1;
            }
        }

        /// The director resets and replays the room on every beat change; a held prop lets go first.
        public void ForceRest()
        {
            returning = -1;
            if (held) { held = false; hand = null; transform.localPosition = restPos; transform.localRotation = restRot; }
        }
    }
}
