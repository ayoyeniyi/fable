"""
Fable step-in room `ithaca-assembly`: the place of assembly at Ithaca (The Odyssey, Book II, Butler's translation).

"Now when the child of morning, rosy-fingered Dawn, appeared Telemachus rose and dressed himself ... he went to the
place of assembly spear in hand - not alone, for his two hounds went with him ... and when he took his place in his
father's seat even the oldest councillors made way for him." Later "Jove ... sent two eagles from the top of the
mountain, and they ... wheeled and circled about".

The moment: first light, before the people have gathered. The open meeting place is a levelled terrace of beaten
earth on the hillside above the town, about 12 m across, ringed with rough-dressed limestone seats (two rows on the
uphill side). Odysseus's seat, raised on two steps with a back and arms, stands empty at the seaward edge with a fleece
on it; a bronze-headed ash spear leans against it and the herald's staff lies across its arm. Behind the reader a
dry-stone retaining wall drops to the flat-roofed stone houses of the town, the harbour and the grey sea, with the
hills of the next island on the horizon. Ahead, beyond the seats, olive terraces, a few houses and the mountain.
The sun has just cleared the eastern ridge: low, warm light raking across the circle from the right, long shadows.
Two eagles circle high over the mountain. No people, no hounds (a missing figure beats a toy one).

Must NOT be there: Odysseus, a beggar, a bow or axes, Telemachus's ship at sea, columns or marble, coins or writing.

Run (from the repo root):
  blender -b -P blender/build_ithaca_assembly.py -- --render --samples 48 --res 1280
  blender -b -P blender/build_ithaca_assembly.py -- --export
Axes: metres, +Z up; the reader faces +Y (north), the sea is to the south (-Y), the sun in the east (+X).
"""
import bpy, math, random, sys, os
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b3 as K
import roomkit as rk
import alice_foliage as af

ARGS = K.setup("ithaca-assembly", seed=202, samples=48)
R = random.Random(202)
fbm, ss = K.fbm, K.smoothstep

# ----------------------------------------------------------------------------- materials
earth = K.stone_mat("beaten_earth", (0.50, 0.42, 0.31), dark=(0.36, 0.29, 0.21), scale=0.7, rough=0.95, bump=0.35)
hill = K.patchy_mat("hillside", (0.50, 0.46, 0.32), patches=[((0.40, 0.38, 0.24), 0.08, 0.45), ((0.21, 0.25, 0.13), 0.045, 0.42),
                                                              ((0.60, 0.58, 0.52), 0.22, 0.12), ((0.45, 0.37, 0.27), 0.6, 0.3)])
lime = K.stone_mat("limestone_seats", (0.62, 0.57, 0.49), dark=(0.36, 0.33, 0.28), lichen=(0.55, 0.53, 0.40), scale=1.0)
rubble = K.stone_mat("rubble_wall", (0.55, 0.51, 0.44), dark=(0.30, 0.27, 0.23), lichen=(0.50, 0.50, 0.38), scale=1.4)
plaster = K.mat("house_plaster", (0.70, 0.62, 0.50), "plaster", rough=0.92)
roofclay = K.mat("roof_clay", (0.42, 0.35, 0.27), "soil", rough=0.96)
timber = K.mat("old_timber", (0.30, 0.23, 0.16), "wood", rough=0.8)
ash = K.mat("ash_shaft", (0.52, 0.40, 0.26), "wood", rough=0.55)
bronze = K.mat("bronze", (0.55, 0.38, 0.18), "metal", rough=0.38)
fleece = K.mat("fleece", (0.86, 0.82, 0.72), "fabric", rough=0.98)
cloak = K.mat("wool_cloak", (0.40, 0.25, 0.17), "fabric", rough=0.97)
door_dark = K.mat("doorway_dark", (0.07, 0.06, 0.05), "plaster", rough=1.0)
bark = K.mat("olive_bark", (0.36, 0.33, 0.28), "bark", rough=0.92)
sea = K.mat("sea", (0.13, 0.22, 0.27), "water", rough=0.12)
bird = K.mat("eagle", (0.20, 0.14, 0.09), "fabric", rough=0.9)
olive = K.leaf_mat("privet", seed=11, name="olive", per_cell=6,
                   palette=[(0.30, 0.34, 0.24), (0.36, 0.40, 0.29), (0.26, 0.30, 0.21), (0.42, 0.45, 0.34), (0.33, 0.36, 0.27), (0.47, 0.49, 0.40)])
