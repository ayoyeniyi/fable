"""
Fable: Victor Frankenstein's garret laboratory at Ingolstadt (Frankenstein, 1818, volume I, chapters 3-4).

"In a solitary chamber, or rather cell, at the top of the house, and separated from all the other apartments by a
gallery and staircase, I kept my workshop of filthy creation."
"It was on a dreary night of November, that I beheld the accomplishment of my toils. With an anxiety that almost
amounted to agony, I collected the instruments of life around me, that I might infuse a spark of being into the
lifeless thing that lay at my feet. It was already one in the morning; the rain pattered dismally against the panes,
and my candle was nearly burnt out ..."

A student's room under the roof of an old house in Ingolstadt, past midnight in November. The roof slopes down on
both sides to low knee walls; black oak rafters, purlins and collar ties overhead; lime plaster gone yellow and
damp-stained; wide worn pine boards. Ahead, in the east gable, a single narrow casement of small panes with rain
running down it and the wet roofs and towers of the town beyond, barely lit. On the left, under the slope, the
workbench: retorts, flasks and receivers, a Leyden jar and a voltaic pile, a mortar, books open and stacked, sheets
of anatomical drawings, an inkstand, and a candle burnt down to a stub in its pewter stick. On the right, on a long
deal table, a long form lies under a linen sheet (nothing of it shows). Behind the reader a fire is dying in the
small grate of the chimney breast; a narrow bed under the slope, the low door, a shelf of books and jars.
No people.

Builds the room procedurally (no downloaded models, textures or HDRIs) with PBR node materials and numpy-painted
drawings and night view, then (by flag) renders Cycles stills, bakes materials to textures, merges static meshes by
material and exports a .gltf + .bin + textures/ for Unity (helpers in frankenstein_kit.py / wotw_kit.py).

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet (floor, z=0), in the middle of the garret, facing east (+X)
  anchor.reader.look      eye height (1.55 m), 2 m ahead: the window in the east gable
  anchor.scene.centre     the floor in the middle of the room
  anchor.room.window, anchor.room.fire, anchor.room.candle, anchor.room.bench, anchor.room.form, anchor.room.door
  Lamp.candle (POINT, the candle stub on the bench, warm), Lamp.fire (POINT, low in the grate, deep orange),
  Lamp.window (SPOT, outside the casement, the faint cold night light; wants a cool override 0.55, 0.65, 1.0)
  Living scenes (docs/LIVING_SCENES.md): fx.candle.0 (the stub's wick), fx.fire.0 (the grate; radius 0.14 as the
  custom property `radius`), sound.rain.0 (on the window), sound.fire.0 (the grate)
  far.night (the wet roofs of the town in rain, seen through the window: emissive backdrop)
  Glass: M_Glass (the glassware), M_PaneGlass (the casement's panes; deliberately not "WindowGlass", which FableBuild
  draws as bright unlit daylight), M_Liquid (the tinctures): swapped by name for FableBuild's URP glass / liquid.

Axes: metres, Blender +Z up, +X east (the window), +Y north (the workbench side). The room's centre at the origin.

Run headless:
  blender -b -P blender/build_ingolstadt_garret.py -- --out out/ingolstadt-garret --render --quick --res 800
  blender -b -P blender/build_ingolstadt_garret.py -- --out out/ingolstadt-garret --bake --export --tex 2048
  blender -b -P blender/build_ingolstadt_garret.py -- --out captures/blender/ingolstadt-garret --prefix blender-render_ --render --res 1400 --samples 128
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wotw_kit as K
import frankenstein_kit as F
from frankenstein_kit import (new_mat, node, math_, mix_rgb, mix_f, maprange, bump_from, c4, obj_xyz, noise_tex, white,
                              combine, tone_ramp, wood, planks, paint, metal, fabric, glass, plain, box, cyl, sphere, torus,
                              lathe, tube, mesh_from, extrude_xz, Frame, anchor, camera, TWO_PI, paint_stroke, paint_dot,
                              fbm, sstep)

args, scene = K.begin("IngolstadtGarret", "out/ingolstadt-garret", seed=1818)
OUT = K.OUT
rnd = random.Random(1818)

# ----------------------------------------------------------------------------- dimensions (metres)
X0, X1 = -3.0, 3.0          # gable inner faces (west: chimney, east: window)
HW = 2.5                    # half width to the knee walls' inner faces
KH = 1.15                   # knee wall height
RH = 3.35                   # ridge (inner roof plane at y = 0)
SL = (RH - KH) / HW         # roof slope (rise per metre)
EYE = 1.55
READER = Vector((-1.0, -0.15, 0.0))
WIN_Y, WIN_W, WIN_Z0, WIN_H = 0.0, 0.58, 0.95, 1.30
RAF_D = 0.14                # rafter depth below the roof boards
def roof_z(y): return RH - SL * abs(y)
NRM_N = Vector((0, SL, 1)).normalized()          # outward normal of the north slope
NRM_S = Vector((0, -SL, 1)).normalized()

def recalc(o):
    """Outward normals for a closed solid built from raw faces."""
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()
    return o

def set_rnd(o, value):
    me = o.data
    a = me.attributes.get("rnd") or me.attributes.new("rnd", 'FLOAT', 'POINT')
    a.data.foreach_set("value", [value] * len(me.vertices))
    return o

# ----------------------------------------------------------------------------- materials
M_FLOOR = planks("M_Floorboards", 0.26, 3.2, [(0.20, 0.13, 0.075), (0.24, 0.16, 0.09), (0.17, 0.11, 0.065), (0.22, 0.145, 0.085)],
                 (0.03, 0.02, 0.012), along='X', rough=0.72, seed=3.0, grain_k=0.6, bumpk=0.3,
                 wear=lambda nt, X, Y, Z: maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', Y, -0.1)), 0.2, 1.1, 0.6, 0.0))
M_ROOFB = planks("M_RoofBoards", 0.22, 2.6, [(0.12, 0.085, 0.055), (0.15, 0.10, 0.065), (0.10, 0.07, 0.045)], (0.015, 0.01, 0.008),
                 along='X', rough=0.85, seed=7.0, grain_k=0.5, bumpk=0.2)

def plaster(name, base, stain=True):
    """Lime plaster on lath: a soft trowelled mottle, hairline cracks, grime low down and smoke-darkening high up,
    brown damp stains (where the rain gets in under the window and the eaves)."""
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    n = noise_tex(nt, xyz, 2.5, 6.0, 0.62)
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 0.35), c4(base), (0.72, 0.68, 0.62, 1))
    vor = node(nt, "ShaderNodeTexVoronoi", feature='DISTANCE_TO_EDGE'); vor.inputs["Scale"].default_value = 3.2
    dn = noise_tex(nt, xyz, 4.0, 3.0, 0.5)
    dv = node(nt, "ShaderNodeVectorMath", operation='ADD'); nt.links.new(xyz, dv.inputs[0]); nt.links.new(dn.outputs["Color"], dv.inputs[1])
    nt.links.new(dv.outputs[0], vor.inputs["Vector"])
    crack = math_(nt, 'MULTIPLY', maprange(nt, vor.outputs["Distance"], 0.0, 0.012, 1.0, 0.0), maprange(nt, noise_tex(nt, xyz, 1.3, 2.0, 0.5).outputs["Fac"], 0.5, 0.62, 0.0, 1.0))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', crack, 0.3), col, (0.16, 0.13, 0.10, 1))
    col = mix_rgb(nt, 'MIX', maprange(nt, Z, 0.35, 0.0, 0.0, 0.45), col, (0.20, 0.16, 0.11, 1))      # scuffed skirting zone
    col = mix_rgb(nt, 'MIX', maprange(nt, Z, 1.8, 3.4, 0.0, 0.5), col, (0.16, 0.13, 0.10, 1))        # smoke up under the roof
    if stain:
        sn = noise_tex(nt, xyz, 0.9, 4.0, 0.65)
        st = maprange(nt, sn.outputs["Fac"], 0.56, 0.66, 0.0, 1.0)
        edge = math_(nt, 'SUBTRACT', st, maprange(nt, sn.outputs["Fac"], 0.60, 0.70, 0.0, 1.0))
        col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', st, 0.35), col, (0.34, 0.25, 0.14, 1))
        col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', edge, 0.5), col, (0.20, 0.13, 0.07, 1))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.82, 0.95), b.inputs["Roughness"])
    f = noise_tex(nt, xyz, 30.0, 4.0, 0.6)
    bump_from(nt, b, math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', f.outputs["Fac"], 0.6), math_(nt, 'MULTIPLY', crack, 0.5)), 0.25, 0.004)
    return m

M_PLASTER = plaster("M_Plaster", (0.50, 0.45, 0.36))
M_BEAM_X = wood("M_BeamsX", (0.16, 0.11, 0.07), (0.06, 0.04, 0.028), rough=0.8, along='X', scale=1.5, seed=1.0, ring=3.0, bumpk=0.25, contrast=0.6)
M_BEAM_Y = wood("M_Rafters", (0.15, 0.10, 0.065), (0.055, 0.037, 0.026), rough=0.8, along='Y', scale=1.5, seed=2.0, ring=3.0, bumpk=0.25, contrast=0.6)
M_OAK = wood("M_Oak", (0.22, 0.14, 0.08), (0.10, 0.06, 0.035), rough=0.55, along='X', scale=3.0, seed=4.0, ring=5.0, bumpk=0.06, contrast=0.45)
M_DEAL = wood("M_Deal", (0.32, 0.23, 0.14), (0.17, 0.11, 0.065), rough=0.7, along='X', scale=2.5, seed=6.0, ring=4.0, bumpk=0.08, contrast=0.5)
M_DOOR = planks("M_DoorBoards", 0.18, 4.0, [(0.13, 0.09, 0.06), (0.16, 0.11, 0.07), (0.11, 0.075, 0.05)], (0.02, 0.014, 0.01),
                along='Z', rough=0.75, seed=9.0)
M_STONE = paint("M_Stone", (0.24, 0.22, 0.19), rough=0.85, mottle=0.25, scale=6.0, bumpk=0.3,
                grime=(0.0, 0.9, (0.07, 0.06, 0.05)))
M_SOOT = paint("M_Sooty", (0.035, 0.03, 0.028), rough=0.95, mottle=0.3, scale=5.0, bumpk=0.4)
M_IRON = metal("M_Iron", (0.06, 0.055, 0.05), rough=0.6, tarnish=(0.10, 0.06, 0.04), scale=5.0)
M_BRASS = metal("M_Brass", (0.62, 0.45, 0.20), rough=0.35, tarnish=(0.22, 0.17, 0.08), scale=9.0)
M_PEWTER = metal("M_Pewter", (0.42, 0.42, 0.40), rough=0.45, tarnish=(0.18, 0.18, 0.17), scale=10.0)
M_COPPER = metal("M_Copper", (0.55, 0.28, 0.16), rough=0.4, tarnish=(0.16, 0.20, 0.14), scale=8.0)
M_ZINC = metal("M_Zinc", (0.40, 0.41, 0.42), rough=0.55, tarnish=(0.25, 0.25, 0.24), scale=14.0)
M_GLASS = glass("M_Glass", (0.86, 0.92, 0.86), rough=0.03)
M_PANE = glass("M_PaneGlass", (0.80, 0.86, 0.84), rough=0.08)
M_LIQ = glass("M_Liquid", (0.55, 0.22, 0.08), rough=0.02, ior=1.34)
M_LIQ.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.62, 0.30, 0.10, 1)
M_SHEET = fabric("M_Sheet", (0.42, 0.40, 0.36), rough=0.9, scale=220.0, sheen=0.4, var=0.12)
M_BLANKET = fabric("M_Blanket", (0.16, 0.12, 0.09), rough=0.95, scale=90.0, sheen=0.6, var=0.25)
M_TICKING = fabric("M_Ticking", (0.40, 0.37, 0.32), rough=0.9, scale=140.0, sheen=0.3)
M_WAX = plain("M_Wax", (0.62, 0.56, 0.44), rough=0.45)
M_WAX.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.4
M_CERAMIC = paint("M_Stoneware", (0.33, 0.27, 0.20), rough=0.55, mottle=0.2, scale=8.0, bumpk=0.05)
M_CORK = paint("M_Cork", (0.30, 0.20, 0.11), rough=0.9, mottle=0.3, scale=40.0, bumpk=0.2)
M_LEATHER = paint("M_Leather", (0.14, 0.07, 0.04), rough=0.6, mottle=0.3, scale=12.0, bumpk=0.1)
M_ASH = paint("M_Ash", (0.22, 0.21, 0.20), rough=1.0, mottle=0.4, scale=20.0, bumpk=0.3)

def embers_mat():
    """Coals going out: black lumps with a few cracks and undersides still glowing deep orange."""
    m, nt, b = new_mat("M_Embers")
    xyz, X, Y, Z = obj_xyz(nt)
    vor = node(nt, "ShaderNodeTexVoronoi", feature='DISTANCE_TO_EDGE'); vor.inputs["Scale"].default_value = 28.0
    nt.links.new(xyz, vor.inputs["Vector"])
    n = noise_tex(nt, xyz, 9.0, 4.0, 0.6)
    glow = math_(nt, 'MULTIPLY', maprange(nt, vor.outputs["Distance"], 0.0, 0.06, 1.0, 0.0), maprange(nt, n.outputs["Fac"], 0.45, 0.65, 0.0, 1.0))
    glow = math_(nt, 'MULTIPLY', glow, maprange(nt, Z, 0.30, 0.16, 0.25, 1.0))
    col = mix_rgb(nt, 'MIX', glow, (0.018, 0.016, 0.015, 1), (0.85, 0.20, 0.03, 1))
    nt.links.new(col, b.inputs["Base Color"]); nt.links.new(col, b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 1.2
    nt.links.new(mix_f(nt, glow, 0.9, 0.6), b.inputs["Roughness"])
    bump_from(nt, b, n.outputs["Fac"], 0.5, 0.01)
    return m
M_EMBERS = embers_mat()

def books_mat():
    """Calf, vellum and cloth bindings: each book's own tone from its 'rnd' attribute, darker toward the edges with
    handling, gilt bands near the head and tail of some spines."""
    m, nt, b = new_mat("M_Books")
    xyz, X, Y, Z = obj_xyz(nt)
    at = node(nt, "ShaderNodeAttribute"); at.attribute_type = 'GEOMETRY'; at.attribute_name = "rnd"
    col = tone_ramp(nt, at.outputs["Fac"], [(0.16, 0.07, 0.04), (0.30, 0.17, 0.08), (0.10, 0.08, 0.06), (0.45, 0.38, 0.26),
                                            (0.08, 0.10, 0.07), (0.22, 0.10, 0.05), (0.36, 0.26, 0.15)])
    n = noise_tex(nt, xyz, 18.0, 5.0, 0.6)
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 0.4), col, (0.6, 0.55, 0.5, 1))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.45, 0.75), b.inputs["Roughness"])
    bump_from(nt, b, n.outputs["Fac"], 0.15, 0.002)
    return m
M_BOOKS = books_mat()

# ----------------------------------------------------------------------------- numpy pictures: drawings and the night view
def ink_line(img, pts, w, col=(0.05, 0.035, 0.025), alpha=0.9):
    for a, b_ in zip(pts, pts[1:]): paint_stroke(img, a, b_, w, w, col, alpha)

def text_lines(img, rs, x0, x1, y0, y1, gap=13, w=1.4, col=(0.06, 0.04, 0.03)):
    y = y1
    while y > y0:
        x = x0 + rs.uniform(0, 12)
        end = x1 - rs.uniform(0, 40) if rs.random() < 0.85 else x0 + (x1 - x0) * rs.uniform(0.3, 0.6)
        while x < end:
            L = rs.uniform(8, 30)
            pts = [(x + t * L / 6, y + rs.uniform(-1.6, 1.6)) for t in range(7)]
            ink_line(img, pts, w, col, rs.uniform(0.55, 0.85))
            x += L + rs.uniform(5, 9)
        y -= gap

def drawings_atlas(N=1024, seed=4):
    """Four sheets (2 x 2) of rough foolscap: the bones of the arm and hand, a skull in profile, a page of close
    notes with a small sketch of a retort, the ribs and spine. Sepia ink, hatching, a few blots, foxing."""
    rs = random.Random(seed); S = N // 2
    u = (np.arange(N) + 0.5) / N; U, V = np.meshgrid(u, u)
    tone = 0.85 + 0.15 * fbm(U * 6, V * 6, 4, seed=3)
    img = np.ones((N, N, 4), np.float32)
    img[..., 0] = 0.56 * tone; img[..., 1] = 0.49 * tone; img[..., 2] = 0.35 * tone
    fox = sstep(0.68, 0.78, fbm(U * 22, V * 22, 3, seed=9))
    img[..., :3] *= (1 - 0.25 * fox[..., None] * np.array([0.6, 0.8, 1.0]))
    def P(vi, x, y):  # sheet-local 0..1 -> pixels
        return ((vi % 2) * S + x * S, (vi // 2) * S + y * S)
    # 0: arm and hand
    vi = 0
    for (xa, ya, xb, yb, wa) in ((0.18, 0.86, 0.30, 0.52, 0.035), (0.30, 0.50, 0.40, 0.26, 0.022), (0.33, 0.50, 0.45, 0.27, 0.02)):
        for side in (-1, 1):
            ink_line(img, [P(vi, xa + side * wa, ya), P(vi, (xa + xb) / 2 + side * wa * 0.6, (ya + yb) / 2), P(vi, xb + side * wa * 0.9, yb)], 1.8)
        paint_dot(img, P(vi, xa, ya), S * wa * 1.25, (0.05, 0.035, 0.025), 0.15)
        ink_line(img, [P(vi, xa - wa * 1.2, ya + 0.01), P(vi, xa, ya + wa * 1.6), P(vi, xa + wa * 1.2, ya + 0.01)], 1.8)
    for k in range(5):        # metacarpals and phalanges fanned out
        a = math.radians(-60 + k * 18); bx, by = 0.44 + k * 0.022, 0.24
        for seg_len in (0.07, 0.045, 0.032, 0.025):
            ex, ey = bx + math.sin(a) * seg_len, by - math.cos(a) * seg_len
            ink_line(img, [P(vi, bx, by), P(vi, ex, ey)], 2.2); paint_dot(img, P(vi, ex, ey), 2.6, (0.05, 0.035, 0.025), 0.8)
            bx, by = ex, ey; a += math.radians(rs.uniform(-6, 6))
    for k in range(40):       # hatching along the humerus
        y = 0.55 + k * 0.007; ink_line(img, [P(vi, 0.21, y), P(vi, 0.24, y - 0.02)], 0.9, alpha=0.5)
    text_lines(img, rs, P(vi, 0.58, 0)[0], P(vi, 0.94, 0)[0], P(vi, 0, 0.12)[1], P(vi, 0, 0.90)[1], gap=12)
    # 1: skull in profile
    vi = 1
    pts = [P(vi, 0.5 + 0.24 * math.cos(t) * (1.0 if math.cos(t) < 0 else 0.9), 0.62 + 0.2 * math.sin(t)) for t in np.linspace(0.05, math.pi + 0.5, 30)]
    ink_line(img, pts, 2.2)
    ink_line(img, [pts[0], P(vi, 0.76, 0.52), P(vi, 0.74, 0.47), P(vi, 0.77, 0.42), P(vi, 0.72, 0.38), P(vi, 0.70, 0.30), P(vi, 0.58, 0.29), P(vi, 0.50, 0.36), P(vi, 0.42, 0.42), pts[-1]], 2.2)
    for t in np.linspace(0, TWO_PI, 18)[:-1]:
        paint_stroke(img, P(vi, 0.63 + 0.05 * math.cos(t), 0.55 + 0.045 * math.sin(t)), P(vi, 0.63 + 0.05 * math.cos(t + 0.37), 0.55 + 0.045 * math.sin(t + 0.37)), 2.0, 2.0, (0.05, 0.035, 0.025))
    for k in range(9): ink_line(img, [P(vi, 0.60 + k * 0.012, 0.37), P(vi, 0.60 + k * 0.012, 0.33)], 1.2)
    for k in range(30): ink_line(img, [P(vi, 0.32 + k * 0.006, 0.64), P(vi, 0.34 + k * 0.006, 0.70)], 0.8, alpha=0.4)
    text_lines(img, rs, P(vi, 0.08, 0)[0], P(vi, 0.92, 0)[0], P(vi, 0, 0.05)[1], P(vi, 0, 0.22)[1], gap=12)
    # 2: notes with a retort
    vi = 2
    text_lines(img, rs, P(vi, 0.07, 0)[0], P(vi, 0.93, 0)[0], P(vi, 0, 0.05)[1], P(vi, 0, 0.94)[1], gap=11)
    img[int(P(vi, 0, 0.55)[1]):int(P(vi, 0, 0.82)[1]), int(P(vi, 0.55, 0)[0]):int(P(vi, 0.93, 0)[0]), :3] = (0.56 * 0.92, 0.49 * 0.92, 0.35 * 0.92)
    ink_line(img, [P(vi, 0.62 + 0.06 * math.cos(t), 0.64 + 0.06 * math.sin(t)) for t in np.linspace(0, TWO_PI, 24)], 1.8)
    ink_line(img, [P(vi, 0.66, 0.69), P(vi, 0.76, 0.76), P(vi, 0.86, 0.74), P(vi, 0.90, 0.66)], 1.6)
    paint_dot(img, P(vi, 0.3, 0.3), 9, (0.05, 0.035, 0.025), 0.7)
    # 3: ribs and spine
    vi = 3
    for k in range(16):
        y = 0.85 - k * 0.042
        ink_line(img, [P(vi, 0.47, y), P(vi, 0.53, y)], 2.4)
    for k in range(9):
        y = 0.80 - k * 0.055; w = 0.18 + 0.06 * math.sin(k / 9 * math.pi)
        for side in (-1, 1):
            ink_line(img, [P(vi, 0.5 + side * 0.03, y), P(vi, 0.5 + side * w * 0.8, y + 0.015), P(vi, 0.5 + side * w, y - 0.04), P(vi, 0.5 + side * w * 0.7, y - 0.09)], 1.7)
    text_lines(img, rs, P(vi, 0.06, 0)[0], P(vi, 0.94, 0)[0], P(vi, 0, 0.04)[1], P(vi, 0, 0.16)[1], gap=12)
    img[..., 3] = 1.0
    return img

def sheet_uv(vi, inset=0.01):
    u0, v0 = (vi % 2) * 0.5, (vi // 2) * 0.5
    return (u0 + inset, v0 + inset, u0 + 0.5 - inset, v0 + 0.5 - inset)

NV_D, NV_W, NV_H, NV_Z0 = 3.0, 9.5, 8.0, -2.5     # the night card: 3 m beyond the gable, 9.5 x 8 m, its foot at z = -2.5
def night_view(W=2048, Hh=1728, seed=21):
    """The town from the garret window at one in the morning in November rain: a low, heavy sky faintly lit from
    below, wet steep roofs and chimneys falling away below the sill, the two square towers of the Frauenkirche a
    little left of centre, a couple of late windows, all softened by rain on the glass. Laid out for the card's
    geometry: eye level (z 1.55) at v 0.51; from the reading place the casement shows u 0.43-0.54, v 0.38-0.66."""
    rs = random.Random(seed)
    u = (np.arange(W) + 0.5) / W; v = (np.arange(Hh) + 0.5) / Hh
    U, V = np.meshgrid(u, v)
    up = np.clip((V - 0.45) / 0.55, 0, 1)
    col = np.array([0.030, 0.032, 0.040]) * (1 - up[..., None]) + np.array([0.012, 0.015, 0.022]) * up[..., None]
    col = col + np.exp(-((V - 0.47) / 0.07) ** 2)[..., None] * np.array([0.030, 0.022, 0.016])       # the town's glow on the cloud base
    cl = fbm(U * 7, V * 14, 5, seed=4)
    col = col * (0.75 + 0.5 * cl[..., None])
    def roofline(base, amp, period, seed_):
        xs = np.arange(W); prof = np.full(W, base, np.float32); x = -rs.randint(0, period)
        r2 = random.Random(seed_)
        while x < W:
            w = int(period * r2.uniform(0.55, 1.45)); peak = base + amp * r2.uniform(0.45, 1.2)
            mid = x + w / 2; seg = np.clip(1 - np.abs(xs - mid) / (w / 2), 0, 1)
            if r2.random() < 0.3: seg = np.minimum(seg * 1.6, 1.0) * (np.abs(xs - mid) < w * 0.45)     # a hipped or flat-topped roof
            prof = np.maximum(prof, base + (peak - base) * seg)
            for _ in range(r2.choice((0, 1, 1, 2))):       # chimneys
                cx = int(x + w * r2.uniform(0.2, 0.8)); cw = max(4, int(period * 0.05))
                lo_, hi_ = max(cx, 0), min(cx + cw, W)
                if hi_ > lo_: prof[lo_:hi_] = np.maximum(prof[lo_:hi_], base + (peak - base) * 0.7 + amp * 0.3)
            x += w
        return prof / Hh
    layers = [(0.445, 0.035, 140, 5, (0.010, 0.011, 0.014), 0.5), (0.40, 0.06, 260, 6, (0.008, 0.009, 0.011), 0.8),
              (0.29, 0.09, 520, 7, (0.006, 0.0065, 0.008), 1.0)]
    for li, (base, amp, period, sd, c, sheen) in enumerate(layers):
        prof = roofline(base * Hh, amp * Hh, period, sd)
        if li == 0:     # the Frauenkirche's two towers, with their steep gabled caps
            for tx, tw, th in ((0.452, 0.020, 0.585), (0.478, 0.020, 0.578)):
                xs = U[0]; inside = (xs > tx) & (xs < tx + tw)
                cap = th + 0.022 * (1 - np.abs(xs - (tx + tw / 2)) / (tw / 2))
                prof = np.where(inside, np.maximum(prof, cap), prof)
        mask = V < prof[None, :]
        wet = (0.55 + 0.45 * fbm(U * 90, V * 30, 3, seed=sd)) * sheen
        shade = np.array(c)[None, None, :] * wet[..., None] * (0.7 + 0.6 * np.clip((V - (prof[None, :] - 0.06)) / 0.06, 0, 1))[..., None]
        hl = sstep(0.004, 0.0, prof[None, :] - V) * 0.010
        col = np.where(mask[..., None], shade + hl[..., None] * np.array([0.8, 0.85, 1.0]), col)
        # a few late windows, warm and small, blurred by the rain
        for k in range((0, 3, 3)[li]):
            wx = rs.uniform(0.44, 0.54) if k == 0 else rs.uniform(0.2, 0.8); wy = base + rs.uniform(-0.04, 0.0) * (li + 1)
            if not (V.min() < wy < prof[int(wx * W)]): continue
            d = ((U - wx) / 0.0009) ** 2 + ((V - wy) / 0.0014) ** 2
            col += np.exp(-d)[..., None] * np.array([0.30, 0.15, 0.05]) * 0.5
            col += np.exp(-d / 12)[..., None] * np.array([0.015, 0.008, 0.003])
    img = np.zeros((Hh, W, 4), np.float32); img[..., :3] = col
    # rain on the glass: runnels and beads, catching a little of the room's light
    for k in range(2200):
        x = rs.uniform(0, W); y = rs.uniform(0, Hh); L = rs.uniform(18, 80)
        pts = [(x, y)]
        for s_ in range(5): pts.append((pts[-1][0] + rs.gauss(0, 1.4), pts[-1][1] - L / 5))
        for a, b_ in zip(pts, pts[1:]): paint_stroke(img, a, b_, 1.6, 1.2, (0.075, 0.075, 0.085), 0.30)
        paint_dot(img, pts[-1], 2.2, (0.10, 0.095, 0.10), 0.45)
    for k in range(9000):
        paint_dot(img, (rs.uniform(0, W), rs.uniform(0, Hh)), rs.uniform(0.7, 1.8), (0.085, 0.085, 0.095), 0.35)
    img[..., 3] = 1.0
    return img

print("painting drawings and night view ...")
M_PAPER = K.card_material("M_Drawings", K.image_from("T_Drawings", drawings_atlas()), rough=0.85, clip=False)
M_NIGHT = K.card_material("M_NightView", K.image_from("T_NightView", night_view()), rough=1.0, clip=False, emissive=True)

def paper(name, corners, vi, mat=None):
    u0, v0, u1, v1 = sheet_uv(vi)
    o = mesh_from(name, corners, [(0, 1, 2, 3)], mat or M_PAPER, uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    K.KEEP_UV.add((mat or M_PAPER).name)
    return o

# ----------------------------------------------------------------------------- the shell
box("Floor", (X1 - X0 + 0.9, 2 * HW + 0.6, 0.12), (0, 0, -0.06), M_FLOOR)
for side in (1, -1):        # knee walls, running up into the roof
    box(f"KneeWall{side}", (X1 - X0 + 0.9, 0.25, KH + 0.35), (0, side * (HW + 0.125), (KH + 0.35) / 2), M_PLASTER)

def roof_slab(side):
    """The boards under the slates: a thick slab whose underside is the roof plane (y from the ridge to past the
    knee wall), long enough to run into both gables."""
    ys = (0.0, side * (HW + 0.45)); xa, xb = X0 - 0.5, X1 + 0.5
    nrm = NRM_N if side > 0 else NRM_S
    lo = [Vector((x, y, roof_z(y))) for y in ys for x in (xa, xb)]
    hi = [p + nrm * 0.18 for p in lo]
    verts = lo + hi
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    o = mesh_from(f"Roof{side}", verts, faces, M_ROOFB)
    return recalc(o)
roof_slab(1); roof_slab(-1)

def gable(name, xa, xb, cut=None):
    pts = [(-HW - 0.3, -0.1), (HW + 0.3, -0.1), (HW + 0.3, roof_z(HW + 0.3) + 0.25), (0.0, RH + 0.3)]
    pts.insert(3, (-(HW + 0.3), roof_z(HW + 0.3) + 0.25)); pts = [pts[0], pts[1], pts[2], pts[4], pts[3]]
    fr = Frame((0, 0), math.radians(90))
    o = extrude_xz(name, pts, -xb, -xa, M_PLASTER, frame=fr)
    if cut is not None:
        md = o.modifiers.new("Cut", 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cut; md.solver = 'EXACT'
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier=md.name)
        bpy.data.objects.remove(cut)
    return o

def cutter(size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc); c = bpy.context.active_object; c.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return c

# east gable with the narrow casement, a deep splayed reveal
gable("GableEast", X1, X1 + 0.42, cut=cutter((1.2, WIN_W, WIN_H), (X1 + 0.2, WIN_Y, WIN_Z0 + WIN_H / 2)))
# west gable with the low door beside the chimney breast
DOOR_Y0, DOOR_Y1, DOOR_H = 1.05, 1.80, 1.66
gable("GableWest", X0 - 0.42, X0, cut=cutter((1.2, DOOR_Y1 - DOOR_Y0, DOOR_H), (X0 - 0.2, (DOOR_Y0 + DOOR_Y1) / 2, DOOR_H / 2)))

# --- the casement: frame, two leaves of small panes behind glazing bars, the sill
WX = X1 + 0.20        # the window plane, set back in the wall
box("WinSill", (0.48, WIN_W + 0.1, 0.05), (X1 + 0.10, WIN_Y, WIN_Z0 - 0.02), M_OAK, bevel=0.01)
for s in (-1, 1):
    box(f"WinJamb{s}", (0.07, 0.06, WIN_H), (WX, WIN_Y + s * (WIN_W / 2 - 0.03), WIN_Z0 + WIN_H / 2), M_OAK)
box("WinHead", (0.07, WIN_W, 0.07), (WX, WIN_Y, WIN_Z0 + WIN_H - 0.035), M_OAK)
box("WinBottom", (0.07, WIN_W, 0.07), (WX, WIN_Y, WIN_Z0 + 0.035), M_OAK)
box("WinMullion", (0.06, 0.045, WIN_H), (WX, WIN_Y, WIN_Z0 + WIN_H / 2), M_OAK)
box("WinTransom", (0.06, WIN_W, 0.05), (WX, WIN_Y, WIN_Z0 + WIN_H * 0.68), M_OAK)
for s in (-1, 1):
    yc = WIN_Y + s * WIN_W / 4
    for k in range(1, 4):
        z = WIN_Z0 + 0.07 + (WIN_H * 0.68 - 0.1) * k / 4
        box(f"WinBarH{s}{k}", (0.025, WIN_W / 2 - 0.05, 0.018), (WX - 0.005, yc, z), M_IRON)
    box(f"WinBarV{s}", (0.025, 0.018, WIN_H - 0.1), (WX - 0.005, yc, WIN_Z0 + WIN_H / 2), M_IRON)
box("WinPanes", (0.008, WIN_W - 0.08, WIN_H - 0.1), (WX + 0.005, WIN_Y, WIN_Z0 + WIN_H / 2), M_PANE)
box("WinLatch", (0.03, 0.02, 0.10), (WX - 0.04, WIN_Y + 0.03, WIN_Z0 + 0.6), M_IRON)
# the night beyond: the town's wet roofs, on a card 3 m out (wide enough for every angle through the reveal)
def night_card():
    xc = X1 + NV_D; Wd, Hd = NV_W, NV_H; zc = NV_Z0 + NV_H / 2
    corners = [(xc, WIN_Y + Wd / 2, zc - Hd / 2), (xc, WIN_Y - Wd / 2, zc - Hd / 2), (xc, WIN_Y - Wd / 2, zc + Hd / 2), (xc, WIN_Y + Wd / 2, zc + Hd / 2)]
    o = mesh_from("NightView", corners, [(0, 1, 2, 3)], M_NIGHT, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    K.KEEP_UV.add(M_NIGHT.name)
    o.visible_shadow = False
    return o
night_card()

# --- the door: ledged boards, strap hinges, a latch
box("Door", (0.05, DOOR_Y1 - DOOR_Y0 - 0.02, DOOR_H - 0.02), (X0 - 0.30, (DOOR_Y0 + DOOR_Y1) / 2, DOOR_H / 2), M_DOOR)
for z in (0.3, 1.3):
    box(f"DoorLedge{z}", (0.035, DOOR_Y1 - DOOR_Y0 - 0.1, 0.12), (X0 - 0.265, (DOOR_Y0 + DOOR_Y1) / 2, z), M_DOOR)
    box(f"DoorHinge{z}", (0.012, 0.45, 0.035), (X0 - 0.24, DOOR_Y1 - 0.25, z + 0.07), M_IRON)
box("DoorLatch", (0.02, 0.16, 0.025), (X0 - 0.24, DOOR_Y0 + 0.12, 0.98), M_IRON)
for s in (0, 1):
    box(f"DoorCasing{s}", (0.04, 0.08, DOOR_H + 0.06), (X0 + 0.01, (DOOR_Y0 - 0.03, DOOR_Y1 + 0.03)[s], DOOR_H / 2), M_BEAM_X)
box("DoorLintel", (0.05, DOOR_Y1 - DOOR_Y0 + 0.16, 0.09), (X0 + 0.01, (DOOR_Y0 + DOOR_Y1) / 2, DOOR_H + 0.04), M_BEAM_X)

# --- timbers: rafters, ridge, purlins, wall plates, collar ties
def slope_point(side, y_abs, depth):
    nrm = NRM_N if side > 0 else NRM_S
    return Vector((0, side * y_abs, roof_z(y_abs))) - nrm * depth

ang = math.atan(SL)
RAFTERS = [X0 + 0.25 + i * (X1 - X0 - 0.5) / 9 for i in range(10)]
for side in (1, -1):
    for i, x in enumerate(RAFTERS):
        a = slope_point(side, 0.08, RAF_D / 2); b_ = slope_point(side, HW + 0.05, RAF_D / 2)
        mid = (a + b_) / 2; L = (b_ - a).length
        o = box(f"Rafter{side}_{i}", (0.10 + rnd.uniform(-0.01, 0.015), L, RAF_D), (x, mid.y, mid.z), M_BEAM_Y, bevel=0.012, rot=(-side * ang, 0, 0))
    for k, (yy, w, d) in enumerate(((1.25, 0.16, 0.19),)):
        p = slope_point(side, yy, RAF_D + d / 2)
        box(f"Purlin{side}_{k}", (X1 - X0 + 0.4, w, d), (0, p.y, p.z), M_BEAM_X, bevel=0.015, rot=(-side * ang, 0, 0))
    box(f"WallPlate{side}", (X1 - X0 + 0.4, 0.2, 0.14), (0, side * (HW - 0.06), KH + 0.05), M_BEAM_X, bevel=0.012)
box("Ridge", (X1 - X0 + 0.4, 0.2, 0.24), (0, 0, RH - 0.08), M_BEAM_X, bevel=0.015)
CZ = 2.42
cy_ = (RH - RAF_D * math.sqrt(1 + SL * SL) - CZ) / SL
for i, x in enumerate(RAFTERS[1::3]):
    box(f"Collar{i}", (0.11, 2 * cy_ + 0.25, 0.17), (x, 0, CZ - 0.06), M_BEAM_Y, bevel=0.012)
    # pegs where the collar meets the rafters
    for s in (-1, 1):
        cyl(f"Peg{i}{s}", 0.018, 0.13, (x, s * (cy_ - 0.05), CZ - 0.06), M_OAK, verts=6, rot=(0, math.pi / 2, 0))

# --- the chimney breast and the dying fire
BX0, BX1, BY = X0, X0 + 0.52, 0.80
FO_W, FO_H, FO_D = 0.78, 0.74, 0.42
def breast():
    o = box("Breast", (BX1 - BX0 + 0.25, 2 * BY, RH + 0.6), (BX0 + (BX1 - BX0 - 0.25) / 2, 0, (RH + 0.6) / 2), M_PLASTER)
    c = cutter((FO_D * 2, FO_W, FO_H * 2), (BX1, 0, 0))
    md = o.modifiers.new("Cut", 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = c; md.solver = 'EXACT'
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier=md.name); bpy.data.objects.remove(c)
breast()
FB = BX1 - FO_D           # back of the firebox
box("FireBack", (0.05, FO_W, FO_H), (FB + 0.025, 0, FO_H / 2), M_SOOT)
for s in (-1, 1):
    box(f"FireCheek{s}", (FO_D, 0.04, FO_H), (FB + FO_D / 2, s * (FO_W / 2 - 0.02), FO_H / 2), M_SOOT)
box("FireCrown", (FO_D, FO_W, 0.04), (FB + FO_D / 2, 0, FO_H - 0.02), M_SOOT)
# stone surround and the hearth slab
for s in (-1, 1):
    box(f"Jamb{s}", (0.08, 0.16, FO_H + 0.12), (BX1 + 0.03, s * (FO_W / 2 + 0.08), (FO_H + 0.12) / 2), M_STONE, bevel=0.008)
box("Lintel", (0.09, FO_W + 0.48, 0.16), (BX1 + 0.035, 0, FO_H + 0.08), M_STONE, bevel=0.008)
box("Mantel", (0.22, FO_W + 0.62, 0.05), (BX1 + 0.06, 0, FO_H + 0.42), M_OAK, bevel=0.01)
box("MantelBracket0", (0.08, 0.05, 0.22), (BX1 + 0.03, -(FO_W / 2 + 0.2), FO_H + 0.29), M_OAK)
box("MantelBracket1", (0.08, 0.05, 0.22), (BX1 + 0.03, (FO_W / 2 + 0.2), FO_H + 0.29), M_OAK)
box("Hearth", (0.62, FO_W + 0.55, 0.05), (BX1 + 0.25, 0, 0.0), M_STONE, bevel=0.01)
box("HearthInner", (FO_D, FO_W, 0.03), (FB + FO_D / 2, 0, 0.0), M_SOOT)
# the grate: an iron basket on legs, the coals settling low, ash beneath
GX = FB + 0.20
for s in (-1, 1):
    box(f"GrateSide{s}", (0.22, 0.02, 0.22), (GX, s * 0.23, 0.17), M_IRON)
    cyl(f"GrateLeg{s}a", 0.015, 0.12, (GX + 0.1, s * 0.23, 0.06), M_IRON, verts=6)
    cyl(f"GrateLeg{s}b", 0.015, 0.12, (GX - 0.1, s * 0.23, 0.06), M_IRON, verts=6)
for k in range(6):
    z = 0.10 + k * 0.035
    cyl(f"GrateBar{k}", 0.009, 0.46, (GX + 0.11, 0, z), M_IRON, verts=6, rot=(math.pi / 2, 0, 0))
for k in range(5):
    cyl(f"GrateFloor{k}", 0.008, 0.46, (GX - 0.08 + k * 0.045, 0, 0.10), M_IRON, verts=6, rot=(math.pi / 2, 0, 0))
for k in range(22):
    p = Vector((GX + rnd.uniform(-0.09, 0.09), rnd.uniform(-0.19, 0.19), 0.13 + rnd.uniform(0, 0.05)))
    if k < 6: p.z += 0.04
    r = rnd.uniform(0.025, 0.05)
    o = sphere(f"Coal{k}", r, tuple(p), M_EMBERS, seg=8, scale=(1, rnd.uniform(0.7, 1.2), rnd.uniform(0.5, 0.8)), rot=(rnd.random(), rnd.random(), rnd.random()))
for k in range(2):         # two half-burnt log ends
    tube(f"LogEnd{k}", [(GX - 0.05, -0.18 + k * 0.2, 0.17 + 0.03 * k), (GX + 0.06, 0.04 + k * 0.17, 0.19 + 0.02 * k)], [0.035, 0.03], M_EMBERS, sides=7)
sphere("AshHeap", 0.24, (GX, 0, 0.0), M_ASH, seg=10, scale=(0.75, 1.1, 0.12))
# fire irons and a coal scuttle
tube("Poker", [(BX1 + 0.12, -(FO_W / 2 + 0.32), 0.02), (BX1 + 0.04, -(FO_W / 2 + 0.28), 0.75)], [0.008, 0.008], M_IRON, sides=6)
torus("PokerRing", 0.025, 0.006, (BX1 + 0.04, -(FO_W / 2 + 0.28), 0.78), M_IRON, rot=(0, math.pi / 2.2, 0), seg=10, rseg=4)
tube("Tongs", [(BX1 + 0.14, -(FO_W / 2 + 0.38), 0.02), (BX1 + 0.05, -(FO_W / 2 + 0.36), 0.70)], [0.007, 0.007], M_IRON, sides=6)
lathe("Scuttle", [(0.0, 0.0), (0.13, 0.0), (0.15, 0.05), (0.16, 0.24), (0.15, 0.26), (0.0, 0.26)], (BX1 + 0.35, FO_W / 2 + 0.45, 0.0), M_COPPER, steps=14)
FIRE = Vector((GX, 0, 0.18))

# mantel things: a stoneware jar, an unlit brass candlestick, a few books, a glass bell over a small bird skeleton is
# too much: a bundle of quills in a pot instead
MZ = FO_H + 0.445
lathe("MantelJar", [(0.0, 0.0), (0.05, 0.0), (0.065, 0.06), (0.06, 0.15), (0.035, 0.18), (0.04, 0.2), (0.0, 0.2)], (BX1 + 0.08, -0.38, MZ), M_CERAMIC, steps=14)
lathe("MantelStick", [(0.0, 0.0), (0.05, 0.0), (0.05, 0.01), (0.015, 0.03), (0.012, 0.16), (0.025, 0.17), (0.02, 0.18), (0.0, 0.18)], (BX1 + 0.08, 0.32, MZ), M_BRASS, steps=12)
cyl("MantelCandle", 0.011, 0.11, (BX1 + 0.08, 0.32, MZ + 0.235), M_WAX, verts=8)
for k in range(5):
    w = rnd.uniform(0.03, 0.05); h = rnd.uniform(0.18, 0.24)
    o = box(f"MantelBook{k}", (0.15, w, h), (BX1 + 0.09, -0.05 + k * 0.05, MZ + h / 2), M_BOOKS, bevel=0.004, rot=(rnd.uniform(-0.05, 0.05) if k < 4 else 0.35, 0, 0))
    set_rnd(o, rnd.random())

# ----------------------------------------------------------------------------- furniture
def table(name, cx, cy, L, W, H, mat, top_t=0.05, stretcher=True):
    box(name + "Top", (L, W, top_t), (cx, cy, H - top_t / 2), mat, bevel=0.006)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"{name}Leg{sx}{sy}", (0.07, 0.07, H - top_t), (cx + sx * (L / 2 - 0.09), cy + sy * (W / 2 - 0.08), (H - top_t) / 2), mat)
    for sy in (-1, 1):
        box(f"{name}Apron{sy}", (L - 0.2, 0.03, 0.10), (cx, cy + sy * (W / 2 - 0.08), H - top_t - 0.05), mat)
    if stretcher:
        box(name + "Stretcher", (L - 0.2, 0.05, 0.05), (cx, cy, 0.16), mat)
        for sx in (-1, 1):
            box(f"{name}Rail{sx}", (0.05, W - 0.16, 0.05), (cx + sx * (L / 2 - 0.09), cy, 0.16), mat)

# the long table on the right, and the form under its sheet
LT = Vector((1.05, -1.42, 0.0)); LT_L, LT_W, LT_H = 2.75, 0.92, 0.80
table("LongTable", LT.x, LT.y, LT_L, LT_W, LT_H, M_DEAL)

def covered_form():
    """A linen sheet over a long figure lying on its back on the table (head to the east). The sheet is a height
    field over the table, made of soft-maximum lumps (feet, shins, knees, hips, chest, the hands at the sides, the
    head), blurred so it spans the hollows, then falls over the table's edges in loose folds."""
    top = LT_H + 0.003
    ML = 0.30                                        # how far the sheet hangs over the edges
    NX, NY = 120, 54
    xs = np.linspace(-LT_L / 2 - ML, LT_L / 2 + ML, NX + 1); ys = np.linspace(-LT_W / 2 - ML, LT_W / 2 + ML, NY + 1)
    Xg, Yg = np.meshgrid(xs, ys)
    u = Xg + 1.22; v = Yg                              # u: metres from the soles toward the head
    def cap(u0, u1, v0, r, h):
        t = np.clip((u - u0) / (u1 - u0), 0, 1); d = np.hypot(u - (u0 + t * (u1 - u0)), v - v0)
        return h * np.clip(1 - (d / r) ** 2, 0, 1) ** 0.8
    def ell(uc, vc, ru, rv, h):
        d = ((u - uc) / ru) ** 2 + ((v - vc) / rv) ** 2
        return h * np.clip(1 - d, 0, 1) ** 0.8
    parts = [ell(0.07, -0.12, 0.09, 0.07, 0.15), ell(0.07, 0.12, 0.09, 0.07, 0.145),          # the feet, toes up
             cap(0.10, 0.62, -0.11, 0.07, 0.11), cap(0.10, 0.62, 0.11, 0.07, 0.11),            # shins
             ell(0.62, -0.11, 0.08, 0.075, 0.14), ell(0.62, 0.11, 0.08, 0.075, 0.14),          # knees
             cap(0.62, 1.10, -0.11, 0.10, 0.15), cap(0.62, 1.10, 0.11, 0.10, 0.15),            # thighs
             ell(1.18, 0.0, 0.18, 0.21, 0.19), ell(1.55, 0.0, 0.30, 0.25, 0.23),                # hips, chest
             cap(1.25, 1.80, -0.31, 0.06, 0.10), cap(1.25, 1.80, 0.31, 0.06, 0.10),            # the arms at the sides
             ell(1.18, -0.34, 0.07, 0.05, 0.08), ell(1.18, 0.34, 0.07, 0.05, 0.08),            # the hands
             ell(1.90, 0.0, 0.05, 0.08, 0.13), ell(2.08, 0.0, 0.13, 0.11, 0.21)]               # neck, head
    h = np.zeros_like(Xg)
    for p_ in parts: h = np.log(np.exp(h * 30) + np.exp(p_ * 30) - 1) / 30
    for _ in range(26):        # the cloth spans the hollows
        hb = h.copy()
        hb[1:-1, 1:-1] = (h[:-2, 1:-1] + h[2:, 1:-1] + h[1:-1, :-2] + h[1:-1, 2:] + 2 * h[1:-1, 1:-1]) / 6
        h = np.maximum(h, hb * 0.97)
    for _ in range(4):        # soften what is left of any edge
        hb = h.copy(); hb[1:-1, 1:-1] = (h[:-2, 1:-1] + h[2:, 1:-1] + h[1:-1, :-2] + h[1:-1, 2:] + 4 * h[1:-1, 1:-1]) / 8; h = hb
    din = np.minimum(LT_L / 2 - np.abs(Xg), LT_W / 2 - np.abs(Yg))
    h = h * sstep(0.0, 0.14, din)
    # creases: a long fold down the body, small wrinkles
    wr = 0.006 * np.sin(Yg * 38 + 3 * np.sin(Xg * 3)) * sstep(0.0, 0.04, h) + 0.004 * (fbm(Xg * 7, Yg * 7, 3, seed=5) - 0.5)
    h = h + wr
    # the hang: outside the table top the sheet falls vertically with folds
    ex = np.clip(np.abs(Xg) - LT_L / 2, 0, None); ey = np.clip(np.abs(Yg) - LT_W / 2, 0, None)
    out = np.hypot(ex, ey)
    px = np.clip(Xg, -LT_L / 2, LT_L / 2); py = np.clip(Yg, -LT_W / 2, LT_W / 2)
    nx_ = np.where(out > 1e-6, (Xg - px) / np.maximum(out, 1e-6), 0); ny_ = np.where(out > 1e-6, (Yg - py) / np.maximum(out, 1e-6), 0)
    edge_h = np.zeros_like(Xg)
    fold = 0.015 * np.sin(px * 17 + py * 13) + 0.010 * np.sin(px * 31 + 1.3) + 0.008 * np.sin(py * 29)
    reach = 0.045 + np.minimum(out, 0.06) * 0.6 + np.clip(out - 0.06, 0, None) * 0.05 + fold * sstep(0.02, 0.2, out)
    X_ = np.where(out > 0, px + nx_ * reach, Xg); Y_ = np.where(out > 0, py + ny_ * reach, Yg)
    Z_ = np.where(out > 0, top + 0.012 - (out - np.minimum(out, 0.012)) - 0.02 * sstep(0.0, 0.08, out) * 0, top + h * sstep(0.0, 0.05, -np.maximum(ex, ey) + 0.05) + 0.008)
    # the hem is uneven
    Z_ = Z_ - np.where(out > 0.2, (out - 0.2) * 0.3 * (fbm(px * 4, py * 4, 2, seed=8) - 0.3), 0)
    verts = [(float(X_[j, i] + LT.x), float(Y_[j, i] + LT.y), float(Z_[j, i])) for j in range(NY + 1) for i in range(NX + 1)]
    faces = [(j * (NX + 1) + i, j * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i) for j in range(NY) for i in range(NX)]
    o = mesh_from("Sheet", verts, faces, M_SHEET, smooth=True)
    K.orient(o, lambda c: (0, 0, 1) if c.z > LT_H - 0.01 else (c.x - LT.x, c.y - LT.y, 0))
    return o
