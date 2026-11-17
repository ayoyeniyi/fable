"""
Fable step-in room: the White Rabbit's upstairs room (Alice's Adventures in Wonderland, chapter 4).

"By this time she had found her way into a tidy little room with a table in the window, and on it (as she had hoped) a
fan and two or three pairs of tiny white kid gloves ... her eye fell upon a little bottle that stood near the
looking-glass. There was no label this time ..."  ... "a shower of little pebbles came rattling in at the window, and
some of them hit her in the face ... the pebbles were all turning into little cakes as they lay on the floor"

A small upstairs bedroom-cum-dressing-room in a neat Victorian cottage at the edge of a wood, about 1865, at human
scale so the reader feels large in it: about 4 x 4 m under a low 2.4 m ceiling. Whitewashed plaster, dark oak boards, a
rag rug. One sash window (the lower sash pushed up) with a small table in it holding a folded fan and three pairs of
tiny white kid gloves; a chintz-skirted dressing table with a gilt looking-glass and, beside it, a little unlabelled
bottle; a narrow cast-iron grate on a brick hearth, cold; a ledged door that opens inwards; a rush-seated chair, a
small chest of drawers. Pebbles scattered on the boards under the window, some already turned into little cakes.
Through the window: the back garden below, with glass cucumber-frames (a few panes broken), a clipped hedge and the
wood beyond, and two ladders lashed together leaning against the house wall, their top just showing at the sill.
No people, no lizard, no animals.

Light: soft spring daylight through the single window; the grate is cold.
Reader: in the middle of the room, facing the window table, the looking-glass to the right, the fireplace to the left.

  blender -b -P blender/build_white_rabbit_house.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_white_rabbit_house.py -- --render --samples 48 --res 1400
  blender -b -P blender/build_white_rabbit_house.py -- --export
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b5 as S
import pride_kit as K
import pride_interior as I
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, MB, anchor, sound, light_obj)

SID = "white-rabbit-house"
ARGS = S.setup(SID, seed=1865)
scene = K.scene
scene.cycles.max_bounces = 8; scene.cycles.diffuse_bounces = 5
rng = random.Random(1865)

R = I.Room(-2.0, 2.0, -2.0, 2.0, 2.4, t=0.32)
GROUND = -2.9                  # the garden, one storey below
WIN_X = 0.15
READER = Vector((0.05, -0.55, 0))

# ----------------------------------------------------------------------------- materials
def whitewash(name="M_Whitewash"):
    """Limewash on uneven plaster: off-white, patchy, a little grey near the floor, faint trowel waves."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1500, -400))
    n = noise_(nt, co, 1.1, 6, 0.6, loc=(-1200, 0)); n2 = noise_(nt, co, 9.0, 4, 0.6, loc=(-1200, -200))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.35, 0.7, 0, 1, (-1000, 0)), c4(K.srgb((0.84, 0.83, 0.78))), c4(K.srgb((0.90, 0.89, 0.85))), (-800, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, n2.outputs["Fac"], 0.3, 0.7, 0.95, 1.03, (-1000, -200)), (-650, 0))
    low = maprange(nt, s.outputs["Z"], 0.0, 0.45, 0.12, 0.0, (-1000, -400))
    col = mix_rgb(nt, 'MULTIPLY', low, col, (0.62, 0.6, 0.56, 1), (-500, 0))
    col = K.ao_mul(nt, col, 0.3, 0.35, (-400, -500))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    bump_from(nt, b, math_(nt, 'ADD', n.outputs["Fac"], math_(nt, 'MULTIPLY', n2.outputs["Fac"], 0.3, (-900, -600)), (-700, -600)), 0.25, 0.006)
    return m

M_WASH = whitewash()
M_FLOOR = I.boards_mat("M_OakBoards", light=(0.17, 0.10, 0.055), dark=(0.065, 0.038, 0.02), width=0.17, axis='Y', wax=0.5)
M_TIMBER = wood("M_DarkOak", base=(0.12, 0.07, 0.035), dark=(0.04, 0.025, 0.012), light=(0.20, 0.13, 0.07), scale=1.2, rough=(0.45, 0.7), grain_dir=(1, 1, 10), coat=0.1)
M_PAINTWD = I.joinery_mat("M_PaintedWood", K.srgb((0.78, 0.76, 0.69)), rough=0.45)
M_BRICK = noisy("M_HearthBrick", [K.srgb((0.42, 0.19, 0.12)), K.srgb((0.52, 0.25, 0.16)), K.srgb((0.36, 0.17, 0.11))], scale=9, rough=0.9, bump=0.4)
M_IRON = noisy("M_Iron", [(0.03, 0.03, 0.032), (0.055, 0.052, 0.05), (0.04, 0.036, 0.034)], scale=30, rough=(0.5, 0.75))
M_SOOT = plain("M_Soot", (0.015, 0.013, 0.012), rough=0.95)
M_PANE = new_mat("M_Pane")[0]
nt = M_PANE.node_tree
for n_ in list(nt.nodes): nt.nodes.remove(n_)
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); nt.links.new(tr.outputs["BSDF"], o_.inputs["Surface"])


