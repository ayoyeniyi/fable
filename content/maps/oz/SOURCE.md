# The Wonderful Wizard of Oz — map source

`oz.jpg` (2048x1536) and `oz.height.png` were drawn for Fable by `tools/draw_map.py` from the layout
`oz.layout.json`, written by hand from the text of the 1900 book (content/books/oz).

- **Licence:** Fable's own work, CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/).
- **Lettering:** EB Garamond (Georg Duffner, Octavio Pardo), SIL Open Font License 1.1
  (`unity/Fable/Assets/Fable/Fonts/EBGaramond-OFL.txt`), rendered into the image.
- **Regenerate:** `python3 tools/draw_map.py content/maps/oz/oz.layout.json content/maps/oz/oz.jpg --height content/maps/oz/oz.height.png`
  (needs numpy, scipy, Pillow).

## Why not the original map

Baum's book of 1900 has no map. The first published maps of Oz are the two endpaper maps of *Tik-Tok of Oz*
(Reilly & Britton, 1914; drawn by John R. Neill after Baum), both public domain:

- *Map of the Marvelous Land of Oz*: only a 717x500 copy is on Wikimedia Commons
  (https://commons.wikimedia.org/wiki/File:Map_of_Oz.png), too small to read on the headset; the Internet Archive
  copies checked (`tiktokofozfrank00baumrich`, `tiktokofoz00baum`) lack the endpapers.
- *Map of the Countries near to the Land of Oz*: a 9548x6618 scan exists (Norman B. Leventhal Map Center, Boston
  Public Library, https://commons.wikimedia.org/wiki/File:Map_of_the_countries_near_to_the_land_of_Oz_(26938965685).jpg),
  but it shows Oz itself small and with none of this book's places.

Both 1914 maps also reverse east and west relative to this book (here the Munchkins live in the East and the
Winkies in the West). So the map is drawn: north at the top, the four countries in the colours the book gives them
(Munchkins blue, Winkies yellow, Quadlings red, the city green; the North has no colour in the book and is drawn
violet, as in the later books), the Emerald City in the middle, the great desert all round, and Dorothy's route
from the house in the East along the road of yellow brick, across the ditch, the river and the poppy field, then
west to the Yellow Castle and south past the china country and the hill of the Hammer-Heads to Glinda's castle.
Kansas is marked at the edge, beyond the desert. Positions are `located: "drawn"`.
