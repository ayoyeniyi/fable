# The Netherfield drawing-room, late evening: cards left mid-game, a few books, fire and candles.
R = kit.rng()

walls = kit.mat("walls", (0.74, 0.75, 0.70), kind="plaster")
ceil = kit.mat("ceiling", (0.82, 0.82, 0.79), kind="plaster")
floor = kit.mat("floor", (0.20, 0.14, 0.10), kind="plaster", rough=0.35)
joinery = kit.mat("joinery", (0.80, 0.80, 0.76), kind="plaster", rough=0.45)
wood = kit.mat("mahogany", (0.20, 0.10, 0.06), kind="plaster", rough=0.3)
marble = kit.mat("marble", (0.84, 0.83, 0.80), kind="rock", rough=0.25)
hearth_stone = kit.mat("hearthstone", (0.42, 0.41, 0.39), kind="rock")
gilt = kit.mat("gilt", (0.62, 0.49, 0.26), kind="plaster", rough=0.3)
canvas1 = kit.mat("canvas_landscape", (0.30, 0.36, 0.26), kind="rock", rough=0.6)
canvas2 = kit.mat("canvas_portrait", (0.12, 0.10, 0.09), kind="rock", rough=0.6)
canvas3 = kit.mat("canvas_sky", (0.48, 0.52, 0.55), kind="rock", rough=0.6)
mirror = kit.mat("mirror", (0.32, 0.33, 0.35), kind="plaster", rough=0.05)
glass = kit.mat("glass", (0.06, 0.08, 0.13), kind="plaster", rough=0.05)
curtain = kit.mat("curtain", (0.38, 0.17, 0.16), kind="fabric")
sofa_fab = kit.mat("sofa_silk", (0.58, 0.58, 0.50), kind="fabric")
chair_fab = kit.mat("chair_fabric", (0.30, 0.38, 0.33), kind="fabric")
cushion = kit.mat("cushion", (0.44, 0.24, 0.22), kind="fabric")
baize = kit.mat("baize", (0.12, 0.25, 0.17), kind="fabric")
cards = kit.mat("cards", (0.88, 0.86, 0.80), kind="plaster", rough=0.5)
counters = kit.mat("counters", (0.80, 0.78, 0.72), kind="plaster", rough=0.3)
book1 = kit.mat("book_red", (0.36, 0.13, 0.11), kind="fabric")
book2 = kit.mat("book_green", (0.16, 0.24, 0.18), kind="fabric")
book3 = kit.mat("book_tan", (0.48, 0.37, 0.25), kind="fabric")
paper = kit.mat("paper", (0.86, 0.83, 0.75), kind="plaster", rough=0.7)
brass = kit.mat("brass", (0.62, 0.50, 0.28), kind="plaster", rough=0.3)
wax = kit.mat("wax", (0.90, 0.88, 0.80), kind="plaster", rough=0.5)
china = kit.mat("china", (0.88, 0.88, 0.86), kind="plaster", rough=0.2)
rug = kit.mat("rug", (0.30, 0.30, 0.38), kind="fabric")
rug_border = kit.mat("rug_border", (0.40, 0.18, 0.15), kind="fabric")
rug_field = kit.mat("rug_field", (0.52, 0.44, 0.32), kind="fabric")
passage = kit.mat("passage", (0.36, 0.35, 0.32), kind="plaster")

kit.room("drawing", 9.0, 7.0, 3.6, walls, floor, ceiling=ceil, openings=[
    {"wall": "w", "at": -1.4, "width": 1.15, "height": 2.5, "sill": 0.65},
    {"wall": "w", "at": 1.4, "width": 1.15, "height": 2.5, "sill": 0.65},
    {"wall": "n", "at": 3.3, "width": 1.1, "height": 2.3, "sill": 0.0},
])
room = "drawing"
kit.panelling(room, joinery, dado=0.9, skirting=0.22, cornice=0.26, panels=True, upper=False,
              picture_rail=3.0, avoid=[("e", 0.0, 2.0)])
