// Fable/Map: the book maps Peek opens (docs/MAPS_HEADSET.md): the globe's Earth, the scroll's sheet and the map pins.
// The reading rooms run from dark interiors to bright fields and the room's own lights are off while reading, so the
// map is self-lit: albedo times a view-facing shade, so a sphere still reads as round. It deliberately ignores the room's
// light probes: an outdoor room's probes, baked with a strong sun, made a grey blot on the dark sea (SH values far over
// 1). _Ambient is a flat lift of the shadows. No light loops, no shadows: one texture pair, cheap.
//   _BaseMap   the map image or the Earth (white for pins)
//   _MaskMap   the scroll's edge mask: albedo *= mask.rgb, clip(mask.a - 0.5) (docs/MAP_PROPS.md); white otherwise
//   _Crop      x = u offset, y = u scale: the unrolling scroll shows only the middle of the image at its true scale
//   _VertexTint 1 = multiply by vertex colour (the pins carry red glass and brass in their colours)
//   _Emit      added glow of _EmitColor (the lit pin's pulse is written here each frame on its own material)
Shader "Fable/Map"
{
    Properties
    {
        _BaseMap ("Map", 2D) = "white" {}
        _MaskMap ("Edge mask (linear)", 2D) = "white" {}
        _Color ("Tint", Color) = (1,1,1,1)
        _Crop ("U crop (offset, scale)", Vector) = (0,1,0,0)
        _Self ("Self light", Range(0, 2)) = 0.95
        _Ambient ("Shadow lift", Range(0, 1)) = 0.12
        _Spec ("Gloss", Range(0, 1)) = 0
        _VertexTint ("Vertex colour", Float) = 0
        [HDR] _EmitColor ("Glow colour", Color) = (1,0.35,0.2,1)
        _Emit ("Glow", Float) = 0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
    }
    SubShader
    {
        Tags { "RenderType" = "TransparentCutout" "RenderPipeline" = "UniversalPipeline" "Queue" = "AlphaTest" }
        Pass
        {
            Name "Map"
            Tags { "LightMode" = "UniversalForward" }
            Cull [_Cull]
            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                float4 _MaskMap_ST;
                half4 _Color;
                float4 _Crop;
                half _Self, _Ambient, _Spec, _VertexTint;
                half4 _EmitColor;
                half _Emit;
            CBUFFER_END
            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            TEXTURE2D(_MaskMap); SAMPLER(sampler_MaskMap);

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float4 color : COLOR; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings
            {
                float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float3 normalWS : TEXCOORD1; float3 positionWS : TEXCOORD2;
                half4 color : TEXCOORD3; half fog : TEXCOORD4;
                UNITY_VERTEX_INPUT_INSTANCE_ID UNITY_VERTEX_OUTPUT_STEREO
            };

            Varyings Vert(Attributes input)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(input); UNITY_TRANSFER_INSTANCE_ID(input, o); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                VertexPositionInputs p = GetVertexPositionInputs(input.positionOS.xyz);
                o.positionCS = p.positionCS; o.positionWS = p.positionWS;
                o.normalWS = TransformObjectToWorldNormal(input.normalOS);
                o.uv = float2(_Crop.x + input.uv.x * _Crop.y, input.uv.y);
                o.color = lerp(half4(1, 1, 1, 1), input.color, _VertexTint);
                o.fog = ComputeFogFactor(p.positionCS.z);
                return o;
            }

            half4 Frag(Varyings i, bool front : SV_IsFrontFace) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i); UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                half4 mask = SAMPLE_TEXTURE2D(_MaskMap, sampler_MaskMap, i.uv);
                clip(mask.a - 0.5);
                half3 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, TRANSFORM_TEX(i.uv, _BaseMap)).rgb * mask.rgb * _Color.rgb * i.color.rgb;
                float3 n = normalize(i.normalWS); n = front ? n : -n;
                float3 v = normalize(GetWorldSpaceViewDir(i.positionWS));
                half ndv = saturate(dot(n, v));
                // facing the reader full, falling off toward the limb; a touch brighter on the upper side, as under a lamp
                half shade = (0.55 + 0.45 * ndv) * (0.9 + 0.1 * n.y);
                half3 c = albedo * (shade * _Self + _Ambient);
                half spec = pow(saturate(dot(n, normalize(v + float3(0, 0.7, 0)))), 48) * _Spec;
                c += spec + _EmitColor.rgb * _Emit;
                c = MixFog(c, i.fog);
                return half4(c, 1);
            }
            ENDHLSL
        }
    }
}
