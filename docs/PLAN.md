# Plan against the competition brief (Meta VR Start 2026, Entertainment, New Experience; deadline 2026-11-18)

Status key: done = built and exercised; partial = built, not yet verified in the headset; todo.

| brief item | status | where |
|---|---|---|
| Comfortable, minimal reader; passage in elegant type | done (editor) | `ReadingPanel.cs`, EB Garamond, paper panel, passage picker; panel placement over the diorama still to fix |
| Hand input only, usable seated | done (headset) | pinch right/left/both, drag-scrub, grab in `ReaderController.cs` / `StoryGrabbable.cs`; controller fallback; untested on hardware |
| Select a passage, miniature scene unfolds in front of the reader | done (editor) | picker on the page; diorama at 0.09 scale grows on the table; hall needs a dollhouse ceiling cut |
| Expand into immersive view | done (direct) | `FlowController.Unfold` scales the room up around the reader |
| Scrub through the passage sentence by sentence, reversible | done (editor) | tap and pinch-drag (6 cm per beat); replay makes it exact, reader size included |
| Highlight the current sentence | done | panel re-typesets with the active sentence in ink, the rest dimmed |
| Pick up important objects, reveal their text | done (editor) | golden key and bottle via Interaction SDK; holding shows the introducing sentence; physical grab unverified |
| Closing returns to the exact reading position | done (editor) | per-passage `progress.json`, survives restart, page reopens on the passage read last |
| Signature: changing-size passage | done (mechanism) | `readerScale` action, 4x on the last beat of the Hall of Doors |
| Visual realism, PBR wood/brass/fabric, natural lamp light | partial | three environments baked and lightmapped; textures ASTC; tuning needs the headset |
| Atmospheric spatial audio | partial | 24 synthesised cues across three scenes, reverb zone, pooled 3D sources; not heard on hardware |
| Backend receives passage, position, prior context | partial | interpreter takes position and prior context; Unity does not send the position yet |
| Structured instructions with approved ids, timing, sentence refs; validated | done | schema + Go + C# validators + tests; validators also reject showing anything before its sentence |
| Limited action vocabulary | done | place, move, remove, animate, light, sound, readerScale |
| Cache successful scenes, preserve progress, fallback if generation fails | done (editor) | interpreter cache, Unity script cache, baseline fallback, per-passage progress |
| One book, three scenes, live interpretation | partial | three environments and baselines done; live generation untested (no API key) |
| Runnable Quest build, source, setup, architecture, demo video | partial | runs on a Quest 2 (72 fps at the page and diorama); video after the task loop is verified |
| Measured headset performance | partial | 72/72 fps, 5 to 10 ms app time at the page and diorama; full-scale hall and outdoor scenes still to log |

## Order of work from here

1. Headset: install `out/fable.apk`, capture (`adb shell screencap`), profile on Quest 2 (OVR Metrics Tool, `adb shell dumpsys SurfaceFlinger --latency`), target 72 Hz. Blocked on a Quest and a working `adb` on the build Mac.
2. Hand-test pinch, scrub, grab and the 4x scale for comfort; fix what breaks.
3. Live interpretation with an API key: `generate` per scene vs baseline, `serve` + `SceneDirector.InterpreterUrl`, send the reading position, a no-baseline passage from the same setting.
4. Visual tuning from the headset view (see HANDOVER, Not done 3-5), dollhouse cut for the hall diorama.
5. Unfamiliar-reader tests, demo video under three minutes from headset footage.

## Richer scenes (requested after headset session 1: "we could be doing more")

Today each sentence has one scripted beat. The brief's wow is a room that keeps answering the text, so:

1. **Two to four actions per beat in the baselines**, all from the existing vocabulary: when Alice tries the doors, every door handle rattles in turn with footsteps between them; when the key is found, it glints *and* the lamps steady; when the bottle appears, the lamp row flickers and the cork pops on "Drink me".
2. **Hall additions worth a Blender pass**: the little door's keyhole glow and a visible garden beyond it (a card is there already), the glass table catching lamp light, dust in the lamp cones (the manifest's `fx.dust` has no mesh yet).
3. **Readings**: ship the Unity switch for the interpreter's variants so one paragraph can be staged four ways; this is the "parallel universes" the reader asked for and it needs no new assets.
4. **Touchable text**: more grabbables that reveal their sentence (the lamp, a door knob), using the pattern `StoryGrabbable` already has.
5. **Outdoor scenes**: give the tea party and croquet ground the same density pass once the hall sets the bar.
