# Globe texture — source

`earth.jpg` (4096x2048, equirectangular: left edge longitude -180, top edge latitude +90) is composed from two NASA
Blue Marble images, both public domain (NASA imagery is not subject to copyright in the US; Wikimedia Commons marks
both files public domain):

1. **Land:** *Whole world - land and oceans 12000.jpg*, NASA Goddard Space Flight Center (Blue Marble: Land Surface,
   Ocean Color and Sea Ice, Reto Stöckli, Robert Simmon and colleagues), 24000x12000.
   - Page: https://commons.wikimedia.org/wiki/File:Whole_world_-_land_and_oceans_12000.jpg
   - File: https://upload.wikimedia.org/wikipedia/commons/8/8f/Whole_world_-_land_and_oceans_12000.jpg
   - SHA-256: `e38957ed3999348670d7855569a1e6775a1b2ca789d74f15b04912889d116219`
2. **Ocean floor shading:** *Blue Marble Next Generation + topography + bathymetry.jpg*, Reto Stöckli, NASA Earth
   Observatory, 3600x1800.
   - Page: https://commons.wikimedia.org/wiki/File:Blue_Marble_Next_Generation_%2B_topography_%2B_bathymetry.jpg
   - File: https://upload.wikimedia.org/wikipedia/commons/5/56/Blue_Marble_Next_Generation_%2B_topography_%2B_bathymetry.jpg
   - SHA-256: `062582f953750c05c12514b9ff498b8db5b2c68e1e0563b0bea2f3385be9f5db`

Processing: both resized to 4096x2048 (Lanczos / bicubic); pixels of image 1 that are its flat ocean colour
(RGB 11,10,50, tolerance 18, mask blurred 1.2 px) replaced by image 2, so the land keeps the sharper image and the
sea gets the shelf and ocean-floor shading. JPEG quality 88.

Licence: public domain (NASA). Credit requested by NASA: "NASA Earth Observatory / NASA Goddard Space Flight Center,
Blue Marble".
