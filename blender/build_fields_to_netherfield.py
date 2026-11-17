"""
Fable: the fields to Netherfield after rain (Pride and Prejudice, chapter 7, Elizabeth's walk to Netherfield).

"Jane had not been gone long before it rained hard." ... "The rain continued the whole evening without intermission"
... "crossing field after field at a quick pace, jumping over stiles and springing over puddles, with impatient
activity, and finding herself at last within view of the house"

The reader stands on the grass verge of a field footpath in Hertfordshire pasture, early on an overcast November
morning after a night of heavy rain. The field is old ridge-and-furrow grassland: the furrows hold the water, and
where the trodden path crosses them it is churned mud with puddles. Ahead-left (11 m) the path reaches a weathered
oak step stile set in a laid hawthorn hedge, under a big hedgerow oak still holding its brown leaves; beyond the hedge
the last field rises gently to Netherfield House, a plain stuccoed Georgian house among park trees (ahead-right, about
95 m away). On the right a second hedge runs back past a field maple to a five-bar gate with a poached, puddled
gateway; ahead-right, a bare ash on hedge A carries an old rookery. Behind, the path runs back to a stile in the far
hedge, and far off on the horizon the tower of Meryton church stands above the trees. No people or animals are
modelled (the rooks are a sound source in the ash).

Light: one coherent overcast morning. A high, even stratocumulus deck, brightest low in the east-south-east where the
sun is behind it (the reader's right); soft, nearly shadowless light from that side; everything wet: dark mud, glossy
puddles reflecting the pale sky, darkened grass. Colour: muted greens, umber mud, grey bark, the pale house; no orange.

Builds everything procedurally (no downloaded models, textures or HDRIs). Foliage cards (grass, rushes, hedge sprays,
oak leaves, bare twigs) read numpy-painted RGBA atlases with alpha clipping; everything else is node materials baked to
textures.

Quest 2 foliage budget (2026-11-17): alpha-tested cards are what the Quest's tile GPU pays for, layer on layer, so they
are kept where they matter: grass cards only within ~9 m (opaque blade tufts, MESH_GrassBlades, carry the sward to
~16 m, and the baked ground beyond); hedge spray cards only within ~20 m of the reader, over an opaque lumpy leafy hedge
mass (MESH_HedgeMass), with a sparse fringe further off; tree crowns are cards only (an opaque mass reads as a ball against
the sky): fewer, larger cards on near trees; on far trees ~28 big cards and none at the branch tips. Measure with
blender/measure_alpha_cards.py (reader view 2.31 -> 0.92 screens of alpha cards; 11453 -> 2627 card faces). By flag the script renders Cycles stills, bakes, merges static meshes by material and exports .gltf + .bin +
textures/ for Unity (helpers in pride_kit.py).

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet on the verge (ground, z = 0), facing +Y
  anchor.reader.look      eye height (1.55 m), 1 m ahead
  anchor.scene.centre     the stile
  anchor.path.stile, anchor.path.gate, anchor.netherfield.house, anchor.meryton.church (direction only)
  light.sun (SUN, the veiled low sun, very soft), light.sky (SUN, cool shadowless fill)
  SkyDome (unlit backdrop, baked base texture), far.land (ground beyond 34 m: backdrop)
  water.puddle.path       the puddles and the ditch water (still water)
  veg.grass.field         grass tufts, rushes, docks, dead umbels (sway weight in COLOR_0.R)
  veg.shrub.hedges        hedge leaf sprays
  veg.crown.oak, veg.crown.bare, veg.crown.maple   tree crowns (cards at the branch ends)
  sound.wind-trees.oak, sound.wind-trees.ash, sound.birds.rooks, sound.birds.hedge, sound.wind.field

Register the scene as Outdoor (sun + sky directional lights, unlit sky dome). The sun must stay weak (overcast):
the FableBuild default 1.5 would throw hard shadows; ~0.45 sun + ~0.45 sky is the intended balance.

Axes: metres, Blender +Z up. Reader at the origin facing +Y (north). East (+X) is the bright side of the sky.

Run headless:
  blender -b -P blender/build_fields_to_netherfield.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_fields_to_netherfield.py -- --render --samples 64 --res 1400 --captures captures/blender/fields-to-netherfield
  blender -b -P blender/build_fields_to_netherfield.py -- --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       texcoord_obj, wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB,
                       anchor, fx, sound, light_obj, camera, smoothstep, lerp, n2, fbm2, link)

ARGS = K.setup("fields-to-netherfield", "out/fields-to-netherfield", 1813, "FieldsToNetherfield", default_samples=64)
OUT = K.OUT
scene = K.scene
rng = random.Random(1813)

# ----------------------------------------------------------------------------- layout (metres)
EYE = 1.55
NEAR = 34.0                      # near ground (4K, warped UVs) inside |x|,|y| < NEAR; far.land beyond
LAND_R = 121.0                   # the land ends under the sky dome
SKY_R = 124.0
SUN_AZ, SUN_EL = math.radians(108.0), math.radians(9.0)     # azimuth from +Y (north) towards +X (east)
SUN_DIR = Vector((math.sin(SUN_AZ) * math.cos(SUN_EL), math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL))).normalized()
CHURCH_DIR = Vector((-0.12, -1.0, 0)).normalized()          # Meryton, behind the reader

PATH = [(1.6, -70), (1.3, -47), (1.0, -30), (0.3, -14), (-0.45, -5), (-0.75, -1.2), (-0.9, 1.0), (-1.6, 3.4), (-2.9, 5.4),
        (-3.95, 6.75), (-4.25, 8.4), (-3.9, 12.5), (-1.5, 24), (6, 42), (18, 58), (30, 72), (37, 80)]
HEDGE_A = [(-75, 3.0), (-42, 5.6), (-25, 6.5), (-12, 6.85), (-4.0, 6.95), (2.0, 7.4), (9.6, 8.5), (18, 10.2), (30, 12.6), (48, 15.5), (80, 19)]
HEDGE_B = [(9.6, 8.5), (9.9, 0.0), (9.4, -12), (8.8, -26), (9.3, -45), (10.2, -80)]
HEDGE_C = [(-41.5, 5.5), (-40.5, -20), (-42.0, -46.5)]
HEDGE_D = [(-42.0, -46.5), (-20, -47.2), (0, -47.0), (9.3, -45), (40, -44), (80, -46)]
HEDGE_E = [(48, 15.5), (55, 45), (66, 70)]                    # the last field's east side, running up towards the park
HEDGE_F = [(-42, 5.6), (-45, 40), (-40, 70), (-30, 98)]
STILE = Vector((-4.0, 6.95))
GATE = Vector((9.55, -10.5))                                   # five-bar gate in hedge B
HOUSE = Vector((40.0, 87.0))                                   # Netherfield House, front centre
HOUSE_YAW = math.atan2(-HOUSE.x, HOUSE.y) + math.radians(18)    # the front faces back across the fields, turned a little east
GAPS_A = [(STILE.x, STILE.y, 0.75)]
GAPS_B = [(GATE.x, GATE.y, 1.6)]
GAPS_D = [(1.25, -47.0, 0.7)]

# ----------------------------------------------------------------------------- 2D helpers
def seg_dist(px, py, poly):
    """distance from (px, py) to a polyline, the parameter along it (metres) and the side (+1 left, -1 right)."""
    best = (1e9, 0.0, 1.0); acc = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy; L = math.sqrt(L2)
        t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L2))
        qx, qy = x0 + t * dx, y0 + t * dy; d = math.hypot(px - qx, py - qy)
        if d < best[0]:
            side = 1.0 if (dx * (py - y0) - dy * (px - x0)) > 0 else -1.0
            best = (d, acc + t * L, side)
        acc += L
    return best

def seg_dist_np(X, Y, poly):
    D = np.full(X.shape, 1e9, np.float32)
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0, 1)
        D = np.minimum(D, np.hypot(X - (x0 + t * dx), Y - (y0 + t * dy)))
    return D

def poly_sample(poly, step):
    pts = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / step))
        for i in range(n):
            t = i / n; pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, (x1 - x0) / L, (y1 - y0) / L))
    x1, y1 = poly[-1]; pts.append((x1, y1, pts[-1][2], pts[-1][3]))
    return pts

def hedge_y_at(x, poly=HEDGE_A):
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        if x0 <= x <= x1: return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return poly[-1][1] if x > poly[-1][0] else poly[0][1]

def in_my_field(x, y):
    return y < hedge_y_at(x) - 0.4 and x < 9.3 and x > -41 and y > -46.5

# ----------------------------------------------------------------------------- the puddles (water.puddle.*): where the path crosses the furrows, at the stile and in the gateway
def furrow_phase(x, y):
    return (x - 1.4 * math.sin(y / 23.0) - 0.15 * y * 0.0) / 7.2       # ridges run north-south with a gentle reversed-S

PUDDLES = []   # (cx, cy, rx, ry, angle, depth)
def _add_puddle(c, rx, ry, ang, depth): PUDDLES.append((c[0], c[1], rx, ry, ang, depth))
# along the path in my field: the furrow bottoms (phase = 0.5) and two ad-hoc wet spots
_ps = poly_sample(PATH, 0.25)
_last = None
for (x, y, dx, dy) in _ps:
    if not (-46 < y < 6.4): continue
    ph = furrow_phase(x, y) % 1.0
    if abs(ph - 0.5) < 0.03 and (_last is None or math.hypot(x - _last[0], y - _last[1]) > 3.0):
        _last = (x, y)
        _add_puddle((x + rng.uniform(-0.15, 0.15), y), rng.uniform(0.55, 1.1), rng.uniform(0.32, 0.55), math.atan2(dy, dx) + rng.uniform(-0.3, 0.3), rng.uniform(0.07, 0.1))
_add_puddle((-1.25, 2.45), 0.62, 0.36, math.radians(62), 0.075)       # the one at the reader's feet, ahead-left
_add_puddle((-3.35, 6.05), 0.95, 0.6, math.radians(50), 0.09)         # the trampled stile approach
_add_puddle((-4.55, 8.0), 0.5, 0.35, math.radians(80), 0.06)          # just over the stile
_add_puddle((-2.15, 4.45), 0.38, 0.26, math.radians(55), 0.05)
_add_puddle((GATE.x - 1.3, GATE.y + 0.2), 1.25, 0.8, math.radians(95), 0.1)   # the poached gateway
_add_puddle((GATE.x - 2.4, GATE.y - 0.9), 0.6, 0.4, math.radians(20), 0.07)
_add_puddle((GATE.x + 1.4, GATE.y - 0.3), 0.9, 0.55, math.radians(85), 0.08)
_add_puddle((-0.1, -8.6), 0.7, 0.42, math.radians(98), 0.08)

def puddle_s(x, y, p):
    """normalised elliptical distance with a ragged rim (0 centre, 1 rim)."""
    cx, cy, rx, ry, ang, depth = p
    dx, dy = x - cx, y - cy; ca, sa = math.cos(ang), math.sin(ang)
    u = (dx * ca + dy * sa) / rx; v = (-dx * sa + dy * ca) / ry
    a = math.atan2(v, u)
    rag = 1.0 + 0.22 * noise.noise(Vector((math.cos(a) * 1.3 + cx, math.sin(a) * 1.3 + cy, 0.5))) + 0.08 * noise.noise(Vector((math.cos(a) * 4 + cx, math.sin(a) * 4, 2.1)))
    return math.sqrt(u * u + v * v) / rag

# ----------------------------------------------------------------------------- the land
def path_info(x, y):
    d, s, side = seg_dist(x, y, PATH)
    w = 0.42 + 0.22 * (0.5 + 0.5 * n2(s, 0.0, 7.0, 3.1)) + 0.5 * smoothstep(3.0, 0.0, math.hypot(x - STILE.x, y - STILE.y))
    return d, s, w

def H(x, y):
    r = math.hypot(x, y)
    z = 0.55 * fbm2(x, y, 70.0, 3, 0.3) + 0.12 * fbm2(x, y, 14.0, 2, 1.7)
    z += 3.3 * smoothstep(9.0, 95.0, y + 0.12 * x)                        # the last field rises to the house
    z += -1.6 * smoothstep(60.0, 118.0, -y) * 0.6                          # the land falls away gently behind, towards Meryton
    # ridge and furrow in the reader's field
    if in_my_field(x, y) or (x < 9.3 and y < hedge_y_at(x) - 0.1 and y > -46.5 and x > -41):
        fade = smoothstep(0.4, 2.4, hedge_y_at(x) - y) * smoothstep(0.3, 2.0, 9.3 - x) * smoothstep(0.3, 2.0, x + 41) * smoothstep(0.3, 2.0, y + 46.5)
        ph = furrow_phase(x, y)
        z += fade * (0.17 * math.cos(2 * math.pi * ph) + 0.02 * math.cos(4 * math.pi * ph))
    # hedge banks and the ditch on the field side of hedge A
    for poly, bank, ditch in ((HEDGE_A, 0.28, 0.32), (HEDGE_B, 0.22, 0.0), (HEDGE_C, 0.2, 0.0), (HEDGE_D, 0.22, 0.0), (HEDGE_E, 0.2, 0.0), (HEDGE_F, 0.2, 0.0)):
        d, s, side = seg_dist(x, y, poly)
        if d < 3.5:
            z += bank * (1.0 - smoothstep(0.3, 1.3, d))
            if ditch and side < 0:     # the field side (south of hedge A)
                z -= ditch * smoothstep(0.9, 1.35, d) * (1.0 - smoothstep(1.6, 2.4, d)) * smoothstep(1.4, 3.0, math.hypot(x - STILE.x, y - STILE.y))
    # the trodden path: a shallow worn trough with ruts, deeper where boots have churned it
    d, s, w = path_info(x, y)
    if d < 2.0:
        z -= 0.045 * (1.0 - smoothstep(w * 0.4, w * 1.15, d))
        z += 0.012 * n2(x, y, 0.18, 5.0) * (1.0 - smoothstep(w * 0.5, w * 1.2, d))
    # the house platform and the gravel sweep
    hd = math.hypot(x - HOUSE.x, y - HOUSE.y)
    if hd < 40: z = lerp(z, 3.3 + 0.55 * fbm2(HOUSE.x, HOUSE.y, 70.0, 3, 0.3), 1.0 - smoothstep(18.0, 34.0, hd))
    # puddles
    for p in PUDDLES:
        if abs(x - p[0]) < 1.6 and abs(y - p[1]) < 1.6:
            sv = puddle_s(x, y, p)
            z -= p[5] * (1.0 - smoothstep(0.35, 1.15, sv))
    # poached ground round the gate and the stile (hoof and boot marks)
    gd = math.hypot(x - GATE.x, y - GATE.y)
    if gd < 4.5: z += 0.03 * (1.0 - gd / 4.5) * noise.noise(Vector((x * 3.1, y * 3.1, 7.7)))
    # the land drops just a little at its edge so the dome's painted land meets it below the horizon
    z -= 2.0 * smoothstep(100.0, LAND_R, r)
    return z

Z0 = H(0.0, 0.0)
def Hz(x, y): return H(x, y) - Z0

# ----------------------------------------------------------------------------- the masks the ground shader reads (generated here, never downloaded)
MASK_EXT = 64.0
def make_masks(res=2048):
    lin = (np.arange(res, dtype=np.float32) + 0.5) / res * 2 * MASK_EXT - MASK_EXT
    X, Y = np.meshgrid(lin, lin)          # row = y, col = x
    dp = seg_dist_np(X, Y, PATH)
    stile_d = np.hypot(X - STILE.x, Y - STILE.y); gate_d = np.hypot(X - GATE.x, Y - GATE.y)
    w = 0.42 + 0.6 * np.clip(1 - stile_d / 3.0, 0, 1) - 0.12 * np.clip((np.hypot(X, Y) - 15) / 30, 0, 1)
    mud = np.clip(1 - (dp - w * 0.4) / (w * 0.75), 0, 1)
    mud = np.maximum(mud, np.clip(1 - (gate_d - 1.0) / 3.2, 0, 1) * (X < 11.5))
    mud = np.maximum(mud, np.clip(1 - (stile_d - 0.8) / 2.4, 0, 1))
    # wet: puddle rims and the ditch
    wet = np.zeros_like(X)
    for (cx, cy, rx, ry, ang, depth) in PUDDLES:
        ca, sa = math.cos(ang), math.sin(ang); dx, dy = X - cx, Y - cy
        u = (dx * ca + dy * sa) / rx; v = (-dx * sa + dy * ca) / ry
        wet = np.maximum(wet, np.clip(1.6 - np.sqrt(u * u + v * v), 0, 1))
    dA = seg_dist_np(X, Y, HEDGE_A)
    hedges = [HEDGE_A, HEDGE_B, HEDGE_C, HEDGE_D, HEDGE_E, HEDGE_F]
    dh = np.min(np.stack([seg_dist_np(X, Y, h) for h in hedges]), axis=0)
    litter = np.clip(1 - (dh - 0.6) / 1.4, 0, 1)
    for (tx, ty, tr) in TREES_LITTER:
        litter = np.maximum(litter, np.clip(1 - np.hypot(X - tx, Y - ty) / tr, 0, 1) ** 1.5 * 0.85)
    bank = np.clip(1 - (dh - 0.2) / 0.7, 0, 1)
    # the ditch along hedge A (field side): standing water strip in the bottom
    hy = np.interp(X, [p[0] for p in HEDGE_A], [p[1] for p in HEDGE_A])
    ditch = np.clip(1 - np.abs(dA - 1.15) / 0.35, 0, 1) * (Y < hy) * np.clip((stile_d - 1.4) / 1.0, 0, 1)
    wet = np.maximum(wet, ditch)
    gravel = np.clip(1 - (np.hypot(X - HOUSE.x, Y - HOUSE.y + 8) - 9) / 2, 0, 1)
    infield = (Y < hy - 0.4) & (X < 9.3) & (X > -41) & (Y > -46.5)
    ph = (X - 1.4 * np.sin(Y / 23.0)) / 7.2
    furrow = np.clip((-np.cos(2 * np.pi * ph) - 0.55) / 0.45, 0, 1) * infield
    wet = np.maximum(wet, 0.5 * furrow)
    a = np.stack([mud, wet, litter, np.maximum(bank * 0.8, gravel * 0.0)], axis=-1).astype(np.float32)
    return K.np_image("A_FieldMasks", a[::-1], noncolor=True)     # row 0 must be the south edge (np_image flips rows)

TREES_LITTER = [(-9.6, 7.0, 8.0), (16.2, 10.0, 5.0), (9.9, -5.0, 4.5), (-20.0, 43.0, 7.0)]

# ----------------------------------------------------------------------------- painted atlases (foliage cards)
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

def grass_atlas():
    """1024 x 1024: row 0 (256 high): four short pasture tufts; rows 1-2 (512 high): four long, wet, lodged margin
    grasses with a few seed heads and straw; row 3: soft rush, dock, dead umbels, nettle."""
    S = 1024; cv = Canvas(S, S)
    R = random.Random(7)
    greens = [(0.29, 0.39, 0.15), (0.34, 0.45, 0.17), (0.26, 0.35, 0.13), (0.39, 0.47, 0.19), (0.31, 0.42, 0.16)]
    tips = [(0.48, 0.55, 0.27), (0.52, 0.57, 0.30), (0.44, 0.51, 0.24)]
    straw = [(0.64, 0.57, 0.39), (0.57, 0.50, 0.33), (0.70, 0.63, 0.45)]
    # short tufts: cells 256 x 256, base at the bottom
    for c in range(4):
        x0 = c * 256; base = 252; cv.clip = (x0 + 1, 1, x0 + 255, 256)
        for i in range(70 + c * 8):
            bx = x0 + 128 + R.gauss(0, 30); g = R.choice(greens); t = R.choice(tips)
            if R.random() < 0.08: g, t = R.choice(straw), R.choice(straw)
            L = R.uniform(90, 235) * (0.8 if c == 3 else 1.0)
            blade(cv, bx, base, L, R.gauss(0, 0.32) + (bx - x0 - 128) / 220, R.gauss(0, 0.5), R.uniform(2.6, 4.2), g, t)
    # long lodged margin grass: cells 256 x 512 (rows 1-2)
    for c in range(4):
        x0 = c * 256; base = 256 + 508; cv.clip = (x0 + 1, 257, x0 + 255, 768)
        for i in range(55):
            bx = x0 + 128 + R.gauss(0, 34); dead = R.random() < (0.28 if c in (1, 3) else 0.15)
            g = R.choice(straw) if dead else R.choice(greens); t = R.choice(straw) if dead else R.choice(tips)
            L = R.uniform(220, 490); lean = R.gauss(0, 0.28) + (bx - x0 - 128) / 260
            curve = R.choice((-1, 1)) * R.uniform(0.4, 1.6)        # wet grass bends over
            ex, ey = blade(cv, bx, base, L, lean, curve, R.uniform(3.0, 5.0), g, t, segs=12)
            if R.random() < 0.12:                                    # an old seed head
                for k in range(9):
                    cv.ellipse(ex + R.gauss(0, 4), ey + R.gauss(0, 7) + k * 2.5, 2.0, 6.0, R.gauss(0, 0.3), R.choice(straw) + (1.0,))
    # row 3: cells 256 x 256
    y0 = 768; base = y0 + 252
    # (0) soft rush: dark, upright, round stems with brown flower clusters
    cv.clip = (1, 769, 255, 1024)
    for i in range(80):
        bx = 128 + R.gauss(0, 22); L = R.uniform(150, 245)
        g = (0.24, 0.34, 0.13) if R.random() > 0.2 else (0.50, 0.45, 0.28)
        ex, ey = blade(cv, bx, base, L, R.gauss(0, 0.16) + (bx - 128) / 300, R.gauss(0, 0.12), 2.4, g, (g[0] * 1.35, g[1] * 1.3, g[2] * 1.2), segs=8)
        if R.random() < 0.15: cv.ellipse(ex - 6 * (bx - 128) / 100, ey + 40, 4, 7, 0.0, (0.30, 0.22, 0.12, 1.0))
    cv.clip = (257, 769, 511, 1024)
    # (1) dock: broad wavy leaves from a rosette, some rust-spotted, one dead seed stalk
    for i in range(7):
        a = R.uniform(-1.1, 1.1); L = R.uniform(120, 210); W = L * 0.22
        cx, cy = 256 + 128 + math.sin(a) * L * 0.5, base - math.cos(a) * L * 0.5
        col = R.choice([(0.30, 0.40, 0.15), (0.36, 0.43, 0.18), (0.46, 0.34, 0.17)])
        cv.ellipse(cx, cy, W, L * 0.5, a, col + (1.0,), soft=1.0, tip=0.45)
        cv.line((256 + 128, base), (cx + math.sin(a) * L * 0.45, cy - math.cos(a) * L * 0.45), 1.6, 0.6, (0.30, 0.22, 0.12, 1.0))
    sx = 256 + 140
    cv.line((sx, base), (sx + 8, base - 240), 2.6, 1.2, (0.34, 0.20, 0.10, 1.0))
    for k in range(18):
        yy = base - 120 - k * 6.5; cv.ellipse(sx + 4 + R.gauss(0, 3) + k * 0.3, yy, 6, 3.2, R.gauss(0, 0.4), (0.40, 0.18, 0.08, 1.0))
    cv.clip = (513, 769, 767, 1024)
    # (2) dead umbels (cow parsley / hogweed skeletons), straw and grey
    for i in range(4):
        bx = 512 + 128 + R.gauss(0, 34); L = R.uniform(170, 240); a = R.gauss(0, 0.12)
        ex, ey = blade(cv, bx, base, L, a, R.gauss(0, 0.15), 2.8, (0.42, 0.36, 0.25), (0.55, 0.50, 0.40), segs=8)
        for k in range(9):
            ra = -1.2 + k * 0.3; rx, ry = ex + math.sin(ra) * 26, ey - math.cos(ra) * 14 - 6
            cv.line((ex, ey), (rx, ry), 1.0, 0.8, (0.50, 0.45, 0.36, 1.0))
            cv.ellipse(rx, ry - 2, 3.0, 1.8, 0, (0.42, 0.34, 0.22, 1.0))
    cv.clip = (769, 769, 1023, 1024)
    # (3) nettle: dark toothed leaves in opposite pairs on wiry stems, half died back
    for i in range(6):
        bx = 768 + 128 + R.gauss(0, 30); L = R.uniform(140, 235); a = R.gauss(0, 0.15)
        x, y = bx, base
        for k in range(6):
            nx, ny = x + math.sin(a) * L / 6, y - math.cos(a) * L / 6
            cv.line((x, y), (nx, ny), 1.8, 1.4, (0.20, 0.17, 0.10, 1.0)); x, y = nx, ny
            if k >= 1:
                col = R.choice([(0.20, 0.31, 0.11), (0.24, 0.34, 0.12), (0.44, 0.38, 0.18)])
                for sgn in (-1, 1):
                    lw = 18 - k * 1.5
                    cv.ellipse(x + sgn * lw * 0.8, y - 3, lw * 0.55, lw, a + sgn * 1.15, col + (1.0,), tip=0.5)
    cv.clip = None; cv.bleed(6)
    return K.np_image("A_GrassCards", cv.a)

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
            else:   # field maple: five-lobed, butter yellow
                for j in range(5):
                    lb = b + (j - 2) * 0.62
                    cv.ellipse(lx + math.sin(lb) * s * 0.35, ly - math.cos(lb) * s * 0.35, s * 0.24, s * 0.42, lb, col + (1.0,), tip=0.25)
        if kind == 'haw' and R.random() < 0.55:      # haws: dark red berries in small bunches
            for k in range(R.randint(2, 5)):
                cv.ellipse(x + R.gauss(0, 6), y + R.gauss(0, 6), 3.6, 4.0, 0, (0.42, 0.05, 0.04, 1.0))
                cv.ellipse(x + R.gauss(0, 6) - 1, y + R.gauss(0, 6) - 1, 1.2, 1.2, 0, (0.70, 0.25, 0.20, 1.0))

def spray_atlas(name, kind, seed, S=1024):
    cv = Canvas(S, S); R = random.Random(seed); h = S // 2
    for (cx, cy) in ((0, 0), (h, 0), (0, h), (h, h)):
        cv.clip = (cx + 1, cy + 1, cx + h - 1, cy + h - 1)
        for k in range(5 if kind == 'haw' else (3 if kind != 'twig' else 2)):
            spray(cv, cx + 4, cy + 4, cx + h - 4, cy + h - 4, R, kind)
    cv.clip = None; cv.bleed(6)
    return K.np_image(name, cv.a)

print("painting atlases ...", flush=True)
IMG_GRASS = grass_atlas()
IMG_HAW = spray_atlas("A_HedgeSprays", 'haw', 21)
IMG_OAK = spray_atlas("A_OakSprays", 'oak', 22)
IMG_TWIG = spray_atlas("A_BareTwigs", 'twig', 23)
IMG_MAPLE = spray_atlas("A_MapleSprays", 'maple', 24, S=512)
IMG_MASK = make_masks()

# ----------------------------------------------------------------------------- materials
M_GRASS = image_mat("M_GrassCards", IMG_GRASS, rough=0.42, alpha=True, spec=0.45)
def blade_tones():
    """16 x 64 opaque strip for the solid grass blades: eight tone columns (greens, two straw), root (bottom) dark to
    tip light. Opaque blades cost no alpha-test overdraw on the Quest's tile GPU."""
    cols = [(0.29, 0.39, 0.15), (0.34, 0.45, 0.17), (0.26, 0.35, 0.13), (0.39, 0.47, 0.19), (0.31, 0.42, 0.16), (0.36, 0.44, 0.18),
            (0.57, 0.50, 0.33), (0.64, 0.57, 0.39)]
    tips = [(0.48, 0.55, 0.27), (0.52, 0.57, 0.30), (0.44, 0.51, 0.24), (0.50, 0.56, 0.28), (0.46, 0.53, 0.25), (0.52, 0.56, 0.30),
            (0.68, 0.61, 0.43), (0.72, 0.65, 0.47)]
    a = np.ones((64, 16, 4), np.float32)
    for i in range(8):
        for r in range(64):
            t = 1.0 - r / 63.0                     # row 0 = top = tip
            g = [c * (0.45 + 0.55 * min(1.0, t * 1.6)) for c in cols[i]]
            col = [lerp(g[k], tips[i][k], smoothstep(0.55, 1.0, t)) for k in range(3)]
            a[r, i * 2:i * 2 + 2, :3] = col
    return K.np_image("A_BladeTones", a)
