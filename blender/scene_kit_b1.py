"""
Fable: shared helpers for the chapter step-in rooms built by room builder 1 (build_pool_bank.py,
build_new_bedford_spouter_corner.py, build_pylos_shore.py, ... see docs/SCENE_ROOMS.md).

Builds on pride_kit.py (node materials, primitives, MB card builder, Canvas atlases, Cycles stills stamped
"Blender render") and eighty_kit.py (bake + merge-by-material + glTF export with extras, water.* handling, fx radius).
What is added here, generalised from build_pillaji_forest.py and build_horsell_sandpits.py:

  * ground(): a log-polar terrain disc round the reader (texel density highest at the reader's feet) from a height
    function, with optional per-vertex float attributes for the ground material (paths, wet margins ...)
  * spray atlases (leafy twig sprays of several species) and a plant atlas of 4 x 2 cells (grasses, reeds, sedges,
    ferns, docks ...), painted in numpy; alpha-clipped cards (glTF MASK) with rounded custom normals
  * tree(): a trunk forking into limbs and branches grown to a crown envelope, leaf-spray cards at the tips and
    through the crown's shell (no blob trees)
  * rock(): a faceted, noise-displaced, half-buried stone; pebble()
  * far bands, sky dome, cameras round the reader, and finish() (budget, stills, bake/export)

Everything procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os, json
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
import eighty_kit as E8
from eighty_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                        wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound,
                        light_obj, camera, link, smoothstep, lerp, n2, fbm2, add_sway, orient)

TWO_PI = 2 * math.pi
GZ = lambda x, y: 0.0          # the room's ground height function (set_ground)
EYE = 1.55


def setup(scene_id, seed, coll_name, samples=48):
    args = K.setup(scene_id, f"out/{scene_id}", seed, coll_name, default_samples=samples)
    if not args.captures:
        args.captures = os.path.join("captures", "blender", scene_id)
    return args


def set_ground(fn):
    global GZ
    GZ = fn


def az_dir(az):
    a = math.radians(az); return Vector((math.sin(a), math.cos(a), 0.0))


def seg_dist(x, y, pts):
    best = 1e9
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy + 1e-12
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L2))
        best = min(best, math.hypot(x - (x0 + t * dx), y - (y0 + t * dy)))
    return best


# ----------------------------------------------------------------------------- ground (log-polar disc round the reader)
def ground(name, mat, near_r, r0=2.5, NA=64, NR=28, attrs=None, centre=(0.0, 0.0), skip=None):
    """A disc of radius near_r round centre; rings spaced log-polar (r0 sets how tight near the middle), UV u round,
    v outward (log), so a baked texture is sharpest at the reader's feet. attrs: {name: fn(x, y) -> float} written as
    point attributes for the material. skip(x, y) -> True drops faces whose centre is there (holes for water)."""
    cx, cy = centre
    def v_of_r(r): return math.log1p(r / r0) / math.log1p(near_r / r0)
    rs = [0.0] + [r0 * math.expm1((j / NR) * math.log1p(near_r / r0)) for j in range(1, NR + 1)]
    verts = [(cx, cy, GZ(cx, cy))]
    for j in range(1, NR + 1):
        for i in range(NA):
            a = TWO_PI * i / NA; x, y = cx + rs[j] * math.sin(a), cy + rs[j] * math.cos(a)
            verts.append((x, y, GZ(x, y)))
    def vi(j, i): return 0 if j == 0 else 1 + (j - 1) * NA + (i % NA)
    faces = []; luv = []
    for j in range(NR):
        for i in range(NA):
            u0, u1 = i / NA, (i + 1) / NA; v0, v1 = v_of_r(rs[j]), v_of_r(rs[j + 1])
            if j == 0:
                f = (vi(0, 0), vi(1, i), vi(1, i + 1)); uv = [((u0 + u1) / 2, 0.0), (u0, v1), (u1, v1)]
            else:
                f = (vi(j, i), vi(j + 1, i), vi(j + 1, i + 1), vi(j, i + 1)); uv = [(u0, v0), (u0, v1), (u1, v1), (u1, v0)]
            if skip is not None:
                c = sum((Vector(verts[k]) for k in f), Vector()) / len(f)
                if skip(c.x, c.y): continue
            faces.append(f); luv.append(uv)
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for p, uvs in zip(me.polygons, luv):
        for li, uv in zip(p.loop_indices, uvs): uvl.data[li].uv = uv
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    link(o)
    for an, fn in (attrs or {}).items():
        at = me.attributes.new(an, 'FLOAT', 'POINT'); at.data.foreach_set("value", [fn(v[0], v[1]) for v in verts])
    orient(o, lambda c: (0, 0, 1))
    return o


def ring_band(name, mat, r_in, r_out, z_in, z_out, seg=72, row=None):
    """A flat-ish annulus (far land) from r_in at z_in(x,y) to r_out at height z_out."""
    verts = []; faces = []
    for k, r in enumerate((r_in, r_out)):
        for i in range(seg):
            a = TWO_PI * i / seg; x, y = r * math.sin(a), r * math.cos(a)
            verts.append((x, y, z_in(x, y) if k == 0 else z_out))
    for i in range(seg):
        j = (i + 1) % seg; faces.append((i, j, seg + j, seg + i))
    return orient(mesh_from(name, verts, faces, mat), lambda c: (0, 0, 1))


# ----------------------------------------------------------------------------- painted atlases
SPRAY_KINDS = {
    #            palette (sRGB), leaves per node, size px, tip, (width k, length k), bark
    "oak":      ([(0.16, 0.22, 0.07), (0.20, 0.27, 0.08), (0.24, 0.30, 0.10), (0.14, 0.19, 0.06), (0.28, 0.32, 0.12)], 5, 15.0, 0.25, (0.45, 0.8), (0.22, 0.17, 0.12)),
    "ash":      ([(0.22, 0.30, 0.10), (0.26, 0.34, 0.12), (0.30, 0.36, 0.13), (0.19, 0.27, 0.09)], 7, 11.0, 0.6, (0.3, 0.85), (0.30, 0.28, 0.24)),
    "willow":   ([(0.30, 0.36, 0.20), (0.36, 0.42, 0.24), (0.26, 0.33, 0.17), (0.42, 0.46, 0.30)], 8, 15.0, 0.9, (0.13, 1.0), (0.32, 0.28, 0.18)),
    "alder":    ([(0.10, 0.17, 0.06), (0.13, 0.20, 0.07), (0.16, 0.23, 0.08), (0.11, 0.16, 0.06)], 5, 14.0, 0.1, (0.55, 0.7), (0.20, 0.17, 0.14)),
    "olive":    ([(0.36, 0.40, 0.30), (0.42, 0.46, 0.36), (0.30, 0.34, 0.25), (0.48, 0.50, 0.42)], 8, 13.0, 0.85, (0.18, 0.95), (0.30, 0.27, 0.22)),
    "plane":    ([(0.20, 0.30, 0.09), (0.26, 0.34, 0.11), (0.30, 0.38, 0.13), (0.18, 0.26, 0.08)], 3, 22.0, 0.2, (0.6, 0.7), (0.32, 0.30, 0.24)),
    "autumn":   ([(0.45, 0.30, 0.10), (0.52, 0.36, 0.12), (0.36, 0.30, 0.10), (0.30, 0.28, 0.10), (0.58, 0.42, 0.16)], 4, 14.0, 0.25, (0.45, 0.8), (0.22, 0.18, 0.14)),
    "pine":     ([(0.10, 0.16, 0.08), (0.12, 0.19, 0.09), (0.15, 0.21, 0.10), (0.09, 0.14, 0.07)], 0, 0.0, 0.0, (0, 0), (0.30, 0.20, 0.14)),
    "dark":     ([(0.06, 0.10, 0.04), (0.08, 0.13, 0.05), (0.10, 0.15, 0.06), (0.07, 0.11, 0.05)], 5, 13.0, 0.35, (0.42, 0.8), (0.16, 0.13, 0.10)),
    "beech":    ([(0.12, 0.20, 0.06), (0.16, 0.25, 0.08), (0.20, 0.29, 0.09), (0.10, 0.17, 0.05), (0.24, 0.31, 0.11)], 5, 13.0, 0.3, (0.42, 0.75), (0.30, 0.29, 0.27)),
    "hawthorn": ([(0.10, 0.17, 0.05), (0.13, 0.21, 0.06), (0.16, 0.24, 0.07), (0.09, 0.14, 0.05)], 6, 9.0, 0.2, (0.5, 0.7), (0.22, 0.18, 0.14)),
    "mango":    ([(0.08, 0.15, 0.05), (0.10, 0.18, 0.06), (0.13, 0.21, 0.07), (0.09, 0.14, 0.05)], 5, 22.0, 0.8, (0.22, 1.0), (0.20, 0.16, 0.12)),
}


def spray(cv, x0, y0, x1, y1, R, kind):
    """A leafy twig spray drawn into the cell (x0, y0)-(x1, y1) (pixels, y down): a forking twig, leaves at its nodes."""
    pal, nper, size, tip, (wk, lk), bark = SPRAY_KINDS[kind]
    W, Hh = x1 - x0, y1 - y0
    stack = [((x0 + W * 0.5 + R.gauss(0, W * 0.05), y1 - 2), R.gauss(0, 0.2), Hh * 0.6, 4.5, 0)]
    nodes = []
    while stack:
        (x, y), a, L, w, depth = stack.pop()
        segs = 5; px, py = x, y
        for sgi in range(segs):
            a += R.gauss(0, 0.16)
            nx, ny = px + math.sin(a) * L / segs, py - math.cos(a) * L / segs
            nx = min(max(nx, x0 + 6), x1 - 6); ny = min(max(ny, y0 + 6), y1 - 2)
            ww = w * (1 - sgi / segs * 0.5)
            cv.line((px, py), (nx, ny), ww * 0.5, ww * 0.42, bark + (1.0,))
            if depth >= 1 or sgi >= 2: nodes.append((nx, ny, a))
            if depth < 2 and R.random() < 0.5:
                stack.append(((nx, ny), a + R.choice((-1, 1)) * R.uniform(0.45, 0.95), L * R.uniform(0.45, 0.7), w * 0.62, depth + 1))
            px, py = nx, ny
        nodes.append((px, py, a))
    if kind == "pine":
        for (x, y, a) in nodes:
            for k in range(14):
                b_ = a + R.choice((-1, 1)) * R.uniform(0.4, 1.2); L = R.uniform(9, 18)
                col = R.choice(pal); sh = R.uniform(0.8, 1.2)
                cv.line((x, y), (x + math.sin(b_) * L, y - math.cos(b_) * L), 1.4, 0.6, (col[0] * sh, col[1] * sh, col[2] * sh, 1.0))
        return
    for (x, y, a) in nodes:
        for k in range(nper):
            b_ = a + R.gauss(0, 1.0); d = R.uniform(2, size * 1.2)
            lx, ly = x + math.sin(b_) * d, y - math.cos(b_) * d
            if not (x0 + 4 < lx < x1 - 4 and y0 + 4 < ly < y1 - 4): continue
            col = R.choice(pal); sh = R.uniform(0.82, 1.15); col = (col[0] * sh, col[1] * sh, col[2] * sh)
            s = size * R.uniform(0.7, 1.25)
            cv.ellipse(lx, ly, s * wk, s * lk, b_, col + (1.0,), tip=tip)
            cv.line((lx - math.sin(b_) * s * 0.6, ly + math.cos(b_) * s * 0.6), (lx + math.sin(b_) * s * 0.6, ly - math.cos(b_) * s * 0.6), 0.6, 0.3,
                    (min(1, col[0] * 1.3), min(1, col[1] * 1.25), min(1, col[2] * 1.1), 1.0))


def spray_atlas(name, kind, seed, S=1024, per=3):
    """2 x 2 cells of sprays (QUAD cells)."""
    cv = Canvas(S, S); R = random.Random(seed); h = S // 2
    for (cx, cy) in ((0, 0), (h, 0), (0, h), (h, h)):
        cv.clip = (cx + 1, cy + 1, cx + h - 1, cy + h - 1)
        for k in range(per): spray(cv, cx + 4, cy + 4, cx + h - 4, cy + h - 4, R, kind)
    cv.clip = None; cv.bleed(6)
    return np_image(name, cv.a)


def blade(cv, x0, y0, length, ang, curve, w0, col_base, col_tip, segs=9, taper=0.9):
    x, y = x0, y0; a = ang
    for i in range(segs):
        t0, t1 = i / segs, (i + 1) / segs
        nx = x + math.sin(a) * length / segs; ny = y - math.cos(a) * length / segs
        col = tuple(cb + (ct - cb) * t1 for cb, ct in zip(col_base, col_tip)) + (1.0,)
        cv.line((x, y), (nx, ny), w0 * (1 - t0 * taper), w0 * (1 - t1 * taper), col)
        x, y = nx, ny; a += curve / segs * (1 + t0)
    return x, y


GREENS = [(0.16, 0.22, 0.07), (0.20, 0.26, 0.08), (0.24, 0.28, 0.09), (0.14, 0.20, 0.06)]
STRAW = [(0.52, 0.44, 0.26), (0.46, 0.38, 0.22), (0.58, 0.50, 0.30)]


def _plant_cell(cv, kind, x0, y0, x1, y1, R, greens, straw):
    cx = (x0 + x1) / 2; W = x1 - x0; Hc = y1 - y0
    if kind in ("tussock", "grass", "tallgrass", "straw"):
        n = {"tussock": 90, "grass": 60, "tallgrass": 70, "straw": 70}[kind]
        for i in range(n):
            bx = cx + R.gauss(0, W * (0.10 if kind == "tussock" else 0.13))
            pool = straw if (kind == "straw" or (kind == "tussock" and R.random() < 0.35)) else greens
            g = R.choice(pool)
            L = Hc * (R.uniform(0.35, 0.95) if kind != "grass" else R.uniform(0.25, 0.55))
            spread = (bx - cx) / (W * 0.5) * (0.9 if kind == "tussock" else 0.5)
            blade(cv, bx, y1 - 4, L, R.gauss(0, 0.2) + spread, R.gauss(0, 0.9) + spread * 0.8, R.uniform(2.2, 3.8), g,
                  tuple(min(1, c * 1.35) for c in g), segs=12)
    elif kind == "reed":          # common reed: tall stems, long drooping leaves, a feathery purple-brown plume
        for i in range(9):
            bx = cx + R.gauss(0, W * 0.12); top = y0 + R.uniform(10, Hc * 0.2)
            ang = R.gauss(0, 0.05)
            cv.line((bx, y1 - 2), (bx + math.sin(ang) * (y1 - top), top), 2.6, 1.6, (0.42, 0.40, 0.24, 1.0))
            for k in range(6):
                t = R.uniform(0.15, 0.8); py = y1 - (y1 - top) * t; px = bx + math.sin(ang) * (y1 - top) * t
                g = R.choice(greens); sd = R.choice((-1, 1))
                blade(cv, px, py, R.uniform(60, 120), sd * R.uniform(0.6, 1.1), sd * R.uniform(0.6, 1.4), 4.0, g, tuple(min(1, c * 1.3) for c in g), segs=8)
            for k in range(40):
                py = top + R.uniform(0, 50); px = bx + math.sin(ang) * (y1 - py) + R.gauss(0, 6)
                cv.line((bx + math.sin(ang) * (y1 - py), py), (px, py + R.uniform(4, 14)), 1.2, 0.5, (0.38, 0.30, 0.26, 1.0))
    elif kind == "bulrush":       # reedmace: flat leaves, a brown sausage head on a few stems
        for i in range(14):
            g = R.choice(greens); bx = cx + R.gauss(0, W * 0.1)
            blade(cv, bx, y1 - 2, Hc * R.uniform(0.55, 0.95), R.gauss(0, 0.15), R.gauss(0, 0.4), 5.0, g, tuple(min(1, c * 1.3) for c in g), segs=10, taper=0.7)
        for i in range(3):
            bx = cx + R.gauss(0, W * 0.08); top = y0 + R.uniform(20, 60)
            cv.line((bx, y1 - 2), (bx, top), 2.2, 1.6, (0.36, 0.38, 0.20, 1.0))
            cv.ellipse(bx, top + 34, 7, 30, 0.0, (0.28, 0.17, 0.09, 1.0))
            cv.line((bx, top + 4), (bx, top - 18), 1.2, 0.6, (0.40, 0.36, 0.22, 1.0))
    elif kind == "sedge":
        for i in range(60):
            g = R.choice(greens); bx = cx + R.gauss(0, W * 0.08)
            blade(cv, bx, y1 - 3, Hc * R.uniform(0.3, 0.8), R.gauss(0, 0.45), R.gauss(0, 1.3), R.uniform(2.5, 3.5), g, tuple(min(1, c * 1.3) for c in g), segs=10)
    elif kind == "fern":
        for f in range(7):
            a = -1.0 + f * 0.33 + R.gauss(0, 0.1); L = R.uniform(0.5, 0.82) * Hc; x, y = cx, y1 - 6
            g = R.choice(greens)
            for k in range(14):
                t = k / 14; nx = x + math.sin(a) * L / 14; ny = y - math.cos(a) * L / 14
                cv.line((x, y), (nx, ny), 2.0, 1.6, (0.18, 0.16, 0.08, 1.0))
                pl = 26 * (1 - t) ** 0.8 + 4
                for sg in (-1, 1):
                    cv.ellipse(nx + math.cos(a) * sg * pl * 0.5, ny + math.sin(a) * sg * pl * 0.5, pl * 0.5, 4.5, a + sg * 1.57, g + (1.0,), tip=0.3)
                x, y = nx, ny; a += 0.07 * math.copysign(1, a)
    elif kind == "dock":          # broad-leaved herb (dock, plantain, burdock)
        for k in range(7):
            a = R.uniform(-1.0, 1.0); L = R.uniform(0.4, 0.75) * Hc; Wl = L * 0.24
            ex, ey = cx + math.sin(a) * L * 0.55, y1 - 6 - math.cos(a) * L * 0.55
            g = R.choice(greens)
            cv.line((cx, y1 - 6), (ex, ey), 3.0, 2.0, (0.22, 0.20, 0.10, 1.0))
            cv.ellipse(ex + math.sin(a) * L * 0.2, ey - math.cos(a) * L * 0.2, Wl, L * 0.42, a, g + (1.0,), tip=0.5)
    elif kind == "flowers":       # meadow flowers in grass (buttercup/daisy heads)
        _plant_cell(cv, "grass", x0, y0, x1, y1, R, greens, straw)
        for k in range(18):
            bx = cx + R.gauss(0, W * 0.15); top = y1 - R.uniform(0.3, 0.7) * Hc
            cv.line((bx, y1 - 2), (bx + R.gauss(0, 8), top), 1.4, 1.0, (0.24, 0.30, 0.10, 1.0))
            col = R.choice([(0.95, 0.80, 0.15), (0.95, 0.95, 0.90), (0.85, 0.75, 0.20)])
            cv.ellipse(bx, top, 6, 6, 0, col + (1.0,))
    elif kind == "weed":          # tall dry weeds/thistle stalks
        for i in range(10):
            bx = cx + R.gauss(0, W * 0.12); g = R.choice(straw)
            ex, ey = blade(cv, bx, y1 - 2, Hc * R.uniform(0.5, 0.9), R.gauss(0, 0.15), R.gauss(0, 0.3), 2.5, g, g, segs=8, taper=0.5)
            for k in range(3):
                cv.ellipse(ex + R.gauss(0, 10), ey + R.uniform(0, 30), 5, 5, 0, (0.40, 0.32, 0.22, 1.0))


def plant_atlas(name, kinds, seed=31, S=1024, greens=None, straw=None):
    """kinds: 8 names for the 4 x 2 cells (256 wide, 512 tall each). Returns (image, {kind: uv rect})."""
    cv = Canvas(S, S); R = random.Random(seed)
    greens = greens or GREENS; straw = straw or STRAW
    cells = {}
    cw, ch = S // 4, S // 2
    for i, kind in enumerate(kinds):
        c, r = i % 4, i // 4
        x0, y0 = c * cw, r * ch
        cv.clip = (x0 + 1, y0 + 1, x0 + cw - 1, y0 + ch - 1)
        _plant_cell(cv, kind, x0, y0, x0 + cw, y0 + ch, R, greens, straw)
        # image row 0 is the top: cell row r=0 is the top half -> v from 0.5 to 1.0
        cells.setdefault(kind, (c * 0.25, 0.5 if r == 0 else 0.0, c * 0.25 + 0.25, 1.0 if r == 0 else 0.5))
    cv.clip = None; cv.bleed(6)
    return np_image(name, cv.a), cells


QUAD = [(0.0, 0.5, 0.5, 1.0), (0.5, 0.5, 1.0, 1.0), (0.0, 0.0, 0.5, 0.5), (0.5, 0.0, 1.0, 0.5)]


def set_card_normals(o, fn):
    me = o.data
    me.normals_split_custom_set_from_vertices([tuple(fn(v.co)) for v in me.vertices])


def card(mb, base, right, up, cell, sway0, sway1, bend=None, segs=1):
    base = Vector(base); right = Vector(right); up = Vector(up)
    u0, v0, u1, v1 = cell; rows = []
    for k in range(segs + 1):
        t = k / segs
        off = up * t + (bend * (t * t) if bend is not None else Vector())
        sw = sway0 + (sway1 - sway0) * t
        rows.append((mb.vert(base - right * 0.5 + off, (u0, v0 + (v1 - v0) * t), sw), mb.vert(base + right * 0.5 + off, (u1, v0 + (v1 - v0) * t), sw)))
    for k in range(segs):
        a, b_ = rows[k]; c, d = rows[k + 1]; mb.face(a, b_, d, c)


def plant(mb, x, y, h, cell, R, face_to=(0.0, 0.0), n=1, sink=0.03, lean=0.06, bend=0.15, segs=2, wk=0.5):
    """n crossed cards of a plant cell standing at (x, y), turned roughly toward face_to (the reader)."""
    z = GZ(x, y)
    to = Vector((face_to[0] - x, face_to[1] - y, 0))
    base_yaw = math.atan2(to.y, to.x) + math.pi / 2 if to.length > 1e-3 else R.uniform(0, math.pi)
    for c in range(n):
        ya = base_yaw + R.gauss(0, 0.45) + c * (math.pi / max(1, n))
        right = Vector((math.cos(ya), math.sin(ya), 0)) * h * wk
        card(mb, (x, y, z - sink), right, Vector((R.gauss(0, lean), R.gauss(0, lean), h)), cell, 0.0, 1.0, segs=segs,
             bend=Vector((R.gauss(0, bend), R.gauss(0, bend), 0)) * h)


# ----------------------------------------------------------------------------- trees
CROWN_MB = {}
CROWNS = []
TREE_SHAPES = {   # trunk fraction, spread multiplier, base radius / height, limb sag, wobble, limb elevation range
    "oak":    (0.30, 1.0, 0.030, 0.06, 0.16, (0.05, 0.75)),
    "ash":    (0.45, 0.8, 0.022, 0.0, 0.10, (0.35, 1.0)),
    "willow": (0.25, 1.0, 0.040, 0.10, 0.14, (0.2, 0.9)),
    "alder":  (0.40, 0.7, 0.020, 0.0, 0.08, (0.4, 1.0)),
    "olive":  (0.25, 1.0, 0.045, 0.04, 0.22, (0.1, 0.8)),
    "plane":  (0.40, 0.9, 0.026, 0.03, 0.12, (0.25, 0.95)),
    "pine":   (0.62, 0.8, 0.022, 0.05, 0.10, (0.0, 0.5)),
    "far":    (0.45, 0.8, 0.020, 0.0, 0.10, (0.3, 1.0)),
}


def tree(name, x, y, height, spread, kind, seed, bark, leaves_key, nlimbs=6, detail=1.0, cards_per_tip=2, card_size=1.3,
         lean=(0, 0), fill=0, roots=True, weep=0.0):
    """Trunk -> limbs to a crown envelope -> branches; leaf-spray cards at the tips and on the crown shell.
    weep > 0 hangs extra drooping cards (willow)."""
    R = random.Random(seed)
    z0 = GZ(x, y) - 0.2
    base = Vector((x, y, z0))
    tf, sk, rk, sag, wob, (el0, el1) = TREE_SHAPES[kind]
    trunk_h = height * tf
    a_ = spread * sk; c_ = (height - trunk_h) * 0.5
    C = base + Vector((lean[0], lean[1], trunk_h + c_ * 0.95))
    r0 = height * rk
    def env(az, el, k=1.0):
        return C + Vector((math.cos(az) * math.cos(el) * a_ * (1 + 0.12 * R.gauss(0, 1)), math.sin(az) * math.cos(el) * a_ * (1 + 0.12 * R.gauss(0, 1)), math.sin(el) * c_)) * k
    tubes = []; tips = []
    top = base + Vector((lean[0], lean[1], trunk_h))
    tp = [base + (top - base) * t + Vector((R.gauss(0, 0.06), R.gauss(0, 0.06), 0)) * float(t > 0) for t in (0, 0.08, 0.3, 0.65, 1.0)]
    if kind == "pine":   # the leader carries on up through the crown
        tp += [top + Vector((R.gauss(0, 0.1), R.gauss(0, 0.1), c_ * 1.6))]
        tubes.append((tp, [r0 * 1.7, r0 * 1.25, r0 * 1.05, r0 * 0.95, r0 * 0.8, r0 * 0.3], 9 if detail >= 1 else 5))
    else:
        tubes.append((tp, [r0 * 1.9, r0 * 1.3, r0 * 1.05, r0 * 0.95, r0 * 0.85], 9 if detail >= 1 else 5))
    def bent(p0, p1, sg, n, wb):
        pts = []
        for i in range(n + 1):
            t = i / n; q = p0.lerp(p1, t); q.z -= sg * math.sin(math.pi * t) * (p1 - p0).length
            if 0 < i < n: q += Vector((R.gauss(0, wb), R.gauss(0, wb), R.gauss(0, wb)))
            pts.append(q)
        return pts
    for i in range(nlimbs):
        az = TWO_PI * (i + R.uniform(-0.3, 0.3)) / nlimbs
        el = R.uniform(el0, el1)
        if kind == "pine":
            start = tp[2].lerp(tp[-1], (i + 0.5) / nlimbs)
        else:
            start = tp[-1] if i % 3 else tp[-2].lerp(tp[-1], 0.6)
        tgt = env(az, el, 0.8)
        if kind == "pine": tgt = Vector((tgt.x, tgt.y, start.z + R.uniform(-0.3, 0.8)))
        lp = bent(start, tgt, sag, 4, wob * spread * 0.08)
        rl = [r0 * 0.6 * (1 - 0.6 * k / 4) for k in range(5)]
        if kind == "pine": rl = [r * 0.5 for r in rl]
        tubes.append((lp, rl, 5 if detail >= 1 else 3) if detail >= 0.5 else (lp[::2], rl[::2], 3))
        tips.append((lp[-1], (tgt - start).normalized(), 0))
        for j in range(4 if detail >= 1 else (3 if detail >= 0.5 else 0)):
            k = R.randint(1, 4); bp = lp[k]
            bt = env(az + R.gauss(0, 0.6), el + R.gauss(0, 0.35), R.uniform(0.92, 1.02))
            bpts = bent(bp, bt, sag * 0.6, 3, wob * 0.25)
            br = [rl[k] * 0.55 * (1 - 0.65 * q / 3) for q in range(4)]
            if detail >= 0.6: tubes.append((bpts, br, 3))
            d = (bt - bp).normalized(); tips.append((bpts[-1], d, 1))
            for q in (1, 2): tips.append((bpts[q] + Vector((R.gauss(0, 0.3), R.gauss(0, 0.3), R.gauss(0, 0.2))), d, 2))
    for k, (pl, rl, sides) in enumerate(tubes):
        tube(f"{name}_b{k}", pl, rl, bark, sides=sides, caps=False)
    mb = CROWN_MB.setdefault(leaves_key, MB())
    def put(q, out, sz, droop=0.0):
        tang = out.cross(Vector((0, 0, 1)))
        if tang.length < 0.1: tang = Vector((1, 0, 0))
        tang.normalize(); bit = out.cross(tang).normalized(); roll = R.uniform(-math.pi, math.pi)
        right = (tang * math.cos(roll) + bit * math.sin(roll)) * sz
        up = (bit * math.cos(roll) - tang * math.sin(roll)) * sz + out * sz * R.uniform(0.2, 0.5)
        if droop:
            right = tang * sz * 0.6; up = Vector((0, 0, -sz * droop)) + out * sz * 0.2
            card(mb, q, right, up, R.choice(QUAD), 0.4, 1.0)
            return
        card(mb, q - up * 0.5, right, up, R.choice(QUAD), 0.35, 1.0)
    for (q, d, depth) in tips:
        for c in range(int(cards_per_tip + R.random())):
            out = ((q - C) * Vector((1 / a_, 1 / a_, 1 / c_))).normalized()
            out = (out + d * 0.5 + Vector((R.gauss(0, 0.45), R.gauss(0, 0.45), R.gauss(0, 0.35)))).normalized()
            put(q, out, card_size * R.uniform(0.75, 1.25))
    for i in range(fill):
        az = R.uniform(0, TWO_PI); el = math.asin(R.uniform(-0.4, 1.0))
        q = env(az, el, R.uniform(0.72, 1.0) ** 0.6)
        out = ((q - C) * Vector((1 / a_, 1 / a_, 1 / c_))).normalized()
        out = (out + Vector((R.gauss(0, 0.4), R.gauss(0, 0.4), R.gauss(0, 0.3)))).normalized()
        put(q, out, card_size * R.uniform(0.7, 1.2))
    for i in range(int(weep)):
        az = R.uniform(0, TWO_PI); el = R.uniform(-0.2, 0.7)
        q = env(az, el, R.uniform(0.85, 1.0))
        out = ((q - C) * Vector((1 / a_, 1 / a_, 0))).normalized()
        put(q, out, card_size * R.uniform(0.8, 1.2), droop=R.uniform(1.6, 2.6))
    CROWNS.append((leaves_key, C, a_, c_))
    if roots and detail >= 1:
        for k in range(5):
            az = TWO_PI * k / 5 + R.uniform(-0.3, 0.3); d = Vector((math.cos(az), math.sin(az), 0))
            p0 = base + Vector((0, 0, r0 * 3.0)); p1 = base + d * r0 * 2.0 + Vector((0, 0, 0.12)); p2 = base + d * r0 * 3.8
            p1.z = max(p1.z, GZ(p1.x, p1.y) + 0.05)
            p2.z = GZ(p2.x, p2.y) - 0.1
            tube(f"{name}_root{k}", [p0, p1, p2], [r0 * 0.6, r0 * 0.4, r0 * 0.1], bark, sides=5)
    return C


def build_crowns(mats, names=None):
    """One swaying card mesh per leaves key, with rounded normals from the nearest crown's centre."""
    out = {}
    for key, mb in CROWN_MB.items():
        o = mb.build((names or {}).get(key, f"Crowns_{key}"), mats[key])
        if o is None: continue
        cs = [(C, a_, c_) for (k2, C, a_, c_) in CROWNS if k2 == key]
        def nfn(p, cs=cs):
            if not cs: return Vector((0, 0, 1))
            C, a_, c_ = min(cs, key=lambda t: (p - t[0]).length)
            return (((p - C) * Vector((1 / a_, 1 / a_, 1 / c_))) + Vector((0, 0, 0.6))).normalized()
        set_card_normals(o, nfn)
        out[key] = o
    return out


