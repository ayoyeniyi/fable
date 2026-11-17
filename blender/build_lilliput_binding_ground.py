"""
Fable scene room: Where Gulliver Lay Bound (Gulliver's Travels, Part I, Chapter I) - lilliput-binding-ground.

"I lay down on the grass, which was very short and soft ... I attempted to rise, but was not able to stir: for, as I
happened to lie on my back, I found my arms and legs were strongly fastened on each side to the ground; and my hair,
which was long and thick, tied down in the same manner. I likewise felt several slender ligatures across my body,
from my armpits to my thighs."
"about four yards from me, over against my right ear ... I saw a stage erected about a foot and a half from the
ground, capable of holding four of the inhabitants, with two or three ladders to mount it"
"several ladders should be applied to my sides ... laden with baskets full of meat"
"one of their largest hogsheads ... it did not hold half a pint"
"a frame of wood raised three inches from the ground, about seven feet long, and four wide, moving upon twenty-two
wheels" ... "Eighty poles, each of one foot high, were erected for this purpose, and very strong cords, of the
bigness of packthread, were fastened by hooks"

The reader is Gulliver-size; Lilliput is built at 1/12 (six-inch people, 7 ft trees = 2.1 m, 40 ft fields = 12 m).
Gulliver himself is not modelled (a convincing giant figure is beyond a procedural build): the reader stands at the
head end of the body-shaped patch of grass he flattened, ringed by the pegs and cut packthread that held him, the
hair pegs at the reader's feet, the ladders left lying along his sides, baskets and two empty hogsheads by where his
right hand lay, spent arrows "like so many needles" in the grass on the left, the stage four yards off by the right
ear, and the 22-wheeled engine drawn up alongside on the left, its poles bundled on it, ready. Beyond: the common, the
tiny hedged fields, little woods of seven-foot trees and, far off to the north, the wall of Mildendo.

Time: early morning after the night's storm, a low clear sun in the east growing hot; a few broken clouds.
No people, no temple, chains or turret, no ship or boat.

Axes: metres, +Z up, +Y north. Reader's feet at the origin, facing a little east of north (yaw 12 degrees).

Run headless:
  blender -b -P blender/build_lilliput_binding_ground.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_lilliput_binding_ground.py -- --render --samples 48 --res 1400
  blender -b -P blender/build_lilliput_binding_ground.py -- --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b4 as S
from scene_kit_b4 import (K, new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, lathe, tube, MB, anchor, sound, camera,
                          smoothstep, lerp, n2, fbm2, link, card, set_card_normals, srgb)

ARGS = S.setup("lilliput-binding-ground", 1699, "LilliputBindingGround", default_samples=48)
rng = random.Random(1699)
EYE = S.EYE
YAW = 24.0
SUN_DIR = Vector((0.93, 0.12, 0.34)).normalized()     # toward the sun: east, a little north, ~20 degrees up
CITY = Vector((7.0, 44.0, 0.0))                       # Mildendo, its wall about forty metres off to the north
HAMLET = Vector((9.5, 9.0, 0.0))
ROAD = [(-1.9, 2.6), (-2.4, 6.5), (-1.7, 12.0), (0.4, 20.0), (3.0, 27.0), (5.2, 31.5)]

# ----------------------------------------------------------------------------- the impression of the body
# Gulliver lay on his back, head at the reader's feet (south), feet to the north; his right side is east (+X).
HEAD = Vector((0.0, 0.55))
CAPS = [  # (p0, p1, radius): head, neck, torso, hips, legs, arms
    ((0.0, 0.50), (0.0, 0.66), 0.105), ((0.0, 0.70), (0.0, 0.80), 0.07), ((0.0, 0.88), (0.0, 1.30), 0.19),
    ((0.0, 1.30), (0.0, 1.42), 0.17), ((-0.09, 1.45), (-0.12, 2.25), 0.075), ((0.09, 1.45), (0.12, 2.25), 0.075),
    ((0.26, 0.86), (0.30, 1.55), 0.055), ((-0.25, 0.86), (-0.40, 1.42), 0.055)]   # left arm a little out: he wrenched it free


def seg_d(px, py, a, b):
    ax, ay = a; bx, by = b; dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-9)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def body_sdf(x, y):
    return min(seg_d(x, y, a, b) - r for a, b, r in CAPS)


def body_depth(x, y):
    d = body_sdf(x, y)
    return 0.028 * (1 - smoothstep(-0.05, 0.05, d))


def gz(x, y):
    r = math.hypot(x, y)
    z = 0.012 * noise.noise(Vector((x * 1.9, y * 1.9, 0.4))) + 0.06 * noise.noise(Vector((x * 0.21, y * 0.21, 1.7)))
    z += 0.5 * noise.noise(Vector((x * 0.03, y * 0.03, 3.1))) * smoothstep(8, 40, r)
    z += 0.7 * math.exp(-((x - CITY.x) ** 2 + (y - CITY.y) ** 2) / (2 * 16.0 ** 2))      # the low rise the city stands on
    if r < 3.2: z -= body_depth(x, y)
    return z


Z0 = gz(0, 0)
def h(x, y): return gz(x, y) - Z0


def road_dist(x, y):
    return min(seg_d(x, y, ROAD[i], ROAD[i + 1]) for i in range(len(ROAD) - 1))


# ----------------------------------------------------------------------------- the body mask image (ground shader)
MASK_N = 512; MASK_W = 3.2       # covers x in [-1.6, 1.6], y in [-0.6, 2.6]
def make_mask():
    a = np.zeros((MASK_N, MASK_N, 4), np.float32)
    xs = (np.arange(MASK_N) + 0.5) / MASK_N * MASK_W - MASK_W / 2
    ys = (np.arange(MASK_N) + 0.5) / MASK_N * MASK_W - 0.6
    X, Y = np.meshgrid(xs, ys)
    D = np.full(X.shape, 9.0, np.float32)
    for (ax, ay), (bx, by), r in CAPS:
        dx, dy = bx - ax, by - ay
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / (dx * dx + dy * dy + 1e-9), 0, 1)
        D = np.minimum(D, np.hypot(X - ax - t * dx, Y - ay - t * dy) - r)
    inside = 1 - np.clip((D + 0.03) / 0.08, 0, 1)
    rim = np.exp(-((D - 0.02) / 0.03) ** 2)          # the grass pushed up and out at the edge
    a[..., 0] = inside; a[..., 1] = rim; a[..., 2] = 0; a[..., 3] = 1
    return np_image("A_BodyMask", a[::-1], noncolor=True)


IMG_MASK = make_mask()

# ----------------------------------------------------------------------------- materials
def ground_mat(name):
    """Short soft turf after rain, early sun: fine mottled greens, small bare and clover patches, worn line of the
    road; the flattened body-shaped patch paler and sheened (blades laid flat), its rim pushed up; far off the
    patchwork of 40-foot fields (pasture, hay, ploughland, a field in flower)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2600, 0)); s = sep_xyz(nt, co, (-2400, 0))
    n1 = noise_(nt, co, 0.9, 5, 0.6, loc=(-1800, 300)); n2_ = noise_(nt, co, 7.0, 6, 0.65, loc=(-1800, 0)); n3 = noise_(nt, co, 40.0, 4, 0.6, loc=(-1800, -300))
    base = ramp(nt, [(0.0, c4(srgb((0.20, 0.29, 0.09)))), (0.35, c4(srgb((0.27, 0.36, 0.12)))), (0.65, c4(srgb((0.33, 0.41, 0.14)))), (1.0, c4(srgb((0.42, 0.45, 0.19))))], (-1300, 300))
    mixn = math_(nt, 'ADD', math_(nt, 'MULTIPLY', n1.outputs["Fac"], 0.6), math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.4), (-1500, 200))
    nt.links.new(mixn, base.inputs["Fac"])
    col = base.outputs["Color"]
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n3.outputs["Fac"], 0.3, 0.7, 0.0, 0.45, (-1100, -300)), col, (0.45, 0.5, 0.3, 1), (-900, 200))
    # fields beyond the common: snapped coords in a frame turned 18 degrees, 12 m cells
    # the hedge grid is world = R(18 deg) (u, v): cells are floor(S R(-18 deg) p), rotating first, then scaling
    mr = node(nt, "ShaderNodeMapping", (-2350, -800)); mr.inputs["Rotation"].default_value = (0, 0, math.radians(-18)); nt.links.new(co, mr.inputs["Vector"])
    mp = node(nt, "ShaderNodeMapping", (-2200, -800)); mp.inputs["Scale"].default_value = (1 / 12.0, 1 / 12.5, 1)
    nt.links.new(mr.outputs["Vector"], mp.inputs["Vector"])
    sn = node(nt, "ShaderNodeVectorMath", (-2000, -800), operation='FLOOR'); nt.links.new(mp.outputs["Vector"], sn.inputs[0])
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1800, -800)); wn.noise_dimensions = '3D'; nt.links.new(sn.outputs[0], wn.inputs["Vector"])
    fr = ramp(nt, [(0.0, c4(srgb((0.24, 0.36, 0.10)))), (0.3, c4(srgb((0.40, 0.47, 0.16)))), (0.5, c4(srgb((0.70, 0.62, 0.32)))), (0.62, c4(srgb((0.45, 0.33, 0.21)))),
                   (0.75, c4(srgb((0.20, 0.31, 0.09)))), (0.88, c4(srgb((0.60, 0.58, 0.24)))), (1.0, c4(srgb((0.62, 0.50, 0.55))))], (-1600, -800), interp='CONSTANT')
    nt.links.new(wn.outputs["Value"], fr.inputs["Fac"])
    fcol = mix_rgb(nt, 'MULTIPLY', maprange(nt, n2_.outputs["Fac"], 0.3, 0.7, 0.0, 0.3, (-1300, -1000)), fr.outputs["Color"], (0.6, 0.6, 0.6, 1), (-1300, -800))
    rr = node(nt, "ShaderNodeVectorMath", (-2200, -1200), operation='LENGTH')
    xy = node(nt, "ShaderNodeCombineXYZ", (-2350, -1200)); nt.links.new(s.outputs["X"], xy.inputs["X"]); nt.links.new(s.outputs["Y"], xy.inputs["Y"]); nt.links.new(xy.outputs[0], rr.inputs[0])
    fw = maprange(nt, math_(nt, 'ADD', rr.outputs["Value"], math_(nt, 'MULTIPLY', n1.outputs["Fac"], 1.5)), 9.0, 16.0, 0, 1, (-1000, -1000))
    col = mix_rgb(nt, 'MIX', fw, col, fcol, (-700, 0))
    # the body mask (red: flattened, green: rim)
    mm = node(nt, "ShaderNodeMapping", (-2200, 900)); mm.inputs["Location"].default_value = (0.5, 0.6 / MASK_W, 0); mm.inputs["Scale"].default_value = (1 / MASK_W, 1 / MASK_W, 1)
    nt.links.new(co, mm.inputs["Vector"])
    # Mapping is scale-then-translate: (x / W + 0.5, y / W + 0.6 / W)
    mt = node(nt, "ShaderNodeTexImage", (-1900, 900)); mt.image = IMG_MASK; mt.extension = 'CLIP'; nt.links.new(mm.outputs["Vector"], mt.inputs["Vector"])
    ms = sep_xyz(nt, mt.outputs["Color"], (-1650, 900))
    streak = noise_(nt, mm.outputs["Vector"], 60.0, 3, 0.5, 0.0, (-1650, 1150))
    flat = mix_rgb(nt, 'MIX', maprange(nt, streak.outputs["Fac"], 0.3, 0.7, 0, 1), c4(srgb((0.50, 0.52, 0.26))), c4(srgb((0.58, 0.58, 0.32))), (-1200, 1000))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', ms.outputs["X"], 0.85), col, flat, (-400, 200))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', ms.outputs["Y"], 0.35), col, (0.55, 0.62, 0.45, 1), (-250, 200))
    # the road: bare trodden earth with two wheel ruts' worth of darker mud
    rd = node(nt, "ShaderNodeAttribute", (-1000, 600)); rd.attribute_name = "road"; rd.attribute_type = 'GEOMETRY'
    roadc = mix_rgb(nt, 'MIX', maprange(nt, n3.outputs["Fac"], 0.3, 0.7, 0, 1), c4(srgb((0.38, 0.33, 0.24))), c4(srgb((0.47, 0.42, 0.31))), (-700, 650))
    col = mix_rgb(nt, 'MIX', maprange(nt, rd.outputs["Fac"], 0.2, 0.8, 0, 1, (-500, 600)), col, roadc, (-100, 300))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    b.inputs["Specular IOR Level"].default_value = 0.18
    hgt = math_(nt, 'ADD', math_(nt, 'MULTIPLY', n3.outputs["Fac"], 0.6), math_(nt, 'MULTIPLY', ms.outputs["Y"], 0.6), (-300, -500))
    bump_from(nt, b, hgt, 0.35, 0.01, (0, -500))
    return m