M_BLADES = image_mat("M_GrassBlades", blade_tones(), rough=0.5, spec=0.4)
M_HAW = image_mat("M_HedgeSprays", IMG_HAW, rough=0.5, alpha=True)
M_OAKL = image_mat("M_OakSprays", IMG_OAK, rough=0.55, alpha=True)
M_TWIG = image_mat("M_BareTwigs", IMG_TWIG, rough=0.6, alpha=True)
M_MAPLE = image_mat("M_MapleSprays", IMG_MAPLE, rough=0.55, alpha=True)

def mask_lookup(nt, loc=(-1600, 600)):
    co = obj_coords(nt, (loc[0] - 400, loc[1]))
    mp = node(nt, "ShaderNodeMapping", (loc[0] - 200, loc[1])); mp.inputs["Location"].default_value = (0.5, 0.5, 0); mp.inputs["Scale"].default_value = (1 / (2 * MASK_EXT), 1 / (2 * MASK_EXT), 0)
    # mapping: (p * scale) + location, with vector type POINT: location applied after scale
    nt.links.new(co, mp.inputs["Vector"])
    # wobble the lookup a little so the 6 cm mask pixels never show
    wob = noise_(nt, co, 1.6, 3, 0.5, loc=(loc[0] - 200, loc[1] - 250))
    wv = node(nt, "ShaderNodeVectorMath", (loc[0], loc[1] - 200), operation='MULTIPLY_ADD'); wv.inputs[1].default_value = (0.0016, 0.0016, 0)
    wv.inputs[2].default_value = (-0.0008, -0.0008, 0)
    nt.links.new(wob.outputs["Color"], wv.inputs[0])
    add = node(nt, "ShaderNodeVectorMath", (loc[0] + 150, loc[1]), operation='ADD'); nt.links.new(mp.outputs["Vector"], add.inputs[0]); nt.links.new(wv.outputs[0], add.inputs[1])
    t = node(nt, "ShaderNodeTexImage", (loc[0] + 350, loc[1])); t.image = IMG_MASK; t.extension = 'EXTEND'
    nt.links.new(add.outputs[0], t.inputs["Vector"])
    s = node(nt, "ShaderNodeSeparateColor", (loc[0] + 650, loc[1])); nt.links.new(t.outputs["Color"], s.inputs["Color"])
    return s.outputs[0], s.outputs[1], s.outputs[2], t.outputs["Alpha"], co