# ----------------------------------------------------------------------------- rocks
def rock_bm(bm, centre, size, R, sub=2, bury=0.35, flat=0.7, facet=0.25, yaw=None, squash=(1.0, 0.8, 0.6)):
    """Add a faceted, noise-displaced stone to bm: size (m) = its long radius; squash shapes it; the bottom is sunk
    `bury` of its height into the ground and flattened (no floating)."""
    res = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    vs = res["verts"]
    yaw = R.uniform(0, TWO_PI) if yaw is None else yaw
    Rm = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(R.gauss(0, 0.15), 3, 'X')
    s = R.uniform(0, 100)
    # a few planar cuts give the stone faces (fracture planes)
    planes = [(Vector((R.gauss(0, 1), R.gauss(0, 1), R.gauss(0, 0.6))).normalized(), R.uniform(0.6, 0.85)) for _ in range(5)]
    for v in vs:
        d = v.co.normalized()
        r = 1.0 + 0.22 * noise.noise(d * 1.6 + Vector((s, 0, 0))) + 0.07 * noise.noise(d * 4.5 + Vector((0, s, 0)))
        for (n, off) in planes:
            k = d.dot(n) * r
            if k > off: r -= (k - off) * facet * 3.0
        q = Vector((d.x * squash[0], d.y * squash[1], d.z * squash[2])) * r * size
        v.co = q
    zs = [v.co.z for v in vs]; zmin, zmax = min(zs), max(zs)
    sink = zmin + (zmax - zmin) * bury
    for v in vs:
        if v.co.z < sink: v.co.z = sink - (sink - v.co.z) * (1 - flat)
        v.co = Rm @ v.co
        v.co += Vector(centre) - Vector((0, 0, sink))
    return vs


