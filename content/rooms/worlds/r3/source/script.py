# The dining room at Maybury: a late-Victorian suburban dining room on a still summer night,
# lit by a pink-shaded lamp on the laid table; the reader stands to the right, the table in view to the left-front.
R = kit.rng()

paper = kit.mat("wallpaper", (0.30, 0.16, 0.14), kind="plaster")
ceil = kit.mat("ceiling", (0.62, 0.58, 0.52), kind="plaster")
boards = kit.mat("floorboards", (0.24, 0.16, 0.11), kind="wood")
joinery = kit.mat("joinery", (0.22, 0.13, 0.09), kind="wood")
mahog = kit.mat("mahogany", (0.26, 0.12, 0.08), kind="wood", rough=0.35)
paint = kit.mat("whitepaint", (0.72, 0.70, 0.64), kind="plaster", rough=0.4)
winglass = kit.mat("windowglass", (0.03, 0.04, 0.07), kind="glass")
linen = kit.mat("tablecloth", (0.86, 0.85, 0.80), kind="fabric")
silver = kit.mat("silver", (0.78, 0.78, 0.76), kind="metal", rough=0.2)
glass = kit.mat("glassware", (0.85, 0.88, 0.90), kind="glass")
wine = kit.mat("wine", (0.36, 0.04, 0.16), kind="glass")
china = kit.mat("china", (0.92, 0.91, 0.87), kind="ceramic")
brass = kit.mat("brass", (0.72, 0.56, 0.30), kind="metal", rough=0.3)
shade = kit.mat("pinkshade", (0.92, 0.50, 0.55), kind="fabric", emission=3.0, emission_color=(1.0, 0.45, 0.52))
marble = kit.mat("marble", (0.74, 0.72, 0.68), kind="stone", rough=0.25)
hearthst = kit.mat("hearthstone", (0.26, 0.25, 0.23), kind="stone")
rugm = kit.mat("rug", (0.30, 0.11, 0.10), kind="fabric")
rugb = kit.mat("rugborder", (0.14, 0.12, 0.16), kind="fabric")
curtain = kit.mat("curtains", (0.26, 0.10, 0.12), kind="fabric")
seat = kit.mat("seatfabric", (0.32, 0.20, 0.15), kind="fabric")
gilt = kit.mat("gilt", (0.62, 0.48, 0.25), kind="metal", rough=0.4)
mirror = kit.mat("mirror", (0.30, 0.30, 0.29), kind="metal", rough=0.05)
canvas1 = kit.mat("painting1", (0.14, 0.15, 0.10), kind="leather")
canvas2 = kit.mat("painting2", (0.24, 0.17, 0.10), kind="leather")
canvas3 = kit.mat("painting3", (0.11, 0.12, 0.15), kind="leather")
bk1 = kit.mat("book1", (0.35, 0.15, 0.12), kind="leather")
bk2 = kit.mat("book2", (0.16, 0.22, 0.18), kind="leather")
bk3 = kit.mat("book3", (0.40, 0.32, 0.20), kind="leather")
bk4 = kit.mat("book4", (0.18, 0.18, 0.26), kind="leather")
wax = kit.mat("wax", (0.92, 0.88, 0.76), kind="plaster")
nuts = kit.mat("nuts", (0.45, 0.30, 0.17), kind="wood")
meat = kit.mat("coldmeat", (0.62, 0.40, 0.34), kind="plaster")
bread = kit.mat("bread", (0.70, 0.52, 0.30), kind="plaster")

# --- the room: 6 x 7 m, two windows to the night (north), door in the south wall
room = kit.room("dining", 6.0, 7.0, 3.2, paper, boards, ceiling=ceil, openings=[
    {"wall": "n", "at": -1.3, "width": 1.1, "height": 2.0, "sill": 0.8},
    {"wall": "n", "at": 1.3, "width": 1.1, "height": 2.0, "sill": 0.8},
    {"wall": "s", "at": 1.8, "width": 1.0, "height": 2.2, "sill": 0.0}])
kit.panelling(room, joinery, dado=0.95, skirting=0.22, cornice=0.26, panels=True, picture_rail=2.3,
              avoid=[("w", 0.0, 1.9)])
kit.windows(room, paint, winglass, curtain=curtain, pelmet=mahog, panes=(2, 2), drawn=0.3)
kit.doors(room, paint, mahog, open_deg=18)
kit.rug("rug", (0, 0.9), (3.2, 3.9), rugm, rot=1.5, border=rugb)

