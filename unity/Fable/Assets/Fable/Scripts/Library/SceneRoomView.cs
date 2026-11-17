// Shows a downloaded scene room (SceneRooms, docs/SCENE_ROOMS_PIPELINE.md) around the reader at runtime, in the
// library-room scene, the way GeneratedRoomView shows a generated room.
//
// The room's light was baked in Blender (blender/runtime_bake.py): each material has its base colour on UV 0 and a
// light texture as its emissive texture on UV 1, drawn by Fable/SceneRoom (base x light, nothing lit at runtime); sky
// and backdrops are unlit. The living parts are applied here from their node names, as FableLiving does in the editor
// for built rooms: veg.* sway and cloth.* billow in the room's wind (LivingScene), water.* gets Fable/Water, fx.* a
// fire (flames, embers, crackle), sound.* a positional loop, and the room's ambience replaces the library's.
// What is not done at runtime: an ocean's swell subdivision and a river's flow directions (the water moves with its
// detail normals only), flame.* meshes and flickering lights (the baked light is fixed).
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using GLTFast;
using GLTFast.Logging;
using GLTFast.Materials;
using GLTFast.Schema;
using Newtonsoft.Json.Linq;
using UnityEngine;
using Material = UnityEngine.Material;

namespace Fable
{
    public static class SceneRoomView
    {
        /// Set before loading the host scene: the room to show and the scene to go back to when the experience ends.
        public static SceneRoomRef Pending; public static string ReturnScene;
        /// The room shown in the current scene (null: none).
        public static string ShownId { get; private set; }
        public static GameObject Shown { get; private set; }
        public static string LastLoad { get; private set; }

        static readonly Dictionary<string, (float amp, float flutter)> Veg = new()
        {
            ["grass"] = (0.11f, 0.15f), ["flowers"] = (0.09f, 0.2f), ["crop"] = (0.14f, 0.15f), ["reeds"] = (0.13f, 0.2f),
            ["shrub"] = (0.05f, 0.5f), ["leaves"] = (0.05f, 0.7f), ["crown"] = (0.12f, 0.3f), ["pines"] = (0.12f, 0.3f), ["pinemass"] = (0.08f, 0.2f),
        };
        static readonly Dictionary<string, float> Cloth = new() { ["sail"] = 0.25f, ["flag"] = 0.15f, ["curtain"] = 0.05f, ["washing"] = 0.1f, ["awning"] = 0.12f };
        static readonly Dictionary<string, string> Sounds = new()
        {
            ["surf"] = "surf", ["river"] = "river", ["fire"] = "fire", ["wind-trees"] = "wind-pines", ["wind"] = "wind-grass", ["birds"] = "birds",
            ["gulls"] = "gulls", ["rigging"] = "rigging", ["crowd"] = "tavern", ["clock"] = "clock", ["rain"] = "rain", ["candle"] = "candle",
        };
        const int MaxSources = 6, MaxFires = 3;
        static Dictionary<string, float> Radii;   // fx.* radius (glTF extras), read from the file: glTFast keeps no extras

        public static void Forget() { ShownId = null; Shown = null; }

