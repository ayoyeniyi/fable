// The realtime light of one fire, candle or lantern (docs/LIVING_SCENES.md fx.*): it flickers on top of the room's
// baked light, so its intensity stays low (the hearth's steady light is already in the lightmap). Its range follows
// the environment's scale (the diorama and Alice's size changes). No allocation per frame.
using UnityEngine;

namespace Fable
{
    [RequireComponent(typeof(Light))]
    public class FireFlicker : MonoBehaviour
    {
        public float Intensity = 0.5f, Depth = 0.6f, Rate = 1f, Range = 3f;
        Light lamp; float seed;

        void Awake() { lamp = GetComponent<Light>(); seed = Random.value * 100f; }

        void Update()
        {
            float t = Time.time * Rate + seed;
            // layered noise: a slow breathing, a quicker flutter and the odd sharp dip as a log shifts
            float n = 0.55f * Mathf.PerlinNoise(t * 1.7f, 0.3f) + 0.3f * Mathf.PerlinNoise(t * 6.1f, 1.7f) + 0.15f * Mathf.PerlinNoise(t * 13f, 4.1f);
            lamp.intensity = Intensity * (1f - Depth + Depth * 1.6f * n);
            lamp.range = Range * transform.lossyScale.x;
        }
    }
}
