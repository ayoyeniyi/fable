"""
Fable: Laputa, the flying island (Gulliver's Travels, Part III, "A Voyage to Laputa", chapters I-III).

"... it appeared to be a firm substance, the bottom flat, smooth, and shining very bright, from the reflection of
the sea below ... I could see the sides of it encompassed with several gradations of galleries, and stairs, at
certain intervals, to descend from one to the other. ... a chain was let down from the lowest gallery, with a seat
fastened to the bottom, to which I fixed myself, and was drawn up by pulleys."
"The bottom, or under surface, which appears to those who view it below, is one even regular plate of adamant,
shooting up to the height of about two hundred yards. ... it is in the power of the monarch to raise the island
above the region of clouds and vapours ..."

A stone gallery on the rim of the island, mid-morning in clear, fine weather. The reader stands in a half-octagonal
belvedere that projects from the gallery, behind a waist-high balustrade, looking out over the void: two lower
galleries and the shining adamant verge step down below, and two miles beneath, through the haze, lie the fields,
river, villages and coast of Balnibarbi with a scattered layer of fair-weather cumulus between. Behind the reader the
galleries rise in tiers, linked by stairs, to the garden trees on the island's upper surface; two great stair towers
close the bay to either side. A brass telescope stands on a pedestal in the belvedere; an iron davit, pulley, chain
and seat hang over the lowest gallery. No people.

Everything is procedural (no downloaded models, textures or HDRIs): PBR node materials in world space, and the sky
and the land below generated as images by this script (numpy value-noise) and shown as emission.

Builds the environment in Blender, then (by flag) renders Cycles stills, bakes materials to textures, merges static
meshes by material and exports .gltf + .bin + textures/ for Unity.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet, on the belvedere paving (z=0), 1.0 m behind the balustrade
  anchor.reader.look      eye height (1.55 m), straight out over the void (the reader faces it)
  anchor.scene.centre     the middle of the gallery floor behind the belvedere
  anchor.gallery.stair.up / gallery.stair.down / gallery.davit / gallery.telescope / tower.left / tower.right
  light.sun (SUN, mid-morning, front-left), light.sky (SUN, cool sky fill), light.bounce (SUN from below: light
  thrown back up by the clouds and land)
  SkyDome (unlit backdrop, baked base texture), far.Land (the land, sea and clouds two miles below: unlit backdrop)

Axes: metres, Blender +Z up. The reader stands at the world origin facing Blender -Y (out over the rim), which
glTFast imports as Unity +Z. The rim runs along X; the island's interior is +Y. Reader's left is +X.
Gallery floors are at multiples of 4.5 m: -9 (the lowest gallery), -4.5, 0 (the reader), 4.5, 9, 13.5 (the top).
The page volume (x within +-0.25, y -0.45..-0.75, z 1.25..1.85) is kept clear; behind it is only sky and haze.

Run headless:
  blender -b -P blender/build_laputa.py -- --out out/laputa --render --quick --res 900
  blender -b -P blender/build_laputa.py -- --out captures/blender/laputa --render --samples 64 --res 1400
  blender -b -P blender/build_laputa.py -- --out out/laputa --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, Euler, noise
import numpy as np

# ----------------------------------------------------------------------------- args
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/laputa")
ap.add_argument("--render", action="store_true")
ap.add_argument("--bake", action="store_true")
ap.add_argument("--export", action="store_true")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", type=int, default=1400)
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--quick", action="store_true", help="low samples for iteration")
ap.add_argument("--cams", default="", help="comma list of camera names to render (default all)")
ap.add_argument("--prefix", default="render_", help="filename prefix for rendered stills")
args = ap.parse_args(argv)
OUT = os.path.abspath(args.out)
os.makedirs(OUT, exist_ok=True)
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "laputa", "gen_cache")
CACHE = os.path.abspath(CACHE); os.makedirs(CACHE, exist_ok=True)
random.seed(1726)

# ----------------------------------------------------------------------------- dimensions (metres)
TIER = 4.5                                  # vertical step between galleries
HX = 28.0                                   # the bay between the two stair towers: x in -HX..HX
TW = 8.0                                    # tower width (x)
PT = 0.32                                   # parapet thickness
G0_EDGE = 0.58                              # outer face of the reader's gallery (its wall drops to the gallery below)
G0_BACK = 4.9                               # back wall of the reader's gallery
T1_EDGE = -3.72                             # outer face of the gallery below (tier -1)
T2_EDGE = -7.92                             # outer face of the lowest gallery's parapet (tier -2)
VERGE = -8.5                                # the adamant verge, a ledge beyond the lowest parapet
BAY_IN = [(-2.8, 0.9), (-0.9, -1.0), (0.9, -1.0), (2.8, 0.9)]     # belvedere: inner face of its balustrade
RAIL_H = 1.0                                # balustrade height (waist high: nobody feels they could fall)
SKY_R = 120.0                               # sky dome radius (Unity far clip is 150 m)
LAND_R = 110.0                              # land dome radius (inside the sky dome)
SUN_DIR = Vector((0.50, -0.60, 0.63)).normalized()   # towards the sun: front-left, ~39 deg up (mid-morning)
H_ISL = 3.0                                 # km: the island's height above Balnibarbi ("about two miles high")
H_CLOUD = 1.5                               # km: cloud tops above the ground

def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def lerp(a, b, t):
    return a + (b - a) * t

# ----------------------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24 if args.quick else args.samples
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.transmission_bounces = 4
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
scene.view_settings.look = 'AgX - Base Contrast'
scene.view_settings.exposure = 0.0

COLL = bpy.data.collections.new("Laputa")
scene.collection.children.link(COLL)
def link(obj):
    COLL.objects.link(obj); return obj

# ----------------------------------------------------------------------------- material helpers (from build_calypsos_cave.py / build_kansas_farmhouse.py)
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

def c4(c): return (c[0], c[1], c[2], 1)

def math_(nt, op, a, b=None, c=None, loc=(0, 0), clamp=False):
    n = node(nt, "ShaderNodeMath", loc, operation=op); n.use_clamp = clamp
    for i, v in enumerate((a, b, c)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]

def map_range(nt, val, fmin, fmax, tmin=0.0, tmax=1.0, loc=(0, 0)):
    n = node(nt, "ShaderNodeMapRange", loc); n.clamp = True
    n.inputs["From Min"].default_value = fmin; n.inputs["From Max"].default_value = fmax
    n.inputs["To Min"].default_value = tmin; n.inputs["To Max"].default_value = tmax
    nt.links.new(val, n.inputs["Value"]); return n.outputs["Result"]

def mix_rgb(nt, a, b_, fac, blend='MIX', loc=(0, 0)):
    """a, b_: sockets or RGBA tuples; fac: socket or float."""
    mx = node(nt, "ShaderNodeMix", loc, data_type='RGBA', blend_type=blend); mx.clamp_result = True
    if isinstance(fac, (int, float)): mx.inputs["Factor"].default_value = fac
    else: nt.links.new(fac, mx.inputs["Factor"])
    for sock, v in ((mx.inputs[6], a), (mx.inputs[7], b_)):
        if isinstance(v, tuple): sock.default_value = v
        else: nt.links.new(v, sock)
    return mx.outputs[2]

def noise_tex(nt, vec, scale, detail=6.0, rough=0.6, distortion=0.0, loc=(-1000, 0)):
    n = node(nt, "ShaderNodeTexNoise", loc); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough; n.inputs["Distortion"].default_value = distortion
    nt.links.new(vec, n.inputs["Vector"]); return n

def wnoise1(nt, w, loc=(0, 0)):
    n = node(nt, "ShaderNodeTexWhiteNoise", loc, noise_dimensions='1D')
    if isinstance(w, (int, float)): n.inputs["W"].default_value = w
    else: nt.links.new(w, n.inputs["W"])
    return n.outputs["Value"]

def combine(nt, x, y, z=0.0, loc=(0, 0)):
    n = node(nt, "ShaderNodeCombineXYZ", loc)
    for sock, v in ((n.inputs[0], x), (n.inputs[1], y), (n.inputs[2], z)):
        if isinstance(v, (int, float)): sock.default_value = v
        else: nt.links.new(v, sock)
    return n.outputs[0]

def geo(nt, loc=(-2400, 0)):
    """World position and normal, separated (transforms are applied, so the bake matches the render)."""
    g = node(nt, "ShaderNodeNewGeometry", loc)
    sp = node(nt, "ShaderNodeSeparateXYZ", (loc[0] + 200, loc[1] + 200)); nt.links.new(g.outputs["Position"], sp.inputs[0])
    sn = node(nt, "ShaderNodeSeparateXYZ", (loc[0] + 200, loc[1] - 200)); nt.links.new(g.outputs["Normal"], sn.inputs[0])
    return g, sp.outputs, sn.outputs

def bump_from(nt, b, height_socket, strength, distance):
    bump = node(nt, "ShaderNodeBump", (50, -300)); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return bump

def ao_mask(nt, dist, loc=(-600, -900)):
    a = node(nt, "ShaderNodeAmbientOcclusion", loc); a.inputs["Distance"].default_value = dist; a.samples = 16
    return a.outputs["AO"]

def stone_mat(name, cols=((0.25, 0.215, 0.165), (0.38, 0.335, 0.265), (0.48, 0.43, 0.35)), course=0.42, blen=(0.75, 1.45),
              lichen=1.0, grime=1.0, rough=0.84, ashlar=True, joint_k=0.55, tone_k=0.35):
    """Coursed ashlar limestone in world space: courses along Z, blocks along the face's horizontal tangent, each
    block its own tone; fine mortar joints; mottling; rain streaks; dirt and moss rising from each gallery floor;
    grey-green and orange crustose lichen, mostly on upward faces; baked AO in the corners."""
    m, nt, b = new_mat(name)
    g, P, N = geo(nt)
    X, Y, Z = P[0], P[1], P[2]
    NX, NY, NZ = N[0], N[1], N[2]
    anz = math_(nt, 'ABSOLUTE', NZ)
    u = math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', NX, Y), math_(nt, 'MULTIPLY', NY, X))
    u = math_(nt, 'MULTIPLY_ADD', anz, math_(nt, 'MULTIPLY_ADD', X, 0.8, math_(nt, 'MULTIPLY', Y, 0.45)), u)
    zc = math_(nt, 'DIVIDE', Z, course)
    k = math_(nt, 'FLOOR', zc); fz = math_(nt, 'FRACT', zc)
    off = math_(nt, 'MULTIPLY', wnoise1(nt, k), 3.1)
    L = math_(nt, 'MULTIPLY_ADD', wnoise1(nt, math_(nt, 'ADD', k, 37.0)), blen[1] - blen[0], blen[0])
    ub = math_(nt, 'DIVIDE', math_(nt, 'ADD', u, off), L)
    bi = math_(nt, 'FLOOR', ub); fu = math_(nt, 'FRACT', ub)
    dz = math_(nt, 'MULTIPLY', math_(nt, 'MINIMUM', fz, math_(nt, 'SUBTRACT', 1.0, fz)), course)
    du = math_(nt, 'MULTIPLY', math_(nt, 'MINIMUM', fu, math_(nt, 'SUBTRACT', 1.0, fu)), L)
    jz = math_(nt, 'MULTIPLY', map_range(nt, dz, 0.003, 0.010, 1.0, 0.0), math_(nt, 'SUBTRACT', 1.0, anz))
    ju = map_range(nt, du, 0.003, 0.010, 1.0, 0.0)
    joint = math_(nt, 'MAXIMUM', jz, ju)
    if not ashlar: joint = math_(nt, 'MULTIPLY', joint, 0.0)
    wb = node(nt, "ShaderNodeTexWhiteNoise", (-1200, 600), noise_dimensions='3D'); nt.links.new(combine(nt, bi, k, 0.5), wb.inputs["Vector"])
    tone = wb.outputs["Value"] if ashlar else math_(nt, 'ADD', 0.5, 0.0)
    mott = noise_tex(nt, g.outputs["Position"], 1.3, 8, 0.62, 0.3)
    fine = noise_tex(nt, g.outputs["Position"], 16.0, 5, 0.6)
    t2 = math_(nt, 'MULTIPLY_ADD', tone, tone_k, math_(nt, 'MULTIPLY', mott.outputs["Fac"], 1.0 - tone_k))
    r = ramp(nt, [(0.25, c4(cols[0])), (0.5, c4(cols[1])), (0.72, c4(cols[2]))]); nt.links.new(t2, r.inputs["Fac"])
    fr = ramp(nt, [(0.3, (0.9, 0.9, 0.9, 1)), (0.7, (1.06, 1.05, 1.03, 1))]); nt.links.new(fine.outputs["Fac"], fr.inputs["Fac"])
    col = mix_rgb(nt, r.outputs["Color"], fr.outputs["Color"], 1.0, 'MULTIPLY')
    # rain streaks running down the faces
    smap = node(nt, "ShaderNodeMapping", (-1400, -500)); smap.inputs["Scale"].default_value = (5.0, 5.0, 0.22)
    nt.links.new(g.outputs["Position"], smap.inputs["Vector"])
    st = noise_tex(nt, smap.outputs["Vector"], 1.6, 4, 0.5)
    streak = math_(nt, 'MULTIPLY', map_range(nt, st.outputs["Fac"], 0.52, 0.70, 0.0, 0.30), math_(nt, 'SUBTRACT', 1.0, anz))
    col = mix_rgb(nt, col, (0.20, 0.19, 0.17, 1), streak, 'MIX')
    # dirt and green rising from the gallery floor below (floors at multiples of 4.5 m)
    hfl = math_(nt, 'MULTIPLY', math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', Z, 0.02), TIER)), TIER)
    gn = noise_tex(nt, g.outputs["Position"], 3.0, 4, 0.6)
    gr = math_(nt, 'MULTIPLY', map_range(nt, hfl, 0.0, 0.55, 0.65, 0.0), map_range(nt, gn.outputs["Fac"], 0.35, 0.65, 0.4, 1.0))
    gr = math_(nt, 'MULTIPLY', gr, grime)
    col = mix_rgb(nt, col, (0.16, 0.17, 0.11, 1), gr, 'MIX')
    # run-off staining hanging below each cornice and coping (the next floor level above)
    below = math_(nt, 'SUBTRACT', TIER, hfl)
    smap2 = node(nt, "ShaderNodeMapping", (-1400, -1100)); smap2.inputs["Scale"].default_value = (2.2, 2.2, 0.12)
    nt.links.new(g.outputs["Position"], smap2.inputs["Vector"])
    st2 = noise_tex(nt, smap2.outputs["Vector"], 2.4, 5, 0.6, 0.3)
    runoff = math_(nt, 'MULTIPLY', map_range(nt, below, 0.3, 2.2, 1.0, 0.0), map_range(nt, st2.outputs["Fac"], 0.42, 0.66, 0.0, 0.55))
    runoff = math_(nt, 'MULTIPLY', runoff, math_(nt, 'SUBTRACT', 1.0, anz))
    col = mix_rgb(nt, col, (0.15, 0.135, 0.11, 1), math_(nt, 'MULTIPLY', runoff, grime), 'MIX')
    # lichen
    up = map_range(nt, NZ, -0.2, 0.9, 0.35, 1.0)
    ln = noise_tex(nt, g.outputs["Position"], 7.5, 4, 0.6, 0.4)
    lic = math_(nt, 'MULTIPLY', map_range(nt, ln.outputs["Fac"], 0.63, 0.67, 0.0, 0.55), up)
    col = mix_rgb(nt, col, (0.36, 0.37, 0.29, 1), math_(nt, 'MULTIPLY', lic, lichen), 'MIX')
    pat = noise_tex(nt, g.outputs["Position"], 0.12, 4, 0.55, 0.5)
    patr = ramp(nt, [(0.3, (0.78, 0.76, 0.74, 1)), (0.5, (0.95, 0.94, 0.92, 1)), (0.7, (1.07, 1.04, 0.98, 1))]); nt.links.new(pat.outputs["Fac"], patr.inputs["Fac"])
    col = mix_rgb(nt, col, patr.outputs["Color"], 1.0, 'MULTIPLY')
    lv = node(nt, "ShaderNodeMapping", (-1400, -800)); lv.inputs["Location"].default_value = (17.3, -4.1, 9.7)
    nt.links.new(g.outputs["Position"], lv.inputs["Vector"])
    lo = noise_tex(nt, lv.outputs["Vector"], 11.0, 3, 0.55, 0.4)
    lic2 = math_(nt, 'MULTIPLY', map_range(nt, lo.outputs["Fac"], 0.67, 0.70, 0.0, 0.6), up)
    col = mix_rgb(nt, col, (0.45, 0.27, 0.10, 1), math_(nt, 'MULTIPLY', lic2, lichen), 'MIX')
    # joints: dark mortar shadow, a little moss near the floors
    jcol = mix_rgb(nt, (0.15, 0.145, 0.13, 1), (0.08, 0.10, 0.05, 1), math_(nt, 'MINIMUM', math_(nt, 'MULTIPLY', gr, 2.0), 1.0))
    col = mix_rgb(nt, col, jcol, math_(nt, 'MULTIPLY', joint, joint_k), 'MIX')
    aor = ramp(nt, [(0.0, (0.45, 0.43, 0.40, 1)), (1.0, (1, 1, 1, 1))]); nt.links.new(ao_mask(nt, 0.6), aor.inputs["Fac"])
    col = mix_rgb(nt, col, aor.outputs["Color"], 1.0, 'MULTIPLY')
    nt.links.new(col, b.inputs["Base Color"])
    rr = math_(nt, 'MULTIPLY_ADD', fine.outputs["Fac"], 0.12, rough - 0.06)
    rr = math_(nt, 'MAXIMUM', rr, math_(nt, 'MULTIPLY', math_(nt, 'MAXIMUM', joint, lic), 0.96))
    nt.links.new(rr, b.inputs["Roughness"])
    h = math_(nt, 'MULTIPLY_ADD', fine.outputs["Fac"], 0.25, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, joint), 0.7))
    h = math_(nt, 'MULTIPLY_ADD', mott.outputs["Fac"], 0.15, h)
    bump_from(nt, b, h, 0.4, 0.008)
    return m

def paving_mat(name, cols=((0.24, 0.21, 0.17), (0.35, 0.315, 0.26), (0.44, 0.40, 0.33)), row=0.72, blen=(0.65, 1.30)):
    """Worn limestone flags in courses along X, each flag its own tone; joints full of dust and a little moss;
    grime and green gathering where the AO says corners and wall-feet are; hairline cracks; worn smooth patches."""
    m, nt, b = new_mat(name)
    g, P, N = geo(nt)
    X, Y, Z = P[0], P[1], P[2]
    yc = math_(nt, 'DIVIDE', Y, row)
    k = math_(nt, 'FLOOR', yc); fy = math_(nt, 'FRACT', yc)
    off = math_(nt, 'MULTIPLY', wnoise1(nt, math_(nt, 'ADD', k, 5.0)), 2.3)
    L = math_(nt, 'MULTIPLY_ADD', wnoise1(nt, math_(nt, 'ADD', k, 91.0)), blen[1] - blen[0], blen[0])
    ub = math_(nt, 'DIVIDE', math_(nt, 'ADD', X, off), L)
    bi = math_(nt, 'FLOOR', ub); fu = math_(nt, 'FRACT', ub)
    dy = math_(nt, 'MULTIPLY', math_(nt, 'MINIMUM', fy, math_(nt, 'SUBTRACT', 1.0, fy)), row)
    dx = math_(nt, 'MULTIPLY', math_(nt, 'MINIMUM', fu, math_(nt, 'SUBTRACT', 1.0, fu)), L)
    jn = noise_tex(nt, g.outputs["Position"], 9.0, 3, 0.5)
    jw = math_(nt, 'MULTIPLY_ADD', jn.outputs["Fac"], 0.008, 0.002)
    joint = math_(nt, 'SUBTRACT', 1.0, map_range(nt, math_(nt, 'SUBTRACT', math_(nt, 'MINIMUM', dx, dy), jw), 0.0, 0.005, 0.0, 1.0))
    wb = node(nt, "ShaderNodeTexWhiteNoise", (-1200, 600), noise_dimensions='3D'); nt.links.new(combine(nt, bi, k, Z), wb.inputs["Vector"])
    mott = noise_tex(nt, g.outputs["Position"], 1.1, 8, 0.62, 0.2)
    fine = noise_tex(nt, g.outputs["Position"], 22.0, 5, 0.6)
    t2 = math_(nt, 'MULTIPLY_ADD', wb.outputs["Value"], 0.5, math_(nt, 'MULTIPLY', mott.outputs["Fac"], 0.5))
    r = ramp(nt, [(0.25, c4(cols[0])), (0.5, c4(cols[1])), (0.75, c4(cols[2]))]); nt.links.new(t2, r.inputs["Fac"])
    fr = ramp(nt, [(0.3, (0.9, 0.9, 0.9, 1)), (0.7, (1.06, 1.05, 1.03, 1))]); nt.links.new(fine.outputs["Fac"], fr.inputs["Fac"])
    col = mix_rgb(nt, r.outputs["Color"], fr.outputs["Color"], 1.0, 'MULTIPLY')
    # worn patches: paler and smoother where feet have gone
    wn_ = noise_tex(nt, g.outputs["Position"], 0.35, 3, 0.5)
    wear = map_range(nt, wn_.outputs["Fac"], 0.5, 0.7, 0.0, 0.35)
    col = mix_rgb(nt, col, (0.47, 0.43, 0.36, 1), wear, 'MIX')
    # hairline cracks
    vw = noise_tex(nt, g.outputs["Position"], 1.5, 2, 0.5, loc=(-1400, -900))
    wv = node(nt, "ShaderNodeMix", (-1200, -900), data_type='VECTOR'); wv.inputs["Factor"].default_value = 0.3
    nt.links.new(g.outputs["Position"], wv.inputs[4]); nt.links.new(vw.outputs["Color"], wv.inputs[5])
    vo = node(nt, "ShaderNodeTexVoronoi", (-1000, -900), feature='DISTANCE_TO_EDGE'); vo.inputs["Scale"].default_value = 1.4
    nt.links.new(wv.outputs[1], vo.inputs["Vector"])
    cmask = map_range(nt, noise_tex(nt, g.outputs["Position"], 0.6, 2, 0.5).outputs["Fac"], 0.55, 0.62, 0.0, 1.0)
    crack = math_(nt, 'MULTIPLY', map_range(nt, vo.outputs["Distance"], 0.0, 0.006, 0.8, 0.0), cmask)
    # grime in the corners and at the wall feet (AO), lichen spots
    grime = map_range(nt, ao_mask(nt, 0.7), 0.55, 1.0, 1.0, 0.0)
    gnz = noise_tex(nt, g.outputs["Position"], 2.5, 4, 0.6)
    grime = math_(nt, 'MULTIPLY', grime, map_range(nt, gnz.outputs["Fac"], 0.3, 0.7, 0.45, 1.0))
    col = mix_rgb(nt, col, (0.17, 0.165, 0.12, 1), grime, 'MIX')
    ln = noise_tex(nt, g.outputs["Position"], 6.0, 3, 0.55, 0.4)
    lic = map_range(nt, ln.outputs["Fac"], 0.65, 0.68, 0.0, 0.45)
    col = mix_rgb(nt, col, (0.38, 0.39, 0.32, 1), lic, 'MIX')
    jcol = mix_rgb(nt, (0.15, 0.14, 0.12, 1), (0.10, 0.12, 0.06, 1), map_range(nt, gnz.outputs["Fac"], 0.45, 0.6, 0.0, 1.0))
    col = mix_rgb(nt, col, jcol, math_(nt, 'MULTIPLY', math_(nt, 'MAXIMUM', joint, crack), 0.85), 'MIX')
    aor = ramp(nt, [(0.0, (0.5, 0.48, 0.45, 1)), (1.0, (1, 1, 1, 1))]); nt.links.new(ao_mask(nt, 0.35, (-600, -1200)), aor.inputs["Fac"])
    col = mix_rgb(nt, col, aor.outputs["Color"], 1.0, 'MULTIPLY')
    nt.links.new(col, b.inputs["Base Color"])
    rr = math_(nt, 'MULTIPLY_ADD', fine.outputs["Fac"], 0.1, math_(nt, 'SUBTRACT', 0.86, math_(nt, 'MULTIPLY', wear, 0.5)))
    nt.links.new(math_(nt, 'MAXIMUM', rr, math_(nt, 'MULTIPLY', joint, 0.97)), b.inputs["Roughness"])
    h = math_(nt, 'MULTIPLY_ADD', fine.outputs["Fac"], 0.2, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, math_(nt, 'MAXIMUM', joint, crack)), 0.7))
    bump_from(nt, b, h, 0.45, 0.006)
    return m

def adamant_mat(name="M_Adamant"):
    """The adamant: a dark, dense, diamond-hard plate, smoothed almost to a polish, with faint cloudy depth, a fine
    crystalline sparkle and pale mineral streaks washed down from the ledge."""
    m, nt, b = new_mat(name)
    g, P, N = geo(nt)
    big = noise_tex(nt, g.outputs["Position"], 0.06, 6, 0.6, 0.4)
    mid = noise_tex(nt, g.outputs["Position"], 0.9, 6, 0.55)
    vo = node(nt, "ShaderNodeTexVoronoi", (-1000, -300)); vo.inputs["Scale"].default_value = 26.0
    nt.links.new(g.outputs["Position"], vo.inputs["Vector"])
    t = math_(nt, 'MULTIPLY_ADD', big.outputs["Fac"], 0.6, math_(nt, 'MULTIPLY', mid.outputs["Fac"], 0.4))
    r = ramp(nt, [(0.3, (0.030, 0.034, 0.042, 1)), (0.5, (0.062, 0.068, 0.082, 1)), (0.72, (0.11, 0.115, 0.13, 1))]); nt.links.new(t, r.inputs["Fac"])
    spk = ramp(nt, [(0.0, (0.9, 0.9, 0.92, 1)), (1.0, (1.12, 1.12, 1.15, 1))]); nt.links.new(vo.outputs["Color"], spk.inputs["Fac"])
    col = mix_rgb(nt, r.outputs["Color"], spk.outputs["Color"], 1.0, 'MULTIPLY')
    smap = node(nt, "ShaderNodeMapping", (-1400, -600)); smap.inputs["Scale"].default_value = (3.0, 3.0, 0.06)
    nt.links.new(g.outputs["Position"], smap.inputs["Vector"])
    st = noise_tex(nt, smap.outputs["Vector"], 2.0, 5, 0.55)
    streak = map_range(nt, st.outputs["Fac"], 0.55, 0.75, 0.0, 0.45)
    col = mix_rgb(nt, col, (0.20, 0.205, 0.21, 1), streak, 'MIX')
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(map_range(nt, mid.outputs["Fac"], 0.3, 0.7, 0.16, 0.34), b.inputs["Roughness"])
    b.inputs["Specular IOR Level"].default_value = 0.7
    bump_from(nt, b, mid.outputs["Fac"], 0.08, 0.02)
    return m

def noisy(name, colors, scale=8.0, rough=0.8, bump=0.2, bump_dist=0.003, detail=6.0, stretch=(1, 1, 1), sheen=0.0, sss=0.0,
          coat=0.0, metallic=0.0, warp=0.0, ao=0.0):
    """Generic organic surface: a colour ramp over fractal noise in world space, with bump."""
    m, nt, b = new_mat(name)
    g = node(nt, "ShaderNodeNewGeometry", (-1600, 0)); mp = node(nt, "ShaderNodeMapping", (-1400, 0)); mp.inputs["Scale"].default_value = stretch
    nt.links.new(g.outputs["Position"], mp.inputs["Vector"])
    n = noise_tex(nt, mp.outputs["Vector"], scale, detail, 0.6, warp)
    stops = [(i / max(1, len(colors) - 1) * 0.6 + 0.2, c4(c)) for i, c in enumerate(colors)]
    r = ramp(nt, stops, (-700, 0)); nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    col = r.outputs["Color"]
    if ao:
        aor = ramp(nt, [(0.0, (1 - ao, 1 - ao, 1 - ao, 1)), (1.0, (1, 1, 1, 1))]); nt.links.new(ao_mask(nt, 0.3), aor.inputs["Fac"])
        col = mix_rgb(nt, col, aor.outputs["Color"], 1.0, 'MULTIPLY')
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if sheen: b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.4
    if sss: b.inputs["Subsurface Weight"].default_value = sss; b.inputs["Subsurface Radius"].default_value = (0.3, 0.4, 0.12)
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.1
    if bump:
        fine = noise_tex(nt, mp.outputs["Vector"], scale * 6, 4, loc=(-1000, -350))
        bump_from(nt, b, fine.outputs["Fac"], bump, bump_dist)
    return m

def leaves_mat(name, tint, light, scale=14.0, sss=0.12, rough=0.5, ao=0.55):
    """Evergreen leaves: voronoi cells give leaf-to-leaf tone, larger noise gives sun-faded and young growth,
    AO darkens the inside of the crown."""
    m, nt, b = new_mat(name)
    g = node(nt, "ShaderNodeNewGeometry", (-1400, 0))
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 200)); v.inputs["Scale"].default_value = scale
    nt.links.new(g.outputs["Position"], v.inputs["Vector"])
    n = noise_tex(nt, g.outputs["Position"], 1.4, 3)
    mx = node(nt, "ShaderNodeMix", (-700, 150), data_type='FLOAT'); mx.inputs["Factor"].default_value = 0.5
    nt.links.new(v.outputs["Color"], mx.inputs[2]); nt.links.new(n.outputs["Fac"], mx.inputs[3])
    r = ramp(nt, [(0.2, c4(tuple(x * 0.55 for x in tint))), (0.5, c4(tint)), (0.82, c4(light))], (-450, 150))
    nt.links.new(mx.outputs[0], r.inputs["Fac"])
    aor = ramp(nt, [(0.0, (1 - ao, 1 - ao * 0.95, 1 - ao, 1)), (1.0, (1, 1, 1, 1))]); nt.links.new(ao_mask(nt, 0.35), aor.inputs["Fac"])
    nt.links.new(mix_rgb(nt, r.outputs["Color"], aor.outputs["Color"], 1.0, 'MULTIPLY'), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Subsurface Weight"].default_value = sss; b.inputs["Subsurface Radius"].default_value = (0.2, 0.4, 0.1)
    b.inputs["Sheen Weight"].default_value = 0.15
    return m

def bark_mat(name, crack_col=(0.04, 0.035, 0.028), mid=(0.17, 0.15, 0.12), top=(0.30, 0.27, 0.22), stretch=(9, 9, 0.7)):
    m, nt, b = new_mat(name)
    g = node(nt, "ShaderNodeNewGeometry", (-1600, 0)); mp = node(nt, "ShaderNodeMapping", (-1400, 0)); mp.inputs["Scale"].default_value = stretch
    nt.links.new(g.outputs["Position"], mp.inputs["Vector"])
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 200), feature='DISTANCE_TO_EDGE'); v.inputs["Scale"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    n = noise_tex(nt, mp.outputs["Vector"], 6, 8, 0.6, 1.5, (-1000, -150))
    crack = ramp(nt, [(0.0, c4(crack_col)), (0.06, c4(mid)), (0.3, c4(top))], (-700, 200)); nt.links.new(v.outputs["Distance"], crack.inputs["Fac"])
    lich = ramp(nt, [(0.55, (1, 1, 1, 1)), (0.75, (0.75, 0.8, 0.7, 1))], (-700, -150)); nt.links.new(n.outputs["Fac"], lich.inputs["Fac"])
    nt.links.new(mix_rgb(nt, crack.outputs["Color"], lich.outputs["Color"], 0.8, 'MULTIPLY'), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
    h = math_(nt, 'MULTIPLY_ADD', v.outputs["Distance"], 0.6, n.outputs["Fac"])
    bump_from(nt, b, h, 0.8, 0.01)
    return m

def grass_mat(name="M_Grass"):
    """Wiry grass in the joints: dark at the root, sun-dried straw at the tips (height above the gallery floor)."""
    m, nt, b = new_mat(name)
    g, P, N = geo(nt)
    hfl = math_(nt, 'MULTIPLY', math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', P[2], 0.03), TIER)), TIER)
    zr = map_range(nt, hfl, 0.0, 0.35, 0.0, 1.0)
    n = noise_tex(nt, g.outputs["Position"], 2.0, 3)
    fz = math_(nt, 'ADD', zr, math_(nt, 'MULTIPLY_ADD', n.outputs["Fac"], 0.5, -0.25))
    r = ramp(nt, [(0.0, (0.05, 0.06, 0.03, 1)), (0.35, (0.16, 0.20, 0.08, 1)), (0.75, (0.36, 0.36, 0.20, 1)), (1.0, (0.50, 0.46, 0.30, 1))])
    nt.links.new(fz, r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.8; b.inputs["Sheen Weight"].default_value = 0.25
    b.inputs["Subsurface Weight"].default_value = 0.08
    return m

def plain(name, color, rough=0.5, metallic=0.0, emission=None, strength=0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = c4(color); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if emission: b.inputs["Emission Color"].default_value = c4(emission); b.inputs["Emission Strength"].default_value = strength
    return m

def iron_mat(name="M_Iron"):
    """Wrought iron left out in the weather: blackened, with rust blooming at the edges."""
    m, nt, b = new_mat(name)
    g = node(nt, "ShaderNodeNewGeometry", (-1400, 0))
    n = noise_tex(nt, g.outputs["Position"], 6.0, 10, 0.68, 0.6)
    r = ramp(nt, [(0.35, (0.025, 0.024, 0.023, 1)), (0.52, (0.05, 0.045, 0.04, 1)), (0.60, (0.17, 0.08, 0.035, 1)), (0.72, (0.33, 0.16, 0.06, 1))])
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(map_range(nt, n.outputs["Fac"], 0.5, 0.62, 0.45, 0.88), b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = 0.55
    fine = noise_tex(nt, g.outputs["Position"], 80.0, 5)
    bump_from(nt, b, fine.outputs["Fac"], 0.4, 0.002)
    return m

def brass_mat(name="M_Brass"):
    """Old instrument brass: warm metal, dulled, with darker tarnish in the hollows and where hands don't reach."""
    m, nt, b = new_mat(name)
    g = node(nt, "ShaderNodeNewGeometry", (-1400, 0))
    n = noise_tex(nt, g.outputs["Position"], 9.0, 8, 0.6)
    r = ramp(nt, [(0.35, (0.16, 0.11, 0.05, 1)), (0.55, (0.36, 0.26, 0.13, 1)), (0.75, (0.46, 0.36, 0.20, 1))])
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    aor = ramp(nt, [(0.0, (0.35, 0.33, 0.3, 1)), (1.0, (1, 1, 1, 1))]); nt.links.new(ao_mask(nt, 0.08), aor.inputs["Fac"])
    nt.links.new(mix_rgb(nt, r.outputs["Color"], aor.outputs["Color"], 1.0, 'MULTIPLY'), b.inputs["Base Color"])
    nt.links.new(map_range(nt, n.outputs["Fac"], 0.3, 0.7, 0.55, 0.36), b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = 1.0
    return m

# ----------------------------------------------------------------------------- materials
M_STONE_NEAR = stone_mat("M_StoneNear")
M_STONE = stone_mat("M_Stone")
M_STONE_FAR = stone_mat("M_StoneFar", course=0.55, blen=(1.0, 1.9), joint_k=0.45, tone_k=0.3)
M_BALUSTER = stone_mat("M_Balusters", cols=((0.28, 0.245, 0.19), (0.41, 0.365, 0.29), (0.50, 0.45, 0.37)), lichen=0.6, grime=0.6, ashlar=False)
M_PAVE_NEAR = paving_mat("M_PavingNear")
M_PAVE = paving_mat("M_Paving")
M_ADAMANT = adamant_mat()
M_IRON = iron_mat()
M_BRASS = brass_mat()
M_WOOD = noisy("M_Wood", [(0.16, 0.14, 0.11), (0.27, 0.24, 0.19), (0.36, 0.33, 0.27)], scale=3, stretch=(1, 1, 12), rough=0.85, bump=0.3, bump_dist=0.002)
M_SOIL = noisy("M_Soil", [(0.05, 0.04, 0.03), (0.10, 0.08, 0.06), (0.16, 0.13, 0.10)], scale=14, rough=0.95, bump=0.6, bump_dist=0.005)
M_GARDEN = noisy("M_Garden", [(0.06, 0.08, 0.035), (0.12, 0.14, 0.06), (0.20, 0.19, 0.10)], scale=0.6, rough=0.95, bump=0.3, bump_dist=0.02)
M_LEAVES = leaves_mat("M_Leaves", (0.07, 0.12, 0.04), (0.17, 0.24, 0.08), scale=30, rough=0.42)        # myrtle and orange tree
M_WALLPLANT = leaves_mat("M_WallPlants", (0.13, 0.17, 0.10), (0.26, 0.31, 0.19), scale=40, rough=0.6, ao=0.3)  # valerian, glaucous
M_TREES = leaves_mat("M_TreeFoliage", (0.05, 0.085, 0.035), (0.13, 0.17, 0.07), scale=6, rough=0.6, ao=0.6)  # garden trees on the top
M_BARK = bark_mat("M_Bark")
M_GRASS = grass_mat()
M_FLOWERS = noisy("M_Flowers", [(0.45, 0.08, 0.12), (0.62, 0.17, 0.22), (0.72, 0.30, 0.34)], scale=40, rough=0.6, bump=0.0, sss=0.1)
M_FRUIT = noisy("M_Fruit", [(0.55, 0.20, 0.02), (0.70, 0.32, 0.04)], scale=30, rough=0.4, bump=0.1, bump_dist=0.001)
M_LITTER = noisy("M_Litter", [(0.12, 0.09, 0.05), (0.25, 0.18, 0.09), (0.36, 0.30, 0.16)], scale=25, rough=0.9, bump=0.0)
M_DARK = noisy("M_Doorways", [(0.010, 0.010, 0.010), (0.025, 0.023, 0.021)], scale=2, rough=0.95, bump=0.0)

# ----------------------------------------------------------------------------- geometry helpers
def _obj(name, bm, mat, smooth=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return link(o)

def _label(n):
    a = max(range(3), key=lambda i: abs(n[i]))
    return ("+" if n[a] > 0 else "-") + "xyz"[a]

def bbox(name, size, loc, mat, rot=(0, 0, 0), keep=None, drop=None, bevel=0.0):
    """A box (bmesh, fast). keep: labels of faces to keep ('+x', '-y', ...); drop: labels to delete."""
    bm = bmesh.new()
    M = Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((size[0], size[1], size[2], 1))
    bmesh.ops.create_cube(bm, size=1.0, matrix=M)
    bm.normal_update()
    if keep is not None or drop is not None:
        dead = [f for f in bm.faces if (keep is not None and _label(f.normal) not in keep) or (drop is not None and _label(f.normal) in drop)]
        bmesh.ops.delete(bm, geom=dead, context='FACES')
    o = _obj(name, bm, mat)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = 1; md.limit_method = 'ANGLE'
    return o

def slab(name, xr, yr, zr, mat, **kw):
    return bbox(name, (xr[1] - xr[0], yr[1] - yr[0], zr[1] - zr[0]), ((xr[0] + xr[1]) / 2, (yr[0] + yr[1]) / 2, (zr[0] + zr[1]) / 2), mat, **kw)

def seg_box(name, p0, p1, w, z0, z1, mat, off=0.0, ext=0.0, **kw):
    """A box along the 2D segment p0->p1, w wide, offset `off` to the segment's right (outward), extended by ext."""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; L = d.length; dn = d / L; rn = Vector((dn.y, -dn.x))
    c = (p0 + p1) / 2 + rn * off
    return bbox(name, (L + 2 * ext, w, z1 - z0), (c.x, c.y, (z0 + z1) / 2), mat, rot=(0, 0, math.atan2(d.y, d.x)), **kw)

def prism(name, pts, plane, a0, a1, mat, keep_caps=True):
    """A 2D polygon extruded: plane 'xz' (pts are (x, z), extruded along y from a0 to a1), 'yz' (along x), 'xy' (along z)."""
    def P(u, v, a):
        if plane == 'xz': return (u, a, v)
        if plane == 'yz': return (a, u, v)
        return (u, v, a)
    bm = bmesh.new()
    A = [bm.verts.new(P(u, v, a0)) for u, v in pts]; B = [bm.verts.new(P(u, v, a1)) for u, v in pts]
    if keep_caps:
        bm.faces.new(A); bm.faces.new(list(reversed(B)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((A[i], A[j], B[j], B[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat)

def lathe(name, profile, loc, mat, steps=12, rot=(0, 0, 0), wobble=0.0, seed=0.0):
    """profile: (radius, z) bottom to top, revolved around Z; optional noise wobble on the radius."""
    bm = bmesh.new(); rings = []
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
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4(), verts=bm.verts)
    return _obj(name, bm, mat, smooth=True)

def blob(name, loc, radius, mat, scale=(1, 1, 1), subdiv=1, amp=0.25, freq=1.6, seed=0.0, flat_bottom=None):
    """Lumpy organic clump: icosphere displaced by noise (crown masses, cores of shrubs)."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    for v in bm.verts:
        n = v.co.normalized()
        k = 1.0 + amp * noise.noise(n * freq + Vector((seed, seed * 1.7, seed * 0.3)))
        p = Vector((n.x * radius * k * scale[0], n.y * radius * k * scale[1], n.z * radius * k * scale[2]))
        if flat_bottom is not None: p.z = max(p.z, flat_bottom)
        v.co = p + Vector(loc)
    return _obj(name, bm, mat, smooth=True)

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

def tube(name, pts, radii, mat, sides=6, n=4, bm=None):
    """A tapered tube along a Catmull-Rom path (trunks, branches). With bm given, adds into it."""
    c = catmull(pts, n); rr = [lerp(radii[0], radii[1], i / max(1, len(c) - 1)) for i in range(len(c))]
    own = bm is None
    if own: bm = bmesh.new()
    rings = []; up = Vector((0, 0, 1))
    for i, p in enumerate(c):
        t = (c[min(i + 1, len(c) - 1)] - c[max(i - 1, 0)]).normalized()
        a = t.cross(up if abs(t.dot(up)) < 0.9 else Vector((1, 0, 0))).normalized(); b_ = t.cross(a).normalized()
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / sides) + b_ * math.sin(2 * math.pi * k / sides)) * rr[i]) for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides; bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if own:
        bm.normal_update(); return _obj(name, bm, mat, smooth=True)

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

# ----------------------------------------------------------------------------- parapets and balustrades
BAL_PROFILE = [(0.068, 0.0), (0.05, 0.06), (0.044, 0.12), (0.078, 0.25), (0.072, 0.33), (0.040, 0.47), (0.035, 0.53), (0.058, 0.575), (0.066, 0.62)]
BAL_PROFILE_LO = [(0.066, 0.0), (0.046, 0.10), (0.078, 0.26), (0.040, 0.47), (0.035, 0.53), (0.064, 0.62)]

def die(name, p, z0, mat, w=0.44, h=None):
    h = RAIL_H + 0.04 if h is None else h
    bbox(name, (w, w, h), (p[0], p[1], z0 + h / 2), mat, bevel=0.01, drop={'-z'})
    bbox(name + "Cap", (w + 0.06, w + 0.06, 0.06), (p[0], p[1], z0 + h + 0.03), mat, bevel=0.012, drop={'-z'})

def balustrade(name, p0, p1, z0, mat, bal_mat, near=True, dies=True):
    """Plinth, turned balusters, sub-rail and a broad handrail coping, along the inner face line p0->p1
    (the balustrade lies to the right of the direction of travel, i.e. outward)."""
    p0v, p1v = Vector(p0), Vector(p1); d = p1v - p0v; L = d.length; dn = d / L; rn = Vector((dn.y, -dn.x))
    seg_box(name + "_Plinth", p0, p1, PT + 0.02, z0, z0 + 0.18, mat, off=PT / 2, bevel=0.01, drop={'-z'})
    seg_box(name + "_SubRail", p0, p1, PT - 0.04, z0 + 0.80, z0 + 0.86, mat, off=PT / 2)
    seg_box(name + "_Rail", p0, p1, PT + 0.06, z0 + 0.86, z0 + RAIL_H, mat, off=PT / 2, bevel=0.018)
    prof = BAL_PROFILE if near else BAL_PROFILE_LO
    inset = 0.30 if dies else 0.12
    n = max(1, int((L - 2 * inset) / 0.25) + 1)
    for i in range(n):
        t = inset + (L - 2 * inset) * (i / max(1, n - 1)) if n > 1 else L / 2
        p = p0v + dn * t + rn * (PT / 2)
        lathe(f"{name}_Bal{i}", [(r, z) for r, z in prof], (p.x, p.y, z0 + 0.18), bal_mat, steps=10 if near else 6)
    if dies:
        die(name + "_DieA", tuple(p0v + rn * (PT / 2)), z0, mat); die(name + "_DieB", tuple(p1v + rn * (PT / 2)), z0, mat)

def solid_parapet(name, x0, x1, y_in, z0, mat, die_every=3.6):
    """A solid parapet along x (outward is -y), inner face at y_in: plinth, wall, coping, with dies at intervals."""
    p0, p1 = (x0, y_in), (x1, y_in)
    seg_box(name + "_Plinth", p0, p1, PT + 0.04, z0, z0 + 0.2, mat, off=PT / 2, drop={'-z'})
    seg_box(name + "_Wall", p0, p1, PT - 0.04, z0 + 0.2, z0 + 0.86, mat, off=PT / 2)
    seg_box(name + "_Rail", p0, p1, PT + 0.08, z0 + 0.86, z0 + RAIL_H, mat, off=PT / 2, bevel=0.018)
    n = max(1, int(round((x1 - x0) / die_every)))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        if abs(x) >= HX - 0.1: continue
        die(f"{name}_Die{i}", (x, y_in - PT / 2), z0, mat, w=0.42)

def parapet_run(name, y_in, z0, mat, gaps=(), bal=(), bal_mat=None, near=False):
    """Parapet along the whole bay (x -HX..HX) with gaps (stair openings) and balustraded stretches."""
    cuts = sorted(set([-HX, HX] + [g for gap in gaps for g in gap] + [b for bb in bal for b in bb]))
    for i, (a, b_) in enumerate(zip(cuts, cuts[1:])):
        mid = (a + b_) / 2
        if any(g0 < mid < g1 for g0, g1 in gaps): continue
        if any(b0 < mid < b1 for b0, b1 in bal): balustrade(f"{name}_B{i}", (a, y_in), (b_, y_in), z0, mat, bal_mat, near=near)
        else: solid_parapet(f"{name}_S{i}", a, b_, y_in, z0, mat)

def offset_poly(pts, d):
    """Offset an open polyline to its right by d (mitred)."""
    lines = []
    for p0, p1 in zip(pts, pts[1:]):
        p0, p1 = Vector(p0), Vector(p1); dn = (p1 - p0).normalized(); rn = Vector((dn.y, -dn.x))
        lines.append((p0 + rn * d, dn))
    out = [tuple(lines[0][0])]
    for (a, da), (b_, db) in zip(lines, lines[1:]):
        # intersect a + s*da with b_ + t*db
        den = da.x * db.y - da.y * db.x
        s = ((b_.x - a.x) * db.y - (b_.y - a.y) * db.x) / den
        out.append(tuple(a + da * s))
    last_p0, last_d = lines[-1]
    L = (Vector(pts[-1]) - Vector(pts[-2])).length
    out.append(tuple(last_p0 + last_d * L))
    return out

# ----------------------------------------------------------------------------- the galleries
# floors (paving slabs: top and front edge only, the front edge is covered by the cornice)
def floor_slab(name, xr, yr, ztop, mat):
    return slab(name, xr, yr, (ztop - 0.3, ztop), mat, keep={'+z', '-y'})

def cornice(name, xr, y_face, ztop, mat):
    """Moulded band under each parapet, covering the floor slab's edge."""
    slab(name, xr, (y_face - 0.09, y_face + 0.02), (ztop - 0.34, ztop), mat, drop={'+y'}, bevel=0.02)
    slab(name + "Lo", xr, (y_face - 0.05, y_face + 0.02), (ztop - 0.44, ztop - 0.34), mat, keep={'-y', '-z'})

def wall_face(name, xr, y, zr, mat):
    """The visible face of a gallery's supporting wall (facing -y, outward)."""
    return slab(name, xr, (y, y + 0.5), zr, mat, keep={'-y'})

# the reader's gallery (tier 0) and its belvedere
NEAR_X = 8.0
floor_slab("Pave_G0_Near", (-NEAR_X, NEAR_X), (G0_EDGE, G0_BACK), 0.0, M_PAVE_NEAR)
floor_slab("Pave_G0_R", (-HX, -NEAR_X), (G0_EDGE, G0_BACK), 0.0, M_PAVE)
floor_slab("Pave_G0_L", (NEAR_X, HX), (G0_EDGE, G0_BACK), 0.0, M_PAVE)
BAY_OUT = offset_poly(BAY_IN, PT)                                 # outer face of the belvedere balustrade
# clip the polygon's first/last points to the gallery edge line
def _at_y(p0, p1, y):
    t = (y - p0[1]) / (p1[1] - p0[1]); return (p0[0] + (p1[0] - p0[0]) * t, y)
BAY_FOOT = [_at_y(BAY_OUT[0], BAY_OUT[1], G0_EDGE)] + BAY_OUT[1:-1] + [_at_y(BAY_OUT[-2], BAY_OUT[-1], G0_EDGE)]
prism("Pave_Bay", [(p[0], p[1]) for p in BAY_FOOT] + [(BAY_FOOT[-1][0], G0_EDGE + 0.3), (BAY_FOOT[0][0], G0_EDGE + 0.3)], 'xy', -0.3, 0.0, M_PAVE_NEAR)
# the belvedere pier: a half-octagonal buttress carried down to the gallery below
pier = [(BAY_FOOT[0][0], G0_EDGE + 0.2)] + [(p[0], p[1]) for p in BAY_FOOT] + [(BAY_FOOT[-1][0], G0_EDGE + 0.2)]
prism("BayPier", pier, 'xy', -TIER - 0.02, -0.30, M_STONE, keep_caps=False)
band = offset_poly([(BAY_FOOT[0][0] - 0.12, G0_EDGE)] + BAY_FOOT[1:-1] + [(BAY_FOOT[-1][0] + 0.12, G0_EDGE)], 0.09)
prism("BayCornice", [(BAY_FOOT[0][0] - 0.1, G0_EDGE + 0.1)] + band + [(BAY_FOOT[-1][0] + 0.1, G0_EDGE + 0.1)], 'xy', -0.34, -0.0, M_STONE_NEAR)
band2 = offset_poly([(BAY_FOOT[0][0] - 0.1, G0_EDGE)] + BAY_FOOT[1:-1] + [(BAY_FOOT[-1][0] + 0.1, G0_EDGE)], 0.05)
prism("BayCorniceLo", [(BAY_FOOT[0][0] - 0.1, G0_EDGE + 0.1)] + band2 + [(BAY_FOOT[-1][0] + 0.1, G0_EDGE + 0.1)], 'xy', -0.46, -0.34, M_STONE)
# corbels under the belvedere's cornice
for i, (p0, p1) in enumerate(zip(BAY_FOOT, BAY_FOOT[1:])):
    p0v, p1v = Vector(p0), Vector(p1); d = p1v - p0v; L = d.length; dn = d / L; rn = Vector((dn.y, -dn.x))
    nk = max(1, int(L / 0.7))
    for k in range(nk):
        p = p0v + dn * (L * (k + 0.5) / nk) + rn * 0.05
        bbox(f"BayCorbel{i}_{k}", (0.16, 0.12, 0.30), (p.x, p.y, -0.62), M_STONE, rot=(0, 0, math.atan2(d.y, d.x)), drop={'+z'})
# the belvedere balustrade (near: full turned balusters)
for i, (p0, p1) in enumerate(zip(BAY_IN, BAY_IN[1:])):
    balustrade(f"BayBal{i}", p0, p1, 0.0, M_STONE_NEAR, M_BALUSTER, near=True, dies=(i == 1))
# gallery parapet: balustrade near the belvedere, solid beyond; the stair-down opening on the right
G0_IN = G0_EDGE + PT
STAIR_A = (-17.4, -16.0)                    # opening for the stair down to tier -1 (on the reader's right)
parapet_run("ParG0", G0_IN, 0.0, M_STONE, gaps=[(-2.8, 2.8), STAIR_A], bal=[(-7.0, -2.8), (2.8, 7.0)], bal_mat=M_BALUSTER, near=False)
for s in (-1, 1):
    die(f"BayCornerDie{s}", (s * 2.8, G0_IN - PT / 2), 0.0, M_STONE_NEAR, w=0.48)
cornice("CorG0", (-HX, HX), G0_EDGE, 0.0, M_STONE)

# the gallery's back wall (tier +1's support): a blind arcade of pilasters and voussoir arches, a bench
wall_face("WallG0Back", (-HX, HX), G0_BACK, (0.0, TIER - 0.32), M_STONE)
slab("CorG0Back", (-HX, HX), (G0_BACK - 0.12, G0_BACK), (TIER - 0.62, TIER - 0.32), M_STONE, drop={'+y'}, bevel=0.02)
STAIR_UP = (5.2, 14.7)                      # stair to tier +1 against the back wall (reader's left, behind)
def arch_band(name, cx, y_face, zc, r0, r1, depth, mat, seg=16):
    """A semicircular moulded arch standing proud of a wall that faces -y."""
    bm = bmesh.new(); fr, bk = [], []
    for k in range(seg + 1):
        a = math.pi * k / seg; c, s_ = math.cos(a), math.sin(a)
        fr.append((bm.verts.new((cx + r0 * c, y_face - depth, zc + r0 * s_)), bm.verts.new((cx + r1 * c, y_face - depth, zc + r1 * s_))))
        bk.append((bm.verts.new((cx + r0 * c, y_face, zc + r0 * s_)), bm.verts.new((cx + r1 * c, y_face, zc + r1 * s_))))
    for k in range(seg):
        bm.faces.new((fr[k][0], fr[k][1], fr[k + 1][1], fr[k + 1][0]))
        bm.faces.new((bk[k][1], fr[k][1], fr[k + 1][1], bk[k + 1][1])[::-1])
        bm.faces.new((bk[k][0], fr[k][0], fr[k + 1][0], bk[k + 1][0]))
    bm.normal_update()
    for f_ in bm.faces:
        cc = f_.calc_center_median()
        if f_.normal.y > 0.5 or (abs(f_.normal.y) < 0.5 and f_.normal.dot(cc - Vector((cx, cc.y, zc))) * (1 if (cc - Vector((cx, cc.y, zc))).length > (r0 + r1) / 2 else -1) < 0):
            f_.normal_flip()
    return _obj(name, bm, mat, smooth=False)

def arcade(name, y_face, z0, xs, mat, h=3.55, arch=True):
    for i, x in enumerate(xs):
        if STAIR_UP[0] - 0.4 < x < STAIR_UP[1] + 0.4 and z0 == 0.0: continue
        slab(f"{name}_Pil{i}", (x - 0.25, x + 0.25), (y_face - 0.14, y_face), (z0, z0 + h), mat, drop={'+y', '-z'})
        slab(f"{name}_PilBase{i}", (x - 0.31, x + 0.31), (y_face - 0.19, y_face), (z0, z0 + 0.32), mat, drop={'+y', '-z'}, bevel=0.015)
        slab(f"{name}_PilCap{i}", (x - 0.31, x + 0.31), (y_face - 0.19, y_face), (z0 + 1.82, z0 + 1.98), mat, drop={'+y'}, bevel=0.015)
    if not arch: return
    for i, (xa, xb) in enumerate(zip(xs, xs[1:])):
        cx = (xa + xb) / 2
        if STAIR_UP[0] - 2.0 < cx < STAIR_UP[1] + 2.0 and z0 == 0.0: continue
        R0 = (xb - xa) / 2 - 0.25; zc = z0 + 1.98
        arch_band(f"{name}_Arch{i}", cx, y_face, zc, R0, R0 + 0.30, 0.13, mat)
        bbox(f"{name}_Key{i}", (0.24, 0.17, 0.42), (cx, y_face - 0.085, zc + R0 + 0.17), mat, drop={'+y'}, bevel=0.01)
arcade("ArcG0", G0_BACK, 0.0, [-26.0 + 4.0 * i for i in range(14)], M_STONE)
# a stone bench in the arcade behind the reader
slab("Bench_Seat", (-1.15, 1.15), (G0_BACK - 0.46, G0_BACK), (0.40, 0.48), M_STONE_NEAR, bevel=0.015, drop={'+y'})
for s in (-1, 1):
    slab(f"Bench_Leg{s}", (s * 0.85 - 0.12, s * 0.85 + 0.12), (G0_BACK - 0.40, G0_BACK), (0.0, 0.40), M_STONE_NEAR, drop={'+y', '-z'})

# tier +1 and tier +2 behind and above, and the island's top
T1_Y = G0_BACK; T2_Y = G0_BACK + 4.0; TOP_Y = G0_BACK + 8.0
floor_slab("Pave_T1", (-HX, HX), (T1_Y, T2_Y), TIER, M_PAVE)
parapet_run("ParT1", T1_Y + PT, TIER, M_STONE, gaps=[(12.7, 14.4)], bal=[(-4.6, 4.6)], bal_mat=M_BALUSTER, near=False)
wall_face("WallT1Back", (-HX, HX), T2_Y, (TIER, 2 * TIER - 0.32), M_STONE_FAR)
slab("CorT1Back", (-HX, HX), (T2_Y - 0.12, T2_Y), (2 * TIER - 0.62, 2 * TIER - 0.32), M_STONE_FAR, drop={'+y'}, bevel=0.02)
arcade("ArcT1", T2_Y, TIER, [-26.0 + 4.0 * i for i in range(14)], M_STONE_FAR, arch=False)
floor_slab("Pave_T2", (-HX, HX), (T2_Y, TOP_Y), 2 * TIER, M_PAVE)
parapet_run("ParT2", T2_Y + PT, 2 * TIER, M_STONE_FAR, gaps=[(-15.4, -13.7)])
wall_face("WallT2Back", (-HX, HX), TOP_Y, (2 * TIER, 3 * TIER - 0.32), M_STONE_FAR)
slab("CorT2Back", (-HX, HX), (TOP_Y - 0.12, TOP_Y), (3 * TIER - 0.62, 3 * TIER - 0.32), M_STONE_FAR, drop={'+y'}, bevel=0.02)
parapet_run("ParTop", TOP_Y + PT, 3 * TIER, M_STONE_FAR)

# the galleries below: tier -1 and the lowest gallery (tier -2)
wall_face("WallG0", (-HX, HX), G0_EDGE, (-TIER, -0.44), M_STONE)
floor_slab("Pave_Tm1", (-HX, HX), (T1_EDGE, G0_EDGE), -TIER, M_PAVE)
STAIR_B = (7.6, 9.0)                        # opening for the stair from tier -1 down to the lowest gallery (left)
parapet_run("ParTm1", T1_EDGE + PT, -TIER, M_STONE, gaps=[STAIR_B])
cornice("CorTm1", (-HX, HX), T1_EDGE, -TIER, M_STONE)
wall_face("WallTm1", (-HX, HX), T1_EDGE, (-2 * TIER, -TIER - 0.44), M_STONE)
floor_slab("Pave_Tm2", (-HX, HX), (T2_EDGE, T1_EDGE), -2 * TIER, M_PAVE)
parapet_run("ParTm2", T2_EDGE + PT, -2 * TIER, M_STONE)
slab("CorTm2", (-HX, HX), (T2_EDGE - 0.06, T2_EDGE + 0.02), (-2 * TIER - 0.3, -2 * TIER), M_STONE, keep={'-y', '-z'})
arcade("ArcTm1", G0_EDGE, -TIER, [-26.0 + 4.0 * i for i in range(14) if abs(-26.0 + 4.0 * i) > 3.5], M_STONE, h=3.6, arch=False)

# the adamant: the island's plate, its verge a ledge beyond the lowest gallery, its face plunging and curving under
ADZ = -2 * TIER - 0.3
adamant_profile = [(30.0, ADZ), (T2_EDGE + 0.05, ADZ), (VERGE, ADZ), (VERGE - 0.22, ADZ - 0.28), (VERGE - 0.55, -26.0), (VERGE - 0.75, -48.0),
                   (VERGE - 0.55, -54.0), (VERGE + 0.6, -58.0), (VERGE + 3.2, -60.4), (VERGE + 8.0, -61.3), (30.0, -61.8)]
prism("Adamant", adamant_profile, 'yz', -46.0, 46.0, M_ADAMANT, keep_caps=False)

# ----------------------------------------------------------------------------- the stairs between the galleries
def stair_flight(name, x_top, x_dir, y_range, z_top, mat_step, mat_side, n=24, rise=0.18, tread=0.30, side_y=None, land=1.4, end_wall=True):
    """A straight flight against a wall, descending from z_top in direction x_dir (+1/-1) along x.
    Solid step blocks, a landing at the top, a sloping solid parapet on the open (outward) side."""
    y0, y1 = y_range; zb = z_top - rise * (n + 1)
    xs = lambda i: x_top + x_dir * tread * i
    for i in range(n):
        xa, xb = sorted((xs(i), xs(i + 1)))
        ztop = z_top - rise * (i + 1)
        slab(f"{name}_Step{i}", (xa, xb), (y0, y1), (zb, ztop), mat_step, drop={'+y', '-z'}, bevel=0.008)
    xl = sorted((x_top, x_top - x_dir * land))
    slab(f"{name}_Landing", xl, (y0, y1), (zb, z_top), mat_step, drop={'+y', '-z'})
    # the open side: a sloping parapet wall on a stringer, plus the landing's end wall
    sy0, sy1 = (y0 - 0.25, y0) if side_y is None else side_y
    xe = x_top - x_dir * land; xb_ = xs(n) + x_dir * 0.3
    pts = [(xe, zb), (xb_, zb), (xb_, zb + 1.0), (x_top, z_top + RAIL_H), (xe, z_top + RAIL_H)]
    if x_dir < 0: pts = list(reversed(pts))
    prism(f"{name}_Side", pts, 'xz', sy0, sy1, mat_side)
    if end_wall:
        xw = sorted((xe, xe - x_dir * 0.3))
        slab(f"{name}_EndWall", xw, (sy0, y1), (zb, z_top + RAIL_H), mat_side, drop={'+y', '-z'})

stair_flight("StairUp", 12.7, -1, (G0_BACK - 1.3, G0_BACK), TIER, M_STONE, M_STONE)               # tier 0 -> +1, left behind
stair_flight("StairUp2", -13.7, +1, (T2_Y - 1.3, T2_Y), 2 * TIER, M_STONE_FAR, M_STONE_FAR)          # tier +1 -> +2, right behind
stair_flight("StairDown", STAIR_A[1], +1, (G0_EDGE - 1.3, G0_EDGE), 0.0, M_STONE, M_STONE)          # tier 0 -> -1, right in front
stair_flight("StairDown2", STAIR_B[1], +1, (T1_EDGE - 1.3, T1_EDGE), -TIER, M_STONE, M_STONE)       # tier -1 -> -2, left in front

# ----------------------------------------------------------------------------- the two stair towers that close the bay
def tower(name, s):
    """s = +1 (reader's left, x 28..36) or -1 (right). Stone above the plate, an adamant buttress below."""
    x0, x1 = (HX, HX + TW) if s > 0 else (-HX - TW, -HX)
    inner = '-x' if s > 0 else '+x'
    YF = -11.0; YB = 22.0; ZT = 17.0
    slab(f"{name}_Body", (x0, x1), (YF, YB), (ADZ, ZT), M_STONE_FAR, keep={inner, '-y', '+z'})
    slab(f"{name}_Buttress", (x0, x1), (YF - 0.5, -1.0), (-60.5, ADZ), M_ADAMANT, keep={inner, '-y', '-z'}, bevel=0.3)
    for k, zb in enumerate([-TIER, 0.0, TIER, 2 * TIER, 3 * TIER]):
        slab(f"{name}_Band{k}", (x0 - 0.12, x1 + 0.12), (YF - 0.12, YB), (zb - 0.36, zb), M_STONE_FAR, keep={inner, '-y', '-z', '+z'}, bevel=0.02)
    slab(f"{name}_Cornice", (x0 - 0.22, x1 + 0.22), (YF - 0.22, YB), (ZT - 0.1, ZT + 0.32), M_STONE_FAR, keep={inner, '-y', '-z', '+z'}, bevel=0.03)
    # crenellated top parapet
    for k in range(9):
        y = YF + 0.1 + k * 1.0
        slab(f"{name}_MerlonF{k}", (x0 + 0.1 + k * 0.92, x0 + 0.62 + k * 0.92), (YF - 0.1, YF + 0.35), (ZT + 0.32, ZT + 1.25), M_STONE_FAR, drop={'-z'})
    for k in range(10):
        y = YF + 0.6 + k * 1.1
        xi = x0 - 0.1 if s > 0 else x1 - 0.35
        slab(f"{name}_MerlonS{k}", (xi, xi + 0.45), (y, y + 0.55), (ZT + 0.32, ZT + 1.25), M_STONE_FAR, drop={'-z'})
    # doorways into the tower at each gallery, slit windows on the front
    xf = x0 if s > 0 else x1
    for k, (yc, zf) in enumerate([(-5.8, -2 * TIER), (-1.6, -TIER), (2.75, 0.0), (6.9, TIER), (10.9, 2 * TIER)]):
        slab(f"{name}_Door{k}", (xf - 0.02, xf + 0.02), (yc - 0.65, yc + 0.65), (zf, zf + 2.55), M_DARK, keep={inner})
        for sj in (-1, 1):
            slab(f"{name}_Jamb{k}{sj}", (xf - 0.12, xf + 0.12), (yc + sj * 0.78 - 0.13, yc + sj * 0.78 + 0.13), (zf, zf + 2.55), M_STONE, drop={'-z'}, bevel=0.01)
        slab(f"{name}_Lintel{k}", (xf - 0.14, xf + 0.14), (yc - 0.95, yc + 0.95), (zf + 2.55, zf + 2.95), M_STONE, bevel=0.015)
    for k, xq in enumerate((x0, x1)):
        for j in range(int((ZT - ADZ) / 1.1)):
            zq = ADZ + 0.1 + j * 1.1; w = 0.9 if j % 2 == 0 else 0.55
            xa = xq - 0.06 if xq == x0 else xq - w; xb_ = xq + w if xq == x0 else xq + 0.06
            slab(f"{name}_Quoin{k}_{j}", (xa, xb_), (YF - 0.07, YF + w), (zq, zq + 0.55), M_STONE_FAR, keep={'-y', inner} if xq == xf else {'-y'})
    xc = (x0 + x1) / 2
    for k, z in enumerate([-6.8, -2.3, 2.0, 6.5, 11.0, 15.0]):
        for j, dx in enumerate((-2.2, 2.2)):
            slab(f"{name}_Slit{k}{j}", (xc + dx - 0.14, xc + dx + 0.14), (YF - 0.03, YF + 0.01), (z, z + 1.3), M_DARK, keep={'-y'})
            slab(f"{name}_SlitSill{k}{j}", (xc + dx - 0.26, xc + dx + 0.26), (YF - 0.10, YF + 0.01), (z - 0.12, z), M_STONE_FAR, drop={'+y'})
for s in (1, -1): tower("TowerL" if s > 0 else "TowerR", s)

# ----------------------------------------------------------------------------- drip spouts under the parapets (rain runs off the galleries)
for tz, yface in ((0.0, G0_EDGE), (-TIER, T1_EDGE), (-2 * TIER, T2_EDGE)):
    for i, x in enumerate([-24.0 + 4.8 * k + (1.2 if tz < 0 else 0) for k in range(11)]):
        if abs(x) < 3.4 and tz == 0.0: continue
        bbox(f"Spout{int(-tz)}_{i}", (0.16, 0.42, 0.12), (x, yface - 0.21, tz - 0.12), M_STONE, rot=(math.radians(-8), 0, 0), drop={'+y'})

# ----------------------------------------------------------------------------- the davit, pulley, chain and seat at the lowest gallery
DV = Vector((-6.0, T2_EDGE + PT + 0.16, -2 * TIER))
slab("Davit_Post", (DV.x - 0.07, DV.x + 0.07), (DV.y - 0.07, DV.y + 0.07), (DV.z, DV.z + 2.75), M_IRON, bevel=0.01)
slab("Davit_Foot", (DV.x - 0.18, DV.x + 0.18), (DV.y - 0.18, DV.y + 0.18), (DV.z, DV.z + 0.05), M_IRON)
ARM_END = Vector((DV.x, VERGE - 0.9, DV.z + 2.6))
slab("Davit_Arm", (DV.x - 0.06, DV.x + 0.06), (ARM_END.y - 0.1, DV.y + 0.07), (ARM_END.z - 0.07, ARM_END.z + 0.07), M_IRON)
br_a = Vector((0, DV.y, DV.z + 1.55)); br_b = Vector((0, DV.y - 1.4, ARM_END.z - 0.05)); bd = br_b - br_a
bbox("Davit_Brace", (0.05, bd.length, 0.07), (DV.x, (br_a.y + br_b.y) / 2, (br_a.z + br_b.z) / 2), M_IRON, rot=(math.atan2(bd.z, bd.y), 0, 0))
PUL = Vector((DV.x, ARM_END.y + 0.02, ARM_END.z - 0.22))
for sj in (-1, 1):
    slab(f"Pulley_Cheek{sj}", (PUL.x + sj * 0.05 - 0.012, PUL.x + sj * 0.05 + 0.012), (PUL.y - 0.14, PUL.y + 0.14), (PUL.z - 0.14, ARM_END.z), M_IRON)
lathe("Pulley_Wheel", [(0.0, -0.035), (0.11, -0.035), (0.13, -0.02), (0.10, 0.0), (0.13, 0.02), (0.11, 0.035), (0.0, 0.035)], tuple(PUL), M_WOOD, steps=14, rot=(0, math.radians(90), 0))
CH_X, CH_Y = PUL.x, PUL.y - 0.12
SEAT_Z = DV.z + 0.55
z = PUL.z
k = 0
while z > SEAT_Z + 0.45:
    rot = (0, 0, 0) if k % 2 == 0 else (0, 0, math.radians(90))
    bbox(f"Chain{k}", (0.045, 0.014, 0.085), (CH_X, CH_Y, z - 0.04), M_IRON, rot=rot)
    z -= 0.068; k += 1
RING_Z = z
lathe("Chain_Ring", [(0.04, -0.01), (0.05, 0.0), (0.04, 0.01)], (CH_X, CH_Y, RING_Z), M_IRON, steps=10, rot=(math.radians(90), 0, 0))
slab("Seat_Board", (CH_X - 0.24, CH_X + 0.24), (CH_Y - 0.17, CH_Y + 0.17), (SEAT_Z - 0.035, SEAT_Z + 0.005), M_WOOD, bevel=0.01)
for sx in (-1, 1):
    for sy in (-1, 1):
        a = Vector((CH_X + sx * 0.21, CH_Y + sy * 0.14, SEAT_Z)); b_ = Vector((CH_X, CH_Y, RING_Z - 0.04)); d = b_ - a
        tube(f"Seat_Rope{sx}{sy}", [tuple(a), tuple(a + d * 0.5), tuple(b_)], (0.008, 0.008), M_IRON, sides=4, n=1)
# the windlass at the post's foot that winds the chain
lathe("Windlass_Drum", [(0.0, -0.22), (0.13, -0.22), (0.10, -0.2), (0.10, 0.2), (0.13, 0.22), (0.0, 0.22)], (DV.x + 0.42, DV.y + 0.45, DV.z + 0.62), M_WOOD, steps=12, rot=(0, math.radians(90), 0))
for sj in (-1, 1):
    slab(f"Windlass_Frame{sj}", (DV.x + 0.42 + sj * 0.26 - 0.03, DV.x + 0.42 + sj * 0.26 + 0.03), (DV.y + 0.30, DV.y + 0.60), (DV.z, DV.z + 0.78), M_IRON)
slab("Windlass_Crank", (DV.x + 0.70, DV.x + 0.74), (DV.y + 0.43, DV.y + 0.47), (DV.z + 0.42, DV.z + 0.64), M_IRON)

# ----------------------------------------------------------------------------- the telescope on its pedestal, in the belvedere
TEL = Vector((1.62, 0.32, 0.0))
lathe("Telescope_Pedestal", [(0.17, 0.0), (0.17, 0.07), (0.12, 0.11), (0.095, 0.19), (0.085, 0.55), (0.095, 0.86), (0.13, 0.90), (0.16, 0.95), (0.16, 1.0), (0.0, 1.0)],
      tuple(TEL), M_STONE_NEAR, steps=14)
lathe("Telescope_Yoke", [(0.05, 1.0), (0.035, 1.04), (0.03, 1.12), (0.0, 1.12)], tuple(TEL), M_BRASS, steps=10)
TDIR = Vector((0.18, -0.80, 0.57)).normalized()
PIV = TEL + Vector((0, 0, 1.17))
qrot = TDIR.to_track_quat('Z', 'Y').to_euler()
lathe("Telescope_Tube", [(0.0, -0.36), (0.035, -0.36), (0.05, -0.34), (0.062, -0.33), (0.058, -0.30), (0.058, 0.10), (0.066, 0.12), (0.052, 0.14), (0.052, 0.36), (0.060, 0.38), (0.060, 0.42), (0.0, 0.42)],
      tuple(PIV), M_BRASS, steps=14, rot=tuple(qrot))
lathe("Telescope_Eyepiece", [(0.0, -0.46), (0.022, -0.46), (0.024, -0.36)], tuple(PIV), M_BRASS, steps=10, rot=tuple(qrot))
for sj in (-1, 1):
    slab(f"Telescope_Fork{sj}", (PIV.x + sj * 0.06 - 0.008, PIV.x + sj * 0.06 + 0.008), (PIV.y - 0.02, PIV.y + 0.02), (TEL.z + 1.10, PIV.z + 0.02), M_BRASS)

# ----------------------------------------------------------------------------- planting: urns with myrtle, an orange tree in a tub, garden trees on the top
def leaf_shell(bm, centre, radii, n, rng, size, seed=0.0, up_bias=0.3, lean=None):
    """n leaf blades scattered on a noisy ellipsoidal shell, each turned a little off the outward normal."""
    c = Vector(centre)
    for i in range(n):
        d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1) + up_bias)).normalized()
        k = 1.0 + 0.22 * noise.noise(d * 2.4 + Vector((seed, 0, 0)))
        rr = rng.uniform(0.72, 1.0) * k
        p = c + Vector((d.x * radii[0], d.y * radii[1], d.z * radii[2])) * rr
        if lean is not None: p += Vector(lean) * max(0.0, d.z)
        nrm = (d + Vector((rng.gauss(0, 0.5), rng.gauss(0, 0.5), rng.gauss(0, 0.5) + 0.3))).normalized()
        t = nrm.cross(Vector((0, 0, 1)) if abs(nrm.z) < 0.95 else Vector((1, 0, 0))).normalized()
        t.rotate(Matrix.Rotation(rng.uniform(-1.2, 1.2), 3, nrm))
        bt = nrm.cross(t).normalized()
        L = size[0] * rng.uniform(0.7, 1.3); W = size[1] * rng.uniform(0.75, 1.25)
        curl = nrm * (L * 0.12)
        vs = [bm.verts.new(p - t * L * 0.5), bm.verts.new(p + bt * W * 0.5 + curl), bm.verts.new(p + t * L * 0.5), bm.verts.new(p - bt * W * 0.5 + curl)]
        bm.faces.new(vs)

def urn(name, p, z0):
    prof = [(0.13, 0.0), (0.15, 0.03), (0.10, 0.07), (0.085, 0.12), (0.16, 0.20), (0.235, 0.34), (0.25, 0.44), (0.215, 0.49), (0.26, 0.52), (0.25, 0.56), (0.2, 0.56), (0.2, 0.52)]
    lathe(name, prof, (p[0], p[1], z0), M_STONE_NEAR, steps=14)
    lathe(name + "_Soil", [(0.0, 0.53), (0.21, 0.53)], (p[0], p[1], z0), M_SOIL, steps=14)

def myrtle(name, p, z, rng, seed):
    blob(name + "_Core", (p[0], p[1], z), 0.24, M_LEAVES, scale=(1.0, 1.0, 0.9), subdiv=2, amp=0.28, freq=2.2, seed=seed)
    bm = bmesh.new()
    leaf_shell(bm, (p[0], p[1], z), (0.32, 0.32, 0.29), 950, rng, (0.045, 0.019), seed=seed)
    for k in range(5):                    # a few stems at the base
        a = 2 * math.pi * k / 5 + rng.uniform(-0.3, 0.3)
        tube(None, [(p[0], p[1], z - 0.30), (p[0] + 0.08 * math.cos(a), p[1] + 0.08 * math.sin(a), z - 0.12)], (0.012, 0.007), None, sides=4, n=1, bm=bm)
    _obj(name + "_Leaves", bm, M_LEAVES)

rng = random.Random(41)
for s in (-1, 1):
    zp = RAIL_H + 0.04 + 0.06
    urn(f"Urn{s}", (s * 2.8, G0_IN - PT / 2), zp)
    myrtle(f"Myrtle{s}", (s * 2.8, G0_IN - PT / 2), zp + 0.56 + 0.24, rng, seed=3.0 + s)

# an orange tree in a stone tub, behind and to the right
OT = Vector((-4.6, 3.75, 0.0))
lathe("OrangeTub", [(0.30, 0.0), (0.34, 0.04), (0.30, 0.08), (0.33, 0.50), (0.38, 0.55), (0.38, 0.60), (0.33, 0.60), (0.33, 0.56)], tuple(OT), M_STONE, steps=16)
lathe("OrangeTub_Soil", [(0.0, 0.55), (0.33, 0.55)], tuple(OT), M_SOIL, steps=16)
bm = bmesh.new()
tube(None, [(OT.x, OT.y, 0.5), (OT.x + 0.03, OT.y - 0.02, 1.0), (OT.x - 0.02, OT.y + 0.03, 1.45)], (0.05, 0.035), None, sides=7, n=3, bm=bm)
for k in range(5):
    a = 2 * math.pi * k / 5 + 0.4
    tube(None, [(OT.x, OT.y, 1.40), (OT.x + 0.30 * math.cos(a), OT.y + 0.30 * math.sin(a), 1.75 + 0.1 * (k % 2))], (0.025, 0.012), None, sides=5, n=2, bm=bm)
_obj("OrangeTree_Trunk", bm, M_BARK, smooth=True)
CROWN = (OT.x, OT.y, 2.05)
blob("OrangeTree_Core", CROWN, 0.62, M_LEAVES, scale=(1.0, 1.0, 0.85), subdiv=2, amp=0.25, freq=1.8, seed=7.0)
bm = bmesh.new(); leaf_shell(bm, CROWN, (0.74, 0.74, 0.64), 1250, random.Random(9), (0.10, 0.042), seed=7.0)
_obj("OrangeTree_Leaves", bm, M_LEAVES)
bm = bmesh.new(); frng = random.Random(12)
for k in range(15):
    d = Vector((frng.gauss(0, 1), frng.gauss(0, 1), frng.gauss(0, 1) * 0.7 - 0.2)).normalized()
    c = Vector(CROWN) + Vector((d.x * 0.72, d.y * 0.72, d.z * 0.6))
    bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=0.04, matrix=Matrix.Translation(c))
_obj("OrangeTree_Fruit", bm, M_FRUIT, smooth=True)

# garden trees on the island's upper surface: tall cypresses and round holm oaks, seen above the top parapet
def garden_tree(name, x, y, kind, h, seed):
    z0 = 3 * TIER
    r = random.Random(seed)
    if kind == 'cypress':
        rad = h * 0.10
        prof = [(rad * 0.5, 0.0), (rad * 0.95, h * 0.12), (rad, h * 0.35), (rad * 0.85, h * 0.6), (rad * 0.55, h * 0.82), (rad * 0.2, h * 0.96), (0.0, h)]
        lathe(name, [(rr, z0 + zz) for rr, zz in prof], (x, y, 0), M_TREES, steps=9, wobble=0.22, seed=seed)
    else:
        tube(name + "_Trunk", [(x, y, z0 - 0.2), (x + 0.2, y, z0 + h * 0.3), (x - 0.1, y + 0.1, z0 + h * 0.5)], (0.22, 0.12), M_BARK, sides=6, n=2)
        for k in range(5):
            a = 2 * math.pi * k / 5 + r.uniform(-0.4, 0.4); rr = h * r.uniform(0.18, 0.28)
            c = (x + math.cos(a) * h * 0.18, y + math.sin(a) * h * 0.18, z0 + h * r.uniform(0.62, 0.78))
            blob(f"{name}_Crown{k}", c, rr, M_TREES, scale=(1.0, 1.0, 0.8), subdiv=1, amp=0.35, freq=1.9, seed=seed + k)
        blob(f"{name}_CrownTop", (x, y, z0 + h * 0.86), h * 0.22, M_TREES, scale=(1.0, 1.0, 0.75), subdiv=1, amp=0.3, freq=2.1, seed=seed + 9)
for i, (x, y, kind, h) in enumerate([(-9.0, 17.5, 'cypress', 12.5), (-6.5, 19.0, 'cypress', 10.0), (3.0, 18.0, 'oak', 8.5), (11.0, 17.0, 'cypress', 13.5),
                                     (14.0, 20.0, 'oak', 7.5), (-19.0, 19.5, 'oak', 9.0), (21.0, 18.5, 'cypress', 11.0), (-2.5, 24.0, 'oak', 9.5)]):
    garden_tree(f"GardenTree{i}", x, y, kind, h, 100 + i * 7)
# the upper surface itself: the island's rich mould, falling gently towards its centre
bm = bmesh.new(); Nx, Ny = 16, 10; grid = []
for j in range(Ny + 1):
    y = TOP_Y + 0.25 + (60.0 - TOP_Y) * (j / Ny) ** 1.4
    row = []
    for i in range(Nx + 1):
        x = -44.0 + 88.0 * i / Nx
        z = 3 * TIER - 0.05 - (y - TOP_Y) * 0.025 + 0.25 * noise.noise(Vector((x * 0.08, y * 0.08, 0.7)))
        row.append(bm.verts.new((x, y, z)))
    grid.append(row)
for j in range(Ny):
    for i in range(Nx): bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
_obj("GardenGround", bm, M_GARDEN, smooth=True)

# ----------------------------------------------------------------------------- grass in the joints and at the wall feet, valerian on the walls, leaf litter
def tuft(bm, p, rng, hscale=1.0, nb=None, wind=Vector((0.35, -0.2, 0))):
    nb = nb or rng.randint(3, 6)
    for _ in range(nb):
        q = Vector((p[0] + rng.uniform(-0.05, 0.05), p[1] + rng.uniform(-0.05, 0.05), p[2] - 0.005))
        h = rng.uniform(0.10, 0.32) * hscale; w = rng.uniform(0.004, 0.008)
        bend = (wind * rng.uniform(0.1, 0.5) + Vector((rng.uniform(-0.35, 0.35), rng.uniform(-0.35, 0.35), 0))) * h
        sa = rng.uniform(0, math.pi); side = Vector((math.cos(sa), math.sin(sa), 0)) * w
        pts = [q + Vector((0, 0, h * t * (1 - 0.2 * t * t))) + bend * t * t for t in (0.0, 0.4, 0.75, 1.0)]
        vs = [(bm.verts.new(c - side * (1 - t)), bm.verts.new(c + side * (1 - t))) for c, t in zip(pts[:3], (0.0, 0.4, 0.75))]
        tip = bm.verts.new(pts[3])
        for k in range(2): bm.faces.new((vs[k][0], vs[k][1], vs[k + 1][1], vs[k + 1][0]))
        bm.faces.new((vs[2][0], vs[2][1], tip))

bm = bmesh.new(); grng = random.Random(77); placed = 0
def in_stairs(x, y, z):
    if abs(z) < 0.1 and STAIR_UP[0] - 0.3 < x < STAIR_UP[1] + 0.3 and y > G0_BACK - 1.6: return True
    if abs(z) < 0.1 and -17.8 < x < -7.9 and y < G0_EDGE + 0.3: return True
    if abs(z + TIER) < 0.1 and STAIR_A[0] - 0.4 < x < -8.0 and y > G0_EDGE - 1.6: return True
    if abs(z + TIER) < 0.1 and 7.2 < x < 17.2 and y < T1_EDGE + 0.4: return True
    if abs(z + 2 * TIER) < 0.1 and 8.8 < x < 17.2 and y > T1_EDGE - 1.6: return True
    if abs(z - TIER) < 0.1 and -15.8 < x < -6.0 and y > T2_Y - 1.6: return True
    return False
lines = [(0.0, G0_BACK - 0.06, -1), (0.0, G0_IN + 0.06, +1), (-TIER, G0_EDGE - 0.06, -1), (-TIER, T1_EDGE + PT + 0.06, +1),
         (-2 * TIER, T1_EDGE - 0.06, -1), (-2 * TIER, T2_EDGE + PT + 0.06, +1), (TIER, T2_Y - 0.06, -1), (TIER, T1_Y + PT + 0.06, +1),
         (2 * TIER, TOP_Y - 0.06, -1), (3 * TIER, TOP_Y + PT + 0.1, +1)]
for (zf, yl, sgn) in lines:
    x = -HX + 0.3
    while x < HX - 0.3:
        x += grng.uniform(0.15, 1.6)
        dens = noise.noise(Vector((x * 0.21, zf * 0.3, 2.2)))
        if dens < 0.08 or grng.random() > 0.42: continue
        if abs(zf) < 0.1 and abs(x) < 3.2 and sgn > 0: continue          # the belvedere's mouth stays clean
        y = yl - sgn * grng.uniform(0.0, 0.10)
        if in_stairs(x, y, zf): continue
        for c in range(grng.randint(1, 2)):
            tuft(bm, (x + grng.uniform(-0.18, 0.18), y - sgn * grng.uniform(0, 0.06), zf), grng, hscale=grng.uniform(0.5, 1.25)); placed += 1
# a few tufts in paving joints and in the belvedere's corners near the reader
for (x, y, hs) in [(-0.92, -0.86, 0.6), (0.95, -0.84, 0.45), (-2.55, 0.74, 0.8), (2.6, 0.70, 0.7), (-3.4, 2.1, 0.5), (5.0, 1.4, 0.6), (-6.2, 4.6, 0.9),
                   (-1.6, 4.62, 0.7), (1.8, 4.65, 0.6), (-8.3, 2.9, 0.5), (9.4, 0.98, 0.8)]:
    tuft(bm, (x, y, 0.0), grng, hscale=hs, nb=grng.randint(5, 9)); placed += 1
print("grass tufts", placed)
_obj("Grass", bm, M_GRASS)

def wall_plant(name, p, outward, rng, size=1.0, flowers=True):
    """Red valerian rooted in a joint: glaucous lance leaves splaying out from the wall, heads of small flowers."""
    o = Vector(outward).normalized(); p = Vector(p)
    bm = bmesh.new()
    leaf_shell(bm, p + o * 0.12 * size + Vector((0, 0, 0.05 * size)), (0.22 * size, 0.22 * size, 0.18 * size), int(38 * size), rng, (0.10 * size, 0.028 * size),
               seed=rng.random() * 10, up_bias=0.6)
    _obj(name + "_Leaves", bm, M_WALLPLANT)
    if flowers:
        bm = bmesh.new()
        for k in range(int(5 * size)):
            c = p + o * rng.uniform(0.12, 0.32) * size + Vector((rng.uniform(-0.2, 0.2) * size, rng.uniform(-0.2, 0.2) * size, rng.uniform(0.15, 0.42) * size))
            c -= o * 0.0
            for j in range(2):
                q = c + Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), rng.uniform(-0.02, 0.03)))
                bmesh.ops.create_uvsphere(bm, u_segments=4, v_segments=3, radius=0.026 * size, matrix=Matrix.Translation(q) @ Matrix.Diagonal((1, 1, 0.7, 1)))
        _obj(name + "_Flowers", bm, M_FLOWERS, smooth=True)
