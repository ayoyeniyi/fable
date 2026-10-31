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
                // A Mad Tea-Party: seated figures gesture about their own pivot (they are sculpted props, not rigs)
                "hatter.look" => Turn(target, new Vector3(0, 22f, 0), duration, hold: true),
                "hatter.eyes-wide" => Swell(target, 1.07f, duration),
                "hatter.speak" or "hare.speak" or "card.speak" => Nod(target, duration, loop, 3.5f, 6f),
                "hare.offer" => Turn(target, new Vector3(9f, 0, 0), duration, hold: false),
                "hare.elbow" => Rattle(target, duration),
                "dormouse.breathe" => Breathe(target, duration, loop),
                "dormouse.twitch" => Rattle(target, duration * 0.5f),
                "armchair.sit" => Dip(target, 0.025f, duration),
                "tea.rattle" => Rattle(target, duration),
                "tea.pour" => Turn(target, new Vector3(0, 0, 18f), duration, hold: false),
                "dapple.sway" => Sway(target, duration, loop),
                // The Queen's Croquet-Ground: the card gardeners
                "card.paint" => Nod(target, duration, loop, 4f, 2.2f),
                "card.look-up" => Turn(target, new Vector3(-10f, 0, 0), duration, hold: true),
                "card.bow" => Turn(target, new Vector3(38f, 0, 0), duration, hold: true),
                "card.sulk" => Turn(target, new Vector3(0, -24f, 0), duration, hold: true),
                "card.fling-brush" => Turn(target, new Vector3(0, 0, -14f), Mathf.Min(duration, 0.6f), hold: false),
                "roses.redden" => Redden(target, duration),
                "roses.rustle" => Sway(target, duration, loop),
                _ => null
            };
            if (routine == null) { Debug.LogWarning($"[Fable] no implementation for clip {clip}"); return; }
            running[key] = StartCoroutine(routine);
        }

        public void StopAll()
        {
            foreach (var c in running.Values) if (c != null) StopCoroutine(c);
            running.Clear();
            foreach (var r in tinted) if (r) r.SetPropertyBlock(null);   // reset is total: replay re-applies tints
            tinted.Clear();
        }

        readonly List<Renderer> tinted = new();

        /// Rotate by an offset about the asset's pivot. hold = stay there (replays land on the end pose); otherwise go and come back.
        IEnumerator Turn(string target, Vector3 euler, float dur, bool hold)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var rest = t.localRotation; var to = rest * Quaternion.Euler(euler);
            for (float e = 0; e < dur; e += Time.deltaTime)
            {
                float x = e / dur; float w = hold ? Ease(x) : Mathf.Sin(Mathf.PI * Mathf.Clamp01(x));
                t.localRotation = Quaternion.Slerp(rest, to, w); yield return null;
            }
            t.localRotation = hold ? to : rest;
        }

        IEnumerator Nod(string target, float dur, bool loop, float degrees, float hz)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var rest = t.localRotation; float e = 0;
            while (loop || e < dur)
            {
                e += Time.deltaTime; float fade = loop ? 1 : Mathf.Sin(Mathf.PI * Mathf.Clamp01(e / dur));
                t.localRotation = rest * Quaternion.Euler(Mathf.Sin(e * hz * Mathf.PI * 2) * degrees * fade, 0, 0); yield return null;
            }
            t.localRotation = rest;
        }

        IEnumerator Swell(string target, float k, float dur)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var s = t.localScale;
            for (float e = 0; e < dur; e += Time.deltaTime) { t.localScale = s * (1 + (k - 1) * Mathf.Sin(Mathf.PI * e / dur)); yield return null; }
            t.localScale = s;
        }

        IEnumerator Breathe(string target, float dur, bool loop)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var s = t.localScale; float e = 0;
            while (loop || e < dur) { e += Time.deltaTime; t.localScale = Vector3.Scale(s, new Vector3(1, 1 + 0.035f * Mathf.Sin(e * 2.4f), 1)); yield return null; }
            t.localScale = s;
        }

        IEnumerator Dip(string target, float depth, float dur)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var p = t.localPosition;
            for (float e = 0; e < dur; e += Time.deltaTime) { t.localPosition = p + Vector3.down * depth * Mathf.Sin(Mathf.PI * e / dur); yield return null; }
            t.localPosition = p;
        }

        /// White roses painted red: tint the blossom renderers (material or mesh named like a rose/bloom), never the leaves.
        IEnumerator Redden(string target, float dur)
        {
            var t = reg.Asset(target); if (!t) yield break;
            var rends = new List<Renderer>();
            foreach (var r in t.GetComponentsInChildren<Renderer>())
            {
                var n = (r.name + " " + (r.sharedMaterial ? r.sharedMaterial.name : "")).ToLowerInvariant();
                if ((n.Contains("rose") || n.Contains("bloom") || n.Contains("petal") || n.Contains("flower")) && !n.Contains("leaf") && !n.Contains("stem") && !n.Contains("trunk")) rends.Add(r);
            }
            if (rends.Count == 0 && t.name.StartsWith("fx.")) rends.AddRange(t.GetComponentsInChildren<Renderer>());
            tinted.AddRange(rends);
            var block = new MaterialPropertyBlock(); var red = new Color(0.78f, 0.06f, 0.08f);
            for (float e = 0; e <= dur; e += Time.deltaTime)
            {
                block.SetColor("_BaseColor", Color.Lerp(Color.white, red, Ease(Mathf.Clamp01(e / Mathf.Max(dur, 0.01f)))));
                foreach (var r in rends) if (r) r.SetPropertyBlock(block);
                yield return null;
            }
            block.SetColor("_BaseColor", red); foreach (var r in rends) if (r) r.SetPropertyBlock(block);
        }

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
