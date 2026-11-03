rng = kit.rng()

plaster = kit.mat("plaster", (0.38, 0.33, 0.25), kind="plaster")
ceilmat = kit.mat("ceiling", (0.24, 0.21, 0.17), kind="plaster")
wainscot = kit.mat("wainscot", (0.27, 0.20, 0.14), kind="wood")
planks = kit.mat("planks", (0.29, 0.22, 0.15), kind="wood", rough=0.8)
planks2 = kit.mat("planks2", (0.23, 0.18, 0.13), kind="wood", rough=0.85)
beamwood = kit.mat("beams", (0.15, 0.11, 0.08), kind="wood")
darkwood = kit.mat("darkwood", (0.22, 0.16, 0.11), kind="wood")
brick = kit.mat("brick", (0.27, 0.19, 0.15), kind="brick")
iron = kit.mat("iron", (0.10, 0.10, 0.10), kind="metal", rough=0.6)
rust = kit.mat("rust", (0.32, 0.19, 0.11), kind="metal", rough=0.85)
bone = kit.mat("bone", (0.62, 0.57, 0.46), kind="rock", rough=0.6)
canvas = kit.mat("canvas", (0.12, 0.11, 0.08), kind="fabric", rough=0.8)
paintsea = kit.mat("paintsea", (0.17, 0.19, 0.15), kind="fabric", rough=0.8)
paintsky = kit.mat("paintsky", (0.36, 0.32, 0.22), kind="fabric", rough=0.8)
paintdark = kit.mat("paintdark", (0.05, 0.05, 0.05), kind="fabric", rough=0.8)
frame = kit.mat("frame", (0.20, 0.15, 0.09), kind="wood")
glass = kit.mat("glass", (0.42, 0.44, 0.41), kind="plaster", rough=0.08)
winglass = kit.mat("winglass", (0.06, 0.07, 0.10), kind="plaster", rough=0.05)
bottle_g = kit.mat("bottle_green", (0.12, 0.22, 0.12), kind="plaster", rough=0.1)
bottle_a = kit.mat("bottle_amber", (0.40, 0.23, 0.09), kind="plaster", rough=0.1)
glow = kit.mat("stoveglow", (1.0, 0.45, 0.15), kind="plaster", emission=5.0, emission_color=(1.0, 0.42, 0.12))
lglow = kit.mat("lanternglow", (0.9, 0.7, 0.45), kind="plaster", emission=2.2, emission_color=(1.0, 0.70, 0.40))
curtain = kit.mat("curtain", (0.28, 0.17, 0.12), kind="fabric")
paper = kit.mat("paper", (0.66, 0.62, 0.50), kind="fabric")
pewter = kit.mat("pewter", (0.42, 0.42, 0.40), kind="metal", rough=0.45)
wax = kit.mat("wax", (0.82, 0.78, 0.66), kind="plaster")
seat = kit.mat("seatfabric", (0.28, 0.21, 0.15), kind="fabric")
rope = kit.mat("rope", (0.44, 0.36, 0.25), kind="fabric")
rugmat = kit.mat("runner", (0.26, 0.22, 0.17), kind="fabric", rough=0.95)

W, D, H = 9.0, 12.0, 2.5
room = kit.room("inn", W, D, H, plaster, beamwood, ceiling=ceilmat, openings=[
    {"wall": "s", "at": 0.0, "width": 1.1, "height": 2.05, "sill": 0.0},
    {"wall": "s", "at": 2.8, "width": 0.9, "height": 1.1, "sill": 0.9},
    {"wall": "s", "at": -2.8, "width": 0.9, "height": 1.1, "sill": 0.9},
    {"wall": "w", "at": 4.0, "width": 0.9, "height": 1.1, "sill": 0.9},
    {"wall": "n", "at": -3.0, "width": 0.95, "height": 2.0, "sill": 0.0},
])
kit.panelling(room, wainscot, dado=1.2, skirting=0.22, cornice=0.2, panels=True)
kit.windows(room, frame, winglass, curtain=curtain, panes=(3, 2), drawn=0.25)
kit.doors(room, frame, darkwood, open_deg=0.0)

