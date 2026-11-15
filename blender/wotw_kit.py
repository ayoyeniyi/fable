"""
Shared helpers for the three hand-built War of the Worlds rooms (build_ogilvys_observatory.py,
build_horsell_sandpits.py, build_maybury_dining_room.py).

The helpers are the ones the earlier hand-built scripts carry inline (build_emerald_throne_room.py,
build_kansas_farmhouse.py, build_poppy_field.py): node-material shorthands, mesh primitives, anchors, cameras,
Cycles stills, and the bake -> merge-by-material -> glTF export step FableBuild imports. They live in one module here
only so the three rooms share one copy. Additions over those scripts:

  * empties for the living-scene names (docs/LIVING_SCENES.md): fx.*, sound.* (`marker`)
  * sway weights: vertex colour R per vertex on veg.* / cloth.* meshes, exported to glTF as COLOR_0 (`set_weight`)
  * "prebaked" materials: alpha-clipped cards whose RGBA texture is painted in numpy, exported as-is (glTF
    alphaMode MASK via a Math ROUND on the alpha, the exporter's convention) instead of being re-baked
  * the export reports the texture megabytes on disk and an ASTC estimate

Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os, argparse
import numpy as np
from mathutils import Vector, Matrix

TWO_PI = 2 * math.pi
COLL = None
OUT = None
ARGS = None
PREBAKED = set()          # material names exported with their own images (no bake, keep hand UVs)
KEEP_UV = set()           # material names whose hand-made UVs the bake keeps (no smart project)
WEIGHTED = set()          # material names whose merged mesh keeps its vertex colour (sway weight R)


def parse_args(default_out):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=default_out)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--bake", action="store_true")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--res", type=int, default=1400)
    ap.add_argument("--tex", type=int, default=2048)
    ap.add_argument("--quick", action="store_true", help="low samples for iteration")
    ap.add_argument("--cams", default="", help="comma list of camera names to render (default all)")
    ap.add_argument("--prefix", default="render_", help="file name prefix for rendered stills")
    return ap.parse_args(argv)


def begin(coll_name, default_out, seed=1894):
    """Factory-empty scene, Cycles on Metal, AgX; returns (args, scene)."""
    global COLL, OUT, ARGS
    ARGS = parse_args(default_out)
    OUT = os.path.abspath(ARGS.out); os.makedirs(OUT, exist_ok=True)
    random.seed(seed)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24 if ARGS.quick else ARGS.samples
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
    COLL = bpy.data.collections.new(coll_name)
    scene.collection.children.link(COLL)
    return ARGS, scene


def link(obj):
    COLL.objects.link(obj); return obj


# ----------------------------------------------------------------------------- node-material shorthands
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

def white(nt, vec):
    wn = node(nt, "ShaderNodeTexWhiteNoise", noise_dimensions='3D'); nt.links.new(vec, wn.inputs["Vector"])
    return wn

def combine(nt, a, b, c):
    n = node(nt, "ShaderNodeCombineXYZ")
    for i, v in enumerate((a, b, c)):
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]

def tone_ramp(nt, fac, cols):
    r = ramp(nt, [(i / (len(cols) - 1), c4(cl)) for i, cl in enumerate(cols)])
    nt.links.new(fac, r.inputs["Fac"]); return r.outputs["Color"]

def scale_col(c, k): return tuple(min(1.0, v * k) for v in c[:3])


# ----------------------------------------------------------------------------- material recipes
def wood_grain(nt, xyz, along='X', scale=1.0, seed=0.0, ring=5.0, distort=5.0):
    """Long wood grain: distorted wave bands stretched along the board, plus fine pores. Returns (grain 0-1, pores)."""
    mp = node(nt, "ShaderNodeMapping"); nt.links.new(xyz, mp.inputs["Vector"])
    s = {'X': (0.08, 1.0, 1.0), 'Y': (1.0, 0.08, 1.0), 'Z': (1.0, 1.0, 0.08)}[along]
    mp.inputs["Scale"].default_value = tuple(v * scale for v in s)
    mp.inputs["Location"].default_value = (seed * 3.1, seed * 1.7, seed * 2.3)
    wv = node(nt, "ShaderNodeTexWave", wave_type='RINGS', rings_direction='SPHERICAL')
    wv.inputs["Scale"].default_value = ring; wv.inputs["Distortion"].default_value = distort
    wv.inputs["Detail"].default_value = 3.0; wv.inputs["Detail Scale"].default_value = 1.2
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    mp2 = node(nt, "ShaderNodeMapping"); nt.links.new(xyz, mp2.inputs["Vector"])
    s2 = {'X': (6.0, 120.0, 120.0), 'Y': (120.0, 6.0, 120.0), 'Z': (120.0, 120.0, 6.0)}[along]
    mp2.inputs["Scale"].default_value = s2
    pores = noise_tex(nt, mp2.outputs["Vector"], 1.0, 2.0, 0.5)
    return wv.outputs["Fac"], pores.outputs["Fac"]

def wood(name, light, dark, rough=0.45, along='X', scale=1.0, seed=0.0, ring=5.0, grime=None, bumpk=0.04, contrast=1.0):
    """Furniture wood: grain between a light and a dark tone, a varnish sheen, a little wear. contrast < 1 pulls the
    dark grain toward the light tone (quiet grain for mouldings that curve, where rings would show as waves)."""
    dark = tuple(l + (d - l) * contrast for l, d in zip(light, dark))
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    g, pores = wood_grain(nt, xyz, along, scale, seed, ring)
    col = tone_ramp(nt, g, [dark, light, scale_col(light, 1.08), dark])
    col = mix_rgb(nt, 'MULTIPLY', 0.25, col, mix_rgb(nt, 'MIX', pores, (0.8, 0.8, 0.8, 1), (1, 1, 1, 1)))
    blot = noise_tex(nt, xyz, 2.2, 4.0, 0.6)
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, blot.outputs["Fac"], 0.3, 0.7, 0.0, 0.25), col, (0.7, 0.66, 0.6, 1))
    if grime:
        z0, z1, gc = grime
        col = mix_rgb(nt, 'MIX', maprange(nt, Z, z1, z0, 0.0, 0.5), col, c4(gc))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, blot.outputs["Fac"], 0.3, 0.7, rough - 0.08, rough + 0.1), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', g, 0.4), math_(nt, 'MULTIPLY', pores, 0.6)), bumpk, 0.001)
    return m

def planks(name, width, length, tones, gap_col, along='X', rough=0.6, wear=None, seed=0.0, grain_k=0.55, bumpk=0.25, coords=None, gap_w=0.035):
    """Boards: one board every `width` across, staggered butt joints every ~`length` along; each board its own tone
    from `tones`, grain, dark joints, a slight cupping. along = 'X' / 'Y' / 'Z' picks the board direction in object
    space; coords = fn(nt, xyz, X, Y, Z) -> (along, across) sockets in metres for curved boards (a dome's courses).
    `wear` = fn(nt, X, Y, Z) -> 0..1 extra wear (lighter, rougher)."""
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    if coords is not None: A, C = coords(nt, xyz, X, Y, Z)
    else: A, C = {'X': (X, Y), 'Y': (Y, X), 'Z': (Z, X)}[along]
    cv = math_(nt, 'DIVIDE', C, width); row = math_(nt, 'FLOOR', cv); fv = math_(nt, 'FRACT', cv)
    rw = white(nt, combine(nt, row, seed, 1.0))
    off = math_(nt, 'MULTIPLY', rw.outputs["Value"], length)
    cu = math_(nt, 'DIVIDE', math_(nt, 'ADD', A, off), length); seg = math_(nt, 'FLOOR', cu); fu = math_(nt, 'FRACT', cu)
    bid = white(nt, combine(nt, row, seg, seed + 3.0))
    tone = tone_ramp(nt, bid.outputs["Value"], tones)
    gv = combine(nt, math_(nt, 'ADD', A, math_(nt, 'MULTIPLY', bid.outputs["Value"], 13.0)), math_(nt, 'ADD', C, math_(nt, 'MULTIPLY', row, 0.37)), math_(nt, 'MULTIPLY', bid.outputs["Value"], 5.0))
    g, pores = wood_grain(nt, gv, 'X', 1.0, seed, 4.0)
    gm = maprange(nt, g, 0.0, 1.0, 1.0 - grain_k * 0.5, 1.0 + grain_k * 0.3)
    gcol = combine(nt, gm, gm, gm)
    col = mix_rgb(nt, 'MULTIPLY', 1.0, tone, gcol)
    col = mix_rgb(nt, 'MULTIPLY', 0.2, col, mix_rgb(nt, 'MIX', pores, (0.75, 0.75, 0.75, 1), (1, 1, 1, 1)))
    ev = math_(nt, 'MINIMUM', fv, math_(nt, 'SUBTRACT', 1.0, fv))
    eu = math_(nt, 'MULTIPLY', math_(nt, 'MINIMUM', fu, math_(nt, 'SUBTRACT', 1.0, fu)), length / width)
    gap = math_(nt, 'MAXIMUM', maprange(nt, ev, 0.0, gap_w, 1.0, 0.0), maprange(nt, eu, 0.0, gap_w * 0.6, 1.0, 0.0))
    cup = math_(nt, 'MULTIPLY', maprange(nt, ev, 0.0, 0.5, 0.0, 1.0, 'SMOOTHSTEP'), 0.3)
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', gap, 0.9), col, c4(gap_col))
    rgh = math_(nt, 'ADD', rough, math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', bid.outputs["Value"], 0.5), 0.12))
    if wear is not None:
        w = wear(nt, X, Y, Z)
        col = mix_rgb(nt, 'MIX', w, col, mix_rgb(nt, 'SCREEN', 0.18, col, (1, 0.95, 0.85, 1)))
        rgh = math_(nt, 'ADD', rgh, math_(nt, 'MULTIPLY', w, 0.12))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, gap, rgh, 0.9), b.inputs["Roughness"])
    h = math_(nt, 'SUBTRACT', math_(nt, 'ADD', cup, math_(nt, 'MULTIPLY', pores, 0.05)), math_(nt, 'MULTIPLY', gap, 0.6))
    bump_from(nt, b, h, bumpk, 0.002)
    return m

def paint(name, color, rough=0.6, mottle=0.12, grime=None, scale=3.0, bumpk=0.05, drips=False):
    """Painted surface (distemper, oil paint): a soft mottle, optional grime by height (z0 dirty, z1 clean)."""
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    n = noise_tex(nt, xyz, scale, 6.0, 0.6)
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, mottle * 2), c4(color), (0.7, 0.68, 0.64, 1))
    if grime:
        z0, z1, gc = grime
        col = mix_rgb(nt, 'MIX', maprange(nt, Z, z0, z1, 0.6, 0.0), col, c4(gc))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.7, rough - 0.08, rough + 0.08), b.inputs["Roughness"])
    f = noise_tex(nt, xyz, 90.0, 3.0, 0.55)
    bump_from(nt, b, f.outputs["Fac"], bumpk, 0.001)
    return m

def metal(name, color, rough=0.35, tarnish=None, scale=8.0, metallic=1.0, rough_var=0.12):
    """Brass, iron, steel, silver: colour and roughness drift, darker tarnish in patches."""
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    n = noise_tex(nt, xyz, scale, 6.0, 0.62)
    col = c4(color)
    if tarnish:
        col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.45, 0.75, 0.0, 0.8), col, c4(tarnish))
    else:
        col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 0.25), col, (0.75, 0.75, 0.75, 1))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.75, rough - rough_var * 0.5, rough + rough_var), b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = metallic
    f = noise_tex(nt, xyz, 160.0, 2.0, 0.5)
    bump_from(nt, b, f.outputs["Fac"], 0.03, 0.0005)
    return m

def fabric(name, base, rough=0.85, scale=160.0, sheen=0.5, weave=True, var=0.18):
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    n = noise_tex(nt, xyz, 3.0, 6.0, 0.6)
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, var * 2), c4(base), (0.7, 0.7, 0.7, 1))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.4
    if weave:
        wv = node(nt, "ShaderNodeTexWave", wave_type='BANDS', bands_direction='X'); wv.inputs["Scale"].default_value = scale
        wv2 = node(nt, "ShaderNodeTexWave", wave_type='BANDS', bands_direction='Y'); wv2.inputs["Scale"].default_value = scale
        nt.links.new(xyz, wv.inputs["Vector"]); nt.links.new(xyz, wv2.inputs["Vector"])
        bump_from(nt, b, math_(nt, 'MULTIPLY', wv.outputs["Fac"], wv2.outputs["Fac"]), 0.12, 0.0006)
    return m

def glass(name, tint=(0.9, 0.95, 0.92), rough=0.04, ior=1.5):
    """Glass: Blender renders it transmissive; Unity's FableBuild swaps any material named *Glass* for its URP glass."""
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = c4(tint); b.inputs["Roughness"].default_value = rough
    b.inputs["Transmission Weight"].default_value = 1.0; b.inputs["IOR"].default_value = ior
    return m

def plain(name, color, rough=0.5, metallic=0.0, emission=None, strength=0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = c4(color); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if emission: b.inputs["Emission Color"].default_value = c4(emission); b.inputs["Emission Strength"].default_value = strength
    return m


# ----------------------------------------------------------------------------- numpy images
def to_srgb(lin):
    lin = np.clip(lin, 0.0, 1.0)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055).astype(np.float32)

def image_from(name, rgba, srgb_in=False, noncolor=False):
    """rgba: (H, W, 4) float, row 0 = bottom. Linear colour unless srgb_in. Saved as a PNG under OUT/textures and
    packed, so the glTF export writes it as-is."""
    h, w, _ = rgba.shape
    img = bpy.data.images.new(name, w, h, alpha=True)
    px = rgba.astype(np.float32).copy()
    if not srgb_in and not noncolor: px[..., :3] = to_srgb(px[..., :3])
    if noncolor: img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(px.ravel())
    path = os.path.join(OUT, "textures", name + ".png"); os.makedirs(os.path.dirname(path), exist_ok=True)
    img.filepath_raw = path; img.file_format = 'PNG'; img.save(); img.pack()
    return img

def vnoise(x, y, seed=0):
    """Value noise on a lattice, smooth interpolation (numpy, any shape)."""
    xi = np.floor(x).astype(np.int64); yi = np.floor(y).astype(np.int64)
    xf = x - xi; yf = y - yi
    def h(ix, iy):
        v = (ix * 374761393 + iy * 668265263 + seed * 2147483647) & 0xFFFFFFFF
        v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
        return ((v ^ (v >> 16)) & 0xFFFF) / 65535.0
    ux = xf * xf * (3 - 2 * xf); uy = yf * yf * (3 - 2 * yf)
    a = h(xi, yi); b_ = h(xi + 1, yi); c = h(xi, yi + 1); d = h(xi + 1, yi + 1)
    return (a + (b_ - a) * ux) + ((c + (d - c) * ux) - (a + (b_ - a) * ux)) * uy

def fbm(x, y, octaves=5, seed=0, gain=0.5):
    tot = np.zeros(np.broadcast(x, y).shape, np.float32); amp = 0.5; f = 1.0; norm = 0.0
    for o in range(octaves):
        tot += amp * vnoise(x * f + o * 17.31, y * f - o * 9.17, seed + o); norm += amp; amp *= gain; f *= 2.0
    return tot / norm

def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0); return t * t * (3 - 2 * t)

