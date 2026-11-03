paving = kit.mat("paving", (0.50, 0.48, 0.44), kind="rock")
flags = kit.mat("flags", (0.56, 0.54, 0.50), kind="rock")
flags2 = kit.mat("flags2", (0.49, 0.47, 0.43), kind="rock")
cobbles = kit.mat("cobbles", (0.38, 0.36, 0.33), kind="rock")
granite = kit.mat("granite", (0.42, 0.41, 0.39), kind="rock")
deckwood = kit.mat("pierdeck", (0.40, 0.34, 0.27), kind="wood")
spile = kit.mat("spiles", (0.27, 0.22, 0.17), kind="wood")
hull_a = kit.mat("hull_black", (0.08, 0.08, 0.08), kind="wood")
hull_b = kit.mat("hull_green", (0.12, 0.17, 0.14), kind="wood")
spar = kit.mat("spars", (0.45, 0.36, 0.24), kind="wood")
rope = kit.mat("rope", (0.22, 0.18, 0.13), kind="fabric")
canvas = kit.mat("canvas", (0.80, 0.76, 0.66), kind="fabric")
iron = kit.mat("iron", (0.10, 0.10, 0.11), kind="rock")
cask = kit.mat("casks", (0.42, 0.30, 0.19), kind="wood")
crate = kit.mat("crates", (0.55, 0.46, 0.33), kind="wood")
water = kit.mat("harbour", (0.12, 0.20, 0.24), kind="water")
brick = kit.mat("brick", (0.50, 0.30, 0.24), kind="brick")
slate = kit.mat("slate", (0.25, 0.26, 0.28), kind="rock")
trim = kit.mat("trim", (0.78, 0.75, 0.68), kind="plaster")
glass = kit.mat("glass", (0.12, 0.14, 0.16), kind="plaster")
bark = kit.mat("bark", (0.25, 0.21, 0.16), kind="bark")
leaves = kit.mat("leaves", (0.22, 0.32, 0.14), kind="foliage")
bench_wood = kit.mat("bench", (0.36, 0.26, 0.17), kind="wood")
weeds = kit.mat("weeds", (0.32, 0.38, 0.18), kind="foliage")
sacking = kit.mat("sacking", (0.58, 0.50, 0.38), kind="fabric")
puddle = kit.mat("puddle", (0.20, 0.24, 0.27), kind="water")

R = kit.rng()

# the paved mole ends at y = 6; beyond it is open harbour
kit.terrain("mole", (120, 46), paving, res=50, relief=0.03, scale=10, seed=2,
            flat=[(0, -8, 30, 0.0)], centre=(0, -17))
kit.water("water", (190, 190), -0.9, water)

# granite mole face and kerb
kit.box("moleface", (120, 0.8, 3.2), (0, 6.4, -3.0), granite)
x = -9.0
i = 0
while x < 9.0:
    l = R.uniform(1.1, 1.8)
    kit.box(f"kerb{i}", (l - 0.03, 0.55, 0.28), (x + l / 2, 6.1, -0.02), granite,
            rot=(0, 0, R.uniform(-1.5, 1.5)), bevel=0.03)
    x += l
    i += 1
for side in (-1, 1):
    x = 13.2
    while x < 40:
        l = R.uniform(1.2, 1.9)
        kit.box(f"kerbo{side}_{i}", (l - 0.03, 0.55, 0.26), (side * (x + l / 2), 6.1, -0.02), granite,
                rot=(0, 0, R.uniform(-1.5, 1.5)), bevel=0.03)
        x += l
        i += 1

# laid granite flags around the reader: staggered courses with visible joints
y = -3.2
row = 0
while y < 5.75:
    d = min(R.uniform(0.7, 0.95), 5.8 - y)
    x = -8.5 - (row % 2) * R.uniform(0.3, 0.6)
    k = 0
    while x < 8.5:
        w = R.uniform(0.75, 1.35)
        m = flags if R.random() < 0.55 else flags2
        kit.box(f"flag{row}_{k}", (w - 0.035, d - 0.035, 0.05), (x + w / 2, y + d / 2, -0.03 + R.uniform(-0.008, 0.008)),
                m, rot=(R.uniform(-0.4, 0.4), R.uniform(-0.4, 0.4), R.uniform(-0.6, 0.6)))
        x += w
        k += 1
    y += d
    row += 1

