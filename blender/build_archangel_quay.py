"""
Fable step-in room `archangel-quay`: the frozen harbour quay at Archangel (Frankenstein, Letter II, 1818 text).

"How slowly the time passes here, encompassed as I am by frost and snow; yet a second step is taken towards my
enterprise. I have hired a vessel, and am occupied in collecting my sailors ... I shall depart for the latter town
[Archangel] in a fortnight or three weeks ... my embarkation is delayed until the weather shall permit."

The moment: a pale overcast afternoon at the end of the northern winter, Archangel on the Northern Dvina in the
1790s. The reader stands on a timber wharf of logs and planks, among the stores waiting to go aboard: casks, crates,
coils of tarred hemp, iron bollards with snow drifted against them, a lantern on a post. Walton's hired vessel, a
three-masted ship with her sails furled on bare yards, lies moored alongside, held fast in the river ice, a gangway
down to the wharf. Beyond her, the frozen Dvina, grey ice under wind-packed snow, runs to a low far bank of dark
spruce. Behind the reader, the merchants' warehouses of dark timber; along the bank to the north, the town and the
domes of its churches. No people, no dog-sledges, no open polar sea, no steamships or cranes.

Ship: the three-master of build_arctic_ice.py (Walton's ship in the pack, chapters 23-24), reused here as she is
before the voyage: no list to speak of, the ice level with the river.

Run (from the repo root):
  blender -b -P blender/build_archangel_quay.py -- --render --samples 48 --res 1280
  blender -b -P blender/build_archangel_quay.py -- --export --tex 2048
  then blender/runtime_bake.py and tools/publish_scene_room.py (docs/SCENE_ROOMS_PIPELINE.md)
Axes: metres, +Z up. The wharf deck is z = 0, its river face along x = -2.2; the river ice is z = -1.8. The ship's
keel runs along +Y (bow north) at x = -6.9. The reader is at the origin looking west-north-west.
"""
import bpy, bmesh, math, random, sys, os, time, shutil
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wotw_kit as K
import frankenstein_kit as F
from frankenstein_kit import (new_mat, node, math_, mix_rgb, mix_f, maprange, bump_from, c4, obj_xyz, noise_tex, white,
                              combine, tone_ramp, wood, planks, paint, metal, fabric, plain, box, cyl, sphere, torus, lathe,
                              tube, mesh_from, anchor, camera, TWO_PI, fbm, sstep)

args, scene = K.begin("ArchangelQuay", "out/archangel-quay", seed=1796)
if not os.environ.get("FABLE_GPU"): scene.cycles.device = "CPU"     # the shared Mac's GPU is short of memory
OUT = K.OUT
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rnd = random.Random(1796)
T0 = time.time()
def log(*a): print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)

EYE = 1.55
LOOK_AZ = -62.0                             # compass-style: 0 = +Y, -90 = -X
SUN_AZ, SUN_EL = -125.0, 7.0                # behind the overcast, low in the south-west
def az_dir(az): a = math.radians(az); return Vector((math.sin(a), math.cos(a), 0.0))
SUN_DIR = (az_dir(SUN_AZ) * math.cos(math.radians(SUN_EL)) + Vector((0, 0, math.sin(math.radians(SUN_EL))))).normalized()
S_ = np.array(SUN_DIR)
ICE = -1.8                                   # the river ice
EDGE = -2.2                                  # the wharf's river face
R_NEAR, R_GEO, R_SKY = 40.0, 1000.0, 1150.0
SX, SY = -6.9, 22.0                          # the ship's centreline x and her midships y
WY0, WY1 = -9.0, 40.0                        # the wharf runs along the river from WY0 to WY1
BANK_X = -480.0                              # the far bank

def shiphalf(y):
    y = np.asarray(y, np.float64)
    return np.interp(y, [-15.0, -12.0, -6.0, 2.0, 8.0, 12.0, 14.5, 15.5], [2.6, 3.3, 3.8, 3.9, 3.6, 2.7, 1.4, 0.15]) * 1.02

# ============================================================================= the ground: the bank, the frozen river, the far bank
def ground_z(x, y):
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    land = 0.02 + 0.18 * (fbm(x / 6.0, y / 6.0, 3, seed=1) - 0.5) + 0.06 * x * sstep(10.0, 60.0, x) * 0.05
    # drifts against the warehouse fronts and the wharf's back
    river = ICE + 0.10 * (fbm(x / 9.0, y / 9.0, 4, seed=2) - 0.5) + 0.12 * sstep(0.55, 0.8, fbm(x / 3.0 + y / 9.0, y / 3.0 - x / 9.0, 3, seed=3))
    # ice heaped up against the hull and pressure-cracked along the wharf
    dsh = np.abs(x - SX) - shiphalf(y - SY)
    river = river + 0.45 * np.exp(-np.maximum(dsh, 0) / 1.2) * (np.abs(y - SY) < 16)
    far = ICE + 9.0 * sstep(BANK_X + 40.0, BANK_X - 60.0, x) + 3.0 * (fbm(x / 60.0, y / 60.0, 3, seed=4) - 0.5) * sstep(BANK_X + 40.0, BANK_X - 60.0, x)
    river = np.where(x < BANK_X + 40.0, np.maximum(river, far), river)
    land = np.where(x < 8.6, -0.25, land)          # under the wharf deck
    t = sstep(EDGE - 0.6, EDGE + 0.2, x)
    return river * (1 - t) + land * t

def gz(x, y): return ground_z(x, y)
def slope_of(x, y, e=0.3):
    return (ground_z(x + e, y) - ground_z(x - e, y)) / (2 * e), (ground_z(x, y + e) - ground_z(x, y - e)) / (2 * e)