M_GROUND = ground_mat("M_GroundNear")
M_FARGROUND = M_GROUND.copy(); M_FARGROUND.name = "M_FarLand"

M_TURF = None
GREENS = [tuple(c) for c in [(0.24, 0.33, 0.11), (0.28, 0.37, 0.13), (0.21, 0.30, 0.10), (0.32, 0.40, 0.15), (0.26, 0.35, 0.12)]]
TIPS = [tuple(c) for c in [(0.38, 0.45, 0.19), (0.42, 0.48, 0.21), (0.35, 0.42, 0.17)]]
STRAW = [tuple(c) for c in [(0.66, 0.60, 0.40), (0.60, 0.53, 0.35)]]


def flowers_row(cv, R, c, x0, base):
    """row 3: short tufts with daisies and clover heads, and (cell 3) blades laid flat (the pressed grass)."""
    if c == 3:
        for i in range(70):
            by = 768 + R.uniform(30, 250); bx = x0 + R.uniform(10, 40)
            S.blade(cv, bx, by, R.uniform(140, 230), math.pi / 2 + R.gauss(0, 0.12), R.gauss(0, 0.2), R.uniform(3.0, 4.4),
                    R.choice(GREENS), R.choice(TIPS + STRAW))
        return
    for i in range(60):
        bx = x0 + 128 + R.gauss(0, 34)
        ex, ey = S.blade(cv, bx, base, R.uniform(60, 170), R.gauss(0, 0.35), R.gauss(0, 0.5), R.uniform(2.6, 4.0), R.choice(GREENS), R.choice(TIPS))
        if R.random() < 0.22:
            if c == 1:   # clover head
                for k in range(7): cv.ellipse(ex + R.gauss(0, 2.5), ey + R.gauss(0, 2.5), 2.6, 2.0, R.uniform(0, 3), (0.85, 0.80, 0.86, 1.0))
            else:        # daisy
                for k in range(8):
                    a = k / 8 * 2 * math.pi
                    cv.ellipse(ex + math.cos(a) * 4, ey + math.sin(a) * 2.2, 3.2, 1.2, a, (0.95, 0.94, 0.90, 1.0))
                cv.ellipse(ex, ey, 2.2, 1.6, 0, (0.90, 0.72, 0.15, 1.0))


