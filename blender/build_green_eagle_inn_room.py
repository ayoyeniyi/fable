"""
Fable scene room: The show room at the Green Eagle (Gulliver's Travels, Part II, Chapter II) - green-eagle-inn-room.

"My master ... hired the crier ... at the sign of the Green Eagle ... I was placed upon a table in the largest room of
the inn, which might be near three hundred feet square. My little nurse stood on a low stool close to the table, to
take care of me, and direct what I should do." "I drank their health, I drew out my hanger, and flourished with it
after the manner of fencers in England. My nurse gave me a part of a straw, which I exercised as a pike" "a thimble
filled with liquor, which Glumdalclitch had given me for a cup" "a hazel nut ... almost as large as a small pumpkin"
"benches set round the table at such a distance as to put me out of everybody's reach" "a box ... close on every
side, with a little door ... and a few gimlet holes to let in air"

The reader is Gulliver-size on the giant table, where everything of Brobdingnag is twelve times ours: the worn plank
top is a floor of boards three metres wide with finger-wide cracks; on it the thimble cup still wet with liquor, the
piece of straw, the hazel nut where it fell, a crumb of bread, and Gulliver's travelling box with its little door and
gimlet holes, its quilt showing; beyond the table's edge the drop to the floor nine metres below, Glumdalclitch's low
stool close by the table, the benches set round at a distance, and the great dim room: dark beams, tall leaded
windows, a hearth with a fire and smoke hanging in the light. The giants (the crowd, Glumdalclitch) are left out.

Light: a summer day, daylight from the tall leaded windows on the left, slightly smoky; the fire's glow far off.

Axes: metres (the reader's), +Z up; the table top is at z = 0, the room's floor at z = -9.0. The reader on the
tabletop facing +Y, toward the stool and the benches beyond.

Run headless:
  blender -b -P blender/build_green_eagle_inn_room.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_green_eagle_inn_room.py -- --cpu --render --samples 48 --res 1024 --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b4 as S
from scene_kit_b4 import (K, new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, lathe, tube, MB, anchor, sound, light_obj, smoothstep, srgb,
                          mb_box, mb_quad)

ARGS = S.setup("green-eagle-inn-room", 1703, "GreenEagleInnRoom", default_samples=48)
scene = K.scene
rng = random.Random(1703)
EYE = S.EYE
X12 = 12.0
FLOOR = -9.0                        # the giants' table is 75 cm high
TX0, TX1, TY0, TY1 = -6.5, 7.5, -12.0, 6.0          # the table top
ROOM = (-45.0, 45.0, -45.0, 45.0); CEIL = 36.0
SUN_DIR = Vector((-0.75, 0.25, 0.6)).normalized()   # toward the sun: through the windows on the west (left) wall

# ----------------------------------------------------------------------------- materials
def table_mat(name):
    """The table top at twelve times: boards ~3 m wide running along y, scrubbed pale in the middle, darkened and
    greasy toward the edges, deep grain, knots like dinner plates, finger-wide cracks between the boards, ring stains."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0)); s = sep_xyz(nt, co, (-2200, 0))
    px = math_(nt, 'DIVIDE', math_(nt, 'ADD', s.outputs["X"], 0.4), 3.0, (-2000, 200))
    fr = math_(nt, 'FRACT', px, None, (-1850, 200))
    crack = maprange(nt, fr, 0.0, 0.012, 1, 0, (-1700, 200))
    plank = node(nt, "ShaderNodeMath", (-1850, 400), operation='FLOOR'); nt.links.new(px, plank.inputs[0])
    cv = node(nt, "ShaderNodeCombineXYZ", (-1650, 600)); nt.links.new(plank.outputs[0], cv.inputs["X"])
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1500, 600)); wn.noise_dimensions = '3D'; nt.links.new(cv.outputs[0], wn.inputs["Vector"])
    gm = node(nt, "ShaderNodeMapping", (-1900, -300)); gm.inputs["Scale"].default_value = (0.9, 0.05, 0.9); nt.links.new(co, gm.inputs["Vector"])
    wave = node(nt, "ShaderNodeTexWave", (-1600, -300)); wave.bands_direction = 'X'; wave.inputs["Scale"].default_value = 3.0
    wave.inputs["Distortion"].default_value = 14.0; wave.inputs["Detail"].default_value = 4.0; nt.links.new(gm.outputs["Vector"], wave.inputs["Vector"])
    fine = noise_(nt, gm.outputs["Vector"], 40.0, 5, 0.6, loc=(-1600, -600))
    tone = math_(nt, 'ADD', math_(nt, 'MULTIPLY', wn.outputs["Value"], 0.55), math_(nt, 'MULTIPLY', wave.outputs["Fac"], 0.45), (-1300, 0))
    col = ramp(nt, [(0.0, c4(srgb((0.44, 0.34, 0.22)))), (0.45, c4(srgb((0.60, 0.49, 0.34)))), (0.75, c4(srgb((0.70, 0.60, 0.44)))), (1.0, c4(srgb((0.52, 0.42, 0.29))))], (-1100, 0))
    nt.links.new(tone, col.inputs["Fac"])
    c = col.outputs["Color"]
    edge = maprange(nt, math_(nt, 'MINIMUM', math_(nt, 'MINIMUM', math_(nt, 'SUBTRACT', s.outputs["X"], TX0), math_(nt, 'SUBTRACT', TX1, s.outputs["X"])),
                                 math_(nt, 'MINIMUM', math_(nt, 'SUBTRACT', s.outputs["Y"], TY0), math_(nt, 'SUBTRACT', TY1, s.outputs["Y"]))), 0.0, 3.0, 0.45, 0.0, (-1100, 400))
    c = mix_rgb(nt, 'MULTIPLY', edge, c, c4(srgb((0.45, 0.38, 0.30))), (-800, 0))
    rings = voronoi_(nt, co, 0.12, 'DISTANCE_TO_EDGE', (-1300, -900))
    ring = math_(nt, 'MULTIPLY', maprange(nt, rings.outputs["Distance"], 0.0, 0.015, 1, 0, (-1100, -900)), maprange(nt, noise_(nt, co, 0.2, 2, 0.5, loc=(-1300, -1100)).outputs["Fac"], 0.55, 0.6, 0, 0.5, (-1100, -1100)), (-900, -950))
    c = mix_rgb(nt, 'MULTIPLY', ring, c, c4(srgb((0.45, 0.35, 0.25))), (-600, 0))
    c = mix_rgb(nt, 'MIX', crack, c, c4(srgb((0.05, 0.04, 0.03))), (-400, 0))
    nt.links.new(c, b.inputs["Base Color"])
    nt.links.new(maprange(nt, edge, 0, 0.45, 0.8, 0.45, (-400, -300)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'SUBTRACT', math_(nt, 'ADD', math_(nt, 'MULTIPLY', wave.outputs["Fac"], 0.2), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.3)), crack, (-300, -600)), 0.3, 0.02, (0, -600))
    return m


