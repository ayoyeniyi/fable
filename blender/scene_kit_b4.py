"""
Fable: shared helpers for the chapter step-in rooms built by room builder 4 (docs/SCENE_ROOMS.md):
build_lilliput_binding_ground.py, build_petersburg_street.py, build_walton_ship_deck.py, build_lucas_lodge_drawing_room.py,
build_como_peasant_cot.py, build_new_bedford_dock_street.py, build_forest_road_lion.py, build_blefuscu_shore_boat.py,
build_suez_consulate.py, build_maybury_hill_storm_road.py, build_green_eagle_inn_room.py.

Everything from pride_kit (materials, Canvas, MB, tube, anchors, stills, bake_and_export) is re-exported, plus:

  * setup(): pride_kit.setup with the room's id; stills are copied to captures/blender/<id>/ by default
  * fx(): fx.<kind>.<tag> empties carrying the `radius` custom property (exported with export_extras)
  * painted atlases: grass_atlas(), spray_atlas() (leaf sprays on twigs for tree crowns, hedges and shrubs)
  * tree(): a branching broadleaf tree (flared trunk, limbs, branches, twigs as tubes) with leaf-spray cards at the
    branch ends and through the crown shell; conifer(): a spruce/pine with tiers of needle cards
  * set_card_normals(): rounded foliage normals
  * sky_mat() / sky_dome(): a procedural sky (gradient, sun glow, perspective cloud deck, distant land band)
  * world(): sun + sky fill lights and the world background for the Blender bake
  * polar_terrain(): a ground mesh dense at the reader and coarse far off
  * finish(): transforms, budget, stills (labelled Blender render), bake_and_export (docs/SCENE_ROOMS_PIPELINE.md)

Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       texcoord_obj, wood, noisy, plain, vcol_mat, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, sweep,
                       mesh_from, MB, Frame, anchor, sound, light_obj, camera, smoothstep, lerp, n2, fbm2, link, srgb, ao_mul, add_sway)

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ID = None
EYE = 1.55


def setup(room_id, seed, coll_name, default_samples=48):
    """K.setup for out/<id>; returns ARGS. --captures defaults to captures/blender/<id>."""
    global ID
    ID = room_id
    args = K.setup(room_id, os.path.join(REPO, "out", room_id), seed, coll_name, default_samples=default_samples)
    if not args.captures:
        args.captures = os.path.join(REPO, "captures", "blender", room_id)
    random.seed(seed)
    return args


def fx(kind, tag, loc, radius):
    """fx.<kind>.<tag>: kind fire / candle / torch / lantern; radius in metres (custom property, export_extras)."""
    e = bpy.data.objects.new(f"fx.{kind}.{tag}", None); e.empty_display_type = 'SPHERE'; e.empty_display_size = radius
    e.location = loc; e["radius"] = float(radius); link(e)
    return e


# ----------------------------------------------------------------------------- painted atlases
def blade(cv, x0, y0, length, ang, curve, w0, col_base, col_tip, segs=9):
    """A tapered grass blade from (x0, y0) (pixels, y down), leaning at ang (0 = up), bending by curve."""
    x, y = x0, y0; a = ang
    for i in range(segs):
        t0, t1 = i / segs, (i + 1) / segs
        nx = x + math.sin(a) * length / segs; ny = y - math.cos(a) * length / segs
        col = tuple(cb + (ct - cb) * t1 for cb, ct in zip(col_base, col_tip)) + (1.0,)
        cv.line((x, y), (nx, ny), w0 * (1 - t0 * 0.92), w0 * (1 - t1 * 0.92), col)
        x, y = nx, ny; a += curve / segs * (1 + t0)
    return x, y


GRASS_SHORT = [((c * 256) / 1024, 1 - 256 / 1024, (c * 256 + 256) / 1024, 1.0) for c in range(4)]
GRASS_LONG = [((c * 256) / 1024, 1 - 768 / 1024, (c * 256 + 256) / 1024, 1 - 256 / 1024) for c in range(4)]
GRASS_ROW3 = [((c * 256) / 1024, 0.0, (c * 256 + 256) / 1024, 256 / 1024) for c in range(4)]
QUAD = [(0.0, 0.5, 0.5, 1.0), (0.5, 0.5, 1.0, 1.0), (0.0, 0.0, 0.5, 0.5), (0.5, 0.0, 1.0, 0.5)]


def grass_atlas(name, greens, tips, straw, seed=7, dead_share=0.1, short_len=(90, 235), long_len=(220, 490), row3=None, flowers=None):
    """1024 x 1024 atlas, row 0 (top 256 px): four short tufts (GRASS_SHORT); rows 1-2: four long grasses (GRASS_LONG);
    row 3 (GRASS_ROW3): row3(cv, R, cell_index, x0, base) paints herbs, or more tufts with flowers."""
    S = 1024; cv = Canvas(S, S); R = random.Random(seed)
    for c in range(4):
        x0 = c * 256; base = 252; cv.clip = (x0 + 1, 1, x0 + 255, 256)
        for i in range(70 + c * 8):
            bx = x0 + 128 + R.gauss(0, 30); g = R.choice(greens); t = R.choice(tips)
            if R.random() < dead_share: g, t = R.choice(straw), R.choice(straw)
            L = R.uniform(*short_len)
            blade(cv, bx, base, L, R.gauss(0, 0.32) + (bx - x0 - 128) / 220, R.gauss(0, 0.5), R.uniform(2.6, 4.2), g, t)
    for c in range(4):
        x0 = c * 256; base = 256 + 508; cv.clip = (x0 + 1, 257, x0 + 255, 768)
        for i in range(55):
            bx = x0 + 128 + R.gauss(0, 34); dead = R.random() < dead_share * 1.6
            g = R.choice(straw) if dead else R.choice(greens); t = R.choice(straw) if dead else R.choice(tips)
            L = R.uniform(*long_len); lean = R.gauss(0, 0.28) + (bx - x0 - 128) / 260
            ex, ey = blade(cv, bx, base, L, lean, R.choice((-1, 1)) * R.uniform(0.2, 1.0), R.uniform(3.0, 5.0), g, t, segs=12)
            if R.random() < 0.14:
                for k in range(9):
                    cv.ellipse(ex + R.gauss(0, 4), ey + R.gauss(0, 7) + k * 2.5, 2.0, 6.0, R.gauss(0, 0.3), R.choice(straw) + (1.0,))
    for c in range(4):
        x0 = c * 256; base = 768 + 252; cv.clip = (x0 + 1, 769, x0 + 255, 1024)
        if row3 is not None:
            row3(cv, R, c, x0, base)
            continue
        for i in range(60):
            bx = x0 + 128 + R.gauss(0, 34); g = R.choice(greens); t = R.choice(tips)
            ex, ey = blade(cv, bx, base, R.uniform(80, 220), R.gauss(0, 0.35), R.gauss(0, 0.5), R.uniform(2.6, 4.0), g, t)
            if flowers and R.random() < 0.25:
                fc = R.choice(flowers)
                for k in range(5):
                    cv.ellipse(ex + R.gauss(0, 3), ey + R.gauss(0, 3), 3.2, 2.2, R.uniform(0, 3), fc + (1.0,))
    cv.clip = None; cv.bleed(6)
    return np_image(name, cv.a)


def spray(cv, x0, y0, x1, y1, R, pal, bark=(0.20, 0.17, 0.14), nper=5, size=12.0, shape='ellipse', depth_max=2, branch_p=0.45, flowers=None, flower_p=0.3):
    """A twig spray drawn into the cell: a forked woody stem with leaves along it. shape: ellipse (broadleaf), oak
    (lobed), round (lime/beech), needle (pine/spruce: dense short strokes), palm (frond), bare (no leaves)."""
    W, Hh = x1 - x0, y1 - y0
    stack = [((x0 + W * 0.5 + R.gauss(0, W * 0.05), y1 - 2), R.gauss(0, 0.2), Hh * 0.55, 4.5, 0)]
    leaves = []
    while stack:
        (x, y), a, L, w, depth = stack.pop()
        segs = 5; px, py = x, y
        for s in range(segs):
            a += R.gauss(0, 0.16)
            nx, ny = px + math.sin(a) * L / segs, py - math.cos(a) * L / segs
            nx = min(max(nx, x0 + 6), x1 - 6); ny = min(max(ny, y0 + 6), y1 - 2)
            ww = w * (1 - s / segs * 0.5)
            cv.line((px, py), (nx, ny), ww * 0.5, ww * 0.42, bark + (1.0,))
            if depth >= 1 or s >= 2: leaves.append((nx, ny, a))
            if depth < depth_max and R.random() < branch_p:
                stack.append(((nx, ny), a + R.choice((-1, 1)) * R.uniform(0.45, 0.95), L * R.uniform(0.45, 0.7), w * 0.62, depth + 1))
            px, py = nx, ny
        leaves.append((px, py, a))
    if shape == 'bare':
        for (x, y, a) in leaves:
            for k in range(2):
                b = a + R.choice((-1, 1)) * R.uniform(0.3, 0.8); L = R.uniform(10, 26)
                cv.line((x, y), (x + math.sin(b) * L, y - math.cos(b) * L), 0.9, 0.5, bark + (1.0,))
        return
    for (x, y, a) in leaves:
        for k in range(nper):
            if shape == 'needle':
                b = a + R.choice((-1, 1)) * R.uniform(0.6, 1.3); L = size * R.uniform(0.8, 1.3)
                col = R.choice(pal); sh = R.uniform(0.8, 1.15)
                cv.line((x, y), (x + math.sin(b) * L, y - math.cos(b) * L), 1.6, 0.8, (col[0] * sh, col[1] * sh, col[2] * sh, 1.0))
                continue
            b = a + R.gauss(0, 1.1); d = R.uniform(2, size * 1.4)
            lx, ly = x + math.sin(b) * d, y - math.cos(b) * d
            if not (x0 + 4 < lx < x1 - 4 and y0 + 4 < ly < y1 - 4): continue
            col = R.choice(pal); sh = R.uniform(0.8, 1.15); col = (col[0] * sh, col[1] * sh, col[2] * sh)
            s = size * R.uniform(0.7, 1.25)
            if shape == 'oak':
                cv.ellipse(lx, ly, s * 0.42, s, b, col + (1.0,), tip=0.3)
                for j in range(3):
                    t = (j - 1) * 0.42
                    ox, oy = lx + math.sin(b) * s * t, ly - math.cos(b) * s * t
                    for sg in (-1, 1):
                        cv.ellipse(ox + math.cos(b) * sg * s * 0.36, oy + math.sin(b) * sg * s * 0.36, s * 0.24, s * 0.2, b, col + (1.0,))
            elif shape == 'round':
                cv.ellipse(lx, ly, s * 0.62, s * 0.7, b, col + (1.0,), tip=0.25)
            elif shape == 'long':      # sweet chestnut: long, narrow, toothed
                cv.ellipse(lx, ly, s * 0.26, s * 1.15, b, col + (1.0,), tip=0.5)
                for j in range(5):
                    t = (j - 2) * 0.38
                    ox, oy = lx + math.sin(b) * s * t, ly - math.cos(b) * s * t
                    for sg in (-1, 1):
                        cv.ellipse(ox + math.cos(b) * sg * s * 0.25, oy + math.sin(b) * sg * s * 0.25, s * 0.05, s * 0.09, b + sg * 0.6, col + (1.0,))
            elif shape == 'palm':
                cv.ellipse(lx, ly, s * 0.18, s * 1.1, b, col + (1.0,), tip=0.6)
            else:
                cv.ellipse(lx, ly, s * 0.45, s * 0.85, b, col + (1.0,), tip=0.45)
            # a darker midrib for the near reading
            cv.line((lx - math.sin(b) * s * 0.6, ly + math.cos(b) * s * 0.6), (lx + math.sin(b) * s * 0.5, ly - math.cos(b) * s * 0.5), 0.6, 0.3,
                    (col[0] * 0.72, col[1] * 0.72, col[2] * 0.66, 1.0))
        if flowers and R.random() < flower_p:   # a five-petalled flower (wild rose, bramble) at the shoot
            fc = R.choice(flowers); fr = size * R.uniform(0.45, 0.65)
            for k in range(5):
                a = 2 * math.pi * k / 5 + R.uniform(0, 0.3)
                cv.ellipse(x + math.cos(a) * fr * 0.55, y + math.sin(a) * fr * 0.55, fr * 0.5, fr * 0.42, a, fc + (1.0,))
            cv.ellipse(x, y, fr * 0.25, fr * 0.25, 0, (0.85, 0.72, 0.25, 1.0))


def spray_atlas(name, pal, seed, S=1024, per_cell=3, **kw):
    """Four sprays (2 x 2 cells, QUAD) on a transparent atlas, colour bled into the transparent texels."""
    cv = Canvas(S, S); R = random.Random(seed); h = S // 2
    for (cx, cy) in ((0, 0), (h, 0), (0, h), (h, h)):
        cv.clip = (cx + 1, cy + 1, cx + h - 1, cy + h - 1)
        for k in range(per_cell):
            spray(cv, cx + 4, cy + 4, cx + h - 4, cy + h - 4, R, pal, **kw)
    cv.clip = None; cv.bleed(6)
    return np_image(name, cv.a)


# ----------------------------------------------------------------------------- card helpers
def set_card_normals(o, fn):
    """Custom normals for foliage cards: fn(position) -> the normal to shade with (rounded, volumetric)."""
    if o is None: return
    me = o.data
    me.normals_split_custom_set_from_vertices([tuple(fn(v.co)) for v in me.vertices])


def card(mb, base, right, up, cell, sway0, sway1, bend=None, segs=1):
    """An atlas card from base (bottom centre) spanning right (full width) and up; cell = (u0, v0, u1, v1)."""
    base = Vector(base); right = Vector(right); up = Vector(up)
    u0, v0, u1, v1 = cell
    rows = []
    for k in range(segs + 1):
        t = k / segs
        off = up * t + (bend * (t * t) if bend is not None else Vector())
        sw = sway0 + (sway1 - sway0) * t
        rows.append((mb.vert(base - right * 0.5 + off, (u0, v0 + (v1 - v0) * t), sw), mb.vert(base + right * 0.5 + off, (u1, v0 + (v1 - v0) * t), sw)))
    for k in range(segs):
        a, b_ = rows[k]; c, d = rows[k + 1]
        mb.face(a, b_, d, c)


# ----------------------------------------------------------------------------- trees
def bark_mat(name, base=(0.17, 0.16, 0.14), dark=(0.07, 0.065, 0.06), light=(0.30, 0.29, 0.26), fissure=True, green=0.25, scale=1.0):
    """Bark: fissured (oak, elm) or smoother, darker in the cracks, with a little algae on one side."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    mp = node(nt, "ShaderNodeMapping", (-1500, 0)); mp.inputs["Scale"].default_value = (3.0 * scale, 3.0 * scale, 0.7 * scale); nt.links.new(co, mp.inputs["Vector"])
    if fissure:
        v = voronoi_(nt, mp.outputs["Vector"], 4.5, 'DISTANCE_TO_EDGE', (-1200, 0))
        h = maprange(nt, v.outputs["Distance"], 0.0, 0.18, 0, 1, (-950, 0), 'SMOOTHSTEP')
    else:
        v = noise_(nt, mp.outputs["Vector"], 9.0, 6, 0.6, loc=(-1200, 0)); h = maprange(nt, v.outputs["Fac"], 0.35, 0.65, 0, 1, (-950, 0))
    nn = noise_(nt, co, 2.0, 4, 0.6, loc=(-1200, 300))
    cr = ramp(nt, [(0.0, c4(dark)), (0.45, c4(base)), (1.0, c4(light))], (-750, 200))
    nt.links.new(math_(nt, 'MULTIPLY', h, maprange(nt, nn.outputs["Fac"], 0.3, 0.7, 0.7, 1.15, (-900, 300)), (-850, 150)), cr.inputs["Fac"])
    col = cr.outputs["Color"]
    nrm = node(nt, "ShaderNodeNewGeometry", (-1300, -900)); sn = sep_xyz(nt, nrm.outputs["Normal"], (-1100, -900))
    alg = math_(nt, 'MULTIPLY', maprange(nt, sn.outputs["X"], 0.1, -0.8, 0, 1, (-900, -900)),
                maprange(nt, noise_(nt, co, 1.5, 3, 0.6, loc=(-1100, -1100)).outputs["Fac"], 0.4, 0.62, 0, green, (-900, -1100)), (-700, -950))
    col = mix_rgb(nt, 'MIX', alg, col, (0.16, 0.22, 0.07, 1), (-400, 200))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, h, 0, 1, 0.85, 0.6, (-300, -200)), b.inputs["Roughness"])
    bump_from(nt, b, h, 0.6, 0.02, (0, -400))
    return m


