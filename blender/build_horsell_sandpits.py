"""
Fable: the sand pits on Horsell Common at dawn (The War of the Worlds, book I, chapters 2-3).

"An enormous hole had been made by the impact of the projectile, and the sand and gravel had been flung violently in
every direction over the heath, forming heaps visible a mile and a half away. The heather was on fire eastward, and
a thin blue smoke rose against the dawn."
"The Thing itself lay almost entirely buried in sand, amidst the scattered splinters of a fir tree it had shivered to
fragments in its descent. The uncovered part had the appearance of a huge cylinder, caked over and its outline
softened by a thick scaly dun-coloured incrustation. It had a diameter of about thirty yards."
"The early morning was wonderfully still, and the sun, just clearing the pine trees towards Weybridge, was already
warm."

The reader stands on a sandy track on a low heathery knoll at the south-east lip of the pit, in August, a few minutes
after sunrise. Ahead (north) the heath falls gently to a misty hollow with bracken, and Scots pines stand in loose
groups; on the left the ground rises to the pit's rim, heaped with flung sand and gravel over buried heather, and in
the pit lies the cylinder, 27 m across, its end and the crown of its body showing above the sand, crusted with a
dun, ashy scale that is flaking off round the edge of the end. Splinters of the fir tree it struck lie round the rim
with the broken stump. On the right the sun is just clearing the pines towards Weybridge; further east a strip of
heather smoulders and a thin blue thread of smoke rises against the dawn. Behind the reader the track runs back
across the common past an old pine and a few gorse bushes. No people (Ogilvy, the crowd and the carts are left out).

Everything is procedural (no downloaded models, textures or HDRIs). Foliage is alpha-clipped cards painted in numpy
(pine-needle sprays, ling heather in bloom, heath grass, gorse, bracken) with soft custom normals, kept lean for the
Quest's tile GPU (alpha-tested overdraw is the cost): heather and grass cards only within ~10 m of the reader (and
nothing tall in the first metres ahead), rising out of an opaque lumpy heather canopy that carries the heath out to
36 m; mid and far pine crowns are fewer, much larger, flatter needle cards; gorse bushes have opaque cores; the ground and sky
are painted in numpy into their own UV layouts (the ground in log-polar UVs, texel density highest at the reader's
feet); the cylinder, bark and splintered wood are node materials baked to textures. Static meshes merge by material;
glTF export with lights for Unity (helpers in wotw_kit.py).

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet on the track (ground, z=0), facing north (+Y)
  anchor.reader.look      eye height (1.55 m), 2 m ahead along the reading direction
  anchor.scene.centre     the pit's near rim, ahead-left
  anchor.pit.cylinder (the centre of the cylinder's end), anchor.heath.smoke (the smouldering heather, far east)
  light.sun (SUN, low dawn sun from the east), light.sky (SUN, cool fill, no shadow)
  SkyDome (unlit backdrop), far.land (ground beyond 75 m), far.treeline (distant pines): backdrop
  Living scenes (docs/LIVING_SCENES.md), vertex colour R = sway weight (0 at roots/trunk, 1 at tips):
    veg.crown.pines (the pine crowns), veg.shrub.heather, veg.shrub.gorse, veg.grass.heath, veg.leaves.bracken
    sound.birds.0 / sound.birds.1 (in the pines ahead and behind), sound.wind-trees.0 (the pine group on the right)
  MESH_HeathMound (the opaque heather canopy), MESH_GorseMound (gorse cores): static, opaque
  MESH_Mist: two soft alpha-blended mist sheets (in the pit and the hollow); no shadows, not lightmapped.

Axes: metres, Blender +Z up, +Y north, +X east. Reader at the origin.

Run headless:
  blender -b -P blender/build_horsell_sandpits.py -- --out out/horsell-sandpits --render --quick --res 800
  blender -b -P blender/build_horsell_sandpits.py -- --out out/horsell-sandpits --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wotw_kit as K
from wotw_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, bump_from, c4, obj_xyz, noise_tex, white,
                      combine, tone_ramp, wood, metal, plain, tube, mesh_from, anchor, marker, camera, TWO_PI,
                      paint_stroke, paint_dot, bleed_alpha, CardMesh, fbm, sstep)

args, scene = K.begin("HorsellSandpits", "out/horsell-sandpits")
OUT = K.OUT
rnd = random.Random(1894)

# ----------------------------------------------------------------------------- the place (metres)
EYE = 1.55
LOOK_AZ = 0.0                                   # compass degrees: north, a little east
SUN_AZ, SUN_EL = 92.0, 9.0                       # just risen, over the pines towards Weybridge
def az_dir(az): a = math.radians(az); return Vector((math.sin(a), math.cos(a), 0.0))
SUN_DIR = (az_dir(SUN_AZ) * math.cos(math.radians(SUN_EL)) + Vector((0, 0, math.sin(math.radians(SUN_EL))))).normalized()
CR = np.array([-28.0, 33.0])                     # the pit's centre (ahead-left, 43 m)
RC = 25.0                                        # pit radius at the lip
PIT_D = 6.0                                      # depth
U_R = Vector((-CR[0], -CR[1], 0)).normalized()   # from the pit toward the reader
RCYL = 13.5                                      # "a diameter of about thirty yards"
CYL_AX = (Matrix.Rotation(math.radians(36), 3, 'Z') @ -U_R).normalized()      # the body runs away from the reader, turned
CYL_TILT = math.radians(9.0)
CYL_A = Vector((CYL_AX.x * math.cos(CYL_TILT), CYL_AX.y * math.cos(CYL_TILT), -math.sin(CYL_TILT)))
CYL_E = Vector((CR[0], CR[1], 0)) + U_R * 5.0 + Vector((0, 0, -4.2))           # the centre of the exposed end
CYL_L = 42.0
NEAR_R, TERRAIN_R, SKY_R = 75.0, 140.0, 146.0

# tracks: polylines (x, y) with half widths
TRACKS = [
    ([(1.5, -80), (0.8, -30), (0.3, -10), (0.0, 0.0), (-2.5, 6.0), (-7.0, 10.5), (-11.5, 12.0)], 0.55),
    ([(0.2, 0.5), (3.0, 12), (7.5, 30), (9.0, 50), (12.0, 80)], 0.32),
    ([(-80, -20), (-45, -6), (-30, 2), (-16, 5.5), (-9.0, 9.0)], 0.4),
]

# ----------------------------------------------------------------------------- terrain, masks (numpy: also used for placement)
def seg_dist(x, y, pts):
    d = np.full(np.broadcast(x, y).shape, 1e9, np.float32)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
        t = np.clip(((x - ax) * dx + (y - ay) * dy) / L2, 0, 1)
        d = np.minimum(d, np.hypot(x - (ax + t * dx), y - (ay + t * dy)))
    return d

def track_mask(x, y):
    m = 0
    for pts, hw in TRACKS:
        d = seg_dist(x, y, pts)
        wob = hw * (1 + 0.35 * (fbm(x * 0.3, y * 0.3, 2, seed=71) - 0.5))
        m = np.maximum(m, sstep(wob + 0.25, wob - 0.1, d))
    return m

def cyl_local(x, y):
    """(t along the axis from the end, w horizontal offset from the axis line) of a ground point."""
    ax, ay = CYL_AX.x, CYL_AX.y
    dx, dy = x - CYL_E.x, y - CYL_E.y
    t = (dx * ax + dy * ay) / math.cos(CYL_TILT)
    w = -dx * ay + dy * ax
    return t, w

def ground_z(x, y):
    x = np.asarray(x, np.float32); y = np.asarray(y, np.float32)
    r = np.hypot(x, y)
    base = 2.6 * (fbm(x / 70 + 3.1, y / 70 + 7.3, 4, seed=1) - 0.5) + 0.5 * (fbm(x / 14, y / 14, 3, seed=2) - 0.5)
    base += -0.022 * y + 0.010 * x
    knoll = 0.55 * np.exp(-(r / 8.0) ** 2)
    hollow = -1.6 * np.exp(-(((x - 6) / 18) ** 2 + ((y - 52) / 14) ** 2))
    d = np.hypot(x - CR[0], y - CR[1])
    ang = np.arctan2(y - CR[1], x - CR[0])
    bowl = -PIT_D * np.clip(1 - (d / RC) ** 2, 0, 1) ** 1.25
    lip = (1.5 + 0.9 * (fbm(np.cos(ang) * 3 + 5, np.sin(ang) * 3, 3, seed=4) - 0.5)) * np.exp(-((d - RC * 1.02) / 4.2) ** 2)
    eject = 0.9 * np.exp(-np.clip(d - RC, 0, None) / 10.0) * (d > RC * 0.95) * (0.5 + fbm(x / 6, y / 6, 3, seed=5))
    # sand heaped against the cylinder's flanks and in front of its end
    t, w = cyl_local(x, y)
    inside = sstep(RC + 4, RC - 2, d)
    flank = 1.0 * np.exp(-((np.abs(w) - RCYL * 0.98) / 3.2) ** 2) * sstep(-4, 3, t) * sstep(CYL_L, CYL_L - 8, t)
    front = 1.0 * np.exp(-((t + 2.0) / 3.0) ** 2) * (np.abs(w) < RCYL + 2)
    z = base + knoll + hollow + bowl + lip + eject + (flank + front) * inside
    return z
Z0 = float(ground_z(0.0, 0.0))
def gz(x, y): return ground_z(x, y) - Z0

def heather_density(x, y):
    """Ling and bell heather cover: patchy, none on the tracks, buried or burnt round the pit."""
    x = np.asarray(x, np.float32); y = np.asarray(y, np.float32)
    patch = sstep(0.22, 0.50, fbm(x / 9 + 11, y / 9 + 3, 4, seed=8))
    d = np.hypot(x - CR[0], y - CR[1])
    buried = sstep(RC + 9, RC + 2, d) * sstep(0.25, 0.65, fbm(x / 3.5, y / 3.5, 3, seed=9) + 0.25 * sstep(RC + 13, RC + 2, d))
    pit = sstep(RC + 2.5, RC + 1.0, d)
    hol = sstep(16, 8, np.hypot((x - 6) / 1.3, y - 52))                    # bracken and grass in the damp hollow
    return np.clip(patch * 0.85 + 0.15, 0, 1) * (1 - track_mask(x, y)) * (1 - buried) * (1 - pit) * (1 - 0.8 * hol)

def sand_cover(x, y):
    """Fresh flung sand: the pit, and splashes over the heath round it."""
    x = np.asarray(x, np.float32); y = np.asarray(y, np.float32)
    d = np.hypot(x - CR[0], y - CR[1])
    ang = np.arctan2(y - CR[1], x - CR[0])
    rays = fbm(np.cos(ang) * 6 + 2, np.sin(ang) * 6 + 2, 3, seed=12)
    reach = RC + 3 + 9 * rays
    return np.maximum(sstep(RC + 2, RC - 1, d), sstep(reach, RC, d) * sstep(0.3, 0.6, fbm(x / 2.5, y / 2.5, 3, seed=13) + 0.35 * sstep(reach, RC + 2, d)))

# ----------------------------------------------------------------------------- the ground texture (numpy, log-polar UVs)
R0 = 3.0
def v_of_r(r): return np.log1p(r / R0) / math.log1p(NEAR_R / R0)
def r_of_v(v): return R0 * np.expm1(v * math.log1p(NEAR_R / R0))

def ground_colour(x, y, fp):
    """Linear RGB of the heath floor at world (x, y); fp = texel footprint (m) to fade fine detail."""
    hd = heather_density(x, y); sc = sand_cover(x, y); tr = track_mask(x, y)
    n1 = fbm(x / 1.7, y / 1.7, 4, seed=21); n2 = fbm(x * 1.3, y * 1.3, 3, seed=22)
    fine = np.where(fp < 0.04, fbm(x * 9, y * 9, 2, seed=23), 0.5)
    litter = np.stack([0.050 + 0.025 * n1, 0.036 + 0.016 * n1, 0.026 + 0.01 * n1], -1)
    # heather seen from above: dark green shoots, brown wood, purple bloom, varying patch by patch
    bloom = sstep(0.35, 0.75, fbm(x / 4 + 9, y / 4, 3, seed=24))
    heath = np.stack([0.060 + 0.055 * bloom, 0.058 + 0.004 * bloom, 0.034 + 0.045 * bloom], -1) * (0.7 + 0.6 * n2[..., None])
    grass = np.stack([0.20 + 0.08 * n2, 0.18 + 0.06 * n2, 0.10 + 0.03 * n2], -1)
    sand_old = np.stack([0.26, 0.22, 0.155], -1) * (0.85 + 0.3 * n1[..., None]) * (0.9 + 0.2 * fine[..., None])
    sand_new = np.stack([0.42, 0.33, 0.20], -1) * (0.85 + 0.25 * n2[..., None]) * (0.85 + 0.3 * fine[..., None])
    grit = (fbm(x * 22, y * 22, 1, seed=25) > 0.78) * (fp < 0.03)
    sand_new = sand_new * (1 - 0.35 * grit[..., None])
    gl = sstep(0.55, 0.8, fbm(x / 6 + 4, y / 6 + 1, 3, seed=26)) * (1 - hd)
    hv = sstep(0.1, 0.45, hd)
    farh = sstep(8.0, 12.0, np.hypot(x, y))[..., None]                    # beyond the cards: the paint carries the heath
    heath = heath * (1 - 0.3 * farh) + farh * 0.3 * np.stack([0.045 + 0.06 * bloom, 0.035 + 0.0 * bloom, 0.03 + 0.05 * bloom], -1) * (0.6 + 0.8 * n2[..., None])
    col = litter * (1 - hv[..., None]) + heath * hv[..., None]
    col = col * (1 - gl[..., None] * 0.7) + grass * (gl[..., None] * 0.7)
    bare = sstep(0.66, 0.78, fbm(x / 5 + 2, y / 5 + 8, 3, seed=27)) * (1 - hd) * 0.6
    col = col * (1 - bare[..., None]) + sand_old * bare[..., None]
    col = col * (1 - tr[..., None]) + sand_old * 1.08 * tr[..., None]
    col = col * (1 - sc[..., None]) + sand_new * sc[..., None]
    # ash and scorch round the cylinder, needle litter under the pines
    t, w = cyl_local(x, y)
    sc2 = sstep(RCYL + 5, RCYL, np.abs(w)) * sstep(-7, -1, t) * sstep(RC + 3, RC - 3, np.hypot(x - CR[0], y - CR[1]))
    ash = np.stack([0.17, 0.155, 0.14], -1) * (0.8 + 0.4 * n2[..., None])
    col = col * (1 - 0.8 * sc2[..., None]) + ash * 0.8 * sc2[..., None]
    for (px, py, pr) in PINES_XYR:
        u = sstep(pr * 1.1, pr * 0.3, np.hypot(x - px, y - py)) * 0.85
        needles = np.stack([0.20, 0.11, 0.05], -1) * (0.8 + 0.4 * n1[..., None])
        col = col * (1 - u[..., None]) + needles * u[..., None]
    return col

def paint_ground(N):
    v = (np.arange(N, dtype=np.float32) + 0.5) / N; u = (np.arange(N, dtype=np.float32) + 0.5) / N
    U, V = np.meshgrid(u, v)
    r = r_of_v(V); th = U * TWO_PI
    x = r * np.cos(th); y = r * np.sin(th)
    fp = np.maximum(r * TWO_PI / N, (r + R0) * math.log1p(NEAR_R / R0) / N)
    col = ground_colour(x, y, fp)
    rgba = np.ones((N, N, 4), np.float32); rgba[..., :3] = col
    return rgba

# ----------------------------------------------------------------------------- the pines (placed by hand for the composition)
#   x, y, height, crown radius, lod (2 near, 1 mid, 0 far)
PINES = [
    (-6.0, -9.5, 17.5, 4.2, 2),          # the old pine behind, left of the track
    (14.0, 26.0, 19.0, 5.0, 2), (19.5, 34.0, 16.5, 4.0, 1), (11.0, 40.0, 15.0, 3.6, 1),     # ahead-right
    (-1.0, 58.0, 18.0, 4.5, 1), (4.0, 66.0, 15.5, 3.8, 1), (-8.0, 70.0, 17.0, 4.0, 0),      # ahead, beyond the hollow
    (30.0, 6.0, 18.5, 4.6, 2), (36.0, -3.0, 16.0, 4.0, 1), (33.0, 14.0, 14.5, 3.4, 1),      # right: the sun clears these
    (-52.0, 52.0, 18.0, 4.5, 0), (-60.0, 38.0, 16.0, 4.0, 0), (-44.0, 64.0, 15.0, 3.6, 0),  # beyond the pit
    (12.0, -24.0, 17.0, 4.2, 1), (20.0, -34.0, 15.0, 3.8, 0), (-22.0, -30.0, 16.5, 4.0, 0), # behind
    (-30.0, -8.0, 14.0, 3.4, 1),
]
PINES_XYR = [(p[0], p[1], p[3] * 0.9) for p in PINES]

def needle_atlas(N=1024, seed=3):
    """Four clumps of Scots-pine foliage (2x2) as a crown reads from 5-60 m: forty-odd shoot tufts, each a star of
    blue-green needle pairs round a small dark core, thick in the middle of the clump and thinning to a ragged,
    bristling edge, with the thin orange twigs that carry them. Straight alpha; colour bled into the gaps."""
    rs = random.Random(seed); img = np.zeros((N, N, 4), np.float32)
    S = N // 2
    for vi in range(4):
        ox, oy = (vi % 2) * S, (vi // 2) * S
        def P(x, y): return (ox + x * S, oy + y * S)
        base = (0.5 + rs.uniform(-0.05, 0.05), 0.12)
        tufts = []
        for k in range([46, 40, 52, 44][vi]):
            for _ in range(20):
                cx, cy = 0.5 + rs.gauss(0, 0.16), 0.55 + rs.gauss(0, 0.15)
                if (cx - 0.5) ** 2 + ((cy - 0.55) / 0.9) ** 2 < 0.40 ** 2: break
            d = Vector((cx - base[0], cy - base[1], 0)).normalized()
            d = (d + Vector((rs.gauss(0, 0.45), rs.gauss(0, 0.45), 0))).normalized()
            tufts.append((cx, cy, d.x, d.y, rs.uniform(0.038, 0.06), rs.random()))
        for (cx, cy, dx, dy, L, tone) in tufts:
            mx, my = (cx + base[0]) * 0.5 + rs.gauss(0, 0.04), (cy + base[1]) * 0.5
            paint_stroke(img, P(*base), P(mx, my), 3.0, 2.0, (0.10, 0.05, 0.022))
            paint_stroke(img, P(mx, my), P(cx - dx * L * 0.5, cy - dy * L * 0.5), 2.0, 1.4, (0.12, 0.06, 0.028))
        tufts.sort(key=lambda t: t[5])
        for (cx, cy, dx, dy, L, tone) in tufts:
            paint_dot(img, P(cx, cy), S * L * 0.28, (0.020 + 0.012 * tone, 0.032 + 0.02 * tone, 0.024 + 0.012 * tone))
            for i in range(22):
                back = i >= 17
                a = math.radians(rs.uniform(-80, 80)) + (math.pi if back else 0.0)
                ca, sa = math.cos(a), math.sin(a)
                nx, ny = dx * ca - dy * sa, dx * sa + dy * ca
                nl = L * rs.uniform(0.75, 1.25) * (0.6 if back else 1.0)
                t2 = tone * 0.7 + rs.random() * 0.3
                col = (0.035 + 0.06 * t2, 0.062 + 0.08 * t2, 0.046 + 0.055 * t2)
                paint_stroke(img, P(cx, cy), P(cx + nx * nl, cy + ny * nl), 2.4, 1.1, col)
            paint_dot(img, P(cx + dx * L * 0.15, cy + dy * L * 0.15), 2.2, (0.20, 0.10, 0.045))
    return bleed_alpha(img)

def heather_atlas(N=512, seed=5):
    """Four clumps of ling in bloom (2x2), seen side on: wiry brown stems fanning up, tiny dark-green scale leaves,
    pale purple-pink flower spikes on the upper third; one variant mostly green, one browner (older)."""
    rs = random.Random(seed); img = np.zeros((N, N, 4), np.float32)
    S = N // 2
    for vi in range(4):
        ox, oy = (vi % 2) * S, (vi // 2) * S
        def P(x, y): return (ox + x * S, oy + y * S)
        bloom = [1.0, 0.75, 0.35, 0.9][vi]; old = [0.0, 0.3, 0.1, 0.55][vi]
        for k in range(46):
            x0 = 0.5 + rs.gauss(0, 0.12); a = rs.gauss(0, 0.42)
            L = rs.uniform(0.5, 0.92) * (1 - 0.6 * abs(x0 - 0.5))
            pts = [(x0, 0.0)]
            for j in range(1, 6):
                a += rs.gauss(0, 0.15)
                px, py = pts[-1]; pts.append((px + math.sin(a) * L / 5, py + math.cos(a) * L / 5))
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                paint_stroke(img, P(ax, ay), P(bx, by), 2.2, 1.6, (0.10, 0.065, 0.042))
            for j, ((ax, ay), (bx, by)) in enumerate(zip(pts, pts[1:])):
                for i in range(7):
                    t = rs.random(); px, py = ax + (bx - ax) * t, ay + (by - ay) * t
                    up = (py - 0.0) / max(L, 0.1)
                    if up > 0.62 and rs.random() < bloom:
                        c = (0.22 + rs.uniform(-0.04, 0.05), 0.10 + rs.uniform(-0.02, 0.03), 0.19 + rs.uniform(-0.03, 0.04))
                        paint_dot(img, P(px + rs.gauss(0, 0.012), py), rs.uniform(1.6, 2.6), c)
                    else:
                        g = rs.random()
                        c = (0.06 + 0.07 * old + 0.03 * g, 0.09 + 0.045 * g - 0.015 * old, 0.04 + 0.015 * g)
                        a2 = rs.uniform(-1.2, 1.2)
                        paint_stroke(img, P(px, py), P(px + math.sin(a2) * 0.03, py + math.cos(a2) * 0.03 + 0.01), 2.4, 1.2, c)
    return bleed_alpha(img)

def grass_atlas(N=512, seed=7):
    """Four tufts of heath grass (purple moor-grass and wavy hair-grass in August): long pale straw-green blades,
    a few thin flowering stems with purplish heads."""
    rs = random.Random(seed); img = np.zeros((N, N, 4), np.float32)
    S = N // 2
    for vi in range(4):
        ox, oy = (vi % 2) * S, (vi // 2) * S
        def P(x, y): return (ox + x * S, oy + y * S)
        for k in range(70):
            x0 = 0.5 + rs.gauss(0, 0.07); a = rs.gauss(0, 0.35); L = rs.uniform(0.45, 0.95)
            bend = rs.gauss(0, 0.5)
            pts = [(x0 + math.sin(a + bend * (j / 6) ** 2) * L * j / 6 * 0.9, L * j / 6 * (1 - 0.15 * (j / 6) ** 2)) for j in range(7)]
            g = rs.random()
            col = (0.17 + 0.12 * g, 0.16 + 0.09 * g, 0.075 + 0.04 * g) if rs.random() < 0.7 else (0.10, 0.12, 0.05)
            for j, ((ax, ay), (bx, by)) in enumerate(zip(pts, pts[1:])):
                paint_stroke(img, P(ax, ay), P(bx, by), 3.0 - 0.4 * j, 2.6 - 0.4 * j, col)
        for k in range(6):
            x0 = 0.5 + rs.gauss(0, 0.05); a = rs.gauss(0, 0.2)
            top = (x0 + math.sin(a) * 0.95, 0.97)
            paint_stroke(img, P(x0, 0.0), P(*top), 1.4, 1.0, (0.22, 0.18, 0.10))
            for i in range(14):
                t = 0.78 + 0.22 * i / 14
                paint_dot(img, P(x0 + (top[0] - x0) * t + rs.gauss(0, 0.012), 0.97 * t), 1.5, (0.16, 0.09, 0.11))
    return bleed_alpha(img)

def gorse_atlas(N=512, seed=9):
    """Gorse in late summer: a dense dark mass of green spines with a scatter of yellow flowers."""
    rs = random.Random(seed); img = np.zeros((N, N, 4), np.float32)
    S = N // 2
    for vi in range(4):
        ox, oy = (vi % 2) * S, (vi // 2) * S
        def P(x, y): return (ox + x * S, oy + y * S)
        for k in range(40):
            paint_dot(img, P(0.5 + rs.gauss(0, 0.15), 0.42 + rs.gauss(0, 0.16)), S * rs.uniform(0.03, 0.06), (0.018, 0.03, 0.012))
        for k in range(900):
            cx, cy = 0.5 + rs.gauss(0, 0.2), 0.45 + rs.gauss(0, 0.2)
            if (cx - 0.5) ** 2 / 0.2 + (cy - 0.45) ** 2 / 0.17 > 0.75 or cy < 0.02: continue
            a = rs.uniform(0, TWO_PI); L = rs.uniform(0.02, 0.045)
            g = rs.random()
            paint_stroke(img, P(cx, cy), P(cx + math.cos(a) * L, cy + math.sin(a) * L), 2.2, 0.8, (0.03 + 0.03 * g, 0.06 + 0.05 * g, 0.02 + 0.015 * g))
        for k in range(int([40, 70, 20, 50][vi])):
            cx, cy = 0.5 + rs.gauss(0, 0.17), 0.5 + rs.gauss(0, 0.15)
            if (cx - 0.5) ** 2 / 0.2 + (cy - 0.45) ** 2 / 0.17 > 0.6: continue
            paint_dot(img, P(cx, cy), rs.uniform(2.0, 3.4), (0.62, 0.42, 0.02))
    return bleed_alpha(img)

def bracken_atlas(N=512, seed=11):
    """Bracken fronds seen from the side and above: a rachis with paired pinnae, green going gold at the edges."""
    rs = random.Random(seed); img = np.zeros((N, N, 4), np.float32)
    S = N // 2
    for vi in range(4):
        ox, oy = (vi % 2) * S, (vi // 2) * S
        def P(x, y): return (ox + x * S, oy + y * S)
        a0 = rs.uniform(-0.3, 0.3); age = [0.0, 0.25, 0.5, 0.15][vi]
        pts = [(0.5, 0.02)]
        a = a0
        for j in range(1, 10):
            a += 0.06; px, py = pts[-1]; pts.append((px + math.sin(a) * 0.1, py + math.cos(a) * 0.1))
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            paint_stroke(img, P(ax, ay), P(bx, by), 3.0, 2.4, (0.10, 0.08, 0.03))
        for j, ((ax, ay), (bx, by)) in enumerate(zip(pts[2:], pts[3:])):
            L = 0.32 * (1 - j / 8) + 0.05
            for side in (-1, 1):
                ang = math.atan2(bx - ax, by - ay) + side * math.radians(70)
                ex, ey = ax + math.sin(ang) * L, ay + math.cos(ang) * L
                for i in range(int(L * 60)):
                    t = i / max(1, int(L * 60))
                    px, py = ax + (ex - ax) * t, ay + (ey - ay) * t
                    ll = 0.035 * (1 - t) + 0.008
                    g = rs.random(); edge = age * (0.5 + 0.5 * t)
                    col = (0.06 + 0.12 * edge + 0.02 * g, 0.11 + 0.02 * g - 0.03 * edge, 0.025)
                    for s2 in (-1, 1):
                        a2 = ang + s2 * math.radians(80)
                        paint_stroke(img, P(px, py), P(px + math.sin(a2) * ll, py + math.cos(a2) * ll), 2.8, 1.4, col)
    return bleed_alpha(img)

def atlas_uv(vi, inset=0.004):
    u0, v0 = (vi % 2) * 0.5, (vi // 2) * 0.5
    return (u0 + inset, v0 + inset, u0 + 0.5 - inset, v0 + 0.5 - inset)

# ----------------------------------------------------------------------------- opaque foliage-mass textures (tileable, numpy)
def _wrap_dot(img, p, r, col, alpha=1.0):
    N = img.shape[0]
    for ox in (-N, 0, N):
        for oy in (-N, 0, N):
            x, y = p[0] + ox, p[1] + oy
            if -r - 2 < x < N + r + 2 and -r - 2 < y < N + r + 2: paint_dot(img, (x, y), r, col, alpha)

def heath_mound_tex(N=512, seed=15):
    """Ling seen from above and at a slant, as the low heather mounds beyond the cards read: dark shoots, brown wood,
    and drifts of purple bloom; tiles (dots wrap round the edges)."""
    rs = random.Random(seed); img = np.zeros((N, N, 4), np.float32); img[...] = (0.030, 0.034, 0.020, 1.0)
    for k in range(2600):
        g = rs.random(); o = rs.random()
        _wrap_dot(img, (rs.uniform(0, N), rs.uniform(0, N)), rs.uniform(1.6, 3.6),
                  (0.05 + 0.04 * o + 0.02 * g, 0.07 + 0.04 * g - 0.02 * o, 0.03 + 0.012 * g))
    for k in range(900):
        _wrap_dot(img, (rs.uniform(0, N), rs.uniform(0, N)), rs.uniform(1.0, 1.8), (0.10, 0.065, 0.042))
    for k in range(700):                                                  # holes into the canopy's shade
        _wrap_dot(img, (rs.uniform(0, N), rs.uniform(0, N)), rs.uniform(1.5, 3.5), (0.01, 0.01, 0.008))
    img[..., :3] *= 0.4                                                   # a canopy full of its own shadow
    for k in range(30):                                                   # drifts of bloom, readable from 10-30 m
        cx, cy = rs.uniform(0, N), rs.uniform(0, N)
        for i in range(8):
            _wrap_dot(img, (cx + rs.gauss(0, 30), cy + rs.gauss(0, 30)), rs.uniform(18, 34), (0.06, 0.03, 0.055), 0.22)
    for k in range(240):
        cx, cy = rs.uniform(0, N), rs.uniform(0, N); b = rs.uniform(0.5, 0.9)
        for i in range(rs.randint(6, 16)):
            c = (0.11 * b + rs.uniform(-0.02, 0.02), 0.05 * b + rs.uniform(-0.01, 0.01), 0.10 * b + rs.uniform(-0.02, 0.02))
            _wrap_dot(img, (cx + rs.gauss(0, 8), cy + rs.gauss(0, 8)), rs.uniform(1.4, 2.6), c)
    img[..., 3] = 1.0
    return img

def gorse_mound_tex(N=256, seed=17):
    """The dark inside of a gorse bush: spines in shade, a few flowers."""
    rs = random.Random(seed); img = np.zeros((N, N, 4), np.float32); img[...] = (0.016, 0.026, 0.010, 1.0)
    for k in range(2200):
        g = rs.random()
        _wrap_dot(img, (rs.uniform(0, N), rs.uniform(0, N)), rs.uniform(0.8, 1.8), (0.03 + 0.03 * g, 0.06 + 0.05 * g, 0.02 + 0.015 * g))
    for k in range(110):
        _wrap_dot(img, (rs.uniform(0, N), rs.uniform(0, N)), rs.uniform(1.0, 1.8), (0.62, 0.42, 0.02))
    img[..., :3] *= 0.4
    img[..., 3] = 1.0
    return img

def treeline_strip(W=4096, Hh=256, seed=13):
    """Distant woods all round the common (one band, wrapping once round the horizon, so it is seamless): a hazed
    canopy of pine and birch with an irregular top, broad flat pine crowns standing a little above it here and there,
    lower where the heath runs out to the horizon."""
    img = np.zeros((Hh, W, 4), np.float32)
    th = (np.arange(W, dtype=np.float32) + 0.5) / W * TWO_PI
    cx, cy = np.cos(th), np.sin(th)
    prof = 0.30 + 0.30 * fbm(cx * 2.2 + 5, cy * 2.2, 4, seed=3) + 0.12 * fbm(cx * 14 + 1, cy * 14, 3, seed=4)
    gap = sstep(0.62, 0.72, fbm(cx * 3 + 9, cy * 3, 3, seed=8))
    prof = prof * (1 - 0.35 * gap)
    lumps = 0.10 * fbm(cx * 40, cy * 40, 2, seed=5)
    prof = (prof + lumps) * Hh
    yy = np.arange(Hh, dtype=np.float32)[:, None]
    n = fbm(cx[None, :] * 160 + yy / 9.0, cy[None, :] * 160, 4, seed=6)
    a = sstep(prof[None, :] + 3, prof[None, :] - 3, yy + (n - 0.5) * 16)
    col = np.array([0.070, 0.080, 0.070]) * (0.75 + 0.5 * n[..., None])
    img[..., :3] = col; img[..., 3] = a
    return bleed_alpha(img)

# ----------------------------------------------------------------------------- the sky (numpy, equirect band packed toward the horizon)
SKY_EL0 = -8.0
def sky_v_of(el): return ((el - SKY_EL0) / (90.0 - SKY_EL0)) ** 0.6
def gen_sky(W=4096, Hh=1024):
    """Dawn a few minutes after sunrise in August: warm gold low in the east, rose and lilac haze along the horizon,
    a pale clean blue overhead, a few high streaks lit from below, and the thread of blue smoke from the heather
    fire to the east."""
    v = (np.arange(Hh) + 0.5) / Hh
    el = SKY_EL0 + (90 - SKY_EL0) * v ** (1 / 0.6)
    az = (np.arange(W) + 0.5) / W * 360.0                      # u = compass az / 360 (u=0 north, east at 0.25)
    AZ, EL = np.meshgrid(az, el)
    azr, elr = np.radians(AZ), np.radians(EL)
    dx, dy, dz = np.cos(elr) * np.sin(azr), np.cos(elr) * np.cos(azr), np.sin(elr)
    cg = np.clip(dx * SUN_DIR.x + dy * SUN_DIR.y + dz * SUN_DIR.z, -1, 1); ang = np.degrees(np.arccos(cg))
    toward = np.clip(cg, 0, 1)
    zen = np.array([0.16, 0.27, 0.50]); midb = np.array([0.36, 0.44, 0.60])
    hor_warm = np.array([1.05, 0.68, 0.38]); hor_cool = np.array([0.62, 0.54, 0.58])
    e = np.clip(EL, 0, 90)[..., None]
    hor = hor_cool * (1 - toward[..., None] ** 2) + hor_warm * toward[..., None] ** 2
    f = (e / 90.0) ** 0.42
    col = hor * (1 - f) * 1.0 + (midb * (1 - f) + zen * f) * f
    col = col * 0.55 + (hor * np.exp(-e / 7.0)) * 0.45
    glow = 2.2 * np.exp(-(ang / 1.2) ** 2) + 0.9 * np.exp(-(ang / 6.0) ** 2) + 0.35 * np.exp(-(ang / 25.0) ** 2)
    col += glow[..., None] * np.array([1.0, 0.80, 0.55])
    sun = (ang < 0.55).astype(np.float32)
    col += sun[..., None] * np.array([6.0, 5.0, 3.6])
    # high streaks, lit gold-pink from below near the sun, lilac-grey away from it
    k = 1.0 / (np.maximum(dz, 0.03) + 0.06)
    pu, pv = dx * k, dy * k
    ca, sa = math.cos(0.4), math.sin(0.4)
    uu = (pu * ca + pv * sa) * 0.35; vv = (-pu * sa + pv * ca) * 3.0
    n = fbm(uu, vv, 5, seed=301)
    streak = sstep(0.60, 0.74, n) * sstep(2.5, 7.0, EL) * sstep(26, 12, EL) * 0.6
    sc = np.array([0.95, 0.62, 0.50]) * toward[..., None] ** 1.5 + np.array([0.48, 0.44, 0.52]) * (1 - toward[..., None] ** 1.5)
    col = col * (1 - 0.65 * streak[..., None]) + sc * 0.65 * streak[..., None]
    # the smoke: a thin column rising from the heather on the eastern horizon, leaning north as it climbs
    s_az = 74.0
    rise = np.clip(EL, 0, None)
    cx = s_az - 0.9 * rise - 0.08 * rise ** 1.6
    width = 0.25 + 0.20 * rise
    sm = np.exp(-((AZ - cx) / width) ** 2) * sstep(-0.3, 0.4, EL) * sstep(13, 4, EL)
    sm *= 0.55 + 0.6 * fbm(AZ / 2.0, EL / 1.2, 3, seed=55)
    col = col * (1 - 0.45 * sm[..., None]) + np.array([0.42, 0.46, 0.58]) * 0.45 * sm[..., None]
    # below the horizon: a dim heath (only seen at the very edge, under the far land)
    below = sstep(0.0, -2.0, EL)
    col = col * (1 - below[..., None]) + np.array([0.10, 0.09, 0.07]) * below[..., None]
    rgba = np.ones((Hh, W, 4), np.float32); rgba[..., :3] = np.clip(col * 0.85, 0, 1)
    return rgba

# ----------------------------------------------------------------------------- terrain meshes
def ring_radii():
    rs = [0.0]; r = 0.0
    while r < NEAR_R:
        step = min(2.4, 0.35 + r * 0.075); r = min(NEAR_R, r + step); rs.append(r)
    return rs
def near_terrain(mat):
    me = bpy.data.meshes.new("Ground"); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rs = ring_radii(); NS = 96
    centre = bm.verts.new((0, 0, gz(0, 0)))
    rings = []
    for r in rs[1:]:
        th = np.arange(NS) / NS * TWO_PI
        xs, ys = r * np.cos(th), r * np.sin(th); zs = gz(xs, ys)
        rings.append([bm.verts.new((float(a), float(b), float(c))) for a, b, c in zip(xs, ys, zs)])
    vr = [float(v_of_r(r)) for r in rs]
    for i in range(NS):
        j = (i + 1) % NS
        f = bm.faces.new((centre, rings[0][i], rings[0][j]))
        for lp, uv in zip(f.loops, ((i / NS + 0.5 / NS, 0.0), (i / NS, vr[1]), ((i + 1) / NS, vr[1]))): lp[uvl].uv = uv
    for k in range(len(rings) - 1):
        for i in range(NS):
            j = (i + 1) % NS
            f = bm.faces.new((rings[k][i], rings[k + 1][i], rings[k + 1][j], rings[k][j]))
            for lp, uv in zip(f.loops, ((i / NS, vr[k + 1]), (i / NS, vr[k + 2]), ((i + 1) / NS, vr[k + 2]), ((i + 1) / NS, vr[k + 1]))): lp[uvl].uv = uv
    for f in bm.faces: f.smooth = True
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Ground", me); me.materials.append(mat); K.link(o)
    K.KEEP_UV.add(mat.name)
    return o, rings[-1]

def far_terrain(mat):
    NS, NR = 56, 7
    me = bpy.data.meshes.new("FarLand"); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rs = [NEAR_R - 0.6 + (TERRAIN_R - NEAR_R + 0.6) * (k / NR) ** 1.3 for k in range(NR + 1)]
    grid = []
    for r in rs:
        row = []
        for i in range(NS):
            th = TWO_PI * i / NS; x, y = r * math.cos(th), r * math.sin(th)
            z = float(gz(x, y)) - (0.25 if r < NEAR_R else 0.0) - 2.5 * ((r - NEAR_R) / (TERRAIN_R - NEAR_R)) ** 2
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for k in range(NR):
        for i in range(NS):
            j = (i + 1) % NS
            f = bm.faces.new((grid[k][i], grid[k + 1][i], grid[k + 1][j], grid[k][j]))
            for lp in f.loops: lp[uvl].uv = (lp.vert.co.x / (2 * TERRAIN_R) + 0.5, lp.vert.co.y / (2 * TERRAIN_R) + 0.5)
    for f in bm.faces: f.smooth = True
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("far.land", me); me.materials.append(mat); K.link(o)
    K.KEEP_UV.add(mat.name)
    return o

def paint_far(N=1024):
    u = (np.arange(N) + 0.5) / N
    U, V = np.meshgrid(u, u)
    x = (U - 0.5) * 2 * TERRAIN_R; y = (V - 0.5) * 2 * TERRAIN_R
    col = ground_colour(x, y, np.full(x.shape, 2 * TERRAIN_R / N))
    haze = np.clip((np.hypot(x, y) - NEAR_R) / 60, 0, 1)[..., None] * 0.35
    col = col * (1 - haze) + np.array([0.30, 0.27, 0.27]) * haze
    rgba = np.ones((N, N, 4), np.float32); rgba[..., :3] = col
    return rgba

print("painting ground ...")
GROUND_N = 4096 if not args.quick else 2048
M_GROUND = K.card_material("M_Ground", K.image_from("T_Ground", paint_ground(GROUND_N)), rough=0.92, clip=False)
M_FAR = K.card_material("M_FarLand", K.image_from("T_FarLand", paint_far(1024)), rough=0.95, clip=False)
GROUND, EDGE = near_terrain(M_GROUND)
far_terrain(M_FAR)

# ----------------------------------------------------------------------------- the cylinder
def cylinder_mat():
    """Thick scaly dun-coloured incrustation: cracked plates of ash-crust, lighter where they have dried, flaking
    off round the circular edge of the end to show a dull grey metal; sand dusted on its lower flanks."""
    m, nt, b = new_mat("M_Cylinder")
    xyz, X, Y, Z = obj_xyz(nt)
    warp = noise_tex(nt, xyz, 0.8, 3.0, 0.6)
    wv = node(nt, "ShaderNodeVectorMath", operation='ADD'); nt.links.new(xyz, wv.inputs[0])
    sc_ = node(nt, "ShaderNodeVectorMath", operation='SCALE'); nt.links.new(warp.outputs["Color"], sc_.inputs[0]); sc_.inputs["Scale"].default_value = 0.6
    nt.links.new(sc_.outputs[0], wv.inputs[1])
    vor = node(nt, "ShaderNodeTexVoronoi", feature='DISTANCE_TO_EDGE'); vor.inputs["Scale"].default_value = 3.2; vor.inputs["Randomness"].default_value = 1.0
    nt.links.new(wv.outputs[0], vor.inputs["Vector"])
    vor2 = node(nt, "ShaderNodeTexVoronoi", feature='F1'); vor2.inputs["Scale"].default_value = 3.2
    nt.links.new(wv.outputs[0], vor2.inputs["Vector"])
    crack = math_(nt, 'MULTIPLY', maprange(nt, vor.outputs["Distance"], 0.0, 0.035, 1.0, 0.0), maprange(nt, noise_tex(nt, xyz, 1.3, 3.0, 0.6).outputs["Fac"], 0.35, 0.6, 0.25, 1.0))
    n = noise_tex(nt, xyz, 0.35, 5.0, 0.6)
    fine = noise_tex(nt, xyz, 6.0, 4.0, 0.6)
    plate = tone_ramp(nt, vor2.outputs["Color"] if False else white(nt, vor2.outputs["Position"]).outputs["Value"],
                      [(0.095, 0.08, 0.06), (0.13, 0.11, 0.08), (0.155, 0.13, 0.095), (0.115, 0.10, 0.08), (0.17, 0.145, 0.11)])
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0.0, 0.35), plate, (0.6, 0.58, 0.55, 1))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.55, 0.72, 0.0, 0.3), col, (0.22, 0.21, 0.19, 1))      # pale ash
    attr = node(nt, "ShaderNodeAttribute"); attr.attribute_name = "Mask"
    sep = node(nt, "ShaderNodeSeparateColor"); nt.links.new(attr.outputs["Color"], sep.inputs[0])
    flake, sand = sep.outputs[0], sep.outputs[1]
    flk = math_(nt, 'MULTIPLY', flake, maprange(nt, fine.outputs["Fac"], 0.35, 0.6, 0.0, 1.0))
    col = mix_rgb(nt, 'MIX', flk, col, (0.50, 0.49, 0.46, 1))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', crack, 0.7), col, (0.045, 0.04, 0.035, 1))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', sand, maprange(nt, fine.outputs["Fac"], 0.3, 0.6, 0.5, 1.0)), col, (0.48, 0.40, 0.27, 1))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, flk, 0.85, 0.32), b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = 0.0
    h = math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.4), math_(nt, 'MULTIPLY', crack, 0.8))
    bump_from(nt, b, h, 0.6, 0.05)
    return m
M_CYL = cylinder_mat()

def build_cylinder():
    ax = CYL_A.normalized()
    ref = Vector((0, 0, 1)); side = ax.cross(ref).normalized(); up = side.cross(ax).normalized()
    NSEG = 96
    me = bpy.data.meshes.new("Cylinder"); bm = bmesh.new()
    def ring(t, r):
        out = []
        for i in range(NSEG):
            th = TWO_PI * i / NSEG
            out.append(CYL_E + ax * t + (side * math.cos(th) + up * math.sin(th)) * r)
        return out
    rings = []
    # the end: a raised rim (the edge the scale is flaking from), a recessed face with a broad shallow boss
    prof = [(-0.9, RCYL - 0.55), (-0.85, RCYL + 0.05), (-0.55, RCYL + 0.25), (-0.2, RCYL + 0.25), (0.0, RCYL), (0.6, RCYL)]
    prof += [(0.4 + (CYL_L - 0.4) * k / 9, RCYL) for k in range(1, 10)]
    face = [(-0.75, RCYL - 0.9), (-0.55, RCYL - 1.15), (-0.62, RCYL - 1.45), (-0.45, RCYL - 1.6), (-0.42, RCYL - 3.5), (-0.36, RCYL - 6.5), (-0.4, RCYL - 9.5), (-0.62, 2.0)]
    for t, r in list(reversed(face)) + prof:
        rings.append([bm.verts.new(p) for p in ring(t, r)])
    for a, b_ in zip(rings, rings[1:]):
        for i in range(NSEG):
            j = (i + 1) % NSEG; bm.faces.new((a[i], a[j], b_[j], b_[i]))
    centre = bm.verts.new(CYL_E + ax * (-0.75))
    for i in range(NSEG):
        bm.faces.new((centre, rings[0][(i + 1) % NSEG], rings[0][i]))
    # crust: lumpy displacement along the normal
    for v in bm.verts:
        p = v.co
        q = K.fbm(np.array(p.x / 2.2 + p.z * 0.3), np.array(p.y / 2.2 - p.z * 0.2), 4, seed=91)
        rel = p - CYL_E; tt = rel.dot(ax)
        radial = (rel - ax * tt)
        nrm = radial.normalized() if radial.length > RCYL * 0.8 else -ax
        v.co = p + nrm * float(q - 0.5) * 0.45
    # drop what is deep under the sand (never seen)
    kill = [f for f in bm.faces if all(v.co.z < gz(v.co.x, v.co.y) - 3.5 for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    for f in bm.faces: f.smooth = True
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Cylinder", me); me.materials.append(M_CYL); K.link(o)
    K.autosmooth(o, 32)
    bm2 = bmesh.new(); bm2.from_mesh(me); bm2.normal_update()
    flip = []
    for f in bm2.faces:
        c = f.calc_center_median()
        if abs(f.normal.dot(ax)) > 0.6: want = -ax                     # the end
        else:
            tt = (c - CYL_E).dot(ax); want = c - (CYL_E + ax * tt)       # the body: outward from the axis
        if f.normal.dot(want) < 0: flip.append(f)
    bmesh.ops.reverse_faces(bm2, faces=flip); bm2.to_mesh(me); bm2.free()
    # masks for the material: R = flaking round the end's edge, G = sand dusting low on the flanks
    at = me.color_attributes.new("Mask", 'FLOAT_COLOR', 'POINT')
    vals = []
    for v in me.vertices:
        rel = v.co - CYL_E; tt = rel.dot(ax); rr = (rel - ax * tt).length
        flake = max(0.0, 1.0 - abs(tt + 0.6) / 1.6) * max(0.0, min(1.0, (rr - (RCYL - 1.7)) / 0.6))
        sand = max(0.0, min(1.0, 1.0 - (v.co.z - float(gz(v.co.x, v.co.y))) / 2.0))
        vals += [flake, sand, 0.0, 1.0]
    at.data.foreach_set("color", vals)
    return o
from wotw_kit import orient
CYL_OBJ = build_cylinder()

# ----------------------------------------------------------------------------- bark, splintered wood
def bark_mat():
    """Scots pine bark: thick grey-brown plates with deep dark fissures low on the trunk, thin flaking orange bark
    up in the crown (vertex attribute 'H': height fraction along the trunk)."""
    m, nt, b = new_mat("M_Bark")
    xyz, X, Y, Z = obj_xyz(nt)
    dn = noise_tex(nt, xyz, 2.0, 3.0, 0.6)
    dv = node(nt, "ShaderNodeVectorMath", operation='ADD'); nt.links.new(xyz, dv.inputs[0])
    dsc = node(nt, "ShaderNodeVectorMath", operation='SCALE'); nt.links.new(dn.outputs["Color"], dsc.inputs[0]); dsc.inputs["Scale"].default_value = 0.08
    nt.links.new(dsc.outputs[0], dv.inputs[1])
    mp = node(nt, "ShaderNodeMapping"); nt.links.new(dv.outputs[0], mp.inputs["Vector"]); mp.inputs["Scale"].default_value = (15.0, 15.0, 2.6)
    vor = node(nt, "ShaderNodeTexVoronoi", feature='DISTANCE_TO_EDGE'); vor.inputs["Scale"].default_value = 1.0
    nt.links.new(mp.outputs["Vector"], vor.inputs["Vector"])
    vorc = node(nt, "ShaderNodeTexVoronoi", feature='F1'); vorc.inputs["Scale"].default_value = 1.0
    nt.links.new(mp.outputs["Vector"], vorc.inputs["Vector"])
    attr = node(nt, "ShaderNodeAttribute"); attr.attribute_name = "H"
    hsep = node(nt, "ShaderNodeSeparateColor"); nt.links.new(attr.outputs["Color"], hsep.inputs[0])
    hh = hsep.outputs[0]
    fiss = maprange(nt, vor.outputs["Distance"], 0.0, 0.08, 1.0, 0.0)
    pv = white(nt, vorc.outputs["Position"]).outputs["Value"]
    low = tone_ramp(nt, pv, [(0.075, 0.058, 0.048), (0.10, 0.078, 0.062), (0.13, 0.10, 0.08), (0.09, 0.07, 0.056)])
    high = tone_ramp(nt, pv, [(0.36, 0.15, 0.06), (0.44, 0.20, 0.08), (0.30, 0.13, 0.05)])
    up = maprange(nt, hh, 0.42, 0.62, 0.0, 1.0, 'SMOOTHSTEP')
    col = mix_rgb(nt, 'MIX', up, low, high)
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', fiss, mix_f(nt, up, 0.92, 0.35)), col, (0.03, 0.022, 0.018, 1))
    n = noise_tex(nt, xyz, 3.0, 4.0, 0.6)
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.55, 0.7, 0.0, 0.3), math_(nt, 'SUBTRACT', 1.0, up)), col, (0.10, 0.12, 0.08, 1))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, fiss, 0.8, 0.95), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, fiss), mix_f(nt, up, 1.0, 0.2)), 0.9, 0.02)
    return m
M_BARK = bark_mat()

def splinter_mat():
    m, nt, b = new_mat("M_Splinters")
    xyz, X, Y, Z = obj_xyz(nt)
    wv = node(nt, "ShaderNodeTexWave", wave_type='BANDS'); wv.inputs["Scale"].default_value = 9.0; wv.inputs["Distortion"].default_value = 14.0
    wv.inputs["Detail"].default_value = 6.0; nt.links.new(xyz, wv.inputs["Vector"])
    col = tone_ramp(nt, wv.outputs["Fac"], [(0.36, 0.27, 0.16), (0.55, 0.44, 0.29), (0.48, 0.37, 0.23), (0.62, 0.52, 0.36)])
    n = noise_tex(nt, xyz, 1.5, 4.0, 0.6)
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.5, 0.7, 0.0, 0.6), col, (0.4, 0.33, 0.27, 1))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, wv.outputs["Fac"], 0.5, 0.01)
    return m
M_SPLIT = splinter_mat()

# ----------------------------------------------------------------------------- foliage materials (numpy atlases)
print("painting foliage ...")
M_NEEDLES = K.card_material("M_PineNeedles", K.image_from("T_PineNeedles", needle_atlas()), rough=0.8)
M_HEATHER = K.card_material("M_Heather", K.image_from("T_Heather", heather_atlas()), rough=0.85)
# opaque stand-ins (the foliage diet for the Quest: alpha-tested overdraw is what costs on its tile GPU):
# the heather canopy the near cards rise out of, and the gorse bushes' cores
M_HEATHMOUND = K.card_material("M_HeathMound", K.image_from("T_HeathMound", heath_mound_tex()), rough=0.9, clip=False, double=False, repeat=True)
M_GORSEMOUND = K.card_material("M_GorseMound", K.image_from("T_GorseMound", gorse_mound_tex()), rough=0.85, clip=False, double=False, repeat=True)
for _m in (M_HEATHMOUND, M_GORSEMOUND):        # a mat of needles or shoots has no glossy skin (no grazing sheen
    _b = next(n for n in _m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')   # toward the low sun)
    _b.inputs["Specular IOR Level"].default_value = 0.0; _b.inputs["Roughness"].default_value = 1.0
M_GRASS = K.card_material("M_HeathGrass", K.image_from("T_HeathGrass", grass_atlas()), rough=0.85)
M_GORSE = K.card_material("M_Gorse", K.image_from("T_Gorse", gorse_atlas()), rough=0.8)
M_BRACKEN = K.card_material("M_Bracken", K.image_from("T_Bracken", bracken_atlas()), rough=0.8)
M_TREELINE = K.card_material("M_DistantTrees", K.image_from("T_DistantTrees", treeline_strip()), rough=0.95, repeat=True)

# ----------------------------------------------------------------------------- pines
BARK_PARTS = []          # (verts, faces, heights) appended into one bark mesh
class BarkMesh:
    def __init__(self): self.bm = bmesh.new(); self.h = []
    def tube(self, pts, radii, sides, hfrac):
        P = [Vector(p) for p in pts]; n = len(P)
        tang = [((P[min(n - 1, i + 1)] - P[max(0, i - 1)]).normalized()) for i in range(n)]
        ref = Vector((1, 0, 0)) if abs(tang[0].x) < 0.9 else Vector((0, 1, 0))
        nrm = tang[0].cross(ref).normalized(); rings = []
        for i in range(n):
            if i > 0:
                nrm = (nrm - tang[i] * nrm.dot(tang[i])).normalized()
            bn = tang[i].cross(nrm)
            ring = []
            for k in range(sides):
                th = TWO_PI * k / sides
                ring.append(self.bm.verts.new(P[i] + (nrm * math.cos(th) + bn * math.sin(th)) * radii[i]))
                self.h.append(hfrac[i])
            rings.append(ring)
        for a, b_ in zip(rings, rings[1:]):
            for k in range(sides):
                k2 = (k + 1) % sides; f = self.bm.faces.new((a[k], a[k2], b_[k2], b_[k])); f.smooth = True
        f = self.bm.faces.new(list(reversed(rings[0]))); f.smooth = True
        f = self.bm.faces.new(rings[-1]); f.smooth = True
    def finish(self, name, mat):
        me = bpy.data.meshes.new(name); self.bm.normal_update(); self.bm.to_mesh(me); self.bm.free()
        o = bpy.data.objects.new(name, me); me.materials.append(mat); K.link(o)
        at = me.color_attributes.new("H", 'FLOAT_COLOR', 'POINT')
        vals = []
        for h in self.h: vals += [h, h, h, 1.0]
        at.data.foreach_set("color", vals)
        return o
BARK = BarkMesh()
CROWNS = CardMesh("veg.crown.pines")

class MassMesh(CardMesh):
    """Opaque lumpy masses with shared vertices, custom (soft) normals and tiled UVs: the heather canopy and the
    gorse bushes' cores."""
    def vert(self, p, n, w):
        self.normals.append(Vector(n).normalized()); self.weights.append(w)
        return self.bm.verts.new(p)
    def face(self, vs, uvs):
        try: f = self.bm.faces.new(vs)
        except ValueError: return None
        for lp, uv in zip(f.loops, uvs): lp[self.uvl].uv = uv
        f.smooth = True
        return f