# flagged walk continuing along the quay edge beyond the laid field, cart lane before the warehouses
kit.footpath("quaywalkL", [(-40, 4.7), (-25, 4.8), (-9, 4.75)], flags, width=1.8, wear=0.15, seed=3)
kit.footpath("quaywalkR", [(9, 4.75), (25, 4.7), (40, 4.8)], flags, width=1.8, wear=0.15, seed=6)
kit.footpath("cartlane", [(-45, -7.0), (-15, -6.2), (0, -6.0), (18, -6.4), (45, -7.2)], cobbles,
             width=3.4, ruts=True, puddles=puddle, wear=0.35, seed=4)
# weeds only in joints: along the kerb, wall feet and corners
for i, (tx, ty) in enumerate([(-6.0, 5.78), (2.5, 5.8), (7.8, 5.78), (-8.4, 1.5), (8.6, -2.2),
                              (-14, -12.3), (6, -13.3), (17, -11.8), (-3.0, -12.9), (-11, 5.7), (12.5, 5.7)]):
    kit.tufts(f"tuft{i}", (tx, ty), 0.35, 18, 0.16, weeds, seed=i)

def line(name, p1, p2, mat, r=0.03):
    dx, dy, dz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    th = math.degrees(math.acos(dz / L))
    ph = math.degrees(math.atan2(dy, dx))
    kit.cylinder(name, r, L, p1, mat, rot=(0, th, ph), sides=4)

def hull(name, cx, y0, L, B, D, wl, mat):
    n = 10
    verts = []
    for i in range(n + 1):
        t = i / n
        if t <= 0.5:
            f = 0.6 + 0.4 * math.sin(math.pi * t)
        else:
            f = max(0.04, math.sin(math.pi * t) ** 0.8)
        hb = B / 2 * f
        y = y0 + L * t
        top = wl + D * 0.45 + 0.5 * (2 * t - 1) ** 2
        bot = wl - D * 0.55
        for (sx, z) in [(-hb, top), (-hb * 0.95, wl), (-hb * 0.45, bot), (hb * 0.45, bot), (hb * 0.95, wl), (hb, top)]:
            verts.append((cx + sx, y, z))
    faces = []
    for i in range(n):
        a = i * 6
        b = (i + 1) * 6
        for j in range(5):
            faces.append((a + j, b + j, b + j + 1, a + j + 1))
        faces.append((a + 5, b + 5, b, a))
    faces.append(tuple(range(5, -1, -1)))
    faces.append(tuple(range(n * 6, n * 6 + 6)))
    kit.mesh(name, verts, faces, mat)

def ship(tag, cx, y0, L, B, hmat, masts, D=5.0):
    hull(tag + "hull", cx, y0, L, B, D, -0.9, hmat)
    kit.box(tag + "house", (B * 0.4, L * 0.13, 1.4), (cx, y0 + L * 0.12, 1.3), spar, bevel=0.05)
    tops = []
    for k, (t, h) in enumerate(masts):
        my = y0 + L * t
        kit.cylinder(f"{tag}mast{k}", 0.28, h, (cx, my, 1.2), spar, sides=8, top_radius=0.12)
        for m, fr in enumerate((0.42, 0.62, 0.8, 0.93)):
            w = B * 1.9 * (1 - 0.55 * fr)
            z = 1.2 + h * fr
            a = R.uniform(-4, 4)
            kit.box(f"{tag}yard{k}_{m}", (w, 0.22, 0.22), (cx, my, z), spar, rot=(0, 0, a))
            kit.box(f"{tag}furl{k}_{m}", (w * 0.85, 0.4, 0.32), (cx, my + 0.05, z - 0.3), canvas, rot=(0, 0, a), bevel=0.1)
        for s in (-1, 1):
            for off in (-0.8, 0.0, 0.8):
                line(f"{tag}shroud{k}{s}{off}", (cx + s * B * 0.47, my + off - 1.2, 1.4), (cx, my, 1.2 + h * 0.62), rope, 0.025)
        tops.append((cx, my, 1.2 + h * 0.97))
    bow = (cx, y0 + L - 0.3, 1.7)
    tip = (cx, y0 + L + L * 0.27, 4.2)
    line(tag + "bowsprit", bow, tip, spar, 0.18)
    line(tag + "forestay", tip, tops[-1], rope, 0.03)
    for k in range(len(tops) - 1):
        line(f"{tag}stay{k}", tops[k + 1], (cx, tops[k][1], tops[k][2] * 0.6), rope, 0.03)
    line(tag + "backstay", tops[0], (cx, y0 + 0.5, 2.0), rope, 0.03)

