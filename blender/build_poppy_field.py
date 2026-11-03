"""
Fable: the poppy field by the river (The Wonderful Wizard of Oz, chapter VIII, "The Deadly Poppy Field").

"They walked along listening to the singing of the brightly colored birds and looking at the lovely flowers which now
became so thick that the ground was carpeted with them. There were big yellow and white and blue and purple blossoms,
besides great clusters of scarlet poppies, which were so brilliant in color they almost dazzled Dorothy's eyes."
"They now came upon more and more of the big scarlet poppies, and fewer and fewer of the other flowers; and soon they
found themselves in the midst of a great meadow of poppies." ... "They followed the bend of the river ..."

The reader stands on the grassy top of the river bank, at the edge where the great meadow of poppies begins. The broad
river runs on the right, below a short earth bank with reeds at the water; fruit trees stand along the near bank and
alders and willows on the far one. The poppies spread away on the left and ahead-left to the horizon; straight ahead
(behind the reading page) the land is the calm sweet grass beyond the end of the poppy bed, with only a few flowers,
and far off on the horizon, ahead-left, a faint green glow where the Emerald City lies. Behind the reader, the way
the travellers came, the meadow is carpeted with yellow, white, blue and purple flowers among clusters of poppies.
Late afternoon, clear sky with a few fair-weather clouds, the sun low in the west (on the reader's left).
No characters (Dorothy, Toto, the Lion, the Scarecrow, the Tin Woodman, the Stork, the mice are left out).

Builds the place procedurally (no downloaded models, textures or HDRIs) with PBR node materials, a low sun and a cool
sky fill, then (by flag) renders Cycles stills, bakes materials to textures, merges static meshes by material and
exports a .gltf + .bin + textures/ for Unity. Modelled on build_kansas_farmhouse.py and build_queens_croquet_ground.py.

Budget technique: everything near the reader is geometry, everything far is texture. Poppies come in three levels of
detail by distance from the reading position (full four-petal flowers with buds, seed heads and lobed leaves within
~4.5 m, simple four-petal cups to ~10 m, three-triangle cups to ~22 m); beyond that the ground texture carries the
flowers as baked speckle driven by the same density map. Flower petals, grass, stems and meadow flowers use small
"palette" textures addressed by hand-made UVs (one column per variant, v from base to tip), so thousands of tiny
cards share a 512 px texture. The near ground uses a log-polar UV layout: texel density is highest at the reader's feet
and falls off with distance, so the single 4K ground texture is spent where it is seen from close by.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet on the bank top (ground, z=0), facing +Y (north, down the river)
  anchor.reader.look      eye height (1.55 m) one metre ahead of the entrance along the reading direction
  anchor.scene.centre     the ground at the edge of the poppy meadow, ahead-left of the reader
  anchor.poppies.field, anchor.river.bank  (extra place anchors)
  light.sun (SUN, low late-afternoon sun from the west), light.sky (SUN, cool fill, no shadow)
  SkyDome (unlit backdrop, baked base texture), far.meadow (ground beyond 40 m), far.treeline (distant trees):
  backdrop, no shadows, not lightmapped (FlowController.IsBackdrop).

Axes: metres, Blender +Z up. Reader at the origin facing +Y. The river runs north on the reader's right (+X), its
near water edge 5 m away, its surface at z = -1.15; the poppy meadow lies to the west (-X) and north-west.

Run headless:
  blender -b -P blender/build_poppy_field.py -- --out out/poppy-field --render --quick --res 900
  blender -b -P blender/build_poppy_field.py -- --out out/poppy-field --render --quick --res 900 --cams reader,left
  blender -b -P blender/build_poppy_field.py -- --out out/poppy-field --bake --export --tex 2048
  blender -b -P blender/build_poppy_field.py -- --out captures/blender/poppy-field --render --res 1400 --samples 64
"""
import bpy, bmesh, math, random, sys, os, argparse
import numpy as np
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/poppy-field")
ap.add_argument("--render", action="store_true")
ap.add_argument("--bake", action="store_true")
ap.add_argument("--export", action="store_true")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", type=int, default=1400)
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--quick", action="store_true", help="low samples for iteration")
ap.add_argument("--cams", default="", help="comma list of camera names to render (default all)")
ap.add_argument("--prefix", default="render_", help="file name prefix for rendered stills")
args = ap.parse_args(argv)
OUT = os.path.abspath(args.out)
os.makedirs(OUT, exist_ok=True)
random.seed(1900)

# ----------------------------------------------------------------------------- dimensions (metres)
EYE = 1.55                       # reader eye height above the entrance
WATER_Z = -1.15                  # river surface (the bank top where the reader stands is z ~ 0)
RW = 6.0                         # river half width at the waterline
NEAR_R = 40.0                    # near ground (4K, log-polar UVs) out to here; far.meadow beyond
TERRAIN_R = 108.0                # the land ends under the sky dome (Unity's far clip is 150 m)
SKY_R = 115.0
SUN_DIR = Vector((-0.80, -0.30, 0.45)).normalized()     # towards the sun: low in the west, a little south (afternoon)
EMERALD_DIR = Vector((-0.55, 0.83, 0.0)).normalized()  # the far green glow, ahead-left on the horizon
LOOK_DIR = Vector((0.0, 1.0, 0.0))

# ----------------------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16 if args.quick else args.samples
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.transmission_bounces = 4
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'; prefs.get_devices()
    for d in prefs.devices: d.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print("Metal not available, CPU render:", e)
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 0.0

COLL = bpy.data.collections.new("PoppyField")
scene.collection.children.link(COLL)
def link(obj):
    COLL.objects.link(obj); return obj

# ----------------------------------------------------------------------------- small maths
def smoothstep(e0, e1, x):
    if e1 == e0: return 1.0 if x >= e1 else 0.0
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)

def n2(x, y, s, off=0.0):
    """Perlin noise in [-1, 1] at feature size s (metres)."""
    return noise.noise(Vector((x / s + off * 7.13, y / s - off * 3.71, off * 1.37 + 0.31)))


# ----------------------------------------------------------------------------- the land: meadow, river, bank, far hills
def river_x(y):
    """Centre line of the river: it bends away east ahead (the bend the travellers followed) and west behind."""
    return 11.0 + (0.0032 * y * y if y > 0 else -0.0018 * y * y)

def bank_w(y):
    return min(3.2, max(1.3, 2.1 + 0.9 * n2(0.0, y, 9.0, 2.1)))

def meadow(x, y):
    return 0.30 * n2(x, y, 24.0, 0.3) + 0.09 * n2(x, y, 7.0, 1.7) + 0.025 * n2(x, y, 1.8, 4.1)
MEADOW0 = meadow(0.0, 0.0)

def rw(y, side=-1):
    """Half width at the waterline: small bays and points along each bank."""
    o = 0.0 if side < 0 else 40.0
    return RW + 0.45 * n2(0.0, y + o, 2.6, 7.7) + 0.22 * n2(0.0, y + o, 0.9, 1.2)

def river_e(x, y):
    """Signed distance (m, across the river) from the nearest waterline: > 0 on land, < 0 in the water; and the side."""
    d = x - river_x(y)
    side = 1 if d > 0 else -1
    return abs(d) - rw(y, side), side

def H(x, y):
    r = math.hypot(x, y)
    m = meadow(x, y) - MEADOW0
    m += 0.010 * max(0.0, -x)                                     # the land rises gently away from the river
    e, side = river_e(x, y)
    if side > 0: m += 0.25 * smoothstep(0.0, 6.0, e)
    a = math.atan2(y, x)
    hills = smoothstep(52.0, 106.0, r) ** 1.4 * (3.2 + 2.6 * noise.noise(Vector((math.cos(a) * 2.2, math.sin(a) * 2.2, 5.5))))
    m += hills * smoothstep(8.0, 40.0, e)                         # the valley floor stays open along the river
    bw = bank_w(y) if side < 0 else bank_w(y + 40.0) * 1.3
    if e >= bw: return m
    if e >= 0.0:
        return WATER_Z + 0.07 + 0.10 * smoothstep(0.0, 0.7, e) + (m - WATER_Z - 0.17) * smoothstep(0.5, bw, e) ** 0.7
    return WATER_Z + 0.07 - 1.0 * smoothstep(0.0, 3.0, -e)

# ----------------------------------------------------------------------------- where the flowers grow
BOUND = [(-110, -30), (-40, -10), (-15, -3.6), (0, -1.6), (6, -2.2), (14, -4.7), (26, -9.6), (45, -18), (110, -60)]
def bound_x(y):
    """x of the poppy meadow's eastern edge at y (the meadow lies west of it)."""
    if y <= BOUND[0][0]: bx = BOUND[0][1]
    elif y >= BOUND[-1][0]: bx = BOUND[-1][1]
    else:
        for (y0, x0), (y1, x1) in zip(BOUND, BOUND[1:]):
            if y0 <= y <= y1:
                t = (y - y0) / (y1 - y0); t = t * t * (3 - 2 * t); bx = x0 + (x1 - x0) * t; break
    return bx + 1.1 * n2(0.0, y, 7.0, 6.2)

def field_s(x, y): return bound_x(y) - x

def P(x, y):
    """Poppy density 0..1: the great meadow of poppies to the west, clusters in the mixed meadow behind, a few strays."""
    s = field_s(x, y)
    core = smoothstep(-0.8, 5.0, s + 1.8 * n2(x, y, 5.0, 3.1))
    patch = 0.62 + 0.38 * n2(x, y, 2.4, 5.5)                    # thick and thin places within the field
    end = 1.0 - smoothstep(60.0, 92.0, y - 0.25 * x)            # far ahead the poppy bed ends in sweet grass
    v = core * patch * end
    if y < 1.0:                                                  # great clusters of scarlet poppies among the other flowers
        v += 0.75 * smoothstep(0.30, 0.62, n2(x, y, 3.2, 8.8)) * (1.0 - smoothstep(-2.0, 1.0, y))
    v += 0.03                                                    # strays everywhere
    e, side = river_e(x, y)
    v *= smoothstep(0.4, 1.6, e) * (0.35 if side > 0 else 1.0)
    return max(0.0, min(1.0, v))

def B(x, y):
    """Other meadow flowers (yellow, white, blue, purple): a carpet behind the reader, thin ahead, few in the poppies."""
    behind = 1.0 - smoothstep(-7.0, 5.0, y)
    v = (0.12 + 0.78 * behind) * (0.55 + 0.45 * n2(x, y, 4.0, 2.2))
    v *= 1.0 - 0.85 * smoothstep(0.0, 4.0, field_s(x, y))
    e, side = river_e(x, y)
    v *= smoothstep(0.6, 2.2, e) * (0.5 if side > 0 else 1.0)
    return max(0.0, min(1.0, v))

# ----------------------------------------------------------------------------- material helpers (from build_kansas_farmhouse.py)
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, bsdf

def node(nt, kind, loc=(0, 0), **props):
    n = nt.nodes.new(kind); n.location = loc
    for k, v in props.items(): setattr(n, k, v)
    return n

def ramp(nt, stops, loc=(0, 0), interp=None):
    r = nt.nodes.new("ShaderNodeValToRGB"); r.location = loc
    cr = r.color_ramp
    if interp: cr.interpolation = interp
    while len(cr.elements) > 1: cr.elements.remove(cr.elements[-1])
    cr.elements[0].position, cr.elements[0].color = stops[0]
    for pos, col in stops[1:]:
        e = cr.elements.new(pos); e.color = col
    return r

def math_(nt, op, a, b=None, loc=(0, 0), c=None):
    n = node(nt, "ShaderNodeMath", loc, operation=op)
    for i, v in enumerate((a, b, c)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]

def mix_rgb(nt, blend, fac, a, b, loc=(0, 0)):
    n = node(nt, "ShaderNodeMix", loc, data_type='RGBA', blend_type=blend)
    for sock, v in ((n.inputs["Factor"], fac), (n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, (int, float)): sock.default_value = v
        elif isinstance(v, tuple): sock.default_value = v
        else: nt.links.new(v, sock)
    return n.outputs[2]

def mix_f(nt, fac, a, b, loc=(0, 0)):
    n = node(nt, "ShaderNodeMix", loc, data_type='FLOAT')
    for sock, v in ((n.inputs["Factor"], fac), (n.inputs[2], a), (n.inputs[3], b)):
        if isinstance(v, (int, float)): sock.default_value = v
        else: nt.links.new(v, sock)
    return n.outputs[0]

def maprange(nt, v, f0, f1, t0=0.0, t1=1.0, loc=(0, 0), interp='LINEAR'):
    n = node(nt, "ShaderNodeMapRange", loc, interpolation_type=interp)
    n.inputs["From Min"].default_value = f0; n.inputs["From Max"].default_value = f1
    n.inputs["To Min"].default_value = t0; n.inputs["To Max"].default_value = t1
    nt.links.new(v, n.inputs["Value"])
    return n.outputs["Result"]

def noise_tex(nt, vec, scale, detail=4.0, rough=0.55, distortion=0.0, loc=(0, 0)):
    n = node(nt, "ShaderNodeTexNoise", loc)
    n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough; n.inputs["Distortion"].default_value = distortion
    if vec is not None: nt.links.new(vec, n.inputs["Vector"])
    return n

def voronoi(nt, vec, scale, feature='F1', loc=(0, 0), rand=1.0):
    n = node(nt, "ShaderNodeTexVoronoi", loc, feature=feature)
    n.inputs["Scale"].default_value = scale; n.inputs["Randomness"].default_value = rand
    if vec is not None: nt.links.new(vec, n.inputs["Vector"])
    return n

def bump_from(nt, b, height_socket, strength, distance, loc=(50, -300)):
    bump = node(nt, "ShaderNodeBump", loc); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return bump

def c4(c): return (c[0], c[1], c[2], 1.0)

def obj_coords(nt, loc=(-1800, 0)):
    tc = node(nt, "ShaderNodeTexCoord", loc)
    return tc, tc.outputs["Object"]

def image_lookup(nt, img, vec_obj, extent, loc=(0, 0)):
    """Sample a generated map image covering [-extent, extent]^2 in x, y."""
    mp = node(nt, "ShaderNodeMapping", (loc[0] - 200, loc[1]))
    mp.inputs["Scale"].default_value = (0.5 / extent, 0.5 / extent, 1.0); mp.inputs["Location"].default_value = (0.5, 0.5, 0.0)
    nt.links.new(vec_obj, mp.inputs["Vector"])
    t = node(nt, "ShaderNodeTexImage", loc, interpolation='Cubic', extension='EXTEND'); t.image = img
    nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
    return t

# ----------------------------------------------------------------------------- palette materials (function of UV only: u = variant column, v = base..tip)
def palette_uv(nt, ncols, loc=(-1600, 0)):
    tc = node(nt, "ShaderNodeTexCoord", loc); sep = node(nt, "ShaderNodeSeparateXYZ", (loc[0] + 200, loc[1]))
    nt.links.new(tc.outputs["UV"], sep.inputs["Vector"])
    uu = math_(nt, 'MULTIPLY', sep.outputs["X"], float(ncols), (loc[0] + 400, loc[1] + 100))
    col = math_(nt, 'FLOOR', uu, None, (loc[0] + 550, loc[1] + 150))
    s = math_(nt, 'FRACT', uu, None, (loc[0] + 550, loc[1] + 50))
    colf = math_(nt, 'DIVIDE', math_(nt, 'ADD', col, 0.5, (loc[0] + 700, loc[1] + 150)), float(ncols), (loc[0] + 850, loc[1] + 150))
    return colf, s, sep.outputs["Y"]

def col_ramp(nt, colf, colors, loc):
    """CONSTANT ramp: one colour per column (colf = (col + 0.5) / ncols)."""
    n = len(colors)
    return ramp(nt, [(i / n, c4(c)) for i, c in enumerate(colors)], loc, interp='CONSTANT')

def petal_mat(name="M_PoppyPetal"):
    """Field poppy petals: scarlet silk, darker at the base, a black blotch on some, the stamen ring black, fine
    radiating veins, the edge a shade lighter where it is thinnest. Columns: six petal variants (bright scarlet,
    blotched, crimson, orange-scarlet, faded/old, blotched bright)."""
    m, nt, b = new_mat(name)
    colf, s, v = palette_uv(nt, 6)
    base = col_ramp(nt, colf, [(0.64, 0.020, 0.008), (0.58, 0.018, 0.008), (0.44, 0.013, 0.010), (0.68, 0.050, 0.007),
                               (0.52, 0.065, 0.045), (0.64, 0.024, 0.009)], (-800, 300))
    blot = col_ramp(nt, colf, [(0, 0, 0), (1, 1, 1), (0, 0, 0), (0, 0, 0), (0.3, 0.3, 0.3), (0.8, 0.8, 0.8)], (-800, 0))
    # radial: dark stamen ring at the very base, blotch to ~0.24, then a deepening towards the base
    bl = maprange(nt, v, 0.16, 0.27, 1.0, 0.0, (-800, -250), 'SMOOTHSTEP')
    blm = math_(nt, 'MULTIPLY', bl, blot.outputs["Color"], (-600, -100))
    ring = maprange(nt, v, 0.09, 0.15, 1.0, 0.0, (-800, -450), 'SMOOTHSTEP')
    dark = math_(nt, 'MAXIMUM', blm, ring, (-450, -200))
    shade = maprange(nt, v, 0.05, 0.55, 0.62, 1.0, (-800, -650), 'SMOOTHSTEP')
    col = mix_rgb(nt, 'MULTIPLY', 1.0, base.outputs["Color"], shade, (-400, 300))
    # veins: thin lines fanning along v, wobbling
    nz = noise_tex(nt, None, 6.0, 3.0, loc=(-1000, -900))
    tc2 = node(nt, "ShaderNodeTexCoord", (-1300, -900)); nt.links.new(tc2.outputs["UV"], nz.inputs["Vector"])
    vein = math_(nt, 'SINE', math_(nt, 'ADD', math_(nt, 'MULTIPLY', s, 46.0, (-800, -850)), math_(nt, 'MULTIPLY', nz.outputs["Fac"], 3.0, (-800, -950)), (-650, -900)), None, (-500, -900))
    veinf = maprange(nt, vein, -1.0, 1.0, 0.86, 1.0, (-350, -900))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, veinf, (-200, 300))
    edge = maprange(nt, v, 0.82, 1.0, 1.0, 1.18, (-350, -1100))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, edge, (-50, 300))
    col = mix_rgb(nt, 'MIX', dark, col, (0.012, 0.008, 0.010, 1), (100, 300))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.52
    b.inputs["Subsurface Weight"].default_value = 0.0
    return m