def rocks(name, specs, mat, sub=2):
    """specs: list of (x, y, size, seed, kw) -> one mesh."""
    bm = bmesh.new()
    for sp in specs:
        x, y, size, seed = sp[:4]; kw = sp[4] if len(sp) > 4 else {}
        R = random.Random(seed)
        rock_bm(bm, (x, y, GZ(x, y)), size, R, sub=kw.pop("sub", sub), **kw)
    me = bpy.data.meshes.new(name); bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat); link(o)
    for p in me.polygons: p.use_smooth = True
    o.modifiers.new("EdgeSplit", 'EDGE_SPLIT').split_angle = math.radians(48)
    return o


# ----------------------------------------------------------------------------- materials
def stone_mat(name, base, dark, light, scale=2.0, wet_z=None, wet_k=0.5, moss=0.0, moss_col=(0.20, 0.24, 0.12), lichen=0.0, rough=0.82, bump=0.35, strata=0.0, cracks=0.6):
    """Weathered stone: tonal mottling, darker cracks (voronoi edges), optional strata, lichen spots, moss on tops,
    wet darkening and gloss below z = wet_z (world)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1800, -500))
    n = noise_(nt, co, scale, 6, 0.62, loc=(-1500, 200))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1300, 200)), c4(K.srgb(base)), c4(K.srgb(light)), (-1100, 200))
    v = voronoi_(nt, co, scale * 1.4, 'DISTANCE_TO_EDGE', (-1500, -100))
    crack = maprange(nt, v.outputs["Distance"], 0.0, 0.05, 1, 0, (-1300, -100))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', crack, cracks, (-1100, -100)), col, c4(K.srgb(dark)), (-900, 200))
    if strata:
        mp = node(nt, "ShaderNodeMapping", (-1500, -300)); mp.inputs["Scale"].default_value = (0.4, 0.4, 6.0); nt.links.new(co, mp.inputs["Vector"])
        st = noise_(nt, mp.outputs["Vector"], 2.0, 3, 0.5, loc=(-1300, -300))
        col = mix_rgb(nt, 'MULTIPLY', strata, col, maprange(nt, st.outputs["Fac"], 0.3, 0.7, 0.75, 1.1, (-1100, -300)), (-800, 200))
    if lichen:
        li = noise_(nt, co, scale * 5, 4, 0.6, loc=(-1300, -450))
        col = mix_rgb(nt, 'MIX', maprange(nt, li.outputs["Fac"], 0.66, 0.72, 0, lichen, (-1100, -450)), col, c4(K.srgb((0.62, 0.60, 0.48))), (-700, 200))
    if moss:
        geo = node(nt, "ShaderNodeNewGeometry", (-1500, -700)); gs = sep_xyz(nt, geo.outputs["Normal"], (-1350, -700))
        mn = noise_(nt, co, scale * 1.5, 4, 0.6, loc=(-1300, -800))
        mk = math_(nt, 'MULTIPLY', maprange(nt, gs.outputs["Z"], 0.4, 0.9, 0, 1, (-1150, -700)), maprange(nt, mn.outputs["Fac"], 0.45, 0.6, 0, moss, (-1150, -800)), (-1000, -750))
        col = mix_rgb(nt, 'MIX', mk, col, c4(K.srgb(moss_col)), (-600, 200))
    rough_s = rough
    if wet_z is not None:
        wz = node(nt, "ShaderNodeNewGeometry", (-1600, -1000)); ws = sep_xyz(nt, wz.outputs["Position"], (-1450, -1000))
        wet = maprange(nt, ws.outputs["Z"], wet_z + 0.12, wet_z - 0.05, 0, 1, (-1300, -1000))
        col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', wet, wet_k, (-1100, -1000)), col, (0.45, 0.43, 0.40, 1), (-500, 200))
        rough_s = mix_f(nt, wet, rough, 0.25, (-500, -500))
    col = K.ao_mul(nt, col, 0.25, 0.45, (-350, -900))
    nt.links.new(col, b.inputs["Base Color"])
    if isinstance(rough_s, float): b.inputs["Roughness"].default_value = rough_s
    else: nt.links.new(rough_s, b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', crack, -0.5, (-700, -1200)), n.outputs["Fac"], (-550, -1200)), bump, 0.02)
    return m


def bark_mat(name, base, dark, light, scale=1.0, fissure=0.6, moss=0.2):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    mp = node(nt, "ShaderNodeMapping", (-1500, 0)); mp.inputs["Scale"].default_value = (3.0 * scale, 3.0 * scale, 0.5 * scale); nt.links.new(co, mp.inputs["Vector"])
    v = voronoi_(nt, mp.outputs["Vector"], 4.0, 'DISTANCE_TO_EDGE', (-1300, 0))
    n = noise_(nt, co, 4.0 * scale, 6, 0.65, loc=(-1300, -250))
    fis = maprange(nt, v.outputs["Distance"], 0.0, 0.12, 1, 0, (-1100, 0))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1100, -250)), c4(K.srgb(base)), c4(K.srgb(light)), (-900, -100))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', fis, fissure, (-900, 100)), col, c4(K.srgb(dark)), (-700, 0))
    if moss:
        mn = noise_(nt, co, 1.5, 4, 0.6, loc=(-1300, -500))
        col = mix_rgb(nt, 'MIX', maprange(nt, mn.outputs["Fac"], 0.6, 0.7, 0, moss, (-1100, -500)), col, c4(K.srgb((0.20, 0.24, 0.12))), (-550, 0))
    col = K.ao_mul(nt, col, 0.3, 0.45, (-400, -700))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.88
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', fis, -1.0, (-600, -900)), math_(nt, 'MULTIPLY', n.outputs["Fac"], 0.4, (-600, -1000)), (-450, -950)), 0.6, 0.02)
    return m


def gradient_sky_mat(name, stops, sun_dir=None, glow=None, clouds=0.0, cloud_col=(0.6, 0.6, 0.65), strength=1.0):
    """Emissive dome colour by elevation (stops: [(el 0-1, linear rgb)]), an optional glow toward sun_dir
    (glow = (rgb, power)), optional soft cloud bands."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-2200, 0), operation='NORMALIZE'); nt.links.new(co, nv.inputs[0]); d = nv.outputs[0]
    s = sep_xyz(nt, d, (-2000, 0)); el = s.outputs["Z"]
    base = ramp(nt, [(p, c4(c)) for p, c in stops], (-1500, 400))
    nt.links.new(maprange(nt, el, -0.1, 1.0, 0, 1, (-1700, 400)), base.inputs["Fac"])
    col = base.outputs["Color"]
    if sun_dir is not None and glow is not None:
        sd = node(nt, "ShaderNodeVectorMath", (-1600, 900), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(Vector(sun_dir).normalized())
        nt.links.new(d, sd.inputs[0])
        g = math_(nt, 'POWER', maprange(nt, sd.outputs["Value"], 0.0, 1.0, 0, 1, (-1450, 900)), glow[1], (-1300, 900))
        col = mix_rgb(nt, 'ADD', g, col, c4(glow[0]), (-900, 600))
    if clouds:
        zk = math_(nt, 'ADD', math_(nt, 'MAXIMUM', el, 0.0, (-1800, -200)), 0.06, (-1650, -200))
        px = math_(nt, 'DIVIDE', s.outputs["X"], zk, (-1500, -150)); py = math_(nt, 'DIVIDE', s.outputs["Y"], zk, (-1500, -300))
        cv = node(nt, "ShaderNodeCombineXYZ", (-1350, -200)); nt.links.new(px, cv.inputs["X"]); nt.links.new(py, cv.inputs["Y"])
        mp = node(nt, "ShaderNodeMapping", (-1200, -200)); mp.inputs["Scale"].default_value = (0.35, 1.2, 1); mp.inputs["Rotation"].default_value = (0, 0, 0.4)
        nt.links.new(cv.outputs[0], mp.inputs["Vector"])
        cl = noise_(nt, mp.outputs["Vector"], 0.8, 6, 0.6, 0.4, (-1000, -200))
        cb = math_(nt, 'MULTIPLY', maprange(nt, cl.outputs["Fac"], 0.5, 0.7, 0, clouds, (-800, -200)), maprange(nt, el, 0.02, 0.2, 0, 1, (-800, -350)), (-650, -250))
        col = mix_rgb(nt, 'MIX', cb, col, c4(cloud_col), (-300, 300))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = strength; b.inputs["Roughness"].default_value = 1.0
    return m


def water_mat(name, deep=(0.02, 0.035, 0.035), rough=0.03, ripple=0.0):
    """Render-time still water (glassy dark, reflective); the export swaps it for the Unity water material."""
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = c4(deep); b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.5; b.inputs["IOR"].default_value = 1.33
    if ripple:
        co = obj_coords(nt)
        n = noise_(nt, co, 3.0, 3, 0.5, loc=(-800, -300))
        bump_from(nt, b, n.outputs["Fac"], ripple, 0.02)
    return m


def water_surface(name, mat, level, inside, extent=60.0, step=1.0, centre=(0.0, 0.0)):
    """A grid of quads at z=level over a square extent; keep faces where inside(x, y) (the pool's outline sits
    under the bank so the edge is hidden). UVs = world/10 (V downstream not needed for still water)."""
    cx, cy = centre
    n = int(extent / step)
    verts = []; idx = {}
    faces = []
    for j in range(n):
        for i in range(n):
            x0, y0 = cx - extent / 2 + i * step, cy - extent / 2 + j * step
            if not inside(x0 + step / 2, y0 + step / 2): continue
            q = []
            for (xx, yy) in ((x0, y0), (x0 + step, y0), (x0 + step, y0 + step), (x0, y0 + step)):
                k = (round(xx, 4), round(yy, 4))
                if k not in idx: idx[k] = len(verts); verts.append((xx, yy, level))
                q.append(idx[k])
            faces.append(tuple(q))
    uvs = [(v[0] / 10.0, v[1] / 10.0) for v in verts]
    o = mesh_from(name, verts, faces, mat, smooth=True, uvs=uvs)
    orient(o, lambda c: (0, 0, 1))
    return o


# ----------------------------------------------------------------------------- cameras and finish
def ring_cams(eye, look_yaw, extra=(), lens=17, pitch=-6.0):
    """Reader view plus left/right/behind/down from the eye. look_yaw: compass degrees (0 = +Y)."""
    E = Vector(eye)
    def at(yaw, pitch_deg, d=10.0):
        a = math.radians(look_yaw + yaw); p = math.radians(pitch_deg)
        return tuple(E + Vector((math.sin(a) * math.cos(p), math.cos(a) * math.cos(p), math.sin(p))) * d)
    cams = [
        camera("Cam_Reader", tuple(E), at(0, pitch), lens=lens),
        camera("Cam_Left", tuple(E), at(-70, pitch), lens=lens),
        camera("Cam_Right", tuple(E), at(70, pitch), lens=lens),
        camera("Cam_Behind", tuple(E), at(180, pitch), lens=lens),
        camera("Cam_Down", tuple(E), at(5, -55), lens=lens),
    ]
    for (nm, loc, look, ln) in extra:
        cams.append(camera(nm, loc, look, lens=ln))
    for c in cams: c.data.clip_end = 1500
    return cams


def page_preview(eye, look_yaw, dist=0.6):
    d = az_dir(look_yaw)
    p = Vector(eye) + d * dist + Vector((0, 0, -0.05))
    o = box("PagePreview", (0.4, 0.004, 0.55), tuple(p), plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9, emission=(0.80, 0.77, 0.69), strength=0.15),
            rot=(0, 0, -math.radians(look_yaw)))
    return o


