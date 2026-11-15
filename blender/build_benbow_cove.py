"""
Fable: the cove below the Admiral Benbow inn, on the Devon coast (Treasure Island, chapters 1-2).

"All day he hung round the cove, or upon the cliffs, with a brass telescope ..."
"... the cove all grey with hoar-frost, the ripple lapping softly on the stones, the sun still low and only touching
the hilltops and shining far to seaward." (chapter 2)
"... still looking about him at the cliffs and up at our signboard." "... as he turned the big rock" (chapters 1-2)

The moment: a January morning just after sunrise, frosty, clear and still but for a cold breath off the land. The sun
has only just cleared the eastern headland: the whole cove lies in its blue shadow, the frost still grey on the
shingle and the grass, while the tops of the western cliffs and the sea far out beyond the headlands are lit. The tide
is half out. No person, animal or ship is modelled.

What is here: the reader stands on the shingle a few paces above the water's edge, facing out of the cove to sea (+Y).
Shingle at the feet (rounded cobbles in slate grey, buff sandstone and white quartz, rimed with frost above the tide
line, wet and dark below it, a line of wrack); the storm ridge and a grass bank behind; cliffs of grey bedded slate
and sandstone on both hands (ledges, joints, a wave-cut notch, the black-lichen and barnacle bands of a real shore,
yellow lichen above, fallen blocks at their feet); the big rock at the turn of the beach on the right; the two
headlands framing the open sea. Behind, up the combe: the path to the Admiral Benbow, a long whitewashed inn with a
slate roof and its signboard by the coast road, gorse and dead bracken on the slopes.

Living scene (docs/LIVING_SCENES.md): water.ocean.cove (vertex colour G = foam at the shore and the rocks),
veg.grass.coarse (R = sway weight, root 0 to tip 1), veg.shrub.gorse, sound.surf.shore, sound.surf.rock,
sound.gulls.cliffs, sound.wind.combe.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet on the shingle (z = 0)
  anchor.reader.look      eye height 1.55 m, 1 m out to sea (+Y)
  anchor.scene.centre     the middle of the beach at the water's edge
  anchor.cove.bigRock, anchor.cove.inn, anchor.cove.signboard
  light.sun (SUN, just risen in the east-south-east, ~5 degrees up), light.sky (SUN, cool shadowless fill)
  SkyDome (unlit backdrop, baked emission), far.land (country beyond ~70 m: backdrop)
Register as Outdoor in FableBuild.

Axes: metres, Blender +Z up, +Y out to sea (south), -X east (the sun's side), +X west.

Run headless (one Blender at a time):
  blender -b -P blender/build_benbow_cove.py -- --out out/benbow-cove --render --quick --res 640
  blender -b -P blender/build_benbow_cove.py -- --out out/benbow-cove --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, treasure_kit as K
importlib.reload(K)
from treasure_kit import F, smooth, lerp, fbm, new_mat, plain, noisy, box, cyl, mesh_obj, from_pydata, Builder, anchor, \
    living_empty, light_obj, camera, sharpen_by_angle, rock_piece

args = K.parse_args("out/benbow-cove")
OUT = args.out
scene, COLL = K.reset_scene("BenbowCove", args, bounces=6, diffuse=4)
random.seed(1754)

# ----------------------------------------------------------------------------- dimensions
EYE = 1.55
SL = -0.95                      # sea level (half tide)
R_FAR = 145.0
SKY_R = 148.0
_az, _el = math.radians(122.0), math.radians(6.5)      # sun bearing from north, elevation
SUN_DIR = Vector((-math.sin(_az) * math.cos(_el), -math.cos(_az) * math.cos(_el), math.sin(_el))).normalized()
DIP = 0.62                      # the slate beds dip steeply along the coast (folded Devonian slate)

def ys(x):
    """the water's edge (y) across the cove"""
    return 5.0 + 0.010 * x * x + 0.6 * math.sin(x / 7.0 + 0.5)

def spline(keys, t):
    if t <= keys[0][0]: return keys[0][1]
    if t >= keys[-1][0]: return keys[-1][1]
    for i in range(len(keys) - 1):
        if keys[i][0] <= t <= keys[i + 1][0]: break
    p0 = keys[max(0, i - 1)]; p1 = keys[i]; p2 = keys[i + 1]; p3 = keys[min(len(keys) - 1, i + 2)]
    u = (t - p1[0]) / (p2[0] - p1[0])
    m1 = (p2[1] - p0[1]) / (p2[0] - p0[0]) * (p2[0] - p1[0])
    m2 = (p3[1] - p1[1]) / (p3[0] - p1[0]) * (p2[0] - p1[0])
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * p1[1] + (u3 - 2 * u2 + u) * m1 + (-2 * u3 + 3 * u2) * p2[1] + (u3 - u2) * m2

CE_KEYS = [(-150, -26), (-60, -22), (-14, -21), (0, -27), (15, -33), (40, -35), (62, -28), (80, -24), (97, -33), (122, -55), (170, -95)]
CW_KEYS = [(-150, 21), (-60, 18), (-14, 18), (0, 24.5), (12, 28.0), (35, 33), (58, 31), (79, 26), (99, 35), (126, 60), (170, 100)]
def cE(y): return spline(CE_KEYS, y)
def cW(y): return spline(CW_KEYS, y)
def out_d(x, y):
    """lateral distance outside the cove's rock line (positive inside the cliffs / on the plateau)"""
    return max(cE(y) - x, x - cW(y))
def plateau(x, y):
    """the top of the land: the downs above the cove"""
    if x < 0: p = 30.0 + 8.0 * smooth(-20, 60, y) + 2.5 * math.sin(y / 23.0)
    else: p = 34.0 + 12.0 * smooth(0, 70, y) + 2.5 * math.sin(y / 19.0 + 1.0)
    p += 4.0 * smooth(-20, -110, y)
    return p + 2.0 * noise.noise(Vector((x * 0.03, y * 0.03, 4.2)))
def rock_top(x, y):
    """the height of the bare rock cliff; above it a steep slope of grass, bracken and gorse rises to the downs"""
    if x < 0: r = 16.0 + 8.0 * smooth(-4, 30, y) + 4.0 * smooth(45, 75, y)
    else: r = 18.0 + 10.0 * smooth(-4, 25, y) + 7.0 * smooth(40, 75, y)
    return r + 3.0 * noise.noise(Vector((y * 0.06, x * 0.01, 8.8)))
def lean(y, side):
    return 0.20 + 0.08 * noise.noise(Vector((y * 0.04, side * 3.0, 1.0)))
ZB_REF = SL - 1.0
def edge_out(x, y):
    side = -1 if x < 0 else 1
    return lean(y, side) * (rock_top(x, y) - ZB_REF) + 0.8

def path_x(y): return -7.0 * smooth(-10, -55, y) + 1.4 * math.sin(y / 9.0) * smooth(-6, -14, y)
def road_y(x): return -50.5 - 0.06 * x - 0.0025 * x * x

def z_cove(x, y):
    d = ys(x) - y
    if d < 0:
        z = SL - 1.7 * (1 - math.exp(d / 5.0)) - 0.05 * (-d)
    else:
        z = SL + 0.19 * min(d, 9.6) - 0.10 * max(0.0, d - 10.6) - 0.004 * max(0.0, d - 9.6) ** 2
    # the inland floor of the combe, rising to the inn
    zin = 0.62 + 0.21 * max(0.0, -9.0 - y) + 0.25 * math.sin(y / 6.0 + x / 9.0) * smooth(-9, -14, y)
    z = max(z, zin) if y < -3 else z
    # small rolls of the shingle and the bank
    z += 0.05 * noise.noise(Vector((x * 0.35, y * 0.35, 0.5))) + 0.02 * noise.noise(Vector((x * 1.3, y * 1.3, 1.5)))
    return z

def h(x, y):
    zc = z_cove(x, y)
    o = out_d(x, y)
    P = plateau(x, y)
    # inland: grassy combe sides
    warp = 6.0 * noise.noise(Vector((y * 0.035, 0.5, 3.3))) + 3.0 * noise.noise(Vector((y * 0.1, x * 0.05, 6.1)))
    w0, w1 = (-15.0, 40.0) if x < 0 else (-11.0, 28.0)
    sl = smooth(w0 + warp, w1 + warp, o)
    zi = zc + (P - zc) * (0.55 * sl ** 1.25 + 0.45 * sl ** 2.2)
    # a shelf (an old field) part way up each side
    zi -= 2.0 * math.exp(-((o - (6.0 if x < 0 else 2.0)) / 5.0) ** 2) * smooth(-14, -30, y)
    # the cove: shingle to the cliff foot (a little talus), then the hidden ramp behind the cliff sheet
    if o < 0:
        zk = zc + 0.5 * smooth(-3.5, 0.0, o)
    else:
        E = edge_out(x, y); Rt = rock_top(x, y)
        zk = zc + 0.5 + (Rt - zc - 0.5) * smooth(1.8, E + 2.5, o) ** 4.0
        if o > E: zk = Rt + max(0.0, P - Rt) * smooth(E, E + 22.0 + 8.0 * noise.noise(Vector((y * 0.05, 1.0, 2.0))), o) ** 0.85
    k = smooth(-15.0, -4.0, y)
    z = lerp(zi, zk, k)
    # relief on the plateau and slopes
    z += 1.6 * fbm(Vector((x * 0.05, y * 0.05, 2.0)), 3) * smooth(-6, 10, o) + 0.35 * noise.noise(Vector((x * 0.18, y * 0.18, 7.0))) * smooth(-10, 2, o)
    z += 0.7 * noise.noise(Vector((x * 0.14, y * 0.14, 9.0))) * smooth(-10, 0, o) * (1.0 - smooth(-8, -2, y))
    # spurs and runnels down the slopes
    z += 1.2 * noise.noise(Vector((x * 0.03, y * 0.11, 5.5))) * smooth(-8, 8, o) * (1.0 - smooth(-6, 2, y))
    return z

