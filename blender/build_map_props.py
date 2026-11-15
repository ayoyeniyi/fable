"""
Fable: map props for Peek on a fictional place (docs/MAP_PROPS.md).

  scroll                       root empty, origin at the centre of the map sheet
    scroll.sheet               the parchment map sheet: a 1.0 x 1.0 design mesh (64 x 40 grid, smooth normals, gentle
                               belly and curling free edges), node scale (W, H, 1); its base-colour texture is the map
    scroll.roller.left/right   the parchment wound on each roller: a unit-height roll, origin at the sheet edge where the
                               sheet leaves the roll, node scale (1, H, 1)
    scroll.finial.<side>.<end> turned walnut handles with a brass ring, origin at the roll end on the roll axis
  pin                          a map pin (glass head, brass needle), origin at the needle tip, pointing down -Y (glTF)
  globe.stand                  a brass meridian ring on a turned walnut stand for a 0.18 m sphere (sphere not included)
    globe.stand.axis           empty at the sphere centre whose local +Y (glTF) is the tilted spin axis

Blender axes: metres, +Z up, the reader stands at -Y looking +Y (the sheet faces -Y). The glTF exporter turns this into
+Y up with the sheet facing +Z.

Every texture is painted procedurally here with numpy (no downloaded assets):
  textures/map_placeholder.png   test map on parchment (red corner = image top-left, green = top-right, blue = bottom-left)
  textures/scroll_edge_mask.png  multiply mask for the sheet (RGB darkening, A = ragged edge cut-out); not bound in the glTF
  textures/walnut.png            dark varnished walnut grain for the finials and globe base
  textures/parchment_roll.png    atlas for the wound rolls: left half the outer parchment, right half the spiral end

Run headless (Blender 5.2):
  /Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_map_props.py -- --export
  /Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_map_props.py -- --export --render --samples 96 \
      --captures captures/blender/map-props
"""
import bpy, bmesh, math, os, sys, argparse, shutil, json
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/map-props")
ap.add_argument("--export", action="store_true")
ap.add_argument("--render", action="store_true")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", type=int, default=1600)
ap.add_argument("--cams", default="")
ap.add_argument("--captures", default="")
ap.add_argument("--cpu", action="store_true")
ARGS = ap.parse_args(argv)
OUT = os.path.abspath(ARGS.out)
TEX = os.path.join(OUT, "textures")
os.makedirs(TEX, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

# ----------------------------------------------------------------------------- dimensions (metres)
W = 0.60            # default sheet (map image) width
H = 0.42            # default sheet height (aspect 1.43, a landscape map)
NX, NY = 64, 40     # sheet grid
BELLY = 0.010       # the sheet's centre sits this far behind its edges
R_ROLL = 0.0175     # outer radius of the parchment wound on each roller
R_ROD = 0.0105      # wooden roller core (seen in the spiral end and the stubs)
SIDES = 18          # around the rolls and finials
GLOBE_R = 0.18      # the sphere the globe stand is made for
GLOBE_C = 0.322     # sphere centre above the base bottom
TILT = 23.44        # axial tilt of the spin axis from vertical, degrees

rs = np.random.default_rng(1883)


# ----------------------------------------------------------------------------- numpy texture painting
def fnoise(h, w, sy, sx, seed):
    """Tileable smooth noise in [-1, 1]: white noise low-passed in the frequency domain (sy, sx = feature size in px)."""
    r = np.random.default_rng(seed)
    n = r.standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-((fy * sy) ** 2 + (fx * sx) ** 2) * 2.0)
    out = np.real(np.fft.ifft2(np.fft.fft2(n) * g))
    out -= out.mean(); out /= (np.abs(out).max() + 1e-9)
    return out


def fbm(h, w, base, seed, octaves=4, aspect=1.0):
    acc = np.zeros((h, w)); amp = 1.0; tot = 0.0
    for o in range(octaves):
        acc += amp * fnoise(h, w, base / 2 ** o, base * aspect / 2 ** o, seed + o); tot += amp; amp *= 0.5
    return acc / tot


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def save_png(name, rgba, non_color=False):
    """rgba: (h, w, 4) floats in [0, 1], row 0 = image top. Written as 8-bit PNG (values are stored as given)."""
    h, w = rgba.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(np.flipud(np.clip(rgba, 0, 1))).astype(np.float32).ravel())
    path = os.path.join(TEX, name + ".png")
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    img.filepath = path
    if non_color: img.colorspace_settings.name = 'Non-Color'
    return img