print("painting atlases ...", flush=True)
IMG_GRASS = S.grass_atlas("A_TurfCards", GREENS, TIPS, STRAW, seed=11, dead_share=0.06, short_len=(70, 200), row3=flowers_row)
M_GRASS = image_mat("M_TurfCards", IMG_GRASS, rough=0.9, alpha=True, spec=0.25)
OAK_PAL = [tuple(c) for c in [(0.28, 0.38, 0.14), (0.33, 0.42, 0.15), (0.24, 0.33, 0.12), (0.38, 0.45, 0.17), (0.30, 0.36, 0.13)]]
IMG_LEAF = S.spray_atlas("A_WoodSprays", OAK_PAL, 21, S=1024, per_cell=3, nper=5, size=13.0, shape='oak')
M_LEAF = image_mat("M_WoodSprays", IMG_LEAF, rough=0.8, alpha=True, spec=0.3)
M_BARK = S.bark_mat("M_Bark", scale=6.0)
M_HEDGE = noisy("M_HedgeMass", [srgb((0.18, 0.27, 0.09)), srgb((0.25, 0.35, 0.12)), srgb((0.34, 0.41, 0.16))], scale=30.0, rough=0.8, bump=0.6, bump_dist=0.01)
M_TIMBER = wood("M_Timber", base=srgb((0.62, 0.52, 0.38)), dark=srgb((0.40, 0.32, 0.22)), light=srgb((0.75, 0.66, 0.52)), scale=6.0, rough=(0.6, 0.85), ao=0.0, bump=0.2)
M_CORD = noisy("M_Packthread", [srgb((0.70, 0.64, 0.50)), srgb((0.62, 0.55, 0.42)), srgb((0.78, 0.72, 0.58))], scale=300.0, rough=0.9, bump=0.0)
M_IRON = noisy("M_Iron", [srgb((0.20, 0.19, 0.18)), srgb((0.30, 0.22, 0.16)), srgb((0.14, 0.13, 0.13))], scale=80.0, rough=(0.5, 0.8), metallic=0.6, bump=0.1)
M_WICKER = noisy("M_Wicker", [srgb((0.62, 0.48, 0.28)), srgb((0.50, 0.37, 0.20)), srgb((0.70, 0.56, 0.34))], scale=200.0, rough=0.75, bump=0.5, stretch=(1, 1, 5))
M_LOAF = noisy("M_Loaves", [srgb((0.70, 0.48, 0.24)), srgb((0.55, 0.34, 0.16)), srgb((0.80, 0.62, 0.36))], scale=150.0, rough=0.7, bump=0.3)
M_MEAT = noisy("M_Joints", [srgb((0.52, 0.30, 0.18)), srgb((0.40, 0.20, 0.12)), srgb((0.66, 0.44, 0.28))], scale=200.0, rough=0.5, bump=0.2)
M_STONE = noisy("M_CityStone", [srgb((0.70, 0.66, 0.58)), srgb((0.62, 0.58, 0.50)), srgb((0.78, 0.74, 0.66))], scale=4.0, rough=0.85, bump=0.0)
M_ROOF = noisy("M_CityRoofs", [srgb((0.55, 0.30, 0.22)), srgb((0.45, 0.25, 0.20)), srgb((0.50, 0.46, 0.44))], scale=2.0, rough=0.8, bump=0.0)
M_FLAG = plain("M_Pennant", srgb((0.72, 0.16, 0.12)), rough=0.8, sheen=0.4)
M_FLETCH = plain("M_Fletching", srgb((0.86, 0.84, 0.78)), rough=0.85)
M_SKY = S.sky_mat(zenith=srgb((0.30, 0.50, 0.80)), horizon=srgb((0.80, 0.84, 0.86)), ground=srgb((0.40, 0.45, 0.32)), sun_dir=SUN_DIR,
                  glow=srgb((1.0, 0.86, 0.62)), glow_k=0.7, glow_pow=8.0, clouds=0.28, cloud_col=srgb((0.98, 0.96, 0.92)),
                  cloud_dark=srgb((0.66, 0.70, 0.78)), cloud_scale=0.8, land=srgb((0.52, 0.60, 0.62)), land_h=0.012, strength=1.0)

# ----------------------------------------------------------------------------- terrain: near disc (to 10 m) and far ring
print("terrain ...", flush=True)
near = S.polar_terrain("GroundNear", h, M_GROUND, r_max=10.0, r0=0.05, rings=40, seg=96, uv_disc=True)
far = S.polar_terrain("FarLand", h, M_FARGROUND, r_max=420.0, r0=10.0, rings=24, seg=96, r_min=10.0, uv_disc=True)
for o in (near,):   # the road weight as a vertex attribute the ground shader reads
    me = o.data; at = me.attributes.new("road", 'FLOAT', 'POINT')
    far.data.attributes.new("road", 'FLOAT', 'POINT')
    at.data.foreach_set("value", [0.0 for v in me.vertices])   # the road is its own strip now (finer than this mesh)

# the road beyond the near disc: a strip of trodden earth a little above the turf (seven Lilliputian feet wide)
M_ROAD = noisy("M_Road", [srgb((0.42, 0.33, 0.22)), srgb((0.50, 0.41, 0.29)), srgb((0.36, 0.30, 0.20))], scale=3.0, rough=0.95, bump=0.3, bump_dist=0.01)
rmb = MB()
pts = []
for i in range(len(ROAD) - 1):
    a_, b_ = Vector(ROAD[i]), Vector(ROAD[i + 1]); n = max(1, int((b_ - a_).length / (0.4 if a_.length < 12 else 1.5)))
    for k in range(n): pts.append(a_.lerp(b_, k / n))
pts.append(Vector(ROAD[-1]))
pts = [p for p in pts if p.y > 2.9]
prev = None
for i, p in enumerate(pts):
    d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized(); sd = Vector((-d.y, d.x)) * (0.32 + 0.003 * p.length)
    l = Vector((p.x + sd.x, p.y + sd.y, 0)); r_ = Vector((p.x - sd.x, p.y - sd.y, 0))
    l.z = h(l.x, l.y) + 0.008 + 0.0004 * p.length; r_.z = h(r_.x, r_.y) + 0.008 + 0.0004 * p.length
    cur = (rmb.vert(l, (0, i)), rmb.vert(r_, (1, i)))
    if prev: rmb.face(prev[0], prev[1], cur[1], cur[0])
    prev = cur
rmb.build("RoadFar", M_ROAD, sway=False)

