"""
Fable: A Mad Tea-Party (Alice's Adventures in Wonderland, chapter VII).

"There was a table set out under a tree in front of the house, and the March Hare and the
Hatter were having tea at it: a Dormouse was sitting between them, fast asleep, and the other
two were using it as a cushion, resting their elbows on it ..."
"... the chimneys were shaped like ears and the roof was thatched with fur." (chapter VI)

Builds the environment procedurally in Blender (no downloaded models or textures), with PBR
node materials and outdoor afternoon light (sun + sky), then (by flag) renders Cycles preview
stills, bakes materials to textures, merges static meshes by material, merges every
script-controlled group into one atlas-baked mesh, and exports a GLB for Unity.

Node naming (what SceneRegistry resolves): anchors are empties "anchor.<manifest anchor id>",
script-controlled assets are empties named by their exact manifest id ("prop.tea-table",
"char.hatter", "fx.steam" ...), lights are named by their exact manifest light id
("light.sun", "light.sky", "light.fill"). "anchor.scene.centre" is the miniature pivot.

Axes: Blender +Z up. The reader stands at anchor.reader.path (world origin) facing Blender -Y,
which glTFast imports as Unity +Z (glTF Y-up export, glTFast negates X).

Run headless:
  blender -b -P blender/build_mad_tea_party.py -- --out out/mad-tea-party --quick --render
  blender -b -P blender/build_mad_tea_party.py -- --out out/mad-tea-party --render --bake --export --samples 96 --res 1280
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, Euler, noise

# ----------------------------------------------------------------------------- args
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/mad-tea-party")
ap.add_argument("--render", action="store_true")
ap.add_argument("--bake", action="store_true")
ap.add_argument("--export", action="store_true")
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--res", type=int, default=1600)
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--quick", action="store_true", help="low samples for iteration")
ap.add_argument("--cams", default="", help="comma list of camera names to render (default all)")
args = ap.parse_args(argv)
OUT = os.path.abspath(args.out)
os.makedirs(OUT, exist_ok=True)
random.seed(1865)

# ----------------------------------------------------------------------------- dimensions (metres)
TABLE_H = 0.74
TABLE_L, TABLE_W = 4.4, 1.1
TX, TY = 0.0, -2.6                     # table centre (floor)
SEAT_H = 0.46
HATTER_SEAT = (1.55, -3.55)            # chair centre, facing +Y
HARE_SEAT = (2.55, -2.95)              # chair at the east end, facing -X (turned a little to the reader)
HARE_YAW = math.radians(90 - 22)       # local +Y forward -> world direction
DORMOUSE = (1.98, -2.98)               # on the table top at the corner between them
ARMCHAIR = (-2.78, -2.6)               # the large arm-chair at the empty west end, facing +X
TREE = (4.1, -5.0)
HOUSE_X, HOUSE_Y = -3.2, -8.6          # centre of the house front wall (front faces +Y)
HOUSE_W, HOUSE_D, WALL_H = 6.2, 4.4, 2.7
SUN_DIR = Vector((0.36, 0.30, 0.88)).normalized()   # direction towards the sun

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
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print("Metal not available, CPU render:", e)
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 0.0

COLL = bpy.data.collections.new("MadTeaParty")
scene.collection.children.link(COLL)

def link(obj):
    COLL.objects.link(obj)
    return obj

# ----------------------------------------------------------------------------- material helpers (from build_hall_of_doors.py)
MATS = {}

def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    MATS[name] = m
    return m, nt, bsdf

def node(nt, kind, loc=(0, 0), **props):
    n = nt.nodes.new(kind); n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n

def ramp(nt, stops, loc=(0, 0)):
    r = nt.nodes.new("ShaderNodeValToRGB"); r.location = loc
    cr = r.color_ramp
    while len(cr.elements) > 1:
        cr.elements.remove(cr.elements[-1])
    cr.elements[0].position, cr.elements[0].color = stops[0]
    for pos, col in stops[1:]:
        e = cr.elements.new(pos); e.color = col
    return r

def texcoord_obj(nt, loc=(-1400, 0)):
    tc = node(nt, "ShaderNodeTexCoord", loc)
    mp = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    return mp

def bump_from(nt, b, height_socket, strength, distance):
    bump = node(nt, "ShaderNodeBump", (50, -300)); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return bump

def c4(c):
    return (c[0], c[1], c[2], 1)

def scaled(c, k):
    return tuple(min(1.0, x * k) for x in c)

def wood(name, base=(0.32, 0.17, 0.08), dark=(0.09, 0.045, 0.02), light=(0.55, 0.33, 0.15), scale=1.0, rough=(0.35, 0.6), grain_dir=(1, 1, 14), bands='Z'):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    mp.inputs["Scale"].default_value = (grain_dir[0] * scale, grain_dir[1] * scale, grain_dir[2] * scale)
    wave = node(nt, "ShaderNodeTexWave", (-1000, 200), wave_type='BANDS', bands_direction=bands)
    wave.inputs["Scale"].default_value = 1.2
    wave.inputs["Distortion"].default_value = 9.0
    wave.inputs["Detail"].default_value = 6.0
    wave.inputs["Detail Scale"].default_value = 1.5
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    fine = node(nt, "ShaderNodeTexNoise", (-1000, -150))
    fine.inputs["Scale"].default_value = 60.0 * scale
    fine.inputs["Detail"].default_value = 8.0
    fine.inputs["Roughness"].default_value = 0.7
    nt.links.new(mp.outputs["Vector"], fine.inputs["Vector"])
    mix = node(nt, "ShaderNodeMix", (-700, 100), data_type='FLOAT')
    mix.inputs["Factor"].default_value = 0.22
    nt.links.new(wave.outputs["Fac"], mix.inputs[2])
    nt.links.new(fine.outputs["Fac"], mix.inputs[3])
    mid = tuple((b_ + l) / 2 for b_, l in zip(base, light))
    lite = tuple((m_ + l) / 2 for m_, l in zip(mid, light))
    r = ramp(nt, [(0.0, c4(dark)), (0.2, c4(base)), (0.5, c4(mid)), (0.72, c4(lite)), (0.9, c4(base))], (-450, 100))
    nt.links.new(mix.outputs[0], r.inputs["Fac"])
    geo = node(nt, "ShaderNodeNewGeometry", (-700, -350))
    pr = ramp(nt, [(0.48, (0, 0, 0, 1)), (0.56, (1, 1, 1, 1))], (-450, -350))
    nt.links.new(geo.outputs["Pointiness"], pr.inputs["Fac"])
    wear = node(nt, "ShaderNodeMix", (-150, 100), data_type='RGBA', blend_type='MIX')
    nt.links.new(pr.outputs["Color"], wear.inputs["Factor"])
    nt.links.new(r.outputs["Color"], wear.inputs[6])
    wear.inputs[7].default_value = (light[0] * 1.1, light[1] * 1.1, light[2] * 1.05, 1)
    nt.links.new(wear.outputs[2], b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", (-150, -200))
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough[1], rough[0]
    nt.links.new(wave.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    bump_from(nt, b, mix.outputs[0], 0.4, 0.003)
    b.inputs["Coat Weight"].default_value = 0.12
    b.inputs["Coat Roughness"].default_value = 0.35
    return m

def painted_wood(name, paint=(0.12, 0.2, 0.14)):
    return wood(name, base=paint, dark=scaled(paint, 0.6), light=scaled(paint, 1.25), rough=(0.32, 0.55), grain_dir=(14, 1, 1), bands='X')

def noisy(name, colors, scale=8.0, rough=0.8, bump=0.2, bump_dist=0.003, detail=6.0, stretch=(1, 1, 1), sheen=0.0, sss=0.0, coat=0.0, metallic=0.0, warp=0.0):
    """Generic organic surface: a colour ramp over fractal noise in object space, with bump."""
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    mp.inputs["Scale"].default_value = stretch
    n = node(nt, "ShaderNodeTexNoise", (-1000, 0)); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = 0.6
    n.inputs["Distortion"].default_value = warp
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    stops = [(i / max(1, len(colors) - 1) * 0.6 + 0.2, c4(c)) for i, c in enumerate(colors)]
    r = ramp(nt, stops, (-700, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.4
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss; b.inputs["Subsurface Radius"].default_value = (0.4, 0.2, 0.12)
    if coat:
        b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.08
    if bump:
        fine = node(nt, "ShaderNodeTexNoise", (-1000, -350)); fine.inputs["Scale"].default_value = scale * 6; fine.inputs["Detail"].default_value = 4
        nt.links.new(mp.outputs["Vector"], fine.inputs["Vector"])
        bump_from(nt, b, fine.outputs["Fac"], bump, bump_dist)
    return m

def plain(name, color, rough=0.5, metallic=0.0, emission=None, strength=0.0, coat=0.0, sss=0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = c4(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if emission:
        b.inputs["Emission Color"].default_value = c4(emission); b.inputs["Emission Strength"].default_value = strength
    if coat:
        b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.05
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss; b.inputs["Subsurface Radius"].default_value = (0.5, 0.25, 0.15)
    return m

def grass(name="M_Grass"):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    big = node(nt, "ShaderNodeTexNoise", (-1000, 300)); big.inputs["Scale"].default_value = 0.12; big.inputs["Detail"].default_value = 4
    nt.links.new(mp.outputs["Vector"], big.inputs["Vector"])
    mid = node(nt, "ShaderNodeTexNoise", (-1000, 0)); mid.inputs["Scale"].default_value = 1.6; mid.inputs["Detail"].default_value = 8; mid.inputs["Roughness"].default_value = 0.65
    nt.links.new(mp.outputs["Vector"], mid.inputs["Vector"])
    blades = node(nt, "ShaderNodeTexVoronoi", (-1000, -300)); blades.inputs["Scale"].default_value = 70
    nt.links.new(mp.outputs["Vector"], blades.inputs["Vector"])
    mx = node(nt, "ShaderNodeMix", (-700, 150), data_type='FLOAT'); mx.inputs["Factor"].default_value = 0.45
    nt.links.new(big.outputs["Fac"], mx.inputs[2]); nt.links.new(mid.outputs["Fac"], mx.inputs[3])
    r = ramp(nt, [(0.25, (0.045, 0.085, 0.018, 1)), (0.45, (0.10, 0.17, 0.035, 1)), (0.62, (0.17, 0.25, 0.06, 1)), (0.8, (0.30, 0.31, 0.10, 1))], (-450, 150))
    nt.links.new(mx.outputs[0], r.inputs["Fac"])
    sh = node(nt, "ShaderNodeMix", (-150, 150), data_type='RGBA', blend_type='MULTIPLY'); sh.inputs["Factor"].default_value = 0.35
    br = ramp(nt, [(0.0, (0.55, 0.6, 0.5, 1)), (0.6, (1, 1, 1, 1))], (-700, -300))
    nt.links.new(blades.outputs["Distance"], br.inputs["Fac"])
    nt.links.new(r.outputs["Color"], sh.inputs[6]); nt.links.new(br.outputs["Color"], sh.inputs[7])
    nt.links.new(sh.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.88
    b.inputs["Sheen Weight"].default_value = 0.4; b.inputs["Sheen Tint"].default_value = (0.8, 1.0, 0.6, 1)
    bump_from(nt, b, blades.outputs["Distance"], 0.5, 0.01)
    return m

def gravel(name="M_Gravel"):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 200)); v.inputs["Scale"].default_value = 28; v.inputs["Randomness"].default_value = 1.0
    nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    n = node(nt, "ShaderNodeTexNoise", (-1000, -150)); n.inputs["Scale"].default_value = 3; n.inputs["Detail"].default_value = 6
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    stones = ramp(nt, [(0.0, (0.26, 0.21, 0.15, 1)), (0.35, (0.40, 0.34, 0.25, 1)), (0.7, (0.50, 0.45, 0.36, 1)), (1.0, (0.34, 0.30, 0.24, 1))], (-700, 300))
    nt.links.new(v.outputs["Color"], stones.inputs["Fac"])
    edge = ramp(nt, [(0.0, (1, 1, 1, 1)), (0.85, (1, 1, 1, 1)), (1.0, (0.45, 0.4, 0.33, 1))], (-700, 50))
    nt.links.new(v.outputs["Distance"], edge.inputs["Fac"])
    m1 = node(nt, "ShaderNodeMix", (-400, 200), data_type='RGBA', blend_type='MULTIPLY'); m1.inputs["Factor"].default_value = 0.6
    nt.links.new(stones.outputs["Color"], m1.inputs[6]); nt.links.new(edge.outputs["Color"], m1.inputs[7])
    dirt = ramp(nt, [(0.3, (0.75, 0.68, 0.55, 1)), (0.7, (1, 1, 1, 1))], (-700, -150))
    nt.links.new(n.outputs["Fac"], dirt.inputs["Fac"])
    m2 = node(nt, "ShaderNodeMix", (-150, 200), data_type='RGBA', blend_type='MULTIPLY'); m2.inputs["Factor"].default_value = 1.0
    nt.links.new(m1.outputs[2], m2.inputs[6]); nt.links.new(dirt.outputs["Color"], m2.inputs[7])
    nt.links.new(m2.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
    inv = node(nt, "ShaderNodeMath", (-400, -350), operation='SUBTRACT'); inv.inputs[0].default_value = 1.0
    nt.links.new(v.outputs["Distance"], inv.inputs[1])
    bump_from(nt, b, inv.outputs[0], 0.7, 0.008)
    return m

def bark(name="M_Bark"):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt); mp.inputs["Scale"].default_value = (9, 9, 0.7)
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 200), feature='DISTANCE_TO_EDGE'); v.inputs["Scale"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    n = node(nt, "ShaderNodeTexNoise", (-1000, -150)); n.inputs["Scale"].default_value = 6; n.inputs["Detail"].default_value = 8; n.inputs["Distortion"].default_value = 1.5
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    crack = ramp(nt, [(0.0, (0.03, 0.022, 0.016, 1)), (0.06, (0.16, 0.12, 0.085, 1)), (0.3, (0.30, 0.24, 0.17, 1))], (-700, 200))
    nt.links.new(v.outputs["Distance"], crack.inputs["Fac"])
    moss = ramp(nt, [(0.55, (1, 1, 1, 1)), (0.75, (0.45, 0.55, 0.25, 1))], (-700, -150))
    nt.links.new(n.outputs["Fac"], moss.inputs["Fac"])
    mx = node(nt, "ShaderNodeMix", (-350, 200), data_type='RGBA', blend_type='MULTIPLY'); mx.inputs["Factor"].default_value = 0.8
    nt.links.new(crack.outputs["Color"], mx.inputs[6]); nt.links.new(moss.outputs["Color"], mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.92
    hm = node(nt, "ShaderNodeMath", (-350, -300), operation='MULTIPLY_ADD'); hm.inputs[1].default_value = 0.6
    nt.links.new(v.outputs["Distance"], hm.inputs[0]); nt.links.new(n.outputs["Fac"], hm.inputs[2])
    bump_from(nt, b, hm.outputs[0], 0.9, 0.02)
    return m

def leaves(name="M_Leaves", tint=(0.08, 0.17, 0.03), light=(0.24, 0.36, 0.07)):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 200)); v.inputs["Scale"].default_value = 14; v.inputs["Randomness"].default_value = 1
    nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    n = node(nt, "ShaderNodeTexNoise", (-1000, -150)); n.inputs["Scale"].default_value = 1.2; n.inputs["Detail"].default_value = 3
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    mx = node(nt, "ShaderNodeMix", (-700, 150), data_type='FLOAT'); mx.inputs["Factor"].default_value = 0.5
    nt.links.new(v.outputs["Color"], mx.inputs[2]); nt.links.new(n.outputs["Fac"], mx.inputs[3])
    r = ramp(nt, [(0.2, c4(scaled(tint, 0.6))), (0.5, c4(tint)), (0.8, c4(light))], (-450, 150))
    nt.links.new(mx.outputs[0], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    b.inputs["Subsurface Weight"].default_value = 0.15; b.inputs["Subsurface Radius"].default_value = (0.2, 0.4, 0.1)
    b.inputs["Sheen Weight"].default_value = 0.3
    inv = node(nt, "ShaderNodeMath", (-400, -350), operation='SUBTRACT'); inv.inputs[0].default_value = 1.0
    nt.links.new(v.outputs["Distance"], inv.inputs[1])
    bump_from(nt, b, inv.outputs[0], 0.8, 0.03)
    return m

def fur(name, colors, stretch=(30, 30, 3), sheen=0.6, scale=1.0, bumpk=0.6):
    """Streaky fur: noise stretched along Z (down the slope / along the limb), soft sheen."""
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt); mp.inputs["Scale"].default_value = tuple(s * scale for s in stretch)
    n = node(nt, "ShaderNodeTexNoise", (-1000, 100)); n.inputs["Scale"].default_value = 1.5; n.inputs["Detail"].default_value = 9; n.inputs["Roughness"].default_value = 0.7; n.inputs["Distortion"].default_value = 0.6
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    big = node(nt, "ShaderNodeTexNoise", (-1000, -200)); big.inputs["Scale"].default_value = 3; big.inputs["Detail"].default_value = 2
    tc = node(nt, "ShaderNodeTexCoord", (-1300, -300)); nt.links.new(tc.outputs["Object"], big.inputs["Vector"])
    mx = node(nt, "ShaderNodeMix", (-700, 100), data_type='FLOAT'); mx.inputs["Factor"].default_value = 0.35
    nt.links.new(n.outputs["Fac"], mx.inputs[2]); nt.links.new(big.outputs["Fac"], mx.inputs[3])
    stops = [(0.25 + i * 0.5 / max(1, len(colors) - 1), c4(c)) for i, c in enumerate(colors)]
    r = ramp(nt, stops, (-450, 100))
    nt.links.new(mx.outputs[0], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.3
    bump_from(nt, b, n.outputs["Fac"], bumpk, 0.01 * scale)
    return m

def linen(name="M_Linen", color=(0.74, 0.74, 0.70)):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    wx = node(nt, "ShaderNodeTexWave", (-1000, 200), wave_type='BANDS', bands_direction='X'); wx.inputs["Scale"].default_value = 260; wx.inputs["Distortion"].default_value = 0.3
    wy = node(nt, "ShaderNodeTexWave", (-1000, -50), wave_type='BANDS', bands_direction='Y'); wy.inputs["Scale"].default_value = 260; wy.inputs["Distortion"].default_value = 0.3
    for w in (wx, wy): nt.links.new(mp.outputs["Vector"], w.inputs["Vector"])
    st = node(nt, "ShaderNodeTexNoise", (-1000, -300)); st.inputs["Scale"].default_value = 2.5; st.inputs["Detail"].default_value = 3
    nt.links.new(mp.outputs["Vector"], st.inputs["Vector"])
    weave = node(nt, "ShaderNodeMath", (-700, 100), operation='MULTIPLY'); nt.links.new(wx.outputs["Fac"], weave.inputs[0]); nt.links.new(wy.outputs["Fac"], weave.inputs[1])
    stain = ramp(nt, [(0.62, c4(color)), (0.75, (color[0] * 0.92, color[1] * 0.86, color[2] * 0.72, 1))], (-700, -300))
    nt.links.new(st.outputs["Fac"], stain.inputs["Fac"]); nt.links.new(stain.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.82
    b.inputs["Sheen Weight"].default_value = 0.5; b.inputs["Sheen Roughness"].default_value = 0.5
    b.inputs["Subsurface Weight"].default_value = 0.08
    bump_from(nt, b, weave.outputs[0], 0.12, 0.0006)
    return m

def checked(name, a, b_col, scale=14.0, rough=0.8):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    ch = node(nt, "ShaderNodeTexChecker", (-900, 0)); ch.inputs["Scale"].default_value = scale
    ch.inputs["Color1"].default_value = c4(a); ch.inputs["Color2"].default_value = c4(b_col)
    nt.links.new(mp.outputs["Vector"], ch.inputs["Vector"]); nt.links.new(ch.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Sheen Weight"].default_value = 0.4
    return m

def porcelain(name, pattern=None, base=(0.88, 0.88, 0.85)):
    m, nt, b = new_mat(name)
    b.inputs["Roughness"].default_value = 0.12
    b.inputs["Coat Weight"].default_value = 1.0; b.inputs["Coat Roughness"].default_value = 0.04
    b.inputs["Subsurface Weight"].default_value = 0.05
    if pattern is None:
        b.inputs["Base Color"].default_value = c4(base)
        return m
    mp = texcoord_obj(nt)
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 100), feature='DISTANCE_TO_EDGE'); v.inputs["Scale"].default_value = 70
    nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    n = node(nt, "ShaderNodeTexNoise", (-1000, -200)); n.inputs["Scale"].default_value = 18; n.inputs["Detail"].default_value = 3
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    mx = node(nt, "ShaderNodeMath", (-700, 0), operation='MULTIPLY'); nt.links.new(v.outputs["Distance"], mx.inputs[0]); nt.links.new(n.outputs["Fac"], mx.inputs[1])
    r = ramp(nt, [(0.0, c4(pattern)), (0.04, c4(pattern)), (0.07, c4(base))], (-450, 0))
    nt.links.new(mx.outputs[0], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    return m

def sky_dome_mat(name="M_SkyDome"):
    m, nt, b = new_mat(name)
    geo = node(nt, "ShaderNodeTexCoord", (-1000, 0))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-800, 0)); nt.links.new(geo.outputs["Object"], sep.inputs["Vector"])
    nrm = node(nt, "ShaderNodeMath", (-600, 0), operation='DIVIDE'); nrm.inputs[1].default_value = 45.0
    nt.links.new(sep.outputs["Z"], nrm.inputs[0])
    r = ramp(nt, [(0.0, (0.72, 0.80, 0.86, 1)), (0.12, (0.52, 0.68, 0.86, 1)), (0.55, (0.26, 0.45, 0.78, 1)), (1.0, (0.16, 0.32, 0.68, 1))], (-400, 0))
    nt.links.new(nrm.outputs[0], r.inputs["Fac"])
    cl = node(nt, "ShaderNodeTexNoise", (-800, -300)); cl.inputs["Scale"].default_value = 0.08; cl.inputs["Detail"].default_value = 6
    nt.links.new(geo.outputs["Object"], cl.inputs["Vector"])
    cr = ramp(nt, [(0.56, (0, 0, 0, 1)), (0.72, (1, 1, 1, 1))], (-500, -300))
    nt.links.new(cl.outputs["Fac"], cr.inputs["Fac"])
    mxc = node(nt, "ShaderNodeMix", (-150, 0), data_type='RGBA', blend_type='MIX')
    nt.links.new(cr.outputs["Color"], mxc.inputs["Factor"]); nt.links.new(r.outputs["Color"], mxc.inputs[6]); mxc.inputs[7].default_value = (0.95, 0.95, 0.93, 1)
    nt.links.new(mxc.outputs[2], b.inputs["Base Color"]); nt.links.new(mxc.outputs[2], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 1.0
    b.inputs["Roughness"].default_value = 1.0
    return m

# ----------------------------------------------------------------------------- materials
M_GRASS = grass()
M_GRAVEL = gravel()
M_BARK = bark()
M_LEAVES = leaves()
M_HEDGE = leaves("M_Hedge", tint=(0.05, 0.12, 0.03), light=(0.14, 0.24, 0.05))
M_FARTREES = leaves("M_FarTrees", tint=(0.07, 0.13, 0.05), light=(0.17, 0.25, 0.09))
M_THATCH = fur("M_FurThatch", [(0.10, 0.055, 0.03), (0.25, 0.14, 0.07), (0.40, 0.25, 0.13), (0.55, 0.40, 0.24)], stretch=(9, 9, 1.0), scale=1.0, bumpk=1.0)
M_EAR_PINK = noisy("M_EarPink", [(0.62, 0.36, 0.34), (0.75, 0.48, 0.44)], scale=6, rough=0.6, sss=0.3)
M_WHITEWASH = noisy("M_Whitewash", [(0.62, 0.58, 0.50), (0.78, 0.74, 0.66), (0.84, 0.81, 0.74)], scale=3, rough=0.92, bump=0.3, bump_dist=0.004)
M_STONE = noisy("M_Stone", [(0.22, 0.21, 0.19), (0.38, 0.36, 0.32), (0.48, 0.46, 0.41)], scale=5, rough=0.9, bump=0.8, bump_dist=0.01, warp=1.5)
M_DOOR = painted_wood("M_DoorGreen", (0.07, 0.17, 0.10))
M_FRAMEPAINT = painted_wood("M_WindowPaint", (0.70, 0.68, 0.60))
M_WINGLASS = plain("M_WindowGlass", (0.03, 0.04, 0.05), rough=0.05, coat=1.0)
M_TABLEWOOD = wood("M_TableWood", base=(0.25, 0.14, 0.07), dark=(0.07, 0.04, 0.02), light=(0.42, 0.26, 0.13))
M_CHAIRWOOD = wood("M_ChairWood", base=(0.30, 0.18, 0.09), dark=(0.09, 0.05, 0.025), light=(0.50, 0.32, 0.16), scale=1.5)
M_LINEN = linen()
M_VELVET = noisy("M_ArmchairVelvet", [(0.18, 0.02, 0.03), (0.34, 0.05, 0.06), (0.42, 0.08, 0.08)], scale=3, rough=0.85, sheen=1.0, bump=0.1, bump_dist=0.001)
M_PORCELAIN = porcelain("M_Porcelain")
M_PORC_BLUE = porcelain("M_PorcelainBlue", pattern=(0.08, 0.16, 0.48))
M_BROWNGLAZE = noisy("M_BrownGlaze", [(0.13, 0.05, 0.02), (0.24, 0.10, 0.04)], scale=4, rough=0.15, coat=1.0, bump=0.0)
M_TEA = plain("M_Tea", (0.22, 0.09, 0.03), rough=0.05, coat=0.5)
M_BREAD = noisy("M_Bread", [(0.80, 0.66, 0.42), (0.90, 0.80, 0.58)], scale=30, rough=0.9, bump=0.5, bump_dist=0.002)
M_CRUST = noisy("M_Crust", [(0.36, 0.18, 0.06), (0.52, 0.30, 0.12)], scale=20, rough=0.8)
M_BUTTER = plain("M_Butter", (0.92, 0.78, 0.32), rough=0.35, sss=0.2)
M_SKIN = noisy("M_Skin", [(0.72, 0.48, 0.36), (0.80, 0.56, 0.43)], scale=8, rough=0.5, sss=0.25, bump=0.05, bump_dist=0.0005)
M_HATFELT = noisy("M_HatFelt", [(0.20, 0.19, 0.16), (0.30, 0.28, 0.24)], scale=12, rough=0.85, sheen=0.6, bump=0.15, bump_dist=0.001)
M_HATBAND = plain("M_HatBand", (0.32, 0.04, 0.05), rough=0.5)
M_COAT = noisy("M_CoatGreen", [(0.03, 0.10, 0.06), (0.06, 0.17, 0.10)], scale=10, rough=0.8, sheen=0.5, bump=0.1, bump_dist=0.001)
M_WAISTCOAT = checked("M_Waistcoat", (0.72, 0.52, 0.12), (0.60, 0.40, 0.08), scale=40)
M_TROUSERS = checked("M_CheckTrousers", (0.62, 0.55, 0.42), (0.30, 0.26, 0.20), scale=22)
M_BOWTIE = plain("M_BowTieRed", (0.55, 0.04, 0.04), rough=0.45)
M_SHIRT = plain("M_Shirt", (0.88, 0.87, 0.83), rough=0.6)
M_SHOE = plain("M_Shoe", (0.03, 0.025, 0.02), rough=0.3, coat=0.6)
M_HAIR_HATTER = noisy("M_HatterHair", [(0.36, 0.20, 0.10), (0.52, 0.32, 0.16)], scale=40, rough=0.7, stretch=(1, 1, 6))
M_PAPER = noisy("M_Paper", [(0.86, 0.81, 0.68), (0.92, 0.88, 0.77)], scale=40, rough=0.95, bump=0.1, bump_dist=0.0003)
M_INK = plain("M_Ink", (0.015, 0.012, 0.01), rough=0.35)
M_EYE = plain("M_EyeWhite", (0.86, 0.85, 0.80), rough=0.15, coat=1.0)
M_HAREFUR = fur("M_HareFur", [(0.24, 0.14, 0.07), (0.42, 0.28, 0.15), (0.56, 0.42, 0.26)], stretch=(40, 40, 6), scale=1.0, bumpk=0.4)
M_MUZZLE = fur("M_HareMuzzle", [(0.62, 0.54, 0.44), (0.78, 0.71, 0.60)], stretch=(40, 40, 6), bumpk=0.3)
M_STRAW = noisy("M_Straw", [(0.62, 0.50, 0.20), (0.82, 0.70, 0.34)], scale=60, rough=0.6, stretch=(1, 1, 8), bump=0.0)
M_BOWTIE_BLUE = plain("M_BowTieBlue", (0.06, 0.12, 0.35), rough=0.45)
M_AMBER = plain("M_EyeAmber", (0.55, 0.30, 0.05), rough=0.1, coat=1.0)
M_DORMFUR = fur("M_DormouseFur", [(0.30, 0.17, 0.07), (0.50, 0.32, 0.14), (0.64, 0.46, 0.24)], stretch=(60, 60, 8), bumpk=0.35)
M_DORMBELLY = fur("M_DormouseBelly", [(0.72, 0.62, 0.46), (0.84, 0.76, 0.60)], stretch=(60, 60, 8), bumpk=0.25)
M_FLOWER_PINK = noisy("M_FlowerPink", [(0.70, 0.20, 0.32), (0.86, 0.45, 0.55), (0.92, 0.85, 0.80)], scale=18, rough=0.6, sss=0.2)
M_FLOWER_YEL = noisy("M_FlowerYellow", [(0.85, 0.65, 0.10), (0.95, 0.88, 0.50)], scale=18, rough=0.6, sss=0.2)
M_SKYDOME = sky_dome_mat()
M_DAPPLE = plain("M_Dapple", (0.80, 0.76, 0.62), rough=1.0, emission=(1.0, 0.88, 0.6), strength=0.35)
M_STEAM = plain("M_Steam", (0.95, 0.95, 0.95), rough=1.0, emission=(1, 1, 1), strength=0.25)

# ----------------------------------------------------------------------------- geometry helpers (from build_hall_of_doors.py)
def _finish(o, mat, smooth=True):
    o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0), smooth=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = 2; md.limit_method = 'ANGLE'; md.harden_normals = False
    return _finish(o, mat, smooth)

def cyl(name, r, h, loc, mat, verts=16, rot=(0, 0, 0), r2=None, bevel=True):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    if bevel:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = min(0.004, r * 0.2); md.segments = 1; md.limit_method = 'ANGLE'
    return _finish(o, mat)

def sphere(name, r, loc, mat, seg=12, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(6, seg // 2), radius=r, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.rotation_euler = rot
    return _finish(o, mat)

def torus(name, R, r, loc, mat, rot=(0, 0, 0), seg=24, rseg=8):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=rseg, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat)

def lathe(name, profile, loc, mat, steps=20, rot=(0, 0, 0)):
    """profile: list of (radius, z) from bottom to top; revolve around Z."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        if r < 1e-5:
            rings.append([bm.verts.new((0, 0, z))])
            continue
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / steps), r * math.sin(2 * math.pi * i / steps), z)) for i in range(steps)])
    for a, b_ in zip(rings, rings[1:]):
        if len(a) == 1 and len(b_) == 1: continue
        if len(a) == 1:
            for i in range(steps): bm.faces.new((a[0], b_[(i + 1) % steps], b_[i]) if False else (a[0], b_[i], b_[(i + 1) % steps]))
        elif len(b_) == 1:
            for i in range(steps): bm.faces.new((a[i], a[(i + 1) % steps], b_[0]))
        else:
            for i in range(steps):
                j = (i + 1) % steps
                bm.faces.new((a[i], a[j], b_[j], b_[i]))
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def limb(name, p1, p2, r1, r2, mat, verts=8):
    """Tapered cylinder from p1 to p2 (capped with nothing; ends hide inside joints)."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=d.length, location=(p1 + p2) / 2)
    o = bpy.context.active_object; o.name = name
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return _finish(o, mat)

def text_mesh(name, body, size, loc, mat, rot=(math.pi / 2, 0, 0), extrude=0.0003, align='CENTER'):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body; cu.size = size; cu.extrude = extrude; cu.align_x = align; cu.align_y = 'CENTER'; cu.resolution_u = 2
    o = bpy.data.objects.new(name, cu); o.location = loc; o.rotation_euler = rot
    link(o)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    o.data.materials.clear(); o.data.materials.append(mat)
    return o

def blob(name, loc, radius, mat, scale=(1, 1, 1), subdiv=1, amp=0.25, freq=1.6, seed=0.0, rot=(0, 0, 0)):
    """Lumpy organic clump: icosphere displaced by noise (foliage, hedges, roof lumps)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    for v in bm.verts:
        n = v.co.normalized()
        k = 1.0 + amp * noise.noise(n * freq + Vector((seed, seed * 1.7, seed * 0.3)))
        v.co = Vector((n.x * radius * k * scale[0], n.y * radius * k * scale[1], n.z * radius * k * scale[2]))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def group(name, objs, loc):
    """Parent objs under a named empty (exported as a glTF node Unity can find by name)."""
    e = bpy.data.objects.new(name, None); e.empty_display_size = 0.05; e.location = loc; link(e)
    bpy.context.view_layer.update()
    for o in objs:
        o.parent = e; o.matrix_parent_inverse = e.matrix_world.inverted()
    return e

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

