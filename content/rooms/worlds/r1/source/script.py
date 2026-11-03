rng = kit.rng()
walls = kit.mat("walls", (0.27, 0.24, 0.20), kind="plaster")
floor = kit.mat("boards", (0.22, 0.16, 0.10), kind="wood")
wood = kit.mat("oak", (0.26, 0.18, 0.11), kind="wood")
domewood = kit.mat("dome", (0.24, 0.21, 0.17), kind="wood")
ribwood = kit.mat("ribs", (0.17, 0.12, 0.08), kind="wood")
brass = kit.mat("brass", (0.58, 0.45, 0.24), kind="metal", rough=0.38)
iron = kit.mat("iron", (0.10, 0.10, 0.11), kind="metal", rough=0.6)
glass = kit.mat("glass", (0.40, 0.47, 0.46), kind="glass", rough=0.1)
glow = kit.mat("lanternglow", (1.0, 0.72, 0.40), kind="glass", emission=5.0, emission_color=(1.0, 0.70, 0.38))
stars = kit.mat("stars", (1.0, 1.0, 1.0), kind="plaster", emission=10.0, emission_color=(0.92, 0.94, 1.0))
dust = kit.mat("stardust", (0.5, 0.55, 0.7), kind="plaster", emission=0.35, emission_color=(0.55, 0.60, 0.80))
rugm = kit.mat("rug", (0.30, 0.14, 0.10), kind="fabric")
rugb = kit.mat("rugborder", (0.17, 0.13, 0.09), kind="fabric")
book_mats = [kit.mat("book1", (0.34, 0.13, 0.10), kind="leather"),
             kit.mat("book2", (0.15, 0.22, 0.16), kind="leather"),
             kit.mat("book3", (0.38, 0.29, 0.18), kind="leather"),
             kit.mat("book4", (0.17, 0.17, 0.24), kind="leather")]
paper = kit.mat("paper", (0.70, 0.66, 0.56), kind="paper")
wax = kit.mat("wax", (0.85, 0.80, 0.68), kind="wax")
chart = kit.mat("starchart", (0.09, 0.11, 0.20), kind="paper")
print_m = kit.mat("print", (0.50, 0.47, 0.40), kind="paper")
leather = kit.mat("leathertop", (0.15, 0.19, 0.13), kind="leather")
seat = kit.mat("seat", (0.28, 0.18, 0.12), kind="fabric")

W = 6.0
H = 2.8
room = kit.room("obs", W, W, H, walls, floor, ceiling=None, openings=[
    {"wall": "s", "at": -1.6, "width": 0.95, "height": 2.05, "sill": 0.0},
    {"wall": "w", "at": -1.0, "width": 0.75, "height": 0.9, "sill": 1.15}])
kit.panelling(room, ribwood, dado=1.1, skirting=0.2, cornice=0.18, picture_rail=2.1,
              avoid=[("e", 0.6, 1.6), ("s", 0.4, 1.4)])
kit.windows(room, iron, glass, curtain=None, panes=(2, 2))
kit.doors(room, ribwood, wood, open_deg=6)

# vaulted dome with a wider oblong slit running north from the crown
N = 28
R = W / 2 + 0.12
DH = 2.2
SW = 0.2
def domez(u, v):
    m = min(1.0, max(abs(u), abs(v)))
    return H + DH * math.sqrt(max(0.0, 1 - m * m))
verts = []
for i in range(N + 1):
    for j in range(N + 1):
        u = -1 + 2 * i / N
        v = -1 + 2 * j / N
        verts.append((u * R, v * R, domez(u, v)))
faces = []
for i in range(N):
    for j in range(N):
        uc = -1 + 2 * (i + 0.5) / N
        vc = -1 + 2 * (j + 0.5) / N
        if abs(uc) < SW and -0.3 < vc < 0.97:
            continue
        a = i * (N + 1) + j
        faces.append((a, a + N + 1, a + N + 2, a + 1))
kit.mesh("dome", verts, faces, domewood, smooth=True)

# dome ribs and a base ring, so the vault reads as structure
bv = []
bf = []
def strip(pts):
    base = len(bv)
    for (x, y, z) in pts:
        bv.extend([(x, y, z - 0.02), (x, y, z - 0.13)])
    for k in range(len(pts) - 1):
        a = base + 2 * k
        bf.append((a, a + 2, a + 3, a + 1))
for u0 in (-0.78, -0.5, -0.27, 0.27, 0.5, 0.78):
    strip([(u0 * R, (-1 + 2 * k / 24) * R, domez(u0, -1 + 2 * k / 24)) for k in range(25)])
for v0 in (-0.7, -0.4):
    strip([((-1 + 2 * k / 24) * R, v0 * R, domez(-1 + 2 * k / 24, v0)) for k in range(25)])
