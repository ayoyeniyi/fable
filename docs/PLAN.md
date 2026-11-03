# Plan (Meta VR Start 2026, Entertainment, New Experience; deadline 2026-11-18)

**The product (brief of 2026-10-31, supersedes the one-book plan):** a VR-native reader for whole books. The reader stands in a lobby with a shelf of four public-domain books, opens one as a floating page inside one of three preset rooms for that book, reads it cover to cover, and can highlight text for Define, Translate, Search, Peek (a small annotated low-fi model) or Step In (the passage staged as a miniature that grows around the reader). Step In stages prebuilt assets from a validated SceneScript; it never builds photoreal geometry at runtime. Spoiler rule everywhere: nothing past the end of the highlight or the reader's position is sent to the interpreter or shown.

Books: Alice (Standard Ebooks), Oz (SE), the Odyssey in Samuel Butler's 1900 prose translation only (Gutenberg #1727), Gulliver (SE). Rooms:

| book | rooms (P0 room first) |
|---|---|
| Alice | Hall of Doors (built) · Mad Tea Party garden (built) · Queen's Croquet Ground (built) |
| Oz | Kansas farmhouse interior, storm sky · Poppy field by the river · Emerald City throne room |
| Odyssey | Calypso's cave on Ogygia · Deck of Odysseus's ship at night, Sirens' isle off the bow · Great hall at Ithaca |
| Gulliver | Glumdalclitch's room in Brobdingnag, reader at doll scale · Lilliput beach, reader at giant scale · Laputa |

## Scope tiers (finish P0 before P1; never trade P0 polish for P2 breadth)

- **P0:** hardware-verified 72 Hz on Quest 2; lobby with shelf and four books; all four books readable cover to cover with typography comfortable for 20 minutes; one finished room per book (Hall of Doors, Kansas farmhouse, Calypso's cave, Glumdalclitch's room); highlight menu with Define, Search, Peek, Step In; Peek from the manifest/library (a) and clay (c) with Claude-written labels; Step In for the Hall of Doors from the headset with the live interpreter; credited music; progress per book across restarts; demo video.
- **P1:** the other eight rooms (HDRI sky plus hero meshes is fine outdoors); Step In for one anchor scene per book with cached baselines; Translate; a ~40-model generic low-poly library for Peek (a); room switching from the page; grabbable key and bottle.
- **P2:** Peek (b) server-side text-to-3D with prefetch; SceneScript prefetch; EPUB upload; voice-read of the current beat.
- **Deferred:** multiplayer, arbitrary books, branching, unrestricted animated characters, Meta VR Glasses-specific features.

## Steps (in order) and status

Status key: done (headset) / done (editor) = built and exercised there; partial; todo.

