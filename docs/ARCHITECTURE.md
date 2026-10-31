# Fable architecture

```
 reader (Quest, hands)                 interpreter (Go, laptop or server)           Claude
 ┌──────────────────────────┐          ┌──────────────────────────────┐           ┌──────────┐
 │ ReadingPanel (TMP, EB    │  pinch   │ POST /interpret               │  prompt   │          │
 │ Garamond) shows passage  │────────▶ │  passage sentences + manifest │─────────▶ │ scene    │
 │ FlowController           │          │  → SceneScript JSON           │ ◀──────── │ director │
 │  Reading→Unfold→Scene→   │ ◀──────  │  validate → repair once →     │  JSON     │          │
 │  Return                  │  script  │  return only valid scripts    │           └──────────┘
 │ SceneDirector            │          └──────────────────────────────┘
 │  beat index = pure       │          falls back to scripts/<scene>.baseline.json bundled in the APK
 │  function of the room    │
 │ ClipPlayer (12 clips)    │          Blender (headless)
 │ SpatialAudio (reverb     │          build_hall_of_doors.py → geometry, PBR node materials,
 │  zone + 3D sources)      │          lamps, anchors, prop groups → bake → merge → hall_of_doors.glb
 │ SceneRegistry: anchors,  │ ◀──────  (names are the manifest ids: anchor.table.top, prop.golden-key,
 │  assets, lights by name  │  GLB     door.little, Lamp3_Light ...)
 └──────────────────────────┘
```

**Contract.** `schema/scene-script.schema.json` is the only thing the model may produce. A SceneScript is a list of beats; each beat cites one sentence id and carries up to eight actions from a closed vocabulary: `place`, `move`, `remove`, `animate` (clip ids per target), `light`, `sound`, `readerScale`. Every id must exist in `schema/manifest.<scene>.json`. The Go interpreter and the Unity client each validate independently; Unity never trusts the wire.

**Determinism.** Going backwards replays beats 0..n-1 instantly from a reset room, so the room is always a function of the beat index. There is no accumulated state to drift.

**Scale.** Alice shrinking is implemented by scaling the environment root about the point on the floor under the reader's head over 3 to 8 seconds. The reader never moves; the world grows. The validator rejects faster scale changes.

**Assets.** Everything is generated: geometry and materials by `blender/build_<scene>.py` (exported as `.gltf` + textures so Unity compresses them), textures by baking those materials, sounds by `audio/synth_sfx.py`. No downloaded models or samples. EB Garamond is OFL.

**Build.** `FableBuild.cs` exposes ConfigureProject, ConfigureXR, BuildScene, BakeLighting, BuildApk, CaptureDesktopPreviews as `-executeMethod` entry points, and the same calls work live through the Unity CLI's Pipeline package (`unity command eval 'Fable.Editor.FableBuild.BuildScene();'`). Quest settings: Android, ARM64, IL2CPP, Vulkan, ASTC, URP with MSAA 4x, single-pass instanced stereo, OpenXR with the Meta XR feature and hand tracking.

**Budgets (Quest 2).** Target about 35k triangles and under 50 meshes per environment. The tea party (35k / 26) and croquet ground (36k / 42) meet it; the hall is 61k / 44 and is the first to cut if Quest 2 profiling demands it. Textures are compressed to ASTC on import (6x6 colour and data, 4x4 normals), with mipmaps, 2K max, plus one 4K ground per scene. Lights are baked (Mixed) with no realtime shadows; there is one baked reflection probe per scene and 6 pooled spatial audio sources. APK: 175 MB for all three scenes.
