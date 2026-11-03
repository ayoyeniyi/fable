# Generated reading rooms for Fable's later books: source and licence

Pride and Prejudice, Moby-Dick, The War of the Worlds and Treasure Island have no hand-built rooms. Each has three
reading rooms made by Fable's room service, the same pipeline that makes rooms for books a reader uploads
(`interpreter/internal/rooms`, `blender/roomkit.py`, `blender/roomgen.py`; `docs/GENERATED_ROOMS.md`), and bundled in
the app so they work offline.

- **How they were made:** the book's text (`content/books/<slug>/book.json`, sent the way the headset sends an upload)
  went to `POST /rooms/prepare` on a private instance of the service. Claude (claude-opus-5-5) chose three places from
  the book's opening only (`plan.json`), wrote a room script for each against the room kit, Blender 5.2 built, checked,
  baked and exported it, and Claude reviewed each built room from the reader's eyes for up to two rounds.
- **What is here:** `<slug>/plan.json` and `<slug>/r<N>/`: `room.gltf`, `room.bin`, `textures/*.jpg` (the baked light),
  `thumb.png` (the check render from the reader's eyes, a Blender render) and `package.json` (title, place, triangles,
  the SHA-256 of every file). `r<N>/source/` keeps the room script and the review notes; it is not shipped.
- **Copied into the app by** `tools/bundle_rooms.py` (file names made plain ASCII) and `FableBuild.SyncData`
  (`StreamingAssets/rooms`, index in `Assets/Fable/Resources/BundledRooms.json`).
- **Pride and Prejudice** reuses the rooms built on 2026-11-03 in the review and kit trial (`docs/GENERATED_ROOMS.md`,
  run B: new kit plus two review rounds) from an earlier import of the same novel (Project Gutenberg's illustrated
  edition, imported as an upload). Its chapter ids were renumbered to this edition (`--chapter-offset -2`; every
  quoted excerpt was checked to be in the renumbered chapter).
- **Licence:** everything here was generated for Fable (code by Claude against Fable's kit, geometry and textures by
  Blender from that code; no downloaded models, images or textures) and is CC0 1.0 like the rest of Fable's content.
  The books' text is public domain; the quotations in `plan.json` are from it.
