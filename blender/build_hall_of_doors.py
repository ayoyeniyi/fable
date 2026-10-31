"""
Fable: Hall of Doors (Alice's Adventures in Wonderland, chapter I).

Builds the environment procedurally in Blender, with PBR materials and lamp lighting,
then (by flag) renders Cycles preview stills, bakes materials to textures, merges meshes
by material and exports a GLB for Unity.

Run headless:
  blender -b -P blender/build_hall_of_doors.py -- --out build/hall --render --bake --export
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector

# ----------------------------------------------------------------------------- args
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/hall")
ap.add_argument("--render", action="store_true")
ap.add_argument("--bake", action="store_true")
ap.add_argument("--export", action="store_true")
ap.add_argument("--samples", type=int, default=160)
ap.add_argument("--res", type=int, default=1600)
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--quick", action="store_true", help="low samples for iteration")
args = ap.parse_args(argv)
OUT = os.path.abspath(args.out)
os.makedirs(OUT, exist_ok=True)
random.seed(1865)

# ----------------------------------------------------------------------------- dimensions (metres)
HALL_L, HALL_W, HALL_H = 14.0, 4.2, 2.65     # "a long, low hall"
WAINSCOT_H = 0.95
LITTLE_DOOR_H = 0.381                         # fifteen inches
TABLE_H = 0.72
LAMP_Z = 1.95                                 # lamp flame height

# ----------------------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24 if args.quick else args.samples
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.transmission_bounces = 8
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
scene.view_settings.exposure = -0.05

COLL = bpy.data.collections.new("HallOfDoors")
scene.collection.children.link(COLL)

def link(obj):
    COLL.objects.link(obj)
    return obj

# ----------------------------------------------------------------------------- material helpers
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
    mid = tuple((b + l) / 2 for b, l in zip(base, light))
    lite = tuple((m + l) / 2 for m, l in zip(mid, light))
    r = ramp(nt, [(0.0, (*dark, 1)), (0.2, (*base, 1)), (0.5, (*mid, 1)), (0.72, (*lite, 1)), (0.9, (*base, 1))], (-450, 100))
    nt.links.new(mix.outputs[0], r.inputs["Fac"])
    # wear: pointiness lifts edges, dust in crevices via AO
    geo = node(nt, "ShaderNodeNewGeometry", (-700, -350))
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-700, -550)); ao.inputs["Distance"].default_value = 0.15
    pr = ramp(nt, [(0.48, (0, 0, 0, 1)), (0.56, (1, 1, 1, 1))], (-450, -350))
    nt.links.new(geo.outputs["Pointiness"], pr.inputs["Fac"])
    wear = node(nt, "ShaderNodeMix", (-150, 100), data_type='RGBA', blend_type='MIX')
    nt.links.new(pr.outputs["Color"], wear.inputs["Factor"])
    nt.links.new(r.outputs["Color"], wear.inputs[6])
    wear.inputs[7].default_value = (light[0] * 1.1, light[1] * 1.1, light[2] * 1.05, 1)
    dust = node(nt, "ShaderNodeMix", (50, 100), data_type='RGBA', blend_type='MULTIPLY')
    dust.inputs["Factor"].default_value = 0.35
    nt.links.new(wear.outputs[2], dust.inputs[6])
    nt.links.new(ao.outputs["Color"], dust.inputs[7])
    nt.links.new(dust.outputs[2], b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", (-150, -200))
    rr.inputs["From Min"].default_value, rr.inputs["From Max"].default_value = 0.0, 1.0
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough[1], rough[0]
    nt.links.new(wave.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    bump = node(nt, "ShaderNodeBump", (50, -300)); bump.inputs["Strength"].default_value = 0.45; bump.inputs["Distance"].default_value = 0.003
    nt.links.new(mix.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Coat Weight"].default_value = 0.15
    b.inputs["Coat Roughness"].default_value = 0.3
    return m

def painted_wood(name, paint=(0.12, 0.2, 0.14)):
    m = wood(name, base=paint, dark=tuple(c * 0.55 for c in paint), light=tuple(min(1, c * 1.25) for c in paint), rough=(0.3, 0.5), grain_dir=(14, 1, 1), bands='X')
    return m

def brass(name="M_Brass", color=(0.83, 0.58, 0.22), rough=(0.18, 0.45)):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = 1.0
    mp = texcoord_obj(nt)
    n1 = node(nt, "ShaderNodeTexNoise", (-900, 0)); n1.inputs["Scale"].default_value = 90; n1.inputs["Detail"].default_value = 6
    nt.links.new(mp.outputs["Vector"], n1.inputs["Vector"])
    n2 = node(nt, "ShaderNodeTexNoise", (-900, -250)); n2.inputs["Scale"].default_value = 7; n2.inputs["Detail"].default_value = 3
    nt.links.new(mp.outputs["Vector"], n2.inputs["Vector"])
    mix = node(nt, "ShaderNodeMix", (-600, 0), data_type='FLOAT'); mix.inputs["Factor"].default_value = 0.5
    nt.links.new(n1.outputs["Fac"], mix.inputs[2]); nt.links.new(n2.outputs["Fac"], mix.inputs[3])
    rr = node(nt, "ShaderNodeMapRange", (-350, 0))
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough
    nt.links.new(mix.outputs[0], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    # tarnish darkens crevices
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-600, -500)); ao.inputs["Distance"].default_value = 0.05
    tar = node(nt, "ShaderNodeMix", (-100, 200), data_type='RGBA', blend_type='MIX')
    tar.inputs["Factor"].default_value = 0.55
    tar.inputs[6].default_value = (*color, 1); tar.inputs[7].default_value = (color[0] * 0.45, color[1] * 0.35, color[2] * 0.25, 1)
    inv = node(nt, "ShaderNodeInvert", (-350, -500)); nt.links.new(ao.outputs["Color"], inv.inputs["Color"])
    nt.links.new(inv.outputs["Color"], tar.inputs["Factor"])
    nt.links.new(tar.outputs[2], b.inputs["Base Color"])
    bump = node(nt, "ShaderNodeBump", (0, -300)); bump.inputs["Strength"].default_value = 0.06; bump.inputs["Distance"].default_value = 0.001
    nt.links.new(n1.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def stone_floor(name="M_StoneFloor"):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    brick = node(nt, "ShaderNodeTexBrick", (-1000, 200))
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.012
    brick.inputs["Mortar Smooth"].default_value = 0.3
    brick.inputs["Bias"].default_value = 0.0
    brick.inputs["Brick Width"].default_value = 0.9
    brick.inputs["Row Height"].default_value = 0.6
    brick.offset = 0.5; brick.offset_frequency = 2
    brick.inputs["Color1"].default_value = (0.42, 0.40, 0.36, 1)
    brick.inputs["Color2"].default_value = (0.30, 0.29, 0.27, 1)
    brick.inputs["Mortar"].default_value = (0.10, 0.09, 0.08, 1)
    nt.links.new(mp.outputs["Vector"], brick.inputs["Vector"])
    grit = node(nt, "ShaderNodeTexNoise", (-1000, -150)); grit.inputs["Scale"].default_value = 35; grit.inputs["Detail"].default_value = 9; grit.inputs["Roughness"].default_value = 0.75
    nt.links.new(mp.outputs["Vector"], grit.inputs["Vector"])
    stain = node(nt, "ShaderNodeTexNoise", (-1000, -400)); stain.inputs["Scale"].default_value = 0.6; stain.inputs["Detail"].default_value = 2
    nt.links.new(mp.outputs["Vector"], stain.inputs["Vector"])
    sr = ramp(nt, [(0.35, (0.55, 0.52, 0.47, 1)), (0.65, (1, 1, 1, 1))], (-700, -400))
    nt.links.new(stain.outputs["Fac"], sr.inputs["Fac"])
    m1 = node(nt, "ShaderNodeMix", (-600, 200), data_type='RGBA', blend_type='MULTIPLY'); m1.inputs["Factor"].default_value = 0.45
    nt.links.new(brick.outputs["Color"], m1.inputs[6])
    gr = ramp(nt, [(0.3, (0.7, 0.7, 0.68, 1)), (0.7, (1.1, 1.08, 1.05, 1))], (-700, -150))
    nt.links.new(grit.outputs["Fac"], gr.inputs["Fac"]); nt.links.new(gr.outputs["Color"], m1.inputs[7])
    m2 = node(nt, "ShaderNodeMix", (-350, 200), data_type='RGBA', blend_type='MULTIPLY'); m2.inputs["Factor"].default_value = 1.0
    nt.links.new(m1.outputs[2], m2.inputs[6]); nt.links.new(sr.outputs["Color"], m2.inputs[7])
    nt.links.new(m2.outputs[2], b.inputs["Base Color"])
    # polished centre walk, rougher edges: roughness from grit, lifted in mortar
    rr = node(nt, "ShaderNodeMapRange", (-350, -100)); rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = 0.45, 0.85
    nt.links.new(grit.outputs["Fac"], rr.inputs["Value"])
    rmix = node(nt, "ShaderNodeMix", (-100, -100), data_type='FLOAT')
    nt.links.new(brick.outputs["Fac"], rmix.inputs["Factor"]); nt.links.new(rr.outputs["Result"], rmix.inputs[2]); rmix.inputs[3].default_value = 0.95
    nt.links.new(rmix.outputs[0], b.inputs["Roughness"])
    # height: mortar recessed, grit bumps
    hmix = node(nt, "ShaderNodeMix", (-350, -600), data_type='FLOAT'); hmix.inputs["Factor"].default_value = 0.15
    inv = node(nt, "ShaderNodeInvert", (-600, -600)); nt.links.new(brick.outputs["Fac"], inv.inputs["Color"])
    nt.links.new(inv.outputs["Color"], hmix.inputs[2]); nt.links.new(grit.outputs["Fac"], hmix.inputs[3])
    bump = node(nt, "ShaderNodeBump", (0, -400)); bump.inputs["Strength"].default_value = 0.6; bump.inputs["Distance"].default_value = 0.01
    nt.links.new(hmix.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def plaster(name="M_Plaster", color=(0.60, 0.54, 0.43)):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    n = node(nt, "ShaderNodeTexNoise", (-900, 0)); n.inputs["Scale"].default_value = 18; n.inputs["Detail"].default_value = 10; n.inputs["Roughness"].default_value = 0.65
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    s = node(nt, "ShaderNodeTexNoise", (-900, -300)); s.inputs["Scale"].default_value = 0.8; s.inputs["Detail"].default_value = 3
    nt.links.new(mp.outputs["Vector"], s.inputs["Vector"])
    r = ramp(nt, [(0.3, (color[0] * 0.78, color[1] * 0.74, color[2] * 0.7, 1)), (0.7, (*color, 1))], (-600, -300))
    nt.links.new(s.outputs["Fac"], r.inputs["Fac"])
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-600, -600)); ao.inputs["Distance"].default_value = 0.4
    soot = node(nt, "ShaderNodeMix", (-300, -300), data_type='RGBA', blend_type='MULTIPLY'); soot.inputs["Factor"].default_value = 0.6
    nt.links.new(r.outputs["Color"], soot.inputs[6]); nt.links.new(ao.outputs["Color"], soot.inputs[7])
    nt.links.new(soot.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.92
    bump = node(nt, "ShaderNodeBump", (0, -200)); bump.inputs["Strength"].default_value = 0.35; bump.inputs["Distance"].default_value = 0.004
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def velvet(name="M_Velvet", color=(0.36, 0.04, 0.05)):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Sheen Weight"].default_value = 1.0
    b.inputs["Sheen Roughness"].default_value = 0.35
    b.inputs["Sheen Tint"].default_value = (0.9, 0.55, 0.5, 1)
    mp = texcoord_obj(nt)
    weave = node(nt, "ShaderNodeTexWave", (-900, 0), wave_type='BANDS', bands_direction='X')
    weave.inputs["Scale"].default_value = 90; weave.inputs["Distortion"].default_value = 0.8
    nt.links.new(mp.outputs["Vector"], weave.inputs["Vector"])
    n = node(nt, "ShaderNodeTexNoise", (-900, -300)); n.inputs["Scale"].default_value = 3; n.inputs["Detail"].default_value = 4
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    r = ramp(nt, [(0.35, (color[0] * 0.6, color[1] * 0.6, color[2] * 0.6, 1)), (0.7, (*color, 1))], (-600, -300))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    bump = node(nt, "ShaderNodeBump", (0, -200)); bump.inputs["Strength"].default_value = 0.06; bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(weave.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def glass(name="M_Glass", tint=(0.86, 0.95, 0.9), rough=0.03):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (*tint, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.5
    # a few smudges
    mp = texcoord_obj(nt)
    n = node(nt, "ShaderNodeTexNoise", (-900, 0)); n.inputs["Scale"].default_value = 12; n.inputs["Detail"].default_value = 4
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    rr = node(nt, "ShaderNodeMapRange", (-500, 0)); rr.inputs["From Min"].default_value = 0.55; rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough, 0.22
    nt.links.new(n.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    m.blend_method = 'BLEND'
    return m

def paper(name="M_Paper"):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (0.93, 0.88, 0.76, 1)
    b.inputs["Roughness"].default_value = 0.95
    b.inputs["Subsurface Weight"].default_value = 0.2
    b.inputs["Subsurface Radius"].default_value = (0.2, 0.15, 0.1)
    mp = texcoord_obj(nt)
    n = node(nt, "ShaderNodeTexNoise", (-900, 0)); n.inputs["Scale"].default_value = 200; n.inputs["Detail"].default_value = 3
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    bump = node(nt, "ShaderNodeBump", (0, -200)); bump.inputs["Strength"].default_value = 0.1; bump.inputs["Distance"].default_value = 0.0003
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def ink(name="M_Ink"):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (0.02, 0.015, 0.012, 1)
    b.inputs["Roughness"].default_value = 0.6
    return m

def flame(name="M_Flame"):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (1, 0.6, 0.2, 1)
    b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.22, 1)
    b.inputs["Emission Strength"].default_value = 7.0
    return m

def lamp_glass(name="M_LampGlass"):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (1, 0.97, 0.9, 1)
    b.inputs["Roughness"].default_value = 0.08
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.45
    b.inputs["Alpha"].default_value = 0.45
    b.inputs["Roughness"].default_value = 0.25
    m.blend_method = 'BLEND'
    return m

def liquid(name="M_Liquid"):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (0.75, 0.25, 0.15, 1)
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.33
    m.blend_method = 'BLEND'
    return m

M_OAK = wood("M_OakPanel", base=(0.20, 0.115, 0.055), dark=(0.055, 0.03, 0.016), light=(0.36, 0.22, 0.11), scale=1.1, rough=(0.3, 0.55))
M_DOOR_OAK = wood("M_DoorOak", base=(0.19, 0.105, 0.05), dark=(0.05, 0.025, 0.012), light=(0.34, 0.2, 0.1), scale=1.4, grain_dir=(14, 1, 1), bands='X')
M_DOOR_MAHOG = wood("M_DoorMahogany", base=(0.20, 0.065, 0.04), dark=(0.06, 0.02, 0.012), light=(0.33, 0.13, 0.08), scale=1.3, grain_dir=(14, 1, 1), bands='X')
M_DOOR_GREEN = painted_wood("M_DoorGreen", (0.075, 0.13, 0.095))
M_DOOR_BLACK = painted_wood("M_DoorBlack", (0.03, 0.03, 0.035))
M_DOOR_BLUE = painted_wood("M_DoorBlue", (0.06, 0.085, 0.14))
M_BEAM = wood("M_Beam", base=(0.14, 0.08, 0.04), dark=(0.035, 0.018, 0.008), light=(0.26, 0.15, 0.07), scale=0.7, rough=(0.55, 0.8))
M_BRASS = brass()
M_GOLD = brass("M_Gold", color=(1.0, 0.76, 0.33), rough=(0.12, 0.3))
M_STONE = stone_floor()
M_PLASTER = plaster()
M_VELVET = velvet()
M_GLASS = glass()
M_PAPER = paper()
M_INK = ink()
M_FLAME = flame()
M_LAMPGLASS = lamp_glass()
M_LIQUID = liquid()

DOOR_MATS = [M_DOOR_OAK, M_DOOR_MAHOG, M_DOOR_GREEN, M_DOOR_BLACK, M_DOOR_BLUE, M_DOOR_OAK, M_DOOR_MAHOG]

# ----------------------------------------------------------------------------- geometry helpers
def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0), smooth=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = 2; md.limit_method = 'ANGLE'; md.harden_normals = False
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def cyl(name, r, h, loc, mat, verts=24, rot=(0, 0, 0), r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    md = o.modifiers.new("Bevel", 'BEVEL'); md.width = min(0.004, r * 0.2); md.segments = 2; md.limit_method = 'ANGLE'
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def sphere(name, r, loc, mat, seg=24, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def torus(name, R, r, loc, mat, rot=(0, 0, 0), seg=32, rseg=12):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=rseg, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def lathe(name, profile, loc, mat, steps=32):
    """profile: list of (radius, z) from bottom to top; revolve around Z."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for i in range(steps):
            a = 2 * math.pi * i / steps
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        rings.append(ring)
    for a, b_ in zip(rings, rings[1:]):
        for i in range(steps):
            j = (i + 1) % steps
            bm.faces.new((a[i], a[j], b_[j], b_[i]))
    # caps
    if profile[0][0] > 1e-5: bm.faces.new(list(reversed(rings[0])))
    if profile[-1][0] > 1e-5: bm.faces.new(rings[-1])
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def text_mesh(name, body, size, loc, mat, rot=(math.pi / 2, 0, 0), extrude=0.0003, align='CENTER'):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body; cu.size = size; cu.extrude = extrude; cu.align_x = align; cu.align_y = 'CENTER'
    o = bpy.data.objects.new(name, cu); o.location = loc; o.rotation_euler = rot
    link(o)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    o.data.materials.append(mat)
    return o

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

