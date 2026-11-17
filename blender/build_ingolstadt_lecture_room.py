"""
Fable step-in room: M. Waldman's lecturing room at the University of Ingolstadt (Frankenstein, Chapter II of the
narrative, book chapter c07).

"... I went into the lecturing room, which M. Waldman entered shortly after. This professor was very unlike his
colleague. He appeared about fifty years of age ... He began his lecture by a recapitulation of the history of
chemistry ... After having made a few preparatory experiments, he concluded with a panegyric upon modern chemistry"
... "whose hands seem only made to dabble in dirt, and their eyes to pore over the microscope or crucible" ... Krempe
"delivered sentences out of a pulpit".

A modest university lecturing room of the 1780s-90s, about 10 x 8 m under a beamed ceiling: dark oak panelling to
shoulder height, whitewash above; plain pine benches with desk-rails in rows facing the front, a central aisle; a
raised lectern like a small pulpit on a dais; before it the long demonstration table with the apparatus of the
preparatory experiments: a small brick furnace with a crucible in its tongs, glass retorts on stands over a spirit lamp,
a receiver, flasks and phials, a mortar, a brass microscope, a balance; a blackboard with a few chalked figures; shelves
of books and stoppered jars of minerals and salts; a green tiled stove in the corner; three tall windows on the east
side with a glimpse over the roofs of the high white steeple of the town. No creature, no anatomy, no electric light.
No people.

Light: grey-white daylight through the tall windows; the spirit lamp under the retort is lit.
Reader: in the aisle among the benches, facing the demonstration table where Waldman speaks.

  blender -b -P blender/build_ingolstadt_lecture_room.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_ingolstadt_lecture_room.py -- --render --samples 32 --res 1280 --cams reader,left,right,behind,table
  blender -b -P blender/build_ingolstadt_lecture_room.py -- --export
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b5 as S
import pride_kit as K
import pride_interior as I
import mobydick_kit as MK
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, anchor, sound, light_obj)

SID = "ingolstadt-lecture-room"
ARGS = S.setup(SID, seed=1790)
scene = K.scene
scene.cycles.max_bounces = 8; scene.cycles.diffuse_bounces = 5
rng = random.Random(1790)

R = I.Room(-4.0, 4.0, -5.0, 5.0, 4.4, t=0.5)          # the front (demonstration table, lectern) at the north end
READER = Vector((0.0, -1.6, 0))

# ----------------------------------------------------------------------------- materials
def whitewash(name="M_Whitewash"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt); n = noise_(nt, co, 1.0, 6, 0.6, loc=(-1200, 0)); n2 = noise_(nt, co, 9.0, 4, 0.6, loc=(-1200, -200))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.35, 0.7, 0, 1, (-1000, 0)), c4(K.srgb((0.80, 0.79, 0.74))), c4(K.srgb((0.88, 0.87, 0.82))), (-800, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, n2.outputs["Fac"], 0.3, 0.7, 0.94, 1.03, (-1000, -200)), (-650, 0))
    col = K.ao_mul(nt, col, 0.4, 0.35, (-400, -500))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    bump_from(nt, b, n.outputs["Fac"], 0.2, 0.006)
    return m
M_WASH = whitewash()
M_OAK = MK.timber_mat("M_OakPanel", base=(0.11, 0.07, 0.04), dark=(0.035, 0.022, 0.013), light=(0.19, 0.12, 0.07), along='Z', rough=(0.35, 0.65), grime=0.3, polish=0.2, seams=('X', 0.55))
M_OAKX = MK.timber_mat("M_OakTrim", base=(0.11, 0.07, 0.04), dark=(0.035, 0.022, 0.013), light=(0.19, 0.12, 0.07), along='X', rough=(0.35, 0.65), grime=0.3, polish=0.2)
M_PINE = MK.timber_mat("M_PineBench", base=(0.36, 0.26, 0.15), dark=(0.14, 0.09, 0.05), light=(0.50, 0.38, 0.24), along='X', rough=(0.5, 0.8), grime=0.5)
M_FLOOR = I.boards_mat("M_FloorBoards", light=(0.30, 0.22, 0.13), dark=(0.13, 0.09, 0.05), width=0.24, axis='Y', wax=0.7)
M_BEAM = MK.timber_mat("M_Beams", base=(0.14, 0.10, 0.06), dark=(0.05, 0.035, 0.02), light=(0.22, 0.16, 0.10), along='X', rough=(0.6, 0.85), grime=0.5)
M_BRICK = noisy("M_FurnaceBrick", [K.srgb((0.46, 0.24, 0.15)), K.srgb((0.36, 0.18, 0.12)), K.srgb((0.52, 0.32, 0.22))], scale=10, rough=0.9, bump=0.4)
M_IRON = MK.iron_mat("M_Iron", rust=0.2)
M_BRASS = plain("M_Brass", K.srgb((0.66, 0.50, 0.24)), rough=0.3, metallic=1.0)
M_GLASS = plain("M_ApparatusGlass", K.srgb((0.66, 0.74, 0.72)), rough=0.06, coat=0.6)
M_GLASSG = plain("M_GreenGlass", K.srgb((0.22, 0.34, 0.26)), rough=0.06, coat=0.6)
M_SLATE = noisy("M_Blackboard", [K.srgb((0.07, 0.08, 0.08)), K.srgb((0.11, 0.12, 0.11)), K.srgb((0.16, 0.17, 0.16))], scale=3, rough=0.85)
M_CHALK = plain("M_Chalk", K.srgb((0.80, 0.80, 0.76)), rough=0.9)
M_TILE = noisy("M_StoveTiles", [K.srgb((0.20, 0.34, 0.24)), K.srgb((0.28, 0.44, 0.32)), K.srgb((0.16, 0.28, 0.20))], scale=6, rough=0.2, bump=0.3, coat=0.4)
M_PAGES = noisy("M_BookPages", [K.srgb((0.80, 0.76, 0.64)), K.srgb((0.72, 0.68, 0.56))], scale=200, rough=0.85, stretch=(1, 1, 30), bump=0.0)
M_SPINES = noisy("M_BookSpines", [K.srgb((0.36, 0.20, 0.11)), K.srgb((0.20, 0.12, 0.07)), K.srgb((0.62, 0.52, 0.36)), K.srgb((0.30, 0.10, 0.07))], scale=30, rough=0.6, stretch=(30, 1, 1), bump=0.2)
M_JARS = noisy("M_SpecimenJars", [K.srgb((0.52, 0.56, 0.50)), K.srgb((0.40, 0.46, 0.40)), K.srgb((0.62, 0.58, 0.46))], scale=12, rough=0.1, coat=0.6)
M_MINERAL = noisy("M_Minerals", [K.srgb((0.52, 0.42, 0.30)), K.srgb((0.30, 0.32, 0.36)), K.srgb((0.62, 0.52, 0.40)), K.srgb((0.20, 0.18, 0.18))], scale=40, rough=0.6, bump=0.5)
M_CLOTH = noisy("M_GreenBaize", [K.srgb((0.14, 0.24, 0.16)), K.srgb((0.18, 0.28, 0.20))], scale=80, rough=0.95, sheen=0.5)
M_PANE = new_mat("M_Pane")[0]
nt = M_PANE.node_tree
for n_ in list(nt.nodes): nt.nodes.remove(n_)
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); nt.links.new(tr.outputs["BSDF"], o_.inputs["Surface"])
M_SASH = I.joinery_mat("M_SashPaint", K.srgb((0.72, 0.70, 0.64)), rough=0.5)
M_FLAME = plain("M_SpiritFlame", (0.0, 0.0, 0.0), emission=(0.45, 0.6, 1.0), strength=6.0)


def town_view(name="M_TownView"):
    """the view from the tall east windows: a pale overcast sky, steep red-brown roofs of Ingolstadt, and above them
    the high white steeple (a slender tower with an onion cupola)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1700, 0)); y, z = s.outputs["Y"], s.outputs["Z"]
    sky = mix_rgb(nt, 'MIX', maprange(nt, z, 3.0, 14.0, 0, 1, (-1400, 400)), (0.86, 0.87, 0.86, 1), (0.66, 0.72, 0.80, 1), (-1200, 400))
    cl = noise_(nt, co, 0.2, 5, 0.6, loc=(-1400, 650)); sky = mix_rgb(nt, 'MIX', maprange(nt, cl.outputs["Fac"], 0.45, 0.65, 0, 0.4, (-1200, 650)), sky, (0.94, 0.94, 0.92, 1), (-1000, 400))
    # roofs: a saw-tooth skyline of steep gables
    gx = math_(nt, 'FRACT', math_(nt, 'DIVIDE', y, 3.4, (-1500, 0)), None, (-1400, 0))
    tri = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', gx, 0.5, (-1300, 0)), None, (-1200, 0))
    rn = noise_(nt, co, 0.35, 2, 0.5, loc=(-1500, -200))
    roof_top = math_(nt, 'ADD', math_(nt, 'ADD', 3.2, math_(nt, 'MULTIPLY', rn.outputs["Fac"], 2.5, (-1300, -200)), (-1150, -200)), math_(nt, 'MULTIPLY', tri, -3.0, (-1100, -50)), (-1000, -100))
    inroof = maprange(nt, math_(nt, 'SUBTRACT', roof_top, z, (-900, -100)), 0.0, 0.05, 0, 1, (-800, -100))
    tile = noise_(nt, co, 3.0, 4, 0.6, loc=(-1100, -400))
    rcol = mix_rgb(nt, 'MIX', maprange(nt, tile.outputs["Fac"], 0.3, 0.7, 0, 1, (-900, -400)), (0.34, 0.18, 0.13, 1), (0.48, 0.28, 0.20, 1), (-750, -400))
    col = mix_rgb(nt, 'MIX', inroof, sky, rcol, (-600, 300))
    # the steeple: a slender white tower at y ~ 1.5, with a darker cupola
    dy = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', y, 1.4, (-1500, -700)), None, (-1400, -700))
    tower = math_(nt, 'MULTIPLY', maprange(nt, dy, 0.55, 0.6, 1, 0, (-1250, -700)), maprange(nt, z, 13.0, 13.1, 1, 0, (-1250, -850)), (-1100, -750))
    cup_r = math_(nt, 'MULTIPLY', maprange(nt, z, 13.0, 15.6, 0.7, 0.0, (-1250, -1000)), maprange(nt, z, 12.9, 13.6, 0.5, 1.0, (-1250, -1150)), (-1100, -1050))
    cupola = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'SUBTRACT', cup_r, dy, (-1000, -1000)), 0.0, 0.03, 0, 1, (-900, -1000)), maprange(nt, z, 12.95, 13.0, 0, 1, (-1000, -1150)), (-800, -1050))
    col = mix_rgb(nt, 'MIX', tower, col, (0.90, 0.89, 0.85, 1), (-450, 300))
    col = mix_rgb(nt, 'MIX', cupola, col, (0.22, 0.28, 0.26, 1), (-350, 300))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1); b.inputs["Emission Strength"].default_value = 1.0
    return m