NH = 10    # herbage columns
H_GRASS, H_GRASS_BLUE, H_GRASS_YEL, H_STRAW, H_POPPY, H_BUD, H_REED, H_SEED, H_BROAD, H_CLOVER = range(NH)
def herbage_mat(name="M_Herbage"):
    """Grass blades, poppy stems and leaves, buds and seed heads, reeds, plantain and clover: one palette.
    v runs from the base (in the shade of the sward) to the tip (sun-bleached, sometimes dry)."""
    m, nt, b = new_mat(name)
    colf, s, v = palette_uv(nt, NH)
    root = col_ramp(nt, colf, [(0.022, 0.040, 0.012), (0.020, 0.040, 0.020), (0.030, 0.046, 0.012), (0.10, 0.085, 0.045), (0.026, 0.045, 0.016),
                               (0.050, 0.075, 0.040), (0.040, 0.050, 0.018), (0.090, 0.080, 0.050), (0.018, 0.038, 0.012), (0.018, 0.040, 0.016)], (-800, 500))
    mid = col_ramp(nt, colf, [(0.060, 0.120, 0.022), (0.050, 0.105, 0.048), (0.090, 0.135, 0.025), (0.24, 0.20, 0.10), (0.055, 0.092, 0.036),
                              (0.105, 0.150, 0.085), (0.080, 0.105, 0.035), (0.20, 0.16, 0.13), (0.045, 0.095, 0.022), (0.045, 0.100, 0.035)], (-800, 250))
    tip = col_ramp(nt, colf, [(0.110, 0.165, 0.035), (0.090, 0.140, 0.070), (0.26, 0.24, 0.085), (0.38, 0.33, 0.19), (0.075, 0.115, 0.048),
                              (0.120, 0.160, 0.100), (0.20, 0.19, 0.08), (0.30, 0.22, 0.20), (0.075, 0.130, 0.035), (0.075, 0.140, 0.060)], (-800, 0))
    t1 = maprange(nt, v, 0.0, 0.45, 0.0, 1.0, (-600, 400), 'SMOOTHSTEP')
    t2 = maprange(nt, v, 0.45, 1.0, 0.0, 1.0, (-600, 100), 'SMOOTHSTEP')
    col = mix_rgb(nt, 'MIX', t1, root.outputs["Color"], mid.outputs["Color"], (-400, 400))
    col = mix_rgb(nt, 'MIX', t2, col, tip.outputs["Color"], (-250, 300))
    # a midrib / vein line down the centre of each card, and fine streaks along it
    mr = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', s, 0.5, (-800, -300)), None, (-650, -300))
    rib = maprange(nt, mr, 0.0, 0.08, 1.12, 1.0, (-500, -300))
    tcs = node(nt, "ShaderNodeTexCoord", (-1100, -600)); mpp = node(nt, "ShaderNodeMapping", (-900, -600)); mpp.inputs["Scale"].default_value = (90.0, 4.0, 1.0)
    nt.links.new(tcs.outputs["UV"], mpp.inputs["Vector"])
    st = noise_tex(nt, mpp.outputs["Vector"], 1.0, 3.0, loc=(-700, -600))
    stf = maprange(nt, st.outputs["Fac"], 0.3, 0.7, 0.85, 1.08, (-500, -600))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, rib, (-100, 300))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, stf, (50, 300))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.72
    b.inputs["Subsurface Weight"].default_value = 0.0
    return m

NM = 8     # meadow flower columns
F_YELLOW, F_WHITE, F_DISC, F_BLUE, F_PURPLE, F_LOOSE, F_PLUM, F_PEACH = range(NM)
def flowers_mat(name="M_MeadowFlowers"):
    """The big yellow and white and blue and purple blossoms (buttercup, ox-eye daisy, its disc, cornflower,
    knapweed, purple loosestrife at the water), and the plums and peaches on the bank trees."""
    m, nt, b = new_mat(name)
    colf, s, v = palette_uv(nt, NM)
    base = col_ramp(nt, colf, [(0.78, 0.52, 0.02), (0.78, 0.77, 0.70), (0.70, 0.36, 0.02), (0.10, 0.20, 0.72), (0.34, 0.10, 0.38),
                               (0.46, 0.10, 0.36), (0.20, 0.04, 0.12), (0.80, 0.34, 0.10)], (-800, 300))
    inner = col_ramp(nt, colf, [(0.55, 0.30, 0.01), (0.60, 0.60, 0.40), (0.40, 0.18, 0.01), (0.05, 0.08, 0.40), (0.18, 0.05, 0.20),
                                (0.30, 0.06, 0.24), (0.10, 0.02, 0.07), (0.60, 0.15, 0.06)], (-800, 0))
    t = maprange(nt, v, 0.0, 0.45, 0.0, 1.0, (-600, 0), 'SMOOTHSTEP')
    col = mix_rgb(nt, 'MIX', t, inner.outputs["Color"], base.outputs["Color"], (-400, 200))
    rough = col_ramp(nt, colf, [(0.28, 0.28, 0.28), (0.60, 0.6, 0.6), (0.75, 0.75, 0.75), (0.55, 0.55, 0.55), (0.6, 0.6, 0.6),
                                (0.6, 0.6, 0.6), (0.35, 0.35, 0.35), (0.55, 0.55, 0.55)], (-800, -300))
    nt.links.new(col, b.inputs["Base Color"]); nt.links.new(rough.outputs["Color"], b.inputs["Roughness"])
    return m

# ----------------------------------------------------------------------------- object-space materials
def ground_mat(dens_img, contact_img, name="M_Ground"):
    """The meadow floor seen from a standing height: a dense green sward with dry and lush patches, clover, the grey
    rosettes of poppy foliage in the field, the flowers as speckle (they lift above the grass, so their density
    rises with distance from the reader), soil on the steep bank, wet mud and pebbles at the water, darkening under
    every tuft and plant (contact), all at the scale it is seen from."""
    m, nt, b = new_mat(name)
    tc, ob = obj_coords(nt)
    geo = node(nt, "ShaderNodeNewGeometry", (-1800, -1600))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1600, 300)); nt.links.new(ob, sep.inputs["Vector"])
    dens = image_lookup(nt, dens_img, ob, NEAR_R, (-1300, 1400))
    dsep = node(nt, "ShaderNodeSeparateColor", (-1100, 1400)); nt.links.new(dens.outputs["Color"], dsep.inputs["Color"])
    Pd, Bd = dsep.outputs["Red"], dsep.outputs["Blue"]
    cont = image_lookup(nt, contact_img, ob, NEAR_R, (-1300, 1100))
    csep = node(nt, "ShaderNodeSeparateColor", (-1100, 1100)); nt.links.new(cont.outputs["Color"], csep.inputs["Color"])
    vl = node(nt, "ShaderNodeVectorMath", (-1500, 900), operation='LENGTH'); nt.links.new(ob, vl.inputs[0])
    dist = vl.outputs["Value"]
    # --- sward
    big = noise_tex(nt, ob, 0.09, 4, loc=(-1300, 600)); midn = noise_tex(nt, ob, 0.6, 6, loc=(-1300, 400))
    fine = noise_tex(nt, ob, 9.0, 4, 0.6, loc=(-1300, 200))
    blades = voronoi(nt, ob, 70.0, loc=(-1300, 0))
    sw = mix_f(nt, 0.45, big.outputs["Fac"], midn.outputs["Fac"], (-1100, 500))
    sward = ramp(nt, [(0.28, (0.026, 0.054, 0.010, 1)), (0.42, (0.048, 0.094, 0.015, 1)), (0.55, (0.080, 0.128, 0.022, 1)),
                      (0.66, (0.122, 0.152, 0.032, 1)), (0.77, (0.175, 0.158, 0.060, 1))], (-900, 500))
    nt.links.new(sw, sward.inputs["Fac"])
    bl = maprange(nt, blades.outputs["Distance"], 0.0, 0.5, 1.25, 0.8, (-1100, 0))
    fn = maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0.75, 1.15, (-1100, 200))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, sward.outputs["Color"], bl, (-700, 400))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, fn, (-600, 400))
    # fibres: short grass leaves and straw seen from above, crossing in two directions
    fibres = []
    for k, (dirn, sc_) in enumerate((('X', 55.0), ('Y', 47.0))):
        wv = node(nt, "ShaderNodeTexWave", (-1300, 1900 + k * 250), wave_type='BANDS', bands_direction=dirn)
        wv.inputs["Scale"].default_value = sc_; wv.inputs["Distortion"].default_value = 22.0
        wv.inputs["Detail"].default_value = 6.0; wv.inputs["Detail Scale"].default_value = 2.5
        nt.links.new(ob, wv.inputs["Vector"]); fibres.append(wv.outputs["Fac"])
    fib = math_(nt, 'MAXIMUM', fibres[0], fibres[1], (-1100, 2000))
    fibv = maprange(nt, fib, 0.2, 1.0, 0.72, 1.18, (-950, 2000))
    fibv = mix_f(nt, maprange(nt, dist, 2.0, 14.0, 1.0, 0.3, (-950, 2150)), 1.0, fibv, (-800, 2050))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, fibv, (-560, 420))
    tus = voronoi(nt, ob, 3.2, loc=(-1300, 1000))
    tusv = maprange(nt, tus.outputs["Distance"], 0.0, 0.75, 1.22, 0.62, (-1100, 1000))
    col = mix_rgb(nt, 'MULTIPLY', 0.85, col, tusv, (-640, 420))
    sh = noise_tex(nt, ob, 0.5, 4, loc=(-1300, 1250))
    shm = maprange(nt, sh.outputs["Fac"], 0.55, 0.70, 0.0, 0.45, (-1100, 1250))
    shm = math_(nt, 'MULTIPLY', shm, maprange(nt, dist, 4.0, 14.0, 0.0, 1.0, (-1100, 1350)), (-950, 1300))
    shm = math_(nt, 'MULTIPLY', shm, math_(nt, 'SUBTRACT', 1.0, Pd, (-1000, 1400)), (-850, 1300))
    col = mix_rgb(nt, 'MIX', shm, col, (0.21, 0.17, 0.12, 1), (-620, 440))
    # close to the reader the eye looks down into the sward (darker, litter); further off it sees the blade tops
    depth_k = maprange(nt, dist, 1.0, 10.0, 0.62, 1.05, (-900, 700))
    litter = noise_tex(nt, ob, 14.0, 3, 0.6, 2.0, loc=(-1300, 750))
    lit_m = maprange(nt, litter.outputs["Fac"], 0.58, 0.66, 0.0, 0.5, (-1100, 750))
    lit_m = math_(nt, 'MULTIPLY', lit_m, maprange(nt, dist, 2.0, 8.0, 1.0, 0.2, (-1100, 850)), (-950, 800))
    col = mix_rgb(nt, 'MIX', lit_m, col, (0.16, 0.13, 0.07, 1), (-550, 450))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, depth_k, (-500, 450))
    # clover drifts: bluer, darker, with tiny white heads
    clov = noise_tex(nt, ob, 0.35, 3, loc=(-1300, -200))
    clm = maprange(nt, clov.outputs["Fac"], 0.60, 0.68, 0.0, 1.0, (-1100, -200))
    clm = math_(nt, 'MULTIPLY', clm, math_(nt, 'SUBTRACT', 1.0, Pd, (-1000, -300)), (-900, -250))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', clm, 0.7, (-800, -200)), col, (0.040, 0.085, 0.040, 1), (-500, 300))
    # poppy foliage rosettes in the field: grey-green lobed leaves at ground level
    pf = voronoi(nt, ob, 6.0, loc=(-1300, -450))
    pfm = maprange(nt, pf.outputs["Distance"], 0.15, 0.45, 1.0, 0.0, (-1100, -450))
    pfm = math_(nt, 'MULTIPLY', pfm, maprange(nt, Pd, 0.1, 0.7, 0.0, 0.85, (-1100, -550)), (-900, -450))
    col = mix_rgb(nt, 'MIX', pfm, col, (0.075, 0.105, 0.060, 1), (-400, 250))
    # --- flowers as speckle: density rises with distance (heads lift above the sward and hide it)
    far_k = maprange(nt, dist, 3.0, 26.0, 0.40, 1.30, (-1300, 1650))
    pk = math_(nt, 'MULTIPLY', Pd, far_k, (-1100, 1650))
    def speckle(scale, thresh_mul, rad0, rad1, colA, colB, dens_sock, loc):
        v_ = voronoi(nt, ob, scale, loc=loc)
        cs = node(nt, "ShaderNodeSeparateColor", (loc[0] + 200, loc[1])); nt.links.new(v_.outputs["Color"], cs.inputs["Color"])
        exists = math_(nt, 'LESS_THAN', cs.outputs["Red"], math_(nt, 'MULTIPLY', dens_sock, thresh_mul, (loc[0] + 200, loc[1] - 120)), (loc[0] + 350, loc[1]))
        rad = math_(nt, 'MULTIPLY_ADD', cs.outputs["Green"], rad1 - rad0, (loc[0] + 350, loc[1] - 120), c=rad0)
        disc = math_(nt, 'LESS_THAN', v_.outputs["Distance"], rad, (loc[0] + 500, loc[1] - 60))
        soft = maprange(nt, math_(nt, 'SUBTRACT', rad, v_.outputs["Distance"], (loc[0] + 500, loc[1] - 160)), 0.0, 0.05, 0.0, 1.0, (loc[0] + 650, loc[1] - 160))
        mask = math_(nt, 'MULTIPLY', exists, soft, (loc[0] + 650, loc[1]))
        cc = mix_rgb(nt, 'MIX', cs.outputs["Blue"], colA, colB, (loc[0] + 650, loc[1] + 150))
        return mask, cc
    pm1, pc1 = speckle(11.0, 0.80, 0.19, 0.36, (0.56, 0.018, 0.008, 1), (0.42, 0.013, 0.009, 1), pk, (-1300, 2000))
    pm2, pc2 = speckle(19.0, 0.50, 0.15, 0.28, (0.60, 0.035, 0.008, 1), (0.48, 0.022, 0.010, 1), pk, (-1300, 2400))
    # fallen petals: few, darker, scattered under the poppies
    pm3, pc3 = speckle(31.0, 0.18, 0.10, 0.22, (0.36, 0.030, 0.020, 1), (0.25, 0.040, 0.025, 1), Pd, (-1300, 2800))
    bk = math_(nt, 'MULTIPLY', Bd, far_k, (-1100, 1800))
    mv = voronoi(nt, ob, 15.0, loc=(-1300, 3200))
    ms = node(nt, "ShaderNodeSeparateColor", (-1100, 3200)); nt.links.new(mv.outputs["Color"], ms.inputs["Color"])
    mex = math_(nt, 'LESS_THAN', ms.outputs["Red"], math_(nt, 'MULTIPLY', bk, 0.95, (-1000, 3100)), (-900, 3200))
    mdisc = maprange(nt, mv.outputs["Distance"], 0.15, 0.23, 1.0, 0.0, (-900, 3050))
    mmask = math_(nt, 'MULTIPLY', mex, mdisc, (-750, 3200))
    mpal = ramp(nt, [(0.0, (0.75, 0.50, 0.02, 1)), (0.30, (0.75, 0.74, 0.66, 1)), (0.55, (0.10, 0.19, 0.66, 1)), (0.75, (0.32, 0.10, 0.36, 1)), (0.88, (0.75, 0.50, 0.02, 1))], (-900, 3400), interp='CONSTANT')
    nt.links.new(ms.outputs["Green"], mpal.inputs["Fac"])
    redb = math_(nt, 'MULTIPLY', Pd, maprange(nt, dist, 12.0, NEAR_R, 0.0, 0.45, (-1100, 1550)), (-950, 1550))
    col = mix_rgb(nt, 'MIX', redb, col, (0.24, 0.008, 0.005, 1), (-300, 250))
    col = mix_rgb(nt, 'MIX', pm3, col, pc3, (-200, 250))
    col = mix_rgb(nt, 'MIX', mmask, col, mpal.outputs["Color"], (-100, 250))
    col = mix_rgb(nt, 'MIX', pm1, col, pc1, (0, 250))
    col = mix_rgb(nt, 'MIX', pm2, col, pc2, (100, 250))
    # --- soil on the steep bank, mud and pebbles at the water
    slope = maprange(nt, node(nt, "ShaderNodeSeparateXYZ", (-1600, -1600)).outputs["Z"], 0.0, 1.0, 0.0, 1.0, (-1400, -1600))
    nsep = slope.node.inputs["Value"].links[0].from_node
    nt.links.new(geo.outputs["Normal"], nsep.inputs["Vector"])
    zr = sep.outputs["Z"]
    soiln = noise_tex(nt, ob, 3.0, 8, 0.6, loc=(-1300, -1200))
    soil = ramp(nt, [(0.3, (0.060, 0.042, 0.026, 1)), (0.55, (0.105, 0.072, 0.044, 1)), (0.75, (0.14, 0.100, 0.066, 1))], (-1100, -1200))
    nt.links.new(soiln.outputs["Fac"], soil.inputs["Fac"])
    peb = voronoi(nt, ob, 26.0, loc=(-1300, -1400))
    pebm = maprange(nt, peb.outputs["Distance"], 0.25, 0.45, 1.0, 0.0, (-1100, -1400))
    pebc = ramp(nt, [(0.0, (0.12, 0.105, 0.085, 1)), (1.0, (0.22, 0.20, 0.165, 1))], (-1100, -1500))
    nt.links.new(peb.outputs["Color"], pebc.inputs["Fac"])
    edgen = noise_tex(nt, ob, 1.1, 5, 0.6, loc=(-1300, -1800))
    zj = math_(nt, 'ADD', zr, math_(nt, 'MULTIPLY_ADD', edgen.outputs["Fac"], 0.42, (-1200, -1800), c=-0.21), (-1150, -1750))
    shelf = maprange(nt, zj, WATER_Z + 0.22, WATER_Z + 0.08, 0.0, 1.0, (-1100, -1700))
    soilc = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', pebm, shelf, (-950, -1400)), 0.5, (-900, -1400)), soil.outputs["Color"], pebc.outputs["Color"], (-800, -1300))
    wet = maprange(nt, zr, WATER_Z + 0.35, WATER_Z + 0.02, 1.0, 0.42, (-1100, -1900))
    soilc = mix_rgb(nt, 'MULTIPLY', 1.0, soilc, wet, (-650, -1300))
    sn = noise_tex(nt, ob, 1.4, 4, loc=(-1300, -1000))
    steep = maprange(nt, math_(nt, 'ADD', slope, math_(nt, 'MULTIPLY', sn.outputs["Fac"], 0.16, (-1200, -1000)), (-1050, -1050)), 0.86, 0.80, 0.0, 1.0, (-900, -1050))
    soilmask = math_(nt, 'MAXIMUM', steep, shelf, (-750, -1100))
    soilmask = math_(nt, 'MINIMUM', soilmask, maprange(nt, zr, -0.05, -0.30, 0.0, 1.0, (-900, -1200)), (-650, -1100))
    col = mix_rgb(nt, 'MIX', soilmask, col, soilc, (250, 250))
    # --- contact darkening under tufts and plants (painted from their positions) and a hint of moisture down the bank
    cdark = maprange(nt, csep.outputs["Green"], 0.0, 1.0, 1.0, 0.42, (-900, 1100))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, cdark, (400, 250))
    nt.links.new(col, b.inputs["Base Color"])
    rough = maprange(nt, zr, WATER_Z + 0.30, WATER_Z + 0.02, 0.93, 0.42, (100, -200))
    nt.links.new(rough, b.inputs["Roughness"])
    h = math_(nt, 'ADD', math_(nt, 'MULTIPLY', blades.outputs["Distance"], 0.6, (-200, -500)), math_(nt, 'MULTIPLY', pebm, 0.5, (-200, -600)), (-50, -550))
    h = math_(nt, 'ADD', h, math_(nt, 'MULTIPLY', csep.outputs["Green"], -0.6, (-200, -700)), (50, -600))
    bump_from(nt, b, h, 0.3, 0.008, (200, -500))
    return m

