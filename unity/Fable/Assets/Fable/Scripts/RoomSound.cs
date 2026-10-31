// A room's sound bed: its ambience loop (Resources/Audio/amb.<id>) and, where it has one, its music (music.<id>), both
// non-spatial and faded in. The ambience clips are synthesised (audio/synth_rooms.py); the music tracks are CC0 /
// public-domain recordings (tools/fetch_music.py, credited in CREDITS.md) or composed in audio/synth_rooms.py.
using System.Collections;
using UnityEngine;

namespace Fable
{
    public class RoomSound : MonoBehaviour
    {
        public string Id;
        public float AmbienceVolume = 0.5f, MusicVolume = 0.22f, FadeSeconds = 3f;
        AudioSource amb, music;

        public bool HasMusic => music && music.clip;
        public string Describe() => $"sound {Id}: ambience={(amb && amb.isPlaying ? amb.clip.name : "-")} music={(music && music.isPlaying ? music.clip.name : "-")}";

        IEnumerator Start()
        {
            amb = Loop("amb." + Id); music = Loop("music." + Id);
            for (float t = 0; t < FadeSeconds; t += Time.deltaTime)
            {
                float e = t / FadeSeconds;
                if (amb) amb.volume = AmbienceVolume * e;
                if (music) music.volume = MusicVolume * e;
                yield return null;
            }
            if (amb) amb.volume = AmbienceVolume;
            if (music) music.volume = MusicVolume;
        }

        AudioSource Loop(string clipName)
        {
            var clip = Resources.Load<AudioClip>("Audio/" + clipName);
            if (!clip) return null;
            var s = gameObject.AddComponent<AudioSource>();
            s.clip = clip; s.loop = true; s.spatialBlend = 0f; s.volume = 0f; s.playOnAwake = false; s.dopplerLevel = 0;
            s.Play();
            Debug.Log($"[Fable] sound: {clipName} ({clip.length:F0} s loop)");
            return s;
        }
    }
}
