"""
Fable scene room: The road below Maybury Hill in the storm (The War of the Worlds, Book I, chapter X) - maybury-hill-storm-road.

"I saw that I was in the road below Maybury Hill ... a flash ... a monstrous tripod, higher than many houses, striding
over the young pine trees ... a walking engine of glittering metal ... a brazen hood ... a huge mass of white metal
like a gigantic fisherman's basket" "the horse went down ... I saw the black bulk of the overturned dog cart and the
silhouette of the wheel still spinning slowly" "a clump of furze ... a shallow pool of water" "the silhouette of
Maybury Hill, with its treetops and roofs black and sharp against the red" "a little one-roomed squatter's hut of
wood, surrounded by a patch of potato garden"

A muddy country road on a moderate incline toward Maybury Hill, just after midnight in a thunderstorm, the late
1890s: the reader stands at the clump of furze beside a shallow pool at the verge; ahead in the road the dog cart lies
overturned, one wheel up, its shafts smashed, the cushions and the lamp flung out; a roadside bank and hedge top on the
left with the dark field beyond (a faint green glow where the third cylinder fell); the edge of a young pine wood on
the right, some trees snapped and leaning, and the squatter's hut in its potato patch with a ditch running to the
pines; beyond, the black silhouette of Maybury Hill with treetops and roofs and the Orphanage, sharp against a red
glare, and far off over the pines on the left the tripod, hood and basket, stopped in mid-stride. The horse is left
out (no convincing figure); no black smoke, red weed or handling-machines, no lamps or modern road.

Light: near darkness. The baked light is a frozen lightning flash (cold violet-white from high in the west), the red
glare low in the north and a faint green afterglow over the field; at runtime the reader's ambience is rain and wind.

Axes: metres, +Z up, +Y north up the road toward the hill. Reader on the east verge facing north-north-west.

Run headless:
  blender -b -P blender/build_maybury_hill_storm_road.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_maybury_hill_storm_road.py -- --cpu --render --samples 48 --res 1024 --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b4 as S
from scene_kit_b4 import (K, new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, lathe, tube, MB, anchor, sound, light_obj, smoothstep, n2, srgb,
                          mb_box, mb_quad, card, set_card_normals)

ARGS = S.setup("maybury-hill-storm-road", 1898, "MayburyHillStormRoad", default_samples=48)
rng = random.Random(1898)
EYE = S.EYE
RW = 2.3
YAW = -14.0
POOL = Vector((3.4, 1.6, 0.0))
CART = Vector((0.2, 6.4, 0.0))
TRIPOD = Vector((-120.0, 210.0, 0.0))
HUT = Vector((10.5, 13.0, 0.0))

def road_x(y): return 0.6 * math.sin(y / 20.0)
def gz(x, y):
    z = 0.075 * y                                                     # the moderate incline
    d = abs(x - road_x(y))
    z += 0.10 * smoothstep(RW - 0.2, RW + 0.6, d)                     # verges a little above the road
    if x < road_x(y): z += 0.7 * smoothstep(RW + 0.4, RW + 1.6, d) * (1 - smoothstep(RW + 2.4, RW + 4.0, d))   # the bank under the hedge, left
    z += 0.04 * noise.noise(Vector((x * 0.9, y * 0.9, 0.3))) + 0.5 * noise.noise(Vector((x * 0.05, y * 0.05, 1.3))) * smoothstep(10, 30, abs(x))
    pd = math.hypot((x - POOL.x) / 1.3, (y - POOL.y) / 0.9)
    z -= 0.12 * (1 - smoothstep(0.6, 1.2, pd))
    return z
Z0 = gz(0, 0)
def h(x, y): return gz(x, y) - Z0

# ----------------------------------------------------------------------------- materials
def mud_mat(name):  # (darker wet sand)
    """Wet sandy mud: Surrey sand washed grey-brown, ruts with water lying in them, pebbles, hoof prints, glossy."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2200, 0)); s = sep_xyz(nt, co, (-2000, 0))
    n1 = noise_(nt, co, 0.8, 5, 0.6, loc=(-1700, 300)); n2_ = noise_(nt, co, 9.0, 5, 0.6, loc=(-1700, 0))
    dx = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', s.outputs["X"], 0.0), None, (-1800, -300))
    rut = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', dx, 0.75)), 0.0, 0.18, 1, 0, (-1600, -300)), maprange(nt, n1.outputs["Fac"], 0.3, 0.6, 0.4, 1.0), (-1400, -300))
    col = mix_rgb(nt, 'MIX', maprange(nt, n2_.outputs["Fac"], 0.3, 0.7, 0, 1), c4(srgb((0.22, 0.19, 0.15))), c4(srgb((0.32, 0.27, 0.21))), (-1200, 200))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', rut, 0.5), col, c4(srgb((0.5, 0.48, 0.45))), (-900, 100))
    verge = node(nt, "ShaderNodeAttribute", (-1600, 600)); verge.attribute_name = "verge"; verge.attribute_type = 'GEOMETRY'
    grass = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.3, 0.7, 0, 1), c4(srgb((0.16, 0.20, 0.08))), c4(srgb((0.24, 0.27, 0.11))), (-1100, 600))
    vg = maprange(nt, math_(nt, 'ADD', verge.outputs["Fac"], math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.3)), 0.55, 0.75, 0, 1, (-900, 600))
    col = mix_rgb(nt, 'MIX', vg, col, grass, (-600, 100))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, math_(nt, 'ADD', rut, math_(nt, 'MULTIPLY', vg, -0.5)), 0, 1, 0.45, 0.08, (-500, -300)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'SUBTRACT', n2_.outputs["Fac"], rut, (-500, -500)), 0.4, 0.02, (0, -500))
    return m


