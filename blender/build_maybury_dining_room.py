"""
Fable: the narrator's dining room at Maybury (The War of the Worlds, book I, chapters 2-3 and 7).

"I remember that dinner table with extraordinary vividness even now. My dear wife's sweet anxious face peering at
me from under the pink lamp shade, the white cloth with its silver and glass table furniture - for in those days even
philosophical writers had many little luxuries - the crimson-purple wine in my glass, are photographically distinct."
"The dinner, which was a cold one, had already been served, and remained neglected on the table."
"At the end of it I sat, tempering nuts with a cigarette ..."

A late-Victorian suburban dining room in a villa on Maybury Hill, on a warm summer evening at dusk. The table is laid
with a white damask cloth, silver and glass: two places, a cold dinner (a cold joint of beef on its dish, a salad,
bread, a pie), the claret decanter and a glass of crimson-purple wine, a dish of nuts, the cruet, and in the middle
the oil lamp with its pink shade. A fire burns low in the cast-iron register grate with its tiled cheeks, under a
black slate mantelpiece with a clock, candlesticks and an overmantel glass. The sash window on the left looks onto
the garden at dusk (the lower sash a little raised, the curtains stirring); a mahogany sideboard with a mirror back
stands ahead, oil paintings in gilt frames on a dark green patterned paper above a brown dado; a Turkey carpet,
dark-stained boards at the edges. No people (the narrator and his wife are left out).

Builds the room procedurally (no downloaded models, textures or HDRIs) with PBR node materials and numpy-painted
pictures and garden, the lamp, the fire, two candles and the dusk at the window as lights, then (by flag) renders
Cycles stills, bakes, merges static meshes by material and exports a .gltf for Unity (helpers in wotw_kit.py).

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet (floor, z=0) at the south end of the table, the door behind
  anchor.reader.look      eye height (1.55 m), 2 m ahead (north, up the table toward the sideboard)
  anchor.scene.centre     the floor under the table
  anchor.room.lamp, anchor.room.fire, anchor.room.window, anchor.room.wine
  Lamp.table (POINT, the oil lamp under its pink shade), Lamp.fire (POINT, low in the grate), Lamp.candles (POINT,
  the mantel candles), Lamp.dusk (SPOT, the last of the daylight in at the window, cool; FableBuild colours Lamp*
  lights warm unless the scene overrides it)
  Living scenes (docs/LIVING_SCENES.md): fx.lantern.0 (the lamp's flame), fx.candle.0 / fx.candle.1 (the mantel
  candles' wicks), fx.fire.0 (the grate; display size = fire radius), cloth.curtain.0 (both window curtains in one
  mesh, vertex colour R = sway weight, 0 at the pole), sound.clock.0 (the mantel clock)
  far.garden (the garden at dusk seen through the window: emissive backdrop)
  Glass: M_Glass (glasses, decanter, sash panes), M_LampGlass (the lamp chimney), M_Liquid (the wine): FableBuild
  swaps them for its URP glass / lamp glass / liquid materials by name.

Axes: metres, Blender +Z up, +Y north (up the table), +X east (the fireplace wall). Room centre at the origin.

Run headless:
  blender -b -P blender/build_maybury_dining_room.py -- --out out/maybury-dining-room --render --quick --res 800
  blender -b -P blender/build_maybury_dining_room.py -- --out out/maybury-dining-room --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wotw_kit as K
from wotw_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, bump_from, c4, obj_xyz, noise_tex, white,
                      combine, tone_ramp, wood, planks, paint, metal, fabric, glass, plain, box, cyl, sphere, torus, lathe,
                      orient, grid_surface, tube, sweep_rect, mesh_from, anchor, marker, Frame, camera, TWO_PI, CardMesh,
                      fbm, sstep, paint_stroke, paint_dot)

args, scene = K.begin("MayburyDiningRoom", "out/maybury-dining-room")
OUT = K.OUT
rnd = random.Random(1894)

# ----------------------------------------------------------------------------- dimensions (metres)
W, L, H = 4.6, 5.6, 3.05          # a villa dining room, 15 ft by 18 ft, 10 ft ceiling
X0, X1, Y0, Y1 = -W / 2, W / 2, -L / 2, L / 2
DADO, PICT = 0.95, 2.45
EYE = 1.55
READER = Vector((0.15, -1.95, 0.0))
LOOK = Vector((0.0, 1.0, 0.0))
TABLE = Vector((0.0, 0.15, 0.0)); TL, TW, TH = 1.95, 1.08, 0.74
WIN_Y, WIN_W, WIN_SILL, WIN_H = 0.35, 1.15, 0.78, 1.95           # the window in the west wall
FIRE_Y, BREAST_W, BREAST_D = 0.25, 1.75, 0.34                    # the chimney breast on the east wall
DOOR_X, DOOR_W, DOOR_H = -0.45, 0.86, 2.15                        # the door in the south wall

# ----------------------------------------------------------------------------- materials
def wallpaper():
    """A small-repeat dark green paper of the 1890s: an olive trellis of stems with stylised flower heads and leaves
    on a deep bottle-green ground, slightly faded, hung in drops with faint joins."""
    m, nt, b = new_mat("M_Wallpaper")
    xyz, X, Y, Z = obj_xyz(nt)
    u = math_(nt, 'ADD', X, Y)                                     # along the wall (walls are axis-aligned)
    rep_w, rep_h = 0.17, 0.17
    cu = math_(nt, 'DIVIDE', u, rep_w); cv = math_(nt, 'DIVIDE', Z, rep_h)
    rowi = math_(nt, 'FLOOR', cv)
    cu2 = math_(nt, 'ADD', cu, math_(nt, 'MULTIPLY', math_(nt, 'FLOORED_MODULO', rowi, 2.0), 0.5))
    fu = math_(nt, 'SUBTRACT', math_(nt, 'FRACT', cu2), 0.5); fv = math_(nt, 'SUBTRACT', math_(nt, 'FRACT', cv), 0.5)
    r = node(nt, "ShaderNodeVectorMath", operation='LENGTH'); nt.links.new(combine(nt, fu, fv, 0.0), r.inputs[0]); rr = r.outputs["Value"]
    ang = math_(nt, 'ARCTAN2', fv, fu)
    petals = math_(nt, 'ADD', 0.16, math_(nt, 'MULTIPLY', math_(nt, 'ABSOLUTE', math_(nt, 'SINE', math_(nt, 'MULTIPLY', ang, 2.5))), 0.09))
    flower = maprange(nt, math_(nt, 'SUBTRACT', rr, petals), 0.01, -0.01, 0.0, 1.0)
    eye_ = maprange(nt, rr, 0.06, 0.04, 0.0, 1.0)
    # the trellis: diagonal stems joining the heads
    d1 = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', math_(nt, 'ADD', cu2, cv)), 0.5))
    d2 = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', math_(nt, 'SUBTRACT', cu2, cv)), 0.5))
    stem = math_(nt, 'MAXIMUM', maprange(nt, d1, 0.03, 0.015, 0.0, 1.0), maprange(nt, d2, 0.03, 0.015, 0.0, 1.0))
    leaf = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'MINIMUM', d1, d2), 0.12)), 0.05, 0.02, 0.0, 1.0),
                 maprange(nt, rr, 0.3, 0.42, 0.0, 1.0))
    ground = (0.040, 0.064, 0.044); olive = (0.075, 0.09, 0.045); head = (0.11, 0.085, 0.045); eyec = (0.16, 0.12, 0.05)
    col = mix_rgb(nt, 'MIX', math_(nt, 'MAXIMUM', stem, math_(nt, 'MULTIPLY', leaf, 0.85)), c4(ground), c4(olive))
    col = mix_rgb(nt, 'MIX', flower, col, c4(head))
    col = mix_rgb(nt, 'MIX', eye_, col, c4(eyec))
    n = noise_tex(nt, xyz, 1.2, 4.0, 0.6)
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 0.18), col, (0.75, 0.75, 0.7, 1))
    drop = math_(nt, 'FRACT', math_(nt, 'DIVIDE', u, 0.53))
    seam = maprange(nt, math_(nt, 'MINIMUM', drop, math_(nt, 'SUBTRACT', 1.0, drop)), 0.0, 0.004, 1.0, 0.0)
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', seam, 0.25), col, (0.02, 0.03, 0.02, 1))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.8
    fine = noise_tex(nt, xyz, 180.0, 2.0, 0.5)
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', flower, 0.5), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.3)), 0.06, 0.001)
    return m

def lincrusta():
    """The dado: embossed Lincrusta, painted and varnished a deep brown, a raised diaper of lozenges."""
    m, nt, b = new_mat("M_Lincrusta")
    xyz, X, Y, Z = obj_xyz(nt)
    u = math_(nt, 'ADD', X, Y)
    cu = math_(nt, 'DIVIDE', u, 0.11); cv = math_(nt, 'DIVIDE', Z, 0.11)
    d = math_(nt, 'ADD', math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', cu), 0.5)), math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', cv), 0.5)))
    raised = maprange(nt, d, 0.42, 0.30, 0.0, 1.0, 'SMOOTHSTEP')
    n = noise_tex(nt, xyz, 2.0, 5.0, 0.6)
    col = mix_rgb(nt, 'MIX', raised, (0.055, 0.030, 0.016, 1), (0.10, 0.058, 0.030, 1))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 0.2), col, (0.7, 0.7, 0.7, 1))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, raised, 0.55, 0.32), b.inputs["Roughness"])
    bump_from(nt, b, raised, 0.6, 0.004)
    return m

def turkey_carpet():
    """A Turkey carpet: a madder-red field with a lattice of indigo and ivory lozenges, a wide indigo main border with
    guard stripes, worn paler along the path round the table. Object coords: the carpet is centred on the table."""
    m, nt, b = new_mat("M_Carpet")
    xyz, X, Y, Z = obj_xyz(nt)
    cx = math_(nt, 'SUBTRACT', X, TABLE.x); cy = math_(nt, 'SUBTRACT', Y, TABLE.y)
    hw, hl = 1.55, 2.05
    ex = math_(nt, 'SUBTRACT', hw, math_(nt, 'ABSOLUTE', cx)); ey = math_(nt, 'SUBTRACT', hl, math_(nt, 'ABSOLUTE', cy))
    e = math_(nt, 'MINIMUM', ex, ey)
    border = maprange(nt, e, 0.36, 0.34, 0.0, 1.0)
    guard = math_(nt, 'MAXIMUM', maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', e, 0.05)), 0.02, 0.01, 0.0, 1.0),
                  maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', e, 0.32)), 0.02, 0.01, 0.0, 1.0))
    # border motif: a running row of medallions along the band
    along = math_(nt, 'ADD', math_(nt, 'MULTIPLY', maprange(nt, ex, 0.0, 0.0001, 1.0, 0.0), cy), cx)
    bm_ = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', cx, cy), 0.28)), 0.5))
    bmot = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'ADD', bm_, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', e, 0.19))), 0.2, 0.14, 0.0, 1.0), border)
    # field lattice
    fu = math_(nt, 'DIVIDE', math_(nt, 'ADD', cx, cy), 0.42); fv = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', cx, cy), 0.42)
    lu = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', fu), 0.5)); lv = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', fv), 0.5))
    lat = maprange(nt, math_(nt, 'MINIMUM', lu, lv), 0.035, 0.015, 0.0, 1.0)
    gem = maprange(nt, math_(nt, 'ADD', lu, lv), 0.22, 0.16, 0.0, 1.0)
    gem2 = maprange(nt, math_(nt, 'ADD', lu, lv), 0.10, 0.07, 0.0, 1.0)
    red = (0.22, 0.035, 0.025); indigo = (0.025, 0.035, 0.08); ivory = (0.42, 0.36, 0.25); gold = (0.30, 0.18, 0.05)
    col = mix_rgb(nt, 'MIX', lat, c4(red), c4(indigo))
    col = mix_rgb(nt, 'MIX', gem, col, c4(indigo))
    col = mix_rgb(nt, 'MIX', gem2, col, c4(gold))
    bcol = mix_rgb(nt, 'MIX', bmot, c4(indigo), c4(red))
    col = mix_rgb(nt, 'MIX', border, col, bcol)
    col = mix_rgb(nt, 'MIX', guard, col, c4(ivory))
    n = noise_tex(nt, xyz, 3.0, 5.0, 0.6); fine = noise_tex(nt, xyz, 300.0, 2.0, 0.5)
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0.0, 0.25), col, (0.7, 0.7, 0.7, 1))
    wear = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'MINIMUM', math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'ABSOLUTE', cx), 0.95)),
                                                     math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'ABSOLUTE', cy), 1.4))), 0.35, 0.0, 0.0, 0.35),
                 maprange(nt, n.outputs["Fac"], 0.35, 0.65, 0.3, 1.0))
    col = mix_rgb(nt, 'MIX', wear, col, (0.22, 0.16, 0.11, 1))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    b.inputs["Sheen Weight"].default_value = 0.4
    bump_from(nt, b, fine.outputs["Fac"], 0.25, 0.002)
    return m

def damask():
    """White damask cloth: a self pattern of satin and matt in the weave, crease lines from the linen press."""
    m, nt, b = new_mat("M_Damask")
    xyz, X, Y, Z = obj_xyz(nt)
    cu = math_(nt, 'DIVIDE', X, 0.16); cv = math_(nt, 'DIVIDE', Y, 0.16)
    fu = math_(nt, 'SUBTRACT', math_(nt, 'FRACT', cu), 0.5); fv = math_(nt, 'SUBTRACT', math_(nt, 'FRACT', cv), 0.5)
    rr = node(nt, "ShaderNodeVectorMath", operation='LENGTH'); nt.links.new(combine(nt, fu, fv, 0.0), rr.inputs[0])
    ang = math_(nt, 'ARCTAN2', fv, fu)
    motif = maprange(nt, math_(nt, 'SUBTRACT', rr.outputs["Value"], math_(nt, 'ADD', 0.24, math_(nt, 'MULTIPLY', math_(nt, 'SINE', math_(nt, 'MULTIPLY', ang, 4.0)), 0.08))), 0.01, -0.01, 0.0, 1.0)
    crease = math_(nt, 'MAXIMUM', maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', X, TABLE.x), 0.54)), 0.5)), 0.006, 0.0, 0.0, 1.0),
                    maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', Y, TABLE.y), 0.65)), 0.5)), 0.006, 0.0, 0.0, 1.0))
    col = mix_rgb(nt, 'MIX', motif, (0.70, 0.69, 0.66, 1), (0.76, 0.75, 0.72, 1))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', crease, 0.35), col, (0.85, 0.85, 0.83, 1))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, motif, 0.75, 0.45), b.inputs["Roughness"])
    b.inputs["Sheen Weight"].default_value = 0.4
    bump_from(nt, b, math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', motif, 0.3), crease), 0.15, 0.002)
    return m

def tiles():
    """Fireplace cheeks and hearth: glazed tiles, deep green with an ochre flower, glossy, dark grout."""
    m, nt, b = new_mat("M_Tiles")
    xyz, X, Y, Z = obj_xyz(nt)
    u = math_(nt, 'ADD', Y, X)
    cu = math_(nt, 'DIVIDE', u, 0.152); cv = math_(nt, 'DIVIDE', math_(nt, 'ADD', Z, math_(nt, 'MULTIPLY', X, 0.0)), 0.152)
    fu = math_(nt, 'SUBTRACT', math_(nt, 'FRACT', cu), 0.5); fv = math_(nt, 'SUBTRACT', math_(nt, 'FRACT', cv), 0.5)
    grout = maprange(nt, math_(nt, 'MAXIMUM', math_(nt, 'ABSOLUTE', fu), math_(nt, 'ABSOLUTE', fv)), 0.47, 0.49, 0.0, 1.0)
    rr = node(nt, "ShaderNodeVectorMath", operation='LENGTH'); nt.links.new(combine(nt, fu, fv, 0.0), rr.inputs[0])
    ang = math_(nt, 'ARCTAN2', fv, fu)
    flower = maprange(nt, math_(nt, 'SUBTRACT', rr.outputs["Value"], math_(nt, 'ADD', 0.16, math_(nt, 'MULTIPLY', math_(nt, 'ABSOLUTE', math_(nt, 'SINE', math_(nt, 'MULTIPLY', ang, 2.0))), 0.14))), 0.01, -0.01, 0.0, 1.0)
    col = mix_rgb(nt, 'MIX', flower, (0.025, 0.07, 0.05, 1), (0.36, 0.22, 0.06, 1))
    col = mix_rgb(nt, 'MIX', grout, col, (0.05, 0.045, 0.04, 1))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, grout, 0.12, 0.8), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'SUBTRACT', 0.0, grout), 0.4, 0.002)
    return m

M_WALLP = wallpaper()
M_DADO = lincrusta()
M_CARPET = turkey_carpet()
M_CLOTH = damask()
M_TILES = tiles()
M_FLOOR = planks("M_Floorboards", 0.14, 3.2, [(0.07, 0.035, 0.018), (0.085, 0.045, 0.022), (0.065, 0.032, 0.016)], (0.02, 0.012, 0.008),
                 along='Y', rough=0.42, seed=1.0, grain_k=0.3)
M_CEIL = paint("M_Ceiling", (0.52, 0.49, 0.42), rough=0.85, mottle=0.08, scale=1.5, bumpk=0.03)
M_FRIEZE = paint("M_Frieze", (0.40, 0.34, 0.24), rough=0.8, mottle=0.1, scale=2.0, bumpk=0.03)
M_PLASTER = paint("M_Mouldings", (0.50, 0.47, 0.40), rough=0.6, mottle=0.06, scale=4.0, bumpk=0.02)
M_JOINERY = wood("M_GrainedDoor", (0.17, 0.085, 0.035), (0.08, 0.035, 0.014), rough=0.35, along='Z', seed=2.0, ring=7.0, contrast=0.5)
M_MAHOG = wood("M_Mahogany", (0.19, 0.065, 0.03), (0.085, 0.028, 0.013), rough=0.25, along='X', seed=0.7, ring=7.0, contrast=0.45)
M_SLATE = metal("M_BlackSlate", (0.022, 0.022, 0.024), rough=0.18, metallic=0.0, scale=3.0, rough_var=0.06)
M_IRON = metal("M_CastIron", (0.03, 0.03, 0.03), rough=0.42, metallic=0.6, tarnish=(0.04, 0.035, 0.03))
M_BRASS = metal("M_Brass", (0.72, 0.50, 0.22), rough=0.25, tarnish=(0.48, 0.34, 0.15))
M_SILVER = metal("M_Silver", (0.80, 0.79, 0.76), rough=0.16, tarnish=(0.55, 0.52, 0.48), scale=12.0)
M_GILT = metal("M_Gilt", (0.62, 0.45, 0.18), rough=0.35, tarnish=(0.33, 0.24, 0.10))
M_CHINA = paint("M_China", (0.78, 0.77, 0.74), rough=0.12, mottle=0.03, scale=8.0, bumpk=0.005)
M_GLASS = glass("M_Glass", (0.92, 0.95, 0.93), rough=0.02)
M_LAMPGLASS = glass("M_LampGlass", (0.95, 0.93, 0.88), rough=0.05)
M_WINE = glass("M_Liquid", (0.30, 0.01, 0.06), rough=0.05)
M_SHADE = plain("M_LampShade", (0.80, 0.36, 0.38), rough=0.7, emission=(1.0, 0.42, 0.40), strength=0.7)
M_FONT = glass("M_LampFontGlass", (0.75, 0.55, 0.65), rough=0.05)
M_LEATHER = fabric("M_Leather", (0.09, 0.025, 0.018), rough=0.45, sheen=0.15, weave=False, var=0.25)
M_VELVET = fabric("M_Velvet", (0.10, 0.018, 0.022), rough=0.9, scale=200.0, sheen=0.8, var=0.2)
M_EMBERS = plain("M_Embers", (0.5, 0.12, 0.02), rough=0.9, emission=(1.0, 0.30, 0.05), strength=8.0)
M_COAL = metal("M_Coal", (0.02, 0.019, 0.018), rough=0.55, metallic=0.0, scale=20.0)
M_MIRROR = metal("M_Mirror", (0.85, 0.85, 0.83), rough=0.03, scale=5.0, rough_var=0.01)
M_WAX = paint("M_Wax", (0.80, 0.77, 0.68), rough=0.4, mottle=0.03, scale=10.0, bumpk=0.0)
M_FOOD = paint("M_ColdBeef", (0.17, 0.055, 0.035), rough=0.55, mottle=0.25, scale=25.0, bumpk=0.1)
M_CRUST = paint("M_Crust", (0.21, 0.10, 0.035), rough=0.7, mottle=0.25, scale=15.0, bumpk=0.15)
M_GREENS = paint("M_Salad", (0.08, 0.20, 0.04), rough=0.5, mottle=0.4, scale=30.0, bumpk=0.2)
M_NUTS = paint("M_Nuts", (0.20, 0.11, 0.05), rough=0.6, mottle=0.3, scale=40.0, bumpk=0.3)
M_DIAL = paint("M_Dial", (0.70, 0.67, 0.58), rough=0.3, mottle=0.04, scale=10.0, bumpk=0.0)
M_FRAME = paint("M_SashPaint", (0.62, 0.60, 0.54), rough=0.4, mottle=0.05, scale=4.0, bumpk=0.01)

# ----------------------------------------------------------------------------- numpy pictures and the garden at dusk
def oil_painting(W_=256, Hh=192, seed=0, kind="landscape"):
    """A small Victorian oil landscape, darkened by varnish: sky, a far line of hills, trees, a pool of light."""
    rs = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:Hh, 0:W_].astype(np.float32); u, v = xx / W_, yy / Hh
    sky = np.array([0.32, 0.30, 0.22]) * (0.6 + 0.6 * v[..., None]) + np.array([0.05, 0.04, 0.0])
    hz = 0.42 + 0.06 * fbm(u * 3 + seed, np.zeros_like(u), 3, seed=seed)
    land = np.array([0.10, 0.09, 0.05]) * (0.7 + 0.6 * fbm(u * 6, v * 6, 4, seed=seed + 1)[..., None])
    col = np.where((v > hz)[..., None], sky * (0.85 + 0.3 * fbm(u * 4, v * 8, 4, seed=seed + 2)[..., None]), land)
    trees = (v < hz + 0.35 * fbm(u * 9 + 3, np.zeros_like(u), 3, seed=seed + 3) * sstep(0.2, 0.5, fbm(u * 3, np.zeros_like(u) + 1, 2, seed=seed + 4))) & (v > hz - 0.05)
    col = np.where(trees[..., None], np.array([0.05, 0.06, 0.03]) * (0.7 + 0.6 * fbm(u * 20, v * 20, 3, seed=seed + 5)[..., None]), col)
    water = (v < hz - 0.08) & (v > hz - 0.2) & (np.abs(u - 0.5 - 0.1 * np.sin(v * 9)) < 0.25)
    col = np.where(water[..., None], sky[::-1] * 0.7, col)
    col = col * np.array([1.0, 0.92, 0.72]) * 0.9
    rgba = np.ones((Hh, W_, 4), np.float32); rgba[..., :3] = np.clip(col, 0, 1)
    return rgba

def garden_dusk(W_=1024, Hh=768, seed=21):
    """The view from the window: a summer garden ten minutes after sunset - lawn going grey, the dark masses of a
    laurel hedge and a lilac, an apple tree, the garden wall and its gate, the pines of Maybury Hill black against a
    sky fading from a pale green-gold glow to deep blue, one bright star."""
    yy, xx = np.mgrid[0:Hh, 0:W_].astype(np.float32); u, v = xx / W_, yy / Hh
    top = np.array([0.020, 0.040, 0.11]); mid = np.array([0.10, 0.13, 0.20]); low = np.array([0.32, 0.30, 0.22])
    t = np.clip((v - 0.35) / 0.65, 0, 1)
    sky = low * (1 - t[..., None]) ** 2 + mid * 2 * t[..., None] * (1 - t[..., None]) + top * t[..., None] ** 2
    sky = sky + np.array([0.10, 0.07, 0.03]) * np.exp(-((u - 0.75) / 0.35) ** 2)[..., None] * (1 - t[..., None]) ** 3
    col = sky.copy()
    ridge = 0.40 + 0.08 * fbm(u * 4, np.zeros_like(u), 4, seed=seed) + 0.06 * sstep(0.55, 0.8, fbm(u * 20, np.zeros_like(u), 2, seed=seed + 1))
    col = np.where((v < ridge)[..., None], np.array([0.012, 0.016, 0.014]), col)
    wall = 0.26
    col = np.where((v < wall)[..., None], np.array([0.05, 0.035, 0.03]) * (0.8 + 0.4 * fbm(u * 60, v * 20, 2, seed=seed + 2)[..., None]), col)
    lawn = 0.18
    col = np.where((v < lawn)[..., None], np.array([0.035, 0.05, 0.03]) * (0.8 + 0.4 * fbm(u * 8, v * 30, 3, seed=seed + 3)[..., None]), col)
    # hedges and shrubs, an apple tree
    for (cx, w, h, c) in ((0.12, 0.2, 0.42, (0.012, 0.022, 0.012)), (0.88, 0.22, 0.38, (0.016, 0.024, 0.014)), (0.55, 0.12, 0.30, (0.02, 0.025, 0.015))):
        prof = h + 0.06 * fbm(u * 25, np.zeros_like(u) + cx * 10, 3, seed=seed + 4) - ((u - cx) / w) ** 2 * h
        col = np.where(((v < prof) & (v > 0.1))[..., None], np.array(c) * (0.7 + 0.6 * fbm(u * 30, v * 30, 3, seed=seed + 5)[..., None]), col)
    tr = (np.abs(u - 0.36 - 0.01 * np.sin(v * 30)) < 0.008) & (v < 0.52)
    col = np.where(tr[..., None], np.array([0.02, 0.018, 0.015]), col)
    crown = ((u - 0.36) / 0.15) ** 2 + ((v - 0.6) / 0.14) ** 2 < 1.0 - 0.6 * fbm(u * 18, v * 18, 3, seed=seed + 6)
    col = np.where(crown[..., None], np.array([0.016, 0.026, 0.014]), col)
    # the first star
    col += np.exp(-(((xx - W_ * 0.68) ** 2 + (yy - Hh * 0.86) ** 2) / 2.0))[..., None] * np.array([0.6, 0.6, 0.55])
    rgba = np.ones((Hh, W_, 4), np.float32); rgba[..., :3] = np.clip(col, 0, 1)
    return rgba

M_GARDEN = K.card_material("M_GardenDusk", K.image_from("T_GardenDusk", garden_dusk()), rough=1.0, clip=False, emissive=True)
PAINTINGS = [K.card_material(f"M_Painting{i}", K.image_from(f"T_Painting{i}", oil_painting(seed=7 + i * 5)), rough=0.35, clip=False) for i in range(3)]

# ----------------------------------------------------------------------------- the shell: floor, walls with openings, ceiling, mouldings
def quad(name, pts, mat, uv=False, want=None):
    o = mesh_from(name, pts, [(0, 1, 2, 3)], mat, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)] if uv else None)
    if want is not None: orient(o, lambda c: Vector(want))
    return o

box("FloorBoards", (W, L, 0.02), (0, 0, -0.01), M_FLOOR)
quad("Ceiling", [(X0, Y0, H), (X1, Y0, H), (X1, Y1, H), (X0, Y1, H)], M_CEIL, want=(0, 0, -1))

def wall_band(name, axis, const, a0, a1, z0, z1, holes, mat, inward):
    """A wall strip between z0 and z1 along one wall, skipping rectangular holes (a, b, zlo, zhi) in wall coords."""
    cuts = sorted(set([a0, a1] + [h[0] for h in holes] + [h[1] for h in holes]))
    zs = sorted(set([z0, z1] + [min(max(h[2], z0), z1) for h in holes] + [min(max(h[3], z0), z1) for h in holes]))
    vs, faces = [], []
    def P(a, z): return (a, const, z) if axis == 'x' else (const, a, z)
    for i in range(len(cuts) - 1):
        for j in range(len(zs) - 1):
            am, zm = (cuts[i] + cuts[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
            if any(h[0] < am < h[1] and h[2] < zm < h[3] for h in holes): continue
            k = len(vs); vs += [P(cuts[i], zs[j]), P(cuts[i + 1], zs[j]), P(cuts[i + 1], zs[j + 1]), P(cuts[i], zs[j + 1])]
            faces.append((k, k + 1, k + 2, k + 3))
    o = mesh_from(name, vs, faces, mat)
    orient(o, lambda c: Vector(inward))
    return o

WIN_HOLE = (WIN_Y - WIN_W / 2, WIN_Y + WIN_W / 2, WIN_SILL, WIN_SILL + WIN_H)
DOOR_HOLE = (DOOR_X - DOOR_W / 2, DOOR_X + DOOR_W / 2, -1.0, DOOR_H)
BREAST = (FIRE_Y - BREAST_W / 2, FIRE_Y + BREAST_W / 2)
walls = [("S", 'x', Y0, X0, X1, [DOOR_HOLE], (0, 1, 0)), ("N", 'x', Y1, X0, X1, [], (0, -1, 0)),
         ("W", 'y', X0, Y0, Y1, [WIN_HOLE], (1, 0, 0)), ("E", 'y', X1, Y0, Y1, [], (-1, 0, 0))]
for nm, ax, const, a0, a1, holes, inw in walls:
    wall_band(f"Dado{nm}", ax, const, a0, a1, 0.0, DADO, holes, M_DADO, inw)
    wall_band(f"Paper{nm}", ax, const, a0, a1, DADO, PICT, holes, M_WALLP, inw)
    wall_band(f"Frieze{nm}", ax, const, a0, a1, PICT, H, holes, M_FRIEZE, inw)
# the chimney breast stands proud of the east wall: its face and returns carry the same paper and dado
bx = X1 - BREAST_D
for nm, z0, z1, mat in (("Dado", 0.0, DADO, M_DADO), ("Paper", DADO, PICT, M_WALLP), ("Frieze", PICT, H, M_FRIEZE)):
    holes = [(FIRE_Y - 0.78, FIRE_Y + 0.78, -1, 1.22)]
    wall_band(f"Breast{nm}", 'y', bx, BREAST[0], BREAST[1], z0, z1, holes if z0 < 1.22 else [], mat, (-1, 0, 0))
    for sy in (BREAST[0], BREAST[1]):
        quad(f"BreastReturn{nm}{sy}", [(bx, sy, z0), (X1, sy, z0), (X1, sy, z1), (bx, sy, z1)], mat, want=(0, -1 if sy == BREAST[0] else 1, 0))

def run_moulding(name, z, prof_w, prof_h, mat, skip=()):
    """Skirting, dado rail, picture rail, cornice: a box strip round the room's perimeter (and the breast)."""
    segs = [((X0, Y0), (X1, Y0)), ((X1, Y0), (X1, BREAST[0])), ((bx, BREAST[0]), (bx, BREAST[1])), ((X1, BREAST[1]), (X1, Y1)),
            ((X1, Y1), (X0, Y1)), ((X0, Y1), (X0, Y0))]
    for i, (a, b_) in enumerate(segs):
        a, b_ = Vector((*a, 0)), Vector((*b_, 0)); d = (b_ - a); Ln = d.length; d.normalize()
        n = Vector((-d.y, d.x, 0))                                        # inward for a clockwise-from-inside walk
        if (Vector((0, 0, 0)) - (a + b_) / 2).dot(n) < 0: n = -n
        pieces = [(0.0, Ln)]
        for (s0, s1, axis_, const) in skip:
            new = []
            for (p0, p1) in pieces:
                if (axis_ == 'x' and abs(a.y - const) < 1e-3 and abs(b_.y - const) < 1e-3) or (axis_ == 'y' and abs(a.x - const) < 1e-3 and abs(b_.x - const) < 1e-3):
                    t0 = ((s0 - (a.x if axis_ == 'x' else a.y)) / ((b_.x - a.x) if axis_ == 'x' else (b_.y - a.y))) * Ln
                    t1 = ((s1 - (a.x if axis_ == 'x' else a.y)) / ((b_.x - a.x) if axis_ == 'x' else (b_.y - a.y))) * Ln
                    t0, t1 = min(t0, t1), max(t0, t1)
                    if p0 < t0: new.append((p0, min(p1, t0)))
                    if p1 > t1: new.append((max(p0, t1), p1))
                else: new.append((p0, p1))
            pieces = new
        for j, (p0, p1) in enumerate(pieces):
            if p1 - p0 < 0.02: continue
            c = a + d * ((p0 + p1) / 2) + n * (prof_w / 2)
            sz = (abs(d.x) * (p1 - p0) + abs(n.x) * prof_w, abs(d.y) * (p1 - p0) + abs(n.y) * prof_w, prof_h)
            box(f"{name}{i}_{j}", sz, (c.x, c.y, z), mat, bevel=min(prof_w, prof_h) * 0.3)