def rgba(rgb, a=None):
    a = np.ones(rgb.shape[:2]) if a is None else a
    return np.dstack([rgb, a])


def lerp3(c0, c1, t):
    c0 = np.array(c0); c1 = np.array(c1)
    return c0[None, None, :] * (1 - t[..., None]) + c1[None, None, :] * t[..., None]


def paint_placeholder_map(w=1200, h=840):
    v, u = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    mott = fbm(h, w, 160, 11)
    paper = lerp3((0.70, 0.56, 0.36), (0.82, 0.70, 0.49), 0.5 + 0.5 * mott)
    land = fbm(h, w, 300, 21, octaves=5) - 0.10 + 0.25 * np.exp(-(((u - 0.55) / 0.22) ** 2 + ((v - 0.5) / 0.28) ** 2)) - 0.15
    sea = land < 0
    col = paper.copy()
    col[sea] = col[sea] * 0.72 + np.array([0.46, 0.55, 0.50]) * 0.28
    col[~sea] *= (0.97 + 0.06 * np.clip(land[~sea] * 3, 0, 1))[:, None] * np.array([1.0, 0.98, 0.92])
    # hatched shallows and a coastline in sepia ink
    dist = np.abs(land)
    ink = np.array([0.24, 0.15, 0.08])
    shallows = sea & (dist < 0.06) & (np.sin((u * w + v * h) * 0.9) > 0.55)
    col[shallows] = col[shallows] * 0.55 + ink * 0.45
    coast = dist < 0.006
    col[coast] = ink
    hills = (~sea) & (np.abs(np.sin(land * 90)) < 0.06) & (land > 0.08)
    col[hills] = col[hills] * 0.6 + ink * 0.4
    # graticule: 8 x 6 cells, thin
    gx = np.abs(((u * 8) + 0.5) % 1 - 0.5) * w / 8; gy = np.abs(((v * 6) + 0.5) % 1 - 0.5) * h / 6
    grid = (gx < 0.8) | (gy < 0.8)
    col[grid] = col[grid] * 0.5 + np.array([0.45, 0.22, 0.12]) * 0.5
    # double neat-line border
    bx = np.minimum(u, 1 - u) * w; by = np.minimum(v, 1 - v) * h
    b = np.minimum(bx, by)
    col[((b > 18) & (b < 21)) | ((b > 25) & (b < 26.5))] = ink
    # compass rose, lower right
    cx, cy, cr = 0.86 * w, 0.78 * h, 70
    dx = u * w - cx; dy = v * h - cy; rr = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    col[(np.abs(rr - cr) < 1.4) | (np.abs(rr - cr * 0.8) < 1.0)] = ink
    star = rr < cr * (0.18 + 0.82 * np.abs(np.cos(2 * th)) ** 6)
    col[star & (np.cos(4 * th) > 0)] = ink
    col[star & (np.cos(4 * th) <= 0)] = col[star & (np.cos(4 * th) <= 0)] * 0.7 + np.array([0.6, 0.2, 0.15]) * 0.3
    # north arrow at the top centre (points to the image top)
    ax = np.abs(u * w - w / 2); ay = v * h
    col[(ay > 34) & (ay < 84) & (ax < (ay - 34) * 0.35)] = np.array([0.55, 0.08, 0.06])
    # orientation corners: red = top-left, green = top-right, blue = bottom-left, nothing bottom-right
    s = 44
    col[(u * w > 30) & (u * w < 30 + s) & (v * h > 30) & (v * h < 30 + s)] = (0.75, 0.08, 0.06)
    col[(u * w < w - 30) & (u * w > w - 30 - s) & (v * h > 30) & (v * h < 30 + s)] = (0.10, 0.50, 0.12)
    col[(u * w > 30) & (u * w < 30 + s) & (v * h < h - 30) & (v * h > h - 30 - s)] = (0.10, 0.20, 0.65)
    # a red X marks the spot
    px, py = 0.42 * w, 0.44 * h
    xx = u * w - px; yy = v * h - py
    col[((np.abs(xx - yy) < 3) | (np.abs(xx + yy) < 3)) & (np.abs(xx) < 14)] = (0.7, 0.05, 0.05)
    return save_png("map_placeholder", rgba(col)), (0.42, 0.44)