M_TABLE = table_mat("M_TableTop")
M_OAK = noisy("M_DarkOak", [srgb((0.18, 0.12, 0.08)), srgb((0.24, 0.17, 0.11)), srgb((0.14, 0.10, 0.07))], scale=0.3, rough=(0.6, 0.85), bump=0.3, bump_dist=0.05, stretch=(4, 4, 0.2))
M_BENCH = noisy("M_BenchWood", [srgb((0.32, 0.24, 0.16)), srgb((0.40, 0.31, 0.21)), srgb((0.26, 0.19, 0.13))], scale=0.3, rough=(0.6, 0.85), bump=0.3, bump_dist=0.04, stretch=(0.2, 4, 4))
M_FLOOR = noisy("M_InnFloor", [srgb((0.26, 0.20, 0.14)), srgb((0.32, 0.25, 0.18)), srgb((0.20, 0.16, 0.11))], scale=0.06, rough=0.8, bump=0.2, bump_dist=0.1, stretch=(0.2, 4, 1))
M_PLASTER = noisy("M_Plaster", [srgb((0.72, 0.66, 0.54)), srgb((0.64, 0.58, 0.47)), srgb((0.78, 0.72, 0.60))], scale=0.08, rough=0.9, bump=0.2, bump_dist=0.2)
M_SILVER = noisy("M_Thimble", [srgb((0.72, 0.70, 0.66)), srgb((0.60, 0.58, 0.55))], scale=3.0, rough=0.3, metallic=1.0, bump=0.4)
M_LIQUOR = plain("M_Liquor", srgb((0.32, 0.14, 0.05)), rough=0.05)
M_STRAW = noisy("M_Straw", [srgb((0.80, 0.68, 0.40)), srgb((0.72, 0.60, 0.34)), srgb((0.86, 0.76, 0.50))], scale=2.0, rough=0.5, bump=0.3, stretch=(0.3, 0.3, 8))
M_NUT = noisy("M_HazelShell", [srgb((0.46, 0.28, 0.14)), srgb((0.56, 0.36, 0.18)), srgb((0.36, 0.22, 0.10))], scale=3.0, rough=0.4, bump=0.3, stretch=(1, 1, 6))
M_NUTCAP = noisy("M_HazelCap", [srgb((0.62, 0.52, 0.36)), srgb((0.54, 0.44, 0.30))], scale=6.0, rough=0.8, bump=0.6)
M_BREAD = noisy("M_Crumb", [srgb((0.80, 0.68, 0.46)), srgb((0.70, 0.58, 0.38))], scale=4.0, rough=0.9, bump=0.9, bump_dist=0.05)
M_CRUST = noisy("M_Crust", [srgb((0.46, 0.28, 0.12)), srgb((0.56, 0.36, 0.16))], scale=6.0, rough=0.6, bump=0.4)
M_BOX = noisy("M_BoxWood", [srgb((0.52, 0.40, 0.26)), srgb((0.60, 0.48, 0.32)), srgb((0.44, 0.34, 0.22))], scale=2.0, rough=0.7, bump=0.2, stretch=(4, 0.3, 4))
M_QUILT = noisy("M_Quilt", [srgb((0.70, 0.40, 0.36)), srgb((0.80, 0.70, 0.58)), srgb((0.60, 0.32, 0.30))], scale=12.0, rough=0.9, bump=0.5)
M_IRON = noisy("M_Iron", [srgb((0.08, 0.07, 0.06)), srgb((0.14, 0.10, 0.07))], scale=1.0, rough=0.6, metallic=0.5)
M_EMBERS = plain("M_Embers", srgb((0.9, 0.35, 0.08)), rough=0.9, emission=(1.0, 0.36, 0.08), strength=4.0)
M_SOOT = plain("M_Soot", (0.02, 0.018, 0.016), rough=0.95)
M_GLASS = noisy("M_LeadedLight", [srgb((0.92, 0.94, 0.90)), srgb((0.84, 0.88, 0.82))], scale=0.5, rough=0.2, bump=0.0)
M_GLASS.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = c4(srgb((0.95, 0.96, 0.92)))
M_GLASS.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 1.2
M_SKY = S.sky_mat(zenith=srgb((0.40, 0.56, 0.80)), horizon=srgb((0.86, 0.86, 0.82)), ground=srgb((0.40, 0.42, 0.30)), sun_dir=SUN_DIR, clouds=0.3, strength=1.0)

