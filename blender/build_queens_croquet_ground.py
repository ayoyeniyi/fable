"""
Fable: The Queen's Croquet-Ground (Alice's Adventures in Wonderland, chapter VIII).

"A large rose-tree stood near the entrance of the garden: the roses growing on it were white,
but there were three gardeners at it, busily painting them red."

Builds the environment procedurally in Blender (no downloaded models or textures), with PBR node
materials and daylight (sun + sky), then (by flag) renders Cycles preview stills, bakes materials to
textures, merges meshes by material and exports a GLB for Unity. Modelled on build_hall_of_doors.py.

Node naming (the contract with Unity's SceneRegistry):
  anchors        empties named "anchor.<manifest anchor id>"      e.g. anchor.rose-tree.crown
  assets         empties named by the exact manifest asset id     e.g. prop.rose-tree, char.two, fx.red-roses
                 (their mesh children never start with an id prefix: "RoseTree_Leaves", "Two_CardFace")
  lights         light objects named by the exact manifest id     light.sun, light.sky, light.fill
  extra          anchor.scene.centre (miniature diorama pivot)
Each asset group's origin sits exactly on the anchor it is placed at in the baseline script, so a
`place` at that anchor leaves it where it was authored.

Run headless:
  blender -b -P blender/build_queens_croquet_ground.py -- --out out/queens-croquet-ground --quick --render
  blender -b -P blender/build_queens_croquet_ground.py -- --out out/queens-croquet-ground --render --bake --export --samples 96 --res 1280
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, noise

# ----------------------------------------------------------------------------- args
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/queens-croquet-ground")
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

# ----------------------------------------------------------------------------- layout (metres, Z up, +Y = into the garden)
GX0, GX1, GY0, GY1 = -9.0, 9.0, -7.5, 16.0      # walled/hedged enclosure; the gate is in the south wall
HEDGE_H, HEDGE_T = 2.6, 0.9
WALL_H, WALL_T = 1.9, 0.36
GATE_HALF = 1.05                                 # half-width of the gate opening
PATH_HALF = 0.9                                  # entrance path half width
READER = Vector((0.0, -6.3, 0.0))                # reader.gate: just inside the entrance; kept clear
TREE = Vector((2.6, -3.2, 0.0))                  # "a large rose-tree stood near the entrance"
CROWN_Z = 1.95
CROWN_ANCHOR_Z = 1.7                             # "the white roses, head height"

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

COLL = bpy.data.collections.new("QueensCroquetGround")
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

def ramp(nt, stops, loc=(0, 0), interp='LINEAR'):
    r = nt.nodes.new("ShaderNodeValToRGB"); r.location = loc
    cr = r.color_ramp
    cr.interpolation = interp
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

def C(rgb, a=1.0):
    return (rgb[0], rgb[1], rgb[2], a)

def scale_c(rgb, k):
    return tuple(min(1.0, c * k) for c in rgb)

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
    r = ramp(nt, [(0.0, C(dark)), (0.25, C(base)), (0.6, C(mid)), (0.9, C(base))], (-450, 100))
    nt.links.new(mix.outputs[0], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", (-150, -200))
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough[1], rough[0]
    nt.links.new(wave.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    bump = node(nt, "ShaderNodeBump", (50, -300)); bump.inputs["Strength"].default_value = 0.45; bump.inputs["Distance"].default_value = 0.003
    nt.links.new(mix.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def foliage(name, base=(0.05, 0.16, 0.04), dark=(0.012, 0.05, 0.012), light=(0.16, 0.3, 0.07), leaf_scale=28.0, rough=0.75, bump_strength=0.9):
    """Clipped leafy surface: voronoi leaf cells for bump and per-leaf tint, large-scale noise for clipping variation."""
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    vor = node(nt, "ShaderNodeTexVoronoi", (-1000, 250)); vor.inputs["Scale"].default_value = leaf_scale
    nt.links.new(mp.outputs["Vector"], vor.inputs["Vector"])
    vor2 = node(nt, "ShaderNodeTexVoronoi", (-1000, -50)); vor2.inputs["Scale"].default_value = leaf_scale * 2.3
    nt.links.new(mp.outputs["Vector"], vor2.inputs["Vector"])
    big = node(nt, "ShaderNodeTexNoise", (-1000, -350)); big.inputs["Scale"].default_value = 1.4; big.inputs["Detail"].default_value = 4
    nt.links.new(mp.outputs["Vector"], big.inputs["Vector"])
    # per-leaf tint from the voronoi cell colour
    sep = node(nt, "ShaderNodeSeparateColor", (-750, 250)); nt.links.new(vor.outputs["Color"], sep.inputs["Color"])
    tint = ramp(nt, [(0.0, C(dark)), (0.45, C(base)), (1.0, C(light))], (-500, 250))
    nt.links.new(sep.outputs["Red"], tint.inputs["Fac"])
    # depth between leaves darkens (distance to cell edge)
    gaps = ramp(nt, [(0.0, (0.25, 0.25, 0.25, 1)), (0.35, (1, 1, 1, 1))], (-500, 0))
    nt.links.new(vor2.outputs["Distance"], gaps.inputs["Fac"])
    m1 = node(nt, "ShaderNodeMix", (-250, 200), data_type='RGBA', blend_type='MULTIPLY'); m1.inputs["Factor"].default_value = 0.7
    nt.links.new(tint.outputs["Color"], m1.inputs[6]); nt.links.new(gaps.outputs["Color"], m1.inputs[7])
    bigr = ramp(nt, [(0.3, (0.7, 0.75, 0.6, 1)), (0.7, (1.15, 1.1, 1.0, 1))], (-500, -350))
    nt.links.new(big.outputs["Fac"], bigr.inputs["Fac"])
    m2 = node(nt, "ShaderNodeMix", (0, 200), data_type='RGBA', blend_type='MULTIPLY'); m2.inputs["Factor"].default_value = 1.0
    nt.links.new(m1.outputs[2], m2.inputs[6]); nt.links.new(bigr.outputs["Color"], m2.inputs[7])
    nt.links.new(m2.outputs[2], b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", (-250, -150)); rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough - 0.25, rough + 0.15
    nt.links.new(vor.outputs["Distance"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    hm = node(nt, "ShaderNodeMath", (-250, -450), operation='ADD')
    nt.links.new(vor.outputs["Distance"], hm.inputs[0]); nt.links.new(vor2.outputs["Distance"], hm.inputs[1])
    bump = node(nt, "ShaderNodeBump", (100, -300)); bump.inputs["Strength"].default_value = bump_strength; bump.inputs["Distance"].default_value = 0.02
    nt.links.new(hm.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Subsurface Weight"].default_value = 0.08
    b.inputs["Subsurface Radius"].default_value = (0.1, 0.25, 0.05)
    return m

def lawn(name, stripes=False, base=(0.10, 0.24, 0.05)):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    blades = node(nt, "ShaderNodeTexNoise", (-1000, 300)); blades.inputs["Scale"].default_value = 260; blades.inputs["Detail"].default_value = 3
    nt.links.new(mp.outputs["Vector"], blades.inputs["Vector"])
    patch = node(nt, "ShaderNodeTexNoise", (-1000, 0)); patch.inputs["Scale"].default_value = 0.35; patch.inputs["Detail"].default_value = 5; patch.inputs["Roughness"].default_value = 0.6
    nt.links.new(mp.outputs["Vector"], patch.inputs["Vector"])
    clover = node(nt, "ShaderNodeTexVoronoi", (-1000, -300)); clover.inputs["Scale"].default_value = 18
    nt.links.new(mp.outputs["Vector"], clover.inputs["Vector"])
    pr = ramp(nt, [(0.25, C(scale_c(base, 0.7))), (0.5, C(base)), (0.75, C((base[0] * 1.5, base[1] * 1.15, base[2] * 1.1)))], (-700, 0))
    nt.links.new(patch.outputs["Fac"], pr.inputs["Fac"])
    br = ramp(nt, [(0.3, (0.72, 0.74, 0.7, 1)), (0.7, (1.12, 1.1, 1.0, 1))], (-700, 300))
    nt.links.new(blades.outputs["Fac"], br.inputs["Fac"])
    m1 = node(nt, "ShaderNodeMix", (-400, 150), data_type='RGBA', blend_type='MULTIPLY'); m1.inputs["Factor"].default_value = 1.0
    nt.links.new(pr.outputs["Color"], m1.inputs[6]); nt.links.new(br.outputs["Color"], m1.inputs[7])
    last = m1
    if stripes:
        # mown stripes, 1.3 m wide, alternating along X
        sx = node(nt, "ShaderNodeSeparateXYZ", (-1000, 550)); nt.links.new(mp.outputs["Vector"], sx.inputs["Vector"])
        dv = node(nt, "ShaderNodeMath", (-800, 550), operation='DIVIDE'); dv.inputs[1].default_value = 1.3
        nt.links.new(sx.outputs["X"], dv.inputs[0])
        fl = node(nt, "ShaderNodeMath", (-650, 550), operation='FLOOR'); nt.links.new(dv.outputs[0], fl.inputs[0])
        md = node(nt, "ShaderNodeMath", (-500, 550), operation='FLOORED_MODULO'); md.inputs[1].default_value = 2.0
        nt.links.new(fl.outputs[0], md.inputs[0])
        st = node(nt, "ShaderNodeMix", (-200, 400), data_type='RGBA', blend_type='MULTIPLY')
        nt.links.new(md.outputs[0], st.inputs["Factor"]); nt.links.new(m1.outputs[2], st.inputs[6]); st.inputs[7].default_value = (0.66, 0.76, 0.62, 1)
        last = st
    nt.links.new(last.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.88
    b.inputs["Sheen Weight"].default_value = 0.25
    b.inputs["Sheen Tint"].default_value = (0.8, 1.0, 0.7, 1)
    hm = node(nt, "ShaderNodeMix", (-400, -300), data_type='FLOAT'); hm.inputs["Factor"].default_value = 0.3
    nt.links.new(blades.outputs["Fac"], hm.inputs[2]); nt.links.new(clover.outputs["Distance"], hm.inputs[3])
    bump = node(nt, "ShaderNodeBump", (0, -300)); bump.inputs["Strength"].default_value = 0.5; bump.inputs["Distance"].default_value = 0.006
    nt.links.new(hm.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def gravel(name="M_Gravel"):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    vor = node(nt, "ShaderNodeTexVoronoi", (-1000, 200)); vor.inputs["Scale"].default_value = 70; vor.inputs["Randomness"].default_value = 1.0
    nt.links.new(mp.outputs["Vector"], vor.inputs["Vector"])
    vor_d = node(nt, "ShaderNodeTexVoronoi", (-1000, -100), feature='DISTANCE_TO_EDGE'); vor_d.inputs["Scale"].default_value = 70
    nt.links.new(mp.outputs["Vector"], vor_d.inputs["Vector"])
    sep = node(nt, "ShaderNodeSeparateColor", (-750, 200)); nt.links.new(vor.outputs["Color"], sep.inputs["Color"])
    stones = ramp(nt, [(0.0, (0.30, 0.27, 0.22, 1)), (0.35, (0.55, 0.50, 0.42, 1)), (0.7, (0.68, 0.64, 0.56, 1)), (1.0, (0.48, 0.42, 0.36, 1))], (-500, 200))
    nt.links.new(sep.outputs["Red"], stones.inputs["Fac"])
    edge = ramp(nt, [(0.0, (0.18, 0.16, 0.13, 1)), (0.12, (1, 1, 1, 1))], (-500, -100))
    nt.links.new(vor_d.outputs["Distance"], edge.inputs["Fac"])
    mx = node(nt, "ShaderNodeMix", (-200, 150), data_type='RGBA', blend_type='MULTIPLY'); mx.inputs["Factor"].default_value = 1.0
    nt.links.new(stones.outputs["Color"], mx.inputs[6]); nt.links.new(edge.outputs["Color"], mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", (-200, -150)); rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = 0.95, 0.6
    nt.links.new(sep.outputs["Green"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    bump = node(nt, "ShaderNodeBump", (100, -300)); bump.inputs["Strength"].default_value = 0.8; bump.inputs["Distance"].default_value = 0.008
    nt.links.new(vor_d.outputs["Distance"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def brick(name="M_Brick"):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    br = node(nt, "ShaderNodeTexBrick", (-1000, 200))
    br.inputs["Scale"].default_value = 4.4
    br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Brick Width"].default_value = 0.5
    br.inputs["Row Height"].default_value = 0.18
    br.inputs["Color1"].default_value = (0.42, 0.13, 0.08, 1)
    br.inputs["Color2"].default_value = (0.30, 0.09, 0.06, 1)
    br.inputs["Mortar"].default_value = (0.55, 0.52, 0.46, 1)
    br.offset = 0.5; br.offset_frequency = 2
    # bricks laid in the XZ plane of the wall and its YZ ends
    sx = node(nt, "ShaderNodeSeparateXYZ", (-1250, 200)); nt.links.new(mp.outputs["Vector"], sx.inputs["Vector"])
    ad = node(nt, "ShaderNodeMath", (-1100, 300), operation='ADD'); nt.links.new(sx.outputs["X"], ad.inputs[0]); nt.links.new(sx.outputs["Y"], ad.inputs[1])
    cx = node(nt, "ShaderNodeCombineXYZ", (-1100, 150)); nt.links.new(ad.outputs[0], cx.inputs["X"]); nt.links.new(sx.outputs["Z"], cx.inputs["Y"])
    nt.links.new(cx.outputs["Vector"], br.inputs["Vector"])
    grit = node(nt, "ShaderNodeTexNoise", (-1000, -150)); grit.inputs["Scale"].default_value = 40; grit.inputs["Detail"].default_value = 8
    nt.links.new(mp.outputs["Vector"], grit.inputs["Vector"])
    gr = ramp(nt, [(0.3, (0.75, 0.75, 0.75, 1)), (0.7, (1.1, 1.05, 1.0, 1))], (-700, -150))
    nt.links.new(grit.outputs["Fac"], gr.inputs["Fac"])
    m1 = node(nt, "ShaderNodeMix", (-400, 200), data_type='RGBA', blend_type='MULTIPLY'); m1.inputs["Factor"].default_value = 1.0
    nt.links.new(br.outputs["Color"], m1.inputs[6]); nt.links.new(gr.outputs["Color"], m1.inputs[7])
    nt.links.new(m1.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.88
    hm = node(nt, "ShaderNodeMix", (-400, -350), data_type='FLOAT'); hm.inputs["Factor"].default_value = 0.2
    inv = node(nt, "ShaderNodeMath", (-600, -350), operation='SUBTRACT'); inv.inputs[0].default_value = 1.0; nt.links.new(br.outputs["Fac"], inv.inputs[1])
    nt.links.new(inv.outputs[0], hm.inputs[2]); nt.links.new(grit.outputs["Fac"], hm.inputs[3])
    bump = node(nt, "ShaderNodeBump", (0, -300)); bump.inputs["Strength"].default_value = 0.7; bump.inputs["Distance"].default_value = 0.01
    nt.links.new(hm.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def stone(name="M_Stone", color=(0.66, 0.62, 0.54), scale=6.0, rough=0.8):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    n = node(nt, "ShaderNodeTexNoise", (-900, 0)); n.inputs["Scale"].default_value = scale * 4; n.inputs["Detail"].default_value = 10; n.inputs["Roughness"].default_value = 0.65
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    s = node(nt, "ShaderNodeTexNoise", (-900, -300)); s.inputs["Scale"].default_value = scale * 0.3; s.inputs["Detail"].default_value = 3
    nt.links.new(mp.outputs["Vector"], s.inputs["Vector"])
    r = ramp(nt, [(0.3, C(scale_c(color, 0.72))), (0.7, C(color))], (-600, -300))
    nt.links.new(s.outputs["Fac"], r.inputs["Fac"])
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-600, -600)); ao.inputs["Distance"].default_value = 0.2
    mx = node(nt, "ShaderNodeMix", (-300, -300), data_type='RGBA', blend_type='MULTIPLY'); mx.inputs["Factor"].default_value = 0.5
    nt.links.new(r.outputs["Color"], mx.inputs[6]); nt.links.new(ao.outputs["Color"], mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    bump = node(nt, "ShaderNodeBump", (0, -200)); bump.inputs["Strength"].default_value = 0.4; bump.inputs["Distance"].default_value = 0.004
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def plain(name, color, rough=0.6, metallic=0.0, coat=0.0, sss=0.0, sss_radius=(0.3, 0.15, 0.1), noise_scale=0.0, noise_amt=0.15, bump=0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = C(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Coat Weight"].default_value = coat
    if sss > 0:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = sss_radius
    if noise_scale > 0:
        mp = texcoord_obj(nt)
        n = node(nt, "ShaderNodeTexNoise", (-900, 0)); n.inputs["Scale"].default_value = noise_scale; n.inputs["Detail"].default_value = 6
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
        r = ramp(nt, [(0.3, C(scale_c(color, 1 - noise_amt))), (0.7, C(scale_c(color, 1 + noise_amt)))], (-600, 0))
        nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
        if bump > 0:
            bp = node(nt, "ShaderNodeBump", (0, -250)); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = 0.002
            nt.links.new(n.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def card_back(name="M_CardBack"):
    """Victorian card back: a fine red diamond lattice."""
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    mp.inputs["Rotation"].default_value = (0, math.radians(45), 0)
    chk = node(nt, "ShaderNodeTexChecker", (-900, 100)); chk.inputs["Scale"].default_value = 26.0
    chk.inputs["Color1"].default_value = (0.50, 0.035, 0.04, 1); chk.inputs["Color2"].default_value = (0.36, 0.02, 0.03, 1)
    nt.links.new(mp.outputs["Vector"], chk.inputs["Vector"])
    chk2 = node(nt, "ShaderNodeTexChecker", (-900, -150)); chk2.inputs["Scale"].default_value = 104.0
    chk2.inputs["Color1"].default_value = (1, 1, 1, 1); chk2.inputs["Color2"].default_value = (0.82, 0.8, 0.8, 1)
    nt.links.new(mp.outputs["Vector"], chk2.inputs["Vector"])
    mx = node(nt, "ShaderNodeMix", (-500, 0), data_type='RGBA', blend_type='MULTIPLY'); mx.inputs["Factor"].default_value = 1.0
    nt.links.new(chk.outputs["Color"], mx.inputs[6]); nt.links.new(chk2.outputs["Color"], mx.inputs[7])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.45
    b.inputs["Coat Weight"].default_value = 0.2
    return m

def paint(name="M_Paint", color=(0.52, 0.012, 0.018)):
    """Wet red paint: glossy, a little uneven."""
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    n = node(nt, "ShaderNodeTexNoise", (-900, 0)); n.inputs["Scale"].default_value = 30; n.inputs["Detail"].default_value = 4
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    r = ramp(nt, [(0.3, C(scale_c(color, 0.75))), (0.7, C(color))], (-600, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", (-500, -250)); rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = 0.08, 0.3
    nt.links.new(n.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    b.inputs["Coat Weight"].default_value = 0.5
    b.inputs["Coat Roughness"].default_value = 0.08
    return m

def rose_petal(name, color, rough=0.5, sss=0.2):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    # petal swirl: a twisted wave around the bloom's axis (each rose is built with its axis along local Z)
    wave = node(nt, "ShaderNodeTexWave", (-1000, 100), wave_type='RINGS', rings_direction='SPHERICAL')
    wave.inputs["Scale"].default_value = 40; wave.inputs["Distortion"].default_value = 6; wave.inputs["Detail"].default_value = 2
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    r = ramp(nt, [(0.0, C(scale_c(color, 0.55))), (0.25, C(scale_c(color, 0.9))), (1.0, C(color))], (-600, 100))
    nt.links.new(wave.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Subsurface Weight"].default_value = sss
    b.inputs["Subsurface Radius"].default_value = (0.2, 0.12, 0.08)
    b.inputs["Sheen Weight"].default_value = 0.3
    bump = node(nt, "ShaderNodeBump", (0, -250)); bump.inputs["Strength"].default_value = 0.5; bump.inputs["Distance"].default_value = 0.003
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def peg(name="M_Peg"):
    """Croquet peg: painted bands blue, red, black, yellow."""
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    sx = node(nt, "ShaderNodeSeparateXYZ", (-1000, 0)); nt.links.new(mp.outputs["Vector"], sx.inputs["Vector"])
    mul = node(nt, "ShaderNodeMath", (-800, 0), operation='MULTIPLY'); mul.inputs[1].default_value = 1 / 0.6
    nt.links.new(sx.outputs["Z"], mul.inputs[0])
    r = ramp(nt, [(0.0, (0.85, 0.83, 0.78, 1)), (0.55, (0.04, 0.1, 0.45, 1)), (0.66, (0.6, 0.03, 0.03, 1)), (0.77, (0.02, 0.02, 0.02, 1)), (0.88, (0.8, 0.6, 0.05, 1))], (-600, 0), interp='CONSTANT')
    nt.links.new(mul.outputs[0], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.4
    return m

M_LAWN = lawn("M_Lawn", stripes=False, base=(0.07, 0.16, 0.035))
M_CROQUET = lawn("M_CroquetLawn", stripes=True, base=(0.09, 0.21, 0.04))
M_GRAVEL = gravel()
M_HEDGE = foliage("M_Hedge", base=(0.035, 0.11, 0.03), dark=(0.008, 0.03, 0.01), light=(0.09, 0.2, 0.05), leaf_scale=26)
M_ROSELEAF = foliage("M_RoseLeaves", base=(0.05, 0.15, 0.035), dark=(0.012, 0.045, 0.012), light=(0.14, 0.28, 0.06), leaf_scale=34, bump_strength=1.0)
M_TREELEAF = foliage("M_TreeLeaves", base=(0.07, 0.17, 0.05), dark=(0.02, 0.06, 0.02), light=(0.2, 0.32, 0.09), leaf_scale=9, bump_strength=0.7)
M_BRICK = brick()
M_STONE = stone("M_Stone", color=(0.5, 0.47, 0.41))
M_DOORGREEN = wood("M_DoorGreen", base=(0.05, 0.12, 0.07), dark=(0.02, 0.05, 0.03), light=(0.09, 0.17, 0.1), scale=1.5, grain_dir=(14, 1, 1), bands='X')
M_SOIL = plain("M_Soil", (0.07, 0.045, 0.03), rough=0.95, noise_scale=18, noise_amt=0.35, bump=0.6)
M_BARK = wood("M_Bark", base=(0.13, 0.09, 0.06), dark=(0.04, 0.03, 0.02), light=(0.24, 0.19, 0.13), scale=3.0, rough=(0.8, 0.95))
M_IRON = plain("M_Iron", (0.03, 0.03, 0.035), rough=0.45, metallic=0.85, noise_scale=40, noise_amt=0.3)
M_TERRACOTTA = plain("M_Terracotta", (0.48, 0.2, 0.1), rough=0.85, noise_scale=12, noise_amt=0.2, bump=0.3)
M_HOOP = plain("M_Hoop", (0.85, 0.85, 0.82), rough=0.35, metallic=0.2)
M_PEG = peg()
M_ROSE_WHITE = rose_petal("M_RoseWhite", (0.86, 0.85, 0.79), rough=0.55, sss=0.25)
M_ROSE_RED = rose_petal("M_RoseRed", (0.55, 0.015, 0.025), rough=0.3, sss=0.1)       # freshly painted: glossier
M_ROSE_PINKWHITE = rose_petal("M_RoseBed", (0.88, 0.62, 0.62), rough=0.55, sss=0.2)   # the beds' own (unpainted) roses
M_PAINT = paint()
M_TIN = plain("M_Tin", (0.55, 0.56, 0.58), rough=0.35, metallic=1.0, noise_scale=25, noise_amt=0.2)
M_BRUSHWOOD = wood("M_BrushWood", base=(0.45, 0.3, 0.16), dark=(0.25, 0.15, 0.07), light=(0.6, 0.45, 0.28), scale=8, rough=(0.4, 0.6))
M_CARDFACE = plain("M_CardFace", (0.88, 0.86, 0.8), rough=0.45, coat=0.25, noise_scale=80, noise_amt=0.03)
M_CARDBACK = card_back()
M_INK = plain("M_Ink", (0.018, 0.016, 0.016), rough=0.5)
M_SKIN = plain("M_Skin", (0.78, 0.55, 0.42), rough=0.55, sss=0.3, sss_radius=(0.4, 0.2, 0.12))

def vcol_mat(name="M_PaintArm"):
    """One material for a small multi-part prop: colour and roughness come from per-part colour attributes,
    so the whole brush arm (sleeve, hand, handle, ferrule, wet bristles) is one mesh and one baked texture set."""
    m, nt, b = new_mat(name)
    col = node(nt, "ShaderNodeAttribute", (-500, 100)); col.attribute_name = "PartColor"
    rgh = node(nt, "ShaderNodeAttribute", (-500, -150)); rgh.attribute_name = "PartRough"
    nt.links.new(col.outputs["Color"], b.inputs["Base Color"]); nt.links.new(rgh.outputs["Fac"], b.inputs["Roughness"])
    return m
M_PAINTARM = vcol_mat()
PART = {"ink": ((0.018, 0.016, 0.016), 0.5), "skin": ((0.78, 0.55, 0.42), 0.55), "wood": ((0.45, 0.3, 0.16), 0.5),
        "tin": ((0.5, 0.51, 0.53), 0.3), "paint": ((0.52, 0.012, 0.018), 0.15)}

def as_part(o, part):
    """Re-material o to M_PAINTARM with the part's colour/roughness written to colour attributes."""
    rgb, rough = PART[part]
    me = o.data
    ca = me.color_attributes.new("PartColor", 'FLOAT_COLOR', 'CORNER')
    cr = me.color_attributes.new("PartRough", 'FLOAT_COLOR', 'CORNER')
    for i in range(len(me.loops)):
        ca.data[i].color = (*rgb, 1.0); cr.data[i].color = (rough, rough, rough, 1.0)
    me.materials.clear(); me.materials.append(M_PAINTARM)
    return o