def paint_edge_mask(n=1024):
    v, u = np.mgrid[0:n, 0:n] / float(n)
    # ragged free edges (top and bottom), ~0.4-1.6 % of the height
    rag_t = 0.009 + 0.006 * fbm(1, n, 1, 31, octaves=5, aspect=60)[0] + 0.003 * fbm(1, n, 1, 35, aspect=8)[0]
    rag_b = 0.009 + 0.006 * fbm(1, n, 1, 41, octaves=5, aspect=60)[0] + 0.003 * fbm(1, n, 1, 45, aspect=8)[0]
    # a couple of small nicks
    for c, d, wd in ((0.23, 0.018, 0.012), (0.71, 0.014, 0.008)):
        rag_t = rag_t + d * np.exp(-((np.linspace(0, 1, n) - c) / wd) ** 2)
    rag_b = rag_b + 0.016 * np.exp(-((np.linspace(0, 1, n) - 0.56) / 0.010) ** 2)
    dt = v - rag_t[None, :]; db = (1 - v) - rag_b[None, :]
    px = 1.0 / n
    alpha = smooth(-px, px, dt) * smooth(-px, px, db)
    dv = np.maximum(np.minimum(dt, db), 0)
    du = np.minimum(u, 1 - u)
    burn = 0.55 * np.exp(-dv / 0.028) + 0.22 * np.exp(-du / 0.02)
    burn += 0.10 * np.exp(-dv / 0.10)
    mott = fbm(n, n, 90, 51)
    burn *= 0.8 + 0.4 * (0.5 + 0.5 * mott)
    # foxing spots
    fox = np.zeros((n, n))
    for _ in range(14):
        cx, cy, r = rs.uniform(0.05, 0.95), rs.uniform(0.05, 0.95), rs.uniform(0.004, 0.018)
        fox += 0.10 * np.exp(-(((u - cx) ** 2 + (v - cy) ** 2) / r ** 2))
    burn = np.clip(burn + fox + 0.04 * (0.5 + 0.5 * mott), 0, 0.8)
    edge = np.array([0.55, 0.38, 0.22])          # the colour the edge darkens toward
    col = 1 - burn[..., None] * (1 - edge[None, None, :]) / 0.8 * 0.8
    return save_png("scroll_edge_mask", rgba(col, alpha), non_color=True)


def paint_walnut(n=512):
    v, u = np.mgrid[0:n, 0:n] / float(n)
    warp = fbm(n, n, 120, 61, aspect=0.35)
    rings = np.sin((u * 9 + warp * 1.6 + 0.25 * fbm(n, n, 40, 65, aspect=0.2)) * 2 * np.pi)
    fine = fbm(n, n, 6, 71, octaves=2, aspect=0.12)
    t = 0.5 + 0.18 * rings + 0.22 * fine
    col = lerp3((0.085, 0.045, 0.022), (0.20, 0.115, 0.055), np.clip(t, 0, 1))
    col *= (0.85 + 0.15 * (0.5 + 0.5 * fbm(n, n, 200, 81)))[..., None]
    pores = fnoise(n, n, 1.2, 1.2, 91) > 0.55
    col[pores] *= 0.6
    return save_png("walnut", rgba(col))


def paint_parchment_roll(h=256):
    w = 2 * h
    img = np.zeros((h, w, 3))
    # left half: the outside of the roll (u = around, v = along the length)
    m = fbm(h, h, 50, 101)
    stripe = fbm(h, h, 6, 107, octaves=2, aspect=0.05)
    img[:, :h] = lerp3((0.62, 0.50, 0.33), (0.77, 0.65, 0.46), 0.5 + 0.4 * m + 0.1 * stripe)
    # right half: the end of the roll, a spiral of parchment layers round the walnut core
    yy, xx = np.mgrid[0:h, 0:h] / float(h)
    dx = (xx - 0.5) * 2; dy = (yy - 0.5) * 2
    r = np.hypot(dx, dy); th = np.arctan2(dy, dx)
    core = R_ROD / R_ROLL
    turns = 5
    phase = (r - core) / (1 - core) * turns - th / (2 * np.pi)
    layer = np.abs((phase % 1) - 0.5) * 2          # 1 mid-layer, 0 at the gaps
    end = lerp3((0.30, 0.22, 0.13), (0.78, 0.67, 0.48), smooth(0.08, 0.45, layer))
    end *= (0.85 + 0.15 * r)[..., None]
    wood = lerp3((0.07, 0.035, 0.016), (0.16, 0.09, 0.04), 0.5 + 0.5 * np.sin(r * 60))
    end[r < core] = wood[r < core]
    ring = np.abs(r - core) < 0.025
    end[ring] *= 0.5
    img[:, h:] = end
    return save_png("parchment_roll", rgba(img))