covered_form()

# the workbench on the left
WB = Vector((0.75, 1.48, 0.0)); WB_L, WB_W, WB_H = 2.3, 0.82, 0.80
table("Bench", WB.x, WB.y, WB_L, WB_W, WB_H, M_OAK)
TZ = WB_H

def chair(name, x, y, yaw):
    fr = Frame((x, y), yaw)
    fr.box(name + "Seat", (0.42, 0.40, 0.04), (0, 0, 0.45), M_OAK, bevel=0.005)
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = 0.43 if sy < 0 else 0.98
            fr.box(f"{name}Leg{sx}{sy}", (0.035, 0.035, h), (sx * 0.18, sy * 0.17, h / 2), M_OAK)
    for z in (0.62, 0.78, 0.94):
        fr.box(f"{name}Slat{z}", (0.36, 0.022, 0.05), (0, 0.17, z), M_OAK)
chair("Chair", 0.10, 0.80, math.radians(185))

# --- the glassware and the instruments on the bench
def flask(name, x, y, r, neck_r, neck_h, liquid=None, z0=TZ):
    prof = [(0.0, 0.0), (r * 0.5, 0.002)] + [(r * math.sin(t), r - r * math.cos(t)) for t in np.linspace(0.5, math.pi * 0.86, 8)] + \
           [(neck_r, 2 * r * 0.93), (neck_r, 2 * r + neck_h), (neck_r * 1.3, 2 * r + neck_h + 0.006), (0.0, 2 * r + neck_h + 0.006)]
    lathe(name, prof, (x, y, z0), M_GLASS, steps=18)
    if liquid:
        lv = r * liquid
        lp = [(0.0, 0.003)] + [(r * 0.94 * math.sin(t), r - r * 0.94 * math.cos(t)) for t in np.linspace(0.3, math.acos(1 - lv / r) if lv < 2 * r else math.pi, 6)] + [(0.0, lv)]
        lathe(name + "Liquid", lp, (x, y, z0), M_LIQ, steps=16)

