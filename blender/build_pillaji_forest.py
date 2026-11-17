"""
Fable: a clearing in the forest near Pillaji, Bundelkhand, at sunset on 24 October 1872 (Around the World in Eighty
Days, chapters 12-13).

"The elephant ... was led into a dense forest ... Towards six o'clock in the evening ... a confused murmur of voices
and the sound of instruments ... The guide ... led the elephant into a thicket ... a procession ... [they] saw ...
the pagoda of Pillaji ... the torches ... 'a suttee'."

The reader stands at the edge of a small clearing in dry deciduous forest - tall sal and teak, a great banyan with
its aerial roots, clumps of bamboo, a tangle of lantana, ferns and grass in the understorey - in the last of the
sun. The clearing ahead-left, where the guide halted Kiouni, is open ground (the elephant was taken out on
2026-11-17: the procedural one did not hold up close in VR). Ahead-right, through a gap in the trees about fifty metres off, the stone tower of the
pagoda of Pillaji catches the low sun; torches burn on poles before its porch, where the procession has gathered
(no people are modelled; their murmur is a sound source), and the wood of the funeral pile is stacked. The sun is
setting behind the reader's left shoulder, raking long light through the trunks; overhead the sky is deepening blue.

Everything procedural (no downloaded models, textures or HDRIs): foliage is alpha-clipped cards painted in numpy;
helpers in blender/eighty_kit.py (pride_kit.py).

Quest 2 foliage budget (2026-11-17): alpha-tested cards are the GPU cost on the Quest's tile renderer, so the near
trees carry fewer, larger cards and the far trees fewer, much larger ones (opaque crown cores and clumps were tried
and read as balls on sticks, so the far canopy is cards plus the two remaining tree-line bands); floor grass stops at
~8 m and the rest of the understorey at ~14 m, with opaque thicket mounds (veg.shrub.thicket, one flowering card
each) further out; nothing tall stands within 2 m of the reader.
blender/measure_alpha_cards.py measures the alpha-card area from the reading position.

Node names Unity relies on:
  anchor.reader.entrance (feet, ground z=0, facing +Y), anchor.reader.look, anchor.scene.centre (the clearing),
  anchor.forest.elephant (kept: the head-height point in the clearing where Kiouni stood), anchor.forest.pagoda, anchor.forest.banyan
  light.sun (SUN, the low setting sun), light.sky (SUN, cool fill), Lamp.torchFire (POINT at the torches: outdoor
  "Fire" lights are warm and baked)
  fx.torch.0-2 (the torches before the porch; custom property radius)
  veg.crown.sal, veg.crown.teak, veg.crown.banyan, veg.leaves.bamboo, veg.shrub.under, veg.grass.floor,
  veg.shrub.thicket (COLOR_0.R sway)
  cloth.flag.pennant (the saffron pennant on the tower's finial)
  sound.birds.dusk, sound.wind-trees.banyan, sound.crowd.procession, sound.fire.torches
  SkyDome, far.Land, far.TreeLine (backdrop)
Register as outdoor (Outdoor = true): a low warm sun, a dusk sky.

Run headless:
  blender -b -P blender/build_pillaji_forest.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_pillaji_forest.py -- --render --samples 48 --res 1400 --captures captures/blender/pillaji-forest
  blender -b -P blender/build_pillaji_forest.py -- --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
import eighty_kit as E8
from eighty_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                        wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound,
                        light_obj, camera, link, smoothstep, lerp, n2, fbm2, add_sway, orient)

ARGS = K.setup("pillaji-forest", "out/pillaji-forest", 1872, "PillajiForest", default_samples=48)
OUT = K.OUT; scene = K.scene
R0 = random.Random(1872)

EYE = 1.55
SUN_AZ, SUN_EL = 258.0, 4.5
def az_dir(az): a = math.radians(az); return Vector((math.sin(a), math.cos(a), 0.0))
SUN_DIR = (az_dir(SUN_AZ) * math.cos(math.radians(SUN_EL)) + Vector((0, 0, math.sin(math.radians(SUN_EL))))).normalized()
ELE = Vector((-3.4, 7.2, 0.0)); ELE_YAW = math.radians(-34.0)
PAGODA = Vector((16.0, 47.0, 0.0))
BANYAN = Vector((-10.5, 2.5, 0.0))
NEAR_R, SKY_R = 46.0, 150.0
PATH = [(0.6, -6.0), (0.4, 0.0), (1.8, 6.0), (5.0, 14.0), (8.5, 24.0), (11.5, 34.0), (14.0, 41.0)]

# ----------------------------------------------------------------------------- the ground
def seg_dist(x, y, pts):
    best = 1e9; bt = 0.0; acc = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L2))
        d = math.hypot(x - (x0 + t * dx), y - (y0 + t * dy))
        if d < best: best = d
    return best
def path_d(x, y): return seg_dist(x, y, PATH)
def H(x, y):
    h = 0.45 * n2(x, y, 0.045, 3.0) + 0.18 * n2(x, y, 0.15, 7.0) + 0.05 * n2(x, y, 0.6, 11.0)
    h += 0.012 * y + 0.4 * smoothstep(20, 46, math.hypot(x, y)) * n2(x, y, 0.03, 5.0)
    h -= 0.08 * smoothstep(1.2, 0.0, path_d(x, y))                               # the trodden path
    clr = smoothstep(7.0, 3.0, math.hypot(x + 1.2, y - 4.0))                       # the clearing, flatter
    return h * (1 - 0.6 * clr)
Z0 = H(0, 0)
def gz(x, y): return H(x, y) - Z0

def ground_mat(name="M_ForestFloor"):
    """dry-season forest floor at low contrast: packed red-brown earth under a scatter of fallen sal leaves (two sizes,
    ochre to tan, curled edges a little darker), thinning to bare earth in drifts; the trodden path smooth, paler and
    leafless, with a few leaves kicked to its edges; faint damp darkening; a few seedlings."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    pa = node(nt, "ShaderNodeAttribute", (-1800, 500)); pa.attribute_name = "bare"
    bare = pa.outputs["Fac"]
    warp = noise_(nt, co, 6.0, 2, 0.5, loc=(-1800, 200))
    wv = node(nt, "ShaderNodeVectorMath", (-1650, 200), operation='MULTIPLY_ADD'); wv.inputs[1].default_value = (0.04, 0.04, 0.0)
    nt.links.new(warp.outputs["Color"], wv.inputs[0]); nt.links.new(co, wv.inputs[2])
    v1 = voronoi_(nt, wv.outputs[0], 11.0, 'F1', (-1500, 200)); v2 = voronoi_(nt, wv.outputs[0], 19.0, 'F1', (-1500, 0))
    lc = node(nt, "ShaderNodeSeparateColor", (-1300, 200)); nt.links.new(v1.outputs["Color"], lc.inputs["Color"])
    lc2 = node(nt, "ShaderNodeSeparateColor", (-1300, 0)); nt.links.new(v2.outputs["Color"], lc2.inputs["Color"])
    leafy = ramp(nt, [(0.0, c4(K.srgb((0.36, 0.25, 0.15)))), (0.35, c4(K.srgb((0.45, 0.32, 0.19)))), (0.7, c4(K.srgb((0.54, 0.41, 0.24)))),
                      (1.0, c4(K.srgb((0.41, 0.29, 0.17))))], (-1100, 200))
    nt.links.new(math_(nt, 'ADD', math_(nt, 'MULTIPLY', lc.outputs[0], 0.6, (-1200, 300)), math_(nt, 'MULTIPLY', lc2.outputs[1], 0.4, (-1200, 150)), (-1150, 250)), leafy.inputs["Fac"])
    edge = maprange(nt, math_(nt, 'MINIMUM', v1.outputs["Distance"], math_(nt, 'MULTIPLY', v2.outputs["Distance"], 1.4, (-1200, -50)), (-1100, 0)), 0.0, 0.18, 0.76, 1.0, (-1000, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, leafy.outputs["Color"], edge, (-900, 200))
    n = noise_(nt, co, 0.5, 4, 0.55, loc=(-1500, -300))
    fine = noise_(nt, co, 40.0, 3, 0.6, loc=(-1500, -450))
    earth = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1300, -300)), c4(K.srgb((0.42, 0.32, 0.23))), c4(K.srgb((0.46, 0.35, 0.25))), (-1100, -300))
    earth = mix_rgb(nt, 'MULTIPLY', 1.0, earth, maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0.93, 1.04, (-1300, -450)), (-1000, -350))
    path = c4(K.srgb((0.50, 0.40, 0.30)))
    earth = mix_rgb(nt, 'MIX', bare, earth, path, (-900, -400))
    cover = maprange(nt, noise_(nt, co, 0.9, 4, 0.6, loc=(-1500, -600)).outputs["Fac"], 0.3, 0.55, 0.62, 1.0, (-1300, -600))
    cover = math_(nt, 'MULTIPLY', cover, maprange(nt, bare, 0.2, 0.7, 1.0, 0.0, (-1300, -750)), (-1100, -650))
    # individual leaves sit on the earth where a cell's random value falls under the cover
    pick = maprange(nt, math_(nt, 'SUBTRACT', cover, lc.outputs[2], (-1000, -600)), -0.02, 0.02, 0, 1, (-900, -600))
    col = mix_rgb(nt, 'MIX', pick, earth, col, (-700, 200))
    damp = maprange(nt, n.outputs["Fac"], 0.62, 0.72, 0, 0.18, (-1000, -850))
    col = mix_rgb(nt, 'MULTIPLY', damp, col, (0.7, 0.66, 0.62, 1), (-500, 200))
    sd = maprange(nt, noise_(nt, co, 3.0, 3, 0.5, loc=(-1500, -1000)).outputs["Fac"], 0.70, 0.72, 0, 0.5, (-1300, -1000))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', sd, math_(nt, 'SUBTRACT', 1.0, bare, (-1100, -1100)), (-1000, -1050)), col, c4(K.srgb((0.30, 0.36, 0.16))), (-400, 200))
    col = K.ao_mul(nt, col, 0.4, 0.4, (-300, -1100))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, pick, 0.82, 0.9, (-300, -200)), b.inputs["Roughness"])
    hgt = math_(nt, 'ADD', math_(nt, 'MULTIPLY', pick, math_(nt, 'MULTIPLY', edge, 1.0, (-700, -1300)), (-600, -1300)), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.15, (-700, -1400)), (-500, -1350))
    bump_from(nt, b, hgt, 0.25, 0.006)
    return m