# ----------------------------------------------------------------------------- materials
def principled(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, image=None, emission=None):
    m = bpy.data.materials.new(name)
    m.use_backface_culling = True       # exported as glTF doubleSided = false (the map sheet overrides this)
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if image is not None:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = image; t.location = (-400, 200)
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission[0], 1)
        b.inputs["Emission Strength"].default_value = emission[1]
    return m


# ----------------------------------------------------------------------------- geometry helpers
def link(o, parent=None):
    scene.collection.objects.link(o)
    if parent is not None: o.parent = parent
    return o


def empty(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, None); o.empty_display_size = 0.05
    o.location = loc; o.rotation_euler = rot
    return link(o, parent)


def to_object(name, bm, mats, loc=(0, 0, 0), parent=None, sharp_deg=None):
    for f in bm.faces: f.smooth = True
    if sharp_deg is not None:
        lim = math.radians(sharp_deg)
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0) > lim: e.smooth = False
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    o = bpy.data.objects.new(name, me); o.location = loc
    return link(o, parent)


def lathe(bm, uv, profile, sides, mat_of, offset=Vector((0, 0, 0)), axis=Matrix.Identity(3), v_range=(0.0, 1.0), u_range=(0.0, 1.0)):
    """Revolve [(r, z), ...] round local Z. mat_of(i) = material index for segment i -> i+1. r == 0 collapses to a pole."""
    lens = [0.0]
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]): lens.append(lens[-1] + math.hypot(r1 - r0, z1 - z0))
    tot = lens[-1] or 1.0
    rings = []
    for (r, z), L in zip(profile, lens):
        if r < 1e-7:
            rings.append([bm.verts.new(offset + axis @ Vector((0, 0, z)))])
        else:
            rings.append([bm.verts.new(offset + axis @ Vector((r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides), z)))
                          for k in range(sides)])
    for i in range(len(profile) - 1):
        A, B = rings[i], rings[i + 1]
        va = v_range[0] + (v_range[1] - v_range[0]) * lens[i] / tot
        vb = v_range[0] + (v_range[1] - v_range[0]) * lens[i + 1] / tot
        for k in range(sides):
            k1 = (k + 1) % sides
            ua = u_range[0] + (u_range[1] - u_range[0]) * k / sides
            ub = u_range[0] + (u_range[1] - u_range[0]) * (k + 1) / sides
            if len(A) == 1 and len(B) == 1: continue
            if len(A) == 1:
                f = bm.faces.new((A[0], B[k1], B[k])); uvs = ((ua + ub) / 2, va), (ub, vb), (ua, vb)
            elif len(B) == 1:
                f = bm.faces.new((A[k], A[k1], B[0])); uvs = (ua, va), (ub, va), ((ua + ub) / 2, vb)
            else:
                f = bm.faces.new((A[k], A[k1], B[k1], B[k])); uvs = (ua, va), (ub, va), (ub, vb), (ua, vb)
            f.material_index = mat_of(i)
            for loop, t in zip(f.loops, uvs): loop[uv].uv = t


# ----------------------------------------------------------------------------- textures and materials
map_img, X_SPOT = paint_placeholder_map()
mask_img = paint_edge_mask()
walnut_img = paint_walnut()
roll_img = paint_parchment_roll()

M_MAP = principled("M_ScrollMap", rough=0.82, image=map_img)
M_ROLL = principled("M_ParchmentRoll", rough=0.8, image=roll_img)
M_WALNUT = principled("M_Walnut", rough=0.32, image=walnut_img)
M_BRASS = principled("M_Brass", color=(0.80, 0.58, 0.28), rough=0.28, metal=1.0)
M_GLASS = principled("M_PinGlass", color=(0.78, 0.04, 0.03), rough=0.08)
M_MAP.use_backface_culling = False

# ----------------------------------------------------------------------------- the scroll
scroll = empty("scroll")
scroll["fable"] = json.dumps({"designWidth": W, "designHeight": H, "rollRadius": R_ROLL, "sheetGrid": [NX, NY]})