kit.mesh("domeribs", bv, bf, ribwood)
kit.box("ring_n", (W, 0.14, 0.12), (0, 2.93, H - 0.06), ribwood)
kit.box("ring_s", (W, 0.14, 0.12), (0, -2.93, H - 0.06), ribwood)
kit.box("ring_e", (0.14, W, 0.12), (2.93, 0, H - 0.06), ribwood)
kit.box("ring_w", (0.14, W, 0.12), (-2.93, 0, H - 0.06), ribwood)

# iron shutter rails along the slit edges
rv = []
rf = []
for x0 in (-SW * R - 0.03, SW * R + 0.03):
    base = len(rv)
    steps = 16
    for k in range(steps + 1):
        v = -0.32 + 1.3 * k / steps
        z = domez(x0 / R, v) - 0.02
        rv += [(x0, v * R, z), (x0, v * R, z - 0.15)]
    for k in range(steps):
        a = base + 2 * k
        rf.append((a, a + 2, a + 3, a + 1))
kit.mesh("slitrails", rv, rf, iron)

# stars through the slit, a streak of stardust across it
sv = []
sf = []
def quad(x, y, z, s):
    b = len(sv)
    sv.extend([(x - s, y - s, z), (x + s, y - s, z), (x + s, y + s, z), (x - s, y + s, z)])
    sf.append((b, b + 1, b + 2, b + 3))
for k in range(500):
    t = rng.uniform(0, 1)
    quad(-12 + 16 * t + rng.gauss(0, 1.3), 30 - 26 * t + rng.gauss(0, 1.8), rng.uniform(19, 21), rng.uniform(0.025, 0.07))
for k in range(350):
    s = rng.uniform(0.04, 0.10) if rng.random() < 0.9 else rng.uniform(0.12, 0.18)
    quad(rng.uniform(-12, 10), rng.uniform(-4, 42), rng.uniform(18, 23), s)
kit.mesh("starfield", sv, sf, stars)
dv = []
df = []
for k in range(40):
    t = rng.uniform(0, 1)
    x = -12 + 16 * t + rng.gauss(0, 0.8)
    y = 30 - 26 * t + rng.gauss(0, 1.0)
    s = rng.uniform(0.6, 1.4)
    b = len(dv)
    dv += [(x - s, y - s * 0.6, 21.5), (x + s, y - s * 0.6, 21.5), (x + s, y + s * 0.6, 21.5), (x - s, y + s * 0.6, 21.5)]
    df.append((b, b + 1, b + 2, b + 3))
kit.mesh("milkyway", dv, df, dust)

# the telescope on its pier under the slit, with clockwork drive
kit.cylinder("pier", 0.17, 1.0, (0.0, 1.4, 0), iron, sides=16, top_radius=0.13)
kit.box("mount", (0.30, 0.34, 0.25), (0.0, 1.35, 1.0), iron, bevel=0.02)
kit.cylinder("tube", 0.105, 2.1, (0.0, 1.25, 1.2), brass, rot=(-38, 0, 0), sides=20, top_radius=0.09)
kit.cylinder("dewcap", 0.115, 0.25, (0.0, 2.38, 2.65), iron, rot=(-38, 0, 0), sides=20)
kit.cylinder("eyepiece", 0.028, 0.16, (0.0, 1.25, 1.2), brass, rot=(142, 0, 0), sides=10)
kit.cylinder("finder", 0.028, 0.5, (0.13, 1.45, 1.42), brass, rot=(-38, 0, 0), sides=10)
kit.cylinder("weightrod", 0.015, 0.45, (-0.45, 1.35, 1.12), iron, rot=(0, 90, 0), sides=8)
kit.cylinder("counterweight", 0.07, 0.12, (-0.52, 1.35, 1.12), iron, rot=(0, 90, 0), sides=12)
kit.box("clockwork", (0.16, 0.22, 0.22), (0.22, 1.45, 0.72), brass, bevel=0.01)
kit.cylinder("drivecord", 0.004, 0.45, (0.22, 1.45, 0.27), iron, sides=6)
kit.cylinder("driveweight", 0.04, 0.16, (0.22, 1.45, 0.11), iron, sides=10)
kit.chair("observingchair", (0.05, 0.55), wood, rot=180, fabric=seat)
kit.rug("rug", (0.0, 1.0), (2.0, 1.6), rugm, rot=3, border=rugb)

