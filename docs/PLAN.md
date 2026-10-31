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
| 7 Rooms: Kansas farmhouse, Calypso's cave, Glumdalclitch's room; music and CREDITS.md | todo | Hall of Doors exists; budgets in ARCHITECTURE.md |
| 8 Step In live: generate vs baseline, latencies (cached / live opus / live haiku), streaming, 20 s fallback | partial | live generation runs on the owner's Mac; latencies, streaming and the 20 s rule not done |
| 9 Grabbables | done (editor) | key and bottle via the Interaction SDK; physical grab on the headset pending |
| 10 Demo video under 3 minutes | todo | caption prepared assets vs cached scripts vs live generation |

## Richer scenes (requested after headset session 1: "we could be doing more")

Today each sentence has one scripted beat. The brief's wow is a room that keeps answering the text, so:

1. **Two to four actions per beat in the baselines**, all from the existing vocabulary: when Alice tries the doors, every door handle rattles in turn with footsteps between them; when the key is found, it glints *and* the lamps steady; when the bottle appears, the lamp row flickers and the cork pops on "Drink me".
2. **Hall additions worth a Blender pass**: the little door's keyhole glow and a visible garden beyond it (a card is there already), the glass table catching lamp light, dust in the lamp cones (the manifest's `fx.dust` has no mesh yet).
3. **Readings**: ship the Unity switch for the interpreter's variants so one paragraph can be staged four ways; this is the "parallel universes" the reader asked for and it needs no new assets.
4. **Touchable text**: more grabbables that reveal their sentence (the lamp, a door knob), using the pattern `StoryGrabbable` already has.
5. **Outdoor scenes**: give the tea party and croquet ground the same density pass once the hall sets the bar.