HEATHMOUND = MassMesh("HeathMound"); GORSEMOUND = MassMesh("GorseMound")

def pad(cm, centre, radius, crown_c, crown_r, rs, ncards, flat=0.55, lean=None, up=0.85):
    """A clump of needle sprays: cards facing outward and up from the pad centre, normals from the crown's centre."""
    for k in range(ncards):
        d = Vector((rs.gauss(0, 1), rs.gauss(0, 1), rs.gauss(0, 1) * flat)).normalized()
        if d.z < -0.3: d.z = -d.z * 0.5
        p = centre + d * radius * rs.uniform(0.15, 0.7)
        out = (p - centre).normalized() if (p - centre).length > 1e-3 else Vector((0, 0, 1))
        if lean is not None: out = (out + lean * 0.8).normalized()
        nrm_card = (out * 0.95 + Vector((0, 0, up))).normalized()
        tang = nrm_card.cross(Vector((rs.uniform(-1, 1), rs.uniform(-1, 1), rs.uniform(-0.3, 0.3)))).normalized()
        if tang.length < 0.5: tang = nrm_card.orthogonal().normalized()
        bit = nrm_card.cross(tang).normalized()
        s = radius * rs.uniform(0.85, 1.3)
        c0 = p - tang * s * 0.5 - bit * s * 0.5
        corners = [c0, c0 + tang * s, c0 + tang * s + bit * s, c0 + bit * s]
        vi = rs.randrange(4); u0, v0, u1, v1 = atlas_uv(vi)
        uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        norms, wts = [], []
        for q in corners:
            nn = (q - crown_c); nn.z *= 0.6
            nn = (nn.normalized() * 0.75 + Vector((0, 0, 0.45))).normalized()
            norms.append(nn)
            hd = Vector((q.x - crown_c.x, q.y - crown_c.y, 0)).length
            wts.append(max(0.15, min(1.0, 0.25 + 0.75 * hd / max(crown_r, 0.5))))
        cm.quad(corners, uvs, norms, wts)

