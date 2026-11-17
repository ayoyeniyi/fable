"""
Fable: the Phaeacians' place of assembly and games ground near the ships (The Odyssey, Book VIII, Samuel Butler's 1900
prose translation). A chapter step-in room: built ahead of time, served from the server, downloaded by the headset.

"... the place of assembly, which was near the ships. When they got there they sat side by side on a seat of polished
stone" ... "Then they went to the place of assembly" ... the discus "flew beyond any mark" ... "the young men ...
levelled the ground for the dance and made a wide space" ... "they brought the lyre ... and hung it on a peg" (Book VIII)

The moment: a clear, bright morning, after the races and the throwing. The reader stands beside the seats of polished
stone at the edge of the place of assembly, facing out over the games ground: packed earth scuffed and dusty, the
starting post of the foot race, the marks pegged in the ground and the stone discus lying far beyond them, the smoothed
circle of the dancing floor with Demodocus's chair and his lyre hung on its peg on a post. Behind the ground the long
timber ship sheds with black ships drawn up in them, more ships afloat in the harbour, masts, oars and furled sails, and
the sea beyond. No people.

Living scene (docs/LIVING_SCENES.md): water.ocean.harbour, cloth.sail.furled, cloth.flag.pennant, veg.grass.edges,
sound.crowd.assembly, sound.gulls.harbour, sound.rigging.ships, sound.wind.ground.

Node names: anchor.reader.entrance, anchor.reader.look, anchor.scene.centre (the games ground), anchor.games.discus,
anchor.games.dance, anchor.games.seat; light.sun, light.sky; SkyDome, far.headland.

Axes: metres, +Z up, the reader at the origin facing +Y (north, towards the harbour).

Run headless (one Blender at a time, CPU):
  blender -b -P blender/build_phaeacian_games_ground.py -- --cpu --render --quick --res 900 --cams reader
  blender -b -P blender/build_phaeacian_games_ground.py -- --cpu --render --samples 40 --res 1280 --captures captures/blender/phaeacian-games-ground
  blender -b -P blender/build_phaeacian_games_ground.py -- --cpu --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
ARGS = K.setup("phaeacian-games-ground", "out/phaeacian-games-ground", 1186, "PhaeacianGames", default_samples=40)
import scene_kit_b2 as B
from scene_kit_b2 import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound,
                          light_obj, camera, smoothstep, lerp, n2, fbm2, link, card, tree, blob, set_card_normals, spray_atlas)
OUT = K.OUT; scene = K.scene
rng = random.Random(1186)
EYE_H = 1.55
SUN_DIR = Vector((0.55, -0.35, 0.76)).normalized()        # mid-morning sun in the south-east (behind the reader's right)
SHORE_Y = 25.0
SEA_Z = -1.2
DANCE = Vector((6.0, 7.0)); DANCE_R = 3.6
NEAR = 40.0

def H(x, y):
    h = 0.08 * fbm2(x, y, 12.0, 3, 0.9)
    h -= 1.0 * smoothstep(SHORE_Y - 3.0, SHORE_Y + 2.0, y)
    h += 0.5 * smoothstep(-6, -30, y) + 1.5 * smoothstep(-25, -40, y)
    h += 0.4 * smoothstep(18, 35, abs(x))
    return h
def gz(x, y): return H(x, y) - H(0, 0)
B.set_ground(gz, (0.0, 0.0, EYE_H))

print("painting atlases ...", flush=True)
IMG_GRASS = B.meadow_atlas("A_EdgeCards", greens=[(0.10, 0.15, 0.04), (0.14, 0.19, 0.05), (0.08, 0.12, 0.03), (0.18, 0.21, 0.07), (0.12, 0.16, 0.05)],
                           tips=[(0.32, 0.32, 0.14), (0.38, 0.36, 0.16), (0.28, 0.28, 0.12)], dry=0.35, seed=61)
M_GRASS = image_mat("M_EdgeCards", IMG_GRASS, rough=0.8, alpha=True, spec=0.2)
def ground_mat(name="M_Ground"):
    """the games ground: packed, sun-dried earth, scuffed and dusty along the race track, the dancing floor smoothed and
    paler, trampled edges going to dry grass; the beach below the sheds."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2200, 0)); s = sep_xyz(nt, co, (-2000, -600)); x = s.outputs["X"]; y = s.outputs["Y"]
    n1 = noise_(nt, co, 0.35, 5, 0.6, loc=(-1700, 300)); n2_ = noise_(nt, co, 4.0, 6, 0.65, loc=(-1700, 100))
    earth = ramp(nt, [(0.0, c4((0.09, 0.06, 0.035))), (0.4, c4((0.14, 0.10, 0.06))), (0.7, c4((0.19, 0.14, 0.09))), (1.0, c4((0.24, 0.19, 0.13)))], (-1300, 300))
    nt.links.new(math_(nt, 'ADD', math_(nt, 'MULTIPLY', n1.outputs["Fac"], 0.6, (-1500, 300)), math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.5, (-1500, 200)), (-1400, 250)), earth.inputs["Fac"])
    grass = ramp(nt, [(0.3, c4((0.12, 0.13, 0.05))), (0.7, c4((0.26, 0.24, 0.12)))], (-1300, -100)); nt.links.new(n2_.outputs["Fac"], grass.inputs["Fac"])
    edge = maprange(nt, math_(nt, 'ADD', math_(nt, 'ABSOLUTE', x, None, (-1500, -300)), math_(nt, 'MULTIPLY', n1.outputs["Fac"], 4.0, (-1500, -400)), (-1400, -350)), 15.0, 19.0, 0.0, 1.0, (-1200, -350))
    behind = maprange(nt, y, -5.0, -8.0, 0.0, 1.0, (-1200, -500))
    gmask = math_(nt, 'MAXIMUM', edge, behind, (-1000, -400))
    col = mix_rgb(nt, 'MIX', gmask, earth.outputs["Color"], grass.outputs["Color"], (-800, 200))
    dx = math_(nt, 'SUBTRACT', x, DANCE.x, (-1500, -700)); dy = math_(nt, 'SUBTRACT', y, DANCE.y, (-1500, -800))
    dr = math_(nt, 'SQRT', math_(nt, 'ADD', math_(nt, 'MULTIPLY', dx, dx, (-1350, -700)), math_(nt, 'MULTIPLY', dy, dy, (-1350, -800)), (-1250, -750)), None, (-1150, -750))
    floor_ = maprange(nt, dr, DANCE_R, DANCE_R - 0.15, 0.0, 1.0, (-1000, -750))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', floor_, 0.65, (-850, -750)), col, c4((0.26, 0.21, 0.15)), (-600, 200))
    track = maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', x, -4.0, (-1500, -1000)), None, (-1350, -1000)), 1.4, 0.8, 0.0, 0.35, (-1200, -1000))
    col = mix_rgb(nt, 'MIX', track, col, c4((0.24, 0.19, 0.13)), (-450, 200))
    sand = maprange(nt, y, SHORE_Y - 6.0, SHORE_Y - 4.0, 0.0, 1.0, (-1200, -1200))
    col = mix_rgb(nt, 'MIX', sand, col, c4((0.30, 0.26, 0.19)), (-300, 200))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.92
    bump_from(nt, b, n2_.outputs["Fac"], 0.7, 0.02, (0, -400))
    return m
