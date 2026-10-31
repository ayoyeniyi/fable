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
- **Interpreter** (`interpreter/`, Go): builds, tests pass (validator + HTTP server), and all three baselines validate. Live generation is **untested**: there is no `ANTHROPIC_API_KEY`.
  - `serve` runs each generation detached from the request (`internal/server`): a headset that stops waiting no longer cancels the Claude call, one generation per scene is in flight at a time, and the result is validated again before it is cached. A request waits `--wait` (default 3 s, or its own `waitSeconds`, max 120 s) and otherwise gets **202** `{"status":"generating"}` with `X-Fable-Cache: pending`; the next open of that passage gets the cached live script. Unity treats the 202 body as an unparseable script and falls back, so no client change was needed; passing `waitSeconds` from Unity would let a demo wait for a live result on first open. `--warm` pre-generates every scene at startup when a key is present. `GET /jobs` lists what is generating and cached; `/health` reports whether a key is present.
  - Smoke-tested without a key: `/health` ok, `POST /interpret` 502 in 1.4 s with the SDK's credential message, cache hit 200 in 0 ms, clean shutdown on SIGINT. Binary 17.8 MB.
- **Last verified editor run**:
  - All three loops through the picker, including hall beat 9 at 4× and expanding at 4×.
  - Stepping back eases 4× → 1×.
  - Grab reveal: the bottle held at beat 9 shows sentence 009, and on release it returns to rest at 0.0000 m.
  - Per-passage resume after a cold restart.
  - 0 errors, 0 warnings.
  - Note: grab was exercised by invoking the handlers directly, because there are no hands in the editor.

## Headset session 1 (Quest 2, 2026-10-31, on the owner's Mac)

Installed over USB and run with hands. Findings and fixes, all pushed:
- `FlowController.Start` read the book with `File.ReadAllText`; StreamingAssets live inside the APK, so it threw on device. Now a `UnityWebRequest` (`SceneDirector.ReadStreaming` already did this for manifests).
- `Assets/Oculus/OculusProjectConfig.asset` had `handTrackingSupport: 0` (controllers only): hands were never tracked by the app. Now `1` (controllers and hands). The page shows the active input ("hands", "controllers", or asks for hands) and `[Fable] input: …` is logged.
- The seven hall lamps were Mixed lights at 2.2: realtime per-pixel lighting cost ~25 ms a frame and, with HDR off on the Mobile URP asset, clipped the hall to yellow. Now fully baked at 1.0 and a less orange colour; `lamp.flicker` modulates the `MESH_Flame` emission instead. The editor runs the PC quality level (HDR on), so this never showed on the desktop.
- Dimmed sentences were 38% opacity: unreadable in the headset. Now 62%; hint text 15 pt and darker; hints name the gesture ("right hand: touch thumb and index finger…").
- The page used to trail every head movement with a left-hand offset; it now holds still, centred above the diorama, and re-aims only when the reader turns more than 28° or on a state change (`ReadingPanel.Recentre`).
- Measured: 72/72 fps at the page (5 to 6 ms app) and with the diorama (9 to 10 ms). The full-scale hall is still to measure with baked lamps (it was 36 fps with realtime ones). Medium dynamic foveated rendering is on.
- Pipeline gotcha: an APK built right after a script edit fails with "script class layout is incompatible" unless the editor has actually recompiled; wait for `Library/ScriptAssemblies/Assembly-CSharp.dll` to change first. The Quest will not start a VR activity while the headset is off the face; `am start` is queued until it is worn.
- Captures: `captures/headset/` (both eyes, `adb screencap`), frame logs `session*_frames.log`.

## Headset session 2 (reader's verdict: stripes gone, gestures work and feel right; "nothing to do in the room")

