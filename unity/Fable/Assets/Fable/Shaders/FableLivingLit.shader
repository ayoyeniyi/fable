// Fable/LivingLit: URP PBR for glTF materials (same inputs as glTFast's pbrMetallicRoughness graph) whose vertices
// move in the scene's wind: foliage sways (veg.*), cloth billows (cloth.*). Vertex colour R is the weight (0 fixed,
// 1 free); it is never used as a tint. The surface is lit exactly like URP Lit: baked lightmap + shadowmask, the
// realtime main light, additional lights, reflection probe and fog. With no wind the mesh is not displaced at all.
// Single-pass instanced stereo safe; one forward pass, a depth pass and the lightmapper's Meta pass.
Shader "Fable/LivingLit"
{
    Properties
    {
        baseColorTexture ("Base colour", 2D) = "white" {}
        baseColorFactor ("Base colour factor", Color) = (1,1,1,1)
        metallicRoughnessTexture ("Metallic (B) roughness (G)", 2D) = "white" {}
        metallicFactor ("Metallic", Range(0,1)) = 0
        roughnessFactor ("Roughness", Range(0,1)) = 1
        [Normal] normalTexture ("Normal", 2D) = "bump" {}
        normalTexture_scale ("Normal scale", Float) = 1
        occlusionTexture ("Occlusion (R)", 2D) = "white" {}
        occlusionTexture_strength ("Occlusion strength", Range(0,1)) = 1
        emissiveTexture ("Emission", 2D) = "white" {}
        [HDR] emissiveFactor ("Emission factor", Color) = (0,0,0,0)
        alphaCutoff ("Alpha cutoff", Range(0,1)) = 0.5
        _SwayAmplitude ("Sway amplitude (m at weight 1)", Float) = 0.1
        _SwayFlutter ("Sway flutter (0 bend .. 1 flutter)", Range(0,1)) = 0.2
        _Billow ("Cloth billow (m at weight 1)", Float) = 0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }

        HLSLINCLUDE
        #pragma shader_feature_local _ALPHATEST_ON
        #pragma shader_feature_local _OCCLUSION
        #pragma shader_feature_local _EMISSIVE
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Cull [_Cull]
            ZWrite On

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag

            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile _ EVALUATE_SH_MIXED EVALUATE_SH_VERTEX
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BLENDING
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BOX_PROJECTION
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile _ _LIGHT_LAYERS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile _ LIGHTMAP_SHADOW_MIXING
            #pragma multi_compile _ SHADOWS_SHADOWMASK
            #pragma multi_compile _ DIRLIGHTMAP_COMBINED
            #pragma multi_compile _ LIGHTMAP_ON
            #pragma multi_compile_fragment _ LIGHTMAP_BICUBIC_SAMPLING
            #pragma multi_compile _ USE_LEGACY_LIGHTMAPS
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ProbeVolumeVariants.hlsl"
            #pragma multi_compile_instancing
            // foliage: diffuse only (baked light + the main light), no normal map, specular or per-pixel extra lights.
            // Cut-out cards are drawn many layers deep, so each layer must be cheap on Quest 2.
            #pragma shader_feature_local_fragment _FABLE_SIMPLE

            #include "FableLivingLitInput.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "FableWind.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
                float4 tangentOS  : TANGENT;
                float4 color      : COLOR;
                float2 uv         : TEXCOORD0;
                float2 lightmapUV : TEXCOORD1;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float2 uv          : TEXCOORD0;
                float3 positionWS  : TEXCOORD1;
                float3 normalWS    : TEXCOORD2;
                half4  tangentWS   : TEXCOORD3;
                half4  fogAndLight : TEXCOORD4;   // x fog, yzw vertex light
                DECLARE_LIGHTMAP_OR_SH(lightmapUV, vertexSH, 5);
#ifdef USE_APV_PROBE_OCCLUSION
                float4 probeOcclusion : TEXCOORD6;
#endif
                float4 positionCS  : SV_POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings Vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

                float3 p = input.positionOS.xyz;
                if (_Billow > 0) p = FableBillowOS(p, input.normalOS, input.color.r, _Billow);
                else p = FableSwayOS(p, input.color.r, _SwayAmplitude, _SwayFlutter);

                VertexPositionInputs v = GetVertexPositionInputs(p);
                VertexNormalInputs n = GetVertexNormalInputs(input.normalOS, input.tangentOS);
                o.uv = TRANSFORM_TEX(input.uv, baseColorTexture);
                o.positionWS = v.positionWS;
                o.normalWS = n.normalWS;
                o.tangentWS = half4(n.tangentWS, input.tangentOS.w * GetOddNegativeScale());
                half fog = ComputeFogFactor(v.positionCS.z);
                o.fogAndLight = half4(fog, VertexLighting(v.positionWS, n.normalWS));
                OUTPUT_LIGHTMAP_UV(input.lightmapUV, unity_LightmapST, o.lightmapUV);
                OUTPUT_SH4(v.positionWS, o.normalWS, GetWorldSpaceNormalizeViewDir(v.positionWS), o.vertexSH, o.probeOcclusion);
                o.positionCS = v.positionCS;
                return o;
            }

            half4 Frag(Varyings input, FRONT_FACE_TYPE facing : FRONT_FACE_SEMANTIC) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);