wrng = random.Random(5)
for i, (p, o, sz) in enumerate([((-9.6, G0_EDGE, -1.3), (0, -1, 0), 1.0), ((12.2, G0_EDGE, -2.7), (0, -1, 0), 0.8), ((19.5, G0_EDGE, -0.9), (0, -1, 0), 1.1),
                                (((BAY_FOOT[1][0] + BAY_FOOT[2][0]) / 2 - 0.4, BAY_FOOT[1][1], -1.9), (0, -1, 0), 0.9),
                                ((-15.0, T1_EDGE, -6.2), (0, -1, 0), 1.0), ((4.5, T1_EDGE, -7.4), (0, -1, 0), 0.8),
                                ((HX, -2.0, -2.6), (-1, 0, 0), 1.0), ((-HX, 1.2, -1.5), (1, 0, 0), 0.9), ((-22.0, G0_BACK, 3.1), (0, -1, 0), 0.7),
                                ((7.5, T2_Y, 7.7), (0, -1, 0), 0.8)]):
    wall_plant(f"Valerian{i}", p, o, wrng, size=sz)

bm = bmesh.new(); lrng = random.Random(23)
def litter(cx, cy, z, r, n):
    for _ in range(n):
        a = lrng.uniform(0, 2 * math.pi); d = r * math.sqrt(lrng.random())
        p = Vector((cx + d * math.cos(a), cy + d * math.sin(a), z + 0.004))
        t = Vector((math.cos(lrng.uniform(0, 6.3)), math.sin(lrng.uniform(0, 6.3)), 0)).normalized(); bt = Vector((-t.y, t.x, 0))
        L = lrng.uniform(0.05, 0.10); W = L * 0.42; lift = Vector((0, 0, lrng.uniform(0.0, 0.012)))
        bm.faces.new([bm.verts.new(p - t * L / 2), bm.verts.new(p + bt * W / 2 + lift), bm.verts.new(p + t * L / 2), bm.verts.new(p - bt * W / 2 + lift)])