def sheet_depth(xd, yd):
    """Blender +Y (away from the reader) for design coords xd, yd in [-0.5, 0.5]. Zero depth and zero slope at xd = +-0.5
    so the sheet leaves each roll tangentially."""
    c = math.cos(math.pi * xd) ** 2
    d = BELLY * c
    d += 0.0016 * math.sin(2 * math.pi * 1.3 * xd + 0.6) * c * (0.8 + 0.2 * math.cos(math.pi * yd))
    # the free edges (top and bottom) curl a little toward the reader, less near the rolls
    t = max(0.0, (abs(yd) - 0.36) / 0.14)
    fade = min(1.0, max(0.0, (0.5 - abs(xd)) / 0.12))
    d -= 0.0075 * t * t * fade * (0.75 + 0.25 * math.sin(7.0 * xd + (1.2 if yd > 0 else 2.6)))
    return d


bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
grid = [[bm.verts.new((i / NX - 0.5, sheet_depth(i / NX - 0.5, j / NY - 0.5), j / NY - 0.5)) for i in range(NX + 1)] for j in range(NY + 1)]
for j in range(NY):
    for i in range(NX):
        # wound so the front face normal points -Y (toward the reader)
        f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
        for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
            loop[uv].uv = (a / NX, b / NY)
bm.normal_update()
bm.faces.ensure_lookup_table()
if bm.faces[0].normal.y > 0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
sheet = to_object("scroll.sheet", bm, [M_MAP], parent=scroll)
sheet.scale = (W, 1.0, H)
sheet["fable"] = json.dumps({"designSize": [1.0, 1.0], "scaleRule": "localScale = (mapWidth, mapHeight, 1)",
                             "edgeMask": "textures/scroll_edge_mask.png"})


def roll_mesh(name, side):
    """The parchment wound on a roller: a cylinder round the roll axis, unit height (z -0.5..0.5), origin at the sheet edge
    (the roll's front tangent point), axis at +R_ROLL behind it. Side wall uses the left half of parchment_roll.png, the
    ends the spiral disc on the right half."""
    bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
    c = Vector((0, R_ROLL, 0))
    ring = lambda z: [bm.verts.new(c + Vector((R_ROLL * math.cos(2 * math.pi * k / 24), R_ROLL * math.sin(2 * math.pi * k / 24), z)))
                      for k in range(24)]
    lo, hi = ring(-0.5), ring(0.5)
    for k in range(24):
        k1 = (k + 1) % 24
        f = bm.faces.new((lo[k], lo[k1], hi[k1], hi[k]))
        for loop, t in zip(f.loops, ((k / 24 * 0.5, 0), ((k + 1) / 24 * 0.5, 0), ((k + 1) / 24 * 0.5, 1), (k / 24 * 0.5, 1))):
            loop[uv].uv = t
    for verts, top in ((hi, True), (lo, False)):
        f = bm.faces.new(verts if top else verts[::-1])
        for loop in f.loops:
            p = (loop.vert.co - c) / R_ROLL
            sx = p.x if side == "right" else -p.x
            loop[uv].uv = (0.75 + 0.25 * 0.98 * sx, 0.5 + 0.25 * 0.98 * p.y * 2)
        f.smooth = False
    bm.normal_update()
    o = to_object(name, bm, [M_ROLL], parent=scroll, sharp_deg=60)
    return o


def finial_mesh(name, end):
    """Turned walnut handle with a brass ring and tip, origin on the roll axis at the roll end, pointing +Z (top) or -Z."""
    P = [  # (r, z, material of the segment that starts here: 0 walnut, 1 brass)
        (R_ROD * 0.95, -0.004, 0), (R_ROD * 0.95, 0.007, 0), (0.019, 0.0085, 0), (0.0245, 0.0105, 0), (0.0255, 0.0135, 0),
        (0.024, 0.0165, 0), (0.013, 0.0185, 0), (0.0098, 0.023, 1), (0.0128, 0.0245, 1), (0.0128, 0.0290, 1), (0.0100, 0.0305, 0),
        (0.0112, 0.034, 0), (0.0158, 0.042, 0), (0.0168, 0.049, 0), (0.0145, 0.057, 0), (0.0095, 0.0635, 1), (0.0062, 0.0660, 1),
        (0.0045, 0.0700, 1), (0.0, 0.0725, 1)]
    bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
    flip = Matrix.Identity(3) if end == "top" else Matrix.Rotation(math.pi, 3, 'X')
    lathe(bm, uv, [(r, z) for r, z, _ in P], SIDES, lambda i: P[i][2], axis=flip)
    bm.normal_update()
    return to_object(name, bm, [M_WALNUT, M_BRASS], parent=scroll, sharp_deg=38)


