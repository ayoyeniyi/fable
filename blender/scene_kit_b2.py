"""
Fable: shared helpers for room builder 2's chapter step-in rooms (build_munchkin_house_landing.py,
build_benbow_parlour.py, build_meryton_assembly_room.py, ...). Rooms are built ahead of time, served from the server and
downloaded by the headset (docs/SCENE_ROOMS.md), not bundled in the app.

It sits on pride_kit.py (scene set-up, node-material helpers, geometry, MB mesh builder, anchors, stills with the
"Blender render" stamp) and adds:

  * the foliage method of build_fields_to_netherfield.py, generalised: painted leaf-spray / grass atlases (numpy, no
    downloads), atlas cards with a sway weight, and tree() which grows a real branching tree (flared trunk, limbs,
    branches, twigs) with leaf-spray cards at the branch ends and through the crown's outer shell. Fruit trees,
    flowering banks and more spray kinds are added here.
  * a clear-sky dome material with sun glow and painted cumulus, a terrain grid from a height function.
  * export_room(): merge by material, bake procedural materials to textures (<= 2K), keep living-scene names and the
    sway colour, export glTF separate (.gltf + .bin + textures/) with export_extras=True (fx.* empties carry a custom
    property `radius`), and write export_stats.txt. Kept in one place so every room can be re-exported when
    docs/SCENE_ROOMS_PIPELINE.md settles the downloadable-room format.

Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os, json
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       texcoord_obj, wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB,
                       anchor, sound, light_obj, camera, smoothstep, lerp, n2, fbm2, link, Frame)

# hooks the room sets: ground height (world x, y -> z) and the reader's eye (cards and blades face it)
GZ = lambda x, y: 0.0
EYE = Vector((0.0, 0.0, 1.55))

def set_ground(fn, eye):
    global GZ, EYE
    GZ = fn; EYE = Vector(eye)

def gz(x, y): return GZ(x, y)

QUAD = [(0.0, 0.5, 0.5, 1.0), (0.5, 0.5, 1.0, 1.0), (0.0, 0.0, 0.5, 0.5), (0.5, 0.0, 1.0, 0.5)]   # 2x2 atlas cells (u0, v0, u1, v1)

def fx(name, loc, radius):
    """fx.fire.* (base of a flame), fx.candle.* (top of a wick), fx.torch.* / fx.lantern.*: an empty with the custom
    property `radius` (exported as a glTF extra) as docs/LIVING_SCENES.md asks."""
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'SPHERE'; e.empty_display_size = radius; e.location = loc
    e["radius"] = float(radius); link(e)
    return e

def blade(cv, x0, y0, length, ang, curve, w0, col_base, col_tip, segs=9, rngl=None):
    """a grass blade from (x0, y0) (pixels, y down) leaning at ang (0 = up), bending by curve; tapered."""
    x, y = x0, y0; a = ang
    for i in range(segs):
        t0, t1 = i / segs, (i + 1) / segs
        nx = x + math.sin(a) * length / segs; ny = y - math.cos(a) * length / segs
        col = tuple(cb + (ct - cb) * t1 for cb, ct in zip(col_base, col_tip)) + (1.0,)
        cv.line((x, y), (nx, ny), w0 * (1 - t0 * 0.92), w0 * (1 - t1 * 0.92), col)
        x, y = nx, ny; a += curve / segs * (1 + t0)
    return x, y


def spray(cv, x0, y0, x1, y1, R, kind):
    """a twig spray drawn into the cell (x0, y0)-(x1, y1): kind 'haw' (hawthorn hedge), 'oak', 'twig' (bare ash/elm), 'maple'."""
    W, Hh = x1 - x0, y1 - y0
    stack = [((x0 + W * 0.5 + R.gauss(0, W * 0.05), y1 - 2), -0.0 + R.gauss(0, 0.2), Hh * 0.55, 4.5 if kind != 'twig' else 4.0, 0)]
    bark = (0.20, 0.17, 0.14) if kind != 'twig' else (0.26, 0.25, 0.23)
    leaves = []
    while stack:
        (x, y), a, L, w, depth = stack.pop()
        segs = 5; px, py = x, y
        for s in range(segs):
            a += R.gauss(0, 0.18 if kind != 'twig' else 0.12)
            nx, ny = px + math.sin(a) * L / segs, py - math.cos(a) * L / segs
            nx = min(max(nx, x0 + 6), x1 - 6); ny = min(max(ny, y0 + 6), y1 - 2)
            ww = w * (1 - s / segs * 0.5)
            cv.line((px, py), (nx, ny), ww * 0.5, ww * 0.42, bark + (1.0,))
            if depth >= 1 or s >= 2: leaves.append((nx, ny, a))
            if depth < (3 if kind == 'twig' else 2) and R.random() < (0.55 if kind == 'twig' else 0.45):
                stack.append(((nx, ny), a + R.choice((-1, 1)) * R.uniform(0.45, 0.95), L * R.uniform(0.45, 0.7), w * 0.62, depth + 1))
            px, py = nx, ny
        leaves.append((px, py, a))
    if kind == 'twig':
        for (x, y, a) in leaves:                    # buds and the finest twiglets
            for k in range(2):
                b = a + R.choice((-1, 1)) * R.uniform(0.3, 0.8); L = R.uniform(10, 26)
                cv.line((x, y), (x + math.sin(b) * L, y - math.cos(b) * L), 0.9, 0.5, (0.30, 0.29, 0.27, 1.0))
            cv.ellipse(x, y, 2.2, 3.2, a, (0.10, 0.09, 0.08, 1.0))     # ash's black buds
        return
    if kind == 'haw':
        pal = [(0.30, 0.38, 0.15), (0.35, 0.43, 0.16), (0.27, 0.35, 0.13), (0.42, 0.46, 0.17), (0.52, 0.50, 0.18), (0.60, 0.48, 0.18), (0.32, 0.40, 0.15), (0.50, 0.36, 0.15)]
        nper, size = 7, 10.0
    elif kind == 'oak':
        pal = [(0.55, 0.38, 0.17), (0.61, 0.43, 0.19), (0.48, 0.33, 0.15), (0.56, 0.49, 0.23), (0.44, 0.43, 0.19), (0.66, 0.51, 0.23), (0.40, 0.27, 0.13)]
        nper, size = 4, 15.0
    elif kind in SPRAY_KINDS:
        pal, nper, size = SPRAY_KINDS[kind][:3]
    else:
        pal = [(0.66, 0.52, 0.16), (0.60, 0.44, 0.12), (0.52, 0.48, 0.16), (0.70, 0.56, 0.20), (0.46, 0.34, 0.12)]
        nper, size = 3, 15.0
    for (x, y, a) in leaves:
        for k in range(nper):
            b = a + R.gauss(0, 1.1); d = R.uniform(2, size * 1.4)
            lx, ly = x + math.sin(b) * d, y - math.cos(b) * d
            if not (x0 + 4 < lx < x1 - 4 and y0 + 4 < ly < y1 - 4): continue
            col = R.choice(pal); sh = R.uniform(0.8, 1.12); col = (col[0] * sh, col[1] * sh, col[2] * sh)
            s = size * R.uniform(0.7, 1.25)
            if kind == 'oak':
                # a lobed oak leaf: a long ellipse with three pairs of lobes
                cv.ellipse(lx, ly, s * 0.42, s, b, col + (1.0,), tip=0.3)
                for j in range(3):
                    t = (j - 1) * 0.42
                    ox, oy = lx + math.sin(b) * s * t, ly - math.cos(b) * s * t
                    for sg in (-1, 1):
                        cv.ellipse(ox + math.cos(b) * sg * s * 0.36, oy + math.sin(b) * sg * s * 0.36, s * 0.24, s * 0.2, b, col + (1.0,))
                cv.line((lx - math.sin(b) * s, ly + math.cos(b) * s), (lx + math.sin(b) * s * 0.8, ly - math.cos(b) * s * 0.8), 0.7, 0.4, (col[0] * 0.7, col[1] * 0.65, col[2] * 0.6, 1.0))
            elif kind == 'haw':
                cv.ellipse(lx, ly, s * 0.55, s * 0.75, b, col + (1.0,), tip=0.35)
                for sg in (-1, 1):
                    cv.ellipse(lx + math.cos(b) * sg * s * 0.45, ly + math.sin(b) * sg * s * 0.45, s * 0.3, s * 0.4, b + sg * 0.5, col + (1.0,))
            elif kind in SPRAY_KINDS:
                shape = SPRAY_KINDS[kind][3]
                if shape == 'narrow':      # willow, olive: long narrow leaves
                    cv.ellipse(lx, ly, s * 0.16, s * 0.95, b, col + (1.0,), tip=0.6)
                elif shape == 'needle':
                    for j in range(5):
                        nb_ = b + (j - 2) * 0.35
                        cv.line((lx, ly), (lx + math.sin(nb_) * s, ly - math.cos(nb_) * s), 1.1, 0.5, col + (1.0,))
                else:                      # broad ovate leaf with a midrib (apple, pear, lime, cherry, plane-ish)
                    cv.ellipse(lx, ly, s * 0.40, s * 0.78, b, col + (1.0,), tip=0.45)
                    cv.line((lx - math.sin(b) * s * 0.7, ly + math.cos(b) * s * 0.7), (lx + math.sin(b) * s * 0.6, ly - math.cos(b) * s * 0.6), 0.6, 0.3,
                            (col[0] * 0.75, col[1] * 0.8, col[2] * 0.7, 1.0))
            else:   # field maple: five-lobed, butter yellow
                for j in range(5):
                    lb = b + (j - 2) * 0.62
                    cv.ellipse(lx + math.sin(lb) * s * 0.35, ly - math.cos(lb) * s * 0.35, s * 0.24, s * 0.42, lb, col + (1.0,), tip=0.25)
        if kind in SPRAY_KINDS and SPRAY_KINDS[kind][4] and R.random() < SPRAY_KINDS[kind][4][0]:   # fruit / blossom
            share, cols, rad = SPRAY_KINDS[kind][4]
            for k in range(R.randint(1, 3)):
                fc = R.choice(cols); fx_, fy_ = x + R.gauss(0, 7), y + R.gauss(0, 7) + rad * 0.6
                cv.ellipse(fx_, fy_, rad, rad * 1.05, 0, fc + (1.0,))
                cv.ellipse(fx_ - rad * 0.35, fy_ - rad * 0.35, rad * 0.35, rad * 0.3, 0, tuple(min(1, c * 1.45 + 0.08) for c in fc) + (1.0,))
                cv.ellipse(fx_ + rad * 0.3, fy_ + rad * 0.4, rad * 0.5, rad * 0.35, 0, tuple(c * 0.6 for c in fc) + (0.6,))
        if kind == 'haw' and R.random() < 0.55:      # haws: dark red berries in small bunches
            for k in range(R.randint(2, 5)):
                cv.ellipse(x + R.gauss(0, 6), y + R.gauss(0, 6), 3.6, 4.0, 0, (0.42, 0.05, 0.04, 1.0))
                cv.ellipse(x + R.gauss(0, 6) - 1, y + R.gauss(0, 6) - 1, 1.2, 1.2, 0, (0.70, 0.25, 0.20, 1.0))

# kind: (palette, leaves per twig end, leaf size px, shape 'broad'|'narrow'|'needle', fruit (share, colours, radius px) or None)
SPRAY_KINDS = {
    "apple": ([(0.20, 0.36, 0.10), (0.25, 0.42, 0.12), (0.17, 0.31, 0.09), (0.30, 0.45, 0.14), (0.22, 0.38, 0.13)], 5, 13.0, 'broad',
              (0.22, [(0.62, 0.07, 0.05), (0.72, 0.14, 0.06), (0.52, 0.06, 0.04), (0.70, 0.40, 0.10)], 6.5)),
    "pear": ([(0.22, 0.38, 0.12), (0.27, 0.43, 0.13), (0.19, 0.33, 0.10), (0.31, 0.46, 0.15)], 5, 13.0, 'broad',
             (0.2, [(0.62, 0.58, 0.18), (0.56, 0.52, 0.16), (0.66, 0.50, 0.14)], 6.5)),
    "plum": ([(0.19, 0.33, 0.11), (0.23, 0.38, 0.12), (0.16, 0.29, 0.09), (0.26, 0.41, 0.14)], 5, 12.0, 'broad',
             (0.25, [(0.22, 0.07, 0.24), (0.30, 0.09, 0.32), (0.40, 0.14, 0.36)], 5.0)),
    "lime": ([(0.27, 0.42, 0.13), (0.31, 0.47, 0.15), (0.23, 0.37, 0.11), (0.35, 0.50, 0.17), (0.28, 0.40, 0.12)], 4, 15.0, 'broad', None),
    "beech": ([(0.30, 0.42, 0.13), (0.35, 0.47, 0.15), (0.26, 0.38, 0.11), (0.38, 0.48, 0.16)], 5, 12.0, 'broad', None),
    "elm": ([(0.21, 0.32, 0.11), (0.25, 0.36, 0.12), (0.18, 0.28, 0.09), (0.28, 0.38, 0.14)], 5, 11.0, 'broad', None),
    "willow": ([(0.36, 0.44, 0.22), (0.42, 0.50, 0.26), (0.32, 0.40, 0.20), (0.46, 0.52, 0.30)], 6, 16.0, 'narrow', None),
    "olive": ([(0.30, 0.34, 0.22), (0.36, 0.40, 0.27), (0.26, 0.30, 0.20), (0.44, 0.47, 0.36)], 6, 13.0, 'narrow', None),
    "oaksummer": ([(0.18, 0.29, 0.09), (0.21, 0.33, 0.10), (0.15, 0.25, 0.08), (0.24, 0.35, 0.12)], 5, 13.0, 'broad', None),
    "pine": ([(0.13, 0.21, 0.10), (0.16, 0.25, 0.12), (0.11, 0.18, 0.09)], 7, 14.0, 'needle', None),
}

def spray_atlas(name, kind, seed, S=1024):
    cv = Canvas(S, S); R = random.Random(seed); h = S // 2
    for (cx, cy) in ((0, 0), (h, 0), (0, h), (h, h)):
        cv.clip = (cx + 1, cy + 1, cx + h - 1, cy + h - 1)
        for k in range(5 if kind == 'haw' else (4 if kind in SPRAY_KINDS else (3 if kind != 'twig' else 2))):
            spray(cv, cx + 4, cy + 4, cx + h - 4, cy + h - 4, R, kind)
    cv.clip = None; cv.bleed(6)
    return K.np_image(name, cv.a)


def set_card_normals(o, fn):
    """custom normals for foliage cards: fn(world position) -> the normal to shade with (rounded, volumetric)."""
    me = o.data
    ns = [tuple(fn(v.co)) for v in me.vertices]
    me.normals_split_custom_set_from_vertices(ns)

def card(mb, base, right, up, cell, sway0, sway1, bend=None, segs=1):
    """an atlas card. cell = (u0, v0, u1, v1). bend: a vector added to the top (curving it over), segs > 1 splits it."""
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

GRASS_SHORT = [((c * 256) / 1024, 1 - 256 / 1024, (c * 256 + 256) / 1024, 1.0) for c in range(4)]
GRASS_LONG = [((c * 256) / 1024, 1 - 768 / 1024, (c * 256 + 256) / 1024, 1 - 256 / 1024) for c in range(4)]
HERB = {k: ((i * 256) / 1024, 0.0, (i * 256 + 256) / 1024, 256 / 1024) for i, k in enumerate(("rush", "dock", "umbel", "nettle"))}
QUAD = [(0.0, 0.5, 0.5, 1.0), (0.5, 0.5, 1.0, 1.0), (0.0, 0.0, 0.5, 0.5), (0.5, 0.0, 1.0, 0.5)]   # 2x2 atlas cells (u0, v0, u1, v1)

def solid_tuft(mb, R, x, y, z, sc, nbl=5):
    """an opaque grass tuft: a few thin tapering blade triangles leaning out of one root, UV'd into a tone column."""
    col = R.randrange(8) if R.random() < 0.85 else R.choice((6, 7))
    if R.random() < 0.85: col = R.randrange(6)
    u = (col * 2 + 1) / 16.0
    for k in range(nbl):
        a = R.uniform(0, 2 * math.pi); lean = R.uniform(0.15, 0.55)
        hgt = R.uniform(0.14, 0.30) * sc
        d = Vector((math.cos(a), math.sin(a), 0))
        w = Vector((-d.y, d.x, 0)) * R.uniform(0.012, 0.022) * sc
        root = Vector((x, y, z - 0.01)) + d * R.uniform(0.0, 0.05) * sc
        tip = root + d * hgt * lean + Vector((0, 0, hgt))
        i0 = mb.vert(root - w, (u - 0.02, 0.0), 0.0); i1 = mb.vert(root + w, (u + 0.02, 0.0), 0.0); i2 = mb.vert(tip, (u, 1.0), 1.0)
        # wind each blade to face the reader: renderers flip the shading normal on back faces, which turns them black
        fnrm = (2 * w).cross(tip - (root - w))
        if fnrm.dot(Vector((EYE.x - x, EYE.y - y, EYE.z - z))) >= 0: mb.face(i0, i1, i2)
        else: mb.face(i1, i0, i2)

