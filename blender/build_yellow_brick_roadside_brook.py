"""
Fable: the roadside brook beyond the Munchkin farms (The Wonderful Wizard of Oz, chapter 4, "The Road Through the
Forest").

"After a few hours the road began to be rough, and the walking grew so difficult that the Scarecrow often stumbled
over the yellow bricks, which were here very uneven. Sometimes, indeed, they were broken or missing altogether,
leaving holes ..." "There were fewer houses and fewer fruit trees, and the farther they went the more dismal and
lonesome the country became. At noon they sat down by the roadside, near a little brook, and Dorothy opened her
basket and got out some bread." "There were no fences at all by the roadside now, and the land was rough and untilled.
Toward evening they came to a great forest, where the trees grew so big and close together that their branches met
over the road of yellow brick."

The reader stands on the grassy verge between the road and a little brook, at noon, facing along the road toward the
dark edge of the great forest on the horizon. The road of yellow brick runs past on the right, its bricks uneven,
cracked, some missing and the holes muddy; weeds push up between them. On the left the brook runs over stones
between sedge and rushes toward the reader, under a lone old apple tree. Round about, rough untilled land gone to
long grass and weeds, a lonely Munchkin house far off, a few fruit trees; Dorothy's little basket with the bread
under a white cloth lies on the verge. The noon sun is a little muted by a high thin haze; the mood is lonesome.
No people, no fences, no Tin Woodman, Lion or Kalidahs.

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py.

Node names the runtime relies on:
  anchor.reader.entrance (feet on the verge, facing +Y along the road), anchor.reader.look, anchor.scene.centre
  (the basket), anchor.road.forest (the forest's edge on the road)
  light.sun (SUN, noon, a little hazed), light.sky (SUN, sky fill, no shadow)
  water.stream.brook (UV V runs downstream), veg.grass.verge, veg.grass.field, veg.reeds.brook, veg.crown.apple,
  veg.crown.forest
  sound.river.brook, sound.wind-trees.apple, sound.birds.0
  SkyDome, far.Forest (backdrop)

Run headless:
  blender -b -P blender/build_yellow_brick_roadside_brook.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_yellow_brick_roadside_brook.py -- --render --samples 48 --res 1400
  blender -b -P blender/build_yellow_brick_roadside_brook.py -- --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b1 as S
from scene_kit_b1 import (K, E8, new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound, light_obj, camera,
                          link, smoothstep, lerp, n2, fbm2, orient, card, plant, set_card_normals, az_dir, TWO_PI)

ARGS = S.setup("yellow-brick-roadside-brook", 1900, "RoadsideBrook", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
SUN_AZ, SUN_EL = 200.0, 58.0
SUN_DIR = (az_dir(SUN_AZ) * math.cos(math.radians(SUN_EL)) + Vector((0, 0, math.sin(math.radians(SUN_EL))))).normalized()

# ----------------------------------------------------------------------------- the road, the brook, the land
ROAD_X = 2.9; ROAD_W = 3.0
def road_cx(y): return ROAD_X + 1.2 * math.sin(y * 0.012) + 0.25 * math.sin(y * 0.05)
BROOK = [(-9.0, 60.0), (-4.5, 44.0), (-1.9, 32.0), (-4.2, 22.0), (-1.9, 13.0), (-3.4, 6.0), (-2.0, 0.5), (-3.6, -6.0), (-2.2, -14.0), (1.0, -24.0), (4.5, -45.0)]
def brook_d(x, y): return S.seg_dist(x, y, BROOK)
def H(x, y):
    z = 0.35 * n2(x, y, 25.0, 3.0) + 0.12 * n2(x, y, 7.0, 5.0) + 0.04 * n2(x, y, 1.5, 9.0)
    z += 0.004 * y
    rd = abs(x - road_cx(y))
    z = z * (1 - 0.8 * smoothstep(ROAD_W * 0.5 + 1.0, ROAD_W * 0.5, rd))          # the road's bed is levelled
    bd = brook_d(x, y)
    z -= 0.55 * smoothstep(1.6, 0.35, bd)                                            # the brook's channel
    z += 0.6 * smoothstep(60, 200, math.hypot(x, y)) * n2(x, y, 40.0, 2.0)           # far undulation
    return z
Z0 = H(0, 0)
def gz(x, y): return H(x, y) - Z0
S.set_ground(gz)
BROOK_W = 0.55

def road_fn(x, y): return smoothstep(ROAD_W * 0.5 + 0.08, ROAD_W * 0.5 - 0.08, abs(x - road_cx(y)))
def brookbank_fn(x, y): return smoothstep(1.4, 0.4, brook_d(x, y))

def ground_mat(name="M_Land"):
    """the verge and the untilled land: rough meadow turf (blade streaks, straw and green, clover, dandelion dots),
    trodden earth along the road's edge, wet dark mud and gravel at the brook's banks; the yellow-brick road drawn by
    a brick pattern where the 'road' attribute is 1: bricks of uneven yellow, some cracked, some missing (muddy holes),
    weeds and moss in the joints."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    ar = node(nt, "ShaderNodeAttribute", (-2100, 700)); ar.attribute_name = "road"
    ab = node(nt, "ShaderNodeAttribute", (-2100, 550)); ab.attribute_name = "bank"
    road, bank = ar.outputs["Fac"], ab.outputs["Fac"]
    # turf
    mp = node(nt, "ShaderNodeMapping", (-1900, 300)); mp.inputs["Scale"].default_value = (14.0, 3.0, 14.0); mp.inputs["Rotation"].default_value = (0, 0, 0.5)
    nt.links.new(co, mp.inputs["Vector"])
    bl = noise_(nt, mp.outputs["Vector"], 8.0, 3, 0.6, 1.2, (-1700, 300))
    mp2 = node(nt, "ShaderNodeMapping", (-1900, 100)); mp2.inputs["Scale"].default_value = (3.0, 14.0, 14.0); mp2.inputs["Rotation"].default_value = (0, 0, -0.7)
    nt.links.new(co, mp2.inputs["Vector"])
    bl2 = noise_(nt, mp2.outputs["Vector"], 8.0, 3, 0.6, 1.2, (-1700, 100))
    blades = math_(nt, 'MAXIMUM', bl.outputs["Fac"], bl2.outputs["Fac"], (-1500, 200))
    patch = noise_(nt, co, 0.4, 4, 0.6, loc=(-1700, -100))
    turf = ramp(nt, [(0.0, c4(K.srgb((0.15, 0.17, 0.08)))), (0.45, c4(K.srgb((0.27, 0.30, 0.13)))), (0.7, c4(K.srgb((0.42, 0.40, 0.22)))), (1.0, c4(K.srgb((0.56, 0.50, 0.32))))], (-1300, 200))
    nt.links.new(math_(nt, 'ADD', math_(nt, 'MULTIPLY', blades, 0.7, (-1400, 300)), math_(nt, 'MULTIPLY', patch.outputs["Fac"], 0.35, (-1400, 100)), (-1350, 200)), turf.inputs["Fac"])
    col = turf.outputs["Color"]
    dots = voronoi_(nt, co, 9.0, 'F1', (-1700, -300))
    dsep = node(nt, "ShaderNodeSeparateColor", (-1500, -300)); nt.links.new(dots.outputs["Color"], dsep.inputs["Color"])
    flower = math_(nt, 'MULTIPLY', maprange(nt, dots.outputs["Distance"], 0.07, 0.04, 0, 1, (-1400, -400)), maprange(nt, dsep.outputs[0], 0.9, 0.93, 0, 1, (-1400, -300)), (-1250, -350))
    col = mix_rgb(nt, 'MIX', flower, col, c4(K.srgb((0.85, 0.75, 0.18))), (-1100, 200))
    # bank mud
    mud = mix_rgb(nt, 'MIX', maprange(nt, patch.outputs["Fac"], 0.3, 0.7, 0, 1, (-1300, -600)), c4(K.srgb((0.18, 0.15, 0.11))), c4(K.srgb((0.30, 0.26, 0.20))), (-1100, -600))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', bank, maprange(nt, blades, 0.3, 0.7, 1.0, 0.4, (-1300, -750)), (-1100, -750)), col, mud, (-900, 200))
    # the road: bricks
    br = node(nt, "ShaderNodeTexBrick", (-1500, 900))
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 0.24; br.inputs["Row Height"].default_value = 0.11
    br.inputs["Mortar Size"].default_value = 0.012; br.inputs["Mortar Smooth"].default_value = 0.3; br.offset = 0.5
    br.inputs["Color1"].default_value = (1, 1, 1, 1); br.inputs["Color2"].default_value = (0.0, 0.0, 0.0, 1)
    br.inputs["Bias"].default_value = 0.0
    swz = node(nt, "ShaderNodeVectorMath", (-1700, 900), operation='MULTIPLY'); swz.inputs[1].default_value = (1.0, 1.0, 0.0)
    nt.links.new(co, swz.inputs[0]); nt.links.new(swz.outputs[0], br.inputs["Vector"])
    brick_id = br.outputs["Color"]                      # random grey per brick
    mortar = br.outputs["Fac"]                           # 1 in the joints
    bsep = node(nt, "ShaderNodeSeparateColor", (-1300, 900)); nt.links.new(brick_id, bsep.inputs["Color"])
    bid = bsep.outputs[0]
    yel = ramp(nt, [(0.0, c4(K.srgb((0.62, 0.48, 0.16)))), (0.4, c4(K.srgb((0.78, 0.62, 0.22)))), (0.7, c4(K.srgb((0.84, 0.70, 0.30)))), (1.0, c4(K.srgb((0.70, 0.54, 0.20))))], (-1100, 900))
    nt.links.new(bid, yel.inputs["Fac"])
    grime = noise_(nt, co, 3.0, 5, 0.6, loc=(-1500, 1150))
    bc = mix_rgb(nt, 'MULTIPLY', 1.0, yel.outputs["Color"], maprange(nt, grime.outputs["Fac"], 0.3, 0.7, 0.62, 1.05, (-1300, 1150)), (-900, 950))
    crack = maprange(nt, voronoi_(nt, co, 14.0, 'DISTANCE_TO_EDGE', (-1500, 1350)).outputs["Distance"], 0.0, 0.015, 1, 0, (-1300, 1350))
    crack = math_(nt, 'MULTIPLY', crack, maprange(nt, noise_(nt, co, 1.5, 3, 0.5, loc=(-1500, 1500)).outputs["Fac"], 0.5, 0.6, 0, 1, (-1300, 1500)), (-1150, 1400))
    bc = mix_rgb(nt, 'MIX', crack, bc, c4(K.srgb((0.20, 0.16, 0.10))), (-800, 950))
    # missing bricks: where a slow noise and the brick's random value say so, a hole of dark mud and weeds
    hole = math_(nt, 'MULTIPLY', maprange(nt, noise_(nt, co, 0.7, 3, 0.5, loc=(-1500, 1650)).outputs["Fac"], 0.55, 0.62, 0, 1, (-1300, 1650)),
                 maprange(nt, bid, 0.35, 0.4, 0, 1, (-1300, 1750)), (-1150, 1700))
    joint = mix_rgb(nt, 'MIX', maprange(nt, grime.outputs["Fac"], 0.4, 0.6, 0, 1, (-1100, 750)), c4(K.srgb((0.30, 0.26, 0.18))), c4(K.srgb((0.24, 0.30, 0.12))), (-900, 750))
    roadc = mix_rgb(nt, 'MIX', mortar, bc, joint, (-700, 900))
    roadc = mix_rgb(nt, 'MIX', hole, roadc, mud, (-600, 900))
    col = mix_rgb(nt, 'MIX', road, col, roadc, (-500, 300))
    col = K.ao_mul(nt, col, 0.3, 0.35, (-400, -900))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, road, mix_f(nt, bank, 0.85, 0.5, (-600, -300)), 0.75, (-450, -300)), b.inputs["Roughness"])
    b.inputs["Specular IOR Level"].default_value = 0.25
    hroad = math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', bid, 0.4, (-700, -1300)), math_(nt, 'ADD', mortar, math_(nt, 'MULTIPLY', hole, 2.0, (-800, -1450)), (-700, -1450)), (-600, -1350))
    hgt = mix_f(nt, road, math_(nt, 'MULTIPLY', blades, 0.6, (-700, -1550)), hroad, (-450, -1450))
    bump_from(nt, b, hgt, 0.6, 0.02)
    return m