def chintz(name="M_Chintz"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 9.0, 'F1', (-1200, 200)); n = noise_(nt, co, 16.0, 4, 0.6, distortion=1.4, loc=(-1200, -100))
    bloom = maprange(nt, v.outputs["Distance"], 0.07, 0.15, 1, 0, (-950, 200)); leaf = maprange(nt, n.outputs["Fac"], 0.56, 0.6, 0, 1, (-950, -100))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', leaf, 0.7, (-800, -100)), c4(K.srgb((0.90, 0.86, 0.76))), c4(K.srgb((0.42, 0.54, 0.40))), (-700, 0))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', bloom, 0.85, (-800, 200)), col, c4(K.srgb((0.80, 0.42, 0.46))), (-550, 0))
    col = K.ao_mul(nt, col, 0.1, 0.4, (-400, -400))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.7; b.inputs["Sheen Weight"].default_value = 0.4
    return m
M_CHINTZ = chintz()
M_MUSLIN = noisy("M_Muslin", [K.srgb((0.92, 0.91, 0.87)), K.srgb((0.86, 0.85, 0.80))], scale=60, rough=0.85, bump=0.1)
M_GILT = I.gilt("M_Gilt")
M_MIRROR = plain("M_Mirror", (0.6, 0.62, 0.62), rough=0.04, metallic=1.0)
M_KID = noisy("M_WhiteKid", [K.srgb((0.93, 0.92, 0.88)), K.srgb((0.88, 0.87, 0.83))], scale=80, rough=0.55, bump=0.2, bump_dist=0.0006)
M_FAN = noisy("M_FanPaper", [K.srgb((0.86, 0.80, 0.70)), K.srgb((0.78, 0.66, 0.60))], scale=30, rough=0.6)
M_IVORY = plain("M_Ivory", K.srgb((0.88, 0.84, 0.74)), rough=0.35)
M_BOTTLE = new_mat("M_BottleGlass")[0]
b_ = M_BOTTLE.node_tree.nodes["Principled BSDF"]
b_.inputs["Base Color"].default_value = (0.55, 0.62, 0.58, 1); b_.inputs["Roughness"].default_value = 0.05; b_.inputs["Transmission Weight"].default_value = 0.85
M_CORK = noisy("M_Cork", [K.srgb((0.58, 0.42, 0.26)), K.srgb((0.48, 0.34, 0.2))], scale=60, rough=0.9)
M_PEBBLE = noisy("M_Pebbles", [K.srgb((0.52, 0.50, 0.46)), K.srgb((0.40, 0.38, 0.35)), K.srgb((0.62, 0.58, 0.52))], scale=40, rough=0.7, bump=0.3)
M_CAKE = noisy("M_LittleCakes", [K.srgb((0.72, 0.50, 0.26)), K.srgb((0.82, 0.62, 0.36)), K.srgb((0.62, 0.40, 0.20))], scale=50, rough=0.75, bump=0.6, bump_dist=0.001)
M_CURRANT = None
M_RUSH = noisy("M_Rush", [K.srgb((0.62, 0.54, 0.34)), K.srgb((0.50, 0.42, 0.25))], scale=40, rough=0.85, stretch=(1, 8, 1), bump=0.4)
M_RAG = noisy("M_RagRug", [K.srgb((0.42, 0.22, 0.18)), K.srgb((0.24, 0.28, 0.34)), K.srgb((0.52, 0.46, 0.34)), K.srgb((0.30, 0.16, 0.14))], scale=22, rough=0.95, bump=0.6, bump_dist=0.003, warp=0.4)
M_CHINA = plain("M_China", K.srgb((0.92, 0.92, 0.90)), rough=0.12)
M_BRASS = plain("M_Brass", (0.70, 0.52, 0.27), rough=0.32, metallic=1.0)

# ----------------------------------------------------------------------------- walls, window, door, floor, ceiling
I.sash_window("Win", R, 'N', R.x1 - WIN_X, 0.9, 0.78, 1.25, M_PAINTWD, M_PANE, M_PAINTWD, panes=(2, 4), curtain_mat=None)
DOOR_Y = -0.9
I.six_panel_door("Door", R, 'W', R.y1 - DOOR_Y, 0.8, 1.95, M_PAINTWD, M_PAINTWD, M_BRASS, open_deg=0, hinge_left=True)
I.build_walls(R, M_WASH)
box("Floor", (R.x1 - R.x0 + 0.7, R.y1 - R.y0 + 0.7, 0.04), (0, 0, -0.02), M_FLOOR)
box("Ceiling", (R.x1 - R.x0 + 0.7, R.y1 - R.y0 + 0.7, 0.04), (0, 0, R.h + 0.02), M_WASH)
for k, x in enumerate((-1.2, 0.0, 1.2)):        # two exposed ceiling joists' worth: a beam across the low ceiling
    if k == 1: box("CeilingBeam", (R.x1 - R.x0, 0.16, 0.14), (0, 0.35, R.h - 0.07), M_TIMBER, bevel=0.01)
I.moulding_runs(R, "Skirting", I.skirting_profile(0.14), 0.0, M_PAINTWD)
# the window: the lower sash pushed up (shown as a second frame over the upper one), white muslin curtains on a rod
o, a, n, L = R.wall_frame('N'); wb = o + a * (R.x1 - WIN_X)
for side in (-1, 1):
    c = I.curtain_panel(f"Curtain{side}", wb, a, n, side * 0.75, side * 0.42, 0.78 + 1.25 + 0.18, 0.7, M_MUSLIN, folds=4, depth=0.03)
    K.add_sway(c, lambda p: max(0.0, min(1.0, (2.2 - p.z) / 1.5)) * 0.8)