def far_ground_mat(dens_img, name="M_DistantMeadow"):
    """The meadow beyond 40 m: the red carpet of the poppy bed fading into green fields, the far hills, warmed by the
    low sun and softened by distance (the haze is in the albedo: Unity lights backdrop meshes but gives them no fog)."""
    m, nt, b = new_mat(name)
    tc, ob = obj_coords(nt)
    dens = image_lookup(nt, dens_img, ob, TERRAIN_R + 2, (-1300, 900))
    dsep = node(nt, "ShaderNodeSeparateColor", (-1100, 900)); nt.links.new(dens.outputs["Color"], dsep.inputs["Color"])
    vl = node(nt, "ShaderNodeVectorMath", (-1500, 600), operation='LENGTH'); nt.links.new(ob, vl.inputs[0])
    big = noise_tex(nt, ob, 0.045, 5, loc=(-1300, 400)); midn = noise_tex(nt, ob, 0.25, 5, loc=(-1300, 200))
    sw = mix_f(nt, 0.5, big.outputs["Fac"], midn.outputs["Fac"], (-1100, 300))
    sward = ramp(nt, [(0.30, (0.040, 0.075, 0.020, 1)), (0.48, (0.060, 0.110, 0.026, 1)), (0.62, (0.095, 0.135, 0.035, 1)), (0.75, (0.150, 0.160, 0.060, 1))], (-900, 300))
    nt.links.new(sw, sward.inputs["Fac"])
    # rows of hedges and copses on the far hills: dark irregular patches
    cop = noise_tex(nt, ob, 0.11, 3, loc=(-1300, -100))
    copm = maprange(nt, cop.outputs["Fac"], 0.64, 0.70, 0.0, 1.0, (-1100, -100))
    copm = math_(nt, 'MULTIPLY', copm, maprange(nt, vl.outputs["Value"], 60.0, 85.0, 0.0, 1.0, (-1100, -200)), (-950, -150))
    col = mix_rgb(nt, 'MIX', copm, sward.outputs["Color"], (0.030, 0.050, 0.025, 1), (-700, 300))
    # poppy carpet: speckle averaged into a red-green mix at this distance
    sp = voronoi(nt, ob, 5.0, loc=(-1300, 1300))
    sps = node(nt, "ShaderNodeSeparateColor", (-1100, 1300)); nt.links.new(sp.outputs["Color"], sps.inputs["Color"])
    pex = math_(nt, 'LESS_THAN', sps.outputs["Red"], math_(nt, 'MULTIPLY', dsep.outputs["Red"], 1.1, (-1000, 1200)), (-900, 1300))
    pdisc = maprange(nt, sp.outputs["Distance"], 0.25, 0.42, 1.0, 0.0, (-900, 1150))
    pmask = math_(nt, 'MAXIMUM', math_(nt, 'MULTIPLY', pex, pdisc, (-750, 1300)), math_(nt, 'MULTIPLY', dsep.outputs["Red"], 0.55, (-750, 1150)), (-600, 1250))
    pcol = mix_rgb(nt, 'MIX', sps.outputs["Blue"], (0.24, 0.008, 0.005, 1), (0.15, 0.007, 0.006, 1), (-500, 1300))
    col = mix_rgb(nt, 'MIX', pmask, col, pcol, (-400, 300))
    mmask = math_(nt, 'MULTIPLY', dsep.outputs["Blue"], 0.35, (-750, 1000))
    col = mix_rgb(nt, 'MIX', mmask, col, (0.40, 0.36, 0.20, 1), (-300, 300))
    # the river margin: mud and reeds where the land meets the water
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1500, -500)); nt.links.new(ob, sep.inputs["Vector"])
    wet = maprange(nt, sep.outputs["Z"], WATER_Z + 0.4, WATER_Z + 0.05, 0.0, 1.0, (-1100, -500))
    col = mix_rgb(nt, 'MIX', wet, col, (0.06, 0.055, 0.035, 1), (-200, 300))
    # distance haze, baked into the albedo
    hz = maprange(nt, vl.outputs["Value"], 45.0, TERRAIN_R, 0.0, 0.18, (-600, -300), 'SMOOTHSTEP')
    col = mix_rgb(nt, 'MIX', hz, col, (0.22, 0.30, 0.34, 1), (0, 300))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    fine = noise_tex(nt, ob, 2.0, 4, loc=(-300, -600))
    bump_from(nt, b, fine.outputs["Fac"], 0.25, 0.05, (200, -500))
    return m

def water_mat(name="M_Water"):
    """The broad river: dark, clear-brown water over silt, a low roughness, a long slow flow pattern (fine ripples
    stretched along the current) and a few drifting red petals near the field bank. The motion stays restrained."""
    m, nt, b = new_mat(name)
    tc, ob = obj_coords(nt)
    mp = node(nt, "ShaderNodeMapping", (-1500, 0)); mp.inputs["Scale"].default_value = (1.0, 0.22, 1.0)
    nt.links.new(ob, mp.inputs["Vector"])
    rip = noise_tex(nt, mp.outputs["Vector"], 3.2, 6, 0.55, 0.4, loc=(-1200, -300))
    sl = noise_tex(nt, mp.outputs["Vector"], 0.25, 3, loc=(-1200, 100))
    colr = ramp(nt, [(0.3, (0.018, 0.026, 0.020, 1)), (0.7, (0.030, 0.040, 0.030, 1))], (-900, 100))
    nt.links.new(sl.outputs["Fac"], colr.inputs["Fac"])
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1500, 400)); nt.links.new(ob, sep.inputs["Vector"])
    pet = voronoi(nt, ob, 2.2, loc=(-1200, 600))
    ps = node(nt, "ShaderNodeSeparateColor", (-1000, 600)); nt.links.new(pet.outputs["Color"], ps.inputs["Color"])
    pex = math_(nt, 'LESS_THAN', ps.outputs["Red"], 0.05, (-850, 600))
    pd = maprange(nt, pet.outputs["Distance"], 0.03, 0.05, 1.0, 0.0, (-850, 500))
    pm = math_(nt, 'MULTIPLY', pex, pd, (-700, 550))
    col = mix_rgb(nt, 'MIX', pm, colr.outputs["Color"], (0.40, 0.03, 0.02, 1), (-500, 200))
    nt.links.new(col, b.inputs["Base Color"])
    rr = maprange(nt, pm, 0.0, 1.0, 0.11, 0.5, (-500, -100)); nt.links.new(rr, b.inputs["Roughness"])
    bump_from(nt, b, rip.outputs["Fac"], 0.2, 0.02, (-200, -400))
    b.inputs["IOR"].default_value = 1.333
    return m

def bark_mat(name="M_Bark"):
    """Fruit-tree and alder bark: grey-brown, smooth with horizontal lenticels on the younger limbs, fissured
    and lichen-spotted low on the trunks, and earth-stained roots."""
    m, nt, b = new_mat(name)
    tc, ob = obj_coords(nt)
    mp = node(nt, "ShaderNodeMapping", (-1500, 0)); mp.inputs["Scale"].default_value = (5.0, 5.0, 1.2)
    nt.links.new(ob, mp.inputs["Vector"])
    fis = voronoi(nt, mp.outputs["Vector"], 3.0, 'DISTANCE_TO_EDGE', (-1200, 200))
    fn = noise_tex(nt, ob, 6.0, 8, 0.65, 0.5, loc=(-1200, -100))
    r = ramp(nt, [(0.30, (0.050, 0.042, 0.035, 1)), (0.50, (0.115, 0.100, 0.085, 1)), (0.70, (0.185, 0.170, 0.150, 1))], (-900, 0))
    nt.links.new(fn.outputs["Fac"], r.inputs["Fac"])
    crack = maprange(nt, fis.outputs["Distance"], 0.0, 0.08, 0.35, 1.0, (-900, 300))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, r.outputs["Color"], crack, (-600, 100))
    lic = noise_tex(nt, ob, 9.0, 3, loc=(-1200, -400))
    lm = maprange(nt, lic.outputs["Fac"], 0.66, 0.72, 0.0, 0.7, (-900, -400))
    col = mix_rgb(nt, 'MIX', lm, col, (0.26, 0.28, 0.20, 1), (-400, 100))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1500, -700)); nt.links.new(ob, sep.inputs["Vector"])
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.88
    h = math_(nt, 'ADD', fis.outputs["Distance"], math_(nt, 'MULTIPLY', fn.outputs["Fac"], 0.3, (-700, -300)), (-500, -300))
    bump_from(nt, b, h, 0.8, 0.02)
    return m

def leaves_mat(name="M_TreeLeaves"):
    """Leafy crowns (no alpha cards on Quest: the crowns are lumpy masses): leaf cells tinted one by one, darker in the
    gaps between them, broad sunlit and shaded drifts across a crown, a bluer cast on the alders and willows across
    the river (east), warmer on the fruit trees; matte, never glossy."""
    m, nt, b = new_mat(name)
    tc, ob = obj_coords(nt)
    vor = voronoi(nt, ob, 26.0, loc=(-1000, 250)); vor2 = voronoi(nt, ob, 58.0, loc=(-1000, -50))
    big = noise_tex(nt, ob, 0.9, 4, loc=(-1000, -350))
    sp = node(nt, "ShaderNodeSeparateColor", (-750, 250)); nt.links.new(vor.outputs["Color"], sp.inputs["Color"])
    tint = ramp(nt, [(0.0, (0.020, 0.045, 0.012, 1)), (0.45, (0.060, 0.115, 0.028, 1)), (0.8, (0.110, 0.165, 0.045, 1)), (1.0, (0.150, 0.170, 0.060, 1))], (-500, 250))
    nt.links.new(sp.outputs["Red"], tint.inputs["Fac"])
    gaps = ramp(nt, [(0.0, (0.12, 0.12, 0.12, 1)), (0.4, (1, 1, 1, 1))], (-500, 0)); nt.links.new(vor2.outputs["Distance"], gaps.inputs["Fac"])
    col = mix_rgb(nt, 'MULTIPLY', 0.9, tint.outputs["Color"], gaps.outputs["Color"], (-250, 200))
    bigr = ramp(nt, [(0.3, (0.70, 0.74, 0.62, 1)), (0.7, (1.12, 1.08, 1.0, 1))], (-500, -350)); nt.links.new(big.outputs["Fac"], bigr.inputs["Fac"])
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, bigr.outputs["Color"], (0, 200))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1000, -600)); nt.links.new(ob, sep.inputs["Vector"])
    east = maprange(nt, sep.outputs["X"], 12.0, 20.0, 0.0, 1.0, (-750, -600))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', east, 0.45, (-600, -650)), col, (0.040, 0.090, 0.060, 1), (150, 200))
    nt.links.new(col, b.inputs["Base Color"])
    rr = maprange(nt, vor.outputs["Distance"], 0.0, 1.0, 0.62, 0.9, (-250, -150)); nt.links.new(rr, b.inputs["Roughness"])
    hm = math_(nt, 'ADD', vor.outputs["Distance"], vor2.outputs["Distance"], (-250, -450))
    bump_from(nt, b, hm, 1.0, 0.05, (100, -400))
    return m

def leaves_shade_mat(name="M_LeavesShade"):
    """The inside of a crown, seen through the gaps between the outer leaves: the same leaves in their own shade."""
    m, nt, b = new_mat(name)
    tc, ob = obj_coords(nt)
    vor = voronoi(nt, ob, 20.0, loc=(-1000, 250)); big = noise_tex(nt, ob, 1.2, 4, loc=(-1000, -100))
    r = ramp(nt, [(0.0, (0.020, 0.040, 0.012, 1)), (0.6, (0.040, 0.075, 0.020, 1)), (1.0, (0.065, 0.100, 0.028, 1))], (-600, 200))
    nt.links.new(vor.outputs["Color"], r.inputs["Fac"])
    bg_ = maprange(nt, big.outputs["Fac"], 0.3, 0.7, 0.75, 1.15, (-600, -100))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, r.outputs["Color"], bg_, (-300, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, vor.outputs["Distance"], 0.8, 0.05)
    return m

