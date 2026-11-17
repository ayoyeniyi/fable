# Chapter experiences (Step In, per chapter)

Step In used to stage whichever passage was on the page, or the passage a highlight fell in. It is now **one
experience per chapter**:

- It is prepared in the background while the reader reads that chapter.
- It is locked until they finish the chapter.
- It can be entered and revisited afterwards.

Peek is unchanged: it inspects a highlighted phrase at once and keeps the stricter reading-position boundary.

## Lifecycle

1. **Entering a chapter starts one job.** The reader's page moves into chapter N (`BookReader.ChapterEntered`), and
   `ChapterExperiences.Enter` queues chapter N once. It never queues the whole book and never prepares a later
   chapter speculatively. Entering N+1 never cancels N.
2. **The job runs on the preparation service** (`fable-interpreter serve`, `interpreter/internal/chapters`). The
   service keeps a persistent queue (`out/chapters/jobs.json`) and runs one job at a time, completed chapters first.
   It is bounded: 12 jobs waiting or running, and more answer 429 so the headset retries. Each job goes through the
   whole pipeline before it is called built (see [The pipeline](#the-pipeline)).
3. **Delivery.** The headset polls, fetches the package and thumbnail into a staging folder, checks them, and swaps
   them into `persistentDataPath/experiences/<chapter>/`.
   - The checks: right chapter, a scene in this build, the script against the same validator and manifest as any
     other script, a moment inside the chapter, and the thumbnail's SHA-256.
   - Only then is preparation "ready". The headset reports the end-to-end time (`POST /chapters/delivered`).
4. **Completion is separate.** It is recorded only by Continue (or "finish and step into this chapter") on the
   end-of-chapter card after the last page, or by **mark as read**. Mark as read is offered for locked chapters
   before the one being read, and asks twice. Nothing is inferred from gaze or time.
5. **What the reader sees** is `ChapterExperiences.StateOf`:

| State | Condition | Tile |
|---|---|---|
| Locked | not completed (whatever preparation has done) | a padlock and "Chapter 3", nothing else |
| Preparing | completed, not ready | an open padlock, "unlocked · <stage>" (no title, no picture) |
| Available | completed and ready | the Blender thumbnail and the title; pinch to enter |
| Failed | completed, preparation failed | "couldn't be prepared · pinch to try again"; completion and reading are untouched |
| Unavailable | completed, no built place fits | "no place built for this chapter yet"; nothing unrelated is substituted |

A finished job never unlocks an unread chapter, and finishing a chapter never makes an unfinished job ready.
Unlocked experiences stay available for revisiting; nothing is regenerated.

All of it survives restarts: the headset's `experiences/state.json` and the service's `jobs.json`. A job that was
mid-pipeline when the service stopped is queued again. With no connection, jobs say "waiting to resume: the
preparation service can't be reached" and resume by themselves. Reading never waits for any of it.

## Where it appears

- **Lobby.** Choosing a book (a board tile, a shelf book, or "continue") opens its book menu before any room loads:
  - **Resume reading**
  - **Reading rooms**: its own room and the library
  - **Chapter experiences**: how many are ready or being prepared, and a button into the list
- **Beside the page.** The bar under the page has **chapters**, **rooms** and **sound**. These open the book menu
  card (`BookMenu.cs`):
  - the chapter tiles
  - reading rooms
  - music on or off, and room sound off / quiet / normal (saved in preferences)
- **The highlight menu's fifth petal** is **Chapters**, in place of the old passage Step In. Peek stays.
- **End of a chapter.** After the last page comes a card:
  - **continue reading ›** is always there.
  - **finish and step into this chapter ›** appears only when the experience is ready.
  - Otherwise the card gives the preparation stage, and **try preparing it again** after a failure.

  Nothing moves the reader on its own: not the end of a chapter, and not a job finishing (a job finishing only
  shows a short note on the bar).
- **Inside a place experience** there is no page (owner, 2026-11-17): the reader stands in the chapter's place and
  looks around. The stationary bar stays (turn, recentre) with **‹ return to the book**, and a caption
  ("Chapter III · The Wager at Whist") shows on the bar for 4.5 s. Stepping in fades to black and back (0.6 s out,
  0.8 s in, `StepInFade.cs`).
  - **Another room** (a room in the app, or a downloaded scene room): it loads in the dark and fades in; at the end
    the reader goes back to the reading room they stepped in from.
  - **The reader's own room**: so that something visibly happens, the reader is moved to another viewpoint with clear
    floor, facing `anchor.scene.centre` (or another `anchor.*`, else the reading view): candidates 2.5-5 m around each
    focus and around the reading start, checked with a floor ray and a body capsule against temporary colliders
    (`FlowController.FindViewpoint`, the runtime version of `Editor/FableReaderStart.cs`). The mood is made
    perceptible even when it is the room's own (`ExperienceMood.Apply(.., distinct: true)`): a light haze in the
    mood's tint, the scene-room colour grade, the ambience a little forward. Nothing garish.
  - Returning reverses it all: fade, the saved rig pose and reading position (not the moment), mood restored.

## Downloadable scene rooms (2026-11-17)

Chapter rooms that are not in the APK (`docs/SCENE_ROOMS.md`, `docs/SCENE_ROOMS_PIPELINE.md`).

- **Which place:** for the first ten chapters of each book `schema/scene_rooms.json` decides
  (`Catalog.Planned`): its existing room, or the download environment published for its new room. Until that room is
  published the chapter is **unavailable** ("its place (…) is still being built"), answered without Claude; it is
  never staged in a merely similar room. Asking again (re-entering the chapter, or Retry) re-plans it once the room is
  published (`Service.plannedPlaceReady`). Later chapters keep the `chapters` lists in `schema/environments.json`.
- **The package** of a download environment carries `sceneRoom` {id, version, file, bytes, sha256}; its thumbnail is
  the room's own Blender view (`content/scene-rooms/<id>/view.jpg`), so the server renders nothing for it.
  `unityScene` is `LibraryRoom`, which hosts the room.
- **Delivery:** the experience is "ready" only once its room is on the headset too. `ChapterExperiences.Fetch`
  downloads the zip through `SceneRooms` with the stage "downloading the place (4.2 of 12.6 MB)" and a time estimate
  from the download rate on the chapter tile, checks the SHA-256, unpacks into `persistentDataPath/scene-rooms/<id>/`
  (entries confined to the folder, swapped in whole). The cache is capped at 600 MB, least recently used first, never
  the room in use. Entering a chapter also prefetches the published rooms of that chapter and the next
  (`GET /scene-rooms/index.json`). A room evicted since is fetched again at step-in, with the progress on the bar.
- **Showing it:** `SceneRoomView` loads `room.gltf` with glTFast in the library-room scene, hides the library, and
  puts `anchor.reader.entrance` under the reader facing `anchor.reader.look`. Materials are `Fable/SceneRoom`:
  base colour × the Blender-baked light texture (UV 1), alpha cut-out cards in the AlphaTest queue, `veg.*` sway and
  `cloth.*` billow in the room's wind (`LivingScene`), `water.*` gets `Fable/Water`, `fx.*` a fire (flames, embers,
  crackle), `sound.*` a positional loop (6 at most), and the room's ambience replaces the library's.
  `Resources/SceneRooms/` keeps the shaders and their variants in the build (`Fable/Scene Room Resources`).
- **Not done at runtime:** an ocean's swell subdivision and a river's flow directions (the water moves by its detail
  normals only), `flame.*` meshes and flickering lights; fog does not apply to scene-room surfaces (the mood works
  through the colour grade there).
- **Verified in editor play mode** (2026-11-17, local service): frankenstein:c28 pointed at the arctic stand-in
  (`sr-arctic-ice`) was planned in 9 s, the 2.9 MB zip downloaded, checked and unpacked, the room loaded in 962 ms
  (42k triangles, 1 billow, 1 water, 3 sounds) with the storm grade, and "return to the book" went back to the
  garret at the saved page. Same-room step-ins: frankenstein:c08 in the garret (moved 2.3 m, night haze) and
  eighty:c03 in the Reform Club (dusk haze, caption), both restored exactly. Desktop previews:
  `captures/unity/step-in/desktop-preview_*.png`. Not verified on a headset.

## The pipeline

Each job goes through these stages, timed and logged (`chapters <id>: done after … (queueWait, planning, scripting,
rendering, validating, packaging)`):

1. **Planning (Claude).** The planner gets:
   - the book's text **only through the end of the target chapter**: the chapter with sentence ids, plus about
     3,000 characters before it
   - the environment catalogue (`schema/environments.json`)
   - the titles and places of earlier chapters' experiences, which come from earlier text only, for continuity

   It chooses the chapter's significant place or moment, an environment that can honestly stand for it (or
   "none"), a stretch of 3 to 40 sentences, a mood and a haze. The answer is validated, with one repair round.
   "none" ends the job as **unavailable**.
