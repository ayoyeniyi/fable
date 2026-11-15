"""
Fable: the Montanvert above the Mer de Glace (Frankenstein, 1818, volume II, chapter 2).

"The ascent is precipitous, but the path is cut into continual and short windings, which enable you to surmount the
perpendicularity of the mountain. ... The pines are not tall or luxuriant, but they are sombre, and add an air of
severity to the scene."
"It was nearly noon when I arrived at the top of the ascent. For some time I sat upon the rock that overlooks the
sea of ice. A mist covered both that and the surrounding mountains. Presently a breeze dissipated the cloud ... The
surface is very uneven, rising like the waves of a troubled sea, descending low, and interspersed by rifts that sink
deep. The field of ice is almost a league in width ... The opposite mountain is a bare perpendicular rock. From the
side where I now stood Montanvert was exactly opposite, at the distance of a league; and above it rose Mont Blanc,
in awful majesty."

The reader stands on the mule path where it tops the ascent, on the steep western flank of the valley about a hundred
metres above the glacier, a little after noon in late summer, the morning's mist lifting. Ahead and to the right the
Mer de Glace runs up the valley: grey, crevassed ice in long swells, dark medial moraines, ogive bands below the far
icefall, banks of grey rubble along its edges. Across it the far side rises in bare granite to the spire of the Dru;
up the valley the great snowy wall at its head (the Grandes Jorasses, the Géant), and on the left, above the dark
pines and boulders of the near slope, the aiguilles. Behind, the valley falls away toward Chamonix under the last of
the mist. No people (Victor and the creature are left out).

Everything is procedural (no downloaded models, textures or HDRIs). The land is one height function (numpy): the
geometry carries it out to 520 m (two terrain discs whose log-polar ground textures put their finest texels at the
reader's feet); beyond that the same land is ray-marched in numpy from the reading place, sun-shaded with cast shadows
and aerial perspective, and painted onto the sky dome (front half 2048 px, back half 1024 px), so the far mountains
cost no geometry and meet the near land without a seam. Spruces are alpha-clipped needle-spray cards with soft
normals; boulders are displaced node-material blobs baked to textures.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet on the path (ground, z = 0), facing up the glacier (+Y)
  anchor.reader.look      eye height (1.55 m), 2 m ahead
  anchor.scene.centre     the reader's feet (the sky dome and fog centre)
  anchor.glacier.edge (the near margin of the ice below), anchor.glacier.far (the icefall at the head)
  light.sun (SUN, high-noon sun from behind the reader's right), light.sky (SUN, cool fill, no shadow)
  SkyDome.front, SkyDome.back (the sky dome with the painted mountains: unlit backdrop), MESH_Mist (soft alpha-blended
  mist banks; no shadows, not lightmapped)
  Living scenes (docs/LIVING_SCENES.md), vertex colour R = sway weight (0 at roots/trunk, 1 at tips):
    veg.crown.spruce (the spruce crowns), veg.shrub.alpenrose, veg.grass.alpine
    sound.wind-trees.0 (the spruces by the path), sound.wind.0 (the open slope above), sound.river.0 (meltwater
    under the ice margin below)
Register as outdoor (Outdoor = true).

Axes: metres, Blender +Z up, +Y up the glacier (the reading direction), +X across it (the glacier lies to the right).
The reader at the origin.

Run headless:
  blender -b -P blender/build_mer_de_glace.py -- --out out/mer-de-glace --pano            (paint the panorama only)
  blender -b -P blender/build_mer_de_glace.py -- --out out/mer-de-glace --render --quick --res 900
  blender -b -P blender/build_mer_de_glace.py -- --out out/mer-de-glace --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os, time
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PANO_ONLY = "--pano" in sys.argv
if PANO_ONLY: sys.argv.remove("--pano")
import wotw_kit as K
import frankenstein_kit as F
from frankenstein_kit import (new_mat, node, math_, mix_rgb, mix_f, maprange, bump_from, c4, obj_xyz, noise_tex, white,
                              combine, tone_ramp, metal, plain, tube, mesh_from, anchor, camera, TWO_PI, paint_stroke,
                              paint_dot, bleed_alpha, CardMesh, fbm, sstep)

args, scene = K.begin("MerDeGlace", "out/mer-de-glace", seed=1816)
OUT = K.OUT
rnd = random.Random(1816)
T0 = time.time()
def log(*a): print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)

EYE = 1.55
SUN_AZ, SUN_EL = 128.0, 34.0            # compass degrees (0 = +Y up the glacier, 90 = +X across it)
def az_dir(az): a = math.radians(az); return Vector((math.sin(a), math.cos(a), 0.0))
SUN_DIR = (az_dir(SUN_AZ) * math.cos(math.radians(SUN_EL)) + Vector((0, 0, math.sin(math.radians(SUN_EL))))).normalized()
S_ = np.array(SUN_DIR)
R_NEAR, R_GEO, R_SKY = 40.0, 520.0, 1150.0

# ============================================================================= the land: one height function
def ridged(x, y, octaves=5, seed=0):
    tot = 0.0; amp = 0.5; f = 1.0; norm = 0.0
    for o in range(octaves):
        n = 1.0 - np.abs(2.0 * K.vnoise(x * f + o * 7.3, y * f - o * 3.1, seed + o) - 1.0)
        tot = tot + amp * n * n; norm += amp; amp *= 0.5; f *= 2.03
    return tot / norm

def glacier_frame(y):
    """Centre line x, half width and ice-surface height of the glacier at y (the valley's axis)."""
    xc = np.where(y >= 0, 420.0 - 400.0 * sstep(0.0, 5200.0, y), 420.0 + 0.05 * y)
    w = 300.0 + 120.0 * sstep(2500.0, 6500.0, y) - 70.0 * sstep(-400.0, -2200.0, y)
    zi = np.where(y >= 0, -95.0 + 0.045 * y + 140.0 * sstep(5600.0, 7600.0, y) + 0.12 * np.maximum(y - 7600.0, 0),
                  np.maximum(-95.0 + 0.16 * y, -900.0))
    return xc, w, zi

# the mountains round the glacier: crest polylines (x, y, crest height above the reader)
CRESTS = [
    [(-900, -3800, 700), (-1100, -2300, 1100), (-1350, -900, 1450), (-1550, 150, 1560), (-2000, 1300, 1620),
     (-2600, 2700, 1500), (-3100, 4600, 1850), (-3500, 6800, 2330), (-2600, 8100, 2050), (-1100, 8900, 2120)],     # our side: Charmoz, Grépon, Blaitière ... Tacul, Géant
    [(-1100, 8900, 2120), (600, 9300, 2150), (2300, 9100, 2300), (3700, 8600, 2200)],                              # the head: the Jorasses wall
    [(3700, 8600, 2200), (3900, 6400, 1800), (3300, 4300, 1650), (2700, 2300, 1700), (2250, 600, 1840),
     (2700, -400, 1700), (3500, -1100, 2200), (3300, -3000, 1500), (2400, -4600, 900)],                              # the far side: Leschaux, the Dru, the Verte
    [(-4500, -5600, 900), (-2500, -5900, 1100), (-500, -5700, 950), (1500, -5800, 1050), (3800, -5500, 800)],      # across the Chamonix valley behind: the Brévent and Aiguilles Rouges
]
SPIRES = [(2250, 600, 1840, 380), (-1550, 150, 1560, 260), (-1350, -900, 1450, 240), (-2000, 1300, 1620, 280), (-1100, 8900, 2120, 300)]

def massif(x, y):
    """The crests as ridges with straight flanks (about 45 degrees, gullied), notched and spired along their tops; the
    named spires as steep cones. Noise is evaluated once for the whole field, not per segment."""
    z = np.full(np.shape(x), -1e4, np.float64)
    if np.min(np.hypot(x, y)) > 1e9: return z
    crag = 0.86 + 0.24 * ridged(x / 420.0, y / 420.0, 3, seed=11)
    flank = 0.95 + 0.35 * fbm(x / 700.0, y / 700.0, 3, seed=12)
    for line in CRESTS:
        for (ax, ay, ah), (bx, by, bh) in zip(line, line[1:]):
            dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
            t = np.clip(((x - ax) * dx + (y - ay) * dy) / L2, 0, 1)
            d = np.hypot(x - (ax + t * dx), y - (ay + t * dy))
            z = np.maximum(z, (ah + (bh - ah) * t) * crag - d * flank)
    for (sx, sy, sh, sr) in SPIRES:
        d = np.hypot(x - sx, y - sy)
        z = np.maximum(z, sh * 1.03 - sh * 0.75 * np.clip(d / (sr * 1.5), 0, 1) ** 0.6 - d * 0.7)
    return z

def path_x(y): return 0.012 * y + 0.00035 * y * y
def path_mask(x, y):
    s = x - path_x(y)
    return s, sstep(160.0, 110.0, np.abs(y))

def land(x, y, detail=1.0, with_path=True):
    """Height (m) above the reader's feet at world (x, y). detail scales the small-scale relief."""
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    xc, w, zi = glacier_frame(y)
    dx = x - xc; d = np.abs(dx); q = d - w; t = np.clip(dx / w, -1, 1)
    waves = (2.2 * np.sin((y + 0.0009 * dx * dx) / 46.0) * (0.5 + fbm(x / 120.0, y / 120.0, 2, seed=3)) +
             1.4 * (fbm(x / 35.0, y / 60.0, 3, seed=4) - 0.5))
    ice = zi + 10.0 * (1 - t * t) + waves * detail * (1 - 0.6 * np.abs(t))
    qp = np.maximum(q, 0.0)
    k = np.where(dx < 0, 1.0, 1.3)
    wall = zi + 8.0 + k * (150.0 * (1 - np.exp(-qp / 250.0)) + 0.25 * qp)
    wall += 15.0 * np.exp(-((q - 22.0) / 13.0) ** 2) - 6.0 * np.exp(-((q - 6.0) / 6.0) ** 2)         # lateral moraine crest
    wall += (18.0 * (fbm(x / 140.0, y / 140.0, 4, seed=5) - 0.5) + 4.0 * (fbm(x / 22.0, y / 22.0, 3, seed=6) - 0.5) * detail) * sstep(0.0, 40.0, q)
    z = np.where(q < 0, ice, wall)
    z = z + (wall - z) * sstep(-14.0, 4.0, q) * (q < 0)
    z = np.maximum(z, massif(x, y) - 700.0 * sstep(160.0, 10.0, q))        # the glacier keeps its bed
    z = z + 70.0 * (ridged(x / 260.0, y / 260.0, 4, seed=9) - 0.4) * sstep(250.0, 900.0, z)        # crags high up
    z = z + 9.0 * (ridged(x / 45.0 + y / 90.0, y / 45.0, 3, seed=10) - 0.45) * sstep(30.0, 250.0, z - zi) * detail   # ribs and gullies
    z = z - OFFS
    if with_path:
        s, m = path_mask(x, y)
        if np.any(m > 0):
            zp = land_path_level(y)
            uphill = sstep(-2.6, -0.85, s); downhill = sstep(2.8, 0.85, s)
            wgt = np.where(s < 0, uphill, downhill) * m
            z = z * (1 - wgt) + zp * wgt
    return z

OFFS = 0.0
OFFS = float(land(np.array(0.0), np.array(0.0), with_path=False))
def land_path_level(y):
    """The path's tread: the slope's height at its centre line, smoothed, a gentle grade."""
    yy = np.asarray(y, np.float64)
    return np.asarray(land(path_x(yy), yy, detail=0.0, with_path=False)) + 0.25 * np.sin(yy / 23.0) * sstep(5, 25, np.abs(yy))
def gz(x, y): return land(x, y)

# ============================================================================= surface classes and colours (shared by the ground textures and the panorama)
def slope_of(x, y, e=2.0, detail=1.0):
    zx = (land(x + e, y, detail) - land(x - e, y, detail)) / (2 * e); zy = (land(x, y + e, detail) - land(x, y - e, detail)) / (2 * e)
    return zx, zy

def albedo(x, y, z, zx, zy, fp):
    """Linear albedo at (x, y): ice with crevasses, moraine bands and ogives; grey rubble; turf, forest, granite;
    snow and hanging ice high up. fp = texel footprint (m) to fade detail finer than a texel."""
    sl = np.hypot(zx, zy)
    xc, w, zi = glacier_frame(y)
    dx = x - xc; q = np.abs(dx) - w; t = dx / w
    fine = sstep(4.0, 0.8, fp)                 # 1 where the texel is fine enough to show small detail
    # ---- granite, turf, forest, snow
    n1 = fbm(x / 9.0, y / 9.0, 4, seed=21); n2 = fbm(x / 60.0, y / 60.0, 4, seed=22)
    rock = np.stack([0.13 + 0.05 * n1, 0.125 + 0.045 * n1, 0.118 + 0.04 * n1], -1) * (0.8 + 0.4 * n2[..., None])
    rock = rock * (1 - 0.35 * sstep(0.55, 0.75, fbm(x / 3.0, y / 25.0, 3, seed=23))[..., None] * fine[..., None])     # dark water streaks
    turf = np.stack([0.055 + 0.04 * n2, 0.068 + 0.03 * n2, 0.028 + 0.012 * n2], -1) * (0.85 + 0.3 * n1[..., None])
    forest = np.array([0.022, 0.034, 0.026]) * (0.8 + 0.4 * fbm(x / 6.0, y / 6.0, 3, seed=24))[..., None]
    rub = fbm(x / 4.0, y / 4.0, 4, seed=25)
    rubble = np.stack([0.15 + 0.07 * rub, 0.145 + 0.06 * rub, 0.135 + 0.05 * rub], -1) * (0.75 + 0.4 * n2[..., None])
    snow = np.array([0.60, 0.63, 0.67]) * (0.92 + 0.08 * n1[..., None])
    # where things grow and lie
    forest_m = sstep(230.0, 120.0, z) * sstep(1.0, 0.65, sl) * sstep(45.0, 90.0, q) * sstep(0.38, 0.5, fbm(x / 50.0, y / 50.0, 4, seed=26) + 0.12 * sstep(120, 0, z))
    turf_m = sstep(420.0, 250.0, z) * sstep(1.7, 1.1, sl) * sstep(35.0, 60.0, q)
    snow_m = np.clip(sstep(850.0, 1150.0, z) * sstep(0.75, 0.5, sl) + sstep(1350.0, 1650.0, z) * sstep(1.1, 0.8, sl), 0, 1)
    snow_m = snow_m * sstep(0.3, 0.45, fbm(x / 90.0, y / 90.0, 4, seed=27) + 0.15 * sstep(900, 1600, z))
    rubble_m = sstep(65.0, 20.0, q) * sstep(-3.0, 3.0, q)
    land_c = rock * (1 - turf_m[..., None]) + turf * turf_m[..., None]
    land_c = land_c * (1 - forest_m[..., None]) + forest * forest_m[..., None]
    land_c = land_c * (1 - rubble_m[..., None]) + rubble * rubble_m[..., None]
    land_c = land_c * (1 - snow_m[..., None]) + snow * snow_m[..., None]
    # ---- the ice
    streak = fbm(dx / 7.0, y / 160.0, 4, seed=31)
    base = 0.31 + 0.10 * (streak - 0.5) + 0.06 * (fbm(x / 20.0, y / 20.0, 3, seed=32) - 0.5)
    ogive = np.sin((y + 0.0016 * dx * dx) / 95.0 * TWO_PI) * sstep(3600, 5200, y) * sstep(7200, 6000, y)
    base = base + 0.05 * ogive
    ice = np.stack([base * 0.95, base * 0.98, base * 1.04], -1)
    dirt = sstep(0.55, 0.95, np.abs(t)) * 0.5 + sstep(0.55, 0.7, fbm(x / 30.0, y / 90.0, 3, seed=33)) * 0.25
    ice = ice * (1 - dirt[..., None]) + np.array([0.20, 0.19, 0.18]) * dirt[..., None]
    for tc, wd in ((-0.42, 0.045), (0.30, 0.035), (0.72, 0.03)):              # medial moraines
        mm = sstep(wd, wd * 0.4, np.abs(t - tc - 0.04 * (fbm(y / 300.0, tc * 9.0, 2, seed=34) - 0.5))) * sstep(-600.0, 300.0, y)
        ice = ice * (1 - mm[..., None]) + rubble * 0.6 * mm[..., None]
    # crevasses: transverse in the middle, chevrons swept up-glacier toward the margins
    zone = np.clip(sstep(0.42, 0.62, fbm(x / 260.0, y / 260.0, 3, seed=35)) + sstep(0.6, 0.85, np.abs(t)) * 0.8, 0, 1)
    ph = (y + 0.75 * np.abs(dx) * sstep(0.25, 0.9, np.abs(t)) + 70.0 * fbm(x / 60.0, y / 60.0, 3, seed=36) + 12.0 * fbm(x / 12.0, y / 12.0, 2, seed=39)) / (17.0 + 10.0 * fbm(x / 200.0, y / 200.0, 2, seed=40))
    fr = ph - np.floor(ph)
    wcr = (0.05 + 0.10 * fbm(x / 40.0, y / 15.0, 3, seed=37)) * zone
    gap = fr / np.maximum(wcr, 1e-4)
    seg_ = sstep(0.42, 0.52, fbm(x / 25.0 + np.floor(ph) * 3.7, y / 25.0, 3, seed=38))      # each crevasse breaks off and starts again
    wcr = wcr * seg_
    crev = (fr < wcr) * fine
    lip = sstep(0.0, 0.03, fr - wcr) * sstep(0.10, 0.03, fr - wcr) * (wcr > 0.02) * fine
    deep = np.clip(1 - np.abs(gap - 0.5) * 2, 0, 1)
    cc = np.array([0.13, 0.19, 0.24]) * (1 - deep[..., None]) + np.array([0.03, 0.05, 0.07]) * deep[..., None]
    ice = ice * (1 - crev[..., None]) + cc * crev[..., None]
    ice = ice * (1 + 0.10 * lip[..., None])
    # broad crevasse fields far off read as grey-blue hatching, not as lines
    far_cr = (1 - fine) * zone * 0.25
    ice = ice * (1 - far_cr[..., None]) + np.array([0.24, 0.30, 0.35]) * far_cr[..., None]
    ice_m = sstep(1.0, -2.0, q) * (y > -1900) * sstep(zi + 30.0 - OFFS, zi + 16.0 - OFFS, z)
    col = land_c * (1 - ice_m[..., None]) + ice * ice_m[..., None]
    return np.clip(col, 0, 1), ice_m, snow_m

# ============================================================================= the panorama on the sky dome
SKY_EL0 = -28.0
def sky_v_of(el): return ((el - SKY_EL0) / (90.0 - SKY_EL0)) ** 0.62
def sky_el_of_v(v): return SKY_EL0 + (90.0 - SKY_EL0) * v ** (1 / 0.62)
SUN_INT, SKY_INT = 3.0, 0.55            # the painted light, matched to light.sun / the world in the Blender stills
SKY_TOP, SKY_HOR = np.array([0.20, 0.29, 0.46]), np.array([0.58, 0.63, 0.70])

def sky_colour(AZ, EL):
    azr, elr = np.radians(AZ), np.radians(EL)
    dxs, dys, dzs = np.cos(elr) * np.sin(azr), np.cos(elr) * np.cos(azr), np.sin(elr)
    e = np.clip(EL, 0, 90)[..., None]
    f = (e / 90.0) ** 0.45
    col = SKY_HOR * (1 - f) + SKY_TOP * f
    cg = np.clip(dxs * S_[0] + dys * S_[1] + dzs * S_[2], -1, 1); ang = np.degrees(np.arccos(cg))
    col = col + (0.9 * np.exp(-(ang / 4.0) ** 2) + 0.22 * np.exp(-(ang / 22.0) ** 2))[..., None] * np.array([1.0, 0.96, 0.88])
    # a high veil of cirrostratus and torn cumulus round the peaks
    k = 1.0 / (np.maximum(dzs, 0.02) + 0.05)
    pu, pv = dxs * k, dys * k
    veil = fbm(pu * 0.6, pv * 0.25, 5, seed=41)
    col = col * (1 - 0.25 * sstep(0.45, 0.75, veil)[..., None]) + np.array([0.70, 0.72, 0.75]) * 0.25 * sstep(0.45, 0.75, veil)[..., None]
    cu = fbm(AZ / 9.0, EL / 3.5, 5, seed=42)
    cum = sstep(0.56, 0.72, cu) * sstep(2.0, 9.0, EL) * sstep(30.0, 14.0, EL)
    shade = 0.70 + 0.35 * sstep(0.5, 0.9, fbm(AZ / 4.0, EL / 2.0 + 3, 3, seed=43))
    col = col * (1 - cum[..., None]) + (np.array([0.66, 0.68, 0.71]) * shade[..., None]) * cum[..., None]
    return col

def build_grid(gd=6.0):
    xs = np.arange(-4500.0, 4500.0 + gd, gd); ys = np.arange(-6200.0, 9800.0 + gd, gd)
    X, Y = np.meshgrid(xs, ys)
    log("grid", X.shape)
    Z = np.empty_like(X)
    for i in range(0, X.shape[0], 400):                 # rows in blocks (memory)
        Z[i:i + 400] = land(X[i:i + 400], Y[i:i + 400], with_path=False)
    return xs, ys, Z

def bilinear(G, xs, ys, x, y):
    gd = xs[1] - xs[0]
    fx = (x - xs[0]) / gd; fy = (y - ys[0]) / gd
    ix = np.clip(np.floor(fx).astype(np.int64), 0, len(xs) - 2); iy = np.clip(np.floor(fy).astype(np.int64), 0, len(ys) - 2)
    tx = np.clip(fx - ix, 0, 1); ty = np.clip(fy - iy, 0, 1)
    if G.ndim == 3: tx, ty = tx[..., None], ty[..., None]
    return (G[iy, ix] * (1 - tx) * (1 - ty) + G[iy, ix + 1] * tx * (1 - ty) + G[iy + 1, ix] * (1 - tx) * ty + G[iy + 1, ix + 1] * tx * ty)

def paint_panorama(W=4096, Hh=1024):
    """Ray-march the land from the reader's eye for every column of the dome (u = azimuth / 360, north = +Y) from
    R_GEO outward; shade each hit with the sun (cast shadows marched toward it), the sky and aerial perspective."""
    xs, ys, Z = build_grid()
    gd = xs[1] - xs[0]
    zy_, zx_ = np.gradient(Z, gd)
    log("albedo grid")
    ALB = np.empty(Z.shape + (3,), np.float32); SNOW = np.empty(Z.shape, np.float32)
    X, Y = np.meshgrid(xs, ys)
    for i in range(0, Z.shape[0], 400):
        a, im, sm = albedo(X[i:i + 400], Y[i:i + 400], Z[i:i + 400], zx_[i:i + 400], zy_[i:i + 400], np.full(X[i:i + 400].shape, gd))
        ALB[i:i + 400] = a; SNOW[i:i + 400] = np.maximum(im, sm)
    del X, Y
    NR = 900
    rr = R_GEO * np.exp(np.linspace(0, math.log(16000.0 / R_GEO), NR))
    az = (np.arange(W) + 0.5) / W * 360.0
    v = (np.arange(Hh) + 0.5) / Hh; el = sky_el_of_v(v)
    tan_el = np.tan(np.radians(el))
    AZ, EL = np.meshgrid(az, el)
    img = sky_colour(AZ, EL)
    hit_r = np.full((Hh, W), np.nan); hit_x = np.zeros((Hh, W)); hit_y = np.zeros((Hh, W))
    log("march")
    for c0 in range(0, W, 256):
        cs = np.arange(c0, min(W, c0 + 256))
        sa, ca = np.sin(np.radians(az[cs])), np.cos(np.radians(az[cs]))
        px = rr[None, :] * sa[:, None]; py = rr[None, :] * ca[:, None]
        inside = (px > xs[0]) & (px < xs[-1]) & (py > ys[0]) & (py < ys[-1])
        h = np.where(inside, bilinear(Z, xs, ys, px, py), -1e4) - EYE - rr[None, :] ** 2 / (2 * 6.371e6)
        ang = h / rr[None, :]
        m = np.maximum.accumulate(ang, axis=1)
        for j, c in enumerate(cs):
            k = np.searchsorted(m[j], tan_el)
            ok = k < NR
            kk = np.minimum(k, NR - 1)
            hit_r[ok, c] = rr[kk[ok]]; hit_x[ok, c] = px[j, kk[ok]]; hit_y[ok, c] = py[j, kk[ok]]
    hm = ~np.isnan(hit_r)
    hx, hy, hr = hit_x[hm], hit_y[hm], hit_r[hm]
    log("shade", hm.sum())
    zx = bilinear(zx_, xs, ys, hx, hy); zy = bilinear(zy_, xs, ys, hx, hy)
    n = np.stack([-zx, -zy, np.ones_like(zx)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    alb = bilinear(ALB, xs, ys, hx, hy); snw = bilinear(SNOW, xs, ys, hx, hy)
    hz = bilinear(Z, xs, ys, hx, hy)
    # cast shadows: march toward the sun from each hit
    lit = np.ones_like(hx)
    for d in np.exp(np.linspace(math.log(12.0), math.log(6000.0), 48)):
        sx, sy, sz = hx + S_[0] * d, hy + S_[1] * d, hz + 2.0 + S_[2] * d
        th = bilinear(Z, xs, ys, sx, sy)
        lit = np.minimum(lit, np.clip((sz - th) / (4.0 + d * 0.01), 0, 1))
    ndl = np.clip(n @ S_, 0, 1)
    sky_vis = 0.55 + 0.45 * n[:, 2]
    rad = alb * (SUN_INT / math.pi * (ndl * lit)[:, None] * np.array([1.0, 0.97, 0.92]) + SKY_INT * sky_vis[:, None] * np.array([0.62, 0.74, 1.0]))
    # snow and ice catch a little more of the blue sky in shade
    rad = rad + (snw * (1 - lit * ndl) * 0.04)[:, None] * np.array([0.5, 0.7, 1.0])
    # aerial perspective (distance), and the mist lying low in the valley behind
    hdir = sky_colour(np.degrees(np.arctan2(hx, hy)) % 360.0, np.zeros_like(hx))
    T = np.exp(-hr / 16000.0)[:, None]
    rad = rad * T + hdir * 0.9 * (1 - T)
    mist = sstep(-250.0, -650.0, hz) * 0.85 + sstep(150.0, -200.0, hz) * sstep(-800.0, -2500.0, hy) * 0.35
    rad = rad * (1 - mist[:, None]) + np.array([0.62, 0.65, 0.70]) * mist[:, None]
    img[hm] = rad
    rgba = np.ones((Hh, W, 4), np.float32); rgba[..., :3] = np.clip(img, 0, 4)
    return rgba

# ============================================================================= paint or load the panorama
PANO_CACHE = os.path.join(OUT, "pano_cache.npy")
if PANO_ONLY or not os.path.exists(PANO_CACHE):
    log("painting panorama ...")
    PANO = paint_panorama(4096 if not args.quick else 2048, 1024 if not args.quick else 512)
    np.save(PANO_CACHE, PANO.astype(np.float16))
else:
    PANO = np.load(PANO_CACHE).astype(np.float32)
if PANO_ONLY:
    img = K.image_from("T_PanoPreview", np.ascontiguousarray(PANO[::-1][::-1]))
    log("saved", os.path.join(OUT, "textures", "T_PanoPreview.png")); sys.exit(0)

def dome_half(name, img_arr, az0, az1, seg=36, rings=13):
    """Half of the sky dome, azimuths az0..az1 (compass deg), its own texture (u spans the half)."""
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
    return o, m

Wp = PANO.shape[1]
front = np.concatenate([PANO[:, 3 * Wp // 4:], PANO[:, :Wp // 4]], axis=1)          # az 270 .. 90 (through north = ahead)
back = PANO[:, Wp // 4: 3 * Wp // 4]                                                  # az 90 .. 270
back = back.reshape(back.shape[0] // 2, 2, back.shape[1] // 2, 2, 4).mean(axis=(1, 3))
DOME_F, M_DOME_F = dome_half("far.sky.front", np.ascontiguousarray(front), -90.0, 90.0)
DOME_B, M_DOME_B = dome_half("far.sky.back", np.ascontiguousarray(back), 90.0, 270.0)
log("dome done")

# ============================================================================= terrain geometry: near disc and the far ring, log-polar textures
NS = 112
def near_radii():
    rs = [0.0]; r = 0.0
    while r < R_NEAR:
        r = min(R_NEAR, r + min(3.0, 0.32 + r * 0.075)); rs.append(r)
    return rs
def far_radii():
    rs = [R_NEAR]; r = R_NEAR
    while r < R_GEO:
        r = min(R_GEO, r * 1.072); rs.append(r)
    return rs
RN, RF = near_radii(), far_radii()
log("rings", len(RN), len(RF))
R0n = 0.6
def vn_of_r(r): return np.log1p(np.asarray(r) / R0n) / math.log1p(R_NEAR / R0n)
def rn_of_v(v): return R0n * np.expm1(np.asarray(v) * math.log1p(R_NEAR / R0n))
def vf_of_r(r): return np.log(np.asarray(r) / R_NEAR) / math.log(R_GEO / R_NEAR)
def rf_of_v(v): return R_NEAR * np.exp(np.asarray(v) * math.log(R_GEO / R_NEAR))

def ground_disc(name, rs, mat, v_of_r, inner=False):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rings = []; start = 0
    if inner:
        c = bm.verts.new((0.0, 0.0, float(gz(0.0, 0.0)))); start = 1
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

def paint_ground(N, near):
    """Ground texture in log-polar layout (u = angle from +X, counter-clockwise; v = radius): albedo with the small
    relief (crevasse walls, boulders, path stones) shaded in, so it holds at the distances it is seen from."""
    u = (np.arange(N) + 0.5) / N; v = (np.arange(N) + 0.5) / N
    U, V = np.meshgrid(u, v)
    r = (rn_of_v if near else rf_of_v)(V); th = U * TWO_PI
    x, y = r * np.cos(th), r * np.sin(th)
    dr = np.gradient(r, axis=0); fp = np.maximum(np.abs(dr), r * TWO_PI / N)
    out = np.empty((N, N, 3), np.float32)
    for i in range(0, N, 256):
        sl = slice(i, i + 256)
        z = gz(x[sl], y[sl]); zx, zy = slope_of(x[sl], y[sl], e=float(max(1.0, np.median(r[sl]) * 0.05)))
        col, ice_m, snow_m = albedo(x[sl], y[sl], z, zx, zy, fp[sl])
        if near:
            col = near_detail(col, x[sl], y[sl], zx, zy, fp[sl])
        # painted micro-relief: the fine terrain's slope against the coarse mesh's, lit from the sun
        zx2, zy2 = slope_of(x[sl], y[sl], e=max(0.3, float(np.median(fp[sl])) * 1.5))
        nf = np.stack([-zx2, -zy2, np.ones_like(zx2)], -1); nf /= np.linalg.norm(nf, axis=-1, keepdims=True)
        nc = np.stack([-zx, -zy, np.ones_like(zx)], -1); nc /= np.linalg.norm(nc, axis=-1, keepdims=True)
        sh = 1.0 + 0.8 * ((nf - nc) @ S_)
        col = col * np.clip(sh, 0.55, 1.35)[..., None]
        out[sl] = col
    rgba = np.ones((N, N, 4), np.float32); rgba[..., :3] = np.clip(out, 0, 1)
    return rgba

def near_detail(col, x, y, zx, zy, fp):
    """The reading place: the mule path's tread of packed grey earth and set stones, the cut bank, turf and
    granite slabs with lichen, scattered stones, needle litter under the spruces."""
    s, m = path_mask(x, y)
    tread = sstep(1.05, 0.75, np.abs(s)) * m
    bank = sstep(-2.6, -1.0, s) * sstep(-0.7, -1.0, s) * m
    n = fbm(x / 0.35, y / 0.35, 4, seed=61); n2 = fbm(x / 1.4, y / 1.4, 4, seed=62)
    earth = np.stack([0.15 + 0.05 * n, 0.13 + 0.04 * n, 0.105 + 0.03 * n], -1) * (0.85 + 0.3 * n2[..., None])
    stones = sstep(0.66, 0.72, fbm(x / 0.09, y / 0.09, 3, seed=63)) * sstep(0.08, 0.02, fp)
    earth = earth * (1 - stones[..., None]) + np.array([0.20, 0.19, 0.175])[None, None, :] * (0.8 + 0.4 * n[..., None]) * stones[..., None]
    soil = np.stack([0.11 + 0.03 * n, 0.085 + 0.02 * n, 0.06 + 0.015 * n], -1)
    col = col * (1 - tread[..., None]) + earth * tread[..., None]
    col = col * (1 - bank[..., None]) + soil * bank[..., None]
    # granite slabs breaking through the turf, lichen on them
    slab = sstep(0.675, 0.69, fbm(x / 4.0, y / 4.0, 5, seed=64)) * (1 - tread) * sstep(18.0, 30.0, np.hypot(x, y))   # bare slabs only further off: near the path the boulders carry the rock
    lich = sstep(0.55, 0.62, fbm(x / 0.15, y / 0.15, 3, seed=65))
    gran = np.stack([0.17 + 0.05 * n, 0.165 + 0.045 * n, 0.155 + 0.04 * n], -1)
    gran = gran * (1 - lich[..., None] * 0.35) + np.array([0.17, 0.18, 0.09]) * lich[..., None] * 0.35
    col = col * (1 - slab[..., None]) + gran * slab[..., None]
    # turf texture: tussocks, dry stems, bilberry darker
    tus = fbm(x / 0.25, y / 0.25, 3, seed=66)
    blades = fbm(x / 0.012 + y / 0.05, y / 0.012 - x / 0.07, 2, seed=68) * sstep(0.02, 0.006, fp)
    grassy = (1 - tread) * (1 - slab)
    col = col * (0.80 + 0.36 * tus[..., None] * (1 - tread[..., None] - slab[..., None] * 0.5))
    col = col * (1 + (blades[..., None] - 0.5) * 0.7 * grassy[..., None] * np.array([1.1, 1.0, 0.7]))
    peb = sstep(0.70, 0.74, fbm(x / 0.035, y / 0.035, 2, seed=69)) * sstep(0.02, 0.006, fp) * (1 - slab) * (0.3 + 0.7 * tread)
    col = col * (1 - peb[..., None] * 0.5) + np.array([0.20, 0.19, 0.18]) * peb[..., None] * 0.5
    litter = sstep(0.5, 0.65, fbm(x / 3.0, y / 3.0, 3, seed=67)) * (1 - tread) * (1 - slab) * 0.35
    col = col * (1 - litter[..., None]) + np.array([0.13, 0.08, 0.045]) * litter[..., None]
    return col

log("painting ground ...")
GN = 2048 if not args.quick else 1024
M_NEARG = K.card_material("M_GroundNear", K.image_from("T_GroundNear", paint_ground(GN, True)), rough=0.9, clip=False)
log("near ground painted")
M_FARG = K.card_material("M_GroundFar", K.image_from("T_GroundFar", paint_ground(GN, False)), rough=0.75, clip=False)
log("far ground painted")
ground_disc("GroundNear", RN, M_NEARG, vn_of_r, inner=True)
ground_disc("GroundFar", RF, M_FARG, vf_of_r)

# ============================================================================= boulders (granite with lichen, node material baked)
def granite_mat():
    m, nt, b = new_mat("M_Granite")
    xyz, X, Y, Z = obj_xyz(nt)
    n = noise_tex(nt, xyz, 1.2, 5.0, 0.6)
    vor = node(nt, "ShaderNodeTexVoronoi", feature='F1'); vor.inputs["Scale"].default_value = 140.0
    nt.links.new(xyz, vor.inputs["Vector"])
    grain = vor.outputs["Color"]
    gsep = node(nt, "ShaderNodeSeparateColor"); nt.links.new(grain, gsep.inputs[0])
    g = gsep.outputs[0]
    base = tone_ramp(nt, g, [(0.10, 0.10, 0.10), (0.30, 0.29, 0.27), (0.36, 0.35, 0.33), (0.40, 0.38, 0.35), (0.20, 0.19, 0.18)])
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 0.35), base, (0.6, 0.58, 0.55, 1))
    # lichen: map lichen (yellow-green), black crust, moss on the tops
    lic = noise_tex(nt, xyz, 7.0, 4.0, 0.65)
    lm = maprange(nt, lic.outputs["Fac"], 0.58, 0.64, 0.0, 1.0)
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', lm, 0.75), col, (0.30, 0.31, 0.15, 1))
    blk = noise_tex(nt, xyz, 4.0, 4.0, 0.6)
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', maprange(nt, blk.outputs["Fac"], 0.60, 0.68, 0.0, 1.0), 0.6), col, (0.05, 0.05, 0.045, 1))
    gm = node(nt, "ShaderNodeNewGeometry"); nsep = node(nt, "ShaderNodeSeparateXYZ"); nt.links.new(gm.outputs["Normal"], nsep.inputs[0])
    moss = math_(nt, 'MULTIPLY', maprange(nt, nsep.outputs["Z"], 0.55, 0.85, 0.0, 1.0), maprange(nt, n.outputs["Fac"], 0.45, 0.6, 0.0, 1.0))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', moss, 0.7), col, (0.07, 0.09, 0.035, 1))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.72, 0.92), b.inputs["Roughness"])
    f = noise_tex(nt, xyz, 18.0, 6.0, 0.65)
    bump_from(nt, b, math_(nt, 'ADD', f.outputs["Fac"], math_(nt, 'MULTIPLY', n.outputs["Fac"], 2.0)), 0.6, 0.02)
    return m
M_GRANITE = granite_mat()

def boulder(name, x, y, r, seed, squash=0.7, sink=0.35):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2 if r < 1.2 else 3, radius=1.0)
    o = bpy.context.active_object; o.name = name
    rs = random.Random(seed); ph = Vector((rs.uniform(0, 50), rs.uniform(0, 50), rs.uniform(0, 50)))
    from mathutils import noise as mn
    for v in o.data.vertices:
        p = v.co.copy()
        d = 1.0 + 0.28 * mn.noise(p * 1.3 + ph) + 0.10 * mn.noise(p * 3.1 + ph)
        p = p * d
        # flat fracture faces: clamp against a few planes
        for k in range(3):
            pl = Vector((math.cos(seed + k * 2.1), math.sin(seed + k * 2.1), 0.35 * (k - 1))).normalized()
            p = p - pl * max(0.0, p.dot(pl) - 0.78)
        v.co = Vector((p.x, p.y * rs.uniform(0.75, 1.0), p.z * squash))
    o.scale = (r, r, r); o.rotation_euler = (0, 0, rs.uniform(0, TWO_PI))
    zg = float(gz(x, y))
    o.location = (x, y, zg - r * squash * sink + r * squash * 0.0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for c in o.users_collection: c.objects.unlink(o)
    K.link(o); o.data.materials.append(M_GRANITE)
    for p in o.data.polygons: p.use_smooth = True
    return o
BOULDERS = [(-3.4, 3.0, 1.3, 1), (-2.6, -4.2, 0.8, 2), (3.0, 6.5, 1.1, 3), (-5.5, 9.5, 2.2, 4), (2.6, -2.0, 0.6, 5),
            (6.0, 1.5, 1.6, 6), (-4.0, -10.0, 1.8, 7), (8.5, 14.0, 2.4, 8), (-9.0, 18.0, 3.0, 9), (11.0, -6.0, 2.0, 10),
            (-1.9, 12.5, 0.7, 11), (4.5, 22.0, 1.4, 12), (-7.0, 1.0, 1.0, 13), (15.0, 9.0, 2.8, 14), (-14.0, -3.0, 2.6, 15),
            (1.6, 3.8, 0.45, 16), (-1.7, -1.6, 0.4, 17)]
for i, (x, y, r, sd) in enumerate(BOULDERS):
    boulder(f"Boulder{i}", x, y, r, sd)

# ============================================================================= spruces
def spray_atlas(N=1024, seed=3):
    """Four Norway-spruce sprays (2 x 2): a drooping twig with alternate side shoots, every shoot a bottle-brush of
    short dark needles, the light catching the upper side; the youngest shoots a fresher green."""
    rs = random.Random(seed); img = np.zeros((N, N, 4), np.float32); S = N // 2
    for vi in range(4):
        ox, oy = (vi % 2) * S, (vi // 2) * S
        def P(x, y): return (ox + x * S, oy + y * S)
        # main twig: from the bottom centre up, curving
        pts = [(0.5 + rs.uniform(-0.04, 0.04), 0.04)]
        for k in range(1, 9):
            pts.append((pts[-1][0] + rs.gauss(0, 0.02), 0.04 + k * 0.11))
        shoots = []
        for k in range(1, 8):
            for side in (-1, 1):
                if rs.random() < 0.05: continue
                bx, by = pts[k]
                L = 0.36 * (1 - k / 11) * rs.uniform(0.8, 1.1)
                a = math.radians(side * rs.uniform(40, 62))
                ex, ey = bx + math.sin(a) * L, by + math.cos(a) * L
                shoots.append(((bx, by), (ex, ey), L))
        twigs = [(pts[i], pts[i + 1], 0.11) for i in range(len(pts) - 1)] + shoots
        for (a, b_, L) in twigs:
            paint_stroke(img, P(*a), P(*b_), 3.0, 1.6, (0.09, 0.05, 0.025))
        for (a, b_, L) in twigs:
            nn = int(L * 260)
            for i in range(nn):
                t = i / max(1, nn - 1)
                cx, cy = a[0] + (b_[0] - a[0]) * t, a[1] + (b_[1] - a[1]) * t
                dx, dy = b_[0] - a[0], b_[1] - a[1]; dl = math.hypot(dx, dy) + 1e-6
                for side in (-1, 1):
                    ang = math.atan2(dy, dx) + side * math.radians(rs.uniform(45, 80))
                    ln = rs.uniform(0.032, 0.048) * (1.0 - 0.3 * t)
                    tone = rs.random()
                    young = t > 0.75 and rs.random() < 0.5
                    if young: col = (0.05 + 0.05 * tone, 0.10 + 0.06 * tone, 0.04 + 0.02 * tone)
                    else: col = (0.018 + 0.02 * tone, 0.040 + 0.03 * tone, 0.030 + 0.02 * tone)
                    if side > 0 and rs.random() < 0.5: col = tuple(c * 1.35 for c in col)
                    paint_stroke(img, P(cx, cy), P(cx + math.cos(ang) * ln, cy + math.sin(ang) * ln), 3.2, 1.4, col)
    return bleed_alpha(img)
def atlas_uv(vi, inset=0.004):
    u0, v0 = (vi % 2) * 0.5, (vi // 2) * 0.5
    return (u0 + inset, v0 + inset, u0 + 0.5 - inset, v0 + 0.5 - inset)

log("painting foliage ...")
M_SPRUCE = K.card_material("M_SpruceNeedles", K.image_from("T_SpruceNeedles", spray_atlas()), rough=0.8)

def bark_mat():
    m, nt, b = new_mat("M_SpruceBark")
    xyz, X, Y, Z = obj_xyz(nt)
    mp = node(nt, "ShaderNodeMapping"); nt.links.new(xyz, mp.inputs["Vector"]); mp.inputs["Scale"].default_value = (14.0, 14.0, 4.0)
    vor = node(nt, "ShaderNodeTexVoronoi", feature='DISTANCE_TO_EDGE'); vor.inputs["Scale"].default_value = 1.0
    nt.links.new(mp.outputs["Vector"], vor.inputs["Vector"])
    n = noise_tex(nt, xyz, 3.0, 4.0, 0.6)
    col = tone_ramp(nt, n.outputs["Fac"], [(0.07, 0.05, 0.04), (0.12, 0.085, 0.065), (0.09, 0.07, 0.055)])
    col = mix_rgb(nt, 'MIX', maprange(nt, vor.outputs["Distance"], 0.0, 0.06, 0.7, 0.0), col, (0.03, 0.022, 0.018, 1))
    lic = maprange(nt, noise_tex(nt, xyz, 6.0, 3.0, 0.6).outputs["Fac"], 0.6, 0.66, 0.0, 0.6)
    col = mix_rgb(nt, 'MIX', lic, col, (0.28, 0.29, 0.22, 1))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.88
    bump_from(nt, b, vor.outputs["Distance"], 0.6, 0.01)
    return m
M_BARK = bark_mat()

class Bark:
    def __init__(self): self.bm = bmesh.new()
    def tube(self, pts, radii, sides):
        P = [Vector(p) for p in pts]; n = len(P)
        tang = [((P[min(n - 1, i + 1)] - P[max(0, i - 1)]).normalized()) for i in range(n)]
        ref = Vector((1, 0, 0)) if abs(tang[0].x) < 0.9 else Vector((0, 1, 0))
        nrm = tang[0].cross(ref).normalized(); rings = []
        for i in range(n):
            if i > 0: nrm = (nrm - tang[i] * nrm.dot(tang[i])).normalized()
            bn = tang[i].cross(nrm)
            rings.append([self.bm.verts.new(P[i] + (nrm * math.cos(TWO_PI * k / sides) + bn * math.sin(TWO_PI * k / sides)) * radii[i]) for k in range(sides)])
        for a, b_ in zip(rings, rings[1:]):
            for k in range(sides):
                f = self.bm.faces.new((a[k], a[(k + 1) % sides], b_[(k + 1) % sides], b_[k])); f.smooth = True
        self.bm.faces.new(rings[-1])
    def finish(self, name, mat):
        me = bpy.data.meshes.new(name); self.bm.normal_update(); self.bm.to_mesh(me); self.bm.free()
        o = bpy.data.objects.new(name, me); me.materials.append(mat); K.link(o); return o
BARK = Bark()
CROWNS = CardMesh("veg.crown.spruce")

def spruce(x, y, H, R, lod, seed):
    """A subalpine Norway spruce: a narrow cone of drooping branch tiers down to near the ground, the tips turned
    up; each branch carries spray cards, half lying along it, half hanging from it like a skirt."""
    rs = random.Random(seed)
    z0 = float(gz(x, y)) - 0.3
    lean = Vector((rs.gauss(0, 0.02), rs.gauss(0, 0.02), 0))
    BARK.tube([(x, y, z0 - 0.2), tuple(Vector((x, y, z0 + H * 0.5)) + lean * H * 0.5), tuple(Vector((x, y, z0 + H)) + lean * H)],
              [0.011 * H + 0.08, 0.006 * H + 0.04, 0.02], {2: 7, 1: 5, 0: 4}[lod])
    gap = {2: 0.36, 1: 0.55, 0: 0.85}[lod]
    h = H * rs.uniform(0.06, 0.14); k = 0
    while h < H * 0.97:
        t = h / H
        nb = {2: 6, 1: 5, 0: 4}[lod]
        for j in range(nb):
            a = k * 2.39996 + j * TWO_PI / nb + rs.gauss(0, 0.25)
            d = Vector((math.cos(a), math.sin(a), 0))
            L = R * (1 - t) ** 0.95 * rs.uniform(0.75, 1.1) + 0.25
            base = Vector((x, y, z0 + h)) + lean * h
            droop = 0.30 + 0.15 * (1 - t)
            mid = base + d * L * 0.55 + Vector((0, 0, -droop * L * 0.45))
            tip = base + d * L + Vector((0, 0, -droop * L * 0.55 + 0.12 * L))
            if lod == 2 and rs.random() < 0.2 and t < 0.6:
                BARK.tube([tuple(base), tuple(mid), tuple(tip)], [0.035 * (1 - t) + 0.01, 0.02, 0.008], 4)
            side = d.cross(Vector((0, 0, 1))).normalized()
            ncard = {2: 2, 1: 2, 0: 1}[lod]
            for c in range(ncard):
                f0 = 0.35 + 0.6 * c / max(1, ncard - 1) if ncard > 1 else 0.6
                cpos = base + (tip - base) * f0 + Vector((0, 0, -0.05 * L))
                w = L * (0.95 if ncard > 1 else 1.3) * rs.uniform(0.85, 1.15) + 0.2
                hang = (c % 2 == 1) or lod == 0
                along = (d * (0.45 if hang else 0.95) + Vector((0, 0, -0.85 if hang else -0.3))).normalized()
                c0 = cpos - side * w * 0.5 - along * w * 0.35
                corners = [c0, c0 + side * w, c0 + side * w + along * w * 0.9, c0 + along * w * 0.9]
                vi = rs.randrange(4); u0, v0, u1, v1 = atlas_uv(vi)
                if rs.random() < 0.5: u0, u1 = u1, u0
                uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
                cc = Vector((x, y, z0 + H * 0.45))
                norms = []; wts = []
                for q in corners:
                    nn = q - cc; nn.z = nn.z * 0.4 + 0.6 * abs(nn.length) * 0.3
                    nn = (nn.normalized() * 0.7 + Vector((0, 0, 0.5))).normalized(); norms.append(nn)
                    hd = Vector((q.x - x, q.y - y, 0)).length
                    wts.append(max(0.08, min(1.0, 0.15 + 0.85 * hd / max(R, 0.5))) * (0.5 + 0.5 * t))
                CROWNS.quad(corners, uvs, norms, wts)
        h += gap * rs.uniform(0.8, 1.2); k += 1
    # the leader
    tipz = Vector((x, y, z0 + H)) + lean * H
    for j in range(2):
        a = j * math.pi / 2 + rs.uniform(0, 0.5); side = Vector((math.cos(a), math.sin(a), 0))
        w = 0.9
        corners = [tipz - side * w / 2 - Vector((0, 0, 1.0)), tipz + side * w / 2 - Vector((0, 0, 1.0)), tipz + side * w / 2 + Vector((0, 0, 0.3)), tipz - side * w / 2 + Vector((0, 0, 0.3))]
        u0, v0, u1, v1 = atlas_uv(rs.randrange(4))
        CROWNS.quad(corners, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], [(side.y, -side.x, 0.4)] * 4, [0.6, 0.6, 1.0, 1.0])

# near spruces round the reading place (left: up the slope; right: below the path, their crowns at eye level)
NEAR_TREES = [(-6.5, 5.0, 17.0, 2.6), (-8.5, -3.5, 21.0, 3.0), (-12.0, 12.0, 19.0, 2.8), (6.5, 11.0, 14.0, 2.4),
              (8.5, -3.5, 16.5, 2.6), (-4.0, 22.0, 15.0, 2.3), (-16.0, -14.0, 20.0, 3.0), (-2.5, -17.0, 13.0, 2.1)]
for i, (x, y, H, R) in enumerate(NEAR_TREES):
    spruce(x, y, H, R, 2 if math.hypot(x, y) < 15 else 1, 300 + i)
# scattered spruces down the slope and along it (mid distance), none on the ice or the moraine
rs = random.Random(7); n_mid = 0
for k in range(900):
    a = rs.uniform(-math.pi, math.pi); r = 26.0 + 300.0 * rs.random() ** 1.6
    x, y = r * math.sin(a), r * math.cos(a)
    xc, w, zi = glacier_frame(np.array(y)); q = abs(x - float(xc)) - float(w)
    if q < 55: continue
    z = float(gz(x, y))
    if z > 140 or z < -80: continue
    zx, zy = slope_of(np.array(x), np.array(y), e=3.0)
    if math.hypot(float(zx), float(zy)) > 1.0: continue
    if float(fbm(np.array(x / 50.0), np.array(y / 50.0), 4, seed=26)) < 0.42: continue
    if any(math.hypot(x - tx, y - ty) < 5 for tx, ty, _, _ in NEAR_TREES): continue
    spruce(x, y, rs.uniform(11, 20), rs.uniform(2.0, 3.0), 1 if r < 70 else 0, 1000 + k); n_mid += 1
    if n_mid >= 30: break
log("mid spruces", n_mid)
BARK.finish("SpruceBark", M_BARK)
CROWNS.finish(M_SPRUCE)

# ============================================================================= alpenrose, bilberry and grass round the path
def shrub_atlas(N=512, seed=5):
    """Four clumps (2 x 2): alpenrose (dark glossy leaves in rosettes, rusty undersides), bilberry (small bright leaves
    on green stems), juniper (grey-green), a dried-out alpenrose going brown."""
    rs = random.Random(seed); img = np.zeros((N, N, 4), np.float32); S = N // 2
    for vi in range(4):
        ox, oy = (vi % 2) * S, (vi // 2) * S
        def P(x, y): return (ox + x * S, oy + y * S)
        pal = [((0.030, 0.050, 0.022), (0.065, 0.085, 0.035)), ((0.05, 0.09, 0.03), (0.10, 0.14, 0.04)),
               ((0.05, 0.07, 0.055), (0.09, 0.11, 0.08)), ((0.08, 0.06, 0.03), (0.13, 0.09, 0.04))][vi]
        for k in range(26):
            bx = 0.5 + rs.gauss(0, 0.06); a = rs.gauss(0, 0.5); L = rs.uniform(0.45, 0.85)
            ex, ey = bx + math.sin(a) * L * 0.6, 0.03 + math.cos(a) * L
            paint_stroke(img, P(bx, 0.02), P(ex, ey), 2.5, 1.2, (0.07, 0.045, 0.03))
            for j in range(10):
                t = rs.uniform(0.3, 1.0); cx, cy = bx + (ex - bx) * t, 0.02 + (ey - 0.02) * t
                for l in range(3 if vi != 2 else 6):
                    la = rs.uniform(0, TWO_PI); ll = rs.uniform(0.03, 0.06) * (0.5 if vi == 2 else 1.0)
                    tone = rs.random(); c = tuple(p0 + (p1 - p0) * tone for p0, p1 in zip(*pal))
                    paint_stroke(img, P(cx, cy), P(cx + math.cos(la) * ll, cy + math.sin(la) * ll), 5.0 if vi != 2 else 2.0, 2.0 if vi != 2 else 1.0, c)
    return bleed_alpha(img)
def grass_atlas(N=512, seed=7):
    rs = random.Random(seed); img = np.zeros((N, N, 4), np.float32); S = N // 2
    for vi in range(4):
        ox, oy = (vi % 2) * S, (vi // 2) * S
        def P(x, y): return (ox + x * S, oy + y * S)
        for k in range(70):
            bx = 0.5 + rs.gauss(0, 0.12); a = rs.gauss(0, 0.32); L = rs.uniform(0.4, 0.95)
            tone = rs.random(); dry = rs.random() < 0.45
            c = (0.17 + 0.1 * tone, 0.15 + 0.07 * tone, 0.07 + 0.03 * tone) if dry else (0.07 + 0.05 * tone, 0.10 + 0.05 * tone, 0.035)
            mx, my = bx + math.sin(a) * L * 0.5, 0.02 + math.cos(a) * L * 0.5
            ex, ey = bx + math.sin(a * 1.5) * L, 0.02 + math.cos(a * 1.5) * L * 0.95
            paint_stroke(img, P(bx, 0.02), P(mx, my), 2.6, 2.0, c); paint_stroke(img, P(mx, my), P(ex, ey), 2.0, 0.7, c)
    return bleed_alpha(img)
M_SHRUB = K.card_material("M_Alpenrose", K.image_from("T_Alpenrose", shrub_atlas()), rough=0.75)
M_GRASS = K.card_material("M_AlpineGrass", K.image_from("T_AlpineGrass", grass_atlas()), rough=0.85)

def ground_normal(x, y, e=0.3):
    zx, zy = slope_of(np.array(x), np.array(y), e=e); return Vector((-float(zx), -float(zy), 1)).normalized()
def clump(cm, x, y, w, h, ncards, rs, pool, sink=0.04, tilt=0.35):
    z = float(gz(x, y)) - sink; gn = ground_normal(x, y); a0 = rs.uniform(0, math.pi)
    for k in range(ncards):
        a = a0 + math.pi * k / ncards + rs.gauss(0, 0.15)
        right = Vector((math.cos(a), math.sin(a), 0)); outward = Vector((-right.y, right.x, 0)) * rs.choice((-1, 1))
        up = (Vector((0, 0, 1)) + outward * rs.uniform(0.0, tilt)).normalized()
        ww = w * rs.uniform(0.8, 1.15); hh = h * rs.uniform(0.8, 1.2); b = Vector((x, y, z))
        corners = [b - right * ww / 2, b + right * ww / 2, b + right * ww / 2 + up * hh, b - right * ww / 2 + up * hh]
        u0, v0, u1, v1 = atlas_uv(rs.choice(pool))
        if rs.random() < 0.5: u0, u1 = u1, u0
        nt_ = (gn * 0.6 + outward * 0.25 + Vector((0, 0, 0.4))).normalized()
        cm.quad(corners, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], [gn, gn, nt_, nt_], [0.0, 0.0, 1.0, 1.0])
SHRUBS = CardMesh("veg.shrub.alpenrose"); GRASS = CardMesh("veg.grass.alpine")
rs = random.Random(11); cnt = [0, 0]
for i in range(-60, 61):
    for j in range(-60, 61):
        x, y = i * 0.5 + rs.uniform(-0.25, 0.25), j * 0.5 + rs.uniform(-0.25, 0.25)
        r = math.hypot(x, y)
        if r < 0.8 or r > 30: continue
        if r > 12 and rs.random() < (r - 12) / 22: continue
        near_r = r < 9
        s, m = path_mask(np.array(x), np.array(y))
        if abs(float(s)) < 1.15: continue
        if any(math.hypot(x - bx, y - by) < br * 0.9 for bx, by, br, _ in BOULDERS): continue
        if r > 18 and float(fbm(np.array(x / 4.0), np.array(y / 4.0), 4, seed=64)) > 0.68: continue         # granite slab
        nsh = float(fbm(np.array(x / 3.0), np.array(y / 3.0), 3, seed=71))
        if rs.random() < (0.15 if near_r else 0.55): continue
        if nsh > 0.56 and rs.random() < 0.7:
            ww = rs.uniform(0.5, 0.9)
            clump(SHRUBS, x, y, ww, ww * rs.uniform(0.5, 0.75), 3, rs, [0, 1, 2, 3] if nsh > 0.62 else [0, 3], sink=0.06); cnt[0] += 1
        elif rs.random() < (0.5 if near_r else 0.28):
            g = rs.uniform(0.25, 0.45)
            clump(GRASS, x, y, g * 0.9, g, 2, rs, [0, 1, 2, 3], sink=0.02, tilt=0.5); cnt[1] += 1
log("shrubs, grass", cnt)
SHRUBS.finish(M_SHRUB); GRASS.finish(M_GRASS)

# ============================================================================= mist: soft banks low in the valley behind and over the far ice
def mist_img(N=512, seed=61):
    u = (np.arange(N) + 0.5) / N; U, V = np.meshgrid(u, u)
    r = np.hypot((U - 0.5) * 1.0, (V - 0.5) * 1.0) * 2
    a = sstep(1.0, 0.25, r) * (0.30 + 0.70 * fbm(U * 4, V * 4, 5, seed=seed)) * 0.45
    rgba = np.ones((N, N, 4), np.float32); rgba[..., :3] = np.array([0.66, 0.69, 0.73]); rgba[..., 3] = a
    return rgba
M_MIST = K.card_material("M_Mist", K.image_from("T_Mist", mist_img()), rough=1.0, clip=False, blend=True)
MIST = CardMesh("Mist")
def mist_sheet(cx, cy, rx, ry, z, rot, tilt=0.0):
    R_ = Matrix.Rotation(rot, 3, 'Z') @ Matrix.Rotation(tilt, 3, 'X')
    pts = [Vector((cx, cy, z)) + R_ @ Vector(p) for p in ((-rx, -ry, 0), (rx, -ry, 0), (rx, ry, 0), (-rx, ry, 0))]
    MIST.quad(pts, [(0, 0), (1, 0), (1, 1), (0, 1)], [(0, 0, 1)] * 4, [0] * 4)
mist_sheet(250, -650, 380, 260, -150, 0.3)
mist_sheet(420, -330, 220, 130, -112, -0.2)
mist_sheet(260, 640, 260, 110, -25, 0.1)

MIST.finish(M_MIST, weighted=False)

# ============================================================================= light
F.sun("light.sun", 3.0, (1.0, 0.97, 0.92), tuple(SUN_DIR), angle_deg=1.5)
F.sun("light.sky", 0.6, (0.62, 0.74, 1.0), (-0.2, 0.15, 1.0), angle_deg=80, shadow=False)
world = bpy.data.worlds.new("Day"); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]
bg.inputs["Color"].default_value = (0.42, 0.50, 0.62, 1); bg.inputs["Strength"].default_value = 0.55

# ============================================================================= anchors and living-scene markers
look = az_dir(0.0)
anchor("reader.entrance", (0.0, 0.0, float(gz(0.0, 0.0))))
anchor("reader.look", (0.0, 2.0, EYE))
anchor("scene.centre", (0.0, 0.0, float(gz(0.0, 0.0))))
xc0, w0, zi0 = glacier_frame(np.array(60.0))
anchor("glacier.edge", (float(xc0 - w0), 60.0, float(gz(float(xc0 - w0), 60.0))))
anchor("glacier.far", (float(glacier_frame(np.array(900.0))[0]), 900.0, float(gz(float(glacier_frame(np.array(900.0))[0]), 900.0))))
F.sound("sound.wind-trees.0", (-7.0, 4.0, float(gz(-7.0, 4.0)) + 8.0))
F.sound("sound.wind.0", (-25.0, 10.0, float(gz(-25.0, 10.0)) + 5.0))
F.sound("sound.river.0", (float(xc0 - w0), 40.0, float(gz(float(xc0 - w0), 40.0)) + 1.0))

K.apply_all_transforms()

# ============================================================================= cameras (reader eye 1.55 m)
E = Vector((0, 0, float(gz(0.0, 0.0)) + EYE))
def ahead(yaw_deg, pitch_deg=0.0, d=10.0):
    a = math.radians(-yaw_deg); p = math.radians(pitch_deg)
    return tuple(E + Vector((math.sin(a) * math.cos(p), math.cos(a) * math.cos(p), math.sin(p))) * d)
cams = [
    camera("Cam_Reader", tuple(E), ahead(0, -6), clip_end=1500),
    camera("Cam_Right", tuple(E), ahead(-60, -10), clip_end=1500),
    camera("Cam_Left", tuple(E), ahead(65, 6), clip_end=1500),
    camera("Cam_Behind", tuple(E), ahead(180, -8), clip_end=1500),
    camera("Cam_Down", tuple(E), ahead(-30, -50), lens=16, clip_end=1500),
    camera("Cam_Up", tuple(E), ahead(-20, 30), clip_end=1500),
]
EXPOSURE = {}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "mer_de_glace_source.blend"))
K.budget_report()

if args.render:
    F.render_stills(scene, cams, EXPOSURE, default_exp=-0.6, label="mer-de-glace")

if args.bake or args.export:
    T_ = args.tex
    size_for = {"M_Granite": (T_ // 2, T_ // 4, T_ // 2), "M_SpruceBark": (T_ // 4, T_ // 8, T_ // 4)}
    F.bake_and_export(scene, "mer_de_glace.gltf", size_for,
                      keep_names={"M_far_sky_front": "SkyDome.front", "M_far_sky_back": "SkyDome.back", "M_GroundNear": "MESH_GroundNear",
                                  "M_GroundFar": "MESH_GroundFar", "M_SpruceNeedles": "veg.crown.spruce", "M_Alpenrose": "veg.shrub.alpenrose",
                                  "M_AlpineGrass": "veg.grass.alpine", "M_Mist": "MESH_Mist"},
                      cams=cams, blend_name="mer_de_glace_baked.blend")
print("DONE")