M_GROUND = ground_mat()
M_POLISHED = noisy("M_PolishedStone", [(0.52, 0.49, 0.44), (0.62, 0.59, 0.53), (0.70, 0.67, 0.61)], scale=3, rough=(0.18, 0.3), bump=0.05, coat=0.4, warp=0.6)
M_ROUGHSTONE = noisy("M_RoughStone", [(0.13, 0.12, 0.10), (0.20, 0.19, 0.16), (0.27, 0.25, 0.21)], scale=4.0, rough=0.85, bump=0.8, bump_dist=0.01, warp=0.8, ao=0.5)
M_TIMBER = wood("M_ShedTimber", base=(0.24, 0.17, 0.10), dark=(0.10, 0.07, 0.04), light=(0.34, 0.25, 0.15), scale=0.8, rough=(0.6, 0.85))
M_THATCH = noisy("M_ShedRoof", [(0.30, 0.25, 0.16), (0.40, 0.34, 0.22), (0.24, 0.20, 0.13)], scale=8, rough=0.95, bump=0.6, stretch=(1, 1, 6))
M_HULL = noisy("M_BlackHull", [(0.02, 0.018, 0.016), (0.05, 0.045, 0.04), (0.08, 0.07, 0.06)], scale=4, rough=0.45, bump=0.3, stretch=(0.3, 1, 1))
M_PROW = noisy("M_PaintedProw", [(0.45, 0.10, 0.05), (0.55, 0.16, 0.07)], scale=6, rough=0.5, bump=0.1)
M_SPAR = wood("M_Spars", base=(0.30, 0.22, 0.13), dark=(0.14, 0.10, 0.06), light=(0.40, 0.31, 0.19), scale=2.0, rough=(0.5, 0.7))
M_SAIL = noisy("M_Sail", [(0.62, 0.58, 0.48), (0.70, 0.66, 0.56)], scale=6, rough=0.9, bump=0.3)
M_ROPE = noisy("M_Rope", [(0.20, 0.16, 0.10), (0.28, 0.23, 0.15)], scale=60, rough=0.9, stretch=(1, 1, 8), bump=0.4)
M_LYREWOOD = wood("M_LyreWood", base=(0.30, 0.18, 0.08), dark=(0.12, 0.06, 0.03), light=(0.42, 0.27, 0.13), scale=3.0, rough=(0.3, 0.5), coat=0.3)
M_SHELL = noisy("M_TortoiseShell", [(0.15, 0.08, 0.03), (0.35, 0.20, 0.06), (0.08, 0.05, 0.02)], scale=12, rough=0.3, coat=0.5, bump=0.1)
M_SILVER = plain("M_Silver", (0.75, 0.75, 0.73), rough=0.25, metallic=0.8)
M_PURPLE = noisy("M_PurpleCloth", [(0.22, 0.05, 0.10), (0.32, 0.08, 0.14)], scale=30, rough=0.9, sheen=0.4, bump=0.1)
M_FLAG = plain("M_Pennant", (0.50, 0.08, 0.05), rough=0.8)
def sea_mat(name="M_Harbour"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-1200, 0)); n = noise_(nt, co, 0.6, 4, 0.6, loc=(-900, 0))
    r = ramp(nt, [(0.0, c4((0.01, 0.06, 0.09))), (1.0, c4((0.03, 0.13, 0.16)))], (-600, 0)); nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.06
    fine = noise_(nt, co, 5.0, 4, 0.6, loc=(-900, -300)); bump_from(nt, b, fine.outputs["Fac"], 0.15, 0.05, (0, -300))
    return m
