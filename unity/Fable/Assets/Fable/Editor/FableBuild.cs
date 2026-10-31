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
        // One Unity scene per passage, each with its own lightmaps. Outdoor scenes get daylight, an unlit sky dome and haze.
        public class SceneDef { public string Id, Scene, Glb; public bool Outdoor; }
        public static readonly SceneDef[] Scenes =
        {
            new SceneDef { Id = "hall-of-doors", Scene = "Assets/Fable/Scenes/HallOfDoors.unity", Glb = "Assets/Fable/Models/hall_of_doors.glb" },
            new SceneDef { Id = "mad-tea-party", Scene = "Assets/Fable/Scenes/MadTeaParty.unity", Glb = "Assets/Fable/Models/mad_tea_party.glb", Outdoor = true },
            new SceneDef { Id = "queens-croquet-ground", Scene = "Assets/Fable/Scenes/QueensCroquetGround.unity", Glb = "Assets/Fable/Models/queens_croquet_ground.glb", Outdoor = true },
        };
        const string ScenePath = "Assets/Fable/Scenes/HallOfDoors.unity";   // the hall: desktop previews
        static SceneDef Def(string id) => Scenes.First(d => d.Id == id);
        /// Scenes whose environment GLB has been exported and imported.
        static SceneDef[] Available => Scenes.Where(d => AssetDatabase.LoadAssetAtPath<GameObject>(d.Glb)).ToArray();
        static SceneDef[] Built => Scenes.Where(d => File.Exists(d.Scene)).ToArray();
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
            // one input backend: "Both" is unsupported on Android. Hands and controllers come through OVRInput/OpenXR,
            // the editor keyboard fallback through the Input System package. Takes effect after an editor restart.
            var player = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset")[0]);
            player.FindProperty("activeInputHandler").intValue = 1; player.ApplyModifiedPropertiesWithoutUndo();
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
                urp.shadowDistance = 0; urp.maxAdditionalLightsCount = 8;
                var so = new SerializedObject(urp); so.FindProperty("m_AdditionalLightShadowsSupported").boolValue = false; so.FindProperty("m_MainLightShadowsSupported").boolValue = false; so.ApplyModifiedPropertiesWithoutUndo();
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
            SyncData();
            foreach (var d in Available) BuildScene(d.Id);
            SetBuildScenes();
        }

        /// Hall first: it is the scene the APK opens on; the passage picker loads the others.
        static void SetBuildScenes() =>
            EditorBuildSettings.scenes = Built.Select(d => new EditorBuildSettingsScene(d.Scene, true)).ToArray();

        static void NotInPlayMode() { if (EditorApplication.isPlayingOrWillChangePlaymode) throw new Exception("exit play mode first (unity command editor.playmode stop)"); }

        public static void BuildScene(string sceneId)
        {
            NotInPlayMode();
            var def = Def(sceneId); bool outdoor = def.Outdoor, hall = sceneId == "hall-of-doors";
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom; RenderSettings.reflectionIntensity = 1f;
            RenderSettings.skybox = null; RenderSettings.fog = true; RenderSettings.fogMode = FogMode.Exponential;
            if (outdoor)
            {
                // a soft English afternoon: sky above, warm ground bounce, a little haze so the far hedges sit back
                RenderSettings.ambientMode = AmbientMode.Trilight;
                RenderSettings.ambientSkyColor = new Color(0.46f, 0.55f, 0.66f); RenderSettings.ambientEquatorColor = new Color(0.42f, 0.45f, 0.38f); RenderSettings.ambientGroundColor = new Color(0.20f, 0.18f, 0.12f);
                RenderSettings.fogDensity = 0.008f; RenderSettings.fogColor = new Color(0.70f, 0.76f, 0.80f);
            }
            else
            {
                RenderSettings.ambientMode = AmbientMode.Flat; RenderSettings.ambientLight = new Color(0.09f, 0.07f, 0.05f);
                RenderSettings.fogDensity = 0.035f; RenderSettings.fogColor = new Color(0.06f, 0.045f, 0.03f);
            }

            // environment from the Blender GLB (glTFast importer creates a prefab-like asset)
            var glb = AssetDatabase.LoadAssetAtPath<GameObject>(def.Glb);
            if (!glb) throw new Exception($"GLB missing at {def.Glb}; run the Blender export first");
            var env = (GameObject)PrefabUtility.InstantiatePrefab(glb);
            env.name = "env." + sceneId;
            foreach (var t in env.GetComponentsInChildren<Transform>(true))
            {
                bool dynamic = SceneRegistry.IsAssetName(t.name) || (t.parent && SceneRegistry.IsAssetName(t.parent.name));
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, dynamic ? 0 : StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.OccluderStatic);
            }
            // the flame sits inside the glass chimney: glass and flame must not occlude the lightmapper or cast shadows
            foreach (var r in env.GetComponentsInChildren<Renderer>(true))
                if (r.name.Contains("LampGlass") || r.name.Contains("Flame") || r.name.Contains("GardenCard"))
                {
                    r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
                    GameObjectUtility.SetStaticEditorFlags(r.gameObject, StaticEditorFlags.BatchingStatic);
                }
            if (outdoor)
            {
                foreach (var l in env.GetComponentsInChildren<Light>(true))
                {
                    l.lightmapBakeType = LightmapBakeType.Mixed; l.shadows = LightShadows.Soft;
                    if (l.name.StartsWith("light.sun")) { l.type = LightType.Directional; l.intensity = 1.5f; l.color = new Color(1f, 0.93f, 0.80f); }
                    else if (l.name.StartsWith("light.sky")) { l.type = LightType.Directional; l.intensity = 0.35f; l.color = new Color(0.62f, 0.74f, 1f); l.shadows = LightShadows.None; }
                    else { l.intensity = 0.5f; l.range = 12f; l.color = new Color(1f, 0.95f, 0.86f); l.shadows = LightShadows.None; }
                }
                // the sky dome and far scenery are unlit backdrop: no lightmap, no shadows, shown only at full scale
                var unlit = Shader.Find("Universal Render Pipeline/Unlit");
                foreach (var r in env.GetComponentsInChildren<Renderer>(true))
                    if (FlowControllerBackdrop(r.name))
                    {
                        r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
                        GameObjectUtility.SetStaticEditorFlags(r.gameObject, StaticEditorFlags.BatchingStatic);
                        if (r.name.Contains("Sky") && r.sharedMaterial && unlit)
                        {
                            var path = $"Assets/Fable/Materials/{sceneId}_Sky.mat"; Directory.CreateDirectory("Assets/Fable/Materials");
                            var src = r.sharedMaterial; var tex = src.HasProperty("baseColorTexture") ? src.GetTexture("baseColorTexture") : src.mainTexture;
                            var m = AssetDatabase.LoadAssetAtPath<Material>(path); if (!m) { m = new Material(unlit); AssetDatabase.CreateAsset(m, path); }
                            m.SetTexture("_BaseMap", tex); m.SetColor("_BaseColor", tex ? Color.white : new Color(0.62f, 0.75f, 0.9f)); EditorUtility.SetDirty(m);
                            r.sharedMaterial = m;
                        }
                    }
            }
            if (outdoor && !env.GetComponentsInChildren<Renderer>(true).Any(r => r.name.Contains("Sky"))) AddSkyDome(env.transform, sceneId);
            if (!outdoor) foreach (var l in env.GetComponentsInChildren<Light>(true))
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
            // one baked reflection probe per scene: brass, glass, porcelain and the floor read their surroundings
            var probeGo = new GameObject(hall ? "HallReflectionProbe" : "SceneReflectionProbe"); probeGo.transform.SetParent(env.transform, false);
            var centreAnchor = FindDeep(env.transform, "anchor.hall.centre") ?? FindDeep(env.transform, "anchor.scene.centre"); probeGo.transform.position = (centreAnchor ? centreAnchor.position : env.transform.position) + Vector3.up * 1.4f;
            var probe = probeGo.AddComponent<ReflectionProbe>(); probe.mode = UnityEngine.Rendering.ReflectionProbeMode.Baked; probe.size = hall ? new Vector3(16, 4, 6) : new Vector3(30, 12, 30); probe.resolution = 128; probe.boxProjection = hall; probe.intensity = 1f;

            // camera rig
            GameObject rig; Transform head;