def ground_mat(name):
    """Wet pasture: dark green grazed sward with yellowed and brown patches and moss; the path's churned umber mud,
    wet and glossy, with boot and hoof prints; puddle rims; fallen leaves under the hedges and trees; bare bank soil."""
    m, nt, b = new_mat(name)
    mud_m, wet_m, lit_m, bank_m, co = mask_lookup(nt)
    sx = sep_xyz(nt, co, (-1800, -200))
    # sward
    n1 = noise_(nt, co, 0.9, 5, 0.6, loc=(-1300, 300)); n2_ = noise_(nt, co, 7.0, 6, 0.65, loc=(-1300, 100)); n3 = noise_(nt, co, 38.0, 4, 0.6, loc=(-1300, -100))
    sw = ramp(nt, [(0.30, c4((0.075, 0.115, 0.032))), (0.48, c4((0.10, 0.145, 0.042))), (0.62, c4((0.125, 0.16, 0.048))), (0.75, c4((0.17, 0.18, 0.065)))], (-1000, 300))
    nt.links.new(math_(nt, 'ADD', math_(nt, 'MULTIPLY', n1.outputs["Fac"], 0.6, (-1150, 350)), math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.4, (-1150, 250)), (-1100, 300)), sw.inputs["Fac"])
    blades = maprange(nt, n3.outputs["Fac"], 0.3, 0.7, 0.72, 1.18, (-1000, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, sw.outputs["Color"], blades, (-800, 300))
    # the sward's own tufts (it carries the grass where there are no grass cards): tussock clumps a few decimetres
    # across, lighter on top and dark between, and a fine mottle of tuft-sized cells with blade tips catching the light
    tus = voronoi_(nt, co, 3.2, loc=(-1500, 1300)); tuf = voronoi_(nt, co, 16.0, loc=(-1500, 1100))
    tus_k = maprange(nt, tus.outputs["Distance"], 0.05, 0.6, 1.18, 0.72, (-1300, 1300))
    tuf_k = math_(nt, 'MULTIPLY', maprange(nt, tuf.outputs["Distance"], 0.0, 0.55, 1.12, 0.78, (-1300, 1150)),
                  maprange(nt, sep_xyz(nt, tuf.outputs["Color"], (-1450, 950)).outputs[0], 0.0, 1.0, 0.85, 1.15, (-1300, 1000)), (-1150, 1100))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, math_(nt, 'MULTIPLY', tus_k, tuf_k, (-1000, 1150)), (-750, 450))
    tip = maprange(nt, n3.outputs["Fac"], 0.55, 0.75, 0.0, 0.35, (-1000, 1000))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', tip, maprange(nt, tus.outputs["Distance"], 0.1, 0.4, 1.0, 0.0, (-1150, 900)), (-900, 950)), col, (0.20, 0.21, 0.09, 1), (-700, 500))
    # straw-dead patches and moss in the furrows
    dead = maprange(nt, noise_(nt, co, 3.0, 4, 0.6, loc=(-1300, -300)).outputs["Fac"], 0.58, 0.72, 0.0, 0.55, (-1000, -300))
    col = mix_rgb(nt, 'MIX', dead, col, (0.20, 0.17, 0.08, 1), (-650, 300))
    # leaf litter
    lv = voronoi_(nt, co, 9.0, loc=(-1300, -550))
    litc = ramp(nt, [(0.0, c4((0.20, 0.10, 0.035))), (0.35, c4((0.28, 0.16, 0.05))), (0.7, c4((0.16, 0.11, 0.05))), (1.0, c4((0.30, 0.22, 0.09)))], (-1000, -550))
    nt.links.new(lv.outputs["Color"], litc.inputs["Fac"])
    lit_n = maprange(nt, math_(nt, 'MULTIPLY', lit_m, maprange(nt, noise_(nt, co, 2.2, 3, 0.5, loc=(-1300, -750)).outputs["Fac"], 0.3, 0.7, 0.5, 1.4, (-1100, -750)), (-950, -700)), 0.25, 0.7, 0, 1, (-800, -700))
    col = mix_rgb(nt, 'MIX', lit_n, col, litc.outputs["Color"], (-500, 300))
    # bank soil showing through at the hedge foot
    bank_soil = math_(nt, 'MULTIPLY', bank_m, maprange(nt, noise_(nt, co, 4.0, 3, 0.6, loc=(-1300, -950)).outputs["Fac"], 0.45, 0.62, 0, 0.8, (-1100, -950)), (-900, -950))
    col = mix_rgb(nt, 'MIX', bank_soil, col, (0.11, 0.08, 0.05, 1), (-350, 300))
    # mud: churned, with prints (voronoi pits) and trampled grass at its edge
    mudn = noise_(nt, co, 2.8, 4, 0.6, distortion=0.4, loc=(-1300, 800))
    patch = noise_(nt, co, 0.9, 3, 0.5, loc=(-1300, 650))
    edge = maprange(nt, math_(nt, 'ADD', math_(nt, 'MULTIPLY', mud_m, maprange(nt, patch.outputs["Fac"], 0.35, 0.65, 0.75, 1.25, (-1150, 650)), (-1100, 700)),
                              math_(nt, 'MULTIPLY', mudn.outputs["Fac"], 0.8, (-1100, 850)), (-1000, 800)), 0.75, 1.1, 0, 1, (-850, 800), 'SMOOTHSTEP')
    prints = voronoi_(nt, co, 5.5, loc=(-1300, 1050))
    pit = maprange(nt, prints.outputs["Distance"], 0.05, 0.32, 0, 1, (-1050, 1050))
    mudc = ramp(nt, [(0.0, c4((0.042, 0.032, 0.022))), (0.5, c4((0.075, 0.056, 0.036))), (1.0, c4((0.11, 0.085, 0.058)))], (-850, 1000))
    nt.links.new(math_(nt, 'MULTIPLY', pit, mudn.outputs["Fac"], (-950, 1000)), mudc.inputs["Fac"])
    col = mix_rgb(nt, 'MIX', edge, col, mudc.outputs["Color"], (-200, 300))
    # puddle rims and the ditch: darker, saturated with water
    wetf = math_(nt, 'MAXIMUM', wet_m, math_(nt, 'MULTIPLY', edge, 0.6, (-400, 650)), (-300, 650))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', wet_m, 0.45, (-300, 550)), col, (0.55, 0.55, 0.55, 1), (-50, 300))
    col = K.ao_mul(nt, col, 0.25, 0.25, (100, -500))
    nt.links.new(col, b.inputs["Base Color"])
    rough = mix_f(nt, wetf, 0.75, 0.42, (0, 0))
    rough = math_(nt, 'SUBTRACT', rough, math_(nt, 'MULTIPLY', lit_n, -0.05, (50, -100)), (150, 0))
    nt.links.new(rough, b.inputs["Roughness"])
    # height: grass texture, mud prints, litter leaves
    h = math_(nt, 'ADD', math_(nt, 'MULTIPLY', n3.outputs["Fac"], 0.4, (-300, -1200)), math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', pit, edge, (-500, -1300)), 0.8, (-300, -1300)), (-150, -1250))
    h = math_(nt, 'ADD', h, math_(nt, 'MULTIPLY', lv.outputs["Distance"], math_(nt, 'MULTIPLY', lit_n, 0.5, (-500, -1450)), (-300, -1450)), (0, -1300))
    h = math_(nt, 'ADD', h, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, math_(nt, 'ADD', tus.outputs["Distance"], math_(nt, 'MULTIPLY', tuf.outputs["Distance"], 0.5, (-600, -1600)), (-450, -1600)), (-350, -1600)), math_(nt, 'SUBTRACT', 1.0, edge, (-500, -1700)), (-250, -1650)), (100, -1400))
    bump_from(nt, b, h, 0.35, 0.012, (150, -400))
    return m