_ICO = {}
def _unit_ico(sub):
    if sub not in _ICO:
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        _ICO[sub] = ([tuple(v.co) for v in bm.verts], [tuple(v.index for v in f.verts) for f in bm.faces]); bm.free()
    return _ICO[sub]

def blob(mb, c, r, seed, sub=2, rough=0.22, fine=0.0):
    """a lumpy opaque foliage blob: an icosphere scaled to radii r and pushed in and out by noise (the leafy lumps)."""
    vs, fs = _unit_ico(sub); c = Vector(c); base = len(mb.v)
    for (vx, vy, vz) in vs:
        d = Vector((vx, vy, vz))
        k = 1.0 + rough * noise.noise(d * 1.6 + Vector((seed * 3.1, seed * 1.7, 0.0))) + 0.5 * rough * noise.noise(d * 3.7 + Vector((0.0, seed, seed))) + 0.6 * rough * noise.noise(d * 7.5 + Vector((seed, 0.0, seed)))
        p = c + Vector((d.x * r[0], d.y * r[1], d.z * r[2] * (0.85 if d.z < 0 else 1.0))) * k
        mb.vert(p, (0, 0), 0.2 + 0.4 * max(0.0, d.z))
    for f in fs: mb.face(*[base + i for i in f])

def tree(name, x, y, height, spread, kind, seed, bark, leaves_mat, nlimbs=6, detail=1.0, cards_per_tip=3, card_size=1.3, lean=(0, 0), dense=1.0, fill=0,
         mass=None, mass_k=0.8, mass_sub=2, nblobs=7):
    """A hedgerow or park tree grown to a crown envelope (an ellipsoid set by its kind): a flared trunk; limbs from the
    top of the trunk reaching out to the envelope with a sag (oak) or an upward sweep (ash, elm); branches off each
    limb to nearby points on the envelope; on near trees, twigs. Atlas cards (leaf sprays or bare twigs) sit at the
    branch ends and through the outer shell of the envelope, facing outwards, so the crown reads as a volume with a
    broken edge. kind: 'oak' (broad, low, crooked), 'ash' (taller, open, upturned), 'maple' (small, round), 'elm'
    (tall, narrow, billowing). mass: an opaque leafy material for a lumpy crown mass at mass_k of the envelope: inside
    the cards on near trees (so fewer, larger cards still read as a full crown), the whole crown on far trees (with at
    most a sparse fringe of cards for a broken edge)."""
    R = random.Random(seed)
    z0 = gz(x, y) - 0.15
    base = Vector((x, y, z0))
    shape = {"oak": (0.34, 1.0, 0.36), "ash": (0.36, 0.85, 0.40), "maple": (0.30, 0.95, 0.40), "elm": (0.28, 0.75, 0.45)}[kind]
    trunk_h = height * shape[0]
    a_ = spread * shape[1] / 1.0; c_ = (height - trunk_h) * 0.5
    C = base + Vector((lean[0], lean[1], trunk_h + c_ * 0.95))
    r0 = height * {"oak": 0.042, "ash": 0.028, "maple": 0.03, "elm": 0.03}[kind]
    def env(az, el, k=1.0):
        return C + Vector((math.cos(az) * math.cos(el) * a_ * (1 + 0.12 * R.gauss(0, 1)), math.sin(az) * math.cos(el) * a_ * (1 + 0.12 * R.gauss(0, 1)), math.sin(el) * c_)) * k
    tubes = []; tips = []
    top = base + Vector((lean[0], lean[1], trunk_h))
    tp = [base + (top - base) * t + Vector((R.gauss(0, 0.05), R.gauss(0, 0.05), 0)) * float(t > 0) for t in (0, 0.3, 0.65, 1.0)]
    tubes.append((tp, [r0 * 1.6, r0 * 1.08, r0, r0 * 0.9], 8 if detail >= 1 else 6))
    def bent(p0, p1, sag, n, wob):
        pts = []
        for i in range(n + 1):
            t = i / n; q = p0.lerp(p1, t)
            q.z -= sag * math.sin(math.pi * t) * (p1 - p0).length
            if 0 < i < n: q += Vector((R.gauss(0, wob), R.gauss(0, wob), R.gauss(0, wob)))
            pts.append(q)
        return pts
    sag = {"oak": 0.10, "ash": -0.06, "maple": 0.0, "elm": -0.05}[kind]
    wob = {"oak": 0.18, "ash": 0.08, "maple": 0.08, "elm": 0.10}[kind]
    for i in range(nlimbs):
        az = 2 * math.pi * (i + R.uniform(-0.3, 0.3)) / nlimbs
        el = R.uniform(0.05, 0.75) if kind == "oak" else R.uniform(0.35, 1.1)
        start = tp[-1] if i % 3 else tp[-2].lerp(tp[-1], 0.6)
        tgt = env(az, el, 0.78)
        lp = bent(start, tgt, sag, 4, wob * spread * 0.08)
        rl = [r0 * 0.62 * (1 - 0.6 * k / 4) for k in range(5)]
        tubes.append((lp, rl, 6 if detail >= 1 else 4))
        tips.append((lp[-1], (tgt - start).normalized(), 0))
        nb = 4 if detail >= 1 else 3
        for j in range(nb):
            k = R.randint(1, 4); bp = lp[k]
            baz = az + R.gauss(0, 0.6); bel = el + R.gauss(0, 0.35)
            bt = env(baz, bel, R.uniform(0.92, 1.02))
            bpts = bent(bp, bt, sag * 0.6, 3, wob * 0.25)
            br = [rl[k] * 0.55 * (1 - 0.65 * q / 3) for q in range(4)]
            if detail >= 0.6: tubes.append((bpts, br, 4 if detail >= 1 else 3))
            d = (bt - bp).normalized(); tips.append((bpts[-1], d, 1))
            for q in (1, 2):
                tips.append((bpts[q] + Vector((R.gauss(0, 0.3), R.gauss(0, 0.3), R.gauss(0, 0.2))), d, 2))
            if detail >= 1:
                for t_ in range(2):
                    tw0 = bpts[R.randint(1, 3)]
                    tw1 = tw0 + (d + Vector((R.gauss(0, 0.6), R.gauss(0, 0.6), R.gauss(0, 0.4) + (0.4 if kind != "oak" else 0)))).normalized() * R.uniform(0.6, 1.3)
                    tubes.append(([tw0, tw0.lerp(tw1, 0.5), tw1], [br[1] * 0.5, br[1] * 0.3, 0.004], 3))
                    tips.append((tw1, d, 3))
    if detail >= 1:
        tubes.append((bent(tp[-1], C + Vector((0, 0, c_ * 0.85)), 0.0, 3, 0.1), [r0 * 0.5, r0 * 0.35, r0 * 0.2, 0.02], 5))
    for k, (pl, rl, sides) in enumerate(tubes):
        tube(f"{name}_b{k}", pl, rl, bark, sides=sides, caps=False)
    mb = MB(); cells = QUAD
    def put(q, out, sz):
        tang = out.cross(Vector((0, 0, 1)))
        if tang.length < 0.1: tang = Vector((1, 0, 0))
        tang.normalize(); bit = out.cross(tang).normalized(); roll = R.uniform(-math.pi, math.pi)
        right = (tang * math.cos(roll) + bit * math.sin(roll)) * sz
        up = (bit * math.cos(roll) - tang * math.sin(roll)) * sz + out * sz * R.uniform(0.2, 0.5)
        card(mb, q - up * 0.5, right, up, R.choice(cells), 0.35, 1.0)
    for (q, d, depth) in tips:
        for c in range(int(cards_per_tip * dense + R.random())):
            out = ((q - C) * Vector((1 / a_, 1 / a_, 1 / c_))).normalized()
            out = (out + d * 0.5 + Vector((R.gauss(0, 0.45), R.gauss(0, 0.45), R.gauss(0, 0.35)))).normalized()
            put(q, out, card_size * R.uniform(0.75, 1.25))
    for i in range(fill):
        az = R.uniform(0, 2 * math.pi); el = math.asin(R.uniform(-0.45, 1.0))
        q = env(az, el, R.uniform(0.9, 1.06) if (mass is not None and cards_per_tip == 0) else R.uniform(0.72, 1.0) ** 0.6)
        out = ((q - C) * Vector((1 / a_, 1 / a_, 1 / c_))).normalized()
        out = (out + Vector((R.gauss(0, 0.4), R.gauss(0, 0.4), R.gauss(0, 0.3)))).normalized()
        put(q, out, card_size * R.uniform(0.7, 1.2))
    crown = mb.build(f"{name}_crown", leaves_mat)
    if mass is not None:
        mm = MB()
        blob(mm, C + Vector((0, 0, -c_ * 0.05)), (a_ * mass_k * 0.72, a_ * mass_k * 0.72, c_ * mass_k * 0.75), seed, 2, rough=0.18)
        for i in range(nblobs):
            az = 2 * math.pi * (i + R.uniform(-0.3, 0.3)) / nblobs; el = math.asin(R.uniform(-0.25, 0.9))
            sh = R.uniform(0.55, 0.72)
            q = C + Vector((math.cos(az) * math.cos(el) * a_, math.sin(az) * math.cos(el) * a_, math.sin(el) * c_)) * mass_k * sh
            rr = a_ * mass_k * R.uniform(0.3, 0.42)
            blob(mm, q, (rr, rr, rr * R.uniform(0.75, 0.95)), seed + i + 1, mass_sub, rough=0.28)
        mm.build(f"{name}_mass", mass, sway=False)
    if crown is not None:
        set_card_normals(crown, lambda p: (((p - C) * Vector((1 / a_, 1 / a_, 1 / c_))) + Vector((0, 0, 0.6))).normalized() if (p - C).length > 0.01 else Vector((0, 0, 1)))
    return tips, C