def card_material(name, img, rough=0.75, clip=True, emissive=False, normal_img=None, double=True, blend=False, repeat=False):
    """A material reading its colour (and alpha, clipped at 0.5) from a numpy-painted image; exported as-is.
    blend=True links the alpha straight (glTF alphaMode BLEND: mist)."""
    m, nt, b = new_mat(name)
    uv = node(nt, "ShaderNodeUVMap"); tex = node(nt, "ShaderNodeTexImage"); tex.image = img
    tex.interpolation = 'Linear'; tex.extension = 'REPEAT' if repeat else 'EXTEND'
    nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if clip:
        nt.links.new(math_(nt, 'ROUND', tex.outputs["Alpha"]), b.inputs["Alpha"])
    elif blend:
        nt.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
    if emissive:
        nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 1.0
    if normal_img is not None:
        nm_t = node(nt, "ShaderNodeTexImage"); nm_t.image = normal_img; nt.links.new(uv.outputs["UV"], nm_t.inputs["Vector"])
        nm = node(nt, "ShaderNodeNormalMap"); nt.links.new(nm_t.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    m.use_backface_culling = not double
    PREBAKED.add(name)
    return m


# ----------------------------------------------------------------------------- geometry helpers
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

def cyl(name, r, h, loc, mat, verts=16, rot=(0, 0, 0), r2=None, smooth=True):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o = _finish(o, mat, smooth=smooth)
    if smooth: autosmooth(o)
    return o

def autosmooth(o, angle=40):
    """Smooth the sides, keep caps and rims sharp (sharp-edge marks survive the glTF export as split normals)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(angle): e.smooth = False
    for f in bm.faces: f.smooth = True
    bm.to_mesh(o.data); bm.free()

def sphere(name, r, loc, mat, seg=12, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(4, seg // 2), radius=r, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return _finish(o, mat, smooth=True)

def torus(name, Rr, r, loc, mat, rot=(0, 0, 0), seg=16, rseg=6, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=Rr, minor_radius=r, major_segments=seg, minor_segments=rseg, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return _finish(o, mat, smooth=True)

def lathe(name, profile, loc, mat, steps=16, closed=False, smooth=True, rot=None, sharp=40):
    """profile: list of (radius, z); revolve around Z (radius 0 = a pole). rot: optional Matrix (3x3) applied before loc."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    RM = rot if rot is not None else Matrix.Identity(3)
    def V(p): return RM @ Vector(p)
    for (r, z) in profile:
        if r < 1e-5: rings.append([bm.verts.new(V((0, 0, z)))]); continue
        rings.append([bm.verts.new(V((r * math.cos(TWO_PI * i / steps), r * math.sin(TWO_PI * i / steps), z))) for i in range(steps)])
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
    if smooth:
        for f in bm.faces: f.smooth = True
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(sharp): e.smooth = False
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; me.materials.append(mat)
    return link(o)

def orient(o, want):
    """Open shells: flip each face so its normal agrees with want(face_centre) (Unity culls backs)."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.normal_update()
    flip = [f for f in bm.faces if f.normal.dot(want(f.calc_center_median())) < 0]
    if flip: bmesh.ops.reverse_faces(bm, faces=flip)
    bm.to_mesh(o.data); bm.free()

def grid_surface(name, fn, nu, nv, mat, wrap_u=True, smooth=True):
    """A surface from fn(u in 0..1, v in 0..1) -> (x,y,z), nu x nv quads, optionally closed in u. UV = (u, v)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    cols = nu if wrap_u else nu + 1
    vs = [[bm.verts.new(fn(i / nu, j / nv)) for i in range(cols)] for j in range(nv + 1)]
    uvl = bm.loops.layers.uv.new("UVMap")
    for j in range(nv):
        for i in range(nu):
            i2 = (i + 1) % cols if wrap_u else i + 1
            f = bm.faces.new((vs[j][i], vs[j][i2], vs[j + 1][i2], vs[j + 1][i]))
            for lp, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                lp[uvl].uv = (uu / nu, vv / nv)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return link(o)

def extrude_xz(name, pts, y0, y1, mat, frame=None):
    """A flat polygon in a local x-z plane extruded along local y from y0 to y1."""
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

def tube(name, pts, radii, mat, sides=8, cap=True, smooth=True):
    """A tube along a polyline (branches, cords, pipes): radii per point. Rings are parallel-transported."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    P = [Vector(p) for p in pts]; n = len(P)
    tang = []
    for i in range(n):
        t = (P[min(n - 1, i + 1)] - P[max(0, i - 1)]); tang.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
    ref = Vector((0, 0, 1)) if abs(tang[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = tang[0].cross(ref).normalized()
    rings = []
    for i in range(n):
        if i > 0:
            nrm = (nrm - tang[i] * nrm.dot(tang[i]))
            nrm = nrm.normalized() if nrm.length > 1e-9 else tang[i].orthogonal().normalized()
        bin_ = tang[i].cross(nrm)
        r = radii[i] if hasattr(radii, "__len__") else radii
        rings.append([bm.verts.new(P[i] + (nrm * math.cos(TWO_PI * k / sides) + bin_ * math.sin(TWO_PI * k / sides)) * r) for k in range(sides)])
    for a, b_ in zip(rings, rings[1:]):
        for k in range(sides):
            k2 = (k + 1) % sides; bm.faces.new((a[k], a[k2], b_[k2], b_[k]))
    if cap:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bm.normal_update()
    for f in bm.faces: f.smooth = smooth
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

def sweep_rect(name, pts, ups, w, d, mat, cap=True):
    """A rectangular section swept along pts: `ups[i]` is the direction the section's depth d extends (e.g. inward
    from a shell), w its width across. The section's base face lies on the path (a rib on a dome, a rail)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); n = len(pts)
    P = [Vector(p) for p in pts]; U = [Vector(u).normalized() for u in ups]
    rings = []
    for i in range(n):
        t = (P[min(n - 1, i + 1)] - P[max(0, i - 1)]).normalized()
        u = (U[i] - t * U[i].dot(t)).normalized(); s_ = t.cross(u)
        rings.append([bm.verts.new(P[i] + s_ * (w / 2) * a + u * d * c) for a, c in ((-1, 0), (1, 0), (1, 1), (-1, 1))])
    for a, b_ in zip(rings, rings[1:]):
        for k in range(4):
            k2 = (k + 1) % 4; bm.faces.new((a[k], a[k2], b_[k2], b_[k]))
    if cap: bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