# --- the dining table, laid with a draped white cloth
kit.table("table", (0, 0.9), mahog, size=(2.0, 1.1, 0.76), rot=90, legs="turned")
T = 0.772
cy = 0.9
rings = [(0.59, 1.04, T), (0.60, 1.05, T - 0.02), (0.615, 1.065, 0.62), (0.64, 1.09, 0.50)]
verts = []
for (hx, hy, z) in rings:
    verts += [(-hx, cy - hy, z), (hx, cy - hy, z), (hx, cy + hy, z), (-hx, cy + hy, z)]
faces = [(0, 1, 2, 3)]
for r in range(len(rings) - 1):
    a = r * 4
    b = a + 4
    for k in range(4):
        k2 = (k + 1) % 4
        faces.append((a + k, b + k, b + k2, a + k2))
kit.mesh("cloth", verts, faces, linen)

for i, (x, y, r) in enumerate([(-0.88, 0.45, 90), (-0.88, 1.35, 90), (0.88, 0.5, -90),
                               (0.92, 1.3, -90), (0.05, 2.42, 0)]):
    kit.chair(f"chair{i}", (x + R.uniform(-0.05, 0.05), y + R.uniform(-0.06, 0.06)), mahog,
              rot=r + R.uniform(-8, 8), fabric=seat)

def place(n, x, y, face):
    kit.cylinder(f"plate{n}", 0.13, 0.012, (x, y, T), china, sides=24)
    kit.box(f"knife{n}", (0.018, 0.21, 0.005), (x + 0.17 * face[1], y - 0.17 * face[0], T), silver,
            rot=(0, 0, 90 * abs(face[0])))
    kit.box(f"fork{n}", (0.02, 0.19, 0.005), (x - 0.17 * face[1], y + 0.17 * face[0], T), silver,
            rot=(0, 0, 90 * abs(face[0])))

def wineglass(n, x, y, full):
    kit.cylinder(f"gfoot{n}", 0.03, 0.004, (x, y, T), glass, sides=12)
    kit.cylinder(f"gstem{n}", 0.006, 0.09, (x, y, T), glass, sides=8)
    kit.cylinder(f"gbowl{n}", 0.025, 0.08, (x, y, T + 0.09), glass, sides=14, top_radius=0.038)
    if full:
        kit.cylinder(f"gwine{n}", 0.023, 0.045, (x, y, T + 0.093), wine, sides=14, top_radius=0.031)

place("head", 0.0, 1.68, (0, -1))
wineglass("head", 0.24, 1.48, True)
kit.cylinder("nutdish", 0.09, 0.03, (-0.24, 1.47, T), silver, sides=20, top_radius=0.11)
for k in range(9):
    a = k * 2.4
    kit.blob(f"nut{k}", 0.02, (-0.24 + 0.045 * math.cos(a) * (k % 3) / 2, 1.47 + 0.045 * math.sin(a) * (k % 3) / 2, T + 0.035),
             nuts, squash=(1.2, 1, 0.8), seed=k)
place("wife", 0.32, 1.3, (-1, 0))
wineglass("wife", 0.32, 1.06, True)
place("side", -0.32, 0.55, (1, 0))
wineglass("side", -0.30, 0.78, False)

kit.cylinder("platter", 0.2, 0.015, (0.05, 0.42, T), china, sides=28)
kit.blob("joint", 0.11, (0.05, 0.42, T + 0.05), meat, squash=(1.3, 1, 0.6), seed=3)
kit.cylinder("breadboard", 0.13, 0.02, (-0.28, 0.12, T), joinery, sides=20)
kit.blob("loaf", 0.08, (-0.28, 0.12, T + 0.06), bread, squash=(1.4, 1, 0.75), seed=5)
kit.cylinder("carafe", 0.05, 0.2, (0.3, 0.2, T), glass, sides=16, top_radius=0.025)
kit.cylinder("saltcellar", 0.025, 0.035, (-0.12, 1.15, T), silver, sides=10)
kit.cylinder("dish", 0.11, 0.04, (0.28, 0.75, T), china, sides=20, top_radius=0.13)

# the pink-shaded lamp: the main light of the room
kit.cylinder("lamp.base", 0.08, 0.04, (0, 1.05, T), brass, sides=16)
kit.cylinder("lamp.col", 0.02, 0.26, (0, 1.05, T + 0.04), brass, sides=10)
kit.blob("lamp.font", 0.07, (0, 1.05, T + 0.32), brass, squash=(1, 1, 0.8), roughness=0.05, seed=1)
kit.cylinder("lamp.chimney", 0.025, 0.2, (0, 1.05, T + 0.36), glass, sides=10)
kit.cylinder("lamp.shade", 0.21, 0.2, (0, 1.05, T + 0.38), shade, sides=24, top_radius=0.1)
kit.lamp("lamplight", (0, 1.05, T + 0.42), power=85, color=(1.0, 0.60, 0.58), radius=0.08)

