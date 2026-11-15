# Treasure Island map — source

`island.jpg` is Robert Louis Stevenson's map of Treasure Island (drawn 1881, published with the novel by Cassell
in 1883), as printed in the 1885 edition.

- **Commons page:** https://commons.wikimedia.org/wiki/File:Treasure-island-map.jpg
- **File:** https://upload.wikimedia.org/wikipedia/commons/c/c6/Treasure-island-map.jpg (2369x4211)
- **SHA-256 of the download:** `11613521afc96b183c534f2951cabc68690df2f779a56af2ea487e9d047cb85c`
- **Author:** Robert Louis Stevenson (1850–1894). Original source given on Commons: Beinecke Library (Yale).
- **Date:** 1883 (this printing 1885).
- **Licence:** public domain (the author died in 1894; published 1883). Marked public domain on its Commons page.

Processing (scripts kept outside the repo): cropped to the chart and its inscriptions (the plain page margins
removed), resized to 1186x2048 (Lanczos), levels stretched (0.3–97th percentile) and the paper tinted to a warm
parchment (RGB 238,226,198); the red and brown inks are kept. JPEG quality 88.

Place positions (`u`,`v` in `map.json`, `located: "scan"`) are where the chart draws each feature or its label;
Ben Gunn's cave is not drawn and is placed from the text (`approximate`). Debug overlay:
`captures/maps/treasure/island.overlay.jpg` (map overlay, not headset).
