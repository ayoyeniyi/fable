"""
Fable: the Kansas farmhouse (The Wonderful Wizard of Oz, chapter I, "The Cyclone").

"Their house was small, for the lumber to build it had to be carried by wagon many miles. There were four walls,
a floor and a roof, which made one room; and this room contained a rusty looking cookstove, a cupboard for the
dishes, a table, three or four chairs, and the beds. Uncle Henry and Aunt Em had a big bed in one corner, and
Dorothy a little bed in another corner. There was no garret at all, and no cellar -- except a small hole dug in the
ground, called a cyclone cellar ... It was reached by a trap door in the middle of the floor ..."
"... she could see nothing but the great gray prairie on every side. Not a tree nor a house broke the broad sweep
of flat country that reached to the edge of the sky in all directions."

One board room under an open roof (no garret), the door standing open to the south on the gray prairie and a
heavy, darkening storm sky. No characters (Dorothy, Toto, Aunt Em and Uncle Henry are left out).

Builds the room procedurally (no downloaded models, textures or HDRIs) with PBR node materials, a storm-dimmed sun,
a cool sky fill and the oil lamp on the table, then (by flag) renders Cycles stills, bakes materials to textures,
merges static meshes by material and exports a .gltf + textures/ for Unity.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet (floor, z=0), north of the trap door
  anchor.reader.look      eye height, in the open doorway (the reader faces it, looking out on the prairie)
  anchor.scene.centre     the room's floor centre (the trap door)
  anchor.cellar.trapdoor  the trap door (floor), anchor.room.stove / room.table / room.bed.big / room.bed.little
  light.sun (SUN, dim, storm-filtered), light.sky (SUN, cool fill), light.lamp (POINT, the table oil lamp)
  SkyDome (unlit backdrop, baked base texture), far.prairie (ground beyond ~9 m, backdrop)

Axes: metres, Blender +Z up. The room spans x -2.5..2.5, y -2..2; the door is in the south wall (-y).

Run headless:
  blender -b -P blender/build_kansas_farmhouse.py -- --out out/kansas-farmhouse --render --quick --res 1200
  blender -b -P blender/build_kansas_farmhouse.py -- --out out/kansas-farmhouse --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/kansas-farmhouse")
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
ROOM_W, ROOM_D = 5.0, 4.0            # x across, y deep; the door is in the south (-y) wall
HX, HY = ROOM_W / 2, ROOM_D / 2
EAVE, RIDGE = 2.5, 3.45              # wall top and roof ridge (no garret: the room is open to the rafters)
T = 0.08                             # board wall thickness
GZ = -0.20                           # prairie ground level (the floor sits on a sill a little above it)
SLOPE = (RIDGE - EAVE) / (HY + T)
PITCH = math.atan(SLOPE)
DOOR_X, DOOR_W, DOOR_H = 0.5, 0.9, 2.0
WIN_Z0, WIN_Z1, WIN_W = 0.9, 1.85, 0.7
WIN_W_Y, WIN_E_Y, WIN_N_X = -0.2, 0.4, 0.35          # west, east and north windows (centres)
TRAP = 0.8                                           # trap door, square, in the middle of the floor
STOVE = (-2.12, -1.3)                                # cookstove (centre), against the west wall, front facing +x
TABLE = (1.15, 0.6)
TABLE_H = 0.74
READER = (0.0, 1.1)
SKY_R = 58.0
NEAR_R = 9.0
SUN_DIR = Vector((-0.80, -0.42, 0.30)).normalized()  # towards the (hidden) sun: low in the west-south-west

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
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'; prefs.get_devices()
    for d in prefs.devices: d.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print("Metal not available, CPU render:", e)
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 1.75

COLL = bpy.data.collections.new("KansasFarmhouse")
scene.collection.children.link(COLL)
def link(obj):
    COLL.objects.link(obj); return obj

# ----------------------------------------------------------------------------- material helpers (from build_lobby.py)
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

def texcoord_obj(nt, loc=(-1400, 0)):
    tc = node(nt, "ShaderNodeTexCoord", loc); mp = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    return mp

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

def bump_from(nt, b, height_socket, strength, distance):
    bump = node(nt, "ShaderNodeBump", (50, -300)); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return bump

def c4(c): return (c[0], c[1], c[2], 1)

def wood(name, base=(0.32, 0.17, 0.08), dark=(0.09, 0.045, 0.02), light=(0.55, 0.33, 0.15), scale=1.0, rough=(0.45, 0.75), grain_dir=(1, 1, 14), bands='Z', coat=0.0):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    mp.inputs["Scale"].default_value = tuple(g * scale for g in grain_dir)
    wave = node(nt, "ShaderNodeTexWave", (-1000, 200), wave_type='BANDS', bands_direction=bands)
    wave.inputs["Scale"].default_value = 1.2; wave.inputs["Distortion"].default_value = 9.0
    wave.inputs["Detail"].default_value = 6.0; wave.inputs["Detail Scale"].default_value = 1.5
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    fine = node(nt, "ShaderNodeTexNoise", (-1000, -150))
    fine.inputs["Scale"].default_value = 60.0 * scale; fine.inputs["Detail"].default_value = 8.0; fine.inputs["Roughness"].default_value = 0.7
    nt.links.new(mp.outputs["Vector"], fine.inputs["Vector"])
    mix = node(nt, "ShaderNodeMix", (-700, 100), data_type='FLOAT'); mix.inputs["Factor"].default_value = 0.22
    nt.links.new(wave.outputs["Fac"], mix.inputs[2]); nt.links.new(fine.outputs["Fac"], mix.inputs[3])
    mid = tuple((x + y) / 2 for x, y in zip(base, light)); lite = tuple((x + y) / 2 for x, y in zip(mid, light))
    r = ramp(nt, [(0.0, c4(dark)), (0.2, c4(base)), (0.5, c4(mid)), (0.72, c4(lite)), (0.9, c4(base))], (-450, 100))
    nt.links.new(mix.outputs[0], r.inputs["Fac"])
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-700, -550)); ao.inputs["Distance"].default_value = 0.12
    dust = mix_rgb(nt, 'MULTIPLY', 0.3, r.outputs["Color"], ao.outputs["Color"], (50, 100))
    nt.links.new(dust, b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", (-150, -200))
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough[1], rough[0]
    nt.links.new(wave.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    bump_from(nt, b, mix.outputs[0], 0.35, 0.003)
    b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.3
    return m

def boards(name, light, dark, axis='Z', width=0.15, grain=(1.2, 1.2, 28), paint=None, paint_amt=0.0, dirt=0.0, rough=0.85, seam=0.85):
    """Sawn boards: index along `axis` (each board its own tone), dark seams, grain, optional paint traces in the
    hollows of the grain (the paint the sun blistered and the rain washed away) and dirt rising from the floor."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1800, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1600, 0))
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    idx = math_(nt, 'DIVIDE', sep.outputs[axis.upper()], width, (-1400, 200))
    fl = math_(nt, 'FLOOR', idx, None, (-1200, 200)); fr = math_(nt, 'FRACT', idx, None, (-1200, 350))
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1000, 200), noise_dimensions='1D'); nt.links.new(fl, wn.inputs["W"])
    seamr = ramp(nt, [(0.0, (0, 0, 0, 1)), (0.035, (1, 1, 1, 1)), (0.965, (1, 1, 1, 1)), (1.0, (0, 0, 0, 1))], (-1000, 400))
    nt.links.new(fr, seamr.inputs["Fac"])
    mid = tuple((x + y) / 2 for x, y in zip(light, dark))
    tone = ramp(nt, [(0.0, c4(dark)), (0.55, c4(mid)), (1.0, c4(light))], (-800, 200))
    nt.links.new(wn.outputs["Value"], tone.inputs["Fac"])
    mp = texcoord_obj(nt, (-1800, -400)); mp.inputs["Scale"].default_value = grain
    gn = node(nt, "ShaderNodeTexNoise", (-1300, -400)); gn.inputs["Scale"].default_value = 1.0; gn.inputs["Detail"].default_value = 10; gn.inputs["Roughness"].default_value = 0.65; gn.inputs["Distortion"].default_value = 0.6
    nt.links.new(mp.outputs["Vector"], gn.inputs["Vector"])
    gr = ramp(nt, [(0.3, (0.55, 0.55, 0.55, 1)), (0.5, (1, 1, 1, 1)), (0.7, (0.8, 0.8, 0.8, 1))], (-1000, -400))
    nt.links.new(gn.outputs["Fac"], gr.inputs["Fac"])
    col = mix_rgb(nt, 'MULTIPLY', 0.6, tone.outputs["Color"], gr.outputs["Color"], (-600, 100))
    if paint is not None:
        pm = texcoord_obj(nt, (-1800, -800)); pm.inputs["Scale"].default_value = (5, 5, 14)
        pn = node(nt, "ShaderNodeTexNoise", (-1300, -800)); pn.inputs["Scale"].default_value = 2.2; pn.inputs["Detail"].default_value = 12; pn.inputs["Roughness"].default_value = 0.7
        nt.links.new(pm.outputs["Vector"], pn.inputs["Vector"])
        pr = ramp(nt, [(0.56, (0, 0, 0, 1)), (0.66, (1, 1, 1, 1))], (-1000, -800))
        nt.links.new(pn.outputs["Fac"], pr.inputs["Fac"])
        pmask = mix_rgb(nt, 'MULTIPLY', 1.0, pr.outputs["Color"], (paint_amt, paint_amt, paint_amt, 1), (-800, -800))
        col = mix_rgb(nt, 'MIX', pmask, col, c4(paint), (-400, 0))
    if dirt > 0:
        zr = node(nt, "ShaderNodeMapRange", (-1000, 650)); zr.inputs["From Min"].default_value = 0.0; zr.inputs["From Max"].default_value = 0.7
        zr.inputs["To Min"].default_value = 1.0 - dirt; zr.inputs["To Max"].default_value = 1.0
        nt.links.new(sep.outputs["Z"], zr.inputs["Value"])
        col = mix_rgb(nt, 'MULTIPLY', 1.0, col, zr.outputs["Result"], (-250, 0))
    col = mix_rgb(nt, 'MULTIPLY', seam, col, seamr.outputs["Color"], (-100, 0))
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-400, -550)); ao.inputs["Distance"].default_value = 0.15
    col = mix_rgb(nt, 'MULTIPLY', 0.35, col, ao.outputs["Color"], (100, 0))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    h = mix_rgb(nt, 'MULTIPLY', 1.0, seamr.outputs["Color"], gr.outputs["Color"], (-200, -300))
    bump_from(nt, b, h, 0.45, 0.003)
    return m