maquis = K.leaf_mat("privet", seed=23, name="lentisk",
                    palette=[(0.13, 0.19, 0.08), (0.17, 0.24, 0.10), (0.21, 0.27, 0.12), (0.15, 0.21, 0.09), (0.25, 0.30, 0.14)])
grass = K.grass_atlas_mat("dry_grass", [(0.66, 0.60, 0.40), (0.58, 0.55, 0.34), (0.50, 0.50, 0.30), (0.72, 0.64, 0.44)], seed=5, dry=0.3)
K.keep(maquis, "veg.shrub.lentisk"); K.keep(olive, "veg.leaves.olive"); K.keep(grass, "veg.grass.dry")
K.size(hill, 1024, 256); K.size(earth, 1024, 256); K.size(lime, 1024, 256); K.size(sea, 256)

# ----------------------------------------------------------------------------- the land
PC = Vector((0.0, 6.5))          # centre of the meeting circle
SEA_Z = -32.0


def land(x, y):
    n = 1.4 * fbm(x, y, 40, 4, 1.3) + 0.3 * fbm(x, y, 9, 3, 4.1)
    if y >= -3.0:
        g = 0.07 * y + 0.0011 * y * max(0.0, y)
    else:
        t_ = -3.0 - y
        g = -(0.22 * t_ + 0.004 * t_ * t_) - 1.1 * (1 - ss(9.0, 15.0, abs(x)))
    # the harbour: the slope runs into the bay; headlands east and west
    bay = -95.0 + 22.0 * math.sin(x / 70.0)
    if y < bay: g = min(g, SEA_Z + 1.5 - 0.6 * (bay - y))
    head = 70.0 * ss(110.0, 260.0, abs(x)) * ss(-40.0, -160.0, y)
    g += head
    # the mountain behind the town (Neritum), and the ridge round to the east
    g += 360.0 * math.exp(-(((x + 80) / 260.0) ** 2 + ((y - 560) / 230.0) ** 2))
    g += 45.0 * math.exp(-(((x - 420) / 160.0) ** 2 + ((y - 260) / 200.0) ** 2))
    g += 60.0 * math.exp(-(((x + 330) / 140.0) ** 2 + ((y - 120) / 200.0) ** 2))
    # the next island across the water, on the south-western horizon
    g += 170.0 * math.exp(-(((x + 420) / 260.0) ** 2 + ((y + 700) / 120.0) ** 2))
    g += 90.0 * math.exp(-(((x - 300) / 200.0) ** 2 + ((y + 760) / 90.0) ** 2))
    z = g + n * (1.0 + abs(g) * 0.04)
    # the levelled terrace of the meeting place
    d = math.hypot(x - PC.x, y - PC.y)
    if y > -3.0:
        k = 1 - ss(9.5, 15.0, d)
        z = z * (1 - k) + (0.03 * fbm(x, y, 2.5, 2, 7.0)) * k
    return z


K.polar_terrain("ground", land, hill, centre=(0.6, 1.0), r_max=900, near_step=0.5, k=0.12, ns=56)
# the trodden earth of the circle (a separate, slightly darker skin over the terrace)
import bmesh
bm = bmesh.new(); rings = []
for i, r in enumerate([0.0, 1.5, 3.0, 4.5, 6.0, 7.2, 8.4]):
    ring = []
    for j in range(48 if r > 0 else 1):
        a = 2 * math.pi * j / 48
        x, y = PC.x + r * math.cos(a) * 1.04, PC.y + r * math.sin(a)
        if y < -2.7: y = -2.7
        ring.append(bm.verts.new((x, y, land(x, y) + 0.012)))
    rings.append(ring)