# old wrinkled planks
pa = ([], [])
pf = ([], [])
x = -4.5
while x < 4.5:
    w = rng.uniform(0.18, 0.28)
    x1 = min(4.5, x + w - 0.008)
    split = rng.uniform(-4.0, 4.0)
    for (ya, yb) in ((-6.0, split - 0.004), (split + 0.004, 6.0)):
        k = 0 if rng.random() < 0.55 else 1
        z0 = rng.uniform(0.002, 0.008)
        z1 = z0 + rng.uniform(-0.004, 0.004)
        n = len(pa[k])
        pa[k].extend([(x, ya, z0), (x1, ya, z1), (x1, yb, z1 + rng.uniform(-0.003, 0.003)), (x, yb, z0)])
        pf[k].append((n, n + 1, n + 2, n + 3))
    x += w
kit.mesh("floorboards_a", pa[0], pf[0], planks)
kit.mesh("floorboards_b", pa[1], pf[1], planks2)
kit.rug("runner", (0.1, -2.7), (1.0, 3.6), rugmat, rot=2)

# low ponderous beams
for i in range(8):
    y = -5.4 + i * 1.55
    kit.box(f"beam{i}", (W, 0.24, 0.2), (0, y + rng.uniform(-0.08, 0.08), H - 0.2), beamwood,
            rot=(rng.uniform(-0.6, 0.6), 0, 0))
kit.box("summer", (0.28, D, 0.16), (-0.2, 0, H - 0.36), beamwood)

# the old central chimney with a low arch through it
y0, y1, r, hs = 0.0, 1.1, 0.6, 1.35
kit.box("chim_l", (0.95, y1 - y0, H), (-1.075, (y0 + y1) / 2, 0), brick)
kit.box("chim_r", (0.95, y1 - y0, H), (1.075, (y0 + y1) / 2, 0), brick)
verts, faces = [], []
N = 14
for k in range(N + 1):
    th = math.pi - math.pi * k / N
    ax, az = r * math.cos(th), hs + r * math.sin(th)
    verts += [(ax, y0, az), (ax, y0, H), (ax, y1, az), (ax, y1, H)]
for k in range(N):
    a, b = 4 * k, 4 * (k + 1)
    faces.append((a, b, b + 1, a + 1))
    faces.append((a + 2, a + 3, b + 3, b + 2))
    faces.append((a, a + 2, b + 2, b))
kit.mesh("chim_arch", verts, faces, brick)
kit.picture("print", (-1.05, -0.01, 1.55), (0.4, 0.32), frame, canvas, rot=0)

# partition walls either side of the chimney: the entry is closed off from the public room
for side, cxp in (("w", -3.025), ("e", 3.025)):
    kit.box(f"part_{side}", (2.95, 0.2, H), (cxp, 0.1, 0), plaster)
    kit.box(f"part_wain_{side}", (2.95, 0.03, 1.2), (cxp, -0.015, 0), wainscot)
    kit.box(f"part_skirt_{side}", (2.95, 0.05, 0.2), (cxp, -0.04, 0), beamwood)
    kit.box(f"part_rail_{side}", (2.95, 0.07, 0.06), (cxp, -0.05, 1.18), beamwood)
    kit.box(f"part_cap_{side}", (2.95, 0.05, 0.12), (cxp, -0.035, H - 0.32), beamwood)
    bx = cxp - 1.35
    while bx < cxp + 1.4:
        kit.box(f"part_bat_{side}_{int(bx * 100)}", (0.07, 0.025, 0.95), (bx, -0.04, 0.2), darkwood)
        bx += rng.uniform(0.42, 0.56)
kit.cylinder("partpeg1", 0.02, 0.1, (-2.6, -0.05, 1.6), iron, rot=(90, 0, 0), sides=6)
kit.blob("hungcoat", 0.17, (-2.6, -0.12, 1.25), canvas, squash=(0.9, 0.5, 1.9), seed=21)
kit.box("noticeboard", (0.5, 0.03, 0.4), (2.7, -0.02, 1.45), darkwood)
kit.box("notice", (0.3, 0.01, 0.22), (2.68, -0.04, 1.53), paper, rot=(0, 4, 0))

# huge smoke-blackened painting on the west wall: a foundering Cape-Horner and a leaping whale
kit.picture("painting", (-4.47, -1.6, 1.82), (2.6, 0.9), frame, canvas, rot=90, depth=0.08)
kit.box("pt_sky", (0.012, 1.4, 0.14), (-4.41, -1.25, 1.98), paintsky, rot=(6, 0, 0))
kit.box("pt_sea", (0.012, 2.3, 0.2), (-4.41, -1.6, 1.42), paintsea, rot=(-3, 0, 0))
kit.box("pt_hull", (0.012, 0.7, 0.13), (-4.398, -2.15, 1.52), paintdark, rot=(24, 0, 0))
for j, my in enumerate((-2.3, -2.05, -1.85)):
    kit.box(f"pt_mast{j}", (0.012, 0.025, 0.42 - j * 0.08), (-4.398, my, 1.6), paintdark, rot=(24 + j * 4, 0, 0))