# ----------------------------------------------------------------------------- the turf: short grass cards (near), flattened blades in the patch
print("grass ...", flush=True)
mb = MB(); R = random.Random(5)
placed = 0
for i in range(40000):
    r = 5.0 * R.random() ** 0.85
    a = R.uniform(0, 2 * math.pi); x, y = r * math.sin(a), r * math.cos(a)
    if r < 0.45: continue
    sd = body_sdf(x, y)
    if road_dist(x, y) < 0.3: continue
    if -2.6 < x < -0.8 and 0.4 < y < 2.9: continue                         # under the engine
    z = h(x, y)
    clump = 0.5 + 0.5 * n2(x, y, 0.9, 4.0)
    if sd < -0.03: continue           # inside the impression the blades lie flat (in the ground texture)
    if sd < 0.0 and R.random() < 0.6: continue
    if R.random() > (clump ** 1.2) * 1.0 + 0.5: continue
    sc = R.uniform(0.55, 0.9) * (0.75 + 0.4 * clump) * (1.0 + 0.3 * smoothstep(2.5, 6.0, r))
    if sd < 0.08: sc *= 1.25                                              # the rim, pushed up
    to_r = Vector((-x, -y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + R.gauss(0, 0.5)
    right = Vector((math.cos(ya), math.sin(ya), 0)) * 0.13 * sc
    up = Vector((0, 0, 0.05 * sc)) - to_r * 0.006 * sc
    cell = R.choice(S.GRASS_SHORT) if R.random() < 0.8 else R.choice(S.GRASS_ROW3[:3])
    card(mb, (x, y, z - 0.01), right, up, cell, 0.0, 1.0)
    placed += 1
    if placed > 3300: break
grass = mb.build("veg_grass", M_GRASS)
set_card_normals(grass, lambda p: Vector((0, 0, 1)))
print("grass cards", placed, flush=True)

# ----------------------------------------------------------------------------- pegs and cut packthread
print("pegs ...", flush=True)
pegs = MB(); cords = []
def peg(x, y, pulled=False, lean=(0.0, 0.0)):
    """a small iron peg (Lilliputian tent peg): a square shank with a hooked head, driven in, or wrenched out lying."""
    z = h(x, y)
    if pulled:
        a = rng.uniform(0, math.pi * 2); d = Vector((math.cos(a), math.sin(a), 0))
        p0 = Vector((x, y, z + 0.004)); p1 = p0 + d * 0.06
        tube_mb(pegs, [p0, p1], [0.0035, 0.002], 4)
        tube_mb(pegs, [p0, p0 + Vector((-d.y, d.x, 0)) * 0.012], [0.003, 0.003], 4)
        return p0
    top = Vector((x + lean[0], y + lean[1], z + 0.028))
    tube_mb(pegs, [Vector((x, y, z - 0.01)), top], [0.0035, 0.003], 4)
    tube_mb(pegs, [top + Vector((-0.008, 0, 0)), top + Vector((0.008, 0, 0.002))], [0.0028, 0.0028], 4)
    return top


def tube_mb(mb, pts, radii, sides):
    pts = [Vector(p) for p in pts]; rings = []
    up = None
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        if up is None:
            ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0)); up = d.cross(ref).normalized()
        else: up = (up - d * up.dot(d)).normalized()
        v = d.cross(up); r = radii[min(i, len(radii) - 1)] if isinstance(radii, (list, tuple)) else radii
        rings.append([mb.vert(p + (up * math.cos(2 * math.pi * k / sides) + v * math.sin(2 * math.pi * k / sides)) * r, (k / sides, i / len(pts))) for k in range(sides)])
    for ra, rb in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides; mb.face(ra[k], ra[j], rb[j], rb[k])


def cord(p0, p1, slack=0.02, n=8, lie=True):
    """packthread from p0 to p1; lying in the grass (follows the ground) or sagging."""
    pts = []
    for i in range(n + 1):
        t = i / n; q = Vector(p0).lerp(Vector(p1), t)
        q.x += 0.012 * noise.noise(Vector((q.x * 30, q.y * 30, 2.0))); q.y += 0.012 * noise.noise(Vector((q.x * 30, q.y * 30, 5.0)))
        if lie and 0 < i < n: q.z = h(q.x, q.y) + 0.003
        else: q.z -= slack * math.sin(math.pi * t)
        pts.append(q)
    cords.append(pts)


# pegs round the outline: arms and legs fastened on each side, the hair at the head; ligatures across the body
outline = []
for side in (-1, 1):
    for k in range(7):         # beside the arm
        y = 0.92 + k * 0.1; x = side * (0.37 + 0.04 * (k % 2)) + (side < 0) * (-0.08 - 0.02 * k)
        outline.append((x, y, side, "arm"))
    for k in range(7):         # beside the leg
        y = 1.55 + k * 0.11; x = side * (0.25 + 0.02 * k)
        outline.append((x, y, side, "leg"))
for k in range(11):            # the hair: a fan of pegs round the head
    a = math.radians(-150 + k * 30 * 1.0) * 0.9
    outline.append((HEAD.x + math.sin(a) * 0.24, HEAD.y - 0.02 + math.cos(a + math.pi) * 0.2 - 0.02, 1 if math.sin(a) > 0 else -1, "hair"))
for (x, y, side, kind) in outline:
    pulled = side < 0 and kind in ("arm", "hair") and rng.random() < 0.7    # left arm wrenched free, hair on the left loosened
    top = peg(x, y, pulled)
    if pulled:
        cord(top, top + Vector((rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), 0)), lie=True, n=4)   # a broken end
        continue
    # the string ran over the limb to the peg on the other side; now cut, a loose end lies in toward the body
    tgt = Vector((x * rng.uniform(0.15, 0.45), y + rng.uniform(-0.06, 0.06), 0))
    cord(top, tgt, lie=True, n=6)
# the slender ligatures across the body, armpits to thighs: pegs well out on each side, cut in the middle
for k in range(6):
    y = 0.92 + k * 0.12
    for side in (-1, 1):
        x = side * (0.55 + 0.05 * rng.random())
        top = peg(x, y)
        cord(top, (side * rng.uniform(0.05, 0.2), y + rng.uniform(-0.05, 0.05), 0), n=7)
cm = MB()
for pts in cords: tube_mb(cm, pts, 0.0011, 3)
cm.build("Cords", M_CORD, sway=False)
pegs.build("Pegs", M_IRON, sway=False)

# ----------------------------------------------------------------------------- spent arrows "like so many needles", mostly by where the left hand lay
arr = MB(); fl = MB()
for i in range(240):
    if i < 150: c = Vector((-0.42 + rng.gauss(0, 0.22), 1.25 + rng.gauss(0, 0.35)))
    else: c = Vector((rng.gauss(0, 0.5), rng.uniform(0.3, 2.4)))
    if math.hypot(c.x, c.y) < 0.35: continue
    a = rng.uniform(0, 2 * math.pi); d = Vector((math.cos(a), math.sin(a), 0))
    z = h(c.x, c.y)
    stuck = rng.random() < 0.3
    L = rng.uniform(0.045, 0.06)
    if stuck:   # standing in the turf at an angle
        dd = (d * 0.6 + Vector((0, 0, 1.0))).normalized(); p0 = Vector((c.x, c.y, z - 0.008)); p1 = p0 + dd * L
    else:
        p0 = Vector((c.x, c.y, z + 0.004)); p1 = p0 + d * L + Vector((0, 0, 0.003))
    tube_mb(arr, [p0, p1], [0.0006, 0.0006], 3)
    tail = p1; dirv = (p1 - p0).normalized(); side = dirv.cross(Vector((0, 0, 1)))
    if side.length < 0.1: side = Vector((1, 0, 0))
    side.normalize()
    q = [tail - dirv * 0.012 - side * 0.002, tail - dirv * 0.012 + side * 0.002, tail + side * 0.002, tail - side * 0.002]
    vs = [fl.vert(p) for p in q]; fl.face(*vs)