def stone_mat(name="M_BankStone"):
    """River stones half-buried at the waterline: grey sandstone, dark and wet below, dry and paler above, moss on top."""
    m, nt, b = new_mat(name)
    tc, ob = obj_coords(nt)
    n = noise_tex(nt, ob, 5.0, 8, 0.6, 0.3, loc=(-1000, 0))
    r = ramp(nt, [(0.3, (0.12, 0.115, 0.10, 1)), (0.55, (0.22, 0.21, 0.185, 1)), (0.75, (0.30, 0.285, 0.25, 1))], (-700, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1000, -300)); nt.links.new(ob, sep.inputs["Vector"])
    wet = maprange(nt, sep.outputs["Z"], WATER_Z + 0.25, WATER_Z + 0.02, 1.0, 0.45, (-700, -300))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, r.outputs["Color"], wet, (-400, 0))
    geo = node(nt, "ShaderNodeNewGeometry", (-1000, -600)); gs = node(nt, "ShaderNodeSeparateXYZ", (-800, -600)); nt.links.new(geo.outputs["Normal"], gs.inputs["Vector"])
    moss = maprange(nt, gs.outputs["Z"], 0.6, 0.9, 0.0, 0.8, (-600, -600))
    mn = noise_tex(nt, ob, 8.0, 3, loc=(-800, -800))
    moss = math_(nt, 'MULTIPLY', moss, maprange(nt, mn.outputs["Fac"], 0.45, 0.6, 0.0, 1.0, (-600, -800)), (-450, -700))
    col = mix_rgb(nt, 'MIX', moss, col, (0.06, 0.09, 0.03, 1), (-200, 0))
    nt.links.new(col, b.inputs["Base Color"])
    rr = maprange(nt, sep.outputs["Z"], WATER_Z + 0.25, WATER_Z + 0.02, 0.85, 0.35, (-400, -300)); nt.links.new(rr, b.inputs["Roughness"])
    fine = noise_tex(nt, ob, 30.0, 6, loc=(-700, -1000))
    bump_from(nt, b, fine.outputs["Fac"], 0.5, 0.004)
    return m

def far_trees_mat(name="M_DistantTrees"):
    """Copses and hedgerow trees far off: crown lumps, hazed blue-green by distance."""
    m, nt, b = new_mat(name)
    tc, ob = obj_coords(nt)
    vor = voronoi(nt, ob, 0.9, loc=(-1000, 200)); nz = noise_tex(nt, ob, 0.35, 4, loc=(-1000, -100))
    gaps = maprange(nt, vor.outputs["Distance"], 0.0, 0.6, 0.55, 1.0, (-700, 200))
    r = ramp(nt, [(0.3, (0.040, 0.065, 0.045, 1)), (0.7, (0.080, 0.105, 0.070, 1))], (-700, -100)); nt.links.new(nz.outputs["Fac"], r.inputs["Fac"])
    col = mix_rgb(nt, 'MULTIPLY', 1.0, r.outputs["Color"], gaps, (-400, 100))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1000, -400)); nt.links.new(ob, sep.inputs["Vector"])
    tz = maprange(nt, sep.outputs["Z"], -1.0, 8.0, 0.75, 1.1, (-700, -400))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, tz, (-250, 100))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.92
    bump_from(nt, b, vor.outputs["Distance"], 0.5, 0.3)
    return m

def sky_dome_mat(name="M_SkyDome"):
    """Late-afternoon sky over Oz: clear and deepening blue overhead, warm and pale low in the west where the sun is,
    a few fair-weather cumulus lit gold on their sun side (thin and few straight ahead, behind the reading page),
    a band of far blue hills along the horizon and, ahead-left, a faint green glow where the Emerald City lies."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-2200, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-2000, 0), operation='NORMALIZE'); nt.links.new(tc.outputs["Object"], nv.inputs[0])
    d = nv.outputs[0]
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1800, 0)); nt.links.new(d, sep.inputs["Vector"])
    el = sep.outputs["Z"]
    base = ramp(nt, [(0.0, (0.40, 0.44, 0.42, 1)), (0.105, (0.64, 0.64, 0.60, 1)), (0.13, (0.56, 0.62, 0.70, 1)), (0.22, (0.34, 0.48, 0.72, 1)),
                     (0.45, (0.17, 0.33, 0.66, 1)), (1.0, (0.08, 0.19, 0.52, 1))], (-1300, 400))
    elm = maprange(nt, el, -0.12, 1.0, 0.0, 1.0, (-1500, 400)); nt.links.new(elm, base.inputs["Fac"])
    col = base.outputs["Color"]
    # the sun's side: warm and bright low in the west, a small disc
    sd = node(nt, "ShaderNodeVectorMath", (-1600, 800), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(SUN_DIR); nt.links.new(d, sd.inputs[0])
    halo = maprange(nt, sd.outputs["Value"], 0.70, 1.0, 0.0, 1.0, (-1400, 800), 'SMOOTHSTEP')
    halo = math_(nt, 'POWER', halo, 2.6, (-1250, 800))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', halo, 0.55, (-1100, 850)), col, (0.95, 0.62, 0.30, 1), (-900, 400))
    disc = maprange(nt, sd.outputs["Value"], 0.99955, 0.99975, 0.0, 1.0, (-1400, 1000))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', disc, 6.0, (-1100, 1000)), col, (1.0, 0.92, 0.80, 1), (-800, 400))
    # cumulus: a flat cloud deck in perspective, thresholded; lit on the sun side (sample shifted towards the sun)
    zk = math_(nt, 'ADD', math_(nt, 'MAXIMUM', el, 0.0, (-1600, -200)), 0.07, (-1450, -200))
    px = math_(nt, 'DIVIDE', sep.outputs["X"], zk, (-1300, -150)); py = math_(nt, 'DIVIDE', sep.outputs["Y"], zk, (-1300, -300))
    cv = node(nt, "ShaderNodeCombineXYZ", (-1150, -200)); nt.links.new(px, cv.inputs["X"]); nt.links.new(py, cv.inputs["Y"])
    mpc = node(nt, "ShaderNodeMapping", (-1000, -200)); mpc.inputs["Scale"].default_value = (0.32, 0.32, 1); mpc.inputs["Location"].default_value = (4.1, 2.7, 0.3)
    nt.links.new(cv.outputs[0], mpc.inputs["Vector"])
    c1 = noise_tex(nt, mpc.outputs["Vector"], 1.0, 9, 0.58, 0.25, loc=(-800, -200))
    sunoff = node(nt, "ShaderNodeVectorMath", (-900, -500), operation='ADD'); sunoff.inputs[1].default_value = (SUN_DIR.x * 0.06, SUN_DIR.y * 0.06, 0.0)
    nt.links.new(mpc.outputs["Vector"], sunoff.inputs[0])
    c2 = noise_tex(nt, sunoff.outputs["Vector"], 1.0, 9, 0.58, 0.25, loc=(-700, -500))
    big = noise_tex(nt, mpc.outputs["Vector"], 0.18, 2, loc=(-800, -800))
    # cloud cover: few overall, fewer straight ahead (behind the page), none near the zenith, a little denser in the east
    fwd = maprange(nt, sep.outputs["Y"], 0.55, 0.92, 1.0, 0.25, (-800, -1000))
    eastm = maprange(nt, sep.outputs["X"], -0.3, 0.8, 0.85, 1.15, (-800, -1150))
    elc = maprange(nt, el, 0.45, 0.16, 0.0, 1.0, (-800, -1300))
    cov = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', fwd, eastm, (-600, -1050)), elc, (-450, -1100))
    thr = math_(nt, 'ADD', math_(nt, 'MULTIPLY', big.outputs["Fac"], 0.25, (-600, -800)), c1.outputs["Fac"], (-450, -700))
    cm = maprange(nt, math_(nt, 'MULTIPLY', thr, cov, (-350, -800)), 0.50, 0.66, 0.0, 1.0, (-200, -800), 'SMOOTHSTEP')
    cm = math_(nt, 'MULTIPLY', cm, maprange(nt, el, 0.012, 0.05, 0.0, 1.0, (-350, -1300)), (-100, -900))
    lit = maprange(nt, math_(nt, 'SUBTRACT', c1.outputs["Fac"], c2.outputs["Fac"], (-450, -500)), -0.04, 0.05, 0.0, 1.0, (-250, -500))
    ccol = mix_rgb(nt, 'MIX', lit, (0.52, 0.55, 0.64, 1), (1.05, 0.95, 0.82, 1), (-100, -500))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', cm, 0.92, (0, -800)), col, ccol, (-600, 400))
    # far hills painted along the horizon (terrain ends below them at 108 m)
    az = math_(nt, 'ARCTAN2', sep.outputs["Y"], sep.outputs["X"], (-1600, -1600))
    azv = node(nt, "ShaderNodeCombineXYZ", (-1450, -1600)); nt.links.new(math_(nt, 'COSINE', az, None, (-1500, -1700)), azv.inputs["X"]); nt.links.new(math_(nt, 'SINE', az, None, (-1500, -1800)), azv.inputs["Y"])
    hn = noise_tex(nt, azv.outputs[0], 2.6, 5, 0.55, loc=(-1300, -1650))
    hill_h = math_(nt, 'MULTIPLY_ADD', hn.outputs["Fac"], 0.050, (-1100, -1650), c=-0.008)
    hill_m = math_(nt, 'LESS_THAN', el, hill_h, (-950, -1650))
    hill_soft = maprange(nt, math_(nt, 'SUBTRACT', hill_h, el, (-950, -1800)), 0.0, 0.004, 0.0, 1.0, (-800, -1800))
    hcol = mix_rgb(nt, 'MIX', maprange(nt, math_(nt, 'SUBTRACT', hill_h, el, (-950, -1950)), 0.0, 0.03, 0.0, 1.0, (-800, -1950)), (0.42, 0.50, 0.55, 1), (0.30, 0.38, 0.38, 1), (-650, -1900))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', hill_m, hill_soft, (-650, -1700)), col, hcol, (-400, 400))
    # the Emerald City: a faint green glow low on the horizon, ahead-left
    ed = node(nt, "ShaderNodeVectorMath", (-1600, 1200), operation='DOT_PRODUCT'); ed.inputs[1].default_value = tuple(EMERALD_DIR); nt.links.new(d, ed.inputs[0])
    eg = maprange(nt, ed.outputs["Value"], 0.985, 1.0, 0.0, 1.0, (-1400, 1200), 'SMOOTHSTEP')
    egel = maprange(nt, el, 0.10, 0.0, 0.0, 1.0, (-1400, 1350), 'SMOOTHSTEP')
    egm = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', eg, egel, (-1250, 1250)), 0.32, (-1100, 1250))
    col = mix_rgb(nt, 'ADD', egm, col, (0.10, 0.55, 0.28, 1), (-200, 400))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m

# ----------------------------------------------------------------------------- the terrain (built first: plants sit on it)
def terrain_grid(name, r0, r1, N, SEG, expo, ratio):
    """A polar grid from r0 to r1 displaced by H(), decimated where the land is flat; its rim rings are protected so
    the near ground and far.meadow keep exactly the same vertices along their shared edge."""
    def ring_r(j): return r0 + (r1 - r0) * (j / N) ** expo
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []; centre = None
    for j in range(N + 1):
        rr = ring_r(j)
        if rr < 1e-6: centre = bm.verts.new((0.0, 0.0, H(0.0, 0.0))); rings.append(None); continue
        ring = []
        for i in range(SEG):
            a_ = 2 * math.pi * i / SEG; x, y = rr * math.cos(a_), rr * math.sin(a_)
            ring.append(bm.verts.new((x, y, H(x, y))))
        rings.append(ring)
    for j in range(N):
        a, b_ = rings[j], rings[j + 1]
        for i in range(SEG):
            k = (i + 1) % SEG
            if a is None: bm.faces.new((centre, b_[i], b_[k]))
            else: bm.faces.new((a[i], a[k], b_[k], b_[i]))
    bmesh.ops.triangulate(bm, faces=bm.faces)
    for f_ in bm.faces:
        if f_.normal.z < 0: f_.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); link(o)
    vg = o.vertex_groups.new(name="rim")
    rim = [v.index for v in me.vertices if abs(math.hypot(v.co.x, v.co.y) - r1) < 1e-3 or (r0 > 0 and abs(math.hypot(v.co.x, v.co.y) - r0) < 1e-3)]
    vg.add(rim, 1.0, 'REPLACE')
    md = o.modifiers.new("Decimate", 'DECIMATE'); md.decimate_type = 'COLLAPSE'; md.ratio = ratio; md.use_collapse_triangulate = True
    md.vertex_group = "rim"; md.invert_vertex_group = True; md.vertex_group_factor = 1000.0
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.modifier_apply(modifier=md.name)
    o.select_set(False)
    for p in me.polygons: p.use_smooth = True
    rim_after = sum(1 for v in me.vertices if abs(math.hypot(v.co.x, v.co.y) - NEAR_R) < 1e-3)
    print(f"terrain {name}: tris={len(me.polygons)} rim verts at NEAR_R={rim_after}")
    return o

LOGK = 3.0
def near_uv(x, y):
    r = math.hypot(x, y)
    if r < 1e-6: return (0.5, 0.5)
    g = math.log(1.0 + r / LOGK) / math.log(1.0 + (NEAR_R + 2.0) / LOGK) * 0.5
    return (0.5 + g * x / r, 0.5 + g * y / r)

def assign_uvs(obj, fn):
    me = obj.data
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers[0]
    for p in me.polygons:
        cx = sum(me.vertices[i].co.x for i in p.vertices) / len(p.vertices)
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl.data[li].uv = fn(co.x, co.y, cx)

def far_uv(x, y, cx):
    """Polar: u = angle (seam straight behind the reader, -Y), v = log radius."""
    if abs(x) < 1e-5: x = 1e-5 if cx > 0 else -1e-5
    th = math.atan2(-x, y)
    u = 1.0 - (th + math.pi) / (2 * math.pi)
    r = max(NEAR_R - 6.0, math.hypot(x, y))
    v = math.log(r / (NEAR_R - 6.0)) / math.log((TERRAIN_R + 2.0) / (NEAR_R - 6.0))
    return (u, v)

GROUND = terrain_grid("Ground", 0.0, NEAR_R, 72, 240, 1.55, 0.115)
FAR = terrain_grid("far.meadow", NEAR_R, TERRAIN_R, 26, 240, 1.3, 0.11)
assign_uvs(GROUND, lambda x, y, cx: near_uv(x, y))
# far: cut along x = 0 so no face straddles the polar seam behind the reader
_bm = bmesh.new(); _bm.from_mesh(FAR.data)
bmesh.ops.bisect_plane(_bm, geom=_bm.verts[:] + _bm.edges[:] + _bm.faces[:], plane_co=(0, 0, 0), plane_no=(1, 0, 0))
_bm.to_mesh(FAR.data); _bm.free()
for p in FAR.data.polygons: p.use_smooth = True
assign_uvs(FAR, far_uv)
FAR.visible_shadow = False

_dg = bpy.context.evaluated_depsgraph_get()
BVH = BVHTree.FromObject(GROUND, _dg)
BVH_FAR = BVHTree.FromObject(FAR, _dg)
def ground_z(x, y):
    for bv in (BVH, BVH_FAR):
        hit = bv.ray_cast(Vector((x, y, 60.0)), Vector((0, 0, -1)))
        if hit[0] is not None: return hit[0].z
    return H(x, y)
def ground_n(x, y):
    hit = BVH.ray_cast(Vector((x, y, 60.0)), Vector((0, 0, -1)))
    return hit[1].normalized() if hit[0] is not None else Vector((0, 0, 1))
print("terrain tris near/far", len(GROUND.data.polygons), len(FAR.data.polygons), "z(0,0)=", round(ground_z(0, 0), 4))

# ----------------------------------------------------------------------------- mesh builder for the many small cards
class MB:
    """Accumulates verts / faces / per-loop UVs for one material and builds one object."""
    def __init__(self, name, mat): self.name, self.mat, self.v, self.f, self.uv = name, mat, [], [], []
    def vert(self, p): self.v.append(tuple(p)); return len(self.v) - 1
    def face(self, idx, uvs, toward=None):
        if toward is not None:
            a, b_, c = (Vector(self.v[i]) for i in idx[:3])
            if (b_ - a).cross(c - a).dot(toward) < 0: idx = list(reversed(idx)); uvs = list(reversed(uvs))
        self.f.append(tuple(idx)); self.uv.append(list(uvs))
    def tris(self): return sum(len(f) - 2 for f in self.f)
    def build(self):
        me = bpy.data.meshes.new(self.name); me.from_pydata(self.v, [], self.f)
        uvl = me.uv_layers.new(name="UVMap")
        for p, uvs in zip(me.polygons, self.uv):
            for li, uv in zip(p.loop_indices, uvs): uvl.data[li].uv = uv
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        o = bpy.data.objects.new(self.name, me); me.materials.append(self.mat)
        return link(o)

def col_u(col, ncols, s):
    """u inside a palette column, inset from its edges (s in 0..1 across the card)."""
    return (col + 0.12 + 0.76 * s) / ncols

EYE_P = Vector((0.0, 0.0, EYE))
def to_reader(p):
    d = EYE_P - Vector(p); d.z *= 0.35
    return d.normalized() if d.length > 1e-6 else Vector((0, -1, 0))

def ribbon(mb, pts, widths, col, ncols, side=None, toward=None, v0=0.0, v1=1.0, tip=True):
    """A strip along pts (list of Vector), width per point, its face turned to the reader (or `toward`)."""
    n = len(pts)
    idx = []
    for k, p in enumerate(pts):
        d = (pts[min(k + 1, n - 1)] - pts[max(k - 1, 0)]).normalized()
        sd = side if side is not None else d.cross(to_reader(p) if toward is None else toward)
        if sd.length < 1e-6: sd = Vector((1, 0, 0))
        sd = sd.normalized()
        w = widths[k]
        v = v0 + (v1 - v0) * k / (n - 1)
        if tip and k == n - 1 and w < 1e-5:
            idx.append(((mb.vert(p), (col_u(col, ncols, 0.5), v)),))
        else:
            idx.append(((mb.vert(p - sd * w), (col_u(col, ncols, 0.0), v)), (mb.vert(p + sd * w), (col_u(col, ncols, 1.0), v))))
    tw = toward if toward is not None else to_reader(pts[n // 2])
    for a, b_ in zip(idx, idx[1:]):
        if len(b_) == 1: mb.face([a[0][0], a[1][0], b_[0][0]], [a[0][1], a[1][1], b_[0][1]], tw)
        else: mb.face([a[0][0], a[1][0], b_[1][0], b_[0][0]], [a[0][1], a[1][1], b_[1][1], b_[0][1]], tw)

M_PETAL = petal_mat(); M_HERB = herbage_mat(); M_FLOWERS = flowers_mat()
MB_PETAL = MB("PoppyPetals", M_PETAL); MB_HERB = MB("Herbage", M_HERB); MB_FLOW = MB("MeadowFlowers", M_FLOWERS)
CONTACT = []    # (x, y, radius, strength): painted into the ground's contact map

# ----------------------------------------------------------------------------- scatter
class Spacing:
    def __init__(self, cell): self.cell, self.g = cell, {}
    def ok(self, x, y, dmin):
        cx, cy = int(math.floor(x / self.cell)), int(math.floor(y / self.cell))
        for i in range(cx - 1, cx + 2):
            for j in range(cy - 1, cy + 2):
                for (px, py) in self.g.get((i, j), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < dmin * dmin: return False
        return True
    def add(self, x, y):
        self.g.setdefault((int(math.floor(x / self.cell)), int(math.floor(y / self.cell))), []).append((x, y))

def scatter(rng, rmin, rmax, per_m2, dens, spacing, dmin, cap):
    area = math.pi * (rmax * rmax - rmin * rmin)
    out = []
    for _ in range(int(area * per_m2)):
        r = math.sqrt(rng.uniform(rmin * rmin, rmax * rmax)); a = rng.uniform(-math.pi, math.pi)
        x, y = r * math.cos(a), r * math.sin(a)
        if rng.random() > dens(x, y): continue
        if not spacing.ok(x, y, dmin): continue
        spacing.add(x, y); out.append((x, y))
        if len(out) >= cap: break
    return out

def clump(x, y, s=1.3, off=0.0):
    return min(1.0, max(0.0, 0.55 + 0.9 * n2(x, y, s, off)))

# ----------------------------------------------------------------------------- poppies (three levels of detail)
def stem_curve(base, top, lean_dir, bow, n):
    pts = []
    for k in range(n + 1):
        t = k / n
        p = base.lerp(top, t) + lean_dir * bow * math.sin(math.pi * t) * 0.5
        pts.append(p)
    return pts

def petal(mb, c, axis, rdir, R, cup, variant, rng, rows=2, crumple=0.12, droop=0.0):
    """One broad poppy petal: a fan from the centre, cupped up along `axis`, fanned along rdir."""
    lat = axis.cross(rdir).normalized()
    def P_(t, s):
        hw = R * (0.30 + 0.70 * math.sin(min(1.0, t * 1.15) * math.pi / 2)) * 0.95
        tt = t * (1.0 - 0.13 * s * s)                                       # rounded rim: the corners pulled back
        z = R * (cup * tt * tt - droop * tt ** 3) + R * crumple * noise.noise(Vector((t * 3.1 + variant, s * 2.3, rng.random())))
        return c + rdir * (R * tt) + lat * (hw * s * t ** 0.6) + axis * z
    def uv(t, s): return (col_u(variant, 6, 0.5 + 0.5 * s), 0.04 + 0.92 * t)
    if rows == 2:
        r0 = [(mb.vert(P_(0.0, 0.0)), uv(0.0, 0.0))]
        r1 = [(mb.vert(P_(0.5, s)), uv(0.5, s)) for s in (-1.0, 0.0, 1.0)]
        r2 = [(mb.vert(P_(1.0, s)), uv(1.0, s)) for s in (-1.0, -0.34, 0.34, 1.0)]
        mb.face([r0[0][0], r1[0][0], r1[1][0]], [r0[0][1], r1[0][1], r1[1][1]], axis)
        mb.face([r0[0][0], r1[1][0], r1[2][0]], [r0[0][1], r1[1][1], r1[2][1]], axis)
        # strip between r1 (3) and r2 (4): 5 triangles
        mb.face([r1[0][0], r2[0][0], r2[1][0]], [r1[0][1], r2[0][1], r2[1][1]], axis)
        mb.face([r1[0][0], r2[1][0], r1[1][0]], [r1[0][1], r2[1][1], r1[1][1]], axis)
        mb.face([r1[1][0], r2[1][0], r2[2][0]], [r1[1][1], r2[1][1], r2[2][1]], axis)
        mb.face([r1[1][0], r2[2][0], r1[2][0]], [r1[1][1], r2[2][1], r1[2][1]], axis)
        mb.face([r1[2][0], r2[2][0], r2[3][0]], [r1[2][1], r2[2][1], r2[3][1]], axis)
    else:
        a0 = (mb.vert(P_(0.0, 0.0)), uv(0.0, 0.0))
        r2 = [(mb.vert(P_(1.0, s)), uv(1.0, s)) for s in (-1.0, 0.0, 1.0)]
        mb.face([a0[0], r2[0][0], r2[1][0]], [a0[1], r2[0][1], r2[1][1]], axis)
        mb.face([a0[0], r2[1][0], r2[2][0]], [a0[1], r2[1][1], r2[2][1]], axis)

def capsule(mb, c, axis, size, col=H_BUD):
    """The seed capsule in the flower's heart (a small four-sided urn with a flat top)."""
    u = axis.orthogonal().normalized(); w = axis.cross(u)
    ring = [c + (u * math.cos(k * math.pi / 2) + w * math.sin(k * math.pi / 2)) * size * 0.8 + axis * size * 0.6 for k in range(4)]
    top = c + axis * size * 1.25
    b0 = mb.vert(c - axis * size * 0.2); iv = [mb.vert(p) for p in ring]; t0 = mb.vert(top)
    for k in range(4):
        mb.face([b0, iv[k], iv[(k + 1) % 4]], [(col_u(col, NH, 0.5), 0.3), (col_u(col, NH, 0.0), 0.7), (col_u(col, NH, 1.0), 0.7)], (ring[k] + ring[(k + 1) % 4]) * 0.5 - c)
        tv = [MB_PETAL.vert(ring[k]), MB_PETAL.vert(top), MB_PETAL.vert(ring[(k + 1) % 4])]
        MB_PETAL.face(tv, [(col_u(2, 6, 0.3), 0.03), (col_u(2, 6, 0.5), 0.01), (col_u(2, 6, 0.7), 0.03)], axis)

