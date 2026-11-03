"""
Fable: the Throne Room of the Emerald City (The Wonderful Wizard of Oz, chapter XI, "The Wonderful City of Oz").

"She opened a little door and Dorothy walked boldly through and found herself in a wonderful place. It was a big,
round room with a high arched roof, and the walls and ceiling and floor were covered with large emeralds set closely
together. In the center of the roof was a great light, as bright as the sun, which made the emeralds sparkle in a
wonderful manner. But what interested Dorothy most was the big throne of green marble that stood in the middle of
the room. It was shaped like a chair and sparkled with gems, as did everything else."
("... I spoke to him as he sat behind his screen ...")

A round rotunda 9.2 m across: a green marble plinth, sixteen marble pilasters and a cornice; between them the walls
are set close with step-cut emeralds; sixteen marble ribs carry the high arched roof (also set with emeralds) up to
the great light, a frosted lens in a gold ring at the crown. The floor is concentric rings of table-cut emeralds in
pale marble, with a worn marble walk from the little door to the stepped round dais, and the big green marble throne
(shaped like a chair, set with cabochon emeralds in gold bezels, a green velvet cushion) stands on the dais in the
middle of the room. It is empty: no Head, no Lady, no Beast, no Ball of Fire, no characters. A folding green silk
screen stands against the west wall (the screen the Wizard sits behind).

Colour: everything is green, as the spectacles make it, but the greens are deep and moderately desaturated, the
settings are pale grey-green marble and the light is warm, so the room stays comfortable for long reading. The
emerald "sparkle" is restrained: flat-topped step cuts (no tiny facets), moderate roughness, inner glow baked into
the base colour. Nothing glitters or shimmers.

Builds the room procedurally (no downloaded models, textures or HDRIs) with PBR node materials and one light (the
great light in the roof), then (by flag) renders Cycles stills, bakes materials to textures, merges static meshes by
material and exports a .gltf + .bin + textures/ for Unity.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet (floor, z=0), a little inside the little door (south wall)
  anchor.reader.look      eye height (1.55 m), 2 m ahead along the facing direction (north, a little west of the throne)
  anchor.scene.centre     the room's floor centre (under the throne)
  anchor.room.throne (the seat), anchor.room.door, anchor.room.screen, anchor.roof.light
  Lamp.roof (POINT, the great light in the centre of the roof; "Lamp" = baked by FableBuild's indoor rule)
  MESH_GreatLight (the emissive lens of the great light)

Axes: metres, Blender +Z up. The room is centred on the origin, radius 4.6 m; the little door is in the south wall
(-y); the throne stands at the centre facing the door (-y).

Run headless:
  blender -b -P blender/build_emerald_throne_room.py -- --out out/emerald-throne-room --render --quick --res 900
  blender -b -P blender/build_emerald_throne_room.py -- --out out/emerald-throne-room --bake --export --tex 2048
  blender -b -P blender/build_emerald_throne_room.py -- --out out/emerald-throne-room --render --res 1400 --samples 96
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/emerald-throne-room")
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
R = 5.2                      # "a big, round room"
WALL_H = 3.6                 # cornice line, where the arched roof springs
RISE = 3.0                   # "a high arched roof": crown at ~6.6 m
OCU_R = 0.62                 # the great light's ring (radius) at the crown
PLINTH_H = 0.62
CORNICE_H = 0.34
NBAY = 16
PIL_W, PIL_D = 0.40, 0.13
DOOR_W, DOOR_H = 0.92, 2.02  # "a little door"
DAIS = [(1.85, 0.15), (1.58, 0.30), (1.32, 0.45)]   # (radius, top) of the three round steps
THRONE_Z = DAIS[-1][1]
READER = (-0.60, -3.95)
LOOK_YAW = math.radians(20.0)  # facing north, turned 20 deg west: the throne sits just right of the page
LIGHT_Z = None               # set from the dome profile below
SCREEN_AZ = math.radians(191.0)

def dome_pt(t):
    """The roof profile (quarter ellipse): radius and height at parameter t (0 = springing, pi/2 = crown)."""
    return R * math.cos(t), WALL_H + RISE * math.sin(t)
T_TOP = math.acos(OCU_R / R)
CROWN_Z = dome_pt(T_TOP)[1]
LIGHT_Z = CROWN_Z - 0.10

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

COLL = bpy.data.collections.new("EmeraldThroneRoom")
scene.collection.children.link(COLL)
def link(obj):
    COLL.objects.link(obj); return obj

# ----------------------------------------------------------------------------- material helpers (from build_kansas_farmhouse.py)
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (900, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (600, 0)
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

def math_(nt, op, a, b=None, c=None, clamp=False):
    n = node(nt, "ShaderNodeMath", operation=op); n.use_clamp = clamp
    for i, v in enumerate((a, b, c)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]

def mix_rgb(nt, blend, fac, a, b):
    n = node(nt, "ShaderNodeMix", data_type='RGBA', blend_type=blend)
    for sock, v in ((n.inputs["Factor"], fac), (n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, (int, float)): sock.default_value = v
        elif isinstance(v, tuple): sock.default_value = v
        else: nt.links.new(v, sock)
    return n.outputs[2]

def mix_f(nt, fac, a, b):
    n = node(nt, "ShaderNodeMix", data_type='FLOAT')
    for sock, v in ((n.inputs["Factor"], fac), (n.inputs[2], a), (n.inputs[3], b)):
        if isinstance(v, (int, float)): sock.default_value = v
        else: nt.links.new(v, sock)
    return n.outputs[0]

def maprange(nt, v, f0, f1, t0, t1, interp='LINEAR'):
    n = node(nt, "ShaderNodeMapRange", interpolation_type=interp); n.clamp = True
    nt.links.new(v, n.inputs["Value"])
    n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = f0, f1
    n.inputs["To Min"].default_value, n.inputs["To Max"].default_value = t0, t1
    return n.outputs["Result"]

def bump_from(nt, b, height_socket, strength, distance):
    bump = node(nt, "ShaderNodeBump", (350, -400)); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return bump

def c4(c): return (c[0], c[1], c[2], 1)

def obj_xyz(nt):
    tc = node(nt, "ShaderNodeTexCoord", (-2400, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-2200, 0))
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    return tc.outputs["Object"], sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]

def noise_tex(nt, vec, scale, detail=6.0, rough=0.6, distortion=0.0, w=None):
    n = node(nt, "ShaderNodeTexNoise", noise_dimensions='4D' if w is not None else '3D')
    n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough; n.inputs["Distortion"].default_value = distortion
    if w is not None: n.inputs["W"].default_value = w
    nt.links.new(vec, n.inputs["Vector"])
    return n

def marble_color(nt, vec, ground, vein, deep, scale=1.0, seed=0.0, vein_amt=1.0):
    """Green marble: cloudy ground, darker drifts and thin pale veins that wander (distorted wave bands)."""
    mp = node(nt, "ShaderNodeMapping"); nt.links.new(vec, mp.inputs["Vector"])
    mp.inputs["Scale"].default_value = (scale, scale * 0.8, scale * 1.1)
    mp.inputs["Rotation"].default_value = (0.6, 0.35 + seed, 0.9)
    mp.inputs["Location"].default_value = (seed * 7.0, seed * 3.0, 0)
    cloud = noise_tex(nt, mp.outputs["Vector"], 1.6, 8.0, 0.62, 0.3)
    cr = ramp(nt, [(0.30, c4(deep)), (0.52, c4(ground)), (0.70, c4(tuple(min(1, x * 1.18) for x in ground)))])
    nt.links.new(cloud.outputs["Fac"], cr.inputs["Fac"])
    vn = noise_tex(nt, mp.outputs["Vector"], 1.1, 7.0, 0.58, 0.9, w=seed + 0.5)
    ridge = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', vn.outputs["Fac"], 0.5))
    thin = maprange(nt, ridge, 0.0, 0.012, 1.0, 0.0, 'SMOOTHSTEP')
    halo = maprange(nt, ridge, 0.0, 0.05, 0.35, 0.0, 'SMOOTHSTEP')
    vfac = math_(nt, 'MULTIPLY', math_(nt, 'MAXIMUM', thin, halo), 0.45 * vein_amt)
    return mix_rgb(nt, 'MIX', vfac, cr.outputs["Color"], c4(vein)), cloud.outputs["Fac"]

def gem_field(nt, cu, cv, xyz, seed, tones, setting, fill=(0.93, 0.93), table=0.72, stagger=True, rough_gem=0.20, rough_set=0.62):
    """Close-set step-cut emeralds in cell space (cu, cv: one cell per stone). Returns (colour, roughness, height, mask).
    Each stone: an octagonal step cut (flat table, bevelled crown), its own tone, a soft inner glow toward the table
    and faint inclusions ("jardin"). The setting between stones is pale stone, not metal."""
    row = math_(nt, 'FLOOR', cv); fv = math_(nt, 'FRACT', cv)
    cu2 = math_(nt, 'ADD', cu, math_(nt, 'MULTIPLY', math_(nt, 'FLOORED_MODULO', row, 2.0), 0.5)) if stagger else cu
    col = math_(nt, 'FLOOR', cu2); fu = math_(nt, 'FRACT', cu2)
    x = math_(nt, 'ABSOLUTE', math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', fu, 0.5), 0.5 * fill[0]))
    y = math_(nt, 'ABSOLUTE', math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', fv, 0.5), 0.5 * fill[1]))
    octd = math_(nt, 'MAXIMUM', math_(nt, 'MAXIMUM', x, y), math_(nt, 'MULTIPLY', math_(nt, 'ADD', x, y), 0.60))
    height = maprange(nt, octd, 1.0, table, 0.0, 1.0, 'SMOOTHSTEP')
    mask = maprange(nt, octd, 1.03, 0.97, 0.0, 1.0)
    cid = node(nt, "ShaderNodeCombineXYZ"); nt.links.new(col, cid.inputs[0]); nt.links.new(row, cid.inputs[1]); cid.inputs[2].default_value = seed
    wn = node(nt, "ShaderNodeTexWhiteNoise", noise_dimensions='3D'); nt.links.new(cid.outputs[0], wn.inputs["Vector"])
    tr = ramp(nt, [(i / (len(tones) - 1), c4(t)) for i, t in enumerate(tones)])
    nt.links.new(wn.outputs["Value"], tr.inputs["Fac"])
    glow = maprange(nt, octd, 1.0, 0.0, 0.62, 1.22)                       # darker crown bevel, lighter toward the table
    stone = mix_rgb(nt, 'MULTIPLY', 1.0, tr.outputs["Color"], (1, 1, 1, 1))
    gl = node(nt, "ShaderNodeCombineColor"); nt.links.new(glow, gl.inputs[0]); nt.links.new(glow, gl.inputs[1]); nt.links.new(glow, gl.inputs[2])
    stone = mix_rgb(nt, 'MULTIPLY', 1.0, stone, gl.outputs[0])
    # step-cut facets on the crown: three bands that catch the light differently (baked, so they never shimmer)
    bev = maprange(nt, octd, table, 1.0, 0.0, 1.0)
    fr = ramp(nt, [(0.0, (1.0, 1.0, 1.0, 1)), (0.02, (1.30, 1.32, 1.28, 1)), (0.30, (0.80, 0.80, 0.80, 1)), (0.62, (1.12, 1.13, 1.10, 1)), (0.9, (0.7, 0.7, 0.7, 1))], interp='CONSTANT')
    nt.links.new(bev, fr.inputs["Fac"])
    stone = mix_rgb(nt, 'MULTIPLY', 1.0, stone, fr.outputs["Color"])
    inc = noise_tex(nt, xyz, 38.0, 4.0, 0.55, 0.4, w=seed)
    incr = ramp(nt, [(0.35, (0.82, 0.82, 0.82, 1)), (0.6, (1.0, 1.0, 1.0, 1)), (0.8, (1.12, 1.14, 1.10, 1))])
    nt.links.new(inc.outputs["Fac"], incr.inputs["Fac"])
    stone = mix_rgb(nt, 'MULTIPLY', 1.0, stone, incr.outputs["Color"])
    colr = mix_rgb(nt, 'MIX', mask, setting, stone)
    rg = math_(nt, 'ADD', rough_gem, math_(nt, 'MULTIPLY', wn.outputs["Value"], 0.08))
    rough = mix_f(nt, mask, rough_set, rg)
    return colr, rough, math_(nt, 'MULTIPLY', height, mask), mask

TWO_PI = 2 * math.pi
EMERALD_TONES = [(0.014, 0.055, 0.034), (0.022, 0.080, 0.048), (0.028, 0.098, 0.056), (0.024, 0.090, 0.064), (0.036, 0.104, 0.052), (0.018, 0.070, 0.052)]
SETTING_WALL = (0.060, 0.090, 0.068)
SETTING_FLOOR = (0.085, 0.115, 0.09)

def emerald_wall(name):
    """The walls between the pilasters: rows of upright step-cut emeralds, an integer count round the room."""
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    gw, gh = 0.15, 0.19
    N = round(TWO_PI * R / gw)
    ang = math_(nt, 'ARCTAN2', Y, X)
    cu = math_(nt, 'MULTIPLY', ang, N / TWO_PI)
    cv = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', Z, PLINTH_H), gh)
    col, rough, h, mask = gem_field(nt, cu, cv, xyz, 3.0, EMERALD_TONES, c4(SETTING_WALL))
    nt.links.new(col, b.inputs["Base Color"]); nt.links.new(rough, b.inputs["Roughness"])
    bump_from(nt, b, h, 0.55, 0.006)
    return m

def emerald_dome(name):
    """The arched roof: rows following the curve of the roof, fewer stones per row toward the crown."""
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    gw, gh = 0.17, 0.19
    rr = node(nt, "ShaderNodeVectorMath", operation='LENGTH')
    cxy = node(nt, "ShaderNodeCombineXYZ"); nt.links.new(X, cxy.inputs[0]); nt.links.new(Y, cxy.inputs[1])
    nt.links.new(cxy.outputs[0], rr.inputs[0]); r = rr.outputs["Value"]
    t = math_(nt, 'ARCTAN2', math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', Z, WALL_H), RISE), math_(nt, 'DIVIDE', r, R))
    RM = 0.5 * (R + RISE)
    cv = math_(nt, 'MULTIPLY', t, RM / gh)
    rowc = math_(nt, 'MULTIPLY', math_(nt, 'ADD', math_(nt, 'FLOOR', cv), 0.5), gh / RM)
    nrow = math_(nt, 'MAXIMUM', math_(nt, 'ROUND', math_(nt, 'MULTIPLY', math_(nt, 'COSINE', rowc), TWO_PI * R / gw)), 8.0)
    ang = math_(nt, 'ARCTAN2', Y, X)
    cu = math_(nt, 'MULTIPLY', math_(nt, 'DIVIDE', ang, TWO_PI), nrow)
    col, rough, h, mask = gem_field(nt, cu, cv, xyz, 7.0, EMERALD_TONES, c4(SETTING_WALL), fill=(0.94, 0.93), stagger=False)
    nt.links.new(col, b.inputs["Base Color"]); nt.links.new(rough, b.inputs["Roughness"])
    bump_from(nt, b, h, 0.5, 0.008)
    return m

def emerald_floor(name):
    """The floor: concentric rings of table-cut emeralds in pale marble, a marble border at the wall and a worn marble
    walk from the little door to the dais (duller, scuffed, the way people come in). Dust gathers in the setting at
    the wall foot."""
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    gw, gh = 0.25, 0.20
    rr = node(nt, "ShaderNodeVectorMath", operation='LENGTH')
    cxy = node(nt, "ShaderNodeCombineXYZ"); nt.links.new(X, cxy.inputs[0]); nt.links.new(Y, cxy.inputs[1])
    nt.links.new(cxy.outputs[0], rr.inputs[0]); r = rr.outputs["Value"]
    cv = math_(nt, 'DIVIDE', r, gh)
    rowr = math_(nt, 'MULTIPLY', math_(nt, 'ADD', math_(nt, 'FLOOR', cv), 0.5), gh)
    nrow = math_(nt, 'MAXIMUM', math_(nt, 'ROUND', math_(nt, 'MULTIPLY', rowr, TWO_PI / gw)), 6.0)
    ang = math_(nt, 'ARCTAN2', Y, X)
    cu = math_(nt, 'MULTIPLY', math_(nt, 'DIVIDE', ang, TWO_PI), nrow)
    tones = [tuple(min(1, v * 1.3) for v in t) for t in EMERALD_TONES]
    gcol, grough, gh_, gmask = gem_field(nt, cu, cv, xyz, 11.0, tones, c4(SETTING_FLOOR), fill=(0.94, 0.92), table=0.78, stagger=False, rough_gem=0.26, rough_set=0.55)
    mcol, mcloud = marble_color(nt, xyz, (0.19, 0.25, 0.19), (0.34, 0.40, 0.33), (0.11, 0.16, 0.12), scale=0.9, seed=0.3)
    # marble walk from the door (y<0, |x|<0.62) and the border ring at the wall (r > R-0.32): square slabs, fine joints
    ax = math_(nt, 'ABSOLUTE', X)
    walk = math_(nt, 'MULTIPLY', maprange(nt, ax, 0.63, 0.60, 0.0, 1.0), maprange(nt, Y, -0.9, -1.1, 0.0, 1.0))
    border = maprange(nt, r, R - 0.34, R - 0.31, 0.0, 1.0)
    slab = math_(nt, 'MAXIMUM', walk, border)
    sy = math_(nt, 'FRACT', math_(nt, 'DIVIDE', Y, 0.62)); sx = math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', X, 0.62), 0.62))
    sa = math_(nt, 'FRACT', math_(nt, 'MULTIPLY', ang, 32.0 / TWO_PI))
    def joint(f):
        return math_(nt, 'MULTIPLY', maprange(nt, f, 0.0, 0.012, 0.0, 1.0), maprange(nt, f, 0.988, 1.0, 1.0, 0.0))
    jw = math_(nt, 'MULTIPLY', joint(sy), joint(sx))
    jb = joint(sa)
    j = mix_f(nt, walk, jb, jw)
    # the walk's own edge: a narrow band of darker marble
    edge = math_(nt, 'MULTIPLY', maprange(nt, ax, 0.50, 0.53, 0.0, 1.0), walk)
    mcol2 = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', edge, 0.45), mcol, (0.45, 0.55, 0.47, 1))
    mcol3 = mix_rgb(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, j), mcol2, (0.45, 0.5, 0.45, 1))
    col = mix_rgb(nt, 'MIX', slab, gcol, mcol3)
    # wear down the middle of the walk: a little duller and lighter where feet go
    wear = math_(nt, 'MULTIPLY', walk, maprange(nt, ax, 0.42, 0.05, 0.0, 1.0))
    wn = noise_tex(nt, xyz, 3.0, 5.0, 0.6)
    wear = math_(nt, 'MULTIPLY', wear, maprange(nt, wn.outputs["Fac"], 0.35, 0.65, 0.4, 1.0))
    col = mix_rgb(nt, 'SCREEN', math_(nt, 'MULTIPLY', wear, 0.08), col, (1, 1, 1, 1))
    # dust in the setting near the wall foot
    dust = math_(nt, 'MULTIPLY', maprange(nt, r, R - 0.9, R - 0.36, 0.0, 1.0), math_(nt, 'SUBTRACT', 1.0, gmask))
    dust = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', dust, math_(nt, 'SUBTRACT', 1.0, slab)), 0.5)
    col = mix_rgb(nt, 'MIX', dust, col, (0.22, 0.24, 0.19, 1))
    nt.links.new(col, b.inputs["Base Color"])
    mr = math_(nt, 'ADD', 0.30, math_(nt, 'MULTIPLY', wear, 0.22))
    rough = mix_f(nt, slab, grough, math_(nt, 'ADD', mr, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, j), 0.3)))
    nt.links.new(rough, b.inputs["Roughness"])
    hgt = mix_f(nt, slab, gh_, math_(nt, 'MULTIPLY', j, 1.0))
    bump_from(nt, b, hgt, 0.45, 0.004)
    return m

def marble(name, ground, vein, deep, scale=1.0, seed=0.0, rough=0.32, vein_amt=1.0):
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    col, cloud = marble_color(nt, xyz, ground, vein, deep, scale=scale, seed=seed, vein_amt=vein_amt)
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, cloud, 0.3, 0.7, rough - 0.06, rough + 0.08), b.inputs["Roughness"])
    fine = noise_tex(nt, xyz, 70.0, 3.0, 0.5)
    bump_from(nt, b, fine.outputs["Fac"], 0.06, 0.002)
    return m

def gold(name):
    """Old gold: warm, not mirror-bright, a little tarnish in the hollows."""
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    n = noise_tex(nt, xyz, 9.0, 6.0, 0.6)
    r = ramp(nt, [(0.3, c4((0.42, 0.30, 0.12))), (0.6, c4((0.62, 0.47, 0.22))), (0.8, c4((0.70, 0.55, 0.28)))])
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.8, 0.48, 0.34), b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = 1.0
    return m

def lacquer(name, base=(0.035, 0.10, 0.06), rough=0.42):
    """Green-lacquered wood: grain showing faintly through the lacquer."""
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    mp = node(nt, "ShaderNodeMapping"); nt.links.new(xyz, mp.inputs["Vector"]); mp.inputs["Scale"].default_value = (1.5, 1.5, 0.12)
    wv = node(nt, "ShaderNodeTexWave", wave_type='BANDS', bands_direction='X')
    wv.inputs["Scale"].default_value = 4.0; wv.inputs["Distortion"].default_value = 6.0; wv.inputs["Detail"].default_value = 4.0
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    r = ramp(nt, [(0.0, c4(tuple(v * 0.9 for v in base))), (0.6, c4(base)), (1.0, c4(tuple(v * 1.06 for v in base)))])
    nt.links.new(wv.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(maprange(nt, wv.outputs["Fac"], 0.0, 1.0, rough + 0.08, rough - 0.04), b.inputs["Roughness"])
    bump_from(nt, b, wv.outputs["Fac"], 0.01, 0.0005)
    return m

def cloth(name, base, sheen_tint=(0.5, 0.7, 0.55), rough=0.85, scale=140.0):
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    n = noise_tex(nt, xyz, 4.0, 6.0, 0.6)
    r = ramp(nt, [(0.3, c4(tuple(v * 0.8 for v in base))), (0.7, c4(base))])
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Sheen Weight"].default_value = 0.6; b.inputs["Sheen Roughness"].default_value = 0.35
    b.inputs["Sheen Tint"].default_value = c4(sheen_tint)
    f = noise_tex(nt, xyz, scale, 2.0, 0.5)
    bump_from(nt, b, f.outputs["Fac"], 0.08, 0.001)
    return m

def gem_solid(name, base=(0.03, 0.16, 0.08)):
    """The throne's cabochons: a deeper, clearer green, polished but not mirror-glossy."""
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    n = noise_tex(nt, xyz, 30.0, 4.0, 0.6, 0.5)
    r = ramp(nt, [(0.3, c4(tuple(v * 0.7 for v in base))), (0.65, c4(base)), (0.85, c4(tuple(min(1, v * 1.4) for v in base)))])
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"]); nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.2
    return m