arr.build("Arrows", M_TIMBER, sway=False)
fl.build("Fletching", M_FLETCH, sway=False)

# ----------------------------------------------------------------------------- ladders
lad = MB()
def ladder(p0, p1, width=0.045, rung=0.025):
    p0 = Vector(p0); p1 = Vector(p1); d = (p1 - p0); L = d.length; d.normalize()
    side = d.cross(Vector((0, 0, 1)))
    if side.length < 0.1: side = Vector((1, 0, 0))
    side.normalize()
    for s in (-1, 1):
        off = side * s * width / 2
        tube_mb(lad, [p0 + off, p1 + off], [0.0035, 0.003], 4)
    n = int(L / rung)
    for k in range(1, n):
        q = p0 + d * (k * rung)
        tube_mb(lad, [q - side * width / 2, q + side * width / 2], 0.0018, 3)


# the ladders applied to his sides, now lying along the flanks
for (x0, y0, x1, y1) in [(0.62, 0.95, 0.42, 1.38), (0.66, 1.62, 0.38, 1.9), (-0.68, 1.05, -0.5, 1.5), (-0.62, 1.78, -0.36, 2.02), (0.5, 0.62, 0.32, 0.78)]:
    ladder((x0, y0, h(x0, y0) + 0.006), (x1, y1, h(x1, y1) + 0.006))
# one still propped against a tussock at the right shoulder
ladder((0.62, 0.78, h(0.62, 0.78)), (0.40, 0.82, h(0.40, 0.82) + 0.12))
lad.build("Ladders", M_TIMBER, sway=False)

# ----------------------------------------------------------------------------- the stage by the right ear, four yards off
print("stage ...", flush=True)
ST = Vector((3.05, 1.75, 0.0)); ST.z = h(ST.x, ST.y)
stg = MB()
SW, SD_, SH = 0.40, 0.30, 0.457
def beam(p0, p1, w, t):
    tube_mb(stg, [p0, p1], w, 4)
for sx in (-1, 1):
    for sy in (-1, 1):
        x, y = ST.x + sx * SW / 2 * 0.9, ST.y + sy * SD_ / 2 * 0.9
        beam(Vector((x, y, h(x, y) - 0.02)), Vector((x, y, ST.z + SH)), 0.008, 0)
for sx in (-1, 1):        # cross bracing
    x = ST.x + sx * SW / 2 * 0.9
    beam(Vector((x, ST.y - SD_ * 0.45, ST.z + 0.05)), Vector((x, ST.y + SD_ * 0.45, ST.z + SH - 0.05)), 0.004, 0)
for sy in (-1, 1):
    y = ST.y + sy * SD_ / 2 * 0.9
    beam(Vector((ST.x - SW * 0.45, y, ST.z + SH - 0.05)), Vector((ST.x + SW * 0.45, y, ST.z + 0.05)), 0.004, 0)
stg.build("StageFrame", M_TIMBER, sway=False)
# deck of planks and a low rail on three sides
for k in range(8):
    x = ST.x - SW / 2 + (k + 0.5) * SW / 8
    box(f"Plank{k}", (SW / 8 - 0.003, SD_ + 0.02, 0.012), (x, ST.y, ST.z + SH + 0.006), M_TIMBER, rot=(0, rng.gauss(0, 0.01), 0))
rail = MB()
for (a, b_) in [((-1, 1), (1, 1)), ((1, 1), (1, -1)), ((-1, 1), (-1, -1))]:
    p0 = Vector((ST.x + a[0] * SW / 2, ST.y + a[1] * SD_ / 2, ST.z + SH + 0.012)); p1 = Vector((ST.x + b_[0] * SW / 2, ST.y + b_[1] * SD_ / 2, ST.z + SH + 0.012))
    tube_mb(rail, [p0 + Vector((0, 0, 0.07)), p1 + Vector((0, 0, 0.07))], 0.003, 4)
    for t in (0.0, 0.5, 1.0):
        q = p0.lerp(p1, t); tube_mb(rail, [q, q + Vector((0, 0, 0.07))], 0.003, 4)
rail.build("StageRail", M_TIMBER, sway=False)
lad = MB()
for (dx, dy) in [(-0.05, -0.15), (0.12, -0.16)]:        # ladders up the side toward the reader and the patch
    top = Vector((ST.x + dx, ST.y - SD_ / 2, ST.z + SH)); foot = Vector((ST.x + dx - 0.02, ST.y - SD_ / 2 - 0.2, 0)); foot.z = h(foot.x, foot.y)
    ladder(foot, top)
top = Vector((ST.x - SW / 2, ST.y + 0.05, ST.z + SH)); foot = Vector((ST.x - SW / 2 - 0.21, ST.y + 0.08, 0)); foot.z = h(foot.x, foot.y); ladder(foot, top)
lad.build("StageLadders", M_TIMBER, sway=False)
# the pennant on a staff at the stage's back corner
fp = Vector((ST.x + SW / 2 - 0.01, ST.y + SD_ / 2 - 0.01, ST.z + SH))
cyl("Staff", 0.003, 0.32, tuple(fp + Vector((0, 0, 0.16))), M_TIMBER, verts=5)
fm = MB()
for i in range(6):
    t0, t1 = i / 6, (i + 1) / 6
    def fpt(t, up):
        return fp + Vector((-0.12 * t, 0.02 * math.sin(t * 5), 0.3 - 0.07 * (1 - up) * (1 - 0.6 * t) - 0.0))
    a = fm.vert(fpt(t0, 1), (t0, 1), t0); b_ = fm.vert(fpt(t1, 1), (t1, 1), t1); c_ = fm.vert(fpt(t1, 0), (t1, 0), t1); d_ = fm.vert(fpt(t0, 0), (t0, 0), t0)
    fm.face(a, b_, c_, d_)
fm.build("cloth.flag.stage", M_FLAG)

# ----------------------------------------------------------------------------- baskets of meat, loaves, two empty hogsheads (by the right hand)
print("baskets ...", flush=True)
def basket(x, y, rx=0.03, hgt=0.028, tipped=False, seed=0):
    z = h(x, y); R2 = random.Random(seed)
    o = lathe(f"Basket{seed}", [(rx * 0.75, 0.0), (rx * 0.9, hgt * 0.4), (rx, hgt), (rx * 1.04, hgt * 1.05), (rx * 0.95, hgt * 1.08), (rx * 0.85, hgt * 0.3)],
              (x, y, z + 0.002), M_WICKER, steps=14)
    if tipped: o.rotation_euler = (math.radians(80), 0, R2.uniform(0, 6.28)); o.location.z += rx * 0.9
    # a bail handle
    hp = [Vector((x - rx, y, z + hgt)), Vector((x - rx * 0.7, y, z + hgt + rx * 0.7)), Vector((x, y, z + hgt + rx)), Vector((x + rx * 0.7, y, z + hgt + rx * 0.7)), Vector((x + rx, y, z + hgt))]
    if not tipped: tube(f"Bail{seed}", hp, 0.0018, M_WICKER, sides=4, caps=False)
    return z + hgt