def pine(x, y, H, CRr, lod, seed):
    rs = random.Random(seed)
    z0 = float(gz(x, y)) - 0.25
    lean = Vector((rs.gauss(0, 0.05), rs.gauss(0, 0.05), 0))
    sides = 12 if lod == 2 else 8 if lod == 1 else 6
    nseg = 10 if lod >= 1 else 5
    trunk = []; radii = []; hf = []
    r0 = 0.20 + H * 0.012
    sweep = rs.uniform(0, TWO_PI); amp = rs.uniform(0.15, 0.6)
    for i in range(nseg + 1):
        t = i / nseg
        off = Vector((math.cos(sweep), math.sin(sweep), 0)) * amp * math.sin(t * math.pi * 0.8) + lean * H * t
        trunk.append(Vector((x, y, z0 + H * t)) + off)
        radii.append(r0 * (1.25 - 0.25 * min(1, t * 6)) * (1 - 0.82 * t) + 0.03)
        hf.append(t)
    BARK.tube([tuple(p) for p in trunk], radii, sides, hf)
    # root flare: a short wider collar half in the ground
    BARK.tube([tuple(trunk[0] + Vector((0, 0, -0.15))), tuple(trunk[0] + Vector((0, 0, 0.55)))], [r0 * 1.7, r0 * 1.12], sides, [0.0, 0.03])
    crown_base = rs.uniform(0.40, 0.52)
    ctop = trunk[-1]
    crown_c = Vector((x, y, z0 + H * (crown_base + 1.0) / 2)) + lean * H * 0.8
    # dead stubs below the crown
    if lod >= 1:
        for k in range(rs.randint(3, 6)):
            t = rs.uniform(0.25, crown_base - 0.05); a = rs.uniform(0, TWO_PI)
            b0 = Vector((x, y, z0 + H * t)) + lean * H * t
            d = Vector((math.cos(a), math.sin(a), rs.uniform(-0.1, 0.2)))
            BARK.tube([tuple(b0), tuple(b0 + d * rs.uniform(0.3, 0.9))], [0.035, 0.012], 4, [t, t])
    nb = {2: 13, 1: 11, 0: 9}[lod]
    for k in range(nb):
        t = crown_base + (0.96 - crown_base) * (k + rs.random() * 0.6) / nb
        a = k * 2.39996 + rs.gauss(0, 0.4)
        b0 = Vector((x, y, z0 + H * t)) + lean * H * t
        reach = CRr * rs.uniform(0.55, 1.0) * (1.0 - 0.55 * ((t - crown_base) / (1 - crown_base)) ** 1.5)
        rise = rs.uniform(0.15, 0.45)
        d = Vector((math.cos(a), math.sin(a), 0))
        b1 = b0 + d * reach * 0.55 + Vector((0, 0, reach * rise * 0.5))
        b2 = b0 + d * reach + Vector((0, 0, reach * rise + rs.uniform(-0.3, 0.4)))
        if lod >= 1:
            BARK.tube([tuple(b0), tuple(b1), tuple(b2)], [0.07 + 0.03 * (1 - t), 0.045, 0.018], 5 if lod == 2 else 4, [t, t, t])
        # each branch's foliage plate: needle cards only (opaque masses read as blocks against the sky). Near pines
        # keep the many-card crowns; mid and far pines get fewer, much larger, flatter cards (Scots pine's layered pads)
        npads = {2: 3, 1: 2, 0: 1}[lod]
        for j in range(npads):
            u = 1.0 - j * 0.3
            pc = b0 + (b2 - b0) * u + Vector((rs.gauss(0, 0.25), rs.gauss(0, 0.25), 0.3 + rs.uniform(-0.35, 0.5)))
            pr = CRr * rs.uniform(0.30, 0.40) * (1.0 - 0.15 * j) * {2: 1.25, 1: 1.6, 0: 1.75}[lod]
            pad(CROWNS, pc, pr, crown_c, CRr, rs, {2: 7, 1: 6, 0: 5}[lod], flat=0.5 if lod == 2 else 0.25, lean=d * 0.3,
                up={2: 0.85, 1: 1.6, 0: 1.6}[lod])
    # foliage through the crown's volume, so it reads as one irregular mass with holes rather than separate tufts
    zc0, zc1 = z0 + H * (crown_base + 0.12), z0 + H * 0.93
    nfill = {2: 7, 1: 5, 0: 3}[lod]
    for k in range(nfill):
        a = rs.uniform(0, TWO_PI); rr = CRr * 0.62 * math.sqrt(rs.random())
        zz = zc0 + (zc1 - zc0) * rs.random() ** 0.8
        taper = 1.0 - 0.5 * ((zz - zc0) / max(zc1 - zc0, 0.1)) ** 2
        pc = Vector((x + math.cos(a) * rr * taper, y + math.sin(a) * rr * taper, zz)) + lean * (zz - z0)
        pad(CROWNS, pc, CRr * rs.uniform(0.30, 0.40) * (1.0 if lod == 2 else 1.4), crown_c, CRr, rs, {2: 6, 1: 5, 0: 4}[lod],
            flat=0.55 if lod == 2 else 0.3, up=0.85 if lod == 2 else 1.4)
    # the leader and the topmost cloud
    pad(CROWNS, ctop + Vector((0, 0, 0.1)), CRr * (0.36 if lod == 2 else 0.45), crown_c, CRr, rs, {2: 8, 1: 6, 0: 4}[lod], flat=0.6)

