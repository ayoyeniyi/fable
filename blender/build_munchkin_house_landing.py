"""
Fable: where the house landed, in the country of the Munchkins (The Wonderful Wizard of Oz, chapter II, "The Council
with the Munchkins"). A chapter step-in room: built ahead of time, served from the server, downloaded by the headset.

"The cyclone had set the house down very gently--for a cyclone--in the midst of a country of marvelous beauty. There
were lovely patches of greensward all about, with stately trees bearing rich and luscious fruits. Banks of gorgeous
flowers were on every hand, and birds with rare and brilliant plumage sang and fluttered in the trees and bushes. A
little way off was a small brook, rushing and sparkling along between green banks ..."
"... there were two feet sticking out, shod in silver shoes with pointed toes." "... just under the corner of the great
beam the house rested on" (chapter II)

The moment: bright morning sunshine just after the landing. The reader stands on the greensward a few metres from the
little gray Kansas house, which sits askew and a little tilted on its sill beams, its door standing open; ahead, under
the near corner of the great beam, the two feet in silver shoes with pointed toes stick out onto the grass. Around:
lawn and longer meadow grass, banks of flowers (the Munchkins' blue foremost, with white, gold and red), fruit trees
heavy with apples, pears and plums, tall limes and beeches behind, and on the right a little brook rushing between green
banks. The drab, sun-blistered clapboard house is the one gray thing in a saturated, sunny country. No figures (the
Munchkins and the Witch of the North are left out) and no birds are modelled (they are sound sources in the trees).

Living scene (docs/LIVING_SCENES.md): water.stream.brook (UV V runs downstream), veg.grass.lawn (cards, R = sway),
veg.flowers.banks, veg.crown.apple / pear / plum / lime / beech, sound.birds.* (3), sound.river.brook,
sound.wind-trees.limes.

Node names: anchor.reader.entrance (feet, z of the lawn), anchor.reader.look (eye height, 1 m ahead), anchor.scene.centre
(the house corner with the feet), anchor.house.door, anchor.witch.feet; light.sun (SUN, morning, from the reader's
back-right), light.sky (SUN, cool shadowless fill); SkyDome (unlit), far.land (ground beyond 40 m).

Axes: metres, Blender +Z up, reader at the origin facing +Y. East (the sun's side) is +X.

Run headless (one Blender at a time):
  blender -b -P blender/build_munchkin_house_landing.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_munchkin_house_landing.py -- --render --samples 48 --res 1400 --captures captures/blender/munchkin-house-landing
  blender -b -P blender/build_munchkin_house_landing.py -- --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
ARGS = K.setup("munchkin-house-landing", "out/munchkin-house-landing", 1900, "MunchkinHouseLanding", default_samples=48)
import scene_kit_b2 as B
from scene_kit_b2 import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          texcoord_obj, wood, noisy, plain, image_mat, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound,
                          light_obj, camera, smoothstep, lerp, n2, fbm2, link, card, tree, blob, set_card_normals, spray_atlas, QUAD)
OUT = K.OUT; scene = K.scene
rng = random.Random(1900)

# ----------------------------------------------------------------------------- layout
EYE_H = 1.55
SUN_DIR = Vector((0.55, -0.62, 0.56)).normalized()          # towards the sun: east-south-east, behind the reader's right shoulder
HOUSE_C = Vector((0.55, 6.6))                               # the house centre (plan)
HOUSE_YAW = math.radians(31.0)
HW, HD = 2.5, 2.0                                           # half width (local x) and half depth (local y)
TILT = (math.radians(3.2), math.radians(-3.6))              # askew: rolled about local x and y
BROOK = [(10.5, 48), (9.2, 30), (10.8, 18), (8.6, 9), (9.4, 0), (11.6, -9), (10.2, -22), (12.0, -40)]   # centre line, upstream first
BROOK_W = 1.7
NEAR = 42.0
SKY_R = 160.0

def brook_d(x, y):
    """distance to the brook centre line and the distance along it (from upstream)."""
    best = (1e9, 0.0); acc = 0.0
    for (x0, y0), (x1, y1) in zip(BROOK, BROOK[1:]):
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy; L = math.sqrt(L2)
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L2))
        d = math.hypot(x - x0 - t * dx, y - y0 - t * dy)
        if d < best[0]: best = (d, acc + t * L)
        acc += L
    return best

def H(x, y):
    """the land: a gentle swell rising behind the house and to the left, a flower bank on the left, the brook's
    channel on the right (banks ~0.7 m)."""
    h = 0.35 * fbm2(x, y, 26.0, 3, 1.3) + 0.6 * smoothstep(5, 40, y) * 0.8 + 0.25 * smoothstep(-2, -25, x)
    h += 0.35 * math.exp(-((x + 9.0) ** 2 / 10.0 + (y - 4.0) ** 2 / 60.0))         # the flower bank on the left
    d, s = brook_d(x, y)
    bed = 0.75 * (1.0 - smoothstep(BROOK_W * 0.45, BROOK_W * 1.6, d))
    h -= bed + 0.08 * smoothstep(BROOK_W * 1.6, BROOK_W * 2.6, d) * 0.0
    h -= 0.02 * s * (1.0 - smoothstep(BROOK_W, BROOK_W * 3, d)) * 0.0
    h -= 0.012 * s * 0.0
    # the reader's spot and the house plot are levelled a little (the lawn)
    return h

Z0 = H(0, 0)
def gz(x, y): return H(x, y) - Z0
RX, RY = -0.35, -1.35                                      # the reader's feet (about 5 m from the house corner)
B.set_ground(gz, (RX, RY, gz(RX, RY) + EYE_H))

# ----------------------------------------------------------------------------- painted atlases
print("painting atlases ...", flush=True)
IMG_MEADOW = B.meadow_atlas("A_MeadowCards", flowers=[((0.20, 0.33, 0.85), (0.95, 0.85, 0.30), 'cup'), ((0.95, 0.94, 0.90), (0.95, 0.72, 0.08), 'daisy'),
                                                      ((0.32, 0.30, 0.86), (0.25, 0.20, 0.60), 'spike'), ((0.92, 0.70, 0.06), (0.75, 0.45, 0.05), 'cup')])
IMG_BANK = B.meadow_atlas("A_FlowerBank", seed=11, flowers=[((0.18, 0.36, 0.92), (0.98, 0.90, 0.40), 'cup'), ((0.85, 0.18, 0.30), (0.20, 0.10, 0.05), 'cup'),
                                                            ((0.40, 0.32, 0.90), (0.30, 0.22, 0.70), 'spike'), ((0.98, 0.96, 0.92), (0.95, 0.80, 0.20), 'umbel')])
B.SPRAY_KINDS["bloom"] = ([(0.17, 0.33, 0.10), (0.21, 0.38, 0.12), (0.15, 0.29, 0.08)], 4, 11.0, 'broad',
                          (0.9, [(0.22, 0.38, 0.95), (0.30, 0.45, 0.98), (0.55, 0.62, 1.0), (0.70, 0.72, 0.85)], 10.0))
IMG_APPLE = spray_atlas("A_AppleSprays", "apple", 31)
IMG_PEAR = spray_atlas("A_PearSprays", "pear", 32)
IMG_PLUM = spray_atlas("A_PlumSprays", "plum", 33)
IMG_LIME = spray_atlas("A_LimeSprays", "lime", 34)
IMG_BEECH = spray_atlas("A_BeechSprays", "beech", 35)
IMG_BLOOM = spray_atlas("A_BloomSprays", "bloom", 36, S=512)

# ----------------------------------------------------------------------------- materials
M_MEADOW = image_mat("M_MeadowCards", IMG_MEADOW, rough=0.8, alpha=True, spec=0.2)
M_BANK = image_mat("M_FlowerBank", IMG_BANK, rough=0.8, alpha=True, spec=0.2)
M_BLADES = image_mat("M_GrassBlades", B.blade_tones(), rough=0.5, spec=0.4)
M_APPLE = image_mat("M_AppleSprays", IMG_APPLE, rough=0.5, alpha=True)
M_PEAR = image_mat("M_PearSprays", IMG_PEAR, rough=0.5, alpha=True)
M_PLUM = image_mat("M_PlumSprays", IMG_PLUM, rough=0.5, alpha=True)
M_LIME = image_mat("M_LimeSprays", IMG_LIME, rough=0.55, alpha=True)
M_BEECH = image_mat("M_BeechSprays", IMG_BEECH, rough=0.55, alpha=True)
M_BLOOM = image_mat("M_BloomSprays", IMG_BLOOM, rough=0.5, alpha=True)
M_BARK = B.bark_mat("M_FruitBark", base=(0.24, 0.20, 0.16), dark=(0.09, 0.075, 0.06), light=(0.36, 0.31, 0.25), fissure=True, green=0.25, scale=1.4)
M_SMOOTHBARK = B.bark_mat("M_SmoothBark", base=(0.20, 0.19, 0.17), dark=(0.09, 0.085, 0.08), light=(0.28, 0.27, 0.25), fissure=False, green=0.3, scale=1.0)

def ground_mat(name="M_Lawn"):
    """greensward: a fine lawn of mixed greens with clover patches, darker under the trees, lusher and wetter on the
    brook's banks, bare wet soil and pebbles at the water's edge."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2000, 0)); s = sep_xyz(nt, co, (-1800, -600))
    n1 = noise_(nt, co, 0.12, 5, 0.65, loc=(-1500, 200)); n2_ = noise_(nt, co, 3.0, 6, 0.6, loc=(-1500, 0))
    mpb = node(nt, "ShaderNodeMapping", (-1700, -200)); mpb.inputs["Scale"].default_value = (90.0, 90.0, 20.0); nt.links.new(co, mpb.inputs["Vector"])
    fine = noise_(nt, mpb.outputs["Vector"], 1.0, 6, 0.8, loc=(-1500, -200))
    g = ramp(nt, [(0.0, c4((0.045, 0.10, 0.018))), (0.35, c4((0.07, 0.15, 0.025))), (0.6, c4((0.10, 0.19, 0.035))), (1.0, c4((0.15, 0.23, 0.05)))], (-1100, 200))
    mixf = math_(nt, 'ADD', math_(nt, 'MULTIPLY', n1.outputs["Fac"], 0.8, (-1300, 300)), math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.25, (-1300, 150)), (-1250, 250))
    mixf = math_(nt, 'ADD', mixf, math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.3, (-1300, -100)), (-1200, 100))
    nt.links.new(mixf, g.inputs["Fac"])
    col = g.outputs["Color"]
    clov = voronoi_(nt, co, 1.2, 'F1', (-1500, -400))
    cm = maprange(nt, clov.outputs["Distance"], 0.25, 0.1, 0, 0.55, (-1200, -400))
    col = mix_rgb(nt, 'MIX', cm, col, (0.04, 0.12, 0.03, 1), (-900, 100))
    # specks of daisies and buttercups in the sward
    sp = noise_(nt, co, 90.0, 2, 0.5, loc=(-1500, -700))
    spm = maprange(nt, sp.outputs["Fac"], 0.68, 0.72, 0, 1, (-1200, -700))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', spm, 0.6, (-1000, -700)), col, (0.85, 0.80, 0.35, 1), (-700, 100))
    # the brook: wet soil and gravel near the water line (z below the bank)
    wet = maprange(nt, s.outputs["Z"], -0.48, -0.62, 0, 1, (-1200, -900))
    soil = mix_rgb(nt, 'MIX', maprange(nt, n2_.outputs["Fac"], 0.3, 0.7, 0, 1, (-1000, -1000)), (0.13, 0.10, 0.07, 1), (0.28, 0.25, 0.20, 1), (-800, -1000))
    col = mix_rgb(nt, 'MIX', wet, col, soil, (-500, 100))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, wet, 0, 1, 0.85, 0.45, (-300, -300)), b.inputs["Roughness"])
    bump_from(nt, b, fine.outputs["Fac"], 0.25, 0.01, (0, -400))
    return m