M_SEA = sea_mat()
M_FAR = noisy("M_FarHeadland", [(0.20, 0.22, 0.18), (0.28, 0.30, 0.24), (0.36, 0.38, 0.32)], scale=0.03, rough=0.95, bump=0.0)

# ----------------------------------------------------------------------------- terrain, sea, headlands
print("terrain ...", flush=True)
verts = []; uvs = []; XS = [-NEAR + i * 1.25 for i in range(int(2 * NEAR / 1.25) + 1)]; YS = [-NEAR * 0.75 + i * 1.0 for i in range(int(NEAR * 0.75 + SHORE_Y + 6) + 1)]
for yy in YS:
    for xx in XS: verts.append((xx, yy, gz(xx, yy))); uvs.append(((xx - XS[0]) / (XS[-1] - XS[0]), (yy - YS[0]) / (YS[-1] - YS[0])))
nx = len(XS) - 1
faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(len(YS) - 1) for i in range(nx)]
mesh_from("GroundNear", verts, faces, M_GROUND, smooth=True, uvs=uvs)
sv = []; sf = []; rs_ = [SHORE_Y - 2, SHORE_Y + 6, SHORE_Y + 16, SHORE_Y + 32, SHORE_Y + 60, SHORE_Y + 120, SHORE_Y + 260]
for yy in rs_:
    for i in range(33): sv.append((-320 + i * 20, yy, SEA_Z - H(0, 0)))
