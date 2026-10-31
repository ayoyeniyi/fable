// Spatial sound: every cue is a 3D AudioSource at a manifest anchor, inside a stone-hall reverb zone.
using System.Collections.Generic;
using UnityEngine;

namespace Fable
{
    public class SpatialAudio : MonoBehaviour
    {
        SceneRegistry reg;
        AudioSource ambience;
        readonly Queue<AudioSource> pool = new();

        public void Init(SceneRegistry r)
        {
            reg = r;
            var zone = reg.EnvironmentRoot.gameObject.GetComponent<AudioReverbZone>() ?? reg.EnvironmentRoot.gameObject.AddComponent<AudioReverbZone>();
            zone.reverbPreset = AudioReverbPreset.StoneCorridor; zone.minDistance = 8; zone.maxDistance = 30;
            for (int i = 0; i < 6; i++) pool.Enqueue(MakeSource("sfx" + i));
        }

        AudioSource MakeSource(string n)
        {
            var go = new GameObject(n); go.transform.SetParent(transform);
            var s = go.AddComponent<AudioSource>();
            s.spatialBlend = 1f; s.rolloffMode = AudioRolloffMode.Logarithmic; s.minDistance = 0.4f; s.maxDistance = 18f; s.dopplerLevel = 0; s.spatialize = true;
            return s;
        }

        public void PlayAmbience(string id, float volume = 0.6f)
        {
            var clip = reg.Clip(id); if (!clip) { Debug.LogWarning($"[Fable] missing ambience {id}"); return; }
            if (!ambience) { ambience = MakeSource("ambience"); ambience.loop = true; ambience.spatialBlend = 0.35f; }
            ambience.clip = clip; ambience.volume = volume; ambience.transform.position = reg.Anchor("hall.ceiling") ? reg.Anchor("hall.ceiling").position : Vector3.up * 2;
            ambience.Play();
        }

        public void StopAmbience() { if (ambience) ambience.Stop(); }

        public void Play(string id, string anchor, float volume)
        {
            var clip = reg.Clip(id); if (!clip) { Debug.LogWarning($"[Fable] missing sound {id}"); return; }
            var s = pool.Dequeue(); pool.Enqueue(s);
            var a = anchor != null ? reg.Anchor(anchor) : null;
            s.transform.position = a ? a.position : reg.EnvironmentRoot.position;
            s.volume = volume; s.pitch = Random.Range(0.97f, 1.03f); s.PlayOneShot(clip);
        }
    }
}