def retort(name, x, y, z0, r, yaw, liquid=0.6):
    """A retort: a glass globe with its long neck bent down and away, on a ring stand."""
    c = Vector((x, y, z0 + r))
    sphere(name + "Bulb", r, tuple(c), M_GLASS, seg=18)
    if liquid: sphere(name + "Liquid", r * 0.93, tuple(c - Vector((0, 0, r * 0.25))), M_LIQ, seg=14, scale=(1, 1, 0.65))
    d = Vector((math.cos(yaw), math.sin(yaw), 0))
    pts = [c + Vector((0, 0, r * 0.85))]
    for k in range(1, 9):
        t = k / 8
        pts.append(c + Vector((0, 0, r * 0.85 + 0.09 * math.sin(t * math.pi * 0.6))) + d * (0.38 * t ** 1.3) + Vector((0, 0, -0.30 * t ** 2)))
    tube(name + "Neck", [tuple(p) for p in pts], [r * 0.38 * (1 - 0.7 * k / 8) + 0.005 for k in range(9)], M_GLASS, sides=10)
    return pts[-1]

def ring_stand(name, x, y, ring_z, ring_r):
    box(name + "Base", (0.18, 0.12, 0.02), (x, y, TZ + 0.01), M_IRON)
    cyl(name + "Rod", 0.007, ring_z - TZ + 0.12, (x - 0.06, y, (ring_z + TZ + 0.12) / 2), M_IRON, verts=6)
    torus(name + "Ring", ring_r, 0.005, (x, y, ring_z), M_IRON, seg=16, rseg=4)
    cyl(name + "Arm", 0.005, 0.06, (x - 0.03, y, ring_z), M_IRON, verts=5, rot=(0, math.pi / 2, 0))

