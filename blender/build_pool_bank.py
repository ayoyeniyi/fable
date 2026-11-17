"""
Fable: the bank of the Pool of Tears (Alice's Adventures in Wonderland, chapter 3, "A Caucus-Race and a Long Tale").

"They were indeed a queer-looking party that assembled on the bank - the birds with draggled feathers, the animals
with their fur clinging close to them, and all dripping wet, cross, and uncomfortable."
"They all sat down at once, in a large ring, with the Mouse in the middle."
"First it marked out a racecourse, in a sort of circle ... and then all the party were placed along the course."
"We beg your acceptance of this elegant thimble."

The reader stands where the Mouse sat, in the middle of the ring on a gently sloping bank of wet dark earth and rough
tussocky grass, facing the pool. Everything is seen at mouse height (about four times life size): the grass tussocks
stand to the reader's chest, the reeds at the margin twice their height, the waterline pebbles are boulders. Round the
reader runs the scuffed circle of the Caucus-race, trodden to mud; comfits lie dropped in the turf, and on a flat stone
beside the ring stands Alice's thimble. Wet patches and dripping trails run up the bank from the water where the party
came out. Ahead, the still salt pool fills the far half of the view, glassy and dark, out to a far shore under the
earthen roof of the hall; across the water a row of lamps hangs from the roof ("a long, low hall, which was lit up by
a row of lamps hanging from the roof", chapter 1), still faintly in reach, warm and reflected in the pool. No sun;
the edges fall into dusk ("the night-air"). No creatures (they have all gone), no door, no garden.

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py (pride_kit,
eighty_kit).

Node names Unity relies on:
  anchor.reader.entrance (feet, z=0, facing +Y toward the pool), anchor.reader.look, anchor.scene.centre (the ring),
  anchor.pool.thimble
  light.key (SUN, the lamps' warm glow from across the pool, soft, low), light.sky (SUN, dim cool fill, no shadow)
  Lamp.hall.0-2 (POINT, the hanging lamps; small and warm)
  fx.lantern.0-2 (the lamps' flames; custom property radius)
  water.pond.tears (the pool), veg.grass.tussock, veg.reeds.margin (COLOR_0.R sway)
  sound.wind.hall (a faint draught in the hall)
  MESH_Hall (the earthen roof and walls), SkyDome is not used (indoor/underground)

Run headless:
  blender -b -P blender/build_pool_bank.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_pool_bank.py -- --render --samples 48 --res 1400
  blender -b -P blender/build_pool_bank.py -- --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b1 as S
from scene_kit_b1 import (K, E8, new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound, light_obj, camera,
                          link, smoothstep, lerp, n2, fbm2, orient, card, plant, set_card_normals, az_dir, TWO_PI)

ARGS = S.setup("pool-bank", 1865, "PoolBank", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
LEVEL = -0.62                 # the pool's surface
POOL_FAR = 46.0

# ----------------------------------------------------------------------------- the ground
def shore_y(x):
    """the waterline ahead: 5.6 m in front of the reader, curving away to the sides (the bank is a low promontory)."""
    return 5.6 + 0.018 * x * x + 0.6 * n2(x, 0, 5.0, 2.0)

def H(x, y):
    r = math.hypot(x, y)
    d = y - shore_y(x)                                           # >0 out in the pool
    bank = -0.08 * smoothstep(-3.5, 0.0, d) * (1 + d / 3.5) if d < 0 else 0.0
    z = 0.0
    z += -0.03 * max(0.0, y)                                     # the bank tips toward the pool
    z += -0.42 * smoothstep(-2.4, 0.0, d)                        # the lip of the bank
    z += -1.3 * smoothstep(0.0, 5.0, d)                          # the pool's bed
    z += 0.06 * n2(x, y, 1.2, 3.0) + 0.12 * n2(x, y, 4.0, 7.0)   # lumpy turf
    z += 0.035 * max(0.0, -y - 2.0) ** 1.2                       # behind: the bank rises gently
    # the far shore and the hall's walls: the ground climbs out of the water toward the roof's foot
    z += 7.0 * smoothstep(38.0, 58.0, r) + smoothstep(30.0, 42.0, r) * (1.0 * n2(x, y, 6.0, 4.0) + 0.6 * n2(x, y, 2.0, 8.0) + 0.6)
    # the ring: trodden almost flat
    rr = math.hypot(x, y)
    z *= 1.0 - 0.6 * smoothstep(3.2, 1.0, rr)
    return z + 0.0 * bank
Z0 = H(0, 0)
def gz(x, y): return H(x, y) - Z0
S.set_ground(gz)
LEVEL = gz(0, shore_y(0)) - 0.02     # the waterline sits exactly at the lip in front of the reader

def wet_fn(x, y):
    """wet: at the waterline, and in drip trails up the bank to the ring (where the party came out)."""
    d = y - shore_y(x)
    w = smoothstep(-1.2, -0.1, d)
    for (x0, x1) in ((-1.6, -0.7), (0.9, 1.4), (2.6, 1.9), (-3.4, -2.2)):       # trails from the water to the ring
        t = (shore_y(x0) - y) / max(0.1, shore_y(x0) - 1.6)
        if 0 <= t <= 1.05:
            cx = x0 + (x1 - x0) * t + 0.25 * math.sin(y * 2.3 + x0)
            w = max(w, smoothstep(0.55, 0.12, abs(x - cx)) * (0.85 - 0.3 * t))
    w = max(w, smoothstep(0.66, 0.74, 0.5 + 0.5 * n2(x, y, 1.6, 9.0)) * 0.6)     # damp patches
    return min(1.0, w)

def worn_fn(x, y):
    """the Caucus-race track: a scuffed circle about 4 m across round the reader (not quite round)."""
    a = math.atan2(y, x)
    rc = 2.05 + 0.18 * math.sin(a * 2 + 0.7) + 0.1 * math.sin(a * 5)
    d = abs(math.hypot(x, y) - rc)
    return smoothstep(0.55, 0.15, d) * (0.75 + 0.25 * n2(x, y, 0.5, 4.0))

def ground_mat(name="M_Bank"):
    """wet dark earth with a coarse short turf (seen at mouse height: blades as long as a hand), the race track
    trodden to muddy bare earth with scuffs, wet patches darker and glossier, fine grit and pebbles at the margin."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    at_w = node(nt, "ShaderNodeAttribute", (-1900, 600)); at_w.attribute_name = "wet"
    at_r = node(nt, "ShaderNodeAttribute", (-1900, 450)); at_r.attribute_name = "worn"
    wet = at_w.outputs["Fac"]; worn = at_r.outputs["Fac"]
    n = noise_(nt, co, 0.6, 5, 0.6, loc=(-1700, 200))
    fine = noise_(nt, co, 14.0, 4, 0.6, loc=(-1700, 0))
    earth = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1500, 200)), c4(K.srgb((0.20, 0.15, 0.10))), c4(K.srgb((0.27, 0.21, 0.15))), (-1300, 200))
    earth = mix_rgb(nt, 'MULTIPLY', 1.0, earth, maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0.82, 1.1, (-1500, 0)), (-1150, 150))
    # turf: streaky blade texture (stretched noise in two directions), moss-green to straw, thinner where worn/wet
    mp = node(nt, "ShaderNodeMapping", (-1700, -250)); mp.inputs["Scale"].default_value = (9.0, 2.2, 9.0); mp.inputs["Rotation"].default_value = (0, 0, 0.6)
    nt.links.new(co, mp.inputs["Vector"])
    bl = noise_(nt, mp.outputs["Vector"], 6.0, 3, 0.6, 1.5, (-1500, -250))
    mp2 = node(nt, "ShaderNodeMapping", (-1700, -450)); mp2.inputs["Scale"].default_value = (2.2, 9.0, 9.0); mp2.inputs["Rotation"].default_value = (0, 0, -0.4)
    nt.links.new(co, mp2.inputs["Vector"])
    bl2 = noise_(nt, mp2.outputs["Vector"], 6.0, 3, 0.6, 1.5, (-1500, -450))
    blades = math_(nt, 'MAXIMUM', bl.outputs["Fac"], bl2.outputs["Fac"], (-1300, -350))
    turf_c = ramp(nt, [(0.0, c4(K.srgb((0.10, 0.12, 0.05)))), (0.5, c4(K.srgb((0.22, 0.25, 0.10)))), (0.75, c4(K.srgb((0.34, 0.34, 0.16)))), (1.0, c4(K.srgb((0.46, 0.42, 0.25))))], (-1100, -350))
    nt.links.new(maprange(nt, blades, 0.35, 0.75, 0, 1, (-1200, -350)), turf_c.inputs["Fac"])
    cover = maprange(nt, noise_(nt, co, 0.35, 4, 0.6, loc=(-1700, -650)).outputs["Fac"], 0.35, 0.6, 0.25, 0.95, (-1500, -650))
    cover = math_(nt, 'MULTIPLY', cover, maprange(nt, worn, 0.15, 0.7, 1.0, 0.05, (-1500, -800)), (-1300, -700))
    cover = math_(nt, 'MULTIPLY', cover, maprange(nt, wet, 0.5, 1.0, 1.0, 0.45, (-1500, -950)), (-1150, -750))
    tuft = math_(nt, 'MULTIPLY', cover, maprange(nt, blades, 0.3, 0.55, 0.0, 1.0, (-1150, -500)), (-1000, -600))
    col = mix_rgb(nt, 'MIX', tuft, earth, turf_c.outputs["Color"], (-900, 100))
    # the track: churned mud with scuff marks (stretched voronoi), a little puddled
    v = voronoi_(nt, co, 3.5, 'F1', (-1300, -1100))
    scuff = maprange(nt, v.outputs["Distance"], 0.1, 0.5, 0.75, 1.05, (-1100, -1100))
    mud = mix_rgb(nt, 'MULTIPLY', 1.0, c4(K.srgb((0.21, 0.16, 0.11))), scuff, (-900, -1100))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', worn, 0.85, (-900, -900)), col, mud, (-700, 100))
    # wet darkening
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', wet, 0.75, (-700, -600)), col, (0.45, 0.44, 0.42, 1), (-500, 100))
    col = K.ao_mul(nt, col, 0.3, 0.35, (-350, -900))
    nt.links.new(col, b.inputs["Base Color"])
    rough = mix_f(nt, math_(nt, 'MULTIPLY', wet, 0.8, (-600, -250)), mix_f(nt, tuft, 0.9, 0.75, (-500, -300)), 0.3, (-350, -300))
    nt.links.new(rough, b.inputs["Roughness"]); b.inputs["Specular IOR Level"].default_value = 0.0
    hgt = math_(nt, 'ADD', math_(nt, 'MULTIPLY', tuft, 0.6, (-700, -1300)), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.3, (-700, -1400)), (-550, -1350))
    hgt = math_(nt, 'ADD', hgt, math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', worn, scuff, (-700, -1500)), 0.4, (-600, -1500)), (-450, -1400))
    bump_from(nt, b, hgt, 0.35, 0.01)
    return m

def hall_mat(name="M_Hall"):
    """the hall's earthen roof and walls far off: packed dark earth with stony bands, root-hairs, darker up high."""
    return S.stone_mat(name, (0.17, 0.13, 0.10), (0.06, 0.05, 0.04), (0.24, 0.19, 0.14), scale=0.25, strata=0.6, moss=0.0, lichen=0.0, rough=0.95, bump=0.5)

print("materials ...", flush=True)
M_GROUND = ground_mat()
M_HALL = hall_mat()
M_PEBBLE = S.stone_mat("M_Pebbles", (0.22, 0.21, 0.19), (0.11, 0.10, 0.10), (0.30, 0.29, 0.27), scale=1.6, wet_z=LEVEL + 0.25, wet_k=0.55, lichen=0.2, rough=0.6, bump=0.12)
M_FLAT = S.stone_mat("M_FlatStone", (0.26, 0.25, 0.22), (0.13, 0.12, 0.11), (0.34, 0.33, 0.30), scale=2.4, lichen=0.35, moss=0.3, rough=0.75, bump=0.2)
M_WATER = S.water_mat("M_PoolWater", deep=(0.012, 0.016, 0.016), rough=0.02)
M_ROOT = S.bark_mat("M_Roots", (0.22, 0.17, 0.12), (0.08, 0.06, 0.05), (0.30, 0.24, 0.17), scale=3.0, fissure=0.4, moss=0.0)
M_SILVER = plain("M_Thimble", (0.80, 0.78, 0.74), rough=0.22, metallic=1.0)
M_BRASS = plain("M_LampBrass", (0.55, 0.40, 0.18), rough=0.35, metallic=1.0)
M_LAMPGLASS = plain("M_LampGlow", (1.0, 0.72, 0.38), rough=0.3, emission=(1.0, 0.66, 0.30), strength=12.0)
M_CHAIN = plain("M_Chain", (0.05, 0.045, 0.04), rough=0.6, metallic=1.0)

def comfit_mat(name="M_Comfits"):
    """sugared comfits: chalky white, pale pink, primrose and pale green sugar shells (colour by object position)."""
    m, nt, b = new_mat(name)
    cell = voronoi_(nt, obj_coords(nt), 6.0, 'F1', (-1100, 0))
    sc = node(nt, "ShaderNodeSeparateColor", (-900, 0)); nt.links.new(cell.outputs["Color"], sc.inputs["Color"])
    r = ramp(nt, [(0.0, c4(K.srgb((0.93, 0.90, 0.86)))), (0.3, c4(K.srgb((0.95, 0.78, 0.80)))), (0.55, c4(K.srgb((0.95, 0.90, 0.62)))),
                  (0.8, c4(K.srgb((0.78, 0.88, 0.72)))), (1.0, c4(K.srgb((0.93, 0.90, 0.86))))], (-600, 0), interp='CONSTANT')
    nt.links.new(sc.outputs[0], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.55
    n = noise_(nt, obj_coords(nt), 80.0, 3, 0.6, loc=(-600, -300))
    bump_from(nt, b, n.outputs["Fac"], 0.2, 0.001)
    return m
M_COMFIT = comfit_mat()

# plant atlas (mouse-height tussock grass, sedge, reeds, bulrush, dock), and feathers
print("atlases ...", flush=True)
WET_GREENS = [(0.14, 0.19, 0.07), (0.18, 0.23, 0.08), (0.22, 0.26, 0.10), (0.12, 0.17, 0.06), (0.26, 0.28, 0.12)]
WET_STRAW = [(0.42, 0.37, 0.22), (0.36, 0.31, 0.19), (0.48, 0.42, 0.27)]
IMG_PLANTS, CELLS = S.plant_atlas("A_BankPlants", ["tussock", "tussock", "sedge", "dock", "reed", "bulrush", "straw", "grass"], seed=1865,
                                  greens=WET_GREENS, straw=WET_STRAW)
M_GRASS = image_mat("M_Tussocks", IMG_PLANTS, rough=0.55, alpha=True)
M_REEDS = image_mat("M_Reeds", IMG_PLANTS, rough=0.5, alpha=True)

def feather_atlas(S_=512):
    """two draggled feathers (a duck's brown speckled covert, a grey-white down feather) side by side."""
    cv = Canvas(S_, S_); R = random.Random(7)
    for k, (cx, col, col2, w) in enumerate(((128, (0.36, 0.27, 0.17), (0.18, 0.13, 0.08), 70), (384, (0.70, 0.68, 0.64), (0.45, 0.44, 0.42), 80))):
        cv.line((cx, S_ - 10), (cx + 6, 20), 3.5, 1.5, (0.82, 0.78, 0.68, 1.0))
        for i in range(120):
            t = i / 120; y = S_ - 40 - t * (S_ - 70); half = w * math.sin(math.pi * min(1, t * 1.15 + 0.05)) * (0.9 if k == 0 else 1.0)
            for sd in (-1, 1):
                ang = sd * (1.1 + R.gauss(0, 0.08)) - 0.25 * sd
                clump = 1.0 if R.random() > 0.12 else 0.5          # draggled: barbs stuck together in wet clumps
                L = half * clump * R.uniform(0.8, 1.05)
                c = col if (i // 6 + (sd > 0)) % 3 else col2
                if k == 0 and R.random() < 0.15: c = (0.80, 0.74, 0.60)
                cv.line((cx + 6 * t, y), (cx + 6 * t + sd * L * abs(math.sin(ang)), y - L * 0.55), 1.6, 0.8, c + (1.0,))
    cv.bleed(6)
    return np_image("A_Feathers", cv.a)
M_FEATHER = image_mat("M_Feathers", feather_atlas(), rough=0.7, alpha=True)

# ----------------------------------------------------------------------------- terrain, pool and the hall
print("terrain ...", flush=True)
NEAR_R = 62.0
GROUND = S.ground("Bank", M_GROUND, NEAR_R, r0=2.2, NA=96, NR=34, attrs={"wet": wet_fn, "worn": worn_fn})
WATER = S.water_surface("PoolOfTears", M_WATER, LEVEL, lambda x, y: gz(x, y) < LEVEL + 0.25 and math.hypot(x, y) < 60, extent=124.0, step=2.0)

def hall_shell():
    """the hall: a low irregular vault of earth over the pool and the bank, its foot below the far ground."""
    me = bpy.data.meshes.new("Hall"); bm = bmesh.new()
    C = Vector((0.0, 12.0, -3.0)); RA = (60.0, 52.0, 14.0)
    NU, NV = 72, 18
    rows = []
    for j in range(NV + 1):
        el = math.radians(-8 + 98 * j / NV)
        row = []
        for i in range(NU):
            az = TWO_PI * i / NU
            d = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
            q = C + Vector((d.x * RA[0], d.y * RA[1], d.z * RA[2]))
            w = 1.0 + 0.10 * noise.noise(d * 3.0 + Vector((3.1, 0, 0))) + 0.05 * noise.noise(d * 9.0) + 0.02 * noise.noise(d * 24.0)
            q = C + (q - C) * w
            row.append(bm.verts.new(q))
        rows.append(row)
    for j in range(NV):
        for i in range(NU):
            i2 = (i + 1) % NU; bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
    bm.faces.new(list(reversed(rows[-1])))
    bm.normal_update()
    for f in bm.faces:
        if f.normal.dot(f.calc_center_median() - C) > 0: f.normal_flip()
        f.smooth = True
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Hall", me); me.materials.append(M_HALL); link(o)
    return o
HALL = hall_shell()
HALL.visible_shadow = False     # the glow reaches under the roof (MESH_Hall casts no shadow)

def roof_z(x, y):
    C = Vector((0.0, 12.0, -3.0)); RA = (60.0, 52.0, 14.0)
    u = ((x - C.x) / RA[0]) ** 2 + ((y - C.y) / RA[1]) ** 2
    return C.z + RA[2] * math.sqrt(max(0.0, 1 - u)) * 0.98

# root tendrils hanging from the roof over the bank (the rabbit-hole's earth above)
R = random.Random(11)
for k in range(34):
    x, y = R.uniform(-26, 26), R.uniform(-24, 30)
    top = roof_z(x, y) + 0.3; L = R.uniform(1.0, 4.5)
    pts = [Vector((x, y, top))]
    for s in range(1, 5):
        p = pts[-1] + Vector((R.gauss(0, 0.18), R.gauss(0, 0.18), -L / 4))
        pts.append(p)
    tube(f"Root{k}", pts, [0.06, 0.04, 0.025, 0.015, 0.006], M_ROOT, sides=4, caps=False)

# ----------------------------------------------------------------------------- the hanging lamps across the water
LAMPS = [Vector((-12.0, 29.0, 0)), Vector((1.5, 34.0, 0)), Vector((15.0, 30.0, 0))]
LAMP_PTS = []
for k, L in enumerate(LAMPS):
    top = roof_z(L.x, L.y) + 0.5; z = top - 3.6 - k * 0.3
    for s in range(14):                                   # the chain: alternate links (cheap rings)
        zz = top - (top - z - 0.6) * (s + 0.5) / 14
        K.box(f"Chain{k}_{s}", (0.05, 0.012, 0.32), (L.x, L.y, zz), M_CHAIN, rot=(0, 0, (s % 2) * math.pi / 2))
    lathe(f"LampBody{k}", [(0.0, 0.62), (0.07, 0.6), (0.20, 0.5), (0.24, 0.42), (0.20, 0.36), (0.16, 0.36)], (L.x, L.y, z - 0.6), M_BRASS, steps=12)
    lathe(f"LampGlass{k}", [(0.15, 0.36), (0.19, 0.24), (0.17, 0.08), (0.10, 0.0), (0.0, -0.02)], (L.x, L.y, z - 0.6), M_LAMPGLASS, steps=12)
    LAMP_PTS.append(Vector((L.x, L.y, z - 0.6 + 0.2)))

# ----------------------------------------------------------------------------- pebbles at the waterline (boulders at mouse height), the flat stone
print("stones ...", flush=True)
R = random.Random(23)
specs = []
for k in range(70):
    x = R.uniform(-22, 22); y = shore_y(x) + R.uniform(-1.1, 0.9)
    if abs(x) < 1.0 and y < 7: continue                      # keep the view ahead open at the water's edge
    s = R.uniform(0.14, 0.42) * (1.0 + 0.6 * smoothstep(4, 18, abs(x)))
    specs.append((x, y, s, 300 + k, {"sub": 2, "bury": R.uniform(0.25, 0.5), "facet": 0.0, "squash": (1.0, R.uniform(0.7, 0.9), R.uniform(0.45, 0.65))}))
for k in range(16):                                          # a few larger stones on the bank and in the shallows
    x = R.uniform(-14, 14); y = shore_y(x) + R.uniform(-3.5, 2.5)
    if math.hypot(x, y) < 3.4 or (abs(x) < 1.6 and y < 9): continue
    specs.append((x, y, R.uniform(0.4, 0.8), 400 + k, {"sub": 2, "bury": 0.45, "facet": 0.05, "squash": (1.0, 0.8, 0.55)}))
FAR_SHORE = []
for i in range(180):
    a = math.radians(-75 + 150 * i / 179); d = Vector((math.sin(a), math.cos(a)))
    for r in np.arange(28.0, 60.0, 0.25):
        if gz(d.x * r, d.y * r) > LEVEL: FAR_SHORE.append((d.x * r, d.y * r)); break
for k in range(60):
    x, y = R.choice(FAR_SHORE); x += R.gauss(0, 0.8); y += R.gauss(0, 0.8)
    specs.append((x, y, R.uniform(0.5, 1.6), 500 + k, {"sub": 1, "bury": 0.4, "facet": 0.15, "squash": (1.0, 0.8, 0.6)}))
S.rocks("Pebbles", specs, M_PEBBLE)
THIMBLE_AT = Vector((1.55, 2.95, 0))
S.rocks("FlatStone", [(THIMBLE_AT.x, THIMBLE_AT.y, 0.42, 77, {"sub": 3, "bury": 0.55, "facet": 0.0, "squash": (1.0, 0.85, 0.34), "yaw": 0.4})], M_FLAT)
fz = gz(THIMBLE_AT.x, THIMBLE_AT.y)
# the stone's top: find it from the mesh
fs = bpy.data.objects["FlatStone"]
top = max((fs.matrix_world @ v.co).z for v in fs.data.vertices if (Vector(((fs.matrix_world @ v.co).x, (fs.matrix_world @ v.co).y)) - THIMBLE_AT.xy).length < 0.12)

# Alice's thimble: a silver thimble standing mouth-down on the stone, dimpled crown, a rolled rim
TH_H = 0.105
th = lathe("Thimble", [(0.0, TH_H), (0.022, TH_H - 0.001), (0.034, TH_H - 0.006), (0.040, TH_H - 0.016), (0.043, 0.03), (0.045, 0.012), (0.049, 0.008),
                       (0.049, 0.0), (0.040, 0.0), (0.038, 0.01), (0.036, TH_H - 0.02), (0.0, TH_H - 0.01)],
           (THIMBLE_AT.x + 0.04, THIMBLE_AT.y - 0.03, top - 0.004), M_SILVER, steps=28)
m = M_SILVER; nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
vv = voronoi_(nt, obj_coords(nt), 160.0, 'F1', (-700, -300))
bump_from(nt, b, maprange(nt, vv.outputs["Distance"], 0.0, 0.45, 0, 1, (-500, -300)), 0.5, 0.002)

# comfits: a few dropped along the ring (one apiece all round, some left uneaten), in the turf
R = random.Random(41)
for k in range(9):
    a = R.uniform(0, TWO_PI); r = R.uniform(1.6, 2.6)
    x, y = r * math.cos(a), r * math.sin(a)
    if y > 0 and abs(x) < 0.55: continue
    s = R.uniform(0.022, 0.03)
    o = sphere(f"Comfit{k}", s, (x, y, gz(x, y) + s * 0.55), M_COMFIT, seg=10, scale=(1.0, 0.75, 0.62))
    o.rotation_euler = (0, 0, R.uniform(0, 3)); o.pass_index = k
o = sphere("ComfitStone", 0.026, (THIMBLE_AT.x - 0.16, THIMBLE_AT.y + 0.05, top + 0.012), M_COMFIT, seg=10, scale=(1.0, 0.75, 0.62))

# feathers on the bank (draggled, flat on the wet ground)
R = random.Random(52)
FMB = MB()
for k, (x, y, cell) in enumerate(((-1.1, 3.3, 0), (2.5, -0.9, 1), (-2.9, 1.6, 0), (0.7, 4.6, 1))):
    z = gz(x, y) + 0.01; a = R.uniform(0, TWO_PI); L = R.uniform(0.32, 0.45)
    d = Vector((math.cos(a), math.sin(a), 0)); s = Vector((-d.y, d.x, 0))
    uv = (0.0, 0.0, 0.5, 1.0) if cell == 0 else (0.5, 0.0, 1.0, 1.0)
    card(FMB, Vector((x, y, z)) - d * L * 0.5, s * L * 0.42, d * L + Vector((0, 0, 0.04)), uv, 0.0, 0.0, bend=Vector((0, 0, -0.03)), segs=2)
fo = FMB.build("Feathers", M_FEATHER, sway=False)
set_card_normals(fo, lambda p: Vector((0, 0, 1)))

# ----------------------------------------------------------------------------- tussocks, sedges, reeds (mouse height)
print("plants ...", flush=True)
GMB = MB(); RMB = MB()
R = random.Random(61)
placed = 0
for i in range(30000):
    r = 22.0 * R.random() ** 1.25 + 0.5; a = R.uniform(0, TWO_PI); x, y = r * math.sin(a), r * math.cos(a)
    d = y - shore_y(x)
    if d > -0.3: continue                                    # dry land only (reeds go separately)
    if worn_fn(x, y) > 0.35: continue                        # the track is trodden bare
    if math.hypot(x, y) < 1.3: continue                      # the Mouse's place
    low = abs(x) < 1.1 and 0 < y < 5.5                       # the view down to the water stays open: low turf only
    if (Vector((x, y)) - THIMBLE_AT.xy).length < 0.7: continue
    if gz(x, y) > 3.0: continue
    dens = 0.35 + 0.65 * smoothstep(0.2, 0.7, 0.5 + 0.5 * n2(x, y, 2.6, 5.0))
    if r > 12: dens *= 0.35
    if R.random() > dens: continue
    kind = R.choices(["tussock", "sedge", "dock", "straw", "grass"], weights=[5, 2, 0.5 if r > 4 else 0.0, 1.5, 2.5])[0]
    h = {"tussock": 1.35, "sedge": 1.1, "dock": 0.8, "straw": 1.25, "grass": 0.7}[kind] * R.uniform(0.75, 1.3)
    if math.hypot(x, y) < 3.0: h = min(h, 0.8)
    if low: kind = "grass"; h = min(h, 0.4)
    n = 2 if (kind == "tussock" and r < 10) else 1
    plant(GMB, x, y, h, CELLS[kind], R, n=n, segs=2 if r < 8 else 1, wk=0.62 if kind == "tussock" else 0.5)
    placed += 1
    if placed > 650: break
print("grass cards", placed)
# reeds and reedmace along the margin, in stands left and right (not straight ahead)
for k in range(260):
    side = R.choice((-1, 1)); x = side * R.uniform(2.6, 26.0) + R.gauss(0, 0.5)
    stand = 0.5 + 0.5 * n2(x, 0, 3.0, 13.0)
    if R.random() > stand: continue
    y = shore_y(x) + R.uniform(-0.5, 1.4)
    if abs(x) < 3.0 and y < 7.5: continue
    kind = "reed" if R.random() < 0.65 else "bulrush"
    h = (4.0 if kind == "reed" else 3.0) * R.uniform(0.75, 1.15) * (1.0 + 0.2 * smoothstep(5, 20, abs(x)))
    plant(RMB, x, y, h, CELLS[kind], R, n=2 if abs(x) < 12 else 1, segs=3, bend=0.1, wk=0.42, sink=0.4 if y > shore_y(x) else 0.05)
for k in range(160):
    x, y = R.choice(FAR_SHORE); x += R.gauss(0, 1.0); y += R.gauss(0, 1.0) + 0.8
    kind = R.choice(("reed", "reed", "bulrush", "tussock"))
    plant(RMB if kind != "tussock" else GMB, x, y, R.uniform(3.0, 4.8) if kind != "tussock" else 1.6, CELLS[kind], R, n=1, segs=1, wk=0.5)
GO = GMB.build("Tussocks", M_GRASS); set_card_normals(GO, lambda p: Vector((0, 0, 1)))
RO = RMB.build("Reeds", M_REEDS); set_card_normals(RO, lambda p: Vector((0, 0, 1)))

# ----------------------------------------------------------------------------- lights and world
K.apply_transforms()
KEY_DIR = (az_dir(8.0) * math.cos(math.radians(22)) + Vector((0, 0, math.sin(math.radians(22))))).normalized()   # from across the pool
light_obj("light.key", 'SUN', 2.2, (1.0, 0.70, 0.42), tuple(KEY_DIR * 30), direction=-KEY_DIR, angle=math.radians(18.0))
skl = light_obj("light.sky", 'SUN', 0.7, (0.55, 0.62, 0.80), (0, 0, 20), direction=(0.2, -0.3, -1.0), angle=math.radians(80))
skl.data.use_shadow = False
for k, p in enumerate(LAMP_PTS):
    light_obj(f"Lamp.hall.{k}", 'POINT', 600.0, (1.0, 0.66, 0.32), tuple(p), shadow_soft_size=0.25)
world = bpy.data.worlds.new("Hall"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.08, 0.085, 0.10, 1); bg.inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- markers and anchors
for k, p in enumerate(LAMP_PTS): E8.fx(f"fx.lantern.{k}", tuple(p + Vector((0, 0, 0.05))), 0.12)
sound("wind", "hall", (-6.0, 12.0, 4.0))
S.reader_anchors(0.0)
anchor("scene.centre", (0.0, 0.0, gz(0, 0)))
anchor("pool.thimble", (THIMBLE_AT.x + 0.04, THIMBLE_AT.y - 0.03, top + TH_H))
S.check_clear(look_yaw=0.0)

# ----------------------------------------------------------------------------- cameras
EZ = gz(0, 0) + EYE
E = Vector((0, 0, EZ))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EZ - 0.8), 17),
    ("Cam_Thimble", (THIMBLE_AT.x - 0.9, THIMBLE_AT.y - 0.9, top + 0.55), (THIMBLE_AT.x + 0.04, THIMBLE_AT.y - 0.03, top + 0.05), 30),
    ("Cam_Shore", (-5.0, shore_y(-5.0) - 2.5, gz(-5, shore_y(-5) - 2.5) + 1.5), (6.0, 2.0, 0.2), 18),
], pitch=-8.0)

S.finish("pool-bank", "pool_bank", cams,
         keep_names={"M_PoolWater": "water.pond.tears", "M_Tussocks": "veg.grass.tussock", "M_Reeds": "veg.reeds.margin",
                     "M_Bank": "GroundNear", "M_Hall": "MESH_Hall"},
         keep_uv={"M_Bank"},
         size_for={"M_Bank": (2048, 512, 1024), "M_Hall": (1024, 64, 512), "M_Pebbles": (1024, 256, 512), "M_FlatStone": (512, 128, 256),
                   "M_Roots": (256, 32, 128), "M_Thimble": (128, 32, 128), "M_Comfits": (64, 32, 32), "M_LampBrass": (64, 32),
                   "M_LampGlow": (32,), "M_Chain": (32,)},
         page=page, default_exposure=0.9, water_colour={"M_PoolWater": (0.012, 0.016, 0.016)}, unlit_emit={"M_LampGlow"})
