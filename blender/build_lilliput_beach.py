"""
Fable: Lilliput, by the shore (Gulliver's Travels, Part I, chapters I-II), seen at Gulliver's size. The reader is the
"great man-mountain" standing among six-inch people; everything in the country is built at one twelfth of ordinary
size, and only the reader is human size. No person or animal is modelled (no Lilliputians, no Gulliver, no horses).

"I lay down on the grass, which was very short and soft, where I slept sounder than ever I remembered ..."
"At the place where the carriage stopped there stood an ancient temple, esteemed to be the largest in the whole
kingdom ... The great gate fronting to the north was about four feet high, and almost two feet wide ... On each side
of the gate was a small window, not above six inches from the ground: into that on the left side, the king's smith
conveyed fourscore and eleven chains ... Over against this temple, on the other side of the great highway, at twenty
feet distance, there was a turret at least five feet high."
"When I found myself on my feet, I looked about me, and must confess I never beheld a more entertaining prospect. The
country around appeared like a continued garden, and the enclosed fields, which were generally forty feet square,
resembled so many beds of flowers. These fields were intermingled with woods of half a stang, and the tallest trees,
as I could judge, appeared to be seven feet high. I viewed the town on my left hand, which looked like the painted
scene of a city in a theatre."

What is here: the reader stands on the short soft turf in front of the temple's north gate (the ground there trodden
bare in the semicircle the chains allowed), the bundled watch-chains running out of the little window on the left of
the gate to the reader's feet, the domestics' tents on each side of the door. In front: the great highway (about
2 ft 4 in wide, i.e. a 28 ft Lilliputian road), the five-foot turret across it, then the patchwork of hedged fields
about 12 m (forty feet) square, small woods whose tallest trees are seven feet (2.1 m), a temple orchard, the walled
town on the left hand (north-west), and to the right the low bank, the beach of a very small declivity, the sea with
two of the emperor's men of war, and Blefuscu faint across the channel to the north-east.

Time and weather: a clear, warm early-summer morning ("the beginning of summer in those parts"), the sun about 33
degrees up in the east-north-east, a thin sea haze on the horizon. One sun, one sky.

Scale: Lilliput is 1/12 (a 40 ft field is 12 m, a 7 ft tree 2.1 m, the temple gate 1.22 m high, hedges 10-22 cm);
the reader's eye is 1.55 m above the turf. Everything sits within 140 m of the reader (the headset far clip is 150 m).

Builds the place procedurally (no downloaded models, textures or HDRIs) with PBR node materials, then (by flag)
renders Cycles stills, bakes materials to textures, merges static meshes by material and exports .gltf + .bin +
textures/ for Unity.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet, on the turf (z=0), 1.4 m in front of the temple's north gate
  anchor.reader.look      eye height 1.55 m, 2 m north of the entrance (the reader faces north over the fields)
  anchor.scene.centre     the same point on the ground (the middle of the semicircle the chains allow)
  anchor.temple.gate, anchor.turret, anchor.town, anchor.shore
  light.sun (SUN, morning, east-north-east), light.sky (SUN, cool fill, no shadow)
  SkyDome (unlit backdrop, baked base texture)
  far.land (country beyond ~58 m), far.sea, far.town, far.ships (backdrop: no shadows, not lightmapped)

Axes: metres, Blender +Z up, +Y north (the reader looks north), +X east (the sea is east, the town north-west).

Run headless:
  blender -b -P blender/build_lilliput_beach.py -- --out out/lilliput-beach --render --quick --res 900
  blender -b -P blender/build_lilliput_beach.py -- --out out/lilliput-beach --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/lilliput-beach")
ap.add_argument("--render", action="store_true")
ap.add_argument("--bake", action="store_true")
ap.add_argument("--export", action="store_true")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", type=int, default=1600)
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--quick", action="store_true", help="low samples for iteration")
ap.add_argument("--cams", default="", help="comma list of camera names to render (default all)")
ap.add_argument("--prefix", default="render_", help="file name prefix for the stills")
args = ap.parse_args(argv)
OUT = os.path.abspath(args.out)
os.makedirs(OUT, exist_ok=True)
random.seed(1699)

# ----------------------------------------------------------------------------- dimensions (metres, Z up, +Y north)
EYE = 1.55
GATE = (0.0, -1.40)                  # the temple's north gate (centre of the threshold)
TW, TD, TH = 3.6, 5.4, 2.0           # temple outer width (x), depth (y), wall height
TY0 = GATE[1]                        # temple front face (y)
TURRET = (3.4, 4.6)                  # "over against this temple, on the other side of the great highway, at twenty feet"
ROAD_Y = 3.0                         # the great highway runs east-west in front of the temple, then bends to the town
TOWN_C, TOWN_A, TOWN_H = (-60.0, 82.0), 0.35, 23.0     # the town: centre, rotation, half side
SKY_R = 140.0
R_FAR = 135.0
SUN_DIR = Vector((0.78, 0.30, 0.55)).normalized()      # towards the sun: east-north-east, ~33 degrees up
FIELD_TH = 0.24
WOODS = [(16.0, 30.0, 6.5), (-31.0, 9.0, 6.0), (22.0, 70.0, 8.0), (-22.0, -27.0, 7.0)]
COMMON_C = (0.0, -3.0)

def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)
def frac(x): return x - math.floor(x)

def coast(y): return 24.0 + 0.30 * y + 4.0 * math.sin(y / 17.0) + 2.0 * math.sin(y / 7.3)
def inland_dist(x, y): return coast(y) - x

def road_k():
    gx, gy = town_gate()
    return (gy - ROAD_Y) / ((gx + 8.0) ** 2)
def town_gate():
    a = TOWN_A
    return (TOWN_C[0] + TOWN_H * math.sin(a), TOWN_C[1] - TOWN_H * math.cos(a))
ROAD_K = road_k()
GATE_X = town_gate()[0]
def road_dist(x, y):
    xm = min(x + 8.0, 0.0); yc = ROAD_Y + ROAD_K * xm * xm; sl = 2 * ROAD_K * xm
    d = abs(y - yc) / math.sqrt(1 + sl * sl)
    if x < GATE_X - 0.3: d = 99.0
    if x > 14.0: d += (x - 14.0) * 2.0
    return d

def common_rlim(phi): return 8.6 + 1.0 * math.sin(3 * phi + 0.7) + 0.7 * math.sin(5 * phi + 2.1)
def is_common(x, y, margin=0.0):
    dx, dy = x - COMMON_C[0], y - COMMON_C[1]
    return math.hypot(dx, dy) < common_rlim(math.atan2(dy, dx)) + margin
def coast_lim(y): return 15.0 + 1.5 * math.sin(y / 6.1)
def is_coastal(x, y, margin=0.0): return inland_dist(x, y) < coast_lim(y) + margin
def town_local(x, y):
    dx, dy = x - TOWN_C[0], y - TOWN_C[1]; c, s = math.cos(-TOWN_A), math.sin(-TOWN_A)
    return dx * c - dy * s, dx * s + dy * c
def in_town(x, y, margin=0.0):
    lu, lv = town_local(x, y); return abs(lu) < TOWN_H + margin and abs(lv) < TOWN_H + margin
def in_wood(x, y, margin=0.0):
    return any(math.hypot(x - wx, y - wy) < wr + margin for wx, wy, wr in WOODS)

def h_raw(x, y):
    d = inland_dist(x, y)
    if d <= 0: zc = max(-4.0, -2.0 + 0.05 * d)
    elif d < 7: zc = -2.0 + 0.07 * d
    elif d < 12: zc = -1.51 + 0.75 * smooth(7, 12, d)
    else: zc = -0.76 + 0.02 * (d - 12)
    r = math.hypot(x, y)
    roll = 0.35 * math.sin(x / 19 + 0.4) * math.sin(y / 23 + 1.1) + 0.18 * math.sin((x + y) / 11.0) + 0.12 * math.sin((x - 2 * y) / 7.0)
    hill = 0.55 * math.exp(-((x - TOWN_C[0]) ** 2 + (y - TOWN_C[1]) ** 2) / (2 * 30.0 ** 2))
    inland = 0.008 * (-x) + 0.003 * y + roll * smooth(6, 30, r) + hill
    w = smooth(10, 22, d)
    return zc + (inland - zc) * w
H0 = h_raw(0.0, 0.0)
def h(x, y):
    z = h_raw(x, y) - H0
    r = math.hypot(x, y)
    # small relief in the turf, strongest at the reader's feet (the brief: nearby surfaces must hold up)
    z += 0.016 * noise.noise(Vector((x * 2.3, y * 2.3, 0.3))) * (1 - smooth(6, 16, r))
    z += 0.04 * noise.noise(Vector((x * 0.35, y * 0.35, 1.7))) * smooth(2, 10, r)
    return z

# ----------------------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24 if args.quick else args.samples
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.transmission_bounces = 2
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

COLL = bpy.data.collections.new("LilliputBeach")
scene.collection.children.link(COLL)
def link(obj):
    COLL.objects.link(obj); return obj

# ----------------------------------------------------------------------------- node-expression helper
class F:
    """A float socket with arithmetic that builds Math nodes."""
    def __init__(s, g, sock): s.g, s.s = g, sock
    def __add__(s, o): return s.g.m('ADD', s, o)
    __radd__ = __add__
    def __sub__(s, o): return s.g.m('SUBTRACT', s, o)
    def __rsub__(s, o): return s.g.m('SUBTRACT', o, s)
    def __mul__(s, o): return s.g.m('MULTIPLY', s, o)
    __rmul__ = __mul__
    def __truediv__(s, o): return s.g.m('DIVIDE', s, o)
    def __rtruediv__(s, o): return s.g.m('DIVIDE', o, s)
    def __neg__(s): return s.g.m('MULTIPLY', s, -1.0)
    def sin(s): return s.g.m('SINE', s)
    def floor(s): return s.g.m('FLOOR', s)
    def fract(s): return s.g.m('FRACT', s)
    def abs(s): return s.g.m('ABSOLUTE', s)
    def sqrt(s): return s.g.m('SQRT', s)
    def min(s, o): return s.g.m('MINIMUM', s, o)
    def max(s, o): return s.g.m('MAXIMUM', s, o)

class G:
    def __init__(s, nt): s.nt = nt; s.i = 0; s._pos = None
    def n(s, kind, **kw):
        nd = s.nt.nodes.new(kind); nd.location = (-2600 + 220 * (s.i // 18), -170 * (s.i % 18)); s.i += 1
        for k, v in kw.items(): setattr(nd, k, v)
        return nd
    def set(s, sock, v):
        if isinstance(v, F): s.nt.links.new(v.s, sock)
        elif isinstance(v, bpy.types.NodeSocket): s.nt.links.new(v, sock)
        elif isinstance(v, (tuple, list)):
            n = len(sock.default_value); v = tuple(v)
            sock.default_value = v + (1.0,) * (n - len(v)) if len(v) < n else v[:n]
        else: sock.default_value = v
    def m(s, op, a, b=None, c=None):
        nd = s.n("ShaderNodeMath", operation=op)
        for i, v in enumerate((a, b, c)):
            if v is not None: s.set(nd.inputs[i], v)
        return F(s, nd.outputs[0])
    def pos(s):
        if s._pos is None: s._pos = s.n("ShaderNodeTexCoord").outputs["Object"]
        return s._pos
    def sep(s, vec):
        nd = s.n("ShaderNodeSeparateXYZ"); s.set(nd.inputs[0], vec)
        return F(s, nd.outputs[0]), F(s, nd.outputs[1]), F(s, nd.outputs[2])
    def comb(s, x, y, z=0.0):
        nd = s.n("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)): s.set(nd.inputs[i], v)
        return nd.outputs[0]
    def noise(s, vec, scale, detail=4.0, rough=0.55, dist=0.0):
        nd = s.n("ShaderNodeTexNoise"); s.set(nd.inputs["Vector"], vec)
        nd.inputs["Scale"].default_value = scale; nd.inputs["Detail"].default_value = detail
        nd.inputs["Roughness"].default_value = rough; nd.inputs["Distortion"].default_value = dist
        return F(s, nd.outputs["Fac"]), nd.outputs["Color"]
    def white(s, vec):
        nd = s.n("ShaderNodeTexWhiteNoise", noise_dimensions='3D'); s.set(nd.inputs["Vector"], vec)
        return F(s, nd.outputs["Value"]), nd.outputs["Color"]
    def vor(s, vec, scale, feature='F1', rand=1.0):
        nd = s.n("ShaderNodeTexVoronoi", feature=feature); s.set(nd.inputs["Vector"], vec)
        nd.inputs["Scale"].default_value = scale; nd.inputs["Randomness"].default_value = rand
        return F(s, nd.outputs["Distance"])
    def ss(s, x, e0, e1):
        nd = s.n("ShaderNodeMapRange", interpolation_type='SMOOTHSTEP')
        s.set(nd.inputs["Value"], x); s.set(nd.inputs["From Min"], e0); s.set(nd.inputs["From Max"], e1)
        return F(s, nd.outputs["Result"])
    def ramp(s, fac, stops, interp=None):
        nd = s.n("ShaderNodeValToRGB"); cr = nd.color_ramp
        if interp: cr.interpolation = interp
        while len(cr.elements) > 1: cr.elements.remove(cr.elements[-1])
        cr.elements[0].position = stops[0][0]; cr.elements[0].color = tuple(stops[0][1]) + (1.0,) * (4 - len(stops[0][1]))
        for p, c in stops[1:]:
            e = cr.elements.new(p); e.color = tuple(c) + (1.0,) * (4 - len(c))
        s.set(nd.inputs["Fac"], fac)
        return nd.outputs["Color"]
    def mix(s, fac, a, b, blend='MIX'):
        nd = s.n("ShaderNodeMix", data_type='RGBA', blend_type=blend, clamp_factor=True)
        s.set(nd.inputs["Factor"], fac); s.set(nd.inputs[6], a); s.set(nd.inputs[7], b)
        return nd.outputs[2]
    def mul(s, a, b, fac=1.0): return s.mix(fac, a, b, 'MULTIPLY')
    def lerp(s, fac, a, b): return a + (b - a) * fac
    def attr(s, name):
        return s.n("ShaderNodeAttribute", attribute_name=name)
    def ao(s, dist):
        nd = s.n("ShaderNodeAmbientOcclusion"); nd.inputs["Distance"].default_value = dist
        return nd.outputs["Color"]
    def bump(s, bsdf, height, strength, distance):
        nd = s.n("ShaderNodeBump"); nd.inputs["Strength"].default_value = strength; nd.inputs["Distance"].default_value = distance
        s.set(nd.inputs["Height"], height); s.nt.links.new(nd.outputs["Normal"], bsdf.inputs["Normal"])

def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, bsdf, G(nt)

# ----------------------------------------------------------------------------- materials
def ground_mat(name, level):
    """The country: the short soft turf of the common round the temple, the trodden semicircle, the highway, the
    patchwork of enclosed fields (each its own crop, 'so many beds of flowers') with hedge banks along their edges,
    wood floors, the coarse grass of the bank, the sand of the very small declivity, wet sand and the wrack line.
    The field layout here and the hedges built in Python come from the same formulas."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    d = 24.0 + 0.30 * y + 4.0 * (y / 17.0).sin() + 2.0 * (y / 7.3).sin() - x
    nlo, _ = g.noise(P, 0.07, 3)
    nmid, _ = g.noise(P, 0.55, 5)
    nhi, _ = g.noise(P, 5.0, 5)
    # --- the enclosed fields
    c, s_ = math.cos(FIELD_TH), math.sin(FIELD_TH)
    u = x * c + y * s_; v = y * c - x * s_
    vw = v + 1.3 * (u / 23.0 + 1.3).sin() + 0.7 * (u / 9.7 + 0.2).sin()
    uw = u + 1.1 * (v / 19.0 + 0.5).sin()
    rowf = vw / 12.0; row = rowf.floor(); frv = rowf - row
    W = 10.5 + 3.0 * (row * 0.381966 + 0.7).fract()
    cf = uw / W + (row * 0.618034 + 0.13).fract(); cell = cf.floor(); fru = cf - cell
    edge = (frv.min(1.0 - frv) * 12.0).min(fru.min(1.0 - fru) * W)
    fid, fidc = g.white(g.comb(row, cell, 0.37))
    _, fid2, fid3 = g.sep(fidc)
    crops = [(0.00, (0.075, 0.13, 0.032)),   # young wheat, deep green
             (0.14, (0.30, 0.24, 0.08)),     # ripening wheat, straw gold
             (0.30, (0.19, 0.20, 0.07)),     # barley, pale gray-green
             (0.42, (0.075, 0.12, 0.035)),   # pasture
             (0.56, (0.12, 0.08, 0.045)),    # fallow, ploughed brown
             (0.66, (0.36, 0.30, 0.05)),     # flowering mustard / rape, yellow
             (0.76, (0.095, 0.14, 0.055)),   # flax, green (blue flower speckle below)
             (0.88, (0.23, 0.20, 0.10))]     # hay meadow, cut and drying
    crop = g.ramp(fid, crops, 'CONSTANT')
    mott = g.ramp(nmid * 0.6 + nhi * 0.4, [(0.3, (0.70, 0.70, 0.70)), (0.5, (1.0, 1.0, 1.0)), (0.72, (1.2, 1.15, 1.05))])
    crop = g.mul(crop, mott)
    # drills / furrows across each field, direction chosen per field; ploughed fields show them most
    along = g.lerp(g.ss(fid2, 0.49, 0.51), fru * W, frv * 12.0)
    drill = ((along * (2 * math.pi / 0.33)).sin() * 0.5 + 0.5)
    fallow = g.ss(fid, 0.56, 0.565) * (1.0 - g.ss(fid, 0.655, 0.66))
    rows_amt = 0.07 + fallow * 0.22
    crop = g.mul(crop, g.mix(rows_amt, (1, 1, 1), g.comb(drill, drill, drill)))
    crop = g.mul(crop, g.comb(0.82 + fid3 * 0.36, 0.82 + fid3 * 0.36, 0.82 + fid3 * 0.36))
    streak, _ = g.noise(g.comb(along * 0.25, nmid * 2.0, fid * 10.0), 3.0, 4)
    crop = g.mul(crop, g.ramp(streak, [(0.35, (0.82, 0.82, 0.8)), (0.65, (1.12, 1.1, 1.05))]))
    headland = (1.0 - g.ss(edge, 0.6, 1.3 + nmid * 0.6)) * 0.45
    crop = g.mix(headland, crop, (0.15, 0.16, 0.07))
    # flower speckle in the flowering fields: yellow in the mustard, blue in the flax, poppies at a few edges
    fl = 1.0 - g.ss(g.vor(P, 18.0), 0.05, 0.16)
    flax = g.ss(fid, 0.76, 0.765) * (1.0 - g.ss(fid, 0.875, 0.88))
    crop = g.mix(fl * flax * 0.35, crop, (0.30, 0.34, 0.50))
    pop = (1.0 - g.ss(edge, 0.3, 1.4)) * g.ss(fid3, 0.62, 0.66) * fl * 0.8
    crop = g.mix(pop, crop, (0.42, 0.05, 0.03))
    # hedge banks along every field edge (the 3D hedges stand on them near the reader)
    hed = (1.0 - g.ss(edge, 0.10, 0.26 + nhi * 0.06))
    crop = g.mix(hed, crop, (0.055, 0.075, 0.03))
    # --- the turf of the common: short and soft, mottled, clover, daisies and buttercups in drifts
    turf = g.ramp(nmid * 0.55 + nhi * 0.45, [(0.25, (0.05, 0.085, 0.022)), (0.42, (0.075, 0.12, 0.03)), (0.58, (0.11, 0.145, 0.04)), (0.75, (0.17, 0.17, 0.07))])
    dry = g.ss(nlo * 0.6 + nmid * 0.4, 0.52, 0.66)
    turf = g.mix(dry * 0.6, turf, (0.20, 0.18, 0.09))
    clov, _ = g.noise(P, 1.6, 3)
    turf = g.mix(g.ss(clov, 0.6, 0.7) * 0.5, turf, (0.045, 0.09, 0.04))
    if level == 'near':
        fine, _ = g.noise(P, 38.0, 4)
        turf = g.mul(turf, g.ramp(fine, [(0.3, (0.8, 0.8, 0.8)), (0.7, (1.12, 1.12, 1.08))]))
        dz = 1.0 - g.ss(g.vor(P, 34.0), 0.06, 0.13)
        drift = g.ss(nlo + nmid * 0.3, 0.55, 0.68)
        turf = g.mix(dz * drift * 0.9, turf, (0.72, 0.72, 0.66))
        bc = 1.0 - g.ss(g.vor(g.comb(x + 3.3, y - 1.1, 0.0), 27.0), 0.05, 0.11)
        turf = g.mix(bc * g.ss(nmid, 0.58, 0.7) * 0.85, turf, (0.65, 0.50, 0.04))
    # --- the trodden semicircle in front of the gate (the reach of the chains) and the strip by the door
    tr = math.hypot(0, 0)
    gx, gy = GATE
    dgate = ((x - gx) * (x - gx) + (y - gy) * (y - gy)).sqrt()
    tramp = (1.0 - g.ss(dgate, 1.55 + nmid * 0.5, 2.2 + nmid * 0.5)) * g.ss(y, gy - 0.3, gy + 0.1)
    trc = g.ramp(nhi * 0.6 + nmid * 0.4, [(0.35, (0.21, 0.16, 0.10)), (0.5, (0.17, 0.17, 0.07)), (0.7, (0.19, 0.21, 0.08))])
    # --- the great highway and its verges
    xm = (x + 8.0).min(0.0); yc = ROAD_Y + ROAD_K * xm * xm; sl = 2 * ROAD_K * xm
    rd = (y - yc).abs() / (1.0 + sl * sl).sqrt()
    rd = rd + (1.0 - g.ss(x, GATE_X - 0.5, GATE_X - 0.2)) * 50.0 + (x - 14.0).max(0.0) * 2.0
    road = 1.0 - g.ss(rd, 0.30 + nhi * 0.05, 0.40 + nhi * 0.05)
    verge = 1.0 - g.ss(rd, 0.40, 0.8)
    rut = 1.0 - g.ss((rd - 0.16).abs(), 0.012, 0.04)
    roadc = g.ramp(nhi * 0.5 + nmid * 0.5, [(0.3, (0.19, 0.14, 0.09)), (0.55, (0.25, 0.19, 0.12)), (0.8, (0.30, 0.24, 0.16))])
    roadc = g.mix(rut * 0.45, roadc, (0.16, 0.12, 0.08))
    # --- coarse grass of the bank and the sand of the shore
    dune = g.ramp(nmid * 0.5 + nhi * 0.5, [(0.3, (0.17, 0.18, 0.08)), (0.55, (0.27, 0.26, 0.13)), (0.8, (0.38, 0.34, 0.20))])
    rip = ((d * (2 * math.pi / 0.11) + nmid * 6.0).sin() * 0.5 + 0.5)
    sand = g.ramp(nmid * 0.6 + nhi * 0.4, [(0.3, (0.33, 0.28, 0.20)), (0.6, (0.40, 0.34, 0.25)), (0.8, (0.44, 0.38, 0.28))])
    sand = g.mul(sand, g.mix(0.08, (1, 1, 1), g.comb(rip, rip, rip)))
    wet = 1.0 - g.ss(z, -1.97 + nmid * 0.03, -1.86 + nmid * 0.04)
    sand = g.mix(wet * 0.75, sand, (0.25, 0.21, 0.155))
    wrack = (1.0 - g.ss((z + 1.80).abs(), 0.004, 0.02 + nhi * 0.01)) * g.ss(nhi, 0.45, 0.6)
    sand = g.mix(wrack * 0.8, sand, (0.10, 0.08, 0.04))
    beach = 1.0 - g.ss(z, -1.58 + nmid * 0.10, -1.42 + nmid * 0.10)
    # --- wood floors (leaf litter and moss) and the town's streets
    woodm = None
    for wx, wy, wr in WOODS:
        dw = ((x - wx) * (x - wx) + (y - wy) * (y - wy)).sqrt()
        wm = 1.0 - g.ss(dw, wr - 0.3 + nmid * 1.2, wr + 1.0 + nmid * 1.2)
        woodm = wm if woodm is None else woodm.max(wm)
    woodc = g.ramp(nhi, [(0.3, (0.09, 0.075, 0.04)), (0.6, (0.075, 0.10, 0.035)), (0.8, (0.13, 0.10, 0.06))])
    ct, st_ = math.cos(-TOWN_A), math.sin(-TOWN_A)
    lu = (x - TOWN_C[0]) * ct - (y - TOWN_C[1]) * st_; lv = (x - TOWN_C[0]) * st_ + (y - TOWN_C[1]) * ct
    town = (1.0 - g.ss(lu.abs(), TOWN_H - 0.2, TOWN_H + 0.4)) * (1.0 - g.ss(lv.abs(), TOWN_H - 0.2, TOWN_H + 0.4))
    # --- masks and composition
    dx_, dy_ = x - COMMON_C[0], y - COMMON_C[1]
    rC = (dx_ * dx_ + dy_ * dy_).sqrt(); phi = g.m('ARCTAN2', dy_, dx_)
    rlim = 8.6 + 1.0 * (phi * 3.0 + 0.7).sin() + 0.7 * (phi * 5.0 + 2.1).sin()
    common = 1.0 - g.ss(rC, rlim - 0.12, rlim + 0.12)
    dl = 15.0 + 1.5 * (y / 6.1).sin()
    coastal = 1.0 - g.ss(d, dl - 0.12, dl + 0.12)
    bankgrass = 1.0 - g.ss(d, 11.0 + nmid * 3.0, 16.0 + nmid * 3.0)
    col = crop
    col = g.mix(common.max(coastal), col, turf)
    col = g.mix(bankgrass * coastal, col, dune)
    col = g.mix(woodm, col, woodc)
    col = g.mix(town, col, (0.32, 0.28, 0.22))
    col = g.mix(verge * 0.55, col, trc)
    col = g.mix(tramp, col, trc)
    col = g.mix(road, col, roadc)
    col = g.mix(beach, col, sand)
    if level == 'far':
        r = (x * x + y * y).sqrt()
        col = g.mix(g.ss(r, 80.0, 135.0) * 0.25, col, (0.30, 0.34, 0.30))
    if level == 'near':
        col = g.mul(col, g.ao(0.25), 0.4)
    g.set(b.inputs["Base Color"], col)
    rough = 0.93 - wet * 0.42 * beach - road * 0.08
    g.set(b.inputs["Roughness"], rough)
    b.inputs["Specular IOR Level"].default_value = 0.35
    hgt = nhi * 0.5 + drill * (0.08 + fallow * 0.5) * (1.0 - common) - road * 0.4 + rut * 0.3 + rip * beach * 0.3
    if level == 'near':
        hgt = hgt + fine * 0.6
        g.bump(b, hgt, 0.35, 0.02)
    else:
        g.bump(b, hgt, 0.25, 0.05)
    return m