# ----------------------------------------------------------------------------- geometry helpers (from build_hall_of_doors.py, plus tube/blob)
def _finish(o, mat, smooth=True):
    o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0), segments=2):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = segments; md.limit_method = 'ANGLE'
        o.data.materials.append(mat)
        for p in o.data.polygons: p.use_smooth = True
        md2 = o.modifiers.new("WN", 'WEIGHTED_NORMAL'); md2.keep_sharp = True
        for c in o.users_collection: c.objects.unlink(o)
        return link(o)
    return _finish(o, mat, smooth=False)

def cyl(name, r, h, loc, mat, verts=16, rot=(0, 0, 0), r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat)

def sphere(name, r, loc, mat, seg=12, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(4, seg // 2), radius=r, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return _finish(o, mat)

def lathe(name, profile, loc, mat, steps=24, wobble=None):
    """profile: list of (radius, z) from bottom to top; revolve around Z. wobble(a, z) -> radius multiplier."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        ring = []
        for i in range(steps):
            a = 2 * math.pi * i / steps
            rr = r * (wobble(a, z) if wobble else 1.0)
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
        rings.append(ring)
    for a, b_ in zip(rings, rings[1:]):
        for i in range(steps):
            j = (i + 1) % steps
            bm.faces.new((a[i], a[j], b_[j], b_[i]))
    if profile[0][0] > 1e-5: bm.faces.new(list(reversed(rings[0])))
    if profile[-1][0] > 1e-5: bm.faces.new(rings[-1])
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def tube(name, pts, radii, mat, sides=8, caps=True):
    """A tube along a polyline, parallel-transported frames (no twisting). radii: float or per-point list."""
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
        v = d.cross(u)
        u_prev = u
        rings.append([bm.verts.new(p + (u * math.cos(2 * math.pi * k / sides) + v * math.sin(2 * math.pi * k / sides)) * radii[i]) for k in range(sides)])
    for a, b_ in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b_[j], b_[k]))
    if caps:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def limb(name, p0, p1, r0, r1, mat, sides=8):
    return tube(name, [p0, p1], [r0, r1], mat, sides=sides)

def blob(name, r, loc, mat, subdiv=2, amp=0.18, freq=1.6, scale=(1, 1, 1), seed=0.0, flat_bottom=None):
    """Displaced icosphere: clipped foliage mass. Returns (object, surface(dir) -> world point)."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=1.0, location=(0, 0, 0))
    o = bpy.context.active_object; o.name = name
    off = Vector((seed * 7.31, seed * 3.17, seed * 5.53))
    sc = Vector(scale)
    def radius_at(d):
        return r * (1.0 + amp * noise.noise(d * freq + off))
    for v in o.data.vertices:
        d = v.co.normalized()
        p = d * radius_at(d)
        v.co = Vector((p.x * sc.x, p.y * sc.y, p.z * sc.z))
        if flat_bottom is not None and v.co.z < flat_bottom: v.co.z = flat_bottom
    o.location = loc
    _finish(o, mat)
    L = Vector(loc)
    def surface(d):
        d = Vector(d).normalized(); p = d * radius_at(d)
        return L + Vector((p.x * sc.x, p.y * sc.y, p.z * sc.z))
    return o, surface

def flat_poly(name, pts2d, y, mat, front=True):
    """Polygon in the XZ plane at depth y; front=True faces -Y (towards a reader standing in front)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new((x, y, z)) for (x, z) in pts2d]
    bm.faces.new(vs if front else list(reversed(vs)))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

def slab(name, pts2d, thick, mat):
    """Extrude a CCW XZ outline to a slab centred on y=0 (front at -thick/2)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    f = [bm.verts.new((x, -thick / 2, z)) for (x, z) in pts2d]
    b_ = [bm.verts.new((x, thick / 2, z)) for (x, z) in pts2d]
    bm.faces.new(f); bm.faces.new(list(reversed(b_)))
    n = len(pts2d)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((f[j], f[i], b_[i], b_[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

def rounded_rect(w, h, r, seg=4, cx=0.0, cz=0.0):
    pts = []
    for (sx, sz, a0) in [(1, -1, -90), (1, 1, 0), (-1, 1, 90), (-1, -1, 180)]:
        ccx, ccz = cx + sx * (w / 2 - r), cz + sz * (h / 2 - r)
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((ccx + r * math.cos(a), ccz + r * math.sin(a)))
    return pts

def text_mesh(name, body, size, loc, mat, rot=(math.pi / 2, 0, 0), extrude=0.0004, align='CENTER'):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body; cu.size = size; cu.extrude = extrude; cu.align_x = align; cu.align_y = 'CENTER'
    cu.resolution_u = 2
    try:
        cu.font = bpy.data.fonts.load("/System/Library/Fonts/Supplemental/Georgia Bold.ttf", check_existing=True)
    except Exception:
        pass   # Blender's built-in font
    o = bpy.data.objects.new(name, cu); o.location = loc; o.rotation_euler = rot
    link(o)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.view_layer.objects.active
    o.data.materials.clear(); o.data.materials.append(mat)
    return o

def group(name, objs, loc, rot_z=0.0):
    """Parent objs under a named empty (exported as a glTF node Unity can find by name)."""
    e = bpy.data.objects.new(name, None); e.empty_display_size = 0.05; e.location = loc; e.rotation_euler = (0, 0, rot_z); link(e)
    bpy.context.view_layer.update()
    for o in objs:
        o.parent = e; o.matrix_parent_inverse = e.matrix_world.inverted()
    return e

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

def look_yaw(frm, to):
    """Yaw about Z so that local -Y (a card's front) faces from frm towards to."""
    d = Vector(to) - Vector(frm)
    return math.atan2(d.x, -d.y)

DYNAMIC = []      # asset groups (manifest ids); their children are merged per group and baked separately
CHILD_PREFIX = {} # group name -> prefix used for its merged children's names

# ----------------------------------------------------------------------------- ground, paths
box("Ground", (40.0, 40.0, 0.1), (0, 4.0, -0.05), M_LAWN)
# entrance path from the gate to the cross walk, a cross walk, and a gravel surround for the croquet lawn
box("Path_Entrance", (PATH_HALF * 2, 8.4, 0.03), (0, -3.3, 0.0015), M_GRAVEL)
box("Path_Cross", (17.2, 1.4, 0.03), (0, 0.7, 0.003), M_GRAVEL)
box("Path_Surround", (14.6, 14.4, 0.03), (0, 8.8, 0.0), M_GRAVEL)
box("Path_Apron", (3.0, 1.0, 0.03), (0, -7.05, 0.0), M_GRAVEL)          # under the open gate
box("CroquetLawn", (13.0, 12.8, 0.05), (0, 8.8, 0.0), M_CROQUET)
# stone edging along the entrance path
for side in (-1, 1):
    box(f"PathEdge_{side}", (0.08, 8.4, 0.05), (side * (PATH_HALF + 0.04), -3.3, 0.01), M_STONE, bevel=0.01)

# ----------------------------------------------------------------------------- south wall with gate piers and open iron gates
for side in (-1, 1):
    x0, x1 = side * (GATE_HALF + 0.25), side * (-GX0 + HEDGE_T)
    cx, ln = (x0 + x1) / 2, abs(x1 - x0)
    box(f"Wall_{side}", (ln, WALL_T, WALL_H), (cx, GY0, WALL_H / 2), M_BRICK, bevel=0.004)
    box(f"WallCoping_{side}", (ln, WALL_T + 0.08, 0.09), (cx, GY0, WALL_H + 0.045), M_STONE, bevel=0.012)
    box(f"WallPlinth_{side}", (ln, WALL_T + 0.06, 0.22), (cx, GY0, 0.11), M_STONE, bevel=0.01)
    px = side * (GATE_HALF + 0.27)
    box(f"Pier_{side}", (0.56, 0.56, 2.3), (px, GY0, 1.15), M_BRICK, bevel=0.006)
    box(f"PierCap_{side}", (0.68, 0.68, 0.12), (px, GY0, 2.36), M_STONE, bevel=0.015)
    box(f"PierBase_{side}", (0.66, 0.66, 0.3), (px, GY0, 0.15), M_STONE, bevel=0.015)
    cyl(f"PierNeck_{side}", 0.1, 0.12, (px, GY0, 2.48), M_STONE, verts=12)
    sphere(f"PierBall_{side}", 0.2, (px, GY0, 2.72), M_STONE, seg=16)
    # gate leaf hinged on the pier, swung outwards (away from the reader), 70 degrees open
    hinge = Vector((side * GATE_HALF, GY0 - 0.05, 0.0))
    along = Vector((-side * math.cos(math.radians(70)), -math.sin(math.radians(70)), 0.0))
    W = GATE_HALF - 0.02
    def gp(t, z):
        return hinge + along * (W * t) + Vector((0, 0, z))
    parts = [tube(f"Gate_{side}_Bottom", [gp(0, 0.12), gp(1, 0.12)], 0.018, M_IRON, sides=6),
             tube(f"Gate_{side}_Rail", [gp(0, 1.25), gp(1, 1.25)], 0.016, M_IRON, sides=6),
             tube(f"Gate_{side}_Hinge", [gp(0, 0.06), gp(0, 1.75)], 0.022, M_IRON, sides=6),
             tube(f"Gate_{side}_Latch", [gp(1, 0.06), gp(1, 1.45)], 0.02, M_IRON, sides=6)]
    nb = 9
    for k in range(1, nb):
        t = k / nb
        top = 1.45 + 0.3 * math.sin(math.pi * t)
        parts.append(tube(f"Gate_{side}_Bar{k}", [gp(t, 0.1), gp(t, top)], 0.011, M_IRON, sides=6))
        parts.append(sphere(f"Gate_{side}_Spear{k}", 0.022, gp(t, top + 0.02), M_IRON, seg=6, scale=(1, 1, 1.8)))
    arch = [gp(k / 12, 1.45 + 0.3 * math.sin(math.pi * k / 12)) for k in range(13)]
    parts.append(tube(f"Gate_{side}_Arch", arch, 0.016, M_IRON, sides=6))

# ----------------------------------------------------------------------------- hedges: tall clipped yew on the west, east and north
def hedge(name, x0, y0, x1, y1, h=HEDGE_H, t=HEDGE_T):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    sx, sy = (abs(x1 - x0) or t), (abs(y1 - y0) or t)
    box(name, (sx, sy, h), (cx, cy, h / 2), M_HEDGE, bevel=0.12, segments=3)
hedge("Hedge_W", GX0 - HEDGE_T / 2, GY0 - 0.2, GX0 - HEDGE_T / 2, GY1 + HEDGE_T)
hedge("Hedge_E", GX1 + HEDGE_T / 2, GY0 - 0.2, GX1 + HEDGE_T / 2, GY1 + HEDGE_T)
hedge("Hedge_N", GX0 - HEDGE_T, GY1 + HEDGE_T / 2, GX1 + HEDGE_T, GY1 + HEDGE_T / 2)
# buttresses for rhythm along the long hedges
for i in range(6):
    y = -3.5 + i * 3.6
    for side in (-1, 1):
        box(f"HedgeButtress_{side}_{i}", (0.5, 0.9, HEDGE_H + 0.25), (side * (GX1 - 0.15), y, (HEDGE_H + 0.25) / 2), M_HEDGE, bevel=0.14, segments=1)
for i in range(4):
    x = -6.75 + i * 4.5
    box(f"HedgeButtressN_{i}", (0.9, 0.5, HEDGE_H + 0.25), (x, GY1 - 0.15, (HEDGE_H + 0.25) / 2), M_HEDGE, bevel=0.14, segments=1)
# an arch in the north hedge: the way on to the Queen's procession
box("Hedge_N_DoorRecess", (1.5, 0.2, 2.1), (0, GY1 + 0.04, 1.05), M_SOIL)
for k in range(5):     # a boarded garden door, ledged, standing in the hedge
    box(f"Hedge_N_Board{k}", (0.27, 0.05, 2.0), (-0.56 + k * 0.28, GY1 - 0.07, 1.0), M_DOORGREEN)
for z in (0.35, 1.65):
    box(f"Hedge_N_Ledge{z}", (1.3, 0.04, 0.12), (0, GY1 - 0.11, z), M_DOORGREEN)
sphere("Hedge_N_Ring", 0.035, (0.45, GY1 - 0.14, 1.0), M_IRON, seg=8)

# ----------------------------------------------------------------------------- beds: rose bushes inside the south wall, soil for the rose tree
box("Bed_W", (6.4, 0.9, 0.12), (-5.3, GY0 + 0.68, 0.06), M_SOIL, bevel=0.03)
box("Bed_E", (3.6, 0.9, 0.12), (6.8, GY0 + 0.68, 0.06), M_SOIL, bevel=0.03)
def rose_bush(name, loc, r, n_roses, mat_rose, seed):
    o, surf = blob(f"{name}_Leaves", r, (loc[0], loc[1], loc[2] + r * 0.8), M_ROSELEAF, subdiv=3, amp=0.22, freq=2.2, scale=(1.15, 1.0, 0.85), seed=seed, flat_bottom=-r * 0.75)
    for k in range(n_roses):
        a = random.uniform(0, 2 * math.pi); el = random.uniform(-0.1, 1.2)
        d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        c = Vector((loc[0], loc[1], loc[2] + r * 0.8))
        p = c + (surf(d) - c) * 0.95
        rose(f"{name}_Rose{k}", p, d, mat_rose, size=0.042, steps=5)
    return o

# ----------------------------------------------------------------------------- roses
def rose_mesh(name, size, steps=7, seed=0.0):
    """A cupped bloom along local +Z: scalloped petals, a darker heart. ~steps*10 triangles."""
    prof = [(0.0, -0.05), (0.55, -0.02), (0.95, 0.22), (1.0, 0.5), (0.82, 0.78), (0.5, 0.74), (0.32, 0.9), (0.0, 0.84)]
    ph = seed * 1.7
    def wob(a, z):
        return 1.0 + 0.13 * math.sin(5 * a + ph) * min(1.0, max(0.0, z / (0.4 * size)))
    o = lathe(name, [(r * size, z * size) for (r, z) in prof], (0, 0, 0), M_ROSE_WHITE, steps=steps, wobble=wob)
    return o

def rose(name, pos, normal, mat, size=0.064, steps=6, tilt=0.3, half=False):
    """Place a bloom at pos facing along normal (blended upwards: roses turn to the light).
    half=True returns two objects: a white half and a painted half (the gardeners only got half way)."""
    n = (Vector(normal).normalized() + Vector((0, 0, tilt))).normalized()
    o = rose_mesh(name, size, steps, seed=random.random() * 10)
    o.data.materials.clear(); o.data.materials.append(mat)
    q = n.to_track_quat('Z', 'Y')
    spin = Matrix.Rotation(random.uniform(0, 2 * math.pi), 4, 'Z')
    o.matrix_world = Matrix.Translation(pos) @ q.to_matrix().to_4x4() @ spin
    if not half:
        return o
    # split: painted half is on the side the brush came from (a random cut through the axis)
    red = o.copy(); red.data = o.data.copy(); red.name = name + "_Painted"; link(red)
    red.data.materials.clear(); red.data.materials.append(M_ROSE_RED)
    cut_n = Vector((math.cos(random.uniform(0, 6.28)), math.sin(random.uniform(0, 6.28)), random.uniform(-0.3, 0.3))).normalized()
    for ob, keep_pos in ((o, False), (red, True)):
        bm = bmesh.new(); bm.from_mesh(ob.data)
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=cut_n, clear_inner=keep_pos, clear_outer=not keep_pos)
        bm.to_mesh(ob.data); bm.free()
    return o, red

# ----------------------------------------------------------------------------- the large rose tree (prop.rose-tree)
tree_parts = []
# a gnarled standard: trunk, a fork and five limbs into the crown
trunk_pts = [TREE + Vector((0, 0, 0)), TREE + Vector((0.03, 0.02, 0.45)), TREE + Vector((-0.02, 0.05, 0.9)), TREE + Vector((0.04, 0.0, 1.25))]
tree_parts.append(tube("RoseTree_Trunk", trunk_pts, [0.11, 0.085, 0.075, 0.065], M_BARK, sides=10))
tree_parts.append(lathe("RoseTree_Flare", [(0.16, 0.0), (0.12, 0.08), (0.1, 0.16)], TREE, M_BARK, steps=10,
                        wobble=lambda a, z: 1.0 + 0.25 * max(0.0, math.sin(3 * a)) * (1 - z / 0.16)))
for k in range(5):
    a = 2 * math.pi * k / 5 + 0.4
    p0 = TREE + Vector((0.04, 0.0, 1.2))
    p1 = TREE + Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 1.55 + 0.1 * (k % 2)))
    p2 = TREE + Vector((math.cos(a) * 0.55, math.sin(a) * 0.55, 1.75 + 0.2 * (k % 3)))
    tree_parts.append(tube(f"RoseTree_Limb{k}", [p0, p1, p2], [0.05, 0.035, 0.02], M_BARK, sides=6))
CROWN = Vector((TREE.x, TREE.y, CROWN_Z))
crown_blobs = [(Vector((0, 0, 0.12)), 0.72, 3)]
# a loose dome of smaller masses: Fibonacci points on an ellipsoid, jittered
NB = 30
for k in range(NB):
    zf = 1 - (k + 0.5) / NB * 1.75            # stop short of the underside
    if zf < -0.75: continue
    rr_ = math.sqrt(max(0.0, 1 - zf * zf)); th = k * 2.39996 + 0.3
    off = Vector((math.cos(th) * rr_ * 0.88, math.sin(th) * rr_ * 0.88, zf * 0.62 + 0.1)) + Vector((random.uniform(-0.06, 0.06), random.uniform(-0.06, 0.06), random.uniform(-0.05, 0.05)))
    crown_blobs.append((off, random.uniform(0.27, 0.36), 2))
crown_surf = []
for k, (off, r, sd) in enumerate(crown_blobs):
    o, surf = blob(f"RoseTree_Crown{k}", r, CROWN + off, M_ROSELEAF, subdiv=sd, amp=0.2 if sd == 2 else 0.12, freq=2.4, seed=k + 0.5)
    tree_parts.append(o); crown_surf.append((CROWN + off, r, surf))

def crown_points(n, bias_dir=None, bias=0.0, min_el=-0.5):
    """Random visible points on the crown surface (not buried inside a neighbouring blob)."""
    pts = []
    tries = 0
    while len(pts) < n and tries < n * 60:
        tries += 1
        c, r, surf = random.choices(crown_surf[1:], weights=[r * r for (_, r, _) in crown_surf[1:]])[0]
        d = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized()
        if d.z < min_el: continue
        p = surf(d)
        if any((p - c2).length < r2 * 0.92 for (c2, r2, _) in crown_surf if c2 is not c): continue
        if bias_dir is not None and bias > 0:
            out = Vector((p.x - CROWN.x, p.y - CROWN.y, 0))
            if out.length > 1e-4 and random.random() < bias and out.normalized().dot(bias_dir) < 0.2: continue
        if any((p - q[0]).length < 0.11 for q in pts): continue
        pts.append((c + (p - c) * 0.94, (p - c).normalized()))     # seat the bloom into the leaves
    return pts

# the side facing the gate (where the reader stands) is where the painting has got to
to_reader = Vector((READER.x - TREE.x, READER.y - TREE.y, 0)).normalized()
white_roses, red_roses, half_roses = [], [], []
pts = crown_points(84, min_el=-0.6)
random.shuffle(pts)
fx_targets = []
for i, (p, nrm) in enumerate(pts):
    out = Vector((p.x - CROWN.x, p.y - CROWN.y, 0)).normalized()
    facing = out.dot(to_reader)
    roll = random.random()
    if facing > 0.25 and roll < 0.38:
        red_roses.append(rose(f"RoseTree_Red{i}", p, nrm, M_ROSE_RED))
    elif facing > -0.1 and roll < 0.62:
        w, r_ = rose(f"RoseTree_Half{i}", p, nrm, M_ROSE_WHITE, half=True)
        white_roses.append(w); half_roses.append(r_)
    else:
        o = rose(f"RoseTree_White{i}", p, nrm, M_ROSE_WHITE)
        white_roses.append(o)
        if facing > -0.35: fx_targets.append(o)
tree_parts += white_roses + red_roses + half_roses
DYNAMIC.append(group("prop.rose-tree", tree_parts, TREE)); CHILD_PREFIX["prop.rose-tree"] = "RoseTree"
# the bed the tree stands in (static): soil disc, a low stone kerb
lathe("TreeBed_Soil", [(0.0, 0.035), (0.9, 0.035), (0.92, 0.0)], TREE, M_SOIL, steps=28)
tube("TreeBed_Kerb", [TREE + Vector((math.cos(2 * math.pi * k / 28) * 0.98, math.sin(2 * math.pi * k / 28) * 0.98, 0.04)) for k in range(29)], 0.055, M_STONE, sides=6, caps=False)

# fx.red-roses: painted overlays for the white roses still facing the reader, at the crown anchor ("roses turning red")
CROWN_ANCHOR = Vector((TREE.x, TREE.y, CROWN_ANCHOR_Z))
fx_roses = []
for k, w in enumerate(fx_targets[:18]):
    o = w.copy(); o.data = w.data.copy(); o.name = f"RedRoses_{k}"; o.parent = None; link(o)
    o.data.materials.clear(); o.data.materials.append(M_ROSE_RED)
    o.matrix_world = w.matrix_world @ Matrix.Scale(1.1, 4)
    fx_roses.append(o)
DYNAMIC.append(group("fx.red-roses", fx_roses, CROWN_ANCHOR)); CHILD_PREFIX["fx.red-roses"] = "RedRoses"

# ----------------------------------------------------------------------------- smaller standard rose trees along the cross walk, and the bed bushes
for k, x in enumerate([-7.0, -4.2, 4.2, 7.0]):
    base = Vector((x, -0.45, 0.0))
    tube(f"Standard{k}_Stem", [base, base + Vector((0.02, 0, 0.7)), base + Vector((0, 0.01, 1.3))], [0.045, 0.035, 0.03], M_BARK, sides=6)
    o, surf = blob(f"Standard{k}_Head", 0.42, base + Vector((0, 0, 1.55)), M_ROSELEAF, subdiv=3, amp=0.2, freq=2.0, seed=20 + k)
    lathe(f"Standard{k}_Bed", [(0.0, 0.03), (0.35, 0.03), (0.37, 0.0)], base, M_SOIL, steps=12)
    for j in range(6):
        a = random.uniform(0, 2 * math.pi); el = random.uniform(-0.3, 1.1)
        d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        rose(f"Standard{k}_Rose{j}", surf(d), d, M_ROSE_WHITE if (k + j) % 3 else M_ROSE_RED, size=0.045, steps=5)
for k in range(4):
    rose_bush(f"BedW{k}", (-7.6 + k * 1.6, GY0 + 0.7, 0.1), 0.45, 6, M_ROSE_PINKWHITE if k % 2 else M_ROSE_WHITE, seed=40 + k)
for k in range(2):
    rose_bush(f"BedE{k}", (5.9 + k * 1.7, GY0 + 0.7, 0.1), 0.45, 6, M_ROSE_WHITE if k % 2 else M_ROSE_PINKWHITE, seed=50 + k)

# topiary: clipped cones in terracotta pots inside the gate
for side in (-1, 1):
    base = Vector((side * 2.35, GY0 + 0.75, 0.0))
    lathe(f"TopiaryPot_{side}", [(0.18, 0.0), (0.24, 0.05), (0.27, 0.45), (0.31, 0.48), (0.31, 0.53), (0.25, 0.53)], base, M_TERRACOTTA, steps=16)
    lathe(f"TopiarySoil_{side}", [(0.0, 0.5), (0.25, 0.5)], base, M_SOIL, steps=12)
    lathe(f"Topiary_{side}", [(0.04, 0.48), (0.3, 0.6), (0.22, 1.1), (0.12, 1.45), (0.0, 1.62)], base, M_HEDGE, steps=14)

# ----------------------------------------------------------------------------- the croquet ground: hoops and the peg
def hoop(name, loc, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    pts = []
    for k in range(9):
        a = math.pi * k / 8
        lx, lz = 0.16 * math.cos(a), 0.3 + 0.16 * math.sin(a)
        pts.append(Vector(loc) + Vector((lx * c, lx * s, lz)))
    full = [pts[0] - Vector((0, 0, 0.3))] + pts + [pts[-1] - Vector((0, 0, 0.3))]
    return tube(name, full, 0.009, M_HOOP, sides=5)
for k, (x, y) in enumerate([(-4.0, 4.0), (4.0, 4.0), (-4.0, 13.4), (4.0, 13.4), (0.0, 6.6), (0.0, 11.0)]):
    hoop(f"Hoop{k}", (x, y, 0.02), 0.0)
cyl("Peg", 0.025, 0.6, (0, 8.8, 0.3), M_PEG, verts=10)

# ----------------------------------------------------------------------------- treeline beyond the hedges and the wall
for k, (x, y, r) in enumerate([(-12.5, -3.0, 2.2), (-13.0, 5.0, 2.6), (-12.0, 13.0, 2.4), (12.5, -2.0, 2.3), (13.0, 6.5, 2.7), (12.2, 14.0, 2.3),
                               (0.0, 20.5, 2.9), (-7.0, -11.5, 2.4)]):
    h = r * 1.5
    tube(f"Tree{k}_Trunk", [(x, y, 0), (x + 0.1, y, h)], [0.3, 0.2], M_BARK, sides=6)
    blob(f"Tree{k}_CanopyA", r, (x, y, h + r * 0.6), M_TREELEAF, subdiv=3, amp=0.25, freq=1.2, scale=(1, 1, 0.9), seed=60 + k)
    blob(f"Tree{k}_CanopyB", r * 0.7, (x + r * 0.5, y + r * 0.3, h + r * 1.3), M_TREELEAF, subdiv=2, amp=0.2, freq=1.2, seed=70 + k)

# ----------------------------------------------------------------------------- the gardeners: playing cards with hands and feet
#   "...three gardeners... they were all ornamented with hearts? No: these were the gardeners, spades."
#   Each card is a flat oblong body with arms at the top corners, legs at the bottom corners, a head above.
CARD_W, CARD_H, CARD_T = 0.64, 0.9, 0.024
LEG_TOP = 0.5
CARD_CZ = LEG_TOP + CARD_H / 2 - 0.02

def spade_outline(size, cx, cz, inverted=False, n=26):
    raw = []
    for i in range(n):
        t = 2 * math.pi * i / n
        hx = 16 * math.sin(t) ** 3
        hy = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        raw.append((hx, -hy))               # flipped heart: point at the top, lobes below
    zs = [p[1] for p in raw]; xs = [p[0] for p in raw]
    zmin, zmax = min(zs), max(zs)
    k = size / (zmax - zmin) * 0.82
    zc = (zmin + zmax) / 2
    lobes = [((x) * k, (z - zc) * k + size * 0.09) for (x, z) in raw]
    # stem: a flared foot under the lobes
    zb = (zmin - zc) * k + size * 0.09
    stem = [(-0.03 * size, zb + 0.12 * size), (0.03 * size, zb + 0.12 * size), (0.16 * size, zb - 0.1 * size), (-0.16 * size, zb - 0.1 * size)]
    stem = list(reversed(stem))  # keep CCW in XZ
    def place(pts):
        out = []
        for (x, z) in pts:
            if inverted: x, z = -x, -z
            out.append((cx + x, cz + z))
        return out
    lob = place(lobes); st = place(stem)
    # CCW check (front-facing); flip if needed
    def area(p): return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))
    if area(lob) < 0: lob.reverse()
    if area(st) < 0: st.reverse()
    return lob, st

PIP_LAYOUT = {
    2: [(0, 0.27, False), (0, -0.27, True)],
    5: [(-0.15, 0.27, False), (0.15, 0.27, False), (0, 0, False), (-0.15, -0.27, True), (0.15, -0.27, True)],
    7: [(-0.15, 0.27, False), (0.15, 0.27, False), (0, 0.135, False), (-0.15, 0, False), (0.15, 0, False), (-0.15, -0.27, True), (0.15, -0.27, True)],
}

def gardener(cid, label, number, pos, face_to, brush_target, free_pose, lean=0.0):
    """Build a card gardener in local space (origin between the feet, front = -Y), then group and place it.
    brush_target: world point the brush tip touches (on the rose tree), or None."""
    P = label
    parts = []
    yaw = look_yaw(pos, face_to)
    to_local = (Matrix.Translation(Vector(pos)) @ Matrix.Rotation(yaw, 4, 'Z')).inverted()
    # card body (white stock), back panel (red lattice), pips and indices (ink)
    body = slab(f"{P}_Card", rounded_rect(CARD_W, CARD_H, 0.045, seg=4, cz=CARD_CZ), CARD_T, M_CARDFACE)
    parts.append(body)
    parts.append(flat_poly(f"{P}_Back", rounded_rect(CARD_W - 0.06, CARD_H - 0.06, 0.03, seg=3, cz=CARD_CZ), CARD_T / 2 + 0.0012, M_CARDBACK, front=False))
    yf = -CARD_T / 2 - 0.0012
    for k, (px, pz, inv) in enumerate(PIP_LAYOUT[number]):
        lob, st = spade_outline(0.12, px, CARD_CZ + pz, inverted=inv)
        parts.append(flat_poly(f"{P}_Pip{k}", lob, yf, M_INK)); parts.append(flat_poly(f"{P}_PipStem{k}", st, yf - 0.0003, M_INK))
    for k, (ix, iz, inv) in enumerate([(-0.25, 0.37, False), (0.25, -0.37, True)]):
        t = text_mesh(f"{P}_Index{k}", str(number), 0.075, (ix, yf - 0.0002, CARD_CZ + iz), M_INK, rot=(math.pi / 2, math.pi if inv else 0, 0), extrude=0.0003)
        parts.append(t)
        lob, st = spade_outline(0.045, ix, CARD_CZ + iz + (0.065 if inv else -0.065), inverted=inv)
        parts.append(flat_poly(f"{P}_IndexPip{k}", lob, yf, M_INK)); parts.append(flat_poly(f"{P}_IndexPipStem{k}", st, yf - 0.0003, M_INK))
    # legs and shoes from the bottom corners
    for sx in (-1, 1):
        hip = Vector((sx * 0.17, 0, LEG_TOP + 0.02)); knee = Vector((sx * 0.18, -0.015, 0.25)); ank = Vector((sx * 0.18, 0, 0.06))
        parts.append(tube(f"{P}_Leg{sx}", [hip, knee, ank], [0.024, 0.021, 0.018], M_INK, sides=7))
        parts.append(sphere(f"{P}_Shoe{sx}", 0.05, (sx * 0.185, -0.035, 0.035), M_INK, seg=10, scale=(0.75, 1.5, 0.6)))
    # head on a short neck, with a gardener's flat cap
    HZ = LEG_TOP + CARD_H + 0.1
    parts.append(tube(f"{P}_Neck", [(0, 0, LEG_TOP + CARD_H - 0.04), (0, 0, HZ - 0.06)], 0.028, M_SKIN, sides=7))
    parts.append(sphere(f"{P}_Head", 0.105, (0, 0, HZ + 0.02), M_SKIN, seg=14, scale=(0.95, 0.9, 1.08)))
    parts.append(sphere(f"{P}_Nose", 0.022, (0, -0.1, HZ + 0.01), M_SKIN, seg=8))
    for ex in (-1, 1):
        parts.append(sphere(f"{P}_Eye{ex}", 0.013, (ex * 0.038, -0.088, HZ + 0.045), M_INK, seg=6))
    parts.append(cyl(f"{P}_CapCrown", 0.1, 0.05, (0, 0.005, HZ + 0.115), M_INK, verts=14, r2=0.09))
    parts.append(cyl(f"{P}_CapPeak", 0.11, 0.012, (0, -0.03, HZ + 0.095), M_INK, verts=14))
    # arms from the top corners; the brush arm reaches for the roses
    SH = LEG_TOP + CARD_H - 0.12
    arm_objs = []
    pivot = None
    if brush_target is not None:
        tgt = to_local @ Vector(brush_target)
        side = 1 if tgt.x > 0 else -1
        sh = Vector((side * (CARD_W / 2 + 0.01), 0, SH))
        d = (tgt - sh); dist = d.length; d.normalize()
        brush_len = 0.3
        reach = min(0.56, max(0.25, dist - brush_len))
        hand = sh + d * reach
        elbow = (sh + hand) / 2 + Vector((0, 0.03, -0.07))
        arm_objs.append(as_part(tube(f"{P}_ArmBrush", [sh, elbow, hand], [0.026, 0.022, 0.02], M_INK, sides=7), "ink"))
        arm_objs.append(as_part(sphere(f"{P}_HandBrush", 0.036, hand, M_SKIN, seg=10, scale=(1, 1, 0.85)), "skin"))
        tip = hand + d * brush_len
        arm_objs.append(as_part(tube(f"{P}_BrushHandle", [hand - d * 0.06, tip - d * 0.07], [0.011, 0.013], M_BRUSHWOOD, sides=6), "wood"))
        arm_objs.append(as_part(tube(f"{P}_BrushFerrule", [tip - d * 0.075, tip - d * 0.05], [0.017, 0.018], M_TIN, sides=8), "tin"))
        arm_objs.append(as_part(tube(f"{P}_BrushBristles", [tip - d * 0.05, tip - d * 0.005, tip], [0.019, 0.016, 0.004], M_PAINT, sides=8), "paint"))
        free_side = -side
    else:
        free_side = 1
    sh2 = Vector((free_side * (CARD_W / 2 + 0.01), 0, SH))
    if free_pose == "hip":
        el2 = sh2 + Vector((free_side * 0.16, -0.02, -0.16)); h2 = Vector((free_side * (CARD_W / 2 + 0.03), -0.03, SH - 0.3))
    elif free_pose == "raised":
        el2 = sh2 + Vector((free_side * 0.15, -0.06, 0.1)); h2 = sh2 + Vector((free_side * 0.2, -0.12, 0.3))
    else:   # hanging
        el2 = sh2 + Vector((free_side * 0.08, -0.02, -0.22)); h2 = sh2 + Vector((free_side * 0.12, -0.06, -0.45))
    parts.append(tube(f"{P}_ArmFree", [sh2, el2, h2], [0.026, 0.022, 0.02], M_INK, sides=7))
    parts.append(sphere(f"{P}_HandFree", 0.036, h2, M_SKIN, seg=10, scale=(1, 1, 0.85)))
    # brush arm under its own shoulder pivot so a clip can swing it (named "<Label>_PaintArm")
    g = group(cid, parts, (0, 0, 0))
    if arm_objs:
        pivot = group(f"{P}_PaintArm", arm_objs, sh)
        pivot.parent = g; pivot.matrix_parent_inverse = g.matrix_world.inverted()
        CHILD_PREFIX[pivot.name] = pivot.name
    g.rotation_euler = (lean, 0, yaw)
    g.location = pos
    bpy.context.view_layer.update()
    CHILD_PREFIX[cid] = P
    DYNAMIC.append(g)
    return g, yaw

def around(angle_deg, r):
    a = math.radians(angle_deg)
    return Vector((TREE.x + math.cos(a) * r, TREE.y + math.sin(a) * r, 0.0))

def crown_point_towards(pos, z):
    d = Vector((pos.x - TREE.x, pos.y - TREE.y, 0)).normalized()
    # walk inwards from outside until we are on the crown's surface at height z
    for k in range(80):
        rr = 1.6 - k * 0.02
        p = Vector((TREE.x + d.x * rr, TREE.y + d.y * rr, z))
        if any((p - c).length < r * 1.05 for (c, r, _) in crown_surf):
            return p
    return Vector((TREE.x + d.x * 0.9, TREE.y + d.y * 0.9, z))

POS_TWO = around(150, 1.62)
POS_SEVEN = around(212, 1.62)
POS_FIVE = around(285, 1.62)
cheat = lambda pos, k: READER * k + Vector((TREE.x, TREE.y, 0)) * (1 - k)   # stage blocking: half turned to the gate
two, yaw_two = gardener("char.two", "Two", 2, POS_TWO, cheat(POS_TWO, 0.55), crown_point_towards(POS_TWO, 1.62), "hip")
seven, yaw_seven = gardener("char.seven", "Seven", 7, POS_SEVEN, cheat(POS_SEVEN, 0.7), crown_point_towards(POS_SEVEN, 1.45), "hanging")
five, yaw_five = gardener("char.five", "Five", 5, POS_FIVE, cheat(POS_FIVE, 0.6), crown_point_towards(POS_FIVE, 1.5), "raised")

# fx.paint-splash: Seven jogged Five's elbow; a splash of red across Five's card. Built in Five's local frame.
splash = []
def splat(name, cx, cz, r, n=18, seed=0.0, y=-CARD_T / 2 - 0.0025):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * (0.75 + 0.4 * noise.noise(Vector((math.cos(a) * 2.1 + seed, math.sin(a) * 2.1, seed))) + (0.35 if i % 5 == 0 else 0.0))
        pts.append((cx + rr * math.cos(a), cz + rr * math.sin(a)))
    return flat_poly(name, pts, y, M_PAINT)
splash.append(splat("Splash_Main", -0.08, CARD_CZ + 0.12, 0.085, n=22, seed=1.3))
for k, (dx, dz, r) in enumerate([(0.06, 0.2, 0.022), (-0.2, 0.05, 0.018), (0.1, 0.02, 0.016), (-0.15, 0.24, 0.014), (0.02, -0.02, 0.012), (-0.24, 0.17, 0.01)]):
    splash.append(splat(f"Splash_Drop{k}", -0.08 + dx, CARD_CZ + 0.12 + dz, r, n=9, seed=k + 3.0))
# two runs of paint dripping down the card
for k, (x0, l) in enumerate([(-0.11, 0.16), (-0.04, 0.11)]):
    pts = [(x0 - 0.008, CARD_CZ + 0.08), (x0 + 0.008, CARD_CZ + 0.08), (x0 + 0.006, CARD_CZ + 0.08 - l), (x0, CARD_CZ + 0.08 - l - 0.012), (x0 - 0.006, CARD_CZ + 0.08 - l)]
    splash.append(flat_poly(f"Splash_Run{k}", list(reversed(pts)), -CARD_T / 2 - 0.0024, M_PAINT))
fx_splash = group("fx.paint-splash", splash, (0, 0, 0))
fx_splash.rotation_euler = (0, 0, yaw_five); fx_splash.location = POS_FIVE
CHILD_PREFIX["fx.paint-splash"] = "Splash"
DYNAMIC.append(fx_splash)

# ----------------------------------------------------------------------------- prop.paint-pot: a tin pail of red paint, brushes
POT = Vector((TREE.x - 0.42, TREE.y - 1.22, 0.0))
pot_parts = []
pot_parts.append(lathe("Pot_Pail", [(0.0, 0.0), (0.12, 0.0), (0.125, 0.01), (0.15, 0.24), (0.158, 0.25), (0.152, 0.255), (0.142, 0.245), (0.118, 0.02), (0.0, 0.02)], POT, M_TIN, steps=20))
pot_parts.append(lathe("Pot_Paint", [(0.0, 0.205), (0.143, 0.205)], POT, M_PAINT, steps=20))
for k, (a, l) in enumerate([(0.3, 0.09), (1.9, 0.14), (2.6, 0.06), (4.4, 0.11), (5.5, 0.08)]):
    c, s = math.cos(a), math.sin(a)
    p0 = POT + Vector((c * 0.157, s * 0.157, 0.25)); p1 = POT + Vector((c * (0.157 - 0.008 * l), s * (0.157 - 0.008 * l), 0.25 - l))
    pot_parts.append(tube(f"Pot_Drip{k}", [p0, p1, p1 + Vector((0, 0, -0.008))], [0.009, 0.007, 0.002], M_PAINT, sides=5))
pot_parts.append(tube("Pot_Handle", [POT + Vector((math.cos(a) * 0.155, 0, 0.23 + 0.1 * math.sin(a))) for a in [k * math.pi / 10 for k in range(11)]], 0.004, M_TIN, sides=5, caps=False))
for k, (yaw_b, tilt) in enumerate([(0.6, 0.35), (2.5, 0.45)]):
    base = POT + Vector((math.cos(yaw_b) * 0.04, math.sin(yaw_b) * 0.04, 0.06))
    d = Vector((math.cos(yaw_b) * math.sin(tilt), math.sin(yaw_b) * math.sin(tilt), math.cos(tilt)))
    pot_parts.append(tube(f"Pot_Brush{k}_Bristles", [base, base + d * 0.07], [0.006, 0.02], M_PAINT, sides=8))
    pot_parts.append(tube(f"Pot_Brush{k}_Ferrule", [base + d * 0.07, base + d * 0.1], 0.019, M_TIN, sides=8))
    pot_parts.append(tube(f"Pot_Brush{k}_Handle", [base + d * 0.1, base + d * 0.36], [0.013, 0.01], M_BRUSHWOOD, sides=6))
# a spare brush on the gravel, and spilt paint
spare = POT + Vector((0.3, -0.08, 0.016))
sd = Vector((0.9, 0.42, 0.0)).normalized()
pot_parts.append(tube("Pot_Spare_Handle", [spare, spare + sd * 0.24], 0.012, M_BRUSHWOOD, sides=6))
pot_parts.append(tube("Pot_Spare_Ferrule", [spare - sd * 0.03, spare], 0.017, M_TIN, sides=8))
pot_parts.append(tube("Pot_Spare_Bristles", [spare - sd * 0.1, spare - sd * 0.03], [0.012, 0.018], M_PAINT, sides=8))
spill = []
for i in range(16):
    a = 2 * math.pi * i / 16
    rr = 0.11 * (0.8 + 0.35 * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, 4.2))))
    spill.append((POT.x + 0.2 + rr * math.cos(a) * 1.4, POT.y - 0.12 + rr * math.sin(a)))
