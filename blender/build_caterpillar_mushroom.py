"""
Fable step-in room: the Caterpillar's mushroom (Alice's Adventures in Wonderland, chapter 5, "Advice from a
Caterpillar").

"There was a large mushroom growing near her, about the same height as herself; and when she had looked under it, and
on both sides of it, and behind it, it occurred to her that she might as well look and see what was on the top of it.
She stretched herself up on tiptoe, and peeped over the edge of the mushroom, and her eyes immediately met those of a
large blue caterpillar, that was sitting on the top with its arms folded, quietly smoking a long hookah" ... "she
leant against a buttercup to rest herself" ... "she ran across the field ... into a thick wood" ... "she stretched her
arms round it as far as they would go, and broke off a bit of the edge with each hand."

A small clearing on the floor of a thick English wood in May, seen at Alice's three-inch scale (everything ~22 times
larger): the mushroom about as tall as the reader, its perfectly round pale cap with a bite broken from each side and
the long hookah left standing on top (the Caterpillar has crawled away into the grass); grass blades arching six to
nine metres overhead, a buttercup the size of a tree to lean against, a great thistle, a few bluebells; beech leaves of
last autumn lying like rafts in the moss; the trunks of the wood standing far off like towers, and the canopy high
overhead letting the midday sun through in shafts and dapples. No Caterpillar, no Alice, no other creatures.

Reader: on the moss, facing the mushroom's cap edge where the Caterpillar sat, the giant grass behind.

  blender -b -P blender/build_caterpillar_mushroom.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_caterpillar_mushroom.py -- --render --samples 48 --res 1400 --cams reader,left,right,behind,mushroom
  blender -b -P blender/build_caterpillar_mushroom.py -- --export
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b5 as S
import pride_kit as K
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, MB, Canvas, anchor, sound, light_obj)

SID = "caterpillar-mushroom"
ARGS = S.setup(SID, seed=1865)
scene = K.scene
rng = random.Random(1865)

MUSH = Vector((0.0, 2.35, 0.0))
CAP_R, CAP_Z = 0.9, 1.2              # cap radius, height of the cap's rim
READER = Vector((0.0, 0.0, 0.0))


def H(x, y):
    """the forest floor: gentle hummocks, a root bulge, lower toward the grass; 0 at the reader"""
    r = math.hypot(x, y - 1.0)
    h = 0.25 * noise.noise(Vector((x / 6.0, y / 6.0, 0.3))) + 0.08 * noise.noise(Vector((x / 1.6, y / 1.6, 1.1)))
    h += 1.2 * K.smoothstep(12, 60, r) * noise.noise(Vector((x / 30.0, y / 30.0, 2.0)))
    return h - (0.25 * noise.noise(Vector((0.0, 0.0, 0.3))) + 0.08 * noise.noise(Vector((0.0, 0.0, 1.1)))) * (1 - K.smoothstep(4, 9, r))


# ----------------------------------------------------------------------------- painted atlases
def spray_atlas(name="A_CanopySpray", S_=1024):
    """four beech sprays (seen from below against the light): zig-zag twigs, oval leaves with parallel veins, in fresh May
    green, translucent-looking where they overlap."""
    cv = Canvas(S_, S_)
    r = random.Random(4)
    for cell in range(4):
        cx0, cy0 = (cell % 2) * S_ // 2, (cell // 2) * S_ // 2
        cv.clip = (cx0, cy0, cx0 + S_ // 2, cy0 + S_ // 2)
        ox, oy = cx0 + S_ // 4, cy0 + S_ // 4
        for b in range(10):
            a = r.uniform(0, 2 * math.pi); L = r.uniform(140, 240)
            p0 = (ox + r.uniform(-20, 20), oy + r.uniform(-20, 20))
            pts = [p0]
            for k in range(5):
                a += r.uniform(-0.5, 0.5); q = pts[-1]; pts.append((q[0] + math.cos(a) * L / 5, q[1] + math.sin(a) * L / 5))
            for k in range(5): cv.line(pts[k], pts[k + 1], 3.2 - 0.5 * k, 2.6 - 0.5 * k, (0.24, 0.20, 0.14, 1))
            for k in range(1, 6):
                for sd in (-1, 1, 1):
                    q = pts[k]; la = a + sd * r.uniform(0.6, 1.2) + r.uniform(-0.3, 0.3); ll = r.uniform(26, 40)
                    c = (q[0] + math.cos(la) * ll * 0.55, q[1] + math.sin(la) * ll * 0.55)
                    g = r.uniform(0, 1)
                    cv.ellipse(c[0], c[1], ll * 0.55, ll * 0.3, la, (0.30 + 0.12 * g, 0.50 + 0.12 * g, 0.12 + 0.06 * g, 1), tip=0.3)
                    cv.line(q, (c[0] + math.cos(la) * ll * 0.5, c[1] + math.sin(la) * ll * 0.5), 0.8, 0.5, (0.42, 0.58, 0.20, 1))
    cv.clip = None; cv.bleed(6)
    return K.np_image(name, cv.a)


A_SPRAY = spray_atlas()
M_CANOPY = K.image_mat("M_Canopy", A_SPRAY, rough=0.6, alpha=True)

# ----------------------------------------------------------------------------- materials
def forest_floor(name="M_ForestFloor"):
    """moss in cushions (bright green where sunlit-looking, olive in the hollows), patches of dark loam and fine litter."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    n1 = noise_(nt, co, 0.45, 5, 0.6, loc=(-1300, 300)); n2 = noise_(nt, co, 3.0, 6, 0.6, loc=(-1300, 100)); n3 = noise_(nt, co, 22.0, 4, 0.7, loc=(-1300, -100))
    v = voronoi_(nt, co, 2.2, 'F1', (-1300, -300))
    moss = mix_rgb(nt, 'MIX', maprange(nt, n3.outputs["Fac"], 0.3, 0.7, 0, 1, (-1100, 200)), (0.10, 0.20, 0.03, 1), (0.26, 0.38, 0.06, 1), (-900, 200))
    moss = mix_rgb(nt, 'MULTIPLY', 1.0, moss, maprange(nt, v.outputs["Distance"], 0.0, 0.5, 1.1, 0.6, (-1100, -300)), (-750, 200))
    loam = mix_rgb(nt, 'MIX', maprange(nt, n3.outputs["Fac"], 0.3, 0.7, 0, 1, (-1100, 0)), (0.06, 0.04, 0.025, 1), (0.16, 0.10, 0.06, 1), (-900, 0))
    litter = mix_rgb(nt, 'MIX', maprange(nt, n3.outputs["Fac"], 0.4, 0.6, 0, 1, (-1100, -150)), (0.30, 0.18, 0.08, 1), (0.46, 0.30, 0.14, 1), (-900, -150))
    m1 = maprange(nt, n1.outputs["Fac"], 0.42, 0.55, 0, 1, (-750, 0))
    col = mix_rgb(nt, 'MIX', m1, loam, moss, (-600, 100))
    col = mix_rgb(nt, 'MIX', maprange(nt, n2.outputs["Fac"], 0.6, 0.68, 0, 0.8, (-750, -200)), col, litter, (-450, 100))
    col = K.ao_mul(nt, col, 0.5, 0.5, (-300, -400))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95; b.inputs["Sheen Weight"].default_value = 0.5
    bump_from(nt, b, math_(nt, 'ADD', n3.outputs["Fac"], math_(nt, 'MULTIPLY', v.outputs["Distance"], -1.0, (-900, -600)), (-700, -600)), 0.6, 0.03)
    return m


