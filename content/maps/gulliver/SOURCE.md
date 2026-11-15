# Gulliver's Travels maps — source

The four scrolls are the maps engraved for the first edition of *Travels into Several Remote Nations of the World*
(Lemuel Gulliver [Jonathan Swift], London: Benjamin Motte, 1726), in the style of Herman Moll's charts. Each
plate is photographed from the Thomas Fisher Rare Book Library (University of Toronto) copy, digitised by the
Internet Archive.

| File | Plate | Internet Archive item, page | SHA-256 of the downloaded page |
|---|---|---|---|
| `lilliput.jpg` | Plate I, Part I (Lilliput and Blefuscu, "Discovered A.D. 1699") | https://archive.org/details/travelsintosever01swif , page n21 (https://archive.org/download/travelsintosever01swif/page/n21.jpg) | `78f14744ab5a88663bff86914930f5008f9e190c39feb1a477637283f56c9367` |
| `brobdingnag.jpg` | Plate II, Part II (Brobdingnag, "Discovered A.D. 1703") | same item, page n177 (https://archive.org/download/travelsintosever01swif/page/n177.jpg) | `9b1ecbbb74caf557c52f20c1d70de3038a9667db590e930ebe1cebb12953f52c` |
| `laputa.jpg` | Plate III, Part III (Laputa, Balnibarbi, Luggnagg, Glubbdubdrib, Japan) | https://archive.org/details/travelsintosever02swif , page n13 (https://archive.org/download/travelsintosever02swif/page/n13.jpg) | `e92c1263fe16e0597b153cd29ea82b68300d2731ad7e7d17e81beb6058d610d5` |
| `houyhnhnms.jpg` | Plate (marked VI), Part IV (Houyhnhnms Land, "Discovered A.D. 1711") | same item, page n181 (https://archive.org/download/travelsintosever02swif/page/n181.jpg) | `ffc536b9b91c17e5ddac03aaf509f4966fe77036e9479bec92c6a0654ebcecbe` |

- **Author:** engraver unrecorded, printed for Benjamin Motte for Jonathan Swift's book, 1726.
- **Licence:** public domain (published 1726). The Internet Archive items carry no rights restriction; a faithful
  photograph of a public-domain flat work adds no new copyright. The same plates are on Wikimedia Commons marked
  public domain (e.g. https://commons.wikimedia.org/wiki/File:Brobdingnag_map.jpg), but only as small copies.

Processing (scripts kept outside the repo): each page cropped to the plate's ruled border (the Brobdingnag and
Laputa plates lose a few letters at the binding: "New Albion", "Discovered A.D. 170[1]"); resized to 2048 px tall
(Lanczos); converted to luminance, divided by a blurred background estimate to flatten the uneven paper and remove
most show-through from the facing page, then re-inked in dark brown (RGB 38,30,22) on parchment (RGB 238,226,198)
with a faint vignette. JPEG quality 88.

Place positions (`u`,`v`, `located: "scan"`) are where each plate draws the place or its label; Swift's spelling
on the plates differs at times from the text (Mendendo for Mildendo, Tralldragdubh, Glubdrubdrib). Debug overlays
(map overlay, not headset): `captures/maps/gulliver/<view>.overlay.jpg`.