me = bpy.data.meshes.new("Pot_Spill"); bm = bmesh.new(); vs = [bm.verts.new((x, y, 0.018)) for (x, y) in spill]; bm.faces.new(vs); bm.to_mesh(me); bm.free()
o = bpy.data.objects.new("Pot_Spill", me); me.materials.append(M_PAINT); link(o); pot_parts.append(o)
DYNAMIC.append(group("prop.paint-pot", pot_parts, POT)); CHILD_PREFIX["prop.paint-pot"] = "Pot"

# ----------------------------------------------------------------------------- anchors (names are the manifest's anchor ids)
anchor("reader.gate", READER)
READER_TREE = Vector((1.0, -5.45, 0.0))
anchor("reader.rose-tree", READER_TREE)
anchor("rose-tree.base", TREE)
anchor("rose-tree.crown", CROWN_ANCHOR)
anchor("gardener.two", POS_TWO)
anchor("gardener.five", POS_FIVE)
anchor("gardener.seven", POS_SEVEN)
anchor("paint.pot", POT)
anchor("garden.path", (0.0, -1.2, 0.0))
anchor("sky", (TREE.x, TREE.y, 9.0))
anchor("scene.centre", ((READER.x + TREE.x) / 2 + 0.1, (READER.y + TREE.y) / 2 + 0.3, 0.0))