def tree(name, base, height, spread, kind, seed, bark, leaves_mat, nlimbs=6, detail=1.0, cards_per_tip=2, card_size=1.3, lean=(0, 0),
         dense=1.0, fill=0, shape=None):
    """A broadleaf tree grown to an ellipsoid crown envelope: a flared trunk, limbs from the top of the trunk reaching
    to the envelope (oak sags, others sweep up), branches off each limb, twigs on near trees (detail >= 1). Atlas
    cards (QUAD cells of leaves_mat) at the branch ends and through the shell (fill), facing outwards so the crown
    reads as a volume with a broken edge. kind: oak, ash, maple, elm, lime, birch, olive, palm-less broadleaf ('broad').
    Returns (tips, crown centre)."""
    R = random.Random(seed)
    base = Vector(base) - Vector((0, 0, 0.15))
    shape = shape or {"oak": (0.34, 1.0, 0.36), "ash": (0.36, 0.85, 0.40), "maple": (0.30, 0.95, 0.40), "elm": (0.28, 0.75, 0.45),
                      "lime": (0.30, 0.8, 0.45), "birch": (0.35, 0.6, 0.45), "olive": (0.35, 1.1, 0.30), "broad": (0.32, 0.95, 0.40)}[kind]
    trunk_h = height * shape[0]
    a_ = spread * shape[1]; c_ = (height - trunk_h) * 0.5
    C = base + Vector((lean[0], lean[1], trunk_h + c_ * 0.95))
    r0 = height * {"oak": 0.042, "ash": 0.028, "maple": 0.03, "elm": 0.03, "lime": 0.032, "birch": 0.02, "olive": 0.05, "broad": 0.032}[kind]

    def env(az, el, k=1.0):
        return C + Vector((math.cos(az) * math.cos(el) * a_ * (1 + 0.12 * R.gauss(0, 1)), math.sin(az) * math.cos(el) * a_ * (1 + 0.12 * R.gauss(0, 1)),
                           math.sin(el) * c_)) * k
    tubes = []; tips = []
    top = base + Vector((lean[0], lean[1], trunk_h))
    tp = [base + (top - base) * t + Vector((R.gauss(0, 0.05), R.gauss(0, 0.05), 0)) * float(t > 0) for t in (0, 0.12, 0.3, 0.65, 1.0)]
    if detail < 0.6: tp = [tp[0], tp[2], tp[4]]
    tubes.append((tp, [r0 * 1.75, r0 * 1.2, r0 * 1.05, r0, r0 * 0.9] if detail >= 0.6 else [r0 * 1.6, r0 * 1.05, r0 * 0.9], 9 if detail >= 1 else (6 if detail >= 0.6 else 5)))

    def bent(p0, p1, sag, n, wob):
        pts = []
        for i in range(n + 1):
            t = i / n; q = p0.lerp(p1, t)
            q.z -= sag * math.sin(math.pi * t) * (p1 - p0).length
            if 0 < i < n: q += Vector((R.gauss(0, wob), R.gauss(0, wob), R.gauss(0, wob)))
            pts.append(q)
        return pts
    sag = {"oak": 0.10, "ash": -0.06, "maple": 0.0, "elm": -0.05, "lime": -0.02, "birch": 0.06, "olive": 0.04, "broad": 0.0}[kind]
    wob = {"oak": 0.18, "ash": 0.08, "maple": 0.08, "elm": 0.10, "lime": 0.07, "birch": 0.06, "olive": 0.2, "broad": 0.1}[kind]
    for i in range(nlimbs):
        az = 2 * math.pi * (i + R.uniform(-0.3, 0.3)) / nlimbs
        el = R.uniform(0.05, 0.75) if kind in ("oak", "olive") else R.uniform(0.35, 1.1)
        start = tp[-1] if i % 3 else tp[-2].lerp(tp[-1], 0.6)
        tgt = env(az, el, 0.78)
        nseg = 4 if detail >= 0.6 else 2
        lp = bent(start, tgt, sag, nseg, wob * spread * 0.08)
        rl = [r0 * 0.62 * (1 - 0.6 * k / nseg) for k in range(nseg + 1)]
        tubes.append((lp, rl, 6 if detail >= 1 else (4 if detail >= 0.6 else 3)))
        tips.append((lp[-1], (tgt - start).normalized(), 0))
        nb = 4 if detail >= 1 else (3 if detail >= 0.6 else 2)
        for j in range(nb):
            k = R.randint(1, nseg); bp = lp[k]
            bt = env(az + R.gauss(0, 0.6), el + R.gauss(0, 0.35), R.uniform(0.92, 1.02))
            bpts = bent(bp, bt, sag * 0.6, 3, wob * 0.25)
            br = [rl[k] * 0.55 * (1 - 0.65 * q / 3) for q in range(4)]
            if detail >= 0.6: tubes.append((bpts, br, 4 if detail >= 1 else 3))
            d = (bt - bp).normalized(); tips.append((bpts[-1], d, 1))
            for q in (1, 2):
                tips.append((bpts[q] + Vector((R.gauss(0, 0.3), R.gauss(0, 0.3), R.gauss(0, 0.2))), d, 2))
            if detail >= 1:
                for t_ in range(2):
                    tw0 = bpts[R.randint(1, 3)]
                    tw1 = tw0 + (d + Vector((R.gauss(0, 0.6), R.gauss(0, 0.6), R.gauss(0, 0.4) + (0.4 if kind != "oak" else 0)))).normalized() * R.uniform(0.6, 1.3) * spread / 5
                    tubes.append(([tw0, tw0.lerp(tw1, 0.5), tw1], [br[1] * 0.5, br[1] * 0.3, 0.004], 3))
                    tips.append((tw1, d, 3))
    if detail >= 1:
        tubes.append((bent(tp[-1], C + Vector((0, 0, c_ * 0.85)), 0.0, 3, 0.1), [r0 * 0.5, r0 * 0.35, r0 * 0.2, 0.02], 5))
    bm_objs = []
    for k, (pl, rl, sides) in enumerate(tubes):
        bm_objs.append(tube(f"{name}_b{k}", pl, rl, bark, sides=sides, caps=False))
    mb = MB()

    def put(q, out, sz):
        tang = out.cross(Vector((0, 0, 1)))
        if tang.length < 0.1: tang = Vector((1, 0, 0))
        tang.normalize(); bit = out.cross(tang).normalized(); roll = R.uniform(-math.pi, math.pi)
        right = (tang * math.cos(roll) + bit * math.sin(roll)) * sz
        up = (bit * math.cos(roll) - tang * math.sin(roll)) * sz + out * sz * R.uniform(0.2, 0.5)
        card(mb, q - up * 0.5, right, up, R.choice(QUAD), 0.35, 1.0)
    for (q, d, depth) in tips:
        for c in range(int(cards_per_tip * dense + R.random())):
            out = ((q - C) * Vector((1 / a_, 1 / a_, 1 / c_))).normalized()
            out = (out + d * 0.5 + Vector((R.gauss(0, 0.45), R.gauss(0, 0.45), R.gauss(0, 0.35)))).normalized()
            put(q, out, card_size * R.uniform(0.75, 1.25))
    for i in range(fill):
        az = R.uniform(0, 2 * math.pi); el = math.asin(R.uniform(-0.45, 1.0))
        q = env(az, el, R.uniform(0.72, 1.0) ** 0.6)
        out = ((q - C) * Vector((1 / a_, 1 / a_, 1 / c_))).normalized()
        out = (out + Vector((R.gauss(0, 0.4), R.gauss(0, 0.4), R.gauss(0, 0.3)))).normalized()
        put(q, out, card_size * R.uniform(0.7, 1.2))
    crown = mb.build(f"{name}_crown", leaves_mat)
    if crown is not None:
        set_card_normals(crown, lambda p: (((p - C) * Vector((1 / a_, 1 / a_, 1 / c_))) + Vector((0, 0, 0.6))).normalized()
                         if (p - C).length > 0.01 else Vector((0, 0, 1)))
    return tips, C


