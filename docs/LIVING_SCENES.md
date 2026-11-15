# Living scenes: naming conventions (2026-11-14)

Hand-built rooms now move and sound alive. The rooms' Blender scripts mark what should move or sound with the names
below. The Unity side (`Assets/Fable/Scripts/Atmosphere/`, and the FableBuild import) finds those names and attaches
the animated materials, particles, lights and sounds. Both sides keep to this file. If a name changes, change it
here first.

| Blender object name | What it is | What Unity does with it |
|---|---|---|
| `water.ocean.*` | sea surface: open water to the horizon, swell | animated water material (moving swell and ripples, sky reflection, foam where the mesh's vertex colour G is high), surf sound at the shore |
| `water.river.*` / `water.stream.*` | flowing water; its UVs run along the flow (U across, V downstream) | water material scrolling along V, river sound |
| `water.pond.*` / `water.puddle.*` | still water | slow ripples only, no sound unless large |
| `fx.fire.*` (empty) | the base of a hearth or campfire flame; the empty's display size is the fire's radius in metres | flame and ember particles, a flickering warm point light (it adds to the baked light, keep it subtle), crackling fire sound |
| `fx.candle.*` (empty) | the top of a candle's wick | a small flame, a gentle flicker, no sound |
| `fx.torch.*` / `fx.lantern.*` (empty) | a wall torch or a lantern's flame | a medium flame and flicker, quiet hiss |
| `veg.<kind>.*` mesh, kind = `grass`, `leaves`, `crown`, `shrub`, `reeds`, `flowers`, `crop` | foliage that sways in the wind | wind-sway material. Vertex colour **R** is how much a vertex moves (0 at the roots or trunk, 1 at the tips). Without vertex colour, height above the mesh's lowest point is used. |
| `cloth.<kind>.*` mesh, kind = `sail`, `flag`, `curtain`, `washing` | cloth that billows | gentle billow with the same R weight (0 where it is fixed) |
| `sound.<kind>.*` (empty) | a point sound source. kind = `surf`, `river`, `fire`, `wind-trees`, `wind`, `birds`, `gulls`, `rigging`, `crowd`, `clock`, `rain` | a looping positional sound from the scene's sound set at that point |

**Scene-wide ambience** (a bed of sound with no position, e.g. a room's quiet air, distant birds, the sea's hush) is
chosen per scene in FableBuild's `SceneDef.Sound`, from the sound library in `audio/` (see `audio/SOURCES.md`).

**Wind** is one direction and strength per scene (`SceneDef.Wind`), so everything sways together. A gentle breeze is
the default outdoors; indoors there is none, except where a window or door is open.

**Budget (Quest 2, 72 Hz):**
- water: one material per water body, at most 2 water bodies in view
- fire: at most 3 particle systems per scene, at most 1 real-time light per fire
- wind: vertex animation only (no physics)
- sound: at most 6 positional sources plus the ambience