def blade_mat(name, base, tip, vein=0.0):
    """giant grass blade: translucent-looking green, paler parallel veins along the blade (UV v along, u across)."""
    m, nt, b = new_mat(name)
    uv = node(nt, "ShaderNodeUVMap", (-1500, 0)); sp = sep_xyz(nt, uv.outputs["UV"], (-1300, 0))
    col = mix_rgb(nt, 'MIX', sp.outputs["Y"], c4(base), c4(tip), (-900, 0))
    veins = math_(nt, 'ABSOLUTE', math_(nt, 'SINE', math_(nt, 'MULTIPLY', sp.outputs["X"], 70.0, (-1100, -200)), None, (-1000, -200)), None, (-900, -200))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, veins, 0.0, 1.0, 0.86, 1.04, (-800, -200)), (-650, 0))
    mid = maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', sp.outputs["X"], 0.5, (-1100, -400)), None, (-1000, -400)), 0.0, 0.05, 1.25, 1.0, (-850, -400))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, mid, (-500, 0))
    n = noise_(nt, obj_coords(nt, (-1500, -600)), 0.8, 4, 0.6, loc=(-1300, -600))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.85, 1.12, (-1000, -600)), (-350, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.45
    bump_from(nt, b, veins, 0.15, 0.004)
    return m


M_FLOOR = forest_floor()
M_GRASS = blade_mat("M_GiantGrass", K.srgb((0.16, 0.32, 0.06)), K.srgb((0.38, 0.52, 0.16)))
M_STEM = blade_mat("M_PlantStem", K.srgb((0.20, 0.34, 0.08)), K.srgb((0.30, 0.44, 0.12)))
M_PETAL = noisy("M_ButtercupPetal", [K.srgb((0.95, 0.74, 0.04)), K.srgb((1.0, 0.82, 0.10)), K.srgb((0.92, 0.66, 0.02))], scale=3, rough=0.12, bump=0.05)
M_STAMEN = noisy("M_Stamens", [K.srgb((0.80, 0.62, 0.05)), K.srgb((0.62, 0.48, 0.04))], scale=40, rough=0.6, bump=0.4)
M_THISTLE = noisy("M_ThistleHead", [K.srgb((0.52, 0.22, 0.52)), K.srgb((0.64, 0.30, 0.62)), K.srgb((0.42, 0.16, 0.42))], scale=60, rough=0.7, bump=0.5)
M_BRACT = noisy("M_ThistleBract", [K.srgb((0.24, 0.32, 0.14)), K.srgb((0.34, 0.40, 0.20))], scale=30, rough=0.7, bump=0.5)
M_BLUEBELL = noisy("M_Bluebell", [K.srgb((0.26, 0.24, 0.62)), K.srgb((0.36, 0.32, 0.72))], scale=8, rough=0.35, bump=0.1)
M_CAP = noisy("M_MushroomCap", [K.srgb((0.86, 0.80, 0.68)), K.srgb((0.78, 0.70, 0.56)), K.srgb((0.90, 0.85, 0.76))], scale=2.5, rough=0.55, bump=0.3, bump_dist=0.004, sheen=0.3)
M_GILLS = noisy("M_Gills", [K.srgb((0.72, 0.62, 0.52)), K.srgb((0.62, 0.52, 0.44))], scale=30, rough=0.9, sheen=0.8, bump=0.3)
M_FLESH = noisy("M_MushroomFlesh", [K.srgb((0.94, 0.92, 0.86)), K.srgb((0.88, 0.86, 0.80))], scale=20, rough=0.8, bump=0.3)
M_MSTEM = noisy("M_MushroomStem", [K.srgb((0.88, 0.85, 0.78)), K.srgb((0.80, 0.76, 0.68))], scale=8, rough=0.7, stretch=(1, 1, 0.15), bump=0.4, bump_dist=0.003)
M_LEAF = noisy("M_BeechLitter", [K.srgb((0.30, 0.17, 0.08)), K.srgb((0.42, 0.26, 0.12)), K.srgb((0.22, 0.13, 0.07)), K.srgb((0.36, 0.30, 0.18))], scale=6, rough=0.85, bump=0.6, bump_dist=0.006, warp=0.4)
M_BARK = noisy("M_BeechBark", [K.srgb((0.40, 0.40, 0.37)), K.srgb((0.48, 0.48, 0.44)), K.srgb((0.30, 0.31, 0.28))], scale=0.15, rough=0.8, stretch=(1, 1, 0.4), bump=0.5, bump_dist=0.05)
M_GLASS = plain("M_HookahGlass", K.srgb((0.42, 0.52, 0.55)), rough=0.08, coat=0.5)
M_BRASS = plain("M_HookahBrass", K.srgb((0.62, 0.46, 0.22)), rough=0.3, metallic=1.0)
M_HOSE = noisy("M_HookahHose", [K.srgb((0.40, 0.12, 0.10)), K.srgb((0.30, 0.08, 0.07))], scale=60, rough=0.6, stretch=(1, 1, 8), bump=0.4)

# ----------------------------------------------------------------------------- the ground
near = S.grid_ground("FloorNear", M_FLOOR, H, -16, 16, -14, 18, 0.7, chunk=4.0)
far = S.polar_ground("FloorFar", M_FLOOR, H, r0=0.0, r1=700.0, nr=30, na=64, expo=2.2, centre=(0.0, 1.0),
                     keep=lambda x, y: not (abs(x) < 15.8 and -13.8 < y < 17.8))
# moss cushions and small stones (pebbles at this scale are boulders: a few half-buried rounded ones)
for k in range(10):
    a = rng.uniform(0, 2 * math.pi); r = rng.uniform(3.5, 12)
    x, y = math.cos(a) * r, 1.0 + math.sin(a) * r
    if abs(x) < 2.0 and -1.5 < y < 4.5: continue
    s_ = rng.uniform(0.4, 1.4)
    o = sphere(f"Pebble{k}", s_, (x, y, H(x, y) - s_ * 0.45), noisy("M_Flint", [K.srgb((0.46, 0.43, 0.38)), K.srgb((0.58, 0.54, 0.48)), K.srgb((0.36, 0.33, 0.30))], scale=1.5, rough=0.6, bump=0.3)
               if k == 0 else bpy.data.materials["M_Flint"], seg=12, scale=(rng.uniform(0.8, 1.3), rng.uniform(0.7, 1.1), rng.uniform(0.5, 0.8)))
    for v in o.data.vertices: v.co += v.normal * 0.06 * noise.noise(v.co * 2 + Vector((k, 0, 0)))

# ----------------------------------------------------------------------------- the mushroom: stem, cap with two bites, gills
lathe("MushStem", [(0.0, -0.1), (0.24, -0.1), (0.27, 0.0), (0.22, 0.15), (0.18, 0.45), (0.165, 0.8), (0.17, 1.05), (0.2, CAP_Z - 0.02), (0.0, CAP_Z - 0.02)],
      (MUSH.x, MUSH.y, H(MUSH.x, MUSH.y)), M_MSTEM, steps=24, jitter=0.03, seed=2)
# the cap: radius as a function of angle with two jagged bites (left and right as the reader sees it)
BITES = (math.radians(180) + 0.15, math.radians(0) - 0.1)
def cap_r(a):
    r = CAP_R * (1 + 0.012 * math.sin(a * 5))
    for bc in BITES:
        d = math.atan2(math.sin(a - bc), math.cos(a - bc))
        if abs(d) < 0.42:
            depth = 0.2 * (1 - (d / 0.42) ** 2) ** 0.6 * (0.94 + 0.06 * math.sin(d * 23))
            r -= depth
    return r
NA, NRING = 72, 9
cv = []; cf = []
zb = H(MUSH.x, MUSH.y)
top_profile = [(0.0, 0.32), (0.18, 0.31), (0.36, 0.28), (0.52, 0.23), (0.66, 0.16), (0.78, 0.09), (0.88, 0.04), (0.96, 0.01), (1.0, -0.02)]
for j, (t, dz) in enumerate(top_profile):
    for i in range(NA):
        a = 2 * math.pi * i / NA; r = cap_r(a) * t
        cv.append((MUSH.x + math.cos(a) * r, MUSH.y + math.sin(a) * r, zb + CAP_Z + dz + 0.01 * noise.noise(Vector((math.cos(a) * 3, math.sin(a) * 3, t * 3)))))
under = len(cv)
for j, (t, dz) in enumerate(((0.98, -0.06), (0.9, -0.1), (0.24, -0.04))):
    for i in range(NA):
        a = 2 * math.pi * i / NA; r = cap_r(a) * t if j < 2 else 0.22
        cv.append((MUSH.x + math.cos(a) * r, MUSH.y + math.sin(a) * r, zb + CAP_Z + dz))
for j in range(len(top_profile) - 1):
    for i in range(NA): cf.append((j * NA + i, (j + 1) * NA + i, (j + 1) * NA + (i + 1) % NA, j * NA + (i + 1) % NA))
last = (len(top_profile) - 1) * NA
for i in range(NA): cf.append((last + i, under + i, under + (i + 1) % NA, last + (i + 1) % NA))
for i in range(NA): cf.append((under + i, under + NA + i, under + NA + (i + 1) % NA, under + (i + 1) % NA))
cap = mesh_from("MushCap", cv, cf, M_CAP, smooth=True)
# the gill surface under the cap (radial fins between the margin and the stem top)
gv = []; gf = []
for i in range(NA):
    a = 2 * math.pi * i / NA
    r0 = 0.22; r1 = cap_r(a) * 0.86
    p0 = Vector((MUSH.x + math.cos(a) * r0, MUSH.y + math.sin(a) * r0, zb + CAP_Z - 0.04)); p1 = Vector((MUSH.x + math.cos(a) * r1, MUSH.y + math.sin(a) * r1, zb + CAP_Z - 0.1))
    base = len(gv)
    gv += [tuple(p0), tuple(p1), tuple(p1 + Vector((0, 0, -0.03 if i % 2 else -0.02))), tuple(p0 + Vector((0, 0, -0.02)))]
    gf.append((base, base + 1, base + 2, base + 3))
mesh_from("MushGills", gv, gf, M_GILLS)
gp = []; gpf = []
for i in range(NA):        # the gill plane, dark between fins
    a = 2 * math.pi * i / NA
for j, (rr, dz) in enumerate(((0.22, -0.035), (0.6, -0.06), (1.0, -0.095))):
    for i in range(NA):
        a = 2 * math.pi * i / NA; r = (cap_r(a) * 0.9 - 0.22) * (rr - 0.22) / 0.78 + 0.22 if j else 0.22
        gp.append((MUSH.x + math.cos(a) * r, MUSH.y + math.sin(a) * r, zb + CAP_Z + dz))
for j in range(2):
    for i in range(NA): gpf.append((j * NA + i, j * NA + (i + 1) % NA, (j + 1) * NA + (i + 1) % NA, (j + 1) * NA + i))
mesh_from("MushGillPlane", gp, gpf, M_GILLS, smooth=True)
# the white flesh showing in the bites: fill each notch's vertical face
for bc in BITES:
    fv = []; ff = []
    for k in range(13):
        a = bc - 0.42 + 0.84 * k / 12; r = cap_r(a)
        p = Vector((MUSH.x + math.cos(a) * r, MUSH.y + math.sin(a) * r, zb + CAP_Z))
        fv += [tuple(p + Vector((0, 0, 0.0))), tuple(p + Vector((0, 0, -0.08)))]
        if k: ff.append((2 * k - 2, 2 * k, 2 * k + 1, 2 * k - 1))
    mesh_from(f"BiteFlesh{bc:.2f}", fv, ff, M_FLESH, smooth=True)
# crumbs of the broken edge on the moss below each bite
for bc in BITES:
    for k in range(4):
        a = bc + rng.uniform(-0.3, 0.3); r = CAP_R + rng.uniform(0.1, 0.5)
        x, y = MUSH.x + math.cos(a) * r, MUSH.y + math.sin(a) * r
        sphere(f"Crumb{bc:.2f}{k}", rng.uniform(0.03, 0.06), (x, y, H(x, y) + 0.02), M_FLESH, seg=6, scale=(1.2, 0.9, 0.6))
anchor("scene.mushroom", tuple(MUSH))

# ----------------------------------------------------------------------------- the hookah on top, its long hose looped over the cap
HK = Vector((MUSH.x + 0.1, MUSH.y + 0.08, zb + CAP_Z + 0.3))
lathe("HookahBase", [(0.0, 0.0), (0.09, 0.0), (0.13, 0.05), (0.14, 0.11), (0.1, 0.17), (0.04, 0.2), (0.03, 0.22), (0.0, 0.22)], tuple(HK), M_GLASS, steps=18)
lathe("HookahWater", [(0.0, 0.005), (0.13, 0.05), (0.135, 0.09), (0.0, 0.09)], tuple(HK), plain("M_HookahWater", K.srgb((0.30, 0.40, 0.36)), rough=0.1), steps=14)
lathe("HookahStem", [(0.0, 0.2), (0.03, 0.2), (0.02, 0.26), (0.03, 0.3), (0.015, 0.34), (0.015, 0.52), (0.035, 0.54), (0.025, 0.56), (0.012, 0.6), (0.0, 0.6)],
      tuple(HK), M_BRASS, steps=12)
lathe("HookahTray", [(0.0, 0.38), (0.09, 0.38), (0.1, 0.39), (0.0, 0.39)], tuple(HK), M_BRASS, steps=16)
lathe("HookahBowl", [(0.0, 0.6), (0.03, 0.6), (0.045, 0.64), (0.05, 0.68), (0.0, 0.67)], tuple(HK), plain("M_ClayBowl", K.srgb((0.52, 0.28, 0.16)), rough=0.8), steps=12)
sphere("HookahEmber", 0.03, tuple(HK + Vector((0, 0, 0.675))), plain("M_Ash", K.srgb((0.40, 0.38, 0.36)), rough=0.9), seg=8, scale=(1, 1, 0.3))
# the hose: from the stem's side port, loops over the cap, the mouthpiece lying near the edge facing the reader
hp = [HK + Vector((0.03, 0, 0.3)), HK + Vector((0.18, -0.02, 0.28)), HK + Vector((0.32, -0.1, 0.12)), HK + Vector((0.34, -0.3, 0.02)),
      HK + Vector((0.2, -0.46, -0.0)), HK + Vector((-0.08, -0.5, 0.0)), HK + Vector((-0.3, -0.36, -0.01)), HK + Vector((-0.34, -0.12, 0.0)),
      HK + Vector((-0.24, 0.05, 0.02)), HK + Vector((-0.1, 0.0, 0.03))]
for p in hp:
    if p.z - HK.z < 0.05:
        rr = math.hypot(p.x - MUSH.x, p.y - MUSH.y) / CAP_R
        p.z = zb + CAP_Z + 0.32 - 0.34 * rr * rr + 0.022
pts = list(hp)
for it in range(3):          # Chaikin corner cutting: a soft, sagging hose
    q = [pts[0]]
    for i in range(len(pts) - 1):
        q += [pts[i].lerp(pts[i + 1], 0.25), pts[i].lerp(pts[i + 1], 0.75)]
    q.append(pts[-1]); pts = q
tube("HookahHose", pts, 0.018, M_HOSE, sides=8)
mp = hp[-1]
lathe("HookahMouthpiece", [(0.0, 0.0), (0.02, 0.0), (0.012, 0.08), (0.0, 0.09)], tuple(mp), plain("M_Amber", K.srgb((0.72, 0.42, 0.10)), rough=0.2), steps=8,
      rot=(math.radians(85), 0, math.radians(30)))
anchor("scene.hookah", tuple(HK))

# ----------------------------------------------------------------------------- giant grass: arching blades 4-9 m tall, behind and round the clearing
def blade(mb, base, h, w, direction, arch, twist=0.0, segs=5, r=None):
    d = Vector((direction[0], direction[1], 0)).normalized(); side = Vector((-d.y, d.x, 0))
    pts = []
    for k in range(segs + 1):
        t = k / segs
        up = h * (t - 0.42 * arch * t * t); out = h * arch * 0.7 * t * t
        pts.append(base + Vector((0, 0, up)) + d * out)
    prev = None
    for k, p in enumerate(pts):
        t = k / segs
        ww = w * (1 - t ** 1.6) * (0.9 if k else 1.0) + 0.002
        tw = twist * t
        sd = side * math.cos(tw) + Vector((0, 0, 1)) * math.sin(tw) * 0.0
        fold = Vector((0, 0, 0)) + (d * 0.0)
        a0 = mb.vert(p - sd * ww, (0.0, t), t); a1 = mb.vert(p + d * (ww * 0.15) , (0.5, t), t); a2 = mb.vert(p + sd * ww, (1.0, t), t)
        if prev: mb.face(prev[0], prev[1], a1, a0); mb.face(prev[1], prev[2], a2, a1)
        prev = (a0, a1, a2)
mbg = MB()
for k in range(130):
    a = rng.uniform(0, 2 * math.pi)
    # denser behind the reader and to the sides; the mushroom's side kept open
    r = rng.uniform(3.2, 13.0) if k < 70 else rng.uniform(13, 28)
    x, y = math.cos(a) * r, 1.0 + math.sin(a) * r
    if (Vector((x, y)) - MUSH.xy).length < 2.6 or (abs(x) < 1.6 and -2.2 < y < 4.0): continue
    if y > 5.5 and abs(x) < 4.5: continue        # a gap beyond the mushroom: the view into the wood
    n = rng.randint(3, 6) if r < 13 else rng.randint(2, 4)
    for q in range(n):
        h = rng.uniform(4.0, 9.0); w = rng.uniform(0.12, 0.22)
        if r > 12: h *= 1.1
        aa = rng.uniform(0, 2 * math.pi)
        base = Vector((x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.3, 0.3), H(x, y) - 0.1))
        blade(mbg, base, h, w, (math.cos(aa), math.sin(aa)), rng.uniform(0.25, 0.9))
