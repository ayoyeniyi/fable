"""
Fable scene room: the drawing-room at Lucas Lodge, an evening party (Pride and Prejudice, chapter 6) - lucas-lodge-drawing-room.

"Sir William Lucas ... a large party were assembled" "Mary ... was eager to display" "'I am going to open the
instrument, Eliza'" "Mary ... at the request of her younger sisters, who with some of the Lucases, and two or three
officers, joined eagerly in dancing at one end of the room." "Mr. Darcy stood near them in silent indignation at such
a mode of passing the evening" "'Your friend performs delightfully,' he continued after a pause, on seeing Bingley
join the group; 'and I doubt not that you are an adept in the science yourself, Mr. Darcy.' ... 'You have a house
in town, I conclude?' ... 'I had once some thoughts of fixing in town myself'" "'My dear Miss Eliza, why are you not
dancing? Mr. Darcy, you must allow me to present this young lady to you'"

A good-sized drawing-room of about 1811 in the house of a newly knighted former tradesman, a mile from Meryton, in
the middle of the evening party as if everyone has just stepped out: walls hung with a showy striped paper with small
gilt sprigs over a painted dado, a painted wooden chimney-piece with a coal fire, an overmantel glass, a pair of
plated candlesticks and chimney ornaments; a square pianoforte opened at the south wall with music books, two
candles on it and a bench before it; chairs drawn up in conversation groups by the fire and along the walls; two
card tables folded and pushed against the wall between the windows, their baize showing; at the east end the
Turkey carpet has been rolled back to the wall for the dancing, leaving the waxed boards bare; candles in gilt
two-light sconces; curtains of a bright crimson moreen drawn across the three windows; over the sofa a framed
engraving of St James's Palace (Sir William's pride: the address to the King, the knighthood). No people.

Light: evening. The fire, candles on the pianoforte, the mantel and four sconces; nothing else.

Axes: metres, +Z up. Room x -4.5..4.5 (9 m), y -3.0..3.0 (6 m); the fire on the west wall, the windows north, the
pianoforte on the south wall; the dancing end east. The reader stands by the pianoforte facing north-north-east.

Run headless:
  blender -b -P blender/build_lucas_lodge_drawing_room.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_lucas_lodge_drawing_room.py -- --cpu --render --samples 48 --res 1280 --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b4 as S
from scene_kit_b4 import K
import pride_interior as I
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       texcoord_obj, wood, noisy, plain, vcol_mat, box, cyl, sphere, lathe, tube, sweep, mesh_from, MB, Frame,
                       anchor, sound, light_obj, camera, link)

ARGS = S.setup("lucas-lodge-drawing-room", 1811, "LucasLodgeDrawingRoom", default_samples=48)
scene = K.scene
rng = random.Random(1811)
scene.cycles.max_bounces = 10; scene.cycles.diffuse_bounces = 6
EYE = S.EYE
R = I.Room(-4.5, 4.5, -3.0, 3.0, 3.6, t=0.35)
READER = Vector((0.55, -1.75, 0.0)); YAW = 18.0
srgb = K.srgb

# ----------------------------------------------------------------------------- materials
def paper_mat(name):
    """A showy striped paper of about 1810: straw ground, broad and narrow stripes in a warm rose-buff, and small
    gilt sprigs scattered in the broad bands; slightly sheened, faded near the windows."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0)); s = sep_xyz(nt, co, (-2200, 0))
    u = math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-2000, 0))
    st = math_(nt, 'FRACT', math_(nt, 'DIVIDE', u, 0.36, (-1850, 0)), None, (-1700, 0))
    broad = math_(nt, 'MULTIPLY', maprange(nt, st, 0.04, 0.06, 0, 1, (-1550, 100)), maprange(nt, st, 0.40, 0.42, 1, 0, (-1550, -50)), (-1400, 50))
    narrow = math_(nt, 'MULTIPLY', maprange(nt, st, 0.58, 0.595, 0, 1, (-1550, -200)), maprange(nt, st, 0.63, 0.645, 1, 0, (-1550, -350)), (-1400, -250))
    ground = c4(srgb((0.86, 0.78, 0.56))); band = c4(srgb((0.80, 0.58, 0.42)))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MAXIMUM', broad, narrow, (-1250, 0)), ground, band, (-1000, 100))
    # sprigs: small dots on a grid offset in the broad bands
    cv = node(nt, "ShaderNodeCombineXYZ", (-1900, -600)); nt.links.new(u, cv.inputs["X"]); nt.links.new(s.outputs["Z"], cv.inputs["Y"])
    vor = voronoi_(nt, cv.outputs[0], 9.0, 'F1', (-1700, -600), rand=0.4)
    sprig = math_(nt, 'MULTIPLY', maprange(nt, vor.outputs["Distance"], 0.12, 0.06, 0, 1, (-1500, -600)), broad, (-1300, -600))
    col = mix_rgb(nt, 'MIX', sprig, col, c4(srgb((0.70, 0.55, 0.26))), (-800, 100))
    n = noise_(nt, co, 1.2, 4, 0.55, loc=(-1500, 400))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 0.12, (-1100, 400)), col, (0.7, 0.66, 0.6, 1), (-600, 100))
    col = K.ao_mul(nt, col, 0.35, 0.3, (-400, -500))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, sprig, 0, 1, 0.62, 0.3, (-400, -300)), b.inputs["Roughness"])
    nt.links.new(sprig, b.inputs["Metallic"])
    return m


