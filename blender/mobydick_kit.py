"""
Fable: shared helpers for the three hand-built Moby-Dick rooms (build_spouter_inn.py, build_pequod_deck.py,
build_battery_waterfront.py). The material and geometry helpers are those of build_odysseus_ship.py /
build_calypsos_cave.py, generalised; the bake + merge + export follows the same pipeline (bake each material's
base colour, roughness and normal to textures, merge static meshes by material, export .gltf + .bin + textures/)
with the additions docs/LIVING_SCENES.md asks for:

  water.ocean.*   kept as its own mesh (never merged, never re-unwrapped): its UVs are world metres / 10 (U = x/10,
                  V = y/10 in Blender's frame) and its vertex colour (COLOR_0) carries foam in G (1 at the hull or the
                  wharf, 0 in open water); R = 0, B = 1, A = 1. Its material is a plain dark water colour, no
                  textures: the Unity side gives it the animated water material.
  veg.<kind>.* / cloth.<kind>.*
                  merged only with meshes of the same object property "merge" (so one swaying mesh per kind), keep
                  that name, baked like any other material, and carry COLOR_0 = (weight, 1, 1, 1): R is how much the
                  vertex moves (0 fixed, 1 free); G and B are 1 so that a shader that multiplies vertex colour into
                  the base colour does not darken them.
  fx.* / sound.*  empties, exported as glTF nodes. The fire's radius (LIVING_SCENES: "the empty's display size")
                  is also written as the custom property "radius", exported in the node's extras.
  far.* / SkyDome backdrop meshes, unlit in Unity (FlowController.IsBackdrop).

Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, Euler, noise

# ----------------------------------------------------------------------------- args and scene
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
    ap.add_argument("--nosave", action="store_true", help="do not save the source .blend")
    return ap.parse_args(argv)

S = {}          # shared state: scene, collection, out dir

def reset_scene(coll_name, args):
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
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0.0
    coll = bpy.data.collections.new(coll_name)
    scene.collection.children.link(coll)
    S.update(scene=scene, coll=coll, args=args, out=os.path.abspath(args.out))
    os.makedirs(S["out"], exist_ok=True)
    return scene, coll

def link(obj):
    S["coll"].objects.link(obj); return obj

def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def lerp(a, b, t): return a + (b - a) * t

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

def c4(c): return (c[0], c[1], c[2], 1)
def scaled(c, k): return tuple(min(1.0, x * k) for x in c)

def coords(nt, world=False, loc=(-1400, 0)):
    if world:
        g = node(nt, "ShaderNodeNewGeometry", loc); mp = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
        nt.links.new(g.outputs["Position"], mp.inputs["Vector"]); return mp
    tc = node(nt, "ShaderNodeTexCoord", loc); mp = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); return mp

def frame_coords(nt, yaw=0.0, origin=(0, 0, 0), stretch=(1, 1, 1), loc=(-1600, 0)):
    """World position -> a local frame (rotated by -yaw about Z around origin), then stretched. Grain keeps running
    along the timbers before and after the merge (which applies every transform)."""
    g = node(nt, "ShaderNodeNewGeometry", loc)
    m0 = node(nt, "ShaderNodeMapping", (loc[0] + 150, loc[1])); m0.inputs["Location"].default_value = tuple(-x for x in origin)
    nt.links.new(g.outputs["Position"], m0.inputs["Vector"])
    m1 = node(nt, "ShaderNodeMapping", (loc[0] + 300, loc[1])); m1.inputs["Rotation"].default_value = (0.0, 0.0, -yaw)
    nt.links.new(m0.outputs["Vector"], m1.inputs["Vector"])
    m2 = node(nt, "ShaderNodeMapping", (loc[0] + 450, loc[1])); m2.inputs["Scale"].default_value = stretch
    nt.links.new(m1.outputs["Vector"], m2.inputs["Vector"])
    return m2, m1

def attr(nt, name, loc=(-1000, 600)):
    a = node(nt, "ShaderNodeAttribute", loc); a.attribute_name = name
    return a.outputs["Fac"]

def bump_from(nt, b, height_socket, strength, distance):
    bump = node(nt, "ShaderNodeBump", (50, -300)); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return bump

def mix_rgb(nt, a, b_, fac, blend='MIX', loc=(0, 0)):
    mx = node(nt, "ShaderNodeMix", loc, data_type='RGBA', blend_type=blend)
    if isinstance(fac, (int, float)): mx.inputs["Factor"].default_value = fac
    else: nt.links.new(fac, mx.inputs["Factor"])
    for sock, v in ((mx.inputs[6], a), (mx.inputs[7], b_)):
        if isinstance(v, tuple): sock.default_value = v
        else: nt.links.new(v, sock)
    return mx.outputs[2]

def mix_f(nt, a, b_, fac, loc=(0, 0)):
    mx = node(nt, "ShaderNodeMix", loc, data_type='FLOAT')
    for sock, v in ((mx.inputs[0], fac), (mx.inputs[2], a), (mx.inputs[3], b_)):
        if isinstance(v, (int, float)): sock.default_value = v
        else: nt.links.new(v, sock)
    return mx.outputs[0]

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

def sep_xyz(nt, vec, loc=(-1100, 0)):
    s = node(nt, "ShaderNodeSeparateXYZ", loc); nt.links.new(vec, s.inputs["Vector"]); return s

def ao_mult(nt, col, dist, dark, loc=(-450, -800)):
    a = node(nt, "ShaderNodeAmbientOcclusion", loc); a.inputs["Distance"].default_value = dist; a.samples = 16
    aor = ramp(nt, [(0.0, c4(dark)), (1.0, (1, 1, 1, 1))], (loc[0] + 200, loc[1])); nt.links.new(a.outputs["AO"], aor.inputs["Fac"])
    return mix_rgb(nt, col, aor.outputs["Color"], 1.0, 'MULTIPLY', (loc[0] + 400, loc[1]))

def world_z(nt, loc=(-1400, -900)):
    g = node(nt, "ShaderNodeNewGeometry", loc); return sep_xyz(nt, g.outputs["Position"], (loc[0] + 200, loc[1])).outputs["Z"]

def noisy(name, colors, scale=8.0, rough=0.8, bump=0.2, bump_dist=0.003, detail=6.0, stretch=(1, 1, 1), sheen=0.0, sss=0.0,
          metallic=0.0, warp=0.0, world=False, ao=None):
    m, nt, b = new_mat(name)
    mp = coords(nt, world=world); mp.inputs["Scale"].default_value = stretch
    n = noise_tex(nt, mp.outputs["Vector"], scale, detail, 0.6, warp)
    stops = [(i / max(1, len(colors) - 1) * 0.6 + 0.2, c4(c)) for i, c in enumerate(colors)]
    r = ramp(nt, stops, (-700, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    col = r.outputs["Color"]
    if ao: col = ao_mult(nt, col, ao[0], ao[1])
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if sheen: b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.4
    if sss: b.inputs["Subsurface Weight"].default_value = sss; b.inputs["Subsurface Radius"].default_value = (0.4, 0.3, 0.1)
    if bump:
        fine = noise_tex(nt, mp.outputs["Vector"], scale * 6, 4, loc=(-1000, -350))
        bump_from(nt, b, fine.outputs["Fac"], bump, bump_dist)
    return m

def timber_mat(name, base, dark, light, along='X', rough=(0.62, 0.85), grime=0.35, scale=1.0, salt=0.0, yaw=0.0, origin=(0, 0, 0),
               seams=None, polish=0.0):
    """Weathered timber: grain along the timber (in a frame turned by yaw), per-piece tone (attribute 'rnd'), grime in
    the hollows (AO), blotches of wear, optional salt; seams=(axis, pitch) draws dark plank joints across that axis."""
    m, nt, b = new_mat(name)
    stretch = {'X': (1.2, 16, 16), 'Y': (16, 1.2, 16), 'Z': (16, 16, 1.2)}[along]
    mp, m1 = frame_coords(nt, yaw, origin, tuple(s * scale for s in stretch))
    wave = node(nt, "ShaderNodeTexWave", (-1000, 250), wave_type='BANDS', bands_direction={'X': 'Y', 'Y': 'X', 'Z': 'X'}[along])
    wave.inputs["Scale"].default_value = 1.6; wave.inputs["Distortion"].default_value = 9.0
    wave.inputs["Detail"].default_value = 5.0; wave.inputs["Detail Scale"].default_value = 1.4
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    fine = noise_tex(nt, mp.outputs["Vector"], 9.0, 8.0, 0.65, loc=(-1000, 0))
    mx = mix_f(nt, wave.outputs["Fac"], fine.outputs["Fac"], 0.6, (-800, 150))
    mid = tuple((x + y) / 2 for x, y in zip(base, light))
    r = ramp(nt, [(0.1, c4(dark)), (0.35, c4(base)), (0.55, c4(mid)), (0.8, c4(light))], (-600, 150))
    nt.links.new(mx, r.inputs["Fac"])
    rnd = attr(nt, "rnd", (-1000, 550))
    tone = ramp(nt, [(0.0, (0.80, 0.80, 0.82, 1)), (0.5, (1.0, 0.97, 0.93, 1)), (1.0, (1.14, 1.08, 1.0, 1))], (-800, 550))
    nt.links.new(rnd, tone.inputs["Fac"])
    col = mix_rgb(nt, r.outputs["Color"], tone.outputs["Color"], 1.0, 'MULTIPLY', (-400, 300))
    big = noise_tex(nt, m1.outputs["Vector"], 1.3, 4, 0.5, loc=(-1000, -250))
    bl = ramp(nt, [(0.35, (0.80, 0.76, 0.72, 1)), (0.5, (1, 1, 1, 1)), (0.68, (1.08, 1.08, 1.06, 1))], (-800, -250))
    nt.links.new(big.outputs["Fac"], bl.inputs["Fac"])
    col = mix_rgb(nt, col, bl.outputs["Color"], 1.0, 'MULTIPLY', (-250, 300))
    hgt = None
    if seams:
        ax, pitch = seams
        sx = sep_xyz(nt, m1.outputs["Vector"], (-1300, -1300))
        jit = noise_tex(nt, m1.outputs["Vector"], 0.7, 2, 0.5, loc=(-1300, -1450))
        cc = math_n(nt, 'ADD', math_n(nt, 'DIVIDE', sx.outputs[ax], pitch, (-1150, -1300)), math_n(nt, 'MULTIPLY', jit.outputs["Fac"], 0.0, (-1150, -1450)), (-1000, -1300))
        fr = math_n(nt, 'FRACT', cc, None, (-900, -1300))
        sm = ramp(nt, [(0.0, (0.35, 0.33, 0.30, 1)), (0.02, (1, 1, 1, 1)), (0.98, (1, 1, 1, 1)), (1.0, (0.35, 0.33, 0.30, 1))], (-750, -1300))
        nt.links.new(fr, sm.inputs["Fac"])
        col = mix_rgb(nt, col, sm.outputs["Color"], 1.0, 'MULTIPLY', (-200, 200))
        hgt = sm.outputs["Color"]
    if salt:
        sn = noise_tex(nt, m1.outputs["Vector"], 7.0, 6, 0.6, loc=(-1000, -450))
        sr = ramp(nt, [(0.62, (0, 0, 0, 1)), (0.75, (1, 1, 1, 1))], (-800, -450)); nt.links.new(sn.outputs["Fac"], sr.inputs["Fac"])
        sf = math_n(nt, 'MULTIPLY', sr.outputs["Color"], salt, (-600, -450))
        col = mix_rgb(nt, col, (0.55, 0.54, 0.50, 1), sf, 'MIX', (-150, 300))
    col = ao_mult(nt, col, 0.35, scaled(dark, 1.0 - grime * 0.4) if grime else (1, 1, 1))
    nt.links.new(col, b.inputs["Base Color"])
    rr = map_range(nt, mx, 0.2, 0.8, rough[1], rough[0], (-150, -200))
    if polish: rr = math_n(nt, 'MULTIPLY', rr, 1.0 - polish, (-100, -250))
    nt.links.new(rr, b.inputs["Roughness"])
    h = math_n(nt, 'MULTIPLY_ADD', wave.outputs["Fac"], 0.6, (-300, -400)); nt.links.new(fine.outputs["Fac"], h.node.inputs[2])
    if hgt is not None: h = math_n(nt, 'ADD', h, math_n(nt, 'MULTIPLY', hgt, 0.8, (-300, -550)), (-200, -450))
    bump_from(nt, b, h, 0.35, 0.002)
    return m

def iron_mat(name, rust=0.3, base=(0.035, 0.033, 0.032), rough=(0.55, 0.85)):
    """Cast or wrought iron, blackened, with rust in patches."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    n = noise_tex(nt, mp.outputs["Vector"], 6.0, 8, 0.65, loc=(-1000, 200))
    rn = noise_tex(nt, mp.outputs["Vector"], 2.5, 6, 0.7, 0.5, loc=(-1000, -100))
    r = ramp(nt, [(0.3, c4(scaled(base, 0.8))), (0.6, c4(base)), (0.8, c4(scaled(base, 1.5)))], (-700, 200)); nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    rr = ramp(nt, [(0.55 - rust * 0.3, (0, 0, 0, 1)), (0.7 - rust * 0.3, (1, 1, 1, 1))], (-700, -100)); nt.links.new(rn.outputs["Fac"], rr.inputs["Fac"])
    rc = ramp(nt, [(0.3, (0.12, 0.05, 0.02, 1)), (0.7, (0.24, 0.10, 0.04, 1))], (-700, -300)); nt.links.new(n.outputs["Fac"], rc.inputs["Fac"])
    col = mix_rgb(nt, r.outputs["Color"], rc.outputs["Color"], rr.outputs["Color"], 'MIX', (-400, 100))
    col = ao_mult(nt, col, 0.2, (0.5, 0.5, 0.5))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = 0.0
    nt.links.new(mix_f(nt, rough[0], rough[1], rr.outputs["Color"], (-300, -200)), b.inputs["Roughness"])
    bump_from(nt, b, mix_f(nt, n.outputs["Fac"], rn.outputs["Fac"], 0.5, (-300, -400)), 0.25, 0.003)
    return m

