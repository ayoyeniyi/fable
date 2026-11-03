# Generated reading rooms for uploaded books

Every book has three reading rooms (plus the library).

- Fable's first four books (Alice, Oz, the Odyssey, Gulliver) have hand-built rooms: Blender scripts, baked in Unity.
- Fable's later four (Pride and Prejudice, Moby-Dick, The War of the Worlds, Treasure Island) have generated rooms made
  by the same service ahead of time and **bundled in the app** (below, "Bundled rooms").
- A book the reader uploads gets three generated rooms: places chosen from that book and built automatically on
  the preparation service.

This document covers the generated ones.

## Lifecycle

1. **Sent once.** When an EPUB or PDF finishes importing (`Library.cs`), or when an uploaded book is opened,
   `GeneratedRooms.Request` sends the book's text to the service (`POST /rooms/prepare`). The service keeps it in
   `out/rooms/<book>/book.json`.
   - A scanned PDF with no text has no rooms. The menu says so.
2. **Planned once (Claude).** One call chooses up to three distinct places from the book's **opening**, which is
   whole chapters up to about a third of the book (at least the first chapter, at most 90,000 characters).
   - This is the spoiler rule for rooms. They are offered from the start, so they may only come from text near the
     start, and Claude is told not to use any knowledge of the book beyond it.
   - Each place gets a title, a physical description, a time of day and weather, the chapter it comes from, and short
     quotations.
   - The plan is kept in `plan.json`, so every room comes from the same plan.
   - A book whose opening has fewer than three places gets fewer rooms. The missing rooms say so; nothing is padded
     or repeated.
3. **Each room (one at a time, in a queue that survives restarts):**
   1. **Scripting (Claude).** Claude writes a short room script against `blender/roomkit.py`, the kit described below.
      Its system prompt contains:
      - the kit's API, read from the kit's own docstrings so it never drifts
      - an example script (`blender/roomkit_example.py`)
      - the brief's standards, condensed
   2. **Building (Blender, `blender/roomgen.py`).** In order:
      - Check the script.
      - Run it in a restricted scope.
      - Check the result. It needs a sky, a light, and the reader on open ground with nothing solid within 1.2 m of
        their eyes. It must stay within 65k triangles and 50 meshes. The reading view must be neither almost black
        nor washed out (from five check renders around the reader).
      - Bake each material group's full Cycles lighting (sun, sky, lamps, bounce, contact shadows) into its colour
        texture, with one exposure for the whole room and a soft highlight roll-off.
      - Export an **unlit** glTF.
   3. **Repair.** Any problem (a script error with its line, a failed check) goes back to Claude with the script, and
      Claude writes a corrected one. Up to three attempts.
   4. **Review (Claude, up to two rounds; `internal/rooms/review.go`).** Claude is shown the passing room's five views
      from the reader's eyes, rendered as the headset draws it (`preview_room.py`: unlit, baked textures). It lists
      what most breaks the place's believability and either approves it or writes a revised script.
      - A revision replaces the room only if it builds and passes the same checks. A failing revision gets one repair;
        if that fails too, the previous room is kept. A review never makes a room fail.
      - `--room-review N` sets the rounds (default 2); `--room-keep-work` keeps every round for comparison.
   5. **Packaging.** `out/rooms/<book>/r<N>/` holds `room.gltf`, `room.bin`, `textures/*.jpg`, `thumb.png` (the check
      render from the reader's eyes) and `package.json`, which has the SHA-256 of every file. It is staged and
      swapped in whole.
4. **Delivery.** The headset polls `GET /rooms/status`, fetches each finished room into
   `persistentDataPath/library/<book>/rooms/r<N>.part`, checks every file's SHA-256, and swaps it in. Only then is the
   room offered. Removing the book removes its rooms.
5. **Reading there.** The rooms appear in both menus with their titles: the lobby's book menu (four buttons: three
   rooms and the library) and the **rooms** tab beside the page. Rooms still being made show their stage.
   - Choosing a room loads the library-room scene with the room in place of the library. `GeneratedRoomView` loads
     the glTF at runtime with glTFast, with every material unlit from a template in `Resources` (so the shader is
     always in the build). It is placed so the room's reader anchor is under the reader, facing its look point.
   - Nothing is lit at runtime.
   - The reading position comes along.

## Bundled rooms (Fable's later books)

The four later books have no hand-built rooms. Their rooms were made with the service exactly as an upload's are
(their text posted to `/rooms/prepare` on a private instance, planned from the opening, scripted, built, reviewed
twice) and ship in the APK, so they work offline with no service.

