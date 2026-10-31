// The supported animation vocabulary. Every clip id in a manifest maps to a coroutine here; anything else
// fails validation before it reaches this class. Clips are small, physical and legible from arm's length.
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace Fable
{
    public class ClipPlayer : MonoBehaviour
    {
        SceneRegistry reg;
        readonly Dictionary<string, Coroutine> running = new();
        readonly Dictionary<string, float> baseIntensity = new();

        public void Init(SceneRegistry r) { reg = r; }

        static float Ease(float x) => x < 0.5f ? 4 * x * x * x : 1 - Mathf.Pow(-2 * x + 2, 3) / 2;

        public void Play(string target, string clip, float duration, bool loop)
        {
            var key = target + "|" + clip.Split('.')[0];
            if (running.TryGetValue(key, out var c) && c != null) StopCoroutine(c);
            IEnumerator routine = clip switch
            {
                "door.open" => Swing(target, -78f, duration),
                "door.close" => Swing(target, 0f, duration),
                "door.rattle" => Rattle(target, duration),
                "lamp.flicker" => Flicker(target, duration, loop),
                "lamp.steady" => Steady(target, duration),
                "curtain.draw" => Slide(target, new Vector3(-0.95f, 0, 0), duration),
                "curtain.sway" => Sway(target, duration, loop),
                "bottle.appear" => Pop(target, duration),
                "bottle.uncork" => Uncork(target, duration),
                "key.glint" => Glint(target, duration),
                "key.turn" => Spin(target, 90f, duration),
                _ => null
            };
            if (routine == null) { Debug.LogWarning($"[Fable] no implementation for clip {clip}"); return; }
            running[key] = StartCoroutine(routine);
        }

        public void StopAll() { foreach (var c in running.Values) if (c != null) StopCoroutine(c); running.Clear(); }

        IEnumerator Swing(string target, float yaw, float dur)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var from = t.localRotation; var to = Quaternion.Euler(0, yaw, 0);
            for (float e = 0; e < dur; e += Time.deltaTime) { t.localRotation = Quaternion.Slerp(from, to, Ease(e / dur)); yield return null; }
            t.localRotation = to;
        }

        IEnumerator Rattle(string target, float dur)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var rest = t.localRotation;
            for (float e = 0; e < dur; e += Time.deltaTime)
            {
                float a = Mathf.Sin(e * 38f) * 1.2f * (1 - e / dur);
                t.localRotation = rest * Quaternion.Euler(0, a, 0); yield return null;
            }
            t.localRotation = rest;
        }

        IEnumerator Flicker(string group, float dur, bool loop)
        {
            var lights = reg.Lights(group); if (lights == null) yield break;
            foreach (var l in lights) if (!baseIntensity.ContainsKey(l.name)) baseIntensity[l.name] = l.intensity;
            float e = 0;
            while (loop || e < dur)
            {
                e += Time.deltaTime;
                for (int i = 0; i < lights.Count; i++)
                {
                    float n = Mathf.PerlinNoise(Time.time * 7f, i * 3.1f) * 0.22f + Mathf.PerlinNoise(Time.time * 1.3f, i) * 0.1f;
                    lights[i].intensity = baseIntensity[lights[i].name] * (0.86f + n);
                }
                yield return null;
            }
        }

        IEnumerator Steady(string group, float dur)
        {
            var lights = reg.Lights(group); if (lights == null) yield break;
            var start = new List<float>(); foreach (var l in lights) start.Add(l.intensity);
            for (float e = 0; e < dur; e += Time.deltaTime)
            {
                for (int i = 0; i < lights.Count; i++) lights[i].intensity = Mathf.Lerp(start[i], baseIntensity.GetValueOrDefault(lights[i].name, start[i]), e / dur);
                yield return null;
            }
        }

        IEnumerator Slide(string target, Vector3 delta, float dur)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var from = t.localPosition; var to = from + delta;
            for (float e = 0; e < dur; e += Time.deltaTime) { t.localPosition = Vector3.Lerp(from, to, Ease(e / dur)); yield return null; }
            t.localPosition = to;
        }

        IEnumerator Sway(string target, float dur, bool loop)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var rest = t.localRotation; float e = 0;
            while (loop || e < dur) { e += Time.deltaTime; t.localRotation = rest * Quaternion.Euler(Mathf.Sin(e * 1.7f) * 0.8f, 0, 0); yield return null; }
            t.localRotation = rest;
        }

        IEnumerator Pop(string target, float dur)
        {
            var t = reg.Asset(target); if (!t) yield break;
            t.gameObject.SetActive(true);
            var s = t.localScale; dur = Mathf.Max(dur, 0.3f);
            for (float e = 0; e < dur; e += Time.deltaTime)
            {
                float x = e / dur; float k = 1 + 0.18f * Mathf.Sin(x * Mathf.PI * 3) * (1 - x);
                t.localScale = s * Mathf.Min(1, x * 3) * k; yield return null;
            }
            t.localScale = s;
        }

        IEnumerator Uncork(string target, float dur)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var cork = t.Find("Cork"); if (!cork) yield break;
            var from = cork.localPosition; var up = from + new Vector3(0, 0.05f, 0.02f);
            for (float e = 0; e < dur; e += Time.deltaTime)
            {
                float x = Ease(e / dur);
                cork.localPosition = Vector3.Lerp(from, up, x); cork.localRotation = Quaternion.Euler(x * 40f, 0, x * 25f);
                yield return null;
            }
        }

        IEnumerator Glint(string target, float dur)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var rends = t.GetComponentsInChildren<Renderer>();
            var block = new MaterialPropertyBlock();
            for (float e = 0; e < dur; e += Time.deltaTime)
            {
                float g = Mathf.Pow(Mathf.Max(0, Mathf.Sin(e / dur * Mathf.PI * 2f)), 6) * 2.2f;
                block.SetColor("_EmissionColor", new Color(1f, 0.82f, 0.45f) * g);
                foreach (var r in rends) r.SetPropertyBlock(block);
                yield return null;
            }
            block.SetColor("_EmissionColor", Color.black); foreach (var r in rends) r.SetPropertyBlock(block);
        }

        IEnumerator Spin(string target, float deg, float dur)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var from = t.localRotation; var to = from * Quaternion.Euler(deg, 0, 0);
            for (float e = 0; e < dur; e += Time.deltaTime) { t.localRotation = Quaternion.Slerp(from, to, Ease(e / dur)); yield return null; }
            t.localRotation = to;
        }
    }
}
