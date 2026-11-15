# Book maps on the headset

How the headset uses the book maps. The data contract (`content/maps/<slug>/map.json`, the matching rule, spoilers)
is `docs/MAPS.md`; the props (scroll, pin, globe stand) are `docs/MAP_PROPS.md`. This file covers only the Unity side.

## What the reader sees

Highlight a phrase and choose **Peek**. If the phrase names a place on the book's map that the highlight has reached,
the map stands beside the page on the reader's left instead of a clay model:

- **Globe** (real places): the Earth on its brass stand turns on its axis for 1.6 s until the place faces the
  reader. For a place more than 8° from the equator the stand also turns 38°, so the tilted axis leans the place
  toward the reader's eyes; the meridian ring then still clears the face of the globe. The lit pin is larger and
  its red glass pulses, and its name stands to the left of the globe with a leader line. Other places the reader has
  reached are smaller, darker pins. Places closer than 2.2° share one pin (Woking, Horsell and Maybury are one
  pin), and pointing at it names the first place and "and N more".
- **Scroll** (invented places): the book's map unrolls from the middle in 1.3 s. The rollers part and the sheet
  shows more of the image at its true scale. Then the pins go in, the lit one with its name in red ink above it.
- **Card**: the place's `label` (or `name`), the view's title, its `note`, how to turn the map, and the view's
  attribution. When the view has another one, a button switches to it. From a scroll with `parent`/`anchor` it
  says "on the globe ›" and shows the parent globe with the anchor lit, if the reader has reached the anchor. From
  a lit globe pin that a scroll comes out of, it gives the scroll's title ("Treasure Island ›") and shows that
  scroll with no pin lit.
- **Hands**: point at the map, pinch, hold and move the hand. Sideways movement turns the globe on its axis
  (0.25 m of hand travel is three quarters of a turn). A scroll turns and tips like a clay model. Pointing at a pin
  names it. Close works as for any Peek: the card's "close ×", or a pinch elsewhere.
- **Spoilers**: the match uses the sentence that holds the end of the highlight. Pins are drawn only for places
  whose `firstSentence` is at or before the later of the highlight and the furthest sentence the reader has reached
  (`BookReader.ReachedOrdinal`, the same limit Search uses). Places not yet reached are not drawn at all. A phrase
  naming a place the reader has not reached falls through to the clay Peek, as does any phrase no place matches.

Map first: a place match wins over the Peek library. The only overlap today is Alice's mushroom. "mushroom" and
"large mushroom" used to open the library's clay mushroom and Caterpillar; they now open the Wonderland scroll at
the Large mushroom.

## Code

| File | |
| --- | --- |
| `Scripts/Maps/BookMap.cs` | `MapDoc` (the JSON), `BookMap` (on the Highlighter's object): loads the open book's map, `Match`, `Normalise`, the image cache. `BookMap.FetchHosted` is the hook for hosted maps (not set yet) |
| `Scripts/Maps/MapView.cs` | builds and runs one view: globe or scroll, pins, labels, the open animation, hover, `Spin` |
| `Scripts/Maps/MapAssets.cs` | `Resources/MapAssets.asset`: the glTF props, the edge mask and the shader, so the build keeps them |
| `Shaders/FableMap.shader` | `Fable/Map`: map and Earth, the props' walnut, brass and parchment, and the pins (vertex colour, glow) |
| `Scripts/Highlighter.cs` | `Peek()` tries the map first (`PeekMap`, `MapAlternative`, `SwitchMapView`); `NewPeekRoot(map: true)` places it; `HoldPeek` spins a globe |
| `Editor/FableBuild.cs` | `SyncMaps` (inside `SyncData`), `MakeMapAssets` |
| `Editor/FableTextureImport.cs` | `MapImage`: map images ASTC, mipmaps, trilinear, aniso 4; the edge mask linear with alpha |
| `Editor/MapPreview.cs` | desktop previews from the play-mode camera into `captures/unity/maps/` |

### Matching (as implemented)

`BookMap.Normalise` follows `docs/MAPS.md` step 1: NFKC; curly single quotes to `'`; U+2012 to U+2015 to a space;
U+2010 and U+2011 to `-`; anything not a letter, digit, `'`, `-` or space to a space; collapse; lower-case; drop
one leading `the `. **One addition:** apostrophes and hyphens at either end of a word are dropped. A highlight taken
from inside quotation marks (`'Woking'`) then still matches, and so does "Nor' West Coast". Place phrases go through
the same function, so internal hyphens and apostrophes (`rabbit-hole`, `Kitt's Hole`) still have to match exactly.
A place matches when its phrase equals the normalised highlight or occurs in it bounded by spaces or the ends. Only
places with `firstSentence` at or before the highlight's last sentence count (reading order from `book.json`; a
`firstSentence` missing from the book means never). The longest matched phrase wins, then the place listed first.

