"""
Fable step-in room `brobdingnag-farmhouse-table`: the farmer's dinner table in Brobdingnag, at noon in June 1703
(Gulliver's Travels, Part II, Chapter I).

"It was about twelve at noon, and a servant brought in dinner. It was only one substantial dish of meat (fit for the
plain condition of a husbandman,) in a dish of about four-and-twenty feet diameter ... The table was about thirty
feet high from the floor ... I was in a terrible fright, and kept as far as I could from the edge, for fear of
falling. The wife minced a bit of meat, then crumbled some bread on a trencher, and placed it before me ... The
mistress ordered her maid to bring a small dram cup, which held about two gallons, and filled it with drink."

The reader is Gulliver-size on the tabletop, everything else twelve times larger: scrubbed deal boards a metre wide
with grain like floorboards, the trencher with crumbled bread and minced meat before the reader, the dram cup, the
vast pewter dish of boiled beef beyond, a loaf like a boulder, the giants' knives, spoons and pewter plates set at
their places, a salt, a stoneware jug. Past the edge (a sheer 9 m drop) the farmhouse room: the giants' benches and
chairs pushed back, the hearth with its fire, whitewashed walls, beams, and the tall window of midday light.
The giant family and the cat are not modelled (a missing figure is better than an unconvincing one): their empty
places, the chairs, a shawl over a chair-back and the pushed-back cushions say where they sit.

Run (from the repo root), one Blender job at a time through the shared slot wrapper:
  blender_slot.sh -b -P blender/build_brobdingnag_farmhouse_table.py -- --cpu --render --samples 40 --res 1280
  blender_slot.sh -b -P blender/build_brobdingnag_farmhouse_table.py -- --export
  then blender/runtime_bake.py (--indoor) and tools/publish_scene_room.py (docs/SCENE_ROOMS_PIPELINE.md)
Axes: metres at the reader's scale, +Z up; the tabletop is z = 0 (9.1 m above the floor), the table runs along X.
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b3 as K
import roomkit as rk
import pride_kit as pk

ARGS = K.setup("brobdingnag-farmhouse-table", seed=1703, samples=40)
if ARGS.cpu: bpy.context.scene.cycles.device = 'CPU'
R = random.Random(1703)
G = 12.0                       # the giants' scale
FLOOR = -9.1


def giant(m, f=1.0 / G):
    """Scale a procedural material's pattern up by the giants' factor (noise, voronoi and brick textures)."""
    for n in m.node_tree.nodes:
        if n.type in ('TEX_NOISE', 'TEX_VORONOI', 'TEX_WAVE') and "Scale" in n.inputs: n.inputs["Scale"].default_value *= f
        if n.type == 'TEX_BRICK':
            n.inputs["Brick Width"].default_value /= f; n.inputs["Row Height"].default_value /= f; n.inputs["Mortar Size"].default_value /= f
        if n.type == 'BUMP': n.inputs["Distance"].default_value /= f
    return m


# ----------------------------------------------------------------------------- materials (all at giant scale)
DEAL = K.mat("scrubbed_deal", (0.74, 0.63, 0.47), "wood", rough=0.7)
OAK = giant(K.mat("oak_furniture", (0.32, 0.22, 0.13), "wood", rough=0.6))
PEWTER = giant(K.mat("pewter", (0.55, 0.56, 0.56), "metal", rough=0.35))
WARE = giant(K.mat("stoneware", (0.62, 0.52, 0.38), "tile", rough=0.4))
BEEF = giant(K.mat("boiled_beef", (0.40, 0.24, 0.17), "soil", rough=0.6))
FAT = giant(K.mat("fat_and_broth", (0.80, 0.70, 0.50), "fabric", rough=0.4))
CRUST = giant(K.mat("bread_crust", (0.58, 0.38, 0.18), "soil", rough=0.8))
CRUMB = giant(K.mat("bread_crumb", (0.86, 0.78, 0.60), "sand", rough=0.9))
MINCE = giant(K.mat("minced_meat", (0.40, 0.22, 0.16), "soil", rough=0.8))
STEEL = giant(K.mat("knife_steel", (0.46, 0.46, 0.47), "metal", rough=0.3))
HORN = giant(K.mat("horn_handles", (0.26, 0.18, 0.11), "wood", rough=0.5))
SALT = giant(K.mat("salt", (0.92, 0.91, 0.88), "sand", rough=0.9))
ALE = giant(K.mat("ale", (0.42, 0.26, 0.08), "water", rough=0.1))
WALL = giant(K.patchy_mat("whitewash", (0.84, 0.81, 0.73), patches=[((0.62, 0.58, 0.50), 0.6, 0.3), ((0.40, 0.36, 0.30), 0.3, 0.1)], rough=0.92))
FLAGS = giant(K.ashlar_mat("floor_flags", (0.50, 0.46, 0.40), block=(0.55, 0.45), joint=0.03, mortar=(0.25, 0.23, 0.20), var=0.2, dark_low=False, floor=True))
BEAM = giant(K.mat("beams", (0.20, 0.14, 0.09), "wood", rough=0.75))
HOMESPUN = giant(K.mat("homespun_shawl", (0.45, 0.30, 0.20), "fabric", rough=0.95))
CUSHION = giant(K.mat("cushion", (0.32, 0.36, 0.22), "fabric", rough=0.95))
SOOT = K.mat("soot", (0.03, 0.028, 0.025), "plaster", rough=0.98)
EMBER = K.emit_mat("embers", (1.0, 0.38, 0.1), 4.0)
FLAME = K.emit_mat("flame", (1.0, 0.62, 0.25), 6.0)
SKYW = K.emit_mat("window_daylight", (0.86, 0.90, 0.95), 2.2)
GLASS = K.mat("window_lead", (0.08, 0.08, 0.08), "metal", rough=0.5)
K.size(DEAL, 2048, 256); K.size(WALL, 1024, 128); K.size(FLAGS, 1024, 128)

# ----------------------------------------------------------------------------- the table (26 x 11 m), its edge and legs
TX0, TX1, TY0, TY1 = -6.0, 20.0, -5.5, 5.5
T = rk._B("table")
T.box(OAK, (TX1 - TX0, TY1 - TY0, 0.5), ((TX0 + TX1) / 2, 0.0, -0.62))
# the top: deal boards about 1.1 m wide (9 inches at the giants' scale), slightly uneven, dark seams between
y = TY0
while y < TY1 - 0.01:
    bw = min(R.uniform(1.0, 1.25), TY1 - y)
    T.box(DEAL, (TX1 - TX0, bw - 0.035, 0.14), ((TX0 + TX1) / 2, y + bw / 2, -0.14 + R.uniform(-0.012, 0.012)), (R.uniform(-0.05, 0.05), 0, 0))
    y += bw
for x in (TX0 + 1.0, TX1 - 1.0):
    for y in (TY0 + 1.0, TY1 - 1.0):
        T.box(OAK, (1.0, 1.0, -FLOOR - 0.6), (x, y, FLOOR))
T.box(OAK, (TX1 - TX0 - 2.0, 0.5, 1.4), ((TX0 + TX1) / 2, TY0 + 1.0, -2.0))
T.box(OAK, (TX1 - TX0 - 2.0, 0.5, 1.4), ((TX0 + TX1) / 2, TY1 - 1.0, -2.0))
T.done()
rk._ground.append(lambda x, y: 0.0 if (TX0 <= x <= TX1 and TY0 <= y <= TY1) else None)

# ----------------------------------------------------------------------------- what is on the table
# the trencher before the reader: a square wooden board with the crumbled bread and minced meat
TR = Vector((0.0, 1.9, 0.0))
pk.box("Trencher", (3.6, 3.6, 0.3), (TR.x, TR.y, 0.15), OAK, bevel=0.15)
for k in range(46):
    p = TR + Vector((R.uniform(-1.3, 1.3), R.uniform(-1.3, 1.3), 0.32))
    s = R.uniform(0.08, 0.28)
    o = pk.box(f"Crumb{k}", (s * R.uniform(0.8, 1.4), s, s * 0.7), tuple(p + Vector((0, 0, s * 0.3))), CRUMB if R.random() < 0.7 else CRUST, bevel=s * 0.25,
               rot=(R.uniform(0, 1), R.uniform(0, 1), R.uniform(0, 3)))
for k in range(30):
    p = TR + Vector((R.uniform(-0.4, 1.1), R.uniform(-1.0, 0.6), 0.32))
    pk.sphere(f"Mince{k}", R.uniform(0.06, 0.14), tuple(p), MINCE, seg=6, scale=(1.3, 1.0, 0.6))
# the dram cup, filled with drink
pk.lathe("DramCup", [(0.0, 0.0), (0.14, 0.0), (0.15, 0.02), (0.13, 0.04), (0.14, 0.24), (0.16, 0.30), (0.145, 0.30), (0.125, 0.06), (0.0, 0.06)], (1.6, 0.0, 0.0), PEWTER, steps=24)
pk.cyl("DramAle", 0.13, 0.01, (1.6, 0.0, 0.27), ALE, verts=20)
# the great dish of boiled beef, 24 feet across
DC = Vector((11.0, 0.5, 0.0))
pk.lathe("Dish", [(0.0, 0.0), (2.8, 0.0), (3.4, 0.25), (3.66, 0.42), (3.6, 0.46), (3.3, 0.33), (2.7, 0.12), (0.0, 0.12)], tuple(DC), PEWTER, steps=48)
pk.cyl("Broth", 2.9, 0.04, tuple(DC + Vector((0, 0, 0.2))), FAT, verts=40)
# the joint: a great lumpy mass of beef with a bone end and a layer of fat
BJ = rk._B("beef", tuple(DC + Vector((0, 0, 0.2))), 25)
for k in range(9):
    BJ.ball(BEEF, R.uniform(0.9, 1.3), (R.uniform(-1.3, 1.3), R.uniform(-0.6, 0.6), 0.5 + R.uniform(0.0, 0.4)), squash=(1.3, 1.0, 0.75), sub=2)
BJ.ball(FAT, 1.15, (0.3, 0.0, 1.25), squash=(1.8, 1.0, 0.35), sub=2)
BJ.seg(FAT, (1.5, 0.2, 0.9), (2.6, 0.5, 1.2), 0.32, 0.26, 10)
BJ.ball(FAT, 0.42, (2.7, 0.5, 1.25), sub=1)
BJ.done()
for k in range(10):
    a = R.uniform(0, 6.28); r = R.uniform(2.2, 2.8)
    pk.sphere(f"Carrot{k}", 0.3, tuple(DC + Vector((math.cos(a) * r, math.sin(a) * r, 0.3))), giant(K.mat("carrots", (0.75, 0.38, 0.12), "fabric", rough=0.6)), seg=8, scale=(1.8, 0.6, 0.5))
# the loaf, the salt, the jug, the giants' plates, knives and spoons at their places
LF = rk._B("loaf", (5.5, 3.6, 0.0), 10)
LF.ball(CRUST, 1.0, (0.2, 0, 0.75), squash=(1.7, 1.05, 0.85), sub=3)
LF.ball(CRUST, 0.6, (0.2, 0, 1.45), squash=(1.5, 0.8, 0.5), sub=2)
LF.done()
pk.lathe("Salt", [(0.0, 0.0), (0.55, 0.0), (0.5, 0.15), (0.3, 0.3), (0.5, 0.75), (0.5, 0.85), (0.0, 0.85)], (7.0, -3.4, 0.0), PEWTER, steps=20)
pk.cyl("SaltHeap", 0.42, 0.06, (7.0, -3.4, 0.83), SALT, verts=16)
pk.lathe("Jug", [(0.0, 0.0), (0.8, 0.0), (1.1, 0.8), (1.2, 1.6), (0.9, 2.6), (0.7, 3.0), (0.85, 3.3), (0.0, 3.2)], (16.0, 3.8, 0.0), WARE, steps=24)
pk.tube("JugHandle", [Vector((16.0, 4.85, 2.8)), Vector((16.0, 5.5, 2.4)), Vector((16.0, 5.3, 1.3)), Vector((16.0, 4.95, 1.1))], 0.12, WARE, sides=8)
PLACES = [(9.0, -4.2, 0), (13.5, -4.2, 0), (17.5, -1.0, 90), (13.5, 4.3, 180), (8.5, 4.3, 180)]
for k, (x, y, yaw) in enumerate(PLACES):
    pk.lathe(f"Plate{k}", [(0.0, 0.0), (1.1, 0.0), (1.5, 0.12), (1.55, 0.16), (1.45, 0.16), (1.05, 0.06), (0.0, 0.06)], (x, y, 0.0), PEWTER, steps=36)
    d = Vector((math.cos(math.radians(yaw + 90)), math.sin(math.radians(yaw + 90)), 0))
    side = Vector((-d.y, d.x, 0))
    kp = Vector((x, y, 0.1)) + side * 2.0
    pk.box(f"KnifeBlade{k}", (0.32, 1.6, 0.05), tuple(kp + d * 0.6), STEEL, rot=(0, 0, math.radians(yaw)))
    pk.box(f"KnifeHandle{k}", (0.36, 1.2, 0.22), tuple(kp - d * 0.8), HORN, bevel=0.08, rot=(0, 0, math.radians(yaw)))
    sp_ = Vector((x, y, 0.06)) - side * 2.0
    pk.sphere(f"SpoonBowl{k}", 0.35, tuple(sp_ + d * 0.9), PEWTER, seg=12, scale=(0.75, 1.0, 0.25))
    pk.box(f"SpoonHandle{k}", (0.12, 1.9, 0.08), tuple(sp_ - d * 0.5), PEWTER, rot=(0, 0, math.radians(yaw)))
# a scatter of giant crumbs and a spill of broth, a bone on a plate
for k in range(14):
    p = Vector((R.uniform(6, 18), R.uniform(-4.5, 4.5), 0.0))
    if (p - DC).length < 4.0: continue
    s = R.uniform(0.12, 0.35)
    pk.box(f"TableCrumb{k}", (s, s * 0.8, s * 0.6), tuple(p + Vector((0, 0, s * 0.25))), CRUMB, bevel=s * 0.25, rot=(0, 0, R.uniform(0, 3)))

# ----------------------------------------------------------------------------- the farmhouse room, 9 m below and all round
RX0, RX1, RY0, RY1 = -40.0, 50.0, -34.0, 34.0
H = 30.0
rk.box("room_floor", (RX1 - RX0, RY1 - RY0, 0.5), ((RX0 + RX1) / 2, 0.0, FLOOR - 0.5), FLAGS)
rk.box("room_ceiling", (RX1 - RX0, RY1 - RY0, 0.6), ((RX0 + RX1) / 2, 0.0, FLOOR + H), giant(K.mat("ceiling_boards", (0.30, 0.24, 0.17), "planks", rough=0.85)))
WIN = (RX0 + 30.0, 14.0, FLOOR + 9.0, 16.0)                 # window in the north wall: x centre, width, sill, height
for (name, size, loc) in (("wall_s", (RX1 - RX0, 1.0, H), ((RX0 + RX1) / 2, RY0 - 0.5, FLOOR)),
                          ("wall_e", (1.0, RY1 - RY0, H), (RX1 + 0.5, 0.0, FLOOR)), ("wall_w", (1.0, RY1 - RY0, H), (RX0 - 0.5, 0.0, FLOOR))):
    rk.box(name, size, loc, WALL)
# the north wall with its tall window (an opening, leaded lights, daylight beyond)
wx, ww, ws, wh = WIN
rk.box("wall_n_left", (wx - ww / 2 - RX0, 1.0, H), ((RX0 + wx - ww / 2) / 2, RY1 + 0.5, FLOOR), WALL)
rk.box("wall_n_right", (RX1 - wx - ww / 2, 1.0, H), ((RX1 + wx + ww / 2) / 2, RY1 + 0.5, FLOOR), WALL)
rk.box("wall_n_low", (ww, 1.0, ws - FLOOR), (wx, RY1 + 0.5, FLOOR), WALL)
rk.box("wall_n_high", (ww, 1.0, FLOOR + H - ws - wh), (wx, RY1 + 0.5, ws + wh), WALL)
rk.box("window_sky", (ww + 2, 0.2, wh + 2), (wx, RY1 + 4.0, ws - 1), SKYW)
WB = rk._B("window_bars")
for k in range(1, 6): WB.box(GLASS, (0.25, 0.3, wh), (wx - ww / 2 + k * ww / 6, RY1 + 0.6, ws))
for k in range(1, 5): WB.box(GLASS, (ww, 0.3, 0.25), (wx, RY1 + 0.6, ws + k * wh / 5))
WB.done()
BM = rk._B("beams")
for x in np.arange(RX0 + 6, RX1, 12.0): BM.box(BEAM, (2.4, RY1 - RY0, 3.0), (x, 0.0, FLOOR + H - 3.0))
BM.done()
# the hearth in the east wall, a fire burning low under the pot-crane
HX = RX1
HE = rk._B("hearth")
HE.box(SOOT, (0.5, 18.0, 14.0), (HX - 0.3, 6.0, FLOOR))
HE.box(WALL, (5.0, 3.0, 16.0), (HX - 2.5, -4.5, FLOOR)); HE.box(WALL, (5.0, 3.0, 16.0), (HX - 2.5, 16.5, FLOOR))
HE.box(BEAM, (5.5, 24.0, 2.6), (HX - 2.6, 6.0, FLOOR + 14.0))
for k in range(5): HE.seg(BEAM, (HX - 4.0, 2.0 + k * 1.6, FLOOR + 0.8), (HX - 1.0, 3.0 + k * 1.5, FLOOR + 1.3), 0.7, 0.6, 8)
for k in range(12): HE.ball(EMBER, R.uniform(0.5, 0.9), (HX - R.uniform(1.0, 4.0), R.uniform(2.0, 10.0), FLOOR + 0.3), squash=(1.3, 1.0, 0.5), sub=0)
HE.done()
# the giants' places: a bench along the south side, chairs pushed back at the end and the north side, a shawl over
# the mistress's chair-back, a cushion on the seat
CH = rk._B("chairs")
CH.box(OAK, (24.0, 4.0, 5.4), (7.0, TY0 - 4.5, FLOOR))
for (x, y, yaw, shawl) in ((9.0, TY1 + 6.5, 180, True), (16.0, TY1 + 7.5, 175, False), (TX1 + 6.0, -1.0, 90, False)):
    C = rk._B("chair", (x, y, FLOOR), yaw)
    C.box(OAK, (5.4, 5.2, 0.8), (0, 0, 5.4))
    for sx in (-1, 1):
        for sy in (-1, 1): C.box(OAK, (0.6, 0.6, 5.4), (sx * 2.2, sy * 2.1, 0))
        C.box(OAK, (0.7, 0.7, 13.0), (sx * 2.2, -2.3, 0))
    for zz in (8.0, 10.5, 12.5): C.box(OAK, (4.4, 0.4, 0.9), (0, -2.3, zz))
    C.box(CUSHION, (4.6, 4.4, 0.9), (0, 0.2, 6.2))
    if shawl:
        C.box(HOMESPUN, (5.0, 0.6, 4.0), (0, -2.5, 9.6), (6, 0, 0))
        C.box(HOMESPUN, (5.2, 1.4, 0.5), (0, -2.3, 13.3))
    C.done()
CH.done()

# ----------------------------------------------------------------------------- light, sound, reader
rk.area_light("window", (wx, RY1 + 2.0, ws + wh / 2), (ww, wh), 90000, color=(1.0, 0.96, 0.88), aim=(-0.25, -1, -0.45))
K.sun(58, 120, strength=3.0, color=(1.0, 0.95, 0.85), softness=1.0)
rk.lamp("hearth", (HX - 4.0, 6.0, FLOOR + 4.0), power=60000, color=(1.0, 0.55, 0.25), radius=2.0)
rk.lamp("fill", (5.0, 0.0, 12.0), power=30000, color=(0.95, 0.92, 0.85), radius=6.0)
w = bpy.context.scene.world
for n in list(w.node_tree.nodes): w.node_tree.nodes.remove(n)
bg = w.node_tree.nodes.new("ShaderNodeBackground"); out = w.node_tree.nodes.new("ShaderNodeOutputWorld")
bg.inputs["Color"].default_value = (0.25, 0.25, 0.23, 1); w.node_tree.links.new(bg.outputs[0], out.inputs[0])
K.fx("fire", "hearth", (HX - 3.0, 6.0, FLOOR + 1.2), 3.0)
K.sound("fire", "hearth", (HX - 3.0, 6.0, FLOOR + 2.0))
K.sound("crowd", "family", (12.0, TY1 + 8.0, 6.0))
K.sound("clock", "room", (RX0 + 2.0, 20.0, FLOOR + 14.0))
E, D = K.reader((-1.2, -0.6), (11.0, 0.5))
K.reader_cams()
K.cam("edge", (-3.0, -4.4, 1.55), (-12.0, -20.0, FLOOR + 4.0), lens=18)
K.cam("table", (-4.5, 3.8, 3.0), (12.0, -1.0, 0.0), lens=18)
K.finish()
