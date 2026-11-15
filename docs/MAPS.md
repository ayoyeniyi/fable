# Book maps

When the reader highlights a place name and uses **Peek**, Fable opens the book's map with that place lit instead
of making a clay model. Real places sit on a **globe** the reader can turn by hand; invented places sit on a
**scroll** map: the book's original published map where there is one (Stevenson's island, Swift's plates), or a
map drawn for Fable in the same spirit (`tools/draw_map.py`). A book that mixes the two (Treasure Island's Bristol
and island; Gulliver's invented islands off real coasts) has a globe for the real world and scrolls that come out
of a pin on it.

This file is the contract between the content (`content/maps/`) and the headset. `tools/check_maps.py` enforces
it; run it after every edit.

## Files

```
content/maps/
  _globe/earth.jpg            NASA Blue Marble, equirectangular, 4096x2048 (shared by every globe view)
  _globe/SOURCE.md
  <slug>/map.json             one per book (schema below)
  <slug>/<view>.jpg           scroll images (long side <= 2048, a few at 4096 where labels need it)
  <slug>/<view>.height.png    optional height maps (grayscale, same aspect, long side <= 1024)
  <slug>/SOURCE.md            where every image came from, author, date, licence
```

Every path inside `map.json` is relative to `content/` and starts with `maps/` (for example
`maps/treasure/island.jpg`). The interpreter serves the same tree:

- `GET /maps/<slug>` returns `content/maps/<slug>/map.json`;
- `GET /maps/<path>` returns any other file under `content/maps/` (so a path `maps/treasure/island.jpg` in the
  JSON is fetched from `<server>/maps/treasure/island.jpg`).

The headset may also bundle the same files (StreamingAssets) and resolve the paths locally.

## Schema

```json
{
  "version": 1,
  "book": "treasure",
  "views": [
    {"id": "world", "kind": "globe", "title": "The World", "texture": "maps/_globe/earth.jpg",
     "focus": {"lat": 51.45, "lon": -2.59}},
    {"id": "island", "kind": "scroll", "title": "Treasure Island", "image": "maps/treasure/island.jpg",
     "aspect": 0.78, "height": "maps/treasure/island.height.png", "parent": "world", "anchor": "treasure-island",
     "source": "maps/treasure/SOURCE.md", "attribution": "Map by Robert Louis Stevenson, 1883 (public domain)"}
  ],
  "places": [
    {"id": "bristol", "name": "Bristol", "aliases": ["Bristol"], "kind": "city", "view": "world",
     "lat": 51.454, "lon": -2.588, "located": "geocoded", "firstSentence": "treasure:c07.p001.s02",
     "note": "The port where the Hispaniola is fitted out."},
    {"id": "skeleton-island", "name": "Skeleton Island", "aliases": [], "kind": "island", "view": "island",
     "u": 0.31, "v": 0.72, "located": "scan", "firstSentence": "treasure:c13.p002.s01",
     "note": "A small island off the south of the main one."}
  ]
}
```

### `version`, `book`

`version` is `1`. `book` is the slug (`content/books/<slug>/book.json`).

### Views

The first view is the one a book opens on when Peek has nothing better to say (normally never used; every map open
goes to a place's view).

| field | views | |
|---|---|---|
| `id` | all | lower-case-hyphenated, unique in the book |
| `kind` | all | `"globe"` or `"scroll"` |
| `title` | all | shown on the map (a cartouche on the scroll, a small label under the globe) |
| `texture` | globe | equirectangular Earth texture: u = 0 at longitude -180, u = 1 at +180; v = 0 at latitude +90 (top of the image), v = 1 at -90 |
| `normal` | globe, optional | a matching normal map (not provided yet) |
| `focus` | globe, optional | `{lat, lon}` the globe faces when it opens with nothing lit (the middle of the book's world) |
| `image` | scroll | the map image (JPEG) |
| `aspect` | scroll | image width / height; the scroll is built at this aspect |
| `height` | scroll, optional | grayscale PNG, same aspect: black = sea level, white = the highest land; raise the land a little (a few millimetres at reading scale). It is a gentle relief, not terrain |
| `parent`, `anchor` | scroll, optional | the scroll comes out of a pin on another view: `parent` is that view's id, `anchor` the id of a place on it. When the reader opens a place on this scroll, the headset may first show the parent view turned to the anchor, then unroll the scroll from that pin. Given together or not at all |
| `source` | scroll | the `SOURCE.md` that records the image's origin and licence |
| `attribution` | scroll, optional | one line to show small on the scroll's edge |

### Places

| field | | |
|---|---|---|
| `id` | required | lower-case-hyphenated, unique in the book |
| `name` | required | the place's name as the book writes it; it must occur in the text and is always matched |
| `label` | optional | what the headset shows when the pin is lit, when that should read better than `name` (Alice's "Neat little house" is labelled "The White Rabbit's House"); defaults to `name`. Never matched |
| `aliases` | required (may be `[]`) | other phrases a reader might highlight for this place, in the book's spelling. The name is always matched too; repeating it in `aliases` is harmless |
| `kind` | required | one of `city town village house building street region country island sea coast harbour river lake mountain forest road field garden room ship-position place`. The headset may pick a pin shape from it; `region`, `country` and `sea` are areas, so their pin sits at the middle and may be drawn as a soft ring rather than a needle |
| `view` | required | the id of the view the place is on |
| `lat`, `lon` | globe places | degrees; north and east positive |
| `u`, `v` | scroll places | position on the image, 0..1 from the image's left and top edges (where the label or the feature is drawn) |
| `located` | required | how the position was found: `geocoded` (a real place, OpenStreetMap Nominatim, checked by hand), `book` (coordinates the book itself gives, e.g. a ship's reckoning), `approximate` (invented place in a real landscape, or a real place the book only roughly fixes, placed at its conventional or likely position), `traditional` (an ancient identification, e.g. Homer's Scheria as Corfu), `scan` (where the original published map draws it), `drawn` (placed by Fable on a map drawn for the book) |
| `firstSentence` | required | the id of the sentence where the book first mentions the place by any of its phrases (`tools/check_maps.py --fill` computes it) |
| `note` | required | one short line (at most ~200 characters) shown beside the lit pin. It must not give away anything after `firstSentence` |

## On the headset

### Matching a highlight

1. Normalise the highlighted phrase and every place phrase (`name` and each alias) the same way: Unicode NFKC;
   curly quotes to straight; figure, en and em dashes (U+2012 to U+2015) to a space, and the Unicode hyphens U+2010 and U+2011 to `-`; any character that is not a letter, digit, apostrophe, hyphen or
   space becomes a space; collapse whitespace; trim; lower-case; drop one leading `the `.
2. A place matches when its normalised phrase equals the highlight, or occurs inside the highlight as whole words
   (bounded by the ends of the string or a space). So highlighting "the Admiral Benbow inn" matches the alias
   "Admiral Benbow", and "Netherfield Park" matches "Netherfield" if that is all the book has.
3. Only places that are **revealed** count: a place is revealed when its `firstSentence` is at or before the
   sentence that holds the highlight, in reading order (compare positions in `book.json` order, not the id
   strings; front matter `f01` comes before `c01`).
4. If several revealed places match, take the one whose matched phrase is longest; if still tied, the one
   listed first in `places`.
5. Match: open the map on that place's `view`, turned or panned to the place, its pin lit, its `label` (or `name`) and
   `note` shown. No match: Peek makes its clay model as before.

No phrase belongs to two places (`check_maps.py` enforces this), and phrases are at least three characters.

### Spoilers

While the map is open, draw only revealed places (as in step 3, against the reader's current sentence). The lit
place is always revealed. Places not yet revealed are not drawn at all, not even greyed. The map image itself is
the book's own published map (or one drawn in its spirit); for a scan, the labels on the image are what the
original readers saw too, so they are not hidden.

### Scale

Globe places a few kilometres apart (Woking, Horsell and Maybury in *The War of the Worlds*; Meryton and
Longbourn) overlap on a globe. That is accepted for now: light the matched pin, and draw the others small. A
regional close-up map is a later addition (it would be another scroll view with `parent` set to the globe).

## Content rules

- Real places: OpenStreetMap Nominatim, checked by hand against what the book says (the right Bristol, the right
  Hertford). Credit: "coordinates © OpenStreetMap contributors (ODbL)" in `CREDITS.md`.
- Invented places in a real landscape (Meryton, Longbourn, Netherfield; Lilliput): their conventional or most
  likely position, `located: "approximate"`.
- Scans: public domain only, with the source URL, author, date and licence in `<slug>/SOURCE.md` and a line in
  `CREDITS.md`. Margins cropped, long side at most 2048 (4096 only if labels become unreadable). Place `u`,`v`
  where the scan draws the place; a debug overlay of the pins on the scan is in `captures/maps/<slug>/`.
- Aliases are phrases a reader would plausibly highlight. No common words ("the house", "home", "the sea") unless
  truly unambiguous in that book.
- `note` is spoiler-free up to `firstSentence`.

## Tools

- `tools/check_maps.py [slug...]`: validate; `--fill` recomputes `firstSentence`; `--find <slug> <phrase>...` lists
  the sentences that mention a phrase.
- `tools/draw_map.py <layout.json> <out.jpg>`: paints an aged-parchment, hand-drawn map from a layout (coasts,
  regions, rivers, roads, forests, hills, places, cartouche, compass rose). The layouts for drawn maps are in
  `content/maps/<slug>/<view>.layout.json`; the server can later use the same tool for uploaded books with a
  Claude-written layout. The layout format is documented at the top of the script.