door_skip = (DOOR_X - DOOR_W / 2 - 0.08, DOOR_X + DOOR_W / 2 + 0.08, 'x', Y0)
win_skip = (WIN_Y - WIN_W / 2 - 0.09, WIN_Y + WIN_W / 2 + 0.09, 'y', X0)
fire_skip = (FIRE_Y - 0.8, FIRE_Y + 0.8, 'y', bx)
run_moulding("Skirting", 0.13, 0.025, 0.26, M_JOINERY, skip=(door_skip, fire_skip))
run_moulding("DadoRail", DADO, 0.03, 0.05, M_JOINERY, skip=(door_skip, win_skip))
run_moulding("PictureRail", PICT, 0.025, 0.04, M_JOINERY, skip=(door_skip,) if DOOR_H > PICT else ())
run_moulding("Cornice", H - 0.08, 0.13, 0.16, M_PLASTER)
lathe("CeilingRose", [(0.0, H - 0.07), (0.12, H - 0.065), (0.2, H - 0.04), (0.28, H - 0.03), (0.30, H - 0.012), (0.0, H - 0.005)], (TABLE.x, TABLE.y, 0), M_PLASTER, steps=32)

# ----------------------------------------------------------------------------- the door (south wall, behind the reader)
df = Frame((DOOR_X, Y0), 0.0)
for sx in (-1, 1):
    df.box(f"DoorArch{sx}", (0.09, 0.03, DOOR_H + 0.09), (sx * (DOOR_W / 2 + 0.045), 0.015, (DOOR_H + 0.09) / 2), M_JOINERY, bevel=0.008)
