// Living scenes, the Unity side of docs/LIVING_SCENES.md: finds the convention names in a room's imported glTF
// (water.*, veg.*, cloth.*, fx.fire/candle/torch/lantern.*, sound.*) plus a table of the older rooms' own names, and
// attaches the moving materials, fires, lights and sounds. FableBuild.BuildScene calls Apply before the bake; for
// scenes already baked, ApplyLiving() re-applies in place (the lightmaps stay valid: meshes keep their lightmap UVs and
// renderers their lightmap slots), so nothing needs rebaking.
//
// Everything starts from the glTF originals (the prefab source of each renderer), so Apply is idempotent. Generated
// assets: Assets/Fable/Living/<scene>/ (meshes with weights in vertex colour, materials), Assets/Fable/Living/Shared/.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace Fable.Editor
{
    public static class FableLiving
    {
        const string Root = "Assets/Fable/Living", Shared = Root + "/Shared";

        /// Names the rooms built before the conventions use for the same things (renderer name -> living name).
        static readonly Dictionary<string, Dictionary<string, string>> Legacy = new()
        {
            ["calypsos-cave"] = new() { ["MESH_Sea"] = "water.ocean.near", ["far.Sea"] = "water.ocean.far", ["MESH_Water"] = "water.stream.rills", ["MESH_AlderLeaves"] = "veg.leaves.alder", ["MESH_PoplarLeaves"] = "veg.leaves.poplar", ["MESH_Cypress"] = "veg.crown.cypress", ["MESH_VineLeaves"] = "veg.leaves.vine", ["MESH_Herbage"] = "veg.grass.herbage", ["MESH_Violets"] = "veg.flowers.violets", ["MESH_Flame"] = "flame.hearth" },
            ["odysseus-ship"] = new() { ["MESH_Sea"] = "water.ocean.near", ["far.Sea"] = "water.ocean.far", ["MESH_Maquis"] = "veg.shrub.maquis" },
            ["lilliput-beach"] = new() { ["far.sea"] = "water.ocean.sea", ["MESH_Hedge"] = "veg.shrub.hedge", ["MESH_Leaves"] = "veg.leaves.trees" },
            ["poppy-field"] = new() { ["MESH_Water"] = "water.river.brook", ["MESH_PoppyPetal"] = "veg.flowers.poppies", ["MESH_MeadowFlowers"] = "veg.flowers.meadow", ["MESH_Herbage"] = "veg.grass.herbage", ["MESH_TreeLeaves"] = "veg.leaves.trees", ["MESH_LeavesShade"] = "veg.leaves.shade" },
            ["mad-tea-party"] = new() { ["MESH_Hedge"] = "veg.shrub.hedge", ["MESH_Leaves"] = "veg.leaves.tree", ["MESH_FlowerPink"] = "veg.flowers.pink", ["MESH_FlowerYellow"] = "veg.flowers.yellow" },
            ["queens-croquet-ground"] = new() { ["MESH_Hedge"] = "veg.shrub.hedge", ["MESH_TreeLeaves"] = "veg.leaves.trees", ["MESH_RoseLeaves"] = "veg.shrub.roses", ["MESH_RoseRed"] = "veg.flowers.red", ["MESH_RoseWhite"] = "veg.flowers.white" },
            ["laputa"] = new() { ["MESH_Grass"] = "veg.grass.lawns", ["MESH_Flowers"] = "veg.flowers.beds", ["MESH_Leaves"] = "veg.leaves.shrubs", ["MESH_TreeFoliage"] = "veg.crown.trees", ["MESH_WallPlants"] = "veg.leaves.wall" },
            ["kansas-farmhouse"] = new() { ["MESH_PrairieGrass"] = "veg.grass.prairie", ["MESH_Flame"] = "flame.lamp" },
            ["ithaca-hall"] = new() { ["MESH_Weeds"] = "veg.grass.weeds", ["MESH_Flame"] = "flame.hearth" },
            ["glumdalclitchs-room"] = new() { ["MESH_Flame"] = "flame.candle" },
            ["hall-of-doors"] = new() { ["MESH_Flame"] = "flame.lamps" },
            ["lobby"] = new() { ["MESH_Flame"] = "flame.lamp" },
            ["library-room"] = new() { ["MESH_Flame"] = "flame.lamp" },
        };
        /// Older rooms' hearths (no fx.fire empty): a fire at the base of the modelled flame.
        static readonly HashSet<string> LegacyHearths = new() { "calypsos-cave", "ithaca-hall" };
        /// Older rooms' point sources: scene -> (sound kind, anchor or renderer name).
        static readonly Dictionary<string, (string kind, string at)[]> LegacySounds = new()
        {
            ["calypsos-cave"] = new[] { ("river", "MESH_Water") },
            ["poppy-field"] = new[] { ("river", "anchor.river.bank") },
        };

        // per kind: sway amplitude (m at weight 1, strength 1), flutter share, height for full weight (m)
        static readonly Dictionary<string, (float amp, float flutter, float height)> VegKinds = new()
        {
            ["grass"] = (0.11f, 0.15f, 0.6f), ["flowers"] = (0.09f, 0.2f, 0.7f), ["crop"] = (0.14f, 0.15f, 1.0f), ["reeds"] = (0.13f, 0.2f, 1.2f),
            ["shrub"] = (0.05f, 0.5f, 1.8f), ["leaves"] = (0.05f, 0.7f, 3f), ["crown"] = (0.12f, 0.3f, 8f),
        };
        static readonly Dictionary<string, float> ClothKinds = new() { ["sail"] = 0.25f, ["flag"] = 0.15f, ["curtain"] = 0.05f, ["washing"] = 0.1f };
        /// sound.<kind>.* -> the library clip amb.<clip>
        public static readonly Dictionary<string, string> SoundClips = new()
        {
            ["surf"] = "surf", ["river"] = "river", ["fire"] = "fire", ["wind-trees"] = "wind-pines", ["wind"] = "wind-grass", ["birds"] = "birds",
            ["gulls"] = "gulls", ["rigging"] = "rigging", ["crowd"] = "tavern", ["clock"] = "clock", ["rain"] = "rain", ["candle"] = "candle",
        };

        const int MaxParticleSystems = 3, MaxRealtimeLights = 3, MaxPositionalSounds = 6;

        public class Report { public int Water, Veg, Cloth, Flames, Fires, Candles, Sounds, Lights, Particles; public List<string> Notes = new(); public override string ToString() => $"water {Water}, veg {Veg}, cloth {Cloth}, flames {Flames}, fires {Fires}, candles/lanterns {Candles}, sounds {Sounds}, realtime lights {Lights}, particle systems {Particles}" + (Notes.Count > 0 ? " (" + string.Join("; ", Notes) + ")" : ""); }

        /// Re-apply to every built scene in place (no rebuild, no rebake).
        [MenuItem("Fable/Apply Living Scenes")]
        public static void ApplyLiving() { foreach (var d in FableBuild.Scenes.Where(d => File.Exists(d.Scene))) ApplyLiving(d.Id); }

        public static void ApplyLiving(string sceneId)
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new Exception("exit play mode first");
            var def = FableBuild.Scenes.First(d => d.Id == sceneId);
            var scene = EditorSceneManager.OpenScene(def.Scene, OpenSceneMode.Single);
            var env = GameObject.Find("env." + sceneId); if (!env) throw new Exception($"no env.{sceneId} in {def.Scene}");
            var r = Apply(env, def);
            var rs = Object.FindFirstObjectByType<RoomSound>(); if (rs) { rs.Id = FableBuild.MusicId(def); rs.Ambience = FableBuild.AmbienceOf(def); EditorUtility.SetDirty(rs); }
            EditorSceneManager.MarkSceneDirty(scene); EditorSceneManager.SaveScene(scene);
            Debug.Log($"[FableLiving] {sceneId}: {r}");
        }

        public static Report Apply(GameObject env, FableBuild.SceneDef def)
        {
            var rep = new Report(); var id = def.Id;
            Directory.CreateDirectory($"{Root}/{id}"); EnsureShared();
            // undo a previous Apply: spawned objects, the runtime component, and every renderer back to its glTF original
            foreach (var t in env.GetComponentsInChildren<Transform>(true).Where(t => t && t.name.StartsWith("living.")).ToList()) if (t) Object.DestroyImmediate(t.gameObject);
            foreach (var c in env.GetComponents<LivingScene>()) Object.DestroyImmediate(c);
            foreach (var r in env.GetComponentsInChildren<Renderer>(true)) Restore(r);

            var legacy = Legacy.TryGetValue(id, out var lm) ? lm : new Dictionary<string, string>();
            var extras = GltfExtras(def.Glb);
            var renderers = env.GetComponentsInChildren<MeshRenderer>(true).Where(r => !UnderAsset(r.transform, env.transform)).ToArray();
            string LivingName(Renderer r)
            {
                foreach (var t in new[] { r.transform, r.transform.parent })
                    if (t && (t.name.StartsWith("water.") || t.name.StartsWith("veg.") || t.name.StartsWith("cloth."))) return t.name;
                return legacy.TryGetValue(r.name, out var n) ? n : null;
            }
            var classified = renderers.Select(r => (r, n: LivingName(r))).Where(x => x.n != null).ToList();

            // ground for sway weights: every other solid surface of the room, as temporary colliders
            var temp = new List<MeshCollider>();
            if (classified.Any(x => x.n.StartsWith("veg.") && !HasColours(x.r)))
                foreach (var r in renderers)
                {
                    if (classified.Any(x => x.r == r) || FlowController.IsBackdrop(r.name) || r.name.Contains("Sky")) continue;
                    var mf = r.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh || r.GetComponent<Collider>()) continue;
                    var mc = r.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; temp.Add(mc);
                }
            Physics.SyncTransforms();
            try
            {
                foreach (var (r, n) in classified)
                {
                    var parts = n.Split('.'); var kind = parts.Length > 1 ? parts[1] : "";
                    if (n.StartsWith("water.")) { MakeWater(r, kind, n, def, rep, legacy.ContainsKey(r.name)); rep.Water++; }
                    else if (n.StartsWith("veg.") && VegKinds.TryGetValue(kind, out var vk)) { MakeSway(r, vk, def, rep); rep.Veg++; }
                    else if (n.StartsWith("cloth.") && ClothKinds.TryGetValue(kind, out var amp)) { MakeCloth(r, amp, def); rep.Cloth++; }
                    else if (n.StartsWith("flame.")) { MakeFlame(r, def); rep.Flames++; }
                    else rep.Notes.Add($"unknown kind {n}");
                }
            }
            finally { foreach (var mc in temp) Object.DestroyImmediate(mc); }

            // distant tree lines and other cut-out backdrop cards: the same cheap foliage lighting, still (no sway)
            foreach (var r in renderers.Where(r => FlowController.IsBackdrop(r.name) && classified.All(x => x.r != r)))
            {
                var orig = OriginalMaterials(r); if (!orig.Any(FablePerf.IsCutout)) continue;
                r.sharedMaterials = orig.Select(m => FablePerf.IsCutout(m) ? Converted(m, Shader.Find("Fable/LivingLit"), def.Id, "_far", c => { c.SetFloat("_SwayAmplitude", 0); c.SetFloat("_Billow", 0); c.EnableKeyword("_FABLE_SIMPLE"); }) : m).ToArray();
                rep.Notes.Add($"{r.name}: cheap cut-out");
            }

            // fires, candles, torches and lanterns at their empties; the older rooms' hearths at their modelled flames
            var living = new GameObject("living.fx"); living.transform.SetParent(env.transform, false);
            var sources = new List<AudioSource>(); var volumes = new List<float>();
            int particles = 0, lights = 0;
            var empties = env.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("fx.fire.") || t.name.StartsWith("fx.candle.") || t.name.StartsWith("fx.torch.") || t.name.StartsWith("fx.lantern.")).ToList();
            var fires = empties.Where(t => t.name.StartsWith("fx.fire.")).Select(t => (pos: t.position, radius: Radius(extras, t), name: t.name.Substring(8))).ToList();
            if (LegacyHearths.Contains(id))
                foreach (var r in env.GetComponentsInChildren<Renderer>(true).Where(r => r.name == "MESH_Flame"))
                { var b = r.bounds; fires.Add((new Vector3(b.center.x, b.min.y, b.center.z), Mathf.Max(b.extents.x, b.extents.z) * 0.9f, "hearth")); }
            foreach (var f in fires)
            {
                var go = new GameObject("living.fire." + f.name); go.transform.SetParent(living.transform, false); go.transform.position = f.pos;
                if (particles < MaxParticleSystems) { Flames(go.transform, f.radius); particles++; }
                if (particles < MaxParticleSystems) { Embers(go.transform, f.radius); particles++; }
                if (lights < MaxLights(def)) { FlickerLight(go.transform, f.radius, 0.45f, 2.5f + f.radius * 8f); lights++; }
                var s = Source(go, "fire", 0.9f, 1f, 14f); if (s && sources.Count < MaxPositionalSounds) { sources.Add(s); volumes.Add(0.75f); }
                rep.Fires++;
            }
            foreach (var t in empties.Where(t => !t.name.StartsWith("fx.fire.")))
            {
                bool candle = t.name.StartsWith("fx.candle.");
                var go = new GameObject("living." + t.name.Substring(3)); go.transform.SetParent(living.transform, false); go.transform.position = t.position;
                Card(go.transform, candle ? 0.014f : 0.05f, candle ? 0.036f : 0.13f);
                if (!candle)
                {
                    if (lights < MaxLights(def)) { FlickerLight(go.transform, 0.05f, 0.25f, 2.5f); lights++; }
                    var s = Source(go, "candle", 0.3f, 0.5f, 5f); if (s && sources.Count < MaxPositionalSounds) { sources.Add(s); volumes.Add(0.3f); }
                }
                rep.Candles++;
            }
            // point sound sources
            var points = env.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("sound.")).Select(t => (kind: t.name.Split('.')[1], pos: t.position)).ToList();
            if (LegacySounds.TryGetValue(id, out var ls))
                foreach (var (kind, at) in ls)
                {
                    var t = env.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == at); if (!t) continue;
                    var rr = t.GetComponent<Renderer>(); points.Add((kind, rr ? rr.bounds.center : t.position));
                }
            foreach (var (kind, pos) in points)
            {
                if (sources.Count >= MaxPositionalSounds) { rep.Notes.Add($"sound.{kind} over the {MaxPositionalSounds}-source budget"); continue; }
                if (!SoundClips.TryGetValue(kind, out var clip)) { rep.Notes.Add($"unknown sound kind {kind}"); continue; }
                var go = new GameObject("living.sound." + kind); go.transform.SetParent(living.transform, false); go.transform.position = pos;
                bool big = kind is "surf" or "wind" or "wind-trees" or "rain" or "gulls";
                var s = Source(go, clip, big ? 6f : 2f, big ? 0.4f : 0.8f, big ? 60f : 25f);
                if (s) { sources.Add(s); volumes.Add(big ? 0.8f : 0.6f); }
            }
            rep.Sounds = sources.Count; rep.Lights = lights; rep.Particles = particles;

            var ls2 = env.AddComponent<LivingScene>();
            ls2.WindStrength = FableBuild.WindOf(def); ls2.WindToward = def.WindToward; ls2.Sources = sources.ToArray(); ls2.SourceVolumes = volumes.ToArray();
            if (living.transform.childCount == 0) Object.DestroyImmediate(living);
            AssetDatabase.SaveAssets();
            return rep;
        }

        // ---------------------------------------------------------------- materials and meshes

        static bool UnderAsset(Transform t, Transform root)
        {
            for (; t && t != root; t = t.parent) if (SceneRegistry.IsAssetName(t.name)) return true;
            return false;
        }

        static bool HasColours(Renderer r) { var mf = r.GetComponent<MeshFilter>(); var m = Original(mf); return m && m.HasVertexAttribute(VertexAttribute.Color); }

        static Mesh Original(MeshFilter mf) { if (!mf) return null; var src = PrefabUtility.GetCorrespondingObjectFromSource(mf); return src ? src.sharedMesh : mf.sharedMesh; }
        static Material[] OriginalMaterials(Renderer r) { var src = PrefabUtility.GetCorrespondingObjectFromSource(r); return src ? src.sharedMaterials : r.sharedMaterials; }

        static void Restore(Renderer r)
        {
            var src = PrefabUtility.GetCorrespondingObjectFromSource(r); if (!src) return;
            if (r.sharedMaterials.Any(m => m && m.shader && m.shader.name.StartsWith("Fable/"))) r.sharedMaterials = src.sharedMaterials;
            var mf = r.GetComponent<MeshFilter>(); var smf = PrefabUtility.GetCorrespondingObjectFromSource(mf);
            if (mf && smf && mf.sharedMesh != smf.sharedMesh && AssetDatabase.GetAssetPath(mf.sharedMesh).StartsWith(Root)) mf.sharedMesh = smf.sharedMesh;
        }

        static string Safe(string s) => new string(s.Select(c => char.IsLetterOrDigit(c) || c == '-' || c == '_' || c == '.' ? c : '_').ToArray());

        static Mesh SaveMesh(Mesh m, string sceneId, string name)
        {
            var path = $"{Root}/{sceneId}/{Safe(name)}.asset";
            // a fresh asset each time: copying into the old one leaves the GPU drawing the old vertices until a reload
            if (AssetDatabase.LoadAssetAtPath<Mesh>(path)) AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(m, path); return m;
        }

        static Material SaveMaterial(Material m, string sceneId, string name)
        {
            var path = $"{Root}/{sceneId}/{Safe(name)}.mat";
            var old = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (old) { old.shader = m.shader; old.CopyPropertiesFromMaterial(m); old.shaderKeywords = m.shaderKeywords; old.renderQueue = m.renderQueue; Object.DestroyImmediate(m); EditorUtility.SetDirty(old); return old; }
            AssetDatabase.CreateAsset(m, path); return m;
        }

        static Material Converted(Material src, Shader shader, string sceneId, string suffix, Action<Material> setup)
        {
            var m = new Material(src) { name = src.name + suffix }; m.shader = shader;
            foreach (var p in new[] { "baseColorTexture", "metallicRoughnessTexture", "normalTexture", "occlusionTexture", "emissiveTexture" })
                if (src.HasProperty(p) && m.HasProperty(p)) { m.SetTexture(p, src.GetTexture(p)); if (src.HasProperty(p + "_ST")) m.SetTextureScale(p, src.GetTextureScale(p)); m.SetTextureOffset(p, src.GetTextureOffset(p)); }
            m.shaderKeywords = new string[0];
            if (src.IsKeywordEnabled("_EMISSIVE")) m.EnableKeyword("_EMISSIVE");
            if (src.IsKeywordEnabled("_OCCLUSION") && src.GetTexture("occlusionTexture")) m.EnableKeyword("_OCCLUSION");
            if (src.HasProperty("_AlphaClip") && src.GetFloat("_AlphaClip") > 0.5f) m.EnableKeyword("_ALPHATEST_ON");
            if (src.HasProperty("_Cull") && m.HasProperty("_Cull")) m.SetFloat("_Cull", src.GetFloat("_Cull"));
            m.renderQueue = -1; m.enableInstancing = true;
            // cut-out after every opaque surface (AlphaTest queue): on Quest's tiled GPU an alpha-tested draw among the
            // opaques switches off early depth rejection for what follows, and drawn last it is rejected wherever a
            // wall, trunk or the ground already stands in front
            if (m.IsKeywordEnabled("_ALPHATEST_ON")) m.renderQueue = (int)RenderQueue.AlphaTest;
            setup?.Invoke(m);
            return SaveMaterial(m, sceneId, src.name + suffix);
        }

        static void MakeSway(Renderer r, (float amp, float flutter, float height) k, FableBuild.SceneDef def, Report rep)
        {
            var mf = r.GetComponent<MeshFilter>(); var src = Original(mf); if (!src) return;
            if (!src.HasVertexAttribute(VertexAttribute.Color))
            {
                var m = Object.Instantiate(src); m.name = src.name + "_sway";
                var v = m.vertices; var cols = new Color[v.Length]; var l2w = r.transform.localToWorldMatrix;
                var islandMin = IslandMinY(m);
                int hits = 0;
                for (int i = 0; i < v.Length; i++)
                {
                    var p = l2w.MultiplyPoint3x4(v[i]);
                    float h = Physics.Raycast(p + Vector3.up * 0.02f, Vector3.down, out var hit, 60f) ? (p.y - hit.point.y) : -1f;
                    if (h >= 0) hits++; else h = v[i].y - islandMin[i];
                    float w = Mathf.Clamp01(h / k.height);
                    cols[i] = new Color(Mathf.Pow(w, k.height < 1.5f ? 1.4f : 1f), 0, 0, 1);
                }
                m.colors = cols;
                mf.sharedMesh = SaveMesh(m, def.Id, r.name + "_sway");
                if (hits < v.Length / 2) rep.Notes.Add($"{r.name}: ground found under {hits}/{v.Length} vertices");
            }
            var mats = OriginalMaterials(r).Select(s => Converted(s, Shader.Find("Fable/LivingLit"), def.Id, "_sway", m => { m.SetFloat("_SwayAmplitude", k.amp); m.SetFloat("_SwayFlutter", k.flutter); m.SetFloat("_Billow", 0); m.EnableKeyword("_FABLE_SIMPLE"); })).ToArray();
            r.sharedMaterials = mats;
            if (def.ThinFoliage < 1f) Thin(r, def, rep);
        }

        /// Realtime flicker lights a room may have: none where the flames' glow is baked (SceneDef.NoFlameLights).
        static int MaxLights(FableBuild.SceneDef def) => def.NoFlameLights ? 0 : MaxRealtimeLights;

        /// Fewer foliage cards (SceneDef.ThinFoliage, the share kept): every card within ThinNear metres of where the
        /// reader stands stays; further out a deterministic share of the cards (mesh islands) is dropped, more of
        /// them the further away they are, so the near view is unchanged and the distant canopy reads as before.
        static void Thin(Renderer r, FableBuild.SceneDef def, Report rep)
        {
            var mf = r.GetComponent<MeshFilter>(); var src = mf ? mf.sharedMesh : null; if (!src) return;
            var at = FableBuild.ReaderFeet(def, r.transform.root);
            var island = Islands(src, out int count); var v = src.vertices; var l2w = r.transform.localToWorldMatrix;
            var centre = new Vector3[count]; var n = new int[count];
            for (int i = 0; i < v.Length; i++) { centre[island[i]] += l2w.MultiplyPoint3x4(v[i]); n[island[i]]++; }
            var keep = new bool[count]; int kept = 0;
            for (int c = 0; c < count; c++)
            {
                var p = centre[c] / Mathf.Max(1, n[c]); float d = at.HasValue ? Vector3.Distance(new Vector3(p.x, 0, p.z), new Vector3(at.Value.x, 0, at.Value.z)) : 99f;
                if (d < def.ThinNear) { keep[c] = true; kept++; continue; }
                // keep share falls from 1 at ThinNear to ThinFoliage at twice that distance and beyond
                float share = Mathf.Lerp(1f, def.ThinFoliage, Mathf.Clamp01((d - def.ThinNear) / def.ThinNear));
                uint h = (uint)(c * 2654435761u) ^ 0x9e3779b9u; h ^= h >> 15; h *= 2246822519u; h ^= h >> 13;
                keep[c] = (h % 10000) / 10000f < share; if (keep[c]) kept++;
            }
            if (kept == count) return;
            var m = Object.Instantiate(src); m.name = src.name + "_thin";
            for (int s = 0; s < m.subMeshCount; s++)
            {
                var t = m.GetTriangles(s); var o = new List<int>(t.Length);
                for (int i = 0; i < t.Length; i += 3) if (keep[island[t[i]]]) { o.Add(t[i]); o.Add(t[i + 1]); o.Add(t[i + 2]); }
                m.SetTriangles(o, s);
            }
            mf.sharedMesh = SaveMesh(m, def.Id, r.name + "_thin");
            rep.Notes.Add($"{r.name}: kept {kept}/{count} cards");
        }

        static void MakeCloth(Renderer r, float amp, FableBuild.SceneDef def)
        {
            var mf = r.GetComponent<MeshFilter>(); var src = Original(mf); if (!src) return;
            if (!src.HasVertexAttribute(VertexAttribute.Color))
            {
                var m = Object.Instantiate(src); var v = m.vertices; float top = v.Max(p => p.y), bot = v.Min(p => p.y), h = Mathf.Max(top - bot, 1e-3f);
                m.colors = v.Select(p => new Color((top - p.y) / h, 0, 0, 1)).ToArray();   // hung from the top
                mf.sharedMesh = SaveMesh(m, def.Id, r.name + "_billow");
            }
            r.sharedMaterials = OriginalMaterials(r).Select(s => Converted(s, Shader.Find("Fable/LivingLit"), def.Id, "_billow", m => { m.SetFloat("_Billow", amp); m.SetFloat("_SwayAmplitude", 0); })).ToArray();
        }

        static void MakeFlame(Renderer r, FableBuild.SceneDef def)
        {
            var mf = r.GetComponent<MeshFilter>(); var src = Original(mf); if (!src) return;
            var m = Object.Instantiate(src); var v = m.vertices; var island = Islands(m, out int count);
            var minY = new float[count]; var maxY = new float[count]; for (int i = 0; i < count; i++) { minY[i] = float.MaxValue; maxY[i] = float.MinValue; }
            for (int i = 0; i < v.Length; i++) { minY[island[i]] = Mathf.Min(minY[island[i]], v[i].y); maxY[island[i]] = Mathf.Max(maxY[island[i]], v[i].y); }
            var rnd = new System.Random(def.Id.GetHashCode()); var phase = Enumerable.Range(0, count).Select(_ => (float)rnd.NextDouble()).ToArray();
            m.colors = Enumerable.Range(0, v.Length).Select(i => new Color(Mathf.Clamp01((v[i].y - minY[island[i]]) / Mathf.Max(maxY[island[i]] - minY[island[i]], 1e-4f)), phase[island[i]], 0, 1)).ToArray();
            mf.sharedMesh = SaveMesh(m, def.Id, r.name + "_flame");
            float tall = Enumerable.Range(0, count).Average(i => maxY[i] - minY[i]);
            r.sharedMaterials = OriginalMaterials(r).Select(s => Converted(s, Shader.Find("Fable/Flame"), def.Id, "_flame", mm => { mm.SetFloat("_Lick", tall * 0.12f); mm.SetFloat("_Flicker", 0.3f); mm.SetFloat("_Cull", 0); })).ToArray();
            r.shadowCastingMode = ShadowCastingMode.Off;
        }

        static void MakeWater(Renderer r, string kind, string name, FableBuild.SceneDef def, Report rep, bool legacyMesh)
        {
            var mf = r.GetComponent<MeshFilter>(); var src = Original(mf); if (!src) return;
            bool ocean = kind == "ocean", river = kind is "river" or "stream";
            var m = Object.Instantiate(src); m.name = src.name + "_water";
            if (!m.HasVertexAttribute(VertexAttribute.Color)) m.colors = new Color[m.vertexCount];   // no foam painted (a missing colour reads as white)
            if (ocean)
            {
                // the swell needs vertices: split triangles until edges are about 2.5 m (at most ~12k vertices)
                for (int pass = 0; pass < 3 && MeanEdge(m) > 2.6f && m.vertexCount * 4 < 12000; pass++) m = Subdivide(m);
            }
            var w = def.WaterOverride ?? new FableBuild.WaterLook();
            if (river)
            {
                // downstream: V by the convention; the older rooms' baked-atlas UVs say nothing, so for them the
                // SceneDef's direction, else downhill
                List<Vector2> flow;
                if (legacyMesh && w.FlowToward.HasValue)
                {
                    float fa = w.FlowToward.Value * Mathf.Deg2Rad; var d = r.transform.InverseTransformDirection(new Vector3(Mathf.Sin(fa), 0, Mathf.Cos(fa)));
                    flow = Enumerable.Repeat(new Vector2(d.x, d.z).normalized, m.vertexCount).ToList();
                }
                else flow = legacyMesh ? Downhill(m) : FlowDirections(m);
                m.SetUVs(3, flow);
            }
            mf.sharedMesh = SaveMesh(m, def.Id, r.name + "_water");
            var srcMat = OriginalMaterials(r)[0];
            var water = new Material(Shader.Find("Fable/Water")) { name = srcMat.name + "_water" };
            var tex = srcMat.HasProperty("baseColorTexture") ? srcMat.GetTexture("baseColorTexture") : null;
            water.SetTexture("_BaseMap", tex); water.SetColor("_BaseColor", srcMat.HasProperty("baseColorFactor") ? srcMat.GetColor("baseColorFactor") : Color.white);
            water.SetTexture("_DetailNormal", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Shared}/WaterNormals.asset"));
            water.SetTexture("_FoamNoise", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Shared}/FoamNoise.asset"));
            water.DisableKeyword("_WATER_OCEAN"); water.DisableKeyword("_WATER_RIVER"); water.DisableKeyword("_WATER_POND");
            water.EnableKeyword(ocean ? "_WATER_OCEAN" : river ? "_WATER_RIVER" : "_WATER_POND"); water.SetFloat("_Water", ocean ? 0 : river ? 1 : 2);
            // the room's sky: its fog colour at the horizon, its ambient sky colour overhead
            var horizon = RenderSettings.fogColor; var zenith = RenderSettings.ambientMode == AmbientMode.Trilight ? RenderSettings.ambientSkyColor * 1.25f : RenderSettings.ambientLight * 2f;
            water.SetColor("_SkyHorizon", horizon); water.SetColor("_SkyZenith", zenith);
            if (ocean) { water.SetFloat("_WaveHeight", w.SwellHeight); water.SetFloat("_WaveLength", w.SwellLength); water.SetFloat("_DetailTiling", 0.3f); water.SetFloat("_DetailStrength", 0.55f); water.SetFloat("_DetailSpeed", 0.35f); }
            else if (river) { water.SetFloat("_DetailTiling", 0.8f); water.SetFloat("_DetailStrength", 0.45f); water.SetFloat("_FlowSpeed", w.FlowSpeed); water.SetFloat("_Reflectivity", 0.7f); water.SetFloat("_GlintPower", 120); }
            else { water.SetFloat("_DetailTiling", 1.2f); water.SetFloat("_DetailStrength", 0.2f); water.SetFloat("_DetailSpeed", 0.06f); water.SetFloat("_Reflectivity", 0.8f); }
            float a = def.WindToward * Mathf.Deg2Rad; var dirWS = new Vector3(Mathf.Sin(a), 0, Mathf.Cos(a)); var dirOS = r.transform.InverseTransformDirection(dirWS);
            water.SetVector("_WaveDir", new Vector4(dirOS.x, 0, dirOS.z, 0));
            if (w.SkyHorizon.HasValue) water.SetColor("_SkyHorizon", w.SkyHorizon.Value);
            if (w.SkyZenith.HasValue) water.SetColor("_SkyZenith", w.SkyZenith.Value);
            water.enableInstancing = true;
            r.sharedMaterials = Enumerable.Repeat(SaveMaterial(water, def.Id, name), r.sharedMaterials.Length).ToArray();
            r.shadowCastingMode = ShadowCastingMode.Off;
        }

        // ---------------------------------------------------------------- fire, candles, sound

        static void Flames(Transform parent, float radius)
        {
            var go = new GameObject("living.flames"); go.transform.SetParent(parent, false);
            var ps = go.AddComponent<ParticleSystem>(); float s = Mathf.Max(radius / 0.25f, 0.2f);
            var main = ps.main; main.loop = true; main.prewarm = true; main.duration = 2f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(0.45f, 0.8f); main.startSpeed = new ParticleSystem.MinMaxCurve(0.25f * Mathf.Sqrt(s), 0.5f * Mathf.Sqrt(s));
            main.startSize = new ParticleSystem.MinMaxCurve(0.16f * s, 0.3f * s); main.startRotation = new ParticleSystem.MinMaxCurve(-0.4f, 0.4f);
            main.maxParticles = 32; main.simulationSpace = ParticleSystemSimulationSpace.Local; main.scalingMode = ParticleSystemScalingMode.Hierarchy;
            main.startColor = Color.white; main.playOnAwake = true;
            var em = ps.emission; em.rateOverTime = 24f;
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 6f; sh.radius = radius * 0.55f; sh.rotation = new Vector3(-90, 0, 0);
            var col = ps.colorOverLifetime; col.enabled = true; col.color = new ParticleSystem.MinMaxGradient(MakeGradient(
                new[] { (0f, new Color(1f, 0.9f, 0.6f)), (0.25f, new Color(1f, 0.62f, 0.22f)), (0.7f, new Color(0.85f, 0.28f, 0.06f)), (1f, new Color(0.4f, 0.08f, 0.02f)) },
                new[] { (0f, 0f), (0.12f, 0.85f), (0.55f, 0.5f), (1f, 0f) }));
            var size = ps.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0, 0.7f), new Keyframe(0.3f, 1f), new Keyframe(1, 0.25f)));
            var rot = ps.rotationOverLifetime; rot.enabled = true; rot.z = new ParticleSystem.MinMaxCurve(-0.8f, 0.8f);
            var pr = go.GetComponent<ParticleSystemRenderer>(); pr.renderMode = ParticleSystemRenderMode.Billboard; pr.sharedMaterial = SharedMat("FireFlames", "Flame", new Color(1f, 0.8f, 0.55f, 1f));
            pr.shadowCastingMode = ShadowCastingMode.Off; pr.receiveShadows = false; pr.sortingFudge = 0; pr.maxParticleSize = 0.5f;
        }

        static void Embers(Transform parent, float radius)
        {
            var go = new GameObject("living.embers"); go.transform.SetParent(parent, false); go.transform.localPosition = Vector3.up * radius * 0.3f;
            var ps = go.AddComponent<ParticleSystem>(); float s = Mathf.Max(radius / 0.25f, 0.2f);
            var main = ps.main; main.loop = true; main.prewarm = true; main.duration = 3f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(1.2f, 2.4f); main.startSpeed = new ParticleSystem.MinMaxCurve(0.35f * s, 0.8f * s);
            main.startSize = new ParticleSystem.MinMaxCurve(0.008f * s, 0.016f * s); main.gravityModifier = -0.02f;
            main.maxParticles = 14; main.simulationSpace = ParticleSystemSimulationSpace.Local; main.scalingMode = ParticleSystemScalingMode.Hierarchy;
            var em = ps.emission; em.rateOverTime = 3.5f;
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 18f; sh.radius = radius * 0.5f; sh.rotation = new Vector3(-90, 0, 0);
            var col = ps.colorOverLifetime; col.enabled = true; col.color = new ParticleSystem.MinMaxGradient(MakeGradient(
                new[] { (0f, new Color(1f, 0.85f, 0.45f)), (0.5f, new Color(1f, 0.45f, 0.1f)), (1f, new Color(0.6f, 0.12f, 0.02f)) },
                new[] { (0f, 0f), (0.08f, 1f), (0.7f, 0.8f), (1f, 0f) }));
            var noise = ps.noise; noise.enabled = true; noise.strength = 0.35f * s; noise.frequency = 1.2f; noise.quality = ParticleSystemNoiseQuality.Low; noise.scrollSpeed = 0.4f;
            var pr = go.GetComponent<ParticleSystemRenderer>(); pr.renderMode = ParticleSystemRenderMode.Billboard; pr.sharedMaterial = SharedMat("FireEmbers", "Ember", new Color(1f, 0.7f, 0.35f, 1f));
            pr.shadowCastingMode = ShadowCastingMode.Off; pr.receiveShadows = false;
        }

        static void Card(Transform parent, float width, float height)
        {
            var go = new GameObject("living.flame-card"); go.transform.SetParent(parent, false); go.transform.localScale = new Vector3(width, height, 1);
            go.transform.localPosition = Vector3.down * height * 0.12f;
            go.AddComponent<MeshFilter>().sharedMesh = AssetDatabase.LoadAssetAtPath<Mesh>($"{Shared}/FlameCard.asset");
            var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = SharedMat("FlameCard", "Flame", new Color(1f, 0.78f, 0.45f, 1f), billboard: true);
            mr.shadowCastingMode = ShadowCastingMode.Off; mr.receiveShadows = false; mr.lightProbeUsage = LightProbeUsage.Off; mr.reflectionProbeUsage = ReflectionProbeUsage.Off;
            GameObjectUtility.SetStaticEditorFlags(go, 0);
        }

        static void FlickerLight(Transform parent, float radius, float intensity, float range)
        {
            var go = new GameObject("living.light"); go.transform.SetParent(parent, false); go.transform.localPosition = Vector3.up * Mathf.Max(radius, 0.05f) * 1.1f;
            var l = go.AddComponent<Light>(); l.type = LightType.Point; l.lightmapBakeType = LightmapBakeType.Realtime; l.shadows = LightShadows.None;
            l.color = new Color(1f, 0.6f, 0.28f); l.intensity = intensity; l.range = range; l.renderMode = LightRenderMode.ForcePixel;
            var f = go.AddComponent<FireFlicker>(); f.Intensity = intensity; f.Range = range; f.Depth = 0.6f;
        }

        static AudioSource Source(GameObject go, string clipKind, float minDistance, float spread, float maxDistance)
        {
            var clip = Clip(clipKind);
            var s = go.AddComponent<AudioSource>(); s.clip = clip; s.loop = true; s.playOnAwake = false; s.spatialBlend = 1f; s.dopplerLevel = 0;
            s.rolloffMode = AudioRolloffMode.Logarithmic; s.minDistance = minDistance; s.maxDistance = maxDistance; s.spatialize = true; s.spread = spread * 60f; s.volume = 0;
            return s;
        }

        public static AudioClip Clip(string kind)
        {
            foreach (var ext in new[] { ".ogg", ".wav" })
            { var c = AssetDatabase.LoadAssetAtPath<AudioClip>($"Assets/Fable/Resources/Audio/amb.{kind}{ext}"); if (c) return c; }
            Debug.LogWarning($"[FableLiving] no sound amb.{kind} in Resources/Audio yet");
            return null;
        }

        static Gradient MakeGradient((float t, Color c)[] cols, (float t, float a)[] alphas)
        {
            var g = new Gradient(); g.SetKeys(cols.Select(k => new GradientColorKey(k.c, k.t)).ToArray(), alphas.Select(k => new GradientAlphaKey(k.a, k.t)).ToArray()); return g;
        }

        static Material SharedMat(string name, string tex, Color colour, bool billboard = false)
        {
            var path = $"{Shared}/{name}.mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(Shader.Find("Fable/FlameGlow")); AssetDatabase.CreateAsset(m, path); }
            m.shader = Shader.Find("Fable/FlameGlow");
            m.SetTexture("_MainTex", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Shared}/{tex}.asset")); m.SetColor("_Color", colour);
            m.SetFloat("_Billboard", billboard ? 1 : 0); m.SetFloat("_Flicker", billboard ? 0.5f : 0); m.enableInstancing = true; EditorUtility.SetDirty(m);
            return m;
        }

        // ---------------------------------------------------------------- generated shared assets

        /// The assets a downloaded scene room needs at runtime (SceneRoomView.cs), kept in the build through Resources:
        /// the Fable/SceneRoom materials (opaque and cut-out), one Fable/Water material per kind, a fire (flames, embers)
        /// and the Fable/ScreenFade material.
        [MenuItem("Fable/Scene Room Resources")]
        public static void MakeSceneRoomResources()
        {
            EnsureShared();
            const string dir = "Assets/Fable/Resources/SceneRooms"; Directory.CreateDirectory(dir);
            Material Mat(string name, string shader, Action<Material> setup)
            {
                var path = $"{dir}/{name}.mat"; var m = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!m) { m = new Material(Shader.Find(shader)); AssetDatabase.CreateAsset(m, path); }
                m.shader = Shader.Find(shader); setup(m); m.enableInstancing = true; EditorUtility.SetDirty(m); return m;
            }
            Mat("SceneRoomLit", "Fable/SceneRoom", m => { m.DisableKeyword("_ALPHATEST_ON"); m.renderQueue = 2000; });
            Mat("SceneRoomCutout", "Fable/SceneRoom", m => { m.EnableKeyword("_ALPHATEST_ON"); m.renderQueue = 2450; m.SetFloat("_Cull", 0); });
            Mat("Fade", "Fable/ScreenFade", m => m.SetColor("_Color", new Color(0, 0, 0, 0)));
            foreach (var kind in new[] { "ocean", "river", "pond" })
                Mat("Water_" + kind, "Fable/Water", w =>
                {
                    w.SetTexture("_DetailNormal", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Shared}/WaterNormals.asset"));
                    w.SetTexture("_FoamNoise", AssetDatabase.LoadAssetAtPath<Texture2D>($"{Shared}/FoamNoise.asset"));
                    w.DisableKeyword("_WATER_OCEAN"); w.DisableKeyword("_WATER_RIVER"); w.DisableKeyword("_WATER_POND");
                    w.EnableKeyword(kind == "ocean" ? "_WATER_OCEAN" : kind == "river" ? "_WATER_RIVER" : "_WATER_POND"); w.SetFloat("_Water", kind == "ocean" ? 0 : kind == "river" ? 1 : 2);
                    w.SetColor("_SkyHorizon", new Color(0.70f, 0.76f, 0.80f)); w.SetColor("_SkyZenith", new Color(0.46f, 0.55f, 0.66f) * 1.25f);
                    if (kind == "ocean") { w.SetFloat("_WaveHeight", 0.12f); w.SetFloat("_WaveLength", 12f); w.SetFloat("_DetailTiling", 0.3f); w.SetFloat("_DetailStrength", 0.55f); w.SetFloat("_DetailSpeed", 0.35f); }
                    else if (kind == "river") { w.SetFloat("_DetailTiling", 0.8f); w.SetFloat("_DetailStrength", 0.45f); w.SetFloat("_FlowSpeed", 0.5f); w.SetFloat("_Reflectivity", 0.7f); w.SetFloat("_GlintPower", 120); }
                    else { w.SetFloat("_DetailTiling", 1.2f); w.SetFloat("_DetailStrength", 0.2f); w.SetFloat("_DetailSpeed", 0.06f); w.SetFloat("_Reflectivity", 0.8f); }
                });
            var fire = new GameObject("Fire");
            try { Flames(fire.transform, 0.25f); Embers(fire.transform, 0.25f); PrefabUtility.SaveAsPrefabAsset(fire, $"{dir}/Fire.prefab"); }
            finally { Object.DestroyImmediate(fire); }
            AssetDatabase.SaveAssets();
            Debug.Log("[FableLiving] scene room resources in " + dir);
        }

        static void EnsureShared()
        {
            Directory.CreateDirectory(Shared);
            if (!AssetDatabase.LoadAssetAtPath<Texture2D>($"{Shared}/WaterNormals.asset")) AssetDatabase.CreateAsset(WaterNormals(256), $"{Shared}/WaterNormals.asset");
            if (!AssetDatabase.LoadAssetAtPath<Texture2D>($"{Shared}/FoamNoise.asset")) AssetDatabase.CreateAsset(FoamNoise(128), $"{Shared}/FoamNoise.asset");
            if (!AssetDatabase.LoadAssetAtPath<Texture2D>($"{Shared}/Flame.asset")) AssetDatabase.CreateAsset(FlameTexture(64, 128), $"{Shared}/Flame.asset");
            if (!AssetDatabase.LoadAssetAtPath<Texture2D>($"{Shared}/Ember.asset")) AssetDatabase.CreateAsset(EmberTexture(32), $"{Shared}/Ember.asset");
            if (!AssetDatabase.LoadAssetAtPath<Mesh>($"{Shared}/FlameCard.asset"))
            {
                var q = new Mesh { name = "FlameCard", vertices = new[] { new Vector3(-0.5f, 0, 0), new Vector3(0.5f, 0, 0), new Vector3(0.5f, 1, 0), new Vector3(-0.5f, 1, 0) }, uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) }, triangles = new[] { 0, 2, 1, 0, 3, 2 } };
                q.RecalculateNormals(); q.bounds = new Bounds(new Vector3(0, 0.5f, 0), new Vector3(1.5f, 1.5f, 1.5f)); AssetDatabase.CreateAsset(q, $"{Shared}/FlameCard.asset");
            }
        }

        /// Tileable ripple normals: a sum of waves with whole-number frequencies on the torus, so the tile has no seam.
        static Texture2D WaterNormals(int n)
        {
            var rnd = new System.Random(7); var waves = new List<(int fx, int fy, float a, float ph)>();
            for (int i = 0; i < 28; i++)
            {
                int fx = rnd.Next(-9, 10), fy = rnd.Next(-9, 10); if (fx == 0 && fy == 0) fy = 1;
                float f = Mathf.Sqrt(fx * fx + fy * fy); waves.Add((fx, fy, 1f / Mathf.Pow(f, 1.2f), (float)rnd.NextDouble() * 6.283f));
            }
            var t = new Texture2D(n, n, TextureFormat.RGBA32, true, true) { name = "WaterNormals", wrapMode = TextureWrapMode.Repeat, filterMode = FilterMode.Trilinear, anisoLevel = 2 };
            var px = new Color[n * n];
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float u = (float)x / n, v = (float)y / n, dx = 0, dy = 0;
                    foreach (var w in waves) { float ang = 6.283f * (w.fx * u + w.fy * v) + w.ph; float c = Mathf.Cos(ang) * w.a; dx += c * w.fx; dy += c * w.fy; }
                    var nn = new Vector3(-dx * 0.035f, -dy * 0.035f, 1).normalized;
                    px[y * n + x] = new Color(nn.x * 0.5f + 0.5f, nn.y * 0.5f + 0.5f, nn.z * 0.5f + 0.5f, 1);
                }
            t.SetPixels(px); t.Apply(true); return t;
        }

        static Texture2D FoamNoise(int n)
        {
            var t = new Texture2D(n, n, TextureFormat.RGBA32, true, true) { name = "FoamNoise", wrapMode = TextureWrapMode.Repeat };
            var px = new Color[n * n]; var rnd = new System.Random(3); var cells = Enumerable.Range(0, 40).Select(_ => new Vector2((float)rnd.NextDouble(), (float)rnd.NextDouble())).ToArray();
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    var p = new Vector2((float)x / n, (float)y / n); float d1 = 9, d2 = 9;
                    foreach (var c in cells) for (int ox = -1; ox <= 1; ox++) for (int oy = -1; oy <= 1; oy++) { float d = (p - c - new Vector2(ox, oy)).magnitude; if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) d2 = d; }
                    float v = Mathf.Clamp01((d2 - d1) * 9f);   // bright cell edges: a lacy foam pattern
                    px[y * n + x] = new Color(v, v, v, 1);
                }
            t.SetPixels(px); t.Apply(true); return t;
        }

        static Texture2D FlameTexture(int w, int h)
        {
            var t = new Texture2D(w, h, TextureFormat.RGBA32, true, true) { name = "Flame", wrapMode = TextureWrapMode.Clamp };
            var px = new Color[w * h];
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    float u = (x + 0.5f) / w * 2 - 1, v = (y + 0.5f) / h;
                    float width = Mathf.Lerp(0.95f, 0.05f, Mathf.Pow(v, 0.8f)) * Mathf.Sqrt(Mathf.Clamp01(v * 6f));   // a teardrop: round base, pointed tip
                    float a = Mathf.Clamp01(1 - Mathf.Abs(u) / Mathf.Max(width, 1e-3f)); a = a * a * (3 - 2 * a) * Mathf.Clamp01((1 - v) * 1.6f);
                    float core = Mathf.Clamp01(1 - Mathf.Abs(u) / Mathf.Max(width * 0.45f, 1e-3f)) * Mathf.Clamp01(1 - v * 1.6f);
                    px[y * w + x] = new Color(1, 0.8f + 0.2f * core, 0.55f + 0.45f * core, a);
                }
            t.SetPixels(px); t.Apply(true); return t;
        }

        static Texture2D EmberTexture(int n)
        {
            var t = new Texture2D(n, n, TextureFormat.RGBA32, true, true) { name = "Ember", wrapMode = TextureWrapMode.Clamp };
            var px = new Color[n * n];
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++) { float d = new Vector2((x + 0.5f) / n * 2 - 1, (y + 0.5f) / n * 2 - 1).magnitude; float a = Mathf.Clamp01(1 - d); px[y * n + x] = new Color(1, 1, 1, a * a); }
            t.SetPixels(px); t.Apply(true); return t;
        }

        // ---------------------------------------------------------------- mesh helpers

        /// Connected parts of a mesh (vertices welded by position, since glTF splits them at UV seams).
        static int[] Islands(Mesh m, out int count)
        {
            var v = m.vertices; var parent = Enumerable.Range(0, v.Length).ToArray();
            int Find(int i) { while (parent[i] != i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; }
            void Union(int a, int b) { a = Find(a); b = Find(b); if (a != b) parent[a] = b; }
            var weld = new Dictionary<Vector3Int, int>();
            for (int i = 0; i < v.Length; i++) { var k = Vector3Int.RoundToInt(v[i] * 1000f); if (weld.TryGetValue(k, out var j)) Union(i, j); else weld[k] = i; }
            for (int s = 0; s < m.subMeshCount; s++) { var tr = m.GetTriangles(s); for (int i = 0; i < tr.Length; i += 3) { Union(tr[i], tr[i + 1]); Union(tr[i], tr[i + 2]); } }
            var ids = new Dictionary<int, int>(); var island = new int[v.Length];
            for (int i = 0; i < v.Length; i++) { int r = Find(i); if (!ids.TryGetValue(r, out var id)) ids[r] = id = ids.Count; island[i] = id; }
            count = ids.Count; return island;
        }

        static float[] IslandMinY(Mesh m)
        {
            var island = Islands(m, out int count); var v = m.vertices; var min = Enumerable.Repeat(float.MaxValue, count).ToArray();
            for (int i = 0; i < v.Length; i++) min[island[i]] = Mathf.Min(min[island[i]], v[i].y);
            return island.Select(i => min[i]).ToArray();
        }

        static float MeanEdge(Mesh m)
        {
            var v = m.vertices; var t = m.triangles; if (t.Length == 0) return 0; double sum = 0;
            for (int i = 0; i < t.Length; i += 3) sum += (v[t[i]] - v[t[i + 1]]).magnitude + (v[t[i + 1]] - v[t[i + 2]]).magnitude + (v[t[i + 2]] - v[t[i]]).magnitude;
            return (float)(sum / t.Length);
        }

        /// Split every triangle into four, interpolating every vertex attribute (lightmap UVs stay exact on planar water).
        static Mesh Subdivide(Mesh src)
        {
            var pos = new List<Vector3>(src.vertices); var nrm = new List<Vector3>(src.normals); var tan = new List<Vector4>(src.tangents); var col = new List<Color>(src.colors);
            var uvs = Enumerable.Range(0, 4).Select(c => { var l = new List<Vector2>(); src.GetUVs(c, l); return l; }).ToArray();
            var mid = new Dictionary<long, int>();
            int Mid(int a, int b)
            {
                long key = a < b ? ((long)a << 32) | (uint)b : ((long)b << 32) | (uint)a;
                if (mid.TryGetValue(key, out var i)) return i;
                i = pos.Count; pos.Add((pos[a] + pos[b]) * 0.5f);
                if (nrm.Count > 0) nrm.Add(((nrm[a] + nrm[b]) * 0.5f).normalized);
                if (tan.Count > 0) tan.Add((tan[a] + tan[b]) * 0.5f);
                if (col.Count > 0) col.Add((col[a] + col[b]) * 0.5f);
                foreach (var l in uvs) if (l.Count > 0) l.Add((l[a] + l[b]) * 0.5f);
                mid[key] = i; return i;
            }
            var subs = new List<int[]>();
            for (int s = 0; s < src.subMeshCount; s++)
            {
                var t = src.GetTriangles(s); var o = new List<int>(t.Length * 4);
                for (int i = 0; i < t.Length; i += 3)
                {
                    int a = t[i], b = t[i + 1], c = t[i + 2], ab = Mid(a, b), bc = Mid(b, c), ca = Mid(c, a);
                    o.AddRange(new[] { a, ab, ca, ab, b, bc, ca, bc, c, ab, bc, ca });
                }
                subs.Add(o.ToArray());
            }
            var m = new Mesh { name = src.name, indexFormat = pos.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
            m.SetVertices(pos); if (nrm.Count > 0) m.SetNormals(nrm); if (tan.Count > 0) m.SetTangents(tan); if (col.Count > 0) m.SetColors(col);
            for (int c = 0; c < 4; c++) if (uvs[c].Count > 0) m.SetUVs(c, uvs[c]);
            m.subMeshCount = subs.Count; for (int s = 0; s < subs.Count; s++) m.SetTriangles(subs[s], s);
            m.RecalculateBounds(); Object.DestroyImmediate(src); return m;
        }

        /// Downstream direction per vertex in object XZ: the direction V increases across each triangle, averaged.
        static List<Vector2> FlowDirections(Mesh m)
        {
            var v = m.vertices; var uv = m.uv; var t = m.triangles; var acc = new Vector2[v.Length];
            for (int i = 0; i < t.Length; i += 3)
            {
                int a = t[i], b = t[i + 1], c = t[i + 2];
                Vector2 p0 = new(v[a].x, v[a].z), p1 = new(v[b].x, v[b].z), p2 = new(v[c].x, v[c].z);
                Vector2 e1 = p1 - p0, e2 = p2 - p0; float dv1 = uv[b].y - uv[a].y, dv2 = uv[c].y - uv[a].y;
                float det = e1.x * e2.y - e1.y * e2.x; if (Mathf.Abs(det) < 1e-8f) continue;
                // gradient of V in XZ: solve [e1; e2] g = [dv1; dv2]
                var g = new Vector2((dv1 * e2.y - dv2 * e1.y) / det, (e1.x * dv2 - e2.x * dv1) / det);
                if (g.sqrMagnitude < 1e-12f) continue; g.Normalize(); acc[a] += g; acc[b] += g; acc[c] += g;
            }
            return acc.Select(g => g.sqrMagnitude > 1e-8f ? g.normalized : Vector2.zero).ToList();
        }

        /// Downhill direction per vertex in object XZ (for streams whose UVs carry no flow).
        static List<Vector2> Downhill(Mesh m)
        {
            var v = m.vertices; var t = m.triangles; var acc = new Vector2[v.Length];
            for (int i = 0; i < t.Length; i += 3)
            {
                int a = t[i], b = t[i + 1], c = t[i + 2];
                var n = Vector3.Cross(v[b] - v[a], v[c] - v[a]); if (n.y < 0) n = -n;
                var g = new Vector2(n.x, n.z); if (g.sqrMagnitude < 1e-10f) continue;   // a level triangle: no say
                g.Normalize(); acc[a] += g; acc[b] += g; acc[c] += g;
            }
            return acc.Select(g => g.sqrMagnitude > 1e-8f ? g.normalized : Vector2.zero).ToList();
        }

        // ---------------------------------------------------------------- glTF extras (the fire radius)

        /// Node name -> "radius" from the glTF's node extras (Blender custom property, exported with export_extras).
        static Dictionary<string, float> GltfExtras(string gltfPath)
        {
            var d = new Dictionary<string, float>();
            try
            {
                if (!gltfPath.EndsWith(".gltf") || !File.Exists(gltfPath)) return d;
                var j = Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(gltfPath));
                foreach (var n in (Newtonsoft.Json.Linq.JArray)j["nodes"] ?? new Newtonsoft.Json.Linq.JArray())
                {
                    var name = (string)n["name"]; var r = n["extras"]?["radius"] ?? n["extras"]?["fire_radius"];
                    if (name != null && r != null) d[name] = (float)r;
                }
            }
            catch (Exception e) { Debug.LogWarning($"[FableLiving] could not read extras from {gltfPath}: {e.Message}"); }
            return d;
        }

        static float Radius(Dictionary<string, float> extras, Transform t)
        {
            if (extras.TryGetValue(t.name, out var r) && r > 0) return r;
            var s = t.lossyScale.x; return s > 0.02f && Mathf.Abs(s - 1f) > 1e-3f ? s : 0.25f;   // the empty's scale, else a hearth-sized fire
        }
    }
}