        /// Load the room into a new root, place it about the rig (anchor.reader.entrance under the reader, facing
        /// anchor.reader.look), wire its living parts, and report how it went (null on success).
        public static IEnumerator Load(SceneRoomRef r, Transform rig, Action<GameObject, string> done)
        {
            var t0 = Time.realtimeSinceStartup;
            var path = SceneRooms.Instance.Gltf(r.Id);
            if (!SceneRooms.Instance.IsReady(r) || !File.Exists(path)) { done(null, "the room is not on the headset"); yield break; }
            JObject meta = null;
            try { var mp = Path.Combine(SceneRooms.Instance.Dir(r.Id), "room.json"); if (File.Exists(mp)) meta = JObject.Parse(File.ReadAllText(mp)); } catch { }
            float lightScale = (float?)meta?["lightScale"] ?? 1f, white = (float?)meta?["white"] ?? 3f;
            var root = new GameObject($"SceneRoom {r.Id}");
            var import = new GltfImport(materialGenerator: new Materials(lightScale, white), logger: new ConsoleLogger());
            Task<bool> load = import.Load(new Uri(path, UriKind.Absolute), new ImportSettings { GenerateMipMaps = true, AnisotropicFilterLevel = 4 });
            while (!load.IsCompleted) yield return null;
            if (load.IsFaulted || !load.Result) { UnityEngine.Object.Destroy(root); done(null, "the room could not be read"); yield break; }
            Task<bool> inst = import.InstantiateMainSceneAsync(root.transform);
            while (!inst.IsCompleted) yield return null;
            if (inst.IsFaulted || !inst.Result) { UnityEngine.Object.Destroy(root); done(null, "the room could not be built"); yield break; }
            var ent = Find(root.transform, "anchor.reader.entrance"); var look = Find(root.transform, "anchor.reader.look");
            float yaw = 0;
            if (ent && look && rig)
            {
                var dir = Vector3.ProjectOnPlane(look.position - ent.position, Vector3.up);
                var fwd = Vector3.ProjectOnPlane(rig.forward, Vector3.up);
                if (dir.sqrMagnitude > 1e-4f && fwd.sqrMagnitude > 1e-4f) { var q = Quaternion.FromToRotation(dir.normalized, fwd.normalized); yaw = q.eulerAngles.y; root.transform.rotation = Quaternion.Euler(0, yaw, 0) * root.transform.rotation; }
                root.transform.position += rig.position - ent.position;
            }
            foreach (var rd in root.GetComponentsInChildren<Renderer>(true)) { rd.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; rd.receiveShadows = false; rd.lightProbeUsage = UnityEngine.Rendering.LightProbeUsage.Off; rd.reflectionProbeUsage = UnityEngine.Rendering.ReflectionProbeUsage.Off; }
            RenderSettings.fog = false;
            float reach = 0; var c = rig ? rig.position : Vector3.zero;
            foreach (var rd in root.GetComponentsInChildren<Renderer>(true)) { var b = rd.bounds; reach = Mathf.Max(reach, (b.center - c).magnitude + Mathf.Max(b.extents.x, Mathf.Max(b.extents.y, b.extents.z))); }
            foreach (var cam in UnityEngine.Object.FindObjectsByType<UnityEngine.Camera>(FindObjectsSortMode.None)) if (cam.farClipPlane < reach * 1.05f) cam.farClipPlane = reach * 1.05f;
            Radii = new Dictionary<string, float>();
            try
            {
                foreach (var node in (JArray)JObject.Parse(File.ReadAllText(path))["nodes"] ?? new JArray())
                    if ((string)node["name"] is string nn && nn.StartsWith("fx.") && node["extras"]?["radius"] != null) Radii[nn] = (float)node["extras"]["radius"];
            }
            catch { }
            var living = Living(root, meta, yaw);
            int tris = 0; foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true)) if (mf.sharedMesh) tris += mf.sharedMesh.triangles.Length / 3;
            ShownId = r.Id; Shown = root; SceneRooms.Instance.InUse = r.Id; SceneRooms.Instance.Touch(r.Id);
            LastLoad = $"{r.Id} {r.Version}: {tris} triangles, {living}, loaded in {(Time.realtimeSinceStartup - t0) * 1000:F0} ms";
            Debug.Log("[Fable] scene rooms: " + LastLoad);
            done(root, null);
        }

        /// The living parts, from the node names (docs/LIVING_SCENES.md).
        static string Living(GameObject root, JObject meta, float yaw)
        {
            int veg = 0, cloth = 0, water = 0, fires = 0;
            var sources = new List<AudioSource>(); var volumes = new List<float>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true).ToList())
            {
                var n = t.name; var parts = n.Split('.'); var kind = parts.Length > 1 ? parts[1] : "";
                if (n.StartsWith("veg.") || n.StartsWith("cloth."))
                {
                    foreach (var rd in t.GetComponentsInChildren<MeshRenderer>(true))
                        foreach (var m in rd.materials)
                        {
                            if (n.StartsWith("veg.")) { var k = Veg.TryGetValue(kind, out var v) ? v : (0.06f, 0.3f); m.SetFloat("_SwayAmplitude", k.Item1); m.SetFloat("_SwayFlutter", k.Item2); veg++; }
                            else { m.SetFloat("_Billow", Cloth.TryGetValue(kind, out var a) ? a : 0.08f); cloth++; }
                        }
                }
                else if (n.StartsWith("water."))
                {
                    var tmpl = Resources.Load<Material>("SceneRooms/Water_" + (kind == "ocean" ? "ocean" : kind is "river" or "stream" ? "river" : "pond"));
                    foreach (var rd in t.GetComponentsInChildren<MeshRenderer>(true))
                    {
                        if (!tmpl) break;
                        var src = rd.sharedMaterial; var w = new Material(tmpl) { name = n + "_water" };
                        if (src && src.HasProperty("_BaseMap")) w.SetTexture("_BaseMap", src.GetTexture("_BaseMap"));
                        float a = (((float?)meta?["windToward"] ?? 60f) + yaw) * Mathf.Deg2Rad; var dirOS = rd.transform.InverseTransformDirection(new Vector3(Mathf.Sin(a), 0, Mathf.Cos(a)));
                        w.SetVector("_WaveDir", new Vector4(dirOS.x, 0, dirOS.z, 0));
                        rd.sharedMaterials = Enumerable.Repeat(w, rd.sharedMaterials.Length).ToArray(); water++;
                    }
                }
                else if (n.StartsWith("fx.") && fires < MaxFires)
                {
                    var prefab = Resources.Load<GameObject>("SceneRooms/Fire");
                    if (prefab)
                    {
                        float radius = Radii != null && Radii.TryGetValue(n, out var rr) ? rr : 0.12f;
                        var go = UnityEngine.Object.Instantiate(prefab, t, false); go.name = "living.fire";
                        go.transform.localScale = Vector3.one * Mathf.Max(0.2f, radius / 0.25f) / Mathf.Max(1e-3f, t.lossyScale.x);
                        fires++;
                        if (sources.Count < MaxSources) { var s = Source(go, kind is "candle" or "lantern" ? "candle" : "fire", 1.2f, 0.3f); if (s) { sources.Add(s); volumes.Add(kind is "candle" or "lantern" ? 0.25f : 0.55f); } }
                    }
                }
                else if (n.StartsWith("sound.") && sources.Count < MaxSources && Sounds.TryGetValue(kind, out var clip))
                {
                    var s = Source(t.gameObject, clip, 2.5f, 0.6f); if (s) { sources.Add(s); volumes.Add(0.5f); }
                }
            }
            var ls = root.AddComponent<LivingScene>();
            bool outdoor = (bool?)meta?["outdoor"] ?? true;
            ls.WindStrength = (float?)meta?["wind"] ?? (outdoor ? 0.35f : 0f);
            ls.WindToward = (((float?)meta?["windToward"] ?? 60f) + yaw) % 360f;
            ls.Sources = sources.ToArray(); ls.SourceVolumes = volumes.ToArray();
            ls.enabled = false; ls.enabled = true;   // OnEnable plays the sources now that they are set
            // the room's ambience replaces the library's
            var amb = (string)meta?["ambience"];
            if (!string.IsNullOrEmpty(amb))
            {
                foreach (var rs in UnityEngine.Object.FindObjectsByType<RoomSound>(FindObjectsSortMode.None)) UnityEngine.Object.Destroy(rs);
                foreach (var a in UnityEngine.Object.FindObjectsByType<AudioSource>(FindObjectsSortMode.None)) if (a.spatialBlend < 0.5f && !a.transform.IsChildOf(root.transform)) a.Stop();
                var rsNew = root.AddComponent<RoomSound>(); rsNew.Ambience = amb;
            }
            return $"living: {veg} sway, {cloth} billow, {water} water, {fires} fires, {sources.Count} sounds, wind {ls.WindStrength:F2}";
        }

        static AudioSource Source(GameObject go, string clipKind, float minDistance, float spread)
        {
            var clip = Resources.Load<AudioClip>("Audio/amb." + clipKind); if (!clip) return null;
            var s = go.AddComponent<AudioSource>(); s.clip = clip; s.loop = true; s.playOnAwake = false; s.spatialBlend = 1f; s.dopplerLevel = 0;
            s.rolloffMode = AudioRolloffMode.Logarithmic; s.minDistance = minDistance; s.maxDistance = 40f; s.spatialize = true; s.spread = spread * 60f; s.volume = 0;
            return s;
        }

        public static Transform Find(Transform t, string name)
        {
            if (t.name == name) return t;
            foreach (Transform c in t) { var f = Find(c, name); if (f) return f; }
            return null;
        }

        /// glTFast material generator: Fable/SceneRoom from the base colour (UV 0) and the light texture (emissive, UV 1).
        class Materials : IMaterialGenerator
        {
            readonly float lightScale, white;
            public Materials(float lightScale, float white) { this.lightScale = lightScale; this.white = white; }
            static Material opaque, cutout;
            static Material Template(bool cut)
            {
                if (!opaque) opaque = Resources.Load<Material>("SceneRooms/SceneRoomLit");
                if (!cutout) cutout = Resources.Load<Material>("SceneRooms/SceneRoomCutout");
                var m = cut ? cutout : opaque;
                return m ? m : new Material(Shader.Find("Fable/SceneRoom"));
            }
            public Material GetDefaultMaterial(bool pointsSupport = false) => new Material(Template(false));
            public Material GenerateMaterial(MaterialBase g, IGltfReadable gltf, bool pointsSupport = false)
            {
                bool cut = g.GetAlphaMode() == MaterialBase.AlphaMode.Mask;
                var m = new Material(Template(cut)) { name = g.name };
                var bt = g.PbrMetallicRoughness?.BaseColorTexture;
                if (bt != null && bt.index >= 0) { var tex = gltf.GetTexture(bt.index); if (tex) { tex.wrapMode = TextureWrapMode.Repeat; m.SetTexture("_BaseMap", tex); } }
                var bc = g.PbrMetallicRoughness?.BaseColor ?? Color.white; m.SetColor("_BaseColor", bc);
                var et = g.EmissiveTexture;
                if (et != null && et.index >= 0 && et.texCoord == 1)
                {
                    var lt = gltf.GetTexture(et.index); if (lt) { lt.wrapMode = TextureWrapMode.Clamp; m.SetTexture("_LightMap", lt); }
                    m.SetFloat("_Unlit", 0); m.SetFloat("_LightScale", lightScale); m.SetFloat("_White", white);
                }
                else m.SetFloat("_Unlit", 1);
                if (cut) { m.EnableKeyword("_ALPHATEST_ON"); m.SetFloat("_Cutoff", g.alphaCutoff); m.renderQueue = 2450; }
                else { m.DisableKeyword("_ALPHATEST_ON"); m.renderQueue = 2000; }
                m.SetFloat("_Cull", g.doubleSided ? 0f : 2f);
                m.enableInstancing = true;
                return m;
            }
            public void SetLogger(ICodeLogger logger) { }
        }
    }
}
