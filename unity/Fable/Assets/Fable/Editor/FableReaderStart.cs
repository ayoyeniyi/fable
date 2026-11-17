// Where the reader appears in each reading room. The room's anchor.reader.* (and anchor.reader.look) came from
// Blender; some put the reader against a chair, a table or a wall. This check stands a body (a 0.4 m capsule from
// knee to head) at the start, looks ahead at knee and chest height for open floor (the page floats about 0.6 m ahead
// at chest height), and if either is blocked searches the floor nearby for the nearest clear spot with an open view
// toward the room's interest (anchor.reader.look, else the original facing). Results are kept in ReaderStarts.json
// (next to this file), which FableBuild.BuildScene applies on every rebuild; Apply() moves the rig in a built scene.
//
//   unity command eval 'return Fable.Editor.FableReaderStart.CheckAll(false);'   report only
//   unity command eval 'return Fable.Editor.FableReaderStart.CheckAll(true);'    fix, store, apply, previews
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Fable.Editor
{
    public static class FableReaderStart
    {
        /// Manual: chosen by hand (FableReaderStart.Probe helps); the check reports it and never replaces it.
        public class Start { public float X, Y, Z, Yaw; public string Note; public bool Manual; [JsonIgnore] public Vector3 At => new(X, Y, Z); }
        const string StorePath = "Assets/Fable/Editor/ReaderStarts.json", ColliderRoot = "__readerstart_colliders";
        static Dictionary<string, Start> store;

        static Dictionary<string, Start> Store()
        {
            if (store != null) return store;
            store = File.Exists(StorePath) ? JsonConvert.DeserializeObject<Dictionary<string, Start>>(File.ReadAllText(StorePath)) ?? new() : new();
            return store;
        }
        public static Start Override(string id) => Store().TryGetValue(id, out var s) ? s : null;
        static void Save() => File.WriteAllText(StorePath, JsonConvert.SerializeObject(new SortedDictionary<string, Start>(Store()), Formatting.Indented) + "\n");

        // the body and the view
        const float Radius = 0.4f, Knee = 0.3f, Head = 1.75f, Chest = 1.25f, Low = 0.5f, ViewRadius = 0.2f;
        const float NeedOpen = 2.5f, WantOpen = 3.5f, MinOpen = 2.0f, MaxOpen = 12f, Search = 4f, Step = 0.25f;
        const int Layer = 31, FloorLayer = 30; const int Mask = 1 << Layer, FloorMask = Mask | (1 << FloorLayer);

        public static string CheckAll(bool fix)
        {
            var sb = new StringBuilder();
            foreach (var d in FableBuild.Scenes.Where(d => d.Room && File.Exists(d.Scene)))
            {
                try { sb.AppendLine(Check(d.Id, fix)); }
                catch (Exception e) { sb.AppendLine($"{d.Id}: failed: {e.Message}"); }
            }
            return sb.ToString();
        }

        /// One room: report the start, and with fix=true store a better one, move the rig and save previews.
        public static string Check(string id, bool fix)
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new Exception("exit play mode first");
            var def = FableBuild.Scenes.First(d => d.Id == id);
            var scene = EditorSceneManager.OpenScene(def.Scene, OpenSceneMode.Single);
            var env = GameObject.Find("env." + id); if (!env) return $"{id}: no env";
            var rig = RigRoot(); if (!rig) return $"{id}: no rig";
            var anchor = FableBuild.ReaderAnchor(env.transform);
            var look = LookAnchor(env.transform);
            Vector3 start = anchor ? anchor.position : rig.position;   // the room's own start, before any override
            float buildYaw = look ? YawTo(start, look.position) : 0f;   // as BuildScene faces it (a rebuilt rig, no override)
            // the room's interest: its look anchor; a room without one faces its scene centre (where its story is staged)
            var centre = env.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name is "anchor.scene.centre" or "anchor.hall.centre");
            float startYaw = !look && centre && Flat(centre.position - start).magnitude > 1.5f ? YawTo(start, centre.position) : buildYaw;
            foreach (var stale in scene.GetRootGameObjects().Where(g => g.name == ColliderRoot)) UnityEngine.Object.DestroyImmediate(stale);
            var root = Colliders(env.transform);
            bool backfaces = Physics.queriesHitBackfaces; Physics.queriesHitBackfaces = true;   // glTF ground may be wound either way
            try
            {
                bool indoor = !def.Outdoor;
                var (bodyHits, floorOk) = Body(start, start.y, indoor);
                float open = Open(start, startYaw, out var blocker);
                var report = $"{id}: start ({start.x:F2},{start.y:F2},{start.z:F2}) yaw {buildYaw:F0}{(startYaw != buildYaw ? $" (view {startYaw:F0})" : "")}: " +
                             (bodyHits.Count > 0 ? $"touching {string.Join(",", bodyHits)}; " : "body clear; ") + (floorOk ? "" : "no floor; ") +
                             $"open {open:F1} m ahead" + (open < MaxOpen ? $" (to {blocker})" : "");
                bool ok = bodyHits.Count == 0 && floorOk && open >= NeedOpen;
                Vector3 at = start; float yaw = startYaw; string note;
                var manual = Override(id) is { Manual: true } m ? m : null;
                if (manual != null) { at = manual.At; yaw = manual.Yaw; note = $"manual: ({at.x:F2},{at.z:F2}) yaw {yaw:F0}, open {Open(at, yaw, out _):F1} m, {(Body(at, at.y, indoor).hits is var mh && mh.Count > 0 ? "touching " + string.Join(",", mh) : "body clear")}"; ok = false; }
                else if (ok && Mathf.Abs(Mathf.DeltaAngle(startYaw, buildYaw)) > 1f) note = $"faces the scene centre: yaw {startYaw:F0} (was {buildYaw:F0}), open {open:F1} m";
                else if (ok) note = "as built";
                else
                {
                    // same spot, another facing; else the nearest clear spot (reachable in sight of the start) with an open view
                    // the view the room was built for: the heading toward its look anchor (or the rig's own), kept
                    // as a heading so that a step aside does not swing the reader round toward a nearby anchor
                    var interest = start + Dir(startYaw) * 100f;   // startYaw already faces anchor.reader.look
                    if (FindSpot(start, interest, indoor, out at, out yaw, out var o3))
                        note = (Flat(at - start).magnitude < 0.01f ? "" : $"moved {Flat(at - start).magnitude:F2} m, ") + $"yaw {yaw:F0} (turned {Mathf.DeltaAngle(startYaw, yaw):F0}), open {o3:F1} m";
                    else { at = start; yaw = startYaw; note = "NO CLEAR SPOT FOUND"; }
                }
                report += $" => {note}";
                if (fix)
                {
                    var dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..", "captures", "unity", id)); Directory.CreateDirectory(dir);
                    Preview(start, buildYaw, Path.Combine(dir, "reader-start-before.png"));
                    var old = Override(id);
                    if (manual != null) { }
                    else if (ok && Mathf.Abs(Mathf.DeltaAngle(startYaw, buildYaw)) <= 1f) Store().Remove(id);
                    else Store()[id] = new Start { X = R(at.x), Y = R(at.y), Z = R(at.z), Yaw = Mathf.Round(Mathf.Repeat(yaw, 360f)), Note = note };
                    Save();
                    UnityEngine.Object.DestroyImmediate(root); root = null;   // never saved with the scene
                    Place(rig, def);
                    Preview(rig.position, rig.eulerAngles.y, Path.Combine(dir, "reader-start-after.png"));
                    EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
                }
                return report;
            }
            finally { if (root) UnityEngine.Object.DestroyImmediate(root); Physics.SyncTransforms(); Physics.queriesHitBackfaces = backfaces; }
        }

        /// A hand-picked spot, measured the same way: "body clear, open N m (to X)".
        public static string Probe(string id, float x, float z, float yaw)
        {
            var def = FableBuild.Scenes.First(d => d.Id == id);
            EditorSceneManager.OpenScene(def.Scene, OpenSceneMode.Single);
            var env = GameObject.Find("env." + id); var anchor = FableBuild.ReaderAnchor(env.transform);
            var root = Colliders(env.transform); bool backfaces = Physics.queriesHitBackfaces; Physics.queriesHitBackfaces = true;
            try
            {
                float y0 = anchor ? anchor.position.y : 0; var fy = Floor(new Vector3(x, y0, z), y0, !def.Outdoor);
                var p = new Vector3(x, fy ?? y0, z); var (hits, floor) = Body(p, p.y, !def.Outdoor);
                float o = Open(p, yaw, out var b);
                return $"({x},{z}) y={p.y:F2} floor={floor} {(hits.Count > 0 ? "touching " + string.Join(",", hits) : "body clear")}, open {o:F1} m (to {b})";
            }
            finally { UnityEngine.Object.DestroyImmediate(root); Physics.queriesHitBackfaces = backfaces; }
        }

        /// Put a built scene's rig where the room's start is now (anchor, then any stored override). The reading room's
        /// floor disc, table and light move with it.
        public static void Apply(string id)
        {
            var def = FableBuild.Scenes.First(d => d.Id == id);
            var scene = EditorSceneManager.OpenScene(def.Scene, OpenSceneMode.Single);
            var rig = RigRoot(); if (!rig) throw new Exception($"{id}: no rig");
            Place(rig, def);
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
        }

        static void Place(Transform rig, FableBuild.SceneDef def)
        {
            var env = GameObject.Find("env." + def.Id).transform;
            var anchor = FableBuild.ReaderAnchor(env); var look = LookAnchor(env);
            var to = def.ReaderAt ?? (anchor ? anchor.position : rig.position);
            float yaw = def.ReaderYaw ?? (look ? YawTo(to, look.position) : 0f);
            var delta = to - rig.position;
            rig.position = to; rig.rotation = Quaternion.Euler(0, yaw, 0);
            var reading = GameObject.Find("ReadingRoom"); if (reading) reading.transform.position += delta;
            EditorUtility.SetDirty(rig);
        }

        /// What BuildScene turns the reader toward: anchor.reader.look, or the library room's shelf.
        static Transform LookAnchor(Component env) => env.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "anchor.reader.look")
                                                     ?? env.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "anchor.lobby.shelf");

        static Transform RigRoot()
        {
            var flow = UnityEngine.Object.FindFirstObjectByType<FlowController>();
            return flow && flow.Head ? flow.Head.root : null;
        }

        static float R(float v) => Mathf.Round(v * 100f) / 100f;
        static Vector3 Flat(Vector3 v) { v.y = 0; return v; }
        static float YawTo(Vector3 from, Vector3 to) { var d = Flat(to - from); return d.sqrMagnitude < 1e-6f ? 0 : Quaternion.LookRotation(d.normalized).eulerAngles.y; }
        static Vector3 Dir(float yaw) => Quaternion.Euler(0, yaw, 0) * Vector3.forward;

        /// Temporary colliders for everything a reader could bump into: not the sky and distant scenery, not grass or
        /// flowers (a reader stands in those), not flames and other living effects.
        static GameObject Colliders(Transform env)
        {
            var root = new GameObject(ColliderRoot);
            foreach (var r in env.GetComponentsInChildren<MeshRenderer>(false))
            {
                var n = r.name; var pn = r.transform.parent ? r.transform.parent.name : "";
                if (FlowController.IsBackdrop(n) || n.Contains("Sky") || n.StartsWith("living.") || pn.StartsWith("living.")) continue;
                if (IsAir(n) || IsAir(pn)) continue;
                var mf = r.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh) continue;
                // grass, flowers and rugs are floor to stand on, not obstacles
                var go = new GameObject(n.StartsWith("water.") || pn.StartsWith("water.") ? "water:" + n : n) { layer = IsLowPlant(n) || IsLowPlant(pn) ? FloorLayer : Layer };
                go.transform.SetParent(root.transform, false);
                go.transform.SetPositionAndRotation(r.transform.position, r.transform.rotation); go.transform.localScale = r.transform.lossyScale;
                go.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh;
            }
            Physics.SyncTransforms();
            return root;
            static bool IsAir(string n) => n.Contains("Dust") || n.Contains("Mote") || n.Contains("Mist") || n.Contains("Fog") || n.Contains("Haze") || n.Contains("Smoke") || n.Contains("Steam") || n.Contains("Shaft") || n.Contains("Beam") || n.Contains("Glow") || n.Contains("Flame") || n.StartsWith("fx.");
            static bool IsLowPlant(string n) => n.StartsWith("veg.grass") || n.StartsWith("veg.flowers") || n.StartsWith("veg.crop") || n.Contains("Grass") || n.Contains("Herbage") || n.Contains("Flower") || n.Contains("Petal") || n.Contains("Rug") || n.Contains("Carpet");
        }

        /// The floor under a point (near the start's level) and what a standing body there would touch.
        static (List<string> hits, bool floor) Body(Vector3 p, float floorY, bool indoor)
        {
            var fy = Floor(p, floorY, indoor);
            if (!fy.HasValue) return (new List<string>(), false);
            var b = new Vector3(p.x, fy.Value, p.z);
            var cs = Physics.OverlapCapsule(b + Vector3.up * (Knee + Radius), b + Vector3.up * (Head - Radius), Radius, Mask, QueryTriggerInteraction.Ignore);
            return (cs.Select(c => c.name).Distinct().ToList(), true);
        }

        /// The walkable surface nearest the start's floor level (not a table or bench top within reach of it).
        static float? Floor(Vector3 p, float floorY, bool indoor)
        {
            float tol = indoor ? 0.2f : 0.8f;
            var hits = Physics.RaycastAll(new Vector3(p.x, floorY + 1.6f, p.z), Vector3.down, 3.2f, FloorMask, QueryTriggerInteraction.Ignore);
            var best = hits.Where(h => Mathf.Abs(h.normal.y) > 0.7f && Mathf.Abs(h.point.y - floorY) <= tol).OrderBy(h => Mathf.Abs(h.point.y - floorY)).Select(h => (RaycastHit?)h).FirstOrDefault();
            if (!best.HasValue || best.Value.collider.name.StartsWith("water:")) return null;
            return best.Value.point.y;
        }

        /// How far the view is open ahead (metres), at knee and chest height: the nearer of the two.
        static float Open(Vector3 feet, float yaw, out string blocker)
        {
            float open = MaxOpen; blocker = "-";
            // straight ahead and 20 degrees either side: the page and the reader's arms take some width
            foreach (var side in new[] { 0f, -20f, 20f })
            foreach (var h in new[] { Low, Chest })
            {
                var d = Dir(yaw + side);
                var o = feet + Vector3.up * h;
                // start just behind the body's centre so a mesh the reader stands against is found
                if (Physics.SphereCast(o - d * 0.05f, ViewRadius, d, out var hit, MaxOpen, Mask, QueryTriggerInteraction.Ignore) && hit.distance < open) { open = hit.distance; blocker = hit.collider.name; }
                var inside = Physics.OverlapSphere(o, ViewRadius, Mask, QueryTriggerInteraction.Ignore);
                if (inside.Length > 0) { open = 0; blocker = inside[0].name; }
            }
            return open;
        }

        /// The facing at a spot whose view is open and nearest the interest (within maxTurn degrees of it).
        static bool BestYaw(Vector3 feet, Vector3 interest, float maxTurn, out float yaw, out float open, float need = NeedOpen)
        {
            float want = YawTo(feet, interest); yaw = want; open = 0; float best = float.NegativeInfinity;
            for (int a = -180; a < 180; a += 10)
            {
                float y = want + a; if (Mathf.Abs(a) > maxTurn) continue;
                float o = Open(feet, y, out _); if (o < need) continue;
                float score = -0.5f * Mathf.Abs(a) + 4f * Mathf.Min(o, 8f);   // the most open view near the room's heading
                if (score > best) { best = score; yaw = Mathf.Repeat(y, 360f); open = o; }
            }
            return best > float.NegativeInfinity;
        }

        static bool FindSpot(Vector3 start, Vector3 interest, bool indoor, out Vector3 at, out float yaw, out float open)
        {
            var cells = new List<Vector3>();
            for (float x = -Search; x <= Search; x += Step)
                for (float z = -Search; z <= Search; z += Step)
                    if (x * x + z * z <= Search * Search) cells.Add(start + new Vector3(x, 0, z));
            // nearest first, a step back (away from the view) before a step aside, a step forward last: the room's view
            // stays in front of the reader rather than being walked past
            var fwd = Dir(YawTo(start, interest));
            float Cost(Vector3 c) { var d = Flat(c - start); float f = Vector3.Dot(d, fwd); return d.magnitude + Mathf.Max(0, f) * 1.5f; }
            cells.Sort((a, b) => Cost(a).CompareTo(Cost(b)));
            // keep the view the room was built for: a small turn or a step back first, a bigger turn only if nothing else
            // (a little more room than the minimum when it is to be had nearby)
            foreach (var (maxTurn, need, reach) in new[] { (20f, WantOpen, 2f), (45f, WantOpen, 2.5f), (20f, NeedOpen, 2.5f), (45f, NeedOpen, 3f), (90f, NeedOpen, Search), (180f, MinOpen, Search) })
                foreach (var c in cells)
                {
                    if (Flat(c - start).magnitude > reach) continue;
                    if (need > NeedOpen && Vector3.Dot(Flat(c - start), fwd) > 0.3f) continue;   // the roomier passes only step back or aside
                    var fy = Floor(c, start.y, indoor); if (!fy.HasValue) continue;
                    var p = new Vector3(c.x, fy.Value, c.z);
                    if (Body(p, fy.Value, indoor).hits.Count > 0) continue;
                    // reachable: nothing between the old start and here at knee and chest height (not through a wall)
                    bool seen = true;
                    foreach (var h in new[] { Low, Chest })
                    {
                        var a = start + Vector3.up * h; var b = p + Vector3.up * h;
                        if (Physics.Linecast(a, b, out var hit, Mask, QueryTriggerInteraction.Ignore) && Vector3.Distance(a, hit.point) > Radius + 0.1f) { seen = false; break; }
                    }
                    if (!seen) continue;
                    if (Flat(p - start).magnitude <= reach && BestYaw(p, interest, maxTurn, out yaw, out open, need)) { at = p; return true; }
                }
            at = start; yaw = 0; open = 0; return false;
        }

        /// What the reader sees on arrival, from eye height (the page and the reading room hidden), as a desktop render.
        public static void Preview(Vector3 feet, float yaw, string file)
        {
            var hide = new List<GameObject>();
            foreach (var n in new[] { "ReadingPanel", "ReadingRoom" }) { var g = GameObject.Find(n); if (g && g.activeSelf) { g.SetActive(false); hide.Add(g); } }
            var go = new GameObject("__preview"); var cam = go.AddComponent<Camera>();
            go.transform.SetPositionAndRotation(feet + Vector3.up * 1.6f, Quaternion.Euler(8, yaw, 0));
            cam.fieldOfView = 75; cam.nearClipPlane = 0.05f; cam.farClipPlane = 1200f; cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = Color.black;
            var rt = new RenderTexture(1280, 720, 24); cam.targetTexture = rt; cam.Render();
            var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false); var prev = RenderTexture.active; RenderTexture.active = rt;
            tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0); tex.Apply(); RenderTexture.active = prev;
            File.WriteAllBytes(file, tex.EncodeToPNG());
            cam.targetTexture = null; UnityEngine.Object.DestroyImmediate(rt); UnityEngine.Object.DestroyImmediate(tex); UnityEngine.Object.DestroyImmediate(go);
            foreach (var g in hide) g.SetActive(true);
        }
    }
}