cyl("CurtainRod", 0.012, 1.7, tuple(wb + n * 0.08 + Vector((0, 0, 0.78 + 1.25 + 0.2))), M_TIMBER, verts=8, rot=(0, math.pi / 2, 0))
# raised lower sash: a frame lying over the top half, set a little inside
fp = wb - n * (R.t * 0.62) + n * 0.06
for (sx, sz, ua, zz) in ((0.06, 0.62, -0.42, 1.73), (0.06, 0.62, 0.42, 1.73), (0.9, 0.05, 0, 2.02), (0.9, 0.07, 0, 1.44), (0.016, 0.6, 0, 1.73)):
    box(f"LowerSash{ua}{zz}{sx}", (sx, 0.04, sz), tuple(fp + a * ua + Vector((0, 0, zz))), M_PAINTWD)

# ----------------------------------------------------------------------------- the table in the window: fan and tiny white kid gloves
WT = Frame((WIN_X, R.y1 - 0.38), math.pi)
WT.box("WinTableTop", (0.75, 0.42, 0.025), (0, 0, 0.7), M_TIMBER, bevel=0.005)
WT.box("WinTableApron", (0.66, 0.34, 0.08), (0, 0, 0.645), M_TIMBER, bevel=0.003)
for sx in (-1, 1):
    for sy in (-1, 1):
        lathe(f"WinTableLeg{sx}{sy}", [(0.0, 0.0), (0.016, 0.0), (0.02, 0.1), (0.014, 0.3), (0.022, 0.42), (0.018, 0.6), (0.0, 0.6)], WT.p(sx * 0.31, sy * 0.15, 0), M_TIMBER, steps=8)
TZ = 0.7125
def glove(name, c, yaw, size=0.085, curl=0.0, mat=M_KID):
    """A tiny kid glove lying flat: palm, four fingers and a thumb, a short gauntlet; built as a thin slab outline."""
    F_ = Frame(c[:2], yaw, z=c[2])
    outline = [(-0.25, -0.5), (0.25, -0.5), (0.3, -0.05), (0.42, 0.05), (0.48, 0.2), (0.4, 0.22), (0.27, 0.12), (0.27, 0.35), (0.22, 0.62), (0.15, 0.62),
               (0.14, 0.36), (0.1, 0.36), (0.09, 0.72), (0.02, 0.72), (0.0, 0.37), (-0.04, 0.37), (-0.06, 0.68), (-0.13, 0.68), (-0.14, 0.35),
               (-0.18, 0.34), (-0.21, 0.55), (-0.27, 0.55), (-0.28, 0.1)]
    vs = []; fs = []
    nO = len(outline)
    for zz in (0.0, 0.006):
        for (x, y) in outline:
            lift = curl * max(0.0, y - 0.3) * 0.1
            vs.append(F_.p(x * size, y * size, zz + lift + 0.001))
    bm = bmesh.new()
    vv = [bm.verts.new(v) for v in vs]
    bm.faces.new(vv[:nO]); bm.faces.new(vv[nO:][::-1])
    for i in range(nO):
        j = (i + 1) % nO; bm.faces.new((vv[i], vv[j], vv[nO + j], vv[nO + i]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:2])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat); K.link(o)
    return o
for k, (dx, dy, yaw) in enumerate(((0.08, 0.06, 0.3), (0.12, 0.08, 0.45), (0.2, -0.06, -0.2), (0.24, -0.04, -0.1), (0.0, -0.1, 1.2), (0.02, -0.12, 1.35))):
    glove(f"Glove{k}", WT.p(dx, dy, TZ + 0.0035 * (k % 2)), WT.yaw + yaw + (math.pi if k % 2 else 0), curl=0.2 * (k % 3))
# the fan: folded ivory sticks with a painted leaf, lying a little open
FN = WT.p(-0.18, 0.02, TZ)
for k in range(9):
    ang = WT.yaw + math.radians(-30 + 7 * k + 90)
    d = Vector((math.cos(ang), math.sin(ang), 0))
    p0 = Vector(FN) + Vector((0, 0, 0.002 + 0.0007 * k)); p1 = p0 + d * 0.22
    box(f"FanStick{k}", (0.008, 0.22, 0.0018), tuple((p0 + p1) / 2), M_IVORY, rot=(0, 0, ang - math.pi / 2))
fv = []; ff = []
for k in range(9):
    ang = WT.yaw + math.radians(-30 + 7 * k + 90); d = Vector((math.cos(ang), math.sin(ang), 0))
    fv += [tuple(Vector(FN) + d * 0.1 + Vector((0, 0, 0.009 + 0.002 * (k % 2)))), tuple(Vector(FN) + d * 0.215 + Vector((0, 0, 0.009 + 0.004 * (k % 2))))]
    if k: ff.append((2 * k - 2, 2 * k, 2 * k + 1, 2 * k - 1))
mesh_from("FanLeaf", fv, ff, M_FAN, smooth=False)
anchor("room.windowTable", WT.p(0, 0, 0))