mbg.build("veg.grass.giant", M_GRASS)

# ----------------------------------------------------------------------------- the buttercup (to the reader's left), the thistle (right, further), bluebells
def stem(name, pts, r0, r1, mat): return tube(name, pts, [r0 + (r1 - r0) * i / (len(pts) - 1) for i in range(len(pts))], mat, sides=8)
BC = Vector((-2.6, 1.6, H(-2.6, 1.6)))
bpts = [BC + Vector((0.0, 0, 0)), BC + Vector((0.1, 0.05, 2.0)), BC + Vector((0.35, 0.15, 4.0)), BC + Vector((0.7, 0.25, 5.8)), BC + Vector((1.1, 0.3, 7.0))]
stem("ButtercupStem", bpts, 0.13, 0.08, M_STEM)
FL = bpts[-1] + Vector((0.15, 0.0, 0.2))
fax = Vector((0.35, 0.05, 1)).normalized()
for k in range(5):
    a = 2 * math.pi * k / 5 + 0.3
    side = fax.cross(Vector((1, 0, 0))).normalized(); up2 = fax.cross(side)
    dirv = (side * math.cos(a) + up2 * math.sin(a))
    vs = []; fs = []
    for j in range(6):
        t = j / 5
        for i in range(5):
            s_ = (i / 4 - 0.5)
            w = 0.62 * math.sin(math.pi * min(1, 0.15 + t * 0.85)) * (1 if t < 0.85 else (1 - t) / 0.15 * 0.7 + 0.3)
            p = FL + dirv * (0.08 + 0.85 * t) + fax * (0.6 * t * t + 0.1 * t) + (dirv.cross(fax)) * s_ * w - fax * 0.12 * (s_ * 2) ** 2 * t
            vs.append(tuple(p))
    for j in range(5):
        for i in range(4): fs.append((j * 5 + i, j * 5 + i + 1, (j + 1) * 5 + i + 1, (j + 1) * 5 + i))
    mesh_from(f"ButtercupPetal{k}", vs, fs, M_PETAL, smooth=True)