def foliage_mat(name, scale=1.0, sheen=0.15):
    """Leaves of the tiny trees and hedges: the per-tree tint attribute, clumped light and shade, a little
    self-shadow, gorse flowers where the tint's alpha says so."""
    m, nt, b, g = new_mat(name)
    P = g.pos()
    at = g.attr("tint")
    n1, _ = g.noise(P, 7.0 * scale, 4, 0.6, 0.3)
    n2, _ = g.noise(P, 40.0 * scale, 3)
    col = g.mul(at.outputs["Color"], g.ramp(n1 * 0.7 + n2 * 0.3, [(0.3, (0.55, 0.55, 0.55)), (0.55, (1.0, 1.0, 1.0)), (0.78, (1.45, 1.4, 1.2))]))
    bl = (1.0 - g.ss(g.vor(P, 70.0 * scale), 0.08, 0.18)) * F(g, at.outputs["Alpha"])
    col = g.mix(bl, col, (0.72, 0.55, 0.04))
    col = g.mul(col, g.ao(0.18 / scale), 0.55)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.82
    b.inputs["Specular IOR Level"].default_value = 0.25
    b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.5
    g.bump(b, n2 * 0.6 + n1 * 0.4, 0.5, 0.02)
    return m

def stone_mat(name):
    """The temple's old limestone ashlar (Lilliputian blocks of about 1 ft x 6 in), weathered: lichen, a green foot
    of moss, dirt streaks under the sills."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    br = g.n("ShaderNodeTexBrick", offset=0.5, squash=1.0)
    g.set(br.inputs["Vector"], g.comb(x + y, z * 1.0, 0.0))
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = 0.085; br.inputs["Row Height"].default_value = 0.042
    br.inputs["Mortar Size"].default_value = 0.0032; br.inputs["Mortar Smooth"].default_value = 0.4
    br.inputs["Bias"].default_value = 0.0
    br.inputs["Color1"].default_value = (0.74, 0.73, 0.71, 1); br.inputs["Color2"].default_value = (1.16, 1.10, 1.0, 1)
    br.inputs["Mortar"].default_value = (0.74, 0.72, 0.68, 1)
    n1, _ = g.noise(P, 3.0, 6, 0.6)
    n2, _ = g.noise(P, 30.0, 4)
    base = g.ramp(n1, [(0.3, (0.25, 0.23, 0.19)), (0.55, (0.33, 0.30, 0.25)), (0.75, (0.38, 0.35, 0.29))])
    col = g.mul(base, br.outputs["Color"])
    lich = g.ss(n1 * 0.6 + n2 * 0.4, 0.6, 0.66)
    col = g.mix(lich * 0.6, col, (0.50, 0.50, 0.34))
    moss = (1.0 - g.ss(z, 0.03, 0.28 + n1 * 0.2)) * g.ss(n2, 0.35, 0.6)
    col = g.mix(moss * 0.8, col, (0.10, 0.14, 0.05))
    sn, _ = g.noise(g.comb(x * 9.0, y * 9.0, z * 0.6), 1.0, 3)
    col = g.mul(col, g.ramp(sn, [(0.4, (0.72, 0.70, 0.66)), (0.6, (1, 1, 1))]), 0.5)
    col = g.mul(col, g.ao(0.12), 0.5)
    g.set(b.inputs["Base Color"], col)
    g.set(b.inputs["Roughness"], 0.82 + n2 * 0.12)
    g.bump(b, F(g, br.outputs["Fac"]) * -0.6 + n2 * 0.4, 0.5, 0.004)
    return m

def roof_mat(name):
    """Stone slates of the old roofs, in courses, gray-brown with lichen."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    br = g.n("ShaderNodeTexBrick", offset=0.5)
    g.set(br.inputs["Vector"], g.comb(x + y * 0.3, z, 0.0))
    br.inputs["Brick Width"].default_value = 0.045; br.inputs["Row Height"].default_value = 0.022
    br.inputs["Mortar Size"].default_value = 0.0025
    br.inputs["Color1"].default_value = (0.85, 0.85, 0.85, 1); br.inputs["Color2"].default_value = (1.1, 1.08, 1.05, 1)
    br.inputs["Mortar"].default_value = (0.35, 0.34, 0.32, 1)
    n1, _ = g.noise(P, 4.0, 5)
    base = g.ramp(n1, [(0.3, (0.17, 0.16, 0.15)), (0.6, (0.25, 0.23, 0.20)), (0.8, (0.30, 0.27, 0.22))])
    col = g.mul(base, br.outputs["Color"])
    col = g.mix(g.ss(n1, 0.62, 0.7) * 0.6, col, (0.40, 0.40, 0.25))
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.85
    g.bump(b, F(g, br.outputs["Fac"]) * -1.0, 0.6, 0.003)
    return m

