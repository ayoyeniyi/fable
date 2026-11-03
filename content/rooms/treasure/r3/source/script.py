# The Spy-glass tavern, Bristol: a bright, low dockside room on a fair morning, doors open onto two streets.
R = kit.rng()
floor = kit.mat("floor", (0.66, 0.56, 0.42), kind="wood", rough=0.8)
seam = kit.mat("seam", (0.44, 0.35, 0.25), kind="wood", rough=0.9)
plaster = kit.mat("plaster", (0.86, 0.82, 0.72), kind="plaster")
ceil = kit.mat("ceiling", (0.80, 0.76, 0.66), kind="plaster")
beam = kit.mat("beam", (0.25, 0.18, 0.12), kind="wood")
panel = kit.mat("panel", (0.36, 0.26, 0.17), kind="wood")
rough = kit.mat("tablewood", (0.48, 0.38, 0.26), kind="wood", rough=0.85)
paint = kit.mat("framepaint", (0.88, 0.86, 0.80), kind="plaster", rough=0.5)
glass = kit.mat("glass", (0.80, 0.86, 0.88), kind="glass", rough=0.05)
curtain = kit.mat("curtain", (0.62, 0.14, 0.11), kind="fabric")
doorleaf = kit.mat("doorleaf", (0.20, 0.27, 0.22), kind="wood")
stone = kit.mat("stone", (0.62, 0.59, 0.53), kind="rock")
cobble = kit.mat("cobbles", (0.42, 0.40, 0.36), kind="rock")
sea = kit.mat("harbour", (0.13, 0.17, 0.17), kind="water")
hull = kit.mat("hull", (0.17, 0.13, 0.10), kind="wood")
band = kit.mat("hullband", (0.70, 0.62, 0.40), kind="wood")
mastw = kit.mat("mast", (0.42, 0.33, 0.22), kind="wood")
brass = kit.mat("brass", (0.78, 0.62, 0.30), kind="metal", rough=0.3)
pewter = kit.mat("pewter", (0.55, 0.55, 0.53), kind="metal", rough=0.4)
pewterd = kit.mat("pewterdark", (0.36, 0.36, 0.35), kind="metal", rough=0.5)
bottle = kit.mat("bottle", (0.16, 0.26, 0.15), kind="glass", rough=0.1)
cask = kit.mat("cask", (0.40, 0.28, 0.16), kind="wood")
iron = kit.mat("iron", (0.10, 0.10, 0.10), kind="metal", rough=0.6)
canvas = kit.mat("canvas", (0.46, 0.42, 0.30), kind="fabric")
seascape = kit.mat("seascape", (0.36, 0.43, 0.46), kind="fabric")
gilt = kit.mat("gilt", (0.66, 0.52, 0.28), kind="metal", rough=0.35)
rugm = kit.mat("rug", (0.45, 0.30, 0.20), kind="fabric")
rugb = kit.mat("rugborder", (0.22, 0.24, 0.30), kind="fabric")
leather = kit.mat("leather", (0.34, 0.20, 0.12), kind="fabric", rough=0.6)
coat = kit.mat("coat", (0.20, 0.22, 0.28), kind="fabric")
brick = kit.mat("housewall", (0.58, 0.45, 0.36), kind="brick")
slate = kit.mat("slate", (0.30, 0.31, 0.33), kind="rock")
wax = kit.mat("wax", (0.92, 0.88, 0.76), kind="plaster")
china = kit.mat("china", (0.90, 0.90, 0.86), kind="plaster", rough=0.3)
paper = kit.mat("paper", (0.88, 0.84, 0.72), kind="fabric")
rope = kit.mat("rope", (0.55, 0.46, 0.32), kind="fabric")
lanternglow = kit.mat("lanternglow", (1.0, 0.85, 0.6), kind="plaster", emission=2.0, emission_color=(1.0, 0.8, 0.55))

# Outside: a cobbled quay falling to the harbour on the east.
kit.terrain("quay", (80, 60), cobble, res=60, relief=0.05, scale=10, seed=2,
            flat=[(0, 0, 12, -0.03)], shore=(0, 11, 2.2))
kit.water("harbour", (60, 90), -0.9, sea, centre=(40, 0))
kit.box("quayedge", (0.6, 50, 0.4), (10.8, 0, -0.35), stone)

