// Fable living scenes: the wind every swaying and billowing material shares (docs/LIVING_SCENES.md).
// LivingScene.cs sets the globals once a frame; with no LivingScene (or Wind 0) nothing moves, so a still frame is
// exactly the baked, unanimated mesh.
#ifndef FABLE_WIND_INCLUDED
#define FABLE_WIND_INCLUDED

float4 _FableWind;        // xyz: world-space wind direction (horizontal, unit) times strength (0 calm, 1 a fresh breeze), w: gust 0..1
float  _FableWindTime;    // seconds; LivingScene advances it (so the editor's scene view stays still)

// Bend a vertex downwind. Amplitudes are in object units, which are metres at full scale; the environment is scaled
// as a whole (diorama, Alice's size changes), so working in object space keeps the motion in proportion.
//   weight: vertex colour R (0 at the root, 1 at the tip)  amp: metres at weight 1 in a strength-1 wind
//   flutter: share of quick sideways flutter (leaves) against slow bending (grass)
float3 FableSwayOS(float3 posOS, float weight, float amp, float flutter)
{
    float strength = length(_FableWind.xyz);
    if (strength < 1e-4 || weight <= 0) return posOS;
    float3 dirOS = mul((float3x3)GetWorldToObjectMatrix(), _FableWind.xyz / strength);
    dirOS.y = 0; float dl = length(dirOS); dirOS = dl > 1e-4 ? dirOS / dl : float3(1, 0, 0);
    float3 sideOS = float3(-dirOS.z, 0, dirOS.x);
    float t = _FableWindTime;
    float along = dot(posOS.xz, dirOS.xz), across = dot(posOS.xz, sideOS.xz);
    // a gust wave rolling downwind across the field (about 9 m long, 2.2 m/s), plus each plant's own slow swing
    float gust = 0.55 + 0.45 * sin(along * 0.7 - t * 2.2 + sin(across * 0.31) * 1.5);
    gust = lerp(1, gust, 0.6) * (0.75 + 0.5 * _FableWind.w);
    float phase = dot(posOS, float3(1.7, 0.9, 2.3));
    float swing = 0.65 + 0.35 * sin(t * 1.6 + phase);
    float bend = strength * gust * swing * (1 - flutter);
    float flick = strength * (0.6 + 0.4 * gust) * flutter * sin(t * 6.3 + phase * 3.1);
    float flickUp = strength * flutter * 0.35 * sin(t * 5.1 + phase * 2.3);
    float w = weight * amp;
    float3 o = dirOS * (bend * w) + sideOS * (flick * w * 0.6) + float3(0, flickUp * w * 0.5, 0);
    o.y -= bend * bend * w * w * 0.35;   // a bent stem is a little shorter: tips dip as they lean
    return posOS + o;
}

// Cloth: billow along the surface normal, fixed where weight is 0.
float3 FableBillowOS(float3 posOS, float3 normalOS, float weight, float amp)
{
    float strength = length(_FableWind.xyz);
    if (strength < 1e-4 || weight <= 0) return posOS;
    float t = _FableWindTime;
    float phase = dot(posOS, float3(1.3, 2.1, 0.7));
    float b = 0.6 + 0.4 * sin(t * 1.3 + phase) + 0.15 * sin(t * 3.7 + phase * 2.0);
    b *= strength * (0.7 + 0.6 * _FableWind.w);
    return posOS + normalOS * (b * weight * amp);
}

#endif
