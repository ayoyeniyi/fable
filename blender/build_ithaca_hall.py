"""
Fable: the great hall (megaron) of Odysseus's house at Ithaca (The Odyssey, Books XVII-XXII, Samuel Butler's 1900
prose translation).

"Ulysses was left in the cloister, pondering on the means whereby with Minerva's help he might be able to kill the
suitors. Presently he said to Telemachus, 'Telemachus, we must get the armour together and take it down inside.
Make some excuse when the suitors ask you why you have removed it. Say that you have taken it to be out of the way
of the smoke, inasmuch as it is no longer what it was when Ulysses went away, but has become soiled and begrimed
with soot.'" (Book XIX)
"Then the other maids in the house rose and lit the fire on the hearth ... But Euryclea called the maids and said,
'Come, wake up; set about sweeping the cloisters and sprinkling them with water to lay the dust; put the covers on
the seats; wipe down the tables, some of you, with a wet sponge; clean out the mixing-jugs and the cups ... the
suitors will be here directly; they will be here early, for it is a feast day.'" (Book XX)

The moment: early on the winter morning of the feast day (Book XX), the morning after Telemachus and Ulysses carried
the armour down to the store-room. The suitors have not come yet. The maids have swept the floor and sprinkled it
(damp patches), put the purple covers on the seats, wiped the tables and set out the cups; the fire on the round
hearth is newly lit and still low. The walls are smoke-blackened, except for the pale, clean shapes where the
shields, helmets and spears hung for twenty years; their bronze pegs are empty, and so is the spear-stand by the
bearing-post. The low winter sun (south-east) comes through the porch and the open doors across the high threshold
of ash-wood, and cool sky light falls through the smoke-lantern over the hearth. No people or animals are modelled.

Also here: the four bearing-posts of cypress round the hearth, the raised smoke-lantern with its opening, the
tables and seats along the walls, Penelope's chair inlaid with ivory and silver by the fire with its fleece and
footstool, the bronze mixing-bowl near the door that leads into the house (the way to the store-room: oak threshold,
double doors fastened with a strap), the stair up to Penelope's upper room, two cold braziers, a water jar and broom,
the minstrel's lyre on its peg; outside, the porch (where Ulysses slept on an undressed hide and fleeces), the
court with the altar of Jove, its walls and gate, and the hills of Ithaca.

Everything is procedural (no downloaded models, textures or HDRIs) with PBR node materials. By flag the script
renders Cycles stills, bakes materials to textures, merges static meshes by material and exports .gltf + .bin +
textures/ for Unity.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet (floor, z=0), in the south-east of the hall, inside the doors
  anchor.reader.look      eye height (1.55 m), 1 m along the facing direction (north, up the hall)
  anchor.scene.centre     the hearth centre on the floor
  anchor.hall.hearth / hall.door / hall.storeroomDoor / hall.stair / hall.mixingBowl / court.altar
  light.sun (SUN, low winter sun from the south-east), light.sky (SUN, cool shadowless fill, as Unity bakes it),
  light.hearthFire (POINT: FableBuild's outdoor block gives names containing "Fire" a warm baked light)
  SkyDome (unlit backdrop, baked base texture), far.hills (backdrop ridge beyond the court wall)
  MESH_Flame (the flames: no shadows / not lightmapped in Unity)

Register the scene as Outdoor (sky shows through the smoke-lantern and the doorway, and the sun is a directional
light); FableBuild's indoor block would zero every light whose name does not start with "Lamp".

Axes: metres, Blender +Z up. The hall interior spans x -5..5, y -6..6; the doors are in the south wall (-y), the
hearth is at (0, 0.6). The reader faces +y (Unity +Z after glTFast's axis change is -Blender Y; FableBuild uses the
anchors, not the axis). The page volume (0.6 m ahead, 0.4 x 0.55 m at eye height) is kept clear and the fire is
well to its left.

Run headless:
  blender -b -P blender/build_ithaca_hall.py -- --out out/ithaca-hall --render --quick --res 900
  blender -b -P blender/build_ithaca_hall.py -- --out out/ithaca-hall --render --samples 96 --res 1400
  blender -b -P blender/build_ithaca_hall.py -- --out out/ithaca-hall --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, noise

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/ithaca-hall")
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
random.seed(1184)

# ----------------------------------------------------------------------------- dimensions (metres)
HX, HY = 5.0, 6.0                     # hall interior half-sizes (10 m across, 12 m deep)
WT = 0.7                              # wall thickness (rubble and mud brick, plastered)
CEIL = 5.2                            # underside of the main beams' top / joist seat
ROOF_TOP = 5.95
HEARTH = Vector((0.0, 0.6, 0.0))
HR_OUT, HR_IN, HR_H = 1.62, 1.22, 0.22   # hearth rim: outer radius, inner radius, height
COL = 2.15                            # column offset from the hearth (x and y)
COLS = [Vector((sx * COL, HEARTH.y + sy * COL, 0)) for sx in (-1, 1) for sy in (-1, 1)]
LAN_Z0 = CEIL                         # smoke-lantern: its sill stands on the main beams
VENT0, VENT1 = ROOF_TOP + 0.1, ROOF_TOP + 0.72   # the open smoke vents round its sides, above the roof
LAN_Z1 = VENT1 + 0.3                  # underside of the lantern roof
HOLE = 0.65                           # half-size of the smoke opening in the lantern roof
DOOR_W, DOOR_H = 2.1, 3.3             # the great doors (south wall, x = 0)
THR_H = 0.26                          # the high threshold of ash-wood
IDOOR_X, IDOOR_W, IDOOR_H = 2.7, 1.3, 2.55   # the door that leads into the house (north wall)
STAIR_X0, STAIR_X1 = -5.0, -3.95      # the stair to the upper room, along the west wall
STAIR_Y0, STAIR_Y1, STAIR_TOP = -0.2, 4.6, 3.0
UDOOR_X = -4.47                       # the upper-room door on the landing (north wall)
PORCH_Y1 = -9.6                       # porch front (the hall's south wall outer face is at -HY - WT)
COURT_Y1, COURT_X = -21.0, 8.0        # the court: south wall inner face, half width
CZ = -0.30                            # court ground level (the porch stands one step up)
READER = Vector((3.3, -3.7, 0.0))
FACE = Vector((2.9, 6.0, 0.0))       # the reader looks up the hall towards this floor point
EYE = 1.55
SKY_R = 62.0
# towards the sun: low in the south-east on a winter morning (azimuth 138 deg from north, 22 deg up)
_az, _el = math.radians(138.0), math.radians(22.0)
SUN_DIR = Vector((math.cos(_el) * math.sin(_az), math.cos(_el) * math.cos(_az), math.sin(_el))).normalized()

# ----------------------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24 if args.quick else args.samples
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.diffuse_bounces = 5
scene.cycles.transmission_bounces = 4
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
scene.cycles.sample_clamp_indirect = 8.0
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'; prefs.get_devices()
    for d in prefs.devices: d.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print("Metal not available, CPU render:", e)
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 1.0

COLL = bpy.data.collections.new("IthacaHall")
scene.collection.children.link(COLL)
def link(obj):
    COLL.objects.link(obj); return obj

# ----------------------------------------------------------------------------- material helpers (from build_lobby.py / build_kansas_farmhouse.py)
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

def mix_f(nt, fac, a, b, loc=(0, 0)):
    n = node(nt, "ShaderNodeMix", loc, data_type='FLOAT')
    for sock, v in ((n.inputs[0], fac), (n.inputs[2], a), (n.inputs[3], b)):
        if isinstance(v, (int, float)): sock.default_value = v
        else: nt.links.new(v, sock)
    return n.outputs[0]

def maprange(nt, val, f0, f1, t0, t1, loc=(0, 0), interp='LINEAR'):
    n = node(nt, "ShaderNodeMapRange", loc, interpolation_type=interp)
    n.inputs["From Min"].default_value = f0; n.inputs["From Max"].default_value = f1
    n.inputs["To Min"].default_value = t0; n.inputs["To Max"].default_value = t1
    nt.links.new(val, n.inputs["Value"])
    return n.outputs["Result"]

def noise_(nt, vec, scale, detail=6.0, rough=0.6, distortion=0.0, loc=(0, 0)):
    n = node(nt, "ShaderNodeTexNoise", loc); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough; n.inputs["Distortion"].default_value = distortion
    nt.links.new(vec, n.inputs["Vector"])
    return n

def bump_from(nt, b, height_socket, strength, distance):
    bump = node(nt, "ShaderNodeBump", (50, -300)); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return bump

def c4(c): return (c[0], c[1], c[2], 1)

def soot_by_height(nt, col, zsock, z0, z1, amount, soot_col=(0.055, 0.047, 0.04), loc=(0, 0)):
    """Smoke-blackening that thickens towards the roof: lerp to soot between z0 and z1, up to `amount`."""
    f = maprange(nt, zsock, z0, z1, 0.0, amount, loc, interp='SMOOTHSTEP')
    return mix_rgb(nt, 'MIX', f, col, c4(soot_col), (loc[0] + 200, loc[1]))

def wood(name, base=(0.32, 0.17, 0.08), dark=(0.09, 0.045, 0.02), light=(0.55, 0.33, 0.15), scale=1.0, rough=(0.45, 0.75),
         grain_dir=(1, 1, 14), bands='Z', coat=0.0, soot=None, wear=None):
    """Wood grain (from build_kansas_farmhouse.py), with optional height soot (z0, z1, amount) and a hand-polished
    band (z0, z1) where people lean and touch."""
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
    col = mix_rgb(nt, 'MULTIPLY', 0.3, r.outputs["Color"], ao.outputs["Color"], (50, 100))
    tc = node(nt, "ShaderNodeTexCoord", (-1400, -700)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1200, -700))
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    rr = node(nt, "ShaderNodeMapRange", (-150, -200))
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough[1], rough[0]
    nt.links.new(wave.outputs["Fac"], rr.inputs["Value"])
    rough_s = rr.outputs["Result"]
    if wear:
        wz = maprange(nt, sep.outputs["Z"], wear[0], wear[1], 0.0, 1.0, (-900, -900))
        wz2 = maprange(nt, sep.outputs["Z"], wear[1], wear[1] + 0.25, 1.0, 0.0, (-900, -1050))
        wm = math_(nt, 'MULTIPLY', wz, wz2, (-700, -950))
        col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', wm, 0.35, (-550, -950)), col, (0.55, 0.5, 0.45, 1), (150, 50))
        rough_s = math_(nt, 'SUBTRACT', rough_s, math_(nt, 'MULTIPLY', wm, 0.2, (-400, -1000)), (0, -250))
    if soot:
        col = soot_by_height(nt, col, sep.outputs["Z"], soot[0], soot[1], soot[2], loc=(200, 150))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(rough_s, b.inputs["Roughness"])
    bump_from(nt, b, mix.outputs[0], 0.35, 0.003)
    b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.3
    return m

def boards(name, light, dark, axis='Z', width=0.15, grain=(1.2, 1.2, 28), dirt=0.0, rough=0.85, seam=0.85, soot=None):
    """Planks (from build_kansas_farmhouse.py): each board its own tone, dark seams, grain, dirt rising from the floor."""
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
    if dirt > 0:
        zr = maprange(nt, sep.outputs["Z"], 0.0, 0.7, 1.0 - dirt, 1.0, (-1000, 650))
        col = mix_rgb(nt, 'MULTIPLY', 1.0, col, zr, (-250, 0))
    col = mix_rgb(nt, 'MULTIPLY', seam, col, seamr.outputs["Color"], (-100, 0))
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-400, -550)); ao.inputs["Distance"].default_value = 0.15
    col = mix_rgb(nt, 'MULTIPLY', 0.35, col, ao.outputs["Color"], (100, 0))
    if soot: col = soot_by_height(nt, col, sep.outputs["Z"], soot[0], soot[1], soot[2], loc=(200, 100))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    h = mix_rgb(nt, 'MULTIPLY', 1.0, seamr.outputs["Color"], gr.outputs["Color"], (-200, -300))
    bump_from(nt, b, h, 0.45, 0.003)
    return m

def noisy(name, colors, scale=8.0, rough=0.8, bump=0.2, bump_dist=0.003, detail=6.0, stretch=(1, 1, 1), sheen=0.0, metallic=0.0, warp=0.0, coat=0.0, soot=None):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt); mp.inputs["Scale"].default_value = stretch
    n = node(nt, "ShaderNodeTexNoise", (-1000, 0)); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = 0.6
    n.inputs["Distortion"].default_value = warp
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    stops = [(i / max(1, len(colors) - 1) * 0.6 + 0.2, c4(c)) for i, c in enumerate(colors)]
    r = ramp(nt, stops, (-700, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    col = r.outputs["Color"]
    if soot:
        tc = node(nt, "ShaderNodeTexCoord", (-1400, -700)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1200, -700))
        nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
        col = soot_by_height(nt, col, sep.outputs["Z"], soot[0], soot[1], soot[2], loc=(-300, 150))
    nt.links.new(col, b.inputs["Base Color"])
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

# ----------------------------------------------------------------------------- the armour that hung on the walls (now in the store-room)
# (wall, kind, u, z, half-width, half-height): wall 'E'/'W' are the side walls (u = y), 'N' the end wall (u = x).
# Each leaves a clean, pale shape in the soot and an empty bronze peg (or two, for spears).
ARMOUR = [
    ('E', 'shield', -4.75, 2.55, 0.46, 0.46), ('E', 'helmet', -4.75, 3.42, 0.16, 0.20),
    ('E', 'spear', -3.05, 1.92, 1.22, 0.030), ('E', 'spear', -3.0, 2.06, 1.18, 0.030),
    ('E', 'shield', -1.35, 2.62, 0.40, 0.40), ('E', 'helmet', -1.35, 3.35, 0.15, 0.19),
    ('E', 'shield', 2.15, 2.58, 0.50, 0.50),
    ('E', 'spear', 3.75, 1.95, 1.15, 0.030), ('E', 'sword', 3.8, 2.75, 0.45, 0.05),
    ('E', 'shield', 5.05, 2.5, 0.42, 0.42), ('E', 'helmet', 5.05, 3.3, 0.15, 0.19),
    ('W', 'shield', -4.85, 2.6, 0.44, 0.44), ('W', 'helmet', -4.85, 3.45, 0.16, 0.20),
    ('W', 'spear', -3.15, 1.96, 1.2, 0.030), ('W', 'spear', -3.2, 2.09, 1.24, 0.030),
    ('W', 'shield', -1.55, 2.55, 0.47, 0.47), ('W', 'helmet', -1.55, 3.42, 0.15, 0.19),
    ('N', 'shield', -2.35, 2.7, 0.43, 0.43), ('N', 'helmet', -2.35, 3.5, 0.15, 0.19),
    ('N', 'shield', -0.9, 2.75, 0.40, 0.40),
]

def armour_ghost_mask(nt, pos, loc=(-1600, -1600)):
    """1 inside the pale shapes left on the soot where the armour hung (soft edged), 0 elsewhere."""
    sep = node(nt, "ShaderNodeSeparateXYZ", loc); nt.links.new(pos, sep.inputs["Vector"])
    side = {
        'E': maprange(nt, sep.outputs["X"], HX - 0.15, HX - 0.05, 0.0, 1.0, (loc[0] + 200, loc[1] + 200)),
        'W': maprange(nt, sep.outputs["X"], -HX + 0.15, -HX + 0.05, 0.0, 1.0, (loc[0] + 200, loc[1] + 100)),
        'N': maprange(nt, sep.outputs["Y"], HY - 0.15, HY - 0.05, 0.0, 1.0, (loc[0] + 200, loc[1])),
    }
    acc = None
    for i, (wall, kind, u, z, ru, rz) in enumerate(ARMOUR):
        y0 = loc[1] - 150 - i * 120
        ucoord = sep.outputs["X"] if wall == 'N' else sep.outputs["Y"]
        du = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', ucoord, u, (loc[0] + 300, y0)), ru, (loc[0] + 450, y0))
        dz = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', sep.outputs["Z"], z, (loc[0] + 300, y0 - 60)), rz, (loc[0] + 450, y0 - 60))
        if kind in ('spear', 'sword'):
            # a long thin shape: a stadium (the spear shaft), with the blade end a little wider
            d = math_(nt, 'MAXIMUM', math_(nt, 'ABSOLUTE', du, None, (loc[0] + 600, y0)), math_(nt, 'ABSOLUTE', dz, None, (loc[0] + 600, y0 - 60)), (loc[0] + 750, y0))
            soft = 1.2
        else:
            d = math_(nt, 'SQRT', math_(nt, 'ADD', math_(nt, 'MULTIPLY', du, du, (loc[0] + 600, y0)), math_(nt, 'MULTIPLY', dz, dz, (loc[0] + 600, y0 - 60)), (loc[0] + 700, y0)), None, (loc[0] + 800, y0))
            soft = 0.05 / ru
        mk = maprange(nt, d, 1.0 - soft * 0.5, 1.0 + soft * 0.5, 1.0, 0.0, (loc[0] + 900, y0))
        mk = math_(nt, 'MULTIPLY', mk, side[wall] if kind not in ('spear', 'sword') else math_(nt, 'MULTIPLY', side[wall], 0.45, (loc[0] + 950, y0 - 60)), (loc[0] + 1050, y0))
        acc = mk if acc is None else math_(nt, 'MAXIMUM', acc, mk, (loc[0] + 1200, y0))
    return acc

# ----------------------------------------------------------------------------- materials
def wall_plaster_mat(name="M_WallPlaster"):
    """Lime plaster over mud brick: a worn red dado with a dark stripe, trowel marks and fine cracks, smoke-blackened
    upwards (streaked), except where the armour hung; damp and dust at the foot of the wall."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-2200, 0)); pos = tc.outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ", (-2000, 300)); nt.links.new(pos, sep.inputs["Vector"])
    z = sep.outputs["Z"]
    mott = noise_(nt, pos, 1.6, 8, 0.6, 0.0, (-1700, 300))
    plaster = ramp(nt, [(0.30, c4((0.52, 0.50, 0.45))), (0.5, c4((0.61, 0.59, 0.53))), (0.72, c4((0.67, 0.65, 0.59)))], (-1450, 300))
    nt.links.new(mott.outputs["Fac"], plaster.inputs["Fac"])
    trow_mp = texcoord_obj(nt, (-2200, -300)); trow_mp.inputs["Scale"].default_value = (2.5, 2.5, 7.0)
    trow = noise_(nt, trow_mp.outputs["Vector"], 2.2, 4, 0.5, 1.2, (-1700, -300))
    col = mix_rgb(nt, 'MULTIPLY', 0.18, plaster.outputs["Color"], trow.outputs["Color"], (-1200, 300))
    # the dado: red-brown, worn and chipped, a dark stripe above it
    chip = noise_(nt, pos, 9.0, 6, 0.7, 0.0, (-1700, 650))
    chipm = maprange(nt, chip.outputs["Fac"], 0.62, 0.68, 0.0, 1.0, (-1450, 650))
    dado = maprange(nt, z, 0.94, 0.955, 1.0, 0.0, (-1450, 800))
    dmott = ramp(nt, [(0.3, c4((0.30, 0.105, 0.055))), (0.7, c4((0.40, 0.16, 0.08)))], (-1250, 700)); nt.links.new(mott.outputs["Fac"], dmott.inputs["Fac"])
    dadoc = mix_rgb(nt, 'MIX', chipm, dmott.outputs["Color"], col, (-1050, 700))
    col = mix_rgb(nt, 'MIX', dado, col, dadoc, (-900, 400))
    s1 = maprange(nt, z, 0.975, 0.985, 0.0, 1.0, (-1450, 950)); s2 = maprange(nt, z, 1.045, 1.055, 1.0, 0.0, (-1450, 1050))
    stripe = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', s1, s2, (-1250, 1000)), math_(nt, 'SUBTRACT', 1.0, math_(nt, 'MULTIPLY', chipm, 0.7, (-1250, 1100)), (-1100, 1100)), (-1000, 1000))
    col = mix_rgb(nt, 'MIX', stripe, col, c4((0.06, 0.065, 0.075)), (-750, 400))
    # cracks
    vor = node(nt, "ShaderNodeTexVoronoi", (-1700, -650), feature='DISTANCE_TO_EDGE'); vor.inputs["Scale"].default_value = 1.4
    wob = noise_(nt, pos, 3.0, 3, 0.5, 0.0, (-1900, -700))
    wv = node(nt, "ShaderNodeMix", (-1800, -650), data_type='VECTOR'); wv.inputs["Factor"].default_value = 0.12
    nt.links.new(pos, wv.inputs[4]); nt.links.new(wob.outputs["Color"], wv.inputs[5]); nt.links.new(wv.outputs[1], vor.inputs["Vector"])
    crn = noise_(nt, pos, 2.0, 2, 0.5, 0.0, (-1700, -850))
    crack = maprange(nt, vor.outputs["Distance"], 0.0, 0.006, 1.0, 0.0, (-1450, -650))
    crack = math_(nt, 'MULTIPLY', crack, maprange(nt, crn.outputs["Fac"], 0.5, 0.6, 0.0, 1.0, (-1450, -850)), (-1250, -700))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', crack, 0.2, (-1100, -700)), col, c4((0.55, 0.52, 0.48)), (-600, 400))
    # soot: thickening upwards, streaked by the rising smoke, less where the armour hung
    st_mp = texcoord_obj(nt, (-2200, -1100)); st_mp.inputs["Scale"].default_value = (2.2, 2.2, 0.55)
    streak = noise_(nt, st_mp.outputs["Vector"], 1.5, 5, 0.6, 0.0, (-1700, -1100))
    sootz = maprange(nt, z, 0.5, 4.6, 0.0, 0.93, (-1450, -1000), interp='SMOOTHSTEP')
    sootv = math_(nt, 'MULTIPLY', sootz, maprange(nt, streak.outputs["Fac"], 0.25, 0.75, 0.82, 1.08, (-1450, -1150)), (-1250, -1050))
    ghost = armour_ghost_mask(nt, pos, (-3200, -1400))
    sootv = math_(nt, 'MULTIPLY', sootv, math_(nt, 'SUBTRACT', 1.0, math_(nt, 'MULTIPLY', ghost, 0.74, (-1250, -1300)), (-1100, -1300)), (-950, -1100))
    sootv = math_(nt, 'MINIMUM', sootv, 0.94, (-850, -1100))
    soot_tone = ramp(nt, [(0.3, c4((0.040, 0.034, 0.029))), (0.7, c4((0.085, 0.072, 0.060)))], (-900, -900)); nt.links.new(mott.outputs["Fac"], soot_tone.inputs["Fac"])
    col = mix_rgb(nt, 'MIX', sootv, col, soot_tone.outputs["Color"], (-450, 400))
    # the floor line: dust and damp from the sprinkling, darker towards the foot of the wall
    foot = maprange(nt, z, 0.0, 0.22, 1.0, 0.0, (-1450, 1250), interp='SMOOTHSTEP')
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', foot, 0.35, (-1250, 1250)), col, c4((0.55, 0.47, 0.38)), (-300, 400))
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-500, -500)); ao.inputs["Distance"].default_value = 0.25
    col = mix_rgb(nt, 'MULTIPLY', 0.3, col, ao.outputs["Color"], (-150, 400))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, sootv, 0.0, 0.8, 0.88, 0.7, (-200, -200)), b.inputs["Roughness"])
    h = mix_f(nt, 0.6, trow.outputs["Fac"], math_(nt, 'SUBTRACT', 1.0, crack, (-500, -700)), (-300, -600))
    bump_from(nt, b, h, 0.25, 0.004)
    return m

