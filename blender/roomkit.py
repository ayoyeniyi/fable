"""
Fable roomkit: the building blocks generated reading rooms are made from.

A generated room (docs/GENERATED_ROOMS.md) is a short Python script written by Claude for one setting of a reader's
own book. roomgen.py runs it inside Blender with only this kit, bpy/bmesh, math, random and mathutils available (no
imports, no files, no network), then bakes the lighting into textures and exports an unlit glTF the headset loads at
runtime. The kit carries the craft the environment brief asks for (docs/ENVIRONMENT_BRIEF.md) so a short script can
reach it: materials with colour, roughness and bump variation at a believable texture scale; terrain that follows a
structure (a valley, a shore, a rise) rather than even noise; rocks partly buried; trees, shrubs and grass varying in
size, lean and density; clustered rather than even scattering; rooms with real openings; a coherent sun and sky.

Units are metres, +Z up. The reader stands at reader(entrance) and faces the look point; the page floats ~0.6 m in
front of them at eye height, so keep that direction calm.
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler, noise

COLL = None            # the collection everything is built into
_ground = []           # height samplers: functions (x, y) -> z or None, consulted by ground()
_mats = {}
_rng = random.Random(1)
STATS = {"objects": 0}


def begin(seed=1):
    """Start an empty scene (roomgen calls this before the room script)."""
    global COLL, _rng
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials): bpy.data.materials.remove(m)
    COLL = bpy.data.collections.new("Room"); bpy.context.scene.collection.children.link(COLL)
    _ground.clear(); _mats.clear(); _rng = random.Random(seed)
    w = bpy.data.worlds.new("World"); bpy.context.scene.world = w; w.use_nodes = True


def lin(c):
    """sRGB 0-1 (how people think of colours) to the linear values Blender's shaders take."""
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3])


def rng():
    return _rng


def _link(o):
    COLL.objects.link(o); STATS["objects"] += 1
    return o


