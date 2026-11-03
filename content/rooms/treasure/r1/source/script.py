# The cove below the Admiral Benbow: frosty shingle at sunrise, quiet silver sea ahead.
R = kit.rng()
shingle = kit.mat("shingle", (0.47, 0.46, 0.44), kind="rock", rough=0.9)
pebble = kit.mat("pebble", (0.43, 0.41, 0.38), kind="rock")
pebble2 = kit.mat("pebble2", (0.62, 0.63, 0.62), kind="rock")
cliff = kit.mat("cliff", (0.36, 0.34, 0.31), kind="rock")
cliff2 = kit.mat("cliff2", (0.42, 0.39, 0.34), kind="rock")
turf = kit.mat("turf", (0.40, 0.43, 0.36), kind="grass")
frostgrass = kit.mat("frostgrass", (0.56, 0.58, 0.54), kind="foliage")
weed = kit.mat("weed", (0.20, 0.17, 0.10), kind="foliage")
sea = kit.mat("sea", (0.30, 0.35, 0.38), kind="water", rough=0.04)
hull = kit.mat("hull", (0.30, 0.24, 0.18), kind="wood")
plank = kit.mat("oar", (0.48, 0.40, 0.30), kind="wood")
walls = kit.mat("innwalls", (0.80, 0.78, 0.72), kind="plaster")
roof = kit.mat("slate", (0.26, 0.27, 0.29), kind="rock")
trim = kit.mat("trim", (0.85, 0.84, 0.80), kind="wood")
glass = kit.mat("glass", (0.18, 0.20, 0.22), kind="glass", rough=0.05)
sign = kit.mat("signpaint", (0.22, 0.30, 0.42), kind="wood")
road = kit.mat("road", (0.42, 0.38, 0.32), kind="soil")
gorse = kit.mat("gorse", (0.27, 0.31, 0.20), kind="foliage")
bark = kit.mat("bark", (0.24, 0.20, 0.16), kind="bark")

# Land: beach levelled at the reader, rising to the inn behind, falling into the sea ahead.
kit.terrain("ground", (120, 120), shingle, res=96, relief=0.45, scale=9, seed=7,
            slope=(0.0, -0.09), flat=[(0, 0, 2.5, 0.45), (0, -30, 8.0, 3.4)],
            shore=(90, 6.5, 2.5), centre=(0, 0))
kit.water("sea", (240, 200), 0.05, sea, centre=(0, 90))


def cliff_face(name, pts, heights, side, mat, capmat, seed, nu=60, nv=28):
    L = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = L[-1]
    verts, faces, cverts, cfaces = [], [], [], []
    rows = [(0.0, 0.0), (1.2, 0.3), (5.0, 0.8), (14.0, 1.6)]
    for i in range(nu):
        d = total * i / (nu - 1)
        k = 0
        while k < len(pts) - 2 and L[k + 1] < d:
            k += 1
        seg = L[k + 1] - L[k]
        t = (d - L[k]) / seg if seg > 0 else 0.0
        a, b = pts[k], pts[k + 1]
        px = a[0] + (b[0] - a[0]) * t
        py = a[1] + (b[1] - a[1]) * t
        H = heights[k] + (heights[k + 1] - heights[k]) * t
        tx, ty = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
        nx, ny = -ty, tx
        if nx * side > 0:
            nx, ny = -nx, -ny
        H *= 1.0 + 0.18 * noise.noise(Vector((d * 0.07, seed, 0.3)))
        base = kit.ground(px, py) - 1.2
        buttress = 1.4 * noise.noise(Vector((d * 0.09, seed * 1.3, 1.7)))
        top = None
        for j in range(nv):
            v = j / (nv - 1)
            z = base + v * (H + 1.2)
            layer = math.floor((z - base) / 1.1)
            off = buttress * (0.6 + 0.4 * v) - (v ** 1.4) * H * 0.3
            off += 0.6 * noise.noise(Vector((layer * 2.3 + seed, d * 0.12, 0.5)))
            off += 0.2 * noise.noise(Vector((px * 0.6, py * 0.6, z * 0.6)))
            top = (px + nx * off, py + ny * off, z)
            verts.append(top)
        for r, (back, dz) in enumerate(rows):
            jit = 0.0 if r == 0 else 0.35 * noise.noise(Vector((top[0] * 0.2 + back, top[1] * 0.2, 2.0)))
            cverts.append((top[0] - nx * back, top[1] - ny * back, top[2] + dz + jit - (0.15 if r == 0 else 0.0)))
    for i in range(nu - 1):
        for j in range(nv - 1):
            a = i * nv + j
            faces.append((a, a + nv, a + nv + 1, a + 1))
        for r in range(len(rows) - 1):
            a = i * len(rows) + r
            cfaces.append((a, a + len(rows), a + len(rows) + 1, a + 1))
    kit.mesh(name, verts, faces, mat, smooth=True)
    kit.mesh(name + "top", cverts, cfaces, capmat, smooth=True)


