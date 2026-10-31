"""
Fable: the lobby. A small panelled reading room where the app opens: a tall bookcase on the far wall with the four
books standing face out on a display shelf at chest height (Odyssey, Gulliver, Alice, Oz, oldest first), their
covers from content/covers (sources in content/covers/SOURCE.md). The reader points at a book and pinches to open it.

Builds the room procedurally with PBR materials and lamp light, then (by flag) renders Cycles stills, bakes materials
to textures, merges static meshes by material and exports a .gltf + textures for Unity. The four books stay separate
nodes named book.<slug> (cover art unbaked: the cover JPEG is the texture) so Unity can find, light and move them.

Run headless:
  blender -b -P blender/build_lobby.py -- --out out/lobby --render --bake --export
"""
import bpy, bmesh, math, random, sys, os, argparse, shutil
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/lobby")
ap.add_argument("--render", action="store_true")
ap.add_argument("--bake", action="store_true")
ap.add_argument("--export", action="store_true")
ap.add_argument("--samples", type=int, default=160)
ap.add_argument("--res", type=int, default=1600)
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--quick", action="store_true", help="low samples for iteration")
args = ap.parse_args(argv)
OUT = os.path.abspath(args.out)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COVERS = os.path.join(ROOT, "content", "covers")
os.makedirs(OUT, exist_ok=True)
random.seed(2026)

# ----------------------------------------------------------------------------- dimensions (metres)
SHELF_T = 0.03
ROOM_W, ROOM_D, ROOM_H = 5.6, 5.0, 3.0          # x across, y deep (shelf wall at +y), z up
WAINSCOT_H = 1.0
CASE_W, CASE_D, CASE_H = 3.3, 0.40, 2.62        # the bookcase on the north wall
DISPLAY_Z = 1.02                                # the display ledge the four books stand on
BOOK_W, BOOK_H, BOOK_T = 0.35, 0.525, 0.065       # the four books: large folios, easy to point at from 2 m
BOOK_LEAN = math.radians(13)
SHELF_ORDER = ["odyssey", "gulliver", "alice", "oz"]   # oldest first, left to right
BOOK_XS = [-1.14, -0.38, 0.38, 1.14]
CLOTH = {"odyssey": (0.10, 0.12, 0.20), "gulliver": (0.26, 0.07, 0.05), "alice": (0.08, 0.18, 0.11), "oz": (0.30, 0.22, 0.06)}

# ----------------------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24 if args.quick else args.samples
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
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
scene.view_settings.exposure = 0.2

COLL = bpy.data.collections.new("Lobby")
scene.collection.children.link(COLL)
def link(obj):
    COLL.objects.link(obj); return obj

# ----------------------------------------------------------------------------- material helpers
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

def texcoord_obj(nt, loc=(-1400, 0)):
    tc = node(nt, "ShaderNodeTexCoord", loc); mp = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    return mp

