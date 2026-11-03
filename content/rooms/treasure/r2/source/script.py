# The squire's library on a cold moonlit night: fire on the east wall, moon through the west sashes,
# tall bookcases with busts lining the walls the reader sees.
R = kit.rng()
plaster = kit.mat("plaster", (0.30, 0.33, 0.30), kind="plaster")
ceilm = kit.mat("ceiling", (0.52, 0.50, 0.46), kind="plaster")
floor = kit.mat("floor", (0.22, 0.14, 0.08), kind="wood")
oak = kit.mat("oak", (0.32, 0.23, 0.14), kind="wood")
mahog = kit.mat("mahogany", (0.26, 0.13, 0.08), kind="wood")
books = [kit.mat("bk_oxblood", (0.34, 0.11, 0.09), kind="fabric"),
         kit.mat("bk_green", (0.13, 0.21, 0.14), kind="fabric"),
         kit.mat("bk_calf", (0.46, 0.33, 0.19), kind="fabric"),
         kit.mat("bk_navy", (0.11, 0.13, 0.22), kind="fabric"),
         kit.mat("bk_brown", (0.26, 0.18, 0.11), kind="fabric")]
marble = kit.mat("marble", (0.82, 0.80, 0.76), kind="rock", rough=0.25)
hearthst = kit.mat("hearthstone", (0.34, 0.32, 0.30), kind="rock")
brass = kit.mat("brass", (0.66, 0.51, 0.27), kind="metal", rough=0.3)
velvet = kit.mat("velvet", (0.19, 0.25, 0.17), kind="fabric")
rugm = kit.mat("rug", (0.24, 0.10, 0.12), kind="fabric")
rugb = kit.mat("rug_border", (0.13, 0.13, 0.20), kind="fabric")
curtain = kit.mat("curtain", (0.34, 0.11, 0.10), kind="fabric")
paint = kit.mat("paint", (0.72, 0.70, 0.64), kind="plaster")
glass = kit.mat("glass", (0.05, 0.06, 0.09), kind="glass")
canvas = kit.mat("canvas", (0.20, 0.18, 0.13), kind="plaster")
canvas2 = kit.mat("canvas_sea", (0.18, 0.22, 0.24), kind="plaster")
gilt = kit.mat("gilt", (0.60, 0.46, 0.22), kind="metal", rough=0.35)
china = kit.mat("china", (0.86, 0.85, 0.80), kind="plaster", rough=0.2)
paper = kit.mat("paper", (0.82, 0.77, 0.62), kind="fabric")
wax = kit.mat("wax", (0.90, 0.86, 0.74), kind="plaster")
leather = kit.mat("leather", (0.16, 0.22, 0.15), kind="fabric")
globem = kit.mat("globe", (0.58, 0.50, 0.34), kind="plaster", rough=0.4)
lawn = kit.mat("lawn", (0.26, 0.29, 0.28), kind="grass")
bark = kit.mat("bark", (0.20, 0.19, 0.17), kind="bark")
hwall = kit.mat("hall_walls", (0.78, 0.77, 0.72), kind="plaster")
slate = kit.mat("slate", (0.18, 0.19, 0.22), kind="rock")

room = kit.room("library", 10.0, 9.0, 4.2, plaster, floor, ceiling=ceilm, openings=[
    {"wall": "w", "at": -2.2, "width": 1.3, "height": 2.6, "sill": 0.7},
    {"wall": "w", "at": 2.2, "width": 1.3, "height": 2.6, "sill": 0.7},
    {"wall": "n", "at": 0.0, "width": 1.1, "height": 2.4, "sill": 0.0}])

CH = 2.8
cases = [
    (-2.8, 4.33, 0, 1.2), (-1.6, 4.33, 0, 1.2), (1.6, 4.33, 0, 1.2), (2.8, 4.33, 0, 1.2),
    (-4.83, 0.0, 90, 1.6), (-4.83, 3.6, 90, 0.9), (-4.83, -3.6, 90, 0.9),
    (4.83, -1.6, -90, 1.2), (4.83, 2.6, -90, 1.2), (4.83, 3.75, -90, 0.8)]
avoid = []
for i, (x, y, r, w) in enumerate(cases):
    kit.shelf(f"case{i}", (x, y), mahog, book_materials=books, width=w, height=CH, depth=0.32, rot=r, seed=i)
    if r == 0:
        avoid.append(("n", x, w + 0.05))
    elif r == 90:
        avoid.append(("w", y, w + 0.05))
    else:
        avoid.append(("e", y, w + 0.05))
avoid.append(("e", 0.5, 2.0))
kit.panelling(room, oak, dado=0.9, skirting=0.22, cornice=0.26, panels=True, picture_rail=3.1, avoid=avoid)
kit.windows(room, paint, glass, curtain=curtain, pelmet=mahog, panes=(3, 3), drawn=0.6)
kit.doors(room, paint, mahog, open_deg=0.0)

def bust(n, x, y, z, s):
    kit.cylinder(n + "_plinth", 0.11, 0.12, (x, y, z), marble, sides=8)
    kit.blob(n + "_chest", 0.17, (x, y, z + 0.12), marble, squash=(1.0, 0.6, 0.55), roughness=0.08, detail=1, seed=s)
    kit.blob(n + "_head", 0.11, (x, y, z + 0.28), marble, squash=(0.85, 0.95, 1.15), roughness=0.08, detail=1, seed=s + 3)

for i, (x, y, r, w) in enumerate(cases):
    if i in (5, 9):
        continue
    ox = R.uniform(-0.15, 0.15)
    if r == 0:
        bust(f"bust{i}", x + ox, y - 0.02, CH + 0.02, i)
    else:
        bust(f"bust{i}", x, y + ox, CH + 0.02, i)