M_GROUND = ground_mat("M_GroundNear")
M_FARLAND = ground_mat("M_FarLand")

def water_mat(name="M_Puddle"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    n = noise_(nt, co, 3.0, 3, 0.5, loc=(-900, -300))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-700, 0)), (0.03, 0.025, 0.018, 1), (0.05, 0.04, 0.028, 1), (-400, 0))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.05; b.inputs["Specular IOR Level"].default_value = 0.4; b.inputs["IOR"].default_value = 1.33
    # very faint ripples from drips
    v = voronoi_(nt, co, 14.0, loc=(-900, -600))
    bump_from(nt, b, maprange(nt, v.outputs["Distance"], 0.0, 0.5, 0, 1, (-600, -600)), 0.015, 0.002, (0, -500))
    return m
M_WATER = water_mat()

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
M_OAKBARK = bark_mat("M_OakBark")
M_ASHBARK = bark_mat("M_AshBark", base=(0.26, 0.26, 0.24), dark=(0.11, 0.11, 0.10), light=(0.36, 0.36, 0.33), fissure=True, green=0.5, scale=1.8)

def leaf_mass_mat(name, pal, leaf=11.0, lump=1.4, dark=0.30):
    """Opaque foliage mass (hedge bodies, far tree crowns, the inside of near crowns): a mottle of leaf-sized cells
    in the leaf palette (sRGB picks), darkened in the creases between lumps and in the hollows (AO), with a leafy bump.
    It replaces layered alpha cards where they cost most on the Quest's tile GPU."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, leaf, loc=(-1200, 200)); v2 = voronoi_(nt, co, leaf * 2.7, loc=(-1200, 0))
    cl = noise_(nt, co, lump, 4, 0.55, loc=(-1200, -250))
    lin = [K.srgb(c) for c in pal]
    stops = [(i / (len(lin) - 1) * 0.9 + 0.05, c4(c)) for i, c in enumerate(lin)]
    cr = ramp(nt, stops, (-850, 300))
    nt.links.new(v.outputs["Color"], cr.inputs["Fac"])
    # leaf-edge shadow: dark at the cell borders of the fine cells
    edge = maprange(nt, v2.outputs["Distance"], 0.0, 0.4, dark, 1.05, (-850, 0))
    lumpf = maprange(nt, cl.outputs["Fac"], 0.35, 0.68, 0.55, 1.1, (-850, -250))
    sh = math_(nt, 'MULTIPLY', edge, lumpf, (-650, -100))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, cr.outputs["Color"], sh, (-450, 200))
    col = K.ao_mul(nt, col, 0.6, 0.45, (-350, -500))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.72
    hgt = math_(nt, 'ADD', math_(nt, 'MULTIPLY', v2.outputs["Distance"], 0.5, (-650, -400)), cl.outputs["Fac"], (-500, -400))
    bump_from(nt, b, hgt, 0.75, 0.05)
    return m
PAL_HAW = [(0.20, 0.26, 0.10), (0.27, 0.35, 0.13), (0.32, 0.40, 0.15), (0.24, 0.31, 0.11), (0.38, 0.42, 0.15), (0.45, 0.40, 0.15), (0.30, 0.37, 0.14)]
PAL_OAK = [(0.36, 0.25, 0.11), (0.48, 0.33, 0.15), (0.42, 0.30, 0.13), (0.50, 0.42, 0.20), (0.38, 0.36, 0.16), (0.55, 0.42, 0.19), (0.32, 0.22, 0.10)]
PAL_MAPLE = [(0.50, 0.38, 0.11), (0.58, 0.45, 0.14), (0.44, 0.40, 0.13), (0.62, 0.50, 0.17), (0.40, 0.30, 0.10)]
M_HEDGEMASS = leaf_mass_mat("M_HedgeMass", PAL_HAW, leaf=12.0, lump=1.6, dark=0.5)

def weathered_oak(name="M_StileOak"):
    """Old oak gone silver-grey, split along the grain, green-grey lichen, dark and wet at the foot, the top rail
    polished paler by hands."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1500, -600))
    mp = node(nt, "ShaderNodeMapping", (-1400, 0)); mp.inputs["Scale"].default_value = (30, 30, 1.6); nt.links.new(co, mp.inputs["Vector"])
    g = noise_(nt, mp.outputs["Vector"], 2.0, 8, 0.7, loc=(-1150, 0))
    cr = ramp(nt, [(0.3, c4((0.10, 0.095, 0.085))), (0.5, c4((0.22, 0.21, 0.19))), (0.7, c4((0.30, 0.29, 0.26)))], (-850, 0))
    nt.links.new(g.outputs["Fac"], cr.inputs["Fac"])
    lich = voronoi_(nt, co, 16.0, loc=(-1150, -300))
    lm = math_(nt, 'MULTIPLY', maprange(nt, lich.outputs["Distance"], 0.25, 0.05, 0, 1, (-900, -300)), maprange(nt, noise_(nt, co, 3.0, 3, 0.5, loc=(-1150, -500)).outputs["Fac"], 0.5, 0.65, 0, 1, (-900, -500)), (-700, -350))
    col = mix_rgb(nt, 'MIX', lm, cr.outputs["Color"], (0.36, 0.40, 0.30, 1), (-500, 0))
    foot = maprange(nt, s.outputs["Z"], 0.35, 0.0, 0, 0.6, (-900, -700))
    col = mix_rgb(nt, 'MIX', foot, col, (0.06, 0.05, 0.035, 1), (-300, 0))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, g.outputs["Fac"], 0.3, 0.7, 0.55, 0.85, (-500, -200)), b.inputs["Roughness"])
    split = maprange(nt, g.outputs["Fac"], 0.28, 0.36, 0, 1, (-700, -800))
    bump_from(nt, b, split, 0.5, 0.004, (0, -400))
    return m
M_STILE = weathered_oak()
M_GATE = weathered_oak("M_GateOak")