DYNAMIC = []   # empties whose children are baked individually and never merged

# ----------------------------------------------------------------------------- room shell
hx, hy = HALL_L / 2, HALL_W / 2
floor = box("Floor", (HALL_L + 0.4, HALL_W + 0.4, 0.1), (0, 0, -0.05), M_STONE)
ceiling = box("Ceiling", (HALL_L + 0.4, HALL_W + 0.4, 0.1), (0, 0, HALL_H + 0.05), M_PLASTER)
T = 0.15
box("Wall_N", (HALL_L + 0.4, T, HALL_H), (0, hy + T / 2, HALL_H / 2), M_PLASTER)
box("Wall_S", (HALL_L + 0.4, T, HALL_H), (0, -hy - T / 2, HALL_H / 2), M_PLASTER)
box("Wall_E", (T, HALL_W + 0.4, HALL_H), (hx + T / 2, 0, HALL_H / 2), M_PLASTER)
box("Wall_W", (T, HALL_W + 0.4, HALL_H), (-hx - T / 2, 0, HALL_H / 2), M_PLASTER)

# wainscot (oak panelling) along both long walls and ends, with rail and skirting
def wainscot_run(name, length, centre, along_x=True, gap=None):
    if along_x:
        yoff = 0.012 if centre[1] < 0 else -0.012
        x0, x1 = centre[0] - length / 2, centre[0] + length / 2
        segments = [(x0, x1)] if gap is None else [(x0, gap[0]), (gap[1], x1)]
        for k, (a, b_) in enumerate(segments):
            box(f"{name}_Panel{k}", (b_ - a, 0.03, WAINSCOT_H), ((a + b_) / 2, centre[1], WAINSCOT_H / 2), M_OAK)
            box(f"{name}_Skirt{k}", (b_ - a, 0.05, 0.14), ((a + b_) / 2, centre[1] + yoff, 0.07), M_OAK, bevel=0.003)
        box(f"{name}_Rail", (length, 0.06, 0.05), (centre[0], centre[1] + (0.02 if centre[1] < 0 else -0.02), WAINSCOT_H + 0.025), M_OAK, bevel=0.004)
        n = int(length / 0.62)
        for i in range(n):
            x = x0 + (i + 0.5) * (length / n)
            if gap and gap[0] - 0.05 < x < gap[1] + 0.05: continue
            box(f"{name}_Stile{i}", (0.07, 0.025, WAINSCOT_H - 0.2), (x, centre[1] + yoff, WAINSCOT_H / 2 + 0.05), M_OAK, bevel=0.003)
        if gap:
            for gx in gap:
                box(f"{name}_GapStile{gx:.2f}", (0.07, 0.025, WAINSCOT_H - 0.2), (gx + (0.035 if gx == gap[0] else -0.035) * -1, centre[1] + yoff, WAINSCOT_H / 2 + 0.05), M_OAK, bevel=0.003)
    else:
        box(f"{name}_Panel", (0.03, length, WAINSCOT_H), (centre[0], centre[1], WAINSCOT_H / 2), M_OAK)
        box(f"{name}_Rail", (0.06, length, 0.05), (centre[0] + (0.02 if centre[0] < 0 else -0.02), centre[1], WAINSCOT_H + 0.025), M_OAK, bevel=0.004)
        box(f"{name}_Skirt", (0.05, length, 0.14), (centre[0] + (0.012 if centre[0] < 0 else -0.012), centre[1], 0.07), M_OAK, bevel=0.003)