def wood(name, base=(0.32, 0.17, 0.08), dark=(0.09, 0.045, 0.02), light=(0.55, 0.33, 0.15), scale=1.0, rough=(0.35, 0.6), grain_dir=(1, 1, 14), bands='Z', coat=0.15):
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
    r = ramp(nt, [(0.0, (*dark, 1)), (0.2, (*base, 1)), (0.5, (*mid, 1)), (0.72, (*lite, 1)), (0.9, (*base, 1))], (-450, 100))
    nt.links.new(mix.outputs[0], r.inputs["Fac"])
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-700, -550)); ao.inputs["Distance"].default_value = 0.12
    dust = node(nt, "ShaderNodeMix", (50, 100), data_type='RGBA', blend_type='MULTIPLY'); dust.inputs["Factor"].default_value = 0.3
    nt.links.new(r.outputs["Color"], dust.inputs[6]); nt.links.new(ao.outputs["Color"], dust.inputs[7])
    nt.links.new(dust.outputs[2], b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", (-150, -200))
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough[1], rough[0]
    nt.links.new(wave.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    bump = node(nt, "ShaderNodeBump", (50, -300)); bump.inputs["Strength"].default_value = 0.35; bump.inputs["Distance"].default_value = 0.003
    nt.links.new(mix.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.3
    return m

def floorboards(name="M_Floorboards"):
    """Oak boards 14 cm wide running away from the reader, each board its own tone, with dark seams."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1400, 0))
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    # board index across x; a per-board offset along y staggers the butt joints
    div = node(nt, "ShaderNodeMath", (-1200, 100), operation='DIVIDE'); div.inputs[1].default_value = 0.14
    nt.links.new(sep.outputs["X"], div.inputs[0])
    fl = node(nt, "ShaderNodeMath", (-1000, 100), operation='FLOOR'); nt.links.new(div.outputs[0], fl.inputs[0])
    fr = node(nt, "ShaderNodeMath", (-1000, 250), operation='FRACT'); nt.links.new(div.outputs[0], fr.inputs[0])
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-800, 100), noise_dimensions='1D'); nt.links.new(fl.outputs[0], wn.inputs["W"])
    seam = ramp(nt, [(0.0, (0, 0, 0, 1)), (0.03, (1, 1, 1, 1)), (0.97, (1, 1, 1, 1)), (1.0, (0, 0, 0, 1))], (-800, 300))
    nt.links.new(fr.outputs[0], seam.inputs["Fac"])
    tone = ramp(nt, [(0.0, (0.20, 0.10, 0.045, 1)), (0.5, (0.30, 0.16, 0.07, 1)), (1.0, (0.38, 0.21, 0.10, 1))], (-600, 100))
    nt.links.new(wn.outputs["Value"], tone.inputs["Fac"])
    # grain along y
    mp = texcoord_obj(nt, (-1600, -400)); mp.inputs["Scale"].default_value = (14, 1.2, 1)
    wave = node(nt, "ShaderNodeTexWave", (-1000, -300), wave_type='BANDS', bands_direction='X')
    wave.inputs["Scale"].default_value = 2.0; wave.inputs["Distortion"].default_value = 7.0; wave.inputs["Detail"].default_value = 5
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    grain = node(nt, "ShaderNodeMix", (-350, 0), data_type='RGBA', blend_type='MULTIPLY'); grain.inputs["Factor"].default_value = 0.35
    nt.links.new(tone.outputs["Color"], grain.inputs[6]); nt.links.new(wave.outputs["Color"], grain.inputs[7])
    seams = node(nt, "ShaderNodeMix", (-150, 0), data_type='RGBA', blend_type='MULTIPLY'); seams.inputs["Factor"].default_value = 0.85
    nt.links.new(grain.outputs[2], seams.inputs[6]); nt.links.new(seam.outputs["Color"], seams.inputs[7])
    nt.links.new(seams.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.42; b.inputs["Coat Weight"].default_value = 0.25; b.inputs["Coat Roughness"].default_value = 0.25
    bump = node(nt, "ShaderNodeBump", (50, -300)); bump.inputs["Strength"].default_value = 0.5; bump.inputs["Distance"].default_value = 0.002
    nt.links.new(seam.outputs["Color"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def plaster(name="M_Plaster", color=(0.52, 0.44, 0.33)):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt); mp.inputs["Scale"].default_value = (3, 3, 3)
    n = node(nt, "ShaderNodeTexNoise", (-900, 0)); n.inputs["Scale"].default_value = 4; n.inputs["Detail"].default_value = 10; n.inputs["Roughness"].default_value = 0.6
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    r = ramp(nt, [(0.3, (color[0] * 0.85, color[1] * 0.85, color[2] * 0.82, 1)), (0.7, (*color, 1))], (-600, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85
    return m

def brass(name="M_Brass", color=(0.83, 0.58, 0.22)):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Metallic"].default_value = 1.0; b.inputs["Roughness"].default_value = 0.3
    return m

def flat(name, color, rough=0.6, metallic=0.0, emission=None, strength=0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1); b.inputs["Emission Strength"].default_value = strength
    return m

def velvet(name="M_Velvet", color=(0.30, 0.05, 0.06)):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = 0.8
    b.inputs["Sheen Weight"].default_value = 0.8; b.inputs["Sheen Tint"].default_value = (1.0, 0.75, 0.7, 1)
    return m

def leather_spines(name="M_Spines"):
    """Book spines on the filler shelves: the colour comes from each book's 'tone' colour attribute."""
    m, nt, b = new_mat(name)
    at = node(nt, "ShaderNodeAttribute", (-700, 0), attribute_name="tone")
    n = node(nt, "ShaderNodeTexNoise", (-700, -250)); n.inputs["Scale"].default_value = 90; n.inputs["Detail"].default_value = 6
    mul = node(nt, "ShaderNodeMix", (-300, 0), data_type='RGBA', blend_type='MULTIPLY'); mul.inputs["Factor"].default_value = 0.25
    nt.links.new(at.outputs["Color"], mul.inputs[6]); nt.links.new(n.outputs["Color"], mul.inputs[7])
    nt.links.new(mul.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.55
    return m

def rug(name="M_Rug"):
    """A worn Turkey carpet: madder field, indigo border, a lozenge medallion."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1400, 0))
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    def centred(axis, loc):
        s = node(nt, "ShaderNodeMath", loc, operation='SUBTRACT'); s.inputs[1].default_value = 0.5
        nt.links.new(sep.outputs[axis], s.inputs[0])
        a = node(nt, "ShaderNodeMath", (loc[0] + 150, loc[1]), operation='ABSOLUTE'); nt.links.new(s.outputs[0], a.inputs[0])
        return a
    ax, ay = centred("X", (-1200, 100)), centred("Y", (-1200, -100))
    mx = node(nt, "ShaderNodeMath", (-850, 0), operation='MAXIMUM'); nt.links.new(ax.outputs[0], mx.inputs[0]); nt.links.new(ay.outputs[0], mx.inputs[1])
    border = ramp(nt, [(0.0, (0, 0, 0, 1)), (0.40, (0, 0, 0, 1)), (0.405, (1, 1, 1, 1)), (0.47, (1, 1, 1, 1)), (0.475, (0, 0, 0, 1))], (-650, 0))
    nt.links.new(mx.outputs[0], border.inputs["Fac"])
    ad = node(nt, "ShaderNodeMath", (-850, -250), operation='ADD'); nt.links.new(ax.outputs[0], ad.inputs[0]); nt.links.new(ay.outputs[0], ad.inputs[1])
    lozenge = ramp(nt, [(0.0, (1, 1, 1, 1)), (0.18, (1, 1, 1, 1)), (0.185, (0, 0, 0, 1)), (0.22, (0, 0, 0, 1)), (0.225, (0.5, 0.5, 0.5, 1)), (0.26, (0.5, 0.5, 0.5, 1)), (0.265, (0, 0, 0, 1))], (-650, -250))
    nt.links.new(ad.outputs[0], lozenge.inputs["Fac"])
    field = (0.36, 0.07, 0.05, 1); indigo = (0.06, 0.08, 0.20, 1); gold = (0.62, 0.45, 0.18, 1)
    c1 = node(nt, "ShaderNodeMix", (-400, 0), data_type='RGBA'); c1.inputs[6].default_value = field; c1.inputs[7].default_value = indigo
    nt.links.new(border.outputs["Color"], c1.inputs["Factor"])
    c2 = node(nt, "ShaderNodeMix", (-200, 0), data_type='RGBA'); c2.inputs[7].default_value = gold
    nt.links.new(c1.outputs[2], c2.inputs[6]); nt.links.new(lozenge.outputs["Color"], c2.inputs["Factor"])
    wear = node(nt, "ShaderNodeTexNoise", (-400, -300)); wear.inputs["Scale"].default_value = 40; wear.inputs["Detail"].default_value = 8
    w = node(nt, "ShaderNodeMix", (0, 0), data_type='RGBA', blend_type='MULTIPLY'); w.inputs["Factor"].default_value = 0.35
    nt.links.new(c2.outputs[2], w.inputs[6]); nt.links.new(wear.outputs["Color"], w.inputs[7])
    nt.links.new(w.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95; b.inputs["Sheen Weight"].default_value = 0.5
    return m

def cover_mat(slug):
    """The cover painting: the JPEG itself, never baked (it ships as its own texture)."""
    m, nt, b = new_mat("M_Cover_" + slug)
    tex = node(nt, "ShaderNodeTexImage", (-400, 0)); tex.image = bpy.data.images.load(os.path.join(COVERS, slug + ".jpg"))
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.5; b.inputs["Coat Weight"].default_value = 0.2
    return m

M_FLOOR = floorboards()
M_PLASTER = plaster()
M_CEILING = plaster("M_Ceiling", (0.62, 0.56, 0.46))
M_PANEL = wood("M_OakPanel", base=(0.24, 0.12, 0.05), dark=(0.07, 0.035, 0.015), light=(0.42, 0.24, 0.11))
M_CASE = wood("M_Bookcase", base=(0.16, 0.075, 0.035), dark=(0.05, 0.022, 0.01), light=(0.30, 0.15, 0.07), coat=0.3)
M_BEAM = wood("M_Beam", base=(0.13, 0.07, 0.035), dark=(0.04, 0.02, 0.01), light=(0.24, 0.13, 0.06), grain_dir=(14, 1, 1), bands='X')
M_BRASS = brass()
M_GILT = brass("M_Gilt", (0.75, 0.55, 0.22))
M_VELVET = velvet()
M_RUG = rug()
M_SPINES = leather_spines()
M_PAPER = flat("M_Paper", (0.80, 0.74, 0.60), rough=0.85)
M_SHADE = flat("M_Shade", (0.85, 0.66, 0.40), rough=0.7, emission=(1.0, 0.72, 0.40), strength=1.5)
M_FLAME = flat("M_Flame", (1, 0.8, 0.5), emission=(1.0, 0.62, 0.25), strength=30)
M_NIGHT = flat("M_WindowNight", (0.02, 0.03, 0.06), rough=0.1, emission=(0.10, 0.16, 0.32), strength=1.2)
M_CLOTH = {s: flat("M_Cloth_" + s, c, rough=0.75) for s, c in CLOTH.items()}
M_COVER = {s: cover_mat(s) for s in SHELF_ORDER}

# ----------------------------------------------------------------------------- geometry helpers
def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = 1; md.limit_method = 'ANGLE'
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def cyl(name, r, h, loc, mat, verts=24, rot=(0, 0, 0), r2=None):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def lathe(name, profile, loc, mat, steps=24):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for (r, z) in profile:
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / steps), r * math.sin(2 * math.pi * i / steps), z)) for i in range(steps)])
    for a, b_ in zip(rings, rings[1:]):
        for i in range(steps):
            j = (i + 1) % steps; bm.faces.new((a[i], a[j], b_[j], b_[i]))
    if profile[0][0] > 1e-5: bm.faces.new(list(reversed(rings[0])))
    if profile[-1][0] > 1e-5: bm.faces.new(rings[-1])
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def sphere(name, r, loc, mat, seg=12, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(scale=True); o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def group(name, objs, loc, rot=(0, 0, 0)):
    """Parent objs under a named empty (a glTF node Unity can find by name)."""
    e = bpy.data.objects.new(name, None); e.empty_display_size = 0.05; e.location = loc; e.rotation_euler = rot; link(e)
    bpy.context.view_layer.update()
    for o in objs: o.parent = e; o.matrix_parent_inverse = e.matrix_world.inverted()
    return e

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

def tone(o, rgb):
    attr = o.data.color_attributes.new("tone", 'FLOAT_COLOR', 'POINT')
    for d in attr.data: d.color = (*rgb, 1)

# ----------------------------------------------------------------------------- room shell
hx, hy = ROOM_W / 2, ROOM_D / 2
box("Floor", (ROOM_W + 0.3, ROOM_D + 0.3, 0.1), (0, 0, -0.05), M_FLOOR)
box("Ceiling", (ROOM_W + 0.3, ROOM_D + 0.3, 0.1), (0, 0, ROOM_H + 0.05), M_CEILING)
T = 0.15
for nm, size, loc in [("Wall_N", (ROOM_W + 0.3, T, ROOM_H), (0, hy + T / 2, ROOM_H / 2)), ("Wall_S", (ROOM_W + 0.3, T, ROOM_H), (0, -hy - T / 2, ROOM_H / 2)),
                      ("Wall_W", (T, ROOM_D + 0.3, ROOM_H), (-hx - T / 2, 0, ROOM_H / 2))]:
    box(nm, size, loc, M_PLASTER)
# east wall with a window opening (1.3 wide, sill 0.9, head 2.4) built from four pieces
WIN_Y, WIN_W, WIN_Z0, WIN_Z1 = 0.6, 1.3, 0.9, 2.4
ex = hx + T / 2
box("Wall_E_a", (T, (WIN_Y - WIN_W / 2) + hy + 0.15, ROOM_H), (ex, (-hy - 0.15 + WIN_Y - WIN_W / 2) / 2, ROOM_H / 2), M_PLASTER)
box("Wall_E_b", (T, hy + 0.15 - (WIN_Y + WIN_W / 2), ROOM_H), (ex, (hy + 0.15 + WIN_Y + WIN_W / 2) / 2, ROOM_H / 2), M_PLASTER)
box("Wall_E_sill", (T, WIN_W, WIN_Z0), (ex, WIN_Y, WIN_Z0 / 2), M_PLASTER)
box("Wall_E_head", (T, WIN_W, ROOM_H - WIN_Z1), (ex, WIN_Y, (ROOM_H + WIN_Z1) / 2), M_PLASTER)
# the window: night sky beyond glazing bars
box("WindowSky", (0.02, WIN_W, WIN_Z1 - WIN_Z0), (ex + 0.06, WIN_Y, (WIN_Z0 + WIN_Z1) / 2), M_NIGHT)
for i in range(3):
    y = WIN_Y - WIN_W / 2 + WIN_W * (i + 1) / 4
    box(f"WindowBar_V{i}", (0.04, 0.03, WIN_Z1 - WIN_Z0), (ex - 0.02, y, (WIN_Z0 + WIN_Z1) / 2), M_BEAM)
for i in range(2):
    z = WIN_Z0 + (WIN_Z1 - WIN_Z0) * (i + 1) / 3
    box(f"WindowBar_H{i}", (0.04, WIN_W, 0.03), (ex - 0.02, WIN_Y, z), M_BEAM)
box("WindowSillBoard", (0.26, WIN_W + 0.2, 0.04), (hx - 0.05, WIN_Y, WIN_Z0 - 0.02), M_PANEL)
for s in (-1, 1):
    box(f"WindowJamb{s}", (0.2, 0.05, WIN_Z1 - WIN_Z0 + 0.1), (hx - 0.03, WIN_Y + s * (WIN_W / 2 + 0.025), (WIN_Z0 + WIN_Z1) / 2), M_PANEL)

# wainscot: raised oak panels below a rail, skirting at the floor (not behind the bookcase)
def wainscot(name, length, centre, along_x, normal_sign, skip=None):
    n = max(1, int(length / 0.75)); pw = length / n
    ax = 0 if along_x else 1
    def pos(t, off, z):
        p = [0, 0, z]; p[ax] = (centre[ax] - length / 2) + t; p[1 - ax] = centre[1 - ax] + normal_sign * off
        return tuple(p)
    def size(l, d, h):
        s = [0, 0, h]; s[ax] = l; s[1 - ax] = d; return tuple(s)
    box(name + "_Back", size(length, 0.02, WAINSCOT_H), pos(length / 2, 0.01, WAINSCOT_H / 2), M_PANEL)
    box(name + "_Rail", size(length, 0.06, 0.06), pos(length / 2, 0.03, WAINSCOT_H), M_PANEL, bevel=0.008)
    box(name + "_Skirt", size(length, 0.03, 0.14), pos(length / 2, 0.025, 0.07), M_PANEL)
    for i in range(n):
        t = pw * (i + 0.5)
        if skip and skip[0] <= (centre[ax] - length / 2) + t <= skip[1]: continue
        box(f"{name}_P{i}", size(pw - 0.14, 0.02, WAINSCOT_H - 0.34), pos(t, 0.03, WAINSCOT_H / 2 + 0.02), M_PANEL, bevel=0.01)
wainscot("Wainscot_S", ROOM_W, (0, -hy), True, +1)
wainscot("Wainscot_W", ROOM_D, (-hx, 0), False, +1)
wainscot("Wainscot_E1", (WIN_Y - WIN_W / 2) + hy, (hx, (-hy + WIN_Y - WIN_W / 2) / 2), False, -1)
wainscot("Wainscot_E2", hy - (WIN_Y + WIN_W / 2), (hx, (hy + WIN_Y + WIN_W / 2) / 2), False, -1)
side = (ROOM_W - CASE_W) / 2
wainscot("Wainscot_NW", side, (-hx + side / 2, hy), True, -1)
wainscot("Wainscot_NE", side, (hx - side / 2, hy), True, -1)
# ceiling beams across the room and a cornice
for i, y in enumerate([-1.25, 0.0, 1.25]):
    box(f"Beam{i}", (ROOM_W, 0.18, 0.22), (0, y, ROOM_H - 0.11), M_BEAM, bevel=0.01)
for nm, size, loc in [("Cornice_N", (ROOM_W, 0.1, 0.1), (0, hy - 0.05, ROOM_H - 0.05)), ("Cornice_S", (ROOM_W, 0.1, 0.1), (0, -hy + 0.05, ROOM_H - 0.05)),
                      ("Cornice_W", (0.1, ROOM_D, 0.1), (-hx + 0.05, 0, ROOM_H - 0.05)), ("Cornice_E", (0.1, ROOM_D, 0.1), (hx - 0.05, 0, ROOM_H - 0.05))]:
    box(nm, size, loc, M_BEAM)

# ----------------------------------------------------------------------------- the bookcase
cy = hy - CASE_D / 2                      # bookcase centre line
front = hy - CASE_D                       # its front face
box("Case_Back", (CASE_W, 0.03, CASE_H), (0, hy - 0.015, CASE_H / 2), M_CASE)
for s in (-1, 1):
    box(f"Case_Side{s}", (0.05, CASE_D, CASE_H), (s * (CASE_W / 2 - 0.025), cy, CASE_H / 2), M_CASE, bevel=0.006)
    box(f"Case_Pilaster{s}", (0.09, 0.03, CASE_H - 0.3), (s * (CASE_W / 2 - 0.045), front - 0.012, CASE_H / 2), M_CASE, bevel=0.008)
box("Case_Top", (CASE_W + 0.12, CASE_D + 0.06, 0.07), (0, cy - 0.03, CASE_H + 0.035), M_CASE, bevel=0.01)
box("Case_Frieze", (CASE_W, 0.03, 0.14), (0, front - 0.012, CASE_H - 0.07), M_CASE)
box("Case_Plinth", (CASE_W + 0.06, CASE_D + 0.03, 0.12), (0, cy - 0.015, 0.06), M_CASE, bevel=0.006)
# middle partitions split the run into three bays
BAYS = [(-CASE_W / 2 + 0.05, -CASE_W / 6), (-CASE_W / 6, CASE_W / 6), (CASE_W / 6, CASE_W / 2 - 0.05)]
FILLER_SHELVES = [0.12, 0.50, 1.84, 2.22]          # shelf tops holding filler books (below and above the display)
# partitions run through the filler shelves only: the display is one open bay so nothing shades a cover
for s in (-1, 1):
    box(f"Case_MidLow{s}", (0.035, CASE_D - 0.03, DISPLAY_Z - 0.045 - 0.12), (s * CASE_W / 6, cy, (DISPLAY_Z - 0.045 + 0.12) / 2), M_CASE)
    box(f"Case_MidHigh{s}", (0.035, CASE_D - 0.03, CASE_H - 0.14 - FILLER_SHELVES[2] + SHELF_T), (s * CASE_W / 6, cy, (CASE_H - 0.14 + FILLER_SHELVES[2] - SHELF_T) / 2), M_CASE)
for z in FILLER_SHELVES[1:] + [CASE_H - 0.14]:
    box(f"Shelf_{z:.2f}", (CASE_W - 0.1, CASE_D - 0.04, SHELF_T), (0, cy, z - SHELF_T / 2), M_CASE, bevel=0.004)
# the display ledge: deeper, with a lip so the books can lean back against the case
box("DisplayLedge", (CASE_W - 0.1, CASE_D + 0.06, 0.045), (0, cy - 0.03, DISPLAY_Z - 0.0225), M_CASE, bevel=0.006)
box("DisplayLip", (CASE_W - 0.1, 0.02, 0.035), (0, front - 0.05, DISPLAY_Z + 0.0175), M_CASE, bevel=0.004)
box("DisplayBacking", (CASE_W - 0.1, 0.02, FILLER_SHELVES[2] - DISPLAY_Z - SHELF_T), (0, hy - 0.04, (DISPLAY_Z + FILLER_SHELVES[2] - SHELF_T) / 2), M_VELVET)

# filler books: spines of many sizes and leathers; a few lean at the end of a run
LEATHERS = [(0.22, 0.05, 0.04), (0.10, 0.13, 0.08), (0.08, 0.09, 0.16), (0.24, 0.15, 0.07), (0.15, 0.06, 0.05), (0.06, 0.06, 0.05),
            (0.30, 0.22, 0.12), (0.12, 0.05, 0.10), (0.18, 0.12, 0.05), (0.32, 0.28, 0.20)]
spine_objs = []; band_objs = []
for zi, z in enumerate(FILLER_SHELVES):
    clear = (FILLER_SHELVES[zi + 1] if zi + 1 < len(FILLER_SHELVES) else CASE_H - 0.14) - SHELF_T - z
    if zi == 1: clear = DISPLAY_Z - 0.045 - z
    for bi, (x0, x1) in enumerate(BAYS):
        x = x0 + 0.03
        while x < x1 - 0.06:
            w = random.uniform(0.022, 0.06); h = min(clear - 0.03, random.uniform(0.62, 0.92) * clear); d = random.uniform(0.17, 0.25)
            if random.random() < 0.06:                         # a gap now and then
                x += random.uniform(0.04, 0.12); continue
            col = random.choice(LEATHERS); col = tuple(c * random.uniform(0.8, 1.2) for c in col)
            o = box(f"Spine_{zi}_{bi}_{len(spine_objs)}", (w, d, h), (x + w / 2, front + 0.02 + d / 2, z + h / 2), M_SPINES)
            tone(o, col); spine_objs.append(o)
            if random.random() < 0.35:                         # gilt bands near the head and tail
                for bz in (z + h * 0.12, z + h * 0.86):
                    band_objs.append(box(f"Band_{len(band_objs)}", (w + 0.002, 0.004, 0.008), (x + w / 2, front + 0.019, bz), M_GILT))
            x += w + random.uniform(0.0, 0.004)
        # a leaning book closes the run
        if x1 - x > 0.08:
            h = clear * 0.8; w = 0.04; lean = math.radians(-18)
            o = box(f"Spine_{zi}_{bi}_lean", (w, 0.2, h), (x + 0.06, front + 0.12, z + h / 2 * math.cos(lean)), M_SPINES, rot=(0, lean, 0))
            tone(o, random.choice(LEATHERS)); spine_objs.append(o)

# ----------------------------------------------------------------------------- the four books, face out
book_groups = {}
for slug, x in zip(SHELF_ORDER, BOOK_XS):
    parts = []
    # boards and page block in the book's own frame: cover faces -y (towards the reader), spine on the left (-x)
    parts.append(box(f"Board_Front_{slug}", (BOOK_W, 0.006, BOOK_H), (0, -BOOK_T / 2 + 0.003, BOOK_H / 2), M_CLOTH[slug], bevel=0.002))
    parts.append(box(f"Board_Back_{slug}", (BOOK_W, 0.006, BOOK_H), (0, BOOK_T / 2 - 0.003, BOOK_H / 2), M_CLOTH[slug], bevel=0.002))
    parts.append(box(f"Spine_{slug}", (0.008, BOOK_T, BOOK_H), (-BOOK_W / 2 + 0.004, 0, BOOK_H / 2), M_CLOTH[slug], bevel=0.002))
    parts.append(box(f"Pages_{slug}", (BOOK_W - 0.012, BOOK_T - 0.012, BOOK_H - 0.012), (0.004, 0, BOOK_H / 2), M_PAPER))
    # the cover art: a plane just proud of the front board, UVs filling the image
    me = bpy.data.meshes.new(f"Cover_{slug}")
    y = -BOOK_T / 2 - 0.0005; hw, hh = BOOK_W / 2 - 0.006, BOOK_H / 2 - 0.006
    me.from_pydata([(-hw, y, BOOK_H / 2 - hh), (hw, y, BOOK_H / 2 - hh), (hw, y, BOOK_H / 2 + hh), (-hw, y, BOOK_H / 2 + hh)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for i, c in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]): uv.data[i].uv = c
    me.materials.append(M_COVER[slug])
    cov = bpy.data.objects.new(f"Cover_{slug}", me); link(cov); parts.append(cov)
    # the book stands on the ledge, leaning back against the velvet; its pivot is the bottom front edge
    g = group(f"book.{slug}", parts, (0, 0, 0))
    # the top of the back board touches the velvet backing
    g.location = (x, hy - 0.05 - BOOK_H * math.sin(BOOK_LEAN) - BOOK_T / 2 * math.cos(BOOK_LEAN), DISPLAY_Z)
    g.rotation_euler = (-BOOK_LEAN, 0, 0)
    book_groups[slug] = g
    anchor(f"shelf.{slug}", (x, front - 0.35, 0.0))

# ----------------------------------------------------------------------------- furniture
# rug where the reader stands
box("Rug", (2.6, 1.8, 0.012), (0, -0.4, 0.006), M_RUG)
# a wing armchair by the window, angled to the room
chair = []
CX, CY, CYAW = 1.75, -1.15, math.radians(35)
chair.append(box("Chair_Seat", (0.62, 0.6, 0.14), (0, 0, 0.42), M_VELVET, bevel=0.03))
chair.append(box("Chair_Base", (0.66, 0.62, 0.3), (0, 0, 0.2), M_VELVET, bevel=0.02))
chair.append(box("Chair_Back", (0.66, 0.14, 0.72), (0, -0.28, 0.84), M_VELVET, bevel=0.04, rot=(math.radians(8), 0, 0)))
for s in (-1, 1):
    chair.append(box(f"Chair_Arm{s}", (0.12, 0.6, 0.2), (s * 0.36, 0.02, 0.6), M_VELVET, bevel=0.03))
    chair.append(box(f"Chair_Wing{s}", (0.1, 0.24, 0.42), (s * 0.34, -0.22, 0.98), M_VELVET, bevel=0.03))
    for fy in (-0.26, 0.26):
        chair.append(cyl(f"Chair_Foot{s}{fy}", 0.025, 0.06, (s * 0.28, fy, 0.03), M_CASE, verts=8))
cg = group("Chair", chair, (0, 0, 0)); cg.location = (CX, CY, 0); cg.rotation_euler = (0, 0, CYAW + math.pi)
# round side table with an oil lamp: the room's main light
TX, TY = 0.95, -1.75
cyl("SideTable_Top", 0.3, 0.03, (TX, TY, 0.66), M_CASE, verts=28)
cyl("SideTable_Pillar", 0.035, 0.56, (TX, TY, 0.37), M_CASE, verts=10)
cyl("SideTable_Foot", 0.18, 0.04, (TX, TY, 0.04), M_CASE, verts=20)
LZ = 0.675
lathe("Lamp0_Font", [(0.0, LZ), (0.07, LZ), (0.075, LZ + 0.02), (0.06, LZ + 0.1), (0.03, LZ + 0.13), (0.035, LZ + 0.16), (0.0, LZ + 0.16)], (TX, TY, 0), M_BRASS)
lathe("Lamp0_Shade", [(0.16, LZ + 0.28), (0.15, LZ + 0.29), (0.06, LZ + 0.44), (0.0, LZ + 0.445)], (TX, TY, 0), M_SHADE)
sphere("Lamp0_Flame", 0.012, (TX, TY, LZ + 0.22), M_FLAME, seg=8, scale=(1, 1, 1.8))
# a book left open on the table, and a stack beside the chair
box("TableBook", (0.22, 0.16, 0.025), (TX - 0.08, TY + 0.12, 0.69), M_PAPER, rot=(0, 0, math.radians(20)))
for i in range(3):
    o = box(f"FloorStack{i}", (0.28 - i * 0.03, 0.2 - i * 0.02, 0.05), (2.3, -0.4, 0.025 + i * 0.05), M_SPINES, rot=(0, 0, math.radians(random.uniform(-12, 12))))
    tone(o, LEATHERS[i * 3])

# a brass picture lamp over each book: they light the four covers
for i, x in enumerate(BOOK_XS):
    cyl(f"Lamp{i + 1}_Arm", 0.008, 0.2, (x, front + 0.06, FILLER_SHELVES[2] - SHELF_T - 0.02), M_BRASS, verts=8, rot=(math.radians(90), 0, 0))
    cyl(f"Lamp{i + 1}_Hood", 0.04, 0.34, (x, front - 0.04, FILLER_SHELVES[2] - SHELF_T - 0.03), M_BRASS, verts=16, rot=(0, math.radians(90), 0))
# wall sconces either side of the bookcase
for i, x in enumerate([-(CASE_W / 2 + 0.55), CASE_W / 2 + 0.55]):
    box(f"Lamp{i + 5}_Plate", (0.1, 0.02, 0.18), (x, hy - 0.01, 1.85), M_BRASS)
    lathe(f"Lamp{i + 5}_Shade", [(0.09, 1.9), (0.085, 1.91), (0.045, 2.04), (0.0, 2.045)], (x, hy - 0.14, 0), M_SHADE)
    cyl(f"Lamp{i + 5}_Arm", 0.008, 0.12, (x, hy - 0.07, 1.86), M_BRASS, verts=8, rot=(math.radians(90), 0, 0))

# ----------------------------------------------------------------------------- lights (names starting "Lamp" are baked in Unity)
def point(name, loc, watts, color=(1.0, 0.72, 0.45), radius=0.05):
    ld = bpy.data.lights.new(name, 'POINT'); ld.energy = watts; ld.color = color; ld.shadow_soft_size = radius
    lo = bpy.data.objects.new(name, ld); lo.location = loc; link(lo); return lo
def spot(name, loc, aim, watts, angle=60, color=(1.0, 0.80, 0.55)):
    ld = bpy.data.lights.new(name, 'SPOT'); ld.energy = watts; ld.color = color; ld.spot_size = math.radians(angle); ld.spot_blend = 0.6; ld.shadow_soft_size = 0.05
    lo = bpy.data.objects.new(name, ld); lo.location = loc; link(lo)
    lo.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return lo
point("Lamp0_Light", (TX, TY, LZ + 0.22), 70)
for i, x in enumerate(BOOK_XS):
    spot(f"Lamp{i + 1}_Light", (x, front - 0.07, FILLER_SHELVES[2] - SHELF_T - 0.06), (x, hy - 0.15, DISPLAY_Z + 0.22), 30, angle=80)
for i, x in enumerate([-(CASE_W / 2 + 0.55), CASE_W / 2 + 0.55]):
    point(f"Lamp{i + 5}_Light", (x, hy - 0.16, 1.96), 22)
moon = bpy.data.lights.new("WindowLight", 'AREA'); moon.energy = 40; moon.color = (0.55, 0.68, 1.0); moon.size = 1.2
mo = bpy.data.objects.new("WindowLight", moon); mo.location = (hx + 0.3, WIN_Y, 1.7); mo.rotation_euler = (0, math.radians(-90), 0); link(mo)

world = bpy.data.worlds.new("Lobby"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.012, 0.02, 1)

# ----------------------------------------------------------------------------- anchors
anchor("reader.entrance", (0.0, -0.9, 0.0))
anchor("lobby.shelf", (0.0, front, DISPLAY_Z + BOOK_H / 2))
anchor("scene.centre", (0.0, 0.0, 0.0))

# ----------------------------------------------------------------------------- cameras (reader eye 1.62 m)
def camera(name, loc, look_at, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co
cams = [
    camera("Cam_Entrance", (0.0, -0.9, 1.62), (0.0, hy, 1.25), lens=20),
    camera("Cam_Shelf", (0.0, 0.6, 1.5), (0.0, hy, 1.22), lens=24),
    camera("Cam_Corner", (-2.2, -2.1, 2.0), (0.8, 1.2, 0.9), lens=18),
]

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "lobby_source.blend"))

if args.render:
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    for c in cams:
        scene.camera = c
        scene.render.filepath = os.path.join(OUT, f"render_{c.name[4:].lower()}.png")
        bpy.ops.render.render(write_still=True); print("rendered", scene.render.filepath)

# ----------------------------------------------------------------------------- bake + merge + export for Unity
def bake_and_export():
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    # the books stay apart (Unity finds and moves them); the chair is static and merges like the rest
    for o in meshes:
        if o.parent is not None and not o.parent.name.startswith("book."):
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    dynamic = [o for o in meshes if o.parent is not None]
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
    size_for = {"M_Floorboards": args.tex, "M_Plaster": args.tex // 2, "M_OakPanel": args.tex, "M_Bookcase": args.tex, "M_Spines": args.tex, "M_Rug": args.tex // 2, "M_Velvet": args.tex // 2}
    for o in dynamic:                                          # one material per book part so each bakes alone
        m = o.data.materials[0]
        if m.users > 1 and not m.name.startswith("M_Cover"):
            m2 = m.copy(); m2.name = m.name + "__" + o.name; o.data.materials[0] = m2
    for o in merged + dynamic:
        m = o.data.materials[0]; nt = m.node_tree
        if m.name.startswith("M_Cover"): continue              # the cover JPEG is the texture
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        base = m.name.split("__")[0]
        size = size_for.get(base, args.tex // 4)
        if o.parent is not None: size = args.tex // 16
        size = max(size, 64)
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
        bpy.ops.object.mode_set(mode='OBJECT')
        baked = {}
        for pass_name, btype, extra, noncolor in [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]:
            img = bpy.data.images.new(f"T_{m.name[2:].replace('__', '_')}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; nt.nodes.active = tex
            bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            img.filepath_raw = os.path.join(OUT, "textures", img.name + ".png"); os.makedirs(os.path.dirname(img.filepath_raw), exist_ok=True)
            img.file_format = 'PNG'; img.save(); img.pack()
            baked[pass_name] = tex
            print("baked", img.name, size)
        metallic = bsdf.inputs["Metallic"].default_value
        emis = bsdf.inputs["Emission Strength"].default_value; ecol = tuple(bsdf.inputs["Emission Color"].default_value)
        for n in list(nt.nodes):
            if n not in baked.values(): nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
        nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Base Color"])
        nt.links.new(baked["Roughness"].outputs["Color"], nb.inputs["Roughness"])
        nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(baked["Normal"].outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], nb.inputs["Normal"])
        nb.inputs["Metallic"].default_value = metallic
        nb.inputs["Emission Strength"].default_value = min(emis, 4.0); nb.inputs["Emission Color"].default_value = ecol
    for c in cams: bpy.data.objects.remove(c)
    bpy.data.objects.remove(bpy.data.objects["WindowLight"])  # render-only moonlight
    os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)
    for slug in SHELF_ORDER:                                    # covers travel with the textures, named for the book
        shutil.copyfile(os.path.join(COVERS, slug + ".jpg"), os.path.join(OUT, "textures", f"cover_{slug}.jpg"))
        img = M_COVER[slug].node_tree.nodes["Image Texture"].image
        img.filepath = os.path.join(OUT, "textures", f"cover_{slug}.jpg"); img.reload()
    gl = os.path.join(OUT, "lobby.gltf")
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='AUTO', export_lights=True, export_cameras=False)
    allm = merged + dynamic
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in allm)
    verts = sum(len(o.data.vertices) for o in allm)
    print(f"EXPORT {gl} meshes={len(allm)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(allm)}\nverts={verts}\ntris={tris}\n")
        for o in allm: f.write(f"{o.name} verts={len(o.data.vertices)} tris={sum(len(p.vertices) - 2 for p in o.data.polygons)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "lobby_baked.blend"))

if args.bake or args.export:
    bake_and_export()
print("DONE")