# ----------------------------------------------------------------------------- the dressing table: chintz skirt, looking-glass, the little bottle
DT = Frame((R.x1 - 0.32, 0.55), math.pi / 2)       # against the east wall, facing -X (into the room)
DT.box("DressTop", (0.95, 0.48, 0.025), (0, 0, 0.74), M_TIMBER, bevel=0.004)
# skirt: a gathered frill of chintz round the front and sides
sv = []; sf = []
NS = 46
for i in range(NS + 1):
    t = i / NS
    if t < 0.25: x, y = -0.48, -0.24 + 0.48 * (1 - t / 0.25)
    elif t < 0.75: x, y = -0.48 + 0.96 * (t - 0.25) / 0.5, -0.24
    else: x, y = 0.48, -0.24 + 0.48 * (t - 0.75) / 0.25
    f = 0.018 * math.sin(i * 2.4)
    for zz, out in ((0.74, 0.0), (0.0, 0.03)):
        nrm = Vector((0 if 0.25 <= t <= 0.75 else (-1 if t < 0.25 else 1), -1 if 0.25 <= t <= 0.75 else 0, 0))
        sv.append(DT.p(x + nrm.x * (f + out), y + nrm.y * (f + out) - 0.015 * (0.25 <= t <= 0.75), zz))
    if i: sf.append((2 * i - 2, 2 * i, 2 * i + 1, 2 * i - 1))
# (local -y is the front: Frame +Y points into the room... the frame faces +Y; the skirt front is at local y = +0.24)
sv = [DT.p(*(Matrix.Rotation(math.pi, 3, 'Z') @ (Vector(v) - DT.o).to_3d() if False else Vector((0, 0, 0)))) for v in []] or sv
skirt = mesh_from("DressSkirt", sv, sf, M_CHINTZ, smooth=True)
for v in skirt.data.vertices:            # flip the frill to the room side
    lv = Matrix.Rotation(-DT.yaw, 3, 'Z') @ (v.co - DT.o)
    lv.y = -lv.y
    v.co = DT.o + Matrix.Rotation(DT.yaw, 3, 'Z') @ lv
DT.box("DressValance", (0.99, 0.5, 0.06), (0, 0, 0.73), M_CHINTZ, bevel=0.01)
# the looking-glass: an oval swing mirror in a gilt frame on a small stand
MG = Vector(DT.p(0, -0.1, 0.765))
MF = Frame((MG.x, MG.y), DT.yaw, z=MG.z)
MF.box("GlassStand", (0.42, 0.18, 0.05), (0, 0, 0.0 + (0.05) / 2), M_TIMBER, bevel=0.008)
for sx in (-1, 1): MF.box(f"GlassPost{sx}", (0.025, 0.025, 0.42), (sx * 0.2, 0, 0.04 + (0.42) / 2), M_TIMBER)
ov = []; of = []; gv = []
for i in range(28):
    a_ = 2 * math.pi * i / 28
    for rr, lst in ((1.0, ov), (0.86, ov)):
        pass
ring_o = []; ring_i = []
for i in range(28):
    a_ = 2 * math.pi * i / 28
    ring_o.append(MF.p(math.cos(a_) * 0.17, 0.0, 0.33 + math.sin(a_) * 0.22))
    ring_i.append(MF.p(math.cos(a_) * 0.145, 0.004, 0.33 + math.sin(a_) * 0.19))
fv = ring_o + ring_i; ff = [(i, (i + 1) % 28, 28 + (i + 1) % 28, 28 + i) for i in range(28)]
fr = mesh_from("GlassFrame", fv, ff, M_GILT); fr.modifiers.new("Solid", 'SOLIDIFY').thickness = 0.025
gl = mesh_from("GlassMirror", [MF.p(0, 0.002, 0.33)] + ring_i, [(0, 1 + (i + 1) % 28, 1 + i) for i in range(28)], M_MIRROR)
# the little bottle, no label, near the looking-glass
BT = Vector(DT.p(-0.3, 0.05, 0.7525))
lathe("Bottle", [(0.0, 0.0), (0.022, 0.0), (0.024, 0.006), (0.024, 0.06), (0.015, 0.075), (0.008, 0.085), (0.008, 0.1), (0.0, 0.1)], tuple(BT), M_BOTTLE, steps=14)
lathe("BottleLiquid", [(0.0, 0.002), (0.02, 0.002), (0.02, 0.045), (0.0, 0.045)], tuple(BT), plain("M_Cordial", K.srgb((0.55, 0.22, 0.30)), rough=0.1), steps=12)
cyl("BottleCork", 0.0075, 0.018, tuple(BT + Vector((0, 0, 0.105))), M_RUSH, verts=8)
# a hairbrush and a small china tray on the dressing table
DT.box("Brush", (0.05, 0.16, 0.025), (0.28, 0.0, 0.765), M_TIMBER, bevel=0.008)
lathe("ChinaTray", [(0.0, 0.0), (0.07, 0.0), (0.08, 0.012), (0.0, 0.006)], DT.p(0.15, 0.12, 0.7525), M_CHINA, steps=16)
anchor("room.lookingGlass", tuple(MG))

