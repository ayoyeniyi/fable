"""
Fable: the washing-cisterns where the river meets the sea, on Scheria (The Odyssey, Book VI, Samuel Butler's 1900
prose translation). A chapter step-in room: built ahead of time, served from the server, downloaded by the headset.

"When they reached the water side they went to the washing cisterns, through which there ran at all times enough pure
water to wash any quantity of linen ... Here they unharnessed the mules and turned them out to feed on the sweet juicy
herbage that grew by the water side ... they laid them out by the sea side, where the waves had raised a high beach of
shingle ... Then they got their dinner by the side of the stream, and waited for the sun to finish drying the clothes."
(Book VI)

The moment: early afternoon, bright sun, the linen drying. The reader stands on the grassy bank between the stone
cisterns (left, fed by a channel from the river) and the shingle beach where the washing lies spread out (ahead and to
the right), facing the calm sea. On the left the river runs down between reeds to its mouth; on the right a low rocky
spit juts out into the sea; behind, the unharnessed mule waggon with its wicker body stands on the grass with the pole
down, and the remains of the picnic lie on a cloth: the provisions basket, bread, the goatskin of wine, the golden cruse
of oil and the ball. At the right-hand edge the olive thicket where Ulysses lies, a bed of fallen leaves pressed flat
beneath it (no figure). No people or animals are modelled (the mules are out of sight, a sound at most).

Living scene (docs/LIVING_SCENES.md): water.river.mouth (V downstream), water.ocean.bay, water.pond.cisterns,
veg.grass.bank, veg.reeds.river, veg.crown.olive, veg.shrub.thicket, cloth.washing.shingle, sound.river.mouth,
sound.surf.beach, sound.birds.thicket, sound.wind-trees.olives.

Node names: anchor.reader.entrance, anchor.reader.look, anchor.scene.centre (the washing on the shingle),
anchor.scheria.cisterns, anchor.scheria.waggon, anchor.scheria.thicket; light.sun, light.sky; SkyDome, far.hills.

Axes: metres, +Z up; the reader at the origin facing +Y (north, the sea). The river is on the left (-X).

Run headless (one Blender at a time):
  blender -b -P blender/build_scheria_washing_pools.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_scheria_washing_pools.py -- --render --samples 48 --res 1400 --captures captures/blender/scheria-washing-pools
  blender -b -P blender/build_scheria_washing_pools.py -- --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
ARGS = K.setup("scheria-washing-pools", "out/scheria-washing-pools", 1184, "ScheriaWashingPools", default_samples=48)
import scene_kit_b2 as B
from scene_kit_b2 import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound,
                          light_obj, camera, smoothstep, lerp, n2, fbm2, link, card, tree, blob, set_card_normals, spray_atlas)
OUT = K.OUT; scene = K.scene
rng = random.Random(1184)

EYE_H = 1.55
SUN_DIR = Vector((-0.42, -0.50, 0.76)).normalized()      # afternoon sun behind the reader's left shoulder (south-west)
SEA_Y = 12.5                                             # the waterline
SEA_Z = -0.35
RIVER = [(-9.5, -40), (-8.0, -22), (-6.8, -10), (-6.3, -2), (-6.9, 5), (-8.2, 10.5), (-9.5, 16)]
RIVER_W = 3.2
NEAR = 40.0
SKY_R = 300.0

def poly_d(x, y, poly):
    best = (1e9, 0.0); acc = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy; L = math.sqrt(L2)
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L2))
        d = math.hypot(x - x0 - t * dx, y - y0 - t * dy)
        if d < best[0]: best = (d, acc + t * L)
        acc += L
    return best

def spit_mask(x, y):
    """the low rocky spit on the right, running out to sea north-east"""
    d, s = poly_d(x, y, [(7.0, 9.0), (12.0, 18.0), (17.0, 26.0), (21.0, 31.0)])
    return (1.0 - smoothstep(1.5, 4.5, d)) * (1.0 - smoothstep(10.0, 24.0, s))

def H(x, y):
    # the grassy bank (reader) at ~0.45, falling to the shingle (y 4..8), the storm ridge of shingle (y ~9.5), the shore
    base = 0.45 + 0.25 * fbm2(x, y, 18.0, 3, 2.1) + 0.04 * y * (y < 0) * -1.0
    beach = lerp(0.45, 0.05, smoothstep(3.5, 8.0, y))
    ridge = 0.35 * math.exp(-((y - 9.6) ** 2) / 1.6)
    shore = -0.75 * smoothstep(10.5, 14.5, y)
    h = beach + (base - 0.45) * (1.0 - smoothstep(3.0, 9.0, y)) + ridge + shore
    h += 0.6 * smoothstep(-10, -35, y) + 2.5 * smoothstep(-20, -40, y)       # rising ground inland behind
    h += 0.5 * spit_mask(x, y)
    h -= 0.04 * smoothstep(13, 30, y) * (y - 13)                              # the sea floor shelving
    d, s = poly_d(x, y, RIVER)
    h -= 0.85 * (1.0 - smoothstep(RIVER_W * 0.35, RIVER_W * 1.0, d))
    # the cistern pits are dug into the bank (their own walls are modelled)
    return h

Z0 = H(0, 0)
def gz(x, y): return H(x, y) - Z0
B.set_ground(gz, (0.0, 0.0, EYE_H))

# ----------------------------------------------------------------------------- atlases and materials
print("painting atlases ...", flush=True)
DRYG = [(0.12, 0.20, 0.05), (0.16, 0.24, 0.06), (0.10, 0.17, 0.04), (0.20, 0.26, 0.08), (0.14, 0.22, 0.06)]
DRYT = [(0.32, 0.36, 0.14), (0.38, 0.38, 0.16), (0.28, 0.32, 0.12)]
IMG_GRASS = B.meadow_atlas("A_BankCards", greens=DRYG, tips=DRYT, dry=0.18, seed=17,
                           flowers=[((0.92, 0.88, 0.80), (0.85, 0.65, 0.10), 'daisy'), ((0.85, 0.65, 0.10), (0.6, 0.4, 0.05), 'cup'),
                                    ((0.55, 0.30, 0.62), (0.4, 0.2, 0.5), 'spike'), ((0.90, 0.88, 0.80), (0.9, 0.9, 0.8), 'umbel')])
IMG_OLIVE = spray_atlas("A_OliveSprays", "olive", 51)
M_GRASS = image_mat("M_BankCards", IMG_GRASS, rough=0.8, alpha=True, spec=0.2)
M_OLIVE = image_mat("M_OliveSprays", IMG_OLIVE, rough=0.6, alpha=True, spec=0.3)
M_BARK = B.bark_mat("M_OliveBark", base=(0.22, 0.20, 0.17), dark=(0.08, 0.075, 0.065), light=(0.36, 0.34, 0.30), fissure=True, green=0.1, scale=1.6)

def ground_mat(name="M_Ground"):
    """sun-dried bank grass and herbage to grey shingle and pale sand, wet and dark at the river's edge and the sea's"""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2200, 0)); s = sep_xyz(nt, co, (-2000, -600)); y = s.outputs["Y"]; z = s.outputs["Z"]
    n1 = noise_(nt, co, 0.25, 5, 0.6, loc=(-1700, 300)); n2_ = noise_(nt, co, 2.5, 6, 0.6, loc=(-1700, 100))
    mpb = node(nt, "ShaderNodeMapping", (-1900, -100)); mpb.inputs["Scale"].default_value = (70.0, 70.0, 20.0); nt.links.new(co, mpb.inputs["Vector"])
    fine = noise_(nt, mpb.outputs["Vector"], 1.0, 6, 0.8, loc=(-1700, -100))
    gcol = ramp(nt, [(0.0, c4((0.035, 0.065, 0.015))), (0.4, c4((0.06, 0.10, 0.025))), (0.7, c4((0.11, 0.13, 0.045))), (1.0, c4((0.20, 0.18, 0.09)))], (-1300, 300))
    nt.links.new(math_(nt, 'ADD', math_(nt, 'MULTIPLY', n1.outputs["Fac"], 0.7, (-1500, 300)), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.4, (-1500, 200)), (-1400, 250)), gcol.inputs["Fac"])
    # shingle: grey pebbles (voronoi cells), some ochre and white
    vor = voronoi_(nt, co, 14.0, 'F1', (-1700, -400))
    pv = ramp(nt, [(0.0, c4((0.14, 0.13, 0.12))), (0.3, c4((0.22, 0.21, 0.19))), (0.6, c4((0.30, 0.28, 0.25))), (0.85, c4((0.30, 0.25, 0.18))), (1.0, c4((0.40, 0.38, 0.35)))], (-1300, -400))
    wv = node(nt, "ShaderNodeTexWhiteNoise", (-1500, -400)); wv.noise_dimensions = '3D'; nt.links.new(vor.outputs["Position"], wv.inputs["Vector"]); nt.links.new(wv.outputs["Value"], pv.inputs["Fac"])
    edge = voronoi_(nt, co, 14.0, 'DISTANCE_TO_EDGE', (-1700, -650))
    peb = mix_rgb(nt, 'MULTIPLY', maprange(nt, edge.outputs["Distance"], 0.0, 0.08, 0.0, 1.0, (-1300, -650)), c4((0.35, 0.32, 0.28)), pv.outputs["Color"], (-1100, -500))
    sand = ramp(nt, [(0.3, c4((0.42, 0.38, 0.30))), (0.7, c4((0.52, 0.47, 0.37)))], (-1300, -850)); nt.links.new(n2_.outputs["Fac"], sand.inputs["Fac"])
    # where: grass on the bank (y < ~4 and inland), shingle beyond, sand at the waterline
    shing = maprange(nt, math_(nt, 'ADD', y, math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 2.5, (-1500, -1100)), (-1350, -1100)), 4.5, 6.5, 0.0, 1.0, (-1200, -1100))
    col = mix_rgb(nt, 'MIX', shing, gcol.outputs["Color"], peb, (-800, 200))
    sandm = maprange(nt, y, 11.0, 12.6, 0.0, 1.0, (-1200, -1300))
    col = mix_rgb(nt, 'MIX', sandm, col, sand.outputs["Color"], (-600, 200))
    wet = maprange(nt, z, -0.25 - Z0 + 0.0, -0.45 - Z0, 0.0, 1.0, (-1200, -1500))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', wet, 0.55, (-1000, -1500)), col, c4((0.45, 0.42, 0.38)), (-400, 200))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, wet, 0, 1, 0.9, 0.35, (-300, -300)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'ADD', fine.outputs["Fac"], math_(nt, 'MULTIPLY', edge.outputs["Distance"], 3.0, (-600, -700)), (-400, -600)), 0.3, 0.01, (0, -400))
    return m
M_GROUND = ground_mat()
M_FAR = noisy("M_FarHills", [(0.10, 0.12, 0.06), (0.16, 0.17, 0.09), (0.24, 0.24, 0.16)], scale=0.04, rough=0.95, bump=0.0)
M_STONE = noisy("M_CisternStone", [(0.13, 0.12, 0.10), (0.22, 0.20, 0.16), (0.30, 0.27, 0.21)], scale=5.0, rough=0.85, bump=0.9, bump_dist=0.015, warp=1.2, ao=0.6)
M_ROCK = noisy("M_SpitRock", [(0.07, 0.065, 0.06), (0.14, 0.13, 0.11), (0.22, 0.20, 0.17)], scale=2.0, rough=0.85, bump=1.0, bump_dist=0.03, warp=1.5, ao=0.5)
M_PEBBLE = noisy("M_Pebbles", [(0.12, 0.11, 0.10), (0.20, 0.19, 0.17), (0.30, 0.27, 0.22)], scale=6, rough=0.6, bump=0.2)
def water_mat(name, deep, shallow, rough=0.06):
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-1200, 0)); n = noise_(nt, co, 1.2, 4, 0.6, loc=(-900, 0))
    r = ramp(nt, [(0.0, c4(deep)), (1.0, c4(shallow))], (-600, 0)); nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    fine = noise_(nt, co, 8.0, 4, 0.6, loc=(-900, -300)); bump_from(nt, b, fine.outputs["Fac"], 0.15, 0.03, (0, -300))
    return m
M_SEA = water_mat("M_Sea", (0.01, 0.05, 0.07), (0.03, 0.12, 0.14))
M_RIVER = water_mat("M_River", (0.02, 0.05, 0.04), (0.06, 0.10, 0.08))
M_POOL = water_mat("M_CisternWater", (0.03, 0.06, 0.05), (0.07, 0.11, 0.09), rough=0.03)
M_WOOD = wood("M_WaggonWood", base=(0.26, 0.17, 0.09), dark=(0.10, 0.06, 0.03), light=(0.38, 0.27, 0.15), scale=1.5, rough=(0.5, 0.75))
M_WICKER = noisy("M_Wicker", [(0.30, 0.22, 0.12), (0.42, 0.32, 0.18), (0.50, 0.40, 0.24)], scale=40, rough=0.8, bump=0.8, bump_dist=0.004, stretch=(1, 1, 8))
M_LEATHER = noisy("M_Goatskin", [(0.14, 0.08, 0.04), (0.24, 0.15, 0.08)], scale=10, rough=0.6, bump=0.4)
M_GOLD = plain("M_Gold", (0.78, 0.56, 0.20), rough=0.25, metallic=0.8)
M_BREAD = noisy("M_Bread", [(0.42, 0.25, 0.10), (0.58, 0.38, 0.17)], scale=9, rough=0.8, bump=0.4)
M_PICNIC = noisy("M_PicnicCloth", [(0.55, 0.50, 0.40), (0.62, 0.57, 0.46)], scale=50, rough=0.9, bump=0.1)
M_BALL = noisy("M_Ball", [(0.45, 0.08, 0.05), (0.20, 0.05, 0.04), (0.55, 0.40, 0.12)], scale=14, rough=0.7, bump=0.2)
M_LITTER = noisy("M_LeafBed", [(0.18, 0.15, 0.09), (0.28, 0.24, 0.14), (0.22, 0.24, 0.12)], scale=30, rough=0.9, bump=0.6, bump_dist=0.006)
def linen_mat(name="M_Washing"):
    """the washing: white linen shirts and robes, saffron and purple woven wool, a red-bordered girdle (colour per
    piece from the 'tone' attribute; a fine weave)."""
    m, nt, b = new_mat(name)
    a = node(nt, "ShaderNodeAttribute", (-800, 0)); a.attribute_name = "tone"
    co = obj_coords(nt, (-1000, -300)); n = noise_(nt, co, 300.0, 3, 0.5, loc=(-800, -300))
    col = mix_rgb(nt, 'MULTIPLY', 0.12, a.outputs["Color"], n.outputs["Color"], (-500, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9; b.inputs["Sheen Weight"].default_value = 0.3
    return m
M_WASH = linen_mat()

# ----------------------------------------------------------------------------- terrain, sea, river, far hills
print("terrain ...", flush=True)
def axis_coords(lo, hi, focus, fine, coarse):
    out = [lo]; x = lo
    while x < hi:
        d = min(abs(x - f) for f in focus); x = min(hi, x + lerp(fine, coarse, smoothstep(2.0, 14.0, d))); out.append(x)
    return out
XS = axis_coords(-NEAR, NEAR, [0.0, -6.5], 0.55, 3.5)
YS = axis_coords(-NEAR, 26.0, [0.0, 9.5], 0.6, 3.0)
verts = []; uvs = []
for y in YS:
    for x in XS:
        verts.append((x, y, gz(x, y))); uvs.append(((x - XS[0]) / (XS[-1] - XS[0]), (y - YS[0]) / (YS[-1] - YS[0])))
nx = len(XS) - 1
faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(len(YS) - 1) for i in range(nx)]
mesh_from("GroundNear", verts, faces, M_GROUND, smooth=True, uvs=uvs)
print("ground grid", len(XS), len(YS), flush=True)
# the sea: a disc of water from the shore out (vertices every ~2.5 m near, coarser far)
sv = []; sf = []; ring = []
rs = [0, 6, 14, 26, 45, 80, 140, 260]
for j, r in enumerate(rs):
    for i in range(64):
        a = math.pi * i / 63
        sv.append((math.cos(a) * (r + 40) * (1 if r else 0) + (0 if r else (i / 63 - 0.5) * 80), SEA_Y - 2 + math.sin(a) * r, SEA_Z - Z0))
for j in range(len(rs) - 1):
    for i in range(63):
        sf.append((j * 64 + i, j * 64 + i + 1, (j + 1) * 64 + i + 1, (j + 1) * 64 + i))
mesh_from("water.ocean.bay", sv, sf, M_SEA, uvs=[((v[0] + 300) / 600, (v[1] + 300) / 600) for v in sv])
# the river: a ribbon from upstream to its mouth, V downstream
pts = []
for (x0, y0), (x1, y1) in zip(RIVER, RIVER[1:]):
    L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / 1.0))
    for i in range(n): t = i / n; pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
pts.append(RIVER[-1])
rv = []; ruv = []; rf = []; vv = 0.0
for k, (x, y) in enumerate(pts):
    if k: vv += math.hypot(x - pts[k - 1][0], y - pts[k - 1][1])
    a_ = pts[min(k + 1, len(pts) - 1)]; b_ = pts[max(k - 1, 0)]; dx, dy = a_[0] - b_[0], a_[1] - b_[1]; L = math.hypot(dx, dy)
    px, py = -dy / L, dx / L; w = RIVER_W * 0.48 * (1 + 0.5 * smoothstep(5, 16, y))
    zc = max(gz(x, y) + 0.55, SEA_Z - Z0 + 0.02) if y < 11 else SEA_Z - Z0 + 0.02
    for side, u in ((-1, 0.0), (1, 1.0)): rv.append((x + px * w * side, y + py * w * side, zc)); ruv.append((u, vv / 5.0))
for k in range(len(pts) - 1): rf.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2))
mesh_from("water.river.mouth", rv, rf, M_RIVER, uvs=ruv)
def far_hills():
    vs = []; fs = []; NS = 72; radii = [NEAR * 0.98, 70, 120, 200, SKY_R * 0.95]
    for j, r in enumerate(radii):
        for i in range(NS + 1):
            a = math.pi * 0.92 + (math.pi * 1.16) * i / NS                     # the landward half (south), round to the two coasts
            x, y = r * math.cos(a), r * math.sin(a) * 0.9
            if j == 0: z = gz(max(-NEAR, min(NEAR, x)), max(-NEAR, min(26, y))) - 0.2
            else:
                ridge = 0.5 + 0.5 * noise.noise(Vector((math.cos(a) * 2.0, math.sin(a) * 2.0, 0.3 * j)))
                z = (3 + j * 9) * (0.4 + ridge) * (1.0 if y < 0 else max(0.0, 1.0 - y / 25))
            vs.append((x, y, z))
    for j in range(len(radii) - 1):
        for i in range(NS):
            fs.append((j * (NS + 1) + i, j * (NS + 1) + i + 1, (j + 1) * (NS + 1) + i + 1, (j + 1) * (NS + 1) + i))
    return mesh_from("FarHills", vs, fs, M_FAR, smooth=True)
far_hills()

# ----------------------------------------------------------------------------- the washing-cisterns: three stone pits fed by a channel from the river
print("cisterns ...", flush=True)
CIS = [(-3.6, -2.6), (-3.6, -0.7), (-3.5, 1.2)]
CW_, CD_ = 1.5, 1.6
rs_ = random.Random(3)
def stone_block(nm, c, size, yaw):
    o = box(nm, size, c, M_STONE, rot=(rs_.uniform(-0.03, 0.03), rs_.uniform(-0.03, 0.03), yaw + rs_.uniform(-0.04, 0.04)), bevel=0.04)
    return o
for k, (cx, cy) in enumerate(CIS):
    top = gz(cx, cy) + 0.12
    # walls of roughly squared blocks, two courses
    for side in range(4):
        for course in range(2):
            n_ = 3
            for i in range(n_):
                t = (i + 0.5) / n_ - 0.5
                if side in (0, 1):
                    yy = cy + (CD_ / 2 if side == 0 else -CD_ / 2); xx = cx + t * CW_
                    stone_block(f"Cis{k}_{side}{course}{i}", (xx + course * 0.12 * (i % 2), yy, top - 0.15 - course * 0.28), (CW_ / n_ - 0.02, 0.28, 0.27), 0.0)
                else:
                    xx = cx + (CW_ / 2 if side == 2 else -CW_ / 2); yy = cy + t * CD_
                    stone_block(f"Cis{k}_{side}{course}{i}", (xx, yy + course * 0.1 * (i % 2), top - 0.15 - course * 0.28), (0.28, CD_ / n_ - 0.02, 0.27), 0.0)
    box(f"CisFloor{k}", (CW_, CD_, 0.1), (cx, cy, top - 0.75), M_STONE)
    mesh_from(f"Pool{k}", [(cx - CW_ / 2 + 0.1, cy - CD_ / 2 + 0.1, top - 0.32), (cx + CW_ / 2 - 0.1, cy - CD_ / 2 + 0.1, top - 0.32),
                           (cx + CW_ / 2 - 0.1, cy + CD_ / 2 - 0.1, top - 0.32), (cx - CW_ / 2 + 0.1, cy + CD_ / 2 - 0.1, top - 0.32)], [(0, 1, 2, 3)], M_POOL,
              uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
# the feed channel from the river along the west side of the pits (stone-lined), with spouts into each
for k in range(9):
    y = -3.6 + k * 0.7; x = -4.65
    for s in (-1, 1): stone_block(f"Chan{k}{s}", (x + s * 0.28, y, gz(x, y) - 0.02), (0.18, 0.68, 0.22), 0.0)
mesh_from("ChannelWater", [(-4.55, -3.9, gz(-4.6, -3.9) - 0.04), (-4.75, -3.9, gz(-4.6, -3.9) - 0.04), (-4.75, 2.3, gz(-4.6, 2.3) - 0.04), (-4.55, 2.3, gz(-4.6, 2.3) - 0.04)],
          [(0, 1, 2, 3)], M_POOL, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
box("Spout", (0.5, 0.18, 0.08), (-4.4, -0.7, gz(-4.4, -0.7) - 0.05), M_STONE)

# ----------------------------------------------------------------------------- the washing laid out on the shingle
print("washing ...", flush=True)
WASH = MB()
tone_cols = []
PIECES = [((1.8, 7.0), 1.4, 1.0, 0.2, (0.84, 0.82, 0.76)), ((3.6, 7.6), 1.2, 0.8, -0.3, (0.80, 0.78, 0.72)), ((0.2, 8.4), 1.6, 1.1, 0.5, (0.62, 0.42, 0.10)),
          ((4.9, 6.2), 0.9, 0.7, 0.1, (0.86, 0.84, 0.78)), ((2.6, 9.1), 1.5, 0.9, -0.15, (0.36, 0.09, 0.14)), ((-1.3, 7.3), 1.0, 0.8, 0.8, (0.82, 0.80, 0.74)),
          ((6.2, 8.4), 1.3, 0.9, 0.35, (0.78, 0.76, 0.70)), ((1.0, 10.2), 1.8, 0.35, 0.1, (0.70, 0.12, 0.08))]
for (c, L, W, yaw, colr) in PIECES:
    ca, sa = math.cos(yaw), math.sin(yaw); rows = []
    for j in range(7):
        row = []
        for i in range(9):
            u = (i / 8 - 0.5) * L; v = (j / 6 - 0.5) * W
            x = c[0] + u * ca - v * sa; y = c[1] + u * sa + v * ca
            z = gz(x, y) + 0.04 + 0.05 * abs(noise.noise(Vector((x * 2.2, y * 2.2, 0.7)))) + 0.03 * max(0.0, math.sin(u * 9.0 + v * 2.0))
            edge = max(abs(i / 8 - 0.5), abs(j / 6 - 0.5)) * 2
            row.append(WASH.vert((x, y, z), (i / 8, j / 6), 0.15 * edge ** 2, tint=(colr[1], colr[2])))
            tone_cols.append(colr)
        rows.append(row)
    for j in range(6):
        for i in range(8): WASH.face(rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i])
wo = WASH.build("cloth.washing.shingle", M_WASH)
ta = wo.data.color_attributes.new("tone", 'BYTE_COLOR', 'POINT')
for i, cc in enumerate(tone_cols): ta.data[i].color = (*cc, 1.0)
wo.data.color_attributes.active_color = wo.data.color_attributes["sway"]

# pebbles and cobbles scattered on the shingle near the reader and round the cloths
PB = MB(); rp = random.Random(9)
for i in range(420):
    x = rp.uniform(-6, 9); y = rp.uniform(4.5, 12.5)
    if rp.random() > 0.15 + 0.45 * smoothstep(6, 10, y): continue
    r_ = rp.uniform(0.03, 0.11) * (1.6 if rp.random() < 0.08 else 1.0)
    B.blob(PB, (x, y, gz(x, y) + r_ * 0.15), (r_, r_ * rp.uniform(0.7, 1.0), r_ * rp.uniform(0.45, 0.7)), i, sub=1, rough=0.12)
PB.build("Pebbles", M_PEBBLE, sway=False)
# the rocky spit and rocks along the shore on the right
RK = MB(); rr = random.Random(12)
for i in range(46):
    s = rr.uniform(0, 1); x = lerp(7.5, 20.0, s) + rr.gauss(0, 1.4); y = lerp(10.0, 30.0, s) + rr.gauss(0, 1.2)
    r_ = rr.uniform(0.4, 1.4) * (1.0 - 0.4 * s)
    B.blob(RK, (x, y, gz(x, y) + r_ * 0.1), (r_ * 1.3, r_, r_ * 0.6), 100 + i, sub=1, rough=0.3)
RK.build("SpitRocks", M_ROCK, sway=False)

# ----------------------------------------------------------------------------- the mule waggon, unharnessed, pole down; the picnic
print("waggon ...", flush=True)
WG = Vector((4.6, -3.6)); WYAW = math.radians(28)
Rw = Matrix.Rotation(WYAW, 3, 'Z')
def wp(x, y, z): return tuple(Vector((WG.x, WG.y, gz(WG.x, WG.y))) + Rw @ Vector((x, y, z)))
WR = 0.45
for sx in (-1, 1):
    for sy in (-1, 1):
        c = Vector(wp(sx * 0.62, sy * 0.85, WR))
        bpy.ops.mesh.primitive_torus_add(major_radius=WR - 0.03, minor_radius=0.035, major_segments=24, minor_segments=6, location=tuple(c), rotation=(0, math.pi / 2, WYAW))
        K._finish(bpy.context.active_object, M_WOOD, smooth=True)
        cyl(f"Hub{sx}{sy}", 0.07, 0.16, tuple(c), M_WOOD, verts=10, rot=(0, math.pi / 2, WYAW))
        for k in range(4):
            a = k * math.pi / 4
            d = Rw @ Vector((0, math.cos(a), math.sin(a)))
            box(f"Spoke{sx}{sy}{k}", (0.035, 0.035, 2 * (WR - 0.05)), tuple(c), M_WOOD, rot=(a, 0, WYAW)) if False else \
                tube(f"Spoke{sx}{sy}{k}", [c - d * (WR - 0.05), c + d * (WR - 0.05)], 0.018, M_WOOD, sides=5, caps=False)
    cyl(f"Axle{sx}", 0.04, 1.4, wp(sx * 0.0, sx * 0.85, WR), M_WOOD, verts=8, rot=(0, math.pi / 2, WYAW))
box("WaggonBed", (1.15, 2.0, 0.06), wp(0, 0, WR + 0.15), M_WOOD, rot=(0, 0, WYAW))
for (nm, size, loc) in (("BodyL", (0.04, 2.0, 0.5), (-0.56, 0, WR + 0.42)), ("BodyR", (0.04, 2.0, 0.5), (0.56, 0, WR + 0.42)),
                        ("BodyF", (1.12, 0.04, 0.5), (0, 0.98, WR + 0.42)), ("BodyB", (1.12, 0.04, 0.3), (0, -0.98, WR + 0.32))):
    box(f"Waggon{nm}", size, wp(*loc), M_WICKER, rot=(0, 0, WYAW), bevel=0.01)
for k in range(5):
    for sx in (-1, 1): cyl(f"Stake{k}{sx}", 0.018, 0.55, wp(sx * 0.57, -0.95 + k * 0.475, WR + 0.42), M_WOOD, verts=6)
# the pole resting on the grass, the yoke beside it
p0 = Vector(wp(0, 1.0, WR + 0.12)); p1 = Vector(wp(0.2, 3.2, 0.0)); p1.z = gz(p1.x, p1.y) + 0.06
tube("WaggonPole", [p0, p1], 0.045, M_WOOD, sides=8)
yk = Vector(wp(0.6, 3.0, 0)); yk.z = gz(yk.x, yk.y) + 0.06
box("Yoke", (1.3, 0.1, 0.08), tuple(yk), M_WOOD, rot=(0, 0, WYAW + 0.4), bevel=0.02)
# the picnic by the stream: a cloth on the grass with the basket, bread, the goatskin of wine, the golden cruse, the ball
PC = Vector((-1.6, -2.6))
pcz = gz(PC.x, PC.y)
box("PicnicCloth", (1.4, 1.0, 0.012), (PC.x, PC.y, pcz + 0.01), M_PICNIC, rot=(0.02, -0.03, 0.4))
lathe("Basket", [(0, 0), (0.22, 0), (0.26, 0.16), (0.27, 0.22), (0.25, 0.22), (0.0, 0.03)], (PC.x - 0.35, PC.y + 0.25, pcz + 0.015), M_WICKER, steps=18)
bpy.ops.mesh.primitive_torus_add(major_radius=0.2, minor_radius=0.015, major_segments=16, minor_segments=4, location=(PC.x - 0.35, PC.y + 0.25, pcz + 0.24), rotation=(math.pi / 2, 0, 0.4))
K._finish(bpy.context.active_object, M_WICKER, smooth=True)
for k in range(3): sphere(f"Loaf{k}", 0.08, (PC.x + 0.1 + k * 0.17, PC.y - 0.2 + k * 0.05, pcz + 0.05), M_BREAD, seg=10, scale=(1, 1, 0.55))
sphere("Goatskin", 0.2, (PC.x + 0.45, PC.y + 0.3, pcz + 0.14), M_LEATHER, seg=12, scale=(1.4, 0.8, 0.65))
lathe("GoldenCruse", [(0, 0), (0.045, 0), (0.07, 0.07), (0.06, 0.14), (0.02, 0.18), (0.018, 0.22), (0.03, 0.23), (0, 0.23)], (PC.x + 0.05, PC.y + 0.25, pcz + 0.015), M_GOLD, steps=14)
sphere("Ball", 0.09, (3.4, 3.6, gz(3.4, 3.6) + 0.07), M_BALL, seg=14)

# ----------------------------------------------------------------------------- olives and the thicket on the right; reeds by the river; grass
print("trees ...", flush=True)
OL = []
for i, (x, y, h, w, sd) in enumerate([(9.2, -1.5, 5.0, 2.8, 61), (10.8, 2.0, 4.4, 2.4, 62), (8.6, 3.2, 3.6, 2.0, 63), (-11.5, -6.0, 5.5, 3.0, 64),
                                      (-13.0, 3.5, 4.8, 2.6, 65), (6.5, -9.0, 5.2, 3.0, 66), (-4.5, -11.0, 5.0, 2.8, 67)]):
    OL.append(tree(f"Olive{i}", x, y, h, w, "oak", sd, M_BARK, M_OLIVE, nlimbs=5, detail=0.8 if i < 3 else 0.6, cards_per_tip=1 if i < 3 else 0,
                   card_size=1.0 if i < 3 else 1.6, fill=90 if i < 3 else 60, lean=(rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4))))
# the thicket: low bushy olives / wild olive scrub, a bed of fallen leaves pressed flat beneath
for i, (x, y) in enumerate([(7.4, 0.0), (8.0, 1.6), (7.0, -1.8), (9.4, 0.6)]):
    tree(f"Scrub{i}", x, y, 1.9, 1.4, "maple", 70 + i, M_BARK, M_OLIVE, nlimbs=5, detail=0.6, cards_per_tip=1, card_size=0.8, fill=45)
lb = MB(); B.blob(lb, (8.1, 0.5, gz(8.1, 0.5) - 0.12), (1.4, 0.8, 0.22), 5, sub=2, rough=0.15); lb.build("LeafBed", M_LITTER, sway=False)
# grass cards on the bank round the reader; reeds along the river; flowers in the herbage by the water
def bank_ok(x, y):
    if y > 4.2 + 1.5 * n2(x, y, 3.0, 1.0): return 0.0
    if poly_d(x, y, RIVER)[0] < RIVER_W * 0.6: return 0.0
    if any(abs(x - cx) < CW_ / 2 + 0.3 and abs(y - cy) < CD_ / 2 + 0.3 for (cx, cy) in CIS) or (-5.0 < x < -4.3 and -4 < y < 2.5): return 0.0
    if math.hypot(x, y) < 0.7: return 0.0
    if abs(x - PC.x) < 0.8 and abs(y - PC.y) < 0.6: return 0.0
    return 0.5 + 0.5 * (0.5 + 0.5 * n2(x, y, 2.0, 3.0))
mb = MB(); R = random.Random(5)
B.scatter_cards(mb, None, R, 30000, 0.3, 9.0, bank_ok, B.MEADOW_SHORT, height=0.16, width=0.34, solid_from=99, maxcards=1500)
for i in range(700):
    x = R.uniform(-12, 4); y = R.uniform(-12, 6)
    d, s = poly_d(x, y, RIVER)
    if not (RIVER_W * 0.45 < d < RIVER_W * 1.0) or R.random() < 0.3: continue
    z = gz(x, y); sc = R.uniform(0.8, 1.3)
    to_r = Vector((-x, -y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + R.gauss(0, 0.5)
    right = Vector((math.cos(ya), math.sin(ya), 0)) * 0.45 * sc
    card(mb, (x, y, z - 0.02), right, Vector((0, 0, 0.9 * sc)), R.choice(B.MEADOW_LONG), 0.0, 1.0, segs=2, bend=Vector((R.gauss(0, 0.1), R.gauss(0, 0.1), 0)))
for i in range(160):
    x = R.uniform(-8, 6); y = R.uniform(-6, 4)
    if bank_ok(x, y) <= 0 or math.hypot(x, y) < 1.5: continue
    z = gz(x, y); to_r = Vector((-x, -y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2
    card(mb, (x, y, z - 0.02), Vector((math.cos(ya), math.sin(ya), 0)) * 0.36, Vector((0, 0, 0.36)), R.choice(B.MEADOW_FLOWER), 0.0, 1.0)
go = mb.build("BankCards", M_GRASS); set_card_normals(go, lambda p: Vector((0, 0, 1)))
print("grass cards", len(mb.f), flush=True)

# ----------------------------------------------------------------------------- sky, light, anchors
SKY_MAT = B.clear_sky_mat("M_SkyDome", SUN_DIR, zenith=(0.08, 0.24, 0.62), horizon=(0.60, 0.74, 0.88), cloud=0.2, strength=1.0)
B.sky_dome("SkyDome", SKY_MAT, SKY_R)
light_obj("light.sun", 'SUN', 4.6, (1.0, 0.95, 0.85), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(1.2))
sl = light_obj("light.sky", 'SUN', 0.5, (0.65, 0.78, 1.0), (0, 0, 40), direction=(0.1, 0.1, -1.0), angle=math.radians(90)); sl.data.use_shadow = False
B.world_sky(zen=(0.14, 0.30, 0.70), hor=(0.62, 0.74, 0.88), ground=(0.18, 0.16, 0.10), strength=1.0)
E = Vector((0.0, 0.0, gz(0, 0) + EYE_H))
B.reader_anchors((0.0, 0.0, gz(0, 0)), (0.0, 1.0, E.z))
anchor("scene.centre", (2.0, 7.8, gz(2.0, 7.8)))
anchor("scheria.cisterns", (CIS[1][0], CIS[1][1], gz(*CIS[1])))
anchor("scheria.waggon", (WG.x, WG.y, gz(WG.x, WG.y)))
anchor("scheria.thicket", (8.1, 0.5, gz(8.1, 0.5)))
sound("river", "mouth", (-7.0, 6.0, gz(-7.0, 6.0) + 0.5))
sound("surf", "beach", (1.0, 12.8, SEA_Z - Z0 + 0.3))
sound("birds", "thicket", (9.0, 0.5, 2.5))
sound("wind-trees", "olives", (-12.0, -1.0, 3.0))
page = B.page_preview(E, (0, 1))
K.apply_transforms()
cams = B.view_cams(E, (0, 1), extra=[("Cam_Washing", E + Vector((0.5, 2.0, 0.2)), (2.5, 8.0, gz(2.5, 8.0)), 24),
                                     ("Cam_Cisterns", E + Vector((-1.0, 2.0, 0.4)), (-3.6, -0.7, gz(-3.6, -0.7) - 0.3), 22),
                                     ("Cam_Waggon", E + Vector((0.5, 0.0, 0.0)), (WG.x, WG.y, gz(WG.x, WG.y) + 0.6), 24),
                                     ("Cam_Wide", Vector((-3.0, -9.0, gz(-3, -9) + 3.0)), (1.0, 8.0, 0.0), 20)])
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "scheria_washing_pools_source.blend"))
K.print_budget()
if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=-0.2, captures_dir=ARGS.captures)
if ARGS.bake or ARGS.export:
    B.export_room("scheria_washing_pools.gltf", cams, page=page,
                  keep_names={"M_BankCards": "veg.grass.bank", "M_OliveSprays": "veg.crown.olive", "M_Washing": "cloth.washing.shingle",
                              "M_Sea": "water.ocean.bay", "M_River": "water.river.mouth", "M_CisternWater": "water.pond.cisterns",
                              "M_SkyDome": "SkyDome", "M_FarHills": "far.hills", "M_Ground": "GroundNear"},
                  keep_uv={"M_Ground", "M_SkyDome", "M_River", "M_Sea"},
                  size_for={"M_Ground": (2048, 512, 1024), "M_FarHills": (512, 64, 128), "M_SkyDome": (2048,), "M_Sea": (512, 64, 256), "M_River": (256, 64, 256),
                            "M_CisternStone": (1024, 256, 1024), "M_SpitRock": (512, 128, 512), "M_Pebbles": (512, 128, 512), "M_OliveBark": (512, 128, 512),
                            "M_WaggonWood": (512, 128, 256), "M_Wicker": (512, 64, 512), "M_Washing": (512, 64, 128), "M_CisternWater": (128, 32, 128),
                            "M_LeafBed": (256, 64, 256), "M_Gold": (64, 32), "M_Ball": (64, 32), "M_Bread": (128, 32, 64)},
                  default_size=(128, 64, 128))
print("DONE")