def _obj(name, bm, mat=None, smooth=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    if mat is not None: me.materials.append(mat if not isinstance(mat, str) else _mats[mat])
    return _link(o)


# ---------------------------------------------------------------- materials

KINDS = {
    #            roughness, rough var, colour var, bump, noise scale (per metre), metallic
    "plaster": (0.85, 0.08, 0.06, 0.15, 1.6, 0.0), "wood": (0.62, 0.12, 0.14, 0.25, 0.8, 0.0),
    "planks": (0.66, 0.12, 0.16, 0.35, 0.5, 0.0), "stone": (0.78, 0.10, 0.12, 0.6, 1.2, 0.0),
    "brick": (0.82, 0.08, 0.14, 0.45, 2.0, 0.0), "soil": (0.92, 0.05, 0.18, 0.55, 0.9, 0.0),
    "grass": (0.88, 0.06, 0.22, 0.30, 0.6, 0.0), "sand": (0.90, 0.05, 0.08, 0.35, 0.7, 0.0),
    "foliage": (0.70, 0.10, 0.20, 0.25, 2.5, 0.0), "bark": (0.85, 0.08, 0.12, 0.7, 3.0, 0.0),
    "fabric": (0.90, 0.04, 0.06, 0.10, 6.0, 0.0), "leather": (0.55, 0.12, 0.10, 0.20, 5.0, 0.0),
    "metal": (0.38, 0.12, 0.08, 0.10, 3.0, 1.0), "water": (0.08, 0.03, 0.04, 0.05, 0.3, 0.0),
    "tile": (0.40, 0.10, 0.08, 0.15, 2.0, 0.0), "paper": (0.90, 0.04, 0.05, 0.05, 8.0, 0.0),
    "glass": (0.05, 0.02, 0.02, 0.0, 1.0, 0.0), "snow": (0.75, 0.06, 0.03, 0.25, 0.8, 0.0),
    "rock": (0.80, 0.10, 0.14, 0.7, 0.9, 0.0), "thatch": (0.95, 0.03, 0.15, 0.6, 4.0, 0.0),
}


def mat(name, color, kind="plaster", rough=None, emission=0.0, emission_color=None):
    """A physically plausible material: base colour (sRGB 0-1 tuple), varied in colour and roughness by noise at a
    believable scale, with a light bump. kind picks the variation preset (see KINDS). emission > 0 makes a light
    surface (a fire, a lamp shade, a window glow)."""
    if name in _mats: return _mats[name]
    r0, rv, cv, bump, scale, metal = KINDS.get(kind, KINDS["plaster"])
    if rough is not None: r0 = rough
    m = bpy.data.materials.new("M_" + name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = scale; n1.inputs["Detail"].default_value = 6.0
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = scale * 7.0; n2.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"]); nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
    if kind in ("wood", "planks", "bark"):
        n1.inputs["Distortion"].default_value = 0.6
        mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 1.0, 9.0) if kind == "bark" else (1.0, 9.0, 1.0)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], n1.inputs["Vector"])
    c = Vector(lin(color))
    ramp = nt.nodes.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
    lo = tuple(max(0.0, x * (1 - cv)) for x in c) + (1,); hi = tuple(min(1.0, x * (1 + cv * 0.8)) for x in c) + (1,)
    e[0].position = 0.3; e[0].color = lo; e[1].position = 0.72; e[1].color = hi
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    # broad patches (dry grass, damp stone, sun-faded wood) at a few metres' scale, so large surfaces are not uniform
    n3 = nt.nodes.new("ShaderNodeTexNoise"); n3.inputs["Scale"].default_value = scale * 0.18; n3.inputs["Detail"].default_value = 2.0
    nt.links.new(tc.outputs["Object"], n3.inputs["Vector"])
    patch = nt.nodes.new("ShaderNodeMix"); patch.data_type = 'RGBA'; patch.blend_type = 'MIX'
    shift = {"grass": (1.25, 1.1, 0.7), "foliage": (1.15, 1.12, 0.8), "soil": (1.2, 1.12, 1.0), "sand": (1.08, 1.06, 1.0)}.get(kind, (1.12, 1.08, 1.02))
    pr = nt.nodes.new("ShaderNodeMapRange"); pr.inputs["From Min"].default_value = 0.45; pr.inputs["From Max"].default_value = 0.7
    pr.inputs["To Max"].default_value = 0.55 if kind in ("grass", "foliage", "soil") else 0.3
    nt.links.new(n3.outputs["Fac"], pr.inputs["Value"]); nt.links.new(pr.outputs["Result"], patch.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], patch.inputs["A"]); patch.inputs["B"].default_value = tuple(min(1.0, c[i] * shift[i]) for i in range(3)) + (1,)
    ramp_out = patch.outputs["Result"]
    if kind in ("stone", "rock", "plaster", "brick", "soil"):
        # weathering: darker, damper low down and in hollows
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = 0.6
        mr.inputs["To Min"].default_value = 0.35; mr.inputs["To Max"].default_value = 0.0
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
        nt.links.new(ramp_out, mix.inputs["A"]); mix.inputs["B"].default_value = (0.55, 0.52, 0.48, 1)
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    else:
        nt.links.new(ramp_out, b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = max(0.02, r0 - rv); rr.inputs["To Max"].default_value = min(1.0, r0 + rv)
    nt.links.new(n2.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = metal
    if bump > 0:
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump * 0.5; bp.inputs["Distance"].default_value = 0.02
        nt.links.new(n2.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    if emission > 0:
        b.inputs["Emission Color"].default_value = lin(emission_color or color) + (1,)
        b.inputs["Emission Strength"].default_value = emission
    if kind == "glass":
        b.inputs["Transmission Weight"].default_value = 0.9
    m["base"] = list(lin(color))
    _mats[name] = m
    return m


def M(name):
    return _mats[name]


# ---------------------------------------------------------------- ground

def ground(x, y):
    """The height of the ground at (x, y): the highest registered surface under that point (terrain, a floor), or 0."""
    zs = [z for z in (f(x, y) for f in _ground) if z is not None]
    return max(zs) if zs else 0.0


def terrain(name, size, material, res=96, relief=0.6, scale=14.0, seed=3, slope=(0.0, 0.0), flat=(), valley=None,
            shore=None, centre=(0.0, 0.0)):
    """Ground with structure. size: (sx, sy) metres. relief: noise amplitude (m) at feature scale `scale` (m).
    slope: (dz/dx, dz/dy) a general tilt. flat: [(x, y, radius, z)] places levelled for the reader or a building
    (blended softly into the land). valley: (x0, y0, x1, y1, width, depth) a channel along a line, e.g. a river bed.
    shore: (direction_deg, distance, drop) the land falls away below water level beyond `distance` from centre
    toward that direction. Registers itself as ground. Returns the object."""
    sx, sy = size; cx, cy = centre
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    shore_dir = Vector((math.cos(math.radians(shore[0])), math.sin(math.radians(shore[0])))) if shore else None

    def h(x, y):
        p = Vector((x / scale, y / scale, 0)) + off
        z = relief * (noise.fractal(p, 0.55, 2.1, 5) * 0.8 + 0.25 * noise.noise(p * 0.31))
        z += slope[0] * (x - cx) + slope[1] * (y - cy)
        if valley:
            x0, y0, x1, y1, w, d = valley
            a = Vector((x0, y0)); bb = Vector((x1, y1)); q = Vector((x, y)); ab = bb - a
            t = max(0.0, min(1.0, (q - a).dot(ab) / max(ab.length_squared, 1e-6)))
            dist = (q - (a + ab * t)).length
            wob = w * (1 + 0.25 * noise.noise(Vector((x * 0.08, y * 0.08, 5.0))))
            if dist < wob: z -= d * (0.5 + 0.5 * math.cos(math.pi * dist / wob))
        if shore_dir is not None:
            along = Vector((x - cx, y - cy)).dot(shore_dir) - shore[1] + 2.0 * noise.noise(Vector((x * 0.05, y * 0.05, 9.0)))
            if along > 0: z -= shore[2] * min(1.0, along / 8.0) ** 1.4
        for fx, fy, fr, fz in flat:
            d = math.hypot(x - fx, y - fy)
            if d < fr * 1.8:
                k = 1.0 if d < fr else 0.5 + 0.5 * math.cos(math.pi * (d - fr) / (fr * 0.8))
                z = z * (1 - k) + fz * k
        return z

    bm = bmesh.new()
    nx = res; ny = max(8, int(res * sy / sx))
    verts = [[bm.verts.new((cx - sx / 2 + sx * i / nx, cy - sy / 2 + sy * j / ny, 0)) for i in range(nx + 1)] for j in range(ny + 1)]
    for row in verts:
        for v in row: v.co.z = h(v.co.x, v.co.y)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
    o = _obj(name, bm, material, smooth=True)
    x0, x1, y0, y1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
    _ground.append(lambda x, y: h(x, y) if x0 <= x <= x1 and y0 <= y <= y1 else None)
    return o


def water(name, size, level, material, centre=(0.0, 0.0), res=24):
    """A still water surface at height `level` (a lake, the sea, a river pool). Does not count as ground."""
    bm = bmesh.new(); sx, sy = size
    bmesh.ops.create_grid(bm, x_segments=res, y_segments=res, size=0.5)
    for v in bm.verts:
        v.co.x = centre[0] + v.co.x * sx; v.co.y = centre[1] + v.co.y * sy
        v.co.z = level + 0.015 * noise.noise(Vector((v.co.x * 0.4, v.co.y * 0.4, 1.0)))
    return _obj(name, bm, material, smooth=True)


# ---------------------------------------------------------------- shapes

def box(name, size, loc, material, rot=(0, 0, 0), bevel=0.0):
    """An axis box of size (x, y, z) whose base centre is at loc, rotated by rot (degrees). bevel rounds its edges."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], (v.co.z + 0.5) * size[2]))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(bevel, min(size) * 0.45), segments=1, affect='EDGES', profile=0.5)
    o = _obj(name, bm, material)
    o.location = loc; o.rotation_euler = Euler([math.radians(a) for a in rot])
    return o


def cylinder(name, radius, height, loc, material, rot=(0, 0, 0), sides=12, top_radius=None):
    """A cylinder (or tapered cone with top_radius) standing on loc."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=sides, radius1=radius,
                          radius2=radius if top_radius is None else top_radius, depth=height)
    for v in bm.verts: v.co.z += height / 2
    o = _obj(name, bm, material, smooth=True)
    o.location = loc; o.rotation_euler = Euler([math.radians(a) for a in rot])
    return o


def blob(name, radius, loc, material, squash=(1, 1, 1), roughness=0.25, detail=2, seed=0):
    """A lumpy rounded mass (a boulder, a foliage clump, a haystack, a cushion): an icosphere displaced by noise."""
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=detail, radius=radius)
    o3 = Vector((seed * 1.7, seed * 2.3, seed * 0.9))
    for v in bm.verts:
        n = v.co.normalized()
        d = 1 + roughness * noise.fractal(n * 1.6 + o3, 0.5, 2.0, 3)
        v.co = Vector((n.x * squash[0], n.y * squash[1], n.z * squash[2])) * radius * d
    o = _obj(name, bm, material, smooth=True)
    o.location = loc
    return o


def mesh(name, verts, faces, material, loc=(0, 0, 0), smooth=False):
    """Any shape from vertex and face lists."""
    bm = bmesh.new(); vs = [bm.verts.new(v) for v in verts]
    for f in faces: bm.faces.new([vs[i] for i in f])
    o = _obj(name, bm, material, smooth=smooth); o.location = loc
    return o


# ---------------------------------------------------------------- nature

def rock(name, loc, size, material, seed=0, bury=0.35, flat=0.65):
    """A rock sitting in the ground: buried by `bury` of its height, flattened by `flat`, with a skirt of soil."""
    x, y = loc[0], loc[1]; z = ground(x, y)
    r = rng()
    o = blob(name, size, (x, y, z + size * flat * (0.5 - bury)), material, squash=(1 + r.uniform(-0.2, 0.3), 1 + r.uniform(-0.2, 0.2), flat),
             roughness=0.32, detail=2, seed=seed)
    o.rotation_euler.z = r.uniform(0, 6.28)
    return o


def tree(name, loc, height, bark, leaves, kind="broadleaf", seed=0, lean=6.0):
    """A tree with a tapering trunk, a few limbs and irregular leaf masses (broadleaf), layered tiers (conifer),
    a fan crown (palm) or bare branches (dead). Grounded at loc (z from the ground). Returns its parts."""
    r = random.Random(seed); x, y = loc[0], loc[1]; z = ground(x, y) - 0.15
    parts = []
    lean_dir = r.uniform(0, 360); la = math.radians(r.uniform(0, lean))
    top = Vector((x + math.sin(la) * height * 0.6 * math.cos(math.radians(lean_dir)), y + math.sin(la) * height * 0.6 * math.sin(math.radians(lean_dir)), z + height * (0.62 if kind == "broadleaf" else 0.95)))
    base = Vector((x, y, z)); trunk_r = height * (0.028 if kind != "palm" else 0.018)
    parts.append(_limb(name + ".trunk", base, top, trunk_r, trunk_r * 0.45, bark))
    if kind == "broadleaf":
        for i in range(r.randint(3, 5)):
            a = r.uniform(0, 6.28); t = r.uniform(0.55, 0.95)
            p0 = base.lerp(top, t); L = height * r.uniform(0.22, 0.38)
            p1 = p0 + Vector((math.cos(a) * L, math.sin(a) * L, L * r.uniform(0.3, 0.8)))
            parts.append(_limb(f"{name}.limb{i}", p0, p1, trunk_r * 0.45, trunk_r * 0.15, bark))
            for k in range(3):
                q = p1 + Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-0.4, 0.6))) * height * 0.07
                parts.append(blob(f"{name}.crown{i}_{k}", height * r.uniform(0.08, 0.14), q, leaves, squash=(1.1, 1.0, 0.8), roughness=0.6, detail=2, seed=seed * 31 + i * 3 + k))
        parts.append(blob(f"{name}.crown", height * 0.24, top + Vector((0, 0, height * 0.08)), leaves, squash=(1.15, 1.1, 0.8), roughness=0.45, detail=2, seed=seed * 7 + 9))
    elif kind == "conifer":
        tiers = r.randint(5, 7)
        for i in range(tiers):
            t = 0.22 + 0.75 * i / tiers; rad = height * 0.26 * (1 - t) + 0.12
            c = base.lerp(top, t)
            parts.append(cylinder(f"{name}.tier{i}", rad, height * 0.2, (c.x, c.y, c.z - height * 0.06), leaves, sides=9, top_radius=0.02))
    elif kind == "palm":
        for i in range(7):
            a = i * 6.28 / 7 + r.uniform(-0.2, 0.2); L = height * 0.32
            tip = top + Vector((math.cos(a) * L, math.sin(a) * L, -L * 0.35))
            mid = top.lerp(tip, 0.5) + Vector((0, 0, L * 0.15))
            parts.append(mesh(f"{name}.frond{i}", [top, mid + Vector((-math.sin(a), math.cos(a), 0)) * L * 0.18, tip, mid - Vector((-math.sin(a), math.cos(a), 0)) * L * 0.18], [(0, 1, 2, 3)], leaves))
    else:   # dead
        for i in range(r.randint(3, 6)):
            a = r.uniform(0, 6.28); t = r.uniform(0.4, 0.95); p0 = base.lerp(top, t); L = height * r.uniform(0.15, 0.3)
            parts.append(_limb(f"{name}.limb{i}", p0, p0 + Vector((math.cos(a) * L, math.sin(a) * L, L * 0.6)), trunk_r * 0.35, 0.01, bark))
    return parts