wainscot_run("Wainscot_N", HALL_L, (0, hy - 0.015))
CURTAIN_X = 3.9
LD_W = 0.26
wainscot_run("Wainscot_S", HALL_L, (0, -hy + 0.015), gap=(CURTAIN_X - LD_W / 2 - 0.12, CURTAIN_X + LD_W / 2 + 0.12))
wainscot_run("Wainscot_E", HALL_W, (hx - 0.015, 0), along_x=False)
wainscot_run("Wainscot_W", HALL_W, (-hx + 0.015, 0), along_x=False)
# cornice and ceiling beams
box("Cornice_N", (HALL_L, 0.08, 0.1), (0, hy - 0.04, HALL_H - 0.05), M_PLASTER, bevel=0.01)
box("Cornice_S", (HALL_L, 0.08, 0.1), (0, -hy + 0.04, HALL_H - 0.05), M_PLASTER, bevel=0.01)
for i in range(7):
    x = -hx + (i + 0.5) * HALL_L / 7
    box(f"Beam{i}", (0.18, HALL_W, 0.22), (x, 0, HALL_H - 0.11), M_BEAM, bevel=0.008)

# ----------------------------------------------------------------------------- doors ("doors all round the hall, but they were all locked")
def make_door(name, w, h, pos, yaw, mat, panels=4, knob_side=1):
    """Door in a frame, closed. pos = centre of the threshold on the wall plane, yaw = facing direction into the hall."""
    objs = []
    cz = math.cos(yaw); sz = math.sin(yaw)
    def place(local, size, m, nm, bevel=0.0):
        # local x along the wall, local y out of the wall into the hall, local z up
        wx = pos[0] + local[0] * cz - local[1] * sz
        wy = pos[1] + local[0] * sz + local[1] * cz
        objs.append(box(f"{name}_{nm}", size, (wx, wy, local[2]), m, bevel=bevel, rot=(0, 0, yaw)))
    ft = min(0.11, w * 0.12); fd = min(0.16, w * 0.17)
    place((-(w / 2 + ft / 2), fd / 2 - 0.04, h / 2), (ft, fd, h), mat, "FrameL", 0.006)
    place(((w / 2 + ft / 2), fd / 2 - 0.04, h / 2), (ft, fd, h), mat, "FrameR", 0.006)
    place((0, fd / 2 - 0.04, h + ft / 2), (w + 2 * ft, fd, ft), mat, "FrameTop", 0.006)
    place((0, 0.02, h / 2), (w, 0.045, h), mat, "Leaf", 0.003)
    rows = panels // 2
    ph = (h - 0.12 * (rows + 1)) / rows
    pw = (w - 0.12 * 3) / 2
    for r in range(rows):
        for c in range(2):
            px = -w / 2 + 0.12 + pw / 2 + c * (pw + 0.12)
            pz = 0.12 + ph / 2 + r * (ph + 0.12)
            place((px, 0.045, pz), (pw, 0.02, ph), mat, f"Panel{r}{c}", 0.008)
    # brass knob, escutcheon, keyhole
    kx = knob_side * (w / 2 - 0.09)
    wx = pos[0] + kx * cz - 0.07 * sz; wy = pos[1] + kx * sz + 0.07 * cz
    objs.append(cyl(f"{name}_KnobStem", min(0.012, w * 0.013), 0.06 * min(1, w), (wx, wy, h * 0.47), M_BRASS, rot=(math.pi / 2, 0, yaw)))
    wx2 = pos[0] + kx * cz - 0.105 * sz; wy2 = pos[1] + kx * sz + 0.105 * cz
    objs.append(sphere(f"{name}_Knob", min(0.032, w * 0.035), (wx2, wy2, h * 0.47), M_BRASS, scale=(1, 1, 0.8)))
    wx3 = pos[0] + kx * cz - 0.046 * sz; wy3 = pos[1] + kx * sz + 0.046 * cz
    objs.append(box(f"{name}_Escutcheon", (min(0.07, w * 0.075), 0.004, min(0.18, w * 0.19)), (wx3, wy3, h * 0.45), M_BRASS, bevel=0.002, rot=(0, 0, yaw)))
    return objs