for j in range(len(rs_) - 1):
    for i in range(32): sf.append((j * 33 + i, j * 33 + i + 1, (j + 1) * 33 + i + 1, (j + 1) * 33 + i))
mesh_from("water.ocean.harbour", sv, sf, M_SEA, uvs=[((v[0] + 320) / 640, (v[1]) / 300) for v in sv])
for k, (x0, x1, h0) in enumerate(((-420, -70, 22), (110, 420, 16))):          # the headlands enclosing the harbour
    vs = []; fs = []
    for i in range(25):
        x = x0 + (x1 - x0) * i / 24; t = i / 24
        h = h0 * (math.sin(t * math.pi) ** 0.6) * (0.7 + 0.3 * noise.noise(Vector((x * 0.02, k, 0))))
        vs.append((x, 120 + 60 * abs(t - (0.0 if k else 1.0)), SEA_Z - 1)); vs.append((x, 160 + 40 * abs(t - (0.0 if k else 1.0)), h))
    for i in range(24): fs.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    mesh_from(f"FarHeadland{k}", vs, fs, M_FAR, smooth=True)

# ----------------------------------------------------------------------------- the seats of polished stone (beside and behind the reader)
print("seats ...", flush=True)
for k in range(7):
    x = -6.0 + k * 1.25; y = -1.2 - 0.04 * (x ** 2) * 0.05
    yaw = math.radians(4 * (k - 3))
    box(f"SeatSlab{k}", (1.2, 0.55, 0.12), (x, y, gz(x, y) + 0.44), M_POLISHED, rot=(0, 0, yaw), bevel=0.03)
    box(f"SeatBase{k}", (1.0, 0.42, 0.38), (x, y, gz(x, y) + 0.19), M_ROUGHSTONE, rot=(0, 0, yaw), bevel=0.02)
    box(f"SeatBack{k}", (1.2, 0.18, 0.5), (x, y - 0.33, gz(x, y) + 0.72), M_POLISHED, rot=(-0.12, 0, yaw), bevel=0.03)
box("SeatStep", (9.2, 0.6, 0.12), (-2.3, -0.65, gz(-2.3, -0.65) + 0.04), M_ROUGHSTONE, bevel=0.02)
for k in range(2):        # the king's seat at the end, a fleece and a purple cloth over it
    box(f"KingCloth{k}", (1.0, 0.5 if k == 0 else 0.06, 0.04 if k == 0 else 0.45), (-0.95, -1.2 if k == 0 else -1.5, gz(-0.95, -1.2) + (0.52 if k == 0 else 0.75)), M_PURPLE, bevel=0.015)

# ----------------------------------------------------------------------------- the games: starting post, marks, the discus far beyond; the dancing floor
cyl("StartPost", 0.09, 1.3, (-4.0, 2.2, gz(-4.0, 2.2) + 0.6), M_TIMBER, verts=10)
cyl("TurnPost", 0.09, 1.3, (-4.0, 15.5, gz(-4.0, 15.5) + 0.6), M_TIMBER, verts=10)
for k, (x, y) in enumerate(((1.0, 11.0), (1.4, 12.2), (0.6, 12.9))):
    cyl(f"Mark{k}", 0.025, 0.45, (x, y, gz(x, y) + 0.15), M_TIMBER, verts=6, rot=(0.15 * k, 0.1, 0))
    box(f"MarkScore{k}", (0.6, 0.03, 0.01), (x, y, gz(x, y) + 0.005), plain("M_Score", (0.18, 0.12, 0.07), rough=0.9))
