"""
Fable scene room: Forest Road (The Wonderful Wizard of Oz, chapter VI, "The Cowardly Lion") - forest-road-lion.

"All this time Dorothy and her companions had been walking through the thick woods. The road was still paved with
yellow brick, but these were much covered by dried branches and dead leaves from the trees, and the walking was not
at all good. There were few birds in this part of the forest, for birds love the open country where there is plenty
of sunshine. But now and then there came a deep growl from some wild animal hidden among the trees." "Just as he
spoke there came from the forest a terrible roar, and the next moment a great Lion bounded into the road."

A stretch of the yellow brick road through deep woods: the old bricks worn, gapped, mossy and half buried under
dried branches and drifts of dead leaves; tall dark trunks close on both sides, ferns and undergrowth between them,
the canopy closing overhead so that the light comes down in a few scattered shafts; ahead-left of the reader the
undergrowth is broken and flattened in a gap at the forest edge, a fallen bough kicked aside on the bricks - where the
Lion bounded into the road. No animals are modelled (the Lion is suggested, not shown); no Kalidahs, ditch, river,
poppies or Emerald City.

Light: day, the sun high in the south, shaded and gloomy under the canopy with shafts and pools of sun.

Axes: metres, +Z up, +Y along the road (north). Reader on the road facing north-west toward the gap.

Run headless:
  blender -b -P blender/build_forest_road_lion.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_forest_road_lion.py -- --cpu --render --samples 32 --res 1280 --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b4 as S
from scene_kit_b4 import (K, new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, lathe, tube, MB, anchor, sound, smoothstep, n2, srgb,
                          mb_box, mb_quad, card, set_card_normals)

ARGS = S.setup("forest-road-lion", 1900, "ForestRoadLion", default_samples=48)
rng = random.Random(1900)
EYE = S.EYE
RW = 1.6              # half width of the road
SUN_DIR = Vector((0.25, -0.62, 0.74)).normalized()     # toward the sun: south, a little east, ~48 degrees up
YAW = -38.0
GAP = Vector((-3.6, 5.2, 0.0))                         # where the undergrowth is broken (the Lion's way)

def road_x(y): return 0.9 * math.sin(y / 14.0) - 0.6 * math.sin(y / 31.0)
def gz(x, y):
    d = abs(x - road_x(y))
    z = 0.25 * noise.noise(Vector((x * 0.12, y * 0.12, 0.6))) + 0.05 * noise.noise(Vector((x * 0.8, y * 0.8, 2.6)))
    z += 0.18 * smoothstep(RW + 0.2, RW + 2.0, d)          # the road sits a little low, worn into the ground
    z += 0.6 * noise.noise(Vector((x * 0.03, y * 0.03, 4.0))) * smoothstep(8, 30, d)
    return z
Z0 = gz(0, 0)
def h(x, y): return gz(x, y) - Z0

# ----------------------------------------------------------------------------- materials
def road_mat(name):
    """Old yellow brick in herringbone-less stretcher bond along the road: yellows from straw to ochre, worn rounded,
    gapped and sunk in places, moss and soil in the joints, dark leaf mould drifting over the edges and patches."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0)); s = sep_xyz(nt, co, (-2200, 0))
    vec = node(nt, "ShaderNodeCombineXYZ", (-2000, 0)); nt.links.new(s.outputs["Y"], vec.inputs["X"]); nt.links.new(s.outputs["X"], vec.inputs["Y"])
    br = node(nt, "ShaderNodeTexBrick", (-1700, 0))
    br.inputs["Scale"].default_value = 1.0; br.inputs["Mortar Size"].default_value = 0.012; br.inputs["Mortar Smooth"].default_value = 0.4
    br.inputs["Brick Width"].default_value = 0.23; br.inputs["Row Height"].default_value = 0.115; br.inputs["Color2"].default_value = (1, 1, 1, 1)
    br.inputs["Color1"].default_value = (0, 0, 0, 1); br.inputs["Mortar"].default_value = (0, 0, 0, 1)
    br.inputs["Bias"].default_value = 0.0
    nt.links.new(vec.outputs[0], br.inputs["Vector"])
    tone = sep_xyz(nt, br.outputs["Color"], (-1500, 0)).outputs["X"]
    yel = ramp(nt, [(0.0, c4(srgb((0.62, 0.48, 0.16)))), (0.5, c4(srgb((0.74, 0.60, 0.22)))), (1.0, c4(srgb((0.82, 0.70, 0.32))))], (-1300, 0))
    nt.links.new(tone, yel.inputs["Fac"])
    n1 = noise_(nt, co, 0.7, 5, 0.6, loc=(-1700, 400)); n2_ = noise_(nt, co, 6.0, 5, 0.6, loc=(-1700, 700))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n2_.outputs["Fac"], 0.3, 0.7, 0.0, 0.4, (-1100, 400)), yel.outputs["Color"], (0.55, 0.5, 0.4, 1), (-1000, 100))
    joint = math_(nt, 'MULTIPLY', br.outputs["Fac"], 1.0, (-1300, -300))
    moss = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.4, 0.6, 0, 1, (-1100, -500)), c4(srgb((0.16, 0.16, 0.08))), c4(srgb((0.24, 0.30, 0.10))), (-900, -400))
    col = mix_rgb(nt, 'MIX', joint, col, moss, (-700, 100))
    mossy = maprange(nt, n1.outputs["Fac"], 0.55, 0.68, 0, 0.7, (-1000, -800))
    col = mix_rgb(nt, 'MIX', mossy, col, c4(srgb((0.22, 0.28, 0.10))), (-500, 100))
    # leaf mould drifting from the edges
    xr = node(nt, "ShaderNodeAttribute", (-1300, -1100)); xr.attribute_name = "edge"; xr.attribute_type = 'GEOMETRY'
    drift = maprange(nt, math_(nt, 'ADD', xr.outputs["Fac"], math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.5)), 0.55, 0.75, 0, 1, (-1000, -1100))
    col = mix_rgb(nt, 'MIX', drift, col, c4(srgb((0.24, 0.16, 0.09))), (-300, 100))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, joint, 0, 1, 0.75, 0.95, (-300, -300)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.3), joint, (-400, -600)), 0.5, 0.01, (0, -600))
    return m