def conifer(name, base, height, seed, bark, needles_mat, radius=None, tiers=9, per_tier=7, card_k=1.0, droop=0.25):
    """A spruce/pine: a straight tapering trunk and whorls of drooping branch cards (needle sprays), widest low down."""
    R = random.Random(seed); base = Vector(base) - Vector((0, 0, 0.2))
    radius = radius or height * 0.22
    tube(name + "_t", [base, base + Vector((0, 0, height * 0.5)), base + Vector((R.gauss(0, 0.05), R.gauss(0, 0.05), height))],
         [height * 0.018 + 0.05, height * 0.011, 0.02], bark, sides=7, caps=False)
    mb = MB()
    for t in range(tiers):
        f = (t + 0.5) / tiers; z = base.z + height * (0.18 + 0.8 * f)
        rad = radius * (1 - f) ** 0.9 + 0.15
        n = max(3, int(per_tier * (1 - f * 0.5)))
        for k in range(n):
            a = 2 * math.pi * (k + R.uniform(-0.3, 0.3)) / n + t * 0.7
            d = Vector((math.cos(a), math.sin(a), 0))
            root = Vector((base.x, base.y, z))
            right = Vector((-d.y, d.x, 0)) * rad * 0.9 * card_k
            up = d * rad * 1.05 + Vector((0, 0, -rad * droop + R.gauss(0, 0.05)))
            card(mb, root - d * rad * 0.05, right, up, R.choice(QUAD), 0.1, 1.0, bend=Vector((0, 0, -rad * droop * 0.6)), segs=2)
    o = mb.build(name + "_crown", needles_mat)
    set_card_normals(o, lambda p: (Vector((p.x - base.x, p.y - base.y, 0)).normalized() * 0.8 + Vector((0, 0, 0.6))).normalized()
                     if math.hypot(p.x - base.x, p.y - base.y) > 0.01 else Vector((0, 0, 1)))
    return o


