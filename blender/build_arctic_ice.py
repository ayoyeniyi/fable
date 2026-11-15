"""
Fable: Walton's ship beset in the Arctic pack (Frankenstein, 1818, Walton's letters and volume III, chapter 7).

"Last Monday (July 31st), we were nearly surrounded by ice, which closed in the ship on all sides, scarcely leaving
her the sea-room in which she floated. ... we beheld, stretched out in every direction, vast and irregular plains of
ice, which seemed to have no end."
"... we perceived a low carriage, fixed on a sledge and drawn by dogs, pass on towards the north, at the distance of
half a mile ... We watched the rapid progress of the traveller with our telescopes, until he was lost among the
distant inequalities of the ice."
"We are still surrounded by mountains of ice, still in imminent danger of being crushed in their conflict."

The reader stands on the snow-covered floe fifty-five metres off the ship's starboard beam, late on a summer night when
the sun hangs a few degrees above the northern horizon. The ship, a three-masted vessel of some 300 tons, lies frozen
in with a slight list, her sails furled and snow-laden on the yards, her rigging rimed, ice rafted up against her
side; a gangway and an ice anchor's hawser run down to the floe. A dog-sledge's track runs from her gangway past
the reader's right and away across the floe behind the reader toward the north-east, between hummocks and pressure ridges,
until it is lost among the distant inequalities of the ice. A far tabular berg stands on the horizon; ahead a dark lead
of open water cuts the floe. The low sun stands behind the ship, rimming her masts and throwing long blue shadows; a faint halo and
sun dogs ring it. No people.

Everything is procedural (no downloaded models, textures or HDRIs). The floe is a height function in numpy: two
terrain discs with log-polar ground textures (finest at the reader's feet) painted with sastrugi, the sledge's runner
grooves and paw prints, bare blue ice where the wind has scoured it; beyond 1 km the pack and the horizon are painted
on the sky dome. Ice blocks of the ridges are bevelled boxes with a baked ice-and-snow node material. The ship's lines
and rig follow the Pequod's (build_pequod_deck.py), rebuilt for a ship seen from the ice.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet on the floe (z = 0), facing west-north-west, the ship broadside on the left of the page
  anchor.reader.look      eye height (1.55 m), 2 m ahead
  anchor.scene.centre     the reader's feet
  anchor.ship.mainmast, anchor.ship.gangway, anchor.track.far (the sledge track's vanishing point), anchor.lead
  light.sun (SUN, the midnight sun low on the right), light.sky (SUN, cool fill, no shadow)
  SkyDome.front, SkyDome.back (sky dome: sky, sun, halo, the far pack and a berg; unlit backdrop)
  Living scenes (docs/LIVING_SCENES.md):
    water.pond.lead (the open lead: still dark water, UV V along the lead), cloth.sail.furled (the furled sails, R
    0 at the yard to 0.3 at the bunt), sound.wind.0 (open floe), sound.wind.1 (the ridge on the right),
    sound.rigging.0 (the ship's rig and timbers)
Register as outdoor (Outdoor = true).

Axes: metres, Blender +Z up; the ship's keel runs along +Y (bow north), its centreline at x = -9.5; the reader at the
origin looking 28 degrees east of north. The floe's surface is z = 0, the sea in the lead z = -0.35.

Run headless:
  blender -b -P blender/build_arctic_ice.py -- --out out/arctic-ice --render --quick --res 900
  blender -b -P blender/build_arctic_ice.py -- --out out/arctic-ice --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os, time
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wotw_kit as K
import frankenstein_kit as F
from frankenstein_kit import (new_mat, node, math_, mix_rgb, mix_f, maprange, bump_from, c4, obj_xyz, noise_tex, white,
                              combine, tone_ramp, wood, planks, paint, metal, fabric, plain, box, cyl, sphere, torus, lathe,
                              tube, mesh_from, anchor, camera, TWO_PI, paint_stroke, paint_dot, CardMesh, fbm, sstep)

args, scene = K.begin("ArcticIce", "out/arctic-ice", seed=1797)
OUT = K.OUT
rnd = random.Random(1797)
T0 = time.time()
def log(*a): print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)

EYE = 1.55
LOOK_AZ = -71.0
SUN_AZ, SUN_EL = -112.0, 8.5
def az_dir(az): a = math.radians(az); return Vector((math.sin(a), math.cos(a), 0.0))
SUN_DIR = (az_dir(SUN_AZ) * math.cos(math.radians(SUN_EL)) + Vector((0, 0, math.sin(math.radians(SUN_EL))))).normalized()
S_ = np.array(SUN_DIR)
WL = -0.35
R_NEAR, R_GEO, R_SKY = 40.0, 1000.0, 1150.0
SX, SY = -54.2, -9.6                        # the ship's centreline x and its midships y (55 m off, her bow 22 degrees left of the page)

# ============================================================================= the floe
def seg_dist(x, y, pts):
    """Distance to a polyline and the arc length at the nearest point."""
    best = np.full(np.shape(x), 1e9); s_at = np.zeros(np.shape(x)); acc = 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy)
        t = np.clip(((x - ax) * dx + (y - ay) * dy) / (L * L), 0, 1)
        d = np.hypot(x - (ax + t * dx), y - (ay + t * dy))
        s_at = np.where(d < best, acc + t * L, s_at); best = np.minimum(best, d); acc += L
    return best, s_at

RIDGES = [  # (polyline, crest height, half width)
    ([(25, -30), (28, -12), (34, 0), (44, 10)], 1.7, 3.2),
    ([(-70, 58), (-35, 86), (0, 104), (34, 116), (70, 128)], 1.5, 3.5),
    ([(-6, -10), (-18, -15), (-32, -20), (-45, -25.5)], 1.6, 2.6),          # the ridge that leads the eye to the ship's stern
    ([(95, 250), (180, 290), (290, 300), (420, 290)], 2.4, 6.0),
    ([(-420, 160), (-300, 240), (-200, 320), (-80, 380)], 2.2, 6.0),
    ([(250, -60), (330, 40), (400, 140)], 2.0, 6.0),
    ([(-300, -180), (-180, -260), (-60, -330), (80, -380)], 2.2, 6.0),
    ([(520, 520), (640, 600), (760, 700)], 2.6, 7.0),
]
TRACK = [(-46.5, -13.6), (-36.0, -12.0), (-24.0, -8.5), (-13.0, -4.0), (-6.0, -0.8), (-0.4, 1.5), (6.0, 6.0), (20.0, 16.0), (50.0, 40.0),
         (100.0, 80.0), (180.0, 140.0), (300.0, 230.0), (480.0, 360.0), (700.0, 520.0), (900.0, 660.0)]   # from the gangway, past the reader's right, away
LEAD = [(-260.0, 180.0), (-170.0, 150.0), (-90.0, 140.0), (-20.0, 170.0), (40.0, 230.0), (70.0, 260.0)]
LEAD_W = 9.0

def lead_half(s):
    return LEAD_W * (0.55 + 0.45 * np.sin(np.asarray(s) / 47.0) ** 2) * sstep(0.0, 25.0, s) * sstep(470.0, 430.0, s)

def floe(x, y):
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    z = 0.22 * (fbm(x / 9.0, y / 9.0, 4, seed=1) - 0.5) + 0.35 * (fbm(x / 40.0, y / 40.0, 3, seed=2) - 0.5)
    drift = fbm(x / 3.0 + y / 9.0, y / 3.0 - x / 9.0, 3, seed=3)
    z = z + 0.10 * sstep(0.5, 0.75, drift)
    for pts, h, hw in RIDGES:
        d, s = seg_dist(x, y, pts)
        hh = h * (0.55 + 0.7 * fbm(s / 14.0, h * 3.0, 3, seed=4))
        z = z + hh * np.exp(-(d / hw) ** 2) + 0.25 * hh * np.exp(-(d / (hw * 2.5)) ** 2)
    # the snow banked against the ship, the trodden track (a little sunk)
    dsh = np.abs(x - SX) - shiphalf(y - SY)
    z = z + 0.7 * np.exp(-np.maximum(dsh, 0) / 1.6) * (np.abs(y - SY) < 16)
    dt, st = seg_dist(x, y, TRACK)
    z = z - 0.04 * sstep(0.7, 0.2, dt)
    dl, sl = seg_dist(x, y, LEAD)
    lw = lead_half(sl)
    z = np.where(dl < lw + 1.2, np.minimum(z, WL + 0.12 + (dl - lw) * 0.4), z)
    z = np.where(dl < lw, WL - 0.25, z)
    return z * sstep(1.5, 0.0, np.hypot(x, y)) * 0.0 + z * sstep(0.0, 1.5, np.hypot(x, y)) + 0.0

def shiphalf(y):
    y = np.asarray(y, np.float64)
    return np.interp(y, [-15.0, -12.0, -6.0, 2.0, 8.0, 12.0, 14.5, 15.5], [2.6, 3.3, 3.8, 3.9, 3.6, 2.7, 1.4, 0.15]) * 1.02

def gz(x, y): return floe(x, y)
def slope_of(x, y, e=0.3):
    return (floe(x + e, y) - floe(x - e, y)) / (2 * e), (floe(x, y + e) - floe(x, y - e)) / (2 * e)

# ============================================================================= ground textures (log-polar)
def snow_albedo(x, y, fp):
    fine = sstep(0.25, 0.04, fp)
    n1 = fbm(x / 5.0, y / 5.0, 4, seed=11)
    col = np.stack([0.66 + 0.04 * n1, 0.69 + 0.04 * n1, 0.74 + 0.03 * n1], -1)
    # sastrugi: wind-cut ridges running with the wind (from the north-west), their lee faces darker
    wx, wy = math.cos(math.radians(40)), math.sin(math.radians(40))
    a_ = x * wx + y * wy; b_ = -x * wy + y * wx
    sas = fbm(a_ / 2.5, b_ / 0.35, 4, seed=12)
    col = col * (1 - (0.10 * sstep(0.5, 0.75, sas) * sstep(1.0, 0.1, fp))[..., None] * np.array([1.0, 0.8, 0.55]))
    # scoured bare ice, grey-blue, and crusted older snow
    bare = sstep(0.66, 0.74, fbm(x / 14.0, y / 14.0, 4, seed=13))
    col = col * (1 - bare[..., None]) + np.array([0.42, 0.52, 0.58]) * (0.9 + 0.2 * n1[..., None]) * bare[..., None]
    crust = sstep(0.4, 0.8, fbm(x / 1.2, y / 1.2, 3, seed=14)) * fine * 0.06
    col = col * (1 - crust[..., None])
    # the sledge track: runner grooves 0.62 m apart, the dogs' trodden lane between, paw prints
    d, s = seg_dist(x, y, TRACK)
    side = signed_side(x, y, TRACK)
    off = np.abs(side) - 0.31
    groove = sstep(0.035, 0.012, np.abs(off)) * sstep(900.0, 600.0, s)
    lip = sstep(0.06, 0.035, np.abs(off - 0.035)) * sstep(900.0, 600.0, s)
    lane = sstep(0.28, 0.18, np.abs(side)) * sstep(800.0, 500.0, s)
    paw = sstep(0.66, 0.72, fbm(x / 0.06, y / 0.06, 3, seed=15)) * lane * sstep(0.08, 0.02, fp) * 0.6
    fade = np.clip(sstep(0.0, 0.3, 1.0 - fp * 2), 0.25, 1.0)[..., None]
    col = col * (1 - groove[..., None] * 0.45 * fade * np.array([1.0, 0.9, 0.75]))
    col = col * (1 + lip[..., None] * 0.08)
    col = col * (1 - lane[..., None] * 0.07) * (1 - paw[..., None] * 0.35 * np.array([1.0, 0.9, 0.8]))
    # far off, where the grooves are finer than a texel, the track is a faint grey line
    far_tr = sstep(0.9, 0.3, d) * sstep(0.05, 0.3, fp) * 0.12
    col = col * (1 - far_tr[..., None])
    # trodden snow by the ship's gangway, a little soot and spilt tar
    tro = sstep(9.0, 3.0, np.hypot(x - (SX + 6.0), y - SY + 3.5)) * sstep(0.55, 0.62, fbm(x / 0.6, y / 0.6, 3, seed=16))
    col = col * (1 - 0.12 * tro[..., None])
    # the lead's thin new ice (grey nilas) at its margins
    dl, sl = seg_dist(x, y, LEAD); lw = lead_half(sl)
    nil = sstep(lw + 3.0, lw + 0.5, dl)
    col = col * (1 - nil[..., None]) + np.array([0.20, 0.25, 0.29]) * nil[..., None]
    return col

def signed_side(x, y, pts):
    best = np.full(np.shape(x), 1e9); sg = np.zeros(np.shape(x))
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
        t = np.clip(((x - ax) * dx + (y - ay) * dy) / L2, 0, 1)
        px, py = ax + t * dx, ay + t * dy
        d = np.hypot(x - px, y - py)
        cr = (dx * (y - ay) - dy * (x - ax)) / math.sqrt(L2)
        sg = np.where(d < best, cr, sg); best = np.minimum(best, d)
    return sg

NS = 112
def near_radii():
    rs = [0.0]; r = 0.0
    while r < R_NEAR:
        r = min(R_NEAR, r + min(3.0, 0.3 + r * 0.075)); rs.append(r)
    return rs
def far_radii():
    rs = [R_NEAR]; r = R_NEAR
    while r < R_GEO:
        r = min(R_GEO, r * 1.13); rs.append(r)
    return rs
RN, RF = near_radii(), far_radii()
R0n = 0.6
def vn_of_r(r): return np.log1p(np.asarray(r) / R0n) / math.log1p(R_NEAR / R0n)
def rn_of_v(v): return R0n * np.expm1(np.asarray(v) * math.log1p(R_NEAR / R0n))
def vf_of_r(r): return np.log(np.asarray(r) / R_NEAR) / math.log(R_GEO / R_NEAR)
def rf_of_v(v): return R_NEAR * np.exp(np.asarray(v) * math.log(R_GEO / R_NEAR))

def paint_ground(N, near):
    u = (np.arange(N) + 0.5) / N; v = (np.arange(N) + 0.5) / N
    U, V = np.meshgrid(u, v)
    r = (rn_of_v if near else rf_of_v)(V); th = U * TWO_PI
    x, y = r * np.cos(th), r * np.sin(th)
    dr = np.gradient(r, axis=0); fp = np.maximum(np.abs(dr), r * TWO_PI / N)
    out = np.empty((N, N, 3), np.float32)
    for i in range(0, N, 256):
        sl = slice(i, i + 256)
        col = snow_albedo(x[sl], y[sl], fp[sl])
        ec = float(max(0.4, np.median(r[sl]) * 0.05)); ef = max(0.05, float(np.median(fp[sl])) * 1.5)
        zx, zy = slope_of(x[sl], y[sl], ec); zx2, zy2 = slope_of(x[sl], y[sl], ef)
        nf = np.stack([-zx2, -zy2, np.ones_like(zx2)], -1); nf /= np.linalg.norm(nf, axis=-1, keepdims=True)
        nc = np.stack([-zx, -zy, np.ones_like(zx)], -1); nc /= np.linalg.norm(nc, axis=-1, keepdims=True)
        sh = 1.0 + 1.6 * ((nf - nc) @ S_)
        out[sl] = col * np.clip(sh, 0.6, 1.3)[..., None]
    rgba = np.ones((N, N, 4), np.float32); rgba[..., :3] = np.clip(out, 0, 1)
    return rgba

def ground_disc(name, rs, mat, v_of_r, inner=False):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rings = []; start = 0
    if inner: c = bm.verts.new((0.0, 0.0, float(gz(0.0, 0.0)))); start = 1
    for r in rs[start:]:
        th = np.arange(NS) / NS * TWO_PI
        x_, y_ = r * np.cos(th), r * np.sin(th); z_ = gz(x_, y_)
        rings.append([bm.verts.new((float(a), float(b), float(cz))) for a, b, cz in zip(x_, y_, z_)])
    vr = [float(v_of_r(r)) for r in rs]
    if inner:
        for i in range(NS):
            j = (i + 1) % NS; f = bm.faces.new((c, rings[0][i], rings[0][j]))
            for lp, uv in zip(f.loops, ((i / NS + 0.5 / NS, 0.0), (i / NS, vr[1]), ((i + 1) / NS, vr[1]))): lp[uvl].uv = uv
    off = 1 if inner else 0
    for k in range(len(rings) - 1):
        for i in range(NS):
            j = (i + 1) % NS
            f = bm.faces.new((rings[k][i], rings[k + 1][i], rings[k + 1][j], rings[k][j]))
            for lp, uv in zip(f.loops, ((i / NS, vr[k + off]), (i / NS, vr[k + off + 1]), ((i + 1) / NS, vr[k + off + 1]), ((i + 1) / NS, vr[k + off]))): lp[uvl].uv = uv
    for f in bm.faces: f.smooth = True
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat); K.link(o)
    K.KEEP_UV.add(mat.name)
    return o

log("painting ground ...")
GN = 2048 if not args.quick else 1024
M_NEARG = K.card_material("M_SnowNear", K.image_from("T_SnowNear", paint_ground(GN, True)), rough=0.8, clip=False)
M_FARG = K.card_material("M_SnowFar", K.image_from("T_SnowFar", paint_ground(GN, False)), rough=0.7, clip=False)
log("ground painted")
ground_disc("SnowNear", RN, M_NEARG, vn_of_r, inner=True)
ground_disc("SnowFar", RF, M_FARG, vf_of_r)

# ============================================================================= the lead: still dark water
def water_mat():
    m, nt, b = new_mat("M_LeadWater")
    xyz, X, Y, Z = obj_xyz(nt)
    n = noise_tex(nt, xyz, 0.08, 3.0, 0.5)
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 1.0), (0.010, 0.016, 0.022, 1), (0.016, 0.024, 0.030, 1))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.06
    f = noise_tex(nt, xyz, 1.5, 3.0, 0.5); bump_from(nt, b, f.outputs["Fac"], 0.08, 0.01)
    return m
M_WATER = water_mat()
def lead_mesh():
    pts = [Vector((p[0], p[1], WL)) for p in LEAD]
    dense = []; acc = [0.0]
    for a, b_ in zip(pts, pts[1:]):
        n = max(2, int((b_ - a).length / 6.0))
        for k in range(n): dense.append(a.lerp(b_, k / n))
    dense.append(pts[-1])
    for a, b_ in zip(dense, dense[1:]): acc.append(acc[-1] + (b_ - a).length)
    verts, uvs, faces = [], [], []
    for i, p in enumerate(dense):
        t = (dense[min(i + 1, len(dense) - 1)] - dense[max(i - 1, 0)]).normalized(); sd = Vector((-t.y, t.x, 0))
        hw = float(lead_half(acc[i])) + 1.6
        for k, u in enumerate((-1.0, 1.0)):
            verts.append(p + sd * hw * u); uvs.append((0.5 + 0.5 * u, acc[i] / 20.0))
        if i: faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
    o = mesh_from("Lead", verts, faces, M_WATER, uvs=uvs)
    K.orient(o, lambda c: (0, 0, 1)); K.KEEP_UV.add(M_WATER.name)
    return o
lead_mesh()

# ============================================================================= pressure ridges: rafted ice blocks
def ice_mat():
    """Sea-ice blocks: blue-green where broken fresh, milky with brine channels, snow lodged on the tops."""
    m, nt, b = new_mat("M_IceBlock")
    xyz, X, Y, Z = obj_xyz(nt)
    n = noise_tex(nt, xyz, 1.6, 5.0, 0.6); n2 = noise_tex(nt, xyz, 7.0, 4.0, 0.6)
    col = tone_ramp(nt, n.outputs["Fac"], [(0.12, 0.38, 0.44), (0.24, 0.50, 0.56), (0.46, 0.60, 0.65), (0.16, 0.42, 0.48)])
    big = noise_tex(nt, xyz, 0.35, 2.0, 0.5)
    col = mix_rgb(nt, 'MIX', maprange(nt, big.outputs["Fac"], 0.35, 0.65, 0.0, 0.7), col, (0.52, 0.62, 0.66, 1))       # milky old ice / clear blue new ice
    wv = node(nt, "ShaderNodeTexWave", wave_type='BANDS', bands_direction='Z'); wv.inputs["Scale"].default_value = 3.0
    wv.inputs["Distortion"].default_value = 6.0; nt.links.new(xyz, wv.inputs["Vector"])
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', wv.outputs["Fac"], 0.12), col, (0.8, 0.85, 0.9, 1))
    gm = node(nt, "ShaderNodeNewGeometry"); ns = node(nt, "ShaderNodeSeparateXYZ"); nt.links.new(gm.outputs["Normal"], ns.inputs[0])
    snow = math_(nt, 'MULTIPLY', maprange(nt, ns.outputs["Z"], 0.25, 0.55, 0.0, 1.0), maprange(nt, n2.outputs["Fac"], 0.3, 0.45, 0.5, 1.0))
    col = mix_rgb(nt, 'MIX', snow, col, (0.66, 0.69, 0.74, 1))
    low = maprange(nt, Z, 0.25, -0.1, 0.0, 0.5)
    col = mix_rgb(nt, 'MIX', low, col, (0.58, 0.62, 0.66, 1))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, snow, 0.25, 0.75), b.inputs["Roughness"])
    b.inputs["Subsurface Weight"].default_value = 0.25; b.inputs["Subsurface Radius"].default_value = (0.3, 0.6, 0.8)
    bump_from(nt, b, n2.outputs["Fac"], 0.3, 0.02)
    return m
M_ICE = ice_mat()

def ice_block(name, p, size, rs):
    rot = (rs.uniform(-0.7, 0.7) * (1.8 if rs.random() < 0.25 else 1.0), rs.uniform(-0.7, 0.7), rs.uniform(0, math.pi))
    near = math.hypot(p[0], p[1]) < 32
    o = box(name, size, p, M_ICE, bevel=min(size) * 0.12 if near else 0.0, rot=rot)
    if not near: return o
    # break the slab's regularity: push the corners about a little
    for v in o.data.vertices: v.co += Vector((rs.gauss(0, 0.06), rs.gauss(0, 0.06), rs.gauss(0, 0.03))) * max(size)
    return o
rs = random.Random(5); nblk = 0
for ri, (pts, h, hw) in enumerate(RIDGES):
    L = sum(math.hypot(b_[0] - a[0], b_[1] - a[1]) for a, b_ in zip(pts, pts[1:]))
    far = math.hypot(*pts[len(pts) // 2]) > 150
    step = 9.0 if far else 1.5
    s = 0.0
    while s < L:
        acc = 0.0
        for a, b_ in zip(pts, pts[1:]):
            sl = math.hypot(b_[0] - a[0], b_[1] - a[1])
            if acc + sl >= s: t = (s - acc) / sl; px, py = a[0] + (b_[0] - a[0]) * t, a[1] + (b_[1] - a[1]) * t; break
            acc += sl
        for k in range(1 if (far or rs.random() < 0.6) else 2):
            x = px + rs.gauss(0, hw * 0.35); y = py + rs.gauss(0, hw * 0.35)
            if math.hypot(x, y) < 6 or math.hypot(x, y) > R_GEO - 20: continue
            sz = rs.uniform(0.5, 1.6) * h * (1.6 if far else 1.0)
            z = float(gz(x, y)) + sz * rs.uniform(-0.3, 0.15)
            ice_block(f"Block{ri}_{nblk}", (x, y, z), (sz * rs.uniform(0.7, 1.8), sz * rs.uniform(0.5, 1.2), sz * rs.uniform(0.15, 0.55)), rs); nblk += 1
        s += step * rs.uniform(0.6, 1.4)
# rafted floe edges against the ship's side, and a few broken blocks about the floe
for k in range(26):
    yl = rs.uniform(-13, 14); x = SX + float(shiphalf(yl)) + rs.uniform(0.2, 1.4); y = yl + SY
    sz = rs.uniform(0.6, 1.3)
    ice_block(f"Raft{k}", (x, y, float(gz(x, y)) + 0.1), (sz * 1.6, sz, sz * 0.3), rs); nblk += 1
for k in range(30):
    a = rs.uniform(0, TWO_PI); r = rs.uniform(8, 90); x, y = r * math.sin(a), r * math.cos(a)
    if abs(x - SX) < 6 and abs(y - SY) < 17: continue
    if seg_dist(np.array(x), np.array(y), TRACK)[0] < 2.5: continue
    sz = rs.uniform(0.3, 0.9)
    ice_block(f"Loose{k}", (x, y, float(gz(x, y)) + sz * 0.05), (sz * 1.3, sz, sz * 0.35), rs); nblk += 1
log("ice blocks", nblk)

# ============================================================================= the ship (keel along +Y, centreline x = SX)
def interp1(table, x):
    xs = [p[0] for p in table]; ys = [p[1] for p in table]
    return float(np.interp(x, xs, ys))
RAIL = [(-15.0, 4.6), (-10.0, 4.05), (-3.0, 3.75), (4.0, 3.75), (10.0, 4.0), (15.5, 4.7)]
LIST = math.radians(3.5)                      # a slight list to port, pushed over by the ice
def rail_z(y): return interp1(RAIL, y)
KEEL = -3.9
def sect(s): return (1.0 - (1.0 - max(0.0, min(1.0, s))) ** 2.6) ** 0.5
def hb(y, z):
    top = rail_z(y); s = (z - KEEL) / (top - KEEL)
    tum = 1.0 - 0.06 * sstep(0.78, 1.0, s)
    return max(0.02, float(shiphalf(y)) / 1.02 * sect(s / 0.86) * tum)
SHIP_M = Matrix.Translation((SX, SY, 0)) @ Matrix.Rotation(-LIST, 4, 'Y')
def W(p): return tuple(SHIP_M @ Vector(p))

M_HULL = planks("M_Hull", 0.20, 6.5, [(0.050, 0.040, 0.032), (0.062, 0.050, 0.040), (0.045, 0.036, 0.029), (0.07, 0.056, 0.044)],
                (0.015, 0.012, 0.010), rough=0.7, seed=2.0, grain_k=0.5, bumpk=0.35, gap_w=0.02,
                coords=lambda nt, xyz, X, Y, Z: (Y, Z),
                wear=lambda nt, X, Y, Z: math_(nt, 'MAXIMUM', maprange(nt, Z, 0.9, -0.2, 0.0, 1.0),
                                               math_(nt, 'MULTIPLY', maprange(nt, noise_tex(nt, combine(nt, X, math_(nt, 'MULTIPLY', Y, 0.4), Z), 2.0, 4.0, 0.6).outputs["Fac"], 0.55, 0.7, 0.0, 1.0), 0.3)))
M_WALE = paint("M_Wale", (0.035, 0.032, 0.03), rough=0.55, mottle=0.2, scale=4.0)
M_BAND = paint("M_PaintBand", (0.42, 0.38, 0.30), rough=0.6, mottle=0.25, scale=6.0, grime=(-0.5, 3.0, (0.2, 0.18, 0.15)))
M_SPAR = wood("M_Spar", (0.36, 0.28, 0.19), (0.18, 0.13, 0.08), rough=0.7, along='Z', scale=2.0, seed=3.0, contrast=0.5)
M_YARD = wood("M_Yard", (0.10, 0.08, 0.06), (0.05, 0.04, 0.03), rough=0.65, along='X', scale=2.0, seed=4.0, contrast=0.5)
M_SAIL = fabric("M_Sail", (0.50, 0.47, 0.40), rough=0.92, scale=60.0, sheen=0.3, var=0.25)
M_SNOWCAP = paint("M_SnowCap", (0.66, 0.69, 0.74), rough=0.8, mottle=0.08, scale=20.0, bumpk=0.2)
M_ROPE = paint("M_Rope", (0.16, 0.14, 0.12), rough=0.85, mottle=0.2, scale=30.0)
M_IRON = metal("M_Iron", (0.07, 0.065, 0.06), rough=0.6, tarnish=(0.14, 0.08, 0.05))
M_CASK = wood("M_Cask", (0.30, 0.22, 0.14), (0.15, 0.10, 0.06), rough=0.7, along='Z', scale=2.0, seed=5.0, contrast=0.5)
M_WINDOW = plain("M_SternLights", (0.03, 0.035, 0.04), rough=0.15)

def hull_surface(NY=56, NZ=14):
    ys = [-15.0 + 30.5 * (1 - math.cos(math.pi * i / NY)) / 2 for i in range(NY + 1)]
    verts, faces = [], []
    for side in (1, -1):
        base = len(verts)
        for y in ys:
            top = rail_z(y)
            for j in range(NZ + 1):
                z = -1.6 + (top + 1.6) * j / NZ
                verts.append(W((side * hb(y, z), y, z)))
        for i in range(NY):
            for j in range(NZ):
                a = base + i * (NZ + 1) + j; b2 = a + NZ + 1
                faces.append((a, a + 1, b2 + 1, b2))
    o = mesh_from("Hull", verts, faces, M_HULL, smooth=True)
    K.orient(o, lambda c: (c.x - SX, 0.0, 0.0))
    return o
hull_surface()
# the transom (stern), its lights, the stem
yS = -15.0
verts = []
for j in range(9):
    z = -1.6 + (rail_z(yS) + 0.15 + 1.6) * j / 8; w = hb(yS, min(z, rail_z(yS)))
    verts += [W((-w, yS, z)), W((w, yS, z))]
faces = [(2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2) for j in range(8)]
K.orient(mesh_from("Transom", verts, faces, M_HULL, smooth=False), lambda c: (0, -1, 0))
for x in (-1.2, -0.4, 0.4, 1.2):
    box(f"SternLight{x}", (0.4, 0.04, 0.32), W((x, yS - 0.02, rail_z(yS) - 0.85)), M_WINDOW, rot=(0, -LIST, 0))
    box(f"SternFrame{x}", (0.48, 0.03, 0.40), W((x, yS - 0.005, rail_z(yS) - 0.85)), M_BAND, rot=(0, -LIST, 0))
tube("Stem", [W((0, 15.45, -1.6)), W((0, 15.8, 1.5)), W((0, 16.0, rail_z(15.5) + 0.5))], [0.16, 0.16, 0.14], M_WALE, sides=6)
# wales, the painted band and the rail cap, along both sides
for side in (1, -1):
    for name, z_of, mat, rr in (("WaleLow", lambda y: 0.9, M_WALE, 0.09), ("WaleHigh", lambda y: rail_z(y) - 1.55, M_WALE, 0.08),
                                ("Band", lambda y: rail_z(y) - 0.95, M_BAND, 0.07), ("RailCap", lambda y: rail_z(y) + 0.03, M_WALE, 0.07)):
        pts = []
        for i in range(31):
            y = -14.8 + 30.0 * i / 30
            z = z_of(y); pts.append(W((side * (hb(y, z) + 0.03), y, z)))
        tube(f"{name}{side}", pts, rr, mat, sides=5)
# deck (only seen from the masts' feet: a plain surface) and the bulwark tops
verts = []
for i in range(17):
    y = -14.6 + 29.6 * i / 16; dz = rail_z(y) - 1.0
    verts += [W((-hb(y, dz) + 0.1, y, dz)), W((hb(y, dz) - 0.1, y, dz))]
faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(16)]
K.orient(mesh_from("Deck", verts, faces, M_SNOWCAP), lambda c: (0, 0, 1))
def deck_z(y): return rail_z(y) - 1.0

# --- masts, yards, furled sails with snow lying on them
SAILS = []
def mast(name, y, d0, lower_h, top_h, tg_h, yards):
    z0 = deck_z(y) - 0.1
    cyl(name + "Lower", d0 / 2, lower_h + 0.3, W((0, y, z0 + (lower_h + 0.3) / 2)), M_SPAR, verts=12, r2=d0 * 0.42, rot=(0, -LIST, 0))
    lh = z0 + lower_h
    box(name + "Top", (2.6, 1.8, 0.1), W((0, y + 0.1, lh - 0.4)), M_SPAR, bevel=0.02, rot=(0, -LIST, 0))
    box(name + "TopSnow", (2.4, 1.6, 0.08), W((0, y + 0.1, lh - 0.31)), M_SNOWCAP, bevel=0.03, rot=(0, -LIST, 0))
    cyl(name + "Topmast", d0 * 0.32, top_h + 2.0, W((0, y - 0.3, lh - 1.6 + (top_h + 2.0) / 2)), M_SPAR, verts=8, r2=d0 * 0.22, rot=(0, -LIST, 0))
    th = lh - 1.6 + top_h + 2.0
    box(name + "Crosstrees", (1.7, 0.45, 0.08), W((0, y - 0.3, th - 1.0)), M_SPAR, rot=(0, -LIST, 0))
    cyl(name + "TopGallant", d0 * 0.2, tg_h + 1.4, W((0, y - 0.4, th - 1.2 + (tg_h + 1.4) / 2)), M_SPAR, verts=6, r2=d0 * 0.1, rot=(0, -LIST, 0))
    tgh = th - 1.2 + tg_h + 1.4
    for k, (h, L, brace) in enumerate(yards):
        yz = z0 + h; yy = y - 0.4
        r0 = 0.18 * L / 15.0 + 0.04
        R_ = Matrix.Rotation(math.radians(brace), 3, 'Z')
        def P(xx, dz=0.0, dy=0.0): return W(tuple(Vector((0, yy, yz + dz)) + R_ @ Vector((xx, dy, 0))))
        tube(f"{name}Yard{k}", [P(-L / 2), P(-L / 4), P(0), P(L / 4), P(L / 2)], [r0 * 0.45, r0 * 0.8, r0, r0 * 0.8, r0 * 0.45], M_YARD, sides=6)
        pts, rr, snow, sr = [], [], [], []
        for i in range(19):
            t = i / 18; xx = -L / 2 + 0.6 + (L - 1.2) * t
            bunt = math.exp(-((t - 0.5) / 0.18) ** 2)
            nz = 0.03 * math.sin(xx * 2.3 + k)
            pts.append(P(xx, r0 + 0.10 + 0.12 * bunt + nz, 0.05 + 0.08 * bunt)); rr.append(0.13 + 0.16 * bunt + 0.02 * math.sin(xx * 3.1))
            snow.append(P(xx, r0 + 0.22 + 0.27 * bunt + nz + 0.06, 0.05 + 0.08 * bunt)); sr.append(0.07 + 0.06 * bunt)
        s = tube(f"Sail{name}{k}", pts, rr, M_SAIL, sides=7); SAILS.append((s, yz))
        sn = tube(f"SailSnow{name}{k}", snow, sr, M_SNOWCAP, sides=5)
        sn.scale = (1, 1, 1)
        for gx in (-L / 3, -L / 8, L / 8, L / 3):
            torus(f"{name}Gasket{k}{gx:.1f}", r0 + 0.24, 0.014, P(gx, 0.13), M_ROPE, rot=(0, math.pi / 2, math.radians(brace)), seg=7, rseg=3)
    return Vector(W((0, y, lh))), Vector(W((0, y - 0.3, th))), Vector(W((0, y - 0.4, tgh)))
MAIN = mast("Main", 0.6, 0.62, 15.5, 10.0, 6.0, [(14.4, 16.5, 8), (21.6, 13.0, 10), (27.2, 9.0, 12)])
FORE = mast("Fore", 9.4, 0.58, 14.5, 9.5, 5.5, [(13.5, 15.5, 6), (20.4, 12.2, 8), (25.6, 8.5, 10)])
MIZ = mast("Mizzen", -8.0, 0.44, 12.0, 7.5, 4.5, [(11.0, 11.5, 12), (16.6, 9.0, 14)])
# bowsprit and jib boom, the spanker boom with its sail furled
BS0 = Vector(W((0, 13.5, deck_z(13.5) + 0.5))); dB = (Vector(W((0, 1.0, 0.27))) - Vector(W((0, 0, 0)))).normalized()
tube("Bowsprit", [tuple(BS0), tuple(BS0 + dB * 5.0), tuple(BS0 + dB * 9.5)], [0.24, 0.18, 0.13], M_SPAR, sides=8)
tube("JibBoom", [tuple(BS0 + dB * 8.0), tuple(BS0 + dB * 14.0)], [0.11, 0.07], M_SPAR, sides=6)
BS_END, JB_END = BS0 + dB * 9.3, BS0 + dB * 13.8
mz = deck_z(-8.0)
tube("SpankerBoom", [W((0, -7.6, mz + 2.6)), W((0, -12.0, mz + 2.75)), W((0, -15.6, mz + 2.9))], [0.13, 0.11, 0.08], M_SPAR, sides=8)
pts = [W((0.02 * math.sin(i), -8.2 - 6.8 * i / 12, mz + 2.88 + 0.01 * i)) for i in range(13)]
SAILS.append((tube("SailSpanker", pts, [0.17 + 0.03 * math.sin(i) for i in range(13)], M_SAIL, sides=7), mz + 2.75))
tube("SpankerSnow", [W((0.02 * math.sin(i), -8.2 - 6.8 * i / 12, mz + 3.08 + 0.01 * i)) for i in range(13)], 0.09, M_SNOWCAP, sides=5)

# --- standing rigging: shrouds with ratlines, backstays, stays (rimed rope)
def rope(name, a, b_, r=0.022, sag=0.0, sides=4):
    a, b_ = Vector(a), Vector(b_); mid = (a + b_) / 2 - Vector((0, 0, sag))
    pts = [a, mid, b_] if sag else [a, b_]
    return tube(name, [tuple(p) for p in pts], r, M_ROPE, sides=sides, cap=False)
def shrouds(name, head, y_base, n, spread, ratlines=True):
    for side in (1, -1):
        ends = []
        for i in range(n):
            y = y_base + spread * (i - (n - 1) / 2) / max(1, n - 1) * 2 + 0.5
            z = rail_z(y) - 0.3
            foot = Vector(W((side * (hb(y, z) + 0.30), y, z + 0.5)))
            hd = head + Vector((side * 0.30, 0.15, -0.3))
            rope(f"{name}Shroud{side}_{i}", foot, hd, 0.026)
            cyl(f"{name}Deadeye{side}_{i}", 0.09, 0.07, tuple(foot - Vector((0, 0, 0.12))), M_WALE, verts=7, rot=(0, math.pi / 2, 0))
            tube(f"{name}Chain{side}_{i}", [tuple(foot - Vector((0, 0, 0.18))), tuple(foot - Vector((0, 0, 1.2)))], 0.02, M_IRON, sides=4)
            ends.append((foot, hd))
        y0 = y_base - spread - 0.2; y1 = y_base + spread + 1.2; zc = rail_z(y_base) - 0.32
        box(f"{name}Channel{side}", (0.36, y1 - y0, 0.09), W((side * (hb((y0 + y1) / 2, zc) + 0.14), (y0 + y1) / 2, zc)), M_WALE, rot=(0, -LIST, 0))
        if ratlines:
            L = (ends[0][1] - ends[0][0]).length; h = 0.5
            while h < L * 0.85:
                t = h / L
                tube(f"{name}Ratline{side}_{h:.2f}", [tuple(a.lerp(b2, t)) for (a, b2) in ends], 0.009, M_ROPE, sides=3, cap=False)
                h += 0.5
shrouds("Main", MAIN[0], 0.6, 5, 1.4)
shrouds("Fore", FORE[0], 9.4, 5, 1.3)
shrouds("Miz", MIZ[0], -8.0, 4, 1.0)
for nm, (lh, th, tgh), y in (("Main", MAIN, 0.6), ("Fore", FORE, 9.4), ("Miz", MIZ, -8.0)):
    for side in (1, -1):
        for i in range(2):
            yy = y - 2.6 - 1.0 * i; z = rail_z(yy)
            rope(f"{nm}Backstay{side}{i}", W((side * (hb(yy, z - 0.3) + 0.25), yy, z)), (th if i == 0 else tgh) + Vector((side * 0.12, 0, -0.2)), 0.02)
        for i in range(3):
            rope(f"{nm}TopShroud{side}{i}", lh + Vector((side * 0.85, 0.15 + 0.3 * (i - 1), -0.35)), th + Vector((side * 0.12, 0, -0.9)), 0.015)
rope("ForeStay", FORE[0] + Vector((0, 0.2, -0.2)), BS_END, 0.035, sag=0.15)
rope("ForeTopStay", FORE[1], JB_END, 0.025, sag=0.2)
rope("MainStay", MAIN[0] + Vector((0, 0.2, -0.2)), W((0, 8.8, deck_z(8.8) + 0.4)), 0.035, sag=0.2)
rope("MainTopStay", MAIN[1], FORE[0] + Vector((0, 0, -0.3)), 0.025, sag=0.2)
rope("MainTGStay", MAIN[2], FORE[1], 0.018, sag=0.25)
rope("MizStay", MIZ[0] + Vector((0, 0.2, -0.2)), W((0, 0.0, deck_z(0) + 1.2)), 0.03, sag=0.2)
rope("MizTopStay", MIZ[1], MAIN[0] + Vector((0, 0, -0.5)), 0.02, sag=0.2)
rope("Bobstay", BS0 + dB * 6.0, W((0, 15.7, 0.6)), 0.03)
# lifts and braces (a few), hanging slack
for nm, (lh, th, tgh), y, L, br in (("Main", MAIN, 0.6, 16.5, 8), ("Fore", FORE, 9.4, 15.5, 6), ("Miz", MIZ, -8.0, 11.5, 12)):
    yz = deck_z(y) - 0.1 + {"Main": 14.4, "Fore": 13.5, "Miz": 11.0}[nm]
    R_ = Matrix.Rotation(math.radians(br), 3, 'Z')
    for side in (1, -1):
        arm = Vector(W(tuple(Vector((0, y - 0.4, yz)) + R_ @ Vector((side * (L / 2 - 0.3), 0, 0)))))
        rope(f"{nm}Lift{side}", arm, lh + Vector((side * 0.3, 0, 0.3)), 0.012, sides=3)
        yb = y - 6.0; zb = rail_z(yb)
        rope(f"{nm}Brace{side}", arm, W((side * (hb(yb, zb - 0.3) - 0.05), yb, zb + 0.1)), 0.012, sag=0.8, sides=3)

# --- the gangway and a Jacob's ladder down to the floe, the ice anchor's hawser, things on the ice
GY = -3.2
g_top = Vector(W((hb(GY, rail_z(GY)) - 0.05, GY, rail_z(GY) + 0.02))); g_bot = Vector((SX + 6.9, SY + GY - 0.3, float(gz(SX + 6.9, SY + GY - 0.3)) + 0.05))
gd = (g_bot - g_top); gl = gd.length
G = box("Gangway", (0.75, gl, 0.06), tuple((g_top + g_bot) / 2), M_CASK, rot=(0, 0, 0))
G.rotation_euler = (gd.normalized().to_track_quat('Y', 'Z')).to_euler()
for k in range(int(gl / 0.4)):
    p = g_top.lerp(g_bot, (k + 0.5) / int(gl / 0.4))
    c = box(f"GangwayCleat{k}", (0.7, 0.05, 0.04), tuple(p + Vector((0, 0, 0.05))), M_CASK)
    c.rotation_euler = G.rotation_euler.copy()
for s_ in (-1, 1):
    rope(f"GangwayRope{s_}", g_top + Vector((0, s_ * 0.4, 0.9)), g_bot + Vector((0, s_ * 0.4, 0.8)), 0.014, sag=0.25, sides=3)
    cyl(f"GangwayStanchion{s_}", 0.03, 0.85, tuple(g_bot + Vector((0, s_ * 0.4, 0.42))), M_SPAR, verts=6)
LY = 6.0
for k in range(2):
    y = LY + k * 0.42; zt = rail_z(y)
    rope(f"Ladder{k}", W((hb(y, zt) + 0.06, y, zt)), (SX + hb(y, 0.5) + 0.25, y + SY, float(gz(SX + hb(y, 0.5) + 0.25, y + SY)) + 0.05), 0.012, sides=3)
for k in range(9):
    z = 0.4 + k * 0.42; y = LY + 0.21
    box(f"LadderRung{k}", (0.05, 0.5, 0.035), W((hb(y, z) + 0.06 + 0.012 * (8 - k), y, z)), M_CASK)
HAWSE = Vector(W((0.9, 14.6, rail_z(14.6) - 0.6)))
# the ice anchor: a hawser from the bow's hawse-hole to an iron anchor bedded in a hole cut in the floe 12 m ahead, a
# mound of the chipped ice beside it
ANCHOR = Vector((SX + 2.5, SY + 27.5, float(gz(SX + 2.5, SY + 27.5))))
rope("IceHawser", HAWSE, ANCHOR + Vector((0, -0.25, 0.35)), 0.05, sag=0.9, sides=6)
tube("IceAnchorShank", [tuple(ANCHOR + Vector((0, -0.3, 0.4))), tuple(ANCHOR + Vector((0, 0.2, 0.15))), tuple(ANCHOR + Vector((0, 0.55, -0.25)))], 0.06, M_IRON, sides=6)
tube("IceAnchorFluke", [tuple(ANCHOR + Vector((-0.35, 0.5, -0.1))), tuple(ANCHOR + Vector((0, 0.6, -0.2))), tuple(ANCHOR + Vector((0.35, 0.5, -0.1)))], 0.05, M_IRON, sides=5)
torus("IceAnchorRing", 0.12, 0.025, tuple(ANCHOR + Vector((0, -0.38, 0.45))), M_IRON, rot=(math.pi / 2, 0, 0), seg=10, rseg=4)
sphere("IceAnchorMound", 0.6, tuple(ANCHOR + Vector((0.7, 0.4, -0.15))), M_SNOWCAP, seg=10, scale=(1.2, 0.9, 0.4))
def cask(name, p, s=1.0, lying=False, rot=0.0):
    prof = [(0.0, 0.0), (0.24 * s, 0.0), (0.28 * s, 0.15 * s), (0.30 * s, 0.35 * s), (0.28 * s, 0.55 * s), (0.24 * s, 0.70 * s), (0.0, 0.70 * s)]
    o = lathe(name, prof, p, M_CASK, steps=14)
    if lying: o.rotation_euler = (math.pi / 2, 0, rot)
    for zz in (0.12, 0.58):
        t = torus(name + f"Hoop{zz}", 0.27 * s, 0.012, (p[0], p[1], p[2] + zz * s), M_IRON, seg=14, rseg=3)
        if lying: t.location = o.location; t.rotation_euler = o.rotation_euler; t.data.transform(Matrix.Translation((0, 0, zz * s))); t.location = (p[0], p[1], p[2])
    return o
for k, (x, y) in enumerate(((SX + 7.6, SY - 5.0), (SX + 8.3, SY - 4.3), (SX + 7.4, SY - 1.9))):
    cask(f"Cask{k}", (x, y, float(gz(x, y)) - 0.05), 0.95)
    sphere(f"CaskCap{k}", 0.25, (x, y, float(gz(x, y)) + 0.625), M_SNOWCAP, seg=10, scale=(1.0, 1.0, 0.22))
box("Crate", (0.8, 0.55, 0.5), (SX + 8.9, SY - 6.2, float(gz(SX + 8.9, SY - 6.2)) + 0.2), M_CASK, bevel=0.01, rot=(0, 0, 0.3))
box("CrateSnow", (0.75, 0.5, 0.06), (SX + 8.9, SY - 6.2, float(gz(SX + 8.9, SY - 6.2)) + 0.47), M_SNOWCAP, bevel=0.025, rot=(0, 0, 0.3))

# ============================================================================= the sky dome: midnight sun, halo, the far pack, a berg
SKY_EL0 = -12.0
def sky_v_of(el): return ((el - SKY_EL0) / (90.0 - SKY_EL0)) ** 0.55
def sky_el_of_v(v): return SKY_EL0 + (90.0 - SKY_EL0) * v ** (1 / 0.55)
BERGS = [(-38.0, 0.9, 5.0), (-165.0, 0.45, 6.5), (95.0, 0.3, 3.0)]       # (az, height deg, width deg)
def paint_sky(W_=4096, Hh=1024):
    az = (np.arange(W_) + 0.5) / W_ * 360.0; v = (np.arange(Hh) + 0.5) / Hh; el = sky_el_of_v(v)
    AZ, EL = np.meshgrid(az, el)
    azr, elr = np.radians(AZ), np.radians(EL)
    dxs, dys, dzs = np.cos(elr) * np.sin(azr), np.cos(elr) * np.cos(azr), np.sin(elr)
    cg = np.clip(dxs * S_[0] + dys * S_[1] + dzs * S_[2], -1, 1); ang = np.degrees(np.arccos(cg))
    toward = np.clip(cg, 0, 1)
    e = np.clip(EL, 0, 90)[..., None]
    zen = np.array([0.11, 0.19, 0.36]); mid = np.array([0.30, 0.37, 0.52])
    hor_c = np.array([0.50, 0.50, 0.57]); hor_w = np.array([1.05, 0.70, 0.44])
    hor = hor_c * (1 - toward[..., None] ** 3) + hor_w * toward[..., None] ** 3
    f = (e / 90.0) ** 0.4
    col = hor * (1 - f) + (mid * (1 - f) + zen * f) * f
    col = col + (2.5 * np.exp(-(ang / 1.0) ** 2) + 0.8 * np.exp(-(ang / 5.0) ** 2) + 0.25 * np.exp(-(ang / 20.0) ** 2))[..., None] * np.array([1.0, 0.82, 0.6])
    col = col + (ang < 0.5)[..., None] * np.array([6.0, 5.0, 3.8])
    # the 22-degree halo and the two sun dogs
    halo = np.exp(-((ang - 22.0) / 0.7) ** 2) * 0.07 * sstep(-1, 3, EL)
    col = col + halo[..., None] * np.array([0.9, 0.85, 0.85])
    for s in (-1, 1):
        dd = np.hypot((AZ - (SUN_AZ + s * 22.6)) / 0.9, (EL - SUN_EL) / 1.6)
        col = col + (np.exp(-dd ** 2) * 0.35)[..., None] * np.array([1.0, 0.8, 0.65])
    # high thin stratus in long bands, lit gold toward the sun
    k = 1.0 / (np.maximum(dzs, 0.02) + 0.04)
    pu, pv = dxs * k, dys * k
    st = fbm(pu * 0.25, pv * 1.4, 5, seed=81)
    band = sstep(0.5, 0.75, st) * sstep(1.0, 5.0, EL) * 0.55
    bc = np.array([0.90, 0.72, 0.58]) * toward[..., None] ** 2 + np.array([0.56, 0.58, 0.64]) * (1 - toward[..., None] ** 2)
    col = col * (1 - band[..., None]) + bc * band[..., None]
    # the ice blink: the underside of the haze lit white over the pack
    col = col + (np.exp(-(EL / 2.0) ** 2) * 0.05)[..., None] * np.array([0.9, 0.92, 1.0])
    # below the horizon: the far pack, ridges as faint lines, haze toward the horizon
    below = EL < 0.0
    dist = 1.55 / np.maximum(np.tan(np.radians(-EL)), 1e-4)
    rid = sstep(0.62, 0.7, fbm(AZ / 0.6, np.log(dist) * 6.0, 3, seed=82))
    pack = np.array([0.46, 0.50, 0.58]) * (1 - 0.18 * rid[..., None]) + toward[..., None] * np.array([0.12, 0.06, 0.0])
    haze = np.clip(sstep(-0.25, 0.0, EL), 0, 1)[..., None]
    pack = pack * (1 - haze) + hor * 0.9 * haze
    col = np.where(below[..., None], pack, col)
    # distant hummocks and ridges standing just above the horizon
    prof = 0.06 + 0.10 * fbm(AZ / 1.5, np.zeros_like(AZ), 4, seed=83)[0]
    ridge_m = (EL >= 0) & (EL < prof[None, :])
    col = np.where(ridge_m[..., None], np.array([0.50, 0.55, 0.63]) + toward[..., None] * np.array([0.12, 0.07, 0.02]), col)
    # tabular bergs on the horizon: a flat top, sheer faces lit on the sun side, blue in shade
    for (baz, bh, bw) in BERGS:
        rel = (AZ - baz + 180.0) % 360.0 - 180.0
        top = bh * (1 - sstep(bw * 0.4, bw * 0.5, np.abs(rel)) * 0.0) * (np.abs(rel) < bw * 0.5)
        top = top - 0.06 * np.abs(rel) / bw * (np.abs(rel) < bw * 0.5)
        m = (EL >= -0.02) & (EL < top)
        lit = (np.sign(rel) == np.sign(((SUN_AZ - baz + 180) % 360) - 180)).astype(float)
        bcol = np.array([0.80, 0.78, 0.76]) * lit[..., None] + np.array([0.46, 0.56, 0.66]) * (1 - lit[..., None])
        bcol = bcol * (0.92 + 0.12 * fbm(AZ * 6, EL * 40, 2, seed=84)[..., None])
        col = np.where(m[..., None], bcol, col)
    rgba = np.ones((Hh, W_, 4), np.float32); rgba[..., :3] = np.clip(col, 0, 4)
    return rgba
log("painting sky ...")
PANO = paint_sky(4096 if not args.quick else 2048, 1024 if not args.quick else 512)

def dome_half(name, img_arr, az0, az1, seg=48, rings=16):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    els = [SKY_EL0 + (89.5 - SKY_EL0) * (j / rings) ** 1.6 for j in range(rings + 1)]
    grid = []
    for el in els:
        e = math.radians(el)
        grid.append([bm.verts.new((R_SKY * math.cos(e) * math.sin(math.radians(az0 + (az1 - az0) * i / seg)),
                                   R_SKY * math.cos(e) * math.cos(math.radians(az0 + (az1 - az0) * i / seg)), R_SKY * math.sin(e))) for i in range(seg + 1)])
    pole = bm.verts.new((0, 0, R_SKY))
    for j in range(rings):
        for i in range(seg):
            f_ = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for l, uv in zip(f_.loops, [(i / seg, sky_v_of(els[j])), ((i + 1) / seg, sky_v_of(els[j])), ((i + 1) / seg, sky_v_of(els[j + 1])), (i / seg, sky_v_of(els[j + 1]))]): l[uvl].uv = uv
    for i in range(seg):
        f_ = bm.faces.new((grid[-1][i], grid[-1][i + 1], pole))
        for l, uv in zip(f_.loops, [(i / seg, sky_v_of(els[-1])), ((i + 1) / seg, sky_v_of(els[-1])), ((i + 0.5) / seg, 1.0)]): l[uvl].uv = uv
    bm.normal_update()
    for f_ in bm.faces:
        if f_.normal.dot(f_.calc_center_median()) > 0: f_.normal_flip()
        f_.smooth = True
    bm.to_mesh(me); bm.free()
    m = K.card_material("M_" + name.replace(".", "_"), K.image_from("T_" + name.replace(".", "_"), img_arr), rough=1.0, clip=False, emissive=True)
    K.KEEP_UV.add(m.name)
    o = bpy.data.objects.new(name, me); me.materials.append(m); K.link(o)
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False; o.visible_transmission = False
    return o
Wp = PANO.shape[1]
# the front half is centred on the reading direction (az LOOK_AZ - 90 .. LOOK_AZ + 90)
sh = int(round((LOOK_AZ - 90.0) / 360.0 * Wp)) % Wp
rolled = np.roll(PANO, -sh, axis=1)
front = rolled[:, :Wp // 2]; back = rolled[:, Wp // 2:]
back = back.reshape(back.shape[0] // 2, 2, back.shape[1] // 2, 2, 4).mean(axis=(1, 3))
a0 = sh / Wp * 360.0
dome_half("far.sky.front", np.ascontiguousarray(front), a0, a0 + 180.0)
dome_half("far.sky.back", np.ascontiguousarray(back), a0 + 180.0, a0 + 360.0)

# ============================================================================= light
F.sun("light.sun", 7.5, (1.0, 0.76, 0.52), tuple(SUN_DIR), angle_deg=0.6)
F.sun("light.sky", 0.7, (0.62, 0.72, 1.0), (-0.1, -0.2, 1.0), angle_deg=80, shadow=False)
world = bpy.data.worlds.new("Polar"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.40, 0.48, 0.66, 1); bg.inputs["Strength"].default_value = 0.5

# ============================================================================= sway weights, anchors, sounds
for s, yz in SAILS:
    K.set_weight(s, lambda p, yz=yz: min(0.3, max(0.0, (p.z - yz - 0.05) * 0.8)))
    K.WEIGHTED.add(M_SAIL.name)
anchor("reader.entrance", (0.0, 0.0, float(gz(0.0, 0.0))))
lk = az_dir(LOOK_AZ)
anchor("reader.look", (lk.x * 2, lk.y * 2, EYE))
anchor("scene.centre", (0.0, 0.0, float(gz(0.0, 0.0))))
anchor("ship.mainmast", tuple(MAIN[0]))
anchor("ship.gangway", tuple(g_bot))
anchor("track.far", (TRACK[-3][0], TRACK[-3][1], 0.0))
anchor("lead", (LEAD[3][0], LEAD[3][1], WL))
F.sound("sound.wind.0", (8.0, 20.0, 2.0))
F.sound("sound.wind.1", (22.0, 25.0, 2.5))
F.sound("sound.rigging.0", tuple(MAIN[0] - Vector((0, 0, 6.0))))

K.apply_all_transforms()

# ============================================================================= cameras
E = Vector((0, 0, float(gz(0.0, 0.0)) + EYE))
def ahead(yaw_deg, pitch_deg=0.0, d=10.0):
    a = math.radians(LOOK_AZ - yaw_deg); p = math.radians(pitch_deg)
    return tuple(E + Vector((math.sin(a) * math.cos(p), math.cos(a) * math.cos(p), math.sin(p))) * d)
cams = [
    camera("Cam_Reader", tuple(E), ahead(0, -4), clip_end=1500),
    camera("Cam_Left", tuple(E), ahead(65, 14), clip_end=1500),
    camera("Cam_Right", tuple(E), ahead(-65, -3), clip_end=1500),
    camera("Cam_Behind", tuple(E), ahead(180, 2), clip_end=1500),
    camera("Cam_Up", tuple(E), ahead(75, 45), clip_end=1500),
    camera("Cam_Ship", (-28.0, -36.0, 1.7), (SX, SY, 7.0), lens=18, clip_end=1500),
]
EXPOSURE = {}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "arctic_ice_source.blend"))
K.budget_report()

if args.render:
    F.render_stills(scene, cams, EXPOSURE, default_exp=-0.5, label="arctic-ice")

if args.bake or args.export:
    T_ = args.tex
    size_for = {"M_Hull": (T_, T_ // 4, T_ // 2), "M_IceBlock": (T_ // 2, T_ // 4, T_ // 2), "M_Spar": (T_ // 4, T_ // 8, T_ // 8),
                "M_Yard": (T_ // 8,), "M_Sail": (T_ // 4, T_ // 16, T_ // 8), "M_SnowCap": (T_ // 8,), "M_Rope": (T_ // 8,),
                "M_Wale": (T_ // 8,), "M_PaintBand": (T_ // 8,), "M_Iron": (T_ // 16,), "M_Cask": (T_ // 4, T_ // 16, T_ // 8),
                "M_SternLights": (32,), "M_LeadWater": (T_ // 8,)}
    F.bake_and_export(scene, "arctic_ice.gltf", size_for,
                      keep_names={"M_far_sky_front": "SkyDome.front", "M_far_sky_back": "SkyDome.back", "M_SnowNear": "MESH_SnowNear",
                                  "M_SnowFar": "MESH_SnowFar", "M_LeadWater": "water.pond.lead", "M_Sail": "cloth.sail.furled"},
                      cams=cams, blend_name="arctic_ice_baked.blend")
print("DONE")