M_VIEW = town_view()

# ----------------------------------------------------------------------------- the room: walls, tall windows on the east, doors, beamed ceiling
WIN_Y = (-2.8, 0.0, 2.8)
for k, y in enumerate(WIN_Y):
    I.sash_window(f"Win{k}", R, 'E', y - R.y0, 1.2, 1.0, 2.9, M_SASH, M_PANE, M_SASH, panes=(3, 6), curtain_mat=None)
I.six_panel_door("Door", R, 'W', R.y1 - (-3.6), 1.1, 2.4, M_OAK, M_OAKX, M_BRASS, open_deg=0, hinge_left=True)
I.build_walls(R, M_WASH)
box("Floor", (R.x1 - R.x0 + 1.0, R.y1 - R.y0 + 1.0, 0.04), (0, 0, -0.02), M_FLOOR)
box("Ceiling", (R.x1 - R.x0 + 1.0, R.y1 - R.y0 + 1.0, 0.05), (0, 0, R.h + 0.025), M_WASH)
for k in range(6):
    y = R.y0 + 0.9 + k * 1.65
    box(f"Beam{k}", (R.x1 - R.x0, 0.24, 0.28), (0, y, R.h - 0.28 + (0.28) / 2), M_BEAM, bevel=0.02)
# oak panelling to 2.0 m (with the seams of the boards), a capping rail
for w in ('S', 'E', 'N', 'W'):
    o, a, n, L = R.wall_frame(w)
    for k, (u0, u1) in enumerate(I.runs(R, w, 0.0, 2.0)):
        c = o + a * ((u0 + u1) / 2) + n * 0.02 + Vector((0, 0, 1.0))
        box(f"Panel{w}{k}", (abs(a.x) * (u1 - u0) + abs(n.x) * 0.04, abs(a.y) * (u1 - u0) + abs(n.y) * 0.04, 2.0), tuple(c), M_OAK)
