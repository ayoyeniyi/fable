# Alice's Adventures in Wonderland — map source

Wonderland has no published map (Carroll drew none, and Tenniel's illustrations show no geography), so
`wonderland.jpg` (2048x1536) and `wonderland.height.png` were drawn for Fable by `tools/draw_map.py` from the layout
`wonderland.layout.json`, written by hand from the text of the 1865 book (content/books/alice).

- **Licence:** Fable's own work, CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/).
- **Lettering:** EB Garamond (Georg Duffner, Octavio Pardo), SIL Open Font License 1.1
  (`unity/Fable/Assets/Fable/Fonts/EBGaramond-OFL.txt`), rendered into the image.
- **Regenerate:** `python3 tools/draw_map.py content/maps/alice/wonderland.layout.json content/maps/alice/wonderland.jpg --height content/maps/alice/wonderland.height.png`
  (needs numpy, scipy, Pillow).

The arrangement follows Alice's route, since Carroll gives almost no directions: above ground the bank and the
rabbit-hole under the hedge; below, the long hall with its little door, the pool of tears and its shore; the wood
with the White Rabbit's house, the Caterpillar's mushroom, the Duchess's house and the March Hare's house with the
tea-table; the beautiful garden (rose-tree, croquet-ground, the court); and the sea where the Mock Turtle sits on
his ledge of rock. Positions are `located: "drawn"`.