for k, (x, y, H, CRr, lod) in enumerate(PINES):
    pine(x, y, H, CRr * 1.2, lod, 100 + k)

# ----------------------------------------------------------------------------- the shivered fir: stump and splinters round the rim
STUMP = Vector((CR[0], CR[1], 0)) + U_R * (RC + 2.5) + Vector((-U_R.y, U_R.x, 0)) * 9.0
def splinters():
    rs = random.Random(77)
    sx, sy = STUMP.x, STUMP.y; sz = float(gz(sx, sy))
    # the stump: a short trunk, its top torn into long splinters
    BARK.tube([(sx, sy, sz - 0.3), (sx, sy, sz + 1.3)], [0.42, 0.36], 12, [0.0, 0.08])
    me = bpy.data.meshes.new("Splinters"); bm = bmesh.new()
    def shard(p0, p1, w, th):
        d = (Vector(p1) - Vector(p0)); L = d.length; d.normalize()
        sd = d.cross(Vector((0, 0, 1))); sd = sd.normalized() if sd.length > 1e-3 else Vector((1, 0, 0))
        up = sd.cross(d).normalized()
        a = Vector(p0); b = Vector(p1)
        vs = [bm.verts.new(a - sd * w - up * th), bm.verts.new(a + sd * w - up * th), bm.verts.new(a + sd * w * 0.8 + up * th), bm.verts.new(a - sd * w * 0.8 + up * th),
              bm.verts.new(b - sd * w * 0.15), bm.verts.new(b + sd * w * 0.25 + up * th * 0.3)]
        for f in ((0, 1, 2, 3), (0, 4, 5, 1), (1, 5, 2), (2, 5, 4, 3), (3, 4, 0)):
            try: bm.faces.new([vs[i] for i in f])
            except Exception: pass
    for k in range(14):
        a = TWO_PI * k / 14 + rs.gauss(0, 0.1); r = 0.33
        p0 = (sx + math.cos(a) * r * 0.8, sy + math.sin(a) * r * 0.8, sz + 1.2)
        p1 = (sx + math.cos(a) * (r + rs.uniform(0.0, 0.25)), sy + math.sin(a) * (r + rs.uniform(0.0, 0.25)), sz + 1.3 + rs.uniform(0.3, 1.6))
        shard(p0, p1, 0.07, 0.04)
    # pieces flung over the heath and into the pit: logs (bark tubes with splintered ends), slabs, branch ends
    for k in range(34):
        ang = rs.uniform(0, TWO_PI); dist = rs.uniform(2.0, 26.0) ** 1.0
        px = sx + math.cos(ang) * dist; py = sy + math.sin(ang) * dist
        if math.hypot(px - CR[0], py - CR[1]) < RC - 4: continue
        pz = float(gz(px, py))
        L = rs.uniform(0.6, 3.2) * (1.4 if k < 6 else 1.0); yaw = rs.uniform(0, TWO_PI)
        d = Vector((math.cos(yaw), math.sin(yaw), rs.uniform(-0.15, 0.15)))
        a0 = Vector((px, py, pz + 0.05)); a1 = a0 + d * L
        a1.z = float(gz(a1.x, a1.y)) + 0.08
        if k < 12:
            rr = rs.uniform(0.08, 0.2)
            BARK.tube([tuple(a0 + Vector((0, 0, rr * 0.6))), tuple(a1 + Vector((0, 0, rr * 0.6)))], [rr, rr * 0.9], 7, [0.5, 0.5])
            shard(tuple(a1 + Vector((0, 0, rr * 0.6))), tuple(a1 + d * rs.uniform(0.2, 0.6) + Vector((0, 0, rr * 0.5))), rr * 0.8, rr * 0.5)
        else:
            shard(tuple(a0), tuple(a1), rs.uniform(0.05, 0.16), rs.uniform(0.02, 0.06))
        if k % 3 == 0:
            pc = a0 + d * L * 0.7 + Vector((0, 0, 0.35))
            pad(CROWNS, pc, rs.uniform(0.5, 0.8), pc - Vector((0, 0, 0.6)), 1.0, rs, 4, flat=0.4)
    bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Splinters", me); me.materials.append(M_SPLIT); K.link(o)
