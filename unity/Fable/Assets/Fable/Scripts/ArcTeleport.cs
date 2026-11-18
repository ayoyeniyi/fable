// Walk about a reading room or a chapter's place: point a hand at the floor and an arc curves out from it to a ring
// where you would stand; pinch and you are there (a blink of black, the page and the bar come along).
//   Only a hand held up, pointing ahead and down at open floor, shows the arc; pointing at the page, its handles, a Peek
//   model or the bar leaves the pinch to them, and a hand resting in the lap shows nothing.
//   Landing needs floor that faces up, near the height of the floor you are on, with head room above it (not under a
//   table or a beam). Rooms with readable meshes get colliders once (lazily); otherwise the floor is the plane you
//   stand on, within the room's footprint.
// The older passage scenes keep their own pointing (Locomotion): this one stays off while that one is active.
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace Fable
{
    public class ArcTeleport : MonoBehaviour
    {
        public float Speed = 7.5f, Gravity = 9.8f, StepSeconds = 0.04f, MaxRange = 14f, MinRange = 0.6f, StepUpDown = 0.6f, HeadRoom = 1.7f;
        public Color Ok = new(0.95f, 0.72f, 0.30f, 0.9f);
        const int MaxSteps = 60;

        FlowController flow; ReaderController input; Transform head, rig;
        LineRenderer line; Transform ring; Material mat;
        readonly Vector3[] pts = new Vector3[MaxSteps + 1]; int count;
        bool valid, aimRight = true, busy; Vector3 target;
        bool collidersBuilt, havePhysics; Bounds footprint; bool haveFootprint; string builtFor;

        public bool Showing => valid;

        public void Init(FlowController f, ReaderController r, Transform h, Transform rigRoot)
        {
            flow = f; input = r; head = h; rig = rigRoot;
            if (!input.Claimers.Contains(Claim)) input.Claimers.Add(Claim);
            if (line) return;   // set up already (the flow sets up its controls again after a room change)
            var shader = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
            mat = new Material(shader) { color = Ok };
            line = new GameObject("TeleportArc").AddComponent<LineRenderer>(); line.transform.SetParent(transform, false);
            line.material = mat; line.useWorldSpace = true; line.widthMultiplier = 0.012f; line.numCapVertices = 2; line.positionCount = 0;
            line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; line.receiveShadows = false;
            ring = GameObject.CreatePrimitive(PrimitiveType.Cylinder).transform; Destroy(ring.GetComponent<Collider>()); ring.name = "TeleportRing";
            ring.SetParent(transform, false); ring.localScale = new Vector3(0.45f, 0.004f, 0.45f);
            var rr = ring.GetComponent<Renderer>(); rr.material = mat; rr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            Show(false);
        }
        void OnDestroy() { if (input) input.Claimers.Remove(Claim); }

        void Show(bool on) { if (line) line.enabled = on; if (ring) ring.gameObject.SetActive(on); }

        bool Allowed()
        {
            if (!flow || !head || !rig || busy) return false;
            if (flow.Move && flow.Move.IsActive) return false;   // a passage scene: its own pointing
            return flow.InPlace || flow.Current == FlowController.State.Reading;
        }

        /// Something else wants this hand's ray: the page, its handles and arrows, a Peek model, the bar.
        bool RayTaken(bool right)
        {
            var p = flow.Pointer;
            if (p && p.OnPage(right, out _)) return true;
            if (p) foreach (var t in p.Targets) if (t(right).HasValue) return true;
            if (ViewControls.Instance && ViewControls.Instance.RayOnBar(right)) return true;
            return false;
        }

        void Update()
        {
            valid = false;
            if (!Allowed()) { Show(false); return; }
            EnsureColliders();
            foreach (var right in aimRight ? new[] { true, false } : new[] { false, true })
            {
                if (!input.PointRay(right, out var ray)) continue;
                // a hand held up and pointing ahead and down; not one resting in the lap or pointing behind
                var fwd = Vector3.ProjectOnPlane(head.forward, Vector3.up).normalized;
                if (ray.origin.y < head.position.y - 0.6f || ray.direction.y > 0.35f || ray.direction.y < -0.97f) continue;
                if (Vector3.Dot(Vector3.ProjectOnPlane(ray.direction, Vector3.up).normalized, fwd) < 0.2f) continue;
                if (RayTaken(right)) continue;
                if (Trace(ray)) { aimRight = right; valid = true; break; }
            }
            Show(valid);
            if (!valid) return;
            line.positionCount = count; line.SetPositions(pts);
            ring.position = target + Vector3.up * 0.01f; ring.rotation = Quaternion.identity;
            float pulse = 1f + 0.06f * Mathf.Sin(Time.time * 6f); ring.localScale = new Vector3(0.45f * pulse, 0.004f, 0.45f * pulse);
        }

        /// The arc a thrown point would follow from the hand; true when it lands on floor you could stand on.
        bool Trace(Ray ray)
        {
            float floorY = rig.position.y;
            Vector3 p = ray.origin, v = ray.direction.normalized * Speed;
            pts[0] = p; count = 1;
            for (int i = 0; i < MaxSteps; i++)
            {
                var next = p + v * StepSeconds; v += Vector3.down * Gravity * StepSeconds;
                if (Hit(p, next, floorY, out var at, out bool stand))
                {
                    pts[count++] = at;
                    if (!stand) return false;
                    var flat = at - head.position; flat.y = 0;
                    if (flat.magnitude < MinRange || flat.magnitude > MaxRange) return false;
                    target = at; return true;
                }
                pts[count++] = next; p = next;
                if (p.y < floorY - 3f) return false;
            }
            return false;
        }

        bool Hit(Vector3 a, Vector3 b, float floorY, out Vector3 at, out bool stand)
        {
            at = b; stand = false;
            var d = b - a; float len = d.magnitude; if (len < 1e-5f) return false;
            if (havePhysics)
            {
                if (!Nearest(a, d / len, len, out var h)) return false;
                at = h.point;
                stand = h.normal.y > 0.8f && Mathf.Abs(h.point.y - floorY) < StepUpDown
                        && !Nearest(h.point + Vector3.up * 0.05f, Vector3.up, HeadRoom, out _);
                return true;
            }
            // no colliders: the floor you stand on, inside the room's footprint
            if ((a.y - floorY) * (b.y - floorY) > 0) return false;
            float t = (a.y - floorY) / (a.y - b.y); at = Vector3.Lerp(a, b, t);
            stand = !haveFootprint || footprint.Contains(new Vector3(at.x, footprint.center.y, at.z));
            return true;
        }

        readonly RaycastHit[] hits = new RaycastHit[16];
        /// The nearest hit that is not the reader's own rig (hand colliders) or the page.
        bool Nearest(Vector3 from, Vector3 dir, float len, out RaycastHit best)
        {
            best = default; float bd = float.PositiveInfinity;
            int n = Physics.RaycastNonAlloc(from, dir, hits, len, ~0, QueryTriggerInteraction.Ignore);
            for (int i = 0; i < n; i++)
            {
                var t = hits[i].collider.transform;
                if (t.IsChildOf(rig) || (flow.Panel && t.IsChildOf(flow.Panel.transform))) continue;
                if (hits[i].distance < bd) { bd = hits[i].distance; best = hits[i]; }
            }
            return bd < float.PositiveInfinity;
        }

        /// Pinch while the arc shows: go there.
        bool Claim(bool right)
        {
            if (!valid || right != aimRight || !Allowed()) return false;
            StartCoroutine(Go(target));
            return true;
        }

        IEnumerator Go(Vector3 to)
        {
            busy = true; Show(false);
            yield return StepInFade.To(head, 1, 0.09f);
            var headFloor = new Vector3(head.position.x, rig.position.y, head.position.z);
            var delta = new Vector3(to.x - headFloor.x, to.y - rig.position.y, to.z - headFloor.z);
            rig.position += delta;
            if (flow.Panel && flow.Panel.gameObject.activeInHierarchy) flow.Panel.Shift(delta);
            if (ViewControls.Instance) ViewControls.Instance.Snap();
            Debug.Log($"[Fable] teleport {delta.magnitude:F1} m");
            yield return StepInFade.To(head, 0, 0.16f);
            busy = false;
        }

        /// Colliders for the room's solid meshes, once per scene (sky, far backdrops and the reader's own things left out).
        void EnsureColliders()
        {
            var scene = gameObject.scene.name + (flow.InPlace ? ":place" : "");
            if (collidersBuilt && builtFor == scene) return;
            collidersBuilt = true; builtFor = scene; havePhysics = false; haveFootprint = false;
            int made = 0, solid = 0;
            foreach (var r in FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
            {
                if (!r.enabled || !r.gameObject.activeInHierarchy || FlowController.IsBackdrop(r.name) || r.name.Contains("Sky")) continue;
                if (r.transform.IsChildOf(rig) || r.transform.IsChildOf(transform) || (flow.Panel && r.transform.IsChildOf(flow.Panel.transform))) continue;
                if (r.GetComponentInParent<Canvas>()) continue;
                if (!haveFootprint) { footprint = r.bounds; haveFootprint = true; } else footprint.Encapsulate(r.bounds);
                if (r.GetComponent<Collider>()) { solid++; continue; }
                var mf = r.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh || !mf.sharedMesh.isReadable) continue;
                var mc = r.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; made++;
            }
            havePhysics = made + solid > 0;
            if (haveFootprint) footprint.Expand(new Vector3(-0.6f, 0, -0.6f));   // keep landings inside the walls
            Physics.SyncTransforms();
            Debug.Log($"[Fable] teleport: {made} colliders made, {solid} already there ({(havePhysics ? "physics" : "floor plane")})");
        }
    }
}