room = kit.room("tavern", 12, 9, 2.8, plaster, floor, ceiling=ceil, openings=[
    {"wall": "e", "at": 0.0, "width": 1.2, "height": 2.15, "sill": 0.0},
    {"wall": "w", "at": 1.5, "width": 1.2, "height": 2.15, "sill": 0.0},
    {"wall": "e", "at": -2.8, "width": 1.1, "height": 1.2, "sill": 0.9},
    {"wall": "e", "at": 2.8, "width": 1.1, "height": 1.2, "sill": 0.9},
    {"wall": "w", "at": -2.5, "width": 1.1, "height": 1.2, "sill": 0.9},
    {"wall": "n", "at": -0.4, "width": 1.2, "height": 1.2, "sill": 0.9},
    {"wall": "s", "at": -3.0, "width": 1.2, "height": 1.2, "sill": 0.9},
    {"wall": "s", "at": 3.0, "width": 1.2, "height": 1.2, "sill": 0.9},
])
kit.panelling(room, panel, dado=1.0, skirting=0.18, cornice=0.12, panels=True,
              avoid=[("n", 2.5, 1.9), ("n", -3.75, 2.6), ("s", 0.0, 2.2)])
kit.windows(room, paint, glass, curtain=curtain, pelmet=None, panes=(3, 2), drawn=0.7)
kit.doors(room, paint, doorleaf, open_deg=82)

# Sanded floorboards: seams of varied spacing running the depth of the room, with a few butt joints.
bx = -5.95
k = 0
while bx < 5.9:
    bx += R.uniform(0.17, 0.27)
    kit.box(f"seam{k}", (0.012, 8.96, 0.002), (bx, 0, 0.0), seam)
    for j in range(2):
        jy = R.uniform(-4.2, 4.2)
        kit.box(f"butt{k}_{j}", (0.2, 0.01, 0.002), (bx + 0.1, jy, 0.0), seam)
    k += 1

# Ceiling beams, slightly irregular.
for i, x in enumerate((-4.6, -2.2, 0.3, 2.6, 4.8)):
    kit.box(f"beam{i}", (0.2, 9.0, 0.2), (x + R.uniform(-0.1, 0.1), 0, 2.6), beam, rot=(0, 0, R.uniform(-0.6, 0.6)))

def bench(n, x, y, length, rot):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    kit.box(n + "seat", (length, 0.3, 0.05), (x, y, 0.42), rough, rot=(0, 0, rot))
    for kk in (-1, 1):
        dx = kk * (length / 2 - 0.15)
        kit.box(n + f"leg{kk}", (0.05, 0.26, 0.42), (x + dx * c, y + dx * s, 0), rough, rot=(0, 0, rot))

def tankards(n, x, y, z, count):
    for kk in range(count):
        a = R.uniform(0, 6.28)
        r = R.uniform(0.1, 0.5)
        kit.cylinder(f"{n}{kk}", 0.045, 0.13, (x + r * math.cos(a), y + 0.25 * math.sin(a), z), pewter, sides=10)

def stool(n, x, y):
    kit.cylinder(n + "top", 0.17, 0.04, (x, y, 0.44), rough, sides=12)
    for kk in range(3):
        a = R.uniform(0, 0.4) + kk * 2.094
        kit.cylinder(n + f"leg{kk}", 0.022, 0.45, (x + 0.11 * math.cos(a), y + 0.11 * math.sin(a), 0), rough,
                     sides=6, rot=(R.uniform(-5, 5), R.uniform(-5, 5), 0))

# Tables set a little askew, benches pushed about.
tables = [(-3.2, -0.4, 6), (-2.7, 2.0, -4), (3.0, -1.2, 9), (3.6, 1.6, -3)]
for i, (x, y, r) in enumerate(tables):
    kit.table(f"table{i}", (x, y), rough, size=(1.8, 0.8, 0.76), rot=r, legs="tapered")
    bench(f"benchA{i}", x + R.uniform(-0.2, 0.2), y - 0.66 - R.uniform(0, 0.12), 1.7, r + R.uniform(-6, 6))
    if i != 2:
        bench(f"benchB{i}", x + R.uniform(-0.2, 0.2), y + 0.66 + R.uniform(0, 0.12), 1.7, r + R.uniform(-6, 6))
    tankards(f"tank{i}_", x, y, 0.76, 2 + i % 2)
stool("stoolA", 3.3, -0.25)
stool("stoolB", -1.6, 2.4)
stool("stoolC", 1.4, -4.0)
stool("stoolD", 3.6, 3.4)
kit.candle("tcandle", (-2.9, 1.9, 0.76), wax, flame=False, height=0.15)
kit.clutter("pipes", (3.0, -1.2, 0.76), "writing", [paper, pewter], rot=14)

