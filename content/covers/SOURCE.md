# Book covers: sources and licences

The four covers stand face out on the lobby shelf. They are made by `blender -b -P tools/make_covers.py` and are
1400 x 2100 JPEGs, the Standard Ebooks (SE) cover size.

| Cover | Made from | Painting | Licence |
|---|---|---|---|
| `alice.jpg` | `epub/images/cover.jpg` from the SE edition (see `content/books/alice/SOURCE.md`), unchanged | *Amanita*, Ivan Shishkin, 1879 | SE cover design CC0 1.0; painting public domain |
| `oz.jpg` | `epub/images/cover.jpg` from the SE edition (`content/books/oz/SOURCE.md`), unchanged | *Heroic Landscape with Rainbow*, Joseph Anton Koch, 1824 | SE cover design CC0 1.0; painting public domain |
| `gulliver.jpg` | `epub/images/cover.jpg` from the SE edition (`content/books/gulliver/SOURCE.md`), unchanged | *Gulliver and the Lilliputians*, Jehan-Georges Vibert, 1870 | SE cover design CC0 1.0; painting public domain |
| `odyssey.jpg` | composed by `tools/make_covers.py` in the SE layout | *Ulysses and Calypso* (*Odysseus und Kalypso*), Arnold Böcklin, 1882 | painting public domain; composition CC0 like the rest of Fable's content |

The painting credits for Alice, Oz and Gulliver are the ones in each SE edition's colophon (quoted in the book's
`SOURCE.md`). SE covers carry League Spartan and Sorts Mill Goudy (The League of Moveable Type, SIL OFL 1.1) rendered
into the image by SE.

## The Odyssey

Butler's translation (Gutenberg #1727) has no SE edition, so the cover is composed to match the others.

- **Painting:** Arnold Böcklin, *Ulysses and Calypso*, 1882, oil on wood, Kunstmuseum Basel.
- **Source page:** https://commons.wikimedia.org/wiki/File:Arnold_B%C3%B6cklin_008.jpg
  (reproduction from The Yorck Project, *10.000 Meisterwerke der Malerei*, 2002).
- **Licence:** public domain. Böcklin died in 1901, so the work is public domain worldwide. Commons tags it
  `PD-Art`: a faithful photographic reproduction of a two-dimensional public-domain work carries no new copyright.
- **File downloaded:** https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Arnold_B%C3%B6cklin_008.jpg/3840px-Arnold_B%C3%B6cklin_008.jpg
  (Commons' 3840 px rendition; the original upload is 6576 x 4562, SHA-1 `7039c7cfc3cc42b6e729c0400dc764cd66e855e2`).
- **SHA-256 of the downloaded file:** `a01342ed6de42d291bff8c563feb44754f6df0cacdda5e5fd790662cc9e24e6d` (the tool
  refuses any other file). Cached at `out/sources/covers/` (not committed).
- **Downloaded:** 2026-10-31.
- **Crop:** the left 46% of the painting at full height (a 2:3 crop). It shows Odysseus alone on the rocks looking out
  to sea, as in Book V; Calypso, on the right of the painting, is not in the crop.
- **Lettering:** "THE ODYSSEY" and "HOMER" in League Spartan Bold, white on a 75% black band, the same position and
  size as the SE covers.
- **Font:** `fonts/LeagueSpartan-Bold.ttf` from https://github.com/theleagueof/league-spartan (`fonts/ttf/`, commit
  `27341b9bf93a2c7faa140538a64ce342486c5fb5`), SHA-256 `28a76032877053bc2a01b9ec15ad2a9c912491ca74e1343aa0ee3297a1dfa230`.
  It is licensed under the SIL Open Font License 1.1 (`fonts/OFL.txt`), Copyright 2020 The League Spartan Project Authors. The font is
  used only to render the cover; it does not ship in the app.

## Checksums of the covers

```
b3e9747ee2b17878eab9a1a427a175bfd3790bee825526a9803b42415b1d3703  alice.jpg
d4639c4caa35def9ffa64980829787476a0508ac91658ff0288f11637b31314a  oz.jpg
20bd6a5a82931a1769cbb445fa5aa2a77a57c10f43a4b50e622c38617d96c16e  gulliver.jpg
85af4c439500a0873638c59d1bdcce14f91f462f1bbf36e8958c8e7d9deff2be  odyssey.jpg
```