# ----------------------------------------------------------------------------- sky and light
def sky_mat(name="M_SkyDome", zenith=(0.20, 0.36, 0.66), horizon=(0.70, 0.78, 0.86), ground=(0.30, 0.31, 0.28), sun_dir=(0.5, 0.5, 0.5),
            glow=(1.0, 0.92, 0.78), glow_k=0.5, glow_pow=6.0, disc=True, clouds=0.35, cloud_col=(0.95, 0.95, 0.96), cloud_dark=(0.62, 0.65, 0.70),
            cloud_scale=1.0, land=None, land_h=0.02, strength=1.0, stars=False, land_detail=0.6, land_scale=2.2):
    """A procedural sky for the dome (emission only). clouds: 0 clear .. 1 overcast; land: colour of a distant land band
    along the horizon (None = no band)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-2200, 0), operation='NORMALIZE'); nt.links.new(co, nv.inputs[0]); d = nv.outputs[0]
    s = sep_xyz(nt, d, (-2000, 0)); el = s.outputs["Z"]
    base = ramp(nt, [(0.0, c4(ground)), (0.095, c4(horizon)), (0.2, c4(tuple(h * 0.8 + z * 0.2 for h, z in zip(horizon, zenith)))), (0.55, c4(zenith)), (1.0, c4(zenith))], (-1500, 400))
    nt.links.new(maprange(nt, el, -0.1, 1.0, 0, 1, (-1700, 400)), base.inputs["Fac"])
    col = base.outputs["Color"]
    sd = node(nt, "ShaderNodeVectorMath", (-1700, 800), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(Vector(sun_dir).normalized()); nt.links.new(d, sd.inputs[0])
    gl = math_(nt, 'POWER', maprange(nt, sd.outputs["Value"], 0.0, 1.0, 0, 1, (-1500, 800)), glow_pow, (-1350, 800))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', gl, glow_k, (-1200, 850)), col, c4(glow), (-1000, 400))
    if disc:
        dk = maprange(nt, sd.outputs["Value"], 0.9993, 0.9997, 0, 1, (-1300, 1000))
        col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', dk, 6.0, (-1150, 1000)), col, c4(glow), (-900, 500))
    if clouds > 0:
        zk = math_(nt, 'ADD', math_(nt, 'MAXIMUM', el, 0.0, (-1800, -200)), 0.08, (-1650, -200))
        px = math_(nt, 'DIVIDE', s.outputs["X"], zk, (-1500, -150)); py = math_(nt, 'DIVIDE', s.outputs["Y"], zk, (-1500, -300))
        cvx = node(nt, "ShaderNodeCombineXYZ", (-1350, -200)); nt.links.new(px, cvx.inputs["X"]); nt.links.new(py, cvx.inputs["Y"])
        mp = node(nt, "ShaderNodeMapping", (-1200, -200)); mp.inputs["Scale"].default_value = (0.5 * cloud_scale, 0.8 * cloud_scale, 1); mp.inputs["Location"].default_value = (3.3, 1.7, 0.2)
        nt.links.new(cvx.outputs[0], mp.inputs["Vector"])
        n1 = noise_(nt, mp.outputs["Vector"], 0.9, 8, 0.62, 0.3, (-1000, -100))
        n2_ = noise_(nt, mp.outputs["Vector"], 3.5, 5, 0.6, loc=(-1000, -350))
        dens = math_(nt, 'ADD', n1.outputs["Fac"], math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.25, (-800, -350)), (-650, -200))
        lo = 0.75 - 0.42 * clouds
        cov = maprange(nt, dens, lo, lo + 0.22, 0, 1, (-450, -250), 'SMOOTHSTEP')
        shade = maprange(nt, n2_.outputs["Fac"], 0.35, 0.7, 0, 1, (-450, -450))
        ccol = mix_rgb(nt, 'MIX', shade, c4(cloud_dark), c4(cloud_col), (-250, -400))
        ccol = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', gl, glow_k * 0.6, (-300, -700)), ccol, c4(glow), (-100, -450))
        fade = maprange(nt, el, 0.0, 0.18, 0.25, 1.0, (-400, -650))
        col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', cov, fade, (-200, -600)), col, ccol, (100, 400))
    if stars:
        st = voronoi_(nt, d, 220.0, 'F1', (-1000, -900))
        sp = maprange(nt, st.outputs["Distance"], 0.06, 0.0, 0, 1, (-800, -900))
        sp = math_(nt, 'MULTIPLY', math_(nt, 'POWER', sp, 6.0, (-650, -900)), maprange(nt, el, 0.05, 0.3, 0, 0.8, (-650, -1050)), (-500, -950))
        col = mix_rgb(nt, 'ADD', sp, col, (0.9, 0.92, 1.0, 1), (250, 300))
    if land is not None:
        az = math_(nt, 'ARCTAN2', s.outputs["X"], s.outputs["Y"], (-1800, -1200))
        azv = node(nt, "ShaderNodeCombineXYZ", (-1650, -1200)); nt.links.new(math_(nt, 'COSINE', az, None, (-1700, -1300)), azv.inputs["X"]); nt.links.new(math_(nt, 'SINE', az, None, (-1700, -1400)), azv.inputs["Y"])
        hn = noise_(nt, azv.outputs[0], land_scale, 4, 0.5, loc=(-1500, -1200)); tn = noise_(nt, azv.outputs[0], 24.0, 4, 0.7, loc=(-1500, -1450))
        hill = math_(nt, 'ADD', math_(nt, 'MULTIPLY', hn.outputs["Fac"], land_h * 1.6, (-1300, -1200)),
                     math_(nt, 'MULTIPLY', maprange(nt, tn.outputs["Fac"], 0.35, 0.65, 0, 1, (-1300, -1450)), land_h * land_detail, (-1150, -1450)), (-1000, -1300))
        hill = math_(nt, 'SUBTRACT', hill, land_h * 0.5, (-900, -1300))
        lmask = maprange(nt, math_(nt, 'SUBTRACT', hill, el, (-650, -1300)), 0.0, 0.0015, 0, 1, (-500, -1300))
        col = mix_rgb(nt, 'MIX', lmask, col, c4(land), (300, 200))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = strength; b.inputs["Roughness"].default_value = 1.0
    return m


def sky_dome(mat, name="SkyDome", radius=400.0, seg=48, rings=16, el_min=-12.0, centre=(0, 0, 0)):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rows = []
    cx, cy, cz = centre
    for j in range(rings + 1):
        e = math.radians(el_min + (90.0 - el_min) * (j / rings))
        rows.append([bm.verts.new((cx + radius * math.cos(e) * math.sin(2 * math.pi * i / seg), cy + radius * math.cos(e) * math.cos(2 * math.pi * i / seg),
                                   cz + radius * math.sin(e))) for i in range(seg)])
    for j in range(rings):
        for i in range(seg):
            i2 = (i + 1) % seg
            f = bm.faces.new((rows[j][i], rows[j + 1][i], rows[j + 1][i2], rows[j][i2]))
            for l, (uu, vv) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                l[uvl].uv = (uu / seg, vv / rings)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    o.visible_diffuse = False; o.visible_glossy = True; o.visible_shadow = False; o.visible_transmission = False
    return link(o)


def world(sun_dir, sun_energy=3.0, sun_col=(1.0, 0.95, 0.86), sun_angle=1.0, sky_cols=((0.16, 0.15, 0.12), (0.62, 0.70, 0.82), (0.32, 0.46, 0.72)),
          sky_strength=1.0, fill=0.0, fill_col=(0.8, 0.86, 0.95), haze=0.0, haze_col=(0.8, 0.82, 0.85)):
    """light.sun (SUN toward -sun_dir), an optional shadowless light.sky fill, and a world background graded by
    elevation (ground, horizon, zenith) that lights the Blender render and bake."""
    sd = Vector(sun_dir).normalized()
    sun = None
    if sun_energy > 0:
        sun = light_obj("light.sun", 'SUN', sun_energy, sun_col, tuple(sd * 40), direction=-sd, angle=math.radians(sun_angle))
    if fill > 0:
        sl = light_obj("light.sky", 'SUN', fill, fill_col, (0, 0, 30), direction=(0.15, -0.1, -1.0), angle=math.radians(90))
        sl.data.use_shadow = False
    w = bpy.data.worlds.new("World"); K.scene.world = w; w.use_nodes = True
    wnt = w.node_tree; bg = wnt.nodes["Background"]
    wtc = wnt.nodes.new("ShaderNodeTexCoord"); wsep = wnt.nodes.new("ShaderNodeSeparateXYZ"); wnt.links.new(wtc.outputs["Generated"], wsep.inputs["Vector"])
    wmr = wnt.nodes.new("ShaderNodeMapRange"); wmr.inputs["From Min"].default_value = -0.1; wmr.inputs["From Max"].default_value = 1.0
    wnt.links.new(wsep.outputs["Z"], wmr.inputs["Value"])
    g, hz, zn = sky_cols
    wr = ramp(wnt, [(0.0, c4(g)), (0.09, c4(hz)), (0.45, c4(zn)), (1.0, c4(zn))])
    wnt.links.new(wmr.outputs["Result"], wr.inputs["Fac"]); wnt.links.new(wr.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = sky_strength
    if haze > 0:
        vol = wnt.nodes.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = haze; vol.inputs["Color"].default_value = c4(haze_col)
        wnt.links.new(vol.outputs[0], wnt.nodes["World Output"].inputs["Volume"])
    return sun


# ----------------------------------------------------------------------------- terrain
def polar_terrain(name, fn, mat, r_max=120.0, r0=0.25, rings=60, seg=96, centre=(0.0, 0.0), uv_scale=None, r_min=0.0, uv_disc=False):
    """A ground mesh in rings around centre whose spacing grows geometrically (fine at the reader's feet, coarse far
    off); z = fn(x, y). UVs are planar world x, y (divided by uv_scale when given)."""
    cx, cy = centre
    radii = [r_min] if r_min > 0 else [0.0]
    q = (r_max / r0) ** (1.0 / (rings - 1))
    r = r0
    while r < r_max:
        if r > radii[-1] + 1e-4: radii.append(r)
        r *= q
    radii.append(r_max)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rows = []
    for rr in radii:
        if rr == 0.0:
            rows.append([bm.verts.new((cx, cy, fn(cx, cy)))]); continue
        rows.append([bm.verts.new((cx + rr * math.cos(2 * math.pi * i / seg), cy + rr * math.sin(2 * math.pi * i / seg),
                                   fn(cx + rr * math.cos(2 * math.pi * i / seg), cy + rr * math.sin(2 * math.pi * i / seg)))) for i in range(seg)])
    for j in range(len(rows) - 1):
        a, b_ = rows[j], rows[j + 1]
        for i in range(seg):
            i2 = (i + 1) % seg
            if len(a) == 1: bm.faces.new((a[0], b_[i], b_[i2]))
            else: bm.faces.new((a[i], b_[i], b_[i2], a[i2]))
    us = uv_scale or 1.0
    for f in bm.faces:
        for l in f.loops:
            if uv_disc: l[uvl].uv = ((l.vert.co.x - cx) / (2 * r_max) + 0.5, (l.vert.co.y - cy) / (2 * r_max) + 0.5)
            else: l[uvl].uv = (l.vert.co.x / us, l.vert.co.y / us)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)


def grid_mesh(name, fn, mat, x0, x1, y0, y1, nx, ny):
    """A height grid (z = fn(x, y)) over a rectangle, UVs in world metres."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    vs = [[bm.verts.new((x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, fn(x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny)))
           for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for l in f.loops: l[uvl].uv = (l.vert.co.x, l.vert.co.y)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)