2. **Scripting**, for scripted environments (Alice's three rooms, which have manifests). A SceneScript is written for
   the chapter's cut passage with the existing director prompt, and validated against the manifest.
3. **Rendering (Blender).** `blender/render_experience_thumb.py` imports the environment's glTF, applies the mood
   and haze, renders from the reader's anchor with auto-exposure, and reports brightness.
4. **Validating.**
   - the environment's measured budget (at most 65k triangles and 50 meshes; anything over the 35k target is
     flagged in the package)
   - the script, again
   - the render: readable, at least 320x200, not black, not washed out
5. **Packaging.** `package.json` plus `thumb.jpg` (SHA-256), under 1 MB, swapped into `out/chapters/<chapter>/`.

**Delivery on the headset** comes last (see [Lifecycle](#lifecycle)). Only after it is the experience ready.

**Adaptation, not new geometry.** This build creates experiences by adapting the six built environments:

- the mood scales the realtime lights and the ambient term and sets fog
- the scripted rooms also get their staging

No new Blender environment is generated per chapter. A chapter none of the six can honestly stand for is reported
as needing a new environment, and that is the next stage to automate (a generated `blender/build_*.py` →
glTF → runtime glTFast load, held to `docs/ENVIRONMENT_BRIEF.md`).

**A shared environment is never changed.** Each chapter's adaptation lives in its own package and is applied at
runtime. Revisiting chapter 2 always shows chapter 2's version of the room, never one that later chapters changed.

## The spoiler boundary (changed on purpose)

The interpreter used to see only text up to the reader's position. Background preparation needs the chapter
**before** the reader has finished it, so the planning stage now sees text **through the end of the target chapter**,
and no further:

- no later chapters
- no whole-book summaries
- no descriptions derived from later text

`TestPlannerSeesNothingAfterTheChapter` checks every later sentence's id and text against the prompt.

To compensate, the generated results are held back:

- **The service** answers status with stages only: no title, place or image.
- **The headset** keeps the fetched package sealed. `ChapterExperiences.Title`, `Thumbnail` and `OpenPackage`
  refuse an uncompleted chapter at the loading boundary, and every menu goes through them.
- **Peek** keeps the stricter rule: text only up to the end of the highlight.

## Measured (2026-11-02, the owner's Mac, claude-opus-5-5, Blender 5.2.3, live)

All times in seconds.

| Chapter | Result | Plan | Script | Blender | Validate + package | Queue wait | Total on the service | On the headset after asking |
|---|---|---|---|---|---|---|---|---|
| Alice I | Hall of Doors, scripted, 9 beats | 4.8 | 24.0 | 7.4 | 0.01 | 0 | 36.2 | 6.2 (already built) |
| Alice II | Hall of Doors, scripted | 5.0 | 24.1 | 7.5 | 0.01 | 0 | 36.7 | 42.2 |
| Alice III | scripted (staged in the croquet ground) | 5.3 | 43.5 | 2.8 | 0.02 | 6.1 | 57.6 | |
| Oz I | Kansas farmhouse, storm | 3.1 | | 1.8 | 0.02 | 36.2 | 41.2 | 3.2 (already built) |
| Oz II | Kansas farmhouse adapted to day ("the house has just landed") | 10.1 | | 2.5 | 0.01 | 0 | 12.7 | 18.3 |
| Odyssey V | Calypso's cave, day | 3.1 | | 2.4 | 0.01 | 46.4 | 52.0 | |
| Oz III | **unavailable** (the Scarecrow's cornfield) | 8.3 | | | | 0 | 8.3 | |
| Oz V | **unavailable** (the Tin Woodman's forest) | 5.3 | | | | 41.1 | 46.4 | |

So far a scripted chapter takes about 35 to 60 s of work and a place chapter about 5 to 13 s. Queue wait adds
whatever runs ahead. That is too few runs for a time range to show to readers, so the interface shows stages only.
None of this has been measured with the headset on Wi-Fi.

## Limitations

- **The service runs on the owner's Mac.** The headset reaches it over `adb reverse` (or `interpreter.txt`). With the
  Mac off, jobs wait.
- **Imported books have no chapter experiences.** The service holds only the four bundled books' text. The book
  menu says so, and their chapter completion is still recorded.
- **New environments are not generated** (see [The pipeline](#the-pipeline)). Many Oz, Odyssey and Gulliver
  chapters will be "no place built yet".
- **Place experiences have no staged interactions:** a room, a mood and the chapter's moment on the page.
- **Mood on the headset is limited:** the room's baked lighting cannot change, so a mood works through fog, the
  ambient term and realtime light only. The Blender thumbnail can therefore differ from the headset view.
- **Nothing here has run on the headset yet.**