litter(OT.x, OT.y - 0.2, 0.0, 1.1, 60); litter(OT.x + 0.8, G0_BACK - 0.25, 0.0, 0.4, 18)
litter(-2.45, 0.70, 0.0, 0.25, 10); litter(2.45, 0.68, 0.0, 0.22, 8); litter(-0.80, -0.82, 0.0, 0.16, 6)
litter(-1.0, G0_BACK - 0.25, 0.0, 0.3, 10)
_obj("Litter", bm, M_LITTER)

# ----------------------------------------------------------------------------- the sky and the land below: generated images on two domes
def _hash(ix, iy, seed):
    n = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n = n ^ (n >> 16)
    return (n & 0xFFFFFF).astype(np.float32) * np.float32(1.0 / 0xFFFFFF)

def vnoise(x, y, seed=0):
    xi = np.floor(x); yi = np.floor(y)
    fx = (x - xi).astype(np.float32); fy = (y - yi).astype(np.float32)
    xi = xi.astype(np.int64); yi = yi.astype(np.int64)
    ux = fx * fx * (3 - 2 * fx); uy = fy * fy * (3 - 2 * fy)
    a = _hash(xi, yi, seed); b_ = _hash(xi + 1, yi, seed); c = _hash(xi, yi + 1, seed); d = _hash(xi + 1, yi + 1, seed)
    ab = a + (b_ - a) * ux; cd = c + (d - c) * ux
    return ab + (cd - ab) * uy