# ----------------------------------------------------------------------------- reader, cameras, finish
def reader(entrance, yaw_deg, eye=EYE):
    """anchor.reader.entrance at the feet, anchor.reader.look 2 m ahead at eye height (yaw 0 = +Y, 90 = +X)."""
    e = Vector(entrance)
    a = math.radians(yaw_deg)
    d = Vector((math.sin(a), math.cos(a), 0))
    anchor("reader.entrance", tuple(e))
    anchor("reader.look", tuple(e + d * 2.0 + Vector((0, 0, eye))))
    return e + Vector((0, 0, eye)), d


def view_cams(eye, yaw_deg, extra=(), lens=17, dz=-0.12):
    """Cam_Reader (the reader's view), Cam_Left / Cam_Right (75 degrees round), Cam_Behind, Cam_Down; extra =
    [(name, loc, look_at, lens)]."""
    def at(deg, pitch=dz):
        a = math.radians(yaw_deg + deg); return tuple(Vector(eye) + Vector((math.sin(a), math.cos(a), pitch)) * 10)
    cams = [camera("Cam_Reader", tuple(eye), at(0), lens=lens),
            camera("Cam_Left", tuple(eye), at(-75), lens=lens),
            camera("Cam_Right", tuple(eye), at(75), lens=lens),
            camera("Cam_Behind", tuple(eye), at(180), lens=lens),
            camera("Cam_Down", tuple(eye), at(0, -0.75), lens=lens)]
    for (n, loc, look, ln) in extra:
        cams.append(camera(n, tuple(loc), tuple(look), lens=ln))
    for c in cams: c.data.clip_end = 1500.0
    return cams