for j in range(48): bm.faces.new((rings[0][0], rings[1][j], rings[1][(j + 1) % 48]))
for a_, b_ in zip(rings[1:], rings[2:]):
    for j in range(48): bm.faces.new((a_[j], b_[j], b_[(j + 1) % 48], a_[(j + 1) % 48]))
rk._obj("circle_floor", bm, earth, smooth=True)

K.water_plane("sea", sea, SEA_Z, radius=820, centre=(0, -120), rings=10, ns=48)
K.keep(sea, "water.ocean.harbour")
K.sky((0.40, 0.56, 0.80), (0.98, 0.82, 0.68), strength=0.75, radius=1000, ground_color=(0.52, 0.53, 0.56))

# ----------------------------------------------------------------------------- the seats
B = rk._B("seats")
ring_r = 6.2


def seat_block(B, x, y, yaw, L, D=0.5, H=0.44, m=lime, tilt=True):
    z = rk.ground(x, y) - 0.06
    K.rough_block(B, m, (L, D, H), (x, y, z), (R.uniform(-1.5, 1.5) if tilt else 0, R.uniform(-1.5, 1.5) if tilt else 0, yaw + R.uniform(-3, 3)), amp=0.02, seed=R.randint(0, 999))


# front row: from east-south-east round the north to west-south-west, a gap for the path in the east
a = math.radians(-58)
while a < math.radians(238):
    deg = math.degrees(a)
    L = R.uniform(1.0, 1.6)
    da = L / ring_r
    if not (-12 < deg < 10):
        x, y = PC.x + ring_r * math.cos(a + da / 2), PC.y + ring_r * math.sin(a + da / 2)
        seat_block(B, x, y, math.degrees(a + da / 2) + 90, L * 0.96, D=R.uniform(0.46, 0.56), H=R.uniform(0.40, 0.47))
    a += da + R.uniform(0.02, 0.07) / ring_r * 3
# back row on the uphill side, raised on an earth-and-stone step
a = math.radians(28)
while a < math.radians(152):
    L = R.uniform(1.1, 1.7); da = L / 7.1
    x, y = PC.x + 7.1 * math.cos(a + da / 2), PC.y + 7.1 * math.sin(a + da / 2)
    z = rk.ground(x, y)
    B.box(rubble, (L * 1.02, 0.95, 0.42), (x, y, z - 0.05), (0, 0, math.degrees(a + da / 2) + 90), bevel=0.04)   # the step
    K.rough_block(B, lime, (L * 0.95, 0.5, 0.44), (x + 0.2 * math.cos(a + da / 2), y + 0.2 * math.sin(a + da / 2), z + 0.36),
                  (R.uniform(-1, 1), R.uniform(-1, 1), math.degrees(a + da / 2) + 90 + R.uniform(-3, 3)), amp=0.02, seed=R.randint(0, 999))
    a += da + 0.012
# a few loose stones and a worn threshold slab at the path
for i in range(14):
    aa = R.uniform(-1.2, 4.3); rr = R.uniform(6.9, 9.0)
    x, y = PC.x + rr * math.cos(aa), PC.y + rr * math.sin(aa)
    if y < -2.4: continue
    s = R.uniform(0.12, 0.28)
    B.box(lime, (s * R.uniform(1, 1.8), s, s * 0.6), (x, y, rk.ground(x, y) - s * 0.2), (R.uniform(-8, 8), R.uniform(-8, 8), R.uniform(0, 180)), bevel=0.03)
B.box(lime, (1.4, 0.9, 0.12), (PC.x + 8.3, PC.y, rk.ground(PC.x + 8.3, PC.y) - 0.07), (0, 0, 90), bevel=0.02)
B.done()

