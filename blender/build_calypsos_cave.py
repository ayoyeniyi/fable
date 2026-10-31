"""
Fable: Calypso's cave on Ogygia (The Odyssey, Book V, Samuel Butler's 1900 prose translation).

"He found her at home. There was a large fire burning on the hearth, and one could smell from far
the fragrant reek of burning cedar and sandal wood. As for herself, she was busy at her loom,
shooting her golden shuttle through the warp and singing beautifully. Round her cave there was a
thick wood of alder, poplar, and sweet smelling cypress trees, wherein all kinds of great birds had
built their nests—owls, hawks, and chattering sea-crows that occupy their business in the waters.
A vine loaded with grapes was trained and grew luxuriantly about the mouth of the cave; there were
also four running rills of water in channels cut pretty close together, and turned hither and
thither so as to irrigate the beds of violets and luscious herbage over which they flowed."
"... he was on the sea-shore as usual, looking out upon the barren ocean ..."

No people: the loom stands with the golden shuttle resting in the warp, the fire burns on the hearth,
the vine hangs about the mouth, four rills run through the violet beds, the grove stands round the
cave and the sea lies beyond. Everything is procedural (no downloaded models, textures or HDRIs).

Builds the environment in Blender with PBR node materials and Mediterranean daylight (sun + sky),
then (by flag) renders Cycles stills, bakes materials to textures, merges static meshes by
material and exports .gltf + .bin + textures/ for Unity.

Node naming: anchors are empties "anchor.<id>" (anchor.reader.entrance, anchor.reader.look,
anchor.scene.centre, ...); lights "light.sun", "light.sky" (both SUN) and "Fire_Light" (POINT).
The sky is the mesh "SkyDome"; far scenery is "far.*" / "*FarTrees*"; the flame is "MESH_Flame".

Axes: metres, Blender +Z up. The reader stands at anchor.reader.entrance (world origin, just inside
the mouth) facing Blender -Y (out of the cave to the sea), which glTFast imports as Unity +Z.
The page volume (x within +-0.6, y about -1.15, z 0.8..1.8) is kept clear.

Run headless:
  blender -b -P blender/build_calypsos_cave.py -- --out out/calypsos-cave --render --quick --res 1200
  blender -b -P blender/build_calypsos_cave.py -- --out out/calypsos-cave --render --samples 160 --res 1600
  blender -b -P blender/build_calypsos_cave.py -- --out out/calypsos-cave --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, Euler, noise

# ----------------------------------------------------------------------------- args
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/calypsos-cave")
ap.add_argument("--render", action="store_true")
ap.add_argument("--bake", action="store_true")
ap.add_argument("--export", action="store_true")
ap.add_argument("--samples", type=int, default=160)
ap.add_argument("--res", type=int, default=1600)
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--quick", action="store_true", help="low samples for iteration")
ap.add_argument("--cams", default="", help="comma list of camera names to render (default all)")
args = ap.parse_args(argv)
OUT = os.path.abspath(args.out)
os.makedirs(OUT, exist_ok=True)
random.seed(1900)

# ----------------------------------------------------------------------------- dimensions (metres)
CAVE_C = Vector((0.0, 2.3, 0.0))       # centre of the cave chamber (floor level)
CAVE_R = (3.9, 4.1, 3.7)               # chamber radii x (across), y (deep), z (height)
FRONT_Y = -1.0                         # inner face of the rock at the mouth
WALL_T = 0.7                           # rock thickness: the mouth is a short tunnel from y=-1.0 to -1.7
MOUTH_W, MOUTH_H = 3.6, 2.85           # the opening (base width, crown height)
MOUTH_C = Vector((0.0, -1.35, 1.4))
OUTER_Y = FRONT_Y - WALL_T             # outer cliff face
VINE_Y = OUTER_Y - 0.25
SEA_Z = -4.5
HEARTH = Vector((2.3, 1.9, 0.0))       # inside, to the reader's left when looking out
LOOM = Vector((-2.25, 1.55, 0.0))      # inside, to the reader's right when looking out
SPRING = Vector((-2.35, -2.55, 0.0))   # the rills rise beside the mouth
SUN_DIR = Vector((-0.50, -0.45, 0.74)).normalized()   # towards the sun: high, over the sea, shining into the mouth

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
scene.cycles.max_bounces = 8
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
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 0.0

COLL = bpy.data.collections.new("CalypsosCave")
scene.collection.children.link(COLL)
def link(obj):
    COLL.objects.link(obj); return obj

# ----------------------------------------------------------------------------- material helpers (from build_lobby.py / build_mad_tea_party.py)
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
    """Object coords (per-object patterns) or world position (patterns that depend on where things are).
    World position survives the merge-by-material before baking; object coords change with it, which only
    re-seeds noise, so anything position-dependent (sand line, smoke, sea depth, flame heat) uses world."""
    if world:
        g = node(nt, "ShaderNodeNewGeometry", loc); mp = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
        nt.links.new(g.outputs["Position"], mp.inputs["Vector"]); return mp
    tc = node(nt, "ShaderNodeTexCoord", loc); mp = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); return mp

def bump_from(nt, b, height_socket, strength, distance):
    bump = node(nt, "ShaderNodeBump", (50, -300)); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return bump

def mix_rgb(nt, a, b_, fac, blend='MIX', loc=(0, 0)):
    """a, b_: sockets or RGBA tuples; fac: socket or float."""
    mx = node(nt, "ShaderNodeMix", loc, data_type='RGBA', blend_type=blend)
    if isinstance(fac, (int, float)): mx.inputs["Factor"].default_value = fac
    else: nt.links.new(fac, mx.inputs["Factor"])
    for sock, v in ((mx.inputs[6], a), (mx.inputs[7], b_)):
        if isinstance(v, tuple): sock.default_value = v
        else: nt.links.new(v, sock)
    return mx.outputs[2]

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

def noisy(name, colors, scale=8.0, rough=0.8, bump=0.2, bump_dist=0.003, detail=6.0, stretch=(1, 1, 1), sheen=0.0, sss=0.0, coat=0.0, metallic=0.0, warp=0.0):
    """Generic organic surface: a colour ramp over fractal noise in object space, with bump."""
    m, nt, b = new_mat(name)
    mp = coords(nt); mp.inputs["Scale"].default_value = stretch
    n = noise_tex(nt, mp.outputs["Vector"], scale, detail, 0.6, warp)
    stops = [(i / max(1, len(colors) - 1) * 0.6 + 0.2, c4(c)) for i, c in enumerate(colors)]
    r = ramp(nt, stops, (-700, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if sheen: b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.4
    if sss: b.inputs["Subsurface Weight"].default_value = sss; b.inputs["Subsurface Radius"].default_value = (0.4, 0.2, 0.12)
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.08
    if bump:
        fine = noise_tex(nt, mp.outputs["Vector"], scale * 6, 4, loc=(-1000, -350))
        bump_from(nt, b, fine.outputs["Fac"], bump, bump_dist)
    return m

def plain(name, color, rough=0.5, metallic=0.0, emission=None, strength=0.0, coat=0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = c4(color); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if emission: b.inputs["Emission Color"].default_value = c4(emission); b.inputs["Emission Strength"].default_value = strength
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.05
    return m

def wood(name, base=(0.32, 0.17, 0.08), dark=(0.09, 0.045, 0.02), light=(0.55, 0.33, 0.15), scale=1.0, rough=(0.4, 0.7), grain_dir=(1, 1, 14), bands='Z'):
    m, nt, b = new_mat(name)
    mp = coords(nt); mp.inputs["Scale"].default_value = tuple(g * scale for g in grain_dir)
    wave = node(nt, "ShaderNodeTexWave", (-1000, 200), wave_type='BANDS', bands_direction=bands)
    wave.inputs["Scale"].default_value = 1.2; wave.inputs["Distortion"].default_value = 9.0
    wave.inputs["Detail"].default_value = 6.0; wave.inputs["Detail Scale"].default_value = 1.5
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    fine = noise_tex(nt, mp.outputs["Vector"], 60.0 * scale, 8.0, 0.7, loc=(-1000, -150))
    mix = node(nt, "ShaderNodeMix", (-700, 100), data_type='FLOAT'); mix.inputs["Factor"].default_value = 0.22
    nt.links.new(wave.outputs["Fac"], mix.inputs[2]); nt.links.new(fine.outputs["Fac"], mix.inputs[3])
    mid = tuple((x + y) / 2 for x, y in zip(base, light)); lite = tuple((x + y) / 2 for x, y in zip(mid, light))
    r = ramp(nt, [(0.0, c4(dark)), (0.2, c4(base)), (0.5, c4(mid)), (0.72, c4(lite)), (0.9, c4(base))], (-450, 100))
    nt.links.new(mix.outputs[0], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    rr = map_range(nt, wave.outputs["Fac"], 0, 1, rough[1], rough[0], (-150, -200)); nt.links.new(rr, b.inputs["Roughness"])
    bump_from(nt, b, mix.outputs[0], 0.4, 0.003)
    return m

def rock(name, colors=((0.22, 0.20, 0.17), (0.36, 0.33, 0.28), (0.48, 0.45, 0.39)), scale=1.0, smoke=False, ao=True, bumpk=0.8):
    """Limestone: fractal noise and strata, fine dark fissures, rain/seep streaks, baked AO, soot above the hearth."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    n = noise_tex(nt, mp.outputs["Vector"], 1.4 * scale, 12, 0.66, 0.5, (-1000, 300))
    strata = node(nt, "ShaderNodeTexWave", (-1000, 0), wave_type='BANDS', bands_direction='Z')
    strata.inputs["Scale"].default_value = 0.8 * scale; strata.inputs["Distortion"].default_value = 2.5; strata.inputs["Detail"].default_value = 3
    strata.inputs["Detail Scale"].default_value = 2.0
    nt.links.new(mp.outputs["Vector"], strata.inputs["Vector"])
    # fissures: voronoi edges, warped by noise so they wander rather than tile
    warp = noise_tex(nt, mp.outputs["Vector"], 2.0 * scale, 3, 0.5, loc=(-1300, -300))
    wv = node(nt, "ShaderNodeMix", (-1150, -300), data_type='VECTOR'); wv.inputs["Factor"].default_value = 0.35
    nt.links.new(mp.outputs["Vector"], wv.inputs[4]); nt.links.new(warp.outputs["Color"], wv.inputs[5])
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, -300), feature='DISTANCE_TO_EDGE'); v.inputs["Scale"].default_value = 3.2 * scale
    nt.links.new(wv.outputs[1], v.inputs["Vector"])
    fac = node(nt, "ShaderNodeMix", (-750, 200), data_type='FLOAT'); fac.inputs["Factor"].default_value = 0.12
    nt.links.new(n.outputs["Fac"], fac.inputs[2]); nt.links.new(strata.outputs["Fac"], fac.inputs[3])
    r = ramp(nt, [(0.3, c4(colors[0])), (0.5, c4(colors[1])), (0.7, c4(colors[2]))], (-550, 200))
    nt.links.new(fac.outputs[0], r.inputs["Fac"])
    # large patches: warm ochre staining against cool grey stone
    pn = noise_tex(nt, mp.outputs["Vector"], 0.3 * scale, 3, 0.5, loc=(-1000, 550))
    pr = ramp(nt, [(0.4, (1.08, 0.96, 0.80, 1)), (0.6, (0.88, 0.90, 0.92, 1))], (-750, 550)); nt.links.new(pn.outputs["Fac"], pr.inputs["Fac"])
    base = mix_rgb(nt, r.outputs["Color"], pr.outputs["Color"], 1.0, 'MULTIPLY', (-400, 350))
    crack = ramp(nt, [(0.0, (0.45, 0.42, 0.38, 1)), (0.01, (0.8, 0.78, 0.74, 1)), (0.025, (1, 1, 1, 1))], (-550, -250))
    nt.links.new(v.outputs["Distance"], crack.inputs["Fac"])
    col = mix_rgb(nt, base, crack.outputs["Color"], 0.6, 'MULTIPLY', (-300, 100))
    # vertical seep streaks
    st_map = node(nt, "ShaderNodeMapping", (-1200, -600)); st_map.inputs["Scale"].default_value = (5.0, 5.0, 0.35)
    nt.links.new(mp.outputs["Vector"], st_map.inputs["Vector"])
    st = noise_tex(nt, st_map.outputs["Vector"], 1.5 * scale, 4, 0.5, loc=(-1000, -600))
    str_ = ramp(nt, [(0.5, (1, 1, 1, 1)), (0.72, (0.82, 0.80, 0.76, 1))], (-750, -600)); nt.links.new(st.outputs["Fac"], str_.inputs["Fac"])
    col = mix_rgb(nt, col, str_.outputs["Color"], 1.0, 'MULTIPLY', (-200, 100))
    if ao:
        a = node(nt, "ShaderNodeAmbientOcclusion", (-550, -800)); a.inputs["Distance"].default_value = 0.9; a.samples = 16
        aor = ramp(nt, [(0.0, (0.3, 0.28, 0.26, 1)), (1.0, (1, 1, 1, 1))], (-350, -800))
        nt.links.new(a.outputs["AO"], aor.inputs["Fac"])
        col = mix_rgb(nt, col, aor.outputs["Color"], 1.0, 'MULTIPLY', (-100, 100))
    if smoke:
        # soot on the vault above the hearth, fading with distance from the smoke's path
        g = node(nt, "ShaderNodeNewGeometry", (-900, -1050))
        dv = node(nt, "ShaderNodeVectorMath", (-700, -1050), operation='DISTANCE'); dv.inputs[1].default_value = (HEARTH.x * 0.85, HEARTH.y, 3.3)
        nt.links.new(g.outputs["Position"], dv.inputs[0])
        sm = map_range(nt, dv.outputs["Value"], 0.6, 2.8, 0.85, 0.0, (-500, -1050))
        sn = noise_tex(nt, mp.outputs["Vector"], 2.5, 4, loc=(-700, -1250))
        smn = math_n(nt, 'MULTIPLY', sm, sn.outputs["Fac"], (-350, -1100)); smn = math_n(nt, 'MULTIPLY', smn, 1.6, (-250, -1100))
        smn = math_n(nt, 'MINIMUM', smn, 0.92, (-150, -1100))
        col = mix_rgb(nt, col, (0.035, 0.03, 0.028, 1), smn, 'MIX', (0, 100))
    nt.links.new(col, b.inputs["Base Color"])
    rr = map_range(nt, n.outputs["Fac"], 0.3, 0.7, 0.95, 0.75, (-150, -300)); nt.links.new(rr, b.inputs["Roughness"])
    h = math_n(nt, 'MULTIPLY_ADD', v.outputs["Distance"], 0.5, (-300, -350)); nt.links.new(n.outputs["Fac"], h.node.inputs[2])
    bump_from(nt, b, h, bumpk, 0.05)
    return m

