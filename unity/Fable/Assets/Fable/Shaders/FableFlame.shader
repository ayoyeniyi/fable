// Fable/Flame: the rooms' own modelled flames (lamp, candle and hearth meshes), drawn unlit and made to flicker and
// lick. Vertex colour R is height within each flame (0 at the wick or embers, 1 at the tip) and G a per-flame random
// phase; FableLiving writes both at import (docs/LIVING_SCENES.md). Opaque, one pass, stereo instancing safe.
Shader "Fable/Flame"
{
    Properties
    {
        baseColorTexture ("Base colour", 2D) = "white" {}
        baseColorFactor ("Base colour factor", Color) = (1,1,1,1)
        emissiveTexture ("Emission", 2D) = "white" {}
        [HDR] emissiveFactor ("Emission factor", Color) = (1,0.7,0.35,1)
        _Lick ("Tip sway (m)", Float) = 0.01
        _Flicker ("Flicker depth", Range(0, 1)) = 0.25
        _Rate ("Flicker rate", Float) = 1
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }
        Pass
        {
            Name "Unlit"
            Tags { "LightMode" = "UniversalForward" }
            Cull [_Cull]
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 baseColorTexture_ST;
                half4 baseColorFactor;
                half4 emissiveFactor;
                float _Lick;
                half _Flicker;
                float _Rate;
            CBUFFER_END
            TEXTURE2D(baseColorTexture); SAMPLER(samplerbaseColorTexture);
            TEXTURE2D(emissiveTexture); SAMPLER(sampleremissiveTexture);

            struct Attributes { float4 positionOS : POSITION; float4 color : COLOR; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; half3 tint : TEXCOORD1; half fog : TEXCOORD2; UNITY_VERTEX_INPUT_INSTANCE_ID UNITY_VERTEX_OUTPUT_STEREO };

            // cheap layered flicker 0..1 (no texture reads)
            half Flicker(float t, float ph)
            {
                return saturate(0.5 + 0.22 * sin(t * 7.3 + ph) + 0.17 * sin(t * 13.1 + ph * 2.7) + 0.11 * sin(t * 23.7 + ph * 5.3));
            }

            Varyings Vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input); UNITY_TRANSFER_INSTANCE_ID(input, o); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float t = _Time.y * _Rate; float ph = input.color.g * 37.0; float w = input.color.r;
                float3 p = input.positionOS.xyz;
                float f = Flicker(t, ph);
                p.x += sin(t * 5.7 + ph) * _Lick * w * w;
                p.z += sin(t * 4.3 + ph * 1.9) * _Lick * w * w * 0.8;
                p.y += (f - 0.5) * _Lick * 1.5 * w;   // the tip stretches and drops with the flicker
                o.positionCS = TransformObjectToHClip(p);
                o.uv = TRANSFORM_TEX(input.uv, baseColorTexture);
                // flicker darkens and reddens a little toward the tip; never brighter than the baked look
                half b = 1 - _Flicker * (1 - f) * (0.5 + 0.5 * w);
                o.tint = half3(b, b * (1 - 0.15 * w * (1 - f)), b * (1 - 0.3 * w * (1 - f)));
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }
            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                half3 e = SAMPLE_TEXTURE2D(emissiveTexture, sampleremissiveTexture, input.uv).rgb * emissiveFactor.rgb;
                half3 a = SAMPLE_TEXTURE2D(baseColorTexture, samplerbaseColorTexture, input.uv).rgb * baseColorFactor.rgb;
                half3 c = saturate(e + a * 0.25) * input.tint;
                return half4(MixFog(c, input.fog), 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
