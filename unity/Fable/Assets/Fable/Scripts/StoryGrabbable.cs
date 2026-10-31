// A prop the reader can pick up in the immersive view (the golden key, the DRINK ME bottle). Holding it
// brings back the sentence that first introduces it; letting go returns it to where the script placed it,
// so the room stays a pure function of the beat index.
//
// The Interaction SDK pieces are added and injected here in Awake, before their Start runs, which is the
// SDK's documented pattern for objects built in code. Hands grab by pinch or palm; controllers by grip.
using Oculus.Interaction;
using Oculus.Interaction.Grab;
using Oculus.Interaction.GrabAPI;
using Oculus.Interaction.HandGrab;
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
        public float ReturnSeconds = 0.6f;

        GrabInteractable grab;
        HandGrabInteractable handGrab;
        bool held, interactive;
        Vector3 restPos; Quaternion restRot;
        float returning = -1; Vector3 releasePos; Quaternion releaseRot;

        public bool Held => held;

        void Awake()
        {
            if (!TryGetComponent<Rigidbody>(out var rb)) rb = gameObject.AddComponent<Rigidbody>();   // not ??: Unity fake-null
            rb.isKinematic = true; rb.useGravity = false;
            if (!GetComponentInChildren<Collider>()) AddBoundsCollider();

            var grabbable = gameObject.AddComponent<Grabbable>();
            grabbable.InjectOptionalRigidbody(rb);
            grabbable.InjectOptionalKinematicWhileSelected(true);
            grabbable.InjectOptionalThrowWhenUnselected(false);

            grab = gameObject.AddComponent<GrabInteractable>();
            grab.InjectAllGrabInteractable(rb);
            grab.InjectOptionalPointableElement(grabbable);

            handGrab = gameObject.AddComponent<HandGrabInteractable>();
            handGrab.InjectAllHandGrabInteractable(GrabTypeFlags.Pinch | GrabTypeFlags.Palm, rb, GrabbingRule.DefaultPinchRule, GrabbingRule.DefaultPalmRule);
            handGrab.InjectOptionalPointableElement(grabbable);

            grab.WhenStateChanged += OnState;
            handGrab.WhenStateChanged += OnState;
            grab.enabled = handGrab.enabled = interactive = false;   // Update turns them on at full immersion
        }

        void OnDestroy()
        {
            if (grab) grab.WhenStateChanged -= OnState;
            if (handGrab) handGrab.WhenStateChanged -= OnState;
        }

        /// Small props (the key is 5 cm) get a generous box so a pinch near them still lands.
        void AddBoundsCollider()
        {
            var rs = GetComponentsInChildren<Renderer>(true);
            var box = gameObject.AddComponent<BoxCollider>();
            if (rs.Length == 0) { box.size = Vector3.one * 0.08f; return; }
            var b = new Bounds(transform.InverseTransformPoint(rs[0].bounds.center), Vector3.zero);
            foreach (var r in rs)
            {
                var wb = r.bounds;
                for (int i = 0; i < 8; i++)
                    b.Encapsulate(transform.InverseTransformPoint(wb.center + Vector3.Scale(wb.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1))));
            }
            box.center = b.center;
            var min = 0.06f / Mathf.Max(1e-4f, transform.lossyScale.x);
            box.size = Vector3.Max(b.size + Vector3.one * (0.02f / Mathf.Max(1e-4f, transform.lossyScale.x)), Vector3.one * min);
        }

        bool Selected => (grab && grab.State == InteractableState.Select) || (handGrab && handGrab.State == InteractableState.Select);

        void OnState(InteractableStateChangeArgs args)
        {
            if (!held && Selected) OnGrab();
            else if (held && !Selected) OnRelease();
        }

        void OnGrab()
        {
            held = true; returning = -1;
            restPos = transform.localPosition; restRot = transform.localRotation;
            if (Reader) Reader.SuppressCurrentPinch();
            var at = Director.IntroducedBy(AssetId);
            if (Panel && at != null) Panel.Show(Director.PassageScene, at, $"{Describe()}, as the story first gives it. let go to put it back");
        }

        void OnRelease()
        {
            held = false;
            releasePos = transform.localPosition; releaseRot = transform.localRotation; returning = 0;
            if (Reader) Reader.SuppressCurrentPinch();
            Flow.RefreshPanel();
        }

        string Describe() => AssetId switch
        {
            "prop.golden-key" => "the tiny golden key",
            "prop.drink-me-bottle" => "the little bottle",
            _ => "this"
        };

        void Update()
        {
            // only touchable at full immersion: the diorama props are a few millimetres across
            bool want = Flow && Flow.Current == FlowController.State.Scene;
            if (want != interactive)
            {
                interactive = want; grab.enabled = want; handGrab.enabled = want;
            }
            if (returning >= 0 && !held)
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
            if (held) { held = false; transform.localPosition = restPos; transform.localRotation = restRot; }
        }
    }
}