class Frame:
    """Local frame for a seated figure or chair: +Y forward, +X right, origin on the floor."""
    def __init__(self, origin, yaw):
        self.o = Vector((origin[0], origin[1], 0.0)); self.yaw = yaw
        self.R = Matrix.Rotation(yaw, 3, 'Z')
    def p(self, x, y, z):
        return tuple(self.o + self.R @ Vector((x, y, z)))
    def r(self, rx=0.0, ry=0.0, rz=0.0):
        return (Matrix.Rotation(self.yaw, 4, 'Z') @ Euler((rx, ry, rz)).to_matrix().to_4x4()).to_euler()

DYNAMIC = []   # empties whose children are merged into one atlas-baked mesh per group

# ----------------------------------------------------------------------------- ground, paths, sky dome
def ground_disc(name, radius, mat, rings=14, seg=48):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    centre = bm.verts.new((0, 0, 0))
    prev = None
    allr = []
    for j in range(1, rings + 1):
        rr = radius * (j / rings) ** 1.6
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            x, y = rr * math.cos(a), rr * math.sin(a)
            # gentle undulation, flat near the table and the reader, rising to low banks at the edge
            flat = max(0.0, min(1.0, (rr - 7.0) / 10.0))
            z = flat * (0.25 * noise.noise(Vector((x * 0.12, y * 0.12, 0.3))) + 0.6 * flat * flat) - 0.002
            ring.append(bm.verts.new((x, y, z)))
        allr.append(ring)
    for i in range(seg):
        bm.faces.new((centre, allr[0][i], allr[0][(i + 1) % seg]))
    for a, b_ in zip(allr, allr[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b_[j], b_[i]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

ground = ground_disc("Ground", 30.0, M_GRASS)

def catmull(pts, n):
    pts = [Vector(p) for p in pts]
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    out.append(pts[-1])
    return out

def path_ribbon(name, pts, width, z=0.012, n=8, seed=0.0):
    c = catmull([(p[0], p[1], 0.0) for p in pts], n)
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rows = []
    for i, p in enumerate(c):
        t = (c[min(i + 1, len(c) - 1)] - c[max(i - 1, 0)]); t.z = 0; t.normalize()
        side = Vector((-t.y, t.x, 0))
        w = width / 2 * (1 + 0.12 * noise.noise(Vector((p.x * 0.7 + seed, p.y * 0.7, 0))))
        row = []
        for s in (-1.0, -0.6, 0.0, 0.6, 1.0):
            q = p + side * (s * w)
            dz = z if abs(s) < 0.9 else z * 0.25
            row.append(bm.verts.new((q.x, q.y, dz)))
        rows.append(row)
    for a, b_ in zip(rows, rows[1:]):
        for k in range(4):
            bm.faces.new((a[k], a[k + 1], b_[k + 1], b_[k]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_GRAVEL)
    for p in me.polygons: p.use_smooth = True
    return link(o)

# the garden walk the reader stands on, and the branch to the March Hare's door
path_ribbon("Path_Walk", [(-14, 2.2), (-7, 1.4), (-2.5, 0.4), (0, 0), (3, -0.3), (8, 0.6), (14, 2.4)], 1.5)
path_ribbon("Path_Door", [(-0.6, -0.2), (-2.2, -0.9), (-4.25, -2.6), (-4.35, -5.6), (HOUSE_X + 0.1, -7.6), (HOUSE_X, HOUSE_Y + 0.35)], 1.1, seed=3.0)

def sky_dome(name, radius=45.0):
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

# ----------------------------------------------------------------------------- the tea table, laid for many
def tablecloth(name, L, W, drop, loc):
    """Linen cloth: flat top plus a hanging skirt with soft folds, deeper at the hem."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    hx, hy, rc = L / 2, W / 2, 0.05
    # perimeter samples of a rounded rectangle
    per = []
    segs = [((-hx + rc, -hy), (hx - rc, -hy)), ((hx, -hy + rc), (hx, hy - rc)), ((hx - rc, hy), (-hx + rc, hy)), ((-hx, hy - rc), (-hx, -hy + rc))]
    centres = [(hx - rc, -hy + rc), (hx - rc, hy - rc), (-hx + rc, hy - rc), (-hx + rc, -hy + rc)]
    for k, (a, b_) in enumerate(segs):
        ln = math.dist(a, b_); n = max(2, int(ln / 0.085))
        for i in range(n):
            t = i / n
            per.append(((a[0] + (b_[0] - a[0]) * t, a[1] + (b_[1] - a[1]) * t), None))
        cx, cy = centres[k]; a0 = -math.pi / 2 + k * math.pi / 2
        for i in range(3):
            ang = a0 + (i / 3) * math.pi / 2
            per.append(((cx + rc * math.cos(ang), cy + rc * math.sin(ang)), None))
    pts = [Vector((p[0][0], p[0][1], 0)) for p in per]
    N = len(pts)
    rows = 4
    grid = []
    acc = 0.0
    for i in range(N):
        p = pts[i]; q = pts[(i + 1) % N]; pr = pts[i - 1]
        t = (q - pr); t.normalize(); out = Vector((t.y, -t.x, 0))
        if out.dot(p) < 0: out = -out
        acc += (q - p).length
        col = []
        for j in range(rows + 1):
            v = j / rows
            fold = 0.022 * math.sin(acc * 2 * math.pi / 0.32) * v ** 1.3 + 0.008 * math.sin(acc * 2 * math.pi / 0.11) * v
            flare = 0.012 + 0.03 * v ** 2
            pos = p + out * (flare + fold) + Vector((0, 0, -drop * v + 0.006 * math.sin(acc * 9) * v))
            if j == 0: pos = p + out * 0.012
            col.append(bm.verts.new(pos))
        grid.append(col)
    for i in range(N):
        a, b_ = grid[i], grid[(i + 1) % N]
        for j in range(rows):
            bm.faces.new((a[j], b_[j], b_[j + 1], a[j + 1]))
    top = bm.faces.new([grid[i][0] for i in range(N)])
    bmesh.ops.triangulate(bm, faces=[top])
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; me.materials.append(M_LINEN)
    for p in me.polygons: p.use_smooth = True
    return link(o)

table_parts = []
table_parts.append(box("Table_Top", (TABLE_L, TABLE_W, 0.04), (TX, TY, TABLE_H - 0.02), M_TABLEWOOD, bevel=0.006))
table_parts.append(box("Table_ApronN", (TABLE_L - 0.2, 0.025, 0.11), (TX, TY + TABLE_W / 2 - 0.06, TABLE_H - 0.095), M_TABLEWOOD))
table_parts.append(box("Table_ApronS", (TABLE_L - 0.2, 0.025, 0.11), (TX, TY - TABLE_W / 2 + 0.06, TABLE_H - 0.095), M_TABLEWOOD))
leg_profile = [(0.03, 0.0), (0.036, 0.09), (0.024, 0.3), (0.034, 0.44), (0.026, 0.52), (0.04, 0.6), (0.04, TABLE_H - 0.04)]
for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1), (0, -1), (0, 1)]):
    table_parts.append(lathe(f"Table_Leg{i}", leg_profile, (TX + sx * (TABLE_L / 2 - 0.1), TY + sy * (TABLE_W / 2 - 0.08), 0.0), M_TABLEWOOD, steps=8))
table_parts.append(tablecloth("Tablecloth", TABLE_L + 0.02, TABLE_W + 0.02, 0.34, (TX, TY, TABLE_H + 0.002)))
DYNAMIC.append(group("prop.tea-table", table_parts, (TX, TY, TABLE_H)))

# chairs: plain wooden ladder-backs laid down both sides ("laid for many"), static
def chair(name, origin, yaw, mat=M_CHAIRWOOD, back=True):
    f = Frame(origin, yaw)
    parts = []
    parts.append(box(f"{name}_Seat", (0.44, 0.42, 0.035), f.p(0, 0, SEAT_H), mat, bevel=0.006, rot=f.r()))
    for i, (x, y) in enumerate([(-0.19, 0.18), (0.19, 0.18), (-0.19, -0.18), (0.19, -0.18)]):
        h = SEAT_H if y > 0 or not back else SEAT_H + 0.5
        parts.append(cyl(f"{name}_Leg{i}", 0.018, h, f.p(x, y, h / 2), mat, verts=8, bevel=False))
    for i, x in enumerate((-0.19, 0.19)):
        parts.append(box(f"{name}_Stretcher{i}", (0.022, 0.36, 0.022), f.p(x, 0, 0.16), mat, rot=f.r()))
    if back:
        for k, z in enumerate((0.70, 0.82, 0.93)):
            parts.append(box(f"{name}_Slat{k}", (0.40, 0.022, 0.06), f.p(0, -0.185, z), mat, rot=f.r(rx=-0.06)))
    return parts

chairs = []
for i, x in enumerate((-1.45, -0.35, 0.75)):
    chairs += chair(f"ChairNear{i}", (x, TY + TABLE_W / 2 + 0.42), math.pi)            # near side, facing the table (-Y)
for i, x in enumerate((-1.5, -0.5, 0.5)):
    chairs += chair(f"ChairFar{i}", (x + 0.1, TY - TABLE_W / 2 - 0.42), 0.0)           # far side, facing the reader (+Y)
chairs += chair("ChairHatter", HATTER_SEAT, 0.0)
chairs += chair("ChairHare", HARE_SEAT, HARE_YAW)

# ----------------------------------------------------------------------------- the large arm-chair at the empty end
def armchair(origin, yaw):
    f = Frame(origin, yaw)
    P = []
    P.append(box("Armchair_Base", (0.78, 0.72, 0.30), f.p(0, 0, 0.27), M_VELVET, bevel=0.03, rot=f.r()))
    P.append(box("Armchair_Cushion", (0.58, 0.62, 0.13), f.p(0, 0.04, 0.47), M_VELVET, bevel=0.045, rot=f.r()))
    P.append(box("Armchair_Back", (0.78, 0.18, 0.86), f.p(0, -0.30, 0.78), M_VELVET, bevel=0.06, rot=f.r(rx=-0.12)))
    for s in (-1, 1):
        P.append(box(f"Armchair_Arm{s}", (0.13, 0.66, 0.30), f.p(s * 0.36, 0.0, 0.55), M_VELVET, bevel=0.05, rot=f.r()))
        P.append(cyl(f"Armchair_Roll{s}", 0.085, 0.66, f.p(s * 0.37, 0.02, 0.72), M_VELVET, verts=14, rot=f.r(rx=math.pi / 2)))
        P.append(box(f"Armchair_Wing{s}", (0.10, 0.22, 0.42), f.p(s * 0.36, -0.24, 1.0), M_VELVET, bevel=0.04, rot=f.r(rz=-s * 0.25)))
    for i, (x, y) in enumerate([(-0.33, 0.29), (0.33, 0.29), (-0.33, -0.29), (0.33, -0.29)]):
        P.append(lathe(f"Armchair_Foot{i}", [(0.03, 0.0), (0.035, 0.03), (0.026, 0.08), (0.04, 0.12), (0.0, 0.125)], f.p(x, y, 0), M_CHAIRWOOD, steps=10))
    # deep buttons on the back
    for i, (x, z) in enumerate([(-0.18, 0.75), (0.0, 0.75), (0.18, 0.75), (-0.09, 0.95), (0.09, 0.95)]):
        P.append(sphere(f"Armchair_Button{i}", 0.014, f.p(x, -0.2 + (z - 0.75) * -0.12, z), M_VELVET, seg=8))
    return P
DYNAMIC.append(group("prop.armchair", armchair(ARMCHAIR, -math.pi / 2), (ARMCHAIR[0], ARMCHAIR[1], 0.0)))

# ----------------------------------------------------------------------------- the tea service along the table
service = []
TOP = TABLE_H + 0.006
cup_profile = [(0.0, 0.0), (0.024, 0.0), (0.034, 0.02), (0.045, 0.062), (0.041, 0.062), (0.032, 0.024), (0.0, 0.012)]
saucer_profile = [(0.0, 0.0), (0.045, 0.002), (0.078, 0.016), (0.07, 0.014), (0.0, 0.008)]
plate_profile = [(0.0, 0.0), (0.075, 0.003), (0.115, 0.018), (0.105, 0.016), (0.0, 0.008)]

def teacup(name, x, y, mat, tipped=False, with_tea=True, yaw=0.0):
    parts = [lathe(f"{name}_Saucer", saucer_profile, (x, y, TOP), mat, steps=10)]
    cz = TOP + 0.008
    if tipped:
        c = lathe(f"{name}_Cup", cup_profile, (x + 0.09, y + 0.02, TOP + 0.042), mat, steps=14, rot=(0, math.radians(95), yaw))
        parts.append(c)
        return parts
    parts.append(lathe(f"{name}_Cup", cup_profile, (x, y, cz), mat, steps=10))
    h = torus(f"{name}_Handle", 0.016, 0.004, (x + 0.05 * math.cos(yaw), y + 0.05 * math.sin(yaw), cz + 0.036), mat, rot=(math.pi / 2, 0, yaw + math.pi / 2), seg=8, rseg=4)
    parts.append(h)
    if with_tea:
        parts.append(cyl(f"{name}_Tea", 0.037, 0.002, (x, y, cz + 0.048), M_TEA, verts=12, bevel=False))
    return parts

def teapot(name, x, y, mat, s=1.0, yaw=0.0):
    prof = [(0.0, 0.0), (0.05, 0.0), (0.07, 0.012), (0.085, 0.045), (0.088, 0.075), (0.078, 0.11), (0.055, 0.13), (0.045, 0.135)]
    prof = [(r * s, z * s) for r, z in prof]
    body = lathe(f"{name}_Body", prof, (x, y, TOP), mat, steps=16)
    lid = lathe(f"{name}_Lid", [(0.05 * s, 0.13 * s), (0.04 * s, 0.15 * s), (0.012 * s, 0.158 * s), (0.016 * s, 0.168 * s), (0.012 * s, 0.18 * s), (0.0, 0.18 * s)], (x, y, TOP), mat, steps=14)
    c, sn = math.cos(yaw), math.sin(yaw)
    sp0 = Vector((x + 0.07 * s * c, y + 0.07 * s * sn, TOP + 0.05 * s)); sp1 = Vector((x + 0.15 * s * c, y + 0.15 * s * sn, TOP + 0.12 * s))
    spout = limb(f"{name}_Spout", sp0, sp1, 0.022 * s, 0.009 * s, mat, verts=10)
    handle = torus(f"{name}_Handle", 0.045 * s, 0.009 * s, (x - 0.085 * s * c, y - 0.085 * s * sn, TOP + 0.075 * s), mat, rot=(math.pi / 2, 0, yaw + math.pi / 2), seg=14, rseg=6)
    return [body, lid, spout, handle], sp1

pots = []
p1, SPOUT1 = teapot("Teapot1", 0.35, TY - 0.05, M_PORC_BLUE, s=1.1, yaw=math.radians(-150)); service += p1
p2, _ = teapot("Teapot2", -1.15, TY + 0.06, M_BROWNGLAZE, s=1.0, yaw=math.radians(30)); service += p2
p3, _ = teapot("Teapot3", 1.25, TY + 0.1, M_PORCELAIN, s=0.9, yaw=math.radians(200)); service += p3
# cups at every place, some used and pushed about
for i, x in enumerate((-1.45, -0.35, 0.75)):
    service += teacup(f"CupNear{i}", x + random.uniform(-0.05, 0.05), TY + 0.36, M_PORCELAIN if i % 2 == 0 else M_PORC_BLUE, yaw=math.radians(random.uniform(-30, 30)), with_tea=i != 1)
for i, x in enumerate((-1.4, -0.4, 0.6)):
    service += teacup(f"CupFar{i}", x + random.uniform(-0.05, 0.05), TY - 0.36, M_PORC_BLUE if i % 2 == 0 else M_PORCELAIN, tipped=(i == 1), yaw=math.radians(random.uniform(150, 210)))
service += teacup("CupHatterPlace", 1.35, TY - 0.33, M_PORCELAIN, yaw=math.radians(180))
service += teacup("CupHarePlace", 1.85, TY - 0.08, M_PORC_BLUE, yaw=math.radians(-90))
service += teacup("CupAlice", -1.95, TY + 0.02, M_PORCELAIN, with_tea=False, yaw=math.radians(90))
# plates of bread-and-butter, the butter dish, milk jug and sugar bowl
for i, (x, y) in enumerate([(-0.85, TY - 0.05), (1.0, TY - 0.22), (-1.95, TY + 0.25)]):
    service.append(lathe(f"Plate{i}", plate_profile, (x, y, TOP), M_PORCELAIN, steps=18))
    for k in range(3 if i != 2 else 1):
        a = random.uniform(0, math.pi)
        service.append(box(f"Bread{i}_{k}", (0.075, 0.07, 0.012), (x + 0.02 * k - 0.02, y + 0.012 * k, TOP + 0.016 + 0.012 * k), M_BREAD, rot=(0, 0, a)))
service.append(lathe("ButterDish", [(0.0, 0.0), (0.06, 0.0), (0.065, 0.012), (0.0, 0.012)], (-0.15, TY - 0.15, TOP), M_PORCELAIN, steps=12))
service.append(box("Butter", (0.06, 0.04, 0.025), (-0.15, TY - 0.15, TOP + 0.024), M_BUTTER, bevel=0.004))
service.append(lathe("MilkJug", [(0.0, 0.0), (0.03, 0.0), (0.04, 0.03), (0.034, 0.07), (0.04, 0.095), (0.036, 0.095), (0.03, 0.07), (0.0, 0.06)], (0.05, TY + 0.22, TOP), M_PORCELAIN, steps=14))
service.append(lathe("SugarBowl", [(0.0, 0.0), (0.03, 0.0), (0.05, 0.03), (0.048, 0.055), (0.0, 0.055)], (0.65, TY + 0.12, TOP), M_PORC_BLUE, steps=14))
service.append(lathe("SugarLid", [(0.048, 0.055), (0.03, 0.07), (0.0, 0.08)], (0.65, TY + 0.12, TOP), M_PORC_BLUE, steps=14))
for i, x in enumerate((-1.2, 0.1, 1.15)):
    service.append(box(f"Spoon{i}", (0.12, 0.012, 0.004), (x, TY + 0.47, TOP + 0.002), M_PORCELAIN, rot=(0, 0, random.uniform(-0.3, 0.3))))
DYNAMIC.append(group("prop.tea-service", service, (TX, TY, TABLE_H)))

# steam rising from the big blue teapot's spout and lid: a few soft puffs
steam = []
for i in range(5):
    t = i / 4
    steam.append(blob(f"Steam{i}", (SPOUT1.x + 0.02 * math.sin(i * 1.7), SPOUT1.y + 0.015 * math.cos(i * 1.3), SPOUT1.z + 0.03 + t * 0.22), 0.018 + 0.02 * t, M_STEAM, subdiv=1, amp=0.35, seed=i * 3.1, scale=(1, 1, 1.4)))
DYNAMIC.append(group("fx.steam", steam, (TX, TY, TABLE_H)))

# dappled sunlight through the leaves: thin warm pools lying just on the cloth (opaque, emissive)
dapple = []
for i in range(12):
    x = random.uniform(0.5, 2.1); y = TY + random.uniform(-0.5, 0.15)
    r = random.uniform(0.03, 0.065)
    dapple.append(blob(f"Dapple{i}", (x, y, TABLE_H + 0.006), r, M_DAPPLE, scale=(random.uniform(1.0, 1.7), 1.0, 0.04), subdiv=1, amp=0.35, freq=2.5, seed=i * 5.3, rot=(0, 0, random.uniform(0, math.pi))))
DYNAMIC.append(group("fx.dappled-light", dapple, (TX, TY, TABLE_H)))

# ----------------------------------------------------------------------------- the Hatter (seated, stylised; not rigged)
def seated_legs(f, name, mat_leg, mat_shoe, thigh_r=0.065, shin_r=0.05, long=1.0, foot=(0.8, 1.6, 0.6)):
    P = []
    P.append(sphere(f"{name}_Hips", 0.17, f.p(0, -0.02, 0.55), mat_leg, scale=(1.0, 0.85, 0.6), rot=f.r()))
    for s in (-1, 1):
        knee = f.p(s * 0.10, 0.36 * long, 0.55)
        P.append(limb(f"{name}_Thigh{s}", f.p(s * 0.09, -0.02, 0.55), knee, thigh_r, thigh_r * 0.85, mat_leg))
        P.append(sphere(f"{name}_Knee{s}", thigh_r * 0.85, knee, mat_leg, seg=10))
        ankle = f.p(s * 0.10, 0.40 * long, 0.09)
        P.append(limb(f"{name}_Shin{s}", knee, ankle, shin_r, shin_r * 0.8, mat_leg))
        P.append(sphere(f"{name}_Foot{s}", 0.06, f.p(s * 0.10, 0.40 * long + 0.06, 0.05), mat_shoe, seg=12, scale=foot, rot=f.r()))
    return P

def arm(f, name, s, shoulder, elbow, hand, mat_sleeve, mat_hand, r=0.05):
    P = [limb(f"{name}_Upper{s}", f.p(*shoulder), f.p(*elbow), r, r * 0.85, mat_sleeve),
         sphere(f"{name}_Elbow{s}", r * 0.86, f.p(*elbow), mat_sleeve, seg=10),
         limb(f"{name}_Fore{s}", f.p(*elbow), f.p(*hand), r * 0.85, r * 0.65, mat_sleeve),
         sphere(f"{name}_Hand{s}", 0.038, f.p(*hand), mat_hand, seg=10, scale=(1, 1.3, 0.8), rot=f.r())]
    return P

def hatter():
    f = Frame(HATTER_SEAT, 0.0)
    P = seated_legs(f, "Hatter", M_TROUSERS, M_SHOE)
    P.append(sphere("Hatter_Torso", 0.20, f.p(0, -0.02, 0.82), M_COAT, scale=(1.0, 0.72, 1.45), rot=f.r(rx=-0.12)))
    P.append(sphere("Hatter_Waistcoat", 0.13, f.p(0, 0.07, 0.83), M_WAISTCOAT, scale=(1.0, 0.55, 1.5), rot=f.r(rx=-0.12)))
    for s in (-1, 1):
        P.append(box(f"Hatter_Lapel{s}", (0.07, 0.02, 0.2), f.p(s * 0.08, 0.12, 0.93), M_COAT, bevel=0.01, rot=f.r(rx=-0.15, ry=s * 0.35)))
    P.append(sphere("Hatter_Collar", 0.075, f.p(0, 0.03, 1.07), M_SHIRT, scale=(1, 1, 0.8)))
    for s in (-1, 1):
        P.append(sphere(f"Hatter_Bow{s}", 0.035, f.p(s * 0.035, 0.1, 1.06), M_BOWTIE, seg=10, scale=(1.2, 0.5, 0.8)))
    P.append(sphere("Hatter_Head", 0.115, f.p(0, 0.04, 1.21), M_SKIN, scale=(0.9, 1.0, 1.12)))
    P.append(sphere("Hatter_Nose", 0.032, f.p(0, 0.155, 1.2), M_SKIN, seg=10, scale=(0.8, 1.5, 0.9)))
    P.append(sphere("Hatter_Chin", 0.05, f.p(0, 0.1, 1.11), M_SKIN, seg=10, scale=(1.0, 0.8, 0.75)))
    for s in (-1, 1):
        P.append(sphere(f"Hatter_Eye{s}", 0.022, f.p(s * 0.042, 0.128, 1.25), M_EYE, seg=10))
        P.append(sphere(f"Hatter_Pupil{s}", 0.011, f.p(s * 0.042, 0.148, 1.25), M_INK, seg=8))
        P.append(sphere(f"Hatter_Ear{s}", 0.03, f.p(s * 0.105, 0.03, 1.21), M_SKIN, seg=8, scale=(0.5, 0.9, 1.2)))
        P.append(sphere(f"Hatter_HairTuft{s}", 0.06, f.p(s * 0.1, -0.02, 1.25), M_HAIR_HATTER, seg=10, scale=(0.7, 1.1, 0.9)))
    P.append(box("Hatter_Mouth", (0.055, 0.012, 0.009), f.p(0, 0.152, 1.158), M_INK, rot=f.r(rx=0.4)))
    # the great top hat, tilted back, ticket in the band: "In this style 10/6"
    hat_tilt = f.r(rx=-0.12, ry=0.05)
    hat_base = Vector(f.p(0, 0.02, 1.29))
    P.append(lathe("Hatter_Hat", [(0.0, 0.0), (0.205, 0.0), (0.21, 0.014), (0.12, 0.018), (0.108, 0.13), (0.118, 0.26), (0.126, 0.30), (0.0, 0.305)], tuple(hat_base), M_HATFELT, steps=20, rot=hat_tilt))
    P.append(lathe("Hatter_HatBand", [(0.113, 0.022), (0.111, 0.08)], tuple(hat_base), M_HATBAND, steps=20, rot=hat_tilt))
    # ticket: a card tucked in the band at the front, the text facing the reader (+Y)
    tk = Euler(hat_tilt).to_matrix()
    tpos = hat_base + tk @ Vector((0.03, 0.118, 0.09))
    trot = (Euler(hat_tilt).to_matrix() @ Euler((-0.15, 0.0, 0.18)).to_matrix()).to_euler()
    P.append(box("Hatter_Ticket", (0.115, 0.004, 0.085), tuple(tpos), M_PAPER, rot=trot))
    tt = text_mesh("Hatter_TicketText", "In this style\n10/6", 0.024, (0, 0, 0), M_INK, extrude=0.0)
    tt.rotation_euler = (trot.to_matrix() @ Euler((math.pi / 2, 0, math.pi)).to_matrix()).to_euler()
    tt.location = tuple(tpos + trot.to_matrix() @ Vector((0, 0.0028, 0)))
    P.append(tt)
    # arms: right elbow on the Dormouse, left hand holding a teacup and a slice of bread-and-butter
    P += arm(f, "Hatter", 1, (0.19, 0.0, 1.0), (0.31, 0.44, 0.80), (0.27, 0.66, 0.84), M_COAT, M_SKIN)
    P += arm(f, "Hatter", -1, (-0.19, 0.0, 1.0), (-0.27, 0.36, 0.80), (-0.12, 0.56, 0.86), M_COAT, M_SKIN)
    hx_, hy_, hz_ = f.p(-0.12, 0.6, 0.86)
    P.append(lathe("Hatter_Cup", cup_profile, (hx_, hy_, hz_ - 0.005), M_PORCELAIN, steps=14))
    P.append(box("Hatter_Bread", (0.075, 0.07, 0.012), f.p(0.27, 0.68, 0.875), M_BREAD, bevel=0.003, rot=f.r(rz=0.5)))
    # coat tails behind on the seat
    P.append(sphere("Hatter_CoatTail", 0.16, f.p(0, -0.14, 0.62), M_COAT, scale=(1.1, 0.5, 1.0)))
    return P
DYNAMIC.append(group("char.hatter", hatter(), (HATTER_SEAT[0], HATTER_SEAT[1], 0.0)))

# ----------------------------------------------------------------------------- the March Hare (seated, straw in his hair)
def march_hare():
    f = Frame(HARE_SEAT, HARE_YAW)
    P = seated_legs(f, "Hare", M_HAREFUR, M_HAREFUR, thigh_r=0.075, shin_r=0.045, long=1.05, foot=(0.75, 2.2, 0.5))
    P.append(sphere("Hare_Torso", 0.19, f.p(0, -0.02, 0.80), M_HAREFUR, scale=(1.0, 0.8, 1.4), rot=f.r(rx=-0.18)))
    P.append(sphere("Hare_Chest", 0.12, f.p(0, 0.08, 0.86), M_MUZZLE, scale=(1.0, 0.55, 1.3), rot=f.r(rx=-0.18)))
    P.append(torus("Hare_Collar", 0.075, 0.018, f.p(0, 0.04, 1.03), M_SHIRT, rot=f.r(rx=-0.25), seg=16, rseg=6))
    for s in (-1, 1):
        P.append(sphere(f"Hare_Bow{s}", 0.03, f.p(s * 0.03, 0.12, 1.02), M_BOWTIE_BLUE, seg=10, scale=(1.2, 0.5, 0.8), rot=f.r()))
    # head: long, forward, with a pale muzzle
    head_c = (0, 0.07, 1.16)
    P.append(sphere("Hare_Head", 0.105, f.p(*head_c), M_HAREFUR, scale=(0.85, 1.3, 0.95), rot=f.r(rx=0.15)))
    P.append(sphere("Hare_Muzzle", 0.06, f.p(0, 0.18, 1.12), M_MUZZLE, seg=12, scale=(1.0, 0.9, 0.8), rot=f.r()))
    P.append(sphere("Hare_Nose", 0.016, f.p(0, 0.235, 1.14), M_EAR_PINK, seg=8, scale=(1.2, 0.8, 0.8)))
    for s in (-1, 1):
        P.append(sphere(f"Hare_Eye{s}", 0.026, f.p(s * 0.072, 0.12, 1.2), M_AMBER, seg=10))
        P.append(sphere(f"Hare_Pupil{s}", 0.013, f.p(s * 0.087, 0.13, 1.205), M_INK, seg=8))
        for k in range(2):
            P.append(limb(f"Hare_Whisker{s}{k}", f.p(s * 0.03, 0.22, 1.12 - k * 0.012), f.p(s * 0.14, 0.24, 1.13 - k * 0.04), 0.0015, 0.0008, M_INK, verts=4))
        # long ears, swept back and apart, pink inside
        er = f.r(rx=-0.35, ry=s * 0.32)
        ec = Vector(f.p(s * 0.06, -0.02, 1.38))
        P.append(sphere(f"Hare_Ear{s}", 0.05, tuple(ec), M_HAREFUR, seg=12, scale=(0.75, 0.4, 3.3), rot=er))
        P.append(sphere(f"Hare_EarInner{s}", 0.04, tuple(ec + Euler(er).to_matrix() @ Vector((0, 0.012, 0.0))), M_EAR_PINK, seg=10, scale=(0.6, 0.25, 3.0), rot=er))
    # straw sticking out of his hair between the ears (Tenniel)
    rnd = random.Random(7)
    for k in range(9):
        base = Vector(f.p(rnd.uniform(-0.04, 0.04), rnd.uniform(-0.02, 0.06), 1.245))
        d = Vector((rnd.uniform(-0.9, 0.9), rnd.uniform(-0.6, 0.6), rnd.uniform(0.5, 1.0))).normalized()
        d = Matrix.Rotation(HARE_YAW, 3, 'Z') @ d
        P.append(limb(f"Hare_Straw{k}", base, base + d * rnd.uniform(0.10, 0.20), 0.0032, 0.0018, M_STRAW, verts=5))
    # arms: left elbow on the Dormouse, right paw out over the table ("Have some wine")
    P += arm(f, "Hare", -1, (-0.17, 0.0, 0.98), (-0.20, 0.40, 0.82), (-0.06, 0.58, 0.85), M_HAREFUR, M_MUZZLE, r=0.045)
    P += arm(f, "Hare", 1, (0.17, 0.0, 0.98), (0.26, 0.30, 0.86), (0.22, 0.56, 0.90), M_HAREFUR, M_MUZZLE, r=0.045)
    P.append(sphere("Hare_Tail", 0.06, f.p(0, -0.2, 0.6), M_MUZZLE, seg=10))
    return P
DYNAMIC.append(group("char.march-hare", march_hare(), (HARE_SEAT[0], HARE_SEAT[1], 0.0)))

# ----------------------------------------------------------------------------- the Dormouse, curled up asleep on the table corner
def dormouse():
    x, y, z = DORMOUSE[0], DORMOUSE[1], TABLE_H + 0.008
    f = Frame((x, y), math.radians(70))
    P = []
    P.append(sphere("Dormouse_Body", 0.1, f.p(0, 0, z + 0.075), M_DORMFUR, scale=(1.3, 1.0, 0.78), rot=f.r()))
    P.append(sphere("Dormouse_Belly", 0.07, f.p(0, 0.05, z + 0.055), M_DORMBELLY, seg=12, scale=(1.3, 0.9, 0.7), rot=f.r()))
    hc = f.p(0.1, 0.07, z + 0.06)
    P.append(sphere("Dormouse_Head", 0.06, hc, M_DORMFUR, seg=14, scale=(1.0, 1.1, 0.9), rot=f.r(rz=0.5)))
    P.append(sphere("Dormouse_Snout", 0.025, f.p(0.135, 0.12, z + 0.045), M_DORMBELLY, seg=10, scale=(1, 1.3, 0.9), rot=f.r(rz=0.5)))
    P.append(sphere("Dormouse_Nose", 0.008, f.p(0.145, 0.15, z + 0.048), M_EAR_PINK, seg=6))
    for s, (ex, ey) in enumerate([(0.06, 0.06), (0.13, 0.03)]):
        P.append(sphere(f"Dormouse_Ear{s}", 0.022, f.p(ex, ey, z + 0.115), M_EAR_PINK, seg=10, scale=(1, 0.35, 1), rot=f.r(rz=0.5)))
    for s, (ex, ey) in enumerate([(0.105, 0.115), (0.145, 0.085)]):
        P.append(limb(f"Dormouse_ClosedEye{s}", f.p(ex - 0.008, ey, z + 0.078), f.p(ex + 0.008, ey + 0.004, z + 0.077), 0.0025, 0.0025, M_INK, verts=4))
    # the tail wraps round the body
    P.append(torus("Dormouse_Tail", 0.12, 0.016, f.p(-0.01, 0.0, z + 0.02), M_DORMFUR, rot=f.r(), seg=18, rseg=6))
    for s in (-1, 1):
        P.append(sphere(f"Dormouse_Paw{s}", 0.014, f.p(0.12 + s * 0.02, 0.11, z + 0.015), M_EAR_PINK, seg=6))
    return P
DYNAMIC.append(group("char.dormouse", dormouse(), (DORMOUSE[0], DORMOUSE[1], TABLE_H)))

# ----------------------------------------------------------------------------- the tree over the table
def tree():
    tx, ty = TREE
    trunk = lathe("Tree_Trunk", [(0.55, -0.05), (0.42, 0.25), (0.33, 0.8), (0.30, 1.8), (0.28, 2.5), (0.24, 3.0), (0.16, 3.5)], (tx, ty, 0), M_BARK, steps=16)
    parts = [trunk]
    # roots flaring into the lawn
    for i in range(5):
        a = i * 2 * math.pi / 5 + 0.3
        parts.append(limb(f"Tree_Root{i}", (tx + 0.25 * math.cos(a), ty + 0.25 * math.sin(a), 0.35), (tx + 0.85 * math.cos(a), ty + 0.85 * math.sin(a), -0.05), 0.13, 0.03, M_BARK, verts=8))
    # main limbs reaching out over the table (towards -X, +Y)
    limbs = [((tx - 0.05, ty, 2.4), (tx - 2.6, ty + 1.7, 3.6), 0.16, 0.07),
             ((tx, ty, 2.8), (tx - 1.2, ty + 2.6, 3.9), 0.14, 0.06),
             ((tx, ty, 3.1), (tx + 1.2, ty - 0.6, 4.4), 0.12, 0.05),
             ((tx, ty, 3.3), (tx - 0.5, ty - 1.4, 4.6), 0.11, 0.05),
             ((tx - 1.4, ty + 0.95, 3.05), (tx - 3.9, ty + 2.4, 3.55), 0.08, 0.035),
             ((tx - 0.6, ty + 1.3, 3.25), (tx - 0.8, ty + 3.6, 3.7), 0.07, 0.03)]
    SH = Vector((-0.3, 1.4, 0.0))                       # the canopy leans out over the table so its shade dapples the cloth
    for i, (a, b_, r1, r2) in enumerate(limbs):
        parts.append(limb(f"Tree_Limb{i}", a, Vector(b_) + SH * (0.5 if i in (2, 3) else 1.0), r1, r2, M_BARK, verts=8))
    canopy = []
    rnd = random.Random(11)
    centres = [(tx - 2.7, ty + 1.9, 3.8), (tx - 1.4, ty + 2.6, 4.1), (tx - 0.3, ty + 1.2, 4.6), (tx + 1.0, ty - 0.4, 4.7), (tx - 0.6, ty - 1.2, 5.0),
               (tx - 3.8, ty + 2.5, 3.7), (tx - 2.0, ty + 0.6, 4.7), (tx + 0.3, ty + 0.3, 5.3)]
    k = 0
    for (cx, cy, cz) in centres:
        for j in range(2):
            r = rnd.uniform(0.8, 1.15)
            canopy.append(blob(f"Leaves{k}", (cx + SH.x + rnd.uniform(-0.7, 0.7), cy + SH.y + rnd.uniform(-0.7, 0.7), cz + rnd.uniform(-0.3, 0.45)), r, M_LEAVES,
                               scale=(1.25, 1.25, 0.8), subdiv=3, amp=0.3, freq=1.9, seed=k * 1.37))
            k += 1
    return parts, canopy
tree_parts, canopy = tree()

# ----------------------------------------------------------------------------- the March Hare's house: ear chimneys, roof thatched with fur
def house():
    P = []
    fx, fy = HOUSE_X, HOUSE_Y            # front wall plane (faces +Y)
    cy = fy - HOUSE_D / 2
    P.append(box("House_Walls", (HOUSE_W, HOUSE_D, WALL_H), (fx, cy, WALL_H / 2), M_WHITEWASH, bevel=0.02))
    P.append(box("House_Plinth", (HOUSE_W + 0.08, HOUSE_D + 0.08, 0.35), (fx, cy, 0.175), M_STONE, bevel=0.02))
    # gable ends (triangular prisms) under the roof
    ridge_h = WALL_H + 1.9
    # ridge runs along X: the reader sees the eaves with the fur thatch rolling down towards them
    me = bpy.data.meshes.new("House_Gables"); bm = bmesh.new()
    for sx in (-1, 1):
        x = fx + sx * (HOUSE_W / 2 - 0.02)
        a = bm.verts.new((x, fy, WALL_H)); b_ = bm.verts.new((x, fy - HOUSE_D, WALL_H)); c = bm.verts.new((x, cy, ridge_h - 0.15))
        f_ = bm.faces.new((a, c, b_))
        if sx > 0: f_.normal_flip()
    bm.normal_update(); bm.to_mesh(me); bm.free()
    gab = bpy.data.objects.new("House_Gables", me); me.materials.append(M_WHITEWASH); link(gab); P.append(gab)
    # thatch: two thick lumpy slopes with a rounded overhang, ridge along X
    def slope(name, sgn):
        me = bpy.data.meshes.new(name); bm = bmesh.new()
        nx, ny = 16, 7
        over = 0.55
        x0, x1 = fx - HOUSE_W / 2 - 0.45, fx + HOUSE_W / 2 + 0.45
        rows = []
        for j in range(ny + 1):
            v = j / ny                        # 0 at ridge, 1 at eave
            yy = cy + sgn * (v * (HOUSE_D / 2 + over))
            zz = ridge_h - v * (ridge_h - WALL_H + 0.35)
            row = []
            for i in range(nx + 1):
                u = i / nx
                xx = x0 + u * (x1 - x0)
                lump = 0.09 * noise.noise(Vector((xx * 1.3, yy * 1.3, 0.5 + sgn))) + 0.035 * math.sin(v * math.pi * 7)
                end_round = 0.18 * (abs(u - 0.5) * 2) ** 6
                row.append(bm.verts.new((xx, yy, zz + lump - end_round)))
            rows.append(row)
        for a, b_ in zip(rows, rows[1:]):
            for i in range(nx):
                f_ = bm.faces.new((a[i], a[i + 1], b_[i + 1], b_[i]))
        bm.normal_update()
        for f_ in bm.faces:
            if f_.normal.z < 0: f_.normal_flip()
        bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); me.materials.append(M_THATCH); link(o)
        for p in me.polygons: p.use_smooth = True
        sol = o.modifiers.new("Solidify", 'SOLIDIFY'); sol.thickness = 0.28; sol.offset = -1
        return o
    P.append(slope("House_ThatchFront", 1)); P.append(slope("House_ThatchBack", -1))
    # fur ridge roll
    P.append(cyl("House_RidgeRoll", 0.2, HOUSE_W + 0.9, (fx, cy, ridge_h + 0.02), M_THATCH, verts=12, rot=(0, math.pi / 2, 0)))
    # chimneys shaped like (hare's) ears: tall, rounded, furred outside, pink inside, facing the garden
    for s in (-1, 1):
        ex = fx + s * 1.45
        er = (math.radians(-12), math.radians(s * 14), 0)
        P.append(sphere(f"House_EarChimney{s}", 0.40, (ex, cy + 0.2, ridge_h + 0.85), M_THATCH, seg=16, scale=(0.75, 0.42, 2.7), rot=er))
        P.append(sphere(f"House_EarInner{s}", 0.32, (ex + s * 0.02, cy + 0.33, ridge_h + 0.9), M_EAR_PINK, seg=14, scale=(0.62, 0.22, 2.4), rot=er))
        P.append(cyl(f"House_ChimneyPot{s}", 0.1, 0.22, (ex + s * math.sin(er[1]) * 1.05, cy + 0.2 - 0.22, ridge_h + 1.92), M_STONE, verts=10))
    # door, frame, step
    dx, dw, dh = fx, 1.0, 2.0
    P.append(box("House_Door", (dw, 0.06, dh), (dx, fy + 0.03, dh / 2 + 0.05), M_DOOR, bevel=0.01))
    for k, (px, pz) in enumerate([(-0.24, 0.55), (0.24, 0.55), (-0.24, 1.45), (0.24, 1.45)]):
        P.append(box(f"House_DoorPanel{k}", (0.36, 0.02, 0.62), (dx + px, fy + 0.065, pz), M_DOOR))
    for s in (-1, 1):
        P.append(box(f"House_DoorFrame{s}", (0.1, 0.12, dh + 0.1), (dx + s * (dw / 2 + 0.05), fy + 0.04, dh / 2 + 0.05), M_FRAMEPAINT, bevel=0.01))
    P.append(box("House_DoorHead", (dw + 0.3, 0.14, 0.12), (dx, fy + 0.05, dh + 0.12), M_FRAMEPAINT, bevel=0.01))
    P.append(box("House_Step", (1.4, 0.45, 0.16), (dx, fy + 0.22, 0.08), M_STONE, bevel=0.02))
    P.append(sphere("House_DoorKnob", 0.035, (dx + 0.36, fy + 0.1, 1.0), M_HATBAND, seg=10))
    # windows with white frames, dark glass, mullions and a flower box
    for s in (-1, 1):
        wx = fx + s * 1.85
        P.append(box(f"House_Win{s}_Glass", (1.0, 0.03, 0.9), (wx, fy + 0.01, 1.55), M_WINGLASS))
        P.append(box(f"House_Win{s}_FrameT", (1.16, 0.1, 0.08), (wx, fy + 0.04, 2.04), M_FRAMEPAINT))
        P.append(box(f"House_Win{s}_FrameB", (1.2, 0.16, 0.08), (wx, fy + 0.06, 1.06), M_FRAMEPAINT))
        for k in (-1, 1):
            P.append(box(f"House_Win{s}_FrameS{k}", (0.08, 0.1, 0.98), (wx + k * 0.54, fy + 0.04, 1.55), M_FRAMEPAINT))
        P.append(box(f"House_Win{s}_MullV", (0.04, 0.06, 0.9), (wx, fy + 0.03, 1.55), M_FRAMEPAINT))
        P.append(box(f"House_Win{s}_MullH", (1.0, 0.06, 0.04), (wx, fy + 0.03, 1.55), M_FRAMEPAINT))
        P.append(box(f"House_Win{s}_Box", (1.1, 0.22, 0.18), (wx, fy + 0.16, 0.96), M_DOOR, bevel=0.01))
        for k in range(6):
            P.append(blob(f"House_Win{s}_Flower{k}", (wx - 0.45 + k * 0.18, fy + 0.17, 1.1), 0.07, M_FLOWER_PINK if k % 2 else M_FLOWER_YEL, subdiv=1, amp=0.4, seed=k + s * 9))
    return P
house_parts = house()

# hedge behind and beside the house, flower clumps along the front, distant trees ring the garden
hedge = []
for i in range(14):
    x = HOUSE_X - 8.5 + i * 1.25
    if HOUSE_X - 3.6 < x < HOUSE_X + 3.6: continue
    hedge.append(blob(f"Hedge{i}", (x, HOUSE_Y - 0.6 + random.uniform(-0.2, 0.2), 0.55), 0.85, M_HEDGE, scale=(1.0, 0.7, 0.8), subdiv=2, amp=0.25, seed=i * 2.2))
for i in range(7):
    x = HOUSE_X - 2.6 + i * 0.85
    if abs(x - HOUSE_X) < 0.9: continue
    hedge.append(blob(f"FrontBed{i}", (x, HOUSE_Y + 0.55, 0.22), 0.32, M_HEDGE, scale=(1.2, 0.8, 0.7), subdiv=2, amp=0.3, seed=i * 4.1 + 1))
    for k in range(3):
        hedge.append(blob(f"FrontFlower{i}_{k}", (x + random.uniform(-0.25, 0.25), HOUSE_Y + 0.6 + random.uniform(-0.15, 0.15), 0.45), 0.06, M_FLOWER_PINK if (i + k) % 2 else M_FLOWER_YEL, subdiv=1, amp=0.4, seed=i * 7 + k))
def treeline(name, r0, r1, seg=96):
    """Continuous ring of distant woodland: a wavy, rounded foliage band (cheaper and softer than blobs)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rows = []
    prof = [(0.0, -0.3), (0.15, 0.55), (0.45, 0.92), (0.75, 1.0), (1.0, 0.75)]     # (depth fraction, height fraction)
    for i in range(seg):
        a = 2 * math.pi * i / seg
        d = Vector((math.cos(a), math.sin(a), 0))
        h = 4.2 + 2.6 * noise.noise(d * 2.2 + Vector((0.3, 0.1, 0))) + 1.4 * abs(noise.noise(d * 7.0))
        rr = r0 + 2.0 * noise.noise(d * 3.1 + Vector((5, 1, 0)))
        rows.append([bm.verts.new(d * (rr + f * (r1 - r0)) + Vector((0, 0, hf * h + (0.6 if f > 0 else 0)))) for f, hf in prof])
    for i in range(seg):
        a, b_ = rows[i], rows[(i + 1) % seg]
        for k in range(len(prof) - 1):
            bm.faces.new((a[k], a[k + 1], b_[k + 1], b_[k]))
    bm.normal_update()
    for f_ in bm.faces:
        c = f_.calc_center_median(); c.z = 0
        if f_.normal.dot(c) > 0: f_.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_FARTREES)
    for p in me.polygons: p.use_smooth = True
    return link(o)
far = [treeline("Treeline", 21.0, 26.0)]
rnd = random.Random(3)
for i, (x, y) in enumerate([(-11, -13), (-15, -6), (9, -14), (14, -9), (-13, 7), (12, 8)]):
    h = rnd.uniform(4.5, 6.5)
    far.append(blob(f"FarTree{i}", (x, y, h * 0.7), h * 0.42, M_FARTREES, scale=(1.0, 1.0, 1.1), subdiv=3, amp=0.25, seed=i * 1.9))
    far.append(cyl(f"FarTrunk{i}", 0.22, h * 0.5, (x, y, h * 0.2), M_BARK, verts=6, bevel=False))

# ----------------------------------------------------------------------------- anchors (names are the manifest's anchor ids)
anchor("reader.path", (0.0, 0.0, 0.0))                          # the reader stands here facing -Y (Unity +Z)
anchor("reader.armchair", (ARMCHAIR[0], ARMCHAIR[1], 0.0))
anchor("table.corner", (1.95, TY - 0.32, TABLE_H))
anchor("table.centre", (TX, TY, TABLE_H))
anchor("table.end", (ARMCHAIR[0], ARMCHAIR[1], 0.0))
anchor("seat.hatter", (HATTER_SEAT[0], HATTER_SEAT[1], 0.0))
anchor("seat.march-hare", (HARE_SEAT[0], HARE_SEAT[1], 0.0))
anchor("seat.dormouse", (DORMOUSE[0], DORMOUSE[1], TABLE_H))
anchor("tree.canopy", (1.6, -3.4, 3.6))
anchor("house.front", (HOUSE_X, HOUSE_Y + 0.6, 0.0))
anchor("scene.centre", (TX, TY - 1.2, 0.0))                     # visual centre of the playable area (miniature pivot)

# ----------------------------------------------------------------------------- lights: afternoon sun, sky, warm bounce (manifest light ids)
def light_obj(name, kind, energy, color, loc, direction=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if direction is not None:
        lo.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return link(lo)
sun = light_obj("light.sun", 'SUN', 4.2, (1.0, 0.93, 0.80), (6, 6, 12), direction=-SUN_DIR, angle=math.radians(1.2))
sky_l = light_obj("light.sky", 'SUN', 0.35, (0.62, 0.75, 1.0), (0, 0, 14), direction=(0.1, -0.15, -1.0), angle=math.radians(60))
fill = light_obj("light.fill", 'POINT', 60.0, (1.0, 0.86, 0.65), (0.6, -1.4, 2.4), shadow_soft_size=1.5)
sky_l.data.use_shadow = False

# world: physical sky for render (the GLB carries the SkyDome mesh for Unity instead)
world = bpy.data.worlds.new("Garden"); scene.world = world; world.use_nodes = True
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

# ----------------------------------------------------------------------------- cameras for preview stills (reader eye height 1.62 m)
def camera(name, loc, look_at, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 120
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    d = Vector(look_at) - Vector(loc)
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return co
cams = [
    camera("Cam_Reader", (0.0, 0.05, 1.62), (0.2, -3.4, 1.15), lens=18),
    camera("Cam_Corner", (0.75, -1.35, 1.3), (2.0, -3.25, 1.0), lens=30),
    camera("Cam_Hatter", (1.45, -2.2, 1.22), (1.6, -3.5, 1.3), lens=40),
    camera("Cam_Armchair", (-2.55, -2.6, 1.15), (2.0, -3.1, 1.0), lens=22),
    camera("Cam_Wide", (6.5, 3.0, 2.4), (-1.5, -5.5, 1.6), lens=20),
]

# save the art-direction .blend before any baking destroys procedural materials
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "mad_tea_party_source.blend"))

# ----------------------------------------------------------------------------- render
if args.render:
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    want = set(c.strip() for c in args.cams.split(",") if c.strip())
    for c in cams:
        if want and c.name[4:].lower() not in want: continue
        scene.camera = c
        scene.render.filepath = os.path.join(OUT, f"render_{c.name[4:].lower()}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)

# ----------------------------------------------------------------------------- bake + merge + export for Unity
def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

def bake_and_export():
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')                       # apply modifiers everywhere
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    # 1. every script-controlled group becomes ONE mesh (multi-material, baked to one atlas)
    group_meshes = []
    for e in DYNAMIC:
        kids = [o for o in COLL.objects if o.type == 'MESH' and o.parent == e]
        # each group gets private copies of its materials so baking never touches the shared static ones
        for o in kids:
            for i, m in enumerate(o.data.materials):
                o.data.materials[i] = m.copy()
        for o in kids: o.select_set(True)
        bpy.context.view_layer.objects.active = kids[0]
        if len(kids) > 1: bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active; j.name = e.name.replace(".", "_").replace("-", "_") + "_mesh"
        group_meshes.append(j); bpy.ops.object.select_all(action='DESELECT')
    # 2. static meshes merged by material
    groups = {}
    for o in COLL.objects:
        if o.type != 'MESH' or o.parent is not None or not o.data.materials: continue
        groups.setdefault(o.data.materials[0].name, []).append(o)
    merged = []
    for mname, objs in groups.items():
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active; o.name = "MESH_" + mname[2:]
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    scene.cycles.samples = 8
    scene.render.bake.margin = 6
    scene.render.bake.use_selected_to_active = False
    T = args.tex
    size_for = {"M_Grass": T * 2, "M_Gravel": T, "M_FurThatch": T, "M_Whitewash": T, "M_Leaves": T, "M_Bark": T // 2,
                "M_SkyDome": T // 2, "M_Hedge": T // 2, "M_FarTrees": T // 4, "M_Stone": T // 2}
    group_size = {"prop.tea-table": T // 2, "prop.tea-service": T // 2, "prop.armchair": T // 2, "char.hatter": T // 2,
                  "char.march-hare": T // 2, "char.dormouse": T // 4, "fx.steam": 64, "fx.dappled-light": 64}

    def bake_object(o, label, size):
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
        bpy.ops.object.mode_set(mode='OBJECT')
        mats = list(o.data.materials)
        imgs = {}
        params = []
        for m in mats:
            bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            params.append((bsdf.inputs["Metallic"].default_value, bsdf.inputs["Emission Strength"].default_value, tuple(bsdf.inputs["Emission Color"].default_value), bsdf.inputs["Emission Color"].is_linked))
        for pass_name, btype, extra, noncolor in [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]:
            img = bpy.data.images.new(f"T_{label}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            for m in mats:
                nt = m.node_tree
                tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.name = "BAKE_" + pass_name
                for n in nt.nodes: n.select = False
                tex.select = True; nt.nodes.active = tex
            bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            img.filepath_raw = os.path.join(OUT, "textures", img.name + ".png"); os.makedirs(os.path.dirname(img.filepath_raw), exist_ok=True)
            img.file_format = 'PNG'; img.save(); img.pack()
            imgs[pass_name] = img
            print("baked", img.name, size)
        # one simple material from the baked maps; keep scalar params of the dominant material
        metallic = max(p[0] for p in params)
        emis = max(p[1] for p in params)
        ecol = params[0][2]; elinked = params[0][3]
        nm_ = "M_" + label
        bm_ = bpy.data.materials.new(nm_); bm_.use_nodes = True; nt = bm_.node_tree
        for n in list(nt.nodes): nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
        tb = nt.nodes.new("ShaderNodeTexImage"); tb.image = imgs["BaseColor"]
        tr = nt.nodes.new("ShaderNodeTexImage"); tr.image = imgs["Roughness"]
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = imgs["Normal"]
        nt.links.new(tb.outputs["Color"], nb.inputs["Base Color"])
        nt.links.new(tr.outputs["Color"], nb.inputs["Roughness"])
        nmap = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tn.outputs["Color"], nmap.inputs["Color"]); nt.links.new(nmap.outputs["Normal"], nb.inputs["Normal"])
        nb.inputs["Metallic"].default_value = metallic
        if emis > 0:
            nb.inputs["Emission Strength"].default_value = emis
            if elinked: nt.links.new(tb.outputs["Color"], nb.inputs["Emission Color"])
            else: nb.inputs["Emission Color"].default_value = ecol
        o.data.materials.clear(); o.data.materials.append(bm_)
        for p in o.data.polygons: p.material_index = 0
        for m in mats:
            if m.users == 0: bpy.data.materials.remove(m)

    for o in merged:
        base = o.data.materials[0].name
        size = size_for.get(base, T // 4)
        bake_object(o, base[2:], max(64, size))
    for e, o in zip(DYNAMIC, group_meshes):
        lbl = e.name.replace(".", "_").replace("-", "_")
        bake_object(o, lbl, max(64, group_size.get(e.name, T // 4)))
    for c in cams: bpy.data.objects.remove(c)
    glb = os.path.join(OUT, "mad_tea_party.glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False)  # JPEG: keeps the GLB under GitHub's 100 MB file limit; Unity recompresses to ASTC anyway
    allm = merged + group_meshes
    tris = sum(tri_count(o) for o in allm)
    verts = sum(len(o.data.vertices) for o in allm)
    print(f"EXPORT {glb} meshes={len(allm)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(allm)}\nverts={verts}\ntris={tris}\n")
        for o in sorted(allm, key=lambda o: -tri_count(o)):
            f.write(f"{o.name} parent={o.parent.name if o.parent else '-'} verts={len(o.data.vertices)} tris={tri_count(o)} tex={o.data.materials[0].node_tree.nodes[2].image.size[0] if o.data.materials else 0}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "mad_tea_party_baked.blend"))

# pre-export stats (also printed in quick runs so the budget is visible while iterating)
_m = [o for o in COLL.objects if o.type == 'MESH']
_dg = bpy.context.evaluated_depsgraph_get()
_cat = {}
for _o in _m:
    _e = _o.evaluated_get(_dg); _me = _e.to_mesh(); _t = sum(len(p.vertices) - 2 for p in _me.polygons); _e.to_mesh_clear()
    _k = _o.parent.name if _o.parent else _o.data.materials[0].name if _o.data.materials else "?"
    _cat[_k] = _cat.get(_k, 0) + _t
print(f"PRE-MERGE objects={len(_m)} tris={sum(_cat.values())}")
for _k, _v in sorted(_cat.items(), key=lambda kv: -kv[1]): print(f"  BUDGET {_k:28s} {_v}")

if args.bake or args.export:
    bake_and_export()
print("DONE")