# ----------------------------------------------------------------------------- Odysseus's seat, the spear and the staff
SX, SY = -1.05, 0.55
S = rk._B("father_seat", (SX, SY, 0.0), 0)
K.rough_block(S, lime, (2.0, 1.55, 0.18), (0, -0.05, -0.04), amp=0.015, seed=7)            # lower step
K.rough_block(S, lime, (1.5, 1.1, 0.18), (0, -0.1, 0.14), amp=0.012, seed=8)               # upper step
K.rough_block(S, lime, (1.0, 0.62, 0.42), (0, -0.18, 0.32), amp=0.012, seed=5)             # the seat
K.rough_block(S, lime, (1.08, 0.2, 0.95), (0, -0.48, 0.32), (-4, 0, 0), amp=0.012, seed=6)  # its back
for sx in (-0.5, 0.5):
    S.box(lime, (0.14, 0.62, 0.30), (sx, -0.18, 0.74), bevel=0.03)        # arms
S.done()
# the fleece over the seat, folded down at the front
fl = rk._B("fleece", (SX, SY, 0.0), 0)
K.rough_block(fl, fleece, (0.86, 0.66, 0.05), (0.0, -0.16, 0.74), amp=0.02, seed=31, cuts=3)
K.rough_block(fl, fleece, (0.80, 0.05, 0.36), (0.0, 0.16, 0.40), (6, 0, 0), amp=0.02, seed=32, cuts=3)
fl.done()
# the spear: ash shaft, bronze leaf blade and butt-spike, leaning against the seat's east arm
sp = rk._B("spear")
base = Vector((SX + 0.9, SY + 0.42, 0.14)); contact = Vector((SX + 0.60, SY - 0.42, 1.24))
topp = base + (contact - base) * 1.95
sp.seg(ash, base, topp, 0.016, 0.014, 8)
dv = (topp - base).normalized(); sd = dv.cross(Vector((0, 0, 1))).normalized()
sp.seg(bronze, topp - dv * 0.02, topp + dv * 0.06, 0.017, 0.016, 8)
sp.mesh(bronze, [tuple(topp + dv * 0.05 + sd * 0.035), tuple(topp + dv * 0.05 - sd * 0.035),
                 tuple(topp + dv * 0.34), tuple(topp + dv * 0.16 + sd.cross(dv) * 0.008), tuple(topp + dv * 0.16 - sd.cross(dv) * 0.008)],
        [(0, 3, 2), (3, 1, 2), (1, 4, 2), (4, 0, 2)])
sp.seg(bronze, base - dv * 0.10, base + dv * 0.02, 0.003, 0.016, 6)
sp.done()
# the herald's staff leaning on the west arm, its foot on the lower step
st = rk._B("staff")
sb = Vector((SX - 0.95, SY + 0.45, 0.14)); sc_ = Vector((SX - 0.58, SY - 0.12, 1.06)); stp = sb + (sc_ - sb) * 1.25
st.seg(timber, sb, stp, 0.017, 0.014, 8)
st.ball(bronze, 0.03, tuple(stp + (stp - sb).normalized() * 0.02), sub=1)
st.done()
# a homespun cloak left folded on the front row (the councillors are on their way)
ck = rk._B("cloak")
cx, cy = PC.x + ring_r * math.cos(math.radians(150)), PC.y + ring_r * math.sin(math.radians(150))
cz = rk.ground(cx, cy) + 0.38
ck.box(cloak, (0.55, 0.42, 0.08), (cx, cy, cz), (0, 0, 60), bevel=0.03)
ck.box(cloak, (0.5, 0.06, 0.36), (cx + 0.18, cy + 0.17, cz - 0.30), (12, 0, 60), bevel=0.02)
ck.done()

# ----------------------------------------------------------------------------- walls
# the retaining wall at the seaward edge of the terrace (coursed rubble with a coping), behind the reader
W = rk._B("retaining")
x = -14.5
while x < 14.5:
    L = R.uniform(0.35, 0.6); zt = 0.12
    zb = min(land(x, -3.25), land(x + L, -3.25)) - 0.2
    zc = zb; k = 0
    while zc < zt:
        hh = min(R.uniform(0.16, 0.26), zt - zc + 0.02)
        W.box(rubble, (L * R.uniform(0.92, 1.02), 0.55, hh * 0.96), (x + L / 2 + (R.uniform(-0.05, 0.05) if k % 2 else 0), -3.2, zc),
              (R.uniform(-2, 2), R.uniform(-2, 2), R.uniform(-2, 2)), bevel=0.02 if (zc + hh >= zt - 0.01 and abs(x) < 6) else 0.0)
        zc += hh; k += 1
    x += L