# ----------------------------------------------------------------------------- materials
def ground_mat(name, level):
    """The cove floor: shingle (rounded cobbles of slate, sandstone, quartz) frosted above the tide and wet below it,
    a wrack line, the storm ridge, then the winter turf, dead bracken and gorse of the combe, the path and the road."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    d = 5.0 + 0.010 * x * x + 0.6 * (x / 7.0 + 0.5).sin() - y
    nlo, _ = g.noise(P, 0.06, 3)
    nmid, _ = g.noise(P, 0.5, 5)
    nhi, _ = g.noise(P, 4.0, 4)
    nz = g.nz()
    # --- shingle: rounded stones lying over one another (three layers of discs, the top one wins), grit between
    pn, _ = g.noise(P, 90.0, 3)
    grit = g.ramp(pn, [(0.3, (0.03, 0.029, 0.027)), (0.7, (0.085, 0.08, 0.072))])
    shing = grit
    dome = F(g, g.ss(pn, 0.0, 1.0).s) * 0.15
    PEB = [(0.085, (0.085, 0.087, 0.09)), (0.2, (0.12, 0.125, 0.13)), (0.36, (0.16, 0.16, 0.155)), (0.5, (0.25, 0.215, 0.165)),
           (0.62, (0.19, 0.165, 0.14)), (0.72, (0.27, 0.205, 0.18)), (0.86, (0.36, 0.355, 0.34)), (1.0, (0.07, 0.07, 0.07))]
    for k, (sc, off) in enumerate(((11.0, (0.0, 0.0)), (15.0, (3.1, 7.7)), (21.0, (5.3, 1.9)))):
        q = g.stretch(g.comb(x + off[0], y + off[1], z * 0.3 + k * 2.0), 1.0, 1.35, 1.0)
        f1, cc, _pp = g.vor(q, sc, out="all")
        cr, cg, cb = g.sep(cc)
        rk = 0.36 + cb * 0.16
        t = (f1 / rk).min(1.0)
        hk = (1.0 - t * t).max(0.0).sqrt()
        mk = 1.0 - g.ss(t, 0.82, 1.0)
        ck = g.ramp(cr, PEB, 'CONSTANT')
        ck = g.mul(ck, g.comb(0.8 + cg * 0.4, 0.8 + cg * 0.4, 0.8 + cg * 0.4))
        ck = g.mul(ck, g.comb(0.7 + hk * 0.3, 0.7 + hk * 0.3, 0.7 + hk * 0.3))      # darker towards each stone's rim
        shing = g.mix(mk, shing, ck)
        dome = g.lerp(mk, dome, hk * (1.0 + k * 0.15))
    gap = 1.0 - g.ss(dome, 0.02, 0.25)
    if level in ('mid', 'far'):
        shing = g.ramp(nhi * 0.5 + nmid * 0.5, [(0.3, (0.12, 0.115, 0.11)), (0.55, (0.17, 0.16, 0.145)), (0.8, (0.21, 0.19, 0.165))])
    # wet below the swash line, frost above the last tide
    wet = 1.0 - g.ss(d, 0.7 + nmid * 0.6, 2.1 + nmid * 0.8)
    under = 1.0 - g.ss(z, SL - 0.06, SL + 0.03)
    frost = g.ss(d, 3.4 + nmid * 0.8, 4.4 + nmid * 0.8)
    fr_amt = 0.15 if level in ('mid', 'far') else 0.22
    shing = g.mix(frost * (fr_amt + g.ss(dome, 0.4, 1.0) * 0.28) * nz.max(0.0), shing, (0.48, 0.50, 0.54))
    shing = g.mul(shing, g.comb(1.0 - wet * 0.45, 1.0 - wet * 0.43, 1.0 - wet * 0.4))
    # the wrack line: broken weed and sticks, dark olive
    wr = (1.0 - g.ss((d - 3.1 - nmid * 0.5).abs(), 0.05, 0.35 + nhi * 0.2)) * g.ss(nhi * 0.7 + nmid * 0.3, 0.42, 0.55)
    shing = g.mix(wr * 0.85, shing, g.ramp(nhi, [(0.3, (0.035, 0.03, 0.012)), (0.7, (0.09, 0.07, 0.03))]))
    seabed = g.ramp(nmid, [(0.3, (0.07, 0.07, 0.06)), (0.7, (0.12, 0.11, 0.09))])
    shing = g.mix(under, shing, seabed)
    # --- turf of the combe in winter: olive, straw, frosted
    turf = g.ramp(nmid * 0.6 + nhi * 0.4, [(0.25, (0.06, 0.075, 0.03)), (0.45, (0.10, 0.105, 0.045)), (0.62, (0.18, 0.155, 0.085)), (0.8, (0.26, 0.21, 0.12))])
    if level in ('feet', 'near'):
        fine, _ = g.noise(P, 30.0, 3)
        turf = g.mul(turf, g.ramp(fine, [(0.3, (0.75, 0.75, 0.75)), (0.7, (1.15, 1.12, 1.05))]))
    slope = 1.0 - g.ss(nz, 0.8, 0.95)
    nb, _ = g.noise(P, 0.11, 6, 0.62, 0.3)
    bracken = g.ss(nb * 0.8 + nhi * 0.2, 0.50, 0.53) * (0.35 + 0.65 * slope)
    brc = g.ramp(nhi * 0.6 + nmid * 0.4, [(0.25, (0.12, 0.07, 0.04)), (0.55, (0.19, 0.11, 0.06)), (0.8, (0.25, 0.16, 0.09))])
    turf = g.mix(bracken * 0.8, turf, brc)
    ng, _ = g.noise(g.comb(x + 40.0, y, z), 0.32, 5, 0.6, 0.4)
    gorse = g.ss(ng, 0.62, 0.65) * (0.3 + 0.7 * slope)
    turf = g.mix(gorse * 0.9, turf, g.ramp(nhi, [(0.3, (0.025, 0.04, 0.015)), (0.7, (0.05, 0.07, 0.025))]))
    # terracettes: the sheep-trodden steps along the contours of steep slopes
    terr = ((z * (2 * math.pi / 0.85) + nmid * 3.0).sin() * 0.5 + 0.5)
    turf = g.mix(g.ss(terr, 0.75, 0.95) * slope * 0.35, turf, (0.20, 0.18, 0.12))
    frs, _ = g.noise(P, 2.2, 4)
    turf = g.mix(g.ss(frs, 0.35, 0.75) * 0.28 * (1.0 - g.ss(z, 28.0, 40.0)) * (1.0 - bracken * 0.6), turf, (0.40, 0.42, 0.45))   # hoar-frost in the shade, patchy
    rock_out = (1.0 - g.ss(nz, 0.5, 0.68)) * g.ss(nmid, 0.45, 0.55)
    turf = g.mix(rock_out * 0.9, turf, g.ramp(nhi, [(0.3, (0.10, 0.095, 0.09)), (0.7, (0.19, 0.18, 0.16))]))
    # --- where the shingle gives way to turf: the storm ridge's back, the combe floor
    o_ish = x.abs() - 18.0
    grassm = g.ss(d, 10.8 + nmid * 2.0, 13.0 + nmid * 2.0).max(g.ss(z, 3.0 + nmid * 2.0, 5.0 + nmid * 2.0))
    col = g.mix(grassm, shing, turf)
    # --- the path up from the beach to the inn, and the coast road
    px_ = -7.0 * g.ss(-y, 10.0, 55.0) + 1.4 * (y / 9.0).sin() * g.ss(-y, 6.0, 14.0)
    pd = (x - px_).abs()
    pathm = (1.0 - g.ss(pd, 0.45 + nhi * 0.2, 0.75 + nhi * 0.25)) * g.ss(-y, 9.0, 11.5) * (1.0 - g.ss(-y, 54.0, 56.0))
    mud = g.ramp(nhi * 0.6 + nmid * 0.4, [(0.3, (0.10, 0.08, 0.06)), (0.55, (0.15, 0.12, 0.09)), (0.8, (0.25, 0.23, 0.22))])
    mud = g.mix(g.ss(nhi, 0.55, 0.65) * 0.6, mud, (0.45, 0.46, 0.48))
    col = g.mix(pathm, col, mud)
    ry = -50.5 - 0.06 * x - 0.0025 * x * x
    rd = (y - ry).abs()
    roadm = 1.0 - g.ss(rd, 1.5 + nhi * 0.3, 2.0 + nhi * 0.3)
    rut = 1.0 - g.ss((rd - 0.75).abs(), 0.05, 0.18)
    roadc = g.mix(rut * 0.5, mud, (0.07, 0.06, 0.05))
    col = g.mix(roadm, col, roadc)
    if level == 'far':
        r = (x * x + y * y).sqrt()
        col = g.mix(g.ss(r, 70.0, 145.0) * 0.35, col, (0.30, 0.33, 0.37))
    if level in ('feet', 'near'):
        col = g.mul(col, g.ao(0.3), 0.5)
    g.set(b.inputs["Base Color"], col)
    rough = 0.86 - wet * (1.0 - grassm) * 0.55 - frost * 0.06
    g.set(b.inputs["Roughness"], rough)
    b.inputs["Specular IOR Level"].default_value = 0.4
    hgt = (dome * 1.0 - gap * 0.6) * (1.0 - grassm) + nhi * 0.3 + pathm * nhi * 0.3 - rut * roadm * 0.4
    if level == 'feet': g.bump(b, hgt, 1.0, 0.04)
    elif level == 'near': g.bump(b, hgt + gorse * 0.8 + bracken * nhi * 0.5, 0.6, 0.03)
    else: g.bump(b, nhi * 0.5 + nmid * 0.5 + gorse * 1.0 + terr * slope * 0.4, 0.3, 0.1)
    return m

def rock_mat(name, detail=1.0):
    """Grey bedded slate and sandstone of the south Devon shore: beds of different stone and hardness, iron stains,
    rain streaks; the zones of a real shore (wrack and green weed at the foot, barnacles, the black lichen band,
    grey and yellow lichens above); hoar-frost on the upward faces in the shade."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    nz = g.nz()
    n1, _ = g.noise(P, 0.35, 5, 0.6, 0.4)
    n2, _ = g.noise(P, 3.0, 5)
    n3, _ = g.noise(P, 18.0 * detail, 4)
    bed = z + y * DIP + n1 * 1.2
    bi = (bed / 1.3).floor()
    bh, _ = g.white(g.comb(bi, 0.37, 1.7))
    bedc = g.ramp(bh, [(0.0, (0.14, 0.135, 0.13)), (0.25, (0.17, 0.16, 0.15)), (0.45, (0.20, 0.18, 0.155)), (0.62, (0.155, 0.155, 0.158)),
                      (0.78, (0.215, 0.19, 0.155)), (0.9, (0.18, 0.15, 0.115))], 'CONSTANT')
    bedc = g.mix(g.ss(n2, 0.3, 0.7) * 0.5, bedc, (0.165, 0.158, 0.15))
    lam = ((bed * (2 * math.pi / 0.09)).sin() * 0.5 + 0.5)
    col = g.mul(bedc, g.ramp(n2 * 0.6 + lam * 0.4, [(0.2, (0.72, 0.72, 0.72)), (0.5, (1.0, 1.0, 1.0)), (0.85, (1.25, 1.22, 1.18))]))
    # cracks (joints) and rain streaks
    cr = g.vor(g.stretch(P, 1.0, 1.0, 0.45), 1.6, feature='DISTANCE_TO_EDGE')
    crack = 1.0 - g.ss(cr, 0.0, 0.035)
    streak, _ = g.noise(g.stretch(P, 9.0, 9.0, 0.35), 1.0, 3)
    col = g.mul(col, g.ramp(streak, [(0.35, (0.70, 0.69, 0.68)), (0.6, (1.0, 1.0, 1.0))]), 0.6)
    iron = g.ss(n2 * 0.6 + bh * 0.4, 0.68, 0.78)
    col = g.mix(iron * 0.3, col, (0.22, 0.13, 0.07))
    # shore zones
    zr = z - SL
    wrack = 1.0 - g.ss(zr, 0.15 + n2 * 0.4, 0.55 + n2 * 0.4)
    barn = (1.0 - g.ss(zr, 0.8 + n2 * 0.3, 1.2 + n2 * 0.3)) * g.ss(zr, -0.1, 0.25)
    blk = (1.0 - g.ss(zr, 2.2 + n1 * 1.2, 2.8 + n1 * 1.2)) * g.ss(zr, 0.9, 1.3)
    above = g.ss(zr, 2.8, 4.0)
    spots = 1.0 - g.ss(g.vor(P, 9.0 * detail), 0.04, 0.12 + n2 * 0.1)
    col = g.mix(blk * 0.6, col, g.ramp(n3, [(0.3, (0.035, 0.035, 0.03)), (0.7, (0.075, 0.075, 0.065))]))
    bar = 1.0 - g.ss(g.vor(P, 70.0 * detail), 0.06, 0.2)
    col = g.mix(barn * (0.35 + bar * 0.5), col, (0.42, 0.40, 0.35))
    col = g.mix(wrack * 0.9, col, g.ramp(n3 * 0.5 + n2 * 0.5, [(0.3, (0.03, 0.03, 0.012)), (0.6, (0.07, 0.06, 0.02)), (0.8, (0.04, 0.07, 0.02))]))
    lgrey = above * g.ss(n2 * 0.7 + n1 * 0.3, 0.5, 0.6) * (0.35 + nz.max(0.0) * 0.5)
    col = g.mix(lgrey * 0.7, col, (0.36, 0.37, 0.33))
    lyel = above * spots * g.ss(n1 * 0.6 + n3 * 0.4, 0.5, 0.62) * (1.0 - g.ss(z, 22.0, 34.0) * 0.5)
    col = g.mix(lyel * 0.8, col, (0.42, 0.24, 0.035))
    # ledge growth (thrift and grass on up-facing ledges) and frost on up-facing rock in the shade
    up = g.ss(nz, 0.55, 0.85) * above
    col = g.mix(up * g.ss(n2, 0.45, 0.6) * 0.8, col, (0.07, 0.075, 0.035))
    col = g.mix(up * 0.45 * (1.0 - g.ss(z, 20.0, 30.0)), col, (0.48, 0.50, 0.53))
    col = g.mix(crack * 0.7, col, (0.025, 0.024, 0.022))
    col = g.mul(col, g.ao(0.6), 0.45)
    g.set(b.inputs["Base Color"], col)
    wet = 1.0 - g.ss(zr, 0.6, 1.4)
    g.set(b.inputs["Roughness"], 0.84 - wet * 0.5 + n3 * 0.08)
    b.inputs["Specular IOR Level"].default_value = 0.45
    hgt = n2 * 0.4 + n3 * 0.35 - crack * 0.6 + lam * 0.15 + bar * barn * 0.3
    g.bump(b, hgt, 0.7, 0.03)
    return m