# --- west: the cold summer fireplace with a glass over it
kit.fireplace("fire", (-3.0, 0.0), marble, rot=90, width=1.5, height=1.2, fire=False,
              hearth_stone=hearthst)
kit.clutter("mantel", (-2.88, 0.0, 1.23), "mantel", [gilt, china], rot=90, seed=2)
kit.picture("overmantel", (-3.0, 0.0, 1.95), (1.0, 0.85), gilt, mirror, rot=90)
kit.picture("pic.w1", (-3.0, -2.1, 1.8), (0.7, 0.55), gilt, canvas1, rot=90)
kit.picture("pic.w2", (-3.0, 2.2, 1.85), (0.6, 0.75), joinery, canvas2, rot=90)

# --- east: the sideboard, candles, decanter, a small bookcase
kit.desk("sideboard", (2.68, 0.6), mahog, rot=-90, size=(1.8, 0.55, 0.9), kind="pedestal", knobs=brass)
kit.candelabra("candelabra", (2.7, 1.25, 0.9), silver, wax, arms=3, power=4)
kit.clutter("sideboard.tea", (2.66, 0.2, 0.9), "tea", [china, silver], rot=-90, seed=4)
kit.cylinder("decanter", 0.06, 0.24, (2.72, -0.15, 0.9), glass, sides=16, top_radius=0.02)
kit.picture("pic.e1", (3.0, 0.6, 1.85), (1.0, 0.7), gilt, canvas1, rot=-90)
kit.shelf("bookcase", (2.8, -2.0), mahog, (bk1, bk2, bk3, bk4), width=1.0, height=1.9, rot=-90, seed=6)
kit.picture("pic.e2", (3.0, -2.0, 2.45), (0.5, 0.4), joinery, canvas3, rot=-90)
kit.picture("pic.e3", (3.0, -3.0, 1.6), (0.35, 0.45), gilt, canvas2, rot=-90)
kit.picture("pic.n", (0.0, 3.5, 1.9), (0.45, 0.6), gilt, canvas2, rot=0)

# --- south: a settee under pictures, a lamp table with books
kit.sofa("settee", (-0.7, -3.08), mahog, seat, rot=180, length=1.8, cushions=curtain)
kit.picture("pic.s1", (-0.7, -3.5, 1.85), (1.1, 0.75), gilt, canvas3, rot=180)
kit.picture("pic.s2", (-1.95, -3.5, 1.7), (0.4, 0.5), joinery, canvas1, rot=180)
kit.picture("pic.s3", (0.55, -3.5, 1.75), (0.4, 0.5), joinery, canvas2, rot=180)
kit.side_table("settee.table", (0.6, -3.15), mahog, size=0.45, height=0.7, round=False)
kit.clutter("settee.books", (0.6, -3.15, 0.7), "books", [bk4, bk2, bk1], rot=170, seed=9)

# corners: a reading chair and little tables
kit.armchair("armchair", (-2.3, -2.6), mahog, seat, rot=-135, kind="bergere")
kit.side_table("teatable", (-2.6, -1.7), mahog, size=0.5, height=0.68, round=True)
kit.clutter("teatable.books", (-2.6, -1.7, 0.68), "books", [bk1, bk3, bk2], rot=20, seed=7)
kit.side_table("cornertable", (2.5, 3.0), mahog, size=0.5, height=0.72, round=False)
kit.candle("cornercandle", (2.5, 3.0, 0.72), wax, power=3, height=0.2)

# --- light: the lamp dominates; faint warm fill, faint moonlight through the windows
kit.lamp("fill", (0.5, -1.0, 2.4), power=3, color=(1.0, 0.75, 0.60), radius=0.3)
kit.area_light("moon.w", (-1.3, 3.3, 1.8), (1.0, 1.6), 6, color=(0.62, 0.70, 0.95), aim=(0, -1, -0.3))
kit.area_light("moon.e", (1.3, 3.3, 1.8), (1.0, 1.6), 6, color=(0.62, 0.70, 0.95), aim=(0, -1, -0.3))
kit.sun(22, 95, strength=0.08, color=(0.62, 0.70, 1.0), softness=2.0)
kit.sky((0.02, 0.03, 0.06), (0.06, 0.07, 0.11), strength=0.1)

kit.reader((1.4, -1.9), (1.2, 3.5, 1.3))