for k in range(40):        # stamens
    a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0.04, 0.2)
    side = fax.cross(Vector((1, 0, 0))).normalized(); up2 = fax.cross(side)
    p0 = FL + (side * math.cos(a) + up2 * math.sin(a)) * rr * 0.5
    tube(f"Stamen{k}", [p0, p0 + fax * rng.uniform(0.15, 0.28) + (side * math.cos(a) + up2 * math.sin(a)) * rr * 0.5], [0.008, 0.006], M_STAMEN, sides=4, caps=False)
sphere("ButtercupBoss", 0.12, tuple(FL + fax * 0.05), M_BRACT, seg=10)
# buttercup leaves: deeply cut, low on the stem and at the base (three-lobed, toothed)
def lobed_leaf(name, base, dirv, L, mat, droop=0.4):
    d = Vector(dirv).normalized(); side = d.cross(Vector((0, 0, 1))).normalized()
    vs = [tuple(base)]; fs = []
    n = 24
    for i in range(n + 1):
        a = -math.pi * 0.8 + 1.6 * math.pi * i / n
        lobe = 0.55 + 0.45 * abs(math.cos(a * 1.5)) ** 0.6 - 0.1 * (i % 2)
        rr = L * lobe
        p = base + d * math.cos(a * 0.6) * rr * 0.8 + side * math.sin(a * 0.6) * rr * 0.75 + Vector((0, 0, -droop * (rr / L) ** 2 * L * 0.3))
        vs.append(tuple(p))
    for i in range(n): fs.append((0, i + 1, i + 2))
    return mesh_from(name, vs, fs, mat, smooth=True)
