// Batch-mode build pipeline. Every step is a static method callable with -executeMethod so the
// whole project can be constructed, baked and built without touching the editor UI.
//
//   Unity -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.ConfigureProject
//   Unity -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.BuildScene
//   Unity -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.BakeLighting
//   Unity -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.BuildApk
using System;
using System.Collections.Generic;
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
        /// Room: a book's own room with no staged passage (the page floats in it; FlowController.RoomOnly). LightScale
        /// stretches indoor light ranges for rooms built at giant scale (Glumdalclitch's room is 12x).
        /// LobbyLook: lit like the lobby (the library room, where imported books are read).
        /// Living scenes (docs/LIVING_SCENES.md, FableLiving.cs):
        ///   Sound: the ambience layers, "kind[:volume]+kind[:volume]" from the sound library (Resources/Audio/amb.<kind>,
        ///          audio/SOURCES.md): surf, harbour, sea-open, river, wind-grass, wind-pines, wind-high, birds, gulls,
        ///          rigging, room-tone, clock, tavern, night, rain, fire, candle. Null: room tone indoors, birds and a
        ///          breeze outdoors.
        ///   Music: music.<id> to play (default the scene's own id; nothing if there is no such clip).
        ///   Wind: strength (0 calm, 0.35 a gentle breeze, 1 fresh, 2 a gale); -1 means 0.35 outdoors, 0 indoors.
        ///   WindToward: compass degrees the wind blows toward in world XZ (0 = +Z).
        ///   Water: swell, flow and sky colours for the scene's water.* (defaults suit a calm sea under the scene's sky).
        ///   Lights: per-light overrides applied after the indoor/outdoor rules (a light whose name is Name or starts with
        ///          Name + "."): intensity, range and colour, e.g. a cool moon or starlight, or one room's lamp balance.
        ///   Ambient: the ambient colour (flat indoors, the sky colour outdoors) when the default does not suit.
        ///   Fog: haze density when the default (0.008 outdoors, 0.035 indoors) hides what the scene is for (a far shore).
        ///   FlipNormals: meshes whose exported normals face away from the room (a painting turned to the wall): drawn
        ///          double-sided they look right, but the lightmap holds one side and bakes them black. Flipped copies.
        ///   ClearPanes: a room's WindowGlass is clear glass (a dusk window onto its backdrop, a deck skylight seen from
        ///          above) instead of the bright unlit daylight pane rooms get by default.
        public class SceneDef { public string Id, Scene, Glb, Book, Sound, Music; public bool Outdoor, Lobby, Room, LobbyLook, ClearPanes; public float LightScale = 1f, Wind = -1f, WindToward = 60f; public WaterLook WaterOverride; public LightLook[] Lights; public string[] FlipNormals; public Color? Ambient; public float Fog = -1f;
            /// Performance (Quest 2): NoFlameLights bakes the fires' glow instead of flickering realtime lights;
            /// ThinFoliage keeps that share of the foliage cards beyond ThinNear metres of the reader (FableLiving.Thin).
            public bool NoFlameLights; public float ThinFoliage = 1f, ThinNear = 7f;
            /// Where the reader starts (feet, world) and the compass yaw they face, when the room's anchor.reader.* does
            /// not leave clear floor and an open view: FableReaderStart finds these and keeps them in ReaderStarts.json;
            /// BuildScene (and FableReaderStart.Apply for built scenes) puts the rig there.
            public Vector3? ReaderAt => FableReaderStart.Override(Id)?.At;
            public float? ReaderYaw => FableReaderStart.Override(Id)?.Yaw; }
        public class LightLook { public string Name; public float Intensity = -1f, Range = -1f; public Color? Color; }
        static LightLook L(string name, float intensity, float range = -1f, Color? color = null) => new LightLook { Name = name, Intensity = intensity, Range = range, Color = color };
        static readonly Color Cool = new(0.62f, 0.70f, 1f), FireGlow = new(1f, 0.62f, 0.30f), CandleGlow = new(1f, 0.78f, 0.52f), Dawn = new(1f, 0.78f, 0.56f);
        public class WaterLook { public float SwellHeight = 0.35f, SwellLength = 18f, FlowSpeed = 0.6f; public float? FlowToward; public Color? SkyHorizon, SkyZenith; }
        public static string MusicId(SceneDef d) => d.Music ?? d.Id;
        public static float WindOf(SceneDef d) => d.Wind >= 0 ? d.Wind : d.Outdoor ? 0.35f : 0f;
        public static string AmbienceOf(SceneDef d) => d.Sound ?? (d.Outdoor ? "birds:0.6+wind-grass:0.7" : "room-tone");
        public static readonly SceneDef[] Scenes =
        {
            // first in the build: the app opens in the lobby (blender/build_lobby.py)
            new SceneDef { Id = "lobby", Scene = "Assets/Fable/Scenes/Lobby.unity", Glb = "Assets/Fable/Models/Lobby/lobby.gltf", Lobby = true, Sound = "room-tone:0.8+clock:0.3" },
            new SceneDef { Id = "hall-of-doors", Scene = "Assets/Fable/Scenes/HallOfDoors.unity", Glb = "Assets/Fable/Models/HallOfDoors/hall_of_doors.gltf" },
            new SceneDef { Id = "mad-tea-party", Scene = "Assets/Fable/Scenes/MadTeaParty.unity", Glb = "Assets/Fable/Models/MadTeaParty/mad_tea_party.gltf", Outdoor = true, Wind = 0.25f },
            new SceneDef { Id = "queens-croquet-ground", Scene = "Assets/Fable/Scenes/QueensCroquetGround.unity", Glb = "Assets/Fable/Models/QueensCroquetGround/queens_croquet_ground.gltf", Outdoor = true, Wind = 0.25f },
            // step 7: one room per book for the other three books
            new SceneDef { Id = "kansas-farmhouse", Scene = "Assets/Fable/Scenes/KansasFarmhouse.unity", Glb = "Assets/Fable/Models/KansasFarmhouse/kansas_farmhouse.gltf", Outdoor = true, Room = true, Book = "oz", Sound = "wind-grass:1+wind-high:0.55+room-tone:0.3", Wind = 1.1f, WindToward = 180f },
            new SceneDef { Id = "calypsos-cave", Scene = "Assets/Fable/Scenes/CalypsosCave.unity", Glb = "Assets/Fable/Models/CalypsosCave/calypsos_cave.gltf", Outdoor = true, Room = true, Book = "odyssey", Sound = "surf:0.55+birds:0.4+wind-pines:0.25", Wind = 0.3f, WaterOverride = new WaterLook { SwellHeight = 0.3f, SwellLength = 14f, FlowSpeed = 0.5f } },
            // the reader's own books are read in the library itself: a neutral room with no staged passages
            new SceneDef { Id = "library-room", Scene = "Assets/Fable/Scenes/LibraryRoom.unity", Glb = "Assets/Fable/Models/Lobby/lobby.gltf", Room = true, LobbyLook = true, Sound = "room-tone:0.8+clock:0.3", Music = "lobby" },
            new SceneDef { Id = "glumdalclitchs-room", Scene = "Assets/Fable/Scenes/GlumdalclitchsRoom.unity", Glb = "Assets/Fable/Models/GlumdalclitchsRoom/glumdalclitchs_room.gltf", Room = true, Book = "gulliver", LightScale = 12f, Sound = "room-tone:1+clock:0.45" },
            // the second and third rooms of Oz, the Odyssey and Gulliver (2026-11-03; blender/build_*.py, one subagent each)
            new SceneDef { Id = "poppy-field", Scene = "Assets/Fable/Scenes/PoppyField.unity", Glb = "Assets/Fable/Models/PoppyField/poppy_field.gltf", Outdoor = true, Room = true, Book = "oz", Sound = "birds:0.7+wind-grass:0.6", Wind = 0.4f, WindToward = 75f, WaterOverride = new WaterLook { FlowSpeed = 0.45f, FlowToward = 0f } },
            new SceneDef { Id = "emerald-throne-room", Scene = "Assets/Fable/Scenes/EmeraldThroneRoom.unity", Glb = "Assets/Fable/Models/EmeraldThroneRoom/emerald_throne_room.gltf", Room = true, Book = "oz", Sound = "room-tone:0.9" },
            new SceneDef { Id = "odysseus-ship", Scene = "Assets/Fable/Scenes/OdysseusShip.unity", Glb = "Assets/Fable/Models/OdysseusShip/odysseus_ship.gltf", Outdoor = true, Room = true, Book = "odyssey", Sound = "sea-open:0.8+harbour:0.5+rigging:0.6+gulls:0.15", Music = "calypsos-cave", Wind = 0.6f, WindToward = 40f, WaterOverride = new WaterLook { SwellHeight = 0.55f, SwellLength = 22f } },
            new SceneDef { Id = "ithaca-hall", Scene = "Assets/Fable/Scenes/IthacaHall.unity", Glb = "Assets/Fable/Models/IthacaHall/ithaca_hall.gltf", Outdoor = true, Room = true, Book = "odyssey", Sound = "room-tone:0.6+birds:0.25", Music = "lobby", Wind = 0.15f },
            new SceneDef { Id = "lilliput-beach", Scene = "Assets/Fable/Scenes/LilliputBeach.unity", Glb = "Assets/Fable/Models/LilliputBeach/lilliput_beach.gltf", Outdoor = true, Room = true, Book = "gulliver", Sound = "surf:0.8+gulls:0.35+wind-grass:0.35", Wind = 0.45f, WindToward = 100f, WaterOverride = new WaterLook { SwellHeight = 0.3f, SwellLength = 16f } },
            new SceneDef { Id = "laputa", Scene = "Assets/Fable/Scenes/Laputa.unity", Glb = "Assets/Fable/Models/Laputa/laputa.gltf", Outdoor = true, Room = true, Book = "gulliver", Sound = "wind-high:0.9+birds:0.2", Wind = 0.6f, WindToward = 120f },
            // the three rooms each of Moby-Dick, The War of the Worlds, Treasure Island and Pride and Prejudice (2026-11-15;
            // blender/build_*.py, replacing their bundled generated rooms). Light balances follow the Blender lamp wattages.
            new SceneDef { Id = "battery-waterfront", Scene = "Assets/Fable/Scenes/BatteryWaterfront.unity", Glb = "Assets/Fable/Models/BatteryWaterfront/battery_waterfront.gltf", Outdoor = true, Room = true, Book = "mobydick", Sound = "harbour:0.6+gulls:0.35+wind-grass:0.45+birds:0.15", Wind = 0.6f, WindToward = 70f, Fog = 0.003f, WaterOverride = new WaterLook { SwellHeight = 0.25f, SwellLength = 12f } },
            new SceneDef { Id = "spouter-inn", Scene = "Assets/Fable/Scenes/SpouterInn.unity", Glb = "Assets/Fable/Models/SpouterInn/spouter_inn.gltf", Room = true, Book = "mobydick", Sound = "room-tone:0.8+tavern:0.15+wind-high:0.2",
                Lights = new[] { L("Lamp.entryHanging", 1.2f), L("Lamp.entryLantern", 1.1f), L("Lamp.barLantern", 1.1f), L("Lamp.roomHanging", 1.0f), L("Lamp.stove", 0.8f, 6f, FireGlow), L("Lamp.candles", 0.45f, 5f, CandleGlow), L("Lamp.doorCandle", 0.35f, 4f, CandleGlow) } },
            new SceneDef { Id = "pequod-deck", Scene = "Assets/Fable/Scenes/PequodDeck.unity", Glb = "Assets/Fable/Models/PequodDeck/pequod_deck.gltf", Outdoor = true, Room = true, Book = "mobydick", Sound = "harbour:0.7+rigging:0.5+gulls:0.3+wind-high:0.3", Wind = 0.5f, WindToward = 110f, Fog = 0.004f, WaterOverride = new WaterLook { SwellHeight = 0.12f, SwellLength = 8f } },
            new SceneDef { Id = "ogilvys-observatory", Scene = "Assets/Fable/Scenes/OgilvysObservatory.unity", Glb = "Assets/Fable/Models/OgilvysObservatory/ogilvys_observatory.gltf", Room = true, Book = "worlds", Sound = "night:0.55+room-tone:0.5",
                Lights = new[] { L("Lamp.lantern", 1.2f), L("Lamp.lanternglow", 0.5f, 5f), L("Lamp.starlight", 0.6f, 9f, Cool) } },
            new SceneDef { Id = "horsell-sandpits", Scene = "Assets/Fable/Scenes/HorsellSandpits.unity", Glb = "Assets/Fable/Models/HorsellSandpits/horsell_sandpits.gltf", Outdoor = true, Room = true, Book = "worlds", Sound = "birds:0.65+wind-pines:0.35", Wind = 0.25f, WindToward = 80f,
                Lights = new[] { L("light.sun", 1.2f, -1f, Dawn), L("light.sky", 0.3f, -1f, new Color(0.62f, 0.70f, 0.95f)) } },
            new SceneDef { Id = "maybury-dining-room", Scene = "Assets/Fable/Scenes/MayburyDiningRoom.unity", Glb = "Assets/Fable/Models/MayburyDiningRoom/maybury_dining_room.gltf", Room = true, Book = "worlds", Sound = "room-tone:0.8+birds:0.15",
                Lights = new[] { L("Lamp.table", 1.5f, 7.5f, new Color(1f, 0.76f, 0.66f)), L("Lamp.dusk", 1.1f, 9f, new Color(0.55f, 0.64f, 1f)), L("Lamp.fire", 0.7f, 6f, FireGlow), L("Lamp.candles", 0.35f, 4f, CandleGlow) } },
            new SceneDef { Id = "benbow-cove", Scene = "Assets/Fable/Scenes/BenbowCove.unity", Glb = "Assets/Fable/Models/BenbowCove/benbow_cove.gltf", Outdoor = true, Room = true, Book = "treasure", Sound = "surf:0.8+gulls:0.3+wind-high:0.4", Wind = 0.5f, WindToward = 30f,
                Lights = new[] { L("light.sun", 1.1f, -1f, Dawn), L("light.sky", 0.35f, -1f, new Color(0.70f, 0.78f, 0.95f)) } },
            new SceneDef { Id = "squires-library", Scene = "Assets/Fable/Scenes/SquiresLibrary.unity", Glb = "Assets/Fable/Models/SquiresLibrary/squires_library.gltf", Room = true, Book = "treasure", Sound = "room-tone:0.8+wind-high:0.1",
                Lights = new[] { L("Lamp.fire", 2.0f, 9f, FireGlow), L("Lamp.candles", 0.5f, 5f, CandleGlow), L("Lamp.mantel", 0.35f, 4f, CandleGlow), L("Lamp.moon", 0.25f, -1f, Cool) } },
            new SceneDef { Id = "spyglass-tavern", Scene = "Assets/Fable/Scenes/SpyglassTavern.unity", Glb = "Assets/Fable/Models/SpyglassTavern/spyglass_tavern.gltf", Outdoor = true, Room = true, Book = "treasure", Sound = "tavern:0.45+harbour:0.5+gulls:0.25", Wind = 0.3f, WaterOverride = new WaterLook { SwellHeight = 0.1f, SwellLength = 8f } },
            new SceneDef { Id = "longbourn-library", Scene = "Assets/Fable/Scenes/LongbournLibrary.unity", Glb = "Assets/Fable/Models/LongbournLibrary/longbourn_library.gltf", Room = true, Book = "pride", Sound = "room-tone:0.8+birds:0.15",
                Lights = new[] { L("Lamp.window", 1.1f, 8f, new Color(0.86f, 0.90f, 1f)), L("Lamp.fire", 1.1f, 7f, FireGlow) }, Ambient = new Color(0.13f, 0.12f, 0.11f) },
            new SceneDef { Id = "fields-to-netherfield", Scene = "Assets/Fable/Scenes/FieldsToNetherfield.unity", Glb = "Assets/Fable/Models/FieldsToNetherfield/fields_to_netherfield.gltf", Outdoor = true, Room = true, Book = "pride", Sound = "birds:0.7+wind-grass:0.5", Wind = 0.4f, WindToward = 90f,
                Lights = new[] { L("light.sun", 0.45f), L("light.sky", 0.45f) } },
            new SceneDef { Id = "netherfield-drawing-room", Scene = "Assets/Fable/Scenes/NetherfieldDrawingRoom.unity", Glb = "Assets/Fable/Models/NetherfieldDrawingRoom/netherfield_drawing_room.gltf", Room = true, Book = "pride", Sound = "room-tone:0.8",
                Lights = new[] { L("Lamp.fire", 1.5f, 8f, FireGlow), L("Lamp.candles.table", 0.6f, 5f, CandleGlow), L("Lamp.candles.mantel", 0.55f, 5f, CandleGlow), L("Lamp.candle.books", 0.35f, 4f, CandleGlow) } },
            // the three rooms each of Around the World in Eighty Days and Frankenstein (2026-11-15; blender/build_*.py).
            // WindToward is Unity's compass (0 = +Z, 90 = +X): a Blender compass bearing (0 = +Y) plus 180, since the
            // glTF import turns Blender's +Y into Unity's -Z and mirrors X.
            new SceneDef { Id = "reform-club", Scene = "Assets/Fable/Scenes/ReformClub.unity", Glb = "Assets/Fable/Models/ReformClub/reform_club.gltf", Room = true, ClearPanes = true, Book = "eighty", Sound = "room-tone:0.7+tavern:0.06", Wind = 0f,
                Lights = new[] { L("Lamp.gasolier", 2.4f, 9f), L("Lamp.bracketN", 0.7f, 5f), L("Lamp.bracketS", 0.7f, 5f), L("Lamp.fire", 0.9f, 6f, FireGlow), L("Lamp.dusk", 0.8f, 6f, new Color(0.55f, 0.65f, 1f)) },
                Ambient = new Color(0.16f, 0.13f, 0.11f), Fog = 0.008f, FlipNormals = new[] { "MESH_MarinePainting" } },
            new SceneDef { Id = "mongolia-deck", Scene = "Assets/Fable/Scenes/MongoliaDeck.unity", Glb = "Assets/Fable/Models/MongoliaDeck/mongolia_deck.gltf", Outdoor = true, Room = true, ClearPanes = true, Book = "eighty", Sound = "sea-open:0.7+wind-high:0.25", Wind = 0.6f, WindToward = 0f, Fog = 0.003f,
                Lights = new[] { L("light.sun", 1.7f, -1f, new Color(1f, 0.94f, 0.84f)), L("light.sky", 0.45f, -1f, new Color(0.65f, 0.76f, 1f)) }, WaterOverride = new WaterLook { SwellHeight = 0.55f, SwellLength = 40f } },
            new SceneDef { Id = "pillaji-forest", Scene = "Assets/Fable/Scenes/PillajiForest.unity", Glb = "Assets/Fable/Models/PillajiForest/pillaji_forest.gltf", Outdoor = true, Room = true, Book = "eighty", Sound = "night:0.5+birds:0.2+wind-pines:0.12", Wind = 0.15f, Fog = 0.002f, NoFlameLights = true,
                Lights = new[] { L("light.sun", 1.1f, -1f, new Color(1f, 0.62f, 0.32f)), L("light.sky", 0.4f, -1f, new Color(0.55f, 0.64f, 0.95f)) } },
            new SceneDef { Id = "ingolstadt-garret", Scene = "Assets/Fable/Scenes/IngolstadtGarret.unity", Glb = "Assets/Fable/Models/IngolstadtGarret/ingolstadt_garret.gltf", Room = true, Book = "frankenstein", Sound = "rain:0.55+room-tone:0.45", Wind = 0f,
                Lights = new[] { L("Lamp.candle", 0.45f, 4f, CandleGlow), L("Lamp.fire", 0.9f, 6f, new Color(1f, 0.45f, 0.18f)), L("Lamp.window", 0.3f, 6f, new Color(0.55f, 0.65f, 1f)) } },
            new SceneDef { Id = "mer-de-glace", Scene = "Assets/Fable/Scenes/MerDeGlace.unity", Glb = "Assets/Fable/Models/MerDeGlace/mer_de_glace.gltf", Outdoor = true, Room = true, Book = "frankenstein", Sound = "wind-high:0.55+wind-pines:0.35+river:0.12", Wind = 0.45f, WindToward = 20f, Fog = 0.0006f, ThinFoliage = 0.6f, ThinNear = 10f,
                Lights = new[] { L("light.sun", 1.5f, -1f, new Color(1f, 0.97f, 0.92f)) } },
            new SceneDef { Id = "arctic-ice", Scene = "Assets/Fable/Scenes/ArcticIce.unity", Glb = "Assets/Fable/Models/ArcticIce/arctic_ice.gltf", Outdoor = true, Room = true, Book = "frankenstein", Sound = "wind-high:0.75+rigging:0.35", Wind = 0.75f, WindToward = 40f, Fog = 0.0006f,
                Lights = new[] { L("light.sun", 1.6f, -1f, new Color(1f, 0.76f, 0.52f)), L("light.sky", 0.55f, -1f, new Color(0.62f, 0.72f, 1f)) }, WaterOverride = new WaterLook { SwellHeight = 0f, FlowSpeed = 0f } },
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
                // Lightmapped (ContributeGI) but never BatchingStatic or occlusion-static: the whole environment is scaled and moved
                // at runtime (diorama, expand, the 4x size change) and static-batched meshes are frozen in world space at load.
                GameObjectUtility.SetStaticEditorFlags(t.gameObject, dynamic ? 0 : StaticEditorFlags.ContributeGI | StaticEditorFlags.ReflectionProbeStatic);
            }
            if (def.FlipNormals != null)
                foreach (var mf in env.GetComponentsInChildren<MeshFilter>(true).Where(f => def.FlipNormals.Contains(f.name) && f.sharedMesh))
                {
                    var m = UnityEngine.Object.Instantiate(mf.sharedMesh); m.name = mf.sharedMesh.name + "_flipped";
                    m.normals = m.normals.Select(n => -n).ToArray();
                    for (int sm = 0; sm < m.subMeshCount; sm++) { var t = m.GetTriangles(sm); for (int i = 0; i < t.Length; i += 3) (t[i + 1], t[i + 2]) = (t[i + 2], t[i + 1]); m.SetTriangles(t, sm); }
                    var meshPath = $"Assets/Fable/Materials/{sceneId}_{mf.name}_flipped.asset"; Directory.CreateDirectory("Assets/Fable/Materials");
                    AssetDatabase.DeleteAsset(meshPath); AssetDatabase.CreateAsset(m, meshPath); mf.sharedMesh = m;
                }
            // the flame sits inside the glass chimney: glass and flame must not occlude the lightmapper or cast shadows
            foreach (var r in env.GetComponentsInChildren<Renderer>(true))
                if (r.name.Contains("LampGlass") || r.name.Contains("Flame") || r.name.Contains("GardenCard") || r.name.Contains("WindowGlass"))
                {
                    r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
                    GameObjectUtility.SetStaticEditorFlags(r.gameObject, 0);
                }
            if (outdoor)
            {
                foreach (var l in env.GetComponentsInChildren<Light>(true))
                {
                    l.lightmapBakeType = LightmapBakeType.Mixed; l.shadows = LightShadows.Soft;
                    if (l.name.StartsWith("light.sun")) { l.type = LightType.Directional; l.intensity = 1.5f; l.color = new Color(1f, 0.93f, 0.80f); }
                    // the sky fill is baked: as a realtime light it is a second per-pixel light on every surface (Quest 2)
                    else if (l.name.StartsWith("light.sky")) { l.type = LightType.Directional; l.intensity = 0.35f; l.color = new Color(0.62f, 0.74f, 1f); l.shadows = LightShadows.None; l.lightmapBakeType = LightmapBakeType.Baked; }
                    else if (l.name.Contains("Fire") || l.name.Contains("lamp") || l.name.Contains("stove")) { l.lightmapBakeType = LightmapBakeType.Baked; l.intensity = l.name.Contains("Fire") ? 6f : 2.2f; l.range = l.name.Contains("Fire") ? 9f : 5f; l.color = new Color(1f, 0.62f, 0.30f); l.shadows = LightShadows.Soft; }   // hearth, oil lamp, stove: warm, baked
                    else { l.intensity = 0.5f; l.range = 12f; l.color = new Color(1f, 0.95f, 0.86f); l.shadows = LightShadows.None; l.lightmapBakeType = LightmapBakeType.Baked; }   // fills: baked, not per-pixel
                }
                if (sceneId == "ithaca-hall")
                {
                    // a hall lit by a low sun through the doors and a newly lit hearth: warm, dim ambient and a light haze,
                    // not the default bright blue outdoor ambient that would flatten the interior
                    foreach (var l in env.GetComponentsInChildren<Light>(true))
                        if (l.name.StartsWith("light.sky")) l.intensity = 0.2f;
                    RenderSettings.ambientSkyColor = new Color(0.22f, 0.20f, 0.18f); RenderSettings.ambientEquatorColor = new Color(0.20f, 0.16f, 0.12f); RenderSettings.ambientGroundColor = new Color(0.10f, 0.08f, 0.06f);
                    RenderSettings.fogDensity = 0.012f; RenderSettings.fogColor = new Color(0.36f, 0.30f, 0.24f);
                }
                if (sceneId == "kansas-farmhouse")
                {
                    // the cyclone coming: a low, filtered sun, a gray-green sky and close gray haze
                    foreach (var l in env.GetComponentsInChildren<Light>(true))
                    {
                        if (l.name.StartsWith("light.sun")) { l.intensity = 0.55f; l.color = new Color(0.80f, 0.84f, 0.74f); }
                        else if (l.name.StartsWith("light.sky")) { l.intensity = 0.3f; l.color = new Color(0.58f, 0.66f, 0.62f); }
                    }
                    RenderSettings.ambientSkyColor = new Color(0.30f, 0.34f, 0.31f); RenderSettings.ambientEquatorColor = new Color(0.26f, 0.27f, 0.24f); RenderSettings.ambientGroundColor = new Color(0.14f, 0.13f, 0.11f);
                    RenderSettings.fogDensity = 0.02f; RenderSettings.fogColor = new Color(0.40f, 0.44f, 0.40f);
                }
                // the sky dome and far scenery are unlit backdrop: no lightmap, no shadows, shown only at full scale
                var unlit = Shader.Find("Universal Render Pipeline/Unlit");
                foreach (var r in env.GetComponentsInChildren<Renderer>(true))
                    if (FlowControllerBackdrop(r.name))
                    {
                        r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
                        GameObjectUtility.SetStaticEditorFlags(r.gameObject, 0);
                        if (r.name.Contains("Sky") && r.sharedMaterial && unlit)
                        {
                            // one material per dome part: a dome split in halves (SkyDome.front / SkyDome.back) has a texture each
                            var part = r.name.StartsWith("SkyDome.") ? "_" + r.name.Substring("SkyDome.".Length) : "";
                            var path = $"Assets/Fable/Materials/{sceneId}_Sky{part}.mat"; Directory.CreateDirectory("Assets/Fable/Materials");
                            var src = r.sharedMaterial; var tex = src.HasProperty("baseColorTexture") ? src.GetTexture("baseColorTexture") : src.mainTexture;
                            var m = AssetDatabase.LoadAssetAtPath<Material>(path); if (!m) { m = new Material(unlit); AssetDatabase.CreateAsset(m, path); }
                            m.SetTexture("_BaseMap", tex); m.SetColor("_BaseColor", tex ? Color.white : new Color(0.62f, 0.75f, 0.9f));
                            m.SetFloat("_Cull", (float)CullMode.Off);   // Blender domes are often wound outward (doubleSided in glTF)
                            EditorUtility.SetDirty(m);
                            r.sharedMaterial = m;
                        }
                    }
            }
            if (outdoor && !env.GetComponentsInChildren<Renderer>(true).Any(r => r.name.Contains("Sky"))) AddSkyDome(env.transform, sceneId);
            if (!outdoor && def.Room)
            {
                // an interior's painted view through its windows (far.*, glTF emissive): drawn unlit from its picture,
                // since the emission does not come through the import and the baked room light would leave it black
                var unlitFar = Shader.Find("Universal Render Pipeline/Unlit");
                foreach (var r in env.GetComponentsInChildren<Renderer>(true).Where(r => r.name.StartsWith("far.") && r.sharedMaterial))
                {
                    var src = r.sharedMaterial; Texture tex = null;
                    foreach (var prop in new[] { "emissiveTexture", "baseColorTexture" }) if (!tex && src.HasProperty(prop)) tex = src.GetTexture(prop);
                    if (!tex) continue;
                    var path = $"Assets/Fable/Materials/{sceneId}_{r.name}.mat"; Directory.CreateDirectory("Assets/Fable/Materials");
                    var m = AssetDatabase.LoadAssetAtPath<Material>(path); if (!m) { m = new Material(unlitFar); AssetDatabase.CreateAsset(m, path); }
                    m.SetTexture("_BaseMap", tex); m.SetColor("_BaseColor", Color.white); m.SetFloat("_Cull", (float)CullMode.Off); EditorUtility.SetDirty(m);
                    r.sharedMaterial = m; r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
                    GameObjectUtility.SetStaticEditorFlags(r.gameObject, 0);
                }
            }
            if (!outdoor) foreach (var l in env.GetComponentsInChildren<Light>(true))
            {
                // Fully baked: seven realtime point lights cost ~25 ms a frame on Quest 2 and blew the hall out to yellow at 2.2.
                l.lightmapBakeType = LightmapBakeType.Baked; l.shadows = LightShadows.Soft; l.intensity = l.name.StartsWith("Lamp") ? 1.0f : 0f; l.range = (l.name.StartsWith("Lamp") ? 7.5f : 3f) * def.LightScale;
                l.color = l.name.StartsWith("Lamp") ? new Color(1f, 0.84f, 0.64f) : new Color(0.72f, 0.9f, 1f);
                // the lobby: the table lamp and the two wall sconces light the room; the four picture lamps (Lamp1-4) the covers
                if (def.Lobby || def.LobbyLook) { l.range = 6f; l.intensity = l.name.StartsWith("Lamp0") ? 4f : l.name.StartsWith("Lamp5") || l.name.StartsWith("Lamp6") ? 5f : 1.1f; }
            }
            if (def.Lobby || def.LobbyLook) RenderSettings.ambientLight = new Color(0.20f, 0.165f, 0.13f);
            if (sceneId == "emerald-throne-room")
            {
                // one great light in the crown of a 6.6 m dome: it must reach the floor at the wall (about 8.2 m away)
                foreach (var l in env.GetComponentsInChildren<Light>(true))
                    if (l.name.StartsWith("Lamp")) { l.range = 18f; l.intensity = 10f; l.color = new Color(1f, 0.92f, 0.8f); }
                RenderSettings.ambientLight = new Color(0.30f, 0.33f, 0.28f);
            }
            if (!outdoor && def.LightScale > 1f)
            {
                // a room at giant scale: the window light travels tens of metres, so it needs far more intensity than a lamp
                foreach (var l in env.GetComponentsInChildren<Light>(true))
                    if (l.name.StartsWith("Lamp")) l.intensity = l.name.Contains("WindowFill") ? 450f : l.name.Contains("Window") ? 600f : 45f;   // inverse-square over 6-50 m
                RenderSettings.ambientLight = new Color(0.30f, 0.27f, 0.24f);
            }
            // per-scene light balance and ambient (SceneDef.Lights / Ambient), after the general rules above
            if (def.Lights != null)
                foreach (var l in env.GetComponentsInChildren<Light>(true))
                    foreach (var o in def.Lights)
                        if (l.name == o.Name || l.name.StartsWith(o.Name + "."))
                        { if (o.Intensity >= 0) l.intensity = o.Intensity; if (o.Range > 0) l.range = o.Range; if (o.Color.HasValue) l.color = o.Color.Value; }
            if (def.Ambient.HasValue) { if (outdoor) RenderSettings.ambientSkyColor = def.Ambient.Value; else RenderSettings.ambientLight = def.Ambient.Value; }
            if (def.Fog >= 0) RenderSettings.fogDensity = def.Fog;
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
                if (def.Room && !def.ClearPanes && r.name.Contains("WindowGlass")) continue;   // rooms draw daylit panes unlit (below)
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
            if (def.Room && !def.ClearPanes)
            {
                // daylit window panes: glTF's emissive strength does not come through, so the glass is drawn unlit and bright
                var unlitGlass = Shader.Find("Universal Render Pipeline/Unlit");
                foreach (var r in env.GetComponentsInChildren<Renderer>(true))
                    if (r.name.Contains("WindowGlass") && unlitGlass)
                    {
                        var path = $"Assets/Fable/Materials/{sceneId}_WindowGlass.mat"; Directory.CreateDirectory("Assets/Fable/Materials");
                        var m = AssetDatabase.LoadAssetAtPath<Material>(path); if (!m) { m = new Material(unlitGlass); AssetDatabase.CreateAsset(m, path); }
                        m.SetColor("_BaseColor", new Color(0.92f, 0.94f, 0.96f)); EditorUtility.SetDirty(m); r.sharedMaterial = m;
                    }
            }
            // one baked reflection probe per scene: brass, glass, porcelain and the floor read their surroundings
            var probeGo = new GameObject(hall ? "HallReflectionProbe" : "SceneReflectionProbe"); probeGo.transform.SetParent(env.transform, false);
            var centreAnchor = FindDeep(env.transform, "anchor.hall.centre") ?? FindDeep(env.transform, "anchor.scene.centre"); probeGo.transform.position = (centreAnchor ? centreAnchor.position : env.transform.position) + Vector3.up * 1.4f;
            var probe = probeGo.AddComponent<ReflectionProbe>(); probe.mode = UnityEngine.Rendering.ReflectionProbeMode.Baked; probe.size = hall ? new Vector3(16, 4, 6) : def.Lobby || def.LobbyLook ? new Vector3(6, 3.2f, 5.4f) : new Vector3(30, 12, 30); probe.resolution = 128; probe.boxProjection = hall || def.Lobby || def.LobbyLook; probe.intensity = 1f;
            if (def.Lobby || def.LobbyLook) probeGo.transform.position = (centreAnchor ? centreAnchor.position : env.transform.position) + Vector3.up * 1.5f;
            if (def.Room)
            {
                // fit the probe to the room itself (not the sky dome or far scenery)
                var rs = env.GetComponentsInChildren<Renderer>(true).Where(r => !FlowControllerBackdrop(r.name) && !r.name.Contains("Sky")).ToArray();
                if (rs.Length > 0) { var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); var size = Vector3.Min(b.size, new Vector3(80, 50, 80)); probeGo.transform.position = b.center; probe.size = size; probe.boxProjection = !outdoor; }
            }

            // living scenes: moving water, swaying foliage, fires and candles, positional sounds (docs/LIVING_SCENES.md)
            Debug.Log($"[FableBuild] living {sceneId}: {FableLiving.Apply(env, def)}");

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
            var entrance = ReaderAnchor(env.transform);
            if (entrance) rig.transform.position = entrance.position;
            if (def.ReaderAt.HasValue) rig.transform.position = def.ReaderAt.Value;   // clear floor and an open view (ReaderStarts.json)
            var cameras = rig.GetComponentsInChildren<Camera>(true);
            // far plane: 150 m, or further when the scene reaches further (a harbour's far shore, a 600 m sky dome)
            float reach = 150f;
            foreach (var r in env.GetComponentsInChildren<Renderer>(true))
                reach = Mathf.Max(reach, Vector3.Distance(rig.transform.position, r.bounds.center) + r.bounds.extents.magnitude * 0.75f);
            reach = Mathf.Min(reach * 1.05f, 1200f);
            foreach (var c in cameras) { c.nearClipPlane = 0.05f; c.farClipPlane = reach; c.clearFlags = CameraClearFlags.SolidColor; c.backgroundColor = Color.black; var d = c.GetUniversalAdditionalCameraData(); if (d) { d.renderPostProcessing = false; d.antialiasing = AntialiasingMode.None; } }

            // the reader faces the room's view: anchor.reader.look (rooms) or the lobby's shelf
            var facing = FindDeep(env.transform, "anchor.reader.look") ?? FindDeep(env.transform, "anchor.lobby.shelf");
            if (facing && entrance) { var look = facing.position - rig.transform.position; look.y = 0; if (look.sqrMagnitude > 1e-4f) rig.transform.rotation = Quaternion.LookRotation(look.normalized, Vector3.up); }
            if (def.ReaderYaw.HasValue) rig.transform.rotation = Quaternion.Euler(0, def.ReaderYaw.Value, 0);
            if (def.Lobby)
            {
                var lobbySystems = new GameObject("Fable");
                var lobbyInput = lobbySystems.AddComponent<ReaderController>();
#if FABLE_META_XR
                lobbyInput.LeftHand = lh; lobbyInput.RightHand = rh; lobbyInput.LeftPointer = ovrRig.leftHandAnchor; lobbyInput.RightPointer = ovrRig.rightHandAnchor;
#endif
                var lobby = lobbySystems.AddComponent<LobbyController>(); lobby.Input = lobbyInput; lobby.Head = head; lobby.Env = env.transform;
                lobby.Font = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>("Assets/Fable/Fonts/EBGaramond-Regular SDF.asset");
                var lobbySound = lobbySystems.AddComponent<RoomSound>(); lobbySound.Id = MusicId(def); lobbySound.Ambience = AmbienceOf(def);
                Directory.CreateDirectory(Path.GetDirectoryName(def.Scene));
                EditorSceneManager.SaveScene(scene, def.Scene);
                SetBuildScenes();
                Debug.Log($"[FableBuild] scene saved: {def.Scene} (lobby, {env.GetComponentsInChildren<Transform>(true).Count(t => t.name.StartsWith("book."))} books)");
                return;
            }

            // reading room: a dark floor disc and a soft overhead light around the page
            var reading = new GameObject("ReadingRoom");
            var disc = GameObject.CreatePrimitive(PrimitiveType.Cylinder); disc.name = "FloorDisc"; disc.transform.SetParent(reading.transform); disc.transform.position = rig.transform.position + new Vector3(0, -0.01f, 0); disc.transform.localScale = new Vector3(6, 0.01f, 6);
            var discMat = new Material(Shader.Find("Universal Render Pipeline/Lit")); discMat.color = new Color(0.08f, 0.075f, 0.07f); discMat.SetFloat("_Smoothness", 0.1f); disc.GetComponent<Renderer>().sharedMaterial = discMat; UnityEngine.Object.DestroyImmediate(disc.GetComponent<Collider>());
            var table = GameObject.CreatePrimitive(PrimitiveType.Cylinder); table.name = "DioramaTable"; table.transform.SetParent(reading.transform);
            table.transform.position = rig.transform.position + new Vector3(0, 0.36f, 0.95f); table.transform.localScale = new Vector3(1.5f, 0.36f, 1.5f);
            var tableMat = new Material(Shader.Find("Universal Render Pipeline/Lit")); tableMat.color = new Color(0.16f, 0.12f, 0.09f); tableMat.SetFloat("_Smoothness", 0.35f); table.GetComponent<Renderer>().sharedMaterial = tableMat; UnityEngine.Object.DestroyImmediate(table.GetComponent<Collider>());
            var soft = new GameObject("ReadingLight").AddComponent<Light>(); soft.transform.SetParent(reading.transform); soft.transform.position = rig.transform.position + new Vector3(0, 2.4f, 0.6f); soft.type = LightType.Point; soft.range = 5; soft.intensity = 0.7f; soft.color = new Color(1f, 0.92f, 0.8f); soft.lightmapBakeType = LightmapBakeType.Realtime; soft.shadows = LightShadows.None;

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
            if (def.Room) { flow.RoomOnly = true; flow.RoomBook = def.Book; var roomSound = systems.AddComponent<RoomSound>(); roomSound.Id = MusicId(def); roomSound.Ambience = AmbienceOf(def); }

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

        /// The room's own reader anchor (anchor.reader.entrance, .path, .gate, or any anchor.reader.*).
        public static Transform ReaderAnchor(Transform env) =>
            new[] { "anchor.reader.entrance", "anchor.reader.path", "anchor.reader.gate" }.Select(n => FindDeep(env, n)).FirstOrDefault(t => t)
            ?? env.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name.StartsWith("anchor.reader.") && t.name != "anchor.reader.look");

        /// Where the reader's feet are at the start: the scene's override, else the anchor.
        public static Vector3? ReaderFeet(SceneDef def, Transform env)
        {
            if (def.ReaderAt.HasValue) return def.ReaderAt;
            var a = ReaderAnchor(env); return a ? a.position : (Vector3?)null;
        }

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
            panel.Hint = Make("Hint", 726, 40, 15, FontStyles.Italic, new Color(0.36f, 0.29f, 0.21f), TextAlignmentOptions.Center);
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
            // whole books (tools/ingest_book.py output): StreamingAssets/books/<slug>/book.json
            var books = Path.Combine(repo, "content", "books");
            if (Directory.Exists(books))
                foreach (var dir in Directory.GetDirectories(books))
                {
                    var src = Path.Combine(dir, "book.json"); if (!File.Exists(src)) continue;
                    var to = Path.Combine(dst, "books", Path.GetFileName(dir)); Directory.CreateDirectory(to);
                    File.Copy(src, Path.Combine(to, "book.json"), true); n++;
                }
            // a small index of the books for the lobby shelf (titles and where each chapter starts), so the lobby can say
            // how far the reader has got without parsing four whole books
            if (Directory.Exists(books))
            {
                var index = new Newtonsoft.Json.Linq.JArray();
                foreach (var dir in Directory.GetDirectories(books).OrderBy(d => d))
                {
                    var src = Path.Combine(dir, "book.json"); if (!File.Exists(src)) continue;
                    var bk = Book.Parse(File.ReadAllText(src)); int first = 0;
                    var chapters = new Newtonsoft.Json.Linq.JArray();
                    foreach (var ch in bk.Chapters)
                    {
                        int count = ch.Paragraphs.Sum(p => p.Sentences.Count);
                        chapters.Add(new Newtonsoft.Json.Linq.JObject { ["id"] = ch.Id, ["heading"] = ch.Heading, ["name"] = ch.Name, ["first"] = first, ["sentences"] = count, ["paragraphs"] = ch.Paragraphs.Count });
                        first += count;
                    }
                    index.Add(new Newtonsoft.Json.Linq.JObject { ["slug"] = bk.Slug, ["title"] = bk.Title, ["author"] = bk.Author, ["sentences"] = first, ["chapters"] = chapters });
                }
                File.WriteAllText(Path.Combine(dst, "books", "index.json"), new Newtonsoft.Json.Linq.JObject { ["books"] = index }.ToString(Newtonsoft.Json.Formatting.None)); n++;
            }
            // the highlight menu's offline data: dictionary (Define) and the Peek library (index + clay models)
            var dict = Path.Combine(repo, "content", "dictionary", "webster1913.json");
            if (File.Exists(dict)) { Directory.CreateDirectory(Path.Combine(dst, "dictionary")); File.Copy(dict, Path.Combine(dst, "dictionary", "webster1913.json"), true); n++; }
            var lib = Path.Combine(repo, "content", "library");
            if (Directory.Exists(lib))
                foreach (var f in Directory.GetFiles(lib, "*.json", SearchOption.AllDirectories))
                {
                    var rel = Path.GetRelativePath(lib, f); var to = Path.Combine(dst, "library", rel);
                    Directory.CreateDirectory(Path.GetDirectoryName(to)); File.Copy(f, to, true); n++;
                }
            n += SyncMaps(repo, dst);
            n += SyncBundledRooms(repo, dst);
            AssetDatabase.Refresh();
            MakeMapAssets();
            Debug.Log($"[FableBuild] synced {n} data files into StreamingAssets");
        }

        /// Book maps (docs/MAPS.md, docs/MAPS_HEADSET.md): each content/maps/<slug>/map.json goes to
        /// StreamingAssets/maps/<slug>/map.json (read like book.json), and the images it uses (scroll images, the shared
        /// Earth) to Resources/Maps/<same path>, so Unity compresses them to ASTC (FableTextureImport.MapImage) instead of
        /// the app decoding JPEGs into uncompressed RGB at run time. Height maps, layouts and SOURCE.md stay behind (the
        /// headset does not use them). Files no longer in content/maps are removed from both places.
        static int SyncMaps(string repo, string dst)
        {
            var maps = Path.Combine(repo, "content", "maps");
            var jsonRoot = Path.Combine(dst, "maps"); var imgRoot = Path.Combine(Application.dataPath, "Fable", "Resources", "Maps");
            if (!Directory.Exists(maps)) return 0;
            var keepJson = new HashSet<string>(); var keepImg = new HashSet<string>(); int n = 0;
            foreach (var dir in Directory.GetDirectories(maps))
            {
                var src = Path.Combine(dir, "map.json"); if (!File.Exists(src)) continue;
                var slug = Path.GetFileName(dir);
                Newtonsoft.Json.Linq.JObject doc;
                try { doc = Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(src)); }
                catch (Exception e) { Debug.LogWarning($"[FableBuild] maps/{slug}/map.json does not parse, skipped: {e.Message}"); continue; }
                var to = Path.Combine(jsonRoot, slug, "map.json"); Directory.CreateDirectory(Path.GetDirectoryName(to));
                File.Copy(src, to, true); keepJson.Add(Path.GetFullPath(to)); n++;
                foreach (var v in doc["views"] ?? new Newtonsoft.Json.Linq.JArray())
                    foreach (var key in new[] { "texture", "image" })
                    {
                        var rel = (string)v[key]; if (string.IsNullOrEmpty(rel) || !rel.StartsWith("maps/")) continue;
                        var from = Path.Combine(repo, "content", rel); if (!File.Exists(from)) { Debug.LogWarning($"[FableBuild] maps/{slug}: {rel} is missing"); continue; }
                        var img = Path.GetFullPath(Path.Combine(imgRoot, rel.Substring(5)));
                        if (keepImg.Add(img))
                        {
                            Directory.CreateDirectory(Path.GetDirectoryName(img));
                            if (!File.Exists(img) || new FileInfo(img).Length != new FileInfo(from).Length || File.GetLastWriteTimeUtc(img) < File.GetLastWriteTimeUtc(from)) File.Copy(from, img, true);
                            n++;
                        }
                    }
            }
            void Prune(string root, HashSet<string> keep)
            {
                if (!Directory.Exists(root)) return;
                foreach (var f in Directory.GetFiles(root, "*", SearchOption.AllDirectories))
                    if (!f.EndsWith(".meta") && !keep.Contains(Path.GetFullPath(f))) { File.Delete(f); if (File.Exists(f + ".meta")) File.Delete(f + ".meta"); }
            }
            Prune(jsonRoot, keepJson); Prune(imgRoot, keepImg);
            return n;
        }

        /// Resources/MapAssets.asset: what the map Peek needs at run time (the glTF props, the map shader, the edge mask).
        /// Rewired on every SyncData, so it follows a re-imported props file.
        public static void MakeMapAssets()
        {
            const string path = "Assets/Fable/Resources/MapAssets.asset";
            var a = AssetDatabase.LoadAssetAtPath<MapAssets>(path);
            bool created = !a; if (created) a = ScriptableObject.CreateInstance<MapAssets>();
            a.Props = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Fable/Models/MapProps/map_props.gltf");
            a.EdgeMask = AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Fable/Models/MapProps/textures/scroll_edge_mask.png");
            a.MapShader = Shader.Find("Fable/Map");
            if (!a.Props || !a.EdgeMask || !a.MapShader) Debug.LogWarning($"[FableBuild] MapAssets incomplete: props={(bool)a.Props} mask={(bool)a.EdgeMask} shader={(bool)a.MapShader}");
            if (created) AssetDatabase.CreateAsset(a, path); else EditorUtility.SetDirty(a);
            AssetDatabase.SaveAssets();
        }

        /// Generated reading rooms bundled for Fable's own books that have no hand-built rooms: content/rooms/<slug>/r<N>
        /// (tools/bundle_rooms.py) -> StreamingAssets/rooms/<slug>/r<N>, only the files each package.json lists, plus an
        /// index the app reads synchronously (Resources/BundledRooms.json: titles and each package.json's SHA-256).
        /// A book with hand-built rooms (ReadingRooms.Bundled) is skipped: since 2026-11-15 that is all four later books,
        /// whose generated rooms stay in content/rooms for the record but are no longer shipped.
        static int SyncBundledRooms(string repo, string dst)
        {
            var src = Path.Combine(repo, "content", "rooms"); var to = Path.Combine(dst, "rooms"); int n = 0;
            if (Directory.Exists(to)) Directory.Delete(to, true);
            var index = new Newtonsoft.Json.Linq.JObject();
            if (Directory.Exists(src))
                foreach (var bookDir in Directory.GetDirectories(src).OrderBy(d => d))
                {
                    if (ReadingRooms.Bundled.ContainsKey(Path.GetFileName(bookDir))) continue;
                    var rooms = new Newtonsoft.Json.Linq.JArray();
                    foreach (var roomDir in Directory.GetDirectories(bookDir, "r*").OrderBy(d => d))
                    {
                        var pj = Path.Combine(roomDir, "package.json"); if (!File.Exists(pj)) continue;
                        var m = Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(pj));
                        var outDir = Path.Combine(to, Path.GetFileName(bookDir), Path.GetFileName(roomDir));
                        foreach (var f in (Newtonsoft.Json.Linq.JArray)m["files"])
                        {
                            var rel = (string)f["path"]; var target = Path.Combine(outDir, rel);
                            Directory.CreateDirectory(Path.GetDirectoryName(target)); File.Copy(Path.Combine(roomDir, rel), target, true); n++;
                        }
                        File.Copy(pj, Path.Combine(outDir, "package.json"), true); n++;
                        string sha; using (var h = System.Security.Cryptography.SHA256.Create()) sha = BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(pj))).Replace("-", "").ToLowerInvariant();
                        rooms.Add(new Newtonsoft.Json.Linq.JObject { ["room"] = (int)m["room"], ["title"] = (string)m["title"], ["place"] = (string)m["place"], ["package"] = sha });
                    }
                    if (rooms.Count > 0) index[Path.GetFileName(bookDir)] = rooms;
                }
            Directory.CreateDirectory("Assets/Fable/Resources");
            File.WriteAllText("Assets/Fable/Resources/BundledRooms.json", index.ToString(Newtonsoft.Json.Formatting.Indented) + "\n"); n++;
            return n;
        }

        static bool FlowControllerBackdrop(string n) => FlowController.IsBackdrop(n);

        /// An inward-facing sphere with a baked vertical gradient (pale horizon to soft blue zenith), unlit, for outdoor
        /// scenes whose Blender sky was a world shader that glTF cannot carry. Named SkyDome so it is backdrop: full scale only.
        static void AddSkyDome(Transform env, string sceneId)
        {
            const int lon = 32, lat = 16; const float radius = 60f;   // keep well inside the cameras' far plane (150 m)
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
            GameObjectUtility.SetStaticEditorFlags(go, 0);
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