def snow_albedo(x, y, fp):
    n1 = fbm(x / 5.0, y / 5.0, 4, seed=11)
    col = np.stack([0.66 + 0.04 * n1, 0.68 + 0.04 * n1, 0.72 + 0.03 * n1], -1)
    river = (x < EDGE)
    # on the river: wind-packed snow in long drifts, scoured grey ice between, a sledge road across far out
    wx, wy = math.cos(math.radians(20)), math.sin(math.radians(20))
    a_ = x * wx + y * wy; b_ = -x * wy + y * wx
    sas = fbm(a_ / 3.0, b_ / 0.5, 4, seed=12)
    col = col * (1 - (0.08 * sstep(0.5, 0.75, sas) * sstep(1.0, 0.1, fp))[..., None] * np.array([1.0, 0.85, 0.6]))
    bare = sstep(0.60, 0.70, fbm(x / 18.0, y / 18.0, 4, seed=13)) * river
    col = col * (1 - bare[..., None]) + np.array([0.38, 0.44, 0.48]) * (0.9 + 0.2 * n1[..., None]) * bare[..., None]
    road = sstep(3.0, 1.5, np.abs(y - 0.35 * x - 140.0)) * river * sstep(EDGE - 40.0, EDGE - 120.0, x)
    col = col * (1 - 0.12 * road[..., None] * np.array([1.0, 0.92, 0.8]))
    # on the bank: trodden, sooty snow round the warehouses and the wharf's back, straw and dung in the lanes
    land = (x >= EDGE)
    trod = land * sstep(0.45, 0.6, fbm(x / 1.4, y / 1.4, 3, seed=14)) * 0.22
    col = col * (1 - trod[..., None] * np.array([0.9, 0.95, 1.0]))
    dirt = land * sstep(0.62, 0.7, fbm(x / 0.5, y / 0.5, 3, seed=15)) * 0.25
    col = col * (1 - dirt[..., None]) + np.array([0.30, 0.25, 0.19]) * dirt[..., None]
    # the far bank: snow under the forest edge, greyer
    fb = sstep(BANK_X + 40.0, BANK_X - 40.0, x)
    col = col * (1 - 0.15 * fb[..., None])
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

NS = 84
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



# ============================================================================= the ship (keel along +Y, centreline x = SX)
def interp1(table, x):
    xs = [p[0] for p in table]; ys = [p[1] for p in table]
    return float(np.interp(x, xs, ys))
RAIL = [(-15.0, 4.6), (-10.0, 4.05), (-3.0, 3.75), (4.0, 3.75), (10.0, 4.0), (15.5, 4.7)]
LIST = math.radians(0.8)                      # sitting all but upright in the river ice
def rail_z(y): return interp1(RAIL, y)
KEEL = -3.9
def sect(s): return (1.0 - (1.0 - max(0.0, min(1.0, s))) ** 2.6) ** 0.5
def hb(y, z):
    top = rail_z(y); s = (z - KEEL) / (top - KEEL)
    tum = 1.0 - 0.06 * sstep(0.78, 1.0, s)
    return max(0.02, float(shiphalf(y)) / 1.02 * sect(s / 0.86) * tum)
SHIP_M = Matrix.Translation((SX, SY, ICE)) @ Matrix.Rotation(-LIST, 4, 'Y')
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


# ============================================================================= the wharf: log crib face, plank deck, kerb, bollards
M_DECK = planks("M_WharfDeck", 0.24, 5.0, [(0.16, 0.13, 0.10), (0.20, 0.16, 0.12), (0.13, 0.11, 0.09), (0.22, 0.18, 0.14)],
                (0.03, 0.025, 0.02), rough=0.8, seed=7.0, grain_k=0.6, bumpk=0.4, gap_w=0.025,
                coords=lambda nt, xyz, X, Y, Z: (Y, X),
                wear=lambda nt, X, Y, Z: maprange(nt, noise_tex(nt, combine(nt, X, Y, Z), 0.6, 4.0, 0.6).outputs["Fac"], 0.5, 0.75, 0.0, 0.8))
M_LOG = wood("M_CribLog", (0.20, 0.16, 0.12), (0.09, 0.07, 0.05), rough=0.85, along='Y', scale=1.5, seed=8.0, contrast=0.6)
M_LOGWALL = wood("M_WarehouseLogs", (0.17, 0.13, 0.09), (0.07, 0.05, 0.035), rough=0.85, along='X', scale=1.2, seed=9.0, contrast=0.6)
M_ROOFSNOW = paint("M_RoofSnow", (0.64, 0.67, 0.72), rough=0.85, mottle=0.1, scale=6.0, bumpk=0.3)
M_DOOR = wood("M_DoorBoards", (0.11, 0.08, 0.06), (0.05, 0.035, 0.025), rough=0.8, along='Z', scale=2.0, seed=10.0, contrast=0.5)
M_TAR = paint("M_TarredRope", (0.10, 0.08, 0.06), rough=0.7, mottle=0.3, scale=40.0)
M_CRATE = wood("M_CrateBoards", (0.36, 0.29, 0.20), (0.20, 0.15, 0.10), rough=0.8, along='X', scale=3.0, seed=11.0, contrast=0.5)
M_LANTERNGLASS = plain("M_LanternGlass", (0.95, 0.78, 0.45), rough=0.2, emission=(1.0, 0.72, 0.38), strength=2.0)