def pier(tag, x0, x1, y0, y1):
    kit.box(tag + "deck", (x1 - x0, y1 - y0, 0.25), ((x0 + x1) / 2, (y0 + y1) / 2, -0.05), deckwood)
    y = y0 + 1.0
    k = 0
    while y < y1:
        for xx in (x0, x1):
            kit.cylinder(f"{tag}spile{k}", R.uniform(0.13, 0.18), R.uniform(3.6, 4.1),
                         (xx, y, -3.2), spile, rot=(R.uniform(-2, 2), R.uniform(-2, 2), 0), sides=7)
            k += 1
        y += R.uniform(2.6, 3.4)

pier("lp", -13, -9, 6, 34)
pier("rp", 9, 13, 6, 32)
ship("sa", -17.2, 9.0, 30.0, 7.0, hull_a, [(0.22, 21.0), (0.5, 25.0), (0.75, 23.0)])
ship("sb", 17.4, 11.0, 27.0, 6.5, hull_b, [(0.25, 19.0), (0.52, 23.0), (0.77, 21.0)])
# a small vessel at anchor far out, well off the reading line
ship("sc", -30.0, 62.0, 16.0, 4.2, hull_a, [(0.35, 12.0), (0.68, 13.5)], D=3.0)

# bollards along the kerb and piers
for i, (bx, by) in enumerate([(-7.0, 5.4), (-3.2, 5.5), (3.4, 5.4), (7.2, 5.5), (-9.4, 14), (-9.4, 24), (9.4, 16), (9.4, 26),
                              (-18, 5.5), (-25, 5.4), (19, 5.5), (26, 5.4)]):
    kit.cylinder(f"bollard{i}", 0.17, 0.62, (bx, by, 0.0 if by < 6 else 0.2), iron, sides=10, top_radius=0.21)
line("mooringA", (-9.4, 14, 0.7), (-13.6, 16, 1.6), rope, 0.035)
line("mooringB", (9.4, 26, 0.7), (14.3, 27, 1.5), rope, 0.035)
line("mooringC", (7.2, 5.5, 0.55), (9.6, 8.0, 0.25), rope, 0.03)

# casks, crates and coiled rope, left and right of the page
for i, (bx, by) in enumerate([(-4.2, 2.6), (-4.8, 3.2), (-3.9, 3.4), (-5.3, 2.3), (-5.9, 3.0)]):
    kit.cylinder(f"cask{i}", 0.3, 0.88, (bx, by, 0.0), cask, sides=12, rot=(0, 0, R.uniform(0, 30)))
kit.cylinder("caskside", 0.3, 0.88, (-3.4, 1.9, 0.3), cask, rot=(90, 0, 35), sides=12)
kit.cylinder("castop", 0.3, 0.88, (-4.5, 2.9, 0.88), cask, sides=12)
kit.box("crate0", (0.9, 0.7, 0.6), (4.6, 3.0, 0.0), crate, rot=(0, 0, 8), bevel=0.02)
kit.box("crate1", (0.7, 0.7, 0.55), (5.3, 3.6, 0.0), crate, rot=(0, 0, -12), bevel=0.02)
kit.box("crate2", (0.6, 0.55, 0.45), (4.7, 3.05, 0.6), crate, rot=(0, 0, 21), bevel=0.02)
kit.box("crate3", (1.1, 0.8, 0.7), (5.8, 2.4, 0.0), crate, rot=(0, 0, 3), bevel=0.02)
for i, (sx, sy, sz) in enumerate([(5.2, 1.9, 0.0), (5.6, 1.6, 0.0), (5.4, 1.75, 0.22)]):
    kit.blob(f"sack{i}", 0.32, (sx, sy, sz + 0.14), sacking, squash=(1.3, 0.9, 0.45), roughness=0.15, seed=i)
kit.cylinder("coil0", 0.42, 0.14, (3.0, 4.6, 0.0), rope, sides=14)
kit.cylinder("coil1", 0.32, 0.12, (3.0, 4.6, 0.14), rope, sides=14)
for i, (bx, by) in enumerate([(-11.5, 10.5), (-10.8, 11.2), (11.6, 9.0)]):
    kit.cylinder(f"piercask{i}", 0.3, 0.88, (bx, by, 0.2), cask, sides=10)
kit.box("piercrate", (1.0, 0.8, 0.7), (11.0, 12.5, 0.2), crate, rot=(0, 0, 14))

