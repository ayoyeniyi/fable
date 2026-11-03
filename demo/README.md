# Fable demo film (Remotion)

The competition demo for Meta VR Start 2026 (Entertainment, New Experience, due 18 November 2026): 1920x1080, 30 fps, under three minutes, silent.

**This is the stills cut.** No headset was attached when it was made, so every shot is a still from `captures/` with a slow Ken Burns move, and every shot's corner caption says which of three sources it is: `Blender render (prepared asset)`, `Unity editor preview` or `Quest 2 capture`, plus `cached script` where a staged scene is shown. No shot claims live generation. It is to be replaced shot for shot with headset screen recordings (`adb shell screenrecord /sdcard/fable.mp4`, then `adb pull`) once a reader session is filmed; keep the same captions and swap `Quest 2 capture` for the recording, and add `live generation` only on shots where the page says "live interpretation".

## Render

```bash
cd demo
npm install                 # pinned: remotion 4.0.540, react 19.3.1, typescript 7.0.2
npm run render              # copies the stills, then renders ../out/demo/fable-demo-stills-cut.mp4 (H.264, CRF 18)
npm run studio              # Remotion Studio to scrub the cut
npm run typecheck
```

`npm run stills` (run by both `render` and `studio`) copies only the captures named in `src/shots.ts` into `public/stills/`, which is generated and git-ignored. The Quest screencaps are 3664x1920 with both eyes side by side; the composition crops to the left eye (1832 px) at render time, so the files in `captures/` are untouched.

## Layout

| file | what |
|---|---|
| `src/shots.ts` | the shot list: file, natural size, source, staging label, seconds, narration line, section |
| `src/Film.tsx` | lays the shots end to end with 0.4 s cross dissolves, merges equal narration lines into one band |
| `src/components/Still.tsx` | letterbox or pillarbox on the paper colour, left-eye crop, Ken Burns (scale 1.00 to 1.06, gentle pan) |
| `src/components/Captions.tsx` | source caption (top right), section badge (top left), narration (bottom) |
| `src/components/Cards.tsx` | title and closing cards |
| `src/theme.ts` | paper `#f3efe6`, ink `#2b2520`, brass `#9a6a1f`; Fraunces via `@remotion/google-fonts` with a system serif fallback |

Music: none. `src/Film.tsx` carries the TODO; any track must be credited in `CREDITS.md` before it goes in.