# Cliffs left, headland right: stratified faces, low at the slope behind, high toward the sea.
cliff_face("cliffL", [(-12, -15), (-12.5, -6), (-14, 2), (-15.5, 12), (-19, 26), (-27, 46), (-34, 62)],
           [2.5, 8, 14, 17, 20, 22, 18], -1, cliff, turf, 3)
cliff_face("cliffR", [(11, -14), (11.5, -5), (12.5, 6), (16, 22), (23, 42), (32, 60)],
           [2.5, 9, 15, 19, 20, 16], 1, cliff2, turf, 9)

# Talus of fallen rock at the cliff feet.
for i, (x, y) in enumerate(kit.scatter((-12.5, -6, -9, 7), 13, seed=9, clusters=3)):
    kit.rock(f"talusL{i}", (x, y), R.uniform(0.4, 1.6), cliff if i % 2 else cliff2, seed=i + 80)
for i, (x, y) in enumerate(kit.scatter((8.5, -4, 11.5, 6), 10, seed=19, clusters=3)):
    kit.rock(f"talusR{i}", (x, y), R.uniform(0.4, 1.3), cliff2 if i % 2 else cliff, seed=i + 120)

# The big rock at the turn of the beach (left, middle distance), lesser rocks right.
kit.rock("bigrock", (-6.5, 5.6), 3.4, cliff2, seed=3, bury=0.25, flat=0.85)
kit.rock("bigrock2", (-4.9, 6.7), 1.2, cliff, seed=13)
kit.rock("bigrock3", (-7.8, 4.2), 0.8, cliff, seed=23)
kit.rock("rockR1", (4.6, 3.4), 1.1, cliff, seed=5)
kit.rock("rockR2", (5.6, 4.4), 0.7, cliff2, seed=6)

# Shingle: dense clustered stones, frost-pale and dark, thick around the reader.
for i, (x, y) in enumerate(kit.scatter((-8, -5, 8, 6.5), 110, seed=4, clusters=9, spread=0.45,
                                       avoid=[(0, 0, 0.6), (0, 1.0, 0.7)])):
    kit.rock(f"pebble{i}", (x, y), R.uniform(0.06, 0.26), pebble2 if i % 3 else pebble,
             seed=i + 40, bury=0.5)
for i, (x, y) in enumerate(kit.scatter((-7, 4.5, 8, 7.0), 18, seed=14, clusters=4)):
    kit.rock(f"cobble{i}", (x, y), R.uniform(0.25, 0.5), pebble, seed=i + 300, bury=0.45)
kit.tufts("frostbeach0", (-3.5, -2.5), 2.0, 60, 0.16, frostgrass, seed=21)
kit.tufts("frostbeach1", (3.8, -3.0), 1.8, 50, 0.14, frostgrass, seed=22)
kit.tufts("frostbeach2", (-1.5, -4.2), 1.5, 40, 0.15, frostgrass, seed=23)

# A rowing boat drawn up on the shingle, to the right, with planked inside and thwart.
yaw = math.radians(-35)
bx, by = 5.6, -0.8
bz = kit.ground(bx, by) - 0.05
n = 9