def reader_anchors(look_yaw, eye=EYE, origin=(0.0, 0.0)):
    x, y = origin; z = GZ(x, y); d = az_dir(look_yaw)
    anchor("reader.entrance", (x, y, z))
    anchor("reader.look", (x + d.x * 2, y + d.y * 2, z + eye))


def check_clear(origin=(0.0, 0.0), look_yaw=0.0, ahead=1.5, around=0.4, zmin=0.08, zmax=2.2, skip=("PagePreview",)):
    """Report mesh vertices in the reader's standing box (0.4 m round, 1.5 m ahead) between zmin and zmax above the
    ground (foliage cards included): the reader must stand on open floor."""
    bpy.context.view_layer.update()
    d = az_dir(look_yaw); side = Vector((d.y, -d.x, 0))
    o0 = Vector((origin[0], origin[1], 0)); bad = {}
    for o in K.COLL.objects:
        if o.type != 'MESH' or o.name in skip: continue
        mw = o.matrix_world
        for v in o.data.vertices:
            p = mw @ v.co; rel = p - o0
            a = rel.dot(d); s = rel.dot(side)
            hz = p.z - GZ(p.x, p.y)
            if not (zmin < hz < zmax): continue
            if (math.hypot(rel.x, rel.y) < around) or (0 <= a <= ahead and abs(s) <= around):
                bad[o.name] = bad.get(o.name, 0) + 1
    print("CLEARANCE", "ok" if not bad else bad, flush=True)
    return bad