def _limb(name, p0, p1, r0, r1, material, sides=7):
    d = p1 - p0
    o = cylinder(name, r0, d.length, (0, 0, 0), material, sides=sides, top_radius=r1)
    o.location = p0; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    return o


def shrub(name, loc, size, leaves, seed=0):
    """A low shrub: two or three overlapping irregular masses, sitting on the ground."""
    r = random.Random(seed); x, y = loc[0], loc[1]; z = ground(x, y)
    parts = [blob(f"{name}.{i}", size * r.uniform(0.5, 0.8), (x + r.uniform(-size, size) * 0.5, y + r.uniform(-size, size) * 0.5, z + size * 0.25),
                  leaves, squash=(1.2, 1.1, 0.7), roughness=0.55, detail=2, seed=seed * 5 + i) for i in range(r.randint(2, 3))]
    # a scatter of smaller tufts over the mass breaks its outline, so it reads as leaves rather than a boulder
    for k in range(r.randint(4, 7)):
        a = r.uniform(0, 6.283); e = r.uniform(0.1, 0.9)
        p = (x + math.cos(a) * size * 0.7 * math.cos(e), y + math.sin(a) * size * 0.7 * math.cos(e), z + size * (0.2 + 0.5 * math.sin(e)))
        parts.append(blob(f"{name}.t{k}", size * r.uniform(0.18, 0.3), p, leaves, squash=(1, 1, 0.8), roughness=0.6, detail=1, seed=seed * 11 + k))
    return parts


