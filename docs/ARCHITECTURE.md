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

**Assets.** Everything is generated: geometry and materials by `blender/build_<scene>.py` (exported as `.gltf` + textures so Unity compresses them), textures by baking those materials, sounds by `audio/synth_sfx.py` and `audio/synth_rooms.py`. No downloaded models or samples; the only downloaded media are two CC0 music recordings (`tools/fetch_music.py`, `CREDITS.md`) and the cover images (`content/covers/SOURCE.md`). EB Garamond is OFL.

**Build.** `FableBuild.cs` exposes ConfigureProject, ConfigureXR, BuildScene, BakeLighting, BuildApk, CaptureDesktopPreviews as `-executeMethod` entry points, and the same calls work live through the Unity CLI's Pipeline package (`unity command eval 'Fable.Editor.FableBuild.BuildScene();'`). Quest settings: Android, ARM64, IL2CPP, Vulkan, ASTC, URP with MSAA 4x, single-pass instanced stereo, OpenXR with the Meta XR feature and hand tracking.

**Input for a reader in one place.** `ReaderController` turns hands and controllers into pinches, taps and drags. A pinch is first offered to the controls in `ReaderController.Claimers`, in this order:
1. the view toolbar
2. the library board
3. the page handles
4. a Peek model

The first control to take the pinch owns it until release; only unclaimed pinches turn pages, highlight, grab or open books. `ViewControls` turns the rig about the head (30° steps). `ReadingPanel` is world-anchored and recentred on request. Rooms follow `docs/ENVIRONMENT_BRIEF.md`.

**Chapter experiences.** Step In is per chapter (`docs/CHAPTER_EXPERIENCES.md`):
- **The service.** `interpreter/internal/chapters` keeps a persistent, bounded queue of one job per chapter, started when the reader enters it. Each job runs plan (Claude, text through the chapter's end only) → script → Blender render → validate → package. Its status answers carry no content.
- **The headset.** `ChapterExperiences` tracks completion apart from preparation, fetches and checks packages into sealed storage, and refuses them until the chapter is finished.
- **Adaptation.** Experiences adapt the six built environments (`schema/environments.json`) by mood and haze, plus staging scripts where a manifest exists, and never change a shared room.

**The personal library.** `Library` (a scene-surviving singleton) owns:
- the imported books' index
- the upload server (`UploadServer`: HTTP on the local Wi-Fi, code-gated)
- imports, done on a worker thread into a staging folder and swapped in

`EpubImport` and `PdfText`/`PdfImport` produce the same `Book` shape and id scheme as `tools/ingest_book.py`, so the reader, highlighting, Search and progress are shared code. `PdfPages` draws PDF pages with the platform renderer: Android `PdfRenderer` on the headset, PDFKit in the editor. Details: `docs/LIBRARY.md`.

**Budgets (Quest 2).** Target about 35k triangles and under 50 meshes per environment. The lobby (10k / 35), Kansas farmhouse (30k / 28), Calypso's cave (34k / 34), Glumdalclitch's room (30k / 31), tea party (35k / 26) and croquet ground (36k / 42) meet it; the hall is 61k / 44 and is the first to cut if Quest 2 profiling demands it. Textures are compressed to ASTC on import (6x6 colour and data, 4x4 normals), with mipmaps, 2K max, plus one 4K ground per scene. Lights are baked (Mixed) with no realtime shadows; there is one baked reflection probe per scene and 6 pooled spatial audio sources. The six rooms of 2026-11-03: poppy field 46.6k / 12, Emerald throne room 37.7k / 12, Odysseus's ship 37.3k / 22, Ithaca hall 26.1k / 31, Lilliput 36.3k / 17, Laputa 45.4k / 23 (three over the 35k target, none over 65k; none profiled on the Quest yet). APK: 519 MB with all fourteen scenes (it was 343 MB with eight). Generated rooms for uploaded books are not in the APK: unlit glTF packages of 1 to 3 MB each, fetched at runtime (docs/GENERATED_ROOMS.md).

**Interpret protocol.** `POST /interpret {sceneId, readingPosition, noCache?, waitSeconds?}`. A valid cached script answers `200` with `X-Fable-Cache: hit`. Otherwise the server starts (or joins) the single generation for that scene, which runs on its own 8-minute context, and waits up to `waitSeconds` (server default 3 s, cap 120 s): a finished script answers `200` with `X-Fable-Cache: miss`, a failure `502`, and anything still running `202 {"status":"generating","retryAfterSeconds":15}` with `X-Fable-Cache: pending`. The reader is never kept on a blank page by a slow model: the client shows its cached or bundled script, and the live one is there the next time the passage opens. Every script is validated twice server-side (interpreter output, then before caching) and once more in Unity.

**Readings (parallel universes).** One passage can be staged several ways. `POST /interpret` takes `variant` (0 is the plain reading; 1 to 3 add a direction note: scale and the body, theatrical and lively, spare and literal), each generated and cached separately (`out/cache/<scene>.v<n>.json`) and reported in `X-Fable-Variant` / `X-Fable-Variants`. The vocabulary and the validators are the same for every reading, so a variant can never show something the text has not reached. `fable-interpreter generate --variant n` writes one to disk.
