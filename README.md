# Fable

A reader for whole books on Meta Quest. You stand in a quiet room with a shelf of four public-domain books (Alice, Oz, Homer's Odyssey in Samuel Butler's translation, Gulliver's Travels), open one as a floating page and read it cover to cover. Highlight a passage to look a word up, search the book, Peek at a small annotated model of the thing described, or Step In: the passage is staged as a miniature that grows around you, driven by a validated SceneScript from the interpreter (prebuilt assets only, nothing past where you have read).

Built so far: the four books ingested and readable page by page with contents, bookmarks and text sizes; the Alice rooms (Hall of Doors, Mad Tea-Party, Queen's Croquet-Ground) with Step In from the page; live interpretation; point-and-pinch input on a Quest 2. See `docs/PLAN.md` for the tiers and `docs/HANDOVER.md` for what is verified where.

## Layout

| path | what |
|---|---|
| `content/books/<slug>/` | `book.json` (whole book, chapters → paragraphs → sentences with stable ids) and `SOURCE.md` (source URL, SHA-256, edition, licence) |
| `content/dictionary/` | `webster1913.json`: Webster 1913 (public domain) cut to the words the four books use, for Define; `SOURCE.md` |
| `content/library/` | Peek library: `peek-library.json` (aliases, the sentence before which an entry is never offered, labels) and `clay/*.json` mock models; `SOURCE.md` |
| `tools/` | `ingest_book.py` (EPUB / Gutenberg text → `book.json`), `books.json` (the four sources), `map_passages.py` (Step In passages → book sentence ids), `ingest_dictionary.py` (Webster 1913 → `content/dictionary`) |
| `book/` | `passages.json`: the Step In passages split into sentence ids, each linked to its book sentence; Gutenberg #11 text kept for reference |
| `schema/` | `scene-script.schema.json` (the contract), `manifest.<scene>.json` (what each scene can do), `mock-model.schema.json` (Peek's clay models: primitives, 2-5 labels, 15k triangles) |
| `interpreter/` | Go: `fable-interpreter generate|validate|serve|mock`. Asks Claude for a SceneScript (or a Peek clay model), validates, repairs once, never emits an invalid one. Claude only ever sees the book up to the reader's highlight |
| `scripts/` | hand-authored, validated baseline scripts bundled in the app for offline use |
| `blender/` | `build_hall_of_doors.py`, `build_mad_tea_party.py`, `build_queens_croquet_ground.py`: each environment as code; renders, bakes, exports `.gltf` + textures; `check_glb_ids.py` checks manifest coverage |
| `audio/` | `synth_sfx.py`: every ambience and foley clip, synthesised |
| `unity/Fable` | Unity 6000.3 URP project; runtime in `Assets/Fable/Scripts`, batch pipeline in `Assets/Fable/Editor` |
| `captures/` | `blender/` (Cycles renders), `desktop/` (Unity editor camera), `headset/` (adb screencap from the Quest). Never mixed |
| `docs/` | `HANDOVER.md` (state of play), `PLAN.md`, `ARCHITECTURE.md`, `SCOPE.md`, `TOOLING.md` |

## Build

```bash
# 1. environments (Blender 5.2, 1-2 min each; add --render for Cycles stills)
for sc in hall_of_doors:hall:HallOfDoors mad_tea_party:mad-tea-party:MadTeaParty queens_croquet_ground:queens-croquet-ground:QueensCroquetGround; do
  IFS=: read py out unity <<< "$sc"
  blender -b -P blender/build_$py.py -- --out out/$out --bake --export --tex 2048
  # copy out/$out/$py.gltf, its .bin and the textures it references into unity/Fable/Assets/Fable/Models/$unity/
done

# 2. sounds
blender -b --python audio/synth_sfx.py -- --out unity/Fable/Assets/Fable/Resources/Audio

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

On the page: point with a hand (or controller) and pinch. A pinch on **contents**, **text size** or **bookmark** presses it; a pinch anywhere else turns the page, a left pinch turns back, and a pinch-drag flips pages. When the page holds a staged passage, **Step in ›** (or holding the right pinch) opens it as a miniature. In the scene: point and pinch on the floor to go there, on the little door to go through; a pinch at nothing reads on; hold left pinch to close and return to the page at the sentence reached. In the editor: the mouse is the right hand's ray; Space / Backspace / Tab / Escape.

**Highlighting.** Pinch on the text and drag the ray across words (or hold still on one word for half a second); release, and a ring opens around the words: **Define** (Webster 1913, offline), **Translate** (shown, not built yet: P1), **Search** (sentences already read that contain the words; pinch one to go there), **Peek** (a low-fi model with labels beside the page), **Step in** (stage the passage from the highlighted sentence). A quick pinch still turns the page. Pinch away from the ring, or left pinch, to close.

Peek looks in the library first: a prop of the room that is loaded, or a shipped clay model; otherwise it asks the interpreter (`POST /peek`), which asks Claude for a clay model shown only the book up to the end of the highlight. Library entries are never offered before the sentence that introduces them, and the interpreter's cache never serves a model made from further on than the reader has read.

## Books

```bash
python3 tools/ingest_book.py all        # downloads into out/sources/, writes content/books/<slug>/{book.json,SOURCE.md}
python3 tools/map_passages.py           # links Step In passages to book sentences
python3 tools/ingest_dictionary.py      # Webster 1913 -> content/dictionary (Define)
unity command eval 'Fable.Editor.FableBuild.SyncData(); return "ok";'   # copies books, dictionary and Peek library into StreamingAssets
```
