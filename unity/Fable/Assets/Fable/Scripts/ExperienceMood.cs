// A chapter experience's mood and haze, applied to the loaded room and undone on the way back to reading. The same
// table as blender/render_experience_thumb.py, so the tile's picture and the room agree. Baked light cannot change,
// so a mood works through what can: fog, the ambient term, and the realtime part of the room's lights.
using System.Collections.Generic;
using UnityEngine;

namespace Fable
{
    public static class ExperienceMood
    {
        // light scale, fog colour, ambient multiplier
        static readonly Dictionary<string, (float light, Color fog, float ambient)> Moods = new()
        {
            ["as-built"] = (1.00f, new Color(0.55f, 0.55f, 0.55f), 1.00f),
            ["dawn"] = (0.80f, new Color(0.75f, 0.62f, 0.58f), 0.85f),
            ["day"] = (1.15f, new Color(0.70f, 0.76f, 0.82f), 1.15f),
            ["dusk"] = (0.70f, new Color(0.55f, 0.38f, 0.30f), 0.70f),
            ["night"] = (0.45f, new Color(0.08f, 0.09f, 0.14f), 0.40f),
            ["storm"] = (0.60f, new Color(0.38f, 0.42f, 0.44f), 0.60f),
        };

        static bool applied; static bool fog; static float density; static Color fogColor, ambient, sky, equator, ground;
        static readonly Dictionary<Light, float> lights = new();
        public static string Current { get; private set; }

        public static void Apply(string mood, float haze)
        {
            Restore();
            if (!Moods.TryGetValue(mood ?? "as-built", out var m)) m = Moods["as-built"];
            fog = RenderSettings.fog; density = RenderSettings.fogDensity; fogColor = RenderSettings.fogColor;
            ambient = RenderSettings.ambientLight; sky = RenderSettings.ambientSkyColor; equator = RenderSettings.ambientEquatorColor; ground = RenderSettings.ambientGroundColor;
            lights.Clear();
            foreach (var l in Object.FindObjectsByType<Light>(FindObjectsSortMode.None)) { lights[l] = l.intensity; l.intensity *= m.light; }
            RenderSettings.ambientLight = ambient * m.ambient; RenderSettings.ambientSkyColor = sky * m.ambient; RenderSettings.ambientEquatorColor = equator * m.ambient; RenderSettings.ambientGroundColor = ground * m.ambient;
            if (haze > 0.01f) { RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Exponential; RenderSettings.fogDensity = Mathf.Max(density, 0.004f + 0.04f * haze); RenderSettings.fogColor = m.fog; }
            applied = true; Current = $"{mood} haze {haze:F2}";
            Debug.Log($"[Fable] experience mood: {Current}");
        }

        public static void Restore()
        {
            if (!applied) return;
            RenderSettings.fog = fog; RenderSettings.fogDensity = density; RenderSettings.fogColor = fogColor;
            RenderSettings.ambientLight = ambient; RenderSettings.ambientSkyColor = sky; RenderSettings.ambientEquatorColor = equator; RenderSettings.ambientGroundColor = ground;
            foreach (var kv in lights) if (kv.Key) kv.Key.intensity = kv.Value;
            lights.Clear(); applied = false; Current = null;
        }
    }
}