print("materials ...", flush=True)
M_LAND = ground_mat()
M_ROAD = M_LAND.copy(); M_ROAD.name = "M_Road"
M_STONE = S.stone_mat("M_BrookStones", (0.40, 0.38, 0.34), (0.20, 0.19, 0.17), (0.52, 0.50, 0.45), scale=2.5, wet_z=gz(-2.4, 5.0) - 0.35, wet_k=0.6, moss=0.4, lichen=0.15, rough=0.75, bump=0.2)
M_WATER = S.water_mat("M_Brook", deep=(0.05, 0.06, 0.04), rough=0.04, ripple=0.3)
M_BARK = S.bark_mat("M_AppleBark", (0.28, 0.24, 0.19), (0.12, 0.10, 0.08), (0.38, 0.34, 0.28), scale=1.5, fissure=0.7, moss=0.3)
M_FBARK = S.bark_mat("M_ForestBark", (0.20, 0.18, 0.15), (0.08, 0.07, 0.06), (0.28, 0.26, 0.22), scale=1.0, fissure=0.6, moss=0.2)
M_WICKER = K.noisy("M_Wicker", [K.srgb((0.55, 0.42, 0.24)), K.srgb((0.45, 0.33, 0.18)), K.srgb((0.62, 0.50, 0.30))], scale=60, rough=0.75, bump=0.4, stretch=(1, 1, 6))
M_CLOTH = K.noisy("M_WhiteCloth", [K.srgb((0.88, 0.87, 0.84)), K.srgb((0.80, 0.79, 0.76))], scale=80, rough=0.9, bump=0.15)
M_BREAD = K.noisy("M_Bread", [K.srgb((0.62, 0.40, 0.18)), K.srgb((0.72, 0.52, 0.26))], scale=20, rough=0.8, bump=0.3)
M_HOUSE = K.noisy("M_MunchkinHouse", [K.srgb((0.30, 0.42, 0.62)), K.srgb((0.26, 0.36, 0.55))], scale=2, rough=0.85, bump=0.1)
M_SKY = S.gradient_sky_mat("M_SkyDome", [(0.0, (0.62, 0.66, 0.70)), (0.1, (0.56, 0.62, 0.70)), (0.4, (0.36, 0.48, 0.66)), (1.0, (0.22, 0.36, 0.60))],
                           sun_dir=SUN_DIR, glow=((0.6, 0.55, 0.45), 30.0), clouds=0.55, cloud_col=(0.82, 0.83, 0.85), strength=1.0)
