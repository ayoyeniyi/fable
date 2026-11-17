"""
Fable scene room: the British consul's office at Suez (Around the World in Eighty Days, chapter VII) - suez-consulate.

"The detective passed down the quay, and rapidly made his way to the consul's office" "a knock was heard at the door,
and two strangers entered ... held out his passport with the request that the consul would do him the favour to visa
it ... Fix observed, or rather devoured, the stranger with his eyes from a corner of the room." "The consul proceeded
to sign and date the passport, after which he added his official seal. Mr. Fogg paid the customary fee, coldly
bowed, and went out"

The consul's office in a house on the corner of the square by the quay, 9 October 1872, just after eleven in the
morning: whitewashed walls, a floor of terracotta and cream tiles, a dark-beamed ceiling; the consul's mahogany
pedestal desk in the middle with a green leather top, the inkstand and pens, the official seal, the fee register open
beside a passport waiting for its visa, a blotter and a sand box; the consul's chair behind it, two cane chairs before
it; behind the desk the tall window with its louvred shutters half closed, the late-morning sun coming through the
slats in bars across the floor and the desk, and beyond it the glare of the quay and the masts of ships in the canal
roads; the royal arms above the window, a chart of the canal from Port Said to Suez on the wall, a cabinet of
pigeon-holes, a hat-stand, the ensign furled on its staff in the corner where Fix stood. No people.

Light: bright clear late morning, the sun high in the south-east through the shutters; the room cool and shaded.

Axes: metres, +Z up; the room x -2.6..2.6, y -3.0..3.0; the window and the desk at +Y. The reader just inside the door
(south wall, left) facing the desk.

Run headless:
  blender -b -P blender/build_suez_consulate.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_suez_consulate.py -- --cpu --render --samples 48 --res 1024 --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b4 as S
from scene_kit_b4 import K
import pride_interior as I
from scene_kit_b4 import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, lathe, tube, MB, Frame, anchor, sound, light_obj, smoothstep, srgb,
                          mb_box, mb_quad)

ARGS = S.setup("suez-consulate", 1872, "SuezConsulate", default_samples=48)
scene = K.scene
rng = random.Random(1872)
scene.cycles.max_bounces = 8; scene.cycles.diffuse_bounces = 5
EYE = S.EYE
R = I.Room(-2.6, 2.6, -3.0, 3.0, 4.0, t=0.5)
SUN_DIR = Vector((0.45, 0.62, 0.64)).normalized()       # toward the sun (through the window at +Y), ~40 degrees up
WIN_X, WIN_W, WIN_Z0, WIN_Z1 = 0.2, 1.4, 0.75, 3.15
DOOR_X, DOOR_W = -1.75, 1.05
READER = Vector((-1.45, -2.05, 0.0)); YAW = 16.0

# ----------------------------------------------------------------------------- materials
def whitewash(name):
    """Lime whitewash on rough plaster: a warm off-white, uneven coats, faint grey at the skirting and round the door
    where hands and chairs have rubbed."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-1800, 0)); s = sep_xyz(nt, co, (-1600, 0))
    n1 = noise_(nt, co, 1.6, 5, 0.6, loc=(-1300, 200)); n2_ = noise_(nt, co, 14.0, 4, 0.6, loc=(-1300, -100))
    col = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.3, 0.7, 0, 1), c4(srgb((0.86, 0.84, 0.78))), c4(srgb((0.93, 0.91, 0.86))), (-1000, 100))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, s.outputs["Z"], 0.0, 0.35, 0.3, 0.0, (-1100, -300)), col, c4(srgb((0.7, 0.66, 0.6))), (-800, 100))
    col = K.ao_mul(nt, col, 0.3, 0.3, (-600, -500))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    bump_from(nt, b, math_(nt, 'ADD', n2_.outputs["Fac"], math_(nt, 'MULTIPLY', n1.outputs["Fac"], 2.0)), 0.15, 0.004, (0, -500))
    return m


