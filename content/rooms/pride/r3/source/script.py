# Mr. Bennet's library at Longbourn: soft grey afternoon, books on every side.
R = kit.rng()
plaster = kit.mat("plaster", (0.62, 0.64, 0.58), kind="plaster")
paint = kit.mat("panel_paint", (0.50, 0.53, 0.47), kind="paint")
ceil = kit.mat("ceiling", (0.78, 0.79, 0.76), kind="plaster")
floor = kit.mat("boards", (0.27, 0.20, 0.14), kind="wood")
mahog = kit.mat("mahogany", (0.27, 0.15, 0.10), kind="wood")
oak = kit.mat("oak", (0.40, 0.30, 0.20), kind="wood")
b1 = kit.mat("book_red", (0.38, 0.13, 0.10), kind="leather")
b2 = kit.mat("book_brown", (0.32, 0.22, 0.13), kind="leather")
b3 = kit.mat("book_green", (0.17, 0.25, 0.17), kind="leather")
b4 = kit.mat("book_tan", (0.52, 0.43, 0.30), kind="leather")
b5 = kit.mat("book_blue", (0.15, 0.19, 0.28), kind="leather")
b6 = kit.mat("book_calf", (0.44, 0.30, 0.18), kind="leather")
books = (b1, b2, b3, b4, b5, b6)
marble = kit.mat("marble", (0.80, 0.79, 0.76), kind="marble")
hstone = kit.mat("hearth_stone", (0.40, 0.39, 0.36), kind="stone")
uphol = kit.mat("upholstery", (0.38, 0.40, 0.33), kind="fabric")
rugm = kit.mat("rug", (0.32, 0.14, 0.12), kind="fabric")
rugb = kit.mat("rug_border", (0.40, 0.33, 0.22), kind="fabric")
gilt = kit.mat("gilt", (0.62, 0.50, 0.30), kind="metal", rough=0.45)
canvas1 = kit.mat("paint_sky", (0.62, 0.65, 0.62), kind="paint")
canvas2 = kit.mat("portrait", (0.20, 0.17, 0.14), kind="paint")
glass = kit.mat("glass", (0.80, 0.84, 0.86), kind="glass")
curtain = kit.mat("curtain", (0.38, 0.40, 0.33), kind="fabric")
brass = kit.mat("brass", (0.62, 0.50, 0.28), kind="metal", rough=0.4)
paper = kit.mat("paper", (0.86, 0.84, 0.77), kind="fabric")
china = kit.mat("china", (0.88, 0.88, 0.86), kind="plaster", rough=0.2)
leather = kit.mat("desk_leather", (0.20, 0.25, 0.17), kind="leather")
sash = kit.mat("sash_paint", (0.80, 0.81, 0.78), kind="paint")
grass = kit.mat("grass", (0.30, 0.36, 0.20), kind="grass")
blades = kit.mat("blades", (0.34, 0.42, 0.22), kind="foliage")
leaves = kit.mat("leaves", (0.22, 0.30, 0.16), kind="foliage")
bark = kit.mat("bark", (0.26, 0.21, 0.16), kind="bark")
lane = kit.mat("lane", (0.40, 0.35, 0.27), kind="soil")
cwall = kit.mat("cottage_wall", (0.66, 0.62, 0.54), kind="stone")
roofm = kit.mat("roof_tile", (0.36, 0.27, 0.22), kind="tile")

# Outside: the lane and the neighbourhood seen through the west windows
kit.terrain("land", (70, 70), grass, res=60, relief=0.5, scale=16, seed=7,
            slope=(0.008, 0.0), flat=[(0, 0, 6, -0.03)])
kit.footpath("lane", [(-8, -32), (-7.5, -10), (-8.5, 6), (-7.8, 32)], lane, width=3.2, ruts=True, seed=2)
kit.hedge("hedge", [(-11.5, -30), (-12, 0), (-11.2, 30)], leaves, height=1.7, near=(0, 0), seed=3,
          gaps=[(-12, 4, 3.0)], stems=bark)
kit.groundcover("verge", blades, (-30, -28, -4, 28), near=(-4, 0), blades=2500, height=0.35, seed=5)
for i, (x, y) in enumerate(kit.scatter((-28, -20, -15, 22), 6, seed=4, clusters=2)):
    kit.tree(f"tree{i}", (x, y), R.uniform(8, 13), bark, leaves, seed=i, detail=0 if x < -22 else 1)
