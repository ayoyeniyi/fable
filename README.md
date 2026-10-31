# Fable

A reading experience for Meta Quest. You read a passage of *Alice's Adventures in Wonderland* on a quiet page; pinch, and the room the passage describes unfolds around you. Each pinch advances one sentence and the validated scene actions that go with it. Pinch both hands and the room folds back into the page.

One book, three scenes. Milestone 1 is the Hall of Doors.

## Layout

| path | what |
|---|---|
| `book/` | Gutenberg #11 text and `passages.json`, the three passages split into sentence ids |
| `schema/` | `scene-script.schema.json` (the contract) and `manifest.<scene>.json` (what each scene can do) |
| `interpreter/` | Go: `fable-interpreter generate|validate|serve`. Asks Claude for a SceneScript, validates against the manifest, repairs once, never emits an invalid script |
| `scripts/` | hand-authored, validated baseline scripts bundled in the app for offline use |
| `blender/` | `build_hall_of_doors.py`: the whole environment as code; renders, bakes, exports GLB |
| `audio/` | `synth_sfx.py`: every ambience and foley clip, synthesised |
| `unity/Fable` | Unity 6000.3 URP project; runtime in `Assets/Fable/Scripts`, batch pipeline in `Assets/Fable/Editor` |
| `captures/` | `blender/` (Cycles renders), `desktop/` (Unity editor camera), `headset/` (adb screencap from the Quest). Never mixed |
| `docs/` | `SCOPE.md`, `TOOLING.md`, `STATUS.md` |

## Build

```bash
# 1. environment (Blender 5.2): renders to out/hall, bakes textures, exports out/hall/hall_of_doors.glb
/Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_hall_of_doors.py -- --out out/hall --render --bake --export
cp out/hall/hall_of_doors.glb unity/Fable/Assets/Fable/Models/

# 2. sounds
/Applications/Blender.app/Contents/MacOS/Blender -b --python audio/synth_sfx.py -- --out unity/Fable/Assets/Fable/Resources/Audio

# 3. interpreter (needs ANTHROPIC_API_KEY for generate/serve; validate works offline)
cd interpreter && go build -o ../out/fable-interpreter ./cmd/fable-interpreter && cd ..
./out/fable-interpreter validate scripts/hall-of-doors.baseline.json
./out/fable-interpreter generate --scene hall-of-doors --out scripts/hall-of-doors.json

# 4. Unity, all headless (editor must be licensed once through Unity Hub)
U=/Applications/Unity/Hub/Editor/6000.3.27f2/Unity.app/Contents/MacOS/Unity
$U -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.ConfigureProject
$U -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.BuildScene
$U -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.BakeLighting
$U -batchmode -quit -projectPath unity/Fable -executeMethod Fable.Editor.FableBuild.BuildApk

# 5. headset
adb install -r unity/Fable/out/fable-hall-of-doors.apk
adb shell am start -n com.fable.alice/com.unity3d.player.UnityPlayerGameActivity
adb shell screencap -p /sdcard/fable.png && adb pull /sdcard/fable.png captures/headset/
```

## Interaction

Right-hand index pinch: next beat. Left-hand pinch: previous beat. Both hands pinched for one second: return to the page. Controller triggers do the same. In the editor: Space / Backspace / Escape.