food = MB()
for i, (x, y, tp) in enumerate([(0.42, 0.72, False), (0.50, 0.66, False), (0.46, 0.80, True), (-0.36, 0.62, False), (0.30, 0.50, False)]):
    top = basket(x, y, tipped=tp, seed=i)
    if not tp:
        for k in range(5):     # loaves "about the bigness of musket bullets", joints smaller than a lark's wing
            q = Vector((x + rng.gauss(0, 0.012), y + rng.gauss(0, 0.012), top - 0.002))
            sp = 0.007 if k < 3 else 0.006
            K.sphere(f"Loaf{i}_{k}", sp, tuple(q), M_LOAF if k < 3 else M_MEAT, seg=8, scale=(1, 0.85, 0.75))
    else:
        for k in range(6):
            a = rng.uniform(-0.6, 0.6); dd = rng.uniform(0.03, 0.09)
            q = Vector((x + math.cos(a) * dd, y + math.sin(a) * dd, 0)); q.z = h(q.x, q.y) + 0.005
            K.sphere(f"Spill{i}_{k}", 0.007, tuple(q), M_LOAF, seg=8, scale=(1, 0.85, 0.75))
M_STAVE = wood("M_Staves", base=srgb((0.55, 0.40, 0.25)), dark=srgb((0.35, 0.24, 0.14)), light=srgb((0.68, 0.52, 0.34)), scale=10.0, rough=(0.5, 0.8), ao=0.0, bump=0.2)
def hogshead(name, loc, rot, open_top=True):
    prof = [(0.030, 0.0), (0.036, 0.025), (0.038, 0.05), (0.036, 0.075), (0.030, 0.10)]
    o = lathe(name, prof, loc, M_STAVE, steps=16); o.rotation_euler = rot
    for k, zz in enumerate((0.012, 0.03, 0.07, 0.088)):
        r_ = 0.0316 + 0.0055 * math.sin(math.pi * zz / 0.1)
        hp = K.lathe(f"{name}_hoop{k}", [(r_ + 0.0012, zz - 0.003), (r_ + 0.0014, zz), (r_ + 0.0012, zz + 0.003)], loc, M_IRON, steps=16)
        hp.rotation_euler = rot
    return o
# thrown down: one on its side by the right shoulder, one upright further off, its head beaten out
hogshead("HogsheadA", (0.78, 0.92, h(0.78, 0.92) + 0.035), (math.radians(90), 0, math.radians(35)))
hogshead("HogsheadB", (1.05, 0.48, h(1.05, 0.48) - 0.004), (0, math.radians(4), 0))
K.lathe("HogsheadB_head", [(0.03, -0.002), (0.03, 0.002)], (1.12, 0.40, h(1.12, 0.40) + 0.002), M_STAVE, steps=12)

# ----------------------------------------------------------------------------- the engine: 7 x 4 ft frame, 3 in high, 22 wheels; poles bundled
print("engine ...", flush=True)
EC = Vector((-1.70, 1.55, 0.0)); EL, EW = 2.13, 1.22
eng = MB(); whl = MB()
ez = h(EC.x, EC.y) + 0.075
ang = math.radians(4)
def ep(u, v, dz=0.0):
    c, s_ = math.cos(ang), math.sin(ang)
    return Vector((EC.x + u * c - v * s_, EC.y + u * s_ + v * c, ez + dz))
# two side rails, end rails, cross members, a slatted bed
for u in (-EW / 2, EW / 2):
    tube_mb(eng, [ep(u, -EL / 2), ep(u, EL / 2)], 0.022, 4)
for v in (-EL / 2, EL / 2):
    tube_mb(eng, [ep(-EW / 2, v), ep(EW / 2, v)], 0.02, 4)
for k in range(1, 10):
    v = -EL / 2 + k * EL / 10
    tube_mb(eng, [ep(-EW / 2, v, 0.012), ep(EW / 2, v, 0.012)], 0.012, 4)
for k in range(14):
    u = -EW / 2 + (k + 0.5) * EW / 14
    tube_mb(eng, [ep(u, -EL / 2, 0.026), ep(u, EL / 2, 0.026)], 0.008, 4)
# axles and 22 wheels: 11 a side
for k in range(11):
    v = -EL / 2 + 0.06 + k * (EL - 0.12) / 10
    tube_mb(eng, [ep(-EW / 2 - 0.03, v, -0.035), ep(EW / 2 + 0.03, v, -0.035)], 0.006, 4)
    for u in (-EW / 2 - 0.035, EW / 2 + 0.035):
        c0 = ep(u, v, -0.035)
        ax = Vector((math.cos(ang), math.sin(ang), 0))
        prof = []
        for j in range(12):
            a = 2 * math.pi * j / 12
            prof.append(Vector((0, math.cos(a), math.sin(a))))
        ring_o = []; ring_i = []
        up = Vector((0, 0, 1)); fwd = ax.cross(up)
        for j in range(12):
            a = 2 * math.pi * j / 12; dvec = fwd * math.cos(a) + up * math.sin(a)
            ring_o.append((whl.vert(c0 + dvec * 0.042 - ax * 0.01), whl.vert(c0 + dvec * 0.042 + ax * 0.01)))
        for j in range(12):
            j2 = (j + 1) % 12
            whl.face(ring_o[j][0], ring_o[j2][0], ring_o[j2][1], ring_o[j][1])
        for sgn in (-1, 1):
            cc = whl.vert(c0 + ax * 0.01 * sgn)
            for j in range(12):
                j2 = (j + 1) % 12
                i0 = 0 if sgn < 0 else 1
                if sgn < 0: whl.face(cc, ring_o[j2][i0], ring_o[j][i0])
                else: whl.face(cc, ring_o[j][i0], ring_o[j2][i0])
# the eighty poles, a foot high, bundled on the bed in four stacks, with hooks; coils of cord and pulleys
for st in range(4):
    v0 = -EL / 2 + 0.25 + st * 0.52
    for k in range(20):
        u = -0.16 + (k % 7) * 0.05 + rng.gauss(0, 0.004); lay = k // 7
        p0 = ep(u, v0 - 0.15, 0.04 + lay * 0.012); p1 = ep(u + rng.gauss(0, 0.01), v0 + 0.15, 0.04 + lay * 0.012)
        tube_mb(eng, [p0, p1], 0.006, 4)
for (u, v) in [(0.35, -0.6), (0.36, 0.3), (-0.4, 0.75)]:
    c0 = ep(u, v, 0.05)
    pts = [c0 + Vector((math.cos(t) * 0.05, math.sin(t) * 0.05, 0.004 * t)) for t in np.linspace(0, 6 * math.pi, 40)]
    tube(f"Coil{u}{v}", pts, 0.0025, M_CORD, sides=3, caps=False)
eng.build("EngineFrame", M_TIMBER, sway=False)
whl.build("EngineWheels", M_STAVE, sway=False)
# ruts where it came over the turf from the road
rut = MB()

