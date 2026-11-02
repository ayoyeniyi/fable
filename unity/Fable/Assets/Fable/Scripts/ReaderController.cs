// Hand input for a reader who stays in one place, seated or standing. Every essential action has a visible control
// (the page's buttons, the highlight menu, the view toolbar); the pinches below are the only gestures, and none of
// them needs two hands, a hold or a pull.
//   right pinch tap        next page / next beat            left pinch tap        previous page / beat
//   right pinch and drag   scroll the story (5 cm = one sentence; up or right = forward, down or left = back)
// A pinch that starts on a control (toolbar button, panel handle, a Peek model) is claimed by it: it fires that
// control once, on the pinch's first frame, and is never also a page turn, a scroll or a highlight. Holding the
// pinch never repeats the action.
// The old shortcuts (both hands pinch = step in / close; hold right = step in; hold left = close; left drag = turn)
// are off by default: readers triggered them by accident. LegacyGestures turns them back on for testing.
// Controllers (index triggers) mirror the pinches. Keyboard in the editor: Space / Backspace, arrows, Escape (return).
using System;
using UnityEngine;

namespace Fable
{
    public class ReaderController : MonoBehaviour
    {
        public event Action Next, Previous, ReturnToReading, Select, ToggleView;
        public event Action<int> Scrub;                 // +1 / -1 per scrub step while dragging
        public event Action<int> Turn;                  // +1 (right) / -1 (left) per step of a left-hand sideways drag
        public event Action<bool> PinchBegan, PinchEnded;   // raw pinch edges per hand (true = right), before taps and holds are judged
        public float TapSeconds = 0.35f, DragStepMetres = 0.05f, TurnStepMetres = 0.10f, HoldToReturn = 1.0f, HoldOneHand = 0.9f;
        /// The two-hand, hold and drag-to-turn shortcuts of earlier builds. Off: every action has a visible control now.
        public bool LegacyGestures = false;
        bool rHeld, lHeld;   // a one-hand hold already fired for this pinch

        /// Controls that take a pinch before the page does (the view toolbar, the panel handles, a Peek model). Asked on
        /// the first frame of a pinch, in order; the first to return true owns that pinch until it is released.
        public readonly System.Collections.Generic.List<Func<bool, bool>> Claimers = new();
        /// The hand whose current pinch a control claimed (true = right), or null.
        public bool? ClaimedHand { get; private set; }
        public bool Claimed(bool right) => ClaimedHand == right;

#if FABLE_META_XR
        public OVRHand LeftHand, RightHand;
        public Transform LeftPointer, RightPointer;     // hand anchors (position source for scrubbing)
#endif
        public bool LeftPinching { get; private set; }
        public bool RightPinching { get; private set; }
        /// "hands", "controllers" or "none": what the headset is tracking right now. Shown on the page and logged, so a
        /// tester can tell at once whether their hands are being seen. Hands win when both are present.
        public string InputMode { get; private set; } = "none";
        public event Action<string> ModeChanged;
        /// Set by Locomotion: a right tap while the ray rests on something goes there instead of turning the page.
        public Func<bool> TapInterceptor;
        string lastMode;

        float rDown = -1, lDown = -1, bothDown = -1; bool bothFired, rDragging, lDragging; Vector3 rStart, rLast, lStart, lLast; float rAccum, lAccum;
        bool suppressed;   // a pinch that grabbed a prop is not also a page turn or a scrub
        bool wasR, wasL;

#if FABLE_META_XR
        /// The ray a hand or controller points along, in world space, shared by the page pointer and the room pointer.
        /// Hands: the system pointer pose (the ray the Quest's own menus use). The SDK reports it in tracking-space
        /// coordinates and leaves it unparented, so it is mapped through the rig's tracking space here; read raw, it was
        /// off by the rig's offset and hands never reached the page while controllers did. While the system has no valid
        /// pointer pose for a tracked hand, the ray runs from the eyes through the hand instead, which is what a first-time
        /// pointer expects anyway: the target sits behind your hand.
        public bool PointRay(bool right, out Ray ray)
        {
            ray = default;
            var hand = right ? RightHand : LeftHand; var anchor = right ? RightPointer : LeftPointer;
            var space = anchor ? anchor.parent : null;
            if (hand && hand.IsTracked && hand.PointerPose)
            {
                var pp = hand.PointerPose; Vector3 pos, dir;
                if (pp.parent == null && space) { pos = space.TransformPoint(pp.localPosition); dir = space.rotation * pp.localRotation * Vector3.forward; }
                else { pos = pp.position; dir = pp.forward; }
                if (hand.IsPointerPoseValid && dir.sqrMagnitude > 0.5f) { ray = new Ray(pos, dir.normalized); return true; }
                var head = Camera.main ? Camera.main.transform : null;
                if (head)
                {
                    var from = pp.localPosition.sqrMagnitude > 1e-6f ? pos : (anchor ? anchor.position : pos);
                    var d = from - head.position;
                    if (d.sqrMagnitude > 0.01f) { ray = new Ray(head.position, d.normalized); return true; }
                }
            }
            var ctrl = right ? OVRInput.Controller.RTouch : OVRInput.Controller.LTouch;
            if (anchor && OVRInput.IsControllerConnected(ctrl) && (hand == null || !hand.IsTracked)) { ray = new Ray(anchor.position, anchor.forward); return true; }
            return false;
        }

