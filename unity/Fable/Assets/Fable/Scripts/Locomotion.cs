// Point and pinch. A ray leaves the pointing hand (or controller) and lands as a disc; a pinch acts on what it touches:
//   floor of the full-size room  -> you are there (teleport)
//   floor of the diorama         -> you step into the room at that spot
//   the little door              -> you go through it into the next place
//   a locked door                -> it rattles
// Nothing here needs two hands or a combination. Walking is arm-swinging (both hands pumping, seated or standing) or
// the controller thumbstick. Pointing at nothing leaves the pinch to the page (next sentence).
using System.Collections.Generic;
using UnityEngine;

namespace Fable
{
    public class Locomotion : MonoBehaviour
    {
        public enum HitKind { None, Floor, LittleDoor, LockedDoor }
        public float TeleportDiscMetres = 0.34f, WalkSpeed = 1.6f, SwingThreshold = 0.45f;
        public Color Brass = new(0.85f, 0.62f, 0.22f), Go = new(0.95f, 0.9f, 0.75f), Locked = new(0.8f, 0.3f, 0.2f);

        FlowController flow; SceneDirector director; ReaderController reader; Transform head, rig;
        LineRenderer line; Transform disc; Material lineMat, discMat;
        HitKind hit; Vector3 hitPoint; bool rightSource = true;
        Vector3 lastL, lastR; float swing; bool hadHands;

        public HitKind CurrentHit => hit;

        public void Init(FlowController f, SceneDirector d, ReaderController r, Transform h, Transform rigRoot)
        {
            flow = f; director = d; reader = r; head = h; rig = rigRoot;
            var shader = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
            lineMat = new Material(shader); discMat = new Material(shader);
            var lg = new GameObject("PointRay"); lg.transform.SetParent(transform, false);
            line = lg.AddComponent<LineRenderer>(); line.material = lineMat; line.positionCount = 2; line.useWorldSpace = true; line.widthMultiplier = 0.006f; line.numCapVertices = 2; line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; line.receiveShadows = false;
            var d0 = GameObject.CreatePrimitive(PrimitiveType.Cylinder); Destroy(d0.GetComponent<Collider>()); d0.name = "PointDisc"; d0.transform.SetParent(transform, false);
            d0.GetComponent<Renderer>().material = discMat; d0.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; disc = d0.transform;
            Show(false);
            reader.TapInterceptor = Activate;
        }

        void Show(bool on) { if (line) line.enabled = on; if (disc) disc.gameObject.SetActive(on); }

        bool Active => flow && (flow.Current == FlowController.State.Miniature || flow.Current == FlowController.State.Scene) && director && director.Registry && director.Registry.EnvironmentRoot && director.Registry.EnvironmentRoot.gameObject.activeInHierarchy;

        /// Where the pointing ray starts and heads. Hands use the SDK's pointer pose (a stable ray from the wrist through the
        /// index); controllers use the hand anchor. The right hand leads; the left stands in when the right is not seen.
        bool Pointer(out Ray ray)
        {
            ray = default;
#if FABLE_META_XR
            foreach (var right in rightSource ? new[] { true, false } : new[] { false, true })
            {
                var hand = right ? reader.RightHand : reader.LeftHand; var anchor = right ? reader.RightPointer : reader.LeftPointer;
                if (hand && hand.IsTracked && hand.IsPointerPoseValid && hand.PointerPose) { ray = new Ray(hand.PointerPose.position, hand.PointerPose.forward); rightSource = right; return true; }
                var ctrl = right ? OVRInput.Controller.RTouch : OVRInput.Controller.LTouch;
                if (anchor && OVRInput.IsControllerConnected(ctrl) && (hand == null || !hand.IsTracked)) { ray = new Ray(anchor.position, anchor.forward); rightSource = right; return true; }
            }
#endif
            return false;
        }

        void Update()
        {
            if (!Active) { hit = HitKind.None; Show(false); return; }
            Aim();
            Walk();
        }