def fbm(x, y, octaves, fp, seed=0, gain=0.5):
    """Band-limited fBm: each octave fades out as its wavelength approaches the texel footprint fp (same units)."""
    tot = np.zeros(np.broadcast(x, y).shape, np.float32); amp = 0.5; f = 1.0; norm = 0.0
    for o in range(octaves):
        w = np.clip((0.7 - fp * f) / 0.45, 0.0, 1.0).astype(np.float32)
        if np.max(w) > 0:
            n = vnoise(x * f + o * 17.31, y * f - o * 9.17, seed + o)
            tot += amp * (w * n + (1 - w) * 0.5)
        else:
            tot += amp * 0.5
        norm += amp; amp *= gain; f *= 2.0
    return tot / norm

def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0); return t * t * (3 - 2 * t)

SUN_AZ = math.atan2(SUN_DIR.y, SUN_DIR.x); SUN_EL = math.asin(SUN_DIR.z)

def horizon_rgb(az):
    """The haze colour at the horizon, brighter and warmer towards the sun's azimuth (shared by sky and land)."""
    cs = np.cos(az - SUN_AZ); g = np.clip(cs, 0, 1) ** 3
    base = np.array([0.60, 0.67, 0.78], np.float32)
    warm = np.array([0.10, 0.09, 0.06], np.float32)
    return base[None, None, :] + warm[None, None, :] * g[..., None]

