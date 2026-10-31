# Fable scope

One book, three scenes, one headset.

**Book.** *Alice's Adventures in Wonderland*, Lewis Carroll, 1865. Text from Project Gutenberg eBook #11 (public domain in the US). `book/passages.json` holds the three passages split into sentences with stable ids such as `hall-of-doors:004`; those ids are what the interpreter and Unity synchronise on.

**Scenes.**

| id | chapter | passage | status |
|---|---|---|---|
| `hall-of-doors` | I. Down the Rabbit-Hole | the long low hall, the lamps, the glass table, the golden key, the low curtain and the fifteen-inch door, the DRINK ME bottle | milestone 1, in progress |
| `mad-tea-party` | VII. A Mad Tea-Party | the table under the tree, the Hatter, the March Hare, the sleeping Dormouse | passage extracted, no assets yet |
| `queens-croquet-ground` | VIII. The Queen's Croquet-Ground | the rose tree, the gardeners painting roses red | passage extracted, no assets yet |

**Milestone 1 acceptance.** Inside the headset: the reader picks the Hall of Doors passage on the reading panel, the room unfolds around them, each right-hand pinch advances one beat (sentence plus validated scene actions), a left-hand pinch steps back, and a two-hand pinch held for a second returns smoothly to the reading panel. Stable 72 Hz on Quest 2, 90 Hz on Quest 3.

**Target device.** Meta Quest 2 is the development headset on hand (adb over USB). Quest 3 is a supported target with the same build. Budgets are set for Quest 2 and therefore hold on Quest 3.

**Runtime.** Unity 6000.3 LTS, Universal Render Pipeline, Meta XR Core SDK for hand tracking and the camera rig, glTFast for importing the Blender assets, TextMesh Pro with EB Garamond for the reading panel. Android, ARM64, IL2CPP, Vulkan, ASTC textures.

**Asset pipeline.** Blender 5.2 drives everything procedurally from `blender/build_hall_of_doors.py`: geometry, PBR node materials, lamps, cameras. The same script bakes base colour, roughness and normal maps, merges meshes by material, and exports `hall_of_doors.glb` for Unity. Art-direction stills are Cycles renders and are labelled as such wherever they appear.

**Interpretation.** `interpreter/` is a Go service and CLI. It takes a passage and the scene manifest (`schema/manifest.<scene>.json`), asks Claude for a SceneScript, validates it against `schema/scene-script.schema.json` and the manifest vocabulary, sends validator findings back once for repair, and returns only scripts that pass. Unity validates again on load. `scripts/<scene>.baseline.json` is a hand-authored, validated fallback bundled in the app so the headset works offline.

**Out of scope for milestone 1.** Other books, more than three scenes, character animation (the Hatter and the Queen will be props and silhouettes before they are rigged characters), voice narration, multiplayer.
