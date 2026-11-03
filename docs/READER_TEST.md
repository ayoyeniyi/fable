# Headset session 4: the first-time-reader test and what has never been worn

Written 2026-11-03. Everything in this file needs a Quest 2 on a face. Nothing here can be done from the editor, which is why it is still open. Run it the next time the headset is on the Mac, and write the findings into `docs/HANDOVER.md` under a new "Headset session 4" heading.

## Before the reader arrives (15 minutes, you alone)

1. Plug the Quest in. `adb devices` must list it; if `adb` is missing again, `brew reinstall android-platform-tools`.
2. Install the current build: `adb install -r unity/Fable/out/fable.apk`. If the APK predates the last commit, rebuild first (README, step 4).
3. Start the interpreter on the Mac and point the headset at it (HANDOVER, "How to work on it"): `set -a; . ~/.config/fable/env; set +a; ./out/fable-interpreter serve --addr 0.0.0.0:8787 --warm --wait 20s`, then `adb reverse tcp:8787 tcp:8787` so the USB tunnel works even when Wi-Fi is wrong.
4. Start a screen recording before the reader puts the headset on, in a second terminal. Three minutes is the Quest limit per file, so loop it:
   ```bash
   for i in 1 2 3 4 5 6; do adb shell screenrecord --time-limit 180 /sdcard/session4_$i.mp4; done
   adb pull /sdcard/session4_1.mp4 captures/headset/   # and so on, after the session
   ```
   Keep the frame log running too: `adb logcat -s VrApi | tee captures/headset/session4_frames.log`.
5. Put the headset on yourself for one minute. The lobby must appear with the four books and the library board, hands must track, the page must open when you pinch a book. If any of that fails, stop and fix it before wasting the reader's time.

## The reader (someone who has never seen Fable, 20 minutes)

Say only this: "You are in a reading room. Point at things with one hand and touch your thumb and index finger together to choose. Everything is under your hand or in front of you; you never have to stand up." Then say nothing until they ask, and write down every question, because each question is a missing cue.

Watch for these eight things in this order. Tick each one only if they did it without coaching.

| # | they should | watch | pass |
|---|---|---|---|
| 1 | open a book from the shelf | do they point and pinch, or reach out to grab the book? | |
| 2 | read two pages and turn forward and back | right pinch forward, left pinch back; do they find the contents / text size buttons on their own? | |
| 3 | look behind them and come back to the page | do they find **recentre** on the bar, or turn their chair, or stand up? | |
| 4 | turn 30° with the bar twice and read on | does the page stay where they put it; do they say the step feels too big or too small? | |
| 5 | highlight a word and Define it | pinch-drag or half-second hold; does the ring open where they expect; do they read the definition or the menu? | |
| 6 | Peek at "the golden key" and turn the model | do they realise they can grab and turn it; does the ray jitter make the 6.6 cm buttons hard to hit? | |
| 7 | finish chapter I (or jump with contents), take the end card's **finish and step into this chapter**, then **‹ return to reading** and find their place | do they understand the padlock; is the return to the same page? | |
| 8 | move the page with its bar and resize it with the corner | do they find the handles unprompted? | |

Then the parts that have never been on a headset:

| # | check | pass |
|---|---|---|
| 9 | **‹ shelf** returns to the lobby; the shelf-edge card shows their progress | |
| 10 | the library board: pinch **+ add a book**; the headset shows an address and a code that can be read at arm's length | |
| 11 | from a phone on the same Wi-Fi, open the address, type the code, send a DRM-free EPUB; the import stages and progress show on the board; the book opens in the library room | |
| 12 | send a PDF with real text (an article) and a scanned PDF; the page view shows the layout, the text view highlights where text exists, the scanned one says so instead of showing an empty text view | |
| 13 | in the library room, Define and Search work on the imported book; Peek and Step In are greyed with the reason; Translate (new, 2026-11-03) returns a translation when the interpreter is up and the plain "needs the interpreter" message when it is not | |
| 14 | the view toolbar is reachable after turning away from the page (it should sit low in front of the reader) | |
| 15 | comfort: 20 minutes of reading at the default text size; ask for a 1 to 5 on eye strain and whether the page should be bigger, nearer or further | |

## Numbers to pull before unplugging

- `captures/headset/session4_frames.log`: FPS and App ms at the page, in the miniature, at full scale in the hall, in the lobby and in the library room. The hall at full scale with baked lamps has never been measured (HANDOVER, session 1).
- Step In latencies as the reader felt them: time from the end card pinch to the miniature. Compare with `docs/LATENCY.md`.
- `adb shell dumpsys meminfo com.fable.alice | head -20` after the PDF import, for the peak.

## Afterwards

Write the eight ticks, the fifteen checks, the questions the reader asked and the numbers into HANDOVER. Every question becomes either a cue to draw or a line in the plan. Pull the recordings into `captures/headset/` and cut the demo (`demo/README.md`) shot for shot from them, replacing the stills.