def page_preview(eye, d):
    """The reading page placeholder (render only, never exported): 0.6 m ahead, 0.4 x 0.55 m."""
    p = Vector(eye) + Vector(d) * 0.6 - Vector((0, 0, 0.05))
    o = box("PagePreview", (0.4, 0.004, 0.55), tuple(p), plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9), rot=(0, 0, math.atan2(-d[0], d[1])))
    return o


def finish(args, cams, gltf_name, keep_names=None, keep_uv=(), size_for=None, default_size=(512, 128, 256), exposure=None,
           default_exposure=0.0, page=None, no_shadow=(), unlit_emit=(), render_only=()):
    K.apply_transforms()
    for o in K.COLL.objects:
        if o.type == 'MESH' and o.data.materials and o.data.materials[0].name in no_shadow: o.visible_shadow = False
    if not args.nosave:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(K.OUT, gltf_name.replace(".gltf", "_source.blend")))
    tris = K.print_budget(exclude=("PagePreview",) + tuple(o.name for o in render_only))
    if args.render:
        K.render_stills(cams, page=page, page_cams={"Cam_Page"}, exposure=exposure, default_exposure=default_exposure, captures_dir=args.captures)
    if args.bake or args.export:
        for o in render_only:
            if o.name in bpy.data.objects: bpy.data.objects.remove(o)
        keep = {"M_SkyDome": "SkyDome"}; keep.update(keep_names or {})
        K.bake_and_export(gltf_name, cams, page=page, keep_names=keep, keep_uv=set(keep_uv) | {"M_SkyDome"}, size_for=size_for or {},
                          default_size=default_size, unlit_emit=unlit_emit)
        # living-scene empties carry custom properties (fx radius): re-export with extras on
        gl = os.path.join(K.OUT, gltf_name)
        bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                                  export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=88, export_lights=True,
                                  export_cameras=False, export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_extras=True)
        K.patch_sun_intensities(gl)
    print("DONE tris", tris, flush=True)
    return tris


