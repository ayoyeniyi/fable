"""
Fable: shared helpers for the three hand-built Treasure Island rooms (build_benbow_cove.py, build_squires_library.py,
build_spyglass_tavern.py). The room scripts import this module (it sits next to them in blender/).

What is here is the method of the earlier hand-built rooms (build_lilliput_beach.py, build_ithaca_hall.py), gathered
in one place so the three rooms share it: the node-expression helper for procedural PBR materials, geometry helpers,
the anchors / living-scene empties (docs/LIVING_SCENES.md), Cycles stills from the reader's eye, and the bake + merge +
glTF export that FableBuild imports.

Living-scene meshes (water.*, veg.*, cloth.*) keep their names through the merge and carry a colour attribute named
"Color" that the glTF exporter writes as COLOR_0 (R = sway weight for veg/cloth, G = foam for water). Every other
mesh's colour attributes are removed before export so nothing else carries COLOR_0.
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix, noise

# ----------------------------------------------------------------------------- arguments and scene
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
    ap.add_argument("--prefix", default="render_", help="file name prefix for the stills")
    ap.add_argument("--nosave", action="store_true", help="skip saving the source .blend")
    a = ap.parse_args(argv)
    a.out = os.path.abspath(a.out); os.makedirs(a.out, exist_ok=True)
    return a

S = {}          # module state: scene, collection, args

def reset_scene(coll_name, args, bounces=6, diffuse=4, clamp=10.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 20 if args.quick else args.samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = bounces
    scene.cycles.diffuse_bounces = diffuse
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 4
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.cycles.sample_clamp_indirect = clamp
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'; prefs.get_devices()
        for d in prefs.devices: d.use = True
        scene.cycles.device = 'GPU'
    except Exception as e:
        print("Metal not available, CPU render:", e)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    coll = bpy.data.collections.new(coll_name)
    scene.collection.children.link(coll)
    S.update(scene=scene, coll=coll, args=args)
    return scene, coll

def link(obj):
    S["coll"].objects.link(obj); return obj

def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def fbm(p, octaves=4, lac=2.0, gain=0.5):
    s, a, f = 0.0, 1.0, 1.0
    for _ in range(octaves):
        s += a * noise.noise(p * f); a *= gain; f *= lac
    return s

# ----------------------------------------------------------------------------- node-expression helper
class F:
    """A float socket with arithmetic that builds Math nodes."""
    def __init__(s, g, sock): s.g, s.s = g, sock
    def __add__(s, o): return s.g.m('ADD', s, o)
    __radd__ = __add__
    def __sub__(s, o): return s.g.m('SUBTRACT', s, o)
    def __rsub__(s, o): return s.g.m('SUBTRACT', o, s)
    def __mul__(s, o): return s.g.m('MULTIPLY', s, o)
    __rmul__ = __mul__
    def __truediv__(s, o): return s.g.m('DIVIDE', s, o)
    def __rtruediv__(s, o): return s.g.m('DIVIDE', o, s)
    def __neg__(s): return s.g.m('MULTIPLY', s, -1.0)
    def sin(s): return s.g.m('SINE', s)
    def floor(s): return s.g.m('FLOOR', s)
    def fract(s): return s.g.m('FRACT', s)
    def abs(s): return s.g.m('ABSOLUTE', s)
    def sqrt(s): return s.g.m('SQRT', s)
    def min(s, o): return s.g.m('MINIMUM', s, o)
    def max(s, o): return s.g.m('MAXIMUM', s, o)
    def pow(s, o): return s.g.m('POWER', s, o)
    def clamp(s): return s.g.m('MINIMUM', s.g.m('MAXIMUM', s, 0.0), 1.0)

class G:
    def __init__(s, nt): s.nt = nt; s.i = 0; s._pos = None; s._geo = None
    def n(s, kind, **kw):
        nd = s.nt.nodes.new(kind); nd.location = (-2600 + 220 * (s.i // 18), -170 * (s.i % 18)); s.i += 1
        for k, v in kw.items(): setattr(nd, k, v)
        return nd
    def set(s, sock, v):
        if isinstance(v, F): s.nt.links.new(v.s, sock)
        elif isinstance(v, bpy.types.NodeSocket): s.nt.links.new(v, sock)
        elif isinstance(v, (tuple, list)):
            n = len(sock.default_value); v = tuple(v)
            sock.default_value = v + (1.0,) * (n - len(v)) if len(v) < n else v[:n]
        else: sock.default_value = v
    def m(s, op, a, b=None, c=None):
        nd = s.n("ShaderNodeMath", operation=op)
        for i, v in enumerate((a, b, c)):
            if v is not None: s.set(nd.inputs[i], v)
        return F(s, nd.outputs[0])
    def pos(s):
        if s._pos is None: s._pos = s.n("ShaderNodeTexCoord").outputs["Object"]
        return s._pos
    def geo(s):
        if s._geo is None: s._geo = s.n("ShaderNodeNewGeometry")
        return s._geo
    def nz(s):
        return s.sep(s.geo().outputs["Normal"])[2]
    def sep(s, vec):
        nd = s.n("ShaderNodeSeparateXYZ"); s.set(nd.inputs[0], vec)
        return F(s, nd.outputs[0]), F(s, nd.outputs[1]), F(s, nd.outputs[2])
    def comb(s, x, y, z=0.0):
        nd = s.n("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)): s.set(nd.inputs[i], v)
        return nd.outputs[0]
    def scale(s, vec, k):
        nd = s.n("ShaderNodeVectorMath", operation='SCALE'); s.set(nd.inputs[0], vec); nd.inputs["Scale"].default_value = k
        return nd.outputs[0]
    def stretch(s, vec, sx, sy, sz):
        mp = s.n("ShaderNodeMapping"); s.set(mp.inputs["Vector"], vec); mp.inputs["Scale"].default_value = (sx, sy, sz)
        return mp.outputs[0]
    def noise(s, vec, scale, detail=4.0, rough=0.55, dist=0.0, dims='3D'):
        nd = s.n("ShaderNodeTexNoise", noise_dimensions=dims); s.set(nd.inputs["Vector"], vec)
        nd.inputs["Scale"].default_value = scale; nd.inputs["Detail"].default_value = detail
        nd.inputs["Roughness"].default_value = rough; nd.inputs["Distortion"].default_value = dist
        return F(s, nd.outputs["Fac"]), nd.outputs["Color"]
    def white(s, vec):
        nd = s.n("ShaderNodeTexWhiteNoise", noise_dimensions='3D'); s.set(nd.inputs["Vector"], vec)
        return F(s, nd.outputs["Value"]), nd.outputs["Color"]
    def vor(s, vec, scale, feature='F1', rand=1.0, metric='EUCLIDEAN', out="Distance"):
        nd = s.n("ShaderNodeTexVoronoi", feature=feature, distance=metric); s.set(nd.inputs["Vector"], vec)
        nd.inputs["Scale"].default_value = scale; nd.inputs["Randomness"].default_value = rand
        if out == "all": return F(s, nd.outputs["Distance"]), nd.outputs["Color"], nd.outputs["Position"]
        return F(s, nd.outputs[out]) if out == "Distance" else nd.outputs[out]
    def ss(s, x, e0, e1):
        nd = s.n("ShaderNodeMapRange", interpolation_type='SMOOTHSTEP')
        s.set(nd.inputs["Value"], x); s.set(nd.inputs["From Min"], e0); s.set(nd.inputs["From Max"], e1)
        return F(s, nd.outputs["Result"])
    def ramp(s, fac, stops, interp=None):
        nd = s.n("ShaderNodeValToRGB"); cr = nd.color_ramp
        if interp: cr.interpolation = interp
        while len(cr.elements) > 1: cr.elements.remove(cr.elements[-1])
        cr.elements[0].position = stops[0][0]; cr.elements[0].color = tuple(stops[0][1]) + (1.0,) * (4 - len(stops[0][1]))
        for p, c in stops[1:]:
            e = cr.elements.new(p); e.color = tuple(c) + (1.0,) * (4 - len(c))
        s.set(nd.inputs["Fac"], fac)
        return nd.outputs["Color"]
    def mix(s, fac, a, b, blend='MIX'):
        nd = s.n("ShaderNodeMix", data_type='RGBA', blend_type=blend, clamp_factor=True)
        s.set(nd.inputs["Factor"], fac); s.set(nd.inputs[6], a); s.set(nd.inputs[7], b)
        return nd.outputs[2]
    def mul(s, a, b, fac=1.0): return s.mix(fac, a, b, 'MULTIPLY')
    def lerp(s, fac, a, b): return a + (b - a) * fac
    def bw(s, col):
        nd = s.n("ShaderNodeRGBToBW"); s.set(nd.inputs[0], col); return F(s, nd.outputs[0])
    def attr(s, name):
        return s.n("ShaderNodeAttribute", attribute_name=name)
    def ao(s, dist):
        nd = s.n("ShaderNodeAmbientOcclusion"); nd.inputs["Distance"].default_value = dist
        return nd.outputs["Color"]
    def bump(s, bsdf, height, strength, distance):
        nd = s.n("ShaderNodeBump"); nd.inputs["Strength"].default_value = strength; nd.inputs["Distance"].default_value = distance
        s.set(nd.inputs["Height"], height); s.nt.links.new(nd.outputs["Normal"], bsdf.inputs["Normal"])

def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, bsdf, G(nt)

def plain(name, color, rough=0.5, metallic=0.0, emission=None, strength=0.0, coat=0.0, transmission=0.0, alpha=1.0):
    m, nt, b, g = new_mat(name)
    b.inputs["Base Color"].default_value = tuple(color) + (1,)
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if coat: b.inputs["Coat Weight"].default_value = coat
    if transmission: b.inputs["Transmission Weight"].default_value = transmission
    if emission is not None:
        b.inputs["Emission Color"].default_value = tuple(emission) + (1,); b.inputs["Emission Strength"].default_value = strength
    return m

def noisy(name, colors, scale=8.0, rough=0.8, bump=0.2, bump_dist=0.003, detail=6.0, stretch=(1, 1, 1), sheen=0.0,
          metallic=0.0, ao=0.0, coat=0.0, warp=0.0, rough_var=0.0):
    m, nt, b, g = new_mat(name)
    P = g.stretch(g.pos(), *stretch)
    n1, _ = g.noise(P, scale, detail, 0.6, warp)
    stops = [(i / max(1, len(colors) - 1) * 0.6 + 0.2, c) for i, c in enumerate(colors)]
    col = g.ramp(n1, stops)
    if ao: col = g.mul(col, g.ao(ao), 0.5)
    g.set(b.inputs["Base Color"], col)
    if rough_var:
        g.set(b.inputs["Roughness"], rough - rough_var * 0.5 + n1 * rough_var)
    else:
        b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if sheen: b.inputs["Sheen Weight"].default_value = sheen
    if coat: b.inputs["Coat Weight"].default_value = coat
    if bump:
        n2, _ = g.noise(P, scale * 6, 4)
        g.bump(b, n2, bump, bump_dist)
    return m

# ----------------------------------------------------------------------------- geometry helpers
def _finish(o, mat, smooth_=False):
    o.data.materials.append(mat)
    if smooth_:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def box(name, size, loc, mat, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        md = o.modifiers.new("bevel", 'BEVEL'); md.width = bevel; md.segments = 1; md.limit_method = 'NONE'
    return _finish(o, mat)

def cyl(name, r, hgt, loc, mat, verts=16, rot=(0, 0, 0), r2=None, smooth_=True):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=hgt, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=hgt, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat, smooth_=smooth_)

def mesh_obj(name, bm, mat, smooth_=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    if smooth_:
        for p in me.polygons: p.use_smooth = True
    return link(o)

def from_pydata(name, verts, faces, mat, smooth_=False):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    if smooth_:
        for p in me.polygons: p.use_smooth = True
    return link(o)

def lathe(name, profile, loc, mat, steps=16, rot=(0, 0, 0)):
    """profile: list of (radius, z). A closed solid of revolution about local Z."""
    verts, faces = [], []
    n = len(profile)
    for i in range(steps):
        a = 2 * math.pi * i / steps
        for r, z in profile: verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(steps):
        j = (i + 1) % steps
        for k in range(n - 1):
            faces.append([i * n + k, j * n + k, j * n + k + 1, i * n + k + 1])
    o = from_pydata(name, verts, faces, mat, smooth_=True)
    o.location = loc; o.rotation_euler = rot
    return o

def set_color_attr(me, fn, name="tint"):
    """fn(index, co) -> (r, g, b, a), stored per point as FLOAT_COLOR."""
    at = me.color_attributes.get(name) or me.color_attributes.new(name, 'FLOAT_COLOR', 'POINT')
    for i, v in enumerate(me.vertices): at.data[i].color = fn(i, v.co)
    return at

class Builder:
    """Accumulates many small pieces into one mesh, with a per-vertex tint (RGBA) and, for living meshes,
    a per-vertex 'Color' (R = sway weight / G = foam)."""
    def __init__(s, name, mat, living=False):
        s.name, s.mat, s.living = name, mat, living
        s.verts, s.faces, s.tints, s.weights = [], [], [], []
    def add(s, verts, faces, tint=(1, 1, 1, 1), weights=None):
        base = len(s.verts)
        s.verts.extend(tuple(v) for v in verts)
        s.faces.extend([[base + i for i in f] for f in faces])
        s.tints.extend([tuple(tint) + (1.0,) * (4 - len(tint))] * len(verts))
        if weights is None: weights = [(0.0, 0.0, 0.0, 1.0)] * len(verts)
        s.weights.extend(weights)
    def finish(s, smooth_=True):
        if not s.verts: return None
        me = bpy.data.meshes.new(s.name)
        me.from_pydata(s.verts, [], s.faces); me.update()
        o = bpy.data.objects.new(s.name, me); me.materials.append(s.mat)
        if smooth_:
            for p in me.polygons: p.use_smooth = True
        t = s.tints; set_color_attr(me, lambda i, co: t[i], "tint")
        if s.living:
            w = s.weights; set_color_attr(me, lambda i, co: w[i], "Color")
        return link(o)

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

def living_empty(name, loc, size=0.1):
    """fx.* and sound.* empties (docs/LIVING_SCENES.md). The display size (for fx.fire, the fire's radius in metres)
    is also written as the custom property 'radius', which the glTF exporter carries as node extras."""
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'SPHERE' if name.startswith("fx.") else 'PLAIN_AXES'
    e.empty_display_size = size; e.location = loc; e["radius"] = float(size); link(e)
    return e

def light_obj(name, kind, energy, color, loc, direction=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if direction is not None: lo.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return link(lo)

def camera(name, loc, look_at, lens=24, clip_end=160):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = clip_end; cd.clip_start = 0.03
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co

def sharpen_by_angle(me, deg=38.0):
    """Smooth shading with sharp edges above the angle (rock fractures and ledges stay crisp)."""
    bm = bmesh.new(); bm.from_mesh(me)
    lim = math.radians(deg)
    for f in bm.faces: f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim: e.smooth = False
    bm.to_mesh(me); bm.free()

# ----------------------------------------------------------------------------- angular rocks (planar fractures, not blobs)
def rock_piece(centre, size, rnd, cuts=7, bury=0.3, flat=0.75, yaw=None, bedding=0.0, sub=1, jitter=0.05, tilt=0.0, detail=0, amp=0.08):
    """A boulder made the way rock breaks: a rough ball cut by planes (joints and bedding), so it has flat faces,
    edges and corners. size = (sx, sy, sz) half-extents. Returns (verts, faces) in world space, its base sunk by
    `bury` of its height."""
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub + 1, radius=1.0)
    for v in bm.verts:
        v.co *= 1.0 + 0.18 * noise.noise(v.co * 1.3 + Vector((rnd.uniform(0, 50), rnd.uniform(0, 50), 0)))
    planes = []
    for k in range(cuts):
        if k < 2 and bedding:
            n = Vector((rnd.uniform(-1, 1) * bedding, rnd.uniform(-1, 1) * bedding, 1.0 if k == 0 else -1.0))
        else:
            a = rnd.uniform(0, 2 * math.pi); el = rnd.uniform(-0.35, 0.6)
            n = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        n.normalize(); planes.append((n, rnd.uniform(0.55, 0.85)))
    for n, d in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=n * d, plane_no=n, clear_outer=True)
        edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            try: bmesh.ops.holes_fill(bm, edges=edges, sides=0)
            except Exception: pass
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    # little chips: jitter the vertices along their normals
    bm.normal_update()
    for v in bm.verts: v.co += v.normal * rnd.uniform(-jitter, jitter)
    if detail:
        # a hero rock: subdivide the facets and break them with smaller fractures and weathering
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=detail, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.normal_update()
        sd = Vector((rnd.uniform(0, 50), rnd.uniform(0, 50), rnd.uniform(0, 50)))
        for v in bm.verts:
            q = v.co * 2.2 + sd
            _d, pts = noise.voronoi(q)
            c = pts[0]
            f = (math.sin(c.x * 12.9898 + c.y * 78.233 + c.z * 37.719) * 43758.5453) % 1.0
            facet = (f - 0.5) * 0.6 + (q - c).dot(Vector((math.sin(f * 40), math.cos(f * 40), 0.3))) * 0.25
            v.co += v.normal * amp * (facet + 0.6 * noise.noise(v.co * 1.3 + sd))
    yaw = rnd.uniform(0, 2 * math.pi) if yaw is None else yaw
    R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(tilt, 3, 'X')
    sx, sy, sz = size
    zmin = min(v.co.z for v in bm.verts) * sz
    verts = []
    for v in bm.verts:
        p = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
        if p.z < zmin + (1 - flat) * sz * 0.3: p.z = zmin + (p.z - zmin) * 0.6
        p.z -= zmin + bury * 2 * sz
        verts.append(Vector(centre) + R @ p)
    faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    return verts, faces

# ----------------------------------------------------------------------------- render
def render_cams(cams, out, page=None, page_cams=(), exposure=None, default_exposure=0.0, prefix="render_"):
    args = S["args"]; scene = S["scene"]
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    want = set(c.strip().lower() for c in args.cams.split(",") if c.strip())
    exposure = exposure or {}
    done = []
    for c in cams:
        if want and c.name[4:].lower() not in want: continue
        scene.camera = c
        if page is not None: page.hide_render = c.name not in page_cams
        scene.view_settings.exposure = exposure.get(c.name, default_exposure)
        scene.render.filepath = os.path.join(out, f"{prefix}{c.name[4:].lower()}.png")
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:
            print("GPU render failed, retrying on CPU:", e); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)
        done.append(scene.render.filepath)
    if len(done) > 1: contact_sheet(done, os.path.join(out, prefix + "contact.png"))

def contact_sheet(paths, dest, cols=2):
    """Tile the stills into one image (for checking several views at once)."""
    import numpy as np
    ims = []
    for p in paths:
        im = bpy.data.images.load(p); w, h = im.size
        px = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(px)
        ims.append(px.reshape(h, w, 4)); bpy.data.images.remove(im)
    h, w = ims[0].shape[:2]; rows = (len(ims) + cols - 1) // cols
    sheet = np.zeros((rows * h, cols * w, 4), dtype=np.float32); sheet[..., 3] = 1
    for i, a in enumerate(ims):
        r = rows - 1 - i // cols; c = i % cols
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = a[:h, :w]
    out = bpy.data.images.new("contact", cols * w, rows * h, alpha=False)
    out.pixels.foreach_set(sheet.ravel()); out.filepath_raw = dest; out.file_format = 'PNG'; out.save()
    print("contact sheet", dest)

# ----------------------------------------------------------------------------- budget, bake + merge + export
def tri_count_eval(o):
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); me = e.to_mesh()
    t = sum(len(p.vertices) - 2 for p in me.polygons); e.to_mesh_clear(); return t

def budget(skip=("PagePreview",)):
    cat = {}
    for o in [o for o in S["coll"].objects if o.type == 'MESH' and o.name not in skip and not o.hide_render]:
        k = o.data.materials[0].name if o.data.materials else "?"
        cat[k] = cat.get(k, 0) + tri_count_eval(o)
    print(f"PRE-MERGE materials={len(cat)} tris={sum(cat.values())}")
    for k, v in sorted(cat.items(), key=lambda kv: -kv[1]): print(f"  BUDGET {k:26s} {v}")
    return cat

def apply_all_transforms():
    bpy.ops.object.select_all(action='DESELECT')
    for o in S["coll"].objects:
        if o.type == 'MESH': o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.select_all(action='DESELECT')

def bake_and_export(basename, keep_names, size_for, keep_uv=(), lightmap_uv=(), emit_only=(), remove=(), default_div=8,
                    rough_div=None, out=None):
    """keep_names: material name -> exported object name (living meshes, backdrop). size_for: material -> texture size
    (an int, or (colour, roughness, normal) sizes; 0 means 'not baked: constant'). keep_uv: object names whose own UVs
    are kept. lightmap_uv: materials unwrapped with lightmap pack (many tiny pieces: grass blades). emit_only: material
    names baked as emission only (unlit backdrop). Returns stats."""
    args = S["args"]; scene = S["scene"]; coll = S["coll"]; out = out or args.out
    for o in remove:
        if o and o.name in bpy.data.objects: bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in coll.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.select_all(action='DESELECT')
    groups = {}
    for o in coll.objects:
        if o.type != 'MESH' or not o.data.materials: continue
        groups.setdefault(o.data.materials[0].name, []).append(o)
    merged = []
    for mname, objs in groups.items():
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active; o.name = keep_names.get(mname, "MESH_" + mname[2:])
        o.data.name = o.name
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    scene.cycles.samples = 8
    scene.render.bake.margin = 6
    T_ = args.tex
    tex_sizes, tex_bytes_gpu = {}, 0.0
    for o in merged:
        m = o.data.materials[0]; nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        spec = size_for.get(m.name, T_ // default_div)
        if isinstance(spec, int): spec = (spec, spec // (rough_div or 4) if spec >= 256 else spec, spec)
        spec = tuple(max(0, s) for s in spec)
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        if o.name not in keep_uv or not o.data.uv_layers:
            while o.data.uv_layers: o.data.uv_layers.remove(o.data.uv_layers[0])
            o.data.uv_layers.new(name="UVMap")
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            if m.name in lightmap_uv:
                bpy.ops.uv.lightmap_pack(PREF_CONTEXT='ALL_FACES', PREF_PACK_IN_ONE=True, PREF_MARGIN_DIV=0.3)
            else:
                bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004)
            bpy.ops.object.mode_set(mode='OBJECT')
        if m.name in emit_only:
            passes = [("BaseColor", 'EMIT', {}, False, spec[0])]
        else:
            passes = [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False, spec[0])]
            if spec[1]: passes.append(("Roughness", 'ROUGHNESS', {}, True, spec[1]))
            if spec[2]: passes.append(("Normal", 'NORMAL', {}, True, spec[2]))
        baked = {}
        for pass_name, btype, extra, noncolor, size in passes:
            size = max(32, size)
            img = bpy.data.images.new(f"T_{m.name[2:]}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            for n in nt.nodes: n.select = False
            tex.select = True; nt.nodes.active = tex
            try:
                bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            except RuntimeError as e:
                print("GPU bake failed, retrying on CPU:", e); scene.cycles.device = 'CPU'
                bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            # a shared GPU that runs out of memory can leave the image black without raising: check, redo on the CPU
            import numpy as np
            px = np.empty(size * size * 4, dtype=np.float32); img.pixels.foreach_get(px)
            if float(px.reshape(-1, 4)[:, :3].max()) < 0.003 and scene.cycles.device != 'CPU':
                print("bake came back black, redoing on the CPU:", img.name)
                dev = scene.cycles.device; scene.cycles.device = 'CPU'
                bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
                scene.cycles.device = dev
            img.filepath_raw = os.path.join(out, "textures", img.name + ".png"); os.makedirs(os.path.dirname(img.filepath_raw), exist_ok=True)
            img.file_format = 'PNG'; img.save(); img.pack()
            baked[pass_name] = tex
            tex_bytes_gpu += size * size * (8.0 / 36.0) * 4.0 / 3.0 / 1.0   # ASTC 6x6 (3.56 bpp) with mips
            tex_sizes.setdefault(o.name, []).append(size)
            print("baked", img.name, size)
        metallic = bsdf.inputs["Metallic"].default_value
        emis = bsdf.inputs["Emission Strength"].default_value; ecol = tuple(bsdf.inputs["Emission Color"].default_value)
        elinked = bsdf.inputs["Emission Color"].is_linked
        rough_v = bsdf.inputs["Roughness"].default_value
        for n in list(nt.nodes):
            if n not in baked.values(): nt.nodes.remove(n)
        outn = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(nb.outputs["BSDF"], outn.inputs["Surface"])
        nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Base Color"])
        if "Roughness" in baked: nt.links.new(baked["Roughness"].outputs["Color"], nb.inputs["Roughness"])
        else: nb.inputs["Roughness"].default_value = rough_v
        if "Normal" in baked:
            nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(baked["Normal"].outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], nb.inputs["Normal"])
        nb.inputs["Metallic"].default_value = metallic
        if emis > 0 and m.name not in emit_only:
            nb.inputs["Emission Strength"].default_value = min(emis, 4.0)
            if elinked: nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"])
            else: nb.inputs["Emission Color"].default_value = ecol
    # only the living meshes carry COLOR_0
    for o in merged:
        living = o.name.split(".")[0] in ("water", "veg", "cloth")
        for a in list(o.data.color_attributes):
            if not (living and a.name == "Color"): o.data.color_attributes.remove(a)
        if living and "Color" in o.data.color_attributes:
            o.data.color_attributes.active_color = o.data.color_attributes["Color"]
    for c in [o for o in coll.objects if o.type == 'CAMERA']: bpy.data.objects.remove(c)
    gl = os.path.join(out, basename + ".gltf")
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=88, export_lights=True,
                              export_cameras=False, export_extras=True, export_vertex_color='NAME', export_vertex_color_name='Color',
                              export_all_vertex_colors=False, export_active_vertex_color_when_no_material=False)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    tdir = os.path.join(out, "textures")
    for f in os.listdir(tdir):                      # the bake intermediates (the export wrote JPEGs)
        if f.lower().endswith(".png"): os.remove(os.path.join(tdir, f))
    jpg = sum(os.path.getsize(os.path.join(tdir, f)) for f in os.listdir(tdir) if f.lower().endswith((".jpg", ".jpeg")))
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris} jpeg_MB={jpg/1e6:.1f} astc6x6_MB={tex_bytes_gpu/1e6:.1f}")
    with open(os.path.join(out, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\njpeg_MB={jpg/1e6:.2f}\nastc6x6_mips_MB={tex_bytes_gpu/1e6:.2f}\n")
        for o in sorted(merged, key=lambda o: -sum(len(p.vertices) - 2 for p in o.data.polygons)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={sum(len(p.vertices) - 2 for p in o.data.polygons)} tex={tex_sizes.get(o.name, [])}\n")
        for o in coll.objects:
            if o.type == 'EMPTY': f.write(f"empty {o.name} at {tuple(round(c, 2) for c in o.location)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, basename + "_baked.blend"))
    return dict(tris=tris, verts=verts, jpeg_mb=jpg / 1e6, gpu_mb=tex_bytes_gpu / 1e6)