def glass_mat(name, tint=(0.75, 0.82, 0.78), rough=0.05, dirt=0.0):
    """Glass (FableBuild turns any material whose name contains 'Glass' into transparent URP glass)."""
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = c4(tint); b.inputs["Roughness"].default_value = rough
    b.inputs["Transmission Weight"].default_value = 1.0; b.inputs["IOR"].default_value = 1.5
    if dirt:
        mp = coords(nt, world=True)
        n = noise_tex(nt, mp.outputs["Vector"], 9.0, 5, 0.6, loc=(-800, -200))
        nt.links.new(map_range(nt, n.outputs["Fac"], 0.4, 0.7, rough, rough + dirt, (-400, -200)), b.inputs["Roughness"])
    return m

def emit_mat(name, color, strength):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = c4(color); b.inputs["Emission Color"].default_value = c4(color)
    b.inputs["Emission Strength"].default_value = strength; b.inputs["Roughness"].default_value = 0.8
    return m

# ----------------------------------------------------------------------------- geometry helpers
def set_attr(o, name, value):
    me = o.data
    if name not in me.attributes: me.attributes.new(name, 'FLOAT', 'POINT')
    a = me.attributes[name]
    vals = value if isinstance(value, list) else [value] * len(me.vertices)
    a.data.foreach_set("value", vals)