def noisy(name, colors, scale=8.0, rough=0.8, bump=0.2, bump_dist=0.003, detail=6.0, stretch=(1, 1, 1), sheen=0.0, metallic=0.0, warp=0.0, coat=0.0):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt); mp.inputs["Scale"].default_value = stretch
    n = node(nt, "ShaderNodeTexNoise", (-1000, 0)); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = 0.6
    n.inputs["Distortion"].default_value = warp
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    stops = [(i / max(1, len(colors) - 1) * 0.6 + 0.2, c4(c)) for i, c in enumerate(colors)]
    r = ramp(nt, stops, (-700, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if sheen: b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.4
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.1
    if bump:
        fine = node(nt, "ShaderNodeTexNoise", (-1000, -350)); fine.inputs["Scale"].default_value = scale * 6; fine.inputs["Detail"].default_value = 4
        nt.links.new(mp.outputs["Vector"], fine.inputs["Vector"])
        bump_from(nt, b, fine.outputs["Fac"], bump, bump_dist)
    return m

def plain(name, color, rough=0.5, metallic=0.0, emission=None, strength=0.0, coat=0.0, transmission=0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = c4(color); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if emission: b.inputs["Emission Color"].default_value = c4(emission); b.inputs["Emission Strength"].default_value = strength
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.05
    if transmission: b.inputs["Transmission Weight"].default_value = transmission
    return m

def rust(name="M_RustIron"):
    """Cast iron gone rusty: near-black iron with orange-brown rust blooming through, pitted."""
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt); mp.inputs["Scale"].default_value = (1, 1, 1)
    n = node(nt, "ShaderNodeTexNoise", (-1000, 0)); n.inputs["Scale"].default_value = 5.0; n.inputs["Detail"].default_value = 12; n.inputs["Roughness"].default_value = 0.68; n.inputs["Distortion"].default_value = 0.8
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    r = ramp(nt, [(0.30, (0.022, 0.021, 0.020, 1)), (0.50, (0.045, 0.040, 0.036, 1)), (0.56, (0.16, 0.07, 0.03, 1)), (0.66, (0.40, 0.18, 0.06, 1)), (0.80, (0.30, 0.13, 0.05, 1))], (-700, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", (-400, -200)); rr.inputs["From Min"].default_value = 0.5; rr.inputs["From Max"].default_value = 0.62
    rr.inputs["To Min"].default_value = 0.38; rr.inputs["To Max"].default_value = 0.9
    nt.links.new(n.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = 0.45
    fine = node(nt, "ShaderNodeTexNoise", (-1000, -350)); fine.inputs["Scale"].default_value = 90; fine.inputs["Detail"].default_value = 6
    nt.links.new(mp.outputs["Vector"], fine.inputs["Vector"])
    bump_from(nt, b, fine.outputs["Fac"], 0.5, 0.002)
    return m

def quilt(name="M_Quilt", cell=0.21):
    """A faded patchwork quilt: square patches, each a washed-out calico tone, with seams."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0))
    sc = node(nt, "ShaderNodeVectorMath", (-1400, 0), operation='DIVIDE'); sc.inputs[1].default_value = (cell, cell, cell)
    nt.links.new(tc.outputs["Object"], sc.inputs[0])
    fl = node(nt, "ShaderNodeVectorMath", (-1200, 0), operation='FLOOR'); nt.links.new(sc.outputs[0], fl.inputs[0])
    fr = node(nt, "ShaderNodeVectorMath", (-1200, 250), operation='FRACTION'); nt.links.new(sc.outputs[0], fr.inputs[0])
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1000, 0), noise_dimensions='3D'); nt.links.new(fl.outputs[0], wn.inputs["Vector"])
    pal = ramp(nt, [(0.0, (0.27, 0.14, 0.11, 1)), (0.2, (0.19, 0.21, 0.25, 1)), (0.4, (0.46, 0.43, 0.36, 1)), (0.6, (0.26, 0.22, 0.16, 1)), (0.8, (0.30, 0.31, 0.26, 1))], (-800, 0), interp='CONSTANT')
    nt.links.new(wn.outputs["Value"], pal.inputs["Fac"])
    # seams: distance of the fractional coord from the patch edge, on x and y
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1000, 300)); nt.links.new(fr.outputs[0], sep.inputs["Vector"])
    def edge(sock, loc):
        a = math_(nt, 'SUBTRACT', sock, 0.5, loc); a = math_(nt, 'ABSOLUTE', a, None, (loc[0] + 120, loc[1]))
        return a
    ex = edge(sep.outputs["X"], (-850, 350)); ey = edge(sep.outputs["Y"], (-850, 250)); ez = edge(sep.outputs["Z"], (-850, 150))
    mx = math_(nt, 'MAXIMUM', math_(nt, 'MAXIMUM', ex, ey, (-600, 300)), ez, (-500, 300))
    sr = ramp(nt, [(0.0, (1, 1, 1, 1)), (0.46, (1, 1, 1, 1)), (0.5, (0.55, 0.55, 0.55, 1))], (-400, 300))
    nt.links.new(mx, sr.inputs["Fac"])
    n = node(nt, "ShaderNodeTexNoise", (-800, -300)); n.inputs["Scale"].default_value = 60; n.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    col = mix_rgb(nt, 'MULTIPLY', 1.0, pal.outputs["Color"], sr.outputs["Color"], (-200, 0))
    col = mix_rgb(nt, 'MULTIPLY', 0.25, col, n.outputs["Color"], (0, 0))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95; b.inputs["Sheen Weight"].default_value = 0.4
    bump_from(nt, b, sr.outputs["Color"], 0.4, 0.004)
    return m

def ragrug(name="M_RagRug"):
    """A braided rag rug: concentric rings of faded rag colours."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1400, 0))
    mp = node(nt, "ShaderNodeMapping", (-1200, 0)); mp.inputs["Location"].default_value = (-0.5, -0.5, 0); mp.inputs["Scale"].default_value = (1, 1, 0)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    vl = node(nt, "ShaderNodeVectorMath", (-1000, 0), operation='LENGTH'); nt.links.new(mp.outputs["Vector"], vl.inputs[0])
    d = math_(nt, 'MULTIPLY', vl.outputs["Value"], 14.0, (-850, 0))
    fr = math_(nt, 'FRACT', d, None, (-700, 100)); fl = math_(nt, 'FLOOR', d, None, (-700, -50))
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-550, -50), noise_dimensions='1D'); nt.links.new(fl, wn.inputs["W"])
    pal = ramp(nt, [(0.0, (0.28, 0.12, 0.09, 1)), (0.25, (0.20, 0.20, 0.22, 1)), (0.5, (0.42, 0.37, 0.28, 1)), (0.75, (0.16, 0.18, 0.24, 1))], (-400, -50), interp='CONSTANT')
    nt.links.new(wn.outputs["Value"], pal.inputs["Fac"])
    braid = node(nt, "ShaderNodeTexWave", (-700, -300), wave_type='RINGS', rings_direction='SPHERICAL'); braid.inputs["Scale"].default_value = 40
    nt.links.new(mp.outputs["Vector"], braid.inputs["Vector"])
    rr = ramp(nt, [(0.0, (0.6, 0.6, 0.6, 1)), (0.5, (1, 1, 1, 1)), (1.0, (0.6, 0.6, 0.6, 1))], (-450, 150))
    nt.links.new(fr, rr.inputs["Fac"])
    col = mix_rgb(nt, 'MULTIPLY', 1.0, pal.outputs["Color"], rr.outputs["Color"], (-150, 0))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    bump_from(nt, b, rr.outputs["Color"], 0.6, 0.004)
    return m

def trapdoor_mat(name="M_TrapDoor"):
    """The trap door: boards across the floor boards, a worn dark gap all round its edge."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1800, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1600, 0))
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    idx = math_(nt, 'DIVIDE', sep.outputs["Y"], TRAP / 5, (-1400, 200))
    fl = math_(nt, 'FLOOR', idx, None, (-1200, 200)); fr = math_(nt, 'FRACT', idx, None, (-1200, 350))
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1000, 200), noise_dimensions='1D'); nt.links.new(fl, wn.inputs["W"])
    tone = ramp(nt, [(0.0, (0.30, 0.25, 0.18, 1)), (1.0, (0.40, 0.34, 0.25, 1))], (-800, 200))
    nt.links.new(wn.outputs["Value"], tone.inputs["Fac"])
    seamr = ramp(nt, [(0.0, (0.1, 0.1, 0.1, 1)), (0.04, (1, 1, 1, 1)), (0.96, (1, 1, 1, 1)), (1.0, (0.1, 0.1, 0.1, 1))], (-1000, 400))
    nt.links.new(fr, seamr.inputs["Fac"])
    mp = texcoord_obj(nt, (-1800, -400)); mp.inputs["Scale"].default_value = (1.2, 26, 1.2)
    gn = node(nt, "ShaderNodeTexNoise", (-1300, -400)); gn.inputs["Detail"].default_value = 10; gn.inputs["Distortion"].default_value = 0.6
    nt.links.new(mp.outputs["Vector"], gn.inputs["Vector"])
    gr = ramp(nt, [(0.3, (0.6, 0.6, 0.6, 1)), (0.6, (1, 1, 1, 1))], (-1000, -400)); nt.links.new(gn.outputs["Fac"], gr.inputs["Fac"])
    # the edge: generated coords run 0..1 across the box
    g = node(nt, "ShaderNodeSeparateXYZ", (-1400, 700)); nt.links.new(tc.outputs["Generated"], g.inputs["Vector"])
    ex = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', g.outputs["X"], 0.5, (-1200, 750)), None, (-1050, 750))
    ey = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', g.outputs["Y"], 0.5, (-1200, 650)), None, (-1050, 650))
    er = ramp(nt, [(0.0, (1, 1, 1, 1)), (0.455, (1, 1, 1, 1)), (0.475, (0.55, 0.55, 0.55, 1)), (0.485, (0.02, 0.02, 0.02, 1))], (-800, 700))
    nt.links.new(math_(nt, 'MAXIMUM', ex, ey, (-900, 700)), er.inputs["Fac"])
    col = mix_rgb(nt, 'MULTIPLY', 0.6, tone.outputs["Color"], gr.outputs["Color"], (-500, 100))
    col = mix_rgb(nt, 'MULTIPLY', 0.9, col, seamr.outputs["Color"], (-300, 100))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, er.outputs["Color"], (-100, 100))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.8
    h = mix_rgb(nt, 'MULTIPLY', 1.0, seamr.outputs["Color"], er.outputs["Color"], (-200, -300))
    bump_from(nt, b, h, 0.6, 0.004)
    return m

def ground_mat(name="M_PrairieGround"):
    """The plowed land the sun baked into a gray mass with little cracks, and the gray grass among it."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1800, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1600, 300))
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    v1 = node(nt, "ShaderNodeTexVoronoi", (-1300, 300), feature='DISTANCE_TO_EDGE'); v1.inputs["Scale"].default_value = 6.5
    v2 = node(nt, "ShaderNodeTexVoronoi", (-1300, 0), feature='DISTANCE_TO_EDGE'); v2.inputs["Scale"].default_value = 22.0
    wobble = node(nt, "ShaderNodeTexNoise", (-1600, -200)); wobble.inputs["Scale"].default_value = 2.0; wobble.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], wobble.inputs["Vector"])
    wv = node(nt, "ShaderNodeMix", (-1450, -100), data_type='VECTOR'); wv.inputs["Factor"].default_value = 0.08
    nt.links.new(tc.outputs["Object"], wv.inputs[4]); nt.links.new(wobble.outputs["Color"], wv.inputs[5])
    nt.links.new(wv.outputs[1], v1.inputs["Vector"]); nt.links.new(wv.outputs[1], v2.inputs["Vector"])
    c1 = ramp(nt, [(0.0, (0.38, 0.38, 0.38, 1)), (0.018, (1, 1, 1, 1))], (-1100, 300)); nt.links.new(v1.outputs["Distance"], c1.inputs["Fac"])
    c2 = ramp(nt, [(0.0, (0.7, 0.7, 0.7, 1)), (0.025, (1, 1, 1, 1))], (-1100, 0)); nt.links.new(v2.outputs["Distance"], c2.inputs["Fac"])
    cracks = mix_rgb(nt, 'MULTIPLY', 1.0, c1.outputs["Color"], c2.outputs["Color"], (-900, 200))
    # furrows of the old plowing running east-west
    fy = math_(nt, 'SINE', math_(nt, 'MULTIPLY', sep.outputs["Y"], 2 * math.pi / 0.75, (-1300, 600)), None, (-1150, 600))
    fur = math_(nt, 'MULTIPLY_ADD', fy, 0.5, (-1000, 600), c=0.5)
    en = node(nt, "ShaderNodeTexNoise", (-1300, -500)); en.inputs["Scale"].default_value = 1.4; en.inputs["Detail"].default_value = 10; en.inputs["Roughness"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], en.inputs["Vector"])
    earth = ramp(nt, [(0.3, (0.16, 0.155, 0.14, 1)), (0.55, (0.24, 0.235, 0.21, 1)), (0.75, (0.29, 0.28, 0.25, 1))], (-1000, -500))
    nt.links.new(en.outputs["Fac"], earth.inputs["Fac"])
    earth_c = mix_rgb(nt, 'MULTIPLY', 1.0, earth.outputs["Color"], cracks, (-700, -300))
    earth_c = mix_rgb(nt, 'MULTIPLY', 0.25, earth_c, fur, (-550, -300))
    # gray grass patches, streaked by the wind from the north
    gm = texcoord_obj(nt, (-1800, -900)); gm.inputs["Scale"].default_value = (6, 40, 1)
    gn = node(nt, "ShaderNodeTexNoise", (-1300, -900)); gn.inputs["Scale"].default_value = 1.0; gn.inputs["Detail"].default_value = 8
    nt.links.new(gm.outputs["Vector"], gn.inputs["Vector"])
    grass = ramp(nt, [(0.3, (0.17, 0.16, 0.125, 1)), (0.5, (0.25, 0.24, 0.19, 1)), (0.7, (0.35, 0.335, 0.27, 1))], (-1000, -900)); nt.links.new(gn.outputs["Fac"], grass.inputs["Fac"])
    pn = node(nt, "ShaderNodeTexNoise", (-1300, -1200)); pn.inputs["Scale"].default_value = 0.35; pn.inputs["Detail"].default_value = 5
    nt.links.new(tc.outputs["Object"], pn.inputs["Vector"])
    # grass thickens with distance from the house (the yard round the door is trodden bare)
    vl = node(nt, "ShaderNodeVectorMath", (-1300, -1400), operation='LENGTH'); nt.links.new(tc.outputs["Object"], vl.inputs[0])
    dr = node(nt, "ShaderNodeMapRange", (-1100, -1400)); dr.inputs["From Min"].default_value = 3.5; dr.inputs["From Max"].default_value = 7.0
    dr.inputs["To Min"].default_value = -0.15; dr.inputs["To Max"].default_value = 0.5
    nt.links.new(vl.outputs["Value"], dr.inputs["Value"])
    gmask_v = math_(nt, 'ADD', pn.outputs["Fac"], dr.outputs["Result"], (-950, -1200))
    gmask = ramp(nt, [(0.48, (0, 0, 0, 1)), (0.62, (1, 1, 1, 1))], (-800, -1200)); nt.links.new(gmask_v, gmask.inputs["Fac"])
    col = mix_rgb(nt, 'MIX', gmask.outputs["Color"], earth_c, grass.outputs["Color"], (-300, -500))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    h = mix_rgb(nt, 'MULTIPLY', 0.4, cracks, fur, (-300, -200))
    bump_from(nt, b, h, 0.7, 0.01)
    return m

