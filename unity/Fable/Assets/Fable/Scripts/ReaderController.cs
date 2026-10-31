// Hand-controlled story progression. Right pinch: next beat. Left pinch: previous beat.
// Both hands pinched and held for a second: return to reading. Keyboard fallback in the editor.
using System;
using UnityEngine;

namespace Fable
{
    public class ReaderController : MonoBehaviour
    {
        public event Action Next, Previous, ReturnToReading, Select;
        public float Debounce = 0.45f;
        public float HoldToReturn = 1.0f;

#if FABLE_META_XR
        public OVRHand LeftHand, RightHand;
#endif
        float lastL, lastR, bothSince = -1;
        bool lPrev, rPrev;

        public bool LeftPinching { get; private set; }
        public bool RightPinching { get; private set; }

        void Update()
        {
            bool l = false, r = false;
#if FABLE_META_XR
            if (LeftHand && LeftHand.IsTracked) l = LeftHand.GetFingerIsPinching(OVRHand.HandFinger.Index) && LeftHand.GetFingerConfidence(OVRHand.HandFinger.Index) == OVRHand.TrackingConfidence.High;
            if (RightHand && RightHand.IsTracked) r = RightHand.GetFingerIsPinching(OVRHand.HandFinger.Index) && RightHand.GetFingerConfidence(OVRHand.HandFinger.Index) == OVRHand.TrackingConfidence.High;
            // controllers work too, so a tester without hand tracking is not stuck
            l |= OVRInput.Get(OVRInput.Button.PrimaryIndexTrigger, OVRInput.Controller.LTouch);
            r |= OVRInput.Get(OVRInput.Button.PrimaryIndexTrigger, OVRInput.Controller.RTouch);
#endif
#if UNITY_EDITOR || UNITY_STANDALONE
            var kb = UnityEngine.InputSystem.Keyboard.current;
            if (kb != null) { r |= kb.spaceKey.isPressed || kb.rightArrowKey.isPressed; l |= kb.backspaceKey.isPressed || kb.leftArrowKey.isPressed; if (kb.escapeKey.wasPressedThisFrame) ReturnToReading?.Invoke(); if (kb.enterKey.wasPressedThisFrame) Select?.Invoke(); }
#endif
            LeftPinching = l; RightPinching = r;
            if (l && r)
            {
                if (bothSince < 0) bothSince = Time.time;
                else if (Time.time - bothSince > HoldToReturn) { bothSince = float.PositiveInfinity; ReturnToReading?.Invoke(); }
            }
            else
            {
                bothSince = -1;
                if (r && !rPrev && Time.time - lastR > Debounce) { lastR = Time.time; Next?.Invoke(); Select?.Invoke(); }
                if (l && !lPrev && Time.time - lastL > Debounce) { lastL = Time.time; Previous?.Invoke(); }
            }
            lPrev = l; rPrev = r;
        }
    }
}