def to_srgb(lin):
    lin = np.clip(lin, 0.0, 1.0)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055).astype(np.float32)

def save_rgb(path, rgb):
    """rgb: (H, W, 3) linear, row 0 = bottom (v=0). Written as an sRGB PNG."""
    h, w, _ = rgb.shape
    img = bpy.data.images.new(os.path.basename(path)[:-4], w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32); px[..., :3] = to_srgb(rgb)
    img.pixels.foreach_set(px.ravel()); img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)

SKY_EL0 = -3.0
def gen_sky(path, W=2048, Hh=1024):
    az = (-math.pi + (np.arange(W) + 0.5) / W * 2 * math.pi).astype(np.float32)
    el = (SKY_EL0 + (np.arange(Hh) + 0.5) / Hh * (90.0 - SKY_EL0)).astype(np.float32)
    AZ, EL = np.meshgrid(az, el)
    elr = np.radians(EL)
    dx = np.cos(elr) * np.cos(AZ); dy = np.cos(elr) * np.sin(AZ); dz = np.sin(elr)
    hor = horizon_rgb(AZ).reshape(Hh, W, 3)
    zen = np.array([0.105, 0.225, 0.52], np.float32)
    f = (np.clip(EL, 0, 90) / 90.0) ** 0.36
    col = hor * (1 - f[..., None]) + zen[None, None, :] * f[..., None]
    # sun: a small bright core, aureole and wide glow
    cosg = np.clip(dx * SUN_DIR.x + dy * SUN_DIR.y + dz * SUN_DIR.z, -1, 1); ang = np.degrees(np.arccos(cosg))
    glow = 1.6 * np.exp(-(ang / 0.9) ** 2) + 0.35 * np.exp(-(ang / 5.0) ** 2) + 0.12 * np.exp(-(ang / 22.0) ** 2) + 0.05 * np.exp(-(ang / 60.0) ** 2)
    col += glow[..., None] * np.array([1.0, 0.95, 0.84], np.float32)[None, None, :]
    # a few faint high cirrus wisps, well away from the horizon
    k = 1.0 / (np.maximum(dz, 0.02) + 0.08)
    px_, py_ = dx * k, dy * k
    ca, sa = math.cos(0.5), math.sin(0.5)
    u = (px_ * ca + py_ * sa) * 0.9; v = (-px_ * sa + py_ * ca) * 4.0
    fpw = (1.0 / W * 2 * math.pi) * k * 4.0
    n = fbm(u, v, 6, fpw, seed=301)
    wisp = sstep(0.60, 0.78, n) * sstep(10.0, 30.0, EL) * 0.10
    col += wisp[..., None] * np.array([1.0, 1.0, 1.0], np.float32)[None, None, :]
    col = np.where((EL < 0)[..., None], hor, col)
    save_rgb(path, col)

