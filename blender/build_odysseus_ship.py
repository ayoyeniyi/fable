"""
Fable: the deck of Ulysses' ship off the island of the Sirens (The Odyssey, Book XII, Samuel Butler's 1900 prose
translation).

"First you will come to the Sirens who enchant all who come near them ... for they sit in a green field and warble
him to death with the sweetness of their song. There is a great heap of dead men's bones lying all around ..."
"... you may get the men to bind you as you stand upright on a cross piece half way up the mast, and they must lash
the rope's ends to the mast itself ..."
"I had hardly finished telling everything to the men before we reached the island of the two Sirens, for the wind
had been very favourable. Then all of a sudden it fell dead calm; there was not a breath of wind nor a ripple upon
the water, so the men furled the sails and stowed them; then taking to their oars they whitened the water with the
foam they raised in rowing. Meanwhile I took a large wheel of wax and cut it up small with my sword. Then I kneaded
the wax in my strong hands till it became soft, which it soon did between the kneading and the rays of the sun-god
son of Hyperion."

No people (no crew, no Ulysses, no Sirens). A Bronze-Age black ship lies still in the dead calm of a hazy summer
morning: an open hull with its rowing benches, the oars shipped along them, the single mast standing with the
cross piece and the lashing ropes at its foot, the yard lowered and the furled sail stowed along the benches, twin
steering oars at the quarters. On the stern deck lie the cut-up wheel of wax and the sword. Off the port bow lies
the Sirens' island: a stratified limestone cliff at its western end, a green field of flowers falling to a small
cove, and the pale heap of bones at the meadow's edge. Far off: Aeaea astern, and ahead to starboard the high rock
whose peak "is lost in a dark cloud". Everything is procedural (no downloaded models, textures or HDRIs).

Time of day: mid-morning, the calm the text describes ("dawn enthroned in gold" when they sail; the sun already
strong enough to soften the wax). The sun stands high to the reader's right and a little behind, so its glitter on
the glassy sea is off to the right, never behind the page; a light summer haze softens the horizon behind the page.

Builds the environment in Blender with PBR node materials and summer daylight (sun + sky), then (by flag) renders
Cycles stills, bakes materials to textures, merges static meshes by material and exports .gltf + .bin + textures/
for Unity. The ship does not rock: every mesh is static, the viewpoint is stable.

Node naming: anchors are empties "anchor.<id>" (anchor.reader.entrance, anchor.reader.look, anchor.scene.centre,
anchor.ship.mast, anchor.ship.bow, anchor.ship.steering_oar, anchor.isle.meadow, anchor.isle.bones); lights
"light.sun", "light.sky" (both SUN). The sky is the mesh "SkyDome" (unlit, baked base texture); far scenery is
"far.Sea", "far.Coast" (backdrop).

Axes: metres, Blender +Z up. The reader stands on the stern deck (z=0) at anchor.reader.entrance (world origin), by
the port steering oar, facing Blender -Y (glTFast imports it as Unity +Z). The ship's bow points 24 degrees to the
reader's right of that, so the page (0.6 m ahead, 0.4 x 0.55 m at eye height) has open calm sea and haze behind it,
the bow and mast frame its right and the island its left. The sea lies at z = -1.30.

Run headless:
  blender -b -P blender/build_odysseus_ship.py -- --out out/odysseus-ship --render --quick --res 900
  blender -b -P blender/build_odysseus_ship.py -- --out out/odysseus-ship --render --samples 96 --res 1400
  blender -b -P blender/build_odysseus_ship.py -- --out out/odysseus-ship --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, Euler, noise

# ----------------------------------------------------------------------------- args
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/odysseus-ship")
ap.add_argument("--render", action="store_true")
ap.add_argument("--bake", action="store_true")
ap.add_argument("--export", action="store_true")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", type=int, default=1400)
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--quick", action="store_true", help="low samples for iteration")
ap.add_argument("--cams", default="", help="comma list of camera names to render (default all)")
args = ap.parse_args(argv)
OUT = os.path.abspath(args.out)
os.makedirs(OUT, exist_ok=True)
random.seed(1900)

# ----------------------------------------------------------------------------- dimensions (metres)
WL = -1.30                               # the sea surface; the stern deck is z = 0
EYE = 1.55
SHIP_YAW = math.radians(-24.0)           # the bow points 24 degrees to the reader's right of the look direction (-Y)
RX = 0.55                                # the reader stands this far to port of the centreline (ship frame +X = port)
MAST_Y = -8.30
THWART_Z = -0.85                         # top of the rowing benches is THWART_Z + 0.03
FLOOR_Z = -1.42
THWARTS = [-3.0 - k * 1.0 for k in range(13)]          # thirteen benches, twenty-six oars
SUN_DIR = Vector((-0.72, 0.30, 0.62)).normalized()     # towards the sun: high, to the reader's right and a little behind
SKY_R = 120.0
SEA_R = 96.0

def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def lerp(a, b, t):
    return a + (b - a) * t

def interp1(table, x):
    """Catmull-Rom (Hermite) through [(x, y)] sorted by x."""
    xs = [p[0] for p in table]; ys = [p[1] for p in table]
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
    x0, x1 = xs[i], xs[i + 1]; y0, y1 = ys[i], ys[i + 1]
    def slope(k):
        a, b_ = max(0, k - 1), min(len(xs) - 1, k + 1)
        return (ys[b_] - ys[a]) / (xs[b_] - xs[a])
    h = x1 - x0; t = (x - x0) / h
    m0, m1 = slope(i) * h, slope(i + 1) * h
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * m1

# hull lines in the ship frame (ship forward = -Y, port = +X); y from the bow (-19.7) to the stern (+2.8)
BEAM = [(-19.7, 0.05), (-18.8, 0.42), (-17.5, 0.86), (-15.5, 1.28), (-12.5, 1.60), (-9.0, 1.72), (-6.0, 1.70),
        (-3.5, 1.58), (-1.5, 1.42), (0.0, 1.25), (1.2, 0.98), (2.1, 0.60), (2.8, 0.06)]
SHEER = [(-19.7, 0.55), (-18.5, 0.22), (-16.5, -0.12), (-13.5, -0.30), (-9.0, -0.38), (-5.0, -0.32), (-2.5, -0.12),
         (-1.2, 0.10), (0.0, 0.28), (1.4, 0.52), (2.4, 0.85), (2.8, 1.10)]
KEEL = [(-19.7, -1.30), (-19.2, -1.45), (-17.0, -1.72), (-12.0, -1.85), (-5.0, -1.85), (-1.0, -1.78), (1.2, -1.55),
        (2.3, -1.15), (2.8, -0.80)]
Y_BOW, Y_STERN = -19.7, 2.8
HULL_T = 0.055

def beam(y): return max(0.04, interp1(BEAM, y))
def sheer(y): return interp1(SHEER, y)
def keel(y): return interp1(KEEL, y)
def sect(s): return (1.0 - (1.0 - max(0.0, min(1.0, s))) ** 2.4) ** 0.55        # round bilge, a little deadrise
def hb(y, z, inner=False):
    """Half-breadth of the hull at (y, z), outer planking or (inner) its inside face."""
    k, sh = keel(y), sheer(y)
    s = (z - k) / max(1e-3, sh - k)
    return max(0.0, beam(y) * sect(s) - (HULL_T if inner else 0.0))

def ship_w(p):
    """Ship frame -> world (the reader's feet are the world origin)."""
    p = Vector(p)
    q = Matrix.Rotation(SHIP_YAW, 3, 'Z') @ Vector((p.x - RX, p.y, p.z))
    return q

# ----------------------------------------------------------------------------- the island of the Sirens (world frame, heights above the sea)
ISLE_BEARING = math.radians(34.0)        # to the reader's left of the look direction
ISLE_DIST = 64.0
ISLE_V = Vector((math.sin(ISLE_BEARING), -math.cos(ISLE_BEARING), 0.0))    # away from the ship
ISLE_U = Vector((ISLE_V.y, -ISLE_V.x, 0.0))                                # the reader's right along the island
ISLE_C = ISLE_V * ISLE_DIST
ISLE_A, ISLE_B = 26.0, 12.5

def isle_uv(x, y):
    d = Vector((x, y, 0.0)) - ISLE_C
    return d.dot(ISLE_U), d.dot(ISLE_V)

def isle_xy(u, v):
    p = ISLE_C + ISLE_U * u + ISLE_V * v
    return p.x, p.y

def isle_cliff(u, v):
    """1 on the stratified sea cliff at the near-western end, 0 on the meadow side."""
    return smoothstep(0.3, -0.35, u / ISLE_A) * smoothstep(0.3, -0.6, v / ISLE_B)

def isle_h(u, v):
    wu = u + 5.0 * noise.noise(Vector((u * 0.04, v * 0.04, 1.1)))
    wv = v + 4.0 * noise.noise(Vector((u * 0.04, v * 0.04, 7.3)))
    r = math.sqrt((wu / ISLE_A) ** 2 + (wv / ISLE_B) ** 2)
    body = 1.0 - r
    hi = smoothstep(0.75, -0.55, u / ISLE_A)
    H = 2.2 + 10.5 * hi
    c = isle_cliff(u, v)
    k = 3.2 + 14.0 * c
    if body > 0: h = H * (1.0 - math.exp(-body * k))
    else: h = max(-7.0, body * k * 2.0)
    # the field rolls in low swells; the ground is rougher towards the rocky western end
    h += (0.9 * noise.noise(Vector((u * 0.07, v * 0.07, 2.0))) + (0.3 + 0.3 * hi) * noise.noise(Vector((u * 0.25, v * 0.25, 3.0)))) * smoothstep(-0.02, 0.3, body)
    # gullies scored down the flanks by winter rain (narrow, running downslope)
    gn = noise.noise(Vector((u * 0.16 + 0.8 * noise.noise(Vector((v * 0.08, u * 0.02, 4.0))), 0.0, 5.5)))
    gully = (1.0 - min(1.0, abs(gn) * 3.0)) ** 3
    h -= 1.5 * gully * smoothstep(0.6, 3.5, h) * (1.0 - smoothstep(0.3, 0.65, body))
    # bedding: limestone beds dipping gently east, weathered back into ledges and risers where the sea cut the cliff
    dip = 0.10 * u - 0.05 * v
    s = h + dip; T = 2.4
    t = s / T; f = t - math.floor(t)
    st = (math.floor(t) + smoothstep(0.55, 0.95, f)) * T - dip
    w = (0.3 + 0.65 * c) * smoothstep(0.0, 0.6, h)
    return lerp(h, st, w)

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
scene.render.film_transparent = False
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

COLL = bpy.data.collections.new("OdysseusShip")
scene.collection.children.link(COLL)
def link(obj):
    COLL.objects.link(obj); return obj

# ----------------------------------------------------------------------------- material helpers (from build_calypsos_cave.py)
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

def ramp(nt, stops, loc=(0, 0)):
    r = nt.nodes.new("ShaderNodeValToRGB"); r.location = loc
    cr = r.color_ramp
    while len(cr.elements) > 1: cr.elements.remove(cr.elements[-1])
    cr.elements[0].position, cr.elements[0].color = stops[0]
    for pos, col in stops[1:]:
        e = cr.elements.new(pos); e.color = col
    return r

def c4(c): return (c[0], c[1], c[2], 1)
def scaled(c, k): return tuple(min(1.0, x * k) for x in c)

def coords(nt, world=False, loc=(-1400, 0)):
    if world:
        g = node(nt, "ShaderNodeNewGeometry", loc); mp = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
        nt.links.new(g.outputs["Position"], mp.inputs["Vector"]); return mp
    tc = node(nt, "ShaderNodeTexCoord", loc); mp = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); return mp

def ship_coords(nt, stretch=(1, 1, 1), loc=(-1600, 0)):
    """World position -> ship frame (so grain runs along the timbers before and after the merge), then stretched."""
    g = node(nt, "ShaderNodeNewGeometry", loc)
    m1 = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
    m1.inputs["Rotation"].default_value = (0.0, 0.0, -SHIP_YAW); m1.inputs["Location"].default_value = (RX, 0.0, 0.0)
    nt.links.new(g.outputs["Position"], m1.inputs["Vector"])
    m2 = node(nt, "ShaderNodeMapping", (loc[0] + 400, loc[1])); m2.inputs["Scale"].default_value = stretch
    nt.links.new(m1.outputs["Vector"], m2.inputs["Vector"])
    return m2, m1

def attr(nt, name, loc=(-1000, 600)):
    a = node(nt, "ShaderNodeAttribute", loc); a.attribute_name = name
    return a.outputs["Fac"]

def bump_from(nt, b, height_socket, strength, distance):
    bump = node(nt, "ShaderNodeBump", (50, -300)); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return bump

def mix_rgb(nt, a, b_, fac, blend='MIX', loc=(0, 0)):
    mx = node(nt, "ShaderNodeMix", loc, data_type='RGBA', blend_type=blend)
    if isinstance(fac, (int, float)): mx.inputs["Factor"].default_value = fac
    else: nt.links.new(fac, mx.inputs["Factor"])
    for sock, v in ((mx.inputs[6], a), (mx.inputs[7], b_)):
        if isinstance(v, tuple): sock.default_value = v
        else: nt.links.new(v, sock)
    return mx.outputs[2]

def mix_f(nt, a, b_, fac, loc=(0, 0)):
    mx = node(nt, "ShaderNodeMix", loc, data_type='FLOAT')
    for sock, v in ((mx.inputs[0], fac), (mx.inputs[2], a), (mx.inputs[3], b_)):
        if isinstance(v, (int, float)): sock.default_value = v
        else: nt.links.new(v, sock)
    return mx.outputs[0]

def math_n(nt, op, a, b_=None, loc=(0, 0)):
    n = node(nt, "ShaderNodeMath", loc, operation=op)
    for sock, v in ((n.inputs[0], a), (n.inputs[1], b_)):
        if v is None: continue
        if isinstance(v, (int, float)): sock.default_value = v
        else: nt.links.new(v, sock)
    return n.outputs[0]

def map_range(nt, val, fmin, fmax, tmin=0.0, tmax=1.0, loc=(0, 0)):
    n = node(nt, "ShaderNodeMapRange", loc)
    n.inputs["From Min"].default_value = fmin; n.inputs["From Max"].default_value = fmax
    n.inputs["To Min"].default_value = tmin; n.inputs["To Max"].default_value = tmax
    nt.links.new(val, n.inputs["Value"]); return n.outputs["Result"]