# handcarts resting on the quay for Sunday
def cart(tag, x, y, r, tilt=0):
    kit.box(tag + "bed", (1.7, 0.95, 0.08), (x, y, 0.5), deckwood, rot=(tilt, 0, r))
    ca, sa = math.cos(math.radians(r)), math.sin(math.radians(r))
    for s in (-1, 1):
        wx, wy = x - sa * s * 0.55, y + ca * s * 0.55
        kit.cylinder(tag + f"wheel{s}", 0.46, 0.07, (wx, wy, 0.44), spar, rot=(90, 0, r), sides=14)
        kit.box(tag + f"side{s}", (1.7, 0.05, 0.25), (x - sa * s * 0.45, y + ca * s * 0.45, 0.58), deckwood, rot=(tilt, 0, r))
        line(tag + f"shaft{s}", (x + ca * 0.85 - sa * s * 0.35, y + sa * 0.85 + ca * s * 0.35, 0.55),
             (x + ca * 2.2 - sa * s * 0.3, y + sa * 2.2 + ca * s * 0.3, 0.05), spar, 0.035)
cart("cartA", -7.5, -4.5, 160)
cart("cartB", 11.0, -10.5, 75)
kit.cylinder("cartcask", 0.3, 0.8, (-7.5, -4.5, 0.58), cask, sides=10)

# goods stacked under the warehouses
for i, (gx, gy) in enumerate(kit.scatter((-26, -13.6, 26, -12.0), 16, seed=8, clusters=4, avoid=[(0, -13, 2.0)])):
    if i % 3 == 0:
        kit.box(f"wcrate{i}", (R.uniform(0.6, 1.1), R.uniform(0.6, 0.9), R.uniform(0.5, 0.8)), (gx, gy, -0.02), crate,
                rot=(0, 0, R.uniform(-15, 15)), bevel=0.02)
    else:
        kit.cylinder(f"wcask{i}", 0.3, 0.88, (gx, gy, -0.02), cask, sides=10)
kit.box("timberstack", (4.0, 1.0, 0.6), (15.0, -3.0, -0.02), spar, rot=(0, 0, 6))
kit.box("timberstack2", (3.6, 0.8, 0.3), (15.1, -3.0, 0.58), spar, rot=(0, 0, 9))

# benches and lamp posts on the promenade
for i, (bx, by, r) in enumerate([(-6.5, -1.5, 3), (6.8, -0.8, -4)]):
    kit.box(f"benchseat{i}", (1.8, 0.45, 0.06), (bx, by, 0.42), bench_wood, rot=(0, 0, r))
    kit.box(f"benchback{i}", (1.8, 0.06, 0.4), (bx, by - 0.24, 0.55), bench_wood, rot=(0, 0, r))
    for s in (-0.8, 0.8):
        kit.box(f"benchleg{i}{s}", (0.06, 0.45, 0.42), (bx + s, by, 0.0), iron, rot=(0, 0, r))
for i, (lx, ly) in enumerate([(-8.0, 3.5), (8.3, 2.8), (-20, 3.6), (21, 3.4)]):
    kit.cylinder(f"lamppost{i}", 0.07, 3.2, (lx, ly, 0.0), iron, sides=8)
    kit.box(f"lantern{i}", (0.3, 0.3, 0.42), (lx, ly, 3.2), glass)
    kit.box(f"lantcap{i}", (0.38, 0.38, 0.06), (lx, ly, 3.62), iron)

# warehouses behind, shade trees kept to the sides
for i, (hx, hy, w, d) in enumerate([(-21, -19, 16, 12), (0, -20, 18, 12), (21, -18.5, 16, 12)]):
    kit.house(f"warehouse{i}", (hx, hy), (w, d), brick, slate, trim, glass, storeys=4, rot=180,
              roof_kind="flat", storey_height=3.0, chimneys=1, detail=1, seed=i)
for i, hx in enumerate((-40, 40)):
    kit.house(f"farware{i}", (hx, -18), (18, 12), brick, slate, trim, glass, storeys=4, rot=180,
              roof_kind="gable", storey_height=3.0, chimneys=2, detail=0, seed=5 + i)
kit.tree("tree0", (-16.0, -9.5), 10.0, bark, leaves, seed=1, lean=4, detail=1)
kit.tree("tree1", (12.0, -9.0), 9.0, bark, leaves, seed=2, lean=7, detail=1)
kit.tree("tree2", (-28.0, -10.0), 8.5, bark, leaves, seed=3, lean=5, detail=1)

# a low, hazy far shore across the harbour
kit.far_hills((0.52, 0.60, 0.64), radius=100, height=3.0, seed=6)
kit.sun(40, 195, strength=3.8, color=(1.0, 0.94, 0.82))
kit.sky((0.38, 0.56, 0.82), (0.82, 0.85, 0.86), strength=1.0)
kit.reader((0, 0), (0, 14, 1.3))