IMG_PLANTS, CELLS = S.plant_atlas("A_VergePlants", ["tussock", "tallgrass", "flowers", "dock", "sedge", "bulrush", "weed", "grass"], seed=1900,
                                  greens=[(0.22, 0.30, 0.09), (0.28, 0.35, 0.11), (0.34, 0.40, 0.14), (0.20, 0.26, 0.08)],
                                  straw=[(0.62, 0.55, 0.32), (0.55, 0.48, 0.28), (0.70, 0.62, 0.38)])
M_GRASS = image_mat("M_VergeGrass", IMG_PLANTS, rough=0.6, alpha=True)
M_FIELD = image_mat("M_FieldGrass", IMG_PLANTS, rough=0.6, alpha=True)
M_REEDS = image_mat("M_BrookReeds", IMG_PLANTS, rough=0.55, alpha=True)
M_APPLE = image_mat("M_AppleLeaves", S.spray_atlas("A_AppleSprays", "alder", 31), rough=0.6, alpha=True)
M_FORESTMASS = S.crown_mass_mat("M_ForestMass", (0.03, 0.05, 0.02), (0.07, 0.11, 0.04), (0.12, 0.16, 0.06), scale=0.4)
M_FOREST = image_mat("M_ForestLeaves", S.spray_atlas("A_ForestSprays", "dark", 32), rough=0.7, alpha=True)