I.moulding_runs(R, "PanelCap", [(0.0, 0.0), (0.07, 0.0), (0.07, 0.03), (0.05, 0.06), (0.0, 0.06)], 2.0, M_OAKX, z_band=(1.95, 2.06))

# the view over the roofs to the steeple (unlit backdrop)
vv = []; vf = []
for j in range(5):
    for i in range(13):
        yy = -9 + 18 * i / 12
        vv.append((R.x1 + 9.0 - 0.02 * yy * yy, yy, -2 + 22 * j / 4))
for j in range(4):
    for i in range(12): vf.append((j * 13 + i, j * 13 + i + 1, (j + 1) * 13 + i + 1, (j + 1) * 13 + i))
view = mesh_from("TownView", vv, vf, M_VIEW)
view.visible_shadow = False; view.visible_diffuse = False; view.visible_glossy = False

# ----------------------------------------------------------------------------- the dais, the lectern (pulpit), the blackboard, the demonstration table
DAIS = 0.25
box("Dais", (5.0, 2.0, DAIS), (0, R.y1 - 1.0, 0 + (DAIS) / 2), M_OAKX, bevel=0.01)
LP = Frame((1.4, R.y1 - 0.75), math.pi)
LP.box("PulpitBase", (0.9, 0.8, 1.0), (0, 0, DAIS + (1.0) / 2), M_OAK, bevel=0.01)
LP.box("PulpitDesk", (1.0, 0.45, 0.05), (0, 0.2, DAIS + 1.12 + (0.05) / 2), M_OAKX, bevel=0.01, rx=-0.25)
LP.box("PulpitCap", (1.0, 0.9, 0.06), (0, 0, DAIS + 1.0 + (0.06) / 2), M_OAKX, bevel=0.01)
for k in range(3): LP.box(f"PulpitStep{k}", (0.5, 0.25, DAIS + 0.2 * (k + 1)), (0.0, -0.55 - 0.25 * (2 - k), 0.0 + (DAIS + 0.2 * (k + 1)) / 2), M_OAKX)
I.book("PulpitBook", LP.p(0.0, 0.15, DAIS + 1.18), (0.04, 0.24, 0.32), LP.yaw + 1.57, M_SPINES, M_PAGES, roll=math.pi / 2)
BB = Frame((-0.4, R.y1), math.pi)
BB.box("Blackboard", (2.4, 0.04, 1.2), (0, 0.05, DAIS + 1.05 + (1.2) / 2), M_SLATE)
BB.box("BlackboardFrame", (2.5, 0.06, 0.06), (0, 0.06, DAIS + 2.25 + (0.06) / 2), M_OAKX); BB.box("BlackboardLedge", (2.5, 0.1, 0.04), (0, 0.08, DAIS + 1.03 + (0.04) / 2), M_OAKX)
# chalked figures: a few lines (an alembic diagram and some symbols)
for k in range(9):
    x0 = rng.uniform(-1.0, 0.9); z0 = rng.uniform(DAIS + 1.25, DAIS + 2.1); L = rng.uniform(0.1, 0.35); a = rng.uniform(-0.6, 0.6)
    BB.box(f"Chalk{k}", (L, 0.005, 0.008), (x0, 0.075, z0), M_CHALK, ry=a)