doors = []
# five doors on each long wall, one on each end wall; varied heights and widths
xs = [-5.2, -2.6, 0.2, 2.9, 5.4]
for i, x in enumerate(xs):
    w, h = random.uniform(0.82, 0.98), random.uniform(1.95, 2.25)
    doors += make_door(f"DoorN{i}", w, h, (x + random.uniform(-0.15, 0.15), hy), math.pi, DOOR_MATS[i % len(DOOR_MATS)], panels=random.choice([4, 6]), knob_side=random.choice([-1, 1]))
for i, x in enumerate(xs):
    w, h = random.uniform(0.82, 0.98), random.uniform(1.95, 2.25)
    doors += make_door(f"DoorS{i}", w, h, (-x + random.uniform(-0.15, 0.15), -hy), 0.0, DOOR_MATS[(i + 3) % len(DOOR_MATS)], panels=random.choice([4, 6]), knob_side=random.choice([-1, 1]))
doors += make_door("DoorE", 1.0, 2.3, (hx, 0.3), math.pi / 2, M_DOOR_BLACK, panels=6)
# the way Alice came in: an arched dark passage at the west end instead of a door
box("Passage_Dark", (0.6, 1.2, 2.1), (-hx - 0.3, -0.6, 1.05), M_INK)
box("PassageArch_L", (0.1, 0.12, 2.1), (-hx + 0.02, -0.6 - 0.62, 1.05), M_OAK, bevel=0.006)
box("PassageArch_R", (0.1, 0.12, 2.1), (-hx + 0.02, -0.6 + 0.62, 1.05), M_OAK, bevel=0.006)
box("PassageArch_T", (0.1, 1.36, 0.14), (-hx + 0.02, -0.6, 2.17), M_OAK, bevel=0.006)