# ----------------------------------------------------------------------------- the table: top, edge thickness, legs, frame
print("table ...", flush=True)
tt = MB()
NX, NY = 28, 36
rows = [[tt.vert(Vector((TX0 + (TX1 - TX0) * i / NX, TY0 + (TY1 - TY0) * j / NY,
                         0.03 * noise.noise(Vector((i * 0.4, j * 0.4, 1.0))) - 0.04 * (abs(((TX0 + (TX1 - TX0) * i / NX + 0.4) / 3.0) % 1.0 - 0.5) < 0.02))), (i, j)) for i in range(NX + 1)] for j in range(NY + 1)]
for j in range(NY):
    for i in range(NX): tt.face(rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i])
tt.build("TableTop", M_TABLE, sway=False)
TH = 0.5      # the top is 4 cm thick at their scale
box("TableEdgeN", (TX1 - TX0, 0.25, TH), ((TX0 + TX1) / 2, TY1 - 0.125, -TH / 2), M_OAK)
box("TableEdgeS", (TX1 - TX0, 0.25, TH), ((TX0 + TX1) / 2, TY0 + 0.125, -TH / 2), M_OAK)
box("TableEdgeE", (0.25, TY1 - TY0, TH), (TX1 - 0.125, (TY0 + TY1) / 2, -TH / 2), M_OAK)
box("TableEdgeW", (0.25, TY1 - TY0, TH), (TX0 + 0.125, (TY0 + TY1) / 2, -TH / 2), M_OAK)
box("TableUnder", (TX1 - TX0, TY1 - TY0, 0.1), ((TX0 + TX1) / 2, (TY0 + TY1) / 2, -TH), M_OAK)
for (x, y) in ((TX0 + 1.2, TY0 + 1.2), (TX1 - 1.2, TY0 + 1.2), (TX0 + 1.2, TY1 - 1.2), (TX1 - 1.2, TY1 - 1.2)):
    box(f"TableLeg{x}{y}", (1.1, 1.1, -FLOOR - TH), (x, y, (FLOOR - TH) / 2), M_OAK)
