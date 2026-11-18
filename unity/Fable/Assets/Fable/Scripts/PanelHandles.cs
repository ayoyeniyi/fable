// Visible handles on the reading page:
//   the bar under the page    point at it, pinch and hold, move the hand: the page goes where you take it
//   the corner at bottom right    pinch and hold, move away from the page's centre or towards it: bigger or smaller
//   the arrows beside the page    pinch either one, with either hand: the page turns that way (a reminder that the
//                                 right hand's pinch turns forward and the left hand's back)
// All take the pinch for themselves (ReaderController.Claimers), so moving the page never turns it or highlights.
// The handles brighten when the ray rests on them and while they are held. The size is saved in the reader's
// preferences; "recentre" on the view toolbar brings a moved page back in front of the reader.
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Fable
{
    public class PanelHandles : MonoBehaviour
    {
        public ReadingPanel Panel;
        public PagePointer Pointer;
        public ReaderController Input;
        public Transform Head;
        public Color Idle = new(0.80f, 0.50f, 0.15f, 0.70f), Hover = new(0.80f, 0.50f, 0.15f, 0.95f), Held = new(0.95f, 0.66f, 0.25f, 1f);

        /// Raised when the X at the page's top right is pinched: the reader puts the book down for a while.
        public event System.Action PutDown;
        /// Raised when the "reading rooms" button above the page is pinched.
        public event System.Action OpenRooms;
        /// Raised when an arrow is pinched: true = next page, false = previous.
        public event System.Action<bool> Turn;
        /// Shown only while the page is a book page (not a scene's passage): set by the flow each frame.
        public bool ArrowsVisible = true;

        /// Editor tests: stands in for the pinch of the hand that holds a handle (null = live input).
        public bool? TestPinch;
        public string State => held == 1 ? "moving" : held == 2 ? "resizing" : hover == 1 ? "over move" : hover == 2 ? "over resize" : "idle";

        RectTransform page, moveBar, corner, prevArrow, nextArrow, roomsBtn, closeBtn, quitBtn; Image moveImg, cornerImg, prevImg, nextImg, roomsImg, closeImg, quitImg; TMP_Text quitLbl; float quitAsked = -10f; TMP_Text roomsLbl; TMP_Text moveLbl;
        int hover, held; bool heldRight;
        float grabDist; Vector3 grabOffset;                // moving: ray distance and the page's offset from the ray point
        float startScale, startRadius; Plane grabPlane;    // resizing

        public void Init(ReadingPanel panel, PagePointer pointer, ReaderController input, Transform head)
        {
            Panel = panel; Pointer = pointer; Input = input; Head = head; page = (RectTransform)panel.transform;
            Build();
            if (Input && !Input.Claimers.Contains(Claim)) Input.Claimers.Add(Claim);
            if (Pointer && !Pointer.Targets.Contains(RayTarget)) Pointer.Targets.Add(RayTarget);
        }
        void OnDestroy() { if (Input) Input.Claimers.Remove(Claim); if (Pointer) Pointer.Targets.Remove(RayTarget); }

        /// For the page pointer: where this hand's ray meets a handle or arrow (outside the page, where it draws no cursor).
        Vector3? RayTarget(bool right) => OnPlane(right, out var w, out _) && (HandleAt(w) != 0 || (held != 0 && heldRight == right)) ? w : null;

        void Build()
        {
            if (moveBar) return;
            var font = Panel.Body ? Panel.Body.font : null;
            moveBar = new GameObject("HandleMove", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>();
            moveBar.SetParent(page, false); moveBar.anchorMin = moveBar.anchorMax = new Vector2(0.5f, 0); moveBar.pivot = new Vector2(0.5f, 1);
            moveBar.anchoredPosition = new Vector2(0, -14); moveBar.sizeDelta = new Vector2(190, 16);
            moveImg = moveBar.GetComponent<Image>(); moveImg.color = Idle; moveImg.raycastTarget = false; moveImg.sprite = Pill(); moveImg.type = Image.Type.Sliced;
            moveLbl = new GameObject("Label", typeof(RectTransform)).AddComponent<TextMeshProUGUI>(); moveLbl.transform.SetParent(moveBar, false);
            moveLbl.rectTransform.anchorMin = moveLbl.rectTransform.anchorMax = new Vector2(0.5f, 0); moveLbl.rectTransform.pivot = new Vector2(0.5f, 1);
            moveLbl.rectTransform.anchoredPosition = new Vector2(0, -2); moveLbl.rectTransform.sizeDelta = new Vector2(240, 20);
            if (font) moveLbl.font = font; moveLbl.fontSize = 13; moveLbl.fontStyle = FontStyles.SmallCaps; moveLbl.alignment = TextAlignmentOptions.Top; moveLbl.color = new Color(0.9f, 0.85f, 0.75f, 0.0f); moveLbl.raycastTarget = false;
            moveLbl.text = "pinch and hold to move";
            corner = new GameObject("HandleResize", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>();
            corner.SetParent(page, false); corner.anchorMin = corner.anchorMax = new Vector2(1, 0); corner.pivot = new Vector2(0, 1);
            corner.anchoredPosition = new Vector2(4, -4); corner.sizeDelta = new Vector2(40, 40);
            cornerImg = corner.GetComponent<Image>(); cornerImg.color = Idle; cornerImg.raycastTarget = false; cornerImg.sprite = Corner();
            // above the middle of each side, clear of the toolbar's column beside the page's lower left (ViewControls)
            prevArrow = Arrow("ArrowPrev", 0f, -1, out prevImg); nextArrow = Arrow("ArrowNext", 1f, 1, out nextImg);
            // the reading rooms, on their own above the page where the eye already is
            roomsBtn = new GameObject("RoomsButton", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>();
            roomsBtn.SetParent(page, false); roomsBtn.anchorMin = roomsBtn.anchorMax = new Vector2(0.5f, 1); roomsBtn.pivot = new Vector2(0.5f, 0);
            roomsBtn.anchoredPosition = new Vector2(0, 18); roomsBtn.sizeDelta = new Vector2(260, 52);
            roomsImg = roomsBtn.GetComponent<Image>(); roomsImg.color = RoomsIdle; roomsImg.raycastTarget = false; roomsImg.sprite = Pill(); roomsImg.type = Image.Type.Sliced;
            roomsLbl = new GameObject("Label", typeof(RectTransform)).AddComponent<TextMeshProUGUI>(); roomsLbl.transform.SetParent(roomsBtn, false);
            roomsLbl.rectTransform.anchorMin = Vector2.zero; roomsLbl.rectTransform.anchorMax = Vector2.one; roomsLbl.rectTransform.offsetMin = roomsLbl.rectTransform.offsetMax = Vector2.zero;
            if (font) roomsLbl.font = font; roomsLbl.fontSize = 24; roomsLbl.fontStyle = FontStyles.SmallCaps; roomsLbl.alignment = TextAlignmentOptions.Center;
            roomsLbl.color = new Color(1f, 0.96f, 0.88f, 1f); roomsLbl.raycastTarget = false; roomsLbl.text = "reading rooms";
            // quit Fable: top right, beside the reading rooms; a second pinch within 4 s confirms
            quitBtn = new GameObject("QuitButton", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>();
            quitBtn.SetParent(page, false); quitBtn.anchorMin = quitBtn.anchorMax = new Vector2(1, 1); quitBtn.pivot = new Vector2(1, 0);
            quitBtn.anchoredPosition = new Vector2(0, 22); quitBtn.sizeDelta = new Vector2(150, 44);
            quitImg = quitBtn.GetComponent<Image>(); quitImg.color = QuitIdle; quitImg.raycastTarget = false; quitImg.sprite = Pill(); quitImg.type = Image.Type.Sliced;
            quitLbl = new GameObject("Label", typeof(RectTransform)).AddComponent<TextMeshProUGUI>(); quitLbl.transform.SetParent(quitBtn, false);
            quitLbl.rectTransform.anchorMin = Vector2.zero; quitLbl.rectTransform.anchorMax = Vector2.one; quitLbl.rectTransform.offsetMin = quitLbl.rectTransform.offsetMax = Vector2.zero;
            if (font) quitLbl.font = font; quitLbl.fontSize = 20; quitLbl.fontStyle = FontStyles.SmallCaps; quitLbl.alignment = TextAlignmentOptions.Center;
            quitLbl.color = new Color(1f, 0.96f, 0.88f, 1f); quitLbl.raycastTarget = false; quitLbl.text = "quit Fable";
            // put the book down: an X just outside the page's top right corner
            closeBtn = new GameObject("CloseButton", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>();
            closeBtn.SetParent(page, false); closeBtn.anchorMin = closeBtn.anchorMax = new Vector2(1, 1); closeBtn.pivot = new Vector2(0, 0);
            closeBtn.anchoredPosition = new Vector2(6, 6); closeBtn.sizeDelta = new Vector2(40, 40);
            closeImg = closeBtn.GetComponent<Image>(); closeImg.color = Idle; closeImg.raycastTarget = false; closeImg.sprite = Cross();
        }

        static readonly Color QuitIdle = new(0.30f, 0.22f, 0.16f, 0.88f), QuitHover = new(0.55f, 0.24f, 0.14f, 0.98f);
        static readonly Color RoomsIdle = new(0.72f, 0.42f, 0.12f, 0.92f), RoomsHover = new(0.90f, 0.56f, 0.18f, 1f);

        RectTransform Arrow(string name, float side, int dir, out Image img)
        {
            var rt = new GameObject(name, typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>();
            rt.SetParent(page, false); rt.anchorMin = rt.anchorMax = new Vector2(side, 0.62f); rt.pivot = new Vector2(side == 0 ? 1 : 0, 0.5f);
            rt.anchoredPosition = new Vector2(dir * 16, 0); rt.sizeDelta = new Vector2(34, 60);
            img = rt.GetComponent<Image>(); img.color = Idle; img.raycastTarget = false; img.sprite = Chevron(dir > 0);
            return rt;
        }

        /// Where a hand's ray meets the page's plane (not limited to the page's rectangle: the handles sit outside it).
        bool OnPlane(bool right, out Vector3 world, out Ray ray)
        {
            world = default; ray = default;
            if (!Pointer || !page.gameObject.activeInHierarchy || !Pointer.Ray(right, out ray)) return false;
            var plane = new Plane(-page.forward, page.position);
            if (!plane.Raycast(ray, out float d) || d < 0 || d > 4f || Vector3.Dot(ray.direction, page.forward) <= 0) return false;
            world = ray.GetPoint(d); return true;
        }

        int HandleAt(Vector3 world)
        {
            bool In(RectTransform rt, float pad) { var r = rt.rect; r.xMin -= pad; r.xMax += pad; r.yMin -= pad; r.yMax += pad; return r.Contains(rt.InverseTransformPoint(world)); }
            if (In(corner, 14)) return 2;
            if (In(moveBar, 16)) return 1;
            if (ArrowsVisible && In(closeBtn, 14)) return 6;
            if (ArrowsVisible && In(quitBtn, 8)) return 7;
            if (ArrowsVisible && In(roomsBtn, 10)) return 5;
            if (ArrowsVisible && In(prevArrow, 18)) return 3;
            if (ArrowsVisible && In(nextArrow, 18)) return 4;
            return 0;
        }

        /// True when either hand's ray rests on a handle (the page pointer shows its cursor as over a control then).
        public bool Over(bool right) => OnPlane(right, out var w, out _) && HandleAt(w) != 0;

        bool Claim(bool right)
        {
            if (!OnPlane(right, out var w, out var ray)) return false;
            int h = HandleAt(w); if (h == 0) return false;
            if (h == 7)
            {
                if (Time.time - quitAsked < 4f) { FlowController.QuitFable(); return true; }
                quitAsked = Time.time; Debug.Log("[Fable] page: quit asked"); return true;
            }
            if (h == 6) { Debug.Log("[Fable] page: put the book down"); PutDown?.Invoke(); return true; }
            if (h == 5) { Debug.Log("[Fable] page: reading rooms"); OpenRooms?.Invoke(); return true; }
            if (h >= 3) { Debug.Log($"[Fable] page arrow: {(h == 4 ? "next" : "previous")}"); Turn?.Invoke(h == 4); return true; }
            held = h; heldRight = right;
            if (h == 1) { grabDist = Vector3.Distance(ray.origin, w); grabOffset = page.position - w; }
            else { grabPlane = new Plane(-page.forward, page.position); startScale = Panel.UserScale; startRadius = Mathf.Max(0.05f, Vector3.Distance(w, page.position)); }
            Debug.Log($"[Fable] page handle: {(h == 1 ? "move" : "resize")} ({(right ? "right" : "left")} hand)");
            return true;
        }

        bool Pinching(bool right) => TestPinch ?? (right ? Input.RightPinching : Input.LeftPinching);

        void Update()
        {
            if (!page) return;
            if (held != 0)
            {
                if (!Pinching(heldRight)) { Release(); }
                else if (Pointer.Ray(heldRight, out var ray))
                {
                    if (held == 1) Panel.PlaceAt(ray.GetPoint(grabDist) + grabOffset);
                    else if (grabPlane.Raycast(ray, out float d))
                    {
                        float r = Vector3.Distance(ray.GetPoint(d), page.position);
                        Panel.UserScale = Mathf.Clamp(startScale * r / startRadius, ReadingPanel.MinUserScale, ReadingPanel.MaxUserScale);
                    }
                }
            }
            hover = 0;
            foreach (var right in new[] { true, false }) if (OnPlane(right, out var w, out _)) { hover = HandleAt(w); if (hover != 0) break; }
            moveImg.color = held == 1 ? Held : hover == 1 ? Hover : Idle;
            cornerImg.color = held == 2 ? Held : hover == 2 ? Hover : Idle;
            if (prevArrow.gameObject.activeSelf != ArrowsVisible) { prevArrow.gameObject.SetActive(ArrowsVisible); nextArrow.gameObject.SetActive(ArrowsVisible); roomsBtn.gameObject.SetActive(ArrowsVisible); closeBtn.gameObject.SetActive(ArrowsVisible); quitBtn.gameObject.SetActive(ArrowsVisible); }
            closeImg.color = hover == 6 ? Hover : Idle;
            bool asking = Time.time - quitAsked < 4f;
            quitImg.color = asking || hover == 7 ? QuitHover : QuitIdle;
            var ql = asking ? "pinch again to quit" : "quit Fable"; if (quitLbl.text != ql) { quitLbl.text = ql; quitLbl.fontSize = asking ? 15 : 20; quitBtn.sizeDelta = new Vector2(asking ? 170 : 150, 44); }   // never wider than the gap to the rooms button
            roomsImg.color = hover == 5 ? RoomsHover : RoomsIdle; roomsBtn.localScale = Vector3.one * (hover == 5 ? 1.06f : 1f);
            prevImg.color = hover == 3 ? Hover : Idle; nextImg.color = hover == 4 ? Hover : Idle;
            moveBar.sizeDelta = new Vector2(held == 1 || hover == 1 ? 230 : 190, held == 1 || hover == 1 ? 20 : 16);
            var lc = moveLbl.color; float a = hover == 1 && held == 0 ? 1f : 0f; if (!Mathf.Approximately(lc.a, a)) moveLbl.color = new Color(lc.r, lc.g, lc.b, Mathf.MoveTowards(lc.a, a, Time.deltaTime * 4f));
        }

        void Release()
        {
            if (held == 2) { var p = ProgressStore.LoadPrefs(); p.PanelScale = Panel.UserScale; ProgressStore.SavePrefs(p); Debug.Log($"[Fable] page size {Panel.UserScale:F2} (saved)"); }
            held = 0;
        }

        /// Test hooks: grab a handle with the test ray, move to a world point, let go.
        public string TestGrab(bool resize) { var rt = resize ? corner : moveBar; Pointer.AimAt(rt.TransformPoint(rt.rect.center)); TestPinch = true; return Claim(true) ? State : "missed"; }
        public void TestRelease() { TestPinch = false; Update(); TestPinch = null; }

        static Sprite Pill()
        {
            const int w = 64, h = 32; var tex = new Texture2D(w, h, TextureFormat.RGBA32, false); var px = new Color32[w * h];
            for (int y = 0; y < h; y++) for (int x = 0; x < w; x++)
            {
                float cx = Mathf.Clamp(x, h / 2f, w - h / 2f), d = Mathf.Sqrt((x - cx) * (x - cx) + (y - h / 2f) * (y - h / 2f));
                px[y * w + x] = new Color32(255, 255, 255, (byte)(255 * Mathf.Clamp01(h / 2f - 1 - d + 0.5f)));
            }
            tex.SetPixels32(px); tex.Apply();
            return Sprite.Create(tex, new Rect(0, 0, w, h), new Vector2(0.5f, 0.5f), 100f, 0, SpriteMeshType.FullRect, new Vector4(16, 0, 16, 0));
        }

        /// An X in a ring: put the book down.
        static Sprite Cross()
        {
            const int n = 40; var tex = new Texture2D(n, n, TextureFormat.RGBA32, false); var px = new Color32[n * n]; float c = (n - 1) / 2f;
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float dx = x - c, dy = y - c, r = Mathf.Sqrt(dx * dx + dy * dy);
                float ring = Mathf.Clamp01(2.2f - Mathf.Abs(r - (c - 2.5f)));
                float diag = Mathf.Min(Mathf.Abs(dx - dy), Mathf.Abs(dx + dy)) / 1.414f;
                float cross = r < c - 9 ? Mathf.Clamp01(3.2f - diag) : 0f;
                px[y * n + x] = new Color32(255, 255, 255, (byte)(255 * Mathf.Max(ring, cross)));
            }
            tex.SetPixels32(px); tex.Apply();
            return Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
        }

        /// A chevron: '>' pointing right when next, '<' when previous.
        static Sprite Chevron(bool right)
        {
            const int w = 34, h = 60; var tex = new Texture2D(w, h, TextureFormat.RGBA32, false); var px = new Color32[w * h];
            for (int y = 0; y < h; y++) for (int x = 0; x < w; x++)
            {
                float u = right ? x : w - 1 - x, t = Mathf.Abs(y - (h - 1) / 2f);   // distance from the middle row
                float d = Mathf.Abs(u - (w - 6 - t * (w - 12) / ((h - 1) / 2f)));    // from the line tip -> corners
                px[y * w + x] = new Color32(255, 255, 255, (byte)(255 * Mathf.Clamp01(4.5f - d)));
            }
            tex.SetPixels32(px); tex.Apply();
            return Sprite.Create(tex, new Rect(0, 0, w, h), new Vector2(0.5f, 0.5f), 100f);
        }

        /// An L-shaped bracket: the page's corner, drawn outside it.
        static Sprite Corner()
        {
            const int n = 48; var tex = new Texture2D(n, n, TextureFormat.RGBA32, false); var px = new Color32[n * n];
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                // the box's top-left touches the page's corner; the bracket is its right column and bottom row, with a tick
                bool bar = (x >= n - 12 && x < n - 2 && y >= 2) || (y >= 2 && y < 12 && x < n - 2);
                bool tick = Mathf.Abs((n - x) - y) < 3 && x > n / 2 && y < n / 2;
                px[y * n + x] = new Color32(255, 255, 255, (byte)(bar || tick ? 255 : 0));
            }
            tex.SetPixels32(px); tex.Apply();
            return Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
        }
    }
}
