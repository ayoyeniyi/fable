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

## What the Unity side does (2026-11-14)

`Editor/FableLiving.cs` runs inside `FableBuild.BuildScene` (before the bake) and, for scenes already baked,
`FableLiving.ApplyLiving()` (menu Fable > Apply Living Scenes) re-applies in place without a rebake: meshes keep their
lightmap UVs and renderers their lightmap slots. It always starts again from the glTF originals, so running it twice
is harmless. Generated meshes and materials go to `Assets/Fable/Living/<scene>/`, shared textures to
`Assets/Fable/Living/Shared/`. What it finds, by the renderer's own name or its parent's:

- `water.ocean.*` → `Fable/Water` (Ocean): three Gerstner waves (height and length from `SceneDef.WaterOverride`,
  direction from `SceneDef.WindToward`), two drifting detail-normal layers, sky reflection by Fresnel from the scene's
  fog colour (horizon) and ambient sky colour (overhead) unless the SceneDef gives its own, a sun glint where the
  baked shadow mask lets the sun through, foam from vertex colour **G** and on the crests. The mesh is subdivided to
  about 2.5 m edges (at most ~12k vertices) so the swell has vertices to move. The body colour is the mesh's own
  base-colour texture lit by its lightmap, so baked shadows (a hull's, a cliff's) stay on the water.
- `water.river.*` / `water.stream.*` → `Fable/Water` (River): the detail normals scroll downstream along the direction
  V increases (worked out per vertex at import, so keep V running downstream). No swell.
- `water.pond.*` / `water.puddle.*` → `Fable/Water` (Pond): very slow ripples, no swell.
- `veg.<kind>.*` → `Fable/LivingLit` (same inputs as glTFast's material, so it looks the same; it samples the
  lightmap): sways in the scene wind. Vertex colour **R** is the weight and is never used as a tint. Without vertex
  colour, the weight is the vertex's height above the surface under it (a downward ray against the rest of the room),
  reaching 1 at 0.6 m for grass, 0.7 flowers, 1 crop, 1.2 reeds, 1.8 shrub, 3 leaves, 8 crown. Per-kind amplitude (m
  at weight 1 in a strength-1 wind): grass 0.11, flowers 0.09, crop 0.14, reeds 0.13, shrub 0.05, leaves 0.05
  (mostly flutter), crown 0.12. A gust wave rolls downwind across the scene.
- `cloth.<kind>.*` → `Fable/LivingLit` billow along the normal: sail 0.25 m, flag 0.15, curtain 0.05, washing 0.1.
  Without vertex colour the weight is 0 at the top edge and 1 at the bottom (hung from the top).
- `fx.fire.*` → `living.fire.*`: flame particles (≤32, additive, one soft texture), ember particles (≤14), one
  realtime flickering point light (no shadows, low intensity: the steady light belongs in the bake), and the crackle
  (`amb.fire`) as a positional source. **Radius:** glTF does not carry an empty's display size, so set a custom
  property `radius` on the empty (`e["radius"] = size`) and export with `export_extras=True`; otherwise the empty's
  scale is used if it is not 1, else 0.25 m.
- `fx.candle.*` → a small billboard flame card that flickers. No light, no sound.
- `fx.torch.*` / `fx.lantern.*` → a larger flame card, a flickering light (within the budget) and a quiet hiss
  (`amb.candle`).
- `sound.<kind>.*` → a looping positional source; the clip is `amb.<clip>` with surf→surf, river→river, fire→fire,
  wind-trees→wind-pines, wind→wind-grass, birds→birds, gulls→gulls, rigging→rigging, crowd→tavern, clock→clock,
  rain→rain.
- A modelled flame mesh (the older rooms' `MESH_Flame`) → `Fable/Flame`: unlit, flickers and licks.

The budget above is enforced: fires beyond the third particle system get no particles, lights beyond three none,
sources beyond six are dropped (the build log says so). `LivingScene` (on the environment root) drives the wind
globals (`_FableWind`, `_FableWindTime`) with slow gusts and sets the positional sources' volume from the reader's
ambience setting. Note that `fx.*` names are also script-controlled asset names (`SceneRegistry`, hidden at a beat
reset), so the generated fire is a sibling (`living.fire.*`), not a child, of the empty.

**Rooms built before the conventions** are mapped by name in `FableLiving.Legacy` (for example Odysseus's `MESH_Sea`
→ `water.ocean`, the poppy field's `MESH_PoppyPetal` → `veg.flowers`), and their hearths (Calypso's cave, the hall at
Ithaca) get a fire at the base of the modelled flame.

**Wiring a new room:** in `FableBuild.Scenes` give the SceneDef `Sound` (ambience layers, `"surf:0.8+gulls:0.3"`;
kinds listed in `audio/SOURCES.md`), `Wind` and `WindToward` if the default (0.35 outdoors, 0 indoors) does not
suit, `Music` if it should play another scene's music, and `WaterOverride` for a rougher or calmer sea or a faster
river. Then `FableBuild.BuildScene("<id>")` and `FableBuild.BakeLighting("<id>")` as usual.
