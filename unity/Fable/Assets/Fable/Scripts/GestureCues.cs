// Animated gesture cues under the passage, in the manner of the Quest's own hand-tracking tutorials: a small looping
// picture per available action, drawn as a real hand (palm, four fingers, thumb) or a Touch controller (body, ring,
// thumbstick, trigger) rather than abstract dots. A pinch closes index to thumb, a hold fills a ring, a drag slides the
// pinched hand, pointing lays a ray to a disc, walking pumps two arms, turning pushes the stick or slides the left hand.
// Everything is built at runtime from two generated sprites (a disc and a ring), so every scene's page gets the row
// without a rebuild. Which cues show follows the flow state and whether hands or controllers are being tracked.
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Fable
{
    public class GestureCues : MonoBehaviour
    {
        public enum Kind { Pinch, Hold, Drag, Point, Swing, Turn, Move }
        public struct Cue { public Kind Kind; public bool Left; public string Label; public Cue(Kind k, bool left, string label) { Kind = k; Left = left; Label = label; } }

        public float Top = 786f, RowHeight = 158f, Period = 2.6f;
        public Color Ink = new(0.13f, 0.11f, 0.09f), Faint = new(0.13f, 0.11f, 0.09f, 0.18f), Accent = new(0.62f, 0.42f, 0.10f);

        FlowController flow; ReaderController input; ReadingPanel panel;
        RectTransform row; Sprite dot, ringSprite; TMP_FontAsset font;
        readonly List<Slot> slots = new();
        string key;

        // one drawn hand or controller; a slot holds one of them, or two for arm-swinging
        class Figure
        {
            public RectTransform Root; public bool Controller;
            public RectTransform Palm, Thumb; public RectTransform[] Fingers; public Image[] FingerImg; public Image ThumbImg, PalmImg;
            public RectTransform Body, Ring, Stick, Trigger; public Image StickImg, TriggerImg, RingImg;
            public RectTransform Ray, Disc; public Image RayImg, DiscImg;
            public Image Fill;   // the hold ring
            public Vector2 Home; // where the figure rests in its slot
        }
        class Slot { public RectTransform Root; public List<Figure> Figures = new(); public TMP_Text Label; public Cue Cue; public bool Controller; }

        // rest and pinched finger poses: angle (degrees, positive swings the fingertip toward the thumb side) and length
        static readonly float[] RestAngle = { -8, -3, 3, 10 }, RestLen = { 26, 28, 25, 20 };
        static readonly float[] PinchAngle = { 75, 4, 10, 17 }, PinchLen = { 22, 22, 20, 16 };
        static readonly float[] PointAngle = { 0, 6, 12, 18 }, PointLen = { 28, 12, 11, 10 };
        static readonly float[] FingerX = { -10, -3, 4, 11 };
        const float RestThumb = 55, PinchThumb = 45, PointThumb = 22, ThumbLen = 24;

        void Awake()
        {
            panel = GetComponent<ReadingPanel>();
            var rt = (RectTransform)transform;
            if (rt.sizeDelta.y < Top + RowHeight) rt.sizeDelta = new Vector2(rt.sizeDelta.x, Top + RowHeight + 12);
            dot = MakeDot(false); ringSprite = MakeDot(true);
            row = new GameObject("GestureCues", typeof(RectTransform)).GetComponent<RectTransform>();
            row.SetParent(transform, false); row.anchorMin = new Vector2(0, 1); row.anchorMax = new Vector2(1, 1); row.pivot = new Vector2(0.5f, 1);
            row.anchoredPosition = new Vector2(0, -Top); row.sizeDelta = new Vector2(-36, RowHeight);
        }

        void Start()
        {
            flow = FindFirstObjectByType<FlowController>(); input = FindFirstObjectByType<ReaderController>();
            if (panel && panel.Hint) font = panel.Hint.font;
        }

        static Sprite MakeDot(bool ring)
        {
            const int n = 64; var tex = new Texture2D(n, n, TextureFormat.RGBA32, false); tex.wrapMode = TextureWrapMode.Clamp;
            var px = new Color32[n * n]; float c = (n - 1) / 2f, r = c - 1.5f, inner = r - 7f;
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float d = Mathf.Sqrt((x - c) * (x - c) + (y - c) * (y - c));
                float a = Mathf.Clamp01(r - d + 0.5f);
                if (ring) a *= Mathf.Clamp01(d - inner + 0.5f);
                px[y * n + x] = new Color32(255, 255, 255, (byte)(255 * a));
            }
            tex.SetPixels32(px); tex.Apply();
            return Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
        }

        void Update()
        {
            if (!flow || !input) return;
            string mode = input.InputMode;
            var verb = flow.Tasks ? flow.Tasks.ActiveVerb : null;
            bool grabbing = verb == StoryTasks.Verb.Grab || verb == StoryTasks.Verb.BringTo;
            string k = flow.Current + "|" + mode + "|" + flow.CanStepIn + "|" + grabbing;
            if (k != key) { key = k; Rebuild(Plan(flow.Current, mode, flow.CanStepIn, grabbing), mode == "controllers"); }
            Animate();
        }

        /// The actions available in this state, in the order a reader needs them. Labels: what you do, then what happens.
        static List<Cue> Plan(FlowController.State state, string mode, bool canStepIn, bool grabbing = false)
        {
            bool ctrl = mode == "controllers";
            string g = ctrl ? "trigger" : "pinch";
            var list = new List<Cue>();
            switch (state)
            {
                case FlowController.State.Reading:
                    list.Add(new Cue(Kind.Pinch, false, $"right {g}\nturn the page"));
                    list.Add(new Cue(Kind.Pinch, true, $"left {g}\npage back"));
                    list.Add(new Cue(Kind.Drag, false, $"{g}, drag over words\nhighlight: define, peek"));
                    list.Add(new Cue(Kind.Point, false, $"point at a button, {g}\ncontents, size, step in"));
                    break;
                case FlowController.State.Miniature:
                    list.Add(new Cue(Kind.Point, false, $"point into the room, {g}\nstand there"));
                    list.Add(new Cue(Kind.Pinch, false, $"right {g}\nnext sentence"));
                    list.Add(new Cue(Kind.Drag, false, $"{g} and drag\nscroll the story"));
                    list.Add(new Cue(Kind.Hold, true, $"hold left {g}\nclose the book"));
                    break;
                case FlowController.State.Scene:
                    list.Add(new Cue(Kind.Point, false, $"point at the floor, {g}\ngo there"));
                    if (ctrl) list.Add(new Cue(Kind.Move, false, "right stick\nwalk"));
                    else list.Add(new Cue(Kind.Swing, false, "swing both arms\nwalk"));
                    if (ctrl) list.Add(new Cue(Kind.Turn, true, "left stick\nturn"));
                    else list.Add(new Cue(Kind.Turn, true, "left pinch, slide sideways\nturn"));
                    if (grabbing) list.Add(new Cue(Kind.Hold, false, $"point at it, {g} and hold\npick it up"));
                    else list.Add(new Cue(Kind.Point, false, $"point at the little door, {g}\ngo through"));
                    list.Add(new Cue(Kind.Pinch, false, $"right {g}\nnext sentence"));
                    break;
            }
            return list;
        }

        void Rebuild(List<Cue> cues, bool controllers)
        {
            foreach (var s in slots) if (s.Root) Destroy(s.Root.gameObject);
            slots.Clear();
            if (cues.Count == 0) return;
            float w = 1f / cues.Count;
            for (int i = 0; i < cues.Count; i++)
            {
                var s = new Slot { Cue = cues[i], Controller = controllers };
                s.Root = new GameObject("Cue" + i, typeof(RectTransform)).GetComponent<RectTransform>();
                s.Root.SetParent(row, false); s.Root.anchorMin = new Vector2(i * w, 0); s.Root.anchorMax = new Vector2((i + 1) * w, 1); s.Root.offsetMin = s.Root.offsetMax = Vector2.zero;
                if (s.Cue.Kind == Kind.Swing && !controllers)
                {
                    s.Figures.Add(Build(s.Root, controllers, true, 0.8f, new Vector2(-20, 36)));
                    s.Figures.Add(Build(s.Root, controllers, false, 0.8f, new Vector2(20, 36)));
                }
                else s.Figures.Add(Build(s.Root, controllers, s.Cue.Left, s.Cue.Kind == Kind.Point ? 1.0f : 1.2f, new Vector2(0, 38)));
                var t = new GameObject("Label").AddComponent<TextMeshProUGUI>(); t.transform.SetParent(s.Root, false);
                var r = t.rectTransform; r.anchorMin = new Vector2(0, 0); r.anchorMax = new Vector2(1, 0); r.pivot = new Vector2(0.5f, 0); r.anchoredPosition = new Vector2(0, -2); r.sizeDelta = new Vector2(-2, 46);
                if (font) t.font = font; t.fontSize = 13f; t.color = Ink; t.alignment = TextAlignmentOptions.Center; t.textWrappingMode = TextWrappingModes.Normal; t.lineSpacing = -6; t.text = s.Cue.Label;
                s.Label = t;
                slots.Add(s);
            }
        }

        Figure Build(RectTransform parent, bool controller, bool left, float scale, Vector2 at)
        {
            var f = new Figure { Controller = controller, Home = at };
            f.Root = new GameObject(controller ? "Controller" : "Hand", typeof(RectTransform)).GetComponent<RectTransform>();
            f.Root.SetParent(parent, false); f.Root.anchorMin = f.Root.anchorMax = new Vector2(0.5f, 0.5f); f.Root.sizeDelta = new Vector2(80, 80); f.Root.anchoredPosition = at;
            f.Root.localScale = new Vector3(left ? -scale : scale, scale, 1);
            f.Fill = Img(f.Root, "Fill", ringSprite, 74, new Color(Accent.r, Accent.g, Accent.b, 0.55f), new Vector2(0, 8)); f.Fill.type = Image.Type.Filled; f.Fill.fillMethod = Image.FillMethod.Radial360; f.Fill.fillOrigin = 2; f.Fill.fillClockwise = true; f.Fill.fillAmount = 0;
            var ink = new Color(Ink.r, Ink.g, Ink.b, 0.82f);
            if (!controller)
            {
                f.PalmImg = Img(f.Root, "Palm", dot, 30, ink, new Vector2(0, 0)); f.Palm = f.PalmImg.rectTransform; f.Palm.sizeDelta = new Vector2(30, 34);
                f.Fingers = new RectTransform[4]; f.FingerImg = new Image[4];
                for (int i = 0; i < 4; i++) { f.FingerImg[i] = Capsule(f.Root, "Finger" + i, 9, RestLen[i], ink, new Vector2(FingerX[i], 13)); f.Fingers[i] = f.FingerImg[i].rectTransform; }
                f.ThumbImg = Capsule(f.Root, "Thumb", 9, ThumbLen, ink, new Vector2(-13, -3)); f.Thumb = f.ThumbImg.rectTransform;
            }
            else
            {
                var body = Img(f.Root, "Body", dot, 26, new Color(Ink.r, Ink.g, Ink.b, 0.30f), new Vector2(0, -6)); f.Body = body.rectTransform; f.Body.sizeDelta = new Vector2(26, 46);
                f.RingImg = Img(f.Root, "Ring", ringSprite, 46, ink, new Vector2(0, 14)); f.Ring = f.RingImg.rectTransform; f.Ring.localScale = new Vector3(1, 0.5f, 1);
                f.StickImg = Img(f.Root, "Stick", dot, 11, ink, new Vector2(0, 4)); f.Stick = f.StickImg.rectTransform;
                f.TriggerImg = Capsule(f.Root, "Trigger", 9, 14, ink, new Vector2(0, -42)); f.Trigger = f.TriggerImg.rectTransform;
            }
            // pointing ray and landing disc, from the top of the figure (hidden unless the cue points)
            f.RayImg = Img(f.Root, "Ray", dot, 2, new Color(Accent.r, Accent.g, Accent.b, 0.8f), Vector2.zero); f.Ray = f.RayImg.rectTransform; f.Ray.pivot = new Vector2(0.5f, 0); f.Ray.sizeDelta = new Vector2(2.5f, 30);
            f.DiscImg = Img(f.Root, "Disc", ringSprite, 16, Accent, Vector2.zero); f.Disc = f.DiscImg.rectTransform; f.Disc.sizeDelta = new Vector2(9, 18);
            f.Ray.gameObject.SetActive(false); f.Disc.gameObject.SetActive(false);
            return f;
        }

        Image Img(RectTransform parent, string name, Sprite sp, float size, Color col, Vector2 pos)
        {
            var im = new GameObject(name).AddComponent<Image>(); im.transform.SetParent(parent, false); im.sprite = sp; im.color = col; im.raycastTarget = false;
            var r = im.rectTransform; r.anchorMin = r.anchorMax = new Vector2(0.5f, 0.5f); r.sizeDelta = new Vector2(size, size); r.anchoredPosition = pos;
            return im;
        }

        /// A rounded bar standing on its base (pivot at the bottom), so rotating it bends it at the knuckle.
        Image Capsule(RectTransform parent, string name, float width, float length, Color col, Vector2 basePos)
        {
            var im = Img(parent, name, dot, width, col, basePos);   // a stretched disc reads as a capsule at these sizes
            var r = im.rectTransform; r.pivot = new Vector2(0.5f, 0.08f); r.sizeDelta = new Vector2(width, length);
            return im;
        }

        void Animate()
        {
            float t = (Time.time % Period) / Period;
            foreach (var s in slots)
            {
                if (!s.Root) continue;
                for (int i = 0; i < s.Figures.Count; i++)
                {
                    var f = s.Figures[i]; if (!f.Root) continue;
                    Pose(f, s.Cue.Kind, s.Controller, i == 0 ? t : (t + 0.5f) % 1f, s.Cue.Left);
                }
            }
        }

        void Pose(Figure f, Kind kind, bool ctrl, float t, bool left)
        {
            // k: how far from rest to pinched; ring: hold progress; slide: sideways travel; point: a pointing pose
            float k = 0, ring = 0, slide = 0, bob = 0, stickX = 0, stickY = 0, discK = 0; bool point = false, press = false;
            switch (kind)
            {
                case Kind.Pinch:
                    k = t < 0.25f ? Ease(t / 0.25f) : t < 0.45f ? 1 : t < 0.7f ? 1 - Ease((t - 0.45f) / 0.25f) : 0; press = k > 0.97f; break;
                case Kind.Hold:
                    k = t < 0.2f ? Ease(t / 0.2f) : t < 0.8f ? 1 : 1 - Ease((t - 0.8f) / 0.2f); ring = t < 0.2f ? 0 : t < 0.8f ? (t - 0.2f) / 0.6f : 0; press = k > 0.97f; break;
                case Kind.Drag:
                    k = 1; press = true; slide = Mathf.Sin(t * Mathf.PI * 2f) * 20f; break;
                case Kind.Turn:
                    if (ctrl) { stickX = Mathf.Sin(t * Mathf.PI * 2f) * 9f; }
                    else { k = 1; press = true; slide = Mathf.Sin(t * Mathf.PI * 2f) * 16f; }
                    break;
                case Kind.Move:
                    stickY = t < 0.5f ? Ease(t / 0.5f) * 9f : (1 - Ease((t - 0.5f) / 0.5f)) * 9f; break;
                case Kind.Swing:
                    bob = Mathf.Sin(t * Mathf.PI * 2f) * 11f; break;
                case Kind.Point:
                    point = true; discK = Mathf.Clamp01(t / 0.5f);
                    k = t < 0.55f ? 0 : t < 0.65f ? Ease((t - 0.55f) / 0.1f) : t < 0.8f ? 1 : 1 - Ease((t - 0.8f) / 0.2f);
                    press = k > 0.97f; break;
            }
            // whole-figure placement: pointing figures lie on their side so the finger (or controller nose) aims to the right
            f.Root.localRotation = Quaternion.Euler(0, 0, point ? -90f : 0f);
            f.Root.anchoredPosition = (point ? f.Home + new Vector2(-22, -6) : f.Home) + new Vector2(slide, bob);
            f.Fill.fillAmount = ring; f.Fill.enabled = ring > 0;

            var accent = Accent; var ink = new Color(Ink.r, Ink.g, Ink.b, 0.82f);
            if (!ctrl)
            {
                var angles = point ? PointAngle : PinchAngle; var lens = point ? PointLen : PinchLen; float kk = point ? 1 : k;
                for (int i = 0; i < 4; i++)
                {
                    float a = Mathf.Lerp(RestAngle[i], angles[i], kk), l = Mathf.Lerp(RestLen[i], lens[i], kk);
                    f.Fingers[i].localRotation = Quaternion.Euler(0, 0, a); f.Fingers[i].sizeDelta = new Vector2(9, l);
                }
                float th = point ? Mathf.Lerp(PointThumb, 4f, k) : Mathf.Lerp(RestThumb, PinchThumb, k);
                f.Thumb.localRotation = Quaternion.Euler(0, 0, th);
                f.FingerImg[0].color = press ? accent : ink; f.ThumbImg.color = press ? accent : ink;
                // the pointing finger's tip, where the ray begins
                var tip = new Vector2(FingerX[0], 13) + Rot(new Vector2(0, PointLen[0]), PointAngle[0]);
                f.Ray.anchoredPosition = tip; f.Disc.anchoredPosition = tip + new Vector2(0, 36);
            }
            else
            {
                f.Stick.anchoredPosition = new Vector2(0, 4) + new Vector2(stickX, stickY);
                bool pushed = Mathf.Abs(stickX) > 4 || stickY > 4;
                f.StickImg.color = pushed ? accent : ink;
                f.Trigger.localScale = new Vector3(1, press ? 0.6f : 1f, 1); f.TriggerImg.color = press ? accent : ink;
                f.Ray.anchoredPosition = new Vector2(0, 26); f.Disc.anchoredPosition = new Vector2(0, 62);
            }
            f.Ray.gameObject.SetActive(point); f.Disc.gameObject.SetActive(point);
            if (point) { f.DiscImg.color = press ? Accent : new Color(Accent.r, Accent.g, Accent.b, 0.35f + 0.5f * discK); f.Disc.localScale = Vector3.one * (0.6f + 0.4f * discK); f.Ray.sizeDelta = new Vector2(2.5f, 30f * discK); }
        }

        static Vector2 Rot(Vector2 v, float deg) { float r = deg * Mathf.Deg2Rad, c = Mathf.Cos(r), s = Mathf.Sin(r); return new Vector2(v.x * c - v.y * s, v.x * s + v.y * c); }
        static float Ease(float x) { x = Mathf.Clamp01(x); return x * x * (3 - 2 * x); }
    }
}