splinters()

BARK.finish("Bark", M_BARK)
CROWN_OBJ = CROWNS.finish(M_NEEDLES)
# the fallen crown pieces must not sway: zero their weight (they lie on the ground)
cw = CROWN_OBJ.data.color_attributes["Col"].data
for i, v in enumerate(CROWN_OBJ.data.vertices):
    if v.co.z - float(gz(v.co.x, v.co.y)) < 2.0: cw[i].color = (0, 0, 0, 1)

# ----------------------------------------------------------------------------- heather, grass, gorse, bracken
def ground_normal(x, y, e=0.4):
    dzx = float(gz(x + e, y) - gz(x - e, y)) / (2 * e); dzy = float(gz(x, y + e) - gz(x, y - e)) / (2 * e)
    return Vector((-dzx, -dzy, 1)).normalized()

def clump(cm, x, y, w, h, ncards, rs, vi_pool, sink=0.04, tilt=0.35, top=False):
    """Crossed cards round a centre, leaning outward a little so the clump reads as a dome; weights 0 at the base."""
    z = float(gz(x, y)) - sink
    gn = ground_normal(x, y)
    a0 = rs.uniform(0, math.pi)
    for k in range(ncards):
        a = a0 + math.pi * k / ncards + rs.gauss(0, 0.15)
        right = Vector((math.cos(a), math.sin(a), 0))
        outward = Vector((-right.y, right.x, 0)) * rs.choice((-1, 1))
        up = (Vector((0, 0, 1)) + outward * rs.uniform(0.0, tilt)).normalized()
        off = outward * w * rs.uniform(0.0, 0.18)
        ww = w * rs.uniform(0.8, 1.15); hh = h * rs.uniform(0.8, 1.2)
        b = Vector((x, y, z)) + off
        corners = [b - right * ww / 2, b + right * ww / 2, b + right * ww / 2 + up * hh, b - right * ww / 2 + up * hh]
        vi = rs.choice(vi_pool); u0, v0, u1, v1 = atlas_uv(vi)
        if rs.random() < 0.5: u0, u1 = u1, u0
        uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        n_top = (gn * 0.6 + outward * 0.25 + Vector((0, 0, 0.4))).normalized()
        cm.quad(corners, uvs, [gn, gn, n_top, n_top], [0.0, 0.0, 1.0, 1.0])
    if top:
        # a flat-ish card over the top so the dome reads from the reader's height
        rgt = Vector((math.cos(a0), math.sin(a0), 0)); fw = Vector((-rgt.y, rgt.x, 0))
        c = Vector((x, y, z + h * 0.62))
        tl = (fw + Vector((0, 0, 0.5))).normalized()
        corners = [c - rgt * w * 0.45 - tl * w * 0.4, c + rgt * w * 0.45 - tl * w * 0.4, c + rgt * w * 0.45 + tl * w * 0.4, c - rgt * w * 0.45 + tl * w * 0.4]
        vi = rs.choice(vi_pool); u0, v0, u1, v1 = atlas_uv(vi)
        cm.quad(corners, [(u0, v0 + 0.2), (u1, v0 + 0.2), (u1, v1), (u0, v1)], [gn] * 4, [0.7, 0.7, 1.0, 1.0])

