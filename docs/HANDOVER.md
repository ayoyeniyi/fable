# Fable handover (written 2026-10-31 by the previous Claude Code session)

Read this first, then `README.md`, `docs/PLAN.md`, `docs/ARCHITECTURE.md`, `docs/TOOLING.md`. Everything below was true at the last commit of that session.

## What exists and is verified

- **Hall of Doors environment** (`blender/build_hall_of_doors.py`): fully procedural Blender 5.2 scene, PBR node materials, 7 hanging oil lamps, 12 doors, low curtain, 15-inch door with a real opening to a lit passage, glass table, golden key, DRINK ME bottle. Bakes base colour, roughness and normal maps, merges static meshes by material, exports `hall_of_doors.glb` (44 meshes, 30k tris, 83 MB with 2K PNG textures) with named anchor empties and prop groups. Six art iterations are archived in `captures/blender/` (Cycles renders, not headset).
- **Unity 6000.3.27f2 project** (`unity/Fable`): URP, OpenXR + Meta XR Core SDK 207.0.1 (hand tracking, Touch profiles enabled in code), glTFast 6.20.0, Newtonsoft, TMP with EB Garamond. Compiles clean. `Assets/Fable/Editor/FableBuild.cs` builds everything headless: ConfigureProject, ConfigureXR, BuildScene (from the GLB), BakeLighting, BuildApk, CaptureDesktopPreviews. Lightmaps and a reflection probe bake correctly (lamp glass excluded from occlusion).
- **Runtime** (`Assets/Fable/Scripts`): SceneRegistry (ids from node names), SceneDirector (validated SceneScript execution, deterministic replay, JumpTo resume, reader scale about the reader's feet relative to the room's current scale), ClipPlayer (12 clips), SpatialAudio (reverb zone + pooled 3D sources), ReaderController (right tap next, left tap previous, right pinch-drag scrubs, both hands quick = toggle miniature/immersive, both hands held 1 s = return; controller triggers mirror; keyboard in editor), ReadingPanel (passage with current sentence in ink), FlowController (Reading -> Growing -> Miniature -> Expanding -> Scene -> Shrinking/Returning), ProgressStore (progress.json + script cache in persistentDataPath).
- **Verified in the editor** through the Unity CLI (desktop, no headset): reading page -> hall grows -> beats 1..9 -> auto return; progress file written; interpreter script cache path exercised with the bundled baseline. The miniature flow compiled and ran but the final verified run of it was still in progress when this handover was written; check `captures/desktop/mini_0*.png` and run the play test below.
- **Interpreter** (`interpreter/`, Go 1.24): `fable-interpreter validate|generate|serve`. Sends passage sentences, manifest, previously read context (`contextBefore`) and reading position to Claude (`claude-opus-5-5`, anthropic-sdk-go), validates against the schema and manifest, repairs once, caches validated scripts under `out/cache/`. Tests pass. Binary 17.7 MB, 12 MB RSS. Live generation is **untested**: no `ANTHROPIC_API_KEY` was available.
- **Book data**: `book/passages.json` with sentence ids and prior context for the three scenes; manifests and validated baseline scripts for all three in `schema/` and `scripts/`.

## Not done / not verified (be honest about these)

1. **No headset run yet.** No Quest was attached. Headset captures (`captures/headset/`) are empty and nothing has measured frame time.
2. **No APK yet.** The IL2CPP build compiled and failed only in Gradle packaging because the laptop ran out of disk (the build needs ~11 GB of scratch under `Library/Bee`). On a machine with space: `FableBuild.BuildApk` or `unity command build run --target Android --outputPath out/fable.apk --confirm true`.
3. **Miniature diorama / scrubbing / grab** are coded but hand-untested. Grabbable key and bottle (reveal their sentence) are not implemented.
4. **Only the Hall of Doors has assets.** Tea party and croquet ground have passages, manifests and baselines but no Blender environment.
5. **Known visual defects** on desktop previews: brass needs the baked reflection probe (`Assets/Fable/Scenes/HallReflectionProbe.exr` is now baked, re-check), glass table tint is a little milky, overall lighting is bright for a "dark hall" (lamp intensity 2.2, tune after a headset look), lightmap resolution is 24 texels/m on a 512 atlas (raise once build times are known).
6. **Passage picker UI** is not built; `FlowController.SceneId` is fixed to `hall-of-doors`.
7. **Miniature view needs a dollhouse cut.** In the last play test (`captures/desktop/mini_02_miniature.png`, desktop camera) the diorama is seen from above, so the reader looks at the lit top of the ceiling slab. Hide `MESH_Plaster`'s ceiling part (export the ceiling as its own mesh from Blender, then disable it while `FlowController.Current == Miniature`) and move the reading panel out of the line of sight to the diorama (it currently sits at `Height = 0.28`, right where the eye looks).
8. **Last verified run** (editor, run-in-background on, 123 fps): Reading -> Growing -> Miniature resumed at the saved beat 5 -> beats 6..8 -> Expanding -> Scene -> beat 9 (4x scale) -> Shrinking -> Reading at beat 9, progress.json written, props placed correctly, no runtime exceptions. The reflection probe baked explicitly (`HallReflectionProbe.exr`) but the lightmapper's own "Reflection System" job logged "Failed to bake the reflection probe" three times; the lightmaps themselves are from the earlier successful bake. Re-run `lighting bake` on the new machine and check brass in the headset.