def floor_mat(name):
    """Forest floor: dark leaf litter of browns and rusts, some old pale leaves, twigs, soil and moss."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2000, 0))
    v = voronoi_(nt, co, 14.0, 'F1', (-1700, 0))
    n1 = noise_(nt, co, 0.5, 4, 0.6, loc=(-1700, 300)); n2_ = noise_(nt, co, 25.0, 4, 0.6, loc=(-1700, -300))
    lv = ramp(nt, [(0.0, c4(srgb((0.14, 0.10, 0.07)))), (0.3, c4(srgb((0.26, 0.18, 0.11)))), (0.55, c4(srgb((0.36, 0.25, 0.14)))), (0.8, c4(srgb((0.20, 0.16, 0.10)))), (1.0, c4(srgb((0.44, 0.36, 0.24))))], (-1400, 0))
    nt.links.new(sep_xyz(nt, v.outputs["Color"], (-1550, -100)).outputs["X"], lv.inputs["Fac"])
    col = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.55, 0.7, 0, 0.7, (-1200, 300)), lv.outputs["Color"], c4(srgb((0.18, 0.24, 0.08))), (-1000, 100))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, v.outputs["Distance"], 0.0, 0.3, 0.6, 0.0, (-1200, -400)), col, (0.4, 0.4, 0.4, 1), (-800, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.92
    bump_from(nt, b, math_(nt, 'ADD', v.outputs["Distance"], math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.5)), 0.6, 0.015, (0, -500))
    return m


def fern_atlas(name, seed):
    """2 x 2 cells of fern fronds (bracken-like and shield-fern-like): a curved rachis with tapering pinnae."""
    S_ = 1024; cv = Canvas(S_, S_); R = random.Random(seed); hh = S_ // 2
    pal = [(0.22, 0.34, 0.10), (0.27, 0.40, 0.12), (0.20, 0.30, 0.09), (0.33, 0.42, 0.14), (0.42, 0.40, 0.16)]
    for ci, (cx, cy) in enumerate(((0, 0), (hh, 0), (0, hh), (hh, hh))):
        cv.clip = (cx + 1, cy + 1, cx + hh - 1, cy + hh - 1)
        for f in range(3 if ci < 2 else 4):
            x, y = cx + hh / 2 + R.gauss(0, 30), cy + hh - 4
            a = R.gauss(0, 0.35); L = R.uniform(330, 470) * (0.8 if ci >= 2 else 1.0); n = 22
            col = R.choice(pal); prev = (x, y)
            for i in range(n):
                t = i / n; a += R.gauss(0.0, 0.03) + 0.03 * (1 if a > 0 else -1)
                nx, ny = x + math.sin(a) * L / n, y - math.cos(a) * L / n
                cv.line((x, y), (nx, ny), 3.0 * (1 - t) + 1, 3.0 * (1 - t) + 0.8, (0.20, 0.22, 0.10, 1.0))
                if t > 0.12:
                    pl = (hh * 0.33) * math.sin(math.pi * min(1.0, (t - 0.1) / 0.92)) * (0.7 if ci >= 2 else 1.0)
                    for sg in (-1, 1):
                        pa = a + sg * 1.25
                        px, py = nx + math.sin(pa) * pl, ny - math.cos(pa) * pl
                        cv.line((nx, ny), (px, py), 1.4, 0.6, (col[0] * 0.8, col[1] * 0.8, col[2] * 0.8, 1.0))
                        m_ = int(pl / 7)
                        for k in range(1, m_):
                            u = k / m_; qx, qy = nx + (px - nx) * u, ny + (py - ny) * u
                            ln = (1 - u) * 9 + 3
                            for sg2 in (-1, 1):
                                qa = pa + sg2 * 1.1
                                cv.ellipse(qx + math.sin(qa) * ln * 0.5, qy - math.cos(qa) * ln * 0.5, 2.4, ln * 0.55, qa, col + (1.0,), tip=0.4)
                x, y = nx, ny
    cv.clip = None; cv.bleed(6)
    return np_image(name, cv.a)


def leaves_atlas(name, seed, n=34):
    """Dead leaves and twigs lying on the road: a scatter of curled brown, rust and yellow leaves on transparency."""
    S_ = 1024; cv = Canvas(S_, S_); R = random.Random(seed); hh = S_ // 2
    pal = [(0.42, 0.26, 0.10), (0.52, 0.32, 0.12), (0.36, 0.20, 0.08), (0.62, 0.46, 0.18), (0.30, 0.18, 0.09), (0.55, 0.40, 0.22)]
    for (cx, cy) in ((0, 0), (hh, 0), (0, hh), (hh, hh)):
        cv.clip = (cx + 1, cy + 1, cx + hh - 1, cy + hh - 1)
        for k in range(n):
            x, y = cx + R.uniform(30, hh - 30), cy + R.uniform(30, hh - 30)
            a = R.uniform(0, 6.28); s_ = R.uniform(14, 30); col = R.choice(pal)
            cv.ellipse(x, y, s_ * 0.5, s_, a, col + (1.0,), tip=0.4)
            cv.line((x - math.sin(a) * s_, y + math.cos(a) * s_), (x + math.sin(a) * s_ * 0.8, y - math.cos(a) * s_ * 0.8), 0.9, 0.5, (col[0] * 0.6, col[1] * 0.6, col[2] * 0.6, 1.0))
        for k in range(4):
            x, y = cx + R.uniform(40, hh - 40), cy + R.uniform(40, hh - 40); a = R.uniform(0, 6.28); L = R.uniform(60, 160)
            cv.line((x, y), (x + math.cos(a) * L, y + math.sin(a) * L), 2.5, 1.5, (0.18, 0.14, 0.10, 1.0))
    cv.clip = None; cv.bleed(6)
    return np_image(name, cv.a)


M_ROAD = road_mat("M_YellowBrick")
M_FLOOR = floor_mat("M_ForestFloor")
M_BARK = S.bark_mat("M_Bark", base=srgb((0.24, 0.21, 0.18)), dark=srgb((0.08, 0.07, 0.06)), light=srgb((0.36, 0.33, 0.29)), scale=0.9, green=0.5)
M_BARK2 = S.bark_mat("M_BarkSmooth", base=srgb((0.33, 0.32, 0.29)), dark=srgb((0.14, 0.14, 0.12)), light=srgb((0.44, 0.43, 0.40)), fissure=False, scale=1.2, green=0.6)
M_DEADWOOD = noisy("M_DeadWood", [srgb((0.26, 0.20, 0.14)), srgb((0.34, 0.27, 0.19)), srgb((0.18, 0.14, 0.10))], scale=3.0, rough=0.9, bump=0.3, stretch=(4, 4, 0.3))
CANOPY_PAL = [(0.16, 0.26, 0.08), (0.20, 0.31, 0.10), (0.14, 0.23, 0.07), (0.24, 0.33, 0.11), (0.18, 0.28, 0.09)]
IMG_CAN = S.spray_atlas("A_CanopySprays", CANOPY_PAL, 61, S=1024, per_cell=3, nper=6, size=14.0, shape='round')
M_CAN = image_mat("M_CanopySprays", IMG_CAN, rough=0.7, alpha=True, spec=0.3)
UNDER_PAL = [(0.18, 0.30, 0.09), (0.22, 0.34, 0.11), (0.15, 0.26, 0.08), (0.28, 0.38, 0.13)]
IMG_UND = S.spray_atlas("A_Undergrowth", UNDER_PAL, 62, S=1024, per_cell=4, nper=5, size=11.0, shape='ellipse')
M_UND = image_mat("M_Undergrowth", IMG_UND, rough=0.65, alpha=True, spec=0.35)
M_FERN = image_mat("M_Ferns", fern_atlas("A_Ferns", 63), rough=0.65, alpha=True, spec=0.3)
M_LITTER = image_mat("M_LeafLitter", leaves_atlas("A_LeafLitter", 64), rough=0.85, alpha=True, spec=0.2)
M_SKY = S.sky_mat(zenith=srgb((0.30, 0.50, 0.80)), horizon=srgb((0.70, 0.78, 0.80)), ground=srgb((0.10, 0.14, 0.08)), sun_dir=SUN_DIR,
                  glow=srgb((1.0, 0.95, 0.80)), glow_k=0.5, glow_pow=8.0, clouds=0.3, cloud_col=srgb((0.98, 0.98, 0.96)),
                  cloud_dark=srgb((0.72, 0.76, 0.82)), cloud_scale=0.8, land=None, strength=1.0)

# ----------------------------------------------------------------------------- ground and road
print("ground ...", flush=True)
near = S.polar_terrain("GroundNear", h, M_FLOOR, r_max=40.0, r0=0.1, rings=34, seg=72, uv_disc=True)
rd = MB()
ys = [-45 + 90 * k / 120 for k in range(121)]
xs_u = [-1.0 + 2.0 * i / 8 for i in range(9)]
rows = []
for y in ys:
    rx = road_x(y); row = []
    for u in xs_u:
        x = rx + u * RW
        z = h(x, y) + 0.03 - 0.03 * abs(u) ** 3 + 0.012 * noise.noise(Vector((x * 2.2, y * 2.2, 3.0)))
        z -= 0.04 * max(0.0, noise.noise(Vector((x * 0.5, y * 0.5, 8.0))))   # sunk places
        row.append(rd.vert(Vector((x, y, z)), (x, y)))
    rows.append(row)
for j in range(len(ys) - 1):
    for i in range(len(xs_u) - 1): rd.face(rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i])
ro = rd.build("Road", M_ROAD, sway=False)
me = ro.data; at = me.attributes.new("edge", 'FLOAT', 'POINT')
at.data.foreach_set("value", [abs(v.co.x - road_x(v.co.y)) / RW for v in me.vertices])

# ----------------------------------------------------------------------------- the trees: tall dark trunks close on both sides, canopy closing overhead
print("trees ...", flush=True)
trunks = []
R2 = random.Random(7)
for i in range(900):
    x = R2.uniform(-48, 48); y = R2.uniform(-48, 48)
    d = abs(x - road_x(y))
    if d < RW + 0.9: continue
    if math.hypot(x - GAP.x, y - GAP.y) < 2.2: continue
    if any(math.hypot(x - tx, y - ty) < (3.2 if math.hypot(x, y) < 16 else 4.5) for tx, ty, _, _ in trunks): continue
    r_ = math.hypot(x, y)
    if r_ > 46: continue
    trunks.append((x, y, R2.uniform(0.18, 0.42) * (1.2 if R2.random() < 0.2 else 1.0), R2.uniform(17, 26)))
    if len(trunks) > 105: break
print("trunks", len(trunks), flush=True)
for k, (x, y, rr, H_) in enumerate(trunks):
    near_ = math.hypot(x, y) < 15
    z = h(x, y) - 0.2; Rk = random.Random(k)
    lean = Vector((Rk.gauss(0, 0.4), Rk.gauss(0, 0.4), 0))
    pts = [Vector((x, y, z)), Vector((x, y, z + 0.6)), Vector((x, y, z + H_ * 0.4)) + lean * 0.4, Vector((x, y, z + H_ * 0.75)) + lean, Vector((x, y, z + H_)) + lean * 1.4]
    rads = [rr * 1.7, rr * 1.15, rr * 0.95, rr * 0.75, rr * 0.4]
    tube(f"Trunk{k}", pts if near_ or math.hypot(x, y) < 28 else [pts[0], pts[2], pts[4]], rads if near_ or math.hypot(x, y) < 28 else [rads[0], rads[2], rads[4]], M_BARK if k % 3 else M_BARK2, sides=10 if near_ else 5, caps=False)
    if near_ and Rk.random() < 0.5:     # a dead lower limb or two
        for j in range(Rk.randint(1, 2)):
            zz = z + Rk.uniform(4, 9); a = Rk.uniform(0, 6.28)
            p0 = Vector((x, y, zz)); p1 = p0 + Vector((math.cos(a) * 1.6, math.sin(a) * 1.6, Rk.uniform(-0.3, 0.6)))
            tube(f"DeadLimb{k}{j}", [p0, p1], [rr * 0.25, 0.02], M_DEADWOOD, sides=5)
    # the crown high up: limbs to an envelope and spray cards (the canopy), leaving a few gaps for shafts of sun
    shape = (0.08, 1.0, 0.45)
    cb = Vector((x, y, z)) + (pts[3] - pts[0]) * 0.92
    S.tree(f"Crown{k}", tuple(cb), H_ * 0.55, Rk.uniform(4.5, 6.5), "birch", 900 + k, M_BARK, M_CAN,
           nlimbs=5 if near_ else 3, detail=0.6 if near_ else 0.3, cards_per_tip=1, card_size=2.8 if near_ else 3.6, fill=44 if near_ else 16, shape=shape)

# an understory of young trees and hollies between the trunks, closing the view at eye height
R4 = random.Random(21); saps = []
for i in range(600):
    x = R4.uniform(-40, 40); y = R4.uniform(-40, 40); r_ = math.hypot(x, y)
    if r_ < 7 or r_ > 38: continue
    if abs(x - road_x(y)) < RW + 2.0: continue
    if math.hypot(x - GAP.x, y - GAP.y) < 4.0: continue
    if any(math.hypot(x - tx, y - ty) < 1.2 for tx, ty, _, _ in trunks) or any(math.hypot(x - sx, y - sy) < 3.0 for sx, sy in saps): continue
    saps.append((x, y))
    H_ = R4.uniform(3.5, 7.0)
    S.tree(f"Sapling{i}", (x, y, h(x, y)), H_, H_ * 0.38, "broad", 1500 + i, M_BARK2, M_UND, nlimbs=3, detail=0.3, cards_per_tip=1, card_size=1.7, fill=14,
           shape=(0.25, 1.0, 0.45))
    if len(saps) > 42: break
print("saplings", len(saps), flush=True)

# ----------------------------------------------------------------------------- undergrowth and ferns between the trunks; the broken gap
print("undergrowth ...", flush=True)
fm = MB(); um = MB(); R3 = random.Random(9)
def gap_k(x, y): return 1.0 - smoothstep(0.8, 2.4, math.hypot(x - GAP.x, y - GAP.y))
nf = 0; nu = 0
for i in range(9000):
    r_ = 30 * R3.random() ** 0.7; a = R3.uniform(0, 2 * math.pi); x, y = r_ * math.cos(a), r_ * math.sin(a)
    d = abs(x - road_x(y))
    if d < RW + 0.15: continue
    z = h(x, y); gk = gap_k(x, y)
    if R3.random() < 0.55 * gk: continue
    if d < RW + 0.8 and R3.random() < 0.5: continue
    clump = 0.5 + 0.5 * n2(x, y, 3.0, 2.0)
    if R3.random() > clump * 1.3: continue
    to_r = Vector((-x, -y, 0)).normalized()
    if R3.random() < (0.62 if r_ < 9 else 0.3):
        if nf > 1200: continue
        for j in range(2):
            ya = R3.uniform(0, 6.28); dirv = Vector((math.cos(ya), math.sin(ya), 0))
            sc = R3.uniform(0.7, 1.25)
            flat = 0.55 + 0.45 * gk     # trampled fronds lie flatter in the gap
            right = Vector((-dirv.y, dirv.x, 0)) * 0.55 * sc
            up = (dirv * (0.45 + 0.4 * flat) + Vector((0, 0, 0.75 * (1 - flat * 0.7)))) * sc
            card(fm, (x, y, z - 0.03), right, up, R3.choice(S.QUAD), 0.0, 1.0, bend=Vector((0, 0, -0.2 * sc)), segs=2)
            nf += 1
    else:
        if nu > 900: continue
        sc = R3.uniform(0.6, 1.3) * (1.0 + 0.8 * smoothstep(6, 18, r_))
        for j in range(3):
            ya = R3.uniform(0, 6.28); dirv = Vector((math.cos(ya), math.sin(ya), 0))
            right = Vector((-dirv.y, dirv.x, 0)) * 0.9 * sc
            up = Vector((0, 0, 0.95 * sc)) + dirv * 0.25 * sc
            card(um, (x, y, z - 0.05 + j * 0.35 * sc), right, up, R3.choice(S.QUAD), 0.1 + j * 0.25, 0.5 + j * 0.25)
            nu += 1
fo = fm.build("veg.leaves.ferns", M_FERN)
set_card_normals(fo, lambda p: Vector((0, 0, 1)))
uo = um.build("veg.shrub.undergrowth", M_UND)
set_card_normals(uo, lambda p: Vector((0, 0, 1)))
print("ferns", nf, "undergrowth", nu, flush=True)
# dead leaves and dried branches over the road
lm = MB()
for i in range(420):
    y = R3.uniform(-18, 22); u = R3.uniform(-1.05, 1.05); x = road_x(y) + u * RW
    if R3.random() > 0.35 + 0.65 * abs(u) ** 1.5: continue
    a = R3.uniform(0, 6.28); s_ = R3.uniform(0.35, 0.7)
    z = h(x, y) + 0.04 + 0.003 * (i % 5)
    p = [Vector((x + math.cos(a + q * math.pi / 2 + math.pi / 4) * s_ * 0.7, y + math.sin(a + q * math.pi / 2 + math.pi / 4) * s_ * 0.7, z)) for q in range(4)]
    cell = R3.choice(S.QUAD)
    mb_quad(lm, p, ((cell[0], cell[1]), (cell[2], cell[1]), (cell[2], cell[3]), (cell[0], cell[3])))
lo = lm.build("LeafLitter", M_LITTER, sway=False)
set_card_normals(lo, lambda p: Vector((0, 0, 1)))
for k in range(26):
    y = R3.uniform(-15, 20); u = R3.uniform(-1.0, 1.0); x = road_x(y) + u * RW
    a = R3.uniform(0, 6.28); L = R3.uniform(0.6, 2.4)
    p0 = Vector((x, y, h(x, y) + 0.06)); p1 = p0 + Vector((math.cos(a) * L, math.sin(a) * L, 0.02))
    mid = p0.lerp(p1, 0.5) + Vector((0, 0, 0.04))
    tube(f"Branch{k}", [p0, mid, p1], [0.035 * L / 2, 0.02, 0.008], M_DEADWOOD, sides=5)
    for j in range(R3.randint(1, 3)):
        q = p0.lerp(p1, R3.uniform(0.2, 0.8)); b_ = a + R3.choice((-1, 1)) * R3.uniform(0.4, 1.0)
        tube(f"Twig{k}{j}", [q, q + Vector((math.cos(b_) * 0.5, math.sin(b_) * 0.5, R3.uniform(0.0, 0.2)))], [0.012, 0.004], M_DEADWOOD, sides=4)
# the bough kicked into the road at the gap, and torn undergrowth
bg = GAP + Vector((1.8, -0.4, 0))
tube("FallenBough", [Vector((GAP.x + 0.4, GAP.y + 0.2, h(GAP.x + 0.4, GAP.y + 0.2) + 0.1)), Vector((bg.x, bg.y, h(bg.x, bg.y) + 0.12)), Vector((bg.x + 1.4, bg.y - 0.9, h(bg.x + 1.4, bg.y - 0.9) + 0.08))],
     [0.11, 0.08, 0.04], M_DEADWOOD, sides=7)
for j in range(5):
    q = Vector((bg.x + 0.4 * j - 0.6, bg.y - 0.2 * j, h(bg.x, bg.y) + 0.1)); b_ = R3.uniform(0, 6.28)
    tube(f"BoughTwig{j}", [q, q + Vector((math.cos(b_) * 0.8, math.sin(b_) * 0.8, R3.uniform(0.1, 0.5)))], [0.03, 0.006], M_DEADWOOD, sides=4)
log = tube("FallenLog", [Vector((8.0, -6.0, h(8.0, -6.0) + 0.25)), Vector((12.5, -1.0, h(12.5, -1.0) + 0.3))], [0.4, 0.32], M_DEADWOOD, sides=10)

# ----------------------------------------------------------------------------- the far forest: a painted wall of trunks and foliage closing the view (far.*: unlit)
def forest_wall_img():
    W_, H_ = 2048, 512; cv = Canvas(W_, H_); R = random.Random(77)
    yy = np.linspace(0, 1, H_)[:, None]
    cv.a[..., 0] = (0.10 + 0.10 * (1 - yy)) * 1.0; cv.a[..., 1] = (0.13 + 0.12 * (1 - yy)); cv.a[..., 2] = (0.10 + 0.08 * (1 - yy)); cv.a[..., 3] = 1.0
    for k in range(260):      # distant crowns (top two thirds), hazier toward the top
        x = R.uniform(0, W_); y = R.uniform(0, H_ * 0.62); rr = R.uniform(25, 70)
        g = R.choice(((0.12, 0.18, 0.10), (0.15, 0.21, 0.11), (0.10, 0.15, 0.08), (0.18, 0.24, 0.13)))
        haze = 0.35 * (1 - y / (H_ * 0.62))
        col = tuple(c * (1 - haze) + h_ * haze for c, h_ in zip(g, (0.42, 0.50, 0.52)))
        cv.ellipse(x, y, rr, rr * 0.7, 0, col + (1.0,))
    for k in range(320):      # trunks
        x = R.uniform(0, W_); w = R.uniform(2, 14); far_ = R.random()
        col = (0.10 + 0.12 * far_, 0.09 + 0.11 * far_, 0.08 + 0.10 * far_, 1.0)
        cv.line((x, H_ * R.uniform(0.15, 0.5)), (x + R.gauss(0, 4), H_), w * 0.6, w, col)
    for k in range(300):      # undergrowth along the bottom
        x = R.uniform(0, W_); y = R.uniform(H_ * 0.72, H_); rr = R.uniform(12, 40)
        g = R.choice(((0.08, 0.13, 0.06), (0.10, 0.16, 0.07), (0.07, 0.10, 0.05)))
        cv.ellipse(x, y, rr, rr * 0.6, 0, g + (1.0,))
    return np_image("A_ForestWall", cv.a)
def far_mat(name, img):
    m, nt, b = new_mat(name)
    t = node(nt, "ShaderNodeTexImage", (-600, 0)); t.image = img; t.extension = 'REPEAT'
    uv = node(nt, "ShaderNodeUVMap", (-900, 0)); nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    nt.links.new(t.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 1.0
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    return m
M_FARWALL = far_mat("M_ForestWall", forest_wall_img())
fw = MB(); NSEG = 48; RFW = 46.0
for i in range(NSEG):
    a0, a1 = 2 * math.pi * i / NSEG, 2 * math.pi * (i + 1) / NSEG
    p = [Vector((math.cos(a) * RFW, math.sin(a) * RFW, z)) for a, z in ((a0, -3.0), (a1, -3.0), (a1, 24.0), (a0, 24.0))]
    u0, u1 = 3 * i / NSEG, 3 * (i + 1) / NSEG
    mb_quad(fw, [p[1], p[0], p[3], p[2]], ((u1, 0), (u0, 0), (u0, 1), (u1, 1)))
fwo = fw.build("far.forest", M_FARWALL, sway=False)
fwo.visible_shadow = False

# ----------------------------------------------------------------------------- sky, light, anchors, sounds
SKY = S.sky_dome(M_SKY, radius=600.0)
S.world(SUN_DIR, sun_energy=5.0, sun_col=(1.0, 0.94, 0.82), sun_angle=1.5,
        sky_cols=(srgb((0.10, 0.12, 0.08)), srgb((0.55, 0.65, 0.70)), srgb((0.30, 0.48, 0.80))), sky_strength=0.9)
RD = Vector((road_x(0.0) + 0.3, 0.0, 0.0)); RD.z = h(RD.x, RD.y) + 0.03
eye, fwd = S.reader(tuple(RD), YAW)
anchor("scene.centre", (GAP.x, GAP.y, h(GAP.x, GAP.y)))
anchor("lion.gap", (GAP.x, GAP.y, h(GAP.x, GAP.y)))
sound("wind-trees", "left", (-8.0, 6.0, 14.0))
sound("wind-trees", "right", (9.0, 10.0, 14.0))
sound("wind-trees", "behind", (2.0, -12.0, 14.0))
page = S.page_preview(eye, fwd)
cams = S.view_cams(eye, YAW, extra=[
    ("Cam_Page", eye, eye + fwd * 10 + Vector((0, 0, -1.2)), 17),
    ("Cam_Gap", eye + Vector((0.3, -0.5, 0.0)), Vector((GAP.x, GAP.y, h(GAP.x, GAP.y) + 0.6)), 26),
    ("Cam_Road", eye, Vector((road_x(30.0), 30.0, h(road_x(30.0), 30.0) + 1.0)), 18),
    ("Cam_Up", eye, eye + Vector((0.2, 0.6, 1.0)) * 10, 17),
])
S.finish(ARGS, cams, "forest_road_lion.gltf", page=page, unlit_emit={"M_ForestWall"},
         keep_names={"M_CanopySprays": "veg.crown.canopy", "M_Ferns": "veg.leaves.ferns", "M_Undergrowth": "veg.shrub.undergrowth",
                     "M_ForestFloor": "GroundNear", "M_ForestWall": "far.forest"},
         keep_uv={"M_ForestFloor"},
         size_for={"M_YellowBrick": (2048, 256, 1024), "M_ForestFloor": (2048, 256, 1024), "M_Bark": (1024, 128, 512), "M_BarkSmooth": (512, 128, 256),
                   "M_DeadWood": (512, 64, 256), "M_SkyDome": (1024,), "M_ForestWall": (2048,)},
         default_size=(256, 64, 128), no_shadow={"M_SkyDome", "M_ForestWall"})