def far_mat(name="M_DistantPrairie"):
    """The broad sweep of flat gray grass to the edge of the sky, long blades bowed in waves before the storm."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0))
    mp = node(nt, "ShaderNodeMapping", (-1400, 0)); mp.inputs["Scale"].default_value = (0.012, 0.06, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    waves = node(nt, "ShaderNodeTexNoise", (-1100, 0)); waves.inputs["Scale"].default_value = 1.0; waves.inputs["Detail"].default_value = 3; waves.inputs["Distortion"].default_value = 1.5
    nt.links.new(mp.outputs["Vector"], waves.inputs["Vector"])
    fm = node(nt, "ShaderNodeMapping", (-1400, -300)); fm.inputs["Scale"].default_value = (0.4, 2.0, 1)
    nt.links.new(tc.outputs["Object"], fm.inputs["Vector"])
    fine = node(nt, "ShaderNodeTexNoise", (-1100, -300)); fine.inputs["Scale"].default_value = 1.0; fine.inputs["Detail"].default_value = 8
    nt.links.new(fm.outputs["Vector"], fine.inputs["Vector"])
    mixf = node(nt, "ShaderNodeMix", (-850, 0), data_type='FLOAT'); mixf.inputs["Factor"].default_value = 0.35
    nt.links.new(waves.outputs["Fac"], mixf.inputs[2]); nt.links.new(fine.outputs["Fac"], mixf.inputs[3])
    r = ramp(nt, [(0.3, (0.17, 0.165, 0.13, 1)), (0.5, (0.26, 0.25, 0.20, 1)), (0.68, (0.35, 0.335, 0.27, 1))], (-600, 0))
    nt.links.new(mixf.outputs[0], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95
    return m

def grass_blade_mat(name="M_PrairieGrass"):
    """Long prairie blades: dark at the root, burned gray at the tips."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1200, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1000, 0))
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    zr = node(nt, "ShaderNodeMapRange", (-800, 0)); zr.inputs["From Min"].default_value = GZ; zr.inputs["From Max"].default_value = GZ + 0.7
    nt.links.new(sep.outputs["Z"], zr.inputs["Value"])
    n = node(nt, "ShaderNodeTexNoise", (-1000, -250)); n.inputs["Scale"].default_value = 2.5; n.inputs["Detail"].default_value = 3
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    f = math_(nt, 'MULTIPLY_ADD', n.outputs["Fac"], 0.4, (-650, -150), c=-0.2)
    fz = math_(nt, 'ADD', zr.outputs["Result"], f, (-500, 0))
    r = ramp(nt, [(0.0, (0.07, 0.07, 0.055, 1)), (0.35, (0.24, 0.23, 0.17, 1)), (0.8, (0.44, 0.42, 0.33, 1)), (1.0, (0.52, 0.50, 0.41, 1))], (-350, 0))
    nt.links.new(fz, r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85; b.inputs["Sheen Weight"].default_value = 0.3
    return m

def sky_dome_mat(name="M_SkyDome"):
    """A heavy, darkening storm sky: a low gray-green cloud deck in perspective, a paler sickly band along the
    flat horizon, darkest to the north where the wind is coming from."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-2000, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-1800, 0), operation='NORMALIZE'); nt.links.new(tc.outputs["Object"], nv.inputs[0])
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1600, 0)); nt.links.new(nv.outputs[0], sep.inputs["Vector"])
    el = sep.outputs["Z"]
    base = ramp(nt, [(0.0, (0.20, 0.215, 0.18, 1)), (0.10, (0.27, 0.29, 0.23, 1)), (0.112, (0.34, 0.36, 0.27, 1)), (0.13, (0.23, 0.26, 0.21, 1)),
                     (0.30, (0.13, 0.155, 0.14, 1)), (1.0, (0.08, 0.095, 0.09, 1))], (-1200, 300))
    elm = node(nt, "ShaderNodeMapRange", (-1400, 300)); elm.inputs["From Min"].default_value = -0.12; elm.inputs["From Max"].default_value = 1.0
    nt.links.new(el, elm.inputs["Value"]); nt.links.new(elm.outputs["Result"], base.inputs["Fac"])
    # project onto a flat cloud deck: xy / (z + k)
    zk = math_(nt, 'ADD', math_(nt, 'MAXIMUM', el, 0.0, (-1400, -100)), 0.10, (-1250, -100))
    px = math_(nt, 'DIVIDE', sep.outputs["X"], zk, (-1100, -50)); py = math_(nt, 'DIVIDE', sep.outputs["Y"], zk, (-1100, -200))
    cv = node(nt, "ShaderNodeCombineXYZ", (-950, -100)); nt.links.new(px, cv.inputs["X"]); nt.links.new(py, cv.inputs["Y"])
    mp = node(nt, "ShaderNodeMapping", (-800, -100)); mp.inputs["Scale"].default_value = (0.45, 0.8, 1); mp.inputs["Location"].default_value = (3.1, 7.7, 0.4)
    nt.links.new(cv.outputs[0], mp.inputs["Vector"])
    cl = node(nt, "ShaderNodeTexNoise", (-600, -100)); cl.inputs["Scale"].default_value = 1.1; cl.inputs["Detail"].default_value = 12; cl.inputs["Roughness"].default_value = 0.62; cl.inputs["Distortion"].default_value = 0.4
    nt.links.new(mp.outputs["Vector"], cl.inputs["Vector"])
    cl2 = node(nt, "ShaderNodeTexNoise", (-600, -400)); cl2.inputs["Scale"].default_value = 0.35; cl2.inputs["Detail"].default_value = 4; cl2.inputs["Distortion"].default_value = 1.0
    nt.links.new(mp.outputs["Vector"], cl2.inputs["Vector"])
    cmix = node(nt, "ShaderNodeMix", (-400, -200), data_type='FLOAT'); cmix.inputs["Factor"].default_value = 0.45
    nt.links.new(cl.outputs["Fac"], cmix.inputs[2]); nt.links.new(cl2.outputs["Fac"], cmix.inputs[3])
    cr = ramp(nt, [(0.28, (0.30, 0.335, 0.28, 1)), (0.42, (0.17, 0.205, 0.175, 1)), (0.56, (0.085, 0.10, 0.088, 1)), (0.70, (0.045, 0.052, 0.047, 1))], (-250, -200))
    nt.links.new(cmix.outputs[0], cr.inputs["Fac"])
    # the cloud deck covers the sky above ~5 degrees and fades out into the paler horizon band below
    cmask = node(nt, "ShaderNodeMapRange", (-400, 150)); cmask.inputs["From Min"].default_value = 0.012; cmask.inputs["From Max"].default_value = 0.09
    nt.links.new(el, cmask.inputs["Value"])
    col = mix_rgb(nt, 'MIX', cmask.outputs["Result"], base.outputs["Color"], cr.outputs["Color"], (0, 100))
    col = mix_rgb(nt, 'MULTIPLY', 0.35, col, base.outputs["Color"], (120, 100))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, (1.25, 1.25, 1.25, 1), (220, 100))
    # darker to the north (+y), a touch lighter and yellower low in the west-south-west where the sun is hidden
    nm = node(nt, "ShaderNodeMapRange", (-400, 400)); nm.inputs["From Min"].default_value = -1.0; nm.inputs["From Max"].default_value = 1.0
    nm.inputs["To Min"].default_value = 1.1; nm.inputs["To Max"].default_value = 0.55
    nt.links.new(sep.outputs["Y"], nm.inputs["Value"])
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, nm.outputs["Result"], (350, 100))
    sd = node(nt, "ShaderNodeVectorMath", (-1400, 600), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(SUN_DIR)
    nt.links.new(nv.outputs[0], sd.inputs[0])
    glow = node(nt, "ShaderNodeMapRange", (-1200, 600)); glow.inputs["From Min"].default_value = 0.75; glow.inputs["From Max"].default_value = 1.0
    glow.inputs["To Min"].default_value = 0.0; glow.inputs["To Max"].default_value = 0.35
    nt.links.new(sd.outputs["Value"], glow.inputs["Value"])
    col = mix_rgb(nt, 'ADD', glow.outputs["Result"], col, (0.32, 0.33, 0.20, 1), (480, 100))
    # emission only (black base): the render then shows exactly the colour Unity's unlit dome will show, and the
    # bake takes it with an EMIT pass
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m

# ----------------------------------------------------------------------------- materials
M_WALL = boards("M_WallBoards", light=(0.36, 0.35, 0.31), dark=(0.21, 0.20, 0.18), axis='Z', width=0.16, paint=(0.47, 0.48, 0.46), paint_amt=0.45, dirt=0.35)
M_FLOOR = boards("M_FloorPlanks", light=(0.36, 0.31, 0.24), dark=(0.20, 0.17, 0.13), axis='X', width=0.19, grain=(30, 1.2, 1.2), dirt=0.0, rough=0.8)
M_ROOF = boards("M_RoofBoards", light=(0.30, 0.27, 0.22), dark=(0.16, 0.14, 0.115), axis='Z', width=0.10, grain=(1.2, 1.2, 28), rough=0.9)
M_DOORPLANK = boards("M_DoorPlanks", light=(0.42, 0.40, 0.35), dark=(0.25, 0.235, 0.21), axis='X', width=0.15, grain=(28, 28, 1.2), paint=(0.56, 0.57, 0.55), paint_amt=0.4)
M_TRAP = trapdoor_mat()
M_RAFTER = wood("M_Rafters", base=(0.30, 0.27, 0.21), dark=(0.12, 0.10, 0.08), light=(0.42, 0.38, 0.30), grain_dir=(1, 14, 1), bands='Y', rough=(0.75, 0.95))
M_TRIM = noisy("M_WindowTrim", [(0.22, 0.20, 0.17), (0.46, 0.45, 0.41), (0.56, 0.55, 0.51)], scale=9, rough=0.8, bump=0.3, bump_dist=0.002, stretch=(1, 1, 4))
M_CUPBOARD = wood("M_Cupboard", base=(0.30, 0.31, 0.29), dark=(0.13, 0.12, 0.10), light=(0.43, 0.44, 0.41), rough=(0.6, 0.85))
M_TABLE = wood("M_TablePine", base=(0.40, 0.35, 0.27), dark=(0.20, 0.16, 0.11), light=(0.52, 0.47, 0.38), grain_dir=(14, 1, 1), bands='X', rough=(0.6, 0.85))
M_CHAIR = wood("M_ChairWood", base=(0.24, 0.17, 0.10), dark=(0.08, 0.05, 0.03), light=(0.36, 0.27, 0.17), scale=1.5)
M_BEDWOOD = wood("M_BedWood", base=(0.22, 0.15, 0.09), dark=(0.07, 0.045, 0.025), light=(0.34, 0.24, 0.14), coat=0.1)
M_RUST = rust()
M_IRON = noisy("M_BlackIron", [(0.025, 0.024, 0.022), (0.05, 0.045, 0.04), (0.12, 0.07, 0.04)], scale=12, rough=0.6, metallic=0.5, bump=0.2, bump_dist=0.001)
M_QUILT = quilt()
M_LINEN = noisy("M_Linen", [(0.50, 0.48, 0.43), (0.60, 0.58, 0.52), (0.64, 0.62, 0.56)], scale=14, rough=0.95, bump=0.2, bump_dist=0.002, sheen=0.3)
M_RAGRUG = ragrug()
M_CROCK = noisy("M_Crockery", [(0.58, 0.57, 0.52), (0.66, 0.65, 0.60)], scale=20, rough=0.25, bump=0.0, coat=0.6)
M_ENAMEL = noisy("M_Enamel", [(0.30, 0.33, 0.35), (0.40, 0.43, 0.45), (0.10, 0.10, 0.10)], scale=60, rough=0.3, bump=0.0, coat=0.4)
M_TIN = plain("M_LampBrass", (0.55, 0.42, 0.22), rough=0.35, metallic=1.0)
M_GLASS = plain("M_LampGlass", (0.85, 0.85, 0.80), rough=0.03, transmission=1.0)
M_FLAME = plain("M_Flame", (1.0, 0.8, 0.5), emission=(1.0, 0.62, 0.25), strength=30)
M_EMBERS = plain("M_StoveEmbers", (0.6, 0.2, 0.05), rough=0.9, emission=(1.0, 0.35, 0.08), strength=4)
M_CALICO = noisy("M_Calico", [(0.36, 0.31, 0.26), (0.48, 0.42, 0.35), (0.55, 0.50, 0.43)], scale=40, rough=0.95, bump=0.1, bump_dist=0.001, sheen=0.4)
M_STRAW = noisy("M_BroomStraw", [(0.36, 0.30, 0.17), (0.50, 0.43, 0.26)], scale=60, rough=0.75, stretch=(1, 1, 10), bump=0.2, bump_dist=0.002)
M_GROUND = ground_mat()
M_FAR = far_mat()
M_GRASS = grass_blade_mat()
M_SKY = sky_dome_mat()

# ----------------------------------------------------------------------------- geometry helpers (from build_lobby.py / build_mad_tea_party.py)
def _finish(o, mat, smooth=False):
    o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = 1; md.limit_method = 'ANGLE'
    return _finish(o, mat)

def cyl(name, r, h, loc, mat, verts=16, rot=(0, 0, 0), r2=None):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat, smooth=True)

def sphere(name, r, loc, mat, seg=12, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(4, seg // 2), radius=r, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, mat, smooth=True)

def torus(name, R, r, loc, mat, rot=(0, 0, 0), seg=16, rseg=6):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=rseg, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat, smooth=True)

def lathe(name, profile, loc, mat, steps=16):
    """profile: list of (radius, z) from bottom to top; revolve around Z (radius 0 = a pole)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for (r, z) in profile:
        if r < 1e-5: rings.append([bm.verts.new((0, 0, z))]); continue
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / steps), r * math.sin(2 * math.pi * i / steps), z)) for i in range(steps)])
    for a, b_ in zip(rings, rings[1:]):
        if len(a) == 1 and len(b_) == 1: continue
        if len(a) == 1:
            for i in range(steps): bm.faces.new((a[0], b_[i], b_[(i + 1) % steps]))
        elif len(b_) == 1:
            for i in range(steps): bm.faces.new((a[i], a[(i + 1) % steps], b_[0]))
        else:
            for i in range(steps):
                j = (i + 1) % steps; bm.faces.new((a[i], a[j], b_[j], b_[i]))
    bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def prism_yz(name, pts, x0, x1, mat):
    """A flat polygon in the y-z plane (pts) extruded along x: the gable ends."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in pts]; b_ = [bm.verts.new((x1, y, z)) for y, z in pts]
    bm.faces.new(a); bm.faces.new(list(reversed(b_)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((a[i], a[j], b_[j], b_[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

class Frame:
    """Local frame for a piece of furniture: +Y forward, origin on the floor, turned by yaw about Z."""
    def __init__(self, origin, yaw):
        self.o = Vector((origin[0], origin[1], 0.0)); self.yaw = yaw; self.R = Matrix.Rotation(yaw, 3, 'Z')
    def p(self, x, y, z): return tuple(self.o + self.R @ Vector((x, y, z)))
    def box(self, name, size, local, mat, bevel=0.0, rx=0.0): return box(name, size, self.p(*local), mat, bevel=bevel, rot=(rx, 0, self.yaw))
    def cyl(self, name, r, h, local, mat, verts=8, r2=None): return cyl(name, r, h, self.p(*local), mat, verts=verts, rot=(0, 0, self.yaw), r2=r2)

# ----------------------------------------------------------------------------- the room: four walls, a floor and a roof
box("Floor", (ROOM_W + 2 * T, ROOM_D + 2 * T, 0.10), (0, 0, -0.05), M_FLOOR)
box("FloorSill", (ROOM_W + 2 * T + 0.04, ROOM_D + 2 * T + 0.04, -GZ - 0.10 + 0.02), (0, 0, (GZ - 0.02 - 0.10) / 2), M_RAFTER)

def wall(name, axis, fixed, a0, a1, z0, z1, openings, mat=M_WALL):
    """A board wall along `axis` at `fixed`, from a0 to a1, with rectangular openings (centre, width, oz0, oz1)."""
    def piece(nm, l, r, zb, zt):
        if r - l < 1e-4 or zt - zb < 1e-4: return
        if axis == 'x': box(nm, (r - l, T, zt - zb), ((l + r) / 2, fixed, (zb + zt) / 2), mat)
        else: box(nm, (T, r - l, zt - zb), (fixed, (l + r) / 2, (zb + zt) / 2), mat)
    cur = a0; k = 0
    for (c, w, oz0, oz1) in sorted(openings):
        l, r = c - w / 2, c + w / 2
        piece(f"{name}_{k}", cur, l, z0, z1); piece(f"{name}_{k}b", l, r, z0, oz0); piece(f"{name}_{k}t", l, r, oz1, z1)
        cur = r; k += 1
    piece(f"{name}_{k}", cur, a1, z0, z1)

WZ0 = GZ - 0.02
wall("Wall_S", 'x', -HY - T / 2, -HX - T, HX + T, WZ0, EAVE, [(DOOR_X, DOOR_W, WZ0, DOOR_H)])
wall("Wall_N", 'x', HY + T / 2, -HX - T, HX + T, WZ0, EAVE, [(WIN_N_X, WIN_W, WIN_Z0, WIN_Z1)])
wall("Wall_W", 'y', -HX - T / 2, -HY, HY, WZ0, EAVE, [(WIN_W_Y, WIN_W, WIN_Z0, WIN_Z1)])
wall("Wall_E", 'y', HX + T / 2, -HY, HY, WZ0, EAVE, [(WIN_E_Y, WIN_W, WIN_Z0, WIN_Z1)])
for s in (-1, 1):
    x0 = s * HX if s > 0 else -HX - T
    prism_yz(f"Gable{s}", [(-HY - T, EAVE), (HY + T, EAVE), (0.0, RIDGE + 0.02)], x0, x0 + T, M_WALL)
# the floor opening at the door is the threshold board
box("Threshold", (DOOR_W, T + 0.04, 0.03), (DOOR_X, -HY - T / 2, 0.015), M_TRIM)

# roof: two board slabs, rafters under them, a ridge board, ceiling ties across at the eaves (no garret above)
OV = 0.30                      # eave overhang beyond the wall face
L_SLAB = (HY + T + OV) / math.cos(PITCH)
for s, nm in ((-1, "S"), (1, "N")):
    # underside line from the ridge (0, RIDGE) down to the eave edge
    ey, ez = s * (HY + T + OV), RIDGE - (HY + T + OV) * SLOPE
    mid = Vector((0, ey / 2, (RIDGE + ez) / 2))
    nrm = Vector((0, s * math.sin(PITCH), math.cos(PITCH)))
    rot = (-s * PITCH, 0, 0)
    box(f"Roof_{nm}", (ROOM_W + 2 * T + 2 * 0.25, L_SLAB + 0.03, 0.04), tuple(mid + nrm * 0.02), M_ROOF, rot=rot)
    # rafters: from the wall plate to the ridge
    lr = (HY + T) / math.cos(PITCH)
    rmid = Vector((0, s * (HY + T) / 2, (RIDGE + EAVE) / 2)) - nrm * 0.05
    for i, x in enumerate([-2.42 + k * 0.605 for k in range(9)]):
        box(f"Rafter_{nm}{i}", (0.05, lr, 0.10), (x, rmid.y, rmid.z), M_RAFTER, rot=rot)
    box(f"Fascia_{nm}", (ROOM_W + 2 * T + 0.5, 0.025, 0.14), (0, ey + s * 0.012, ez - 0.03), M_RAFTER)
    box(f"Plate_{nm}", (ROOM_W, 0.10, 0.08), (0, s * (HY - 0.05), EAVE - 0.04), M_RAFTER)
box("RidgeBoard", (ROOM_W + 2 * T, 0.04, 0.18), (0, 0, RIDGE - 0.12), M_RAFTER)
for i, x in enumerate([-1.21, 0.0, 1.21]):
    box(f"CeilingTie{i}", (0.06, ROOM_D, 0.12), (x, 0, EAVE - 0.02), M_RAFTER)
for s in (-1, 1):
    box(f"PlateEW{s}", (0.10, ROOM_D, 0.08), (s * (HX - 0.05), 0, EAVE - 0.04), M_RAFTER)
# corner posts inside (the frame the boards are nailed to)
for sx in (-1, 1):
    for sy in (-1, 1):
        box(f"CornerPost{sx}{sy}", (0.08, 0.08, EAVE), (sx * (HX - 0.04), sy * (HY - 0.04), EAVE / 2), M_RAFTER)

# ----------------------------------------------------------------------------- the door (open) and windows
def casing_x(name, cx, w, z0, z1, y_in, depth_sign):
    """Trim round an opening in a wall along x (inner face at y_in, room on the -depth_sign side)."""
    box(f"{name}_JambL", (0.03, T + 0.02, z1 - z0), (cx - w / 2 + 0.015, y_in + depth_sign * T / 2, (z0 + z1) / 2), M_TRIM)
    box(f"{name}_JambR", (0.03, T + 0.02, z1 - z0), (cx + w / 2 - 0.015, y_in + depth_sign * T / 2, (z0 + z1) / 2), M_TRIM)
    box(f"{name}_Head", (w + 0.20, 0.02, 0.10), (cx, y_in - depth_sign * 0.01, z1 + 0.05), M_TRIM)
    for s in (-1, 1):
        box(f"{name}_Case{s}", (0.08, 0.02, z1 - max(z0, 0.0)), (cx + s * (w / 2 + 0.04), y_in - depth_sign * 0.01, (max(z0, 0.0) + z1) / 2), M_TRIM)

def casing_y(name, cy, w, z0, z1, x_in, depth_sign):
    box(f"{name}_JambL", (T + 0.02, 0.03, z1 - z0), (x_in + depth_sign * T / 2, cy - w / 2 + 0.015, (z0 + z1) / 2), M_TRIM)
    box(f"{name}_JambR", (T + 0.02, 0.03, z1 - z0), (x_in + depth_sign * T / 2, cy + w / 2 - 0.015, (z0 + z1) / 2), M_TRIM)
    box(f"{name}_Head", (0.02, w + 0.20, 0.10), (x_in - depth_sign * 0.01, cy, z1 + 0.05), M_TRIM)
    for s in (-1, 1):
        box(f"{name}_Case{s}", (0.02, 0.08, z1 - z0), (x_in - depth_sign * 0.01, cy + s * (w / 2 + 0.04), (z0 + z1) / 2), M_TRIM)

def sash(name, centre, w, along, z0, z1):
    """An open-paned window sash in the plane of the wall (no glass: nothing between the reader and the prairie)."""
    cx, cy = centre
    def bar(nm, length, horiz, a, z):
        if horiz:
            size = (length, 0.035, 0.035) if along == 'x' else (0.035, length, 0.035)
        else:
            size = (0.025, 0.035, length) if along == 'x' else (0.035, 0.025, length)
        loc = (cx + a, cy, z) if along == 'x' else (cx, cy + a, z)
        box(nm, size, loc, M_TRIM)
    for i, z in enumerate([z0 + 0.025, (z0 + z1) / 2, z1 - 0.025]):
        bar(f"{name}_Rail{i}", w, True, 0.0, z)
    for i, a in enumerate([-w / 2 + 0.02, -w / 6, w / 6, w / 2 - 0.02]):
        bar(f"{name}_Stile{i}", z1 - z0, False, a, (z0 + z1) / 2)
    # sill: a board proud of the wall on both faces
    if along == 'x': box(f"{name}_Sill", (w + 0.12, T + 0.10, 0.03), (cx, cy, z0 - 0.015), M_TRIM)
    else: box(f"{name}_Sill", (T + 0.10, w + 0.12, 0.03), (cx, cy, z0 - 0.015), M_TRIM)

casing_x("DoorCase", DOOR_X, DOOR_W, 0.0, DOOR_H, -HY, -1)
sash("WinN", (WIN_N_X, HY + T / 2), WIN_W, 'x', WIN_Z0, WIN_Z1); casing_x("WinNCase", WIN_N_X, WIN_W, WIN_Z0, WIN_Z1, HY, 1)
sash("WinW", (-HX - T / 2, WIN_W_Y), WIN_W, 'y', WIN_Z0, WIN_Z1); casing_y("WinWCase", WIN_W_Y, WIN_W, WIN_Z0, WIN_Z1, -HX, -1)
sash("WinE", (HX + T / 2, WIN_E_Y), WIN_W, 'y', WIN_Z0, WIN_Z1); casing_y("WinECase", WIN_E_Y, WIN_W, WIN_Z0, WIN_Z1, HX, 1)
# a faded flour-sack curtain hung on a string, pushed to one side of the east window
box("CurtainE", (0.012, 0.30, 0.62), (HX - 0.03, WIN_E_Y + 0.24, WIN_Z1 - 0.33), M_CALICO, bevel=0.004)
cyl("CurtainString", 0.003, WIN_W + 0.2, (HX - 0.03, WIN_E_Y, WIN_Z1 + 0.0), M_IRON, verts=4, rot=(math.radians(90), 0, 0))

# the door leaf: battened planks, hinged on the west jamb and swung in against the wall, a little ajar
hinge = Vector((DOOR_X - DOOR_W / 2 + 0.03, -HY + 0.02, 0.0))
DOOR_OPEN = math.radians(158)
LW = DOOR_W - 0.04
ldir = Vector((math.cos(DOOR_OPEN), math.sin(DOOR_OPEN), 0)); lnrm = Vector((-ldir.y, ldir.x, 0))
def leafpt(a, n, z): return tuple(hinge + ldir * a + lnrm * n + Vector((0, 0, z)))
box("DoorLeaf", (LW, 0.035, DOOR_H - 0.02), leafpt(LW / 2, 0.0, DOOR_H / 2), M_DOORPLANK, rot=(0, 0, DOOR_OPEN))
for i, z in enumerate([0.25, 1.0, 1.75]):
    box(f"DoorBatten{i}", (LW - 0.08, 0.025, 0.11), leafpt(LW / 2, -0.03, z), M_DOORPLANK, rot=(0, 0, DOOR_OPEN))
for i, (za, zb) in enumerate([(0.25, 1.0), (1.0, 1.75)]):
    ln = math.hypot(LW - 0.16, zb - za - 0.06)
    box(f"DoorBrace{i}", (ln, 0.022, 0.09), leafpt(LW / 2, -0.03, (za + zb) / 2), M_DOORPLANK, rot=(0, -math.atan2(zb - za - 0.06, LW - 0.16), DOOR_OPEN))
for i, z in enumerate([0.25, 1.75]):
    box(f"DoorStrap{i}", (0.32, 0.006, 0.03), leafpt(0.17, 0.02, z), M_IRON, rot=(0, 0, DOOR_OPEN))
lathe("DoorLatch", [(0.012, 0), (0.012, 0.03), (0.0, 0.035)], leafpt(LW - 0.08, 0.02, 1.0), M_IRON, steps=8)
# the doorstep outside, where Uncle Henry sat
box("Doorstep", (1.25, 0.42, 0.14), (DOOR_X, -HY - T - 0.21, GZ + 0.07), M_DOORPLANK, bevel=0.01)
box("DoorstepBlock", (1.1, 0.34, 0.10), (DOOR_X, -HY - T - 0.20, GZ + 0.0), M_RAFTER)

# ----------------------------------------------------------------------------- the trap door to the cyclone cellar
box("TrapDoor", (TRAP, TRAP, 0.03), (0, 0, -0.011), M_TRAP)
torus("TrapRing", 0.06, 0.009, (0, -TRAP / 2 + 0.12, 0.009), M_IRON)
box("TrapRingStaple", (0.03, 0.02, 0.006), (0, -TRAP / 2 + 0.075, 0.006), M_IRON)
for s in (-1, 1):
    box(f"TrapHinge{s}", (0.045, 0.30, 0.006), (s * 0.24, TRAP / 2 - 0.10, 0.006), M_IRON)
    box(f"TrapHingeLeaf{s}", (0.10, 0.05, 0.006), (s * 0.24, TRAP / 2 + 0.04, 0.006), M_IRON)

# ----------------------------------------------------------------------------- a rusty-looking cookstove, against the west wall
sx, sy = STOVE
SD, SW, SH = 0.60, 0.95, 0.74                      # depth (x), width (y), top height
st = []
box("Stove_Body", (SD - 0.04, SW - 0.18, SH - 0.20), (sx, sy + 0.09, 0.15 + (SH - 0.20) / 2), M_RUST, bevel=0.01)
box("Stove_Firebox", (SD - 0.04, 0.16, SH - 0.20), (sx, sy - SW / 2 + 0.08, 0.15 + (SH - 0.20) / 2), M_RUST, bevel=0.01)
box("Stove_Top", (SD + 0.04, SW + 0.06, 0.04), (sx, sy, SH - 0.03), M_RUST, bevel=0.008)
box("Stove_Skirt", (SD, SW, 0.06), (sx, sy, 0.17), M_RUST, bevel=0.005)
box("Stove_OvenDoor", (0.02, 0.50, 0.32), (sx + SD / 2 - 0.01, sy + 0.12, 0.40), M_RUST, bevel=0.006)
box("Stove_OvenHandle", (0.03, 0.14, 0.02), (sx + SD / 2 + 0.015, sy + 0.12, 0.53), M_IRON, bevel=0.004)
box("Stove_FireDoor", (0.02, 0.15, 0.17), (sx + SD / 2 - 0.01, sy - SW / 2 + 0.09, 0.50), M_RUST, bevel=0.005)
for k in range(4):                                  # the draft slots in the firebox door: the fire is in for Aunt Em's dishwater
    box(f"Stove_Draft{k}", (0.006, 0.016, 0.06), (sx + SD / 2 + 0.0, sy - SW / 2 + 0.05 + k * 0.026, 0.50), M_EMBERS)
box("Stove_AshDoor", (0.02, 0.15, 0.09), (sx + SD / 2 - 0.01, sy - SW / 2 + 0.09, 0.25), M_RUST, bevel=0.004)
box("Stove_Rail", (0.025, SW + 0.04, 0.025), (sx + SD / 2 + 0.06, sy, SH - 0.10), M_IRON)
for s in (-1, 1):
    box(f"Stove_RailArm{s}", (0.08, 0.02, 0.02), (sx + SD / 2 + 0.02, sy + s * (SW / 2 + 0.01), SH - 0.10), M_IRON)
for i, (dx, dy) in enumerate([(-0.12, -0.24), (0.12, -0.24), (-0.12, 0.05), (0.12, 0.05)]):
    cyl(f"Stove_Lid{i}", 0.095, 0.012, (sx + dx, sy + dy, SH - 0.004), M_IRON, verts=16)
    box(f"Stove_LidLift{i}", (0.04, 0.012, 0.006), (sx + dx, sy + dy, SH + 0.005), M_IRON)
box("Stove_Back", (0.04, SW + 0.06, 0.36), (sx - SD / 2 + 0.0, sy, SH + 0.17), M_RUST, bevel=0.006)
box("Stove_Shelf", (0.24, SW + 0.06, 0.025), (sx - SD / 2 + 0.10, sy, SH + 0.36), M_RUST, bevel=0.005)
for dx in (-1, 1):
    for dy in (-1, 1):
        cyl(f"Stove_Leg{dx}{dy}", 0.03, 0.16, (sx + dx * (SD / 2 - 0.05), sy + dy * (SW / 2 - 0.06), 0.08), M_IRON, verts=8, r2=0.02)
# stovepipe straight up through the roof boards, with a damper collar
PIPE = (sx - SD / 2 + 0.12, sy + 0.12)
roof_z_at_pipe = RIDGE - abs(PIPE[1]) * SLOPE
pipe_top = roof_z_at_pipe + 0.55
cyl("Stove_Pipe", 0.065, pipe_top - (SH + 0.38), (PIPE[0], PIPE[1], (pipe_top + SH + 0.38) / 2), M_RUST, verts=14)
cyl("Stove_PipeCollar", 0.075, 0.05, (PIPE[0], PIPE[1], SH + 0.42), M_IRON, verts=14)
cyl("Stove_PipeDamper", 0.072, 0.03, (PIPE[0], PIPE[1], 1.55), M_IRON, verts=14)
cyl("Stove_PipeCap", 0.11, 0.08, (PIPE[0], PIPE[1], pipe_top + 0.04), M_RUST, verts=14, r2=0.03)
cyl("Stove_RoofJack", 0.12, 0.06, (PIPE[0], PIPE[1], roof_z_at_pipe + 0.04), M_RUST, verts=14)
# the kettle and a skillet on the stove
KZ = SH + 0.006
lathe("Kettle", [(0.0, KZ), (0.10, KZ), (0.115, KZ + 0.04), (0.11, KZ + 0.11), (0.07, KZ + 0.15), (0.04, KZ + 0.16), (0.045, KZ + 0.17), (0.0, KZ + 0.17)], (sx - 0.1, sy - 0.24, 0), M_IRON, steps=16)
torus("KettleBail", 0.075, 0.006, (sx - 0.1, sy - 0.24, KZ + 0.17), M_IRON, rot=(math.radians(90), 0, 0), seg=16, rseg=4)
cyl("KettleSpout", 0.015, 0.12, (sx - 0.1 + 0.12, sy - 0.24, KZ + 0.10), M_IRON, verts=6, rot=(0, math.radians(55), 0), r2=0.008)
cyl("Skillet", 0.12, 0.035, (sx + 0.12, sy + 0.08, KZ + 0.018), M_IRON, verts=16)
box("SkilletHandle", (0.18, 0.025, 0.012), (sx + 0.27, sy + 0.08, KZ + 0.03), M_IRON)
# the wood box beside the stove, with cobs and chips
WB = (-2.18, -0.55)
box("WoodBox_Base", (0.46, 0.38, 0.02), (WB[0], WB[1], 0.01), M_DOORPLANK)
for s in (-1, 1):
    box(f"WoodBox_SideY{s}", (0.46, 0.02, 0.36), (WB[0], WB[1] + s * 0.18, 0.18), M_DOORPLANK)
    box(f"WoodBox_SideX{s}", (0.02, 0.38, 0.36), (WB[0] + s * 0.22, WB[1], 0.18), M_DOORPLANK)
for i in range(9):
    a = random.uniform(0, math.pi)
    cyl(f"WoodBox_Stick{i}", random.uniform(0.025, 0.04), 0.40, (WB[0] + random.uniform(-0.12, 0.12), WB[1] + random.uniform(-0.1, 0.1), 0.30 + random.uniform(0, 0.06)),
        M_RAFTER, verts=6, rot=(math.radians(90) + random.uniform(-0.2, 0.2), 0, a))

# ----------------------------------------------------------------------------- the cupboard for the dishes (north wall)
CB_X0, CB_X1 = 1.30, 2.40
cbx = (CB_X0 + CB_X1) / 2; CBW = CB_X1 - CB_X0
LD, UD = 0.46, 0.28                                    # lower and upper depths
yb = HY                                                # back against the north wall
box("Cupboard_LowerCase", (CBW, LD, 0.84), (cbx, yb - LD / 2, 0.46), M_CUPBOARD, bevel=0.006)
box("Cupboard_Plinth", (CBW + 0.02, LD - 0.04, 0.05), (cbx, yb - LD / 2 + 0.01, 0.025), M_CUPBOARD)
box("Cupboard_Counter", (CBW + 0.06, LD + 0.04, 0.03), (cbx, yb - LD / 2 - 0.01, 0.895), M_CUPBOARD, bevel=0.006)
for i, s in enumerate((-1, 1)):
    box(f"Cupboard_Door{i}", (CBW / 2 - 0.06, 0.02, 0.68), (cbx + s * CBW / 4, yb - LD - 0.008, 0.47), M_CUPBOARD, bevel=0.008)
    sphere(f"Cupboard_Knob{i}", 0.014, (cbx + s * 0.06, yb - LD - 0.03, 0.62), M_IRON, seg=8)
box("Cupboard_DrawerRail", (CBW, 0.02, 0.04), (cbx, yb - LD - 0.008, 0.85), M_CUPBOARD)
# upper: open plate shelves
UZ0, UZ1 = 0.91, 2.05
for s in (-1, 1):
    box(f"Cupboard_UpperSide{s}", (0.025, UD, UZ1 - UZ0), (cbx + s * (CBW / 2 - 0.0125), yb - UD / 2, (UZ0 + UZ1) / 2), M_CUPBOARD)
box("Cupboard_UpperBack", (CBW, 0.015, UZ1 - UZ0), (cbx, yb - 0.008, (UZ0 + UZ1) / 2), M_CUPBOARD)
box("Cupboard_Cornice", (CBW + 0.08, UD + 0.06, 0.05), (cbx, yb - UD / 2 - 0.03, UZ1 + 0.025), M_CUPBOARD, bevel=0.008)
SHELVES = [1.28, 1.66]
for i, z in enumerate(SHELVES):
    box(f"Cupboard_Shelf{i}", (CBW - 0.05, UD - 0.02, 0.02), (cbx, yb - UD / 2, z - 0.01), M_CUPBOARD)
    box(f"Cupboard_PlateRail{i}", (CBW - 0.05, 0.012, 0.02), (cbx, yb - UD + 0.05, z + 0.05), M_CUPBOARD)
# plates stood up along the shelves, cups and bowls on the counter shelf
for i, z in enumerate(SHELVES):
    n = 6 if i == 0 else 5
    for k in range(n):
        x = CB_X0 + 0.11 + k * (CBW - 0.22) / max(1, n - 1)
        r = 0.11 if i == 0 else 0.09
        cyl(f"Plate{i}_{k}", r, 0.012, (x, yb - 0.10, z + r + 0.002), M_CROCK, verts=14, rot=(math.radians(76), 0, 0))
for k in range(5):
    x = CB_X0 + 0.14 + k * 0.2
    lathe(f"Cup{k}", [(0.0, UZ0 + 0.02), (0.03, UZ0 + 0.02), (0.042, UZ0 + 0.10), (0.039, UZ0 + 0.10), (0.0, UZ0 + 0.03)], (x, yb - 0.16, 0), M_CROCK, steps=10)
lathe("Pitcher", [(0.0, UZ0 + 0.02), (0.06, UZ0 + 0.02), (0.075, UZ0 + 0.12), (0.05, UZ0 + 0.22), (0.058, UZ0 + 0.26), (0.0, UZ0 + 0.255)], (CB_X1 - 0.12, yb - 0.12, 0), M_ENAMEL, steps=14)

# ----------------------------------------------------------------------------- the table, with the oil lamp and Aunt Em's dishes
tx, ty = TABLE
TW, TD = 1.10, 0.74
box("Table_Top", (TW, TD, 0.035), (tx, ty, TABLE_H - 0.0175), M_TABLE, bevel=0.006)
for s in (-1, 1):
    box(f"Table_ApronX{s}", (TW - 0.12, 0.022, 0.10), (tx, ty + s * (TD / 2 - 0.07), TABLE_H - 0.085), M_TABLE)
    box(f"Table_ApronY{s}", (0.022, TD - 0.14, 0.10), (tx + s * (TW / 2 - 0.08), ty, TABLE_H - 0.085), M_TABLE)
for dx in (-1, 1):
    for dy in (-1, 1):
        cyl(f"Table_Leg{dx}{dy}", 0.028, TABLE_H - 0.035, (tx + dx * (TW / 2 - 0.08), ty + dy * (TD / 2 - 0.07), (TABLE_H - 0.035) / 2), M_TABLE, verts=8, r2=0.02)
# oil lamp: tin font, glass chimney, a small flame (the room's lamp)
LX, LY, LZ = tx + 0.30, ty + 0.16, TABLE_H
lathe("Lamp_Font", [(0.0, LZ), (0.065, LZ), (0.07, LZ + 0.015), (0.03, LZ + 0.03), (0.025, LZ + 0.07), (0.07, LZ + 0.10), (0.072, LZ + 0.14), (0.04, LZ + 0.17), (0.022, LZ + 0.18), (0.0, LZ + 0.18)], (LX, LY, 0), M_TIN, steps=16)
lathe("Lamp_Burner", [(0.0, LZ + 0.18), (0.025, LZ + 0.18), (0.028, LZ + 0.21), (0.0, LZ + 0.215)], (LX, LY, 0), M_TIN, steps=12)
lathe("LampGlass", [(0.022, LZ + 0.21), (0.03, LZ + 0.22), (0.045, LZ + 0.26), (0.043, LZ + 0.30), (0.024, LZ + 0.35), (0.022, LZ + 0.44)], (LX, LY, 0), M_GLASS, steps=16)
sphere("Lamp_Flame", 0.009, (LX, LY, LZ + 0.245), M_FLAME, seg=8, scale=(1, 1, 2.0))
# the dishpan, a stack of plates and a cup
lathe("Dishpan", [(0.0, TABLE_H + 0.002), (0.13, TABLE_H + 0.002), (0.17, TABLE_H + 0.10), (0.175, TABLE_H + 0.105), (0.168, TABLE_H + 0.105), (0.125, TABLE_H + 0.012), (0.0, TABLE_H + 0.012)], (tx - 0.22, ty - 0.08, 0), M_ENAMEL, steps=18)
for k in range(4):
    cyl(f"TablePlate{k}", 0.11, 0.012, (tx + 0.10, ty - 0.12, TABLE_H + 0.006 + k * 0.013), M_CROCK, verts=16)
lathe("TableCup", [(0.0, TABLE_H), (0.03, TABLE_H), (0.042, TABLE_H + 0.08), (0.039, TABLE_H + 0.08), (0.0, TABLE_H + 0.01)], (tx + 0.32, ty - 0.18, 0), M_CROCK, steps=10)
box("DishCloth", (0.24, 0.18, 0.006), (tx - 0.02, ty + 0.2, TABLE_H + 0.003), M_LINEN, rot=(0, 0, math.radians(14)))

# ----------------------------------------------------------------------------- three or four chairs (four plain ladder-backs)
def chair(name, origin, yaw):
    f = Frame(origin, yaw)
    f.box(f"{name}_Seat", (0.42, 0.40, 0.03), (0, 0, 0.45), M_CHAIR, bevel=0.005)
    for dx in (-1, 1):
        f.cyl(f"{name}_FrontLeg{dx}", 0.018, 0.45, (dx * 0.18, 0.17, 0.225), M_CHAIR)
        f.cyl(f"{name}_BackPost{dx}", 0.02, 0.98, (dx * 0.18, -0.17, 0.49), M_CHAIR)
        f.box(f"{name}_SideRung{dx}", (0.016, 0.34, 0.016), (dx * 0.18, 0.0, 0.16), M_CHAIR)
    for i, z in enumerate([0.68, 0.80, 0.92]):
        f.box(f"{name}_Slat{i}", (0.34, 0.016, 0.055), (0, -0.17, z), M_CHAIR, bevel=0.003)
    f.box(f"{name}_FrontRung", (0.34, 0.016, 0.016), (0, 0.17, 0.12), M_CHAIR)
chair("ChairS", (tx - 0.05, ty - TD / 2 - 0.22), 0.0 + math.radians(6))
chair("ChairN", (tx + 0.05, ty + TD / 2 + 0.22), math.pi - math.radians(4))
chair("ChairE", (tx + TW / 2 + 0.30, ty - 0.02), math.radians(90) + math.radians(8))
chair("ChairStove", (-1.48, -0.62), math.radians(-115))

# ----------------------------------------------------------------------------- the beds
def bed(name, x0, x1, y0, y1, head_y_sign, head_h, foot_h, mat_frame, iron=False, pillows=2):
    """A bed whose head is against the wall on the head_y_sign side: x0..x1 across, y0..y1 long."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; w, L = x1 - x0, y1 - y0
    hy_ = y1 if head_y_sign > 0 else y0; fy_ = y0 if head_y_sign > 0 else y1
    inward = -head_y_sign
    if iron:
        for i, (yy, h) in enumerate([(hy_, head_h), (fy_, foot_h)]):
            for s in (-1, 1):
                cyl(f"{name}_Post{i}{s}", 0.018, h, (cx + s * (w / 2 - 0.02), yy + inward * 0.02 * (1 if i == 0 else -1), h / 2), mat_frame, verts=8)
            cyl(f"{name}_TopRail{i}", 0.014, w - 0.04, (cx, yy + inward * 0.02 * (1 if i == 0 else -1), h - 0.03), mat_frame, verts=8, rot=(0, math.radians(90), 0))
            cyl(f"{name}_MidRail{i}", 0.01, w - 0.04, (cx, yy + inward * 0.02 * (1 if i == 0 else -1), 0.32), mat_frame, verts=6, rot=(0, math.radians(90), 0))
            for k in range(5):
                xx = cx - w / 2 + 0.1 + k * (w - 0.2) / 4
                cyl(f"{name}_Spindle{i}{k}", 0.007, h - 0.36, (xx, yy + inward * 0.02 * (1 if i == 0 else -1), 0.32 + (h - 0.36) / 2), mat_frame, verts=6)
        for s in (-1, 1):
            box(f"{name}_SideRail{s}", (0.03, L - 0.04, 0.05), (cx + s * (w / 2 - 0.02), cy, 0.30), mat_frame)
    else:
        box(f"{name}_Headboard", (w, 0.05, head_h), (cx, hy_ + inward * 0.025, head_h / 2), mat_frame, bevel=0.01)
        box(f"{name}_HeadCap", (w + 0.06, 0.08, 0.05), (cx, hy_ + inward * 0.03, head_h + 0.02), mat_frame, bevel=0.01)
        box(f"{name}_Footboard", (w, 0.05, foot_h), (cx, fy_ - inward * 0.025, foot_h / 2), mat_frame, bevel=0.01)
        box(f"{name}_FootCap", (w + 0.06, 0.08, 0.05), (cx, fy_ - inward * 0.03, foot_h + 0.02), mat_frame, bevel=0.01)
        for s in (-1, 1):
            box(f"{name}_SideRail{s}", (0.04, L - 0.08, 0.16), (cx + s * (w / 2 - 0.02), cy, 0.32), mat_frame, bevel=0.005)
    mz = 0.40
    box(f"{name}_Mattress", (w - 0.08, L - 0.10, 0.20), (cx, cy, mz + 0.10), M_LINEN, bevel=0.04)
    # the quilt: over the top and hanging down the open side(s), turned back at the head
    qL = L - 0.40
    qy = cy + inward * 0.17
    box(f"{name}_QuiltTop", (w - 0.02, qL, 0.04), (cx, qy, mz + 0.21), M_QUILT, bevel=0.015)
    for s in (-1, 1):
        box(f"{name}_QuiltSide{s}", (0.02, qL, 0.26), (cx + s * (w / 2 - 0.005), qy, mz + 0.10), M_QUILT, bevel=0.008)
    box(f"{name}_QuiltFoot", (w - 0.02, 0.02, 0.22), (cx, fy_ - inward * 0.07, mz + 0.12), M_QUILT, bevel=0.008)
    box(f"{name}_SheetTurn", (w - 0.04, 0.16, 0.05), (cx, qy - inward * (qL / 2 + 0.06), mz + 0.215), M_LINEN, bevel=0.015)
    for k in range(pillows):
        px = cx + (k - (pillows - 1) / 2) * (w / max(1, pillows)) * 0.95
        sphere(f"{name}_Pillow{k}", 0.5, (px, hy_ + inward * 0.22, mz + 0.27), M_LINEN, seg=12, scale=((w / pillows) * 0.82 if pillows > 1 else w * 0.7, 0.36, 0.12))