def finish(scene_id, gltf_base, cams, keep_names, size_for, keep_uv=(), default_size=(256, 64, 128), page=None, exposure=None,
           default_exposure=0.0, water_colour=None, unlit_emit=()):
    ARGS = K.ARGS
    if not ARGS.nosave:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(K.OUT, f"{gltf_base}_source.blend"))
    K.print_budget(exclude=("PagePreview",))
    if ARGS.render:
        K.render_stills(cams, page=page, page_cams={"Cam_Page"}, exposure=exposure, default_exposure=default_exposure, captures_dir=ARGS.captures)
    if ARGS.bake or ARGS.export:
        # the diffuse-colour bake of a metal is black, and the runtime draws base x light without metalness:
        # bake every material as a dielectric so brass, gold, iron and tin keep their colour
        for m in bpy.data.materials:
            if not m.use_nodes: continue
            for n in m.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    for l in list(n.inputs["Metallic"].links): m.node_tree.links.remove(l)
                    n.inputs["Metallic"].default_value = 0.0
        E8.bake_and_export(f"{gltf_base}.gltf", cams, page=page, keep_names=keep_names, keep_uv=set(keep_uv), size_for=size_for,
                           default_size=default_size, water_colour=water_colour, unlit_emit=unlit_emit)
    print("DONE", flush=True)