# ----------------------------------------------------------------------------- ground, brook
print("ground ...", flush=True)
GROUND = S.ground("Land", M_LAND, 160.0, r0=2.0, NA=112, NR=36, attrs={"road": road_fn, "bank": brookbank_fn})
# raise the road's surface a hair on its own denser strip near the reader, so the bricks' unevenness shows in the
# silhouette (rocked bricks, sunken holes): a ribbon from 6 m behind to 40 m ahead
def road_strip():
    """16 chunks of 2.875 m laid out 4 x 4 in UV (each chunk's bake texels about 6 mm), so the bricks hold up."""
    verts = []; faces = []; uvs = []; NX = 10; PER = 12; CH = 2.875
    for c in range(16):
        y0 = -6.0 + c * CH; col, row = c % 4, c // 4
        base = len(verts)
        for j in range(PER + 1):
            y = y0 + CH * j / PER
            for i in range(NX + 1):
                u = i / NX; x = road_cx(y) - ROAD_W / 2 + ROAD_W * u
                z = gz(x, y) + 0.025 + 0.012 * noise.noise(Vector((x * 3.0, y * 3.0, 0.5)))
                hole = smoothstep(0.55, 0.65, 0.5 + 0.5 * noise.noise(Vector((x * 0.7, y * 0.7, 3.0))))
                z -= 0.06 * hole
                if i in (0, NX): z -= 0.03
                verts.append((x, y, z)); uvs.append(((col + 0.01 + 0.98 * u) / 4, (row + 0.01 + 0.98 * j / PER) / 4))
        for j in range(PER):
            for i in range(NX):
                a = base + j * (NX + 1) + i; faces.append((a, a + 1, a + NX + 2, a + NX + 1))
    o = mesh_from("RoadStrip", verts, faces, M_ROAD, smooth=True, uvs=uvs)
    me = o.data
    at = me.attributes.new("road", 'FLOAT', 'POINT'); at.data.foreach_set("value", [1.0] * len(verts))
    at2 = me.attributes.new("bank", 'FLOAT', 'POINT'); at2.data.foreach_set("value", [0.0] * len(verts))
    orient(o, lambda c: (0, 0, 1))
    return o