def mesh_from(name, verts, faces, mat, smooth=False, uvs=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    if uvs is not None:
        uvl = me.uv_layers.new(name="UVMap")
        for li, lp in enumerate(me.loops): uvl.data[li].uv = uvs[lp.vertex_index]
    for p in me.polygons: p.use_smooth = smooth
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    return link(o)

def set_weight(o, fn):
    """Sway weight for veg.* / cloth.*: vertex colour R = fn(world-space vertex co) in 0..1 (G, B = R, A = 1).
    Exported to glTF as COLOR_0 (see docs/LIVING_SCENES.md)."""
    me = o.data
    at = me.color_attributes.get("Col") or me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
    mw = o.matrix_world
    vals = []
    for v in me.vertices:
        w = max(0.0, min(1.0, fn(mw @ v.co))); vals += [w, w, w, 1.0]
    at.data.foreach_set("color", vals)
    me.color_attributes.active_color = at
    try: me.color_attributes.render_color_index = me.color_attributes.find("Col")
    except Exception: pass
    return o

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

def marker(name, loc, size=0.1, rot=(0, 0, 0)):
    """An empty for the living-scene names (fx.fire.*, fx.candle.*, fx.lantern.*, sound.*): its display size carries
    the fire's radius for fx.fire.*."""
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'SPHERE'; e.empty_display_size = size
    e.location = loc; e.rotation_euler = rot; link(e)
    return e

class Frame:
    """Local frame: +Y forward, origin on the floor, turned by yaw about Z."""
    def __init__(self, origin, yaw, z0=0.0):
        self.o = Vector((origin[0], origin[1], z0 if len(origin) < 3 else origin[2])); self.yaw = yaw; self.R = Matrix.Rotation(yaw, 3, 'Z')
    def p(self, x, y, z): return tuple(self.o + self.R @ Vector((x, y, z)))
    def box(self, name, size, local, mat, bevel=0.0, seg=1, rot=(0, 0, 0)):
        return box(name, size, self.p(*local), mat, bevel=bevel, rot=(rot[0], rot[1], rot[2] + self.yaw), seg=seg)
    def cyl(self, name, r, h, local, mat, verts=8, r2=None, rot=(0, 0, 0)):
        if rot == (0, 0, 0):
            return cyl(name, r, h, self.p(*local), mat, verts=verts, rot=(0, 0, self.yaw), r2=r2)
        mrot = (Matrix.Rotation(self.yaw, 3, 'Z') @ _euler_m(rot)).to_euler()
        return cyl(name, r, h, self.p(*local), mat, verts=verts, rot=tuple(mrot), r2=r2)
    def lathe(self, name, profile, local, mat, steps=16, smooth=True, closed=False, sharp=40):
        return lathe(name, profile, self.p(*local), mat, steps=steps, smooth=smooth, closed=closed, rot=self.R, sharp=sharp)

def _euler_m(rot):
    from mathutils import Euler
    return Euler(rot, 'XYZ').to_matrix()

def apply_all_transforms():
    bpy.ops.object.select_all(action='DESELECT')
    for o in COLL.objects:
        if o.type == 'MESH': o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.select_all(action='DESELECT')


# ----------------------------------------------------------------------------- cameras + renders
def camera(name, loc, look_at, lens=18, clip_end=200):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = clip_end; cd.clip_start = 0.03
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co

def budget_report():
    dg = bpy.context.evaluated_depsgraph_get(); cat = {}
    for o in [o for o in COLL.objects if o.type == 'MESH']:
        e = o.evaluated_get(dg); me = e.to_mesh(); t = sum(len(p.vertices) - 2 for p in me.polygons); e.to_mesh_clear()
        k = o.data.materials[0].name if o.data.materials else "?"
        cat[k] = cat.get(k, 0) + t
    print(f"PRE-MERGE materials={len(cat)} tris={sum(cat.values())}")
    for k, v in sorted(cat.items(), key=lambda kv: -kv[1]): print(f"  BUDGET {k:24s} {v}")
    return sum(cat.values())

def render_stills(scene, cams, exposure=None, default_exp=0.0):
    exposure = exposure or {}
    scene.render.resolution_x = ARGS.res; scene.render.resolution_y = int(ARGS.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    want = set(c.strip().lower() for c in ARGS.cams.split(",") if c.strip())
    for c in cams:
        if want and c.name[4:].lower() not in want: continue
        scene.camera = c
        scene.view_settings.exposure = exposure.get(c.name, default_exp)
        scene.render.filepath = os.path.join(OUT, f"{ARGS.prefix}{c.name[4:].lower()}.png")
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:
            # the GPU is shared with other jobs on this Mac: on a Metal out-of-memory error, finish on the CPU
            print("GPU render failed, retrying on the CPU:", str(e)[:120]); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)


# ----------------------------------------------------------------------------- bake + merge + export for Unity
def tri_count(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

def bake_and_export(scene, gltf_name, size_for, keep_names=None, cams=(), blend_name=None):
    """Join meshes by material (named MESH_<material> unless keep_names maps the material to a living-scene name such
    as veg.crown.pines), bake each procedural material to BaseColor / Roughness / Normal images (lighting stays out:
    Unity bakes it), keep prebaked card materials as they are, then export .gltf + .bin + textures/ (JPEG; PNG for
    cards with alpha). Sway weights (vertex colour) survive only on the WEIGHTED materials' meshes."""
    keep_names = keep_names or {}
    T_ = ARGS.tex
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')
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
        o = bpy.context.view_layer.objects.active; o.name = keep_names.get(mname, "MESH_" + mname[2:])
        if mname not in WEIGHTED:
            for an in [a.name for a in o.data.color_attributes]: o.data.color_attributes.remove(o.data.color_attributes[an])
        else:
            ca = o.data.color_attributes
            for an in [a.name for a in ca if a.name != "Col"]: ca.remove(ca[an])
            if ca.get("Col"): ca.active_color = ca["Col"]
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    # 1-sample bakes on the CPU (the croquet ground found Metal kernel compiles crashing mid-bake in 5.2.3)
    scene.cycles.samples = 1; scene.cycles.device = 'CPU'
    scene.render.bake.margin = 6
    tex_sizes = {}
    for o in merged:
        m = o.data.materials[0]; nt = m.node_tree
        if m.name in PREBAKED:
            tex_sizes[o.name] = max((n.image.size[0] for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image), default=0); continue
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        sizes = size_for.get(m.name, (T_ // 4,))
        if isinstance(sizes, int): sizes = (sizes,)
        sizes = tuple(max(32, s) for s in sizes)
        tex_sizes[o.name] = sizes[0]
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        if m.name not in KEEP_UV or not o.data.uv_layers:
            for uvn in [u.name for u in o.data.uv_layers]: o.data.uv_layers.remove(o.data.uv_layers[uvn])
            o.data.uv_layers.new(name="UVMap")
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
            bpy.ops.object.mode_set(mode='OBJECT')
        # the diffuse colour pass of a metal or glass is black: bake their albedo as if dielectric and opaque
        metallic = bsdf.inputs["Metallic"].default_value
        transm = bsdf.inputs["Transmission Weight"].default_value
        for sock in ("Metallic", "Transmission Weight"):
            for l in list(bsdf.inputs[sock].links): nt.links.remove(l)
            bsdf.inputs[sock].default_value = 0.0
        passes = [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False)]
        if len(sizes) > 1: passes.append(("Roughness", 'ROUGHNESS', {}, True))
        if len(sizes) > 2: passes.append(("Normal", 'NORMAL', {}, True))
        baked = {}
        for (pass_name, btype, extra, noncolor), size in zip(passes, sizes):
            img = bpy.data.images.new(f"T_{m.name[2:]}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            for n in nt.nodes: n.select = False
            tex.select = True; nt.nodes.active = tex
            bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            img.filepath_raw = os.path.join(OUT, "textures", img.name + ".jpg"); os.makedirs(os.path.dirname(img.filepath_raw), exist_ok=True)
            img.file_format = 'JPEG'
            try: img.save(quality=90)
            except TypeError: img.save()
            img.pack()
            baked[pass_name] = tex
            print("baked", img.name, size)
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
        nb.inputs["Transmission Weight"].default_value = transm
        if emis > 0:
            nb.inputs["Emission Strength"].default_value = min(emis, 1.0)
            if elinked: nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"])
            else: nb.inputs["Emission Color"].default_value = ecol
    for c in cams: bpy.data.objects.remove(c)
    gl = os.path.join(OUT, gltf_name)
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='AUTO', export_lights=True, export_cameras=False,
                              export_vertex_color='ACTIVE', export_all_vertex_colors=False)
    # JPEG for the opaque baked maps (as the other rooms), PNG kept for alpha cards: convert after export
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    tdir = os.path.join(OUT, "textures")
    used = set()
    import json
    with open(gl) as f: gj = json.load(f)
    for im in gj.get("images", []): used.add(os.path.basename(im["uri"]))
    tex_bytes = sum(os.path.getsize(os.path.join(tdir, u)) for u in used if os.path.exists(os.path.join(tdir, u)))
    gpu = 0
    for im in bpy.data.images:
        if im.size[0] and ((im.name + ".png") in used or (im.name + ".jpg") in used):
            gpu += im.size[0] * im.size[1] * (1.0 if im.colorspace_settings.name == 'Non-Color' and 'Normal' in im.name else 0.444) * 1.33
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris} textures_on_disk={tex_bytes / 1e6:.1f}MB astc_est={gpu / 1e6:.1f}MB")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\ntextures_on_disk_mb={tex_bytes / 1e6:.2f}\nastc_estimate_mb={gpu / 1e6:.2f}\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={tex_sizes.get(o.name, 0)} colour={'yes' if o.data.color_attributes else 'no'}\n")
    if blend_name: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, blend_name))
    return merged