def noisy(name, colors, scale=8.0, rough=0.8, bump=0.2, metallic=0.0, stretch=(1, 1, 1), sheen=0.0, ao=0.0):
    m, nt, b, g = new_mat(name)
    mp = g.n("ShaderNodeMapping"); g.set(mp.inputs["Vector"], g.pos()); mp.inputs["Scale"].default_value = stretch
    n1, _ = g.noise(mp.outputs[0], scale, 6, 0.6)
    stops = [(i / max(1, len(colors) - 1) * 0.6 + 0.2, c) for i, c in enumerate(colors)]
    col = g.ramp(n1, stops)
    if ao: col = g.mul(col, g.ao(ao), 0.5)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if sheen: b.inputs["Sheen Weight"].default_value = sheen
    if bump:
        n2, _ = g.noise(mp.outputs[0], scale * 6, 4)
        g.bump(b, n2, bump, 0.003)
    return m

def rock_mat(name):
    """Weathered sandstone of the shore: lichen on the tops, dark and wet near the water."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    n1, _ = g.noise(P, 6.0, 8, 0.65, 0.4)
    n2, _ = g.noise(P, 40.0, 4)
    col = g.ramp(n1, [(0.3, (0.25, 0.22, 0.18)), (0.5, (0.36, 0.32, 0.26)), (0.7, (0.44, 0.40, 0.33))])
    strata = ((z * 90.0 + n1 * 4.0).sin() * 0.5 + 0.5)
    col = g.mul(col, g.mix(0.15, (1, 1, 1), g.comb(strata, strata, strata)))
    geo = g.n("ShaderNodeNewGeometry"); _, _, nz = g.sep(geo.outputs["Normal"])
    lich = g.ss(nz, 0.55, 0.8) * g.ss(n2, 0.45, 0.6)
    col = g.mix(lich * 0.7, col, (0.52, 0.50, 0.36))
    wet = 1.0 - g.ss(z, -1.95, -1.75)
    col = g.mix(wet * 0.7, col, (0.10, 0.09, 0.075))
    col = g.mul(col, g.ao(0.1), 0.5)
    g.set(b.inputs["Base Color"], col)
    g.set(b.inputs["Roughness"], 0.88 - wet * 0.45)
    g.bump(b, n1 * 0.5 + n2 * 0.5, 0.6, 0.01)
    return m

def tint_mat(name, rough=0.8, scale=20.0, var=0.25):
    """Colour from the per-vertex tint attribute (town walls and roofs, ships' hulls and sails) with mottling."""
    m, nt, b, g = new_mat(name)
    at = g.attr("tint")
    n1, _ = g.noise(g.pos(), scale, 4)
    col = g.mul(at.outputs["Color"], g.ramp(n1, [(0.3, (1 - var,) * 3), (0.7, (1 + var * 0.5,) * 3)]))
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = rough
    return m

def sea_mat(name):
    """The sea: green and pale over the sand of the very small declivity, deep blue-green further out, a thin line
    of surf; small waves in the normal for the morning glitter."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    d = 24.0 + 0.30 * y + 4.0 * (y / 17.0).sin() + 2.0 * (y / 7.3).sin() - x
    off = -d
    n1, _ = g.noise(P, 0.15, 3)
    n2, _ = g.noise(g.comb(x * 1.0, y * 1.0, 0.0), 1.4, 5, 0.6, 0.6)
    depth = g.ss(off + n1 * 6.0, 0.0, 28.0)
    col = g.ramp(depth, [(0.0, (0.16, 0.25, 0.20)), (0.12, (0.07, 0.20, 0.20)), (0.5, (0.03, 0.10, 0.13)), (1.0, (0.02, 0.06, 0.10))])
    foam = (1.0 - g.ss(off, 0.25, 1.2 + n2 * 0.8)) * g.ss(n2 + ((off * 6.0).sin()) * 0.15, 0.5, 0.62)
    col = g.mix(foam * 0.55, col, (0.58, 0.62, 0.60))
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.07
    b.inputs["IOR"].default_value = 1.33
    sw = ((off * (2 * math.pi / 0.9) + n2 * 3.0).sin() * 0.5 + 0.5)
    n3, _ = g.noise(P, 6.0, 3)
    g.bump(b, sw * 0.4 + n2 * 0.3 + n3 * 0.3, 0.25, 0.02)
    return m

def sky_dome_mat(name="M_SkyDome"):
    """A clear early-summer morning: deep blue overhead, paling to a warm haze at the horizon and a bright glow
    round the east-north-east sun; a few small fair-weather clouds low in the south and west (none behind the page);
    the low hazy hills of the rest of the island painted along the land horizon and Blefuscu faint across the
    channel to the north-east."""
    m, nt, b, g = new_mat(name)
    tc = g.n("ShaderNodeTexCoord")
    nv = g.n("ShaderNodeVectorMath", operation='NORMALIZE'); g.set(nv.inputs[0], tc.outputs["Object"])
    dx, dy, el = g.sep(nv.outputs[0])
    base = g.ramp(g.ss(el, -0.02, 0.9), [(0.0, (0.62, 0.67, 0.70)), (0.03, (0.50, 0.60, 0.74)), (0.10, (0.30, 0.46, 0.72)),
                                       (0.35, (0.15, 0.30, 0.62)), (1.0, (0.08, 0.20, 0.50))])
    sd = g.n("ShaderNodeVectorMath", operation='DOT_PRODUCT'); g.set(sd.inputs[0], nv.outputs[0]); sd.inputs[1].default_value = tuple(SUN_DIR)
    sdot = F(g, sd.outputs["Value"])
    glow = g.ss(sdot, 0.72, 1.0)
    col = g.mix(glow * glow * 0.8, base, (1.0, 0.93, 0.78))
    disc = g.ss(sdot, 0.9993, 0.9997)
    col = g.mix(disc, col, (6.0, 5.6, 4.8))
    # clouds: projected onto a flat deck, sparse, kept away from the north (behind the page)
    zk = el.max(0.0) + 0.06
    px, py = dx / zk, dy / zk
    cl, _ = g.noise(g.comb(px * 0.35 + 3.1, py * 0.35 + 7.7, 0.4), 1.0, 6, 0.55, 0.3)
    cl2, _ = g.noise(g.comb(px * 0.08 + 1.3, py * 0.08, 0.9), 1.0, 2)
    north = g.ss(dy, 0.25, 0.7)
    cover = g.ss(cl * 0.7 + cl2 * 0.3, 0.58, 0.72) * (1.0 - north) * g.ss(el, 0.01, 0.05) * (1.0 - g.ss(el, 0.25, 0.45))
    ccol = g.mix(g.ss(cl, 0.6, 0.8), (0.80, 0.80, 0.80), (0.98, 0.96, 0.92))
    col = g.mix(cover * 0.85, col, ccol)
    # the land horizon: low hills, hazy blue-green, where the far terrain meets the sky; sea haze elsewhere
    az = g.m('ARCTAN2', dx, dy)
    land = (1.0 - g.ss(az, 0.40, 0.52)) * g.ss(az, -3.0, -2.9)
    hn, _ = g.noise(g.comb(dx * 3.0, dy * 3.0, 0.0), 1.0, 4)
    hill_h = 0.004 + hn * 0.022
    hills = land * (1.0 - g.ss(el - hill_h, -0.001, 0.001))
    col = g.mix(hills, col, g.ramp(hn, [(0.3, (0.36, 0.43, 0.42)), (0.7, (0.42, 0.48, 0.47))]))
    blef = g.ss(az, 0.62, 0.70) * (1.0 - g.ss(az, 0.88, 0.96))
    bh = 0.0035 * blef + hn * 0.002 * blef
    col = g.mix(blef * (1.0 - g.ss(el - bh, -0.0006, 0.0006)) * 0.6, col, (0.47, 0.55, 0.60))
    below = 1.0 - g.ss(el, -0.004, 0.0)
    col = g.mix(below * (1.0 - land), col, (0.40, 0.50, 0.54))
    g.set(b.inputs["Emission Color"], col); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m

M_GNEAR = ground_mat("M_GroundNear", 'near')
M_GMID = ground_mat("M_GroundFields", 'mid')
M_FARLAND = ground_mat("M_FarLand", 'far')
M_SEA = sea_mat("M_Sea")
M_SKY = sky_dome_mat()
M_LEAVES = foliage_mat("M_Leaves")
M_HEDGE = foliage_mat("M_Hedge", scale=1.4, sheen=0.1)
M_STONE = stone_mat("M_TempleStone")
M_ROOF = roof_mat("M_TempleRoof")
M_BARK = noisy("M_Bark", [(0.07, 0.06, 0.05), (0.15, 0.13, 0.10), (0.22, 0.20, 0.16)], scale=30, rough=0.9, stretch=(1, 1, 0.2))
M_WOOD = noisy("M_GateOak", [(0.09, 0.065, 0.04), (0.16, 0.12, 0.08), (0.22, 0.18, 0.13)], scale=12, rough=0.8, stretch=(1, 1, 0.12))
M_IRON = noisy("M_ChainIron", [(0.05, 0.045, 0.04), (0.12, 0.10, 0.08), (0.24, 0.13, 0.06)], scale=60, rough=0.5, metallic=0.75, bump=0.5)
M_CANVAS = noisy("M_TentCanvas", [(0.13, 0.11, 0.08), (0.18, 0.155, 0.11), (0.22, 0.19, 0.14)], scale=25, rough=0.95, sheen=0.3, ao=0.08)
M_ROCK = rock_mat("M_ShoreRock")
M_TOWN = tint_mat("M_Town", scale=3.0)
M_SHIPS = tint_mat("M_Ships", rough=0.7, scale=12.0)
M_INTERIOR = noisy("M_TempleDark", [(0.03, 0.028, 0.025), (0.06, 0.055, 0.05)], scale=8, rough=0.95, bump=0.0)

# ----------------------------------------------------------------------------- geometry helpers
def _finish(o, mat, smooth=False):
    o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def box(name, size, loc, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, mat)

def cyl(name, r, hgt, loc, mat, verts=16, rot=(0, 0, 0), r2=None):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=hgt, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=hgt, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat, smooth=True)

def prism_xz(name, pts, y0, y1, mat):
    """A flat polygon in the x-z plane extruded along y (gable ends, the pediment)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in pts]; b_ = [bm.verts.new((x, y1, z)) for x, z in pts]
    bm.faces.new(a); bm.faces.new(list(reversed(b_)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((a[i], a[j], b_[j], b_[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

def cut(target, cutter):
    md = target.modifiers.new("cut_" + cutter.name, 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'EXACT'
    cutter.hide_render = True; cutter.display_type = 'WIRE'
    return md

def apply_mods(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')

def set_tint(me, rgba_for_vert):
    """rgba_for_vert(index, co) -> (r, g, b, a). Stored as a point FLOAT_COLOR attribute named 'tint'."""
    at = me.color_attributes.get("tint") or me.color_attributes.new("tint", 'FLOAT_COLOR', 'POINT')
    for i, v in enumerate(me.vertices): at.data[i].color = rgba_for_vert(i, v.co)

def mesh_obj(name, bm, mat, smooth=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return link(o)

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

# ----------------------------------------------------------------------------- terrain: near (r<14), fields (to 58), far.land (to 135)
RINGS = [0.0]
r_ = 0.28
while r_ < R_FAR:
    RINGS.append(r_); r_ *= 1.165
RINGS.append(R_FAR)
SEG = 84
def ring_index(rv): return min(range(len(RINGS)), key=lambda i: abs(RINGS[i] - rv))
I_NEAR, I_MID = ring_index(14.0), ring_index(58.0)
R_NEAR, R_MID = RINGS[I_NEAR], RINGS[I_MID]
print("terrain rings", len(RINGS), "near", R_NEAR, "mid", R_MID)

def terrain(name, i0, i1, mat, uv_half):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    grid = []
    for j in range(i0, i1 + 1):
        rr = RINGS[j]
        if rr < 1e-6: grid.append([bm.verts.new((0.0, 0.0, h(0.0, 0.0)))]); continue
        row = []
        for i in range(SEG):
            a = 2 * math.pi * (i + 0.5 * (j % 2)) / SEG
            x, y = rr * math.cos(a), rr * math.sin(a)
            row.append(bm.verts.new((x, y, h(x, y))))
        grid.append(row)
    for j in range(len(grid) - 1):           # alternate rings are offset half a step; split along the shorter diagonal
        A, B = grid[j], grid[j + 1]
        if len(A) == 1:
            for i in range(SEG): bm.faces.new((A[0], B[i], B[(i + 1) % SEG]))
            continue
        for i in range(SEG):
            k = (i + 1) % SEG
            a0, a1, b0, b1 = A[i], A[k], B[i], B[k]
            if (a0.co - b1.co).length < (a1.co - b0.co).length:
                bm.faces.new((a0, b0, b1)); bm.faces.new((a0, b1, a1))
            else:
                bm.faces.new((a0, b0, a1)); bm.faces.new((a1, b0, b1))
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < 0: f.normal_flip()
        f.smooth = True
        for l in f.loops: l[uvl].uv = (l.vert.co.x / (2 * uv_half) + 0.5, l.vert.co.y / (2 * uv_half) + 0.5)
    return mesh_obj(name, bm, mat, smooth=True)

terrain("GroundNear", 0, I_NEAR, M_GNEAR, R_NEAR)
terrain("GroundFields", I_NEAR, I_MID, M_GMID, R_MID)
terrain("far.land", I_MID, len(RINGS) - 1, M_FARLAND, R_FAR)

# the sea: a polar sheet kept only where it is offshore
def sea_sheet():
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rs = [r for r in RINGS if r >= 8.0]
    seg = 72; grid = []
    for rr in rs:
        grid.append([bm.verts.new((rr * math.cos(2 * math.pi * i / seg), rr * math.sin(2 * math.pi * i / seg), -1.985)) for i in range(seg)])
    for j in range(len(grid) - 1):
        for i in range(seg):
            k = (i + 1) % seg
            q = (grid[j][i], grid[j + 1][i], grid[j + 1][k], grid[j][k])
            if min(inland_dist(v.co.x, v.co.y) for v in q) < 3.0:
                f = bm.faces.new(q)
    for v in [v for v in bm.verts if not v.link_faces]: bm.verts.remove(v)
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < 0: f.normal_flip()
        for l in f.loops: l[uvl].uv = (l.vert.co.x / (2 * R_FAR) + 0.5, l.vert.co.y / (2 * R_FAR) + 0.5)
    return mesh_obj("far.sea", bm, M_SEA)
sea_sheet()

# ----------------------------------------------------------------------------- vegetation builders
ICO1 = None
def lobe_template(subdiv):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    return [v.co.copy() for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces]
LOBE = {2: lobe_template(2), 1: lobe_template(1), 0: lobe_template(0)}
def uvsphere_template(seg=7, rings=5):
    verts = [Vector((0, 0, -1))]
    for j in range(1, rings):
        t = math.pi * j / rings; z = -math.cos(t); rr = math.sin(t)
        for i in range(seg): verts.append(Vector((rr * math.cos(2 * math.pi * i / seg), rr * math.sin(2 * math.pi * i / seg), z)))
    verts.append(Vector((0, 0, 1))); top = len(verts) - 1
    faces = []
    for i in range(seg): faces.append([0, 1 + (i + 1) % seg, 1 + i])
    for j in range(rings - 2):
        for i in range(seg):
            a = 1 + j * seg + i; b_ = 1 + j * seg + (i + 1) % seg
            faces.append([a, b_, b_ + seg, a + seg])
    base = 1 + (rings - 2) * seg
    for i in range(seg): faces.append([base + i, base + (i + 1) % seg, top])
    return verts, faces
LOBE['uv'] = uvsphere_template()

class Builder:
    """Accumulates many small pieces into one bmesh with a per-vertex tint."""
    def __init__(s, name, mat): s.name, s.mat = name, mat; s.bm = bmesh.new(); s.tints = []
    def add(s, verts, faces, tint):
        vs = [s.bm.verts.new(tuple(v)) for v in verts]
        for f in faces:
            try: s.bm.faces.new([vs[i] for i in f])
            except ValueError: pass
        s.tints.extend([tint] * len(vs))
    def finish(s, smooth=True):
        o = mesh_obj(s.name, s.bm, s.mat, smooth=smooth)
        t = s.tints; set_tint(o.data, lambda i, co: t[i] if i < len(t) else (0.1, 0.15, 0.05, 0.0))
        return o

LEAF = Builder("Leaves", M_LEAVES)
BARK = Builder("Bark", M_BARK)

def lobe(centre, radius, squash, lod, rnd, tint, flat_bottom=0.35):
    tv, tf = LOBE[lod]
    seed = Vector((rnd.uniform(0, 100), rnd.uniform(0, 100), rnd.uniform(0, 100)))
    out = []
    for v in tv:
        n = noise.noise(v * 1.4 + seed) * 0.28 + noise.noise(v * 3.1 + seed) * 0.10
        p = v * (1.0 + n)
        p.z *= squash
        if p.z < -flat_bottom: p.z = -flat_bottom + (p.z + flat_bottom) * 0.35
        out.append(centre + p * radius)
    LEAF.add(out, tf, tint)

def trunk(base, top, r0, r1, sides=6):
    """A tapered trunk (a cylinder from base to top), sunk a little into the ground."""
    axis = (top - base); L = axis.length; axis.normalize()
    side = axis.orthogonal().normalized(); side2 = axis.cross(side)
    vs = []; fs = []
    for k, (p, r) in enumerate(((base, r0), (top, r1))):
        for i in range(sides):
            a = 2 * math.pi * i / sides
            vs.append(p + (side * math.cos(a) + side2 * math.sin(a)) * r)
    for i in range(sides):
        j = (i + 1) % sides; fs.append([i, j, sides + j, sides + i])
    BARK.add(vs, fs, (1, 1, 1, 0))

SPECIES = {   # leaf tint (linear), crown shape
    "oak":    ((0.065, 0.10, 0.028), 0.42, 0.72),
    "elm":    ((0.075, 0.115, 0.03), 0.36, 0.95),
    "beech":  ((0.09, 0.125, 0.032), 0.40, 0.8),
    "poplar": ((0.085, 0.13, 0.04), 0.14, 2.6),
    "ash":    ((0.10, 0.14, 0.05), 0.37, 0.8),
    "fruit":  ((0.10, 0.15, 0.045), 0.42, 0.7),
}
TREES = []
def tree(x, y, H, kind, rnd, lod=1, nlobes=4, with_trunk=True, lean=0.0):
    tint0, crw, sq = SPECIES[kind]
    k = rnd.uniform(0.85, 1.18); hue = rnd.uniform(-0.012, 0.012)
    tint = (tint0[0] * k + hue, tint0[1] * k, tint0[2] * k * rnd.uniform(0.8, 1.2), 0.0)
    z0 = h(x, y)
    ldir = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * lean
    Rc = H * crw
    cz = z0 + H - Rc * sq * 1.0
    centre = Vector((x, y, cz)) + ldir * H
    if with_trunk:
        trunk(Vector((x, y, z0 - 0.03)), centre - Vector((0, 0, Rc * sq * 0.2)), H * 0.016 + 0.004, H * 0.008 + 0.002)
        if kind not in ("poplar",) and H > 0.8:
            for b_ in range(2):
                a = rnd.uniform(0, 2 * math.pi)
                bt = centre + Vector((math.cos(a) * Rc * 0.55, math.sin(a) * Rc * 0.55, rnd.uniform(-0.1, 0.25) * Rc))
                bb = Vector((x, y, z0)) + (centre - Vector((x, y, z0))) * rnd.uniform(0.55, 0.7)
                trunk(bb, bt, H * 0.007 + 0.002, H * 0.003 + 0.001, sides=4)
    if kind == "poplar":
        for i in range(nlobes):
            t = i / max(1, nlobes - 1)
            c = Vector((x, y, z0 + H * (0.30 + 0.55 * t))) + ldir * H * t + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * Rc * 0.2
            lobe(c, Rc * (1.0 - 0.35 * t) * rnd.uniform(0.9, 1.1), 1.7, lod, rnd, tint, flat_bottom=0.8)
    else:
        lobe(centre, Rc * rnd.uniform(0.78, 0.9), sq, lod, rnd, tint)
        for i in range(nlobes - 1):
            a = rnd.uniform(0, 2 * math.pi) + i * 2.1
            off = Vector((math.cos(a), math.sin(a), rnd.uniform(-0.55, 0.35) * sq)) * Rc * rnd.uniform(0.5, 0.7)
            lobe(centre + off, Rc * rnd.uniform(0.5, 0.68), sq * rnd.uniform(0.9, 1.15), lod, rnd, tint)
    TREES.append((x, y, H))

def lod_for(x, y):
    r = math.hypot(x, y)
    return (2, 6) if r < 10 else (1, 6) if r < 12 else (1, 4) if r < 25 else (1, 3) if r < 45 else ('uv', 2)

# the woods "of half a stang": tallest trees seven feet (2.1 m), lower at the edges, mixed species
rw = random.Random(31)
for wi, (wx, wy, wr) in enumerate(WOODS):
    n = int(wr * wr * 0.32)
    pts = []
    tries = 0
    while len(pts) < n and tries < 2000:
        tries += 1
        a = rw.uniform(0, 2 * math.pi); rr = wr * math.sqrt(rw.random()) * (1.0 + 0.2 * math.sin(3 * a + wi))
        px, py = wx + rr * math.cos(a), wy + rr * math.sin(a)
        if any(math.hypot(px - qx, py - qy) < 1.15 for qx, qy, _ in pts): continue
        if is_coastal(px, py, -4.0): continue
        pts.append((px, py, rr / wr))
    kinds = ["oak", "oak", "elm", "beech", "ash"]
    for px, py, edge in pts:
        H = (2.1 - 0.9 * edge ** 2) * rw.uniform(0.82, 1.0)
        lod, nl = lod_for(px, py)
        inner = edge < 0.55
        tree(px, py, H, rw.choice(kinds), rw, lod=lod, nlobes=max(2, nl - (1 if inner else 0)), with_trunk=not inner or rw.random() < 0.3)

# hedgerow trees and a few lone trees on the common, an old elm (the tallest, seven feet) left of the view
LONE = [(-7.5, 5.5, 2.1, "elm"), (9.5, -7.0, 1.55, "ash"), (6.0, 16.5, 1.25, "oak"), (-14.5, 18.0, 1.9, "poplar"),
        (-12.8, 21.5, 1.75, "poplar"), (11.5, 12.0, 0.9, "beech"), (-5.0, -12.5, 1.6, "beech")]
for x, y, H, k in LONE:
    lod, nl = lod_for(x, y)
    tree(x, y, H, k, rw, lod=lod, nlobes=nl + (1 if math.hypot(x, y) < 10 else 0), lean=0.04)

# the temple orchard behind the gorse, south-west of the temple: small fruit trees in rows, some missing
ox, oy, oa = -5.0, -6.6, 0.30
for i in range(4):
    for j in range(3):
        if rw.random() < 0.15: continue
        lx, ly = (i - 1.5) * 0.75 + rw.uniform(-0.08, 0.08), (j - 1.0) * 0.75 + rw.uniform(-0.08, 0.08)
        x = ox + lx * math.cos(oa) - ly * math.sin(oa); y = oy + lx * math.sin(oa) + ly * math.cos(oa)
        tree(x, y, rw.uniform(0.42, 0.62), "fruit", rw, lod=1, nlobes=2, lean=0.08)

# ----------------------------------------------------------------------------- hedges along the field edges (same layout as the shader)
c_, s_ = math.cos(FIELD_TH), math.sin(FIELD_TH)
def xy_of(u, v): return u * c_ - v * s_, u * s_ + v * c_
def warp_v(u): return 1.3 * math.sin(u / 23 + 1.3) + 0.7 * math.sin(u / 9.7 + 0.2)
def warp_u(v): return 1.1 * math.sin(v / 19 + 0.5)
def Wrow(k): return 10.5 + 3 * frac(k * 0.381966 + 0.7)
def shrow(k): return frac(k * 0.618034 + 0.13)
HEDGE_R = 46.0
def hedge_ok(x, y):
    if math.hypot(x, y) > HEDGE_R: return False
    if is_common(x, y, 0.35) or is_coastal(x, y, 0.35) or in_wood(x, y, 0.6) or in_town(x, y, 1.0): return False
    if road_dist(x, y) < 0.75: return False
    return True

polylines = []
for k in range(-6, 7):                                   # boundaries between rows of fields
    pts = []
    for i in range(-160, 161):
        u = i * 0.5; v = 12 * k - warp_v(u)
        pts.append(xy_of(u, v))
    polylines.append(pts)
for k in range(-6, 6):                                   # boundaries between fields within a row
    W = Wrow(k); sh = shrow(k)
    for mm in range(-10, 11):
        pts = []
        for i in range(-60, 61):
            v = 12 * k + i * 0.25
            u = (mm - sh) * W - warp_u(v)
            if math.floor((v + warp_v(u)) / 12) != k: continue
            pts.append(xy_of(u, v))
        if len(pts) > 2: polylines.append(pts)
# the hedge round the common (with its gaps for the highway)
pts = []
for i in range(0, 721):
    phi = 2 * math.pi * i / 720; rr = common_rlim(phi)
    pts.append((COMMON_C[0] + rr * math.cos(phi), COMMON_C[1] + rr * math.sin(phi)))
polylines.append(pts)

def hedge_ok_common(x, y):
    if is_coastal(x, y, 0.5) or road_dist(x, y) < 0.8 or in_wood(x, y, 0.3): return False
    return True

runs = []
for pi_, pl in enumerate(polylines):
    is_c = (pi_ == len(polylines) - 1)
    cur = []
    for (x, y) in pl:
        ok = hedge_ok_common(x, y) if is_c else hedge_ok(x, y)
        if ok: cur.append((x, y))
        elif cur: runs.append(cur); cur = []
    if cur: runs.append(cur)

HEDGE = Builder("Hedges", M_HEDGE)
rh = random.Random(77)
def build_hedge(run):
    # resample by length, add field-gate gaps now and then
    L = [0.0]
    for a, b_ in zip(run, run[1:]): L.append(L[-1] + math.hypot(b_[0] - a[0], b_[1] - a[1]))
    total = L[-1]
    if total < 1.5: return
    rmid = min(math.hypot(*p) for p in run)
    ds = 0.40 if rmid < 14 else 0.7 if rmid < 26 else 1.2 if rmid < 36 else 1.8
    n = max(2, int(total / ds) + 1)
    def at(t):
        for i in range(len(L) - 1):
            if L[i + 1] >= t:
                f = (t - L[i]) / max(1e-6, L[i + 1] - L[i])
                return (run[i][0] + (run[i + 1][0] - run[i][0]) * f, run[i][1] + (run[i + 1][1] - run[i][1]) * f)
        return run[-1]
    seed = rh.uniform(0, 100)
    Hh = rh.uniform(0.10, 0.20); Ww = rh.uniform(0.15, 0.24)
    tint = (0.055 * rh.uniform(0.85, 1.2), 0.085 * rh.uniform(0.9, 1.15), 0.028, 0.0)
    # optional gap (a field gate)
    gap = None
    if total > 6 and rh.random() < 0.35:
        g0 = rh.uniform(1.0, total - 2.0); gap = (g0, g0 + rh.uniform(0.35, 0.6))
    segs = [[]]
    for i in range(n):
        t = total * i / (n - 1)
        if gap and gap[0] < t < gap[1]:
            if segs[-1]: segs.append([])
            continue
        segs[-1].append(t)
    for seg in segs:
        if len(seg) < 2: continue
        ring = []
        five = rmid < 22
        for t in seg:
            p = at(t); q = at(min(total, t + 0.05)); p0 = at(max(0, t - 0.05))
            tan = Vector((q[0] - p0[0], q[1] - p0[1], 0)).normalized(); nrm = Vector((-tan.y, tan.x, 0))
            nn = noise.noise(Vector((t * 0.9, seed, 0.5)))
            hh = Hh * (1.0 + 0.45 * nn + 0.30 * noise.noise(Vector((t * 2.6, seed, 2.0))) + 0.15 * noise.noise(Vector((t * 7.0, seed, 3.0))))
            ww = Ww * (1.0 + 0.35 * noise.noise(Vector((t * 1.7, seed, 4.0))) + 0.15 * noise.noise(Vector((t * 5.3, seed, 6.0))))
            off = nrm * (0.04 * noise.noise(Vector((t * 0.6, seed, 7.0))) + 0.025 * noise.noise(Vector((t * 4.0, seed, 9.0))))
            z = h(p[0], p[1])
            c = Vector((p[0], p[1], z)) + off
            if five:
                ring.append([c - nrm * ww * 0.5 + Vector((0, 0, -0.03)), c - nrm * ww * 0.42 + Vector((0, 0, hh * 0.62)),
                             c + Vector((0, 0, hh)), c + nrm * ww * 0.42 + Vector((0, 0, hh * 0.62)), c + nrm * ww * 0.5 + Vector((0, 0, -0.03))])
            else:
                ring.append([c - nrm * ww * 0.5 + Vector((0, 0, -0.03)), c - nrm * ww * 0.3 + Vector((0, 0, hh)),
                             c + nrm * ww * 0.3 + Vector((0, 0, hh)), c + nrm * ww * 0.5 + Vector((0, 0, -0.03))])
        nv = len(ring[0]); verts = [v for r in ring for v in r]; faces = []
        for i in range(len(ring) - 1):
            for j in range(nv - 1):
                a = i * nv + j; faces.append([a, a + 1, a + nv + 1, a + nv])
        faces.append(list(range(nv - 1, -1, -1)))
        faces.append([(len(ring) - 1) * nv + j for j in range(nv)])
        HEDGE.add(verts, faces, tint)
        # bushes standing proud of the hedge (hawthorn, elder) near the reader
        if rmid < 24:
            for t in seg[::max(1, int(2.6 / ds))]:
                if rh.random() < 0.55: continue
                p = at(t); z = h(p[0], p[1])
                bs = Hh * rh.uniform(0.8, 1.3)
                bt = (tint[0] * rh.uniform(0.9, 1.4), tint[1] * rh.uniform(0.95, 1.3), tint[2], 0.15 if rh.random() < 0.3 else 0.0)
                lobe(Vector((p[0], p[1], z + bs * 0.9)), bs * 0.85, 0.9, 1 if rmid < 14 else 'uv', rh, bt, flat_bottom=0.6)
for run in runs: build_hedge(run)

# hedgerow trees standing in the hedges
cand = [p for run in runs for p in run[::6]]
rw.shuffle(cand)
placed = []
for (x, y) in cand:
    if len(placed) >= 14: break
    if math.hypot(x, y) < 9 or abs(x) < 4 and y > 0 and y < 40: continue     # keep the view behind the page open
    if any(math.hypot(x - a, y - b_) < 9 for a, b_ in placed): continue
    placed.append((x, y))
    lod, nl = lod_for(x, y)
    tree(x, y, rw.uniform(1.2, 1.95), rw.choice(["oak", "ash", "elm", "poplar"]), rw, lod=lod, nlobes=nl, lean=0.05)

# gorse and broom on the bank above the beach and at the road verges, flowering
for i in range(26):
    if i < 20:
        y = rw.uniform(-26, 24); dd = rw.uniform(8.5, 15.0); x = coast(y) - dd
    else:
        x = rw.uniform(-12, 12); y = ROAD_Y + rw.choice((-1, 1)) * rw.uniform(0.55, 0.9)
    if math.hypot(x, y) < 2.5: continue
    sz = rw.uniform(0.06, 0.16)
    z0 = h(x, y)
    tint = (0.06, 0.095, 0.03, rw.uniform(0.45, 0.9))
    for k in range(rw.randint(1, 3)):
        c = Vector((x + rw.uniform(-1, 1) * sz, y + rw.uniform(-1, 1) * sz, z0 + sz * 0.35))
        lobe(c, sz * rw.uniform(0.7, 1.0), 0.65, 1 if math.hypot(x, y) < 20 else 'uv', rw, tint, flat_bottom=0.5)

# ----------------------------------------------------------------------------- the ancient temple (Gulliver's house)
gx, gy = GATE
TX0, TX1 = -TW / 2, TW / 2
TYF, TYB = TY0, TY0 - TD
zs = [h(x, y) for x in (TX0, 0, TX1) for y in (TYF, (TYF + TYB) / 2, TYB)]
ZB, ZT = min(zs) - 0.18, max(zs) + 0.05          # foundation bottom (buried) and floor level
plinth = box("Temple_Plinth", (TW + 0.16, TD + 0.16, ZT - ZB), (0, (TYF + TYB) / 2, (ZB + ZT) / 2), M_STONE)
shell = box("Temple_Shell", (TW, TD, TH), (0, (TYF + TYB) / 2, ZT + TH / 2), M_STONE)
WT = 0.24
inner = box("cut_Inner", (TW - 2 * WT, TD - 2 * WT, TH), (0, (TYF + TYB) / 2, ZT + TH / 2 + 0.02), M_STONE)
cut(shell, inner)
def arch_cutter(name, cx, cy, w, z0, zspring, axis='y', depth=0.6):
    """Rectangle from z0 to zspring plus a half-round head: a doorway or a lancet."""
    if axis == 'y':
        a = box(name, (w, depth, zspring - z0), (cx, cy, (z0 + zspring) / 2), M_STONE)
        c = cyl(name + "_head", w / 2, depth, (cx, cy, zspring), M_STONE, verts=16, rot=(math.pi / 2, 0, 0))
    else:
        a = box(name, (depth, w, zspring - z0), (cx, cy, (z0 + zspring) / 2), M_STONE)
        c = cyl(name + "_head", w / 2, depth, (cx, cy, zspring), M_STONE, verts=16, rot=(0, math.pi / 2, 0))
    return a, c
GATE_W, GATE_H = 0.61, 1.22
for o in arch_cutter("cut_Gate", gx, TYF, GATE_W, ZT - 0.01, ZT + GATE_H - GATE_W / 2): cut(shell, o)
for s in (-1, 1):                                   # the two little windows by the gate, six inches from the ground
    cut(shell, box(f"cut_LowWin{s}", (0.12, 0.6, 0.15), (gx + s * 0.62, TYF, ZT + 0.07 + 0.075), M_STONE))
for s in (-1, 1):                                   # lancets down the sides
    for k in range(3):
        yy = TYF - 1.15 - k * 1.45
        for o in arch_cutter(f"cut_Lancet{s}{k}", s * TW / 2, yy, 0.16, ZT + 0.85, ZT + 1.45, axis='x'): cut(shell, o)
for s in (-1, 1):                                   # empty niches on the front ("all the ornaments carried away")
    for o in arch_cutter(f"cut_Niche{s}", s * 1.05, TYF + 0.02, 0.24, ZT + 1.05, ZT + 1.55, depth=0.16): cut(shell, o)
apply_mods(shell)
for o in [o for o in COLL.objects if o.name.startswith("cut_")]: bpy.data.objects.remove(o)
# dark interior (floor and a back screen so the open gate shows depth, not sky)
box("TempleInterior_Floor", (TW - 2 * WT - 0.02, TD - 2 * WT - 0.02, 0.02), (0, (TYF + TYB) / 2, ZT + 0.01), M_INTERIOR)
# niche shelves and the plinth course, string course, cornice
for s in (-1, 1):
    box(f"Temple_NicheSill{s}", (0.30, 0.10, 0.03), (s * 1.05, TYF + 0.03, ZT + 1.04), M_STONE)
box("Temple_StringCourse", (TW + 0.04, 0.05, 0.05), (0, TYF + 0.02, ZT + 1.80), M_STONE)
box("Temple_BaseCourse", (TW + 0.06, TD + 0.06, 0.10), (0, (TYF + TYB) / 2, ZT + 0.05), M_STONE)
for s in (-1, 1):
    box(f"Temple_Cornice{s}", (0.07, TD + 0.08, 0.06), (s * (TW / 2 + 0.01), (TYF + TYB) / 2, ZT + TH - 0.02), M_STONE)
# arch voussoirs round the gate
for i in range(9):
    a = math.pi * i / 8
    cx = gx + math.cos(a) * (GATE_W / 2 + 0.05); cz = ZT + GATE_H - GATE_W / 2 + math.sin(a) * (GATE_W / 2 + 0.05)
    box(f"Temple_Voussoir{i}", (0.07, 0.05, 0.11), (cx, TYF + 0.015, cz), M_STONE, rot=(0, -(a - math.pi / 2), 0))
for s in (-1, 1):
    box(f"Temple_GateJamb{s}", (0.07, 0.05, GATE_H - GATE_W / 2), (gx + s * (GATE_W / 2 + 0.035), TYF + 0.015, ZT + (GATE_H - GATE_W / 2) / 2), M_STONE)
# the gate leaves standing open inward
for s in (-1, 1):
    hinge = Vector((gx + s * GATE_W / 2, TYF - WT + 0.02, ZT))
    ang = math.radians(-90 + s * -18) if s < 0 else math.radians(-90 + 18)
    dirv = Vector((-s * math.cos(math.radians(70)), -math.sin(math.radians(70)), 0))
    c = hinge + dirv * (GATE_W / 4) + Vector((0, 0, 0.5))
    box(f"Temple_GateLeaf{s}", (GATE_W / 2 - 0.01, 0.025, 1.0), tuple(c), M_WOOD, rot=(0, 0, math.atan2(dirv.y, dirv.x)))
# the roof: a gable, stone slates, the pediment over the gate with a round window (dark)
RIDGE = ZT + TH + 0.95; EAVE = ZT + TH; OV = 0.10
pitch = math.atan((RIDGE - EAVE) / (TW / 2 + OV))
Ls = (TW / 2 + OV) / math.cos(pitch)
for s in (-1, 1):
    mid = Vector((s * (TW / 2 + OV) / 2, (TYF + TYB) / 2, (RIDGE + EAVE) / 2 - 0.0))
    nrm = Vector((s * math.sin(pitch), 0, math.cos(pitch)))
    box(f"Temple_Roof{s}", (Ls + 0.02, TD + 0.16, 0.05), tuple(mid + nrm * 0.03), M_ROOF, rot=(0, s * pitch, 0))
box("Temple_Ridge", (0.07, TD + 0.18, 0.06), (0, (TYF + TYB) / 2, RIDGE + 0.04), M_ROOF)
for y0, y1, nm in ((TYF - WT, TYF, "Front"), (TYB, TYB + WT, "Back")):
    ped = prism_xz(f"Temple_Gable{nm}", [(TX0, EAVE - 0.01), (TX1, EAVE - 0.01), (0, RIDGE)], y0, y1, M_STONE)
    if nm == "Front":
        oc = cyl("cut_Oculus", 0.15, 0.8, (0, TYF, EAVE + 0.38), M_STONE, verts=20, rot=(math.pi / 2, 0, 0))
        cut(ped, oc); apply_mods(ped); bpy.data.objects.remove(oc)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.165, minor_radius=0.025, major_segments=20, minor_segments=4,
                                         location=(0, TYF + 0.01, EAVE + 0.38), rotation=(math.pi / 2, 0, 0))
        tor = bpy.context.active_object; tor.name = "Temple_OculusRing"; _finish(tor, M_STONE, smooth=True)
box("Temple_PedimentCornice", (TW + 0.10, 0.06, 0.05), (0, TYF + 0.02, EAVE), M_STONE)
# buttresses
for s in (-1, 1):
    for k in range(4):
        yy = TYF - 0.42 - k * 1.45
        if k == 3: yy = TYB + 0.3
        bz = h(s * (TW / 2 + 0.1), yy)
        box(f"Temple_Buttress{s}{k}", (0.20, 0.22, EAVE - 0.35 - ZB), (s * (TW / 2 + 0.10), yy, (ZB + EAVE - 0.35) / 2), M_STONE)
        box(f"Temple_ButtressCap{s}{k}", (0.24, 0.24, 0.06), (s * (TW / 2 + 0.10), yy, EAVE - 0.33), M_STONE, rot=(0, s * 0.35, 0))
for s in (-1, 1):
    box(f"Temple_FrontButtress{s}", (0.24, 0.22, EAVE - 0.2 - ZB), (s * (TW / 2 - 0.08), TYF + 0.11, (ZB + EAVE - 0.2) / 2), M_STONE)
# the bell tower at the back, with a pyramid roof and belfry openings
BT = 1.3; BTY = TYB - BT / 2 + 0.25; BTH = ZT + 3.35
tower = box("Temple_Tower", (BT, BT, BTH - ZB), (0, BTY, (ZB + BTH) / 2), M_STONE)
for k, (ax, dx, dy) in enumerate((('y', 0, BT / 2), ('y', 0, -BT / 2), ('x', BT / 2, 0), ('x', -BT / 2, 0))):
    for o in arch_cutter(f"cut_Belfry{k}", dx, BTY + dy, 0.26, ZT + 2.62, ZT + 2.95, axis=ax, depth=0.5): cut(tower, o)
apply_mods(tower)
for o in [o for o in COLL.objects if o.name.startswith("cut_")]: bpy.data.objects.remove(o)
box("Temple_TowerFill", (BT - 0.3, BT - 0.3, 0.9), (0, BTY, ZT + 2.75), M_INTERIOR)
box("Temple_TowerCornice", (BT + 0.08, BT + 0.08, 0.07), (0, BTY, BTH), M_STONE)
cyl("Temple_TowerRoof", (BT + 0.12) / math.sqrt(2), 0.95, (0, BTY, BTH + 0.475 + 0.03), M_ROOF, verts=4, r2=0.0, rot=(0, 0, math.pi / 4))
anchor("temple.gate", (gx, gy, ZT))

# ----------------------------------------------------------------------------- the turret across the highway (five feet high)
tx_, ty_ = TURRET; tz = h(tx_, ty_)
TR = 0.30
cyl("Turret_Body", TR, 1.38 + 0.15, (tx_, ty_, tz - 0.15 + (1.38 + 0.15) / 2), M_STONE, verts=18)
cyl("Turret_Batter", TR + 0.06, 0.28, (tx_, ty_, tz + 0.06), M_STONE, verts=18, r2=TR)
cyl("Turret_Corbel", TR + 0.05, 0.06, (tx_, ty_, tz + 1.36), M_STONE, verts=18)
for i in range(9):
    a = 2 * math.pi * i / 9
    box(f"Turret_Merlon{i}", (0.10, 0.07, 0.12), (tx_ + math.cos(a) * (TR + 0.015), ty_ + math.sin(a) * (TR + 0.015), tz + 1.45), M_STONE, rot=(0, 0, a + math.pi / 2))
cyl("Turret_Parapet", TR + 0.04, 0.05, (tx_, ty_, tz + 1.415), M_STONE, verts=18)
cyl("Turret_Floor", TR - 0.01, 0.02, (tx_, ty_, tz + 1.40), M_INTERIOR, verts=12)
# the door (facing the highway) and arrow slits (dark insets)
a0 = math.atan2(gy - ty_, gx - tx_)
box("Turret_Door", (0.03, 0.11, 0.20), (tx_ + math.cos(a0) * (TR - 0.005), ty_ + math.sin(a0) * (TR - 0.005), tz + 0.10), M_WOOD, rot=(0, 0, a0))
for k, (aa, zz) in enumerate(((a0 + 0.9, 0.55), (a0 - 1.6, 0.85), (a0 + 2.6, 1.10))):
    box(f"Turret_Slit{k}", (0.02, 0.022, 0.09), (tx_ + math.cos(aa) * (TR - 0.004), ty_ + math.sin(aa) * (TR - 0.004), tz + zz), M_INTERIOR, rot=(0, 0, aa))
anchor("turret", (tx_, ty_, tz))

# ----------------------------------------------------------------------------- the chains: 91 watch chains, bundled in three, out of the left window
CH_START = Vector((gx - 0.62, TYF - 0.10, ZT + 0.12))
def chain_bundle(name, ctrl, r):
    """A tube along a polyline of control points on the ground, sunk a little into the turf."""
    pts = []
    for (a, b_) in zip(ctrl, ctrl[1:]):
        L = (b_ - a).length; n = max(1, int(L / 0.05))
        for i in range(n): pts.append(a + (b_ - a) * (i / n))
    pts.append(ctrl[-1])
    # smooth (Chaikin-ish) and drop onto the ground where outside the temple
    for _ in range(2):
        pts = [pts[0]] + [(pts[i - 1] + pts[i] * 2 + pts[i + 1]) / 4 for i in range(1, len(pts) - 1)] + [pts[-1]]
    for p in pts:
        if p.y > TYF + 0.06: p.z = h(p.x, p.y) + r * 0.6
    bm = bmesh.new(); sides = 6; rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        sd = t.cross(Vector((0, 0, 1))); sd = sd.normalized() if sd.length > 1e-4 else Vector((1, 0, 0))
        up = sd.cross(t).normalized()
        tw = i * 0.35
        rings.append([bm.verts.new(p + (sd * math.cos(2 * math.pi * k / sides + tw) + up * math.sin(2 * math.pi * k / sides + tw)) * r * (1.0 + 0.12 * math.sin(i * 1.7 + k)))
                      for k in range(sides)])
    for i in range(len(rings) - 1):
        for k in range(sides):
            j = (k + 1) % sides; bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))
    bm.faces.new(rings[-1])
    return mesh_obj(name, bm, M_IRON, smooth=True)
ENDS = [Vector((-0.20, -0.22, 0)), Vector((-0.10, -0.28, 0)), Vector((-0.26, -0.12, 0))]
for k in range(3):
    off = Vector(((k - 1) * 0.022, 0, (k - 1) * 0.012))
    ctrl = [CH_START + off + Vector((0, -0.12, 0)), CH_START + off, Vector((CH_START.x + off.x, TYF + 0.14, 0)),
            Vector((-0.66 + k * 0.05, -1.0 + k * 0.03, 0)), Vector((-0.42 + k * 0.10, -0.80 - k * 0.04, 0)),
            Vector((-0.55 + k * 0.12, -0.50, 0)), Vector((-0.36 + k * 0.06, -0.32 + k * 0.02, 0)), ENDS[k]]
    chain_bundle(f"Chain{k}", ctrl, 0.0085 - k * 0.0012)
# the six-and-thirty padlocks, unlocked and dropped in a little heap where the chains end
for i in range(14):
    a = random.uniform(0, 2 * math.pi); rr = random.uniform(0.0, 0.07)
    x, y = -0.18 + math.cos(a) * rr, -0.22 + math.sin(a) * rr
    box(f"Padlock{i}", (0.022, 0.009, 0.026), (x, y, h(x, y) + 0.004), M_IRON, rot=(math.radians(random.uniform(70, 110)), 0, random.uniform(0, math.pi)))

# ----------------------------------------------------------------------------- the domestics' tents on each side of the door
rt = random.Random(5)
def tent(x, y, yaw, L, Wd, Ht, bell=False):
    z = h(x, y) - 0.01
    if bell:
        cyl(f"Tent_{x:.1f}_{y:.1f}", Wd / 2, Ht, (x, y, z + Ht / 2), M_CANVAS, verts=9, r2=0.004)
        return
    R = Matrix.Rotation(yaw, 3, 'Z')
    def P(a, b_, c): return Vector((x, y, z)) + R @ Vector((a, b_, c))
    bm = bmesh.new()
    v = [bm.verts.new(P(-L / 2, -Wd / 2, 0)), bm.verts.new(P(L / 2, -Wd / 2, 0)), bm.verts.new(P(L / 2, Wd / 2, 0)), bm.verts.new(P(-L / 2, Wd / 2, 0)),
         bm.verts.new(P(-L / 2, 0, Ht)), bm.verts.new(P(L / 2, 0, Ht))]
    bm.faces.new((v[0], v[1], v[5], v[4])); bm.faces.new((v[2], v[3], v[4], v[5])); bm.faces.new((v[1], v[2], v[5])); bm.faces.new((v[3], v[0], v[4]))
    mesh_obj(f"Tent_{x:.1f}_{y:.1f}", bm, M_CANVAS)
for s in (-1, 1):
    for i in range(6):
        x = s * (TW / 2 + 0.55 + (i % 3) * 0.42 + rt.uniform(-0.05, 0.05)); y = TYF - 0.25 - (i // 3) * 0.50 + rt.uniform(-0.06, 0.06)
        tent(x, y, rt.uniform(-0.15, 0.15), rt.uniform(0.22, 0.30), rt.uniform(0.15, 0.19), rt.uniform(0.11, 0.15), bell=(i == 4))

# ----------------------------------------------------------------------------- the engine that carried Gulliver here, left on the common
# "a frame of wood raised three inches from the ground, about seven feet long, and four wide, moving upon twenty-two wheels"
EN_C, EN_YAW = Vector((-4.3, 0.9, 0.0)), math.radians(74)
ER = Matrix.Rotation(EN_YAW, 3, 'Z')
def ep(a, b_, c=0.0):
    p = EN_C + ER @ Vector((a, b_, 0.0)); return Vector((p.x, p.y, h(p.x, p.y) + c))
EL, EW, WR_ = 2.13, 1.22, 0.034
for s in (-1, 1):
    box(f"Engine_Beam{s}", (EL, 0.05, 0.035), tuple(ep(0, s * (EW / 2 - 0.05), WR_ + 0.012)), M_WOOD, rot=(0, 0, EN_YAW))
for k in range(6):
    box(f"Engine_Cross{k}", (0.04, EW, 0.025), tuple(ep(-EL / 2 + 0.06 + k * (EL - 0.12) / 5, 0, WR_ + 0.038)), M_WOOD, rot=(0, 0, EN_YAW))
for k in range(11):                                  # planks of the bed, a few missing
    if k in (3, 8): continue
    box(f"Engine_Plank{k}", (0.17, EW - 0.04, 0.010), tuple(ep(-EL / 2 + 0.10 + k * (EL - 0.2) / 10, 0, WR_ + 0.056)), M_WOOD, rot=(0, 0, EN_YAW + random.uniform(-0.02, 0.02)))
for s in (-1, 1):
    for k in range(11):
        c = ep(-EL / 2 + 0.08 + k * (EL - 0.16) / 10, s * (EW / 2 + 0.004), WR_ - 0.004)
        cyl(f"Engine_Wheel{s}{k}", WR_, 0.014, tuple(c), M_WOOD, verts=8, rot=(math.pi / 2, 0, EN_YAW))
box("Engine_Pole", (0.55, 0.03, 0.025), tuple(ep(EL / 2 + 0.27, 0, 0.03)), M_WOOD, rot=(0, -0.08, EN_YAW))

# ----------------------------------------------------------------------------- rocks along the shore, partly buried
ROCKS = Builder("Rocks", M_ROCK)
rr_ = random.Random(11)
rock_spots = [(rr_.uniform(-22, 22), rr_.uniform(-1.0, 9.0), rr_.uniform(0.06, 0.32)) for _ in range(12)]
rock_spots += [(-14 + rr_.uniform(-2, 2), rr_.uniform(-4.0, 0.5), rr_.uniform(0.15, 0.5)) for _ in range(6)]
rock_spots += [(rr_.uniform(-8, 8), rr_.uniform(9.5, 13), rr_.uniform(0.04, 0.12)) for _ in range(5)]
for (yy, dd, sz) in rock_spots:
    x, y = coast(yy) - dd, yy
    if math.hypot(x, y) > 70: continue
    tv, tf = LOBE[1]
    seed = Vector((rr_.uniform(0, 50), rr_.uniform(0, 50), 0))
    sq = (rr_.uniform(0.8, 1.3), rr_.uniform(0.6, 1.0), rr_.uniform(0.35, 0.6))
    rot = Matrix.Rotation(rr_.uniform(0, math.pi), 3, 'Z')
    z0 = h(x, y)
    out = []
    for v in tv:
        n = noise.noise(v * 1.2 + seed) * 0.25 + noise.noise(v * 3.0 + seed) * 0.08
        p = v * (1 + n); p = Vector((p.x * sq[0], p.y * sq[1], p.z * sq[2]))
        out.append(Vector((x, y, z0 - sz * 0.22)) + rot @ (p * sz))
    ROCKS.add(out, tf, (1, 1, 1, 0))

# ----------------------------------------------------------------------------- the town on the left hand (backdrop)
TOWN = Builder("far.town", M_TOWN)
rtn = random.Random(1726)
cT, sT = math.cos(TOWN_A), math.sin(TOWN_A)
def tw(lu, lv): return (TOWN_C[0] + lu * cT - lv * sT, TOWN_C[1] + lu * sT + lv * cT)
def tbox(lu, lv, du, dv, z0, z1, tint, yaw=0.0):
    a = TOWN_A + yaw; ca, sa = math.cos(a), math.sin(a); cx, cy = tw(lu, lv)
    def P(u, v_, z): return (cx + u * ca - v_ * sa, cy + u * sa + v_ * ca, z)
    vs = [P(-du / 2, -dv / 2, z0), P(du / 2, -dv / 2, z0), P(du / 2, dv / 2, z0), P(-du / 2, dv / 2, z0),
          P(-du / 2, -dv / 2, z1), P(du / 2, -dv / 2, z1), P(du / 2, dv / 2, z1), P(-du / 2, dv / 2, z1)]
    TOWN.add(vs, [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [4, 5, 6, 7]], tint)
def troof(lu, lv, du, dv, z0, rh, tint, yaw=0.0, hip=False):
    a = TOWN_A + yaw; ca, sa = math.cos(a), math.sin(a); cx, cy = tw(lu, lv)
    def P(u, v_, z): return (cx + u * ca - v_ * sa, cy + u * sa + v_ * ca, z)
    if hip:
        vs = [P(-du / 2, -dv / 2, z0), P(du / 2, -dv / 2, z0), P(du / 2, dv / 2, z0), P(-du / 2, dv / 2, z0), P(0, 0, z0 + rh)]
        TOWN.add(vs, [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]], tint); return
    vs = [P(-du / 2, -dv / 2, z0), P(du / 2, -dv / 2, z0), P(du / 2, dv / 2, z0), P(-du / 2, dv / 2, z0), P(-du / 2, 0, z0 + rh), P(du / 2, 0, z0 + rh)]
    TOWN.add(vs, [[0, 1, 5, 4], [2, 3, 4, 5], [1, 2, 5], [3, 0, 4]], tint)
def tz(lu, lv): return h(*tw(lu, lv))
WALLC = (0.42, 0.38, 0.30, 0); LIME = [(0.55, 0.51, 0.42, 0), (0.50, 0.45, 0.36, 0), (0.46, 0.43, 0.38, 0), (0.58, 0.54, 0.46, 0)]
ROOFS = [(0.30, 0.12, 0.07, 0), (0.24, 0.10, 0.06, 0), (0.17, 0.15, 0.14, 0), (0.33, 0.17, 0.10, 0), (0.20, 0.13, 0.09, 0)]
# the wall, two and a half feet high, with towers every ten feet (here every 6 m) and a gate on the south side
Hh_ = TOWN_H
for side in range(4):
    for k in range(8):
        t0 = -Hh_ + k * (2 * Hh_ / 8); t1 = t0 + 2 * Hh_ / 8; tm = (t0 + t1) / 2
        if side == 0: lu, lv, du, dv = tm, -Hh_, (t1 - t0), 0.32
        elif side == 1: lu, lv, du, dv = Hh_, tm, 0.32, (t1 - t0)
        elif side == 2: lu, lv, du, dv = tm, Hh_, (t1 - t0), 0.32
        else: lu, lv, du, dv = -Hh_, tm, 0.32, (t1 - t0)
        if side == 0 and abs(tm) < 3.0:                                 # the gate in the middle of the south wall
            for sg in (-1, 1):
                z0 = tz(sg * 3.6, lv) - 0.15; tbox(sg * 3.6, lv, 4.4, dv, z0, z0 + 0.91, WALLC)
            continue
        z0 = tz(lu, lv) - 0.15
        tbox(lu, lv, du, dv, z0, z0 + 0.15 + 0.76, WALLC)
    for k in range(9):
        t = -Hh_ + k * (2 * Hh_ / 8)
        lu, lv = [(t, -Hh_), (Hh_, t), (t, Hh_), (-Hh_, t)][side]
        z0 = tz(lu, lv) - 0.15
        tbox(lu, lv, 0.62, 0.62, z0, z0 + 0.15 + 1.05, WALLC)
        troof(lu, lv, 0.66, 0.66, z0 + 1.2, 0.35, ROOFS[2], hip=True)
for s in (-1, 1):                                                       # gate towers
    z0 = tz(s * 1.2, -Hh_) - 0.15
    tbox(s * 1.25, -Hh_, 0.8, 0.8, z0, z0 + 1.4, WALLC); troof(s * 1.25, -Hh_, 0.84, 0.84, z0 + 1.4, 0.5, ROOFS[0], hip=True)
# houses in blocks between the two great streets (5 ft wide) and the lanes; the palace in the middle
for i in range(-4, 4):
    for j in range(-4, 4):
        bu0 = -Hh_ + 1.4 + (i + 4) * ((2 * Hh_ - 2.8) / 8); bv0 = -Hh_ + 1.4 + (j + 4) * ((2 * Hh_ - 2.8) / 8)
        bw = (2 * Hh_ - 2.8) / 8 - 0.9
        cu, cv = bu0 + bw / 2, bv0 + bw / 2
        if abs(cu) < 1.5 or abs(cv) < 1.5: continue                     # the two great streets
        if abs(cu) < 8.5 and abs(cv) < 8.5: continue                    # the palace court
        nh = rtn.randint(2, 3)
        for k in range(nh):
            seg = bw / nh
            uu = bu0 + seg * (k + 0.5)
            vv = cv + rtn.uniform(-0.15, 0.15)
            z0 = tz(uu, vv) - 0.1
            ht = rtn.uniform(0.40, 0.95)
            lime = rtn.choice(LIME); rf = rtn.choice(ROOFS)
            tbox(uu, vv, seg * 0.96, bw * 0.9, z0, z0 + 0.1 + ht, lime)
            troof(uu, vv, seg * 1.0, bw * 0.94, z0 + 0.1 + ht, rtn.uniform(0.3, 0.5), rf)
# the palace: an inner wall two feet high, the courts, towers and the great hall
for side in range(4):
    lu, lv, du, dv = [(0, -8.5, 17, 0.25), (8.5, 0, 0.25, 17), (0, 8.5, 17, 0.25), (-8.5, 0, 0.25, 17)][side]
    z0 = tz(lu, lv) - 0.1; tbox(lu, lv, du, dv, z0, z0 + 0.7, LIME[3])
pz = tz(0, 0)
tbox(0, 1.5, 9.0, 4.0, pz - 0.1, pz + 1.6, LIME[3]); troof(0, 1.5, 9.2, 4.2, pz + 1.6, 0.9, ROOFS[2])
tbox(-4.5, -3.0, 3.0, 5.0, pz - 0.1, pz + 1.2, LIME[0]); troof(-4.5, -3.0, 3.2, 5.2, pz + 1.2, 0.7, ROOFS[2], yaw=math.pi / 2)
tbox(4.5, -3.0, 3.0, 5.0, pz - 0.1, pz + 1.2, LIME[0]); troof(4.5, -3.0, 3.2, 5.2, pz + 1.2, 0.7, ROOFS[2], yaw=math.pi / 2)
for (lu, lv, ht) in ((-5.5, 4.5, 2.6), (5.5, 4.5, 2.6), (0, 4.0, 3.4), (-5.5, -6.0, 2.0), (5.5, -6.0, 2.0)):
    z0 = tz(lu, lv) - 0.1
    tbox(lu, lv, 1.1, 1.1, z0, z0 + ht, LIME[3]); troof(lu, lv, 1.2, 1.2, z0 + ht, 1.0 if ht > 3 else 0.7, (0.12, 0.13, 0.15, 0), hip=True)
# two church towers in the quarters
for (lu, lv) in ((-14, 12), (13, -13)):
    z0 = tz(lu, lv) - 0.1
    tbox(lu, lv, 0.8, 0.8, z0, z0 + 2.0, LIME[2]); troof(lu, lv, 0.85, 0.85, z0 + 2.0, 1.1, (0.13, 0.13, 0.14, 0), hip=True)
anchor("town", (TOWN_C[0], TOWN_C[1], h(*TOWN_C)))

# ----------------------------------------------------------------------------- two of the emperor's men of war (nine feet long) offshore (backdrop)
SHIPS = Builder("far.ships", M_SHIPS)
def ship(x, y, yaw, L=2.7, beam=0.7, furled=False):
    R = Matrix.Rotation(yaw, 3, 'Z'); base = Vector((x, y, -1.985))
    def P(a, b_, c): return base + R @ Vector((a, b_, c))
    hull = (0.20, 0.13, 0.08, 0); dark = (0.06, 0.05, 0.04, 0); sail = (0.62, 0.58, 0.50, 0)
    # hull: a lofted shape, keel below the water, sheer rising at the bow and stern
    st = [(-L / 2, 0.55), (-L * 0.3, 1.0), (L * 0.15, 1.0), (L * 0.38, 0.7), (L / 2, 0.0)]
    vs = []; fs = []
    for i, (a, w) in enumerate(st):
        sheer = 0.32 + (0.12 if i == 0 else 0.0) + (0.06 if i == len(st) - 1 else 0.0)
        vs += [P(a, -beam / 2 * w, sheer), P(a, -beam / 2 * w * 0.8, -0.05), P(a, 0, -0.22), P(a, beam / 2 * w * 0.8, -0.05), P(a, beam / 2 * w, sheer)]
    for i in range(len(st) - 1):
        for k in range(4):
            a = i * 5 + k; fs.append([a, a + 5, a + 6, a + 1])
    fs.append([0, 1, 2, 3, 4][::-1])
    fs.append([20 + k for k in range(5)])
    SHIPS.add(vs, fs, hull)
    # deck
    SHIPS.add([P(-L / 2 + 0.05, -beam * 0.45, 0.30), P(L * 0.36, -beam * 0.33, 0.30), P(L * 0.36, beam * 0.33, 0.30), P(-L / 2 + 0.05, beam * 0.45, 0.30)], [[0, 1, 2, 3]], (0.30, 0.24, 0.16, 0))
    # three masts and their sails
    for mx, mh in ((-L * 0.28, 1.9), (0.0, 2.3), (L * 0.27, 1.8)):
        r0 = 0.025; side = 5; mv = []
        for zz in (0.3, 0.3 + mh):
            for k in range(side):
                a = 2 * math.pi * k / side; mv.append(P(mx + math.cos(a) * r0, math.sin(a) * r0, zz))
        SHIPS.add(mv, [[k, (k + 1) % side, side + (k + 1) % side, side + k] for k in range(side)], dark)
        for (z0, z1, w0, w1) in ((0.75, 1.45, 0.9, 0.75), (1.55, 2.05, 0.66, 0.5)):
            if z1 > 0.3 + mh: continue
            if furled:
                SHIPS.add([P(mx + 0.03, -w0 / 2, z1), P(mx + 0.03, w0 / 2, z1), P(mx + 0.03, w0 / 2, z1 - 0.06), P(mx + 0.03, -w0 / 2, z1 - 0.06)], [[0, 1, 2, 3], [3, 2, 1, 0]], sail)
            else:
                belly = 0.10
                sv = [P(mx + 0.03, -w0 / 2, z0), P(mx + 0.03 + belly, 0, z0), P(mx + 0.03, w0 / 2, z0),
                      P(mx + 0.03, -w1 / 2, z1), P(mx + 0.03 + belly * 0.7, 0, z1), P(mx + 0.03, w1 / 2, z1)]
                SHIPS.add(sv, [[0, 1, 4, 3], [1, 2, 5, 4], [3, 4, 1, 0], [4, 5, 2, 1]], sail)
    SHIPS.add([P(L / 2 - 0.05, 0, 0.35), P(L / 2 + 0.6, 0, 0.75), P(L / 2 + 0.62, 0, 0.73)], [[0, 1, 2]], dark)   # bowsprit
ship(54.0, 34.0, math.radians(200), furled=True)
ship(70.0, -10.0, math.radians(165))

# ----------------------------------------------------------------------------- finish builders
LEAF.finish(); BARK.finish(smooth=True); HEDGE.finish(); ROCKS.finish(); TOWN.finish(smooth=False); SHIPS.finish(smooth=False)

# ----------------------------------------------------------------------------- the sky dome
def sky_dome(name, radius=SKY_R, seg=48, rings=18, el_min=-10.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    els = [el_min + (89.0 - el_min) * (j / rings) ** 1.6 for j in range(rings + 1)]
    grid = []
    for el in els:
        e = math.radians(el)
        grid.append([bm.verts.new((radius * math.cos(e) * math.cos(2 * math.pi * i / seg), radius * math.cos(e) * math.sin(2 * math.pi * i / seg), radius * math.sin(e))) for i in range(seg)])
    pole = bm.verts.new((0, 0, radius))
    def v_of(el): return (el - el_min) / (90.0 - el_min)
    for j in range(rings):
        for i in range(seg):
            k = (i + 1) % seg
            f_ = bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][k], grid[j][k]))
            u0, u1 = i / seg, (i + 1) / seg
            for l, uv in zip(f_.loops, [(u0, v_of(els[j])), (u0, v_of(els[j + 1])), (u1, v_of(els[j + 1])), (u1, v_of(els[j]))]):
                l[uvl].uv = uv
    for i in range(seg):
        k = (i + 1) % seg
        f_ = bm.faces.new((grid[-1][i], pole, grid[-1][k]))
        for l, uv in zip(f_.loops, [(i / seg, v_of(els[-1])), ((i + 0.5) / seg, 1.0), ((i + 1) / seg, v_of(els[-1]))]):
            l[uvl].uv = uv
    bm.normal_update()
    for f_ in bm.faces:
        if f_.normal.dot(f_.calc_center_median()) > 0: f_.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_SKY)
    for p in me.polygons: p.use_smooth = True
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False; o.visible_transmission = False; o.visible_volume_scatter = False
    return link(o)
sky_dome("SkyDome")

# ----------------------------------------------------------------------------- lights (manifest light ids)
def light_obj(name, kind, energy, color, loc, direction=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if direction is not None: lo.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return link(lo)
light_obj("light.sun", 'SUN', 4.2, (1.0, 0.93, 0.82), tuple(SUN_DIR * 40), direction=-SUN_DIR, angle=math.radians(1.2))
sky_l = light_obj("light.sky", 'SUN', 0.35, (0.62, 0.74, 1.0), (0, 0, 30), direction=(-0.2, -0.1, -1.0), angle=math.radians(80))
sky_l.data.use_shadow = False

# world: a clear-sky gradient for the render's ambient light (Unity gets the SkyDome mesh and its own ambient)
world = bpy.data.worlds.new("Morning"); scene.world = world; world.use_nodes = True
wnt = world.node_tree; bg = wnt.nodes["Background"]
wtc = wnt.nodes.new("ShaderNodeTexCoord"); wsep = wnt.nodes.new("ShaderNodeSeparateXYZ"); wnt.links.new(wtc.outputs["Generated"], wsep.inputs["Vector"])
wmr = wnt.nodes.new("ShaderNodeMapRange"); wmr.inputs["From Min"].default_value = -0.1; wmr.inputs["From Max"].default_value = 1.0
wnt.links.new(wsep.outputs["Z"], wmr.inputs["Value"])
wr = wnt.nodes.new("ShaderNodeValToRGB"); cr = wr.color_ramp
cr.elements[0].position = 0.0; cr.elements[0].color = (0.16, 0.15, 0.12, 1)
cr.elements[1].position = 0.12; cr.elements[1].color = (0.62, 0.70, 0.80, 1)
e = cr.elements.new(0.35); e.color = (0.36, 0.52, 0.80, 1)
e = cr.elements.new(1.0); e.color = (0.20, 0.36, 0.70, 1)
wnt.links.new(wmr.outputs["Result"], wr.inputs["Fac"]); wnt.links.new(wr.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.9

# ----------------------------------------------------------------------------- anchors
anchor("reader.entrance", (0.0, 0.0, 0.0))
look = anchor("reader.look", (0.0, 2.0, EYE))
anchor("scene.centre", (0.0, 0.0, 0.0))
anchor("shore", (coast(0.0) - 3.0, 0.0, h(coast(0.0) - 3.0, 0.0)))

# apply every transform so object space == world space (the procedural materials then bake exactly as rendered)
bpy.ops.object.select_all(action='DESELECT')
for o in COLL.objects:
    if o.type == 'MESH': o.select_set(True); bpy.context.view_layer.objects.active = o
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.select_all(action='DESELECT')

# a stand-in for the reading page, for composition renders only (never exported)
pm_, pnt, pb, _pg = new_mat("M_PageProxy")
pb.inputs["Base Color"].default_value = (0.80, 0.77, 0.68, 1); pb.inputs["Roughness"].default_value = 0.9
pb.inputs["Emission Color"].default_value = (0.80, 0.77, 0.68, 1); pb.inputs["Emission Strength"].default_value = 0.35
bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0.6, EYE), rotation=(math.pi / 2, 0, 0))
PAGE = bpy.context.active_object; PAGE.name = "PageProxy"; PAGE.scale = (0.40, 0.55, 1); PAGE.data.materials.append(pm_)
PAGE.hide_render = True

# ----------------------------------------------------------------------------- cameras (reader eye 1.55 m; ~90 degrees across, like the headset)
def camera(name, loc, look_at, lens=18):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 300; cd.clip_start = 0.05
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co
E = (0.0, 0.0, EYE)
def az(deg, pitch_deg, dist=20.0):
    a, p = math.radians(deg), math.radians(pitch_deg)
    return (math.sin(a) * math.cos(p) * dist, math.cos(a) * math.cos(p) * dist, EYE + math.sin(p) * dist)
cams = [
    camera("Cam_Reader", E, az(0, -6)),
    camera("Cam_Page", E, az(0, -6)),
    camera("Cam_Town", E, az(-50, -3), lens=22),
    camera("Cam_Left", E, az(-95, -8)),
    camera("Cam_Right", E, az(80, -8)),
    camera("Cam_Behind", E, az(180, -4)),
    camera("Cam_Down", E, az(-165, -52), lens=16),
    camera("Cam_Feet", E, az(-20, -60), lens=16),
    camera("Cam_Shore", (6.0, -2.0, EYE + h(6.0, -2.0)), (30.0, 6.0, -2.0), lens=20),
]
EXPOSURE = {}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "lilliput_beach_source.blend"))