road_strip()

def brook_ribbon():
    """the water: a ribbon along the brook's path, U across, V downstream (toward -Y: the brook runs past the reader
    from the forest side), at the channel's water level."""
    pts = []
    for (a, b_) in zip(BROOK, BROOK[1:]):
        for t in np.linspace(0, 1, 14, endpoint=False):
            pts.append(Vector(a).lerp(Vector(b_), t))
    pts.append(Vector(BROOK[-1]))
    verts = []; faces = []; uvs = []
    acc = 0.0
    for k, p in enumerate(pts):
        if k: acc += (p - pts[k - 1]).length
        t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized(); nrm = Vector((-t.y, t.x))
        w = BROOK_W * (0.8 + 0.3 * noise.noise(Vector((p.x * 0.3, p.y * 0.3, 1.0))))
        zc = gz(p.x, p.y) + 0.22
        for s in (-1, 1):
            q = p + nrm * s * w
            verts.append((q.x, q.y, zc)); uvs.append(((s + 1) / 2, acc / 4.0))
    for k in range(len(pts) - 1):
        a = 2 * k; faces.append((a, a + 1, a + 3, a + 2))
    o = mesh_from("Brook", verts, faces, M_WATER, smooth=True, uvs=uvs)
    orient(o, lambda c: (0, 0, 1))
    return o