def leaves(name, tint, light, scale=14.0, sss=0.15):
    m, nt, b = new_mat(name)
    mp = coords(nt)
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 200)); v.inputs["Scale"].default_value = scale; v.inputs["Randomness"].default_value = 1
    nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    n = noise_tex(nt, mp.outputs["Vector"], 1.2, 3, loc=(-1000, -150))
    mx = node(nt, "ShaderNodeMix", (-700, 150), data_type='FLOAT'); mx.inputs["Factor"].default_value = 0.5
    nt.links.new(v.outputs["Color"], mx.inputs[2]); nt.links.new(n.outputs["Fac"], mx.inputs[3])
    r = ramp(nt, [(0.2, c4(scaled(tint, 0.55))), (0.5, c4(tint)), (0.8, c4(light))], (-450, 150))
    nt.links.new(mx.outputs[0], r.inputs["Fac"])
    a = node(nt, "ShaderNodeAmbientOcclusion", (-450, -150)); a.inputs["Distance"].default_value = 0.4
    aor = ramp(nt, [(0.0, (0.4, 0.42, 0.38, 1)), (1.0, (1, 1, 1, 1))], (-250, -150)); nt.links.new(a.outputs["AO"], aor.inputs["Fac"])
    nt.links.new(mix_rgb(nt, r.outputs["Color"], aor.outputs["Color"], 1.0, 'MULTIPLY', (-100, 150)), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    b.inputs["Subsurface Weight"].default_value = sss; b.inputs["Subsurface Radius"].default_value = (0.2, 0.4, 0.1)
    b.inputs["Sheen Weight"].default_value = 0.3
    inv = math_n(nt, 'SUBTRACT', 1.0, v.outputs["Distance"], (-400, -350))
    bump_from(nt, b, inv, 0.8, 0.03)
    return m

def bark(name, crack_col=(0.03, 0.022, 0.016), mid=(0.16, 0.12, 0.085), top=(0.30, 0.24, 0.17), stretch=(9, 9, 0.7)):
    m, nt, b = new_mat(name)
    mp = coords(nt); mp.inputs["Scale"].default_value = stretch
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 200), feature='DISTANCE_TO_EDGE'); v.inputs["Scale"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    n = noise_tex(nt, mp.outputs["Vector"], 6, 8, 0.6, 1.5, (-1000, -150))
    crack = ramp(nt, [(0.0, c4(crack_col)), (0.06, c4(mid)), (0.3, c4(top))], (-700, 200))
    nt.links.new(v.outputs["Distance"], crack.inputs["Fac"])
    moss = ramp(nt, [(0.55, (1, 1, 1, 1)), (0.75, (0.55, 0.6, 0.4, 1))], (-700, -150)); nt.links.new(n.outputs["Fac"], moss.inputs["Fac"])
    nt.links.new(mix_rgb(nt, crack.outputs["Color"], moss.outputs["Color"], 0.8, 'MULTIPLY', (-350, 200)), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.92
    h = math_n(nt, 'MULTIPLY_ADD', v.outputs["Distance"], 0.6, (-350, -300)); nt.links.new(n.outputs["Fac"], h.node.inputs[2])
    bump_from(nt, b, h, 0.9, 0.02)
    return m

def ground_mat(name="M_Ground"):
    """Island ground: dry Mediterranean grass and earth, greener on the watered terrace, rock on steep
    banks, sand at the shore (world height), so the baked texture follows the terrain."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    big = noise_tex(nt, mp.outputs["Vector"], 0.09, 4, loc=(-1000, 400))
    mid = noise_tex(nt, mp.outputs["Vector"], 1.4, 8, 0.65, loc=(-1000, 150))
    blades = node(nt, "ShaderNodeTexVoronoi", (-1000, -100)); blades.inputs["Scale"].default_value = 55
    nt.links.new(mp.outputs["Vector"], blades.inputs["Vector"])
    mx = node(nt, "ShaderNodeMix", (-750, 300), data_type='FLOAT'); mx.inputs["Factor"].default_value = 0.45
    nt.links.new(big.outputs["Fac"], mx.inputs[2]); nt.links.new(mid.outputs["Fac"], mx.inputs[3])
    dry = ramp(nt, [(0.28, (0.10, 0.10, 0.04, 1)), (0.42, (0.20, 0.18, 0.08, 1)), (0.56, (0.32, 0.26, 0.12, 1)), (0.7, (0.27, 0.19, 0.10, 1))], (-550, 300))
    nt.links.new(mx.outputs[0], dry.inputs["Fac"])
    lush = ramp(nt, [(0.3, (0.035, 0.07, 0.02, 1)), (0.5, (0.07, 0.12, 0.03, 1)), (0.66, (0.13, 0.16, 0.05, 1)), (0.8, (0.22, 0.19, 0.09, 1))], (-550, 100))
    nt.links.new(mx.outputs[0], lush.inputs["Fac"])
    # watered terrace in front of the cave
    g = node(nt, "ShaderNodeNewGeometry", (-1200, -400))
    dv = node(nt, "ShaderNodeVectorMath", (-1000, -400), operation='DISTANCE'); dv.inputs[1].default_value = (0.0, -6.0, 0.0)
    nt.links.new(g.outputs["Position"], dv.inputs[0])
    wet = map_range(nt, dv.outputs["Value"], 3.5, 8.5, 0.85, 0.0, (-800, -400))
    col = mix_rgb(nt, dry.outputs["Color"], lush.outputs["Color"], wet, 'MIX', (-300, 300))
    br = ramp(nt, [(0.0, (0.45, 0.46, 0.4, 1)), (0.7, (1, 1, 1, 1))], (-700, -100)); nt.links.new(blades.outputs["Distance"], br.inputs["Fac"])
    col = mix_rgb(nt, col, br.outputs["Color"], 0.6, 'MULTIPLY', (-150, 300))
    # rock on steep slopes
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1000, -650)); nt.links.new(g.outputs["Normal"], sep.inputs["Vector"])
    steep = map_range(nt, sep.outputs["Z"], 0.86, 0.68, 0.0, 1.0, (-800, -650))
    rk = ramp(nt, [(0.3, (0.30, 0.27, 0.21, 1)), (0.7, (0.52, 0.47, 0.38, 1))], (-550, -650)); nt.links.new(mid.outputs["Fac"], rk.inputs["Fac"])
    col = mix_rgb(nt, col, rk.outputs["Color"], steep, 'MIX', (0, 300))
    # sand at the shore
    sz = node(nt, "ShaderNodeSeparateXYZ", (-1000, -900)); nt.links.new(g.outputs["Position"], sz.inputs["Vector"])
    sandf = map_range(nt, sz.outputs["Z"], SEA_Z + 1.4, SEA_Z + 0.6, 0.0, 1.0, (-800, -900))
    sand = ramp(nt, [(0.3, (0.52, 0.45, 0.33, 1)), (0.7, (0.68, 0.61, 0.47, 1))], (-550, -900)); nt.links.new(mid.outputs["Fac"], sand.inputs["Fac"])
    col = mix_rgb(nt, col, sand.outputs["Color"], sandf, 'MIX', (150, 300))
    wetsand = map_range(nt, sz.outputs["Z"], SEA_Z + 0.35, SEA_Z - 0.1, 0.0, 0.55, (-800, -1100))
    col = mix_rgb(nt, col, (0.22, 0.19, 0.14, 1), wetsand, 'MIX', (300, 300))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
    bump_from(nt, b, blades.outputs["Distance"], 0.5, 0.01)
    return m

def sea_mat(name, r0, r1, near, far, rough=0.08):
    """Sea surface coloured by distance from the cave (world), wave normals from stretched noise."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1100, 300)); nt.links.new(mp.outputs["Vector"], sep.inputs["Vector"])
    cx = node(nt, "ShaderNodeCombineXYZ", (-950, 300)); nt.links.new(sep.outputs["X"], cx.inputs["X"]); nt.links.new(sep.outputs["Y"], cx.inputs["Y"])
    ln = node(nt, "ShaderNodeVectorMath", (-800, 300), operation='LENGTH'); nt.links.new(cx.outputs["Vector"], ln.inputs[0])
    d = map_range(nt, ln.outputs["Value"], r0, r1, 0, 1, (-650, 300))
    r = ramp(nt, [(0.0, c4(near)), (1.0, c4(far))], (-450, 300)); nt.links.new(d, r.inputs["Fac"])
    wv = node(nt, "ShaderNodeMapping", (-1000, -200)); wv.inputs["Scale"].default_value = (1.0, 3.5, 1.0)
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    w = noise_tex(nt, wv.outputs["Vector"], 1.1, 6, 0.55, 0.3, (-800, -200))
    shade = ramp(nt, [(0.3, (0.82, 0.86, 0.9, 1)), (0.7, (1.08, 1.06, 1.02, 1))], (-550, -200)); nt.links.new(w.outputs["Fac"], shade.inputs["Fac"])
    nt.links.new(mix_rgb(nt, r.outputs["Color"], shade.outputs["Color"], 1.0, 'MULTIPLY', (-200, 300)), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.3
    bump_from(nt, b, w.outputs["Fac"], 0.25, 0.08)
    return m

def sky_dome_mat(name="M_SkyDome", radius=58.0):
    m, nt, b = new_mat(name)
    g = node(nt, "ShaderNodeNewGeometry", (-1000, 0))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-800, 0)); nt.links.new(g.outputs["Position"], sep.inputs["Vector"])
    nrm = math_n(nt, 'DIVIDE', sep.outputs["Z"], radius, (-600, 0))
    r = ramp(nt, [(0.0, (0.72, 0.80, 0.86, 1)), (0.04, (0.56, 0.70, 0.88, 1)), (0.16, (0.32, 0.52, 0.84, 1)), (0.45, (0.17, 0.36, 0.76, 1)), (1.0, (0.09, 0.24, 0.62, 1))], (-400, 0))
    nt.links.new(nrm, r.inputs["Fac"])
    cmap = node(nt, "ShaderNodeMapping", (-800, -300)); cmap.inputs["Scale"].default_value = (1.0, 1.0, 3.0)
    nt.links.new(g.outputs["Position"], cmap.inputs["Vector"])
    cl = noise_tex(nt, cmap.outputs["Vector"], 0.05, 6, 0.55, loc=(-650, -300))
    cr = ramp(nt, [(0.60, (0, 0, 0, 1)), (0.76, (1, 1, 1, 1))], (-450, -300)); nt.links.new(cl.outputs["Fac"], cr.inputs["Fac"])
    hi = map_range(nt, sep.outputs["Z"], 3.0, 14.0, 0.0, 0.8, (-450, -500))       # no clouds at the horizon line
    cf = math_n(nt, 'MULTIPLY', cr.outputs["Color"], hi, (-250, -300))
    col = mix_rgb(nt, r.outputs["Color"], (0.96, 0.95, 0.92, 1), cf, 'MIX', (-150, 0))
    nt.links.new(col, b.inputs["Base Color"]); nt.links.new(col, b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m

def flame_mat(name="M_Flame"):
    """Emissive flame: white-gold at the root, orange then red at the tips (world height above the hearth)."""
    m, nt, b = new_mat(name)
    g = node(nt, "ShaderNodeNewGeometry", (-900, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-700, 0))
    nt.links.new(g.outputs["Position"], sep.inputs["Vector"])
    t = map_range(nt, sep.outputs["Z"], 0.06, 0.72, 0, 1, (-500, 0))
    r = ramp(nt, [(0.0, (1.0, 0.86, 0.52, 1)), (0.35, (1.0, 0.58, 0.14, 1)), (0.75, (0.95, 0.28, 0.04, 1)), (1.0, (0.6, 0.10, 0.02, 1))], (-300, 0))
    nt.links.new(t, r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"]); nt.links.new(r.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 14.0; b.inputs["Roughness"].default_value = 1.0
    return m

def embers_mat(name="M_Embers"):
    m, nt, b = new_mat(name)
    mp = coords(nt)
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 0)); v.inputs["Scale"].default_value = 30
    nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    n = noise_tex(nt, mp.outputs["Vector"], 8, 4, loc=(-1000, -250))
    f = math_n(nt, 'MULTIPLY', v.outputs["Distance"], n.outputs["Fac"], (-750, 0))
    r = ramp(nt, [(0.05, (1.0, 0.45, 0.08, 1)), (0.18, (0.35, 0.06, 0.01, 1)), (0.3, (0.03, 0.025, 0.02, 1))], (-500, 0))
    nt.links.new(f, r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"]); nt.links.new(r.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 3.0; b.inputs["Roughness"].default_value = 0.9
    return m

def violet_mat(name, leaf_lo, leaf_hi, violet_density, soil=None):
    """Heart-shaped-leaf green with sweet violets as purple dots (Viola odorata); optionally dark loam showing."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    lv = node(nt, "ShaderNodeTexVoronoi", (-1000, 300)); lv.inputs["Scale"].default_value = 22
    nt.links.new(mp.outputs["Vector"], lv.inputs["Vector"])
    n = noise_tex(nt, mp.outputs["Vector"], 2.0, 5, loc=(-1000, 50))
    mx = node(nt, "ShaderNodeMix", (-750, 300), data_type='FLOAT'); mx.inputs["Factor"].default_value = 0.4
    nt.links.new(lv.outputs["Distance"], mx.inputs[2]); nt.links.new(n.outputs["Fac"], mx.inputs[3])
    lr = ramp(nt, [(0.2, c4(scaled(leaf_lo, 0.6))), (0.5, c4(leaf_lo)), (0.85, c4(leaf_hi))], (-550, 300)); nt.links.new(mx.outputs[0], lr.inputs["Fac"])
    col = lr.outputs["Color"]
    if soil:
        sr = ramp(nt, [(0.55, (0, 0, 0, 1)), (0.72, (1, 1, 1, 1))], (-550, 50)); nt.links.new(n.outputs["Fac"], sr.inputs["Fac"])
        col = mix_rgb(nt, col, c4(soil), sr.outputs["Color"], 'MIX', (-300, 200))
    fv = node(nt, "ShaderNodeTexVoronoi", (-1000, -250)); fv.inputs["Scale"].default_value = 26
    nt.links.new(mp.outputs["Vector"], fv.inputs["Vector"])
    pick = ramp(nt, [(violet_density, (0, 0, 0, 1)), (violet_density + 0.02, (1, 1, 1, 1))], (-750, -250)); nt.links.new(fv.outputs["Color"], pick.inputs["Fac"])
    dot = ramp(nt, [(0.0, (1, 1, 1, 1)), (0.3, (1, 1, 1, 1)), (0.4, (0, 0, 0, 1))], (-750, -450)); nt.links.new(fv.outputs["Distance"], dot.inputs["Fac"])
    sel = math_n(nt, 'MULTIPLY', pick.outputs["Color"], dot.outputs["Color"], (-500, -300))
    tone = ramp(nt, [(0.0, (0.16, 0.05, 0.36, 1)), (0.6, (0.30, 0.12, 0.55, 1)), (1.0, (0.42, 0.24, 0.66, 1))], (-500, -500))
    nt.links.new(n.outputs["Fac"], tone.inputs["Fac"])
    col = mix_rgb(nt, col, tone.outputs["Color"], sel, 'MIX', (-150, 200))
    a = node(nt, "ShaderNodeAmbientOcclusion", (-450, -700)); a.inputs["Distance"].default_value = 0.25
    aor = ramp(nt, [(0.0, (0.45, 0.45, 0.42, 1)), (1.0, (1, 1, 1, 1))], (-250, -700)); nt.links.new(a.outputs["AO"], aor.inputs["Fac"])
    col = mix_rgb(nt, col, aor.outputs["Color"], 1.0, 'MULTIPLY', (0, 200))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.75
    b.inputs["Subsurface Weight"].default_value = 0.1
    inv = math_n(nt, 'SUBTRACT', 1.0, lv.outputs["Distance"], (-400, -900))
    bump_from(nt, b, inv, 0.6, 0.01)
    return m

def cloth_mat(name="M_Cloth"):
    """The web on the loom: purple wool with saffron bands and a running wave border, a tabby weave."""
    m, nt, b = new_mat(name)
    mp = coords(nt)
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1200, 300)); nt.links.new(mp.outputs["Vector"], sep.inputs["Vector"])
    # wavy band: |frac(z*2.6 + 0.04 sin(x*30)) - 0.5|
    sx = math_n(nt, 'MULTIPLY', sep.outputs["X"], 28.0, (-1000, 400)); sx = math_n(nt, 'SINE', sx, None, (-850, 400)); sx = math_n(nt, 'MULTIPLY', sx, 0.05, (-700, 400))
    z = math_n(nt, 'MULTIPLY_ADD', sep.outputs["Z"], 2.4, (-550, 300)); nt.links.new(sx, z.node.inputs[2])
    fr = math_n(nt, 'FRACT', z, None, (-400, 300))
    band = ramp(nt, [(0.0, (0, 0, 0, 1)), (0.40, (0, 0, 0, 1)), (0.41, (1, 1, 1, 1)), (0.47, (1, 1, 1, 1)), (0.48, (0.5, 0.5, 0.5, 1)), (0.52, (0.5, 0.5, 0.5, 1)), (0.53, (1, 1, 1, 1)), (0.59, (1, 1, 1, 1)), (0.60, (0, 0, 0, 1))], (-250, 300))
    nt.links.new(fr, band.inputs["Fac"])
    purple = (0.20, 0.035, 0.10, 1); saffron = (0.78, 0.48, 0.07, 1); white = (0.80, 0.74, 0.60, 1)
    col = mix_rgb(nt, purple, saffron, band.outputs["Color"], 'MIX', (-50, 300))
    wline = ramp(nt, [(0.0, (0, 0, 0, 1)), (0.45, (0, 0, 0, 1)), (0.5, (1, 1, 1, 1)), (0.55, (0, 0, 0, 1))], (-250, 100))
    nt.links.new(band.outputs["Color"], wline.inputs["Fac"])
    col = mix_rgb(nt, col, white, wline.outputs["Color"], 'MIX', (100, 300))
    wx = node(nt, "ShaderNodeTexWave", (-1000, -100), wave_type='BANDS', bands_direction='X'); wx.inputs["Scale"].default_value = 160
    wz = node(nt, "ShaderNodeTexWave", (-1000, -300), wave_type='BANDS', bands_direction='Z'); wz.inputs["Scale"].default_value = 160
    for w in (wx, wz): nt.links.new(mp.outputs["Vector"], w.inputs["Vector"])
    weave = math_n(nt, 'MULTIPLY', wx.outputs["Fac"], wz.outputs["Fac"], (-700, -200))
    wr = ramp(nt, [(0.0, (0.7, 0.7, 0.7, 1)), (1.0, (1, 1, 1, 1))], (-500, -200)); nt.links.new(weave, wr.inputs["Fac"])
    col = mix_rgb(nt, col, wr.outputs["Color"], 1.0, 'MULTIPLY', (250, 300))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85; b.inputs["Sheen Weight"].default_value = 0.7
    bump_from(nt, b, weave, 0.2, 0.001)
    return m

def warp_mat(name="M_Warp"):
    """Hanging warp threads: undyed wool, one band per thread."""
    m, nt, b = new_mat(name)
    mp = coords(nt)
    wx = node(nt, "ShaderNodeTexWave", (-1000, 0), wave_type='BANDS', bands_direction='X'); wx.inputs["Scale"].default_value = 60
    wx.inputs["Distortion"].default_value = 0.4
    nt.links.new(mp.outputs["Vector"], wx.inputs["Vector"])
    r = ramp(nt, [(0.0, (0.16, 0.13, 0.09, 1)), (0.35, (0.44, 0.39, 0.29, 1)), (0.7, (0.58, 0.52, 0.40, 1))], (-700, 0))
    nt.links.new(wx.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85; b.inputs["Sheen Weight"].default_value = 0.6
    bump_from(nt, b, wx.outputs["Fac"], 0.4, 0.001)
    return m

def grapes_mat(name="M_Grapes"):
    m, nt, b = new_mat(name)
    mp = coords(nt)
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 0)); v.inputs["Scale"].default_value = 40
    nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    r = ramp(nt, [(0.0, (0.28, 0.14, 0.32, 1)), (0.45, (0.12, 0.03, 0.14, 1)), (1.0, (0.03, 0.01, 0.04, 1))], (-700, 0))
    nt.links.new(v.outputs["Distance"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.4; b.inputs["Sheen Weight"].default_value = 0.6; b.inputs["Sheen Tint"].default_value = (0.7, 0.75, 0.9, 1)
    inv = math_n(nt, 'SUBTRACT', 1.0, v.outputs["Distance"], (-500, -300))
    bump_from(nt, b, inv, 1.0, 0.01)
    return m

# ----------------------------------------------------------------------------- materials
M_ROCK = rock("M_CaveRock", smoke=True)
M_BOULDER = rock("M_Boulder", colors=((0.34, 0.30, 0.24), (0.52, 0.47, 0.38), (0.66, 0.61, 0.52)), scale=2.5, ao=False, bumpk=0.6)
M_FLOOR = rock("M_CaveFloor", colors=((0.14, 0.11, 0.08), (0.24, 0.19, 0.14), (0.33, 0.27, 0.20)), scale=2.0, ao=True, bumpk=0.4)
M_GROUND = ground_mat()
M_SEA = sea_mat("M_Sea", 18.0, 34.0, (0.04, 0.30, 0.32), (0.015, 0.08, 0.20))
M_FARSEA = sea_mat("M_FarSea", 34.0, 57.0, (0.015, 0.08, 0.20), (0.22, 0.36, 0.52), rough=0.12)
M_SKYDOME = sky_dome_mat()
M_HEADLAND = noisy("M_Headland", [(0.33, 0.40, 0.44), (0.40, 0.46, 0.48), (0.46, 0.50, 0.50)], scale=0.3, rough=1.0, bump=0.0)
M_FARTREES = noisy("M_FarTrees", [(0.20, 0.27, 0.27), (0.25, 0.32, 0.30)], scale=1.0, rough=1.0, bump=0.0)
M_BARK = bark("M_Bark")
M_POPLARBARK = bark("M_PoplarBark", (0.12, 0.11, 0.09), (0.45, 0.44, 0.40), (0.62, 0.61, 0.56), stretch=(3, 3, 1.0))
M_ALDER = leaves("M_AlderLeaves", (0.05, 0.11, 0.03), (0.13, 0.22, 0.05))
M_POPLAR = leaves("M_PoplarLeaves", (0.11, 0.17, 0.07), (0.34, 0.40, 0.24), scale=18)
M_CYPRESS = leaves("M_Cypress", (0.03, 0.075, 0.035), (0.07, 0.14, 0.055), scale=24, sss=0.05)
M_VINEWOOD = bark("M_VineWood", (0.05, 0.035, 0.025), (0.22, 0.16, 0.10), (0.34, 0.27, 0.19), stretch=(14, 14, 1.0))
M_VINELEAVES = leaves("M_VineLeaves", (0.10, 0.21, 0.035), (0.30, 0.42, 0.09), scale=9, sss=0.3)
M_GRAPES = grapes_mat()
M_WATER = plain("M_Water", (0.05, 0.13, 0.12), rough=0.03, coat=0.0)
M_CHANNEL = rock("M_ChannelStone", colors=((0.30, 0.27, 0.22), (0.44, 0.40, 0.33), (0.56, 0.52, 0.44)), scale=6, ao=False, bumpk=0.5)
M_BED = violet_mat("M_VioletBed", (0.05, 0.12, 0.025), (0.11, 0.21, 0.04), 0.62, soil=(0.08, 0.055, 0.03))
M_VIOLETS = violet_mat("M_Violets", (0.04, 0.12, 0.025), (0.12, 0.23, 0.05), 0.42)
M_HERBAGE = leaves("M_Herbage", (0.07, 0.19, 0.03), (0.22, 0.36, 0.07), scale=30, sss=0.25)
M_HEARTH = rock("M_HearthStone", colors=((0.10, 0.09, 0.08), (0.24, 0.22, 0.19), (0.36, 0.33, 0.28)), scale=5, ao=False, bumpk=0.5)
M_ASH = noisy("M_Ash", [(0.06, 0.055, 0.05), (0.18, 0.17, 0.16), (0.32, 0.30, 0.28)], scale=12, rough=1.0, bump=0.3, bump_dist=0.003)
M_LOGS = wood("M_Logs", base=(0.06, 0.035, 0.02), dark=(0.01, 0.008, 0.007), light=(0.16, 0.09, 0.05), scale=2.0, rough=(0.7, 0.9))
M_EMBERS = embers_mat()
M_FLAME = flame_mat()
M_LOOMWOOD = wood("M_LoomWood", base=(0.27, 0.18, 0.10), dark=(0.08, 0.05, 0.03), light=(0.46, 0.33, 0.19))
M_WARP = warp_mat()
M_CLOTH = cloth_mat()
M_TERRACOTTA = noisy("M_Terracotta", [(0.40, 0.18, 0.08), (0.55, 0.27, 0.13), (0.62, 0.34, 0.18)], scale=10, rough=0.8, bump=0.2, bump_dist=0.001)
M_GOLD = plain("M_Gold", (0.95, 0.70, 0.30), rough=0.22, metallic=1.0)
M_FLEECE = noisy("M_Fleece", [(0.55, 0.50, 0.40), (0.72, 0.66, 0.55), (0.80, 0.75, 0.64)], scale=25, rough=0.95, sheen=0.8, bump=0.8, bump_dist=0.006)
M_NEST = noisy("M_Twigs", [(0.10, 0.07, 0.04), (0.24, 0.17, 0.10), (0.36, 0.28, 0.17)], scale=40, rough=0.95, stretch=(1, 1, 5), bump=0.8, bump_dist=0.005, warp=2.0)

# ----------------------------------------------------------------------------- geometry helpers
def _finish(o, mat, smooth=True):
    o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0), smooth=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = 1; md.limit_method = 'ANGLE'
    return _finish(o, mat, smooth)

def cyl(name, r, h, loc, mat, verts=12, rot=(0, 0, 0), r2=None):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat)

def lathe(name, profile, loc, mat, steps=16, rot=(0, 0, 0), wobble=0.0, seed=0.0):
    """profile: (radius, z) bottom to top, revolved around Z; optional noise wobble on the radius."""
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

def blob(name, loc, radius, mat, scale=(1, 1, 1), subdiv=1, amp=0.25, freq=1.6, seed=0.0, rot=(0, 0, 0), flat_bottom=None):
    """Lumpy organic clump: icosphere displaced by noise (foliage, stones, headlands)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    for v in bm.verts:
        n = v.co.normalized()
        k = 1.0 + amp * noise.noise(n * freq + Vector((seed, seed * 1.7, seed * 0.3)))
        p = Vector((n.x * radius * k * scale[0], n.y * radius * k * scale[1], n.z * radius * k * scale[2]))
        if flat_bottom is not None: p.z = max(p.z, flat_bottom)
        v.co = p
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def tube(name, pts, radii, mat, sides=6, n=4):
    """A tapered tube along a Catmull-Rom path (vine stems, branches)."""
    c = catmull(pts, n); rr = [lerp(radii[0], radii[1], i / max(1, len(c) - 1)) for i in range(len(c))]
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    up = Vector((0, 0, 1))
    for i, p in enumerate(c):
        t = (c[min(i + 1, len(c) - 1)] - c[max(i - 1, 0)]).normalized()
        a = t.cross(up if abs(t.dot(up)) < 0.9 else Vector((1, 0, 0))).normalized(); b_ = t.cross(a).normalized()
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / sides) + b_ * math.sin(2 * math.pi * k / sides)) * rr[i]) for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides; bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
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

