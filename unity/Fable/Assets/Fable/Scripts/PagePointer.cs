// Where each hand points on the reading page. Hands use the system pointer pose (the same ray the Quest's own menus
// use), controllers their own forward ray; in the editor the mouse stands in for the right hand. A thin ray runs from
// the hand to the page and a dot marks where it lands, growing when it rests on a control, so the reader can see what
// a pinch will press. Controls are padded a little: a hand held in the air is never pixel-steady.
using UnityEngine;
using UnityEngine.UI;

namespace Fable
{
    public class PagePointer : MonoBehaviour
    {
        public ReaderController Reader;
        public RectTransform Page;          // the reading panel's canvas
        public float MaxDistance = 3f, Padding = 16f;   // Padding: extra page pixels around each control that still count as over it
        public Color Dot = new(0.62f, 0.42f, 0.10f, 0.85f);

        Image cursor; LineRenderer ray; Material rayMat; BookReader reader;

        /// Editor tests: a right-hand ray to use instead of the hand or mouse (null = live input).
        public Ray? TestRay;

        /// Test helper: aim the right-hand ray from the head camera at a point on the page.
        public void AimAt(Vector3 world) { var cam = Camera.main; if (cam) TestRay = new Ray(cam.transform.position, (world - cam.transform.position).normalized); }

        void Start()
        {
            if (!Page) return;
            cursor = new GameObject("PageCursor", typeof(RectTransform)).AddComponent<Image>();
            cursor.transform.SetParent(Page, false);
            cursor.rectTransform.sizeDelta = new Vector2(14, 14);
            cursor.sprite = MakeDot(); cursor.color = Dot; cursor.raycastTarget = false;
            cursor.gameObject.SetActive(false);
            var shader = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
            rayMat = new Material(shader) { color = new Color(Dot.r, Dot.g, Dot.b, 0.7f) };
            var lg = new GameObject("PageRay"); lg.transform.SetParent(transform, false);
            ray = lg.AddComponent<LineRenderer>(); ray.material = rayMat; ray.positionCount = 2; ray.useWorldSpace = true; ray.widthMultiplier = 0.004f; ray.numCapVertices = 2;
            ray.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; ray.receiveShadows = false; ray.enabled = false;
            reader = FindFirstObjectByType<BookReader>();
        }

        /// The ray a hand is pointing along, if that hand is tracked (or the mouse, in the editor without a headset).
        public bool Ray(bool right, out Ray ray)
        {
            ray = default;
            if (right && TestRay.HasValue) { ray = TestRay.Value; return true; }
#if FABLE_META_XR
            if (Reader && Reader.PointRay(right, out ray)) return true;
#endif
#if UNITY_EDITOR || UNITY_STANDALONE
            if (right && !UnityEngine.XR.XRSettings.isDeviceActive && Camera.main && UnityEngine.InputSystem.Mouse.current != null)
            {
                ray = Camera.main.ScreenPointToRay(UnityEngine.InputSystem.Mouse.current.position.ReadValue());
                return true;
            }
#endif
            return false;
        }

        /// Where a hand's ray meets the page plane, in the page's local units (pixels), or false if it misses.
        public bool OnPage(bool right, out Vector2 local)
        {
            local = default;
            if (!Page || !Page.gameObject.activeInHierarchy || !Ray(right, out var ray)) return false;
            var plane = new Plane(-Page.forward, Page.position);
            if (!plane.Raycast(ray, out float d) || d > MaxDistance || d < 0) return false;
            if (Vector3.Dot(ray.direction, Page.forward) <= 0) return false;   // pointing at the back of the page
            local = Page.InverseTransformPoint(ray.GetPoint(d));
            return Page.rect.Contains(local);
        }

        /// True when a hand points inside a rect on the page (a control's RectTransform).
        public bool Over(bool right, RectTransform target)
        {
            if (!target || !target.gameObject.activeInHierarchy || !OnPage(right, out var local)) return false;
            var world = Page.TransformPoint(local);
            var r = target.rect; r.xMin -= Padding; r.xMax += Padding; r.yMin -= Padding; r.yMax += Padding;
            return r.Contains(target.InverseTransformPoint(world));
        }

        void LateUpdate()
        {
            if (!cursor) return;
            bool right = true;
            bool on = OnPage(true, out var p); if (!on) { right = false; on = OnPage(false, out p); }
            cursor.gameObject.SetActive(on);
            if (ray) ray.enabled = on;
            if (!on) return;
            bool overControl = reader && reader.Active && (reader.PressAt(right, dryRun: true) || reader.OverStepIn(right));
            cursor.rectTransform.localPosition = new Vector3(p.x, p.y, -1f); cursor.transform.SetAsLastSibling();
            cursor.rectTransform.sizeDelta = Vector2.one * (overControl ? 26f : 16f);
            cursor.color = overControl ? new Color(0.80f, 0.36f, 0.08f, 0.95f) : Dot;
            if (Ray(right, out var r)) { ray.SetPosition(0, r.origin + r.direction * 0.04f); ray.SetPosition(1, Page.TransformPoint(new Vector3(p.x, p.y, -1f))); }
        }

        static Sprite MakeDot()
        {
            const int n = 32; var tex = new Texture2D(n, n, TextureFormat.RGBA32, false);
            var px = new Color32[n * n]; float c = (n - 1) / 2f, r = c - 1f;
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float d = Mathf.Sqrt((x - c) * (x - c) + (y - c) * (y - c));
                px[y * n + x] = new Color32(255, 255, 255, (byte)(255 * Mathf.Clamp01(r - d + 0.5f)));
            }
            tex.SetPixels32(px); tex.Apply();
            return Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100f);
        }
    }
}
