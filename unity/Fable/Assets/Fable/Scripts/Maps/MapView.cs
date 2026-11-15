// One view of a book's map, built for Peek (docs/MAPS_HEADSET.md): a globe on its brass stand, or a scroll that unrolls,
// with a pin for every place the reader has reached and the matched place's pin lit and labelled.
//
//   globe   UV sphere (64 x 32) in the stand's axis, Earth texture u = 0 at longitude -180, v = 0 at the south pole
//           (Unity's flip of the image's top row); it turns on open so the lit pin faces the reader, and by hand.
//   scroll  the glTF scroll fitted to the image's aspect (docs/MAP_PROPS.md FitMap); it unrolls from the middle with the
//           sheet's U range cropped, so the image keeps its true scale as the rollers part.
//   pins    one combined mesh for every dim pin (one draw call; places closer than PinMerge on the globe share a pin),
//           one lit pin with its own material whose glow pulses. Pointing at a pin shows its name.
//
// The view owns everything it makes (meshes, materials, labels) and frees it in OnDestroy; the props' shared assets and
// the map images (BookMap) are not touched. Nothing is allocated per frame.
using System.Collections.Generic;
using TMPro;
using UnityEngine;

namespace Fable
{
    public class MapView : MonoBehaviour
    {
        /// Globe size: the stand is made for a 0.18 m radius sphere, 0.52 m tall; shown at this scale (radius 0.126 m, 0.36 m tall).
        public const float GlobeScale = 0.7f;
        /// Scroll sheet width and the most it may stand tall (metres).
        public const float ScrollWidth = 0.44f, ScrollMaxHeight = 0.34f;
        /// Globe places closer than this (degrees) share one dim pin.
        const float PinMerge = 2.2f;
        /// How far the stand turns (degrees) to lean the pole toward or away from the reader.
        const float StandTurn = 38f;
        const float SphereRadius = 0.18f, PinHead = 0.0205f, PinHeadRadius = 0.0045f;

        public MapDoc.View View { get; private set; }
        public MapDoc.Place Lit { get; private set; }
        public bool Globe => View != null && View.Globe;
        /// Bounds in the Peek root's space at full size (for the hand's ray), computed once.
        public Bounds Bounds { get; private set; }
        public int Triangles { get; private set; }
        public int PinCount { get; private set; }
        /// The name under the pointer, or null.
        public string Hovered { get; private set; }
        public bool Settled => anim >= 1f;

        PagePointer pointer;
        readonly List<Object> owned = new();
        Transform spinner, pinsRoot, litPin; float spin, spinFrom, spinTo, anim, animSeconds;
        Material surface, dimMat, litMat; GameObject dimPins; Vector3 litScale;
        // scroll
        Transform sheet, rollL, rollR, fLT, fLB, fRT, fRB; float sx = 1f, rollZ, fullW, fullH;
        // pins under the pointer
        readonly List<Vector3> heads = new(); readonly List<string> headNames = new();
        TextMeshPro label, hoverLabel; LineRenderer line; int hoverIndex = -1;

        static Mesh sphereMesh, pinMesh;
        static readonly Dictionary<Material, Material> capped = new();

        // ---------------------------------------------------------------- building

