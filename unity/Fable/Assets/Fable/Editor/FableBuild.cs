// Batch-mode build pipeline. Every step is a static method callable with -executeMethod so the
// whole project can be constructed, baked and built without touching the editor UI.
//
//   Unity -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.ConfigureProject
//   Unity -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.BuildScene
//   Unity -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.BakeLighting
//   Unity -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.BuildApk
using System;
using System.IO;
using System.Linq;
using TMPro;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

namespace Fable.Editor
{
    public static class FableBuild
    {
        const string ScenePath = "Assets/Fable/Scenes/HallOfDoors.unity";
        const string GlbPath = "Assets/Fable/Models/hall_of_doors.glb";
        const string Defines = "FABLE_META_XR";

        [MenuItem("Fable/1 Configure Project")]
        public static void ConfigureProject()
        {
            var target = NamedBuildTarget.Android;
            PlayerSettings.SetScriptingBackend(target, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel32;
            PlayerSettings.Android.targetSdkVersion = AndroidSdkVersions.AndroidApiLevelAuto;
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.Vulkan });
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.SetApplicationIdentifier(target, "com.fable.alice");
            PlayerSettings.productName = "Fable";
            PlayerSettings.companyName = "Fable";
            PlayerSettings.Android.textureCompressionFormats = new[] { TextureCompressionFormat.ASTC };
            PlayerSettings.gpuSkinning = true;
            // keep the Android build's footprint down: release IL2CPP, size-optimised codegen, high stripping, no symbol packages
            PlayerSettings.SetIl2CppCompilerConfiguration(target, Il2CppCompilerConfiguration.Release);
            PlayerSettings.SetIl2CppCodeGeneration(target, Il2CppCodeGeneration.OptimizeSize);
            PlayerSettings.SetManagedStrippingLevel(target, ManagedStrippingLevel.High);
            EditorUserBuildSettings.androidCreateSymbols = AndroidCreateSymbols.Disabled;
            EditorUserBuildSettings.androidBuildSubtarget = MobileTextureSubtarget.ASTC;
            PlayerSettings.SetScriptingDefineSymbols(target, Defines);
            PlayerSettings.SetScriptingDefineSymbols(NamedBuildTarget.Standalone, Defines);
            EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Android, BuildTarget.Android);
            QualitySettings.SetQualityLevel(0);
            QualitySettings.antiAliasing = 4;
            QualitySettings.shadows = UnityEngine.ShadowQuality.Disable;
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = -1;
            // URP asset: the template's Mobile asset, tuned for Quest 2
            var urp = AssetDatabase.FindAssets("t:UniversalRenderPipelineAsset").Select(g => AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(AssetDatabase.GUIDToAssetPath(g))).FirstOrDefault(a => a.name.Contains("Mobile")) ??
                      AssetDatabase.FindAssets("t:UniversalRenderPipelineAsset").Select(g => AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(AssetDatabase.GUIDToAssetPath(g))).FirstOrDefault();
            if (urp)
            {
                urp.msaaSampleCount = 4; urp.supportsHDR = false; urp.renderScale = 1.0f; urp.supportsCameraDepthTexture = false; urp.supportsCameraOpaqueTexture = false;
                urp.shadowDistance = 0; urp.maxAdditionalLightsCount = 8; urp.supportsAdditionalLightShadows = false; urp.supportsMainLightShadows = false;
                GraphicsSettings.defaultRenderPipeline = urp; QualitySettings.renderPipeline = urp;
                EditorUtility.SetDirty(urp);
            }
            AssetDatabase.SaveAssets();
            ConfigureXR();
            Debug.Log("[FableBuild] project configured for Quest (Android, ARM64, IL2CPP, Vulkan, ASTC, URP mobile, MSAA 4x)");
        }

        /// OpenXR loader for Android with the Meta Quest feature and hand tracking, done in code so the batch pipeline needs no clicks.
        [MenuItem("Fable/1b Configure XR")]
        public static void ConfigureXR()
        {
            var settingsPath = "Assets/XR/XRGeneralSettingsPerBuildTarget.asset";
            Directory.CreateDirectory("Assets/XR");
            var perTarget = AssetDatabase.LoadAssetAtPath<UnityEditor.XR.Management.XRGeneralSettingsPerBuildTarget>(settingsPath);
            if (!perTarget)
            {
                perTarget = ScriptableObject.CreateInstance<UnityEditor.XR.Management.XRGeneralSettingsPerBuildTarget>();
                AssetDatabase.CreateAsset(perTarget, settingsPath);
            }
            foreach (var group in new[] { BuildTargetGroup.Android, BuildTargetGroup.Standalone })
            {
                if (!perTarget.HasSettingsForBuildTarget(group)) perTarget.CreateDefaultSettingsForBuildTarget(group);
                var gs = perTarget.SettingsForBuildTarget(group);
                gs.InitManagerOnStart = true;
                if (gs.Manager == null)
                {
                    gs.Manager = ScriptableObject.CreateInstance<UnityEngine.XR.Management.XRManagerSettings>();
                    gs.Manager.name = group + " Providers"; AssetDatabase.AddObjectToAsset(gs.Manager, perTarget);
                }
                UnityEditor.XR.Management.Metadata.XRPackageMetadataStore.AssignLoader(gs.Manager, "UnityEngine.XR.OpenXR.OpenXRLoader", group);
                UnityEditor.XR.OpenXR.Features.FeatureHelpers.RefreshFeatures(group);
                var oxr = UnityEngine.XR.OpenXR.OpenXRSettings.GetSettingsForBuildTargetGroup(group);
                Debug.Log($"[FableBuild] OpenXR settings for {group}: {(oxr ? oxr.GetFeatures().Length + " features" : "none")}");
                if (oxr != null)
                {
                    oxr.renderMode = UnityEngine.XR.OpenXR.OpenXRSettings.RenderMode.SinglePassInstanced;
                    oxr.depthSubmissionMode = UnityEngine.XR.OpenXR.OpenXRSettings.DepthSubmissionMode.Depth16Bit;
                    foreach (var f in oxr.GetFeatures())
                    {
                        var n = f.GetType().Name;
                        if (n.StartsWith("Detached")) { f.enabled = false; continue; }
                        if (n.Contains("MetaQuest") || n.Contains("OculusTouchControllerProfile") || n.Contains("HandInteractionProfile") || n.Contains("HandTracking") || n.Contains("MetaXRFeature"))
                        { f.enabled = true; Debug.Log($"[FableBuild] OpenXR feature on ({group}): {n}"); }
                    }
                    EditorUtility.SetDirty(oxr);
                }
            }
            UnityEditor.EditorBuildSettings.AddConfigObject(UnityEngine.XR.Management.XRGeneralSettings.k_SettingsKey, perTarget, true);
            EditorUtility.SetDirty(perTarget); AssetDatabase.SaveAssets();
            Debug.Log("[FableBuild] XR: OpenXR loader assigned for Android and Standalone");
        }

        [MenuItem("Fable/2 Build Scene")]
        public static void BuildScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            RenderSettings.ambientMode = AmbientMode.Flat; RenderSettings.ambientLight = new Color(0.09f, 0.07f, 0.05f);
            RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom; RenderSettings.reflectionIntensity = 1f;
            RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Exponential; RenderSettings.fogDensity = 0.035f; RenderSettings.fogColor = new Color(0.06f, 0.045f, 0.03f);
            RenderSettings.skybox = null;

            // environment from the Blender GLB (glTFast importer creates a prefab-like asset)
            var glb = AssetDatabase.LoadAssetAtPath<GameObject>(GlbPath);
            if (!glb) throw new Exception($"GLB missing at {GlbPath}; run the Blender export first");
            var env = (GameObject)PrefabUtility.InstantiatePrefab(glb);
            env.name = "env.hall-of-doors";
            foreach (var t in env.GetComponentsInChildren<Transform>(true))
            {
                bool dynamic = t.name.StartsWith("prop.") || t.name.StartsWith("fx.") || t.name == "door.little" || (t.parent && (t.parent.name.StartsWith("prop.") || t.parent.name.StartsWith("fx.") || t.parent.name == "door.little"));
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, dynamic ? 0 : StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OccluderStatic);
            }
            // the flame sits inside the glass chimney: glass and flame must not occlude the lightmapper or cast shadows
            foreach (var r in env.GetComponentsInChildren<Renderer>(true))
                if (r.name.Contains("LampGlass") || r.name.Contains("Flame") || r.name.Contains("GardenCard"))
                {
                    r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
                    GameObjectUtility.SetStaticEditorFlags(r.gameObject, StaticEditorFlags.BatchingStatic);
                }
            foreach (var l in env.GetComponentsInChildren<Light>(true))
            {
                l.lightmapBakeType = LightmapBakeType.Mixed; l.shadows = LightShadows.Soft; l.intensity = l.name.StartsWith("Lamp") ? 2.2f : 0f; l.range = l.name.StartsWith("Lamp") ? 7.5f : 3f;
                l.color = l.name.StartsWith("Lamp") ? new Color(1f, 0.72f, 0.45f) : new Color(0.72f, 0.9f, 1f);
            }
            // glass and transparent props: switch to URP Lit transparent so the table and bottle read as glass
            Directory.CreateDirectory("Assets/Fable/Materials");
            Material Glassy(string name, Color tint, float smooth)
            {
                var path = $"Assets/Fable/Materials/{name}.mat"; var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (existing) { existing.color = tint; existing.SetFloat("_Smoothness", smooth); EditorUtility.SetDirty(existing); return existing; }
                var gm = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                gm.SetFloat("_Surface", 1); gm.SetFloat("_Blend", 0); gm.SetFloat("_ZWrite", 0); gm.SetFloat("_Metallic", 0f); gm.SetFloat("_Smoothness", smooth);
                gm.SetFloat("_EnvironmentReflections", 1f); gm.SetFloat("_SpecularHighlights", 1f);
                gm.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); gm.DisableKeyword("_ALPHAPREMULTIPLY_ON"); gm.SetOverrideTag("RenderType", "Transparent"); gm.renderQueue = 3000;
                gm.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha); gm.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                gm.color = tint; AssetDatabase.CreateAsset(gm, path); return gm;
            }
            var glassMat = Glassy("M_Glass_URP", new Color(0.55f, 0.7f, 0.65f, 0.10f), 0.98f);
            var liquidMat = Glassy("M_Liquid_URP", new Color(0.65f, 0.18f, 0.08f, 0.85f), 0.9f);
            var lampGlassMat = Glassy("M_LampGlass_URP", new Color(1f, 0.95f, 0.85f, 0.25f), 0.8f);
            foreach (var r in env.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials; bool changed = false;
                for (int i = 0; i < mats.Length; i++)
                {
                    var m = mats[i]; if (!m) continue;
                    if (m.name.Contains("LampGlass")) { mats[i] = lampGlassMat; changed = true; }
                    else if (m.name.Contains("Liquid")) { mats[i] = liquidMat; changed = true; }
                    else if (m.name.Contains("Glass")) { mats[i] = glassMat; changed = true; }
                }
                if (changed) r.sharedMaterials = mats;
            }
            // one baked reflection probe for the whole hall: brass, glass and the stone floor read their surroundings
            var probeGo = new GameObject("HallReflectionProbe"); probeGo.transform.SetParent(env.transform, false);
            var centreAnchor = FindDeep(env.transform, "anchor.hall.centre"); probeGo.transform.position = (centreAnchor ? centreAnchor.position : env.transform.position) + Vector3.up * 1.4f;
            var probe = probeGo.AddComponent<ReflectionProbe>(); probe.mode = UnityEngine.Rendering.ReflectionProbeMode.Baked; probe.size = new Vector3(16, 4, 6); probe.resolution = 128; probe.boxProjection = true; probe.intensity = 1f;

            // camera rig
            GameObject rig; Transform head;