df.box("DoorHead", (DOOR_W + 0.18, 0.03, 0.09), (0, 0.015, DOOR_H + 0.045), M_JOINERY, bevel=0.008)
df.box("DoorLeaf", (DOOR_W - 0.02, 0.045, DOOR_H - 0.01), (0, -0.02, DOOR_H / 2), M_JOINERY)
for (px, pz, pw, ph) in ((-0.2, 1.55, 0.3, 0.75), (0.2, 1.55, 0.3, 0.75), (-0.2, 0.55, 0.3, 0.75), (0.2, 0.55, 0.3, 0.75)):
    df.box(f"DoorPanel{px}{pz}", (pw, 0.012, ph), (px, 0.007, pz), M_JOINERY, bevel=0.01)
df.cyl("DoorKnob", 0.028, 0.06, (DOOR_W / 2 - 0.08, 0.04, 1.0), M_BRASS, verts=14, rot=(math.pi / 2, 0, 0))
df.box("DoorPlate", (0.05, 0.006, 0.18), (DOOR_W / 2 - 0.08, 0.026, 1.0), M_BRASS, bevel=0.003)

# ----------------------------------------------------------------------------- the window (west wall): sashes, shutters' boxing, sill, curtains
wf = Frame((X0, WIN_Y), -math.pi / 2)            # +y into the room (east), x along the wall (northward = -x here)
D_REV = 0.30                                     # wall thickness at the reveal
for sx in (-1, 1):
    wf.box(f"WinArch{sx}", (0.09, 0.03, WIN_H + 0.09), (sx * (WIN_W / 2 + 0.045), 0.015, WIN_SILL + (WIN_H + 0.09) / 2 - 0.045), M_JOINERY, bevel=0.008)
    wf.box(f"WinReveal{sx}", (0.02, D_REV, WIN_H), (sx * (WIN_W / 2 + 0.01), -D_REV / 2, WIN_SILL + WIN_H / 2), M_FRAME)