## How to work on it

```bash
git clone https://github.com/ayoyeniyi/fable && cd fable
# Unity CLI (https://unity.com/install.sh) installs editors and drives a running one
unity install 6000.3.27f2 --module android android-sdk-ndk-tools android-open-jdk
unity pipeline install --project-path unity/Fable
unity open unity/Fable --build-target Android
unity status --until-ready --project-path unity/Fable
unity command eval 'Fable.Editor.FableBuild.ConfigureProject(); Fable.Editor.FableBuild.ConfigureXR();' --project-path unity/Fable --timeout 600
unity command eval 'Fable.Editor.FableBuild.BuildScene();' --project-path unity/Fable --timeout 600
unity command lighting bake --project-path unity/Fable       # then: unity command lighting bake_status
unity command build run --target Android --outputPath out/fable.apk --confirm true --project-path unity/Fable
adb install -r unity/Fable/out/fable.apk && adb shell am start -n com.fable.alice/com.unity3d.player.UnityPlayerGameActivity
```

Play-mode smoke test from the CLI (the editor must be allowed to run unfocused: `unity command editor.playmode set_run_in_background --enable true`):

```bash
unity command editor.playmode start --project-path unity/Fable
F='UnityEngine.Object.FindFirstObjectByType<Fable.FlowController>()'
unity command eval "$F.StepInto(); return $F.Describe();" --project-path unity/Fable      # Growing -> Miniature
unity command eval "$F.StepNext(); return $F.Describe();"  --project-path unity/Fable      # beats
unity command eval "$F.StepToggle(); return $F.Describe();" --project-path unity/Fable     # Expanding -> Scene
unity command eval "$F.StepReturn(); return $F.Describe();" --project-path unity/Fable     # back to the page
unity command console get --level error --tail 10 --project-path unity/Fable
```

Gotchas learned the hard way: the Pipeline server restarts after every recompile, so run `unity recompile` then `unity status --until-ready` before driving the editor; `recompile` can report success with `compilationFailed: true`, so also check `unity command console get --level error`; capture `save_path` must be inside the project; without an HMD the OVR centre eye sits at the floor (FlowController lifts it to 1.25 m in that case); MonoBehaviour dictionaries are not serialized, so SceneRegistry rebuilds in Awake; URP asset shadow flags are read-only properties (use SerializedObject); TMP Essential Resources must be imported once (`TMP Essential Resources.unitypackage` from `Packages/com.unity.ugui/Package Resources`).

Blender: `blender -b -P blender/build_hall_of_doors.py -- --out out/hall --render --bake --export --samples 160 --res 1600 --tex 2048` (about 25 minutes on an M-series GPU; `--quick --render` for a 5-minute look). Never write to a folder named `build/` in this repo owner's environment.

## Order of work from here (see docs/PLAN.md)

1. Attach a Quest, build and install the APK, capture (`adb shell screencap`), profile (OVR Metrics Tool or `adb shell dumpsys SurfaceFlinger --latency`), fix what the headset shows. Target 72 Hz on Quest 2.
2. Hand-test the miniature flow and scrubbing; add grabbable key and bottle (Meta Interaction SDK, `com.meta.xr.sdk.interaction.ovr` is already installed) that reveal their sentence.
3. Run `fable-interpreter generate --scene hall-of-doors` with an API key, compare to the baseline, then `serve` and point `SceneDirector.InterpreterUrl` at it from the headset.
4. Passage picker on the reading panel; the other two environments in Blender with the same pipeline.
5. Demo video under three minutes, unfamiliar-reader tests.
