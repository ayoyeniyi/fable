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
        /// The reader's sound settings changed (BookMenu's sound card): every room sound applies them at once.
        public static event System.Action SettingsChanged;
        public static void NotifySettings() => SettingsChanged?.Invoke();
        float AmbTarget => AmbienceVolume * new[] { 0f, 0.45f, 1f }[Mathf.Clamp(ProgressStore.LoadPrefs().AmbienceLevel, 0, 2)];
        float MusicTarget => ProgressStore.LoadPrefs().MusicOn ? MusicVolume : 0f;
        void OnEnable() { SettingsChanged += Apply; }
        void OnDisable() { SettingsChanged -= Apply; }
        void Apply() { if (amb) amb.volume = AmbTarget; if (music) music.volume = MusicTarget; }

        public bool HasMusic => music && music.clip;
        public string Describe() => $"sound {Id}: ambience={(amb && amb.isPlaying ? amb.clip.name : "-")} music={(music && music.isPlaying ? music.clip.name : "-")}";

        IEnumerator Start()
        {
            amb = Loop("amb." + Id); music = Loop("music." + Id);
            float at = AmbTarget, mt = MusicTarget;
            for (float t = 0; t < FadeSeconds; t += Time.deltaTime)
            {
                float e = t / FadeSeconds;
                if (amb) amb.volume = at * e;
                if (music) music.volume = mt * e;
                yield return null;
            }
            Apply();
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