def tufts(name, centre, radius, count, height, material, seed=0, flowers=None, flower_share=0.0):
    """Grass, reeds or flowers as clustered crossed blades, varying in height and lean; one object. flowers: a
    material for blossoms (small quads at the tips of `flower_share` of the blades)."""
    r = random.Random(seed); bm = bmesh.new(); fl = bmesh.new() if flowers else None
    cx, cy = centre
    for i in range(count):
        ang = r.uniform(0, 6.28); d = radius * math.sqrt(r.random()) * (0.6 + 0.4 * noise.noise(Vector((ang, seed, 0.3))))
        x, y = cx + math.cos(ang) * d, cy + math.sin(ang) * d; z = ground(x, y) - 0.02
        hgt = height * r.uniform(0.5, 1.25); w = hgt * r.uniform(0.05, 0.1); a = r.uniform(0, 3.14)
        lean = Vector((r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), 1)).normalized() * hgt
        for k in (0, 1):
            aa = a + k * 1.5708; ox, oy = math.cos(aa) * w, math.sin(aa) * w
            v = [bm.verts.new((x - ox, y - oy, z)), bm.verts.new((x + ox, y + oy, z)), bm.verts.new((x + lean.x + ox * 0.15, y + lean.y + oy * 0.15, z + lean.z))]
            bm.faces.new(v)
        if fl is not None and r.random() < flower_share:
            s = hgt * 0.12; tx, ty, tz = x + lean.x, y + lean.y, z + lean.z
            v = [fl.verts.new((tx - s, ty, tz)), fl.verts.new((tx, ty - s, tz + s * 0.3)), fl.verts.new((tx + s, ty, tz)), fl.verts.new((tx, ty + s, tz + s * 0.3))]
            fl.faces.new(v)
    return _cards(name, bm, material, fl, flowers)