def hull_verts(scale, lift):
    vs = []
    for s in range(n):
        t = -1 + 2 * s / (n - 1)
        w = 0.62 * scale * max(0.03, 1 - t * t) ** 0.6
        Lg = t * 1.6 * (scale ** 0.3)
        sheer = 0.5 + 0.12 * t * t
        for (u, z) in [(-w, sheer), (-0.75 * w, 0.14), (0.0, 0.0), (0.75 * w, 0.14), (w, sheer)]:
            z2 = z * (1 if scale == 1 else 0.97) + lift + u * 0.18
            x2 = u * math.cos(yaw) - Lg * math.sin(yaw)
            y2 = u * math.sin(yaw) + Lg * math.cos(yaw)
            vs.append((bx + x2, by + y2, bz + z2))
    return vs


outer, inner, fo, fi = hull_verts(1.0, 0.0), hull_verts(0.92, 0.04), [], []
for s in range(n - 1):
    for k in range(4):
        a = s * 5 + k
        fo.append((a, a + 1, a + 6, a + 5))
        fi.append((a, a + 5, a + 6, a + 1))
kit.mesh("boat", outer, fo, hull, smooth=True)
kit.mesh("boatin", inner, fi, plank, smooth=True)
kit.box("thwart", (1.0, 0.18, 0.04), (bx, by, bz + 0.34), plank, rot=(8, 0, -35))
kit.box("oar", (0.08, 2.6, 0.04), (bx - 1.0, by + 0.4, kit.ground(bx - 1.0, by + 0.4) + 0.02), plank, rot=(0, 0, -20))

# Wrack line of weed along the water's edge.
for i, (x, y) in enumerate([(-7, 5.9), (-3.5, 6.4), (-0.5, 6.6), (2.5, 6.1), (6.5, 5.6), (9, 5.2)]):
    kit.tufts(f"wrack{i}", (x, y), R.uniform(0.9, 1.6), 45, 0.07, weed, seed=i)

# Up the slope behind: frosted grass, gorse, the coast road, the inn and its sign.
kit.groundcover("grass", frostgrass, (-12, -45, 12, -5), near=(0, 0), blades=3000, height=0.3,
                seed=4, patchiness=0.7)
kit.footpath("coastroad", [(-35, -20), (-12, -21), (8, -22), (35, -25)], road, width=3.0, ruts=True, seed=2)
kit.footpath("beachpath", [(1.5, -4), (2.5, -10), (1.0, -16), (0.5, -21)], road, width=0.9, seed=5, wear=0.5)
kit.house("inn", (0, -32), (11, 7), walls, roof, trim, glass, storeys=2, rot=180, roof_kind="gable",
          storey_height=2.6, pitch=42, bays=4, chimneys=2, detail=1, seed=3)
sx, sy = 4.5, -26.0
sz = kit.ground(sx, sy)
kit.cylinder("signpost", 0.08, 3.2, (sx, sy, sz), plank, sides=8)
kit.box("signarm", (1.1, 0.08, 0.08), (sx + 0.5, sy, sz + 3.0), plank)
kit.box("signboard", (0.8, 0.05, 0.6), (sx + 0.6, sy, sz + 2.3), sign, bevel=0.01)
for i, (x, y) in enumerate(kit.scatter((-10, -26, 10, -7), 14, seed=6, clusters=4, avoid=[(0, -20, 3), (2, -10, 1.5)])):
    kit.shrub(f"gorse{i}", (x, y), R.uniform(0.5, 1.4), gorse, seed=i)
for i, (x, y) in enumerate(kit.scatter((-10, -18, 10, -7), 6, seed=16, clusters=2)):
    kit.rock(f"slope{i}", (x, y), R.uniform(0.4, 1.0), cliff2, seed=i + 160)
kit.tree("thorn", (-8, -30), 4.5, bark, gorse, kind="broadleaf", seed=2, lean=14, detail=1)

kit.far_hills((0.42, 0.45, 0.47), radius=100, height=6, seed=5)
kit.sun(5, 65, strength=3.2, color=(1.0, 0.84, 0.66), softness=1.2)
kit.sky((0.46, 0.58, 0.76), (0.90, 0.85, 0.78), strength=1.0, ground_color=(0.40, 0.44, 0.46))
kit.reader((0, 0), (0, 20, 1.3))