kit.windows(room, joinery, glass, curtain=curtain, pelmet=gilt, panes=(3, 2), drawn=0.15)
kit.doors(room, joinery, wood, open_deg=35)

# passage beyond the door, dim
kit.box("passage_floor", (2.6, 2.2, 0.02), (3.3, 4.65, 0.0), floor)
kit.box("passage_back", (2.6, 0.15, 3.0), (3.3, 5.7, 0.0), passage)
kit.box("passage_side", (0.15, 2.2, 3.0), (2.0, 4.65, 0.0), passage)
kit.box("passage_ceiling", (2.6, 2.2, 0.1), (3.3, 4.65, 2.9), passage)
kit.lamp("passage_light", (3.8, 5.2, 2.0), power=4, color=(1.0, 0.72, 0.45))

# fireplace on the east wall with a glass above and garniture
kit.fireplace("chimneypiece", (4.5, 0.0), marble, rot=-90, width=1.5, height=1.2, fire=True,
              hearth_stone=hearth_stone)
kit.picture("overmantel", (4.46, 0.0, 2.2), (1.1, 0.85), gilt, mirror, rot=-90, depth=0.07)
kit.clutter("garniture", (4.38, 0.0, 1.22), "mantel", [gilt, china], rot=-90, seed=2)
kit.picture("east_pic_n", (4.46, 2.2, 2.0), (0.55, 0.7), gilt, canvas2, rot=-90, depth=0.07)
kit.picture("east_pic_s", (4.46, -2.2, 2.0), (0.55, 0.7), gilt, canvas3, rot=-90, depth=0.07)

# rug and chandelier
kit.rug("carpet", (0.0, 0.5), (5.6, 4.4), rug, border=rug_border)
kit.rug("carpet_field", (0.0, 0.5, 0.006), (3.4, 2.4), rug_field, border=rug)
kit.chandelier("chandelier", (0.0, 0.6, 3.6), brass, wax, arms=8, power=7, drops=glass, drop=0.9)

# loo table, left mid-ground, cards left mid-game
tx, ty = -1.6, 1.0
kit.table("loo_table", (tx, ty), wood, size=(1.0, 1.0, 0.74), legs="turned")
kit.box("baize", (0.86, 0.86, 0.004), (tx, ty, 0.74), baize)
kit.candelabra("loo_candles", (tx, ty, 0.744), brass, wax, arms=3, power=8)
for i in range(16):
    a = R.uniform(0, 6.28)
    r = R.uniform(0.18, 0.38)
    kit.box(f"card{i}", (0.063, 0.088, 0.002),
            (tx + r * math.cos(a), ty + r * math.sin(a), 0.744 + 0.002 * (i % 3)), cards,
            rot=(0, 0, R.uniform(0, 180)))
for i in range(14):
    cx = tx + R.choice([-0.3, 0.3]) + R.uniform(-0.06, 0.06)
    cy = ty + R.choice([-0.3, 0.3]) + R.uniform(-0.06, 0.06)
    kit.cylinder(f"counter{i}", 0.013, 0.004, (cx, cy, 0.744 + 0.004 * (i % 2)), counters, sides=8)
kit.chair("loo_chair_s", (tx + 0.2, ty - 1.05), wood, rot=200, fabric=chair_fab)
kit.chair("loo_chair_n", (tx - 0.05, ty + 0.98), wood, rot=-8, fabric=chair_fab)
kit.chair("loo_chair_w", (tx - 1.1, ty + 0.2), wood, rot=110, fabric=chair_fab)
kit.chair("loo_chair_e", (tx + 1.05, ty + 0.25), wood, rot=-64, fabric=chair_fab)

# small table of a few books between the windows
kit.side_table("book_table", (-3.75, 0.0), wood, size=0.6, height=0.7, round=False)
kit.clutter("few_books", (-3.75, 0.0, 0.7), "books", [book1, book2, book3], rot=90, seed=4)
kit.candle("book_candle", (-3.6, 0.22, 0.7), wax, power=5)
kit.picture("pier_picture", (-4.46, 0.0, 2.05), (0.6, 0.75), gilt, canvas2, rot=90, depth=0.07)