# the retort over its spirit lamp, its neck into a receiver
RX_, RY_ = 1.10, 1.55
ring_stand("RetortStand", RX_, RY_, TZ + 0.17, 0.06)
lathe("SpiritLamp", [(0.0, 0.0), (0.045, 0.0), (0.05, 0.03), (0.035, 0.07), (0.012, 0.08), (0.012, 0.10), (0.0, 0.10)], (RX_, RY_, TZ), M_GLASS, steps=14)
tip = retort("Retort", RX_, RY_, TZ + 0.13, 0.075, math.radians(-25))
flask("Receiver", tip.x + 0.06, tip.y - 0.02, 0.07, 0.022, 0.05, liquid=0.5)
# flasks, phials, a rack of tubes, jars with stoppers, a bell jar
flask("Flask0", 0.62, 1.70, 0.06, 0.016, 0.13, liquid=0.7)
flask("Flask1", 0.48, 1.62, 0.045, 0.012, 0.10)
flask("Flask2", 1.55, 1.72, 0.08, 0.02, 0.12, liquid=0.35)
for k in range(4):
    x = 1.70 + k * 0.07
    lathe(f"Phial{k}", [(0.0, 0.0), (0.016, 0.0), (0.016, 0.09 + 0.02 * k), (0.01, 0.10 + 0.02 * k), (0.0, 0.10 + 0.02 * k)], (x, 1.36, TZ), M_GLASS, steps=10)
    cyl(f"PhialCork{k}", 0.009, 0.02, (x, 1.36, TZ + 0.11 + 0.02 * k), M_CORK, verts=8)