HEATHER = CardMesh("veg.shrub.heather"); GRASS = CardMesh("veg.grass.heath")
GORSE = CardMesh("veg.shrub.gorse"); BRACKEN = CardMesh("veg.leaves.bracken")
rs = random.Random(5)
def look_weight(x, y):
    """More detail where the reader looks most (ahead and to the sides), less behind."""
    a = math.degrees(math.atan2(x, y)) - LOOK_AZ
    a = (a + 180) % 360 - 180
    return 1.0 if abs(a) < 110 else 0.55

def mound(mm, x, y, rx, ry, h, rs, seg=8, lump=0.2, tile=1.4):
    """A low opaque lumpy dome sitting in the ground (its foot ring sunk 8 cm): a heather or gorse bush's mass."""
    yaw = rs.uniform(0, TWO_PI); ca, sa = math.cos(yaw), math.sin(yaw)
    ox, oy = rs.uniform(0, 50), rs.uniform(0, 50)
    def uv(q): return ((q.x + 0.35 * q.z) / tile + ox, (q.y + 0.35 * q.z) / tile + oy)
    z0 = float(gz(x, y)); rings = []
    for (rf, hf, off) in ((1.0, 0.0, 0.0), (0.66, 0.62, 0.5)):
        ring = []
        for i in range(seg):
            a = TWO_PI * (i + off) / seg; k = (1 + lump * rs.gauss(0, 1)) * (1.0 if (i % 2 or hf) else 0.8)
            lx, ly = math.cos(a) * rx * rf * k, math.sin(a) * ry * rf * k
            px, py = x + lx * ca - ly * sa, y + lx * sa + ly * ca
            pz = (float(gz(px, py)) - 0.08) if hf == 0 else z0 + h * (0.42 + 0.5 * (i % 2)) * (1 + lump * rs.gauss(0, 1))
            nn = Vector((lx * ca - ly * sa, lx * sa + ly * ca, 0)).normalized() * (0.75 if hf == 0 else 0.55) + Vector((0, 0, 0.6 if hf == 0 else 0.9))
            ring.append((mm.vert(Vector((px, py, pz)), nn, 0.0), Vector((px, py, pz))))
        rings.append(ring)
    tq = Vector((x + rs.gauss(0, rx * 0.2), y + rs.gauss(0, ry * 0.2), z0 + h * (0.8 + lump * abs(rs.gauss(0, 0.8)))))
    vt = mm.vert(tq, (0, 0, 1), 0.0)
    for i in range(seg):
        j = (i + 1) % seg
        (a0, qa0), (a1, qa1) = rings[0][i], rings[0][j]
        (c0, qc0), (c1, qc1) = rings[1][i], rings[1][j]
        mm.face([a0, a1, c0], [uv(qa0), uv(qa1), uv(qc0)])
        mm.face([a1, c1, c0], [uv(qa1), uv(qc1), uv(qc0)])
        mm.face([c0, c1, vt], [uv(qc0), uv(qc1), uv(tq)])