brook_ribbon()
R = random.Random(4)
specs = []
for k in range(60):
    seg = R.randint(2, 7); a, b_ = Vector(BROOK[seg]), Vector(BROOK[seg + 1]); p = a.lerp(b_, R.random())
    t = (b_ - a).normalized(); nrm = Vector((-t.y, t.x)); p = p + nrm * R.uniform(-1.1, 1.1)
    specs.append((p.x, p.y, R.uniform(0.08, 0.28), 100 + k, {"sub": 2, "bury": 0.45, "facet": 0.05, "squash": (1.0, 0.8, 0.55)}))
S.rocks("BrookStones", specs, M_STONE)

# ----------------------------------------------------------------------------- the basket by the reader
BASKET = Vector((-0.75, 0.85, 0))
bz = gz(BASKET.x, BASKET.y)
bk = lathe("Basket", [(0.0, 0.0), (0.15, 0.0), (0.17, 0.02), (0.19, 0.16), (0.185, 0.17), (0.17, 0.165), (0.155, 0.02), (0.0, 0.02)], (BASKET.x, BASKET.y, bz), M_WICKER, steps=20)
bk.scale = (1.35, 1.0, 1.0)
tube("BasketHandle", [Vector((BASKET.x - 0.24, BASKET.y, bz + 0.16)), Vector((BASKET.x - 0.15, BASKET.y, bz + 0.34)), Vector((BASKET.x, BASKET.y, bz + 0.39)),
                      Vector((BASKET.x + 0.15, BASKET.y, bz + 0.34)), Vector((BASKET.x + 0.24, BASKET.y, bz + 0.16))], [0.012] * 5, M_WICKER, sides=6)
sphere("BasketBread", 0.09, (BASKET.x + 0.05, BASKET.y, bz + 0.16), M_BREAD, seg=12, scale=(1.4, 0.9, 0.7))
# the white cloth: laid over the bread, falling over one side of the rim
cbm = bmesh.new(); bmesh.ops.create_grid(cbm, x_segments=12, y_segments=12, size=0.24)
for v in cbm.verts:
    x, y = v.co.x, v.co.y
    rr = math.hypot(x / 1.35, y)
    z = 0.19 + 0.05 * math.exp(-((x - 0.05) ** 2 + y ** 2) / 0.008)
    if rr > 0.16: z -= (rr - 0.16) * 2.2
    v.co = Vector((BASKET.x + x, BASKET.y + y + 0.02 * math.sin(x * 20), bz + z + 0.004 * noise.noise(Vector((x * 30, y * 30, 0)))))
cme = bpy.data.meshes.new("Cloth"); cbm.to_mesh(cme); cbm.free()
co_ = bpy.data.objects.new("Cloth", cme); cme.materials.append(M_CLOTH); link(co_)
for p in cme.polygons: p.use_smooth = True
orient(co_, lambda c: (0, 0, 1))