def noise_tex(nt, vec, scale, detail=6.0, rough=0.6, distortion=0.0, loc=(-1000, 0)):
    n = node(nt, "ShaderNodeTexNoise", loc); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough; n.inputs["Distortion"].default_value = distortion
    nt.links.new(vec, n.inputs["Vector"]); return n

def sep_xyz(nt, vec, loc=(-1100, 0)):
    s = node(nt, "ShaderNodeSeparateXYZ", loc); nt.links.new(vec, s.inputs["Vector"]); return s

def ao_mult(nt, col, dist, dark, loc=(-450, -800)):
    a = node(nt, "ShaderNodeAmbientOcclusion", loc); a.inputs["Distance"].default_value = dist; a.samples = 16
    aor = ramp(nt, [(0.0, c4(dark)), (1.0, (1, 1, 1, 1))], (loc[0] + 200, loc[1])); nt.links.new(a.outputs["AO"], aor.inputs["Fac"])
    return mix_rgb(nt, col, aor.outputs["Color"], 1.0, 'MULTIPLY', (loc[0] + 400, loc[1]))

def noisy(name, colors, scale=8.0, rough=0.8, bump=0.2, bump_dist=0.003, detail=6.0, stretch=(1, 1, 1), sheen=0.0, sss=0.0, metallic=0.0, warp=0.0, world=False):
    m, nt, b = new_mat(name)
    mp = coords(nt, world=world); mp.inputs["Scale"].default_value = stretch
    n = noise_tex(nt, mp.outputs["Vector"], scale, detail, 0.6, warp)
    stops = [(i / max(1, len(colors) - 1) * 0.6 + 0.2, c4(c)) for i, c in enumerate(colors)]
    r = ramp(nt, stops, (-700, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if sheen: b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.4
    if sss: b.inputs["Subsurface Weight"].default_value = sss; b.inputs["Subsurface Radius"].default_value = (0.4, 0.3, 0.1)
    if bump:
        fine = noise_tex(nt, mp.outputs["Vector"], scale * 6, 4, loc=(-1000, -350))
        bump_from(nt, b, fine.outputs["Fac"], bump, bump_dist)
    return m

# ----------------------------------------------------------------------------- materials
def timber_mat(name, base, dark, light, along='X', rough=(0.62, 0.85), grime=0.35, scale=1.0, salt=0.0):
    """Weathered ship timber: grain along the timber (ship frame), per-piece tone (attribute 'rnd'), grime in the
    hollows (AO), sun-greyed tops, a little salt."""
    m, nt, b = new_mat(name)
    stretch = {'X': (1.2, 16, 16), 'Y': (16, 1.2, 16), 'Z': (16, 16, 1.2)}[along]
    mp, m1 = ship_coords(nt, tuple(s * scale for s in stretch))
    wave = node(nt, "ShaderNodeTexWave", (-1000, 250), wave_type='BANDS', bands_direction={'X': 'Y', 'Y': 'X', 'Z': 'X'}[along])
    wave.inputs["Scale"].default_value = 1.6; wave.inputs["Distortion"].default_value = 9.0
    wave.inputs["Detail"].default_value = 5.0; wave.inputs["Detail Scale"].default_value = 1.4
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    fine = noise_tex(nt, mp.outputs["Vector"], 9.0, 8.0, 0.65, loc=(-1000, 0))
    mx = mix_f(nt, wave.outputs["Fac"], fine.outputs["Fac"], 0.6, (-800, 150))
    mid = tuple((x + y) / 2 for x, y in zip(base, light))
    r = ramp(nt, [(0.1, c4(dark)), (0.35, c4(base)), (0.55, c4(mid)), (0.8, c4(light))], (-600, 150))
    nt.links.new(mx, r.inputs["Fac"])
    # per-piece tone: each plank, bench and oar was cut from a different tree and has weathered differently
    rnd = attr(nt, "rnd", (-1000, 550))
    tone = ramp(nt, [(0.0, (0.80, 0.80, 0.82, 1)), (0.5, (1.0, 0.97, 0.93, 1)), (1.0, (1.12, 1.08, 1.0, 1))], (-800, 550))
    nt.links.new(rnd, tone.inputs["Fac"])
    col = mix_rgb(nt, r.outputs["Color"], tone.outputs["Color"], 1.0, 'MULTIPLY', (-400, 300))
    # large blotches of grime and of sun-bleached grey
    big = noise_tex(nt, m1.outputs["Vector"], 1.3, 4, 0.5, loc=(-1000, -250))
    bl = ramp(nt, [(0.35, (0.82, 0.78, 0.74, 1)), (0.5, (1, 1, 1, 1)), (0.68, (1.08, 1.08, 1.06, 1))], (-800, -250))
    nt.links.new(big.outputs["Fac"], bl.inputs["Fac"])
    col = mix_rgb(nt, col, bl.outputs["Color"], 1.0, 'MULTIPLY', (-250, 300))
    if salt:
        sn = noise_tex(nt, m1.outputs["Vector"], 7.0, 6, 0.6, loc=(-1000, -450))
        sr = ramp(nt, [(0.62, (0, 0, 0, 1)), (0.75, (1, 1, 1, 1))], (-800, -450)); nt.links.new(sn.outputs["Fac"], sr.inputs["Fac"])
        sf = math_n(nt, 'MULTIPLY', sr.outputs["Color"], salt, (-600, -450))
        col = mix_rgb(nt, col, (0.62, 0.60, 0.55, 1), sf, 'MIX', (-150, 300))
    col = ao_mult(nt, col, 0.35, scaled(dark, 1.0 - grime * 0.4) if grime else (1, 1, 1))
    nt.links.new(col, b.inputs["Base Color"])
    rr = map_range(nt, mx, 0.2, 0.8, rough[1], rough[0], (-150, -200)); nt.links.new(rr, b.inputs["Roughness"])
    h = math_n(nt, 'MULTIPLY_ADD', wave.outputs["Fac"], 0.6, (-300, -400)); nt.links.new(fine.outputs["Fac"], h.node.inputs[2])
    bump_from(nt, b, h, 0.35, 0.002)
    return m

def hull_mat(name, inner=False):
    """Pitch-black planking (Homer's black ships). Strake seams from the attribute 's' (0 keel .. 1 sheer); the
    pitch is worn thin to brown wood where hands and oars rub; weed and salt at the waterline outside, a damp dark
    bilge inside."""
    m, nt, b = new_mat(name)
    mp, m1 = ship_coords(nt, (1, 1, 1))
    g = node(nt, "ShaderNodeNewGeometry", (-1600, -600)); wz = sep_xyz(nt, g.outputs["Position"], (-1400, -600))
    s = attr(nt, "s", (-1400, 600))
    strakes = math_n(nt, 'MULTIPLY', s, 11.0, (-1200, 600)); fr = math_n(nt, 'FRACT', strakes, None, (-1050, 600))
    seam = ramp(nt, [(0.0, (0.55, 0.55, 0.55, 1)), (0.035, (1, 1, 1, 1)), (0.965, (1, 1, 1, 1)), (1.0, (0.55, 0.55, 0.55, 1))], (-900, 600))
    nt.links.new(fr, seam.inputs["Fac"])
    gr, _ = ship_coords(nt, (0.8, 0.06, 0.8), (-1600, 300))
    grain = noise_tex(nt, gr.outputs["Vector"], 6.0, 6, 0.6, loc=(-1000, 300))
    big = noise_tex(nt, m1.outputs["Vector"], 0.6, 5, 0.55, loc=(-1000, 0))
    if not inner:
        pitch = ramp(nt, [(0.3, (0.012, 0.011, 0.010, 1)), (0.55, (0.022, 0.019, 0.016, 1)), (0.75, (0.040, 0.032, 0.024, 1))], (-800, 300))
    else:
        pitch = ramp(nt, [(0.25, (0.030, 0.021, 0.014, 1)), (0.5, (0.060, 0.042, 0.027, 1)), (0.75, (0.105, 0.075, 0.048, 1))], (-800, 300))
    nt.links.new(mix_f(nt, grain.outputs["Fac"], big.outputs["Fac"], 0.5, (-900, 200)), pitch.inputs["Fac"])
    col = mix_rgb(nt, pitch.outputs["Color"], seam.outputs["Color"], 1.0, 'MULTIPLY', (-600, 300))
    # worn through to the wood near the sheer (the upper strakes): brown showing under the pitch
    wear = map_range(nt, s, 0.8, 0.98, 0.0, 1.0, (-800, 0))
    wn = noise_tex(nt, gr.outputs["Vector"], 14.0, 6, 0.6, loc=(-800, -150))
    wr = ramp(nt, [(0.5, (0, 0, 0, 1)), (0.66, (1, 1, 1, 1))], (-600, -150)); nt.links.new(wn.outputs["Fac"], wr.inputs["Fac"])
    wf = math_n(nt, 'MULTIPLY', wear, wr.outputs["Color"], (-450, -50)); wf = math_n(nt, 'MULTIPLY', wf, 0.6 if inner else 0.4, (-350, -50))
    col = mix_rgb(nt, col, (0.16, 0.10, 0.055, 1), wf, 'MIX', (-300, 300))
    if not inner:
        # waterline: green-brown weed just above the sea, a salt crust above that
        weed = map_range(nt, wz.outputs["Z"], WL + 0.22, WL + 0.02, 0.0, 1.0, (-800, -600))
        wdn = noise_tex(nt, m1.outputs["Vector"], 4.0, 5, 0.6, loc=(-800, -800))
        wcol = ramp(nt, [(0.3, (0.035, 0.045, 0.02, 1)), (0.7, (0.07, 0.075, 0.03, 1))], (-600, -800)); nt.links.new(wdn.outputs["Fac"], wcol.inputs["Fac"])
        col = mix_rgb(nt, col, wcol.outputs["Color"], weed, 'MIX', (-150, 300))
        saltb = map_range(nt, wz.outputs["Z"], WL + 0.65, WL + 0.25, 0.0, 0.35, (-800, -1000))
        sn = noise_tex(nt, m1.outputs["Vector"], 9.0, 6, 0.6, loc=(-800, -1150))
        sr = ramp(nt, [(0.5, (0, 0, 0, 1)), (0.72, (1, 1, 1, 1))], (-600, -1150)); nt.links.new(sn.outputs["Fac"], sr.inputs["Fac"])
        col = mix_rgb(nt, col, (0.30, 0.29, 0.26, 1), math_n(nt, 'MULTIPLY', saltb, sr.outputs["Color"], (-450, -1050)), 'MIX', (0, 300))
    else:
        # the bilge: damp and darker towards the keel
        damp = map_range(nt, s, 0.35, 0.1, 0.0, 0.6, (-800, -600))
        col = mix_rgb(nt, col, (0.015, 0.012, 0.010, 1), damp, 'MIX', (-150, 300))
        col = ao_mult(nt, col, 0.4, (0.35, 0.33, 0.30), (-450, -900))
    nt.links.new(col, b.inputs["Base Color"])
    rr = map_range(nt, big.outputs["Fac"], 0.3, 0.7, 0.32 if not inner else 0.55, 0.62 if not inner else 0.85, (-150, -250))
    if not inner:
        wet = map_range(nt, wz.outputs["Z"], WL + 0.3, WL + 0.05, 0.0, 1.0, (-300, -450))
        rr = mix_f(nt, rr, 0.25, wet, (-50, -350))
    nt.links.new(rr, b.inputs["Roughness"])
    h = math_n(nt, 'MULTIPLY', seam.outputs["Color"], 0.6, (-300, -500)); h = math_n(nt, 'MULTIPLY_ADD', grain.outputs["Fac"], 0.3, (-200, -500)); nt.links.new(seam.outputs["Color"], h.node.inputs[2])
    bump_from(nt, b, h, 0.3, 0.004)
    return m

def deck_mat(name="M_DeckPlanks"):
    """The stern deck: athwartship boards of weathered pine, silvered by sun and salt, pitch in the seams, treenail
    heads where the boards sit on the deck beams, darker and smoother where feet have worn them."""
    m = timber_mat(name, base=(0.30, 0.235, 0.165), dark=(0.10, 0.075, 0.05), light=(0.47, 0.41, 0.33), along='X', rough=(0.55, 0.85), salt=0.4)
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    base_link = b.inputs["Base Color"].links[0]; col = base_link.from_socket
    mp, m1 = ship_coords(nt, (1, 1, 1), (-1600, -1400))
    sx = sep_xyz(nt, m1.outputs["Vector"], (-1300, -1400))
    # treenails: pegs at the beams x = +-0.55 (ship frame), one per board (board pitch ~0.21 m)
    pegs = node(nt, "ShaderNodeTexVoronoi", (-1100, -1600)); pegs.inputs["Scale"].default_value = 1.0
    pm = node(nt, "ShaderNodeMapping", (-1300, -1600)); pm.inputs["Scale"].default_value = (1 / 0.55, 1 / 0.21, 1.0)
    nt.links.new(m1.outputs["Vector"], pm.inputs["Vector"]); nt.links.new(pm.outputs["Vector"], pegs.inputs["Vector"])
    pegs.inputs["Randomness"].default_value = 0.08
    dot = map_range(nt, pegs.outputs["Distance"], 0.045, 0.07, 1.0, 0.0, (-900, -1600))
    col = mix_rgb(nt, col, (0.05, 0.035, 0.022, 1), math_n(nt, 'MULTIPLY', dot, 0.85, (-750, -1600)), 'MIX', (-600, -1400))
    # foot-worn path along the middle of the deck, by the steering oars
    ax = math_n(nt, 'ABSOLUTE', math_n(nt, 'SUBTRACT', sx.outputs["X"], RX * 0.6, (-1100, -1200)), None, (-950, -1200))
    worn = map_range(nt, ax, 0.9, 0.2, 0.0, 0.22, (-800, -1200))
    col = mix_rgb(nt, col, (0.20, 0.155, 0.11, 1), worn, 'MIX', (-450, -1300))
    nt.links.new(col, b.inputs["Base Color"])
    return m

def sail_mat(name="M_Sail"):
    """Furled linen sail: undyed flax gone ivory-grey with salt and weather, folds shaded by AO."""
    m, nt, b = new_mat(name)
    mp, m1 = ship_coords(nt, (1, 0.35, 1))
    n = noise_tex(nt, mp.outputs["Vector"], 5.0, 6, 0.6, 1.5, (-1000, 200))
    r = ramp(nt, [(0.3, (0.21, 0.19, 0.155, 1)), (0.55, (0.29, 0.27, 0.225, 1)), (0.75, (0.35, 0.33, 0.28, 1))], (-700, 200))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    st = noise_tex(nt, m1.outputs["Vector"], 2.0, 4, 0.5, loc=(-1000, -100))
    sr = ramp(nt, [(0.55, (1, 1, 1, 1)), (0.7, (0.82, 0.78, 0.70, 1))], (-700, -100)); nt.links.new(st.outputs["Fac"], sr.inputs["Fac"])
    col = mix_rgb(nt, r.outputs["Color"], sr.outputs["Color"], 1.0, 'MULTIPLY', (-400, 200))
    col = ao_mult(nt, col, 0.2, (0.35, 0.33, 0.30))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9; b.inputs["Sheen Weight"].default_value = 0.5
    wx = node(nt, "ShaderNodeTexWave", (-1000, -400), wave_type='BANDS', bands_direction='X'); wx.inputs["Scale"].default_value = 300
    nt.links.new(m1.outputs["Vector"], wx.inputs["Vector"])
    bump_from(nt, b, mix_f(nt, wx.outputs["Fac"], n.outputs["Fac"], 0.7, (-300, -400)), 0.25, 0.004)
    return m

def rope_mat(name="M_Rope"):
    """Twisted papyrus/flax rope: diagonal lay, tan going grey."""
    m, nt, b = new_mat(name)
    mp = coords(nt)
    w = node(nt, "ShaderNodeTexWave", (-1000, 0), wave_type='BANDS', bands_direction='DIAGONAL'); w.inputs["Scale"].default_value = 60
    w.inputs["Distortion"].default_value = 0.6
    nt.links.new(mp.outputs["Vector"], w.inputs["Vector"])
    n = noise_tex(nt, mp.outputs["Vector"], 6.0, 4, loc=(-1000, -250))
    r = ramp(nt, [(0.0, (0.07, 0.055, 0.035, 1)), (0.4, (0.26, 0.21, 0.14, 1)), (0.8, (0.36, 0.31, 0.22, 1))], (-700, 0))
    nt.links.new(mix_f(nt, w.outputs["Fac"], n.outputs["Fac"], 0.3, (-850, 0)), r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.92; b.inputs["Sheen Weight"].default_value = 0.4
    bump_from(nt, b, w.outputs["Fac"], 0.6, 0.002)
    return m

def bronze_mat(name="M_Bronze"):
    m, nt, b = new_mat(name)
    mp = coords(nt)
    n = noise_tex(nt, mp.outputs["Vector"], 18.0, 6, 0.6, loc=(-1000, 0))
    r = ramp(nt, [(0.35, (0.48, 0.30, 0.13, 1)), (0.6, (0.62, 0.43, 0.20, 1)), (0.78, (0.30, 0.34, 0.24, 1))], (-700, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = 1.0
    nt.links.new(map_range(nt, n.outputs["Fac"], 0.4, 0.8, 0.32, 0.6, (-300, -200)), b.inputs["Roughness"])
    return m

def wax_mat(name="M_Wax"):
    m, nt, b = new_mat(name)
    mp = coords(nt)
    n = noise_tex(nt, mp.outputs["Vector"], 30.0, 4, 0.5, loc=(-1000, 0))
    r = ramp(nt, [(0.3, (0.27, 0.16, 0.035, 1)), (0.7, (0.40, 0.26, 0.07, 1))], (-700, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.45; b.inputs["Subsurface Weight"].default_value = 0.35
    b.inputs["Subsurface Radius"].default_value = (0.3, 0.15, 0.05); b.inputs["Subsurface Scale"].default_value = 0.02
    bump_from(nt, b, n.outputs["Fac"], 0.3, 0.001)
    return m

def stone_mat(name, colors, scale=4.0, world=True, wet_below=None, lichen=0.0, crack=1.0, beds=0.0):
    """Limestone / beach stone: fractal noise, fine fissures, a dark wet band (world z) and pale lichen."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=world)
    n = noise_tex(nt, mp.outputs["Vector"], scale, 10, 0.62, 0.4, (-1000, 300))
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 0), feature='DISTANCE_TO_EDGE'); v.inputs["Scale"].default_value = scale * 1.6
    nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    r = ramp(nt, [(0.3, c4(colors[0])), (0.5, c4(colors[1])), (0.72, c4(colors[2]))], (-700, 300)); nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    crack_r = ramp(nt, [(0.0, (0.5, 0.48, 0.45, 1)), (0.02, (0.85, 0.84, 0.8, 1)), (0.05, (1, 1, 1, 1))], (-700, 0)); nt.links.new(v.outputs["Distance"], crack_r.inputs["Fac"])
    col = mix_rgb(nt, r.outputs["Color"], crack_r.outputs["Color"], crack, 'MULTIPLY', (-450, 300))
    if beds:
        bw = node(nt, "ShaderNodeTexWave", (-1000, 550), wave_type='BANDS', bands_direction='Z'); bw.inputs["Scale"].default_value = 1.4
        bw.inputs["Distortion"].default_value = 2.0; bw.inputs["Detail"].default_value = 3
        nt.links.new(mp.outputs["Vector"], bw.inputs["Vector"])
        br = ramp(nt, [(0.2, (0.8, 0.78, 0.74, 1)), (0.5, (1, 1, 1, 1)), (0.85, (1.06, 1.05, 1.02, 1))], (-700, 550)); nt.links.new(bw.outputs["Fac"], br.inputs["Fac"])
        col = mix_rgb(nt, col, br.outputs["Color"], beds, 'MULTIPLY', (-380, 300))
    if lichen:
        ln = noise_tex(nt, mp.outputs["Vector"], scale * 2.5, 5, 0.6, loc=(-1000, -300))
        lr = ramp(nt, [(0.62, (0, 0, 0, 1)), (0.7, (1, 1, 1, 1))], (-700, -300)); nt.links.new(ln.outputs["Fac"], lr.inputs["Fac"])
        col = mix_rgb(nt, col, (0.58, 0.56, 0.47, 1), math_n(nt, 'MULTIPLY', lr.outputs["Color"], lichen, (-500, -300)), 'MIX', (-300, 300))
    rough = map_range(nt, n.outputs["Fac"], 0.3, 0.7, 0.92, 0.78, (-300, -200))
    if wet_below is not None:
        g = node(nt, "ShaderNodeNewGeometry", (-1200, -600)); wz = sep_xyz(nt, g.outputs["Position"], (-1000, -600))
        wet = map_range(nt, wz.outputs["Z"], wet_below + 0.35, wet_below + 0.02, 0.0, 1.0, (-800, -600))
        col = mix_rgb(nt, col, (0.10, 0.10, 0.07, 1), math_n(nt, 'MULTIPLY', wet, 0.75, (-650, -600)), 'MIX', (-150, 300))
        rough = mix_f(nt, rough, 0.35, wet, (-100, -300))
    col = ao_mult(nt, col, 0.6, (0.4, 0.38, 0.35))
    nt.links.new(col, b.inputs["Base Color"]); nt.links.new(rough, b.inputs["Roughness"])
    h = math_n(nt, 'MULTIPLY_ADD', v.outputs["Distance"], 0.6 * crack, (-300, -450)); nt.links.new(n.outputs["Fac"], h.node.inputs[2])
    bump_from(nt, b, h, 0.6, 0.03)
    return m

def water_surface(nt, b, mp, loc=(-1000, -1400)):
    """The glassy calm shared by the sea and the island's shallows: faint slicks (roughness patches) and a long,
    very low swell. Returns (roughness, height) sockets."""
    sm = node(nt, "ShaderNodeMapping", (loc[0] - 200, loc[1])); sm.inputs["Scale"].default_value = (1.0, 0.45, 1.0)
    sm.inputs["Rotation"].default_value = (0, 0, 0.5)
    nt.links.new(mp.outputs["Vector"], sm.inputs["Vector"])
    sl = noise_tex(nt, sm.outputs["Vector"], 0.035, 3, 0.5, 0.6, loc)
    rough = map_range(nt, sl.outputs["Fac"], 0.42, 0.62, 0.025, 0.075, (loc[0] + 200, loc[1]))
    sw = node(nt, "ShaderNodeTexWave", (loc[0], loc[1] - 250), wave_type='BANDS', bands_direction='Y'); sw.inputs["Scale"].default_value = 0.09
    sw.inputs["Distortion"].default_value = 1.2; sw.inputs["Detail"].default_value = 2
    nt.links.new(sm.outputs["Vector"], sw.inputs["Vector"])
    rip = noise_tex(nt, mp.outputs["Vector"], 0.9, 4, 0.5, loc=(loc[0], loc[1] - 450))
    h = mix_f(nt, sw.outputs["Fac"], rip.outputs["Fac"], 0.25, (loc[0] + 200, loc[1] - 300))
    return rough, h, sl.outputs["Fac"]

SEA_DEEP = (0.010, 0.040, 0.062)
def sea_mat(name="M_Sea", far=False):
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    rough, h, sl = water_surface(nt, b, mp)
    tint = ramp(nt, [(0.3, c4(scaled(SEA_DEEP, 0.92))), (0.7, c4(scaled(SEA_DEEP, 1.08)))], (-700, 300)); nt.links.new(sl, tint.inputs["Fac"])
    col = tint.outputs["Color"]
    if far:
        # the far sea fades into the summer haze towards the horizon (backdrop: matches the dome's horizon colour)
        g = node(nt, "ShaderNodeNewGeometry", (-1200, 600)); s_ = sep_xyz(nt, g.outputs["Position"], (-1000, 600))
        cx = node(nt, "ShaderNodeCombineXYZ", (-850, 600)); nt.links.new(s_.outputs["X"], cx.inputs["X"]); nt.links.new(s_.outputs["Y"], cx.inputs["Y"])
        ln = node(nt, "ShaderNodeVectorMath", (-700, 600), operation='LENGTH'); nt.links.new(cx.outputs["Vector"], ln.inputs[0])
        d = map_range(nt, ln.outputs["Value"], SEA_R, SKY_R - 2.0, 0.0, 1.0, (-550, 600))
        hz = ramp(nt, [(0.0, c4(SEA_DEEP)), (0.55, (0.10, 0.17, 0.22, 1)), (1.0, (0.42, 0.50, 0.56, 1))], (-400, 600)); nt.links.new(d, hz.inputs["Fac"])
        col = hz.outputs["Color"]
        rough = mix_f(nt, rough, 0.25, d, (-200, -100))
    nt.links.new(col, b.inputs["Base Color"]); nt.links.new(rough, b.inputs["Roughness"])
    b.inputs["Specular IOR Level"].default_value = 0.5
    bump_from(nt, b, h, 0.05, 0.25)
    return m

def isle_ground_mat(name="M_IsleGround"):
    """The Sirens' island in one material (world coordinates and the mesh attributes 'depth' and 'cliff'):
    stratified limestone on the cliff and the steep banks, the green field with drifts of flowers on the gentle
    slopes, shingle at the cove, a dark wet band at the sea's edge, the bone-litter about the heap, and below the
    waterline the clear shallows over sand and weed going down into the deep blue of the open sea."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    g = node(nt, "ShaderNodeNewGeometry", (-1800, -900))
    wz = sep_xyz(nt, g.outputs["Position"], (-1600, -900)); nz = sep_xyz(nt, g.outputs["Normal"], (-1600, -1100))
    depth = attr(nt, "depth", (-1600, 900)); cliff = attr(nt, "cliff", (-1600, 1100))
    big = noise_tex(nt, mp.outputs["Vector"], 0.08, 4, 0.5, loc=(-1300, 600))
    mid = noise_tex(nt, mp.outputs["Vector"], 0.5, 8, 0.62, loc=(-1300, 350))
    # meadow: green field, drier on the crests, flower drifts (yellow, white, purple)
    mm = mix_f(nt, big.outputs["Fac"], mid.outputs["Fac"], 0.5, (-1100, 500))
    meadow = ramp(nt, [(0.3, (0.045, 0.085, 0.02, 1)), (0.48, (0.085, 0.135, 0.035, 1)), (0.62, (0.14, 0.17, 0.055, 1)), (0.78, (0.21, 0.19, 0.09, 1))], (-900, 500))
    nt.links.new(mm, meadow.inputs["Fac"])
    col = meadow.outputs["Color"]
    for k, (fcol, sc, th, seed) in enumerate([((0.62, 0.52, 0.10), 0.35, 0.66, (3, 1, 0)), ((0.50, 0.50, 0.44), 0.5, 0.73, (9, 4, 0)), ((0.34, 0.20, 0.42), 0.42, 0.70, (17, 2, 0))]):
        fm = node(nt, "ShaderNodeMapping", (-1300, 150 - k * 220)); fm.inputs["Location"].default_value = seed
        nt.links.new(mp.outputs["Vector"], fm.inputs["Vector"])
        fn = noise_tex(nt, fm.outputs["Vector"], sc, 6, 0.65, loc=(-1100, 150 - k * 220))
        fr = map_range(nt, fn.outputs["Fac"], th, th + 0.06, 0.0, 0.4, (-900, 150 - k * 220))
        col = mix_rgb(nt, col, c4(fcol), fr, 'MIX', (-700, 150 - k * 220))
    # rock on the steep faces and on the cliff ledges: pale limestone, bedded, streaked
    beds = node(nt, "ShaderNodeTexWave", (-1300, -350), wave_type='BANDS', bands_direction='Z'); beds.inputs["Scale"].default_value = 0.4
    beds.inputs["Distortion"].default_value = 6.0; beds.inputs["Detail"].default_value = 4; beds.inputs["Detail Scale"].default_value = 0.8
    bm_ = node(nt, "ShaderNodeMapping", (-1500, -350)); bm_.inputs["Rotation"].default_value = (0.1, -0.05, 0.0)
    nt.links.new(mp.outputs["Vector"], bm_.inputs["Vector"]); nt.links.new(bm_.outputs["Vector"], beds.inputs["Vector"])
    rk = ramp(nt, [(0.25, (0.12, 0.11, 0.095, 1)), (0.5, (0.18, 0.17, 0.145, 1)), (0.75, (0.25, 0.235, 0.20, 1))], (-900, -350))
    nt.links.new(mix_f(nt, mid.outputs["Fac"], beds.outputs["Fac"], 0.18, (-1050, -350)), rk.inputs["Fac"])
    st_m = node(nt, "ShaderNodeMapping", (-1500, -600)); st_m.inputs["Scale"].default_value = (1.4, 1.4, 0.3)
    nt.links.new(mp.outputs["Vector"], st_m.inputs["Vector"])
    stn = noise_tex(nt, st_m.outputs["Vector"], 1.2, 4, 0.5, loc=(-1300, -600))
    streak = ramp(nt, [(0.45, (1, 1, 1, 1)), (0.7, (0.72, 0.70, 0.66, 1))], (-1100, -600)); nt.links.new(stn.outputs["Fac"], streak.inputs["Fac"])
    rock = mix_rgb(nt, rk.outputs["Color"], streak.outputs["Color"], 1.0, 'MULTIPLY', (-700, -350))
    patch = ramp(nt, [(0.35, (0.78, 0.76, 0.74, 1)), (0.65, (1.08, 1.04, 0.98, 1))], (-1100, -450)); nt.links.new(big.outputs["Fac"], patch.inputs["Fac"])
    rock = mix_rgb(nt, rock, patch.outputs["Color"], 1.0, 'MULTIPLY', (-650, -350))
    # scrub (lentisk, juniper) clinging to the ledges and the less steep parts of the cliff
    scn = noise_tex(nt, mp.outputs["Vector"], 0.7, 6, 0.65, 0.5, (-1300, -800))
    ledge = map_range(nt, nz.outputs["Z"], 0.12, 0.6, 0.25, 1.0, (-1100, -800))
    scrub = math_n(nt, 'MULTIPLY', map_range(nt, scn.outputs["Fac"], 0.48, 0.58, 0.0, 1.0, (-1100, -950)), ledge, (-950, -850))
    rock = mix_rgb(nt, rock, (0.035, 0.05, 0.022, 1), scrub, 'MIX', (-600, -350))
    steep = map_range(nt, nz.outputs["Z"], 0.80, 0.58, 0.0, 1.0, (-1300, -1100))
    rockf = math_n(nt, 'MAXIMUM', steep, math_n(nt, 'MULTIPLY', cliff, map_range(nt, mid.outputs["Fac"], 0.45, 0.6, 0.3, 0.9, (-1300, -1300)), (-1100, -1250)), (-950, -1150))
    col = mix_rgb(nt, col, rock, rockf, 'MIX', (-500, 300))
    # shingle and coarse sand at the cove and along the low shore
    shore = map_range(nt, wz.outputs["Z"], WL + 1.3, WL + 0.45, 0.0, 1.0, (-1300, -1500))
    shore = math_n(nt, 'MULTIPLY', shore, math_n(nt, 'SUBTRACT', 1.0, rockf, (-1100, -1550)), (-950, -1500))
    sh = ramp(nt, [(0.3, (0.21, 0.19, 0.155, 1)), (0.7, (0.31, 0.285, 0.235, 1))], (-900, -1700)); nt.links.new(mid.outputs["Fac"], sh.inputs["Fac"])
    shc = mix_rgb(nt, sh.outputs["Color"], (0.11, 0.105, 0.09, 1), math_n(nt, 'MULTIPLY', cliff, 0.8, (-900, -1850)), 'MIX', (-700, -1700))   # under the cliff: a dark wave-cut bench
    col = mix_rgb(nt, col, shc, shore, 'MIX', (-350, 300))
    # the bones lying all around the heap: pale litter in the grass
    dv = node(nt, "ShaderNodeVectorMath", (-1300, -1900), operation='DISTANCE'); dv.inputs[1].default_value = (BONES_XY[0], BONES_XY[1], 0.0)
    flat = node(nt, "ShaderNodeVectorMath", (-1500, -1900), operation='MULTIPLY'); flat.inputs[1].default_value = (1, 1, 0)
    nt.links.new(g.outputs["Position"], flat.inputs[0]); nt.links.new(flat.outputs[0], dv.inputs[0])
    bf = map_range(nt, dv.outputs["Value"], 7.0, 2.0, 0.0, 1.0, (-1100, -1900))
    bv = node(nt, "ShaderNodeTexVoronoi", (-1300, -2100)); bv.inputs["Scale"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], bv.inputs["Vector"])
    bsp = map_range(nt, bv.outputs["Distance"], 0.32, 0.18, 0.0, 1.0, (-1100, -2100))
    col = mix_rgb(nt, col, (0.56, 0.53, 0.46, 1), math_n(nt, 'MULTIPLY', bf, bsp, (-950, -2000)), 'MIX', (-200, 300))
    # the wet band at the sea's edge (calm: no surf, a dark film of biofilm and weed)
    wet = map_range(nt, wz.outputs["Z"], WL + 0.40, WL + 0.02, 0.0, 1.0, (-1300, -2300))
    col = mix_rgb(nt, col, (0.08, 0.085, 0.055, 1), math_n(nt, 'MULTIPLY', wet, 0.8, (-1100, -2300)), 'MIX', (-50, 300))
    col = ao_mult(nt, col, 1.5, (0.45, 0.45, 0.42), (-500, -2500))
    # below the waterline: the shallows (sand and weed seen through clear water) into the deep sea colour
    sea_r, sea_h, sl = water_surface(nt, b, mp, (-1300, -2800))
    sb = ramp(nt, [(0.35, (0.10, 0.19, 0.18, 1)), (0.65, (0.05, 0.12, 0.12, 1))], (-900, 1000)); nt.links.new(mid.outputs["Fac"], sb.inputs["Fac"])
    shallow = mix_rgb(nt, sb.outputs["Color"], (0.05, 0.10, 0.07, 1), math_n(nt, 'MULTIPLY', cliff, 0.7, (-900, 1200)), 'MIX', (-700, 1000))
    dd = map_range(nt, depth, 0.0, 4.5, 0.0, 1.0, (-1100, 800))
    dpow = math_n(nt, 'POWER', dd, 0.55, (-950, 800))
    tint = ramp(nt, [(0.3, c4(scaled(SEA_DEEP, 0.92))), (0.7, c4(scaled(SEA_DEEP, 1.08)))], (-900, 1300)); nt.links.new(sl, tint.inputs["Fac"])
    waterc = mix_rgb(nt, shallow, tint.outputs["Color"], dpow, 'MIX', (-500, 900))
    water = map_range(nt, wz.outputs["Z"], WL - 0.002, WL - 0.009, 0.0, 1.0, (-1100, 1500))
    col = mix_rgb(nt, col, waterc, water, 'MIX', (100, 300))
    nt.links.new(col, b.inputs["Base Color"])
    land_r = map_range(nt, mid.outputs["Fac"], 0.3, 0.7, 0.95, 0.82, (-300, -200))
    land_r = mix_f(nt, land_r, 0.72, math_n(nt, 'MULTIPLY', wet, 0.7, (-500, -250)), (-200, -250))
    nt.links.new(mix_f(nt, land_r, sea_r, water, (0, -200)), b.inputs["Roughness"])
    fine = noise_tex(nt, mp.outputs["Vector"], 3.0, 6, 0.6, loc=(-500, -600))
    hh = mix_f(nt, fine.outputs["Fac"], sea_h, water, (-200, -600))
    bump_from(nt, b, hh, 0.05, 0.25)          # exactly the sea's bump, so the shallows and the open sea meet without a seam
    return m

def sky_dome_mat(name="M_SkyDome"):
    """A hazy summer morning in a dead calm: milky-white haze along the horizon, a soft blue overhead, a few thin
    high streaks well above the horizon, the sun's glow behind the reader's right shoulder, and the dark cloud
    that never leaves the peak of Scylla's rock far ahead to starboard. Emission only (unlit in Unity)."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeNewGeometry", (-2000, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-1800, 0), operation='NORMALIZE'); nt.links.new(tc.outputs["Position"], nv.inputs[0])
    sep = sep_xyz(nt, nv.outputs[0], (-1600, 0)); el = sep.outputs["Z"]
    base = ramp(nt, [(0.0, (0.66, 0.70, 0.72, 1)), (0.10, (0.70, 0.74, 0.77, 1)), (0.135, (0.60, 0.68, 0.77, 1)), (0.2, (0.45, 0.58, 0.75, 1)),
                     (0.4, (0.29, 0.45, 0.70, 1)), (1.0, (0.18, 0.34, 0.63, 1))], (-1200, 300))
    nt.links.new(map_range(nt, el, -0.12, 1.0, 0.0, 1.0, (-1400, 300)), base.inputs["Fac"])
    col = base.outputs["Color"]
    # thin high cirrus, projected onto a flat deck, kept well above the horizon
    zk = math_n(nt, 'ADD', math_n(nt, 'MAXIMUM', el, 0.0, (-1400, -100)), 0.08, (-1250, -100))
    px = math_n(nt, 'DIVIDE', sep.outputs["X"], zk, (-1100, -50)); py = math_n(nt, 'DIVIDE', sep.outputs["Y"], zk, (-1100, -200))
    cv = node(nt, "ShaderNodeCombineXYZ", (-950, -100)); nt.links.new(px, cv.inputs["X"]); nt.links.new(py, cv.inputs["Y"])
    mp = node(nt, "ShaderNodeMapping", (-800, -100)); mp.inputs["Scale"].default_value = (0.25, 1.4, 1); mp.inputs["Rotation"].default_value = (0, 0, 0.6)
    mp.inputs["Location"].default_value = (2.1, 5.3, 0.0)
    nt.links.new(cv.outputs[0], mp.inputs["Vector"])
    cl = noise_tex(nt, mp.outputs["Vector"], 0.9, 8, 0.6, 0.6, (-600, -100))
    cr = map_range(nt, cl.outputs["Fac"], 0.56, 0.72, 0.0, 0.28, (-400, -100))
    cmask = map_range(nt, el, 0.22, 0.45, 0.0, 1.0, (-400, -300))
    col = mix_rgb(nt, col, (0.86, 0.88, 0.90, 1), math_n(nt, 'MULTIPLY', cr, cmask, (-250, -200)), 'MIX', (-100, 100))
    # the sun's glow (behind the reader's right shoulder)
    sd = node(nt, "ShaderNodeVectorMath", (-1400, 600), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(SUN_DIR)
    nt.links.new(nv.outputs[0], sd.inputs[0])
    glow = map_range(nt, sd.outputs["Value"], 0.7, 1.0, 0.0, 0.45, (-1200, 600))
    col = mix_rgb(nt, col, (0.98, 0.95, 0.86, 1), glow, 'MIX', (50, 100))
    # Scylla's cloud: a dark grey cap sitting on the far peak
    hz = node(nt, "ShaderNodeCombineXYZ", (-1500, 900)); nt.links.new(sep.outputs["X"], hz.inputs["X"]); nt.links.new(sep.outputs["Y"], hz.inputs["Y"])
    hn = node(nt, "ShaderNodeVectorMath", (-1350, 900), operation='NORMALIZE'); nt.links.new(hz.outputs["Vector"], hn.inputs[0])
    cd = node(nt, "ShaderNodeVectorMath", (-1200, 900), operation='DOT_PRODUCT'); cd.inputs[1].default_value = tuple(Vector((CLOUD_DIR.x, CLOUD_DIR.y, 0.0)).normalized())
    nt.links.new(hn.outputs[0], cd.inputs[0])
    cn = noise_tex(nt, nv.outputs[0], 14.0, 6, 0.62, 0.8, (-1400, 1100))
    jit = math_n(nt, 'MULTIPLY', math_n(nt, 'SUBTRACT', cn.outputs["Fac"], 0.5, (-1200, 1100)), 0.06, (-1100, 1100))
    az = map_range(nt, math_n(nt, 'ADD', cd.outputs["Value"], math_n(nt, 'MULTIPLY', jit, 0.05, (-1050, 1000)), (-1000, 950)), math.cos(math.radians(13.0)), math.cos(math.radians(4.0)), 0.0, 1.0, (-850, 950))
    elv = math_n(nt, 'ADD', el, math_n(nt, 'MULTIPLY', jit, 0.6, (-1100, 1250)), (-1000, 1150))
    lo = map_range(nt, elv, math.sin(_ce - math.radians(5.5)), math.sin(_ce - math.radians(3.0)), 0.0, 1.0, (-850, 1150))
    hi_ = map_range(nt, elv, math.sin(_ce + math.radians(3.5)), math.sin(_ce + math.radians(0.8)), 0.0, 1.0, (-850, 1300))
    capf = math_n(nt, 'MULTIPLY', math_n(nt, 'MULTIPLY', az, lo, (-700, 1000)), hi_, (-600, 1000))
    capf = math_n(nt, 'MULTIPLY', capf, 0.9, (-500, 1000))
    capc = ramp(nt, [(0.3, (0.40, 0.42, 0.45, 1)), (0.7, (0.50, 0.52, 0.55, 1))], (-850, 1450)); nt.links.new(cn.outputs["Fac"], capc.inputs["Fac"])
    col = mix_rgb(nt, col, capc.outputs["Color"], capf, 'MIX', (200, 100))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m

# positions the materials need
_bu, _bv = 0.40 * ISLE_A, -0.48 * ISLE_B
BONES_XY = isle_xy(_bu, _bv)
PEAK_BEARING = math.radians(-52.0)                       # to the reader's right, ahead (bow at -24)
PEAK_DIST, PEAK_H = 113.0, 19.0
PEAK_XY = (PEAK_DIST * math.sin(PEAK_BEARING), -PEAK_DIST * math.cos(PEAK_BEARING))
_ce = math.atan2(PEAK_H - 2.0 - EYE, PEAK_DIST)
CLOUD_DIR = Vector((math.sin(PEAK_BEARING) * math.cos(_ce), -math.cos(PEAK_BEARING) * math.cos(_ce), math.sin(_ce))).normalized()

M_HULL = hull_mat("M_HullBlack")
M_HULLIN = hull_mat("M_HullInner", inner=True)
M_WALE = timber_mat("M_Wale", base=(0.035, 0.026, 0.018), dark=(0.012, 0.010, 0.008), light=(0.09, 0.065, 0.045), along='Y', rough=(0.4, 0.7), grime=0.2)
M_DECK = deck_mat()
M_TIMBER = timber_mat("M_Timber", base=(0.20, 0.135, 0.08), dark=(0.06, 0.04, 0.025), light=(0.36, 0.27, 0.18), along='X', salt=0.15)
M_FRAMES = timber_mat("M_Frames", base=(0.12, 0.08, 0.05), dark=(0.035, 0.025, 0.016), light=(0.22, 0.16, 0.10), along='Z', grime=0.5)
M_OAR = timber_mat("M_OarWood", base=(0.36, 0.28, 0.18), dark=(0.13, 0.09, 0.055), light=(0.52, 0.44, 0.32), along='Y', rough=(0.5, 0.8), salt=0.2)
M_SPAR = timber_mat("M_Spar", base=(0.27, 0.19, 0.115), dark=(0.08, 0.055, 0.035), light=(0.42, 0.33, 0.22), along='Z', rough=(0.5, 0.8), salt=0.15)
M_SAIL = sail_mat()
M_ROPE = rope_mat()
M_BRONZE = bronze_mat()
M_WAX = wax_mat()
M_TERRA = noisy("M_Terracotta", [(0.36, 0.17, 0.08), (0.48, 0.25, 0.13), (0.55, 0.33, 0.20)], scale=9, rough=0.85, bump=0.2, bump_dist=0.001)
M_BALLAST = stone_mat("M_Ballast", ((0.22, 0.21, 0.19), (0.36, 0.34, 0.30), (0.50, 0.47, 0.41)), scale=9.0, world=False)
M_SEA = sea_mat()
M_FARSEA = sea_mat("M_FarSea", far=True)
M_SKYDOME = sky_dome_mat()
M_ISLE = isle_ground_mat()
M_ISLEROCK = stone_mat("M_IsleRock", ((0.20, 0.19, 0.165), (0.30, 0.285, 0.25), (0.38, 0.36, 0.31)), scale=1.1, wet_below=WL, lichen=0.35, crack=0.25, beds=0.8)
M_SHRUB = noisy("M_Maquis", [(0.018, 0.032, 0.012), (0.04, 0.058, 0.022), (0.07, 0.08, 0.035)], scale=2.6, rough=0.85, bump=0.9, bump_dist=0.08, world=True, warp=1.5)
M_BONES = noisy("M_Bones", [(0.22, 0.205, 0.17), (0.31, 0.29, 0.245), (0.38, 0.36, 0.30)], scale=6.0, rough=0.85, bump=0.6, bump_dist=0.03, world=True)
M_FARCOAST = noisy("M_FarCoast", [(0.19, 0.23, 0.27), (0.23, 0.27, 0.30), (0.26, 0.29, 0.31)], scale=0.06, rough=1.0, bump=0.0, world=True)
def _summit_in_cloud(m):
    """Scylla's rock 'reaches heaven and its peak is lost in a dark cloud': above ~15 m the far coast fades, with a
    ragged edge, into the grey of the cloud bank the dome paints round the summit."""
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    col = b.inputs["Base Color"].links[0].from_socket
    g = node(nt, "ShaderNodeNewGeometry", (-1200, -600)); wz = sep_xyz(nt, g.outputs["Position"], (-1000, -600))
    cn = noise_tex(nt, g.outputs["Position"], 0.35, 5, 0.6, 0.5, (-1000, -800))
    zz = math_n(nt, 'ADD', wz.outputs["Z"], math_n(nt, 'MULTIPLY', cn.outputs["Fac"], 6.0, (-850, -800)), (-750, -650))
    f = map_range(nt, zz, PEAK_H - 9.0, PEAK_H - 3.0, 0.0, 1.0, (-600, -650))
    nt.links.new(mix_rgb(nt, col, (0.40, 0.41, 0.43, 1), f, 'MIX', (-300, 0)), b.inputs["Base Color"])
_summit_in_cloud(M_FARCOAST)

# ----------------------------------------------------------------------------- geometry helpers (from build_calypsos_cave.py)
def set_attr(o, name, value):
    me = o.data
    if name not in me.attributes: me.attributes.new(name, 'FLOAT', 'POINT')
    a = me.attributes[name]
    vals = value if isinstance(value, list) else [value] * len(me.vertices)
    a.data.foreach_set("value", vals)

def _finish(o, mat, smooth=True):
    o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0), smooth=False, rnd=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = 1; md.limit_method = 'ANGLE'
    o = _finish(o, mat, smooth)
    set_attr(o, "rnd", random.random() if rnd is None else rnd)
    return o

def cyl(name, r, h, loc, mat, verts=12, rot=(0, 0, 0), r2=None, rnd=None):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o = _finish(o, mat)
    set_attr(o, "rnd", random.random() if rnd is None else rnd)
    return o

def torus(name, R, r, loc, mat, rot=(0, 0, 0), seg=16, mseg=4):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=mseg, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat)

def lathe(name, profile, loc, mat, steps=16, rot=(0, 0, 0), wobble=0.0, seed=0.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for (r, z) in profile:
        if r < 1e-5: rings.append([bm.verts.new((0, 0, z))]); continue
        ring = []
        for i in range(steps):
            a = 2 * math.pi * i / steps
            k = 1.0 + (wobble * noise.noise(Vector((math.cos(a) * 1.5 + seed, math.sin(a) * 1.5, z * 2.0))) if wobble else 0.0)
            ring.append(bm.verts.new((r * k * math.cos(a), r * k * math.sin(a), z)))
        rings.append(ring)
    for a, b_ in zip(rings, rings[1:]):
        if len(a) == 1 and len(b_) == 1: continue
        if len(a) == 1:
            for i in range(steps): bm.faces.new((a[0], b_[(i + 1) % steps], b_[i]))
        elif len(b_) == 1:
            for i in range(steps): bm.faces.new((a[i], a[(i + 1) % steps], b_[0]))
        else:
            for i in range(steps):
                j = (i + 1) % steps; bm.faces.new((a[i], a[j], b_[j], b_[i]))
    bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def blob(name, loc, radius, mat, scale=(1, 1, 1), subdiv=1, amp=0.25, freq=1.6, seed=0.0, rot=(0, 0, 0), flat_bottom=None, flat_top=None, smooth=True):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    for v in bm.verts:
        n = v.co.normalized()
        k = 1.0 + amp * noise.noise(n * freq + Vector((seed, seed * 1.7, seed * 0.3)))
        p = Vector((n.x * radius * k * scale[0], n.y * radius * k * scale[1], n.z * radius * k * scale[2]))
        if flat_bottom is not None: p.z = max(p.z, flat_bottom)
        if flat_top is not None: p.z = min(p.z, flat_top)
        v.co = p
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = smooth
    return link(o)

def catmull(pts, n):
    pts = [Vector(p) for p in pts]
    P = [pts[0]] + pts + [pts[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    out.append(pts[-1])
    return out

def tube(name, pts, radii, mat, sides=6, n=4, rnd=None, rect=None):
    """A tapered tube along a Catmull-Rom path; rect=(w, h) gives a rectangular timber section (h along up)."""
    c = catmull(pts, n); rr = [lerp(radii[0], radii[1], i / max(1, len(c) - 1)) for i in range(len(c))]
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    up = Vector((0, 0, 1))
    for i, p in enumerate(c):
        t = (c[min(i + 1, len(c) - 1)] - c[max(i - 1, 0)]).normalized()
        a = t.cross(up if abs(t.dot(up)) < 0.9 else Vector((1, 0, 0))).normalized(); b_ = t.cross(a).normalized()
        if rect:
            w, h = rect
            rings.append([bm.verts.new(p + a * (sx * w / 2) + b_ * (sy * h / 2)) for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
        else:
            rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / sides) + b_ * math.sin(2 * math.pi * k / sides)) * rr[i]) for k in range(sides)])
    ns = 4 if rect else sides
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(ns):
            j = (k + 1) % ns; bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = not rect
    link(o)
    set_attr(o, "rnd", random.random() if rnd is None else rnd)
    return o

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

# ============================================================================= THE SHIP (built in the ship frame, then turned into place)
_before_ship = set(COLL.objects)

def hull_surface(name, mat, inner=False, NY=50, NS=10):
    """Lofted planking: stations along y, a section from port sheer down round the keel to starboard sheer.
    Attribute 's' is the height up the section (0 keel .. 1 sheer) for the strake seams."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    s0 = 0.16 if inner else 0.0
    rows = []; svals = []
    for i in range(NY + 1):
        t = i / NY
        y = lerp(Y_BOW + 0.02, Y_STERN - 0.02, 0.5 - 0.5 * math.cos(math.pi * t) * 0.25 - (0.5 - t) * 0.75)
        k, sh = keel(y), sheer(y)
        row = []
        for side in (1, -1):
            js = range(NS, -1, -1) if side == 1 else range(1, NS + 1)
            for j in js:
                s = lerp(s0, 1.0, (j / NS) ** 0.8)
                z = k + (sh - k) * s + (0.06 if inner and s < 0.3 else 0.0) * (1 - s / 0.3)
                x = side * max(0.0, beam(y) * sect(s) - (HULL_T if inner else 0.0))
                if side == -1 and j == 0: continue
                row.append(bm.verts.new((x, y, z))); svals.append(s)
        rows.append(row)
    for a, b_ in zip(rows, rows[1:]):
        for k in range(len(a) - 1):
            f = bm.faces.new((a[k], a[k + 1], b_[k + 1], b_[k]) if not inner else (a[k], b_[k], b_[k + 1], a[k + 1]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    link(o)
    set_attr(o, "s", svals); set_attr(o, "rnd", 0.5)
    # make the outer normals face out, the inner face in (towards the centreline)
    bm = bmesh.new(); bm.from_mesh(me)
    for f in bm.faces:
        c = f.calc_center_median(); out = Vector((c.x, 0.0, max(0.0, -(c.z - keel(c.y)) * 0.0))).normalized() if abs(c.x) > 1e-3 else Vector((0, 0, -1))
        want_out = not inner
        if (f.normal.dot(out) > 0) != want_out: f.normal_flip()
    bm.to_mesh(me); bm.free()
    return o

hull_surface("HullOuter", M_HULL)
hull_surface("HullInner", M_HULLIN, inner=True)

# the wale (gunwale timber) capping the planking along the sheer, and a rubbing strake outside
for side in (1, -1):
    ys = [lerp(-19.1, 2.55, i / 30) for i in range(31)]
    tube(f"Gunwale{side}", [(side * (beam(y) - HULL_T * 0.5), y, sheer(y) + 0.025) for y in ys], (0.05, 0.05), M_WALE, n=2, rect=(0.11, 0.075))
    tube(f"Rubbing{side}", [(side * (beam(y) * sect(0.62) + 0.02), y, keel(y) + (sheer(y) - keel(y)) * 0.62) for y in ys[2:-3]], (0.04, 0.04), M_WALE, n=2, rect=(0.05, 0.08))

# stem and stern post: the black ship's curved ends, the stern rising high over the steersman
tube("SternPost", [(0, 2.62, -1.55), (0, 2.86, -0.6), (0, 2.98, 0.5), (0, 2.92, 1.5), (0, 2.62, 2.35), (0, 2.15, 2.78), (0, 1.78, 2.72), (0, 1.66, 2.5)],
     (0.13, 0.045), M_HULL, sides=7, n=4)
tube("Stem", [(0, -19.55, -1.5), (0, -19.82, -0.7), (0, -19.95, 0.3), (0, -19.88, 1.0), (0, -19.62, 1.42), (0, -19.38, 1.5)], (0.11, 0.05), M_HULL, sides=7, n=3)
tube("Cutwater", [(0, -19.4, -1.48), (0, -20.1, -1.40), (0, -20.65, -1.22)], (0.09, 0.05), M_HULL, sides=6, n=2)
for o in [bpy.data.objects[n] for n in ("SternPost", "Stem", "Cutwater")]: set_attr(o, "s", 0.98)

# frames (ribs) inside, between the benches; a clamp (stringer) carrying the benches
for k, y in enumerate([-2.45 - i * 1.0 for i in range(14)] + [-16.05]):
    for side in (1, -1):
        pts = []
        for s in (0.17, 0.33, 0.52, 0.72, 0.9, 0.99):
            z = keel(y) + (sheer(y) - keel(y)) * s
            pts.append((side * (beam(y) * sect(s) - HULL_T - 0.03), y, z))
        tube(f"Frame{k}_{side}", pts, (0.032, 0.032), M_FRAMES, n=2, rect=(0.07, 0.065))
for side in (1, -1):
    ys = [lerp(-2.3, -15.8, i / 16) for i in range(17)]
    zc = THWART_Z - 0.06
    tube(f"Clamp{side}", [(side * (hb(y, zc, True) - 0.035), y, zc) for y in ys], (0.03, 0.03), M_FRAMES, n=2, rect=(0.06, 0.08))

# rowing benches (thwarts), each on a stanchion; the bench before the mast is heavier (the mast partner)
for k, y in enumerate(THWARTS):
    w = 0.30 if abs(y - (MAST_Y + 0.3)) < 0.45 else 0.23 + random.uniform(-0.015, 0.02)
    th = 0.085 if w > 0.28 else 0.06
    L = 2 * hb(y, THWART_Z, True) + 0.02
    box(f"Thwart{k}", (L, w, th), (0, y + random.uniform(-0.02, 0.02), THWART_Z), M_TIMBER, bevel=0.008, rot=(0, 0, random.uniform(-0.012, 0.012)))
    if k % 2 == 0:
        cyl(f"Stanchion{k}", 0.04, THWART_Z - FLOOR_Z - 0.03, (0, y, (THWART_Z + FLOOR_Z) / 2 - 0.015), M_FRAMES, verts=6)

# loose floor boards along the bottom between the benches, ballast stones in the bilge between them
FLOOR_PLANKS = [-0.66, -0.36, -0.05, 0.27, 0.58]
for i, x in enumerate(FLOOR_PLANKS):
    ys = [y for y in [lerp(-1.9, -16.4, j / 120) for j in range(121)] if hb(y, FLOOR_Z, True) > abs(x) + 0.18]
    if len(ys) < 2: continue
    y0, y1 = max(ys), min(ys)
    # each run is two or three boards butted end to end
    cuts = sorted([y0, y1] + [lerp(y0, y1, f) for f in random.sample([0.31, 0.47, 0.63], 1 + i % 2)], reverse=True)
    for k, (ya, yb) in enumerate(zip(cuts, cuts[1:])):
        box(f"FloorBoard{i}_{k}", (0.27 + random.uniform(-0.02, 0.01), ya - yb - 0.012, 0.03), (x, (ya + yb) / 2, FLOOR_Z), M_TIMBER, bevel=0.005,
            rot=(random.uniform(-0.01, 0.01), 0, random.uniform(-0.006, 0.006)))
rb = random.Random(12)
for k in range(22):
    y = rb.uniform(-15.5, -2.4)
    side = rb.choice((-1, 1))
    zz = FLOOR_Z - 0.02
    x = side * rb.uniform(0.82, max(0.85, hb(y, zz, True) - 0.08))
    r = rb.uniform(0.06, 0.12)
    blob(f"Ballast{k}", (x, y, zz + r * 0.35), r, M_BALLAST, scale=(1.2, 1.0, 0.7), subdiv=1, amp=0.25, seed=k * 1.9, rot=(0, 0, rb.uniform(0, 3)))

# the stern deck (ikria): athwartship boards on two beams, a riser closing its front, a light rail each side
DECK_Y0, DECK_Y1 = -1.75, 1.62
y = DECK_Y0; k = 0
while y < DECK_Y1 - 0.08:
    w = random.uniform(0.18, 0.24)
    yc = y + w / 2
    L = 2 * hb(yc, -0.02, True) - 0.01
    box(f"DeckBoard{k}", (L, w - 0.009, 0.045), (0, yc, -0.0225), M_DECK, bevel=0.006, rot=(random.uniform(-0.004, 0.004), 0, random.uniform(-0.004, 0.004)))
    y += w; k += 1
for x in (-0.55, 0.55):
    tube(f"DeckBeamLong{x}", [(x, DECK_Y0 - 0.02, -0.11), (x, DECK_Y1 - 0.15, -0.11)], (0.05, 0.05), M_FRAMES, n=1, rect=(0.10, 0.12))
box("DeckBeamFront", (2 * hb(DECK_Y0, -0.12, True), 0.12, 0.13), (0, DECK_Y0 + 0.05, -0.11), M_FRAMES, bevel=0.01)

def section_panel(name, y, z0, z1, thick, mat, n=8):
    """A slab of boards filling the hull's inside section between two heights (front of the stern deck)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    zs = [lerp(z0, z1, i / n) for i in range(n + 1)]
    front, back = [], []
    for z in zs:
        h = hb(y, z, True) - 0.005
        front.append((bm.verts.new((-h, y - thick / 2, z)), bm.verts.new((h, y - thick / 2, z))))
        back.append((bm.verts.new((-h, y + thick / 2, z)), bm.verts.new((h, y + thick / 2, z))))
    for i in range(n):
        bm.faces.new((front[i][0], front[i][1], front[i + 1][1], front[i + 1][0]))
        bm.faces.new((back[i][1], back[i][0], back[i + 1][0], back[i + 1][1]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat); link(o)
    set_attr(o, "rnd", 0.4)
    return o
section_panel("SternRiser", DECK_Y0 - 0.03, FLOOR_Z - 0.05, -0.05, 0.03, M_TIMBER)
section_panel("BowBulkhead", -16.85, FLOOR_Z, -0.32, 0.03, M_TIMBER)
# a two-step ladder down from the stern deck into the rowing space
for i, z in enumerate((-0.45, -0.95)):
    box(f"Step{i}", (0.55, 0.2, 0.05), (-0.25, DECK_Y0 - 0.25 - i * 0.22, z), M_TIMBER, bevel=0.006)
for sx in (-0.52, 0.02):
    tube(f"StepStringer{sx}", [(sx, DECK_Y0 - 0.08, -0.05), (sx, DECK_Y0 - 0.62, FLOOR_Z + 0.02)], (0.03, 0.03), M_TIMBER, n=1, rect=(0.04, 0.12))
# rail on short posts along the stern deck sides
for side in (1, -1):
    ys = [lerp(-1.55, 1.45, i / 5) for i in range(6)]
    for j, yy in enumerate(ys):
        x = side * (beam(yy) - 0.09)
        cyl(f"RailPost{side}_{j}", 0.025, 0.86 - sheer(yy), (x, yy, (0.86 + sheer(yy)) / 2), M_SPAR, verts=6)
    tube(f"Rail{side}", [(side * (beam(yy) - 0.09), yy, 0.88) for yy in ys], (0.03, 0.03), M_OAR, sides=6, n=3, rnd=0.15)

# foredeck at the bow
y = -19.05; k = 0
while y < -16.95:
    w = random.uniform(0.2, 0.25); yc = y + w / 2
    L = 2 * hb(yc, -0.34, True) - 0.01
    if L > 0.15: box(f"ForeBoard{k}", (L, w - 0.01, 0.04), (0, yc, -0.32), M_DECK, bevel=0.005)
    y += w; k += 1

# thole pins on the gunwale, one per oar
for k, y in enumerate(THWARTS):
    for side in (1, -1):
        yy = y + 0.32
        cyl(f"Thole{k}_{side}", 0.022, 0.2, (side * (beam(yy) - HULL_T * 0.5), yy, sheer(yy) + 0.13), M_TIMBER, verts=6)

# oars shipped: drawn in and laid fore-and-aft along the benches, in three runs a side
def oar(name, x, y0, length, flip, z, rnd):
    d = 1 if flip else -1                                 # blades forward unless flipped
    yb = y0 + d * (length - 0.55)                         # the blade end
    tube(name + "_Loom", [(x, y0, z), (x, yb, z)], (0.034, 0.03), M_OAR, sides=6, n=1, rnd=rnd)
    box(name + "_Blade", (0.15, 0.62, 0.022), (x, yb + d * 0.27, z - 0.005), M_OAR, rot=(0, random.uniform(-0.25, 0.25), 0), rnd=rnd)
    cyl(name + "_Grip", 0.026, 0.3, (x, y0 - d * 0.12, z), M_OAR, verts=6, rot=(math.pi / 2, 0, 0), rnd=min(1.0, rnd * 0.3))
oz = THWART_Z + 0.03 + 0.034
n_oar = 0
for side in (1, -1):
    for run, (ys, flip) in enumerate([(-2.75, False), (-7.05, False), (-11.4, False)]):
        nslot = 5 if run < 2 else 3
        for j in range(nslot):
            x = side * (hb(ys - 4.1, THWART_Z, True) - 0.12 - j * 0.085)     # clear of the planking at the narrower, forward end
            stagger = random.uniform(-0.15, 0.15)
            if n_oar >= 26: break
            oar(f"Oar{n_oar}", x, ys + stagger, 4.1 + random.uniform(-0.1, 0.1), flip, oz, random.random())
            n_oar += 1
print("oars", n_oar)

# the mast, stepped in its box, the crosspiece Ulysses stood upon, the rope's ends lashed to the mast itself
MAST_TOP = 7.4
cyl("Mast", 0.12, MAST_TOP - FLOOR_Z, (0, MAST_Y, (MAST_TOP + FLOOR_Z) / 2), M_SPAR, verts=12, r2=0.075)
box("MastStep", (0.42, 0.55, 0.14), (0, MAST_Y, FLOOR_Z + 0.05), M_FRAMES, bevel=0.012)
for sx in (-1, 1):
    box(f"MastCheek{sx}", (0.05, 0.62, 0.62), (sx * 0.15, MAST_Y, (THWART_Z + FLOOR_Z) / 2 + 0.05), M_FRAMES, bevel=0.006)
box("MastCap", (0.2, 0.2, 0.18), (0, MAST_Y, MAST_TOP + 0.05), M_SPAR, bevel=0.015)
CROSS_Z = THWART_Z + 0.75
box("MastCrosspiece", (0.66, 0.1, 0.08), (0, MAST_Y - 0.14, CROSS_Z), M_SPAR, bevel=0.01)
for i, z in enumerate([CROSS_Z + 0.06, CROSS_Z + 0.1, CROSS_Z + 0.95, CROSS_Z + 1.0, CROSS_Z + 1.05]):
    torus(f"MastLashing{i}", 0.118 - 0.002 * z, 0.014, (0, MAST_Y, z), M_ROPE, rot=(random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08), 0), seg=14, mseg=4)
# the loose ends of the bonds hanging from the lashing and coiled on the bench by the mast
tube("RopeEnd0", [(0.1, MAST_Y - 0.05, CROSS_Z + 0.95), (0.2, MAST_Y - 0.12, CROSS_Z + 0.5), (0.24, MAST_Y - 0.2, CROSS_Z + 0.1), (0.3, MAST_Y + 0.08, THWART_Z + 0.08)],
     (0.014, 0.014), M_ROPE, sides=5, n=4)
for i in range(5):
    torus(f"RopeCoil{i}", 0.19 - i * 0.012, 0.016, (0.45 + random.uniform(-0.01, 0.01), MAST_Y + 0.33, THWART_Z + 0.05 + i * 0.026), M_ROPE, seg=16, mseg=4,
          rot=(random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05), i))
# rigging: two forestays to the bow, the backstay to the stern, the halyard down to the mast foot
def rope_line(name, a, b_, sag=0.06, r=0.016):
    a, b_ = Vector(a), Vector(b_); m_ = (a + b_) / 2 - Vector((0, 0, sag))
    tube(name, [a, a.lerp(m_, 0.5), m_, m_.lerp(b_, 0.5), b_], (r, r), M_ROPE, sides=4, n=2)
for sx in (-1, 1):
    rope_line(f"Forestay{sx}", (0.04 * sx, MAST_Y - 0.06, MAST_TOP - 0.05), (sx * 0.3, -18.6, sheer(-18.6) + 0.05), sag=0.12)
rope_line("Backstay", (0, MAST_Y + 0.06, MAST_TOP - 0.05), (0, 1.95, 2.55), sag=0.15)
rope_line("Halyard", (0.0, MAST_Y + 0.12, MAST_TOP - 0.1), (0.0, MAST_Y + 0.24, THWART_Z + 0.1), sag=0.0, r=0.012)

# the yard lowered and the furled sail stowed along the benches to starboard of the mast
YARD_X = -0.48
tube("Yard", [(YARD_X, -3.3, THWART_Z + 0.12), (YARD_X - 0.02, -8.0, THWART_Z + 0.12), (YARD_X, -13.4, THWART_Z + 0.12)], (0.07, 0.06), M_SPAR, sides=8, n=4)
sail_pts = []
for i in range(29):
    t = i / 28; y = lerp(-3.6, -13.1, t)
    sail_pts.append((YARD_X + 0.1 + 0.05 * math.sin(t * 9.0), y, 0.0))
c_ = catmull(sail_pts, 2)
me = bpy.data.meshes.new("SailBundle"); bm = bmesh.new(); rings = []
for i, p in enumerate(c_):
    t = i / (len(c_) - 1)
    r0 = (0.14 + 0.045 * noise.noise(Vector((t * 9.0, 0.3, 0.0)))) * (0.5 + 0.5 * math.sin(math.pi * min(1.0, t * 1.12 + 0.03)) ** 0.4)
    zc = THWART_Z + 0.03 + r0 * 0.62
    ring = []
    for k in range(10):
        a = 2 * math.pi * k / 10
        rr = r0 * (1.0 + 0.22 * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, t * 18.0))))
        zz = zc + math.sin(a) * rr * 0.66
        ring.append(bm.verts.new((p.x + math.cos(a) * rr * 1.3, p.y, max(zz, THWART_Z + 0.035))))
    rings.append(ring)
for r0_, r1_ in zip(rings, rings[1:]):
    for k in range(10):
        j = (k + 1) % 10; bm.faces.new((r0_[k], r0_[j], r1_[j], r1_[k]))
bmesh.ops.contextual_create(bm, geom=rings[0]); bmesh.ops.contextual_create(bm, geom=rings[-1])
bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
_so = bpy.data.objects.new("SailBundle", me); me.materials.append(M_SAIL); link(_so)
for p in me.polygons: p.use_smooth = True
for i, t in enumerate([0.08, 0.27, 0.46, 0.65, 0.84]):
    p = c_[int(t * (len(c_) - 1))]
    r_ = 0.14 * (0.5 + 0.5 * math.sin(math.pi * min(1.0, t * 1.12 + 0.03)) ** 0.4)
    torus(f"SailTie{i}", r_ * 1.05, 0.011, (p.x, p.y, THWART_Z + 0.03 + r_ * 0.62), M_ROPE, rot=(math.pi / 2, 0, 0), seg=12, mseg=4)
    bpy.data.objects[f"SailTie{i}"].scale = (1.3, 1.0, 0.66)

# twin steering oars at the quarters, their tillers reaching inboard over the stern deck
for side in (1, -1):
    yp = 0.92
    xs = side * (beam(yp) + 0.05)
    top = Vector((side * (beam(yp) - 0.02), yp - 0.12, 1.02))
    bot = Vector((side * (beam(yp) + 0.55), yp + 2.35, WL - 1.1))
    d = (bot - top).normalized()
    tube(f"SteerLoom{side}", [top, top + d * 1.2, bot - d * 1.4], (0.07, 0.06), M_OAR, sides=8, n=2, rnd=0.35)
    bl0 = bot - d * 1.45
    blade = box(f"SteerBlade{side}", (0.05, 0.36, 1.55), ((bl0 + bot) / 2), M_OAR, rnd=0.3)
    blade.rotation_euler = d.to_track_quat('Z', 'X').to_euler()
    tiller_end = Vector((side * 0.32 if side == -1 else side * 0.18, yp - 0.05, 0.98))
    tube(f"Tiller{side}", [top + Vector((0, 0, -0.03)), tiller_end], (0.032, 0.026), M_OAR, sides=6, n=1, rnd=0.25)
    # the pivot: a chock on the wale and a lashing round the loom
    box(f"SteerChock{side}", (0.16, 0.3, 0.16), (xs - side * 0.02, yp - 0.05, sheer(yp) + 0.1), M_FRAMES, bevel=0.015)
    pv = top + d * ((sheer(yp) + 0.18 - top.z) / d.z)
    torus(f"SteerLashing{side}", 0.085, 0.018, pv, M_ROPE, rot=d.to_track_quat('Z', 'X').to_euler(), seg=12, mseg=4)
    torus(f"SteerLashing2{side}", 0.085, 0.018, pv + d * 0.06, M_ROPE, rot=d.to_track_quat('Z', 'X').to_euler(), seg=12, mseg=4)

# on the stern deck: the wheel of wax cut up small, the sword beside it, a coil of line, two jars lashed aft
WAX = Vector((RX - 0.35, -0.95, 0.0))
def wax_wheel(name, c, r=0.125, h=0.055, keep=1.42, a0=0.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); n = max(3, int(16 * keep / 2))
    rim_b, rim_t = [], []
    for i in range(n + 1):
        a = a0 + keep * math.pi * i / n
        k = 1.0 + 0.03 * noise.noise(Vector((math.cos(a) * 3, math.sin(a) * 3, 0.5)))
        rim_b.append(bm.verts.new((c.x + r * k * math.cos(a), c.y + r * k * math.sin(a), c.z)))
        rim_t.append(bm.verts.new((c.x + r * k * 0.96 * math.cos(a), c.y + r * k * 0.96 * math.sin(a), c.z + h)))
    cb = bm.verts.new((c.x, c.y, c.z)); ct = bm.verts.new((c.x, c.y, c.z + h))
    for i in range(n):
        bm.faces.new((rim_b[i], rim_b[i + 1], rim_t[i + 1], rim_t[i]))
        bm.faces.new((ct, rim_t[i], rim_t[i + 1])); bm.faces.new((cb, rim_b[i + 1], rim_b[i]))
    bm.faces.new((cb, rim_b[0], rim_t[0], ct)); bm.faces.new((cb, ct, rim_t[-1], rim_b[-1]))
    bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_WAX); link(o)
    return o
box("WaxBoard", (0.42, 0.3, 0.03), (WAX.x, WAX.y, 0.015), M_TIMBER, bevel=0.006, rot=(0, 0, 0.2))
wax_wheel("WaxWheel", Vector((WAX.x - 0.04, WAX.y, 0.03)), keep=1.62, a0=-0.35 * math.pi)
wax_wheel("WaxWedge", Vector((WAX.x + 0.02, WAX.y + 0.05, 0.03)), keep=0.2, a0=1.37 * math.pi, r=0.12)
rw = random.Random(3)
for k in range(9):
    a = rw.uniform(1.3 * math.pi, 1.65 * math.pi); r = rw.uniform(0.06, 0.17)
    s_ = rw.uniform(0.016, 0.03)
    bx = box(f"WaxPiece{k}", (s_ * rw.uniform(0.9, 1.6), s_, s_ * 0.8), (WAX.x - 0.04 + r * math.cos(a), WAX.y + r * math.sin(a), 0.03 + s_ * 0.4), M_WAX,
             bevel=0.004, rot=(0, 0, rw.uniform(0, 3)), smooth=True)
for k in range(3):                                         # a few crumbs fallen on the deck
    s_ = rw.uniform(0.012, 0.02)
    box(f"WaxCrumb{k}", (s_, s_ * 1.2, s_ * 0.7), (WAX.x + rw.uniform(-0.3, 0.25), WAX.y + rw.uniform(-0.25, 0.22), s_ * 0.3), M_WAX, bevel=0.003, smooth=True, rot=(0, 0, rw.uniform(0, 3)))
# the bronze sword: a leaf-shaped blade, a hilt bound in cord, lying by the board
SW = Vector((WAX.x + 0.33, WAX.y - 0.12, 0.012))
sw_rot = 0.45
me = bpy.data.meshes.new("SwordBlade"); bm = bmesh.new()
prof = [(0.0, 0.020), (0.12, 0.024), (0.30, 0.020), (0.46, 0.026), (0.56, 0.018), (0.62, 0.0)]
top, bot_ = [], []
for (s, w) in prof:
    top.append((bm.verts.new((s, w, 0.004)), bm.verts.new((s, 0.0, 0.009)), bm.verts.new((s, -w, 0.004))))
    bot_.append((bm.verts.new((s, w, -0.004 + 0.004)), bm.verts.new((s, 0.0, -0.001 + 0.0)), bm.verts.new((s, -w, 0.0))))
for i in range(len(prof) - 1):
    a, b_ = top[i], top[i + 1]
    bm.faces.new((a[0], b_[0], b_[1], a[1])); bm.faces.new((a[1], b_[1], b_[2], a[2]))
bm.normal_update(); bm.to_mesh(me); bm.free()
_sb = bpy.data.objects.new("SwordBlade", me); me.materials.append(M_BRONZE); link(_sb)
_sb.location = SW; _sb.rotation_euler = (0, 0, sw_rot)
ca, sa = math.cos(sw_rot), math.sin(sw_rot)
cyl("SwordHilt", 0.014, 0.12, (SW.x - 0.06 * ca, SW.y - 0.06 * sa, SW.z + 0.012), M_ROPE, verts=6, rot=(0, math.pi / 2, sw_rot))
box("SwordGuard", (0.025, 0.09, 0.018), (SW.x - 0.005 * ca, SW.y - 0.005 * sa, SW.z + 0.008), M_BRONZE, rot=(0, 0, sw_rot))
blob("SwordPommel", (SW.x - 0.125 * ca, SW.y - 0.125 * sa, SW.z + 0.014), 0.02, M_BRONZE, scale=(1, 1, 0.8), subdiv=1, amp=0.05)
# a coil of line on the deck to starboard
for i in range(6):
    torus(f"DeckCoil{i}", 0.22 - i * 0.022, 0.017, (-0.45, -0.75, 0.017 + (i % 2) * 0.012), M_ROPE, seg=18, mseg=4, rot=(random.uniform(-0.03, 0.03), random.uniform(-0.03, 0.03), i * 0.7))
# two jars of wine and water, lashed against the stern
for i, (x, yy, s) in enumerate([(0.32, 1.35, 1.0), (-0.12, 1.42, 0.9)]):
    lathe(f"Jar{i}", [(0.0, 0.0), (0.06 * s, 0.0), (0.17 * s, 0.14 * s), (0.21 * s, 0.32 * s), (0.18 * s, 0.5 * s), (0.08 * s, 0.62 * s), (0.055 * s, 0.68 * s),
                     (0.07 * s, 0.72 * s), (0.0, 0.72 * s)], (x, yy, 0.0), M_TERRA, steps=12, rot=(0, 0, i))
    torus(f"JarLashing{i}", 0.205 * s, 0.012, (x, yy, 0.3 * s), M_ROPE, seg=14, mseg=4)
tube("JarLine", [(-0.5, 1.45, 0.3), (-0.12, 1.25, 0.28), (0.32, 1.17, 0.3), (0.68, 1.3, 0.32)], (0.011, 0.011), M_ROPE, sides=4, n=3)

# turn the whole ship into place: world = Rz(yaw) (ship - reader)
SHIP_OBJS = [o for o in COLL.objects if o not in _before_ship]
ship_e = bpy.data.objects.new("Ship", None); link(ship_e)
bpy.context.view_layer.update()
for o in SHIP_OBJS:
    if o.parent is None: o.parent = ship_e
ship_e.rotation_euler = (0, 0, SHIP_YAW)
ship_e.location = Matrix.Rotation(SHIP_YAW, 3, 'Z') @ Vector((-RX, 0, 0))
bpy.context.view_layer.update()

# ============================================================================= THE SEA, THE ISLAND, THE FAR COASTS, THE SKY
def disc(name, r0, r1, z, mat, rings=6, seg=48, z1=None, curve=1.0, hole=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); allr = []
    centre = bm.verts.new((0, 0, z)) if r0 <= 0 else None
    for j in range(rings + 1):
        if r0 <= 0 and j == 0: continue
        f = j / rings
        rr = lerp(r0, r1, f ** curve if z1 is None else f); zz = z if z1 is None else lerp(z, z1, f ** curve)
        allr.append([bm.verts.new((rr * math.cos(2 * math.pi * i / seg), rr * math.sin(2 * math.pi * i / seg), zz)) for i in range(seg)])
    if centre is not None:
        for i in range(seg): bm.faces.new((centre, allr[0][i], allr[0][(i + 1) % seg]))
    for a, b_ in zip(allr, allr[1:]):
        for i in range(seg):
            j = (i + 1) % seg; bm.faces.new((a[i], b_[i], b_[j], a[j]))
    if hole:
        kill = [f for f in bm.faces if all(hole(v.co.x, v.co.y) for v in f.verts)]
        bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

# the island: a heightfield in its own frame; below the waterline it is flattened just under the sea plane and
# coloured as the shallows by depth, so the water's edge follows the shore exactly
ISLE_UR, ISLE_VR = (-44.0, 40.0), (-30.0, 22.0)
def isle_mesh(name="SirensIsle", NU=76, NV=46):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); grid = []; depth = []; cliffv = []
    for j in range(NV + 1):
        fv = j / NV; v = lerp(ISLE_VR[0], ISLE_VR[1], fv)
        row = []
        for i in range(NU + 1):
            fu = i / NU; u = lerp(ISLE_UR[0], ISLE_UR[1], fu)
            h = isle_h(u, v)
            x, y = isle_xy(u, v)
            row.append(bm.verts.new((x, y, WL + max(h, -0.012))))
            depth.append(max(0.0, -h)); cliffv.append(isle_cliff(u, v))
        grid.append(row)
    for j in range(NV):
        for i in range(NU):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    # a skirt dropping from the patch's border, so no gap can open where it slides under the open sea
    border = [grid[0][i] for i in range(NU)] + [grid[j][NU] for j in range(NV)] + [grid[NV][i] for i in range(NU, 0, -1)] + [grid[j][0] for j in range(NV, 0, -1)]
    low = [bm.verts.new((v.co.x, v.co.y, WL - 3.0)) for v in border]
    for k in range(len(border)):
        k2 = (k + 1) % len(border)
        bm.faces.new((border[k], low[k], low[k2], border[k2]))
    depth += [7.0] * len(low); cliffv += [0.0] * len(low)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0 and abs(f.normal.z) > 0.2: f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_ISLE); link(o)
    for p in me.polygons: p.use_smooth = True
    set_attr(o, "depth", depth); set_attr(o, "cliff", cliffv)
    # split the normals where the cliff meets the flat water, or the cliff foot shades as if it were horizontal
    es = o.modifiers.new("EdgeSplit", 'EDGE_SPLIT'); es.split_angle = math.radians(55); es.use_edge_sharp = False
    return o
isle = isle_mesh()

def in_isle_hole(x, y, margin=2.0):
    u, v = isle_uv(x, y)
    return ISLE_UR[0] + margin < u < ISLE_UR[1] - margin and ISLE_VR[0] + margin < v < ISLE_VR[1] - margin
def sea_mesh(name="Sea", M=40, K=18):
    sc = ship_w((0.0, -8.5, 0.0)); sc.z = 0.0
    ys = [lerp(-19.66, 1.85, 0.5 - 0.5 * math.cos(math.pi * j / M)) for j in range(M + 1)]
    outline = [(hb(y, WL) - 0.022, y) for y in ys] + [(-(hb(y, WL) - 0.022), y) for y in reversed(ys[1:-1])]
    me = bpy.data.meshes.new(name); bm = bmesh.new(); grid = []
    for (x, y) in outline:
        p = ship_w((max(0.0, x) if x >= 0 else min(0.0, x), y, 0.0)); p.z = 0.0
        d = (p - sc).normalized()
        b_ = sc.dot(d); c_ = sc.length_squared - SEA_R ** 2
        t = -b_ + math.sqrt(b_ * b_ - c_)
        q = sc + d * t
        grid.append([bm.verts.new((lerp(p.x, q.x, (k / K) ** 2.0), lerp(p.y, q.y, (k / K) ** 2.0), WL)) for k in range(K + 1)])
    n = len(grid)
    for i in range(n):
        a, b2 = grid[i], grid[(i + 1) % n]
        for k in range(K): bm.faces.new((a[k], b2[k], b2[k + 1], a[k + 1]))
    kill = [f for f in bm.faces if all(in_isle_hole(v.co.x, v.co.y) for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_SEA)
    return link(o)
sea_mesh()
FARSEA_RIM = EYE - 0.28
disc("far.Sea", SEA_R - 1.5, SKY_R - 1.5, WL - 0.04, M_FARSEA, rings=5, seg=96, z1=FARSEA_RIM, curve=1.7)   # tucked under the near sea's ragged rim
def farsea_z(r): return lerp(WL, FARSEA_RIM, ((r - SEA_R) / (SKY_R - 1.5 - SEA_R)) ** 1.7) if r > SEA_R else WL

def sky_dome(name, radius=SKY_R, seg=48, rings=18, el_min=-12.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    els = [el_min + (89.0 - el_min) * (j / rings) ** 1.25 for j in range(rings + 1)]
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
    o = bpy.data.objects.new(name, me); me.materials.append(M_SKYDOME)
    for p in me.polygons: p.use_smooth = True
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False; o.visible_transmission = False; o.visible_volume_scatter = False
    return link(o)
sky = sky_dome("SkyDome")

# far coasts on the horizon, hazy with distance: Aeaea astern, a long low coast to port, and ahead to starboard
# the high rock whose peak is lost in a dark cloud
def far_ridge(name, bearing_deg, dist, width_deg, height, seed, N=28, peak=None):
    """A distant coast as a ridge along an arc: a fractal skyline over a sloping face, foot in the far sea.
    peak = (t, h, w): a steep summit at fraction t along the ridge."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rows = []
    for i in range(N + 1):
        t = i / N
        br = math.radians(bearing_deg + (t - 0.5) * width_deg)
        dirv = Vector((math.sin(br), -math.cos(br), 0.0))
        env = math.sin(math.pi * t) ** 0.6
        hh = height * env * (0.62 + 0.38 * (0.5 + 0.5 * noise.noise(Vector((t * 5.0 + seed, seed, 0.0)))) + 0.12 * noise.noise(Vector((t * 17.0, seed, 1.0))))
        if peak:
            pt, ph, pw = peak
            w_ = pw * (0.55 if t < pt else 1.4)
            hh = max(hh, ph * math.exp(-((t - pt) / w_) ** 2 * 1.6) * (1.0 + 0.06 * noise.noise(Vector((t * 25.0, seed, 2.0)))))
        foot = farsea_z(dist) - 0.6
        row = []
        for f_, back in ((0.0, -1.5), (0.55, 1.0), (1.0, 3.0)):
            p = dirv * (dist + back)
            row.append(bm.verts.new((p.x, p.y, foot + (hh + 0.6) * f_)))
        rows.append(row)
    for a, b_ in zip(rows, rows[1:]):
        for k in range(2): bm.faces.new((a[k], b_[k], b_[k + 1], a[k + 1]))
    bm.normal_update()
    for f in bm.faces:
        if f.normal.dot(f.calc_center_median()) > 0: f.normal_flip()      # face the ship
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_FARCOAST)
    for p in me.polygons: p.use_smooth = True
    return link(o)
far_ridge("far.Coast_Aeaea", 172, 114, 34, 5.5, 1.0)
far_ridge("far.Coast_Port", 100, 115, 22, 3.2, 9.0, N=16)
far_ridge("far.Coast_Scylla", math.degrees(PEAK_BEARING) + 4.0, PEAK_DIST, 30, 6.0, 21.0, peak=(0.36, PEAK_H, 0.17))

# talus and fallen blocks at the foot of the cliff, partly in the water; a few at the cove's ends
def shoreline_v(u, v_lo=-24.0):
    """The near-side waterline (v where the ground rises out of the sea) along the island at u."""
    a, b_ = v_lo, 0.0
    if isle_h(u, a) > 0 or isle_h(u, b_) < 0: return None
    for _ in range(24):
        m_ = (a + b_) / 2
        if isle_h(u, m_) > 0: b_ = m_
        else: a = m_
    return (a + b_) / 2
ri = random.Random(44)
n_b = 0
u = -24.0
while u < 17.0:
    v0 = shoreline_v(u)
    c = isle_cliff(u, -10.0)
    step = lerp(4.5, 1.6, c) * ri.uniform(0.7, 1.3)
    if v0 is not None and (c > 0.15 or ri.random() < 0.35):
        r = lerp(0.4, 1.7, c) * ri.uniform(0.6, 1.2)
        vv = v0 + ri.uniform(-2.0, 0.25) * (0.5 + c)
        x, y = isle_xy(u, vv)
        z = WL + max(isle_h(u, vv), -1.2) - r * 0.25
        blob(f"Talus{n_b}", (x, y, z), r, M_ISLEROCK, scale=(1.4, 1.0, 0.8), subdiv=1, amp=0.42, freq=1.3, seed=n_b * 1.7,
             rot=(ri.uniform(-0.25, 0.25), ri.uniform(-0.25, 0.25), ri.uniform(0, 3)), flat_top=r * ri.uniform(0.35, 0.55), smooth=False)
        n_b += 1
        if c > 0.5 and ri.random() < 0.6:                      # a smaller block lying against the bigger one
            x2, y2 = isle_xy(u + r * 0.9, vv - r * 0.4)
            blob(f"Talus{n_b}", (x2, y2, WL + max(isle_h(u + r * 0.9, vv - r * 0.4), -1.0) - 0.15), r * 0.45, M_ISLEROCK, scale=(1.3, 1.0, 0.7), subdiv=1, amp=0.4, seed=n_b * 2.3,
                 flat_top=r * 0.2, smooth=False, rot=(0, 0, ri.uniform(0, 3)))
            n_b += 1
    u += step
print("talus blocks", n_b)

# maquis: low shrubs of differing size hugging the slopes and the cliff ledges, thicker in the hollows
n_s = 0
for k in range(200):
    if n_s >= 15: break
    uu, vv = ri.uniform(-24, 18), ri.uniform(-11, 9)
    h = isle_h(uu, vv)
    if h < 1.0: continue
    # slope from finite differences: shrubs on moderate slopes and ledges, not on the open field
    gx = (isle_h(uu + 0.8, vv) - isle_h(uu - 0.8, vv)) / 1.6; gy = (isle_h(uu, vv + 0.8) - isle_h(uu, vv - 0.8)) / 1.6
    sl = math.hypot(gx, gy)
    if sl < 0.25 and ri.random() < 0.75: continue
    if sl > 1.4: continue
    x, y = isle_xy(uu, vv)
    r = ri.uniform(0.35, 1.3) * (1.0 if uu < 4 else 0.7)
    for q in range(1 if r < 0.7 else ri.choice((2, 3))):
        a = ri.uniform(0, 6.3); dd = r * 0.7 * q
        x2, y2 = x + dd * math.cos(a), y + dd * math.sin(a)
        u2, v2 = isle_uv(x2, y2)
        r2 = r * (1.0 if q == 0 else ri.uniform(0.5, 0.8))
        blob(f"Maquis{n_s}_{q}", (x2, y2, WL + isle_h(u2, v2) - r2 * 0.25), r2, M_SHRUB, scale=(1.25, 1.1, ri.uniform(0.55, 0.8)), subdiv=2 if r2 > 0.55 else 1, amp=0.45, freq=3.2, seed=n_s * 3.1 + q,
             rot=(ri.uniform(-0.2, 0.2), ri.uniform(-0.2, 0.2), ri.uniform(0, 3)))
    n_s += 1
print("shrubs", n_s)

# the heap of bones at the meadow's edge above the cove, and a few lying apart
hb_z = WL + isle_h(_bu, _bv)
blob("BoneHeap", (BONES_XY[0], BONES_XY[1], hb_z - 0.3), 1.2, M_BONES, scale=(1.5, 1.1, 0.38), subdiv=2, amp=0.5, freq=4.5, seed=5.0, rot=(0, 0, 0.6), flat_bottom=-0.1)
for k in range(7):
    a = ri.uniform(0, 2 * math.pi); d = ri.uniform(2.2, 5.0)
    uu, vv = _bu + d * math.cos(a), _bv + d * math.sin(a) * 0.7
    x, y = isle_xy(uu, vv)
    blob(f"Bones{k}", (x, y, WL + isle_h(uu, vv) - 0.05), ri.uniform(0.18, 0.35), M_BONES, scale=(1.8, 0.8, 0.4), subdiv=1, amp=0.3, seed=k * 2.0, rot=(0, 0, ri.uniform(0, 3)))

# ----------------------------------------------------------------------------- anchors
anchor("reader.entrance", (0.0, 0.0, 0.0))              # on the stern deck by the port steering oar, facing -Y
anchor("reader.look", (0.0, -3.0, EYE))                  # eye height, towards the bow quarter and the open sea
anchor("scene.centre", tuple(ship_w((0.0, MAST_Y, FLOOR_Z))))
anchor("ship.mast", tuple(ship_w((0.0, MAST_Y, CROSS_Z))))
anchor("ship.bow", tuple(ship_w((0.0, -19.6, -0.3))))
anchor("ship.steering_oar", tuple(ship_w((beam(0.92), 0.8, 0.0))))
_mu, _mv = 0.2 * ISLE_A, -0.1 * ISLE_B
anchor("isle.meadow", (*isle_xy(_mu, _mv), WL + isle_h(_mu, _mv)))
anchor("isle.bones", (BONES_XY[0], BONES_XY[1], hb_z))

# ----------------------------------------------------------------------------- lights: summer sun high to the right, cool sky fill
def light_obj(name, kind, energy, color, loc, direction=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if direction is not None: lo.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return link(lo)
sun = light_obj("light.sun", 'SUN', 3.0, (1.0, 0.94, 0.84), (-8, 4, 12), direction=-SUN_DIR, angle=math.radians(1.5))
sky_l = light_obj("light.sky", 'SUN', 0.3, (0.66, 0.77, 1.0), (0, 0, 14), direction=(0.1, -0.15, -1.0), angle=math.radians(60))
sky_l.data.use_shadow = False

world = bpy.data.worlds.new("SirensCalm"); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]
try:
    skyn = wn.nodes.new("ShaderNodeTexSky")
    skyn.sky_type = 'MULTIPLE_SCATTERING'
    skyn.sun_disc = False
    skyn.sun_elevation = math.asin(SUN_DIR.z)
    skyn.sun_rotation = math.atan2(SUN_DIR.x, SUN_DIR.y)
    skyn.altitude = 100
    wn.links.new(skyn.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.15
except Exception as e:
    print("sky texture unavailable:", e)
    bg.inputs["Color"].default_value = (0.5, 0.62, 0.8, 1); bg.inputs["Strength"].default_value = 0.8

# ----------------------------------------------------------------------------- the reading page (preview renders only, never exported)
pm_, pnt, pb = new_mat("PREVIEW_PageMat")
pb.inputs["Base Color"].default_value = (0.78, 0.74, 0.64, 1); pb.inputs["Roughness"].default_value = 0.9
pb.inputs["Emission Color"].default_value = (0.78, 0.74, 0.64, 1); pb.inputs["Emission Strength"].default_value = 0.6
bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, -0.6, EYE), rotation=(math.pi / 2, 0, 0))
page = bpy.context.active_object; page.name = "PREVIEW_Page"; page.scale = (0.4, 0.55, 1.0)
page.data.materials.append(pm_)
for c in page.users_collection: c.objects.unlink(page)
link(page); page.hide_render = True

# ----------------------------------------------------------------------------- cameras for preview stills (reader eye 1.55 m)
def camera(name, loc, look_at, lens=18):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 150; cd.clip_start = 0.05
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co
E = (0.0, 0.0, EYE)
cams = [
    camera("Cam_Reader", E, (0.0, -10.0, 1.15)),
    camera("Cam_Page", E, (0.0, -10.0, 1.35)),
    camera("Cam_Left", E, (10.0, -1.5, 1.0)),
    camera("Cam_Right", E, (-10.0, -1.0, 0.9)),
    camera("Cam_Behind", E, (0.3, 10.0, 1.7)),
    camera("Cam_Deck", E, (0.05, -1.05, 0.0), lens=20),
    camera("Cam_Over", (0.42, -0.2, 1.45), (1.7, -1.1, WL), lens=20),
    camera("Cam_Isle", E, (ISLE_C.x, ISLE_C.y, WL + 4.0), lens=55),
]
CAM_EXPOSURE = {"Cam_Deck": 0.0}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "odysseus_ship_source.blend"))

# pre-export stats (printed every run so the budget is visible while iterating)
def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)
_m = [o for o in COLL.objects if o.type == 'MESH' and not o.name.startswith("PREVIEW_")]
_dg = bpy.context.evaluated_depsgraph_get()
_cat = {}
for _o in _m:
    _e = _o.evaluated_get(_dg); _me = _e.to_mesh(); _t = sum(len(p.vertices) - 2 for p in _me.polygons); _e.to_mesh_clear()
    _k = _o.data.materials[0].name if _o.data.materials else "?"
    _cat[_k] = _cat.get(_k, 0) + _t
print(f"PRE-MERGE objects={len(_m)} materials={len(_cat)} tris={sum(_cat.values())}")
for _k, _v in sorted(_cat.items(), key=lambda kv: -kv[1]): print(f"  BUDGET {_k:28s} {_v}")

# ----------------------------------------------------------------------------- render
if args.render:
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    want = set(c.strip() for c in args.cams.split(",") if c.strip())
    for c in cams:
        if want and c.name[4:].lower() not in want: continue
        scene.camera = c
        page.hide_render = c.name != "Cam_Page"
        scene.view_settings.exposure = CAM_EXPOSURE.get(c.name, 0.0)
        scene.render.filepath = os.path.join(OUT, f"render_{c.name[4:].lower()}.png")
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:
            print("GPU render failed, retrying on CPU:", str(e)[:120]); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)
    scene.view_settings.exposure = 0.0
    page.hide_render = True

# ----------------------------------------------------------------------------- bake + merge + export for Unity
KEEP_NAMES = {"M_SkyDome": "SkyDome", "M_FarSea": "far.Sea", "M_FarCoast": "far.Coast"}   # backdrop meshes keep the names Unity looks for
KEEP_UV = {"SkyDome"}                                                                       # its hand-made (longitude/latitude) UVs

def bake_and_export():
    bpy.data.objects.remove(page)
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')                       # apply modifiers (bevels)
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes:                                            # nothing here is script-controlled: unparent, keep the world transform
        if o.parent is not None:
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for e in [o for o in COLL.objects if o.type == 'EMPTY' and not o.name.startswith("anchor.")]:
        bpy.data.objects.remove(e)
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
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    scene.cycles.samples = 16
    scene.cycles.device = 'CPU'        # GPU bakes come back black when the shared GPU runs out of memory; CPU is slower but sure
    scene.render.bake.margin = 6
    T_ = args.tex
    size_for = {"M_DeckPlanks": min(4096, T_ * 2), "M_HullBlack": T_, "M_HullInner": T_, "M_Timber": T_, "M_IsleGround": T_, "M_SkyDome": T_,
                "M_Frames": T_ // 2, "M_OarWood": T_ // 2, "M_Spar": T_ // 2, "M_Sail": T_ // 2, "M_Sea": T_ // 2, "M_IsleRock": T_ // 2,
                "M_Wale": T_ // 2, "M_Rope": T_ // 4, "M_Ballast": T_ // 4, "M_Maquis": T_ // 4, "M_Terracotta": T_ // 4, "M_FarSea": T_ // 4,
                "M_FarCoast": T_ // 4, "M_Wax": T_ // 8, "M_Bronze": T_ // 8, "M_Bones": T_ // 8}
    tex_sizes = {}
    for o in merged:
        m = o.data.materials[0]; nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        size = max(64, size_for.get(m.name, T_ // 8))
        tex_sizes[o.name] = size
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        if o.name not in KEEP_UV or not o.data.uv_layers:
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
            bpy.ops.object.mode_set(mode='OBJECT')
        passes = [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]
        if o.name == "SkyDome": passes = [("BaseColor", 'EMIT', {}, False)]   # unlit in Unity: the emitted colour is its base texture
        baked = {}
        metallic = bsdf.inputs["Metallic"].default_value
        for pass_name, btype, extra, noncolor in passes:
            # a diffuse-colour bake of a metal is black: bake its albedo as a dielectric, restore metallic after
            bsdf.inputs["Metallic"].default_value = 0.0 if pass_name == "BaseColor" else metallic
            img = bpy.data.images.new(f"T_{m.name[2:]}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            for n in nt.nodes: n.select = False
            tex.select = True; nt.nodes.active = tex
            bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            img.filepath_raw = os.path.join(OUT, "textures", img.name + ".png"); os.makedirs(os.path.dirname(img.filepath_raw), exist_ok=True)
            img.file_format = 'PNG'; img.save(); img.pack()
            baked[pass_name] = tex
            print("baked", img.name, size)
        bsdf.inputs["Metallic"].default_value = metallic
        emis = bsdf.inputs["Emission Strength"].default_value; ecol = tuple(bsdf.inputs["Emission Color"].default_value)
        elinked = bsdf.inputs["Emission Color"].is_linked
        rough_v = bsdf.inputs["Roughness"].default_value
        for n in list(nt.nodes):
            if n not in baked.values(): nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
        if o.name == "SkyDome":
            nb.inputs["Base Color"].default_value = (0, 0, 0, 1)
            nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"]); nb.inputs["Emission Strength"].default_value = 1.0
            nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Base Color"])
            continue
        nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Base Color"])
        if "Roughness" in baked: nt.links.new(baked["Roughness"].outputs["Color"], nb.inputs["Roughness"])
        else: nb.inputs["Roughness"].default_value = rough_v
        if "Normal" in baked:
            nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(baked["Normal"].outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], nb.inputs["Normal"])
        nb.inputs["Metallic"].default_value = metallic
    for c in cams: bpy.data.objects.remove(c)
    gl = os.path.join(OUT, "odysseus_ship.gltf")
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False)
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={tex_sizes.get(o.name, 0)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "odysseus_ship_baked.blend"))

if args.bake or args.export:
    bake_and_export()
print("DONE")
