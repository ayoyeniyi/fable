"""
Fable step-in room `blefuscu-harbour-channel`: the channel off Blefuscu harbour (Gulliver's Travels, Part I,
Chapter V).

"I walked towards the north-east coast ... and in less than half an hour arrived at the fleet. The enemy was so
frightened when they saw me, that they leaped out of their ships, and swam to shore, where there could not be fewer
than thirty thousand souls. I then took my tackling, and, fastening a hook to the hole at the prow of each, I tied all
the cords together at the end. While I was thus employed, the enemy discharged several thousand arrows, many of which
stuck in my hands and face ... I took up the knotted end of the cables, to which my hooks were tied, and with great
ease drew fifty of the enemy's largest men of war after me."

The reader is Gulliver-size, standing chest-deep in the channel (feet on the sand 1.1 m under the surface, eyes
0.45 m above it) a little off Blefuscu harbour on a bright late morning near high water. Ahead the enemy fleet lies
at anchor, bunched: some fifty men of war (1/12 scale, up to 2.7 m long, three masts, sails furled on the yards) and
smaller one-masted transports, decks empty, a cord running from the prow of each to the knotted bundle that floats at
the reader's right hand, each cord ending in one of Gulliver's iron hooks. Arrows stand in the water round the reader
and in the hulls. Beyond, the stone quays and warehouses of the harbour, the town of Blefuscu rising behind, and the
shore and quays dark with the crowd. Behind the reader, across the channel, the low coast of Lilliput.
No people modelled (the crowd is a speckle on the far shore), no boat, no fire, no ceremonies, nothing full-size.

Run (from the repo root):
  blender -b -P blender/build_blefuscu_harbour_channel.py -- --cpu --render --samples 40 --res 1280
  blender -b -P blender/build_blefuscu_harbour_channel.py -- --export
  then blender/runtime_bake.py and tools/publish_scene_room.py (docs/SCENE_ROOMS_PIPELINE.md)
Axes: metres, +Z up; the sea surface is z = 0, the reader's feet at z = -1.1, facing +Y (north-east, the harbour).
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b3 as K
import roomkit as rk

ARGS = K.setup("blefuscu-harbour-channel", seed=1701, samples=40)
if ARGS.cpu: bpy.context.scene.cycles.device = 'CPU'
R = random.Random(1701)
fbm, ss = K.fbm, K.smoothstep
FEET = -1.1

# ----------------------------------------------------------------------------- materials
sand = K.patchy_mat("sand", (0.66, 0.60, 0.46), patches=[((0.52, 0.48, 0.38), 0.3, 0.4), ((0.40, 0.42, 0.30), 0.08, 0.15)], rough=0.9)
land = K.patchy_mat("land", (0.36, 0.42, 0.22), patches=[((0.44, 0.44, 0.26), 0.05, 0.4), ((0.22, 0.30, 0.14), 0.08, 0.3), ((0.55, 0.50, 0.36), 0.2, 0.15)])
sea = K.mat("sea", (0.08, 0.20, 0.24), "water", rough=0.14)
hullm = K.mat("tarred_hull", (0.09, 0.07, 0.05), "planks", rough=0.6)
wale = K.mat("hull_paint", (0.55, 0.42, 0.18), "wood", rough=0.5)
spar = K.mat("spars", (0.42, 0.32, 0.20), "wood", rough=0.7)
sail = K.mat("furled_sail", (0.80, 0.76, 0.66), "fabric", rough=0.9)
cord = K.mat("packthread", (0.62, 0.55, 0.40), "fabric", rough=0.9)
iron = K.mat("iron_hooks", (0.13, 0.12, 0.11), "metal", rough=0.6)
arrow = K.mat("arrow_shafts", (0.55, 0.46, 0.30), "wood", rough=0.7)
fletch = K.mat("fletching", (0.85, 0.82, 0.76), "fabric", rough=0.8)
stone = K.mat("quay_stone", (0.70, 0.66, 0.56), "stone", rough=0.85)
roof = K.mat("roof_tiles", (0.52, 0.27, 0.18), "brick", rough=0.8)
plaster = K.mat("town_plaster", (0.82, 0.78, 0.68), "plaster", rough=0.85)
flagm = K.mat("flags", (0.20, 0.26, 0.55), "fabric", rough=0.7)
crowd = K.patchy_mat("crowd", (0.30, 0.26, 0.22), patches=[((0.60, 0.20, 0.15), 4.0, 0.25), ((0.20, 0.25, 0.45), 4.5, 0.25), ((0.80, 0.75, 0.62), 5.0, 0.3), ((0.15, 0.30, 0.18), 3.5, 0.2)], rough=0.9)
trees = K.mat("tree_masses", (0.18, 0.26, 0.11), "foliage", rough=0.85)
K.keep(sea, "water.ocean.channel"); K.keep(sail, "cloth.sail.furled"); K.keep(flagm, "cloth.flag.harbour")
K.size(sand, 1024, 128); K.size(land, 1024, 128); K.size(hullm, 1024, 128); K.size(sea, 256)

# ----------------------------------------------------------------------------- the sea bed, the Blefuscu shore, Lilliput across the channel
SHORE_Y = 34.0


def shore_y(x): return SHORE_Y + 4.0 * math.sin(x / 13.0) + 2.0 * math.sin(x / 5.3 + 1.0)


def ground(x, y):
    sy = shore_y(x)
    if y < 0:
        # the channel deepens toward the middle, then rises to Lilliput's coast 730 m off
        z = FEET - 0.7 * ss(0.0, -60.0, y) + 2.5 * ss(-600.0, -730.0, y) + 6.0 * ss(-730.0, -800.0, y) * (0.6 + 0.4 * fbm(x, y, 90, 3, 1.0))
    else:
        z = FEET + (0.0 - FEET) * ss(0.0, sy, y) ** 1.6
        z += 0.6 * ss(sy - 2.0, sy + 6.0, y) + 0.03 * (y - sy) * (y > sy)
        z += 1.2 * ss(sy + 6.0, sy + 40.0, y) * (0.5 + 0.5 * fbm(x, y, 20, 3, 2.0))
        z += 30.0 * ss(150.0, 450.0, y) * (0.6 + 0.4 * fbm(x, y, 120, 3, 3.0))
    return z + 0.05 * fbm(x, y, 3.0, 3, 5.0)


K.polar_terrain("seabed_and_shore", ground, sand, centre=(0.0, 0.0), r_max=880, near_step=0.5, k=0.12, ns=44)
K.water_plane("sea", sea, 0.0, radius=860, centre=(0, 0), rings=12, ns=56,
              foam=lambda x, y: max(0.0, 1.0 - abs(y - shore_y(x)) / 2.5) * 0.8)
# the land above the beach is greener (a second skin over the terrain, behind the quays)
bm = bmesh.new(); xs = np.linspace(-120, 120, 49); ys = np.linspace(0, 1, 9)
grid = []
for t in ys:
    row = []
    for x in xs:
        y = shore_y(x) + 7.0 + t * 400.0 * t
        row.append(bm.verts.new((x * (1 + t * 2.5), y, ground(x * (1 + t * 2.5), y) + 0.03)))
    grid.append(row)
for j in range(len(ys) - 1):
    for i in range(len(xs) - 1):
        bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
rk._obj("fields", bm, land, smooth=True)
K.sky((0.30, 0.50, 0.82), (0.82, 0.86, 0.90), strength=1.0, radius=950, ground_color=(0.35, 0.40, 0.40))

# ----------------------------------------------------------------------------- the harbour: quays, warehouses, the town rising behind
H = rk._B("harbour")
QX0, QX1 = -26.0, 26.0
for i, x in enumerate(np.arange(QX0, QX1, 1.6)):
    y = shore_y(x) - 0.6
    H.box(stone, (1.65, 2.2, 0.55), (x, y, -0.35), (0, 0, 0))
H.box(stone, (1.4, 9.0, 0.5), (-8.0, shore_y(-8.0) - 5.0, -0.35))          # a mole running out
H.box(stone, (1.4, 7.0, 0.5), (11.0, shore_y(11.0) - 4.0, -0.35))
H.box(stone, (0.6, 0.6, 0.75), (-8.0, shore_y(-8.0) - 9.3, -0.35))          # a little light-tower at its end
H.cyl(stone, 0.22, 0.55, (-8.0, shore_y(-8.0) - 9.3, 0.4), sides=8)
H.ball(roof, 0.24, (-8.0, shore_y(-8.0) - 9.3, 0.95), squash=(1, 1, 0.8), sub=1)
# warehouses along the quay (1/12: three storeys about 0.9 m), then houses climbing the slope
def house(Hb, x, y, w, d, h, yaw, tall=False):
    z = ground(x, y) - 0.1
    m = plaster if R.random() < 0.6 else stone
    Hb.box(m, (w, d, h), (x, y, z), (0, 0, yaw))
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    rh = min(w, d) * 0.45
    Hb.mesh(roof, [(x - c * w / 2 - s * d / 2 * -1, y - s * w / 2 + c * -d / 2, z + h), (x + c * w / 2 + s * d / 2, y + s * w / 2 - c * d / 2, z + h),
                   (x + c * w / 2, y + s * w / 2, z + h + rh), (x - c * w / 2, y - s * w / 2, z + h + rh)], [(0, 1, 2, 3)])
    Hb.mesh(roof, [(x + c * w / 2 - s * d / 2, y + s * w / 2 + c * d / 2, z + h), (x - c * w / 2 - s * d / 2, y - s * w / 2 + c * d / 2, z + h),
                   (x - c * w / 2, y - s * w / 2, z + h + rh), (x + c * w / 2, y + s * w / 2, z + h + rh)], [(0, 1, 2, 3)])
    for sx in (-1, 1):
        ex, ey = x + sx * c * w / 2, y + sx * s * w / 2
        Hb.mesh(m, [(ex - s * d / 2, ey + c * d / 2, z + h), (ex + s * d / 2, ey - c * d / 2, z + h), (ex, ey, z + h + rh)], [(0, 1, 2)] if sx > 0 else [(1, 0, 2)])
    if tall:
        wm = rk.M("window_dark") if "window_dark" in rk._mats else K.mat("window_dark", (0.05, 0.05, 0.06), "glass", rough=0.2)
        for f in range(min(2, max(1, int(h / 0.3)))):
            for k in range(int(w / 0.25)):
                u = -w / 2 + 0.125 + k * 0.25
                px, py = x + c * u + s * (d / 2 + 0.004), y + s * u - c * (d / 2 + 0.004)
                Hb.box(wm, (0.08, 0.01, 0.13), (px, py, z + 0.1 + f * 0.3), (0, 0, yaw))
for i, x in enumerate(np.arange(QX0 + 1.0, QX1, 2.4)):
    if abs(x + 8.0) < 1.2 or abs(x - 11.0) < 1.2: continue
    house(H, x + R.uniform(-0.3, 0.3), shore_y(x) + 2.4, R.uniform(1.6, 2.2), R.uniform(1.0, 1.4), R.uniform(0.6, 0.95), R.uniform(-4, 4), tall=True)
H.done()
TW = rk._B("town")
placed = []
for i in range(220):
    x = R.uniform(-60, 60); y = shore_y(x) + R.uniform(6.0, 60.0)
    if any(math.hypot(x - px, y - py) < 1.6 for px, py in placed): continue
    placed.append((x, y))
    d = math.hypot(x, y)
    house(TW, x, y, R.uniform(0.8, 1.6), R.uniform(0.7, 1.1), R.uniform(0.35, 0.6) * (1.0 if d < 60 else 1.3), R.uniform(-10, 10) + (0 if R.random() < 0.7 else 90))
# the emperor of Blefuscu's palace and a temple on the rise behind the town
for (x, y, w, d, h) in ((6.0, shore_y(6.0) + 48.0, 7.0, 4.0, 1.6), (-20.0, shore_y(-20.0) + 40.0, 3.0, 5.0, 1.2)):
    z = ground(x, y)
    TW.box(stone, (w, d, h), (x, y, z - 0.2))
    TW.box(roof, (w + 0.2, d + 0.2, 0.08), (x, y, z - 0.2 + h))
    TW.cyl(stone, 0.5, h * 1.8, (x + w / 2 - 0.5, y, z - 0.2), sides=8)
    TW.cyl(roof, 0.6, 0.9, (x + w / 2 - 0.5, y, z - 0.2 + h * 1.8), sides=8, r1=0.01)
TW.done()
# the crowd: the quays, the shore and the mole dark with people (a speckled skin, no figures)
CB = bmesh.new()
for (x0, x1, off0, off1) in ((QX0, QX1, 0.35, 1.9), (-40.0, -26.0, -1.0, 3.0), (26.0, 44.0, -1.0, 3.0)):
    n = int((x1 - x0) / 0.8)
    rows = []
    for t in (0.0, 1.0):
        rows.append([CB.verts.new((x0 + (x1 - x0) * i / n, shore_y(x0 + (x1 - x0) * i / n) + (off0 if t == 0 else off1),
                                   max(0.0, ground(x0 + (x1 - x0) * i / n, shore_y(x0 + (x1 - x0) * i / n) + (off0 if t == 0 else off1))) + 0.22 + (0.25 if x0 == QX0 else 0.0))) for i in range(n + 1)])
    for i in range(n):
        CB.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
rk._obj("crowd", CB, crowd, smooth=False)
# trees on the hill behind (low masses: at 1/12, an oak is under a metre)
TB = rk._B("woods")
for i in range(60):
    x = R.uniform(-140, 140); y = shore_y(x) + R.uniform(45, 200)
    if any(math.hypot(x - px, y - py) < 2.0 for px, py in placed): continue
    rr = R.uniform(0.6, 1.4) * (1 + y / 150)
    K.scrub(TB, trees, (x, y, ground(x, y) - 0.1), rr, rr * 0.9, seed=i)
TB.done()
# Lilliput's coast across the channel: a low line of land with the white specks of houses
LB = rk._B("lilliput_coast")
for i in range(40):
    x = R.uniform(-500, 500); y = -760.0 + R.uniform(-10, 10)
    LB.box(plaster, (R.uniform(3, 8), 2.0, R.uniform(1.0, 2.5)), (x, y, ground(x, y) - 0.5))
LB.done()


# ----------------------------------------------------------------------------- the fleet at anchor
SH = rk._B("fleet")
SL = rk._B("fleet_sails")
CORDS = rk._B("cords")
PROWS = []


def ship(x, y, heading, L, masts=3, detail=1):
    """A ship of the line at 1/12: a tarred hull with a gilt-yellow wale and a raised stern, masts, yards with the
    sails furled, a bowsprit; anchored, her cable down from the bow."""
    c, s = math.cos(math.radians(heading)), math.sin(math.radians(heading))
    def P(u, v, w): return (x + c * u - s * v, y + s * u + c * v, w)
    B_ = L * 0.27; dr = L * 0.07; fb = L * 0.13
    nst = 10 if detail else 6
    secs = []
    for i in range(nst + 1):
        t = i / nst; u = -L / 2 + L * t
        full = 1 - abs(2 * t - 1.1) ** 3 * 0.8 if t > 0.55 else 1 - abs(2 * t - 1.1) ** 4 * 0.45
        wdt = B_ / 2 * max(0.12, full)
        rail = fb + L * 0.03 * ((2 * t - 1) ** 2) + (L * 0.05 if t < 0.25 else 0.0) + (L * 0.025 if t > 0.82 else 0.0)
        sec = [(0.92, rail), (1.0, fb * 0.55), (1.0, 0.0), (0.82, -dr * 0.6), (0.3, -dr)]
        secs.append([P(u, -wdt * k, z) for k, z in sec] + [P(u, wdt * k, z) for k, z in reversed(sec)])
    for a, b_ in zip(secs, secs[1:]):
        for k in range(len(a) - 1):
            SH.mesh(hullm, [a[k], b_[k], b_[k + 1], a[k + 1]], [(0, 1, 2, 3)])
    # decks: the waist, the raised quarterdeck aft and the forecastle
    def deck(t0, t1, zz):
        i0, i1 = int(t0 * nst), int(t1 * nst)
        q = [secs[i0][0], secs[i0][-1], secs[i1][-1], secs[i1][0]]
        SH.mesh(spar, [(v[0], v[1], zz) for v in q], [(0, 1, 2, 3)])
    deck(0.0, 1.0, fb * 0.85); deck(0.0, 0.25, fb + L * 0.035)
    SH.mesh(hullm, list(reversed(secs[0])), [tuple(range(len(secs[0])))])
    SH.mesh(hullm, secs[-1], [tuple(range(len(secs[-1])))])
    # the painted band with its row of gunports, and a gilt-yellow wale
    for side in (-1, 1):
        for zf, m_, r_ in ((0.62, wale, L * 0.012), (0.95, wale, L * 0.007)):
            pts = []
            for t in np.linspace(0.04, 0.96, 7):
                full = 1 - abs(2 * t - 1.1) ** 3 * 0.8 if t > 0.55 else 1 - abs(2 * t - 1.1) ** 4 * 0.45
                pts.append(P(-L / 2 + L * t, side * B_ / 2 * max(0.12, full) * 1.01, fb * zf))
            if detail: SH.tube(m_, pts, [r_] * len(pts), 4)
        if detail:
            for t in np.linspace(0.2, 0.8, 5):
                full = 1 - abs(2 * t - 1.1) ** 3 * 0.8 if t > 0.55 else 1 - abs(2 * t - 1.1) ** 4 * 0.45
                q = P(-L / 2 + L * t, side * B_ / 2 * max(0.12, full) * 1.03, fb * 0.62)
                SH.box(hullm, (L * 0.03, 0.004, L * 0.02), (q[0], q[1], q[2] - L * 0.01), (0, 0, heading))
    # the stern: windows of the great cabin, a lantern
    st = P(-L / 2 - 0.002, 0, fb + L * 0.02)
    SH.box(wale, (0.004, B_ * 0.6, L * 0.03), st, (0, 0, heading))
    # bowsprit
    SH.seg(spar, P(L / 2 - L * 0.05, 0, fb + L * 0.02), P(L / 2 + L * 0.28, 0, fb + L * 0.12), L * 0.012, L * 0.007, 5)
    PROWS.append(Vector(P(L / 2 + 0.02, 0, fb * 0.5)))
    # masts, yards, furled sails
    mpos = [0.22, -0.05, -0.28][:masts] if masts > 1 else [0.05]
    hgt = [1.0, 1.08, 0.82][:masts] if masts > 1 else [0.9]
    for mp, hk in zip(mpos, hgt):
        mh = L * 0.85 * hk
        b0 = P(L * mp, 0, fb * 0.8)
        SH.seg(spar, b0, P(L * mp, 0, fb + mh), L * 0.012, L * 0.005, 5 if detail else 4)
        for j, (zf, yl) in enumerate(((0.38, 0.62), (0.68, 0.46), (0.9, 0.3))[: (3 if detail else 1)]):
            zz = fb + mh * zf; half = L * yl * 0.5
            SH.seg(spar, P(L * mp, -half, zz), P(L * mp, half, zz), L * 0.006, L * 0.006, 4)
            SL.tube(sail, [P(L * mp + L * 0.004, -half * 0.9, zz + L * 0.006), P(L * mp + L * 0.008, 0, zz + L * 0.012), P(L * mp + L * 0.004, half * 0.9, zz + L * 0.006)],
                    [L * 0.008, L * 0.016, L * 0.008], 5)
        if detail:
            # shrouds to the channels
            for side in (-1, 1):
                for k in range(2):
                    SH.seg(cord, P(L * mp + (k - 0.5) * L * 0.05, side * B_ / 2, fb + L * 0.03), P(L * mp, side * L * 0.01, fb + mh * 0.66), 0.003, 0.003, 3)
            # a pennant at the masthead
            if mp == mpos[0]:
                SH.mesh(flagm, [P(L * mp, 0, fb + mh), P(L * mp, 0, fb + mh - L * 0.02), P(L * mp - L * 0.25, L * 0.03, fb + mh - L * 0.015)], [(0, 1, 2)])
    # the anchor cable from the hawse down into the water
    SH.seg(cord, P(L / 2 - L * 0.02, B_ * 0.3, fb * 0.4), P(L / 2 + L * 0.25, B_ * 0.5, -0.4), 0.006, 0.006, 3)
    # arrows stuck in her side and deck
    for k in range(R.randint(1, 4) if detail else 0):
        u = R.uniform(-L * 0.4, L * 0.4); side = R.choice((-1, 1))
        p = Vector(P(u, side * B_ * 0.5, fb * R.uniform(0.2, 0.9)))
        d = Vector((R.gauss(0, 0.3), R.gauss(0, 0.3), 0.6)).normalized()
        SH.seg(arrow, p, p + d * 0.08, 0.0015, 0.0015, 3)


ships = []
for i in range(58):
    for _ in range(40):
        x = R.gauss(0.0, 7.5); y = R.uniform(4.5, 26.0)
        if abs(x) > 18: continue
        L = R.uniform(1.9, 2.7) if i < 50 else R.uniform(0.9, 1.4)
        if all(math.hypot(x - a, y - b) > (L + l2) * 0.42 for a, b, l2 in ships): break
    ships.append((x, y, L))
    near = math.hypot(x, y) < 10
    ship(x, y, 250 + R.uniform(-18, 18), L, masts=3 if L > 1.6 else 1, detail=1 if near else 0)
SH.done(); SL.done()

# ----------------------------------------------------------------------------- the cords and hooks, gathered at the reader's right hand
KNOT = Vector((0.5, 0.5, 0.03))
for i, pr in enumerate(PROWS[:50]):
    # each cord runs from the knot, floating just under and on the surface, to the hook in the prow
    d = pr - KNOT; n = 6
    pts = []
    for k in range(n + 1):
        t = (k / n) ** 2
        p = KNOT.lerp(pr, t)
        p.z = KNOT.z * (1 - t) + pr.z * t - 0.12 * math.sin(math.pi * t) * (d.length / 10.0)
        if 0 < k < n: p.z = -0.025
        pts.append(p)
    CORDS.tube(cord, pts, [0.0028] * len(pts), 3)
    # the hook: three iron bars twisted together, bent at the end into the hole at the prow
    hk = pr
    CORDS.tube(iron, [hk + Vector((-0.12, 0, 0.0)), hk + Vector((0.0, 0, 0.0)), hk + Vector((0.03, 0, 0.04)), hk + Vector((0.0, 0, 0.07))], [0.008] * 4, 4)
# the knot: the cords tied together, a rough ball of packthread
CORDS.ball(cord, 0.07, tuple(KNOT), squash=(1.4, 1.0, 0.8), sub=1)
CORDS.done()
# arrows standing in the water round the reader, and a few floating
AR = rk._B("arrows")
for i in range(60):
    a = R.uniform(0, 6.283); r = R.uniform(0.45, 3.5)
    if r < 0.6 and abs(a - 1.0) < 0.6: continue
    x, y = r * math.cos(a), r * math.sin(a)
    if math.hypot(x, y - 1.0) < 0.5: continue
    d = Vector((R.gauss(0, 0.3), R.gauss(0, 0.3), 1.0)).normalized()
    p = Vector((x, y, -0.03))
    AR.seg(arrow, p, p + d * 0.07, 0.0018, 0.0018, 3)
    AR.mesh(fletch, [tuple(p + d * 0.055), tuple(p + d * 0.075), tuple(p + d * 0.07 + Vector((0.006, 0, 0)))], [(0, 1, 2)])
AR.done()

# ----------------------------------------------------------------------------- light, sound, reader
K.sun(52, 135, strength=4.2, color=(1.0, 0.96, 0.88), softness=0.8)
K.sound("surf", "shore", (0.0, SHORE_Y, 0.2))
K.sound("gulls", "harbour", (6.0, 24.0, 6.0))
K.sound("rigging", "fleet", (0.0, 10.0, 1.0))
K.sound("crowd", "quays", (-4.0, SHORE_Y + 2.0, 0.5))
E, D = K.reader((0.0, 0.0, FEET), (0.0, 10.0), eye=1.55)
K.reader_cams(eye=1.55)
K.cam("fleet", (3.5, 2.0, 1.2), (-1.0, 14.0, 0.3), lens=22)
K.cam("hooks", (1.2, -0.4, 0.75), (2.0, 4.0, 0.0), lens=24)
K.finish()