def set_weight_colour(o, weight_fn=None, foam_fn=None, kind="sway"):
    """COLOR_0 for living meshes. kind 'sway': (w, 1, 1, 1) with w = weight_fn(world co); kind 'water': (0, foam, 1, 1)."""
    me = o.data; mw = o.matrix_world
    if "Col" in me.color_attributes: me.color_attributes.remove(me.color_attributes["Col"])
    ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
    vals = []
    for v in me.vertices:
        p = mw @ v.co
        if kind == "water": vals += [0.0, max(0.0, min(1.0, foam_fn(p))), 1.0, 1.0]
        else: vals += [max(0.0, min(1.0, weight_fn(p))), 1.0, 1.0, 1.0]
    ca.data.foreach_set("color", vals)
    me.color_attributes.active_color = ca
    try: me.color_attributes.render_color_index = me.color_attributes.active_color_index
    except Exception: pass
    return ca

def _finish(o, mat, smooth=True):
    o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0), smooth=False, rnd=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = 1; md.limit_method = 'ANGLE'
    o = _finish(o, mat, smooth)
    set_attr(o, "rnd", random.random() if rnd is None else rnd)
    return o

def cyl(name, r, h, loc, mat, verts=12, rot=(0, 0, 0), r2=None, rnd=None, smooth=True):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o = _finish(o, mat, smooth)
    if smooth:
        es = o.modifiers.new("EdgeSplit", 'EDGE_SPLIT'); es.split_angle = math.radians(50)
    set_attr(o, "rnd", random.random() if rnd is None else rnd)
    return o