# ----------------------------------------------------------------------------- the low curtain and the little door
curtain_rod = cyl("CurtainRod", 0.012, 1.3, (CURTAIN_X, -hy + 0.11, 0.86), M_BRASS, rot=(0, math.pi / 2, 0))
sphere("CurtainFinialL", 0.025, (CURTAIN_X - 0.66, -hy + 0.11, 0.86), M_BRASS)
sphere("CurtainFinialR", 0.025, (CURTAIN_X + 0.66, -hy + 0.11, 0.86), M_BRASS)
# curtain: a subdivided plane with sinusoidal folds and a heavier hem
def make_curtain(name, w, h, loc):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    nx, nz = 60, 24
    grid = []
    for i in range(nx + 1):
        col = []
        u = i / nx
        for j in range(nz + 1):
            v = j / nz
            x = -w / 2 + u * w
            folds = 0.035 * math.sin(u * 2 * math.pi * 7 + 0.3) * (0.4 + 0.6 * (1 - v))
            folds += 0.012 * math.sin(u * 2 * math.pi * 19) * (1 - v)
            y = folds + 0.02 * (1 - v) ** 2
            z = v * h + 0.004 * math.sin(u * 2 * math.pi * 7) * (1 - v)
            col.append(bm.verts.new((x, y, z)))
        grid.append(col)
    for i in range(nx):
        for j in range(nz):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; me.materials.append(M_VELVET)
    for p in me.polygons: p.use_smooth = True
    sol = o.modifiers.new("Solidify", 'SOLIDIFY'); sol.thickness = 0.006
    return link(o)