box("TubeRack", (0.24, 0.07, 0.015), (0.85, 1.25, TZ + 0.09), M_OAK)
box("TubeRackBase", (0.24, 0.07, 0.015), (0.85, 1.25, TZ + 0.008), M_OAK)
for s in (-1, 1): box(f"TubeRackEnd{s}", (0.015, 0.07, 0.10), (0.85 + s * 0.115, 1.25, TZ + 0.05), M_OAK)
for k in range(6):
    x = 0.76 + k * 0.035
    cyl(f"TestTube{k}", 0.009, 0.15, (x, 1.25, TZ + 0.085), M_GLASS, verts=10)
    if k % 2 == 0: cyl(f"TestTubeLiq{k}", 0.007, 0.05, (x, 1.25, TZ + 0.035), M_LIQ, verts=8)
for k, (x, y, r, h) in enumerate(((1.84, 1.70, 0.05, 0.16), (1.96, 1.62, 0.04, 0.12), (0.26, 1.74, 0.045, 0.14))):
    lathe(f"Jar{k}", [(0.0, 0.0), (r, 0.0), (r, h), (r * 0.8, h + 0.01), (r * 0.8, h + 0.025), (0.0, h + 0.025)], (x, y, TZ), M_GLASS, steps=16)
    lathe(f"JarLiq{k}", [(0.0, 0.003), (r * 0.92, 0.003), (r * 0.92, h * 0.7), (0.0, h * 0.7)], (x, y, TZ), M_LIQ, steps=14)
    cyl(f"JarCork{k}", r * 0.78, 0.03, (x, y, TZ + h + 0.035), M_CORK, verts=12)