def bud(mb, tip, hang, size, rng):
    """A nodding, hairy bud: an elongated octahedron hanging from the hooked stem."""
    a = hang.normalized(); u = a.orthogonal().normalized(); w = a.cross(u)
    L = size * 2.0
    p0 = tip; p1 = tip + a * L
    mid = [tip + a * L * 0.55 + (u * math.cos(k * math.pi / 2) + w * math.sin(k * math.pi / 2)) * size * 0.75 for k in range(4)]
    i0, i1 = mb.vert(p0), mb.vert(p1); im = [mb.vert(p) for p in mid]
    for k in range(4):
        out = (mid[k] + mid[(k + 1) % 4]) * 0.5 - (tip + a * L * 0.55)
        mb.face([i0, im[k], im[(k + 1) % 4]], [(col_u(H_BUD, NH, 0.5), 0.55), (col_u(H_BUD, NH, 0.0), 0.8), (col_u(H_BUD, NH, 1.0), 0.8)], out)
        mb.face([im[k], i1, im[(k + 1) % 4]], [(col_u(H_BUD, NH, 0.0), 0.8), (col_u(H_BUD, NH, 0.5), 0.98), (col_u(H_BUD, NH, 1.0), 0.8)], out)

def lobed_leaf(mb, base, direction, length, width, rng, col=H_POPPY):
    """A pinnately lobed poppy leaf arching out from the base of the plant."""
    d = Vector((direction.x, direction.y, 0)).normalized()
    up = Vector((0, 0, 1)); side = d.cross(up).normalized()
    lift = rng.uniform(0.25, 0.6)
    pts = [base + d * length * t + up * length * (lift * math.sin(t * math.pi * 0.8) * 0.6) for t in (0.0, 0.33, 0.66, 1.0)]
    ws = [width * 0.25, width, width * 0.7, 0.0]
    # zig-zag lobes: alternate the half widths
    idx = []
    for k, (p, w) in enumerate(zip(pts, ws)):
        v = k / 3
        if k == 3:
            idx.append(((mb.vert(p), (col_u(col, NH, 0.5), 0.98)),)); continue
        wl = w * (1.0 if k % 2 else 0.65); wr = w * (0.65 if k % 2 else 1.0)
        idx.append(((mb.vert(p - side * wl + up * w * 0.15), (col_u(col, NH, 0.0), 0.2 + 0.75 * v)), (mb.vert(p + side * wr + up * w * 0.15), (col_u(col, NH, 1.0), 0.2 + 0.75 * v))))
    for a, b_ in zip(idx, idx[1:]):
        if len(b_) == 1: mb.face([a[0][0], a[1][0], b_[0][0]], [a[0][1], a[1][1], b_[0][1]], up)
        else: mb.face([a[0][0], a[1][0], b_[1][0], b_[0][0]], [a[0][1], a[1][1], b_[1][1], b_[0][1]], up)

def poppy_plant(x, y, rng, lod):
    gz = ground_z(x, y) - 0.015
    base = Vector((x, y, gz))
    r_from = math.hypot(x, y)
    age = rng.random()
    h = rng.uniform(0.26, 0.74) * (0.85 + 0.3 * clump(x, y, 4.0, 9.1))
    if lod == 2: h *= 0.72
    lean = Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0)).normalized()
    sunh = Vector((SUN_DIR.x, SUN_DIR.y, 0)).normalized()
    lean = (lean + sunh * 0.35).normalized()
    tilt = rng.uniform(0.05, 0.42)
    top = base + Vector((0, 0, h)) + lean * h * tilt * 0.5
    axis = (Vector((0, 0, 1)) + lean * tilt * 1.4 + Vector((rng.gauss(0, 0.15), rng.gauss(0, 0.15), 0))).normalized()
    R = rng.uniform(0.030, 0.050) * (1.0, 1.15, 1.3)[lod]
    variant = rng.choice([0, 0, 0, 1, 1, 2, 3, 3, 5])
    stem_w = 0.0022 if lod == 0 else 0.0026 if lod == 1 else 0.0035
    CONTACT.append((x, y, 0.07 if lod == 0 else 0.05, 0.35))
    if lod == 2:
        # three-triangle cup on a needle stem
        lat = axis.orthogonal().normalized(); lat2 = axis.cross(lat)
        rim = [top + axis * R * 0.55 + (lat * math.cos(a_) + lat2 * math.sin(a_)) * R * 1.05 for a_ in (0.3, 2.4, 4.5)]
        c0 = MB_PETAL.vert(top - axis * R * 0.05); rv = [MB_PETAL.vert(p) for p in rim]
        for k in range(3):
            MB_PETAL.face([c0, rv[k], rv[(k + 1) % 3]], [(col_u(variant, 6, 0.5), 0.1), (col_u(variant, 6, 0.0), 0.9), (col_u(variant, 6, 1.0), 0.9)], to_reader(top))
        return
    if (lod == 0 and age < 0.16) or (lod == 1 and age < 0.06):
        # a bud on a hooked stem (younger plant)
        hb = h * rng.uniform(0.75, 0.95)
        topb = base + Vector((0, 0, hb)) + lean * hb * tilt * 0.4
        hook = topb + lean * 0.03 + Vector((0, 0, 0.015))
        pts = stem_curve(base, topb, lean, 0.03, 3) + [hook]
        ribbon(MB_HERB, pts, [stem_w * 1.1, stem_w, stem_w, stem_w * 0.9, stem_w * 0.8], H_POPPY, NH, v0=0.1, v1=0.85, tip=False)
        bud(MB_HERB, hook, (lean * 0.6 + Vector((0, 0, -1))).normalized(), rng.uniform(0.008, 0.012), rng)
        if lod == 0:
            for _ in range(rng.randint(1, 2)): lobed_leaf(MB_HERB, base, Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0)), rng.uniform(0.08, 0.15), rng.uniform(0.012, 0.02), rng)
        return
    nseg = 3 if lod == 0 else 1
    if lod == 0 or r_from < 6.0:
        pts = stem_curve(base, top, lean, rng.uniform(0.0, 0.06), nseg)
        ribbon(MB_HERB, pts, [stem_w * 1.15] + [stem_w] * (nseg - 1) + [stem_w * 0.8], H_POPPY, NH, v0=0.1, v1=0.9, tip=False)
    if lod <= 1 and age > 0.93:
        capsule(MB_HERB, top, axis, rng.uniform(0.008, 0.011)); return    # petals fallen: the seed head alone
    phi = rng.uniform(0, 2 * math.pi)
    u = axis.orthogonal().normalized(); w = axis.cross(u)
    opening = age < 0.26                                              # just opened: deep cup, petals still crumpled
    old = age > 0.84                                                   # old: flat, a little reflexed, faded
    if old: variant = 4 if rng.random() < 0.6 else variant
    cup = 1.0 if opening else (0.18 if old else rng.uniform(0.5, 0.85))
    droop = 0.35 if old else 0.0
    rows = 2 if lod == 0 else 1
    for k in range(4):
        a_ = phi + k * math.pi / 2 + rng.gauss(0, 0.12)
        rdir = (u * math.cos(a_) + w * math.sin(a_)).normalized()
        inner = k % 2 == 1
        RR = R * (0.86 if inner else 1.0) * (0.75 if opening else 1.0)
        if old and k == 3 and rng.random() < 0.5: continue           # one petal already dropped
        petal(MB_PETAL, top + axis * (0.006 if inner else 0.0), axis, rdir, RR, cup + (0.15 if inner else 0.0), variant, rng, rows=rows, crumple=0.16 if opening else 0.10, droop=droop)
    if lod == 0:
        capsule(MB_HERB, top + axis * 0.002, axis, R * 0.2)
        for _ in range(rng.randint(0, 1)): lobed_leaf(MB_HERB, base, Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0)), rng.uniform(0.09, 0.17), rng.uniform(0.012, 0.022), rng)
        if rng.random() < 0.3:      # a second, younger bud from the same root
            b2 = base + Vector((rng.gauss(0, 0.02), rng.gauss(0, 0.02), 0)); l2 = Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0)).normalized()
            hb = h * rng.uniform(0.45, 0.7); t2 = b2 + Vector((0, 0, hb)) + l2 * 0.02
            hook = t2 + l2 * 0.025 + Vector((0, 0, 0.012))
            ribbon(MB_HERB, [b2, b2.lerp(t2, 0.5), t2, hook], [stem_w, stem_w * 0.9, stem_w * 0.8, stem_w * 0.7], H_POPPY, NH, v0=0.1, v1=0.85, tip=False)
            bud(MB_HERB, hook, (l2 * 0.5 + Vector((0, 0, -1))).normalized(), rng.uniform(0.007, 0.010), rng)

rng_p = random.Random(41)
space_p = Spacing(0.25)
def poppy_density(x, y):
    if math.hypot(x, y) < 0.45: return 0.0
    return P(x, y) * clump(x, y, 1.1, 2.0)
near_p = scatter(rng_p, 0.4, 2.6, 60.0, poppy_density, space_p, 0.075, 150)
mid_p = scatter(rng_p, 2.6, 9.5, 30.0, poppy_density, space_p, 0.09, 540)
far_p = scatter(rng_p, 9.5, 23.0, 9.0, poppy_density, space_p, 0.14, 820)
for (x, y) in near_p: poppy_plant(x, y, rng_p, 0)
t_near = MB_PETAL.tris() + MB_HERB.tris()
for (x, y) in mid_p: poppy_plant(x, y, rng_p, 1)
t_mid = MB_PETAL.tris() + MB_HERB.tris() - t_near
for (x, y) in far_p: poppy_plant(x, y, rng_p, 2)
print(f"poppies near={len(near_p)} mid={len(mid_p)} far={len(far_p)}  tris near={t_near} mid={t_mid} far={MB_PETAL.tris() + MB_HERB.tris() - t_near - t_mid}")

# a few fallen petals lying on the ground among the near poppies
for k in range(40):
    x, y = rng_p.uniform(-4.0, 1.0), rng_p.uniform(-3.0, 4.5)
    if P(x, y) < 0.3 or math.hypot(x, y) < 0.4: continue
    c = Vector((x, y, ground_z(x, y) + 0.004)); a_ = rng_p.uniform(0, 2 * math.pi)
    rd = Vector((math.cos(a_), math.sin(a_), 0)); lt = Vector((-rd.y, rd.x, 0)); R = rng_p.uniform(0.025, 0.04)
    var = rng_p.choice([2, 4, 4])
    pts = [c, c + rd * R * 0.6 + lt * R * 0.45 + Vector((0, 0, 0.004)), c + rd * R + Vector((0, 0, 0.008)), c + rd * R * 0.6 - lt * R * 0.45 + Vector((0, 0, 0.004))]
    iv = [MB_PETAL.vert(p) for p in pts]
    MB_PETAL.face(iv, [(col_u(var, 6, 0.5), 0.2), (col_u(var, 6, 0.0), 0.7), (col_u(var, 6, 0.5), 0.95), (col_u(var, 6, 1.0), 0.7)], Vector((0, 0, 1)))