# ----------------------------------------------------------------------------- many small boxes in one mesh
def mb_box(mb, c, size, yaw=0.0, tilt=(0.0, 0.0), skip=()):
    """An axis box (centre c, full size sx, sy, sz) turned by yaw about Z (and small tilts about X, Y) into an MB;
    UVs are the faces' metric extents (for image or planar materials)."""
    sx, sy, sz = size; c = Vector(c)
    R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(tilt[1], 3, 'Y') @ Matrix.Rotation(tilt[0], 3, 'X')
    P = [c + R @ Vector((x * sx / 2, y * sy / 2, z * sz / 2)) for z in (-1, 1) for y in (-1, 1) for x in (-1, 1)]
    faces = [((0, 2, 3, 1), (sx, sy)), ((4, 5, 7, 6), (sx, sy)), ((0, 1, 5, 4), (sx, sz)), ((2, 6, 7, 3), (sx, sz)),
             ((0, 4, 6, 2), (sy, sz)), ((1, 3, 7, 5), (sy, sz))]
    for fi, (idx, (w, hh)) in enumerate(faces):
        if fi in skip: continue    # 0 bottom, 1 top, 2 -y, 3 +y, 4 -x, 5 +x
        uvs = ((0, 0), (w, 0), (w, hh), (0, hh))
        vs = [mb.vert(P[i], uv) for i, uv in zip(idx, uvs)]
        mb.face(*vs)


def mb_quad(mb, corners, uvs=((0, 0), (1, 0), (1, 1), (0, 1)), sway=(0, 0, 0, 0)):
    vs = [mb.vert(Vector(p), uv, w) for p, uv, w in zip(corners, uvs, sway)]
    mb.face(*vs)


def text_mesh(name, txt, loc, size, mat, rot=(math.pi / 2, 0, 0), extrude=0.004, align='CENTER'):
    """A line of raised letters (Blender's built-in font) converted to a mesh."""
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = txt; cu.size = size; cu.extrude = extrude; cu.align_x = align; cu.align_y = 'CENTER'
    cu.resolution_u = 2
    o = bpy.data.objects.new(name, cu); o.location = loc; o.rotation_euler = rot; link(o)
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    m_o = bpy.data.objects.new(name + "_m", me); m_o.matrix_world = o.matrix_world.copy(); me.materials.clear(); me.materials.append(mat)
    bpy.data.objects.remove(o); bpy.data.curves.remove(cu)
    return link(m_o)