lathe("BellJar", [(0.0, 0.32), (0.04, 0.315), (0.09, 0.28), (0.11, 0.2), (0.11, 0.0), (0.105, 0.0), (0.105, 0.2), (0.085, 0.275), (0.0, 0.31)], (1.32, 1.28, TZ), M_GLASS, steps=20)
sphere("BellJarKnob", 0.02, (1.32, 1.28, TZ + 0.335), M_GLASS, seg=8)
box("BellJarPlate", (0.26, 0.26, 0.012), (1.32, 1.28, TZ + 0.006), M_PEWTER)
# the electrical apparatus: a Leyden jar and a voltaic pile of copper and zinc discs, wires
lathe("LeydenJar", [(0.0, 0.0), (0.06, 0.0), (0.06, 0.20), (0.05, 0.22), (0.0, 0.22)], (1.95, 1.30, TZ), M_GLASS, steps=16)
lathe("LeydenFoil", [(0.0, -0.001), (0.0615, -0.001), (0.0615, 0.12), (0.0, 0.12)], (1.95, 1.30, TZ), M_ZINC, steps=16)
cyl("LeydenRod", 0.004, 0.18, (1.95, 1.30, TZ + 0.29), M_BRASS, verts=6)
sphere("LeydenBall", 0.016, (1.95, 1.30, TZ + 0.385), M_BRASS, seg=10)
PILE = Vector((1.62, 1.18, TZ))
for k in range(26):
    cyl(f"PileDisc{k}", 0.032, 0.006, tuple(PILE + Vector((0, 0, 0.012 + k * 0.0075))), (M_COPPER, M_ZINC, M_CORK)[k % 3], verts=14)
for s in (-1, 1): cyl(f"PileRod{s}", 0.004, 0.24, tuple(PILE + Vector((s * 0.045, 0, 0.12))), M_OAK, verts=6)
box("PileBase", (0.14, 0.09, 0.02), tuple(PILE + Vector((0, 0, 0.01))), M_OAK)
tube("Wire0", [tuple(PILE + Vector((0, 0, 0.21))), (1.75, 1.15, TZ + 0.22), (1.86, 1.22, TZ + 0.08), (1.95, 1.30, TZ + 0.39)], [0.0025] * 4, M_COPPER, sides=4)
tube("Wire1", [tuple(PILE + Vector((0.0, -0.02, 0.012))), (1.50, 1.05, TZ + 0.005), (1.10, 1.02, TZ + 0.004), (0.80, 1.08, -0.0 + TZ + 0.003)], [0.0025] * 4, M_COPPER, sides=4)
# the mortar and pestle, a brass balance
lathe("Mortar", [(0.0, 0.03), (0.05, 0.03), (0.06, 0.0), (0.075, 0.0), (0.085, 0.09), (0.065, 0.09), (0.05, 0.05), (0.0, 0.045)], (0.30, 1.38, TZ), M_STONE, steps=16, sharp=60)
tube("Pestle", [(0.30, 1.38, TZ + 0.05), (0.36, 1.42, TZ + 0.17)], [0.018, 0.012], M_STONE, sides=8)
box("BalanceBase", (0.18, 0.08, 0.02), (1.40, 1.80, TZ + 0.01), M_OAK)
cyl("BalancePillar", 0.006, 0.24, (1.40, 1.80, TZ + 0.13), M_BRASS, verts=6)
box("BalanceBeam", (0.005, 0.22, 0.008), (1.40, 1.80, TZ + 0.25), M_BRASS)
for s in (-1, 1):
    lathe(f"BalancePan{s}", [(0.0, 0.0), (0.035, 0.008), (0.04, 0.012), (0.0, 0.012)], (1.40, 1.80 + s * 0.105, TZ + 0.10), M_BRASS, steps=12)
    for k in range(3):
        a = k * TWO_PI / 3
        tube(f"BalanceCord{s}{k}", [(1.40 + 0.033 * math.cos(a), 1.80 + s * 0.105 + 0.033 * math.sin(a), TZ + 0.11), (1.40, 1.80 + s * 0.105, TZ + 0.25)], [0.0012, 0.0012], M_IRON, sides=3)