W.done()
# a low field wall round the uphill side of the terrace (coarser away from the reader)
TW = rk._B("terrace_wall")
pts = [(13.0, -2.8), (14.6, 4.0), (14.0, 12.0), (9.0, 18.0), (0.0, 20.0), (-9.0, 18.0), (-14.0, 12.0), (-14.6, 4.0), (-13.0, -2.8)]
gaps = [(15.0, 6.5, 2.4), (-4.5, 19.4, 1.8)]
for (ax, ay), (bx, by) in zip(pts, pts[1:]):
    L = math.hypot(bx - ax, by - ay); yaw = math.degrees(math.atan2(by - ay, bx - ax)); t = 0.0
    while t < L:
        l = R.uniform(0.55, 0.95); m_ = (t + l / 2) / L
        x, y = ax + (bx - ax) * m_, ay + (by - ay) * m_
        if not any(math.hypot(x - gx, y - gy) < gw / 2 for gx, gy, gw in gaps):
            zc = land(x, y) - 0.15
            for k, hh in enumerate((0.32, 0.28, 0.22) if y < 12 else (0.45, 0.37)):
                o = R.uniform(-0.08, 0.08)
                TW.box(rubble, (l * R.uniform(0.9, 1.0), 0.6 - 0.08 * k, hh), (x + o * math.cos(math.radians(yaw)), y + o * math.sin(math.radians(yaw)), zc),
                       (R.uniform(-2, 2), R.uniform(-2, 2), yaw + R.uniform(-4, 4)))
                zc += hh * 0.97
        t += l
TW.done()

# ----------------------------------------------------------------------------- the town
Hs = rk._B("town")


def house(x, y, w, d, h, yaw, seed):
    r = random.Random(seed)
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    corners = [(x + c * dx - s * dy, y + s * dx + c * dy) for dx in (-w / 2, w / 2) for dy in (-d / 2, d / 2)]
    zs = [land(*p) for p in corners]; zb = min(zs) - 0.6; zt = max(zs) + h
    m = plaster if r.random() < 0.45 else rubble
    Hs.box(m, (w, d, zt - zb), (x, y, zb), (0, 0, yaw))
    Hs.box(roofclay, (w + 0.25, d + 0.25, 0.22), (x, y, zt), (0, 0, yaw), bevel=0.05)
    # beam ends under the roof on the front, a doorway and a small window
    fx_, fy_ = x - s * (-d / 2 - 0.01), y + c * (-d / 2 - 0.01)
    if math.hypot(x, y) < 45:
        for k in range(int(w / 0.6)):
            o = -w / 2 + 0.3 + k * 0.6
            Hs.box(timber, (0.13, 0.25, 0.13), (fx_ + c * o - s * (-0.1), fy_ + s * o + c * (-0.1), zt - 0.17), (0, 0, yaw))
    dz = land(fx_, fy_)
    do = r.uniform(-w * 0.25, w * 0.25)
    Hs.box(door_dark, (0.85, 0.06, 1.75), (fx_ + c * do, fy_ + s * do, max(dz, zb + 0.3)), (0, 0, yaw))
    if w > 4.5:
        wo = do + (1.4 if do < 0 else -1.4)
        Hs.box(door_dark, (0.45, 0.06, 0.45), (fx_ + c * wo, fy_ + s * wo, zt - 1.1), (0, 0, yaw))
    # a courtyard wall in front of some houses
    if r.random() < 0.4:
        cd = r.uniform(2.5, 4.0)
        for (ax, ay, L, yy) in ((-w / 2, -d / 2 - cd / 2, cd, 90), (w / 2, -d / 2 - cd / 2, cd, 90), (0, -d / 2 - cd, w, 0)):
            px, py = x + c * ax - s * ay, y + s * ax + c * ay
            Hs.box(rubble, (L, 0.45, 1.4), (px, py, land(px, py) - 0.4), (0, 0, yaw + yy), bevel=0.05)


