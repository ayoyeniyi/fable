# Fable

A reading experience for Meta Quest. You read a passage of *Alice's Adventures in Wonderland* on a quiet page; pinch, and the room the passage describes unfolds around you. Each pinch advances one sentence and the validated scene actions that go with it. Pinch both hands and the room folds back into the page.

One book, three scenes: the Hall of Doors, A Mad Tea-Party and the Queen's Croquet-Ground. Choose one on the reading page; the hall's signature beat grows the room 4x around you as Alice drinks.

## Layout

| path | what |
|---|---|
| `book/` | Gutenberg #11 text and `passages.json`, the three passages split into sentence ids |
| `schema/` | `scene-script.schema.json` (the contract) and `manifest.<scene>.json` (what each scene can do) |
| `interpreter/` | Go: `fable-interpreter generate|validate|serve`. Asks Claude for a SceneScript, validates against the manifest, repairs once, never emits an invalid script |
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

On the page: drag a right pinch or tap left to choose a passage, tap right to open it. In the scene: right tap next beat, left tap previous, right pinch-drag scrubs, both hands quick toggles miniature / immersive, both hands held for a second returns to the page at the sentence reached. Pick up the golden key or the bottle to see the sentence that introduces it. Controller triggers mirror the pinches. In the editor: Space / Backspace / Tab / Escape / Enter.