# Uncle Henry and Aunt Em's big bed in the north-west corner
bed("BigBed", -HX + 0.03, -HX + 1.45, 0.05, HY - 0.03, +1, 1.15, 0.72, M_BEDWOOD, pillows=2)
# Dorothy's little bed in the south-east corner (an iron cot, head to the south wall)
bed("LittleBed", HX - 0.82, HX - 0.03, -HY + 0.03, -HY + 1.65, -1, 0.95, 0.70, M_IRON, iron=True, pillows=1)

# a braided rag rug between the big bed and the stove
cyl("RagRug", 0.5, 0.01, (-1.25, -0.40, 0.005), M_RAGRUG, verts=32).scale = (1.15, 0.72, 1)

# by the door: a broom and a water bucket with a dipper
bx, by = -1.05, -HY + 0.08
cyl("Broom_Handle", 0.013, 1.25, (bx + 0.05, by + 0.04, 0.32 + 0.6), M_RAFTER, verts=8, rot=(math.radians(-6), math.radians(-4), 0))
cyl("Broom_Straw", 0.11, 0.36, (bx, by, 0.18), M_STRAW, verts=10, r2=0.04).scale = (1.0, 0.35, 1)
lathe("Bucket", [(0.0, 0.0), (0.13, 0.0), (0.155, 0.28), (0.15, 0.28), (0.125, 0.012), (0.0, 0.012)], (1.30, -HY + 0.22, 0), M_DOORPLANK, steps=16)
for k, z in enumerate([0.05, 0.24]):
    torus(f"BucketHoop{k}", 0.135 + z * 0.09, 0.006, (1.30, -HY + 0.22, z), M_IRON, seg=16, rseg=4)