# ----------------------------------------------------------------------------- hedges round the 40-foot fields, beyond the common
print("hedges and woods ...", flush=True)
hm = MB()
CA, SA = math.cos(math.radians(18)), math.sin(math.radians(18))
def to_world(u, v): return (u * CA - v * SA, u * SA + v * CA)
def hedge_run(p0, p1, R2):
    L = math.dist(p0, p1); n = max(2, int(L / (0.7 if math.hypot(*p0) < 20 else 1.4)))
    d = Vector((p1[0] - p0[0], p1[1] - p0[1], 0)).normalized(); sd = Vector((-d.y, d.x, 0))
    rows = []
    for i in range(n + 1):
        t = i / n; x = p0[0] + (p1[0] - p0[0]) * t; y = p0[1] + (p1[1] - p0[1]) * t
        z = h(x, y); hh = 0.20 + 0.06 * noise.noise(Vector((x * 1.3, y * 1.3, 0.5))) + 0.03 * R2.random()
        w = 0.10 + 0.03 * noise.noise(Vector((x * 2.1, y * 2.1, 1.5)))
        prof = [(-w, -0.02), (-w * 1.1, hh * 0.6), (0, hh), (w * 1.1, hh * 0.6), (w, -0.02)]
        rows.append([hm.vert(Vector((x, y, z)) + sd * a + Vector((0, 0, b_)), (t * L, k / 4), 0.0) for k, (a, b_) in enumerate(prof)])
    for ra, rb in zip(rows, rows[1:]):
        for k in range(len(ra) - 1): hm.face(ra[k], rb[k], rb[k + 1], ra[k + 1])
R2 = random.Random(9)
for gi in range(-8, 9):
    for gj in range(-6, 12):
        for horiz in (0, 1):
            u0, v0 = gi * 12.0, gj * 12.5
            a_ = (u0, v0); b_ = (u0 + 12.0, v0) if horiz else (u0, v0 + 12.5)
            wa, wb = to_world(*a_), to_world(*b_)
            mx, my = (wa[0] + wb[0]) / 2, (wa[1] + wb[1]) / 2
            r = math.hypot(mx, my)
            if r < 7.6 or r > 48: continue
            if math.hypot(mx - CITY.x, my - CITY.y) < 18 or math.hypot(mx - HAMLET.x, my - HAMLET.y) < 1.8: continue
            if r > 30 and R2.random() < 0.18: continue
            if road_dist(mx, my) < 1.0:   # gap where the road passes
                continue
            # leave a gate gap
            g = R2.uniform(0.2, 0.7)
            hedge_run(wa, (wa[0] + (wb[0] - wa[0]) * g, wa[1] + (wb[1] - wa[1]) * g), R2)
            hedge_run((wa[0] + (wb[0] - wa[0]) * (g + 0.08), wa[1] + (wb[1] - wa[1]) * (g + 0.08)), wb, R2)
hm.build("veg.shrub.hedges", M_HEDGE, sway=True)

# little woods of seven-foot trees and a few hedgerow trees
woods = [(-11.0, 13.0, 2.6, 8), (-15.0, -5.0, 3.0, 7), (17.0, -7.0, 2.5, 5), (-24.0, 26.0, 4.0, 7), (27.0, 26.0, 4.0, 6), (-6.0, -17.0, 3.0, 5), (-30.0, 6.0, 3.5, 5)]
ti = 0
for (wx, wy, wr, n) in woods:
    for k in range(n):
        a = rng.uniform(0, 2 * math.pi); d = wr * math.sqrt(rng.random())
        x, y = wx + math.cos(a) * d, wy + math.sin(a) * d
        H_ = rng.uniform(0.7, 2.1); far_ = math.hypot(x, y) > 14
        S.tree(f"T{ti}", (x, y, h(x, y)), H_, H_ * 0.32, rng.choice(("oak", "elm", "ash", "lime")), 100 + ti, M_BARK, M_LEAF,
               nlimbs=4 if far_ else 5, detail=0.3 if far_ else 0.6, cards_per_tip=1, card_size=H_ * (0.2 if far_ else 0.16), fill=10 if far_ else 16)
        ti += 1
for (x, y, H_) in [(-8.2, 8.6, 1.3), (6.2, 13.8, 2.0), (9.6, -4.2, 0.9), (-9.0, -1.0, 1.6), (12.5, 4.0, 1.1)]:
    S.tree(f"T{ti}", (x, y, h(x, y)), H_, H_ * 0.36, "oak", 200 + ti, M_BARK, M_LEAF, nlimbs=6, detail=0.6, cards_per_tip=2, card_size=H_ * 0.15, fill=26)
    ti += 1
print("trees", ti, flush=True)

# ----------------------------------------------------------------------------- Mildendo, far off on its rise: the wall two and a half feet high, towers
cw = MB()
def cbox(mb, c, sx, sy, sz, yaw=0.0):
    ca, sa = math.cos(yaw), math.sin(yaw)
    pts = []
    for dz in (0, sz):
        for (u, v) in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
            pts.append(mb.vert(Vector((c.x + u * ca - v * sa, c.y + u * sa + v * ca, c.z + dz))))
    for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        mb.face(*[pts[i] for i in f])
cr = MB()
def cottage(p, w, d, wh, yaw, wallmb=None, roofmb=None):
    """a Lilliputian cottage or town house: plastered walls, a pitched roof with eaves, a chimney (w, d full sizes)."""
    wallmb = wallmb or cw; roofmb = roofmb or cr
    p = Vector((p.x, p.y, h(p.x, p.y) - 0.02))
    cbox(wallmb, p, w / 2, d / 2, wh, yaw)
    Rm = Matrix.Rotation(yaw, 3, 'Z'); top = p + Vector((0, 0, wh)); rh = d * 0.5
    q = [top + Rm @ Vector(v) for v in ((-w / 2 - 0.02, -d / 2 - 0.03, -0.01), (w / 2 + 0.02, -d / 2 - 0.03, -0.01), (w / 2 + 0.02, 0, rh), (-w / 2 - 0.02, 0, rh),
                                         (-w / 2 - 0.02, d / 2 + 0.03, -0.01), (w / 2 + 0.02, d / 2 + 0.03, -0.01))]
    for f in ((0, 1, 2, 3), (5, 4, 3, 2)): roofmb.face(*[roofmb.vert(q[i]) for i in f])
    for (i0, i1, i2) in ((0, 3, 4), (1, 5, 2)): wallmb.face(wallmb.vert(q[i0] + Vector((0, 0, 0.01))), wallmb.vert(q[i1]), wallmb.vert(q[i2] + Vector((0, 0, 0.01))))
    cbox(wallmb, top + Rm @ Vector((w * 0.3, d * 0.15, 0)), 0.025, 0.025, rh * 0.95, yaw)
    # door and windows (dark) on the long side facing -y local
    for (u, z0, ww, hh_) in ((0.0, 0.0, 0.05, 0.09), (-w * 0.3, 0.07, 0.045, 0.045), (w * 0.3, 0.07, 0.045, 0.045)):
        c0 = p + Rm @ Vector((u, -d / 2 - 0.002, z0))
        a_ = Rm @ Vector((ww / 2, 0, 0))
        win.face(win.vert(c0 - a_), win.vert(c0 + a_), win.vert(c0 + a_ + Vector((0, 0, hh_))), win.vert(c0 - a_ + Vector((0, 0, hh_))))
win = MB()
side = 26.0
for k in range(4):
    a = k * math.pi / 2 + 0.3
    for j in range(9):
        t = (j - 4) / 4.5
        c = CITY + Vector((math.cos(a) * side / 2 - math.sin(a) * t * side / 2, math.sin(a) * side / 2 + math.cos(a) * t * side / 2, 0))
        c.z = h(c.x, c.y) - 0.05
        if j % 3 == 0: cbox(cw, c, 0.22, 0.22, 1.05, a); cbox(cr, c + Vector((0, 0, 1.05)), 0.25, 0.25, 0.06, a)
    cm_ = CITY + Vector((math.cos(a) * side / 2, math.sin(a) * side / 2, 0)); cm_.z = h(cm_.x, cm_.y) - 0.05
    cbox(cw, cm_, side / 2 * 1.02, 0.09, 0.76, a + math.pi / 2)