- **Source:** `content/rooms/<slug>/r<N>/` (package files, plus `source/` with the room script and review notes, not
  shipped) and `plan.json`, written by `tools/bundle_rooms.py` from the service's `out/rooms/<book>/`. It makes file
  names plain ASCII (the glTF's image URIs follow) and rewrites `package.json` with the book's slug and SHA-256s.
  Provenance and licence: `content/rooms/SOURCE.md`.
- **Build:** `FableBuild.SyncData` copies each package's files to `StreamingAssets/rooms/<slug>/r<N>/` (not in git)
  and writes `Assets/Fable/Resources/BundledRooms.json` (title, place and the SHA-256 of each `package.json`), which
  the app reads synchronously.
- **Runtime:** `GeneratedRooms.IsBundled(slug)` makes the book's three rooms always ready in both menus. Opening one
  runs `GeneratedRooms.Unpack` first: StreamingAssets are inside the APK on Android, and glTFast needs files, so the
  room is copied once with `UnityWebRequest` into `persistentDataPath/bundled-rooms/<slug>/r<N>/`, every file checked,
  swapped in whole. A copy whose `package.json` hash differs from the app's (an older build) is replaced. Then
  `GeneratedRoomView` loads it like an upload's room. Such a book opens in its first room from the lobby.
- **Uploaded books are unchanged.**
- **Far plane:** the kit's sky dome is 160 to 180 m across; `GeneratedRoomView` now raises every camera's far plane
  past the room's farthest point. With the old 150 m it cut a black hole in the sky (seen in the editor with Pride and
  Prejudice's fields). This affected uploaded books' rooms too.

### The twelve bundled rooms (2026-11-03)

Built on the owner's Mac (Blender 5.2.3, Metal, claude-opus-5-5) by a private service instance on port 8790, one room
at a time, while other Blender jobs ran. Triangles are roomgen's count (Unity's count adds the sky dome, about 1k).
"Load" is the editor's play-mode time on first open, including copying the room out of StreamingAssets.

| Book | Room | Triangles / meshes | Package | Build | Load (editor) |
|---|---|---|---|---|---|
| Pride and Prejudice | The fields to Netherfield after rain (ch. 7) | 56,850 / 23 | 5.4 MB | 464 s | 261 ms |
| | The Netherfield drawing-room (ch. 8) | 28,862 / 36 | 2.6 MB | 370 s | 111 ms |
| | Mr. Bennet's library at Longbourn (ch. 3) | 56,186 / 42 | 5.3 MB | 512 s | 193 ms |
| Moby-Dick | The Spouter-Inn entry and public room (ch. 3) | 16,570 / 31 | 1.9 MB | 635 s | 166 ms |
| | The upstairs room with the prodigious bed (ch. 4) | 13,785 / 38 | 2.1 MB | 597 s | 118 ms |
| | The Battery waterfront, Manhattan (ch. 1) | 60,092 / 30 | 6.3 MB | 770 s | 301 ms |
| The War of the Worlds | Ogilvy's observatory at Ottershaw (ch. 1) | 15,546 / 26 | 1.9 MB | 455 s | 105 ms |
| | The sand pits on Horsell Common at dawn (ch. 2) | 45,444 / 22 | 3.9 MB | 493 s | 184 ms |
| | The dining room at Maybury (ch. 7) | 23,934 / 37 | 2.2 MB | 352 s | 108 ms |
| Treasure Island | The cove below the Admiral Benbow (ch. 2) | 57,948 / 23 | 4.1 MB | 603 s | 222 ms |
| | The squire's library at the Hall (ch. 6) | 49,366 / 38 | 4.7 MB | 739 s | 212 ms |
| | The Spy-glass tavern, Bristol (ch. 8) | 44,033 / 41 | 4.7 MB | 677 s | 211 ms |

- Pride and Prejudice's rooms are run B of the trial below, reused (`content/rooms/SOURCE.md`).
- Moby-Dick's opening (the 90,000-character cap reaches chapter 4 or so) gives two rooms of the same inn.
- Copying a room out of the app took 78 to 123 ms in the editor; the Quest will be slower.
- **Rebuilt:** the Treasure Island cove once, because its reading view is half filled by a smooth rock. The rebuild
  opened the view but baked its right-hand cliff pure black: a review revision wound the faces inward, and the bake
  saw their backs. The first build ships. roomgen's checks look at brightness from five views, not at one material
  baking black; a check for a mostly black baked texture would have caught it.
- **Weak spots seen in the renders:** orange candlelight in the drawing-room and the squire's library, faceted
  pines on Horsell Common, blobby rock faces at the cove, seven rooms over the 35k target.
- Desktop previews from the editor: `captures/desktop/desktop-preview_LibraryRoom_<book>-r<N>*.png`.

## Why scripts, and why they are safe to run

A fixed set of templates cannot cover the places books contain, so Claude writes code. But it writes it against a
kit that carries the craft, and roomgen treats the code as untrusted.

