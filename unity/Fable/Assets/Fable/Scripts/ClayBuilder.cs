// Builds a Peek mock model (schema/mock-model.schema.json) from primitives. Every shape has a fixed triangle cost
// that matches interpreter/internal/mock (box 12, cone 32, cylinder 64, hemisphere 256, torus 384, sphere 448,
// capsule 448), so the budget checked on the server is the budget drawn here. One renderer per part, one material
// per colour and finish; the meshes are built once per shape (capsules and tori per proportion) and shared.
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;

namespace Fable
{
    public class MockModel
    {
        public class Part
        {
            [JsonProperty("id")] public string Id;
            [JsonProperty("parent")] public string Parent;
            [JsonProperty("shape")] public string Shape;
            [JsonProperty("size")] public float[] Size;
            [JsonProperty("position")] public float[] Position;
            [JsonProperty("rotation")] public float[] Rotation;
            [JsonProperty("color")] public string Color;
            [JsonProperty("material")] public string Material;
        }
        public class Label { [JsonProperty("text")] public string Text; [JsonProperty("part")] public string Part; [JsonProperty("quote")] public bool Quote; }
        [JsonProperty("version")] public int Version;
        [JsonProperty("id")] public string Id;
        [JsonProperty("title")] public string Title;
        [JsonProperty("book")] public string Book;
        [JsonProperty("phrase")] public string Phrase;
        [JsonProperty("sentenceId")] public string SentenceId;
        [JsonProperty("heightMetres")] public float HeightMetres = 0.25f;
        [JsonProperty("realHeight")] public string RealHeight;
        [JsonProperty("source")] public string Source;
        [JsonProperty("parts")] public List<Part> Parts = new();
        [JsonProperty("labels")] public List<Label> Labels = new();
    }

    public static class ClayBuilder
    {
        public static readonly Dictionary<string, int> Triangles = new() { { "box", 12 }, { "sphere", 448 }, { "hemisphere", 256 }, { "cylinder", 64 }, { "cone", 32 }, { "capsule", 448 }, { "torus", 384 } };
        public const int Budget = 15000;
        const int Seg = 16;

        static readonly Dictionary<string, Mesh> meshes = new();
        static Material clayBase;

        /// Build the model under a new root, scaled so its tallest extent is heightMetres, standing on the root's origin.
        /// parts maps part id to its transform (labels point at these). Returns the triangle count, or -1 if the model
        /// is over budget or names an unknown shape (nothing is built then).
        public static int Build(MockModel m, Transform root, Dictionary<string, Transform> parts)
        {
            parts.Clear(); int tris = 0;
            foreach (var p in m.Parts) { if (!Triangles.TryGetValue(p.Shape ?? "", out var t)) { Debug.LogWarning($"[Fable] clay: unknown shape {p.Shape}"); return -1; } tris += t; }
            if (tris > Budget) { Debug.LogWarning($"[Fable] clay: {tris} triangles is over the {Budget} budget"); return -1; }

            var model = new GameObject("Clay " + (m.Id ?? m.Title)).transform; model.SetParent(root, false);
            var mats = new Dictionary<string, Material>();
            foreach (var p in m.Parts)
            {
                var node = new GameObject(p.Id).transform;
                node.SetParent(p.Parent != null && parts.TryGetValue(p.Parent, out var par) ? par : model, false);
                node.localPosition = V(p.Position, Vector3.zero);
                var r = V(p.Rotation, Vector3.zero); node.localRotation = Quaternion.Euler(r);
                parts[p.Id] = node;
                // the visible shape is a child, so a part's own scale never stretches its children
                var shape = new GameObject("shape", typeof(MeshFilter), typeof(MeshRenderer)).transform; shape.SetParent(node, false);
                var size = V(p.Size, Vector3.one);
                shape.GetComponent<MeshFilter>().sharedMesh = MeshFor(p.Shape, size, out var scale);
                shape.localScale = scale;
                var mr = shape.GetComponent<MeshRenderer>(); mr.sharedMaterial = MaterialFor(p.Color, p.Material, mats);
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; mr.receiveShadows = false;
            }
            // fit: tallest extent -> heightMetres, feet on the origin, centred in x and z
            var b = Bounds(model, root);
            float tallest = Mathf.Max(b.size.x, b.size.y, b.size.z);
            float k = tallest > 1e-5f ? Mathf.Clamp(m.HeightMetres, 0.03f, 0.6f) / tallest : 1f;
            model.localScale = Vector3.one * k;
            model.localPosition = new Vector3(-b.center.x * k, -b.min.y * k, -b.center.z * k);
            return tris;
        }

