// Hand-controlled story progression, seated, hands only.
//   right pinch tap        next beat          left pinch tap        previous beat
//   right pinch and drag   scrub (6 cm = one beat, either direction)
//   both hands pinch, quick release   toggle miniature / immersive
//   both hands pinch, hold 1 s        close the scene, back to the page
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
        public float TapSeconds = 0.35f, DragStepMetres = 0.06f, HoldToReturn = 1.0f;

#if FABLE_META_XR
        public OVRHand LeftHand, RightHand;
        public Transform LeftPointer, RightPointer;     // hand anchors (position source for scrubbing)
#endif
        public bool LeftPinching { get; private set; }
        public bool RightPinching { get; private set; }

        float rDown = -1, lDown = -1, bothDown = -1; bool bothFired, rDragging; Vector3 rStart, rLast; float rAccum;

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
            float now = Time.time;

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
            if (r && rDown < 0) { rDown = now; rStart = rLast = rPos; rAccum = 0; rDragging = false; }
            else if (r)
            {
                var moved = rPos - rStart; moved.y = 0;
                if (!rDragging && moved.magnitude > 0.02f) rDragging = true;
                if (rDragging)
                {
                    var step = rPos - rLast; var fwd = Camera.main ? Camera.main.transform.right : Vector3.right; fwd.y = 0; fwd.Normalize();
                    rAccum += Vector3.Dot(step, fwd);
                    while (rAccum > DragStepMetres) { rAccum -= DragStepMetres; Scrub?.Invoke(+1); }
                    while (rAccum < -DragStepMetres) { rAccum += DragStepMetres; Scrub?.Invoke(-1); }
                    rLast = rPos;
                }
            }
            else if (rDown >= 0)
            {
                if (!rDragging && now - rDown < TapSeconds) { Next?.Invoke(); Select?.Invoke(); }
                rDown = -1; rDragging = false;
            }

            // left hand: tap = previous
            if (l && lDown < 0) lDown = now;
            else if (!l && lDown >= 0) { if (now - lDown < TapSeconds) Previous?.Invoke(); lDown = -1; }
        }
    }
}