# ----------------------------------------------------------------------------- the narrow fireplace (west wall... south-west), cold
FPW = Frame((R.x0, 0.75), -math.pi / 2)     # local +Y points +X (into the room)
FPW.box("Breast", (1.0, 0.18, R.h), (0, 0.0, R.h / 2), M_WASH)
FPW.box("HearthBricks", (0.86, 0.4, 0.04), (0, 0.3, 0.02), M_BRICK, bevel=0.003)
for sx in (-1, 1):
    FPW.box(f"Jamb{sx}", (0.12, 0.06, 0.82), (sx * 0.31, 0.12, 0.41), M_PAINTWD, bevel=0.004)
FPW.box("Mantel", (0.84, 0.17, 0.035), (0, 0.15, 0.84), M_PAINTWD, bevel=0.006)
FPW.box("Lintel", (0.62, 0.05, 0.12), (0, 0.12, 0.76), M_PAINTWD, bevel=0.004)
FPW.box("GratePlate", (0.5, 0.03, 0.7), (0, 0.095, 0.35), M_IRON)
FPW.box("GrateMouth", (0.32, 0.03, 0.32), (0, 0.105, 0.26), M_SOOT)
for k in range(4): FPW.box(f"GrateBar{k}", (0.32, 0.012, 0.012), (0, 0.16, 0.14 + k * 0.04), M_IRON)
FPW.box("GrateBasket", (0.32, 0.08, 0.02), (0, 0.13, 0.12), M_IRON)
for k in range(7):     # a few cold cinders
    sphere(f"Cinder{k}", rng.uniform(0.012, 0.022), FPW.p(rng.uniform(-0.12, 0.12), rng.uniform(0.11, 0.15), 0.15), M_SOOT, seg=5)
# on the narrow mantel shelf: a pair of china dogs? no (no animals): a candlestick and a small clock-less vase
I.candlestick("MantelStick", FPW.p(-0.28, 0.15, 0.8575), M_BRASS, plain("M_Wax", K.srgb((0.93, 0.91, 0.85)), rough=0.45), height=0.18, candle_h=0.14, flame=False)
lathe("MantelVase", [(0.0, 0.0), (0.03, 0.0), (0.04, 0.05), (0.02, 0.1), (0.03, 0.13), (0.0, 0.13)], FPW.p(0.25, 0.15, 0.8575), M_CHINA, steps=12)
FPW.box("FireBox", (0.22, 0.15, 0.14), (0.38, 0.32, 0.0), M_BRASS) if False else None
anchor("room.fireplace", FPW.p(0, 0.3, 0))

# ----------------------------------------------------------------------------- chair, chest of drawers, rug, hooks
def rush_chair(name, x, y, yaw):
    F = Frame((x, y), yaw)
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = 0.43 if sy > 0 else 0.92
            F.cyl(f"{name}Leg{sx}{sy}", 0.016, h, (sx * 0.19, sy * 0.18, h / 2), M_TIMBER, verts=8)
    F.box(f"{name}Seat", (0.4, 0.38, 0.03), (0, 0, 0.42), M_RUSH, bevel=0.01)
    for z in (0.62, 0.76, 0.88): F.box(f"{name}Slat{z}", (0.38, 0.02, 0.05), (0, -0.18, z), M_TIMBER, bevel=0.006)
    for z in (0.15,): F.box(f"{name}Stretch{z}", (0.38, 0.015, 0.02), (0, 0.18, z), M_TIMBER)
rush_chair("Chair", -1.2, 1.35, math.radians(-160))
CH = Frame((R.x1 - 0.26, -1.25), math.pi / 2)
CH.box("ChestCarcase", (0.85, 0.45, 0.8), (0, 0, 0.04 + (0.8) / 2), M_TIMBER, bevel=0.006)
CH.box("ChestTop", (0.9, 0.48, 0.025), (0, 0, 0.84), M_TIMBER, bevel=0.005)
for k, (zz, hh) in enumerate(((0.12, 0.2), (0.35, 0.2), (0.58, 0.2))):
    CH.box(f"Drawer{k}", (0.78, 0.02, hh - 0.02), (0, 0.23, zz + (hh - 0.02) / 2), M_TIMBER, bevel=0.004)
    for sx in (-1, 1): sphere(f"DrawerKnob{k}{sx}", 0.014, CH.p(sx * 0.22, 0.25, zz + hh / 2 - 0.01), M_TIMBER, seg=8)
CH.box("Washbowl", (0.0, 0.0, 0.0), (0, 0, 0), M_TIMBER) if False else None
lathe("Basin", [(0.0, 0.0), (0.06, 0.0), (0.15, 0.06), (0.16, 0.075), (0.15, 0.075), (0.055, 0.008), (0.0, 0.008)], CH.p(0.05, 0, 0.8525), M_CHINA, steps=24)
lathe("Jug", [(0.0, 0.0), (0.05, 0.0), (0.065, 0.06), (0.06, 0.13), (0.04, 0.17), (0.05, 0.2), (0.0, 0.2)], CH.p(0.05, 0, 0.86), M_CHINA, steps=16)
box("RagRug", (1.5, 0.95, 0.012), (0.1, -0.35, 0.006), M_RAG, bevel=0.006)
# hooks by the door with a little coat? (no: nothing of the Rabbit himself) - a towel on the chest's side rail
CH.box("TowelRail", (0.02, 0.4, 0.02), (0.44, 0.0, 0.72), M_TIMBER)
CH.box("Towel", (0.012, 0.3, 0.42), (0.46, 0.0, 0.5), M_MUSLIN, bevel=0.004)
# a small sampler picture and a text on the whitewash
I.picture("Sampler", R, 'S', 1.6, 1.55, 0.32, 0.38, M_TIMBER, noisy("M_Sampler", [K.srgb((0.84, 0.78, 0.64)), K.srgb((0.62, 0.40, 0.36)), K.srgb((0.42, 0.50, 0.40))], scale=60, rough=0.9))