        /// Build the view under `root` (the Peek root, its +Z pointing away from the reader). tex is the view's image.
        public static MapView Build(Transform root, MapDoc doc, MapDoc.View view, MapDoc.Place lit, int revealedUpTo, Texture2D tex, PagePointer pointer, TMP_FontAsset font)
        {
            var assets = MapAssets.Get();
            if (!assets || !assets.Props || !assets.MapShader) { Debug.LogWarning("[Fable] map: Resources/MapAssets is missing (FableBuild.SyncData)"); return null; }
            var go = new GameObject("Peek map");
            go.transform.SetParent(root, false);
            var v = go.AddComponent<MapView>();
            v.View = view; v.Lit = lit; v.pointer = pointer;
            v.surface = v.Own(new Material(assets.MapShader) { name = "Map surface" });
            v.surface.SetTexture("_BaseMap", tex);
            v.dimMat = v.Own(new Material(assets.MapShader) { name = "Map pins" });
            v.dimMat.SetFloat("_VertexTint", 1); v.dimMat.SetColor("_Color", new Color(0.62f, 0.52f, 0.46f)); v.dimMat.SetFloat("_Spec", 0.25f);
            v.litMat = v.Own(new Material(assets.MapShader) { name = "Map lit pin" });
            v.litMat.SetFloat("_VertexTint", 1); v.litMat.SetFloat("_Spec", 0.6f); v.litMat.SetColor("_EmitColor", new Color(1f, 0.30f, 0.16f));
            PinMeshFrom(assets.Props.transform);
            if (view.Globe) v.BuildGlobe(assets, doc, revealedUpTo);
            else v.BuildScroll(assets, doc, revealedUpTo);
            v.BuildLabels(font);
            v.Bounds = ClayBuilder.Bounds(go.transform, root);
            v.Triangles = 0;
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>(true)) if (mf.sharedMesh) for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) v.Triangles += (int)mf.sharedMesh.GetIndexCount(s) / 3;
            v.anim = 0; v.Tick(0);
            return v;
        }

        T Own<T>(T o) where T : Object { owned.Add(o); return o; }

        void OnDestroy() { foreach (var o in owned) if (o) Destroy(o); owned.Clear(); }

        static Transform Find(Transform t, string name)
        {
            if (t.name == name) return t;
            foreach (Transform c in t) { var f = Find(c, name); if (f) return f; }
            return null;
        }

        /// The props drawn with the map's own shader, so they read the same in a dark room and a bright field and need
        /// no light: walnut and parchment keep their painted textures, brass becomes a warm flat brass with a little
        /// gloss (the glTF brass is fully metallic and renders black or blown out with the room hidden). Made once and
        /// shared by every map opened in the session.
        static void Restyle(Transform t, Shader shader)
        {
            foreach (var r in t.GetComponentsInChildren<Renderer>(true))
            {
                var ms = r.sharedMaterials;
                for (int i = 0; i < ms.Length; i++)
                {
                    var m = ms[i]; if (!m) continue;
                    if (!capped.TryGetValue(m, out var c))
                    {
                        c = new Material(shader) { name = "Map " + m.name };
                        if (m.name.Contains("Brass")) { c.SetColor("_Color", new Color(0.66f, 0.48f, 0.21f)); c.SetFloat("_Spec", 0.45f); c.SetFloat("_Self", 1.05f); }
                        else
                        {
                            if (m.HasProperty("baseColorTexture")) c.SetTexture("_BaseMap", m.GetTexture("baseColorTexture"));
                            if (m.HasProperty("baseColorFactor")) c.SetColor("_Color", m.GetColor("baseColorFactor"));
                            c.SetFloat("_Spec", m.name.Contains("Walnut") ? 0.1f : 0.03f); c.SetFloat("_Self", 0.9f);
                        }
                        capped[m] = c;
                    }
                    ms[i] = c;
                }
                r.sharedMaterials = ms;
                r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            }
        }

        /// The glTF pin (glass head submesh 0, brass needle submesh 1) as one submesh with the colours in its vertices:
        /// alpha 1 on the head marks where the lit pin glows.
        static void PinMeshFrom(Transform props)
        {
            if (pinMesh) return;
            var src = Find(props, "pin").GetComponent<MeshFilter>().sharedMesh;
            var verts = src.vertices; var normals = src.normals; var cols = new Color[verts.Length];
            var tris = new List<int>();
            for (int s = 0; s < src.subMeshCount; s++)
            {
                var idx = src.GetTriangles(s);
                var col = s == 0 ? new Color(0.86f, 0.10f, 0.08f, 1f) : new Color(0.72f, 0.56f, 0.26f, 0f);
                foreach (var i in idx) cols[i] = col;
                tris.AddRange(idx);
            }
            pinMesh = new Mesh { name = "Map pin" };
            pinMesh.vertices = verts; pinMesh.normals = normals; pinMesh.colors = cols; pinMesh.SetTriangles(tris, 0);
            pinMesh.RecalculateBounds();
        }

        Transform Instance(MapAssets assets, string node, Transform parent)
        {
            var t = Instantiate(Find(assets.Props.transform, node).gameObject, parent).transform;
            t.name = node; t.localPosition = Vector3.zero; t.localRotation = Quaternion.identity; t.localScale = Vector3.one;
            Restyle(t, assets.MapShader);
            return t;
        }

        // ---- globe

        static Vector3 Dir(float lat, float lon)
        {
            float a = lat * Mathf.Deg2Rad, b = lon * Mathf.Deg2Rad;
            // seen from outside with north up, east is to the right: lon 0 faces -Z, lon +90 faces +X
            return new Vector3(Mathf.Cos(a) * Mathf.Sin(b), Mathf.Sin(a), -Mathf.Cos(a) * Mathf.Cos(b));
        }

        static Mesh Sphere()
        {
            if (sphereMesh) return sphereMesh;
            const int seg = 64, rings = 32;
            var v = new Vector3[(seg + 1) * (rings + 1)]; var n = new Vector3[v.Length]; var uv = new Vector2[v.Length];
            for (int r = 0; r <= rings; r++)
                for (int s = 0; s <= seg; s++)
                {
                    float lat = -90f + 180f * r / rings, lon = -180f + 360f * s / seg;
                    int i = r * (seg + 1) + s; var d = Dir(lat, lon);
                    v[i] = d * SphereRadius; n[i] = d; uv[i] = new Vector2(s / (float)seg, r / (float)rings);
                }
            var t = new int[seg * rings * 6]; int k = 0;
            for (int r = 0; r < rings; r++)
                for (int s = 0; s < seg; s++)
                {
                    int a = r * (seg + 1) + s, b = a + seg + 1;
                    // seen from outside, s runs east (right) and r north (up): clockwise is a, b, a+1
                    if (r > 0) { t[k++] = a; t[k++] = b; t[k++] = a + 1; }
                    if (r < rings - 1) { t[k++] = a + 1; t[k++] = b; t[k++] = b + 1; }
                }
            System.Array.Resize(ref t, k);
            sphereMesh = new Mesh { name = "Map globe", vertices = v, normals = n, uv = uv, triangles = t };
            sphereMesh.RecalculateBounds();
            return sphereMesh;
        }

        void BuildGlobe(MapAssets assets, MapDoc doc, int upTo)
        {
            var stand = Instance(assets, "globe.stand", transform);
            stand.localScale = Vector3.one * GlobeScale;
            var axis = Find(stand, "globe.stand.axis");
            // the axis leans 23.4 degrees within the meridian ring's plane; the stand turns a little so that, for a
            // northern place, the north pole leans toward the reader and the place comes round to face their eyes (for
            // a southern place, away). More than this and the ring crosses the face of the globe.
            float lat = Lit != null ? Lit.Lat : View.Focus != null ? View.Focus.Lat : 0f;
            if (Mathf.Abs(lat) > 8f)
            {
                stand.localRotation = Quaternion.Euler(0, StandTurn, 0);
                if (Vector3.Dot(axis.up, transform.forward) * lat > 0) stand.localRotation = Quaternion.Euler(0, -StandTurn, 0);
            }
            spinner = new GameObject("globe").transform; spinner.SetParent(axis, false);
            spinner.gameObject.AddComponent<MeshFilter>().sharedMesh = Sphere();
            var mr = spinner.gameObject.AddComponent<MeshRenderer>(); mr.sharedMaterial = surface;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; mr.receiveShadows = false;
            surface.SetFloat("_Spec", 0f); surface.SetFloat("_Self", 1.0f);   // no gloss: the sea is so dark in linear light that any glint reads as a grey blot

            // pins: the lit place first, then the others, merging near neighbours into one pin
            var dirs = new List<Vector3>(); var names = new List<List<string>>();
            void Add(MapDoc.Place p)
            {
                var d = Dir(p.Lat, p.Lon);
                for (int i = 0; i < dirs.Count; i++) if (Vector3.Angle(dirs[i], d) < PinMerge) { names[i].Add(p.Display); return; }
                dirs.Add(d); names.Add(new List<string> { p.Display });
            }
            if (Lit != null) Add(Lit);
            foreach (var p in doc.Places) if (p != Lit && p.View == View.Id && p.Ordinal >= 0 && p.Ordinal <= upTo) Add(p);
            PinCount = dirs.Count;
            pinsRoot = spinner;
            var combine = new List<CombineInstance>();
            for (int i = 0; i < dirs.Count; i++)
            {
                bool lit = i == 0 && Lit != null;
                var rot = Quaternion.FromToRotation(Vector3.up, dirs[i]); var pos = dirs[i] * SphereRadius;
                float scale = lit ? 1.6f : 0.75f;
                heads.Add(pos + rot * new Vector3(0, PinHead * scale, 0));
                headNames.Add(names[i].Count == 1 ? names[i][0] : $"{names[i][0]} <size=75%>and {names[i].Count - 1} more</size>");
                if (lit) litPin = Pin(spinner, pos, rot, scale);
                else combine.Add(new CombineInstance { mesh = pinMesh, transform = Matrix4x4.TRS(pos, rot, Vector3.one * scale) });
            }
            DimPins(spinner, combine);

            // turn so the lit place (or the view's focus) faces the reader; open from a little way round
            var target = Lit != null ? Dir(Lit.Lat, Lit.Lon) : View.Focus != null ? Dir(View.Focus.Lat, View.Focus.Lon) : Vector3.back;
            var head = Camera.main ? Camera.main.transform.position : transform.position - transform.forward;
            var a = axis.up; var d0 = axis.TransformDirection(target); var r0 = head - axis.position;
            spinTo = Vector3.SignedAngle(Vector3.ProjectOnPlane(d0, a), Vector3.ProjectOnPlane(r0, a), a);
            spinFrom = spinTo - 150f; spin = spinFrom; animSeconds = 1.6f;
        }

        Transform Pin(Transform parent, Vector3 pos, Quaternion rot, float scale)
        {
            var t = new GameObject("pin.lit").transform; t.SetParent(parent, false);
            t.localPosition = pos; t.localRotation = rot; t.localScale = litScale = Vector3.one * scale;
            t.gameObject.AddComponent<MeshFilter>().sharedMesh = pinMesh;
            var r = t.gameObject.AddComponent<MeshRenderer>(); r.sharedMaterial = litMat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            var h = new GameObject("pin.head").transform; h.SetParent(t, false); h.localPosition = new Vector3(0, PinHead, 0);
            return t;
        }

        void DimPins(Transform parent, List<CombineInstance> combine)
        {
            if (combine.Count == 0) return;
            var m = Own(new Mesh { name = "Map pins", indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 });
            m.CombineMeshes(combine.ToArray(), true, true);
            var t = new GameObject("pins").transform; t.SetParent(parent, false); dimPins = t.gameObject;
            t.gameObject.AddComponent<MeshFilter>().sharedMesh = m;
            var r = t.gameObject.AddComponent<MeshRenderer>(); r.sharedMaterial = dimMat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
        }

        // ---- scroll

        void BuildScroll(MapAssets assets, MapDoc doc, int upTo)
        {
            float aspect = Mathf.Clamp(View.Aspect > 0 ? View.Aspect : 1.4f, 0.5f, 2.5f);
            fullW = ScrollWidth; fullH = fullW / aspect;
            if (fullH > ScrollMaxHeight) { fullH = ScrollMaxHeight; fullW = fullH * aspect; }
            var scroll = Instance(assets, "scroll", transform);
            // the sheet's front faces the scroll's +Z: turn it to the reader, tipped back to face their eyes
            scroll.localPosition = new Vector3(0, fullH / 2 + 0.075f, 0);
            var head = Camera.main ? Camera.main.transform.position : scroll.position - transform.forward;
            scroll.rotation = Quaternion.LookRotation(head - scroll.position, Vector3.up);
            sheet = Find(scroll, "scroll.sheet"); rollL = Find(scroll, "scroll.roller.left"); rollR = Find(scroll, "scroll.roller.right");
            fLT = Find(scroll, "scroll.finial.left.top"); fLB = Find(scroll, "scroll.finial.left.bottom");
            fRT = Find(scroll, "scroll.finial.right.top"); fRB = Find(scroll, "scroll.finial.right.bottom");
            sx = Mathf.Sign(rollL.localPosition.x); if (sx == 0) sx = 1; rollZ = fLT.localPosition.z;
            var sr = sheet.GetComponent<MeshRenderer>(); sr.sharedMaterial = surface;
            surface.SetTexture("_MaskMap", assets.EdgeMask); surface.SetFloat("_Cull", 0); surface.SetFloat("_Self", 1.0f);

            var sheetMesh = sheet.GetComponent<MeshFilter>().sharedMesh;
            var sv = sheetMesh.vertices; var suv = sheetMesh.uv;
            float Depth(float u, float v)   // the sheet's belly and curl at this point of the image (v from the top)
            {
                float best = float.MaxValue, z = 0; var want = new Vector2(u, 1 - v);
                for (int i = 0; i < suv.Length; i++) { float d = (suv[i] - want).sqrMagnitude; if (d < best) { best = d; z = sv[i].z; } }
                return z;
            }
            pinsRoot = scroll;
            var combine = new List<CombineInstance>();
            var tilt = Quaternion.AngleAxis(-14f, Vector3.right) * Quaternion.FromToRotation(Vector3.up, Vector3.forward);
            void Add(MapDoc.Place p, bool lit)
            {
                float u = Mathf.Clamp01(p.U), v = Mathf.Clamp01(p.V);
                var pos = new Vector3(sx * (0.5f - u) * fullW, (0.5f - v) * fullH, Depth(u, v));
                float scale = lit ? 1.5f : 0.65f;
                heads.Add(pos + tilt * new Vector3(0, PinHead * scale, 0)); headNames.Add(p.Display);
                if (lit) litPin = Pin(scroll, pos, tilt, scale);
                else combine.Add(new CombineInstance { mesh = pinMesh, transform = Matrix4x4.TRS(pos, tilt, Vector3.one * scale) });
            }
            if (Lit != null) Add(Lit, true);
            foreach (var p in doc.Places) if (p != Lit && p.View == View.Id && p.Ordinal >= 0 && p.Ordinal <= upTo) Add(p, false);
            PinCount = heads.Count;
            DimPins(scroll, combine);
            FitMap(fullW, 1f);   // full size for the bounds; Tick(0) rolls it up again
            animSeconds = 1.3f;
        }

        /// docs/MAP_PROPS.md FitMap, with the sheet showing the middle `shown` of the image's width.
        void FitMap(float w, float shown)
        {
            float h = fullH;
            sheet.localScale = new Vector3(w, h, 1f);
            surface.SetVector("_Crop", new Vector4(0.5f - shown / 2f, shown, 0, 0));
            rollL.localPosition = new Vector3(sx * w / 2, 0, 0); rollL.localScale = new Vector3(1, h, 1);
            rollR.localPosition = new Vector3(-sx * w / 2, 0, 0); rollR.localScale = new Vector3(1, h, 1);
            fLT.localPosition = new Vector3(sx * w / 2, h / 2, rollZ); fLB.localPosition = new Vector3(sx * w / 2, -h / 2, rollZ);
            fRT.localPosition = new Vector3(-sx * w / 2, h / 2, rollZ); fRB.localPosition = new Vector3(-sx * w / 2, -h / 2, rollZ);
        }

        // ---- labels

        static Material labelMat;
        /// One shared outlined copy of the font's material (setting outlineWidth on each label would make an instance).
        static Material LabelMaterial(TMP_FontAsset font, float width)
        {
            if (labelMat) return labelMat;
            labelMat = new Material(font.material) { name = "Map label" };
            labelMat.EnableKeyword("OUTLINE_ON");
            labelMat.SetFloat("_OutlineWidth", width); labelMat.SetFloat("_OutlineSoftness", 0f); labelMat.SetColor("_OutlineColor", new Color32(40, 26, 12, 255));
            labelMat.SetFloat("_FaceDilate", 0.1f);
            return labelMat;
        }

        void BuildLabels(TMP_FontAsset font)
        {
            TextMeshPro Text(string name, float size, TextAlignmentOptions align)
            {
                var t = new GameObject(name).AddComponent<TextMeshPro>(); t.transform.SetParent(transform, false);
                t.font = font; t.fontSize = size; t.color = new Color(0.20f, 0.14f, 0.08f); t.alignment = align;
                t.textWrappingMode = TextWrappingModes.Normal; t.richText = true; t.raycastTarget = false;
                return t;
            }
            hoverLabel = Text("map.hover", 0.16f, TextAlignmentOptions.Bottom);
            hoverLabel.rectTransform.sizeDelta = new Vector2(0.18f, 0.03f); hoverLabel.rectTransform.pivot = new Vector2(0.5f, 0); hoverLabel.textWrappingMode = TextWrappingModes.NoWrap;
            hoverLabel.color = new Color(0.98f, 0.94f, 0.84f); hoverLabel.fontSharedMaterial = LabelMaterial(font, 0.28f);
            if (!Globe) { hoverLabel.fontSharedMaterial = font.material; hoverLabel.color = new Color(0.16f, 0.09f, 0.03f); hoverLabel.fontStyle = FontStyles.Bold; }
            hoverLabel.gameObject.SetActive(false);
            if (Lit == null) return;
            label = Text("map.label", 0.2f, TextAlignmentOptions.BottomLeft);
            label.text = $"<b>{Lit.Display}</b>";
            // light lettering with a dark edge: the map stands against the room, which may be dark or bright
            label.color = new Color(0.98f, 0.94f, 0.84f); label.fontSharedMaterial = LabelMaterial(font, 0.28f);
            if (Globe)
            {
                // to the reader's left of the globe (away from the page), with a leader line to the lit pin's head
                label.alignment = TextAlignmentOptions.BottomRight; label.textWrappingMode = TextWrappingModes.NoWrap;
                label.rectTransform.sizeDelta = new Vector2(0.16f, 0.03f); label.rectTransform.pivot = new Vector2(1, 0);
                float r = SphereRadius * GlobeScale, cy = 0.322f * GlobeScale;
                label.rectTransform.localPosition = new Vector3(-r - 0.035f, cy + r * 0.75f, 0);
                label.transform.localRotation = Quaternion.identity;
                line = label.gameObject.AddComponent<LineRenderer>();
                line.sharedMaterial = dimMat; line.positionCount = 2; line.widthMultiplier = 0.0012f; line.useWorldSpace = true;
                line.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; line.receiveShadows = false;
                line.startColor = line.endColor = new Color(0.35f, 0.22f, 0.10f, 1f);
            }
            else
            {
                // on the sheet just above the pin, facing the reader with the scroll
                label.transform.SetParent(pinsRoot, false);
                label.alignment = TextAlignmentOptions.Bottom; label.fontSize = 0.2f; label.textWrappingMode = TextWrappingModes.NoWrap;
                label.rectTransform.sizeDelta = new Vector2(0.2f, 0.03f); label.rectTransform.pivot = new Vector2(0.5f, 0);
                // dark red ink on the parchment, like the map's own lettering but in the lit pin's colour
                label.fontSharedMaterial = font.material; label.color = new Color(0.42f, 0.05f, 0.02f);
                // TextMeshPro reads from its -Z side; the scroll's front is +Z
                label.transform.localRotation = Quaternion.Euler(0, 180, 0);
                label.rectTransform.localPosition = heads[0] + new Vector3(0, 0.014f, 0.006f);
            }
        }

        // ---------------------------------------------------------------- per frame

        /// Turn the globe by hand (degrees about its axis). Returns false for a scroll (Peek turns it like a model).
        public bool Spin(float degrees)
        {
            if (!Globe) return false;
            anim = 1f; spin += degrees; spinner.localRotation = Quaternion.AngleAxis(spin, Vector3.up);
            return true;
        }

        void Update() => Tick(Time.deltaTime);

        void Tick(float dt)
        {
            if (anim < 1f)
            {
                anim = Mathf.Min(1f, anim + dt / Mathf.Max(0.01f, animSeconds));
                float e = anim * anim * (3f - 2f * anim);
                if (Globe) { spin = Mathf.LerpUnclamped(spinFrom, spinTo, e); spinner.localRotation = Quaternion.AngleAxis(spin, Vector3.up); }
                else
                {
                    float f = Mathf.Lerp(0.07f, 1f, 1f - (1f - anim) * (1f - anim));   // ease out
                    FitMap(fullW * f, f);
                    bool open = anim >= 1f;   // the pins go in once the map is open
                    if (dimPins) dimPins.SetActive(open);
                    if (litPin) litPin.gameObject.SetActive(open);
                    if (label) label.gameObject.SetActive(open);
                }
            }
            if (litPin)
            {
                // a soft pulse of the glass
                float t = Time.time;
                float pulse = Mathf.Sin(t * 3.2f);
                litMat.SetFloat("_Emit", 0.4f + 0.35f * pulse);
                litPin.localScale = litScale * (1f + 0.04f * pulse);
            }
            if (line && litPin)
            {
                var h = litPin.GetChild(0).position;
                line.SetPosition(0, label.rectTransform.TransformPoint(new Vector3(0.004f, 0.006f, 0)));
                line.SetPosition(1, h);
            }
            Hover();
        }

        /// The pin nearest either hand's ray (within a generous radius around its head), named beside it.
        void Hover()
        {
            int best = -1; float bestD = float.MaxValue; var cam = Camera.main;
            if (pointer && pinsRoot && anim >= 1f)
                for (int hand = 0; hand < 2; hand++)
                {
                    if (!pointer.Ray(hand == 0, out var ray)) continue;
                    for (int i = 0; i < heads.Count; i++)
                    {
                        var w = pinsRoot.TransformPoint(heads[i]);
                        if (Globe && Vector3.Dot(w - spinner.position, ray.direction) > 0) continue;   // round the back of the globe
                        var to = w - ray.origin; float along = Vector3.Dot(to, ray.direction); if (along <= 0) continue;
                        float off = (to - ray.direction * along).magnitude, reach = 0.012f + along * 0.01f;
                        if (off < reach && off < bestD) { bestD = off; best = i; }
                    }
                }
            if (best != hoverIndex)
            {
                hoverIndex = best; Hovered = best < 0 ? null : headNames[best];
                hoverLabel.gameObject.SetActive(best >= 0 && !(best == 0 && Lit != null && label));
                if (best >= 0) hoverLabel.text = headNames[best];
            }
            if (hoverLabel.gameObject.activeSelf && cam)
            {
                var w = pinsRoot.TransformPoint(heads[best]);
                var toCam = (cam.transform.position - w).normalized;
                hoverLabel.transform.position = w + toCam * 0.01f + Vector3.up * 0.008f;
                hoverLabel.transform.rotation = Quaternion.LookRotation(-toCam, Vector3.up);
            }
        }

        /// Test hook: where pin i's head is now (0 is the lit pin when there is one), to aim PagePointer.TestRay at.
        public Vector3 PinWorld(int i) => i >= 0 && i < heads.Count && pinsRoot ? pinsRoot.TransformPoint(heads[i]) : Vector3.zero;

        public string Describe() => $"view={View?.Id}({View?.Kind}) lit={Lit?.Id ?? "-"} pins={PinCount} tris={Triangles} settled={Settled} hover={Hovered ?? "-"}";
    }
}
