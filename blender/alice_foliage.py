"""
Fable: real trees, rose trees, shrubs and clipped hedges for Alice's outdoor rooms
(build_queens_croquet_ground.py, build_mad_tea_party.py).

The first-generation Alice rooms grew their foliage from displaced icospheres: on the headset the trees read as
green blobs. This module replaces them with the approach the newer rooms use (build_fields_to_netherfield.py,
build_horsell_sandpits.py, pride_kit.py, wotw_kit.py): a trunk that forks into limbs, branches and twigs grown to a
lobed crown envelope, and leaf-spray cards (numpy-painted RGBA atlases, alpha-tested, glTF alphaMode MASK) at the
branch ends and through the crown's outer shell, facing outwards, with rounded custom normals so the crown shades as a
volume. Clipped hedges are a gently uneven rounded block carrying a painted, tileable clipped-yew (or privet) leaf
texture, with short sprig cards standing out of the top and faces to break the clipped line.

Card meshes carry the living-scene sway weight (docs/LIVING_SCENES.md) in a 'sway' colour attribute, R channel:
0 at the root or trunk, 1 at the tip. Materials made here are tagged m["fable_image"] = 1: the rooms' bake step must
not re-UV or bake them (their painted atlases are exported as they are).

Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, os, shutil
import numpy as np
from mathutils import Vector, Matrix, noise
from pride_kit import Canvas

OUT = None
_LINK = None
IMAGE_MATS = set()


def init(out_dir, link_fn):
    """out_dir: the room's out/<id> (atlases go to out_dir/textures); link_fn: the room's link(obj) into its collection."""
    global OUT, _LINK
    OUT = out_dir; _LINK = link_fn


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------- images and materials
def np_image(name, arr):
    """arr: (H, W, 4) float 0-1 (sRGB picks), row 0 = top of the picture. Saved as PNG into OUT/textures and packed."""
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1].astype(np.float32)).ravel())
    d = os.path.join(OUT, "textures"); os.makedirs(d, exist_ok=True)
    img.filepath_raw = os.path.join(d, name + ".png"); img.file_format = 'PNG'; img.save(); img.pack()
    return img


def image_mat(name, img, rough=0.6, alpha=True, spec=0.22, translucency=0.0):
    """A material that reads its painted image directly through UVMap. alpha=True: clipped at 0.5 (glTF MASK)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (500, 0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.location = (200, 0)
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "UVMap"; uv.location = (-700, 0)
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; t.interpolation = 'Linear'; t.location = (-450, 0)
    nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = spec
    if translucency > 0:      # thin leaves let a little light through (render only)
        b.inputs["Subsurface Weight"].default_value = translucency
        b.inputs["Subsurface Radius"].default_value = (0.02, 0.03, 0.01)
    if alpha:
        r = nt.nodes.new("ShaderNodeMath"); r.operation = 'ROUND'; r.location = (-150, -250)
        nt.links.new(t.outputs["Alpha"], r.inputs[0]); nt.links.new(r.outputs[0], b.inputs["Alpha"])
    m.use_backface_culling = False
    m["fable_image"] = 1
    IMAGE_MATS.add(name)
    return m


def is_image_mat(m):
    return m is not None and (m.get("fable_image") or m.name.split("__")[0] in IMAGE_MATS or m.name.split(".")[0] in IMAGE_MATS)


# ----------------------------------------------------------------------------- painting: leaves, sprays and tiles
def _shade(c, k): return tuple(min(1.0, max(0.0, v * k)) for v in c[:3])


def _leaf(cv, x, y, b, L, W, col, tip=0.4, fold=0.86, rib=True, heart=False):
    """A leaf from its stalk end (x, y) pointing along angle b (0 = up the image, clockwise), length L, width W (px):
    the far half shaded darker along the midrib (a folded leaf catches light on one side), a pale midrib."""
    dx, dy = math.sin(b), -math.cos(b)
    cx, cy = x + dx * L * 0.5, y + dy * L * 0.5
    ang = b - math.pi / 2
    cv.ellipse(cx, cy, L * 0.5, W * 0.5, ang, col + (1.0,), soft=1.0, tip=tip)
    if heart:
        for sg in (-1, 1):
            cv.ellipse(x + dx * L * 0.18 + dy * sg * W * 0.22, y + dy * L * 0.18 - dx * sg * W * 0.22, L * 0.2, W * 0.28, ang, col + (1.0,))
    # the shaded half: a narrower ellipse pushed to one side
    px, py = -dy, dx
    cv.ellipse(cx + px * W * 0.16, cy + py * W * 0.16, L * 0.46, W * 0.3, ang, _shade(col, fold) + (1.0,), soft=1.0, tip=tip)
    if rib:
        cv.line((x + dx * L * 0.05, y + dy * L * 0.05), (x + dx * L * 0.85, y + dy * L * 0.85), 0.7, 0.3, _shade(col, 1.22) + (0.8,))


def _stem(cv, p0, p1, w0, w1, col):
    cv.line(p0, p1, w0, w1, col + (1.0,))


PALETTES = {
    # sRGB picks, from shaded to sunlit; a few with light coming through
    "rose": [(0.11, 0.21, 0.06), (0.14, 0.26, 0.07), (0.17, 0.30, 0.08), (0.20, 0.33, 0.09), (0.12, 0.23, 0.07), (0.24, 0.36, 0.10), (0.16, 0.27, 0.08)],
    "lime": [(0.20, 0.31, 0.09), (0.25, 0.37, 0.11), (0.30, 0.42, 0.13), (0.35, 0.47, 0.15), (0.22, 0.34, 0.10), (0.42, 0.52, 0.18), (0.28, 0.40, 0.12)],
    "beech": [(0.18, 0.29, 0.08), (0.23, 0.35, 0.10), (0.28, 0.40, 0.12), (0.33, 0.45, 0.13), (0.20, 0.31, 0.09), (0.38, 0.49, 0.16)],
    "oak": [(0.16, 0.26, 0.07), (0.21, 0.32, 0.09), (0.26, 0.37, 0.11), (0.31, 0.42, 0.13), (0.19, 0.29, 0.08), (0.36, 0.45, 0.15)],
    "yew": [(0.09, 0.17, 0.05), (0.12, 0.22, 0.07), (0.15, 0.26, 0.08), (0.18, 0.30, 0.09), (0.22, 0.35, 0.11)],
    "privet": [(0.11, 0.20, 0.06), (0.14, 0.25, 0.07), (0.17, 0.29, 0.08), (0.21, 0.33, 0.10), (0.13, 0.22, 0.07)],
}
BARK_COL = {"rose": (0.24, 0.20, 0.10), "lime": (0.22, 0.17, 0.12), "beech": (0.30, 0.28, 0.25), "oak": (0.20, 0.16, 0.11),
            "yew": (0.26, 0.15, 0.09), "privet": (0.22, 0.19, 0.13)}


def _spray(cv, x0, y0, x1, y1, R, kind):
    """One twig spray drawn into the cell (x0, y0)-(x1, y1), its stalk at the bottom middle (where the card's base is)."""
    W, H = x1 - x0, y1 - y0
    pal = PALETTES[kind]; bark = BARK_COL[kind]
    leaves = []
    stack = [((x0 + W * 0.5 + R.gauss(0, W * 0.04), y1 - 3), R.gauss(0, 0.18), H * 0.62, W * 0.012, 0)]
    maxdepth = {"rose": 2, "lime": 2, "beech": 2, "oak": 2, "yew": 2, "privet": 2}[kind]
    while stack:
        (x, y), a, L, w, depth = stack.pop()
        segs = 6; px, py = x, y
        for s in range(segs):
            a += R.gauss(0, 0.12)
            nx = min(max(px + math.sin(a) * L / segs, x0 + 8), x1 - 8); ny = min(max(py - math.cos(a) * L / segs, y0 + 8), y1 - 3)
            _stem(cv, (px, py), (nx, ny), max(0.8, w * (1 - s / segs * 0.6)), max(0.6, w * (1 - (s + 1) / segs * 0.6)), bark)
            leaves.append((nx, ny, a, depth, s / segs))
            if depth < maxdepth and s >= 1 and R.random() < (0.45 if kind != "yew" else 0.55):
                side = R.choice((-1, 1))
                stack.append(((nx, ny), a + side * R.uniform(0.45, 0.9), L * R.uniform(0.38, 0.6), w * 0.6, depth + 1))
            px, py = nx, ny
        leaves.append((px, py, a, depth, 1.0))
    sc = W / 512.0
    for (x, y, a, depth, t) in leaves:
        if kind == "yew":
            # two-ranked flat needles along the shoot: short, dark, a fresh pale tip
            for sg in (-1, 1):
                b = a + sg * R.uniform(1.05, 1.35)
                ln = R.uniform(15, 22) * sc * (0.75 if t > 0.85 else 1.0)
                col = R.choice(pal) if t < 0.8 or R.random() < 0.5 else (0.24, 0.36, 0.10)
                cv.line((x, y), (x + math.sin(b) * ln, y - math.cos(b) * ln), 2.2 * sc + 0.6, 1.4 * sc + 0.4, _shade(col, R.uniform(0.85, 1.15)) + (1.0,))
            continue
        if kind == "rose":
            # pinnate leaves at alternate nodes: a stalk and five leaflets (a terminal one and two pairs)
            if R.random() < 0.3: continue
            side = R.choice((-1, 1)); b = a + side * R.uniform(0.55, 1.0)
            pl = R.uniform(46, 64) * sc
            ex, ey = x + math.sin(b) * pl, y - math.cos(b) * pl
            _stem(cv, (x, y), (ex, ey), 1.4 * sc + 0.4, 0.8 * sc + 0.3, (0.22, 0.24, 0.09))
            col = R.choice(pal); k = R.uniform(0.85, 1.15); col = _shade(col, k)
            if R.random() < 0.05: col = (0.34, 0.24, 0.12)          # young growth, red-bronze
            lf = R.uniform(26, 34) * sc
            _leaf(cv, ex, ey, b + R.gauss(0, 0.15), lf, lf * 0.62, col, tip=0.35)
            for j, f in enumerate((0.45, 0.85)):
                qx, qy = x + math.sin(b) * pl * f, y - math.cos(b) * pl * f
                for sg in (-1, 1):
                    _leaf(cv, qx, qy, b + sg * R.uniform(0.9, 1.25), lf * (0.88 - 0.1 * j), lf * 0.55, _shade(col, R.uniform(0.9, 1.08)), tip=0.35)
            continue
        # broadleaf: a few leaves per node on short stalks, larger where the shoot is old
        nper = {"lime": 2, "beech": 3, "oak": 3, "privet": 2}[kind]
        size = {"lime": 30, "beech": 22, "oak": 26, "privet": 13}[kind] * sc * 512.0 / 512.0
        if kind == "privet":
            for sg in (-1, 1):       # opposite pairs
                b = a + sg * R.uniform(0.7, 1.1); s_ = size * R.uniform(0.8, 1.2)
                _leaf(cv, x, y, b, s_, s_ * 0.48, _shade(R.choice(pal), R.uniform(0.85, 1.15)), tip=0.25, rib=False)
            continue
        for k in range(nper):
            if R.random() < 0.3: continue
            b = a + R.gauss(0, 1.0); d = R.uniform(2, size * 0.45)
            lx, ly = x + math.sin(b) * d, y - math.cos(b) * d
            if not (x0 + 6 < lx < x1 - 6 and y0 + 6 < ly < y1 - 6): continue
            s_ = size * R.uniform(0.75, 1.25)
            col = _shade(R.choice(pal), R.uniform(0.82, 1.15))
            if kind == "oak":
                _leaf(cv, lx, ly, b, s_, s_ * 0.42, col, tip=0.2)
                for j in range(3):
                    t2 = 0.25 + j * 0.22; ox, oy = lx + math.sin(b) * s_ * t2, ly - math.cos(b) * s_ * t2
                    for sg in (-1, 1):
                        cv.ellipse(ox + math.cos(b) * sg * s_ * 0.17, oy + math.sin(b) * sg * s_ * 0.17, s_ * 0.13, s_ * 0.1, b, col + (1.0,))
            else:
                _leaf(cv, lx, ly, b, s_, s_ * (0.78 if kind == "lime" else 0.6), col, tip=0.45 if kind == "lime" else 0.35, heart=(kind == "lime"))


QUAD = [(0.0, 0.5, 0.5, 1.0), (0.5, 0.5, 1.0, 1.0), (0.0, 0.0, 0.5, 0.5), (0.5, 0.0, 1.0, 0.5)]   # 2x2 atlas cells (u0, v0, u1, v1)


def spray_atlas(name, kind, seed, S=1024, per_cell=3):
    """A 2 x 2 atlas of leaf sprays of one kind (each cell a different spray), colour bled into the clear texels."""
    cv = Canvas(S, S); R = random.Random(seed); h = S // 2
    for (cx, cy) in ((0, 0), (h, 0), (0, h), (h, h)):
        cv.clip = (cx + 1, cy + 1, cx + h - 1, cy + h - 1)
        for k in range(per_cell):
            _spray(cv, cx + 4, cy + 4, cx + h - 4, cy + h - 4, R, kind)
    cv.clip = None; cv.bleed(6)
    return np_image(name, cv.a)


def treeline_atlas(name, seed, S=1024, pal=None):
    """A 2 x 2 atlas of distant tree-line silhouettes (a few overlapping crowns per cell, built from thousands of small
    leaf clusters, sunlit at the top, shaded below), filling to the cell's bottom edge so a card can stand on an
    opaque wooded band and break its top line into tree crowns."""
    R = random.Random(seed); cv = Canvas(S, S); h = S // 2
    pal = pal or [(0.27, 0.37, 0.19), (0.32, 0.42, 0.22), (0.37, 0.47, 0.25), (0.43, 0.52, 0.29), (0.50, 0.58, 0.34)]
    for (cx, cy) in ((0, 0), (h, 0), (0, h), (h, h)):
        cv.clip = (cx + 1, cy + 1, cx + h - 1, cy + h - 1)
        crowns = []
        for k in range(R.randint(2, 4)):
            w = R.uniform(0.25, 0.45) * h; t = R.uniform(0.35, 0.85) * h
            crowns.append((cx + R.uniform(0.15, 0.85) * h, cy + h - t + w * 0.55, w, w * R.uniform(0.75, 1.0)))
        crowns.append((cx + h * 0.5, cy + h * 1.0, h * 0.7, h * 0.32))       # the wood below, to the bottom edge
        for (ex, ey, rx, ry) in crowns:
            for i in range(int(rx * ry * 0.09)):
                a = R.uniform(0, 2 * math.pi); d = math.sqrt(R.random())
                d *= 1.0 + 0.18 * math.sin(a * 5 + ex) + 0.1 * math.sin(a * 11 + ey)
                x, y = ex + math.cos(a) * rx * d, ey + math.sin(a) * ry * d
                lit = max(0.0, min(1.0, 0.55 - (y - ey) / (ry * 1.6) + (x - ex) / (rx * 4) + R.gauss(0, 0.15)))
                col = pal[min(len(pal) - 1, int(lit * len(pal)))]
                r_ = R.uniform(2.5, 5.0) * S / 1024
                cv.ellipse(x, y, r_, r_ * R.uniform(0.6, 1.0), R.uniform(0, 3.14), _shade(col, R.uniform(0.9, 1.1)) + (1.0,))
    cv.clip = None; cv.bleed(6)
    return np_image(name, cv.a)


def leaf_tile(name, kind, seed, S=1024):
    """An opaque, tileable texture of a clipped hedge's face: layer on layer of short shoots, darker in the depth,
    fresher and paler at the clipped surface (kind 'yew' or 'privet'). One tile spans TILE_M metres."""
    R = random.Random(seed)
    cv = Canvas(S, S, bg=(0.035, 0.07, 0.025, 1.0))
    pal = PALETTES[kind]
    layers = [(0.5, 900), (0.7, 900), (0.9, 900), (1.1, 800), (1.3, 260)]
    for li, (bright, n) in enumerate(layers):
        for i in range(n):
            x, y = R.uniform(0, S), R.uniform(0, S); a = R.uniform(0, 2 * math.pi)
            for ox in (-S, 0, S):
                for oy in (-S, 0, S):
                    if not (-40 < x + ox < S + 40 and -40 < y + oy < S + 40): continue
                    _tile_shoot(cv, x + ox, y + oy, a, kind, pal, bright, random.Random(li * 100000 + i), li == len(layers) - 1)
    a = cv.a
    # a broad, faint mottle (clipping unevenness), made tileable by building it from whole sine periods
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S * 2 * math.pi
    m = 1.0 + 0.06 * np.sin(xx * 2 + 1.3) * np.sin(yy * 3 + 0.4) + 0.05 * np.sin(xx * 5 + yy * 3 + 2.0)
    a[..., :3] *= m[..., None]
    a[..., 3] = 1.0
    return np_image(name, np.clip(a, 0, 1))


def _tile_shoot(cv, x, y, a, kind, pal, bright, R, top):
    L = R.uniform(28, 46); segs = 4; px, py = x, y
    for s in range(segs):
        a += R.gauss(0, 0.15)
        nx, ny = px + math.sin(a) * L / segs, py - math.cos(a) * L / segs
        if kind == "yew":
            for sg in (-1, 1):
                for q in (0.0, 0.5):
                    qx, qy = px + (nx - px) * q, py + (ny - py) * q
                    b = a + sg * R.uniform(1.0, 1.4); ln = R.uniform(9, 13)
                    col = _shade(R.choice(pal), bright * R.uniform(0.85, 1.15))
                    if top and s == segs - 1: col = _shade((0.22, 0.34, 0.09), R.uniform(0.9, 1.15))
                    cv.line((qx, qy), (qx + math.sin(b) * ln, qy - math.cos(b) * ln), 1.6, 1.0, col + (1.0,))
        else:
            for sg in (-1, 1):
                b = a + sg * R.uniform(0.7, 1.1); s_ = R.uniform(11, 16)
                col = _shade(R.choice(pal), bright * R.uniform(0.85, 1.15))
                _leaf(cv, nx, ny, b, s_, s_ * 0.5, col, tip=0.25, rib=False)
        px, py = nx, ny


# ----------------------------------------------------------------------------- mesh builder
class MB:
    """Many small parts in one object: positions, faces, per-corner UVs and a per-vertex sway weight (written to the
    'sway' colour attribute, R; G and B 1), all in world space."""
    def __init__(self):
        self.v = []; self.f = []; self.uv = []; self.w = []; self.n = []

    def vert(self, p, uv=(0, 0), sway=0.0, nrm=None):
        self.v.append(tuple(p)); self.uv.append(tuple(uv)); self.w.append(sway); self.n.append(nrm); return len(self.v) - 1

    def face(self, *idx): self.f.append(tuple(idx))

    def build(self, name, mat, sway=True, normals=None, smooth=True):
        """normals: fn(world pos) -> shading normal (custom split normals), or None."""
        if not self.f: return None
        me = bpy.data.meshes.new(name); me.from_pydata(self.v, [], self.f); me.update()
        uvl = me.uv_layers.new(name="UVMap")
        lv = np.zeros(len(me.loops), np.int64); me.loops.foreach_get("vertex_index", lv)
        uva = np.array(self.uv, np.float32)[lv]; uvl.data.foreach_set("uv", uva.ravel())
        if sway:
            ca = me.color_attributes.new("sway", 'BYTE_COLOR', 'POINT')
            col = np.ones((len(self.v), 4), np.float32); col[:, 0] = np.clip(np.array(self.w, np.float32), 0, 1)
            ca.data.foreach_set("color", col.ravel())
            me.color_attributes.active_color = ca; me.color_attributes.render_color_index = 0
        o = bpy.data.objects.new(name, me); me.materials.append(mat)
        if smooth:
            for p in me.polygons: p.use_smooth = True
        if normals is not None:
            me.normals_split_custom_set_from_vertices([tuple(normals(Vector(v))) for v in self.v])
        return _LINK(o)


def tube(mb, pts, radii, sides=6, uv_v=0.0):
    """A tube along a polyline into mb (parallel-transported frames, open ends)."""
    pts = [Vector(p) for p in pts]
    if len(pts) < 2: return
    rings = []; u_prev = None
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
        if d.length < 1e-6: d = Vector((0, 0, 1))
        d.normalize()
        if u_prev is None:
            ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
            u = d.cross(ref).normalized()
        else:
            u = (u_prev - d * u_prev.dot(d)); u = u.normalized() if u.length > 1e-6 else d.orthogonal().normalized()
        v = d.cross(u); u_prev = u
        r = radii[i]
        rings.append([mb.vert(p + (u * math.cos(2 * math.pi * k / sides) + v * math.sin(2 * math.pi * k / sides)) * r, (k / sides, i)) for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            mb.face(a[k], a[j], b[j], b[k])


def card(mb, base, right, up, cell, sway0, sway1, bend=None, segs=1):
    """An atlas card from its base centre, spanning right (full width) and up (height). cell = (u0, v0, u1, v1)."""
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


def put_card(mb, R, q, out, sz, sway0, sway1, cells=QUAD, aspect=1.0, lift=(0.2, 0.5)):
    """A card at q roughly facing `out`: turned at random about it, tipped outwards a little, its middle at q."""
    out = Vector(out).normalized()
    tang = out.cross(Vector((0, 0, 1)))
    if tang.length < 0.1: tang = Vector((1, 0, 0))
    tang.normalize(); bit = out.cross(tang).normalized(); roll = R.uniform(-math.pi, math.pi)
    right = (tang * math.cos(roll) + bit * math.sin(roll)) * sz * aspect
    up = (bit * math.cos(roll) - tang * math.sin(roll)) * sz + out * sz * R.uniform(*lift)
    card(mb, Vector(q) - up * 0.5, right, up, R.choice(cells), sway0, sway1)


# ----------------------------------------------------------------------------- trees
class Crown:
    """A crown envelope made of ellipsoid lobes: [(centre, (ax, ay, az))]."""
    def __init__(self, lobes):
        self.lobes = [(Vector(c), Vector(r)) for c, r in lobes]
        self.centre = sum((c for c, _ in self.lobes), Vector()) / len(self.lobes)

    def f(self, p):
        """< 1 inside the envelope."""
        return min(Vector(((p.x - c.x) / r.x, (p.y - c.y) / r.y, (p.z - c.z) / r.z)).length for c, r in self.lobes)

    def nearest(self, p):
        best = None
        for c, r in self.lobes:
            k = Vector(((p.x - c.x) / r.x, (p.y - c.y) / r.y, (p.z - c.z) / r.z)).length
            if best is None or k < best[0]: best = (k, c, r)
        return best

    def normal(self, p):
        k, c, r = self.nearest(p)
        g = Vector(((p.x - c.x) / (r.x * r.x), (p.y - c.y) / (r.y * r.y), (p.z - c.z) / (r.z * r.z)))
        return g.normalized() if g.length > 1e-6 else Vector((0, 0, 1))

    def shell_point(self, R, k0=0.85, k1=1.02, min_el=-0.5, lobe=None):
        """A random point between k0 and k1 of a lobe's radii (on the outside of the union), weighted by lobe size."""
        for _ in range(60):
            if lobe is None:
                c, r = R.choices(self.lobes, weights=[r.x * r.y + r.z * r.x for _, r in self.lobes])[0]
            else:
                c, r = self.lobes[lobe]
            d = Vector((R.gauss(0, 1), R.gauss(0, 1), R.gauss(0, 1))).normalized()
            if d.z < min_el: continue
            k = R.uniform(k0, k1)
            p = c + Vector((d.x * r.x, d.y * r.y, d.z * r.z)) * k
            # keep it on the outer surface of the union: not deep inside another lobe
            if any(Vector(((p.x - c2.x) / r2.x, (p.y - c2.y) / r2.y, (p.z - c2.z) / r2.z)).length < k0 * 0.92 for c2, r2 in self.lobes if c2 is not c):
                continue
            return p
        return c + Vector((0, 0, r.z))


def auto_crown(R, top, height_above, spread, nlobes=5, flat=0.75, offset=(0.0, 0.0)):
    """A clumpy crown: a main ellipsoid and nlobes smaller ones set into its upper surface."""
    c0 = top + Vector((offset[0], offset[1], height_above * 0.48))
    a = spread; c = height_above * 0.5
    lobes = [(c0, (a * 0.8, a * 0.8, c * 0.78))]
    for i in range(nlobes):
        az = 2 * math.pi * (i + R.uniform(-0.3, 0.3)) / nlobes; el = R.uniform(-0.1, 0.75)
        q = c0 + Vector((math.cos(az) * math.cos(el) * a * 0.55, math.sin(az) * math.cos(el) * a * 0.55, math.sin(el) * c * 0.5))
        rr = a * R.uniform(0.42, 0.55)
        lobes.append((q, (rr, rr, rr * flat)))
    lobes.append((c0 + Vector((0, 0, c * 0.45)), (a * 0.45, a * 0.45, c * 0.5)))
    return Crown(lobes)


def grow_tree(name, R, base, crown, bark, leaves, trunk_top, r0, nlimbs=6, limbs=None, detail=1.0, card_size=1.2,
              cards_per_tip=2, fill=60, flare=True, sag=0.06, wob=0.12, card_lift=(0.2, 0.5), sway0=0.3, twig_k=1.0,
              branch_per_limb=4, facing=None, trunk=True, limb_sides=None):
    """A trunk from base to trunk_top (radius r0 at the foot), limbs out to the crown's lobes (or the given limbs:
    [(start, end, r_start, r_end)]), branches off each limb to the envelope, twigs, then leaf-spray cards at the branch
    ends and through the crown's shell. facing = (point, min_dot): leave out the cards on the far side of the crown
    from that point (the side the reader can never see; they would only add hidden alpha-tested overdraw).
    Returns (bark object, crown object, tips)."""
    def hidden(q, out):
        if facing is None: return False
        v = Vector(facing[0]) - q; v.z = 0
        return v.length > 1e-3 and out.dot(v.normalized()) < facing[1]
    base = Vector(base); trunk_top = Vector(trunk_top)
    bm = MB(); cm = MB(); tips = []

    def bent(p0, p1, sg, n, wb):
        pts = []
        for i in range(n + 1):
            t = i / n; q = p0.lerp(p1, t)
            q.z -= sg * math.sin(math.pi * t) * (p1 - p0).length
            if 0 < i < n: q += Vector((R.gauss(0, wb), R.gauss(0, wb), R.gauss(0, wb * 0.6)))
            pts.append(q)
        return pts

    # trunk: a slightly wandering column, flared at the foot
    H = (trunk_top - base).length
    tp = [base + (trunk_top - base) * t + (Vector((R.gauss(0, 1), R.gauss(0, 1), 0)) * r0 * 0.6 if 0 < t < 1 else Vector()) for t in (0.0, 0.08, 0.35, 0.7, 1.0)]
    tp[0] = tp[0] - Vector((0, 0, 0.2))
    if trunk: tube(bm, tp, [r0 * 1.35, r0 * 1.12, r0, r0 * 0.9, r0 * 0.78], 9 if detail >= 1 else 7)
    if flare and trunk:
        for k in range(5 if detail >= 1 else 3):
            a = 2 * math.pi * k / (5 if detail >= 1 else 3) + R.uniform(-0.3, 0.3); d = Vector((math.cos(a), math.sin(a), 0))
            tube(bm, [base + d * r0 * 0.4 + Vector((0, 0, r0 * 3.2)), base + d * r0 * 1.5 + Vector((0, 0, r0 * 0.6)), base + d * r0 * 2.6 - Vector((0, 0, 0.08))],
                 [r0 * 0.5, r0 * 0.42, r0 * 0.12], 5)
    # limbs
    if limbs is None:
        limbs = []
        lob = crown.lobes[1:] if len(crown.lobes) > 2 else crown.lobes
        for i in range(nlimbs):
            c, r = lob[i % len(lob)]
            d = Vector((R.gauss(0, 1), R.gauss(0, 1), abs(R.gauss(0, 0.6)))).normalized()
            end = c + Vector((d.x * r.x, d.y * r.y, d.z * r.z)) * 0.5
            start = tp[-2].lerp(tp[-1], R.uniform(0.25, 1.0))
            limbs.append((start, end, r0 * R.uniform(0.5, 0.65), r0 * 0.18))
    for (start, end, rs, re) in limbs:
        start = Vector(start); end = Vector(end)
        lp = bent(start, end, sag, 4, wob)
        rl = [rs + (re - rs) * (k / 4) for k in range(5)]
        tube(bm, lp, rl, limb_sides or (7 if detail >= 1 else 5))
        dlimb = (end - start).normalized()
        tips.append((lp[-1], dlimb))
        # branches from the limb's outer part to points on the envelope near its direction
        for j in range(branch_per_limb):
            k = R.randint(2, 4); bp = lp[k]
            out = crown.normal(end)
            dirn = (dlimb * 0.6 + out * 0.8 + Vector((R.gauss(0, 0.5), R.gauss(0, 0.5), R.gauss(0, 0.35)))).normalized()
            # march out along dirn to the envelope surface
            L = 0.0; q = bp.copy()
            while crown.f(q) < R.uniform(0.92, 1.0) and L < 12.0:
                L += 0.1; q = bp + dirn * L
            if L < 0.25: continue
            bpts = bent(bp, q, sag * 0.5, 3, wob * 0.35)
            br = [rl[k] * 0.55 * (1 - 0.7 * s / 3) for s in range(4)]
            if detail >= 0.6: tube(bm, bpts, br, 5 if detail >= 1 else 3)
            tips.append((bpts[-1], dirn))
            tips.append((bpts[2] + Vector((R.gauss(0, 0.15), R.gauss(0, 0.15), R.gauss(0, 0.1))) * L, dirn))
            if detail >= 1:
                for t_ in range(int(2 * twig_k + R.random())):
                    tw0 = bpts[R.randint(1, 3)]
                    tw1 = tw0 + (dirn + Vector((R.gauss(0, 0.6), R.gauss(0, 0.6), R.gauss(0, 0.4) + 0.2))).normalized() * L * R.uniform(0.2, 0.4)
                    tube(bm, [tw0, tw0.lerp(tw1, 0.5), tw1], [br[1] * 0.45, br[1] * 0.28, 0.006], 3)
                    tips.append((tw1, dirn))
    bark_o = bm.build(name + "_Bark", bark, sway=False)
    # leaf cards: at the tips, then through the shell
    for (q, d) in tips:
        for c in range(int(cards_per_tip + R.random())):
            out = (crown.normal(q) * 1.0 + d * 0.4 + Vector((R.gauss(0, 0.4), R.gauss(0, 0.4), R.gauss(0, 0.3)))).normalized()
            p = q + out * card_size * R.uniform(-0.1, 0.3)
            if crown.f(p) > 1.12: p = q
            if hidden(p, out): continue
            put_card(cm, R, p, out, card_size * R.uniform(0.75, 1.2), sway0, 1.0, lift=card_lift)
    for i in range(fill):
        q = crown.shell_point(R, 0.72, 1.0, -0.45)
        out = (crown.normal(q) + Vector((R.gauss(0, 0.35), R.gauss(0, 0.35), R.gauss(0, 0.3)))).normalized()
        if hidden(q, out): continue
        put_card(cm, R, q, out, card_size * R.uniform(0.75, 1.15), sway0, 1.0, lift=card_lift)
    nrm = lambda p: (crown.normal(p) + Vector((0, 0, 0.55))).normalized()
    crown_o = cm.build(name + "_Crown", leaves, sway=True, normals=nrm)
    return bark_o, crown_o, tips


# ----------------------------------------------------------------------------- rose standards and rose bushes
def rose_head(name, R, graft, crown, bark, leaves, ncanes=14, card_size=0.36, cards_per_cane=5, fill=40, cane_r=0.016, sway0=0.25,
              bloom_sites=40, sway=True, shoots=2, cane_sides=4):
    """A rose head: canes springing from the graft, arching out to the envelope, side shoots, rose-leaf sprays along
    their outer half and through the shell. Returns (bark object, crown object, bloom sites [(pos, outward normal)])."""
    grafts = [Vector(g) for g in graft] if isinstance(graft, (list, tuple)) and len(graft) and hasattr(graft[0], "__len__") else [Vector(graft)]
    bm = MB(); cm = MB(); sites = []
    for i in range(ncanes):
        graft = grafts[i % len(grafts)]
        az = 2 * math.pi * (i + R.uniform(-0.35, 0.35)) / ncanes
        el = R.uniform(-0.15, 0.95)
        d = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
        end = crown.shell_point(R, 0.9, 1.0, -0.3)
        # arch: rises steeply from the graft, then bends over to the end point
        mid = graft.lerp(end, 0.45) + Vector((0, 0, (end - graft).length * 0.28))
        pts = [graft + Vector((R.gauss(0, 0.01), R.gauss(0, 0.01), 0.0)), graft.lerp(mid, 0.5) + Vector((R.gauss(0, 0.03), R.gauss(0, 0.03), 0.02)), mid, mid.lerp(end, 0.55) + Vector((0, 0, 0.03)), end]
        rr = [cane_r, cane_r * 0.85, cane_r * 0.65, cane_r * 0.45, cane_r * 0.25]
        tube(bm, pts, rr, cane_sides)
        sites.append((end, crown.normal(end)))
        # side shoots from the upper part of the cane
        for j in range(shoots):
            s0 = pts[R.randint(2, 3)]
            s1 = crown.shell_point(R, 0.88, 1.0, -0.4)
            if (s1 - s0).length > 0.6: s1 = s0 + (s1 - s0).normalized() * 0.6
            tube(bm, [s0, s0.lerp(s1, 0.5) + Vector((0, 0, 0.04)), s1], [cane_r * 0.45, cane_r * 0.32, cane_r * 0.15], 3)
            sites.append((s1, crown.normal(s1)))
            for c in range(2):
                q = s0.lerp(s1, R.uniform(0.5, 1.0))
                put_card(cm, R, q, (crown.normal(q) + Vector((R.gauss(0, 0.4), R.gauss(0, 0.4), 0.2))).normalized(), card_size * R.uniform(0.75, 1.15), sway0, 1.0, lift=(0.15, 0.4))
        for c in range(cards_per_cane):
            t = R.uniform(0.4, 1.0); k = min(3, int(t * 4)); q = pts[k].lerp(pts[k + 1], t * 4 - k)
            put_card(cm, R, q, (crown.normal(q) + Vector((R.gauss(0, 0.45), R.gauss(0, 0.45), 0.25))).normalized(), card_size * R.uniform(0.75, 1.2), sway0, 1.0, lift=(0.15, 0.4))
    for i in range(fill):
        q = crown.shell_point(R, 0.6 if i % 3 == 0 else 0.8, 1.0, -0.5)
        put_card(cm, R, q, (crown.normal(q) + Vector((R.gauss(0, 0.3), R.gauss(0, 0.3), 0.15))).normalized(), card_size * R.uniform(0.8, 1.15), sway0, 1.0, lift=(0.15, 0.4))
    while len(sites) < bloom_sites:
        q = crown.shell_point(R, 0.93, 1.03, -0.55); sites.append((q, crown.normal(q)))
    nrm = lambda p: (crown.normal(p) + Vector((0, 0, 0.5))).normalized()
    return bm.build(name + "_Canes", bark, sway=False), cm.build(name + "_Sprays", leaves, sway=sway, normals=nrm), sites


# ----------------------------------------------------------------------------- clipped hedges
def _rounded(p, c, h, r):
    """Project a point on the box (centre c, half sizes h) onto the box with rounded edges of radius r; also the normal."""
    d = p - c
    inner = Vector((max(0.0, h.x - r), max(0.0, h.y - r), max(0.0, h.z - r)))
    q = Vector((max(-inner.x, min(inner.x, d.x)), max(-inner.y, min(inner.y, d.y)), max(-inner.z, min(inner.z, d.z))))
    n = d - q
    n = n.normalized() if n.length > 1e-6 else Vector((0, 0, 1))
    return c + q + n * r, n


def clipped_block(mb, size, centre, seed, tile=1.0, round_r=0.14, step=0.3, amp=0.03, batter=0.04, bottom=0.0, sway=False):
    """A clipped hedge block into mb: a box (size, its base centre at `centre`) with rounded edges, a slight batter
    (narrower at the top), and a gentle unevenness of the clipping along the surface normal. UVs are box-projected
    in metres / tile (for a tileable leaf texture). The bottom face is left open (it stands on the lawn)."""
    sx, sy, sz = size; c = Vector(centre) + Vector((0, 0, sz / 2)); h = Vector((sx / 2, sy / 2, sz / 2))
    o = Vector((seed * 1.37, seed * 0.71, seed * 2.11))
    faces = [(Vector((1, 0, 0)), 'Y', 'Z'), (Vector((-1, 0, 0)), 'Y', 'Z'), (Vector((0, 1, 0)), 'X', 'Z'), (Vector((0, -1, 0)), 'X', 'Z'), (Vector((0, 0, 1)), 'X', 'Y')]
    ax = {'X': Vector((1, 0, 0)), 'Y': Vector((0, 1, 0)), 'Z': Vector((0, 0, 1))}
    for (n0, ua, va) in faces:
        U = ax[ua]; V = ax[va]
        lu = h.dot(U) * 2; lv = h.dot(V) * 2
        nu = max(2, int(math.ceil(lu / step))); nv = max(2, int(math.ceil(lv / step)))
        grid = []
        for j in range(nv + 1):
            row = []
            for i in range(nu + 1):
                p = c + n0 * h.dot(Vector((abs(n0.x), abs(n0.y), abs(n0.z)))) + U * (-lu / 2 + lu * i / nu) + V * (-lv / 2 + lv * j / nv)
                p, nn = _rounded(p, c, h, round_r)
                zf = (p.z - (c.z - h.z)) / (2 * h.z)
                p = p + Vector((nn.x, nn.y, 0)) * (-batter * zf)
                if p.z > c.z - h.z + 0.02:
                    p = p + nn * amp * (noise.noise(p * 1.3 + o) + 0.5 * noise.noise(p * 3.1 + o))
                else:
                    p.z = c.z - h.z - bottom
                # box-projected UVs, one projection per side (so the rounded edges do not smear the texture)
                if n0.z > 0.5: uv = (p.x / tile, p.y / tile)
                elif abs(n0.x) > 0.5: uv = (p.y / tile, p.z / tile)
                else: uv = (p.x / tile, p.z / tile)
                row.append(mb.vert(p, uv, 0.0, nn))
            grid.append(row)
        for j in range(nv):
            for i in range(nu):
                a, b_, cc, d = grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]
                # wind the quad to face outwards
                pa, pb, pc = Vector(mb.v[a]), Vector(mb.v[b_]), Vector(mb.v[cc])
                if (pb - pa).cross(pc - pa).dot(n0) >= 0: mb.face(a, b_, cc, d)
                else: mb.face(a, d, cc, b_)
    return c, h


def build_hedge_mesh(name, mb, mat):
    """Build a clipped-hedge MB into an object: merge the coincident grid edges, smooth, outward normals."""
    if not mb.f: return None
    me = bpy.data.meshes.new(name); me.from_pydata(mb.v, [], mb.f); me.update()
    uvl = me.uv_layers.new(name="UVMap")
    lv = np.zeros(len(me.loops), np.int64); me.loops.foreach_get("vertex_index", lv)
    uva = np.array(mb.uv, np.float32)[lv]; uvl.data.foreach_set("uv", uva.ravel())
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.004)
    for f in bm.faces: f.smooth = True
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return _LINK(o)


def hedge_sprigs(mb, R, c, h, density_faces, top_density, size=(0.2, 0.34), faces=("+x", "-x", "+y", "-y"), sway=(0.1, 0.45), out_tilt=(0.25, 0.6),
                 skip=None):
    """Short sprig cards standing out of a clipped block (centre c, half sizes h): `top_density` per metre along the
    top edges and spread over the top, `density_faces` per m2 on the listed faces, so the clipped line is broken."""
    sides = {"+x": Vector((1, 0, 0)), "-x": Vector((-1, 0, 0)), "+y": Vector((0, 1, 0)), "-y": Vector((0, -1, 0))}
    for f in faces:
        n = sides[f]; U = Vector((abs(n.y), abs(n.x), 0))
        lu = abs(h.dot(U)) * 2; area = lu * h.z * 2
        for i in range(int(area * density_faces + R.random())):
            u = R.uniform(-0.5, 0.5) * lu; zf = R.uniform(0.12, 0.97) ** 0.7
            p = c + n * abs(h.dot(Vector((abs(n.x), abs(n.y), 0)))) + U * u + Vector((0, 0, -h.z + zf * 2 * h.z))
            if skip and skip(p): continue
            p, nn = _rounded(p, c, h, 0.14)
            out = (nn + Vector((R.gauss(0, 0.3), R.gauss(0, 0.3), R.uniform(0.1, 0.6)))).normalized()
            sz = R.uniform(*size)
            put_card(mb, R, p + nn * sz * 0.15, out, sz, sway[0], sway[1], lift=out_tilt)
        # the top edge on this side: sprigs leaning up and out
        for i in range(int(lu * top_density + R.random())):
            u = R.uniform(-0.5, 0.5) * lu
            p = c + n * abs(h.dot(Vector((abs(n.x), abs(n.y), 0)))) + U * u + Vector((0, 0, h.z))
            if skip and skip(p): continue
            p, nn = _rounded(p, c, h, 0.14)
            out = (nn * 0.7 + Vector((0, 0, 1)) + Vector((R.gauss(0, 0.3), R.gauss(0, 0.3), 0))).normalized()
            sz = R.uniform(*size)
            put_card(mb, R, p, out, sz, sway[0], sway[1], lift=out_tilt)
    top = h.x * h.y * 4
    for i in range(int(top * top_density * 0.6 + R.random())):
        p = c + Vector((R.uniform(-h.x, h.x) * 0.85, R.uniform(-h.y, h.y) * 0.85, h.z))
        if skip and skip(p): continue
        out = (Vector((R.gauss(0, 0.35), R.gauss(0, 0.35), 1))).normalized()
        sz = R.uniform(*size)
        put_card(mb, R, p, out, sz, sway[0], sway[1], lift=out_tilt)


# ----------------------------------------------------------------------------- stills
def render_stills(scene, cams, scene_id, out_dir, res, captures_dir="", want=(), before=None, after=None):
    """Every still is labelled a Blender render, in its file name and in a stamp burnt into the image."""
    scene.render.resolution_x = res; scene.render.resolution_y = int(res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    spp = scene.cycles.samples
    r = scene.render
    r.use_stamp = True
    for k in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time", "use_stamp_frame", "use_stamp_frame_range", "use_stamp_memory",
              "use_stamp_hostname", "use_stamp_camera", "use_stamp_lens", "use_stamp_scene", "use_stamp_marker", "use_stamp_filename",
              "use_stamp_sequencer_strip", "use_stamp_note"):
        if hasattr(r, k): setattr(r, k, False)
    r.use_stamp_note = True; r.stamp_font_size = max(12, res // 90)
    r.stamp_foreground = (1, 1, 1, 0.85); r.stamp_background = (0, 0, 0, 0.35)
    paths = []
    for c in cams:
        view = c.name[4:].lower()
        if want and view not in want: continue
        if before: before(c)
        scene.camera = c
        r.stamp_note_text = f"Blender render (Cycles {spp} spp) - {scene_id} - {view}"
        fn = f"blender-render_{scene_id}_{view}_cycles-{spp}spp.png"
        r.filepath = os.path.join(out_dir, fn)
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:
            print("GPU render failed, retrying on CPU:", e); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        if after: after(c)
        print("rendered", r.filepath, flush=True)
        paths.append(r.filepath)
        if captures_dir:
            os.makedirs(captures_dir, exist_ok=True); shutil.copy(r.filepath, os.path.join(captures_dir, fn))
    r.use_stamp = False
    return paths


def strip_colours(objs, keep=lambda o: False):
    """Remove colour attributes from meshes that are not living-scene foliage (glTF COLOR_0 would tint them)."""
    for o in objs:
        if o.type != 'MESH' or keep(o): continue
        for an in [a.name for a in o.data.color_attributes]:
            o.data.color_attributes.remove(o.data.color_attributes[an])