kit.blob("pt_whale", 0.12, (-4.40, -0.85, 1.78), paintdark, squash=(0.08, 1.5, 0.75), roughness=0.15, seed=5)

# old carved settle under the painting
kit.box("settle_seat", (0.5, 1.7, 0.06), (-4.15, -1.6, 0.42), darkwood)
kit.box("settle_back", (0.08, 1.7, 1.1), (-4.40, -1.6, 0), darkwood)
kit.box("settle_cap", (0.14, 1.8, 0.06), (-4.38, -1.6, 1.1), beamwood, bevel=0.01)
kit.box("settle_end1", (0.5, 0.06, 0.95), (-4.15, -2.45, 0), darkwood)
kit.box("settle_end2", (0.5, 0.06, 0.95), (-4.15, -0.75, 0), darkwood)
kit.box("settle_apron", (0.04, 1.7, 0.36), (-3.92, -1.6, 0), darkwood)
kit.blob("settle_coat", 0.16, (-4.15, -1.2, 0.55), canvas, squash=(1.0, 1.5, 0.5), seed=11)
kit.blob("seabag", 0.26, (-3.6, -3.4, 0.0), canvas, squash=(1.0, 0.8, 1.2), seed=9)
kit.box("seachest", (0.9, 0.5, 0.48), (-3.9, -4.9, 0), darkwood, rot=(0, 0, 84), bevel=0.03)
kit.box("chestlid", (0.94, 0.54, 0.06), (-3.9, -4.9, 0.48), beamwood, rot=(0, 0, 84), bevel=0.02)
kit.blob("ropecoil", 0.28, (-3.88, -4.85, 0.56), rope, squash=(1.0, 1.0, 0.35), roughness=0.15, seed=3)

# heathenish array on the east wall, uneven and crowded
for t, (cy, cz, L) in enumerate([(-3.4, 1.74, 0.85), (-2.15, 1.86, 1.0), (-0.9, 1.72, 0.9)]):
    angs = [(-55, -28, 0, 30, 50), (-60, -35, -12, 12, 35, 58), (-48, -20, 8, 40)][t]
    for j, ang in enumerate(angs):
        rx = ang + rng.uniform(-6, 6)
        Lj = L * rng.uniform(0.85, 1.1)
        d = (-math.sin(math.radians(rx)), math.cos(math.radians(rx)))
        by, bz = cy - d[0] * Lj / 2, cz - d[1] * Lj / 2
        kit.cylinder(f"spear{t}_{j}", 0.014, Lj, (4.44, by, bz), darkwood, rot=(rx, 0, 0), sides=6)
        kit.cylinder(f"spearhead{t}_{j}", 0.03, 0.17, (4.44, cy + d[0] * Lj / 2, cz + d[1] * Lj / 2),
                     bone if (j + t) % 2 else rust, rot=(rx, 0, 0), sides=6, top_radius=0.002)
    for j, ang in enumerate((34 + t * 6, -30 - t * 5)):
        Lc = 0.6 + 0.06 * t
        d = (-math.sin(math.radians(ang)), math.cos(math.radians(ang)))
        by, bz = cy - d[0] * Lc / 2, cz - 0.05 - d[1] * Lc / 2
        kit.cylinder(f"club{t}_{j}", 0.02, Lc, (4.42, by, bz), beamwood, rot=(ang, 0, 0), sides=8, top_radius=0.045)
        kit.blob(f"clubhead{t}_{j}", 0.07 + 0.02 * j, (4.41, by + d[0] * Lc, bz + d[1] * Lc), beamwood,
                 squash=(0.6, 1.0, 1.3), seed=t * 2 + j)
    kit.box(f"boss{t}", (0.05, 0.1, 0.1), (4.45, cy, cz - 0.1), iron)
for i in range(3):
    z = 1.28 + i * 0.08
    kit.cylinder(f"lance{i}", 0.013, 3.6 - i * 0.4, (4.42, -0.4 - i * 0.25, z), rust,
                 rot=(90 + rng.uniform(-2.5, 2.5), 0, 0), sides=6)
for i in range(2):
    kit.cylinder(f"lancehead{i}", 0.04, 0.24, (4.42, -4.0 + i * 0.4, 1.28 + i * 0.08), rust, rot=(90, 0, 0), sides=4, top_radius=0.002)