# poisson-ish scatter: jittered grid, density from the masks. Cards only out to ~10 m (the reader's near field, where
# the heather's wiry outline matters), each clump with an opaque lumpy core so three cards read as a full bush; beyond
# that low opaque heather mounds over the heath-painted ground, bigger and sparser with distance. Nothing tall right
# in front of the reader's feet.
counts = {"heather": 0, "grass": 0, "mounds": 0}
NEAR_CARDS = 10.0
for ring_r0, ring_r1, cell in ((0.7, NEAR_CARDS + 1.5, 0.8), (NEAR_CARDS - 0.5, 22.0, 1.8), (22.0, 34.0, 2.6)):
    n = int(2 * ring_r1 / cell)
    for i in range(n):
        for j in range(n):
            x = -ring_r1 + (i + rs.random()) * cell; y = -ring_r1 + (j + rs.random()) * cell
            r = math.hypot(x, y)
            if r < ring_r0 or r >= ring_r1: continue
            near = ring_r0 < 1.0
            # the card / mound hand-over: dithered over 9-11.5 m
            if near and r > NEAR_CARDS - 1.0 and rs.random() < (r - NEAR_CARDS + 1.0) / 2.5: continue
            if not near and ring_r0 < NEAR_CARDS and r < NEAR_CARDS + 1.5 and rs.random() > (r - NEAR_CARDS + 1.0) / 2.5: continue
            if rs.random() > look_weight(x, y): continue
            hd = float(heather_density(x, y))
            if math.hypot(x - CR[0], y - CR[1]) < RC + 1.5: continue
            if any(math.hypot(x - px, y - py) < 0.8 for px, py, _ in PINES_XYR): continue
            ahead_ = abs((math.degrees(math.atan2(x, y)) - LOOK_AZ + 180) % 360 - 180) < 75
            if rs.random() < (hd * 0.95 if near else min(1.0, hd * 1.25)):
                if near:
                    w = rs.uniform(0.52, 0.85) * (0.7 + 0.5 * hd)
                    hh = w * rs.uniform(0.5, 0.72)
                    if r < 2.4 and ahead_: hh *= 0.45 + 0.2 * (r / 2.4)     # low right at the feet, ahead
                    elif r < 1.5: hh *= 0.6
                    if not (r < 1.6 and ahead_):
                        clump(HEATHER, x, y, w, hh, 3, rs, [0, 1, 2, 3] if hd > 0.5 else [1, 3], tilt=0.45)
                    counts["heather"] += 1
                else:
                    continue                                       # the canopy carries the heath out here
                    w = cell * rs.uniform(0.45, 0.65) * (0.7 + 0.4 * hd)
                    mound(HEATHMOUND, x, y, w * rs.uniform(0.95, 1.3), w * rs.uniform(0.75, 1.0), min(0.8, w * rs.uniform(0.45, 0.6)), rs,
                          seg=8 if r < 24 else 6)
                    counts["mounds"] += 1
            elif near and r > 1.2 and rs.random() < 0.35 * (1 - float(sand_cover(x, y))) * (1 - float(track_mask(x, y)) * 0.8):
                g = rs.uniform(0.35, 0.6) * (1 + r / 40) * (0.6 if (r < 2.4 and ahead_) else 1.0)
                clump(GRASS, x, y, g * 0.9, g, 2, rs, [0, 1, 2, 3], sink=0.02, tilt=0.5)
                counts["grass"] += 1
# a fringe of heather cards along the track edges near the reader, softening where the canopy dips to the sand
for pts, hw in TRACKS:
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = math.hypot(bx - ax, by - ay); nx, ny = -(by - ay) / L, (bx - ax) / L
        for k in range(int(L / 0.75)):
            t = (k + rs.random()) * 0.75 / L
            for side in (-1, 1):
                off = hw + rs.uniform(0.35, 0.8)
                x = ax + (bx - ax) * t + nx * off * side; y = ay + (by - ay) * t + ny * off * side
                r = math.hypot(x, y)
                if r < 1.8 or r > NEAR_CARDS or rs.random() < 0.35: continue
                if r < 2.6 and abs((math.degrees(math.atan2(x, y)) - LOOK_AZ + 180) % 360 - 180) < 75: continue
                if math.hypot(x - CR[0], y - CR[1]) < RC + 1.5 or float(sand_cover(x, y)) > 0.5: continue
                if float(track_mask(x, y)) > 0.3: continue
                w = rs.uniform(0.45, 0.75)
                clump(HEATHER, x, y, w, w * rs.uniform(0.5, 0.7), 3, rs, [0, 1, 2, 3], tilt=0.45)
                counts["heather"] += 1
print("heather clumps", counts)

def heath_canopy(mm, r0=1.0, r1=36.0, NS=144, tile=1.4):
    """The heather as one continuous opaque canopy (the bed the near cards rise out of; beyond them, the heath itself): a sheet 0.15-0.5 m over the ground where the
    heather grows (lumpy with fine noise, so its far edge is ragged against the sand), dipping under the ground where
    it doesn't (tracks, sand, the pit) and at its inner and outer edges."""
    rs_ = [r0]
    while rs_[-1] < r1: rs_.append(rs_[-1] + 0.35 + rs_[-1] * 0.03)
    th = np.arange(NS) / NS * TWO_PI
    grid = []
    for k, r in enumerate(rs_):
        jit = np.array([math.sin(i * 2.7 + k * 1.3) for i in range(NS)]) * (TWO_PI * r / NS) * 0.25
        x = r * np.cos(th) + jit * np.sin(th); y = r * np.sin(th) - jit * np.cos(th)
        def cover(px, py): return sstep(0.12, 0.6, heather_density(px, py)) * (1 - 0.85 * sand_cover(px, py))
        # blurred cover (a ring of samples 0.9 m out): the sheet tapers into the ground over a metre or so at the
        # tracks and the sand instead of ending in a cut edge
        cv = cover(x, y) * 0.3
        for q in range(7):
            ang = TWO_PI * q / 7; cv = cv + 0.1 * cover(x + 0.9 * math.cos(ang), y + 0.9 * math.sin(ang))
        taper = np.clip(cv, 0, 1) ** 1.6
        fine = fbm(x / 0.9 + 3, y / 0.9 + 1, 2, seed=31); coarse = fbm(x / 3.0, y / 3.0, 2, seed=32)
        h = (0.12 + 0.24 * coarse + 0.16 * fine) * (0.45 + 0.55 * sstep(6.0, 10.0, r)) + 0.08 * (fine - 0.5)
        h = h * taper * sstep(r0, r0 + 1.2, r) * sstep(r1, r1 - 3.0, r) - 0.06
        z = gz(x, y) + h
        grid.append([mm.vert(Vector((float(a), float(b), float(c))), (0, 0, 1), 0.0) for a, b, c in zip(x, y, z)])
    verts = [v for row in grid for v in row]
    for k in range(len(rs_) - 1):
        for i in range(NS):
            j = (i + 1) % NS
            q = [grid[k][i], grid[k + 1][i], grid[k + 1][j], grid[k][j]]
            mm.face(q, [((v.co.x + 0.35 * v.co.z) / tile, (v.co.y + 0.35 * v.co.z) / tile) for v in q])
    # soft normals from the sheet itself, bent up (a canopy lit from above, not a hard surface)
    mm.bm.normal_update()
    base = len(mm.normals) - len(verts)
    for n_, v in enumerate(verts):
        mm.normals[base + n_] = (v.normal * 0.6 + Vector((0, 0, 0.5))).normalized()