# A hanging ship's lantern over the left tables.
kit.cylinder("lanternchain", 0.01, 0.35, (-2.95, 0.8, 2.25), iron, sides=4)
kit.cylinder("lanterncap", 0.11, 0.08, (-2.95, 0.8, 2.17), iron, sides=8, top_radius=0.03)
kit.cylinder("lanternbody", 0.08, 0.2, (-2.95, 0.8, 1.97), lanternglow, sides=8)
kit.cylinder("lanternbase", 0.1, 0.03, (-2.95, 0.8, 1.94), iron, sides=8)
kit.lamp("lanternlight", (-2.95, 0.8, 2.05), power=15, color=(1.0, 0.8, 0.55), radius=0.08)

# A round table by the south-west window with two chairs.
kit.side_table("roundtable", (-4.6, -3.4), rough, size=0.7, height=0.72)
kit.chair("chair1", (-4.0, -3.5), rough, rot=100)
kit.chair("chair2", (-4.9, -2.8), rough, rot=200)
kit.clutter("tea", (-4.6, -3.4, 0.72), "tea", [china, pewter], rot=20)

# The bar along the north-west, a back-bar of shelves with bottles and pewter.
kit.box("barfront", (2.6, 0.55, 1.02), (-3.75, 3.35, 0), panel)
for k in range(5):
    kit.box(f"barstile{k}", (0.08, 0.04, 0.9), (-4.95 + k * 0.6, 3.06, 0.06), beam)
kit.box("bartop", (2.8, 0.7, 0.06), (-3.75, 3.35, 1.02), rough)
for k, z in enumerate((1.25, 1.65, 2.05)):
    kit.box(f"backshelf{k}", (2.5, 0.25, 0.04), (-3.75, 4.37, z), panel)
    for b in range(9):
        bxx = -4.9 + b * 0.27 + R.uniform(-0.05, 0.05)
        if R.random() < 0.8:
            if (b + k) % 3 == 0:
                kit.cylinder(f"pot{k}_{b}", 0.05, 0.14, (bxx, 4.36, z + 0.04), pewter, sides=8)
            else:
                kit.cylinder(f"bot{k}_{b}", 0.04, 0.26, (bxx, 4.36, z + 0.04), bottle, sides=8, top_radius=0.02)
tankards("bartank", -3.3, 3.35, 1.08, 3)
kit.clutter("ledger", (-4.5, 3.35, 1.08), "books", [rugm, rugb, paper], rot=-6)
kit.candle("barcandle", (-2.7, 3.3, 1.08), wax, flame=False, height=0.2)

# Casks on a rack along the west wall: bellied staves with iron hoops.
kit.box("rack", (0.8, 2.6, 0.3), (-5.5, -1.6, 0), beam)
for k in range(3):
    cy = -2.6 + k * 0.85 + R.uniform(-0.04, 0.04)
    kit.cylinder(f"caskA{k}", 0.30, 0.375, (-5.85, cy, 0.65), cask, rot=(0, 90, 0), sides=14, top_radius=0.35)
    kit.cylinder(f"caskB{k}", 0.35, 0.375, (-5.475, cy, 0.65), cask, rot=(0, 90, 0), sides=14, top_radius=0.30)
    for j, hx in enumerate((-5.80, -5.18)):
        kit.cylinder(f"hoop{k}_{j}", 0.318, 0.04, (hx, cy, 0.65), iron, rot=(0, 90, 0), sides=14)
kit.cylinder("caskup1", 0.3, 0.8, (-1.9, 3.9, 0), cask, sides=14)
kit.cylinder("caskup1h", 0.31, 0.04, (-1.9, 3.9, 0.62), iron, sides=14)
kit.cylinder("caskup2", 0.27, 0.7, (5.4, -3.8, 0), cask, sides=14)
kit.cylinder("caskup2h", 0.28, 0.04, (5.4, -3.8, 0.55), iron, sides=14)

# A cold hearth on the north wall, a small rug before it, a worn leather chair.
kit.fireplace("hearth", (2.5, 4.5), stone, rot=0, width=1.4, height=1.15, fire=False, hearth_stone=stone)
kit.clutter("mantel", (2.5, 4.35, 1.2), "mantel", [brass, china])
kit.rug("hearthrug", (2.5, 3.3), (1.6, 0.9), rugm, rot=3, border=rugb)
kit.armchair("settle", (1.4, 3.2), panel, leather, rot=200, kind="wing")
kit.picture("smallship", (1.0, 4.5, 1.75), (0.36, 0.3), gilt, seascape, rot=0)
kit.picture("ship3", (2.5, 4.42, 1.95), (0.7, 0.42), gilt, canvas, rot=0)