# ----------------------------------------------------------------------------- daylight: sun + sky (+ a soft fill); names are the manifest's light ids
SUN_AZ, SUN_EL = math.radians(215), math.radians(38)       # afternoon sun from behind the reader's left shoulder
sun_dir = Vector((math.cos(SUN_EL) * math.cos(SUN_AZ), math.cos(SUN_EL) * math.sin(SUN_AZ), math.sin(SUN_EL)))  # towards the sun
def light(name, kind, energy, color, loc, aim=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if aim is not None:
        lo.rotation_euler = Vector(aim).to_track_quat('-Z', 'Y').to_euler()
    return link(lo)
sun = light("light.sun", 'SUN', 4.0, (1.0, 0.93, 0.82), (TREE.x, TREE.y, 12.0), aim=-sun_dir, angle=math.radians(1.2))
sky_l = light("light.sky", 'SUN', 0.35, (0.62, 0.76, 1.0), (0.0, 4.0, 14.0), aim=(0.15, -0.2, -1.0), angle=math.radians(60))
fill = light("light.fill", 'SPOT', 180.0, (1.0, 0.94, 0.86), (-0.6, -6.8, 4.2), aim=Vector((TREE.x, TREE.y, 1.0)) - Vector((-0.6, -6.8, 4.2)),
             spot_size=math.radians(60), spot_blend=0.6, shadow_soft_size=1.5)

world = bpy.data.worlds.new("Garden"); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]
sky = wn.nodes.new("ShaderNodeTexSky")
try:
    sky.sky_type = 'MULTIPLE_SCATTERING'