#if FABLE_META_XR
            var rigPrefab = AssetDatabase.FindAssets("OVRCameraRig t:Prefab").Select(g => AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(g))).FirstOrDefault(p => p.name == "OVRCameraRig");
            rig = (GameObject)PrefabUtility.InstantiatePrefab(rigPrefab);
            var ovrRig = rig.GetComponent<OVRCameraRig>();
            if (!rig.TryGetComponent<OVRManager>(out var manager)) manager = rig.AddComponent<OVRManager>();
            manager.trackingOriginType = OVRManager.TrackingOrigin.FloorLevel;
            head = ovrRig.centerEyeAnchor;
            // Interaction SDK rig: hand and controller data, grab/poke/ray interactors and hand visuals in one prefab,
            // pointed at this camera rig. Its OVRHand data sources also feed the reader's pinch gestures.
            var isdkPrefab = AssetDatabase.FindAssets("OVRComprehensiveInteractionRig t:Prefab").Select(AssetDatabase.GUIDToAssetPath)
                .Where(p => p.EndsWith("/OVRComprehensiveInteractionRig.prefab")).Select(AssetDatabase.LoadAssetAtPath<GameObject>).FirstOrDefault();
            if (!isdkPrefab) throw new Exception("OVRComprehensiveInteractionRig prefab not found (com.meta.xr.sdk.interaction.ovr)");
            var isdk = (GameObject)PrefabUtility.InstantiatePrefab(isdkPrefab, rig.transform);
            var rigRefSo = new SerializedObject(isdk.GetComponent<Oculus.Interaction.Input.OVRCameraRigRef>());
            rigRefSo.FindProperty("_ovrCameraRig").objectReferenceValue = ovrRig; rigRefSo.ApplyModifiedPropertiesWithoutUndo();
            // The reader never moves (the world scales around them), so the rig's locomotion stack (teleport, slide, turn,
            // microgesture locomotion, the capsule locomotor and its tunnelling vignettes) is removed rather than left half-wired.
            PrefabUtility.UnpackPrefabInstance(isdk, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            var doomed = isdk.GetComponentsInChildren<Transform>(true).Where(t => t.name == "Locomotor" || t.name.Contains("Locomotion")).ToList();
            foreach (var t in doomed) if (t) UnityEngine.Object.DestroyImmediate(t.gameObject);
            // drop the now-empty references those objects left in interactor groups and gates (the SDK asserts on null items)
            foreach (var mb in isdk.GetComponentsInChildren<MonoBehaviour>(true))
            {
                if (!mb) continue;
                var so = new SerializedObject(mb); var it = so.GetIterator(); bool changed = false;
                while (it.Next(true))
                {
                    if (!it.isArray || it.propertyType != SerializedPropertyType.Generic || it.arraySize == 0) continue;
                    if (it.GetArrayElementAtIndex(0).propertyType != SerializedPropertyType.ObjectReference) continue;
                    for (int i = it.arraySize - 1; i >= 0; i--)
                        if (it.GetArrayElementAtIndex(i).objectReferenceValue == null) { it.DeleteArrayElementAtIndex(i); changed = true; }
                }
                if (changed) so.ApplyModifiedPropertiesWithoutUndo();
            }
            OVRHand lh = null, rh = null;
            foreach (var h in isdk.GetComponentsInChildren<OVRHand>(true)) { if (h.name.Contains("Left")) lh = h; else if (h.name.Contains("Right")) rh = h; }
            if (!lh || !rh) throw new Exception("Interaction rig has no OVRHand data sources");
#else
            rig = new GameObject("CameraRig"); var camGo = new GameObject("CenterEye"); camGo.transform.SetParent(rig.transform); camGo.transform.localPosition = new Vector3(0, 1.62f, 0);
            var cam = camGo.AddComponent<Camera>(); cam.nearClipPlane = 0.05f; cam.farClipPlane = 60f; camGo.AddComponent<AudioListener>(); head = camGo.transform;
#endif
            var entrance = new[] { "anchor.reader.entrance", "anchor.reader.path", "anchor.reader.gate" }.Select(n => FindDeep(env.transform, n)).FirstOrDefault(t => t)
                           ?? env.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name.StartsWith("anchor.reader."));
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
            flow.SceneId = sceneId;

            Directory.CreateDirectory(Path.GetDirectoryName(def.Scene));
            EditorSceneManager.SaveScene(scene, def.Scene);
            SetBuildScenes();
            Debug.Log($"[FableBuild] scene saved: {def.Scene} with {registry.AssetIds.Count()} script-controlled assets");
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

        /// The repo's book, manifests and baseline scripts are the source of truth; StreamingAssets holds copies the app reads.
        [MenuItem("Fable/Sync Data")]
        public static void SyncData()
        {
            var repo = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", ".."));
            var dst = Path.Combine(Application.dataPath, "StreamingAssets");
            Directory.CreateDirectory(Path.Combine(dst, "book")); Directory.CreateDirectory(Path.Combine(dst, "scripts"));
            File.Copy(Path.Combine(repo, "book", "passages.json"), Path.Combine(dst, "book", "passages.json"), true);
            int n = 1;
            foreach (var f in Directory.GetFiles(Path.Combine(repo, "schema"), "manifest.*.json")) { File.Copy(f, Path.Combine(dst, "scripts", Path.GetFileName(f)), true); n++; }
            foreach (var f in Directory.GetFiles(Path.Combine(repo, "scripts"), "*.baseline.json")) { File.Copy(f, Path.Combine(dst, "scripts", Path.GetFileName(f)), true); n++; }
            AssetDatabase.Refresh();
            Debug.Log($"[FableBuild] synced {n} data files into StreamingAssets");
        }

        static bool FlowControllerBackdrop(string n) => FlowController.IsBackdrop(n);

        /// An inward-facing sphere with a baked vertical gradient (pale horizon to soft blue zenith), unlit, for outdoor
        /// scenes whose Blender sky was a world shader that glTF cannot carry. Named SkyDome so it is backdrop: full scale only.
        static void AddSkyDome(Transform env, string sceneId)
        {
            const int lon = 32, lat = 16; const float radius = 60f;
            var verts = new System.Collections.Generic.List<Vector3>(); var uvs = new System.Collections.Generic.List<Vector2>(); var tris = new System.Collections.Generic.List<int>();
            for (int y = 0; y <= lat; y++)
                for (int x = 0; x <= lon; x++)
                {
                    float v = (float)y / lat, phi = Mathf.Lerp(-0.15f, 1f, v) * Mathf.PI / 2, th = (float)x / lon * Mathf.PI * 2;
                    verts.Add(new Vector3(Mathf.Cos(phi) * Mathf.Cos(th), Mathf.Sin(phi), Mathf.Cos(phi) * Mathf.Sin(th)) * radius);
                    uvs.Add(new Vector2((float)x / lon, v));
                }
            for (int y = 0; y < lat; y++)
                for (int x = 0; x < lon; x++)
                {
                    int a = y * (lon + 1) + x, b = a + lon + 1;
                    tris.AddRange(new[] { a, a + 1, b, a + 1, b + 1, b });   // wound to face inward
                }
            var mesh = new Mesh { name = "SkyDome" }; mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0); mesh.RecalculateBounds();
            Directory.CreateDirectory("Assets/Fable/Materials");
            var meshPath = $"Assets/Fable/Materials/{sceneId}_SkyDome.asset"; AssetDatabase.DeleteAsset(meshPath); AssetDatabase.CreateAsset(mesh, meshPath);
            var tex = new Texture2D(1, 128, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp, name = "SkyGradient" };
            for (int i = 0; i < 128; i++)
            {
                float v = i / 127f; var horizon = new Color(0.86f, 0.89f, 0.88f); var mid = new Color(0.62f, 0.76f, 0.92f); var zenith = new Color(0.36f, 0.55f, 0.85f);
                tex.SetPixel(0, i, v < 0.25f ? Color.Lerp(horizon, mid, v / 0.25f) : Color.Lerp(mid, zenith, (v - 0.25f) / 0.75f));
            }
            tex.Apply();
            var texPath = $"Assets/Fable/Materials/{sceneId}_SkyGradient.asset"; AssetDatabase.DeleteAsset(texPath); AssetDatabase.CreateAsset(tex, texPath);
            var mat = new Material(Shader.Find("Universal Render Pipeline/Unlit")) { name = "SkyDome" }; mat.SetTexture("_BaseMap", tex);
            var matPath = $"Assets/Fable/Materials/{sceneId}_Sky.mat"; AssetDatabase.DeleteAsset(matPath); AssetDatabase.CreateAsset(mat, matPath);
            var go = new GameObject("SkyDome"); go.transform.SetParent(env, false);
            var centre = FindDeep(env, "anchor.scene.centre"); if (centre) go.transform.position = new Vector3(centre.position.x, env.position.y, centre.position.z);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = mat; mr.shadowCastingMode = ShadowCastingMode.Off; mr.receiveShadows = false;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
        }

        [MenuItem("Fable/3 Bake Lighting")]
        public static void BakeLighting() { foreach (var d in Built) BakeLighting(d.Id); }

        public static void BakeLighting(string sceneId)
        {
            NotInPlayMode();
            var def = Def(sceneId); bool hall = sceneId == "hall-of-doors";
            EditorSceneManager.OpenScene(def.Scene);
            Lightmapping.lightingSettings = new LightingSettings
            {
                lightmapper = LightingSettings.Lightmapper.ProgressiveGPU, lightmapMaxSize = 2048, lightmapResolution = 12, lightmapPadding = 2,
                directSampleCount = 32, indirectSampleCount = 256, environmentSampleCount = 64, maxBounces = 3, denoiserTypeDirect = LightingSettings.DenoiserType.OpenImage,
                denoiserTypeIndirect = LightingSettings.DenoiserType.OpenImage, lightmapCompression = LightmapCompression.HighQuality, mixedBakeMode = MixedLightingMode.Shadowmask, ao = true, aoMaxDistance = 0.6f
            };
            if (def.Outdoor) { Lightmapping.lightingSettings.lightmapResolution = 6; Lightmapping.lightingSettings.aoMaxDistance = 1.2f; }   // larger area, same atlas budget
            var name = hall ? "FableLighting" : Path.GetFileNameWithoutExtension(def.Scene) + "Lighting";
            Lightmapping.lightingSettings.name = name; AssetDatabase.CreateAsset(Lightmapping.lightingSettings, $"Assets/Fable/Scenes/{name}.lighting");
            if (!Lightmapping.Bake()) throw new Exception($"lightmap bake failed for {sceneId}");
            EditorSceneManager.SaveOpenScenes();
            Debug.Log($"[FableBuild] lightmaps baked for {sceneId}: {LightmapSettings.lightmaps.Length} maps");
        }

        [MenuItem("Fable/4 Build APK")]
        public static void BuildApk()
        {
            SyncData();
            Directory.CreateDirectory("out");
            SetBuildScenes();
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes = Built.Select(d => d.Scene).ToArray(), locationPathName = "out/fable.apk", target = BuildTarget.Android, options = BuildOptions.None });
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