def floor_mat(name="M_Floor"):
    """The hall floor: lime plaster laid in squares with incised, red-painted joints (faded, a few squares tinted),
    worn smooth on the way from the doors to the hearth, ash scuffed round the hearth, dust at the walls, and the
    morning's sprinkling still dark and damp in patches."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-2400, 0)); pos = tc.outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ", (-2200, 300)); nt.links.new(pos, sep.inputs["Vector"])
    x, y = sep.outputs["X"], sep.outputs["Y"]
    CELL = 1.0
    gx = math_(nt, 'DIVIDE', math_(nt, 'ADD', x, HX, (-2000, 500)), CELL, (-1850, 500)); gy = math_(nt, 'DIVIDE', math_(nt, 'ADD', y, HY, (-2000, 400)), CELL, (-1850, 400))
    cxy = node(nt, "ShaderNodeCombineXYZ", (-1650, 450)); nt.links.new(math_(nt, 'FLOOR', gx, None, (-1750, 520)), cxy.inputs["X"]); nt.links.new(math_(nt, 'FLOOR', gy, None, (-1750, 420)), cxy.inputs["Y"])
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1450, 450), noise_dimensions='3D'); nt.links.new(cxy.outputs[0], wn.inputs["Vector"])
    pal = ramp(nt, [(0.0, c4((0.57, 0.51, 0.41))), (0.4, c4((0.60, 0.54, 0.44))), (0.75, c4((0.58, 0.49, 0.37))), (0.88, c4((0.55, 0.43, 0.33))), (0.95, c4((0.52, 0.50, 0.45)))], (-1250, 450), interp='CONSTANT')
    nt.links.new(wn.outputs["Value"], pal.inputs["Fac"])
    mott = noise_(nt, pos, 0.9, 10, 0.66, 0.3, (-1700, 100))
    mr = ramp(nt, [(0.25, c4((0.70, 0.67, 0.62))), (0.5, c4((0.95, 0.94, 0.92))), (0.75, c4((1.08, 1.06, 1.02)))], (-1450, 100)); nt.links.new(mott.outputs["Fac"], mr.inputs["Fac"])
    col = mix_rgb(nt, 'MULTIPLY', 1.0, pal.outputs["Color"], mr.outputs["Color"], (-1050, 300))
    fine = noise_(nt, pos, 40.0, 5, 0.6, 0.0, (-1700, -100))
    col = mix_rgb(nt, 'MULTIPLY', 0.15, col, fine.outputs["Color"], (-900, 300))
    # joints: distance to the cell edge (wobbly), worn away in places
    fxn = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', gx, None, (-1750, 700)), 0.5, (-1600, 700)), None, (-1450, 700))
    fyn = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', gy, None, (-1750, 800)), 0.5, (-1600, 800)), None, (-1450, 800))
    jw = noise_(nt, pos, 3.0, 3, 0.5, 0.0, (-1700, 950))
    jd = math_(nt, 'ADD', math_(nt, 'MAXIMUM', fxn, fyn, (-1300, 750)), math_(nt, 'MULTIPLY', jw.outputs["Fac"], 0.018, (-1450, 950)), (-1150, 750))
    joint = maprange(nt, jd, 0.4995, 0.5035, 0.0, 0.55, (-1000, 750))
    jwear = maprange(nt, noise_(nt, pos, 6.0, 4, 0.6, 0.0, (-1300, 1050)).outputs["Fac"], 0.42, 0.58, 0.25, 1.0, (-1000, 1000))
    joint = math_(nt, 'MULTIPLY', joint, jwear, (-850, 850))
    col = mix_rgb(nt, 'MIX', joint, col, c4((0.33, 0.17, 0.11)), (-750, 300))
    # the worn track: doors -> hearth -> seats, smoother and paler
    trk = math_(nt, 'ABSOLUTE', x, None, (-1700, -400))
    trk = maprange(nt, trk, 0.6, 1.8, 1.0, 0.0, (-1500, -400), interp='SMOOTHSTEP')
    trk = math_(nt, 'MULTIPLY', trk, maprange(nt, y, -1.0, 0.0, 1.0, 0.0, (-1500, -500)), (-1300, -450))
    hdist = node(nt, "ShaderNodeVectorMath", (-1900, -700), operation='DISTANCE'); hdist.inputs[1].default_value = (HEARTH.x, HEARTH.y, 0.0)
    nt.links.new(pos, hdist.inputs[0])
    ring = maprange(nt, hdist.outputs["Value"], HR_OUT, HR_OUT + 1.2, 1.0, 0.0, (-1600, -700), interp='SMOOTHSTEP')
    wear = math_(nt, 'MAXIMUM', trk, math_(nt, 'MULTIPLY', ring, 0.7, (-1400, -700)), (-1150, -550))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', wear, 0.25, (-1000, -550)), col, c4((0.66, 0.61, 0.52)), (-600, 300))
    # ash and soot scuffed round the hearth
    ashn = noise_(nt, pos, 7.0, 6, 0.7, 0.0, (-1700, -950))
    ash = math_(nt, 'MULTIPLY', maprange(nt, hdist.outputs["Value"], HR_OUT, HR_OUT + 1.0, 0.75, 0.0, (-1500, -900)),
                maprange(nt, ashn.outputs["Fac"], 0.4, 0.65, 0.0, 1.0, (-1500, -1000)), (-1300, -950))
    col = mix_rgb(nt, 'MIX', ash, col, c4((0.26, 0.245, 0.23)), (-450, 300))
    # dust at the walls (the sweepings left along the foot of the wall)
    ex = math_(nt, 'SUBTRACT', HX, math_(nt, 'ABSOLUTE', x, None, (-1900, -1250)), (-1750, -1250))
    ey = math_(nt, 'SUBTRACT', HY, math_(nt, 'ABSOLUTE', y, None, (-1900, -1350)), (-1750, -1350))
    edge = maprange(nt, math_(nt, 'MINIMUM', ex, ey, (-1600, -1300)), 0.02, 0.45, 1.0, 0.0, (-1450, -1300), interp='SMOOTHSTEP')
    dn = noise_(nt, pos, 4.0, 5, 0.6, 0.0, (-1700, -1500))
    dust = math_(nt, 'MULTIPLY', edge, maprange(nt, dn.outputs["Fac"], 0.35, 0.6, 0.3, 1.0, (-1450, -1500)), (-1250, -1350))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', dust, 0.6, (-1100, -1350)), col, c4((0.46, 0.42, 0.36)), (-300, 300))
    # the sprinkling: water flung from a bowl in arcs, drying from the edges; darker and less rough while damp
    sp_mp = texcoord_obj(nt, (-2400, -1800)); sp_mp.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    sp = noise_(nt, sp_mp.outputs["Vector"], 0.9, 4, 0.55, 1.4, (-1900, -1800))
    spf = noise_(nt, pos, 14.0, 3, 0.6, 0.0, (-1900, -2000))
    damp = maprange(nt, math_(nt, 'ADD', sp.outputs["Fac"], math_(nt, 'MULTIPLY', spf.outputs["Fac"], 0.14, (-1700, -2000)), (-1550, -1850)), 0.56, 0.64, 0.0, 1.0, (-1400, -1850))
    damp = math_(nt, 'MULTIPLY', damp, math_(nt, 'SUBTRACT', 1.0, ring, (-1400, -2000)), (-1200, -1900))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', damp, 0.42, (-1050, -1900)), col, c4((0.62, 0.58, 0.52)), (-150, 300))
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-500, -500)); ao.inputs["Distance"].default_value = 0.3
    col = mix_rgb(nt, 'MULTIPLY', 0.35, col, ao.outputs["Color"], (0, 300))
    nt.links.new(col, b.inputs["Base Color"])
    rough = math_(nt, 'SUBTRACT', 0.86, math_(nt, 'ADD', math_(nt, 'MULTIPLY', wear, 0.22, (-800, -700)), math_(nt, 'MULTIPLY', damp, 0.34, (-800, -800)), (-650, -750)), (-500, -750))
    nt.links.new(rough, b.inputs["Roughness"])
    h = mix_f(nt, 0.5, math_(nt, 'SUBTRACT', 1.0, joint, (-600, -1000)), fine.outputs["Fac"], (-300, -900))
    bump_from(nt, b, h, 0.3, 0.003)
    return m

def hearth_mat(name="M_HearthRim"):
    """The round hearth's clay rim, plastered and painted (a running flame pattern round the side between dark
    bands), cracked by the heat and blackened towards the fire."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-2000, 0)); pos = tc.outputs["Object"]
    rel = node(nt, "ShaderNodeVectorMath", (-1800, 0), operation='SUBTRACT'); rel.inputs[1].default_value = (HEARTH.x, HEARTH.y, 0)
    nt.links.new(pos, rel.inputs[0])
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1600, 0)); nt.links.new(rel.outputs[0], sep.inputs["Vector"])
    ang = math_(nt, 'ARCTAN2', sep.outputs["Y"], sep.outputs["X"], (-1400, 200))
    t = math_(nt, 'FRACT', math_(nt, 'MULTIPLY', ang, 44 / (2 * math.pi), (-1250, 200)), None, (-1100, 200))
    tri = math_(nt, 'MULTIPLY', math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', t, 0.5, (-950, 200)), None, (-800, 200)), 2.0, (-650, 200))
    zr = math_(nt, 'DIVIDE', sep.outputs["Z"], HR_H, (-1400, 0))
    flame = math_(nt, 'LESS_THAN', zr, math_(nt, 'ADD', 0.22, math_(nt, 'MULTIPLY', tri, 0.55, (-650, 100)), (-500, 100)), (-350, 100))
    band_lo = math_(nt, 'LESS_THAN', zr, 0.12, (-500, -50)); band_hi = math_(nt, 'GREATER_THAN', zr, 0.86, (-500, -150))
    geo = node(nt, "ShaderNodeNewGeometry", (-1400, -400))
    gn = node(nt, "ShaderNodeSeparateXYZ", (-1200, -400)); nt.links.new(geo.outputs["Normal"], gn.inputs["Vector"])
    top = maprange(nt, gn.outputs["Z"], 0.5, 0.7, 0.0, 1.0, (-1000, -400))
    rlen = node(nt, "ShaderNodeVectorMath", (-1400, -650), operation='LENGTH'); nt.links.new(sep.outputs["X"], rlen.inputs[0])
    cmb = node(nt, "ShaderNodeCombineXYZ", (-1600, -650)); nt.links.new(sep.outputs["X"], cmb.inputs["X"]); nt.links.new(sep.outputs["Y"], cmb.inputs["Y"])
    rlen2 = node(nt, "ShaderNodeVectorMath", (-1400, -750), operation='LENGTH'); nt.links.new(cmb.outputs[0], rlen2.inputs[0])
    r = rlen2.outputs["Value"]
    mott = noise_(nt, pos, 6.0, 6, 0.6, 0.0, (-1400, 500))
    cream = ramp(nt, [(0.3, c4((0.52, 0.47, 0.38))), (0.7, c4((0.62, 0.57, 0.47)))], (-1200, 500)); nt.links.new(mott.outputs["Fac"], cream.inputs["Fac"])
    side_col = mix_rgb(nt, 'MIX', flame, cream.outputs["Color"], c4((0.42, 0.12, 0.06)), (-200, 300))
    side_col = mix_rgb(nt, 'MIX', math_(nt, 'MAXIMUM', band_lo, band_hi, (-350, -100)), side_col, c4((0.07, 0.06, 0.06)), (-50, 300))
    topband = math_(nt, 'MULTIPLY', maprange(nt, r, HR_IN + 0.04, HR_IN + 0.10, 1.0, 0.0, (-1000, -700)), 1.0, (-850, -700))
    top_col = mix_rgb(nt, 'MIX', topband, cream.outputs["Color"], c4((0.08, 0.06, 0.05)), (-200, 0))
    col = mix_rgb(nt, 'MIX', top, side_col, top_col, (100, 200))
    # chipped paint and heat cracks; soot towards the fire (inner edge) and on the top
    chip = noise_(nt, pos, 14.0, 6, 0.7, 0.0, (-1000, 700))
    chipm = maprange(nt, chip.outputs["Fac"], 0.6, 0.66, 0.0, 0.85, (-800, 700))
    col = mix_rgb(nt, 'MIX', chipm, col, c4((0.40, 0.34, 0.27)), (250, 200))
    sootr = maprange(nt, r, HR_IN - 0.05, HR_IN + 0.45, 0.92, 0.15, (-800, -900), interp='SMOOTHSTEP')
    sn = noise_(nt, pos, 3.0, 5, 0.6, 0.0, (-1000, -1100))
    sootr = math_(nt, 'MULTIPLY', sootr, maprange(nt, sn.outputs["Fac"], 0.3, 0.7, 0.6, 1.1, (-800, -1100)), (-600, -1000))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MINIMUM', sootr, 0.95, (-450, -1000)), col, c4((0.035, 0.03, 0.028)), (400, 200))
    vor = node(nt, "ShaderNodeTexVoronoi", (-1000, -1300), feature='DISTANCE_TO_EDGE'); vor.inputs["Scale"].default_value = 3.0
    nt.links.new(pos, vor.inputs["Vector"])
    crack = maprange(nt, vor.outputs["Distance"], 0.0, 0.01, 1.0, 0.0, (-800, -1300))
    crack = math_(nt, 'MULTIPLY', crack, maprange(nt, noise_(nt, pos, 2.5, 3, 0.5, 0.0, (-1000, -1500)).outputs["Fac"], 0.48, 0.6, 0.0, 1.0, (-800, -1500)), (-650, -1400))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', crack, 0.3, (-600, -1300)), col, c4((0.45, 0.42, 0.38)), (550, 200))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, math_(nt, 'SUBTRACT', 1.0, crack, (-400, -1300)), 0.4, 0.003)
    return m

def ash_mat(name="M_Ash"):
    """The ash bed: pale grey-white wood ash, darker and charcoal-flecked towards the fire."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0)); pos = tc.outputs["Object"]
    n = noise_(nt, pos, 5.0, 8, 0.65, 0.3, (-1300, 0))
    r = ramp(nt, [(0.3, c4((0.06, 0.057, 0.055))), (0.5, c4((0.15, 0.145, 0.14))), (0.72, c4((0.25, 0.24, 0.23)))], (-1050, 0)); nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    vor = node(nt, "ShaderNodeTexVoronoi", (-1300, -300)); vor.inputs["Scale"].default_value = 38.0; nt.links.new(pos, vor.inputs["Vector"])
    flk = maprange(nt, vor.outputs["Distance"], 0.0, 0.25, 1.0, 0.0, (-1050, -300))
    d = node(nt, "ShaderNodeVectorMath", (-1300, -550), operation='DISTANCE'); d.inputs[1].default_value = (HEARTH.x, HEARTH.y, 0.1); nt.links.new(pos, d.inputs[0])
    centre = maprange(nt, d.outputs["Value"], 0.3, 1.0, 1.0, 0.0, (-1050, -550))
    flk = math_(nt, 'MULTIPLY', flk, math_(nt, 'ADD', 0.25, centre, (-900, -450)), (-800, -350))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MINIMUM', flk, 1.0, (-700, -350)), r.outputs["Color"], c4((0.03, 0.028, 0.026)), (-500, 0))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', centre, 0.6, (-700, -600)), col, c4((0.35, 0.33, 0.31)), (-300, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.97
    bump_from(nt, b, n.outputs["Fac"], 0.8, 0.02)
    return m

def charwood_mat(name="M_Charwood"):
    """Split logs, charred black and crazed into checks where the fire has them, brown and barked at the cool ends."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0)); pos = tc.outputs["Object"]
    vor = node(nt, "ShaderNodeTexVoronoi", (-1300, 200), feature='DISTANCE_TO_EDGE'); vor.inputs["Scale"].default_value = 16.0; nt.links.new(pos, vor.inputs["Vector"])
    chk = maprange(nt, vor.outputs["Distance"], 0.0, 0.06, 0.0, 1.0, (-1050, 200))
    d = node(nt, "ShaderNodeVectorMath", (-1300, -100), operation='DISTANCE'); d.inputs[1].default_value = (HEARTH.x, HEARTH.y, 0.15); nt.links.new(pos, d.inputs[0])
    burnt = maprange(nt, d.outputs["Value"], 0.35, 0.8, 1.0, 0.0, (-1050, -100), interp='SMOOTHSTEP')
    n = noise_(nt, pos, 9.0, 6, 0.6, 0.0, (-1300, -350))
    bark = ramp(nt, [(0.3, c4((0.10, 0.07, 0.045))), (0.7, c4((0.24, 0.16, 0.09)))], (-1050, -350)); nt.links.new(n.outputs["Fac"], bark.inputs["Fac"])
    char = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, chk, (-900, 200)), 0.35, (-800, 200)), c4((0.035, 0.03, 0.027)), c4((0.20, 0.19, 0.18)), (-650, 150))
    col = mix_rgb(nt, 'MIX', burnt, bark.outputs["Color"], char, (-400, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.92
    bump_from(nt, b, chk, 0.6, 0.004)
    return m

def embers_mat(name="M_Embers"):
    """Glowing embers under the new fire: orange-red heat broken by grey crust (base colour drives the emission)."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1400, 0))
    n = noise_(nt, tc.outputs["Object"], 18.0, 6, 0.65, 0.4, (-1100, 0))
    r = ramp(nt, [(0.40, c4((0.025, 0.02, 0.018))), (0.52, c4((0.35, 0.05, 0.005))), (0.64, c4((0.85, 0.22, 0.02))), (0.78, c4((1.0, 0.48, 0.08)))], (-800, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"]); nt.links.new(r.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 3.0; b.inputs["Roughness"].default_value = 0.9
    return m

def bronze_mat(name="M_Bronze", soot=None):
    """Worked bronze, dulled and spotted with green-brown patina, brighter where hands rub it."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1400, 0)); pos = tc.outputs["Object"]
    n = noise_(nt, pos, 7.0, 8, 0.65, 0.5, (-1100, 0))
    r = ramp(nt, [(0.30, c4((0.26, 0.17, 0.08))), (0.55, c4((0.52, 0.36, 0.17))), (0.68, c4((0.62, 0.46, 0.24))), (0.80, c4((0.24, 0.27, 0.18)))], (-800, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.4, 0.8, 0.32, 0.7, (-600, -200)), b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = 0.7
    fine = noise_(nt, pos, 80.0, 4, 0.6, 0.0, (-1100, -350))
    bump_from(nt, b, fine.outputs["Fac"], 0.15, 0.001)
    return m

def purple_mat(name="M_PurpleCover"):
    """Woollen covers dyed purple (a deep red-violet), faded on the folds, with a coarse weave and woven border bands."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0)); pos = tc.outputs["Object"]
    n = noise_(nt, pos, 6.0, 6, 0.6, 0.0, (-1300, 0))
    r = ramp(nt, [(0.3, c4((0.22, 0.05, 0.08))), (0.6, c4((0.34, 0.08, 0.12))), (0.8, c4((0.42, 0.14, 0.16)))], (-1050, 0)); nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    wv = node(nt, "ShaderNodeTexWave", (-1300, -300), wave_type='BANDS', bands_direction='X'); wv.inputs["Scale"].default_value = 260.0
    nt.links.new(pos, wv.inputs["Vector"])
    wv2 = node(nt, "ShaderNodeTexWave", (-1300, -500), wave_type='BANDS', bands_direction='Y'); wv2.inputs["Scale"].default_value = 260.0
    nt.links.new(pos, wv2.inputs["Vector"])
    weave = math_(nt, 'MULTIPLY', wv.outputs["Fac"], wv2.outputs["Fac"], (-1050, -400))
    col = mix_rgb(nt, 'MULTIPLY', 0.25, r.outputs["Color"], weave, (-800, 0))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1300, 400)); nt.links.new(pos, sep.inputs["Vector"])
    bnd = math_(nt, 'FRACT', math_(nt, 'MULTIPLY', sep.outputs["Z"], 9.0, (-1100, 400)), None, (-950, 400))
    bandm = math_(nt, 'MULTIPLY', maprange(nt, bnd, 0.0, 0.03, 0.0, 1.0, (-800, 450)), maprange(nt, bnd, 0.07, 0.10, 1.0, 0.0, (-800, 350)), (-650, 400))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', bandm, 0.7, (-500, 400)), col, c4((0.42, 0.30, 0.12)), (-400, 100))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95; b.inputs["Sheen Weight"].default_value = 0.5; b.inputs["Sheen Roughness"].default_value = 0.5
    bump_from(nt, b, weave, 0.3, 0.002)
    return m

def terracotta_mat(name="M_Terracotta"):
    """Fired clay jars: orange-buff body with dark painted bands, rubbed and chipped."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0)); pos = tc.outputs["Object"]
    n = noise_(nt, pos, 9.0, 6, 0.6, 0.0, (-1300, 0))
    r = ramp(nt, [(0.3, c4((0.42, 0.22, 0.12))), (0.7, c4((0.56, 0.33, 0.19)))], (-1050, 0)); nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1300, 300)); nt.links.new(pos, sep.inputs["Vector"])
    bnd = math_(nt, 'FRACT', math_(nt, 'MULTIPLY', sep.outputs["Z"], 11.0, (-1100, 300)), None, (-950, 300))
    bandm = math_(nt, 'LESS_THAN', bnd, 0.16, (-800, 300))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', bandm, 0.85, (-650, 300)), r.outputs["Color"], c4((0.08, 0.05, 0.04)), (-500, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.7
    bump_from(nt, b, n.outputs["Fac"], 0.15, 0.002)
    return m

def stone_slabs_mat(name="M_PorchStone", cell=(0.9, 0.62), base=((0.38, 0.36, 0.32), (0.55, 0.52, 0.46)), rough=0.8):
    """Limestone paving in running courses: each slab its own tone, worn soft at the edges, dark joints."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-2000, 0)); pos = tc.outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1800, 300)); nt.links.new(pos, sep.inputs["Vector"])
    gy = math_(nt, 'DIVIDE', sep.outputs["Y"], cell[1], (-1600, 200))
    row = math_(nt, 'FLOOR', gy, None, (-1450, 200))
    off = math_(nt, 'MULTIPLY', math_(nt, 'FRACT', math_(nt, 'MULTIPLY', row, 0.5, (-1300, 350)), None, (-1150, 350)), cell[0], (-1000, 350))
    gx = math_(nt, 'DIVIDE', math_(nt, 'ADD', sep.outputs["X"], off, (-900, 450)), cell[0], (-750, 450))
    cxy = node(nt, "ShaderNodeCombineXYZ", (-600, 300)); nt.links.new(math_(nt, 'FLOOR', gx, None, (-650, 450)), cxy.inputs["X"]); nt.links.new(row, cxy.inputs["Y"])
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-450, 300), noise_dimensions='3D'); nt.links.new(cxy.outputs[0], wn.inputs["Vector"])
    tone = ramp(nt, [(0.0, c4(base[0])), (1.0, c4(base[1]))], (-300, 300)); nt.links.new(wn.outputs["Value"], tone.inputs["Fac"])
    fx = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', gx, None, (-600, 650)), 0.5, (-450, 650)), None, (-300, 650))
    fy = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', gy, None, (-600, 750)), 0.5, (-450, 750)), None, (-300, 750))
    jn = noise_(nt, pos, 4.0, 3, 0.5, 0.0, (-600, 900))
    jd = math_(nt, 'ADD', math_(nt, 'MAXIMUM', fx, math_(nt, 'MULTIPLY', fy, cell[1] / cell[0] * 0.0 + 1.0, (-150, 750)), (-50, 700)), math_(nt, 'MULTIPLY', jn.outputs["Fac"], 0.02, (-300, 900)), (100, 700))
    joint = maprange(nt, jd, 0.475, 0.495, 0.0, 1.0, (250, 700))
    n = noise_(nt, pos, 3.0, 9, 0.62, 0.0, (-600, -100))
    mr = ramp(nt, [(0.3, c4((0.78, 0.76, 0.72))), (0.6, c4((1, 1, 1))), (0.8, c4((1.05, 1.04, 1.0)))], (-300, -100)); nt.links.new(n.outputs["Fac"], mr.inputs["Fac"])
    col = mix_rgb(nt, 'MULTIPLY', 1.0, tone.outputs["Color"], mr.outputs["Color"], (0, 200))
    col = mix_rgb(nt, 'MIX', joint, col, c4((0.12, 0.11, 0.09)), (400, 200))
    ao = node(nt, "ShaderNodeAmbientOcclusion", (0, -400)); ao.inputs["Distance"].default_value = 0.3
    col = mix_rgb(nt, 'MULTIPLY', 0.35, col, ao.outputs["Color"], (550, 200))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    bump_from(nt, b, mix_f(nt, 0.5, math_(nt, 'SUBTRACT', 1.0, joint, (300, -300)), n.outputs["Fac"], (450, -300)), 0.5, 0.006)
    return m

def court_ground_mat(name="M_CourtGround"):
    """The court: beaten earth with a worn path of trodden stone from the gate to the porch and the altar, ash and
    straw by the altar, green-black damp at the foot of the walls, frost-wet in the shade."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-2000, 0)); pos = tc.outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1800, 300)); nt.links.new(pos, sep.inputs["Vector"])
    n = noise_(nt, pos, 1.1, 10, 0.62, 0.0, (-1500, 0))
    earth = ramp(nt, [(0.3, c4((0.20, 0.16, 0.115))), (0.55, c4((0.31, 0.25, 0.18))), (0.75, c4((0.38, 0.32, 0.24)))], (-1250, 0)); nt.links.new(n.outputs["Fac"], earth.inputs["Fac"])
    vor = node(nt, "ShaderNodeTexVoronoi", (-1500, -300)); vor.inputs["Scale"].default_value = 5.0; nt.links.new(pos, vor.inputs["Vector"])
    pebn = maprange(nt, vor.outputs["Distance"], 0.0, 0.25, 1.0, 0.0, (-1250, -300))
    peb = math_(nt, 'MULTIPLY', pebn, maprange(nt, noise_(nt, pos, 2.0, 3, 0.5, 0.0, (-1500, -500)).outputs["Fac"], 0.45, 0.6, 0.0, 1.0, (-1250, -500)), (-1050, -400))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', peb, 0.8, (-900, -400)), earth.outputs["Color"], c4((0.52, 0.49, 0.43)), (-700, 0))
    path = maprange(nt, math_(nt, 'ABSOLUTE', sep.outputs["X"], None, (-1500, 400)), 0.8, 2.2, 1.0, 0.0, (-1250, 400), interp='SMOOTHSTEP')
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', path, 0.45, (-1050, 400)), col, c4((0.44, 0.40, 0.34)), (-500, 0))
    ex = math_(nt, 'SUBTRACT', COURT_X, math_(nt, 'ABSOLUTE', sep.outputs["X"], None, (-1500, 700)), (-1350, 700))
    edge = maprange(nt, ex, 0.0, 0.8, 1.0, 0.0, (-1200, 700), interp='SMOOTHSTEP')
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', edge, 0.6, (-1050, 700)), col, c4((0.10, 0.11, 0.07)), (-300, 0))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, edge, 0.0, 1.0, 0.92, 0.6, (-300, -300)), b.inputs["Roughness"])
    bump_from(nt, b, mix_f(nt, 0.5, n.outputs["Fac"], pebn, (-300, -500)), 0.6, 0.02)
    return m

def far_hills_mat(name="M_FarHills"):
    """Ithaca's hills: grey limestone breaking through dark maquis scrub and olive terraces, paler with distance."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0)); pos = tc.outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1400, 300)); nt.links.new(pos, sep.inputs["Vector"])
    n = noise_(nt, pos, 0.18, 8, 0.62, 0.0, (-1300, 0))
    r = ramp(nt, [(0.35, c4((0.11, 0.13, 0.08))), (0.55, c4((0.19, 0.20, 0.13))), (0.68, c4((0.40, 0.38, 0.33))), (0.8, c4((0.50, 0.48, 0.43)))], (-1000, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    hz = maprange(nt, sep.outputs["Z"], 0.0, 16.0, 0.0, 0.4, (-1000, 300))
    col = mix_rgb(nt, 'MIX', hz, r.outputs["Color"], c4((0.44, 0.46, 0.50)), (-600, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    return m

def weed_mat(name="M_Weeds"):
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1200, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1000, 0))
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    zr = maprange(nt, sep.outputs["Z"], CZ, CZ + 0.35, 0.0, 1.0, (-800, 0))
    n = noise_(nt, tc.outputs["Object"], 3.0, 3, 0.5, 0.0, (-1000, -250))
    fz = math_(nt, 'ADD', zr, math_(nt, 'MULTIPLY_ADD', n.outputs["Fac"], 0.5, (-650, -150), c=-0.25), (-500, 0))
    r = ramp(nt, [(0.0, c4((0.04, 0.05, 0.025))), (0.4, c4((0.12, 0.16, 0.06))), (0.8, c4((0.26, 0.28, 0.14))), (1.0, c4((0.40, 0.37, 0.24)))], (-350, 0))
    nt.links.new(fz, r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.8; b.inputs["Sheen Weight"].default_value = 0.2
    return m

def sky_dome_mat(name="M_SkyDome"):
    """A clear, cold winter morning: deep clear blue overhead, paling to a warm haze low in the south-east where the
    sun is, thin high cloud catching the light."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-2000, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-1800, 0), operation='NORMALIZE'); nt.links.new(tc.outputs["Object"], nv.inputs[0])
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1600, 0)); nt.links.new(nv.outputs[0], sep.inputs["Vector"])
    el = sep.outputs["Z"]
    base = ramp(nt, [(0.0, c4((0.50, 0.50, 0.48))), (0.10, c4((0.62, 0.66, 0.70))), (0.25, c4((0.42, 0.53, 0.68))), (0.6, c4((0.22, 0.34, 0.56))), (1.0, c4((0.14, 0.24, 0.46)))], (-1200, 300))
    nt.links.new(maprange(nt, el, -0.12, 1.0, 0.0, 1.0, (-1400, 300)), base.inputs["Fac"])
    zk = math_(nt, 'ADD', math_(nt, 'MAXIMUM', el, 0.0, (-1400, -100)), 0.12, (-1250, -100))
    px = math_(nt, 'DIVIDE', sep.outputs["X"], zk, (-1100, -50)); py = math_(nt, 'DIVIDE', sep.outputs["Y"], zk, (-1100, -200))
    cv = node(nt, "ShaderNodeCombineXYZ", (-950, -100)); nt.links.new(px, cv.inputs["X"]); nt.links.new(py, cv.inputs["Y"])
    mp = node(nt, "ShaderNodeMapping", (-800, -100)); mp.inputs["Scale"].default_value = (0.25, 1.1, 1); mp.inputs["Location"].default_value = (1.7, 4.2, 0.3)
    nt.links.new(cv.outputs[0], mp.inputs["Vector"])
    cl = noise_(nt, mp.outputs["Vector"], 1.3, 8, 0.6, 0.6, (-600, -100))
    cm = maprange(nt, cl.outputs["Fac"], 0.56, 0.74, 0.0, 0.55, (-400, -100))
    cm = math_(nt, 'MULTIPLY', cm, maprange(nt, el, 0.04, 0.25, 0.0, 1.0, (-400, -250)), (-250, -150))
    sd = node(nt, "ShaderNodeVectorMath", (-1400, 600), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(SUN_DIR)
    nt.links.new(nv.outputs[0], sd.inputs[0])
    glow = maprange(nt, sd.outputs["Value"], 0.55, 1.0, 0.0, 1.0, (-1200, 600), interp='SMOOTHSTEP')
    cloud_col = mix_rgb(nt, 'MIX', glow, c4((0.80, 0.80, 0.82)), c4((1.0, 0.82, 0.60)), (-200, 300))
    col = mix_rgb(nt, 'MIX', cm, base.outputs["Color"], cloud_col, (0, 200))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', glow, 0.55, (-1000, 600)), col, c4((0.95, 0.70, 0.40)), (200, 200))
    disc = maprange(nt, sd.outputs["Value"], 0.9993, 0.9997, 0.0, 1.0, (-1000, 800))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', disc, 6.0, (-800, 800)), col, c4((1.0, 0.85, 0.6)), (350, 200))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m

M_WALL = wall_plaster_mat()
M_WALLCORE = noisy("M_WallCore", [(0.40, 0.37, 0.32), (0.53, 0.50, 0.44), (0.60, 0.57, 0.51)], scale=3.0, rough=0.9, bump=0.35, bump_dist=0.006, soot=(4.6, 6.0, 0.25))
M_COURTWALL = noisy("M_CourtWall", [(0.44, 0.41, 0.36), (0.58, 0.55, 0.49), (0.66, 0.63, 0.57)], scale=2.2, rough=0.92, bump=0.5, bump_dist=0.01, warp=0.4)
M_FLOOR = floor_mat()
M_CEIL = boards("M_CeilingReeds", light=(0.12, 0.10, 0.085), dark=(0.045, 0.04, 0.035), axis='X', width=0.045, grain=(30, 1.5, 1.5), rough=0.9, seam=0.6)
M_BEAM = wood("M_Beams", base=(0.14, 0.095, 0.06), dark=(0.04, 0.03, 0.022), light=(0.24, 0.17, 0.11), grain_dir=(5, 0.25, 5), bands='DIAGONAL', rough=(0.7, 0.9), soot=(3.0, 6.5, 0.45))
M_COLUMN = wood("M_CypressPost", base=(0.21, 0.135, 0.085), dark=(0.07, 0.045, 0.03), light=(0.32, 0.22, 0.14), grain_dir=(4, 4, 0.2), bands='DIAGONAL', rough=(0.45, 0.75), soot=(2.4, 5.2, 0.6), wear=(0.7, 1.5))
M_ASHWOOD = wood("M_AshThreshold", base=(0.46, 0.36, 0.24), dark=(0.20, 0.14, 0.08), light=(0.60, 0.50, 0.36), grain_dir=(0.25, 5, 5), bands='DIAGONAL', rough=(0.35, 0.65))
M_DOOR = boards("M_DoorOak", light=(0.34, 0.23, 0.13), dark=(0.17, 0.11, 0.06), axis='X', width=0.21, grain=(1.2, 1.2, 26), dirt=0.25, rough=0.75, soot=(2.0, 4.5, 0.4))
M_TABLE = wood("M_TableWood", base=(0.36, 0.22, 0.11), dark=(0.13, 0.07, 0.035), light=(0.50, 0.34, 0.18), grain_dir=(5, 0.25, 5), bands='DIAGONAL', rough=(0.4, 0.7), coat=0.08)
M_SEAT = wood("M_SeatWood", base=(0.25, 0.14, 0.07), dark=(0.07, 0.04, 0.02), light=(0.38, 0.24, 0.12), scale=1.4, grain_dir=(4, 4, 0.3), bands='DIAGONAL', rough=(0.4, 0.7), coat=0.15)
M_HEARTH = hearth_mat()
M_ASH = ash_mat()
M_CHAR = charwood_mat()
M_EMBERS = embers_mat()
M_FLAME = plain("M_Flame", (0.0, 0.0, 0.0), rough=1.0, emission=(1.0, 0.40, 0.08), strength=3.0)   # pure emission: the fire light inside must not bleach it
M_BRONZE = bronze_mat()
M_PURPLE = purple_mat()
M_FLEECE = noisy("M_Fleece", [(0.42, 0.38, 0.31), (0.58, 0.54, 0.46), (0.66, 0.62, 0.54)], scale=45, rough=1.0, bump=0.9, bump_dist=0.008, detail=8, sheen=0.6, warp=1.5)
M_HIDE = noisy("M_Hide", [(0.18, 0.11, 0.06), (0.30, 0.20, 0.11), (0.40, 0.29, 0.18)], scale=7, rough=0.8, bump=0.4, bump_dist=0.004, warp=0.8)
M_IVORY = noisy("M_IvoryInlay", [(0.55, 0.50, 0.40), (0.68, 0.63, 0.52)], scale=30, rough=0.35, bump=0.05, coat=0.3)
M_CLAY = terracotta_mat()
M_STONE = noisy("M_Limestone", [(0.36, 0.34, 0.30), (0.50, 0.48, 0.43), (0.58, 0.56, 0.51)], scale=4.0, rough=0.85, bump=0.4, bump_dist=0.006, warp=0.5)
M_PORCH = stone_slabs_mat()
M_COURT = court_ground_mat()
M_ROOF = noisy("M_RoofClay", [(0.28, 0.24, 0.19), (0.38, 0.33, 0.26), (0.45, 0.40, 0.32)], scale=2.5, rough=0.95, bump=0.4, bump_dist=0.01)
M_TWIG = noisy("M_Broom", [(0.20, 0.15, 0.08), (0.34, 0.27, 0.15)], scale=40, rough=0.85, stretch=(1, 1, 12), bump=0.3, bump_dist=0.002)
M_GUT = plain("M_LyreString", (0.55, 0.48, 0.36), rough=0.5)
M_FAR = far_hills_mat()
M_WEED = weed_mat()
M_SKY = sky_dome_mat()

# ----------------------------------------------------------------------------- geometry helpers (from build_lobby.py / build_kansas_farmhouse.py)
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

def lathe(name, profile, loc, mat, steps=16, jitter=0.0, seed=0):
    """profile: list of (radius, z) from bottom to top; revolve around Z (radius 0 = a pole). `jitter` roughens the
    radius a little (hand-thrown pots, a hand-built hearth)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for j, (r, z) in enumerate(profile):
        if r < 1e-5: rings.append([bm.verts.new((0, 0, z))]); continue
        ring = []
        for i in range(steps):
            a = 2 * math.pi * i / steps
            rr = r * (1 + jitter * noise.noise(Vector((math.cos(a) * 1.7 + seed, math.sin(a) * 1.7, j * 0.37))))
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
        rings.append(ring)
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

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

class Frame:
    """Local frame for a piece of furniture: +Y forward, origin on the floor, turned by yaw about Z."""
    def __init__(self, origin, yaw):
        self.o = Vector((origin[0], origin[1], 0.0)); self.yaw = yaw; self.R = Matrix.Rotation(yaw, 3, 'Z')
    def p(self, x, y, z): return tuple(self.o + self.R @ Vector((x, y, z)))
    def box(self, name, size, local, mat, bevel=0.0, rx=0.0, ry=0.0): return box(name, size, self.p(*local), mat, bevel=bevel, rot=(rx, ry, self.yaw))
    def cyl(self, name, r, h, local, mat, verts=8, r2=None): return cyl(name, r, h, self.p(*local), mat, verts=verts, rot=(0, 0, self.yaw), r2=r2)

def plane_xy(name, x0, x1, y0, y1, z, mat, nx=1, ny=1, uv=True, height=None):
    """A floor/ground plane with planar UVs over its own extent (the whole texture goes to the visible top)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap") if uv else None
    vs = [[bm.verts.new((x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, z + (height(x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny) if height else 0.0)))
           for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            if uv:
                for l in f.loops: l[uvl].uv = ((l.vert.co.x - x0) / (x1 - x0), (l.vert.co.y - y0) / (y1 - y0))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

# ----------------------------------------------------------------------------- the hall: floor, walls, ceiling and the smoke-lantern
plane_xy("Floor", -HX, HX, -HY, HY, 0.0, M_FLOOR, nx=10, ny=12)

def wall_run(name, axis, fixed, a0, a1, z0, z1, openings, mat, thick):
    """A wall along `axis` centred at `fixed`, from a0 to a1, with rectangular openings (centre, width, oz0, oz1)."""
    def piece(nm, l, r, zb, zt):
        if r - l < 1e-4 or zt - zb < 1e-4: return
        if axis == 'x': box(nm, (r - l, thick, zt - zb), ((l + r) / 2, fixed, (zb + zt) / 2), mat)
        else: box(nm, (thick, r - l, zt - zb), (fixed, (l + r) / 2, (zb + zt) / 2), mat)
    cur = a0; k = 0
    for (c, w, oz0, oz1) in sorted(openings):
        l, r = c - w / 2, c + w / 2
        piece(f"{name}_{k}", cur, l, z0, z1); piece(f"{name}_{k}b", l, r, z0, oz0); piece(f"{name}_{k}t", l, r, oz1, z1)
        cur = r; k += 1
    piece(f"{name}_{k}", cur, a1, z0, z1)

S_OPEN = [(0.0, DOOR_W, -0.3, DOOR_H)]
N_OPEN = [(IDOOR_X, IDOOR_W, -0.3, IDOOR_H), (UDOOR_X, 0.95, STAIR_TOP, STAIR_TOP + 2.0)]
# the wall cores (outer render, rubble under plaster) set 1 cm back from the interior plaster skins
CORE = WT - 0.01
wall_run("WallCore_S", 'x', -HY - 0.01 - CORE / 2, -HX - WT, HX + WT, CZ, ROOF_TOP, S_OPEN, M_WALLCORE, CORE)
wall_run("WallCore_N", 'x', HY + 0.01 + CORE / 2, -HX - WT, HX + WT, CZ, ROOF_TOP, N_OPEN, M_WALLCORE, CORE)
wall_run("WallCore_W", 'y', -HX - 0.01 - CORE / 2, -HY - 0.01, HY + 0.01, CZ, ROOF_TOP, [], M_WALLCORE, CORE)
wall_run("WallCore_E", 'y', HX + 0.01 + CORE / 2, -HY - 0.01, HY + 0.01, CZ, ROOF_TOP, [], M_WALLCORE, CORE)
# interior plaster skins (thin), the full height to the ceiling
SK = 0.012
wall_run("Plaster_S", 'x', -HY - SK / 2 + 0.002, -HX, HX, 0.0, CEIL + 0.3, S_OPEN, M_WALL, SK)
wall_run("Plaster_N", 'x', HY + SK / 2 - 0.002, -HX, HX, 0.0, CEIL + 0.3, N_OPEN, M_WALL, SK)
wall_run("Plaster_W", 'y', -HX - SK / 2 + 0.002, -HY, HY, 0.0, CEIL + 0.3, [], M_WALL, SK)
wall_run("Plaster_E", 'y', HX + SK / 2 - 0.002, -HY, HY, 0.0, CEIL + 0.3, [], M_WALL, SK)
# a plaster cove where the walls meet the floor (the plasterer's fillet), so the walls sit into the floor
for nm, size, loc in (("Cove_W", (0.09, 2 * HY, 0.09), (-HX, 0, 0.0)), ("Cove_E", (0.09, 2 * HY, 0.09), (HX, 0, 0.0))):
    box(nm, size, loc, M_WALL, rot=(0, math.radians(45), 0))
for nm, x0, x1, yy in (("Cove_N0", -HX, IDOOR_X - IDOOR_W / 2, HY), ("Cove_N1", IDOOR_X + IDOOR_W / 2, HX, HY),
                       ("Cove_S0", -HX, -DOOR_W / 2, -HY), ("Cove_S1", DOOR_W / 2, HX, -HY)):
    box(nm, (x1 - x0, 0.09, 0.09), ((x0 + x1) / 2, yy, 0.0), M_WALL, rot=(math.radians(45), 0, 0))

# the ceiling: main beams on the column lines (both ways), joists across, reed matting laid over them (soot-black)
BEAM_W, BEAM_H = 0.34, 0.36
BZ0 = CEIL - BEAM_H
for s in (-1, 1):
    box(f"MainBeamY{s}", (BEAM_W, 2 * HY + 0.4, BEAM_H), (s * COL, 0, BZ0 + BEAM_H / 2), M_BEAM)
for k, yy in enumerate((HEARTH.y - COL, HEARTH.y + COL)):
    box(f"MainBeamX{k}", (2 * HX + 0.4, BEAM_W, BEAM_H), (0, yy, BZ0 + BEAM_H / 2), M_BEAM)
JW, JH = 0.15, 0.19
for k in range(17):
    yy = -HY + 0.35 + k * ((2 * HY - 0.7) / 16)
    inside = HEARTH.y - COL - 0.1 < yy < HEARTH.y + COL + 0.1
    segs = [(-HX, -COL), (COL, HX)] if inside else [(-HX, HX)]
    for j, (a, bnd) in enumerate(segs):
        box(f"Joist{k}_{j}", (bnd - a, JW, JH), ((a + bnd) / 2, yy + 0.02 * math.sin(k * 2.3), CEIL + JH / 2 - 0.005), M_BEAM)
RZ = CEIL + JH
L0, L1 = HEARTH.y - COL, HEARTH.y + COL
for nm, x0, x1, y0, y1 in (("Reeds_W", -HX, -COL, -HY, HY), ("Reeds_E", COL, HX, -HY, HY), ("Reeds_S", -COL, COL, -HY, L0), ("Reeds_N", -COL, COL, L1, HY)):
    box(nm, (x1 - x0, y1 - y0, 0.06), ((x0 + x1) / 2, (y0 + y1) / 2, RZ + 0.03), M_CEIL)
box("RoofClay", (2 * HX + 2 * WT, 2 * HY + 2 * WT, ROOF_TOP - RZ - 0.06), (0, 0, (RZ + 0.06 + ROOF_TOP) / 2), M_ROOF)
# the roof slab has the lantern square cut out of it: rebuild as four pieces instead of one
bpy.data.objects.remove(bpy.data.objects["RoofClay"])
for nm, x0, x1, y0, y1 in (("RoofClay_W", -HX - WT, -COL, -HY - WT, HY + WT), ("RoofClay_E", COL, HX + WT, -HY - WT, HY + WT),
                           ("RoofClay_S", -COL, COL, -HY - WT, L0), ("RoofClay_N", -COL, COL, L1, HY + WT)):
    box(nm, (x1 - x0, y1 - y0, ROOF_TOP - RZ - 0.06), ((x0 + x1) / 2, (y0 + y1) / 2, (RZ + 0.06 + ROOF_TOP) / 2), M_ROOF)

# the smoke-lantern over the hearth: a timber sill, open vents between posts, a lintel, a roof with the smoke hole
LH = COL + BEAM_W / 2                       # outer half-size of the lantern frame (on the main beams)
for s in (-1, 1):
    box(f"LanSillX{s}", (2 * LH, 0.18, VENT0 - LAN_Z0 + 0.02), (0, HEARTH.y + s * (LH - 0.09), (LAN_Z0 + VENT0) / 2), M_WALLCORE)
    box(f"LanSillY{s}", (0.18, 2 * LH - 0.36, VENT0 - LAN_Z0 + 0.02), (s * (LH - 0.09), HEARTH.y, (LAN_Z0 + VENT0) / 2), M_WALLCORE)
    box(f"LanLintelX{s}", (2 * LH, 0.2, LAN_Z1 - VENT1), (0, HEARTH.y + s * (LH - 0.1), (VENT1 + LAN_Z1) / 2), M_BEAM)
    box(f"LanLintelY{s}", (0.2, 2 * LH - 0.4, LAN_Z1 - VENT1), (s * (LH - 0.1), HEARTH.y, (VENT1 + LAN_Z1) / 2), M_BEAM)
for i, t in enumerate((-1.0, -0.33, 0.33, 1.0)):
    for s in (-1, 1):
        box(f"LanPostX{i}{s}", (0.16, 0.16, VENT1 - VENT0), (t * (LH - 0.09), HEARTH.y + s * (LH - 0.09), (VENT0 + VENT1) / 2), M_BEAM)
        if abs(t) < 0.9:
            box(f"LanPostY{i}{s}", (0.16, 0.16, VENT1 - VENT0), (s * (LH - 0.09), HEARTH.y + t * (LH - 0.09), (VENT0 + VENT1) / 2), M_BEAM)
for k in range(6):                               # lantern ceiling joists, reeds over, the clay roof with the smoke hole
    xx = -LH + 0.35 + k * (2 * LH - 0.7) / 5
    for j, (a, bnd) in enumerate(((-LH + 0.2, -HOLE), (HOLE, LH - 0.2))) if abs(xx) < HOLE + 0.1 else [(0, (-LH + 0.2, LH - 0.2))]:
        box(f"LanJoist{k}_{j}", (JW, bnd - a, JH), (xx, HEARTH.y + (a + bnd) / 2, LAN_Z1 + JH / 2), M_BEAM)
LRZ = LAN_Z1 + JH
for nm, x0, x1, y0, y1 in (("LanReeds_W", -LH, -HOLE, -LH, LH), ("LanReeds_E", HOLE, LH, -LH, LH), ("LanReeds_S", -HOLE, HOLE, -LH, -HOLE), ("LanReeds_N", -HOLE, HOLE, HOLE, LH)):
    box(nm, (x1 - x0, y1 - y0, 0.05), ((x0 + x1) / 2, HEARTH.y + (y0 + y1) / 2, LRZ + 0.025), M_CEIL)
    box(nm.replace("Reeds", "Roof"), (x1 - x0 + (0.15 if 'W' in nm[-1] or 'E' in nm[-1] else 0), y1 - y0 + 0.15, 0.22), ((x0 + x1) / 2, HEARTH.y + (y0 + y1) / 2, LRZ + 0.16), M_ROOF)
for s in (-1, 1):                                # the clay collar round the smoke hole
    box(f"HoleCollarX{s}", (2 * HOLE + 0.24, 0.12, 0.45), (0, HEARTH.y + s * (HOLE + 0.06), LRZ + 0.27 + 0.2), M_ROOF)
    box(f"HoleCollarY{s}", (0.12, 2 * HOLE, 0.45), (s * (HOLE + 0.06), HEARTH.y, LRZ + 0.27 + 0.2), M_ROOF)
    box(f"HoleFrameX{s}", (2 * HOLE + 0.1, 0.10, 0.12), (0, HEARTH.y + s * (HOLE + 0.05), LRZ - 0.02), M_BEAM)

# ----------------------------------------------------------------------------- the four bearing-posts of cypress
def column(name, base_xy, h_top=BZ0, r0=0.215, r1=0.25):
    bx, by = base_xy
    lathe(f"{name}_Base", [(0.0, 0.0), (0.40, 0.0), (0.41, 0.07), (0.38, 0.12), (0.0, 0.12)], (bx, by, 0), M_STONE, steps=20, jitter=0.03, seed=bx + by)
    shaft_top = h_top - 0.42
    prof = [(r0, 0.12), (r0 * 1.004, 0.9), ((r0 + r1) / 2, 2.4), (r1, shaft_top)]
    lathe(f"{name}_Shaft", prof, (bx, by, 0), M_COLUMN, steps=20)
    lathe(f"{name}_Collar", [(r1 + 0.01, shaft_top), (r1 + 0.03, shaft_top + 0.04), (r1 + 0.03, shaft_top + 0.08), (r1 + 0.01, shaft_top + 0.1)], (bx, by, 0), M_COLUMN, steps=20)
    lathe(f"{name}_Echinus", [(r1 + 0.01, shaft_top + 0.1), (r1 + 0.16, shaft_top + 0.2), (r1 + 0.2, shaft_top + 0.26), (0.0, shaft_top + 0.27)], (bx, by, 0), M_COLUMN, steps=20)
    box(f"{name}_Abacus", (0.62, 0.62, 0.15), (bx, by, h_top - 0.075), M_COLUMN, bevel=0.012)

for i, c in enumerate(COLS):
    column(f"Column{i}", (c.x, c.y))

# ----------------------------------------------------------------------------- the round hearth with the new fire
hx, hy = HEARTH.x, HEARTH.y
lathe("Hearth_Rim", [(HR_OUT + 0.03, 0.0), (HR_OUT, 0.02), (HR_OUT - 0.01, HR_H - 0.03), (HR_OUT - 0.04, HR_H), (HR_IN + 0.03, HR_H), (HR_IN, HR_H - 0.03), (HR_IN - 0.02, 0.07)],
      (hx, hy, 0), M_HEARTH, steps=56, jitter=0.006, seed=3.1)
lathe("Hearth_Ash", [(HR_IN - 0.01, 0.07), (HR_IN - 0.25, 0.085), (0.75, 0.095), (0.4, 0.11), (0.0, 0.115)], (hx, hy, 0), M_ASH, steps=40, jitter=0.03, seed=8.0)
FIRE = Vector((hx - 0.12, hy + 0.10, 0.11))      # the fire is laid a little off-centre, to the north-west
rnd = random.Random(42)
for i, (ang, ln, rr, tilt) in enumerate([(0.35, 0.78, 0.065, 0.20), (1.9, 0.72, 0.055, 0.16), (3.6, 0.66, 0.06, 0.22), (4.8, 0.58, 0.05, 0.12), (2.7, 0.5, 0.045, 0.30)]):
    d = Vector((math.cos(ang), math.sin(ang), 0))
    c = FIRE + d * (ln * 0.32) + Vector((0, 0, rr + 0.02 + tilt * 0.25))
    rot_z = ang; rot_y = math.radians(90) - tilt
    cyl(f"Log{i}", rr, ln, tuple(c), M_CHAR, verts=7, rot=(0, rot_y, rot_z))
for i in range(3):                                 # two spare split logs on the rim's ash bed, waiting
    cyl(f"SpareLog{i}", 0.06, 0.7, (hx + 0.55 + i * 0.13, hy - 0.62 + i * 0.04, 0.165 + (0.1 if i == 2 else 0)), M_CHAR, verts=6, rot=(0, math.radians(90), math.radians(62 + 8 * i)))
lathe("Embers", [(0.0, 0.10), (0.42, 0.10), (0.36, 0.13), (0.18, 0.15), (0.0, 0.155)], tuple(FIRE * Vector((1, 1, 0))), M_EMBERS, steps=18, jitter=0.25, seed=1.0)
for i in range(7):
    a = rnd.uniform(0, 2 * math.pi); r_ = rnd.uniform(0.1, 0.4)
    sphere(f"Ember{i}", rnd.uniform(0.025, 0.05), (FIRE.x + r_ * math.cos(a), FIRE.y + r_ * math.sin(a), 0.13), M_EMBERS, seg=6, scale=(1.3, 1, 0.55))
for i, (dx, dy, h, r) in enumerate([(0.0, 0.0, 0.34, 0.05), (0.09, 0.04, 0.24, 0.035), (-0.08, 0.07, 0.2, 0.035), (0.04, -0.1, 0.17, 0.03),
                                    (-0.05, -0.05, 0.27, 0.04), (0.13, -0.06, 0.13, 0.025), (-0.13, 0.0, 0.12, 0.025)]):
    cyl(f"Flame{i}", r * 1.5, h, (FIRE.x + dx, FIRE.y + dy, 0.16 + h / 2), M_FLAME, verts=7, r2=0.003,
        rot=(0.25 * math.sin(i * 2.1), 0.25 * math.cos(i * 1.7), 0))

# ----------------------------------------------------------------------------- the great doors and the high threshold of ash
TY = -HY - WT / 2
box("Threshold", (DOOR_W + 0.3, WT + 0.06, THR_H), (0, TY, THR_H / 2), M_ASHWOOD, bevel=0.015)
for s in (-1, 1):
    box(f"DoorPost{s}", (0.24, WT + 0.08, DOOR_H), (s * (DOOR_W / 2 + 0.11), TY, DOOR_H / 2), M_COLUMN, bevel=0.01)
box("DoorLintel", (DOOR_W + 0.8, WT + 0.1, 0.3), (0, TY, DOOR_H + 0.15), M_COLUMN, bevel=0.01)
# the leaves, swung inward against the inside of the south wall
LW = DOOR_W / 2 - 0.02
for s in (-1, 1):
    hinge = Vector((s * (DOOR_W / 2 - 0.02), -HY + 0.03, 0))
    # the leaf lies along the wall, opening into the room: from the hinge outwards (away from the opening) and slightly in
    ldir = Vector((s * math.cos(math.radians(14)), math.sin(math.radians(14)), 0))
    c = hinge + ldir * (LW / 2) + Vector((0, 0, THR_H + (DOOR_H - THR_H) / 2))
    yaw = math.atan2(ldir.y, ldir.x)
    box(f"DoorLeaf{s}", (LW, 0.07, DOOR_H - THR_H - 0.04), tuple(c), M_DOOR, rot=(0, 0, yaw), bevel=0.01)
    for k, zz in enumerate((THR_H + 0.35, THR_H + 1.5, DOOR_H - 0.35)):
        cc = hinge + ldir * (LW / 2) + Vector((0, 0, zz)) + Vector((-ldir.y, ldir.x, 0)) * 0.04
        box(f"DoorRail{s}{k}", (LW - 0.06, 0.03, 0.12), tuple(cc), M_DOOR, rot=(0, 0, yaw))
    ring_c = hinge + ldir * (LW - 0.15) + Vector((0, 0, 1.3)) + Vector((-ldir.y, ldir.x, 0)) * 0.05
    torus(f"DoorRing{s}", 0.06, 0.008, tuple(ring_c), M_BRONZE, rot=(math.radians(90), 0, yaw), seg=12, rseg=4)

# ----------------------------------------------------------------------------- the door that leads into the house (to the store-room), closed
ITY = HY + WT / 2
box("InnerThreshold", (IDOOR_W + 0.2, WT + 0.04, 0.12), (IDOOR_X, ITY, 0.06), M_TABLE, bevel=0.01)
for s in (-1, 1):
    box(f"InnerPost{s}", (0.18, WT + 0.06, IDOOR_H), (IDOOR_X + s * (IDOOR_W / 2 + 0.07), ITY, IDOOR_H / 2), M_COLUMN, bevel=0.01)
    box(f"InnerLeaf{s}", (IDOOR_W / 2 + 0.01, 0.07, IDOOR_H - 0.14), (IDOOR_X + s * (IDOOR_W / 4), HY + 0.08, 0.12 + (IDOOR_H - 0.14) / 2), M_DOOR, bevel=0.008)
    for k, zz in enumerate((0.45, 1.3, IDOOR_H - 0.35)):
        for j in range(3):                     # bronze nail heads on the rails
            sphere(f"InnerStud{s}{k}{j}", 0.018, (IDOOR_X + s * (0.12 + j * 0.2), HY + 0.04, zz), M_BRONZE, seg=6, scale=(1, 0.5, 1))
box("InnerPassage", (IDOOR_W + 0.8, 0.2, IDOOR_H + 0.4), (IDOOR_X, HY + WT + 0.1, IDOOR_H / 2), M_WALLCORE)
box("UpperPassage", (1.5, 0.2, 2.4), (UDOOR_X, HY + WT + 0.1, STAIR_TOP + 1.0), M_WALLCORE)
box("InnerLintel", (IDOOR_W + 0.5, WT + 0.08, 0.24), (IDOOR_X, ITY, IDOOR_H + 0.12), M_COLUMN, bevel=0.01)
torus("InnerHandle", 0.055, 0.008, (IDOOR_X - 0.1, HY + 0.02, 1.15), M_BRONZE, rot=(math.radians(90), 0, 0), seg=12, rseg=4)
# the strap through the door, tied round the handle (the key-hole above)
box("InnerStrap", (0.03, 0.006, 0.42), (IDOOR_X - 0.1, HY + 0.035, 0.95), M_HIDE, rot=(0, math.radians(6), 0))
box("InnerStrapKnot", (0.06, 0.02, 0.05), (IDOOR_X - 0.1, HY + 0.03, 1.13), M_HIDE, bevel=0.01)

# ----------------------------------------------------------------------------- the stair to Penelope's upper room (west wall, north end)
N_STEPS = 15
run = (STAIR_Y1 - STAIR_Y0) / N_STEPS; rise = STAIR_TOP / N_STEPS
for k in range(N_STEPS):
    y0 = STAIR_Y0 + k * run
    box(f"Step{k}", (STAIR_X1 - STAIR_X0, run + 0.03, 0.06), ((STAIR_X0 + STAIR_X1) / 2, y0 + run / 2, (k + 1) * rise - 0.03), M_STONE, bevel=0.01)
# the solid plastered flank under the stair (a stepped profile, built as stacked blocks)
for k in range(N_STEPS):
    y0 = STAIR_Y0 + k * run
    box(f"StairFlank{k}", (STAIR_X1 - STAIR_X0 - 0.02, run, (k + 1) * rise - 0.06), ((STAIR_X0 + STAIR_X1) / 2, y0 + run / 2, ((k + 1) * rise - 0.06) / 2), M_WALL)
box("Landing", (STAIR_X1 - STAIR_X0 + 0.3, HY - STAIR_Y1, 0.1), ((STAIR_X0 + STAIR_X1 + 0.3) / 2, (STAIR_Y1 + HY) / 2, STAIR_TOP - 0.05), M_STONE, bevel=0.01)
box("LandingBlock", (STAIR_X1 - STAIR_X0 + 0.28, HY - STAIR_Y1, STAIR_TOP - 0.1), ((STAIR_X0 + STAIR_X1 + 0.28) / 2, (STAIR_Y1 + HY) / 2, (STAIR_TOP - 0.1) / 2), M_WALL)
# a timber handrail on posts along the open side
for k, t in enumerate((0.0, 0.5, 1.0)):
    yy = STAIR_Y0 + 0.15 + t * (STAIR_Y1 - STAIR_Y0 - 0.3); zz = (yy - STAIR_Y0) / run * rise
    cyl(f"RailPost{k}", 0.035, 1.0, (STAIR_X1 - 0.06, yy, zz + 0.5), M_SEAT, verts=8)
rl = math.hypot(STAIR_Y1 - STAIR_Y0 - 0.3, (STAIR_Y1 - STAIR_Y0 - 0.3) / run * rise)
cyl("Handrail", 0.03, rl + 0.1, (STAIR_X1 - 0.06, (STAIR_Y0 + STAIR_Y1) / 2, (STAIR_Y1 - STAIR_Y0) / 2 / run * rise + 0.98), M_SEAT, verts=8,
    rot=(-(math.pi / 2 - math.atan2(rise, run)), 0, 0))
# the upper-room door on the landing: shut
for s in (-1, 1):
    box(f"UpperPost{s}", (0.14, WT + 0.04, 2.0), (UDOOR_X + s * 0.545, ITY, STAIR_TOP + 1.0), M_COLUMN)
box("UpperLeaf", (0.95, 0.06, 1.95), (UDOOR_X, HY + 0.08, STAIR_TOP + 0.98), M_DOOR, bevel=0.006)
box("UpperLintel", (1.3, WT + 0.06, 0.2), (UDOOR_X, ITY, STAIR_TOP + 2.1), M_COLUMN)

# ----------------------------------------------------------------------------- tables and seats (the suitors' places), covers on the seats
def table(name, cx, cy, yaw, L=1.6, D=0.66, H=0.72):
    f = Frame((cx, cy), yaw)
    f.box(f"{name}_Top", (L, D, 0.05), (0, 0, H - 0.025), M_TABLE, bevel=0.008)
    for dx in (-1, 1):
        for dy in (-1, 1):
            f.cyl(f"{name}_Leg{dx}{dy}", 0.03, H - 0.05, (dx * (L / 2 - 0.1), dy * (D / 2 - 0.08), (H - 0.05) / 2), M_TABLE, verts=8)
        f.box(f"{name}_Stretcher{dx}", (0.035, D - 0.2, 0.04), (dx * (L / 2 - 0.1), 0, 0.16), M_TABLE)
    f.box(f"{name}_Rail", (L - 0.2, 0.035, 0.04), (0, 0, 0.16), M_TABLE)
    return f

def seat(name, cx, cy, yaw, back=True, cover=True, arms=False, H=0.46, W=0.56, D=0.5, mat=None, stool=True):
    """A seat with turned legs and a back (thronos), a purple cover thrown over the seat and the back, a footstool."""
    mat = mat or M_SEAT
    f = Frame((cx, cy), yaw)
    f.box(f"{name}_Seat", (W, D, 0.05), (0, 0, H - 0.025), mat, bevel=0.006)
    for dx in (-1, 1):
        for dy in (-1, 1):
            f.cyl(f"{name}_Leg{dx}{dy}", 0.026, H - 0.05, (dx * (W / 2 - 0.05), dy * (D / 2 - 0.05), (H - 0.05) / 2), mat, verts=8, r2=0.02)
    if back:
        for dx in (-1, 1):
            f.box(f"{name}_BackPost{dx}", (0.045, 0.045, 0.62), (dx * (W / 2 - 0.04), -D / 2 + 0.03, H + 0.30), mat, rx=math.radians(-6))
        f.box(f"{name}_BackRail", (W - 0.04, 0.04, 0.12), (0, -D / 2 + 0.0, H + 0.56), mat, bevel=0.005, rx=math.radians(-6))
    if arms:
        for dx in (-1, 1):
            f.box(f"{name}_Arm{dx}", (0.05, D - 0.04, 0.05), (dx * (W / 2 - 0.02), 0.01, H + 0.22), mat, bevel=0.005)
            f.cyl(f"{name}_ArmPost{dx}", 0.02, 0.22, (dx * (W / 2 - 0.02), D / 2 - 0.06, H + 0.11), mat, verts=6)
    if cover:
        f.box(f"{name}_Cover", (W + 0.02, D + 0.04, 0.03), (0, 0.01, H + 0.012), M_PURPLE, bevel=0.012)
        f.box(f"{name}_CoverFront", (W - 0.02, 0.025, 0.2), (0, D / 2 + 0.018, H - 0.08), M_PURPLE, bevel=0.008)
        if back:
            f.box(f"{name}_CoverBack", (W - 0.06, 0.03, 0.5), (0, -D / 2 + 0.045, H + 0.29), M_PURPLE, bevel=0.01, rx=math.radians(-6))
    if stool:
        f.box(f"{name}_Footstool", (0.42, 0.26, 0.12), (0, D / 2 + 0.24, 0.06), mat, bevel=0.01)
    return f

def cup(name, x, y, z, scale=1.0, mat=None):
    """A two-handled drinking cup (kylix) on a short stem."""
    mat = mat or M_CLAY; s = scale
    lathe(name, [(0.0, z), (0.035 * s, z), (0.03 * s, z + 0.01 * s), (0.012 * s, z + 0.02 * s), (0.012 * s, z + 0.045 * s), (0.07 * s, z + 0.07 * s), (0.085 * s, z + 0.095 * s),
                 (0.08 * s, z + 0.095 * s), (0.0, z + 0.06 * s)], (x, y, 0), mat, steps=12)

# east side: three tables with their seats, the high seat by the middle one (the master's place)
T_E = [(-3.35, 0.0), (-0.15, 0.06), (3.45, -0.04)]
for i, (yy, jit) in enumerate(T_E):
    table(f"TableE{i}", HX - 0.95, yy, math.radians(90) + jit, L=1.7)
for i, (yy, yaw_j) in enumerate([(-4.15, 0.12), (-2.55, -0.18), (-0.95, 0.05), (0.75, -0.1), (2.65, 0.2), (4.25, -0.06)]):
    seat(f"SeatE{i}", HX - 0.33, yy, math.radians(90) + yaw_j, cover=(i != 3), stool=(i % 2 == 0))
# west side, south of the stair: two tables and four seats
T_W = [(-4.0, -0.03), (-1.55, 0.05)]
for i, (yy, jit) in enumerate(T_W):
    table(f"TableW{i}", -HX + 0.95, yy, math.radians(-90) + jit, L=1.6)
for i, (yy, yaw_j) in enumerate([(-4.75, -0.1), (-3.25, 0.15), (-2.3, -0.05), (-0.8, 0.12)]):
    seat(f"SeatW{i}", -HX + 0.33, yy, math.radians(-90) + yaw_j, cover=(i != 1), stool=(i % 2 == 1))
# along the north wall, west of the inner door: a long bench with a cover rolled along it
box("BenchN", (2.6, 0.42, 0.06), (-0.6, HY - 0.32, 0.43), M_SEAT, bevel=0.008)
for k, xx in enumerate((-1.75, -0.6, 0.55)):
    box(f"BenchNLeg{k}", (0.08, 0.36, 0.40), (xx, HY - 0.32, 0.2), M_SEAT)
box("BenchNCover", (1.5, 0.44, 0.035), (-0.95, HY - 0.32, 0.475), M_PURPLE, bevel=0.012)
cyl("BenchNCoverRoll", 0.07, 0.44, (-0.05, HY - 0.32, 0.53), M_PURPLE, verts=10, rot=(math.radians(90), 0, 0))

# the tables, wiped down: cups set out on one, a sponge and a bowl of water on another, the rest bare and damp
for k in range(6):
    cup(f"CupE0_{k}", HX - 0.95 + (0.18 if k % 2 else -0.18), -3.35 - 0.6 + k * 0.24, 0.72, scale=1.0 + 0.06 * math.sin(k * 3.1))
for k in range(4):
    cup(f"CupStack{k}", HX - 0.85, 3.85, 0.72 + k * 0.045, scale=1.0 - 0.01 * k)
lathe("WashBowl", [(0.0, 0.72), (0.08, 0.72), (0.16, 0.76), (0.19, 0.82), (0.185, 0.825), (0.15, 0.78), (0.0, 0.765)], (HX - 1.0, 3.1, 0), M_BRONZE, steps=20)
sphere("Sponge", 0.07, (HX - 0.78, 2.85, 0.75), M_HIDE, seg=8, scale=(1.2, 0.9, 0.5))
for k in range(3):
    cup(f"CupW{k}", -HX + 0.85 + 0.12 * (k - 1), -1.65 + 0.3 * k, 0.72, scale=0.95)
lathe("Jug", [(0.0, 0.72), (0.06, 0.72), (0.11, 0.82), (0.105, 0.92), (0.05, 0.99), (0.04, 1.03), (0.055, 1.06), (0.0, 1.06)], (-HX + 1.05, -4.25, 0), M_CLAY, steps=16)

# ----------------------------------------------------------------------------- Penelope's chair by the fire, inlaid with ivory and silver, a fleece over it
pf = seat("PenelopeChair", hx - 0.9, hy - 2.35, math.radians(-21), back=True, cover=False, arms=True, H=0.48, W=0.62, D=0.56, stool=True)
for k, zz in enumerate((0.15, 0.30)):
    pf.box(f"Inlay{k}", (0.5, 0.012, 0.035), (0, 0.285, zz), M_IVORY)
for dx in (-1, 1):
    pf.box(f"InlayBack{dx}", (0.012, 0.05, 0.45), (dx * 0.27, -0.24, 0.80), M_IVORY, rx=math.radians(-6))
pf.box("PenelopeFleece", (0.62, 0.58, 0.07), (0, 0.02, 0.52), M_FLEECE, bevel=0.03)
pf.box("PenelopeFleeceBack", (0.56, 0.06, 0.5), (0, -0.23, 0.80), M_FLEECE, bevel=0.025, rx=math.radians(-6))
pf.box("PenelopeFleeceDrape", (0.06, 0.5, 0.32), (0.33, 0.02, 0.36), M_FLEECE, bevel=0.025)

# ----------------------------------------------------------------------------- the bronze mixing-bowl on its stand, by the door into the house
KX, KY = 1.25, HY - 0.95
for k in range(3):
    a = math.radians(90 + 120 * k)
    cyl(f"KraterStandLeg{k}", 0.025, 0.62, (KX + 0.22 * math.cos(a), KY + 0.22 * math.sin(a), 0.31), M_BRONZE, verts=6, rot=(0.12 * math.sin(a), -0.12 * math.cos(a), 0))
torus("KraterStandRing", 0.25, 0.022, (KX, KY, 0.60), M_BRONZE, seg=16, rseg=4)
lathe("Krater", [(0.0, 0.58), (0.10, 0.58), (0.12, 0.62), (0.24, 0.74), (0.29, 0.86), (0.27, 0.98), (0.30, 1.04), (0.33, 1.07), (0.31, 1.075), (0.27, 1.03), (0.0, 0.99)],
      (KX, KY, 0), M_BRONZE, steps=28)
for s in (-1, 1):
    torus(f"KraterHandle{s}", 0.07, 0.014, (KX + s * 0.30, KY, 0.92), M_BRONZE, rot=(math.radians(90), 0, math.radians(90)), seg=10, rseg=4)
cyl("KraterLadle", 0.012, 0.5, (KX + 0.1, KY + 0.12, 1.05), M_BRONZE, verts=6, rot=(math.radians(25), math.radians(15), 0))
seat("SilverStuddedSeat", KX + 0.85, KY - 0.15, math.radians(200), back=False, cover=True, stool=False, H=0.44, W=0.5, D=0.42)
for j in range(5):
    sphere(f"SeatStud{j}", 0.012, (KX + 0.85 + math.cos(math.radians(200 + 90)) * (j - 2) * 0.09, KY - 0.15 + math.sin(math.radians(290)) * (j - 2) * 0.09 + 0.0, 0.405), M_IVORY, seg=6)

# ----------------------------------------------------------------------------- empty pegs where the armour hung, and the empty spear-stand by a bearing-post
def peg(name, wall, u, z):
    if wall == 'E': loc, rot = (HX - 0.06, u, z), (0, math.radians(-80), 0)
    elif wall == 'W': loc, rot = (-HX + 0.06, u, z), (0, math.radians(80), 0)
    else: loc, rot = (u, HY - 0.06, z), (math.radians(80), 0, 0)
    cyl(name, 0.018, 0.13, loc, M_BRONZE, verts=6, rot=rot, r2=0.013)
for i, (wall, kind, u, z, ru, rz) in enumerate(ARMOUR):
    if kind in ('spear', 'sword'):
        for s in (-0.7, 0.7): peg(f"Peg{i}{'ab'[s > 0]}", wall, u + s * ru, z - rz - 0.02)
    else:
        peg(f"Peg{i}", wall, u, z + rz * 0.62)
SC = Vector((COLS[2].x - 0.34, COLS[2].y, 0))   # against the west face of the bearing-post nearest the reader
box("SpearStand_Plank", (0.08, 0.36, 1.45), (SC.x, SC.y, 0.725), M_SEAT, bevel=0.006)
box("SpearStand_Rack", (0.22, 0.42, 0.06), (SC.x - 0.07, SC.y, 1.28), M_SEAT, bevel=0.006)
box("SpearStand_Foot", (0.26, 0.46, 0.10), (SC.x - 0.07, SC.y, 0.05), M_SEAT, bevel=0.01)
for k in range(3):                                  # the notches (now empty), cut as dark gaps by little blocks
    box(f"SpearStand_Tooth{k}", (0.10, 0.04, 0.07), (SC.x - 0.12, SC.y - 0.18 + k * 0.18, 1.31), M_SEAT)

# ----------------------------------------------------------------------------- the minstrel's lyre on its peg (on the bearing-post by Penelope's chair)
LC = COLS[0]
ly = Vector((LC.x + 0.25, LC.y - 0.12, 1.62))
cyl("LyrePeg", 0.014, 0.12, (LC.x + 0.22, LC.y - 0.06, 1.88), M_SEAT, verts=6, rot=(0, math.radians(80), math.radians(-25)))
sphere("LyreShell", 0.13, (ly.x + 0.04, ly.y - 0.02, ly.z - 0.18), M_HIDE, seg=10, scale=(0.35, 1.0, 1.05))
for s in (-1, 1):
    cyl(f"LyreArm{s}", 0.012, 0.36, (ly.x + 0.03, ly.y - 0.02 + s * 0.09, ly.z + 0.04), M_SEAT, verts=6, rot=(math.radians(-14 * s), 0, 0))
cyl("LyreYoke", 0.012, 0.28, (ly.x + 0.03, ly.y - 0.02, ly.z + 0.22), M_SEAT, verts=6, rot=(math.radians(90), 0, 0))
for k in range(5):
    box(f"LyreString{k}", (0.002, 0.002, 0.34), (ly.x + 0.08, ly.y - 0.02 - 0.06 + k * 0.03, ly.z + 0.03), M_GUT)

# ----------------------------------------------------------------------------- the braziers, emptied last night and standing cold
def brazier(name, x, y):
    for k in range(3):
        a = math.radians(30 + 120 * k)
        cyl(f"{name}_Leg{k}", 0.018, 0.56, (x + 0.2 * math.cos(a), y + 0.2 * math.sin(a), 0.28), M_BRONZE, verts=6, rot=(0.25 * math.sin(a), -0.25 * math.cos(a), 0))
    lathe(f"{name}_Bowl", [(0.0, 0.52), (0.12, 0.53), (0.25, 0.60), (0.32, 0.70), (0.33, 0.72), (0.30, 0.715), (0.0, 0.66)], (x, y, 0), M_BRONZE, steps=20)
    lathe(f"{name}_Ash", [(0.0, 0.67), (0.29, 0.70), (0.0, 0.705)], (x, y, 0), M_ASH, steps=12)
brazier("BrazierA", -1.05, -3.5)
brazier("BrazierB", 1.15, 4.2)

# ----------------------------------------------------------------------------- the maids' things: a water jar (for the sprinkling) and a broom, by the doors
lathe("WaterJar", [(0.0, 0.0), (0.09, 0.0), (0.2, 0.16), (0.23, 0.32), (0.2, 0.48), (0.09, 0.58), (0.075, 0.66), (0.10, 0.69), (0.0, 0.69)], (-1.75, -HY + 0.38, 0), M_CLAY, steps=18, jitter=0.01)
torus("WaterJarHandle", 0.07, 0.016, (-1.75 + 0.22, -HY + 0.38, 0.38), M_CLAY, rot=(math.radians(90), 0, math.radians(90)), seg=10, rseg=4)
lathe("SprinkleBowl", [(0.0, 0.0), (0.06, 0.0), (0.15, 0.06), (0.17, 0.1), (0.16, 0.1), (0.0, 0.03)], (-1.35, -HY + 0.55, 0), M_CLAY, steps=16)
cyl("BroomHandle", 0.015, 1.3, (-2.18, -HY + 0.14, 0.72), M_SEAT, verts=6, rot=(math.radians(-8), math.radians(-6), 0))
cyl("BroomTwigs", 0.13, 0.45, (-2.12, -HY + 0.2, 0.2), M_TWIG, verts=10, r2=0.04).scale = (1.0, 0.45, 1.0)

# ----------------------------------------------------------------------------- the porch (where Ulysses slept) and the court
PY0 = -HY - WT                                   # porch back (the hall's outer south face)
plane_xy("PorchFloor", -HX - WT, HX + WT, PORCH_Y1, PY0, 0.0, M_PORCH, nx=4, ny=2)
box("PorchStep", (2 * HX + 2 * WT, 0.4, -CZ), (0, PORCH_Y1 - 0.2, CZ / 2), M_STONE, bevel=0.02)
for s in (-1, 1):                                # the side walls of the porch (antae) and their stone facings
    box(f"Anta{s}", (WT, PY0 - PORCH_Y1, 4.3 - CZ), (s * (HX + WT / 2), (PY0 + PORCH_Y1) / 2, (4.3 + CZ) / 2), M_WALLCORE)
    box(f"AntaFace{s}", (WT + 0.08, 0.3, 4.3 - CZ), (s * (HX + WT / 2), PORCH_Y1 + 0.15, (4.3 + CZ) / 2), M_STONE)
    column(f"PorchCol{s}", (s * 2.3, PORCH_Y1 + 0.45), h_top=3.9, r0=0.19, r1=0.22)
box("PorchBeam", (2 * HX + 2 * WT, 0.4, 0.4), (0, PORCH_Y1 + 0.45, 4.1), M_BEAM)
box("PorchCeiling", (2 * HX + 2 * WT, PY0 - PORCH_Y1, 0.1), (0, (PY0 + PORCH_Y1) / 2, 4.35), M_CEIL)
box("PorchRoof", (2 * HX + 2 * WT + 0.3, PY0 - PORCH_Y1 + 0.5, 0.35), (0, (PY0 + PORCH_Y1) / 2 - 0.2, 4.57), M_ROOF)
# the undressed bullock's hide with fleeces on it, where the stranger slept, by the porch wall
HB = (-3.2, -7.6)
box("SleepHide", (1.0, 2.0, 0.025), (HB[0], HB[1] - 0.2, 0.0125), M_HIDE, bevel=0.01, rot=(0, 0, math.radians(84)))
box("SleepFleece0", (0.8, 1.1, 0.07), (HB[0] + 0.25, HB[1] - 0.25, 0.06), M_FLEECE, bevel=0.03, rot=(0, 0, math.radians(78)))
box("SleepFleece1", (0.7, 0.6, 0.11), (HB[0] - 0.5, HB[1] - 0.15, 0.08), M_FLEECE, bevel=0.04, rot=(0, 0, math.radians(95)))
# the court: beaten earth, its walls with a coping, the gateway opposite, the altar of Jove
plane_xy("CourtGround", -COURT_X - 1.5, COURT_X + 1.5, COURT_Y1 - 1.5, PORCH_Y1, CZ, M_COURT, nx=12, ny=10,
         height=lambda x, y: 0.05 * noise.noise(Vector((x * 0.25, y * 0.25, 0.3))) - 0.04 * max(0.0, 1.0 - abs(abs(x) - 1.2) / 1.0))
CW_H = 3.3
for s in (-1, 1):
    box(f"CourtWall{s}", (0.6, PORCH_Y1 - COURT_Y1 + 0.6, CW_H), (s * (COURT_X + 0.3), (PORCH_Y1 + COURT_Y1) / 2 - 0.3, CZ + CW_H / 2), M_COURTWALL)
    box(f"CourtCoping{s}", (0.75, PORCH_Y1 - COURT_Y1 + 0.75, 0.14), (s * (COURT_X + 0.3), (PORCH_Y1 + COURT_Y1) / 2 - 0.3, CZ + CW_H + 0.07), M_STONE)
    box(f"CourtJoin{s}", (COURT_X - HX - WT + 0.3, 0.6, CW_H), (s * (HX + WT + (COURT_X - HX - WT + 0.3) / 2), PORCH_Y1 + 0.3, CZ + CW_H / 2), M_COURTWALL)
GW = 2.4
for s in (-1, 1):
    box(f"CourtWallS{s}", (COURT_X - GW / 2 + 0.6, 0.6, CW_H), (s * (GW / 2 + (COURT_X - GW / 2 + 0.6) / 2), COURT_Y1 - 0.3, CZ + CW_H / 2), M_COURTWALL)
    box(f"CourtCopingS{s}", (COURT_X - GW / 2 + 0.75, 0.75, 0.14), (s * (GW / 2 + (COURT_X - GW / 2 + 0.6) / 2), COURT_Y1 - 0.3, CZ + CW_H + 0.07), M_STONE)
    box(f"GatePost{s}", (0.5, 0.9, 3.9), (s * (GW / 2 + 0.25), COURT_Y1 - 0.3, CZ + 1.95), M_STONE)
    box(f"GateLeaf{s}", (GW / 2 - 0.05, 0.08, 2.9), (s * GW / 4, COURT_Y1 - 0.55, CZ + 1.5), M_DOOR)   # the gate shut
box("GateLintel", (GW + 1.2, 1.0, 0.4), (0, COURT_Y1 - 0.3, CZ + 4.05), M_STONE)
box("GateRoof", (GW + 1.6, 1.6, 0.25), (0, COURT_Y1 - 0.3, CZ + 4.37), M_ROOF)
# cloister roofs along the court walls (a lean-to on posts each side)
for s in (-1, 1):
    box(f"CloisterRoof{s}", (2.0, PORCH_Y1 - COURT_Y1 - 2.0, 0.18), (s * (COURT_X - 0.9), (PORCH_Y1 + COURT_Y1) / 2 - 0.5, CZ + 2.95), M_ROOF, rot=(0, -s * math.radians(6), 0))
    for k in range(4):
        yy = PORCH_Y1 - 1.6 - k * (PORCH_Y1 - COURT_Y1 - 3.0) / 3
        cyl(f"CloisterPost{s}{k}", 0.11, 2.75, (s * (COURT_X - 1.75), yy, CZ + 1.375), M_COLUMN, verts=10)
# the altar of Jove in the court
AX, AY = 0.9, -15.2
box("Altar", (1.3, 0.95, 0.95), (AX, AY, CZ + 0.475), M_STONE, bevel=0.03)
box("AltarTop", (1.45, 1.1, 0.12), (AX, AY, CZ + 1.0), M_STONE, bevel=0.02)
box("AltarStep", (1.8, 1.5, 0.15), (AX, AY, CZ + 0.05), M_STONE, bevel=0.02)
lathe("AltarAsh", [(0.0, CZ + 1.06), (0.42, CZ + 1.06), (0.2, CZ + 1.12), (0.0, CZ + 1.13)], (AX, AY, 0), M_ASH, steps=12, jitter=0.15)

# weeds and winter grass at the foot of the court walls, thicker in the corners, none on the trodden path
def weed_tufts(name, n_clumps):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rnd = random.Random(11)
    placed = 0; tries = 0
    while placed < n_clumps and tries < n_clumps * 40:
        tries += 1
        side = rnd.random()
        if side < 0.42: x = rnd.choice((-1, 1)) * (COURT_X - rnd.uniform(0.05, 0.6) ** 1.5); y = rnd.uniform(COURT_Y1 + 0.2, PORCH_Y1 - 0.5)
        elif side < 0.62: x = rnd.uniform(-COURT_X + 0.2, COURT_X - 0.2); y = COURT_Y1 + rnd.uniform(0.05, 0.7) ** 1.5
        elif side < 0.8: x = rnd.uniform(-COURT_X + 0.3, COURT_X - 0.3); y = PORCH_Y1 - 0.4 - rnd.uniform(0.0, 0.4)
        else: a = rnd.uniform(0, 2 * math.pi); rr = rnd.uniform(0.9, 1.4); x = AX + rr * math.cos(a); y = AY + rr * math.sin(a) * 0.8
        if abs(x) < 1.6 and side >= 0.42 and side < 0.8: continue
        placed += 1
        nb = rnd.randint(4, 7); hs = rnd.uniform(0.35, 1.0)
        for _ in range(nb):
            p = Vector((x + rnd.uniform(-0.1, 0.1), y + rnd.uniform(-0.1, 0.1), CZ - 0.02))
            h = rnd.uniform(0.12, 0.38) * hs; w = rnd.uniform(0.008, 0.018)
            bend = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized() * h * rnd.uniform(0.2, 0.7)
            sa = rnd.uniform(0, math.pi); sd = Vector((math.cos(sa), math.sin(sa), 0)) * w
            pts = [p + Vector((0, 0, h * t)) + bend * t * t for t in (0.0, 0.5, 1.0)]
            v0 = (bm.verts.new(pts[0] - sd), bm.verts.new(pts[0] + sd)); v1 = (bm.verts.new(pts[1] - sd * 0.6), bm.verts.new(pts[1] + sd * 0.6)); tip = bm.verts.new(pts[2])
            bm.faces.new((v0[0], v0[1], v1[1], v1[0])); bm.faces.new((v1[0], v1[1], tip))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_WEED)
    return link(o)
weed_tufts("CourtWeeds", 170)

# the hills of Ithaca beyond the court wall (backdrop ring, far.*)
def far_ridge(name, r0, r1, seg=72):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); top = []; bot = []; back = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        d = Vector((math.cos(a), math.sin(a), 0))
        hgt = 6.0 + 14.0 * max(0.0, noise.noise(d * 1.6 + Vector((3.3, 1.1, 0.0))) * 0.6 + 0.45) + 4.0 * noise.noise(d * 5.0)
        if d.y < -0.3: hgt *= 1.25                  # higher ground to the south (Neritum's flank)
        top.append(bm.verts.new(d * r0 + Vector((0, 0, max(2.5, hgt)))))
        bot.append(bm.verts.new(d * r0 + Vector((0, 0, CZ - 0.5))))
        back.append(bm.verts.new(d * r1 + Vector((0, 0, max(2.5, hgt) * 0.8))))
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((bot[i], bot[j], top[j], top[i])); bm.faces.new((top[i], top[j], back[j], back[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.dot(Vector((-c.x, -c.y, 0))) < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_FAR)
    for p in me.polygons: p.use_smooth = True
    return link(o)
far_ridge("far.hills", 42.0, 55.0)

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
sky = sky_dome("SkyDome")

# ----------------------------------------------------------------------------- lights (manifest light ids)
def light_obj(name, kind, energy, color, loc, direction=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if direction is not None: lo.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return link(lo)
light_obj("light.sun", 'SUN', 4.2, (1.0, 0.86, 0.68), tuple(SUN_DIR * 30), direction=-SUN_DIR, angle=math.radians(1.2))
sky_l = light_obj("light.sky", 'SUN', 0.2, (0.70, 0.78, 0.95), (0, 0, 14), direction=(0.1, 0.25, -1.0), angle=math.radians(80))
sky_l.data.use_shadow = False
light_obj("light.hearthFire", 'POINT', 170.0, (1.0, 0.55, 0.24), (FIRE.x, FIRE.y, 0.6), shadow_soft_size=0.4)

# world: the same winter-morning sky, render-only (Unity gets the SkyDome mesh)
world = bpy.data.worlds.new("WinterMorning"); scene.world = world; world.use_nodes = True
wnt = world.node_tree; bg = wnt.nodes["Background"]
wtc = wnt.nodes.new("ShaderNodeTexCoord"); wsep = wnt.nodes.new("ShaderNodeSeparateXYZ"); wnt.links.new(wtc.outputs["Generated"], wsep.inputs["Vector"])
wmr = wnt.nodes.new("ShaderNodeMapRange"); wmr.inputs["From Min"].default_value = -0.12; wmr.inputs["From Max"].default_value = 1.0
wnt.links.new(wsep.outputs["Z"], wmr.inputs["Value"])
wr = ramp(wnt, [(0.0, (0.16, 0.14, 0.11, 1)), (0.10, (0.62, 0.64, 0.66, 1)), (0.3, (0.40, 0.50, 0.66, 1)), (1.0, (0.18, 0.28, 0.52, 1))])
wnt.links.new(wmr.outputs["Result"], wr.inputs["Fac"]); wnt.links.new(wr.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.6

# ----------------------------------------------------------------------------- anchors
fwd = (FACE - READER); fwd.z = 0; fwd.normalize()
anchor("reader.entrance", (READER.x, READER.y, 0.0))
look = anchor("reader.look", (READER.x + fwd.x, READER.y + fwd.y, EYE))
anchor("scene.centre", (HEARTH.x, HEARTH.y, 0.0))
anchor("hall.hearth", (HEARTH.x, HEARTH.y, 0.0))
anchor("hall.door", (0.0, -HY - WT / 2, THR_H))
anchor("hall.storeroomDoor", (IDOOR_X, HY, 0.0))
anchor("hall.stair", ((STAIR_X0 + STAIR_X1) / 2, STAIR_Y0, 0.0))
anchor("hall.mixingBowl", (KX, KY, 0.0))
anchor("hall.penelopeChair", (hx - 0.9, hy - 2.35, 0.0))
anchor("porch.hide", (HB[0], HB[1], 0.0))
anchor("court.altar", (AX, AY, CZ))

# the reading page placeholder (render-only, never exported): 0.6 m ahead, 0.4 x 0.55 m, at eye height
PAGE_C = Vector((READER.x, READER.y, EYE - 0.05)) + fwd * 0.6
page = box("PagePreview", (0.4, 0.004, 0.55), tuple(PAGE_C), plain("M_PagePreview", (0.80, 0.76, 0.66), rough=0.9), rot=(0, 0, math.atan2(fwd.y, fwd.x) - math.pi / 2))

# apply every transform so object space == world space (the procedural materials then bake exactly as rendered)
bpy.ops.object.select_all(action='DESELECT')
for o in COLL.objects:
    if o.type == 'MESH': o.select_set(True); bpy.context.view_layer.objects.active = o
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.select_all(action='DESELECT')

# ----------------------------------------------------------------------------- cameras (reader eye 1.55 m)
def camera(name, loc, look_at, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 150; cd.clip_start = 0.05
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co
E = Vector((READER.x, READER.y, EYE))
def yawed(deg, dist=6.0, dz=-0.25):
    a = math.radians(deg); d = Matrix.Rotation(a, 3, 'Z') @ fwd
    return tuple(E + d * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(E), yawed(0, 8.0, -0.35), lens=17),
    camera("Cam_Page", tuple(E), yawed(0, 8.0, -0.35), lens=17),
    camera("Cam_Left", tuple(E), yawed(80, 6.0, -0.35), lens=17),
    camera("Cam_Right", tuple(E), yawed(-80, 6.0, -0.35), lens=17),
    camera("Cam_Behind", tuple(E), yawed(180, 6.0, -0.2), lens=17),
    camera("Cam_Up", tuple(E), (HEARTH.x + 0.3, HEARTH.y - 0.6, 6.4), lens=17),
    camera("Cam_Down", tuple(E), (HX - 0.95, READER.y + 1.5, 0.3), lens=18),
    camera("Cam_Hearth", (hx + 1.5, hy - 2.3, 1.35), (hx - 0.2, hy + 0.2, 0.3), lens=22),
]
EXPOSURE = {"Cam_Behind": 0.1}
PAGE_CAMS = {"Cam_Page"}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "ithaca_hall_source.blend"))

if args.render:
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    want = set(c.strip() for c in args.cams.split(",") if c.strip())
    for c in cams:
        if want and c.name[4:].lower() not in want: continue
        scene.camera = c
        page.hide_render = c.name not in PAGE_CAMS
        scene.view_settings.exposure = EXPOSURE.get(c.name, 0.9)
        scene.render.filepath = os.path.join(OUT, f"render_{c.name[4:].lower()}.png")
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:                      # the shared GPU can run out of memory: fall back to the CPU
            print("GPU render failed, retrying on CPU:", e); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)

# ----------------------------------------------------------------------------- bake + merge + export for Unity
def tri_count(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

KEEP_NAMES = {"M_SkyDome": "SkyDome", "M_FarHills": "far.hills"}        # backdrop meshes keep the names Unity looks for
KEEP_UV = {"SkyDome"}                                                    # its hand-made spherical UVs

def bake_and_export():
    bpy.data.objects.remove(page)
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
    size_for = {"M_Floor": min(4096, T_ * 2), "M_WallPlaster": T_, "M_SkyDome": T_, "M_CeilingReeds": T_ // 2, "M_Beams": T_ // 2,
                "M_CypressPost": T_ // 2, "M_HearthRim": T_ // 2, "M_CourtGround": T_ // 2, "M_WallCore": T_ // 2, "M_CourtWall": T_ // 2,
                "M_TableWood": T_ // 2, "M_SeatWood": T_ // 2, "M_PurpleCover": T_ // 2, "M_DoorOak": T_ // 2, "M_Limestone": T_ // 2,
                "M_PorchStone": T_ // 2, "M_Ash": T_ // 4, "M_Bronze": T_ // 4, "M_RoofClay": T_ // 4, "M_FarHills": T_ // 4, "M_AshThreshold": T_ // 4,
                "M_Fleece": T_ // 4, "M_Terracotta": T_ // 4, "M_Charwood": T_ // 4, "M_Hide": T_ // 4, "M_Embers": T_ // 8, "M_Weeds": T_ // 8}
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
            try:
                bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            except RuntimeError as e:                  # shared GPU out of memory: bake this pass on the CPU instead
                print("GPU bake failed, retrying on CPU:", e); scene.cycles.device = 'CPU'
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
    gl = os.path.join(OUT, "ithaca_hall.gltf")
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False)
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={tex_sizes.get(o.name, 0)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "ithaca_hall_baked.blend"))

# pre-export budget (printed every run so the budget is visible while iterating)
_dg = bpy.context.evaluated_depsgraph_get(); _cat = {}
for _o in [o for o in COLL.objects if o.type == 'MESH' and o.name != "PagePreview"]:
    _e = _o.evaluated_get(_dg); _me = _e.to_mesh(); _t = sum(len(p.vertices) - 2 for p in _me.polygons); _e.to_mesh_clear()
    _k = _o.data.materials[0].name if _o.data.materials else "?"
    _cat[_k] = _cat.get(_k, 0) + _t
print(f"PRE-MERGE materials={len(_cat)} tris={sum(_cat.values())}")
for _k, _v in sorted(_cat.items(), key=lambda kv: -kv[1]): print(f"  BUDGET {_k:24s} {_v}")

if args.bake or args.export:
    bake_and_export()
print("DONE")