def group(name, objs, loc=(0, 0, 0), rot=(0, 0, 0)):
    """Parent objs under a named empty, then move/turn the empty (objs built in its local frame)."""
    e = bpy.data.objects.new(name, None); e.empty_display_size = 0.05; link(e)
    bpy.context.view_layer.update()
    for o in objs: o.parent = e
    e.location = loc; e.rotation_euler = rot
    return e

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

# ----------------------------------------------------------------------------- terrain: a terrace before the cave, a bluff, a beach, the cave hill
def cave_e(x, y):
    return math.sqrt((x / CAVE_R[0]) ** 2 + ((y - CAVE_C.y) / CAVE_R[1]) ** 2)

def terrain_h(x, y):
    s = -y                                               # distance seaward from the reader
    S = 17.0 + 0.012 * x * x                             # the shoreline bows out into a bay
    h = -0.02 - 0.03 * max(0.0, s - 1.0)                 # the watered terrace, falling gently seaward
    h = lerp(h, SEA_Z + 0.5, smoothstep(8.0, S - 2.5, s) ** 0.8)      # bluff down to the beach
    h = lerp(h, SEA_Z - 2.0, smoothstep(S - 2.5, S + 4.0, s))          # beach shelving into the sea
    terrace = 1.0 - max(smoothstep(5.0, 9.0, abs(x)), smoothstep(8.0, 10.0, s), smoothstep(-1.0, 1.0, y))
    shore = 1.0 - smoothstep(S - 4.0, S - 1.0, s)
    h += (0.9 * noise.noise(Vector((x * 0.11, y * 0.11, 0.5))) + 0.25 * noise.noise(Vector((x * 0.4, y * 0.4, 1.5)))) * (1 - terrace) * shore
    # the cave hill: rises outside the rock shell, round the back and the flanks, never in front of the mouth
    e = cave_e(x, y)
    mask = max(smoothstep(-1.0, 1.5, y), smoothstep(3.0, 5.5, abs(x)) * smoothstep(-8.0, -2.0, y))
    hill = 2.6 * smoothstep(1.3, 1.8, e) * math.exp(-(max(0.0, e - 1.8) / 1.9) ** 2) * mask
    hill += 0.8 * noise.noise(Vector((x * 0.25, y * 0.25, 3.3))) * smoothstep(1.3, 1.8, e) * mask
    h += hill
    # island edges drop into the sea
    r = math.hypot(x, y - 2.0)
    h = lerp(h, SEA_Z - 2.5, smoothstep(26.0, 34.0, r))
    if e < 1.02 and y > FRONT_Y - 0.1: h = min(h, -0.25)   # under the cave floor
    return h