# ----------------------------------------------------------------------------- numpy painting for cards (foliage atlases)
def paint_stroke(img, p0, p1, w0, w1, col, alpha=1.0):
    """Anti-aliased tapered stroke from p0 to p1 (pixel coords x, y; y up), widths w0 -> w1 px, onto an (H, W, 4)
    straight-alpha float image (painted over: later strokes cover earlier ones)."""
    H, W = img.shape[:2]
    x0, y0 = p0; x1, y1 = p1
    pad = max(w0, w1) + 2
    xa, xb = int(max(0, math.floor(min(x0, x1) - pad))), int(min(W, math.ceil(max(x0, x1) + pad)))
    ya, yb = int(max(0, math.floor(min(y0, y1) - pad))), int(min(H, math.ceil(max(y0, y1) + pad)))
    if xa >= xb or ya >= yb: return
    yy, xx = np.mgrid[ya:yb, xa:xb].astype(np.float32)
    dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy + 1e-9
    t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / L2, 0, 1)
    d = np.hypot(xx - (x0 + t * dx), yy - (y0 + t * dy))
    hw = (w0 + (w1 - w0) * t) * 0.5
    a = np.clip(hw + 0.5 - d, 0, 1) * alpha
    if not np.any(a > 0): return
    sub = img[ya:yb, xa:xb]
    c = np.asarray(col, np.float32)
    if c.ndim == 1: c = c[None, None, :3]
    sub[..., :3] = sub[..., :3] * (1 - a[..., None]) + c * a[..., None]
    sub[..., 3] = np.maximum(sub[..., 3], a)

