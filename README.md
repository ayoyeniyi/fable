# Fable

A reader for whole books on Meta Quest. You stand in a quiet room with a shelf of ten public-domain classics (Homer's Odyssey in Samuel Butler's translation, Gulliver's Travels, Pride and Prejudice, Frankenstein, Moby-Dick, Alice, Around the World in Eighty Days in George Makepeace Towle's translation, Treasure Island, The War of the Worlds, Oz), open one as a floating page and read it cover to cover. Highlight a passage to look a word up, search the book, Peek at a small annotated model of the thing described, or Step In: the passage is staged as a miniature that grows around you, driven by a validated SceneScript from the interpreter (prebuilt assets only, nothing past where you have read).

Built so far: the ten books ingested and readable page by page with contents, bookmarks and text sizes; the Alice rooms (Hall of Doors, Mad Tea-Party, Queen's Croquet-Ground) with Step In from the page; three hand-built rooms for each of the ten classics (thirty scenes), with chapter experiences prepared per chapter in them; 57 downloadable chapter scene rooms (chapters 1-10 of each book), fetched from the server when a chapter is entered; live interpretation; point-and-pinch input on a Quest 2. See `docs/PLAN.md` for the tiers and `docs/HANDOVER.md` for what is verified where.

## Layout

| path | what |
|---|---|
| `content/books/<slug>/` | `book.json` (whole book, chapters → paragraphs → sentences with stable ids) and `SOURCE.md` (source URL, SHA-256, edition, licence) |
| `content/dictionary/` | `webster1913.json`: Webster 1913 (public domain) cut to the words the ten books use, for Define; `SOURCE.md` |
| `content/covers/` | the ten shelf covers (1400 x 2100): the nine Standard Ebooks covers unchanged and an Odyssey cover composed from Böcklin's *Ulysses and Calypso* (public domain); `SOURCE.md` records every source, licence and hash |
| `content/rooms/` | the three generated reading rooms of each of the four later books (Pride and Prejudice, Moby-Dick, The War of the Worlds, Treasure Island): unlit glTF packages made by the room service, kept for the record but no longer shipped (those books now have hand-built rooms), `plan.json`, the room scripts; `SOURCE.md` |
| `content/scene-rooms/` | the downloadable chapter scene rooms (git-ignored; zip + manifest per room, published by `tools/publish_scene_room.py` and served from `GET /scene-rooms/...`); the plan is `schema/scene_rooms.json`, each room's download environment is in `schema/environments.json`; `docs/SCENE_ROOMS_PIPELINE.md` |
| `content/library/` | Peek library: `peek-library.json` (aliases, the sentence before which an entry is never offered, labels) and `clay/*.json` mock models; `SOURCE.md` |
| `tools/` | `ingest_book.py` (EPUB / Gutenberg text → `book.json`), `books.json` (the ten sources), `bundle_rooms.py` (generated rooms from the room service → `content/rooms`), `map_passages.py` (Step In passages → book sentence ids), `ingest_dictionary.py` (Webster 1913 → `content/dictionary`), `make_covers.py` (Blender: the shelf covers → `content/covers`), `fetch_music.py` (the two CC0 recordings, SHA-1 checked) |
| `book/` | `passages.json`: the Step In passages split into sentence ids, each linked to its book sentence; Gutenberg #11 text kept for reference |
| `schema/` | `scene-script.schema.json` (the contract), `manifest.<scene>.json` (what each scene can do), `mock-model.schema.json` (Peek's clay models: primitives, 2-5 labels, 15k triangles) |
| `interpreter/` | Go: `fable-interpreter generate|validate|serve|mock`. Asks Claude for a SceneScript (or a Peek clay model), validates, repairs once, never emits an invalid one. Claude only ever sees the book up to the reader's highlight |
| `scripts/` | hand-authored, validated baseline scripts bundled in the app for offline use |
| `blender/` | `build_lobby.py` (the room the app opens in: the bookcase with the ten books face out), `build_kansas_farmhouse.py`, `build_calypsos_cave.py`, `build_glumdalclitchs_room.py`, `build_poppy_field.py`, `build_emerald_throne_room.py`, `build_odysseus_ship.py`, `build_ithaca_hall.py`, `build_lilliput_beach.py`, `build_laputa.py` (the Oz, Odyssey and Gulliver rooms), the twelve rooms of the four later books (`build_battery_waterfront.py`, `build_spouter_inn.py`, `build_pequod_deck.py`; `build_ogilvys_observatory.py`, `build_horsell_sandpits.py`, `build_maybury_dining_room.py`; `build_benbow_cove.py`, `build_squires_library.py`, `build_spyglass_tavern.py`; `build_longbourn_library.py`, `build_fields_to_netherfield.py`, `build_netherfield_drawing_room.py`), `roomkit.py` + `roomgen.py` (generated rooms for uploaded books), `build_hall_of_doors.py`, `build_mad_tea_party.py`, `build_queens_croquet_ground.py`: each environment as code; renders, bakes, exports `.gltf` + textures; `check_glb_ids.py` checks manifest coverage |
| `audio/` | `make_ambience.py`: the ambient beds, positional loops (fire, candle, clock) and four Alice sfx, cut from CC0 / CC-BY field recordings listed in `SOURCES.md`; `synth_sfx.py` (the Alice rooms) and `synth_rooms.py` (lobby and the step 7 rooms, plus Calypso's lyre): the remaining foley and room clips, synthesised |
| `unity/Fable` | Unity 6000.3 URP project; runtime in `Assets/Fable/Scripts`, batch pipeline in `Assets/Fable/Editor` |
| `captures/` | `blender/` (Cycles renders), `desktop/` (Unity editor camera), `headset/` (adb screencap from the Quest). Never mixed |
| `CREDITS.md` | every text, image, typeface, recording and tool, with source and licence |
| `docs/` | `HANDOVER.md` (state of play), `PLAN.md`, `ARCHITECTURE.md`, `SCOPE.md`, `TOOLING.md` |

## Build

```bash
# 1. environments (Blender 5.2, 1-2 min each; add --render for Cycles stills)
blender -b -P tools/make_covers.py                     # the ten covers (content/covers), before the lobby
for sc in lobby:lobby:Lobby kansas_farmhouse:kansas-farmhouse:KansasFarmhouse calypsos_cave:calypsos-cave:CalypsosCave glumdalclitchs_room:glumdalclitchs-room:GlumdalclitchsRoom hall_of_doors:hall:HallOfDoors mad_tea_party:mad-tea-party:MadTeaParty queens_croquet_ground:queens-croquet-ground:QueensCroquetGround; do
  IFS=: read py out unity <<< "$sc"
  blender -b -P blender/build_$py.py -- --out out/$out --bake --export --tex 2048
  # copy out/$out/$py.gltf, its .bin and the textures it references into unity/Fable/Assets/Fable/Models/$unity/
done

# 2. sounds
blender -b --python audio/synth_sfx.py -- --out unity/Fable/Assets/Fable/Resources/Audio
blender -b --python audio/synth_rooms.py -- --out unity/Fable/Assets/Fable/Resources/Audio
~/fable-sound-tools-venv/bin/python -I audio/make_ambience.py ~/fable-sound-downloads   # recordings listed in audio/SOURCES.md
python3 tools/fetch_music.py                            # CC0 Satie and Handel (macOS afconvert for the FLAC one)

# 3. interpreter (needs ANTHROPIC_API_KEY for generate/serve; validate works offline)
cd interpreter && go build -o ../out/fable-interpreter ./cmd/fable-interpreter && cd ..
./out/fable-interpreter validate scripts/hall-of-doors.baseline.json
./out/fable-interpreter mock --check content/library/clay/*.json                       # offline
./out/fable-interpreter mock --book alice --passage "little golden key" --phrase "golden key"   # needs the key

# 4. Unity, driven live through the Unity CLI (see docs/HANDOVER.md for the full sequence)
export UNITY_PROJECT_PATH=$PWD/unity/Fable
unity open unity/Fable --build-target Android && unity status --until-ready
unity command eval 'Fable.Editor.FableBuild.ConfigureProject(); return "ok";' --timeout 600
unity command eval 'Fable.Editor.FableBuild.BuildScene(); Fable.Editor.FableBuild.BakeLighting(); return "ok";' --timeout 3600
unity command eval 'Fable.Editor.FableBuild.BuildApk(); return "ok";' --timeout 3600      # -> unity/Fable/out/fable.apk

# 5. headset
adb install -r unity/Fable/out/fable.apk
adb shell am start -n com.fable.alice/com.unity3d.player.UnityPlayerGameActivity
adb shell screencap -p /sdcard/fable.png && adb pull /sdcard/fable.png captures/headset/
```

## Interaction

In the lobby (where the app opens): point at a book on the shelf and it slides forward; pinch to open it. A card on the shelf edge under each book says how far you have read. On the page, **‹ library** goes back to the lobby. Every book has the library as a reading room, and all but the two newest have three rooms of their own. Alice: the Hall of Doors, the Mad Tea-Party, the Queen's croquet ground. Oz: the Kansas farmhouse with the storm coming, the poppy field by the river, the Throne Room of the Emerald City. The Odyssey: Calypso's cave, the deck of Odysseus's ship off the Sirens' island, the hall at Ithaca. Gulliver: Glumdalclitch's room at doll scale, the shore of Lilliput at giant scale, a gallery on the rim of Laputa. The four later books have generated rooms, made by the room service from each book's opening and bundled in the app (`content/rooms`): Pride and Prejudice: the fields to Netherfield after rain, the Netherfield drawing-room, Mr. Bennet's library. Moby-Dick: the Spouter-Inn, the upstairs room with the prodigious bed, the Battery. The War of the Worlds: Ogilvy's observatory, the sand pits on Horsell Common at dawn, the dining room at Maybury. Treasure Island: the cove below the Admiral Benbow, the squire's library, the Spy-glass tavern. Their chapters have no experiences yet (no place is built for them). Around the World in Eighty Days and Frankenstein are read in the library room until their own rooms are built. A book opens in its first room; the others are under **reading rooms**, the button above the page. Books you upload are an early preview: each gets three simpler, generated rooms of its own, made from places in its opening chapters (`docs/GENERATED_ROOMS.md`). Credits for every text, image, font and piece of music: `CREDITS.md`.

Fable is designed to be used from one place, seated or standing. A bar of buttons under the page (or low in front of you, once you have turned away from the page) holds:
- **‹ turn** and **turn ›**: 30° about your head, one turn per pinch.
- **recentre**: brings the page back in front of you.
- the way back from wherever you are: **‹ return to reading**, **back to the table**, **stand in the room ›**.

The page stays where you put it. Move it with the orange bar under it, and resize it with its bottom-right corner. The chevrons beside the page turn it. The **X** at its top right puts the book down (the bar then offers **open the book**); **quit Fable** at the top right asks for a second pinch to confirm.

**Fable's menu:** the Quest menu gesture (left palm up, pinch) or the left controller's menu button opens it in front of you, in reading rooms and the lobby: back, library, quit Fable.

**Walking about:** in a reading room or a chapter's place, point a raised hand at open floor; an arc curves to a ring, pinch to go there (the page and the bar come along).

On the page: point with a hand (or controller) and pinch. A pinch on **contents**, **text size** or **bookmark** presses it; a pinch anywhere else turns the page, a left pinch turns back, and a pinch-drag flips pages. **Step In is per chapter.** Each chapter's experience is prepared in the background while you read it, and stays locked (a padlock and its number, nothing else) until you finish the chapter. After a chapter's last page, an end card offers **continue reading ›** and, when its experience is ready, **finish and step into this chapter ›**. Finished chapters' experiences are under **chapters** on the bar (or the highlight menu's **Chapters** petal) for revisiting. Inside one, **‹ return to reading** takes you back to your page. In Alice's scenes: point and pinch on the floor to go there; a pinch at nothing reads on. Details: `docs/CHAPTER_EXPERIENCES.md`.

Choosing a book in the lobby opens its menu first: **resume reading**, **reading rooms** (its own room or the library), **chapter experiences**. Beside the page, the bar's **chapters / rooms / sound** open the same choices, plus music and room-sound settings. In the editor: the mouse is the right hand's ray; Space / Backspace / Escape.

**Your own books.** The lobby is your library: a board in front of you lists the ten classics first, then every book you add (an early preview, tagged as such).
1. Pinch **+ add a book**. The headset shows an address and a code.
2. On a phone or computer on the same Wi-Fi, open the address, type the code and send an EPUB (DRM-free) or a PDF, up to 150 MB.
3. Keep reading while it imports.

Imported books open in the library room until their three generated rooms are built (minutes, on the preparation service), then the rooms are offered beside the page and in the book's menu. PDFs show their pages as laid out, and have a text view for highlighting where the PDF has real text. Formats, limits and what happens when something goes wrong: `docs/LIBRARY.md`.

**Highlighting.** Pinch on the text and drag the ray across words (or hold still on one word for half a second); release, and a ring opens around the words: **Define** (Webster 1913, offline), **Translate** (the highlight in another language, from the interpreter; pinch **to Spanish ▼** on the card, or **Translate into** under **settings** on the bar, for the language picker: 54 languages on large tiles, the current one marked, the headset's language and your recent ones first; it starts as the headset's language when that is offered, else Spanish, and works for your own books too), **Search** (sentences already read that contain the words; pinch one to go there), **Peek** (a low-fi model with labels beside the page: point at it, pinch and hold to turn it), **Step in** (stage the passage from the highlighted sentence). For your own books Peek and Step In are shown greyed, with the reason. A quick pinch still turns the page. Pinch away from the ring, or left pinch, to close.

Peek looks in the library first: a prop of the room that is loaded, or a shipped clay model; otherwise it asks the interpreter (`POST /peek`), which asks Claude for a clay model shown only the book up to the end of the highlight. Library entries are never offered before the sentence that introduces them, and the interpreter's cache never serves a model made from further on than the reader has read.

Translate sends the interpreter (`POST /translate`) only the highlighted words and the book's title, nothing before or after them, and the interpreter caches each (text, language) pair so a repeat is instant. Without the interpreter the card says so; Define and Search still work. Languages (54; `TranslateLanguages.cs`, the same list in `interpreter/internal/server/languages.go`, a Go test checks they match): Afrikaans, Amharic, Arabic, Bengali, Chichewa, Chinese (Simplified), Chinese (Traditional), Czech, Danish, Dutch, Filipino, Finnish, French, German, Greek, Gujarati, Hausa, Hebrew, Hindi, Hungarian, Igbo, Indonesian, isiNdebele, isiXhosa, isiZulu, Italian, Japanese, Kannada, Kinyarwanda, Korean, Malay, Malayalam, Marathi, Nepali, Norwegian, Persian, Polish, Portuguese, Punjabi, Romanian, Russian, Shona, Somali, Spanish, Swahili, Swedish, Tamil, Telugu, Thai, Turkish, Ukrainian, Urdu, Vietnamese, Yoruba. Latin, Cyrillic and Greek translations are shown as text in EB Garamond. Scripts TextMeshPro cannot shape or lay out right to left (Arabic, Persian, Urdu, Hebrew, the Indic scripts, Thai), Amharic, Chinese, Japanese, Korean and Yoruba (stacked tone marks) are drawn by the interpreter with Noto fonts (`interpreter/internal/textimg`, fonts fetched by `python3 tools/fetch_fonts.py`) and shown on the card as a picture, so no font for them is in the app; the picker's native names for them are `Resources/LanguageNames.png` (`fable-interpreter render-names`).

**Waiting.** Every wait the reader sees says how long it usually takes and how long is left, rounded up ("about 15 seconds left"; "taking a little longer than usual" past it): Peek (with a bar under the words), Translate (only when slow), a chapter's experience being prepared (on its tile and on the end-of-chapter card) and an uploaded book's rooms (under **rooms**). The service puts `etaSeconds` in its chapter and room status answers from its own recent jobs and queue; Peek and Translate use a running average kept on the headset (`WaitEstimate.cs`), seeded from `docs/LATENCY.md`. A cached answer is instant and nothing is said.

## Books

```bash
python3 tools/ingest_book.py all        # downloads into out/sources/, writes content/books/<slug>/{book.json,SOURCE.md}
python3 tools/map_passages.py           # links Step In passages to book sentences
python3 tools/ingest_dictionary.py      # Webster 1913 -> content/dictionary (Define)
# the later books' rooms: run the room service privately, POST each book to /rooms/prepare (docs/GENERATED_ROOMS.md), then
python3 tools/bundle_rooms.py --service-dir <root>/out/rooms/worlds --slug worlds   # -> content/rooms/worlds
unity command eval 'Fable.Editor.FableBuild.SyncData(); return "ok";'   # copies books, dictionary, Peek library and bundled rooms into StreamingAssets
```