for k, (t, a, L) in enumerate(((0.0, 0.5, 1.6), (0.0, 2.6, 1.4), (0.0, 4.3, 1.5), (2.2, 1.2, 1.1), (3.6, 3.9, 0.9))):
    base = BC + Vector((0, 0, 0.3 + t))
    lobed_leaf(f"ButterLeaf{k}", base, (math.cos(a), math.sin(a), 0.2), L, M_STEM)
anchor("scene.buttercup", tuple(BC))
# the great thistle: a stout ribbed stem, spiny leaves, a purple head with its bract-cup, a second bud
TH = Vector((4.8, 4.2, H(4.8, 4.2)))
tp = [TH, TH + Vector((0.05, 0, 3.0)), TH + Vector((-0.1, 0.1, 6.5)), TH + Vector((-0.3, 0.2, 9.0))]
stem("ThistleStem", tp, 0.2, 0.12, M_BRACT)
TPH = tp[-1] + Vector((0, 0, 0.35))
sphere("ThistleCup", 0.5, tuple(TPH), M_BRACT, seg=14, scale=(1, 1, 0.9))
for k in range(28):        # bract spines round the cup
    a = rng.uniform(0, 2 * math.pi); el = rng.uniform(-0.6, 0.6)
    d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
    tube(f"Bract{k}", [TPH + d * 0.45, TPH + d * 0.62 + Vector((0, 0, 0.1))], [0.03, 0.002], M_BRACT, sides=4, caps=False)