LAND_AZ0, LAND_AZ1 = math.radians(-205.0), math.radians(25.0)
LAND_EL0 = 0.4
def land_el(t): return LAND_EL0 - (LAND_EL0 + 90.0) * t ** 1.6

def gen_land(path, W=4096, Hh=2048):
    """The land two miles below as seen from the gallery: fields, woods, a river, villages, Lagado, a coast and the
    sea, mountains to the left, a layer of fair-weather cumulus between with their shadows, all under aerial haze.
    Coordinates in km on the ground; every pattern is band-limited by the texel's ground footprint."""
    az = (LAND_AZ0 + (np.arange(W) + 0.5) / W * (LAND_AZ1 - LAND_AZ0)).astype(np.float64)
    t = 1.0 - (np.arange(Hh) + 0.5) / Hh
    el = land_el(t)
    dep = np.radians(np.maximum(-el, 0.03))
    tan_d = np.tan(dep); sin_d = np.sin(dep)
    r_g = H_ISL / tan_d
    ddep = np.radians((LAND_EL0 + 90.0) * 1.6 * np.maximum(t, 1e-3) ** 0.6 / Hh)
    fp = np.maximum(H_ISL / sin_d ** 2 * ddep, r_g * (LAND_AZ1 - LAND_AZ0) / W)[:, None].astype(np.float32)
    ca = np.cos(az)[None, :]; sa = np.sin(az)[None, :]
    gx = (r_g[:, None] * ca).astype(np.float32); gy = (r_g[:, None] * sa).astype(np.float32)
    shp = (Hh, W)
    def C(c): return np.array(c, np.float32)[None, None, :]
    # --- fields: two field systems of different grain and orientation
    def fields(ang, rw, l0, l1, seed):
        c_, s_ = math.cos(ang), math.sin(ang)
        fu = wx * c_ + wy * s_; fv = -wx * s_ + wy * c_
        row = np.floor(fv / rw); fvv = fv / rw - row
        ri = row.astype(np.int64)
        off = _hash(ri, np.zeros_like(ri), seed); fl = l0 + (l1 - l0) * _hash(ri, np.ones_like(ri), seed + 1)
        cu = fu / fl + off * 3.0; cell = np.floor(cu); fuu = cu - cell
        ci = cell.astype(np.int64)
        tone = _hash(ci, ri, seed + 2)
        split = 0.3 + 0.4 * _hash(ci, ri, seed + 3); dosplit = _hash(ci, ri, seed + 4) < 0.45
        upper = dosplit & (fvv > split)
        tone = np.where(upper, _hash(ci, ri, seed + 5), tone)
        pal = np.array([[0.32, 0.24, 0.11], [0.26, 0.20, 0.12], [0.15, 0.105, 0.065], [0.10, 0.13, 0.05], [0.21, 0.19, 0.09],
                        [0.25, 0.22, 0.15], [0.35, 0.27, 0.13], [0.19, 0.145, 0.085], [0.29, 0.23, 0.15], [0.115, 0.08, 0.05], [0.14, 0.16, 0.07]], np.float32)
        idx = np.minimum((tone * len(pal)).astype(np.int64), len(pal) - 1)
        col = pal[idx]
        size = np.minimum(fl, rw)
        vis = sstep(1.2, 3.5, size / fp)[..., None]
        col = col * vis + pal.mean(axis=0)[None, None, :] * (1 - vis)
        d = np.minimum(np.minimum(fuu, 1 - fuu) * fl, np.minimum(fvv, 1 - fvv) * rw)
        d = np.where(dosplit, np.minimum(d, np.abs(fvv - split) * rw), d)
        hw = 0.006; wv = np.maximum(hw, fp)
        hedge = ((d < wv) * (hw / wv) * 0.5)[..., None]
        col = col * (1 - hedge) + C((0.06, 0.07, 0.04)) * hedge
        return col
    macro = fbm(gx / 18.0, gy / 18.0, 4, fp / 18.0, seed=1)
    wx = gx + 0.35 * (fbm(gx / 1.6, gy / 1.6, 3, fp / 1.6, seed=7) - 0.5); wy = gy + 0.35 * (fbm(gx / 1.6 + 5.2, gy / 1.6, 3, fp / 1.6, seed=8) - 0.5)
    fa = fields(0.32, 0.17, 0.16, 0.48, 10); fb = fields(-0.55, 0.24, 0.12, 0.34, 20)
    sel = sstep(0.47, 0.53, fbm(gx / 7.0 + 3.1, gy / 7.0, 3, fp / 7.0, seed=2))[..., None]
    land = fa * (1 - sel) + fb * sel
    mott = fbm(gx / 0.35, gy / 0.35, 5, fp / 0.35, seed=3)
    land *= (0.80 + 0.40 * mott)[..., None]
    arid = sstep(0.45, 0.62, macro)[..., None]
    scrub = C((0.27, 0.225, 0.155)) * (0.85 + 0.3 * mott)[..., None]
    land = land * (1 - arid * 0.6) + scrub * arid * 0.6
    # woods
    wd = fbm(gx / 0.6, gy / 0.6, 5, fp / 0.6, seed=4)
    woods = sstep(0.655, 0.685, wd + (0.5 - macro) * 0.2)[..., None]
    land = land * (1 - woods) + C((0.035, 0.052, 0.028)) * (0.8 + 0.4 * mott)[..., None] * woods
    # the river, winding across the plain in front, with a green strip along it
    rv = gy + 8.5 + 2.2 * np.sin(gx / 3.3) + 3.0 * (fbm(gx / 5.0, 0.37 + gy * 0.0, 4, fp / 5.0, seed=6) - 0.5) * 2
    ar = np.abs(rv)
    rip = sstep(0.9, 0.15, ar)[..., None]
    land = land * (1 - rip * 0.35) + C((0.07, 0.11, 0.05)) * rip * 0.35
    rcov = (np.clip(0.5 + (0.055 - ar) / np.maximum(fp * 0.7, 0.005), 0, 1) * np.minimum(1.0, 0.11 / np.maximum(fp, 1e-3)))[..., None]
    land = land * (1 - rcov) + C((0.24, 0.31, 0.40)) * rcov
    # villages: small clusters of roofs, mostly near the river
    vc = 1.7; vx = np.floor(gx / vc).astype(np.int64); vy = np.floor(gy / vc).astype(np.int64)
    cx_ = (vx + 0.2 + 0.6 * _hash(vx, vy, 41)) * vc; cy_ = (vy + 0.2 + 0.6 * _hash(vx, vy, 42)) * vc
    has = (_hash(vx, vy, 43) < (0.18 + 0.45 * rip[..., 0])).astype(np.float32)
    dv = np.hypot(gx - cx_, (gy - cy_) * 1.3)
    vr = (0.05 + 0.06 * _hash(vx, vy, 44)) * (0.6 + 0.8 * fbm((gx - cx_) / 0.05, (gy - cy_) / 0.05, 3, fp / 0.05, seed=46))
    vcov = has * np.clip(0.5 + (vr - dv) / np.maximum(fp, 0.01), 0, 1) * np.minimum(1.0, 0.2 / np.maximum(fp, 1e-3))
    roofs = 0.75 + 0.5 * fbm(gx / 0.03, gy / 0.03, 2, fp / 0.03, seed=45)
    land = land * (1 - vcov[..., None]) + C((0.31, 0.27, 0.235)) * roofs[..., None] * vcov[..., None]
    # Lagado, the metropolis, ahead and to the left
    LG = (7.5, -15.0); dl = np.hypot(gx - LG[0], (gy - LG[1]) * 1.2)
    lcov = np.clip(0.5 + (1.3 + 0.4 * (fbm(gx / 0.8, gy / 0.8, 3, fp / 0.8, seed=47) - 0.5) - dl) / np.maximum(fp, 0.02), 0, 1)
    streets = 1.0 - 0.35 * np.minimum(1.0, 0.012 / np.maximum(fp, 1e-3)) * ((np.abs(((gx - LG[0]) / 0.09) % 1.0 - 0.5) > 0.42) | (np.abs(((gy - LG[1]) / 0.09) % 1.0 - 0.5) > 0.42))
    city = C((0.38, 0.34, 0.30)) * (roofs * streets)[..., None]
    land = land * (1 - lcov[..., None]) + city * lcov[..., None]
    # mountains to the left (+x), shaded from the sun
    m = gx * 0.85 - gy * 0.25 - 16.0 + 6.0 * (fbm(gx / 9.0, gy / 9.0, 4, fp / 9.0, seed=50) - 0.5)
    mm = sstep(0.0, 5.0, m)
    sel_m = mm > 0.005
    if np.any(sel_m):
        xs_, ys_, fps_ = gx[sel_m], gy[sel_m], np.broadcast_to(fp, shp)[sel_m]
        def hgt(x, y): return 1.0 - np.abs(2.0 * fbm(x / 3.0, y / 3.0, 7, fps_ / 3.0, seed=51) - 1.0)
        e = 0.08
        h0 = hgt(xs_, ys_); hx = hgt(xs_ + e, ys_); hy = hgt(xs_, ys_ + e)
        sx, sy = math.cos(SUN_AZ), math.sin(SUN_AZ)
        slope = ((hx - h0) * sx + (hy - h0) * sy) / e
        shade = np.clip(0.75 + 1.8 * slope, 0.3, 1.45)
        rock = np.array([0.20, 0.18, 0.15], np.float32)[None, :] * (1 - h0[:, None] * 0.0)
        forest = np.array([0.05, 0.07, 0.04], np.float32)[None, :]
        fm = sstep(0.55, 0.40, h0)[:, None]
        mc = (rock * (1 - fm) + forest * fm) * shade[:, None]
        w_ = mm[sel_m][:, None]
        land[sel_m] = land[sel_m] * (1 - w_) + mc * w_
    # the coast and the sea to the right (-x)
    s = (-gx) * 0.80 + (-gy) * 0.30 - 7.0 + 5.0 * (fbm(gx / 6.0, gy / 6.0, 6, fp / 6.0, seed=60) - 0.5)
    fpk = np.maximum(fp, 0.02)
    seacov = sstep(-fpk, fpk, s)[..., None]
    beach = (np.clip(1 - np.abs(s + 0.06) / np.maximum(fpk, 0.06), 0, 1) * np.minimum(1.0, 0.08 / fpk) * 0.8)[..., None]
    land = land * (1 - beach) + C((0.44, 0.40, 0.31)) * beach
    deep = sstep(0.0, 4.0, s)[..., None]
    sea = C((0.085, 0.16, 0.18)) * (1 - deep) + C((0.040, 0.075, 0.115)) * deep
    swell = 0.9 + 0.2 * fbm(gx / 0.2, gy / 0.6, 4, fp / 0.2, seed=61)
    land = land * (1 - seacov) + sea * swell[..., None] * seacov
    # cloud shadows on the land
    sox, soy = math.cos(SUN_AZ) * H_CLOUD / math.tan(SUN_EL), math.sin(SUN_AZ) * H_CLOUD / math.tan(SUN_EL)
    def cden(x, y, f_):
        return fbm(x / 2.2, y / 2.2, 6, f_ / 2.2, seed=21) * 0.8 + fbm(x / 0.55 + 3.3, y / 0.55 - 1.7, 4, f_ / 0.55, seed=29) * 0.2
    THR = 0.575
    shad = sstep(THR - 0.02, THR + 0.14, cden(gx + sox, gy + soy, fp))
    land *= (1 - 0.30 * shad)[..., None]
    # aerial haze over the land (mostly in the low boundary layer)
    L = (H_ISL * 0.55 / sin_d)[:, None].astype(np.float32)
    hz = (1 - np.exp(-L / 14.0 - L / 80.0))[..., None]
    hc = horizon_rgb(np.broadcast_to(az[None, :], shp).astype(np.float32))
    hc_low = hc * 0.92
    out = land * (1 - hz) + hc_low * hz
    # the cloud layer between (above the haze)
    rc = (r_g * (H_ISL - H_CLOUD) / H_ISL)[:, None].astype(np.float32)
    cx = rc * ca.astype(np.float32); cy = rc * sa.astype(np.float32); fpc = fp * (H_ISL - H_CLOUD) / H_ISL
    den = cden(cx, cy, fpc)
    thr = THR + 0.035 * sstep(25.0, 70.0, rc)        # sparser far out
    soft = 0.08 + np.clip(fpc / 1.2, 0, 0.25)
    alpha = sstep(thr, thr + soft, den)
    den_s = cden(cx + math.cos(SUN_AZ) * 0.35, cy + math.sin(SUN_AZ) * 0.35, fpc)
    lit = np.clip(0.55 + (den - den_s) * 6.0, 0.0, 1.0)[..., None]
    thick = sstep(thr, thr + 0.22, den)[..., None]
    ccol = C((0.52, 0.57, 0.66)) * (1 - lit) + C((0.93, 0.92, 0.89)) * lit
    ccol = ccol * (1 - 0.12 * thick)
    Lc = ((H_ISL - H_CLOUD) / sin_d)[:, None].astype(np.float32)
    hzc = (1 - np.exp(-Lc / 22.0))[..., None]
    ccol = ccol * (1 - hzc) + hc * hzc
    a3 = alpha[..., None]
    out = out * (1 - a3) + ccol * a3
    # very near the horizon: everything goes into the haze; a faint range of mountains on the left horizon
    nearh = sstep(-1.2, 0.2, el)[:, None, None].astype(np.float32)
    out = out * (1 - nearh) + hc * nearh
    azd = np.degrees(np.broadcast_to(az[None, :], shp))
    ridge = 1.0 - np.abs(2.0 * fbm(azd / 7.0, np.zeros_like(azd) + 0.5, 5, 0.02 + np.zeros_like(azd), seed=70) - 1.0)
    e_top = -1.25 + 1.15 * ridge * sstep(-70.0, -45.0, azd) * sstep(-8.0, -28.0, azd)
    elb = np.broadcast_to(el[:, None], shp)
    mband = ((elb < e_top) & (elb > -2.8)).astype(np.float32) * sstep(-2.8, -1.8, elb) * sstep(-70.0, -45.0, azd) * sstep(-8.0, -28.0, azd)
    out = out * (1 - 0.22 * mband[..., None]) + C((0.36, 0.42, 0.55)) * (0.22 * mband[..., None])
    save_rgb(path, out.astype(np.float32))