wf.box("WinHead", (WIN_W + 0.18, 0.03, 0.09), (0, 0.015, WIN_SILL + WIN_H + 0.045), M_JOINERY, bevel=0.008)
wf.box("WinSoffit", (WIN_W, D_REV, 0.02), (0, -D_REV / 2, WIN_SILL + WIN_H + 0.01), M_FRAME)
wf.box("WinBoard", (WIN_W + 0.16, D_REV + 0.06, 0.035), (0, -D_REV / 2 + 0.03, WIN_SILL - 0.017), M_JOINERY, bevel=0.006)
wf.box("WinApron", (WIN_W + 0.1, 0.025, 0.12), (0, 0.012, WIN_SILL - 0.1), M_JOINERY, bevel=0.005)
SASH_Y = -0.20; RAISE = 0.17
def sash(name, z0, h, y):
    wf.box(f"{name}Top", (WIN_W, 0.05, 0.05), (0, y, z0 + h - 0.025), M_FRAME)
    wf.box(f"{name}Bot", (WIN_W, 0.05, 0.07), (0, y, z0 + 0.035), M_FRAME)
    for sx in (-1, 1): wf.box(f"{name}Stile{sx}", (0.05, 0.05, h), (sx * (WIN_W / 2 - 0.025), y, z0 + h / 2), M_FRAME)
    wf.box(f"{name}Bar", (0.022, 0.035, h), (0, y, z0 + h / 2), M_FRAME)
    wf.box(f"{name}Pane", (WIN_W - 0.06, 0.006, h - 0.1), (0, y, z0 + h / 2), M_GLASS)