def cobble_mat(name):
    """Rounded beach cobbles, each its own stone (tint), frosted on top above the tide."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    at = g.attr("tint")
    n1, _ = g.noise(P, 12.0, 4)
    n2, _ = g.noise(P, 60.0, 3)
    col = g.mul(at.outputs["Color"], g.ramp(n1 * 0.6 + n2 * 0.4, [(0.3, (0.8, 0.8, 0.8)), (0.7, (1.15, 1.12, 1.08))]))
    vein = 1.0 - g.ss(g.vor(g.stretch(P, 1, 1, 4), 6.0, feature='DISTANCE_TO_EDGE'), 0.0, 0.01)
    col = g.mix(vein * F(g, at.outputs["Alpha"]) * 0.6, col, (0.55, 0.53, 0.50))
    nz = g.nz()
    d = 5.0 + 0.010 * x * x + 0.6 * (x / 7.0 + 0.5).sin() - y
    frost = g.ss(d, 3.4, 4.4) * g.ss(nz, 0.3, 0.8)
    col = g.mix(frost * 0.45, col, (0.50, 0.52, 0.56))
    wet = 1.0 - g.ss(d, 0.7, 2.1)
    col = g.mul(col, g.comb(1.0 - wet * 0.45, 1.0 - wet * 0.43, 1.0 - wet * 0.4))
    col = g.mul(col, g.ao(0.12), 0.6)
    g.set(b.inputs["Base Color"], col)
    g.set(b.inputs["Roughness"], 0.6 + n2 * 0.15 - wet * 0.35)
    g.bump(b, n2 * 0.5 + n1 * 0.5, 0.25, 0.004)
    return m

def grass_mat(name):
    """Coarse winter grass: olive at the root, straw and grey frost at the tips (the 'Color' R weight is height)."""
    m, nt, b, g = new_mat(name)
    at = g.attr("tint"); wt = g.attr("Color")
    t = F(g, g.sep(wt.outputs["Color"])[0].s)
    n1, _ = g.noise(g.pos(), 9.0, 3)
    base = g.mul(at.outputs["Color"], g.ramp(n1, [(0.3, (0.8, 0.8, 0.8)), (0.7, (1.15, 1.1, 1.05))]))
    col = g.mix(g.ss(t, 0.2, 0.9) * 0.8, g.mul(base, (0.75, 0.75, 0.7)), (0.36, 0.31, 0.19))
    col = g.mix(g.ss(t, 0.5, 1.0) * F(g, at.outputs["Alpha"]) * 0.5, col, (0.55, 0.57, 0.60))
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.8
    b.inputs["Sheen Weight"].default_value = 0.2
    b.inputs["Subsurface Weight"].default_value = 0.0
    return m

def gorse_mat(name):
    m, nt, b, g = new_mat(name)
    P = g.pos()
    n1, _ = g.noise(P, 6.0, 4, 0.6, 0.4)
    n2, _ = g.noise(P, 45.0, 3)
    col = g.ramp(n1 * 0.6 + n2 * 0.4, [(0.3, (0.04, 0.06, 0.025)), (0.55, (0.07, 0.10, 0.04)), (0.8, (0.12, 0.14, 0.06))])
    fl = (1.0 - g.ss(g.vor(P, 40.0), 0.05, 0.13)) * g.ss(n1, 0.5, 0.62)
    col = g.mix(fl * 0.9, col, (0.62, 0.42, 0.03))
    nz = g.nz()
    col = g.mix(g.ss(nz, 0.3, 0.9) * 0.45, col, (0.45, 0.47, 0.50))
    col = g.mul(col, g.ao(0.25), 0.6)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.8
    g.bump(b, n2, 0.6, 0.02)
    return m

def sea_mat(name):
    """For the Blender stills only (Unity animates its own water): a cold grey-green sea, the sky in it, foam where
    the mesh's vertex colour G says."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    wt = g.attr("Color"); _, foam, _ = g.sep(wt.outputs["Color"])
    n1, _ = g.noise(g.stretch(P, 0.25, 1.0, 1.0), 0.8, 4)
    n2, _ = g.noise(P, 6.0, 3)
    r = (x * x + y * y).sqrt()
    col = g.ramp(g.ss(r, 6.0, 40.0), [(0.0, (0.035, 0.05, 0.045)), (1.0, (0.012, 0.022, 0.026))])
    fm = foam * g.ss(n2 * 0.6 + n1 * 0.4 + foam * 0.4, 0.7, 0.85) * 0.8
    col = g.mix(fm, col, (0.55, 0.57, 0.57))
    g.set(b.inputs["Base Color"], col)
    g.set(b.inputs["Roughness"], 0.045 + fm * 0.6)
    b.inputs["IOR"].default_value = 1.33
    swell = (y * (2 * math.pi / 7.0) + n1 * 4.0).sin()
    n4, _ = g.noise(g.stretch(P, 0.6, 1.4, 1.0), 2.5, 3)
    g.bump(b, swell * 0.5 + n1 * 0.6 + n4 * 0.5 + n2 * 0.15, 0.45, 0.05)
    return m

def sky_nodes(g, dvec):
    """A clear January dawn: the sun just up in the east-south-east with a warm glow along that horizon, a cold clear
    blue overhead, the pink belt and blue-grey earth shadow opposite, a few thin streaks of cirrus to the south-west."""
    dx, dy, el = g.sep(dvec)
    base = g.ramp(g.ss(el, -0.02, 0.95), [(0.0, (0.50, 0.52, 0.55)), (0.03, (0.46, 0.52, 0.60)), (0.12, (0.30, 0.40, 0.58)),
                                         (0.4, (0.13, 0.24, 0.48)), (1.0, (0.07, 0.15, 0.38))])
    sd = g.n("ShaderNodeVectorMath", operation='DOT_PRODUCT'); g.set(sd.inputs[0], dvec); sd.inputs[1].default_value = tuple(SUN_DIR)
    sdot = F(g, sd.outputs["Value"])
    low = 1.0 - g.ss(el, 0.0, 0.35)
    glow = g.ss(sdot, 0.35, 1.0)
    col = g.mix(glow * glow * low * 0.9, base, (1.15, 0.78, 0.45))
    col = g.mix(g.ss(sdot, 0.93, 1.0) * 0.8, col, (1.6, 1.25, 0.85))
    anti = g.ss(-sdot, 0.3, 0.95)
    belt = g.ss(el, 0.025, 0.06) * (1.0 - g.ss(el, 0.10, 0.2))
    col = g.mix(anti * belt * 0.45, col, (0.62, 0.48, 0.52))
    shadow = 1.0 - g.ss(el, 0.0, 0.03)
    col = g.mix(anti * shadow * 0.5, col, (0.33, 0.38, 0.47))
    disc = g.ss(sdot, 0.99965, 0.99985)
    col = g.mix(disc, col, (40.0, 30.0, 18.0))
    zk = el.max(0.0) + 0.08
    px, py = dx / zk, dy / zk
    ci, _ = g.noise(g.comb(px * 0.25 + 3.0, py * 1.4 + 1.0, 0.3), 1.0, 5, 0.6, 0.5)
    cover = g.ss(ci, 0.60, 0.74) * g.ss(dx, 0.1, 0.5) * g.ss(el, 0.04, 0.12) * (1.0 - g.ss(el, 0.35, 0.6))
    col = g.mix(cover * 0.45, col, g.mix(glow, (0.80, 0.78, 0.80), (1.1, 0.85, 0.65)))
    below = 1.0 - g.ss(el, -0.01, 0.0)
    col = g.mix(below, col, (0.22, 0.25, 0.28))
    return col

