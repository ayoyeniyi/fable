// Shows a generated reading room (GeneratedRooms) around the reader at runtime.
//
// The room is an unlit glTF whose light was baked in Blender, so it is loaded with glTFast and given plain unlit
// materials (UnlitRooms below, from a material kept in Resources so its shader is always in the build) and nothing
// is lit at runtime. It is placed so its anchor.reader.entrance is under the reader and anchor.reader.look is
// straight ahead of the rig.
using System;
using System.Collections;
using System.IO;
using System.Threading.Tasks;
using GLTFast;
using GLTFast.Logging;
using GLTFast.Materials;
using GLTFast.Schema;
using UnityEngine;
using Material = UnityEngine.Material;

namespace Fable
{
    public static class GeneratedRoomView
    {
        /// Set before loading the library room scene: the uploaded book's room to show there instead of the library.
        public static string PendingBook; public static int PendingRoom;
        public static string LastLoad { get; private set; }

        /// Load the room into a new root, place it about the rig, and report how it went (null on success).
        public static IEnumerator Load(string slug, int n, Transform rig, Action<GameObject, string> done)
        {
            var t0 = Time.realtimeSinceStartup;
            var path = Path.Combine(GeneratedRooms.Dir(slug, n), "room.gltf");
            if (!File.Exists(path)) { done(null, "the room is not on the headset"); yield break; }
            var root = new GameObject($"GeneratedRoom {slug} r{n}");
            var import = new GltfImport(materialGenerator: new UnlitRooms(), logger: new ConsoleLogger());
            var settings = new ImportSettings { GenerateMipMaps = true, AnisotropicFilterLevel = 4 };
            Task<bool> load = import.Load(new Uri(path, UriKind.Absolute), settings);
            while (!load.IsCompleted) yield return null;
            if (load.IsFaulted || !load.Result) { UnityEngine.Object.Destroy(root); done(null, "the room could not be read"); yield break; }
            Task<bool> inst = import.InstantiateMainSceneAsync(root.transform);
            while (!inst.IsCompleted) yield return null;
            if (inst.IsFaulted || !inst.Result) { UnityEngine.Object.Destroy(root); done(null, "the room could not be built"); yield break; }
            var ent = Find(root.transform, "anchor.reader.entrance"); var look = Find(root.transform, "anchor.reader.look");
            if (ent && look && rig)
            {
                var dir = Vector3.ProjectOnPlane(look.position - ent.position, Vector3.up);
                var fwd = Vector3.ProjectOnPlane(rig.forward, Vector3.up);
                if (dir.sqrMagnitude > 1e-4f && fwd.sqrMagnitude > 1e-4f) root.transform.rotation = Quaternion.FromToRotation(dir.normalized, fwd.normalized) * root.transform.rotation;
                root.transform.position += rig.position - ent.position;
            }
            foreach (var r in root.GetComponentsInChildren<Renderer>(true)) { r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false; }
            RenderSettings.fog = false;
            int tris = 0; foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true)) if (mf.sharedMesh) tris += mf.sharedMesh.triangles.Length / 3;
            LastLoad = $"{slug} r{n}: {tris} triangles, loaded in {(Time.realtimeSinceStartup - t0) * 1000:F0} ms";
            Debug.Log("[Fable] rooms: " + LastLoad);
            done(root, null);
        }

        static Transform Find(Transform t, string name)
        {
            if (t.name == name) return t;
            foreach (Transform c in t) { var f = Find(c, name); if (f) return f; }
            return null;
        }

        /// glTFast material generator: every material is unlit with its base colour texture (the baked light).
        class UnlitRooms : IMaterialGenerator
        {
            static Material template;
            static Material Template()
            {
                if (template) return template;
                template = Resources.Load<Material>("GeneratedRoomUnlit");
                if (!template) template = new Material(Shader.Find("Universal Render Pipeline/Unlit"));
                return template;
            }
            public Material GetDefaultMaterial(bool pointsSupport = false) => new Material(Template());
            public Material GenerateMaterial(MaterialBase gltfMaterial, IGltfReadable gltf, bool pointsSupport = false)
            {
                var m = new Material(Template()) { name = gltfMaterial.name };
                var info = gltfMaterial.PbrMetallicRoughness?.BaseColorTexture;
                if (info != null && info.index >= 0)
                {
                    var tex = gltf.GetTexture(info.index);
                    if (tex) { tex.wrapMode = TextureWrapMode.Clamp; m.SetTexture("_BaseMap", tex); m.mainTexture = tex; }
                }
                m.SetColor("_BaseColor", Color.white);
                if (gltfMaterial.doubleSided) m.SetFloat("_Cull", 0f);   // grass blades and leaf cards are seen from both sides
                return m;
            }
            public void SetLogger(ICodeLogger logger) { }
        }
    }
}
