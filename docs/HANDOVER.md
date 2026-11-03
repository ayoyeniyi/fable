# Fable handover (updated 2026-11-02: chapter-based Step In, stationary controls, the personal library)

Read this first, then `README.md`, `docs/PLAN.md`, `docs/ARCHITECTURE.md`, `docs/TOOLING.md`. Everything below was true at the commit that last touched this file. "Verified" always says where: **editor** (Unity play mode on a Mac, desktop camera, no HMD) or **headset**. Nothing has been verified on a headset yet.

## What exists and is verified

**2026-11-03: three rooms per book, and three generated rooms per uploaded book.**
- Six new rooms (Oz: poppy field, Emerald throne room; Odyssey: Odysseus's ship off the Sirens, the hall at Ithaca; Gulliver: Lilliput at giant scale, Laputa), each a `blender/build_*.py` written by its own subagent to `docs/ENVIRONMENT_BRIEF.md`, Unity scenes built and baked (`FableBuild.Scenes`, with lighting overrides for the throne room and Ithaca). Blender renders in `captures/blender/<room>/`, desktop previews in `captures/desktop/desktop-preview_<Scene>_room.png`. Each room's remaining compromises against the brief are listed in its commit message; the common ones: over the 35k target (three rooms), stylised foliage, static water.
- Found by two subagents: a GPU (Metal) bake under memory pressure returns black without an error, and a metal's diffuse-colour bake is black. Their scripts bake on the CPU and zero Metallic for the colour pass; `build_calypsos_cave.py`'s gold and Glumdalclitch's metal probably need the same fix (the "metal renders black" fault in the brief).
- Generated rooms: `docs/GENERATED_ROOMS.md`. Verified in the editor against the live service with Pride and Prejudice: planning, three rooms built (4 to 7 minutes each on a busy Mac), fetched with checksums, loaded at runtime (226 ms, 33k triangles), listed in both menus.
- Chapter experiences: chapters found to have no place are planned again when `schema/environments.json` changes (six new place environments).
- **Not on the headset:** the APK (519 MB) is built but the headset was disconnected; frame time of the six rooms, runtime glTF loading, texture memory.

- **Seven environments** (the lobby, three Alice rooms and one room each for Oz, the Odyssey and Gulliver), all procedural Blender 5.2 scripts with the same pipeline (geometry, PBR node materials, baked base colour / roughness-metal / normal maps, static meshes merged by material, named anchors and prop groups), exported as `.gltf` + `.bin` + `textures/`:
  - `blender/build_lobby.py`: 10,058 tris, 35 meshes. The room the app opens in (step 6 below).
  - `blender/build_kansas_farmhouse.py`: 30,343 tris, 28 meshes (the grass blades are 16.6k of them). Oz.
  - `blender/build_calypsos_cave.py`: 33,772 tris, 34 meshes. The Odyssey.
  - `blender/build_glumdalclitchs_room.py`: 30,424 tris, 31 meshes, built at 12x scale. Gulliver.
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

## The product now: a reader for whole books (brief of 2026-10-31, supersedes the one-book framing)

Fable is a VR reader for four public-domain books (Alice, Oz, the Butler Odyssey, Gulliver), read cover to cover on a floating page inside one of three rooms per book, with a highlight menu (Define, Translate, Search, Peek, Step In). Scope tiers and the step order are in `docs/PLAN.md`. Status by step:

**Step 4, content pipeline and whole-book reading: built, editor-verified; page legibility not yet measured on the headset.**
- `tools/ingest_book.py` (stdlib Python) turns a Standard Ebooks EPUB or a Gutenberg text into `content/books/<slug>/book.json` (chapters → paragraphs → sentences, ids like `alice:c01.p016.s01`) and `SOURCE.md` (URL, SHA-256, edition, licence, the SE colophon with the cover painting). `tools/books.json` lists the four sources. Standard Ebooks has only the Bryant Odyssey, so the Odyssey is Gutenberg #1727 (Butler). Front/back matter, licence blocks and every note and note mark are dropped; authors' own prefaces and epigraphs stay. Verse keeps its line breaks (`lineBefore`). Counts: alice 12 ch / 1,407 sentences / 26.6k words; oz 24 / 2,117 / 39.3k; odyssey 24 / 3,859 / 117.0k; gulliver 39 / 2,620 / 102.6k. Downloads cache in `out/sources/`.
- `tools/map_passages.py` links each Step In passage sentence (`hall-of-doors:004`) to its book sentence and gives each passage a `bookFrom`/`bookTo` range (all matches ≥ 0.95).
- `FableBuild.SyncData` copies the books to `StreamingAssets/books/<slug>/book.json` (2.5 MB; APK 179 MB).
- `BookReader.cs` replaces the passage picker. Pages are measured by a hidden TextMeshPro copy (exact at four sizes: 17 / 19.5 / 22.5 / 26 pt on the 0.001-scale page), ragged right, running head, chapter title on its first page, footer with page, pages left in the chapter and % of the book. Contents (chapters, then bookmarks), bookmark ribbon, text size; progress per book in `progress.json` (`Books[slug]`: page-anchor sentence, bookmarks, size). Re-layouts keep the reader's sentence on the page. Only the next page is laid out, at most one a frame.
- `PagePointer.cs`: the hand's pointer pose / controller ray / editor mouse onto the page, with a cursor dot. Pinch on a control presses it; pinch elsewhere turns the page; left pinch goes back. Consistent with the point-and-pinch model below.
- Step In from the page: when the page holds a staged passage, "Step in ›" (or hold right pinch) opens its miniature at the beat for the page's first sentence (across Unity scenes for the tea party and croquet ground); closing returns to the page at the sentence reached. `FlowController.OpenBook(slug)` switches books (the lobby will call it).
- Verified in the editor (play mode, desktop camera): all four books paginate (medium: alice 121 pages, oz 171, odyssey 420, gulliver 396; 2.0-3.6 ms per page on the M-series Mac); every control through the pinch path (`PagePointer.TestRay`); resume after restart; resize without drift; Step In and return in the hall and across scenes to the croquet ground; 0 errors. Desktop previews: `captures/desktop/desktop-preview_HallOfDoors_book-*.png`.
- **Not verified:** legibility and comfort of the page for 20 minutes on the Quest 2 (the brief requires measuring this on the headset); per-page layout cost on the Quest (estimate 8-15 ms; one layout happens on each page turn and a chapter-back or text-size change lays out up to a whole chapter at once); the pointer dot's usability with hand pointer poses. Test hooks: `FlowController.Reader.Describe()`, `.Press("contents"|"size"|"bookmark"|"entry:N")`, `.NextPage()`, `.GoToSentence(id)`, `.PageCensus()`.

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

## Input model after headset session 3 (the reader's words: "the absolute easiest way")

The reader found two-hand gestures unintuitive and reached the garden by accident. The model is now **point and pinch acts on what you point at**, with one hand, seated:
- `Locomotion.cs` (added to the Fable systems object at runtime): a ray from the hand's SDK pointer pose (or the controller) with a landing disc. Pinch on the full-size floor = teleport there; on the diorama floor = step in at that spot (`FlowController.ExpandAt`); on the little door = go through to the linked place (`FlowController.Links`: hall → garden → tea party → hall); on a big door = it rattles (locked). Pointing at nothing leaves the pinch to the page (next sentence) via `ReaderController.TapInterceptor`.
- Walking at full scale: arm-swing (both hands pumping in opposite phase, works seated) or the controller thumbstick. No vignette yet; watch comfort.
- Still available but never required: right hold = step inside/back to the table, left hold = close the book, both-hands gestures.
- `GestureCues` leads with Point and Swing glyphs; hints lead with pointing.
- Tasks (`StoryTasks`) accept point-and-pinch as touching, aiming the held key at the door, and a steady gaze to go through, so none needs the reader to walk.

**Live interpretation runs.** Key in `~/.config/fable/env` on the owner's Mac (never in the repo). `fable-interpreter serve --addr 0.0.0.0:8787 --warm --wait 20s` generated all three scenes on the first attempt (9 to 12 beats each, 20 to 28 s) once the prompt spelled out the exact JSON shape (`internal/llm/claude.go`) and the repair round named every unknown key (`script.UnknownFields`). The headset reads the server URL from `/sdcard/Android/data/com.fable.alice/files/interpreter.txt`; the page then says "scene: interpreter cache". Observed in the first live hall script: Claude placed `fx.dust` (no mesh in the export) and did not use `readerScale` on the DRINK ME sentence; prompt nudges for both are the next tuning step.

**Step 5, highlight menu, Define, Search and Peek: built, editor-verified; nothing of it measured on the headset, and live clay generation not run (no API key on that machine).**
- **Selecting** (`Highlighter.cs`): a right pinch that starts on the body text and either moves the ray at least one word and lasts over 0.18 s, or crosses three words, or holds still on a word for 0.5 s, becomes a highlight; it calls `ReaderController.SuppressCurrentPinch()` so it is not also a page turn, scrub or hold. Anything shorter is the old page turn. Word hit-testing reads the body's TMP layout (`BookReader.WordAt`, `Selection`, `SelectionRects`), and the highlight is drawn as one tinted bar per line (no re-layout). On release a ring of five petals opens around the last word (each petal kept on the page); the flow sends right pinches to `Highlighter.HandleTap` first, a left pinch closes, and scrubbing / hold-to-step-in are off while the ring or a card is up.
- **Define**: `content/dictionary/webster1913.json`, built by `tools/ingest_dictionary.py` from Gutenberg #29765 (public domain; source and SHA in its `SOURCE.md`): the 8,245 headwords the four books use plus 4,238 inflected forms; 89% of the books' distinct words. Phrases define the head word first. Known gaps: some common words are missing from that transcription ("rabbit"), some senses carry OCR slips ("shsrl"), names are absent and the card says so.
- **Search**: whole words, case-insensitive, over sentences up to `BookProgress.Furthest` (new: the furthest sentence ever on a page; later matches are neither shown nor counted). Six results on the card; pinch one to go there. The book's normalised text is built off the main thread at load.
- **Peek**: (a) `content/library/peek-library.json`: the four hall props (cloned from the loaded room, metalness capped because the room's reflections are off while reading) and ten clay models (`content/library/clay`, written by Claude in this session as fixtures, two or three per book; every quoted label checked against the text up to its sentence by `fable-interpreter mock --check`). The matcher (`PeekLibrary.Match`) only offers an entry once the highlight has reached its `notBefore` sentence. (c) Otherwise `POST /peek` to the interpreter (`Director.InterpreterUrl`), polling 202s for up to 30 s; Claude gets the book up to the end of the highlight only (`books.TextUpTo`); the server's cache serves the model made from the most text that does not pass the reader. `ClayBuilder.cs` builds the primitive tree with fixed per-shape triangle costs that match the Go validator (checked: `ClayBuilder.CheckCounts()`). The model stands in front of the card with its own point light (the room's lights are off while reading), turns slowly, labels in a column with leader lines.
- **Step in** from the ring stages the passage from the highlight's first sentence (`FlowController.StepInAt`).
- **Measured in the editor** (M-series Mac, play mode; the Quest 2 will be several times slower): dictionary parse 289 ms and library parse, both off the main thread; ring opens 0.1-3.7 ms after release; Define 2.5-3.8 ms; Search over the whole Odyssey ~1 ms (60-96 ms before the off-thread index); matcher 0.1-0.7 ms; prop copy 1-10 ms; clay build 0.2-0.9 ms per model (3.9 ms for the first, which makes the shared meshes), 16 ms with file load; interpreter cache hit over localhost 38 ms. Clay fixtures are 144-5,376 triangles. APK 182 MB (+3 MB, the dictionary).
- **Verified in the editor**: hold, drag, release and petal pinch through the real path (`PagePointer.TestRay` plus `Highlighter.TestPinch`); a quick pinch does not highlight; Define, Search (and jumping to a result), Peek from a hall prop, from a clay fixture, from the interpreter's cache, and the interpreter's failure message; Step In from a highlight opens the miniature at that sentence's beat (6/13 for "curtain") and returns to the page; the spoiler rule on a library entry ("mushroom" at its first mention is not offered the mushroom-and-Caterpillar model) and on the server cache (a request from an earlier sentence is not served the later model); 0 console errors; the APK builds. Desktop previews: `captures/desktop/desktop-preview_HallOfDoors_{highlight-menu,highlight-drag-menu,define-curtain,search-key,peek-golden-key,peek-white-rabbit}.png`.
- **Not verified**: whether pinch-drag selection is accurate with real hand rays (word height is about 2 cm at the page's distance; the hand ray jitters), the thresholds (0.18 s / 0.5 s) on real pinches, label legibility and the Peek light's cost on the Quest, live clay generation and its latency (needs `ANTHROPIC_API_KEY`: run `fable-interpreter mock --book alice --passage "little golden key" --phrase "golden key"` and time it), and the matcher on phrases nobody has tried. Translate was built on 2026-11-03 (see "Not done") and has not been tried in the editor or on a headset. Test hooks: `FlowController.Highlight.Select(phrase)`, `.Choose("define"|"translate"|"search"|"peek"|"chapters")`, `.Describe()` (includes `translate=` status), `.CardText`, `.WordWorld(phrase)`; `FlowController.Menu.Open("sound")` then `.Press("translate")` cycles the language.

**Step 6, the lobby: built, editor-verified; not tried on the headset.**
- **The room** (`blender/build_lobby.py`, same pipeline as the other environments): a panelled reading room, 5.6 x 5 m, with an oak bookcase on the far wall. The four books stand face out on a velvet-backed display shelf at chest height (oldest first: Odyssey, Gulliver, Alice, Oz), each under its own brass picture lamp; filler shelves of plain spines above and below; armchair, side table with an oil lamp, two sconces, a night window, a rug where the reader stands. 10,058 triangles, 35 meshes (budget 35k / 50). The books are separate nodes `book.<slug>`; their cover planes use the cover JPEG directly (not baked). Baked lights: `Lamp0` table lamp, `Lamp1-4` picture lamps, `Lamp5-6` sconces. Blender renders: `captures/blender/lobby/`.
- **Covers** (`content/covers`, made by `blender -b -P tools/make_covers.py`, every source in `content/covers/SOURCE.md`): Alice, Oz and Gulliver are the Standard Ebooks covers taken unchanged from the EPUBs (CC0 design; paintings by Shishkin, Koch and Vibert are public domain, as named in each colophon). The Odyssey has no SE edition, so its cover is composed in the SE layout from Arnold Böcklin's *Ulysses and Calypso* (1882, public domain, Wikimedia Commons, file hash recorded): a 2:3 crop of Odysseus alone on the rocks (Calypso is outside the crop), titled in League Spartan Bold (SIL OFL 1.1, font and licence in `content/covers/fonts`, used only to render the image).
- **Interaction** (`LobbyController.cs`): the app now opens in the lobby (first scene in the build). Either hand's ray (the mouse in the editor) makes the book it hits slide forward 6 cm and its card light up; a pinch from the hand pointing at it lifts the book off the shelf to the reader (0.7 s) while the reading scene loads, then the page opens on that book where it was left (`FlowController.PendingBook`). A cream card clipped to the shelf edge under each book shows the chapter reached, its name and the share of the book read, from `ProgressStore` and a small books index written by Sync Data (`StreamingAssets/books/index.json`), so the lobby never parses a whole book. On the page, a new **‹ shelf** control (top row, beside contents) returns to the lobby.
- **Each book opens in its own room** since step 7 (below). A room missing from the build falls back to the Hall of Doors scene's quiet reading space.
- **Measured in the editor** (M-series Mac): pinch on the shelf to the book on the page 1.1-1.4 s, including the 0.7 s flight (Alice 1,359 ms, Odyssey 1,095 ms). Lobby lightmaps: 2 maps. APK 206.8 MB (+25 MB: the lobby's baked textures and the four covers), built in 111 s with the scenes Lobby, HallOfDoors, MadTeaParty, QueensCroquetGround.
- **Verified in the editor**: hover and pinch through the real path (`LobbyController.TestRay` / `AimAt` and the pinch handler itself), opening Oz, Gulliver, Alice and the Odyssey, Alice keeps her Step In (rabbits-house at chapter IV) and the others show none, **‹ shelf** returns to the lobby, cards show saved progress, 0 console errors. Desktop previews: `captures/desktop/desktop-preview_Lobby_{lobby-shelf,lobby-hover-alice,lobby-hover-oz,lobby-cards-close,lobby-opening-oz}.png` and `desktop-preview_HallOfDoors_oz-page-shelf.png`.
- **Not verified**: anything on the headset: frame rate in the lobby, whether the books are easy to hit with a hand ray from the rug (2.5 m; the colliders are 3 cm generous), whether the shelf cards are legible at that distance (they are clear from 1.4 m in the editor; from the rug they are small), the room's brightness in the lenses, and the flight of the book feeling right. A left-hand pinch opens a book only when the left hand's own ray is on it; in the editor only the right hand (mouse) has a ray.

**Step 7, a room for each of the other three books, sound, music and credits: built, editor-verified; not tried on the headset.**
- **Rooms** (the scripts were written by three Claude Code subagents in parallel, following `build_lobby.py`; all procedural, nothing downloaded; Cycles stills in `captures/blender/<room>/`):
  - **Kansas farmhouse** (Oz ch. I): one room of weathered gray boards, open to the rafters, the trap door to the cyclone cellar in the middle of the floor, rusty cookstove, dish cupboard, table with oil lamp, chairs, the big bed and Dorothy's little bed; the door open on the gray prairie, grass bent by the north wind, a gray-green storm sky. The reader faces the open door.
  - **Calypso's cave** (Odyssey Book V, Butler's words): the reader stands inside the mouth looking out through the vine loaded with grapes to the four rills among violet beds, the grove of alder, poplar and cypress, and the sea; behind them the hearth fire and the loom with its golden shuttle.
  - **Glumdalclitch's room** (Gulliver Part II, c09-c11): a girl's bedroom at 12x scale; the reader stands on the table (9 m up) among her sewing (pincushion with pins, needle and thread, thimble of cordial, linen), the doll's cradle in its drawer, the travelling box with its door and gimlet holes, a giant candlestick; bed, cabinet, chair and leaded window beyond the table edge. No people or animals in any room.
- **Reading in the room** (`FlowController.RoomOnly`, set by `FableBuild` for `SceneDef.Room`): the room stays in view and the page floats in it (`PanelInRoom`: 1.1 m out, a little below the eyes); same page, pointer, highlight menu and shelf control; no Director passage, no miniature, no tasks, no Step In (P1). The rig faces `anchor.reader.look`. The lobby sends oz / odyssey / gulliver to `KansasFarmhouse` / `CalypsosCave` / `GlumdalclitchsRoom`.
- **Lighting in Unity**: Kansas gets its own storm settings (dim filtered sun, gray-green ambient and haze); the cave's hearth, the farmhouse lamp and stove are baked warm point lights; Glumdalclitch's room scales light ranges by 12 and needs intensities of 45 (candle) to 600 (window spot) because baked light falls off with the square of tens of metres; its window panes are drawn unlit because glTF emissive strength does not come through.
- **Sound** (`RoomSound.cs`, `Resources/Audio/amb.<scene>` and `music.<scene>`): synthesised ambience by `audio/synth_rooms.py` for the lobby (room tone, slow clock), Kansas (low wailing north wind, grass, creaking boards, a whistle from the south), Ogygia (surf, four rills, cedar fire crackle, sea-crows and small birds) and the giant room (deep room tone, a huge slow clock, wind at the casement). Music: Satie's Gymnopédie No. 1 in the lobby and Handel's Harmonious Blacksmith in Gulliver's room (CC0 recordings from Wikimedia Commons, SHA-1 checked by `tools/fetch_music.py`; the Satie file is FLAC in Ogg, which Unity cannot import, so it is decoded to WAV), and a sparse Dorian lyre composed by `synth_rooms.py` for the cave. Kansas has the storm and no music. Music streams (`FableAudioImport.cs`); ambience is Vorbis decompressed on load. I could not listen to any of it: levels, spectra and loop seams were checked numerically only. Alice's hall still has no sound while reading.
- **`CREDITS.md`**: every book edition, the dictionary, the covers and their paintings, the typefaces, the music with performers and hashes, and the software.
- **APK 342.9 MB** (was 206.8 MB), built in 48 s with all seven scenes. 95% of the build is textures: each 2048 normal map is 5.3 MB as ASTC 4x4 with mips and each room has a 4K ground (9.5 MB). Within the Quest's 1 GB APK limit; if size matters, capping normal maps at 1024 (except grounds) is the largest saving.
- **Measured in the editor**: shelf pinch to page 0.96-1.15 s for the new rooms. Lightmaps baked in 5-48 s per room.
- **Verified in the editor**: from the lobby, each of the four books opens in its room with its sound (and music where it has one), the page reads, the shelf control returns; 0 console errors. Desktop previews: `captures/desktop/desktop-preview_{KansasFarmhouse,CalypsosCave,GlumdalclitchsRoom}_room-*.png`.
- **Known faults**: metal reads black in Unity (the golden shuttle, the brass candlestick; the Blender bakes, not the probe); the linen in the giant room is dark; Kansas grass is spiky up close with a seam at 9 m; the cave's outside reads as a boulder, not a hillside; Glumdalclitch's cradle shows only its top from where the reader stands.
- **Not verified**: anything on the headset, including frame rate in the three rooms (all inside the 35k budget, but Kansas grass and the cave's leaf cards are alpha-free geometry, untested for cost), comfort standing on a 9 m table, page legibility against the bright cave mouth, and how the sound mixes in the headset.

**Live interpreter on this Mac (2026-10-31, evening).** An API key now lives in `~/.config/fable/env` here (created in the Anthropic Console for this machine; never in the repo). First live Peek: `mock --book alice --passage "little golden key" --phrase "golden key"` made a valid 6-part, 600-triangle model with 3 labels on the first attempt in 13.5 s (claude-opus-5-5). The server runs as `fable-interpreter serve --addr 127.0.0.1:8787 --wait 20s` with `adb reverse tcp:8787 tcp:8787`. The headset runs Fable in a secondary account (user 10), whose app folder adb cannot write, so `interpreter.txt` cannot be pushed there; the app now defaults to `http://127.0.0.1:8787` on Android when that file is absent (a refused connection falls back to the bundled script at once). The old Fable on the headset (signed on another machine, installed for user 0) was uninstalled to install this Mac's build; its progress was lost.

**Step In per chapter (2026-11-02, owner's brief): built, verified in the editor against the live preparation service; the APK builds; not on the headset (not connected).** Full design, states, spoiler boundary and measurements: `docs/CHAPTER_EXPERIENCES.md`.

**What changed:**
- The page's **Step in ›** and the highlight menu's Step in are gone. The fifth petal is **Chapters**.
- Entering a chapter queues its experience once, on the service (`interpreter/internal/chapters`, persistent queue in `out/chapters/`). Each job is planned by Claude from text through the end of that chapter only, then scripted (Alice's rooms), rendered in Blender (`blender/render_experience_thumb.py`), validated and packaged.
- The headset (`ChapterExperiences.cs`) fetches each package into a sealed folder, checks it, and keeps it locked until the chapter is finished.
- After a chapter's last page comes an end card: **continue reading ›**, **finish and step into this chapter ›** (only when ready), or the preparation stage, or **try preparing it again**.
- The lobby's book choice opens a **book menu** (resume reading, reading rooms, chapter experiences).
- The bar under the page has **chapters / rooms / sound** (`BookMenu.cs`; sound settings saved in `Prefs`).
- An experience is either scripted (Alice: miniature, then the room, with the prepared script) or a **place** (a room with the chapter's mood and its moment on the page). **‹ return to reading** restores the saved page and undoes the mood.

**Interpreter boundary change (deliberate):** chapter planning sees text through the end of the target chapter, before the reader has finished it. Its outputs are held back:
- status answers carry stages only
- the headset refuses titles, pictures and packages for uncompleted chapters at the loading boundary
- Peek keeps the highlight-end boundary

**Verified in the editor**, play mode against `fable-interpreter serve` with the real key and Blender:
- **Oz, start to finish:**
  - Entering chapter 1 queued one job. It was delivered sealed and stayed **Locked**: title and package refused.
  - The end card offered step-in only once ready. Continue unlocked it, and the tile showed the Blender thumbnail and title.
  - Entering chapter 2 started chapter 2's job.
  - The place experience applied the storm mood, showed the moment's 21 sentences, and returned to the saved page (Chapter II, first sentence).
- **Restart:** the state was kept, and revisiting chapter 1 reused the package (generated once).
- **Service stopped:** chapter 3 showed "waiting to resume: the preparation service can't be reached" while reading went on. It resumed when the service came back, and was judged **unavailable** (the cornfield), still locked as unread.
- **Alice:** "finish and step into this chapter" opened the miniature with the prepared 9-beat script ("prepared chapter experience"), stand in the room, and return to the saved place.
- **Mark as read:** asks twice, unlocks into **Preparing**, and the completed chapter went ahead of an earlier-queued one on the service.
- **Lobby book menu:** "chapter experiences ›" opened the room with the chapters card.
- **Console:** 0 errors.
- **Go tests** (`internal/chapters`): one job per chapter, completed first, restart resumes, a bounded queue, failure then retry, unavailable never packaged, and the planner prompt holds nothing after the chapter.

**Measured** (live, the owner's Mac):

| Kind of chapter | Time |
|---|---|
| Scripted (Alice) | 36 to 58 s of service work (plan 5, script 24 to 44, Blender 3 to 8) |
| Place | 5 to 13 s (plan 3 to 10, Blender 2 to 3) |
| No fitting room | 5 to 8 s |

Package to headset: 3 to 6 s when already built, 18 s and 42 s from first request. Desktop previews: `desktop-preview_KansasFarmhouse_{chapter-end-card,chapter-experiences-menu,experience-place-oz-c01}.png`, `desktop-preview_HallOfDoors_experience-scripted-alice-c01.png` (the editor camera faces a door at the hall's standing spot: the existing Expand keeps the rig's facing; check the facing on the headset), `desktop-preview_Lobby_book-menu-alice.png`.

**Limitations:**
- No new environments are generated: chapters without a fitting built room are "no place built yet".
- Imported books have no experiences.
- Place experiences have no staged interactions.
- Mood on the headset cannot change baked light.
- The service is the owner's Mac.

**Not verified on the headset:** everything above, including polling over `adb reverse`, sealed storage, and the end card's buttons with a hand ray.

**Stationary controls (2026-11-01, owner's brief: a reader who stays in one place, seated or standing): built, editor-verified; not tried on the headset.**
- **Every essential action has a visible control.** The pinch-and-pull-apart (both hands) Step In, the hold-right Step In, the hold-left close and the left-hand drag-to-turn are off (`ReaderController.LegacyGestures = false`). Step In is the highlight menu's label or the page's **Step in ›**.
- **View toolbar** (`ViewControls.cs`, in every reading scene and the lobby):
  - Buttons: **‹ turn**, **recentre**, **turn ›**, plus the way back from wherever the reader is:
    - Miniature: **‹ return to reading**, **stand in the room ›**
    - Scene: **‹ return to reading**, **back to the table**
    - Lobby: **face the shelf**
  - A turn rotates the rig 30° about the tracked head, on the vertical axis only, with no translation, pitch or roll. The step is saved in `Prefs.TurnDegrees`; headset testing should confirm it.
  - Each pinch fires once, on its first frame, and holding never repeats.
  - The controller's left stick turns one step per push, in every state.
  - The bar docks under the page and floats low in front of the reader once they turn away. Over the Alice reading room's diorama table it rises and comes forward rather than sinking into it.
- **Pinch claiming** (`ReaderController.Claimers`): a pinch that starts on the toolbar, a page handle, a Peek model or the library board belongs to that control. It is never also a page turn, scroll, highlight, grab, or book opened on the shelf behind.
- **The page stays put in the room.** It no longer trails the head; **recentre** brings it back. It still follows teleports and walking (`ReadingPanel.Shift`) and a change of eye height while the reader faces it.
- **Page handles** (`PanelHandles.cs`): a bar under the page (pinch, hold and move) and a corner at bottom right (pinch, hold, and drag out or in, 0.7x to 1.6x). The size is saved in `Prefs.PanelScale`. Both brighten on hover and while held.
- **Peek**: point at the model, pinch and hold, and move the hand. Sideways turns it round (0.25 m of hand travel is a full turn); up and down tips it. The model lifts 5% while held and stays as left; the slow automatic spin stops once it has been touched. The card says "Pinch and hold it to turn it." While a model is being made, the card counts real seconds.
- **Hints**: one-time tips under the bar (`ViewControls.Tip`, remembered in `Prefs.HintsShown`). The gesture row and the page's hint line no longer mention hold gestures.
- **Verified in the editor:**
  - turns, through the real button path: the head did not move (0.0000 m) and the rig turned exactly 30°
  - recentre, with the bar docking again
  - Step In → stand in the room → back to the table → return to reading, using only bar buttons
  - the move handle and the resize handle (scale saved)
  - Peek grab: a 79° turn from a 6 cm hand move, with no spin after release
  - the lobby bar and face the shelf
  - 0 console errors

  Desktop previews: `captures/desktop/desktop-preview_HallOfDoors_{stationary-toolbar,peek-grab}.png`, `desktop-preview_Lobby_lobby-toolbar.png`.
- **Not verified (needs the headset and a first-time reader):** whether a new reader finds the bar, the handles and the grab without coaching; whether hand-ray jitter makes the 6.6 cm buttons hard to hit; comfort of 30° steps; the palm-up shortcut menu (not built: the bar is always reachable, so it was left out).

**Personal library and book uploads (2026-11-01/02): built, editor-verified end to end over HTTP; the APK builds; not tried on the headset (it was not connected when the build finished).** Full description, formats, limits and failure handling: `docs/LIBRARY.md`.
- **The library board** (`Scripts/Library/LibraryPanel.cs`): the lobby's board shows bundled and imported books with covers (drawn ones when missing), badges, progress, continue, paging and remove (asks first).
- **Sending a book:** "+ add a book" starts the headset's upload page (`UploadServer.cs`, port 8642, code-gated) on the local Wi-Fi.
- **Importing** (`Library.cs`): EPUB (`EpubImport.cs`) or PDF (`PdfText.cs` + `PdfImport.cs`) runs on a worker thread, in a staging folder, and moves into place in one step.
- **Reading:**
  - Imported books read in **LibraryRoom** (the lobby room in room mode, `SceneDef library-room`).
  - PDFs have a page view (`PdfPages.cs`: Android `PdfRenderer` on the headset, PDFKit via `tools/pdf_page.swift` in the editor) and a text view where the text is reliable.
  - Peek and Step In are greyed with a reason for imported books.
- **Test set:** in the session scratchpad, rebuilt by the commands in `docs/LIBRARY.md`'s spirit.
  - EPUBs: Standard Ebooks Oz, Gutenberg Moby-Dick (EPUB 2), Gutenberg Pride and Prejudice (EPUB 3 with images, 24 MB), Moby-Dick with its cover stripped.
  - PDFs: a Chrome-made PDF (CID fonts + ToUnicode), a Quartz-made PDF (Core Text), a hand-written Type 1 PDF with no ToUnicode, a two-page scanned (image-only) PDF.
  - Failures: a DRM-marked EPUB, a truncated EPUB, a fake Word file named .pdf, a .mobi, a .txt.

**Editor results** (every file sent through the real HTTP server in play mode):

| File | Result |
|---|---|
| Standard Ebooks Oz | 25 chapters / 2,117 sentences: **identical to `tools/ingest_book.py`** |
| Moby-Dick | 140 chapters, several per file, split at the contents' anchors |
| Pride and Prejudice | 63 chapters, Gutenberg header and licence dropped |
| Moby-Dick without its cover | drawn cover |
| Chrome PDF | 12 pages / 240 sentences, paragraphs joined across lines |
| Quartz PDF | 9 / 145 |
| Type 1 PDF | curly quotes from WinAnsi, a hyphenated word rejoined |
| Scanned PDF | 2 pages, no text, "pages only" |
| Duplicate | not added again |
| DRM EPUB | refused: encrypted (DRM) |
| Truncated EPUB | refused: "not a complete zip archive" |
| .mobi and .txt | refused before transfer, with Kindle or plain-text advice |
| Interrupted transfer (raw socket) | "stopped after … nothing was added"; partial file deleted |
| 400 MB declared | 413 before any byte is stored |
| Board closed | 409 |
| Five wrong codes | the code changes |

Imports take 0.4 to 1.0 s on the Mac from the first byte, including the 24 MB EPUB.

- **Reading checks in the editor:**
  - An imported EPUB opens from the board in LibraryRoom; Define and Search work, and Peek and Step In are greyed with a reason.
  - PDF page view draws real pages (82 to 95 ms a page via PDFKit on the Mac).
  - Page turns, bookmarks, contents by tens of pages, and the text view at the same page all work, with Define in the text view and back again.
  - The scanned PDF is page view only, with the footer saying why.
  - After a restart, "continue" reopens the PDF at page 3 with its bookmark.

  Desktop previews: `desktop-preview_Lobby_library-{board,add-card}.png`, `desktop-preview_LibraryRoom_{imported-epub-menu,pdf-page-view,pdf-scanned}.png`.
- **Not verified on the headset:**
  - **Wi-Fi and the device:** the server on the Quest's Wi-Fi, and that its Wi-Fi address is found (a UDP-connect trick, Dns fallback), with a real phone on the same network.
  - **PDF rendering on device:** `PdfRenderer` through JNI, including the null-argument `render` call, page draw time on the XR2 (estimate 50 to 150 ms at 1300 px), and texture memory (about 7 MB a page, three kept).
  - **The board:** cover decode time and legibility at 0.9 m.
  - **Storage:** free-space reporting through `java.io.File.getUsableSpace`.
  - **Scale:** a 150 MB PDF read into memory (the parser holds the whole file).

  Known limits: no OCR; PDF text is one chapter per page; multi-column PDFs may interleave; no Kindle, Word or plain text.

**Environment brief (2026-11-01).** `docs/ENVIRONMENT_BRIEF.md` is now the standing rule for every room, whether built by script, subagent or generation. The step 7 rooms predate it, and their known faults are listed there.

## Not done / not verified

1. **Headset coverage is partial.** Sessions 1-3 above ran on a Quest 2. The step 7 build was installed and launched on 2026-10-31 but not yet tried by a reader. Not yet seen on a headset:
   - the stationary controls
   - the library board, uploads and PDF rendering

   **Still owed:** the first-time-reader check the owner asked for. A new reader must select a book, read, look behind them, return to the page, use Peek, enter Step In and return to reading, all without coaching and without leaving their place. The session is scripted step by step in `docs/READER_TEST.md` (2026-11-03): eight things the reader should do unprompted, fifteen checks for what has never been worn, the recording commands, and which numbers to pull. Usability issues found then go here, and `adb` is not present on the build Mac in every session (security software has removed it before).
2. **Live generation** works on the owner's Mac (see "Input model after headset session 3"). The pinch-to-miniature latencies the brief asks for are measured on the Mac in `docs/LATENCY.md` (2026-11-03): cache hit about 1 ms; a whole passage live is 20 to 31 s on Opus and 10 to 25 s on Haiku (hall of doors, mad tea party, 3 runs each); Peek "golden key" 14 to 16 s Opus, 9 to 10 s Haiku. Opus validated first time in 18 of 18 runs, Haiku in 12 of 15 (two repaired, one failed with a `502`). Not measured from the headset, and the headset never waits for a live script anyway: `SceneDirector` times out at 8 s and shows the cached or bundled script while the live one fills the cache for next time. Streaming and the 20 s fallback rule are still not built. The page shows where the scene came from ("live interpretation", "interpreter cache", "saved on this headset", "bundled baseline").
3. **Miniature, now fixed in the editor** (it was broken before, though the state strings looked right):
   - Static-batched environment meshes didn't scale with the diorama. Environments are no longer `BatchingStatic`.
   - The reading panel was set to about 600× its size in the miniature.
   - Long passages overflowed the page.

   The diorama now sits about 43° below the eye with a dollhouse cut (`MESH_Ceiling`, the tea party's `MESH_Leaves`), and outdoor scenes stand on a lawn plinth. Untested in a headset: comfort, panel legibility, and whether 43° suits a seated reader. The tea party's main tree trunk is cut along with the far trees, because they share `MESH_Bark`.
4. **Visual tuning from the headset.** Brass reflections, milky glass, the hall is bright for a "dark hall" (lamp 2.2), lightmap resolution. In the croquet ground, the rose tree reads as topiary and Seven partly hides Two. In the tea party, the dappled light is opaque petals.
5. **Triangle budget.** The hall at 61.6k is nearly double the ARCHITECTURE target; profile on Quest 2 before cutting.
6. **The little door is visible before the curtain appears** (sentence 005). It is architecture, but the curtain could arguably be present from the start.
7. **Demo video: stills cut done, headset cut owed.** `out/demo/fable-demo-stills-cut.mp4` (2:26, 1080p, rendered 2026-11-03 from `demo/`, a Remotion project; `demo/README.md` says how) tells the story from the captures with every shot labelled Blender render, Unity editor preview or Quest 2 capture, and staged shots labelled cached script (no capture is tied to live generation, so none says so). It is to be replaced shot for shot with `adb shell screenrecord` footage from headset session 4 (`docs/READER_TEST.md`). The unfamiliar-reader test is item 1.
8. **Translate is built and verified in the editor, not on a headset.** On 2026-11-03 the petal went from greyed ("coming later") to live: `POST /translate` and `fable-interpreter translate` (`interpreter/internal/server/translate.go`, `internal/llm/translate.go`; Go tests cover the cache, the 202 path and the refusals under a fake model). Verified the same day in play mode through the hooks (`Highlight.Select("Alice")`, `Choose("translate")`, `Menu.Open("sound")`, `Press("translate")`): with no interpreter URL the card says "Translate needs the interpreter; Define and Search work offline"; with the Mac's server it showed "Alicia · Spanish · translated by the interpreter" in about 3 s, then "from its cache" on the second pinch; the sound tab's "Translate to" row cycles Spanish to French and persists; 0 console errors. Not verified: anything on a headset, the card with long translations, and glyphs for Arabic, Hindi and Chinese (EB Garamond SDF has none; TMP fallback fonts are needed before those three languages are offered on device). The editor has no default interpreter URL (only Android builds default to 127.0.0.1:8787 over adb reverse); set `Director.InterpreterUrl` at runtime to test live.
9. **`fx.dust` is exported now (2026-11-03).** `blender/build_hall_of_doors.py` adds a group `fx.dust` with one mesh `DustMotes`: 7 lamps x 24 motes, each two crossed quads, 4 to 8.5 mm, scattered in a cone under each shade; 672 triangles, one draw call; material `M_DustMote` is flat (alpha 0.42, emissive 1.6, `alphaMode BLEND`, in `NO_BAKE` so it is exported as factors, not baked). The hall is 61,614 triangles / 46 meshes. `scripts/hall-of-doors.baseline.json` places it at `hall-of-doors:002` (the row of lamps) with a fade; the baseline validates. The HallOfDoors scene was rebuilt and rebaked from the new export the same day and the node is in the scene (checked in play mode). Still open: how the specks read on the Quest, and whether 0.42 / 1.6 is the right strength. `check_glb_ids.py` still lists the pre-existing hall naming (`lamp.row`, `light.garden`, `scene.centre` are mapped in `SceneRegistry`; `light.fill` has no light object at all).

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
- **Android builds use High managed stripping.** Newtonsoft builds Fable's data classes by reflection, so the stripper removed their constructors and the getters of anonymous types. On the headset (never in the editor) request bodies went out as `{}` and replies could not be read: Peek failed with `book "" is not one of …`, and chapter preparation either failed with `unknown book ""` or re-sent the same request forever. Fixed on 2026-11-03 by `Assets/link.xml`, which keeps `Assembly-CSharp` whole, and by building request bodies with `JObject`. Verified on the headset: chapter preparation now requests, polls and settles. Any new JSON type in Fable's own code is covered by `link.xml`, but a type in a new assembly (asmdef) needs adding to it.
- GitHub rejects files over 100 MB and git-lfs is not installed; keep textures as separate files.
- Never write to a folder named `build/` in this owner's environment.