def plain(name, color, rough=0.5, metallic=0.0, emission=None, strength=0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = c4(color); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if emission: b.inputs["Emission Color"].default_value = c4(emission); b.inputs["Emission Strength"].default_value = strength
    return m

# ----------------------------------------------------------------------------- materials
M_FLOOR = emerald_floor("M_EmeraldFloor")
M_WALL = emerald_wall("M_EmeraldWall")
M_WALLNEAR = emerald_wall("M_EmeraldWallNear")        # the same stones, its own texture: the bays round the reader
M_DOME = emerald_dome("M_EmeraldDome")
M_MARBLE = marble("M_GreenMarble", (0.12, 0.19, 0.135), (0.30, 0.37, 0.29), (0.06, 0.10, 0.07), scale=0.8, seed=0.0, rough=0.36)
M_THRONE = marble("M_ThroneMarble", (0.07, 0.17, 0.10), (0.28, 0.40, 0.30), (0.025, 0.065, 0.04), scale=1.1, seed=1.7, rough=0.28)
M_GOLD = gold("M_Gold")
M_GEMS = gem_solid("M_ThroneGems")
M_VELVET = cloth("M_Velvet", (0.025, 0.085, 0.05), rough=0.9)
M_SILK = cloth("M_ScreenSilk", (0.09, 0.19, 0.11), sheen_tint=(0.7, 0.85, 0.7), rough=0.6, scale=220.0)
M_LACQUER = lacquer("M_GreenLacquer")
M_LIGHT = plain("M_GreatLight", (1.0, 0.97, 0.88), rough=0.6, emission=(1.0, 0.92, 0.78), strength=60.0)

# ----------------------------------------------------------------------------- geometry helpers (from build_kansas_farmhouse.py)
def _finish(o, mat, smooth=False):
    o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0), seg=1):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = seg; md.limit_method = 'ANGLE'
    return _finish(o, mat)

