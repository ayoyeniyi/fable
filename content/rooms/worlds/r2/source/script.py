# Horsell Common at dawn: the reader on a low rise of heather, the fresh pit with its half-buried, scale-crusted cylinder front-left,
# a loose group of pines towards the low sun, sandy tracks across the heath and a faint thread of smoke far to the east.
r = kit.rng()
sand = kit.mat("sand", (0.60, 0.50, 0.35), kind="soil")
sand_dark = kit.mat("sand_dark", (0.46, 0.38, 0.27), kind="soil")
gravel_soil = kit.mat("gravel_soil", (0.50, 0.45, 0.38), kind="soil")
turf = kit.mat("turf", (0.40, 0.37, 0.24), kind="grass")
heather = kit.mat("heather", (0.30, 0.24, 0.20), kind="foliage")
heath_bush = kit.mat("heath_bush", (0.26, 0.21, 0.18), kind="foliage")
heath_green = kit.mat("heath_green", (0.24, 0.26, 0.16), kind="foliage")
bloom = kit.mat("bloom", (0.45, 0.33, 0.42), kind="fabric")
gravel = kit.mat("gravel", (0.50, 0.46, 0.40), kind="rock")
scale = kit.mat("scale", (0.36, 0.32, 0.26), kind="rock", rough=0.97)
ash = kit.mat("ash", (0.48, 0.44, 0.38), kind="rock", rough=0.98)
bark = kit.mat("bark", (0.31, 0.21, 0.16), kind="bark")
needles = kit.mat("needles", (0.15, 0.20, 0.13), kind="foliage")
splint = kit.mat("splinter", (0.64, 0.52, 0.38), kind="bark", rough=0.85)
char = kit.mat("char", (0.12, 0.10, 0.09), kind="soil")
ember = kit.mat("ember", (0.9, 0.42, 0.16), kind="plaster", emission=1.2)
smoke = kit.mat("smoke", (0.62, 0.66, 0.76), kind="plaster", emission=0.04, emission_color=(0.60, 0.64, 0.76))

CX, CY = -16.0, 22.0
kit.terrain("heath", (170, 170), turf, res=54, relief=0.7, scale=20, seed=7, slope=(0.01, 0.0),
            flat=[(0, 0, 3.0, 0.6)], valley=(CX - 4, CY, CX + 4, CY, 30, 6.0))

# raw sand floor of the pit
kit.blob("pitfloor", 12.5, (CX, CY, kit.ground(CX, CY) - 1.2), sand_dark, squash=(1.2, 1.0, 0.12), roughness=0.35, detail=2, seed=3)

# the cylinder, about thirty yards across, almost entirely buried
R = 13.0
g = kit.ground(CX, CY)
CZ = g + 3.2 - R
ang = math.radians(-30)
ax = (math.sin(ang), -math.cos(ang))
nx = (-ax[1], ax[0])
loc = (CX - ax[0] * 7.0, CY - ax[1] * 7.0, CZ)
kit.cylinder("cylinder", R, 14.0, loc, scale, rot=(90, 0, -30), sides=40)
for i in range(18):
    t = r.uniform(-6.5, 6.5)
    s = r.uniform(-8.0, 8.0)
    x = CX + ax[0] * t + nx[0] * s
    y = CY + ax[1] * t + nx[1] * s
    z = CZ + math.sqrt(max(R * R - s * s, 0)) - 0.35
    m = ash if i % 3 == 0 else scale
    kit.blob(f"crust{i}", r.uniform(0.7, 1.6), (x, y, z), m, squash=(1.3, 1.0, r.uniform(0.35, 0.6)),
             roughness=0.55, detail=1, seed=i)
for i in range(6):
    t = r.uniform(-6, 6)
    s = r.uniform(-7.5, 7.5)
    x = CX + ax[0] * t + nx[0] * s
    y = CY + ax[1] * t + nx[1] * s
    z = CZ + math.sqrt(max(R * R - s * s, 0)) - 0.3
    kit.blob(f"sandcap{i}", r.uniform(1.0, 2.2), (x, y, z), sand, squash=(1.6, 1.2, 0.35), roughness=0.4, detail=1, seed=40 + i)

# a continuous rim of flung sand and gravel, overlapping heaps, lower on the reader's side
toward = math.atan2(-CY, -CX)
for i in range(24):
    a = i / 24 * math.tau + r.uniform(-0.08, 0.08)
    d = r.uniform(13.5, 16.5)
    x, y = CX + math.cos(a) * d, CY + math.sin(a) * d
    near_side = abs((a - toward + math.pi) % math.tau - math.pi) < 0.8
    rad = r.uniform(1.6, 2.4) if near_side else r.uniform(2.6, 4.0)
    m = [sand, sand_dark, gravel_soil][i % 3]
    kit.blob(f"heap{i}", rad, (x, y, kit.ground(x, y) - rad * 0.3), m,
             squash=(1.7, 1.2, r.uniform(0.45, 0.65)), roughness=0.45, detail=1, seed=i)
# sand thrown out over the heath, thinning towards the reader
spills = [(-6.0, 7.0), (-8.5, 10.0), (-4.0, 12.0), (-11.0, 5.5), (-3.0, 16.0), (5.0, 13.0), (-13.0, 8.5), (-9.0, 3.5)]
for i, (x, y) in enumerate(spills):
    rad = r.uniform(0.7, 1.5)
    kit.blob(f"spill{i}", rad, (x, y, kit.ground(x, y) - rad * 0.25), sand if i % 2 else gravel_soil,
             squash=(2.0, 1.4, 0.28), roughness=0.5, detail=1, seed=20 + i)