for x in (TX0 + 1.2, TX1 - 1.2):
    box(f"Stretcher{x}", (0.6, TY1 - TY0 - 2.4, 0.8), (x, (TY0 + TY1) / 2, FLOOR + 1.6), M_OAK)
box("Apron", (TX1 - TX0 - 1.6, TY1 - TY0 - 1.6, 1.4), ((TX0 + TX1) / 2, (TY0 + TY1) / 2, -TH - 0.7), M_OAK)

# ----------------------------------------------------------------------------- on the table: the thimble cup, the straw pike, the hazel nut, a crumb, the box
print("props ...", flush=True)
TB = Vector((1.9, 2.4, 0.0))
prof = [(0.0, 0.0), (0.105, 0.0), (0.105, 0.02), (0.112, 0.03), (0.105, 0.04), (0.098, 0.20), (0.075, 0.25), (0.04, 0.265), (0.0, 0.27)]
th = lathe("Thimble", [(r * 1.0, z) for r, z in prof], (TB.x, TB.y, 0.0), M_SILVER, steps=28)
th.rotation_euler = (math.pi, 0, 0); th.location.z = 0.27      # standing open end up as a cup
lathe("ThimbleLiquor", [(0.0, 0.0), (0.092, 0.0)], (TB.x, TB.y, 0.23), M_LIQUOR, steps=24)
lathe("Spill", [(0.0, 0.0), (0.16, 0.0)], (TB.x + 0.25, TB.y - 0.1, 0.004), M_LIQUOR, steps=16).scale = (1.4, 0.8, 1.0)
tube("Straw", [Vector((-1.2, 3.6, 0.03)), Vector((0.1, 3.2, 0.03)), Vector((0.9, 2.95, 0.035))], 0.026, M_STRAW, sides=10)
tube("StrawNode", [Vector((-0.42, 3.37, 0.03)), Vector((-0.38, 3.36, 0.03))], 0.031, M_STRAW, sides=10)
NUT = Vector((-2.4, 6.8 - 2.2, 0.0))
nut = K.sphere("HazelNut", 0.12, (NUT.x, NUT.y, 0.115), M_NUT, seg=20, scale=(1.0, 0.95, 1.12))
nut.rotation_euler = (0.4, 1.2, 0.2)
lathe("NutBase", [(0.0, 0.0), (0.075, 0.0), (0.072, 0.012), (0.0, 0.014)], (NUT.x - 0.105, NUT.y + 0.02, 0.06), M_NUTCAP, steps=16).rotation_euler = (0, -1.2, 0)
K.sphere("Crumb", 0.11, (3.4, -1.0, 0.07), M_BREAD, seg=10, scale=(1.3, 1.0, 0.6))
K.sphere("CrumbCrust", 0.07, (3.55, -0.92, 0.08), M_CRUST, seg=8, scale=(1.2, 0.9, 0.5))
# Gulliver's travelling box: made to his size, close on every side, a little door, gimlet holes, the quilt within
BX = Vector((-3.6, -3.2, 0.0)); BW, BD, BH = 1.5, 1.2, 1.45
bb = MB()
for (c, size) in (((BX.x, BX.y, 0.04), (BW, BD, 0.08)), ((BX.x, BX.y, BH - 0.04), (BW, BD, 0.08)), ((BX.x - BW / 2 + 0.03, BX.y, BH / 2), (0.06, BD, BH)),
                  ((BX.x + BW / 2 - 0.03, BX.y, BH / 2), (0.06, BD, BH)), ((BX.x, BX.y - BD / 2 + 0.03, BH / 2), (BW, 0.06, BH))):
    mb_box(bb, Vector(c), size)