#if defined(_FABLE_SIMPLE)
                half4 alb = SAMPLE_TEXTURE2D(baseColorTexture, samplerbaseColorTexture, input.uv) * baseColorFactor;
    #if defined(_ALPHATEST_ON)
                clip(alb.a - alphaCutoff);
    #endif
                float3 nS = normalize(input.normalWS * IS_FRONT_VFACE(facing, 1.0, -1.0));
                float4 scS = float4(0, 0, 0, 0);
    #if defined(MAIN_LIGHT_CALCULATE_SHADOWS)
                scS = TransformWorldToShadowCoord(input.positionWS);
    #endif
                half3 giS = SAMPLE_GI(input.lightmapUV, input.vertexSH, nS);
                half4 smS = SAMPLE_SHADOWMASK(input.lightmapUV);
                Light mlS = GetMainLight(scS, input.positionWS, smS);
                half ndl = saturate(dot(nS, mlS.direction) * 0.75 + 0.25);   // a little wrap: thin leaves pass light through
                half3 colS = alb.rgb * (giS + mlS.color * (mlS.distanceAttenuation * mlS.shadowAttenuation * ndl) + input.fogAndLight.yzw);
                colS = MixFog(colS, InitializeInputDataFog(float4(input.positionWS, 1.0), input.fogAndLight.x));
                return half4(colS, 1);
#endif
                SurfaceData s;
                FableInitSurface(input.uv, s);

                InputData d = (InputData)0;
                d.positionWS = input.positionWS;
                float3 nWS = input.normalWS * IS_FRONT_VFACE(facing, 1.0, -1.0);   // double-sided leaves and petals light their back face
                float sgn = input.tangentWS.w;
                float3 bitangent = sgn * cross(nWS, input.tangentWS.xyz);
                half3x3 tbn = half3x3(input.tangentWS.xyz, bitangent, nWS);
                d.tangentToWorld = tbn;
                d.normalWS = NormalizeNormalPerPixel(TransformTangentToWorld(s.normalTS, tbn));
                d.viewDirectionWS = GetWorldSpaceNormalizeViewDir(input.positionWS);
#if defined(MAIN_LIGHT_CALCULATE_SHADOWS)
                d.shadowCoord = TransformWorldToShadowCoord(input.positionWS);
#endif
                d.fogCoord = InitializeInputDataFog(float4(input.positionWS, 1.0), input.fogAndLight.x);
                d.vertexLighting = input.fogAndLight.yzw;
                d.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(input.positionCS);
#if !defined(LIGHTMAP_ON) && (defined(PROBE_VOLUMES_L1) || defined(PROBE_VOLUMES_L2))
                d.bakedGI = SAMPLE_GI(input.vertexSH, GetAbsolutePositionWS(d.positionWS), d.normalWS, d.viewDirectionWS, input.positionCS.xy, input.probeOcclusion, d.shadowMask);
#else
                d.bakedGI = SAMPLE_GI(input.lightmapUV, input.vertexSH, d.normalWS);
                d.shadowMask = SAMPLE_SHADOWMASK(input.lightmapUV);
#endif
                half4 c = UniversalFragmentPBR(d, s);
                c.rgb = MixFog(c.rgb, d.fogCoord);
                c.a = 1;
                return c;
            }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            ZWrite On ColorMask R
            Cull [_Cull]

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #include "FableLivingLitInput.hlsl"
            #include "FableWind.hlsl"

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float4 color : COLOR; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID UNITY_VERTEX_OUTPUT_STEREO };

            Varyings Vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 p = input.positionOS.xyz;
                if (_Billow > 0) p = FableBillowOS(p, input.normalOS, input.color.r, _Billow);
                else p = FableSwayOS(p, input.color.r, _SwayAmplitude, _SwayFlutter);
                o.positionCS = TransformObjectToHClip(p);
                o.uv = TRANSFORM_TEX(input.uv, baseColorTexture);
                return o;
            }
            half Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
#if defined(_ALPHATEST_ON)
                clip(SAMPLE_TEXTURE2D(baseColorTexture, samplerbaseColorTexture, input.uv).a * baseColorFactor.a - alphaCutoff);
#endif
                return input.positionCS.z;
            }
            ENDHLSL
        }

        // the lightmapper's albedo and emission: the rest pose (bakes see the undisplaced mesh)
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
            #include "FableLivingLitInput.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/BRDF.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/MetaInput.hlsl"

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv0 : TEXCOORD0; float2 uv1 : TEXCOORD1; float2 uv2 : TEXCOORD2; };
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
                o.uv = TRANSFORM_TEX(input.uv0, baseColorTexture);
#ifdef EDITOR_VISUALIZATION
                UnityEditorVizData(input.positionOS.xyz, input.uv0, input.uv1, input.uv2, o.VizUV, o.LightCoord);
#endif
                return o;
            }
            half4 Frag(Varyings input) : SV_Target
            {
                SurfaceData s; FableInitSurface(input.uv, s);
                BRDFData b; InitializeBRDFData(s.albedo, s.metallic, s.specular, s.smoothness, s.alpha, b);
                MetaInput m = (MetaInput)0;
                m.Albedo = b.diffuse + b.specular * b.roughness * 0.5;
                m.Emission = s.emission;
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