def groundcover(name, material, area, near=(0.0, 0.0), blades=6000, height=0.4, seed=0, avoid=(), flowers=None, flower_share=0.0,
                patchiness=0.6):
    """Grass, reeds or heather over a whole area: dense near `near` (the reader) and thinning with distance, in
    natural patches (noise), with gaps; crossed blades varying in height and lean. One object (two with flowers).
    Roughly 2 triangles a blade (+2 a flower)."""
    r = random.Random(seed); bm = bmesh.new(); fl = bmesh.new() if flowers else None
    x0, y0, x1, y1 = area; nx, ny = near; placed = 0; tries = 0
    while placed < blades and tries < blades * 12:
        tries += 1
        # distance-weighted sampling: half the blades within ~8 m of the reader
        if r.random() < 0.55:
            a = r.uniform(0, 6.283); d = abs(r.gauss(0, 6.0)); x, y = nx + math.cos(a) * d, ny + math.sin(a) * d
        else:
            x, y = r.uniform(x0, x1), r.uniform(y0, y1)
        if not (x0 <= x <= x1 and y0 <= y <= y1): continue
        if any(math.hypot(x - ax, y - ay) < ar for ax, ay, ar in avoid): continue
        dens = 0.5 + 0.5 * noise.noise(Vector((x * 0.18, y * 0.18, seed + 0.5)))
        if r.random() > dens ** (1 + 3 * patchiness) * 1.6: continue
        z = ground(x, y) - 0.02
        hgt = height * r.uniform(0.45, 1.3) * (0.7 + 0.6 * dens); w = hgt * r.uniform(0.035, 0.07); ang = r.uniform(0, 3.14)
        lean = Vector((r.uniform(-0.35, 0.35), r.uniform(-0.35, 0.35), 1)).normalized() * hgt
        ox, oy = math.cos(ang) * w, math.sin(ang) * w
        v = [bm.verts.new((x - ox, y - oy, z)), bm.verts.new((x + ox, y + oy, z)), bm.verts.new((x + lean.x, y + lean.y, z + lean.z))]
        bm.faces.new(v); placed += 1
        if fl is not None and r.random() < flower_share:
            s = hgt * 0.1; tx, ty, tz = x + lean.x, y + lean.y, z + lean.z
            fv = [fl.verts.new((tx - s, ty, tz)), fl.verts.new((tx, ty - s, tz + s * 0.4)), fl.verts.new((tx + s, ty, tz)), fl.verts.new((tx, ty + s, tz + s * 0.4))]
            fl.faces.new(fv)
    return _cards(name, bm, material, fl, flowers)


def _cards(name, bm, material, fl, flowers):
    # blades: v = 0 at the root, 1 at the tip (the third vertex of each triangle); flowers: v = 1
    for b_ in (bm, fl):
        if b_ is None or not len(b_.faces): continue
        uv = b_.loops.layers.uv.new("UVMap")
        for f in b_.faces:
            for i, l in enumerate(f.loops): l[uv].uv = (0.5, 0.97 if (b_ is fl or i == 2) else 0.03)
    o = _obj(name, bm, material); o.data.materials[0]["card"] = True
    if fl is not None and len(fl.verts):
        f2 = _obj(name + ".flowers", fl, flowers); f2.data.materials[0]["card"] = True
        return [o, f2]
    if fl is not None: fl.free()
    return [o]


def scatter(area, count, seed=0, clusters=3, spread=0.35, avoid=()):
    """Clustered positions (not an even scatter): `clusters` centres in `area` = (x0, y0, x1, y1), points gathered
    around them with falloff. avoid: [(x, y, radius)] kept clear (the reader's spot, a path). Returns [(x, y)]."""
    r = random.Random(seed); x0, y0, x1, y1 = area; out = []
    cs = [(r.uniform(x0, x1), r.uniform(y0, y1), r.uniform(0.5, 1.5)) for _ in range(max(1, clusters))]
    tries = 0
    while len(out) < count and tries < count * 40:
        tries += 1
        cx, cy, wgt = r.choice(cs); s = spread * min(x1 - x0, y1 - y0) * wgt
        x, y = r.gauss(cx, s), r.gauss(cy, s)
        if not (x0 <= x <= x1 and y0 <= y <= y1): continue
        if any(math.hypot(x - ax, y - ay) < ar for ax, ay, ar in avoid): continue
        out.append((x, y))
    return out


# ---------------------------------------------------------------- buildings and rooms

