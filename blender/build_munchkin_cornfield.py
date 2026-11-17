"""
Fable step-in room: the Munchkin cornfield and the Scarecrow (The Wonderful Wizard of Oz, chapter 3).

"... she saw, not far away, a Scarecrow, placed high on a pole to keep the birds from the ripe corn. Dorothy leaned her
chin upon her hand and gazed thoughtfully at the Scarecrow. Its head was a small sack stuffed with straw, with eyes,
nose, and mouth painted on it to represent a face. An old, pointed blue hat, that had belonged to some Munchkin, was
perched on his head, and the rest of the figure was a blue suit of clothes, worn and faded, which had also been stuffed
with straw. On the feet were some old boots with blue tops ..."

The yellow brick road runs east-west across Munchkin farmland on a bright morning. Neat fences painted a dainty blue line
both sides; through an open field gate in the north fence a trodden path leads a few metres into the ripe corn, taller
than a child, to the Scarecrow on his pole in a small trampled clearing. South of the road: a vegetable plot and fields
of grain; round blue Munchkin houses with big domed roofs stand among the fields in the distance. No people, no Toto.

Reader: on the road by the gate (where Dorothy sat on the fence), facing north to the Scarecrow.

Living-scene nodes: veg.crop.corn (modelled near plants), veg.crop.cornCards (painted plant cards behind),
veg.grass.verge, sound.birds.corn, sound.wind.field. Outdoor; a light breeze from the south-west.

  blender -b -P blender/build_munchkin_cornfield.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_munchkin_cornfield.py -- --render --samples 48 --res 1400
  blender -b -P blender/build_munchkin_cornfield.py -- --export
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b5 as S
import pride_kit as K
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, MB, Canvas, anchor, sound, light_obj)

SID = "munchkin-cornfield"
ARGS = S.setup(SID, seed=1900)
scene = K.scene
rng = random.Random(1900)

ROAD_W = 3.2              # yellow brick road along X, centred on y = 0
FENCE_Y = 2.05            # the fences, both sides
FIELD_Y0 = 2.5            # the corn starts here
GATE = (-0.55, 0.85)      # x span of the open gate in the north fence
SCARE = Vector((0.35, 5.6, 0))
CLEAR_R = 1.7             # trampled clearing round the pole
READER = Vector((0.15, 0.55, 0))


def H(x, y):
    """flat near the road; long gentle swells further out"""
    r = math.hypot(x, y)
    k = K.smoothstep(25.0, 120.0, r)
    return k * (2.2 * noise.noise(Vector((x / 160.0, y / 160.0, 0.3))) + 0.6 * noise.noise(Vector((x / 45.0, y / 45.0, 1.7)))) - 0.012 * (abs(y) > ROAD_W / 2) * (1 - k)


def path_d(x, y):
    """distance to the trodden path from the gate to the pole"""
    a = Vector((0.15, FENCE_Y)); b = Vector((SCARE.x, SCARE.y)); p = Vector((x, y))
    t = max(0.0, min(1.0, (p - a).dot(b - a) / (b - a).length_squared))
    return (p - (a + (b - a) * t)).length


def in_corn(x, y):
    if y < FIELD_Y0: return False
    if path_d(x, y) < 0.42: return False
    if (Vector((x, y)) - SCARE.xy).length < CLEAR_R: return False
    return True


# ----------------------------------------------------------------------------- painted atlases
def brick_atlas(S_=1024, tile=2.4):
    """Yellow glazed bricks laid in running bond across the road (stretchers 0.24 x 0.115 m), a tileable 2.4 m square:
    each brick its own shade of yellow, worn paler and matt in the middle, chipped arrises, dark sandy joints."""
    a = np.zeros((S_, S_, 4), np.float32); a[..., 3] = 1
    yy, xx = np.mgrid[0:S_, 0:S_].astype(np.float32) / S_ * tile
    bw, bh, j = 0.24, 0.12, 0.008
    row = np.floor(yy / bh); off = (row % 2) * bw / 2
    col = np.floor((xx + off) / bw)
    fx = (xx + off) / bw - col; fy = yy / bh - row
    ex = np.minimum(fx, 1 - fx) * bw; ey = np.minimum(fy, 1 - fy) * bh
    edge = np.minimum(ex, ey)
    r = np.random.RandomState(7)
    ids = (row * 97 + col * 13).astype(np.int64) % 4096
    tone = r.uniform(0.0, 1.0, 4096)[ids]; tone2 = r.uniform(0.0, 1.0, 4096)[ids]
    base = np.stack([0.86 + 0.08 * tone, 0.66 + 0.10 * tone, 0.20 + 0.12 * tone2], -1)
    base = np.where((tone2 > 0.9)[..., None], base * np.array([0.92, 0.82, 0.7]), base)      # a few burnt-orange ones
    # fine speckle and a duller worn centre
    sp = r.uniform(0.92, 1.05, (S_, S_))
    centre = np.clip(1 - np.minimum(ex / (bw / 2), ey / (bh / 2)), 0, 1)
    base = base * sp[..., None] * (0.92 + 0.08 * centre[..., None])
    # chipped arrises: darker within ~6 mm of the joint, irregular
    chip = np.clip((edge - j * 0.5) / 0.008, 0, 1)
    jn = r.uniform(0, 1, (S_ // 8, S_ // 8)).repeat(8, 0).repeat(8, 1)
    joint = edge < (j * (0.7 + 0.6 * jn))
    base = base * (0.72 + 0.28 * chip[..., None])
    mortar = np.stack([0.30 + 0.06 * jn, 0.26 + 0.05 * jn, 0.17 + 0.04 * jn], -1)
    a[..., :3] = np.where(joint[..., None], mortar, base)
    a[..., :3] = np.clip(a[..., :3], 0, 1) ** 2.2     # paint in sRGB, store linear-ish for the sRGB image
    return K.np_image("A_YellowBricks", np.clip(a[..., :3] ** (1 / 2.2), 0, 1).reshape(S_, S_, 3).__array__().copy() if False else
                      np.concatenate([np.clip(a[..., :3] ** (1 / 2.2), 0, 1), np.ones((S_, S_, 1), np.float32)], -1))


def corn_atlas(S_=1024):
    """Four ripe corn plants side by side (each a 256 x 1024 cell, 2.4 m tall): a jointed stalk, long arching leaves
    yellowing at the tips and the lower ones dry, one or two husked ears, a pale tassel."""
    cv = Canvas(S_, S_)
    r = random.Random(11)
    for k in range(4):
        x0 = k * 256 + 128; ground = S_ - 4; top = 40 + r.randint(0, 60)
        H_ = ground - top
        stalk_g = (0.42, 0.50, 0.22, 1)
        cv.clip = (k * 256, 0, k * 256 + 256, S_)
        sway = r.uniform(-14, 14)
        def sx(t): return x0 + sway * t * t
        for i in range(12):
            t0, t1 = i / 12, (i + 1) / 12
            cv.line((sx(t0), ground - H_ * t0), (sx(t1), ground - H_ * t1), 7.5 - 4.5 * t0, 7.5 - 4.5 * t1, stalk_g)
        # nodes
        for i in range(1, 9):
            t = i / 10; cv.ellipse(sx(t), ground - H_ * t, 6, 2.2, 0, (0.55, 0.55, 0.28, 1))
        # leaves: alternate sides, arching out and down
        nleaf = 11
        for i in range(nleaf):
            t = 0.12 + 0.72 * i / nleaf + r.uniform(-0.02, 0.02)
            side = 1 if i % 2 else -1
            L = (0.36 + 0.3 * math.sin(math.pi * min(1, t * 1.2))) * 260 * r.uniform(0.85, 1.1)
            dry = t < 0.3 and r.random() < 0.7
            px, py = sx(t), ground - H_ * t
            ang = math.radians(r.uniform(35, 60)); droop = r.uniform(0.8, 1.6)
            pts = []
            for s in range(13):
                u = s / 12
                a_ = ang - droop * u * u
                pts.append((px + side * L * u * math.sin(math.pi / 2 - 0) * math.cos(a_) * 0.95 * 0.45,
                            py - L * 0.45 * math.sin(a_) * u + (L * 0.08 * u * u)))
            for s in range(12):
                u0, u1 = s / 12, (s + 1) / 12
                w0 = 9.0 * math.sin(math.pi * min(1.0, 0.15 + u0 * 0.9)) * (0.6 if dry else 1.0)
                w1 = 9.0 * math.sin(math.pi * min(1.0, 0.15 + u1 * 0.9)) * (0.6 if dry else 1.0)
                if dry: c = (0.62, 0.52, 0.30, 1)
                else:
                    y_ = max(0.0, u0 - 0.65) / 0.35
                    c = (0.31 + 0.32 * y_ + 0.05 * (i % 3), 0.43 + 0.1 * y_ - 0.02 * (i % 2), 0.14 + 0.08 * y_, 1)
                cv.line(pts[s], pts[s + 1], max(0.8, w0 * 0.5), max(0.8, w1 * 0.5), c)
            for s in range(10):    # midrib
                cv.line(pts[s], pts[s + 1], 0.7, 0.5, (0.62, 0.66, 0.38, 1))
        # ears in husks (one or two), with silks
        for e in range(r.choice((1, 2))):
            t = 0.42 + 0.1 * e; side = -1 if e else 1
            px, py = sx(t), ground - H_ * t
            cx, cy = px + side * 12, py - 34
            cv.ellipse(cx, cy, 34, 9, math.radians(-90 + side * 18), (0.50, 0.55, 0.27, 1), tip=0.5)
            cv.ellipse(cx + side * 2, cy - 2, 28, 6, math.radians(-90 + side * 18), (0.62, 0.62, 0.34, 1), tip=0.6)
            for s in range(5):
                cv.line((cx + side * 6, cy - 30), (cx + side * (10 + 4 * s), cy - 44 - 2 * s), 1.0, 0.6, (0.52, 0.30, 0.12, 1))
        # tassel
        tx, ty = sx(1.0), top
        for s in range(9):
            a_ = math.radians(-90 + r.uniform(-60, 60)); L = r.uniform(30, 55)
            cv.line((tx, ty + 6), (tx + math.cos(a_) * L * 0.5, ty + 6 + abs(math.sin(a_)) * L * 0.2 - L * 0.5 * (s % 2)), 1.6, 0.8, (0.80, 0.70, 0.42, 1))
        cv.line((tx, ty + 30), (tx, ty - 10), 2.2, 1.2, (0.75, 0.68, 0.40, 1))
    cv.clip = None
    cv.bleed(6)
    return K.np_image("A_CornPlants", cv.a)


def leaf_strip_atlas(W=128, Hh=1024):
    """A strip texture for modelled corn leaves and stalks (u across, v along the leaf): green blade with fine parallel
    veins and a pale midrib, yellowing and drying toward the tip (v = 1); the stalk uses the left quarter's base."""
    a = np.zeros((Hh, W, 4), np.float32); a[..., 3] = 1
    yy, xx = np.mgrid[0:Hh, 0:W].astype(np.float32)
    v = 1 - yy / Hh; u = xx / W
    g = np.stack([0.30 + 0.0 * u, 0.42 + 0.0 * u, 0.13 + 0.0 * u], -1)
    yel = np.clip((v - 0.5) / 0.5, 0, 1) ** 1.3
    g = g * (1 - yel[..., None]) + np.array([0.62, 0.55, 0.30]) * yel[..., None]
    veins = 0.93 + 0.07 * np.sin(u * W * 0.9) ** 2
    mid = np.exp(-((u - 0.5) / 0.035) ** 2)
    g = g * veins[..., None]
    g = g * (1 - 0.6 * mid[..., None]) + np.array([0.60, 0.66, 0.40]) * 0.6 * mid[..., None]
    a[..., :3] = np.clip(g, 0, 1)
    return K.np_image("A_CornLeaf", a)