LAND_VER, SKY_VER = "v5", "v4"
SKY_PNG = os.path.join(CACHE, f"sky_{SKY_VER}.png"); LAND_PNG = os.path.join(CACHE, f"land_{LAND_VER}.png")
if not os.path.exists(SKY_PNG): print("generating sky"); gen_sky(SKY_PNG)
if not os.path.exists(LAND_PNG): print("generating land (a minute)"); gen_land(LAND_PNG)

def dome_mat(name, png):
    """Emission only (black base): the render then shows exactly the colour Unity's unlit backdrop will show."""
    m, nt, b = new_mat(name)
    tex = node(nt, "ShaderNodeTexImage", (-400, 0)); tex.image = bpy.data.images.load(png); tex.extension = 'EXTEND'
    tex.interpolation = 'Cubic'
    nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0; b.inputs["Specular IOR Level"].default_value = 0.0
    return m
M_SKY = dome_mat("M_SkyDome", SKY_PNG)
M_LAND = dome_mat("M_Land", LAND_PNG)

def dome(name, mat, radius, az0, az1, els, vs, seg, pole):
    """An inward-facing sphere band: rings at elevations els (deg) with texture v's vs; azimuth az0..az1 (rad)."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    full = abs((az1 - az0) - 2 * math.pi) < 1e-6
    ncol = seg if full else seg + 1
    grid = []
    for el in els:
        e = math.radians(el)
        grid.append([bm.verts.new((radius * math.cos(e) * math.cos(az0 + (az1 - az0) * i / seg), radius * math.cos(e) * math.sin(az0 + (az1 - az0) * i / seg), radius * math.sin(e))) for i in range(ncol)])
    for j in range(len(els) - 1):
        for i in range(seg):
            k = (i + 1) % ncol if full else i + 1
            f_ = bm.faces.new((grid[j][i], grid[j][k], grid[j + 1][k], grid[j + 1][i]))
            for l, uv in zip(f_.loops, [(i / seg, vs[j]), ((i + 1) / seg, vs[j]), ((i + 1) / seg, vs[j + 1]), (i / seg, vs[j + 1])]):
                l[uvl].uv = uv
    pz = radius if pole > 0 else -radius
    pv = bm.verts.new((0, 0, pz)); vp = 1.0 if pole > 0 else 0.0
    for i in range(seg):
        k = (i + 1) % ncol if full else i + 1
        f_ = bm.faces.new((grid[-1][i], grid[-1][k], pv))
        for l, uv in zip(f_.loops, [(i / seg, vs[-1]), ((i + 1) / seg, vs[-1]), ((i + 0.5) / seg, vp)]):
            l[uvl].uv = uv
    bm.normal_update()
    for f_ in bm.faces:
        if f_.normal.dot(f_.calc_center_median()) > 0: f_.normal_flip()
    o = _obj(name, bm, mat, smooth=True)
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False; o.visible_transmission = False; o.visible_volume_scatter = False
    return o
NR = 18; sky_els = [SKY_EL0 + (89.0 - SKY_EL0) * (j / NR) ** 1.2 for j in range(NR + 1)]
dome("SkyDome", M_SKY, SKY_R, -math.pi, math.pi, sky_els, [(e - SKY_EL0) / (90.0 - SKY_EL0) for e in sky_els], 48, +1)
NL = 26; land_ts = [j / NL for j in range(NL)]
dome("far.Land", M_LAND, LAND_R, LAND_AZ0, LAND_AZ1, [land_el(t) for t in land_ts], [1.0 - t for t in land_ts], 56, -1)

# ----------------------------------------------------------------------------- anchors
LOOK = (0.0, -2.0, 1.55)
anchor("reader.entrance", (0.0, 0.0, 0.0))            # the reader stands here, in the belvedere, facing -Y (out over the rim)
anchor("reader.look", LOOK)                           # eye height, straight out over the void
anchor("scene.centre", (0.0, 2.7, 0.0))
anchor("gallery.stair.up", (STAIR_UP[0] + 0.3, G0_BACK - 0.65, 0.0))
anchor("gallery.stair.down", (STAIR_A[0] + 0.7, G0_EDGE - 0.65, 0.0))
anchor("gallery.davit", (DV.x, DV.y, DV.z))
anchor("gallery.telescope", (TEL.x, TEL.y, 1.17))
anchor("gallery.orange.tree", (OT.x, OT.y, 0.0))
anchor("tower.left", (HX, 2.75, 0.0))
anchor("tower.right", (-HX, 2.75, 0.0))
anchor("land.lagado", (0.0, -40.0, -30.0))

# ----------------------------------------------------------------------------- lights: mid-morning sun, cool sky fill, light thrown up from below
def light_obj(name, kind, energy, color, loc, direction=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if direction is not None: lo.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return link(lo)
sun = light_obj("light.sun", 'SUN', 3.6, (1.0, 0.93, 0.80), tuple(SUN_DIR * 30), direction=-SUN_DIR, angle=math.radians(1.2))
sky_l = light_obj("light.sky", 'SUN', 0.30, (0.70, 0.80, 1.0), (0, 0, 30), direction=(-0.15, 0.25, -1.0), angle=math.radians(70))
sky_l.data.use_shadow = False
bounce = light_obj("light.bounce", 'SUN', 0.30, (0.86, 0.88, 0.92), (0, -10, -20), direction=(0.1, 0.3, 1.0), angle=math.radians(80))
bounce.data.use_shadow = False

# world: physical sky for render only (the glTF carries the SkyDome and far.Land meshes for Unity instead)
world = bpy.data.worlds.new("Laputa"); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]
try:
    skyn = wn.nodes.new("ShaderNodeTexSky")
    skyn.sky_type = 'MULTIPLE_SCATTERING'
    skyn.sun_disc = False
    skyn.sun_elevation = SUN_EL
    skyn.sun_rotation = math.atan2(SUN_DIR.x, SUN_DIR.y)
    skyn.altitude = 3200
    wtc = wn.nodes.new("ShaderNodeTexCoord"); wsep = wn.nodes.new("ShaderNodeSeparateXYZ"); wn.links.new(wtc.outputs["Generated"], wsep.inputs[0])
    below = map_range(wn, wsep.outputs["Z"], 0.02, -0.15, 0.0, 1.0)
    wmix = wn.nodes.new("ShaderNodeMix"); wmix.data_type = 'RGBA'
    wn.links.new(below, wmix.inputs["Factor"]); wn.links.new(skyn.outputs["Color"], wmix.inputs[6]); wmix.inputs[7].default_value = (0.012, 0.013, 0.015, 1)
    wn.links.new(wmix.outputs[2], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.14
except Exception as e:
    print("sky texture unavailable:", e)
    bg.inputs["Color"].default_value = (0.45, 0.6, 0.85, 1); bg.inputs["Strength"].default_value = 0.8

# apply every transform so object space == world space (the world-space materials then bake exactly as rendered)
bpy.ops.object.select_all(action='DESELECT')
for o in COLL.objects:
    if o.type == 'MESH': o.select_set(True); bpy.context.view_layer.objects.active = o
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.select_all(action='DESELECT')

# ----------------------------------------------------------------------------- cameras for preview stills (reader eye 1.55 m)
def camera(name, loc, look_at, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 150; cd.clip_start = 0.05
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co
E = (0.0, 0.0, 1.55)
cams = [
    camera("Cam_Reader", E, (0.0, -8.0, 0.7), lens=16),
    camera("Cam_Page", E, (0.0, -8.0, 1.45), lens=50),
    camera("Cam_Left", E, (10.0, -3.0, 0.2), lens=16),
    camera("Cam_Right", E, (-10.0, -3.0, 0.2), lens=16),
    camera("Cam_Behind", E, (0.0, 8.0, 4.0), lens=16),
    camera("Cam_Down", E, (0.6, -0.9, 0.0), lens=18),
    camera("Cam_Lean", (0.1, -1.35, 1.40), (-1.5, -6.5, -8.5), lens=16),
    camera("Cam_Outside", (-16.0, -48.0, -6.0), (2.0, 0.0, -3.0), lens=24),
]
CAM_EXPOSURE = {}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "laputa_source.blend"))

# pre-export stats (printed every run so the budget is visible while iterating)
def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)
_m = [o for o in COLL.objects if o.type == 'MESH']
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
        scene.view_settings.exposure = CAM_EXPOSURE.get(c.name, 0.0)
        scene.render.filepath = os.path.join(OUT, f"{args.prefix}{c.name[4:].lower()}.png")
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:                                  # GPU busy/out of memory (other renders in parallel): fall back to CPU
            print("GPU render failed, retrying on CPU:", str(e)[:120]); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)
    scene.view_settings.exposure = 0.0

# ----------------------------------------------------------------------------- bake + merge + export for Unity
FAR_MATS = {"M_SkyDome": "SkyDome", "M_Land": "far.Land"}
PREBAKED = {"M_SkyDome": SKY_PNG, "M_Land": LAND_PNG}     # backdrops: their generated image is already the base texture

def bake_and_export():
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')                       # apply modifiers everywhere
    bpy.ops.object.select_all(action='DESELECT')
    for e in [o for o in COLL.objects if o.type == 'EMPTY' and not o.name.startswith("anchor.")]:
        bpy.data.objects.remove(e)
    # static meshes merged by material
    groups = {}
    for o in COLL.objects:
        if o.type != 'MESH' or not o.data.materials: continue
        groups.setdefault(o.data.materials[0].name, []).append(o)
    merged = []
    for mname, objs in groups.items():
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active
        o.name = FAR_MATS.get(mname, "MESH_" + mname[2:])
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    scene.cycles.samples = 16
    scene.cycles.device = 'CPU'     # Metal under memory pressure (parallel renders) can return black bakes without raising
    scene.render.bake.margin = 6
    scene.render.bake.use_selected_to_active = False
    T = args.tex
    size_for = {"M_PavingNear": T, "M_StoneNear": T, "M_Balusters": T, "M_Stone": T, "M_Paving": T, "M_StoneFar": T, "M_Adamant": T,
                "M_Leaves": T // 2, "M_TreeFoliage": T // 2, "M_Grass": T // 4, "M_WallPlants": T // 4, "M_Garden": T // 4, "M_Bark": T // 4,
                "M_Iron": T // 4, "M_Brass": T // 4, "M_Wood": T // 8, "M_Soil": T // 8, "M_Flowers": T // 8, "M_Fruit": T // 16,
                "M_Litter": T // 8, "M_Doorways": T // 16}
    bakedir = os.path.join(OUT, "bake_png"); os.makedirs(bakedir, exist_ok=True)

    def bake_object(o, label, size):
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
        bpy.ops.object.mode_set(mode='OBJECT')
        m = o.data.materials[0]; nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        metallic = bsdf.inputs["Metallic"].default_value
        imgs = {}
        for pass_name, btype, extra, noncolor in [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]:
            img = bpy.data.images.new(f"T_{label}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            for n in nt.nodes: n.select = False
            tex.select = True; nt.nodes.active = tex
            # a DIFFUSE colour bake returns black for metal: bake the albedo with Metallic at 0 (restored below)
            bsdf.inputs["Metallic"].default_value = 0.0 if pass_name == "BaseColor" else metallic
            try:
                bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            except RuntimeError as e:
                print("GPU bake failed, retrying on CPU:", str(e)[:120]); scene.cycles.device = 'CPU'
                bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            if pass_name == "BaseColor":
                _px = np.empty(size * size * 4, np.float32); img.pixels.foreach_get(_px)
                if float(_px.reshape(-1, 4)[:, :3].max()) < 0.01: raise RuntimeError(f"blank bake for {label}")
            img.filepath_raw = os.path.join(bakedir, img.name + ".png"); img.file_format = 'PNG'; img.save(); img.pack()
            imgs[pass_name] = img
            print("baked", img.name, size, flush=True)
        bm_ = bpy.data.materials.new("M_" + label); bm_.use_nodes = True; nt2 = bm_.node_tree
        for n in list(nt2.nodes): nt2.nodes.remove(n)
        out = nt2.nodes.new("ShaderNodeOutputMaterial"); nb = nt2.nodes.new("ShaderNodeBsdfPrincipled")
        nt2.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
        tb = nt2.nodes.new("ShaderNodeTexImage"); tb.image = imgs["BaseColor"]
        tr = nt2.nodes.new("ShaderNodeTexImage"); tr.image = imgs["Roughness"]
        tn = nt2.nodes.new("ShaderNodeTexImage"); tn.image = imgs["Normal"]
        nt2.links.new(tb.outputs["Color"], nb.inputs["Base Color"]); nt2.links.new(tr.outputs["Color"], nb.inputs["Roughness"])
        nmap = nt2.nodes.new("ShaderNodeNormalMap"); nt2.links.new(tn.outputs["Color"], nmap.inputs["Color"]); nt2.links.new(nmap.outputs["Normal"], nb.inputs["Normal"])
        nb.inputs["Metallic"].default_value = metallic
        o.data.materials.clear(); o.data.materials.append(bm_)
        for p in o.data.polygons: p.material_index = 0

    def backdrop_object(o, label, png):
        """SkyDome / far.Land keep their own UVs; the generated image is the base (and emission) texture."""
        img = bpy.data.images.load(png); img.name = f"T_{label}_BaseColor"; img.pack()
        bm_ = bpy.data.materials.new("M_" + label); bm_.use_nodes = True; nt2 = bm_.node_tree
        for n in list(nt2.nodes): nt2.nodes.remove(n)
        out = nt2.nodes.new("ShaderNodeOutputMaterial"); nb = nt2.nodes.new("ShaderNodeBsdfPrincipled")
        nt2.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
        tb = nt2.nodes.new("ShaderNodeTexImage"); tb.image = img
        nt2.links.new(tb.outputs["Color"], nb.inputs["Base Color"]); nt2.links.new(tb.outputs["Color"], nb.inputs["Emission Color"])
        nb.inputs["Emission Strength"].default_value = 1.0; nb.inputs["Roughness"].default_value = 1.0
        o.data.materials.clear(); o.data.materials.append(bm_)

    for o in merged:
        base = o.data.materials[0].name
        if base in PREBAKED: backdrop_object(o, base[2:], PREBAKED[base])
        else: bake_object(o, base[2:], max(64, size_for.get(base, T // 4)))
    for c in [o for o in COLL.objects if o.type == 'CAMERA']: bpy.data.objects.remove(c)
    gl = os.path.join(OUT, "laputa.gltf")   # .gltf + textures/: Unity imports the images as compressed (ASTC) textures
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False)
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            img = next((n.image for n in o.data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE'), None)
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={img.size[0] if img else 0}x{img.size[1] if img else 0}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "laputa_baked.blend"))

if args.bake or args.export:
    bake_and_export()
print("DONE")