def room(name, width, depth, height, walls, floor, ceiling=None, openings=(), thickness=0.18, centre=(0.0, 0.0)):
    """A rectangular room with real openings. Walls are named n, s, e, w (+y, -y, +x, -x). openings: dicts
    {"wall": "s", "at": 0.0 (offset along the wall from its middle, m), "width": 1.0, "height": 2.1, "sill": 0.0}
    for doors (sill 0) and windows. ceiling None leaves it open to the sky. Registers the floor as ground."""
    cx, cy = centre; hw, hd = width / 2, depth / 2
    box(name + ".floor", (width + thickness * 2, depth + thickness * 2, 0.06), (cx, cy, -0.06), floor)
    _ground.append(lambda x, y: 0.0 if abs(x - cx) <= hw + thickness and abs(y - cy) <= hd + thickness else None)
    if ceiling is not None:
        box(name + ".ceiling", (width + thickness * 2, depth + thickness * 2, 0.08), (cx, cy, height), ceiling)
    specs = {"n": (width, (cx, cy + hd + thickness / 2), 0), "s": (width, (cx, cy - hd - thickness / 2), 0),
             "e": (depth, (cx + hw + thickness / 2, cy), 90), "w": (depth, (cx - hw - thickness / 2, cy), 90)}
    for wname, (length, (wx, wy), rot) in specs.items():
        ops = sorted([o for o in openings if o["wall"] == wname], key=lambda o: o.get("at", 0))
        x = -length / 2 - (thickness if rot == 0 else 0); end = length / 2 + (thickness if rot == 0 else 0)
        segs = []
        for o in ops:
            a = o.get("at", 0) - o["width"] / 2; b = o.get("at", 0) + o["width"] / 2
            segs.append((x, a, 0, height)); sill = o.get("sill", 0.0); top = sill + o["height"]
            if sill > 0: segs.append((a, b, 0, sill))
            if top < height: segs.append((a, b, top, height))
            x = b
        segs.append((x, end, 0, height))
        for i, (s0, s1, z0, z1) in enumerate(segs):
            if s1 - s0 < 0.01 or z1 - z0 < 0.01: continue
            m = (s0 + s1) / 2
            loc = (wx + (m if rot == 0 else 0), wy + (m if rot != 0 else 0), z0)
            box(f"{name}.wall.{wname}{i}", (s1 - s0, thickness, z1 - z0), loc, walls, rot=(0, 0, rot))


def gable_roof(name, width, depth, eave, pitch_deg, material, centre=(0.0, 0.0), overhang=0.3, thickness=0.12):
    """A pitched roof over a width x depth plan, ridge along y, eaves at height `eave`."""
    cx, cy = centre; hw = width / 2 + overhang; hd = depth / 2 + overhang
    rise = hw * math.tan(math.radians(pitch_deg)); L = math.hypot(hw, rise)
    for side in (-1, 1):
        o = box(f"{name}.{'w' if side < 0 else 'e'}", (L, depth + overhang * 2, thickness), (0, 0, 0), material)
        o.rotation_euler = Euler((0, math.atan2(rise, hw) * side, 0))
        o.location = (cx + side * hw / 2, cy, eave + rise / 2 - thickness)
    gable = [(-width / 2, 0, 0), (width / 2, 0, 0), (0, 0, rise - overhang * math.tan(math.radians(pitch_deg)))]
    for s, y in (("n", cy + depth / 2), ("s", cy - depth / 2)):
        mesh(f"{name}.gable.{s}", [(cx + v[0], y, eave + v[2]) for v in gable], [(0, 1, 2)], material)


def table(name, loc, material, size=(1.2, 0.75, 0.76), rot=0):
    x, y, z = loc[0], loc[1], ground(loc[0], loc[1]) if len(loc) < 3 else loc[2]
    parts = [box(name + ".top", (size[0], size[1], 0.04), (x, y, z + size[2] - 0.04), material, rot=(0, 0, rot), bevel=0.008)]
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    for dx in (-1, 1):
        for dy in (-1, 1):
            lx, ly = dx * (size[0] / 2 - 0.06), dy * (size[1] / 2 - 0.06)
            parts.append(box(f"{name}.leg{dx}{dy}", (0.05, 0.05, size[2] - 0.04), (x + lx * c - ly * s, y + lx * s + ly * c, z), material, rot=(0, 0, rot)))
    return parts


def chair(name, loc, material, rot=0):
    x, y = loc[0], loc[1]; z = ground(x, y); c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    parts = [box(name + ".seat", (0.44, 0.42, 0.04), (x, y, z + 0.44), material, rot=(0, 0, rot), bevel=0.006)]
    for dx in (-1, 1):
        for dy in (-1, 1):
            lx, ly = dx * 0.19, dy * 0.18; h = 0.92 if dy > 0 else 0.44
            parts.append(box(f"{name}.leg{dx}{dy}", (0.035, 0.035, h), (x + lx * c - ly * s, y + lx * s + ly * c, z), material, rot=(0, 0, rot)))
    bx, by = 0, 0.18
    parts.append(box(name + ".back", (0.42, 0.03, 0.3), (x + bx * c - by * s, y + bx * s + by * c, z + 0.6), material, rot=(0, 0, rot)))
    return parts