# ----------------------------------------------------------------------------- bark (from build_fields_to_netherfield.py, drier by default)
def bark_mat(name, base=(0.17, 0.16, 0.14), dark=(0.07, 0.065, 0.06), light=(0.30, 0.29, 0.26), fissure=True, green=0.35, scale=1.0):
    """Wet bark: grey-brown, fissured (oak) or smoother (ash), with green algae on the weather side (west, -X) and
    darker wet streaks running down."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1600, -600))
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
    # algae on the west side (Pleurococcus) and wet streaks
    nrm = node(nt, "ShaderNodeNewGeometry", (-1300, -900))
    sn = sep_xyz(nt, nrm.outputs["Normal"], (-1100, -900))
    alg = math_(nt, 'MULTIPLY', maprange(nt, sn.outputs["X"], 0.1, -0.8, 0, 1, (-900, -900)), maprange(nt, noise_(nt, co, 1.5, 3, 0.6, loc=(-1100, -1100)).outputs["Fac"], 0.4, 0.62, 0, green, (-900, -1100)), (-700, -950))
    col = mix_rgb(nt, 'MIX', alg, col, (0.16, 0.22, 0.07, 1), (-400, 200))
    streak = noise_(nt, mp.outputs["Vector"], 2.0, 3, 0.5, loc=(-1200, -350))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, streak.outputs["Fac"], 0.45, 0.7, 0.0, 0.45, (-900, -350)), col, (0.6, 0.6, 0.6, 1), (-200, 200))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, h, 0, 1, 0.75, 0.5, (-300, -200)), b.inputs["Roughness"])
    bump_from(nt, b, h, 0.6, 0.02, (0, -400))
    return m


# ----------------------------------------------------------------------------- meadow grass and flower atlas, blade tones
def meadow_atlas(name="A_MeadowCards", greens=None, tips=None, flowers=None, seed=7, dry=0.06):
    """1024 x 1024: row 0 (256 high): four short lawn/greensward tufts; rows 1-2 (512 high): four long meadow grass
    clumps; row 3: four flowering clumps (flowers: list of 4 (petal colour, centre colour, kind) with kind 'daisy',
    'cup', 'spike', 'umbel')."""
    S = 1024; cv = Canvas(S, S); R = random.Random(seed)
    greens = greens or [(0.08, 0.20, 0.03), (0.11, 0.24, 0.04), (0.06, 0.16, 0.025), (0.14, 0.27, 0.05), (0.09, 0.21, 0.035)]
    tips = tips or [(0.22, 0.36, 0.08), (0.26, 0.40, 0.10), (0.18, 0.32, 0.07)]
    straw = [(0.42, 0.38, 0.18), (0.36, 0.32, 0.15)]
    for c in range(4):
        x0 = c * 256; base = 252; cv.clip = (x0 + 1, 1, x0 + 255, 256)
        for i in range(80 + c * 8):
            bx = x0 + 128 + R.gauss(0, 32); g = R.choice(greens); t = R.choice(tips)
            if R.random() < dry: g, t = R.choice(straw), R.choice(straw)
            L = R.uniform(80, 220)
            blade(cv, bx, base, L, R.gauss(0, 0.30) + (bx - x0 - 128) / 230, R.gauss(0, 0.45), R.uniform(2.6, 4.2), g, t)
    for c in range(4):
        x0 = c * 256; base = 256 + 508; cv.clip = (x0 + 1, 257, x0 + 255, 768)
        for i in range(60):
            bx = x0 + 128 + R.gauss(0, 34); dead = R.random() < dry * 1.5
            g = R.choice(straw) if dead else R.choice(greens); t = R.choice(straw) if dead else R.choice(tips)
            L = R.uniform(220, 490); lean = R.gauss(0, 0.25) + (bx - x0 - 128) / 260
            ex, ey = blade(cv, bx, base, L, lean, R.choice((-1, 1)) * R.uniform(0.2, 1.1), R.uniform(3.0, 5.0), g, t, segs=12)
            if R.random() < 0.18:
                for k in range(8):
                    cv.ellipse(ex + R.gauss(0, 3), ey + R.gauss(0, 6) + k * 2.5, 2.0, 5.5, R.gauss(0, 0.3), (0.55, 0.55, 0.35, 1.0))
    flowers = flowers or [((0.95, 0.93, 0.88), (0.95, 0.75, 0.10), 'daisy'), ((0.90, 0.72, 0.08), (0.80, 0.55, 0.05), 'cup'),
                          ((0.45, 0.22, 0.62), (0.35, 0.15, 0.50), 'spike'), ((0.85, 0.20, 0.25), (0.20, 0.10, 0.05), 'cup')]
    y0 = 768; base = y0 + 252
    for c, (pc, cc, fk) in enumerate(flowers):
        x0 = c * 256; cv.clip = (x0 + 1, 769, x0 + 255, 1024)
        for i in range(30):          # leafy base
            bx = x0 + 128 + R.gauss(0, 30)
            blade(cv, bx, base, R.uniform(60, 140), R.gauss(0, 0.5), R.gauss(0, 0.6), R.uniform(3, 5), R.choice(greens), R.choice(tips))
        for i in range(9 if fk != 'spike' else 6):
            bx = x0 + 128 + R.gauss(0, 34); L = R.uniform(120, 230)
            ex, ey = blade(cv, bx, base, L, R.gauss(0, 0.18) + (bx - x0 - 128) / 300, R.gauss(0, 0.25), 2.0, (0.07, 0.17, 0.03), (0.12, 0.24, 0.05), segs=8)
            sh = R.uniform(0.85, 1.1); p = tuple(min(1.0, v * sh) for v in pc)
            if fk == 'daisy':
                for k in range(12):
                    a = k / 12 * 2 * math.pi
                    cv.ellipse(ex + math.cos(a) * 8, ey + math.sin(a) * 4.5, 7.0, 2.4, a, p + (1.0,))
                cv.ellipse(ex, ey, 4.5, 3.2, 0, cc + (1.0,))
            elif fk == 'cup':
                for k in range(5):
                    a = -math.pi / 2 + (k - 2) * 0.5
                    cv.ellipse(ex + math.cos(a) * 6, ey + math.sin(a) * 6 - 2, 5.5, 8.5, a + math.pi / 2, p + (1.0,), tip=0.2)
                cv.ellipse(ex, ey + 2, 3.5, 2.5, 0, cc + (1.0,))
            elif fk == 'spike':
                for k in range(14):
                    cv.ellipse(ex + R.gauss(0, 2.5), ey + k * 4.5, 4.2 - k * 0.12, 3.2, R.gauss(0, 0.4), tuple(v * R.uniform(0.85, 1.1) for v in p) + (1.0,))
            else:   # umbel
                for k in range(16):
                    cv.ellipse(ex + R.gauss(0, 9), ey + abs(R.gauss(0, 3)), 2.6, 2.2, 0, p + (1.0,))
    cv.clip = None; cv.bleed(6)
    return np_image(name, cv.a)

MEADOW_SHORT = [((c * 256) / 1024, 1 - 256 / 1024, (c * 256 + 256) / 1024, 1.0) for c in range(4)]
MEADOW_LONG = [((c * 256) / 1024, 1 - 768 / 1024, (c * 256 + 256) / 1024, 1 - 256 / 1024) for c in range(4)]
MEADOW_FLOWER = [((c * 256) / 1024, 0.0, (c * 256 + 256) / 1024, 256 / 1024) for c in range(4)]

def blade_tones(name="A_BladeTones", cols=None, tips=None):
    """16 x 64 opaque strip for solid grass blades: eight tone columns, root (bottom) dark to tip light."""
    cols = cols or [(0.08, 0.20, 0.03), (0.11, 0.24, 0.04), (0.06, 0.16, 0.025), (0.14, 0.27, 0.05), (0.09, 0.21, 0.035), (0.12, 0.23, 0.045),
                    (0.30, 0.28, 0.12), (0.16, 0.26, 0.06)]
    tips = tips or [(0.22, 0.36, 0.08), (0.26, 0.40, 0.10), (0.18, 0.32, 0.07), (0.24, 0.38, 0.09), (0.20, 0.34, 0.08), (0.26, 0.38, 0.10),
                    (0.45, 0.40, 0.20), (0.28, 0.40, 0.11)]
    a = np.ones((64, 16, 4), np.float32)
    for i in range(8):
        for r in range(64):
            t = 1.0 - r / 63.0
            g = [c * (0.45 + 0.55 * min(1.0, t * 1.6)) for c in cols[i]]
            col = [lerp(g[k], tips[i][k], smoothstep(0.55, 1.0, t)) for k in range(3)]
            a[r, i * 2:i * 2 + 2, :3] = col
    return np_image(name, a)


def scatter_cards(mb, sb, R, n, rmin, rmax, ok, cells, height=0.24, width=0.30, solid_from=4.0, centre=(0.0, 0.0), maxcards=1200, nbl=5, segs=1):
    """grass/flower cards around the reader (within rmax of centre), each turned to face the eye; beyond solid_from, opaque
    blade tufts into sb instead. ok(x, y) -> density 0..1 (0 = none)."""
    placed = 0; cx, cy = centre
    for i in range(n):
        r = rmin + (rmax - rmin) * R.random() ** 1.1; a = R.uniform(0, 2 * math.pi)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        d = ok(x, y)
        if d <= 0 or R.random() > d: continue
        z = gz(x, y); sc = R.uniform(0.7, 1.25)
        de = math.hypot(x - EYE.x, y - EYE.y)
        if sb is not None and de > solid_from:
            solid_tuft(sb, R, x, y, z, sc * 1.1, nbl=nbl); placed += 1; continue
        to_r = Vector((EYE.x - x, EYE.y - y, 0)); to_r = to_r.normalized() if to_r.length > 1e-3 else Vector((0, -1, 0))
        ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + R.gauss(0, 0.45)
        right = Vector((math.cos(ya), math.sin(ya), 0)) * width * sc
        up = Vector((0, 0, height * sc)) - to_r * height * 0.25 * sc
        card(mb, (x, y, z - 0.015), right, up, R.choice(cells), 0.0, 1.0, segs=segs)
        placed += 1
        if placed >= maxcards: break
    return placed


# ----------------------------------------------------------------------------- terrain
def terrain(name, fn, x0, x1, y0, y1, nx, ny, mat, uv_scale=None):
    """a height-field grid; UVs map the whole grid to 0..1 (baked as one texture), or repeat every uv_scale metres."""
    verts = []; uvs = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx; y = y0 + (y1 - y0) * j / ny
            verts.append((x, y, fn(x, y)))
            uvs.append(((x - x0) / uv_scale, (y - y0) / uv_scale) if uv_scale else (i / nx, j / ny))
    faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(ny) for i in range(nx)]
    return mesh_from(name, verts, faces, mat, smooth=True, uvs=uvs)


# ----------------------------------------------------------------------------- clear sky dome
def clear_sky_mat(name, sun_dir, zenith=(0.16, 0.36, 0.78), horizon=(0.66, 0.80, 0.95), cloud=0.45, strength=1.0, land=None, seed=3.3):
    """A clear morning/day sky: deep blue overhead to a pale horizon, a warm glow round the sun, scattered fair-weather
    cumulus (flat bases, lit tops) in perspective; optional land silhouette band along the horizon
    (land = (colour near, colour far, height)). Emission only (unlit backdrop)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-2200, 0), operation='NORMALIZE'); nt.links.new(co, nv.inputs[0]); d = nv.outputs[0]
    s = sep_xyz(nt, d, (-2000, 0)); el = s.outputs["Z"]
    base = ramp(nt, [(0.0, c4(horizon)), (0.12, c4(tuple(lerp(horizon[i], zenith[i], 0.35) for i in range(3)))), (0.45, c4(tuple(lerp(horizon[i], zenith[i], 0.8) for i in range(3)))), (1.0, c4(zenith))], (-1500, 400))
    nt.links.new(maprange(nt, el, 0.0, 1.0, 0, 1, (-1700, 400)), base.inputs["Fac"])
    col = base.outputs["Color"]
    sd = node(nt, "ShaderNodeVectorMath", (-1700, 800), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(Vector(sun_dir).normalized()); nt.links.new(d, sd.inputs[0])
    glow = math_(nt, 'POWER', maprange(nt, sd.outputs["Value"], 0.6, 1.0, 0, 1, (-1500, 800)), 4.0, (-1350, 800))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', glow, 0.6, (-1200, 850)), col, (1.0, 0.92, 0.78, 1), (-1000, 400))
    disc = maprange(nt, sd.outputs["Value"], 0.9993, 0.9996, 0, 1, (-1500, 1000))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', disc, 6.0, (-1200, 1000)), col, (1.0, 0.97, 0.9, 1), (-900, 500))
    if cloud > 0:
        zk = math_(nt, 'ADD', math_(nt, 'MAXIMUM', el, 0.0, (-1800, -200)), 0.08, (-1650, -200))
        px = math_(nt, 'DIVIDE', s.outputs["X"], zk, (-1500, -150)); py = math_(nt, 'DIVIDE', s.outputs["Y"], zk, (-1500, -300))
        cvv = node(nt, "ShaderNodeCombineXYZ", (-1350, -200)); nt.links.new(px, cvv.inputs["X"]); nt.links.new(py, cvv.inputs["Y"]); cvv.inputs["Z"].default_value = seed
        n1 = noise_(nt, cvv.outputs[0], 0.55, 6, 0.55, 0.2, (-1100, -200))
        n2_ = noise_(nt, cvv.outputs[0], 2.2, 4, 0.6, 0.0, (-1100, -450))
        dens = math_(nt, 'ADD', n1.outputs["Fac"], math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.25, (-900, -450)), (-800, -300))
        thr = 0.68 - cloud * 0.12
        cov = maprange(nt, dens, thr, thr + 0.12, 0, 1, (-650, -300), 'SMOOTHSTEP')
        cov = math_(nt, 'MULTIPLY', cov, maprange(nt, el, 0.015, 0.12, 0, 1, (-650, -550)), (-500, -400))
        shade = maprange(nt, n2_.outputs["Fac"], 0.35, 0.7, 0.72, 1.0, (-650, -700))
        ccol = mix_rgb(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, shade, (-450, -700)), (1.0, 0.99, 0.96, 1), (0.62, 0.66, 0.74, 1), (-300, -650))
        ccol = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', glow, 0.4, (-450, -900)), ccol, (1.0, 0.85, 0.6, 1), (-200, -750))
        col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', cov, 0.92, (-300, -400)), col, ccol, (0, 300))
    if land:
        near_c, far_c, hgt = land
        az = math_(nt, 'ARCTAN2', s.outputs["X"], s.outputs["Y"], (-1800, -1200))
        azv = node(nt, "ShaderNodeCombineXYZ", (-1650, -1200)); nt.links.new(math_(nt, 'COSINE', az, None, (-1700, -1300)), azv.inputs["X"]); nt.links.new(math_(nt, 'SINE', az, None, (-1700, -1400)), azv.inputs["Y"])
        azv.inputs["Z"].default_value = seed
        hn = noise_(nt, azv.outputs[0], 1.8, 3, 0.5, loc=(-1500, -1200)); tn = noise_(nt, azv.outputs[0], 22.0, 4, 0.7, loc=(-1500, -1450))
        hill = math_(nt, 'ADD', math_(nt, 'MULTIPLY', hn.outputs["Fac"], hgt * 2.0, (-1300, -1200)), math_(nt, 'MULTIPLY', maprange(nt, tn.outputs["Fac"], 0.35, 0.65, 0, 1, (-1300, -1450)), hgt * 0.5, (-1150, -1450)), (-1000, -1300))
        hill = math_(nt, 'SUBTRACT', hill, hgt * 0.6, (-900, -1300))
        landm = maprange(nt, math_(nt, 'SUBTRACT', hill, el, (-650, -1300)), 0.0, 0.002, 0, 1, (-500, -1300))
        landcol = mix_rgb(nt, 'MIX', maprange(nt, el, 0.0, hgt * 1.5, 1, 0, (-500, -1500)), c4(far_c), c4(near_c), (-300, -1400))
        col = mix_rgb(nt, 'MIX', landm, col, landcol, (300, 400))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = strength; b.inputs["Roughness"].default_value = 1.0
    return m