hh = WIN_H / 2 + 0.03
sash("UpperSash", WIN_SILL + WIN_H - hh, hh, SASH_Y - 0.055)
sash("LowerSash", WIN_SILL + RAISE, hh, SASH_Y)
wf.box("WinMeetRail", (WIN_W, 0.05, 0.035), (0, SASH_Y - 0.055, WIN_SILL + WIN_H - hh + 0.02), M_FRAME)
wf.cyl("SashLift0", 0.012, 0.04, (-0.3, SASH_Y + 0.04, WIN_SILL + RAISE + 0.05), M_BRASS, verts=8, rot=(math.pi / 2, 0, 0))
wf.cyl("SashLift1", 0.012, 0.04, (0.3, SASH_Y + 0.04, WIN_SILL + RAISE + 0.05), M_BRASS, verts=8, rot=(math.pi / 2, 0, 0))
wf.box("OutsideSill", (WIN_W + 0.1, 0.14, 0.05), (0, -D_REV - 0.05, WIN_SILL - 0.04), M_FRAME)
# the curtain pole and the curtains (cloth.curtain.*: corrugated folds, weight 0 at the pole, 1 at the hem)
POLE_Z = WIN_SILL + WIN_H + 0.22
tube("CurtainPole", [wf.p(-WIN_W / 2 - 0.42, 0.10, POLE_Z), wf.p(WIN_W / 2 + 0.42, 0.10, POLE_Z)], 0.02, M_BRASS, sides=10)
for sx in (-1, 1):
    sphere(f"PoleFinial{sx}", 0.04, wf.p(sx * (WIN_W / 2 + 0.46), 0.10, POLE_Z), M_BRASS, seg=10)
    lathe(f"PoleBracket{sx}", [(0.0, 0.0), (0.015, 0.0), (0.015, 0.11), (0.0, 0.11)], wf.p(sx * (WIN_W / 2 + 0.3), 0.0, POLE_Z), M_BRASS, steps=8,
          rot=Matrix.Rotation(-math.pi / 2, 3, 'Z') @ Matrix.Rotation(math.pi / 2, 3, 'X') if False else Matrix.Rotation(math.pi / 2, 3, 'Y'))