def sky_dome_mat(name="M_SkyDome"):
    m, nt, b, g = new_mat(name)
    nv = g.n("ShaderNodeVectorMath", operation='NORMALIZE'); g.set(nv.inputs[0], g.pos())
    col = sky_nodes(g, nv.outputs[0])
    g.set(b.inputs["Emission Color"], col); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m

def whitewash_mat(name):
    """Limewashed rubble walls of the inn: off-white, greyed and green-streaked by weather, the stone showing through."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    n1, _ = g.noise(P, 1.5, 5)
    n2, _ = g.noise(P, 12.0, 4)
    st = 1.0 - g.ss(g.vor(g.stretch(P, 1, 1, 1.8), 5.0, feature='DISTANCE_TO_EDGE'), 0.0, 0.05)
    col = g.ramp(n1, [(0.3, (0.48, 0.47, 0.43)), (0.6, (0.60, 0.59, 0.55)), (0.8, (0.66, 0.65, 0.61))])
    col = g.mix(g.ss(n2 * 0.6 + n1 * 0.4, 0.62, 0.72) * 0.6, col, (0.25, 0.23, 0.20))
    streak, _ = g.noise(g.stretch(P, 6.0, 6.0, 0.4), 1.0, 3)
    col = g.mul(col, g.ramp(streak, [(0.35, (0.72, 0.74, 0.68)), (0.6, (1, 1, 1))]), 0.7)
    col = g.mix(st * 0.25, col, (0.30, 0.29, 0.27))
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.92
    g.bump(b, n2 * 0.5 - st * 0.5, 0.4, 0.02)
    return m

def slate_roof_mat(name):
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    br = g.n("ShaderNodeTexBrick", offset=0.5)
    g.set(br.inputs["Vector"], g.comb(x + y * 0.0, z * 1.35, 0.0))
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 0.30; br.inputs["Row Height"].default_value = 0.13
    br.inputs["Mortar Size"].default_value = 0.008
    br.inputs["Color1"].default_value = (0.85, 0.85, 0.86, 1); br.inputs["Color2"].default_value = (1.1, 1.08, 1.06, 1)
    br.inputs["Mortar"].default_value = (0.3, 0.3, 0.3, 1)
    n1, _ = g.noise(P, 1.2, 5)
    col = g.mul(g.ramp(n1, [(0.3, (0.075, 0.08, 0.09)), (0.7, (0.12, 0.125, 0.13))]), br.outputs["Color"])
    col = g.mix(g.ss(n1, 0.6, 0.7) * 0.5, col, (0.30, 0.29, 0.20))
    col = g.mix(0.35, col, (0.44, 0.46, 0.49))                       # frost on the roof in the shade
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.6
    g.bump(b, F(g, br.outputs["Fac"]) * -1.0, 0.5, 0.01)
    return m

M_FEET = ground_mat("M_ShingleFeet", 'feet')
M_GNEAR = ground_mat("M_GroundNear", 'near')
M_GMID = ground_mat("M_GroundMid", 'mid')
M_GFAR = ground_mat("M_FarLand", 'far')
M_ROCK = rock_mat("M_CliffNear")
M_ROCKFAR = rock_mat("M_CliffFar", detail=0.6)
M_BOULDER = rock_mat("M_Boulders", detail=1.6)
M_COBBLE = cobble_mat("M_Cobbles")
M_GRASS = grass_mat("M_Grass")
M_GORSE = gorse_mat("M_Gorse")
M_SEA = sea_mat("M_Sea")
M_SKY = sky_dome_mat()
M_WASH = whitewash_mat("M_InnWalls")
M_SLATE = slate_roof_mat("M_InnRoof")
M_TIMBER = noisy("M_InnTimber", [(0.035, 0.03, 0.025), (0.07, 0.055, 0.04), (0.10, 0.08, 0.06)], scale=6, rough=0.75, stretch=(1, 1, 0.15), bump=0.3)
M_WINDOW = plain("M_InnWindowGlass", (0.02, 0.025, 0.03), rough=0.08)
M_FRAME = noisy("M_InnPaint", [(0.55, 0.54, 0.50), (0.62, 0.61, 0.57)], scale=20, rough=0.6, bump=0.1)
M_SIGN = noisy("M_Signboard", [(0.02, 0.05, 0.09), (0.03, 0.07, 0.12)], scale=5, rough=0.5, bump=0.05)
M_DRYSTONE = rock_mat("M_FieldWall", detail=2.0)
M_DRIFT = noisy("M_Driftwood", [(0.22, 0.21, 0.19), (0.34, 0.32, 0.29), (0.42, 0.40, 0.37)], scale=10, rough=0.9, stretch=(1, 1, 0.1), bump=0.5, bump_dist=0.004)
M_BARK = noisy("M_Hawthorn", [(0.03, 0.03, 0.028), (0.07, 0.065, 0.06), (0.12, 0.12, 0.11)], scale=25, rough=0.9, stretch=(1, 1, 0.3), bump=0.4)

# ----------------------------------------------------------------------------- terrain: polar rings, dense at the reader
RINGS = [0.0]
r_ = 0.3
while r_ < R_FAR:
    RINGS.append(r_); r_ *= 1.15 if r_ < 3.6 else 1.115
RINGS.append(R_FAR)
SEG = 96
def ring_index(rv): return min(range(len(RINGS)), key=lambda i: abs(RINGS[i] - rv))
I_FEET, I_NEAR, I_MID = ring_index(3.6), ring_index(16.0), ring_index(68.0)
print("terrain rings", len(RINGS), RINGS[I_FEET], RINGS[I_NEAR], RINGS[I_MID])

HCACHE = {}
def hc(x, y):
    k = (round(x, 4), round(y, 4))
    if k not in HCACHE: HCACHE[k] = h(x, y)
    return HCACHE[k]

def terrain(name, i0, i1, mat, seg=SEG):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    grid = []
    for j in range(i0, i1 + 1):
        rr = RINGS[j]
        if rr < 1e-6: grid.append([bm.verts.new((0.0, 0.0, hc(0.0, 0.0)))]); continue
        row = []
        for i in range(seg):
            a = 2 * math.pi * (i + 0.5 * (j % 2)) / seg
            x, y = rr * math.cos(a), rr * math.sin(a)
            row.append(bm.verts.new((x, y, hc(x, y))))
        grid.append(row)
    for j in range(len(grid) - 1):
        A, B = grid[j], grid[j + 1]
        if len(A) == 1:
            for i in range(seg): bm.faces.new((A[0], B[i], B[(i + 1) % seg]))
            continue
        for i in range(seg):
            k = (i + 1) % seg
            a0, a1, b0, b1 = A[i], A[k], B[i], B[k]
            q = (a0, a1, b0, b1)
            if max(v.co.z for v in q) < SL - 3.5 and min(v.co.y for v in q) > 14: continue      # deep water: never seen
            if (a0.co - b1.co).length < (a1.co - b0.co).length:
                bm.faces.new((a0, b0, b1)); bm.faces.new((a0, b1, a1))
            else:
                bm.faces.new((a0, b0, a1)); bm.faces.new((a1, b0, b1))
    for v in [v for v in bm.verts if not v.link_faces]: bm.verts.remove(v)
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < 0: f.normal_flip()
        f.smooth = True
        for l in f.loops: l[uvl].uv = (l.vert.co.x / (2 * RINGS[i1]) + 0.5, l.vert.co.y / (2 * RINGS[i1]) + 0.5)
    return mesh_obj(name, bm, mat, smooth_=True)

terrain("GroundFeet", 0, I_FEET, M_FEET)
terrain("GroundNear", I_FEET, I_NEAR, M_GNEAR)
terrain("GroundMid", I_NEAR, I_MID, M_GMID)
terrain("far.land", I_MID, len(RINGS) - 1, M_GFAR, seg=88)

# ----------------------------------------------------------------------------- the cliffs: bedded, jointed sheets
def h01(*a):
    s = 0.0
    for i, v in enumerate(a): s += v * (12.9898 + 31.7 * i)
    return (math.sin(s) * 43758.5453) % 1.0

def cliff_disp(y, z, side, P):
    """How far the rock face stands out (+) or is sunk (-) at a point: buttresses and gullies, then the faceted
    blocks that jointed slate breaks into (each a tilted plane), elongated along the steeply dipping beds."""
    sd = 3.7 if side < 0 else 9.1
    zb = z + DIP * y + 1.0 * noise.noise(Vector((y * 0.05, z * 0.05, sd)))
    big = 2.6 * fbm(Vector((y * 0.035, z * 0.05, sd + 5)), 3)
    gully = -2.0 * max(0.0, 1.0 - abs(noise.noise(Vector((y * 0.05, 0.3, sd + 7)))) * 4.0)
    facet = 0.0
    for lvl, (su, sz, amp) in enumerate(((4.2, 2.2, 1.0), (1.7, 0.9, 0.38))):
        q = Vector((y / su, zb / sz, sd + 11.0 * lvl))
        _d, pts = noise.voronoi(q)
        c = pts[0]
        a0 = h01(c.x, c.y, sd + lvl) - 0.5
        gy = (h01(c.x + 1.7, c.y, sd + lvl) - 0.5) * 1.3
        gz = (h01(c.x, c.y + 2.3, sd + lvl) - 0.2) * 1.1        # faces lean back more often than forward
        facet += amp * (a0 * 1.1 + gy * (q.x - c.x) + gz * (q.y - c.y))
    small = 0.06 * noise.noise(Vector((y * 0.9, z * 0.9, sd)))
    seaward = smooth(0.0, 6.0, y - ys(cE(y) if side < 0 else cW(y)))
    notch = -0.9 * math.exp(-((z - (SL + 0.7)) / 0.8) ** 2) * seaward
    return big + facet + small + notch + gully * smooth(0.2 * P, 0.6 * P, z)

def cliff_sheet(name, side, y0, y1, mat, du=0.45, dz=0.45, target=4500):
    """The cliff face: a dense displaced sheet along the rock line, then decimated to its triangle budget (the
    collapse keeps the facets' edges where the shape needs them)."""
    cf = cE if side < 0 else cW
    yl = [y0 + i * du for i in range(int((y1 - y0) / du) + 1)]
    cols = []
    for yv in yl:
        x0 = cf(yv); dx = cf(yv + 0.5) - cf(yv - 0.5)
        T = Vector((dx, 1.0, 0)).normalized()
        N = Vector((-T.y, T.x, 0))
        if N.x * (-side) < 0: N = -N                      # N points into the cove
        lz = lean(yv, side)
        P = rock_top(x0 + side * 3.0, yv)
        E_ = lz * (P - ZB_REF) + 0.8
        P = min(P, h(x0 + side * (E_ + 2.6), yv) - 0.35)  # never stand above the ground behind the cliff
        P = max(P, SL + 1.0)
        cols.append((yv, x0, N, lz, P))
    zbot = SL - 3.0
    zmax = max(c[4] for c in cols)
    nz_ = int((zmax + 1.0 - zbot) / dz) + 2
    verts, faces = [], []
    for (yv, x0, N, lz, P) in cols:
        for j in range(nz_):
            t = j / (nz_ - 1)
            z = zbot + t * (P + 0.2 - zbot)               # rows stretch to each column's own top
            dsp = max(-1.3, cliff_disp(yv, z, side, P)) * (1.0 - smooth(P - 3.0, P - 0.6, z))
            setback = lz * (z - ZB_REF) + 2.6 * smooth(P - 1.2, P + 0.2, z) - dsp
            if z > P - 0.2: setback += 3.0 * smooth(P - 0.2, P + 0.2, z); z = min(z, P - 0.4 * smooth(P - 0.2, P + 0.2, z))
            verts.append(Vector((x0, yv, 0)) - N * setback + Vector((0, 0, z)))
    nc = len(cols)
    for i in range(nc - 1):
        for j in range(nz_ - 1):
            a = i * nz_ + j; b_ = (i + 1) * nz_ + j
            faces.append([a, a + 1, b_ + 1, b_] if side < 0 else [a, b_, b_ + 1, a + 1])
    o = from_pydata(name, verts, faces, mat)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bm.normal_update()
    flip = sum(1 for f in bm.faces if f.normal.x * (-side) < -0.2)
    if flip > len(bm.faces) / 2:
        for f in bm.faces: f.normal_flip()
    bm.to_mesh(o.data); bm.free()
    tris0 = 2 * len(faces)
    if tris0 > target:
        md = o.modifiers.new("dec", 'DECIMATE'); md.decimate_type = 'COLLAPSE'; md.ratio = target / tris0; md.use_collapse_triangulate = True
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=md.name)
    sharpen_by_angle(o.data, 36.0)
    print("cliff", name, tris0, "->", len(o.data.polygons))
    return o