def stucco_mat(name="M_HouseStucco"):
    """Netherfield's walls: lined-out stucco in a pale warm stone colour, streaked below sills and cornice by rain,
    darker plinth."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1500, -500))
    n = noise_(nt, co, 1.2, 4, 0.6, loc=(-1200, 0))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.35, 0.65, 0, 1, (-1000, 0)), (0.56, 0.53, 0.47, 1), (0.64, 0.61, 0.55, 1), (-800, 0))
    # ashlar lines (stucco lined out to imitate stone)
    zl = math_(nt, 'FRACT', math_(nt, 'DIVIDE', s.outputs["Z"], 0.38, (-1300, -800)), None, (-1150, -800))
    line = maprange(nt, zl, 0.0, 0.04, 0.82, 1.0, (-1000, -800))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, line, (-600, 0))
    st = noise_(nt, co, 1.0, 3, 0.5, loc=(-1200, -300))
    mp = node(nt, "ShaderNodeMapping", (-1350, -300)); mp.inputs["Scale"].default_value = (6, 6, 0.25); nt.links.new(co, mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], st.inputs["Vector"])
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, st.outputs["Fac"], 0.5, 0.75, 0, 0.35, (-1000, -300)), col, (0.62, 0.60, 0.56, 1), (-400, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    return m
M_STUCCO = stucco_mat()
M_SLATE = noisy("M_HouseSlate", [(0.09, 0.10, 0.11), (0.13, 0.14, 0.15), (0.11, 0.115, 0.12)], scale=30, rough=0.45, stretch=(1, 1, 3))
M_HOUSEWIN = plain("M_HouseWindows", (0.025, 0.03, 0.035), rough=0.08)
M_HOUSEPAINT = plain("M_HousePaint", (0.72, 0.71, 0.67), rough=0.5)
M_CHURCH = noisy("M_FarStone", [(0.30, 0.31, 0.32), (0.36, 0.36, 0.36)], scale=4, rough=0.9)

# ----------------------------------------------------------------------------- the terrain (built first: everything else sits on it)
def build_terrain():
    """A grid warped so its spacing is fine at the reader (8 cm) and coarse at the land's edge, carved by H(), then
    decimated (the quadric collapse keeps the furrows, ruts and puddle hollows) and split into near / far parts."""
    N = 300; a = 2.2; tmax = math.asinh(LAND_R / a)
    ts = [math.sinh(-tmax + 2 * tmax * i / N) * a for i in range(N + 1)]
    me = bpy.data.meshes.new("Terrain"); bm = bmesh.new()
    vs = [[None] * (N + 1) for _ in range(N + 1)]
    for j, y in enumerate(ts):
        for i, x in enumerate(ts):
            if math.hypot(x, y) > LAND_R + 6: continue
            vs[j][i] = bm.verts.new((x, y, Hz(x, y)))
    for j in range(N):
        for i in range(N):
            q = (vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i])
            if all(q): bm.faces.new(q)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Terrain", me); link(o)
    print("terrain raw tris", len(me.polygons) * 2, flush=True)
    md = o.modifiers.new("Dec", 'DECIMATE'); md.decimate_type = 'COLLAPSE'; md.ratio = 0.06; md.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.modifier_apply(modifier="Dec"); o.select_set(False)
    print("terrain decimated tris", len(o.data.polygons), flush=True)
    return o

TERRAIN = build_terrain()
_bm = bmesh.new(); _bm.from_mesh(TERRAIN.data); BVH = BVHTree.FromBMesh(_bm); _bm.free()

def gz(x, y):
    hit = BVH.ray_cast(Vector((x, y, 60.0)), Vector((0, 0, -1)))
    return hit[0].z if hit[0] is not None else Hz(x, y)

def split_terrain():
    """near ground (4K, warped UVs) and far.land (planar UVs, 1K)."""
    near = TERRAIN; far = near.copy(); far.data = near.data.copy(); link(far)
    for o, keep_near in ((near, True), (far, False)):
        bm = bmesh.new(); bm.from_mesh(o.data)
        kill = [f for f in bm.faces if (max(abs(v.co.x) for v in f.verts) < NEAR and max(abs(v.co.y) for v in f.verts) < NEAR) != keep_near]
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        uvl = bm.loops.layers.uv.new("UVMap")
        A = 5.0; tm = math.asinh(NEAR / A)
        for f in bm.faces:
            for l in f.loops:
                x, y = l.vert.co.x, l.vert.co.y
                if keep_near: l[uvl].uv = (0.5 + 0.5 * math.asinh(x / A) / tm, 0.5 + 0.5 * math.asinh(y / A) / tm)
                else: l[uvl].uv = (0.5 + 0.5 * x / (LAND_R + 6), 0.5 + 0.5 * y / (LAND_R + 6))
        bm.to_mesh(o.data); bm.free()
        o.data.materials.clear(); o.data.materials.append(M_GROUND if keep_near else M_FARLAND)
        o.name = "GroundNear" if keep_near else "far.land"
        for p in o.data.polygons: p.use_smooth = True
split_terrain()

# ----------------------------------------------------------------------------- the puddle water
def build_puddles():
    """Each puddle is a flat fan at its water level, its rim found by marching outwards over the decimated terrain
    until the ground rises above the water (so the water never floats or pokes through the mud)."""
    mb_v = []; mb_f = []
    for p in PUDDLES:
        cx, cy, rx, ry, ang, depth = p
        base = gz(cx, cy)
        level = base + depth * 0.62
        rim = []
        NR = 40; radii = []
        for k in range(NR):
            a = 2 * math.pi * k / NR
            d = Vector((math.cos(a + ang) * rx, math.sin(a + ang) * ry, 0))
            d = Vector((math.cos(ang) * math.cos(a) * rx - math.sin(ang) * math.sin(a) * ry, math.sin(ang) * math.cos(a) * rx + math.cos(ang) * math.sin(a) * ry, 0))
            t = 0.0; last = 0.0
            while t < 1.6:
                q = Vector((cx, cy, 0)) + d * t
                if gz(q.x, q.y) > level - 0.003: break
                last = t; t += 0.02
            radii.append((d, max(0.02, last)))
        for k in range(NR):          # smooth the marched rim (no jagged steps), staying inside the lowest neighbour
            d, t = radii[k]; tt = min(t, (radii[k - 1][1] + 2 * t + radii[(k + 1) % NR][1]) / 4)
            q = Vector((cx, cy, 0)) + d * tt * 0.97
            rim.append((q.x, q.y, level))
        if max(math.hypot(r[0] - cx, r[1] - cy) for r in rim) < 0.06: continue
        c = len(mb_v); mb_v.append((cx, cy, level)); mb_v.extend(rim)
        for k in range(NR): mb_f.append((c, c + 1 + k, c + 1 + (k + 1) % NR))
    o = mesh_from("water.puddle.path", mb_v, mb_f, M_WATER)
    for poly in o.data.polygons:            # water seen from above must face up (from below, Cycles sees total internal reflection)
        if poly.normal.z < 0: poly.flip()
    o.data.update()
    return o
build_puddles()

# ----------------------------------------------------------------------------- foliage: card helpers
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

# ----------------------------------------------------------------------------- grass, rushes and herbs
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
        if fnrm.dot(Vector((-x, -y, EYE - z))) >= 0: mb.face(i0, i1, i2)
        else: mb.face(i1, i0, i2)

def build_grass():
    mb = MB(); sb = MB()
    R = random.Random(5); RS = random.Random(55)
    # short pasture tufts: clumped (grazed sward, tussocks), thinning out by 9 m (beyond, the baked ground carries the
    # sward); each a single card turned towards the reading position (the reader does not walk about), leaning back a
    # little. Kept sparse right under the reader, where each card would fill much of the view (alpha overdraw).
    placed = 0
    for i in range(20000):
        r = 9.0 * R.random() ** 1.25
        a = R.uniform(0, 2 * math.pi); x, y = r * math.sin(a), r * math.cos(a)
        if r < 0.6: continue
        if r < 2.2 and R.random() < 0.55 * (1.0 - smoothstep(0.6, 2.2, r)) + 0.25: continue
        if not in_my_field(x, y) and not (x > 9.9 and y < 8): continue
        d, s_, w = path_info(x, y)
        if d < w * 0.85: continue
        if d < w * 1.5 and R.random() < 0.55: continue
        if any(puddle_s(x, y, p) < 1.2 for p in PUDDLES if abs(x - p[0]) < 2.5 and abs(y - p[1]) < 2.5): continue
        clump = 0.5 + 0.5 * (0.7 * n2(x, y, 1.7, 4.0) + 0.3 * n2(x, y, 0.5, 9.0))
        if R.random() > clump ** 1.6 * 1.6: continue
        z = gz(x, y)
        sc = R.uniform(0.7, 1.2) * (0.8 + 0.5 * clump)
        if r > 3.6 and RS.random() < 0.55 * smoothstep(3.6, 6.0, r) + 0.15:
            solid_tuft(sb, RS, x, y, z, sc * 1.1); placed += 1; continue
        to_r = Vector((-x, -y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + R.gauss(0, 0.45)
        right = Vector((math.cos(ya), math.sin(ya), 0)) * 0.30 * sc
        up = Vector((0, 0, 0.24 * sc)) - to_r * 0.06 * sc
        card(mb, (x, y, z - 0.015), right, up, R.choice(GRASS_SHORT), 0.0, 1.0)
        placed += 1
        if placed > 1100: break
    # long, lodged margin grass along the hedge feet and round the stile and gate posts
    for poly, lo, hi, nmax in ((HEDGE_A, -14, 12, 85), (HEDGE_B, -10, 8.5, 45)):
        cnt = 0
        for (x, y, dx, dy) in poly_sample(poly, 0.22):
            if not (lo < (x if poly is HEDGE_A else y) < hi): continue
            dist = math.hypot(x, y)
            if dist > 15.0 or R.random() > (0.8 - smoothstep(6, 15, dist) * 0.5): continue
            for side in (-1, 1):
                if R.random() < 0.45: continue
                off = R.uniform(0.55, 1.15) if side < 0 else R.uniform(0.55, 0.95)
                px, py = x + dy * off * side, y - dx * off * side
                if poly is HEDGE_A and any(math.hypot(px - g[0], py - g[1]) < g[2] + 0.2 for g in GAPS_A): continue
                if poly is HEDGE_B and any(math.hypot(px - g[0], py - g[1]) < g[2] + 0.4 for g in GAPS_B): continue
                z = gz(px, py); sc = R.uniform(0.7, 1.25)
                cell = R.choice(GRASS_LONG)
                lean = Vector((R.gauss(0, 0.35), R.gauss(0, 0.35), 0)) + Vector((dy * side, -dx * side, 0)) * 0.25
                to_r = Vector((-px, -py, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + R.gauss(0, 0.5)
                right = Vector((math.cos(ya), math.sin(ya), 0)) * 0.36 * sc
                card(mb, (px, py, z - 0.02), right, Vector((0, 0, 0.52 * sc)), cell, 0.0, 1.0, bend=lean * 0.3 * sc, segs=2)
                cnt += 1
            if cnt > nmax: break
    # soft rush clumps in the wet furrows and by the gate; docks by the gate and the stile; dead umbels and nettles at hedge feet
    herbs = []
    for i in range(40):
        x, y = R.uniform(-25, 9), R.uniform(-30, 6)
        if not in_my_field(x, y) or math.hypot(x, y) < 2.0: continue
        if abs((furrow_phase(x, y) % 1.0) - 0.5) > 0.12: continue
        if path_info(x, y)[0] < 1.2: continue
        herbs.append(("rush", x, y, R.uniform(0.8, 1.3)))
    herbs += [("dock", GATE.x - 2.8, GATE.y + 1.9, 1.0), ("dock", GATE.x - 3.4, GATE.y - 2.0, 0.85), ("dock", STILE.x + 1.6, STILE.y - 1.25, 0.9),
              ("dock", -2.4, 1.4, 0.75), ("rush", 1.6, 3.1, 1.05), ("rush", -3.0, -1.9, 0.9), ("dock", 2.1, -1.6, 0.7)]
    for (x, y, dx, dy) in poly_sample(HEDGE_A, 1.3):
        if -15 < x < 13 and R.random() < 0.5:
            off = R.uniform(0.45, 0.85); px, py = x + dy * off, y - dx * off
            if math.hypot(px - STILE.x, py - STILE.y) < 1.0: continue
            herbs.append((R.choice(("umbel", "nettle", "nettle", "umbel", "dock")), px, py, R.uniform(0.8, 1.25)))
    for (x, y, dx, dy) in poly_sample(HEDGE_B, 1.6):
        if -14 < y < 8 and R.random() < 0.5:
            px, py = x - 0.6, y
            if abs(py - GATE.y) < 2.0: continue
            herbs.append((R.choice(("umbel", "nettle", "dock")), px, py, R.uniform(0.8, 1.2)))
    for (kind, x, y, sc) in herbs:
        z = gz(x, y); hgt = {"rush": 0.62, "dock": 0.42, "umbel": 1.05, "nettle": 0.75}[kind] * sc
        wid = {"rush": 0.55, "dock": 0.62, "umbel": 0.8, "nettle": 0.6}[kind] * sc
        to_r = Vector((-x, -y, 0)).normalized()
        for k in range(1 if kind != "dock" else 2):
            ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + R.gauss(0, 0.4) + k * 1.2
            right = Vector((math.cos(ya), math.sin(ya), 0)) * wid
            card(mb, (x, y, z - 0.02), right, Vector((R.gauss(0, 0.04), R.gauss(0, 0.04), hgt)) - to_r * hgt * (0.35 if kind == "dock" else 0.0), HERB[kind], 0.0, 0.7 if kind != "umbel" else 1.0)
    # beyond the cards (to ~16 m): opaque blade tufts on the sward's tussocks, so the field's surface stays rough
    for i in range(6000):
        r = RS.uniform(8.0, 16.0); a = RS.uniform(0, 2 * math.pi); x, y = r * math.sin(a), r * math.cos(a)
        if not in_my_field(x, y) and not (x > 9.9 and y < 8): continue
        d, s_, w = path_info(x, y)
        if d < w * 1.1: continue
        if any(puddle_s(x, y, p) < 1.2 for p in PUDDLES if abs(x - p[0]) < 2.5 and abs(y - p[1]) < 2.5): continue
        clump = 0.5 + 0.5 * (0.7 * n2(x, y, 1.7, 4.0) + 0.3 * n2(x, y, 0.5, 9.0))
        if RS.random() > clump ** 2 * 0.9: continue
        solid_tuft(sb, RS, x, y, gz(x, y), RS.uniform(0.8, 1.3) * (0.8 + 0.5 * clump), nbl=4)
        if len(sb.f) > 6400: break
    print("solid grass blades", len(sb.f), flush=True)
    so = sb.build("GrassBlades", M_BLADES)
    if so is not None: set_card_normals(so, lambda p: (Vector((0, 0, 1.0)) + Vector((-p.x, -p.y, 0)).normalized() * 0.8).normalized())
    o = mb.build("GrassCards", M_GRASS)
    set_card_normals(o, lambda p: Vector((0, 0, 1)))
    return o
print("grass ...", flush=True)
build_grass()

# ----------------------------------------------------------------------------- hedges
def build_hedge(name, poly, seed, h0=1.55, w0=1.2, gaps=(), step=0.7, card_density=1.0, card_size=0.75, near_only=None, cards=True, ring=8):
    """A laid-and-grown-out hawthorn hedge on its low bank: a dark lumpy core (narrow at the foot, where the stems show,
    widest at two-thirds of its height) in an opaque leafy material. Near the reader (to ~20 m) a skin of leaf-spray
    cards lies on its upper surface like scales, tilting outwards, so the cards make the face and the ragged silhouette;
    further off the lumpy mass carries the hedge and only a sparse fringe of cards breaks its top line (alpha-tested
    cards are what costs on the Quest's tile GPU). Taller shoots stand above the top."""
    R = random.Random(seed)
    def hgt(x, y): return h0 * (1.0 + 0.16 * n2(x, y, 6.0, seed) + 0.10 * n2(x, y, 1.2, seed + 3) + 0.25 * max(0.0, n2(x, y, 3.0, seed + 9)))
    def wid(x, y): return w0 * (1.0 + 0.2 * n2(x, y, 5.0, seed + 7))
    def gapf(x, y):
        f = 1.0
        for g in gaps:
            dg = math.hypot(x - g[0], y - g[1])
            if dg < g[2]: return 0.0
            if dg < g[2] + 1.2: f = min(f, 0.72 + 0.28 * smoothstep(g[2], g[2] + 1.2, dg))
        return f
    prof = [(-0.30, -0.15), (-0.50, 0.55), (-0.40, 0.92), (0.0, 1.0), (0.40, 0.92), (0.50, 0.55), (0.30, -0.15)]
    core_v = []; core_f = []; prev_ring = None
    for (x, y, dx, dy) in poly_sample(poly, max(step, 0.9 if cards and step < 1.0 else 1.3)):
        f = gapf(x, y)
        if f == 0.0:
            if prev_ring is not None: core_f.append(tuple(prev_ring))
            prev_ring = None; continue
        far_k = smoothstep(12.0, 26.0, math.hypot(x, y)) if cards else 1.0
        bulge = 1.0 + 0.12 * noise.noise(Vector((x * 0.35, y * 0.35, seed + 0.5)))
        gz0 = gz(x, y); hh = hgt(x, y) * f * lerp(0.9, 0.98, far_k) * bulge; ww = wid(x, y) * f * lerp(0.8, 0.95, far_k) * bulge
        nx, ny = dy, -dx; ring_pts = []
        for k, (a, hz) in enumerate(prof):
            jit = 1.0 + 0.16 * noise.noise(Vector((x * 0.9, y * 0.9, k * 1.7 + seed))) + 0.12 * noise.noise(Vector((x * 2.3, y * 2.3, k * 0.9 + seed * 2)))
            ring_pts.append(len(core_v)); core_v.append((x + nx * a * ww * jit, y + ny * a * ww * jit, gz0 + hz * hh))
        if prev_ring is not None:
            for k in range(len(prof) - 1): core_f.append((prev_ring[k], prev_ring[k + 1], ring_pts[k + 1], ring_pts[k]))
        else: core_f.append(tuple(reversed(ring_pts)))
        prev_ring = ring_pts
    if prev_ring is not None: core_f.append(tuple(prev_ring))
    core = mesh_from(name + "Core", core_v, core_f, M_HEDGEMASS, smooth=True)
    if not cards: return core, None
    mb = MB(); cstep = 0.5
    for (x, y, dx, dy) in poly_sample(poly, cstep):
        f = gapf(x, y)
        if f == 0.0: continue
        gz0 = gz(x, y); hh = hgt(x, y) * f; ww = wid(x, y) * f
        nx, ny = dy, -dx; tang = Vector((dx, dy, 0)).normalized()
        dist = math.hypot(x, y)
        near = 1.0 - smoothstep(12.0, 24.0, dist)
        n = int(card_density * near * 2.4 + R.random() * near)
        fringe = R.random() < 0.28 * (1.0 - near) * (1.0 - smoothstep(40.0, 65.0, dist))
        if fringe: n = 1
        for c in range(n):
            # an angle round the profile: -1 (foot, one side) .. 0 (top) .. 1 (foot, other side), weighted to the upper
            # half; the mass shows below, so the cards keep to the upper face and the top (the fringe to the top only)
            th = R.uniform(-0.75, 0.75) if not fringe else R.uniform(-0.3, 0.3)
            ang = th * math.pi * 0.62
            outward = (Vector((nx, ny, 0)) * math.sin(ang) + Vector((0, 0, 1)) * math.cos(ang)).normalized()
            px = x + nx * math.sin(ang) * ww * 0.5 + dx * R.uniform(-cstep, cstep) * 0.5
            py = y + ny * math.sin(ang) * ww * 0.5 + dy * R.uniform(-cstep, cstep) * 0.5
            pz = gz0 + hh * (0.55 + 0.45 * math.cos(ang) * 1.05) + R.gauss(0, 0.04)
            sz = card_size * 1.15 * R.uniform(0.75, 1.25) * (1.0 + 0.6 * smoothstep(15, 60, dist))
            surf_up = outward.cross(tang).normalized()
            if surf_up.z < 0: surf_up = -surf_up
            roll = R.uniform(-1.2, 1.2)
            right = (tang * math.cos(roll) + surf_up * math.sin(roll)) * sz
            up = (surf_up * math.cos(roll) - tang * math.sin(roll)) * sz * 0.9 + outward * sz * R.uniform(0.15, 0.5)
            base = Vector((px, py, pz)) + outward * R.uniform(0.0, 0.15) - up * 0.45
            card(mb, base, right, up, R.choice(QUAD), 0.12, 0.45)
        if R.random() < 0.08 * card_density and dist < 26:
            sz = R.uniform(0.6, 1.0)
            card(mb, (x, y, gz0 + hh * 0.85), Vector((dx, dy, 0)) * sz * 0.9, Vector((R.gauss(0, 0.15), R.gauss(0, 0.15), sz)), R.choice(QUAD), 0.3, 0.8)
    sprays = mb.build(name + "Sprays", M_HAW)
    if sprays is not None:
        set_card_normals(sprays, lambda p: (Vector((0, 0, 0.7)) + (Vector((p.x, p.y, 0)) - Vector(_closest(poly, p.x, p.y))).normalized()).normalized())
    return core, sprays

def _closest(poly, px, py):
    best = (1e9, (px, py, 0))
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L2))
        qx, qy = x0 + t * dx, y0 + t * dy; d = math.hypot(px - qx, py - qy)
        if d < best[0]: best = (d, (qx, qy, 0))
    return best[1]