def furze_atlas():
    """Gorse sprays: dense dark spiny green with a few yellow flowers (furze flowers in every month)."""
    S_ = 1024; cv = Canvas(S_, S_); R = random.Random(81); hh = S_ // 2
    for (cx, cy) in ((0, 0), (hh, 0), (0, hh), (hh, hh)):
        cv.clip = (cx + 1, cy + 1, cx + hh - 1, cy + hh - 1)
        for st in range(7):
            x, y = cx + hh / 2 + R.gauss(0, 60), cy + hh - 4; a = R.gauss(0, 0.4); L = R.uniform(250, 460)
            for i in range(30):
                nx, ny = x + math.sin(a) * L / 30, y - math.cos(a) * L / 30; a += R.gauss(0, 0.08)
                cv.line((x, y), (nx, ny), 3.5, 3.0, (0.18, 0.16, 0.10, 1.0))
                for k in range(5):
                    b_ = a + R.uniform(-1.6, 1.6); l2 = R.uniform(10, 26)
                    g = R.choice(((0.10, 0.20, 0.07), (0.14, 0.24, 0.08), (0.12, 0.18, 0.06)))
                    cv.line((nx, ny), (nx + math.sin(b_) * l2, ny - math.cos(b_) * l2), 2.0, 0.6, g + (1.0,))
                if R.random() < 0.18: cv.ellipse(nx + R.gauss(0, 6), ny + R.gauss(0, 6), 5, 4, R.uniform(0, 3), (0.88, 0.72, 0.12, 1.0))
                x, y = nx, ny
    cv.clip = None; cv.bleed(6)
    return np_image("A_Furze", cv.a)