for k in range(12):
    a = 2 * math.pi * k / 12
    BB.box(f"ChalkCircle{k}", (0.07, 0.005, 0.008), (0.55 + 0.12 * math.cos(a), 0.075, DAIS + 1.7 + 0.12 * math.sin(a)), M_CHALK, ry=a + math.pi / 2)

DT = Frame((0.0, R.y1 - 2.35), math.pi)       # the long demonstration table on the floor before the dais, facing the benches
TT = 0.9
DT.box("DemoTop", (3.2, 0.9, 0.06), (0, 0, TT - 0.06 + (0.06) / 2), M_OAKX, bevel=0.008)
DT.box("DemoBaize", (1.2, 0.6, 0.004), (0.9, 0, TT + (0.004) / 2), M_CLOTH)
DT.box("DemoFront", (3.1, 0.04, 0.7), (0, -0.42, 0.12 + (0.7) / 2), M_OAK)
for sx in (-1.5, 1.5):
    for sy in (-0.38, 0.38): DT.box(f"DemoLeg{sx}{sy}", (0.08, 0.08, TT - 0.06), (sx, sy, 0 + (TT - 0.06) / 2), M_OAKX)
# the small brick furnace on the left end, with a crucible held in tongs above its mouth
DT.box("Furnace", (0.5, 0.45, 0.45), (-1.25, 0.05, TT + (0.45) / 2), M_BRICK, bevel=0.01)
DT.box("FurnaceMouth", (0.2, 0.02, 0.14), (-1.25, -0.18, TT + 0.06 + (0.14) / 2), plain("M_Soot", (0.02, 0.018, 0.016), rough=0.95))
cyl("FurnacePipe", 0.06, 1.6, DT.p(-1.25, 0.15, TT + 0.45 + 0.8), M_IRON, verts=10)
lathe("Crucible", [(0.0, 0.0), (0.03, 0.0), (0.045, 0.07), (0.05, 0.08), (0.0, 0.075)], DT.p(-1.25, 0.05, TT + 0.45), plain("M_Crucible", K.srgb((0.62, 0.58, 0.52)), rough=0.8), steps=12)
tube("Tongs", [DT.p(-1.25, -0.05, TT + 0.5), DT.p(-0.9, -0.2, TT + 0.04)], 0.007, M_IRON, sides=4)
# retort on a ring stand over a spirit lamp, its neck into a receiver flask
RT = Vector(DT.p(-0.35, 0.0, TT))
cyl("StandRod", 0.008, 0.6, tuple(RT + Vector((0.18, 0.12, 0.3))), M_IRON, verts=6)
box("StandFoot", (0.18, 0.12, 0.015), tuple(RT + Vector((0.15, 0.1, 0.0))), M_IRON)
tube("StandRing", [tuple(RT + Vector((0.07 * math.cos(a), 0.07 * math.sin(a), 0.2))) for a in [2 * math.pi * k / 12 for k in range(13)]], 0.005, M_IRON, sides=4)
lathe("SpiritLamp", [(0.0, 0.0), (0.04, 0.0), (0.045, 0.03), (0.02, 0.06), (0.008, 0.07), (0.0, 0.07)], tuple(RT), M_GLASS, steps=12)
lathe("SpiritFlame", [(0.0, 0.0), (0.008, 0.01), (0.007, 0.03), (0.0, 0.05)], tuple(RT + Vector((0, 0, 0.072))), M_FLAME, steps=8)
sphere("RetortBulb", 0.08, tuple(RT + Vector((0, 0, 0.28))), M_GLASS, seg=14)
tube("RetortNeck", [RT + Vector((0, 0, 0.33)), RT + Vector((0.08, -0.05, 0.4)), RT + Vector((0.35, -0.25, 0.2))], [0.025, 0.015, 0.008], M_GLASS, sides=8)
sphere("Receiver", 0.07, tuple(RT + Vector((0.42, -0.3, 0.07))), M_GLASSG, seg=12)
# flasks, phials, a mortar, a balance, the microscope, a candle
for k in range(6):
    p = DT.p(0.35 + 0.12 * k + rng.uniform(-0.02, 0.02), 0.15 + rng.uniform(-0.1, 0.1), TT)
    if k % 2: lathe(f"Phial{k}", [(0.0, 0.0), (0.015, 0.0), (0.015, 0.1), (0.008, 0.12), (0.0, 0.12)], p, M_GLASSG if k == 3 else M_GLASS, steps=8)
    else: lathe(f"Flask{k}", [(0.0, 0.0), (0.05, 0.0), (0.06, 0.04), (0.04, 0.09), (0.014, 0.12), (0.014, 0.18), (0.0, 0.18)], p, M_GLASS, steps=12)