# the crib face: horizontal logs from the ice up to the deck, notched cross-ties showing every few metres
z = ICE - 0.35; k = 0
while z < -0.05:
    r = 0.16 + 0.02 * math.sin(k * 1.7)
    cyl(f"Crib{k}", r, WY1 - WY0 + 0.4 * (k % 2), (EDGE - r * 0.8, (WY0 + WY1) / 2 + 0.2 * (k % 2), z + r), M_LOG, verts=10, rot=(math.pi / 2, 0, 0))
    z += r * 1.85; k += 1
for y in np.arange(WY0 + 1.0, WY1, 3.1):
    for zz in (ICE + 0.2, -0.75):
        cyl(f"Tie{y:.1f}_{zz:.1f}", 0.15, 0.5, (EDGE - 0.35, y, zz), M_LOG, verts=8, rot=(0, math.pi / 2, 0))
box("Deck", (8.0 - EDGE, WY1 - WY0, 0.16), ((EDGE + 8.0) / 2, (WY0 + WY1) / 2, -0.08), M_DECK)
cyl("Kerb", 0.15, WY1 - WY0, (EDGE + 0.15, (WY0 + WY1) / 2, 0.11), M_LOG, verts=10, rot=(math.pi / 2, 0, 0))
# timber fenders hung against the face where the ship lies
for y in np.arange(SY - 13.0, SY + 12.0, 2.6):
    box(f"Fender{y:.1f}", (0.22, 0.3, 1.9), (EDGE - 0.45, y, -0.95), M_LOG, rot=(0, 0.06, 0))

BOLLARDS = [(EDGE + 0.7, -6.5), (EDGE + 0.7, 4.6), (EDGE + 0.7, 15.0), (EDGE + 0.7, 27.0), (EDGE + 0.7, 37.5)]
def bollard(name, x, y):
    lathe(name, [(0.0, 0.0), (0.2, 0.0), (0.2, 0.06), (0.15, 0.1), (0.14, 0.42), (0.19, 0.48), (0.2, 0.55), (0.12, 0.6), (0.0, 0.6)], (x, y, 0.0), M_IRON, steps=16)
    # snow drifted against the north-east (windward) side, a cap on the top
    sphere(name + "Drift", 0.42, (x + 0.25, y + 0.22, 0.0), M_SNOWCAP, seg=10, scale=(1.3, 1.0, 0.45))
    sphere(name + "Cap", 0.16, (x, y, 0.6), M_SNOWCAP, seg=8, scale=(1.0, 1.0, 0.35))
for i, (x, y) in enumerate(BOLLARDS): bollard(f"Bollard{i}", x, y)
# mooring: hawsers from the bow and stern to the bollards, a chain from the stern bollard
STERN_P = Vector(W((hb(-13.5, rail_z(-13.5) - 0.8) + 0.05, -13.5, rail_z(-13.5) - 0.8)))
BOW_P = Vector(W((hb(13.0, rail_z(13.0) - 0.9) + 0.05, 13.0, rail_z(13.0) - 0.9)))
rope("SternLine", STERN_P, Vector((BOLLARDS[1][0], BOLLARDS[1][1], 0.45)), 0.04, sag=0.5, sides=6)
rope("SternSpring", STERN_P + Vector((0, 2.0, 0.2)), Vector((BOLLARDS[2][0], BOLLARDS[2][1], 0.45)), 0.035, sag=0.4, sides=6)
rope("BowLine", BOW_P, Vector((BOLLARDS[4][0], BOLLARDS[4][1], 0.45)), 0.04, sag=0.5, sides=6)
rope("BowSpring", BOW_P - Vector((0, 2.0, -0.2)), Vector((BOLLARDS[3][0], BOLLARDS[3][1], 0.45)), 0.035, sag=0.4, sides=6)
# the gangway from the ship's waist down to the wharf
GY = -4.0
g_top = Vector(W((hb(GY, rail_z(GY)) - 0.05, GY, rail_z(GY) + 0.02))); g_bot = Vector((EDGE + 1.6, SY + GY - 0.4, 0.02))
gd = (g_bot - g_top); gl = gd.length
G = box("Gangway", (0.75, gl, 0.06), tuple((g_top + g_bot) / 2), M_CRATE)
G.rotation_euler = (gd.normalized().to_track_quat('Y', 'Z')).to_euler()
for k in range(int(gl / 0.4)):
    p = g_top.lerp(g_bot, (k + 0.5) / int(gl / 0.4))
    c = box(f"GangwayCleat{k}", (0.7, 0.05, 0.04), tuple(p + Vector((0, 0, 0.05))), M_CRATE)
    c.rotation_euler = G.rotation_euler.copy()
for s_ in (-1, 1):
    rope(f"GangwayRope{s_}", g_top + Vector((0, s_ * 0.4, 0.9)), g_bot + Vector((0, s_ * 0.4, 0.8)), 0.014, sag=0.25, sides=3)
    cyl(f"GangwayStanchion{s_}", 0.03, 0.85, tuple(g_bot + Vector((0, s_ * 0.4, 0.42))), M_SPAR, verts=6)