#if FABLE_META_XR
            var rigPrefab = AssetDatabase.FindAssets("OVRCameraRig t:Prefab").Select(g => AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(g))).FirstOrDefault(p => p.name == "OVRCameraRig");
            rig = (GameObject)PrefabUtility.InstantiatePrefab(rigPrefab);
            var ovrRig = rig.GetComponent<OVRCameraRig>();
            var manager = rig.GetComponent<OVRManager>() ?? rig.AddComponent<OVRManager>();
            manager.trackingOriginType = OVRManager.TrackingOrigin.FloorLevel;
            head = ovrRig.centerEyeAnchor;
            var left = new GameObject("LeftHand"); left.transform.SetParent(ovrRig.leftHandAnchor, false); var lh = left.AddComponent<OVRHand>(); SetHandType(lh, OVRHand.Hand.HandLeft);
            var right = new GameObject("RightHand"); right.transform.SetParent(ovrRig.rightHandAnchor, false); var rh = right.AddComponent<OVRHand>(); SetHandType(rh, OVRHand.Hand.HandRight);
            var lskel = left.AddComponent<OVRSkeleton>(); var rskel = right.AddComponent<OVRSkeleton>();
            var lmesh = left.AddComponent<OVRMesh>(); var rmesh = right.AddComponent<OVRMesh>();
            left.AddComponent<OVRMeshRenderer>(); right.AddComponent<OVRMeshRenderer>();
            left.AddComponent<SkinnedMeshRenderer>(); right.AddComponent<SkinnedMeshRenderer>();