def bark_mat(name, base, dark, light, scale=1.0, fissure=0.6, moss=0.2):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    mp = node(nt, "ShaderNodeMapping", (-1500, 0)); mp.inputs["Scale"].default_value = (3.0 * scale, 3.0 * scale, 0.5 * scale); nt.links.new(co, mp.inputs["Vector"])
    v = voronoi_(nt, mp.outputs["Vector"], 4.0, 'DISTANCE_TO_EDGE', (-1300, 0))
    n = noise_(nt, co, 4.0 * scale, 6, 0.65, loc=(-1300, -250))
    fis = maprange(nt, v.outputs["Distance"], 0.0, 0.12, 1, 0, (-1100, 0))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1100, -250)), c4(base), c4(light), (-900, -100))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', fis, fissure, (-900, 100)), col, c4(dark), (-700, 0))
    if moss:
        mn = noise_(nt, co, 1.5, 4, 0.6, loc=(-1300, -500))
        col = mix_rgb(nt, 'MIX', maprange(nt, mn.outputs["Fac"], 0.6, 0.7, 0, moss, (-1100, -500)), col, c4(K.srgb((0.20, 0.24, 0.12))), (-550, 0))
    col = K.ao_mul(nt, col, 0.3, 0.45, (-400, -700))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.88
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', fis, -1.0, (-600, -900)), math_(nt, 'MULTIPLY', n.outputs["Fac"], 0.4, (-600, -1000)), (-450, -950)), 0.6, 0.02)
    return m