lathe("Mortar", [(0.0, 0.0), (0.06, 0.0), (0.07, 0.06), (0.06, 0.07), (0.0, 0.03)], DT.p(1.25, -0.1, TT), plain("M_Marble", K.srgb((0.82, 0.80, 0.76)), rough=0.4), steps=14)
tube("Pestle", [DT.p(1.25, -0.1, TT + 0.04), DT.p(1.3, -0.05, TT + 0.16)], [0.012, 0.016], bpy.data.materials["M_Marble"], sides=6)
# the microscope (brass, on a baize cloth): a pillar, a stage, a tilted body tube with eyepiece and objective
MC = Vector(DT.p(0.9, 0.05, TT))
box("MicroBase", (0.12, 0.12, 0.02), tuple(MC), M_OAKX, bevel=0.003)
cyl("MicroPillar", 0.012, 0.2, tuple(MC + Vector((0, 0.03, 0.12))), M_BRASS, verts=8)
box("MicroStage", (0.07, 0.07, 0.005), tuple(MC + Vector((0, -0.01, 0.1))), M_BRASS)
tube("MicroTube", [MC + Vector((0, -0.01, 0.13)), MC + Vector((0, -0.04, 0.3))], [0.014, 0.018], M_BRASS, sides=10)
cyl("MicroEye", 0.01, 0.03, tuple(MC + Vector((0, -0.045, 0.31))), M_BRASS, verts=8)
sphere("MicroMirror", 0.02, tuple(MC + Vector((0, -0.01, 0.05))), plain("M_Mirror", (0.7, 0.7, 0.7), rough=0.05, metallic=1.0), seg=8, scale=(1, 1, 0.3))
# the balance
BLc = Vector(DT.p(1.45, 0.2, TT))
cyl("BalancePost", 0.006, 0.3, tuple(BLc + Vector((0, 0, 0.15))), M_BRASS, verts=6)
box("BalanceBeam", (0.3, 0.006, 0.006), tuple(BLc + Vector((0, 0, 0.3))), M_BRASS)
for sx in (-1, 1):
    lathe(f"BalancePan{sx}", [(0.0, 0.0), (0.04, 0.0), (0.045, 0.01), (0.0, 0.005)], tuple(BLc + Vector((sx * 0.14, 0, 0.12))), M_BRASS, steps=10)
    tube(f"BalanceStr{sx}", [BLc + Vector((sx * 0.14, 0, 0.3)), BLc + Vector((sx * 0.14, 0, 0.13))], 0.0015, M_BRASS, sides=3)