DISCUS = Vector((2.4, 17.6))
o = lathe("Discus", [(0.0, -0.035), (0.13, -0.015), (0.15, 0.0), (0.13, 0.015), (0.0, 0.035)], (DISCUS.x, DISCUS.y, gz(DISCUS.x, DISCUS.y) + 0.06), M_ROUGHSTONE, steps=20)
o.rotation_euler = (0.35, 0.1, 0.5)
for k in range(5):
    box(f"DiscusScuff{k}", (0.25, 0.6, 0.008), (DISCUS.x - 0.1 * k, DISCUS.y - 0.6 - k * 0.5, gz(DISCUS.x, DISCUS.y - 1) + 0.003), plain("M_Scuff", (0.20, 0.14, 0.08), rough=0.95), rot=(0, 0, 0.2))
# Demodocus's chair (silver-studded) at the dancing floor's edge, his lyre on a peg on a post above it
DC = DANCE + Vector((-DANCE_R - 0.4, 0.3))
F = K.Frame((DC.x, DC.y), math.radians(-90), z=gz(DC.x, DC.y))
F.box("BardSeat", (0.55, 0.5, 0.05), (0, 0, 0.46), M_TIMBER, bevel=0.01)
for sx in (-1, 1):
    for sy in (-1, 1): F.cyl(f"BardLeg{sx}{sy}", 0.025, 0.44, (sx * 0.22, sy * 0.2, 0.22), M_TIMBER, verts=8)
    F.box(f"BardBackPost{sx}", (0.04, 0.04, 0.6), (sx * 0.24, -0.23, 0.76), M_TIMBER)
F.box("BardBackRail", (0.52, 0.04, 0.1), (0, -0.23, 1.02), M_TIMBER)
for k in range(6): sphere(f"BardStud{k}", 0.012, F.p(-0.2 + k * 0.08, 0.255, 0.46), M_SILVER, seg=6)
F.box("BardCloth", (0.6, 0.55, 0.03), (0, 0.02, 0.5), M_PURPLE, bevel=0.012)
post = Vector(F.p(0.0, -0.5, 0.0)); cyl("LyrePost", 0.07, 2.4, (post.x, post.y, post.z + 1.2), M_TIMBER, verts=10)
cyl("LyrePeg", 0.015, 0.16, tuple(Vector(F.p(0.0, -0.42, 2.05))), M_TIMBER, verts=6, rot=(math.pi / 2, 0, math.radians(-90)))
ly = Vector(F.p(0.0, -0.36, 1.78))
sphere("LyreShell", 0.14, (ly.x, ly.y, ly.z - 0.12), M_SHELL, seg=12, scale=(0.4, 1.0, 1.0)).rotation_euler = (0, 0, math.radians(-90))
for s in (-1, 1): cyl(f"LyreArm{s}", 0.012, 0.36, tuple(Vector(F.p(s * 0.09, -0.36, 1.92))), M_LYREWOOD, verts=6, rot=(0, math.radians(14 * s), math.radians(-90)))
cyl("LyreYoke", 0.012, 0.3, tuple(Vector(F.p(0.0, -0.36, 2.1))), M_LYREWOOD, verts=6, rot=(0, math.pi / 2, math.radians(-90)))
for k in range(7): box(f"LyreString{k}", (0.002, 0.002, 0.34), tuple(Vector(F.p(-0.06 + k * 0.02, -0.33, 1.9))), plain("M_Gut", (0.6, 0.55, 0.42), rough=0.5))
# a ring of low stones round the dancing floor
for k in range(28):
    a = 2 * math.pi * k / 28; p = DANCE + Vector((math.cos(a), math.sin(a))) * (DANCE_R + 0.15)
    if abs(a - math.pi) < 0.25: continue
    box(f"RingStone{k}", (0.3, 0.2, 0.12), (p.x, p.y, gz(p.x, p.y) + 0.03), M_ROUGHSTONE, rot=(0, 0, a + math.pi / 2), bevel=0.03)