# ----------------------------------------------------------------------------- plants
print("plants ...", flush=True)
VMB = MB(); FMB = MB(); RMB = MB()
placed = 0
for i in range(60000):
    r = 32.0 * R.random() ** 1.2 + 0.6; a = R.uniform(0, TWO_PI); x, y = r * math.sin(a), r * math.cos(a)
    if road_fn(x, y) > 0.05: continue
    bd = brook_d(x, y)
    if bd < BROOK_W + 0.1: continue
    if math.hypot(x, y) < 0.7 or (abs(x) < 0.5 and 0 < y < 2.0) or (Vector((x, y)) - BASKET.xy).length < 0.45: continue
    rd = abs(x - road_cx(y)) - ROAD_W / 2
    dens = 0.55 + 0.45 * n2(x, y, 3.0, 6.0)
    if R.random() > dens: continue
    if bd < 2.2:
        kind = R.choice(("sedge", "bulrush", "sedge", "tussock")); h = R.uniform(0.6, 1.3) if kind != "bulrush" else R.uniform(1.2, 1.7); mb = RMB
    elif rd < 1.2:
        kind = R.choice(("grass", "grass", "flowers", "dock", "weed")); h = R.uniform(0.25, 0.5); mb = VMB
    else:
        kind = R.choices(["tallgrass", "tussock", "weed", "flowers", "dock", "grass"], weights=[4, 3, 1.5, 1, 0.8, 2])[0]
        h = {"tallgrass": 0.9, "tussock": 0.7, "weed": 1.0, "flowers": 0.55, "dock": 0.6, "grass": 0.4}[kind] * R.uniform(0.75, 1.3)
        mb = FMB if r > 6 else VMB
    if r < 2.5: h = min(h, 0.45)
    plant(mb, x, y, h, CELLS[kind], R, n=2 if r < 8 else 1, segs=2 if r < 10 else 1, wk=0.6)
    placed += 1
    if placed > 1100: break
# weeds in the road's joints and holes
for k in range(70):
    y = R.uniform(-4, 38); x = road_cx(y) + R.uniform(-ROAD_W / 2 + 0.1, ROAD_W / 2 - 0.1)
    if abs(x) < 0.6 and 0 < y < 2: continue
    plant(VMB, x, y, R.uniform(0.12, 0.3), CELLS[R.choice(("grass", "dock", "flowers"))], R, n=1, segs=1, wk=0.8, sink=0.0)
for nm, mb, mat in (("VergeGrass", VMB, M_GRASS), ("FieldGrass", FMB, M_FIELD), ("BrookReeds", RMB, M_REEDS)):
    o = mb.build(nm, mat)
    if o: set_card_normals(o, lambda p: Vector((0, 0, 1)))

# ----------------------------------------------------------------------------- trees: an old apple by the brook, a few fruit trees, the great forest ahead
print("trees ...", flush=True)
S.tree("Apple", -5.2, 3.0, 6.0, 3.6, "oak", 41, M_BARK, "apple", nlimbs=6, detail=1.0, cards_per_tip=1, card_size=1.1, fill=70, lean=(0.4, -0.2))
for k, (x, y, h) in enumerate(((-24.0, 30.0, 5.0), (-30.0, 22.0, 4.5), (22.0, 46.0, 5.0), (-14.0, -26.0, 5.0))):
    S.tree(f"Fruit{k}", x, y, h, 3.0, "oak", 50 + k, M_BARK, "apple", nlimbs=5, detail=0.6, cards_per_tip=1, card_size=1.5, fill=36)
# the forest: a deep belt across the far end of the road (branches meeting over it), big close trees
FR = random.Random(77)
for k in range(80):
    x = FR.uniform(-160, 160); y = 185 + FR.uniform(-10, 40) + 0.0005 * x * x
    if abs(x - road_cx(y)) < 2.5: x += 6 * (1 if x > road_cx(y) else -1)
    S.tree(f"Forest{k}", x, y, FR.uniform(24, 32), FR.uniform(8, 11), "far", 700 + k, M_FBARK, "forest", nlimbs=4, detail=0.3,
           cards_per_tip=0, card_size=9.0, fill=18, roots=False)
for k in range(10):   # nearer outliers at the forest's edge
    x = FR.uniform(-80, 80); y = FR.uniform(150, 210)
    if abs(x - road_cx(y)) < 4: continue
    S.tree(f"Outlier{k}", x, y, FR.uniform(14, 20), FR.uniform(5, 7), "oak", 800 + k, M_FBARK, "forest", nlimbs=5, detail=0.5,
           cards_per_tip=1, card_size=4.0, fill=30, roots=False)
