// Fable/Water: moving water for Quest 2 (docs/LIVING_SCENES.md water.*). Opaque, one pass, no depth or opaque
// texture reads. The body colour is the room's own baked water texture lit by its lightmap and the sun, so the water
// keeps the room's look; on top: a swell of three summed Gerstner waves (ocean), two scrolling detail-normal layers
// (flowing along UV V for rivers, very slow for ponds), a sky reflection by Fresnel from the room's sky colours, a
// sun glint, foam from vertex colour G (shorelines) and on the swell's crests, and the scene's fog.
// Everything runs in object space, so the waves keep their proportion when the environment is scaled.
Shader "Fable/Water"
{
    Properties
    {
        [KeywordEnum(Ocean, River, Pond)] _Water ("Kind", Float) = 0
        _BaseMap ("Body colour (the room's water texture)", 2D) = "white" {}
        _BaseColor ("Body tint", Color) = (1,1,1,1)
        [NoScaleOffset][Normal] _DetailNormal ("Detail normals (tileable)", 2D) = "bump" {}
        [NoScaleOffset] _FoamNoise ("Foam noise (R)", 2D) = "gray" {}
        _DetailTiling ("Detail tiles per metre", Float) = 0.35
        _DetailStrength ("Detail normal strength", Range(0, 2)) = 0.6
        _DetailSpeed ("Detail drift (m/s)", Float) = 0.12
        _FlowSpeed ("River flow (m/s downstream)", Float) = 0.6
        _WaveHeight ("Swell height (m)", Float) = 0.35
        _WaveLength ("Swell wavelength (m)", Float) = 18
        _WaveSpeed ("Swell speed scale", Float) = 1
        _WaveDir ("Swell direction (object XZ)", Vector) = (1, 0, 0.3, 0)
        _SkyHorizon ("Sky at the horizon", Color) = (0.78, 0.84, 0.88, 1)
        _SkyZenith ("Sky overhead", Color) = (0.42, 0.58, 0.82, 1)
        _Reflectivity ("Reflection strength", Range(0, 1)) = 0.85
        _Glint ("Sun glint", Range(0, 4)) = 1.2
        _GlintPower ("Glint tightness", Float) = 180
        _FoamColor ("Foam", Color) = (0.92, 0.94, 0.95, 1)
        _CrestFoam ("Foam on crests", Range(0, 1)) = 0.35
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

        CBUFFER_START(UnityPerMaterial)
            float4 _BaseMap_ST;
            half4  _BaseColor;
            float  _DetailTiling;
            half   _DetailStrength;
            float  _DetailSpeed;
            float  _FlowSpeed;
            float  _WaveHeight;
            float  _WaveLength;
            float  _WaveSpeed;
            float4 _WaveDir;
            half4  _SkyHorizon;
            half4  _SkyZenith;
            half   _Reflectivity;
            half   _Glint;
            half   _GlintPower;
            half4  _FoamColor;
            half   _CrestFoam;
        CBUFFER_END
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
        TEXTURE2D(_DetailNormal); SAMPLER(sampler_DetailNormal);
        TEXTURE2D(_FoamNoise); SAMPLER(sampler_FoamNoise);
        float _FableWindTime;

        // Three Gerstner waves about the main direction. Returns the displaced position; n gets the analytic normal,
        // crest the normalised height (-1 trough .. 1 crest).
        float3 Swell(float3 p, out float3 n, out float crest)
        {
            n = float3(0, 1, 0); crest = 0;
#if defined(_WATER_OCEAN)
            float t = _FableWindTime * _WaveSpeed;
            float2 d0 = normalize(_WaveDir.xz + 1e-4);
            float2 dirs[3] = { d0, normalize(d0 + float2(-d0.y, d0.x) * 0.6), normalize(d0 - float2(-d0.y, d0.x) * 0.45) };
            float lens[3] = { 1.0, 0.61, 0.37 };
            float amps[3] = { 0.55, 0.3, 0.15 };
            float3 o = 0; float3 dn = 0; float h = 0;
            [unroll] for (int i = 0; i < 3; i++)
            {
                float L = _WaveLength * lens[i]; float k = 6.2831853 / L; float c = sqrt(9.81 / k);
                float A = _WaveHeight * 0.5 * amps[i]; float Q = 0.55 / (k * A * 3 + 1e-4);   // steepness, never looping
                Q = min(Q, 1);
                float f = k * (dot(dirs[i], p.xz) - c * t);
                float s, co; sincos(f, s, co);
                o.xz += dirs[i] * (Q * A * co);
                o.y += A * s;
                dn.xz += dirs[i] * (k * A * co);
                dn.y += Q * k * A * s;
                h += amps[i] * s;
            }
            n = normalize(float3(-dn.x, 1 - dn.y, -dn.z));
            crest = h / 1.0;
            return p + o;
#else
            return p;
#endif
        }
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Cull Back
            ZWrite On

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma shader_feature_local _WATER_OCEAN _WATER_RIVER _WATER_POND
            #pragma multi_compile _ LIGHTMAP_SHADOW_MIXING
            #pragma multi_compile _ SHADOWS_SHADOWMASK
            #pragma multi_compile _ LIGHTMAP_ON
            #pragma multi_compile _ USE_LEGACY_LIGHTMAPS
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
                float4 color      : COLOR;
                float2 uv         : TEXCOORD0;
                float2 lightmapUV : TEXCOORD1;
                float2 flow       : TEXCOORD3;   // river: unit downstream direction in object XZ (FableLiving computes it from V)
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float2 flow       : TEXCOORD5;
                float4 uv         : TEXCOORD0;   // xy body uv, zw object-space xz (detail and foam)
                float3 positionWS : TEXCOORD1;
                float3 normalWS   : TEXCOORD2;
                half4  extra      : TEXCOORD3;   // x fog, y foam (vertex colour G), z crest, w river v
                DECLARE_LIGHTMAP_OR_SH(lightmapUV, vertexSH, 4);
                float4 positionCS : SV_POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings Vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 nOS; float crest;
                float3 p = Swell(input.positionOS.xyz, nOS, crest);
#if !defined(_WATER_OCEAN)
                nOS = input.normalOS;
#endif
                VertexPositionInputs v = GetVertexPositionInputs(p);
                o.positionWS = v.positionWS;
                o.normalWS = TransformObjectToWorldNormal(nOS);
                o.uv = float4(TRANSFORM_TEX(input.uv, _BaseMap), input.positionOS.xz);
                o.extra = half4(ComputeFogFactor(v.positionCS.z), input.color.g, crest, 0);
                o.flow = dot(input.flow, input.flow) > 1e-4 ? normalize(input.flow) : normalize(_WaveDir.xz + 1e-4);
                OUTPUT_LIGHTMAP_UV(input.lightmapUV, unity_LightmapST, o.lightmapUV);
                OUTPUT_SH(o.normalWS, o.vertexSH);
                o.positionCS = v.positionCS;
                return o;
            }

            half3 SampleDetail(float2 uv)
            {
                return UnpackNormal(SAMPLE_TEXTURE2D(_DetailNormal, sampler_DetailNormal, uv));
            }

            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                float t = _FableWindTime;
                float2 xz = input.uv.zw * _DetailTiling;
                float2 uvA, uvB;
#if defined(_WATER_RIVER)
                // flow downstream (the mesh's V direction, worked out per vertex at import), two layers at different
                // rates so the surface never repeats
                float2 fd = input.flow.xy;
                uvA = xz - fd * (t * _FlowSpeed * _DetailTiling);
                uvB = xz * 1.7 + float2(0.37, 0.11) - fd * (t * _FlowSpeed * _DetailTiling * 1.55);
#elif defined(_WATER_POND)
                uvA = xz + float2(t, t * 0.6) * _DetailSpeed * 0.15;
                uvB = xz * 1.6 + float2(-t * 0.7, t) * _DetailSpeed * 0.12 + 0.5;
#else
                float2 wd = normalize(_WaveDir.xz + 1e-4);
                uvA = xz + wd * (t * _DetailSpeed);
                uvB = xz * 1.9 + float2(-wd.y, wd.x) * (t * _DetailSpeed * 0.8) + 0.31;
#endif
                half3 dA = SampleDetail(uvA), dB = SampleDetail(uvB);
                half2 slope = (dA.xy + dB.xy) * _DetailStrength;
                float3 n = normalize(input.normalWS);
                n = normalize(n + float3(slope.x, 0, slope.y));

                float3 v = GetWorldSpaceNormalizeViewDir(input.positionWS);
                half4 body = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv.xy) * _BaseColor;

                // light: the lightmap (or ambient probes) and the realtime sun with its baked shadow mask
                half3 gi = SAMPLE_GI(input.lightmapUV, input.vertexSH, float3(0, 1, 0));
                half4 mask = SAMPLE_SHADOWMASK(input.lightmapUV);
                Light sun = GetMainLight(float4(0, 0, 0, 0), input.positionWS, mask);
                half atten = sun.distanceAttenuation * sun.shadowAttenuation;
                half3 diffuse = body.rgb * (gi + sun.color * atten * saturate(dot(float3(0, 1, 0), sun.direction)));

                // sky by Fresnel (Schlick, water F0 0.02), brighter toward the horizon as on real water
                half ndv = saturate(dot(n, v));
                half fres = 0.02 + 0.98 * pow(1 - ndv, 5);
                float3 r = reflect(-v, n);
                half3 sky = lerp(_SkyHorizon.rgb, _SkyZenith.rgb, sqrt(saturate(r.y)));
                half3 c = lerp(diffuse, sky, saturate(fres * _Reflectivity));
                // the sun's glint (only where the baked mask says the sun reaches)
                float3 hv = normalize(sun.direction + v);
                c += sun.color * atten * pow(saturate(dot(n, hv)), _GlintPower) * _Glint;

                // foam: shore foam painted in vertex colour G, crest foam on the swell, broken up by noise
                half noise = SAMPLE_TEXTURE2D(_FoamNoise, sampler_FoamNoise, uvA * 0.7).r;
                half foam = saturate(input.extra.y * 1.4 - (1 - noise) * 0.8);
