// Import rules for the environment textures that Blender exports next to each .gltf (Assets/Fable/Models/<Scene>/textures).
// glTFast decodes images embedded in a .glb into uncompressed textures; external images go through Unity's own
// TextureImporter instead, so they are compressed for Quest here. Each image's role is read from the .gltf itself:
//   normalTexture                          -> normal map, linear, ASTC 4x4
//   metallicRoughnessTexture, occlusion    -> linear data, ASTC 6x6
//   everything else (base colour, emission) -> sRGB colour, ASTC 6x6
// Mipmaps on, 2048 max, except a 4K colour map (the one ground texture the budget allows) which keeps 4096.
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace Fable.Editor
{
    public class FableTextureImport : AssetPostprocessor
    {
        const string Root = "Assets/Fable/Models/";
        enum Role { Color, Linear, Normal }

        void OnPreprocessTexture()
        {
            if (!assetPath.StartsWith(Root)) return;
            var ti = (TextureImporter)assetImporter;
            var role = RoleOf(assetPath);
            ti.textureShape = TextureImporterShape.Texture2D;   // glTFast requires 2D
            ti.textureType = role == Role.Normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            ti.sRGBTexture = role == Role.Color;
            ti.mipmapEnabled = true; ti.isReadable = false; ti.alphaSource = TextureImporterAlphaSource.None;
            ti.GetSourceTextureWidthAndHeight(out var w, out var h);
            bool ground = role == Role.Color && Mathf.Max(w, h) >= 4096;
            ti.maxTextureSize = ground ? 4096 : 2048;
            ti.anisoLevel = ground ? 4 : 1;
            var android = ti.GetPlatformTextureSettings("Android");
            android.overridden = true; android.maxTextureSize = ti.maxTextureSize;
            android.format = role == Role.Normal ? TextureImporterFormat.ASTC_4x4 : TextureImporterFormat.ASTC_6x6;
            android.compressionQuality = 50;
            ti.SetPlatformTextureSettings(android);
        }

        static readonly Dictionary<string, Dictionary<string, Role>> cache = new();

        /// Finds the .gltf that references this image (same folder or the parent of textures/) and reads its role.
        static Role RoleOf(string texPath)
        {
            var file = Path.GetFileName(texPath);
            var dir = Path.GetDirectoryName(texPath);
            foreach (var d in new[] { dir, Path.GetDirectoryName(dir) })
            {
                if (string.IsNullOrEmpty(d) || !Directory.Exists(d)) continue;
                foreach (var gltf in Directory.GetFiles(d, "*.gltf"))
                {
                    var roles = Roles(gltf);
                    if (roles.TryGetValue(file, out var r)) return r;
                }
            }
            var n = file.ToLowerInvariant();   // fallback when no .gltf is found: Blender's bake pass names
            return n.Contains("normal") ? Role.Normal : n.Contains("rough") || n.Contains("metal") || n.Contains("occlusion") ? Role.Linear : Role.Color;
        }

        static Dictionary<string, Role> Roles(string gltfPath)
        {
            var key = gltfPath + File.GetLastWriteTimeUtc(gltfPath).Ticks;
            if (cache.TryGetValue(key, out var hit)) return hit;
            var roles = new Dictionary<string, Role>();
            try
            {
                var doc = JObject.Parse(File.ReadAllText(gltfPath));
                var images = (JArray)doc["images"] ?? new JArray(); var textures = (JArray)doc["textures"] ?? new JArray();
                string ImageFile(JToken texInfo)
                {
                    var ti = texInfo?["index"]?.Value<int?>(); if (ti == null || ti >= textures.Count) return null;
                    var src = textures[ti.Value]?["source"]?.Value<int?>(); if (src == null || src >= images.Count) return null;
                    var uri = images[src.Value]?["uri"]?.Value<string>(); return uri == null ? null : Path.GetFileName(System.Uri.UnescapeDataString(uri));
                }
                void Mark(JToken texInfo, Role r)
                {
                    var f = ImageFile(texInfo); if (f == null) return;
                    // a file used both as colour and data keeps the stricter (data) role
                    if (!roles.TryGetValue(f, out var prev) || r != Role.Color && prev == Role.Color) roles[f] = r;
                }
                foreach (var m in (JArray)doc["materials"] ?? new JArray())
                {
                    Mark(m["normalTexture"], Role.Normal);
                    Mark(m["occlusionTexture"], Role.Linear);
                    Mark(m["pbrMetallicRoughness"]?["metallicRoughnessTexture"], Role.Linear);
                    Mark(m["pbrMetallicRoughness"]?["baseColorTexture"], Role.Color);
                    Mark(m["emissiveTexture"], Role.Color);
                }
            }
            catch (System.Exception e) { Debug.LogWarning($"[FableBuild] could not read texture roles from {gltfPath}: {e.Message}"); }
            cache[key] = roles;
            return roles;
        }
    }
}
