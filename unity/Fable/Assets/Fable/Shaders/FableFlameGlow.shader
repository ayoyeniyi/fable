// Fable/FlameGlow: additive soft flame for the fire particles (flames, embers) and the small flame cards that
// FableLiving puts on fx.candle.* / fx.torch.* / fx.lantern.*. Texture alpha times vertex colour (particles' colour
// over lifetime). _Billboard 1 turns a card about its up axis to face the eye (cards only), and flickers it.
// No depth write, fog fades it out with distance like everything else. Stereo instancing safe.
Shader "Fable/FlameGlow"
{
    Properties
    {
        _MainTex ("Flame (alpha)", 2D) = "white" {}
        [HDR] _Color ("Colour", Color) = (1, 0.75, 0.4, 1)
        _Billboard ("Billboard card", Float) = 0
        _Flicker ("Flicker (cards)", Range(0, 1)) = 0
        _Phase ("Phase", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "RenderPipeline" = "UniversalPipeline" "Queue" = "Transparent" "IgnoreProjector" = "True" "PreviewType" = "Plane" }
        Pass
        {
            Name "Glow"
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha One
            ZWrite Off
            Cull Off
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                half4 _Color;
                float _Billboard;
                half _Flicker;
                float _Phase;
            CBUFFER_END
            TEXTURE2D(_MainTex); SAMPLER(sampler_MainTex);

            struct Attributes { float4 positionOS : POSITION; half4 color : COLOR; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; half4 color : COLOR; half fog : TEXCOORD1; UNITY_VERTEX_INPUT_INSTANCE_ID UNITY_VERTEX_OUTPUT_STEREO };

            Varyings Vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input); UNITY_TRANSFER_INSTANCE_ID(input, o); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 posWS;
                half k = 1;
                if (_Billboard > 0.5)
                {
                    // a card in the object's XY plane (x across, y up), turned about world up to face this eye
                    float3 centre = TransformObjectToWorld(float3(0, 0, 0));
                    float3 toEye = GetCameraPositionWS() - centre; toEye.y = 0;
                    float3 fwd = dot(toEye, toEye) > 1e-6 ? normalize(toEye) : float3(0, 0, 1);
                    float3 right = float3(fwd.z, 0, -fwd.x);
                    float sx = length(GetObjectToWorldMatrix()._m00_m10_m20), sy = length(GetObjectToWorldMatrix()._m01_m11_m21);
                    float t = _Time.y; float ph = _Phase * 17.0;
                    half f = saturate(0.55 + 0.2 * sin(t * 8.1 + ph) + 0.15 * sin(t * 15.3 + ph * 2.1) + 0.1 * sin(t * 27.7 + ph * 3.7));
                    float up = input.positionOS.y;
                    float lean = sin(t * 3.1 + ph) * 0.12 * saturate(up / 0.5);
                    posWS = centre + right * ((input.positionOS.x + lean) * sx) + float3(0, 1, 0) * (up * sy * (0.85 + 0.3 * f));
                    k = lerp(1, f * 1.2, _Flicker);
                }
                else posWS = TransformObjectToWorld(input.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(posWS);
                o.uv = TRANSFORM_TEX(input.uv, _MainTex);
                o.color = input.color * _Color * k;
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }
            half4 Frag(Varyings input) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                half4 tex = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, input.uv);
                half4 c = tex * input.color;
                // additive: fade toward black (no light added) in the fog rather than toward the fog colour
                c.rgb *= ComputeFogIntensity(input.fog);
                return c;
            }
            ENDHLSL
        }
    }
    FallBack Off
}