anchor("room.demoTable", DT.p(0, 0, 0))

# ----------------------------------------------------------------------------- shelves of books and stoppered jars on the north wall, the green tiled stove
def shelves(name, x0, x1):
    F_ = Frame(((x0 + x1) / 2, R.y1 - 0.18), math.pi)
    w = x1 - x0
    F_.box(f"{name}Back", (w, 0.02, 2.4), (0, -0.15, DAIS + (2.4) / 2), M_OAK)
    for sx in (-1, 1): F_.box(f"{name}Side{sx}", (0.04, 0.32, 2.4), (sx * w / 2, 0, DAIS + (2.4) / 2), M_OAKX)
    for k in range(6):
        z = DAIS + 0.05 + k * 0.45
        F_.box(f"{name}Shelf{k}", (w, 0.32, 0.03), (0, 0, z + (0.03) / 2), M_OAKX)
        if k == 5: continue
        if k < 3:
            x = -w / 2 + 0.05
            while x < w / 2 - 0.08:
                t_ = rng.uniform(0.03, 0.07); h_ = rng.uniform(0.24, 0.36)
                F_.box(f"{name}Book{k}_{x:.2f}", (t_, 0.22, h_), (x + t_ / 2, 0.0, z + 0.03 + (h_) / 2), M_SPINES)
                x += t_ + 0.003
        else:
            for j in range(int(w / 0.16)):
                x = -w / 2 + 0.1 + j * 0.16
                lathe(f"{name}Jar{k}_{j}", [(0.0, 0.0), (0.05, 0.0), (0.055, 0.14), (0.03, 0.17), (0.035, 0.2), (0.0, 0.2)], F_.p(x, 0.0, z + 0.03), M_JARS, steps=10)
                if j % 2: sphere(f"{name}Min{k}_{j}", 0.035, F_.p(x, 0.0, z + 0.06), M_MINERAL, seg=6, scale=(1.2, 1, 0.8))