def engraving_mat(name):
    """A framed engraving (St James's Palace): a pale sheet with a darker hatched view, the gatehouse's two towers
    against a hatched sky, a title line below."""
    m, nt, b = new_mat(name)
    co = node(nt, "ShaderNodeTexCoord", (-1800, 0)); g = co.outputs["Generated"]; s = sep_xyz(nt, g, (-1600, 0))
    v = s.outputs["Z"]; uu = math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-1450, -100))
    hatch = node(nt, "ShaderNodeTexWave", (-1300, 300)); hatch.inputs["Scale"].default_value = 160.0; hatch.wave_type = 'BANDS'; hatch.bands_direction = 'Z'
    nt.links.new(g, hatch.inputs["Vector"])
    # the building's silhouette: a long range with two crenellated towers in the middle
    towers = math_(nt, 'MULTIPLY', maprange(nt, uu, 0.40, 0.41, 0, 1, (-1200, -300)), maprange(nt, uu, 0.60, 0.61, 1, 0, (-1200, -450)), (-1050, -350))
    gap = math_(nt, 'MULTIPLY', maprange(nt, uu, 0.46, 0.47, 0, 1, (-1200, -600)), maprange(nt, uu, 0.54, 0.55, 1, 0, (-1200, -750)), (-1050, -650))
    top = math_(nt, 'ADD', 0.52, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', towers, gap, (-950, -500)), 0.2, (-850, -500)), (-750, -500))
    bld = maprange(nt, math_(nt, 'SUBTRACT', top, v, (-650, -500)), 0.0, 0.004, 0, 1, (-550, -500))
    bld = math_(nt, 'MULTIPLY', bld, maprange(nt, v, 0.16, 0.17, 0, 1, (-650, -700)), (-450, -550))
    ink = math_(nt, 'MULTIPLY', maprange(nt, hatch.outputs["Fac"], 0.4, 0.7, 0, 1, (-1000, 300)), math_(nt, 'ADD', math_(nt, 'MULTIPLY', bld, 0.75), maprange(nt, v, 0.6, 1.0, 0.0, 0.3, (-1000, 100)), (-800, 200)), (-600, 200))
    title = math_(nt, 'MULTIPLY', maprange(nt, v, 0.07, 0.075, 0, 1, (-900, -900)), maprange(nt, v, 0.10, 0.105, 1, 0, (-900, -1050)), (-750, -950))
    title = math_(nt, 'MULTIPLY', title, maprange(nt, uu, 0.25, 0.26, 0, 1, (-900, -1200)), (-600, -1000))
    title = math_(nt, 'MULTIPLY', title, maprange(nt, uu, 0.74, 0.75, 1, 0, (-900, -1350)), (-500, -1050))
    ink = math_(nt, 'MAXIMUM', ink, math_(nt, 'MULTIPLY', title, 0.5), (-400, 0))
    col = mix_rgb(nt, 'MIX', ink, c4(srgb((0.86, 0.82, 0.70))), c4(srgb((0.22, 0.19, 0.16))), (-200, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    return m


M_PAPER = paper_mat("M_WallPaper")
M_DADO = I.paint_mat("M_DadoPaint", srgb((0.62, 0.66, 0.58)), rough=0.6, dirt=0.1)
M_JOIN = I.joinery_mat("M_Joinery", srgb((0.88, 0.86, 0.80)))
M_CEIL = I.paint_mat("M_Ceiling", srgb((0.86, 0.85, 0.80)), rough=0.9, dirt=0.0)
M_FLOOR = I.boards_mat("M_FloorBoards")
M_CARPET = I.carpet_mat("M_Carpet", -1.05, 0.0, 3.05, 2.7, field=(0.24, 0.04, 0.03), ground2=(0.10, 0.08, 0.04), border=(0.04, 0.05, 0.08))
M_MAHOG = I.mahogany("M_Mahogany")
M_SATIN = wood("M_Satinwood", base=srgb((0.78, 0.60, 0.34)), dark=srgb((0.58, 0.42, 0.22)), light=srgb((0.88, 0.72, 0.46)), scale=1.5, rough=(0.25, 0.45), coat=0.4, ao=0.2)
M_GILT = I.gilt("M_Gilt")
M_SILVER = plain("M_Silver", (0.80, 0.80, 0.78), rough=0.18, metallic=1.0)
M_BRASS = plain("M_Brass", (0.72, 0.55, 0.30), rough=0.3, metallic=1.0)
M_IRON = noisy("M_Iron", [(0.025, 0.025, 0.027), (0.05, 0.05, 0.05), (0.035, 0.032, 0.03)], scale=30, rough=(0.45, 0.7), metallic=0.6)
M_SOOT = plain("M_Soot", (0.012, 0.011, 0.01), rough=0.95)
M_WAX = plain("M_Wax", srgb((0.93, 0.91, 0.85)), rough=0.45)
M_CHAIRSILK = I.silk("M_ChairSilk", srgb((0.50, 0.20, 0.16)), srgb((0.60, 0.28, 0.22)), damask=0.6, sheen=0.6)
M_SOFASILK = I.silk("M_SofaSilk", srgb((0.70, 0.58, 0.30)), srgb((0.82, 0.72, 0.44)), stripes=1.0, stripe_w=0.05, axis='X', sheen=0.7)
M_CURTAIN = I.silk("M_Curtains", srgb((0.52, 0.08, 0.08)), srgb((0.62, 0.13, 0.12)), damask=0.3, sheen=0.4, rough=0.75)
M_NIGHT = plain("M_WindowGlassNight", (0.008, 0.01, 0.016), rough=0.05)
M_MIRROR = plain("M_Mirror", (0.75, 0.75, 0.73), rough=0.04, metallic=1.0)
M_BAIZE = noisy("M_Baize", [srgb((0.12, 0.30, 0.16)), srgb((0.16, 0.36, 0.20))], scale=60, rough=0.95, bump=0.2)
M_IVORY = plain("M_Ivory", srgb((0.88, 0.84, 0.74)), rough=0.3)
M_EBONY = plain("M_Ebony", srgb((0.03, 0.025, 0.02)), rough=0.3)
M_MUSIC = noisy("M_MusicPaper", [srgb((0.84, 0.80, 0.68)), srgb((0.78, 0.73, 0.60))], scale=30, rough=0.85, bump=0.0)
M_BOARDCOVER = noisy("M_MusicCovers", [srgb((0.28, 0.20, 0.14)), srgb((0.36, 0.26, 0.18))], scale=18, rough=0.6, bump=0.1)
M_PORCELAIN = plain("M_Porcelain", srgb((0.90, 0.90, 0.88)), rough=0.15, coat=0.6)
M_ENGRAVING = engraving_mat("M_Engraving")
M_LAND = I.landscape_mat("M_Landscape", 3)
M_PAINTWOOD = I.joinery_mat("M_ChimneyPaint", srgb((0.90, 0.88, 0.82)), rough=0.45)

def embers_mat(name="M_Embers"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 28.0, 'DISTANCE_TO_EDGE', (-900, 0))
    glow = maprange(nt, v.outputs["Distance"], 0.0, 0.08, 1, 0, (-700, 0))
    n = noise_(nt, co, 9.0, 4, 0.6, loc=(-900, -250))
    glow = math_(nt, 'MULTIPLY', glow, maprange(nt, n.outputs["Fac"], 0.35, 0.65, 0.2, 1.0, (-700, -250)), (-500, -100))
    col = mix_rgb(nt, 'MIX', glow, (0.02, 0.018, 0.016, 1), (0.9, 0.28, 0.05, 1), (-300, 0))
    nt.links.new(col, b.inputs["Base Color"])
    ec = mix_rgb(nt, 'MULTIPLY', 1.0, (1.0, 0.33, 0.06, 1), glow, (-300, -300))
    nt.links.new(ec, b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 3.0
    b.inputs["Roughness"].default_value = 0.9
    return m
M_EMBERS = embers_mat()

# ----------------------------------------------------------------------------- windows (north), door (south-east), walls
for k, x in enumerate((-1.6, 0.9, 3.4)):
    I.sash_window(f"Win{k}", R, 'N', R.x1 - x, 1.1, 0.62, 2.4, M_JOIN, M_NIGHT, M_JOIN, panes=(3, 6), curtain_mat=M_CURTAIN, pelmet_mat=M_GILT, drawn=1.0)
DOOR_U = 7.6      # along the south wall from x0
M_DOOR = I.mahogany("M_DoorMahogany", rough=(0.3, 0.55), coat=0.2)
I.six_panel_door("Door", R, 'S', DOOR_U, 1.0, 2.4, M_DOOR, M_JOIN, M_BRASS, open_deg=18, hinge_left=True)
I.build_walls(R, M_PAPER)
dp = R.at('S', DOOR_U)
box("PassageFloor", (1.4, 2.2, 0.02), (dp.x, R.y0 - R.t - 1.1, -0.01), M_FLOOR)
box("PassageWallS", (1.6, 0.1, 3.0), (dp.x, R.y0 - R.t - 2.2, 1.5), M_DADO)
box("PassageWallE", (0.1, 2.2, 3.0), (dp.x + 0.75, R.y0 - R.t - 1.1, 1.5), M_DADO)
box("PassageWallW", (0.1, 2.2, 3.0), (dp.x - 0.75, R.y0 - R.t - 1.1, 1.5), M_DADO)
box("PassageCeil", (1.6, 2.4, 0.05), (dp.x, R.y0 - R.t - 1.1, 3.0), M_CEIL)
K.box("Floor", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.04), (0, 0, -0.02), M_FLOOR)
box("Ceiling", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.05), (0, 0, R.h + 0.025), M_CEIL)
lathe("CeilingRose", [(0.0, 0.0), (0.38, 0.0), (0.36, -0.02), (0.3, -0.03), (0.22, -0.05), (0.1, -0.07), (0.0, -0.08)], (-1.0, 0.0, R.h), M_CEIL, steps=28)
# the carpet, rolled back from the east end for the dancing
CX0, CX1 = -4.1, 2.0
box("Carpet", (CX1 - CX0, 5.4, 0.012), ((CX0 + CX1) / 2, 0.0, 0.006), M_CARPET, bevel=0.004)
M_JUTE = noisy("M_CarpetBack", [srgb((0.46, 0.38, 0.27)), srgb((0.52, 0.44, 0.32)), srgb((0.40, 0.33, 0.23))], scale=120, rough=0.95, bump=0.4, bump_dist=0.002, stretch=(1, 1, 8))
roll = lathe("CarpetRoll", [(0.0, -2.75), (0.16, -2.75), (0.17, -2.7), (0.17, 2.7), (0.16, 2.75), (0.0, 2.75)], (CX1 + 0.2, 0.0, 0.17), M_JUTE, steps=14)
roll.rotation_euler = (math.pi / 2, 0, 0)
box("CarpetTail", (0.25, 5.4, 0.012), (CX1 + 0.08, 0.0, 0.03), M_CARPET, rot=(0, -0.5, 0))
for sy in (-1, 1): cyl(f"RollEnd{sy}", 0.168, 0.01, (CX1 + 0.2, sy * 2.752, 0.17), M_CARPET, verts=14, rot=(math.pi / 2, 0, 0))
# mouldings
I.moulding_runs(R, "Skirting", I.skirting_profile(0.24), 0.0, M_JOIN)
I.moulding_runs(R, "ChairRail", I.rail_profile(), 0.9, M_JOIN, z_band=(0.86, 0.94))
I.moulding_runs(R, "Cornice", I.cornice_profile(0.24, 0.28), R.h, M_JOIN, z_band=(R.h - 0.28, R.h))
for w in ('S', 'E', 'N', 'W'):
    o, a, n, L = R.wall_frame(w)
    for k, (u0, u1) in enumerate(I.runs(R, w, 0.24, 0.88)):
        c = o + a * ((u0 + u1) / 2) + n * 0.004 + Vector((0, 0, 0.56))
        box(f"Dado{w}{k}", (abs(a.x) * (u1 - u0) + abs(n.x) * 0.008, abs(a.y) * (u1 - u0) + abs(n.y) * 0.008, 0.64), tuple(c), M_DADO)

# ----------------------------------------------------------------------------- the chimney-piece (west wall, painted), the fire
FP_Y = 0.2
F = Frame((R.x0, FP_Y), math.atan2(-1, 0))
def FP(x, y, z): return F.p(x, y, z)
OW, OH = 0.86, 0.88
F.box("HearthStone", (1.6, 0.5, 0.04), (0, 0.25, 0.02), noisy("M_HearthStone", [srgb((0.52, 0.50, 0.46)), srgb((0.44, 0.42, 0.38))], scale=6, rough=0.6), bevel=0.004)
for sx in (-1, 1):
    F.box(f"Jamb{sx}", (0.24, 0.15, OH), (sx * (OW / 2 + 0.12), 0.075, OH / 2), M_PAINTWOOD, bevel=0.006)
    F.box(f"Pilaster{sx}", (0.14, 0.03, OH - 0.1), (sx * (OW / 2 + 0.12), 0.16, OH / 2), M_PAINTWOOD, bevel=0.006)
    F.box(f"CornerBlock{sx}", (0.26, 0.17, 0.24), (sx * (OW / 2 + 0.12), 0.085, OH + 0.12), M_PAINTWOOD, bevel=0.008)
    cyl(f"Patera{sx}", 0.06, 0.02, FP(sx * (OW / 2 + 0.12), 0.175, OH + 0.12), M_GILT, verts=14, rot=(math.pi / 2, 0, F.yaw))
F.box("Frieze", (OW, 0.14, 0.24), (0, 0.07, OH + 0.12), M_PAINTWOOD, bevel=0.004)
F.box("FriezeSwag", (0.6, 0.02, 0.1), (0, 0.15, OH + 0.12), M_GILT, bevel=0.02)
F.box("Shelf", (1.7, 0.24, 0.05), (0, 0.11, OH + 0.27), M_PAINTWOOD, bevel=0.012)
F.box("GratePlate", (OW, 0.03, OH), (0, 0.012, OH / 2), M_IRON)
F.box("GrateMouth", (OW * 0.62, 0.03, OH * 0.5), (0, 0.02, OH * 0.38), M_SOOT)
F.box("BasketFloor", (0.52, 0.22, 0.03), (0, 0.12, 0.15), M_IRON)
for k in range(5): F.box(f"BasketBar{k}", (0.52, 0.014, 0.014), (0, 0.24, 0.17 + k * 0.045), M_IRON, bevel=0.003)
for sx in (-1, 1):
    F.box(f"BasketSide{sx}", (0.02, 0.22, 0.22), (sx * 0.26, 0.12, 0.25), M_IRON)
    lathe(f"Urn{sx}", [(0.0, 0.0), (0.03, 0.0), (0.03, 0.03), (0.022, 0.06), (0.035, 0.1), (0.02, 0.14), (0.0, 0.15)], FP(sx * 0.32, 0.24, 0.15), M_BRASS, steps=10)
cr = random.Random(5)
for k in range(24):
    lx = cr.uniform(-0.22, 0.22); ly = cr.uniform(0.04, 0.22); lz = 0.18 + cr.uniform(0, 0.09) * (1 - abs(lx) / 0.3)
    sphere(f"Coal{k}", cr.uniform(0.028, 0.05), FP(lx, ly, lz), M_EMBERS if lz < 0.25 or cr.random() < 0.5 else M_IRON, seg=6,
           scale=(cr.uniform(0.8, 1.3), cr.uniform(0.8, 1.3), cr.uniform(0.6, 0.9)))
FIRE_BASE = Vector(FP(0, 0.13, 0.22))
F.box("FenderFront", (1.45, 0.012, 0.09), (0, 0.48, 0.045), M_BRASS, bevel=0.004)
for sx in (-1, 1): F.box(f"FenderSide{sx}", (0.012, 0.34, 0.09), (sx * 0.72, 0.32, 0.045), M_BRASS, bevel=0.004)
SHELF_Z = OH + 0.295
F.box("MirrorGlass", (1.25, 0.02, 1.05), (0, 0.03, SHELF_Z + 0.7), M_MIRROR)
for (fx_, fz, sw, sh) in ((0, SHELF_Z + 0.7 + 0.57, 1.42, 0.09), (0, SHELF_Z + 0.7 - 0.57, 1.42, 0.09), (-0.67, SHELF_Z + 0.7, 0.09, 1.05), (0.67, SHELF_Z + 0.7, 0.09, 1.05)):
    F.box(f"MirrorFrame{fx_}{fz}", (sw, 0.06, sh), (fx_, 0.05, fz), M_GILT, bevel=0.015)
F.box("MirrorCrest", (0.5, 0.04, 0.16), (0, 0.05, SHELF_Z + 1.36), M_GILT, bevel=0.04)
# chimney ornaments: a pair of porcelain vases, a gilt clock under a dome
for sx in (-1, 1):
    lathe(f"Vase{sx}", [(0.0, 0.0), (0.045, 0.0), (0.04, 0.02), (0.06, 0.08), (0.05, 0.14), (0.025, 0.18), (0.035, 0.21), (0.0, 0.21)], FP(sx * 0.45, 0.12, SHELF_Z), M_PORCELAIN, steps=14)
F.box("ClockBase", (0.3, 0.14, 0.05), (0, 0.11, SHELF_Z + 0.025), M_GILT, bevel=0.01)
F.box("ClockBody", (0.2, 0.1, 0.22), (0, 0.11, SHELF_Z + 0.16), M_GILT, bevel=0.02)
cyl("ClockDial", 0.055, 0.01, FP(0, 0.165, SHELF_Z + 0.17), M_PORCELAIN, verts=20, rot=(math.pi / 2, 0, F.yaw))
CANDLE_TOPS = {"mantel": []}
for sx in (-1, 1):
    CANDLE_TOPS["mantel"] += I.candlestick(f"MantelStick{sx}", FP(sx * 0.72, 0.11, SHELF_Z), M_SILVER, M_WAX, height=0.27, candle_h=0.17)
anchor("room.fireplace", FP(0, 0.4, 0))

# ----------------------------------------------------------------------------- the square pianoforte (south wall), opened, with music and candles
PFX = -0.95
PF = Frame((PFX, R.y0 + 0.4), 0.0)
PF.box("PianoCase", (1.68, 0.62, 0.28), (0, 0, 0.72), M_MAHOG, bevel=0.008)
PF.box("PianoBand", (1.70, 0.64, 0.03), (0, 0, 0.6), M_SATIN, bevel=0.004)
# the lid raised and propped, the front flap folded back
lid = PF.box("PianoLid", (1.68, 0.62, 0.02), (0, -0.02, 0.87), M_MAHOG, bevel=0.006)
lid.rotation_euler = (math.radians(-38), 0, 0); lid.location = PF.p(0, -0.27, 1.06)
PF.box("PianoProp", (0.02, 0.02, 0.36), (0.45, 0.0, 1.0), M_MAHOG)
PF.box("Soundboard", (1.55, 0.5, 0.01), (0, -0.02, 0.84), M_SATIN)
for k in range(0, 40):    # strings, a hint of them
    PF.box(f"String{k}", (0.002, 0.44 - 0.006 * k, 0.002), (-0.62 + k * 0.035, -0.03, 0.852), M_BRASS)
# the keyboard: 5 octaves, ivory naturals, ebony sharps (as the period)
KB = MB()
for k in range(35):
    S.mb_box(KB, Vector(PF.p(-0.62 + k * 0.0224, 0.27, 0.745)), (0.021, 0.12, 0.014), yaw=PF.yaw)
KB.build("PianoNaturals", M_IVORY, sway=False)
KS = MB()
for k in range(35):
    if k % 7 in (2, 6): continue
    S.mb_box(KS, Vector(PF.p(-0.62 + k * 0.0224 + 0.0112, 0.245, 0.758)), (0.012, 0.075, 0.014), yaw=PF.yaw)
KS.build("PianoSharps", M_EBONY, sway=False)
PF.box("NameBoard", (0.9, 0.02, 0.09), (-0.24, 0.215, 0.81), M_SATIN, bevel=0.003)
PF.box("MusicDesk", (0.5, 0.02, 0.32), (-0.24, 0.12, 1.0), M_MAHOG, bevel=0.004)
# open music on the desk, more music books in a pile on the lid end
mb_ = MB()
for k, (dx, ang) in enumerate(((-0.13, 0.08), (0.13, -0.08))):
    S.mb_box(mb_, Vector(PF.p(-0.24 + dx, 0.10, 1.03)), (0.24, 0.006, 0.31), yaw=PF.yaw + ang)
mb_.build("OpenMusic", M_MUSIC, sway=False)
for k in range(4):
    PF.box(f"MusicBook{k}", (0.25, 0.33, 0.018), (0.55 + 0.01 * k, 0.05 - 0.005 * k, 0.89 + k * 0.019), M_BOARDCOVER if k % 2 == 0 else M_MUSIC, bevel=0.002)
for sx in (-1, 1):
    for sy in (-1, 1):
        lathe(f"PianoLeg{sx}{sy}", [(0.0, 0.0), (0.018, 0.0), (0.02, 0.08), (0.032, 0.3), (0.036, 0.5), (0.0, 0.58)], PF.p(sx * 0.76, sy * 0.25, 0.0), M_MAHOG, steps=10)
CANDLE_TOPS["piano"] = []
for sx in (-1, 1):
    CANDLE_TOPS["piano"] += I.candlestick(f"PianoStick{sx}", PF.p(sx * 0.62 - 0.24 * 0, 0.18, 0.86), M_SILVER, M_WAX, height=0.24, candle_h=0.15)
# the bench before the instrument
PF.box("BenchTop", (0.95, 0.36, 0.06), (-0.24, 0.72, 0.47), M_CHAIRSILK, bevel=0.025)
PF.box("BenchRail", (0.92, 0.33, 0.06), (-0.24, 0.72, 0.42), M_MAHOG, bevel=0.006)
for sx in (-1, 1):
    for sy in (-1, 1): PF.cyl(f"BenchLeg{sx}{sy}", 0.018, 0.42, (-0.24 + sx * 0.42, 0.72 + sy * 0.14, 0.2), M_MAHOG, verts=8, r2=0.013)
anchor("pianoforte", PF.p(0, 0, 0))

# ----------------------------------------------------------------------------- chairs grouped for conversation, the sofa, card tables pushed aside
def face(pos, target): return math.atan2(-(target[0] - pos[0]), target[1] - pos[1])
G1 = Vector((-2.9, -1.6))       # a group by the fire
for k, (dx, dy) in enumerate(((-0.6, 0.6), (0.6, 0.55), (0.35, -0.75), (-0.75, -0.45))):
    pos = G1 + Vector((dx, dy))
    I.sabre_chair(f"ChairG1_{k}", (pos.x, pos.y), face(pos, G1) + rng.uniform(-0.3, 0.3), M_MAHOG, M_CHAIRSILK)
G2 = Vector((-1.2, 1.0))        # a group in the middle of the room, half turned to watch the dancing
for k, (dx, dy) in enumerate(((-0.5, 0.45), (0.55, 0.35), (0.4, -0.6))):
    pos = G2 + Vector((dx, dy))
    I.sabre_chair(f"ChairG2_{k}", (pos.x, pos.y), face(pos, G2 + Vector((1.5, -0.3))) + rng.uniform(-0.25, 0.25), M_MAHOG, M_CHAIRSILK)
for k, y in enumerate((-1.9, -0.9, 0.1, 1.1, 2.1)):   # chairs set back along the east wall for the dancers
    if abs(y - 0.0) < 0.2: continue
    I.sabre_chair(f"ChairE_{k}", (R.x1 - 0.35, y), math.pi / 2 + rng.uniform(-0.1, 0.1), M_MAHOG, M_CHAIRSILK)
def sofa(name, x, y, yaw, length=1.9):
    Fs = Frame((x, y), yaw)
    Fs.box(f"{name}Rail", (length, 0.68, 0.16), (0, 0, 0.3), M_MAHOG, bevel=0.01)
    Fs.box(f"{name}Seat", (length - 0.2, 0.6, 0.12), (0, 0.03, 0.43), M_SOFASILK, bevel=0.04)
    Fs.box(f"{name}Back", (length - 0.05, 0.16, 0.5), (0, -0.27, 0.66), M_SOFASILK, bevel=0.05, rx=-0.12)
    for sx in (-1, 1):
        Fs.box(f"{name}ArmPad{sx}", (0.12, 0.58, 0.3), (sx * (length / 2 - 0.06), 0.0, 0.58), M_SOFASILK, bevel=0.04)
        cyl(f"{name}Bolster{sx}", 0.1, 0.52, Fs.p(sx * (length / 2 - 0.18), 0.02, 0.6), M_SOFASILK, verts=12, rot=(math.pi / 2, 0, Fs.yaw))
        for sy in (-1, 1):
            tube(f"{name}Leg{sx}{sy}", [Fs.p(sx * (length / 2 - 0.05), sy * 0.3, 0.22), Fs.p(sx * (length / 2 + 0.03), sy * 0.33, 0.1), Fs.p(sx * (length / 2 + 0.06), sy * 0.35, 0.0)],
                 [0.025, 0.02, 0.015], M_MAHOG, sides=6)
sofa("Sofa", -3.35, R.y1 - 0.45, math.pi)
I.picture("Engraving", R, 'N', R.x1 - (-3.35), 1.95, 0.9, 0.62, M_GILT, M_ENGRAVING)
I.picture("Landscape", R, 'S', 2.6 + 0.2, 1.95, 0.8, 0.62, M_GILT, M_LAND)
def card_table(name, x, y, yaw):
    """a folding card table, its top folded over, pushed against the wall: the baize lining shows when open; folded,
    a satinwood half-moon top on four tapered legs, one swung back."""
    Ft = Frame((x, y), yaw)
    Ft.box(f"{name}Top", (0.9, 0.44, 0.03), (0, 0.0, 0.74), M_SATIN, bevel=0.005)
    Ft.box(f"{name}Leaf", (0.9, 0.44, 0.03), (0, 0.0, 0.77), M_SATIN, bevel=0.005)
    Ft.box(f"{name}Apron", (0.86, 0.4, 0.11), (0, 0.0, 0.67), M_MAHOG, bevel=0.004)
    for sx in (-1, 1):
        for sy in (-1, 1): Ft.cyl(f"{name}Leg{sx}{sy}", 0.02, 0.62, (sx * 0.4, sy * 0.18, 0.31), M_MAHOG, verts=8, r2=0.012)
card_table("CardTableA", -0.35, R.y1 - 0.27, math.pi)
card_table("CardTableB", 2.15, R.y1 - 0.27, math.pi)
# one card table still open in the corner, its baize and a few cards and counters on it (the earlier game)
Ft = Frame((3.4, R.y1 - 0.75), math.pi * 0.85)
Ft.box("OpenTableTop", (0.9, 0.9, 0.03), (0, 0, 0.74), M_SATIN, bevel=0.005)
Ft.box("OpenTableBaize", (0.82, 0.82, 0.004), (0, 0, 0.757), M_BAIZE)
Ft.box("OpenTableApron", (0.86, 0.86, 0.1), (0, 0, 0.67), M_MAHOG, bevel=0.004)
for sx in (-1, 1):
    for sy in (-1, 1): Ft.cyl(f"OpenTableLeg{sx}{sy}", 0.02, 0.62, (sx * 0.4, sy * 0.4, 0.31), M_MAHOG, verts=8, r2=0.012)
M_CARD = plain("M_CardBacks", srgb((0.40, 0.46, 0.56)), rough=0.45)
for k in range(9):
    Ft.box(f"Card{k}", (0.064, 0.09, 0.0012), (rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0.76 + 0.0012 * k), M_CARD).rotation_euler.z += rng.uniform(0, 3)
# girandoles: gilt two-light sconces on the walls
def sconce(name, w, u, z):
    o, a, n, L = R.wall_frame(w)
    c = o + a * u + n * 0.02 + Vector((0, 0, z))
    box(f"{name}Plate", (abs(a.x) * 0.16 + abs(n.x) * 0.03, abs(a.y) * 0.16 + abs(n.y) * 0.03, 0.36), tuple(c), M_GILT, bevel=0.03)
    tops = []
    for s_ in (-1, 1):
        arm0 = c + n * 0.03 + Vector((0, 0, -0.08)); arm1 = c + n * 0.2 + a * s_ * 0.16 + Vector((0, 0, -0.04))
        tube(f"{name}Arm{s_}", [arm0, (arm0 + arm1) / 2 + Vector((0, 0, -0.05)), arm1], 0.008, M_GILT, sides=6)
        tops += I.candlestick(f"{name}C{s_}", tuple(arm1 + Vector((0, 0, -0.05))), M_GILT, M_WAX, height=0.06, candle_h=0.16)
    return tops
CANDLE_TOPS["sconces"] = []
for (w, u) in (('N', 4.85), ('N', 2.35), ('S', 4.6), ('E', 3.0)):
    CANDLE_TOPS["sconces"] += sconce(f"Sconce{w}{u:.0f}", w, u, 1.85)

# ----------------------------------------------------------------------------- lights
def centre(pts): return sum((Vector(p) for p in pts), Vector()) / len(pts)
light_obj("Lamp.fire", 'POINT', 80.0, (1.0, 0.52, 0.24), tuple(FIRE_BASE + Vector((0.38, 0, 0.12))), shadow_soft_size=0.22)
light_obj("Lamp.candles.piano", 'POINT', 9.0, (1.0, 0.72, 0.45), tuple(centre(CANDLE_TOPS["piano"]) + Vector((0, 0, 0.02))), shadow_soft_size=0.3)
light_obj("Lamp.candles.mantel", 'POINT', 7.0, (1.0, 0.72, 0.45), tuple(centre(CANDLE_TOPS["mantel"]) + Vector((0.08, 0, 0.015))), shadow_soft_size=0.4)
for k in range(0, len(CANDLE_TOPS["sconces"]), 2):
    light_obj(f"Lamp.sconce{k // 2}", 'POINT', 9.0, (1.0, 0.72, 0.45), tuple(centre(CANDLE_TOPS["sconces"][k:k + 2]) + Vector((0, 0, 0.02))), shadow_soft_size=0.15)
pl = light_obj("RenderOnly_PassageGlow", 'POINT', 3.0, (1.0, 0.7, 0.45), (dp.x, R.y0 - R.t - 1.2, 1.6), shadow_soft_size=0.05)
I.RENDER_ONLY.append(pl)
world = bpy.data.worlds.new("Night"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.010, 0.012, 0.018, 1)

# ----------------------------------------------------------------------------- anchors and living-scene sources
eye, fwd = S.reader(tuple(READER), YAW)
anchor("scene.centre", (0.0, 0.0, 0.0))
anchor("dancing.end", (3.0, 0.0, 0.0))
S.fx("fire", "hearth", tuple(FIRE_BASE), 0.22)
k = 0
for grp, tops in CANDLE_TOPS.items():
    for t in tops:
        S.fx("candle", f"{grp}{k}", t, 0.012); k += 1
sound("fire", "hearth", tuple(FIRE_BASE + Vector((0.2, 0, 0.1))))
sound("crowd", "passage", (dp.x, R.y0 - R.t - 1.0, 1.4))
sound("clock", "mantel", FP(0, 0.15, SHELF_Z + 0.17))
page = S.page_preview(eye, fwd)
cams = S.view_cams(eye, YAW, extra=[
    ("Cam_Page", eye, eye + fwd * 10 + Vector((0, 0, -1.2)), 17),
    ("Cam_Piano", Vector((1.0, -0.6, 1.5)), Vector(PF.p(0, 0, 0.85)), 24),
    ("Cam_Fire", Vector((-1.8, -0.4, 1.3)), Vector(FP(0, 0.2, 0.9)), 24),
    ("Cam_Dance", Vector((-0.8, -1.2, 1.55)), Vector((3.4, 0.6, 0.6)), 20),
])
S.finish(ARGS, cams, "lucas_lodge_drawing_room.gltf", page=page, render_only=list(I.RENDER_ONLY), default_exposure=0.6,
         keep_names={"M_Embers": "MESH_Embers", "M_WindowGlassNight": "WindowGlass_night", "M_Curtains": "cloth.curtain.windows"},
         size_for={"M_FloorBoards": (1024, 256, 1024), "M_Carpet": (2048, 128, 1024), "M_WallPaper": (2048, 128, 1024), "M_Ceiling": (512, 64, 256),
                   "M_Joinery": (1024, 256, 1024), "M_DadoPaint": (1024, 64, 256), "M_Mahogany": (1024, 256, 512), "M_Satinwood": (512, 128, 256),
                   "M_Curtains": (1024, 128, 512), "M_SofaSilk": (512, 128, 256), "M_ChairSilk": (512, 128, 256), "M_Gilt": (512, 128, 256),
                   "M_DoorMahogany": (512, 128, 256), "M_Landscape": (512, 64, 128), "M_Engraving": (512, 64, 128), "M_Silver": (128, 64, 64),
                   "M_Brass": (128, 64, 64), "M_Iron": (256, 64, 128), "M_Embers": (256, 64, 128), "M_ChimneyPaint": (512, 128, 256),
                   "M_Wax": (128, 32), "M_Mirror": (64, 32), "M_WindowGlassNight": (32, 32), "M_Soot": (32, 32), "M_Ivory": (128, 32),
                   "M_Ebony": (64, 32), "M_MusicPaper": (256, 64, 128), "M_MusicCovers": (128, 64, 64), "M_Baize": (128, 64, 128), "M_CarpetBack": (256, 64, 128)},
         default_size=(256, 64, 128))