# ============================================================================= the stores on the wharf
def cask(name, p, s=1.0, lying=False, rot=0.0, snow=True):
    prof = [(0.0, 0.0), (0.24 * s, 0.0), (0.28 * s, 0.15 * s), (0.30 * s, 0.35 * s), (0.28 * s, 0.55 * s), (0.24 * s, 0.70 * s), (0.0, 0.70 * s)]
    if lying:
        o = lathe(name, [(r_, h - 0.35 * s) for r_, h in prof], (p[0], p[1], p[2] + 0.30 * s), M_CASK, steps=14)
        o.rotation_euler = (math.pi / 2, 0, rot)
        for zz in (-0.23, 0.23):
            t = torus(name + f"Hoop{zz}", 0.275 * s, 0.012, (p[0] + math.sin(rot) * zz * s * -1, p[1] + math.cos(rot) * zz * s, p[2] + 0.30 * s), M_IRON, seg=14, rseg=3, rot=(math.pi / 2, 0, rot))
        if snow: sphere(name + "Snow", 0.22 * s, (p[0], p[1], p[2] + 0.58 * s), M_SNOWCAP, seg=8, scale=(0.9, 1.6, 0.25))
        return o
    o = lathe(name, prof, p, M_CASK, steps=14)
    for zz in (0.12, 0.58):
        torus(name + f"Hoop{zz}", 0.27 * s, 0.012, (p[0], p[1], p[2] + zz * s), M_IRON, seg=14, rseg=3)
    if snow: sphere(name + "Cap", 0.25 * s, (p[0], p[1], p[2] + 0.70 * s), M_SNOWCAP, seg=10, scale=(1.0, 1.0, 0.2))
    return o
for k, (x, y, s, ly, r) in enumerate(((1.7, -2.2, 0.95, False, 0), (2.35, -1.6, 0.95, False, 0), (2.25, -2.75, 0.95, False, 0),
                                      (2.3, -2.2, 0.95, False, 0), (1.5, -3.2, 0.9, True, 0.4), (3.4, -0.6, 1.0, False, 0),
                                      (0.8, 6.2, 0.95, False, 0), (1.4, 6.6, 0.95, False, 0), (1.1, 7.3, 0.9, True, 1.3))):
    zb = 0.70 * 0.95 if (k == 3) else 0.0
    cask(f"Cask{k}", (x, y, zb), s, ly, r, snow=True)
def crate(name, c, size, rot=0.0):
    box(name, size, (c[0], c[1], c[2] + size[2] / 2), M_CRATE, bevel=0.01, rot=(0, 0, rot))
    for sx in (-1, 1):
        box(name + f"Batten{sx}", (0.06, size[1] + 0.02, size[2] + 0.02), (c[0] + sx * (size[0] / 2 - 0.08) * math.cos(rot), c[1] + sx * (size[0] / 2 - 0.08) * math.sin(rot), c[2] + size[2] / 2),
            M_CRATE, rot=(0, 0, rot))
    box(name + "Snow", (size[0] - 0.04, size[1] - 0.04, 0.05), (c[0], c[1], c[2] + size[2] + 0.02), M_SNOWCAP, bevel=0.022, rot=(0, 0, rot))
crate("Crate0", (3.2, 2.4, 0.0), (1.0, 0.7, 0.6), 0.2)
crate("Crate1", (3.25, 2.45, 0.6), (0.8, 0.6, 0.5), 0.35)
crate("Crate2", (4.3, 2.9, 0.0), (0.9, 0.7, 0.55), -0.15)
crate("Crate3", (2.6, 9.5, 0.0), (1.2, 0.8, 0.7), 0.05)
crate("Crate4", (3.0, 10.4, 0.0), (0.9, 0.7, 0.6), 0.5)
# coils of tarred hemp, flat on the deck
def coil(name, x, y, R0=0.42, turns=5, r=0.035, layers=2):
    for L in range(layers):
        for t in range(turns):
            torus(f"{name}_{L}_{t}", R0 - t * r * 2.05, r, (x, y, r + L * r * 1.9), M_TAR, seg=14, rseg=4)
    sphere(name + "Snow", R0 * 0.9, (x, y, layers * r * 1.9 + 0.01), M_SNOWCAP, seg=10, scale=(1.0, 1.0, 0.08))