shelves("ShelfL", R.x0 + 0.2, -2.0)
shelves("ShelfR", 2.2, R.x1 - 0.2)
# the tiled stove in the north-west corner (closed: its fire is behind the iron door)
ST = Frame((R.x0 + 0.6, R.y1 - 2.7), -math.pi / 2)
ST.box("StoveBase", (0.95, 0.75, 0.25), (0, 0, 0.0 + (0.25) / 2), M_BRICK, bevel=0.01)
ST.box("StoveBody", (0.85, 0.65, 1.3), (0, 0, 0.25 + (1.3) / 2), M_TILE, bevel=0.02)
ST.box("StoveCornice", (0.95, 0.75, 0.12), (0, 0, 1.55 + (0.12) / 2), M_TILE, bevel=0.02)
ST.box("StoveTop", (0.7, 0.5, 0.6), (0, 0, 1.67 + (0.6) / 2), M_TILE, bevel=0.03)
ST.box("StoveDoor", (0.24, 0.02, 0.22), (0, 0.33, 0.45 + (0.22) / 2), M_IRON)
cyl("StovePipe", 0.08, 1.2, ST.p(0, -0.1, 2.85), M_IRON, verts=10)
FIRE = Vector(ST.p(0, 0.2, 0.55))

# ----------------------------------------------------------------------------- the benches: rows of plain pine benches with desk-rails, a central aisle
for row in range(6):
    y = R.y1 - 4.0 - row * 1.05
    for side in (-1, 1):
        x0, x1 = (0.65, R.x1 - 0.45) if side > 0 else (R.x0 + 0.45, -0.65)
        w = x1 - x0; cx = (x0 + x1) / 2
        box(f"BenchSeat{row}{side}", (w, 0.32, 0.05), (cx, y - 0.25, 0.43 + (0.05) / 2), M_PINE, bevel=0.006)
        box(f"Desk{row}{side}", (w, 0.34, 0.04), (cx, y + 0.2, 0.76 + (0.04) / 2), M_PINE, bevel=0.006, rot=(-0.12, 0, 0))
        box(f"DeskFront{row}{side}", (w, 0.03, 0.35), (cx, y + 0.36, 0.4 + (0.35) / 2), M_PINE)
        for k, x in enumerate((x0 + 0.05, cx, x1 - 0.05)):
            box(f"BenchLeg{row}{side}{k}", (0.05, 0.3, 0.43), (x, y - 0.25, 0.0 + (0.43) / 2), M_PINE)
            box(f"DeskLeg{row}{side}{k}", (0.05, 0.05, 0.74), (x, y + 0.34, 0.0 + (0.74) / 2), M_PINE)
        # a book or a slate left on some desks; an inkwell
        if rng.random() < 0.5:
            I.book(f"DeskBook{row}{side}", (cx + rng.uniform(-1, 1), y + 0.2, 0.79), (0.03, 0.15, 0.22), rng.uniform(0, 6.28), M_SPINES, M_PAGES, roll=math.pi / 2)

