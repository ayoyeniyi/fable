// Desktop previews of the map Peek from the play-mode camera (docs/MAPS_HEADSET.md). Editor only: renders Camera.main
// (no HMD, so this is the desktop view, not what the headset shows) into captures/unity/maps/desktop-preview_<name>.png.
using System.IO;
using UnityEngine;

namespace Fable.Editor
{
    public static class MapPreview
    {
        /// Optional: look from `from` toward `at` for this shot (the camera is put back afterwards).
        public static string Capture(string name, Vector3? from = null, Vector3? at = null, int width = 1600, int height = 1000)
        {
            var cam = Camera.main; if (!cam) return "no camera";
            var dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..", "captures", "unity", "maps"));
            Directory.CreateDirectory(dir);
            var t = cam.transform; var p0 = t.position; var r0 = t.rotation; var tt0 = cam.targetTexture;
            if (from.HasValue) { t.position = from.Value; if (at.HasValue) t.LookAt(at.Value); }
            var rt = RenderTexture.GetTemporary(width, height, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB, 4);
            cam.targetTexture = rt; cam.Render(); cam.targetTexture = tt0;
            var tex = new Texture2D(width, height, TextureFormat.RGB24, false);
            var prev = RenderTexture.active; RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, width, height), 0, 0); tex.Apply(); RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);
            var path = Path.Combine(dir, $"desktop-preview_{name}.png");
            File.WriteAllBytes(path, tex.EncodeToPNG()); Object.DestroyImmediate(tex);
            t.position = p0; t.rotation = r0;
            return path;
        }
    }
}