### Data in the build

`FableBuild.SyncData`, which `BuildApk` also runs, copies:

- `content/maps/<slug>/map.json` to `StreamingAssets/maps/<slug>/map.json`;
- every image a view names (`texture`, `image`) to `Assets/Fable/Resources/Maps/<path after maps/>`, so that Unity
  compresses them (`Resources.LoadAsync`, unloaded when the book closes). The brief said "StreamingAssets, map.json
  and images". The images went to Resources instead because a JPEG from StreamingAssets decodes to uncompressed RGB
  on the device: 13 MB for one scroll against 3.6 MB as ASTC.

Height maps, layouts and `SOURCE.md` are not copied: the headset does not use them. A file removed from
`content/maps` is removed from both places at the next sync. Run SyncData after the data agent changes a map.

## Performance (editor measurements; the Quest 2 is not measured)

- **Triangles:** globe 5.9k with one pin (sphere 4,032, stand 1,712, pins 264 each), 11.2k with Moby-Dick's 21
  merged pins. Scroll 8.6k to 10.2k (props 7,824 plus pins).
- **Draw calls:** about +10 for a globe and +16 for a scroll over the page alone. Unity's frame stats in the
  Spy-glass cove went from 22 to 38 batches. The scroll's four finials are two submeshes each.
- **Pins:** all dim pins are one combined mesh with one material; the lit pin has its own material.
- **Per frame:** no allocation. The open animation, pulse, label line and hover test reuse cached transforms and
  lists. The hover test loops over at most a few dozen pins.
- **Textures** (Android, ASTC with mipmaps): Earth 4096×2048 ASTC 6×6, 5.0 MB. Each scroll 2048×2048 ASTC 5×5, 3.6 MB.
  The scans are 1186–1315 × 2048 and are scaled up to a power of two, because left NPOT this Unity imported them
  as RGBA32. A book holds at most the Earth plus the scrolls it has opened: Treasure Island 8.6 MB, Gulliver
  19.4 MB with all four plates. Everything is released when the book closes or another opens.
- **Load:** map.json is parsed off the main thread when the book opens (11–20 ms in the editor). Opening a map
  takes 2–30 ms after its image loads, and the match takes under 0.5 ms.

## Testing in the editor

Test hooks: `Highlight.Select(phrase)`, `.Choose("peek")`, `.Describe()` (now with `map=` and `view=… lit=… pins=…`),
`.SwitchMapView()`, `.Map.PinWorld(i)` to aim `PagePointer.TestRay` at a pin (then `.Map.Hovered`), and
`TestPeekPinch` with the private `ClaimPeek` to turn the globe. `Fable.Editor.MapPreview.Capture(name, from, at)`
writes `captures/unity/maps/desktop-preview_<name>.png`.

Verified in play mode (2026-11-15): London and Woking on the War of the Worlds globe; Wonderland's thick wood on the
scroll, mid-unroll and pointing at a pin; Treasure Island's Skeleton Island on the scroll, then "on the globe" with
Treasure Island lit; Gulliver's Mildendo on the Lilliput plate, then Van Diemen's Land on the globe; Moby-Dick's
Season-on-the-Line on the globe with 21 pins. "equator" in Moby-Dick chapter 2, before that place's `firstSentence`
in chapter 44, falls through to clay, and the same place opens the globe from chapter 44. "White Rabbit" (no place)
still opens the clay rabbit. A hand drag turned the globe about 70°; the map closes with the card. No console errors.

**Not verified:** anything on the headset. Still open there: frame rate with a map open, whether 0.25 m of hand
travel per three-quarter turn feels right, the map's place beside the page (0.26 m left of the page's edge, 0.30 m
nearer, its foot 0.30 m below the page's middle: `Highlighter.MapBesidePage`, `MapNearer`, `MapBelow`), and label
legibility at Quest resolution. Also open: the map can stand inside a room's furniture (it ignores room geometry,
as clay Peek does). The scroll does not zoom to the pin, so a small island on a large plate (Lilliput on Plate I)
stays small.
