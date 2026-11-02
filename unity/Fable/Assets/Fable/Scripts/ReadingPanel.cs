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
        public Color Ink = new(0.13f, 0.11f, 0.09f), Dim = new(0.13f, 0.11f, 0.09f, 0.62f), Paper = new(0.96f, 0.93f, 0.86f);

        /// Size relative to the authored panel (the canvas itself is scaled ~0.001 to turn pixels into metres). Each
        /// flow state sets its own; the reader's own size (the resize handle, saved in their preferences) multiplies it.
        public float Scale = 1f;
        public float UserScale = 1f;
        float baseScale;

        Passage.Scene scene; string currentId;

        void Awake() { baseScale = transform.localScale.x; UserScale = Mathf.Clamp(ProgressStore.LoadPrefs().PanelScale, MinUserScale, MaxUserScale); }
        public const float MinUserScale = 0.7f, MaxUserScale = 1.6f;

        /// The page stays where it is in the room. It does not trail the reader's head: a reader who turns (with the view
        /// toolbar, or by looking over a shoulder) to see the room finds the page where they left it, and "recentre"
        /// brings it back in front of them. It moves on its own only when the flow places it (Recentre), when the reader
        /// moves it by its handle, when the rig moves (teleport, walking: Shift), and when the reader sits down or
        /// stands up in front of it (their eye height changes by more than ChangeOfHeight while they face it).
        public float ChangeOfHeight = 0.35f;
        /// The diorama table in the reading room tops out at 0.72 m; a page that follows a low, seated head would sink
        /// its footer and gesture cues into it, so over the table the page's bottom edge never drops below this height.
        public float MinBottom = 0.76f; public bool ClampToTable = true;
        bool recentring = true;
        /// The reader has put the page somewhere themselves: only Recentre undoes that.
        public bool PlacedByReader { get; private set; }
        public void Recentre() { recentring = true; PlacedByReader = false; }
        /// The view turned: a page still gliding into place stops where it is, rather than following the turn.
        public void HoldStill() { recentring = false; }
        /// The rig moved by `delta` (teleport, walking): the page comes along.
        public void Shift(Vector3 delta) { transform.position += delta; }
        /// The reader dragged the page by its handle to a new place, facing them.
        public void PlaceAt(Vector3 world)
        {
            recentring = false; PlacedByReader = true;
            transform.position = world;
            if (Head) transform.rotation = Quaternion.LookRotation(transform.position - Head.position, Vector3.up);
        }
        public float HalfHeightMetres => ((RectTransform)transform).rect.height * baseScale * Scale * UserScale * 0.5f;

        void LateUpdate()
        {
            transform.localScale = Vector3.one * (baseScale * Scale * UserScale);
            if (!Head) return;
            var fwd = Vector3.ProjectOnPlane(Head.forward, Vector3.up).normalized;
            if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            var right = Vector3.Cross(Vector3.up, fwd);
            var target = Head.position + fwd * Distance + Vector3.up * Height + right * Side;
            if (ClampToTable) { float half = HalfHeightMetres; target.y = Mathf.Max(target.y, MinBottom + half); }
            if (!recentring && !PlacedByReader)
            {
                // sitting down or standing up in front of the page: it keeps its place in the room but meets the new eye height
                var toPanel = transform.position - Head.position;
                bool facing = Vector3.Angle(fwd, Vector3.ProjectOnPlane(toPanel, Vector3.up)) < 35f;
                if (facing && Mathf.Abs(toPanel.y - (target.y - Head.position.y)) > ChangeOfHeight) recentring = true;
            }
            if (!recentring) return;
            transform.position = Vector3.Lerp(transform.position, target, Time.deltaTime * Follow);
            var look = Quaternion.LookRotation(transform.position - Head.position, Vector3.up);
            transform.rotation = Quaternion.Slerp(transform.rotation, look, Time.deltaTime * Follow);
            if ((transform.position - target).sqrMagnitude < 0.0004f && Quaternion.Angle(transform.rotation, look) < 1.5f) { transform.position = target; transform.rotation = look; recentring = false; }
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