def sky_dome(name, mat, radius, seg=48, rings=16, el_min=-10.0, centre=(0, 0, 0)):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rows = []; cx, cy, cz = centre
    for j in range(rings + 1):
        e = math.radians(el_min + (90.0 - el_min) * (j / rings))
        rows.append([bm.verts.new((cx + radius * math.cos(e) * math.sin(2 * math.pi * i / seg), cy + radius * math.cos(e) * math.cos(2 * math.pi * i / seg), cz + radius * math.sin(e))) for i in range(seg)])
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

def world_sky(zen=(0.25, 0.42, 0.75), hor=(0.75, 0.82, 0.90), ground=(0.12, 0.13, 0.08), strength=1.0):
    scene = K.scene
    world = bpy.data.worlds.new("World"); scene.world = world; world.use_nodes = True
    wnt = world.node_tree; bg = wnt.nodes["Background"]
    wtc = wnt.nodes.new("ShaderNodeTexCoord"); wsep = wnt.nodes.new("ShaderNodeSeparateXYZ"); wnt.links.new(wtc.outputs["Generated"], wsep.inputs["Vector"])
    wmr = wnt.nodes.new("ShaderNodeMapRange"); wmr.inputs["From Min"].default_value = -0.1; wmr.inputs["From Max"].default_value = 1.0
    wnt.links.new(wsep.outputs["Z"], wmr.inputs["Value"])
    wr = ramp(wnt, [(0.0, c4(ground)), (0.09, c4(hor)), (1.0, c4(zen))])
    wnt.links.new(wmr.outputs["Result"], wr.inputs["Fac"]); wnt.links.new(wr.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    return world

def world_flat(color=(0.05, 0.05, 0.05), strength=1.0):
    scene = K.scene
    world = bpy.data.worlds.new("World"); scene.world = world; world.use_nodes = True
    bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = c4(color); bg.inputs["Strength"].default_value = strength
    return world


# ----------------------------------------------------------------------------- reader anchors, cameras, page
def reader_anchors(entrance, look):
    """entrance: feet on the floor; look: a point at eye height ahead (the direction the reader faces)."""
    anchor("reader.entrance", tuple(entrance)); anchor("reader.look", tuple(look))

def page_preview(eye, fwd, dist=0.6):
    fwd = Vector((fwd[0], fwd[1], 0)).normalized(); c = Vector(eye) + fwd * dist + Vector((0, 0, -0.05))
    yaw = math.atan2(fwd.y, fwd.x) - math.pi / 2
    return box("PagePreview", (0.4, 0.004, 0.55), tuple(c), plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9), rot=(0, 0, yaw))