print("hedges ...", flush=True)
build_hedge("HedgeA", HEDGE_A, 11, h0=1.5, w0=1.25, gaps=GAPS_A, card_density=1.0)
build_hedge("HedgeB", HEDGE_B, 12, h0=1.7, w0=1.3, gaps=GAPS_B, card_density=0.85)
build_hedge("HedgeC", HEDGE_C, 13, h0=1.9, w0=1.6, step=2.0, card_density=0.35, card_size=1.3, ring=8)
build_hedge("HedgeD", HEDGE_D, 14, h0=1.8, w0=1.5, gaps=GAPS_D, step=2.0, card_density=0.35, card_size=1.3, ring=8)
build_hedge("HedgeE", HEDGE_E, 15, h0=2.0, w0=1.6, step=3.0, card_density=0.2, card_size=1.8, ring=8)
build_hedge("HedgeF", HEDGE_F, 16, h0=2.0, w0=1.6, step=3.0, card_density=0.2, card_size=1.8, ring=8)

# ----------------------------------------------------------------------------- trees
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

print("trees ...", flush=True)
OAK = tree("OakStile", -9.6, 7.0, 15.5, 7.5, "oak", 31, M_OAKBARK, M_OAKL, nlimbs=7, cards_per_tip=1, card_size=1.9, fill=190)
ASH = tree("AshRooks", 16.2, 10.0, 17.0, 5.5, "ash", 32, M_ASHBARK, M_TWIG, nlimbs=6, cards_per_tip=1, card_size=1.8, dense=1.0, fill=60)
MAPLE = tree("MapleB", 9.9, -5.0, 8.5, 3.6, "maple", 33, M_OAKBARK, M_MAPLE, nlimbs=5, cards_per_tip=1, card_size=1.4, fill=80)
# far trees: cards only (an opaque crown mass reads as a smooth ball against the sky), but few and large: ~28 cards at
# ~1.8x the old size, none at the branch tips (bare ashes keep a few twig cards)
FAR = dict(nlimbs=5, detail=0.6, cards_per_tip=0)
tree("OakField", -20.0, 43.0, 14.0, 7.0, "oak", 34, M_OAKBARK, M_OAKL, card_size=3.6, fill=34, **dict(FAR, nlimbs=6))
tree("MapleC", -40.8, -18.0, 12.0, 5.0, "maple", 35, M_OAKBARK, M_MAPLE, card_size=3.9, fill=34, **FAR)
tree("OakD", -16.0, -47.2, 13.0, 6.0, "oak", 36, M_OAKBARK, M_OAKL, card_size=3.6, fill=34, **FAR)
tree("AshD", 24.0, -44.3, 14.0, 4.5, "ash", 37, M_ASHBARK, M_TWIG, nlimbs=5, detail=0.6, cards_per_tip=1, card_size=2.2, fill=40)
tree("OakE", 52.0, 30.0, 13.0, 6.0, "oak", 38, M_OAKBARK, M_OAKL, card_size=4.0, fill=34, **FAR)
tree("MapleA", 38.0, 14.2, 11.0, 4.6, "maple", 39, M_OAKBARK, M_MAPLE, card_size=4.0, fill=34, **FAR)
tree("OakF", -44.5, 30.0, 14.0, 6.0, "oak", 40, M_OAKBARK, M_OAKL, card_size=4.0, fill=34, **FAR)
# the park round the house: a cedar on the lawn, beeches and limes behind
def cedar(name, x, y, h, seed):
    R = random.Random(seed); z = gz(x, y)
    tube(name + "_t", [(x, y, z - 0.2), (x, y, z + h * 0.5), (x + 0.3, y, z + h * 0.92)], [0.75, 0.6, 0.25], M_OAKBARK, sides=7)
    mb = MB()
    for tier in range(5):
        tz = z + h * (0.28 + tier * 0.15); rad = (h * 0.55) * (1 - tier * 0.17)
        for k in range(10):
            a = 2 * math.pi * k / 10 + R.gauss(0, 0.2)
            d = Vector((math.cos(a), math.sin(a), 0))
            for j in range(2):
                c = Vector((x, y, tz)) + d * rad * (0.45 + 0.4 * j)
                right = Vector((-d.y, d.x, 0)) * rad * 0.55
                card(mb, c - d * rad * 0.2, right, d * rad * 0.5 + Vector((0, 0, 0.3)), (0.0, 0.0, 0.5, 0.5), 0.2, 0.6)
    o = mb.build(name + "_crown", M_CEDAR)
    if o: set_card_normals(o, lambda p: Vector((0, 0, 1)))
def cedar_atlas():
    cv = Canvas(256, 256); R = random.Random(9)
    for i in range(900):
        x, y = R.uniform(10, 246), R.uniform(10, 246)
        cv.ellipse(x, y, R.uniform(3, 7), R.uniform(2, 4), R.uniform(0, 3), (R.uniform(0.08, 0.14), R.uniform(0.14, 0.2), R.uniform(0.10, 0.14), 1.0))
    cv.a[..., 3] = np.where(cv.a[..., 3] > 0.5, 1.0, 0.0); cv.bleed(4)
    return K.np_image("A_Cedar", cv.a)
M_CEDAR = image_mat("M_CedarCards", cedar_atlas(), rough=0.7, alpha=True)
cedar("Cedar", 22.0, 84.0, 17.0, 41)
for i, (tx, ty, th, kind) in enumerate([(62, 96, 19, "elm"), (55, 103, 17, "oak"), (30, 100, 18, "ash"), (16, 92, 15, "oak"), (70, 80, 16, "oak"),
                                         (-5, 88, 16, "elm"), (-25, 75, 14, "oak"), (5, 70, 12, "oak")]):
    if math.hypot(tx, ty) > LAND_R - 6: continue
    bare = kind == "ash"
    tree(f"Park{i}", tx, ty, th, th * 0.42, kind, 50 + i, M_ASHBARK if kind != "oak" else M_OAKBARK, M_TWIG if bare else M_OAKL,
         nlimbs=5, detail=0.5, cards_per_tip=1 if bare else 0, card_size=2.8 if bare else 4.7, fill=40 if bare else 30)

# rooks' nests in the ash: rough twig balls in the upper forks
for (q, d, depth) in ASH[0]:
    pass