# the front (+Y) with the little door standing open
mb_box(bb, Vector((BX.x - 0.45, BX.y + BD / 2 - 0.03, BH / 2)), (0.6, 0.06, BH))
mb_box(bb, Vector((BX.x + 0.6, BX.y + BD / 2 - 0.03, BH / 2)), (0.3, 0.06, BH))
mb_box(bb, Vector((BX.x + 0.15, BX.y + BD / 2 - 0.03, BH - 0.18)), (0.6, 0.06, 0.36))
bb.build("TravelBox", M_BOX, sway=False)
door = box("BoxDoor", (0.58, 0.04, 1.05), (BX.x + 0.15 + 0.29 * 0, BX.y + BD / 2 + 0.3, 0.55), M_BOX)
door.rotation_euler = (0, 0, math.radians(70)); door.location = (BX.x + 0.45 + 0.1, BX.y + BD / 2 + 0.27, 0.55)
box("BoxRing", (0.05, 0.05, 0.3), (BX.x, BX.y, BH + 0.15), M_IRON)
for k in range(6):           # gimlet holes along the sides
    for sx in (-1, 1):
        cyl(f"Gimlet{k}{sx}", 0.025, 0.07, (BX.x + sx * (BW / 2 - 0.02), BX.y - 0.45 + k * 0.18, 1.1), M_SOOT, verts=8, rot=(0, math.pi / 2, 0))
box("BoxQuilt", (BW - 0.2, BD - 0.2, 0.18), (BX.x, BX.y, 0.17), M_QUILT, bevel=0.06)
# a giant's candlestick at the far end of the table (unlit by day) and a pewter dish
lathe("Candlestick", [(0.0, 0.0), (0.75, 0.0), (0.7, 0.12), (0.2, 0.3), (0.16, 1.6), (0.28, 1.75), (0.3, 1.82), (0.0, 1.85)], (5.6, TY1 - 1.6, 0.0), M_IRON, steps=20)
lathe("Candle", [(0.0, 1.82), (0.16, 1.82), (0.16, 3.6), (0.12, 3.68), (0.0, 3.7)], (5.6, TY1 - 1.6, 0.0), plain("M_Tallow", srgb((0.86, 0.80, 0.62)), rough=0.6), steps=14)
lathe("PewterDish", [(0.0, 0.0), (1.4, 0.0), (1.7, 0.14), (2.2, 0.22), (2.25, 0.26), (2.15, 0.26), (1.65, 0.18), (1.35, 0.05), (0.0, 0.05)], (-3.6, TY1 - 1.0, 0.0), noisy("M_Pewter", [srgb((0.50, 0.50, 0.48)), srgb((0.42, 0.42, 0.40))], scale=1.0, rough=0.35, metallic=0.8), steps=28)