for yy in (-0.9, -2.2, -3.6):
    kit.box(f"peg{yy}", (0.08, 0.03, 0.03), (4.44, yy, 1.24), iron)
kit.cylinder("leaning_harpoon", 0.016, 2.2, (4.15, -4.6, 0), rust, rot=(0, 7, 0), sides=6)
kit.chair("entrychair", (3.6, -2.9), darkwood, rot=-70)

# barrels by the south-east window
for i, (bx, by) in enumerate([(3.85, -5.4), (3.3, -5.6)]):
    kit.cylinder(f"barrel{i}", 0.3, 0.8, (bx, by, 0), darkwood, sides=14, top_radius=0.27)
    kit.cylinder(f"hoop{i}", 0.305, 0.04, (bx, by, 0.62), iron, sides=14)
kit.cylinder("spittoon", 0.12, 0.1, (2.6, -5.3, 0), pewter, sides=10, top_radius=0.09)

# great iron stove, glimpsed through the arch
kit.box("stovebase", (0.9, 0.9, 0.08), (-1.4, 2.8, 0), brick)
kit.cylinder("stove", 0.4, 0.9, (-1.4, 2.8, 0.08), iron, sides=16)
kit.cylinder("stovecap", 0.44, 0.08, (-1.4, 2.8, 0.98), iron, sides=16)
kit.cylinder("stovepipe", 0.08, H - 1.06, (-1.4, 2.8, 1.06), iron, sides=10)
kit.box("stovegrate", (0.28, 0.04, 0.16), (-1.4, 2.41, 0.3), glow)

# long table of cracked glass cases
kit.table("casetable", (-3.9, 2.8), darkwood, size=(2.6, 0.7, 0.8), rot=90)
for i in range(3):
    y = 1.95 + i * 0.85
    kit.box(f"case{i}", (0.6, 0.78, 0.3), (-3.9, y, 0.8), glass)
    kit.blob(f"curio{i}", 0.08, (-3.9 + rng.uniform(-0.15, 0.15), y, 0.84), bone,
             squash=(1.4, 0.8, 0.6), seed=i)
    kit.cylinder(f"curio_s{i}", 0.04, 0.12, (-3.8, y + 0.2, 0.8), rust, sides=8)

# the bar inside the whale's jaw, framed by the arch
def tube(name, pts, r0, r1, mat, sides=10):
    verts, faces = [], []
    n = len(pts)
    for i, p in enumerate(pts):
        a = Vector(pts[min(i + 1, n - 1)]) - Vector(pts[max(i - 1, 0)])
        a.normalize()
        u = Vector((0, 1, 0))
        if abs(a.dot(u)) > 0.9:
            u = Vector((1, 0, 0))
        v = a.cross(u)
        v.normalize()
        u = v.cross(a)
        u.normalize()
        rr = r0 + (r1 - r0) * i / (n - 1)
        for k in range(sides):
            ang = 2 * math.pi * k / sides
            q = Vector(p) + u * (math.cos(ang) * rr) + v * (math.sin(ang) * rr * 0.75)
            verts.append((q.x, q.y, q.z))
    for i in range(n - 1):
        for k in range(sides):
            faces.append((i * sides + k, i * sides + (k + 1) % sides,
                          (i + 1) * sides + (k + 1) % sides, (i + 1) * sides + k))
    kit.mesh(name, verts, faces, mat, smooth=True)

cx, a, b = 0.35, 1.15, 2.12
for side, (t0, t1) in (("l", (math.pi, math.pi / 2)), ("r", (0.0, math.pi / 2))):
    pts = []
    for j in range(14):
        th = t0 + (t1 - t0) * j / 13
        pts.append((cx + a * math.cos(th), 4.0 - 0.12 * math.sin(th), max(0.0, b * math.sin(th))))
    tube(f"jaw_{side}", pts, 0.2, 0.11, bone)
kit.box("barcounter", (1.9, 0.55, 1.0), (cx, 4.7, 0), darkwood, bevel=0.02)
kit.box("bartop", (2.0, 0.62, 0.05), (cx, 4.7, 1.0), beamwood)
for s, z in enumerate((1.15, 1.5, 1.85)):
    kit.box(f"barshelf{s}", (2.0, 0.24, 0.03), (cx, 5.86, z), darkwood, rot=(0, rng.uniform(-1.5, 1.5), 0))
    bx = cx - 0.9
    while bx < cx + 0.9:
        hgt = rng.uniform(0.16, 0.28)
        kit.cylinder(f"bottle{s}_{int(bx * 100) + 500}", rng.uniform(0.035, 0.055), hgt, (bx, 5.86 + rng.uniform(-0.04, 0.04), z + 0.03),
                     bottle_g if rng.random() < 0.5 else bottle_a, sides=8, top_radius=0.015)
        bx += rng.uniform(0.12, 0.3)