# ----------------------------------------------------------------------------- the ship sheds with black ships drawn up; ships afloat; masts and furled sails
print("ships ...", flush=True)
def hull(name, c, L, Bm, D, yaw, z0):
    nsec, st = 12, 9; rows = []
    for i in range(nsec):
        u = i / (nsec - 1) * 2 - 1; ends = abs(u)
        half = Bm / 2 * (1 - ends ** 2.2) ** 0.75 + 0.03
        sheer = D * (1 + 0.35 * ends ** 2.5)
        rows.append([Vector((u * L / 2, -math.cos(math.pi * k / (st - 1)) * half, sheer - math.sin(math.pi * k / (st - 1)) ** 0.7 * D * (1 - 0.3 * ends ** 2))) for k in range(st)])
    R_ = Matrix.Rotation(yaw, 3, 'Z'); base = Vector((c.x, c.y, z0))
    vs = [base + R_ @ p for r in rows for p in r]
    fs = [(i * st + k, i * st + k + 1, (i + 1) * st + k + 1, (i + 1) * st + k) for i in range(nsec - 1) for k in range(st - 1)]
    mesh_from(name, vs, fs, M_HULL, smooth=True)
    for s in (-1, 1):   # the curved stem and stern posts, painted
        tip = base + R_ @ Vector((s * L / 2, 0, D * 1.35)); top = base + R_ @ Vector((s * (L / 2 + 0.6), 0, D * 2.1))
        tube(f"{name}_Post{s}", [base + R_ @ Vector((s * L / 2 * 0.95, 0, 0.1)), tip, top], [0.12, 0.1, 0.06], M_PROW, sides=6)
    return base, R_
SHIPS = []
for k in range(4):        # in the sheds, on rollers, bows to the sea
    x = -18 + k * 9.0
    SHIPS.append(hull(f"ShedShip{k}", Vector((x, SHORE_Y - 3.5)), 14.0, 2.8, 1.1, math.pi / 2, gz(x, SHORE_Y - 3.5) + 0.35))
    for s in (-1, 1):
        for j in range(4): cyl(f"Shed{k}Post{s}{j}", 0.12, 4.0, (x + s * 2.3, SHORE_Y - 10 + j * 4.2, gz(x, SHORE_Y - 10 + j * 4.2) + 2.0), M_TIMBER, verts=8)
    rv = [(x - 2.6, SHORE_Y - 10.5, 4.0), (x + 2.6, SHORE_Y - 10.5, 4.0), (x + 2.6, SHORE_Y + 2.5, 3.6), (x - 2.6, SHORE_Y + 2.5, 3.6), (x, SHORE_Y - 10.5, 5.6), (x, SHORE_Y + 2.5, 5.2)]
    mesh_from(f"ShedRoof{k}", [(a, b, gz(x, b) + c) for (a, b, c) in rv], [(0, 4, 5, 3), (4, 1, 2, 5)], M_THATCH)
    for j in range(5): cyl(f"Roller{k}{j}", 0.1, 2.4, (x, SHORE_Y - 9 + j * 2.6, gz(x, SHORE_Y - 9 + j * 2.6) + 0.1), M_TIMBER, verts=8, rot=(0, math.pi / 2, 0))
for k, (x, y, yaw) in enumerate(((16.0, SHORE_Y + 12.0, 0.3), (28.0, SHORE_Y + 20.0, -0.2), (6.0, SHORE_Y + 28.0, 0.1))):
    SHIPS.append(hull(f"Afloat{k}", Vector((x, y)), 16.0, 3.0, 1.2, yaw, SEA_Z - H(0, 0) - 0.5))