# ----------------------------------------------------------------------------- opaque foliage masses (hedges, thickets, far crowns)
def crown_mass_mat(name, dark, mid, light, scale=1.6):
    """opaque foliage mass: leaf clumps as voronoi cells (lit on their upper faces, dark in the gaps), a slow tonal
    drift, darker underneath; a strong clump bump. Colours sRGB."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    warp = noise_(nt, co, 2.0, 2, 0.5, loc=(-1700, 200))
    wv = node(nt, "ShaderNodeVectorMath", (-1550, 200), operation='MULTIPLY_ADD'); wv.inputs[1].default_value = (0.25, 0.25, 0.25)
    nt.links.new(warp.outputs["Color"], wv.inputs[0]); nt.links.new(co, wv.inputs[2])
    v = voronoi_(nt, wv.outputs[0], scale, 'F1', (-1400, 200))
    gap = maprange(nt, v.outputs["Distance"], 0.25, 0.6, 0, 1, (-1200, 200))
    n = noise_(nt, co, 0.15, 3, 0.5, loc=(-1400, -100))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.35, 0.65, 0, 1, (-1200, -100)), c4(K.srgb(mid)), c4(K.srgb(light)), (-1000, 0))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', gap, 0.75, (-1000, 200)), col, c4(K.srgb(dark)), (-800, 0))
    geo = node(nt, "ShaderNodeNewGeometry", (-1400, -400)); gs = sep_xyz(nt, geo.outputs["Normal"], (-1250, -400))
    under = maprange(nt, gs.outputs["Z"], 0.1, -0.7, 0, 0.55, (-1100, -400))
    col = mix_rgb(nt, 'MIX', under, col, c4(K.srgb(dark)), (-600, 0))
    fine = noise_(nt, co, 9.0, 3, 0.6, loc=(-1400, -650))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0.8, 1.12, (-1200, -650)), (-450, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.8
    b.inputs["Specular IOR Level"].default_value = 0.3
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', gap, -1.0, (-700, -800)), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.3, (-700, -900)), (-550, -850)), 0.8, 0.15)
    return m


def lumps(mb, C, a_, c_, n, R, seed, sub=1, sway=(0.15, 0.55), flat_bottom=None, stretch=(1.0, 1.0)):
    """an opaque foliage mass of n noise-displaced icospheres filling an ellipsoid (a_*sx, a_*sy, c_) round C."""
    bm = bmesh.new()
    for k in range(n):
        if k == 0: off = Vector((0, 0, 0)); r = 0.78
        else:
            az = R.uniform(0, TWO_PI); el = R.uniform(-0.35, 0.9)
            off = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * R.uniform(0.35, 0.62); r = R.uniform(0.42, 0.6)
        ctr = C + Vector((off.x * a_ * stretch[0], off.y * a_ * stretch[1], off.z * c_))
        rr = Vector((r * a_ * stretch[0] * R.uniform(0.85, 1.1), r * a_ * stretch[1] * R.uniform(0.85, 1.1), r * c_ * R.uniform(0.85, 1.05)))
        res = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        for v in res["verts"]:
            d = v.co.normalized()
            w = 1.0 + 0.16 * noise.noise(d * 2.2 + Vector((seed * 0.37 + k, k * 1.3, seed * 0.11)))
            q = ctr + Vector((d.x * rr.x, d.y * rr.y, d.z * rr.z)) * w
            if flat_bottom is not None: q.z = max(q.z, flat_bottom)
            v.co = q
    zs = [v.co.z for v in bm.verts]; z0, z1 = min(zs), max(zs)
    vmap = {}
    for v in bm.verts:
        t = (v.co.z - z0) / max(1e-6, z1 - z0)
        vmap[v] = mb.vert(v.co.copy(), (0, 0), sway[0] + (sway[1] - sway[0]) * t)
    for f in bm.faces: mb.face(*[vmap[v] for v in f.verts])
    bm.free()