        /// Bounds of every renderer under t, in `space`'s local coordinates.
        public static Bounds Bounds(Transform t, Transform space)
        {
            bool any = false; var b = new Bounds();
            foreach (var mf in t.GetComponentsInChildren<MeshFilter>())
            {
                if (!mf.sharedMesh) continue;
                var mb = mf.sharedMesh.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var c = mb.center + Vector3.Scale(mb.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                    var w = space.InverseTransformPoint(mf.transform.TransformPoint(c));
                    if (!any) { b = new Bounds(w, Vector3.zero); any = true; } else b.Encapsulate(w);
                }
            }
            return b;
        }

        static Vector3 V(float[] a, Vector3 d) => a != null && a.Length == 3 ? new Vector3(a[0], a[1], a[2]) : d;

        static Material MaterialFor(string hex, string finish, Dictionary<string, Material> cache)
        {
            finish = string.IsNullOrEmpty(finish) ? "matte" : finish;
            var key = hex + finish;
            if (cache.TryGetValue(key, out var m)) return m;
            if (!clayBase) clayBase = Resources.Load<Material>("FableClay");
            m = clayBase ? new Material(clayBase) : new Material(Shader.Find("Universal Render Pipeline/Lit"));
            m.name = "Clay " + key;
            if (!ColorUtility.TryParseHtmlString(hex, out var c)) c = Color.grey;
            m.SetColor("_BaseColor", c);
            m.SetFloat("_Metallic", finish == "metal" ? 0.35f : 0f);   // more reads black: there is little to reflect beside the page
            m.SetFloat("_Smoothness", finish == "metal" ? 0.55f : finish == "gloss" || finish == "glass" ? 0.75f : 0.2f);
            if (finish == "emissive") { m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", c * 1.5f); }
            if (finish == "glass") m.SetColor("_BaseColor", Color.Lerp(c, Color.white, 0.25f));   // opaque: transparency costs fill rate on Quest
            cache[key] = m;
            return m;
        }

        /// Clay materials are per model; destroy them with it.
        public static void DestroyModel(Transform model)
        {
            if (!model) return;
            var seen = new HashSet<Material>();
            foreach (var r in model.GetComponentsInChildren<Renderer>(true))
                foreach (var m in r.sharedMaterials) if (m && m.name.StartsWith("Clay ") && seen.Add(m)) Object.Destroy(m);
            Object.Destroy(model.gameObject);
        }

        // ---------------------------------------------------------------- meshes (unit size, centred, y up)

        static Mesh MeshFor(string shape, Vector3 size, out Vector3 scale)
        {
            scale = size;
            switch (shape)
            {
                case "capsule":
                {
                    // round caps whatever the proportions: build at the part's aspect (quantised so meshes are shared)
                    float w = Mathf.Max(1e-4f, (size.x + size.z) / 2f), h = Mathf.Max(1f, Mathf.Round(size.y / w * 4f) / 4f);
                    scale = new Vector3(size.x, size.y / h, size.z);
                    return Cached("capsule" + h, () => Capsule(h));
                }
                case "torus":
                {
                    float d = Mathf.Max(size.x, size.z), tube = Mathf.Clamp(Mathf.Round(size.y / d * 40f) / 40f, 0.025f, 0.45f);
                    scale = new Vector3(size.x, d, size.z);   // tube thickness in the mesh is tube * d once scaled
                    return Cached("torus" + tube, () => Torus(tube));
                }
                case "box": return Cached("box", Box);
                case "sphere": return Cached("sphere", () => Sphere(15, false));
                case "hemisphere": return Cached("hemisphere", () => Sphere(8, true));
                case "cylinder": return Cached("cylinder", () => Cylinder(1f));
                case "cone": return Cached("cone", () => Cylinder(0f));
            }
            return Cached("box", Box);
        }

        static Mesh Cached(string key, System.Func<Mesh> make)
        {
            if (meshes.TryGetValue(key, out var m) && m) return m;
            m = make(); m.name = "clay." + key; meshes[key] = m; return m;
        }

        static Mesh Finish(List<Vector3> v, List<Vector3> n, List<int> t)
        {
            var m = new Mesh(); m.SetVertices(v); m.SetNormals(n); m.SetTriangles(t, 0); m.RecalculateBounds(); return m;
        }

        static Mesh Box()
        {
            var v = new List<Vector3>(); var n = new List<Vector3>(); var t = new List<int>();
            Vector3[] dirs = { Vector3.right, Vector3.left, Vector3.up, Vector3.down, Vector3.forward, Vector3.back };
            foreach (var d in dirs)
            {
                var u = Mathf.Abs(d.y) > 0.5f ? Vector3.right : Vector3.up; var w = Vector3.Cross(d, u);
                int s = v.Count;
                v.Add((d - u - w) * 0.5f); v.Add((d - u + w) * 0.5f); v.Add((d + u + w) * 0.5f); v.Add((d + u - w) * 0.5f);
                for (int i = 0; i < 4; i++) n.Add(d);
                t.AddRange(new[] { s, s + 2, s + 1, s, s + 3, s + 2 });
            }
            return Fix(Finish(v, n, t));
        }

        /// Make every face wind outwards (front faces point along their normals), whatever order the builder used.
        static Mesh Fix(Mesh m)
        {
            var v = m.vertices; var n = m.normals; var t = m.triangles;
            for (int i = 0; i < t.Length; i += 3)
            {
                var f = Vector3.Cross(v[t[i + 1]] - v[t[i]], v[t[i + 2]] - v[t[i]]);
                var avg = n[t[i]] + n[t[i + 1]] + n[t[i + 2]];
                if (Vector3.Dot(f, avg) < 0) (t[i + 1], t[i + 2]) = (t[i + 2], t[i + 1]);
            }
            m.triangles = t; m.UploadMeshData(true);   // GPU only from here: frees the CPU copy
            return m;
        }

        /// UV sphere of diameter 1 with `rings` latitude bands (15 for a sphere: 448 triangles). hemisphere: the top
        /// half over 8 bands plus a base disc (256), spanning y -0.5..0.5 so its size is its full extent.
        static Mesh Sphere(int rings, bool half)
        {
            var v = new List<Vector3>(); var n = new List<Vector3>(); var t = new List<int>();
            float span = half ? Mathf.PI / 2f : Mathf.PI;
            for (int r = 0; r <= rings; r++)
            {
                float th = span * r / rings;
                for (int s = 0; s <= Seg; s++)
                {
                    float ph = 2 * Mathf.PI * s / Seg;
                    var d = new Vector3(Mathf.Sin(th) * Mathf.Cos(ph), Mathf.Cos(th), Mathf.Sin(th) * Mathf.Sin(ph));
                    n.Add(d); v.Add(half ? new Vector3(d.x * 0.5f, d.y - 0.5f, d.z * 0.5f) : d * 0.5f);
                }
            }
            int W = Seg + 1;
            for (int r = 0; r < rings; r++)
                for (int s = 0; s < Seg; s++)
                {
                    int a = r * W + s, b = a + 1, c = a + W, d = c + 1;
                    if (r != 0) t.AddRange(new[] { a, b, c });              // the pole band is a fan: one triangle a segment
                    if (half || r != rings - 1) t.AddRange(new[] { b, d, c });   // a full sphere's bottom band is a fan too
                }
            if (half) Disc(v, n, t, -0.5f, Vector3.down, 0.5f);
            return Fix(Finish(v, n, t));
        }

        static void Disc(List<Vector3> v, List<Vector3> n, List<int> t, float y, Vector3 normal, float radius)
        {
            int c = v.Count; v.Add(new Vector3(0, y, 0)); n.Add(normal);
            for (int s = 0; s <= Seg; s++) { float ph = 2 * Mathf.PI * s / Seg; v.Add(new Vector3(Mathf.Cos(ph) * radius, y, Mathf.Sin(ph) * radius)); n.Add(normal); }
            for (int s = 0; s < Seg - 1; s++) t.AddRange(new[] { c, c + 1 + s, c + 2 + s });
            t.AddRange(new[] { c, c + Seg, c + 1 });   // close the fan: Seg triangles in all
        }

        /// Cylinder (topRadius 1: 64 triangles) or cone (topRadius 0: 32), diameter 1, height 1.
        static Mesh Cylinder(float topRadius)
        {
            var v = new List<Vector3>(); var n = new List<Vector3>(); var t = new List<int>();
            bool cone = topRadius <= 0f; float slope = 0.5f;   // cone normal tilt: radius 0.5 over height 1
            for (int s = 0; s <= Seg; s++)
            {
                float ph = 2 * Mathf.PI * s / Seg; var d = new Vector3(Mathf.Cos(ph), 0, Mathf.Sin(ph));
                var nn = cone ? (d + Vector3.up * slope).normalized : d;
                v.Add(d * 0.5f + Vector3.down * 0.5f); n.Add(nn);
                v.Add(cone ? Vector3.up * 0.5f : d * 0.5f + Vector3.up * 0.5f); n.Add(nn);
            }
            for (int s = 0; s < Seg; s++)
            {
                int a = s * 2, b = a + 1, c = a + 2, d = a + 3;
                t.AddRange(new[] { a, b, c });
                if (!cone) t.AddRange(new[] { b, d, c });
            }
            Disc(v, n, t, -0.5f, Vector3.down, 0.5f);
            if (!cone) Disc(v, n, t, 0.5f, Vector3.up, 0.5f);
            return Fix(Finish(v, n, t));
        }

        /// Capsule of diameter 1 and total height h (>= 1): two 7-band hemispherical caps and a side. 448 triangles.
        static Mesh Capsule(float h)
        {
            var v = new List<Vector3>(); var n = new List<Vector3>(); var t = new List<int>();
            const int bands = 7; float half = (h - 1f) / 2f; int W = Seg + 1;
            // rows from the top pole to the bottom pole: top cap rows 0..bands, bottom cap rows bands+1..2*bands+1
            for (int r = 0; r <= 2 * bands + 1; r++)
            {
                bool top = r <= bands; float th = top ? (Mathf.PI / 2f) * r / bands : Mathf.PI / 2f + (Mathf.PI / 2f) * (r - bands - 1) / bands;
                float yOff = top ? half : -half;
                for (int s = 0; s <= Seg; s++)
                {
                    float ph = 2 * Mathf.PI * s / Seg;
                    var d = new Vector3(Mathf.Sin(th) * Mathf.Cos(ph), Mathf.Cos(th), Mathf.Sin(th) * Mathf.Sin(ph));
                    n.Add(d); v.Add(d * 0.5f + Vector3.up * yOff);
                }
            }
            int rows = 2 * bands + 1;
            for (int r = 0; r < rows; r++)
                for (int s = 0; s < Seg; s++)
                {
                    int a = r * W + s, b = a + 1, c = a + W, d = c + 1;
                    if (r == 0) { t.AddRange(new[] { b, d, c }); continue; }              // top fan
                    if (r == rows - 1) { t.AddRange(new[] { a, b, c }); continue; }       // bottom fan
                    t.AddRange(new[] { a, b, c }); t.AddRange(new[] { b, d, c });
                }
            return Fix(Finish(v, n, t));
        }

        /// Torus with outer diameter 1 and tube radius `tube` (fraction of the diameter): 24 x 8 x 2 = 384 triangles.
        static Mesh Torus(float tube)
        {
            var v = new List<Vector3>(); var n = new List<Vector3>(); var t = new List<int>();
            const int major = 24, minor = 8; float rt = tube / 2f, R = 0.5f - rt;
            for (int i = 0; i <= major; i++)
            {
                float a = 2 * Mathf.PI * i / major; var c = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a));
                for (int j = 0; j <= minor; j++)
                {
                    float b = 2 * Mathf.PI * j / minor; var d = c * Mathf.Cos(b) + Vector3.up * Mathf.Sin(b);
                    n.Add(d); v.Add(c * R + d * rt);
                }
            }
            int W = minor + 1;
            for (int i = 0; i < major; i++)
                for (int j = 0; j < minor; j++)
                {
                    int a = i * W + j, b = a + 1, c = a + W, d = c + 1;
                    t.AddRange(new[] { a, c, b }); t.AddRange(new[] { b, c, d });
                }
            return Fix(Finish(v, n, t));
        }

        /// Test and measurement: the triangles actually in each shape's mesh (must equal Triangles).
        public static string CheckCounts()
        {
            var sb = new System.Text.StringBuilder(); bool ok = true;
            foreach (var kv in Triangles)
            {
                var mesh = MeshFor(kv.Key, new Vector3(1, kv.Key == "capsule" ? 3 : kv.Key == "torus" ? 0.2f : 1, 1), out _);
                int got = (int)mesh.GetIndexCount(0) / 3;
                ok &= got == kv.Value; sb.Append($"{kv.Key}:{got}/{kv.Value} ");
            }
            return (ok ? "OK " : "MISMATCH ") + sb;
        }
    }
}
