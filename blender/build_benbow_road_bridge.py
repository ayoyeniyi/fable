"""
Fable step-in room: the road and the little bridge below the Admiral Benbow, a frosty moonlit January night
(Treasure Island, chapter 5, "The Last of the Blind Man").

"My mother and I ... I helped her to the edge of the bank, where, sure enough, I had to do it, and the bridge was
very low ... we were close behind the little bridge" ... "the moon shone quite clear on the high ground ... a thin veil
still lay in the exact bottom of the dell and round the tavern door" ... "Down went the door of the 'Admiral Benbow'"
... "the window of the captain's room was thrown open with a slam and a jingle of broken glass, and a man leaned out
into the moonlight" ... "one of the newcomers carried a lantern" ... "I crept back to the bank again ... under cover
of a great bush of broom."

The coast road runs down the dell from the Admiral Benbow, 35 m up the road, to the low rubble bridge over a little
stream; frosty hedgerows of bare thorn line it; the hillside rises behind the inn toward the hamlet. The inn's door
stands open on lamplight, the captain's upstairs window is thrown open and lit; the signboard hangs by the road. A
pirate's lantern lies where it was dropped in the road, still burning. A thin frost lies on everything.

Reader: on the bank below the road, by the bridge, beside the great broom bush, facing up the road to the inn.

Living-scene nodes: water.stream.dell (UV V runs downstream), veg.shrub.broom, veg.grass.frost, fx.lantern.road,
fx.lantern.innDoor, fx.candle.captainWindow, sound.river.stream, sound.wind.dell.

  blender -b -P blender/build_benbow_road_bridge.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_benbow_road_bridge.py -- --render --samples 48 --res 1280 --cams reader,left,right,behind,inn
  blender -b -P blender/build_benbow_road_bridge.py -- --export
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b5 as S
import pride_kit as K
import mobydick_kit as MK
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, MB, Canvas, anchor, sound, light_obj)

SID = "benbow-road-bridge"
ARGS = S.setup(SID, seed=1750)
scene = K.scene
rng = random.Random(1750)

READER = Vector((-1.3, -2.2, 0))
STREAM_Y = 0.6
INN = Vector((2.5, 36.0, 0))


def road_x(y): return 1.5 + 0.9 * math.sin(y / 18.0) - 0.4 * K.smoothstep(20, 40, y)


def H(x, y):
    """the dell: low along the stream, rising north to the inn's terrace and higher to the hamlet; banks either side"""
    base = 0.035 * min(max(0.0, y), 60.0) ** 1.25 * (1 - 0.5 * K.smoothstep(30, 45, y)) + 6.0 * K.smoothstep(40, 140, y)
    base += 0.1 * min(max(0.0, -y - 2), 15.0) ** 1.1 - 2.0 * K.smoothstep(-20, -80, y)
    dx_ = abs(x - road_x(y))
    side = (2.2 * K.smoothstep(3.0, 28.0, dx_) + 0.012 * max(0.0, dx_ - 28.0) * 1.0) * (1 if y > 3 else 0.6)    # the dell's sides, then gentle country
    ch = math.exp(-((y - STREAM_Y) / 1.0) ** 2) * 0.9 * (1 - math.exp(-((x - road_x(y)) / 1.2) ** 2) * 0.0)
    rough = 0.15 * noise.noise(Vector((x / 4, y / 4, 0.3))) + 0.6 * noise.noise(Vector((x / 25, y / 25, 1.3))) * K.smoothstep(6, 30, math.hypot(x, y))
    z = base + side + rough - ch
    if abs(x - road_x(y)) < 2.2 and y > STREAM_Y - 1.6:        # the road keeps an even grade (the bridge carries it over the stream)
        k = K.smoothstep(2.2, 1.6, abs(x - road_x(y)))
        rz = 0.035 * max(0.0, y) ** 1.25 * (1 - 0.5 * K.smoothstep(30, 45, y)) + 0.05 + (0.6 if abs(y - STREAM_Y) < 1.8 else 0.0) * 0
        if abs(y - STREAM_Y) > 1.6: z = z * (1 - k) + rz * k
    return z


def road_z(y):
    return 0.035 * max(0.0, y) ** 1.25 * (1 - 0.5 * K.smoothstep(30, 45, y)) + 0.05 + 0.1 * max(0.0, -y - 2) ** 1.1


# ----------------------------------------------------------------------------- materials
def frost_ground(name="M_FrostGround"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1500, 0))
    n1 = noise_(nt, co, 0.5, 5, 0.6, loc=(-1300, 300)); n2 = noise_(nt, co, 5.0, 5, 0.6, loc=(-1300, 100)); n3 = noise_(nt, co, 30.0, 4, 0.7, loc=(-1300, -100))
    grass = mix_rgb(nt, 'MIX', maprange(nt, n2.outputs["Fac"], 0.3, 0.7, 0, 1, (-1100, 200)), (0.10, 0.12, 0.07, 1), (0.22, 0.22, 0.14, 1), (-900, 200))
    frost = maprange(nt, n3.outputs["Fac"], 0.35, 0.65, 0.3, 0.75, (-1100, 0))
    col = mix_rgb(nt, 'MIX', frost, grass, (0.70, 0.72, 0.74, 1), (-700, 100))
    # the road: packed earth with ruts, frosted at the crown
    ry = s.outputs["Y"]
    col = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.55, 0.7, 0, 0.5, (-900, -200)), col, (0.30, 0.24, 0.16, 1), (-500, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, n3.outputs["Fac"], 0.4, 0.01)
    return m