box("BucketBench", (0.46, 0.34, 0.035), (1.30, -HY + 0.22, -0.0), M_DOORPLANK)
# pegs on the east wall with a shawl hung up, a calendar-less wall, a shelf with a clock above the table
for k in range(3):
    cyl(f"Peg{k}", 0.012, 0.10, (HX - 0.05, -0.55 + k * 0.2, 1.65), M_RAFTER, verts=6, rot=(0, math.radians(90), 0))
box("Shawl", (0.02, 0.32, 0.55), (HX - 0.06, -0.35, 1.38), M_CALICO, bevel=0.006)
box("WallShelf", (0.55, 0.16, 0.025), (-0.50, HY - 0.08, 1.70), M_CUPBOARD, bevel=0.004)
for s in (-1, 1):
    box(f"WallShelfBracket{s}", (0.02, 0.12, 0.12), (-0.50 + s * 0.22, HY - 0.07, 1.63), M_CUPBOARD)
box("Clock_Case", (0.20, 0.09, 0.30), (-0.62, HY - 0.08, 1.865), M_BEDWOOD, bevel=0.01)
cyl("Clock_Face", 0.07, 0.006, (-0.62, HY - 0.126, 1.90), M_CROCK, verts=16, rot=(math.radians(90), 0, 0))
lathe("ShelfJar", [(0.0, 1.71), (0.045, 1.71), (0.05, 1.80), (0.035, 1.84), (0.0, 1.845)], (-0.36, HY - 0.08, 0), M_ENAMEL, steps=12)

