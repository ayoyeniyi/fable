# Fable handover (updated 2026-10-31, second Claude Code session)

Read this first, then `README.md`, `docs/PLAN.md`, `docs/ARCHITECTURE.md`, `docs/TOOLING.md`. Everything below was true at the commit that last touched this file. "Verified" always says where: **editor** (Unity play mode on a Mac, desktop camera, no HMD) or **headset**. Nothing has been verified on a headset yet.

## What exists and is verified

- **Three environments**, all procedural Blender 5.2 scripts with the same pipeline (geometry, PBR node materials, baked base colour / roughness-metal / normal maps, static meshes merged by material, named anchors and prop groups), exported as `.gltf` + `.bin` + `textures/`:
  - `blender/build_hall_of_doors.py`: 60,942 tris, 44 meshes. (Earlier docs said 30k; the exported file has always been 61k.)
  - `blender/build_mad_tea_party.py`: 35,344 tris, 26 meshes. Hatter, March Hare and Dormouse are sculpted props, not rigs.
  - `blender/build_queens_croquet_ground.py`: 35,750 tris, 42 meshes. Card gardeners Two, Five, Seven; rose tree with white and red roses.
  - `blender/check_glb_ids.py <file.gltf|.glb> --manifest ... --baseline ...` confirms every manifest and baseline id is a node. The tea party and croquet ground pass. The hall fails only on its older names (lamps named `Lamp*`, `hall.centre`, no `fx.dust` node), which `SceneRegistry` maps on purpose.
  - Cycles renders are in `captures/blender/<scene>/` (Blender renders, not Unity).
- **Unity project** (`unity/Fable`, 6000.3.27f2, URP, OpenXR + Meta XR Core 207.0.1, Interaction SDK, glTFast). `FableBuild.cs` provides:
  - `ConfigureProject`, which sets Android/IL2CPP/ARM64/Vulkan/ASTC and Input System only (Active Input Handling "Both" is unsupported on Android).
  - `ConfigureXR`.
  - `BuildScene`: one Unity scene per passage, the hall first.
  - `BakeLighting`: per-scene lightmaps and a reflection probe.
  - `BuildApk`, which writes `unity/Fable/out/fable.apk`.
  - `SyncData`, which copies book, manifests and baselines into StreamingAssets and runs before builds.
  - Build steps refuse to run in play mode.
- **Texture import** (`FableTextureImport.cs`): each image's role comes from the `.gltf`.
  - Normal maps: ASTC 4×4, linear.
  - Roughness-metal and occlusion: ASTC 6×6, linear.
  - Colour: ASTC 6×6, sRGB.
  - Mipmaps on, 2048 cap; the one 4K ground per scene stays at 4096.
  - Measured result: texture data went from 1.5 GB to 267 MB, and the **APK is 175 MB** (it was 400 MB when the textures came embedded in `.glb` files and glTFast imported them uncompressed).
- **APK builds** in about 1.5 minutes. The first Gradle run on a new machine may fail to resolve `dl.google.com`; retry it.
- **Runtime**
  - **Passage picker** on the reading page: drag the right pinch or tap left to choose, tap right to open. Opening another passage loads its Unity scene and goes straight into the miniature.
  - **Progress per passage** (`progress.json`). The app boots into the hall scene, but the page offers the passage read last, "where you left it".
  - **Miniature → immersive → return.** The reader's size is part of the beat state: the diorama never changes size, expanding arrives at the current size (4× after DRINK ME), stepping back past that beat eases the room back over 3 s, and leaving the scene stops any scaling.
  - **Grabbable golden key and DRINK ME bottle** (Interaction SDK hand pinch/palm and controller grip, immersive view only). Holding one shows the sentence that introduces it (manifest `introducedBy`). Letting go returns it to where the script placed it. A pinch that grabs never also turns a page.
  - **31 clips.** Tea party and croquet: lean/nod/bow/turn, breathe, rattle, pour, and roses reddening (the tint clears on rewind).
  - **24 synthesised sounds** (`audio/synth_sfx.py`), including two garden ambiences. The "No room!" shout is a formant chorus, not speech.
  - **Outdoor scenes:** sky dome and far scenery show only at full scale. A gradient dome is generated when the export has none (the croquet ground).
- **Spoiler guard.** Manifests carry `introducedBy` (asset → first sentence) and `readerScaleFrom`. The Go and C# validators both reject:
  - placing, moving or animating an asset before its sentence;
  - a size change before `readerScaleFrom`;
  - a size change faster than 3 s.

  It caught the hall baseline rattling the little door two sentences before Alice finds it, and that action is removed.