lathe("ThistleFloret", [(0.0, 0.0), (0.36, 0.0), (0.42, 0.25), (0.36, 0.45), (0.2, 0.55), (0.0, 0.56)], tuple(TPH + Vector((0, 0, 0.25))), M_THISTLE, steps=16, jitter=0.08, seed=3)
for k in range(5):
    t = 0.2 + 0.15 * k; base = Vector(tp[1]).lerp(Vector(tp[2]), t) if k < 3 else Vector(tp[0]).lerp(Vector(tp[1]), t)
    a = rng.uniform(0, 6.28)
    lobed_leaf(f"ThistleLeaf{k}", base, (math.cos(a), math.sin(a), -0.1), rng.uniform(1.2, 2.0), M_BRACT, droop=0.8)
# bluebells: arching stalks with nodding bells on one side
for k, (bx, by) in enumerate(((-5.5, 6.5), (6.0, -2.5), (-4.0, -4.5))):
    base = Vector((bx, by, H(bx, by)))
    h = rng.uniform(4.5, 6.0)
    pts = [base, base + Vector((0.1, 0, h * 0.5)), base + Vector((0.5, 0.1, h * 0.85)), base + Vector((1.2, 0.2, h * 0.92))]
    stem(f"BluebellStalk{k}", pts, 0.06, 0.03, M_STEM)
    for j in range(5):
        p = Vector(pts[1]).lerp(Vector(pts[3]), 0.2 + 0.18 * j)
        lathe(f"Bell{k}{j}", [(0.0, 0.0), (0.12, -0.05), (0.2, -0.3), (0.26, -0.45), (0.3, -0.5), (0.22, -0.48), (0.0, -0.3)], tuple(p + Vector((0.0, 0.0, -0.1))), M_BLUEBELL, steps=12,
              rot=(rng.uniform(-0.3, 0.3), 0.3, 0))
    for j in range(2):
        blade(mbg, base, h * 0.6, 0.18, (rng.uniform(-1, 1), rng.uniform(-1, 1)), 0.7)

