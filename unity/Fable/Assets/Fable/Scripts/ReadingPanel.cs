// The reading surface: a quiet world-space page, EB Garamond, one sentence in focus, the passage around it dimmed.
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;

namespace Fable
{
    public class ReadingPanel : MonoBehaviour
    {
        public TMP_Text Title, Chapter, Body, Hint;
        public Transform Head;
        public float Distance = 1.15f, Height = -0.08f, Side = 0f, Follow = 2.2f;   // Side: metres to the reader's right (negative = left)
        public Color Ink = new(0.13f, 0.11f, 0.09f), Dim = new(0.13f, 0.11f, 0.09f, 0.38f), Paper = new(0.96f, 0.93f, 0.86f);

        /// Size relative to the authored panel (the canvas itself is scaled ~0.001 to turn pixels into metres).
        public float Scale = 1f;
        float baseScale;

        Passage.Scene scene; string currentId;

        void Awake() { baseScale = transform.localScale.x; }

        void LateUpdate()
        {
            transform.localScale = Vector3.one * (baseScale * Scale);
            if (!Head) return;
            var fwd = Vector3.ProjectOnPlane(Head.forward, Vector3.up).normalized;
            if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            var right = Vector3.Cross(Vector3.up, fwd);
            var target = Head.position + fwd * Distance + Vector3.up * Height + right * Side;
            transform.position = Vector3.Lerp(transform.position, target, Time.deltaTime * Follow);
            var look = Quaternion.LookRotation(transform.position - Head.position, Vector3.up);
            transform.rotation = Quaternion.Slerp(transform.rotation, look, Time.deltaTime * Follow);
        }

        public void Show(Passage.Scene s, string sentenceId, string hint)
        {
            scene = s; currentId = sentenceId;
            if (Title) Title.text = s.Title;
            if (Chapter) Chapter.text = "Chapter " + s.Chapter;
            if (Hint) Hint.text = hint;
            if (!Body) return;
            // Longer passages do not fit the page: show the stretch around the current sentence, fitted to the page,
            // with an ellipsis where earlier or later text is left out. Truncate is only the last guard.
            var items = new System.Collections.Generic.List<(Passage.Sentence s, bool paraEnd)>();
            foreach (var p in s.Paragraphs) for (int i = 0; i < p.Count; i++) items.Add((p[i], i == p.Count - 1));
            int cur = Mathf.Max(0, items.FindIndex(x => x.s.Id == sentenceId));
            string dim = ColorUtility.ToHtmlStringRGBA(Dim), ink = ColorUtility.ToHtmlStringRGBA(Ink);
            string Build(int a, int b)
            {
                var sb = new StringBuilder();
                if (a > 0) sb.Append($"<color=#{dim}>\u2026 </color>");
                for (int i = a; i <= b; i++)
                {
                    bool c = items[i].s.Id == sentenceId;
                    sb.Append(c ? $"<color=#{ink}><b>" : $"<color=#{dim}>").Append(items[i].s.Text).Append(c ? "</b></color> " : "</color> ");
                    if (items[i].paraEnd && i < b) sb.Append("\n\n");
                }
                if (b < items.Count - 1) sb.Append($"<color=#{dim}>\u2026</color>");
                return sb.ToString().TrimEnd();
            }
            bool Fits(int a, int b) { Body.text = Build(a, b); Body.ForceMeshUpdate(); return !Body.isTextOverflowing; }
            Body.overflowMode = TextOverflowModes.Overflow;
            int lo = cur, hi = cur;
            if (Fits(0, items.Count - 1)) { lo = 0; hi = items.Count - 1; }
            else
            {
                lo = Mathf.Max(0, cur - 1);                                    // one sentence of lead-in when it fits
                if (!Fits(lo, hi)) lo = cur;
                while (hi + 1 < items.Count && Fits(lo, hi + 1)) hi++;        // then as much of what follows as fits
                while (lo > 0 && Fits(lo - 1, hi)) lo--;                      // and fill any room left with what came before
            }
            Body.text = Build(lo, hi);
            Body.overflowMode = TextOverflowModes.Truncate;
        }
    }
}