# The south wall: an oak dresser with pewter plates and pots, pictures either side.
kit.box("dresserbase", (2.0, 0.5, 0.85), (0.0, -4.25, 0), panel)
kit.box("dressertop", (2.1, 0.55, 0.05), (0.0, -4.25, 0.85), rough)
kit.box("dresserback", (2.0, 0.04, 1.2), (0.0, -4.47, 0.9), beam)
kit.box("dressercrown", (2.1, 0.28, 0.08), (0.0, -4.37, 2.1), panel)
for side in (-1, 1):
    kit.box(f"dresserside{side}", (0.04, 0.24, 1.2), (side * 0.98, -4.37, 0.9), panel)
for k, z in enumerate((1.28, 1.68)):
    kit.box(f"dshelf{k}", (1.92, 0.22, 0.03), (0.0, -4.37, z), panel)
    kit.box(f"dplaterail{k}", (1.92, 0.015, 0.03), (0.0, -4.30, z + 0.03), beam)
    for p in range(5):
        px = -0.76 + p * 0.38 + R.uniform(-0.03, 0.03)
        pr = 0.13 - 0.02 * (p % 2)
        kit.cylinder(f"plate{k}_{p}", pr, 0.012, (px, -4.40, z + pr + 0.02), pewter,
                     rot=(80, 0, R.uniform(-4, 4)), sides=20)
        kit.cylinder(f"platewell{k}_{p}", pr * 0.62, 0.006, (px, -4.412, z + pr + 0.022), pewterd,
                     rot=(80, 0, 0), sides=16)
for p in range(4):
    kit.cylinder(f"jug{p}", 0.06, 0.16, (-0.6 + p * 0.4 + R.uniform(-0.05, 0.05), -4.12, 0.9),
                 pewter if p % 2 else china, sides=10, top_radius=0.045)
kit.cylinder("dcandle_hold", 0.05, 0.03, (0.75, -4.1, 0.9), brass, sides=10)
kit.candle("dcandle", (0.75, -4.1, 0.93), wax, flame=False, height=0.18)
kit.picture("shipS", (-1.65, -4.47, 1.7), (0.5, 0.4), gilt, seascape, rot=180)
kit.picture("notice", (1.62, -4.47, 1.55), (0.35, 0.45), beam, paper, rot=180)
kit.box("pegrail", (0.9, 0.04, 0.08), (-1.65, -4.47, 1.25), beam)

# Coat pegs by the west door, with a coat and a hat hung up.
kit.box("westpegs", (0.04, 1.0, 0.08), (-5.98, 3.0, 1.62), beam)
for k in range(4):
    kit.cylinder(f"wpeg{k}", 0.015, 0.1, (-5.96, 2.62 + k * 0.25, 1.64), beam, rot=(0, 90, 0), sides=6)
kit.blob("hungcoat", 0.3, (-5.88, 2.87, 1.05), coat, squash=(0.35, 0.8, 1.9), roughness=0.2, seed=3)
kit.cylinder("hatbrim", 0.17, 0.02, (-5.86, 3.37, 1.58), coat, rot=(0, 80, 0), sides=12)
kit.cylinder("hatcrown", 0.1, 0.1, (-5.86, 3.37, 1.58), coat, rot=(0, 80, 0), sides=10)

# Pictures: ships and a chart.
kit.picture("ship1", (5.97, 1.4, 1.7), (0.7, 0.5), gilt, seascape, rot=-90)
kit.picture("ship1b", (5.97, -1.4, 1.75), (0.5, 0.4), beam, canvas, rot=-90)
kit.picture("chart", (-5.97, -0.5, 1.75), (0.8, 0.55), beam, paper, rot=90)
kit.picture("ship2", (4.4, 4.5, 1.7), (0.6, 0.45), gilt, canvas, rot=0)
kit.cylinder("ropecoil", 0.3, 0.18, (5.4, 3.8, 0), rope, sides=14, top_radius=0.26)
kit.cylinder("ropecoil2", 0.22, 0.1, (5.35, 3.85, 0.18), rope, sides=14, top_radius=0.18)

# The sign: a large brass telescope on a bracket outside the east door.
kit.box("signarm", (1.3, 0.06, 0.08), (6.75, 0.0, 2.55), iron)
kit.box("chain1", (0.02, 0.02, 0.3), (6.85, 0.0, 2.25), iron)
kit.box("chain2", (0.02, 0.02, 0.3), (7.25, 0.0, 2.25), iron)
kit.cylinder("telescope", 0.11, 1.1, (6.5, 0.0, 2.15), brass, rot=(0, 90, 0), sides=16, top_radius=0.07)

# The quay: bollards, casks, ships with shaped hulls and a forest of masts.
for k, y in enumerate((-12, -4, 5, 13)):
    kit.cylinder(f"bollard{k}", 0.2, 0.6, (10.2, y, -0.03), iron, sides=10)