M_LAWN = ground_mat()
M_FAR = noisy("M_FarLand", [(0.035, 0.08, 0.02), (0.06, 0.12, 0.03), (0.09, 0.15, 0.04)], scale=0.05, rough=0.9, bump=0.0)

def clapboard_mat(name="M_Clapboard"):
    """sun-blistered, unpainted-gray clapboard: silvered pine with darker grain, weather streaks and lichen-free dust."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2000, 0))
    mp = node(nt, "ShaderNodeMapping", (-1800, 0)); mp.inputs["Scale"].default_value = (0.8, 0.8, 30.0); nt.links.new(co, mp.inputs["Vector"])
    wave = node(nt, "ShaderNodeTexNoise", (-1500, 200)); wave.inputs["Scale"].default_value = 1.4; wave.inputs["Detail"].default_value = 4.0
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    fib = noise_(nt, mp.outputs["Vector"], 8.0, 8, 0.7, loc=(-1500, -50))
    blot = noise_(nt, co, 1.6, 4, 0.6, loc=(-1500, -300))
    r = ramp(nt, [(0.0, c4((0.10, 0.10, 0.09))), (0.35, c4((0.19, 0.185, 0.17))), (0.7, c4((0.27, 0.26, 0.24))), (1.0, c4((0.33, 0.32, 0.30)))], (-1000, 100))
    f = math_(nt, 'ADD', math_(nt, 'MULTIPLY', wave.outputs["Fac"], 0.45, (-1200, 200)), math_(nt, 'MULTIPLY', fib.outputs["Fac"], 0.35, (-1200, 0)), (-1100, 100))
    f = math_(nt, 'ADD', f, math_(nt, 'MULTIPLY', blot.outputs["Fac"], 0.3, (-1200, -250)), (-1050, 0))
    nt.links.new(f, r.inputs["Fac"])
    col = K.ao_mul(nt, r.outputs["Color"], 0.2, 0.55, (-700, -500))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.88
    bump_from(nt, b, f, 0.5, 0.004, (0, -400))
    return m
M_CLAP = clapboard_mat()
M_TRIM = wood("M_HouseTrim", base=(0.20, 0.195, 0.18), dark=(0.09, 0.085, 0.08), light=(0.30, 0.29, 0.27), scale=1.5, rough=(0.75, 0.9), ao=0.4)
M_SHINGLE = noisy("M_Shingles", [(0.12, 0.115, 0.11), (0.19, 0.18, 0.17), (0.25, 0.24, 0.22)], scale=6.0, rough=0.9, bump=0.4, stretch=(1, 1, 6), ao=0.5)
M_BEAM = wood("M_SillBeam", base=(0.28, 0.25, 0.21), dark=(0.10, 0.09, 0.08), light=(0.40, 0.37, 0.32), scale=0.8, rough=(0.8, 0.95), ao=0.4, bump=0.6)
M_GLASS = plain("M_Glass", (0.05, 0.06, 0.07), rough=0.06, coat=0.0)
M_INTERIOR = noisy("M_Interior", [(0.10, 0.08, 0.06), (0.16, 0.13, 0.10)], scale=4.0, rough=0.85, bump=0.0)
M_STOCK = noisy("M_Stocking", [(0.025, 0.025, 0.035), (0.05, 0.05, 0.07)], scale=60.0, rough=0.85, bump=0.1)
M_SOLE = plain("M_ShoeSole", (0.10, 0.09, 0.08), rough=0.6)
M_SILVER = plain("M_SilverShoe", (0.70, 0.72, 0.75), rough=0.28, metallic=0.35, coat=0.6)
M_STONE = noisy("M_BrookStones", [(0.07, 0.07, 0.06), (0.13, 0.12, 0.10), (0.20, 0.19, 0.16)], scale=3.0, rough=(0.5, 0.85), bump=0.5)
def water_mat(name="M_Brook"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-1200, 0)); n = noise_(nt, co, 6.0, 4, 0.6, loc=(-900, 0))
    r = ramp(nt, [(0.0, c4((0.015, 0.03, 0.025))), (1.0, c4((0.05, 0.08, 0.06)))], (-600, 0)); nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.12
    bump_from(nt, b, n.outputs["Fac"], 0.3, 0.02, (0, -300))
    return m
M_WATER = water_mat()

# ----------------------------------------------------------------------------- the ground
print("terrain ...", flush=True)
def axis_coords(lo, hi, focus, fine, coarse):
    """grid lines from lo to hi, spaced `fine` near focus values and `coarse` far from them."""
    out = [lo]; x = lo
    while x < hi:
        d = min(abs(x - f) for f in focus)
        step = lerp(fine, coarse, smoothstep(2.0, 14.0, d)); x = min(hi, x + step); out.append(x)
    return out
def terrain_xy(name, fn, xs, ys, mat):
    nx, ny = len(xs) - 1, len(ys) - 1; x0, x1, y0, y1 = xs[0], xs[-1], ys[0], ys[-1]
    verts = []; uvs = []
    for y in ys:
        for x in xs:
            verts.append((x, y, fn(x, y))); uvs.append(((x - x0) / (x1 - x0), (y - y0) / (y1 - y0)))
    faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(ny) for i in range(nx)]
    return mesh_from(name, verts, faces, mat, smooth=True, uvs=uvs)
XS = axis_coords(-NEAR, NEAR, [0.0, 10.0], 0.55, 3.2)
YS = axis_coords(-NEAR, NEAR, [0.0, 5.0], 0.7, 3.2)
GROUND = terrain_xy("GroundNear", gz, XS, YS, M_LAWN)
print("ground grid", len(XS), len(YS), flush=True)
# far land: a ring from NEAR to the sky (rising gently into hills), low poly
def far_land():
    verts = []; faces = []; NS = 48; radii = [NEAR * 0.95, 60, 90, 130, SKY_R * 0.97]
    for j, r in enumerate(radii):
        for i in range(NS):
            a = 2 * math.pi * i / NS; x, y = r * math.cos(a), r * math.sin(a)
            z = gz(max(-NEAR, min(NEAR, x)), max(-NEAR, min(NEAR, y))) - 0.3 if j == 0 else (2.5 + 22.0 * ((j - 1) / 3) ** 1.3) * (0.55 + 0.9 * max(0.0, 0.5 + noise.noise(Vector((math.cos(a) * 2.2, math.sin(a) * 2.2, j * 0.3)))))
            verts.append((x, y, z))
    for j in range(len(radii) - 1):
        for i in range(NS):
            i2 = (i + 1) % NS; faces.append((j * NS + i, j * NS + i2, (j + 1) * NS + i2, (j + 1) * NS + i))
    return mesh_from("FarLand", verts, faces, M_FAR, smooth=True)
far_land()

# ----------------------------------------------------------------------------- the brook (water.stream: V runs downstream)
def brook():
    acc = 0.0; pts = []
    for (x0, y0), (x1, y1) in zip(BROOK, BROOK[1:]):
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / 1.0))
        for i in range(n): t = i / n; pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    pts.append(BROOK[-1])
    verts = []; uvs = []; faces = []; v = 0.0
    for k, (x, y) in enumerate(pts):
        if k > 0: v += math.hypot(x - pts[k - 1][0], y - pts[k - 1][1])
        nx_, ny_ = (pts[min(k + 1, len(pts) - 1)][0] - pts[max(k - 1, 0)][0]), (pts[min(k + 1, len(pts) - 1)][1] - pts[max(k - 1, 0)][1])
        L = math.hypot(nx_, ny_); px, py = -ny_ / L, nx_ / L
        w = BROOK_W * 0.62 * (1 + 0.35 * noise.noise(Vector((x * 0.25, y * 0.25, 1.0))))
        zc = gz(x, y) + 0.22
        for side, u in ((-1, 0.0), (1, 1.0)):
            verts.append((x + px * w * side, y + py * w * side, zc)); uvs.append((u, v / 4.0))
    for k in range(len(pts) - 1):
        faces.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2))
    o = mesh_from("water.stream.brook", verts, faces, M_WATER, uvs=uvs)
    # stones in the bed and along the margins, some breaking the surface
    R = random.Random(4)
    for k in range(0, len(pts), 2):
        x, y = pts[k]
        if abs(y) > 30: continue
        for j in range(2):
            side = R.uniform(-1, 1); px = x + side * BROOK_W * 0.7 + R.gauss(0, 0.15); py = y + R.gauss(0, 0.4)
            r_ = R.uniform(0.08, 0.26) * (1.3 if abs(side) > 0.7 else 1.0)
            st = sphere(f"Stone_{k}_{j}", r_, (px, py, gz(px, py) + 0.14 + r_ * 0.15), M_STONE, seg=8, scale=(1.0, R.uniform(0.7, 1.1), R.uniform(0.45, 0.7)))
            st.rotation_euler = (0, 0, R.uniform(0, 3))
    return o
brook()

# ----------------------------------------------------------------------------- the house (local frame: front wall at -y, door at x=+0.5)
print("house ...", flush=True)
house_parts = []
def H_(o): house_parts.append(o); return o
FLOOR_Z = 0.42                     # house floor above the lawn (it sits on the sills, which sit on the grass)
WALL_H = 2.5; T = 0.06
DOOR_X, DOOR_W, DOOR_H = 0.5, 0.86, 1.98
WINS = [("L", 0.2), ("R", -0.4), ("B", 0.35)]   # windows: left (-x) wall, right (+x) wall, back (+y) wall: centre along the wall
WIN_Z0, WIN_Z1, WIN_W = FLOOR_Z + 0.9, FLOOR_Z + 1.8, 0.72

def clap_wall(name, a, b, z0, z1, openings, out):
    """clapboards from z0 to z1 along the local line a->b (outer face), each board a lapped, tilted slab; openings =
    [(u0, u1, zlo, zhi)] along the wall (metres from a)."""
    a = Vector(a); b = Vector(b); L = (b - a).length; d = (b - a).normalized(); o = Vector(out)
    board = 0.155; n = int((z1 - z0) / board) + 1
    mb = []
    for i in range(n):
        zb = z0 + i * board; zt = min(z1, zb + board + 0.025)
        cuts = [(0.0, L)]
        for (u0, u1, zl, zh) in openings:
            if zt > zl and zb < zh:
                new = []
                for (c0, c1) in cuts:
                    if u1 <= c0 or u0 >= c1: new.append((c0, c1)); continue
                    if u0 > c0: new.append((c0, u0))
                    if u1 < c1: new.append((u1, c1))
                cuts = new
        for (c0, c1) in cuts:
            if c1 - c0 < 0.02: continue
            p0 = a + d * c0; p1 = a + d * c1
            # a lapped board: thick (2 cm) at its foot, thin at its head, so each board steps out over the one below
            v = [p0 + o * 0.022 + Vector((0, 0, zb)), p1 + o * 0.022 + Vector((0, 0, zb)), p1 + o * 0.004 + Vector((0, 0, zt)), p0 + o * 0.004 + Vector((0, 0, zt)),
                 p0 + Vector((0, 0, zb)), p1 + Vector((0, 0, zb)), p1 + Vector((0, 0, zt)), p0 + Vector((0, 0, zt))]
            mb.append(v)
    verts = []; faces = []
    for v in mb:
        k = len(verts); verts += v
        faces += [(k, k + 1, k + 2, k + 3), (k + 4, k, k + 3, k + 7), (k + 1, k + 5, k + 6, k + 2), (k + 4, k + 5, k + 1, k)]
    return H_(mesh_from(name, verts, faces, M_CLAP))

z0w, z1w = FLOOR_Z - 0.12, FLOOR_Z + WALL_H
corners = [(-HW, -HD), (HW, -HD), (HW, HD), (-HW, HD)]
# inner sheathing (a plain board box) so the walls have thickness and the interior is closed
for nm, (a, b), outv in (("F", ((-HW, -HD), (HW, -HD)), (0, -1, 0)), ("R", ((HW, -HD), (HW, HD)), (1, 0, 0)), ("B", ((HW, HD), (-HW, HD)), (0, 1, 0)), ("L", ((-HW, HD), (-HW, -HD)), (-1, 0, 0))):
    L = math.dist(a, b); ops = []
    if nm == "F": ops.append((HW + DOOR_X - DOOR_W / 2, HW + DOOR_X + DOOR_W / 2, FLOOR_Z, FLOOR_Z + DOOR_H))
    for (w, c) in WINS:
        if w == nm:
            uc = (L / 2 + c) if nm in ("R", "L") else (L / 2 - c)
            ops.append((uc - WIN_W / 2, uc + WIN_W / 2, WIN_Z0, WIN_Z1))
    clap_wall(f"Clap_{nm}", (a[0], a[1], 0), (b[0], b[1], 0), z0w, z1w, ops, outv)
    # inner face boards (dark, seen through the door and windows)
    d = Vector((b[0] - a[0], b[1] - a[1], 0)).normalized(); o = Vector(outv)
    segs = [(0.0, L)]
    for (u0, u1, zl, zh) in ops:
        new = []
        for (c0, c1) in segs:
            if u1 <= c0 or u0 >= c1: new.append((c0, c1)); continue
            if u0 > c0: new.append((c0, u0))
            if u1 < c1: new.append((u1, c1))
        segs = new
    for k, (c0, c1) in enumerate(segs):
        c = Vector((a[0], a[1], 0)) + d * ((c0 + c1) / 2) - o * T * 0.5
        H_(box(f"Inner_{nm}{k}", (abs(d.x) * (c1 - c0) + abs(o.x) * T + 0.001, abs(d.y) * (c1 - c0) + abs(o.y) * T + 0.001, WALL_H), (c.x, c.y, FLOOR_Z + WALL_H / 2), M_INTERIOR))
    for (u0, u1, zl, zh) in ops:          # lintels and sills of the inner box over openings
        c = Vector((a[0], a[1], 0)) + d * ((u0 + u1) / 2) - o * T * 0.5
        sz = (abs(d.x) * (u1 - u0) + abs(o.x) * T, abs(d.y) * (u1 - u0) + abs(o.y) * T)
        H_(box(f"InnerTop_{nm}{u0:.1f}", (sz[0], sz[1], FLOOR_Z + WALL_H - zh), (c.x, c.y, (zh + FLOOR_Z + WALL_H) / 2), M_INTERIOR))
        if zl > FLOOR_Z + 0.01: H_(box(f"InnerBot_{nm}{u0:.1f}", (sz[0], sz[1], zl - FLOOR_Z), (c.x, c.y, (zl + FLOOR_Z) / 2), M_INTERIOR))
# corner boards and trim
for (cx, cy) in corners:
    sx, sy = (1 if cx > 0 else -1), (1 if cy > 0 else -1)
    H_(box(f"CornerA_{cx}{cy}", (0.11, 0.03, WALL_H + 0.12), (cx + sx * 0.015 - sx * 0.04, cy + sy * 0.035, FLOOR_Z + WALL_H / 2 - 0.06), M_TRIM))
    H_(box(f"CornerB_{cx}{cy}", (0.03, 0.11, WALL_H + 0.12), (cx + sx * 0.035, cy + sy * 0.015 - sy * 0.04, FLOOR_Z + WALL_H / 2 - 0.06), M_TRIM))
# sill beams (the great beams the house rests on): heavy squared timbers, ends projecting past the corners
for (nm, size, loc) in (("SillF", (2 * HW + 0.5, 0.24, 0.26), (0, -HD + 0.05, FLOOR_Z - 0.25)), ("SillB", (2 * HW + 0.5, 0.24, 0.26), (0, HD - 0.05, FLOOR_Z - 0.25)),
                        ("SillL", (0.24, 2 * HD + 0.1, 0.24), (-HW + 0.05, 0, FLOOR_Z - 0.25)), ("SillR", (0.24, 2 * HD + 0.1, 0.24), (HW - 0.05, 0, FLOOR_Z - 0.25))):
    H_(box(nm, size, loc, M_BEAM, bevel=0.012))
# floor (seen through the door), door, frame, step
H_(box("Floor", (2 * HW - 0.1, 2 * HD - 0.1, 0.05), (0, 0, FLOOR_Z - 0.025), M_INTERIOR))
dx0 = DOOR_X - DOOR_W / 2
for (nm, size, loc) in (("DoorJambL", (0.08, 0.10, DOOR_H + 0.1), (dx0 - 0.04, -HD - 0.02, FLOOR_Z + DOOR_H / 2)), ("DoorJambR", (0.08, 0.10, DOOR_H + 0.1), (dx0 + DOOR_W + 0.04, -HD - 0.02, FLOOR_Z + DOOR_H / 2)),
                        ("DoorHead", (DOOR_W + 0.28, 0.11, 0.12), (DOOR_X, -HD - 0.02, FLOOR_Z + DOOR_H + 0.08)), ("DoorSill", (DOOR_W + 0.2, 0.16, 0.05), (DOOR_X, -HD - 0.03, FLOOR_Z - 0.01))):
    H_(box(nm, size, loc, M_TRIM))
# the door: ledged boards, standing open inwards against the wall (hinged on the left jamb)
dop = math.radians(104)
hinge = Vector((dx0 + 0.02, -HD + 0.02, FLOOR_Z + 0.01))
for i in range(5):
    w = DOOR_W / 5 - 0.004; u = (i + 0.5) * DOOR_W / 5
    c = hinge + Vector((math.cos(dop) * u, math.sin(dop) * u, DOOR_H / 2 - 0.02))
    H_(box(f"DoorBoard{i}", (w, 0.03, DOOR_H - 0.04), tuple(c), M_TRIM, rot=(0, 0, dop)))
for zz in (0.25, 1.0, 1.75):
    c = hinge + Vector((math.cos(dop) * DOOR_W / 2, math.sin(dop) * DOOR_W / 2, zz)) + Vector((math.cos(dop + math.pi / 2), math.sin(dop + math.pi / 2), 0)) * 0.025
    H_(box(f"DoorLedge{zz}", (DOOR_W - 0.06, 0.025, 0.11), tuple(c), M_TRIM, rot=(0, 0, dop)))
# a plank step in front of the door, knocked askew in the landing
H_(box("DoorStep", (1.0, 0.36, 0.06), (DOOR_X + 0.05, -HD - 0.32, 0.14), M_BEAM, rot=(0.03, -0.05, 0.06)))
H_(box("DoorStepBlock", (0.22, 0.22, 0.14), (DOOR_X - 0.3, -HD - 0.3, 0.05), M_BEAM))
H_(box("DoorStepBlock2", (0.22, 0.22, 0.14), (DOOR_X + 0.4, -HD - 0.3, 0.05), M_BEAM))
# windows: frame, sash bars, panes
for (w, c) in WINS:
    if w == "L": centre, along, outv = Vector((-HW, -c, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0))
    elif w == "R": centre, along, outv = Vector((HW, c, 0)), Vector((0, 1, 0)), Vector((1, 0, 0))
    else: centre, along, outv = Vector((-c, HD, 0)), Vector((1, 0, 0)), Vector((0, 1, 0))
    zc = (WIN_Z0 + WIN_Z1) / 2; hgt = WIN_Z1 - WIN_Z0
    def wb(nm, a_len, h_, off_a, off_z, depth, mat):
        sz = (abs(along.x) * a_len + abs(outv.x) * depth, abs(along.y) * a_len + abs(outv.y) * depth, h_)
        p = centre + along * off_a + outv * 0.02 + Vector((0, 0, zc + off_z))
        H_(box(nm, sz, tuple(p), mat))
    wb(f"Win{w}_glass", WIN_W, hgt, 0, 0, 0.01, M_GLASS)
    wb(f"Win{w}_top", WIN_W + 0.16, 0.09, 0, hgt / 2 + 0.04, 0.07, M_TRIM)
    wb(f"Win{w}_sill", WIN_W + 0.22, 0.05, 0, -hgt / 2 - 0.03, 0.10, M_TRIM)
    wb(f"Win{w}_l", 0.07, hgt, -WIN_W / 2 - 0.03, 0, 0.07, M_TRIM); wb(f"Win{w}_r", 0.07, hgt, WIN_W / 2 + 0.03, 0, 0.07, M_TRIM)
    wb(f"Win{w}_mid", WIN_W, 0.04, 0, 0.0, 0.05, M_TRIM); wb(f"Win{w}_bar", 0.03, hgt, 0, 0, 0.05, M_TRIM)
# roof: gable, ridge along local x, wood shingles in courses, overhanging; gable ends in clapboard
RIDGE_Z = FLOOR_Z + WALL_H + 1.0; OV = 0.3
for side in (-1, 1):
    # the roof deck and shingle courses
    n_c = 9
    for i in range(n_c):
        t0 = i / n_c; t1 = (i + 1.25) / n_c
        y0 = side * (HD + OV) * (1 - t0); y1 = side * (HD + OV) * (1 - min(1.0, t1))
        z0 = FLOOR_Z + WALL_H - OV * (1.0 / HD) * 1.0 + (RIDGE_Z - FLOOR_Z - WALL_H + OV / HD) * t0
        z1 = FLOOR_Z + WALL_H - OV * (1.0 / HD) * 1.0 + (RIDGE_Z - FLOOR_Z - WALL_H + OV / HD) * min(1.0, t1)
        x0 = -HW - OV; x1 = HW + OV
        lift = 0.035
        v = [(x0, y0, z0 + lift), (x1, y0, z0 + lift), (x1, y1, z1 + 0.012), (x0, y1, z1 + 0.012),
             (x0, y0, z0), (x1, y0, z0)]
        H_(mesh_from(f"Shingle_{side}_{i}", v, [(0, 1, 2, 3) if side < 0 else (3, 2, 1, 0), (4, 5, 1, 0) if side < 0 else (0, 1, 5, 4)], M_SHINGLE))
    deck = [(-HW - OV, side * (HD + OV), FLOOR_Z + WALL_H - OV / HD), (HW + OV, side * (HD + OV), FLOOR_Z + WALL_H - OV / HD), (HW + OV, 0, RIDGE_Z), (-HW - OV, 0, RIDGE_Z)]
    H_(mesh_from(f"RoofDeck_{side}", deck, [(0, 1, 2, 3) if side > 0 else (3, 2, 1, 0)], M_TRIM))
H_(box("Ridge", (2 * HW + 2 * OV, 0.14, 0.08), (0, 0, RIDGE_Z + 0.04), M_TRIM))
for sx in (-1, 1):   # gables: clapboard triangles approximated by the board run, plus barge boards
    gv = [(sx * HW, -HD, FLOOR_Z + WALL_H), (sx * HW, HD, FLOOR_Z + WALL_H), (sx * HW, 0, RIDGE_Z - 0.03)]
    H_(mesh_from(f"Gable_{sx}", [(sx * (HW + 0.01), y, z) for (_, y, z) in gv], [(0, 1, 2) if sx > 0 else (2, 1, 0)], M_CLAP))
    for side in (-1, 1):
        a = Vector((sx * (HW + OV), side * (HD + OV), FLOOR_Z + WALL_H - OV / HD)); b = Vector((sx * (HW + OV), 0, RIDGE_Z))
        H_(tube(f"Barge_{sx}{side}", [a, b], 0.05, M_TRIM, sides=4, caps=True, smooth=False))
# stove pipe through the roof
H_(cyl("StovePipe", 0.075, 1.0, (-1.4, 0.9, RIDGE_Z - 0.1), plain("M_Pipe", (0.12, 0.11, 0.10), rough=0.6, metallic=0.7), verts=12))
H_(cyl("StovePipeCap", 0.11, 0.05, (-1.4, 0.9, RIDGE_Z + 0.42), plain("M_Pipe2", (0.10, 0.09, 0.08), rough=0.6, metallic=0.7), verts=12))
# inside: a glimpse of Dorothy's little bed and the table through the door
H_(box("BedFrame", (0.8, 1.7, 0.4), (1.5, 1.1, FLOOR_Z + 0.2), M_TRIM))
H_(box("BedQuilt", (0.82, 1.5, 0.12), (1.5, 1.15, FLOOR_Z + 0.46), noisy("M_Quilt", [(0.55, 0.50, 0.42), (0.40, 0.25, 0.20), (0.62, 0.58, 0.48)], scale=12.0, rough=0.9, bump=0.0)))
H_(box("TableTop", (1.0, 0.7, 0.04), (-0.6, 0.5, FLOOR_Z + 0.74), M_TRIM))
for (lx, ly) in ((-1.05, 0.2), (-0.15, 0.2), (-1.05, 0.8), (-0.15, 0.8)): H_(box(f"TableLeg{lx}{ly}", (0.05, 0.05, 0.72), (lx, ly, FLOOR_Z + 0.36), M_TRIM))
LIGHT_IN = light_obj("SunPatchInside", 'AREA', 30.0, (1.0, 0.92, 0.8), (0.3, -0.4, FLOOR_Z + 2.3), direction=(0, 0, -1), size=1.2)

# the house frame in the world: askew (yaw), tilted, the near-left corner sunk on the feet
Mh = Matrix.Translation((HOUSE_C.x, HOUSE_C.y, gz(HOUSE_C.x, HOUSE_C.y) - 0.02)) @ Matrix.Rotation(HOUSE_YAW, 4, 'Z') @ Matrix.Rotation(TILT[0], 4, 'X') @ Matrix.Rotation(TILT[1], 4, 'Y')
for o in house_parts + [LIGHT_IN]: o.matrix_world = Mh @ o.matrix_world
def hw(lx, ly, lz): return Mh @ Vector((lx, ly, lz))
NEAR_CORNER = hw(-HW, -HD, 0)
DOOR_W_ = hw(DOOR_X, -HD - 0.4, FLOOR_Z)
print("near corner", tuple(round(c, 2) for c in NEAR_CORNER), "door", tuple(round(c, 2) for c in DOOR_W_))

# ----------------------------------------------------------------------------- the feet: two legs in dark stockings, silver shoes with pointed toes
def loft(name, spine, sections, mat):
    """a closed loft: spine = [(point, across unit, depth unit, half-width, half-depth)], elliptical sections."""
    verts = []; faces = []; n = sections
    for (p, ax, dp, w, d) in spine:
        for i in range(n):
            a = 2 * math.pi * i / n
            verts.append(tuple(p + ax * math.cos(a) * w + dp * math.sin(a) * d))
    for j in range(len(spine) - 1):
        for i in range(n):
            i2 = (i + 1) % n; faces.append((j * n + i, j * n + i2, (j + 1) * n + i2, (j + 1) * n + i))
    k = len(verts); verts.append(tuple(spine[-1][0])); faces += [((len(spine) - 1) * n + i, (len(spine) - 1) * n + (i + 1) % n, k) for i in range(n)]
    k0 = len(verts); verts.append(tuple(spine[0][0])); faces += [((i + 1) % n, i, k0) for i in range(n)]
    o = mesh_from(name, verts, faces, mat, smooth=True)
    return o

def foot(name, root, dirv, side, splay):
    """one leg from under the beam, lying on its back on the grass: a stockinged shin running out from under the beam,
    the ankle, and a silver shoe standing up from it, toes to the sky, the long pointed toe curling over a little
    towards the reader and splayed outwards."""
    dirv = Vector(dirv).normalized(); up = Vector((0, 0, 1)); lat = dirv.cross(up).normalized()
    p0 = Vector(root); ank = p0 + dirv * 0.34 + up * 0.075
    # the shin: from under the beam out to the ankle, resting on the turf (calf flattened on the ground)
    spine = []
    for t, w in ((-0.25, 0.060), (0.0, 0.058), (0.12, 0.056), (0.22, 0.046), (0.30, 0.036), (0.34, 0.034)):
        c = p0 + dirv * t + up * (0.075 - 0.01 * (1 - t))
        spine.append((c, lat, up, w, w * 0.88))
    loft(f"{name}_shin", spine, 12, M_STOCK)
    # the shoe: spine rises from the heel (on the ground behind the ankle) up past the instep and on to a long point
    toe_dir = (up * math.cos(0.5) + dirv * math.sin(0.5)); toe_dir = (Matrix.Rotation(splay * side, 3, dirv) @ toe_dir).normalized()
    sl = toe_dir.cross(dirv).normalized()                  # across the sole
    sole = sl.cross(toe_dir).normalized()                  # out of the sole (towards the reader)
    if sole.dot(dirv) < 0: sole = -sole
    heel = ank + dirv * 0.02 - toe_dir * 0.03
    sp = []
    prof = [(0.0, 0.034, 0.038), (0.035, 0.046, 0.056), (0.08, 0.050, 0.058), (0.13, 0.052, 0.044), (0.17, 0.047, 0.032),
            (0.215, 0.036, 0.024), (0.26, 0.022, 0.015), (0.30, 0.011, 0.008), (0.33, 0.003, 0.003)]
    for (s_, w, d) in prof:
        curl = 0.06 * max(0.0, (s_ - 0.15) / 0.15) ** 2
        c = heel + toe_dir * s_ + sole * (curl + 0.012) 
        sp.append((c, sl, sole, w, d))
    loft(f"{name}_shoe", sp, 14, M_SILVER)
    # the sole: a thin dark leather layer on the reader's side, a little heel block
    sp2 = [(c + sole * (d * 0.9), sl_, sole_, w * 0.92, 0.006) for (c, sl_, sole_, w, d) in sp[:-1]]
    loft(f"{name}_sole", sp2, 10, M_SOLE)
    box(f"{name}_heel", (0.05, 0.035, 0.035), tuple(heel + sole * 0.045 + toe_dir * 0.025), M_SOLE, rot=(0, 0, math.atan2(dirv.y, dirv.x)))
    return ank
corner_g = Vector((NEAR_CORNER.x, NEAR_CORNER.y, 0))
out_dir = (Vector((0, 0, 0)) - corner_g); out_dir.z = 0; out_dir.normalize()
out_dir = (out_dir + Vector((-0.25, 0.0, 0))).normalized()
lat_g = out_dir.cross(Vector((0, 0, 1))).normalized()
FEET = corner_g + out_dir * 0.18
for k, sgn in enumerate((-1, 1)):
    r0 = FEET + lat_g * sgn * 0.11
    r0.z = gz(r0.x, r0.y) + 0.02
    foot(f"WitchFoot{k}", r0, (out_dir + lat_g * sgn * 0.06), sgn, math.radians(16))

# ----------------------------------------------------------------------------- trees: fruit trees round the lawn, limes and beeches behind
print("trees ...", flush=True)
TREES = []
def T_(*a, **k):
    r = tree(*a, **k); TREES.append(r); return r
# fruit trees (stately: old standards, broad crowns), cards at the branch ends and through the crown
APPLE1 = T_("Apple1", -7.2, 7.8, 8.5, 4.6, "oak", 41, M_BARK, M_APPLE, nlimbs=6, cards_per_tip=1, card_size=1.35, fill=150)
APPLE2 = T_("Apple2", -12.5, -1.5, 8.0, 4.2, "oak", 42, M_BARK, M_APPLE, nlimbs=5, cards_per_tip=1, card_size=1.5, fill=110, detail=0.8)
PEAR = T_("Pear1", 5.4, 15.5, 10.5, 3.6, "elm", 43, M_BARK, M_PEAR, nlimbs=6, cards_per_tip=1, card_size=1.5, fill=120)
PLUM = T_("Plum1", -3.5, 17.0, 7.0, 3.6, "maple", 44, M_BARK, M_PLUM, nlimbs=5, cards_per_tip=1, card_size=1.3, fill=90, detail=0.8)
APPLE3 = T_("Apple3", 15.5, 4.0, 8.5, 4.2, "oak", 45, M_BARK, M_APPLE, nlimbs=5, cards_per_tip=1, card_size=1.5, fill=100, detail=0.8)
# behind the reader: a pear and an apple
T_("Pear2", -6.0, -9.5, 9.5, 3.4, "elm", 46, M_BARK, M_PEAR, nlimbs=5, cards_per_tip=1, card_size=1.6, fill=90, detail=0.7)
T_("Apple4", 4.5, -11.0, 7.5, 4.0, "oak", 47, M_BARK, M_APPLE, nlimbs=5, cards_per_tip=0, card_size=2.0, fill=80, detail=0.6)
# far: limes and beeches, cards only, few and large
FAR = dict(nlimbs=5, detail=0.6, cards_per_tip=0)
LIME1 = T_("Lime1", -18.0, 24.0, 17.0, 6.0, "elm", 48, M_SMOOTHBARK, M_LIME, card_size=3.6, fill=50, **FAR)
T_("Lime2", 16.0, 30.0, 18.0, 6.5, "elm", 49, M_SMOOTHBARK, M_LIME, card_size=3.8, fill=50, **FAR)
T_("Beech1", 3.0, 34.0, 16.0, 7.5, "ash", 50, M_SMOOTHBARK, M_BEECH, card_size=4.0, fill=50, **FAR)
T_("Beech2", -27.0, 6.0, 15.0, 7.0, "ash", 51, M_SMOOTHBARK, M_BEECH, card_size=4.0, fill=45, **FAR)
T_("Lime3", 24.0, -6.0, 16.0, 6.0, "elm", 52, M_SMOOTHBARK, M_LIME, card_size=3.8, fill=45, **FAR)
T_("Beech3", -16.0, -22.0, 15.0, 7.0, "ash", 53, M_SMOOTHBARK, M_BEECH, card_size=4.0, fill=45, **FAR)
T_("Lime4", 14.0, -26.0, 17.0, 6.0, "elm", 54, M_SMOOTHBARK, M_LIME, card_size=3.8, fill=45, **FAR)
T_("Beech4", -32.0, 30.0, 16.0, 7.0, "ash", 55, M_SMOOTHBARK, M_BEECH, card_size=4.2, fill=40, **FAR)
T_("Lime5", 34.0, 20.0, 16.0, 6.0, "elm", 56, M_SMOOTHBARK, M_LIME, card_size=4.0, fill=40, **FAR)
# a loose ring of woods and orchard trees on the far side of the greensward (cheap: few large cards, thin limbs)
RF = random.Random(77)
for i in range(16):
    a = 2 * math.pi * i / 16 + RF.uniform(-0.12, 0.12); r = RF.uniform(40, 55)
    x, y = r * math.sin(a), r * math.cos(a)
    if brook_d(x, y)[0] < 4: x += 6
    tree(f"FarTree{i}", x, y, RF.uniform(11, 17), RF.uniform(5, 7), RF.choice(("elm", "ash", "oak")), 90 + i, M_SMOOTHBARK, RF.choice((M_LIME, M_BEECH, M_APPLE)),
         nlimbs=4, detail=0.5, cards_per_tip=0, card_size=5.0, fill=22)

# flowering shrubs (blue hydrangea-like bushes) on the banks: small multi-stemmed trees with bloom cards
def shrub(name, x, y, h, w, seed):
    return tree(name, x, y, h, w, "maple", seed, M_BARK, M_BLOOM, nlimbs=4, detail=0.6, cards_per_tip=1, card_size=0.75, fill=40)
for i, (x, y, h, w) in enumerate([(-5.2, 3.2, 1.6, 1.0), (-9.5, 1.8, 1.9, 1.2), (-4.0, 11.5, 1.7, 1.1), (6.8, 8.5, 1.5, 0.9), (7.5, -3.5, 1.6, 1.0),
                                  (-10.8, 9.5, 2.0, 1.2), (3.0, 12.5, 1.4, 0.9), (-2.2, -6.8, 1.5, 1.0)]):
    shrub(f"Bush{i}", x, y, h, w, 60 + i)

# ----------------------------------------------------------------------------- grass and flower banks
print("grass ...", flush=True)
HOUSE_INV = (Matrix.Rotation(-HOUSE_YAW, 2))
def in_house(x, y, pad=0.0):
    p = HOUSE_INV @ Vector((x - HOUSE_C.x, y - HOUSE_C.y))
    return abs(p.x) < HW + 0.35 + pad and abs(p.y) < HD + 0.35 + pad
def lawn_ok(x, y):
    if in_house(x, y): return 0.0
    if (Vector((x, y)) - FEET.xy).length < 0.55: return 0.0
    d, s = brook_d(x, y)
    if d < BROOK_W * 0.75: return 0.0
    if math.hypot(x - RX, y - RY) < 0.7: return 0.0
    if math.hypot(x - DOOR_W_.x, y - DOOR_W_.y) < 0.8: return 0.25
    return 0.6 + 0.4 * (0.5 + 0.5 * n2(x, y, 2.0, 3.0))
mb = MB(); sb = MB(); R = random.Random(5)
B.scatter_cards(mb, None, R, 30000, 0.3, 8.5, lawn_ok, B.MEADOW_SHORT, height=0.12, width=0.36, solid_from=99, maxcards=2000, centre=(RX, RY + 1.0))
# long grass and flowers on the banks: the brook's margins, the bank on the left, round the tree feet and against the house
fb = MB(); RB = random.Random(9)
def bank_ok(x, y):
    if in_house(x, y): return 0.0
    d, s = brook_d(x, y)
    if d < BROOK_W * 0.72: return 0.0
    bank = (1.0 - smoothstep(BROOK_W * 0.9, BROOK_W * 2.4, d))
    left = math.exp(-((x + 9.0) ** 2 / 9.0 + (y - 4.0) ** 2 / 50.0))
    trees = max([math.exp(-((x - t[1].x) ** 2 + (y - t[1].y) ** 2) / 3.0) for t in TREES[:5]] + [0.0])
    wall = 0.0 if not in_house(x, y, 0.6) else 0.8
    return min(1.0, bank * 0.9 + left * 1.1 + trees * 0.6 + wall)
pl = 0
for i in range(14000):
    x, y = RB.uniform(-16, 16), RB.uniform(-12, 24)
    d_ = bank_ok(x, y)
    if d_ <= 0 or RB.random() > d_: continue
    if math.hypot(x - RX, y - RY) < 1.8: continue
    z = gz(x, y); sc = RB.uniform(0.75, 1.3)
    to_r = Vector((RX - x, RY - y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + RB.gauss(0, 0.5)
    right = Vector((math.cos(ya), math.sin(ya), 0)) * 0.42 * sc
    if RB.random() < 0.6:
        card(fb, (x, y, z - 0.02), right, Vector((0, 0, 0.42 * sc)), RB.choice(B.MEADOW_FLOWER), 0.0, 1.0)
    else:
        card(fb, (x, y, z - 0.02), right * 1.1, Vector((0, 0, 0.62 * sc)), RB.choice(B.MEADOW_LONG), 0.0, 1.0, segs=2,
             bend=Vector((RB.gauss(0, 0.1), RB.gauss(0, 0.1), 0)))
    pl += 1
    if pl > 900: break
print("lawn cards", len(mb.f), "blades", len(sb.f), "bank cards", len(fb.f), flush=True)
o = mb.build("LawnCards", M_MEADOW); set_card_normals(o, lambda p: Vector((0, 0, 1)))
o = fb.build("BankCards", M_BANK); set_card_normals(o, lambda p: Vector((0, 0, 1)))
so = sb.build("GrassBlades", M_BLADES)
if so is not None: set_card_normals(so, lambda p: (Vector((0, 0, 1.0)) + Vector((-p.x, -p.y, 0)).normalized() * 0.8).normalized())

# ----------------------------------------------------------------------------- sky, light, world
SKY_MAT = B.clear_sky_mat("M_SkyDome", SUN_DIR, zenith=(0.10, 0.28, 0.72), horizon=(0.62, 0.78, 0.94), cloud=0.5, strength=1.0,
                          land=((0.16, 0.30, 0.12), (0.42, 0.55, 0.62), 0.02))
SKY = B.sky_dome("SkyDome", SKY_MAT, SKY_R)
light_obj("light.sun", 'SUN', 4.2, (1.0, 0.95, 0.86), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(1.5))
sky_l = light_obj("light.sky", 'SUN', 0.45, (0.70, 0.80, 1.0), (0, 0, 40), direction=(0.1, 0.1, -1.0), angle=math.radians(90)); sky_l.data.use_shadow = False
B.world_sky(zen=(0.20, 0.38, 0.80), hor=(0.70, 0.80, 0.92), ground=(0.10, 0.16, 0.05), strength=1.1)

# ----------------------------------------------------------------------------- anchors and living-scene sources
E = Vector((RX, RY, gz(RX, RY) + EYE_H))
FWD = (Vector((NEAR_CORNER.x + 0.6, NEAR_CORNER.y, 0)) - Vector((RX, RY, 0))).normalized()
B.reader_anchors((RX, RY, gz(RX, RY)), (RX + FWD.x, RY + FWD.y, E.z))
anchor("scene.centre", tuple(NEAR_CORNER))
anchor("house.door", tuple(DOOR_W_))
anchor("witch.feet", tuple(FEET))
sound("birds", "apple", tuple(APPLE1[1] + Vector((0, 0, 1))))
sound("birds", "pear", tuple(PEAR[1]))
sound("birds", "lime", tuple(LIME1[1]))
sound("river", "brook", (9.4, 2.0, gz(9.4, 2.0) + 0.3))
sound("wind-trees", "limes", (2.0, 30.0, 10.0))

page = B.page_preview(E, FWD)
K.apply_transforms()
cams = B.view_cams(E, FWD, extra=[("Cam_Feet", E + Vector((0.6, 0.6, -0.5)), FEET + Vector((0, 0, 0.1)), 35),
                                     ("Cam_Brook", E + Vector((2.5, 1.0, 0)), (9.6, 6.0, gz(9.6, 6.0)), 24),
                                     ("Cam_Wide", Vector((-6.0, -7.0, gz(-6, -7) + 2.6)), (1.0, 6.0, 1.2), 20)])
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "munchkin_house_landing_source.blend"))
K.print_budget()
if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.0, captures_dir=ARGS.captures)
if ARGS.bake or ARGS.export:
    bpy.data.objects.remove(LIGHT_IN)
    B.export_room("munchkin_house_landing.gltf", cams, page=page,
                  keep_names={"M_MeadowCards": "veg.grass.lawn", "M_FlowerBank": "veg.flowers.banks", "M_GrassBlades": "veg.grass.blades",
                              "M_AppleSprays": "veg.crown.apple", "M_PearSprays": "veg.crown.pear", "M_PlumSprays": "veg.crown.plum",
                              "M_LimeSprays": "veg.crown.lime", "M_BeechSprays": "veg.crown.beech", "M_BloomSprays": "veg.shrub.bloom",
                              "M_Brook": "water.stream.brook", "M_SkyDome": "SkyDome", "M_FarLand": "far.land", "M_Lawn": "GroundNear"},
                  keep_uv={"M_Lawn", "M_SkyDome", "M_Brook"},
                  size_for={"M_Lawn": (2048, 512, 1024), "M_FarLand": (512, 64, 128), "M_SkyDome": (2048,), "M_Clapboard": (1024, 256, 1024),
                            "M_FruitBark": (512, 128, 512), "M_SmoothBark": (512, 128, 256), "M_Shingles": (512, 128, 512), "M_SillBeam": (512, 128, 512),
                            "M_HouseTrim": (512, 128, 256), "M_Brook": (256, 64, 256), "M_SilverShoe": (64, 32), "M_Stocking": (128, 64, 128),
                            "M_BrookStones": (256, 64, 256), "M_Interior": (128, 32), "M_Glass": (32, 32)},
                  default_size=(128, 64, 128))
print("DONE")