def shelf(name, loc, material, book_materials=(), width=1.0, height=1.8, depth=0.32, rot=0, seed=0):
    """A bookcase or dresser with shelves; filled with books of varied height and lean when book_materials given."""
    x, y = loc[0], loc[1]; z = ground(x, y); r = random.Random(seed)
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    def at(lx, ly): return (x + lx * c - ly * s, y + lx * s + ly * c)
    parts = [box(name + ".back", (width, 0.02, height), (*at(0, depth / 2), z), material, rot=(0, 0, rot))]
    for side in (-1, 1): parts.append(box(f"{name}.side{side}", (0.03, depth, height), (*at(side * width / 2, 0), z), material, rot=(0, 0, rot)))
    n = max(2, int(height / 0.36))
    for i in range(n + 1):
        sz = z + i * (height - 0.03) / n
        parts.append(box(f"{name}.board{i}", (width, depth, 0.025), (*at(0, 0), sz), material, rot=(0, 0, rot)))
        if book_materials and i < n:
            bx = -width / 2 + 0.03
            while bx < width / 2 - 0.08:
                bw = r.uniform(0.025, 0.06); bh = r.uniform(0.2, 0.3)
                if r.random() < 0.12: bx += r.uniform(0.04, 0.12); continue
                parts.append(box(f"{name}.book{i}_{len(parts)}", (bw, depth * r.uniform(0.6, 0.85), bh), (*at(bx + bw / 2, 0.02), sz + 0.025), r.choice(book_materials), rot=(0, r.uniform(-3, 3), rot)))
                bx += bw + 0.002
    return parts


def bed(name, loc, frame, linen, rot=0, size=(1.4, 2.0)):
    x, y = loc[0], loc[1]; z = ground(x, y)
    p = [box(name + ".frame", (size[0], size[1], 0.35), (x, y, z), frame, rot=(0, 0, rot), bevel=0.02)]
    p.append(box(name + ".mattress", (size[0] - 0.08, size[1] - 0.08, 0.2), (x, y, z + 0.35), linen, rot=(0, 0, rot), bevel=0.06))
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot)); hy = size[1] / 2
    p.append(box(name + ".head", (size[0], 0.06, 1.0), (x - hy * s, y + hy * c, z), frame, rot=(0, 0, rot)))
    p.append(blob(name + ".pillow", 0.3, (x - (hy - 0.3) * s, y + (hy - 0.3) * c, z + 0.6), linen, squash=(1.2, 0.6, 0.35), roughness=0.08))
    return p


def hearth(name, loc, stone, fire=True, rot=0, width=1.4):
    """A stone fireplace (or open hearth) with an optional fire that is also a light source."""
    x, y = loc[0], loc[1]; z = ground(x, y)
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    def at(lx, ly): return (x + lx * c - ly * s, y + lx * s + ly * c)
    p = [box(name + ".back", (width, 0.3, 1.6), (*at(0, 0.25), z), stone, rot=(0, 0, rot), bevel=0.02)]
    for sd in (-1, 1): p.append(box(f"{name}.jamb{sd}", (0.25, 0.5, 1.2), (*at(sd * (width / 2 - 0.12), 0), z), stone, rot=(0, 0, rot), bevel=0.02))
    p.append(box(name + ".lintel", (width, 0.55, 0.3), (*at(0, 0), z + 1.2), stone, rot=(0, 0, rot), bevel=0.02))
    p.append(box(name + ".chimney", (width * 0.7, 0.45, 2.0), (*at(0, 0.15), z + 1.5), stone, rot=(0, 0, rot)))
    if fire:
        f = mat("fire", (1.0, 0.45, 0.12), kind="fabric", emission=6.0)
        p.append(blob(name + ".embers", 0.22, (*at(0, 0.0), z + 0.08), f, squash=(1.4, 0.8, 0.45), roughness=0.4))
        lamp(name + ".fire", (*at(0, -0.1), z + 0.45), power=180, color=(1.0, 0.55, 0.25), radius=0.25)
    return p


def rug(name, loc, size, material, rot=0):
    x, y = loc[0], loc[1]
    return box(name, (size[0], size[1], 0.012), (x, y, ground(x, y) + 0.001), material, rot=(0, 0, rot), bevel=0.004)


def candle(name, loc, wax, power=12):
    x, y, z = loc
    p = cylinder(name, 0.025, 0.18, (x, y, z), wax, sides=8)
    lamp(name + ".flame", (x, y, z + 0.22), power=power, color=(1.0, 0.68, 0.36), radius=0.02)
    return p


# ---------------------------------------------------------------- light, sky, reader

def sun(elevation, azimuth, strength=4.0, color=(1.0, 0.95, 0.86), softness=1.5):
    """The one sun: elevation and azimuth in degrees (azimuth 0 = from +x, 90 = from +y). Also sets the world's sky
    light to match (see sky())."""
    l = bpy.data.lights.new("light.sun", 'SUN'); l.energy = strength; l.color = lin(color); l.angle = math.radians(softness)
    o = bpy.data.objects.new("light.sun", l); _link(o)
    el, az = math.radians(elevation), math.radians(azimuth)
    d = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    return o