# ----------------------------------------------------------------------------- the room: floor, walls with tall leaded windows, beams, hearth; the stool and the benches
print("room ...", flush=True)
x0, x1, y0, y1 = ROOM
box("RoomFloor", (x1 - x0, y1 - y0, 0.5), (0, 0, FLOOR - 0.25), M_FLOOR)
box("RoomCeiling", (x1 - x0, y1 - y0, 0.5), (0, 0, FLOOR + CEIL + 0.25), M_PLASTER)
for k in range(9): box(f"Beam{k}", (x1 - x0, 3.6, 4.2), (0, y0 + 5 + k * 10.0, FLOOR + CEIL - 2.1), M_OAK)
box("WallE", (1.0, y1 - y0, CEIL), (x1 + 0.5, 0, FLOOR + CEIL / 2), M_PLASTER)
box("WallN", (x1 - x0, 1.0, CEIL), (0, y1 + 0.5, FLOOR + CEIL / 2), M_PLASTER)
box("WallS", (x1 - x0, 1.0, CEIL), (0, y0 - 0.5, FLOOR + CEIL / 2), M_PLASTER)
# the west wall: piers between three tall windows of leaded lights
WINS = [(-26.0, 12.0), (0.0, 12.0), (26.0, 12.0)]
cuts = [y0] + [v for (c, w) in WINS for v in (c - w / 2, c + w / 2)] + [y1]
for i in range(0, len(cuts), 2):
    box(f"WallWPier{i}", (1.0, cuts[i + 1] - cuts[i], CEIL), (x0 - 0.5, (cuts[i] + cuts[i + 1]) / 2, FLOOR + CEIL / 2), M_PLASTER)
lead = MB()
for (c, w) in WINS:
    box(f"WinSill{c}", (2.0, w, 6.0), (x0 - 0.5, c, FLOOR + 3.0), M_PLASTER)
    box(f"WinHead{c}", (2.0, w, 4.0), (x0 - 0.5, c, FLOOR + CEIL - 2.0), M_PLASTER)
    box(f"WinGlass{c}", (0.2, w, CEIL - 10.0), (x0 - 0.3, c, FLOOR + 6.0 + (CEIL - 10.0) / 2), M_GLASS)
    for k in range(1, 4): mb_box(lead, Vector((x0 + 0.0, c - w / 2 + k * w / 4, FLOOR + 6.0 + (CEIL - 10.0) / 2)), (0.6, 0.5, CEIL - 10.0))     # mullions
    for k in range(1, 6): mb_box(lead, Vector((x0 + 0.0, c, FLOOR + 6.0 + k * (CEIL - 10.0) / 6)), (0.5, w, 0.45))                               # transoms
    # the leading: a diamond lattice of cames
    for k in range(-14, 15):
        for sg in (-1, 1):
            p0 = Vector((x0 + 0.1, c + k * 1.0, FLOOR + 6.0)); L = (CEIL - 10.0)
            p1 = p0 + Vector((0, sg * L * 0.5, L))
            # clip to the window opening
            ya, yb = p0.y, p1.y
            lo, hi = c - w / 2, c + w / 2
            ts = sorted([(lo - ya) / (yb - ya), (hi - ya) / (yb - ya)])
            t0, t1 = max(0.0, ts[0]), min(1.0, ts[1])
            if t1 <= t0: continue
            q0, q1 = p0.lerp(p1, t0), p0.lerp(p1, t1)
            d = (q1 - q0); u = Vector((0.0, -d.z, d.y)).normalized() * 0.06
            mb_quad(lead, [q0 - u, q0 + u, q1 + u, q1 - u])
lead.build("WindowLeads", M_IRON, sway=False)
# timber framing on the plastered walls: posts and a rail (their oak, a foot square: 3.6 m to us)
for k in range(8):
    y = y0 + 6 + k * 11.5
    box(f"PostE{k}", (1.2, 3.0, CEIL), (x1 - 0.6, y, FLOOR + CEIL / 2), M_OAK)
    x = x0 + 6 + k * 11.5
    box(f"PostN{k}", (3.0, 1.2, CEIL), (x, y1 - 0.6, FLOOR + CEIL / 2), M_OAK)
    box(f"PostS{k}", (3.0, 1.2, CEIL), (x, y0 + 0.6, FLOOR + CEIL / 2), M_OAK)