def paint_dot(img, p, r, col, alpha=1.0):
    H, W = img.shape[:2]
    x0, y0 = p
    xa, xb = int(max(0, math.floor(x0 - r - 2))), int(min(W, math.ceil(x0 + r + 2)))
    ya, yb = int(max(0, math.floor(y0 - r - 2))), int(min(H, math.ceil(y0 + r + 2)))
    if xa >= xb or ya >= yb: return
    yy, xx = np.mgrid[ya:yb, xa:xb].astype(np.float32)
    a = np.clip(r + 0.5 - np.hypot(xx - x0, yy - y0), 0, 1) * alpha
    sub = img[ya:yb, xa:xb]
    sub[..., :3] = sub[..., :3] * (1 - a[..., None]) + np.asarray(col, np.float32)[None, None, :3] * a[..., None]
    sub[..., 3] = np.maximum(sub[..., 3], a)

def bleed_alpha(img, iters=8):
    """Spread colour into transparent texels (so mipmaps and filtering don't pull a dark or white fringe)."""
    rgb = img[..., :3].copy(); a = (img[..., 3] > 0.02).astype(np.float32)
    for _ in range(iters):
        acc = np.zeros_like(rgb); cnt = np.zeros(a.shape, np.float32)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(rgb * a[..., None], dx, 1), dy, 0); cnt += np.roll(np.roll(a, dx, 1), dy, 0)
        fill = (a == 0) & (cnt > 0)
        rgb[fill] = acc[fill] / cnt[fill][:, None]; a = np.maximum(a, fill.astype(np.float32))
    solid = img[..., 3] > 0.5
    if np.any(solid): rgb[a == 0] = rgb[solid].mean(0)       # the rest: the mean colour, so far mips don't darken the edges
    img[..., :3] = rgb
    return img