# ----------------------------------------------------------------------------- grass: soft arching tufts, seed heads, plantain, clover
def blade2(mb, base, h, w, ld, lean, droop, col, twist=0.0):
    """A curved grass leaf in three triangles: a base quad to a bend, then the tip; it arches out and over."""
    up = Vector((0, 0, 1)); ld = Vector((ld.x, ld.y, 0)).normalized()
    def dirv(a_): return up * math.cos(a_) + ld * math.sin(a_)
    mid = base + dirv(lean + 0.22 * droop) * h * 0.55
    tip = mid + dirv(lean + 0.95 * droop) * h * 0.5
    side = up.cross(ld).normalized()
    side = (side * math.cos(twist) + ld * math.sin(twist)).normalized()
    ribbon(mb, [base, mid, tip], [w, w * 0.78, 0.0], col, NH, side=side, v0=0.0, v1=1.0)

def tuft(x, y, rng, scale, lod, lean_bias=None):
    """A tussock of meadow grass: many curved leaves of uneven length fanning out of one crown, the long ones arching
    over and lying down, a few dead and straw-coloured; sometimes flowering stalks with narrow seed heads."""
    gz = ground_z(x, y) - 0.012
    col_main = rng.choice([H_GRASS, H_GRASS, H_GRASS, H_GRASS_BLUE, H_GRASS_YEL])
    nb = rng.randint(9, 14) if lod == 0 else rng.randint(5, 7)
    rad = 0.02 + 0.05 * scale
    for _ in range(nb):
        a_ = rng.uniform(0, 2 * math.pi); off = rad * math.sqrt(rng.random())
        b0 = Vector((x + math.cos(a_) * off, y + math.sin(a_) * off, gz))
        ld = Vector((math.cos(a_ + rng.gauss(0, 0.6)), math.sin(a_ + rng.gauss(0, 0.6)), 0))
        if lean_bias is not None: ld = (ld + lean_bias * 0.8).normalized()
        hh = scale * rng.uniform(0.35, 1.05)
        lean = rng.uniform(0.05, 0.35) + (off / rad) * 0.35
        droop = rng.uniform(0.4, 1.5) * min(1.0, hh / 0.25)
        r_ = rng.random()
        col = col_main if r_ < 0.66 else (H_STRAW if r_ < 0.76 else rng.choice([H_GRASS, H_GRASS_BLUE, H_GRASS_YEL]))
        blade2(MB_HERB, b0, hh, rng.uniform(0.0035, 0.0065), ld, lean, droop, col, rng.uniform(-0.6, 0.6))
    if rng.random() < (0.3 if lod == 0 else 0.12):   # flowering stalks with a narrow seed head
        base = Vector((x, y, gz))
        for _ in range(rng.randint(1, 3)):
            ld = Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0)).normalized()
            hh = scale * rng.uniform(1.3, 2.0)
            tip = base + Vector((0, 0, hh)) + ld * hh * rng.uniform(0.05, 0.3)
            pts = [base, base.lerp(tip, 0.5) + ld * 0.02, tip]
            ribbon(MB_HERB, pts, [0.0012, 0.0010, 0.0008], H_GRASS_YEL, NH, v0=0.3, v1=0.9, tip=False)
            hd = (tip - pts[1]).normalized(); L = rng.uniform(0.05, 0.10)
            sd = hd.cross(Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0)).normalized()).normalized()
            ribbon(MB_HERB, [tip, tip + hd * L * 0.5, tip + hd * L], [0.0035, 0.0055, 0.0], H_SEED, NH, side=sd, v0=0.3, v1=1.0)
    CONTACT.append((x, y, rad * 2.2 + 0.05, 0.6 if lod == 0 else 0.45))

def fuzz(mb, x, y, rng, n, rad):
    """Short sward: single-triangle leaves 3-10 cm tall, thick round the reader's feet, so the ground has relief."""
    for _ in range(n):
        a_ = rng.uniform(0, 6.28); off = rad * math.sqrt(rng.random())
        px, py = x + math.cos(a_) * off, y + math.sin(a_) * off
        b0 = Vector((px, py, ground_z(px, py) - 0.006))
        ld = Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0)).normalized(); side = Vector((-ld.y, ld.x, 0))
        hh = rng.uniform(0.03, 0.10); w = rng.uniform(0.0025, 0.005)
        tip = b0 + Vector((0, 0, hh)) + ld * hh * rng.uniform(0.15, 0.8)
        col = rng.choice([H_GRASS, H_GRASS, H_GRASS_BLUE, H_GRASS_YEL, H_CLOVER, H_STRAW])
        iv = [mb.vert(b0 - side * w), mb.vert(b0 + side * w), mb.vert(tip)]
        mb.face(iv, [(col_u(col, NH, 0.0), 0.15), (col_u(col, NH, 1.0), 0.15), (col_u(col, NH, 0.5), rng.uniform(0.7, 0.95))], to_reader(tip))

def poppy_foliage(x, y, rng):
    """The poppies' own leafy floor in the field: a rosette of grey-green, pinnately lobed leaves arching up."""
    a0 = rng.uniform(0, 6.28); n = rng.randint(3, 5)
    for k in range(n):
        a_ = a0 + k * 2 * math.pi / n + rng.gauss(0, 0.3)
        lobed_leaf(MB_HERB, Vector((x, y, ground_z(x, y) - 0.005)), Vector((math.cos(a_), math.sin(a_), 0)), rng.uniform(0.10, 0.19), rng.uniform(0.016, 0.026), rng)
    CONTACT.append((x, y, 0.16, 0.45))

def plantain(x, y, rng):
    gz = ground_z(x, y) + 0.004
    c = Vector((x, y, gz)); n = rng.randint(4, 7); a0 = rng.uniform(0, 6.28)
    for k in range(n):
        a_ = a0 + k * 2 * math.pi / n + rng.gauss(0, 0.2); d = Vector((math.cos(a_), math.sin(a_), 0))
        L = rng.uniform(0.07, 0.14); lift = rng.uniform(0.1, 0.45)
        pts = [c, c + d * L * 0.4 + Vector((0, 0, L * lift * 0.5)), c + d * L * 0.85 + Vector((0, 0, L * lift * 0.6)), c + d * L + Vector((0, 0, L * lift * 0.4))]
        side = d.cross(Vector((0, 0, 1)))
        ribbon(MB_HERB, pts, [0.004, L * 0.22, L * 0.16, 0.0], H_BROAD, NH, side=side, toward=Vector((0, 0, 1)), v0=0.2, v1=1.0)
    CONTACT.append((x, y, 0.12, 0.35))

def clover_patch(x, y, rng):
    for _ in range(rng.randint(5, 10)):
        px, py = x + rng.gauss(0, 0.07), y + rng.gauss(0, 0.07)
        gz = ground_z(px, py); hgt = rng.uniform(0.03, 0.09)
        stem_top = Vector((px, py, gz + hgt))
        for k in range(3):
            a_ = rng.uniform(0, 6.28) + k * 2.09; d = Vector((math.cos(a_), math.sin(a_), 0.1))
            p0 = stem_top; p1 = stem_top + d * 0.012; p2 = stem_top + d * 0.022
            ribbon(MB_HERB, [p0, p1, p2], [0.002, 0.008, 0.0], H_CLOVER, NH, side=d.cross(Vector((0, 0, 1))).normalized(), toward=Vector((0, 0, 1)), v0=0.4, v1=1.0)
    CONTACT.append((x, y, 0.13, 0.3))

rng_g = random.Random(77)
space_g = Spacing(0.3)
def grass_density(x, y):
    r = math.hypot(x, y)
    if r < 0.32: return 0.0
    e, side = river_e(x, y)
    if e < 0.8: return 0.0
    v = 0.45 + 0.55 * clump(x, y, 0.9, 4.4)
    v *= 1.0 - 0.6 * smoothstep(0.0, 3.0, field_s(x, y))       # poppy foliage takes the ground in the field
    return v
def grass_scale(x, y):
    e, side = river_e(x, y)
    s = 0.34 + 0.14 * n2(x, y, 3.0, 1.9) + 0.18 * (1.0 - smoothstep(1.0, 4.0, e))   # lusher and longer near the water
    return max(0.14, s)
def downslope(x, y):
    n_ = ground_n(x, y)
    v = Vector((n_.x, n_.y, 0))
    return v.normalized() * min(1.0, v.length * 3) if v.length > 0.05 else None
near_g = scatter(rng_g, 0.3, 4.4, 14.0, grass_density, space_g, 0.14, 135)
mid_g = scatter(rng_g, 4.4, 9.5, 3.0, grass_density, space_g, 0.2, 95)
tg0 = MB_HERB.tris()
for (x, y) in near_g: tuft(x, y, rng_g, grass_scale(x, y), 0, downslope(x, y))
for (x, y) in mid_g: tuft(x, y, rng_g, grass_scale(x, y), 1, downslope(x, y))
tg1 = MB_HERB.tris()
rng_fz = random.Random(19); nfz = 0
for (x, y) in scatter(rng_fz, 0.15, 3.2, 30.0, lambda x, y: (1.0 - 0.6 * P(x, y)) * (0.4 + 0.6 * clump(x, y, 0.5, 6.6)) if river_e(x, y)[0] > 0.6 else 0.0, Spacing(0.2), 0.10, 250):
    fuzz(MB_HERB, x, y, rng_fz, 9, 0.09); nfz += 1
print(f"fuzz patches={nfz} tris={MB_HERB.tris() - tg1}")
tg1 = MB_HERB.tris()
for (x, y) in scatter(rng_g, 0.5, 7.5, 4.0, lambda x, y: smoothstep(0.15, 0.6, P(x, y)) * 0.9, space_g, 0.16, 95): poppy_foliage(x, y, rng_g)
print(f"poppy foliage tris={MB_HERB.tris() - tg1}")
for (x, y) in scatter(rng_g, 0.5, 3.5, 2.0, lambda x, y: (1.0 - P(x, y)) * 0.8, space_g, 0.2, 18): plantain(x, y, rng_g)
for (x, y) in scatter(rng_g, 0.5, 4.0, 0.8, lambda x, y: (1.0 - P(x, y)), space_g, 0.3, 10): clover_patch(x, y, rng_g)
print(f"grass tufts near={len(near_g)} mid={len(mid_g)} tris={tg1 - tg0}")

# ----------------------------------------------------------------------------- the other flowers: buttercup, ox-eye daisy, cornflower, knapweed
def small_flower(x, y, rng, kind, lod):
    gz = ground_z(x, y) - 0.01
    base = Vector((x, y, gz))
    h = rng.uniform(0.18, 0.55) if kind != F_BLUE else rng.uniform(0.30, 0.65)
    ld = Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0)).normalized()
    top = base + Vector((0, 0, h)) + ld * h * rng.uniform(0.02, 0.2)
    ribbon(MB_HERB, [base, top], [0.0018, 0.0012], H_GRASS, NH, v0=0.1, v1=0.8, tip=False)
    axis = (Vector((0, 0, 1)) + ld * rng.uniform(0.1, 0.6)).normalized()
    u = axis.orthogonal().normalized(); w = axis.cross(u)
    def ring(n, r, lift, ph=0.0): return [top + axis * lift + (u * math.cos(ph + k * 2 * math.pi / n) + w * math.sin(ph + k * 2 * math.pi / n)) * r for k in range(n)]
    mb = MB_FLOW
    if kind == F_YELLOW:      # buttercup: a glossy shallow cup of five petals
        R = rng.uniform(0.014, 0.020); rim = ring(5, R, R * 0.5)
        c0 = mb.vert(top); rv = [mb.vert(p) for p in rim]
        for k in range(5): mb.face([c0, rv[k], rv[(k + 1) % 5]], [(col_u(F_YELLOW, NM, 0.5), 0.05), (col_u(F_YELLOW, NM, 0.0), 0.95), (col_u(F_YELLOW, NM, 1.0), 0.95)], axis)
    elif kind == F_WHITE:     # ox-eye daisy: white ray petals round a raised yellow disc
        R = rng.uniform(0.026, 0.036); n = 8 if lod == 0 else 5; ph = rng.uniform(0, 1)
        for k in range(n):
            a_ = ph + k * 2 * math.pi / n; d = u * math.cos(a_) + w * math.sin(a_); lt = axis.cross(d) * R * 0.16
            p0 = top + d * R * 0.25 + axis * 0.002; p1 = top + d * R + axis * (-0.002)
            iv = [mb.vert(p0 - lt), mb.vert(p0 + lt), mb.vert(p1)]
            mb.face(iv, [(col_u(F_WHITE, NM, 0.0), 0.5), (col_u(F_WHITE, NM, 1.0), 0.5), (col_u(F_WHITE, NM, 0.5), 0.95)], axis)
        dr = ring(4, R * 0.28, 0.003, ph); c0 = mb.vert(top + axis * 0.006); dv = [mb.vert(p) for p in dr]
        for k in range(4): mb.face([c0, dv[k], dv[(k + 1) % 4]], [(col_u(F_DISC, NM, 0.5), 0.3), (col_u(F_DISC, NM, 0.0), 0.7), (col_u(F_DISC, NM, 1.0), 0.7)], axis)
    elif kind == F_BLUE:      # cornflower: a ragged ring of florets
        R = rng.uniform(0.017, 0.023); rim = ring(7, R, R * 0.35, rng.uniform(0, 1)); inn = ring(7, R * 0.45, R * 0.15)
        c0 = mb.vert(top); rv = [mb.vert(p + axis * (0.003 if k % 2 else 0.0)) for k, p in enumerate(rim)]
        for k in range(7): mb.face([c0, rv[k], rv[(k + 1) % 7]], [(col_u(F_BLUE, NM, 0.5), 0.1), (col_u(F_BLUE, NM, 0.0), 0.95), (col_u(F_BLUE, NM, 1.0), 0.95)], axis)
    else:                     # knapweed: a purple brush on a dark knob
        R = rng.uniform(0.011, 0.015); rim = ring(5, R, R * 0.9); c0 = mb.vert(top - axis * R * 0.5); t0 = mb.vert(top + axis * R * 1.4)
        rv = [mb.vert(p) for p in rim]
        for k in range(5):
            mb.face([c0, rv[k], rv[(k + 1) % 5]], [(col_u(F_PURPLE, NM, 0.5), 0.05), (col_u(F_PURPLE, NM, 0.0), 0.4), (col_u(F_PURPLE, NM, 1.0), 0.4)], (rim[k] - top))
            mb.face([rv[k], t0, rv[(k + 1) % 5]], [(col_u(F_PURPLE, NM, 0.0), 0.6), (col_u(F_PURPLE, NM, 0.5), 0.98), (col_u(F_PURPLE, NM, 1.0), 0.6)], (rim[k] - top))
    CONTACT.append((x, y, 0.05, 0.25))

rng_f = random.Random(93)
def meadow_density(x, y):
    if math.hypot(x, y) < 0.5: return 0.0
    return B(x, y) * clump(x, y, 0.8, 7.7)
kinds = [F_YELLOW, F_YELLOW, F_YELLOW, F_WHITE, F_WHITE, F_BLUE, F_PURPLE]
mf_near = scatter(rng_f, 0.5, 5.0, 34.0, meadow_density, space_p, 0.08, 300)
mf_mid = scatter(rng_f, 5.0, 8.0, 10.0, meadow_density, space_p, 0.13, 60)
for (x, y) in mf_near:
    k = kinds[int(abs(n2(x, y, 1.1, 3.3)) * 9 + rng_f.random() * 2.5) % len(kinds)]
    small_flower(x, y, rng_f, k, 0)
for (x, y) in mf_mid:
    k = kinds[int(abs(n2(x, y, 1.1, 3.3)) * 9 + rng_f.random() * 2.5) % len(kinds)]
    small_flower(x, y, rng_f, k, 1)
print(f"meadow flowers near={len(mf_near)} mid={len(mf_mid)} tris={MB_FLOW.tris()}")

# ----------------------------------------------------------------------------- the water's edge: reeds, rushes, loosestrife, stones
def reed_clump(x, y, rng):
    gz = ground_z(x, y) - 0.03
    base = Vector((x, y, gz)); n = rng.randint(6, 12)
    for _ in range(n):
        a_ = rng.uniform(0, 6.28); off = rng.uniform(0, 0.12)
        b0 = base + Vector((math.cos(a_) * off, math.sin(a_) * off, 0))
        ld = Vector((math.cos(a_), math.sin(a_), 0)); hh = rng.uniform(0.7, 1.5)
        blade2(MB_HERB, b0, hh, rng.uniform(0.004, 0.007), ld, rng.uniform(0.02, 0.18), rng.uniform(0.1, 0.5), H_REED, rng.uniform(-0.5, 0.5))
    if rng.random() < 0.45:     # a bulrush head or two
        for _ in range(rng.randint(1, 2)):
            ld = Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0)).normalized(); hh = rng.uniform(1.1, 1.6)
            tip = base + Vector((0, 0, hh)) + ld * 0.06
            ribbon(MB_HERB, [base, base.lerp(tip, 0.5), tip], [0.003, 0.0025, 0.002], H_REED, NH, v0=0.2, v1=0.7, tip=False)
            hd = (tip - base).normalized(); c = tip - hd * 0.12
            for k in range(3):
                sd = hd.cross(Vector((math.cos(k * 2.1), math.sin(k * 2.1), 0))).normalized()
                ribbon(MB_HERB, [c - hd * 0.06, c, c + hd * 0.06], [0.009, 0.011, 0.008], H_SEED, NH, side=sd, v0=0.02, v1=0.25, tip=False)
    CONTACT.append((x, y, 0.2, 0.5))