for side, sx in (("left", -1), ("right", 1)):
    r = roll_mesh(f"scroll.roller.{side}", side)
    r.location = (sx * W / 2, 0, 0); r.scale = (1, 1, H)
    r["fable"] = json.dumps({"scaleRule": "localPosition.x = +-mapWidth/2, localScale = (1, mapHeight, 1)", "rollRadius": R_ROLL})
    for end, sz in (("top", 1), ("bottom", -1)):
        f = finial_mesh(f"scroll.finial.{side}.{end}", end)
        f.location = (sx * W / 2, R_ROLL, sz * H / 2)
        f["fable"] = json.dumps({"scaleRule": "localPosition = (+-mapWidth/2, +-mapHeight/2, rollAxisZ); no scaling"})

# ----------------------------------------------------------------------------- the pin (origin at the tip, up = +Z Blender)
pin = None
def build_pin():
    hc, hr = 0.0205, 0.0045
    P = [(0.0, 0.0, 1), (0.00035, 0.0012, 1), (0.00055, 0.0150, 1), (0.0011, 0.0156, 1), (0.0013, 0.0166, 1)]
    head = [(hr * math.sin(a), hc - hr * math.cos(a)) for a in np.linspace(math.radians(24), math.pi, 8)]
    P += [(r, z, 0) for r, z in head]
    bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
    lathe(bm, uv, [(r, z) for r, z, _ in P], 12, lambda i: P[i][2])
    bm.normal_update()
    o = to_object("pin", bm, [M_GLASS, M_BRASS], sharp_deg=50)
    o["fable"] = json.dumps({"origin": "needle tip", "points": "-Y", "length": 0.025, "headRadius": hr})
    return o


pin = build_pin()
pin.location = (0.55, 0, -0.1)


# ----------------------------------------------------------------------------- the globe stand (origin at the base bottom)
def build_globe_stand():
    stand = empty("globe.stand")
    stand.location = (1.05, 0.0, -0.60)
    stand["fable"] = json.dumps({"sphereRadius": GLOBE_R, "sphereCentreHeight": GLOBE_C, "axialTiltDeg": TILT})
    bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
    # turned base: walnut, brass cup at the top that grips the meridian
    ring_out = GLOBE_R + 0.0185
    cup_top = GLOBE_C - ring_out + 0.009
    P = [(0.0, 0.0, 0), (0.112, 0.0, 0), (0.118, 0.003, 0), (0.118, 0.011, 0), (0.111, 0.015, 0), (0.096, 0.019, 0),
         (0.080, 0.027, 0), (0.066, 0.036, 0), (0.046, 0.042, 0), (0.034, 0.049, 0), (0.031, 0.055, 0), (0.035, 0.059, 0),
         (0.031, 0.064, 0), (0.019, 0.071, 0), (0.0155, 0.083, 0), (0.0165, 0.094, 0), (0.0215, 0.101, 0), (0.0225, cup_top - 0.020, 1),
         (0.0205, cup_top - 0.018, 1), (0.0160, cup_top - 0.004, 1), (0.0150, cup_top, 1), (0.0, cup_top, 1)]
    lathe(bm, uv, [(r, z) for r, z, _ in P], 24, lambda i: P[i][2])
    # meridian ring: a flat brass band (radial 12 mm x 5 mm) in the XZ plane round the sphere centre
    seg = 64; r0, r1, t = GLOBE_R + 0.0065, ring_out, 0.0025
    c = Vector((0, 0, GLOBE_C))
    sect = [(r0, -t), (r1, -t), (r1, t), (r0, t)]
    loops = []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        d = Vector((math.cos(a), 0, math.sin(a)))
        loops.append([bm.verts.new(c + d * rr + Vector((0, yy, 0))) for rr, yy in sect])
    for k in range(seg):
        A, B = loops[k], loops[(k + 1) % seg]
        for s in range(4):
            f = bm.faces.new((A[s], A[(s + 1) % 4], B[(s + 1) % 4], B[s])); f.material_index = 1
            for loop, tt in zip(f.loops, ((k / seg, s / 4), (k / seg, (s + 1) / 4), ((k + 1) / seg, (s + 1) / 4), ((k + 1) / seg, s / 4))):
                loop[uv].uv = tt
    # axis pivots at the poles: a brass pin through the ring with a domed nut outside
    axis = Matrix.Rotation(math.radians(TILT), 3, 'Y')
    for sgn in (1, -1):
        rot = axis if sgn > 0 else axis @ Matrix.Rotation(math.pi, 3, 'X')
        P2 = [(0.0, GLOBE_R - 0.004, 1), (0.0028, GLOBE_R - 0.004, 1), (0.0028, ring_out + 0.002, 1), (0.0055, ring_out + 0.002, 1),
              (0.0060, ring_out + 0.005, 1), (0.0045, ring_out + 0.0085, 1), (0.0, ring_out + 0.010, 1)]
        lathe(bm, uv, [(r, z) for r, z, _ in P2], 12, lambda i: 1, offset=c, axis=rot)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    o = to_object("globe.stand.mesh", bm, [M_WALNUT, M_BRASS], parent=stand, sharp_deg=38)
    o.name = "globe.stand.mesh"
    ax = empty("globe.stand.axis", (0, 0, GLOBE_C), parent=stand, rot=(0, math.radians(TILT), 0))
    ax["fable"] = json.dumps({"sphereRadius": GLOBE_R, "note": "parent the sphere here; spin about local +Y (glTF/Unity)"})
    return stand