for k, (x, y) in enumerate(kit.scatter((7.5, -8, 10, 8), 6, seed=4, clusters=2, avoid=[(7, 0, 1.5)])):
    kit.cylinder(f"qcask{k}", 0.3, 0.8, (x, y, kit.ground(x, y)), cask, sides=12)

def ship_hull(n, x, y, w, L):
    st = [(-L / 2, 0.05, 0.5), (-L / 2 + 2.0, 0.55, 0.8), (-L / 4, 0.95, 1.0), (0.0, 1.0, 1.0),
          (L / 4, 0.92, 0.95), (L / 2, 0.75, 0.7)]
    verts = []
    for (sy, wf, df) in st:
        hw = w / 2 * wf
        top = 1.3 + (0.5 if sy > L / 3 else 0.0) + (0.3 if sy < -L / 2 + 1 else 0.0)
        verts += [(-hw, sy, top), (hw, sy, top), (hw * 0.85, sy, -0.6), (0.0, sy, -2.2 * df), (-hw * 0.85, sy, -0.6)]
    faces = []
    for i in range(len(st) - 1):
        a = i * 5
        b = a + 5
        for kk in range(5):
            k2 = (kk + 1) % 5
            faces.append((a + kk, a + k2, b + k2, b + kk))
    faces.append((25, 26, 27, 28, 29))
    kit.mesh(n, verts, faces, hull, loc=(x, y, 0))
    kit.box(n + "band", (w * 1.01, L * 0.7, 0.18), (x, y + L * 0.05, 0.75), band)
    kit.cylinder(n + "sprit", 0.12, 7.0, (x, y - L / 2 + 0.5, 1.4), mastw, rot=(-70, 0, 0), sides=8, top_radius=0.05)

ships = [(15, -10, 4.0), (15.5, 6, 4.5), (24, -2, 4.2)]
for i, (x, y, w) in enumerate(ships):
    ship_hull(f"hull{i}", x, y, w, 20)
    kit.blob(f"figure{i}", 0.45, (x, y - 10.3, 1.1), paint, squash=(0.6, 0.8, 1.5), seed=i)
    for m in range(3):
        my = y - 6 + m * 6 + R.uniform(-0.5, 0.5)
        h = R.uniform(16, 22)
        kit.cylinder(f"mast{i}_{m}", 0.22, h, (x, my, 1.0), mastw, sides=8, top_radius=0.1, rot=(R.uniform(-1.5, 1.5), 0, 0))
        for yz in (0.45, 0.7, 0.88):
            kit.box(f"yard{i}_{m}_{yz}", (w * 2.2 * (1.1 - yz), 0.18, 0.18), (x, my, 1.0 + h * yz), mastw,
                    rot=(0, 0, R.uniform(-8, 8)))

# Across the streets: brick houses.
kit.house("westhouse", (-15, 1), (12, 8), brick, slate, paint, glass, storeys=3, rot=90,
          roof_kind="gable", storey_height=2.9, chimneys=2, detail=1, seed=2)
kit.house("northhouse", (0, 15), (14, 8), brick, slate, paint, glass, storeys=3, rot=180,
          roof_kind="hipped", storey_height=3.0, chimneys=2, detail=1, seed=5)

# Light: morning sun from the south-east, daylight through doors and windows.
kit.sun(28, -35, strength=4.0, color=(1.0, 0.94, 0.84))
kit.sky((0.40, 0.58, 0.85), (0.86, 0.86, 0.82), strength=1.0)
kit.area_light("eastdoorlight", (6.4, 0.0, 1.2), (1.2, 2.0), 180, color=(1.0, 0.95, 0.88), aim=(-1, 0, 0))
kit.area_light("westdoorlight", (-6.4, 1.5, 1.2), (1.2, 2.0), 90, aim=(1, 0, 0))
for k, (x, y, a) in enumerate([(6.4, -2.8, (-1, 0, 0)), (6.4, 2.8, (-1, 0, 0)), (-6.4, -2.5, (1, 0, 0)),
                               (-0.4, 4.9, (0, -1, 0)), (-3.0, -4.9, (0, 1, 0)), (3.0, -4.9, (0, 1, 0))]):
    kit.area_light(f"winlight{k}", (x, y, 1.5), (1.1, 1.2), 70, color=(1.0, 0.96, 0.90), aim=a)
kit.lamp("barfill", (-3.0, 2.6, 2.3), power=20, color=(1.0, 0.85, 0.65), radius=0.3)

kit.reader((0.0, -2.0), (0.0, 4.0, 1.45))