def curtain(idx, x_in, x_out, gather):
    """A heavy velvet curtain hanging from the pole in deep folds, drawn back to one side of the window."""
    cm = CardMesh(f"cloth.curtain.{idx}")
    nu, nv = 28, 12
    z_top, z_bot = POLE_Z - 0.03, 0.02
    grid = []
    for j in range(nv + 1):
        t = j / nv; z = z_top + (z_bot - z_top) * t
        row = []
        for i in range(nu + 1):
            s = i / nu
            x = x_out + (x_in - x_out) * s * (1 - gather * t * (1 - t) * 1.2)
            fold = math.sin(s * nu * math.pi * 0.5) * (0.045 + 0.02 * t)
            row.append(Vector(wf.p(x, 0.06 + fold, z)))
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            corners = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            uvs = [(i / nu, 1 - j / nv), ((i + 1) / nu, 1 - j / nv), ((i + 1) / nu, 1 - (j + 1) / nv), (i / nu, 1 - (j + 1) / nv)]
            nrm = []
            for (ii, jj) in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                s = ii / nu
                slope = math.cos(s * nu * math.pi * 0.5)
                nrm.append((Matrix.Rotation(-math.pi / 2, 3, 'Z') @ Vector((-slope * 0.6, 1.0, 0.0))).normalized())
            wts = [min(1.0, (jj / nv) ** 1.3) for (ii, jj) in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
            cm.quad(corners, uvs, nrm, wts)
    return cm.finish(M_VELVET)
curtain(0, -WIN_W / 2 + 0.08, -WIN_W / 2 - 0.40, 0.25)
curtain(1, WIN_W / 2 - 0.08, WIN_W / 2 + 0.40, 0.25)
# the garden beyond, a little below and well out from the glass
gp = [Vector(wf.p(-4.2, -6.5, -0.6)), Vector(wf.p(4.2, -6.5, -0.6)), Vector(wf.p(4.2, -6.5, 5.4)), Vector(wf.p(-4.2, -6.5, 5.4))]
quad("GardenDusk", [tuple(p) for p in gp], M_GARDEN, uv=True, want=tuple(Vector(wf.p(0, 1, 0)) - Vector(wf.p(0, 0, 0))))
K.KEEP_UV.add("M_GardenDusk")

# ----------------------------------------------------------------------------- the fireplace (east wall): grate, tiled cheeks, hearth, slate mantel, overmantel glass
ff = Frame((bx, FIRE_Y), math.pi / 2)            # +y into the room (west), x along the breast (southward = +x... local)
OPEN_W, OPEN_H = 0.92, 0.95
# slate chimneypiece: jambs, frieze, shelf
for sx in (-1, 1):
    ff.box(f"MantelJamb{sx}", (0.2, 0.08, 1.1), (sx * 0.66, 0.04, 0.55), M_SLATE, bevel=0.008)
    ff.box(f"MantelCorbel{sx}", (0.22, 0.13, 0.12), (sx * 0.66, 0.065, 1.12), M_SLATE, bevel=0.01)
ff.box("MantelFrieze", (1.52, 0.08, 0.2), (0, 0.04, 1.1), M_SLATE, bevel=0.006)
ff.box("MantelShelf", (1.66, 0.24, 0.045), (0, 0.10, 1.225), M_SLATE, bevel=0.01)
# tiled cheeks and the cast-iron register grate with its arched opening
for sx in (-1, 1):
    ff.box(f"Cheek{sx}", (0.17, 0.02, 0.92), (sx * 0.475, 0.01, 0.46), M_TILES)
ff.box("CheekHead", (0.92, 0.02, 0.1), (0, 0.01, 0.97), M_TILES)
ff.box("GrateFrame", (0.78, 0.04, 0.85), (0, 0.0, 0.425), M_IRON)
# the arched opening: a dark recess made of an iron back and an arched hood
ff.box("FireBack", (0.5, 0.02, 0.55), (0, -0.28, 0.42), M_IRON)
for sx in (-1, 1):
    ff.box(f"FireSide{sx}", (0.02, 0.28, 0.55), (sx * 0.25, -0.14, 0.42), M_IRON)
ff.box("FireHood", (0.5, 0.3, 0.02), (0, -0.14, 0.70), M_IRON)
arch = [(math.cos(math.pi * k / 12) * 0.26, 0.56 + math.sin(math.pi * k / 12) * 0.16) for k in range(13)]
pts = [(0.39, 0.85), (-0.39, 0.85), (-0.39, 0.12)] + [(-0.26, 0.12)] + [(x, z) for x, z in reversed(arch)][::-1][::-1] + [(0.26, 0.12), (0.39, 0.12)]
K.extrude_xz("GrateFace", [(-0.39, 0.12), (-0.26, 0.12), (-0.26, 0.56)] + [(-math.cos(math.pi * k / 12) * 0.26, 0.56 + math.sin(math.pi * k / 12) * 0.16) for k in range(1, 12)] +
             [(0.26, 0.56), (0.26, 0.12), (0.39, 0.12), (0.39, 0.85), (-0.39, 0.85)], 0.025, 0.045, M_IRON, frame=ff)
# the fire basket: bars, coals, embers
ff.box("BasketFront", (0.48, 0.02, 0.012), (0, 0.03, 0.30), M_IRON)
for k in range(4): ff.box(f"BasketBar{k}", (0.48, 0.012, 0.012), (0, 0.03, 0.14 + 0.05 * k), M_IRON)
ff.box("FireBed", (0.46, 0.25, 0.04), (0, -0.12, 0.13), M_EMBERS)
rr_ = random.Random(3)
for k in range(26):
    px, py, pz = rr_.uniform(-0.2, 0.2), rr_.uniform(-0.24, 0.0), 0.16 + rr_.uniform(0, 0.12) * (1 - abs(rr_.gauss(0, 0.5)))
    s = rr_.uniform(0.03, 0.06)
    sphere(f"Coal{k}", s, ff.p(px, py, pz), M_COAL if rr_.random() < 0.7 else M_EMBERS, seg=6, scale=(1, 0.9, 0.7), rot=(rr_.random(), rr_.random(), rr_.random()))
# hearth, fender and fire irons
ff.box("Hearth", (1.5, 0.48, 0.03), (0, 0.24, 0.015), M_SLATE)
ff.box("HearthKerb", (1.56, 0.05, 0.05), (0, 0.49, 0.025), M_SLATE, bevel=0.006)
ff.box("FenderFront", (1.3, 0.012, 0.09), (0, 0.42, 0.05), M_BRASS, bevel=0.003)
for sx in (-1, 1): ff.box(f"FenderSide{sx}", (0.012, 0.36, 0.09), (sx * 0.65, 0.24, 0.05), M_BRASS, bevel=0.003)
for k, x in enumerate((0.58, 0.62)):
    tube(f"FireIron{k}", [ff.p(x, 0.32, 0.06), ff.p(x - 0.02, 0.28, 0.72)], 0.008, M_BRASS, sides=6)
    sphere(f"FireIronKnob{k}", 0.02, ff.p(x - 0.02, 0.28, 0.74), M_BRASS, seg=8)
# on the mantel: a black slate clock, a pair of candlesticks with candles, a pair of vases
ff.box("ClockCase", (0.30, 0.13, 0.26), (0, 0.10, 1.38), M_SLATE, bevel=0.01)
ff.box("ClockTop", (0.34, 0.15, 0.03), (0, 0.10, 1.525), M_SLATE, bevel=0.008)
DIAL_ROT = ff.R @ Matrix.Rotation(-math.pi / 2, 3, 'X')         # the dial's axis along the frame's +y (into the room)
lathe("ClockDial", [(0.0, 0.0), (0.075, 0.0), (0.08, 0.006), (0.0, 0.008)], ff.p(0, 0.166, 1.39), M_DIAL, steps=24, rot=DIAL_ROT)
lathe("ClockBezel", [(0.078, 0.0), (0.09, 0.0), (0.09, 0.012), (0.078, 0.012)], ff.p(0, 0.166, 1.39), M_GILT, steps=24, closed=True, rot=DIAL_ROT)
CANDLES = []
for sx in (-1, 1):
    ff.lathe(f"Candlestick{sx}", [(0.0, 1.25), (0.065, 1.25), (0.065, 1.265), (0.03, 1.29), (0.018, 1.33), (0.025, 1.38), (0.014, 1.42), (0.016, 1.52),
                                  (0.03, 1.535), (0.032, 1.545), (0.0, 1.545)], (sx * 0.52, 0.12, 0), M_BRASS, steps=16)
    ff.cyl(f"Candle{sx}", 0.011, 0.20, (sx * 0.52, 0.12, 1.645), M_WAX, verts=10)
    CANDLES.append(Vector(ff.p(sx * 0.52, 0.12, 1.752)))
    ff.lathe(f"Vase{sx}", [(0.0, 1.25), (0.04, 1.25), (0.06, 1.30), (0.065, 1.36), (0.04, 1.42), (0.028, 1.46), (0.035, 1.49), (0.0, 1.49)],
             (sx * 0.74, 0.10, 0), M_CHINA, steps=16)
# overmantel glass in a gilt frame
ff.box("OvermantelFrame", (1.20, 0.05, 0.95), (0, 0.04, 1.80), M_GILT, bevel=0.02, seg=2)
ff.box("OvermantelGlass", (1.02, 0.01, 0.78), (0, 0.068, 1.80), M_MIRROR)
FIRE_POS = Vector(ff.p(0, -0.12, 0.16))

# ----------------------------------------------------------------------------- the table, cloth, chairs
tf = Frame((TABLE.x, TABLE.y), 0.0)
for sx in (-1, 1):
    for sy in (-1, 1):
        tf.lathe(f"TableLeg{sx}{sy}", [(0.0, 0.0), (0.03, 0.0), (0.035, 0.04), (0.028, 0.08), (0.04, 0.2), (0.048, 0.34), (0.038, 0.5), (0.042, 0.58), (0.035, 0.64), (0.045, 0.66), (0.045, TH - 0.03), (0.0, TH - 0.03)],
                 (sx * (TW / 2 - 0.09), sy * (TL / 2 - 0.12), 0), M_MAHOG, steps=12)
tf.box("TableApron", (TW - 0.12, TL - 0.16, 0.10), (0, 0, TH - 0.08), M_MAHOG)
tf.box("TableTop", (TW, TL, 0.03), (0, 0, TH - 0.015), M_MAHOG, bevel=0.008)
# the cloth: a top and four drops, falling 0.32 m, with a little flare and the corners' folds
CL_X, CL_Y, DROP = TW / 2 + 0.12, TL / 2 + 0.12, 0.34
tf.box("ClothTop", (2 * CL_X - 0.02, 2 * CL_Y - 0.02, 0.006), (0, 0, TH + 0.003), M_CLOTH, bevel=0.003)
def cloth_drop(name, a0, a1, side, along):
    vs, faces = [], []
    n = 22
    for i in range(n + 1):
        s = i / n; a = a0 + (a1 - a0) * s
        for j, t in enumerate((0.0, 0.5, 1.0)):
            out = 0.012 + 0.03 * t * t + 0.012 * math.sin(s * 9.0 + side) * t
            z = TH + 0.004 - DROP * t * (1 - 0.06 * math.sin(s * math.pi))
            if along == 'x': vs.append((TABLE.x + a, TABLE.y + side * (CL_Y + out - 0.01), z))
            else: vs.append((TABLE.x + side * (CL_X + out - 0.01), TABLE.y + a, z))
    for i in range(n):
        for j in range(2):
            k = i * 3 + j; faces.append((k, k + 3, k + 4, k + 1))
    o = mesh_from(name, vs, faces, M_CLOTH, smooth=True)
    orient(o, lambda c, side=side, along=along: Vector((0, side, 0)) if along == 'x' else Vector((side, 0, 0)))
for side in (-1, 1):
    cloth_drop(f"ClothDropEnd{side}", -CL_X, CL_X, side, 'x')
    cloth_drop(f"ClothDropSide{side}", -CL_Y, CL_Y, side, 'y')

def chair(name, pos, yaw, pulled=0.0):
    c = Frame(pos, yaw)
    for sx in (-1, 1):
        c.box(f"{name}LegF{sx}", (0.035, 0.035, 0.45), (sx * 0.2, 0.19, 0.225), M_MAHOG)
        tube(f"{name}LegB{sx}", [c.p(sx * 0.19, -0.19, 0.0), c.p(sx * 0.19, -0.2, 0.45), c.p(sx * 0.18, -0.26, 0.95)], 0.017, M_MAHOG, sides=6)
    c.box(f"{name}Seat", (0.46, 0.44, 0.05), (0, 0.0, 0.47), M_MAHOG, bevel=0.01)
    c.box(f"{name}Pad", (0.42, 0.40, 0.04), (0, 0.0, 0.51), M_LEATHER, bevel=0.015, seg=2)
    # balloon back: an oval hoop and a waisted rail
    hoop = [c.p(0.18 * math.sin(TWO_PI * k / 20), -0.24 - 0.02 * (math.cos(TWO_PI * k / 20)), 0.80 + 0.15 * math.cos(TWO_PI * k / 20)) for k in range(21)]
    tube(f"{name}Hoop", hoop, 0.016, M_MAHOG, sides=6, cap=False)
    tube(f"{name}Rail", [c.p(-0.16, -0.23, 0.70), c.p(0, -0.21, 0.68), c.p(0.16, -0.23, 0.70)], 0.014, M_MAHOG, sides=6)
for k, (pos, yaw) in enumerate([((TABLE.x - TW / 2 - 0.12, TABLE.y - 0.45), -math.pi / 2), ((TABLE.x - TW / 2 - 0.12, TABLE.y + 0.45), -math.pi / 2),
                                ((TABLE.x + TW / 2 + 0.12, TABLE.y - 0.45), math.pi / 2), ((TABLE.x + TW / 2 + 0.12, TABLE.y + 0.45), math.pi / 2),
                                ((TABLE.x, TABLE.y + TL / 2 + 0.22), math.pi), ((TABLE.x - 0.55, TABLE.y - TL / 2 - 0.42), 0.35)]):
    chair(f"Chair{k}", pos, yaw)

# ----------------------------------------------------------------------------- the table laid: two places, a cold dinner, the lamp
TOPZ = TH + 0.007
def plate(name, x, y, r=0.125, deep=0.018):
    lathe(name, [(0.0, TOPZ), (r * 0.55, TOPZ), (r * 0.62, TOPZ + 0.004), (r * 0.62, TOPZ + 0.006), (r * 0.98, TOPZ + deep), (r, TOPZ + deep + 0.002),
                 (r * 0.97, TOPZ + deep + 0.004), (r * 0.6, TOPZ + 0.009), (0.0, TOPZ + 0.009)], (x, y, 0), M_CHINA, steps=28)
def place(tag, x, y, facing):
    """A place setting: a dinner plate on the cloth, knife and fork, a dessert spoon, a wine glass, a tumbler, a napkin."""
    plate(f"Plate{tag}", x, y)
    for s, kind in ((-1, "fork"), (1, "knife")):
        px = x + s * 0.17 * facing
        box(f"{kind}{tag}", (0.018 if kind == "knife" else 0.022, 0.21, 0.004), (px, y, TOPZ + 0.003), M_SILVER, bevel=0.0015)
    box(f"Spoon{tag}", (0.17, 0.016, 0.004), (x, y + 0.17 * facing, TOPZ + 0.003), M_SILVER, bevel=0.0015)
    gx, gy = x + 0.16 * facing, y + 0.15 * facing
    lathe(f"WineGlass{tag}", [(0.0, TOPZ), (0.035, TOPZ), (0.036, TOPZ + 0.004), (0.005, TOPZ + 0.01), (0.004, TOPZ + 0.085), (0.02, TOPZ + 0.095),
                              (0.034, TOPZ + 0.125), (0.033, TOPZ + 0.165), (0.031, TOPZ + 0.165), (0.032, TOPZ + 0.127), (0.0, TOPZ + 0.099)], (gx, gy, 0), M_GLASS, steps=18)
    lathe(f"Tumbler{tag}", [(0.0, TOPZ), (0.03, TOPZ), (0.035, TOPZ + 0.10), (0.032, TOPZ + 0.10), (0.027, TOPZ + 0.008), (0.0, TOPZ + 0.008)], (gx - 0.08 * facing, gy + 0.02, 0), M_GLASS, steps=16)
    box(f"Napkin{tag}", (0.15, 0.2, 0.025), (x - 0.27 * facing, y, TOPZ + 0.012), M_CLOTH, bevel=0.008, rot=(0, 0, 0.1 * facing))
    return Vector((gx, gy, TOPZ))
# the narrator's place at the south end (nearest the reader), his wife's at the north end
G1 = place("Him", TABLE.x, TABLE.y - TL / 2 + 0.22, 1)
G2 = place("Her", TABLE.x, TABLE.y + TL / 2 - 0.22, -1)
# the crimson-purple wine in his glass
lathe("WineInGlass", [(0.0, TOPZ + 0.1), (0.022, TOPZ + 0.104), (0.031, TOPZ + 0.125), (0.031, TOPZ + 0.135), (0.0, TOPZ + 0.135)], (G1.x, G1.y, 0), M_WINE, steps=16)
# the claret decanter and its stopper, half full
DEC = (TABLE.x + 0.26, TABLE.y - 0.42)
lathe("Decanter", [(0.0, TOPZ), (0.055, TOPZ), (0.07, TOPZ + 0.04), (0.072, TOPZ + 0.10), (0.05, TOPZ + 0.16), (0.022, TOPZ + 0.20), (0.02, TOPZ + 0.25),
                   (0.028, TOPZ + 0.26), (0.0, TOPZ + 0.26)], (DEC[0], DEC[1], 0), M_GLASS, steps=20)
lathe("DecanterWine", [(0.0, TOPZ + 0.006), (0.052, TOPZ + 0.006), (0.066, TOPZ + 0.04), (0.067, TOPZ + 0.09), (0.0, TOPZ + 0.09)], (DEC[0], DEC[1], 0), M_WINE, steps=18)
lathe("Stopper", [(0.0, TOPZ + 0.255), (0.012, TOPZ + 0.255), (0.03, TOPZ + 0.28), (0.02, TOPZ + 0.30), (0.0, TOPZ + 0.31)], (DEC[0], DEC[1], 0), M_GLASS, steps=12)
# the cold dinner: a joint of cold beef on its dish with a carving knife and fork, bread on a board, a salad, a pie
plate("BeefDish", TABLE.x - 0.18, TABLE.y + 0.18, r=0.2, deep=0.025)
sphere("ColdBeef", 0.085, (TABLE.x - 0.18, TABLE.y + 0.18, TOPZ + 0.06), M_FOOD, seg=14, scale=(1.3, 0.9, 0.65))
box("CarvingKnife", (0.02, 0.3, 0.005), (TABLE.x - 0.02, TABLE.y + 0.12, TOPZ + 0.03), M_SILVER, rot=(0, 0, 0.25), bevel=0.002)
box("BreadBoard", (0.26, 0.2, 0.02), (TABLE.x + 0.24, TABLE.y + 0.32, TOPZ + 0.01), M_MAHOG, bevel=0.006)
sphere("Loaf", 0.07, (TABLE.x + 0.24, TABLE.y + 0.32, TOPZ + 0.06), M_CRUST, seg=12, scale=(1.4, 1.0, 0.75))
lathe("SaladBowl", [(0.0, TOPZ), (0.05, TOPZ), (0.09, TOPZ + 0.04), (0.10, TOPZ + 0.08), (0.095, TOPZ + 0.08), (0.085, TOPZ + 0.045), (0.0, TOPZ + 0.01)], (TABLE.x + 0.28, TABLE.y - 0.05, 0), M_GLASS, steps=20)
for k in range(9):
    a = TWO_PI * k / 9
    sphere(f"Leaf{k}", 0.03, (TABLE.x + 0.28 + math.cos(a) * 0.04, TABLE.y - 0.05 + math.sin(a) * 0.04, TOPZ + 0.07), M_GREENS, seg=6, scale=(1.2, 0.8, 0.5))
lathe("PieDish", [(0.0, TOPZ), (0.09, TOPZ), (0.11, TOPZ + 0.04), (0.0, TOPZ + 0.04)], (TABLE.x - 0.28, TABLE.y - 0.25, 0), M_CHINA, steps=20)
lathe("PieCrust", [(0.0, TOPZ + 0.07), (0.07, TOPZ + 0.065), (0.11, TOPZ + 0.042), (0.0, TOPZ + 0.042)], (TABLE.x - 0.28, TABLE.y - 0.25, 0), M_CRUST, steps=20)
# the dish of nuts by his place, and the nutcrackers
NUTS = (TABLE.x - 0.2, TABLE.y - TL / 2 + 0.45)
lathe("NutDish", [(0.0, TOPZ), (0.03, TOPZ), (0.03, TOPZ + 0.03), (0.07, TOPZ + 0.05), (0.075, TOPZ + 0.058), (0.0, TOPZ + 0.036)], (NUTS[0], NUTS[1], 0), M_SILVER, steps=20)
rn = random.Random(9)
for k in range(14):
    a, r = rn.uniform(0, TWO_PI), rn.uniform(0, 0.05)
    sphere(f"Nut{k}", rn.uniform(0.011, 0.016), (NUTS[0] + math.cos(a) * r, NUTS[1] + math.sin(a) * r, TOPZ + 0.05 + rn.uniform(0, 0.015)), M_NUTS, seg=6, scale=(1.2, 1, 0.9))
tube("Nutcracker", [(NUTS[0] + 0.1, NUTS[1] - 0.03, TOPZ + 0.006), (NUTS[0] + 0.22, NUTS[1] + 0.0, TOPZ + 0.006)], 0.005, M_SILVER, sides=5)
# the cruet stand
CRU = (TABLE.x - 0.25, TABLE.y + 0.55)
lathe("CruetStand", [(0.0, TOPZ), (0.07, TOPZ), (0.07, TOPZ + 0.01), (0.0, TOPZ + 0.01)], (CRU[0], CRU[1], 0), M_SILVER, steps=20)
cyl("CruetHandle", 0.006, 0.2, (CRU[0], CRU[1], TOPZ + 0.11), M_SILVER, verts=6)
for k in range(4):
    a = TWO_PI * k / 4
    lathe(f"CruetBottle{k}", [(0.0, TOPZ + 0.01), (0.02, TOPZ + 0.01), (0.022, TOPZ + 0.08), (0.008, TOPZ + 0.11), (0.012, TOPZ + 0.125), (0.0, TOPZ + 0.13)],
          (CRU[0] + math.cos(a) * 0.04, CRU[1] + math.sin(a) * 0.04, 0), M_GLASS, steps=10)
# the oil lamp under its pink shade
LAMP = Vector((TABLE.x + 0.02, TABLE.y + 0.0, TOPZ))
lathe("LampBase", [(0.0, 0.0), (0.085, 0.0), (0.085, 0.015), (0.06, 0.03), (0.03, 0.06), (0.022, 0.12), (0.03, 0.22), (0.022, 0.30), (0.035, 0.33), (0.0, 0.33)],
      tuple(LAMP), M_BRASS, steps=20)
lathe("LampFont", [(0.0, 0.33), (0.06, 0.34), (0.085, 0.38), (0.08, 0.42), (0.04, 0.45), (0.0, 0.455)], tuple(LAMP), M_FONT, steps=20)
lathe("LampBurner", [(0.0, 0.45), (0.035, 0.45), (0.04, 0.48), (0.034, 0.50), (0.0, 0.50)], tuple(LAMP), M_BRASS, steps=16)
lathe("LampChimney", [(0.028, 0.50), (0.034, 0.53), (0.036, 0.57), (0.022, 0.62), (0.02, 0.74), (0.018, 0.74), (0.02, 0.62), (0.033, 0.57), (0.031, 0.53), (0.025, 0.50)],
      tuple(LAMP), M_LAMPGLASS, steps=16)
lathe("LampShadeRing", [(0.04, 0.56), (0.05, 0.56), (0.05, 0.565), (0.04, 0.565)], tuple(LAMP), M_BRASS, steps=16, closed=True)
shade = []
for k in range(11):
    t = k / 10; z = 0.535 + 0.17 * t
    r = 0.19 - 0.13 * t + 0.015 * math.sin(t * math.pi)
    shade.append((r, z))
sh = lathe("LampShade", [(r, z) for r, z in shade] + [(r * 0.97, z) for r, z in reversed(shade)], tuple(LAMP), M_SHADE, steps=36)
# a frilled hem on the shade
bm = bmesh.new(); bm.from_mesh(sh.data)
for v in bm.verts:
    if v.co.z < 0.54:
        a = math.atan2(v.co.y, v.co.x); v.co.z += 0.012 * math.sin(a * 18)
bm.to_mesh(sh.data); bm.free()
FLAME = LAMP + Vector((0, 0, 0.53))

# ----------------------------------------------------------------------------- the sideboard (north wall, ahead) and the pictures
sf = Frame((0.0, Y1 - 0.3), math.pi)
sf.box("SideboardTop", (1.9, 0.58, 0.04), (0, 0, 0.92), M_MAHOG, bevel=0.01)
for sx in (-1, 1):
    sf.box(f"SidePed{sx}", (0.5, 0.52, 0.86), (sx * 0.67, 0, 0.45), M_MAHOG, bevel=0.006)
    sf.box(f"SideDoor{sx}", (0.42, 0.015, 0.6), (sx * 0.67, -0.265, 0.45), M_MAHOG, bevel=0.008)
    sf.cyl(f"SideKnob{sx}", 0.013, 0.03, (sx * 0.67 - sx * 0.15, -0.28, 0.5), M_BRASS, verts=8, rot=(math.pi / 2, 0, 0))
sf.box("SideDrawers", (0.84, 0.5, 0.16), (0, 0, 0.8), M_MAHOG, bevel=0.006)
for sx in (-1, 1): sf.box(f"SideDrawerFront{sx}", (0.38, 0.015, 0.12), (sx * 0.2, -0.255, 0.8), M_MAHOG, bevel=0.004)
sf.box("SidePlinth", (1.86, 0.54, 0.06), (0, 0, 0.03), M_MAHOG)
sf.box("SideBack", (1.8, 0.04, 0.9), (0, 0.27, 1.42), M_MAHOG, bevel=0.01)
sf.box("SideMirror", (1.2, 0.01, 0.62), (0, 0.245, 1.40), M_MIRROR)
sf.box("SideCrest", (1.9, 0.08, 0.1), (0, 0.25, 1.92), M_MAHOG, bevel=0.015)
for sx in (-1, 1): sf.box(f"SideShelf{sx}", (0.26, 0.16, 0.025), (sx * 0.72, 0.18, 1.52), M_MAHOG, bevel=0.005)
# on it: a tantalus of decanters, a silver tray with a teapot, a fruit comport
sf.box("Tray", (0.5, 0.34, 0.012), (-0.48, -0.02, 0.946), M_SILVER, bevel=0.004)
sf.lathe("Teapot", [(0.0, 0.95), (0.06, 0.95), (0.09, 0.99), (0.095, 1.04), (0.07, 1.09), (0.03, 1.1), (0.035, 1.12), (0.0, 1.13)], (-0.48, -0.02, 0), M_SILVER, steps=18)
for k, dx in enumerate((0.38, 0.52, 0.66)):
    sf.lathe(f"SideDecanter{k}", [(0.0, 0.94), (0.045, 0.94), (0.05, 1.02), (0.035, 1.08), (0.016, 1.12), (0.016, 1.17), (0.025, 1.19), (0.0, 1.2)], (dx, 0.0, 0), M_GLASS, steps=14)
sf.lathe("Comport", [(0.0, 0.94), (0.06, 0.94), (0.015, 0.96), (0.012, 1.05), (0.12, 1.08), (0.13, 1.1), (0.0, 1.08)], (0.0, 0.0, 0), M_CHINA, steps=22)
for k in range(7):
    a = TWO_PI * k / 7
    sphere(f"Fruit{k}", 0.035, sf.p(math.cos(a) * 0.06, math.sin(a) * 0.06, 1.12 + (0.03 if k % 2 else 0)), M_CRUST if k % 3 else M_GREENS, seg=8)
# three oil paintings in gilt frames
def picture(i, frame, cx, z, w, h):
    frame.box(f"PicFrame{i}", (w + 0.12, 0.04, h + 0.12), (cx, 0.02, z), M_GILT, bevel=0.025, seg=2)
    vs = [frame.p(cx - w / 2, 0.042, z - h / 2), frame.p(cx + w / 2, 0.042, z - h / 2), frame.p(cx + w / 2, 0.042, z + h / 2), frame.p(cx - w / 2, 0.042, z + h / 2)]
    mesh_from(f"Canvas{i}", vs, [(0, 1, 2, 3)], PAINTINGS[i], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    K.KEEP_UV.add(PAINTINGS[i].name)
    # the cord to the picture rail
    tube(f"PicCord{i}", [frame.p(cx - w / 3, 0.01, z + h / 2 + 0.06), frame.p(cx, 0.005, PICT), frame.p(cx + w / 3, 0.01, z + h / 2 + 0.06)], 0.003, M_BRASS, sides=4, cap=False)
picture(0, Frame((0.0, Y1), math.pi), -1.45, 1.75, 0.5, 0.38)
picture(1, Frame((0.0, Y1), math.pi), 1.45, 1.75, 0.5, 0.38)
picture(2, Frame((X0, -1.5), -math.pi / 2), 0.0, 1.70, 0.62, 0.46)
picture(3 - 3, Frame((0.75, Y0), 0.0), 0.0, 1.72, 0.36, 0.46) if False else None

# ----------------------------------------------------------------------------- lights (names starting "Lamp" are baked in Unity)
def light(name, kind, energy, color, loc, size=0.05, aim=None, spot=None):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color; ld.shadow_soft_size = size
    if spot: ld.spot_size, ld.spot_blend = spot
    lo = bpy.data.objects.new(name, ld); lo.location = tuple(loc)
    if aim is not None: lo.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    lo.visible_camera = False; lo.visible_glossy = False; lo.visible_transmission = False
    return K.link(lo)
light("Lamp.table", 'POINT', 110.0, (1.0, 0.62, 0.52), FLAME, size=0.04)
light("Lamp.fire", 'POINT', 22.0, (1.0, 0.42, 0.12), FIRE_POS + Vector(ff.p(0, 0.25, 0.15)) - Vector(ff.p(0, 0, 0)), size=0.15)
light("Lamp.candles", 'POINT', 6.0, (1.0, 0.66, 0.36), (CANDLES[0] + CANDLES[1]) / 2 + Vector((0, 0, 0.03)), size=0.3)
win_out = Vector(wf.p(0, -1.2, WIN_SILL + WIN_H * 0.7))
light("Lamp.dusk", 'SPOT', 140.0, (0.50, 0.60, 1.0), win_out, size=1.2, aim=Vector(wf.p(0, 3.0, 0.4)), spot=(math.radians(110), 1.0))

world = bpy.data.worlds.new("Dusk"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.02, 0.025, 0.045, 1); bg.inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors and living-scene markers
anchor("reader.entrance", (READER.x, READER.y, 0.0))
anchor("reader.look", tuple(Vector((READER.x, READER.y, EYE)) + LOOK * 2.0))
anchor("scene.centre", (TABLE.x, TABLE.y, 0.0))
anchor("room.lamp", tuple(FLAME))
anchor("room.fire", tuple(FIRE_POS))
anchor("room.window", wf.p(0, 0, WIN_SILL + WIN_H / 2))
anchor("room.wine", tuple(G1 + Vector((0, 0, 0.12))))
marker("fx.lantern.0", tuple(FLAME), size=0.02)
for i, cpos in enumerate(CANDLES): marker(f"fx.candle.{i}", tuple(cpos), size=0.01)
marker("fx.fire.0", tuple(FIRE_POS), size=0.2)
marker("sound.clock.0", ff.p(0, 0.10, 1.38), size=0.1)

K.apply_all_transforms()

# ----------------------------------------------------------------------------- cameras
E = Vector((READER.x, READER.y, EYE))
def ahead(yaw_deg, pitch_deg=0.0, d=3.0):
    a = math.atan2(LOOK.x, LOOK.y) - math.radians(yaw_deg); p = math.radians(pitch_deg)
    return tuple(E + Vector((math.sin(a) * math.cos(p), math.cos(a) * math.cos(p), math.sin(p))) * d)
cams = [
    camera("Cam_Reader", tuple(E), ahead(0, -8)),
    camera("Cam_Left", tuple(E), ahead(65, -8)),
    camera("Cam_Right", tuple(E), ahead(-65, -10)),
    camera("Cam_Behind", tuple(E), ahead(180, -6)),
    camera("Cam_Down", tuple(E), ahead(0, -55), lens=16),
    camera("Cam_Table", tuple(Vector((TABLE.x - 0.5, TABLE.y - 1.0, 1.25))), tuple(Vector((TABLE.x, TABLE.y - 0.3, TOPZ + 0.1))), lens=24),
    camera("Cam_Fire", tuple(Vector((0.4, FIRE_Y - 0.6, 1.1))), tuple(Vector((X1 - BREAST_D, FIRE_Y, 0.6))), lens=24),
]
EXPOSURE = {}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "maybury_dining_room_source.blend"))
K.budget_report()