        float nextDiag;
        /// A line in the log every few seconds for the first minutes, so a tester can see what the headset makes of each hand.
        void Diagnose()
        {
            if (Time.time < nextDiag || Time.time > 240f) return; nextDiag = Time.time + 3f;
            foreach (var right in new[] { true, false })
            {
                var hand = right ? RightHand : LeftHand; var anchor = right ? RightPointer : LeftPointer;
                if (!hand) { Debug.Log($"[Fable] point {(right ? "R" : "L")}: no OVRHand"); continue; }
                var pp = hand.PointerPose; bool got = PointRay(right, out var r);
                Debug.Log($"[Fable] point {(right ? "R" : "L")}: tracked={hand.IsTracked} valid={hand.IsPointerPoseValid} conf={hand.HandConfidence} ppLocal={(pp ? pp.localPosition.ToString("F2") : "-")} ppParent={(pp && pp.parent ? pp.parent.name : "none")} anchor={(anchor ? anchor.position.ToString("F2") : "-")} head={(Camera.main ? Camera.main.transform.position.ToString("F2") : "-")} ray={(got ? r.origin.ToString("F2") + "->" + r.direction.ToString("F2") : "none")}");
            }
        }
#endif

        /// A pinch starting or ending. A control may claim a starting pinch; a claimed pinch is not reported as a raw
        /// pinch either (so a grab or a book on the shelf does not also react to it).
        void Edge(bool right, bool down)
        {
            if (down)
            {
                foreach (var c in Claimers)
                    if (c != null && c(right)) { ClaimedHand = right; SuppressCurrentPinch(); return; }
                PinchBegan?.Invoke(right);
            }
            else
            {
                if (ClaimedHand == right) { ClaimedHand = null; return; }
                PinchEnded?.Invoke(right);
            }
        }

        /// Called when a pinch picks something up (or puts it down): that pinch no longer counts as a tap or drag.
        public void SuppressCurrentPinch() { suppressed = true; rDown = lDown = bothDown = -1; rDragging = false; }

        bool Pinch(bool left, out Vector3 pos)
        {
            pos = Vector3.zero; bool p = false;
#if FABLE_META_XR
            var h = left ? LeftHand : RightHand; var a = left ? LeftPointer : RightPointer;
            if (h && h.IsTracked)
            {
                p = h.GetFingerIsPinching(OVRHand.HandFinger.Index) && h.GetFingerConfidence(OVRHand.HandFinger.Index) == OVRHand.TrackingConfidence.High;
                p |= h.GetFingerIsPinching(OVRHand.HandFinger.Middle) && h.GetFingerConfidence(OVRHand.HandFinger.Middle) == OVRHand.TrackingConfidence.High;   // a closing hand
                if (a) pos = a.position;
            }
            var ctrl = left ? OVRInput.Controller.LTouch : OVRInput.Controller.RTouch;
            if (OVRInput.Get(OVRInput.Button.PrimaryIndexTrigger, ctrl)) { p = true; pos = OVRInput.GetLocalControllerPosition(ctrl); if (a && a.parent) pos = a.parent.TransformPoint(pos); }
#endif
#if UNITY_EDITOR || UNITY_STANDALONE
            var kb = UnityEngine.InputSystem.Keyboard.current;
            if (kb != null)
            {
                if (!left) p |= kb.spaceKey.isPressed || kb.rightArrowKey.isPressed;
                else p |= kb.backspaceKey.isPressed || kb.leftArrowKey.isPressed;
                if (!left && kb.escapeKey.wasPressedThisFrame) ReturnToReading?.Invoke();
                if (!left && kb.tabKey.wasPressedThisFrame) ToggleView?.Invoke();
                if (!left && kb.enterKey.wasPressedThisFrame) Select?.Invoke();
            }
#endif
            return p;
        }