def view_cams(eye, fwd, extra=(), lens=17, dist=10.0):
    """reader, page, left, right, behind and down from the eye, plus extra (name, loc, look_at, lens)."""
    E = Vector(eye); f = Vector((fwd[0], fwd[1], 0)).normalized()
    def yawed(deg, dz):
        a = math.radians(deg); ca, sa = math.cos(a), math.sin(a)
        v = Vector((f.x * ca + f.y * sa, -f.x * sa + f.y * ca, 0))     # positive deg turns right (clockwise from above)
        return tuple(E + v * dist + Vector((0, 0, dz)))
    cams = [camera("Cam_Reader", tuple(E), yawed(0, -1.2), lens=lens), camera("Cam_Page", tuple(E), yawed(0, -1.2), lens=lens),
            camera("Cam_Left", tuple(E), yawed(-80, -1.0), lens=lens), camera("Cam_Right", tuple(E), yawed(80, -1.0), lens=lens),
            camera("Cam_Behind", tuple(E), yawed(180, -1.0), lens=lens),
            camera("Cam_Down", tuple(E), tuple(E + f * 1.6 + Vector((0, 0, -E.z + 0.0)) * 1.0), lens=lens)]
    for (n, loc, at, ln) in extra: cams.append(camera(n, tuple(loc), tuple(at), lens=ln))
    for c in cams: c.data.clip_end = 1500.0      # the sky domes reach out to ~1 km
    return cams