SAILS = MB(); RIG = MB()
for k, (base, R_) in enumerate(SHIPS):
    mh = 9.0 if k >= 4 else 0.0
    if k < 4:            # masts lowered in the sheds: lying along the ship on crutches
        tube(f"MastDown{k}", [base + R_ @ Vector((-6, 0, 2.2)), base + R_ @ Vector((5, 0, 2.2))], 0.11, M_SPAR, sides=8)
        continue
    m0 = base + R_ @ Vector((0.0, 0, 0.8)); m1 = m0 + Vector((0, 0, mh))
    tube(f"Mast{k}", [m0, m1], [0.14, 0.08], M_SPAR, sides=8)
    y0 = m1 - Vector((0, 0, 0.8)); yd = R_ @ Vector((0, 1, 0))
    tube(f"Yard{k}", [y0 - yd * 4.5, y0 + yd * 4.5], 0.07, M_SPAR, sides=6)
    # the sail furled along the yard (a lumpy roll, cloth.sail)
    for j in range(12):
        t = j / 11 - 0.5; c = y0 + yd * t * 8.0 - Vector((0, 0, 0.18))
        B.blob(SAILS, c, (0.22, 0.42, 0.2), 700 + k * 20 + j, sub=1, rough=0.2)
    for s in (-1, 1):
        for p in (base + R_ @ Vector((7.0 * s, 0, 1.4)), base + R_ @ Vector((0, 1.5 * s, 1.0))):
            d = m1 - p; n_ = d.cross(Vector((0, 0, 1))).normalized() * 0.02
            a = RIG.vert(p - n_); b_ = RIG.vert(p + n_); c_ = RIG.vert(m1 + n_); e_ = RIG.vert(m1 - n_); RIG.face(a, b_, c_, e_)
    for j in range(10):         # oars shipped along the gunwale
        tube(f"Oar{k}{j}", [base + R_ @ Vector((-5 + j * 1.1, 1.6, 1.25)), base + R_ @ Vector((-5 + j * 1.1 + 0.3, 3.4, 0.2))], 0.03, M_SPAR, sides=4, caps=False)
so = SAILS.build("cloth.sail.furled", M_SAIL)
K.add_sway(so, lambda p: 0.15)
RIG.build("Rigging", M_ROPE, sway=False)
pn = MB()
base, R_ = SHIPS[4]; top_ = base + R_ @ Vector((0, 0, 9.8))
for i in range(7):
    t = i / 6
    a = pn.vert(top_ + R_ @ Vector((t * 2.5, 0, 0)) - Vector((0, 0, 0.0)), (t, 0), t); b_ = pn.vert(top_ + R_ @ Vector((t * 2.5, 0, 0)) - Vector((0, 0, 0.4 * (1 - t) + 0.02)), (t, 1), t)
    if i: pn.face(pa, pb, b_, a)
    pa, pb = a, b_
pn.build("cloth.flag.pennant", M_FLAG)

# grass along the edges of the ground and round the seats
def grass_ok(x, y):
    e = smoothstep(13.0, 17.0, abs(x)) + smoothstep(-3.5, -6.0, y)
    if (Vector((x, y)) - DANCE).length < DANCE_R + 0.5: return 0.0
    if y > SHORE_Y - 6: return 0.0
    if -7 < x < 1 and -1.8 < y < -0.3: return 0.0
    return min(1.0, 0.012 + e)
mb = MB(); R = random.Random(5)
B.scatter_cards(mb, None, R, 30000, 0.8, 16.0, grass_ok, B.MEADOW_SHORT + B.MEADOW_LONG[:2], height=0.22, width=0.4, solid_from=99, maxcards=800)
go = mb.build("EdgeCards", M_GRASS); set_card_normals(go, lambda p: Vector((0, 0, 1)))
# stones and pebbles kicked about the ground, thicker towards the edges and the beach
PB = MB(); rp = random.Random(77)
for i in range(700):
    x = rp.uniform(-16, 16); y = rp.uniform(-4, SHORE_Y - 4)
    if (Vector((x, y)) - DANCE).length < DANCE_R + 0.2 or (-7 < x < 1 and -1.8 < y < -0.2): continue
    if rp.random() > 0.25 + 0.6 * smoothstep(10, 16, abs(x)) + 0.4 * smoothstep(SHORE_Y - 10, SHORE_Y - 5, y): continue
    r_ = rp.uniform(0.025, 0.09) * (2.2 if rp.random() < 0.05 else 1.0)
    B.blob(PB, (x, y, gz(x, y) + r_ * 0.1), (r_, r_ * rp.uniform(0.7, 1.0), r_ * rp.uniform(0.4, 0.7)), 3000 + i, sub=1, rough=0.2)