# ----------------------------------------------------------------------------- last autumn's beech leaves lying in the moss (rafts a metre long)
for k in range(22):
    a = rng.uniform(0, 2 * math.pi); r = rng.uniform(1.4, 8)
    x, y = math.cos(a) * r, 1.0 + math.sin(a) * r
    if (Vector((x, y)) - READER.xy).length < 1.1 or (Vector((x, y)) - MUSH.xy).length < 1.2: continue
    L = rng.uniform(0.7, 1.2); yaw = rng.uniform(0, 6.28)
    d = Vector((math.cos(yaw), math.sin(yaw), 0)); side = Vector((-d.y, d.x, 0))
    vs = []; fs = []
    for j in range(7):
        t = j / 6; w = L * 0.32 * math.sin(math.pi * min(1, 0.05 + t * 0.95)) ** 0.8
        for i in range(5):
            s_ = i / 4 - 0.5
            curl = 0.07 * (2 * s_) ** 2 + 0.03 * math.sin(t * 9 + k) + 0.04 * t * t
            p = Vector((x, y, 0)) + d * (t - 0.5) * L + side * s_ * 2 * w
            vs.append((p.x, p.y, H(p.x, p.y) + 0.02 + curl + 0.03 * t))
    for j in range(6):
        for i in range(4): fs.append((j * 5 + i, j * 5 + i + 1, (j + 1) * 5 + i + 1, (j + 1) * 5 + i))
    mesh_from(f"LitterLeaf{k}", vs, fs, M_LEAF, smooth=True)

# ----------------------------------------------------------------------------- the wood: tree trunks like towers far off, the canopy far overhead
for k in range(20):
    a = rng.uniform(0, 2 * math.pi) if k else math.radians(95); r = rng.uniform(45, 200) if k else 70
    x, y = math.cos(a) * r, 1.0 + math.sin(a) * r
    rad = rng.uniform(4, 8); h = 140
    pts = [Vector((x, y, H(x, y) - 2)), Vector((x + rng.uniform(-3, 3), y + rng.uniform(-3, 3), 60)), Vector((x + rng.uniform(-8, 8), y + rng.uniform(-8, 8), h))]
    tube(f"Trunk{k}", pts, [rad * 1.25, rad, rad * 0.8], M_BARK, sides=12)
    for q in range(3):      # buttress roots
        aa = rng.uniform(0, 6.28); dd = Vector((math.cos(aa), math.sin(aa), 0))
        tube(f"Root{k}{q}", [Vector((x, y, 6)), Vector((x, y, 0)) + dd * rad * 1.6, Vector((x, y, -2)) + dd * rad * 3.0], [rad * 0.6, rad * 0.35, rad * 0.1], M_BARK, sides=6)
    for q in range(3):      # limbs into the canopy
        aa = rng.uniform(0, 6.28); dd = Vector((math.cos(aa), math.sin(aa), 0.7)).normalized()
        p0 = pts[1].lerp(pts[2], rng.uniform(0.5, 0.9))
        tube(f"Limb{k}{q}", [p0, p0 + dd * rng.uniform(25, 45)], [rad * 0.45, rad * 0.15], M_BARK, sides=7)