def stone_mat(name="M_TempleStone"):
    """weathered buff sandstone: fine grain, black streaks of monsoon run-off down from every ledge, lichen, moss low down."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1800, -500))
    n = noise_(nt, co, 3.0, 6, 0.6, loc=(-1500, 200))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1300, 200)), c4(K.srgb((0.50, 0.42, 0.32))), c4(K.srgb((0.62, 0.53, 0.40))), (-1100, 200))
    mp = node(nt, "ShaderNodeMapping", (-1500, -200)); mp.inputs["Scale"].default_value = (4.0, 4.0, 0.25); nt.links.new(co, mp.inputs["Vector"])
    st = noise_(nt, mp.outputs["Vector"], 3.0, 4, 0.6, loc=(-1300, -200))
    col = mix_rgb(nt, 'MIX', maprange(nt, st.outputs["Fac"], 0.5, 0.7, 0, 0.7, (-1100, -200)), col, c4(K.srgb((0.16, 0.14, 0.12))), (-900, 200))
    li = noise_(nt, co, 6.0, 4, 0.6, loc=(-1300, -450))
    col = mix_rgb(nt, 'MIX', maprange(nt, li.outputs["Fac"], 0.65, 0.72, 0, 0.5, (-1100, -450)), col, c4(K.srgb((0.62, 0.62, 0.52))), (-700, 200))
    moss = math_(nt, 'MULTIPLY', maprange(nt, s.outputs["Z"], 1.6, 0.3, 0, 1, (-1300, -700)), maprange(nt, n.outputs["Fac"], 0.45, 0.6, 0, 0.8, (-1300, -800)), (-1100, -750))
    col = mix_rgb(nt, 'MIX', moss, col, c4(K.srgb((0.22, 0.26, 0.12))), (-500, 200))
    col = K.ao_mul(nt, col, 0.25, 0.5, (-350, -900))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, n.outputs["Fac"], 0.3, 0.02)
    return m

def sky_mat(name="M_SkyDome"):
    """sunset over central India: an orange-gold glow low in the west-south-west where the sun is going down, pink and
    lilac above it, a clear deepening blue overhead and in the east, a few long cloud bars lit from below in the west."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-2200, 0), operation='NORMALIZE'); nt.links.new(co, nv.inputs[0]); d = nv.outputs[0]
    s = sep_xyz(nt, d, (-2000, 0)); el = s.outputs["Z"]
    base = ramp(nt, [(0.0, c4((0.30, 0.28, 0.32))), (0.10, c4((0.55, 0.50, 0.55))), (0.2, c4((0.36, 0.42, 0.62))), (0.5, c4((0.16, 0.25, 0.50))), (1.0, c4((0.08, 0.14, 0.34)))], (-1500, 400))
    nt.links.new(maprange(nt, el, -0.1, 1.0, 0, 1, (-1700, 400)), base.inputs["Fac"])
    col = base.outputs["Color"]
    hz = node(nt, "ShaderNodeCombineXYZ", (-1900, 900)); nt.links.new(s.outputs["X"], hz.inputs["X"]); nt.links.new(s.outputs["Y"], hz.inputs["Y"])
    hn = node(nt, "ShaderNodeVectorMath", (-1750, 900), operation='NORMALIZE'); nt.links.new(hz.outputs["Vector"], hn.inputs[0])
    sd = node(nt, "ShaderNodeVectorMath", (-1600, 900), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(Vector((SUN_DIR.x, SUN_DIR.y, 0)).normalized())
    nt.links.new(hn.outputs[0], sd.inputs[0])
    west = math_(nt, 'POWER', maprange(nt, sd.outputs["Value"], -0.2, 1.0, 0, 1, (-1450, 900)), 2.0, (-1300, 900))
    low = maprange(nt, el, 0.35, 0.0, 0, 1, (-1450, 750))
    glow = math_(nt, 'MULTIPLY', west, low, (-1150, 850))
    gcol = ramp(nt, [(0.0, c4((0.55, 0.38, 0.45))), (0.5, c4((0.95, 0.55, 0.30))), (1.0, c4((1.0, 0.72, 0.38)))], (-1000, 1000))
    nt.links.new(glow, gcol.inputs["Fac"])
    col = mix_rgb(nt, 'MIX', math_(nt, 'POWER', glow, 0.7, (-900, 850)), col, gcol.outputs["Color"], (-700, 400))
    zk = math_(nt, 'ADD', math_(nt, 'MAXIMUM', el, 0.0, (-1800, -200)), 0.05, (-1650, -200))
    px = math_(nt, 'DIVIDE', s.outputs["X"], zk, (-1500, -150)); py = math_(nt, 'DIVIDE', s.outputs["Y"], zk, (-1500, -300))
    cv = node(nt, "ShaderNodeCombineXYZ", (-1350, -200)); nt.links.new(px, cv.inputs["X"]); nt.links.new(py, cv.inputs["Y"])
    mp = node(nt, "ShaderNodeMapping", (-1200, -200)); mp.inputs["Scale"].default_value = (0.25, 2.2, 1); mp.inputs["Rotation"].default_value = (0, 0, 0.3)
    nt.links.new(cv.outputs[0], mp.inputs["Vector"])
    cl = noise_(nt, mp.outputs["Vector"], 0.7, 6, 0.6, 0.6, (-1000, -200))
    cbar = math_(nt, 'MULTIPLY', maprange(nt, cl.outputs["Fac"], 0.56, 0.68, 0, 0.8, (-800, -200)), maprange(nt, el, 0.02, 0.2, 0, 1, (-800, -350)), (-650, -250))
    ccol = mix_rgb(nt, 'MIX', math_(nt, 'POWER', west, 0.5, (-700, -500)), (0.22, 0.20, 0.30, 1), (1.0, 0.50, 0.28, 1), (-500, -400))
    col = mix_rgb(nt, 'MIX', cbar, col, ccol, (-300, 300))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m

# ----------------------------------------------------------------------------- painted atlases
def spray(cv, x0, y0, x1, y1, R, kind):
    """a leafy twig spray drawn into a cell: 'sal' (ovate, glossy), 'teak' (very large, rough, few), 'banyan'
    (leathery ovals with figs), 'bamboo' (narrow lanceolate leaves in fans on thin twigs)."""
    W, Hh = x1 - x0, y1 - y0
    bark = (0.20, 0.15, 0.10) if kind != 'bamboo' else (0.30, 0.32, 0.16)
    stack = [((x0 + W * 0.5 + R.gauss(0, W * 0.05), y1 - 2), R.gauss(0, 0.2), Hh * 0.55, 4.5, 0)]
    leaves = []
    while stack:
        (x, y), a, L, w, depth = stack.pop()
        segs = 5; px, py = x, y
        for sgi in range(segs):
            a += R.gauss(0, 0.16)
            nx, ny = px + math.sin(a) * L / segs, py - math.cos(a) * L / segs
            nx = min(max(nx, x0 + 6), x1 - 6); ny = min(max(ny, y0 + 6), y1 - 2)
            ww = w * (1 - sgi / segs * 0.5)
            cv.line((px, py), (nx, ny), ww * 0.5, ww * 0.42, bark + (1.0,))
            if depth >= 1 or sgi >= 2: leaves.append((nx, ny, a))
            if depth < 2 and R.random() < 0.45:
                stack.append(((nx, ny), a + R.choice((-1, 1)) * R.uniform(0.45, 0.95), L * R.uniform(0.45, 0.7), w * 0.62, depth + 1))
            px, py = nx, ny
        leaves.append((px, py, a))
    if kind == 'sal':
        pal = [(0.11, 0.17, 0.05), (0.14, 0.21, 0.06), (0.17, 0.24, 0.07), (0.20, 0.25, 0.08), (0.13, 0.19, 0.06), (0.26, 0.26, 0.09)]
        nper, size, tip = 5, 16.0, 0.4
    elif kind == 'teak':
        pal = [(0.15, 0.20, 0.07), (0.19, 0.23, 0.08), (0.24, 0.25, 0.09), (0.30, 0.27, 0.11), (0.36, 0.28, 0.12)]
        nper, size, tip = 2, 30.0, 0.25
    elif kind == 'banyan':
        pal = [(0.08, 0.14, 0.04), (0.10, 0.17, 0.05), (0.13, 0.19, 0.05), (0.09, 0.15, 0.05)]
        nper, size, tip = 6, 12.0, 0.15
    else:
        pal = [(0.20, 0.27, 0.08), (0.24, 0.30, 0.09), (0.30, 0.32, 0.11), (0.38, 0.36, 0.14), (0.18, 0.25, 0.07)]
        nper, size, tip = 7, 15.0, 0.9
    for (x, y, a) in leaves:
        for k in range(nper):
            b_ = a + R.gauss(0, 1.0); d = R.uniform(2, size * 1.2)
            lx, ly = x + math.sin(b_) * d, y - math.cos(b_) * d
            if not (x0 + 4 < lx < x1 - 4 and y0 + 4 < ly < y1 - 4): continue
            col = R.choice(pal); sh = R.uniform(0.82, 1.15); col = (col[0] * sh, col[1] * sh, col[2] * sh)
            s = size * R.uniform(0.7, 1.25)
            if kind == 'bamboo':
                cv.ellipse(lx, ly, s * 0.12, s, b_, col + (1.0,), tip=0.85)
            else:
                cv.ellipse(lx, ly, s * (0.42 if kind != 'banyan' else 0.5), s * (0.75 if kind != 'teak' else 0.85), b_, col + (1.0,), tip=tip)
                cv.line((lx - math.sin(b_) * s * 0.6, ly + math.cos(b_) * s * 0.6), (lx + math.sin(b_) * s * 0.6, ly - math.cos(b_) * s * 0.6), 0.6, 0.3,
                        (col[0] * 1.3, col[1] * 1.25, col[2] * 1.1, 1.0))
        if kind == 'banyan' and R.random() < 0.3:
            for k in range(R.randint(2, 4)):
                cv.ellipse(x + R.gauss(0, 5), y + R.gauss(0, 5), 2.8, 2.8, 0, (0.55, 0.20, 0.10, 1.0))

def spray_atlas(name, kind, seed, S=1024, per=3):
    cv = Canvas(S, S); R = random.Random(seed); h = S // 2
    for (cx, cy) in ((0, 0), (h, 0), (0, h), (h, h)):
        cv.clip = (cx + 1, cy + 1, cx + h - 1, cy + h - 1)
        for k in range(per): spray(cv, cx + 4, cy + 4, cx + h - 4, cy + h - 4, R, kind)
    cv.clip = None; cv.bleed(6)
    return np_image(name, cv.a)

def blade(cv, x0, y0, length, ang, curve, w0, col_base, col_tip, segs=9):
    x, y = x0, y0; a = ang
    for i in range(segs):
        t0, t1 = i / segs, (i + 1) / segs
        nx = x + math.sin(a) * length / segs; ny = y - math.cos(a) * length / segs
        col = tuple(cb + (ct - cb) * t1 for cb, ct in zip(col_base, col_tip)) + (1.0,)
        cv.line((x, y), (nx, ny), w0 * (1 - t0 * 0.9), w0 * (1 - t1 * 0.9), col)
        x, y = nx, ny; a += curve / segs * (1 + t0)
    return x, y

def under_atlas(S=1024):
    """understorey, 4 x 2 cells (256 wide, 512 tall): (0) tall dry grass, (1) fern, (2) lantana shrub with its orange-pink
    flower heads, (3) a broad-leaved herb (wild turmeric / arrowroot); row 2: (4) short grass tuft, (5) seedling sal,
    (6) dry grass gone straw, (7) a young bamboo shoot."""
    cv = Canvas(S, S); R = random.Random(31)
    greens = [(0.16, 0.22, 0.07), (0.20, 0.26, 0.08), (0.24, 0.28, 0.09), (0.14, 0.20, 0.06)]
    straw = [(0.52, 0.44, 0.26), (0.46, 0.38, 0.22), (0.58, 0.50, 0.30)]
    def cell(c, r): return (c * 256, r * 512, c * 256 + 256, r * 512 + 512)
    # (0) tall grass
    x0, y0, x1, y1 = cell(0, 0); cv.clip = (x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    for i in range(70):
        bx = x0 + 128 + R.gauss(0, 30); g = R.choice(greens if R.random() > 0.3 else straw)
        blade(cv, bx, y1 - 4, R.uniform(250, 490), R.gauss(0, 0.25) + (bx - x0 - 128) / 300, R.gauss(0, 0.8), R.uniform(2.5, 4.0), g, tuple(c * 1.4 for c in g), segs=12)
    # (1) fern: arching fronds with paired pinnae
    x0, y0, x1, y1 = cell(1, 0); cv.clip = (x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    for f in range(7):
        a = -1.0 + f * 0.33 + R.gauss(0, 0.1); L = R.uniform(260, 420); x, y = x0 + 128, y1 - 6
        g = R.choice(greens)
        for k in range(14):
            t = k / 14; nx = x + math.sin(a) * L / 14; ny = y - math.cos(a) * L / 14
            cv.line((x, y), (nx, ny), 2.0, 1.6, (0.18, 0.16, 0.08, 1.0))
            pl = 26 * (1 - t) ** 0.8 + 4
            for sg in (-1, 1):
                cv.ellipse(nx + math.cos(a) * sg * pl * 0.5, ny + math.sin(a) * sg * pl * 0.5, pl * 0.5, 4.5, a + sg * 1.57, g + (1.0,), tip=0.3)
            x, y = nx, ny; a += 0.07 * math.copysign(1, a)
    # (2) lantana
    x0, y0, x1, y1 = cell(2, 0); cv.clip = (x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    for k in range(4): spray(cv, x0 + 4, y0 + 160, x1 - 4, y1 - 4, R, 'sal')
    for k in range(26):
        fx, fy = x0 + R.uniform(30, 226), y0 + R.uniform(200, 420)
        for j in range(9):
            cv.ellipse(fx + R.gauss(0, 4), fy + R.gauss(0, 4), 3.2, 3.2, 0, R.choice([(0.85, 0.42, 0.18), (0.90, 0.60, 0.25), (0.80, 0.35, 0.45)]) + (1.0,))
    # (3) broad herb
    x0, y0, x1, y1 = cell(3, 0); cv.clip = (x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    for k in range(6):
        a = R.uniform(-0.9, 0.9); L = R.uniform(200, 380); W = L * 0.26
        cx_, cy_ = x0 + 128 + math.sin(a) * L * 0.55, y1 - 6 - math.cos(a) * L * 0.55
        cv.line((x0 + 128, y1 - 6), (cx_, cy_), 3.0, 2.0, (0.18, 0.22, 0.08, 1.0))
        cv.ellipse(cx_ + math.sin(a) * L * 0.2, cy_ - math.cos(a) * L * 0.2, W, L * 0.42, a, R.choice(greens) + (1.0,), tip=0.5)
    # row 2
    x0, y0, x1, y1 = cell(0, 1); cv.clip = (x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    for i in range(60):
        bx = x0 + 128 + R.gauss(0, 34); g = R.choice(greens)
        blade(cv, bx, y1 - 4, R.uniform(120, 260), R.gauss(0, 0.35), R.gauss(0, 0.6), R.uniform(2.5, 3.5), g, tuple(c * 1.4 for c in g))
    x0, y0, x1, y1 = cell(1, 1); cv.clip = (x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    for k in range(2): spray(cv, x0 + 4, y0 + 120, x1 - 4, y1 - 4, R, 'sal')
    x0, y0, x1, y1 = cell(2, 1); cv.clip = (x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    for i in range(70):
        bx = x0 + 128 + R.gauss(0, 34); g = R.choice(straw)
        blade(cv, bx, y1 - 4, R.uniform(200, 470), R.gauss(0, 0.3), R.gauss(0, 1.0), R.uniform(2.0, 3.5), g, tuple(min(1, c * 1.2) for c in g), segs=12)
    x0, y0, x1, y1 = cell(3, 1); cv.clip = (x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    for k in range(2): spray(cv, x0 + 4, y0 + 40, x1 - 4, y1 - 4, R, 'bamboo')
    cv.clip = None; cv.bleed(6)
    return np_image("A_Understorey", cv.a)

def treeline_atlas(W=2048, Hrow=256):
    """the distance in four bands, one per atlas row (top row first): low hills in the warm sunset haze, then far,
    middle and near forest canopy, each a soft silhouette made of rounded crowns (union of circles, no points),
    darker and less hazed the nearer the band; a little tone in each crown, lighter on its upper edge."""
    rows = []
    specs = [  # (base height px, crown radius range px, colour, haze-lit top tint)
        (60, (70, 140), (0.50, 0.40, 0.39), (0.58, 0.45, 0.40)),
        (95, (22, 46), (0.34, 0.30, 0.30), (0.40, 0.34, 0.32)),
        (100, (18, 38), (0.24, 0.23, 0.22), (0.29, 0.26, 0.23)),
        (90, (14, 32), (0.16, 0.165, 0.15), (0.20, 0.19, 0.16)),
    ]
    xs = np.arange(W, dtype=np.float32)
    for k, (base, (r0, r1), col, tint) in enumerate(specs):
        R = random.Random(50 + k)
        h = np.full(W, float(base), np.float32)
        x = 0.0
        while x < W:
            r = R.uniform(r0, r1); cy = base + R.uniform(-0.6, 0.15) * r + (25 * math.sin(x / W * 2 * math.pi * 2 + k) if k else 0)
            for off in (-W, 0, W):
                d = xs - (x + off)
                inside = np.abs(d) < r
                h = np.where(inside, np.maximum(h, cy + np.sqrt(np.maximum(0.0, r * r - d * d))), h)
            x += R.uniform(0.45, 0.9) * r
        h = np.minimum(h, Hrow - 4)
        yy = np.arange(Hrow, dtype=np.float32)[:, None]            # 0 at the bottom of the band
        inside = yy < h[None, :]
        img = np.zeros((Hrow, W, 4), np.float32)
        topness = np.clip(1.0 - (h[None, :] - yy) / 18.0, 0, 1)    # within 18 px of the edge: lit by the sky
        n = np.random.RandomState(7 + k).rand(Hrow, W).astype(np.float32) * 0.02
        for c in range(3):
            img[..., c] = col[c] * (1 - topness) + tint[c] * topness + n
        img[..., 3] = inside.astype(np.float32)
        # bleed colour into the transparent pixels (no dark fringe under mipmapping)
        img[..., :3] = np.where(inside[..., None], img[..., :3], np.array(tint, np.float32))
        rows.append(img[::-1])                                    # row 0 = top of the band
    atlas = np.concatenate(rows, axis=0)
    return np_image("A_TreeLine", atlas)

print("painting atlases ...", flush=True)
IMG_SAL = spray_atlas("A_SalSprays", 'sal', 11)
IMG_TEAK = spray_atlas("A_TeakSprays", 'teak', 12, per=2)
IMG_BANYAN = spray_atlas("A_BanyanSprays", 'banyan', 13, per=3)
IMG_BAMBOO = spray_atlas("A_BambooSprays", 'bamboo', 14, per=3)
IMG_UNDER = under_atlas()
IMG_TREELINE = treeline_atlas()

M_SAL = image_mat("M_SalLeaves", IMG_SAL, rough=0.5, alpha=True)
M_TEAKL = image_mat("M_TeakLeaves", IMG_TEAK, rough=0.6, alpha=True)
M_BANYANL = image_mat("M_BanyanLeaves", IMG_BANYAN, rough=0.45, alpha=True)
M_BAMBOOL = image_mat("M_BambooLeaves", IMG_BAMBOO, rough=0.5, alpha=True)
M_UNDER = image_mat("M_Understorey", IMG_UNDER, rough=0.6, alpha=True)
M_GRASS = image_mat("M_FloorGrass", IMG_UNDER, rough=0.6, alpha=True)
M_TREELINE = image_mat("M_TreeLine", IMG_TREELINE, rough=1.0, alpha=True, spec=0.0)
M_GROUND = ground_mat()
M_SALBARK = bark_mat("M_SalBark", K.srgb((0.24, 0.20, 0.16)), K.srgb((0.08, 0.06, 0.05)), K.srgb((0.34, 0.30, 0.25)), scale=1.0, fissure=0.7, moss=0.15)
M_TEAKBARK = bark_mat("M_TeakBark", K.srgb((0.36, 0.32, 0.26)), K.srgb((0.16, 0.13, 0.10)), K.srgb((0.46, 0.42, 0.35)), scale=1.6, fissure=0.5, moss=0.05)
M_BANYANBARK = bark_mat("M_BanyanBark", K.srgb((0.30, 0.28, 0.25)), K.srgb((0.15, 0.14, 0.12)), K.srgb((0.38, 0.36, 0.32)), scale=0.5, fissure=0.3, moss=0.3)
M_BAMBOO = noisy("M_BambooCulm", [K.srgb((0.40, 0.42, 0.20)), K.srgb((0.48, 0.48, 0.24)), K.srgb((0.36, 0.38, 0.17))], scale=8, rough=0.45, bump=0.1, stretch=(4, 4, 0.3))
M_STONE = stone_mat()
M_LOG = bark_mat("M_DeadWood", K.srgb((0.30, 0.26, 0.21)), K.srgb((0.12, 0.10, 0.08)), K.srgb((0.42, 0.38, 0.32)), scale=1.2, fissure=0.6, moss=0.25)
M_PYRE = noisy("M_PyreWood", [K.srgb((0.36, 0.28, 0.18)), K.srgb((0.45, 0.36, 0.24)), K.srgb((0.28, 0.21, 0.14))], scale=10, rough=0.8, stretch=(1, 1, 6))
M_ROCK = noisy("M_Rock", [K.srgb((0.32, 0.28, 0.24)), K.srgb((0.40, 0.36, 0.30)), K.srgb((0.26, 0.23, 0.20))], scale=3, rough=0.85, bump=0.4, bump_dist=0.01)
M_IRON = plain("M_TorchIron", (0.03, 0.028, 0.025), rough=0.6)
M_FLAG = plain("M_Pennant", K.srgb((0.85, 0.42, 0.08)), rough=0.8)
M_FARLAND = noisy("M_FarLand", [K.srgb((0.05, 0.045, 0.04)), K.srgb((0.07, 0.06, 0.05))], scale=0.1, rough=1.0, bump=0.0)
next(n for n in M_FARLAND.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs["Specular IOR Level"].default_value = 0.0
M_SKY = sky_mat()
M_BRASS = plain("M_Brass", (0.70, 0.50, 0.24), rough=0.3, metallic=1.0)
def crown_mass_mat(name, dark, mid, light, scale=1.6):
    """opaque foliage mass for the thickets: leaf clumps as voronoi cells (lit on their upper faces,
    dark in the gaps between them), a slow tonal drift, darker underneath; a strong clump bump."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    warp = noise_(nt, co, 2.0, 2, 0.5, loc=(-1700, 200))
    wv = node(nt, "ShaderNodeVectorMath", (-1550, 200), operation='MULTIPLY_ADD'); wv.inputs[1].default_value = (0.25, 0.25, 0.25)
    nt.links.new(warp.outputs["Color"], wv.inputs[0]); nt.links.new(co, wv.inputs[2])
    v = voronoi_(nt, wv.outputs[0], scale, 'F1', (-1400, 200))
    gap = maprange(nt, v.outputs["Distance"], 0.25, 0.6, 0, 1, (-1200, 200))
    n = noise_(nt, co, 0.15, 3, 0.5, loc=(-1400, -100))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.35, 0.65, 0, 1, (-1200, -100)), c4(mid), c4(light), (-1000, 0))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', gap, 0.75, (-1000, 200)), col, c4(dark), (-800, 0))
    geo = node(nt, "ShaderNodeNewGeometry", (-1400, -400)); gs = sep_xyz(nt, geo.outputs["Normal"], (-1250, -400))
    under = maprange(nt, gs.outputs["Z"], 0.1, -0.7, 0, 0.55, (-1100, -400))
    col = mix_rgb(nt, 'MIX', under, col, c4(dark), (-600, 0))
    fine = noise_(nt, co, 9.0, 3, 0.6, loc=(-1400, -650))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0.8, 1.12, (-1200, -650)), (-450, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.75
    b.inputs["Specular IOR Level"].default_value = 0.3
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', gap, -1.0, (-700, -800)), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.3, (-700, -900)), (-550, -850)), 0.8, 0.15)
    return m
M_THICKET = crown_mass_mat("M_Thicket", K.srgb((0.07, 0.08, 0.03)), K.srgb((0.17, 0.20, 0.07)), K.srgb((0.30, 0.28, 0.12)), scale=4.0)
M_FLAME = plain("M_RenderFlame", (1.0, 0.6, 0.2), emission=(1.0, 0.55, 0.18), strength=40.0)

# ----------------------------------------------------------------------------- the ground mesh (log-polar UVs: densest at the reader's feet)
RG0 = 2.5
def v_of_r(r): return math.log1p(r / RG0) / math.log1p(NEAR_R / RG0)
def ground():
    NA, NR = 48, 23
    verts = []; faces = []; uvs = {}; bare = []
    rs = [0.0] + [RG0 * math.expm1(v * math.log1p(NEAR_R / RG0)) for v in [(j / NR) for j in range(1, NR + 1)]]
    verts.append((0.0, 0.0, gz(0, 0))); bare.append(smoothstep(1.1, 0.45, path_d(0, 0)))
    for j in range(1, NR + 1):
        r = rs[j]
        for i in range(NA):
            a = 2 * math.pi * i / NA
            x, y = r * math.sin(a), r * math.cos(a)
            verts.append((x, y, gz(x, y))); bare.append(smoothstep(1.1, 0.45, path_d(x, y)))
    def vi(j, i): return 0 if j == 0 else 1 + (j - 1) * NA + (i % NA)
    loops_uv = []
    for j in range(NR):
        for i in range(NA):
            u0, u1 = i / NA, (i + 1) / NA; v0, v1 = v_of_r(rs[j]), v_of_r(rs[j + 1])
            if j == 0:
                faces.append((vi(0, 0), vi(1, i), vi(1, i + 1))); loops_uv.append([((u0 + u1) / 2, 0.0), (u0, v1), (u1, v1)])
            else:
                faces.append((vi(j, i), vi(j + 1, i), vi(j + 1, i + 1), vi(j, i + 1))); loops_uv.append([(u0, v0), (u0, v1), (u1, v1), (u1, v0)])
    me = bpy.data.meshes.new("Ground"); me.from_pydata(verts, [], faces); me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for p, luv in zip(me.polygons, loops_uv):
        for li, uv in zip(p.loop_indices, luv): uvl.data[li].uv = uv
    o = bpy.data.objects.new("Ground", me); me.materials.append(M_GROUND)
    for p in me.polygons: p.use_smooth = True
    link(o)
    at = me.attributes.new("bare", 'FLOAT', 'POINT'); at.data.foreach_set("value", bare)
    orient(o, lambda c: (0, 0, 1))
    return o
GROUND = ground()
def far_land():
    verts = []; faces = []; seg = 72
    for r in (NEAR_R - 1.0, SKY_R - 3.0):
        for i in range(seg):
            a = 2 * math.pi * i / seg; x, y = r * math.sin(a), r * math.cos(a)
            verts.append((x, y, gz(x, y) - 0.05 if r < NEAR_R else gz(0, 0) + 0.8))
    for i in range(seg):
        j = (i + 1) % seg; faces.append((i, j, seg + j, seg + i))
    return orient(mesh_from("FarLand", verts, faces, M_FARLAND), lambda c: (0, 0, 1))
far_land()

# ----------------------------------------------------------------------------- card helpers
def set_card_normals(o, fn):
    me = o.data
    me.normals_split_custom_set_from_vertices([tuple(fn(v.co)) for v in me.vertices])
def card(mb, base, right, up, cell, sway0, sway1, bend=None, segs=1):
    base = Vector(base); right = Vector(right); up = Vector(up)
    u0, v0, u1, v1 = cell; rows = []
    for k in range(segs + 1):
        t = k / segs
        off = up * t + (bend * (t * t) if bend is not None else Vector())
        sw = sway0 + (sway1 - sway0) * t
        rows.append((mb.vert(base - right * 0.5 + off, (u0, v0 + (v1 - v0) * t), sw), mb.vert(base + right * 0.5 + off, (u1, v0 + (v1 - v0) * t), sw)))
    for k in range(segs):
        a, b_ = rows[k]; c, d = rows[k + 1]; mb.face(a, b_, d, c)
QUAD = [(0.0, 0.5, 0.5, 1.0), (0.5, 0.5, 1.0, 1.0), (0.0, 0.0, 0.5, 0.5), (0.5, 0.0, 1.0, 0.5)]
UNDER = {k: ((i % 4) * 0.25, 0.5 if i < 4 else 0.0, (i % 4) * 0.25 + 0.25, 1.0 if i < 4 else 0.5)
         for i, k in enumerate(("tallgrass", "fern", "lantana", "herb", "grass", "seedling", "straw", "shoot"))}

# ----------------------------------------------------------------------------- trees (after build_fields_to_netherfield.py's tree(): limbs to a crown envelope, cards at the ends)
CROWN_MB = {}
THICKET = MB()
def lumps(mb, C, a_, c_, n, R, seed, sub=1, sway=(0.15, 0.55), flat_bottom=None):
    """an opaque foliage mass: n overlapping noise-displaced icospheres filling an ellipsoid (a_, a_, c_) round C,
    the larger lumps toward the middle; sway weight R rises from sway[0] at the bottom to sway[1] at the top."""
    bm = bmesh.new()
    for k in range(n):
        if k == 0: off = Vector((0, 0, 0)); r = 0.78
        else:
            az = R.uniform(0, 2 * math.pi); el = R.uniform(-0.35, 0.9)
            off = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * R.uniform(0.35, 0.62); r = R.uniform(0.42, 0.6)
        ctr = C + Vector((off.x * a_, off.y * a_, off.z * c_))
        rr = Vector((r * a_ * R.uniform(0.85, 1.1), r * a_ * R.uniform(0.85, 1.1), r * c_ * R.uniform(0.85, 1.05)))
        res = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        for v in res["verts"]:
            d = v.co.normalized()
            w = 1.0 + 0.16 * noise.noise(d * 2.2 + Vector((seed * 0.37 + k, k * 1.3, seed * 0.11)))
            q = ctr + Vector((d.x * rr.x, d.y * rr.y, d.z * rr.z)) * w
            if flat_bottom is not None: q.z = max(q.z, flat_bottom)
            v.co = q
    zs = [v.co.z for v in bm.verts]; z0, z1 = min(zs), max(zs)
    b0 = len(mb.v)
    vmap = {}
    for v in bm.verts:
        t = (v.co.z - z0) / max(1e-6, z1 - z0)
        vmap[v] = mb.vert(v.co.copy(), (0, 0), sway[0] + (sway[1] - sway[0]) * t)
    for f in bm.faces: mb.face(*[vmap[v] for v in f.verts])
    bm.free()

def tree(name, x, y, height, spread, kind, seed, bark, leaves_key, nlimbs=6, detail=1.0, cards_per_tip=3, card_size=1.3, lean=(0, 0), fill=0):
    R = random.Random(seed)
    z0 = gz(x, y) - 0.2
    base = Vector((x, y, z0))
    shape = {"sal": (0.55, 0.75, 0.28), "teak": (0.45, 1.0, 0.32), "banyan": (0.22, 1.0, 0.36), "far": (0.5, 0.8, 0.3)}[kind]
    trunk_h = height * shape[0]
    a_ = spread * shape[1]; c_ = (height - trunk_h) * 0.5
    C = base + Vector((lean[0], lean[1], trunk_h + c_ * 0.95))
    r0 = height * {"sal": 0.024, "teak": 0.026, "banyan": 0.06, "far": 0.02}[kind]
    def env(az, el, k=1.0):
        return C + Vector((math.cos(az) * math.cos(el) * a_ * (1 + 0.12 * R.gauss(0, 1)), math.sin(az) * math.cos(el) * a_ * (1 + 0.12 * R.gauss(0, 1)), math.sin(el) * c_)) * k
    tubes = []; tips = []
    top = base + Vector((lean[0], lean[1], trunk_h))
    tp = [base + (top - base) * t + Vector((R.gauss(0, 0.06), R.gauss(0, 0.06), 0)) * float(t > 0) for t in (0, 0.08, 0.3, 0.65, 1.0)]
    tubes.append((tp, [r0 * 1.9, r0 * 1.3, r0 * 1.05, r0 * 0.95, r0 * 0.85], 9 if detail >= 1 else 5))
    def bent(p0, p1, sag, n, wob):
        pts = []
        for i in range(n + 1):
            t = i / n; q = p0.lerp(p1, t); q.z -= sag * math.sin(math.pi * t) * (p1 - p0).length
            if 0 < i < n: q += Vector((R.gauss(0, wob), R.gauss(0, wob), R.gauss(0, wob)))
            pts.append(q)
        return pts
    sag = {"sal": -0.04, "teak": 0.0, "banyan": 0.12, "far": 0.0}[kind]
    wob = {"sal": 0.08, "teak": 0.12, "banyan": 0.2, "far": 0.1}[kind]
    for i in range(nlimbs):
        az = 2 * math.pi * (i + R.uniform(-0.3, 0.3)) / nlimbs
        el = R.uniform(0.0, 0.45) if kind == "banyan" else R.uniform(0.3, 1.0)
        start = tp[-1] if i % 3 else tp[-2].lerp(tp[-1], 0.6)
        tgt = env(az, el, 0.8)
        lp = bent(start, tgt, sag, 4, wob * spread * 0.08)
        rl = [r0 * (0.75 if kind == "banyan" else 0.6) * (1 - 0.6 * k / 4) for k in range(5)]
        tubes.append((lp, rl, 5 if detail >= 1 else 3) if detail >= 0.5 else (lp[::2], rl[::2], 3))
        tips.append((lp[-1], (tgt - start).normalized(), 0))
        for j in range(4 if detail >= 1 else (3 if detail >= 0.5 else 0)):
            k = R.randint(1, 4); bp = lp[k]
            bt = env(az + R.gauss(0, 0.6), el + R.gauss(0, 0.35), R.uniform(0.92, 1.02))
            bpts = bent(bp, bt, sag * 0.6, 3, wob * 0.25)
            br = [rl[k] * 0.55 * (1 - 0.65 * q / 3) for q in range(4)]
            if detail >= 0.6: tubes.append((bpts, br, 3))
            d = (bt - bp).normalized(); tips.append((bpts[-1], d, 1))
            for q in (1, 2): tips.append((bpts[q] + Vector((R.gauss(0, 0.3), R.gauss(0, 0.3), R.gauss(0, 0.2))), d, 2))
    for k, (pl, rl, sides) in enumerate(tubes):
        tube(f"{name}_b{k}", pl, rl, bark, sides=sides, caps=False)
    mb = CROWN_MB.setdefault(leaves_key, MB())
    def put(q, out, sz):
        tang = out.cross(Vector((0, 0, 1)))
        if tang.length < 0.1: tang = Vector((1, 0, 0))
        tang.normalize(); bit = out.cross(tang).normalized(); roll = R.uniform(-math.pi, math.pi)
        right = (tang * math.cos(roll) + bit * math.sin(roll)) * sz
        up = (bit * math.cos(roll) - tang * math.sin(roll)) * sz + out * sz * R.uniform(0.2, 0.5)
        card(mb, q - up * 0.5, right, up, R.choice(QUAD), 0.35, 1.0)
    for (q, d, depth) in tips:
        for c in range(int(cards_per_tip + R.random())):
            out = ((q - C) * Vector((1 / a_, 1 / a_, 1 / c_))).normalized()
            out = (out + d * 0.5 + Vector((R.gauss(0, 0.45), R.gauss(0, 0.45), R.gauss(0, 0.35)))).normalized()
            put(q, out, card_size * R.uniform(0.75, 1.25))
    for i in range(fill):
        az = R.uniform(0, 2 * math.pi); el = math.asin(R.uniform(-0.4, 1.0))
        q = env(az, el, R.uniform(0.72, 1.0) ** 0.6)
        out = ((q - C) * Vector((1 / a_, 1 / a_, 1 / c_))).normalized()
        out = (out + Vector((R.gauss(0, 0.4), R.gauss(0, 0.4), R.gauss(0, 0.3)))).normalized()
        put(q, out, card_size * R.uniform(0.7, 1.2))
    CROWNS.append((leaves_key, C, a_, c_))
    # buttress roots at the foot
    for k in range(5 if detail >= 1 else 0):
        az = 2 * math.pi * k / 5 + R.uniform(-0.3, 0.3); d = Vector((math.cos(az), math.sin(az), 0))
        p0 = base + Vector((0, 0, r0 * 3.5)); p1 = base + d * r0 * 4.5 + Vector((0, 0, 0.15)); p2 = base + d * r0 * 8 + Vector((0, 0, 0.0))
        p2.z = gz(p2.x, p2.y) - 0.08
        rk = 0.55 if kind == "banyan" else 1.0
        tube(f"{name}_root{k}", [p0, p1, p2], [r0 * 0.8 * rk, r0 * 0.5 * rk, r0 * 0.15 * rk], bark, sides=5)
    return C
CROWNS = []

print("trees ...", flush=True)
TREES = [  # x, y, height, spread, kind, seed, near?
    (6.5, 10.5, 21.0, 4.5, "sal", 101, True), (-6.5, 15.5, 23.0, 5.0, "sal", 102, True), (2.0, 19.0, 22.0, 4.5, "sal", 103, True),
    (9.5, 3.5, 18.0, 5.5, "teak", 104, True), (-2.5, -7.5, 20.0, 5.0, "sal", 105, True), (7.5, -6.0, 17.0, 5.5, "teak", 106, True),
    (-14.0, 19.0, 22.0, 5.0, "sal", 107, False), (12.0, 22.0, 20.0, 5.0, "sal", 108, False), (-4.5, 28.0, 24.0, 5.5, "sal", 109, False),
    (20.0, 30.0, 21.0, 5.0, "teak", 110, False), (5.5, 34.0, 22.0, 5.0, "sal", 111, False), (24.0, 14.0, 20.0, 5.5, "sal", 112, False),
    (-18.0, 8.0, 19.0, 5.0, "teak", 113, False), (-20.0, -10.0, 21.0, 5.5, "sal", 114, False), (14.0, -14.0, 20.0, 5.0, "sal", 115, False),
    (-8.0, -18.0, 21.0, 5.0, "teak", 116, False), (26.0, 40.0, 20.0, 5.0, "sal", 117, False), (8.0, 46.0, 21.0, 5.0, "sal", 118, False),
    (-12.0, 36.0, 22.0, 5.0, "sal", 119, False), (30.0, 22.0, 19.0, 5.0, "teak", 120, False), (2.0, -20.0, 20.0, 5.0, "sal", 121, False),
    (-26.0, 26.0, 20.0, 5.0, "sal", 122, False), (22.0, -4.0, 19.0, 5.0, "sal", 123, False), (-28.0, 2.0, 20.0, 5.0, "sal", 124, False),
]
for k, (x, y, h, s, kind, seed, near) in enumerate(TREES):
    leaves = "sal" if kind == "sal" else "teak"
    # near: fewer, larger cards; far (18 m and more): fewer, much larger cards
    tree(f"Tree{k}", x, y, h, s, kind, seed, M_SALBARK if kind == "sal" else M_TEAKBARK, leaves, nlimbs=5 if near else 4, detail=1.0 if near else 0.5,
         cards_per_tip=1 if near else 0, card_size=(2.3 if kind == "sal" else 2.5) * (1.0 if near else 1.75), fill=26 if near else 28)

# a ring of cheap distant trees (trunk, four limbs, cards) between the clearing's trees and the skyline strip
FR = random.Random(909)
for k in range(14):
    a = 2 * math.pi * (k + FR.uniform(-0.3, 0.3)) / 14; r = FR.uniform(31.0, 45.0)
    x, y = r * math.sin(a), r * math.cos(a)
    if math.hypot(x - PAGODA.x, y - PAGODA.y) < 10: continue
    tree(f"FarTree{k}", x, y, FR.uniform(18, 24), FR.uniform(5, 6.5), "far", 600 + k, M_SALBARK, "sal", nlimbs=4, detail=0.3,
         cards_per_tip=0, card_size=5.5, fill=14)

# the banyan: a broad low crown on great limbs, a fluted trunk, aerial roots hanging from the limbs, some grown into props
def banyan():
    R = random.Random(77)
    C = tree("Banyan", BANYAN.x, BANYAN.y, 15.0, 10.0, "banyan", 201, M_BANYANBARK, "banyan", nlimbs=8, detail=1.0, cards_per_tip=1, card_size=2.6, fill=150)
    for k in range(6):   # extra trunk flutes
        a = 2 * math.pi * k / 6 + R.uniform(-0.2, 0.2); d = Vector((math.cos(a), math.sin(a), 0))
        b0 = BANYAN + d * 0.45; b0.z = gz(b0.x, b0.y) - 0.1
        tube(f"BanyanFlute{k}", [b0, b0 + d * 0.15 + Vector((0, 0, 1.5)), BANYAN + d * 0.25 + Vector((0, 0, 3.4))], [0.32, 0.22, 0.18], M_BANYANBARK, sides=6)
    for k in range(20):   # aerial roots
        a = R.uniform(0, 2 * math.pi); r = R.uniform(2.0, 8.5)
        p = BANYAN + Vector((math.cos(a) * r, math.sin(a) * r, 0)); top_z = gz(p.x, p.y) + R.uniform(4.0, 6.0)
        prop = R.random() < 0.3
        bot = gz(p.x, p.y) - 0.05 if prop else top_z - R.uniform(1.5, 3.8)
        pts = [Vector((p.x, p.y, top_z)), Vector((p.x + R.gauss(0, 0.08), p.y + R.gauss(0, 0.08), (top_z + bot) / 2)), Vector((p.x + R.gauss(0, 0.12), p.y + R.gauss(0, 0.12), bot))]
        tube(f"BanyanRoot{k}", pts, [0.05, 0.035, 0.02] if not prop else [0.09, 0.08, 0.11], M_BANYANBARK, sides=4 if not prop else 6)
    return C
BANYAN_C = banyan()

# bamboo clumps: tall arching culms with fans of leaves toward their tips
def bamboo_clump(name, x, y, n, h, seed, cards=4):
    R = random.Random(seed); mb = CROWN_MB.setdefault("bamboo", MB())
    for k in range(n):
        a = R.uniform(0, 2 * math.pi); r = R.uniform(0.0, 0.7)
        p0 = Vector((x + math.cos(a) * r, y + math.sin(a) * r, gz(x, y) - 0.1))
        out = Vector((math.cos(a), math.sin(a), 0)) * R.uniform(0.15, 0.45)
        hh = h * R.uniform(0.7, 1.05)
        pts = [p0 + out * (hh * t * t) * 0.6 + Vector((0, 0, hh * t)) for t in (0, 0.25, 0.5, 0.75, 1.0)]
        tube(f"{name}Culm{k}", pts, [0.06, 0.055, 0.045, 0.03, 0.012], M_BAMBOO, sides=4, caps=False)
        for t in np.linspace(0.5, 1.0, cards):
            q = pts[0].lerp(pts[-1], t) + out * (hh * t * t) * 0.0
            q = pts[min(4, int(t * 4))].lerp(pts[min(4, int(t * 4) + 1)], (t * 4) % 1) if t < 1 else pts[-1]
            for c in range(1):
                o2 = (out.normalized() + Vector((R.gauss(0, 0.6), R.gauss(0, 0.6), R.uniform(-0.3, 0.3)))).normalized()
                sz = R.uniform(1.5, 2.2)
                right = o2.cross(Vector((0, 0, 1))).normalized() * sz
                card(mb, q - Vector((0, 0, sz * 0.5)), right, Vector((0, 0, sz)) + o2 * sz * 0.4, R.choice(QUAD), 0.4, 1.0)
for k, (x, y, n, h, sd, nc) in enumerate(((5.5, 6.5, 8, 10.0, 301, 3), (-13.0, 12.0, 9, 11.0, 302, 3), (11.0, 15.5, 7, 9.5, 303, 3), (-6.0, -3.5, 7, 9.0, 304, 3),
                                           (19.0, 36.0, 6, 10.0, 305, 2), (1.0, 40.0, 6, 9.0, 306, 2))):
    bamboo_clump(f"Bamboo{k}", x, y, n, h, sd, cards=nc)

# ----------------------------------------------------------------------------- understorey, grass, litter, logs, rocks
def understorey():
    R = random.Random(5); mbu = MB(); mbg = MB()
    placed = 0
    for i in range(40000):
        r = 14.0 * R.random() ** 1.1; a = R.uniform(0, 2 * math.pi); x, y = r * math.sin(a), r * math.cos(a)
        if r < 1.4: continue
        if path_d(x, y) < 0.9: continue
        if math.hypot(x - ELE.x, y - ELE.y) < 2.6: continue
        if math.hypot(x - PAGODA.x, y - PAGODA.y) < 9: continue
        clr = smoothstep(4.5, 7.5, math.hypot(x + 1.2, y - 4.0))
        dens = 0.18 + 0.82 * clr
        clump = 0.5 + 0.5 * n2(x, y, 0.25, 9.0)
        if R.random() > dens * clump ** 1.4: continue
        z = gz(x, y)
        to_r = Vector((-x, -y, 0)).normalized()
        kind = R.choices(["tallgrass", "fern", "lantana", "herb", "grass", "seedling", "straw", "shoot"], weights=[3, 3, 2.2, 0.8 if r > 4 else 0.0, 4, 1.2, 2, 0.6])[0]
        if r > 9.0 and kind in ("tallgrass", "grass", "straw"): continue          # no grass cards beyond ~8 m
        hgt = {"tallgrass": 1.1, "fern": 0.9, "lantana": 1.4, "herb": 0.7, "grass": 0.45, "seedling": 1.1, "straw": 1.0, "shoot": 1.6}[kind] * R.uniform(0.7, 1.3)
        if r < 2.2: hgt = min(hgt, 0.45)                                          # nothing tall right before the reader
        elif r < 4.5: hgt = min(hgt, 0.85)
        wid = hgt * 0.5
        mbx = mbg if kind in ("tallgrass", "grass", "straw") else mbu
        ncard = 2 if kind in ("fern", "lantana") and 3.0 < r < 6.0 else 1
        for c in range(ncard):
            ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + R.gauss(0, 0.5) + c * 1.3
            right = Vector((math.cos(ya), math.sin(ya), 0)) * wid
            card(mbx, (x, y, z - 0.03), right, Vector((R.gauss(0, 0.06), R.gauss(0, 0.06), hgt)), UNDER[kind], 0.0, 1.0, segs=2 if r < 6 else 1,
                 bend=Vector((R.gauss(0, 0.15), R.gauss(0, 0.15), 0)) * hgt)
        placed += 1
        if placed > 640: break
    o2 = mbg.build("FloorGrass", M_GRASS)
    if o2 is not None: set_card_normals(o2, lambda p: Vector((0, 0, 1)))
    mbu2 = mbu
    # beyond the cards: low opaque thickets of lantana and young growth, scattered more thickly with distance
    placed = 0
    for i in range(4000):
        r = R.uniform(9.5, 36.0); a = R.uniform(0, 2 * math.pi); x, y = r * math.sin(a), r * math.cos(a)
        if path_d(x, y) < 2.2 or math.hypot(x - ELE.x, y - ELE.y) < 3.0 or math.hypot(x - PAGODA.x, y - PAGODA.y) < 9.5: continue
        if R.random() > 0.25 + 0.35 * (0.5 + 0.5 * n2(x, y, 0.12, 4.0)): continue
        w = R.uniform(1.0, 2.0) * (1 + max(0.0, r - 12) / 40); h = R.uniform(0.55, 1.2)
        z = gz(x, y)
        lumps(THICKET, Vector((x, y, z + h * 0.25)), w, h * 0.8, R.randint(3, 4), R, 7000 + i, sub=1, sway=(0.0, 0.35), flat_bottom=z - 0.08)
        # one flowering lantana or fern card on the thicket's near side breaks its outline
        to_r = Vector((-x, -y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + R.gauss(0, 0.3)
        kh = h * R.uniform(1.1, 1.4); kind = R.choice(("lantana", "lantana", "fern", "herb"))
        card(mbu2, (x + to_r.x * w * 0.6, y + to_r.y * w * 0.6, z - 0.05), Vector((math.cos(ya), math.sin(ya), 0)) * kh * 0.9, Vector((0, 0, kh)), UNDER[kind], 0.0, 1.0)
        placed += 1
        if placed >= 62: break
    o1 = mbu.build("Understorey", M_UNDER)
    if o1 is not None: set_card_normals(o1, lambda p: Vector((0, 0, 1)))
understorey()
# a fallen log and dead branches near the reader, rocks half-buried
tube("FallenLog", [Vector((2.4, 2.2, gz(2.4, 2.2) + 0.18)), Vector((4.2, 3.6, gz(4.2, 3.6) + 0.2)), Vector((6.3, 4.4, gz(6.3, 4.4) + 0.16))], [0.24, 0.22, 0.17], M_LOG, sides=10)
for k in range(9):
    R = random.Random(400 + k); x, y = R.uniform(-9, 9), R.uniform(-6, 14)
    if math.hypot(x, y) < 1.8 or path_d(x, y) < 0.8: continue
    a = R.uniform(0, math.pi); L = R.uniform(0.8, 2.2); d = Vector((math.cos(a), math.sin(a), 0))
    p0 = Vector((x, y, gz(x, y) + 0.03)); p1 = p0 + d * L; p1.z = gz(p1.x, p1.y) + 0.03
    tube(f"Branch{k}", [p0, p0.lerp(p1, 0.5) + Vector((0, 0, 0.05)), p1], [0.04, 0.03, 0.015], M_LOG, sides=5)
for k in range(10):
    R = random.Random(500 + k); x, y = R.uniform(-12, 14), R.uniform(-8, 20)
    if math.hypot(x, y) < 2.0 or path_d(x, y) < 1.0 or math.hypot(x - ELE.x, y - ELE.y) < 3: continue
    s = R.uniform(0.25, 0.7)
    K.sphere(f"Rock{k}", s, (x, y, gz(x, y) - s * 0.45), M_ROCK, seg=8, scale=(1.0, R.uniform(0.7, 1.2), R.uniform(0.5, 0.8)))

# ----------------------------------------------------------------------------- the pagoda of Pillaji (a Nagara shrine) with its porch, torches and the pile
def pagoda():
    P = PAGODA; zg = gz(P.x, P.y)
    yaw = math.radians(-70)                      # the porch faces west-south-west, toward the clearing and the sun
    Mf = Matrix.Translation((P.x, P.y, zg)) @ Matrix.Rotation(yaw, 4, 'Z')
    objs = []
    def B(nm, size, loc, mat=M_STONE, bevel=0.02):
        o = box(nm, size, loc, mat, bevel=bevel); objs.append(o); return o
    # the plinth (jagati) in three steps
    for k, (w, h) in enumerate(((10.0, 0.5), (9.0, 0.45), (8.2, 0.4))):
        B(f"Plinth{k}", (w, w, h), (0, 0, sum(hh for _, hh in ((10.0, 0.5), (9.0, 0.45), (8.2, 0.4))[:k]) + h / 2))
    zb = 1.35
    # the sanctum walls with offset projections (rathas) and a moulded base and cornice
    B("SanctumBase", (5.4, 5.4, 0.5), (0, 0, zb + 0.25))
    B("Sanctum", (4.8, 4.8, 3.4), (0, 0, zb + 0.5 + 1.7))
    for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        B(f"Ratha{sx}{sy}", (1.8 if sx == 0 else 0.4, 1.8 if sy == 0 else 0.4, 3.4), (sx * 2.5, sy * 2.5, zb + 0.5 + 1.7))
        B(f"Niche{sx}{sy}", (1.0 if sx == 0 else 0.1, 1.0 if sy == 0 else 0.1, 1.4), (sx * 2.72, sy * 2.72, zb + 2.3), M_LOG)
    B("SanctumCornice", (5.6, 5.6, 0.35), (0, 0, zb + 4.05))
    # the curvilinear tower (shikhara): many thin courses, each a little smaller, the profile bowing inward to the top
    zt = zb + 4.2; N = 12
    for k in range(N):
        t = k / N; w = 5.2 * (1.0 - 0.72 * t ** 1.35); h = 0.69
        B(f"Course{k}", (w, w, h * 0.82), (0, 0, zt + k * h + h * 0.41), bevel=0.0)
        B(f"CourseLip{k}", (w + 0.16, w + 0.16, h * 0.18), (0, 0, zt + k * h + h * 0.91), bevel=0.0)
        for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            B(f"CourseRatha{k}{sx}{sy}", (w * 0.36 if sx == 0 else 0.3, w * 0.36 if sy == 0 else 0.3, h * 0.8), (sx * (w / 2 + 0.1), sy * (w / 2 + 0.1), zt + k * h + h * 0.4), bevel=0.0)
    ztop = zt + N * 0.69
    # the amalaka (ribbed stone disc) and the kalasha (finial pot)
    me = bpy.data.meshes.new("Amalaka"); bm = bmesh.new(); ns = 32; rings = []
    for (rr, zz) in ((0.6, 0.0), (1.05, 0.18), (1.12, 0.32), (1.0, 0.48), (0.55, 0.6)):
        rings.append([bm.verts.new((rr * (1 + 0.06 * math.cos(16 * 2 * math.pi * i / ns)) * math.cos(2 * math.pi * i / ns), rr * (1 + 0.06 * math.cos(16 * 2 * math.pi * i / ns)) * math.sin(2 * math.pi * i / ns), ztop + zz)) for i in range(ns)])
    for a, b_ in zip(rings, rings[1:]):
        for i in range(ns): bm.faces.new((a[i], a[(i + 1) % ns], b_[(i + 1) % ns], b_[i]))
    bm.faces.new(rings[-1]); bm.to_mesh(me); bm.free()
    am = bpy.data.objects.new("Amalaka", me); me.materials.append(M_STONE); link(am); objs.append(am)
    for p in me.polygons: p.use_smooth = True
    kal = lathe("Kalasha", [(0.0, 0.0), (0.25, 0.0), (0.32, 0.18), (0.22, 0.38), (0.1, 0.5), (0.14, 0.6), (0.05, 0.8), (0.0, 0.85)], (0, 0, ztop + 0.6), M_BRASS, steps=12)
    objs.append(kal)
    # the porch (mandapa) on four pillars before the door, with a stepped pyramidal roof
    px = -4.6
    B("PorchFloor", (3.8, 4.2, 0.2), (px, 0, zb - 0.1))
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = cyl(f"PorchPillar{sx}{sy}", 0.18, 2.8, (px + sx * 1.4, sy * 1.6, zb + 1.4), M_STONE, verts=8); objs.append(c)
            B(f"PorchCapital{sx}{sy}", (0.5, 0.5, 0.25), (px + sx * 1.4, sy * 1.6, zb + 2.9))
    for k in range(4):
        w = 4.4 - k * 0.8
        B(f"PorchRoof{k}", (w * 0.95, w + 0.4, 0.32), (px, 0, zb + 3.15 + k * 0.32))
    B("Door", (0.08, 1.2, 2.2), (-2.41, 0, zb + 0.5 + 1.1), M_LOG)
    for k in range(3):
        B(f"Steps{k}", (0.45, 2.4, 0.42), (-5.4 - k * 0.45 - 1.0, 0, 1.35 - 0.21 - k * 0.42))
    for o in objs:
        o.matrix_world = Mf @ o.matrix_world
    # the saffron pennant on a staff from the finial
    fp = Mf @ Vector((0, 0, ztop + 1.4))
    cyl("PennantStaff", 0.03, 2.2, (fp.x, fp.y, fp.z + 0.4), M_LOG, verts=6)
    verts = []; faces = []
    for j in range(3):
        for i in range(8):
            u = i / 7; v = j / 2
            dd = az_dir(80.0) * (u * 1.6)
            verts.append((fp.x + dd.x, fp.y + dd.y + 0.08 * math.sin(u * 6), fp.z + 1.4 - v * 0.55 * (1 - 0.8 * u) - 0.15 * u))
    for j in range(2):
        for i in range(7):
            a = j * 8 + i; faces.append((a, a + 1, a + 9, a + 8))
    flag = mesh_from("Pennant", verts, faces, M_FLAG, smooth=True)
    return Mf, flag, zb
PG_M, PENNANT, PG_ZB = pagoda()
# the torches on poles before the porch, and the stacked wood of the pile
TORCHES = []
for k, (lx, ly) in enumerate(((-8.5, -2.6), (-8.0, 2.4), (-11.5, 0.2))):
    p = PG_M @ Vector((lx, ly, 0)); zg = gz(p.x, p.y)
    cyl(f"TorchPole{k}", 0.035, 2.3, (p.x, p.y, zg + 1.15), M_LOG, verts=6)
    lathe(f"TorchCage{k}", [(0.0, 0.0), (0.05, 0.0), (0.11, 0.14), (0.12, 0.24), (0.0, 0.24)], (p.x, p.y, zg + 2.25), M_IRON, steps=8)
    TORCHES.append(Vector((p.x, p.y, zg + 2.5)))
    fl = sphere(f"RenderOnly_TorchFlame{k}", 0.16, (p.x, p.y, zg + 2.62), M_FLAME, seg=8, scale=(0.8, 0.8, 1.6))
pc = PG_M @ Vector((-10.0, 5.0, 0)); zg = gz(pc.x, pc.y)
for layer in range(6):
    for k in range(5):
        ang = math.radians(-70) + (math.pi / 2 if layer % 2 else 0)
        d = Vector((math.cos(ang), math.sin(ang), 0)); o_ = Vector((-d.y, d.x, 0)) * (k - 2) * 0.32
        c0 = Vector((pc.x, pc.y, zg + 0.14 + layer * 0.24)) + o_
        tube(f"Pyre{layer}_{k}", [c0 - d * 1.1, c0 + d * 1.1], 0.12, M_PYRE, sides=6)

# ----------------------------------------------------------------------------- Kiouni
# Kiouni is not modelled (removed 2026-11-17); the anchors keep the points where he stood (feet) and his head was
EL_PTS = {"feet": (ELE.x, ELE.y, gz(ELE.x, ELE.y) - 0.04), "head": (-1.576, 5.97, 2.251)}

# ----------------------------------------------------------------------------- crowns (built once, one swaying mesh per kind), far tree line, sky
for key, mb in CROWN_MB.items():
    mat = {"sal": M_SAL, "teak": M_TEAKL, "banyan": M_BANYANL, "bamboo": M_BAMBOOL}[key]
    o = mb.build(f"Crowns_{key}", mat)
    cs = [(C, a_, c_) for (k2, C, a_, c_) in CROWNS if k2 == key]
    def nfn(p, cs=cs):
        if not cs: return Vector((0, 0, 1))
        C, a_, c_ = min(cs, key=lambda t: (p - t[0]).length)
        return (((p - C) * Vector((1 / a_, 1 / a_, 1 / c_))) + Vector((0, 0, 0.6))).normalized()
    set_card_normals(o, nfn)
THICKET.build("Thickets", M_THICKET)
def far_treeline():
    """four concentric bands carrying the atlas rows: near canopy at 47 m, middle at 57 m, far at 70 m, the hills at
    125 m; each band's foot is below the ground, the atlas repeats four times round."""
    verts = []; faces = []; luv = []; N = 64
    bands = [(52.0, 7.5, 3), (125.0, 22.0, 0)]     # two of the four bands (overdraw); the ring of far trees stands before them
    for (r0, top_, row) in bands:
        b0 = len(verts)
        for i in range(N + 1):
            a = 2 * math.pi * i / N + row * 0.37; r = r0 + 2.0 * math.sin(a * 3.0 + row)
            x, y = r * math.sin(a), r * math.cos(a)
            verts += [(x, y, top_), (x, y, -1.5)]
        v_lo = (3 - row) / 4.0; v_hi = v_lo + 0.25
        for i in range(N):
            q = b0 + 2 * i; faces.append((q, q + 2, q + 3, q + 1))
            u0 = (i % 16) / 16.0; u1 = u0 + 1 / 16.0
            luv.append([(u0, v_hi - 0.002), (u1, v_hi - 0.002), (u1, v_lo + 0.002), (u0, v_lo + 0.002)])
    me = bpy.data.meshes.new("TreeLine"); me.from_pydata(verts, [], faces); me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for p, uvs in zip(me.polygons, luv):
        for li, uv in zip(p.loop_indices, uvs): uvl.data[li].uv = uv
    o = bpy.data.objects.new("TreeLine", me); me.materials.append(M_TREELINE); link(o)
    orient(o, lambda c: (-c.x, -c.y, 0))
    for p in me.polygons: p.use_smooth = True
    set_card_normals(o, lambda p: Vector((0, 0, 1)))       # even shading all round (no facets lit by the low sun)
    return o
far_treeline()
SKY = E8.sky_dome("SkyDome", M_SKY, SKY_R, seg=40, rings=12, el_min=-6.0)

# ----------------------------------------------------------------------------- lights, world, markers
K.apply_transforms()
light_obj("light.sun", 'SUN', 4.0, (1.0, 0.62, 0.32), tuple(SUN_DIR * 40), direction=-SUN_DIR, angle=math.radians(1.5))
skl = light_obj("light.sky", 'SUN', 0.45, (0.55, 0.64, 0.95), (0, 0, 30), direction=(0.15, -0.1, -1.0), angle=math.radians(80))
skl.data.use_shadow = False
tc = sum(TORCHES, Vector()) / len(TORCHES)
light_obj("Lamp.torchFire", 'POINT', 900.0, (1.0, 0.55, 0.22), tuple(tc + Vector((0, 0, -0.2))), shadow_soft_size=0.5)
world = bpy.data.worlds.new("Dusk"); scene.world = world; world.use_nodes = True
wnt = world.node_tree; bg = wnt.nodes["Background"]
wtc = wnt.nodes.new("ShaderNodeTexCoord"); wsep = wnt.nodes.new("ShaderNodeSeparateXYZ"); wnt.links.new(wtc.outputs["Generated"], wsep.inputs["Vector"])
wmr = wnt.nodes.new("ShaderNodeMapRange"); wmr.inputs["From Min"].default_value = -0.1; wmr.inputs["From Max"].default_value = 1.0
wnt.links.new(wsep.outputs["Z"], wmr.inputs["Value"])
wr = ramp(wnt, [(0.0, (0.10, 0.08, 0.07, 1)), (0.09, (0.60, 0.45, 0.42, 1)), (0.3, (0.28, 0.34, 0.55, 1)), (1.0, (0.12, 0.18, 0.40, 1))])
wnt.links.new(wmr.outputs["Result"], wr.inputs["Fac"]); wnt.links.new(wr.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.6

for k, t in enumerate(TORCHES): E8.fx(f"fx.torch.{k}", tuple(t), 0.12)
sound("birds", "dusk", (-4.0, 16.0, 10.0))
sound("wind-trees", "banyan", tuple(BANYAN + Vector((0, 0, 8.0))))
sound("crowd", "procession", tuple(PG_M @ Vector((-9.0, 0.0, 1.6))))
sound("fire", "torches", tuple(tc))
anchor("reader.entrance", (0.0, 0.0, gz(0, 0)))
anchor("reader.look", (0.0, 1.0, gz(0, 0) + EYE))
anchor("scene.centre", tuple(Vector(EL_PTS["feet"])))
anchor("forest.elephant", tuple(Vector(EL_PTS["head"])))
anchor("forest.pagoda", tuple(PAGODA + Vector((0, 0, 6.0))))
anchor("forest.banyan", tuple(BANYAN))

# sway weights
SWAY_KEYS = {"Thickets": None, "Crowns_sal": None, "Crowns_teak": None, "Crowns_banyan": None, "Crowns_bamboo": None, "Understorey": None, "FloorGrass": None}
add_sway(PENNANT, lambda p: min(1.0, max(0.0, (p - Vector((PENNANT.data.vertices[0].co))).length / 1.6)))
for o in K.COLL.objects:
    if o.type == 'MESH' and o.data.materials and o.data.materials[0].name in ("M_SkyDome", "M_TreeLine", "M_FarLand"):
        o.visible_shadow = False
for o in list(K.COLL.objects):
    if o.name.startswith("RenderOnly_"):
        o.visible_shadow = False

EZ = gz(0, 0) + EYE
page = box("PagePreview", (0.4, 0.004, 0.55), (0.0, 0.6, EZ - 0.05), plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9, emission=(0.80, 0.77, 0.69), strength=0.15))
E = Vector((0.0, 0.0, EZ))
def yawed(deg, dist=8.0, dz=-0.6):
    a = math.radians(deg); return tuple(E + Vector((math.sin(a), math.cos(a), 0)) * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(E), yawed(0, 10, -0.2), lens=17),
    camera("Cam_Page", tuple(E), yawed(0, 10, -0.2), lens=17),
    camera("Cam_Left", tuple(E), yawed(-70, 10, 0.0), lens=17),
    camera("Cam_Right", tuple(E), yawed(70, 10, 0.0), lens=17),
    camera("Cam_Behind", tuple(E), yawed(180, 10, 0.0), lens=17),
    camera("Cam_Down", tuple(E), (0.6, 1.6, gz(0.6, 1.6)), lens=17),
    camera("Cam_Up", tuple(E), (2.0, 8.0, 18.0), lens=17),
    camera("Cam_Pagoda", tuple(E), tuple(PAGODA + Vector((0, 0, 6.0))), lens=40),
]
for c in cams: c.data.clip_end = 400
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "pillaji_forest_source.blend"))
K.print_budget(exclude=("PagePreview",) + tuple(o.name for o in K.COLL.objects if o.name.startswith("RenderOnly_")))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=1.3, captures_dir=ARGS.captures)

if ARGS.bake or ARGS.export:
    for o in [o for o in K.COLL.objects if o.name.startswith("RenderOnly_")]:
        bpy.data.objects.remove(o)
    E8.bake_and_export(
        "pillaji_forest.gltf", cams, page=page,
        keep_names={"M_SalLeaves": "veg.crown.sal", "M_TeakLeaves": "veg.crown.teak", "M_BanyanLeaves": "veg.crown.banyan", "M_BambooLeaves": "veg.leaves.bamboo",
                    "M_Understorey": "veg.shrub.under", "M_FloorGrass": "veg.grass.floor", "M_Pennant": "cloth.flag.pennant",
                    "M_Thicket": "veg.shrub.thicket",
                    "M_SkyDome": "SkyDome", "M_FarLand": "far.Land", "M_TreeLine": "far.TreeLine", "M_ForestFloor": "GroundNear"},
        keep_uv={"M_ForestFloor", "M_SkyDome"},
        size_for={"M_ForestFloor": (2048, 512, 2048), "M_SkyDome": (2048,), "M_FarLand": (256, 32, 64), "M_SalBark": (1024, 128, 512),
                  "M_TeakBark": (512, 128, 256), "M_BanyanBark": (1024, 128, 512), "M_BambooCulm": (256, 64, 128), "M_TempleStone": (2048, 256, 1024),
                  "M_Thicket": (512, 128, 256),
                  "M_DeadWood": (512, 128, 256), "M_PyreWood": (256, 64, 128), "M_Rock": (256, 64, 128), "M_TorchIron": (32, 32), "M_Pennant": (64, 32),
                  "M_Brass": (64, 32)},
        default_size=(256, 64, 128))
print("DONE")