def road_mat(name="M_Road"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    uv = node(nt, "ShaderNodeUVMap", (-1600, 300)); su = sep_xyz(nt, uv.outputs["UV"], (-1400, 300))
    n2 = noise_(nt, co, 3.0, 5, 0.6, loc=(-1300, 100)); n3 = noise_(nt, co, 40.0, 4, 0.7, loc=(-1300, -100))
    earth = mix_rgb(nt, 'MIX', maprange(nt, n2.outputs["Fac"], 0.3, 0.7, 0, 1, (-1100, 100)), (0.16, 0.12, 0.08, 1), (0.30, 0.24, 0.16, 1), (-900, 100))
    # two wheel ruts and the hoof-worn middle: across position u (0..1)
    u = su.outputs["X"]
    rut = math_(nt, 'MAXIMUM', maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', u, 0.28, (-1200, 400)), None, (-1100, 400)), 0.0, 0.06, 1, 0, (-1000, 400)),
                maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', u, 0.72, (-1200, 550)), None, (-1100, 550)), 0.0, 0.06, 1, 0, (-1000, 550)), (-850, 450))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', rut, 0.5, (-800, 300)), earth, (0.5, 0.45, 0.4, 1), (-700, 100))
    frost = math_(nt, 'MULTIPLY', maprange(nt, n3.outputs["Fac"], 0.4, 0.62, 0, 0.8, (-1100, -100)), math_(nt, 'SUBTRACT', 1.0, rut, (-900, -200)), (-800, -150))
    col = mix_rgb(nt, 'MIX', frost, col, (0.66, 0.68, 0.70, 1), (-500, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.8
    bump_from(nt, b, math_(nt, 'ADD', n3.outputs["Fac"], math_(nt, 'MULTIPLY', rut, -1.0, (-700, -400)), (-600, -400)), 0.5, 0.02)
    return m


def rubble_mat(name="M_Rubble"):
    """dry-stone rubble: irregular grey-brown stones, dark gaps, lichen, frost on the tops."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 6.0, 'F1', (-1300, 200))
    e = voronoi_(nt, co, 6.0, 'DISTANCE_TO_EDGE', (-1300, 0))
    n = noise_(nt, co, 14.0, 5, 0.6, loc=(-1300, -200))
    st = ramp(nt, [(0.0, (0.20, 0.19, 0.17, 1)), (0.5, (0.32, 0.30, 0.27, 1)), (1.0, (0.40, 0.37, 0.32, 1))], (-1100, 200))
    nt.links.new(v.outputs["Color"], st.inputs["Fac"]) if "Color" in v.outputs else None
    col = mix_rgb(nt, 'MULTIPLY', 1.0, st.outputs["Color"], maprange(nt, e.outputs["Distance"], 0.0, 0.08, 0.15, 1.0, (-1100, 0)), (-900, 100))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.62, 0.7, 0, 0.6, (-1100, -200)), col, (0.42, 0.44, 0.30, 1), (-700, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, e.outputs["Distance"], 0.8, 0.04)
    return m


def water_mat(name="M_Stream"):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (0.02, 0.025, 0.03, 1); b.inputs["Roughness"].default_value = 0.05
    n = noise_(nt, obj_coords(nt), 6.0, 3, 0.5, loc=(-800, -200)); bump_from(nt, b, n.outputs["Fac"], 0.2, 0.01)
    return m


def broom_atlas(S_=512):
    """broom in winter: dense bundles of stiff green switches, a few dark seed pods; no flowers in January."""
    cv = Canvas(S_, S_)
    r = random.Random(6)
    for k in range(260):
        x0 = S_ / 2 + r.gauss(0, S_ * 0.08); y0 = S_ - 6
        a = math.radians(-90 + r.gauss(0, 28)); L = r.uniform(S_ * 0.45, S_ * 0.95)
        x1 = x0 + math.cos(a) * L; y1 = y0 + math.sin(a) * L
        g = r.uniform(0, 1)
        cv.line((x0, y0), ((x0 + x1) / 2 + r.uniform(-8, 8), (y0 + y1) / 2), 1.6, 1.3, (0.10 + 0.05 * g, 0.20 + 0.06 * g, 0.08, 1))
        cv.line(((x0 + x1) / 2, (y0 + y1) / 2), (x1, y1), 1.3, 0.7, (0.14 + 0.06 * g, 0.26 + 0.06 * g, 0.10, 1))
        if r.random() < 0.15: cv.ellipse(x1, y1, 4, 1.5, a, (0.05, 0.04, 0.03, 1))
    cv.bleed(4)
    return K.np_image("A_Broom", cv.a)


def thorn_atlas(S_=1024):
    """a bare hawthorn/blackthorn hedge top: a tangle of dark twigs, rimed pale on top, against nothing."""
    cv = Canvas(S_, S_ // 2)
    r = random.Random(8)
    def twig(x, y, a, L, w, d):
        x1 = x + math.cos(a) * L; y1 = y + math.sin(a) * L
        cv.line((x, y), (x1, y1), w, w * 0.7, (0.07, 0.06, 0.05, 1))
        cv.line((x, y - w * 0.4), (x1, y1 - w * 0.4), w * 0.35, w * 0.25, (0.55, 0.57, 0.60, 0.6))
        if d < 4:
            for k in range(2):
                twig(x1, y1, a + r.uniform(-0.8, 0.8), L * r.uniform(0.55, 0.8), w * 0.7, d + 1)
    for k in range(26):
        twig(r.uniform(0, S_), S_ // 2 - 2, math.radians(-90 + r.gauss(0, 30)), r.uniform(60, 140), 4.5, 0)
    cv.bleed(4)
    return K.np_image("A_Thorn", cv.a)


M_GROUND = frost_ground()
M_ROAD = road_mat()
M_RUBBLE = rubble_mat()
M_WATER = water_mat()
M_BROOM = K.image_mat("M_Broom", broom_atlas(), rough=0.7, alpha=True)
M_THORN = K.image_mat("M_ThornTwigs", thorn_atlas(), rough=0.8, alpha=True)
M_HEDGEMASS = noisy("M_HedgeMass", [K.srgb((0.08, 0.07, 0.06)), K.srgb((0.14, 0.12, 0.10)), K.srgb((0.30, 0.31, 0.32))], scale=4, rough=0.9, bump=0.8, bump_dist=0.05, warp=0.6)
M_BROOMMASS = noisy("M_BroomMass", [K.srgb((0.06, 0.12, 0.05)), K.srgb((0.12, 0.20, 0.08))], scale=8, rough=0.8, bump=0.8, bump_dist=0.03, warp=0.5)
M_WASH = noisy("M_InnWhitewash", [K.srgb((0.80, 0.80, 0.76)), K.srgb((0.70, 0.70, 0.66)), K.srgb((0.86, 0.85, 0.80))], scale=1.5, rough=0.9, bump=0.3)
M_SLATE = noisy("M_Slate", [K.srgb((0.16, 0.17, 0.19)), K.srgb((0.24, 0.25, 0.27))], scale=6, rough=0.6, stretch=(1, 4, 1), bump=0.4)
M_TIMBER = MK.timber_mat("M_InnTimber", base=(0.14, 0.10, 0.07), dark=(0.05, 0.035, 0.025), light=(0.22, 0.16, 0.11), along='Z', rough=(0.5, 0.85), grime=0.5)
M_LIT = plain("M_LitWindow", (0.0, 0.0, 0.0), rough=0.5, emission=(1.0, 0.62, 0.30), strength=3.0)
M_LITROOM = plain("M_LitInterior", (0.0, 0.0, 0.0), rough=0.5, emission=(0.95, 0.55, 0.25), strength=1.6)
M_IRON = MK.iron_mat("M_Iron", rust=0.5)
M_HORN = plain("M_LanternHorn", (0.0, 0.0, 0.0), rough=0.5, emission=(1.0, 0.70, 0.35), strength=4.0)
M_BARKW = noisy("M_WinterBark", [K.srgb((0.14, 0.13, 0.12)), K.srgb((0.22, 0.21, 0.19))], scale=3, rough=0.85, stretch=(1, 1, 0.3), bump=0.5)
M_SIGN = noisy("M_SignBoard", [K.srgb((0.20, 0.16, 0.10)), K.srgb((0.30, 0.24, 0.14))], scale=6, rough=0.7)

# ----------------------------------------------------------------------------- the ground, the road, the stream
def keep_near(x, y): return True
near = S.grid_ground("GroundNear", M_GROUND, H, -22, 24, -12, 48, 1.0, chunk=8.0,
                     keep=lambda x, y: not (abs(x - road_x(y)) < 1.75 and y > STREAM_Y + 1.7) and not (abs(x - road_x(y)) < 1.75 and y < STREAM_Y - 1.7))
far = S.polar_ground("GroundFar", M_GROUND, H, r0=0.0, r1=800.0, nr=28, na=64, expo=2.0, centre=(1.0, 18.0),
                     keep=lambda x, y: not (-21.5 < x < 23.5 and -11.5 < y < 47.5))
# the road surface (two strips either side of the bridge), UV u across, v along
def road_strip(name, y0, y1):
    vs = []; fs = []; uvs = []
    ys_ = np.arange(y0, y1 + 0.01, 1.0)
    for i, y in enumerate(ys_):
        cx = road_x(y)
        for j, u in enumerate((0.0, 0.5, 1.0)):
            x = cx - 1.8 + 3.6 * u
            vs.append((x, y, road_z(y) - 0.02 * (1 - abs(u - 0.5) * 2) * 0 + (0.04 if u == 0.5 else 0.0))); uvs.append((u, y / 3.0))
        if i: fs += [((i - 1) * 3, (i - 1) * 3 + 1, i * 3 + 1, i * 3), ((i - 1) * 3 + 1, (i - 1) * 3 + 2, i * 3 + 2, i * 3 + 1)]
    o = K.mesh_from(name, vs, fs, M_ROAD, smooth=True)
    uvl = o.data.uv_layers.new(name="UVMap")
    for li, l in enumerate(o.data.loops): uvl.data[li].uv = uvs[l.vertex_index]
    return o
road_strip("RoadNorth", STREAM_Y + 1.6, 46)
road_strip("RoadSouth", -12, STREAM_Y - 1.6)
# the stream: a ribbon along its bed, flowing west (V increases downstream), with its banks of stones
sv = []; sf = []; suv = []
xs = np.arange(-22, 24.01, 1.0)
for i, x in enumerate(xs[::-1]):
    y = STREAM_Y + 0.3 * math.sin(x / 3.0) + 0.15 * math.sin(x / 1.3)
    w = 0.55 + 0.15 * math.sin(x / 2.2)
    for j, s_ in enumerate((-1, 1)):
        sv.append((x, y + s_ * w, -0.62)); suv.append(((s_ + 1) / 2, i * 1.0 / 2.0))
    if i: sf.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
st = K.mesh_from("water.stream.dell", sv, sf, M_WATER, smooth=True)
uvl = st.data.uv_layers.new(name="UVMap")
for li, l in enumerate(st.data.loops): uvl.data[li].uv = suv[l.vertex_index]
for k in range(40):       # stones in and along the stream
    x = rng.uniform(-14, 18); y = STREAM_Y + 0.3 * math.sin(x / 3.0) + rng.uniform(-0.9, 0.9)
    s_ = rng.uniform(0.08, 0.25)
    o = sphere(f"StreamStone{k}", s_, (x, y, -0.62 + s_ * 0.2), M_RUBBLE, seg=8, scale=(1.3, 1.0, 0.6))

# ----------------------------------------------------------------------------- the little bridge: a low rubble arch, parapets, the road over it
BX = road_x(STREAM_Y)
BR = Frame((BX, STREAM_Y), 0.0)
deck_z = road_z(STREAM_Y) + 0.0
# the arch barrel and spandrels: a solid with a low segmental opening under it (the stream runs through)
av = []; af = []
NS = 12
for side, x in enumerate((BX - 1.9, BX + 1.9)):
    for k in range(NS + 1):
        t = k / NS; a = math.pi * t
        yy = STREAM_Y - 0.85 * math.cos(a); zz = -0.65 + 0.62 * math.sin(a)
        av.append((x, yy, zz))
for k in range(NS):
    af.append((k, k + 1, NS + 1 + k + 1, NS + 1 + k))
mesh_from("BridgeArch", av, [f[::-1] for f in af], M_RUBBLE, smooth=True)
for sgn, x in ((-1, BX - 1.9), (1, BX + 1.9)):
    # spandrel face: from the arch to the road level, rubble
    fv = []; ff = []
    for k in range(NS + 1):
        t = k / NS; a = math.pi * t
        yy = STREAM_Y - 0.85 * math.cos(a); zz = -0.65 + 0.62 * math.sin(a)
        fv += [(x, yy, zz), (x, yy, deck_z + 0.02)]
    fv += [(x, STREAM_Y - 1.6, -0.65), (x, STREAM_Y - 1.6, deck_z + 0.02), (x, STREAM_Y + 1.6, -0.65), (x, STREAM_Y + 1.6, deck_z + 0.02)]
    for k in range(NS): ff.append((2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1))
    n0 = 2 * (NS + 1)
    ff.append((n0, 0, 1, n0 + 1)); ff.append((2 * NS, n0 + 2, n0 + 3, 2 * NS + 1))
    o = mesh_from(f"BridgeFace{sgn}", fv, ff, M_RUBBLE)
    # parapet: a low rubble wall with rough coping, splaying out at the ends
    pts = [(x + sgn * 0.0, STREAM_Y - 2.2, road_z(STREAM_Y - 2.2)), (x, STREAM_Y - 1.2, deck_z), (x, STREAM_Y + 1.2, deck_z), (x + sgn * 0.3, STREAM_Y + 2.4, road_z(STREAM_Y + 2.4))]
    for i in range(3):
        p, q = Vector(pts[i]), Vector(pts[i + 1])
        c = (p + q) / 2; d = q - p; L = d.length
        box(f"Parapet{sgn}{i}", (0.42, L + 0.1, 0.55), (c.x, c.y, c.z - 0.05 + (0.55) / 2), M_RUBBLE, rot=(0, 0, math.atan2(-d.x, d.y)))
        for j in range(int(L / 0.3)):
            t = (j + 0.5) / int(L / 0.3)
            cc = p.lerp(q, t)
            box(f"Coping{sgn}{i}{j}", (0.46, 0.26, 0.12 + rng.uniform(0, 0.08)), (cc.x, cc.y, cc.z + 0.5 + (0.12 + rng.uniform(0, 0.08)) / 2), M_RUBBLE, rot=(rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), math.atan2(-d.x, d.y)))
box("BridgeDeck", (3.6, 3.4, 0.25), (BX, STREAM_Y, deck_z - 0.1), M_RUBBLE)
vs = [(BX - 1.8, STREAM_Y - 1.7, deck_z + 0.04), (BX + 1.8, STREAM_Y - 1.7, deck_z + 0.04), (BX + 1.8, STREAM_Y + 1.7, deck_z + 0.04), (BX - 1.8, STREAM_Y + 1.7, deck_z + 0.04)]
bd = K.mesh_from("BridgeRoad", vs, [(0, 1, 2, 3)], M_ROAD)
u_ = bd.data.uv_layers.new(name="UVMap")
for li, l in enumerate(bd.data.loops): u_.data[li].uv = [(0, 0), (1, 0), (1, 1.1), (0, 1.1)][l.vertex_index]
anchor("scene.bridge", (BX, STREAM_Y, deck_z))

# ----------------------------------------------------------------------------- the great bush of broom beside the reader, more broom and gorse on the banks
mbb = MB()
def broom_bush(x, y, h, r_, n):
    z = H(x, y)
    box_ = sphere(f"BroomCore{x:.1f}", r_ * 0.7, (x, y, z + h * 0.42), M_BROOMMASS, seg=10, scale=(1.0, 1.0, h / r_ * 0.55))
    for k in range(n):
        a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0.0, r_ * 0.7)
        bx_, by_ = x + math.cos(a) * rr, y + math.sin(a) * rr
        yaw = rng.uniform(0, math.pi)
        hh = h * rng.uniform(0.7, 1.05); w = h * rng.uniform(0.7, 1.0)
        right = Vector((math.cos(yaw), math.sin(yaw), 0)) * w
        mbb.quad_card((bx_, by_, z - 0.05), right, (rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), hh), sway=(0.0, 1.0))
broom_bush(0.25, -1.75, 1.55, 0.6, 16)            # the one the reader hides behind (ahead-right)
broom_bush(-3.4, -0.8, 1.2, 0.6, 9)
broom_bush(5.0, -1.0, 1.4, 0.7, 10)
broom_bush(-4.8, 3.6, 1.3, 0.6, 9)
broom_bush(6.2, 4.4, 1.1, 0.5, 7)
mbb.build("veg.shrub.broom", M_BROOM)

# ----------------------------------------------------------------------------- hedgerows of bare thorn along both sides of the road up to the inn
mbh = MB()
for sgn in (-1, 1):
    pts = []
    y = STREAM_Y + 2.6
    while y < 31:
        pts.append((road_x(y) + sgn * (2.4 + 0.3 * math.sin(y * 0.7)), y)); y += 1.2
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; h = 1.5 + 0.35 * noise.noise(Vector((cx / 3, cy / 3, sgn)))
        z = H(cx, cy)
        hm = sphere(f"HedgeMass{sgn}{i}", 0.75, (cx, cy, z + h * 0.32), M_HEDGEMASS, seg=10, scale=(0.75, 1.0, h * 0.55))
        for v in hm.data.vertices:
            v.co += v.normal * 0.12 * noise.noise(v.co * 3.1 + Vector((i, sgn, 0)))
        for k in range(2):     # twig cards: along the hedge, standing out of its top
            right = Vector((x1 - x0, y1 - y0, 0)).normalized() * 1.8
            off = Vector((sgn * rng.uniform(-0.3, 0.3), 0, 0))
            mbh.quad_card(Vector((cx, cy, z + h * 0.55)) + off, right + Vector((rng.uniform(-0.3, 0.3), 0, 0)), (0, 0, h * 0.75), sway=(0.0, 1.0))
mbh.build("veg.shrub.thorn", M_THORN)
# rough frosty grass tussocks on the banks
mbg = MB()
pts = []
for k in range(420):
    x = rng.uniform(-7, 9); y = rng.uniform(-6, 6)
    if abs(x - road_x(y)) < 2.0 and abs(y - STREAM_Y) > 1.5: continue
    if abs(y - STREAM_Y) < 0.75: continue
    if (Vector((x, y)) - READER.xy).length < 0.45: continue
    pts.append((x, y))
S.grass_clumps(mbg, pts, H, rng, height=(0.2, 0.5), blades=(4, 7), lean=0.5, width=0.012, tint=lambda x, y: (rng.uniform(0.2, 0.6), rng.uniform(0.6, 1.0)))
mat_g = new_mat("M_FrostGrass")[0]
ntg = mat_g.node_tree; bg = ntg.nodes["Principled BSDF"]
at = node(ntg, "ShaderNodeAttribute", (-900, 0)); at.attribute_name = "sway"
spc = node(ntg, "ShaderNodeSeparateColor", (-700, 0)); ntg.links.new(at.outputs["Color"], spc.inputs[0])
cc = mix_rgb(ntg, 'MIX', spc.outputs["Red"], (0.16, 0.15, 0.09, 1), (0.66, 0.68, 0.70, 1), (-500, 0))
ntg.links.new(cc, bg.inputs["Base Color"]); bg.inputs["Roughness"].default_value = 0.7
mbg.build("veg.grass.frost", mat_g)

# ----------------------------------------------------------------------------- the Admiral Benbow: a long whitewashed inn, slate roof, door open, the captain's window thrown open
IZ = H(INN.x, INN.y)
IW, ID, IH = 13.0, 6.0, 5.2
IF = Frame((INN.x, INN.y), 0.0, z=IZ)
IF.box("InnPlinth", (IW + 0.2, ID + 0.2, 0.4), (0, 0, -0.35 + (0.4) / 2), M_RUBBLE)
# walls as panels round openings on the front (south, local -Y): door, ground windows, upper windows
front_ops = [(-3.8, 1.1, 0.0, 2.1, "door"), (-1.2, 1.0, 0.9, 1.9, "w"), (1.8, 1.0, 0.9, 1.9, "w"), (4.6, 1.0, 0.9, 1.9, "w"),
             (-3.8, 0.9, 3.0, 4.0, "w"), (-1.2, 0.9, 3.0, 4.0, "capt"), (1.8, 0.9, 3.0, 4.0, "w"), (4.6, 0.9, 3.0, 4.0, "w")]
cuts = sorted(set([-IW / 2, IW / 2] + [c - w / 2 for c, w, *_ in front_ops] + [c + w / 2 for c, w, *_ in front_ops]))
for i in range(len(cuts) - 1):
    a, b_ = cuts[i], cuts[i + 1]
    zs = [0.0, IH]
    for c, w, z0, z1, k in front_ops:
        if a >= c - w / 2 - 1e-6 and b_ <= c + w / 2 + 1e-6: zs += [z0, z1]
    zs = sorted(set(zs))
    for j in range(len(zs) - 1):
        z0, z1 = zs[j], zs[j + 1]
        inside = any(a >= c - w / 2 - 1e-6 and b_ <= c + w / 2 + 1e-6 and z0 >= o0 - 1e-6 and z1 <= o1 + 1e-6 for c, w, o0, o1, k in front_ops)
        if inside or z1 - z0 < 1e-3: continue
        IF.box(f"InnFront{i}_{j}", (b_ - a, 0.45, z1 - z0), ((a + b_) / 2, -ID / 2, z0 + (z1 - z0) / 2), M_WASH)
IF.box("InnBack", (IW, 0.45, IH), (0, ID / 2, 0 + (IH) / 2), M_WASH)
for sx in (-1, 1): IF.box(f"InnGable{sx}", (0.45, ID, IH), (sx * IW / 2, 0, 0 + (IH) / 2), M_WASH)
# gable-end walls up into the roof, and the roof itself
for sx in (-1, 1):
    gv = [IF.p(sx * IW / 2, -ID / 2 - 0.2, IH), IF.p(sx * IW / 2, ID / 2 + 0.2, IH), IF.p(sx * IW / 2, 0, IH + 2.6)]
    mesh_from(f"InnGableTop{sx}", gv, [(0, 1, 2)], M_WASH).modifiers.new("S", 'SOLIDIFY').thickness = 0.45
for sy in (-1, 1):
    rv = [IF.p(-IW / 2 - 0.35, sy * (ID / 2 + 0.5), IH - 0.3), IF.p(IW / 2 + 0.35, sy * (ID / 2 + 0.5), IH - 0.3), IF.p(IW / 2 + 0.35, 0, IH + 2.65), IF.p(-IW / 2 - 0.35, 0, IH + 2.65)]
    r_ = mesh_from(f"InnRoof{sy}", rv, [(0, 1, 2, 3)], M_SLATE); r_.modifiers.new("S", 'SOLIDIFY').thickness = 0.12
for sx in (-1, 1):
    IF.box(f"Chimney{sx}", (0.9, 0.7, 2.0), (sx * (IW / 2 - 0.4), 0, IH + 1.6 + (2.0) / 2), M_RUBBLE)
# the openings: the door standing open (the leaf swung in), lamplit interior behind; windows dark or lit
inner = Frame((INN.x, INN.y), 0.0, z=IZ)
for c, w, z0, z1, k in front_ops:
    if k == "door":
        IF.box("DoorLight", (w, 0.05, z1 - z0), (c, -ID / 2 + 1.2, z0 + (z1 - z0) / 2), M_LITROOM)
        for sx in (-1, 1): IF.box(f"DoorReveal{sx}", (0.05, 1.2, z1 - z0), (c + sx * w / 2, -ID / 2 + 0.6, z0 + (z1 - z0) / 2), M_LITROOM)
        IF.box("DoorLeaf", (0.06, w, z1 - z0 - 0.05), (c - w / 2 + 0.05, -ID / 2 + w / 2 + 0.25, z0 + (z1 - z0 - 0.05) / 2), M_TIMBER)
        IF.box("DoorStep", (w + 0.4, 0.5, 0.15), (c, -ID / 2 - 0.4, -0.12), M_RUBBLE)
    elif k == "capt":
        IF.box("CaptainRoom", (w, 0.05, z1 - z0), (c, -ID / 2 + 1.5, z0 + (z1 - z0) / 2), M_LITROOM)
        IF.box("CaptainCasementOpen", (0.05, 0.45, z1 - z0 - 0.1), (c + w / 2 + 0.02, -ID / 2 - 0.45, z0 + 0.05 + (z1 - z0 - 0.1) / 2), M_TIMBER)
        for sx in (-1, 1): IF.box(f"CaptReveal{sx}", (0.05, 1.5, z1 - z0), (c + sx * w / 2, -ID / 2 + 0.75, z0 + (z1 - z0) / 2), M_LITROOM)
        IF.box("CaptSill", (w + 0.2, 0.3, 0.06), (c, -ID / 2 - 0.15, z0 - 0.06), M_RUBBLE)
    else:
        lit = (c, z0) in ((1.8, 0.9),)
        IF.box(f"Glass{c}{z0}", (w, 0.04, z1 - z0), (c, -ID / 2 + 0.12, z0 + (z1 - z0) / 2), M_LIT if lit else plain("M_DarkGlass", (0.015, 0.018, 0.022), rough=0.1) if "M_DarkGlass" not in bpy.data.materials else bpy.data.materials["M_DarkGlass"])
        IF.box(f"WinBarV{c}{z0}", (0.05, 0.06, z1 - z0), (c, -ID / 2 + 0.08, z0 + (z1 - z0) / 2), M_TIMBER)
        IF.box(f"WinBarH{c}{z0}", (w, 0.06, 0.05), (c, -ID / 2 + 0.08, (z0 + z1) / 2), M_TIMBER)
        IF.box(f"WinSill{c}{z0}", (w + 0.15, 0.25, 0.06), (c, -ID / 2 - 0.12, z0 - 0.06), M_RUBBLE)
# the signboard on its post by the road
SP = Vector((road_x(30.5) + 2.6, 30.5, H(road_x(30.5) + 2.6, 30.5)))
cyl("SignPost", 0.09, 4.0, (SP.x, SP.y, SP.z + 2.0), M_TIMBER, verts=8)
tube("SignArm", [SP + Vector((0, 0, 3.7)), SP + Vector((-1.3, 0, 3.7))], 0.05, M_TIMBER, sides=6)
box("SignBoard", (0.06, 1.1, 0.8), (SP.x - 0.85, SP.y, SP.z + 2.75), M_SIGN, rot=(0, 0, math.radians(90)), bevel=0.01)
for sy in (-1, 1): tube(f"SignChain{sy}", [SP + Vector((-0.85 + sy * 0.4, 0, 3.68)), SP + Vector((-0.85 + sy * 0.4, 0, 3.15))], 0.01, M_IRON, sides=4)
anchor("scene.inn", tuple(INN))

# ----------------------------------------------------------------------------- the dropped lantern in the road, still burning
LT = Vector((road_x(9.0) - 0.4, 9.0, road_z(9.0)))
LF = Frame((LT.x, LT.y), math.radians(30), z=LT.z)
# lying on its side: a tin box lantern with horn panes
LF.box("LanternBody", (0.22, 0.2, 0.2), (0, 0, 0.0 + (0.2) / 2), M_IRON, rx=math.pi / 2)
for sx in (-1, 1): LF.box(f"LanternHorn{sx}", (0.012, 0.16, 0.14), (sx * 0.11, 0.0, 0.03 + (0.14) / 2), M_HORN)
LF.box("LanternHornTop", (0.16, 0.012, 0.14), (0, 0.11, 0.03 + (0.14) / 2), M_HORN)
tube("LanternRing", [LF.p(0, -0.12, 0.1), LF.p(0, -0.2, 0.15), LF.p(0, -0.2, 0.05), LF.p(0, -0.12, 0.04)], 0.008, M_IRON, sides=4)

# ----------------------------------------------------------------------------- a few bare trees: an ash by the inn, thorn trees on the bank
def bare_tree(name, base, h, r0, seed, nlimb=5):
    r = random.Random(seed)
    def grow(p, d, L, rad, depth):
        q = p + d * L
        tube(f"{name}B{depth}_{r.randint(0, 99999)}", [p, p + d * L * 0.5 + Vector((r.uniform(-0.1, 0.1), r.uniform(-0.1, 0.1), 0)) * L, q], [rad, rad * 0.85, rad * 0.7], M_BARKW, sides=max(4, 8 - depth * 2))
        if depth >= 3: return
        for k in range(2 if depth < 2 else 3):
            a = r.uniform(0, 2 * math.pi); nd = (d * 1.2 + Vector((math.cos(a), math.sin(a), r.uniform(-0.1, 0.5)))).normalized()
            grow(q, nd, L * r.uniform(0.55, 0.75), rad * 0.62, depth + 1)
    trunk_top = base + Vector((r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), h * 0.4))
    tube(f"{name}Trunk", [base - Vector((0, 0, 0.3)), base + Vector((0, 0, h * 0.2)), trunk_top], [r0 * 1.2, r0, r0 * 0.85], M_BARKW, sides=8)
    for k in range(nlimb):
        a = 2 * math.pi * k / nlimb + r.uniform(-0.3, 0.3)
        d = Vector((math.cos(a) * 0.6, math.sin(a) * 0.6, 1)).normalized()
        grow(trunk_top, d, h * 0.25, r0 * 0.55, 1)
bare_tree("AshInn", Vector((INN.x + 9.5, INN.y - 3.0, H(INN.x + 9.5, INN.y - 3.0))), 11.0, 0.3, 3, nlimb=4)
bare_tree("ThornBank", Vector((-5.5, 6.5, H(-5.5, 6.5))), 4.5, 0.12, 7, nlimb=3)
bare_tree("ThornBank2", Vector((7.5, 12.0, H(7.5, 12.0))), 5.0, 0.13, 9, nlimb=3)

# ----------------------------------------------------------------------------- the hamlet's cottages on the hill beyond, one window lit
for k, (x, y, rot) in enumerate(((-30, 90, 0.2), (-12, 105, -0.1), (25, 98, 0.3))):
    z = H(x, y)
    F = Frame((x, y), rot, z=z)
    F.box(f"Cot{k}", (7, 4.5, 3.2), (0, 0, -0.3 + (3.2) / 2), M_WASH)
    for sy in (-1, 1):
        rv = [F.p(-3.7, sy * 2.6, 2.7), F.p(3.7, sy * 2.6, 2.7), F.p(3.7, 0, 4.6), F.p(-3.7, 0, 4.6)]
        mesh_from(f"CotRoof{k}{sy}", rv, [(0, 1, 2, 3)], M_SLATE)
    if k == 1: F.box(f"CotLit{k}", (0.7, 0.05, 0.8), (1.2, -2.27, 1.0 + (0.8) / 2), M_LIT)

# ----------------------------------------------------------------------------- the night sky, the full moon, light
MOON_TO = Vector((0.45, 0.62, 0.64)).normalized()        # the moon high over the south-east... ahead-right of the reader, above the hill
def night_sky(name="M_SkyDome"):
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-2000, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-1800, 0), operation='NORMALIZE'); nt.links.new(tc.outputs["Object"], nv.inputs[0])
    d = nv.outputs[0]; sp = sep_xyz(nt, d, (-1600, 0)); el = sp.outputs["Z"]
    g = ramp(nt, [(0.0, (0.035, 0.045, 0.06, 1)), (0.12, (0.05, 0.065, 0.09, 1)), (0.4, (0.022, 0.032, 0.06, 1)), (1.0, (0.010, 0.015, 0.035, 1))], (-1200, 300))
    nt.links.new(maprange(nt, el, -0.1, 1.0, 0, 1, (-1400, 300)), g.inputs["Fac"])
    col = g.outputs["Color"]
    md = node(nt, "ShaderNodeVectorMath", (-1400, 700), operation='DOT_PRODUCT'); md.inputs[1].default_value = tuple(MOON_TO); nt.links.new(d, md.inputs[0])
    halo = math_(nt, 'POWER', maprange(nt, md.outputs["Value"], 0.85, 1.0, 0, 1, (-1200, 700)), 4.0, (-1050, 700))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', halo, 0.25, (-900, 750)), col, (0.45, 0.50, 0.60, 1), (-800, 300))
    disc = maprange(nt, md.outputs["Value"], 0.99988, 0.99992, 0, 1, (-1200, 900))
    mn = noise_(nt, d, 600.0, 3, 0.5, loc=(-1200, 1100))
    moon = mix_rgb(nt, 'MULTIPLY', 1.0, (2.2, 2.2, 2.1, 1), maprange(nt, mn.outputs["Fac"], 0.3, 0.7, 0.7, 1.0, (-1000, 1100)), (-850, 1000))
    col = mix_rgb(nt, 'MIX', disc, col, moon, (-650, 300))
    # stars: sparse points, fewer near the moon and low down
    v = voronoi_(nt, d, 260.0, 'F1', (-1400, -300))
    star = maprange(nt, v.outputs["Distance"], 0.0, 0.06, 1, 0, (-1200, -300))
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1400, -500), noise_dimensions='3D'); nt.links.new(v.outputs["Position"], wn.inputs["Vector"])
    star = math_(nt, 'MULTIPLY', star, maprange(nt, wn.outputs["Value"], 0.8, 1.0, 0, 1, (-1200, -500)), (-1050, -400))
    star = math_(nt, 'MULTIPLY', star, maprange(nt, el, 0.05, 0.3, 0, 1, (-1200, -650)), (-950, -450))
    star = math_(nt, 'MULTIPLY', star, maprange(nt, md.outputs["Value"], 0.7, 0.95, 1, 0, (-1200, -800)), (-850, -500))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', star, 0.8, (-700, -500)), col, (0.9, 0.92, 1.0, 1), (-500, 300))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1); b.inputs["Emission Strength"].default_value = 1.0
    return m
S.sky_dome(night_sky(), radius=1000.0)
light_obj("Lamp.moon", 'SUN', 0.35, (0.70, 0.78, 1.0), (0, 0, 50), direction=tuple(-MOON_TO), angle=math.radians(0.6))
light_obj("Lamp.innDoor", 'POINT', 180.0, (1.0, 0.62, 0.32), IF.p(-3.8, -ID / 2 + 0.6, 1.4), shadow_soft_size=0.3)
light_obj("Lamp.captainWindow", 'POINT', 60.0, (1.0, 0.62, 0.32), IF.p(-1.2, -ID / 2 + 0.7, 3.5), shadow_soft_size=0.2)
light_obj("Lamp.lantern", 'POINT', 12.0, (1.0, 0.68, 0.36), tuple(LT + Vector((0, 0, 0.12))), shadow_soft_size=0.05)
world = bpy.data.worlds.new("Night"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.016, 0.028, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors, sources
S.reader(READER, (INN.x - READER.x, INN.y - READER.y))
anchor("scene.centre", (BX, STREAM_Y, 0))
S.fx("fx.lantern.road", tuple(LT + Vector((0, 0, 0.1))), 0.05)
S.fx("fx.lantern.innDoor", IF.p(-3.8, -ID / 2 + 0.9, 1.9), 0.06)
S.fx("fx.candle.captainWindow", IF.p(-1.2, -ID / 2 + 0.9, 3.4), 0.02)
sound("river", "stream", (BX - 3.0, STREAM_Y, -0.3))
sound("wind", "dell", (-6.0, 8.0, 3.0))
sound("surf", "cove", (-10.0, -60.0, 0.0))
page = S.page_preview()
K.apply_transforms()

E = READER + Vector((0, 0, S.EYE))
fwd = (INN - READER).normalized()
cams = S.eye_cams([("Reader", 0), ("Left", -80), ("Right", 80), ("Behind", 180)], dz=0.3, dist=8.0, extra=[
    ("Page", E, E + fwd * 8 + Vector((0, 0, 0.3)), 17),
    ("Inn", E + fwd * 14 + Vector((0, 0, 0.5)), INN + Vector((0, -3, 3)), 28),
    ("Bridge", Vector((BX - 4.5, STREAM_Y - 3.5, 1.2)), Vector((BX, STREAM_Y, -0.2)), 24),
])
probs = S.check_reader(ignore=("PagePreview", "veg.grass.frost"))
K.print_budget(exclude=("PagePreview",))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=2.2, captures_dir=ARGS.captures)

if ARGS.export or ARGS.bake:
    S.export(SID, cams, page=page, unlit_emit=("M_LitWindow", "M_LitInterior", "M_LanternHorn"),
             keep_names={"M_Stream": "water.stream.dell", "M_Broom": "veg.shrub.broom", "M_ThornTwigs": "veg.shrub.thorn", "M_FrostGrass": "veg.grass.frost"},
             size_for={"M_FrostGround": (2048, 64, 1024), "M_Road": (1024, 64, 512), "M_Rubble": (1024, 64, 512), "M_InnWhitewash": (1024, 32, 256),
                       "M_Slate": (512, 32, 256), "M_HedgeMass": (1024, 32, 256), "M_BroomMass": (256, 32, 128), "M_SkyDome": (2048,), "M_WinterBark": (512, 32, 256),
                       "M_FrostGrass": (256, 32, 64), "M_Stream": (256, 32, 128)},
             default_size=(256, 32, 128))
print("DONE")