RC = random.Random(12)
for k in range(70):          # the town within: streets of houses two or three storeys (0.4-0.7 m), the palace in the middle
    c = CITY + Vector((RC.uniform(-11.5, 11.5), RC.uniform(-11.5, 11.5), 0))
    if abs(c.x - CITY.x) < 2.6 and abs(c.y - CITY.y) < 2.6: continue
    yaw = 0.3 + (math.pi / 2 if RC.random() < 0.5 else 0)
    cottage(c, RC.uniform(0.5, 0.9), RC.uniform(0.4, 0.55), RC.uniform(0.35, 0.65), yaw)
c = CITY.copy(); c.z = h(c.x, c.y)
cbox(cw, c, 2.2, 2.2, 1.1, 0.3); cbox(cr, c + Vector((0, 0, 1.1)), 2.3, 2.3, 0.12, 0.3)
for k in range(4):
    a = 0.3 + k * math.pi / 2 + math.pi / 4
    tc = c + Vector((math.cos(a) * 2.6, math.sin(a) * 2.6, 0)); cbox(cw, tc, 0.3, 0.3, 1.6, 0.3); cbox(cr, tc + Vector((0, 0, 1.6)), 0.36, 0.36, 0.3, 0.3)
# a hamlet near at hand on the right: cottages, a barn, a church with its spire
HAMLET_C = HAMLET
for k, (dx, dy, w, d, wh, yaw) in enumerate(((0.0, 0.0, 0.55, 0.42, 0.24, 0.1), (0.9, 0.5, 0.5, 0.4, 0.22, 0.25), (-0.8, 0.7, 0.6, 0.42, 0.25, -0.1),
                                             (0.3, 1.4, 0.48, 0.38, 0.22, 1.7), (1.6, -0.4, 0.8, 0.5, 0.3, 0.2), (-1.4, -0.2, 0.5, 0.4, 0.22, 0.05))):
    cottage(HAMLET + Vector((dx, dy, 0)), w, d, wh, yaw)
ch = HAMLET + Vector((-0.6, 2.6, 0)); ch.z = h(ch.x, ch.y)
cottage(ch, 1.1, 0.5, 0.42, 0.15)
tw_ = ch + Vector((-0.75, -0.1, 0)); cbox(cw, tw_, 0.13, 0.13, 0.95, 0.15)
sp = tw_ + Vector((0, 0, 0.95))
for k in range(4):
    a0, a1 = math.pi / 2 * k + 0.15 + math.pi / 4, math.pi / 2 * (k + 1) + 0.15 + math.pi / 4
    cr.face(cr.vert(sp + Vector((math.cos(a0) * 0.19, math.sin(a0) * 0.19, 0))), cr.vert(sp + Vector((math.cos(a1) * 0.19, math.sin(a1) * 0.19, 0))), cr.vert(sp + Vector((0, 0, 0.7))))
# a farm cart on the road and hay stooks in the field by the hamlet
cc = Vector((-2.3, 8.2, 0)); cc.z = h(cc.x, cc.y)
cbox(cw, cc + Vector((0, 0, 0.045)), 0.07, 0.13, 0.04, 0.05)
for sx in (-1, 1):
    for sy in (-1, 1): K.cyl(f"CartWheel{sx}{sy}", 0.035, 0.012, (cc.x + sx * 0.085, cc.y + sy * 0.08, cc.z + 0.035), M_TIMBER, verts=10, rot=(0, math.pi / 2, 0.05))
for k in range(14):
    p = HAMLET + Vector((-3.5 + (k % 5) * 0.55 + rng.uniform(-0.1, 0.1), -3.0 + (k // 5) * 0.6, 0)); p.z = h(p.x, p.y)
    K.lathe(f"Stook{k}", [(0.0, 0.0), (0.06, 0.0), (0.045, 0.07), (0.0, 0.1)], tuple(p), M_LOAF, steps=6)
win.build("TownWindows", M_IRON, sway=False)
cr.build("CityRoofs", M_ROOF, sway=False)
cw.build("CityWalls", M_STONE, sway=False)

# ----------------------------------------------------------------------------- sky, light, anchors, sounds
SKY = S.sky_dome(M_SKY, radius=900.0)
S.world(SUN_DIR, sun_energy=5.0, sun_col=(1.0, 0.87, 0.70), sun_angle=0.8,
        sky_cols=(srgb((0.30, 0.32, 0.25)), srgb((0.70, 0.78, 0.86)), srgb((0.30, 0.48, 0.80))), sky_strength=1.1)
eye, fwd = S.reader((0.0, 0.0, h(0, 0)), YAW)
anchor("scene.centre", (0.0, 1.3, h(0, 1.3)))
anchor("stage", tuple(ST))
anchor("engine", tuple(EC + Vector((0, 0, ez))))
anchor("city", tuple(CITY))
sound("crowd", "stage", (ST.x + 1.0, ST.y + 1.5, 0.3))
sound("crowd", "engine", (EC.x - 2.0, EC.y + 2.0, 0.3))
sound("wind", "common", (-6.0, 4.0, 1.0))
sound("birds", "wood", (-30.0, 38.0, 3.0))
sound("birds", "hedge", (20.0, 16.0, 1.5))
sound("wind-trees", "wood", (34.0, 52.0, 2.0))

page = S.page_preview(eye, fwd)
cams = S.view_cams(eye, YAW, extra=[
    ("Cam_Page", eye, eye + fwd * 10 + Vector((0, 0, -1.2)), 17),
    ("Cam_Patch", Vector((0.9, -0.5, h(0.9, -0.5) + 1.25)), Vector((-0.1, 1.3, h(0, 1.3))), 22),
    ("Cam_Stage", Vector((2.2, -0.4, h(2.2, -0.4) + 0.9)), ST + Vector((0, 0, 0.3)), 30),
    ("Cam_Aerial", Vector((-6.0, -8.0, 14.0)), Vector((6.0, 30.0, 0.0)), 24),
    ("Cam_Engine", Vector((-0.4, -0.4, h(-0.4, -0.4) + 1.1)), EC + Vector((0, 0, 0.05)), 26),
])

S.finish(ARGS, cams, "lilliput_binding_ground.gltf", page=page,
         keep_names={"M_TurfCards": "veg.grass.turf", "M_WoodSprays": "veg.crown.woods", "M_HedgeMass": "veg.shrub.hedges",
                     "M_Pennant": "cloth.flag.stage", "M_GroundNear": "GroundNear", "M_FarLand": "far.land"},
         keep_uv={"M_GroundNear", "M_FarLand"},
         size_for={"M_GroundNear": (2048, 512, 1024), "M_FarLand": (1024, 128), "M_SkyDome": (1024,), "M_Bark": (512, 128, 256),
                   "M_Timber": (512, 128, 256), "M_HedgeMass": (512, 128, 256), "M_CityStone": (128,), "M_CityRoofs": (64,),
                   "M_Pennant": (64,), "M_Fletching": (32,), "M_Iron": (128, 64), "M_Packthread": (128,), "M_Wicker": (256, 64, 128),
                   "M_Loaves": (64,), "M_Joints": (64,), "M_Staves": (256, 64, 128)},
         default_size=(256, 64, 128), no_shadow={"M_SkyDome"})