#else
            rig = new GameObject("CameraRig"); var camGo = new GameObject("CenterEye"); camGo.transform.SetParent(rig.transform); camGo.transform.localPosition = new Vector3(0, 1.62f, 0);
            var cam = camGo.AddComponent<Camera>(); cam.nearClipPlane = 0.05f; cam.farClipPlane = 60f; camGo.AddComponent<AudioListener>(); head = camGo.transform;
#endif
            var entrance = env.transform.Find("anchor.reader.entrance") ?? FindDeep(env.transform, "anchor.reader.entrance");
            if (entrance) rig.transform.position = entrance.position;
            var cameras = rig.GetComponentsInChildren<Camera>(true);
            foreach (var c in cameras) { c.nearClipPlane = 0.05f; c.farClipPlane = 60f; c.clearFlags = CameraClearFlags.SolidColor; c.backgroundColor = Color.black; var d = c.GetUniversalAdditionalCameraData(); if (d) { d.renderPostProcessing = false; d.antialiasing = AntialiasingMode.None; } }

            // reading room: a dark floor disc and a soft overhead light around the page
            var reading = new GameObject("ReadingRoom");
            var disc = GameObject.CreatePrimitive(PrimitiveType.Cylinder); disc.name = "FloorDisc"; disc.transform.SetParent(reading.transform); disc.transform.position = rig.transform.position + new Vector3(0, -0.01f, 0); disc.transform.localScale = new Vector3(6, 0.01f, 6);
            var discMat = new Material(Shader.Find("Universal Render Pipeline/Lit")); discMat.color = new Color(0.08f, 0.075f, 0.07f); discMat.SetFloat("_Smoothness", 0.1f); disc.GetComponent<Renderer>().sharedMaterial = discMat; UnityEngine.Object.DestroyImmediate(disc.GetComponent<Collider>());
            var table = GameObject.CreatePrimitive(PrimitiveType.Cylinder); table.name = "DioramaTable"; table.transform.SetParent(reading.transform);
            table.transform.position = rig.transform.position + new Vector3(0, 0.36f, 0.95f); table.transform.localScale = new Vector3(1.5f, 0.36f, 1.5f);
            var tableMat = new Material(Shader.Find("Universal Render Pipeline/Lit")); tableMat.color = new Color(0.16f, 0.12f, 0.09f); tableMat.SetFloat("_Smoothness", 0.35f); table.GetComponent<Renderer>().sharedMaterial = tableMat; UnityEngine.Object.DestroyImmediate(table.GetComponent<Collider>());
            var soft = new GameObject("ReadingLight").AddComponent<Light>(); soft.transform.SetParent(reading.transform); soft.transform.position = rig.transform.position + new Vector3(0, 2.4f, 0.6f); soft.type = LightType.Point; soft.range = 5; soft.intensity = 1.1f; soft.color = new Color(1f, 0.92f, 0.8f); soft.lightmapBakeType = LightmapBakeType.Realtime; soft.shadows = LightShadows.None;

            // systems
            var systems = new GameObject("Fable");
            var registry = systems.AddComponent<SceneRegistry>(); registry.Build(env.transform);
            var clips = systems.AddComponent<ClipPlayer>(); clips.Init(registry);
            var audio = systems.AddComponent<SpatialAudio>();
            var director = systems.AddComponent<SceneDirector>(); director.Registry = registry; director.Clips = clips; director.Audio = audio; director.ReaderHead = head;
            var input = systems.AddComponent<ReaderController>();
