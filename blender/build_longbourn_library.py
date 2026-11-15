"""
Fable: Mr Bennet's library at Longbourn (Pride and Prejudice, chapter 3).

"Mr. Bingley returned Mr. Bennet's visit, and sat about ten minutes with him in his library." ...
"they had the advantage of ascertaining, from an upper window, that he wore a blue coat and rode a black horse."
... "With a book, he was regardless of time"

A modest gentleman's working library in a family house of the 1780s, mid-afternoon, soft grey daylight. Painted
deal shelving fills the south wall, the alcoves either side of the chimney-piece on the west wall and the piers either
side of the east window; the books are well used: calf and sheepskin worn at the joints, a few vellum and boarded
volumes, some leaning, some lying flat, gaps where volumes are out. The writing table stands at the east window with an
open folio, papers, an inkstand with a quill, a sand-caster and a pen-knife; its chair is pushed back. On the north
wall, under a framed county map, two armchairs face each other across a small table, where a short morning call might
be received. A plain painted chimney-piece with a small coal fire burning, a terrestrial globe, a Turkey carpet on
oak boards. Through the window: the lane, a low brick wall, a field gate, a few trees and the cottages of the village
under a pale grey sky. No people.

Light: one direction: soft north-of-east daylight through the single window on the reader's right, the small fire on
the left a warm accent. Exposure is set for the page; the window is bright but not blown out.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet (floor), facing +Y (north), the window on the right
  anchor.reader.look      eye height (1.55 m), 1 m ahead
  anchor.scene.centre     the middle of the carpet
  anchor.room.desk, anchor.room.fireplace, anchor.room.chairs, anchor.room.window
  Lamp.window (POINT just inside the window: the daylight), Lamp.fire (POINT, the hearth)
  fx.fire.hearth (base of the coal fire, size = radius)
  sound.fire.hearth, sound.clock.passage (a long-case clock heard through the door), sound.birds.lane (outside the window)
  Panes_east (the window glass: its material M_PaneGlass is swapped for FableBuild's transparent glass, so the view shows;
              it is deliberately not called WindowGlass, which FableBuild would draw as a flat bright pane)
  far.windowView (the lane and village seen through the window: a backdrop with an emissive baked texture, unlit)

Register the scene as indoor. Axes: metres, Blender +Z up, the reader faces +Y.

Run headless:
  blender -b -P blender/build_longbourn_library.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_longbourn_library.py -- --render --samples 64 --res 1400 --captures captures/blender/longbourn-library
  blender -b -P blender/build_longbourn_library.py -- --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
import pride_interior as I
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       texcoord_obj, wood, noisy, plain, box, cyl, sphere, lathe, tube, sweep, mesh_from, MB, Frame,
                       anchor, fx, sound, light_obj, camera, link)

ARGS = K.setup("longbourn-library", "out/longbourn-library", 1797, "LongbournLibrary", default_samples=64)
OUT = K.OUT; scene = K.scene
rng = random.Random(1797)
scene.cycles.max_bounces = 10; scene.cycles.diffuse_bounces = 6

EYE = 1.55
R = I.Room(-2.7, 2.9, -2.1, 2.7, 3.05, t=0.45)
READER = Vector((0.05, -0.55, 0.0))
WIN_Y = 0.75                       # the window's centre on the east wall
FP_Y = 0.35                        # the chimney-piece's centre on the west wall
DOOR_X = 1.75                      # the door in the south wall (to the hall)

# ----------------------------------------------------------------------------- materials
M_WALL = I.paint_mat("M_WallPaint", K.srgb((0.60, 0.64, 0.58)), rough=0.82)
M_JOIN = I.joinery_mat("M_Joinery", K.srgb((0.80, 0.79, 0.73)))
M_SHELF = I.joinery_mat("M_ShelfPaint", K.srgb((0.52, 0.55, 0.50)), rough=0.5)
M_CEIL = I.paint_mat("M_Ceiling", K.srgb((0.82, 0.81, 0.77)), rough=0.9, dirt=0.0)
M_FLOOR = I.boards_mat("M_FloorBoards", light=(0.26, 0.17, 0.09), dark=(0.11, 0.065, 0.03), width=0.21, axis='Y')
M_CARPET = I.carpet_mat("M_Carpet", -0.05, 0.2, 1.75, 1.45, field=(0.16, 0.035, 0.03), ground2=(0.04, 0.05, 0.10), border=(0.03, 0.04, 0.08), buff=(0.40, 0.31, 0.17))
M_MAHOG = I.mahogany("M_Mahogany")
M_GILT = I.gilt("M_Gilt")
M_BRASS = plain("M_Brass", (0.70, 0.54, 0.30), rough=0.32, metallic=1.0)
M_IRON = noisy("M_Iron", [(0.025, 0.025, 0.027), (0.05, 0.05, 0.05), (0.035, 0.032, 0.03)], scale=30, rough=(0.45, 0.7), metallic=0.6)
M_SOOT = plain("M_Soot", (0.012, 0.011, 0.01), rough=0.95)
M_STONE = noisy("M_Portland", [K.srgb((0.66, 0.64, 0.58)), K.srgb((0.72, 0.70, 0.64)), K.srgb((0.62, 0.60, 0.55))], scale=6, rough=0.7, bump=0.15, ao=0.4)
M_LEATHER = noisy("M_DeskLeather", [K.srgb((0.16, 0.22, 0.16)), K.srgb((0.20, 0.27, 0.19)), K.srgb((0.13, 0.18, 0.13))], scale=10, rough=(0.4, 0.6), bump=0.2, bump_dist=0.001)
M_CHAIRCOVER = I.silk("M_ChairWool", K.srgb((0.42, 0.33, 0.24)), K.srgb((0.50, 0.40, 0.30)), damask=0.0, sheen=0.3, rough=0.85)
M_PAPER = noisy("M_Paper", [K.srgb((0.86, 0.84, 0.77)), K.srgb((0.80, 0.77, 0.69))], scale=30, rough=0.85, bump=0.05)
M_PAGES = noisy("M_BookPages", [K.srgb((0.80, 0.76, 0.64)), K.srgb((0.70, 0.65, 0.54))], scale=200, rough=0.85, stretch=(1, 1, 30), bump=0.0)
M_PANE = plain("M_PaneGlass", (0.6, 0.65, 0.65), rough=0.03, transmission=1.0)
M_PEWTER = plain("M_Pewter", (0.42, 0.42, 0.40), rough=0.35, metallic=1.0)
M_INK = plain("M_InkGlass", (0.01, 0.01, 0.012), rough=0.1)
M_QUILL = plain("M_Quill", K.srgb((0.85, 0.83, 0.78)), rough=0.6, sheen=0.5)

def embers_mat(name="M_Embers"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 30.0, 'DISTANCE_TO_EDGE', (-900, 0))
    glow = maprange(nt, v.outputs["Distance"], 0.0, 0.07, 1, 0, (-700, 0))
    n = noise_(nt, co, 9.0, 4, 0.6, loc=(-900, -250))
    glow = math_(nt, 'MULTIPLY', glow, maprange(nt, n.outputs["Fac"], 0.4, 0.65, 0.1, 1.0, (-700, -250)), (-500, -100))
    col = mix_rgb(nt, 'MIX', glow, (0.02, 0.018, 0.016, 1), (0.9, 0.28, 0.05, 1), (-300, 0))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_rgb(nt, 'MULTIPLY', 1.0, (1.0, 0.33, 0.06, 1), glow, (-300, -300)), b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 2.5
    b.inputs["Roughness"].default_value = 0.9
    return m
M_EMBERS = embers_mat()

def spines_mat(name="M_BookSpines"):
    """every book's binding in one material: its colour from the 'tone' attribute (calf, sheep, vellum, cloth-boards,
    morocco), darkened and rubbed paler at the head, tail and joints; gilt bands and a label from the 'sv' attribute
    (0 at the tail .. 1 at the head of the spine), seen only on the spine face ('face' attribute = 1)."""
    m, nt, b = new_mat(name)
    tone = node(nt, "ShaderNodeAttribute", (-1400, 200)); tone.attribute_name = "tone"
    sv = node(nt, "ShaderNodeAttribute", (-1400, -100)); sv.attribute_name = "sv"
    sf = node(nt, "ShaderNodeAttribute", (-1400, -350)); sf.attribute_name = "face"
    v = node(nt, "ShaderNodeSeparateColor", (-1200, -100)); nt.links.new(sv.outputs["Color"], v.inputs["Color"])
    s = v.outputs[0]; kind = v.outputs[1]              # R = position along the spine, G = band style
    co = obj_coords(nt)
    n = noise_(nt, co, 90.0, 5, 0.6, loc=(-1200, 400))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, tone.outputs["Color"], maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.8, 1.12, (-1000, 400)), (-900, 200))
    # rubbed head and tail
    rub = math_(nt, 'MAXIMUM', maprange(nt, s, 0.0, 0.04, 1, 0, (-1000, -50)), maprange(nt, s, 0.96, 1.0, 0, 1, (-1000, -200)), (-850, -100))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', rub, 0.45, (-750, -100)), col, (0.45, 0.36, 0.26, 1), (-650, 200))
    # gilt bands (raised-band look) and a darker title label, on spines only
    def band(c, w):
        return math_(nt, 'MULTIPLY', maprange(nt, s, c - w, c - w + 0.004, 0, 1, (-1000, -500)), maprange(nt, s, c + w - 0.004, c + w, 1, 0, (-1000, -600)), (-850, -550))
    bands = band(0.16, 0.012)
    for c in (0.36, 0.56, 0.84):
        bands = math_(nt, 'MAXIMUM', bands, band(c, 0.012), (-700, -550))
    label = band(0.72, 0.06)
    on_spine = maprange(nt, sf.outputs["Color"], 0.4, 0.6, 0, 1, (-1000, -800))
    has_gilt = maprange(nt, kind, 0.3, 0.5, 0, 1, (-1000, -950))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', label, on_spine, (-550, -700)), has_gilt, (-450, -700)), col, (0.06, 0.035, 0.02, 1), (-400, 200))
    g = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', bands, on_spine, (-550, -850)), math_(nt, 'MULTIPLY', has_gilt, 0.85, (-550, -950)), (-450, -850))
    col = mix_rgb(nt, 'MIX', g, col, (0.55, 0.40, 0.17, 1), (-250, 200))
    col = K.ao_mul(nt, col, 0.08, 0.5, (-150, -400))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, g, 0.55, 0.3, (-150, -150)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'ADD', bands, math_(nt, 'MULTIPLY', n.outputs["Fac"], 0.3, (-400, -1100)), (-300, -1000)), 0.4, 0.001)
    return m
M_SPINES = spines_mat()

# ----------------------------------------------------------------------------- openings, walls, floor, ceiling, mouldings
# east wall (runs from y0 north): u = y - y0
I.sash_window("Win", R, 'E', WIN_Y - R.y0, 1.05, 0.7, 1.95, M_JOIN, M_PANE, M_JOIN, panes=(3, 4), curtain_mat=I.silk("M_Curtains", K.srgb((0.48, 0.52, 0.44)), K.srgb((0.55, 0.58, 0.50)), damask=0.4, rough=0.8, sheen=0.3),
              pelmet_mat=M_BRASS, drawn=0.0)
M_DOOR = I.joinery_mat("M_DoorPaint", K.srgb((0.62, 0.62, 0.56)), rough=0.4)
I.six_panel_door("Door", R, 'S', DOOR_X - R.x0, 0.9, 2.2, M_DOOR, M_JOIN, M_BRASS, open_deg=0.0, hinge_left=True)
# the chimney-piece takes no opening in the wall (its grate is set into the wall face)
I.build_walls(R, M_WALL)
box("Floor", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.04), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, -0.02), M_FLOOR)
box("Carpet", (3.5, 2.9, 0.01), (-0.05, 0.2, 0.005), M_CARPET, bevel=0.003)
box("Ceiling", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.05), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, R.h + 0.025), M_CEIL)
I.moulding_runs(R, "Skirting", I.skirting_profile(0.2), 0.0, M_JOIN)
I.moulding_runs(R, "Cornice", I.cornice_profile(0.16, 0.18), R.h, M_JOIN, z_band=(R.h - 0.18, R.h))
I.moulding_runs(R, "ChairRail", I.rail_profile(), 0.88, M_JOIN, z_band=(0.85, 0.92), walls=('N',))

# ----------------------------------------------------------------------------- the bookcases and the books
BOOK_TONES = [K.srgb(c) for c in [(0.36, 0.20, 0.11), (0.42, 0.25, 0.13), (0.30, 0.17, 0.09), (0.47, 0.30, 0.17), (0.25, 0.14, 0.08), (0.52, 0.36, 0.22),
                                   (0.33, 0.12, 0.08), (0.20, 0.25, 0.18), (0.18, 0.19, 0.24), (0.62, 0.55, 0.42), (0.70, 0.64, 0.50), (0.40, 0.31, 0.22),
                                   (0.28, 0.22, 0.17), (0.44, 0.17, 0.10)]]
BOOK_W = [9, 9, 9, 8, 7, 6, 5, 5, 2, 3, 2, 4, 6, 3]          # weights: mostly calf and sheep, a few vellum, morocco, boards

class Books:
    """every book in one mesh: a box with 5 faces (no bottom, no back), per-corner 'tone', 'sv' (R = height along the
    spine, G = gilt style), 'face' (1 on the spine)."""
    def __init__(self): self.v = []; self.f = []; self.tone = []; self.sv = []; self.face = []
    def add(self, c, yaw, t, w, h, tone, gilt, lean=0.0, lie=False):
        """c: centre of the book's bottom-front edge on the shelf; spine faces local -Y... the room: we use the frame's
        local axes (x along the shelf, y into the shelf (away from the room), z up)."""
        Fm = Matrix.Rotation(yaw, 3, 'Z'); L = Matrix.Rotation(lean, 3, 'Y')
        if lie: L = Matrix.Rotation(-math.pi / 2, 3, 'Y')          # height along -x, thickness up
        def P(x, y, z): return tuple(Vector(c) + Fm @ (L @ Vector((x, y, z))))
        corners = {}
        for ix in (-1, 1):
            for iy in (0, 1):
                for iz in (0, 1):
                    corners[(ix, iy, iz)] = P(ix * t / 2, iy * w, iz * h)
        quads = [((-1, 0, 0), (1, 0, 0), (1, 0, 1), (-1, 0, 1), 1.0),       # spine (front, facing the room)
                 ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1), 0.0),         # side
                 ((-1, 1, 0), (-1, 0, 0), (-1, 0, 1), (-1, 1, 1), 0.0),     # side
                 ((-1, 0, 1), (1, 0, 1), (1, 1, 1), (-1, 1, 1), 0.0)]       # top (page edges show here: darker tone)
        for q in quads:
            base = len(self.v)
            for k in q[:4]:
                self.v.append(corners[k]); self.sv.append((float(k[2]), gilt, 0.0, 1.0)); self.face.append((q[4],) * 3 + (1.0,))
                tn = tone if q[4] > 0.5 or q is not quads[3] else (0.55, 0.50, 0.40)
                self.tone.append(tuple(tn) + (1.0,))
            self.f.append((base, base + 1, base + 2, base + 3))
    def build(self, name):
        o = mesh_from(name, self.v, self.f, M_SPINES)
        me = o.data
        for an, data in (("tone", self.tone), ("sv", self.sv), ("face", self.face)):
            ca = me.color_attributes.new(an, 'FLOAT_COLOR', 'POINT')
            ca.data.foreach_set("color", np.array(data, np.float32).ravel())
        return o
BOOKS = Books()

def bookcase(name, R, w, u0, u1, z0, z1, depth=0.3, shelves=6, fill=0.9, seed=0, cornice=True, plinth=0.28, cupboard=False):
    """painted deal shelving on wall w between u0 and u1 (from the wall's start), floor-standing from z0 to z1:
    uprights every ~1 m, fixed shelves, a plinth, a small cornice; filled with books of several sizes (folios low down,
    octavos and duodecimos higher), with gaps, leaners and a few lying flat."""
    o, a, n, L = R.wall_frame(w)
    rr = random.Random(seed)
    yaw = math.atan2(a.y, a.x)                               # local x along the wall
    span = u1 - u0; nb = max(1, int(round(span / 0.95)))
    bay = span / nb
    def W(u, d, z): return o + a * u + n * d + Vector((0, 0, z))
    for k in range(nb + 1):
        uu = u0 + k * bay
        box(f"{name}Up{k}", (abs(a.x) * 0.03 + abs(n.x) * depth, abs(a.y) * 0.03 + abs(n.y) * depth, z1 - z0), tuple(W(uu, depth / 2, (z0 + z1) / 2)), M_SHELF, bevel=0.003)
    box(f"{name}Back", (abs(a.x) * span + abs(n.x) * 0.012, abs(a.y) * span + abs(n.y) * 0.012, z1 - z0), tuple(W((u0 + u1) / 2, 0.006, (z0 + z1) / 2)), M_SHELF)
    box(f"{name}Plinth", (abs(a.x) * span + abs(n.x) * 0.02, abs(a.y) * span + abs(n.y) * 0.02, plinth), tuple(W((u0 + u1) / 2, depth - 0.01, z0 + plinth / 2)), M_SHELF)
    if cornice:
        sweep(f"{name}Cornice", [(0.0, 0.0), (depth + 0.03, 0.0), (depth + 0.05, 0.03), (depth + 0.05, 0.07), (depth, 0.08), (0.0, 0.08)], [W(u0 - 0.02, 0, z1), W(u1 + 0.02, 0, z1)], M_SHELF, cap=True)
    heights = []; z = z0 + plinth
    avail = z1 - z - 0.02
    rows = [0.42, 0.36, 0.3] + [0.26] * max(0, shelves - 3)
    rows = rows[:shelves]
    sc = avail / sum(rows); rows = [r * sc for r in rows]
    for i, rh in enumerate(rows):
        box(f"{name}Shelf{i}", (abs(a.x) * span + abs(n.x) * depth, abs(a.y) * span + abs(n.y) * depth, 0.022), tuple(W((u0 + u1) / 2, depth / 2, z + 0.011)), M_SHELF)
        # books on this shelf
        hmax = rh - 0.035
        size_cls = 0 if i == 0 else (1 if i == 1 else (2 if i < 4 else 3))
        for k in range(nb):
            uu = u0 + k * bay + 0.025; uend = u0 + (k + 1) * bay - 0.025
            run_tone = rr.choice(BOOK_TONES); run_left = 0
            while uu < uend - 0.02:
                if rr.random() > fill and run_left == 0:
                    gap = rr.uniform(0.04, 0.25); uu += gap; continue
                if run_left == 0:          # sets of the same binding (a multi-volume work)
                    run_left = rr.choice([1, 1, 1, 2, 3, 4, 6, 8]); run_tone = rr.choices(BOOK_TONES, weights=BOOK_W)[0]
                    hh = [0.40, 0.31, 0.23, 0.18][size_cls] * rr.uniform(0.82, 1.0); hh = min(hh, hmax)
                    ww = hh * rr.uniform(0.68, 0.78); tt = [0.055, 0.04, 0.032, 0.026][size_cls] * rr.uniform(0.7, 1.4)
                    gilt = 1.0 if rr.random() < 0.75 else 0.0
                    run_h, run_w, run_t = hh, min(ww, depth - 0.03), tt
                tone = tuple(c * rr.uniform(0.9, 1.08) for c in run_tone)
                t = run_t * rr.uniform(0.92, 1.08)
                if uu + t > uend: break
                lean = 0.0
                if rr.random() < 0.03 and run_left == 1:                 # a leaner at the end of a run
                    lean = rr.choice((-1, 1)) * rr.uniform(0.15, 0.3)
                if rr.random() < 0.012 and hmax > run_w + 0.02:          # one lying flat (a short pile)
                    for j in range(rr.randint(1, 3)):
                        BOOKS.add(tuple(W(uu + run_h, depth - 0.02 - run_w, z + 0.022 + run_t / 2 + j * run_t)), yaw, run_t, run_w, run_h, tone, gilt, lie=True)
                    uu += run_h + 0.02; run_left = 0; continue
                setback = rr.uniform(0.0, 0.025)
                BOOKS.add(tuple(W(uu + t / 2, depth - 0.012 - setback - run_w + run_w, z + 0.022)), yaw + math.pi, t, run_w, run_h * rr.uniform(0.97, 1.0), tone, gilt, lean=lean)
                uu += t + rr.uniform(0.0, 0.004); run_left -= 1
        z += rh
    box(f"{name}Top", (abs(a.x) * span + abs(n.x) * depth, abs(a.y) * span + abs(n.y) * depth, 0.022), tuple(W((u0 + u1) / 2, depth / 2, z1 - 0.011)), M_SHELF)

# south wall (runs from x0 east): bookcases either side of the door
bookcase("CaseS1", R, 'S', 0.0, DOOR_X - R.x0 - 0.62, 0.0, 2.55, shelves=7, seed=1)
bookcase("CaseS2", R, 'S', DOOR_X - R.x0 + 0.62, R.x1 - R.x0, 0.0, 2.55, shelves=7, seed=2)
# west wall (runs from y1 south): the alcoves either side of the chimney-piece
FPU = R.y1 - FP_Y
bookcase("CaseW1", R, 'W', 0.0, FPU - 0.98, 0.0, 2.55, shelves=7, seed=3)
bookcase("CaseW2", R, 'W', FPU + 0.98, R.y1 - R.y0 - 0.32, 0.0, 2.55, shelves=7, seed=4)
# east wall (runs from y0 north): the piers either side of the window
WU = WIN_Y - R.y0
bookcase("CaseE1", R, 'E', 0.32, WU - 0.92, 0.0, 2.55, shelves=7, seed=5)
bookcase("CaseE2", R, 'E', WU + 0.92, R.y1 - R.y0, 0.0, 2.55, shelves=7, seed=6)
BOOKS.build("Books")

# ----------------------------------------------------------------------------- the chimney-piece (west wall): plain Portland stone, a small coal grate, fire burning
F = Frame((R.x0, FP_Y), -math.pi / 2)
def FP(x, y, z): return F.p(x, y, z)
OW, OH = 0.78, 0.82
F.box("HearthStone", (1.45, 0.45, 0.035), (0, 0.22, 0.017), M_STONE, bevel=0.004)
for sx in (-1, 1):
    F.box(f"Jamb{sx}", (0.2, 0.12, OH), (sx * (OW / 2 + 0.1), 0.06, OH / 2), M_STONE, bevel=0.006)
F.box("Lintel", (OW + 0.4, 0.12, 0.2), (0, 0.06, OH + 0.1), M_STONE, bevel=0.006)
F.box("Shelf", (1.42, 0.2, 0.045), (0, 0.1, OH + 0.225), M_STONE, bevel=0.01)
F.box("GratePlate", (OW, 0.03, OH), (0, 0.012, OH / 2), M_IRON)
F.box("GrateMouth", (OW * 0.6, 0.03, OH * 0.55), (0, 0.02, OH * 0.4), M_SOOT)
F.box("BasketFloor", (0.46, 0.2, 0.025), (0, 0.11, 0.14), M_IRON)
for k in range(4): F.box(f"BasketBar{k}", (0.46, 0.012, 0.012), (0, 0.22, 0.16 + k * 0.045), M_IRON, bevel=0.003)
for sx in (-1, 1): F.box(f"BasketSide{sx}", (0.02, 0.2, 0.2), (sx * 0.23, 0.11, 0.23), M_IRON)
cr = random.Random(4)
for k in range(18):
    lx = cr.uniform(-0.19, 0.19); ly = cr.uniform(0.03, 0.2); lz = 0.17 + cr.uniform(0, 0.08) * (1 - abs(lx) / 0.24)
    sphere(f"Coal{k}", cr.uniform(0.025, 0.045), FP(lx, ly, lz), M_EMBERS if lz < 0.22 or cr.random() < 0.5 else M_IRON, seg=6,
           scale=(cr.uniform(0.8, 1.3), cr.uniform(0.8, 1.3), cr.uniform(0.6, 0.9)))
FIRE_BASE = Vector(FP(0, 0.12, 0.2))
# no render-only fire flames: the glowing coals and the light carry the stills; Unity draws flames at fx.fire.hearth
F.box("FenderFront", (1.25, 0.01, 0.08), (0, 0.42, 0.04), M_IRON, bevel=0.003)
for sx in (-1, 1): F.box(f"FenderSide{sx}", (0.01, 0.3, 0.08), (sx * 0.62, 0.28, 0.04), M_IRON, bevel=0.003)
for k in range(2):
    p0 = Vector(FP(0.55, 0.25 + 0.04 * k, 0.05)); p1 = Vector(FP(0.53 - 0.03 * k, 0.08, 0.68))
    tube(f"FireIron{k}", [p0, p1], 0.007, M_IRON, sides=5); sphere(f"FireIronKnob{k}", 0.016, tuple(p1), M_BRASS, seg=8)
SHELF_Z = OH + 0.25
# on the shelf: a pair of brass candlesticks (unlit; it is afternoon), a tobacco jar, a spill vase
I.candlestick("MantelStick0", FP(-0.55, 0.1, SHELF_Z), M_BRASS, plain("M_Tallow", K.srgb((0.86, 0.82, 0.70)), rough=0.5), height=0.24, candle_h=0.15, flame=False)
I.candlestick("MantelStick1", FP(0.55, 0.1, SHELF_Z), M_BRASS, plain("M_Tallow2", K.srgb((0.86, 0.82, 0.70)), rough=0.5), height=0.24, candle_h=0.12, flame=False)
lathe("TobaccoJar", [(0.0, 0.0), (0.06, 0.0), (0.07, 0.04), (0.068, 0.13), (0.05, 0.15), (0.052, 0.17), (0.02, 0.19), (0.0, 0.19)], FP(-0.2, 0.1, SHELF_Z), M_PEWTER, steps=14)
lathe("SpillVase", [(0.0, 0.0), (0.035, 0.0), (0.03, 0.05), (0.025, 0.12), (0.032, 0.14), (0.0, 0.14)], FP(0.25, 0.1, SHELF_Z), M_PEWTER, steps=12)
for k in range(6):
    tube(f"Spill{k}", [FP(0.25 + cr.gauss(0, 0.006), 0.1 + cr.gauss(0, 0.006), SHELF_Z + 0.05), FP(0.25 + cr.gauss(0, 0.02), 0.1 + cr.gauss(0, 0.02), SHELF_Z + 0.22 + cr.uniform(0, 0.04))], 0.003, M_PAPER, sides=3)
# over the shelf: a framed engraving (a landscape)
M_PRINT = I.landscape_mat("M_Engraving", 3)
I.picture("Engraving", R, 'W', FPU, 1.85, 0.62, 0.46, M_GILT, M_PRINT)
anchor("room.fireplace", FP(0, 0.4, 0))

# ----------------------------------------------------------------------------- the writing table at the window, its chair, the papers
DESK = Vector((2.15, WIN_Y, 0))
D = Frame((DESK.x, DESK.y), math.pi / 2)        # local +Y -> world -X (the sitter faces the window... the desk front faces into the room)
D = Frame((DESK.x, DESK.y), math.atan2(1, 0))   # local +Y -> world -X: the writer sits on the room side facing east
DW, DD, DH = 1.25, 0.68, 0.76
D.box("DeskTop", (DW, DD, 0.03), (0, 0, DH - 0.015), M_MAHOG, bevel=0.006)
D.box("DeskLeather", (DW - 0.12, DD - 0.12, 0.003), (0, 0, DH + 0.001), M_LEATHER)
D.box("DeskFrieze", (DW - 0.06, DD - 0.06, 0.12), (0, 0, DH - 0.09), M_MAHOG, bevel=0.004)
for sx in (-1, 1):
    D.box(f"DeskDrawerFront{sx}", (0.5, 0.008, 0.08), (sx * 0.3, DD / 2 - 0.027, DH - 0.09), M_MAHOG, bevel=0.003)
    sphere(f"DeskKnob{sx}", 0.013, D.p(sx * 0.3, DD / 2 - 0.015, DH - 0.09), M_BRASS, seg=8)
    for sy in (-1, 1):
        lathe(f"DeskLeg{sx}{sy}", [(0.0, 0.0), (0.016, 0.0), (0.018, 0.04), (0.022, 0.08), (0.026, 0.4), (0.03, 0.55), (0.028, DH - 0.15), (0.0, DH - 0.15)],
              D.p(sx * (DW / 2 - 0.06), sy * (DD / 2 - 0.06), 0), M_MAHOG, steps=10)
anchor("room.desk", tuple(DESK))
# the chair, pushed back and turned (the writer has just got up)
I.sabre_chair("DeskChair", (DESK.x - 0.78, DESK.y - 0.25), math.atan2(-1, 0) * -1 + 0.35 - math.pi, M_MAHOG, M_CHAIRCOVER)
# an open folio on a slope, papers, inkstand with quill, sand-caster, a pen-knife, spectacles
dz = DH + 0.004
def open_book(name, c, yaw, w=0.2, h=0.3, t=0.04, open_ang=0.12):
    Fo = Frame((c[0], c[1]), yaw, z=c[2])
    for sx in (-1, 1):
        Fo.box(f"{name}Board{sx}", (w, h, 0.004), (sx * w / 2, 0, 0.002), M_MAHOG if False else noisy_calf, ry=sx * 0.03)
        # the text block of each half, slightly domed toward the gutter
        verts = []; faces = []
        nx, ny = 8, 2
        for j in range(ny + 1):
            for i in range(nx + 1):
                s = i / nx; yy = -h / 2 + 0.008 + (h - 0.016) * j / ny
                xx = sx * (0.004 + (w - 0.012) * s)
                zz = 0.006 + (t / 2) * (1 - s) ** 0.5 * 0.9 + 0.004 * math.sin(math.pi * s)
                verts.append(Fo.p(xx, yy, zz))
        for j in range(ny):
            for i in range(nx):
                a_ = j * (nx + 1) + i; faces.append((a_, a_ + 1, a_ + nx + 2, a_ + nx + 1) if sx > 0 else (a_, a_ + nx + 1, a_ + nx + 2, a_ + 1))
        mesh_from(f"{name}Pages{sx}", verts, faces, M_PRINTED, smooth=True)
noisy_calf = noisy("M_Calf", [K.srgb((0.36, 0.20, 0.11)), K.srgb((0.44, 0.26, 0.14)), K.srgb((0.30, 0.17, 0.09))], scale=14, rough=(0.35, 0.6), bump=0.3, bump_dist=0.001)
def printed_mat(name="M_PrintedPage"):
    """a printed page seen from a metre: two columns of grey text lines in a margin, a running head."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1400, 0))
    rot = node(nt, "ShaderNodeVectorRotate", (-1300, -300), rotation_type='Z_AXIS'); rot.inputs["Angle"].default_value = math.radians(90) + DESK_YAW
    nt.links.new(co, rot.inputs["Vector"]); sp = sep_xyz(nt, rot.outputs[0], (-1150, -300))
    lines = math_(nt, 'FRACT', math_(nt, 'DIVIDE', sp.outputs["Y"], 0.0042, (-1000, -300)), None, (-900, -300))
    ln = maprange(nt, lines, 0.15, 0.25, 1, 0, (-800, -300))
    wn = noise_(nt, rot.outputs[0], 900.0, 2, 0.5, loc=(-1000, -500))
    ln = math_(nt, 'MULTIPLY', ln, maprange(nt, wn.outputs["Fac"], 0.42, 0.5, 0.0, 1.0, (-800, -500)), (-650, -400))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', ln, 0.55, (-500, -400)), K.c4(K.srgb((0.86, 0.83, 0.74))), (0.12, 0.11, 0.1, 1), (-300, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    return m
DESK_YAW = D.yaw
M_PRINTED = printed_mat()
open_book("Folio", D.p(-0.05, 0.05, dz), D.yaw + 0.08, w=0.22, h=0.33, t=0.05)
for k in range(5):
    D.box(f"Paper{k}", (0.21, 0.29, 0.0006), (0.38 + rng.gauss(0, 0.03), -0.04 + rng.gauss(0, 0.03), DH + 0.004 + k * 0.0007), M_PAPER)
    bpy.context.view_layer.objects.active = None
# inkstand: a mahogany tray, two glass wells with pewter lids, a quill
D.box("InkTray", (0.26, 0.16, 0.025), (-0.42, -0.2, DH + 0.0125), M_MAHOG, bevel=0.006)
for k, xo in enumerate((-0.48, -0.36)):
    D.cyl(f"InkWell{k}", 0.03, 0.05, (xo, -0.2, DH + 0.05), M_INK, verts=10)
    D.cyl(f"InkLid{k}", 0.033, 0.008, (xo, -0.2, DH + 0.078), M_PEWTER, verts=10)
qp0 = Vector(D.p(-0.48, -0.2, DH + 0.06)); qp1 = Vector(D.p(-0.32, -0.08, DH + 0.24))
tube("QuillShaft", [qp0, qp1], [0.003, 0.002], M_QUILL, sides=4)
qv = []; qf = []
for i in range(6):
    t = 0.35 + 0.65 * i / 5; p = qp0.lerp(qp1, t); wq = 0.012 * math.sin(math.pi * (i / 5) * 0.9 + 0.2)
    side = (qp1 - qp0).cross(Vector((0, 0, 1))).normalized()
    qv += [tuple(p - side * wq * 0.3), tuple(p + side * wq)]
for i in range(5): qf.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
mesh_from("QuillVane", qv, qf, M_QUILL)
D.cyl("SandCaster", 0.022, 0.07, (-0.2, -0.24, DH + 0.035), M_PEWTER, verts=10)
# a terrestrial globe on a tripod stand near the desk (continents are invented shapes)
def globe_mat():
    m, nt, b = new_mat("M_Globe")
    co = obj_coords(nt)
    n = noise_(nt, co, 2.6, 4, 0.55, loc=(-900, 0))
    land = maprange(nt, n.outputs["Fac"], 0.52, 0.54, 0, 1, (-700, 0))
    col = mix_rgb(nt, 'MIX', land, K.c4(K.srgb((0.62, 0.62, 0.50))), K.c4(K.srgb((0.66, 0.55, 0.36))), (-500, 0))
    col = mix_rgb(nt, 'MULTIPLY', 0.4, col, (0.85, 0.72, 0.48, 1), (-300, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.35
    return m
G = Vector((1.85, 2.05, 0))
sphere("Globe", 0.23, (G.x, G.y, 0.95), globe_mat(), seg=20)

from pride_kit import box as _b
lathe("GlobePillar", [(0.0, 0.1), (0.05, 0.1), (0.06, 0.14), (0.035, 0.2), (0.03, 0.4), (0.045, 0.5), (0.028, 0.6), (0.022, 0.7), (0.0, 0.7)], (G.x, G.y, 0), M_MAHOG, steps=12)
for k in range(3):
    a = 2 * math.pi * k / 3 + 0.3; d = Vector((math.cos(a), math.sin(a), 0))
    tube(f"GlobeFoot{k}", [G + d * 0.04 + Vector((0, 0, 0.14)), G + d * 0.2 + Vector((0, 0, 0.07)), G + d * 0.3 + Vector((0, 0, 0.01))], [0.03, 0.022, 0.016], M_MAHOG, sides=6)
for sgn in (-1, 1):
    d = Vector((math.cos(0.6) * sgn, math.sin(0.6) * sgn, 0))
    tube(f"GlobeBracket{sgn}", [Vector((G.x, G.y, 0.68)), Vector((G.x, G.y, 0.68)) + d * 0.18 + Vector((0, 0, 0.06)), Vector((G.x, G.y, 0.93)) + d * 0.285], 0.012, M_MAHOG, sides=5)
lathe("GlobeHorizon", [(0.27, 0.0), (0.30, 0.0), (0.30, 0.02), (0.27, 0.02)], (G.x, G.y, 0.93), M_MAHOG, steps=32)
lathe("GlobeMeridian", [(0.245, -0.012), (0.255, -0.012), (0.255, 0.012), (0.245, 0.012)], (G.x, G.y, 0.95), M_BRASS, steps=32, rot=(math.pi / 2, 0, 0.6))

# ----------------------------------------------------------------------------- two chairs facing each other across a small table, under the county map (north wall)
def face(pos, target): return math.atan2(-(target[0] - pos[0]), target[1] - pos[1])
def armchair(name, x, y, yaw):
    F2 = Frame((x, y), yaw)
    F2.box(f"{name}Frame", (0.62, 0.58, 0.1), (0, 0, 0.36), M_MAHOG, bevel=0.01)
    F2.box(f"{name}Seat", (0.54, 0.5, 0.09), (0, 0.03, 0.45), M_CHAIRCOVER, bevel=0.03)
    F2.box(f"{name}Back", (0.56, 0.08, 0.5), (0, -0.26, 0.74), M_CHAIRCOVER, bevel=0.035, rx=-0.12)
    for sx in (-1, 1):
        # back uprights (raked), arms from the uprights to turned front supports, short tapered legs
        tube(f"{name}Upright{sx}", [F2.p(sx * 0.29, -0.25, 0.40), F2.p(sx * 0.29, -0.29, 0.72), F2.p(sx * 0.285, -0.33, 1.0)], 0.02, M_MAHOG, sides=6)
        tube(f"{name}Arm{sx}", [F2.p(sx * 0.29, -0.27, 0.66), F2.p(sx * 0.30, 0.05, 0.67), F2.p(sx * 0.30, 0.24, 0.66)], 0.019, M_MAHOG, sides=6)
        tube(f"{name}ArmPost{sx}", [F2.p(sx * 0.30, 0.24, 0.66), F2.p(sx * 0.29, 0.25, 0.53), F2.p(sx * 0.28, 0.24, 0.41)], [0.022, 0.016, 0.02], M_MAHOG, sides=6)
        F2.box(f"{name}ArmPad{sx}", (0.05, 0.28, 0.02), (sx * 0.30, -0.03, 0.685), M_CHAIRCOVER, bevel=0.008)
        for sy in (-1, 1):
            F2.cyl(f"{name}Leg{sx}{sy}", 0.02, 0.32, (sx * 0.27, sy * 0.24, 0.16), M_MAHOG, verts=8, r2=0.015)
    tube(f"{name}Crest", [F2.p(-0.285, -0.33, 1.0), F2.p(0, -0.35, 1.02), F2.p(0.285, -0.33, 1.0)], 0.022, M_MAHOG, sides=6)
CH = Vector((-0.35, R.y1 - 0.75, 0))
armchair("ChairA", CH.x - 0.75, CH.y, face((CH.x - 0.75, CH.y), (CH.x + 0.75, CH.y - 0.2)))
armchair("ChairB", CH.x + 0.75, CH.y, face((CH.x + 0.75, CH.y), (CH.x - 0.75, CH.y - 0.2)))
st = I.pedestal_table("SmallTable", (CH.x, CH.y + 0.1), M_MAHOG, M_MAHOG, radius=0.3, height=0.62, feet=3)
I.book("TableBook", (CH.x + 0.05, CH.y + 0.08, st[2] + 0.012), (0.024, 0.12, 0.19), 0.4, noisy_calf, M_PAGES, roll=math.pi / 2)
anchor("room.chairs", tuple(CH))
def map_mat():
    """an old county map: pale toned paper, a hatched border, a meandering river, roads, hachured hills, woods in
    green wash. Invented geography; no names."""
    m, nt, b = new_mat("M_CountyMap")
    co = node(nt, "ShaderNodeTexCoord", (-1600, 0)); g = co.outputs["Generated"]; s = sep_xyz(nt, g, (-1400, 0))
    paper = mix_rgb(nt, 'MIX', maprange(nt, noise_(nt, g, 4.0, 4, 0.6, loc=(-1200, 300)).outputs["Fac"], 0.3, 0.7, 0, 1, (-1000, 300)),
                    K.c4(K.srgb((0.82, 0.77, 0.62))), K.c4(K.srgb((0.74, 0.68, 0.52))), (-800, 300))
    river = noise_(nt, g, 2.0, 3, 0.5, distortion=1.0, loc=(-1200, 0))
    rv = math_(nt, 'MULTIPLY', maprange(nt, river.outputs["Fac"], 0.495, 0.5, 0, 1, (-1000, 0)), maprange(nt, river.outputs["Fac"], 0.5, 0.505, 1, 0, (-1000, -100)), (-850, -50))
    roads = voronoi_(nt, g, 7.0, 'DISTANCE_TO_EDGE', (-1200, -300))
    rd = maprange(nt, roads.outputs["Distance"], 0.0, 0.012, 1, 0, (-1000, -300))
    woods = maprange(nt, noise_(nt, g, 9.0, 4, 0.6, loc=(-1200, -550)).outputs["Fac"], 0.6, 0.62, 0, 1, (-1000, -550))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', woods, 0.45, (-700, -550)), paper, K.c4(K.srgb((0.52, 0.58, 0.40))), (-600, 300))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', rd, 0.6, (-700, -300)), col, (0.30, 0.22, 0.14, 1), (-450, 300))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', rv, 0.8, (-700, 0)), col, K.c4(K.srgb((0.34, 0.44, 0.52))), (-300, 300))
    # neat-line border
    ex = math_(nt, 'MINIMUM', math_(nt, 'MINIMUM', s.outputs["X"], math_(nt, 'SUBTRACT', 1.0, s.outputs["X"], (-1200, -800)), (-1050, -800)),
               math_(nt, 'MINIMUM', s.outputs["Z"], math_(nt, 'SUBTRACT', 1.0, s.outputs["Z"], (-1200, -950)), (-1050, -950)), (-900, -850))
    ey = math_(nt, 'MINIMUM', ex, math_(nt, 'MINIMUM', s.outputs["Y"], math_(nt, 'SUBTRACT', 1.0, s.outputs["Y"], (-1200, -1100)), (-1050, -1100)), (-800, -950))
    border = math_(nt, 'MULTIPLY', maprange(nt, ey, 0.03, 0.035, 1, 0, (-650, -900)), 1.0, (-500, -900))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', border, 0.5, (-400, -900)), col, (0.25, 0.2, 0.14, 1), (-150, 300))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.6
    return m
I.picture("CountyMap", R, 'N', R.x1 - CH.x, 1.85, 1.15, 0.85, M_MAHOG, map_mat())
# a long-case clock? (no: it stands in the passage; heard through the door)

# ----------------------------------------------------------------------------- the view through the window (a backdrop: lane, brick wall, gate, trees, cottages, grey sky)
def view_mat(name="M_WindowView"):
    """painted from the window's point of view onto a curved backdrop 7 m outside: pale grey afternoon sky, a line of
    elms and a cottage roof beyond the lane, the lane itself, the low garden wall of old red-brown brick with a white
    field gate, the lawn below the window. Baked as an emissive texture (unlit backdrop)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1800, 0))
    z = s.outputs["Z"]; yy = s.outputs["Y"]
    sky = mix_rgb(nt, 'MIX', maprange(nt, z, 2.0, 7.0, 0, 1, (-1500, 400)), (0.78, 0.80, 0.80, 1), (0.62, 0.66, 0.72, 1), (-1300, 400))
    cl = noise_(nt, co, 0.35, 5, 0.6, 0.3, (-1500, 650))
    sky = mix_rgb(nt, 'MIX', maprange(nt, cl.outputs["Fac"], 0.45, 0.65, 0, 0.35, (-1300, 650)), sky, (0.88, 0.88, 0.86, 1), (-1100, 400))
    # trees: billowy line, top varying with Y
    tn = noise_(nt, co, 0.6, 6, 0.7, 0.4, (-1500, 100))
    tree_top = math_(nt, 'ADD', 2.6, math_(nt, 'MULTIPLY', tn.outputs["Fac"], 3.2, (-1300, 100)), (-1200, 100))
    is_tree = maprange(nt, math_(nt, 'SUBTRACT', tree_top, z, (-1100, 100)), 0.0, 0.08, 0, 1, (-1000, 100))
    leaf = noise_(nt, co, 6.0, 5, 0.6, loc=(-1300, -100))
    tcol = mix_rgb(nt, 'MIX', maprange(nt, leaf.outputs["Fac"], 0.35, 0.65, 0, 1, (-1100, -100)), (0.14, 0.15, 0.10, 1), (0.30, 0.27, 0.15, 1), (-950, -100))
    col = mix_rgb(nt, 'MIX', is_tree, sky, tcol, (-800, 300))
    # a cottage: a pale gable wall and a dark thatch/tile roof, left of centre
    cot = math_(nt, 'MULTIPLY', maprange(nt, yy, -2.6, -2.5, 0, 1, (-1300, -400)), maprange(nt, yy, -0.4, -0.3, 1, 0, (-1300, -500)), (-1150, -450))
    roof_h = math_(nt, 'SUBTRACT', 3.3, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', yy, -1.45, (-1300, -650)), None, (-1200, -650)), (-1100, -650))
    in_roof = math_(nt, 'MULTIPLY', cot, maprange(nt, math_(nt, 'SUBTRACT', roof_h, z, (-1000, -650)), 0.0, 0.03, 0, 1, (-900, -650)), (-800, -600))
    in_wall = math_(nt, 'MULTIPLY', cot, maprange(nt, z, 1.95, 2.0, 1, 0, (-1000, -800)), (-800, -800))
    col = mix_rgb(nt, 'MIX', in_roof, col, (0.20, 0.17, 0.14, 1), (-650, 300))
    col = mix_rgb(nt, 'MIX', in_wall, col, (0.66, 0.62, 0.54, 1), (-550, 300))
    # the lane (pale, damp) and the verge
    lane = maprange(nt, z, 0.95, 1.0, 1, 0, (-1300, -1000))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', lane, maprange(nt, z, 0.55, 0.6, 0, 1, (-1150, -1100)), (-1000, -1050)), col, (0.42, 0.40, 0.34, 1), (-450, 300))
    # the garden wall: old brick with a coping, a white gate in it right of centre
    wall = maprange(nt, z, 0.55, 0.58, 1, 0, (-1300, -1300))
    brick = voronoi_(nt, co, 14.0, loc=(-1300, -1500))
    bcol = mix_rgb(nt, 'MIX', maprange(nt, brick.outputs["Distance"], 0.1, 0.4, 0, 1, (-1100, -1500)), (0.30, 0.14, 0.09, 1), (0.40, 0.22, 0.15, 1), (-950, -1450))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', wall, maprange(nt, z, 0.1, 0.15, 0, 1, (-1150, -1350)), (-1000, -1350)), col, bcol, (-350, 300))
    gate = math_(nt, 'MULTIPLY', maprange(nt, yy, 0.6, 0.65, 0, 1, (-1300, -1700)), maprange(nt, yy, 1.8, 1.85, 1, 0, (-1300, -1800)), (-1150, -1750))
    bars = maprange(nt, math_(nt, 'FRACT', math_(nt, 'DIVIDE', z, 0.11, (-1300, -1950)), None, (-1200, -1950)), 0.0, 0.25, 1, 0, (-1100, -1950))
    gm = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', gate, bars, (-1000, -1850)), maprange(nt, z, 0.62, 0.65, 1, 0, (-1000, -2000)), (-900, -1900))
    col = mix_rgb(nt, 'MIX', gm, col, (0.62, 0.62, 0.58, 1), (-250, 300))
    # the lawn below
    lawn = maprange(nt, z, 0.1, 0.15, 1, 0, (-1300, -2200))
    col = mix_rgb(nt, 'MIX', lawn, col, (0.17, 0.22, 0.10, 1), (-150, 300))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0
    return m
M_VIEW = view_mat()
# the backdrop: a curved panel 6 m outside the east wall, ground level 0.9 m below the floor (a raised ground floor)
vv = []; vf = []; vu = []
for j in range(3):
    for i in range(13):
        a = math.radians(-60 + 120 * i / 12); r = 6.5
        vv.append((R.x1 + 0.4 + r * math.cos(a) * 0.9, WIN_Y + r * math.sin(a), -0.9 + 8.0 * j / 2)); vu.append((i / 12, j / 2))
for j in range(2):
    for i in range(12): vf.append((j * 13 + i, j * 13 + i + 1, (j + 1) * 13 + i + 1, (j + 1) * 13 + i))
view = mesh_from("WindowView", [(x, y, z) for (x, y, z) in vv], vf, M_VIEW, uvs=vu)
for p in view.data.polygons: p.flip()
# the view's coordinates for the painting: z above the outside ground, y across
for v in view.data.vertices: pass
view.visible_shadow = False; view.visible_diffuse = False
anchor("room.window", R.at('E', WIN_Y - R.y0, 1.6))

# ----------------------------------------------------------------------------- lights
WINP = Vector(R.at('E', WIN_Y - R.y0, 1.65)) + Vector((-0.45, 0, 0))
light_obj("Lamp.window", 'POINT', 30.0, (0.86, 0.90, 1.0), tuple(WINP), shadow_soft_size=0.6)
light_obj("Lamp.fire", 'POINT', 30.0, (1.0, 0.55, 0.26), tuple(FIRE_BASE + Vector((0.15, 0, 0.12))), shadow_soft_size=0.15)
# render-only: the daylight through the window as an area light in the opening, plus the sky
ld = bpy.data.lights.new("RenderOnly_WindowArea", 'AREA'); ld.energy = 260.0; ld.color = (0.84, 0.89, 1.0); ld.shape = 'RECTANGLE'; ld.size = 1.0; ld.size_y = 1.9
wa = bpy.data.objects.new("RenderOnly_WindowArea", ld); wa.location = Vector(R.at('E', WIN_Y - R.y0, 1.67)) + Vector((0.12, 0, 0)); K.link(wa)
wa.rotation_euler = Vector((-1, -0.25, -0.25)).to_track_quat('-Z', 'Y').to_euler(); I.RENDER_ONLY.append(wa)
world = bpy.data.worlds.new("GreyAfternoon"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.58, 0.62, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors, sources
fwd = Vector((0, 1, 0))
anchor("reader.entrance", tuple(READER))
anchor("reader.look", tuple(READER + fwd + Vector((0, 0, EYE))))
anchor("scene.centre", (-0.05, 0.2, 0.0))
fx("fx.fire.hearth", tuple(FIRE_BASE), 0.2)
sound("fire", "hearth", tuple(FIRE_BASE + Vector((0.2, 0, 0.1))))
sound("clock", "passage", (DOOR_X, R.y0 - 1.2, 1.6))
sound("birds", "lane", (R.x1 + 6.0, WIN_Y, 3.0))

page = box("PagePreview", (0.4, 0.004, 0.55), tuple(READER + fwd * 0.6 + Vector((0, 0, EYE - 0.05))), plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9))
K.apply_transforms()

# ----------------------------------------------------------------------------- cameras
E = READER + Vector((0, 0, EYE))
def yawed(deg, dist=4.0, dz=-0.6):
    a = math.radians(deg); return tuple(E + Vector((math.sin(a), math.cos(a), 0)) * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(E), yawed(0, 5, -0.6), lens=17),
    camera("Cam_Page", tuple(E), yawed(0, 5, -0.6), lens=17),
    camera("Cam_Left", tuple(E), yawed(-80, 5, -0.6), lens=17),
    camera("Cam_Right", tuple(E), yawed(75, 5, -0.6), lens=17),
    camera("Cam_Behind", tuple(E), yawed(180, 5, -0.4), lens=17),
    camera("Cam_Down", tuple(E), tuple(READER + Vector((0.1, 1.3, 0))), lens=17),
    camera("Cam_Up", tuple(E), tuple(READER + Vector((0, 1.6, R.h))), lens=17),
    camera("Cam_Desk", tuple(DESK + Vector((-1.2, -0.7, 1.45))), tuple(DESK + Vector((0, 0, 0.8))), lens=28),
    camera("Cam_Shelves", tuple(E + Vector((0.2, 0.6, -0.1))), tuple(Vector(R.at('S', 1.4, 1.2))), lens=24),
]
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "longbourn_library_source.blend"))
K.print_budget(exclude=("PagePreview",) + tuple(o.name for o in I.RENDER_ONLY))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.0, captures_dir=ARGS.captures)

if ARGS.bake or ARGS.export:
    for o in I.RENDER_ONLY:
        if o.name in bpy.data.objects: bpy.data.objects.remove(o)
    K.bake_and_export(
        "longbourn_library.gltf", cams, page=page,
        keep_names={"M_Embers": "MESH_Embers", "M_PaneGlass": "Panes_east", "M_WindowView": "far.windowView"},
        unlit_emit=("M_WindowView",),
        size_for={"M_FloorBoards": (1024, 256, 1024), "M_Carpet": (2048, 128, 1024), "M_WallPaint": (1024, 64, 512), "M_Ceiling": (512, 32, 128),
                  "M_Joinery": (1024, 128, 512), "M_ShelfPaint": (2048, 128, 512), "M_BookSpines": (2048, 512, 1024), "M_Mahogany": (2048, 256, 1024),
                  "M_Portland": (512, 128, 256), "M_DeskLeather": (256, 64, 128), "M_ChairWool": (512, 64, 256), "M_Paper": (256, 32, 64),
                  "M_PrintedPage": (512, 32), "M_WindowView": (1024,), "M_CountyMap": (512, 32), "M_Engraving": (256, 32), "M_Globe": (256, 64),
                  "M_Curtains": (512, 64, 256), "M_DoorPaint": (512, 64, 256), "M_Iron": (256, 64, 128), "M_Embers": (256, 64, 128),
                  "M_Brass": (64, 32), "M_Pewter": (64, 32), "M_PaneGlass": (32, 32), "M_Soot": (32, 32), "M_InkGlass": (32, 32), "M_Quill": (64, 32),
                  "M_Calf": (256, 64, 128), "M_BookPages": (256, 64, 128), "M_Gilt": (256, 128, 128), "M_Wick": (32, 32)},
        default_size=(256, 64, 128))
print("DONE")