def terrain(name, N=42):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); grid = []
    for j in range(N + 1):
        v = -1 + 2 * j / N; y = 34.0 * (0.35 * v + 0.65 * v * abs(v)) - 4.0
        row = []
        for i in range(N + 1):
            u = -1 + 2 * i / N; x = 36.0 * (0.35 * u + 0.65 * u * abs(u))
            row.append(bm.verts.new((x, y, terrain_h(x, y))))
        grid.append(row)
    for j in range(N):
        for i in range(N):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_GROUND)
    for p in me.polygons: p.use_smooth = True
    return link(o)

ground = terrain("Ground")

# ----------------------------------------------------------------------------- the cave: a displaced rock shell with a mouth cut in its cliff face
def mouth_hw(z, seed=0.0):
    if z <= 0: return MOUTH_W / 2
    t = min(1.0, z / MOUTH_H)
    return MOUTH_W / 2 * max(0.0, 1 - t ** 2.2) ** 0.5

def cave_shell(name="CaveShell"):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=30, radius=1.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for v in bm.verts:
        d = v.co.normalized()
        k = 1.0 + 0.09 * noise.noise(d * 1.3 + Vector((3.1, 0.7, 1.9)))
        p = Vector((d.x * CAVE_R[0] * k, d.y * CAVE_R[1] * k, d.z * CAVE_R[2] * k)) + CAVE_C
        p.y = max(p.y, FRONT_Y); p.z = max(p.z, -0.5)
        v.co = p
    def in_mouth(c):
        return c.y < 0.3 and abs(c.x) < mouth_hw(c.z)
    kill = [f for f in bm.faces if all(v.co.z <= -0.499 for v in f.verts) or in_mouth(f.calc_center_median())]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    # snap the ragged rim of the opening onto the arch outline (with a little rock jitter)
    for v in bm.verts:
        if not v.is_boundary or v.co.z <= -0.45 or v.co.y > 0.6: continue
        x, z = v.co.x, v.co.z
        sgn = 1 if x >= 0 else -1
        jit = 0.07 * noise.noise(Vector((x * 2.0, z * 2.0, 7.7)))
        if z < MOUTH_H * 0.72:
            v.co.x = sgn * (mouth_hw(z) + jit)
        else:
            q = min(1.0, abs(x) / (MOUTH_W / 2))
            v.co.z = MOUTH_H * max(0.0, 1 - q * q) ** (1 / 2.2) + jit
    bmesh.ops.reverse_faces(bm, faces=bm.faces)          # normals into the cave
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); link(o); me.materials.append(M_ROCK)
    sol = o.modifiers.new("Solidify", 'SOLIDIFY'); sol.thickness = WALL_T; sol.offset = -1.0; sol.use_rim = True; sol.use_even_offset = True
    n_inner = len(me.vertices)
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); o.modifiers.clear(); o.data = me2
    off1, off2, off3 = Vector((11.0, 3.0, 5.0)), Vector((2.0, 9.0, 4.0)), Vector((5.0, 1.0, 8.0))
    din = sum(((me2.vertices[i].co - CAVE_C).length for i in range(n_inner))) / n_inner
    dout = sum(((me2.vertices[i].co - CAVE_C).length for i in range(n_inner, len(me2.vertices)))) / max(1, len(me2.vertices) - n_inner)
    print(f"cave shell: inner verts {n_inner} mean r {din:.2f}, outer mean r {dout:.2f}")
    for idx, v in enumerate(me2.vertices):
        p = v.co.copy()
        amp = 0.62 * (0.25 + 0.75 * smoothstep(1.5, 3.6, (p - MOUTH_C).length))
        for c_, rad in ((LOOM, 1.6), (HEARTH, 1.2)):       # keep the walls off the loom and the fire
            amp *= 0.45 + 0.55 * smoothstep(rad * 0.6, rad * 1.4, Vector((p.x - c_.x, p.y - c_.y, 0)).length)
        q = p + noise.noise_vector(p * 0.42 + off1) * amp + noise.noise_vector(p * 1.4 + off2) * amp * 0.3
        if idx >= n_inner:
            # the outside: a thick craggy hill over the chamber, thin only at the cliff face round the mouth
            d = Vector(((p.x - CAVE_C.x) / CAVE_R[0], (p.y - CAVE_C.y) / CAVE_R[1], max(0.0, p.z) / CAVE_R[2])).normalized()
            thick = 2.2 * smoothstep(-0.55, 0.05, d.y) * (0.75 + 0.5 * noise.noise(p * 0.3 + off3))
            radial = Vector((d.x, d.y * 0.6, d.z + 0.35)).normalized()
            q += radial * thick + noise.noise_vector(p * 0.22 + off3) * 0.9 * smoothstep(-0.55, 0.05, d.y)
        v.co = q
    for p in me2.polygons: p.use_smooth = True
    return o