        void Update()
        {
            bool r = Pinch(false, out var rPos), l = Pinch(true, out var lPos);
            LeftPinching = l; RightPinching = r;
#if FABLE_META_XR
            bool handsSeen = (LeftHand && LeftHand.IsTracked) || (RightHand && RightHand.IsTracked);
            bool ctrlSeen = OVRInput.IsControllerConnected(OVRInput.Controller.LTouch) || OVRInput.IsControllerConnected(OVRInput.Controller.RTouch);
            InputMode = handsSeen ? "hands" : ctrlSeen ? "controllers" : "none";
#elif UNITY_EDITOR || UNITY_STANDALONE
            InputMode = "keyboard";
#endif
            if (InputMode != lastMode) { lastMode = InputMode; Debug.Log($"[Fable] input: {InputMode}"); ModeChanged?.Invoke(InputMode); }
            if (r != wasR) { wasR = r; Edge(true, r); }
            if (l != wasL) { wasL = l; Edge(false, l); }
#if FABLE_META_XR
            Diagnose();
#endif
            float now = Time.time;
            if (suppressed) { if (!l && !r) suppressed = false; return; }

            // both hands: quick release toggles the view, a held pinch closes the scene
            if (LegacyGestures && l && r)
            {
                if (bothDown < 0) { bothDown = now; bothFired = false; }
                else if (!bothFired && now - bothDown > HoldToReturn) { bothFired = true; ReturnToReading?.Invoke(); }
                rDown = lDown = -1; rDragging = false;
                return;
            }
            if (bothDown >= 0)
            {
                if (!bothFired && now - bothDown < 0.6f) ToggleView?.Invoke();
                bothDown = -1; rDown = lDown = -1; return;
            }

            // right hand: tap = next, drag = scrub
            if (r && rDown < 0) { rDown = now; rStart = rLast = rPos; rAccum = 0; rDragging = false; rHeld = false; }
            else if (r)
            {
                var moved = rPos - rStart;
                if (!rDragging && moved.magnitude > 0.02f) rDragging = true;
                if (LegacyGestures && !rDragging && !rHeld && now - rDown > HoldOneHand) { rHeld = true; ToggleView?.Invoke(); }
                if (rDragging)
                {
                    // one-hand scrolling, as on a phone: a pinched hand moving up (or to the right) scrolls the story forward,
                    // down (or left) scrolls back, 5 cm per sentence, along whichever axis the hand moves most
                    var step = rPos - rLast; var right = Camera.main ? Camera.main.transform.right : Vector3.right; right.y = 0; right.Normalize();
                    float dx = Vector3.Dot(step, right), dy = step.y;
                    rAccum += Mathf.Abs(dy) > Mathf.Abs(dx) ? dy : dx;
                    while (rAccum > DragStepMetres) { rAccum -= DragStepMetres; Scrub?.Invoke(+1); }
                    while (rAccum < -DragStepMetres) { rAccum += DragStepMetres; Scrub?.Invoke(-1); }
                    rLast = rPos;
                }
            }
            else if (rDown >= 0)
            {
                if (!rDragging && !rHeld && now - rDown < TapSeconds && !(TapInterceptor != null && TapInterceptor())) { Next?.Invoke(); Select?.Invoke(); }
                rDown = -1; rDragging = false; rHeld = false;
            }

            // left hand: tap = previous, hold = close the scene, sideways drag = turn
            if (l && lDown < 0) { lDown = now; lHeld = false; lDragging = false; lStart = lLast = lPos; lAccum = 0; }
            else if (l)
            {
                if (!lDragging && (lPos - lStart).magnitude > 0.025f) lDragging = true;
                if (LegacyGestures && !lDragging && !lHeld && now - lDown > HoldOneHand) { lHeld = true; ReturnToReading?.Invoke(); }
                if (LegacyGestures && lDragging)
                {
                    var right = Camera.main ? Camera.main.transform.right : Vector3.right; right.y = 0; right.Normalize();
                    lAccum += Vector3.Dot(lPos - lLast, right);
                    while (lAccum > TurnStepMetres) { lAccum -= TurnStepMetres; Turn?.Invoke(+1); }
                    while (lAccum < -TurnStepMetres) { lAccum += TurnStepMetres; Turn?.Invoke(-1); }
                    lLast = lPos;
                }
            }
            else if (lDown >= 0) { if (!lDragging && !lHeld && now - lDown < TapSeconds) Previous?.Invoke(); lDown = -1; lHeld = false; lDragging = false; }
        }
    }
}
