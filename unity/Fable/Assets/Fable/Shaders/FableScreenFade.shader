// Fable/ScreenFade: a black shell around the reader's head for fades between places (StepInFade.cs). Drawn last, over
// everything, without depth. Kept in the build by Resources/SceneRooms/Fade.mat.
Shader "Fable/ScreenFade"
{
    Properties { _Color ("Colour", Color) = (0,0,0,0) }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "RenderPipeline" = "UniversalPipeline" "Queue" = "Overlay+100" }
        Pass
        {
            Tags { "LightMode" = "UniversalForward" }
            ZTest Always ZWrite Off Cull Off Blend SrcAlpha OneMinusSrcAlpha
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            CBUFFER_START(UnityPerMaterial) float4 _Color; CBUFFER_END
            struct A { float4 p : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct V { float4 p : SV_POSITION; UNITY_VERTEX_OUTPUT_STEREO };
            V Vert(A a) { V o; UNITY_SETUP_INSTANCE_ID(a); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o); o.p = TransformObjectToHClip(a.p.xyz); return o; }
            half4 Frag(V i) : SV_Target { return _Color; }
            ENDHLSL
        }
    }
}
