// Fable/SceneRoom: a downloaded scene room's surfaces (docs/SCENE_ROOMS_PIPELINE.md). The room's light was baked in
// Blender (blender/runtime_bake.py) into a light texture on UV 1; this draws base colour (UV 0) x light x _LightScale
// with the same soft highlight roll-off as the bake's exposure, and nothing is lit at runtime. Sky and backdrops have
// no light texture (_Unlit 1): their colour is drawn as it is. Foliage and cloth move in the scene's wind like
// Fable/LivingLit (vertex colour R is the weight; _SwayAmplitude / _Billow 0: still). Cut-out cards: _ALPHATEST_ON.
// Single-pass instanced stereo safe; kept in the build by Resources/SceneRoomLit.mat and SceneRoomCutout.mat.
Shader "Fable/SceneRoom"
{
    Properties
    {
        _BaseMap ("Base colour", 2D) = "white" {}
        _BaseColor ("Base colour factor", Color) = (1,1,1,1)
        _LightMap ("Light (UV 1)", 2D) = "white" {}
        _LightScale ("Light scale", Float) = 1
        _White ("Roll-off white point", Float) = 3
        _Unlit ("Unlit (sky, backdrops)", Float) = 0
        _Cutoff ("Alpha cutoff", Range(0,1)) = 0.5
        _SwayAmplitude ("Sway amplitude (m at weight 1)", Float) = 0
        _SwayFlutter ("Sway flutter", Range(0,1)) = 0.2
        _Billow ("Cloth billow (m at weight 1)", Float) = 0
        _Grade ("Mood grade (rgb multiply)", Color) = (1,1,1,1)
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "FableWind.hlsl"
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
        TEXTURE2D(_LightMap); SAMPLER(sampler_LightMap);
        CBUFFER_START(UnityPerMaterial)
            float4 _BaseMap_ST; float4 _BaseColor; float _LightScale, _White, _Unlit, _Cutoff, _SwayAmplitude, _SwayFlutter, _Billow; float4 _Grade;
        CBUFFER_END
        float4 _FableSceneGrade;   // the experience's mood (rgb multiply, set by ExperienceMood); zero means none

        struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv0 : TEXCOORD0; float2 uv1 : TEXCOORD1; float4 color : COLOR; UNITY_VERTEX_INPUT_INSTANCE_ID };
        struct Varyings { float4 positionCS : SV_POSITION; float2 uv0 : TEXCOORD0; float2 uv1 : TEXCOORD1; UNITY_VERTEX_OUTPUT_STEREO };

        float3 Moved(Attributes v)
        {
            float3 p = v.positionOS.xyz;
            if (_SwayAmplitude > 0) p = FableSwayOS(p, v.color.r, _SwayAmplitude, _SwayFlutter);
            if (_Billow > 0) p = FableBillowOS(p, v.normalOS, v.color.r, _Billow);
            return p;
        }
        Varyings Vert(Attributes v)
        {
            Varyings o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
            o.positionCS = TransformObjectToHClip(Moved(v)); o.uv0 = TRANSFORM_TEX(v.uv0, _BaseMap); o.uv1 = v.uv1;
            return o;
        }
        ENDHLSL

        Pass
        {
            Name "Unlit"
            Tags { "LightMode" = "UniversalForward" }
            Cull [_Cull]
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_local _ _ALPHATEST_ON
            #pragma multi_compile_instancing
            half4 Frag(Varyings i) : SV_Target
            {
                half4 base = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv0) * _BaseColor;
                #if defined(_ALPHATEST_ON)
                clip(base.a - _Cutoff);
                #endif
                half3 c = base.rgb;
                if (_Unlit < 0.5)
                {
                    c *= SAMPLE_TEXTURE2D(_LightMap, sampler_LightMap, i.uv1).rgb * _LightScale;
                    float w2 = _White * _White;
                    c = c * (1 + c / w2) / (1 + c);
                }
                half3 g = _FableSceneGrade.a > 0 ? _FableSceneGrade.rgb : half3(1, 1, 1);
                return half4(c * _Grade.rgb * g, 1);
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
            #pragma fragment FragDepth
            #pragma multi_compile_local _ _ALPHATEST_ON
            #pragma multi_compile_instancing
            half FragDepth(Varyings i) : SV_Target
            {
                #if defined(_ALPHATEST_ON)
                clip(SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv0).a * _BaseColor.a - _Cutoff);
                #endif
                return 0;
            }
            ENDHLSL
        }
    }
}