**The kit** (`roomkit.py`) is what lets a short script approach the environment brief:
- materials with colour, roughness and bump variation at a believable scale, plus broad patches and weathering
- terrain with structure (valleys, shores, levelled places, a tilt) instead of even noise
- rocks bedded into the ground
- trees in four habits
- shrubs
- distance-weighted ground cover that thins away from the reader in patches
- clustered scattering with clear zones
- rooms with real door and window openings
- furniture: tables, chairs, bookcases filled with books, beds, hearths with fire light, rugs, candles
- sun, sky (with a ground tone below the horizon), point and area lights
- far hills

All colours are given in sRGB, the way people think of them.

**What roomgen allows the script:**
- **Checked before it runs:** no imports; no names or attributes starting with `_`; no
  `open/exec/eval/getattr/type/...`; no try/with/class/global; and none of the `bpy` areas that reach files,
  add-ons, handlers, preferences or rendering (`bpy.ops.wm`, `bpy.ops.export_*`, `bpy.data.texts`, `bpy.app`,
  `bpy.utils`, ...).
- **Runs with only these in scope:** `kit`, `bpy`, `bmesh`, `math`, `random`, `Vector/Euler/Matrix`, `noise`, and
  a short list of plain builtins.
- **Writes nothing itself:** roomgen writes the outputs, not the script.

**Blender's environment.** Blender runs `--factory-startup` (no user add-ons or settings). Its environment has every
variable whose name mentions a key, token or secret removed, so the Claude key is never visible to it. It keeps the
normal home folder because Cycles' GPU kernel cache lives there; a fresh home crashed Metal (measured).

## Measured (2026-11-03, the owner's Mac, Blender 5.2.3 on Metal, claude-opus-5-5, live)

*Pride and Prejudice*, imported in the editor, planned three places from its opening:
1. the fields to Netherfield after rain (from chapter 7)
2. the Netherfield drawing-room (chapter 10)
3. Mr Bennet's library at Longbourn (chapter 5)

The first room, "The fields to Netherfield after rain", was built on the first attempt in 396 s while six other
Blender jobs shared the machine:
- 19,418 triangles, 14 meshes
- a 2.7 MB package of 17 files

Two earlier attempts failed on the service's own bugs, both since fixed:
- a relative path to roomgen
- Blender crashing in Metal's kernel cache with a throwaway home folder

The test room (`roomkit_example.py`, a river meadow) builds in about 65 s on an idle machine (bake 55 s):
- 34k triangles, 9 meshes

## Review and kit trial (2026-11-03)

The same three *Pride and Prejudice* places, from the same plan, built with the old kit plus review (A) and with the
new kit plus review (B). Blender renders of the exported rooms are compared side by side in a private artifact (the
owner's); the renders are kept in `out/compare/`.

| Room | A: old kit + 2 reviews | B: new kit + 2 reviews |
|---|---|---|
| Fields to Netherfield | 507 s, 45,290 tris | 464 s, 56,850 tris |
| Netherfield drawing-room | 543 s, 7,152 tris | 370 s, 28,862 tris (2 attempts) |
| Mr Bennet's library | 652 s, 45,230 tris | 512 s, 56,186 tris |

- **Review** fixes mistakes and composition the checks cannot see. It found a footpath rendering black (faces
  pointing down), a library door opening onto a meadow, the reader 2 m from a fireplace, blank pictures, and
  oversaturated light.
- **The kit** (hedges, walls, fences, stiles, gates, footpaths, Georgian houses, panelling, sash windows and
  curtains, doors, fireplaces, Regency furniture, chandeliers) fixes how things are made. Review alone cannot get
  past old parts.
- **Still weak:**
  - faceted tree crowns
  - an orange cast in candlelit rooms
  - a black bake patch on one floor
  - dark edge lines on thin mouldings
  - rooms over the 35k triangle target, though under the 65k limit
- **Not yet run on the headset.**

## Limitations

- **Stylised, not photoreal.** Generated rooms are coherent, lit and cheap to draw, but they are clearly stylised:
  - faceted foliage masses
  - simple buildings
  - grass made of blades
  - faint bake seams on rounded shapes

  The hand-built rooms are better, and the environment brief is the bar neither fully reaches yet.
- **Baked light only.** No runtime light, reflections or movement: the room is still apart from the reader.
- **No sound of their own.** The library's quiet sound plays.
- **The service runs on the owner's Mac.** Rooms wait while it is off. A book takes roughly 5 to 20 minutes for all
  three rooms on a busy machine.
- **Not run on the headset yet.** Still to check there:
  - the runtime glTF load and its time
  - texture memory
  - the unlit look against the hand-built rooms
  - 72 Hz