# ----------------------------------------------------------------------------- outside: the gray prairie to the edge of the sky
def disc_ring(name, r0, r1, rings, seg, mat, z, uv_scale=None):
    """A flat disc (r0 = 0) or annulus at height z, with planar UVs (x, y) / uv_scale when given."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    radii = [r0 + (r1 - r0) * (j / rings) ** 1.5 for j in range(rings + 1)]
    allr = []
    centre = None
    for j, rr in enumerate(radii):
        if rr < 1e-6: centre = bm.verts.new((0, 0, z)); allr.append(None); continue
        allr.append([bm.verts.new((rr * math.cos(2 * math.pi * i / seg), rr * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
    for j in range(len(allr) - 1):
        a, b_ = allr[j], allr[j + 1]
        for i in range(seg):
            k = (i + 1) % seg
            if a is None: bm.faces.new((centre, b_[i], b_[k]))
            else: bm.faces.new((a[i], a[k], b_[k], b_[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f_ in bm.faces:
        if f_.normal.z < 0: f_.normal_flip()
    if uv_scale:
        uvl = bm.loops.layers.uv.new("UVMap")
        for f_ in bm.faces:
            for l in f_.loops: l[uvl].uv = (l.vert.co.x / uv_scale + 0.5, l.vert.co.y / uv_scale + 0.5)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

disc_ring("Ground", 0.0, NEAR_R, 12, 48, M_GROUND, GZ)
disc_ring("far.prairie", NEAR_R, SKY_R + 1.0, 10, 48, M_FAR, GZ, uv_scale=2 * (SKY_R + 1.0))

# long gray grass round the house, bowing to the south before the north wind
def grass_tufts(name, n_clumps, rmin_house=0.7, rmax=NEAR_R - 0.3):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rnd = random.Random(7)
    wind = Vector((0.15, -1.0, 0)).normalized()
    placed = 0; tries = 0
    while placed < n_clumps and tries < n_clumps * 20:
        tries += 1
        x, y = rnd.uniform(-rmax, rmax), rnd.uniform(-rmax, rmax)
        if math.hypot(x, y) > rmax: continue
        dx = max(0.0, abs(x) - HX - T); dy = max(0.0, abs(y) - HY - T)
        dh = math.hypot(dx, dy)
        if dh < rmin_house: continue
        # the trodden yard in front of the door: thin grass there
        if y < -HY and abs(x - DOOR_X) < 1.0 and y > -HY - 1.8 and rnd.random() < 0.85: continue
        if rnd.random() > min(1.0, 0.25 + dh / 4.0) * (1.0 if y < 0 else 0.55): continue
        placed += 1
        nb = rnd.randint(5, 7); hscale = rnd.uniform(0.6, 1.1) * min(1.0, 0.45 + dh / 3.5)
        for _ in range(nb):
            p = Vector((x + rnd.uniform(-0.14, 0.14), y + rnd.uniform(-0.14, 0.14), GZ - 0.01))
            h = rnd.uniform(0.4, 0.95) * hscale
            w = rnd.uniform(0.014, 0.024)
            bend = (wind * rnd.uniform(0.35, 0.8) + Vector((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 0))) * h
            side_a = rnd.uniform(0, math.pi); side = Vector((math.cos(side_a), math.sin(side_a), 0)) * w
            pts = []
            for k in range(4):
                t = k / 3
                c = p + Vector((0, 0, h * t * (1 - 0.25 * t * t))) + bend * t * t
                pts.append((c, (1 - t) * 1.0))
            vs = []
            for k, (c, wk) in enumerate(pts[:3]):
                vs.append((bm.verts.new(c - side * wk), bm.verts.new(c + side * wk)))
            tip = bm.verts.new(pts[3][0])
            for k in range(2):
                bm.faces.new((vs[k][0], vs[k][1], vs[k + 1][1], vs[k + 1][0]))
            bm.faces.new((vs[2][0], vs[2][1], tip))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_GRASS)
    print("grass clumps", placed)
    return link(o)
grass_tufts("PrairieGrass", 560)

# the sky dome: an inward-facing hemisphere (and a skirt below the horizon), with spherical UVs
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
            f_ = bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][k], grid[j][k]))      # inward winding
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
    # render: the dome is seen by the camera only; the world lights the scene
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
light_obj("light.sun", 'SUN', 0.7, (0.92, 0.93, 0.78), (-8, -4, 10), direction=-SUN_DIR, angle=math.radians(14))
sky_l = light_obj("light.sky", 'SUN', 0.25, (0.62, 0.72, 0.68), (0, 0, 14), direction=(0.05, 0.2, -1.0), angle=math.radians(70))
sky_l.data.use_shadow = False
light_obj("light.stove", 'POINT', 1.8, (1.0, 0.45, 0.15), (sx + SD / 2 + 0.28, sy - SW / 2 + 0.10, 0.48), shadow_soft_size=0.08)
light_obj("light.lamp", 'POINT', 28.0, (1.0, 0.70, 0.40), (LX, LY, LZ + 0.25), shadow_soft_size=0.03)

# world: the same storm gradient, render-only (Unity gets the SkyDome mesh)
world = bpy.data.worlds.new("Storm"); scene.world = world; world.use_nodes = True
wnt = world.node_tree; bg = wnt.nodes["Background"]
wtc = wnt.nodes.new("ShaderNodeTexCoord"); wsep = wnt.nodes.new("ShaderNodeSeparateXYZ"); wnt.links.new(wtc.outputs["Generated"], wsep.inputs["Vector"])
wmr = wnt.nodes.new("ShaderNodeMapRange"); wmr.inputs["From Min"].default_value = -0.12; wmr.inputs["From Max"].default_value = 1.0
wnt.links.new(wsep.outputs["Z"], wmr.inputs["Value"])
wr = ramp(wnt, [(0.0, (0.10, 0.10, 0.085, 1)), (0.10, (0.36, 0.39, 0.32, 1)), (0.16, (0.30, 0.33, 0.29, 1)), (0.4, (0.20, 0.23, 0.21, 1)), (1.0, (0.15, 0.17, 0.16, 1))])
wnt.links.new(wmr.outputs["Result"], wr.inputs["Fac"]); wnt.links.new(wr.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.9

# ----------------------------------------------------------------------------- anchors
anchor("reader.entrance", (READER[0], READER[1], 0.0))
look = anchor("reader.look", (DOOR_X, -HY - 0.05, 1.5))
anchor("scene.centre", (0.0, 0.0, 0.0))
anchor("cellar.trapdoor", (0.0, 0.0, 0.0))
anchor("room.door", (DOOR_X, -HY, 0.0))
anchor("room.stove", (STOVE[0] + SD / 2, STOVE[1], 0.0))
anchor("room.table", (tx, ty, TABLE_H))
anchor("room.bed.big", (-HX + 0.74, 1.0, 0.0))
anchor("room.bed.little", (HX - 0.42, -HY + 0.85, 0.0))
anchor("room.cupboard", (cbx, HY - LD, 0.0))
anchor("prairie.doorstep", (DOOR_X, -HY - T - 0.21, GZ + 0.14))

# apply every transform so object space == world space (the procedural materials then bake exactly as rendered)
bpy.ops.object.select_all(action='DESELECT')
for o in COLL.objects:
    if o.type == 'MESH': o.select_set(True); bpy.context.view_layer.objects.active = o
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.select_all(action='DESELECT')

# ----------------------------------------------------------------------------- cameras (reader eye 1.6 m)
def camera(name, loc, look_at, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 150
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co
cams = [
    camera("Cam_Reader", (READER[0], READER[1], 1.60), tuple(look.location), lens=16),
    camera("Cam_Room", (0.95, -1.55, 1.62), (-1.3, 1.3, 0.95), lens=15),
    camera("Cam_Stove", (-0.45, 0.05, 1.45), (-2.15, -1.35, 0.7), lens=22),
    camera("Cam_Cellar", (READER[0], READER[1], 1.60), (0.15, -0.35, 0.0), lens=18),
    camera("Cam_Outside", (5.0, -10.5, 1.6), (0.2, -1.0, 1.75), lens=24),
]

EXPOSURE = {"Cam_Reader": 1.45, "Cam_Room": 1.6, "Cam_Stove": 1.6, "Cam_Cellar": 1.5, "Cam_Outside": 0.55}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "kansas_farmhouse_source.blend"))

if args.render:
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    want = set(c.strip() for c in args.cams.split(",") if c.strip())
    for c in cams:
        if want and c.name[4:].lower() not in want: continue
        scene.camera = c
        scene.view_settings.exposure = EXPOSURE.get(c.name, 1.5)      # preview stills only: a dark room and the open prairie
        scene.render.filepath = os.path.join(OUT, f"render_{c.name[4:].lower()}.png")
        bpy.ops.render.render(write_still=True); print("rendered", scene.render.filepath)

# ----------------------------------------------------------------------------- bake + merge + export for Unity
def tri_count(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

KEEP_NAMES = {"M_SkyDome": "SkyDome", "M_DistantPrairie": "far.prairie"}    # backdrop meshes keep the names Unity looks for
KEEP_UV = {"SkyDome", "far.prairie"}                                       # their hand-made UVs (spherical / planar)

def bake_and_export():
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')                           # apply modifiers (bevels)
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
    scene.cycles.samples = 8
    scene.render.bake.margin = 6
    T_ = args.tex
    size_for = {"M_PrairieGround": min(4096, T_ * 2), "M_WallBoards": T_, "M_FloorPlanks": T_, "M_RoofBoards": T_ // 2, "M_SkyDome": T_,
                "M_DistantPrairie": T_ // 2, "M_Rafters": T_ // 2, "M_RustIron": T_ // 2, "M_Quilt": T_ // 2, "M_Cupboard": T_ // 2,
                "M_TrapDoor": T_ // 4, "M_TablePine": T_ // 4, "M_ChairWood": T_ // 4, "M_BedWood": T_ // 4, "M_Linen": T_ // 4,
                "M_DoorPlanks": T_ // 2, "M_WindowTrim": T_ // 4, "M_PrairieGrass": T_ // 4, "M_RagRug": T_ // 4}
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
        for pass_name, btype, extra, noncolor in passes:
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
        metallic = bsdf.inputs["Metallic"].default_value
        emis = bsdf.inputs["Emission Strength"].default_value; ecol = tuple(bsdf.inputs["Emission Color"].default_value)
        elinked = bsdf.inputs["Emission Color"].is_linked
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
        if emis > 0:
            nb.inputs["Emission Strength"].default_value = min(emis, 4.0)
            if elinked: nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"])
            else: nb.inputs["Emission Color"].default_value = ecol
    for c in cams: bpy.data.objects.remove(c)
    gl = os.path.join(OUT, "kansas_farmhouse.gltf")
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False)
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={tex_sizes.get(o.name, 0)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "kansas_farmhouse_baked.blend"))

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
