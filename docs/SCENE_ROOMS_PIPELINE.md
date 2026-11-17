# Scene rooms: from a Blender build to a download on the headset

Chapter step-in rooms (`docs/SCENE_ROOMS.md`, `schema/scene_rooms.json`) are **not bundled in the APK**. Each one is
built in Blender, baked so that it needs no Unity lightmap, packed into one zip, published on the server, and downloaded
by the headset when the reader reaches the chapter (or steps into it). This page is the contract for room builders.

## 1. Build the room (as for every hand-built room)

- One script per room: `blender/build_<id_with_underscores>.py`, using a shared kit (`pride_kit`, `eighty_kit`,
  `frankenstein_kit`, `wotw_kit`, ...). `K.setup("<id>", "out/<id>", ...)`. Follow `docs/ENVIRONMENT_BRIEF.md` and the
  place's brief in `docs/SCENE_ROOMS.md`.
- Export with the kit's `bake_and_export`, which writes `out/<id>/<id_underscored>.gltf`, its `.bin`, `textures/`
  and **`<id_underscored>_baked.blend`**. Keep that `_baked.blend`: the runtime bake (step 2) starts from it, because it
  still has the lights.
  ```
  blender -b -P blender/build_pool_bank.py -- --bake --export --tex 2048
  ```
- Do not add the room to Unity (`FableBuild.Scenes`) and do not commit anything under `out/`.

### Names the headset relies on

| Node | Meaning |
|---|---|
| `anchor.reader.entrance` | an empty at the reader's **feet** on clear floor (eye is 1.55 m above it) |
| `anchor.reader.look` | an empty at eye height in the direction the reader should face |
| `SkyDome` (or `SkyDome.*`), `far.*` | sky and backdrops: emissive/unlit, never lit by the bake |
| `veg.<kind>.*` | swaying foliage, kind = grass, flowers, crop, reeds, shrub, leaves, crown; vertex colour R = sway weight (0 root, 1 tip) |
| `cloth.<kind>.*` | billowing cloth, kind = sail, flag, curtain, washing; vertex colour R = weight |
| `water.<kind>.*` | water, kind = ocean, river/stream, pond (drawn by the Fable/Water shader) |
| `fx.<kind>.<n>` | an empty with a `radius` custom property: fire, torch, candle, lantern (flames and a crackle at runtime) |
| `sound.<kind>.<n>` | an empty: a positional loop; kind = surf, river, fire, wind-trees, wind, birds, gulls, rigging, crowd, clock, rain, candle |
| `light.*`, `Lamp.*` | lights: used by the bake, not exported |

Names follow `docs/LIVING_SCENES.md`; meshes are merged per material by the kit (`MESH_<material>` unless kept).

## 2. Bake the light into the room for runtime

A room loaded at runtime has no Unity lightmap. `blender/runtime_bake.py` gives it one made in Blender, the way
generated rooms are lit (`blender/roomgen.py`), but keeping the albedo's detail:

```
blender -b -P blender/runtime_bake.py -- out/<id> --wind 0.4 --wind-toward 90 --ambience "birds:0.6+wind-grass:0.5"
```