# books: open, stacked, one propped on another
def book(name, x, y, z, L, W, T, yaw=0.0, tilt=0.0):
    o = box(name, (L, W, T), (x, y, z + T / 2), M_BOOKS, bevel=0.003, rot=(tilt, 0, yaw)); set_rnd(o, rnd.random()); return o
zc = TZ
for k in range(4):
    T = rnd.uniform(0.04, 0.07); book(f"Stack{k}", 2.02 + rnd.uniform(-0.01, 0.01), 1.68, zc, 0.30 - k * 0.02, 0.22 - k * 0.01, T, yaw=rnd.uniform(-0.12, 0.12)); zc += T
book("Propped", 0.05, 1.72, TZ + 0.05, 0.25, 0.04, 0.33, yaw=0.1, tilt=-0.45)
def open_book(name, x, y, yaw, L=0.30, W=0.22):
    fr = Frame((x, y), yaw, z0=TZ)
    fr.box(name + "Cover", (L + 0.01, 2 * W + 0.02, 0.006), (0, 0, 0.003), M_LEATHER)
    for s in (-1, 1):
        def fn(u, v, s=s):
            yy = s * (0.01 + v * W); zz = 0.006 + 0.025 * math.sin(min(1, v * 1.4) * math.pi / 2) * (1 - 0.6 * v) + 0.004
            return fr.p((u - 0.5) * L, yy, zz)
        o = K.grid_surface(name + f"Page{s}", fn, 2, 6, M_PAPER, wrap_u=False)
        u0, v0, u1, v1 = sheet_uv(2)
        for lp in o.data.loops: pass
        uvl = o.data.uv_layers.active
        for poly in o.data.polygons:
            for li in poly.loop_indices:
                uu, vv = uvl.data[li].uv
                uvl.data[li].uv = (u0 + (u1 - u0) * uu, v0 + (v1 - v0) * (vv if s > 0 else 1 - vv))
        o.data.update()
open_book("OpenBook", 0.62, 1.30, math.radians(-8))
# drawings on the bench, and pinned to the wall left of the window
def sheet_flat(name, x, y, yaw, vi, w=0.21, h=0.30, z=TZ + 0.002):
    fr = Frame((x, y), yaw, z0=z)
    c = [fr.p(-w / 2, -h / 2, 0), fr.p(w / 2, -h / 2, 0), fr.p(w / 2, h / 2, 0.003), fr.p(-w / 2, h / 2, 0)]
    paper(name, c, vi)
sheet_flat("SheetArm", 0.95, 1.12, math.radians(96), 0)
sheet_flat("SheetRibs", 1.30, 1.00, math.radians(80), 3, z=TZ + 0.003)
sheet_flat("SheetNotes", 0.38, 1.12, math.radians(100), 2)
sheet_flat("SheetFloor", -0.35, 0.65, math.radians(30), 2, z=0.002)
def sheet_wall(name, y, z, vi, w=0.24, h=0.32, tilt=0.0):
    x = X1 - 0.004; c = [(x, y + w / 2, z - h / 2), (x, y - w / 2, z - h / 2 + tilt), (x, y - w / 2, z + h / 2 + tilt), (x, y + w / 2, z + h / 2)]
    paper(name, c, vi)
    cyl(name + "Pin", 0.005, 0.01, (x - 0.004, y, z + h / 2 - 0.02), M_BRASS, verts=6, rot=(0, math.pi / 2, 0))
sheet_wall("WallArm", 0.95, 1.55, 0, tilt=0.01)
sheet_wall("WallSkull", 1.25, 1.20, 1, tilt=-0.01)
sheet_wall("WallRibs", -0.85, 1.45, 3, tilt=0.008)
# the inkstand and a quill
box("Inkstand", (0.16, 0.10, 0.02), (0.20, 1.18, TZ + 0.01), M_PEWTER)
lathe("Inkpot", [(0.0, 0.0), (0.025, 0.0), (0.028, 0.03), (0.012, 0.045), (0.0, 0.045)], (0.17, 1.18, TZ + 0.02), M_GLASS, steps=12)
tube("Quill", [(0.24, 1.16, TZ + 0.02), (0.30, 1.05, TZ + 0.09), (0.33, 0.98, TZ + 0.14)], [0.003, 0.004, 0.001], M_SHEET, sides=4)
# the candle, burnt to a stub, in its pewter stick, wax run down
CS = Vector((-0.05, 1.20, TZ))
lathe("CandleStick", [(0.0, 0.0), (0.07, 0.0), (0.072, 0.008), (0.06, 0.015), (0.02, 0.025), (0.016, 0.08), (0.03, 0.09), (0.03, 0.10), (0.0, 0.10)], tuple(CS), M_PEWTER, steps=16)
torus("CandleStickHandle", 0.025, 0.005, tuple(CS + Vector((0.075, 0, 0.012))), M_PEWTER, rot=(math.pi / 2, 0, 0), seg=10, rseg=4)
STUB_H = 0.035
lathe("CandleStub", [(0.0, 0.0), (0.0115, 0.0), (0.012, STUB_H - 0.006), (0.009, STUB_H), (0.004, STUB_H - 0.003), (0.0, STUB_H - 0.004)], tuple(CS + Vector((0, 0, 0.10))), M_WAX, steps=12)
for k in range(5):
    a = rnd.uniform(0, TWO_PI); d = Vector((math.cos(a), math.sin(a), 0))
    p0 = CS + Vector((0, 0, 0.10 + STUB_H - 0.004)) + d * 0.011
    tube(f"Drip{k}", [tuple(p0), tuple(p0 + d * 0.004 + Vector((0, 0, -0.02))), tuple(p0 + d * 0.012 + Vector((0, 0, -0.03 - rnd.uniform(0, 0.02))))], [0.004, 0.0035, 0.003], M_WAX, sides=5)
sphere("WaxPool", 0.03, tuple(CS + Vector((0.02, 0.01, 0.100))), M_WAX, seg=8, scale=(1.2, 1.0, 0.12))
WICK = CS + Vector((0, 0, 0.10 + STUB_H + 0.004))
cyl("Wick", 0.0012, 0.01, tuple(WICK - Vector((0, 0, 0.002))), M_SOOT, verts=4)

# ----------------------------------------------------------------------------- the rest of the room
# the low bookcase along the north knee wall, behind the reader's left
BC_X0, BC_X1 = -2.35, -0.55
BC_Y = HW - 0.17
box("ShelfBack", (BC_X1 - BC_X0, 0.02, 1.02), ((BC_X0 + BC_X1) / 2, HW - 0.012, 0.51), M_DEAL)
for s in (0, 1): box(f"ShelfEnd{s}", (0.03, 0.32, 1.04), ((BC_X0, BC_X1)[s], BC_Y, 0.52), M_DEAL)
for z in (0.05, 0.52, 1.02):
    box(f"Shelf{z}", (BC_X1 - BC_X0, 0.32, 0.025), ((BC_X0 + BC_X1) / 2, BC_Y, z), M_DEAL)
for z0 in (0.065, 0.535):
    x = BC_X0 + 0.03
    while x < BC_X1 - 0.08:
        if rnd.random() < 0.10:      # a gap, a jar or a book lying flat
            if rnd.random() < 0.5:
                r = rnd.uniform(0.04, 0.06); h = rnd.uniform(0.12, 0.2)
                lathe(f"ShelfJar{x:.2f}{z0}", [(0.0, 0.0), (r, 0.0), (r, h), (r * 0.8, h + 0.02), (0.0, h + 0.02)], (x + r, BC_Y, z0), M_GLASS if rnd.random() < 0.5 else M_CERAMIC, steps=12)
                x += 2 * r + 0.02
            else:
                L = rnd.uniform(0.2, 0.26); book(f"ShelfFlat{x:.2f}{z0}", x + L / 2, BC_Y, z0, L, 0.18, rnd.uniform(0.03, 0.05)); x += L + 0.01
            continue
        w = rnd.uniform(0.025, 0.06); h = rnd.uniform(0.2, 0.36); d = rnd.uniform(0.16, 0.24)
        lean = rnd.uniform(-0.06, 0.06) if rnd.random() < 0.3 else 0.0
        o = box(f"ShelfBook{x:.2f}{z0}", (w, d, h), (x + w / 2, BC_Y - (0.28 - d) / 2 + 0.03, z0 + h / 2), M_BOOKS, bevel=0.003, rot=(0, lean, 0))
        set_rnd(o, rnd.random()); x += w + 0.002
# things on the bookcase top: a skull is too much; a lamp unlit, a jar of brushes, a rolled chart
lathe("ShelfTopJar", [(0.0, 0.0), (0.05, 0.0), (0.055, 0.14), (0.045, 0.16), (0.0, 0.16)], (-2.05, BC_Y, 1.035), M_CERAMIC, steps=12)
tube("RolledChart", [(-1.6, BC_Y, 1.075), (-1.0, BC_Y + 0.02, 1.075)], [0.035, 0.035], M_PAPER, sides=10)