heath_canopy(HEATHMOUND)
# gorse: a few bushes by the tracks and on the knoll behind; an opaque dark core, cards for the spiny outline (the far
# bushes: two cards over a bigger core)
GORSE_AT = [(-3.2, -4.5, 1.5), (2.6, -6.5, 1.2), (5.0, 3.2, 1.0), (-4.5, 3.0, 0.9), (8.0, -12.0, 1.6), (-10.0, -14.0, 1.4),
            (12.5, 9.0, 1.3), (-14.0, -2.0, 1.1), (6.5, 18.0, 1.2), (-2.0, 24.0, 1.0)]
for (x, y, s) in GORSE_AT:
    far_ = math.hypot(x, y) > NEAR_CARDS
    for k in range(3):
        cx, cy = x + rs.gauss(0, s * 0.35), y + rs.gauss(0, s * 0.35)
        w, hh = s * rs.uniform(0.9, 1.3), s * rs.uniform(0.8, 1.1)
        mound(GORSEMOUND, cx, cy, w * (0.42 if far_ else 0.32), w * (0.36 if far_ else 0.28), hh * (0.7 if far_ else 0.55), rs, seg=7, tile=0.9, lump=0.3)
        clump(GORSE, cx, cy, w, hh, 2 if far_ else 4, rs, [0, 1, 2, 3], sink=0.1, tilt=0.45)
# bracken: drifts in the damp hollow ahead and under the pines on the right (40-55 m off: fewer, larger clumps)
for k in range(150):
    if k < 100: x, y = 6 + rs.gauss(0, 9), 50 + rs.gauss(0, 6)
    else: x, y = 28 + rs.gauss(0, 6), 8 + rs.gauss(0, 7)
    if math.hypot(x, y) > NEAR_R - 2: continue
    clump(BRACKEN, x, y, rs.uniform(0.85, 1.3), rs.uniform(0.7, 1.05), 2, rs, [0, 1, 2, 3], sink=0.05, tilt=0.8)
HEATHER.finish(M_HEATHER); GRASS.finish(M_GRASS); GORSE.finish(M_GORSE); BRACKEN.finish(M_BRACKEN)
HEATHMOUND.finish(M_HEATHMOUND, weighted=False); GORSEMOUND.finish(M_GORSEMOUND, weighted=False)

# ----------------------------------------------------------------------------- distant treeline (backdrop cards)
def treeline():
    """One band round the horizon at ~118 m, its foot below the far land."""
    cm = CardMesh("far.treeline")
    NSEG, RR, Hh = 96, 118.0, 12.5
    for i in range(NSEG):
        a0, a1 = TWO_PI * i / NSEG, TWO_PI * (i + 1) / NSEG
        p0 = Vector((math.sin(a0) * RR, math.cos(a0) * RR, 0)); p1 = Vector((math.sin(a1) * RR, math.cos(a1) * RR, 0))
        z0 = float(gz(p0.x * NEAR_R / RR, p0.y * NEAR_R / RR)) - 4.5
        z1 = float(gz(p1.x * NEAR_R / RR, p1.y * NEAR_R / RR)) - 4.5
        nrm = -(p0 + p1).normalized()
        cm.quad([p0 + Vector((0, 0, z0)), p1 + Vector((0, 0, z1)), p1 + Vector((0, 0, z1 + Hh)), p0 + Vector((0, 0, z0 + Hh))],
                [(i / NSEG, 0.0), ((i + 1) / NSEG, 0.0), ((i + 1) / NSEG, 1.0), (i / NSEG, 1.0)], [nrm] * 4, [0, 0, 0, 0])
    return cm.finish(M_TREELINE, weighted=False)
treeline()

# ----------------------------------------------------------------------------- mist (alpha-blended sheets in the pit and the hollow)
def mist_img(N=512):
    u = (np.arange(N) + 0.5) / N; U, V = np.meshgrid(u, u)
    r = np.hypot(U - 0.5, V - 0.5) * 2
    a = sstep(1.0, 0.35, r) * (0.35 + 0.65 * fbm(U * 5, V * 5, 4, seed=61)) * 0.55
    rgba = np.ones((N, N, 4), np.float32); rgba[..., :3] = np.array([0.80, 0.76, 0.72]); rgba[..., 3] = a
    return rgba
M_MIST = K.card_material("M_Mist", K.image_from("T_Mist", mist_img()), rough=1.0, clip=False, blend=True)
def mist_sheet(cx, cy, rx, ry, z, rot):
    cm = CardMesh("Mist")
    R_ = Matrix.Rotation(rot, 3, 'Z')
    pts = [Vector((cx, cy, z)) + R_ @ Vector(p) for p in ((-rx, -ry, 0), (rx, -ry, 0), (rx, ry, 0), (-rx, ry, 0))]
    cm.quad(pts, [(0, 0), (1, 0), (1, 1), (0, 1)], [(0, 0, 1)] * 4, [0] * 4)
    return cm.finish(M_MIST, weighted=False)
mist_sheet(CR[0], CR[1], RC * 0.95, RC * 0.8, float(gz(CR[0], CR[1])) + 1.1, 0.4)
mist_sheet(6.0, 52.0, 26, 13, float(gz(6, 52)) + 0.7, 0.15)
mist_sheet(-8.0, 88.0, 40, 16, float(gz(-8 * 0.8, 88 * 0.8)) + 0.6, -0.2)

# ----------------------------------------------------------------------------- sky dome
def sky_dome(name, radius=SKY_R, seg=64, rings=14):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    els = [SKY_EL0 + (89.0 - SKY_EL0) * (j / rings) ** 1.6 for j in range(rings + 1)]
    grid = []
    for el in els:
        e = math.radians(el)
        grid.append([bm.verts.new((radius * math.cos(e) * math.sin(TWO_PI * i / seg), radius * math.cos(e) * math.cos(TWO_PI * i / seg), radius * math.sin(e))) for i in range(seg + 1)])
    pole = bm.verts.new((0, 0, radius))
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
    o = bpy.data.objects.new(name, me); me.materials.append(M_SKY); K.link(o)
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False; o.visible_transmission = False
    return o
print("painting sky ...")
M_SKY = K.card_material("M_SkyDome", K.image_from("T_SkyDome", gen_sky(4096 if not args.quick else 2048, 1024)), rough=1.0, clip=False, emissive=True, repeat=True)
K.KEEP_UV.add("M_SkyDome")
sky_dome("SkyDome")

# ----------------------------------------------------------------------------- lights
def light_obj(name, kind, energy, color, loc, direction=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if direction is not None: lo.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return K.link(lo)
light_obj("light.sun", 'SUN', 7.0, (1.0, 0.70, 0.42), tuple(SUN_DIR * 30), direction=-SUN_DIR, angle=math.radians(1.0))
skl = light_obj("light.sky", 'SUN', 0.35, (0.62, 0.70, 0.95), (0, 0, 30), direction=(0.15, -0.1, -1.0), angle=math.radians(80))
skl.data.use_shadow = False
world = bpy.data.worlds.new("Dawn"); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]
sk = wn.nodes.new("ShaderNodeTexSky")
try: sk.sky_type = 'MULTIPLE_SCATTERING'
except Exception: sk.sky_type = 'SINGLE_SCATTERING'
try: sk.sun_disc = False
except Exception: pass
sk.sun_elevation = math.radians(SUN_EL); sk.sun_rotation = math.atan2(SUN_DIR.y, SUN_DIR.x) - math.pi / 2
tint = wn.nodes.new("ShaderNodeMix"); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs["Factor"].default_value = 1.0
wn.links.new(sk.outputs["Color"], tint.inputs[6]); tint.inputs[7].default_value = (1.0, 0.86, 0.72, 1)
wn.links.new(tint.outputs[2], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.18

# ----------------------------------------------------------------------------- anchors and living-scene markers
look = az_dir(LOOK_AZ)
anchor("reader.entrance", (0.0, 0.0, float(gz(0, 0))))
anchor("reader.look", (look.x * 2, look.y * 2, EYE))
rim = Vector((CR[0], CR[1], 0)) + U_R * RC
anchor("scene.centre", (rim.x, rim.y, float(gz(rim.x, rim.y))))
anchor("pit.cylinder", tuple(CYL_E))
sm = az_dir(74.0) * 400.0
anchor("heath.smoke", (sm.x, sm.y, 0.0))
marker("sound.birds.0", (13.0, 27.0, 13.0), size=0.5)
marker("sound.birds.1", (-6.0, -9.0, 12.0), size=0.5)
marker("sound.wind-trees.0", (32.0, 6.0, 12.0), size=0.5)

K.apply_all_transforms()

# ----------------------------------------------------------------------------- cameras (reader eye 1.55 m)
E = Vector((0, 0, EYE))
def ahead(yaw_deg, pitch_deg=0.0, d=10.0):
    a = math.radians(LOOK_AZ - yaw_deg); p = math.radians(pitch_deg)
    return tuple(E + Vector((math.sin(a) * math.cos(p), math.cos(a) * math.cos(p), math.sin(p))) * d)
cams = [
    camera("Cam_Reader", tuple(E), ahead(0, -3)),
    camera("Cam_Left", tuple(E), ahead(55, -4)),
    camera("Cam_Right", tuple(E), ahead(-75, 0)),
    camera("Cam_Behind", tuple(E), ahead(180, -6)),
    camera("Cam_Down", tuple(E), ahead(10, -62), lens=16),
    camera("Cam_Pit", tuple(rim + Vector((0, 0, float(gz(rim.x, rim.y)) + 1.6)) + U_R * 2), tuple(CYL_E + Vector((0, 0, 4))), lens=20),
    camera("Cam_Pine", (-3.5, -6.0, 1.5), (-6.0, -9.5, 6.0), lens=18),
]
EXPOSURE = {"Cam_Right": -0.2}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "horsell_sandpits_source.blend"))
K.budget_report()

if args.render:
    K.render_stills(scene, cams, EXPOSURE, default_exp=0.5)

if args.bake or args.export:
    T_ = args.tex
    size_for = {"M_Cylinder": (T_, T_ // 2, T_), "M_Bark": (T_, T_ // 4, T_ // 2), "M_Splinters": (T_ // 4, T_ // 8, T_ // 4)}
    K.bake_and_export(scene, "horsell_sandpits.gltf", size_for,
                      keep_names={"M_SkyDome": "SkyDome", "M_FarLand": "far.land", "M_DistantTrees": "far.treeline", "M_Ground": "MESH_Ground",
                                  "M_PineNeedles": "veg.crown.pines", "M_Heather": "veg.shrub.heather", "M_HeathGrass": "veg.grass.heath",
                                  "M_Gorse": "veg.shrub.gorse", "M_Bracken": "veg.leaves.bracken", "M_Mist": "MESH_Mist",
                                  "M_HeathMound": "MESH_HeathMound", "M_GorseMound": "MESH_GorseMound"},
                      cams=cams, blend_name="horsell_sandpits_baked.blend")
print("DONE")