except Exception:
    sky.sky_type = 'SINGLE_SCATTERING'
sky.sun_disc = False
sky.sun_elevation = SUN_EL
sky.sun_rotation = SUN_AZ - math.pi / 2
sky.air_density = 1.0; sky.aerosol_density = 1.6
wn.links.new(sky.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.18

# ----------------------------------------------------------------------------- cameras for preview stills (reader eye height 1.62 m)
def camera(name, loc, look_at, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_start = 0.05
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    d = Vector(look_at) - Vector(loc)
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return co
EYE = 1.62
cams = [
    camera("Cam_Gate", (READER.x, READER.y, EYE), (TREE.x - 0.4, TREE.y + 1.0, 1.25), lens=20),
    camera("Cam_RoseTree", (READER_TREE.x, READER_TREE.y, EYE), (TREE.x - 0.2, TREE.y, 1.7), lens=22),
    camera("Cam_Gardeners", (TREE.x + 1.9, TREE.y - 3.6, 1.45), (TREE.x - 0.5, TREE.y - 0.2, 1.15), lens=26),
    camera("Cam_Ground", (-1.4, READER.y - 0.2, 1.75), (0.6, 8.0, 0.4), lens=18),
    camera("Cam_Painted", (READER_TREE.x, READER_TREE.y, EYE), (TREE.x - 0.2, TREE.y, 1.7), lens=22),
]

def set_hidden(obj, hidden):
    for o in [obj] + list(obj.children_recursive):
        o.hide_render = hidden; o.hide_viewport = hidden

# fx groups start hidden, as in the app (the script places them)
for nm in ("fx.red-roses", "fx.paint-splash"):
    set_hidden(bpy.data.objects[nm], True)

# save the art-direction .blend before any baking destroys procedural materials
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "queens_croquet_ground_source.blend"))

