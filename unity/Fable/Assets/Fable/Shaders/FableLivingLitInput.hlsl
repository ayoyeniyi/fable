// Material inputs for Fable/LivingLit, named as glTFast names them (baseColorTexture, metallicRoughnessTexture ...)
// so a glTF material is converted by swapping its shader: every texture and factor carries over.
#ifndef FABLE_LIVING_LIT_INPUT_INCLUDED
#define FABLE_LIVING_LIT_INPUT_INCLUDED

#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/SurfaceInput.hlsl"

CBUFFER_START(UnityPerMaterial)
    float4 baseColorTexture_ST;
    half4  baseColorFactor;
    half   metallicFactor;
    half   roughnessFactor;
    half   normalTexture_scale;
    half   occlusionTexture_strength;
    half4  emissiveFactor;
    half   alphaCutoff;
    half   _SwayAmplitude;     // metres at weight 1 in a strength-1 wind
    half   _SwayFlutter;       // 0 slow bending (grass) .. 1 quick flutter (leaves)
    half   _Billow;            // metres of cloth billow at weight 1 (0 for foliage)
CBUFFER_END

TEXTURE2D(baseColorTexture);          SAMPLER(samplerbaseColorTexture);
TEXTURE2D(metallicRoughnessTexture);  SAMPLER(samplermetallicRoughnessTexture);
TEXTURE2D(normalTexture);             SAMPLER(samplernormalTexture);
TEXTURE2D(occlusionTexture);          SAMPLER(samplerocclusionTexture);
TEXTURE2D(emissiveTexture);           SAMPLER(sampleremissiveTexture);

// glTF packs roughness in G and metalness in B; URP wants metallic and smoothness.
void FableInitSurface(float2 uv, out SurfaceData s)
{
    s = (SurfaceData)0;
    half4 albedo = SAMPLE_TEXTURE2D(baseColorTexture, samplerbaseColorTexture, uv) * baseColorFactor;
    s.alpha = albedo.a;
#if defined(_ALPHATEST_ON)
    clip(s.alpha - alphaCutoff);
#endif
    s.albedo = albedo.rgb;
    half4 mr = SAMPLE_TEXTURE2D(metallicRoughnessTexture, samplermetallicRoughnessTexture, uv);
    s.metallic = mr.b * metallicFactor;
    s.smoothness = 1 - mr.g * roughnessFactor;
    s.specular = half3(0, 0, 0);
    s.normalTS = UnpackNormalScale(SAMPLE_TEXTURE2D(normalTexture, samplernormalTexture, uv), normalTexture_scale);
#if defined(_OCCLUSION)
    s.occlusion = lerp(1, SAMPLE_TEXTURE2D(occlusionTexture, samplerocclusionTexture, uv).r, occlusionTexture_strength);
#else
    s.occlusion = 1;
#endif
#if defined(_EMISSIVE)
    s.emission = SAMPLE_TEXTURE2D(emissiveTexture, sampleremissiveTexture, uv).rgb * emissiveFactor.rgb;
#else
    s.emission = 0;
#endif
}

#endif