globe = build_globe_stand()


# ----------------------------------------------------------------------------- budget
def tris(o):
    if o.type != 'MESH': return 0
    o.data.calc_loop_triangles(); return len(o.data.loop_triangles)


budget = {o.name: tris(o) for o in scene.objects if o.type == 'MESH'}
scroll_tris = sum(v for k, v in budget.items() if k.startswith("scroll."))
print("TRIS", json.dumps(budget, indent=1))
print("TRIS scroll total", scroll_tris, "pin", budget["pin"], "globe.stand", budget["globe.stand.mesh"])

# ----------------------------------------------------------------------------- export
if ARGS.export:
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "map_props.gltf"), export_format='GLTF_SEPARATE',
                              export_texture_dir="textures", export_extras=True, export_yup=True, export_cameras=False,
                              export_lights=False, export_apply=False, export_image_format='AUTO')
    with open(os.path.join(OUT, "triangles.json"), "w") as fh:
        json.dump({"objects": budget, "scrollTotal": scroll_tris}, fh, indent=1)
    print("EXPORTED", os.path.join(OUT, "map_props.gltf"))

# ----------------------------------------------------------------------------- review renders
if ARGS.render:
    # preview the Unity shader: base = map * mask.rgb, alpha-clipped by mask.a
    nt = M_MAP.node_tree; b = nt.nodes["Principled BSDF"]
    tmap = [n for n in nt.nodes if n.type == 'TEX_IMAGE'][0]
    tm = nt.nodes.new("ShaderNodeTexImage"); tm.image = mask_img; tm.location = (-400, -150)
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 1.0
    nt.links.new(tmap.outputs["Color"], mul.inputs[6]); nt.links.new(tm.outputs["Color"], mul.inputs[7])
    nt.links.new(mul.outputs[2], b.inputs["Base Color"]); nt.links.new(tm.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Subsurface Weight"].default_value = 0.08
    b.inputs["Subsurface Radius"].default_value = (0.01, 0.006, 0.003)
    # a lit pin on the X
    M_GLASS.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1.0, 0.15, 0.08, 1)
    M_GLASS.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.6
    ps = pin.copy(); link(ps)
    xd, yd = X_SPOT[0] - 0.5, 0.5 - X_SPOT[1]
    ps.location = (xd * W, sheet_depth(xd, yd) + 0.002, yd * H)
    ps.rotation_euler = (math.radians(90 - 12), 0, math.radians(-10))
    pl = bpy.data.lights.new("PinGlow", 'POINT'); pl.energy = 0.04; pl.color = (1.0, 0.25, 0.12); pl.shadow_soft_size = 0.004
    po = bpy.data.objects.new("PinGlow", pl); link(po); po.location = ps.location + Vector((0, -0.022, 0.004))
    # backdrop, lights and world
    bd = principled("M_Backdrop", color=(0.035, 0.028, 0.024), rough=0.9)
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0.45, 0), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(bd)
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, -0.60))
    bpy.context.object.data.materials.append(bd)
    def area(name, e, col, loc, size, look=(0, 0, 0)):
        ld = bpy.data.lights.new(name, 'AREA'); ld.energy = e; ld.color = col; ld.size = size
        o = bpy.data.objects.new(name, ld); link(o); o.location = loc
        o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    area("Key", 45, (1.0, 0.86, 0.68), (-0.9, -1.0, 0.9), 0.8)
    area("Fill", 14, (0.75, 0.82, 1.0), (1.2, -0.9, 0.1), 1.2)
    area("Rim", 25, (1.0, 0.8, 0.6), (0.6, 0.6, 0.8), 0.5)
    world = bpy.data.worlds.new("Dim"); scene.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.045, 0.04, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

    scene.render.engine = 'CYCLES'; scene.cycles.samples = ARGS.samples; scene.cycles.use_denoising = True
    try:
        if ARGS.cpu: raise RuntimeError("cpu")
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'; prefs.get_devices()
        for d in prefs.devices: d.use = True
        scene.cycles.device = 'GPU'
    except Exception as e:
        print("CPU render:", e)
    scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'
    r = scene.render
    r.resolution_x = ARGS.res; r.resolution_y = int(ARGS.res * 0.625)
    r.use_stamp = True
    for k in dir(r):
        if k.startswith("use_stamp_"): setattr(r, k, False)
    r.use_stamp_note = True; r.stamp_font_size = max(12, ARGS.res // 80)
    r.stamp_foreground = (1, 1, 1, 0.85); r.stamp_background = (0, 0, 0, 0.35)

    def cam(name, loc, look, lens):
        cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_start = 0.01
        o = bpy.data.objects.new(name, cd); link(o); o.location = loc
        o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        return o
    G = globe.location
    cams = {
        "reader": cam("reader", (0, -1.42, 0.02), (0, 0, 0), 50),
        "angle": cam("angle", (-0.95, -1.05, 0.42), (0.02, 0.0, -0.02), 50),
        "roller": cam("roller", (-0.47, -0.30, 0.31), (-0.30, R_ROLL, 0.20), 50),
        "pin": cam("pin", (xd * W + 0.10, -0.075, yd * H + 0.035), (xd * W, -0.008, yd * H + 0.006), 60),
        "globe": cam("globe", (G.x + 0.75, -1.25, G.z + 0.62), (G.x, G.y, G.z + 0.24), 50),
        "portrait": cam("portrait", (0, -2.45, 0.02), (0, 0, 0), 50),
    }
    # render-only preview sphere for the globe (Unity supplies its own)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=GLOBE_R, segments=64, ring_count=32, location=G + Vector((0, 0, GLOBE_C)))
    sph = bpy.context.object; bpy.ops.object.shade_smooth()
    sph.data.materials.append(principled("M_PreviewOcean", color=(0.20, 0.30, 0.30), rough=0.45))
    scroll_set = [o for o in scene.objects if o.name.startswith("scroll")] + [ps, po]
    globe_set = [globe] + list(globe.children_recursive) + [sph]
    def apply_map_size(w, h):
        """The rule Unity applies for a map of aspect w/h (docs/MAP_PROPS.md), done here in Blender axes."""
        sheet.scale = (w, 1, h)
        for side, sx in (("left", -1), ("right", 1)):
            ro = scene.objects[f"scroll.roller.{side}"]; ro.location = (sx * w / 2, 0, 0); ro.scale = (1, 1, h)
            for end, sz in (("top", 1), ("bottom", -1)):
                scene.objects[f"scroll.finial.{side}.{end}"].location = (sx * w / 2, R_ROLL, sz * h / 2)
        ps.location = ((X_SPOT[0] - 0.5) * w, sheet_depth(xd, yd) + 0.002, (0.5 - X_SPOT[1]) * h)
        po.location = ps.location + Vector((0, -0.022, 0.004))

    want = [c for c in ARGS.cams.split(",") if c] or list(cams)
    for name in want:
        apply_map_size(*((0.60, 0.60 / 0.72) if name == "portrait" else (W, H)))
        for o in globe_set: o.hide_render = name != "globe"
        for o in scroll_set: o.hide_render = name == "globe"
        pin.hide_render = True
        scene.camera = cams[name]
        r.stamp_note_text = f"Blender render (Cycles {ARGS.samples} spp) - map-props - {name}"
        fn = f"blender-render_map-props_{name}_cycles-{ARGS.samples}spp.png"
        r.filepath = os.path.join(OUT, "renders", fn)
        bpy.ops.render.render(write_still=True)
        print("RENDERED", r.filepath, flush=True)
        if ARGS.captures:
            os.makedirs(ARGS.captures, exist_ok=True); shutil.copy(r.filepath, os.path.join(ARGS.captures, fn))
print("DONE")