# ----------------------------------------------------------------------------- render
def report_budget():
    ms = [o for o in COLL.objects if o.type == 'MESH']
    deps = bpy.context.evaluated_depsgraph_get()
    tris = 0; by = {}
    for o in ms:
        ev = o.evaluated_get(deps); me = ev.to_mesh(); me.calc_loop_triangles(); n = len(me.loop_triangles); ev.to_mesh_clear()
        tris += n; key = o.name.split("_")[0].rstrip("0123456789"); by[key] = by.get(key, 0) + n
    mats = {o.data.materials[0].name for o in ms if o.parent is None and o.data.materials}
    print(f"BUDGET pre-merge objects={len(ms)} tris={tris} static_materials={len(mats)}")
    print("BUDGET by prefix:", sorted(by.items(), key=lambda kv: -kv[1])[:14])
report_budget()
if args.render:
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    for c in cams:
        painted = c.name == "Cam_Painted"
        if painted:
            for nm in ("fx.red-roses", "fx.paint-splash"): set_hidden(bpy.data.objects[nm], False)
        scene.camera = c
        scene.render.filepath = os.path.join(OUT, f"render_{c.name[4:].lower()}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)
        if painted:
            for nm in ("fx.red-roses", "fx.paint-splash"): set_hidden(bpy.data.objects[nm], True)

# ----------------------------------------------------------------------------- bake + merge + export for Unity
def tri_count(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)

def join_objs(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = name
    bpy.ops.object.select_all(action='DESELECT')
    return o

def patch_sun_intensities(glb):
    """Blender 5.2.3's glTF exporter writes every SUN light at strength 1 (683 lux) whatever its energy.
    Rewrite the directional intensities in the GLB's JSON chunk from the Blender lights (W/m2 * 683 = lux)."""
    import json, struct
    want = {o.name: o.data.energy * 683.0 for o in COLL.objects if o.type == 'LIGHT' and o.data.type == 'SUN'}
    if glb.endswith(".gltf"):
        with open(glb) as f: g = json.load(f)
        for l in g.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", []):
            if l.get("type") == "directional" and l.get("name") in want: l["intensity"] = want[l["name"]]
        with open(glb, "w") as f: json.dump(g, f, indent=1)
        print("patched sun intensities (lux)", want); return
    with open(glb, "rb") as f: data = f.read()
    jlen = struct.unpack_from("<I", data, 12)[0]
    g = json.loads(data[20:20 + jlen]); rest = data[20 + jlen:]
    for l in g.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", []):
        if l.get("type") == "directional" and l.get("name") in want: l["intensity"] = want[l["name"]]
    js = json.dumps(g, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + len(rest)) + struct.pack("<II", len(js), 0x4E4F534A) + js + rest
    with open(glb, "wb") as f: f.write(out)
    print("patched sun intensities (lux)", want)

def bake_and_export():
    # assets are exported visible; Unity's SceneDirector hides what the script has not placed yet
    for o in COLL.objects:
        o.hide_render = False; o.hide_viewport = False
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes:
        o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')       # apply modifiers everywhere
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    # static meshes (no parent): one mesh per material
    groups = {}
    for o in meshes:
        if o.parent is not None or not o.data.materials: continue
        groups.setdefault(o.data.materials[0].name, []).append(o)
    merged = [join_objs(objs, "MESH_" + mname[2:]) for mname, objs in groups.items()]
    # dynamic groups: inside every empty (asset group or a pivot inside one), one mesh per material
    dynamic_members = []
    empties = [o for o in COLL.objects if o.type == 'EMPTY' and o.name in CHILD_PREFIX]
    for e in empties:
        kids = [c for c in e.children if c.type == 'MESH']
        by_mat = {}
        for c in kids: by_mat.setdefault(c.data.materials[0].name, []).append(c)
        for mname, objs in by_mat.items():
            nm = f"{CHILD_PREFIX[e.name]}_Mesh" if mname == "M_PaintArm" else f"{CHILD_PREFIX[e.name]}_{mname[2:]}"
            dynamic_members.append(join_objs(objs, nm))
    scene.cycles.samples = 1
    # 1-sample bakes on the CPU: on Metal every new material triggers a background kernel specialisation
    # compile, which crashed Blender 5.2.3 mid-bake (MetalKernelPipeline::compile); the CPU is quick enough here
    scene.cycles.device = 'CPU'
    scene.render.bake.margin = 6
    scene.render.bake.use_selected_to_active = False
    size_for = {"M_Lawn": args.tex * 2, "M_CroquetLawn": args.tex, "M_Gravel": args.tex, "M_Hedge": args.tex, "M_Brick": args.tex // 2,
                "M_Stone": args.tex // 2, "M_TreeLeaves": args.tex // 2, "M_RoseLeaves": args.tex // 2, "M_Bark": args.tex // 4}
    dyn_size = {"RoseTree_RoseLeaves": args.tex // 2, "RoseTree_RoseWhite": args.tex // 4, "RoseTree_RoseRed": args.tex // 4, "RoseTree_Bark": args.tex // 4,
                "RedRoses_RoseRed": args.tex // 4}
    for o in dynamic_members:
        m = o.data.materials[0]
        if m.users > 1:
            m2 = m.copy(); m2.name = m.name + "__" + o.name; o.data.materials[0] = m2
    for o in merged + dynamic_members:
        m = o.data.materials[0]; nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        base = m.name.split("__")[0]
        if o.parent is None:
            size = size_for.get(base, args.tex // 4)
        else:
            size = dyn_size.get(o.name, args.tex // 4 if base in ("M_CardFace", "M_CardBack") else args.tex // 8)
        size = max(size, 64)
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
        metallic = bsdf.inputs["Metallic"].default_value
        for n in list(nt.nodes):
            if n not in baked.values(): nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
        nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Base Color"])
        nt.links.new(baked["Roughness"].outputs["Color"], nb.inputs["Roughness"])
        nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(baked["Normal"].outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], nb.inputs["Normal"])
        nb.inputs["Metallic"].default_value = metallic
    for c in cams: bpy.data.objects.remove(c)
    glb = os.path.join(OUT, "queens_croquet_ground.gltf")   # .gltf + textures/: Unity imports the images as compressed (ASTC) textures; embedded GLB images import uncompressed
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False)  # JPEG: keeps the GLB under GitHub's 100 MB file limit; Unity recompresses to ASTC anyway
    patch_sun_intensities(glb)
    allm = merged + dynamic_members
    tris = sum(tri_count(o) for o in allm)
    verts = sum(len(o.data.vertices) for o in allm)
    print(f"EXPORT {glb} meshes={len(allm)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(allm)}\nverts={verts}\ntris={tris}\n")
        for o in sorted(allm, key=lambda o: -tri_count(o)):
            f.write(f"{o.name} parent={o.parent.name if o.parent else '-'} verts={len(o.data.vertices)} tris={tri_count(o)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "queens_croquet_ground_baked.blend"))


if args.bake or args.export:
    bake_and_export()
print("DONE")