curtain = make_curtain("Curtain", 1.24, 0.80, (CURTAIN_X, -hy + 0.125, 0.03))
# brass rings
_rings = [torus(f"CurtainRing{i}", 0.022, 0.003, (CURTAIN_X - 0.6 + i * 0.15, -hy + 0.11, 0.86), M_BRASS, rot=(0, math.pi / 2, 0), seg=20, rseg=8) for i in range(9)]
DYNAMIC.append(group("prop.curtain", [curtain] + _rings, (CURTAIN_X, -hy + 0.125, 0.0)))
# little door behind the curtain (15 inches high), own tiny frame, brass knob, keyhole
little = make_door("LittleDoor", LD_W, LITTLE_DOOR_H, (CURTAIN_X, -hy), 0.0, M_DOOR_OAK, panels=2, knob_side=1)
_leaf = [o for o in little if any(k in o.name for k in ("Leaf", "Panel", "Knob", "Escutcheon"))]
DYNAMIC.append(group("door.little", _leaf, (CURTAIN_X - LD_W / 2, -hy + 0.02, 0.0)))
# the opening itself: a boolean cut through the wall (applied at export, cutter never exported)
_wall_s = bpy.data.objects["Wall_S"]
_cutter = box("LittleDoor_Cutter", (LD_W, 0.6, LITTLE_DOOR_H), (CURTAIN_X, -hy, LITTLE_DOOR_H / 2), M_PLASTER)
_cutter.hide_render = True; _cutter.display_type = 'WIRE'
_bool = _wall_s.modifiers.new("LittleDoorHole", 'BOOLEAN'); _bool.operation = 'DIFFERENCE'; _bool.object = _cutter
# garden beyond: a bright emissive card and a short passage "not much larger than a rat-hole"
for nm, size, loc in [("LittlePassage_Floor", (LD_W + 0.06, 0.62, 0.03), (CURTAIN_X, -hy - 0.31, -0.015)),
                      ("LittlePassage_Ceil", (LD_W + 0.06, 0.62, 0.03), (CURTAIN_X, -hy - 0.31, LITTLE_DOOR_H + 0.015)),
                      ("LittlePassage_L", (0.03, 0.62, LITTLE_DOOR_H), (CURTAIN_X - LD_W / 2 - 0.015, -hy - 0.31, LITTLE_DOOR_H / 2)),
                      ("LittlePassage_R", (0.03, 0.62, LITTLE_DOOR_H), (CURTAIN_X + LD_W / 2 + 0.015, -hy - 0.31, LITTLE_DOOR_H / 2))]:
    box(nm, size, loc, M_PLASTER)
garden_mat, gnt, gb = new_mat("M_GardenGlow")
gb.inputs["Base Color"].default_value = (0.55, 0.8, 0.45, 1)
gb.inputs["Emission Color"].default_value = (0.75, 0.95, 0.6, 1)
gb.inputs["Emission Strength"].default_value = 6.0
DYNAMIC.append(group("fx.garden-glow", [box("GardenCard", (0.26, 0.01, LITTLE_DOOR_H - 0.02), (CURTAIN_X, -hy - 0.62, LITTLE_DOOR_H / 2), garden_mat)], (CURTAIN_X, -hy - 0.62, LITTLE_DOOR_H / 2)))

# ----------------------------------------------------------------------------- the three-legged glass table, key, bottle
TX, TY = 0.9, 0.15
table_top = cyl("TableTop", 0.27, 0.025, (TX, TY, TABLE_H - 0.0125), M_GLASS, verts=64)
tt = table_top.modifiers["Bevel"]; tt.width = 0.008; tt.segments = 4
leg_profile = [(0.045, 0.0), (0.05, 0.012), (0.028, 0.03), (0.022, 0.12), (0.03, 0.2), (0.022, 0.28), (0.02, 0.42), (0.032, 0.5), (0.02, 0.56), (0.024, TABLE_H - 0.03)]
_legs = [lathe(f"TableLeg{i}", leg_profile, (TX + 0.17 * math.cos(math.radians(90 + i * 120)), TY + 0.17 * math.sin(math.radians(90 + i * 120)), 0.0), M_GLASS) for i in range(3)]
DYNAMIC.append(group("prop.glass-table", [table_top] + _legs, (TX, TY, 0.0)))
# tiny golden key (6 cm)
KX, KY, KZ = TX - 0.06, TY + 0.05, TABLE_H + 0.004
key_bow = torus("Key_Bow", 0.011, 0.0028, (KX - 0.022, KY, KZ), M_GOLD, rot=(0, 0, 0), seg=24, rseg=8)
key_shaft = cyl("Key_Shaft", 0.0025, 0.044, (KX, KY, KZ), M_GOLD, rot=(0, math.pi / 2, 0), verts=12)
_kb1 = box("Key_Bit1", (0.006, 0.0025, 0.009), (KX + 0.018, KY, KZ - 0.005), M_GOLD, bevel=0.0005)
_kb2 = box("Key_Bit2", (0.004, 0.0025, 0.006), (KX + 0.009, KY, KZ - 0.0035), M_GOLD, bevel=0.0005)
DYNAMIC.append(group("prop.golden-key", [key_bow, key_shaft, _kb1, _kb2], (KX, KY, KZ)))
# the DRINK ME bottle (12 cm) with cork and paper label
BX, BY = TX + 0.08, TY - 0.04
bottle_profile = [(0.0, 0.0), (0.024, 0.0), (0.027, 0.004), (0.028, 0.03), (0.028, 0.06), (0.024, 0.075), (0.012, 0.085), (0.009, 0.095), (0.009, 0.112), (0.0115, 0.114), (0.0115, 0.12), (0.0, 0.12)]
bottle = lathe("Bottle", bottle_profile, (BX, BY, TABLE_H), M_GLASS, steps=40)
liquid_profile = [(0.0, 0.004), (0.023, 0.004), (0.026, 0.03), (0.026, 0.055), (0.0, 0.055)]
bottle_liquid = lathe("Bottle_Liquid", liquid_profile, (BX, BY, TABLE_H), M_LIQUID, steps=40)
cork = cyl("Cork", 0.0085, 0.022, (BX, BY, TABLE_H + 0.125), wood("M_Cork", base=(0.62, 0.46, 0.28), dark=(0.4, 0.28, 0.15), light=(0.75, 0.6, 0.4), scale=6, rough=(0.8, 0.95)), verts=20, r2=0.0095)
# label: a slightly curved paper band facing the reader, text "DRINK ME"
label = lathe("Label", [(0.0285, 0.028), (0.0285, 0.06)], (BX, BY, TABLE_H), M_PAPER, steps=40)
# trim the label to a front-facing band by deleting back faces
bpy.ops.object.select_all(action='DESELECT'); label.select_set(True); bpy.context.view_layer.objects.active = label
bpy.ops.object.mode_set(mode='EDIT'); bm = bmesh.from_edit_mesh(label.data)
for f in bm.faces:
    c = f.calc_center_median()
    f.select = (c.y > -0.012)  # keep faces around -Y (towards the hall's south, where the reader stands)