A_BRICK = brick_atlas()
A_CORN = corn_atlas()
A_LEAF = leaf_strip_atlas()
M_ROAD = K.image_mat("M_YellowBrick", A_BRICK, rough=0.45, spec=0.5)
M_CORNCARD = K.image_mat("M_CornCards", A_CORN, rough=0.6, alpha=True)
M_CORN = K.image_mat("M_CornLeaf", A_LEAF, rough=0.55)


# ----------------------------------------------------------------------------- materials
def ground_mat(name="M_Ground"):
    """Farmland seen from the road: short sward on the verges, bare trodden earth and stubble under the corn, the
    vegetable plot's dark soil rows south of the road, wheat stubble gold beyond; all varied by noise at several scales."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1900, 0)); x, y = s.outputs["X"], s.outputs["Y"]
    n1 = noise_(nt, co, 0.6, 5, 0.6, loc=(-1500, 400)); n2 = noise_(nt, co, 6.0, 5, 0.6, loc=(-1500, 200)); n3 = noise_(nt, co, 40.0, 3, 0.6, loc=(-1500, 0))
    grass = mix_rgb(nt, 'MIX', maprange(nt, n2.outputs["Fac"], 0.3, 0.7, 0, 1, (-1300, 300)), (0.09, 0.15, 0.04, 1), (0.20, 0.26, 0.08, 1), (-1100, 300))
    grass = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.45, 0.7, 0, 0.6, (-1300, 500)), grass, (0.30, 0.28, 0.12, 1), (-950, 300))
    soil = mix_rgb(nt, 'MIX', maprange(nt, n3.outputs["Fac"], 0.3, 0.7, 0, 1, (-1300, 0)), (0.12, 0.08, 0.05, 1), (0.22, 0.16, 0.10, 1), (-1100, 0))
    litter = mix_rgb(nt, 'MIX', maprange(nt, n2.outputs["Fac"], 0.4, 0.65, 0, 0.7, (-1300, -150)), soil, (0.40, 0.33, 0.20, 1), (-950, 0))
    # under the corn (y > field start): earth with dry leaf litter; the verge strip next to the fences stays grassy
    corn = maprange(nt, y, FIELD_Y0 - 0.3, FIELD_Y0 + 0.4, 0, 1, (-1300, -400))
    col = mix_rgb(nt, 'MIX', corn, grass, litter, (-800, 200))
    # south: vegetable rows (dark soil and green lines along X) from y -4 to -30, then gold wheat stubble
    south = maprange(nt, y, -3.2, -4.2, 0, 1, (-1300, -700))
    rows = math_(nt, 'SINE', math_(nt, 'MULTIPLY', y, 9.0, (-1300, -850)), None, (-1200, -850))
    rowm = maprange(nt, rows, 0.1, 0.6, 0, 1, (-1050, -850))
    veg = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', rowm, maprange(nt, n1.outputs['Fac'], 0.3, 0.7, 0.3, 0.8, (-1150, -950)), (-1000, -900)), (0.12, 0.09, 0.055, 1), (0.14, 0.22, 0.07, 1), (-900, -850))
    wheat = mix_rgb(nt, 'MIX', maprange(nt, n2.outputs["Fac"], 0.3, 0.7, 0, 1, (-1050, -1050)), (0.55, 0.42, 0.18, 1), (0.70, 0.56, 0.26, 1), (-900, -1050))
    farm = mix_rgb(nt, 'MIX', maprange(nt, y, -11, -14, 0, 1, (-1050, -1200)), veg, wheat, (-750, -950))
    col = mix_rgb(nt, 'MIX', south, col, farm, (-600, 200))
    # far patchwork: fields of grain and vegetables tinted by large noise
    far = maprange(nt, math_(nt, 'ADD', math_(nt, 'ABSOLUTE', x, None, (-1300, -1400)), math_(nt, 'ABSOLUTE', y, None, (-1300, -1500)), (-1200, -1450)), 60, 90, 0, 1, (-1050, -1450))
    pv = voronoi_(nt, co, 0.012, 'F1', (-1300, -1650))
    pc = ramp(nt, [(0.0, (0.55, 0.43, 0.18, 1)), (0.3, (0.16, 0.24, 0.07, 1)), (0.55, (0.62, 0.52, 0.24, 1)), (0.8, (0.22, 0.30, 0.10, 1)), (1.0, (0.45, 0.40, 0.16, 1))], (-1050, -1650))
    nt.links.new(pv.outputs["Color"], pc.inputs["Fac"]) if "Color" in pv.outputs else None
    col = mix_rgb(nt, 'MIX', far, col, pc.outputs["Color"], (-450, 200))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, n3.outputs["Fac"], 0.3, 0.7, 0.85, 1.1, (-600, -300)), (-300, 200))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    bump_from(nt, b, n3.outputs["Fac"], 0.3, 0.01)
    return m


def grass_mat(name="M_VergeGrass"):
    m, nt, b = new_mat(name)
    a = node(nt, "ShaderNodeAttribute", (-1000, 0)); a.attribute_name = "sway"
    sp = node(nt, "ShaderNodeSeparateColor", (-800, 0)); nt.links.new(a.outputs["Color"], sp.inputs[0])
    c = mix_rgb(nt, 'MIX', sp.outputs["Green"], (0.12, 0.20, 0.05, 1), (0.30, 0.36, 0.12, 1), (-600, 0))
    c = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', maprange(nt, sp.outputs["Blue"], 0.7, 1.0, 0, 1, (-800, -200)), 0.8, (-650, -200)), c, (0.52, 0.46, 0.24, 1), (-450, 0))
    c = mix_rgb(nt, 'MULTIPLY', 1.0, c, maprange(nt, sp.outputs["Red"], 0, 1, 0.55, 1.1, (-650, -350)), (-300, 0))
    nt.links.new(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.6
    return m


def sky_and_hills():
    pass


M_GROUND = ground_mat()
M_GRASS = grass_mat()
M_BLUEPAINT = noisy("M_BluePaint", [K.srgb((0.36, 0.52, 0.74)), K.srgb((0.44, 0.60, 0.80)), K.srgb((0.30, 0.44, 0.64))], scale=6, rough=(0.5, 0.75), bump=0.25, bump_dist=0.002)
M_HOUSE = noisy("M_HouseBlue", [K.srgb((0.40, 0.56, 0.78)), K.srgb((0.48, 0.63, 0.82))], scale=0.8, rough=0.8, bump=0.1)
M_DOME = noisy("M_DomeBlue", [K.srgb((0.20, 0.32, 0.58)), K.srgb((0.26, 0.40, 0.66))], scale=1.2, rough=0.6, bump=0.1)
M_WOOD = wood("M_PoleWood", base=(0.28, 0.22, 0.15), dark=(0.12, 0.09, 0.06), light=(0.40, 0.33, 0.24), scale=1.0, rough=(0.7, 0.9), grain_dir=(1, 1, 8))
M_SACK = noisy("M_Sacking", [K.srgb((0.66, 0.56, 0.38)), K.srgb((0.58, 0.48, 0.30)), K.srgb((0.72, 0.62, 0.44))], scale=40, rough=0.95, bump=0.6, bump_dist=0.002)
M_STRAW = noisy("M_Straw", [K.srgb((0.80, 0.68, 0.38)), K.srgb((0.70, 0.56, 0.28)), K.srgb((0.86, 0.76, 0.48))], scale=30, rough=0.8, stretch=(1, 1, 8))
M_SUIT = noisy("M_FadedBlueSuit", [K.srgb((0.14, 0.19, 0.28)), K.srgb((0.24, 0.30, 0.38)), K.srgb((0.36, 0.38, 0.40)), K.srgb((0.17, 0.22, 0.31))], scale=7, rough=0.97, bump=1.0, bump_dist=0.004, sheen=0.3, warp=0.6)
M_HAT = noisy("M_HatFelt", [K.srgb((0.22, 0.34, 0.58)), K.srgb((0.28, 0.40, 0.62))], scale=8, rough=0.9, bump=0.3, sheen=0.5)
M_BOOT = noisy("M_BootLeather", [K.srgb((0.16, 0.10, 0.06)), K.srgb((0.24, 0.15, 0.09))], scale=12, rough=(0.5, 0.8), bump=0.3)
M_PAINT = plain("M_FacePaint", K.srgb((0.08, 0.07, 0.07)), rough=0.8)
M_FACEBLUE = plain("M_FacePaintBlue", K.srgb((0.22, 0.34, 0.62)), rough=0.8)
M_FACERED = plain("M_FacePaintRed", K.srgb((0.62, 0.18, 0.14)), rough=0.8)
M_STONE = noisy("M_KerbStone", [K.srgb((0.62, 0.56, 0.42)), K.srgb((0.52, 0.47, 0.36))], scale=4, rough=0.85, bump=0.3)


# ----------------------------------------------------------------------------- the ground and the road
def keep_near(x, y): return not (abs(y) < ROAD_W / 2 - 0.02 and abs(x) < 90)
near = S.grid_ground("GroundNear", M_GROUND, H, -30, 30, -30, 36, 1.5, keep=keep_near, chunk=6.0)
farg = S.polar_ground("GroundFar", M_GROUND, H, r0=0.0, r1=1000.0, nr=34, na=72, expo=2.0,
                      keep=lambda x, y: not (abs(x) < 29.5 and -29.5 < y < 35.5))
# the road: bricks (tiled UVs: the painted atlas repeats every 2.4 m) from x -90 to 90, then curving off east and west
rv = []; rf = []; ruv = []
def road_centre(t):          # t in metres along the road from x = 0
    x = t; y = 0.0
    if abs(t) > 40: y = math.copysign(1, t) * 0.0015 * (abs(t) - 40) ** 2 * (1 if t > 0 else -0.6)
    return x, y
ts = [-160 + k * 2.0 for k in range(161)]
for i, t in enumerate(ts):
    x, y = road_centre(t); x2, y2 = road_centre(t + 0.5)
    d = Vector((x2 - x, y2 - y)).normalized(); nn = Vector((-d.y, d.x))
    for j, sgn in enumerate((-1, 1)):
        px, py = x + nn.x * sgn * ROAD_W / 2, y + nn.y * sgn * ROAD_W / 2
        rv.append((px, py, H(px, py) + 0.03)); ruv.append((t / 2.4, (sgn * ROAD_W / 2) / 2.4))
for i in range(len(ts) - 1):
    rf.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
road = K.mesh_from("Road", rv, rf, M_ROAD)
uvl = road.data.uv_layers.new(name="UVMap")
for li, l in enumerate(road.data.loops): uvl.data[li].uv = ruv[l.vertex_index]
# a low kerb of yellow stone at the road edges near the reader
for sgn in (-1, 1):
    pts = [(t, sgn * (ROAD_W / 2 + 0.04), 0.035) for t in range(-40, 41, 2)]
    K.sweep(f"Kerb{sgn}", [(0.0, -0.03), (0.08, -0.03), (0.08, 0.02), (0.0, 0.03)][::(1 if sgn < 0 else -1)], pts, M_STONE)

# ----------------------------------------------------------------------------- the blue fences (posts and two rails), the open gate
def fence(name, y, x0, x1, gap=None):
    xs = []; x = x0
    while x <= x1 + 1e-6: xs.append(x); x += 2.4
    r = random.Random(hash(name) & 0xfff)
    for i, x in enumerate(xs):
        if gap and gap[0] - 0.05 < x < gap[1] + 0.05: continue
        lean = (r.uniform(-0.03, 0.03), r.uniform(-0.03, 0.03))
        box(f"{name}Post{i}", (0.1, 0.1, 1.25), (x, y, -0.25 + (1.25) / 2), M_BLUEPAINT, bevel=0.012 if abs(x) < 8 else 0.0, rot=(lean[0], lean[1], r.uniform(-0.05, 0.05)))
        box(f"{name}Cap{i}", (0.12, 0.12, 0.03), (x + lean[1] * 1.0, y - lean[0] * 1.0, 1.0), M_BLUEPAINT)
    for i in range(len(xs) - 1):
        a, b_ = xs[i], xs[i + 1]
        if gap and not (b_ <= gap[0] or a >= gap[1]):
            # rails stop at the gate posts
            for (p, q) in ((a, gap[0]), (gap[1], b_)):
                if q - p > 0.2:
                    for z in (0.45, 0.85): box(f"{name}Rail{i}_{p:.1f}_{z}", (q - p, 0.04, 0.1), ((p + q) / 2, y + 0.06, z), M_BLUEPAINT)
            continue
        for z in (0.45, 0.85):
            box(f"{name}Rail{i}_{z}", (b_ - a + 0.05, 0.04, 0.1), ((a + b_) / 2, y + 0.06 * (1 if y > 0 else -1), z + r.uniform(-0.01, 0.01)), M_BLUEPAINT)
fence("FenceN", FENCE_Y, -40.8, 40.8, gap=GATE)
fence("FenceS", -FENCE_Y, -40.8, 40.8)
for gx in GATE:
    box(f"GatePost{gx}", (0.13, 0.13, 1.45), (gx, FENCE_Y, -0.3 + (1.45) / 2), M_BLUEPAINT, bevel=0.015)
# the gate leaf, swung open into the field against the corn (hinged on the west post)
G = Frame((GATE[0] + 0.05, FENCE_Y + 0.05), math.radians(-80))   # local +X along the leaf
gw = GATE[1] - GATE[0] - 0.14
for z in (0.25, 0.6, 0.95):
    G.box(f"GateBar{z}", (gw, 0.035, 0.08), (gw / 2, 0, z), M_BLUEPAINT, bevel=0.006)
for xx in (0.03, gw - 0.03):
    G.box(f"GateStile{xx}", (0.07, 0.05, 1.0), (xx, 0, 0.12 + (1.0) / 2), M_BLUEPAINT, bevel=0.008)
d_ = math.atan2(0.7, gw)
G.box("GateBrace", (math.hypot(gw, 0.7), 0.03, 0.06), (gw / 2, 0.0, 0.6), M_BLUEPAINT, bevel=0.005, ry=-d_)
# fences of the far fields: blue rails seen from afar along the road curves
for k, (x, y, ln, yaw) in enumerate(((60, 30, 40, 0.1), (-70, -40, 50, -0.05), (95, -25, 60, 0.3), (-110, 35, 45, 0.2))):
    F_ = Frame((x, y), yaw, z=H(x, y))
    for i in range(int(ln / 3)):
        F_.box(f"FarPost{k}_{i}", (0.1, 0.1, 1.1), (-ln / 2 + i * 3, 0, 0 + (1.1) / 2), M_BLUEPAINT)
    F_.box(f"FarRail{k}", (ln, 0.05, 0.08), (0, 0, 0.8), M_BLUEPAINT)

# ----------------------------------------------------------------------------- the corn
plants = []       # (x, y, h, yaw, lean)
for row in range(-60, 61):
    x = row * 0.76 + 0.2
    y = FIELD_Y0 + 0.2 + (row % 2) * 0.15
    while y < 34:
        jx = x + rng.uniform(-0.08, 0.08); jy = y + rng.uniform(-0.06, 0.06)
        if in_corn(jx, jy) and abs(jx) < 46:
            hgt = rng.uniform(2.05, 2.55) * (1 - 0.15 * math.exp(-((jx - SCARE.x) ** 2 + (jy - SCARE.y) ** 2) / 6))
            plants.append((jx, jy, hgt, rng.uniform(0, 2 * math.pi), (rng.gauss(0, 0.04), rng.gauss(0, 0.04))))
        y += rng.uniform(0.26, 0.36)
def near_plant(x, y):
    d_r = math.hypot(x - READER.x, y - READER.y); d_s = math.hypot(x - SCARE.x, y - SCARE.y)
    return (d_r < 4.6) or d_s < 2.5 or (y < FIELD_Y0 + 0.5 and abs(x) < 7)
geo = [p for p in plants if near_plant(p[0], p[1])]
cards = [p for p in plants if not near_plant(p[0], p[1]) and p[1] < 30 and abs(p[0]) < 46
         and (math.hypot(p[0] - READER.x, p[1] - READER.y) < 10 or rng.random() < (0.45 if p[1] < 14 else 0.16))]
print("corn: modelled", len(geo), "cards", len(cards))

mbc = MB()
def corn_plant(mb, x, y, h, yaw, lean, r):
    """Stalk (5-sided, 4 segments), 9-11 leaves as bent strips (2 segments wide... 1 x 4), an ear in its husk, a tassel."""
    z0 = H(x, y)
    base = Vector((x, y, z0 - 0.02)); top = base + Vector((lean[0] * h, lean[1] * h, h))
    def P(t): return base.lerp(top, t) + Vector((0, 0, 0)) * t
    # stalk as a 4-sided tube
    rr = [0.016, 0.014, 0.011, 0.008, 0.004]; segs = 4; sides = 4
    rings = []
    for i in range(segs + 1):
        t = i / segs; c = P(t * 0.92)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides + yaw
            ring.append(mb.vert(c + Vector((math.cos(a), math.sin(a), 0)) * rr[i], (0.02 + 0.06 * k / sides, 0.02 + 0.3 * t), t * t * 0.6))
        rings.append(ring)
    for i in range(segs):
        for k in range(sides):
            mb.face(rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k])
    n = r.randint(9, 11)
    for i in range(n):
        t = 0.1 + 0.75 * i / n + r.uniform(-0.02, 0.02)
        a = yaw + (math.pi if i % 2 else 0) + r.uniform(-0.5, 0.5)
        d = Vector((math.cos(a), math.sin(a), 0)); side = Vector((-d.y, d.x, 0))
        L = (0.45 + 0.4 * math.sin(math.pi * min(1, t * 1.15))) * r.uniform(0.85, 1.1) * (h / 2.3)
        W = 0.04 + 0.025 * math.sin(math.pi * t)
        up = r.uniform(0.7, 1.1); droop = r.uniform(0.9, 1.6)
        o = P(t)
        prev = None
        for s in range(4):
            u = s / 3
            p = o + d * (L * u * 0.85) + Vector((0, 0, L * (up * u - droop * u * u) * 0.55))
            w = W * math.sin(math.pi * min(0.98, 0.18 + u * 0.8)) * (1.0 if s < 3 else 0.15)
            curl = side * w + Vector((0, 0, w * 0.25))
            sway = min(1.0, t * 0.7 + u * 0.4)
            v0 = mb.vert(p - curl, (0.3, u), sway); v1 = mb.vert(p + Vector((0, 0, 0.004)), (0.5, u), sway); v2 = mb.vert(p + curl, (0.7, u), sway)
            if prev: mb.face(prev[0], prev[1], v1, v0); mb.face(prev[1], prev[2], v2, v1)
            prev = (v0, v1, v2)
    # the ear: a husked spindle leaning out from the stalk
    if r.random() < 0.85:
        t = r.uniform(0.4, 0.5); a = yaw + r.uniform(0, 6.28); d = Vector((math.cos(a), math.sin(a), 0))
        o = P(t) + d * 0.02; ax = (d * 0.45 + Vector((0, 0, 1))).normalized()
        prof = [(0.0, 0.0), (0.026, 0.05), (0.028, 0.14), (0.0, 0.23)]
        ring_prev = None
        side = ax.cross(Vector((0, 0, 1))).normalized() if abs(ax.z) < 0.99 else Vector((1, 0, 0)); up2 = side.cross(ax)
        tip = None
        for j, (rad, zz) in enumerate(prof):
            c = o + ax * zz
            if rad == 0:
                vi = mb.vert(c, (0.85, 0.1 + zz), t * 0.6)
                if ring_prev is None: ring_prev = [vi] * 5
                else:
                    for k in range(5): mb.face(ring_prev[k], ring_prev[(k + 1) % 5], vi)
                continue
            ring = [mb.vert(c + (side * math.cos(2 * math.pi * k / 5) + up2 * math.sin(2 * math.pi * k / 5)) * rad, (0.86 + 0.02 * k, 0.3 + zz), t * 0.6) for k in range(5)]
            if j == 1:
                for k in range(5): mb.face(ring_prev[0], ring[k], ring[(k + 1) % 5])
            else:
                for k in range(5): mb.face(ring_prev[k], ring_prev[(k + 1) % 5], ring[(k + 1) % 5], ring[k])
            ring_prev = ring
    # the tassel: a central spike and three thin side branches, each a narrow strip
    tp = top
    for k in range(4):
        if k == 0: d = Vector((0, 0, 1)); L = 0.3
        else:
            a = yaw + k * 2.1 + r.uniform(-0.3, 0.3); d = Vector((math.cos(a) * 0.8, math.sin(a) * 0.8, 0.45)).normalized(); L = r.uniform(0.14, 0.2)
        s_ = d.cross(Vector((0, 0, 1))) if k else Vector((1, 0, 0))
        s_ = s_.normalized() * 0.005
        p1 = tp + d * L * 0.5; p2 = tp + d * L + Vector((0, 0, -0.04 if k else 0))
        a0 = mb.vert(tp - s_, (0.93, 0.96), 1.0); a1 = mb.vert(tp + s_, (0.95, 0.96), 1.0)
        b0 = mb.vert(p1 - s_ * 0.7, (0.93, 0.98), 1.0); b1 = mb.vert(p1 + s_ * 0.7, (0.95, 0.98), 1.0); c0 = mb.vert(p2, (0.94, 1.0), 1.0)
        mb.face(a0, a1, b1, b0); mb.face(b0, b1, c0)
for (x, y, h, yaw, lean) in geo:
    corn_plant(mbc, x, y, h, yaw, lean, rng)
corn_o = mbc.build("veg.crop.corn", M_CORN)
# cards: two crossed cards per plant, a random cell of the atlas
mbk = MB()
for (x, y, h, yaw, lean) in cards:
    cell = rng.randrange(4); z0 = H(x, y)
    to_r = math.atan2(READER.y - y, READER.x - x) + math.pi / 2 + rng.uniform(-0.5, 0.5)
    for k in range(1):
        a = to_r; d = Vector((math.cos(a), math.sin(a), 0)) * 0.6
        mbk.quad_card((x, y, z0 - 0.03), d, (lean[0] * h, lean[1] * h, h * 1.04), uv0=(cell / 4, 0), uv1=((cell + 1) / 4, 1), sway=(0.0, 1.0))
cards_o = mbk.build("veg.crop.cornCards", M_CORNCARD)
# beyond the cards: an opaque corn mass whose top is a ragged line of tassels and leaves (the field to its far edge)
def corn_mass():
    """a low opaque backing behind the last cards (at 30 m and along the far sides): it only shows through gaps"""
    vs = []; fs = []
    outline = [(-46, 2.6), (-46, 30), (46, 30), (46, 2.6)]
    pts = []
    for (a, b_) in zip(outline, outline[1:]):
        n = max(1, int(math.hypot(b_[0] - a[0], b_[1] - a[1]) / 4))
        for k in range(n): pts.append((a[0] + (b_[0] - a[0]) * k / n, a[1] + (b_[1] - a[1]) * k / n))
    pts.append(outline[-1])
    for (x, y) in pts:
        z = H(x, y); vs += [(x, y, z - 0.05), (x, y, z + 1.9)]
    for i in range(len(pts) - 1): fs.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    o = K.mesh_from("CornMass", vs, fs, noisy("M_CornMass", [K.srgb((0.22, 0.30, 0.10)), K.srgb((0.32, 0.38, 0.14)), K.srgb((0.40, 0.40, 0.18))],
                                                         scale=2.5, rough=0.8, stretch=(1, 1, 0.3)))
    bm = bmesh.new(); bm.from_mesh(o.data)
    for f in bm.faces:       # every face toward the reader
        if f.normal.dot(Vector((0, 5, 0)) - f.calc_center_median()) < 0: f.normal_flip()
    bm.to_mesh(o.data); bm.free()
    return o
corn_mass()


# ----------------------------------------------------------------------------- the Scarecrow on his pole
P = SCARE
cyl("Pole", 0.05, 3.0, (P.x, P.y, H(P.x, P.y) - 0.3 + 1.5), M_WOOD, verts=8, r2=0.04)
CB_Z = 1.95                       # the crossbar at shoulder height
cyl("CrossBar", 0.035, 1.5, (P.x, P.y + 0.02, CB_Z), M_WOOD, verts=7, rot=(0, math.pi / 2, 0))
for sgn in (-1, 1):
    tube(f"Lashing{sgn}", [(P.x - 0.06, P.y + 0.06 * sgn, CB_Z - 0.05), (P.x + 0.06, P.y - 0.06 * sgn, CB_Z + 0.05)], 0.008, M_STRAW, sides=4)
# the body: a stuffed coat on the pole (lumpy torso), the sleeves along the crossbar, hands of straw at the cuffs
F = Frame((P.x, P.y - 0.08), math.pi)            # faces -Y (towards the road and the reader)
def lumpy(name, profile, loc, mat, seed, amp=0.04, steps=14, squash=(1, 1)):
    o = lathe(name, profile, loc, mat, steps=steps, jitter=0.0)
    for v in o.data.vertices:
        nrm = Vector((v.co.x, v.co.y, 0))
        if nrm.length > 1e-4:
            k = 1 + amp * noise.noise(v.co * 7 + Vector((seed, 0, 0))) * 2.2
            v.co.x *= k * squash[0]; v.co.y *= k * squash[1]
    return o
# torso: a jacket, broad at the shoulders, the waist sagging where the straw has settled
lumpy("Coat", [(0.0, 1.05), (0.16, 1.07), (0.2, 1.2), (0.19, 1.45), (0.22, 1.7), (0.24, 1.86), (0.2, 1.94), (0.08, 1.98), (0.0, 1.99)],
      (P.x, P.y - 0.06, 0), M_SUIT, 1.0, amp=0.05, squash=(1.0, 0.62))
# coat tails and lapels
for sgn in (-1, 1):
    F.box(f"Lapel{sgn}", (0.07, 0.02, 0.32), (sgn * 0.08, 0.15, 1.7), M_SUIT, rx=0.0, ry=sgn * 0.25)
    F.box(f"CoatTail{sgn}", (0.17, 0.03, 0.36), (sgn * 0.09, -0.04, 0.9), M_SUIT, rx=0.12, ry=sgn * 0.05)
for k, z in enumerate((1.62, 1.48, 1.34)):
    sphere(f"CoatButton{k}", 0.014, F.p(0.02, 0.135, z), plain("M_HornButton", K.srgb((0.22, 0.17, 0.12)), rough=0.4), seg=6)
# sleeves: tubes along the crossbar, bulging and sagging, cuffs open with straw
for sgn in (-1, 1):
    pts = [Vector((P.x + sgn * 0.18, P.y - 0.04, CB_Z - 0.06)), Vector((P.x + sgn * 0.38, P.y - 0.03, CB_Z - 0.08)),
           Vector((P.x + sgn * 0.56, P.y - 0.02, CB_Z - 0.12)), Vector((P.x + sgn * 0.68, P.y - 0.02, CB_Z - 0.14))]
    tube(f"Sleeve{sgn}", pts, [0.085, 0.075, 0.07, 0.068], M_SUIT, sides=9)
    cpt = pts[-1]
    for k in range(14):
        a = k / 14 * 2 * math.pi; o = cpt + Vector((0, math.cos(a) * 0.04, math.sin(a) * 0.04))
        e = o + Vector((sgn * rng.uniform(0.08, 0.17), rng.uniform(-0.04, 0.04), rng.uniform(-0.12, 0.02)))
        tube(f"CuffStraw{sgn}_{k}", [o, e], [0.004, 0.002], M_STRAW, sides=3, caps=False)
# trousers: legs hanging limp from the coat, a little bent, straw sticking out at the knees' tears
for sgn in (-1, 1):
    hip = Vector((P.x + sgn * 0.1, P.y - 0.08, 1.12))
    knee = Vector((P.x + sgn * 0.13, P.y - 0.15, 0.78)); ankle = Vector((P.x + sgn * 0.12, P.y - 0.11, 0.42))
    tube(f"Leg{sgn}", [hip, hip.lerp(knee, 0.5), knee, ankle], [0.095, 0.085, 0.075, 0.07], M_SUIT, sides=9)
    # boots with blue tops: a blue turned-down top, the leather foot hanging toe-down
    tube(f"BootTop{sgn}", [ankle + Vector((0, 0, 0.04)), ankle - Vector((0, 0, 0.1))], [0.082, 0.072], M_FACEBLUE, sides=10)
    tube(f"BootLeg{sgn}", [ankle - Vector((0, 0, 0.08)), ankle - Vector((0, -0.01, 0.24))], [0.064, 0.058], M_BOOT, sides=10)
    toe = ankle - Vector((0, 0.13, 0.31))
    tube(f"BootFoot{sgn}", [ankle - Vector((0, -0.03, 0.25)), ankle - Vector((0, 0.04, 0.3)), toe], [0.06, 0.05, 0.035], M_BOOT, sides=10)
    for k in range(6):
        o = knee + Vector((sgn * 0.07, -0.04, rng.uniform(-0.05, 0.05)))
        tube(f"KneeStraw{sgn}_{k}", [o, o + Vector((sgn * rng.uniform(0.03, 0.08), rng.uniform(-0.06, 0.0), rng.uniform(-0.06, 0.04)))], [0.003, 0.0015], M_STRAW, sides=3, caps=False)
M_PATCH = noisy("M_SuitPatch", [K.srgb((0.30, 0.36, 0.46)), K.srgb((0.38, 0.42, 0.50))], scale=9, rough=0.97, bump=0.6)
F.box("PatchCoat", (0.1, 0.012, 0.09), (-0.11, 0.115, 1.38), M_PATCH, ry=0.15)
box("PatchKnee", (0.012, 0.09, 0.08), (P.x + 0.21, P.y - 0.15, 0.8), M_PATCH)
# straw at the neck
for k in range(16):
    a = k / 16 * 2 * math.pi; o = Vector((P.x + math.cos(a) * 0.09, P.y - 0.06 + math.sin(a) * 0.06, 1.98))
    tube(f"NeckStraw{k}", [o, o + Vector((math.cos(a) * rng.uniform(0.04, 0.09), math.sin(a) * 0.05, rng.uniform(0.0, 0.06)))], [0.0035, 0.0015], M_STRAW, sides=3, caps=False)
# the head: a small sack stuffed with straw, tied at the neck, a little lopsided
HEAD = Vector((P.x + 0.02, P.y - 0.08, 2.17))
hd = sphere("Head", 0.15, tuple(HEAD), M_SACK, seg=16, scale=(1.0, 0.85, 1.12))
for v in hd.data.vertices:
    v.co += v.normal * 0.012 * noise.noise(v.co * 9 + Vector((3, 1, 2)))
    if v.co.z < -0.1: v.co.x *= 0.7; v.co.y *= 0.7
hd.rotation_euler = (0.08, -0.1, 0.12)
tube("NeckTie", [tuple(HEAD + Vector((math.cos(a) * 0.085, math.sin(a) * 0.075, -0.135))) for a in [2 * math.pi * k / 10 for k in range(11)]], 0.012, M_STRAW, sides=4)
for k in range(3):        # the gathered sack ends above the tie
    sphere(f"SackGather{k}", 0.03, tuple(HEAD + Vector((-0.05 + 0.05 * k, 0.04, -0.16))), M_SACK, seg=8, scale=(1, 0.8, 0.6))
# the painted face, on the side facing the road (-Y): two round eyes (blue irises, one a little larger: "one eye
# smaller than the other"... painted by the farmer), a nose, and a wide mouth
def decal(name, centre, rx, rz, mat, tilt=0.0, n=12):
    vs = [tuple(centre)]
    for k in range(n):
        a = 2 * math.pi * k / n
        lx, lz = math.cos(a) * rx, math.sin(a) * rz
        lx, lz = lx * math.cos(tilt) - lz * math.sin(tilt), lx * math.sin(tilt) + lz * math.cos(tilt)
        vs.append(tuple(Vector(centre) + Vector((lx, 0, lz))))
    fs = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)][::-1]
    return K.mesh_from(name, vs, fs, mat)
fy = HEAD.y - 0.128
ec = 0.02
decal("EyeL", HEAD + Vector((-0.052, -0.123, 0.03)), 0.028, 0.03, M_PAINT); decal("IrisL", HEAD + Vector((-0.052, -0.1245, 0.027)), 0.015, 0.016, M_FACEBLUE)
decal("EyeR", HEAD + Vector((0.055, -0.121, 0.04)), 0.022, 0.024, M_PAINT); decal("IrisR", HEAD + Vector((0.055, -0.1225, 0.037)), 0.012, 0.013, M_FACEBLUE)
decal("Nose", HEAD + Vector((0.0, -0.13, -0.01)), 0.014, 0.022, M_PAINT)
mvs = []; mfs = []
for k in range(9):
    t = k / 8; x = -0.065 + 0.13 * t; z = -0.065 - 0.022 * math.sin(math.pi * t)
    yv = -0.122 + 0.02 * (abs(x) / 0.065) ** 2
    w = 0.006 * (1 - abs(2 * t - 1) ** 3) + 0.0015
    mvs += [tuple(HEAD + Vector((x, yv, z + w))), tuple(HEAD + Vector((x, yv, z - w)))]
    if k: mfs.append((2 * k - 2, 2 * k, 2 * k + 1, 2 * k - 1))
K.mesh_from("Mouth", mvs, mfs, M_FACERED)
for o_ in ("EyeL", "IrisL", "EyeR", "IrisR", "Nose", "Mouth"):
    ob = bpy.data.objects[o_]
    for v in ob.data.vertices:      # wrap the decals onto the sack's curve: push back with distance from centre
        dx = v.co.x - HEAD.x; dz = v.co.z - HEAD.z
        v.co.y += (dx * dx + dz * dz) * 0.9
# the old pointed blue hat, perched a little askew: a brim with a sagging edge and a tall, bent cone
HAT = HEAD + Vector((0.0, 0.01, 0.13))
bv = []; bf = []
for j, rr in enumerate((0.11, 0.17, 0.22)):
    for i in range(20):
        a = 2 * math.pi * i / 20
        sag = -0.025 * (j / 2) * (1 + math.sin(a * 2 + 0.5)) * 0.8
        bv.append(tuple(HAT + Vector((math.cos(a) * rr, math.sin(a) * rr * 0.95, sag))))
for j in range(2):
    for i in range(20): bf.append((j * 20 + i, j * 20 + (i + 1) % 20, (j + 1) * 20 + (i + 1) % 20, (j + 1) * 20 + i))
br = K.mesh_from("HatBrim", bv, bf, M_HAT, smooth=True); br.modifiers.new("Solid", 'SOLIDIFY').thickness = 0.008
cone = [Vector(HAT) + Vector((0, 0, 0.0))]
pts = [HAT + Vector((0.0, 0, 0.0)), HAT + Vector((0.01, 0.0, 0.12)), HAT + Vector((0.03, 0.01, 0.24)), HAT + Vector((0.07, 0.02, 0.33)), HAT + Vector((0.12, 0.02, 0.36))]
tube("HatCone", pts, [0.105, 0.08, 0.05, 0.025, 0.006], M_HAT, sides=14)
tube("HatBand", [tuple(HAT + Vector((math.cos(a) * 0.106, math.sin(a) * 0.104, 0.025))) for a in [2 * math.pi * k / 16 for k in range(17)]], 0.014, plain("M_HatBand", K.srgb((0.14, 0.20, 0.34)), rough=0.8), sides=4)

# ----------------------------------------------------------------------------- Munchkin houses in the distance: round, blue, a big dome for a roof
def munchkin_house(name, x, y, rad, rot):
    z = H(x, y)
    cyl(f"{name}Wall", rad, rad * 0.95, (x, y, z + rad * 0.95 / 2 - 0.1), M_HOUSE, verts=14)
    dome = sphere(f"{name}Dome", rad * 1.08, (x, y, z + rad * 0.9), M_DOME, seg=14, scale=(1, 1, 0.95))
    for v in dome.data.vertices:
        if v.co.z < 0: v.co.z = 0
    d = Vector((math.cos(rot), math.sin(rot), 0))
    box(f"{name}Door", (0.9, 0.08, 1.6), tuple(Vector((x, y, z + 0.8)) + d * rad * 0.99), plain("M_DoorBlue", K.srgb((0.16, 0.24, 0.40)), rough=0.7), rot=(0, 0, rot + math.pi / 2))
    for s in (-1, 1):
        dd = Vector((math.cos(rot + s * 0.8), math.sin(rot + s * 0.8), 0))
        box(f"{name}Win{s}", (0.6, 0.08, 0.7), tuple(Vector((x, y, z + 1.4)) + dd * rad * 0.99), plain("M_HouseWindow", (0.04, 0.05, 0.07), rough=0.2), rot=(0, 0, rot + s * 0.8 + math.pi / 2))
    sphere(f"{name}Finial", rad * 0.08, (x, y, z + rad * 0.9 + rad * 1.03), M_HOUSE, seg=8)
for k, (x, y, rad) in enumerate(((-34, -46, 3.4), (22, -62, 3.0), (60, -38, 3.6), (-80, -90, 3.2), (110, 40, 3.4), (-120, 55, 3.0), (5, -140, 3.8), (160, -95, 3.5))):
    munchkin_house(f"House{k}", x, y, rad, math.atan2(-y, -x))

# ----------------------------------------------------------------------------- grass on the verges and along the fence lines
mbg = MB()
pts = []
for i in range(300):
    x = rng.uniform(-16, 16)
    y = rng.choice((1, -1)) * (ROAD_W / 2 + abs(rng.gauss(0, 0.5)) + 0.02)
    if abs(x - READER.x) < 0.5 and y > 0 and y < FENCE_Y + 0.3 and GATE[0] < x < GATE[1]: continue
    pts.append((x, y))
for i in range(120):
    x = rng.uniform(-8, 8); y = rng.uniform(-FENCE_Y - 0.4, -FENCE_Y - 3.0)
    pts.append((x, y))
for i in range(90):          # the trodden path's edges and the clearing's rim
    t = rng.random(); a = Vector((0.15, FENCE_Y)); b = SCARE.xy
    p = a.lerp(b, t); off = rng.choice((-1, 1)) * rng.uniform(0.3, 0.55)
    pts.append((p.x + off, p.y))
S.grass_clumps(mbg, pts, H, rng, height=(0.15, 0.4), blades=(3, 6), lean=0.55, width=0.016)
mbg.build("veg.grass.verge", M_GRASS)
# a few dandelion-like flower heads? no: keep the verges plain grass (Oz is tidy farmland)

# ----------------------------------------------------------------------------- sky and light: a bright morning, sun high in the south-south-east
SUN_TO = Vector((-0.25, -0.62, 0.74)).normalized()        # direction toward the sun (behind the reader, a little left)
M_SKY = S.sky_mat("M_SkyDome", SUN_TO, zenith=(0.10, 0.24, 0.62), mid=(0.28, 0.48, 0.80), horizon=(0.66, 0.74, 0.84), cloud=0.45,
                  clear_dir=(0, 1, 0.25), hills=(0.022, (0.30, 0.40, 0.36), (0.50, 0.60, 0.66)))
S.sky_dome(M_SKY, radius=1100.0)
light_obj("Lamp.sun", 'SUN', 4.5, (1.0, 0.95, 0.86), (0, 0, 50), direction=tuple(-SUN_TO), angle=math.radians(1.2))
world = bpy.data.worlds.new("Day"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.56, 0.80, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors and living-scene sources
S.reader(READER, (SCARE.x - READER.x, SCARE.y - READER.y))
anchor("scene.centre", tuple(SCARE))
anchor("scene.scarecrow", tuple(SCARE))
sound("birds", "corn", (6.0, 14.0, 3.0))
sound("birds", "verge", (-12.0, -6.0, 1.5))
sound("wind", "field", (-8.0, 9.0, 2.5))
page = S.page_preview()
K.apply_transforms()

# ----------------------------------------------------------------------------- cameras
E = READER + Vector((0, 0, S.EYE))
cams = S.eye_cams([("Reader", 0), ("Left", -80), ("Right", 80), ("Behind", 180)], dz=-0.2, extra=[
    ("Page", E, E + (SCARE - READER).normalized() * 5 + Vector((0, 0, -0.2)), 17),
    ("Scarecrow", Vector((0.2, 3.6, 1.5)), HEAD + Vector((0, 0, -0.45)), 28),
    ("Road", Vector((-9.0, -0.8, 1.6)), Vector((6.0, 2.5, 0.9)), 20),
])
probs = S.check_reader(ignore=("PagePreview", "veg.grass.verge"))
K.print_budget(exclude=("PagePreview",))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.0, captures_dir=ARGS.captures)

if ARGS.export or ARGS.bake:
    S.export(SID, cams, page=page, unlit_emit=(),
             keep_names={"M_CornLeaf": "veg.crop.corn", "M_CornCards": "veg.crop.cornCards", "M_VergeGrass": "veg.grass.verge"},
             size_for={"M_Ground": (2048, 64, 1024), "M_BluePaint": (1024, 64, 512), "M_FadedBlueSuit": (1024, 64, 512), "M_Sacking": (512, 64, 256),
                       "M_HatFelt": (512, 64, 256), "M_VergeGrass": (1024, 32, 64), "M_HouseBlue": (512, 32, 128), "M_DomeBlue": (512, 32, 128),
                       "M_CornMass": (1024, 32, 256), "M_PoleWood": (512, 64, 256), "M_Straw": (512, 32, 128), "M_KerbStone": (512, 64, 256),
                       "M_SkyDome": (2048,), "M_BootLeather": (256, 64, 128)},
             default_size=(128, 32, 64))
print("DONE")
