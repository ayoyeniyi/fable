# Plan against the competition brief (Meta VR Start 2026, Entertainment, New Experience; deadline 2026-11-18)

Status key: done = built and exercised; partial = built, not yet verified in the headset; todo.

| brief item | status | where |
|---|---|---|
| Comfortable, minimal reader; passage in elegant type | partial | `ReadingPanel.cs`, EB Garamond, paper panel; passage picker todo |
| Hand input only, usable seated | partial | pinch right/left/both in `ReaderController.cs`; controller fallback; untested on hardware |
| Select a passage, miniature scene unfolds in front of the reader | todo | planned: diorama stage at 0.35 scale on a pedestal in the reading room, then `expand` to 1.0 |
| Expand into immersive view | done (direct) | `FlowController.Unfold` scales the room up around the reader |
| Scrub through the passage sentence by sentence, reversible | partial | discrete beats Next/Previous are deterministic; continuous pinch-drag scrubbing todo |
| Highlight the current sentence | done | panel re-typesets with the active sentence in ink, the rest dimmed |
| Pick up important objects, reveal their text | todo | planned: grab the key and the bottle with Interaction SDK, show the sentence that introduces them |
| Closing returns to the exact reading position | done | `FlowController.Return` keeps the beat's sentence; progress persistence todo |
| Signature: changing-size passage | done (mechanism) | `readerScale` action, 4x on the last beat of the Hall of Doors |
| Visual realism, PBR wood/brass/fabric, natural lamp light | partial | Cycles renders in `captures/blender`; Unity lightmap bake pending; see STATUS.md for defects |
| Atmospheric spatial audio | partial | 9 synthesised cues, reverb zone, pooled 3D sources; not heard on hardware |
| Backend receives passage, position, prior context | partial | passage + manifest sent; reading position and prior-context window todo |
| Structured instructions with approved ids, timing, sentence refs; validated | done | schema + Go + C# validators + tests |
| Limited action vocabulary | done | place, move, remove, animate, light, sound, readerScale |
| Cache successful scenes, preserve progress, fallback if generation fails | partial | baseline fallback done; cache and progress file todo |
| One book, three scenes, live interpretation | partial | passages, manifests and baselines for all three; only the Hall of Doors has assets |
| Runnable Quest build, source, setup, architecture, demo video | partial | source, README, ARCHITECTURE; APK build next; video after headset testing |
| Measured headset performance | todo | needs a Quest on USB |

## Order of work from here

1. Rebuild the scene from the iteration-6 GLB, bake lighting and the reflection probe, build the APK, install when a Quest is attached, capture and profile (OVR Metrics, `adb shell dumpsys SurfaceFlinger --latency`).
2. Miniature diorama stage and continuous scrubbing (pinch-and-drag along the passage), with the sentence highlight tracking the scrub.
3. Grabbable key and bottle through the Interaction SDK, revealing their sentences.
4. Progress file and scene cache in `Application.persistentDataPath`; prior-context window and reading position in the interpreter request.
5. Tea party and croquet ground environments in Blender, same pipeline.
6. Unfamiliar-reader tests, demo video under three minutes.