cave = cave_shell()
# a lintel ledge of rock jutting over the mouth (shades the reader's view, hangs the vine)
blob("MouthBrow", (0.0, OUTER_Y + 0.25, MOUTH_H + 0.75), 1.0, M_ROCK, scale=(2.4, 0.7, 0.55), subdiv=3, amp=0.3, freq=1.8, seed=8.0)

def cave_floor(name="CaveFloor", rings=10, seg=44):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    centre = bm.verts.new((CAVE_C.x, CAVE_C.y, 0.0)); allr = []
    for j in range(1, rings + 1):
        f = (j / rings) ** 0.8 * 1.04; ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            x, y = CAVE_C.x + CAVE_R[0] * f * math.cos(a), CAVE_C.y + CAVE_R[1] * f * math.sin(a)
            y = max(y, OUTER_Y - 0.08)
            z = 0.015 * noise.noise(Vector((x * 0.8, y * 0.8, 0.2)))
            if y < FRONT_Y - 0.2:                         # droop to the terrace at the threshold
                z = lerp(z, terrain_h(x, y) + 0.004, smoothstep(FRONT_Y - 0.2, OUTER_Y - 0.08, y))
            ring.append(bm.verts.new((x, y, z)))
        allr.append(ring)
    for i in range(seg): bm.faces.new((centre, allr[0][i], allr[0][(i + 1) % seg]))
    for a, b_ in zip(allr, allr[1:]):
        for i in range(seg):
            j = (i + 1) % seg; bm.faces.new((a[i], b_[i], b_[j], a[j]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_FLOOR)
    for p in me.polygons: p.use_smooth = True
    return link(o)

cave_floor()
# a few fallen stones along the walls inside
for i, (x, y, r) in enumerate([(-3.0, 4.2, 0.35), (3.1, 4.0, 0.3), (-1.2, 5.9, 0.4), (1.6, 6.0, 0.3), (-3.2, -0.2, 0.28), (3.0, 0.1, 0.32)]):
    blob(f"CaveStone{i}", (x, y, 0.0), r, M_BOULDER, scale=(1.2, 1.0, 0.6), subdiv=2, amp=0.35, seed=i * 2.3, flat_bottom=-0.05)

# ----------------------------------------------------------------------------- sea, sky dome, far headlands
def disc(name, r0, r1, z, mat, rings=6, seg=48, z1=None, curve=1.0):
    """Flat (or, with z1, bowl-shaped) annulus/disc facing up."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); allr = []
    centre = bm.verts.new((0, 0, z)) if r0 <= 0 else None
    for j in range(rings + 1):
        if r0 <= 0 and j == 0: continue
        rr = lerp(r0, r1, j / rings); zz = z if z1 is None else lerp(z, z1, (j / rings) ** curve)
        allr.append([bm.verts.new((rr * math.cos(2 * math.pi * i / seg), rr * math.sin(2 * math.pi * i / seg), zz)) for i in range(seg)])
    if centre is not None:
        for i in range(seg): bm.faces.new((centre, allr[0][i], allr[0][(i + 1) % seg]))
    for a, b_ in zip(allr, allr[1:]):
        for i in range(seg):
            j = (i + 1) % seg; bm.faces.new((a[i], b_[i], b_[j], a[j]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

disc("Sea", 0.0, 34.0, SEA_Z, M_SEA, rings=6)
FARSEA_RIM = 1.15                                          # the far sea rises to just under eye height so the horizon sits where it should
disc("far.Sea", 34.0, 57.5, SEA_Z, M_FARSEA, rings=5, z1=FARSEA_RIM, curve=1.6)
def farsea_z(r): return lerp(SEA_Z, FARSEA_RIM, smoothstep(0.0, 1.0, (r - 34.0) / 23.5) ** 1.0) if r > 34.0 else SEA_Z

def sky_dome(name, radius=58.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=12, radius=radius)
    for v in list(bm.verts):
        if v.co.z < -radius * 0.12: v.co.z = -radius * 0.12
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_SKYDOME)
    for p in me.polygons: p.use_smooth = True
    # render: the dome is seen by the camera only; the world sky lights the scene
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False; o.visible_transmission = False; o.visible_volume_scatter = False
    return link(o)
sky = sky_dome("SkyDome")

# distant headlands of the island's own coast, hazy with distance
for nm, (x, y), r, sc, sd in [("far.Headland_Distant_W", (-40.0, -34.0), 11.0, (1.5, 0.75, 0.42), 1.0),
                              ("far.Headland_Distant_E", (39.0, -38.0), 12.0, (1.4, 0.7, 0.36), 4.0)]:
    blob(nm, (x, y, farsea_z(math.hypot(x, y)) - 1.0), r, M_HEADLAND, scale=sc, subdiv=2, amp=0.3, freq=1.4, seed=sd, rot=(0, 0, math.atan2(y, x)), flat_bottom=-0.5)
    for k in range(5):
        a = math.atan2(y, x) + random.uniform(-0.18, 0.18); d = math.hypot(x, y) + random.uniform(-4, 3)
        hz = farsea_z(math.hypot(x, y)) - 1.0 + r * sc[2] * random.uniform(0.6, 0.95)
        blob(f"FarTrees_{nm[-1]}{k}", (d * math.cos(a), d * math.sin(a), hz), random.uniform(1.0, 1.7), M_FARTREES, scale=(1, 1, 1.6), subdiv=1, amp=0.3, seed=k + sd)

# shore rocks: where Ulysses sat, "on the rocks and on the sea shore ... always looking out upon the sea"
for i, (x, y, r) in enumerate([(-3.5, -17.6, 1.0), (-2.2, -18.6, 0.6), (4.8, -18.0, 0.8), (9.0, -18.2, 1.2), (-9.5, -18.0, 1.3), (1.2, -19.6, 0.5)]):
    blob(f"ShoreRock{i}", (x, y, terrain_h(x, y) - 0.1), r, M_BOULDER, scale=(1.3, 1.0, 0.7), subdiv=1, amp=0.35, seed=10 + i * 1.3)
# boulders about the cave's cliff and terrace edges
for i, (x, y, r) in enumerate([(-3.4, -2.6, 0.55), (3.2, -2.3, 0.6), (4.2, -1.2, 0.8), (-4.4, -1.8, 0.9), (-5.8, -8.5, 0.6), (6.0, -9.2, 0.7)]):
    blob(f"Boulder{i}", (x, y, terrain_h(x, y) - 0.05), r, M_BOULDER, scale=(1.2, 1.0, 0.75), subdiv=2, amp=0.3, seed=30 + i * 1.7)

# ----------------------------------------------------------------------------- the grove: alder, poplar and sweet smelling cypress
def cypress(name, x, y, h, seed):
    z0 = terrain_h(x, y) - 0.1
    prof = [(0.0, 0.0), (0.12, 0.0), (0.12, 0.6)] + [(h * 0.085 * math.sin(math.pi * min(1.0, (t * 0.92 + 0.08))) ** 0.7 * (1.0 - 0.35 * t), 0.6 + t * (h - 0.6)) for t in [0.0, 0.1, 0.25, 0.4, 0.55, 0.7, 0.82, 0.92]] + [(0.0, h)]
    lathe(name + "_Foliage", prof[2:], (x, y, z0), M_CYPRESS, steps=10, wobble=0.22, seed=seed)
    cyl(name + "_Trunk", 0.12, 1.0, (x, y, z0 + 0.5), M_BARK, verts=6)

def poplar(name, x, y, h, seed):
    z0 = terrain_h(x, y) - 0.1
    cyl(name + "_Trunk", 0.18, h * 0.55, (x, y, z0 + h * 0.275), M_POPLARBARK, verts=7, r2=0.11)
    prof = [(h * 0.02, h * 0.22)] + [(h * 0.16 * math.sin(math.pi * t) ** 0.6 * (1.0 - 0.3 * t), h * 0.22 + t * h * 0.78) for t in [0.05, 0.15, 0.3, 0.45, 0.6, 0.75, 0.88, 0.96]] + [(0.0, h)]
    lathe(name + "_Crown", prof, (x, y, z0), M_POPLAR, steps=12, wobble=0.3, seed=seed)

def alder(name, x, y, h, seed):
    z0 = terrain_h(x, y) - 0.1
    cyl(name + "_Trunk", 0.2, h * 0.5, (x, y, z0 + h * 0.25), M_BARK, verts=7, r2=0.12)
    for k, (dx, dy, dz, rr) in enumerate([(0.0, 0.0, 0.72, 0.31), (0.24, 0.1, 0.52, 0.23), (-0.22, -0.14, 0.56, 0.23)]):
        a = seed * 2.1; ca, sa = math.cos(a), math.sin(a)
        blob(f"{name}_Crown{k}", (x + (dx * ca - dy * sa) * h, y + (dx * sa + dy * ca) * h, z0 + dz * h), rr * h, M_ALDER, scale=(1.0, 0.95, 0.85), subdiv=2, amp=0.32, freq=2.2, seed=seed + k * 3)

TREES = [
    ("cypress", -4.3, -3.4, 8.0), ("cypress", 4.7, -4.4, 9.0), ("cypress", -7.0, -9.5, 9.5), ("cypress", 7.6, -11.0, 8.0),
    ("cypress", -4.6, 5.0, 8.5), ("cypress", 5.8, 4.2, 7.5), ("cypress", -11.5, -13.0, 8.0),
    ("poplar", 5.6, -1.6, 11.0), ("poplar", -6.0, -0.8, 12.0), ("poplar", 10.0, -6.8, 10.5), ("poplar", -10.5, -5.5, 10.0), ("poplar", 2.8, 8.8, 11.0),
    ("alder", 7.2, -7.2, 7.0), ("alder", -8.0, -3.8, 6.5), ("alder", -9.0, -12.5, 6.0), ("alder", 9.5, -14.5, 6.0),
    ("alder", -1.8, 8.2, 7.0), ("alder", -9.8, 2.2, 6.5), ("alder", 10.0, 0.5, 6.5), ("alder", 12.5, -11.0, 6.0),
    ("cypress", 8.3, -3.0, 9.5), ("cypress", -8.6, -7.6, 8.5), ("cypress", 13.0, -6.0, 8.0), ("cypress", -13.5, -2.0, 9.0), ("cypress", 6.2, 9.0, 8.0),
    ("poplar", -13.0, -9.0, 10.0), ("poplar", 14.5, -2.5, 11.0), ("alder", -5.5, 10.5, 7.0), ("alder", 15.5, -9.0, 6.0), ("cypress", -6.4, -13.6, 7.5),
]
for i, (kind, x, y, h) in enumerate(TREES):
    {"cypress": cypress, "poplar": poplar, "alder": alder}[kind](f"{kind.capitalize()}{i}", x, y, h, i * 1.37)
# nests of the great birds (owls, hawks, sea-crows) in the poplar and alder crowns
for i, (x, y, z) in enumerate([(5.25, -1.9, 7.4), (7.0, -6.6, 5.9), (-5.7, -1.1, 8.6)]):
    lathe(f"Nest{i}", [(0.12, 0.0), (0.3, 0.06), (0.34, 0.16), (0.24, 0.17), (0.14, 0.09), (0.0, 0.08)], (x, y, terrain_h(x, y) + z - 0.1), M_NEST, steps=10, wobble=0.25, seed=i)

# ----------------------------------------------------------------------------- the vine, loaded with grapes, trained about the mouth of the cave
POLE_X = 2.05
for s in (-1, 1):
    cyl(f"VinePole{s}", 0.045, 3.4, (s * POLE_X, VINE_Y - 0.08, 1.7), M_VINEWOOD, verts=6, rot=(0, math.radians(-s * 2), 0))
cyl("VineCrossbar", 0.04, POLE_X * 2 + 0.4, (0, VINE_Y - 0.08, 3.32), M_VINEWOOD, verts=6, rot=(0, math.radians(90), 0))
vine_path = [(1.95, VINE_Y, 0.0), (2.0, VINE_Y + 0.02, 0.8), (1.92, VINE_Y, 1.6), (1.95, VINE_Y - 0.05, 2.5), (1.6, VINE_Y - 0.05, 3.2),
             (0.6, VINE_Y - 0.06, 3.35), (-0.6, VINE_Y - 0.06, 3.3), (-1.6, VINE_Y - 0.05, 3.2), (-1.95, VINE_Y - 0.03, 2.6), (-2.0, VINE_Y, 1.9)]
tube("VineStem", vine_path, (0.09, 0.03), M_VINEWOOD, sides=7, n=4)
tube("VineStem2", [(1.95, VINE_Y, 2.4), (2.4, VINE_Y + 0.2, 3.1), (2.9, VINE_Y + 0.5, 3.6)], (0.04, 0.015), M_VINEWOOD, sides=5, n=3)
tube("VineStem3", [(-1.7, VINE_Y - 0.05, 3.2), (-2.5, VINE_Y + 0.3, 3.7), (-3.1, VINE_Y + 0.6, 3.9)], (0.035, 0.015), M_VINEWOOD, sides=5, n=3)
vc = catmull(vine_path, 4)
LEAF_OUTLINE = []
for k in range(11):                                           # a five-lobed vine leaf, the stalk notch at the bottom
    a = math.radians(-145 + 290 * k / 10)
    rr = 1.0 if k % 2 == 1 else 0.62
    if k in (0, 10): rr = 0.45
    LEAF_OUTLINE.append((math.sin(a) * rr, math.cos(a) * rr))
LEAF_MESHES = []
def vine_leaf(x, y, z, size, rng):
    """One flat leaf facing roughly out of the cave (-Y), tipped and turned at random."""
    me = bpy.data.meshes.new("VineLeaf"); bm = bmesh.new()
    c = bm.verts.new((0, 0, 0)); ring = [bm.verts.new((u * size, 0.0, (w + 0.35) * size)) for u, w in LEAF_OUTLINE]
    for k in range(len(ring) - 1): bm.faces.new((c, ring[k + 1], ring[k]))
    bm.normal_update()
    rot = Euler((rng.uniform(-0.9, 0.5), rng.uniform(-0.5, 0.5), rng.uniform(-0.7, 0.7))).to_matrix()
    for v in bm.verts:
        q = rot @ v.co
        q.y += 0.15 * (q.x ** 2 + q.z ** 2) / max(size, 1e-3)            # a slight cup
        v.co = q + Vector((x, y, z))
    bm.to_mesh(me); bm.free()
    LEAF_MESHES.append(me)
rngl = random.Random(11)
def clear_of_page(x, z):
    return z > 2.3 or abs(x) > 1.45
for k, p in enumerate(vc):
    for _ in range(6 if p.z > 2.0 else 4):
        x, z = p.x + rngl.uniform(-0.3, 0.3), p.z + rngl.uniform(-0.35, 0.25)
        if not clear_of_page(x, z) or z < 0.25: continue
        vine_leaf(x, VINE_Y - rngl.uniform(0.04, 0.2), z, rngl.uniform(0.09, 0.14), rngl)
for (a, b_) in [((1.95, 2.4), (2.9, 3.6)), ((-1.7, 3.2), (-3.1, 3.9))]:   # the two side shoots running up the rock
    for t in [0.1, 0.3, 0.5, 0.7, 0.9]:
        for _ in range(4):
            x = lerp(a[0], b_[0], t) + rngl.uniform(-0.25, 0.25); z = lerp(a[1], b_[1], t) + rngl.uniform(-0.25, 0.2)
            vine_leaf(x, VINE_Y + 0.3 * t * 1.5 - 0.1, z, rngl.uniform(0.09, 0.13), rngl)
for x in [i * 0.16 - 1.35 for i in range(18)]:                  # a fringe hanging from the lintel, kept above the page
    for _ in range(2):
        vine_leaf(x + rngl.uniform(-0.06, 0.06), VINE_Y - rngl.uniform(0.0, 0.15), 2.45 + rngl.uniform(0.0, 0.5) + 0.1 * math.cos(x * 2.2), rngl.uniform(0.1, 0.14), rngl)
# join the leaves into one object
_bm = bmesh.new()
for me_ in LEAF_MESHES: _bm.from_mesh(me_); bpy.data.meshes.remove(me_)
_lm = bpy.data.meshes.new("VineLeaves"); _bm.to_mesh(_lm); _bm.free()
_lo = bpy.data.objects.new("VineLeaves", _lm); _lm.materials.append(M_VINELEAVES); link(_lo)
print("vine leaves", len(_lm.polygons))

# grape bunches: berries on a tapering cone, each bunch on its stalk
grape_spots = [(-1.0, 2.5), (-0.35, 2.58), (0.3, 2.52), (0.95, 2.56), (-1.6, 2.7), (1.62, 2.72), (2.18, 1.95), (-2.2, 1.75), (-2.25, 2.3)]
_bm = bmesh.new(); rngg = random.Random(5)
for i, (x, z) in enumerate(grape_spots):
    top = Vector((x, VINE_Y - 0.16, z)); L = rngg.uniform(0.17, 0.24)
    core = Matrix.Translation(top + Vector((0, 0, -L * 0.42))) @ Matrix.Diagonal((0.042 * L / 0.2, 0.042 * L / 0.2, L * 0.48, 1.0))
    bmesh.ops.create_icosphere(_bm, subdivisions=2, radius=1.0, matrix=core)
    for k in range(9):
        t = (k / 8) ** 0.9
        rad = lerp(0.05, 0.014, t) * L / 0.2
        a = k * 2.39996 + rngg.uniform(-0.3, 0.3)
        c = top + Vector((math.cos(a) * rad, math.sin(a) * rad, -t * L))
        bmesh.ops.create_icosphere(_bm, subdivisions=1, radius=rngg.uniform(0.014, 0.018), matrix=Matrix.Translation(c))
_gm = bpy.data.meshes.new("Grapes"); _bm.to_mesh(_gm); _bm.free()
_go = bpy.data.objects.new("Grapes", _gm); _gm.materials.append(M_GRAPES); link(_go)
for p_ in _gm.polygons: p_.use_smooth = True
for i, (x, z) in enumerate(grape_spots):
    cyl(f"GrapeStalk{i}", 0.006, 0.12, (x, VINE_Y - 0.15, z + 0.05), M_VINEWOOD, verts=4)

# ----------------------------------------------------------------------------- the spring and four running rills in channels, the violet beds
blob("SpringBasinStone", (SPRING.x, SPRING.y, terrain_h(SPRING.x, SPRING.y) - 0.18), 0.75, M_CHANNEL, scale=(1.0, 0.85, 0.32), subdiv=3, amp=0.15, seed=4.4)
disc_o = disc("SpringPool", 0.0, 0.55, 0.0, M_WATER, rings=2, seg=20)
disc_o.location = (SPRING.x, SPRING.y, terrain_h(SPRING.x, SPRING.y) + 0.07); disc_o.scale = (1.0, 0.82, 1.0)
for i in range(7):
    a = 2 * math.pi * i / 7 + 0.3
    blob(f"SpringRim{i}", (SPRING.x + 0.62 * math.cos(a), SPRING.y + 0.52 * math.sin(a), terrain_h(SPRING.x, SPRING.y) + 0.04), 0.16, M_CHANNEL, scale=(1.3, 1.0, 0.6), subdiv=1, amp=0.3, seed=i * 1.9)

def rill_centre(t):
    """Shared centreline of the four rills, t in 0..1 from the spring to the terrace edge."""
    y = lerp(SPRING.y - 0.5, -8.6, t)
    x = lerp(SPRING.x + 0.4, 0.8, t) + 0.6 * math.sin(t * 5.2 + 0.4) * smoothstep(0.0, 0.25, t)
    return x, y

RILLS = []
for k in range(4):
    off = (k - 1.5) * 0.52
    pts = []
    for i in range(25):
        t = i / 24
        x, y = rill_centre(t)
        fan = 1.0 + 0.9 * smoothstep(0.55, 1.0, t)                      # they turn apart towards the far beds
        wig = 0.18 * math.sin(t * 17.0 + k * 1.9) * smoothstep(0.05, 0.3, t)    # hither and thither
        sp = smoothstep(0.0, 0.12, t)
        pts.append((x + (off * fan + wig) * sp + off * 0.25 * (1 - sp), y))
    RILLS.append(pts)

def ribbon(name, pts2d, profile, mat, n=1):
    """A strip across a profile [(s, dz)] following a 2D path; z follows the terrain."""
    c = catmull([(p[0], p[1], 0.0) for p in pts2d], n)
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rows = []
    for i, p in enumerate(c):
        t = (c[min(i + 1, len(c) - 1)] - c[max(i - 1, 0)]); t.z = 0; t.normalize()
        side = Vector((-t.y, t.x, 0))
        rows.append([bm.verts.new((p.x + side.x * s, p.y + side.y * s, terrain_h(p.x + side.x * s, p.y + side.y * s) + dz)) for s, dz in profile])
    for a, b_ in zip(rows, rows[1:]):
        for k in range(len(profile) - 1): bm.faces.new((a[k], b_[k], b_[k + 1], a[k + 1]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

CHANNEL = [(-0.2, 0.005), (-0.11, 0.075), (-0.075, 0.03), (0.075, 0.03), (0.11, 0.075), (0.2, 0.005)]
for k, pts in enumerate(RILLS):
    ribbon(f"RillChannel{k}", pts, CHANNEL, M_CHANNEL)
    ribbon(f"RillWater{k}", pts, [(-0.08, 0.045), (0.08, 0.045)], M_WATER)

def near_rill(x, y, d):
    for pts in RILLS:
        for p in pts:
            if (p[0] - x) ** 2 + (p[1] - y) ** 2 < d * d: return True
    return False

def bed(name, cx, cy, rx, ry, rot, seed):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); seg = 22
    ca, sa = math.cos(rot), math.sin(rot)
    def pt(f, a):
        k = 1.0 + 0.18 * noise.noise(Vector((math.cos(a) * 1.2 + seed, math.sin(a) * 1.2, 0.0)))
        lx, ly = rx * f * k * math.cos(a), ry * f * k * math.sin(a)
        x, y = cx + lx * ca - ly * sa, cy + lx * sa + ly * ca
        return bm.verts.new((x, y, terrain_h(x, y) + (0.025 if f < 0.99 else 0.0)))
    c = bm.verts.new((cx, cy, terrain_h(cx, cy) + 0.028))
    r1 = [pt(0.55, 2 * math.pi * i / seg) for i in range(seg)]; r2 = [pt(1.0, 2 * math.pi * i / seg) for i in range(seg)]
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((c, r1[i], r1[j])); bm.faces.new((r1[i], r2[i], r2[j], r1[j]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_BED)
    for p in me.polygons: p.use_smooth = True
    return link(o)

BEDS = []
for i, t in enumerate([0.12, 0.36, 0.62, 0.9]):
    x, y = rill_centre(t)
    BEDS.append((x + 0.2, y, 1.7 + 0.5 * t, 1.3, 0.25 * i))
BEDS += [(-4.0, -5.4, 1.3, 1.0, 0.6), (3.9, -6.6, 1.4, 1.0, -0.5), (3.4, -3.4, 1.1, 0.8, 0.3), (-3.4, -8.6, 1.3, 0.9, 0.2)]
for i, (x, y, rx, ry, rot) in enumerate(BEDS):
    bed(f"VioletBed{i}", x, y, rx, ry, rot, i * 2.1)
# clumps of violets and luscious herbage on the beds, clear of the channels
rnd = random.Random(7)
nv = nh = 0
for (bx, by, rx, ry, rot) in BEDS:
    for _ in range(int(rx * ry * 4.0)):
        a = rnd.uniform(0, 2 * math.pi); f = math.sqrt(rnd.uniform(0, 0.85))
        lx, ly = rx * f * math.cos(a), ry * f * math.sin(a)
        x, y = bx + lx * math.cos(rot) - ly * math.sin(rot), by + lx * math.sin(rot) + ly * math.cos(rot)
        if near_rill(x, y, 0.3) or y > -2.0: continue
        z = terrain_h(x, y) + 0.02
        if rnd.random() < 0.6:
            blob(f"Violets{nv}", (x, y, z - 0.02), rnd.uniform(0.2, 0.3), M_VIOLETS, scale=(1.0, 0.9, 0.28), subdiv=2, amp=0.3, freq=2.5, seed=nv * 0.9, flat_bottom=0.0); nv += 1
        else:
            blob(f"Herbage{nh}", (x, y, z - 0.03), rnd.uniform(0.16, 0.24), M_HERBAGE, scale=(1.0, 1.0, 1.1), subdiv=2, amp=0.55, freq=3.2, seed=nh * 1.3, flat_bottom=0.0); nh += 1
print("clumps: violets", nv, "herbage", nh)

# ----------------------------------------------------------------------------- the hearth: a large fire of cedar and sandal wood
def hearth():
    hx, hy = HEARTH.x, HEARTH.y
    disc_a = disc("HearthAsh", 0.0, 0.5, 0.0, M_ASH, rings=2, seg=18); disc_a.location = (hx, hy, 0.012)
    for i in range(10):
        a = 2 * math.pi * i / 10 + random.uniform(-0.1, 0.1)
        blob(f"HearthStone{i}", (hx + 0.58 * math.cos(a), hy + 0.58 * math.sin(a), 0.0), random.uniform(0.12, 0.16), M_HEARTH, scale=(1.3, 1.0, 0.75), subdiv=2, amp=0.3, seed=i * 1.7, flat_bottom=-0.02,
             rot=(0, 0, a))
    disc_e = disc("HearthEmbers", 0.0, 0.3, 0.0, M_EMBERS, rings=2, seg=14); disc_e.location = (hx, hy, 0.03)
    # logs leaning together over the embers (cedar and sandal wood)
    for i in range(6):
        a = 2 * math.pi * i / 6 + 0.2
        tilt = math.radians(58)
        o = cyl(f"HearthLog{i}", 0.045, 0.62, (0, 0, 0), M_LOGS, verts=7)
        o.rotation_euler = (0, tilt, a)
        d = Vector((math.cos(a), math.sin(a), 0)) * 0.13
        o.location = (hx - d.x * 1.0, hy - d.y * 1.0, 0.16)
        # point each log's top towards the centre
        o.rotation_euler = (Vector((hx, hy, 0.36)) - Vector((hx + math.cos(a) * 0.3, hy + math.sin(a) * 0.3, 0.05))).to_track_quat('Z', 'Y').to_euler()
        o.location = (hx + math.cos(a) * 0.17, hy + math.sin(a) * 0.17, 0.2)
    # flames: tongues of fire rising from the embers
    for i, (dx, dy, s, tw) in enumerate([(0.0, 0.0, 1.0, 0.0), (0.09, 0.05, 0.7, 0.5), (-0.08, 0.06, 0.75, 1.2), (0.03, -0.09, 0.65, 2.1), (-0.06, -0.06, 0.55, 2.9), (0.1, -0.03, 0.5, 3.6)]):
        prof = [(0.0, 0.0), (0.09 * s, 0.04), (0.10 * s, 0.13 * s), (0.08 * s, 0.26 * s), (0.045 * s, 0.42 * s), (0.015 * s, 0.56 * s), (0.0, 0.64 * s)]
        lathe(f"Flame{i}", prof, (HEARTH.x + dx, HEARTH.y + dy, 0.05), M_FLAME, steps=7, wobble=0.35, seed=tw,
              rot=(random.uniform(-0.12, 0.12), random.uniform(-0.12, 0.12), tw))
    # a stack of split cedar beside the hearth
    for i in range(7):
        row, col = divmod(i, 4)
        cyl(f"Woodpile{i}", 0.05, 0.7, (hx + 0.55 + col * 0.105 + row * 0.05, hy + 0.85, 0.05 + row * 0.09), M_LOGS, verts=6, rot=(0, math.radians(90), math.radians(70)))
hearth()

# ----------------------------------------------------------------------------- the loom (an upright warp-weighted loom), the golden shuttle resting in the warp
def loom():
    parts = []
    W, Hgt = 1.9, 2.3
    lean = math.radians(9)
    for s in (-1, 1):
        parts.append(box(f"LoomUpright{s}", (0.09, 0.09, Hgt), (s * W / 2, 0, Hgt / 2), M_LOOMWOOD, bevel=0.01))
        parts.append(box(f"LoomBracket{s}", (0.06, 0.16, 0.06), (s * W / 2, 0.1, 1.02), M_LOOMWOOD, bevel=0.006))
        parts.append(box(f"LoomFork{s}", (0.07, 0.12, 0.12), (s * W / 2, 0.02, Hgt - 0.04), M_LOOMWOOD, bevel=0.008))
    parts.append(cyl("LoomClothBeam", 0.055, W + 0.25, (0, 0.02, Hgt - 0.12), M_LOOMWOOD, verts=12, rot=(0, math.radians(90), 0)))
    parts.append(cyl("LoomShedRod", 0.025, W + 0.05, (0, -0.03, 0.72), M_LOOMWOOD, verts=8, rot=(0, math.radians(90), 0)))
    parts.append(cyl("LoomHeddleBar", 0.022, W + 0.2, (0, 0.12, 1.06), M_LOOMWOOD, verts=8, rot=(0, math.radians(90), 0)))
    # the web already woven, wound from the cloth beam down to the fell
    fell = 1.22
    parts.append(box("LoomCloth", (W - 0.32, 0.012, Hgt - 0.17 - fell), (0, 0.065, (Hgt - 0.17 + fell) / 2), M_CLOTH))
    parts.append(cyl("LoomClothRoll", 0.075, W - 0.3, (0, 0.03, Hgt - 0.12), M_CLOTH, verts=12, rot=(0, math.radians(90), 0)))
    # warp threads in bundles fanning down to the clay loom weights
    nb = 16; span = W - 0.36
    for i in range(nb):
        x0 = -span / 2 + span * (i + 0.5) / nb
        for layer, (yy, zw) in enumerate([(0.07, 0.40), (-0.02, 0.33)]):
            xa, xb = x0 - span / nb * 0.3, x0 + span / nb * 0.3
            xw = x0 + (0.012 if layer else -0.012)
            me = bpy.data.meshes.new(f"Warp{i}_{layer}")
            ys = 0.068 if layer == 0 else 0.06
            me.from_pydata([(xa, ys, fell), (xb, ys, fell), (xw + 0.012, yy, zw + 0.06), (xw - 0.012, yy, zw + 0.06)], [], [(0, 1, 2, 3)])
            o = bpy.data.objects.new(f"Warp{i}_{layer}", me); me.materials.append(M_WARP); link(o)
            sol = o.modifiers.new("Solidify", 'SOLIDIFY'); sol.thickness = 0.003
            parts.append(o)
            parts.append(cyl(f"LoomWeight{i}_{layer}", 0.045, 0.1, (xw, yy, zw), M_TERRACOTTA, verts=4, r2=0.02, rot=(0, 0, math.radians(45))))
    # the golden shuttle lies in the shed at the fell, its point through the warp
    shut = lathe("GoldenShuttle", [(0.0, -0.24), (0.008, -0.21), (0.022, -0.14), (0.03, -0.05), (0.031, 0.0), (0.03, 0.05), (0.022, 0.14), (0.008, 0.21), (0.0, 0.24)],
                 (0.36, 0.1, fell - 0.05), M_GOLD, steps=12, rot=(0, math.radians(90), math.radians(-14)))
    parts.append(shut)
    parts.append(cyl("ShuttleYarn", 0.022, 0.13, (0.36, 0.1, fell - 0.05), M_CLOTH, verts=10, rot=(0, math.radians(90), math.radians(-14))))
    # the weft thread running from the shuttle back into the web
    parts.append(cyl("WeftThread", 0.003, 0.3, (0.2, 0.08, fell - 0.025), M_CLOTH, verts=4, rot=(0, math.radians(90 + 8), math.radians(-10))))
    g = group("Loom", parts)
    # stand it against the cave wall, leaning back, its face to the hearth and the mouth
    face = Vector((0.3, -0.25, 0)) - LOOM; yaw = math.atan2(face.y, face.x) - math.pi / 2
    g.location = LOOM; g.rotation_euler = Euler((0, 0, yaw)).to_matrix().to_4x4().to_euler()
    g.rotation_euler = (Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(-lean, 4, 'X')).to_euler()
    # a wool basket (kalathos) and a stool beside the loom, in the world frame
    fx, fy = math.cos(yaw), math.sin(yaw)            # the loom's local +X in the world
    bx, by = LOOM.x + fx * 1.25 + 0.35 * math.cos(yaw + math.pi / 2), LOOM.y + fy * 1.25 + 0.35 * math.sin(yaw + math.pi / 2)
    lathe("WoolBasket", [(0.0, 0.0), (0.12, 0.0), (0.2, 0.32), (0.18, 0.33), (0.1, 0.03), (0.0, 0.03)], (bx, by, 0.0), M_NEST, steps=12)
    for k in range(3):
        blob(f"WoolBall{k}", (bx + 0.06 * math.cos(k * 2.1), by + 0.06 * math.sin(k * 2.1), 0.27 + 0.03 * k), 0.07, M_CLOTH, subdiv=2, amp=0.1, seed=k)
    return g, yaw
loom_g, LOOM_YAW = loom()

# ----------------------------------------------------------------------------- furnishings: a seat and a table by the fire, jars and a fleece-strewn couch within
SEAT = Vector((1.25, 3.0, 0.0))
box("SeatBody", (0.55, 0.5, 0.42), (SEAT.x, SEAT.y, 0.21), M_LOOMWOOD, bevel=0.02, rot=(0, 0, 0.5))
blob("SeatFleece", (SEAT.x, SEAT.y, 0.44), 0.32, M_FLEECE, scale=(1.0, 0.9, 0.22), subdiv=2, amp=0.2, seed=2.0, rot=(0, 0, 0.5))
TABLE = Vector((1.05, 2.0, 0.0))
cyl("TableTop", 0.36, 0.05, (TABLE.x, TABLE.y, 0.6), M_LOOMWOOD, verts=16)
for i in range(3):
    a = 2 * math.pi * i / 3 + 0.4
    cyl(f"TableLeg{i}", 0.025, 0.58, (TABLE.x + 0.24 * math.cos(a), TABLE.y + 0.24 * math.sin(a), 0.29), M_LOOMWOOD, verts=6)
lathe("NectarBowl", [(0.0, 0.0), (0.05, 0.0), (0.06, 0.02), (0.15, 0.08), (0.16, 0.09), (0.13, 0.085), (0.0, 0.04)], (TABLE.x + 0.05, TABLE.y - 0.04, 0.625), M_GOLD, steps=14)
for i, (x, y, s) in enumerate([(-1.6, 5.4, 1.0), (-1.05, 5.75, 0.85), (-2.1, 4.9, 0.9)]):
    lathe(f"Amphora{i}", [(0.0, 0.0), (0.05 * s, 0.0), (0.16 * s, 0.18 * s), (0.22 * s, 0.4 * s), (0.2 * s, 0.6 * s), (0.1 * s, 0.75 * s), (0.065 * s, 0.82 * s), (0.08 * s, 0.86 * s), (0.0, 0.86 * s)],
          (x, y, 0.0), M_TERRACOTTA, steps=12, rot=(0, 0, i))
box("CouchBase", (2.0, 0.95, 0.38), (0.9, 5.6, 0.19), M_BOULDER, bevel=0.04, rot=(0, 0, 0.12))
blob("CouchFleece", (0.9, 5.55, 0.42), 0.6, M_FLEECE, scale=(1.75, 0.85, 0.25), subdiv=3, amp=0.15, seed=5.0, rot=(0, 0, 0.12))

# ----------------------------------------------------------------------------- anchors
anchor("reader.entrance", (0.0, 0.0, 0.0))                 # the reader stands here, just inside the mouth, facing -Y (out)
anchor("reader.look", (0.0, -3.0, 1.5))                    # eye-height point out through the mouth
anchor("scene.centre", (0.0, 1.5, 0.0))
anchor("cave.hearth", (HEARTH.x, HEARTH.y, 0.0))
anchor("cave.loom", (LOOM.x, LOOM.y, 0.0))
anchor("cave.mouth", (0.0, FRONT_Y - WALL_T / 2, 0.0))
anchor("garden.spring", (SPRING.x, SPRING.y, terrain_h(SPRING.x, SPRING.y)))
anchor("shore.rock", (-3.5, -17.6, terrain_h(-3.5, -17.6) + 0.6))

# ----------------------------------------------------------------------------- lights: Mediterranean sun, cool sky fill, the hearth fire
def light_obj(name, kind, energy, color, loc, direction=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if direction is not None: lo.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return link(lo)
sun = light_obj("light.sun", 'SUN', 4.6, (1.0, 0.92, 0.78), (-6, -6, 12), direction=-SUN_DIR, angle=math.radians(1.0))
sky_l = light_obj("light.sky", 'SUN', 0.35, (0.62, 0.75, 1.0), (0, 0, 14), direction=(0.1, 0.15, -1.0), angle=math.radians(60))
sky_l.data.use_shadow = False
fire = light_obj("Fire_Light", 'POINT', 260.0, (1.0, 0.56, 0.24), (HEARTH.x, HEARTH.y, 0.45), shadow_soft_size=0.25)

# world: physical sky for render only (the glTF carries the SkyDome mesh for Unity instead)
world = bpy.data.worlds.new("Ogygia"); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]
try:
    skyn = wn.nodes.new("ShaderNodeTexSky")
    skyn.sky_type = 'MULTIPLE_SCATTERING'
    skyn.sun_disc = False
    skyn.sun_elevation = math.asin(SUN_DIR.z)
    skyn.sun_rotation = math.atan2(SUN_DIR.x, SUN_DIR.y)
    skyn.altitude = 100
    wn.links.new(skyn.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.22
except Exception as e:
    print("sky texture unavailable:", e)
    bg.inputs["Color"].default_value = (0.45, 0.6, 0.85, 1); bg.inputs["Strength"].default_value = 0.8

# ----------------------------------------------------------------------------- cameras for preview stills (reader eye 1.55 m)
def camera(name, loc, look_at, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 150
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co
cams = [
    camera("Cam_Reader", (0.0, 0.0, 1.55), (0.0, -8.0, 1.15), lens=16),
    camera("Cam_Hearth", (0.0, 0.0, 1.55), (HEARTH.x, HEARTH.y, 0.6), lens=18),
    camera("Cam_Loom", (0.0, 0.0, 1.55), (LOOM.x, LOOM.y, 1.2), lens=18),
    camera("Cam_Interior", (0.4, 5.2, 1.65), (0.0, -3.0, 1.1), lens=16),
    camera("Cam_Outside", (1.2, -9.5, 2.3), (0.0, -1.0, 1.8), lens=20),
]
CAM_EXPOSURE = {"Cam_Hearth": 0.6, "Cam_Loom": 0.6, "Cam_Interior": 0.5}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "calypsos_cave_source.blend"))

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
        scene.render.filepath = os.path.join(OUT, f"render_{c.name[4:].lower()}.png")
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:                                  # GPU busy/out of memory (other renders in parallel): fall back to CPU
            print("GPU render failed, retrying on CPU:", str(e)[:120]); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)
    scene.view_settings.exposure = 0.0

# ----------------------------------------------------------------------------- bake + merge + export for Unity
FAR_MATS = {"M_FarSea": "far.Sea", "M_Headland": "far.Headland_Distant", "M_FarTrees": "far.FarTrees", "M_SkyDome": "SkyDome"}

def bake_and_export():
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')                       # apply modifiers everywhere
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes:                                            # nothing here is script-controlled: unparent, keep the world transform
        if o.parent is not None:
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
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
    scene.render.bake.margin = 6
    scene.render.bake.use_selected_to_active = False
    T = args.tex
    size_for = {"M_Ground": T * 2, "M_CaveRock": T, "M_CaveFloor": T, "M_SkyDome": T // 2, "M_Sea": T // 2, "M_VineLeaves": T // 2,
                "M_AlderLeaves": T // 2, "M_PoplarLeaves": T // 2, "M_Cypress": T // 2, "M_VioletBed": T // 2, "M_Violets": T // 2,
                "M_Herbage": T // 2, "M_Cloth": T // 2, "M_Warp": T // 2, "M_ChannelStone": T // 2, "M_Boulder": T // 2, "M_LoomWood": T // 2,
                "M_FarSea": T // 4, "M_Headland": T // 4, "M_FarTrees": T // 8, "M_Flame": T // 16, "M_Gold": T // 16, "M_Water": T // 8,
                "M_Embers": T // 8, "M_Ash": T // 8}
    bakedir = os.path.join(OUT, "bake_png"); os.makedirs(bakedir, exist_ok=True)

    def bake_object(o, label, size):
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
        bpy.ops.object.mode_set(mode='OBJECT')
        m = o.data.materials[0]; nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        metallic = bsdf.inputs["Metallic"].default_value
        emis = bsdf.inputs["Emission Strength"].default_value; ecol = tuple(bsdf.inputs["Emission Color"].default_value); elinked = bsdf.inputs["Emission Color"].is_linked
        imgs = {}
        for pass_name, btype, extra, noncolor in [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]:
            img = bpy.data.images.new(f"T_{label}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            for n in nt.nodes: n.select = False
            tex.select = True; nt.nodes.active = tex
            bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            img.filepath_raw = os.path.join(bakedir, img.name + ".png"); img.file_format = 'PNG'; img.save(); img.pack()
            imgs[pass_name] = img
            print("baked", img.name, size)
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
        if emis > 0:
            nb.inputs["Emission Strength"].default_value = min(emis, 6.0)
            if elinked: nt2.links.new(tb.outputs["Color"], nb.inputs["Emission Color"])
            else: nb.inputs["Emission Color"].default_value = ecol
        o.data.materials.clear(); o.data.materials.append(bm_)
        for p in o.data.polygons: p.material_index = 0

    for o in merged:
        base = o.data.materials[0].name
        bake_object(o, base[2:], max(64, size_for.get(base, T // 4)))
    for c in cams: bpy.data.objects.remove(c)
    gl = os.path.join(OUT, "calypsos_cave.gltf")   # .gltf + textures/: Unity imports the images as compressed (ASTC) textures
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False)
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            img = next((n.image for n in o.data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE'), None)
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={img.size[0] if img else 0}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "calypsos_cave_baked.blend"))

if args.bake or args.export:
    bake_and_export()
print("DONE")