def tiles_mat(name):
    """Square floor tiles, terracotta and cream laid chequerwise on the diagonal, worn and dusty, thin grout lines."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2000, 0))
    mp = node(nt, "ShaderNodeMapping", (-1800, 0)); mp.inputs["Rotation"].default_value = (0, 0, math.radians(45)); mp.inputs["Scale"].default_value = (1 / 0.28, 1 / 0.28, 1)
    nt.links.new(co, mp.inputs["Vector"])
    ch = node(nt, "ShaderNodeTexChecker", (-1500, 0)); ch.inputs["Scale"].default_value = 1.0
    ch.inputs["Color1"].default_value = c4(srgb((0.62, 0.34, 0.22))); ch.inputs["Color2"].default_value = c4(srgb((0.82, 0.76, 0.62)))
    nt.links.new(mp.outputs["Vector"], ch.inputs["Vector"])
    sx = sep_xyz(nt, mp.outputs["Vector"], (-1500, -300))
    gx = maprange(nt, math_(nt, 'FRACT', sx.outputs["X"], None, (-1300, -300)), 0.0, 0.03, 1, 0, (-1150, -300))
    gy = maprange(nt, math_(nt, 'FRACT', sx.outputs["Y"], None, (-1300, -450)), 0.0, 0.03, 1, 0, (-1150, -450))
    grout = math_(nt, 'MAXIMUM', gx, gy, (-1000, -350))
    n = noise_(nt, co, 3.0, 5, 0.6, loc=(-1300, 300))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 0.25, (-1000, 300)), ch.outputs["Color"], c4(srgb((0.7, 0.66, 0.6))), (-800, 100))
    col = mix_rgb(nt, 'MIX', grout, col, c4(srgb((0.55, 0.50, 0.44))), (-600, 100))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.45, 0.75, (-600, -200)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'SUBTRACT', 1.0, grout), 0.3, 0.003, (0, -500))
    return m


def arms_atlas():
    """The royal arms, painted on a board: the quartered shield (three lions passant gold on red twice, the lion
    rampant of Scotland, the harp of Ireland on blue) within the garter, the lion and the unicorn supporting, the crown
    above and the motto scroll below. 512 x 512, row 0 at the top; transparent round the outline."""
    S_ = 512; cv = Canvas(S_, S_)
    gold = (0.80, 0.62, 0.22, 1.0); red = (0.62, 0.10, 0.08, 1.0); blue = (0.10, 0.18, 0.48, 1.0); white = (0.92, 0.90, 0.84, 1.0)
    cx, cy = 256, 270
    cv.ellipse(cx, cy, 120, 140, 0, (0.10, 0.16, 0.36, 1.0))        # the garter (blue)
    cv.ellipse(cx, cy, 104, 124, 0, gold)
    # the shield: four quarters
    for (qx, qy, col) in ((-1, -1, red), (1, -1, gold), (-1, 1, blue), (1, 1, red)):
        cv.ellipse(cx + qx * 46, cy + qy * 52, 44, 50, 0, col, soft=2.0)
    cv.line((cx, cy - 104), (cx, cy + 112), 3, 3, gold); cv.line((cx - 92, cy), (cx + 92, cy), 3, 3, gold)
    for (qx, qy) in ((-1, -1), (1, 1)):          # three lions as gold bars
        for k in range(3): cv.ellipse(cx + qx * 46, cy + qy * 52 - 28 + k * 26, 26, 7, 0, gold)
    cv.ellipse(cx + 46, cy - 52, 16, 28, 0.3, red)          # Scotland's lion
    cv.line((cx - 60, cy + 40), (cx - 34, cy + 80), 4, 3, gold); cv.ellipse(cx - 42, cy + 52, 14, 20, 0.3, gold)   # the harp
    # supporters: the lion (gold) left and the unicorn (white) right, rearing
    for sg, col in ((-1, gold), (1, white)):
        cv.ellipse(cx + sg * 160, cy + 20, 34, 70, -sg * 0.25, col)
        cv.ellipse(cx + sg * 150, cy - 64, 24, 26, 0, col)
        cv.line((cx + sg * 175, cy + 80), (cx + sg * 185, cy + 150), 9, 7, col); cv.line((cx + sg * 140, cy + 80), (cx + sg * 135, cy + 150), 9, 7, col)
        cv.line((cx + sg * 135, cy - 20), (cx + sg * 105, cy - 40), 8, 6, col)
    cv.line((cx + 160, cy - 86), (cx + 175, cy - 130), 3, 1, gold)    # the unicorn's horn
    # the crown
    cv.ellipse(cx, cy - 170, 52, 22, 0, gold); cv.ellipse(cx, cy - 192, 34, 26, 0, red); cv.ellipse(cx, cy - 214, 8, 8, 0, gold)
    # the motto scroll
    cv.ellipse(cx, cy + 190, 150, 16, 0, white)
    for k in range(9): cv.line((cx - 110 + k * 27, cy + 190), (cx - 96 + k * 27, cy + 190), 2, 2, (0.2, 0.15, 0.1, 1.0))
    cv.bleed(4)
    return np_image("A_RoyalArms", cv.a)


def chart_mat(name):
    """A printed chart of the canal: buff paper, the blue line of the canal running from Port Said through Lake Timsah
    and the Bitter Lakes to Suez, the sea at each end, a fine grid and a cartouche."""
    m, nt, b = new_mat(name)
    co = node(nt, "ShaderNodeTexCoord", (-1800, 0)); g = co.outputs["Generated"]; s = sep_xyz(nt, g, (-1600, 0))
    v = s.outputs["Z"]; u = math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-1450, -100))
    line_x = math_(nt, 'ADD', 0.5, math_(nt, 'MULTIPLY', math_(nt, 'SINE', math_(nt, 'MULTIPLY', v, 5.0)), 0.06), (-1300, 200))
    canal = maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', u, line_x), None, (-1150, 200)), 0.004, 0.009, 1, 0, (-1000, 200))
    lakes = maprange(nt, voronoi_(nt, g, 3.0, 'F1', (-1300, 500)).outputs["Distance"], 0.12, 0.08, 0, 1, (-1100, 500))
    lakes = math_(nt, 'MULTIPLY', lakes, maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', u, line_x)), 0.05, 0.02, 0, 1, (-1100, 650)), (-950, 550))
    seas = math_(nt, 'ADD', maprange(nt, v, 0.08, 0.06, 0, 1, (-1100, 800)), maprange(nt, v, 0.92, 0.94, 0, 1, (-1100, 950)), (-950, 850))
    water = math_(nt, 'MINIMUM', math_(nt, 'ADD', math_(nt, 'ADD', canal, lakes), seas), 1.0, (-800, 500))
    gridu = maprange(nt, math_(nt, 'FRACT', math_(nt, 'MULTIPLY', u, 10.0)), 0.0, 0.01, 1, 0, (-1100, -300))
    gridv = maprange(nt, math_(nt, 'FRACT', math_(nt, 'MULTIPLY', v, 10.0)), 0.0, 0.01, 1, 0, (-1100, -450))
    grid = math_(nt, 'MULTIPLY', math_(nt, 'MAXIMUM', gridu, gridv), 0.25, (-950, -380))
    col = mix_rgb(nt, 'MIX', water, c4(srgb((0.84, 0.78, 0.62))), c4(srgb((0.46, 0.60, 0.70))), (-600, 200))
    col = mix_rgb(nt, 'MULTIPLY', grid, col, c4(srgb((0.5, 0.45, 0.4))), (-400, 200))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.8
    return m


def louvre_shutter(name, origin, yaw, w, hgt, open_deg, slat_tilt, mat):
    """A louvred shutter leaf: a frame with horizontal slats tilted (slat_tilt radians), hinged at origin, opened by open_deg."""
    mb = MB(); Rm = Matrix.Rotation(yaw + math.radians(open_deg), 3, 'Z')
    def P(x, y, z): return Vector(origin) + Rm @ Vector((x, y, z))
    for (x, wd) in ((0.025, 0.05), (w - 0.025, 0.05)):
        mb_box(mb, P(x, 0, hgt / 2), (wd, 0.035, hgt), yaw=yaw + math.radians(open_deg))
    for z in (0.025, hgt / 2, hgt - 0.025): mb_box(mb, P(w / 2, 0, z), (w, 0.035, 0.05), yaw=yaw + math.radians(open_deg))
    n = int(hgt / 0.055)
    for k in range(1, n):
        z = k * hgt / n
        if abs(z - hgt / 2) < 0.04: continue
        mb_box(mb, P(w / 2, 0, z), (w - 0.09, 0.006, 0.05), yaw=yaw + math.radians(open_deg), tilt=(slat_tilt, 0))
    return mb.build(name, mat, sway=False)


M_WALL = whitewash("M_Whitewash")
M_FLOOR = tiles_mat("M_FloorTiles")
M_BEAM = noisy("M_DarkBeams", [srgb((0.20, 0.14, 0.09)), srgb((0.26, 0.19, 0.12)), srgb((0.15, 0.11, 0.07))], scale=3.0, rough=0.75, bump=0.2, stretch=(6, 0.4, 6))
M_MAHOG = I.mahogany("M_Mahogany")
M_SHUTTER = noisy("M_ShutterPaint", [srgb((0.20, 0.30, 0.22)), srgb((0.24, 0.34, 0.25)), srgb((0.30, 0.36, 0.28))], scale=8.0, rough=0.6, bump=0.05)
M_LEATHER = noisy("M_GreenLeather", [srgb((0.12, 0.22, 0.14)), srgb((0.16, 0.27, 0.18))], scale=40.0, rough=0.5, bump=0.1)
M_BRASS = plain("M_Brass", srgb((0.78, 0.60, 0.32)), rough=0.25, metallic=1.0)
M_GLASS = plain("M_InkGlass", srgb((0.10, 0.12, 0.14)), rough=0.05)
M_PAPER = noisy("M_Paper", [srgb((0.90, 0.87, 0.78)), srgb((0.84, 0.80, 0.70))], scale=30.0, rough=0.85, bump=0.0)
M_CANE = noisy("M_Cane", [srgb((0.70, 0.56, 0.34)), srgb((0.62, 0.48, 0.28)), srgb((0.78, 0.64, 0.42))], scale=120.0, rough=0.6, bump=0.5, bump_dist=0.002)
M_BENTWOOD = noisy("M_Bentwood", [srgb((0.26, 0.15, 0.08)), srgb((0.32, 0.19, 0.10))], scale=10.0, rough=0.4, bump=0.05)
M_CHART = chart_mat("M_Chart")
M_FRAME = I.gilt("M_Frame")
M_ARMS = image_mat("M_RoyalArms", arms_atlas(), rough=0.5, alpha=True, spec=0.3)
M_ARMSBOARD = plain("M_ArmsBoard", srgb((0.08, 0.08, 0.10)), rough=0.4)
M_OUTSIDE = noisy("M_QuayGlare", [srgb((0.86, 0.78, 0.62)), srgb((0.80, 0.72, 0.56))], scale=2.0, rough=0.9, bump=0.0)
M_BUILD = noisy("M_QuayBuildings", [srgb((0.88, 0.82, 0.70)), srgb((0.80, 0.74, 0.62))], scale=1.0, rough=0.9, bump=0.0)
M_SEA = noisy("M_CanalWater", [srgb((0.18, 0.40, 0.46)), srgb((0.22, 0.46, 0.50))], scale=0.2, rough=0.1, bump=0.0)
M_SPAR = plain("M_Spars", srgb((0.30, 0.22, 0.14)), rough=0.6)
M_RED = plain("M_EnsignRed", srgb((0.60, 0.10, 0.09)), rough=0.85)
M_SKY = S.sky_mat(zenith=srgb((0.30, 0.52, 0.86)), horizon=srgb((0.88, 0.86, 0.80)), ground=srgb((0.80, 0.72, 0.56)), sun_dir=SUN_DIR,
                  glow=srgb((1.0, 0.95, 0.85)), glow_k=0.4, glow_pow=8.0, clouds=0.05, strength=1.4)

# ----------------------------------------------------------------------------- the shell: walls with the window (N) and the door (S); floor, beamed ceiling
R.openings['N'].append((R.x1 - WIN_X, WIN_W, WIN_Z0, WIN_Z1, 'window'))
R.openings['S'].append((DOOR_X - R.x0, DOOR_W, 0.0, 2.45, 'door'))
I.build_walls(R, M_WALL)
K.box("Floor", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.04), (0, 0, -0.02), M_FLOOR)
box("Ceiling", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.05), (0, 0, R.h + 0.025), M_WALL)
for k in range(6): box(f"Beam{k}", (R.x1 - R.x0, 0.16, 0.2), (0, R.y0 + 0.5 + k * 1.0, R.h - 0.1), M_BEAM)
I.moulding_runs(R, "Skirting", I.skirting_profile(0.14), 0.0, M_BEAM)
# window: deep reveal, frame, casement glass, sill; the louvred shutters inside, one leaf closed, one half open
wy = R.y1
box("WinSill", (WIN_W + 0.2, R.t + 0.12, 0.06), (WIN_X, wy + R.t / 2 - 0.06, WIN_Z0 - 0.03), M_BEAM)
for sx in (-1, 1): box(f"WinFrame{sx}", (0.07, 0.08, WIN_Z1 - WIN_Z0), (WIN_X + sx * (WIN_W / 2 - 0.035), wy + R.t * 0.6, (WIN_Z0 + WIN_Z1) / 2), M_SHUTTER)
box("WinHead", (WIN_W, 0.08, 0.07), (WIN_X, wy + R.t * 0.6, WIN_Z1 - 0.035), M_SHUTTER)
box("WinMullion", (0.05, 0.06, WIN_Z1 - WIN_Z0), (WIN_X, wy + R.t * 0.6, (WIN_Z0 + WIN_Z1) / 2), M_SHUTTER)
louvre_shutter("ShutterL", (WIN_X - WIN_W / 2, wy - 0.03, WIN_Z0), 0.0, WIN_W / 2, WIN_Z1 - WIN_Z0, 0.0, math.radians(-35), M_SHUTTER)
louvre_shutter("ShutterR", (WIN_X + WIN_W / 2, wy - 0.03, WIN_Z0), math.pi, WIN_W / 2, WIN_Z1 - WIN_Z0, -62.0, math.radians(35), M_SHUTTER)
# outside: the glare of the quay, the buildings across the square, the canal roads with ships' masts
box("Quay", (120, 80, 0.2), (0, 45, -0.6), M_OUTSIDE)
box("Canal", (300, 300, 0.1), (0, 230, -1.6), M_SEA)
for k in range(6):
    box(f"QuayHouse{k}", (rng.uniform(6, 12), 6, rng.uniform(5, 9)), (-40 + k * 15, 30 + rng.uniform(0, 4), 2.5), M_BUILD)
for k, (x, y, hgt) in enumerate(((-6, 95, 24), (8, 120, 30), (22, 140, 22), (-20, 160, 26))):
    tube(f"FarMast{k}", [Vector((x, y, -1.5)), Vector((x, y, hgt))], [0.35, 0.12], M_SPAR, sides=6)
    tube(f"FarYard{k}", [Vector((x - 6, y, hgt * 0.7)), Vector((x + 6, y, hgt * 0.7))], 0.12, M_SPAR, sides=5)
    box(f"FarHull{k}", (6, 34, 4), (x, y, -0.5), M_SPAR)
# the door, open inward against the wall
M_DOOR = I.mahogany("M_DoorWood", rough=(0.4, 0.6), coat=0.1)
dl = box("DoorLeaf", (DOOR_W - 0.06, 0.05, 2.38), (DOOR_X, R.y0 + 0.5, 1.2), M_DOOR, rot=(0, 0, math.radians(-82)))
dl.location = (DOOR_X - DOOR_W / 2 + 0.03, R.y0 + (DOOR_W - 0.06) / 2, 1.2)
for sx in (-1, 1): box(f"DoorCase{sx}", (0.1, 0.06, 2.5), (DOOR_X + sx * (DOOR_W / 2 + 0.04), R.y0 + 0.03, 1.25), M_BEAM)
box("DoorCaseHead", (DOOR_W + 0.28, 0.06, 0.12), (DOOR_X, R.y0 + 0.03, 2.5), M_BEAM)
box("Passage", (2.2, 2.4, 3.0), (DOOR_X, R.y0 - R.t - 1.2, 1.5), M_WALL)   # the dim passage behind the open door (its inside faces)

# ----------------------------------------------------------------------------- the consul's desk and its things
DK = Vector((WIN_X, 1.35, 0.0))
F = Frame((DK.x, DK.y), math.pi)        # the consul sits on the window side, facing the reader
F.box("DeskTop", (1.6, 0.85, 0.04), (0, 0, 0.76), M_MAHOG, bevel=0.006)
F.box("DeskLeather", (1.4, 0.65, 0.004), (0, 0, 0.782), M_LEATHER)
for sx in (-1, 1):
    F.box(f"Pedestal{sx}", (0.45, 0.78, 0.72), (sx * 0.56, 0, 0.37), M_MAHOG, bevel=0.006)
    for k in range(3): F.box(f"Drawer{sx}{k}", (0.38, 0.02, 0.18), (sx * 0.56, -0.4, 0.15 + k * 0.22), M_MAHOG, bevel=0.004)
    for k in range(3): cyl(f"Knob{sx}{k}", 0.012, 0.02, F.p(sx * 0.56, -0.415, 0.15 + k * 0.22), M_BRASS, verts=8, rot=(math.pi / 2, 0, F.yaw))
F.box("KneeBack", (0.67, 0.02, 0.5), (0, 0.35, 0.47), M_MAHOG)
top = 0.785
# inkstand: a brass tray with two cut-glass wells and a pen
F.box("InkTray", (0.30, 0.17, 0.015), (0.0, 0.2, top + 0.008), M_BRASS, bevel=0.004)
for sx in (-1, 1):
    lathe(f"InkWell{sx}", [(0.0, 0.0), (0.035, 0.0), (0.035, 0.05), (0.022, 0.06), (0.0, 0.065)], F.p(sx * 0.07, 0.2, top + 0.015), M_GLASS, steps=8)
    lathe(f"InkLid{sx}", [(0.0, 0.0), (0.024, 0.0), (0.02, 0.012), (0.0, 0.016)], F.p(sx * 0.07, 0.2, top + 0.078), M_BRASS, steps=8)
tube("Pen", [Vector(F.p(0.08, 0.12, top + 0.02)), Vector(F.p(-0.1, 0.1, top + 0.03))], 0.004, M_BENTWOOD, sides=5)
# the official seal: a turned ebony handle on a brass matrix
lathe("Seal", [(0.0, 0.0), (0.03, 0.0), (0.03, 0.012), (0.012, 0.03), (0.015, 0.07), (0.022, 0.1), (0.0, 0.11)], F.p(-0.42, -0.05, top), M_BRASS, steps=10)
# the passport, open for its visa, and the fee register
F.box("Passport", (0.22, 0.3, 0.003), (0.05, -0.14, top + 0.003), M_PAPER).rotation_euler.z += 0.12
F.box("RegisterL", (0.26, 0.36, 0.035), (0.42, 0.05, top + 0.018), M_PAPER).rotation_euler.z -= 0.05
F.box("RegisterR", (0.26, 0.36, 0.035), (0.68, 0.05, top + 0.018), M_PAPER).rotation_euler.z -= 0.05
F.box("RegisterCover", (0.54, 0.38, 0.01), (0.55, 0.05, top + 0.002), M_LEATHER).rotation_euler.z -= 0.05
F.box("Blotter", (0.45, 0.32, 0.012), (-0.25, -0.12, top + 0.006), M_LEATHER)
F.box("BlotSheet", (0.42, 0.29, 0.002), (-0.25, -0.12, top + 0.013), M_PAPER)
lathe("SandBox", [(0.0, 0.0), (0.03, 0.0), (0.032, 0.04), (0.025, 0.06), (0.0, 0.065)], F.p(-0.55, 0.22, top), M_BRASS, steps=10)
for k in range(5):    # a few papers held under a brass weight
    F.box(f"Paper{k}", (0.21, 0.29, 0.002), (-0.62 + rng.uniform(-0.02, 0.02), 0.08 + rng.uniform(-0.02, 0.02), top + 0.003 + k * 0.002), M_PAPER).rotation_euler.z += rng.uniform(-0.15, 0.15)
lathe("PaperWeight", [(0.0, 0.0), (0.04, 0.0), (0.03, 0.03), (0.0, 0.04)], F.p(-0.62, 0.08, top + 0.013), M_BRASS, steps=10)
# chairs: the consul's bentwood armchair behind the desk, two cane chairs before it
def bentwood(name, x, y, yaw, cane=True):
    Fc = Frame((x, y), yaw)
    lathe(f"{name}Seat", [(0.0, 0.44), (0.22, 0.44), (0.23, 0.47), (0.0, 0.47)], Fc.p(0, 0, 0), M_CANE if cane else M_BENTWOOD, steps=16)
    tube(f"{name}SeatRing", [Vector(Fc.p(math.cos(a) * 0.23, math.sin(a) * 0.23, 0.44)) for a in np.linspace(0, 2 * math.pi, 17)], 0.016, M_BENTWOOD, sides=6, caps=False)
    for (lx, ly) in ((-0.17, 0.15), (0.17, 0.15)):
        tube(f"{name}FLeg{lx}", [Vector(Fc.p(lx, ly, 0.45)), Vector(Fc.p(lx * 1.2, ly * 1.3, 0.0))], 0.016, M_BENTWOOD, sides=6)
    for lx in (-0.15, 0.15):
        tube(f"{name}BLeg{lx}", [Vector(Fc.p(lx * 1.3, -0.25, 0.0)), Vector(Fc.p(lx, -0.2, 0.45)), Vector(Fc.p(lx * 1.1, -0.26, 0.75)), Vector(Fc.p(lx * 0.9, -0.24, 0.95))], 0.016, M_BENTWOOD, sides=6)
    tube(f"{name}Back", [Vector(Fc.p(-0.14, -0.24, 0.95)), Vector(Fc.p(-0.2, -0.3, 0.82)), Vector(Fc.p(0, -0.33, 0.78)), Vector(Fc.p(0.2, -0.3, 0.82)), Vector(Fc.p(0.14, -0.24, 0.95))],
         0.014, M_BENTWOOD, sides=6)
    tube(f"{name}Hoop", [Vector(Fc.p(math.cos(a) * 0.2, math.sin(a) * 0.2, 0.2)) for a in np.linspace(0, 2 * math.pi, 13)], 0.01, M_BENTWOOD, sides=5, caps=False)
bentwood("ConsulChair", DK.x + 0.1, DK.y + 0.75, math.pi + 0.1, cane=False)
bentwood("ChairA", DK.x - 0.45, DK.y - 0.85, -0.25)
bentwood("ChairB", DK.x + 0.55, DK.y - 0.95, 0.35)
# ----------------------------------------------------------------------------- the walls: royal arms, chart, pigeon-holes, hat-stand, ensign
am = MB()
mb_quad(am, [Vector((WIN_X - 0.42, R.y1 - 0.03, 3.25 - 0.0)), Vector((WIN_X + 0.42, R.y1 - 0.03, 3.25)), Vector((WIN_X + 0.42, R.y1 - 0.03, 3.95)), Vector((WIN_X - 0.42, R.y1 - 0.03, 3.95))])
am.build("RoyalArms", M_ARMS, sway=False)
I.picture("Chart", R, 'E', 3.6, 1.75, 1.3, 0.9, M_FRAME, M_CHART)
# pigeon-holes on the west wall
PH = Frame((R.x0, 0.6), math.atan2(-1, 0))
PH.box("PigeonCase", (1.4, 0.36, 1.1), (0, 0.18, 1.55), M_MAHOG, bevel=0.005)
for i in range(7):
    for j in range(5):
        PH.box(f"Hole{i}{j}", (0.17, 0.02, 0.18), (-0.6 + i * 0.2, 0.37, 1.1 + j * 0.2), M_BEAM)
        if rng.random() < 0.55: PH.box(f"Docket{i}{j}", (0.14, 0.03, 0.08), (-0.6 + i * 0.2, 0.33, 1.06 + j * 0.2), M_PAPER)
PH.box("PigeonDesk", (1.4, 0.5, 0.04), (0, 0.25, 0.95), M_MAHOG)
for sx in (-1, 1): PH.box(f"PigeonLeg{sx}", (0.06, 0.45, 0.93), (sx * 0.66, 0.25, 0.47), M_MAHOG)
# the hat-stand by the door, the ensign furled on its staff in Fix's corner
lathe("HatStand", [(0.0, 0.0), (0.22, 0.0), (0.2, 0.03), (0.03, 0.06), (0.025, 1.75), (0.04, 1.8), (0.0, 1.85)], (DOOR_X - 0.85, R.y0 + 0.45, 0.0), M_BENTWOOD, steps=10)
for k in range(4):
    a = k * math.pi / 2 + 0.4
    tube(f"HatHook{k}", [Vector((DOOR_X - 0.85, R.y0 + 0.45, 1.7)), Vector((DOOR_X - 0.85 + math.cos(a) * 0.15, R.y0 + 0.45 + math.sin(a) * 0.15, 1.78))], 0.01, M_BENTWOOD, sides=5)
lathe("HatOnStand", [(0.0, 0.0), (0.16, 0.0), (0.16, 0.01), (0.09, 0.012), (0.085, 0.14), (0.0, 0.145)], (DOOR_X - 0.85, R.y0 + 0.45, 1.81), M_ARMSBOARD, steps=14)
FC = Vector((R.x1 - 0.35, R.y0 + 0.4, 0))
tube("EnsignStaff", [FC, FC + Vector((-0.25, 0.1, 2.6))], 0.022, M_BENTWOOD, sides=6)
fm = MB()
for k in range(9):          # the furled flag wrapped round the staff, hanging in folds
    t = k / 8; c = FC + Vector((-0.25, 0.1, 2.6)) * (0.62 + 0.36 * t)
    for j in range(8):
        a0 = 2 * math.pi * j / 8; a1 = 2 * math.pi * (j + 1) / 8; rr = 0.06 + 0.03 * math.sin(k * 1.3) + 0.04 * (1 - t)
        if k < 8:
            c2 = FC + Vector((-0.25, 0.1, 2.6)) * (0.62 + 0.36 * (k + 1) / 8); rr2 = 0.06 + 0.03 * math.sin((k + 1) * 1.3) + 0.04 * (1 - (k + 1) / 8)
            vs = [fm.vert(c + Vector((math.cos(a0) * rr, math.sin(a0) * rr, 0)), (j / 8, t), 0.0), fm.vert(c + Vector((math.cos(a1) * rr, math.sin(a1) * rr, 0)), ((j + 1) / 8, t), 0.0),
                  fm.vert(c2 + Vector((math.cos(a1) * rr2, math.sin(a1) * rr2, 0)), ((j + 1) / 8, t), 0.1), fm.vert(c2 + Vector((math.cos(a0) * rr2, math.sin(a0) * rr2, 0)), (j / 8, t), 0.1)]
            fm.face(*vs)
fm.build("cloth.flag.ensign", M_RED)
# a straw mat at the door, a waste basket
box("DoorMat", (0.9, 0.6, 0.012), (DOOR_X, R.y0 + 0.75, 0.006), M_CANE)
lathe("Basket", [(0.0, 0.0), (0.13, 0.0), (0.16, 0.32), (0.0, 0.32)], (DK.x + 0.95, DK.y + 0.3, 0.0), M_CANE, steps=12)

# ----------------------------------------------------------------------------- light and world
S.world(SUN_DIR, sun_energy=6.0, sun_col=(1.0, 0.95, 0.86), sun_angle=0.6,
        sky_cols=(srgb((0.70, 0.62, 0.48)), srgb((0.86, 0.86, 0.84)), srgb((0.36, 0.56, 0.88))), sky_strength=1.6)
SKY = S.sky_dome(M_SKY, radius=600.0)
light_obj("Lamp.windowfill", 'AREA', 60.0, (0.96, 0.95, 1.0), (WIN_X, R.y1 - 0.15, 2.0), direction=(0, -1, -0.2), size=1.3, size_y=2.2, shape='RECTANGLE')
eye, fwd = S.reader(tuple(READER), YAW)
anchor("scene.centre", tuple(DK))
anchor("desk", tuple(DK + Vector((0, 0, 0.78))))
anchor("fix.corner", (R.x1 - 0.5, R.y0 + 0.5, 0.0))
sound("crowd", "quay", (WIN_X, R.y1 + 3.0, 1.5))
page = S.page_preview(eye, fwd)
cams = S.view_cams(eye, YAW, extra=[
    ("Cam_Page", eye, eye + fwd * 10 + Vector((0, 0, -1.2)), 17),
    ("Cam_Desk", Vector((DK.x - 0.4, DK.y - 1.1, 1.45)), tuple(DK + Vector((0, 0, 0.78))), 30),
    ("Cam_Corner", Vector((R.x1 - 0.5, R.y0 + 0.5, 1.6)), tuple(DK + Vector((-0.8, 0.0, 1.1))), 20),
])
S.finish(ARGS, cams, "suez_consulate.gltf", page=page, default_exposure=0.0,
         keep_names={"M_RoyalArms": "MESH_RoyalArms", "M_EnsignRed": "cloth.flag.ensign"},
         size_for={"M_Whitewash": (2048, 128, 1024), "M_FloorTiles": (2048, 256, 1024), "M_DarkBeams": (512, 64, 256), "M_Mahogany": (1024, 256, 512),
                   "M_ShutterPaint": (512, 64, 256), "M_GreenLeather": (256, 64, 128), "M_Chart": (512, 64), "M_Paper": (256, 64),
                   "M_Cane": (512, 128, 256), "M_Bentwood": (256, 64, 128), "M_QuayGlare": (256,), "M_QuayBuildings": (256,), "M_CanalWater": (128,),
                   "M_SkyDome": (1024,), "M_DoorWood": (512, 128, 256)},
         default_size=(256, 64, 128), no_shadow={"M_SkyDome"})