for i in range(3):
    kit.cylinder(f"tankard{i}", 0.045, 0.12, (cx - 0.6 + i * 0.4 + rng.uniform(-0.05, 0.05), 4.65, 1.05), pewter, sides=10)
kit.clutter("ledger", (cx + 0.4, 4.7, 1.05), "writing", [paper, pewter], rot=8, seed=2)

# tables and chairs in the public room, a little out of line
kit.table("table1", (2.2, 2.7), darkwood, size=(1.2, 0.75, 0.74), rot=8)
kit.chair("chair1", (2.2, 2.05), darkwood, rot=185, fabric=seat)
kit.chair("chair2", (1.35, 2.9), darkwood, rot=-75)
kit.chair("chair3", (3.0, 3.2), darkwood, rot=100)
kit.cylinder("mug1", 0.045, 0.12, (2.4, 2.75, 0.74), pewter, sides=10)
kit.candle("tablecandle", (2.0, 2.6, 0.74), wax, power=12)
kit.table("table2", (-2.6, 4.8), darkwood, size=(1.0, 0.7, 0.74), rot=-6)
kit.chair("chair4", (-2.6, 5.45), darkwood, rot=10)
kit.chair("chair5", (-1.8, 4.6), darkwood, rot=80)

# hanging lanterns
def lantern(name, x, y, power):
    kit.cylinder(name + "_chain", 0.01, 0.32, (x, y, H - 0.52), iron, sides=4)
    kit.cylinder(name + "_cap", 0.09, 0.06, (x, y, H - 0.58), iron, sides=8, top_radius=0.03)
    kit.cylinder(name + "_body", 0.07, 0.2, (x, y, H - 0.78), lglow, sides=8)
    kit.cylinder(name + "_foot", 0.08, 0.03, (x, y, H - 0.81), iron, sides=8)
    kit.lamp(name + "_light", (x, y, H - 0.68), power=power, color=(1.0, 0.68, 0.40), radius=0.08)

lantern("entrylantern", 1.3, -2.4, 60)
lantern("entrylantern2", -1.6, -4.4, 35)
lantern("barlantern", cx + 0.8, 5.0, 80)
lantern("publantern", 1.6, 3.4, 45)
lantern("publantern2", -2.8, 1.8, 30)

# uneven cross-lights, stove and case glow, dim fill
kit.lamp("paintlight1", (-3.6, -0.6, 2.0), power=45, color=(1.0, 0.68, 0.40))
kit.lamp("paintlight2", (-3.3, -3.2, 1.0), power=18, color=(1.0, 0.66, 0.38))
kit.lamp("weaponlight", (3.4, -3.0, 2.05), power=45, color=(1.0, 0.68, 0.42))
kit.lamp("archface", (0.0, -1.6, 2.15), power=22, color=(1.0, 0.70, 0.42), radius=0.1)
kit.lamp("stovelight", (-1.4, 2.2, 0.4), power=110, color=(1.0, 0.46, 0.18), radius=0.12)
kit.lamp("caselamp", (-3.6, 2.8, 1.9), power=20, color=(1.0, 0.70, 0.44))
kit.area_light("entryfill", (0.0, -3.0, H - 0.05), (3.5, 4.0), 55, color=(1.0, 0.76, 0.52), aim=(0, 0, -1))
kit.area_light("pubfill", (0.5, 3.5, H - 0.05), (4.0, 4.0), 30, color=(1.0, 0.72, 0.48), aim=(0, 0, -1))
kit.area_light("moon_s1", (2.8, -6.6, 1.45), (0.8, 1.0), 10, color=(0.6, 0.7, 0.95), aim=(0, 1, 0))
kit.area_light("moon_s2", (-2.8, -6.6, 1.45), (0.8, 1.0), 10, color=(0.6, 0.7, 0.95), aim=(0, 1, 0))
kit.sun(18, 250, strength=0.12, color=(0.65, 0.72, 0.95))
kit.sky((0.03, 0.04, 0.08), (0.08, 0.09, 0.13), strength=0.12)

kit.reader((0.0, -4.8), (0.0, 4.0, 1.5))
