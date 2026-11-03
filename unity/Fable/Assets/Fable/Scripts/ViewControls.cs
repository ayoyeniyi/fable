// The view toolbar: a row of buttons that is always within reach of a reader who stays in one place.
//   ‹ turn        the view turns 30 degrees to the left about the reader's own head (one turn per pinch)
//   recentre      the page (or the library panel) comes back in front of the reader, where they now look
//   turn ›        30 degrees to the right
// plus the actions of the moment ("‹ return to reading", "back to the table", "stand in the room ›", "face the shelf").
//
// The bar sits just under the page while the page is in view. When the reader turns away from the page, the bar
// leaves it and floats low in front of them, so recentre is always one point-and-pinch away. A pinch that starts on
// the bar is claimed by it (ReaderController.Claimers): the button fires once, on the pinch's first frame, and that
// pinch never also turns a page, scrolls, highlights or grabs. Holding the pinch does not repeat the turn.
// A turn rotates the camera rig about the tracked head position and the vertical axis only: no translation of the
// head, no pitch, no roll, and head tracking carries on as normal. The controller thumbstick turns by the same step.
using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Fable
{
    public class ViewControls : MonoBehaviour
    {
        public static ViewControls Instance { get; private set; }

        public ReaderController Input;
        public Transform Head, Rig;
        /// The panel the bar docks under (the reading page or the library panel). Null: the bar always floats.
        public RectTransform Dock;
        public TMP_FontAsset Font;
        /// Degrees per turn. Saved in the reader's preferences; 30 until headset testing says otherwise.
        public float TurnDegrees = 30f;
        public float DockGapMetres = 0.035f, FloatForward = 0.62f, FloatDrop = 0.42f, DockedWithinDegrees = 42f, FollowDeadZone = 24f;
        public Color Paper = new(0.97f, 0.93f, 0.84f, 0.97f), Ink = new(0.20f, 0.14f, 0.08f), Lit = new(0.99f, 0.86f, 0.52f, 1f), Edge = new(0.45f, 0.33f, 0.18f, 0.9f);

        /// The lowest the bar's bottom edge may go (the reading room's diorama table top); -inf when nothing is below.
        public float MinY = float.NegativeInfinity;

        /// Fired by "recentre". The owner brings its panel back in front of the reader.
        public event Action Recentred;
        /// Fired after every turn (degrees, signed: + is to the right).
        public event Action<float> Turned;

        /// Editor tests: a right-hand ray to use instead of the hand or mouse (null = live input).
        public Ray? TestRay;
        public string HoveredLabel => hovered >= 0 && hovered < buttons.Count ? buttons[hovered].Label : null;
        public bool Docked { get; private set; }

        class Button { public string Label; public Action Act; public RectTransform Rt; public Image Bg; public TMP_Text Text; public float Flash, Width; }
        readonly List<Button> buttons = new();
        RectTransform bar, tipRt; TMP_Text tip; float tipUntil; Canvas canvas;
        LineRenderer line; Image cursor; Material lineMat;
        int hovered = -1; bool hoverRight = true;
        (string label, Action act)[] extras = Array.Empty<(string, Action)>();
        string extrasKey = "";
        Vector3 floatPos; Quaternion floatRot; bool floatInit;
        float netTurn;   // degrees turned since the last recentre: the bar floats with the reader until they face the page again
        const float Px = 0.001f, ButtonH = 48f, Pad = 6f;
        /// Laid out as a column beside the page (when the table leaves no room under it) rather than a row under it.
        bool column;
        /// The bar's size on the page: never wider than the page (row) or taller than half of it (column).
        float scale = Px;

        /// True while something the reader is looking at sits where the bar would be (a Peek card and model, the
        /// highlight menu): the bar hides until it is closed.
        public Func<bool> Quiet;

        void Awake() { Instance = this; }
        void OnDestroy() { if (Instance == this) Instance = null; if (Input) Input.Claimers.Remove(Claim); }

        public void Init(ReaderController input, Transform head, Transform rig, RectTransform dock, TMP_FontAsset font)
        {
            Input = input; Head = head; Rig = rig; Dock = dock; Font = font;
            TurnDegrees = Mathf.Clamp(ProgressStore.LoadPrefs().TurnDegrees, 10f, 90f);
            Build();
            if (Input && !Input.Claimers.Contains(Claim)) Input.Claimers.Insert(0, Claim);
        }

        /// The actions of the moment, shown before the turn buttons. Rebuilds the bar only when they change.
        public void SetActions(params (string label, Action act)[] actions)
        {
            var key = string.Join("|", Array.ConvertAll(actions, a => a.label));
            extras = actions;
            if (key == extrasKey) return;
            extrasKey = key; Rebuild();
        }

        // ---------------------------------------------------------------- the reader's actions

        /// Turn the view by one step to the right (dir > 0) or left (dir < 0), about the head.
        public void Turn(int dir)
        {
            if (!Rig || !Head || dir == 0) return;
            float deg = TurnDegrees * Mathf.Sign(dir);
            Rig.RotateAround(Head.position, Vector3.up, deg);
            netTurn = Mathf.Repeat(netTurn + deg + 180f, 360f) - 180f; floatInit = false;
            Debug.Log($"[Fable] view: turn {(dir > 0 ? "right" : "left")} {TurnDegrees:F0}");
            Turned?.Invoke(deg);
        }

        public void Recentre()
        {
            Debug.Log("[Fable] view: recentre");
            Recentred?.Invoke();
            floatInit = false; netTurn = 0;
        }

        /// Test hook: press a button by its label (as a pinch on it would). Returns the labels on the bar.
        public string Press(string label)
        {
            var b = buttons.Find(x => x.Label == label || x.Label.Contains(label));
            if (b == null) return "no button " + label + "; bar: " + Describe();
            b.Act?.Invoke(); b.Flash = 1f;
            return Describe();
        }

        public string Describe() => $"view bar [{string.Join(" | ", buttons.ConvertAll(b => b.Label))}] docked={Docked} {(column ? "column" : "row")} width={bar.sizeDelta.x * scale:F2}m shown={bar.gameObject.activeSelf} hovered={HoveredLabel ?? "-"} turn={TurnDegrees:F0}";

        /// A short contextual hint above the bar, shown once per install for each key (and for `seconds`).
        public void Tip(string key, string text, float seconds = 8f)
        {
            if (!tip) return;
            var prefs = ProgressStore.LoadPrefs();
            if (key != null && prefs.HintsShown.Contains(key)) return;
            if (key != null) { prefs.HintsShown.Add(key); ProgressStore.SavePrefs(prefs); }
            tip.text = text; tipUntil = Time.time + seconds; tipRt.gameObject.SetActive(true);
        }

        // ---------------------------------------------------------------- pointing

        bool Ray(bool right, out Ray r)
        {
            r = default;
            if (right && TestRay.HasValue) { r = TestRay.Value; return true; }
#if FABLE_META_XR
            if (Input && Input.PointRay(right, out r)) return true;
#endif
#if UNITY_EDITOR || UNITY_STANDALONE
            if (right && !UnityEngine.XR.XRSettings.isDeviceActive && Camera.main && UnityEngine.InputSystem.Mouse.current != null)
            { r = Camera.main.ScreenPointToRay(UnityEngine.InputSystem.Mouse.current.position.ReadValue()); return true; }
#endif
            return false;
        }

        /// Where a hand's ray meets the bar, in bar pixels, if it does.
        bool OnBar(bool right, out Vector2 local)
        {
            local = default;
            if (!bar || !bar.gameObject.activeInHierarchy || !Ray(right, out var r)) return false;
            var plane = new Plane(-bar.forward, bar.position);
            if (!plane.Raycast(r, out float d) || d < 0 || d > 4f || Vector3.Dot(r.direction, bar.forward) <= 0) return false;
            local = bar.InverseTransformPoint(r.GetPoint(d));
            var rect = bar.rect; rect.xMin -= 10; rect.xMax += 10; rect.yMin -= 10; rect.yMax += 10;
            return rect.Contains(local);
        }

        /// True when either hand's ray rests on the bar (other pointers hide their own rays then).
        public bool RayOnBar(bool right) => OnBar(right, out _);

        int ButtonAt(Vector2 barLocal)
        {
            var world = bar.TransformPoint(barLocal);
            for (int i = 0; i < buttons.Count; i++)
            {
                var r = buttons[i].Rt.rect; r.xMin -= Pad / 2; r.xMax += Pad / 2; r.yMin -= 12; r.yMax += 12;
                if (r.Contains(buttons[i].Rt.InverseTransformPoint(world))) return i;
            }
            return -1;
        }

        /// ReaderController claimer: a pinch that starts on the bar belongs to the bar.
        bool Claim(bool right)
        {
            if (!OnBar(right, out var at)) return false;
            int i = ButtonAt(at);
            if (i >= 0) { buttons[i].Flash = 1f; buttons[i].Act?.Invoke(); }
            return true;   // on the bar but between buttons: still not a page turn
        }

        // ---------------------------------------------------------------- building

        void Build()
        {
            if (bar) return;
            var go = new GameObject("ViewBar", typeof(RectTransform));
            go.transform.SetParent(transform, false);
            canvas = go.AddComponent<Canvas>(); canvas.renderMode = RenderMode.WorldSpace; canvas.sortingOrder = 5;
            bar = (RectTransform)go.transform; bar.localScale = Vector3.one * Px; bar.sizeDelta = new Vector2(400, ButtonH + 2 * Pad);
            var bg = go.AddComponent<Image>(); bg.color = new Color(0.16f, 0.12f, 0.09f, 0.35f); bg.raycastTarget = false;

            // the hint hangs under the bar on a paper card (above it would cover the page's foot)
            var tipBg = new GameObject("Tip", typeof(RectTransform), typeof(Image)); tipRt = (RectTransform)tipBg.transform; tipRt.SetParent(bar, false);
            tipRt.anchorMin = new Vector2(0, 0); tipRt.anchorMax = new Vector2(1, 0); tipRt.pivot = new Vector2(0.5f, 1); tipRt.anchoredPosition = new Vector2(0, -8); tipRt.sizeDelta = new Vector2(120, 58);
            var tipImg = tipBg.GetComponent<Image>(); tipImg.color = new Color(0.985f, 0.96f, 0.90f, 0.97f); tipImg.raycastTarget = false;
            var t = new GameObject("Text", typeof(RectTransform)).AddComponent<TextMeshProUGUI>(); t.transform.SetParent(tipRt, false);
            t.rectTransform.anchorMin = Vector2.zero; t.rectTransform.anchorMax = Vector2.one; t.rectTransform.offsetMin = new Vector2(12, 4); t.rectTransform.offsetMax = new Vector2(-12, -4);
            if (Font) t.font = Font; t.fontSize = 19; t.color = Ink; t.alignment = TextAlignmentOptions.Center; t.textWrappingMode = TextWrappingModes.Normal; t.raycastTarget = false;
            tip = t; tipRt.gameObject.SetActive(false);

            cursor = new GameObject("BarCursor", typeof(RectTransform)).AddComponent<Image>(); cursor.transform.SetParent(bar, false);
            cursor.rectTransform.sizeDelta = new Vector2(16, 16); cursor.color = new Color(0.80f, 0.36f, 0.08f, 0.95f); cursor.raycastTarget = false; cursor.sprite = Dot();
            cursor.gameObject.SetActive(false);
            lineMat = new Material(Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color")) { color = new Color(0.62f, 0.42f, 0.10f, 0.7f) };
            var lg = new GameObject("BarRay"); lg.transform.SetParent(transform, false);
            line = lg.AddComponent<LineRenderer>(); line.material = lineMat; line.positionCount = 2; line.useWorldSpace = true; line.widthMultiplier = 0.004f; line.numCapVertices = 2;
            line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; line.receiveShadows = false; line.enabled = false;
            Rebuild();
        }

        void Rebuild()
        {
            if (!bar) return;
            foreach (var b in buttons) if (b.Rt) Destroy(b.Rt.gameObject);
            buttons.Clear();
            foreach (var (label, act) in extras) Add(label, act, 0);
            Add("‹ turn", () => Turn(-1), 92);
            Add("recentre", Recentre, 112);
            Add("turn ›", () => Turn(+1), 92);
            Layout();
        }

        /// A row (left to right, under the page) or a column (top to bottom, beside it).
        void Layout()
        {
            if (!column)
            {
                float x = Pad;
                foreach (var b in buttons) { b.Rt.pivot = new Vector2(0, 0.5f); b.Rt.sizeDelta = new Vector2(b.Width, ButtonH); b.Rt.anchoredPosition = new Vector2(x, 0); x += b.Width + Pad; }
                bar.sizeDelta = new Vector2(x, ButtonH + 2 * Pad);
                foreach (var b in buttons) b.Rt.anchoredPosition -= new Vector2(x / 2, 0);
            }
            else
            {
                float w = 0; foreach (var b in buttons) w = Mathf.Max(w, b.Width);
                float y = -Pad;
                foreach (var b in buttons) { b.Rt.pivot = new Vector2(0.5f, 1); b.Rt.sizeDelta = new Vector2(w, ButtonH); b.Rt.anchoredPosition = new Vector2(0, y); y -= ButtonH + Pad; }
                bar.sizeDelta = new Vector2(w + 2 * Pad, -y);
                foreach (var b in buttons) b.Rt.anchoredPosition += new Vector2(0, -y / 2);
            }
        }

        void Add(string label, Action act, float width)
        {
            var go = new GameObject("Btn " + label, typeof(RectTransform), typeof(Image));
            var rt = (RectTransform)go.transform; rt.SetParent(bar, false);
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f); rt.pivot = new Vector2(0, 0.5f);
            var img = go.GetComponent<Image>(); img.color = Paper; img.raycastTarget = false;
            var edge = go.AddComponent<Outline>(); edge.effectColor = Edge; edge.effectDistance = new Vector2(2, -2);
            var t = new GameObject("Label", typeof(RectTransform)).AddComponent<TextMeshProUGUI>(); t.transform.SetParent(rt, false);
            t.rectTransform.anchorMin = Vector2.zero; t.rectTransform.anchorMax = Vector2.one; t.rectTransform.offsetMin = new Vector2(6, 0); t.rectTransform.offsetMax = new Vector2(-6, 0);
            if (Font) t.font = Font; t.fontSize = 19; t.fontStyle = FontStyles.SmallCaps; t.color = Ink; t.alignment = TextAlignmentOptions.Center; t.textWrappingMode = TextWrappingModes.NoWrap; t.raycastTarget = false;
            t.text = label;
            if (width <= 0) { t.ForceMeshUpdate(); width = Mathf.Max(92, t.preferredWidth + 24); }
            rt.sizeDelta = new Vector2(width, ButtonH);
            buttons.Add(new Button { Label = label, Act = act, Rt = rt, Bg = img, Text = t, Width = width });
        }

        static Sprite Dot()
        {
            const int n = 32; var tex = new Texture2D(n, n, TextureFormat.RGBA32, false);
            var px = new Color32[n * n]; float c = (n - 1) / 2f, r = c - 1f;
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++) { float d = Mathf.Sqrt((x - c) * (x - c) + (y - c) * (y - c)); px[y * n + x] = new Color32(255, 255, 255, (byte)(255 * Mathf.Clamp01(r - d + 0.5f))); }
            tex.SetPixels32(px); tex.Apply();
            return Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
        }

        // ---------------------------------------------------------------- every frame

        bool stickArmed = true;
        /// Controllers: one push of the left thumbstick is one turn; it re-arms when the stick comes back to centre.
        void Update()
        {
#if FABLE_META_XR
            var stick = OVRInput.Get(OVRInput.Axis2D.PrimaryThumbstick, OVRInput.Controller.LTouch);
            if (stickArmed && Mathf.Abs(stick.x) > 0.6f) { stickArmed = false; Turn(stick.x > 0 ? 1 : -1); }
            else if (Mathf.Abs(stick.x) < 0.3f) stickArmed = true;
#endif
        }

        void LateUpdate()
        {
            if (!bar || !Head) return;
            bool quiet = Quiet != null && Quiet();
            if (bar.gameObject.activeSelf == quiet) bar.gameObject.SetActive(!quiet);
            if (quiet) { hovered = -1; line.enabled = false; return; }
            Place();
            // hover: which button the ray rests on (right hand first)
            hovered = -1; Vector2 at = default; bool on = false;
            foreach (var right in new[] { true, false }) if (OnBar(right, out at)) { on = true; hoverRight = right; break; }
            if (on) hovered = ButtonAt(at);
            cursor.gameObject.SetActive(on); line.enabled = on;
            if (on)
            {
                cursor.rectTransform.anchoredPosition = at; cursor.transform.SetAsLastSibling();
                cursor.rectTransform.sizeDelta = Vector2.one * (hovered >= 0 ? 24f : 14f);
                if (Ray(hoverRight, out var r)) { line.SetPosition(0, r.origin + r.direction * 0.04f); line.SetPosition(1, bar.TransformPoint(at)); }
            }
            for (int i = 0; i < buttons.Count; i++)
            {
                var b = buttons[i]; b.Flash = Mathf.MoveTowards(b.Flash, 0, Time.deltaTime * 3f);
                var c = Color.Lerp(i == hovered ? Lit : Paper, new Color(0.95f, 0.66f, 0.25f, 1f), b.Flash);
                if (b.Bg.color != c) b.Bg.color = c;
            }
            if (tipRt.gameObject.activeSelf && Time.time > tipUntil) tipRt.gameObject.SetActive(false);
        }

        /// Docked under the panel while the panel is in front of the reader; otherwise floating low in front of them,
        /// following their facing lazily (it moves only once they have turned well away from it).
        void Place()
        {
            var fwd = Vector3.ProjectOnPlane(Head.forward, Vector3.up).normalized; if (fwd.sqrMagnitude < 0.01f) fwd = Vector3.forward;
            bool dockOk = Dock && Dock.gameObject.activeInHierarchy && Mathf.Abs(netTurn) < 1f;
            if (dockOk)
            {
                var toDock = Vector3.ProjectOnPlane(Dock.position - Head.position, Vector3.up);
                dockOk = toDock.sqrMagnitude > 0.01f && Vector3.Angle(fwd, toDock) < DockedWithinDegrees && toDock.magnitude < 3f;
            }
            Vector3 pos; Quaternion rot;
            if (dockOk)
            {
                var r = Dock.rect; var ps = Dock.lossyScale;
                rot = Dock.rotation;
                // a row under the page, no wider than it; where the table leaves no room under the page, a column
                // beside its lower left corner. Never in front of the page: it must not cover the text or a Peek model.
                SetColumn(false);
                scale = Mathf.Min(Px, r.width * ps.x / bar.sizeDelta.x);
                float half = bar.sizeDelta.y * scale * 0.5f;
                pos = Dock.TransformPoint(new Vector3(r.center.x, r.yMin, 0)) - Dock.up * (DockGapMetres + half) - Dock.forward * 0.005f;
                if (pos.y - half < MinY)
                {
                    SetColumn(true);
                    scale = Mathf.Min(Px, r.height * ps.y * 0.55f / bar.sizeDelta.y);
                    float hw = bar.sizeDelta.x * scale * 0.5f; half = bar.sizeDelta.y * scale * 0.5f;
                    pos = Dock.TransformPoint(new Vector3(r.xMin, r.yMin, 0)) - Dock.right * (DockGapMetres + hw) + Dock.up * half - Dock.forward * 0.005f;
                    if (pos.y - half < MinY) pos.y = MinY + half + 0.01f;
                }
            }
            else
            {
                SetColumn(false); scale = Px;
                if (!floatInit || Vector3.Angle(fwd, Vector3.ProjectOnPlane(floatPos - Head.position, Vector3.up)) > FollowDeadZone)
                {
                    floatPos = Head.position + fwd * FloatForward + Vector3.down * FloatDrop;
                    floatPos.y = Mathf.Max(floatPos.y, MinY + bar.sizeDelta.y * Px * 0.5f + 0.01f);
                    floatRot = Quaternion.LookRotation(floatPos - Head.position, Vector3.up);
                    if (!floatInit) { bar.position = floatPos; bar.rotation = floatRot; }
                    floatInit = true;
                }
                pos = floatPos; rot = floatRot;
            }
            if (dockOk != Docked) Docked = dockOk;
            float k = 1f - Mathf.Exp(-Time.deltaTime * 7f);
            bar.position = Vector3.Lerp(bar.position, pos, k);
            bar.rotation = Quaternion.Slerp(bar.rotation, rot, k);
            if (!Mathf.Approximately(bar.localScale.x, scale)) bar.localScale = Vector3.one * scale;
        }

        void SetColumn(bool on) { if (column == on) return; column = on; Layout(); }
    }
}