cliff_sheet("Cliff_EastNear", -1, -12.0, 46.4, M_ROCK, du=0.4, target=3600)
cliff_sheet("Cliff_WestNear", 1, -12.0, 46.4, M_ROCK, du=0.4, target=3600)
cliff_sheet("Cliff_EastFar", -1, 46.0, 150.0, M_ROCKFAR, du=1.0, dz=0.9, target=1500)
cliff_sheet("Cliff_WestFar", 1, 46.0, 150.0, M_ROCKFAR, du=1.0, dz=0.9, target=1500)

# ----------------------------------------------------------------------------- the big rock at the turn of the beach, fallen blocks, cobbles
ROCKS = Builder("Boulders", M_BOULDER)
rr = random.Random(7)
BIG = Vector((17.6, 11.6, 0.0))
BIG.z = h(BIG.x, BIG.y)
def add_rock(c, size, rnd, **kw):
    v, f = rock_piece(c, size, rnd, **kw); ROCKS.add(v, f)
# the big rock: one sea-worn mass of the same slate, its beds tilted with the cliffs', a lower shoulder on the shore side
add_rock(BIG + Vector((0.0, 0.0, -0.6)), (3.0, 2.3, 4.3), rr, cuts=13, bury=0.1, sub=1, bedding=0.35, yaw=0.45, jitter=0.06, tilt=0.35, detail=2, amp=0.35)
add_rock(BIG + Vector((-2.4, -1.4, -0.4)), (2.0, 1.6, 2.0), rr, cuts=11, bury=0.2, sub=1, bedding=0.35, yaw=0.3, jitter=0.05, tilt=0.3, detail=1, amp=0.2)
add_rock(BIG + Vector((2.0, 1.6, -0.5)), (1.3, 1.1, 0.9), rr, cuts=9, bury=0.3)
add_rock(BIG + Vector((-3.8, 0.9, 0.0)), (0.7, 0.6, 0.45), rr, cuts=8, bury=0.35)
add_rock(BIG + Vector((0.6, 3.2, 0.0)), (1.1, 0.9, 0.7), rr, cuts=8, bury=0.4)
# fallen blocks at the cliff feet, in fans below the gullies, fewer and smaller further off
for side, cf in ((-1, cE), (1, cW)):
    for i in range(26):
        yv = rr.uniform(-4.0, 62.0)
        fan = 0.5 + 0.5 * math.sin(yv * 0.21 + side)
        if rr.random() > 0.35 + 0.6 * fan: continue
        x0 = cf(yv); out = rr.uniform(0.3, 1.0) ** 2 * 6.0
        x = x0 - side * (out - 0.6)
        if math.hypot(x, yv) < 6: continue
        s = rr.uniform(0.25, 1.0) ** 2 * 1.7 + 0.2
        if yv > 40: s *= 0.8
        z = h(x, yv)
        add_rock(Vector((x, yv, z)), (s * rr.uniform(0.8, 1.3), s * rr.uniform(0.7, 1.1), s * rr.uniform(0.5, 0.8)), rr,
                 cuts=rr.randint(6, 8), bury=rr.uniform(0.2, 0.45), sub=1 if s > 1.2 and yv < 30 else 0, bedding=0.3)
# a few boulders out on the shingle and in the shallows
for (x, y, s) in [(-9.5, 6.3, 0.55), (-13.0, 3.0, 0.35), (8.5, 7.8, 0.45), (12.5, 4.5, 0.3), (-4.8, 9.3, 0.6), (5.5, 12.0, 0.8), (-16, 11.5, 0.9)]:
    add_rock(Vector((x, y, h(x, y))), (s * 1.2, s, s * 0.7), rr, cuts=7, bury=0.35, sub=1, bedding=0.3)
ROCKS.finish(smooth_=True)
sharpen_by_angle(bpy.data.objects["Boulders"].data, 42.0)

# rounded cobbles at the reader's feet and along the storm ridge
COB = Builder("Cobbles", M_COBBLE)
CTPL_V, CTPL_F = [], []
_seg, _rg = 6, 3
CTPL_V.append(Vector((0, 0, -1)))
for j in range(1, _rg + 1):
    t = math.pi * j / (_rg + 1); zz = -math.cos(t); r0 = math.sin(t)
    for i in range(_seg): CTPL_V.append(Vector((r0 * math.cos(2 * math.pi * i / _seg), r0 * math.sin(2 * math.pi * i / _seg), zz)))
CTPL_V.append(Vector((0, 0, 1)))
for i in range(_seg): CTPL_F.append([0, 1 + (i + 1) % _seg, 1 + i])
for j in range(_rg - 1):
    for i in range(_seg):
        a = 1 + j * _seg + i; b_ = 1 + j * _seg + (i + 1) % _seg
        CTPL_F.append([a, b_, b_ + _seg, a + _seg])
top = len(CTPL_V) - 1; base = 1 + (_rg - 1) * _seg
for i in range(_seg): CTPL_F.append([base + i, base + (i + 1) % _seg, top])
PEB_COLS = [(0.10, 0.10, 0.10, 0.0), (0.13, 0.135, 0.14, 0.0), (0.16, 0.16, 0.15, 0.0), (0.28, 0.24, 0.18, 0.0), (0.20, 0.17, 0.14, 0.0),
            (0.50, 0.49, 0.46, 0.0), (0.30, 0.22, 0.19, 0.0), (0.09, 0.09, 0.095, 1.0), (0.14, 0.14, 0.14, 1.0)]
rc = random.Random(11)
placed = []
tries = 0
while len(placed) < 90 and tries < 4000:
    tries += 1
    if len(placed) < 80:
        a = rc.uniform(0, 2 * math.pi); r0 = 0.25 + 3.2 * math.sqrt(rc.random())
        x, y = r0 * math.cos(a), r0 * math.sin(a)
        s = rc.uniform(0.03, 0.075) * (1.6 if rc.random() < 0.15 else 1.0)
    else:
        x = rc.uniform(-14, 14); y = ys(x) - rc.uniform(8.8, 10.4)
        s = rc.uniform(0.06, 0.15)
    if ys(x) - y < 0.6: continue
    if any((x - px) ** 2 + (y - py) ** 2 < (s + ps) ** 2 * 1.1 for px, py, ps in placed): continue
    placed.append((x, y, s))
    sx, sy, sz = s * rc.uniform(0.95, 1.3), s * rc.uniform(0.8, 1.0), s * rc.uniform(0.45, 0.7)
    yaw = rc.uniform(0, 2 * math.pi); R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(rc.uniform(-0.2, 0.2), 3, 'X')
    z = hc(x, y) if math.hypot(x, y) < 3.6 else h(x, y)
    seed = Vector((rc.uniform(0, 99), rc.uniform(0, 99), 0))
    vs = []
    for v in CTPL_V:
        p = Vector((v.x * sx, v.y * sy, v.z * sz)) * (1.0 + 0.10 * noise.noise(v * 1.7 + seed))
        vs.append(Vector((x, y, z + sz * 0.35)) + R @ p)
    COB.add(vs, CTPL_F, rc.choice(PEB_COLS))
COB.finish(smooth_=True)

# driftwood and a tangle of old rope on the wrack line, a broken spar under the east cliff
def log(name_b, p0, p1, r0, r1, sides=6):
    ax = (p1 - p0); L = ax.length; ax.normalize()
    s1 = ax.orthogonal().normalized(); s2 = ax.cross(s1)
    vs, fs = [], []
    for k, (p, r) in enumerate(((p0, r0), (p1, r1))):
        for i in range(sides):
            a = 2 * math.pi * i / sides
            vs.append(p + (s1 * math.cos(a) + s2 * math.sin(a)) * r * (1 + 0.15 * math.sin(3 * a + k)))
    for i in range(sides):
        j = (i + 1) % sides; fs.append([i, j, sides + j, sides + i])
    fs.append(list(range(sides - 1, -1, -1))); fs.append([sides + i for i in range(sides)])
    name_b.add(vs, fs)