bmesh.update_edit_mesh(label.data)
bpy.ops.mesh.delete(type='FACE'); bpy.ops.object.mode_set(mode='OBJECT')
label_thread = torus("Label_String", 0.0105, 0.0006, (BX, BY, TABLE_H + 0.098), M_PAPER, seg=24, rseg=6)
text = text_mesh("Label_Text", "DRINK\nME", 0.0115, (BX, BY - 0.0292, TABLE_H + 0.044), M_INK, rot=(math.pi / 2, 0, 0), extrude=0.00015)
text.data.materials.clear(); text.data.materials.append(M_INK)
DYNAMIC.append(group("prop.drink-me-bottle", [bottle, bottle_liquid, cork, label, label_thread, text], (BX, BY, TABLE_H)))

# ----------------------------------------------------------------------------- anchors (names are the manifest's anchor ids)
anchor("reader.entrance", (-5.5, -0.6, 0.0))
anchor("reader.table", (TX, TY - 0.85, 0.0))
anchor("reader.curtain", (CURTAIN_X, -hy + 1.0, 0.0))
anchor("table.top", (TX, TY, TABLE_H))
anchor("table.beside", (TX + 0.7, TY, 0.0))
anchor("curtain.front", (CURTAIN_X, -hy + 0.5, 0.0))
anchor("door.little", (CURTAIN_X, -hy, LITTLE_DOOR_H / 2))
anchor("hall.centre", (0.0, 0.0, 0.0))
anchor("hall.ceiling", (0.0, 0.0, LAMP_Z))

# ----------------------------------------------------------------------------- lamps: "lit up by a row of lamps hanging from the roof"
LAMP_XS = [-5.6, -3.7, -1.85, 0.0, 1.85, 3.7, 5.6]
lamp_lights = []
for i, x in enumerate(LAMP_XS):
    # chain + ceiling rose
    cyl(f"Lamp{i}_Rose", 0.07, 0.025, (x, 0, HALL_H - 0.0125), M_BRASS)
    cyl(f"Lamp{i}_Chain", 0.006, HALL_H - LAMP_Z - 0.66, (x, 0, (HALL_H + LAMP_Z + 0.66) / 2), M_BRASS, verts=10)
    # brass font (oil reservoir) and gallery
    lathe(f"Lamp{i}_Font", [(0.0, LAMP_Z - 0.02), (0.05, LAMP_Z - 0.02), (0.075, LAMP_Z + 0.02), (0.07, LAMP_Z + 0.09), (0.035, LAMP_Z + 0.12), (0.03, LAMP_Z + 0.15), (0.045, LAMP_Z + 0.155), (0.045, LAMP_Z + 0.17), (0.0, LAMP_Z + 0.17)], (x, 0, 0), M_BRASS)
    lathe(f"Lamp{i}_Shade", [(0.17, LAMP_Z + 0.27), (0.17, LAMP_Z + 0.275), (0.09, LAMP_Z + 0.34), (0.04, LAMP_Z + 0.37), (0.04, LAMP_Z + 0.39), (0.0, LAMP_Z + 0.39)], (x, 0, 0), M_BRASS)
    lathe(f"Lamp{i}_SmokeBell", [(0.0, LAMP_Z + 0.62), (0.075, LAMP_Z + 0.62), (0.09, LAMP_Z + 0.64), (0.0, LAMP_Z + 0.66)], (x, 0, 0), M_BRASS)
    # glass chimney
    lathe(f"Lamp{i}_Chimney", [(0.03, LAMP_Z + 0.17), (0.042, LAMP_Z + 0.21), (0.036, LAMP_Z + 0.3), (0.024, LAMP_Z + 0.42)], (x, 0, 0), M_LAMPGLASS)
    # flame
    sphere(f"Lamp{i}_Flame", 0.012, (x, 0, LAMP_Z + 0.2), M_FLAME, seg=12, scale=(1, 1, 1.8))
    # light
    ld = bpy.data.lights.new(f"Lamp{i}_Light", 'POINT')
    ld.energy = random.uniform(68, 76)                     # watts, warm oil flame under a brass shade
    ld.color = (1.0, 0.70, 0.42)
    ld.shadow_soft_size = 0.06
    lo = bpy.data.objects.new(f"Lamp{i}_Light", ld); lo.location = (x, 0, LAMP_Z + 0.2); link(lo)
    lamp_lights.append(lo)
# cool fill from the little door's garden
gl = bpy.data.lights.new("GardenLight", 'SPOT'); gl.energy = 160; gl.color = (0.7, 0.9, 1.0); gl.spot_size = math.radians(70); gl.shadow_soft_size = 0.1
glo = bpy.data.objects.new("GardenLight", gl); glo.location = (CURTAIN_X, -hy - 0.55, 0.25); glo.rotation_euler = (math.radians(-85), 0, 0); link(glo)

# world: near-black with a whisper of dust haze (render only)
world = bpy.data.worlds.new("Hall"); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]; bg.inputs["Color"].default_value = (0.03, 0.02, 0.013, 1); bg.inputs["Strength"].default_value = 1
vs = wn.nodes.new("ShaderNodeVolumeScatter"); vs.inputs["Density"].default_value = 0.025; vs.inputs["Anisotropy"].default_value = 0.4
wn.links.new(vs.outputs["Volume"], wn.nodes["World Output"].inputs["Volume"])