M_MUD = mud_mat("M_Mud")
M_FIELD = noisy("M_FieldDark", [srgb((0.12, 0.15, 0.07)), srgb((0.18, 0.20, 0.10)), srgb((0.10, 0.12, 0.06))], scale=1.0, rough=0.9, bump=0.2)
M_POOL = plain("M_Pool", srgb((0.04, 0.05, 0.06)), rough=0.03)
M_HEDGE = noisy("M_HedgeMass", [srgb((0.06, 0.09, 0.04)), srgb((0.09, 0.13, 0.05)), srgb((0.12, 0.15, 0.07))], scale=12.0, rough=0.85, bump=0.6, bump_dist=0.03)
M_CARTBODY = noisy("M_CartVarnish", [srgb((0.12, 0.06, 0.04)), srgb((0.18, 0.09, 0.05))], scale=4.0, rough=0.2, bump=0.05, coat=0.4)
M_CARTWOOD = noisy("M_CartWood", [srgb((0.34, 0.24, 0.14)), srgb((0.42, 0.30, 0.18))], scale=6.0, rough=0.5, bump=0.1, stretch=(0.5, 0.5, 6))
M_IRON = noisy("M_Iron", [srgb((0.05, 0.05, 0.05)), srgb((0.09, 0.08, 0.07))], scale=20.0, rough=0.4, metallic=0.7)
M_CUSHION = noisy("M_Cushions", [srgb((0.12, 0.14, 0.24)), srgb((0.16, 0.18, 0.30))], scale=30.0, rough=0.8, bump=0.3)
M_LEATHER = noisy("M_Harness", [srgb((0.06, 0.04, 0.03)), srgb((0.10, 0.07, 0.05))], scale=20.0, rough=0.4, bump=0.1)
M_BRASS = plain("M_Brass", srgb((0.70, 0.55, 0.30)), rough=0.25, metallic=1.0)
M_HUT = noisy("M_HutBoards", [srgb((0.22, 0.18, 0.13)), srgb((0.28, 0.23, 0.17)), srgb((0.18, 0.15, 0.11))], scale=3.0, rough=0.8, bump=0.3, stretch=(6, 6, 0.3))
M_TARFELT = noisy("M_TarFelt", [srgb((0.05, 0.05, 0.05)), srgb((0.08, 0.08, 0.07))], scale=8.0, rough=0.5, bump=0.2)
M_PINEBARK = S.bark_mat("M_PineBark", base=srgb((0.30, 0.20, 0.13)), dark=srgb((0.12, 0.08, 0.05)), light=srgb((0.44, 0.30, 0.20)), scale=1.6, green=0.1)
M_TRIPOD = noisy("M_TripodMetal", [srgb((0.20, 0.20, 0.22)), srgb((0.30, 0.28, 0.26))], scale=0.2, rough=0.25, metallic=0.9, bump=0.0)
M_HOOD = plain("M_BrazenHood", srgb((0.55, 0.38, 0.18)), rough=0.3, metallic=1.0)
PINE_PAL = [(0.10, 0.16, 0.08), (0.12, 0.19, 0.09), (0.08, 0.13, 0.06), (0.14, 0.20, 0.10)]
IMG_PINE = S.spray_atlas("A_PineSprays", PINE_PAL, 71, S=1024, per_cell=5, nper=16, size=9.0, shape='palm', bark=(0.25, 0.17, 0.12), depth_max=3, branch_p=0.6)
M_PINE = image_mat("M_PineSprays", IMG_PINE, rough=0.7, alpha=True, spec=0.4)
M_FURZE = image_mat("M_Furze", furze_atlas(), rough=0.75, alpha=True, spec=0.2)
GREENS = [(0.18, 0.24, 0.10), (0.22, 0.28, 0.12), (0.16, 0.20, 0.09)]
TIPS = [(0.30, 0.34, 0.16), (0.34, 0.36, 0.18)]
STRAW = [(0.40, 0.36, 0.22), (0.36, 0.32, 0.20)]
M_GRASS = image_mat("M_VergeGrass", S.grass_atlas("A_VergeGrass", GREENS, TIPS, STRAW, seed=29, dead_share=0.2), rough=0.75, alpha=True, spec=0.2)
M_SKY = S.sky_mat(zenith=srgb((0.008, 0.008, 0.014)), horizon=srgb((0.10, 0.03, 0.025)), ground=srgb((0.008, 0.008, 0.008)), sun_dir=(0.0, 1.0, 0.03),
                  glow=srgb((0.75, 0.16, 0.05)), glow_k=0.55, glow_pow=14.0, disc=False, clouds=0.85, cloud_col=srgb((0.05, 0.035, 0.045)),
                  cloud_dark=srgb((0.012, 0.012, 0.018)), cloud_scale=1.2, land=srgb((0.004, 0.004, 0.005)), land_h=0.05, strength=1.0, land_detail=0.9, land_scale=3.0)

# ----------------------------------------------------------------------------- ground: road, verges, bank, field; the pool
print("ground ...", flush=True)
near = S.polar_terrain("GroundNear", h, M_MUD, r_max=22.0, r0=0.06, rings=40, seg=84, uv_disc=True)
far = S.polar_terrain("FarLand", h, M_FIELD, r_max=500.0, r0=22.0, rings=16, seg=84, r_min=22.0, uv_disc=True)
me = near.data; at = me.attributes.new("verge", 'FLOAT', 'POINT')
at.data.foreach_set("value", [smoothstep(RW - 0.3, RW + 0.4, abs(v.co.x - road_x(v.co.y))) for v in me.vertices])
pool = MB(); prow = []
for i in range(17):
    a = 2 * math.pi * i / 16
    prow.append(pool.vert(Vector((POOL.x + math.cos(a) * 1.25 * (1 + 0.1 * math.sin(3 * a)), POOL.y + math.sin(a) * 0.85, h(POOL.x, POOL.y) + 0.07))))