DRIFT = Builder("Driftwood", M_DRIFT)
for (x0, y0, x1, y1, r) in [(-3.2, 1.9, -1.5, 2.5, 0.05), (-1.6, 2.4, -1.0, 2.0, 0.03), (3.8, 1.6, 5.9, 1.3, 0.07), (-11.0, -1.0, -7.4, -2.2, 0.12)]:
    p0 = Vector((x0, y0, h(x0, y0) + r * 0.4)); p1 = Vector((x1, y1, h(x1, y1) + r * 0.3))
    log(DRIFT, p0, p1, r, r * 0.7)
    log(DRIFT, p0.lerp(p1, 0.6), p0.lerp(p1, 0.6) + Vector((0.3, 0.35, 0.05)), r * 0.5, r * 0.25, sides=5)
DRIFT.finish(smooth_=True)

# a small clinker-built boat drawn up on the shingle above the tide, keel on two old spars, oars inside
BOAT_M = noisy("M_BoatTar", [(0.03, 0.035, 0.04), (0.06, 0.065, 0.07), (0.11, 0.11, 0.105)], scale=9, rough=0.55, stretch=(0.15, 1, 1), bump=0.3)
def boat(cx, cy, yaw, Lb=4.2, Bb=1.45, Db=0.62):
    st, nsec = 10, 13
    rows = []
    for i in range(nsec):
        t = i / (nsec - 1); u = t * 2 - 1
        half = Bb / 2 * (1 - abs(u) ** 2.3) ** 0.8 + 0.02
        sheer = Db * (1 + 0.25 * u * u)
        row = []
        for k in range(st):
            a = math.pi * k / (st - 1)
            yy = -math.cos(a) * half
            zz = sheer - math.sin(a) * Db * (1 - 0.35 * abs(u) ** 3) - (0.0 if 0 < k < st - 1 else 0.0)
            # clinker: stepped strakes
            zz += 0.012 * ((k % 2) - 0.5)
            row.append(Vector((u * Lb / 2, yy, zz)))
        rows.append(row)
    vs, fs = [], []
    for row in rows: vs.extend(row)
    for i in range(nsec - 1):
        for k in range(st - 1):
            a = i * st + k; fs.append([a, a + 1, a + st + 1, a + st])
    # inner skin (the boat is open): a slightly smaller copy, reversed
    off = len(vs)
    for row in rows: vs.extend([Vector((p.x * 0.97, p.y * 0.9, p.z * 0.92 + Db * 0.08)) for p in row])
    for i in range(nsec - 1):
        for k in range(st - 1):
            a = off + i * st + k; fs.append([a, a + st, a + st + 1, a + 1])
    for i in range(nsec - 1):        # gunwale caps
        for k in (0, st - 1):
            a, b_ = i * st + k, (i + 1) * st + k
            fs.append([a, b_, off + b_, off + a] if k == 0 else [a, off + a, off + b_, b_])
    R = Matrix.Rotation(yaw, 3, 'Z')
    z0 = h(cx, cy)
    heel = Matrix.Rotation(0.12, 3, 'X')
    world = [Vector((cx, cy, z0 + 0.12)) + R @ (heel @ (p + Vector((0, 0, Db * 0.85)))) for p in vs]
    from_pydata("Boat_Hull", world, fs, BOAT_M, smooth_=True)
    for s_ in (-0.25, 0.25):        # thwarts
        p = Vector((cx, cy, z0 + 0.12)) + R @ (heel @ Vector((s_ * Lb, 0, Db * 1.3)))
        box(f"Boat_Thwart{s_}", (0.22, Bb * 0.8, 0.04), tuple(p), M_DRIFT, rot=(0.12, 0, yaw))
    for k in (-0.12, 0.1):          # oars lying across the thwarts
        p = Vector((cx, cy, z0 + 0.12)) + R @ (heel @ Vector((0.0, k, Db * 1.42)))
        cyl(f"Boat_Oar{k}", 0.025, 3.0, tuple(p), M_DRIFT, verts=6, rot=(0.12, math.pi / 2 - 0.05, yaw + 0.04))
    for k in (-1, 1):               # the spars it rests on
        p = Vector((cx, cy, 0)) + R @ Vector((k * Lb * 0.28, 0, 0)); p.z = h(p.x, p.y) + 0.05
        cyl(f"Boat_Spar{k}", 0.06, 2.0, tuple(p), M_DRIFT, verts=6, rot=(math.pi / 2, 0, yaw))
boat(-7.8, -3.6, math.radians(-62))

# ----------------------------------------------------------------------------- the sea (its own mesh: Unity moves the vertices)
def sea_sheet():
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rs = [2.8]
    while rs[-1] < R_FAR: rs.append(min(R_FAR, rs[-1] * 1.10 + 0.05))
    seg = 112; grid = []
    for rr_ in rs:
        row = []
        for i in range(seg):
            a = math.pi * (-0.08 + 1.16 * i / (seg - 1))
            row.append((rr_ * math.cos(a), rr_ * math.sin(a)))
        grid.append(row)
    vmap = {}
    def V(j, i):
        if (j, i) not in vmap:
            x, y = grid[j][i]; vmap[(j, i)] = bm.verts.new((x, y, SL))
        return vmap[(j, i)]
    for j in range(len(rs) - 1):
        for i in range(seg - 1):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            hz = [h(x, y) for x, y in q]
            if min(hz) > SL + 0.06: continue
            if min(out_d(x, y) for x, y in q) > edge_out(q[0][0], q[0][1]) + 2: continue
            bm.faces.new((V(j, i), V(j, i + 1), V(j + 1, i + 1), V(j + 1, i)))
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < 0: f.normal_flip()
        for l in f.loops: l[uvl].uv = (l.vert.co.x / (2 * R_FAR) + 0.5, l.vert.co.y / (2 * R_FAR) + 0.5)
    o = mesh_obj("water.ocean.cove", bm, M_SEA)
    # vertex colour G: foam where the water is shallow over the shingle, round the rocks and at the cliff foot
    def foam(i, co):
        depth = SL - h(co.x, co.y)
        f = 1.0 - smooth(0.0, 0.3, depth)
        dr = (Vector((co.x, co.y, 0)) - Vector((BIG.x, BIG.y, 0))).length
        f = max(f, 0.85 * (1.0 - smooth(2.6, 5.0, dr)))
        oc = out_d(co.x, co.y)
        f = max(f, 0.7 * smooth(-3.5, -0.5, oc) * smooth(-2, 6, co.y - ys(co.x)))
        f *= 0.75 + 0.25 * noise.noise(Vector((co.x * 0.4, co.y * 0.4, 3.0)))
        return (0.0, max(0.0, min(1.0, f)), 0.0, 1.0)
    K.set_color_attr(o.data, foam, "Color")
    return o
SEA = sea_sheet()

# ----------------------------------------------------------------------------- coarse grass (veg.grass) and gorse (veg.shrub)
GRASS = Builder("veg.grass.coarse", M_GRASS, living=True)
rg = random.Random(23)
def tussock(x, y, H, n, segs, lean_, rnd, frosty=1.0, width=0.012):
    z0 = h(x, y) if math.hypot(x, y) > 3.6 else hc(x, y)
    tint = (0.15 * rnd.uniform(0.8, 1.2), 0.15 * rnd.uniform(0.85, 1.15), 0.07, frosty)
    for k in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        out = rnd.uniform(0.15, 0.55)
        dirv = Vector((math.cos(a) * out + lean_[0], math.sin(a) * out + lean_[1], 1.0)).normalized()
        L = H * rnd.uniform(0.55, 1.05)
        side = Vector((-math.sin(a), math.cos(a), 0))
        base = Vector((x + math.cos(a) * 0.02, y + math.sin(a) * 0.02, z0 - 0.02))
        vs, ws, fs = [], [], []
        droop = rnd.uniform(0.15, 0.45)
        for s in range(segs + 1):
            t = s / segs
            p = base + dirv * L * t + Vector((math.cos(a), math.sin(a), 0)) * droop * L * t * t - Vector((0, 0, droop * 0.5 * L * t * t))
            w = width * (1.0 - t * 0.85) if s < segs else 0.0
            if s < segs:
                vs += [p - side * w, p + side * w]; ws += [(t ** 1.3, 0, 0, 1)] * 2
            else:
                vs.append(p); ws.append((1.0, 0, 0, 1))
        for s in range(segs - 1):
            i0 = 2 * s; fs.append([i0, i0 + 1, i0 + 3, i0 + 2])
        i0 = 2 * (segs - 1); fs.append([i0, i0 + 1, len(vs) - 1])
        GRASS.add(vs, fs, tint, ws)
# on the storm ridge's back, the bank and the path sides behind the reader; a few in the shingle top
for i in range(4000):
    if len(GRASS.verts) > 7600: break
    x = rg.uniform(-17, 15); y = rg.uniform(-24, 0)
    d = ys(x) - y
    if d < 9.0: continue
    dens = smooth(9.5, 13.0, d) * (0.55 + 0.45 * noise.noise(Vector((x * 0.25, y * 0.25, 5.0))))
    if abs(x - path_x(y)) < 0.9 and y < -9: continue
    if out_d(x, y) > -1.5: continue
    r = math.hypot(x, y)
    if rg.random() > math.sqrt(max(0.0, dens)) * (1.0 if r < 18 else 0.4): continue
    tussock(x, y, rg.uniform(0.35, 0.7), rg.randint(14, 22) if r < 14 else rg.randint(9, 13), 2, (0.08, -0.05), rg, width=0.016 if r < 12 else 0.026)
# fringes along the cliff tops, against the sky
for side, cf in ((-1, cE), (1, cW)):
    for i in range(40):
        yv = rg.uniform(-2, 60)
        x0 = cf(yv); E = edge_out(x0 + side * 3, yv)
        x = x0 + side * (E - 0.4 + rg.uniform(-0.3, 0.6))
        tussock(x, yv, rg.uniform(0.35, 0.6), rg.randint(5, 7), 2, (side * -0.15, 0.0), rg, frosty=0.3, width=0.035)
GRASS.finish(smooth_=True)