# ----------------------------------------------------------------------------- the stile (ahead-left) and the five-bar gate (right, behind)
def stile():
    a = math.atan2(HEDGE_A[4][1] - HEDGE_A[3][1], HEDGE_A[4][0] - HEDGE_A[3][0])   # along the hedge
    t = Vector((math.cos(a), math.sin(a), 0)); n = Vector((-t.y, t.x, 0))
    c = Vector((STILE.x, STILE.y, 0)); z = gz(c.x, c.y)
    def P(u, v, h): return c + t * u + n * v + Vector((0, 0, z + h))
    rot = (0, 0, a)
    for k, u in enumerate((-0.62, 0.62)):
        box(f"StilePost{k}", (0.13, 0.12, 1.55), tuple(P(u, 0, 1.55 / 2 - 0.35)), M_STILE, bevel=0.012, rot=(0.02 * (k - 0.5), 0.015, a))
    box("StileTopRail", (1.5, 0.08, 0.1), tuple(P(0.0, 0.0, 1.02)), M_STILE, bevel=0.012, rot=(0, 0.02, a))
    box("StileMidRail", (1.42, 0.07, 0.09), tuple(P(0.0, 0.0, 0.55)), M_STILE, bevel=0.01, rot=(0, -0.03, a))
    for k, v in enumerate((-0.42, 0.42)):        # a step plank either side on two stubs
        for u in (-0.42, 0.42):
            box(f"StileStub{k}{u}", (0.09, 0.09, 0.6), tuple(P(u, v, 0.08)), M_STILE, bevel=0.008, rot=(0.0, 0.0, a))
        box(f"StileStep{k}", (1.05, 0.26, 0.055), tuple(P(0.0, v, 0.38)), M_STILE, bevel=0.01, rot=(0.03 * (k - 0.5), 0, a))
    anchor("path.stile", tuple(P(0, 0, 0)))
    return P(0, 0, 0)
STILE_P = stile()

def five_bar_gate():
    c = Vector((GATE.x, GATE.y, 0)); z = gz(c.x, c.y)
    t = Vector((0.0, 1.0, 0)); W = 3.0
    hp = c - t * (W / 2 + 0.12); sp = c + t * (W / 2 + 0.1)
    box("GateHangPost", (0.22, 0.22, 2.0), (hp.x, hp.y, gz(hp.x, hp.y) + 0.55), M_GATE, bevel=0.015)
    box("GateShutPost", (0.17, 0.17, 1.75), (sp.x, sp.y, gz(sp.x, sp.y) + 0.45), M_GATE, bevel=0.012)
    g0 = hp + t * 0.14
    zz = z + 0.25
    box("GateHeel", (0.09, 0.11, 1.18), tuple(g0 + Vector((0, 0, zz + 0.6))), M_GATE, bevel=0.01)
    box("GateHead", (0.08, 0.09, 1.1), tuple(g0 + t * (W - 0.2) + Vector((0, 0, zz + 0.58))), M_GATE, bevel=0.01)
    for k, hb in enumerate((0.08, 0.32, 0.55, 0.80, 1.10)):
        box(f"GateBar{k}", (0.05, W - 0.15, 0.085 if k < 4 else 0.12), tuple(g0 + t * (W / 2 - 0.12) + Vector((0, 0, zz + hb))), M_GATE, bevel=0.008)
    d0 = g0 + t * 0.05 + Vector((0, 0, zz + 0.08)); d1 = g0 + t * (W - 0.3) + Vector((0, 0, zz + 1.08))
    mid = (d0 + d1) / 2; L = (d1 - d0).length; ang = math.atan2(d1.z - d0.z, (d1 - d0).y)
    box("GateBrace", (0.045, L, 0.08), tuple(mid + Vector((0.05, 0, 0))), M_GATE, bevel=0.006, rot=(ang, 0, 0))
    anchor("path.gate", (c.x, c.y, z))
five_bar_gate()

# ----------------------------------------------------------------------------- Netherfield House
def house():
    """A plain, handsome Georgian house of the 1760s: a stuccoed centre block of seven bays and three storeys with a
    slightly projecting, pedimented centre of three bays and a Tuscan porch, a hipped slate roof with four chimney
    stacks, and lower two-storey wings set back each side. Sashes with white glazing bars, dark glass."""
    yaw = HOUSE_YAW
    F = K.Frame((HOUSE.x, HOUSE.y), yaw, z=gz(HOUSE.x, HOUSE.y) - 0.3)
    W, D, Hh = 21.0, 13.0, 13.2        # centre block: width, depth, height to the parapet top
    F.box("HouseMain", (W, D, Hh), (0, D / 2, Hh / 2), M_STUCCO)
    F.box("HousePlinth", (W + 0.2, D + 0.2, 1.1), (0, D / 2, 0.55), M_CHURCH)
    F.box("HouseCentre", (7.6, 0.6, Hh), (0, -0.3 + 0.0, Hh / 2), M_STUCCO)
    F.box("HouseCornice", (W + 0.5, D + 0.5, 0.35), (0, D / 2, Hh - 1.0), M_HOUSEPAINT)
    F.box("HouseCorniceC", (8.1, 0.7, 0.35), (0, -0.3, Hh - 1.0), M_HOUSEPAINT)
    # pediment over the centre
    p0 = F.p(-3.9, -0.62, Hh - 0.82); p1 = F.p(3.9, -0.62, Hh - 0.82); p2 = F.p(0, -0.62, Hh + 1.5)
    b0 = F.p(-3.9, 0.3, Hh - 0.82); b1 = F.p(3.9, 0.3, Hh - 0.82); b2 = F.p(0, 0.3, Hh + 1.5)
    mesh_from("HousePediment", [p0, p1, p2, b0, b1, b2], [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], M_STUCCO)
    # hipped roof
    rz = Hh - 0.8; rh = 4.0
    v = [F.p(-W / 2 + 0.3, 0.3, rz), F.p(W / 2 - 0.3, 0.3, rz), F.p(W / 2 - 0.3, D - 0.3, rz), F.p(-W / 2 + 0.3, D - 0.3, rz),
         F.p(-W / 2 + 6.5, D / 2, rz + rh), F.p(W / 2 - 6.5, D / 2, rz + rh)]
    mesh_from("HouseRoof", v, [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)], M_SLATE)
    for k, (cx, cy) in enumerate(((-6.0, 2.6), (6.0, 2.6), (-6.0, 10.4), (6.0, 10.4))):
        F.box(f"HouseChimney{k}", (1.6, 0.8, 3.4), (cx, cy, rz + 3.0), M_STUCCO)
        F.box(f"HouseChimneyCap{k}", (1.8, 1.0, 0.2), (cx, cy, rz + 4.75), M_HOUSEPAINT)
        for j in range(3):
            F.cyl(f"HousePot{k}{j}", 0.13, 0.5, (cx - 0.5 + j * 0.5, cy, rz + 5.05), M_CHURCH, verts=6)
    # wings
    for sgn in (-1, 1):
        wx = sgn * (W / 2 + 4.0)
        F.box(f"HouseWing{sgn}", (8.0, 10.0, 8.2), (wx, D / 2 + 1.2, 4.1), M_STUCCO)
        F.box(f"HouseWingCornice{sgn}", (8.4, 10.4, 0.3), (wx, D / 2 + 1.2, 7.7), M_HOUSEPAINT)
        wv = [F.p(wx - 4.0, 1.4, 8.0), F.p(wx + 4.0, 1.4, 8.0), F.p(wx + 4.0, D + 1.0, 8.0), F.p(wx - 4.0, D + 1.0, 8.0),
              F.p(wx - 1.5, D / 2 + 1.2, 10.4), F.p(wx + 1.5, D / 2 + 1.2, 10.4)]
        mesh_from(f"HouseWingRoof{sgn}", wv, [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)], M_SLATE)
        for col_ in range(3):
            for row in range(2):
                xw = wx - 2.5 + col_ * 2.5; zw = 1.7 + row * 3.4
                F.box(f"HouseWWf{sgn}{col_}{row}", (1.25, 0.06, 2.0), (xw, 2.19, zw), M_HOUSEPAINT)
                F.box(f"HouseWWg{sgn}{col_}{row}", (1.05, 0.06, 1.8), (xw, 2.17, zw), M_HOUSEWIN)
    # the windows: seven bays, three storeys (tall piano nobile, square attic)
    for bay in range(7):
        xw = -9.0 + bay * 3.0
        yf = -0.62 if abs(xw) < 4 else -0.02
        for row, (zw, hw) in enumerate(((2.2, 2.2), (6.0, 2.7), (10.0, 1.4))):
            F.box(f"HouseWf{bay}{row}", (1.35, 0.06, hw + 0.2), (xw, yf, zw), M_HOUSEPAINT)
            F.box(f"HouseWg{bay}{row}", (1.12, 0.06, hw), (xw, yf - 0.02, zw), M_HOUSEWIN)
            F.box(f"HouseWbar{bay}{row}", (0.05, 0.07, hw), (xw, yf - 0.03, zw), M_HOUSEPAINT)
            F.box(f"HouseWbarh{bay}{row}", (1.12, 0.07, 0.05), (xw, yf - 0.03, zw), M_HOUSEPAINT)
    # porch: four Tuscan columns and an entablature, steps
    for k in range(4):
        F.cyl(f"HousePorchCol{k}", 0.28, 3.6, (-2.4 + k * 1.6, -2.8, 2.2), M_HOUSEPAINT, verts=10)
    F.box("HousePorchTop", (5.6, 2.8, 0.6), (0, -1.9, 4.3), M_HOUSEPAINT)
    F.box("HouseDoor", (1.5, 0.08, 2.9), (0, -0.66, 1.85), M_HOUSEWIN)
    for k in range(3): F.box(f"HouseStep{k}", (6.0 - k * 0.3, 1.0 + 3.0 - k * 1.0, 0.18), (0, -2.0 - 0.5 * (2 - k), 0.35 + k * 0.18), M_CHURCH)
    anchor("netherfield.house", tuple(F.p(0, -4, 0.3)))
house()

# the church tower of Meryton far behind (a backdrop silhouette on the horizon: drawn on the sky dome)