def loosestrife(x, y, rng):
    gz = ground_z(x, y) - 0.02
    base = Vector((x, y, gz)); hh = rng.uniform(0.6, 1.0); ld = Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0)).normalized()
    top = base + Vector((0, 0, hh)) + ld * 0.05
    ribbon(MB_HERB, [base, base.lerp(top, 0.6), top], [0.003, 0.0025, 0.002], H_POPPY, NH, v0=0.1, v1=0.6, tip=False)
    sp0 = base.lerp(top, 0.62)
    for k in range(2):
        sd = Vector((1, 0, 0)) if k == 0 else Vector((0, 1, 0))
        ribbon(MB_FLOW, [sp0, sp0.lerp(top, 0.5), top + Vector((0, 0, 0.03))], [0.012, 0.010, 0.0], F_LOOSE, NM, side=sd, v0=0.2, v1=1.0)

rng_r = random.Random(55)
reeds = []
y = -26.0
while y < 30.0:
    y += rng_r.uniform(0.35, 1.9)
    xe = river_x(y) - rw(y) + rng_r.uniform(-0.25, 0.55)   # just in the water to the top of the muddy shelf
    if math.hypot(xe, y) > 26: continue
    if rng_r.random() < 0.12: continue                     # gaps where the bank is open
    reed_clump(xe, y, rng_r); reeds.append((xe, y))
    if rng_r.random() < 0.3: loosestrife(xe + rng_r.uniform(0.2, 0.6), y + rng_r.uniform(-0.4, 0.4), rng_r)
print(f"reed clumps={len(reeds)} herbage tris now={MB_HERB.tris()}")

def rock(name, loc, size, rng, mat, sink=0.45, squash=0.55):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    off = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
    for v in bm.verts:
        d = v.co.normalized()
        rr = 1.0 + 0.22 * noise.noise(d * 1.6 + off) + 0.06 * noise.noise(d * 5.0 + off)
        v.co = Vector((d.x * rr * size[0], d.y * rr * size[1], d.z * rr * size[2] * squash))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    o.location = (loc[0], loc[1], ground_z(loc[0], loc[1]) - size[2] * squash * sink)
    o.rotation_euler = (rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), rng.uniform(0, 6.28))
    for p in me.polygons: p.use_smooth = True
    CONTACT.append((loc[0], loc[1], max(size[0], size[1]) * 1.3, 0.55))
    return link(o)

M_STONE = stone_mat()
for k, (yy, dx, s) in enumerate([(-3.2, -0.1, 0.32), (-2.5, 0.35, 0.18), (1.8, 0.1, 0.24), (6.4, -0.2, 0.38), (7.0, 0.5, 0.16), (-9.5, 0.2, 0.3), (12.5, 0.0, 0.28)]):
    xx = river_x(yy) - rw(yy) + dx
    rock(f"Stone{k}", (xx, yy), (s * rng_r.uniform(0.9, 1.4), s * rng_r.uniform(0.8, 1.1), s), rng_r, M_STONE)
rock("StoneBank0", (-1.1, -1.6), (0.16, 0.12, 0.12), rng_r, M_STONE, sink=0.6)     # an old field stone in the grass, half sunk

# ----------------------------------------------------------------------------- trees: fruit trees on the near bank, alders and willows across the river
M_BARK = bark_mat(); M_LEAVES = leaves_mat(); M_SHADE = leaves_shade_mat()
def tube(name, pts, radii, mat, sides=8, caps=True):
    """A tube along a polyline, parallel-transported frames (from build_queens_croquet_ground.py)."""
    pts = [Vector(p) for p in pts]
    if not isinstance(radii, (list, tuple)): radii = [radii] * len(pts)
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rings = []; u_prev = None
    for i, p in enumerate(pts):
        if i == 0: d = pts[1] - p
        elif i == len(pts) - 1: d = p - pts[i - 1]
        else: d = pts[i + 1] - pts[i - 1]
        d.normalize()
        if u_prev is None:
            ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
            u = d.cross(ref).normalized()
        else:
            u = (u_prev - d * u_prev.dot(d)).normalized()
        v = d.cross(u); u_prev = u
        rings.append([bm.verts.new(p + (u * math.cos(2 * math.pi * k / sides) + v * math.sin(2 * math.pi * k / sides)) * radii[i]) for k in range(sides)])
    for a, b_ in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b_[j], b_[k]))
    if caps: bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def blob(name, r, loc, mat, subdiv=2, amp=0.22, freq=1.8, scale=(1, 1, 1), seed=0.0, flat_bottom=None, jag=0.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    off = Vector((seed * 7.31, seed * 3.17, seed * 5.53)); sc = Vector(scale)
    for v in bm.verts:
        d = v.co.normalized()
        rr = r * (1.0 + amp * noise.noise(d * freq + off) + amp * 0.45 * noise.noise(d * freq * 3.1 + off) + jag * noise.noise(d * 9.7 + off * 1.3))
        p = d * rr; p = Vector((p.x * sc.x, p.y * sc.y, p.z * sc.z))
        if flat_bottom is not None and p.z < flat_bottom: p.z = flat_bottom + (p.z - flat_bottom) * 0.25
        v.co = p
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat); o.location = loc
    for p in me.polygons: p.use_smooth = True
    return link(o)

def crown(name, c, r, rng, subdiv=2, scale=(1, 1, 1), flat=0.45, droop=0.0, n=14, mat=None, chip=None, core_mat=None):
    """A leafy crown without alpha cards: a dark core mass (so the sky never shows through the middle) and a cloud of
    n small irregular leaf chips (tetrahedra, 4 triangles) packed towards the crown's surface, thicker on the sunlit
    upper side, with gaps between them at the edge so the silhouette is broken and sky shows through. Normals are
    bent towards the crown's own centre, the usual foliage trick, so the whole crown shades as one soft volume
    (lit side, shaded side) while each chip still flickers a little. Willows trail strands of chips downwards."""
    mat = mat or M_LEAVES; sc = Vector(scale)
    rx, ry, rz = r * sc.x, r * sc.y, r * sc.z
    chip = chip or r * 0.12
    verts, faces, nrm = [], [], []
    def radial(p):
        q = Vector(((p.x - c.x) / rx ** 2, (p.y - c.y) / ry ** 2, (p.z - c.z) / rz ** 2))
        return q.normalized() if q.length > 1e-9 else Vector((0, 0, 1))
    # core: an icosphere, a little inside the shell, flattened underneath
    cb = bmesh.new(); bmesh.ops.create_icosphere(cb, subdivisions=subdiv, radius=1.0)
    off = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
    base_i = len(verts)
    for v in cb.verts:
        d = v.co.normalized(); k = 0.84 + 0.10 * noise.noise(d * 2.5 + off)
        p = c + Vector((d.x * rx * k, d.y * ry * k, d.z * rz * k))
        if p.z < c.z - rz * flat: p.z = c.z - rz * flat + (p.z - (c.z - rz * flat)) * 0.3
        verts.append(p); nrm.append(radial(p))
    for f_ in cb.faces: faces.append(tuple(base_i + v.index for v in f_.verts))
    cb.free()
    cme = bpy.data.meshes.new(name + "_Core"); cme.from_pydata([tuple(v) for v in verts], [], faces)
    cme.polygons.foreach_set("use_smooth", [True] * len(cme.polygons)); cme.normals_split_custom_set_from_vertices([tuple(n_) for n_ in nrm])
    co_ = bpy.data.objects.new(name + "_Core", cme); cme.materials.append(core_mat or M_SHADE); link(co_)
    verts, faces, nrm = [], [], []
    sun = Vector((SUN_DIR.x, SUN_DIR.y, max(0.3, SUN_DIR.z))).normalized()
    placed = 0; tries = 0
    while placed < n and tries < n * 6:
        tries += 1
        d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
        if d.z < -flat * 1.2 and rng.random() < 0.8: continue
        if rng.random() > 0.55 + 0.45 * max(0.0, d.dot(sun) * 0.5 + d.z * 0.5): continue
        f = rng.uniform(0.86, 1.08)
        p = c + Vector((d.x * rx * f, d.y * ry * f, d.z * rz * f))
        if droop and d.z < 0.3 and rng.random() < 0.5:
            p.z -= droop * rz * rng.uniform(0.2, 1.0)
        n_out = radial(p)
        t1 = n_out.orthogonal().normalized(); t2 = n_out.cross(t1)
        s_ = chip * rng.uniform(0.7, 1.3); th = rng.uniform(0, 6.28)
        tilt = Vector((rng.gauss(0, 0.35), rng.gauss(0, 0.35), 0))
        b0 = len(verts)
        for k in range(3):
            a_ = th + k * 2.094 + rng.gauss(0, 0.25)
            q = p + (t1 * math.cos(a_) + t2 * math.sin(a_)) * s_ * rng.uniform(0.75, 1.15) + n_out * s_ * (tilt.x * math.cos(a_) + tilt.y * math.sin(a_))
            verts.append(q); nrm.append((radial(q) * 0.85 + n_out * 0.15).normalized())
        tri = [b0, b0 + 1, b0 + 2]
        n_ = (verts[tri[1]] - verts[tri[0]]).cross(verts[tri[2]] - verts[tri[0]])
        if n_.dot(n_out) < 0: tri.reverse()
        faces.append(tuple(tri))
        placed += 1
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.normals_split_custom_set_from_vertices([tuple(n_) for n_ in nrm])
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

def tree(name, x, y, height, crown_r, rng, kind="fruit", nblobs=6, subdiv=2, fruit=0):
    gz = ground_z(x, y)
    base = Vector((x, y, gz - 0.25))
    lean = Vector((rng.gauss(0, 0.12), rng.gauss(0, 0.12), 1.0)).normalized()
    if kind == "fruit": fork_h = height * rng.uniform(0.28, 0.36)
    else: fork_h = height * rng.uniform(0.38, 0.5)
    fork = base + lean * (fork_h + 0.25)
    r0 = 0.10 + 0.018 * height
    tube(f"{name}_Trunk", [base, base.lerp(fork, 0.35) + Vector((rng.gauss(0, 0.04), rng.gauss(0, 0.04), 0)), base.lerp(fork, 0.7), fork], [r0 * 1.25, r0, r0 * 0.9, r0 * 0.8], M_BARK, sides=7 if kind == "fruit" else 6)
    # root flare: a few roots running into the ground
    for k in range(4 if kind == "fruit" else 3 if kind != "bush" else 0):
        a_ = rng.uniform(0, 6.28) + k * 1.57; d = Vector((math.cos(a_), math.sin(a_), 0))
        p0 = base + Vector((0, 0, 0.42)) + d * r0 * 0.6; p1 = Vector((x, y, 0)) + d * r0 * 2.6; p1.z = ground_z(p1.x, p1.y) - 0.02
        p2 = Vector((x, y, 0)) + d * r0 * 4.5; p2.z = ground_z(p2.x, p2.y) - 0.07
        tube(f"{name}_Root{k}", [p0, p1, p2], [r0 * 0.45, r0 * 0.28, r0 * 0.12], M_BARK, sides=4, caps=False)
    CONTACT.append((x, y, crown_r * 0.9, 0.55))
    CONTACT.append((x, y, r0 * 5, 0.7))
    crown_c = base + lean * (height * (0.66 if kind == "fruit" else 0.58 if kind != "bush" else 0.55)) + Vector((0, 0, 0.25))
    ch = height - fork_h
    surf_pts = []
    nl = rng.randint(3, 4) if kind != "bush" else 0
    for k in range(nl):
        a_ = k * 2 * math.pi / nl + rng.uniform(-0.4, 0.4)
        d = Vector((math.cos(a_), math.sin(a_), 0))
        end = crown_c + d * crown_r * rng.uniform(0.45, 0.75) + Vector((0, 0, ch * rng.uniform(0.0, 0.3)))
        mid = fork.lerp(end, 0.5) + d * crown_r * 0.1 + Vector((0, 0, 0.1))
        tube(f"{name}_Limb{k}", [fork, mid, end], [r0 * 0.6, r0 * 0.42, r0 * 0.2], M_BARK, sides=4, caps=False)
    zsc = 0.78 if kind == "fruit" else (1.3 if kind == "willow" else 0.8 if kind == "bush" else 1.3)
    crown(f"{name}_Crown", crown_c, crown_r, rng, subdiv=subdiv, scale=(1.0, 1.0, zsc), flat=0.45 if kind != "willow" else 0.9,
          droop=0.6 if kind == "willow" else 0.0, n=nblobs)
    surf_pts = [(crown_c + Vector((0, 0, -crown_r * 0.1)), crown_r * 0.95)]
    for k in range(1 if kind in ("alder", "willow") else 0):      # a second, lower crown mass on the big trees
        a_ = rng.uniform(0, 6.28)
        c2 = crown_c + Vector((math.cos(a_) * crown_r * 0.7, math.sin(a_) * crown_r * 0.7, -ch * 0.25))
        crown(f"{name}_Crown2", c2, crown_r * 0.62, rng, subdiv=subdiv, scale=(1.0, 1.0, zsc), flat=0.4, n=nblobs // 3, chip=crown_r * 0.62 * 0.13)
    # fruit: plums and peaches among the leaves (the travellers breakfasted off them)
    for k in range(fruit):
        c, sz = rng.choice(surf_pts)
        a_ = rng.uniform(0, 6.28); el = rng.uniform(-0.8, 0.2)
        d = Vector((math.cos(a_) * math.cos(el), math.sin(a_) * math.cos(el), math.sin(el)))
        p = c + d * sz * 0.98; fr = 0.028; colf = F_PLUM if kind == "plum" or (kind == "fruit" and k % 2) else F_PEACH
        u = Vector((1, 0, 0)); w = Vector((0, 1, 0)); up = Vector((0, 0, 1))
        pts = [p + up * fr, p - up * fr, p + u * fr, p - u * fr, p + w * fr, p - w * fr]
        iv = [MB_FLOW.vert(q) for q in pts]
        for (i0, i1, i2) in ((0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2), (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5)):
            MB_FLOW.face([iv[i0], iv[i1], iv[i2]], [(col_u(colf, NM, 0.5), 0.9), (col_u(colf, NM, 0.0), 0.6), (col_u(colf, NM, 1.0), 0.6)], (pts[i0] + pts[i1] + pts[i2]) / 3 - p)

rng_t = random.Random(12)
# near bank: the fruit trees beside the river
tree("FruitTreeAhead", 3.6, 9.6, 4.2, 1.55, rng_t, "fruit", 1000, 3, fruit=12)
tree("FruitTreeBehind", 2.4, -5.8, 4.2, 1.8, rng_t, "fruit", 1150, 3, fruit=14)
tree("FruitTreeFar", -7.5, -15.5, 5.0, 2.2, rng_t, "fruit", 400, 2, fruit=0)
tree("FruitTreeUp", 1.6, -16.5, 4.4, 1.9, rng_t, "fruit", 360, 2)
# across the river: alders and willows along the far bank, irregular in size and spacing
FAR_BANK = [(-24.0, 1.5, 9.0, 3.4, "alder", 300), (-20.0, 4.5, 7.0, 2.6, "alder", 230), (-11.0, 0.6, 5.0, 2.8, "willow", 300),
            (-2.0, 2.8, 10.5, 3.6, "alder", 340), (3.5, 0.5, 2.6, 1.6, "bush", 150), (5.5, 0.9, 1.9, 1.2, "bush", 100), (8.0, 1.4, 6.5, 3.0, "willow", 320),
            (17.0, 3.0, 9.0, 3.2, "alder", 300), (21.0, 6.5, 11.0, 3.6, "alder", 300), (-15.5, 0.4, 2.2, 1.5, "bush", 100)]
for k, (yy, dx, hh, cr, kind, nc) in enumerate(FAR_BANK):
    xx = river_x(yy) + RW + dx
    tree(f"FarBankTree{k}", xx, yy, hh, cr, rng_t, kind, nc, 2)

# ----------------------------------------------------------------------------- the river surface
def water_strip(name, mat):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rows = []; ys = []
    y = -110.0
    while y <= 110.0:
        ys.append(y); y += 0.8 + abs(y) * 0.06
    for y in ys:
        xc = river_x(y); half = RW + 1.6
        rows.append((bm.verts.new((xc - half, y, WATER_Z)), bm.verts.new((xc + half, y, WATER_Z))))
    def vv(y): return 0.5 + 0.5 * math.copysign(math.log(1 + abs(y) / 4.0) / math.log(1 + 110 / 4.0), y)
    for (a, b_), ya, yb in zip(zip(rows, rows[1:]), ys, ys[1:]):
        if math.hypot(river_x(ya), ya) > TERRAIN_R - 6 and math.hypot(river_x(yb), yb) > TERRAIN_R - 6: continue
        f_ = bm.faces.new((a[0], a[1], b_[1], b_[0]))
        for l, uv in zip(f_.loops, [(0.02, vv(ya)), (0.98, vv(ya)), (0.98, vv(yb)), (0.02, vv(yb))]): l[uvl].uv = uv
    bm.normal_update()
    for f_ in bm.faces:
        if f_.normal.z < 0: f_.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)
