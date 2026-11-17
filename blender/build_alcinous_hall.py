"""
Fable step-in room `alcinous-hall`: the great hall of King Alcinous's palace in Scheria, at nightfall (The Odyssey,
Book VII, Butler's translation).

"The walls on either side were of bronze from end to end, and the cornice was of blue enamel. The doors were gold,
and hung on pillars of silver that rose from a floor of bronze, while the lintel was silver and the hook of the door
was of gold ... Seats were ranged all along the wall, here and there from one end to the other, with coverings of
fine woven work which the women of the house had made ... and there were golden figures of young men with lighted
torches in their hands, raised on pedestals, to give light by night to those who were at table ... Ulysses ... sat
down on the hearth among the ashes."

A megaron about 12 x 10 m: walls sheathed in hammered bronze plates under a frieze of blue enamel (kyanos) with gold
rosettes, four painted columns round a great round hearth with its fire and ashes, the seats of Alcinous and Arete
beside it, benches along the walls with woven covers, a loom with its weights and spindles, mixing-bowls and cups on
low tables. The golden torch-bearers stand on pedestals along the walls: the figures are modelled as gilded herm
pillars (a column with a head, the archaic form) holding torches, rather than as naturalistic youths, which could
not be made convincing here. The reader stands on the hearth by the queen's seat facing the doorway: the bronze
threshold, the gold doors open on their silver pillars under a silver lintel, and beyond, the dark garden of pears,
pomegranates and figs under the night sky. No people, no Demodocus or games, no ship, no modern lamps.

Run (from the repo root), one Blender job at a time through the shared slot wrapper:
  blender_slot.sh -b -P blender/build_alcinous_hall.py -- --cpu --render --samples 40 --res 1280
  blender_slot.sh -b -P blender/build_alcinous_hall.py -- --export
  then blender/runtime_bake.py (--indoor) and tools/publish_scene_room.py (docs/SCENE_ROOMS_PIPELINE.md)
Axes: metres, +Z up; the doorway is in the south wall (-Y), the hearth at the centre; the reader faces south.
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, Euler, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b3 as K
import roomkit as rk
import pride_kit as pk

ARGS = K.setup("alcinous-hall", seed=700, samples=40)
if ARGS.cpu: bpy.context.scene.cycles.device = 'CPU'
R = random.Random(700)


def bronze_plates(name, base=(0.62, 0.40, 0.20), plate=(0.6, 0.9)):
    """Hammered bronze sheathing: plates with seams and rivet rows, each plate a slightly different patina, dimpled."""
    m = bpy.data.materials.new("M_" + name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); b = N("ShaderNodeBsdfPrincipled"); L(b.outputs["BSDF"], out.inputs["Surface"])
    tc = N("ShaderNodeTexCoord"); sp = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sp.inputs["Vector"])
    ad = N("ShaderNodeMath"); ad.operation = 'ADD'; L(sp.outputs["X"], ad.inputs[0]); L(sp.outputs["Y"], ad.inputs[1])
    cb = N("ShaderNodeCombineXYZ"); L(ad.outputs[0], cb.inputs["X"]); L(sp.outputs["Z"], cb.inputs["Y"])
    bt = N("ShaderNodeTexBrick"); L(cb.outputs["Vector"], bt.inputs["Vector"]); bt.offset = 0.0
    bt.inputs["Scale"].default_value = 1.0; bt.inputs["Brick Width"].default_value = plate[0]; bt.inputs["Row Height"].default_value = plate[1]
    bt.inputs["Mortar Size"].default_value = 0.006
    c0 = rk.lin(base)
    bt.inputs["Color1"].default_value = tuple(x * 0.85 for x in c0) + (1,); bt.inputs["Color2"].default_value = tuple(min(1, x * 1.1) for x in c0) + (1,)
    bt.inputs["Mortar"].default_value = tuple(x * 0.35 for x in c0) + (1,)
    vo = N("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 40.0; L(tc.outputs["Object"], vo.inputs["Vector"])
    n1 = N("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 3.0; n1.inputs["Detail"].default_value = 5; L(tc.outputs["Object"], n1.inputs["Vector"])
    mr = N("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.5; mr.inputs["From Max"].default_value = 0.75; mr.inputs["To Max"].default_value = 0.5
    L(n1.outputs["Fac"], mr.inputs["Value"])
    mx = N("ShaderNodeMix"); mx.data_type = 'RGBA'; L(mr.outputs["Result"], mx.inputs["Factor"]); L(bt.outputs["Color"], mx.inputs["A"])
    mx.inputs["B"].default_value = tuple(x * 0.55 for x in c0) + (1,)
    L(mx.outputs["Result"], b.inputs["Base Color"]); b.inputs["Metallic"].default_value = 0.9
    rr = N("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.28; rr.inputs["To Max"].default_value = 0.5; L(n1.outputs["Fac"], rr.inputs["Value"])
    L(rr.outputs["Result"], b.inputs["Roughness"])
    hb = N("ShaderNodeMath"); hb.operation = 'ADD'; L(vo.outputs["Distance"], hb.inputs[0]); L(bt.outputs["Fac"], hb.inputs[1])
    bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35; bp.inputs["Distance"].default_value = 0.004
    L(hb.outputs[0], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    m["base"] = list(c0); rk._mats[name] = m
    return m


# ----------------------------------------------------------------------------- materials
BRONZE = bronze_plates("bronze_walls", base=(0.50, 0.36, 0.22))
FLOOR = K.ashlar_mat("painted_floor", (0.62, 0.48, 0.34), block=(0.8, 0.8), joint=0.02, mortar=(0.36, 0.22, 0.16), var=0.18, dark_low=False, floor=True)
KYANOS = K.mat("blue_enamel", (0.10, 0.22, 0.52), "tile", rough=0.25)
GOLD = K.mat("gold", (0.92, 0.70, 0.30), "metal", rough=0.22)
SILVER = K.mat("silver", (0.78, 0.78, 0.76), "metal", rough=0.25)
BEAMS = K.mat("cypress_beams", (0.22, 0.14, 0.09), "wood", rough=0.7)
COLUMN = K.mat("painted_columns", (0.42, 0.12, 0.08), "wood", rough=0.6)
PLASTER = K.patchy_mat("hearth_plaster", (0.80, 0.74, 0.64), patches=[((0.45, 0.42, 0.40), 0.8, 0.35), ((0.25, 0.22, 0.20), 2.0, 0.15)], rough=0.9)
ASH = K.patchy_mat("ashes", (0.40, 0.38, 0.36), patches=[((0.15, 0.14, 0.13), 6.0, 0.35), ((0.62, 0.60, 0.58), 4.0, 0.25)], rough=0.98)
LOGS = K.mat("logs", (0.30, 0.22, 0.15), "bark", rough=0.9)
EMBER = K.emit_mat("embers", (1.0, 0.35, 0.08), 4.0)
FLAME = K.emit_mat("flame", (1.0, 0.55, 0.18), 3.0)
WOOL_A = K.mat("woven_red", (0.55, 0.14, 0.10), "fabric", rough=0.9)
WOOL_B = K.mat("woven_purple", (0.32, 0.12, 0.30), "fabric", rough=0.9)
WOOL_C = K.mat("woven_saffron", (0.78, 0.58, 0.22), "fabric", rough=0.9)
WOOD = K.mat("olive_wood", (0.42, 0.30, 0.18), "wood", rough=0.6)
IVORY = K.mat("ivory", (0.85, 0.80, 0.68), "plaster", rough=0.4)
CLAY = K.mat("loom_weights", (0.55, 0.38, 0.26), "soil", rough=0.85)
NIGHT = K.mat("night_garden_ground", (0.06, 0.07, 0.05), "grass", rough=0.95)
LEAF = K.leaf_mat("beech", seed=31, name="garden_trees", palette=[(0.10, 0.16, 0.07), (0.13, 0.20, 0.08), (0.08, 0.13, 0.05), (0.15, 0.22, 0.09), (0.11, 0.17, 0.06)])
BARK = K.mat("garden_bark", (0.18, 0.15, 0.12), "bark", rough=0.9)
FRUIT = K.mat("pomegranates", (0.55, 0.10, 0.08), "fabric", rough=0.5)
K.size(BRONZE, 2048, 256); K.size(FLOOR, 2048, 128); K.size(PLASTER, 512, 64)

# ----------------------------------------------------------------------------- the hall
HW, HD, H = 6.0, 5.0, 5.4
rk.room("hall", 2 * HW, 2 * HD, H, BRONZE, FLOOR, ceiling=BEAMS,
        openings=[{"wall": "s", "at": 0.0, "width": 2.4, "height": 3.6, "sill": 0.0}], thickness=0.6)
# the blue-enamel cornice, gold rosettes along it, a gold fillet under it
B = rk._B("cornice")
for (L_, loc, rot) in ((2 * HW, (0, HD - 0.06, H - 0.75), 0), (2 * HW, (0, -HD + 0.06, H - 0.75), 0), (2 * HD, (HW - 0.06, 0, H - 0.75), 90), (2 * HD, (-HW + 0.06, 0, H - 0.75), 90)):
    B.box(KYANOS, (L_, 0.12, 0.5), loc, (0, 0, rot))
    B.box(GOLD, (L_, 0.14, 0.04), (loc[0], loc[1], loc[2] - 0.04), (0, 0, rot))
    B.box(GOLD, (L_, 0.14, 0.04), (loc[0], loc[1], loc[2] + 0.5), (0, 0, rot))
    n = int(L_ / 0.55)
    for i in range(n):
        u = -L_ / 2 + 0.275 + i * L_ / n
        if rot == 0: p = (u, loc[1] + (-0.07 if loc[1] > 0 else 0.07), loc[2] + 0.25)
        else: p = (loc[0] + (-0.07 if loc[0] > 0 else 0.07), u, loc[2] + 0.25)
        B.ball(GOLD, 0.07, p, squash=(1, 0.35, 1) if rot == 0 else (0.35, 1, 1), sub=1)
B.done()
# the roof beams and the smoke-hole over the hearth
BM = rk._B("roof_beams")
for x in np.arange(-HW + 0.6, HW, 1.2):
    BM.box(BEAMS, (0.28, 2 * HD, 0.3), (x, 0, H - 0.3))
BM.done()

# the hearth: a raised round plastered hearth with a painted rim, the fire and its ashes
HC = Vector((0.0, 0.5, 0.0))
pk.cyl("HearthDrum", 1.6, 0.18, (HC.x, HC.y, 0.09), PLASTER, verts=48)
pk.cyl("HearthRim", 1.64, 0.06, (HC.x, HC.y, 0.05), KYANOS, verts=48)
pk.cyl("HearthAsh", 1.0, 0.03, (HC.x, HC.y, 0.19), ASH, verts=32)
F = rk._B("fire")
FC = HC + Vector((0, 0, 0.2))
for k in range(6):
    a = math.radians(30 * k + R.uniform(-10, 10))
    d = Vector((math.cos(a), math.sin(a), 0))
    F.seg(LOGS, tuple(FC - d * 0.45 + Vector((0, 0, 0.05))), tuple(FC + d * 0.45 + Vector((0, 0, 0.12 + 0.03 * (k % 2)))), 0.07, 0.06, 7)
for k in range(18):
    F.ball(EMBER, R.uniform(0.04, 0.07), (FC.x + R.uniform(-0.45, 0.45), FC.y + R.uniform(-0.45, 0.45), FC.z + 0.02), squash=(1.3, 1.0, 0.5), sub=0)
F.done()
# four columns round the hearth: dark red shafts tapering downward, black cushion capitals, gold bands
COLS = [(-2.2, -1.5), (2.2, -1.5), (-2.2, 2.5), (2.2, 2.5)]
for i, (x, y) in enumerate(COLS):
    pk.cyl(f"ColBase{i}", 0.42, 0.18, (x, y, 0.09), K.mat("column_base", (0.66, 0.60, 0.52), "stone", rough=0.8), verts=20)
    pk.cyl(f"ColShaft{i}", 0.3, H - 0.9, (x, y, 0.18 + (H - 0.9) / 2), COLUMN, verts=20, r2=0.36)
    pk.cyl(f"ColNeck{i}", 0.37, 0.08, (x, y, H - 0.68), GOLD, verts=20)
    pk.sphere(f"ColEchinus{i}", 0.5, (x, y, H - 0.55), BEAMS, seg=20, scale=(1, 1, 0.35))
    pk.box(f"ColAbacus{i}", (0.9, 0.9, 0.16), (x, y, H - 0.38), BEAMS)

# ----------------------------------------------------------------------------- the doorway: bronze threshold, silver pillars and lintel, gold doors
DW = 2.4; DH = 3.6
TH = rk._B("doorway")
TH.box(BRONZE, (DW + 0.6, 0.9, 0.16), (0, -HD - 0.1, 0.0))                       # the bronze threshold
for sx in (-1, 1):
    TH.box(SILVER, (0.3, 0.7, DH), (sx * (DW / 2 + 0.15), -HD - 0.0, 0.0))         # silver door-pillars
TH.box(SILVER, (DW + 0.9, 0.75, 0.35), (0, -HD, DH))                              # silver lintel
TH.done()
for sx in (-1, 1):
    # the gold doors, folded back into the hall, studded, with a gold hook
    D = rk._B(f"door{sx}", (sx * DW / 2, -HD + 0.35, 0.16), -55 if sx > 0 else -125)
    D.box(GOLD, (1.18, 0.07, DH - 0.2), (-sx * 0.59 * 0 - 0.59, 0, 0))
    for zz in np.arange(0.3, DH - 0.2, 0.45):
        for xx in np.arange(-1.05, -0.1, 0.3): D.ball(GOLD, 0.03, (xx, 0.05, zz), sub=0)
    D.done()
# the garden beyond the court: dark ground, fruit trees against the night sky
pk.box("GardenGround", (40.0, 30.0, 0.1), (0.0, -HD - 16.0, -0.05), NIGHT)
for i, (x, y, h) in enumerate(((-3.5, -11.0, 4.5), (2.5, -12.5, 5.0), (-0.5, -16.0, 5.5), (5.5, -15.0, 4.0), (-6.5, -14.5, 5.0), (1.0, -20.0, 6.0))):
    K.tree(f"garden_tree{i}", (x, y, 0.0), h, h * 0.4, BARK, LEAF, seed=60 + i, trunk_frac=0.35, nlimbs=4, detail=0.6, card=1.1, fill=40, lobes=4)
    for k in range(10):
        pk.sphere(f"Fruit{i}_{k}", 0.06, (x + R.uniform(-1.2, 1.2), y + R.uniform(-1.2, 1.2), h * R.uniform(0.45, 0.8)), FRUIT if i % 2 else GOLD, seg=6)
rk.box("garden_wall", (40.0, 0.5, 2.2), (0.0, -HD - 26.0, 0.0), K.mat("garden_wall", (0.20, 0.18, 0.15), "stone", rough=0.9))
K.sky((0.025, 0.035, 0.08), (0.06, 0.07, 0.11), strength=0.8, radius=300, ground_color=(0.015, 0.018, 0.02))

# ----------------------------------------------------------------------------- seats, the royal seats, tables, the loom
SE = rk._B("benches")
for (x0, x1, y, rot) in ((-HW + 0.5, -1.6, -HD + 0.45, 0), (1.6, HW - 0.5, -HD + 0.45, 0), (-HW + 0.5, HW - 0.5, HD - 0.45, 0)):
    SE.box(WOOD, (x1 - x0, 0.55, 0.42), ((x0 + x1) / 2, y, 0.0))
    for k, x in enumerate(np.arange(x0 + 0.6, x1, 1.3)):
        SE.box([WOOL_A, WOOL_B, WOOL_C][k % 3], (1.1, 0.6, 0.05), (x, y, 0.42), (0, 0, R.uniform(-3, 3)))
        SE.box([WOOL_A, WOOL_B, WOOL_C][k % 3], (1.1, 0.04, 0.3), (x, y - 0.3 if y > 0 else y + 0.3, 0.17))
for x in (-HW + 0.45, HW - 0.45):
    SE.box(WOOD, (0.55, 2 * HD - 1.8, 0.42), (x, 0.0, 0.0))
    for k, y in enumerate(np.arange(-HD + 1.6, HD - 1.0, 1.3)):
        SE.box([WOOL_C, WOOL_A, WOOL_B][k % 3], (0.6, 1.1, 0.05), (x, y, 0.42))
SE.done()
# the royal seats by the hearth (Alcinous's and Arete's), ivory-inlaid, with footstools
def throne(name, x, y, yaw):
    T = rk._B(name, (x, y, 0.0), yaw)
    T.box(WOOD, (0.7, 0.62, 0.5), (0, 0, 0.0))
    T.box(WOOD, (0.7, 0.1, 1.25), (0, -0.28, 0.0))
    T.box(IVORY, (0.5, 0.02, 0.7), (0, -0.225, 0.5))
    T.box(GOLD, (0.72, 0.12, 0.06), (0, -0.28, 1.25))
    for sx in (-1, 1): T.box(WOOD, (0.08, 0.55, 0.25), (sx * 0.33, 0.0, 0.5))
    T.box(WOOL_B, (0.66, 0.6, 0.06), (0, 0.0, 0.5))
    T.box(WOOD, (0.5, 0.32, 0.12), (0, 0.48, 0.0))
    T.done()
throne("seat_alcinous", 2.4, 0.4, 90 + 180 + 0)
throne("seat_arete", -1.0, 2.6, 160)
# low tables with a mixing-bowl and cups
for k, (x, y) in enumerate(((-4.0, -2.8), (4.0, -2.8), (-4.2, 2.5), (4.2, 2.5))):
    pk.box(f"Table{k}", (1.0, 0.6, 0.05), (x, y, 0.5), WOOD)
    for sx in (-1, 1): pk.box(f"TableLeg{k}{sx}", (0.06, 0.5, 0.48), (x + sx * 0.42, y, 0.24), WOOD)
    pk.lathe(f"Cup{k}", [(0.0, 0.0), (0.04, 0.0), (0.02, 0.03), (0.02, 0.07), (0.07, 0.1), (0.06, 0.11), (0.0, 0.1)], (x - 0.25, y, 0.525), GOLD, steps=14)
pk.lathe("MixingBowl", [(0.0, 0.0), (0.14, 0.0), (0.1, 0.1), (0.16, 0.18), (0.36, 0.35), (0.42, 0.55), (0.40, 0.58), (0.36, 0.56), (0.0, 0.5)], (3.2, -3.4, 0.0), BRONZE, steps=28)
# Arete's loom against the west wall: two uprights, the beam, the web half-woven, the loom weights, spindles
LM = rk._B("loom", (-HW + 0.55, 1.3, 0.0), -90)
for sx in (-1, 1): LM.box(WOOD, (0.1, 0.1, 2.3), (sx * 0.8, 0.0, 0.0), (8, 0, 0))
LM.box(WOOD, (1.8, 0.12, 0.12), (0, -0.15, 2.15))
LM.box(WOOL_C, (1.5, 0.02, 1.1), (0, -0.12, 1.05), (8, 0, 0))
for k in range(18):
    LM.ball(CLAY, 0.05, (-0.72 + k * 0.085, 0.05, 0.42), squash=(0.8, 0.5, 1.2), sub=0)
LM.done()
for k in range(3):
    pk.tube(f"Spindle{k}", [Vector((-HW + 1.2 + k * 0.1, 0.3 + k * 0.05, 0.46)), Vector((-HW + 1.25 + k * 0.1, 0.0 + k * 0.05, 0.47))], 0.008, WOOD, sides=5)
    pk.sphere(f"Whorl{k}", 0.025, (-HW + 1.21 + k * 0.1, 0.25 + k * 0.05, 0.465), CLAY, seg=8, scale=(1, 1, 0.5))

# ----------------------------------------------------------------------------- the golden torch-bearers on their pedestals
TORCHES = []
for i, (x, y) in enumerate(((-HW + 0.9, -2.0), (-HW + 0.9, 3.3), (HW - 0.9, -2.0), (HW - 0.9, 3.3))):
    side = -1 if x < 0 else 1
    pk.box(f"Pedestal{i}", (0.6, 0.6, 1.0), (x, y, 0.5), K.mat("pedestal_stone", (0.70, 0.66, 0.58), "stone", rough=0.7), bevel=0.02)
    pk.box(f"PedestalCap{i}", (0.7, 0.7, 0.08), (x, y, 1.04), GOLD)
    # a herm: a tapering gilded pillar with a youth's head (archaic, almond eyes and long hair suggested), arms holding a torch
    T = rk._B(f"herm{i}", (x, y, 1.08), 90 * side)
    T.box(GOLD, (0.24, 0.22, 1.25), (0, 0, 0.0))
    T.box(GOLD, (0.36, 0.24, 0.12), (0, 0, 1.25))
    T.ball(GOLD, 0.075, (0, 0, 1.43), squash=(0.9, 1.0, 1.15), sub=2)
    T.ball(GOLD, 0.08, (0, -0.02, 1.47), squash=(0.95, 0.9, 0.8), sub=1)
    T.box(GOLD, (0.16, 0.06, 0.2), (0, -0.06, 1.3))
    T.seg(GOLD, (0.15, 0.04, 1.3), (0.22, 0.2, 1.15), 0.04, 0.035, 6)
    T.seg(GOLD, (0.22, 0.2, 1.15), (0.2, 0.28, 1.35), 0.035, 0.03, 6)
    T.done()
    hand = Vector(T.at(0.2, 0.28, 1.35))
    top = hand + Vector((0, 0, 0.55))
    pk.tube(f"Torch{i}", [hand - Vector((0, 0, 0.25)), top], 0.035, LOGS, sides=6)
    pk.cyl(f"TorchHead{i}", 0.06, 0.16, tuple(top), K.mat("pitch", (0.06, 0.04, 0.03), "soil", rough=0.8), verts=8)
    pk.cyl(f"TorchFlame{i}", 0.08, 0.38, tuple(top + Vector((0, 0, 0.27))), FLAME, verts=8, r2=0.005)
    TORCHES.append(top + Vector((0, 0, 0.18)))

# ----------------------------------------------------------------------------- light, sound, reader
rk.lamp("hearth", (FC.x, FC.y, FC.z + 0.6), power=320, color=(1.0, 0.62, 0.32), radius=0.4)
for i, t in enumerate(TORCHES):
    rk.lamp(f"torch{i}", tuple(t + Vector((0, 0, 0.2))), power=70, color=(1.0, 0.74, 0.46), radius=0.12)
rk.lamp("moon", (4.0, -HD - 10.0, 12.0), power=3000, color=(0.55, 0.65, 1.0), radius=2.0)
w = bpy.context.scene.world
K.fx("fire", "hearth", tuple(FC + Vector((0, 0, 0.05))), 0.5)
for i, t in enumerate(TORCHES): K.fx("torch", str(i), tuple(t + Vector((0, 0, 0.1))), 0.1)
K.sound("fire", "hearth", tuple(FC + Vector((0, 0, 0.3))))
K.sound("crowd", "hall", (0.0, 3.5, 1.2))
E, D = K.reader((-1.3, 1.3, 0.18), (0.0, -HD), eye=1.55)
K.reader_cams()
K.cam("hall", (3.8, -3.6, 1.8), (-1.0, 2.0, 1.4), lens=18)
K.cam("torchbearer", (-3.2, -0.6, 1.8), (-HW + 0.9, -2.0, 2.0), lens=26)
K.finish()