# pre-export budget (printed every run so the budget is visible while iterating)
_dg = bpy.context.evaluated_depsgraph_get(); _cat = {}
for _o in [o for o in COLL.objects if o.type == 'MESH']:
    _e = _o.evaluated_get(_dg); _me = _e.to_mesh(); _t = sum(len(p.vertices) - 2 for p in _me.polygons); _e.to_mesh_clear()
    _k = _o.data.materials[0].name if _o.data.materials else "?"
    _cat[_k] = _cat.get(_k, 0) + _t
print(f"PRE-MERGE materials={len(_cat)} tris={sum(_cat.values())}")
for _k, _v in sorted(_cat.items(), key=lambda kv: -kv[1]): print(f"  BUDGET {_k:24s} {_v}")

if args.render:
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    want = set(c.strip().lower() for c in args.cams.split(",") if c.strip())
    for c in cams:
        if want and c.name[4:].lower() not in want: continue
        scene.camera = c
        PAGE.hide_render = (c.name != "Cam_Page")
        scene.view_settings.exposure = EXPOSURE.get(c.name, 0.0)
        scene.render.filepath = os.path.join(OUT, f"{args.prefix}{c.name[4:].lower()}.png")
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:                  # the GPU is shared with other renders: fall back to the CPU
            print("GPU render failed, retrying on CPU:", e)
            scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)
    PAGE.hide_render = True

