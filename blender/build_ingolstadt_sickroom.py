"""
Fable: Victor's sickroom in his lodgings at Ingolstadt, in spring (Frankenstein, chapter V of Victor's narrative, book
c10). A chapter step-in room: built ahead of time, served from the server, downloaded by the headset.

"... the young buds were shooting forth from the trees that shaded my window. It was a divine spring" ... "Here is a
letter that has been lying here some days for you: it is from your cousin, I believe." ... "I wrote, and this exertion
greatly fatigued me" ... "Henry ... had removed all my apparatus from my view." (chapters V-VI of Victor's narrative)

The moment: a soft spring morning in March, the convalescence. A plain student's bedchamber (5 x 4 m): lime-washed
walls, a beamed plaster ceiling, wide scrubbed pine boards, a tiled stove in the corner (cold now), the bed with its
green woollen curtains drawn back, linen sheets and a wool blanket, Elizabeth's letter lying on the coverlet; Clerval's
chair beside the bed; a small oak table under the window with pen, ink and paper and a few pages written; a shelf with
Clerval's books (the Persian, Arabic and Sanskrit grammars) and a jug and basin on a stand. Opposite the bed, a
two-light casement standing open, its muslin curtain stirring, and outside the young buds on the lime trees that shade
the window, the roofs of the old town and the white steeple beyond, in soft daylight. No apparatus of any kind, no
people.

Living scene (docs/LIVING_SCENES.md): veg.leaves.buds (the budding lime branches at the window), cloth.curtain.window,
cloth.curtain.bed, fx.candle.table (a candle in a pewter stick, unlit by day: the flame is Unity's), sound.birds.lime,
sound.clock.stair.

Node names: anchor.reader.entrance (feet on the boards by the bedside), anchor.reader.look (facing the window),
anchor.scene.centre / anchor.room.window, anchor.room.bed, anchor.room.letter, anchor.room.table; light.sun (SUN,
morning, through the window), light.window (AREA, sky light at the opening), light.sky (SUN, outdoor fill);
SkyDome, far.town.

Axes: metres, +Z up. Room x -2.5..2.5, y -2..2; the window in the north (+y) wall, the bed against the south wall,
the reader at its foot facing north.

Run headless (one Blender at a time, CPU):
  blender -b -P blender/build_ingolstadt_sickroom.py -- --cpu --render --quick --res 900 --cams reader
  blender -b -P blender/build_ingolstadt_sickroom.py -- --cpu --render --samples 40 --res 1280 --captures captures/blender/ingolstadt-sickroom
  blender -b -P blender/build_ingolstadt_sickroom.py -- --cpu --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
import pride_interior as I
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, anchor, sound, light_obj, camera, link)
ARGS = K.setup("ingolstadt-sickroom", "out/ingolstadt-sickroom", 1790, "IngolstadtSickroom", default_samples=40)
import scene_kit_b2 as B
OUT = K.OUT; scene = K.scene
scene.cycles.max_bounces = 10; scene.cycles.diffuse_bounces = 6
rng = random.Random(1790)

EYE = 1.55
R = I.Room(-2.5, 2.5, -2.0, 2.0, 2.85, t=0.55)
READER = Vector((0.55, -0.35, 0.0))
LOOK_AT = Vector((0.05, 2.0, 0.0))
WIN_X, WIN_W, WIN_SILL, WIN_H = 0.0, 1.15, 0.85, 1.45
SUN_DIR = Vector((0.35, 0.75, 0.55)).normalized()          # towards the sun: the morning sun north-east-ish, through the window

# ----------------------------------------------------------------------------- materials
M_WALL = I.paint_mat("M_LimeWash", K.srgb((0.80, 0.78, 0.71)), rough=0.92, dirt=0.12)
M_CEIL = I.paint_mat("M_Ceiling", K.srgb((0.82, 0.80, 0.74)), rough=0.92, dirt=0.0)
M_FLOOR = I.boards_mat("M_PineBoards", light=(0.42, 0.30, 0.17), dark=(0.20, 0.13, 0.07), width=0.26, axis='Y', wax=0.15)
M_BEAM = wood("M_Beams", base=(0.20, 0.13, 0.07), dark=(0.08, 0.05, 0.025), light=(0.28, 0.19, 0.11), scale=0.8, rough=(0.55, 0.75))
M_OAK = wood("M_Oak", base=(0.22, 0.14, 0.07), dark=(0.09, 0.055, 0.025), light=(0.32, 0.22, 0.12), scale=1.4, rough=(0.35, 0.55), coat=0.15)
M_LINEN = noisy("M_Linen", [K.srgb((0.86, 0.84, 0.78)), K.srgb((0.80, 0.78, 0.71))], scale=60, rough=0.85, bump=0.15, sheen=0.3)
M_BLANKET = noisy("M_WoolBlanket", [K.srgb((0.42, 0.36, 0.26)), K.srgb((0.50, 0.43, 0.31))], scale=30, rough=0.95, bump=0.3, sheen=0.4)
M_BEDCURT = noisy("M_BedCurtain", [K.srgb((0.28, 0.38, 0.30)), K.srgb((0.34, 0.45, 0.36))], scale=25, rough=0.9, bump=0.1, sheen=0.4)
M_MUSLIN = noisy("M_Muslin", [K.srgb((0.88, 0.87, 0.82)), K.srgb((0.82, 0.81, 0.76))], scale=80, rough=0.9, bump=0.05)
M_PAPER = noisy("M_Paper", [K.srgb((0.86, 0.82, 0.70)), K.srgb((0.80, 0.76, 0.64))], scale=60, rough=0.85, bump=0.02)
M_INK = plain("M_Ink", (0.01, 0.01, 0.012), rough=0.2)
M_PEWTER = noisy("M_Pewter", [(0.30, 0.30, 0.29), (0.42, 0.42, 0.40)], scale=8, rough=0.35, metallic=0.7, bump=0.1)
M_WAX = plain("M_Wax", K.srgb((0.92, 0.89, 0.80)), rough=0.45)
M_GLASS = plain("M_PaneGlass", (0.6, 0.65, 0.65), rough=0.04, transmission=0.9)
M_STOVE = noisy("M_StoveTiles", [K.srgb((0.30, 0.42, 0.36)), K.srgb((0.36, 0.48, 0.42)), K.srgb((0.26, 0.36, 0.30))], scale=4, rough=0.25, coat=0.5, bump=0.2)
M_JUG = plain("M_Faience", K.srgb((0.85, 0.84, 0.80)), rough=0.2, coat=0.5)
M_QUILL = plain("M_Quill", K.srgb((0.85, 0.82, 0.74)), rough=0.6)
BOOKC = [noisy(f"M_Calf{i}", [K.srgb(c), K.srgb(tuple(v * 1.2 for v in c))], scale=14, rough=0.5, bump=0.2) for i, c in enumerate(((0.36, 0.20, 0.11), (0.30, 0.10, 0.08), (0.20, 0.22, 0.14)))]
M_PAGES = noisy("M_Pages", [K.srgb((0.80, 0.76, 0.64)), K.srgb((0.72, 0.68, 0.56))], scale=200, rough=0.85, stretch=(1, 1, 30), bump=0.0)
B.SPRAY_KINDS["buds"] = ([(0.30, 0.42, 0.10), (0.38, 0.48, 0.14), (0.26, 0.36, 0.09), (0.45, 0.50, 0.18)], 2, 7.0, 'broad', (0.3, [(0.45, 0.20, 0.12), (0.55, 0.28, 0.15)], 3.0))
IMG_BUDS = B.spray_atlas("A_BudSprays", "buds", 71)
M_BUDS = K.image_mat("M_BudSprays", IMG_BUDS, rough=0.6, alpha=True, spec=0.3)
M_BARK = B.bark_mat("M_LimeBark", base=(0.16, 0.15, 0.13), dark=(0.06, 0.055, 0.05), light=(0.24, 0.23, 0.21), fissure=True, green=0.3)
def town_mat(name="M_FarTown"):
    """the view from the window: steep red-tiled roofs and gables of the old town in soft morning haze, the high white
    steeple, a pale spring sky (emission: an unlit backdrop)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-1600, 0)); s = sep_xyz(nt, co, (-1400, 0)); x = s.outputs["X"]; z = s.outputs["Z"]
    hn = noise_(nt, node(nt, "ShaderNodeCombineXYZ", (-1300, -300)).outputs[0], 1.0, 2, 0.5, loc=(-1100, -300))
    cmb = hn.inputs["Vector"].links[0].from_node; nt.links.new(math_(nt, 'MULTIPLY', x, 0.25, (-1400, -300)), cmb.inputs["X"])
    roofs = math_(nt, 'ADD', 4.0, math_(nt, 'MULTIPLY', math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', math_(nt, 'MULTIPLY', x, 0.28, (-1200, 300)), None, (-1050, 300)), 0.5, (-900, 300)), None, (-750, 300)), -6.0, (-600, 300)), (-450, 300))
    roofs = math_(nt, 'ADD', roofs, math_(nt, 'MULTIPLY', hn.outputs["Fac"], 4.0, (-900, -300)), (-400, 100))
    steeple = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', x, 6.0, (-1200, 600)), None, (-1050, 600)), 1.2, 0.9, 0.0, 1.0, (-900, 600)), 22.0, (-750, 600))
    spire = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', x, 6.0, (-1200, 750)), None, (-1050, 750)), 0.6, 0.0, 0.0, 1.0, (-900, 750)), 30.0, (-750, 750))
    top = math_(nt, 'MAXIMUM', roofs, math_(nt, 'MAXIMUM', steeple, spire, (-600, 650)), (-300, 400))
    isb = maprange(nt, math_(nt, 'SUBTRACT', top, z, (-200, 400)), -0.1, 0.1, 0.0, 1.0, (-50, 400))
    isst = math_(nt, 'MULTIPLY', isb, maprange(nt, math_(nt, 'SUBTRACT', math_(nt, 'MAXIMUM', steeple, spire, (-450, 800)), z, (-300, 800)), -0.1, 0.1, 0.0, 1.0, (-150, 800)), (0, 700))
    sky = mix_rgb(nt, 'MIX', maprange(nt, z, 0, 40, 0, 1, (-200, 0)), c4((0.80, 0.84, 0.88)), c4((0.50, 0.64, 0.85)), (100, 0))
    rc = mix_rgb(nt, 'MIX', maprange(nt, hn.outputs["Fac"], 0.3, 0.7, 0, 1, (-200, -500)), c4((0.42, 0.20, 0.13)), c4((0.55, 0.32, 0.22)), (100, -300))
    rc = mix_rgb(nt, 'MIX', 0.35, rc, c4((0.70, 0.72, 0.76)), (250, -300))    # haze
    col = mix_rgb(nt, 'MIX', isb, sky, rc, (400, 0))
    col = mix_rgb(nt, 'MIX', isst, col, c4((0.86, 0.85, 0.82)), (550, 0))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1); b.inputs["Emission Strength"].default_value = 1.0
    return m
M_TOWN = town_mat()

# ----------------------------------------------------------------------------- the shell: walls, the casement opening, a door, floor, beamed ceiling
I.sash_window("Casement", R, 'N', 2.5 - WIN_X, WIN_W, WIN_SILL, WIN_H, M_OAK, M_GLASS, M_OAK, panes=(2, 3)) if False else R.openings['N'].append((2.5 - WIN_X, WIN_W, WIN_SILL, WIN_SILL + WIN_H, "window"))
DOOR_U = 2.0 + 1.3
R.openings['E'].append((DOOR_U, 0.9, 0.0, 2.05, "door"))
I.build_walls(R, M_WALL)
box("Floor", (5.2, 4.2, 0.04), (0, 0, -0.02), M_FLOOR)
box("Ceiling", (5.2, 4.2, 0.05), (0, 0, R.h + 0.025), M_CEIL)
for k in range(5): box(f"Beam{k}", (0.16, 4.0, 0.18), (-2.0 + k * 1.0, 0, R.h - 0.09), M_BEAM, bevel=0.01)
I.moulding_runs(R, "Skirting", I.skirting_profile(0.14), 0.0, M_BEAM)
# the casement: frame in the reveal, two leaves standing open into the room, small panes, a muslin curtain
WY = R.y1
box("WinSill", (WIN_W + 0.2, 0.32, 0.05), (WIN_X, WY + 0.1, WIN_SILL - 0.025), M_OAK)
for s in (-1, 1): box(f"WinJamb{s}", (0.07, 0.12, WIN_H), (WIN_X + s * (WIN_W / 2 - 0.035), WY + 0.2, WIN_SILL + WIN_H / 2), M_OAK)
box("WinHead", (WIN_W, 0.12, 0.07), (WIN_X, WY + 0.2, WIN_SILL + WIN_H - 0.035), M_OAK)
box("WinMullion", (0.05, 0.12, WIN_H), (WIN_X, WY + 0.2, WIN_SILL + WIN_H / 2), M_OAK)
for s in (-1, 1):
    ang = math.radians(86 if s < 0 else 84); hinge = Vector((WIN_X + s * (WIN_W / 2 - 0.07), WY + 0.14, 0))
    d = Vector((-s * math.cos(ang), -math.sin(ang), 0)); lw = WIN_W / 2 - 0.08; yaw = math.atan2(d.y, d.x)
    c = hinge + d * lw / 2
    box(f"Leaf{s}_Glass", (lw, 0.01, WIN_H - 0.12), (c.x, c.y, WIN_SILL + WIN_H / 2), M_GLASS, rot=(0, 0, yaw))
    for t in (0.0, 1.0): box(f"Leaf{s}_Stile{t}", (0.04, 0.04, WIN_H - 0.1), tuple(hinge + d * (0.02 + t * (lw - 0.04)) + Vector((0, 0, WIN_SILL + WIN_H / 2))), M_OAK, rot=(0, 0, yaw))
    for j in range(4): box(f"Leaf{s}_Rail{j}", (lw, 0.035, 0.03), (c.x, c.y, WIN_SILL + 0.06 + j * (WIN_H - 0.12) / 3), M_OAK, rot=(0, 0, yaw))
cm = K.MB()
for j in range(8):
    t = j / 7; z = WIN_SILL + WIN_H + 0.12 - t * (WIN_H + 0.1)
    row = []
    for i in range(13):
        u = i / 12; x = WIN_X - WIN_W / 2 - 0.35 + u * 0.55; y = WY - 0.06 - 0.03 * math.sin(u * 20) * (0.5 + t)
        row.append(cm.vert((x, y, z), (u, t), t ** 1.2))
    if j: [cm.face(prev[i], prev[i + 1], row[i + 1], row[i]) for i in range(12)]
    prev = row
cm.build("cloth.curtain.window", M_MUSLIN)
cyl("CurtainRod", 0.012, WIN_W + 0.9, (WIN_X, WY - 0.06, WIN_SILL + WIN_H + 0.14), M_PEWTER, verts=8, rot=(0, math.pi / 2, 0))
# the backdrop beyond: the town and its white steeple (unlit), the budding lime branches across the window
mesh_from("far.town", [(-60, 70, -5), (60, 70, -5), (60, 70, 60), (-60, 70, 60)], [(0, 1, 2, 3)], M_TOWN, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
LIME = B.tree("LimeA", -2.2, WY + 3.5, 11.0, 4.5, "elm", 501, M_BARK, M_BUDS, nlimbs=6, cards_per_tip=2, card_size=0.9, fill=120) if False else None
B.set_ground(lambda x, y: -4.0, (READER.x, READER.y, EYE))     # the ground below the window is a storey down
L1 = B.tree("LimeA", -2.6, WY + 3.2, 13.0, 4.2, "elm", 501, M_BARK, M_BUDS, nlimbs=6, cards_per_tip=2, card_size=0.85, fill=110)
L2 = B.tree("LimeB", 0.4, WY + 4.6, 12.0, 3.4, "elm", 502, M_BARK, M_BUDS, nlimbs=6, detail=0.9, cards_per_tip=3, card_size=1.2, fill=140)
box("StreetBelow", (40.0, 30.0, 0.1), (0, WY + 15.0, -4.05), noisy("M_Cobbles", [(0.25, 0.23, 0.20), (0.33, 0.31, 0.27)], scale=20, rough=0.8, bump=0.4))
box("HouseOpposite", (40.0, 1.0, 9.0), (0, WY + 30.0, 0.5), I.paint_mat("M_OppositeHouse", K.srgb((0.82, 0.76, 0.62)), rough=0.9))
for k in range(8): box(f"OppWin{k}", (0.9, 0.1, 1.3), (-14 + k * 4.0, WY + 29.45, 0.5 + (k % 2) * 0.0), plain("M_OppWindow", (0.04, 0.05, 0.06), rough=0.2))
for k in range(8): box(f"OppWinUp{k}", (0.9, 0.1, 1.3), (-14 + k * 4.0, WY + 29.45, 3.0), plain("M_OppWindow", (0.04, 0.05, 0.06), rough=0.2))
# the door (east wall, closed)
box("Door", (0.05, 0.86, 2.0), (R.x1 - 0.03, R.y0 + DOOR_U, 1.0), M_OAK)
for z in (0.45, 1.45): box(f"DoorPanel{z}", (0.06, 0.6, 0.6), (R.x1 - 0.04, R.y0 + DOOR_U, z), M_OAK, bevel=0.02)
box("DoorFrame", (0.08, 1.06, 2.15), (R.x1 - 0.01, R.y0 + DOOR_U, 1.075), M_BEAM)

# ----------------------------------------------------------------------------- the bed (south wall), curtains drawn back, the letter on the coverlet
BX, BY = -1.1, R.y0 + 1.05
for (lx, ly) in ((-0.55, -1.0), (0.55, -1.0), (-0.55, 1.0), (0.55, 1.0)):
    box(f"BedPost{lx}{ly}", (0.08, 0.08, 2.1), (BX + lx, BY + ly * 0.0 + (ly * 1.0 if False else 0) + (-0.95 if ly < 0 else 0.95) * 1.0 * (1 if False else 0) + (ly * 0.95), 1.05), M_OAK, bevel=0.01) if False else None
for sx in (-1, 1):
    for sy in (-1, 1):
        box(f"BedPost{sx}{sy}", (0.08, 0.08, 2.1), (BX + sx * 0.6, BY + sy * 0.98, 1.05), M_OAK, bevel=0.01)
for sx in (-1, 1): box(f"Tester{sx}", (0.06, 2.0, 0.12), (BX + sx * 0.6, BY, 2.1), M_OAK)
for sy in (-1, 1): box(f"TesterE{sy}", (1.26, 0.06, 0.12), (BX, BY + sy * 0.98, 2.1), M_OAK)
box("BedHead", (1.2, 0.05, 0.9), (BX, R.y0 + 0.08, 0.95), M_OAK, bevel=0.01)
box("BedFrame", (1.2, 1.95, 0.22), (BX, BY, 0.36), M_OAK, bevel=0.01)
box("Mattress", (1.12, 1.9, 0.2), (BX, BY, 0.56), M_LINEN, bevel=0.06)
cyl("Bolster", 0.09, 1.05, (BX, R.y0 + 0.25, 0.74), M_LINEN, verts=14, rot=(0, math.pi / 2, 0))
sphere("Pillow", 0.3, (BX + 0.05, R.y0 + 0.48, 0.73), M_LINEN, seg=16, scale=(1.0, 0.6, 0.22))
# the coverlet turned back, a wool blanket over the foot, hanging down at the sides
box("Blanket", (1.22, 1.3, 0.06), (BX, R.y0 + 1.4, 0.68), M_BLANKET, bevel=0.025)
for sx in (-1, 1): box(f"BlanketSide{sx}", (0.04, 1.28, 0.32), (BX + sx * 0.6, R.y0 + 1.4, 0.52), M_BLANKET, bevel=0.015)
box("BlanketFoot", (1.2, 0.04, 0.3), (BX, R.y0 + 2.05, 0.53), M_BLANKET, bevel=0.015)
box("SheetTurn", (1.14, 0.3, 0.025), (BX, R.y0 + 0.75, 0.69), M_LINEN)
# Elizabeth's letter: folded sheets with the broken seal, lying on the coverlet
box("Letter", (0.21, 0.15, 0.004), (BX + 0.25, BY + 0.2, 0.735), M_PAPER, rot=(0, 0, 0.35))
box("LetterOpen", (0.2, 0.27, 0.003), (BX + 0.05, BY + 0.05, 0.733), M_PAPER, rot=(0.04, 0, -0.2))
cyl("Seal", 0.012, 0.004, (BX + 0.3, BY + 0.22, 0.739), plain("M_SealWax", (0.40, 0.03, 0.02), rough=0.4), verts=10)
for k in range(9): box(f"Script{k}", (0.13, 0.002, 0.0008), (BX + 0.05 + 0.01 * math.sin(k), BY - 0.03 + k * 0.022, 0.735), M_INK, rot=(0, 0, -0.2))
# bed curtains: green wool, drawn back to the posts at the head and foot
def bed_curtain(nm, x0, y0, along, width, z0, z1):
    C = K.MB(); rows_ = []
    for j in range(9):
        t = j / 8; z = z1 - t * (z1 - z0); gather = 0.6 - 0.25 * math.sin(t * math.pi)
        row = []
        for i in range(11):
            u = i / 10; p = Vector((x0, y0, z)) + along * u * width * gather
            n_ = Vector((-along.y, along.x, 0)) * 0.05 * math.sin(u * 15)
            row.append(C.vert(tuple(p + n_), (u, t), t ** 1.3))
        if rows_: [C.face(rows_[-1][i], rows_[-1][i + 1], row[i + 1], row[i]) for i in range(10)]
        rows_.append(row)
    return C
cc = K.MB()
for (x0, y0, al) in ((BX + 0.62, BY + 1.0, Vector((0, -1, 0))), (BX - 0.62, BY + 1.0, Vector((0, -1, 0))), (BX + 0.6, BY - 0.95, Vector((-1, 0, 0)))):
    c_ = bed_curtain("BC", x0, y0, al, 0.7, 0.4, 2.05)
    base = len(cc.v); cc.v += c_.v; cc.uv += c_.uv; cc.col += c_.col; cc.f += [tuple(i + base for i in f) for f in c_.f]
cc.build("cloth.curtain.bed", M_BEDCURT)
box("Valance", (1.3, 2.06, 0.18), (BX, BY, 2.0), M_BEDCURT)

# ----------------------------------------------------------------------------- Clerval's chair, the little table at the window, books, wash-stand, stove
I.sabre_chair("ClervalChair", (BX + 1.0, BY + 0.25), math.radians(100), M_OAK, M_BLANKET)
TBx, TBy = 0.9, R.y1 - 0.45
box("TableTop", (0.8, 0.55, 0.035), (TBx, TBy, 0.74), M_OAK, bevel=0.005)
for sx in (-1, 1):
    for sy in (-1, 1): box(f"TableLeg{sx}{sy}", (0.04, 0.04, 0.72), (TBx + sx * 0.35, TBy + sy * 0.23, 0.36), M_OAK)
box("TableDrawer", (0.72, 0.48, 0.1), (TBx, TBy, 0.67), M_OAK)
TZ = 0.76
for k in range(4): box(f"Sheet{k}", (0.21, 0.29, 0.002), (TBx - 0.12 + k * 0.01, TBy - 0.02 + k * 0.008, TZ + 0.001 * k), M_PAPER, rot=(0, 0, 0.1 - 0.05 * k))
for k in range(8): box(f"Writing{k}", (0.15, 0.002, 0.0008), (TBx - 0.12, TBy - 0.12 + k * 0.025, TZ + 0.006), M_INK, rot=(0, 0, 0.05))
lathe("Inkstand", [(0, 0), (0.04, 0), (0.04, 0.05), (0.015, 0.06), (0, 0.06)], (TBx + 0.2, TBy + 0.12, TZ), M_PEWTER, steps=12)
cyl("Quill", 0.003, 0.3, (TBx + 0.21, TBy + 0.1, TZ + 0.12), M_QUILL, verts=5, rot=(0.6, 0.4, 0))
lathe("CandleStick", [(0, 0), (0.05, 0), (0.05, 0.01), (0.012, 0.03), (0.011, 0.14), (0.025, 0.15), (0, 0.155)], (TBx + 0.28, TBy - 0.15, TZ), M_PEWTER, steps=12)
cyl("Candle", 0.011, 0.14, (TBx + 0.28, TBy - 0.15, TZ + 0.225), M_WAX, verts=8)
K.fx("fx.candle.table", (TBx + 0.28, TBy - 0.15, TZ + 0.305), 0.012)["radius"] = 0.012
box("Shelf", (1.2, 0.24, 0.03), (2.1, 0.2, 1.55), M_OAK) if False else box("Shelf", (0.24, 1.2, 0.03), (R.x1 - 0.13, 0.0, 1.55), M_OAK)
x_ = R.x1 - 0.14
for k in range(11):
    th = rng.uniform(0.03, 0.06); hh = rng.uniform(0.2, 0.28)
    yy = -0.5 + sum(0.065 for _ in range(k)) if False else -0.52 + k * 0.075
    box(f"Book{k}", (0.17, th, hh), (x_, yy, 1.565 + hh / 2), BOOKC[k % 3], bevel=0.003)
box("BookFlat", (0.17, 0.24, 0.04), (x_, 0.42, 1.585), BOOKC[1])
# wash-stand with jug and basin (east wall, near the door)
box("WashTop", (0.45, 0.4, 0.03), (R.x1 - 0.3, -1.2, 0.8), M_OAK)
for sx in (-1, 1):
    for sy in (-1, 1): box(f"WashLeg{sx}{sy}", (0.03, 0.03, 0.8), (R.x1 - 0.3 + sx * 0.19, -1.2 + sy * 0.17, 0.4), M_OAK)
lathe("Basin", [(0, 0), (0.08, 0), (0.17, 0.06), (0.18, 0.08), (0, 0.04)], (R.x1 - 0.3, -1.2, 0.815), M_JUG, steps=18)
lathe("Jug", [(0, 0), (0.06, 0), (0.09, 0.1), (0.07, 0.2), (0.045, 0.24), (0.06, 0.27), (0, 0.27)], (R.x1 - 0.3, -1.2, 0.83), M_JUG, steps=14)
# the tiled stove in the north-east corner (cold in spring)
box("Stove", (0.7, 0.7, 1.6), (R.x1 - 0.45, R.y1 - 0.45, 0.8), M_STOVE, bevel=0.03)
box("StoveTop", (0.78, 0.78, 0.1), (R.x1 - 0.45, R.y1 - 0.45, 1.65), M_STOVE, bevel=0.02)
box("StoveBase", (0.8, 0.8, 0.12), (R.x1 - 0.45, R.y1 - 0.45, 0.06), plain("M_StoveFeet", (0.05, 0.05, 0.05), rough=0.6))

# ----------------------------------------------------------------------------- light, anchors
SKY = B.clear_sky_mat("M_SkyDome", SUN_DIR, zenith=(0.30, 0.48, 0.78), horizon=(0.75, 0.82, 0.90), cloud=0.4, strength=1.0)
B.sky_dome("SkyDome", SKY, 120.0)
light_obj("light.sun", 'SUN', 3.2, (1.0, 0.95, 0.86), tuple(SUN_DIR * 30), direction=-SUN_DIR, angle=math.radians(2.0))
sl = light_obj("light.sky", 'SUN', 0.3, (0.70, 0.78, 0.95), (0, 0, 30), direction=(0.1, -0.2, -1.0), angle=math.radians(90)); sl.data.use_shadow = False
light_obj("light.window", 'AREA', 240.0, (0.85, 0.90, 1.0), (WIN_X, WY + 0.32, WIN_SILL + WIN_H / 2), direction=(0, -1, -0.2), size=WIN_W, shape='RECTANGLE', size_y=WIN_H)
B.world_sky(zen=(0.30, 0.45, 0.75), hor=(0.75, 0.80, 0.85), ground=(0.2, 0.18, 0.15), strength=1.0)
E = READER + Vector((0, 0, EYE)); fwd = (LOOK_AT - READER); fwd.z = 0; fwd.normalize()
B.reader_anchors(tuple(READER), tuple(E + fwd))
anchor("scene.centre", (WIN_X, WY, WIN_SILL)); anchor("room.window", (WIN_X, WY, WIN_SILL)); anchor("room.bed", (BX, BY, 0.0))
anchor("room.letter", (BX + 0.15, BY + 0.1, 0.735)); anchor("room.table", (TBx, TBy, 0.0))
sound("birds", "lime", (-2.0, WY + 3.0, 4.0)); sound("clock", "stair", (R.x1 + 1.0, 1.3, 1.5))
page = B.page_preview(E, fwd)
K.apply_transforms()
def yawed(deg, dist=3.0, dz=-0.4):
    d = Matrix.Rotation(math.radians(-deg), 3, 'Z') @ fwd
    return tuple(E + d * dist + Vector((0, 0, dz)))
cams = [camera("Cam_Reader", tuple(E), yawed(0, 3.0, -0.25), lens=17), camera("Cam_Page", tuple(E), yawed(0, 3.0, -0.25), lens=17),
        camera("Cam_Left", tuple(E), yawed(-80, 3.0, -0.4), lens=17), camera("Cam_Right", tuple(E), yawed(80, 3.0, -0.4), lens=17),
        camera("Cam_Behind", tuple(E), yawed(180, 3.0, -0.5), lens=17),
        camera("Cam_Bed", tuple(E + Vector((0.4, 0.3, -0.1))), (BX, BY, 0.7), lens=24),
        camera("Cam_Window", tuple(E + Vector((0.0, 1.6, 0.0))), (WIN_X - 0.5, WY + 4.0, 3.5), lens=24)]
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "ingolstadt_sickroom_source.blend"))
K.print_budget()
if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=1.1, captures_dir=ARGS.captures)
if ARGS.bake or ARGS.export:
    B.export_room("ingolstadt_sickroom.gltf", cams, page=page,
                  keep_names={"M_BudSprays": "veg.leaves.buds", "M_Muslin": "cloth.curtain.window", "M_BedCurtain": "cloth.curtain.bed",
                              "M_SkyDome": "SkyDome", "M_FarTown": "far.town"},
                  keep_uv={"M_SkyDome", "M_FarTown"}, unlit_emit=("M_FarTown",),
                  size_for={"M_PineBoards": (2048, 256, 1024), "M_LimeWash": (2048, 64, 1024), "M_Ceiling": (512, 32, 128), "M_Beams": (512, 128, 256),
                            "M_Oak": (1024, 256, 512), "M_Linen": (512, 64, 256), "M_WoolBlanket": (512, 64, 256), "M_BedCurtain": (512, 64, 256),
                            "M_Muslin": (256, 32, 128), "M_StoveTiles": (512, 128, 256), "M_FarTown": (1024,), "M_SkyDome": (512,), "M_LimeBark": (512, 64, 256)},
                  default_size=(128, 64, 128))
print("DONE")