| step | status | notes |
|---|---|---|
| 1-3 Build, headset install, hand-testing (earlier brief) | done (headset) | Quest 2 sessions 1-3 in HANDOVER; 72 fps at the page and diorama |
| 4 Content pipeline, whole-book pages | done (editor) | `tools/ingest_book.py`, `content/books/*`, `BookReader.cs`, `PagePointer.cs`; page legibility for 20 minutes still to measure on the headset |
| 5 Highlight menu, Define, Search, Peek (c) clay + (a) matcher, `fable-interpreter mock` | done (editor) | `Highlighter.cs`, `ClayBuilder.cs`, `Lookup.cs`, `schema/mock-model.schema.json`, `content/dictionary`, `content/library`, `fable-interpreter mock` and `POST /peek`; editor latencies in HANDOVER. Not measured: live clay generation (no API key in that session), anything on the headset. Translate is shown disabled (P1) |
| 6 Lobby with shelf and four books | done (editor) | `blender/build_lobby.py` (10,058 tris, 35 meshes), `LobbyController.cs`, covers in `content/covers` (`tools/make_covers.py`, sources in its `SOURCE.md`); the app opens in the lobby, pinch a book to open it, **‹ shelf** on the page comes back. Not tried on the headset. The other three books read in the Hall scene's reading space until step 7 |
| 7 Rooms: Kansas farmhouse, Calypso's cave, Glumdalclitch's room; music and CREDITS.md | done (editor) | `blender/build_{kansas_farmhouse,calypsos_cave,glumdalclitchs_room}.py` (30k / 34k / 30k tris), read in the room (`FlowController.RoomOnly`), `RoomSound` (synthesised ambience, `audio/synth_rooms.py`; CC0 Satie in the lobby and Handel in Gulliver's room via `tools/fetch_music.py`; a composed lyre in the cave), `CREDITS.md`. No Step In from these rooms yet (P1). Not tried on the headset |
| 7b Stationary controls (owner's brief, 2026-11-01) | done (editor) | `ViewControls.cs` (turn 30° per pinch about the head, recentre, back / return to reading), `PanelHandles.cs`, Peek grab-to-turn, pinch claiming, the page stays put; two-hand and hold gestures off. First-time-reader test on the headset still owed |
| 7c Personal library and book uploads (owner's brief, 2026-11-01) | done (editor) | `Scripts/Library/*`, `docs/LIBRARY.md`: the lobby board, the Wi-Fi upload page on the headset, EPUB and PDF import (page view + text view), LibraryRoom. Every format and failure case verified in the editor over HTTP; nothing yet on the headset |
| 8a Step In per chapter (owner's brief, 2026-11-02) | done (editor, live service) | `docs/CHAPTER_EXPERIENCES.md`: one experience per chapter, prepared in the background from the moment the chapter is entered (`interpreter/internal/chapters`: plan → script → Blender → validate → package; `ChapterExperiences.cs` delivers and seals), locked until the chapter is finished, end-of-chapter card, book menu in the lobby and beside the page. Measured live; new environments are not generated yet (chapters with no fitting room say so); not on the headset |
| 7d The other eight rooms: three per book (owner, 2026-11-03) | done (editor) | Oz: `build_poppy_field.py`, `build_emerald_throne_room.py`; Odyssey: `build_odysseus_ship.py` (a calm hazy morning, as the text has it, not night), `build_ithaca_hall.py`; Gulliver: `build_lilliput_beach.py` (1/12 scale), `build_laputa.py`. One subagent each, held to `docs/ENVIRONMENT_BRIEF.md`; Unity scenes built and lightmaps baked; listed in both rooms menus (`ReadingRooms.cs`) and in `schema/environments.json` for chapter experiences. 26k to 47k triangles each. Not on the headset |
| 7e Three generated rooms per uploaded book (owner, 2026-11-03) | done (editor, live service) | `docs/GENERATED_ROOMS.md`: Claude chooses three places from the book's opening, writes room scripts against `blender/roomkit.py`, `blender/roomgen.py` checks, runs, bakes light and exports unlit glTF; the headset fetches with SHA-256 and loads at runtime (`GeneratedRooms.cs`, `GeneratedRoomView.cs`). Live on Pride and Prejudice: three rooms in 4 to 7 minutes each. Stylised, not photoreal; not on the headset |
| 8 Step In live: generate vs baseline, latencies (cached / live opus / live haiku), streaming, 20 s fallback | partial (superseded in part by 8a) | live generation runs on the owner's Mac; latencies, streaming and the 20 s rule not done |
| 9 Grabbables | done (editor) | key and bottle via the Interaction SDK; physical grab on the headset pending |
| 10 Demo video under 3 minutes | todo | caption prepared assets vs cached scripts vs live generation |

## Richer scenes (requested after headset session 1: "we could be doing more")

Today each sentence has one scripted beat. The brief's wow is a room that keeps answering the text, so:

1. **Two to four actions per beat in the baselines**, all from the existing vocabulary: when Alice tries the doors, every door handle rattles in turn with footsteps between them; when the key is found, it glints *and* the lamps steady; when the bottle appears, the lamp row flickers and the cork pops on "Drink me".
2. **Hall additions worth a Blender pass**: the little door's keyhole glow and a visible garden beyond it (a card is there already), the glass table catching lamp light, dust in the lamp cones (the manifest's `fx.dust` has no mesh yet).
3. **Readings**: ship the Unity switch for the interpreter's variants so one paragraph can be staged four ways; this is the "parallel universes" the reader asked for and it needs no new assets.
4. **Touchable text**: more grabbables that reveal their sentence (the lamp, a door knob), using the pattern `StoryGrabbable` already has.
5. **Outdoor scenes**: give the tea party and croquet ground the same density pass once the hall sets the bar.