- It opens `out/<id>/<id_underscored>_baked.blend`, gives every lit mesh a second UV set and bakes Cycles
  diffuse irradiance (direct + indirect, sun, sky, lamps, bounce, contact shadows; alpha cards cast their cut-out
  shadows) into a light texture per mesh, at one exposure for the room (from a linear render at the reader's eye).
- The glTF it writes (`out/<id>/runtime/room.gltf`, `.bin`, `textures/`) has per material: the base colour texture
  (UV 0, alpha kept for cut-out cards) and the light texture as the emissive texture on **UV 1**. Roughness and normal
  maps are dropped. The headset draws `base × light` with a soft highlight roll-off (`Fable/SceneRoom` shader). Sky,
  `far.*` and emissive materials carry no light texture and are drawn as they are.
- It also writes `room.json` (anchors, wind, ambience, exposure, sizes) and `view.jpg` (the reader's view,
  rendered in Blender; it becomes the chapter card's picture on the server).
- Options: `--wind` (0 calm .. 2 gale, default 0.35 outdoors / 0 indoors), `--wind-toward` (compass degrees in
  Blender's frame, 0 = +Y), `--ambience` (`kind:volume+...` from the sound library, `docs/LIVING_SCENES.md`),
  `--indoor`, `--light-max 1024` (largest light texture), `--samples 64`, `--exposure-stops 0` (nudge).

## 3. Budget (checked by the publisher)

- **Download ≤ 15 MB** per room (the zip). Hard limit 25 MB.
- Textures ≤ 2048 px (the bake shrinks larger ones); JPEG. Most materials 512-1024.
- Triangles: target 35k, at most 65k; at most 50 meshes (`schema/environments.json` budget).
- Quest 2 frame rate: cut-out (alpha-tested) cards are the main cost. Keep reader-view card area small; prefer
  opaque masses with a fringe of cards. No realtime lights at runtime.

## 4. Publish

```
python3 tools/publish_scene_room.py out/<id>
```

This checks the budget and names, zips `out/<id>/runtime/` (`room.gltf`, `.bin`, `textures/`, `room.json`) into
`content/scene-rooms/<id>/room-<sha8>.zip`, writes `content/scene-rooms/<id>/manifest.json` (id, version, title,
place, book, chapters, zip size and SHA-256, triangles, anchors) and `view.jpg`, and adds or updates the room's
environment in `schema/environments.json` (`"delivery": "download"`, `"sceneRoom": "<id>"`, hosted in the
`LibraryRoom` scene), taking the title, book and chapters from `schema/scene_rooms.json`.

- **Packages are not committed** (`content/scene-rooms/` is ignored by git: 56 rooms at ~15 MB would add ~0.8 GB to a
  repository that is already large). Commit the build script, `schema/environments.json` and captures only.
- They reach the server with the next `deploy/deploy.sh <ip>`, which rsyncs `content/scene-rooms/` **without**
  deleting rooms the VM has and the Mac lacks. The Mac that deploys is the publishing source; keep `out/<id>/` and
  `content/scene-rooms/<id>/` there.
- Served at `GET /scene-rooms/index.json` and `GET /scene-rooms/<id>/<file>` (behind the access key, ordinary rate
  limit), like `/maps`.

## 5. What happens on the headset

When the reader enters a chapter, its experience is prepared on the server (`docs/CHAPTER_EXPERIENCES.md`); a
package whose environment is a scene room names the zip (`sceneRoom`: id, file, bytes, sha256). The headset downloads
it with progress on the chapter card, checks the SHA-256, unpacks it into `persistentDataPath/scene-rooms/<id>/`
(an LRU cache with a size cap), and only then calls the experience ready. The next chapter's room is prefetched.
Stepping in loads the room with glTFast in the `LibraryRoom` scene, puts the reader at `anchor.reader.entrance`
facing `anchor.reader.look` with no page (a caption on the bar), and returns to the reading room at the end.

## Notes from the first rooms

- Cut-out atlases (alpha cards) stay PNG in the runtime export so they keep their alpha; everything else is JPEG.
- `arctic-ice` is published as a **stand-in** (`--as sr-arctic-ice --no-chapters`): an environment that names no
  chapters is never planned, so it only serves for testing the download path. Re-run
  `python3 tools/publish_scene_room.py out/arctic-ice --as sr-arctic-ice --book frankenstein --no-chapters` after a
  rebuild of the arctic room.
- `publish_scene_room.py` edits one line of `schema/environments.json`. If two builders publish at once, re-run the
  publish of whichever lost its line (it is idempotent).

## Chapters whose new room is not published yet

For the first ten chapters of each book `schema/scene_rooms.json` decides the place. A chapter planned for a new
room that is not published yet answers **"this chapter's place is still being built"** (unavailable, no Claude call);
it is not staged in the nearest existing room, because a merely similar room is not the chapter's place. It becomes
available once the room is published and the server redeployed (the headset asks again on Retry or on its next
visit to the chapter).