FMASS = MB()
for k in range(70):
    x = -200 + k * 5.8 + FR.gauss(0, 2); y = 215 + 0.0005 * x * x + FR.gauss(0, 6)
    if abs(x - road_cx(y)) < 4: continue
    S.lumps(FMASS, Vector((x, y, gz(x, y) + 14)), 7.0, 11.0, 2, FR, 900 + k, sub=1, sway=(0, 0.2), flat_bottom=gz(x, y))
FMASS.build("ForestMass", M_FORESTMASS, sway=False)
S.build_crowns({"apple": M_APPLE, "forest": M_FOREST}, names={"apple": "CrownsApple", "forest": "CrownsForest"})
# a lonely Munchkin house far off on the left (round, domed), a little rise behind it
HX, HY = -70.0, 95.0
hz = gz(HX, HY)
cyl("MunchkinHouse", 3.2, 3.0, (HX, HY, hz + 1.4), M_HOUSE, verts=20)
sphere("MunchkinDome", 3.4, (HX, HY, hz + 2.9), M_HOUSE, seg=20, scale=(1.0, 1.0, 0.9))

# ----------------------------------------------------------------------------- sky, light
SKY = E8.sky_dome("SkyDome", M_SKY, 900.0, seg=48, rings=14, el_min=-6.0)
K.apply_transforms()
light_obj("light.sun", 'SUN', 3.0, (1.0, 0.95, 0.86), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(3.0))
skl = light_obj("light.sky", 'SUN', 0.8, (0.70, 0.78, 0.95), (0, 0, 30), direction=(0.1, 0.2, -1.0), angle=math.radians(85))
skl.data.use_shadow = False
world = bpy.data.worlds.new("Noon"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.55, 0.62, 0.75, 1); bg.inputs["Strength"].default_value = 0.6

sound("river", "brook", (-2.4, 4.0, gz(-2.4, 4.0) + 0.2))
sound("wind-trees", "apple", (-5.2, 3.0, 5.0))
sound("birds", "0", (-24.0, 30.0, 5.0))
S.reader_anchors(0.0)
anchor("scene.centre", (BASKET.x, BASKET.y, bz))
anchor("road.forest", (road_cx(225.0), 225.0, gz(road_cx(225.0), 225.0)))
S.check_clear(look_yaw=0.0)
EZ = gz(0, 0) + EYE
E = Vector((0, 0, EZ))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EZ - 0.6), 17),
    ("Cam_Basket", (BASKET.x + 0.9, BASKET.y - 0.9, bz + 0.9), (BASKET.x, BASKET.y, bz + 0.15), 28),
    ("Cam_Road", (road_cx(3.0), 3.0, gz(road_cx(3), 3) + 1.2), (road_cx(9.0), 9.0, gz(road_cx(9), 9)), 24),
], pitch=-3.0)
S.finish("yellow-brick-roadside-brook", "yellow_brick_roadside_brook", cams,
         keep_names={"M_Brook": "water.stream.brook", "M_VergeGrass": "veg.grass.verge", "M_FieldGrass": "veg.grass.field", "M_BrookReeds": "veg.reeds.brook",
                     "M_AppleLeaves": "veg.crown.apple", "M_ForestLeaves": "veg.crown.forest", "M_Land": "GroundNear", "M_SkyDome": "SkyDome"},
         keep_uv={"M_Land", "M_Road"},
         size_for={"M_Land": (2048, 256, 2048), "M_Road": (2048, 256, 2048), "M_BrookStones": (512, 64, 256), "M_AppleBark": (512, 64, 256), "M_ForestBark": (256, 32, 128),
                   "M_Wicker": (256, 64, 256), "M_WhiteCloth": (256, 32, 128), "M_Bread": (64, 32, 32), "M_MunchkinHouse": (64, 32), "M_ForestMass": (512, 32, 128), "M_SkyDome": (1024,)},
         page=page, default_exposure=0.0, water_colour={"M_Brook": (0.05, 0.06, 0.04)})
