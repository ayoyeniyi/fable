# Map props: scroll, pin, globe stand

Built by `blender/build_map_props.py` (Blender 5.2, headless, re-runnable):

```
/Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_map_props.py -- --export
/Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_map_props.py -- --export --render --samples 96 --captures captures/blender/map-props
```

Output: `out/map-props/map_props.gltf` + `map_props.bin` + `textures/` (glTF separate, node extras exported).
**`out/` is git-ignored** (`.gitignore: out/`): copy the folder into Unity from disk; re-run the script to regenerate it.
This file is kept in git as `docs/MAP_PROPS.md`. Review renders: `captures/blender/map-props/` ("Blender render" in the
file names and burnt into each image).

All textures are painted procedurally in the script with numpy. No external assets.

## Objects (glTF node names) and triangles

| Node | Triangles | What it is |
| --- | --- | --- |
| `scroll` | – | root, origin at the centre of the map sheet |
| `scroll.sheet` | 5120 | the map: 1.0 × 1.0 design mesh, 64 × 40 quads, smooth normals |
| `scroll.roller.left`, `scroll.roller.right` | 92 each | parchment wound on each roller (end caps show the spiral of turns and the walnut core) |
| `scroll.finial.{left,right}.{top,bottom}` | 630 each | turned walnut handle, brass ring and tip |
| **scroll total** | **7824** | under the 8k budget |
| `pin` | 264 | map pin, 25 mm: red glass head (r 4.5 mm), brass needle |
| `globe.stand` → `globe.stand.mesh` | 1712 | brass meridian ring + turned walnut base (sphere not included) |
| `globe.stand.axis` | – | empty at the sphere centre; its local +Y is the tilted spin axis |

The sheet grid is 64 × 40 rather than 96 × 64 to keep the scroll under 8k triangles. That is enough for a gentle
shader height displacement (a few mm, about 9 mm × 10 mm cells at 0.60 × 0.42 m); use tessellation if more is needed.

The three roots are spread along +X in the file only so the glTF previews cleanly. Zero their positions when you instance
them.

Materials: `M_ScrollMap` (sheet, double-sided, base colour = `textures/map_placeholder.png`), `M_ParchmentRoll`
(`parchment_roll.png`), `M_Walnut` (`walnut.png`, dark varnished walnut, roughness 0.32), `M_Brass` (metallic 1,
roughness 0.28), `M_PinGlass` (red glass, roughness 0.08; tint or add emission at runtime to light the pin). All except
the sheet are single-sided.

## Axes and facing

Metres. glTF: +Y up, **the sheet's front faces +Z** (its normal is +Z, so the reader stands on the +Z side looking
toward −Z). The reader's left is −X in glTF. The sheet has a slight belly: its centre sits about 11 mm behind (−Z) its
roller edges, the free top and bottom edges curl up to 7.5 mm toward the reader, and the rolls sit behind the sheet
plane (roll axis at z = −0.0175).

Unity (glTFast or UnityGLTF) mirrors glTF X on import (x → −x) to convert to left-handed. In Unity the front still faces
local **+Z** (`transform.forward`), so turn the scroll root so its forward points at the reader. Because X is mirrored,
`scroll.roller.left` arrives at local x = **+0.30**. It is still on the reader's left as seen from the front. Read the
sign from the imported positions rather than hard-coding it (see the snippet below).

## UVs and the map texture

`scroll.sheet` has one UV set covering 0..1 exactly, no seams. As the reader sees it:

* u = 0 at the map's left edge (left roller), u = 1 at the right edge (right roller);
* glTF `TEXCOORD_0`: v = 0 at the **top** of the map and v = 1 at the bottom (the glTF convention, where image row 0 is
  v = 0). Verified in the export: top-left vertex uv (0, 0), top-right (1, 0), bottom-left (0, 1).
* After a Unity glTF import, v is flipped to Unity's convention: v = 0 bottom, v = 1 top. **Assign a normally imported
  map Texture2D to the base map as it is, with no flip or offset**, and the image appears upright.

`textures/map_placeholder.png` is a test map: **red square = image top-left, green = top-right, blue = bottom-left**,
a red arrow points to the top, a red X at (u 0.42, v 0.44 from the top). The renders show the red square at the
reader's top-left.

To place the pin for a location (u, v) read off the map image, with v measured from the image top, use
`sheet.TransformPoint(new Vector3(sx * (0.5f - u), 0.5f - v, 0))`. Here `sx` is the sign from the snippet below (+1
under glTFast). The sheet's scale maps the unit design to metres. This point lies on the flat plane through the sheet's
edges, and the real surface is up to 11 mm behind it. For an exact contact, raycast from it along −forward against a
MeshCollider on the sheet.

