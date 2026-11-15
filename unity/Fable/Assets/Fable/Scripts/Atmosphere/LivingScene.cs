// A hand-built room's living parts at runtime (docs/LIVING_SCENES.md): the scene's one wind (direction, strength and
// slow gusts) for every swaying and billowing material, the clock the water and wind shaders run on, and the volume
// of the room's positional sounds (fire crackle, sound.* sources), which follow the reader's ambience setting.
// FableLiving (editor) builds and wires everything when the scene is built; this only animates it. No allocation per frame.
using UnityEngine;

namespace Fable
{
    public class LivingScene : MonoBehaviour
    {
        [Tooltip("compass degrees the wind blows toward, in world XZ (0 = +Z, 90 = +X)")] public float WindToward = 60f;
        [Tooltip("0 calm, 0.35 a gentle breeze, 1 a fresh wind, 2 a gale")] public float WindStrength = 0.35f;
        [Tooltip("how much the strength rises and falls in gusts (0..1)")] public float Gustiness = 0.5f;
        public AudioSource[] Sources = new AudioSource[0];
        public float[] SourceVolumes = new float[0];

        static readonly int WindId = Shader.PropertyToID("_FableWind"), TimeId = Shader.PropertyToID("_FableWindTime");
        float clock;

        public string Describe() => $"living: wind {WindStrength:F2} toward {WindToward:F0}°, {Sources.Length} positional sounds";

        void OnEnable()
        {
            RoomSound.SettingsChanged += ApplyVolumes;
            ApplyVolumes();
            for (int i = 0; i < Sources.Length; i++)
                if (Sources[i] && Sources[i].clip) { Sources[i].time = Random.Range(0f, Sources[i].clip.length * 0.9f); Sources[i].Play(); }
        }

        void OnDisable()
        {
            RoomSound.SettingsChanged -= ApplyVolumes;
            Shader.SetGlobalVector(WindId, Vector4.zero);
        }

        void ApplyVolumes()
        {
            float k = RoomSound.AmbienceFactor;
            for (int i = 0; i < Sources.Length; i++)
                if (Sources[i]) Sources[i].volume = (i < SourceVolumes.Length ? SourceVolumes[i] : 0.5f) * k;
        }

        void Update()
        {
            clock += Time.deltaTime;
            // gusts: two slow incommensurate swells, so the field breathes rather than pulses
            float g = 0.5f + 0.3f * Mathf.Sin(clock * 0.23f) + 0.2f * Mathf.Sin(clock * 0.61f + 1.3f);
            float s = WindStrength * (1f - Gustiness * 0.5f + Gustiness * g);
            float a = WindToward * Mathf.Deg2Rad;
            Shader.SetGlobalVector(WindId, new Vector4(Mathf.Sin(a) * s, 0f, Mathf.Cos(a) * s, g));
            Shader.SetGlobalFloat(TimeId, clock);
        }
    }
}