def torus(name, R, r, loc, mat, rot=(0, 0, 0), seg=16, mseg=4):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=mseg, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat)

def lathe(name, profile, loc, mat, steps=16, rot=(0, 0, 0), wobble=0.0, seed=0.0, cap=True):
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
    link(o); set_attr(o, "rnd", random.random())
    return o

def blob(name, loc, radius, mat, scale=(1, 1, 1), subdiv=1, amp=0.25, freq=1.6, seed=0.0, rot=(0, 0, 0), flat_bottom=None, flat_top=None, smooth=True):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    for v in bm.verts:
        n = v.co.normalized()
        k = 1.0 + amp * noise.noise(n * freq + Vector((seed, seed * 1.7, seed * 0.3)))
        p = Vector((n.x * radius * k * scale[0], n.y * radius * k * scale[1], n.z * radius * k * scale[2]))
        if flat_bottom is not None: p.z = max(p.z, flat_bottom)
        if flat_top is not None: p.z = min(p.z, flat_top)
        v.co = p
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = smooth
    link(o); set_attr(o, "rnd", random.random())
    return o

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

def tube(name, pts, radii, mat, sides=6, n=4, rnd=None, rect=None, caps=True, up=None):
    """A tapered tube along a Catmull-Rom path; rect=(w, h) gives a rectangular section (h along up).
    radii: (r0, r1) linear taper, or a list matching the sampled points."""
    c = catmull(pts, n)
    if isinstance(radii, (list, tuple)) and len(radii) == len(c): rr = list(radii)
    else: rr = [lerp(radii[0], radii[1], i / max(1, len(c) - 1)) for i in range(len(c))]
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    upv = Vector(up) if up else Vector((0, 0, 1))
    for i, p in enumerate(c):
        t = (c[min(i + 1, len(c) - 1)] - c[max(i - 1, 0)]).normalized()
        a = t.cross(upv if abs(t.dot(upv)) < 0.9 else Vector((1, 0, 0))).normalized(); b_ = t.cross(a).normalized()
        if rect:
            w, h = rect
            rings.append([bm.verts.new(p + a * (sx * w / 2) + b_ * (sy * h / 2)) for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
        else:
            rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / sides) + b_ * math.sin(2 * math.pi * k / sides)) * rr[i]) for k in range(sides)])
    ns = 4 if rect else sides
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(ns):
            j = (k + 1) % ns; bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    if caps:
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.normal_update(); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = not rect
    link(o)
    set_attr(o, "rnd", random.random() if rnd is None else rnd)
    return o