for (nm, c, sz) in (("RailE", (x1 - 0.7, 0, FLOOR + 14.0), (1.0, y1 - y0, 2.2)), ("RailN", (0, y1 - 0.7, FLOOR + 14.0), (x1 - x0, 1.0, 2.2)), ("RailS", (0, y0 + 0.7, FLOOR + 14.0), (x1 - x0, 1.0, 2.2))):
    box(nm, sz, c, M_OAK)

# the hearth on the east wall: a great opening, firedogs, logs, the fire
HZ = Vector((x1 - 1.0, -8.0, FLOOR))
box("HearthBack", (1.2, 16.0, 14.0), (x1 - 0.6, HZ.y, FLOOR + 7.0), M_SOOT)
for sy in (-1, 1): box(f"HearthJamb{sy}", (3.0, 2.4, 14.0), (x1 - 1.5, HZ.y + sy * 9.2, FLOOR + 7.0), M_PLASTER)
box("HearthLintel", (3.6, 21.0, 3.0), (x1 - 1.8, HZ.y, FLOOR + 15.0), M_OAK)
box("HearthHood", (5.0, 21.0, 16.0), (x1 - 2.5, HZ.y, FLOOR + 24.5), M_PLASTER)
for k in range(4):
    tube(f"Log{k}", [Vector((x1 - 3.0 - k * 0.6, HZ.y - 4.0, FLOOR + 1.0 + k * 0.4)), Vector((x1 - 3.2, HZ.y + 4.0, FLOOR + 1.2))], 0.9, M_OAK, sides=8)
for k in range(10): K.sphere(f"Embers{k}", rng.uniform(0.6, 1.1), (x1 - 3.2 + rng.uniform(-1, 1), HZ.y + rng.uniform(-4, 4), FLOOR + 0.5), M_EMBERS, seg=6, scale=(1.3, 1.3, 0.5))
FIRE = Vector((x1 - 3.2, HZ.y, FLOOR + 1.0))
# Glumdalclitch's low stool close by the table (her standing place), and the benches round at a distance
ST = Vector((1.0, TY1 + 3.6, FLOOR))
box("StoolTop", (4.4, 3.0, 0.5), (ST.x, ST.y, FLOOR + 3.4), M_BENCH)
for sx in (-1, 1):
    for sy in (-1, 1): box(f"StoolLeg{sx}{sy}", (0.5, 0.5, 3.2), (ST.x + sx * 1.7, ST.y + sy * 1.1, FLOOR + 1.6), M_BENCH, rot=(sy * 0.08, -sx * 0.08, 0))
def bench(cx, cy, yaw, L=26.0):
    Rm = Matrix.Rotation(yaw, 3, 'Z')
    def P(x, y, z): return Vector((cx, cy, FLOOR)) + Rm @ Vector((x, y, z))
    box(f"BenchTop{cx}{cy}", (L, 3.6, 0.6), tuple(P(0, 0, 5.4)), M_BENCH, rot=(0, 0, yaw))
    for k in range(4):
        x = -L / 2 + 1.5 + k * (L - 3.0) / 3
        box(f"BenchLeg{cx}{cy}{k}", (0.6, 3.0, 5.2), tuple(P(x, 0, 2.6)), M_BENCH, rot=(0, 0, yaw))
for (cx, cy, yaw) in ((0.0, 28.0, 0.0), (-26.0, 0.0, math.pi / 2), (28.0, -2.0, math.pi / 2), (0.0, -34.0, 0.0), (-22.0, 26.0, 0.6), (24.0, 24.0, -0.6)):
    bench(cx, cy, yaw)