# ----------------------------------------------------------------------------- export for the downloadable room
def export_room(gltf_name, cams, page=None, keep_names=None, keep_uv=(), size_for=None, default_size=(256, 64, 128), sky_names=("SkyDome",),
                unlit_emit=(), max_tex=2048):
    """pride_kit.bake_and_export (merge by material, bake procedural materials, keep painted atlases and living-scene
    names and sway colour) with export_extras=True so fx.* empties keep their `radius`, every baked texture capped at
    max_tex (2K) and the result checked against the step-in room budget (<= 45k triangles)."""
    size_for = {k: tuple(min(max_tex, s) for s in v) for k, v in (size_for or {}).items()}
    # pride_kit's exporter call has no export_extras: wrap bpy's glTF operator for the duration
    real = bpy.ops.export_scene.gltf
    class _Wrap:
        def __call__(self, **kw):
            kw["export_extras"] = True
            return real(**kw)
    bpy.ops.export_scene.gltf = _Wrap()
    try:
        gl = K.bake_and_export(gltf_name, cams, page=page, keep_names=keep_names, keep_uv=set(keep_uv), size_for=size_for,
                               default_size=default_size, sky_names=sky_names, unlit_emit=unlit_emit)
    finally:
        bpy.ops.export_scene.gltf = real
    with open(gl) as f: g = json.load(f)
    fxn = [n for n in g.get("nodes", []) if n.get("name", "").startswith("fx.")]
    print("FX NODES", [(n["name"], n.get("extras", {}).get("radius")) for n in fxn])
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in K.COLL.objects if o.type == 'MESH')
    size = sum(os.path.getsize(os.path.join(dp, fn)) for dp, _, fns in os.walk(K.OUT) for fn in fns
               if fn.endswith((".gltf", ".bin", ".jpg", ".jpeg", ".png")) and ("textures" in dp or fn.startswith(gltf_name.split(".")[0])))
    print(f"ROOM {gltf_name}: tris={tris} (budget 45000) download~{size / 1e6:.1f}MB (budget 15MB)")
    return gl