# ----------------------------------------------------------------------------- bake + merge + export for Unity
def tri_count(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

KEEP_NAMES = {"M_SkyDome": "SkyDome", "M_FarLand": "far.land", "M_Sea": "far.sea", "M_Town": "far.town", "M_Ships": "far.ships"}
KEEP_UV = {"SkyDome", "far.land", "far.sea", "MESH_GroundNear", "MESH_GroundFields"}

def bake_and_export():
    bpy.data.objects.remove(PAGE)
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
    scene.cycles.samples = 4
    scene.render.bake.margin = 6
    T_ = args.tex
    size_for = {"M_GroundNear": min(4096, T_ * 2), "M_GroundFields": T_, "M_FarLand": T_ // 2, "M_Sea": T_ // 2, "M_SkyDome": T_,
                "M_Leaves": T_, "M_Hedge": T_ // 2, "M_TempleStone": T_, "M_TempleRoof": T_ // 2, "M_ShoreRock": T_ // 4,
                "M_Bark": T_ // 4, "M_ChainIron": T_ // 4, "M_TentCanvas": T_ // 4, "M_GateOak": T_ // 4, "M_Town": T_ // 2,
                "M_Ships": T_ // 8, "M_TempleDark": 64}
    bake_dir = os.path.join(OUT, "bake_png"); os.makedirs(bake_dir, exist_ok=True)
    tex_sizes = {}
    for o in merged:
        m = o.data.materials[0]; nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        size = max(64, size_for.get(m.name, T_ // 8))
        tex_sizes[o.name] = size
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        if o.name not in KEEP_UV or not o.data.uv_layers:
            for uvl in list(o.data.uv_layers): o.data.uv_layers.remove(uvl)
            o.data.uv_layers.new(name="UVMap")
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
            bpy.ops.object.mode_set(mode='OBJECT')
        passes = [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]
        if o.name == "SkyDome": passes = [("BaseColor", 'EMIT', {}, False)]
        if m.name == "M_TempleDark": passes = passes[:1]
        baked = {}
        for pass_name, btype, extra, noncolor in passes:
            img = bpy.data.images.new(f"T_{m.name[2:]}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            for n in nt.nodes: n.select = False
            tex.select = True; nt.nodes.active = tex
            try:
                bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            except RuntimeError as e:
                print("GPU bake failed, retrying on CPU:", e); scene.cycles.device = 'CPU'
                bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            img.filepath_raw = os.path.join(bake_dir, img.name + ".png")
            img.file_format = 'PNG'; img.save(); img.pack()
            baked[pass_name] = tex
            print("baked", img.name, size, flush=True)
        metallic = bsdf.inputs["Metallic"].default_value
        emis = bsdf.inputs["Emission Strength"].default_value
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
            nb.inputs["Emission Strength"].default_value = 1.0
            nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"])
        # drop helper attributes the export does not need (the tint is baked into the base colour)
        for an in [a.name for a in o.data.color_attributes]: o.data.color_attributes.remove(o.data.color_attributes[an])
    for c in cams: bpy.data.objects.remove(c)
    gl = os.path.join(OUT, "lilliput_beach.gltf")
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False)
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={tex_sizes.get(o.name, 0)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "lilliput_beach_baked.blend"))

if args.bake or args.export:
    bake_and_export()
print("DONE")