if args.render:
    K.render_stills(scene, cams, EXPOSURE, default_exp=0.8)

if args.bake or args.export:
    T_ = args.tex
    size_for = {"M_Wallpaper": (T_, T_ // 4, T_ // 2), "M_Lincrusta": (T_, T_ // 4, T_), "M_Carpet": (T_, T_ // 8, T_ // 2), "M_Floorboards": (T_ // 2, T_ // 4, T_ // 2),
                "M_Damask": (T_, T_ // 4, T_ // 2), "M_Mahogany": (T_, T_ // 4, T_ // 2), "M_Frieze": (T_ // 4,), "M_Ceiling": (T_ // 4,), "M_Mouldings": (T_ // 4, T_ // 8),
                "M_GrainedDoor": (T_ // 2, T_ // 8, T_ // 4), "M_Tiles": (T_ // 2, T_ // 4, T_ // 4), "M_BlackSlate": (T_ // 4, T_ // 8), "M_Brass": (T_ // 4, T_ // 8),
                "M_Silver": (T_ // 4, T_ // 8), "M_Gilt": (T_ // 4, T_ // 8, T_ // 4), "M_China": (T_ // 4,), "M_Velvet": (T_ // 2, T_ // 8, T_ // 4),
                "M_Leather": (T_ // 4, T_ // 8), "M_CastIron": (T_ // 4, T_ // 8), "M_Mirror": (64,), "M_Glass": (64,), "M_LampGlass": (64,), "M_Liquid": (64,),
                "M_LampFontGlass": (64,), "M_LampShade": (T_ // 8,), "M_Embers": (T_ // 16,), "M_Coal": (T_ // 16,)}
    K.bake_and_export(scene, "maybury_dining_room.gltf", size_for, keep_names={"M_GardenDusk": "far.garden", "M_Velvet": "cloth.curtain.0"},
                      cams=cams, blend_name="maybury_dining_room_baked.blend")
print("DONE")