Added after that verdict, built and installed, not yet seen by the reader:
- **Tasks** (`StoryTasks.cs`, added to the Fable systems object at runtime): per sentence, a thing to do in the room. The target glows (emission pulse), the page shows the prompt in bold, and completing it calls `Director.Next()`; pinching still works. Verbs: Touch (hand within reach of the target's renderers, or any `MESH_Door*` for "doors"), Grab (`StoryGrabbable.Held`), BringTo (held target near an anchor or the head), LookAt (head near and facing), GoThrough (head at the little door after the 4x shrink → `FlowController.OpenPassage("queens-croquet-ground")`). Tables for all three scenes live in the class; the hall's chain is door → key → door → look through → bottle → drink → through the door into the garden.
- **One-hand scrolling**: pinch and move up/down or sideways, 5 cm per sentence, on the dominant axis.
- Baselines: every sentence now has a beat (hall 13/52 actions, tea party 17/48, croquet 13/44).

Earlier in the session:

- **Stripes: fixed, confirmed by the reader.** Transparent vertical bands (several per eye) came from the Meta Quest OpenXR feature's depth submission (`m_depthSubmissionMode: 1`) under Vulkan + MSAA; set to `0` in both feature blocks and the bands are gone. Keep it off.
- **One-hand forms** (`ReaderController.cs`): hold the right pinch ~0.9 s without moving = toggle miniature/immersive; hold the left pinch = close the book. Taps stay under 0.35 s; the both-hands gestures still work. Same for the controller triggers.
- **Gesture cues** (`GestureCues.cs`, added to the page at runtime by `FlowController.Start`): a row of looping glyphs under the passage (pinch, hold with a filling ring, slide), one per available action, labelled for hands or controllers, following the flow state. Built from a generated circle sprite, so no scene rebuild was needed; it grows the panel to 906 px.
- **Readings** (interpreter only so far): `variant` 0..3 in `/interpret`, direction notes in `internal/llm/claude.go` (`Readings`), cache per variant. Unity does not send `variant` yet; the plan is a left-hand pinch-and-slide in the miniature to switch readings, the page showing "reading 2 of 4", and the diorama re-running the new script at the same sentence. Needs a live key to be visible.

## Not done / not verified

1. **No headset run.** No Quest has been attached, and on this Mac security software kills and deletes `adb` (it needs whitelisting). There are no headset captures, no frame timings, and no physical test of pinch, grab or comfort.
2. **Live generation untested** (no API key). The plumbing is tested: Unity posts `sceneId` and `readingPosition`, the server answered from its validated cache, and with no key the server returned 502 and Unity fell back to the bundled baseline within 5 s. The page shows where the scene came from ("live interpretation", "interpreter cache", "saved on this headset", "bundled baseline"), so a demo never passes a prepared scene off as live.
3. **Miniature, now fixed in the editor** (it was broken before, though the state strings looked right):
   - Static-batched environment meshes didn't scale with the diorama. Environments are no longer `BatchingStatic`.
   - The reading panel was set to about 600× its size in the miniature.
   - Long passages overflowed the page.

   The diorama now sits about 43° below the eye with a dollhouse cut (`MESH_Ceiling`, the tea party's `MESH_Leaves`), and outdoor scenes stand on a lawn plinth. Untested in a headset: comfort, panel legibility, and whether 43° suits a seated reader. The tea party's main tree trunk is cut along with the far trees, because they share `MESH_Bark`.
4. **Visual tuning from the headset.** Brass reflections, milky glass, the hall is bright for a "dark hall" (lamp 2.2), lightmap resolution. In the croquet ground, the rose tree reads as topiary and Seven partly hides Two. In the tea party, the dappled light is opaque petals.
5. **Triangle budget.** The hall at 61k is double the ARCHITECTURE target; profile on Quest 2 before cutting.
6. **The little door is visible before the curtain appears** (sentence 005). It is architecture, but the curtain could arguably be present from the start.
7. Demo video and unfamiliar-reader tests.
8. **`fx.dust` has no node in the hall export** (`schema/manifest.hall-of-doors.json` lists it; `hall_of_doors.gltf` has no `fx.dust`), so a script that places it does nothing. Either export the mote card or drop it from the manifest; `blender/check_glb_ids.py` reports it.

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