kit.house("cottage", (-24, 10), (8, 6), cwall, roofm, sash, glass, storeys=2, storey_height=2.6,
          roof_kind="gable", pitch=45, rot=90, chimneys=1, detail=1, seed=2)
kit.far_hills((0.42, 0.46, 0.42), radius=90, height=7)

# The room
r = kit.room("library", 6.4, 7.0, 3.1, plaster, floor, ceiling=ceil, openings=[
    {"wall": "w", "at": -1.1, "width": 1.15, "height": 1.9, "sill": 0.75},
    {"wall": "w", "at": 1.7, "width": 1.15, "height": 1.9, "sill": 0.75},
    {"wall": "s", "at": 1.6, "width": 1.0, "height": 2.2, "sill": 0.0}])
kit.panelling(r, paint, dado=0.9, picture_rail=2.3, avoid=[
    ("n", -2.0, 2.0), ("n", 2.0, 2.0), ("e", -1.9, 1.6), ("e", 0.3, 1.7), ("e", 2.1, 1.6),
    ("s", -1.5, 1.6), ("w", 0.3, 0.9), ("w", -2.6, 1.3)])
kit.windows(r, sash, glass, curtain=curtain, pelmet=mahog, panes=(3, 2), drawn=0.6)
kit.doors(r, sash, mahog, open_deg=12)

# Bookcases: wide runs nearly filling the walls, slightly differing
kit.shelf("case_n1", (-2.02, 3.31), mahog, books, width=1.9, height=2.45, seed=1)
kit.shelf("case_n2", (1.98, 3.31), mahog, books, width=1.9, height=2.4, seed=2)
kit.shelf("case_e1", (3.01, -1.9), mahog, books, width=1.5, height=2.4, rot=-90, seed=3)
kit.shelf("case_e2", (3.01, 2.1), mahog, books, width=1.5, height=2.45, rot=-90, seed=4)
kit.shelf("case_s", (-1.5, -3.31), oak, books, width=1.5, height=2.2, rot=180, seed=5)
kit.shelf("case_w_low", (-3.01, 0.3), mahog, books, width=0.8, height=1.0, rot=90, seed=7, cornice=False)
kit.shelf("case_w_corner", (-3.01, -2.6), oak, books, width=1.2, height=2.1, rot=90, seed=8)
kit.clutter("low_books", (-2.93, 0.3, 1.0), "books", [b6, b3, b1], rot=88, seed=9)

# A simple painted landscape inside a frame on a north (sgn=1) or south (sgn=-1) wall
def painted(cx, wall_y, cz, w, h, sgn, tag):
    y = wall_y - sgn * 0.035
    iw = w * 0.82
    kit.box(f"{tag}_hill", (iw, 0.015, h * 0.14), (cx, y, cz - h * 0.14), leaves, rot=(0, 4, 0))
    kit.box(f"{tag}_field", (iw, 0.02, h * 0.26), (cx, y - sgn * 0.004, cz - h * 0.38), grass)
    kit.blob(f"{tag}_treeA", h * 0.13, (cx - w * 0.22, y - sgn * 0.006, cz - h * 0.02), leaves,
             squash=(1.0, 0.12, 1.3), seed=11)
    kit.blob(f"{tag}_treeB", h * 0.09, (cx + w * 0.26, y - sgn * 0.006, cz - h * 0.08), leaves,
             squash=(1.0, 0.12, 1.2), seed=12)
    kit.box(f"{tag}_lane", (w * 0.12, 0.022, h * 0.2), (cx + w * 0.05, y - sgn * 0.008, cz - h * 0.38),
            lane, rot=(0, 20, 0))

# Chimneypiece on the east wall, a portrait over it, things round the hearth
kit.fireplace("fire", (3.2, 0.3), marble, rot=-90, width=1.4, height=1.2, hearth_stone=hstone)
kit.clutter("mantel", (3.05, 0.3, 1.22), "mantel", [gilt, china], rot=-90, seed=1)
kit.picture("portrait", (3.2, 0.3, 2.05), (0.6, 0.75), gilt, canvas2, rot=-90)
kit.box("portrait_coat", (0.02, 0.30, 0.26), (3.165, 0.3, 1.74), b5)
kit.box("portrait_stock", (0.022, 0.09, 0.08), (3.162, 0.3, 1.98), paper)
kit.blob("portrait_face", 0.07, (3.16, 0.3, 2.12), paper, squash=(0.2, 0.8, 1.05), seed=7)
kit.rug("hearth_rug", (2.55, 0.3), (0.7, 1.5), rugb, rot=0, border=rugm)
kit.cylinder("log_basket", 0.2, 0.32, (2.8, 1.25, 0.0), oak, sides=12, top_radius=0.23)
for i in range(3):
    kit.cylinder(f"log{i}", 0.05, 0.42, (2.72 + i * 0.07, 1.18 + i * 0.05, 0.3), bark,
                 rot=(R.uniform(60, 80), 0, R.uniform(-30, 30)), sides=7)