for i, (x, y) in enumerate(kit.scatter((-15, 3, 3, 17), 14, seed=5, clusters=4, avoid=[(0, 0, 3.0), (1.5, 8, 3.0)])):
    kit.rock(f"gravel{i}", (x, y), r.uniform(0.08, 0.3), gravel, seed=i)

# the fir it shivered to fragments, at the pit's near rim
FX, FY = -6.5, 12.5
kit.cylinder("fir.stump", 0.34, 1.3, (FX, FY, kit.ground(FX, FY) - 0.1), bark, rot=(9, -6, 0), top_radius=0.2, sides=9)
kit.cylinder("fir.top", 0.24, 6.5, (FX - 2.0, FY + 1.5, kit.ground(FX - 2.0, FY + 1.5) + 0.15), bark, rot=(86, 0, 70), top_radius=0.07, sides=8)
kit.cylinder("fir.limb", 0.12, 3.0, (FX + 1.5, FY + 3.0, kit.ground(FX + 1.5, FY + 3.0) + 0.05), bark, rot=(85, 0, -40), top_radius=0.04, sides=6)
for i, (x, y) in enumerate(kit.scatter((-14, 9, -2, 19), 22, seed=9, clusters=3, spread=0.3, avoid=[(0, 0, 3.0)])):
    m = splint if i % 3 else bark
    kit.box(f"splinter{i}", (r.uniform(0.05, 0.16), r.uniform(0.3, 2.2), r.uniform(0.04, 0.12)),
            (x, y, kit.ground(x, y) - 0.02), m, rot=(r.uniform(-12, 12), r.uniform(-25, 25), r.uniform(0, 180)))

# pines: a loose, uneven group towards the low sun, odd ones about the heath
pines = [(15, 11, 15, 1), (18.5, 13.5, 10, 1), (23, 19, 18, 0), (20, 6, 12, 0), (31, -5, 16, 0),
         (10, 38, 14, 0), (-38, 3, 17, 0), (-4, 50, 13, 0), (13, -24, 16, 0)]
for i, (x, y, h, d) in enumerate(pines):
    kit.tree(f"pine{i}", (x, y), h, bark, needles, kind="conifer", seed=i + 3, lean=r.uniform(3, 11), detail=d)

# sandy tracks across the heath
kit.footpath("track", [(-30, -20), (-12, -8), (-4, -3), (6, 4), (14, 16), (26, 34)], sand, width=1.2, seed=2, wear=0.6)
kit.footpath("track2", [(6, 4), (18, -2), (40, -8)], sand_dark, width=0.8, seed=3, wear=0.7)

# heather in drifts of mounds
for i, (x, y) in enumerate(kit.scatter((-12, -10, 12, 12), 9, seed=11, clusters=3, spread=0.3,
                                       avoid=[(0, 0, 2.2), (1.5, 7, 2.6), (CX, CY, 17)])):
    kit.shrub(f"heathn{i}", (x, y), r.uniform(0.35, 0.8), heath_bush if i % 3 else heath_green, seed=i, detail=1)
for i, (x, y) in enumerate(kit.scatter((-40, -35, 40, 40), 12, seed=12, clusters=5, spread=0.3,
                                       avoid=[(0, 0, 10), (CX, CY, 17)])):
    kit.shrub(f"heathf{i}", (x, y), r.uniform(0.5, 1.2), heath_bush if i % 2 else heath_green, seed=50 + i, detail=0)
kit.groundcover("heather", heather, (-40, -35, 40, 45), near=(0, 0), blades=3200, height=0.38, seed=4,
                avoid=[(CX, CY, 15.5), (0, 0, 0.6)], flowers=bloom, flower_share=0.05, patchiness=0.55)
kit.tufts("heath.l", (-2.6, 2.4), 1.0, 45, 0.4, heather, seed=2, flowers=bloom, flower_share=0.08)
kit.tufts("heath.r", (3.0, 1.0), 0.9, 40, 0.35, heather, seed=6, flowers=bloom, flower_share=0.06)

# heather smouldering far to the east: a faint blue thread of smoke
SX, SY = 88, 14
kit.box("burnt", (3.0, 16.0, 0.05), (SX, SY, kit.ground(SX, SY)), char)
for i in range(3):
    kit.box(f"ember{i}", (0.4, 0.4, 0.05), (SX + r.uniform(-1, 1), SY - 4 + i * 3, kit.ground(SX, SY - 4 + i * 3) + 0.02), ember)
for i in range(14):
    kit.blob(f"smoke{i}", 0.12 + i * 0.028, (SX - i * 0.25, SY + i * 0.12, kit.ground(SX, SY) + 0.6 + i * 1.4), smoke,
             squash=(1, 1, 2.8), roughness=0.3, detail=1, seed=i)

kit.far_hills((0.48, 0.45, 0.44), radius=115, height=3.5, seed=6)
kit.sun(7, 15, strength=4.0, color=(1.0, 0.80, 0.58))
kit.sky((0.42, 0.55, 0.76), (0.96, 0.82, 0.64), strength=0.9, ground_color=(0.42, 0.38, 0.32))
kit.reader((0, 0), (2, 14, 1.4))