def mesh_from(name, verts, faces, mat, smooth=True, uvs=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = smooth
    if uvs is not None:
        uvl = me.uv_layers.new(name="UVMap")
        for li, loop in enumerate(me.loops): uvl.data[li].uv = uvs[loop.vertex_index]
    link(o); set_attr(o, "rnd", random.random())
    return o

def grid_mesh(name, nx, ny, fn, mat, smooth=True, uv_fn=None):
    """A (nx+1) x (ny+1) grid; fn(i/nx, j/ny) -> world point."""
    verts = []; uvs = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            p = fn(i / nx, j / ny); verts.append(p)
            if uv_fn: uvs.append(uv_fn(p, i / nx, j / ny))
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i; faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return mesh_from(name, verts, faces, mat, smooth, uvs if uv_fn else None)

def orient(o, dir_fn):
    """Flip faces so their normals agree with dir_fn(face centre, object-local) -> wanted direction (Unity culls back faces)."""
    me = o.data; bm = bmesh.new(); bm.from_mesh(me)
    flip = [f for f in bm.faces if f.normal.dot(Vector(dir_fn(f.calc_center_median()))) < 0]
    if flip: bmesh.ops.reverse_faces(bm, faces=flip)
    bm.to_mesh(me); bm.free(); me.update()
    return o

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

def fx_empty(name, loc, radius=0.05):
    """fx.fire.* / fx.candle.* / fx.lantern.* (LIVING_SCENES): display size = radius; also custom property 'radius'."""
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'SPHERE'; e.empty_display_size = radius; e.location = loc
    e["radius"] = radius; link(e)
    return e

def sound_empty(name, loc):
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'CONE'; e.empty_display_size = 0.3; e.location = loc; link(e)
    return e

def light_obj(name, kind, energy, color, loc, direction=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if direction is not None: lo.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return link(lo)

def sky_dome(name, mat, radius, seg=48, rings=18, el_min=-12.0):
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
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False; o.visible_transmission = False; o.visible_volume_scatter = False
    return link(o)

def image_from_array(name, arr):
    """arr: numpy float32 (h, w, 4) in linear RGBA -> a packed Blender image."""
    h, w = arr.shape[0], arr.shape[1]
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels.foreach_set(arr.astype("float32").ravel())
    img.pack()
    return img

# ----------------------------------------------------------------------------- preview page, cameras, stats, render
def preview_page(eye, look=(0, -1, 0), dist=0.6):
    pm_, pnt, pb = new_mat("PREVIEW_PageMat")
    pb.inputs["Base Color"].default_value = (0.78, 0.74, 0.64, 1); pb.inputs["Roughness"].default_value = 0.9
    pb.inputs["Emission Color"].default_value = (0.78, 0.74, 0.64, 1); pb.inputs["Emission Strength"].default_value = 0.6
    lv = Vector(look).normalized()
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(lv.x * dist, lv.y * dist, eye), rotation=(math.pi / 2, 0, math.atan2(lv.x, -lv.y)))
    page = bpy.context.active_object; page.name = "PREVIEW_Page"; page.scale = (0.4, 0.55, 1.0)
    page.data.materials.append(pm_)
    for c in page.users_collection: c.objects.unlink(page)
    link(page); page.hide_render = True
    S["page"] = page
    return page

def camera(name, loc, look_at, lens=18, clip_end=400):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = clip_end; cd.clip_start = 0.05
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    S.setdefault("cams", []).append(co)
    return co

def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

def print_budget():
    coll = S["coll"]
    _m = [o for o in coll.objects if o.type == 'MESH' and not o.name.startswith("PREVIEW_")]
    dg = bpy.context.evaluated_depsgraph_get()
    cat = {}
    for o in _m:
        e = o.evaluated_get(dg); me = e.to_mesh(); t = sum(len(p.vertices) - 2 for p in me.polygons); e.to_mesh_clear()
        k = o.get("merge") or (o.data.materials[0].name if o.data.materials else "?")
        cat[k] = cat.get(k, 0) + t
    print(f"PRE-MERGE objects={len(_m)} groups={len(cat)} tris={sum(cat.values())}")
    for k, v in sorted(cat.items(), key=lambda kv: -kv[1]): print(f"  BUDGET {k:30s} {v}")
    return sum(cat.values())

def render_cams(scene_id, exposure=None):
    args = S["args"]; scene = S["scene"]; OUT = S["out"]; page = S.get("page")
    exposure = exposure or {}
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    want = set(c.strip().lower() for c in args.cams.split(",") if c.strip())
    spp = scene.cycles.samples
    for c in S.get("cams", []):
        cn = c.name[4:].lower()
        if want and cn not in want: continue
        scene.camera = c
        if page: page.hide_render = c.name != "Cam_Page"
        scene.view_settings.exposure = exposure.get(c.name, exposure.get("*", 0.0))
        scene.render.filepath = os.path.join(OUT, f"blender-render_{scene_id}_{cn}_cycles-{spp}spp.png")
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:
            print("GPU render failed, retrying on CPU:", str(e)[:120]); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)
    scene.view_settings.exposure = 0.0
    if page: page.hide_render = True