# ----------------------------------------------------------------------------- the sky dome (overcast, washed after rain)
def sky_mat(name="M_SkyDome"):
    """A high, even stratocumulus deck: soft grey cells with paler joins, brighter and warmer low in the east-south-east
    where the sun is behind the cloud, darker and bluer overhead; a pale washed band at the horizon; distant blue-grey
    tree belts and low hills along the horizon (the land beyond the dome) and Meryton church tower behind."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-2200, 0), operation='NORMALIZE'); nt.links.new(co, nv.inputs[0]); d = nv.outputs[0]
    s = sep_xyz(nt, d, (-2000, 0)); el = s.outputs["Z"]
    base = ramp(nt, [(0.0, c4((0.36, 0.37, 0.36))), (0.09, c4((0.64, 0.66, 0.67))), (0.16, c4((0.60, 0.62, 0.64))), (0.45, c4((0.47, 0.50, 0.54))), (1.0, c4((0.36, 0.39, 0.44)))], (-1500, 400))
    nt.links.new(maprange(nt, el, -0.1, 1.0, 0, 1, (-1700, 400)), base.inputs["Fac"])
    col = base.outputs["Color"]
    # the veiled sun: a broad, brighter, slightly warm region, no disc
    sd = node(nt, "ShaderNodeVectorMath", (-1700, 800), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(SUN_DIR); nt.links.new(d, sd.inputs[0])
    glow = math_(nt, 'POWER', maprange(nt, sd.outputs["Value"], 0.3, 1.0, 0, 1, (-1500, 800)), 3.0, (-1350, 800))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', glow, 0.42, (-1200, 850)), col, (0.95, 0.88, 0.76, 1), (-1000, 400))
    # the cloud deck in perspective
    zk = math_(nt, 'ADD', math_(nt, 'MAXIMUM', el, 0.0, (-1800, -200)), 0.06, (-1650, -200))
    px = math_(nt, 'DIVIDE', s.outputs["X"], zk, (-1500, -150)); py = math_(nt, 'DIVIDE', s.outputs["Y"], zk, (-1500, -300))
    cv = node(nt, "ShaderNodeCombineXYZ", (-1350, -200)); nt.links.new(px, cv.inputs["X"]); nt.links.new(py, cv.inputs["Y"])
    mp = node(nt, "ShaderNodeMapping", (-1200, -200)); mp.inputs["Scale"].default_value = (0.55, 0.85, 1); mp.inputs["Location"].default_value = (3.3, 1.7, 0.2)
    nt.links.new(cv.outputs[0], mp.inputs["Vector"])
    cells = voronoi_(nt, mp.outputs["Vector"], 1.6, 'F1', (-1000, -100))
    wob = noise_(nt, mp.outputs["Vector"], 2.5, 6, 0.6, 0.5, (-1000, -350))
    big = noise_(nt, mp.outputs["Vector"], 0.35, 3, 0.5, loc=(-1000, -600))
    lump = math_(nt, 'ADD', math_(nt, 'MULTIPLY', cells.outputs["Distance"], 0.9, (-800, -100)), math_(nt, 'MULTIPLY', wob.outputs["Fac"], 0.55, (-800, -350)), (-650, -200))
    lump = math_(nt, 'ADD', lump, math_(nt, 'MULTIPLY', big.outputs["Fac"], 0.5, (-800, -600)), (-550, -300))
    joins = maprange(nt, lump, 0.7, 1.15, 0, 1, (-400, -300), 'SMOOTHSTEP')
    # cloud bodies darker grey, joins paler (light through thinner cloud); fade into the haze towards the horizon
    hz = maprange(nt, el, 0.02, 0.22, 0, 1, (-400, -550))
    cloudcol = mix_rgb(nt, 'MIX', joins, (0.40, 0.42, 0.45, 1), (0.66, 0.67, 0.68, 1), (-200, -300))
    cloudcol = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', glow, 0.35, (-300, -700)), cloudcol, (0.85, 0.78, 0.66, 1), (-50, -400))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', hz, 0.75, (-200, -550)), col, cloudcol, (100, 400))
    # distant land along the horizon: tree belts and low hills, hazy blue-grey
    az = math_(nt, 'ARCTAN2', s.outputs["X"], s.outputs["Y"], (-1800, -1200))
    azv = node(nt, "ShaderNodeCombineXYZ", (-1650, -1200)); nt.links.new(math_(nt, 'COSINE', az, None, (-1700, -1300)), azv.inputs["X"]); nt.links.new(math_(nt, 'SINE', az, None, (-1700, -1400)), azv.inputs["Y"])
    hn = noise_(nt, azv.outputs[0], 2.2, 3, 0.5, loc=(-1500, -1200)); tn = noise_(nt, azv.outputs[0], 24.0, 4, 0.7, loc=(-1500, -1450))
    hill = math_(nt, 'ADD', math_(nt, 'MULTIPLY', hn.outputs["Fac"], 0.035, (-1300, -1200)), math_(nt, 'MULTIPLY', maprange(nt, tn.outputs["Fac"], 0.35, 0.65, 0, 1, (-1300, -1450)), 0.016, (-1150, -1450)), (-1000, -1300))
    hill = math_(nt, 'SUBTRACT', hill, 0.005, (-900, -1300))
    # Meryton church: a square tower with corner pinnacles, behind the reader, a little to the left
    cd = node(nt, "ShaderNodeVectorMath", (-1700, -1700), operation='DOT_PRODUCT'); cd.inputs[1].default_value = tuple(CHURCH_DIR); nt.links.new(d, cd.inputs[0])
    cx_ = math_(nt, 'ARCCOSINE', math_(nt, 'MINIMUM', cd.outputs["Value"], 1.0, (-1550, -1700)), None, (-1400, -1700))
    tower = math_(nt, 'MULTIPLY', math_(nt, 'LESS_THAN', cx_, 0.0075, (-1250, -1700)), 0.036, (-1100, -1700))
    pinn = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', math_(nt, 'GREATER_THAN', cx_, 0.0052, (-1250, -1850)), math_(nt, 'LESS_THAN', cx_, 0.0075, (-1250, -1950)), (-1100, -1900)), 0.043, (-950, -1900))
    hill = math_(nt, 'MAXIMUM', hill, math_(nt, 'MAXIMUM', tower, pinn, (-850, -1800)), (-750, -1400))
    land = maprange(nt, math_(nt, 'SUBTRACT', hill, el, (-650, -1300)), 0.0, 0.0015, 0, 1, (-500, -1300))
    landcol = mix_rgb(nt, 'MIX', maprange(nt, el, 0.0, 0.03, 1, 0, (-500, -1500)), (0.42, 0.45, 0.47, 1), (0.30, 0.33, 0.33, 1), (-300, -1400))
    belowc = mix_rgb(nt, 'MIX', maprange(nt, el, 0.0, -0.08, 0, 1, (-300, -1650)), landcol, (0.16, 0.19, 0.13, 1), (-100, -1550))
    col = mix_rgb(nt, 'MIX', land, col, belowc, (300, 400))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 0.8; b.inputs["Roughness"].default_value = 1.0
    return m
M_SKY = sky_mat()

def sky_dome(name="SkyDome", radius=SKY_R, seg=48, rings=16, el_min=-10.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rows = []
    for j in range(rings + 1):
        e = math.radians(el_min + (90.0 - el_min) * (j / rings) ** 1.0)
        rows.append([bm.verts.new((radius * math.cos(e) * math.sin(2 * math.pi * i / seg), radius * math.cos(e) * math.cos(2 * math.pi * i / seg), radius * math.sin(e))) for i in range(seg)])
    for j in range(rings):
        for i in range(seg):
            i2 = (i + 1) % seg
            f = bm.faces.new((rows[j][i], rows[j + 1][i], rows[j + 1][i2], rows[j][i2]))
            for l, (uu, vv) in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                l[uvl].uv = (uu / seg, vv / rings)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_SKY)
    o.visible_diffuse = False; o.visible_glossy = True; o.visible_shadow = False; o.visible_transmission = False
    return link(o)
SKY = sky_dome()

# ----------------------------------------------------------------------------- light (Blender preview) and the world
light_obj("light.sun", 'SUN', 1.6, (1.0, 0.95, 0.88), tuple(SUN_DIR * 40), direction=-SUN_DIR, angle=math.radians(28))
sky_l = light_obj("light.sky", 'SUN', 0.35, (0.80, 0.86, 0.95), (0, 0, 30), direction=(0.15, -0.1, -1.0), angle=math.radians(90))
sky_l.data.use_shadow = False
world = bpy.data.worlds.new("OvercastMorning"); scene.world = world; world.use_nodes = True
wnt = world.node_tree; bg = wnt.nodes["Background"]
wtc = wnt.nodes.new("ShaderNodeTexCoord"); wsep = wnt.nodes.new("ShaderNodeSeparateXYZ"); wnt.links.new(wtc.outputs["Generated"], wsep.inputs["Vector"])
wmr = wnt.nodes.new("ShaderNodeMapRange"); wmr.inputs["From Min"].default_value = -0.1; wmr.inputs["From Max"].default_value = 1.0
wnt.links.new(wsep.outputs["Z"], wmr.inputs["Value"])
wr = ramp(wnt, [(0.0, (0.16, 0.17, 0.13, 1)), (0.09, (0.62, 0.64, 0.66, 1)), (0.4, (0.50, 0.53, 0.58, 1)), (1.0, (0.40, 0.43, 0.48, 1))])
wnt.links.new(wmr.outputs["Result"], wr.inputs["Fac"]); wnt.links.new(wr.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 2.3
# a thin morning haze (render only; Unity uses its exponential fog)
vol = wnt.nodes.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.0006; vol.inputs["Color"].default_value = (0.78, 0.80, 0.82, 1)
wnt.links.new(vol.outputs[0], wnt.nodes["World Output"].inputs["Volume"])

# ----------------------------------------------------------------------------- anchors, living-scene sources
READER = Vector((0.0, 0.0, 0.0))
LOOK = Vector((0.0, 1.0, 0.0))
anchor("reader.entrance", (0.0, 0.0, gz(0, 0)))
anchor("reader.look", (0.0, 1.0, gz(0, 0) + EYE))
anchor("scene.centre", tuple(STILE_P))
anchor("meryton.church", tuple(CHURCH_DIR * 110 + Vector((0, 0, 2))))
sound("wind-trees", "oak", tuple(OAK[1]))
sound("wind-trees", "ash", tuple(ASH[1]))
sound("birds", "rooks", tuple(ASH[1] + Vector((0, 0, 3))))
sound("birds", "hedge", (STILE.x + 3.5, STILE.y + 0.4, gz(STILE.x + 3.5, STILE.y) + 1.0))
sound("wind", "field", (-14.0, -6.0, 1.5))

# the reading page placeholder (render-only, never exported): 0.6 m ahead, 0.4 x 0.55 m at eye height
EZ = gz(0, 0) + EYE
page = box("PagePreview", (0.4, 0.004, 0.55), (0.0, 0.6, EZ - 0.05), plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9))

K.apply_transforms()
for o in K.COLL.objects:
    if o.type == 'MESH' and o.name not in ("SkyDome",):
        o.visible_shadow = bool(o.data.materials) and o.data.materials[0].name not in ("M_Puddle",)

# ----------------------------------------------------------------------------- cameras (reader eye 1.55 m)
E = Vector((0.0, 0.0, EZ))
def yawed(deg, dist=8.0, dz=-0.6):
    a = math.radians(deg); return tuple(E + Vector((math.sin(a), math.cos(a), 0)) * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(E), yawed(0, 10, -0.9), lens=17),
    camera("Cam_Page", tuple(E), yawed(0, 10, -0.9), lens=17),
    camera("Cam_Left", tuple(E), yawed(-75, 10, -0.6), lens=17),
    camera("Cam_Right", tuple(E), yawed(80, 10, -0.6), lens=17),
    camera("Cam_Behind", tuple(E), yawed(180, 10, -0.4), lens=17),
    camera("Cam_Down", tuple(E), (-0.8, 2.0, gz(-0.8, 2.0)), lens=17),
    camera("Cam_Stile", tuple(E + Vector((-1.4, 3.0, 0))), tuple(STILE_P + Vector((0, 0, 0.6))), lens=24),
    camera("Cam_House", tuple(E), (HOUSE.x, HOUSE.y, gz(HOUSE.x, HOUSE.y) + 6), lens=50),
    camera("Cam_Ash", tuple(E), (16.2, 10.0, gz(16.2, 10.0) + 9.0), lens=28),
]
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "fields_to_netherfield_source.blend"))
K.print_budget()

for _n in os.environ.get("FIELDS_HIDE", "").split(","):
    if _n and _n in bpy.data.objects: bpy.data.objects[_n].hide_render = True
if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=1.5, exposure={"Cam_House": 1.0, "Cam_Ash": 1.0}, captures_dir=ARGS.captures)

if ARGS.bake or ARGS.export:
    T_ = ARGS.tex
    K.bake_and_export(
        "fields_to_netherfield.gltf", cams, page=page,
        keep_names={"M_GrassCards": "veg.grass.field", "M_HedgeSprays": "veg.shrub.hedges", "M_OakSprays": "veg.crown.oak",
                    "M_BareTwigs": "veg.crown.bare", "M_MapleSprays": "veg.crown.maple", "M_CedarCards": "veg.crown.cedar",
                    "M_Puddle": "water.puddle.path", "M_SkyDome": "SkyDome", "M_FarLand": "far.land", "M_GroundNear": "GroundNear"},
        keep_uv={"M_GroundNear", "M_FarLand", "M_SkyDome"},
        size_for={"M_GroundNear": (4096, 2048, 2048), "M_FarLand": (1024, 256, 512), "M_SkyDome": (2048,),
                  "M_HedgeMass": (1024, 256, 512), "M_OakBark": (1024, 256, 512), "M_AshBark": (512, 128, 512),
                  "M_StileOak": (512, 256, 512), "M_GateOak": (512, 128, 256), "M_HouseStucco": (1024, 128, 256),
                  "M_HouseSlate": (256, 64, 128), "M_Puddle": (128, 64, 128), "M_HouseWindows": (32, 32), "M_HousePaint": (64, 32),
                  "M_FarStone": (128, 32)},
        default_size=(256, 64, 128))
print("DONE")