- **Interpreter** (`interpreter/`, Go): builds, tests pass, and all three baselines validate. Live generation is **untested**: there is no `ANTHROPIC_API_KEY`.
- **Last verified editor run**:
  - All three loops through the picker, including hall beat 9 at 4× and expanding at 4×.
  - Stepping back eases 4× → 1×.
  - Grab reveal: the bottle held at beat 9 shows sentence 009, and on release it returns to rest at 0.0000 m.
  - Per-passage resume after a cold restart.
  - 0 errors, 0 warnings.
  - Note: grab was exercised by invoking the handlers directly, because there are no hands in the editor.

## Not done / not verified

1. **No headset run.** No Quest has been attached, and on this Mac security software kills and deletes `adb` (it needs whitelisting). There are no headset captures, no frame timings, and no physical test of pinch, grab or comfort.
2. **Live generation untested** (no API key). `SceneDirector` sends only `sceneId` to `/interpret`; it does not send the reading position yet.
3. **Miniature needs a dollhouse cut.** The hall diorama is seen from above, so the reader sees the ceiling slab. Export the ceiling as its own mesh and hide it while in the miniature. Also move the reading panel out of the line of sight (`Height = 0.28`).
4. **Visual tuning from the headset.** Brass reflections, milky glass, the hall is bright for a "dark hall" (lamp 2.2), lightmap resolution. In the croquet ground, the rose tree reads as topiary and Seven partly hides Two. In the tea party, the dappled light is opaque petals.
5. **Triangle budget.** The hall at 61k is double the ARCHITECTURE target; profile on Quest 2 before cutting.
6. **The little door is visible before the curtain appears** (sentence 005). It is architecture, but the curtain could arguably be present from the start.
7. Demo video and unfamiliar-reader tests.

## How to work on it

```bash
git clone git@github.com:ayoyeniyi/fable.git && cd fable
curl -fsSL https://unity.com/install.sh | bash             # Unity CLI (if its CDN 404s, use Unity Hub --headless install)
unity install 6000.3.27f2 --module android android-sdk-ndk-tools android-open-jdk
unity pipeline install --project-path unity/Fable
unity open unity/Fable --build-target Android
export UNITY_PROJECT_PATH=$PWD/unity/Fable                # the CLI wants --project-path BEFORE the subcommand; the env var avoids that
unity status --until-ready
unity command eval 'Fable.Editor.FableBuild.ConfigureProject(); return "ok";' --timeout 600   # then restart the editor once (input handling)
unity command eval 'Fable.Editor.FableBuild.BuildScene(); Fable.Editor.FableBuild.BakeLighting(); return "ok";' --timeout 3600
unity command eval 'Fable.Editor.FableBuild.BuildApk(); return "ok";' --timeout 3600
adb install -r unity/Fable/out/fable.apk && adb shell am start -n com.fable.alice/com.unity3d.player.UnityPlayerGameActivity
```

Environments: run `blender -b -P blender/build_<scene>.py -- --out out/<scene> --bake --export --tex 2048`, which takes 1–2 minutes each. Add `--render` for Cycles stills. Then copy the `.gltf`, the `.bin` and the referenced `textures/` into `unity/Fable/Assets/Fable/Models/<Scene>/`. Sounds: `blender -b --python audio/synth_sfx.py -- --out unity/Fable/Assets/Fable/Resources/Audio`.

Play-mode test from the CLI (FlowController has test hooks: `StepInto`, `StepNext`, `StepBack`, `StepToggle`, `StepReturn`, `StepChoose(dir)`, `Describe()`, `ChosenId`):

```bash
unity command editor.playmode set_run_in_background --enable true
unity command editor.playmode start
F='UnityEngine.Object.FindFirstObjectByType<Fable.FlowController>()'
unity command --result-only eval "$F.StepInto(); return $F.Describe();"
```

Poll `Describe()` until it reaches the state you expect; don't rely on fixed sleeps. Under memory pressure, play-mode start and scene loads stall for many seconds.

## Gotchas

- The Pipeline server restarts after every recompile, so run `unity status --until-ready` afterwards. `recompile` can succeed with `compilationFailed: true`; check `console get`.
- `?? AddComponent` never adds anything in Unity, because of Unity's fake-null; use `TryGetComponent`.
- `OVRComprehensiveInteractionRig` brings a locomotion stack. BuildScene deletes it and cleans the dangling references; the reader never moves.
- Editor-noise files to leave out of commits:
  - `Assets/Resources/DevAgentSettings.asset`, which **holds an access token; an older one is already in history**;
  - `UnityConnectSettings.asset`;
  - the EB Garamond SDF atlas;
  - `PerformanceTestRun*`;
  - `.utmp/`;
  - `runInBackground` in `ProjectSettings.asset`.
- GitHub rejects files over 100 MB and git-lfs is not installed; keep textures as separate files.
- Never write to a folder named `build/` in this owner's environment.