# Fire, chairs either side, table near the hearth
kit.fireplace("chimneypiece", (5.0, 0.5), marble, rot=-90, width=1.6, height=1.25, fire=True, hearth_stone=hearthst)
kit.clutter("mantel", (4.85, 0.5, 1.27), "mantel", [gilt, china], rot=-90, seed=2)
kit.picture("overmantel", (4.99, 0.5, 2.45), (1.1, 0.85), gilt, canvas2, rot=-90)
kit.armchair("squire_chair", (3.5, -0.75), mahog, velvet, rot=118, kind="wing")
kit.armchair("doctor_chair", (3.5, 1.8), mahog, velvet, rot=64, kind="bergere")
kit.rug("hearth_rug", (3.4, 0.5), (2.0, 3.0), rugm, border=rugb)
kit.rug("main_rug", (-0.6, 0.3), (5.0, 4.4), rugm, rot=1.5, border=rugb)
kit.table("map_table", (2.25, 0.55), mahog, size=(1.4, 0.8, 0.76), rot=92, legs="turned")
kit.clutter("map", (2.25, 0.15, 0.77), "writing", [paper, brass], rot=88, seed=3)
kit.clutter("table_books", (2.3, 1.0, 0.77), "books", books[:4], rot=95, seed=4)
kit.candelabra("table_light", (2.1, 0.6, 0.77), brass, wax, arms=3, power=12)
kit.chair("table_chair", (1.45, 0.7), mahog, rot=97, fabric=velvet)
kit.side_table("tea_table", (2.9, -1.75), mahog, size=0.6, height=0.68, round=True)
kit.clutter("tea", (2.9, -1.75, 0.69), "tea", [china, brass], rot=20, seed=5)
kit.desk("desk", (-3.3, 1.3), mahog, rot=88, size=(1.2, 0.65, 0.76), top=leather, knobs=brass, kind="writing")
kit.chair("desk_chair", (-2.55, 1.25), mahog, rot=-85, fabric=velvet)
kit.clutter("desk_books", (-3.35, 1.4, 0.77), "books", books[2:], rot=80, seed=6)
kit.candle("desk_candle", (-3.45, 0.95, 0.77), wax, power=8)
# A terrestrial globe on a stand between the windows
kit.cylinder("globe_foot", 0.22, 0.05, (-3.7, -2.0, 0), mahog, sides=12)
kit.cylinder("globe_stem", 0.04, 0.62, (-3.7, -2.0, 0.05), mahog, sides=8, top_radius=0.03)
kit.cylinder("globe_ring", 0.3, 0.03, (-3.7, -2.0, 0.66), brass, sides=16)
kit.blob("globe_ball", 0.26, (-3.7, -2.0, 0.68), globem, roughness=0.01, detail=2, seed=9)
kit.picture("door_picture", (0.0, 4.49, 3.1), (0.9, 0.6), gilt, canvas, rot=0)
kit.picture("north_left_pic", (-4.0, 4.49, 1.9), (0.6, 0.8), gilt, canvas, rot=0)
kit.picture("north_right_pic", (4.0, 4.49, 1.9), (0.6, 0.8), gilt, canvas2, rot=0)
# South wall behind the reader: a settee under portraits
kit.sofa("settee", (0.0, -4.0), mahog, velvet, rot=180, length=2.0, cushions=curtain)
kit.picture("south_pic_a", (-1.6, -4.49, 2.0), (1.0, 1.3), gilt, canvas, rot=180)
kit.picture("south_pic_b", (1.6, -4.49, 2.0), (1.0, 1.3), gilt, canvas2, rot=180)
kit.chandelier("chandelier", (-0.3, 0.4, 4.2), brass, wax, arms=5, power=4, drop=1.0)

# Outside: frosted lawn, a leafless avenue and the pale line of the Hall
kit.terrain("park", (80, 80), lawn, res=24, relief=0.4, scale=20, seed=7, centre=(-46, 0), flat=[(-12, 0, 6, -0.2)])
for j, s in enumerate((-1, 1)):
    kit.tree(f"avenue{j}", (-13 + R.uniform(-1, 1), s * 6.0 + R.uniform(-0.6, 0.6)), R.uniform(10, 14),
             bark, bark, kind="dead", seed=j, lean=R.uniform(2, 6), detail=0)
kit.house("hall_wing", (-60, 20), (34, 12), hwall, slate, paint, glass, storeys=3, rot=90, bays=9, detail=0)
kit.far_hills((0.04, 0.05, 0.07), radius=95, height=7)

# Light: cool moon from the west, the fire as the warm heart, candles within, little fill
kit.sun(26, 180, strength=0.25, color=(0.62, 0.72, 1.0), softness=0.8)
kit.area_light("moon_win_s", (-5.5, -2.2, 1.9), (1.2, 2.2), 24, color=(0.58, 0.68, 1.0), aim=(1, 0, -0.35))
kit.area_light("moon_win_n", (-5.5, 2.2, 1.9), (1.2, 2.2), 24, color=(0.58, 0.68, 1.0), aim=(1, 0, -0.35))
kit.lamp("fire_glow", (4.3, 0.5, 0.6), power=200, color=(1.0, 0.55, 0.28), radius=0.35)
kit.lamp("fire_spill", (3.2, 0.5, 1.2), power=30, color=(1.0, 0.62, 0.36), radius=0.6)
kit.lamp("room_fill", (0.0, -0.5, 3.4), power=6, color=(0.95, 0.82, 0.68), radius=0.6)
kit.sky((0.01, 0.015, 0.04), (0.03, 0.04, 0.07), strength=0.06)
kit.reader((0.0, -1.8), (0.0, 4.0, 1.5))