GORSE = Builder("veg.shrub.gorse", M_GORSE, living=True)
def lobe_tpl(seg=8, rings=5):
    vs = [Vector((0, 0, -1))]
    for j in range(1, rings):
        t = math.pi * j / rings; zz = -math.cos(t); r0 = math.sin(t)
        for i in range(seg): vs.append(Vector((r0 * math.cos(2 * math.pi * i / seg), r0 * math.sin(2 * math.pi * i / seg), zz)))
    vs.append(Vector((0, 0, 1))); top = len(vs) - 1
    fs = [[0, 1 + (i + 1) % seg, 1 + i] for i in range(seg)]
    for j in range(rings - 2):
        for i in range(seg):
            a = 1 + j * seg + i; b_ = 1 + j * seg + (i + 1) % seg; fs.append([a, b_, b_ + seg, a + seg])
    base = 1 + (rings - 2) * seg
    fs += [[base + i, base + (i + 1) % seg, top] for i in range(seg)]
    return vs, fs
LOBE_V, LOBE_F = lobe_tpl(7, 4)
def gorse(x, y, s, rnd):
    z0 = h(x, y)
    for k in range(rnd.randint(1, 3)):
        cx_, cy_ = x + rnd.uniform(-1, 1) * s * 0.8, y + rnd.uniform(-1, 1) * s * 0.8
        c = Vector((cx_, cy_, h(cx_, cy_) + s * rnd.uniform(0.3, 0.45)))
        rad = s * rnd.uniform(0.55, 0.9); seed = Vector((rnd.uniform(0, 99), rnd.uniform(0, 99), 0))
        vs, ws = [], []
        for v in LOBE_V:
            p = v * (1.0 + 0.3 * noise.noise(v * 1.6 + seed) + 0.12 * noise.noise(v * 4.0 + seed))
            p.z *= 0.62
            if p.z < -0.1: p.z = -0.1 + (p.z + 0.1) * 0.2
            q = c + p * rad
            vs.append(q); ws.append((max(0.0, min(1.0, (q.z - z0) / (2 * s))) * 0.6, 0, 0, 1))
        GORSE.add(vs, LOBE_F, (1, 1, 1, 1), ws)
for i in range(22):
    x = rg.uniform(-34, 34); y = rg.uniform(-60, -8)
    o = out_d(x, y)
    if o < -4 or o > 22: continue
    if abs(y - road_y(x)) < 3: continue
    if noise.noise(Vector((x * 0.06, y * 0.06, 9.0))) < -0.05: continue
    gorse(x, y, rg.uniform(0.5, 1.3), rg)

# ----------------------------------------------------------------------------- the Admiral Benbow, its signboard, the coast road walls
INN = Vector((-7.5, -61.0, 0.0))
INN.z = min(h(INN.x + dx, INN.y + dy) for dx in (-7.5, 7.5) for dy in (-3.2, 3.2)) - 0.3
IW, ID, IH = 15.0, 6.6, 5.4               # length (x), depth (y), wall height
ROOF_H = 3.1
gz = INN.z
box("Inn_Walls", (IW, ID, IH + 0.3), (INN.x, INN.y, gz + (IH + 0.3) / 2), M_WASH)
# lean-to at the west end (the stable / brewhouse)
box("Inn_LeanTo", (4.0, 5.2, 3.0), (INN.x + IW / 2 + 2.0, INN.y - 0.4, gz + 1.5), M_WASH)
def gable_roof(name, cx, cy, w, d, z0, rh, ov=0.35, mat=M_SLATE, axis='x'):
    L = (d / 2 + ov) / math.cos(math.atan(rh / (d / 2)))
    pitch = math.atan(rh / (d / 2))
    for s in (-1, 1):
        mid = Vector((cx, cy + s * (d / 2 + ov) / 2 - s * 0.0, z0 + rh / 2 - 0.05))
        box(f"{name}{s}", (w + 2 * ov * 0.6, L + 0.05, 0.12), tuple(mid), mat, rot=(-s * pitch, 0, 0))
gable_roof("Inn_Roof", INN.x, INN.y, IW, ID, gz + IH, ROOF_H)
box("Inn_Ridge", (IW + 0.4, 0.28, 0.2), (INN.x, INN.y, gz + IH + ROOF_H + 0.02), M_SLATE)
# gable ends
for sx in (-1, 1):
    vs = [(INN.x + sx * IW / 2, INN.y - ID / 2, gz + IH), (INN.x + sx * IW / 2, INN.y + ID / 2, gz + IH), (INN.x + sx * IW / 2, INN.y, gz + IH + ROOF_H)]
    vs2 = [(v[0] - sx * 0.3, v[1], v[2]) for v in vs]
    from_pydata(f"Inn_Gable{sx}", vs + vs2, [[0, 1, 2], [5, 4, 3], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]], M_WASH)
    box(f"Inn_Chimney{sx}", (0.9, 1.1, 2.4), (INN.x + sx * (IW / 2 - 0.5), INN.y, gz + IH + ROOF_H + 0.3), M_WASH)
    box(f"Inn_ChimneyCap{sx}", (1.0, 1.2, 0.12), (INN.x + sx * (IW / 2 - 0.5), INN.y, gz + IH + ROOF_H + 1.5), M_DRYSTONE)
    for k in (-0.22, 0.22):
        cyl(f"Inn_Pot{sx}{k}", 0.11, 0.35, (INN.x + sx * (IW / 2 - 0.5), INN.y + k, gz + IH + ROOF_H + 1.72), M_TIMBER, verts=8)
gable_roof("Inn_LeanRoof", INN.x + IW / 2 + 2.0, INN.y - 0.4, 4.0, 5.2, gz + 3.0, 1.1)
# windows (12 small panes, white sashes) and the door, on the seaward front (+y)
FY = INN.y + ID / 2
for i, wx in enumerate((-5.6, -2.8, 2.8, 5.6)):
    for wz in (1.5, 4.0):
        if wz == 1.5 and abs(wx) < 1: continue
        cx = INN.x + wx
        box(f"Inn_Win{i}{wz}", (0.95, 0.06, 1.25), (cx, FY + 0.02, gz + wz + 0.62), M_WINDOW)
        box(f"Inn_WinFrame{i}{wz}a", (1.12, 0.10, 0.09), (cx, FY + 0.05, gz + wz), M_FRAME)
        box(f"Inn_WinFrame{i}{wz}b", (1.12, 0.10, 0.09), (cx, FY + 0.05, gz + wz + 1.25), M_FRAME)
        for k in (-0.5, 0.0, 0.5):
            box(f"Inn_WinFrame{i}{wz}v{k}", (0.06, 0.08, 1.25), (cx + k * 0.95, FY + 0.05, gz + wz + 0.62), M_FRAME)
        box(f"Inn_WinFrame{i}{wz}m", (0.95, 0.08, 0.05), (cx, FY + 0.05, gz + wz + 0.62), M_FRAME)
box("Inn_Door", (1.05, 0.08, 2.0), (INN.x, FY + 0.03, gz + 1.0 + 0.3), M_TIMBER)
box("Inn_DoorHood", (1.5, 0.5, 0.1), (INN.x, FY + 0.25, gz + 2.55), M_SLATE, rot=(0.2, 0, 0))
box("Inn_Step", (1.4, 0.7, 0.3), (INN.x, FY + 0.35, gz + 0.3), M_DRYSTONE)
# the signboard on its post by the road: board hung from a bracket
SIGN = Vector((INN.x + 4.0, road_y(INN.x + 4.0) - 2.6, 0.0)); SIGN.z = h(SIGN.x, SIGN.y)
box("Sign_Post", (0.2, 0.2, 3.6), (SIGN.x, SIGN.y, SIGN.z + 1.6), M_TIMBER)
box("Sign_Arm", (1.3, 0.12, 0.12), (SIGN.x + 0.6, SIGN.y, SIGN.z + 3.25), M_TIMBER)
box("Sign_Board", (0.9, 0.05, 0.7), (SIGN.x + 0.75, SIGN.y, SIGN.z + 2.65), M_SIGN)
box("Sign_Frame", (0.98, 0.04, 0.78), (SIGN.x + 0.75, SIGN.y - 0.012, SIGN.z + 2.65), M_FRAME)
# dry-stone walls (Devon hedge-banks) along the road on the seaward side, with a gap for the path
WALL = Builder("FieldWalls", M_DRYSTONE)
for side in (-1, 1):
    pts = []
    xs = [side * (2.0 + i * 1.0) for i in range(42)]
    for x in xs:
        y = road_y(x) + 2.4
        if abs(x - path_x(y)) < 1.4: continue
        pts.append((x, y))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        z0, z1 = h(x0, y0), h(x1, y1)
        hh = 0.9 + 0.15 * noise.noise(Vector((x0 * 0.3, 0.5, 1)))
        vs = [(x0, y0 - 0.45, z0 - 0.2), (x0, y0 + 0.45, z0 - 0.2), (x0, y0 + 0.3, z0 + hh), (x0, y0 - 0.3, z0 + hh),
              (x1, y1 - 0.45, z1 - 0.2), (x1, y1 + 0.45, z1 - 0.2), (x1, y1 + 0.3, z1 + hh), (x1, y1 - 0.3, z1 + hh)]
        WALL.add([Vector(v) for v in vs], [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])
WALL.finish(smooth_=False)

# a wind-bent hawthorn or two by the path (leafless in January)
THORN = Builder("Hawthorns", M_BARK)
def branch(p0, d, L, r, depth, rnd, maxd=3, wind=Vector((0.35, -0.25, 0)), spread=0.8):
    p1 = p0 + d * L
    log(THORN, p0, p1, r, r * 0.65, sides=6 if depth < 2 else 4)
    if depth >= maxd or r < 0.008: return
    for k in range(2 if depth < 1 else rnd.randint(2, 3)):
        nd = (d + Vector((rnd.uniform(-spread, spread), rnd.uniform(-spread, spread), rnd.uniform(-0.1, 0.5))) + wind).normalized()
        branch(p1, nd, L * rnd.uniform(0.6, 0.8), r * 0.62, depth + 1, rnd, maxd, wind, spread)
rt = random.Random(5)
for (x, y) in [(-3.8, -27.0), (4.5, -40.0), (-12.5, -44.0)]:
    z = h(x, y)
    branch(Vector((x, y, z - 0.1)), Vector((0.35, -0.2, 1.0)).normalized(), 1.0, 0.11, 0, rt)
# two old sycamores sheltering the inn's west end and the lane, bare
for (x, y, H) in [(INN.x - 10.5, INN.y + 1.5, 2.6), (INN.x + 13.5, INN.y - 4.0, 2.2)]:
    z = h(x, y)
    branch(Vector((x, y, z - 0.2)), Vector((0.05, -0.05, 1.0)).normalized(), H, 0.30, 0, rt, maxd=4, wind=Vector((0.1, -0.08, 0.15)), spread=0.9)