# ----------------------------------------------------------------------------- the pebbles under the window, some turned into little cakes
for k in range(26):
    x = WIN_X + rng.gauss(0, 0.45); y = R.y1 - 0.25 - abs(rng.gauss(0, 0.65))
    if (Vector((x, y)) - READER.xy).length < 0.45 or abs(x - WIN_X) < 0.4 and y > R.y1 - 0.62: continue
    if rng.random() < 0.4:
        r_ = rng.uniform(0.022, 0.03)
        lathe(f"Cake{k}", [(0.0, 0.0), (r_, 0.0), (r_ * 1.02, r_ * 0.4), (r_ * 0.8, r_ * 0.7), (0.0, r_ * 0.8)], (x, y, 0.0), M_CAKE, steps=10)
        for j in range(3):
            a_ = rng.uniform(0, 6.28); sphere(f"Currant{k}{j}", 0.004, (x + math.cos(a_) * r_ * 0.5, y + math.sin(a_) * r_ * 0.5, r_ * 0.68), M_SOOT, seg=5)
    else:
        r_ = rng.uniform(0.01, 0.022)
        sphere(f"Pebble{k}", r_, (x, y, r_ * 0.55), M_PEBBLE, seg=6, scale=(rng.uniform(0.8, 1.3), rng.uniform(0.8, 1.2), 0.65))