# north wall: modest bookcase, landscape, side chair, writing desk
kit.shelf("bookcase", (-2.6, 3.28), wood, book_materials=(book1, book2, book3), width=1.2,
          height=2.0, depth=0.32, seed=3)
kit.picture("landscape", (-0.3, 3.46, 2.0), (1.1, 0.8), gilt, canvas1, depth=0.07)
kit.chair("wall_chair", (0.65, 3.15), wood, rot=9, fabric=chair_fab)
kit.desk("writing_desk", (1.8, 3.12), wood, size=(1.2, 0.65, 0.76), top=book2, kind="writing", knobs=brass)
kit.clutter("letters", (1.8, 3.05, 0.76), "writing", [paper, brass], seed=5)
kit.chair("desk_chair", (1.7, 2.3), wood, rot=163, fabric=chair_fab)
kit.candle("desk_candle", (2.25, 3.2, 0.76), wax, power=5)
kit.picture("portrait", (1.8, 3.46, 2.0), (0.65, 0.85), gilt, canvas2, depth=0.07)

# seating about the fire, right mid-ground
kit.sofa("settee", (2.4, 0.1), wood, sofa_fab, rot=93, length=1.9, cushions=cushion)
kit.armchair("arm_n", (3.4, 1.75), wood, chair_fab, rot=22, kind="bergere")
kit.armchair("arm_s", (3.45, -1.65), wood, sofa_fab, rot=158, kind="wing")
kit.side_table("tea_table", (3.0, 1.0), wood, size=0.5, height=0.7, round=True)
kit.clutter("tea", (3.0, 1.0, 0.7), "tea", [china, brass], seed=6)
kit.blob("dropped_cushion", 0.2, (2.0, 1.25, 0.0), cushion, squash=(1.0, 0.8, 0.45), roughness=0.15, seed=7)

# behind the reader: pier table with a tall glass and candles, pictures, chairs against the wall
kit.table("pier_table", (-1.6, -3.2), wood, size=(1.1, 0.45, 0.82), rot=0)
kit.picture("pier_glass", (-1.6, -3.46, 1.9), (0.9, 1.3), gilt, mirror, rot=180, depth=0.07)
kit.candelabra("pier_candles", (-1.85, -3.2, 0.82), brass, wax, arms=2, power=5)
kit.clutter("pier_books", (-1.35, -3.2, 0.82), "books", [book3, book1], seed=8)
kit.picture("south_picture", (1.2, -3.46, 2.0), (1.0, 0.75), gilt, canvas1, rot=180, depth=0.07)
kit.picture("south_small", (3.0, -3.46, 2.0), (0.5, 0.65), gilt, canvas3, rot=180, depth=0.07)
kit.chair("south_chair_a", (0.8, -3.15), wood, rot=180, fabric=chair_fab)
kit.chair("south_chair_b", (2.4, -3.05), wood, rot=166, fabric=chair_fab)
kit.picture("south_west_pic", (-3.6, -3.46, 2.0), (0.55, 0.7), gilt, canvas2, rot=180, depth=0.07)

# light: candles and fire carry the room; a soft, less amber fill, faint moonlight at the curtain gaps
kit.lamp("candle_fill", (0.0, 0.5, 2.6), power=11, color=(1.0, 0.87, 0.72), radius=0.6)
kit.lamp("fire_glow", (3.9, 0.0, 0.6), power=18, color=(1.0, 0.62, 0.35), radius=0.3)
kit.area_light("moon_n", (-5.3, 1.4, 2.0), (1.0, 2.0), 14, color=(0.70, 0.80, 1.0), aim=(1, 0, -0.3))
kit.area_light("moon_s", (-5.3, -1.4, 2.0), (1.0, 2.0), 14, color=(0.70, 0.80, 1.0), aim=(1, 0, -0.3))
kit.sky((0.01, 0.015, 0.04), (0.04, 0.05, 0.08), strength=0.15)

kit.reader((0.0, -2.2), (0.0, 3.5, 1.45))