# ----------------------------------------------------------------------------- cameras for preview stills (reader eye height 1.62 m)
def camera(name, loc, look_at, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    d = Vector(look_at) - Vector(loc)
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return co
cams = [
    camera("Cam_Entrance", (-6.4, -0.9, 1.62), (2.0, 0.1, 1.1), lens=22),
    camera("Cam_Table", (0.25, -0.55, 1.05), (TX, TY, TABLE_H + 0.05), lens=40),
    camera("Cam_Curtain", (CURTAIN_X - 0.9, -0.6, 0.75), (CURTAIN_X, -hy, 0.3), lens=32),
    camera("Cam_Lamps", (2.5, 1.3, 1.5), (-2.0, 0, 2.1), lens=28),
]

# save the art-direction .blend before any baking destroys procedural materials
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "hall_of_doors_source.blend"))

# ----------------------------------------------------------------------------- render
if args.render:
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    curtain_grp = bpy.data.objects["prop.curtain"]; door_grp = bpy.data.objects["door.little"]
    for c in cams:
        opened = c.name == "Cam_Curtain"
        if opened:
            curtain_grp.location.x -= 0.95; door_grp.rotation_euler.z = math.radians(78)
        scene.camera = c
        scene.render.filepath = os.path.join(OUT, f"render_{c.name[4:].lower()}{'_open' if opened else ''}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)
        if opened:
            curtain_grp.location.x += 0.95; door_grp.rotation_euler.z = 0

# ----------------------------------------------------------------------------- bake + merge + export for Unity
def bake_and_export():
    # strip render-only things
    wn.links.remove(wn.links[-1]) if False else None
    for l in list(wn.links):
        if l.to_socket.name == "Volume": wn.links.remove(l)
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    # apply modifiers everywhere
    for o in meshes:
        o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.data.objects.remove(bpy.data.objects["LittleDoor_Cutter"])
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    # group static meshes by material; dynamic members (children of prop/door/fx empties) stay separate
    dynamic_members = [o for o in meshes if o.parent is not None]
    groups = {}
    for o in meshes:
        if o.parent is not None or not o.data.materials: continue
        groups.setdefault(o.data.materials[0].name, []).append(o)
    merged = []
    for mname, objs in groups.items():
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active; o.name = "MESH_" + mname[2:]
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    scene.cycles.samples = 1
    scene.render.bake.margin = 6
    scene.render.bake.use_selected_to_active = False
    size_for = {"M_StoneFloor": args.tex * 2, "M_Plaster": args.tex, "M_OakPanel": args.tex, "M_Beam": args.tex // 2}
    small = {"M_Gold", "M_Ink", "M_Paper", "M_Flame", "M_Cork", "M_Liquid", "M_LampGlass", "M_GardenGlow"}
    # dynamic members sharing a material would share one node tree; give each its own copy so the bake is per object
    for o in dynamic_members:
        m = o.data.materials[0]
        if m.users > 1:
            m2 = m.copy(); m2.name = m.name + "__" + o.name; o.data.materials[0] = m2
    for o in merged + dynamic_members:
        m = o.data.materials[0]; nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        base = m.name.split("__")[0]
        size = size_for.get(base, args.tex // 4 if base in small else args.tex // 2)
        if o.parent is not None: size = args.tex // 2 if o.name in ("Curtain", "LittleDoor_Leaf", "TableTop") else args.tex // 8
        size = max(size, 64)
        # UVs
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
        bpy.ops.object.mode_set(mode='OBJECT')
        baked = {}
        for pass_name, btype, extra, noncolor in [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]:
            img = bpy.data.images.new(f"T_{m.name[2:].replace('__', '_')}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; nt.nodes.active = tex
            tex.select = True
            bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            img.filepath_raw = os.path.join(OUT, "textures", img.name + ".png"); os.makedirs(os.path.dirname(img.filepath_raw), exist_ok=True)
            img.file_format = 'PNG'; img.save(); img.pack()
            baked[pass_name] = tex
            print("baked", img.name, size)
        # rebuild simple material from baked maps, keep scalar params
        metallic = bsdf.inputs["Metallic"].default_value
        trans = bsdf.inputs["Transmission Weight"].default_value
        emis = bsdf.inputs["Emission Strength"].default_value
        ecol = tuple(bsdf.inputs["Emission Color"].default_value)
        alpha = bsdf.inputs["Alpha"].default_value
        ior = bsdf.inputs["IOR"].default_value
        for n in list(nt.nodes):
            if n not in baked.values(): nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
        nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Base Color"])
        nt.links.new(baked["Roughness"].outputs["Color"], nb.inputs["Roughness"])
        nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(baked["Normal"].outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], nb.inputs["Normal"])
        nb.inputs["Metallic"].default_value = metallic
        nb.inputs["Transmission Weight"].default_value = trans
        nb.inputs["IOR"].default_value = ior
        nb.inputs["Alpha"].default_value = alpha if trans < 0.5 else 0.25
        nb.inputs["Emission Strength"].default_value = emis
        nb.inputs["Emission Color"].default_value = ecol
        if trans > 0.5 or alpha < 1: m.blend_method = 'BLEND'
    # remove cameras from export, keep lights
    for c in cams: bpy.data.objects.remove(c)
    glb = os.path.join(OUT, "hall_of_doors.gltf")   # .gltf + textures/: Unity imports the images as compressed (ASTC) textures; embedded GLB images import uncompressed
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='AUTO', export_lights=True, export_cameras=False)
    allm = merged + dynamic_members
    tris = sum(len(o.data.polygons) for o in allm)
    verts = sum(len(o.data.vertices) for o in allm)
    print(f"EXPORT {glb} meshes={len(allm)} verts={verts} faces={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(allm)}\nverts={verts}\nfaces={tris}\n")
        for o in allm: f.write(f"{o.name} verts={len(o.data.vertices)} faces={len(o.data.polygons)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "hall_of_doors_baked.blend"))

if args.bake or args.export:
    bake_and_export()
print("DONE")