placed = []
for i in range(80):
    zone = R.random()
    if zone < 0.62:   # the slope below, down to the harbour
        x, y = R.uniform(-80, 80), R.uniform(-75, -9)
    elif zone < 0.82:   # beside the terrace, east and west
        x, y = R.choice((-1, 1)) * R.uniform(22, 90), R.uniform(-8, 40)
    else:   # a few up the hill beyond the seats
        x, y = R.uniform(-70, 70), R.uniform(30, 90)
    if land(x, y) < SEA_Z + 2.0: continue
    w, d = R.uniform(4.0, 7.5), R.uniform(3.5, 6.0)
    if any(math.hypot(x - px, y - py) < max(w, d) + pw for px, py, pw in placed): continue
    if math.hypot(x - PC.x, y - PC.y) < (14 if y < -5 else 22): continue
    yaw = math.degrees(math.atan2(-y, -x)) * 0.0 + R.uniform(-25, 25) + (0 if y < 0 else 180) * 0
    house(x, y, w, d, R.uniform(2.5, 3.6), yaw, i)
    placed.append((x, y, max(w, d)))
    if len(placed) >= 46: break
Hs.done()
# ----------------------------------------------------------------------------- olives, maquis and grass
trees = [(-9.5, 21.5, 6.5, 3.3), (10.5, 22.0, 5.5, 2.8), (-17.5, 9.0, 6.0, 3.0), (17.0, 13.5, 6.8, 3.4), (-15.5, -6.5, 5.0, 2.6),
         (16.0, -7.0, 5.8, 2.9), (-4.0, 27.0, 6.0, 3.0), (26.0, 30.0, 6.0, 3.0), (-28.0, 26.0, 6.5, 3.2), (4.0, 36.0, 6.0, 3.0)]
for i, (x, y, h, sp_) in enumerate(trees):
    near = math.hypot(x, y) < 15
    K.tree(f"olive{i}", (x, y), h, sp_, bark, olive, seed=40 + i, trunk_frac=0.38, r0=h * 0.045, nlimbs=5 if near else 3,
           detail=1.0 if near else 0.5, card=1.5, fill=90 if near else 60, lobes=4, flat=0.6,
           lean=(R.uniform(-0.05, 0.05), R.uniform(-0.05, 0.05)), branch_per_limb=3 if near else 2, cards_per_tip=3 if near else 4)
# olive groves on the terraces further off: smaller, simpler
for i in range(10):
    x, y = R.uniform(-150, 150), R.uniform(-60, 160)
    if math.hypot(x - PC.x, y - PC.y) < 35 or land(x, y) < SEA_Z + 3: continue
    if any(math.hypot(x - px, y - py) < pw + 3 for px, py, pw in placed): continue
    h = R.uniform(4.5, 6.5)
    K.tree(f"grove{i}", (x, y), h, h * 0.5, bark, olive, seed=100 + i, trunk_frac=0.4, r0=h * 0.04, nlimbs=3, detail=0.3, card=1.6,
           fill=18, lobes=3, flat=0.6, branch_per_limb=1, cards_per_tip=1)
for i, (x, y, rr) in enumerate([(-12.0, 15.5, 0.9), (12.4, 16.0, 1.1), (-14.6, 2.0, 0.8), (14.0, -0.5, 1.0), (9.5, 19.5, 0.7),
                                (-7.0, 20.0, 0.8), (-12.5, -4.8, 0.9), (12.0, -5.0, 0.8), (21.0, 4.0, 1.2), (-22.0, 3.0, 1.1)]):
    K.shrub(f"lentisk{i}", (x, y), rr, rr * 1.1, bark, maquis, seed=300 + i, card=0.5, fill=26)