# ----------------------------------------------------------------------------- outside: the garden below, cucumber-frames, hedge, the two ladders
def garden_ground(name="M_Garden"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1500, 0))
    n = noise_(nt, co, 0.8, 5, 0.6, loc=(-1300, 200)); n2 = noise_(nt, co, 7.0, 4, 0.6, loc=(-1300, 0))
    grass = mix_rgb(nt, 'MIX', maprange(nt, n2.outputs["Fac"], 0.3, 0.7, 0, 1, (-1100, 200)), (0.10, 0.18, 0.05, 1), (0.22, 0.30, 0.09, 1), (-900, 200))
    bed = mix_rgb(nt, 'MIX', maprange(nt, n2.outputs["Fac"], 0.3, 0.7, 0, 1, (-1100, -100)), (0.10, 0.07, 0.045, 1), (0.18, 0.13, 0.08, 1), (-900, -100))
    isbed = maprange(nt, s.outputs["Y"], 3.6, 3.8, 0, 1, (-1100, -300))
    isbed = math_(nt, 'MULTIPLY', isbed, maprange(nt, s.outputs["Y"], 6.4, 6.6, 1, 0, (-1100, -400)), (-950, -350))
    col = mix_rgb(nt, 'MIX', isbed, grass, bed, (-700, 100))
    path = math_(nt, 'MULTIPLY', maprange(nt, s.outputs["Y"], 2.2, 2.35, 0, 1, (-1100, -600)), maprange(nt, s.outputs["Y"], 3.1, 3.25, 1, 0, (-1100, -700)), (-950, -650))
    col = mix_rgb(nt, 'MIX', path, col, (0.42, 0.37, 0.28, 1), (-500, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    return m
M_GARDEN = garden_ground()
box("GardenGround", (24, 22, 0.1), (0, R.y1 + 10.5, GROUND - 0.05), M_GARDEN)
# the house wall outside (seen at the window reveal edges) is the wall box itself; a brick plinth below the window
M_EXTWALL = noisy("M_Render", [K.srgb((0.82, 0.78, 0.68)), K.srgb((0.74, 0.70, 0.60))], scale=2, rough=0.9, bump=0.3)
box("ExtWall", (8.0, 0.1, 6.0), (0, R.y1 + R.t + 0.05, GROUND + 3.0 - 0.1), M_EXTWALL) if False else None
# cucumber-frames: low timber boxes with sloping glazed lights, some panes broken
M_HEDGE = noisy("M_Hedge", [K.srgb((0.08, 0.14, 0.05)), K.srgb((0.16, 0.24, 0.08)), K.srgb((0.11, 0.18, 0.06))], scale=6, rough=0.85, bump=0.8, bump_dist=0.03, warp=0.5)
M_FRAMEWD = noisy("M_FrameWood", [K.srgb((0.42, 0.40, 0.34)), K.srgb((0.34, 0.32, 0.27)), K.srgb((0.50, 0.48, 0.40))], scale=5, rough=0.9, stretch=(1, 1, 6), bump=0.3)
M_FRAMEGLASS = plain("M_FrameGlass", K.srgb((0.62, 0.70, 0.72)), rough=0.08)
for k, (fx_, fy_) in enumerate(((-1.6, 4.6), (0.1, 4.7), (1.8, 4.55))):
    F = Frame((fx_, fy_), rng.uniform(-0.05, 0.05), z=GROUND)
    F.box(f"CFrameBack{k}", (1.5, 0.05, 0.42), (0, 0.55, 0 + (0.42) / 2), M_FRAMEWD)
    F.box(f"CFrameFront{k}", (1.5, 0.05, 0.24), (0, -0.55, 0 + (0.24) / 2), M_FRAMEWD)
    for sx in (-1, 1): F.box(f"CFrameSide{k}{sx}", (0.05, 1.12, 0.3), (sx * 0.73, 0, 0 + (0.3) / 2), M_FRAMEWD)
    for j in range(3):
        lx = -0.5 + 0.5 * j
        broken = (k, j) in ((0, 1), (2, 0), (1, 2))
        F.box(f"CLightBar{k}{j}", (0.04, 1.16, 0.03), (lx - 0.24, 0, 0.34), M_FRAMEWD, rx=math.atan2(0.18, 1.1))
        if not broken:
            F.box(f"CLight{k}{j}", (0.46, 1.12, 0.006), (lx, 0, 0.34), M_FRAMEGLASS, rx=math.atan2(0.18, 1.1))
        else:     # a broken light: shards left in the frame, the rest fallen in among the plants
            F.box(f"CShard{k}{j}", (0.2, 0.3, 0.006), (lx - 0.1, 0.38, 0.39), M_FRAMEGLASS, rx=math.atan2(0.18, 1.1))
            for q in range(3):
                F.box(f"CShardF{k}{j}{q}", (rng.uniform(0.06, 0.14), rng.uniform(0.06, 0.12), 0.005), (lx + rng.uniform(-0.15, 0.15), rng.uniform(-0.3, 0.2), 0.08), M_FRAMEGLASS, rx=rng.uniform(-0.3, 0.3))
    # cucumber leaves inside (dark green lumps)
    for q in range(6):
        sphere(f"Cuke{k}{q}", rng.uniform(0.08, 0.14), F.p(rng.uniform(-0.55, 0.55), rng.uniform(-0.35, 0.35), 0.08), M_HEDGE, seg=8, scale=(1.3, 1.1, 0.5))
# the hedge at the garden's end and the wood beyond (backdrop)
hg = box("Hedge", (16, 1.0, 1.6), (0, R.y1 + 8.5, GROUND + (1.6) / 2), M_HEDGE)
hsub = hg.modifiers.new("Sub", 'SUBSURF'); hsub.levels = 2
hd = hg.modifiers.new("Disp", 'DISPLACE'); tex = bpy.data.textures.new("HedgeN", 'CLOUDS'); tex.noise_scale = 0.4; hd.texture = tex; hd.strength = 0.25
for k in range(9):      # trees of the wood beyond the hedge: trunks and big leaf masses (seen only through the window)
    x = -7 + 1.8 * k + rng.uniform(-0.5, 0.5); y = R.y1 + 12 + rng.uniform(0, 4)
    h = rng.uniform(4, 7)
    cyl(f"WoodTrunk{k}", rng.uniform(0.15, 0.3), h * 0.6, (x, y, GROUND + h * 0.3), M_FRAMEWD, verts=8)
M_WOODVIEW = new_mat("M_WoodView")[0]
ntw = M_WOODVIEW.node_tree; bw = ntw.nodes["Principled BSDF"]
cw = obj_coords(ntw); nn1 = noise_(ntw, cw, 0.5, 6, 0.65, 0.5, (-900, 0)); nn2 = noise_(ntw, cw, 4.0, 5, 0.6, loc=(-900, -200))
col = mix_rgb(ntw, 'MIX', maprange(ntw, nn2.outputs["Fac"], 0.35, 0.65, 0, 1, (-700, -200)), (0.04, 0.07, 0.03, 1), (0.22, 0.32, 0.10, 1), (-500, 0))
sep_ = sep_xyz(ntw, cw, (-900, 300))
top_ = math_(ntw, 'ADD', GROUND + 3.0, math_(ntw, 'MULTIPLY', nn1.outputs["Fac"], 5.0, (-700, 300)), (-600, 300))
sky_ = mix_rgb(ntw, 'MIX', maprange(ntw, sep_.outputs["Z"], 2, 10, 0, 1, (-600, 500)), (0.80, 0.84, 0.86, 1), (0.50, 0.64, 0.82, 1), (-450, 500))
isw = maprange(ntw, math_(ntw, 'SUBTRACT', top_, sep_.outputs["Z"], (-500, 300)), 0, 0.1, 0, 1, (-400, 300))
col = mix_rgb(ntw, 'MIX', isw, sky_, col, (-300, 100))
ntw.links.new(col, bw.inputs["Emission Color"]); bw.inputs["Emission Strength"].default_value = 1.0; bw.inputs["Base Color"].default_value = (0, 0, 0, 1)
vv = []; vf = []
for j in range(5):
    for i in range(17):
        a_ = math.radians(-70 + 140 * i / 16); r = 16
        vv.append((r * math.sin(a_) * 1.2, R.y1 + 2 + r * math.cos(a_) * 0.9, GROUND - 1 + 22 * j / 4))
for j in range(4):
    for i in range(16): vf.append((j * 17 + i, (j + 1) * 17 + i, (j + 1) * 17 + i + 1, j * 17 + i + 1))
view = mesh_from("WoodView", vv, vf, M_WOODVIEW)
view.visible_shadow = False; view.visible_diffuse = False; view.visible_glossy = False
# the two ladders tied together, leaning against the house wall beside the window, their top just above the sill
LD = Vector((WIN_X + 0.1, R.y1 + R.t + 0.02, 0.0))
foot = Vector((LD.x + 0.1, LD.y + 1.25, GROUND)); top = Vector((LD.x, LD.y + 0.05, 0.98))
ax = (top - foot).normalized(); side = Vector((1, 0, 0))
L_ = (top - foot).length
M_LADDER = noisy("M_LadderWood", [K.srgb((0.52, 0.44, 0.32)), K.srgb((0.42, 0.35, 0.25))], scale=4, rough=0.85, stretch=(1, 1, 8))
for sx in (-1, 1):
    tube(f"LadderRail{sx}", [foot + side * sx * 0.2, top + side * sx * 0.2], 0.03, M_LADDER, sides=6)
for k in range(1, int(L_ / 0.28)):
    p = foot + ax * (k * 0.28)
    tube(f"Rung{k}", [p - side * 0.2, p + side * 0.2], 0.016, M_LADDER, sides=5)
mid = foot + ax * (L_ * 0.5)
for sx in (-1, 1):       # the lashing where the two ladders join
    for q in range(4):
        tube(f"Lash{sx}{q}", [mid + side * sx * 0.2 + ax * (q * 0.03 - 0.05) + Vector((0, -0.04, 0)), mid + side * sx * 0.2 + ax * (q * 0.03 - 0.05) + Vector((0, 0.04, 0))], 0.008, M_RUSH, sides=4)

# ----------------------------------------------------------------------------- light: soft spring daylight from the window (north-ish sky, sun from the side)
sun_dir = Vector((0.55, -0.6, -0.58)).normalized()
light_obj("Lamp.sun", 'SUN', 4.0, (1.0, 0.95, 0.86), (0, 8, 8), direction=tuple(sun_dir), angle=math.radians(2.0))
ld = bpy.data.lights.new("Lamp.windowSky", 'AREA'); ld.energy = 160.0; ld.color = (0.84, 0.90, 1.0); ld.shape = 'RECTANGLE'; ld.size = 0.85; ld.size_y = 1.2
wl = bpy.data.objects.new("Lamp.windowSky", ld); wl.location = tuple(wb + n * 0.05 - n * 0.4 + Vector((0, 0, 1.4))); K.link(wl)
wl.rotation_euler = Vector((0.0, -1.0, -0.3)).to_track_quat('-Z', 'Y').to_euler()
world = bpy.data.worlds.new("Spring"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.66, 0.74, 0.86, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.2

# ----------------------------------------------------------------------------- anchors, sources
S.reader(READER, (WIN_X - READER.x, R.y1 - READER.y))
anchor("scene.centre", (0.0, 0.2, 0.0))
anchor("room.door", tuple(R.at('W', R.y1 - DOOR_Y)))
sound("birds", "garden", (0.0, R.y1 + 6.0, 1.0))
sound("wind-trees", "wood", (-3.0, R.y1 + 14.0, 4.0))
page = S.page_preview()
K.apply_transforms()

E = READER + Vector((0, 0, S.EYE))
cams = S.eye_cams([("Reader", 0), ("Left", -75), ("Right", 75), ("Behind", 180)], dz=-0.7, dist=4.0, extra=[
    ("Page", E, E + Vector((0, 4, -0.7)), 17),
    ("Table", Vector((WIN_X - 0.5, R.y1 - 1.25, 1.35)), Vector(WT.p(0, 0, 0.7)), 30),
    ("Window", Vector((WIN_X - 0.2, R.y1 - 0.9, 1.6)), Vector((WIN_X + 0.4, R.y1 + 4.0, GROUND + 0.5)), 24),
    ("Glass", Vector((0.2, 0.1, 1.4)), Vector(DT.p(-0.15, 0, 0.85)), 28),
])
probs = S.check_reader(ignore=("PagePreview", "WoodView"))
K.print_budget(exclude=("PagePreview",))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.0, captures_dir=ARGS.captures)

if ARGS.export or ARGS.bake:
    S.export(SID, cams, page=page, unlit_emit=("M_WoodView",),
             remove=[o.name for o in bpy.data.objects if o.name.startswith("WindowGlass_")],
             keep_names={"M_Muslin": "cloth.curtain.window", "M_WoodView": "far.woodView"},
             size_for={"M_Whitewash": (2048, 64, 1024), "M_OakBoards": (1024, 128, 1024), "M_DarkOak": (1024, 128, 512), "M_PaintedWood": (1024, 64, 512),
                       "M_Chintz": (512, 64, 256), "M_Muslin": (512, 64, 128), "M_RagRug": (512, 64, 256), "M_Garden": (512, 32, 128),
                       "M_WoodView": (1024,), "M_Hedge": (512, 32, 256), "M_WhiteKid": (256, 32, 128), "M_HearthBrick": (256, 64, 128)},
             default_size=(256, 32, 128))
print("DONE")