# the shuttered lantern in the north-east corner
lx, ly = 2.55, 2.55
kit.box("lanternbase", (0.22, 0.22, 0.04), (lx, ly, 0), iron)
kit.box("lanternglass", (0.16, 0.16, 0.22), (lx, ly, 0.04), glow)
kit.box("shutter", (0.2, 0.02, 0.24), (lx - 0.03, ly - 0.11, 0.03), iron, rot=(0, 0, 22))
kit.box("shutter2", (0.02, 0.2, 0.24), (lx - 0.11, ly - 0.02, 0.03), iron, rot=(0, 0, -10))
kit.cylinder("lanterntop", 0.13, 0.1, (lx, ly, 0.26), iron, sides=8, top_radius=0.03)
kit.cylinder("lanternring", 0.05, 0.01, (lx, ly, 0.38), iron, rot=(90, 0, 0), sides=8)
kit.lamp("lanternlight", (lx - 0.22, ly - 0.22, 0.2), power=130, color=(1.0, 0.66, 0.34), radius=0.06)

# little table with the soda siphon
kit.side_table("siphontable", (1.85, 1.95), wood, size=0.48, height=0.7, round=True)
kit.cylinder("siphon", 0.045, 0.24, (1.83, 1.95, 0.71), glass, sides=14)
kit.cylinder("siphonhead", 0.032, 0.08, (1.83, 1.95, 0.95), brass, sides=10)
kit.box("spout", (0.08, 0.015, 0.015), (1.87, 1.95, 1.0), brass, rot=(0, -15, 0))
kit.cylinder("tumbler", 0.035, 0.09, (1.96, 1.87, 0.71), glass, sides=12)

# books, writing table, star chart
kit.shelf("shelf_e", (2.82, 0.6), wood, book_materials=book_mats, width=1.4, height=1.9, rot=-90, seed=3)
kit.shelf("shelf_s", (0.4, -2.82), wood, book_materials=book_mats, width=1.2, height=1.7, rot=180, seed=8)
kit.desk("desk", (-2.6, 1.4), wood, rot=90, size=(1.1, 0.6, 0.76), top=leather, knobs=brass)
kit.clutter("deskpapers", (-2.6, 1.35, 0.77), "writing", [paper, brass], rot=90, seed=2)
kit.candle("deskcandle", (-2.7, 1.85, 0.77), wax, power=12)
kit.chair("deskchair", (-2.0, 1.3), wood, rot=-80, fabric=seat)
kit.picture("chart", (1.3, 2.91, 1.7), (0.8, 0.62), wood, chart, rot=0)
kit.picture("moonprint", (-1.4, 2.91, 1.6), (0.45, 0.36), wood, print_m, rot=0)
kit.picture("map_e", (2.91, -1.2, 1.65), (0.7, 0.55), wood, print_m, rot=-90)
kit.picture("chart_e", (2.91, -2.25, 1.75), (0.35, 0.45), wood, chart, rot=-90)
# barometer on the east wall
kit.box("barometer", (0.05, 0.12, 0.8), (2.94, -0.15, 1.3), wood, bevel=0.01)
kit.cylinder("barodial", 0.1, 0.03, (2.92, -0.15, 1.85), brass, rot=(0, 90, 0), sides=16)
kit.box("chest", (0.9, 0.5, 0.5), (-2.4, -2.4, 0), wood, rot=(0, 0, 4), bevel=0.02)
kit.clutter("chestbooks", (-2.4, -2.4, 0.5), "books", book_mats, rot=4, seed=5)
# instrument case on the south wall
kit.box("instcase", (0.6, 0.35, 0.3), (-0.6, -2.75, 0), wood, rot=(0, 0, -3), bevel=0.02)
kit.box("instlid", (0.5, 0.25, 0.08), (-0.6, -2.75, 0.3), ribwood, rot=(0, 0, 2), bevel=0.01)

# shaded oil lamp behind the reader, a low warm light on the page
kit.side_table("lamptable", (2.05, -2.45), wood, size=0.42, height=0.7, round=False)
kit.cylinder("lampfont", 0.07, 0.12, (2.05, -2.45, 0.71), brass, sides=12, top_radius=0.05)
kit.cylinder("lampchimney", 0.035, 0.2, (2.05, -2.45, 0.83), glow, sides=10)
kit.cylinder("lampshade", 0.13, 0.12, (2.05, -2.45, 0.95), ribwood, sides=14, top_radius=0.07)
kit.lamp("oillamp", (2.05, -2.45, 0.92), power=45, color=(1.0, 0.72, 0.42), radius=0.05)

# midnight: deep starry sky, cool spill through the slit and the small window
kit.sky((0.01, 0.014, 0.04), (0.03, 0.035, 0.07), strength=0.3)
kit.sun(40, 95, strength=0.06, color=(0.70, 0.78, 1.0), softness=0.8)
kit.area_light("slitlight", (0.0, 1.2, 4.7), (0.8, 3.2), 70, color=(0.66, 0.74, 1.0))
kit.area_light("windowlight", (-2.8, -1.0, 1.6), (0.7, 0.8), 12, color=(0.66, 0.74, 1.0), aim=(1, 0, -0.2))
kit.reader((1.3, -1.6), (0.9, 3.5, 1.6))
