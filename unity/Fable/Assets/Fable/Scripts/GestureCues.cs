// Animated gesture cues under the passage, in the manner of the Quest's own hand-tracking tutorials: a small looping
// glyph per available action (thumb and index dots that meet, hold with a filling ring, or slide to scrub), labelled
// for whatever the reader is holding. Everything is built at runtime from a generated circle sprite, so every scene's
// page gets the row without a rebuild. Which cues show follows the flow state and the active input.
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Fable
{
    public class GestureCues : MonoBehaviour
    {
        public enum Kind { Pinch, Hold, Drag, Point, Swing }
        public struct Cue { public Kind Kind; public bool Left; public string Label; public Cue(Kind k, bool left, string label) { Kind = k; Left = left; Label = label; } }

        public float Top = 790f, RowHeight = 104f, Period = 2.4f;
        public Color Ink = new(0.13f, 0.11f, 0.09f), Faint = new(0.13f, 0.11f, 0.09f, 0.18f), Accent = new(0.62f, 0.42f, 0.10f);

        FlowController flow; ReaderController input; ReadingPanel panel;
        RectTransform row; Sprite dot; TMP_FontAsset font;
        readonly List<Slot> slots = new();
        string key;

        class Slot { public RectTransform Root; public Image Palm, Thumb, Index, Ring; public TMP_Text Label; public Cue Cue; }

        void Awake()
        {
            panel = GetComponent<ReadingPanel>();
            var rt = (RectTransform)transform;
            if (rt.sizeDelta.y < Top + RowHeight) rt.sizeDelta = new Vector2(rt.sizeDelta.x, Top + RowHeight + 12);
            dot = MakeDot();
            row = new GameObject("GestureCues", typeof(RectTransform)).GetComponent<RectTransform>();
            row.SetParent(transform, false); row.anchorMin = new Vector2(0, 1); row.anchorMax = new Vector2(1, 1); row.pivot = new Vector2(0.5f, 1);
            row.anchoredPosition = new Vector2(0, -Top); row.sizeDelta = new Vector2(-96, RowHeight);
        }

        void Start()
        {
            flow = FindFirstObjectByType<FlowController>(); input = FindFirstObjectByType<ReaderController>();
            if (panel && panel.Hint) font = panel.Hint.font;
        }

        static Sprite MakeDot()
        {
            const int n = 64; var tex = new Texture2D(n, n, TextureFormat.RGBA32, false); tex.wrapMode = TextureWrapMode.Clamp;
            var px = new Color32[n * n]; float c = (n - 1) / 2f, r = c - 1.5f;
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float d = Mathf.Sqrt((x - c) * (x - c) + (y - c) * (y - c));
                byte a = (byte)(255 * Mathf.Clamp01(r - d + 0.5f));
                px[y * n + x] = new Color32(255, 255, 255, a);
            }
            tex.SetPixels32(px); tex.Apply();
            return Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
        }

        void Update()
        {
            if (!flow || !input) return;
            string mode = input.InputMode;
            string k = flow.Current + "|" + mode + "|" + flow.CanStepIn;
            if (k != key) { key = k; Rebuild(Plan(flow.Current, mode, flow.CanStepIn)); }
            Animate();
        }

        /// The actions available in this state, in the order a reader needs them.
        static List<Cue> Plan(FlowController.State state, string mode, bool canStepIn)
        {
            string g = mode == "controllers" ? "trigger" : "pinch";
            var list = new List<Cue>();
            switch (state)
            {
                case FlowController.State.Reading:
                    list.Add(new Cue(Kind.Pinch, false, $"right {g}\nturn the page"));
                    list.Add(new Cue(Kind.Pinch, true, $"left {g}\npage back"));
                    list.Add(new Cue(Kind.Pinch, false, $"point and {g}\ncontents, size, bookmark"));
                    if (canStepIn) list.Add(new Cue(Kind.Hold, false, $"hold right {g}\nstep in"));
                    break;
                case FlowController.State.Miniature:
                    list.Add(new Cue(Kind.Point, false, $"point into the room, {g}\nstep in there"));
                    list.Add(new Cue(Kind.Pinch, false, $"{g}\nnext sentence"));
                    list.Add(new Cue(Kind.Hold, true, $"hold left {g}\nclose the book"));
                    break;
                case FlowController.State.Scene:
                    list.Add(new Cue(Kind.Point, false, $"point at the floor, {g}\ngo there"));
                    list.Add(new Cue(Kind.Swing, false, "swing your arms\nwalk"));
                    list.Add(new Cue(Kind.Point, false, $"point at a door, {g}\ngo through"));
                    list.Add(new Cue(Kind.Pinch, false, $"{g}\nnext sentence"));
                    break;
            }
            return list;
        }

        void Rebuild(List<Cue> cues)
        {
            foreach (var s in slots) if (s.Root) Destroy(s.Root.gameObject);
            slots.Clear();
            if (cues.Count == 0) return;
            float w = 1f / cues.Count;
            for (int i = 0; i < cues.Count; i++)
            {
                var s = new Slot { Cue = cues[i] };
                s.Root = new GameObject("Cue" + i, typeof(RectTransform)).GetComponent<RectTransform>();
                s.Root.SetParent(row, false); s.Root.anchorMin = new Vector2(i * w, 0); s.Root.anchorMax = new Vector2((i + 1) * w, 1); s.Root.offsetMin = s.Root.offsetMax = Vector2.zero;
                s.Ring = Img(s.Root, "Ring", 58, Faint, new Vector2(0, 16)); s.Ring.type = Image.Type.Filled; s.Ring.fillMethod = Image.FillMethod.Radial360; s.Ring.fillOrigin = 2; s.Ring.fillClockwise = true; s.Ring.fillAmount = 0;
                s.Palm = Img(s.Root, "Palm", 46, Faint, new Vector2(0, 16));
                s.Thumb = Img(s.Root, "Thumb", 12, Ink, Vector2.zero);
                s.Index = Img(s.Root, "Index", 12, Ink, Vector2.zero);
                var t = new GameObject("Label").AddComponent<TextMeshProUGUI>(); t.transform.SetParent(s.Root, false);
                var r = t.rectTransform; r.anchorMin = new Vector2(0, 0); r.anchorMax = new Vector2(1, 0); r.pivot = new Vector2(0.5f, 0); r.anchoredPosition = new Vector2(0, 0); r.sizeDelta = new Vector2(0, 36);
                if (font) t.font = font; t.fontSize = 11.5f; t.color = Ink; t.alignment = TextAlignmentOptions.Center; t.textWrappingMode = TextWrappingModes.Normal; t.lineSpacing = -8; t.text = s.Cue.Label;
                s.Label = t;
                slots.Add(s);
            }
        }

        Image Img(RectTransform parent, string name, float size, Color col, Vector2 pos)
        {
            var im = new GameObject(name).AddComponent<Image>(); im.transform.SetParent(parent, false); im.sprite = dot; im.color = col; im.raycastTarget = false;
            var r = im.rectTransform; r.anchorMin = r.anchorMax = new Vector2(0.5f, 0.5f); r.sizeDelta = new Vector2(size, size); r.anchoredPosition = pos;
            return im;
        }

        void Animate()
        {
            float t = (Time.time % Period) / Period;
            foreach (var s in slots)
            {
                if (!s.Root) continue;
                float side = s.Cue.Left ? -1f : 1f;
                Vector2 centre = new Vector2(0, 16);
                float gap, slide = 0, ring = 0; bool touching;
                switch (s.Cue.Kind)
                {
                    case Kind.Pinch:
                        // apart, close, touch, open, rest
                        gap = t < 0.25f ? Mathf.Lerp(16, 0, Ease(t / 0.25f)) : t < 0.45f ? 0 : t < 0.7f ? Mathf.Lerp(0, 16, Ease((t - 0.45f) / 0.25f)) : 16;
                        touching = gap < 1f;
                        break;
                    case Kind.Hold:
                        // close, then hold while the ring fills, then open
                        gap = t < 0.2f ? Mathf.Lerp(16, 0, Ease(t / 0.2f)) : t < 0.8f ? 0 : Mathf.Lerp(0, 16, Ease((t - 0.8f) / 0.2f));
                        ring = t < 0.2f ? 0 : t < 0.8f ? (t - 0.2f) / 0.6f : 0;
                        touching = gap < 1f;
                        break;
                    case Kind.Point:
                        // a hand held out: index dot leads, a ring lands ahead, then a pinch
                        gap = t < 0.55f ? 10f : t < 0.75f ? 0f : 10f; touching = gap < 1f;
                        s.Ring.fillAmount = t < 0.55f ? Mathf.Clamp01(t / 0.45f) : 1f; s.Ring.rectTransform.anchoredPosition = centre + new Vector2(0, -26f);
                        s.Ring.color = new Color(Accent.r, Accent.g, Accent.b, 0.55f);
                        s.Thumb.rectTransform.anchoredPosition = centre + new Vector2(-gap * 0.4f, 8f);
                        s.Index.rectTransform.anchoredPosition = centre + new Vector2(gap * 0.4f, 16f);
                        s.Palm.rectTransform.anchoredPosition = centre + new Vector2(0, 2f);
                        s.Thumb.color = s.Index.color = touching ? Accent : Ink;
                        continue;
                    case Kind.Swing:
                        // two hands pumping in opposite phase
                        gap = 0; touching = false;
                        s.Thumb.rectTransform.anchoredPosition = centre + new Vector2(-14f, Mathf.Sin(t * Mathf.PI * 4f) * 14f);
                        s.Index.rectTransform.anchoredPosition = centre + new Vector2(14f, -Mathf.Sin(t * Mathf.PI * 4f) * 14f);
                        s.Palm.rectTransform.anchoredPosition = centre; s.Ring.fillAmount = 0;
                        s.Thumb.color = s.Index.color = Ink;
                        continue;
                    default:
                        // pinched, slide to one side and back
                        gap = 0; touching = true;
                        slide = Mathf.Sin(t * Mathf.PI * 2f) * 22f;
                        break;
                }
                s.Thumb.rectTransform.anchoredPosition = centre + new Vector2(slide - gap * 0.5f * side, -gap * 0.35f);
                s.Index.rectTransform.anchoredPosition = centre + new Vector2(slide + gap * 0.5f * side, gap * 0.35f);
                s.Palm.rectTransform.anchoredPosition = centre + new Vector2(slide * 0.6f, -6f);
                var c = touching ? Accent : Ink; s.Thumb.color = c; s.Index.color = c;
                s.Ring.fillAmount = ring; s.Ring.color = ring > 0 ? new Color(Accent.r, Accent.g, Accent.b, 0.55f) : Faint;
                s.Ring.rectTransform.anchoredPosition = centre + new Vector2(slide * 0.6f, 0);
            }
        }

        static float Ease(float x) { x = Mathf.Clamp01(x); return x * x * (3 - 2 * x); }
    }
}