def lamp(name, loc, power=60, color=(1.0, 0.8, 0.6), radius=0.05):
    """A point light (lamp, candle, fire, window glow). power in watts."""
    l = bpy.data.lights.new("light." + name, 'POINT'); l.energy = power; l.color = lin(color); l.shadow_soft_size = radius
    o = bpy.data.objects.new("light." + name, l); o.location = loc; _link(o)
    return o


def area_light(name, loc, size, power, color=(0.9, 0.95, 1.0), aim=(0, 0, -1)):
    """A soft rectangular light: daylight through a window or doorway (aim it into the room)."""
    l = bpy.data.lights.new("light." + name, 'AREA'); l.energy = power; l.color = lin(color); l.shape = 'RECTANGLE'
    l.size, l.size_y = size[0], size[1]
    o = bpy.data.objects.new("light." + name, l); o.location = loc; _link(o)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, -1)).rotation_difference(Vector(aim).normalized())
    return o


def sky(zenith, horizon, strength=1.0, radius=120.0, ground_color=None):
    """The sky: a world light of these colours (sRGB 0-1) and a dome mesh (SkyDome) with the same gradient, which
    becomes the unlit backdrop the headset shows. Below the horizon it fades to ground_color (default: a dim tone of
    the horizon), so no pale gap shows under distant land. For interiors with no view out, call it anyway (dim)."""
    gcol = lin(ground_color) if ground_color else tuple(x * 0.35 for x in lin(horizon))

    def gradient(nt, z_socket, z_horizon, z_top):
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = z_horizon - 0.06 * (z_top - z_horizon)
        mr.inputs["From Max"].default_value = z_top
        nt.links.new(z_socket, mr.inputs["Value"])
        ramp = nt.nodes.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
        e[0].position = 0.0; e[0].color = gcol + (1,)
        e[1].position = 1.0; e[1].color = lin(zenith) + (1,)
        h = e.new(0.07); h.color = lin(horizon) + (1,)
        m2 = e.new(0.35); m2.color = tuple(0.5 * a + 0.5 * b for a, b in zip(lin(horizon), lin(zenith))) + (1,)
        nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
        return ramp.outputs["Color"]

    w = bpy.context.scene.world; nt = w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])      # world: the view direction, z from -1 to 1
    nt.links.new(gradient(nt, sep.outputs["Z"], 0.0, 0.75), bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength; nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    m = bpy.data.materials.new("M_SkyDome"); m.use_nodes = True; mt = m.node_tree
    for n in list(mt.nodes): mt.nodes.remove(n)
    mo = mt.nodes.new("ShaderNodeOutputMaterial"); em = mt.nodes.new("ShaderNodeEmission")
    gc = mt.nodes.new("ShaderNodeTexCoord"); gs = mt.nodes.new("ShaderNodeSeparateXYZ")
    mt.links.new(gc.outputs["Generated"], gs.inputs["Vector"])       # dome: its bounding box, z from 0 to 1
    mt.links.new(gradient(mt, gs.outputs["Z"], 0.5, 0.875), em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0; mt.links.new(em.outputs["Emission"], mo.inputs["Surface"])
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)
    for v in bm.verts: v.co *= radius
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    o = _obj("SkyDome", bm, m, smooth=True)
    o.visible_shadow = False; o.visible_diffuse = False; o.visible_glossy = False
    return o


def far_hills(color, radius=90.0, height=8.0, seed=4, material_kind="grass"):
    """A ring of distant land on the horizon (backdrop, named far.hills): soft, low-contrast silhouettes."""
    m = mat("far_hills", color, kind=material_kind)
    bm = bmesh.new(); n = 96; ring_lo = []; ring_hi = []
    for i in range(n + 1):
        a = 6.2832 * i / n
        h = height * (0.4 + 0.6 * (0.5 + 0.5 * noise.fractal(Vector((math.cos(a) * 2 + seed, math.sin(a) * 2, 0)), 0.5, 2.0, 4)))
        ring_lo.append(bm.verts.new((math.cos(a) * radius, math.sin(a) * radius, -2)))
        ring_hi.append(bm.verts.new((math.cos(a) * radius * 0.98, math.sin(a) * radius * 0.98, h)))
    for i in range(n):
        bm.faces.new((ring_lo[i + 1], ring_lo[i], ring_hi[i], ring_hi[i + 1]))
    return _obj("far.hills", bm, m)


READER = {}


def reader(entrance, look, eye=1.55):
    """Where the reader stands: entrance (x, y) on the ground, facing the look point (x, y, z). The page floats
    ~0.6 m from their eyes toward the look point; keep that direction calm."""
    x, y = entrance[0], entrance[1]; z = ground(x, y)
    a = bpy.data.objects.new("anchor.reader.entrance", None); a.location = (x, y, z); _link(a)
    b = bpy.data.objects.new("anchor.reader.look", None); b.location = tuple(look) if len(look) == 3 else (look[0], look[1], z + eye); _link(b)
    c = bpy.data.objects.new("anchor.scene.centre", None); c.location = (x, y, z); _link(c)
    READER.update(entrance=Vector((x, y, z)), look=Vector(b.location), eye=eye)
    return a