#if defined(_WATER_OCEAN)
                foam = max(foam, saturate((input.extra.z - 0.55) * 3) * _CrestFoam * smoothstep(0.45, 0.8, noise));
#endif
                c = lerp(c, _FoamColor.rgb * (gi + sun.color * atten * 0.8), foam);
                c = MixFog(c, input.extra.x);
                return half4(c, 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            ZWrite On ColorMask R
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma shader_feature_local _WATER_OCEAN _WATER_RIVER _WATER_POND
            #pragma multi_compile_instancing
            struct Attributes { float4 positionOS : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID UNITY_VERTEX_OUTPUT_STEREO };
            Varyings Vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input); UNITY_TRANSFER_INSTANCE_ID(input, o); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 n; float crest; o.positionCS = TransformObjectToHClip(Swell(input.positionOS.xyz, n, crest));
                return o;
            }
            half Frag(Varyings input) : SV_Target { UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input); return input.positionCS.z; }
            ENDHLSL
        }

        Pass
        {
            Name "Meta"
            Tags { "LightMode" = "Meta" }
            Cull Off
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma shader_feature EDITOR_VISUALIZATION
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/MetaInput.hlsl"
            struct Attributes { float4 positionOS : POSITION; float2 uv0 : TEXCOORD0; float2 uv1 : TEXCOORD1; float2 uv2 : TEXCOORD2; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0;
#ifdef EDITOR_VISUALIZATION
                float2 VizUV : TEXCOORD1; float4 LightCoord : TEXCOORD2;
#endif
            };
            Varyings Vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                o.positionCS = UnityMetaVertexPosition(input.positionOS.xyz, input.uv1, input.uv2);
                o.uv = TRANSFORM_TEX(input.uv0, _BaseMap);
#ifdef EDITOR_VISUALIZATION
                UnityEditorVizData(input.positionOS.xyz, input.uv0, input.uv1, input.uv2, o.VizUV, o.LightCoord);
#endif
                return o;
            }
            half4 Frag(Varyings input) : SV_Target
            {
                MetaInput m = (MetaInput)0;
                m.Albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv).rgb * _BaseColor.rgb;
#ifdef EDITOR_VISUALIZATION
                m.VizUV = input.VizUV; m.LightCoord = input.LightCoord;
#endif
                return UnityMetaFragment(m);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