## Edge mask (ragged, darker parchment edge)

The edge is **a separate texture, `textures/scroll_edge_mask.png`**, not a vertex colour, and is not bound in the glTF
material. It uses the same UVs as the map (same 0..1 orientation, with the image top at the map top):

* **RGB**: multiply over the map colour (1 = untouched; darker and browner toward the top and bottom edges, a little
  toward the rollers, with faint foxing spots). Import it with sRGB off (it was painted as linear multipliers).
* **A**: the ragged torn top and bottom edges plus two nicks. Alpha-clip at 0.5.

Shader: `albedo = map.rgb * mask.rgb; clip(mask.a - 0.5)`. The renders preview exactly that. Because the mask is in
UV space it stretches with the sheet, so very tall maps get proportionally deeper tears. That is acceptable from 0.7 to
1.6.

## Scaling for a map's aspect

The sheet is a unit design, so scale it to the map. Choose a width `W` (the default design is 0.60 m) and set
`H = W / aspect` (aspect = image width / height, about 0.7 to 1.6). The exported defaults are W = 0.60, H = 0.42.

| Node | Set |
| --- | --- |
| `scroll.sheet` | `localScale = (W, H, 1)` (z stays 1, so the belly and curl keep their size in metres) |
| `scroll.roller.left/right` | `localPosition = (±W/2, 0, 0)`, `localScale = (1, H, 1)`. The roller's origin is the sheet edge where the sheet leaves the roll, so it sits exactly at the sheet's edge |
| `scroll.finial.<side>.top/bottom` | `localPosition = (±W/2, ±H/2, rollZ)`, unscaled. Keep the imported z (−0.0175 m, the roll axis) |

```csharp
// after import: cache the mirror sign once (glTFast puts roller.left at +x)
float sx = Mathf.Sign(rollerLeft.localPosition.x);          // +1 under glTFast/UnityGLTF
float rollZ = finialLeftTop.localPosition.z;
void FitMap(float W, float aspect) {
    float H = W / aspect;
    sheet.localScale = new Vector3(W, H, 1f);
    rollerLeft.localPosition  = new Vector3( sx * W / 2, 0, 0); rollerLeft.localScale  = new Vector3(1, H, 1);
    rollerRight.localPosition = new Vector3(-sx * W / 2, 0, 0); rollerRight.localScale = new Vector3(1, H, 1);
    finialLeftTop.localPosition     = new Vector3( sx * W / 2,  H / 2, rollZ);
    finialLeftBottom.localPosition  = new Vector3( sx * W / 2, -H / 2, rollZ);
    finialRightTop.localPosition    = new Vector3(-sx * W / 2,  H / 2, rollZ);
    finialRightBottom.localPosition = new Vector3(-sx * W / 2, -H / 2, rollZ);
}
```

The `portrait` render applies exactly this rule for aspect 0.72 (the placeholder is stretched there; a real map would
match its own aspect). An unroll animation can animate `W` from about 0.04 to the target, which closes the rollers
together. For that, also scale the sheet's U tiling/offset if the map should appear to emerge from the rolls rather than
squash.

Node extras (`extras.fable`, a JSON string) restate these rules on each node.

## Pin

`pin`: origin at the needle tip, the pin points **down −Y** (glTF and Unity), total length 25 mm, glass head radius
4.5 mm centred 20.5 mm above the tip. To stick it into the scroll, rotate so local +Y aligns with the sheet's normal
(+Z): `pin.rotation = sheet.rotation * Quaternion.FromToRotation(Vector3.up, Vector3.forward)`, and add a few degrees
of tilt. On the globe: `+Y` = surface normal at the place, tip on the sphere surface (r = 0.18).

## Globe stand

`globe.stand`: origin at the centre of the base's underside (it stands on a table at y = 0). It is made for a
**sphere of radius 0.18 m** centred at **y = 0.322** (the `globe.stand.axis` node). The meridian ring is a flat brass band
(inner radius 0.1865, outer 0.1985, 5 mm thick) in the stand's XY plane. The spin axis is tilted 23.44° from vertical
within that plane; brass pivot pins at both poles reach to r = 0.176. Parent Unity's UV sphere (scale it to radius 0.18)
under `globe.stand.axis` at the local origin and spin it about local +Y. The base footprint is 0.236 m in diameter and the
total height is about 0.52 m.