M_WATER = water_mat()
water_strip("River", M_WATER)

# ----------------------------------------------------------------------------- far copses (backdrop, merged into far.treeline)
M_FARTREES = far_trees_mat()
rng_ft = random.Random(5)
def copse(name, x, y, n, rng):
    """A copse far off on the meadow: a few lumpy crowns standing together, hazed by distance (backdrop)."""
    for k in range(n):
        px, py = x + rng.gauss(0, 2.4), y + rng.gauss(0, 2.4)
        r_ = rng.uniform(2.4, 4.4); zs = rng.uniform(1.0, 1.5); gz = ground_z(px, py)
        lift = rng.uniform(1.2, 2.6)
        cz = gz + lift + r_ * zs * 0.7
        tube(f"{name}_{k}_Trunk", [(px, py, gz - 0.5), (px + rng.gauss(0, 0.2), py + rng.gauss(0, 0.2), cz)], [0.25, 0.16], M_FARTREES, sides=4, caps=False)
        crown(f"{name}_{k}", Vector((px, py, cz)), r_, rng, subdiv=2, scale=(1.0, 1.0, zs), flat=0.7, n=75,
              mat=M_FARTREES, chip=r_ * 0.2, core_mat=M_FARTREES)
COPSES = [(river_x(55) + 30, 55, 3), (river_x(-5) + 44, -5, 3), (river_x(-40) + 40, -40, 3), (river_x(-70) + 25, -70, 2),
          (-35, -82, 2), (-70, -50, 3), (-88, 10, 2), (40, 92, 2)]
for k, (cx_, cy_, n_) in enumerate(COPSES):
    if math.hypot(cx_, cy_) < TERRAIN_R - 8: copse(f"far.copse{k}", cx_, cy_, n_, rng_ft)
for o in COLL.objects:
    if o.name.startswith("far.copse"): o.visible_shadow = False

# ----------------------------------------------------------------------------- build the card meshes
MB_PETAL.build(); MB_HERB.build(); MB_FLOW.build()

# ----------------------------------------------------------------------------- the maps the ground shaders read (generated here, never downloaded)
def make_density(extent, res):
    arr = np.zeros((res, res, 4), np.float32)
    for j in range(res):
        yy = -extent + (j + 0.5) / res * 2 * extent
        for i in range(res):
            xx = -extent + (i + 0.5) / res * 2 * extent
            arr[j, i, 0] = P(xx, yy); arr[j, i, 2] = B(xx, yy)
    arr[..., 3] = 1.0
    return arr

def float_image(name, arr):
    res_y, res_x = arr.shape[:2]
    img = bpy.data.images.new(name, res_x, res_y, alpha=True, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(arr.ravel()); img.pack()
    return img

def make_contact(extent, res):
    C = np.zeros((res, res), np.float32)
    for (x, y, rad, s) in CONTACT:
        px = (x + extent) / (2 * extent) * res; py = (y + extent) / (2 * extent) * res; rp = rad / (2 * extent) * res
        r3 = max(1.5, rp * 1.6)
        i0, i1 = int(max(0, px - r3)), int(min(res, px + r3 + 1)); j0, j1 = int(max(0, py - r3)), int(min(res, py + r3 + 1))
        if i0 >= i1 or j0 >= j1: continue
        xs = np.arange(i0, i1) + 0.5 - px; ys = np.arange(j0, j1) + 0.5 - py
        g = np.exp(-(xs[None, :] ** 2 + ys[:, None] ** 2) / max(0.6, rp * rp * 0.5)) * s
        C[j0:j1, i0:i1] = 1.0 - (1.0 - C[j0:j1, i0:i1]) * (1.0 - g)
    arr = np.zeros((res, res, 4), np.float32); arr[..., 1] = C; arr[..., 3] = 1.0
    return arr

DENS_NEAR = float_image("PF_DensityNear", make_density(NEAR_R, 192))
DENS_FAR = float_image("PF_DensityFar", make_density(TERRAIN_R + 2, 160))
CONTACT_IMG = float_image("PF_Contact", make_contact(NEAR_R, 2048))
print("contact stamps", len(CONTACT))

M_GROUND = ground_mat(DENS_NEAR, CONTACT_IMG); GROUND.data.materials.append(M_GROUND)
M_FAR = far_ground_mat(DENS_FAR); FAR.data.materials.append(M_FAR)

# ----------------------------------------------------------------------------- the sky dome
M_SKY = sky_dome_mat()
def sky_dome(name, radius=SKY_R, seg=48, rings=14, el_min=-12.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    # rings packed towards the horizon, where the far hills and clouds are
    els = [el_min + (89.0 - el_min) * (j / rings) ** 1.6 for j in range(rings + 1)]
    grid = []
    for el in els:
        e = math.radians(el)
        grid.append([bm.verts.new((radius * math.cos(e) * math.cos(2 * math.pi * i / seg), radius * math.cos(e) * math.sin(2 * math.pi * i / seg), radius * math.sin(e))) for i in range(seg)])
    pole = bm.verts.new((0, 0, radius))
    def v_of(el):
        # more texture rows near the horizon: v = sqrt-ish of elevation
        t = (el - el_min) / (90.0 - el_min); return t ** 0.6
    for j in range(rings):
        for i in range(seg):
            k = (i + 1) % seg
            f_ = bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][k], grid[j][k]))
            u0, u1 = i / seg, (i + 1) / seg
            for l, uv in zip(f_.loops, [(u0, v_of(els[j])), (u0, v_of(els[j + 1])), (u1, v_of(els[j + 1])), (u1, v_of(els[j]))]): l[uvl].uv = uv
    for i in range(seg):
        k = (i + 1) % seg
        f_ = bm.faces.new((grid[-1][i], pole, grid[-1][k]))
        for l, uv in zip(f_.loops, [(i / seg, v_of(els[-1])), ((i + 0.5) / seg, 1.0), ((i + 1) / seg, v_of(els[-1]))]): l[uvl].uv = uv
    bm.normal_update()
    for f_ in bm.faces:
        if f_.normal.dot(f_.calc_center_median()) > 0: f_.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_SKY)
    for p in me.polygons: p.use_smooth = True
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False; o.visible_transmission = False; o.visible_volume_scatter = False
    return link(o)
sky = sky_dome("SkyDome")

# ----------------------------------------------------------------------------- lights (manifest light ids)
def light_obj(name, kind, energy, color, loc, direction=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if direction is not None: lo.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return link(lo)
light_obj("light.sun", 'SUN', 5.0, (1.0, 0.82, 0.60), tuple(SUN_DIR * 20), direction=-SUN_DIR, angle=math.radians(1.5))
sky_l = light_obj("light.sky", 'SUN', 0.35, (0.62, 0.74, 1.0), (0, 0, 20), direction=(0.2, 0.1, -1.0), angle=math.radians(70))
sky_l.data.use_shadow = False

# world: a physical sky for the render's ambient light (Unity gets the SkyDome mesh and its own ambient)
world = bpy.data.worlds.new("Afternoon"); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]
sk = wn.nodes.new("ShaderNodeTexSky")
try: sk.sky_type = 'MULTIPLE_SCATTERING'
except Exception: sk.sky_type = 'SINGLE_SCATTERING'
try: sk.sun_disc = False
except Exception: pass
sk.sun_elevation = math.asin(SUN_DIR.z); sk.sun_rotation = math.atan2(SUN_DIR.y, SUN_DIR.x) - math.pi / 2
try: sk.air_density = 1.0; sk.aerosol_density = 1.8
except Exception: pass
wn.links.new(sk.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.16

# ----------------------------------------------------------------------------- anchors
def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e
anchor("reader.entrance", (0.0, 0.0, 0.0))
look = anchor("reader.look", (0.0, 1.0, EYE))
anchor("scene.centre", (-2.5, 6.0, ground_z(-2.5, 6.0)))
anchor("poppies.field", (-6.0, 3.0, ground_z(-6.0, 3.0)))
anchor("river.bank", (river_x(0.0) - rw(0.0) + 0.4, 0.0, ground_z(river_x(0.0) - rw(0.0) + 0.4, 0.0)))

# apply every transform so object space == world space (the procedural materials then bake exactly as rendered)
bpy.ops.object.select_all(action='DESELECT')
for o in COLL.objects:
    if o.type == 'MESH': o.select_set(True); bpy.context.view_layer.objects.active = o
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.select_all(action='DESELECT')

# ----------------------------------------------------------------------------- cameras (reader eye 1.55 m)
def camera(name, loc, look_at, lens=18):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 150
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co
E = (0.0, 0.0, EYE)
cams = [
    camera("Cam_Reader", E, (0.0, 10.0, EYE - 0.9), lens=17),
    camera("Cam_Left", E, (-10.0, 1.5, EYE - 1.2), lens=17),
    camera("Cam_Right", E, (10.0, 0.5, EYE - 2.0), lens=17),
    camera("Cam_Behind", E, (1.0, -10.0, EYE - 1.0), lens=17),
    camera("Cam_Down", E, (-0.2, 1.4, 0.0), lens=20),
    camera("Cam_Field", (-0.3, 0.3, 1.35), (-2.3, 1.9, 0.30), lens=30),
    camera("Cam_Bank", (1.6, 0.3, 1.45), (4.8, 1.6, -1.1), lens=22),
]
EXPOSURE = {}

if args.bake or args.export or not args.render:      # render-only runs (captures) write stills only
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "poppy_field_source.blend"))

def page_overlay(path, cam):
    """Outline the reading page (0.4 x 0.55 m, 0.6 m ahead at eye height) on the reader still, to judge what is behind it."""
    from bpy_extras.object_utils import world_to_camera_view
    img = bpy.data.images.load(path); w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
    c = Vector((0.0, 0.6, EYE))
    corners = [c + Vector((sx * 0.2, 0, sz * 0.275)) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    pts = [world_to_camera_view(scene, cam, p) for p in corners]
    for a, b_ in zip(pts, pts[1:] + pts[:1]):
        for t in np.linspace(0, 1, 2000):
            x = int((a.x + (b_.x - a.x) * t) * w); y = int((a.y + (b_.y - a.y) * t) * h)
            if 0 <= x < w and 0 <= y < h: px[max(0, y - 1):y + 2, max(0, x - 1):x + 2, :3] = (1.0, 1.0, 1.0)
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path.replace(".png", "_page.png"); img.file_format = 'PNG'; img.save()

if args.render:
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    want = set(c.strip() for c in args.cams.split(",") if c.strip())
    for c in cams:
        if want and c.name[4:].lower() not in want: continue
        scene.camera = c
        scene.view_settings.exposure = EXPOSURE.get(c.name, 0.0)
        scene.render.filepath = os.path.join(OUT, f"{args.prefix}{c.name[4:].lower()}.png")
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:      # the GPU is shared with other jobs: fall back to the CPU
            print("GPU render failed, CPU fallback:", str(e)[:120]); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)
        if c.name == "Cam_Reader":
            try: page_overlay(scene.render.filepath, c)
            except Exception as e: print("page overlay failed", e)

# ----------------------------------------------------------------------------- bake + merge + export for Unity
def tri_count(o):
    o.data.calc_loop_triangles(); return len(o.data.loop_triangles)

KEEP_NAMES = {"M_SkyDome": "SkyDome", "M_DistantMeadow": "far.meadow", "M_DistantTrees": "far.treeline"}   # backdrop meshes keep the names Unity looks for
KEEP_UV = {"M_SkyDome", "M_DistantMeadow", "M_Ground", "M_Water", "M_PoppyPetal", "M_Herbage", "M_MeadowFlowers"}   # hand-made UVs
PALETTE = {"M_PoppyPetal", "M_Herbage", "M_MeadowFlowers"}      # UV-only colour: base colour + roughness, no normal map

def patch_sun_intensities(gltf_path):
    """Blender 5.2.3's glTF exporter writes every SUN light at strength 1 whatever its energy (see the croquet ground)."""
    import json
    want = {o.name: o.data.energy * 683.0 for o in COLL.objects if o.type == 'LIGHT' and o.data.type == 'SUN'}
    with open(gltf_path) as f: g = json.load(f)
    for l in g.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", []):
        if l.get("type") == "directional" and l.get("name") in want: l["intensity"] = want[l["name"]]
    with open(gltf_path, "w") as f: json.dump(g, f, indent=1)
    print("patched sun intensities (lux)", want)

def bake_and_export():
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.select_all(action='DESELECT')
    groups = {}
    for o in COLL.objects:
        if o.type != 'MESH' or not o.data.materials: continue
        groups.setdefault(o.data.materials[0].name, []).append(o)
    merged = []
    for mname, objs in groups.items():
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active; o.name = KEEP_NAMES.get(mname, "MESH_" + mname[2:])
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    # 1-sample bakes on the CPU (the croquet ground found Metal kernel compiles crashing mid-bake in 5.2.3)
    scene.cycles.samples = 1; scene.cycles.device = 'CPU'
    scene.render.bake.margin = 6
    T_ = args.tex
    size_for = {"M_Ground": (min(4096, T_ * 2), T_, T_), "M_DistantMeadow": (T_, T_ // 2, T_ // 2), "M_SkyDome": (T_,),
                "M_TreeLeaves": (T_, T_ // 2, T_), "M_Bark": (T_ // 2, T_ // 4, T_ // 2), "M_Water": (T_ // 2, T_ // 4, T_ // 2),
                "M_DistantTrees": (T_ // 2, T_ // 4, T_ // 4), "M_BankStone": (T_ // 4, T_ // 4, T_ // 4),
                "M_PoppyPetal": (T_ // 4, T_ // 8), "M_Herbage": (T_ // 4, T_ // 8), "M_MeadowFlowers": (T_ // 8, T_ // 16)}
    tex_sizes = {}
    for o in merged:
        m = o.data.materials[0]; nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        sizes = size_for.get(m.name, (T_ // 4, T_ // 4, T_ // 4))
        tex_sizes[o.name] = sizes[0]
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        if m.name not in KEEP_UV or not o.data.uv_layers:
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
            bpy.ops.object.mode_set(mode='OBJECT')
        passes = [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]
        if m.name in PALETTE: passes = passes[:2]
        if o.name == "SkyDome": passes = [("BaseColor", 'EMIT', {}, False)]
        baked = {}
        for (pass_name, btype, extra, noncolor), size in zip(passes, sizes):
            size = max(64, size)
            img = bpy.data.images.new(f"T_{m.name[2:]}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            for n in nt.nodes: n.select = False
            tex.select = True; nt.nodes.active = tex
            bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            img.filepath_raw = os.path.join(OUT, "textures", img.name + ".png"); os.makedirs(os.path.dirname(img.filepath_raw), exist_ok=True)
            img.file_format = 'PNG'; img.save(); img.pack()
            baked[pass_name] = tex
            print("baked", img.name, size, flush=True)
        metallic = bsdf.inputs["Metallic"].default_value
        rough_v = bsdf.inputs["Roughness"].default_value
        for n in list(nt.nodes):
            if n not in baked.values(): nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
        nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Base Color"])
        if "Roughness" in baked: nt.links.new(baked["Roughness"].outputs["Color"], nb.inputs["Roughness"])
        else: nb.inputs["Roughness"].default_value = rough_v
        if "Normal" in baked:
            nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(baked["Normal"].outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], nb.inputs["Normal"])
        nb.inputs["Metallic"].default_value = metallic
        if o.name == "SkyDome":
            nb.inputs["Emission Strength"].default_value = 1.0; nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"])
    for c in cams: bpy.data.objects.remove(c)
    gl = os.path.join(OUT, "poppy_field.gltf")
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False)
    patch_sun_intensities(gl)
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={tex_sizes.get(o.name, 0)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "poppy_field_baked.blend"))

# pre-export budget (printed every run so the budget is visible while iterating)
_dg = bpy.context.evaluated_depsgraph_get(); _cat = {}
for _o in [o for o in COLL.objects if o.type == 'MESH']:
    _e = _o.evaluated_get(_dg); _me = _e.to_mesh(); _t = sum(len(p.vertices) - 2 for p in _me.polygons); _e.to_mesh_clear()
    _k = _o.data.materials[0].name if _o.data.materials else "?"
    _cat[_k] = _cat.get(_k, 0) + _t
print(f"PRE-MERGE materials={len(_cat)} tris={sum(_cat.values())}")
for _k, _v in sorted(_cat.items(), key=lambda kv: -kv[1]): print(f"  BUDGET {_k:24s} {_v}")

if args.bake or args.export:
    bake_and_export()
print("DONE")