kit.cylinder("fire_irons", 0.012, 0.75, (2.9, -0.55, 0.0), brass, rot=(4, 3, 0), sides=6)

# North wall centre: landscape over a table, a little off the axis
kit.picture("landscape", (0.05, 3.5, 1.65), (0.9, 0.65), gilt, canvas1, rot=0)
painted(0.05, 3.5, 1.65, 0.9, 0.65, 1, "landA")
kit.side_table("n_table", (0.15, 3.12), mahog, size=0.65, height=0.72, round=False)
kit.clutter("n_books", (0.15, 3.12, 0.72), "books", [b2, b4, b5], rot=6, seed=2)

# South wall behind the reader: a picture over a table with papers
kit.picture("view_s", (0.2, -3.5, 1.7), (0.8, 0.6), gilt, canvas1, rot=180)
painted(0.2, -3.5, 1.7, 0.8, 0.6, -1, "landB")
kit.picture("small_s", (-0.55, -3.5, 2.55), (0.3, 0.36), gilt, canvas2, rot=180)
kit.side_table("s_table", (0.15, -3.18), oak, size=0.75, height=0.74, round=False)
kit.clutter("s_papers", (0.15, -3.18, 0.74), "writing", [paper, brass], rot=176, seed=8)

# Pier between the west windows: a larger picture over the low case
kit.picture("pier_pic", (-3.2, 0.3, 1.75), (0.6, 0.75), gilt, canvas1, rot=90)

# Two chairs facing each other for a morning call
kit.armchair("chair_a", (1.8, 1.25), oak, uphol, rot=-8, kind="bergere")
kit.armchair("chair_b", (1.9, -0.65), oak, uphol, rot=172, kind="bergere")
kit.side_table("tea_table", (1.35, 0.3), mahog, size=0.5, round=True)
kit.clutter("tea", (1.35, 0.3, 0.7), "tea", [china, mahog], rot=20, seed=3)
kit.rug("rug", (0.7, 0.5), (3.9, 3.0), rugm, rot=2, border=rugb)
kit.rug("desk_rug", (-2.1, 1.6), (1.0, 1.6), rugb, rot=-3, border=rugm)

# Writing table by the window
kit.desk("desk", (-2.45, 1.6), mahog, rot=90, size=(1.2, 0.65, 0.76), top=leather, knobs=brass)
kit.clutter("letters", (-2.45, 1.45, 0.76), "writing", [paper, brass], rot=95, seed=4)
kit.clutter("open_book", (-2.5, 1.95, 0.76), "books", [b1, b3, b4], rot=80, seed=5)
kit.chair("desk_chair", (-1.75, 1.55), mahog, rot=-80, fabric=uphol)
kit.chair("spare_chair", (-2.2, -1.85), mahog, rot=35, fabric=uphol)
kit.clutter("floor_books", (2.45, -2.75, 0.0), "books", [b2, b5, b1], rot=-15, seed=6)
kit.candelabra("desk_candles", (-2.55, 1.15, 0.76), brass, china, arms=2, power=1)

# Light: grey daylight through the west sashes dominates; a low fire; cool soft fill
kit.sun(30, 200, strength=1.0, color=(0.90, 0.93, 0.98), softness=4.0)
kit.area_light("win1", (-3.7, -1.1, 1.75), (1.2, 1.8), 180, color=(0.84, 0.89, 0.97), aim=(1, 0, -0.25))
kit.area_light("win2", (-3.7, 1.7, 1.75), (1.2, 1.8), 180, color=(0.84, 0.89, 0.97), aim=(1, 0, -0.25))
kit.area_light("fill", (0.0, 0.3, 3.0), (3.0, 3.0), 40, color=(0.88, 0.91, 0.96), aim=(0, 0, -1))
kit.sky((0.58, 0.62, 0.67), (0.74, 0.75, 0.75), strength=0.85)
kit.reader((0.0, -1.6), (0.0, 3.4, 1.45))