def render_stamped(scene, cams, scene_id, out, res, cams_filter="", page=None, page_cams=(), exposure=None, default_exposure=0.0, captures_dir=""):
    """Stills labelled as Blender renders (file name and a stamp burnt into the image), for kits other than pride_kit
    (treasure_kit's render_cams has no stamp)."""
    import shutil
    exposure = exposure or {}
    scene.render.resolution_x = res; scene.render.resolution_y = int(res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    want = set(c.strip().lower() for c in cams_filter.split(",") if c.strip())
    spp = scene.cycles.samples; r = scene.render
    r.use_stamp = True
    for k in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time", "use_stamp_frame", "use_stamp_frame_range", "use_stamp_memory",
              "use_stamp_hostname", "use_stamp_camera", "use_stamp_lens", "use_stamp_scene", "use_stamp_marker", "use_stamp_filename",
              "use_stamp_sequencer_strip"):
        if hasattr(r, k): setattr(r, k, False)
    r.use_stamp_note = True; r.stamp_font_size = max(12, res // 90)
    r.stamp_foreground = (1, 1, 1, 0.85); r.stamp_background = (0, 0, 0, 0.35)
    paths = []
    for c in cams:
        view = c.name[4:].lower()
        if want and view not in want: continue
        scene.camera = c
        if page is not None: page.hide_render = c.name not in page_cams
        scene.view_settings.exposure = exposure.get(c.name, default_exposure)
        r.stamp_note_text = f"Blender render (Cycles {spp} spp) - {scene_id} - {view}"
        fn = f"blender-render_{scene_id}_{view}_cycles-{spp}spp.png"
        r.filepath = os.path.join(out, fn)
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:
            print("GPU render failed, retrying on CPU:", e); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", r.filepath, flush=True); paths.append(r.filepath)
        if captures_dir:
            os.makedirs(captures_dir, exist_ok=True); shutil.copy(r.filepath, os.path.join(captures_dir, fn))
    r.use_stamp = False
    return paths