# the canopy: leaf-spray cards in clusters on a broken dome 90-150 m up, gaps where the sun breaks through
mbc = MB()
SUN_TO = Vector((0.25, 0.35, 0.9)).normalized()
for k in range(900):
    a = rng.uniform(0, 2 * math.pi); r = 260 * math.sqrt(rng.random())
    x, y = math.cos(a) * r, 1.0 + math.sin(a) * r
    z = 120 + 30 * noise.noise(Vector((x / 80, y / 80, 0.5))) - r * 0.25
    # gaps: a few larger clear patches, one roughly sunward of the clearing
    g = noise.noise(Vector((x / 45.0, y / 45.0, 3.3)))
    sun_gap = (Vector((x, y, z)) - Vector((0, 1, 0)) - SUN_TO * ((z) / SUN_TO.z)).length
    if g > 0.42 or sun_gap < 14: continue
    cell = rng.randrange(4); sz = rng.uniform(30, 52)
    yaw = rng.uniform(0, 6.28); tilt = rng.uniform(-0.4, 0.4)
    right = Vector((math.cos(yaw), math.sin(yaw), 0)) * sz; up = Vector((-math.sin(yaw), math.cos(yaw), tilt)) * sz
    u0 = ((cell % 2) * 0.5, (cell // 2) * 0.5)
    mbc.quad_card((x, y, z), right, up, uv0=u0, uv1=(u0[0] + 0.5, u0[1] + 0.5), sway=(0.6, 1.0), bottom_pivot=False)
mbc.build("veg.crown.canopy", M_CANOPY)

# the wood beyond: a painted ring of shaded trunks and undergrowth closing the horizon (unlit backdrop, far.*)
M_WOODWALL = new_mat("M_WoodWall")[0]
ntw = M_WOODWALL.node_tree; bw = ntw.nodes["Principled BSDF"]
cw = obj_coords(ntw); sw_ = sep_xyz(ntw, cw, (-1300, 300))
az = math_(ntw, 'ARCTAN2', sw_.outputs["Y"], sw_.outputs["X"], (-1100, 300))
azv = node(ntw, "ShaderNodeCombineXYZ", (-1000, 300)); ntw.links.new(math_(ntw, 'MULTIPLY', az, 40.0, (-1050, 450)), azv.inputs["X"]); ntw.links.new(math_(ntw, 'MULTIPLY', sw_.outputs["Z"], 0.02, (-1050, 150)), azv.inputs["Y"])
tr_ = noise_(ntw, azv.outputs[0], 1.0, 3, 0.5, loc=(-850, 300))
trunk = maprange(ntw, tr_.outputs["Fac"], 0.55, 0.6, 0, 1, (-700, 300))
lf = noise_(ntw, cw, 0.08, 6, 0.65, loc=(-850, 0))
low = maprange(ntw, sw_.outputs["Z"], 0, 40, 1, 0, (-850, -200))
base = mix_rgb(ntw, 'MIX', maprange(ntw, lf.outputs["Fac"], 0.35, 0.65, 0, 1, (-700, 0)), (0.05, 0.08, 0.04, 1), (0.16, 0.24, 0.08, 1), (-550, 0))
base = mix_rgb(ntw, 'MIX', math_(ntw, 'MULTIPLY', trunk, maprange(ntw, sw_.outputs["Z"], 5, 60, 0.9, 0.4, (-700, -350)), (-550, -300)), base, (0.20, 0.21, 0.19, 1), (-400, 0))
base = mix_rgb(ntw, 'MIX', math_(ntw, 'MULTIPLY', low, 0.4, (-550, -200)), base, (0.10, 0.16, 0.06, 1), (-300, 0))
ntw.links.new(base, bw.inputs["Emission Color"]); bw.inputs["Emission Strength"].default_value = 1.0; bw.inputs["Base Color"].default_value = (0, 0, 0, 1)
wv = []; wf = []
for j in range(4):
    for i in range(48):
        a = 2 * math.pi * i / 48; wv.append((math.cos(a) * 240, 1.0 + math.sin(a) * 240, -5 + 75 * j))
for j in range(3):
    for i in range(48): wf.append((j * 48 + i, j * 48 + (i + 1) % 48, (j + 1) * 48 + (i + 1) % 48, (j + 1) * 48 + i))
ww = mesh_from("WoodWall", wv, wf, M_WOODWALL)
ww.visible_shadow = False; ww.visible_diffuse = False; ww.visible_glossy = False

# ----------------------------------------------------------------------------- sky, sun, world
M_SKY = S.sky_mat("M_SkyDome", SUN_TO, zenith=(0.24, 0.42, 0.74), mid=(0.48, 0.62, 0.82), horizon=(0.66, 0.74, 0.70), cloud=0.3,
                  haze_low=(0.30, 0.38, 0.26))
S.sky_dome(M_SKY, radius=900.0)
light_obj("Lamp.sun", 'SUN', 5.0, (1.0, 0.95, 0.84), (0, 0, 100), direction=tuple(-SUN_TO), angle=math.radians(1.0))
world = bpy.data.worlds.new("WoodShade"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.36, 0.48, 0.34, 1)    # green bounce from the leaves
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9

# ----------------------------------------------------------------------------- anchors, sources
S.reader(READER, (MUSH.x - READER.x, MUSH.y - READER.y))
anchor("scene.centre", tuple(MUSH))
sound("wind-trees", "canopy", (20.0, 30.0, 60.0))
sound("birds", "wood", (-30.0, 20.0, 40.0))
sound("birds", "near", (8.0, -10.0, 6.0))
page = S.page_preview()
K.apply_transforms()

E = READER + Vector((0, 0, S.EYE))
cams = S.eye_cams([("Reader", 0), ("Left", -75), ("Right", 75), ("Behind", 180)], dz=-0.2, dist=6.0, extra=[
    ("Page", E, E + (MUSH - READER).normalized() * 5 + Vector((0, 0, -0.2)), 17),
    ("Mushroom", Vector((1.3, 0.6, 2.2)), MUSH + Vector((0, 0, CAP_Z + 0.2)), 26),
    ("Up", E, E + Vector((0.4, 2.0, 5.0)), 17),
])
probs = S.check_reader(ignore=("PagePreview",))
K.print_budget(exclude=("PagePreview",))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.0, captures_dir=ARGS.captures)

if ARGS.export or ARGS.bake:
    S.export(SID, cams, page=page,
             keep_names={"M_GiantGrass": "veg.grass.giant", "M_Canopy": "veg.crown.canopy", "M_WoodWall": "far.woodWall"}, unlit_emit=("M_WoodWall",),
             size_for={"M_ForestFloor": (2048, 64, 1024), "M_GiantGrass": (1024, 64, 512), "M_MushroomCap": (1024, 64, 512), "M_MushroomStem": (512, 64, 256),
                       "M_Gills": (512, 64, 256), "M_PlantStem": (1024, 64, 512), "M_ButtercupPetal": (512, 64, 256), "M_BeechBark": (1024, 64, 512),
                       "M_BeechLitter": (512, 64, 256), "M_SkyDome": (2048,), "M_WoodWall": (2048,), "M_ThistleBract": (512, 64, 256), "M_HookahHose": (256, 32, 128)},
             default_size=(256, 32, 128))
print("DONE")