# ----------------------------------------------------------------------------- light: grey-white daylight from the east windows
light_obj("Lamp.sun", 'SUN', 1.6, (1.0, 0.96, 0.9), (20, 0, 10), direction=(-1.0, 0.25, -0.55), angle=math.radians(4))
for k, y in enumerate(WIN_Y):
    ld = bpy.data.lights.new(f"Lamp.windowSky{k}", 'AREA'); ld.energy = 260.0; ld.color = (0.88, 0.92, 1.0); ld.shape = 'RECTANGLE'; ld.size = 1.2; ld.size_y = 2.9
    wl = bpy.data.objects.new(f"Lamp.windowSky{k}", ld); wl.location = (R.x1 + 0.1, y, 2.45); K.link(wl)
    wl.rotation_euler = Vector((-1.0, 0.0, -0.3)).to_track_quat('-Z', 'Y').to_euler()
light_obj("Lamp.spirit", 'POINT', 1.5, (0.7, 0.8, 1.0), tuple(RT + Vector((0, 0, 0.1))), shadow_soft_size=0.01)
world = bpy.data.worlds.new("Overcast"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.72, 0.76, 0.82, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors, sources
S.reader(READER, (0, 1))
anchor("scene.centre", DT.p(0, 0, 0))
S.fx("fx.candle.spiritLamp", tuple(RT + Vector((0, 0, 0.075))), 0.01)
sound("fire", "stove", tuple(FIRE))
sound("clock", "hall", (R.x0 - 1.0, R.y1 - (-3.6) * 0 - 8.6, 2.0))
sound("crowd", "corridor", (R.x0 - 1.5, -3.6, 1.6))
page = S.page_preview()
K.apply_transforms()

E = READER + Vector((0, 0, S.EYE))
cams = S.eye_cams([("Reader", 0), ("Left", -80), ("Right", 75), ("Behind", 180)], dz=-0.5, dist=5.0, extra=[
    ("Page", E, E + Vector((0, 5, -0.5)), 17),
    ("Table", Vector((0.6, R.y1 - 4.0, 1.6)), Vector(DT.p(-0.2, 0, TT)), 26),
])
probs = S.check_reader(ignore=("PagePreview",))
K.print_budget(exclude=("PagePreview",))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.0, captures_dir=ARGS.captures)

if ARGS.export or ARGS.bake:
    S.export(SID, cams, page=page, unlit_emit=("M_TownView", "M_SpiritFlame"),
             remove=[o.name for o in bpy.data.objects if o.name.startswith("WindowGlass_")],
             keep_names={"M_TownView": "far.townView", "M_SpiritFlame": "MESH_SpiritFlame"},
             size_for={"M_Whitewash": (2048, 64, 1024), "M_FloorBoards": (1024, 128, 1024), "M_OakPanel": (2048, 128, 1024), "M_OakTrim": (1024, 64, 512),
                       "M_PineBench": (2048, 128, 1024), "M_Beams": (1024, 64, 512), "M_TownView": (1024,), "M_BookSpines": (512, 64, 256),
                       "M_StoveTiles": (512, 64, 256), "M_Blackboard": (512, 32, 128)},
             default_size=(256, 32, 128))
print("DONE")