def card_quad(bm, uvl, centre, right, up, w, h, uv_rect, normal_fn=None, weight_fn=None, base_at_bottom=True):
    """Add a textured quad to bmesh: centre (bottom-centre if base_at_bottom), right/up unit vectors, size w x h,
    uv_rect = (u0, v0, u1, v1). Returns the face."""
    c = Vector(centre); r = Vector(right) * (w / 2); u = Vector(up) * h
    if base_at_bottom: corners = [c - r, c + r, c + r + u, c - r + u]
    else: corners = [c - r - u * 0.5, c + r - u * 0.5, c + r + u * 0.5, c - r + u * 0.5]
    vs = [bm.verts.new(p) for p in corners]
    f = bm.faces.new(vs)
    u0, v0, u1, v1 = uv_rect
    for lp, uv in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))): lp[uvl].uv = uv
    return f


class CardMesh:
    """Builds a mesh of textured cards with per-vertex custom normals (soft, volumetric shading for foliage) and a
    per-vertex sway weight (vertex colour R, docs/LIVING_SCENES.md)."""
    def __init__(self, name):
        self.name = name; self.bm = bmesh.new(); self.uvl = self.bm.loops.layers.uv.new("UVMap")
        self.normals = []; self.weights = []
    def quad(self, corners, uvs, normals, weights):
        vs = []
        for p, n, w in zip(corners, normals, weights):
            vs.append(self.bm.verts.new(p)); self.normals.append(Vector(n).normalized()); self.weights.append(w)
        f = self.bm.faces.new(vs)
        for lp, uv in zip(f.loops, uvs): lp[self.uvl].uv = uv
        f.smooth = True
        return f
    def finish(self, mat, weighted=True):
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free()
        o = bpy.data.objects.new(self.name, me); me.materials.append(mat); link(o)
        for p in me.polygons: p.use_smooth = True
        try: me.normals_split_custom_set_from_vertices([tuple(n) for n in self.normals])
        except Exception as e: print("custom normals failed", e)
        if weighted:
            at = me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
            vals = []
            for w in self.weights: vals += [w, w, w, 1.0]
            at.data.foreach_set("color", vals); me.color_attributes.active_color = at
            WEIGHTED.add(mat.name)
        KEEP_UV.add(mat.name)
        return o