#if FABLE_META_XR
            input.LeftHand = lh; input.RightHand = rh; input.LeftPointer = ovrRig.leftHandAnchor; input.RightPointer = ovrRig.rightHandAnchor;
#endif
            var panel = BuildPanel(head);
            var flow = systems.AddComponent<FlowController>(); flow.Director = director; flow.Input = input; flow.Panel = panel; flow.Head = head; flow.ReadingRoom = reading;

            Directory.CreateDirectory(Path.GetDirectoryName(ScenePath));
            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            Debug.Log($"[FableBuild] scene saved: {ScenePath} with {registry.AssetIds.Count()} script-controlled assets");
        }

#if FABLE_META_XR
        static void SetHandType(OVRHand hand, OVRHand.Hand type)
        {
            var so = new SerializedObject(hand); so.FindProperty("HandType").enumValueIndex = (int)type; so.ApplyModifiedPropertiesWithoutUndo();
        }
#endif

        static Transform FindDeep(Transform root, string name) => root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == name);

        static ReadingPanel BuildPanel(Transform head)
        {
            var font = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>("Assets/Fable/Fonts/EBGaramond-Regular SDF.asset");
            if (!font)
            {
                var ttf = AssetDatabase.LoadAssetAtPath<Font>("Assets/Fable/Fonts/EBGaramond-Regular.ttf");
                font = TMP_FontAsset.CreateFontAsset(ttf, 90, 9, UnityEngine.TextCore.LowLevel.GlyphRenderMode.SDFAA, 2048, 2048);
                AssetDatabase.CreateAsset(font, "Assets/Fable/Fonts/EBGaramond-Regular SDF.asset");
                font.atlasTexture.name = "EBGaramond-Regular Atlas"; AssetDatabase.AddObjectToAsset(font.atlasTexture, font);
                font.material.name = "EBGaramond-Regular Material"; AssetDatabase.AddObjectToAsset(font.material, font);
                AssetDatabase.SaveAssets();
            }
            var go = new GameObject("ReadingPanel"); var canvas = go.AddComponent<Canvas>(); canvas.renderMode = RenderMode.WorldSpace;
            var rt = go.GetComponent<RectTransform>(); rt.sizeDelta = new Vector2(620, 780); go.transform.localScale = Vector3.one * 0.001f;
            var bg = new GameObject("Paper").AddComponent<UnityEngine.UI.Image>(); bg.transform.SetParent(go.transform, false); bg.rectTransform.anchorMin = Vector2.zero; bg.rectTransform.anchorMax = Vector2.one; bg.rectTransform.offsetMin = bg.rectTransform.offsetMax = Vector2.zero;
            bg.color = new Color(0.96f, 0.93f, 0.86f, 0.97f);
            TMP_Text Make(string n, float y, float h, float size, FontStyles style, Color col, TextAlignmentOptions align)
            {
                var t = new GameObject(n).AddComponent<TextMeshProUGUI>(); t.transform.SetParent(go.transform, false);
                var r = t.rectTransform; r.anchorMin = new Vector2(0, 1); r.anchorMax = new Vector2(1, 1); r.pivot = new Vector2(0.5f, 1); r.anchoredPosition = new Vector2(0, -y); r.sizeDelta = new Vector2(-96, h);
                t.font = font; t.fontSize = size; t.fontStyle = style; t.color = col; t.alignment = align; t.textWrappingMode = TextWrappingModes.Normal; t.richText = true; t.lineSpacing = 6; t.paragraphSpacing = 18;
                return t;
            }
            var panel = go.AddComponent<ReadingPanel>(); panel.Head = head;
            panel.Chapter = Make("Chapter", 44, 28, 15, FontStyles.SmallCaps, new Color(0.45f, 0.38f, 0.3f), TextAlignmentOptions.Center);
            panel.Title = Make("Title", 76, 52, 34, FontStyles.Normal, new Color(0.13f, 0.11f, 0.09f), TextAlignmentOptions.Center);
            panel.Body = Make("Body", 150, 560, 19.5f, FontStyles.Normal, new Color(0.13f, 0.11f, 0.09f), TextAlignmentOptions.TopJustified);
            panel.Hint = Make("Hint", 730, 30, 13, FontStyles.Italic, new Color(0.45f, 0.38f, 0.3f), TextAlignmentOptions.Center);
            return panel;
        }

        [MenuItem("Fable/3 Bake Lighting")]
        public static void BakeLighting()
        {
            EditorSceneManager.OpenScene(ScenePath);
            Lightmapping.lightingSettings = new LightingSettings
            {
                lightmapper = LightingSettings.Lightmapper.ProgressiveGPU, lightmapMaxSize = 2048, lightmapResolution = 12, lightmapPadding = 2,
                directSampleCount = 32, indirectSampleCount = 256, environmentSampleCount = 64, maxBounces = 3, denoiserTypeDirect = LightingSettings.DenoiserType.OpenImage,
                denoiserTypeIndirect = LightingSettings.DenoiserType.OpenImage, lightmapCompression = LightmapCompression.HighQuality, mixedBakeMode = MixedLightingMode.Shadowmask, ao = true, aoMaxDistance = 0.6f
            };
            Lightmapping.lightingSettings.name = "FableLighting"; AssetDatabase.CreateAsset(Lightmapping.lightingSettings, "Assets/Fable/Scenes/FableLighting.lighting");
            if (!Lightmapping.Bake()) throw new Exception("lightmap bake failed");
            EditorSceneManager.SaveOpenScenes();
            Debug.Log("[FableBuild] lightmaps baked");
        }

        [MenuItem("Fable/4 Build APK")]
        public static void BuildApk()
        {
            Directory.CreateDirectory("out");
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = new[] { ScenePath }, locationPathName = "out/fable-hall-of-doors.apk", target = BuildTarget.Android, options = BuildOptions.None });
            Debug.Log($"[FableBuild] {report.summary.result}: {report.summary.totalSize / 1e6:F1} MB, {report.summary.totalErrors} errors, {report.summary.totalTime.TotalSeconds:F0}s");
            if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded) throw new Exception("APK build failed");
        }

        /// Desktop preview captures from the editor camera, labelled as such.
        [MenuItem("Fable/Capture Desktop Previews")]
        public static void CaptureDesktopPreviews()
        {
            EditorSceneManager.OpenScene(ScenePath);
            Directory.CreateDirectory("../../captures/desktop");
            var cam = UnityEngine.Object.FindFirstObjectByType<Camera>();
            var env = GameObject.Find("env.hall-of-doors"); if (env) env.SetActive(true);
            var rt = new RenderTexture(1920, 1080, 24); cam.targetTexture = rt;
            void Shot(string name, Vector3 pos, Vector3 look)
            {
                cam.transform.position = pos; cam.transform.LookAt(look); cam.Render();
                var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false); RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0); tex.Apply();
                File.WriteAllBytes($"../../captures/desktop/{name}.png", tex.EncodeToPNG());
            }
            var e = FindDeep(env.transform, "anchor.reader.entrance"); var t = FindDeep(env.transform, "anchor.table.top"); var d = FindDeep(env.transform, "anchor.door.little"); var c = FindDeep(env.transform, "anchor.hall.centre"); var rc = FindDeep(env.transform, "anchor.reader.curtain");
            var panel = GameObject.Find("ReadingPanel"); if (panel) panel.SetActive(false);
            var reading = GameObject.Find("ReadingRoom"); if (reading) reading.SetActive(false);
            Shot("desktop_entrance", e.position + Vector3.up * 1.62f, t.position + Vector3.up * 0.6f);
            var toCentre = (c.position - t.position); toCentre.y = 0; toCentre = toCentre.sqrMagnitude < 0.01f ? Vector3.forward : toCentre.normalized;
            Shot("desktop_table", t.position + toCentre * 0.75f + Vector3.up * 0.4f, t.position);
            var toHall = (rc.position - d.position); toHall.y = 0; toHall = toHall.normalized;
            Shot("desktop_little_door", d.position + toHall * 0.9f + Vector3.up * 0.55f, d.position);
            if (panel) panel.SetActive(true); if (reading) reading.SetActive(true);
            cam.targetTexture = null; Debug.Log("[FableBuild] desktop previews written to captures/desktop");
        }
    }
}