PB.build("Stones", M_ROUGHSTONE, sway=False)

# ----------------------------------------------------------------------------- sky, light, anchors
SKY = B.clear_sky_mat("M_SkyDome", SUN_DIR, zenith=(0.08, 0.24, 0.62), horizon=(0.62, 0.74, 0.86), cloud=0.25, strength=1.0)
B.sky_dome("SkyDome", SKY, 450.0)
light_obj("light.sun", 'SUN', 4.6, (1.0, 0.95, 0.86), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(1.2))
sl = light_obj("light.sky", 'SUN', 0.5, (0.65, 0.78, 1.0), (0, 0, 40), direction=(0.1, 0.1, -1.0), angle=math.radians(90)); sl.data.use_shadow = False
B.world_sky(zen=(0.14, 0.30, 0.70), hor=(0.62, 0.74, 0.86), ground=(0.20, 0.16, 0.10), strength=1.0)
vol = scene.world.node_tree.nodes.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.0012; vol.inputs["Color"].default_value = (0.85, 0.78, 0.66, 1)
pass   # no world volume: an infinite haze in Cycles swallows the sun (Unity has its own fog)
E = Vector((0.0, 0.0, gz(0, 0) + EYE_H)); fwd = Vector((0.12, 1.0, 0)).normalized()
B.reader_anchors((0.0, 0.0, gz(0, 0)), tuple(E + fwd))
anchor("scene.centre", (1.0, 9.0, gz(1, 9))); anchor("games.discus", (DISCUS.x, DISCUS.y, gz(DISCUS.x, DISCUS.y)))
anchor("games.dance", (DANCE.x, DANCE.y, gz(DANCE.x, DANCE.y))); anchor("games.seat", (-0.95, -1.2, gz(-0.95, -1.2)))
sound("crowd", "assembly", (-2.0, 4.0, 1.5)); sound("gulls", "harbour", (5.0, SHORE_Y + 8.0, 10.0))
sound("rigging", "ships", (16.0, SHORE_Y + 12.0, 5.0)); sound("wind", "ground", (8.0, 10.0, 2.0))
page = B.page_preview(E, fwd)
K.apply_transforms()
cams = B.view_cams(E, fwd, extra=[("Cam_Dance", E + Vector((1.0, 1.0, 0.0)), (DC.x, DC.y, gz(DC.x, DC.y) + 1.2), 26),
                                  ("Cam_Ships", tuple(E), (0.0, SHORE_Y, 2.0), 30), ("Cam_Seats", E + Vector((3.0, 3.0, 0.2)), (-3.0, -1.2, 0.5), 22)])
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "phaeacian_games_ground_source.blend"))
K.print_budget()
if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=-0.2, captures_dir=ARGS.captures)
if ARGS.bake or ARGS.export:
    scene.world.node_tree.nodes.remove(vol)
    B.export_room("phaeacian_games_ground.gltf", cams, page=page,
                  keep_names={"M_EdgeCards": "veg.grass.edges", "M_Harbour": "water.ocean.harbour", "M_Sail": "cloth.sail.furled", "M_Pennant": "cloth.flag.pennant",
                              "M_SkyDome": "SkyDome", "M_FarHeadland": "far.headland", "M_Ground": "GroundNear"},
                  keep_uv={"M_Ground", "M_SkyDome", "M_Harbour"},
                  size_for={"M_Ground": (2048, 256, 1024), "M_SkyDome": (2048,), "M_Harbour": (512, 64, 256), "M_PolishedStone": (1024, 256, 512),
                            "M_RoughStone": (512, 128, 512), "M_ShedTimber": (1024, 128, 512), "M_ShedRoof": (512, 64, 512), "M_BlackHull": (1024, 128, 512),
                            "M_Spars": (256, 64, 128), "M_FarHeadland": (256, 32, 64)},
                  default_size=(128, 64, 128))
print("DONE")