# ----------------------------------------------------------------------------- bake + merge + export for Unity
LIVING = ("water.", "veg.", "cloth.")

def bake_and_export(gltf_name, size_for, default_size=256, keep_names=None, keep_uv=None, emit_only=None):
    """keep_names: material name -> merged mesh name (backdrops); keep_uv: mesh names whose UVs are hand-made;
    emit_only: mesh names baked as emission (unlit sky)."""
    args = S["args"]; scene = S["scene"]; COLL = S["coll"]; OUT = S["out"]
    keep_names = keep_names or {}; keep_uv = set(keep_uv or ()); emit_only = set(emit_only or ())
    if S.get("page"): bpy.data.objects.remove(S["page"])
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')                       # apply modifiers (bevels, edge splits)
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes:
        if o.parent is not None:
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for e in [o for o in COLL.objects if o.type == 'EMPTY' and not o.name.startswith(("anchor.", "fx.", "sound."))]:
        bpy.data.objects.remove(e)
    groups = {}
    for o in COLL.objects:
        if o.type != 'MESH' or not o.data.materials: continue
        if o.name.startswith("water."):
            groups[("__keep__", o.name)] = [o]; continue
        mg = o.get("merge")
        key = (mg + "|" + o.data.materials[0].name) if mg else o.data.materials[0].name
        groups.setdefault(key, []).append(o)
    # a named group that spans several materials is split by material (one baked material per mesh)
    mcount = {}
    for key in groups:
        if isinstance(key, str) and "|" in key: mcount[key.split("|")[0]] = mcount.get(key.split("|")[0], 0) + 1
    def group_name(key):
        if isinstance(key, tuple): return key[1]
        if "|" in key:
            mg, mat = key.split("|", 1)
            if mcount[mg] == 1: return mg
            return mg + "." + (mat[2:] if mat.startswith("M_") else mat)
        return None
    merged = []
    for key, objs in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active
        gn = group_name(key)
        if gn and (gn.startswith(LIVING) or gn.startswith("far.")): o.name = gn
        elif gn: o.name = "MESH_" + gn
        else: o.name = keep_names.get(key, "MESH_" + key[2:] if key.startswith("M_") else "MESH_" + key)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    scene.cycles.samples = 6
    scene.cycles.use_denoising = False
    scene.cycles.device = 'CPU'        # GPU bakes come back black when the shared GPU runs out of memory; CPU is slower but sure
    scene.render.bake.margin = 6
    tex_sizes = {}
    used = set()
    for o in merged:
        m = o.data.materials[0]
        if m.name in used:                      # a material shared by two merge groups: each bakes its own copy
            base_name = m.name; m = m.copy(); m.name = base_name + "_" + o.name.replace(".", "_"); o.data.materials[0] = m
            size_for.setdefault(m.name, size_for.get(base_name, default_size))
        used.add(m.name)
        for slot in range(1, len(o.data.materials)): o.data.materials[slot] = m
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        if o.name.startswith("water."):
            # plain water colour, no textures: Unity gives it the animated water material
            col = tuple(bsdf.inputs["Base Color"].default_value); rough = bsdf.inputs["Roughness"].default_value
            for n in list(nt.nodes): nt.nodes.remove(n)
            out = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
            nt.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
            nb.inputs["Base Color"].default_value = col; nb.inputs["Roughness"].default_value = rough
            tex_sizes[o.name] = 0
            continue
        size = max(64, size_for.get(m.name, default_size))
        tex_sizes[o.name] = size
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        if o.name not in keep_uv or not o.data.uv_layers:
            for uvl in list(o.data.uv_layers): o.data.uv_layers.remove(uvl)
            o.data.uv_layers.new(name="UVMap")
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
            bpy.ops.object.mode_set(mode='OBJECT')
        passes = [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]
        if o.name in emit_only: passes = [("BaseColor", 'EMIT', {}, False)]
        baked = {}
        metallic = bsdf.inputs["Metallic"].default_value
        transmission = bsdf.inputs["Transmission Weight"].default_value
        for pass_name, btype, extra, noncolor in passes:
            bsdf.inputs["Metallic"].default_value = 0.0 if pass_name == "BaseColor" else metallic
            bsdf.inputs["Transmission Weight"].default_value = 0.0 if pass_name == "BaseColor" else transmission
            img = bpy.data.images.new(f"T_{m.name[2:]}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            for n in nt.nodes: n.select = False
            tex.select = True; nt.nodes.active = tex
            bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            img.pack()
            baked[pass_name] = tex
            print("baked", img.name, size, flush=True)
        bsdf.inputs["Metallic"].default_value = metallic
        rough_v = bsdf.inputs["Roughness"].default_value
        for n in list(nt.nodes):
            if n not in baked.values(): nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
        if o.name in emit_only:
            nb.inputs["Base Color"].default_value = (0, 0, 0, 1)
            nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"]); nb.inputs["Emission Strength"].default_value = 1.0
            nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Base Color"])
            continue
        nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Base Color"])
        if "Roughness" in baked: nt.links.new(baked["Roughness"].outputs["Color"], nb.inputs["Roughness"])
        else: nb.inputs["Roughness"].default_value = rough_v
        if "Normal" in baked:
            nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(baked["Normal"].outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], nb.inputs["Normal"])
        nb.inputs["Metallic"].default_value = metallic
        if transmission > 0: nb.inputs["Transmission Weight"].default_value = transmission
    for c in S.get("cams", []): bpy.data.objects.remove(c)
    # static meshes carry no vertex colour: only the living meshes export COLOR_0
    for o in merged:
        if not o.name.startswith(LIVING):
            for ca in list(o.data.color_attributes): o.data.color_attributes.remove(ca)
    gl = os.path.join(OUT, gltf_name)
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False,
                              export_vertex_color='ACTIVE', export_extras=True)
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    tdir = os.path.join(OUT, "textures")
    jpg_mb = sum(os.path.getsize(os.path.join(tdir, f)) for f in os.listdir(tdir)) / 1e6 if os.path.isdir(tdir) else 0.0
    # GPU estimate after Unity's import: ASTC 6x6 (3.56 bpp) colour/roughness, 4x4 (8 bpp) normals, +1/3 for mips
    gpu = 0.0
    for o in merged:
        s = tex_sizes.get(o.name, 0)
        if not s: continue
        npass = 1 if o.name in emit_only else 3
        gpu += (s * s * 3.56 / 8 * (1 if npass == 1 else 2) + (s * s * 1.0 if npass == 3 else 0)) * 4 / 3
    gpu /= 1e6
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris} textures_jpeg_MB={jpg_mb:.1f} textures_gpu_est_MB={gpu:.1f}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\ntextures_jpeg_MB={jpg_mb:.2f}\ntextures_gpu_est_MB={gpu:.2f}\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={tex_sizes.get(o.name, 0)}\n")
        f.write("empties:\n")
        for o in COLL.objects:
            if o.type == 'EMPTY': f.write(f"  {o.name} {tuple(round(x, 3) for x in o.location)}\n")
            if o.type == 'LIGHT': f.write(f"  LIGHT {o.name} {o.data.type} {tuple(round(x, 3) for x in o.location)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, gltf_name.replace(".gltf", "_baked.blend")))