c = pool.vert(Vector((POOL.x, POOL.y, h(POOL.x, POOL.y) + 0.07)))
for i in range(16): pool.face(c, prow[i], prow[i + 1])
pool.build("water.puddle.pool", M_POOL, sway=False)
for k in range(5):          # rain water lying in the ruts
    y0 = rng.uniform(-6, 16); xr = road_x(y0) + rng.choice((-0.75, 0.75))
    pm = MB(); L = rng.uniform(0.8, 2.2); w = 0.16
    pts = [pm.vert(Vector((xr + sx * w, y0 + sy * L / 2, h(xr, y0 + sy * L / 2) + 0.015))) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    pm.face(*pts); pm.build(f"water.puddle.rut{k}", M_POOL, sway=False)

# ----------------------------------------------------------------------------- the hedge on the bank (left), the pine wood edge (right), the furze
print("vegetation ...", flush=True)
hm = MB()
def hedge(y0, y1):
    n = int((y1 - y0) / 0.6)
    rows_ = []
    for i in range(n + 1):
        y = y0 + (y1 - y0) * i / n; x = road_x(y) - RW - 2.6; z = h(x, y)
        hh = 1.5 + 0.35 * noise.noise(Vector((y * 0.4, 0, 1.0))); w = 0.75 + 0.15 * noise.noise(Vector((y * 0.5, 0, 3.0)))
        prof = [(-w * 0.7, -0.1), (-w, hh * 0.5), (-w * 0.7, hh * 0.9), (0, hh), (w * 0.7, hh * 0.9), (w, hh * 0.5), (w * 0.7, -0.1)]
        rows_.append([hm.vert(Vector((x + a + 0.12 * noise.noise(Vector((y * 1.7, b_ * 2, 0.0))), y, z + b_ + 0.1 * noise.noise(Vector((y * 2.1, a * 3, 4.0))))), (y, k / 6), 0.0) for k, (a, b_) in enumerate(prof)])
    for ra, rb_ in zip(rows_, rows_[1:]):
        for k in range(6): hm.face(ra[k], rb_[k], rb_[k + 1], ra[k + 1])
hedge(-30, 7.5); hedge(10.0, 45)
hm.build("veg.shrub.hedge", M_HEDGE, sway=True)
# a few cards on the hedge top for a ragged edge near the reader
hc = MB(); RH = random.Random(3)
for i in range(160):
    y = RH.uniform(-10, 25); x = road_x(y) - RW - 2.6 + RH.uniform(-0.6, 0.6); z = h(x, y) + 1.4 + RH.uniform(0, 0.4)
    out = Vector((RH.gauss(0, 0.5), RH.gauss(0, 0.5), 1.0)).normalized(); right = out.cross(Vector((1, 0, 0))).normalized() * 0.7
    card(hc, Vector((x, y, z)), right, out * 0.6, RH.choice(S.QUAD), 0.4, 1.0)
hco = hc.build("veg.shrub.hedgetop", M_FURZE)
# young Scots pines on the right, some snapped and leaning; the wood thickens behind
PINES = []
RP = random.Random(5)
for i in range(400):
    x = RP.uniform(RW + 4.0, 45.0); y = RP.uniform(-25, 60)
    if math.hypot(x - HUT.x, y - HUT.y) < 6.5: continue
    if any(math.hypot(x - px, y - py) < 2.6 for px, py, _ in PINES): continue
    PINES.append((x, y, RP.uniform(4.5, 9.0)))
    if len(PINES) > 46: break
for k, (x, y, H_) in enumerate(PINES):
    near_ = math.hypot(x, y) < 18
    if k % 9 == 4 and near_:      # snapped: a broken stem and the top lying across the ditch
        z = h(x, y)
        tube(f"PineSnap{k}", [Vector((x, y, z - 0.2)), Vector((x, y, z + H_ * 0.35))], [0.13, 0.1], M_PINEBARK, sides=6)
        top = S.conifer(f"PineTop{k}", (x, y, z), H_ * 0.65, 400 + k, M_PINEBARK, M_PINE, tiers=5, per_tier=5)
        top.rotation_euler = (math.radians(70), 0, math.radians(200 + k * 7)); top.location = (x, y, z + H_ * 0.35)
        continue
    o = S.conifer(f"Pine{k}", (x, y, h(x, y)), H_, 400 + k, M_PINEBARK, M_PINE, tiers=7 if near_ else 5, per_tier=6 if near_ else 4)
    if k % 7 == 2: o.rotation_euler = (math.radians(rng.uniform(-14, 14)), math.radians(rng.uniform(-14, 14)), 0)
# the clump of furze beside the pool (the reader's side) and more along the verges
fz = MB(); RF = random.Random(7)
def furze(cx, cy, r, hgt, n):
    for k in range(n):
        a = RF.uniform(0, 2 * math.pi); d = r * math.sqrt(RF.random())
        x, y = cx + math.cos(a) * d, cy + math.sin(a) * d; z = h(x, y) + hgt * (1 - (d / r) ** 2) * RF.uniform(0.5, 1.0)
        out = Vector((math.cos(a), math.sin(a), 1.2 * (1 - d / r) + 0.3)).normalized()
        tang = out.cross(Vector((0, 0, 1)));
        if tang.length < 0.1: tang = Vector((1, 0, 0))
        tang.normalize(); bit = out.cross(tang).normalized(); sz = RF.uniform(0.55, 0.9)
        card(fz, Vector((x, y, z)) - (bit * sz) * 0.5, tang * sz, bit * sz + out * sz * 0.3, RF.choice(S.QUAD), 0.2, 1.0)
furze(POOL.x + 1.6, POOL.y - 0.9, 1.1, 1.3, 70)
furze(POOL.x + 2.0, POOL.y + 1.8, 0.8, 1.0, 40)
furze(-RW - 1.4, 2.0, 0.9, 1.0, 40)
furze(RW + 1.5, 14.0, 1.0, 1.2, 45)
fzo = fz.build("veg.shrub.furze", M_FURZE)
set_card_normals(fzo, lambda p: Vector((0, 0, 1)))
gm = MB(); RG = random.Random(9); placed = 0
for i in range(15000):
    r_ = 14 * RG.random() ** 0.8; a = RG.uniform(0, 2 * math.pi); x, y = r_ * math.cos(a), r_ * math.sin(a)
    if abs(x - road_x(y)) < RW + 0.05: continue
    if math.hypot((x - POOL.x) / 1.3, (y - POOL.y) / 0.9) < 1.1: continue
    z = h(x, y); sc = RG.uniform(0.7, 1.2)
    to_r = Vector((-x, -y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + RG.gauss(0, 0.5)
    card(gm, (x, y, z - 0.02), Vector((math.cos(ya), math.sin(ya), 0)) * 0.42 * sc, Vector((RG.gauss(0, 0.08), RG.gauss(0, 0.08), 0.42 * sc)), RG.choice(S.GRASS_LONG), 0.0, 1.0, segs=2,
         bend=Vector((0.1, 0.12, -0.08)) * sc)     # beaten down by the rain
    placed += 1
    if placed > 1300: break
go = gm.build("veg.grass.verges", M_GRASS)
set_card_normals(go, lambda p: Vector((0, 0, 1)))

# ----------------------------------------------------------------------------- the overturned dog cart
print("dog cart ...", flush=True)
cyaw = math.radians(35)
Rc = Matrix.Rotation(cyaw, 3, 'Z') @ Matrix.Rotation(math.radians(80), 3, 'Y')      # rolled onto its left side
cz = h(CART.x, CART.y) + 0.62
def CP(x, y, z): return Vector((CART.x, CART.y, cz)) + Rc @ Vector((x, y, z))
cb = MB()
mb_box(cb, CP(0, 0, 0.0), (1.2, 1.5, 0.05), yaw=0.0)
for sx in (-1, 1): mb_quad(cb, [CP(sx * 0.6, -0.75, 0.0), CP(sx * 0.6, 0.75, 0.0), CP(sx * 0.6, 0.75, 0.55), CP(sx * 0.6, -0.75, 0.55)])
for sy in (-1, 1): mb_quad(cb, [CP(-0.6, sy * 0.75, 0.0), CP(0.6, sy * 0.75, 0.0), CP(0.6, sy * 0.75, 0.55), CP(-0.6, sy * 0.75, 0.55)])
mb_quad(cb, [CP(-0.6, -0.1, 0.55), CP(0.6, -0.1, 0.55), CP(0.6, -0.1, 0.95), CP(-0.6, -0.1, 0.95)])        # back-to-back seat backs
mb_quad(cb, [CP(-0.6, 0.1, 0.55), CP(0.6, 0.1, 0.55), CP(0.6, 0.1, 0.95), CP(-0.6, 0.1, 0.95)])
for sy in (-1, 1): mb_box(cb, CP(0, sy * 0.4, 0.58), (1.18, 0.6, 0.05))
for k in range(5): mb_quad(cb, [CP(-0.6, -0.75 + k * 0.08, 0.1), CP(0.6, -0.75 + k * 0.08, 0.1), CP(0.6, -0.75 + k * 0.08, 0.13), CP(-0.6, -0.75 + k * 0.08, 0.13)])   # louvred dog box
cb.build("CartBody", M_CARTBODY, sway=False)
# the wheels: the lower one crushed under, the upper one in the air (still spinning in the text)
def wheel(name, c, axis, r=0.7, spokes=12, broken=False):
    axis = axis.normalized(); u = axis.cross(Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))).normalized(); v = axis.cross(u)
    rim = [c + (u * math.cos(t) + v * math.sin(t)) * r for t in np.linspace(0, 2 * math.pi, 25)]
    tube(name + "Rim", rim, 0.03, M_CARTWOOD, sides=5, caps=False)
    tube(name + "Tyre", [p + (p - c).normalized() * 0.025 for p in rim], 0.018, M_IRON, sides=4, caps=False)
    for k in range(spokes):
        if broken and k in (3, 4, 8): continue
        t = 2 * math.pi * k / spokes
        tube(f"{name}Spoke{k}", [c, c + (u * math.cos(t) + v * math.sin(t)) * r], [0.025, 0.016], M_CARTWOOD, sides=5)
    tube(name + "Hub", [c - axis * 0.1, c + axis * 0.1], 0.08, M_CARTWOOD, sides=8)
ax = Rc @ Vector((1, 0, 0))
wheel("WheelUp", CP(0.75, 0.0, -0.25), ax)
wheel("WheelDown", CP(-0.75, 0.0, -0.25) + Vector((0, 0, -0.1)), ax, broken=True)
tube("Axle", [CP(-0.8, 0, -0.25), CP(0.8, 0, -0.25)], 0.035, M_IRON, sides=6)
for sx in (-1, 1):
    tube(f"Spring{sx}", [CP(sx * 0.55, -0.6, -0.08), CP(sx * 0.55, 0.0, -0.22), CP(sx * 0.55, 0.6, -0.08)], 0.02, M_IRON, sides=5)
# the shafts, smashed: one splintered off short, the other broken in two with its end in the mud
s0 = CP(0.45, 0.75, -0.05); s1 = s0 + Vector((math.sin(cyaw + 0.2), math.cos(cyaw + 0.2), 0)) * 1.1; s1.z = h(s1.x, s1.y) + 0.35
tube("ShaftA", [s0, s1], [0.045, 0.035], M_CARTWOOD, sides=6)
s2 = s1 + Vector((-0.2, 0.15, 0)); s3 = s2 + Vector((0.9, 1.5, 0)); s2.z = h(s2.x, s2.y) + 0.05; s3.z = h(s3.x, s3.y) + 0.04
tube("ShaftABroken", [s2, s3], [0.035, 0.03], M_CARTWOOD, sides=6)
s4 = CP(-0.45, 0.75, -0.05); s5 = s4 + Vector((math.sin(cyaw - 0.1), math.cos(cyaw - 0.1), 0)) * 0.6
tube("ShaftB", [s4, s5], [0.045, 0.04], M_CARTWOOD, sides=6)
for k in range(5):          # splinters
    q = s5 + Vector((rng.gauss(0, 0.05), rng.gauss(0, 0.05), rng.gauss(0, 0.03)))
    tube(f"Splinter{k}", [s5, q + Vector((math.sin(cyaw) * 0.25, math.cos(cyaw) * 0.25, 0.04))], [0.012, 0.003], M_CARTWOOD, sides=3)
# flung out: a seat cushion, the carriage lamp, a trace of harness in the mud
box("CushionA", (0.55, 0.45, 0.09), (CART.x - 1.4, CART.y - 0.6, h(CART.x - 1.4, CART.y - 0.6) + 0.05), M_CUSHION, rot=(0.1, 0.05, 0.7))
box("CushionB", (0.55, 0.45, 0.09), (CART.x + 1.3, CART.y + 1.4, h(CART.x + 1.3, CART.y + 1.4) + 0.06), M_CUSHION, rot=(0.3, 0.1, -0.4))
lp = Vector((CART.x + 1.6, CART.y - 1.2, 0)); lp.z = h(lp.x, lp.y) + 0.1
lamp = lathe("CarriageLamp", [(0.0, 0.0), (0.06, 0.0), (0.07, 0.08), (0.07, 0.2), (0.05, 0.22), (0.02, 0.3), (0.0, 0.31)], tuple(lp), M_BRASS, steps=8)
lamp.rotation_euler = (math.radians(85), 0, 0.6)
hp = [Vector((CART.x + 0.6 + 0.4 * k, CART.y + 1.6 + 0.6 * k + 0.2 * math.sin(k), 0)) for k in range(6)]
for p in hp: p.z = h(p.x, p.y) + 0.02
tube("Trace", hp, 0.02, M_LEATHER, sides=4)

# ----------------------------------------------------------------------------- the squatter's hut in its potato patch, and the ditch to the pines
HF = K.Frame((HUT.x, HUT.y), math.radians(100))
hz = h(HUT.x, HUT.y)
box("HutBody", (3.0, 2.4, 2.0), (HUT.x, HUT.y, hz + 1.0), M_HUT, rot=(0, 0, math.radians(100)))
rf = MB()
for sg in (-1, 1):
    a = HF.p(-1.7, sg * 1.45, 2.0); b_ = HF.p(1.7, sg * 1.45, 2.0); c_ = HF.p(1.7, 0, 2.7); d = HF.p(-1.7, 0, 2.7)
    a, b_, c_, d = [Vector(q) + Vector((0, 0, hz)) for q in (a, b_, c_, d)]
    mb_quad(rf, [a, b_, c_, d] if sg > 0 else [b_, a, d, c_])
rf.build("HutRoof", M_TARFELT, sway=False)
gb = MB()
for sx in (-1, 1):
    p = [Vector(HF.p(sx * 1.5, -1.2, 2.0)) + Vector((0, 0, hz)), Vector(HF.p(sx * 1.5, 1.2, 2.0)) + Vector((0, 0, hz)), Vector(HF.p(sx * 1.5, 0, 2.6)) + Vector((0, 0, hz))]
    vs = [gb.vert(q) for q in p]; gb.face(*vs)
gb.build("HutGables", M_HUT, sway=False)
box("HutDoor", (0.05, 0.8, 1.7), tuple(Vector(HF.p(-1.52, 0.3, 0.85)) + Vector((0, 0, hz))), M_TARFELT, rot=(0, 0, math.radians(100)))
box("HutWindow", (0.05, 0.5, 0.45), tuple(Vector(HF.p(-1.52, -0.7, 1.3)) + Vector((0, 0, hz))), M_IRON, rot=(0, 0, math.radians(100)))
cyl("HutFlue", 0.07, 1.0, tuple(Vector(HF.p(0.9, 0.5, 2.9)) + Vector((0, 0, hz))), M_IRON, verts=6)
pr = MB()
for r in range(7):          # potato ridges, haulms died back
    y0 = HUT.y - 6.0 + r * 0.75
    for k in range(10):
        x = HUT.x - 5.5 + k * 0.6; z = h(x, y0)
        mb_box(pr, (x, y0, z + 0.06), (0.6, 0.35, 0.18), tilt=(0.0, 0.0))
pr.build("PotatoRidges", M_MUD, sway=False)
w_ = MB()
for k in range(29):
    t0, t1 = k / 29, (k + 1) / 29
    def P(t, s_): x = RW + 1.0 + t * 12.0; y = 9.0 + t * 3.0 + 0.6 * math.sin(t * 6) + s_ * 0.3; return Vector((x, y, h(x, y) - 0.12))
    mb_quad(w_, [P(t0, -1), P(t1, -1), P(t1, 1), P(t0, 1)])
w_.build("water.puddle.ditch", M_POOL, sway=False)

# ----------------------------------------------------------------------------- the tripod, stopped in mid-stride far off on the left (a silhouette)
print("tripod ...", flush=True)
T0 = TRIPOD + Vector((0, 0, h(TRIPOD.x, TRIPOD.y)))
BODY = T0 + Vector((6.0, -4.0, 44.0))
feet = [T0 + Vector((-9.0, 4.0, 0)), T0 + Vector((7.0, 9.0, 0)), T0 + Vector((14.0, -11.0, 0))]
for k, f in enumerate(feet):
    knee = BODY.lerp(f, 0.45) + Vector((3.0 * (1 if k != 1 else -1), 2.0, 6.0))
    tube(f"far.tripod.leg{k}", [BODY, knee, f], [1.1, 0.9, 0.7], M_TRIPOD, sides=8)
hood = lathe("far.tripod.hood", [(0.0, -2.0), (5.0, -1.8), (6.2, 0.0), (5.4, 2.2), (3.5, 3.6), (0.0, 4.2)], tuple(BODY + Vector((0, 0, 1.0))), M_HOOD, steps=16)
hood.rotation_euler = (math.radians(12), 0, math.radians(30))
basket = MB()
bc = BODY + Vector((-1.5, -4.5, -3.5))
for k in range(9):
    a = 2 * math.pi * k / 9
    for j in range(3):
        p0 = bc + Vector((math.cos(a) * 2.2, math.sin(a) * 2.2, -j * 1.6)); p1 = bc + Vector((math.cos(a + 0.7) * 2.2, math.sin(a + 0.7) * 2.2, -(j + 1) * 1.6))
        d = (p1 - p0); u = d.cross(Vector((0, 0, 1))).normalized() * 0.18
        mb_quad(basket, [p0 - u, p0 + u, p1 + u, p1 - u])
basket.build("far.tripod.basket", M_TRIPOD, sway=False)
for k in range(5):           # the articulate ropes of steel, hanging
    a = rng.uniform(0, 2 * math.pi); p0 = BODY + Vector((math.cos(a) * 3.0, math.sin(a) * 3.0, -1.5))
    tube(f"far.tripod.tentacle{k}", [p0, p0 + Vector((rng.uniform(-3, 3), rng.uniform(-3, 3), -8.0)), p0 + Vector((rng.uniform(-5, 5), rng.uniform(-5, 5), -16.0))], [0.25, 0.18, 0.1], M_TRIPOD, sides=5)

# ----------------------------------------------------------------------------- the storm light: a frozen flash, the red glare, the green afterglow
SKY = S.sky_dome(M_SKY, radius=900.0)
S.world(Vector((-0.55, 0.25, 0.8)), sun_energy=0.6, sun_col=(0.78, 0.80, 1.0), sun_angle=8.0,
        sky_cols=(srgb((0.01, 0.01, 0.01)), srgb((0.06, 0.03, 0.03)), srgb((0.015, 0.016, 0.025))), sky_strength=1.0)
bpy.data.objects["light.sun"].name = "light.flash"
light_obj("Lamp.glare", 'AREA', 9000.0, (1.0, 0.30, 0.10), (0.0, 260.0, 20.0), direction=(0, -1, -0.05), size=200.0, size_y=40.0, shape='RECTANGLE')
light_obj("Lamp.greenglow", 'AREA', 6000.0, (0.35, 1.0, 0.45), (-60.0, 20.0, 6.0), direction=(1, 0, -0.1), size=60.0, size_y=12.0, shape='RECTANGLE')
light_obj("Lamp.hutfill", 'POINT', 1.0, (1.0, 0.8, 0.6), (HUT.x - 2.0, HUT.y, hz + 1.2))
RD = Vector((POOL.x - 0.6, POOL.y - 2.1, 0.0)); RD.z = h(RD.x, RD.y)
eye, fwd = S.reader(tuple(RD), YAW)
anchor("scene.centre", tuple(CART + Vector((0, 0, h(CART.x, CART.y)))))
anchor("dogcart", tuple(CART + Vector((0, 0, h(CART.x, CART.y)))))
anchor("tripod", tuple(T0))
sound("rain", "road", (0.0, 4.0, 1.0))
sound("rain", "pines", (12.0, 10.0, 3.0))
sound("wind-trees", "pines", (15.0, 20.0, 6.0))
sound("wind", "field", (-15.0, 5.0, 2.0))
page = S.page_preview(eye, fwd)
cams = S.view_cams(eye, YAW, extra=[
    ("Cam_Page", eye, eye + fwd * 10 + Vector((0, 0, -1.2)), 17),
    ("Cam_Cart", Vector((CART.x + 2.6, CART.y - 2.6, h(CART.x, CART.y) + 1.6)), tuple(CART + Vector((0, 0, h(CART.x, CART.y) + 0.5))), 24),
    ("Cam_Tripod", eye, tuple(BODY), 30),
    ("Cam_Hut", eye, tuple(HUT + Vector((0, 0, hz + 1.2))), 24),
])
S.finish(ARGS, cams, "maybury_hill_storm_road.gltf", page=page, default_exposure=1.6,
         keep_names={"M_PineSprays": "veg.crown.pines", "M_Furze": "veg.shrub.furze", "M_HedgeMass": "veg.shrub.hedge", "M_VergeGrass": "veg.grass.verges",
                     "M_Pool": "water.puddle.pool", "M_TripodMetal": "far.tripod", "M_BrazenHood": "far.tripod.hood", "M_Mud": "GroundNear", "M_FieldDark": "far.land"},
         keep_uv={"M_Mud"},
         size_for={"M_Mud": (2048, 256, 1024), "M_FieldDark": (512, 64), "M_HedgeMass": (512, 64, 256), "M_PineBark": (512, 64, 256),
                   "M_CartVarnish": (256, 64, 128), "M_CartWood": (256, 64, 128), "M_HutBoards": (512, 64, 256), "M_TripodMetal": (256,), "M_BrazenHood": (64,),
                   "M_SkyDome": (1024,)},
         default_size=(256, 64, 128), no_shadow={"M_SkyDome"})