K.grass_cards("grass_near", (-15, -2.6, 15, 22), 620, 0.30, grass, seed=8, clusters=70, spread=0.5, avoid=[(PC.x, PC.y, 6.6), (SX, SY, 1.4), (0.7, 0.8, 1.0)])
K.grass_cards("grass_slope", (-40, -25, 40, 40), 220, 0.4, grass, seed=9, clusters=40, spread=1.0, avoid=[(PC.x, PC.y, 13.0)])

# maquis on the hillsides: lentisk and myrtle bushes clustered on the steeper, rockier ground
mq = [(-24, 14), (-27, 19), (-31, 12), (22, 18), (26, 23), (29, 15), (-18, 30), (15, 33), (35, 30), (-36, 26)]
for i, (x, y) in enumerate(mq):
    rr = R.uniform(0.9, 1.5)
    K.shrub(f"maquis{i}", (x, y), rr, rr * 1.1, bark, maquis, seed=500 + i, card=0.75, fill=14)

# limestone breaking through the thin soil: outcrops and loose stones, half buried
RK = rk._B("outcrops")
for i in range(46):
    if i < 16: x, y = R.uniform(-14, 14), R.uniform(9, 21)
    else: x, y = R.uniform(-45, 45), R.uniform(-30, 45)
    if math.hypot(x - PC.x, y - PC.y) < 7.6 or (abs(x) < 15 and -4 < y < 3): continue
    sz = R.uniform(0.25, 0.7) if i < 16 else R.uniform(0.4, 1.6)
    K.rough_block(RK, rubble, (sz * R.uniform(1.0, 1.8), sz * R.uniform(0.8, 1.3), sz * 0.7), (x, y, land(x, y) - sz * 0.35),
                  (R.uniform(-12, 12), R.uniform(-12, 12), R.uniform(0, 180)), amp=sz * 0.12, seed=i)
RK.done()

# ----------------------------------------------------------------------------- the two eagles, high over the mountain
EG = rk._B("eagles")
for (x, y, z, yaw, bank) in ((-30, 95, 75, 30, 18), (-8, 120, 88, 200, -22)):
    c = Vector((x, y, z))
    EG.ball(bird, 0.32, (x, y, z), squash=(2.6, 0.7, 0.6), sub=1, rot=(bank, 0, yaw))
    for sgn in (-1, 1):
        q = [Vector((0.25, 0, 0)), Vector((0.55, sgn * 1.2, 0.15)), Vector((0.25, sgn * 2.4, 0.28)), Vector((-0.15, sgn * 2.5, 0.25)),
             Vector((-0.35, sgn * 1.1, 0.1)), Vector((-0.35, 0, 0))]
        from mathutils import Euler
        M = Euler((math.radians(bank), 0, math.radians(yaw))).to_matrix()
        pts = [tuple(c + M @ p) for p in q]
        EG.mesh(bird, pts, [(0, 1, 4, 5), (1, 2, 3, 4)] if sgn > 0 else [(5, 4, 1, 0), (4, 3, 2, 1)])
    tl = [Vector((-0.6, 0, 0)), Vector((-1.3, 0.35, 0)), Vector((-1.3, -0.35, 0))]
    EG.mesh(bird, [tuple(c + M @ p) for p in tl], [(0, 1, 2)])
EG.done()

# ----------------------------------------------------------------------------- light, sound, reader
K.sun(11, 15, strength=3.6, color=(1.0, 0.80, 0.58), softness=1.2)
K.sound("wind", "hill", (0.0, -12.0, 2.0))
K.sound("birds", "olives", (-10.0, 21.0, 4.0))
K.sound("crowd", "benches", (2.0, 14.0, 1.0))
K.sound("gulls", "harbour", (-10.0, -80.0, -20.0))
E, D = K.reader((0.75, 0.75), (0.75, 12.0))
K.reader_cams()
K.cam("circle", (9.5, -1.8, 3.4), (-1.5, 6.5, 0.4), lens=20)
K.cam("seat", (1.6, 3.6, 1.35), (SX, SY - 0.2, 0.75), lens=28)
K.finish()
