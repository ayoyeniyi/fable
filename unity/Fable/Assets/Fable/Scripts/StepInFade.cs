// A short fade to black and back around a step into a chapter's place (and back out of it): a black shell around the
// reader's head (Fable/ScreenFade, drawn over everything), so the move to the place's viewpoint is never seen as a jump.
using System.Collections;
using UnityEngine;

namespace Fable
{
    public static class StepInFade
    {
        public const float OutSeconds = 0.6f, InSeconds = 0.8f;
        static GameObject shell; static Material mat;
        static readonly int ColorId = Shader.PropertyToID("_Color");
        public static float Alpha { get; private set; }

        static void Ensure(Transform head)
        {
            if (shell && shell.transform.parent == head) return;
            if (shell) Object.Destroy(shell);
            var tmpl = Resources.Load<Material>("SceneRooms/Fade");
            mat = tmpl ? new Material(tmpl) : new Material(Shader.Find("Fable/ScreenFade"));
            shell = GameObject.CreatePrimitive(PrimitiveType.Sphere); shell.name = "StepInFade";
            Object.Destroy(shell.GetComponent<Collider>());
            shell.transform.SetParent(head, false); shell.transform.localPosition = Vector3.zero; shell.transform.localScale = Vector3.one * 0.3f;
            var r = shell.GetComponent<MeshRenderer>(); r.sharedMaterial = mat; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            Set(Alpha);
        }

        static void Set(float a)
        {
            Alpha = a;
            if (!mat) return;
            mat.SetColor(ColorId, new Color(0, 0, 0, a));
            if (shell) shell.SetActive(a > 0.001f);
        }

        /// Fade to black (to = 1) or back (to = 0) over the given seconds.
        public static IEnumerator To(Transform head, float to, float seconds)
        {
            if (!head) yield break;
            Ensure(head);
            float from = Alpha;
            for (float t = 0; t < seconds; t += Time.unscaledDeltaTime) { Set(Mathf.Lerp(from, to, Mathf.SmoothStep(0, 1, t / seconds))); yield return null; }
            Set(to);
        }

        /// Black at once (after a scene load that should open dark, then fade in).
        public static void Black(Transform head) { if (!head) return; Ensure(head); Set(1); }
    }
}