def cyl(name, r, h, loc, mat, verts=16, rot=(0, 0, 0), r2=None):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat, smooth=True)

def sphere(name, r, loc, mat, seg=12, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(4, seg // 2), radius=r, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return _finish(o, mat, smooth=True)

def torus(name, Rr, r, loc, mat, rot=(0, 0, 0), seg=16, rseg=6, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=Rr, minor_radius=r, major_segments=seg, minor_segments=rseg, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, mat, smooth=True)

def lathe(name, profile, loc, mat, steps=16, closed=False, smooth=True):
    """profile: list of (radius, z); revolve around Z (radius 0 = a pole). closed=True joins the last profile point
    back to the first (a ring moulding: a closed solid, so normals recalc outward reliably)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for (r, z) in profile:
        if r < 1e-5: rings.append([bm.verts.new((0, 0, z))]); continue
        rings.append([bm.verts.new((r * math.cos(TWO_PI * i / steps), r * math.sin(TWO_PI * i / steps), z)) for i in range(steps)])
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for a, b_ in pairs:
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
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return link(o)

def orient(o, want):
    """Open shells (walls, roof, floor): flip each face so its normal agrees with want(face_centre) (Unity culls backs)."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    flip = [f for f in bm.faces if f.normal.dot(want(f.calc_center_median())) < 0]
    if flip: bmesh.ops.reverse_faces(bm, faces=flip)
    bm.to_mesh(o.data); bm.free()

def grid_surface(name, fn, nu, nv, mat, wrap_u=True, smooth=True):
    """A surface from fn(u in 0..1, v in 0..1) -> (x,y,z), nu x nv quads, optionally closed in u."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    cols = nu if wrap_u else nu + 1
    vs = [[bm.verts.new(fn(i / nu, j / nv)) for i in range(cols)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            i2 = (i + 1) % cols if wrap_u else i + 1
            bm.faces.new((vs[j][i], vs[j][i2], vs[j + 1][i2], vs[j + 1][i]))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return link(o)

def extrude_xz(name, pts, y0, y1, mat, frame=None):
    """A flat polygon in a local x-z plane extruded along local y from y0 to y1 (the throne back, the door head)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    P = frame.p if frame else (lambda x, y, z: (x, y, z))
    a = [bm.verts.new(P(x, y0, z)) for x, z in pts]; b_ = [bm.verts.new(P(x, y1, z)) for x, z in pts]
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
    """Local frame: +Y forward, origin on the floor, turned by yaw about Z."""
    def __init__(self, origin, yaw, z0=0.0):
        self.o = Vector((origin[0], origin[1], z0)); self.yaw = yaw; self.R = Matrix.Rotation(yaw, 3, 'Z')
    def p(self, x, y, z): return tuple(self.o + self.R @ Vector((x, y, z)))
    def box(self, name, size, local, mat, bevel=0.0, seg=1): return box(name, size, self.p(*local), mat, bevel=bevel, rot=(0, 0, self.yaw), seg=seg)
    def cyl(self, name, r, h, local, mat, verts=8, r2=None, rot=(0, 0, 0)):
        return cyl(name, r, h, self.p(*local), mat, verts=verts, rot=(rot[0], rot[1], rot[2] + self.yaw), r2=r2)

def az_frame(az, r=R, z0=0.0):
    """A frame on the wall at azimuth az: +Y points into the room (toward the axis)."""
    return Frame((r * math.cos(az), r * math.sin(az)), az + math.pi / 2, z0)

# ----------------------------------------------------------------------------- the round wall
DOOR_AZ = -math.pi / 2
READER_AZ = math.atan2(READER[1], READER[0])
BAY_W = TWO_PI / NBAY
pil_az = [DOOR_AZ + BAY_W * (k + 0.5) for k in range(NBAY)]      # the door bay is centred between two pilasters

def wall_band(name, a0, a1, z0, z1, mat, nu):
    return grid_surface(name, lambda u, v: (R * math.cos(a0 + (a1 - a0) * u), R * math.sin(a0 + (a1 - a0) * u), z0 + (z1 - z0) * v),
                        nu, 2, mat, wrap_u=False)
# the field of emeralds between plinth and cornice: the five bays round the reader and the door get their own texture
NEAR_HALF = BAY_W * 2.5
near = wall_band("WallNear", DOOR_AZ - NEAR_HALF, DOOR_AZ + NEAR_HALF, PLINTH_H - 0.02, WALL_H - CORNICE_H + 0.02, M_WALLNEAR, 40)
far_ = wall_band("WallFar", DOOR_AZ + NEAR_HALF, DOOR_AZ + TWO_PI - NEAR_HALF, PLINTH_H - 0.02, WALL_H - CORNICE_H + 0.02, M_WALL, 88)
for o in (near, far_): orient(o, lambda c: Vector((-c.x, -c.y, 0)))

# plinth: a green marble base with a torus-like roll and a fillet (closed ring solids, faces point into the room)
lathe("Plinth", [(R + 0.02, 0.0), (R - 0.10, 0.0), (R - 0.10, 0.06), (R - 0.085, 0.09), (R - 0.085, PLINTH_H - 0.10), (R - 0.11, PLINTH_H - 0.07),
                 (R - 0.11, PLINTH_H - 0.04), (R - 0.07, PLINTH_H - 0.01), (R - 0.04, PLINTH_H), (R + 0.02, PLINTH_H)], (0, 0, 0), M_MARBLE, steps=128, closed=True)
lathe("Plinth_Fillet", [(R + 0.01, PLINTH_H - 0.005), (R - 0.045, PLINTH_H - 0.005), (R - 0.05, PLINTH_H + 0.02), (R - 0.03, PLINTH_H + 0.035), (R + 0.01, PLINTH_H + 0.035)],
      (0, 0, 0), M_GOLD, steps=128, closed=True)
# cornice: architrave, a gold bead, a frieze and an overhanging crown moulding where the roof springs
C0 = WALL_H - CORNICE_H
lathe("Cornice", [(R + 0.02, C0 - 0.01), (R - 0.04, C0 - 0.01), (R - 0.05, C0 + 0.06), (R - 0.07, C0 + 0.08), (R - 0.07, C0 + 0.20), (R - 0.10, C0 + 0.23),
                  (R - 0.20, C0 + 0.30), (R - 0.22, C0 + 0.34), (R - 0.20, C0 + 0.355), (R + 0.02, C0 + 0.355)], (0, 0, 0), M_MARBLE, steps=128, closed=True)
lathe("Cornice_Bead", [(R - 0.04, C0 + 0.075), (R - 0.085, C0 + 0.075), (R - 0.095, C0 + 0.10), (R - 0.085, C0 + 0.125), (R - 0.06, C0 + 0.125)],
      (0, 0, 0), M_GOLD, steps=128, closed=True)

# pilasters: base, shaft (fluted look from three strips), capital
for k, az in enumerate(pil_az):
    f = az_frame(az)
    f.box(f"Pil{k}_Base", (PIL_W + 0.10, (PIL_D + 0.07) * 2, PLINTH_H + 0.04), (0, 0, (PLINTH_H + 0.04) / 2), M_MARBLE, bevel=0.015)
    f.box(f"Pil{k}_Shaft", (PIL_W, PIL_D * 2, C0 - PLINTH_H), (0, 0, (C0 + PLINTH_H) / 2), M_MARBLE, bevel=0.012)
    for s in (-1, 0, 1):
        f.box(f"Pil{k}_Flute{s}", (0.04, 0.02, C0 - PLINTH_H - 0.5), (s * 0.11, PIL_D + 0.006, (C0 + PLINTH_H) / 2), M_MARBLE, bevel=0.01)
    f.box(f"Pil{k}_Cap", (PIL_W + 0.12, (PIL_D + 0.08) * 2, 0.16), (0, 0, C0 - 0.07), M_MARBLE, bevel=0.02)
    f.box(f"Pil{k}_CapGold", (PIL_W + 0.06, (PIL_D + 0.04) * 2, 0.03), (0, 0, C0 - 0.16), M_GOLD)

# ----------------------------------------------------------------------------- the high arched roof, its ribs and the great light
NV = 26
dome = grid_surface("Dome", lambda u, v: (dome_pt(T_TOP * v)[0] * math.cos(TWO_PI * u), dome_pt(T_TOP * v)[0] * math.sin(TWO_PI * u), dome_pt(T_TOP * v)[1]),
                    96, NV, M_DOME)
orient(dome, lambda c: Vector((0, 0, WALL_H + 0.3)) - c)

def rib(name, az, w0=0.30, w1=0.12, d0=0.15, d1=0.08, n=24):
    """A marble rib on the roof above a pilaster, tapering to the great light's ring."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    ca, sa = math.cos(az), math.sin(az); side = Vector((-sa, ca, 0))
    rings = []
    for i in range(n + 1):
        t = T_TOP * i / n
        r, z = dome_pt(t)
        p = Vector((r * ca, r * sa, z))
        nrm = Vector((-math.cos(t) / R * ca, -math.cos(t) / R * sa, -math.sin(t) / RISE)).normalized()   # inward normal of the ellipse
        w = w0 + (w1 - w0) * (i / n); d = d0 + (d1 - d0) * (i / n)
        q = [p - side * w / 2 - nrm * 0.02, p + side * w / 2 - nrm * 0.02, p + side * (w / 2 - 0.02) + nrm * d, p - side * (w / 2 - 0.02) + nrm * d]
        rings.append([bm.verts.new(v) for v in q])
    for a, b_ in zip(rings, rings[1:]):
        for k in range(4):
            j = (k + 1) % 4; bm.faces.new((a[k], a[j], b_[j], b_[k]))
    bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_MARBLE)
    return link(o)
for k, az in enumerate(pil_az): rib(f"Rib{k}", az)

# the great light: a frosted lens in a deep gold ring at the crown, a short drum above it
lathe("Light_Ring", [(OCU_R + 0.22, CROWN_Z - 0.06), (OCU_R + 0.05, CROWN_Z - 0.16), (OCU_R - 0.02, CROWN_Z - 0.14), (OCU_R - 0.03, CROWN_Z + 0.02),
                     (OCU_R + 0.10, CROWN_Z + 0.06), (OCU_R + 0.24, CROWN_Z + 0.02)], (0, 0, 0), M_GOLD, steps=64, closed=True)
drum = lathe("Light_Drum", [(OCU_R + 0.01, CROWN_Z), (OCU_R + 0.01, CROWN_Z + 0.34), (0.0, CROWN_Z + 0.36)], (0, 0, 0), M_MARBLE, steps=48)
orient(drum, lambda c: Vector((0, 0, CROWN_Z)) - c)
lathe("GreatLight", [(0.0, CROWN_Z - 0.02), (OCU_R - 0.02, CROWN_Z - 0.04), (OCU_R - 0.02, CROWN_Z + 0.03), (0.0, CROWN_Z + 0.03)], (0, 0, 0), M_LIGHT, steps=48)

# ----------------------------------------------------------------------------- the floor and the round dais
floor = grid_surface("Floor", lambda u, v: ((0.3 + (R + 0.05 - 0.3) * v) * math.cos(TWO_PI * u), (0.3 + (R + 0.05 - 0.3) * v) * math.sin(TWO_PI * u), 0.0), 96, 18, M_FLOOR, smooth=False)
orient(floor, lambda c: Vector((0, 0, 1)))
prev = 0.0
for i, (rr, top) in enumerate(DAIS):
    lathe(f"Dais{i}", [(0.0, prev - 0.01), (rr, prev - 0.01), (rr, top - 0.025), (rr - 0.02, top - 0.004), (rr - 0.04, top), (0.0, top)], (0, 0, 0), M_MARBLE, steps=96)
    prev = top
torus("Dais_GoldEdge", DAIS[-1][0] - 0.06, 0.012, (0, 0, THRONE_Z + 0.002), M_GOLD, seg=96, rseg=4)

# ----------------------------------------------------------------------------- the big throne of green marble, shaped like a chair
TF = Frame((0.0, 0.12), math.pi, THRONE_Z)    # +Y of the frame points south, toward the little door
SW, SD, SH = 1.55, 0.95, 0.74                  # seat width, depth, height (a big chair)
TF.box("Throne_Base", (SW + 0.5, SD + 0.5, 0.16), (0, 0.05, 0.08), M_THRONE, bevel=0.03, seg=2)
TF.box("Throne_Seat", (SW, SD, SH - 0.21), (0, 0.05, 0.16 + (SH - 0.21) / 2), M_THRONE, bevel=0.025, seg=2)
TF.box("Throne_SeatLip", (SW + 0.08, SD + 0.06, 0.10), (0, 0.06, SH - 0.10), M_THRONE, bevel=0.035, seg=2)
TF.box("Throne_Cushion", (SW - 0.34, SD - 0.24, 0.13), (0, 0.10, SH + 0.015), M_VELVET, bevel=0.05, seg=3)
# the back: an arched slab with a raised border and a crest
BW, BT = SW + 0.10, 0.30
back_top = 2.75
pts = [(-BW / 2, 0.15)]
for i in range(17):
    a = math.pi * i / 16
    pts.append((-BW / 2 * math.cos(a), back_top - 0.75 + 0.75 * math.sin(a) ** 0.9))
pts.append((BW / 2, 0.15))
by = -SD / 2 - 0.02
extrude_xz("Throne_Back", pts, by - BT, by, M_THRONE, TF)
inner = [(-BW / 2 + 0.16, SH + 0.10)] + [(-(BW / 2 - 0.16) * math.cos(math.pi * i / 16), back_top - 0.82 + 0.62 * math.sin(math.pi * i / 16) ** 0.9) for i in range(17)] + [(BW / 2 - 0.16, SH + 0.10)]
extrude_xz("Throne_BackPanel", inner, by - 0.01, by + 0.035, M_THRONE, TF)
gold_line = [(x * 1.035, z) for x, z in inner]
extrude_xz("Throne_BackGold", [(-BW / 2 + 0.13, SH + 0.08)] + gold_line[1:-1] + [(BW / 2 - 0.13, SH + 0.08)], by - 0.005, by + 0.022, M_GOLD, TF)
for s in (-1, 1):
    TF.box(f"Throne_Post{s}", (0.20, BT + 0.06, back_top - 0.85), (s * (BW / 2 + 0.02), by - BT / 2, 0.16 + (back_top - 0.85 - 0.16) / 2 + 0.08), M_THRONE, bevel=0.025, seg=2)
    TF.box(f"Throne_PostCap{s}", (0.26, BT + 0.12, 0.08), (s * (BW / 2 + 0.02), by - BT / 2, back_top - 0.72), M_THRONE, bevel=0.02)
    TF.box(f"Throne_PostGold{s}", (0.215, BT + 0.075, 0.025), (s * (BW / 2 + 0.02), by - BT / 2, back_top - 0.79), M_GOLD)
    sphere(f"Throne_PostOrb{s}", 0.10, TF.p(s * (BW / 2 + 0.02), by - BT / 2, back_top - 0.58), M_THRONE, seg=16)
TF.cyl("Throne_Finial", 0.13, 0.12, (0, by - BT / 2, back_top + 0.04), M_THRONE, verts=16)
sphere("Throne_FinialOrb", 0.15, TF.p(0, by - BT / 2, back_top + 0.22), M_THRONE, seg=16)
# arms: blocks on the seat with rolled scroll ends at the front
for s in (-1, 1):
    ax_ = s * (SW / 2 - 0.12)
    TF.box(f"Throne_Arm{s}", (0.30, SD - 0.05, 0.42), (ax_, 0.0, SH + 0.21), M_THRONE, bevel=0.04, seg=2)
    TF.box(f"Throne_ArmPost{s}", (0.26, 0.26, SH + 0.30 - 0.16), (ax_, SD / 2 - 0.08, 0.16 + (SH + 0.30 - 0.16) / 2), M_THRONE, bevel=0.03, seg=2)
    TF.cyl(f"Throne_Scroll{s}", 0.15, 0.32, (ax_, SD / 2 - 0.08, SH + 0.30), M_THRONE, verts=20, rot=(0, math.pi / 2, 0))

# "and sparkled with gems": cabochon emeralds in gold bezels on the back's arch, the arms and the base
def cabochon(name, local, rx, rz, depth, frame=TF, face_y=1.0):
    p = frame.p(*local)
    rot = (math.pi / 2, 0, frame.yaw)
    sphere(name, 1.0, p, M_GEMS, seg=14, scale=(rx, depth, rz), rot=(0, 0, frame.yaw))
    torus(name + "_Bezel", 1.0, 0.2, p, M_GOLD, rot=rot, seg=16, rseg=4, scale=(1, 1, 1))
    bz = bpy.data.objects[name + "_Bezel"]
    # scale the unit bezel to the stone (in its own frame) by rebuilding the mesh coordinates
    Rm = Matrix.Rotation(frame.yaw, 4, 'Z')
    for v in bz.data.vertices:
        lv = Rm.inverted() @ (v.co - Vector(p))
        lv = Vector((lv.x * rx * 1.12, lv.y * 0.35 * depth / 0.2, lv.z * rz * 1.12))
        v.co = Rm @ lv + Vector(p)
GY = by + 0.04
for i in range(7):
    a = math.pi * (0.08 + 0.84 * i / 6)
    x = -(BW / 2 - 0.08) * math.cos(a); z = back_top - 0.75 + 0.75 * math.sin(a) ** 0.9 - 0.09
    cabochon(f"Gem_Back{i}", (x, GY - 0.02, z), 0.045, 0.06, 0.03)
cabochon("Gem_BackCentre", (0, by + 0.045, back_top - 0.58), 0.11, 0.14, 0.045)
for s in (-1, 1):
    cabochon(f"Gem_Arm{s}", (s * (SW / 2 - 0.12), SD / 2 + 0.05, 0.48), 0.055, 0.075, 0.03)
for i, x in enumerate((-0.6, -0.3, 0.0, 0.3, 0.6)):
    cabochon(f"Gem_Base{i}", (x, SD / 2 + 0.31, 0.08), 0.05, 0.04, 0.025)
for i, x in enumerate((-0.45, 0.0, 0.45)):
    cabochon(f"Gem_Lip{i}", (x, SD / 2 + 0.095, SH - 0.10), 0.05, 0.035, 0.025)

# ----------------------------------------------------------------------------- the little door (south wall, behind the reader)
DF = az_frame(DOOR_AZ)
DF.box("Door_JambL", (0.16, 0.42, DOOR_H + 0.08), (-DOOR_W / 2 - 0.08, 0.0, (DOOR_H + 0.08) / 2), M_MARBLE, bevel=0.015)
DF.box("Door_JambR", (0.16, 0.42, DOOR_H + 0.08), (DOOR_W / 2 + 0.08, 0.0, (DOOR_H + 0.08) / 2), M_MARBLE, bevel=0.015)
DF.box("Door_Lintel", (DOOR_W + 0.40, 0.46, 0.20), (0, 0.0, DOOR_H + 0.16), M_MARBLE, bevel=0.02)
DF.box("Door_LintelGold", (DOOR_W + 0.30, 0.03, 0.03), (0, 0.235, DOOR_H + 0.12), M_GOLD)
DF.box("Door_Sill", (DOOR_W + 0.30, 0.44, 0.02), (0, 0.0, 0.01), M_MARBLE)
# the leaf, set back in the reveal: two raised panels and a gold ring handle
DF.box("Door_Leaf", (DOOR_W, 0.06, DOOR_H), (0, 0.11, DOOR_H / 2), M_LACQUER, bevel=0.008)
for i, (z0, z1) in enumerate(((0.18, 0.86), (1.02, 1.86))):
    DF.box(f"Door_Panel{i}", (DOOR_W - 0.24, 0.025, z1 - z0), (0, 0.15, (z0 + z1) / 2), M_LACQUER, bevel=0.012)
    DF.box(f"Door_PanelGem{i}", (0.07, 0.02, 0.09), (0, 0.165, (z0 + z1) / 2), M_GEMS, bevel=0.01)
torus("Door_Ring", 0.055, 0.008, DF.p(DOOR_W / 2 - 0.13, 0.17, 1.0), M_GOLD, rot=(math.pi / 2, 0, DF.yaw), seg=16, rseg=4)
DF.box("Door_RingPlate", (0.06, 0.012, 0.10), (DOOR_W / 2 - 0.13, 0.147, 1.06), M_GOLD, bevel=0.004)
for s, zz in ((-1, 0.3), (-1, 1.7)):
    DF.box(f"Door_Hinge{zz}", (0.18, 0.012, 0.035), (s * (DOOR_W / 2 - 0.10), 0.146, zz), M_GOLD)

# ----------------------------------------------------------------------------- the screen (west wall)
SF = az_frame(SCREEN_AZ, r=R - 0.55)
LW, LH = 0.50, 1.95
x = -2 * LW
ZZ = math.radians(32)
pts_ = [Vector((0, 0))]
for i in range(4):
    a = ZZ if i % 2 == 0 else -ZZ
    pts_.append(pts_[-1] + Vector((math.cos(a), math.sin(a))) * LW)
off = (pts_[0] + pts_[-1]) / 2
pos = [(((pts_[i] + pts_[i + 1]) / 2 - off).x, ((pts_[i] + pts_[i + 1]) / 2 - off).y, ZZ if i % 2 == 0 else -ZZ) for i in range(4)]
for i, (cx, cy, yaw) in enumerate(pos):
    lf = Frame(SF.p(cx, cy, 0)[:2], SF.yaw + yaw)
    lf.box(f"Screen{i}_StileL", (0.04, 0.035, LH), (-LW / 2 + 0.02, 0, LH / 2 + 0.02), M_LACQUER, bevel=0.006)
    lf.box(f"Screen{i}_StileR", (0.04, 0.035, LH), (LW / 2 - 0.02, 0, LH / 2 + 0.02), M_LACQUER, bevel=0.006)
    for zz in (0.12, LH):
        lf.box(f"Screen{i}_Rail{zz}", (LW - 0.06, 0.03, 0.04), (0, 0, zz), M_LACQUER, bevel=0.006)
    lf.box(f"Screen{i}_Silk", (LW - 0.07, 0.006, LH - 0.14), (0, 0, (0.12 + LH) / 2), M_SILK)
    for sx in (-1, 1):
        lf.cyl(f"Screen{i}_Knob{sx}", 0.022, 0.05, (sx * (LW / 2 - 0.02), 0, LH + 0.045), M_GOLD, verts=8)
    for sx in (-1, 1):
        lf.box(f"Screen{i}_Foot{sx}", (0.05, 0.05, 0.03), (sx * (LW / 2 - 0.02), 0, 0.015), M_GOLD)

# ----------------------------------------------------------------------------- lights (names starting "Lamp" are baked in Unity)
ld = bpy.data.lights.new("Lamp.roof", 'POINT'); ld.energy = 6500.0; ld.color = (1.0, 0.88, 0.72); ld.shadow_soft_size = OCU_R * 0.9
L_ROOF = bpy.data.objects.new("Lamp.roof", ld); L_ROOF.location = (0, 0, LIGHT_Z - 0.06); link(L_ROOF)

world = bpy.data.worlds.new("Room"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.01, 0.012, 0.01, 1); bg.inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors
EYE = 1.55
look_dir = Vector((-math.sin(LOOK_YAW), math.cos(LOOK_YAW), 0))
anchor("reader.entrance", (READER[0], READER[1], 0.0))
look = anchor("reader.look", (READER[0] + look_dir.x * 2.0, READER[1] + look_dir.y * 2.0, EYE))
anchor("scene.centre", (0.0, 0.0, 0.0))
anchor("room.throne", (TF.p(0, 0.1, SH)))
anchor("room.door", (0.0, -R + 0.1, 0.0))
anchor("room.screen", SF.p(0, 0, 0))
anchor("roof.light", (0, 0, LIGHT_Z))

# apply every transform so object space == world space (the procedural materials then bake exactly as rendered)
bpy.ops.object.select_all(action='DESELECT')
for o in COLL.objects:
    if o.type == 'MESH': o.select_set(True); bpy.context.view_layer.objects.active = o
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.select_all(action='DESELECT')

# ----------------------------------------------------------------------------- cameras (reader eye 1.6 m; lens 18 ~ the headset's 90 deg)
def camera(name, loc, look_at, lens=18):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 100
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co
E = (READER[0], READER[1], 1.6)
def ahead(yaw_deg, pitch_deg=0.0, d=4.0):
    a = LOOK_YAW + math.radians(yaw_deg); p = math.radians(pitch_deg)
    return (E[0] - math.sin(a) * d * math.cos(p), E[1] + math.cos(a) * d * math.cos(p), E[2] + d * math.sin(p))
cams = [
    camera("Cam_Reader", E, ahead(0, -4)),
    camera("Cam_Left", E, ahead(70, -6)),
    camera("Cam_Right", E, ahead(-70, -6)),
    camera("Cam_Behind", E, ahead(180, -8)),
    camera("Cam_Roof", E, ahead(-15, 62)),
    camera("Cam_Near", E, ahead(150, -42), lens=22),
    camera("Cam_Throne", (1.9, -2.7, 1.55), (0.0, 0.2, 1.3), lens=24),
]
EXPOSURE = {"Cam_Roof": -1.0}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "emerald_throne_room_source.blend"))

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
        scene.view_settings.exposure = EXPOSURE.get(c.name, -0.35)
        scene.render.filepath = os.path.join(OUT, f"render_{c.name[4:].lower()}.png")
        bpy.ops.render.render(write_still=True); print("rendered", scene.render.filepath)

# ----------------------------------------------------------------------------- bake + merge + export for Unity
def tri_count(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

KEEP_NAMES = {}
KEEP_UV = set()

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
    size_for = {"M_EmeraldFloor": min(4096, T_ * 2), "M_EmeraldWall": T_, "M_EmeraldWallNear": T_, "M_EmeraldDome": T_,
                "M_GreenMarble": T_, "M_ThroneMarble": T_, "M_Gold": T_ // 2, "M_GreenLacquer": T_ // 2, "M_ScreenSilk": T_ // 4,
                "M_Velvet": T_ // 4, "M_ThroneGems": T_ // 4, "M_GreatLight": T_ // 16}
    tex_sizes = {}
    for o in merged:
        m = o.data.materials[0]; nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        size = max(64, size_for.get(m.name, T_ // 8))
        tex_sizes[o.name] = size
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        if o.name not in KEEP_UV or not o.data.uv_layers:
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002)
            bpy.ops.object.mode_set(mode='OBJECT')
        passes = [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]
        if m.name == "M_GreatLight": passes = [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False)]
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
    gl = os.path.join(OUT, "emerald_throne_room.gltf")
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False)
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={tex_sizes.get(o.name, 0)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "emerald_throne_room_baked.blend"))

if args.bake or args.export:
    bake_and_export()
print("DONE")
