// A room's sound bed: its ambience layers and, where it has one, its music (music.<Id>), all non-spatial and faded in.
// Ambience is a mix of real field recordings from the sound library (Resources/Audio/amb.<kind>, sources and licences
// in audio/SOURCES.md), written "surf:0.8+gulls:0.3" (kind, optional relative volume). The room's positional sounds
// (fire, sound.* sources) live in LivingScene and follow the same ambience setting. Music tracks are CC0 /
// public-domain recordings (tools/fetch_music.py, credited in CREDITS.md) or composed in audio/synth_rooms.py.
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace Fable
{
    public class RoomSound : MonoBehaviour
    {
        [Tooltip("music.<Id> is played if it exists")] public string Id;
        [Tooltip("ambience layers: kind[:volume]+kind[:volume], each Resources/Audio/amb.<kind>")] public string Ambience;
        public float AmbienceVolume = 0.5f, MusicVolume = 0.22f, FadeSeconds = 3f;
        readonly List<AudioSource> beds = new(); readonly List<float> bedLevels = new();
        AudioSource music;
        /// The reader's sound settings changed (BookMenu's sound card): every room sound applies them at once.
        public static event System.Action SettingsChanged;
        public static void NotifySettings() => SettingsChanged?.Invoke();
        /// The reader's ambience level as a gain (off, low, full), shared with LivingScene's positional sounds.
        public static float AmbienceFactor => new[] { 0f, 0.45f, 1f }[Mathf.Clamp(ProgressStore.LoadPrefs().AmbienceLevel, 0, 2)];
        float AmbTarget => AmbienceVolume * AmbienceFactor;
        float MusicTarget => ProgressStore.LoadPrefs().MusicOn ? MusicVolume : 0f;
        void OnEnable() { SettingsChanged += Apply; }
        void OnDisable() { SettingsChanged -= Apply; }
        void Apply() { SetBeds(AmbTarget); if (music) music.volume = MusicTarget; }
        void SetBeds(float v) { for (int i = 0; i < beds.Count; i++) beds[i].volume = v * bedLevels[i]; }

        public bool HasMusic => music && music.clip;
        public string Describe()
        {
            var names = new List<string>(); foreach (var b in beds) if (b.isPlaying) names.Add(b.clip.name);
            return $"sound {Id}: ambience={(names.Count > 0 ? string.Join("+", names) : "-")} music={(music && music.isPlaying ? music.clip.name : "-")}";
        }

        IEnumerator Start()
        {
            foreach (var layer in (Ambience ?? "").Split('+'))
            {
                var parts = layer.Trim().Split(':'); if (parts[0].Length == 0) continue;
                float level = parts.Length > 1 && float.TryParse(parts[1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var l) ? l : 1f;
                var s = Loop("amb." + parts[0]); if (!s) continue;
                s.time = Random.Range(0f, s.clip.length * 0.9f);   // layers never line up the same way twice
                beds.Add(s); bedLevels.Add(level);
            }
            if (!string.IsNullOrEmpty(Id)) music = Loop("music." + Id);
            float at = AmbTarget, mt = MusicTarget;
            for (float t = 0; t < FadeSeconds; t += Time.deltaTime)
            {
                float e = t / FadeSeconds;
                SetBeds(at * e);
                if (music) music.volume = mt * e;
                yield return null;
            }
            Apply();
        }

        AudioSource Loop(string clipName)
        {
            var clip = Resources.Load<AudioClip>("Audio/" + clipName);
            if (!clip) { if (clipName.StartsWith("amb.")) Debug.LogWarning($"[Fable] sound: no {clipName} in Resources/Audio"); return null; }
            var s = gameObject.AddComponent<AudioSource>();
            s.clip = clip; s.loop = true; s.spatialBlend = 0f; s.volume = 0f; s.playOnAwake = false; s.dopplerLevel = 0;
            s.Play();
            Debug.Log($"[Fable] sound: {clipName} ({clip.length:F0} s loop)");
            return s;
        }
    }
}
