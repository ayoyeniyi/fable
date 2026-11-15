"""
Fable: the Netherfield drawing-room in the evening (Pride and Prejudice, chapter 8).

"On entering the drawing-room, she found the whole party at loo, and was immediately invited to join them" ...
"[she] walked towards a table where a few books were lying." ... "she could suit herself perfectly with those in the room."

A spacious drawing-room in a rich rented house, late in a still November evening, as if everyone has just stepped out.
Pale grey-green painted walls over a panelled dado, white joinery, a deep cornice; three tall sash windows on the north
wall with their curtains of slate-blue damask drawn against the night; a white statuary-marble chimney-piece on the
west wall with a coal fire burning low in the register grate, a gilt overmantel glass, a bracket clock and a pair of
silver candlesticks on the shelf; a round mahogany loo table with the cards and mother-of-pearl counters left mid-game
and four sabre-legged chairs pushed back; by the east window a small table with a few books lying in a loose stack and
a single candle; a scroll-ended sofa in striped silk on the south wall below two landscapes; a square pianoforte; a
door to the passage stands a little open on the east wall. No people.

Light: the fire (low, left of the reader) and five candles; nothing else. The light is warm, the walls and curtains cool,
so the room reads as candlelit without an orange cast; exposure is set for the page, keeping detail in the shadows.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet (floor, z = 0), between the sofa and the loo table, facing +Y (north)
  anchor.reader.look      eye height (1.55 m), 1 m ahead
  anchor.scene.centre     the loo table
  anchor.room.fireplace, anchor.room.cardTable, anchor.room.booksTable, anchor.room.door
  Lamp.fire, Lamp.candles.table, Lamp.candles.mantel, Lamp.candle.books   (POINT; FableBuild's indoor block keeps "Lamp*")
  fx.fire.hearth (base of the coal fire, size = radius), fx.candle.* (wick tops)
  sound.fire.hearth, sound.clock.mantel
  MESH_Embers (emissive coals), WindowGlass_* (dark night panes behind the curtains)

Register the scene as indoor (not Outdoor). Axes: metres, Blender +Z up, the reader faces +Y.

Run headless:
  blender -b -P blender/build_netherfield_drawing_room.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_netherfield_drawing_room.py -- --render --samples 64 --res 1400 --captures captures/blender/netherfield-drawing-room
  blender -b -P blender/build_netherfield_drawing_room.py -- --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
import pride_interior as I
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       texcoord_obj, wood, noisy, plain, vcol_mat, box, cyl, sphere, lathe, tube, sweep, mesh_from, MB, Frame,
                       anchor, fx, sound, light_obj, camera, link)

ARGS = K.setup("netherfield-drawing-room", "out/netherfield-drawing-room", 1811, "NetherfieldDrawingRoom", default_samples=64)
OUT = K.OUT; scene = K.scene
rng = random.Random(1811)
scene.cycles.max_bounces = 10; scene.cycles.diffuse_bounces = 6

EYE = 1.55
R = I.Room(-3.6, 4.4, -2.4, 5.0, 3.9, t=0.4)
READER = Vector((0.7, -0.35, 0.0))

# ----------------------------------------------------------------------------- materials
M_WALL = I.paint_mat("M_WallPaint", K.srgb((0.67, 0.71, 0.66)), rough=0.8)
M_DADO = I.paint_mat("M_DadoPaint", K.srgb((0.72, 0.73, 0.68)), rough=0.6, dirt=0.1)
M_JOIN = I.joinery_mat("M_Joinery", K.srgb((0.86, 0.85, 0.80)))
M_CEIL = I.paint_mat("M_Ceiling", K.srgb((0.84, 0.84, 0.81)), rough=0.9, dirt=0.0)
M_FLOOR = I.boards_mat("M_FloorBoards")
M_CARPET = I.carpet_mat("M_Carpet", 0.4, 1.3, 3.3, 3.0)
M_MAHOG = I.mahogany("M_Mahogany")
M_GILT = I.gilt("M_Gilt")
M_MARBLE = I.marble("M_Marble")
M_SILVER = plain("M_Silver", (0.80, 0.80, 0.78), rough=0.18, metallic=1.0)
M_BRASS = plain("M_Brass", (0.72, 0.55, 0.30), rough=0.3, metallic=1.0)
M_IRON = noisy("M_Iron", [(0.025, 0.025, 0.027), (0.05, 0.05, 0.05), (0.035, 0.032, 0.03)], scale=30, rough=(0.45, 0.7), metallic=0.6)
M_SOOT = plain("M_Soot", (0.012, 0.011, 0.01), rough=0.95)
M_WAX = plain("M_Wax", K.srgb((0.93, 0.91, 0.85)), rough=0.45)
M_STRIPE = I.silk("M_SofaSilk", K.srgb((0.62, 0.66, 0.56)), K.srgb((0.83, 0.82, 0.72)), stripes=1.0, stripe_w=0.045, axis='X', sheen=0.7)
M_CHAIRSILK = I.silk("M_ChairSilk", K.srgb((0.42, 0.52, 0.50)), K.srgb((0.52, 0.62, 0.60)), damask=0.6, sheen=0.6)
M_CURTAIN = I.silk("M_Curtains", K.srgb((0.28, 0.35, 0.45)), K.srgb((0.36, 0.44, 0.54)), damask=0.7, sheen=0.5, rough=0.7)
M_NIGHT = plain("M_WindowGlassNight", (0.008, 0.01, 0.016), rough=0.05)
M_MIRROR = plain("M_Mirror", (0.75, 0.75, 0.73), rough=0.04, metallic=1.0)
M_EMBERS = None
M_LAND1 = I.landscape_mat("M_Landscape1", 1); M_LAND2 = I.landscape_mat("M_Landscape2", 2)
M_CLOCKFACE = plain("M_ClockFace", K.srgb((0.70, 0.66, 0.58)), rough=0.4)
M_PAGES = noisy("M_BookPages", [K.srgb((0.80, 0.76, 0.64)), K.srgb((0.72, 0.68, 0.56))], scale=200, rough=0.85, stretch=(1, 1, 30), bump=0.0)
M_CARDS = None   # vertex-coloured playing cards (built below)

def embers_mat(name="M_Embers"):
    """glowing coals: dark clinker with orange-red cracks, emissive (static glow; Unity adds the flames)."""
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

# ----------------------------------------------------------------------------- openings, then walls
# north wall (runs from x1 to x0): u = 4.4 - x
WIN_X = [-2.1, 0.55, 3.1]
for k, x in enumerate(WIN_X):
    I.sash_window(f"Win{k}", R, 'N', 4.4 - x, 1.12, 0.62, 2.55, M_JOIN, M_NIGHT, M_JOIN, panes=(3, 6), curtain_mat=M_CURTAIN, pelmet_mat=M_GILT, drawn=1.0)
# east wall (runs from y0 up): u = y + 2.4; the door to the passage, standing a little open
DOOR_Y = 0.05
M_DOOR = I.mahogany("M_DoorMahogany", rough=(0.3, 0.55), coat=0.2)
I.six_panel_door("Door", R, 'E', DOOR_Y + 2.4, 1.0, 2.45, M_DOOR, M_JOIN, M_BRASS, open_deg=24, hinge_left=False)
I.build_walls(R, M_WALL)
# the passage beyond the door: a dim floor, walls and a stair newel glimpsed
box("PassageFloor", (2.2, 2.6, 0.02), (R.x1 + R.t + 1.1, DOOR_Y, -0.01), M_FLOOR)
box("PassageWallE", (0.1, 2.6, 3.0), (R.x1 + R.t + 2.2, DOOR_Y, 1.5), M_DADO)
box("PassageWallN", (2.2, 0.1, 3.0), (R.x1 + R.t + 1.1, DOOR_Y + 1.3, 1.5), M_DADO)
box("PassageWallS", (2.2, 0.1, 3.0), (R.x1 + R.t + 1.1, DOOR_Y - 1.3, 1.5), M_DADO)
box("PassageCeil", (2.4, 2.8, 0.05), (R.x1 + R.t + 1.1, DOOR_Y, 3.0), M_CEIL)

# floor, carpet, ceiling
K.box("Floor", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.04), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, -0.02), M_FLOOR)
cx, cy, chx, chy = 0.4, 1.3, 3.3, 3.0
box("Carpet", (chx * 2, chy * 2, 0.012), (cx, cy, 0.006), M_CARPET, bevel=0.004)
box("Ceiling", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.05), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, R.h + 0.025), M_CEIL)
lathe("CeilingRose", [(0.0, -0.0), (0.42, 0.0), (0.4, -0.02), (0.34, -0.03), (0.3, -0.05), (0.2, -0.055), (0.12, -0.075), (0.05, -0.09), (0.0, -0.09)],
      (0.4, 1.3, R.h), M_CEIL, steps=32)

# mouldings: skirting, chair rail, dado panels, cornice
I.moulding_runs(R, "Skirting", I.skirting_profile(0.26), 0.0, M_JOIN)
I.moulding_runs(R, "ChairRail", I.rail_profile(), 0.92, M_JOIN, z_band=(0.88, 0.96))
I.dado_panels(R, M_JOIN, rail_z=0.92, skirt=0.26)
I.moulding_runs(R, "Cornice", I.cornice_profile(0.26, 0.3), R.h, M_JOIN, z_band=(R.h - 0.3, R.h))
# dado field painted a shade warmer than the wall
for w in ('S', 'E', 'N', 'W'):
    o, a, n, L = R.wall_frame(w)
    for k, (u0, u1) in enumerate(I.runs(R, w, 0.26, 0.9)):
        c = o + a * ((u0 + u1) / 2) + n * 0.002 + Vector((0, 0, 0.58))
        box(f"Dado{w}{k}", (abs(a.x) * (u1 - u0) + abs(n.x) * 0.004, abs(a.y) * (u1 - u0) + abs(n.y) * 0.004, 0.64), tuple(c), M_DADO)

# ----------------------------------------------------------------------------- the chimney-piece, grate and fire (west wall)
FP_Y = 1.75
F = Frame((R.x0, FP_Y), -math.pi / 2)          # local +Y points into the room (+X world), local +X = -Y world... check below
F = Frame((R.x0, FP_Y), math.atan2(-1, 0))     # yaw so that local +Y -> world +X
def FP(x, y, z): return F.p(x, y, z)
OW, OH = 0.92, 0.92                             # the fire opening
# hearth stone and slips
F.box("HearthStone", (1.75, 0.52, 0.04), (0, 0.26, 0.02), M_MARBLE, bevel=0.004)
# jambs: plain pilasters with a reeded face, blocks with roundels at the top corners
for sx in (-1, 1):
    F.box(f"Jamb{sx}", (0.26, 0.16, OH + 0.02), (sx * (OW / 2 + 0.13), 0.08, (OH + 0.02) / 2), M_MARBLE, bevel=0.006)
    for r in range(3):
        F.box(f"Reed{sx}{r}", (0.022, 0.02, OH - 0.1), (sx * (OW / 2 + 0.13) + (r - 1) * 0.06, 0.165, OH / 2 + 0.02), M_MARBLE, bevel=0.009)
    F.box(f"CornerBlock{sx}", (0.28, 0.18, 0.27), (sx * (OW / 2 + 0.13), 0.09, OH + 0.135), M_MARBLE, bevel=0.008)
    cyl(f"Roundel{sx}", 0.07, 0.025, FP(sx * (OW / 2 + 0.13), 0.185, OH + 0.135), M_MARBLE, verts=16, rot=(math.pi / 2, 0, F.yaw))
F.box("Frieze", (OW, 0.15, 0.25), (0, 0.075, OH + 0.125), M_MARBLE, bevel=0.004)
F.box("Tablet", (0.36, 0.03, 0.17), (0, 0.16, OH + 0.135), M_MARBLE, bevel=0.006)
F.box("Shelf", (1.82, 0.26, 0.05), (0, 0.12, OH + 0.295), M_MARBLE, bevel=0.012)
F.box("ShelfBed", (1.72, 0.2, 0.03), (0, 0.10, OH + 0.255), M_MARBLE, bevel=0.006)
# the register grate: a cast-iron plate filling the opening, a dark arched mouth, a barred fire basket on short legs
F.box("GratePlate", (OW, 0.03, OH), (0, 0.012, OH / 2), M_IRON)
F.box("GrateMouth", (OW * 0.62, 0.03, OH * 0.52), (0, 0.02, OH * 0.40), M_SOOT)
F.box("BasketFloor", (0.56, 0.24, 0.03), (0, 0.13, 0.15), M_IRON)
for k in range(5):
    F.box(f"BasketBar{k}", (0.56, 0.014, 0.014), (0, 0.255, 0.17 + k * 0.045), M_IRON, bevel=0.003)
for sx in (-1, 1):
    F.box(f"BasketSide{sx}", (0.02, 0.24, 0.22), (sx * 0.28, 0.13, 0.25), M_IRON)
    F.cyl(f"BasketLeg{sx}", 0.012, 0.16, (sx * 0.26, 0.25, 0.08), M_IRON, verts=6)
    lathe(f"Urn{sx}", [(0.0, 0.0), (0.03, 0.0), (0.03, 0.03), (0.022, 0.06), (0.035, 0.1), (0.02, 0.14), (0.0, 0.15)], FP(sx * 0.34, 0.26, 0.15), M_BRASS, steps=10)
# coals: a heap of lumps, the lower ones glowing
cr = random.Random(5)
for k in range(26):
    lx = cr.uniform(-0.24, 0.24); ly = cr.uniform(0.04, 0.24); lz = 0.18 + cr.uniform(0, 0.09) * (1 - abs(lx) / 0.3)
    sphere(f"Coal{k}", cr.uniform(0.028, 0.05), FP(lx, ly, lz), M_EMBERS if lz < 0.25 or cr.random() < 0.5 else M_IRON, seg=6,
           scale=(cr.uniform(0.8, 1.3), cr.uniform(0.8, 1.3), cr.uniform(0.6, 0.9)))
FIRE_BASE = Vector(FP(0, 0.14, 0.22))
# no render-only fire flames: the glowing coals and the light carry the stills; Unity draws flames at fx.fire.hearth
# fender and fire irons
F.box("FenderFront", (1.5, 0.012, 0.09), (0, 0.5, 0.045), M_BRASS, bevel=0.004)
for sx in (-1, 1): F.box(f"FenderSide{sx}", (0.012, 0.36, 0.09), (sx * 0.75, 0.33, 0.045), M_BRASS, bevel=0.004)
F.box("FenderPlate", (1.5, 0.37, 0.01), (0, 0.33, 0.045), M_IRON)
for k, (ang, ln) in enumerate(((0.12, 0.72), (0.18, 0.70), (0.08, 0.68))):
    p0 = Vector(FP(0.66, 0.3, 0.06)); p1 = Vector(FP(0.66 - 0.04 * k, 0.12, 0.72))
    tube(f"FireIron{k}", [p0, p1], 0.008, M_IRON, sides=5)
    sphere(f"FireIronKnob{k}", 0.018, tuple(p1 + Vector((0, 0, 0.01))), M_BRASS, seg=8)
# the overmantel glass in a gilt frame, a bracket clock and two candlesticks on the shelf
SHELF_Z = OH + 0.32
F.box("MirrorGlass", (1.3, 0.02, 1.15), (0, 0.03, SHELF_Z + 0.75), M_MIRROR)
for (fx_, fz, sw, sh) in ((0, SHELF_Z + 0.75 + 0.62, 1.48, 0.09), (0, SHELF_Z + 0.75 - 0.62, 1.48, 0.09), (-0.695, SHELF_Z + 0.75, 0.09, 1.15), (0.695, SHELF_Z + 0.75, 0.09, 1.15)):
    F.box(f"MirrorFrame{fx_}{fz}", (sw, 0.06, sh), (fx_, 0.05, fz), M_GILT, bevel=0.015)
F.box("MirrorCrest", (0.6, 0.04, 0.12), (0, 0.05, SHELF_Z + 1.46), M_GILT, bevel=0.03)
# bracket clock (mahogany case, arched top, white dial, brass bezel)
F.box("ClockCase", (0.26, 0.15, 0.32), (0, 0.11, SHELF_Z + 0.16), M_MAHOG, bevel=0.008)
cyl("ClockArch", 0.13, 0.15, FP(0, 0.11, SHELF_Z + 0.32), M_MAHOG, verts=16, rot=(math.pi / 2, 0, F.yaw))
cyl("ClockDial", 0.085, 0.01, FP(0, 0.19, SHELF_Z + 0.2), M_CLOCKFACE, verts=24, rot=(math.pi / 2, 0, F.yaw))
cyl("ClockBezel", 0.092, 0.006, FP(0, 0.187, SHELF_Z + 0.2), M_BRASS, verts=24, rot=(math.pi / 2, 0, F.yaw))
for k, (ang, ln) in enumerate(((math.radians(-60), 0.055), (math.radians(20), 0.07))):     # hands at ten past ten
    F.box(f"ClockHand{k}", (0.005, 0.004, ln), (math.sin(ang) * ln / 2, 0.197, SHELF_Z + 0.2 + math.cos(ang) * ln / 2), M_IRON, ry=-ang)
for sx in (-1, 1): F.box(f"ClockFoot{sx}", (0.04, 0.12, 0.02), (sx * 0.1, 0.11, SHELF_Z - 0.0), M_BRASS)
CANDLE_TOPS = {}
CANDLE_TOPS["mantel"] = []
for sx in (-1, 1):
    CANDLE_TOPS["mantel"] += I.candlestick(f"MantelStick{sx}", FP(sx * 0.66, 0.12, SHELF_Z), M_SILVER, M_WAX, height=0.28, candle_h=0.19)
anchor("room.fireplace", FP(0, 0.4, 0))

# ----------------------------------------------------------------------------- the loo table, mid-game, and four chairs pushed back
TABLE = Vector((-1.25, 2.45, 0))
def face(pos, target):
    """the Frame yaw that turns local +Y (the way a chair faces) from pos towards target."""
    return math.atan2(-(target[0] - pos[0]), target[1] - pos[1])
top = I.pedestal_table("LooTable", (TABLE.x, TABLE.y), M_MAHOG, M_MAHOG, radius=0.64, height=0.72, feet=4)
anchor("room.cardTable", tuple(TABLE))
def cards_mat():
    m, nt, b = new_mat("M_PlayingCards")
    a = node(nt, "ShaderNodeAttribute", (-800, 0)); a.attribute_name = "tone"
    nt.links.new(a.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.42
    return m
M_CARDS = cards_mat()
def card_mesh():
    """all the cards in one mesh, coloured by the 'tone' attribute (plain blue-grey backs: period cards had no
    corner indices; fronts white with a red or black centre mark standing in for the pips)."""
    me_v = []; me_f = []; cols = []
    cr2 = random.Random(8)
    def slab(c, yaw, w=0.064, h=0.09, face_up=False, red=False, lift=0.0):
        ca, sa = math.cos(yaw), math.sin(yaw)
        base = len(me_v)
        for (px, py) in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
            me_v.append((c[0] + px * ca - py * sa, c[1] + px * sa + py * ca, c[2] + lift + 0.0015))
        me_f.append((base, base + 1, base + 2, base + 3))
        cols.append((0.80, 0.78, 0.72) if face_up else (0.36, 0.42, 0.50))
        if face_up:
            base2 = len(me_v); s = 0.012
            for (px, py) in ((-s, -s * 1.3), (s, -s * 1.3), (s, s * 1.3), (-s, s * 1.3)):
                me_v.append((c[0] + px * ca - py * sa, c[1] + px * sa + py * ca, c[2] + lift + 0.0019))
            me_f.append((base2, base2 + 1, base2 + 2, base2 + 3))
            cols.append((0.55, 0.06, 0.05) if red else (0.03, 0.03, 0.03))
    tz = top[2]
    for k in range(4):            # four hands left face down at the places, in small fans
        ang = math.radians(35 + 90 * k)
        hc = Vector((TABLE.x + math.cos(ang) * 0.42, TABLE.y + math.sin(ang) * 0.42, tz))
        for j in range(3):
            slab(hc + Vector((math.cos(ang + 1.57) * (j - 1) * 0.022, math.sin(ang + 1.57) * (j - 1) * 0.022, 0)), ang + 1.57 + (j - 1) * 0.18, lift=j * 0.0006)
    for j in range(4):            # the trick in the middle, face up
        a2 = cr2.uniform(0, 6.28); r2 = cr2.uniform(0.05, 0.16)
        slab((TABLE.x + math.cos(a2) * r2, TABLE.y + math.sin(a2) * r2, tz), cr2.uniform(0, 3.14), face_up=True, red=cr2.random() < 0.5, lift=j * 0.0006)
    for j in range(12):           # the rest of the pack, squared
        slab((TABLE.x - 0.3, TABLE.y - 0.22, tz), 0.4 + cr2.gauss(0, 0.02), lift=j * 0.0006)
    o = mesh_from("PlayingCards", me_v, me_f, M_CARDS)
    ca = o.data.color_attributes.new("tone", 'BYTE_COLOR', 'CORNER')
    for p in o.data.polygons:
        for li in p.loop_indices: ca.data[li].color = (*cols[p.index], 1.0)
    return o
card_mesh()
M_PEARL = plain("M_Pearl", K.srgb((0.86, 0.85, 0.82)), rough=0.25, coat=0.6)
for k in range(4):                # mother-of-pearl fish counters at the places and in the pool
    ang = math.radians(35 + 90 * k) + 0.45
    for j in range(cr.randint(3, 6)):
        c = Vector((TABLE.x + math.cos(ang) * 0.45 + cr.gauss(0, 0.02), TABLE.y + math.sin(ang) * 0.45 + cr.gauss(0, 0.02), top[2] + 0.003 + j * 0.002))
        sphere(f"Counter{k}{j}", 0.022, tuple(c), M_PEARL, seg=8, scale=(1.0, 0.45, 0.08))
for j in range(9):
    c = Vector((TABLE.x + cr.gauss(0, 0.04), TABLE.y + cr.gauss(0, 0.04), top[2] + 0.003 + (j % 3) * 0.002))
    sphere(f"Pool{j}", 0.022, tuple(c), M_PEARL, seg=8, scale=(1.0, 0.45, 0.08))
CANDLE_TOPS["table"] = []
for k, (dx, dy) in enumerate(((0.2, 0.13), (-0.16, -0.18))):
    CANDLE_TOPS["table"] += I.candlestick(f"TableStick{k}", (TABLE.x + dx, TABLE.y + dy, top[2]), M_SILVER, M_WAX, height=0.24, candle_h=0.17 - 0.05 * k)
for k, (ang, push, turn) in enumerate(((35, 0.28, 0.25), (125, 0.12, -0.1), (215, 0.42, 0.5), (305, 0.2, -0.35))):
    a = math.radians(ang)
    pos = TABLE + Vector((math.cos(a), math.sin(a), 0)) * (0.72 + push)
    I.sabre_chair(f"CardChair{k}", (pos.x, pos.y), face(pos, TABLE) + turn, M_MAHOG, M_CHAIRSILK)     # facing the table, turned a little

# ----------------------------------------------------------------------------- the small table with a few books, by the east window
BT = Vector((3.15, 3.05, 0))
bt = I.pedestal_table("BooksTable", (BT.x, BT.y), M_MAHOG, M_MAHOG, radius=0.36, height=0.71, feet=3)
anchor("room.booksTable", tuple(BT))
M_CALF = noisy("M_Calf", [K.srgb((0.36, 0.20, 0.11)), K.srgb((0.46, 0.27, 0.15)), K.srgb((0.30, 0.16, 0.09))], scale=14, rough=(0.35, 0.6), bump=0.3, bump_dist=0.001, coat=0.2)
M_BOARDS2 = noisy("M_GreenCloth", [K.srgb((0.20, 0.27, 0.22)), K.srgb((0.26, 0.33, 0.27))], scale=40, rough=0.7)
stack = [((0.03, 0.16, 0.24), 0.12, M_CALF), ((0.026, 0.14, 0.215), -0.2, M_BOARDS2), ((0.034, 0.15, 0.23), 0.35, M_CALF), ((0.022, 0.12, 0.19), -0.05, M_CALF)]
zz = bt[2]
for k, ((t_, w_, h_), yaw, mat) in enumerate(stack):
    I.book(f"Book{k}", (BT.x - 0.06 + 0.02 * k, BT.y + 0.03 * (k % 2), zz + t_ / 2), (t_, w_, h_), yaw + 0.5, mat, M_PAGES, roll=math.pi / 2)
    zz += t_
I.book("BookAside", (BT.x + 0.17, BT.y - 0.12, bt[2] + 0.014), (0.028, 0.15, 0.22), -0.9, M_CALF, M_PAGES, roll=math.pi / 2)
CANDLE_TOPS["books"] = I.candlestick("BooksStick", (BT.x + 0.1, BT.y + 0.18, bt[2]), M_SILVER, M_WAX, height=0.26, candle_h=0.14)

# ----------------------------------------------------------------------------- the sofa (south wall), armchairs by the fire, the pianoforte
def scroll_sofa(name, x, y, yaw, length=2.0):
    F = Frame((x, y), yaw)
    F.box(f"{name}Rail", (length, 0.7, 0.16), (0, 0, 0.3), M_MAHOG, bevel=0.01)
    F.box(f"{name}Seat", (length - 0.2, 0.62, 0.12), (0, 0.03, 0.43), M_STRIPE, bevel=0.04)
    F.box(f"{name}Back", (length - 0.05, 0.16, 0.5), (0, -0.28, 0.66), M_STRIPE, bevel=0.05, rx=-0.12)
    F.box(f"{name}BackRail", (length, 0.06, 0.06), (0, -0.33, 0.93), M_MAHOG, bevel=0.015)
    for sx in (-1, 1):
        pts = [F.p(sx * length / 2, 0.3, 0.38), F.p(sx * length / 2, 0.3, 0.62), F.p(sx * length / 2 * 1.02, 0.18, 0.76), F.p(sx * length / 2 * 1.04, 0.05, 0.74), F.p(sx * length / 2 * 1.02, -0.2, 0.72)]
        tube(f"{name}ArmWood{sx}", pts, 0.035, M_MAHOG, sides=6)
        F.box(f"{name}ArmPad{sx}", (0.12, 0.6, 0.3), (sx * (length / 2 - 0.06), 0.0, 0.58), M_STRIPE, bevel=0.04)
        cyl(f"{name}Bolster{sx}", 0.1, 0.55, F.p(sx * (length / 2 - 0.18), 0.02, 0.6), M_STRIPE, verts=12, rot=(math.pi / 2, 0, F.yaw))
        for sy in (-1, 1):
            tube(f"{name}Leg{sx}{sy}", [F.p(sx * (length / 2 - 0.05), sy * 0.3, 0.22), F.p(sx * (length / 2 - 0.02) + sx * 0.04, sy * 0.33, 0.1), F.p(sx * (length / 2 + 0.05), sy * 0.35, 0.0)],
                 [0.025, 0.02, 0.015], M_MAHOG, sides=6)
scroll_sofa("Sofa", 0.55, R.y0 + 0.45, 0.0)
def bergere(name, x, y, yaw):
    F = Frame((x, y), yaw)
    F.box(f"{name}Frame", (0.66, 0.6, 0.12), (0, 0, 0.36), M_MAHOG, bevel=0.01)
    F.box(f"{name}Cushion", (0.56, 0.52, 0.11), (0, 0.04, 0.47), M_CHAIRSILK, bevel=0.035)
    F.box(f"{name}Back", (0.62, 0.1, 0.55), (0, -0.27, 0.72), M_CHAIRSILK, bevel=0.04, rx=-0.1)
    tube(f"{name}TopRail", [F.p(-0.33, -0.3, 0.98), F.p(0, -0.34, 1.0), F.p(0.33, -0.3, 0.98)], 0.02, M_MAHOG, sides=6)
    for sx in (-1, 1):
        F.box(f"{name}Side{sx}", (0.07, 0.52, 0.28), (sx * 0.31, -0.02, 0.56), M_CHAIRSILK, bevel=0.025)
        tube(f"{name}Arm{sx}", [F.p(sx * 0.32, -0.28, 0.7), F.p(sx * 0.33, 0.1, 0.71), F.p(sx * 0.33, 0.27, 0.66), F.p(sx * 0.32, 0.29, 0.42)], 0.022, M_MAHOG, sides=6)
        for sy in (-1, 1):
            F.cyl(f"{name}Leg{sx}{sy}", 0.022, 0.32, (sx * 0.28, sy * 0.25, 0.16), M_MAHOG, verts=8, r2=0.016)
bergere("ArmchairFire", -2.55, 0.35, face((-2.55, 0.35), (R.x0, FP_Y)) + 0.25)
bergere("ArmchairFire2", -2.45, 3.3, face((-2.45, 3.3), (R.x0, FP_Y)) - 0.3)
PF = Frame((-2.25, R.y0 + 0.36), 0.0)          # square pianoforte against the south wall
PF.box("PianoCase", (1.65, 0.6, 0.27), (0, 0, 0.71), M_MAHOG, bevel=0.008)
PF.box("PianoLid", (1.67, 0.62, 0.02), (0, 0, 0.855), M_MAHOG, bevel=0.006)
PF.box("PianoKeys", (0.95, 0.12, 0.02), (-0.2, 0.31, 0.74), M_PEARL)
PF.box("PianoFrieze", (1.62, 0.02, 0.1), (0, 0.31, 0.8), M_MAHOG)
PF.box("PianoStand", (1.5, 0.5, 0.05), (0, 0, 0.55), M_MAHOG, bevel=0.005)
for sx in (-1, 1):
    for sy in (-1, 1):
        PF.cyl(f"PianoLeg{sx}{sy}", 0.03, 0.55, (sx * 0.74, sy * 0.24, 0.29), M_MAHOG, verts=10, r2=0.02)
for k, x in enumerate((-0.78, 1.83)):          # pier tables between the windows
    PT = Frame((x, R.y1 - 0.24), math.pi)
    PT.box(f"PierTop{k}", (0.95, 0.42, 0.04), (0, 0, 0.84), M_MARBLE, bevel=0.006)
    PT.box(f"PierApron{k}", (0.9, 0.38, 0.09), (0, 0, 0.775), M_GILT, bevel=0.01)
    for sx in (-1, 1): PT.cyl(f"PierLeg{k}{sx}", 0.022, 0.73, (sx * 0.4, -0.12, 0.36), M_GILT, verts=8, r2=0.014)
    PT.box(f"PierShelf{k}", (0.85, 0.3, 0.025), (0, 0.0, 0.12), M_MAHOG)
I.picture("PictureS1", R, 'S', 3.15, 2.05, 0.95, 0.72, M_GILT, M_LAND1)
I.picture("PictureS2", R, 'S', 5.15, 2.05, 0.95, 0.72, M_GILT, M_LAND2)
I.picture("PictureE", R, 'E', 5.6, 2.0, 0.8, 1.0, M_GILT, M_LAND2)

# ----------------------------------------------------------------------------- lights (one per group; FableBuild's indoor block keeps names starting "Lamp")
def centre(pts): return sum((Vector(p) for p in pts), Vector()) / len(pts)
light_obj("Lamp.fire", 'POINT', 85.0, (1.0, 0.52, 0.24), tuple(FIRE_BASE + Vector((0.38, 0, 0.12))), shadow_soft_size=0.22)
light_obj("Lamp.candles.table", 'POINT', 9.0, (1.0, 0.72, 0.45), tuple(centre(CANDLE_TOPS["table"]) + Vector((0, 0, 0.015))), shadow_soft_size=0.12)
light_obj("Lamp.candles.mantel", 'POINT', 8.0, (1.0, 0.72, 0.45), tuple(centre(CANDLE_TOPS["mantel"]) + Vector((0.08, 0, 0.015))), shadow_soft_size=0.4)
light_obj("Lamp.candle.books", 'POINT', 4.5, (1.0, 0.72, 0.45), tuple(Vector(CANDLE_TOPS["books"][0]) + Vector((0, 0, 0.015))), shadow_soft_size=0.02)
pl = light_obj("RenderOnly_PassageGlow", 'POINT', 3.0, (1.0, 0.7, 0.45), (R.x1 + R.t + 1.6, DOOR_Y + 0.9, 1.4), shadow_soft_size=0.05)
I.RENDER_ONLY.append(pl)
world = bpy.data.worlds.new("Night"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.010, 0.012, 0.018, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors and living-scene sources
fwd = Vector((0, 1, 0))
anchor("reader.entrance", tuple(READER))
anchor("reader.look", tuple(READER + fwd + Vector((0, 0, EYE))))
anchor("scene.centre", tuple(TABLE))
anchor("room.door", R.at('E', DOOR_Y + 2.4))
fx("fx.fire.hearth", tuple(FIRE_BASE), 0.24)
k = 0
for grp, tops in CANDLE_TOPS.items():
    for t in tops:
        fx(f"fx.candle.{grp}{k}", t, 0.012); k += 1
sound("fire", "hearth", tuple(FIRE_BASE + Vector((0.2, 0, 0.1))))
sound("clock", "mantel", FP(0, 0.15, SHELF_Z + 0.2))

page = box("PagePreview", (0.4, 0.004, 0.55), tuple(READER + fwd * 0.6 + Vector((0, 0, EYE - 0.05))), plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9))
K.apply_transforms()

# ----------------------------------------------------------------------------- cameras
E = READER + Vector((0, 0, EYE))
def yawed(deg, dist=5.0, dz=-0.6):
    a = math.radians(deg); return tuple(E + Vector((math.sin(a), math.cos(a), 0)) * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(E), yawed(0, 6, -0.7), lens=17),
    camera("Cam_Page", tuple(E), yawed(0, 6, -0.7), lens=17),
    camera("Cam_Left", tuple(E), yawed(-70, 6, -0.7), lens=17),
    camera("Cam_Right", tuple(E), yawed(70, 6, -0.6), lens=17),
    camera("Cam_Behind", tuple(E), yawed(180, 6, -0.4), lens=17),
    camera("Cam_Down", tuple(E), tuple(READER + Vector((-0.3, 1.4, 0))), lens=17),
    camera("Cam_Up", tuple(E), tuple(READER + Vector((-0.5, 2.0, R.h))), lens=17),
    camera("Cam_Table", tuple(TABLE + Vector((0.95, -0.9, 1.35))), tuple(TABLE + Vector((0, 0, 0.72))), lens=28),
    camera("Cam_Fire", (-1.6, 0.9, 1.25), FP(0, 0.2, 0.7), lens=24),
    camera("Cam_Books", tuple(BT + Vector((-0.9, -0.9, 1.4))), tuple(BT + Vector((0, 0, 0.75))), lens=30),
]
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "netherfield_drawing_room_source.blend"))
K.print_budget(exclude=("PagePreview",) + tuple(o.name for o in I.RENDER_ONLY))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.6, captures_dir=ARGS.captures)

if ARGS.bake or ARGS.export:
    for o in I.RENDER_ONLY:
        if o.name in bpy.data.objects: bpy.data.objects.remove(o)
    K.bake_and_export(
        "netherfield_drawing_room.gltf", cams, page=page,
        keep_names={"M_Embers": "MESH_Embers", "M_WindowGlassNight": "WindowGlass_night"},
        size_for={"M_FloorBoards": (1024, 256, 1024), "M_Carpet": (2048, 128, 1024), "M_WallPaint": (2048, 128, 1024), "M_Ceiling": (1024, 64, 256),
                  "M_Joinery": (2048, 256, 1024), "M_DadoPaint": (1024, 64, 256), "M_Mahogany": (2048, 512, 1024), "M_Marble": (1024, 256, 512),
                  "M_Curtains": (1024, 256, 1024), "M_SofaSilk": (1024, 128, 512), "M_ChairSilk": (1024, 128, 512), "M_Gilt": (512, 256, 256),
                  "M_DoorMahogany": (1024, 256, 512), "M_Landscape1": (512, 64, 128), "M_Landscape2": (512, 64, 128), "M_Silver": (128, 64, 64),
                  "M_Brass": (128, 64, 64), "M_Iron": (256, 128, 128), "M_Embers": (256, 64, 128), "M_PlayingCards": (512, 64), "M_Pearl": (64, 32),
                  "M_Wax": (128, 32), "M_Mirror": (64, 32), "M_WindowGlassNight": (32, 32), "M_Soot": (32, 32), "M_Calf": (256, 128, 256),
                  "M_GreenCloth": (128, 64, 64), "M_BookPages": (256, 64, 128), "M_ClockFace": (128, 32), "M_Wick": (32, 32)},
        default_size=(256, 64, 128))
print("DONE")
