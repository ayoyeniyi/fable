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
        public float Distance = 1.15f, Height = -0.08f, Follow = 2.2f;
        public Color Ink = new(0.13f, 0.11f, 0.09f), Dim = new(0.13f, 0.11f, 0.09f, 0.38f), Paper = new(0.96f, 0.93f, 0.86f);

        Passage.Scene scene; string currentId;

        void LateUpdate()
        {
            if (!Head) return;
            var fwd = Vector3.ProjectOnPlane(Head.forward, Vector3.up).normalized;
            if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            var target = Head.position + fwd * Distance + Vector3.up * Height;
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
            var sb = new StringBuilder();
            string dim = ColorUtility.ToHtmlStringRGBA(Dim), ink = ColorUtility.ToHtmlStringRGBA(Ink);
            foreach (var p in s.Paragraphs)
            {
                foreach (var se in p)
                {
                    bool cur = se.Id == sentenceId;
                    sb.Append(cur ? $"<color=#{ink}><b>" : $"<color=#{dim}>").Append(se.Text).Append(cur ? "</b></color> " : "</color> ");
                }
                sb.Append("\n\n");
            }
            Body.text = sb.ToString().TrimEnd();
        }
    }
}