# hats and a cloak left on a bench, a pot of ale on the floor (their size)
lathe("Tankard", [(0.0, 0.0), (1.1, 0.0), (1.0, 2.2), (1.05, 2.3), (0.0, 2.25)], (-6.0, 28.0, FLOOR + 5.7), noisy("M_Pewter2", [srgb((0.46, 0.46, 0.44)), srgb((0.38, 0.38, 0.36))], scale=1.0, rough=0.35, metallic=0.8), steps=18)
hat = lathe("Hat", [(0.0, 0.0), (3.2, 0.0), (3.2, 0.1), (1.8, 0.15), (1.7, 1.6), (0.0, 1.7)], (8.0, 28.0, FLOOR + 5.7), noisy("M_Felt", [srgb((0.14, 0.13, 0.12)), srgb((0.18, 0.16, 0.14))], scale=2.0, rough=0.9, bump=0.2), steps=20)

# ----------------------------------------------------------------------------- light: daylight through the windows (sun + window glow), the hearth, smoke haze
S.world(SUN_DIR, sun_energy=2.5, sun_col=(1.0, 0.94, 0.82), sun_angle=1.0,
        sky_cols=(srgb((0.40, 0.42, 0.30)), srgb((0.82, 0.84, 0.86)), srgb((0.40, 0.56, 0.82))), sky_strength=1.2)
SKY = S.sky_dome(M_SKY, radius=300.0)
for (c, w) in WINS:
    light_obj(f"Lamp.window{c:.0f}", 'AREA', 22000.0, (0.95, 0.96, 1.0), (x0 + 1.0, c, FLOOR + 6.0 + (CEIL - 10.0) / 2), direction=(1, 0, -0.15), size=w, size_y=CEIL - 10.0, shape='RECTANGLE')
light_obj("Lamp.hearth", 'POINT', 40000.0, (1.0, 0.45, 0.16), tuple(FIRE + Vector((-4.0, 0, 3.0))), shadow_soft_size=3.0)
eye, fwd = S.reader((0.0, -1.0, 0.0), 0.0)
anchor("scene.centre", (0.0, 1.0, 0.0))
anchor("stool", tuple(ST))
S.fx("fire", "hearth", tuple(FIRE), 3.0)
sound("crowd", "benches_n", (0.0, 28.0, FLOOR + 10.0))
sound("crowd", "benches_w", (-26.0, 0.0, FLOOR + 10.0))
sound("crowd", "benches_e", (28.0, -2.0, FLOOR + 10.0))
sound("fire", "hearth", tuple(FIRE + Vector((-2.0, 0, 2.0))))
page = S.page_preview(eye, fwd)
cams = S.view_cams(eye, 0.0, extra=[
    ("Cam_Page", eye, eye + fwd * 10 + Vector((0, 0, -1.2)), 17),
    ("Cam_Props", Vector((0.8, 0.4, 1.0)), Vector((0.0, 3.2, 0.1)), 24),
    ("Cam_Box", Vector((-1.5, -1.2, 1.3)), tuple(BX + Vector((0, 0, 0.7))), 24),
    ("Cam_Edge", Vector((1.0, TY1 - 2.0, 1.55)), tuple(ST + Vector((0, 0, 3.4))), 20),
    ("Cam_Room", eye, Vector((-40.0, 10.0, 5.0)), 17),
])
S.finish(ARGS, cams, "green_eagle_inn_room.gltf", page=page,
         keep_names={"M_Embers": "MESH_Embers", "M_LeadedLight": "far.windows"},
         size_for={"M_TableTop": (2048, 256, 1024), "M_DarkOak": (1024, 128, 512), "M_BenchWood": (1024, 128, 512), "M_InnFloor": (1024, 128, 512),
                   "M_Plaster": (1024, 128, 512), "M_Thimble": (512, 128, 256), "M_Straw": (256, 64, 128), "M_HazelShell": (256, 64, 128),
                   "M_BoxWood": (512, 64, 256), "M_Quilt": (256, 64, 128), "M_LeadedLight": (128,), "M_SkyDome": (512,)},
         default_size=(256, 64, 128), no_shadow={"M_SkyDome"})