        void Aim()
        {
            hit = HitKind.None;
            if (!Pointer(out var ray)) { Show(false); return; }
            // only a hand held up and pointed roughly ahead or down shows the ray; a hand resting in the lap does not
            var fwd = Vector3.ProjectOnPlane(head.forward, Vector3.up).normalized;
            if (Vector3.Dot(Vector3.ProjectOnPlane(ray.direction, Vector3.up).normalized, fwd) < 0.1f || ray.origin.y < head.position.y - 0.55f) { Show(false); return; }
            var reg = director.Registry; float scale = reg.EnvironmentRoot.lossyScale.x;
            float best = float.PositiveInfinity; Vector3 point = Vector3.zero;
            // the little door, when the room shows it
            var little = reg.Asset("door.little");
            if (little && little.gameObject.activeInHierarchy && Bounds(little, out var lb) && lb.IntersectRay(ray, out float dl) && dl < best) { best = dl; point = ray.GetPoint(dl); hit = HitKind.LittleDoor; }
            // the big doors are locked
            foreach (var r in reg.EnvironmentRoot.GetComponentsInChildren<Renderer>())
                if (r.name.StartsWith("MESH_Door") && !r.name.Contains("Little") && r.bounds.IntersectRay(ray, out float dd) && dd < best) { best = dd; point = ray.GetPoint(dd); hit = HitKind.LockedDoor; }
            // the floor: the room's floor plane, within the room's footprint
            float floorY = reg.Centre.position.y;
            if (ray.direction.y < -0.02f)
            {
                float t = (floorY - ray.origin.y) / ray.direction.y;
                if (t > 0 && t < best && t < 60f)
                {
                    var p = ray.GetPoint(t);
                    if (Footprint(out var fb) && fb.Contains(new Vector3(p.x, fb.center.y, p.z))) { best = t; point = p; hit = HitKind.Floor; }
                }
            }
            if (hit == HitKind.None) { Show(false); return; }
            hitPoint = point;
            Show(true);
            line.SetPosition(0, ray.origin); line.SetPosition(1, point);
            var c = hit == HitKind.Floor ? Brass : hit == HitKind.LittleDoor ? Go : Locked;
            lineMat.color = c; discMat.color = c;
            float dia = TeleportDiscMetres * Mathf.Clamp(scale, 0.05f, 4f);
            disc.position = point + Vector3.up * 0.004f * Mathf.Max(scale, 0.2f); disc.localScale = new Vector3(dia, 0.002f * Mathf.Max(scale, 0.2f), dia); disc.rotation = Quaternion.identity;
            if (hit != HitKind.Floor) { disc.localScale = Vector3.one * 0.03f * Mathf.Max(scale, 0.5f); }
        }

        static bool Bounds(Transform t, out Bounds b)
        {
            b = default; bool any = false;
            foreach (var r in t.GetComponentsInChildren<Renderer>()) { if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds); }
            return any;
        }

        bool Footprint(out Bounds b)
        {
            b = default; bool any = false;
            foreach (var r in director.Registry.EnvironmentRoot.GetComponentsInChildren<Renderer>())
            {
                if (!r.name.StartsWith("MESH_")) continue;
                if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
            }
            if (any) b.Expand(new Vector3(0, 1000f, 0));   // a column: only x and z matter
            return any;
        }

        /// The right tap, when the ray is on something. Returns true when it consumed the pinch.
        bool Activate()
        {
            if (!Active || hit == HitKind.None) return false;
            switch (hit)
            {
                case HitKind.Floor:
                    if (flow.Current == FlowController.State.Miniature) { flow.ExpandAt(hitPoint); }
                    else { var delta = hitPoint - new Vector3(head.position.x, hitPoint.y, head.position.z); rig.position += new Vector3(delta.x, 0, delta.z); }
                    Debug.Log($"[Fable] go: {flow.Current} -> {hitPoint}");
                    return true;
                case HitKind.LittleDoor:
                    Debug.Log("[Fable] through the little door");
                    if (!flow.OpenLinkedPassage()) director.Clips.Play("door.little", "door.rattle", 0.8f, false);
                    return true;
                case HitKind.LockedDoor:
                    director.Audio.Play("sfx.door-locked-rattle", "hall.centre", 0.6f);
                    return true;
            }
            return false;
        }

        /// Arm-swing walking (both hands pumping) or the controller thumbstick. Full-scale room only.
        void Walk()
        {
            if (flow.Current != FlowController.State.Scene || !rig) return;
            var fwd = Vector3.ProjectOnPlane(head.forward, Vector3.up).normalized; var right = Vector3.Cross(Vector3.up, fwd);
            Vector3 move = Vector3.zero;
#if FABLE_META_XR
            var stick = OVRInput.Get(OVRInput.Axis2D.PrimaryThumbstick, OVRInput.Controller.RTouch) + OVRInput.Get(OVRInput.Axis2D.PrimaryThumbstick, OVRInput.Controller.LTouch);
            if (stick.sqrMagnitude > 0.04f) move = (fwd * stick.y + right * stick.x) * WalkSpeed;
            bool hands = reader.LeftPointer && reader.RightPointer && reader.LeftHand && reader.RightHand && reader.LeftHand.IsTracked && reader.RightHand.IsTracked && !reader.LeftPinching && !reader.RightPinching;
            if (hands)
            {
                var l = reader.LeftPointer.position; var r = reader.RightPointer.position;
                if (hadHands && Time.deltaTime > 0)
                {
                    float vl = (l.y - lastL.y) / Time.deltaTime, vr = (r.y - lastR.y) / Time.deltaTime;
                    bool opposite = Mathf.Sign(vl) != Mathf.Sign(vr);
                    float pump = (Mathf.Abs(vl) + Mathf.Abs(vr)) * 0.5f;
                    float target = opposite && pump > SwingThreshold ? Mathf.Clamp(pump * 0.9f, 0.4f, WalkSpeed) : 0f;
                    swing = Mathf.Lerp(swing, target, Time.deltaTime * (target > swing ? 6f : 3f));
                }
                lastL = l; lastR = r; hadHands = true;
            }
            else { hadHands = false; swing = Mathf.Lerp(swing, 0, Time.deltaTime * 3f); }
            if (swing > 0.05f) move += fwd * swing;
#endif
            if (move.sqrMagnitude > 0) rig.position += move * Time.deltaTime;
        }
    }
}
