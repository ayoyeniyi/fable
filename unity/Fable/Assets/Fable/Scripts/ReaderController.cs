// Hand-controlled story progression, seated, hands only.
//   right pinch tap        next beat          left pinch tap        previous beat
//   right pinch and drag   scroll the story (5 cm = one sentence; up or right = forward, down or left = back)
//   both hands pinch, quick release   toggle miniature / immersive      (one hand: hold the right pinch ~1 s)
//   both hands pinch, hold 1 s        close the scene, back to the page  (one hand: hold the left pinch ~1 s)
// Controllers (index triggers) mirror the pinches so testers without hand tracking are not stuck.
// Keyboard fallback in the editor: Space / Backspace, arrows, Tab (toggle), Escape (return).
using System;
using UnityEngine;

namespace Fable
{
    public class ReaderController : MonoBehaviour
    {
        public event Action Next, Previous, ReturnToReading, Select, ToggleView;
        public event Action<int> Scrub;                 // +1 / -1 per scrub step while dragging
        public float TapSeconds = 0.35f, DragStepMetres = 0.05f, HoldToReturn = 1.0f, HoldOneHand = 0.9f;
        bool rHeld, lHeld;   // a one-hand hold already fired for this pinch

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
        string lastMode;

        float rDown = -1, lDown = -1, bothDown = -1; bool bothFired, rDragging; Vector3 rStart, rLast; float rAccum;
        bool suppressed;   // a pinch that grabbed a prop is not also a page turn or a scrub

        /// Called when a pinch picks something up (or puts it down): that pinch no longer counts as a tap or drag.
        public void SuppressCurrentPinch() { suppressed = true; rDown = lDown = bothDown = -1; rDragging = false; }

        bool Pinch(bool left, out Vector3 pos)
        {
            pos = Vector3.zero; bool p = false;
#if FABLE_META_XR
            var h = left ? LeftHand : RightHand; var a = left ? LeftPointer : RightPointer;
            if (h && h.IsTracked) { p = h.GetFingerIsPinching(OVRHand.HandFinger.Index) && h.GetFingerConfidence(OVRHand.HandFinger.Index) == OVRHand.TrackingConfidence.High; if (a) pos = a.position; }
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
            bool r = Pinch(false, out var rPos), l = Pinch(true, out _);
            LeftPinching = l; RightPinching = r;
#if FABLE_META_XR
            bool handsSeen = (LeftHand && LeftHand.IsTracked) || (RightHand && RightHand.IsTracked);
            bool ctrlSeen = OVRInput.IsControllerConnected(OVRInput.Controller.LTouch) || OVRInput.IsControllerConnected(OVRInput.Controller.RTouch);
            InputMode = handsSeen ? "hands" : ctrlSeen ? "controllers" : "none";
#elif UNITY_EDITOR || UNITY_STANDALONE
            InputMode = "keyboard";
#endif
            if (InputMode != lastMode) { lastMode = InputMode; Debug.Log($"[Fable] input: {InputMode}"); ModeChanged?.Invoke(InputMode); }
            float now = Time.time;
            if (suppressed) { if (!l && !r) suppressed = false; return; }

            // both hands: quick release toggles the view, a held pinch closes the scene
            if (l && r)
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
                if (!rDragging && !rHeld && now - rDown > HoldOneHand) { rHeld = true; ToggleView?.Invoke(); }
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
                if (!rDragging && !rHeld && now - rDown < TapSeconds) { Next?.Invoke(); Select?.Invoke(); }
                rDown = -1; rDragging = false; rHeld = false;
            }

            // left hand: tap = previous, hold = close the scene
            if (l && lDown < 0) { lDown = now; lHeld = false; }
            else if (l && !lHeld && now - lDown > HoldOneHand) { lHeld = true; ReturnToReading?.Invoke(); }
            else if (!l && lDown >= 0) { if (!lHeld && now - lDown < TapSeconds) Previous?.Invoke(); lDown = -1; lHeld = false; }
        }
    }
}