THORN.finish(smooth_=True)

# the combe's sides: outcrops of the same slate breaking through the turf, and field walls with gorse along them
OUTC = Builder("Outcrops", M_BOULDER)
ro = random.Random(19)
for (x, y, s_) in [(-24.0, -22.0, 2.6), (-31.0, -36.0, 3.4), (-19.5, -47.0, 2.0), (21.0, -18.0, 2.8), (26.0, -31.0, 3.6),
                   (17.0, -44.0, 2.2), (31.0, -12.0, 2.5), (-36.0, -12.0, 3.0), (-14.0, -30.0, 1.4), (12.5, -27.0, 1.5)]:
    for k in range(ro.randint(1, 3)):
        c = Vector((x + ro.uniform(-1.5, 1.5), y + ro.uniform(-1.5, 1.5), 0)); c.z = h(c.x, c.y)
        sz = s_ * ro.uniform(0.6, 1.0)
        v, f = rock_piece(c, (sz, sz * ro.uniform(0.6, 0.9), sz * ro.uniform(0.5, 0.75)), ro, cuts=9, bury=0.5, sub=0, bedding=0.25, jitter=0.05)
        OUTC.add(v, f)
o_ = OUTC.finish(smooth_=True); sharpen_by_angle(o_.data, 40.0)

WALL2 = Builder("FieldWallsSlopes", M_DRYSTONE)
def wall_line(pts, hh=1.1, step=1.6):
    L = [0.0]
    for a_, b_ in zip(pts, pts[1:]): L.append(L[-1] + math.dist(a_, b_))
    n = max(2, int(L[-1] / step))
    def at(t):
        for i in range(len(L) - 1):
            if L[i + 1] >= t:
                f = (t - L[i]) / max(1e-6, L[i + 1] - L[i]); return (lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f))
        return pts[-1]
    q = [at(L[-1] * i / n) for i in range(n + 1)]
    for (x0, y0), (x1, y1) in zip(q, q[1:]):
        d = Vector((x1 - x0, y1 - y0, 0)).normalized(); nn = Vector((-d.y, d.x, 0))
        z0, z1 = h(x0, y0), h(x1, y1)
        e0 = hh * (1 + 0.12 * noise.noise(Vector((x0 * 0.4, y0 * 0.4, 1)))); e1 = hh * (1 + 0.12 * noise.noise(Vector((x1 * 0.4, y1 * 0.4, 1))))
        p0 = Vector((x0, y0, 0)); p1 = Vector((x1, y1, 0))
        vs = [p0 - nn * 0.5 + Vector((0, 0, z0 - 0.3)), p0 + nn * 0.5 + Vector((0, 0, z0 - 0.3)), p0 + nn * 0.32 + Vector((0, 0, z0 + e0)), p0 - nn * 0.32 + Vector((0, 0, z0 + e0)),
              p1 - nn * 0.5 + Vector((0, 0, z1 - 0.3)), p1 + nn * 0.5 + Vector((0, 0, z1 - 0.3)), p1 + nn * 0.32 + Vector((0, 0, z1 + e1)), p1 - nn * 0.32 + Vector((0, 0, z1 + e1))]
        WALL2.add(vs, [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])
        if ro.random() < 0.2:
            gorse(x0 + nn.x * ro.uniform(-0.6, 0.6), y0 + nn.y * ro.uniform(-0.6, 0.6), ro.uniform(0.5, 0.9), ro)
for pts in ([(-6.0, -30.0), (-14.0, -31.5), (-24.0, -35.0), (-36.0, -40.0), (-48.0, -43.0)],
            [(4.0, -24.0), (12.0, -26.0), (20.0, -30.5), (30.0, -36.0), (40.0, -38.0)],
            [(-24.0, -35.0), (-26.0, -24.0), (-30.0, -14.0)],
            [(20.0, -30.5), (22.5, -42.0), (23.5, -49.0)]):
    wall_line(pts)
WALL2.finish(smooth_=False)
GORSE.finish(smooth_=True)

# ----------------------------------------------------------------------------- sky dome (lat-long UVs, inward)
def sky_dome(name, radius=SKY_R, seg=40, rings=16, el_min=-10.0):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    els = [math.radians(el_min)] + [math.radians(90.0 * (j / rings) ** 1.4) for j in range(rings)] + [math.radians(89.9)]
    grid = []
    for e in els:
        grid.append([bm.verts.new((radius * math.cos(e) * math.cos(2 * math.pi * i / seg), radius * math.cos(e) * math.sin(2 * math.pi * i / seg), radius * math.sin(e))) for i in range(seg + 1)])
    for j in range(len(els) - 1):
        for i in range(seg):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for l, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uvl].uv = (ii / seg, jj / (len(els) - 1))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001) if False else None
    for f in bm.faces:
        f.normal_update()
        if f.normal.dot(f.calc_center_median()) > 0: f.normal_flip()
    o = mesh_obj(name, bm, M_SKY, smooth_=True)
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False; o.visible_transmission = False; o.visible_volume_scatter = False
    return o
sky = sky_dome("SkyDome")

# ----------------------------------------------------------------------------- lights, world, living-scene empties, anchors
light_obj("light.sun", 'SUN', 3.2, (1.0, 0.70, 0.46), tuple(SUN_DIR * 60), direction=-SUN_DIR, angle=math.radians(0.8))
sky_l = light_obj("light.sky", 'SUN', 0.0, (0.70, 0.78, 0.95), (0, 0, 30), direction=(0.1, 0.25, -1.0), angle=math.radians(80))
sky_l.data.use_shadow = False

world = bpy.data.worlds.new("FrostyDawn"); scene.world = world; world.use_nodes = True
wnt = world.node_tree
for n in list(wnt.nodes): wnt.nodes.remove(n)
wg = K.G(wnt)
wout = wnt.nodes.new("ShaderNodeOutputWorld"); bg = wnt.nodes.new("ShaderNodeBackground")
wnt.links.new(bg.outputs[0], wout.inputs[0])
wtc = wg.n("ShaderNodeTexCoord")
wg.set(bg.inputs["Color"], sky_nodes(wg, wtc.outputs["Generated"]))
bg.inputs["Strength"].default_value = 1.25

living_empty("sound.surf.shore", (0.0, ys(0.0) + 1.0, SL + 0.2), 0.3)
living_empty("sound.surf.rock", (BIG.x, BIG.y + 1.5, SL + 0.5), 0.3)
living_empty("sound.gulls.cliffs", (cW(30.0) - 3.0, 30.0, 22.0), 0.3)
living_empty("sound.wind.combe", (-1.0, -18.0, h(-1.0, -18.0) + 1.5), 0.3)

anchor("reader.entrance", (0.0, 0.0, hc(0.0, 0.0)))
anchor("reader.look", (0.0, 1.0, hc(0.0, 0.0) + EYE))
anchor("scene.centre", (0.0, ys(0.0), SL))
anchor("cove.bigRock", tuple(BIG))
anchor("cove.inn", (INN.x, FY, gz))
anchor("cove.signboard", (SIGN.x, SIGN.y, SIGN.z))

Z0 = hc(0.0, 0.0)
E = Vector((0.0, 0.0, Z0 + EYE))
fwd = Vector((0.0, 1.0, 0.0))
PAGE_C = E + fwd * 0.6 - Vector((0, 0, 0.05))
page = box("PagePreview", (0.4, 0.004, 0.55), tuple(PAGE_C), plain("M_PagePreview", (0.80, 0.76, 0.66), rough=0.9))

K.apply_all_transforms()

def yawed(deg, dist=10.0, dz=-0.6):
    a = math.radians(deg); d = Matrix.Rotation(a, 3, 'Z') @ fwd
    return tuple(E + d * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(E), yawed(0, 10.0, -0.35), lens=17),
    camera("Cam_Page", tuple(E), yawed(0, 10.0, -0.35), lens=17),
    camera("Cam_Left", tuple(E), yawed(80, 10.0, 0.6), lens=17),
    camera("Cam_Right", tuple(E), yawed(-75, 10.0, 0.4), lens=17),
    camera("Cam_Behind", tuple(E), yawed(180, 10.0, 0.9), lens=17),
    camera("Cam_Down", tuple(E), (0.15, 1.2, Z0), lens=17),
    camera("Cam_Rock", (6.0, 2.0, hc(0, 0) + 1.6), (BIG.x, BIG.y, BIG.z + 2.2), lens=24),
    camera("Cam_Inn", (-2.0, -12.0, h(-2, -12) + 1.6), (INN.x, INN.y, gz + 4.0), lens=35),
]
EXPOSURE = {"Cam_Down": 1.1}

if not args.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "benbow_cove_source.blend"))
K.budget()
if args.render:
    K.render_cams(cams, OUT, page=page, page_cams={"Cam_Page"}, exposure=EXPOSURE, default_exposure=0.95, prefix=args.prefix)

if args.bake or args.export:
    T_ = args.tex
    stats = K.bake_and_export(
        "benbow_cove",
        keep_names={"M_SkyDome": "SkyDome", "M_FarLand": "far.land", "M_Sea": "water.ocean.cove", "M_Grass": "veg.grass.coarse",
                    "M_Gorse": "veg.shrub.gorse"},
        size_for={"M_ShingleFeet": (T_, T_ // 4, T_), "M_GroundNear": (T_, T_ // 4, T_), "M_GroundMid": (T_, 256, T_ // 2),
                  "M_FarLand": (T_ // 2, 0, T_ // 4), "M_CliffNear": (T_, T_ // 4, T_), "M_CliffFar": (T_ // 2, 0, T_ // 2),
                  "M_Boulders": (T_ // 2, T_ // 8, T_ // 2), "M_Cobbles": (T_ // 4, T_ // 8, T_ // 4), "M_Grass": (T_ // 4, 0, 0),
                  "M_Gorse": (T_ // 8, 0, T_ // 8), "M_Sea": (128, 0, 0), "M_SkyDome": (T_, 0, 0), "M_InnWalls": (T_ // 4, 0, T_ // 4),
                  "M_InnRoof": (T_ // 4, 0, T_ // 4), "M_FieldWall": (T_ // 4, 0, T_ // 4)},
        keep_uv={"SkyDome", "water.ocean.cove", "MESH_ShingleFeet", "MESH_GroundNear", "MESH_GroundMid", "far.land"},
        lightmap_uv={"M_Grass"}, emit_only={"M_SkyDome"}, remove=[page], default_div=16)
    print("STATS", stats)
print("DONE")