# the narrow bed under the south slope, behind the reader's right
BD = Vector((-2.05, -1.98, 0.0)); BD_L, BD_W = 1.85, 0.80
for sx in (-1, 1):
    for sy in (-1, 1):
        box(f"BedPost{sx}{sy}", (0.06, 0.06, 0.55 if sx < 0 else 0.42), (BD.x + sx * BD_L / 2, BD.y + sy * BD_W / 2, (0.55 if sx < 0 else 0.42) / 2), M_DEAL)
for sy in (-1, 1): box(f"BedRail{sy}", (BD_L, 0.04, 0.12), (BD.x, BD.y + sy * BD_W / 2, 0.30), M_DEAL)
box("BedHead", (0.03, BD_W, 0.28), (BD.x - BD_L / 2, BD.y, 0.40), M_DEAL)
box("Mattress", (BD_L - 0.06, BD_W - 0.06, 0.12), (BD.x, BD.y, 0.40), M_TICKING, bevel=0.03, seg=2)
def blanket():
    def fn(u, v):
        x = BD.x - BD_L / 2 + 0.35 + u * (BD_L - 0.35); y = BD.y - BD_W / 2 - 0.12 + v * (BD_W + 0.24)
        inside = min(v * (BD_W + 0.24), (1 - v) * (BD_W + 0.24))
        z = 0.47 + 0.03 * math.sin(u * 9 + v * 4) * math.sin(v * math.pi) + 0.05 * math.exp(-((u - 0.25) / 0.12) ** 2) * math.sin(v * math.pi)
        if inside < 0.12: z = 0.47 - (0.12 - inside) * 2.2; y = BD.y + (BD_W / 2 + 0.02) * (1 if v > 0.5 else -1) + 0.02 * math.sin(u * 23) * (0.12 - inside) * 8
        return (x, y, z)
    o = K.grid_surface("Blanket", fn, 24, 16, M_BLANKET, wrap_u=False)
    K.orient(o, lambda c: (c - Vector((BD.x, BD.y, 0.2))))
blanket()
sphere("Pillow", 0.25, (BD.x - BD_L / 2 + 0.22, BD.y, 0.50), M_TICKING, seg=12, scale=(0.55, 1.2, 0.3))

# a sea chest at the foot of the bed, a washstand by the door, a bucket
box("Chest", (0.40, 0.75, 0.42), (-0.45, -2.12, 0.21), M_OAK, bevel=0.01)
for s in (-1, 1): box(f"ChestBand{s}", (0.42, 0.03, 0.43), (-0.45, -2.12 + s * 0.25, 0.215), M_IRON)
box("Wash", (0.45, 0.40, 0.75), (-2.70, 2.15, 0.375), M_DEAL, bevel=0.005)
lathe("Basin", [(0.0, 0.0), (0.08, 0.0), (0.17, 0.08), (0.18, 0.085), (0.165, 0.085), (0.075, 0.012), (0.0, 0.012)], (-2.70, 2.15, 0.75), M_CERAMIC, steps=18, sharp=70)
lathe("Jug", [(0.0, 0.0), (0.06, 0.0), (0.09, 0.08), (0.08, 0.17), (0.05, 0.22), (0.06, 0.25), (0.0, 0.25)], (-2.42, 2.30, 0.0), M_CERAMIC, steps=14)
lathe("Bucket", [(0.0, 0.0), (0.12, 0.0), (0.14, 0.26), (0.0, 0.26)], (2.55, -1.95, 0.0), M_DEAL, steps=14)
torus("BucketHoop", 0.135, 0.006, (2.55, -1.95, 0.18), M_IRON, seg=16, rseg=4)
# a crate of more glass in straw under the bench, a basket under the long table
box("Crate", (0.5, 0.38, 0.30), (1.55, 1.75, 0.15), M_DEAL, bevel=0.005)
for k in range(3): flask(f"CrateFlask{k}", 1.42 + k * 0.12, 1.75, 0.045, 0.012, 0.06, z0=0.21)
lathe("Basket", [(0.0, 0.0), (0.16, 0.0), (0.2, 0.22), (0.0, 0.22)], (1.9, -1.45, 0.0), M_CORK, steps=16)
for k in range(3):
    book(f"FloorBook{k}", 2.45 + k * 0.03, 1.05, k * 0.05, 0.28, 0.2, 0.05, yaw=rnd.uniform(-0.4, 0.4))

# ----------------------------------------------------------------------------- lights (names starting "Lamp" are baked in Unity)
F.light("Lamp.candle", 'POINT', 6.0, (1.0, 0.70, 0.42), tuple(WICK + Vector((0, 0, 0.015))), size=0.01)
F.light("Lamp.fire", 'POINT', 12.0, (1.0, 0.42, 0.15), tuple(FIRE + Vector((0.16, 0, 0.06))), size=0.15)
F.light("Lamp.window", 'SPOT', 45.0, (0.55, 0.65, 1.0), (X1 + 0.05, WIN_Y, WIN_Z0 + WIN_H * 0.75), size=0.35,
        aim=(1.0, -1.3, 0.75), spot=(math.radians(150), 1.0))
world = bpy.data.worlds.new("Night"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.004, 0.005, 0.008, 1); bg.inputs["Strength"].default_value = 1.0

# preview flames (Blender stills only; Unity makes its own flame on fx.candle.0 / fx.fire.0)
M_FLAME = plain("M_PreviewFlame", (1.0, 0.6, 0.25), emission=(1.0, 0.55, 0.18), strength=25.0)
PREVIEW = [lathe("PreviewFlame", [(0.0, 0.0), (0.004, 0.004), (0.005, 0.012), (0.0035, 0.022), (0.0, 0.032)], tuple(WICK - Vector((0, 0, 0.001))), M_FLAME, steps=8)]
for k, (dy, h) in enumerate(((-0.08, 0.07), (0.05, 0.05), (0.13, 0.04))):
    PREVIEW.append(lathe(f"PreviewFire{k}", [(0.0, 0.0), (0.02, 0.01), (0.018, h * 0.5), (0.0, h)], (GX + 0.02, dy, 0.19), M_FLAME, steps=8))
for o in PREVIEW: o.visible_shadow = False

# ----------------------------------------------------------------------------- anchors and living-scene markers
anchor("reader.entrance", (READER.x, READER.y, 0.0))
anchor("reader.look", (READER.x + 2.0, READER.y, EYE))
anchor("scene.centre", (0.0, 0.0, 0.0))
anchor("room.window", (X1 + 0.2, WIN_Y, WIN_Z0 + WIN_H / 2))
anchor("room.fire", tuple(FIRE))
anchor("room.candle", tuple(WICK))
anchor("room.bench", (WB.x, WB.y, TZ))
anchor("room.form", (LT.x, LT.y, LT_H + 0.2))
anchor("room.door", (X0, (DOOR_Y0 + DOOR_Y1) / 2, 0.0))
F.fx("fx.candle.0", tuple(WICK), radius=0.008)
F.fx("fx.fire.0", tuple(FIRE), radius=0.14)
F.sound("sound.rain.0", (X1 + 0.5, WIN_Y, WIN_Z0 + WIN_H * 0.7))
F.sound("sound.fire.0", tuple(FIRE + Vector((0.1, 0, 0.1))))

K.apply_all_transforms()

# ----------------------------------------------------------------------------- cameras (reader eye 1.55 m; lens 18 ~ the headset's 90 deg)
E = Vector((READER.x, READER.y, EYE))
def ahead(yaw_deg, pitch_deg=0.0, d=3.0):
    a = math.radians(yaw_deg); p = math.radians(pitch_deg)
    return tuple(E + Vector((math.cos(a) * math.cos(p), math.sin(a) * math.cos(p), math.sin(p))) * d)
cams = [
    camera("Cam_Reader", tuple(E), ahead(0, -6)),
    camera("Cam_Left", tuple(E), ahead(62, -22)),
    camera("Cam_Right", tuple(E), ahead(-60, -22)),
    camera("Cam_Behind", tuple(E), ahead(180, -14)),
    camera("Cam_Up", tuple(E), ahead(20, 55)),
    camera("Cam_Bench", (0.55, 0.55, 1.25), (1.15, 1.45, 0.95), lens=24),
    camera("Cam_Form", (-0.25, -0.35, 1.45), (1.4, -1.45, 0.85), lens=20),
    camera("Cam_Overview", (2.6, -1.1, 1.75), (-1.4, 0.6, 0.7), lens=14),
]
EXPOSURE = {}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "ingolstadt_garret_source.blend"))
K.budget_report()

if args.render:
    F.render_stills(scene, cams, EXPOSURE, default_exp=1.9, label="ingolstadt-garret")

if args.bake or args.export:
    for o in PREVIEW: bpy.data.objects.remove(o)
    T_ = args.tex
    size_for = {"M_Floorboards": (T_, T_ // 2, T_ // 2), "M_Plaster": (T_, T_ // 4, T_ // 2), "M_RoofBoards": (T_, T_ // 4, T_ // 2),
                "M_BeamsX": (T_ // 2, T_ // 8, T_ // 4), "M_Rafters": (T_ // 2, T_ // 8, T_ // 4), "M_Oak": (T_ // 2, T_ // 8, T_ // 4),
                "M_Deal": (T_ // 2, T_ // 8, T_ // 4), "M_DoorBoards": (T_ // 4, T_ // 8, T_ // 4), "M_Stone": (T_ // 4, T_ // 8, T_ // 4),
                "M_Sooty": (T_ // 8,), "M_Iron": (T_ // 4, T_ // 8), "M_Brass": (T_ // 8, T_ // 16), "M_Pewter": (T_ // 8, T_ // 16),
                "M_Copper": (T_ // 8,), "M_Zinc": (T_ // 16,), "M_Glass": (64,), "M_PaneGlass": (64,), "M_Liquid": (64,),
                "M_Sheet": (T_ // 2, T_ // 8, T_ // 4), "M_Blanket": (T_ // 4, T_ // 16, T_ // 8), "M_Ticking": (T_ // 8,),
                "M_Wax": (64,), "M_Stoneware": (T_ // 8,), "M_Cork": (T_ // 16,), "M_Leather": (T_ // 16,), "M_Ash": (T_ // 16,),
                "M_Embers": (T_ // 8,), "M_Books": (T_ // 4, T_ // 16)}
    F.bake_and_export(scene, "ingolstadt_garret.gltf", size_for, keep_names={"M_NightView": "far.night"}, cams=cams,
                      blend_name="ingolstadt_garret_baked.blend")
print("DONE")