coil("Coil0", -0.6, 2.4); coil("Coil1", 0.4, 3.3, 0.36, 4, 0.03, 3); coil("Coil2", -1.1, -3.0, 0.45, 5, 0.04, 2)
coil("Coil3", 1.9, 12.0, 0.4)
# a sledge's worth of firewood stacked against the crates, a hand-barrow, a capstan bar
for k in range(18):
    x = 4.7 + (k % 6) * 0.0; y = 1.6 + (k % 6) * 0.17 - 0.4; zz = 0.08 + (k // 6) * 0.15
    cyl(f"Billet{k}", 0.075, 0.9, (5.0, y + (k // 6) * 0.08, zz), M_LOG, verts=7, rot=(0, math.pi / 2, 0.05 * (k % 3)))
box("BarrowBed", (1.4, 0.6, 0.08), (0.6, -5.4, 0.42), M_CRATE, rot=(0, -0.25, 0.4))
for sx in (-1, 1):
    tube(f"BarrowHandle{sx}", [(0.6 - 0.7 * math.cos(0.4) - sx * 0.3 * math.sin(0.4) * 0, -5.4 - 0.7 * math.sin(0.4) + sx * 0.3, 0.6), (0.6 + 1.1 * math.cos(0.4), -5.4 + 1.1 * math.sin(0.4) + sx * 0.3, 0.25)], 0.025, M_CRATE, sides=5)
# the lantern on its post at the head of the gangway
LP = Vector((EDGE + 1.3, 15.8, 0.0))
cyl("LanternPost", 0.08, 2.5, tuple(LP + Vector((0, 0, 1.25))), M_LOG, verts=8)
tube("LanternArm", [tuple(LP + Vector((0, 0, 2.35))), tuple(LP + Vector((-0.45, 0, 2.38)))], 0.025, M_IRON, sides=5)
LANT = LP + Vector((-0.45, 0, 2.05))
box("LanternGlass", (0.16, 0.16, 0.22), tuple(LANT), M_LANTERNGLASS)
for dx in (-1, 1):
    for dy in (-1, 1):
        box(f"LanternFrame{dx}{dy}", (0.02, 0.02, 0.26), tuple(LANT + Vector((dx * 0.085, dy * 0.085, 0))), M_IRON)
lathe("LanternHood", [(0.0, 0.0), (0.13, 0.0), (0.09, 0.07), (0.03, 0.12), (0.02, 0.2), (0.0, 0.2)], tuple(LANT + Vector((0, 0, 0.12))), M_IRON, steps=8)
box("LanternBase", (0.2, 0.2, 0.03), tuple(LANT + Vector((0, 0, -0.12))), M_IRON)
# snow lying in patches on the deck, swept from the gangway and the stores
for k in range(10):
    x = rnd.uniform(EDGE + 0.6, 8.0); y = rnd.uniform(WY0 + 0.5, WY1 - 0.5)
    if math.hypot(x, y) < 1.4 or abs(y - (SY + GY)) < 1.5: continue
    sphere(f"DeckSnow{k}", rnd.uniform(0.3, 0.6), (x, y, -0.03), M_SNOWCAP, seg=8, scale=(rnd.uniform(0.6, 1.0), rnd.uniform(1.5, 3.0), 0.08))
# broken river ice heaved up along the wharf face and round the hull, older floes frozen in further out
M_RIVERICE = paint("M_RiverIce", (0.52, 0.60, 0.65), rough=0.35, mottle=0.25, scale=3.0, bumpk=0.3)
for k in range(70):
    if k < 30:
        y = rnd.uniform(WY0, WY1); x = EDGE - rnd.uniform(0.4, 1.4)
        if abs(y - SY) < 15.5: x = SX + float(shiphalf(y - SY)) + rnd.uniform(0.1, 0.7)
    else:
        a = rnd.uniform(-2.6, -0.4); r = rnd.uniform(8, 70); x, y = EDGE - 2 + r * math.cos(a) * 1.0 - 4, r * math.sin(a) * 0.0 + rnd.uniform(-30, 60)
        x = EDGE - rnd.uniform(6, 80)
        if abs(x - SX) < 5 and abs(y - SY) < 17: continue
    sz = rnd.uniform(0.35, 1.0) * (1.0 if k < 30 else 1.4)
    o = box(f"IceSlab{k}", (sz * rnd.uniform(1.0, 1.9), sz * rnd.uniform(0.7, 1.2), sz * rnd.uniform(0.15, 0.3)),
            (x, y, float(gz(x, y)) + sz * 0.05), M_RIVERICE if rnd.random() < 0.55 else M_SNOWCAP, bevel=sz * 0.08,
            rot=(rnd.uniform(-0.6, 0.6), rnd.uniform(-0.5, 0.5), rnd.uniform(0, math.pi)))
# low snow banks along the back of the wharf and against the kerb
for k in range(16):
    y = WY0 + 1.0 + k * (WY1 - WY0 - 2.0) / 15
    sphere(f"BankBack{k}", 1.1, (8.4, y + rnd.uniform(-0.5, 0.5), -0.15), M_SNOWCAP, seg=8, scale=(1.0, 1.9, 0.35))
    if abs(y - SY - GY) > 2.0 and abs(y) > 2.5:
        sphere(f"BankKerb{k}", 0.4, (EDGE + 0.45, y + rnd.uniform(-0.5, 0.5), 0.0), M_SNOWCAP, seg=8, scale=(0.9, 2.2, 0.4))

# ============================================================================= the merchants' warehouses behind the wharf
def warehouse(name, x0, yc, w, d, eave, ridge):
    """Two-storey log store, gable to the river: horizontal logs with notched corners, a steep board roof thick with
    snow, double doors and a loading door under a hoist beam in the gable."""
    for k, z in enumerate(np.arange(0.0, eave, 0.28)):
        r = 0.15
        cyl(f"{name}LogF{k}", r, w + 0.5, (x0, yc, z + r), M_LOGWALL, verts=8, rot=(math.pi / 2, 0, 0))
        cyl(f"{name}LogB{k}", r, w + 0.5, (x0 + d, yc, z + r), M_LOGWALL, verts=6, rot=(math.pi / 2, 0, 0))
    for sy in (-1, 1):
        box(f"{name}Side{sy}", (d, 0.3, eave), (x0 + d / 2, yc + sy * w / 2, eave / 2), M_LOGWALL)
    # the gable triangle, boarded
    g = [(x0 - 0.02, yc - w / 2, eave), (x0 - 0.02, yc + w / 2, eave), (x0 - 0.02, yc, ridge)]
    mesh_from(f"{name}Gable", g, [(0, 2, 1)], M_DOOR)
    gb = [(x0 + d + 0.02, yc - w / 2, eave), (x0 + d + 0.02, yc + w / 2, eave), (x0 + d + 0.02, yc, ridge)]
    mesh_from(f"{name}GableB", gb, [(0, 1, 2)], M_DOOR)
    # the roof: two snow-laden slopes with board ends showing at the eaves
    for sy in (-1, 1):
        a = (x0 - 0.5, yc, ridge + 0.15); b_ = (x0 + d + 0.5, yc, ridge + 0.15)
        c = (x0 + d + 0.5, yc + sy * (w / 2 + 0.6), eave - 0.25); dd = (x0 - 0.5, yc + sy * (w / 2 + 0.6), eave - 0.25)
        mesh_from(f"{name}Roof{sy}", [a, b_, c, dd], [(3, 2, 1, 0) if sy < 0 else (0, 1, 2, 3)], M_ROOFSNOW)
        box(f"{name}Eave{sy}", (d + 1.0, 0.1, 0.14), (x0 + d / 2, yc + sy * (w / 2 + 0.6), eave - 0.32), M_DOOR)
    box(f"{name}Barge", (0.12, 0.12, 0.12), (x0 - 0.52, yc, ridge + 0.1), M_DOOR)
    box(f"{name}Doors", (0.08, 2.4, 2.4), (x0 - 0.12, yc, 1.2), M_DOOR, bevel=0.01)
    box(f"{name}DoorBar", (0.1, 2.6, 0.12), (x0 - 0.18, yc, 1.3), M_IRON)
    box(f"{name}Loft", (0.08, 1.2, 1.4), (x0 - 0.1, yc, eave + 0.4), M_DOOR, bevel=0.01)
    box(f"{name}Hoist", (1.2, 0.2, 0.22), (x0 - 0.4, yc, ridge - 0.9), M_LOGWALL)
    box(f"{name}Step", (0.6, 2.8, 0.25), (x0 - 0.4, yc, 0.12), M_LOG)
for k, (yc, w, d, e, rdg) in enumerate(((-31.0, 9.0, 13.0, 4.4, 8.0), (-19.0, 10.0, 14.0, 4.8, 8.6), (-6.5, 9.0, 14.0, 4.6, 8.4), (5.5, 10.0, 16.0, 5.0, 9.2), (18.5, 9.0, 14.0, 4.4, 8.0), (30.5, 10.0, 15.0, 4.8, 8.8))):
    warehouse(f"Store{k}", 10.5 + (k % 2) * 0.8, yc, w, d, e, rdg)
# log houses of the merchants' quarter further back, smaller, and a wooden church with a tented roof and onion dome
for k, (x0_, yc_, w_, d_) in enumerate(((32.0, -14.0, 7.0, 8.0), (34.0, 0.0, 6.0, 7.0), (31.0, 13.0, 7.0, 8.0), (36.0, 27.0, 6.5, 7.0), (44.0, -6.0, 6.0, 7.0), (45.0, 20.0, 6.0, 6.0))):
    warehouse(f"House{k}", x0_, yc_, w_, d_, 3.4, 6.2)
CH = Vector((52.0, 6.0, 0.0))
box("ChurchBody", (8.0, 6.0, 7.0), tuple(CH + Vector((0, 0, 3.5))), M_LOGWALL)
cyl("ChurchTent", 3.2, 7.0, tuple(CH + Vector((0, 0, 10.5))), M_ROOFSNOW, verts=8, r2=0.4)
cyl("ChurchDrum", 0.7, 1.4, tuple(CH + Vector((0, 0, 14.5))), M_LOGWALL, verts=10)
sphere("ChurchDome", 1.0, tuple(CH + Vector((0, 0, 15.9))), M_DOOR, seg=12, scale=(1, 1, 1.3))
cyl("ChurchCross", 0.06, 2.0, tuple(CH + Vector((0, 0, 18.0))), M_IRON, verts=4)
box("ChurchCrossBar", (0.9, 0.08, 0.08), tuple(CH + Vector((0, 0, 18.4))), M_IRON)
# the lane between the wharf and the stores: a hitching rail
for y in (-1.5, 11.8, 24.6):
    box(f"Rail{y}", (0.1, 2.6, 0.1), (9.2, y, 1.0), M_LOG)
    for sy in (-1, 1): cyl(f"RailPost{y}{sy}", 0.07, 1.1, (9.2, y + sy * 1.2, 0.55), M_LOG, verts=6)

# ============================================================================= the ensign at the stern
fl_img = np.zeros((48, 96, 4), np.float32); fl_img[..., 3] = 1
fl_img[..., :3] = np.array([0.55, 0.06, 0.05])
can = fl_img[:24, :48]
can[..., :3] = np.array([0.08, 0.12, 0.35])
yy, xx = np.mgrid[0:24, 0:48].astype(np.float32)
diag = (np.abs(yy / 24 - xx / 48) < 0.08) | (np.abs(yy / 24 - (1 - xx / 48)) < 0.08)
can[diag, :3] = np.array([0.85, 0.84, 0.80])
cross_w = (np.abs(xx - 24) < 5) | (np.abs(yy - 12) < 5)
can[cross_w, :3] = np.array([0.85, 0.84, 0.80])
cross_r = (np.abs(xx - 24) < 3) | (np.abs(yy - 12) < 3)
can[cross_r, :3] = np.array([0.55, 0.06, 0.05])
M_FLAG = K.card_material("M_Ensign", K.image_from("T_Ensign", fl_img[::-1].copy()), rough=0.9, clip=False)
K.KEEP_UV.add(M_FLAG.name); K.PREBAKED.add(M_FLAG.name)
STAFF0 = Vector(W((0, -15.3, rail_z(-15.0) + 0.1)))
tube("EnsignStaff", [tuple(STAFF0), tuple(STAFF0 + Vector((0, -0.9, 3.2)))], 0.03, M_SPAR, sides=6)
top = STAFF0 + Vector((0, -0.9 * 0.97, 3.2 * 0.97))
fv, ff, fu = [], [], []
NU, NV = 10, 6
for j in range(NV + 1):
    for i in range(NU + 1):
        u = i / NU; v = j / NV
        droop = 1.1 * u * u
        fv.append(tuple(top + Vector((0.08 * math.sin(u * 7 + v * 2) * u, -0.02 - 1.4 * u * 0.55, -droop - 0.9 * v)))); fu.append((u, 1 - v))
for j in range(NV):
    for i in range(NU):
        ff.append((j * (NU + 1) + i, j * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i))
FLAG = mesh_from("Ensign", fv, ff, M_FLAG, uvs=fu, smooth=True)
K.set_weight(FLAG, lambda p: min(1.0, max(0.0, (p - top).length / 1.6))); K.WEIGHTED.add(M_FLAG.name)

# ============================================================================= the sky: overcast late afternoon, the far bank's forest, the town
SKY_EL0 = -12.0
def sky_v_of(el): return ((el - SKY_EL0) / (90.0 - SKY_EL0)) ** 0.55
def sky_el_of_v(v): return SKY_EL0 + (90.0 - SKY_EL0) * v ** (1 / 0.55)
def paint_sky(W_=4096, Hh=1024):
    az = (np.arange(W_) + 0.5) / W_ * 360.0; v = (np.arange(Hh) + 0.5) / Hh; el = sky_el_of_v(v)
    AZ, EL = np.meshgrid(az, el)
    azr, elr = np.radians(AZ), np.radians(EL)
    dxs, dys, dzs = np.cos(elr) * np.sin(azr), np.cos(elr) * np.cos(azr), np.sin(elr)
    cg = np.clip(dxs * S_[0] + dys * S_[1] + dzs * S_[2], -1, 1); ang = np.degrees(np.arccos(cg))
    toward = np.clip(cg, 0, 1)
    e = np.clip(EL, 0, 90)[..., None]
    zen = np.array([0.40, 0.42, 0.46]); hor = np.array([0.70, 0.70, 0.71])
    f = (e / 90.0) ** 0.5
    col = hor * (1 - f) + zen * f
    # a paler, warmer glow where the sun is behind the cloud
    col = col + (0.25 * np.exp(-(ang / 18.0) ** 2) + 0.10 * np.exp(-(ang / 45.0) ** 2))[..., None] * np.array([1.0, 0.92, 0.80])
    # the cloud deck: soft lumpy stratocumulus, darker bases
    k = 1.0 / (np.maximum(dzs, 0.02) + 0.05)
    pu, pv = dxs * k, dys * k
    cl = fbm(pu * 0.35, pv * 0.35, 5, seed=81)
    col = col * (0.86 + 0.22 * cl[..., None])
    # below the horizon: river ice, hazy
    below = EL < 0.0
    col = np.where(below[..., None], np.array([0.58, 0.60, 0.63]), col)
    # the far bank (west half): a low snowy bank and the dark spruce forest above it, ragged tops, hazed blue-grey
    rel = (AZ + 180.0) % 360.0 - 180.0                    # -180..180, 0 = north
    west = sstep(-10.0, -25.0, rel) * sstep(-178.0, -165.0, rel) + sstep(-178.0, -175.0, rel) * 0.0
    bank_el = np.degrees(np.arctan2(9.0 + ICE * 0 - (EYE - ICE) + ICE * 0, np.abs(BANK_X) / np.maximum(np.abs(np.sin(np.radians(rel))), 0.2)))
    # spruce tops: a row of narrow spires of random height (one per ~0.1 degree), a ragged canopy line below them
    kk = AZ / 0.11; idx = np.floor(kk).astype(np.int64); fr = kk - idx
    hr = (np.sin(idx * 12.9898) * 43758.5453) % 1.0
    spire = (1.0 - 2.0 * np.abs(fr - 0.5)) ** 0.8 * (0.6 + 1.1 * hr)
    tops = bank_el + 0.45 + 0.25 * fbm(AZ / 1.5, np.zeros_like(AZ), 3, seed=82)[0][None, :] + spire
    forest = (EL >= bank_el - 0.15) & (EL < tops) & (west > 0.5)
    fcol = np.array([0.07, 0.09, 0.09]) * 0.8 + hor * 0.2
    col = np.where(forest[..., None], fcol * (0.92 + 0.12 * fbm(AZ * 4, EL * 30, 2, seed=84)[..., None]), col)
    # the town along the bank to the north: snowy roofs, log houses, the Gostiny Dvor's towers, onion domes
    town = sstep(-6.0, 4.0, rel) * sstep(48.0, 36.0, rel)
    rnd2 = np.random.RandomState(5)
    roofl = np.zeros(W_, np.float32)
    for i in range(140):
        c = rnd2.uniform(-6.0, 46.0); w = rnd2.uniform(0.5, 1.6); h = rnd2.uniform(0.5, 1.1)
        aa = ((az + 180.0) % 360.0 - 180.0)
        m = np.abs(aa - c) < w / 2
        roofl = np.where(m, np.maximum(roofl, h - np.abs(aa - c) * h / (w * 0.6) * 0.6), roofl)
    houses = (EL >= -0.05) & (EL < roofl[None, :] + 0.1) & (town > 0.5)
    hcol = np.array([0.42, 0.42, 0.44]) * 0.6 + hor * 0.4
    col = np.where(houses[..., None], hcol, col)
    for (c, h, w, dome) in ((12.0, 3.2, 0.7, True), (14.0, 2.4, 0.45, True), (27.0, 2.8, 0.6, True), (34.5, 2.0, 1.8, False), (6.0, 2.2, 0.35, True)):
        aa = ((AZ + 180.0) % 360.0 - 180.0)
        body = (np.abs(aa - c) < w / 2) & (EL >= 0) & (EL < h)
        col = np.where(body[..., None], np.array([0.62, 0.61, 0.60]) * 0.7 + hor * 0.3, col)
        if dome:
            dd = np.hypot((aa - c) / (w * 0.55), (EL - h - w * 0.35) / (w * 0.55))
            col = np.where((dd < 1.0)[..., None], np.array([0.30, 0.33, 0.36]) * 0.7 + hor * 0.3, col)
            sp = (np.abs(aa - c) < 0.05) & (EL >= h) & (EL < h + w * 1.3)
            col = np.where(sp[..., None], np.array([0.25, 0.25, 0.25]), col)
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
F.sun("light.sun", 1.6, (1.0, 0.90, 0.78), tuple(SUN_DIR), angle_deg=12.0)
F.sun("light.sky", 1.3, (0.80, 0.84, 0.92), (0.1, 0.2, 1.0), angle_deg=90, shadow=False)
world = bpy.data.worlds.new("Overcast"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.62, 0.64, 0.68, 1); bg.inputs["Strength"].default_value = 0.6

# ============================================================================= sway weights, anchors, living scene
for s, yz in SAILS:
    K.set_weight(s, lambda p, yz=yz: min(0.3, max(0.0, (p.z - yz - 0.05) * 0.8)))
    K.WEIGHTED.add(M_SAIL.name)
anchor("reader.entrance", (0.0, 0.0, 0.0))
lk = az_dir(LOOK_AZ)
anchor("reader.look", (lk.x, lk.y, EYE))
anchor("scene.centre", (0.0, 0.0, 0.0))
anchor("ship.mainmast", tuple(MAIN[0]))
anchor("ship.gangway", tuple(g_bot))
F.fx("fx.lantern.post", tuple(LANT), 0.12)
F.sound("sound.wind.river", (-25.0, 6.0, 1.5))
F.sound("sound.rigging.ship", tuple(MAIN[0] - Vector((0, 0, 4.0))))
F.sound("sound.gulls.river", (-40.0, 30.0, 12.0))
F.sound("sound.wind.stores", (9.0, -2.0, 3.0))

K.apply_all_transforms()

# ============================================================================= cameras
E = Vector((0, 0, EYE))
def ahead(yaw_deg, pitch_deg=0.0, d=10.0):
    a = math.radians(LOOK_AZ - yaw_deg); p = math.radians(pitch_deg)
    return tuple(E + Vector((math.sin(a) * math.cos(p), math.cos(a) * math.cos(p), math.sin(p))) * d)
cams = [
    camera("Cam_Reader", tuple(E), ahead(0, 2), clip_end=1500),
    camera("Cam_Left", tuple(E), ahead(65, 3), clip_end=1500),
    camera("Cam_Right", tuple(E), ahead(-70, 4), clip_end=1500),
    camera("Cam_Behind", tuple(E), ahead(180, 3), clip_end=1500),
    camera("Cam_Ship", (4.0, -8.0, 2.2), (SX, SY, 9.0), lens=18, clip_end=1500),
]
for c in cams: c.data.clip_start = 0.05
K.budget_report()

# reader clearance: 1.5 m ahead, 0.4 m around, at knee, waist and eye height
dg = bpy.context.evaluated_depsgraph_get(); probs = []
for hz in (0.3, 0.9, 1.55):
    o = Vector((0, 0, hz))
    if scene.ray_cast(dg, o, Vector((lk.x, lk.y, 0)), distance=1.5)[0]: probs.append(f"blocked ahead at {hz}")
    for k in range(12):
        a = TWO_PI * k / 12
        if scene.ray_cast(dg, o, Vector((math.cos(a), math.sin(a), 0)), distance=0.4)[0]: probs.append(f"blocked around at {hz} dir {k * 30}")
print("READER CHECK", probs or "ok", flush=True)

if args.render:
    F.render_stills(scene, cams, {}, default_exp=0.0, label="archangel-quay")
    cap = os.path.join(REPO, "captures", "blender", "archangel-quay"); os.makedirs(cap, exist_ok=True)
    for c in cams:
        src = os.path.join(OUT, f"{args.prefix}{c.name[4:].lower()}.png")
        if os.path.exists(src) and not args.quick:
            shutil.copy(src, os.path.join(cap, f"blender-render_archangel-quay_{c.name[4:].lower()}_cycles-{scene.cycles.samples}spp.png"))

if args.bake or args.export:
    T_ = args.tex
    size_for = {"M_Hull": (T_ // 2, T_ // 8), "M_Spar": (T_ // 8, T_ // 16), "M_Yard": (T_ // 8,), "M_Sail": (T_ // 4, T_ // 16),
                "M_SnowCap": (T_ // 4,), "M_Rope": (T_ // 8,), "M_Wale": (T_ // 8,), "M_PaintBand": (T_ // 8,), "M_Iron": (T_ // 8,),
                "M_Cask": (T_ // 4, T_ // 16), "M_SternLights": (32,), "M_WharfDeck": (T_ // 2, T_ // 8), "M_CribLog": (T_ // 4, T_ // 16),
                "M_WarehouseLogs": (T_ // 2, T_ // 8), "M_RoofSnow": (T_ // 4,), "M_DoorBoards": (T_ // 4,), "M_TarredRope": (T_ // 8,),
                "M_CrateBoards": (T_ // 4, T_ // 16), "M_LanternGlass": (32,), "M_RiverIce": (T_ // 8,)}
    F.bake_and_export(scene, "archangel_quay.gltf", size_for,
                      keep_names={"M_far_sky_front": "SkyDome.front", "M_far_sky_back": "SkyDome.back", "M_SnowNear": "MESH_SnowNear",
                                  "M_SnowFar": "MESH_SnowFar", "M_Sail": "cloth.sail.furled", "M_Ensign": "cloth.flag.ensign"},
                      cams=cams, blend_name="archangel_quay_baked.blend")
print("DONE")
