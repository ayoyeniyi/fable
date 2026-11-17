"""
Fable step-in room `duchess-kitchen`: the Duchess's kitchen (Alice's Adventures in Wonderland, Chapter VI, "Pig and
Pepper").

"The door led right into a large kitchen, which was full of smoke from one end to the other: the Duchess was sitting
on a three-legged stool in the middle, nursing a baby; the cook was leaning over the fire, stirring a large cauldron
which seemed to be full of soup ... The only things in the kitchen that did not sneeze, were the cook, and a large cat
which was sitting on the hearth and grinning from ear to ear ... the cook took the cauldron of soup off the fire, and
at once set to work throwing everything within her reach at the Duchess and the baby - the fire-irons came first;
then followed a shower of saucepans, plates, and dishes."

A Victorian country kitchen (about 1865) shown at full room scale: rough stone flags, sooty lime-washed walls, smoke-
blackened beams, a wide open hearth on the far wall under an oak bressumer with a low fire and a black iron cauldron
of soup hanging from a crane, a deal table with the pepper-box and crockery, a dresser of plates, copper pans on a
rail. The three-legged stool stands empty in the middle; the fire-irons, saucepans, a frying-pan and broken plates and
dishes lie thrown about the flags. On the hearth seat, only a faint grin. Firelight, and dim daylight from a small
window and the open door behind the reader; the air hazy with smoke and pepper.
No people, no baby or pig, no croquet things, no modern stove.

Run (from the repo root), one Blender job at a time through the shared slot wrapper:
  blender_slot.sh -b -P blender/build_duchess_kitchen.py -- --cpu --render --samples 40 --res 1280
  blender_slot.sh -b -P blender/build_duchess_kitchen.py -- --export
  then blender/runtime_bake.py (--indoor) and tools/publish_scene_room.py (docs/SCENE_ROOMS_PIPELINE.md)
Axes: metres, +Z up; the door is in the south wall, the hearth in the north wall; the reader faces north-east.
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b3 as K
import roomkit as rk
import pride_kit as pk

ARGS = K.setup("duchess-kitchen", seed=1865, samples=40)
if ARGS.cpu: bpy.context.scene.cycles.device = 'CPU'
R = random.Random(1865)

# ----------------------------------------------------------------------------- materials
FLAGS = K.ashlar_mat("stone_flags", (0.46, 0.43, 0.38), block=(0.62, 0.48), joint=0.03, mortar=(0.20, 0.18, 0.16), var=0.22, rough=0.85, dark_low=False, floor=True)
WALL = K.patchy_mat("sooty_limewash", (0.70, 0.66, 0.56), patches=[((0.30, 0.27, 0.23), 0.6, 0.30), ((0.52, 0.50, 0.42), 1.5, 0.35), ((0.20, 0.18, 0.16), 0.25, 0.12)], rough=0.92, bump=0.4)
BEAM = K.mat("smoked_oak", (0.13, 0.09, 0.06), "wood", rough=0.8)
BOARDS = K.mat("ceiling_boards", (0.20, 0.15, 0.11), "planks", rough=0.85)
HEARTHST = K.stone_mat("hearth_stone", (0.44, 0.41, 0.36), dark=(0.20, 0.18, 0.16), scale=1.2)
SOOT = K.mat("soot", (0.035, 0.03, 0.028), "plaster", rough=0.98)
IRON = K.mat("black_iron", (0.05, 0.048, 0.045), "metal", rough=0.55)
COPPER = K.mat("copper", (0.72, 0.38, 0.22), "metal", rough=0.3)
DEAL = K.mat("scrubbed_deal", (0.72, 0.60, 0.44), "wood", rough=0.75)
DRESSER = K.mat("painted_dresser", (0.36, 0.42, 0.40), "wood", rough=0.7)
CROCK = K.mat("crockery", (0.86, 0.85, 0.80), "tile", rough=0.25)
WILLOW = K.mat("blue_ware", (0.34, 0.42, 0.62), "tile", rough=0.25)
EARTHEN = K.mat("earthenware", (0.62, 0.38, 0.22), "tile", rough=0.5)
TIN = K.mat("tin", (0.62, 0.62, 0.60), "metal", rough=0.35)
SOUP = K.mat("soup", (0.36, 0.24, 0.12), "water", rough=0.2)
LOGS = K.mat("logs", (0.30, 0.22, 0.15), "bark", rough=0.9)
EMBER = K.emit_mat("embers", (1.0, 0.35, 0.08), 4.0)
FLAME = K.emit_mat("flame", (1.0, 0.62, 0.22), 6.0)
GRIN = K.emit_mat("grin", (0.86, 0.84, 0.76), 0.25)
GLASS = K.mat("leaded_glass", (0.55, 0.60, 0.58), "glass", rough=0.1)
DOORW = K.mat("door_boards", (0.26, 0.19, 0.13), "planks", rough=0.8)
DAY = K.emit_mat("daylight_outside", (0.72, 0.78, 0.70), 1.6)
PEPPER = K.mat("pepper", (0.12, 0.10, 0.08), "soil", rough=0.95)
K.size(FLAGS, 2048, 256); K.size(WALL, 1024, 128); K.size(BEAM, 1024, 128); K.size(HEARTHST, 1024, 128)

# ----------------------------------------------------------------------------- the room
HW, HD, H = 3.0, 2.5, 2.7
rk.room("kitchen", 2 * HW, 2 * HD, H, WALL, FLAGS, ceiling=BOARDS,
        openings=[{"wall": "s", "at": -1.6, "width": 0.95, "height": 2.0, "sill": 0.0},
                  {"wall": "w", "at": 0.7, "width": 0.75, "height": 0.8, "sill": 1.1}], thickness=0.45)
# smoke-blackened beams and joists
B = rk._B("beams")
for x in np.arange(-HW + 0.5, HW, 1.0):
    B.box(BEAM, (0.2, 2 * HD, 0.24), (x + R.uniform(-0.05, 0.05), 0.0, H - 0.24), (0, 0, R.uniform(-1, 1)))
B.box(BEAM, (2 * HW, 0.28, 0.3), (0.0, 0.2, H - 0.54))
B.done()
# outside the door and the window: a bright daylit backdrop (the wood)
rk.box("door_daylight", (1.2, 0.02, 2.2), (-1.6, -HD - 0.9, 0.0), DAY)
rk.box("window_daylight", (0.02, 0.9, 1.0), (-HW - 0.7, 0.7, 1.0), DAY)
# the door, standing open into the room, and the window's leaded casement
D = rk._B("door", (-1.6 + 0.47, -HD + 0.02, 0.0), 95)
D.box(DOORW, (0.92, 0.05, 1.98), (-0.46, 0.0, 0.0))
for zz in (0.3, 1.0, 1.7): D.box(DOORW, (0.86, 0.06, 0.12), (-0.46, 0.04, zz))
D.ball(IRON, 0.025, (-0.82, 0.08, 1.0), sub=0)
D.done()
Wn = rk._B("window")
Wn.box(GLASS, (0.02, 0.73, 0.78), (-HW - 0.2, 0.7, 1.11))
for k in range(5): Wn.box(IRON, (0.025, 0.006, 0.78), (-HW - 0.19, 0.7 - 0.36 + k * 0.18, 1.11))
for k in range(5): Wn.box(IRON, (0.025, 0.73, 0.006), (-HW - 0.19, 0.7, 1.11 + k * 0.19))
Wn.box(BEAM, (0.5, 0.85, 0.06), (-HW - 0.05, 0.7, 1.04))
Wn.done()

# ----------------------------------------------------------------------------- the hearth: chimney breast, inglenook opening, bressumer
CB = rk._B("hearth")
OW, OH, OD = 2.0, 1.45, 0.6
y0 = HD - OD                                      # face of the chimney breast
for sx in (-1, 1):
    CB.box(HEARTHST, (0.45, OD, OH), (sx * (OW / 2 + 0.225), HD - OD / 2, 0.0))
    K.rough_block(CB, HEARTHST, (0.47, 0.06, 0.4), (sx * (OW / 2 + 0.225), y0 - 0.02, 0.0), amp=0.01, seed=3 + sx)
CB.box(WALL, (OW + 0.9, OD, H - OH - 0.3), (0.0, HD - OD / 2, OH + 0.3))
CB.box(BEAM, (OW + 0.9, 0.34, 0.3), (0.0, y0 + 0.12, OH))                       # the oak bressumer
CB.box(SOOT, (OW, 0.05, OH), (0.0, HD - 0.02, 0.0))                              # fireback
for sx in (-1, 1): CB.box(SOOT, (0.04, OD, OH), (sx * OW / 2, HD - OD / 2, 0.0))
CB.box(SOOT, (OW, OD, 0.04), (0.0, HD - OD / 2, OH - 0.04))
CB.box(HEARTHST, (OW + 1.0, OD + 0.45, 0.08), (0.0, HD - OD / 2 - 0.2, 0.0))     # raised hearth stone
# the hearth seat in the inglenook's left corner (where the cat sat)
CB.box(BEAM, (0.45, 0.4, 0.06), (-OW / 2 + 0.3, HD - 0.3, 0.42))
for sx in (-1, 1): CB.box(BEAM, (0.06, 0.36, 0.42), (-OW / 2 + 0.3 + sx * 0.19, HD - 0.3, 0.0))
# a mantel shelf on the bressumer with jars and a candlestick
CB.box(BEAM, (OW + 1.0, 0.22, 0.05), (0.0, y0 - 0.02, OH + 0.3))
CB.done()
for k, x in enumerate((-1.1, -0.8, 0.5, 0.85, 1.15)):
    pk.lathe(f"MantelJar{k}", [(0.0, 0.0), (0.05, 0.0), (0.06, 0.06), (0.045, 0.14), (0.03, 0.16), (0.0, 0.16)], (x, y0 - 0.02, OH + 0.35), EARTHEN if k % 2 else WILLOW, steps=12)
# the fire: logs on firedogs, embers, a low flame
F = rk._B("fire")
FC = Vector((0.15, HD - 0.3, 0.08))
for sx in (-1, 1):
    F.box(IRON, (0.05, 0.4, 0.05), (FC.x + sx * 0.3, FC.y, FC.z), (0, 0, 0))
    F.box(IRON, (0.05, 0.05, 0.3), (FC.x + sx * 0.3, FC.y - 0.2, FC.z))
for k in range(5):
    a = R.uniform(-0.3, 0.3)
    F.seg(LOGS, (FC.x - 0.4, FC.y + R.uniform(-0.12, 0.12), FC.z + 0.06 + 0.05 * (k % 2)), (FC.x + 0.4, FC.y + R.uniform(-0.12, 0.12) + a * 0.3, FC.z + 0.06 + 0.05 * (k % 2)), 0.06, 0.055, 7)
for k in range(14):
    F.ball(EMBER, R.uniform(0.03, 0.06), (FC.x + R.uniform(-0.3, 0.3), FC.y + R.uniform(-0.15, 0.15), FC.z + 0.02), squash=(1.3, 1.0, 0.5), sub=0)
F.done()
# the crane: an iron post on the left jamb, its arm swung over the fire, a pot-hook, the cauldron of soup
CR = rk._B("crane")
post = Vector((-OW / 2 + 0.12, HD - 0.25, 0.08))
CR.seg(IRON, tuple(post), tuple(post + Vector((0, 0, 1.25))), 0.022, 0.022, 6)
arm_end = Vector((FC.x + 0.02, FC.y - 0.05, post.z + 1.15))
CR.seg(IRON, tuple(post + Vector((0, 0, 1.15))), tuple(arm_end), 0.018, 0.018, 6)
CR.seg(IRON, tuple(post + Vector((0, 0, 0.55))), tuple(post + Vector((0.6, 0, 1.15))), 0.014, 0.014, 5)
CR.seg(IRON, tuple(arm_end), tuple(arm_end - Vector((0, 0, 0.42))), 0.01, 0.01, 4)
CR.done()
CAUL = arm_end - Vector((0, 0, 0.42 + 0.48))
pk.lathe("Cauldron", [(0.0, 0.0), (0.12, 0.0), (0.24, 0.06), (0.30, 0.2), (0.30, 0.34), (0.26, 0.44), (0.27, 0.47), (0.25, 0.48), (0.24, 0.44), (0.0, 0.44)],
         tuple(CAUL), IRON, steps=24)
pk.cyl("Soup", 0.245, 0.01, tuple(CAUL + Vector((0, 0, 0.43))), SOUP, verts=24)
pk.tube("Bail", [CAUL + Vector((-0.28, 0, 0.44)), CAUL + Vector((-0.18, 0, 0.75)), CAUL + Vector((0, 0, 0.82)), CAUL + Vector((0.18, 0, 0.75)), CAUL + Vector((0.28, 0, 0.44))], 0.008, IRON, sides=5)
pk.tube("Ladle", [CAUL + Vector((0.1, -0.05, 0.4)), CAUL + Vector((0.35, -0.2, 0.85))], 0.008, TIN, sides=5)
anchor = K.anchor("kitchen.hearth", (0.0, y0, 0.0))
# the faint grin on the hearth seat: a crescent of teeth hanging in the smoke, nothing else
gm = bmesh.new(); gc = Vector((-OW / 2 + 0.3, HD - 0.38, 0.74))
for i in range(15):
    t = (i + 0.5) / 15; a = math.radians(205 + 130 * t)
    o = gc + Vector((math.cos(a) * 0.12, -0.015 * math.sin(math.pi * t), math.sin(a) * 0.04 + 0.05))
    hh = 0.012 + 0.012 * math.sin(math.pi * t)
    q = [gm.verts.new(o + Vector((-0.0055, 0, -hh))), gm.verts.new(o + Vector((0.0055, 0, -hh))), gm.verts.new(o + Vector((0.0055, 0, hh))), gm.verts.new(o + Vector((-0.0055, 0, hh)))]
    gm.faces.new(q)
rk._obj("grin", gm, GRIN)

# ----------------------------------------------------------------------------- the three-legged stool, the table, the dresser, pans
ST = rk._B("stool", (0.15, 0.25, 0.0), 20)
ST.cyl(DEAL, 0.18, 0.05, (0, 0, 0.42), sides=16)
for k in range(3):
    a = math.radians(90 + 120 * k)
    ST.seg(DEAL, (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.0), (math.cos(a) * 0.1, math.sin(a) * 0.1, 0.43), 0.022, 0.02, 6)
ST.done()
TB = rk._B("table", (-2.15, 0.55, 0.0), 90)
TB.box(DEAL, (1.7, 0.8, 0.05), (0, 0, 0.74))
for sx in (-1, 1):
    for sy in (-1, 1): TB.box(DEAL, (0.07, 0.07, 0.74), (sx * 0.75, sy * 0.33, 0.0))
TB.box(DEAL, (1.5, 0.03, 0.12), (0, 0.33, 0.6)); TB.box(DEAL, (1.5, 0.03, 0.12), (0, -0.33, 0.6))
TB.done()
TZ = 0.79
# on the table: the pepper-box (tin, its lid pierced), spilt pepper, a bowl, a jug, a loaf, a chopping board
pk.lathe("PepperBox", [(0.0, 0.0), (0.035, 0.0), (0.035, 0.09), (0.03, 0.1), (0.02, 0.12), (0.0, 0.125)], (-2.0, 0.2, TZ), TIN, steps=12)
pb = bmesh.new()
for k in range(160):
    r = abs(R.gauss(0, 0.07)); a = R.uniform(0, 6.283)
    bmesh.ops.create_cube(pb, size=0.004, matrix=Matrix.Translation((-2.0 + 0.06 + math.cos(a) * r, 0.2 + math.sin(a) * r, TZ + 0.001)))
rk._obj("spilt_pepper", pb, PEPPER)
pk.lathe("MixingBowl", [(0.0, 0.0), (0.08, 0.0), (0.16, 0.06), (0.17, 0.11), (0.155, 0.11), (0.145, 0.065), (0.0, 0.02)], (-2.25, 0.85, TZ), EARTHEN, steps=20)
pk.lathe("Jug", [(0.0, 0.0), (0.06, 0.0), (0.075, 0.06), (0.06, 0.16), (0.045, 0.2), (0.055, 0.23), (0.0, 0.22)], (-2.4, 0.2, TZ), CROCK, steps=14)
pk.box("Loaf", (0.24, 0.14, 0.1), (-2.0, 1.05, TZ + 0.05), K.mat("crust", (0.55, 0.36, 0.18), "soil", rough=0.8), bevel=0.04)
pk.box("Board", (0.4, 0.26, 0.025), (-2.05, 1.0, TZ + 0.0125), DEAL, bevel=0.005)
# the dresser on the east wall: a cupboard base, a rack of plates, cups on hooks
DR = rk._B("dresser", (HW - 0.27, -0.6, 0.0), 90)
DR.box(DRESSER, (1.6, 0.5, 0.86), (0, 0, 0.0)); DR.box(DRESSER, (1.66, 0.54, 0.04), (0, 0, 0.86))
for k in (-0.4, 0.4): DR.box(DRESSER, (0.7, 0.02, 0.62), (k, -0.26, 0.12))
DR.box(DRESSER, (1.6, 0.03, 1.15), (0, 0.24, 0.9)); DR.box(DRESSER, (1.7, 0.3, 0.06), (0, 0.1, 2.05))
for sx in (-1, 1): DR.box(DRESSER, (0.04, 0.28, 1.15), (sx * 0.78, 0.1, 0.9))
for k, zz in enumerate((1.25, 1.6)):
    DR.box(DRESSER, (1.5, 0.22, 0.03), (0, 0.12, zz))
    DR.box(DRESSER, (1.5, 0.02, 0.03), (0, 0.02, zz + 0.05))
DR.done()
for k, zz in enumerate((0.9, 1.28, 1.63)):
    for i in range(7):
        x = -0.65 + i * 0.21
        if k == 0 and i % 2: continue
        loc = Vector(((HW - 0.27) - 0.12 + (0.05 if k else 0.0), -0.6 + x, zz + 0.12))
        o = pk.cyl(f"Plate{k}_{i}", 0.1, 0.012, tuple(loc), WILLOW if (i + k) % 3 else CROCK, verts=16, rot=(0, math.radians(-75), 0))
# copper pans on a rail beside the hearth, a skillet, a warming pan
for k in range(5):
    x = 1.55 + k * 0.28; r_ = 0.08 + 0.015 * k
    hook = Vector((x, HD - 0.04, 1.85))
    pk.cyl(f"PanBody{k}", r_, 0.09, tuple(hook + Vector((0, -0.02, -0.25 - r_))), COPPER, verts=16, rot=(math.pi / 2, 0, 0))
    pk.tube(f"PanHandle{k}", [hook + Vector((0, -0.02, -0.25 - r_ + r_)), hook], 0.01, COPPER, sides=5)
pk.box("PanRail", (1.6, 0.03, 0.03), (2.1, HD - 0.03, 1.86), IRON)
# the thrown things on the flags: fire-irons, saucepans, a frying-pan, plates and dishes in pieces
MESS = rk._B("mess")
MESS.seg(IRON, (0.9, 0.9, 0.012), (1.5, 0.35, 0.012), 0.011, 0.011, 5)                           # poker
MESS.seg(IRON, (-0.35, 1.25, 0.012), (0.2, 1.55, 0.03), 0.009, 0.009, 5)                          # tongs
MESS.seg(IRON, (-0.3, 1.22, 0.012), (0.18, 1.6, 0.012), 0.009, 0.009, 5)
MESS.seg(IRON, (0.7, -0.4, 0.015), (1.3, -0.6, 0.015), 0.01, 0.01, 5)                             # shovel handle
MESS.box(IRON, (0.18, 0.2, 0.015), (1.38, -0.63, 0.0), (0, 0, -18))
MESS.done()
pk.lathe("FryingPan", [(0.0, 0.0), (0.16, 0.0), (0.18, 0.04), (0.17, 0.045), (0.155, 0.006), (0.0, 0.006)], (-0.9, 0.95, 0.045), IRON, steps=20, rot=(math.pi, 0, 0))
pk.tube("FryingPanHandle", [Vector((-0.75, 0.95, 0.02)), Vector((-0.38, 0.85, 0.02))], 0.012, IRON, sides=5)
for k, (x, y, rx) in enumerate(((0.55, 1.3, 1.4), (-0.5, -0.2, 1.57), (1.2, 1.4, 0.0))):
    o = pk.lathe(f"Saucepan{k}", [(0.0, 0.0), (0.1, 0.0), (0.11, 0.12), (0.105, 0.12), (0.095, 0.01), (0.0, 0.01)], (x, y, 0.1 if rx else 0.0), COPPER if k != 1 else TIN, steps=16, rot=(rx, 0, R.uniform(0, 3)))
for k in range(16):
    x, y = R.uniform(-1.0, 1.6), R.uniform(-0.6, 1.6)
    if math.hypot(x - 0.15, y - 0.25) < 0.35 or math.hypot(x + 1.4, y + 1.75) < 1.0: continue
    a0 = R.uniform(0, 6.28); span = R.uniform(0.6, 1.8); r1 = R.uniform(0.06, 0.12)
    sm = bmesh.new(); c = sm.verts.new((x, y, 0.006)); vs = []
    for i in range(6):
        a = a0 + span * i / 5
        vs.append(sm.verts.new((x + math.cos(a) * r1, y + math.sin(a) * r1, 0.006 + 0.008 * (i % 2))))
    for i in range(5): sm.faces.new((c, vs[i], vs[i + 1]))
    rk._obj(f"shard{k}", sm, CROCK if k % 3 else WILLOW)
pk.lathe("Dish", [(0.0, 0.0), (0.12, 0.0), (0.16, 0.03), (0.15, 0.032), (0.11, 0.008), (0.0, 0.008)], (0.95, 0.15, 0.0), WILLOW, steps=20, rot=(0.35, 0, 0.5))

# ----------------------------------------------------------------------------- light, sound, reader
rk.lamp("fire", (FC.x, FC.y - 0.35, 0.45), power=180, color=(1.0, 0.55, 0.22), radius=0.25)
rk.area_light("door", (-1.6, -HD - 0.3, 1.2), (0.9, 1.9), 220, color=(0.85, 0.9, 1.0), aim=(0, 1, -0.15))
rk.area_light("window", (-HW - 0.3, 0.7, 1.5), (0.7, 0.8), 70, color=(0.85, 0.9, 1.0), aim=(1, 0, -0.3))
rk.lamp("fill", (0.0, -0.5, 2.3), power=25, color=(0.9, 0.85, 0.75), radius=0.8)
w = bpy.context.scene.world; w.use_nodes = True
for n in list(w.node_tree.nodes): w.node_tree.nodes.remove(n)
bg = w.node_tree.nodes.new("ShaderNodeBackground"); out = w.node_tree.nodes.new("ShaderNodeOutputWorld")
bg.inputs["Color"].default_value = (0.05, 0.05, 0.045, 1); w.node_tree.links.new(bg.outputs[0], out.inputs[0])
K.fx("fire", "hearth", (FC.x, FC.y, FC.z + 0.06), 0.35)
K.sound("fire", "hearth", (FC.x, FC.y - 0.2, 0.3))
E, Dd = K.reader((-1.4, -1.75), (0.0, 2.0))
K.reader_cams()
K.cam("hearth", (-0.6, 0.2, 1.2), (0.0, HD, 0.7), lens=22)
K.cam("mess", (1.9, -1.6, 1.6), (0.3, 0.8, 0.0), lens=22)
K.finish()
