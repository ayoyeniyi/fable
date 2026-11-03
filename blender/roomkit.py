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
_rooms = {}            # room specs by name, for panelling(), windows(), doors()
STATS = {"objects": 0}


def begin(seed=1):
    """Start an empty scene (roomgen calls this before the room script)."""
    global COLL, _rng
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials): bpy.data.materials.remove(m)
    COLL = bpy.data.collections.new("Room"); bpy.context.scene.collection.children.link(COLL)
    _ground.clear(); _mats.clear(); _clear.clear(); _rooms.clear(); _rng = random.Random(seed)
    w = bpy.data.worlds.new("World"); bpy.context.scene.world = w; w.use_nodes = True


def lin(c):
    """sRGB 0-1 (how people think of colours) to the linear values Blender's shaders take."""
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3])


def rng():
    """The room's seeded random.Random (use it for varied sizes and angles)."""
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


# ---------------------------------------------------------------- part builder (private)
# Parts are built into one bmesh per material inside a local frame (origin + yaw), then become one object per
# material: far fewer objects than one box each, and roomgen merges by material anyway.

class _B:
    def __init__(self, name, loc=(0, 0, 0), rot=0.0):
        self.name = name; self.parts = {}
        self.M = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(rot), 4, 'Z')

    def bm(self, m):
        if m.name not in self.parts: self.parts[m.name] = (m, bmesh.new())
        return self.parts[m.name][1]

    def _fin(self, m, vs, T, smooth, bevel=0.0, seg=1):
        bm = self.bm(m)
        faces = {f for v in vs for f in v.link_faces}
        edges = list({e for v in vs for e in v.link_edges})
        bmesh.ops.transform(bm, matrix=self.M @ T, verts=vs)
        if bevel > 0:
            res = bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=seg, affect='EDGES', profile=0.5, clamp_overlap=True)
            faces |= set(res.get("faces", []))
        if smooth:
            for f in faces:
                if f.is_valid: f.smooth = True

    def box(self, m, size, loc, rot=(0, 0, 0), bevel=0.0, seg=1, smooth=False):
        """size (x, y, z) with its base centre at loc (local), rotated by rot (degrees, XYZ)."""
        vs = bmesh.ops.create_cube(self.bm(m), size=1.0)["verts"]
        for v in vs: v.co = Vector((v.co.x * size[0], v.co.y * size[1], (v.co.z + 0.5) * size[2]))
        self._fin(m, vs, _mx(loc, rot), smooth, min(bevel, min(size) * 0.45), seg)

    def cyl(self, m, r0, h, loc, rot=(0, 0, 0), sides=10, r1=None, smooth=True):
        vs = bmesh.ops.create_cone(self.bm(m), cap_ends=True, cap_tris=False, segments=sides, radius1=r0,
                                   radius2=r0 if r1 is None else r1, depth=h)["verts"]
        for v in vs: v.co.z += h / 2
        bm = self.bm(m); faces = {f for v in vs for f in v.link_faces}
        bmesh.ops.transform(bm, matrix=self.M @ _mx(loc, rot), verts=vs)
        if smooth:
            for f in faces: f.smooth = len(f.verts) == 4

    def seg(self, m, p0, p1, r0, r1, sides=6):
        """A tapered rod between two local points."""
        p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
        if d.length < 1e-5: return
        vs = bmesh.ops.create_cone(self.bm(m), cap_ends=True, cap_tris=False, segments=sides, radius1=r0, radius2=r1, depth=d.length)["verts"]
        for v in vs: v.co.z += d.length / 2
        T = Matrix.Translation(p0) @ Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
        bm = self.bm(m); faces = {f for v in vs for f in v.link_faces}
        bmesh.ops.transform(bm, matrix=self.M @ T, verts=vs)
        for f in faces: f.smooth = len(f.verts) == 4

    def ball(self, m, r, loc, squash=(1, 1, 1), sub=1, rot=(0, 0, 0)):
        vs = bmesh.ops.create_icosphere(self.bm(m), subdivisions=sub + 1, radius=1.0)["verts"]
        for v in vs: v.co = Vector((v.co.x * squash[0] * r, v.co.y * squash[1] * r, v.co.z * squash[2] * r))
        self._fin(m, vs, _mx(loc, rot), True)

    def tube(self, m, pts, radii, sides=6, cap=False):
        """A bent tube through local points (branches, rails, scrolls)."""
        bm = self.bm(m); pts = [Vector(p) for p in pts]; rings = []
        prev = None
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            if prev is None: prev = t.orthogonal().normalized()
            u = (prev - t * prev.dot(t)).normalized(); w = t.cross(u); prev = u
            rings.append([bm.verts.new(self.M @ (p + (u * math.cos(a) + w * math.sin(a)) * radii[i]))
                          for a in (6.2832 * k / sides for k in range(sides))])
        for a, b in zip(rings, rings[1:]):
            for k in range(sides):
                f = bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k])); f.smooth = True
        if cap: bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])

    def poly(self, m, pts, smooth=False):
        bm = self.bm(m)
        f = bm.faces.new([bm.verts.new(self.M @ Vector(p)) for p in pts]); f.smooth = smooth
        return f

    def mesh(self, m, verts, faces, smooth=False):
        bm = self.bm(m); vs = [bm.verts.new(self.M @ Vector(v)) for v in verts]
        for f in faces:
            ff = bm.faces.new([vs[i] for i in f]); ff.smooth = smooth

    def at(self, lx, ly, lz=0.0):
        return self.M @ Vector((lx, ly, lz))

    def done(self):
        out = []
        for k, (m, bm) in self.parts.items():
            if len(bm.faces): out.append(_obj(f"{self.name}.{k[2:]}", bm, m))
            else: bm.free()
        self.parts = {}
        return out


def _mx(loc=(0, 0, 0), rot=(0, 0, 0)):
    return Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot]).to_matrix().to_4x4()


def _spline(points, step, smooth=True):
    """Evenly spaced samples [(pos2, tangent2, s)] along a Catmull-Rom curve through 2D points."""
    P = [Vector((p[0], p[1])) for p in points]
    if len(P) < 2: return []
    dense = []
    for i in range(len(P) - 1):
        p0 = P[i - 1] if i > 0 else P[i] * 2 - P[i + 1]; p1, p2 = P[i], P[i + 1]
        p3 = P[i + 2] if i + 2 < len(P) else P[i + 1] * 2 - P[i]
        n = max(2, int((p2 - p1).length / 0.25))
        for k in range(n):
            t = k / n
            if smooth:
                t2, t3 = t * t, t * t * t
                dense.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
            else:
                dense.append(p1.lerp(p2, t))
    dense.append(P[-1])
    cum = [0.0]
    for a, b in zip(dense, dense[1:]): cum.append(cum[-1] + (b - a).length)
    L = cum[-1]; m = max(1, int(round(L / step))); out = []; j = 0
    for i in range(m + 1):
        s = L * i / m
        while j < len(cum) - 2 and cum[j + 1] < s: j += 1
        seg = max(cum[j + 1] - cum[j], 1e-6); t = (s - cum[j]) / seg
        p = dense[j].lerp(dense[j + 1], min(1.0, max(0.0, t)))
        tg = (dense[j + 1] - dense[j]).normalized()
        out.append((p, tg, s))
    return out


_clear = []   # keep-out strips (paths, walls, hedges): (x0, y0, x1, y1, [(a, b, half width)])


def _keep_clear(samples, hw):
    if not samples: return
    pts = [p for p, _, _ in samples][::4] + [samples[-1][0]]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]
    _clear.append((min(xs) - hw, min(ys) - hw, max(xs) + hw, max(ys) + hw, [(a, b, hw) for a, b in zip(pts, pts[1:])]))


def _cleared(x, y):
    for x0, y0, x1, y1, segs in _clear:
        if x0 <= x <= x1 and y0 <= y <= y1:
            q = Vector((x, y))
            for a, b, hw in segs:
                ab = b - a; t = max(0.0, min(1.0, (q - a).dot(ab) / max(ab.length_squared, 1e-9)))
                if (q - a - ab * t).length < hw: return True
    return False


def _in_gap(p, gaps):
    return any(math.hypot(p.x - g[0], p.y - g[1]) < g[2] / 2 for g in gaps)


def _rdir(r, up=0.0):
    z = max(-1.0, min(1.0, r.uniform(-1, 1) + up)); a = r.uniform(0, 6.2832); s = math.sqrt(max(0.0, 1 - z * z))
    return Vector((s * math.cos(a), s * math.sin(a), z))


def _lump(B, m, c, rad, squash=(1, 1, 1), seed=0, sub=1, rough=0.42, yaw=0.0, tilt=0.0):
    """A crumpled leaf lump: an icosphere pushed about by noise, flatter underneath."""
    bm = B.bm(m); vs = bmesh.ops.create_icosphere(bm, subdivisions=sub + 1, radius=1.0)["verts"]   # sub 1: 80 tris
    o = Vector((seed * 1.31 + 0.5, seed * 0.77 + 1.5, seed * 2.03 + 2.5))
    R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(tilt, 3, 'Y')
    for v in vs:
        n = v.co.normalized()
        d = 1 + rough * noise.noise(n * 1.6 + o) + rough * 0.6 * noise.noise(n * 3.7 + o * 1.7)
        if n.z < 0: d *= 1 + n.z * 0.3
        v.co = R @ Vector((n.x * squash[0], n.y * squash[1], n.z * squash[2])) * rad * max(0.35, d) + Vector(c)
    bmesh.ops.transform(bm, matrix=B.M, verts=vs)
    for f in {f for v in vs for f in v.link_faces}: f.smooth = True


def _card_twin(m):
    """A card (gradient-shaded, not baked) twin of a foliage material, for leaf sprays too small to bake."""
    nm = m.name[2:] + " sprays"
    if nm not in _mats:
        base = m.get("base", [0.05, 0.08, 0.03])
        c = mat(nm, tuple(min(1.0, (x * 1.15) ** (1 / 2.2)) for x in base), kind="foliage")
        c["card"] = True
    return _mats[nm]


def _spray(B, m, p, nrm, size, r):
    """A small leaf spray: a bent, irregular card roughly facing nrm (breaks the outline of a leaf mass). Shaded
    by roomgen from a gradient: brighter when it faces the sky and sits high, darker underneath."""
    n = (nrm + Vector((r.uniform(-0.7, 0.7), r.uniform(-0.7, 0.7), r.uniform(-0.1, 0.9)))).normalized()
    t = Matrix.Rotation(r.uniform(0, 6.28), 3, n) @ n.orthogonal().normalized(); b = n.cross(t)
    L = size; W = size * r.uniform(0.45, 0.75)
    cm = _card_twin(m)
    f = B.poly(cm, [p - t * L * 0.5 - n * L * 0.1, p + b * W * 0.5 + t * L * r.uniform(-0.15, 0.15),
                    p + t * L * 0.5 + n * L * r.uniform(0.05, 0.3), p - b * W * 0.5 + t * L * r.uniform(-0.15, 0.15)])
    bm = B.bm(cm); uv = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    v = max(0.05, min(0.95, 0.42 + 0.35 * nrm.z + r.uniform(-0.12, 0.12)))
    for l in f.loops: l[uv].uv = (0.5, v)


def _leaves(B, m, centre, rad, squash, r, clumps, sprays, sub=1, seed=0, spray_size=None):
    """A leaf mass: `clumps` crumpled lumps packed into an ellipsoid, with leaf sprays on their outer sides."""
    centre = Vector(centre)
    for i in range(clumps):
        d = _rdir(r, 0.25); t = 0.0 if i == 0 else r.uniform(0.3, 0.75)
        c = centre + Vector((d.x * squash[0], d.y * squash[1], d.z * squash[2])) * rad * t
        rr = rad * r.uniform(0.46, 0.64) * (1.15 - 0.4 * t)
        _lump(B, m, c, rr, (1.0, 1.0, 0.82), seed * 37 + i, sub)
        out = (c - centre); out = out.normalized() if out.length > 1e-4 else Vector((0, 0, 1))
        for k in range(sprays // max(1, clumps)):
            dd = (out * 0.9 + _rdir(r, 0.3)).normalized()
            p = c + Vector((dd.x, dd.y, dd.z * 0.82)) * rr * r.uniform(0.9, 1.25)
            _spray(B, m, p, dd, spray_size or min(0.55, max(0.14, rr * r.uniform(0.35, 0.6))), r)


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
    if kind == "brick":
        # courses and mortar on walls: brick coordinates from (along the wall, height)
        sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sp.inputs["Vector"])
        ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'ADD'; nt.links.new(sp.outputs["X"], ad.inputs[0]); nt.links.new(sp.outputs["Y"], ad.inputs[1])
        cb = nt.nodes.new("ShaderNodeCombineXYZ"); nt.links.new(ad.outputs[0], cb.inputs["X"]); nt.links.new(sp.outputs["Z"], cb.inputs["Y"])
        bt = nt.nodes.new("ShaderNodeTexBrick"); nt.links.new(cb.outputs["Vector"], bt.inputs["Vector"])
        bt.inputs["Scale"].default_value = 1.0; bt.inputs["Mortar Size"].default_value = 0.01
        bt.inputs["Brick Width"].default_value = 0.225; bt.inputs["Row Height"].default_value = 0.075
        nt.links.new(ramp_out, bt.inputs["Color1"])
        mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs["Factor"].default_value = 1.0
        nt.links.new(ramp_out, mul.inputs["A"]); mul.inputs["B"].default_value = (0.82, 0.8, 0.78, 1)
        nt.links.new(mul.outputs["Result"], bt.inputs["Color2"])
        bt.inputs["Mortar"].default_value = (min(1, c[0] * 1.6 + 0.12), min(1, c[1] * 1.6 + 0.12), min(1, c[2] * 1.6 + 0.12), 1)
        ramp_out = bt.outputs["Color"]
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
    if kind == "foliage":
        vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 11.0
        nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
        vr = nt.nodes.new("ShaderNodeMapRange"); vr.inputs["From Min"].default_value = 0.05; vr.inputs["From Max"].default_value = 0.45
        vr.inputs["To Min"].default_value = 1.15; vr.inputs["To Max"].default_value = 0.55
        nt.links.new(vo.outputs["Distance"], vr.inputs["Value"])
        vm = nt.nodes.new("ShaderNodeMix"); vm.data_type = 'RGBA'; vm.blend_type = 'MULTIPLY'; vm.inputs["Factor"].default_value = 1.0
        cmb = nt.nodes.new("ShaderNodeCombineXYZ")
        for k_ in ("X", "Y", "Z"): nt.links.new(vr.outputs["Result"], cmb.inputs[k_])
        src = b.inputs["Base Color"].links[0].from_socket
        nt.links.new(src, vm.inputs["A"]); nt.links.new(cmb.outputs["Vector"], vm.inputs["B"])
        nt.links.new(vm.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = max(0.02, r0 - rv); rr.inputs["To Max"].default_value = min(1.0, r0 + rv)
    nt.links.new(n2.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = metal
    if bump > 0:
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump * 0.5; bp.inputs["Distance"].default_value = 0.02
        nt.links.new(n2.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
        if kind == "foliage":
            bp.inputs["Strength"].default_value = 0.7; bp.inputs["Distance"].default_value = 0.05
            nt.links.new(vo.outputs["Distance"], bp.inputs["Height"])
    if emission > 0:
        b.inputs["Emission Color"].default_value = lin(emission_color or color) + (1,)
        b.inputs["Emission Strength"].default_value = emission
    if kind == "glass":
        b.inputs["Transmission Weight"].default_value = 0.9
    m["base"] = list(lin(color))
    _mats[name] = m
    return m


def M(name):
    """The material made earlier under this name."""
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


def tree(name, loc, height, bark, leaves, kind="broadleaf", seed=0, lean=6.0, detail=1):
    """A tree grounded at loc: a flared, bending trunk with limbs and twigs; broadleaf crowns are several leaf
    lobes (crumpled lumps edged with leaf sprays) with gaps showing the limbs; conifer = drooping tiers; palm =
    fan crown; dead = bare branches. detail: 0 distant (>35 m, ~1.2k tris), 1 (~3k), 2 hero tree near the reader
    (~6k). Returns its objects (one per material)."""
    r = random.Random(seed); x, y = loc[0], loc[1]; z = ground(x, y)
    B = _B(name, (x, y, z), r.uniform(0, 360)); detail = max(0, min(2, int(detail)))
    la = math.radians(r.uniform(0, lean)); h = height
    lv = Vector((math.sin(la), 0, 0))   # lean, in the tree's own (randomly turned) frame
    tr = h * (0.028 if kind != "palm" else 0.018)
    if kind == "palm":
        top = Vector((lv.x * h * 0.9, 0, h * 0.95))
        B.tube(bark, [(0, 0, -0.3), (lv.x * h * 0.2, 0, h * 0.3), top * 0.7, top], [tr * 1.6, tr * 1.1, tr * 0.9, tr * 0.7], 7)
        for i in range(7 + 2 * detail):
            a = i * 6.28 / (7 + 2 * detail) + r.uniform(-0.2, 0.2); L = h * r.uniform(0.28, 0.36)
            d = Vector((math.cos(a), math.sin(a), 0)); side = Vector((-d.y, d.x, 0))
            pts = [top + d * L * t + Vector((0, 0, L * (0.25 * t - 0.75 * t * t))) for t in (0, 0.25, 0.5, 0.75, 1.0)]
            for p0, p1, t in zip(pts, pts[1:], (0, 0.25, 0.5, 0.75)):
                w0, w1 = L * 0.16 * (1 - t * 0.7), L * 0.16 * (1 - (t + 0.25) * 0.7)
                B.poly(leaves, [p0 - side * w0 - Vector((0, 0, w0 * 0.3)), p1 - side * w1 - Vector((0, 0, w1 * 0.3)), p1, p0])
                B.poly(leaves, [p0, p1, p1 + side * w1 - Vector((0, 0, w1 * 0.3)), p0 + side * w0 - Vector((0, 0, w0 * 0.3))])
        return B.done()
    if kind == "conifer":
        top = Vector((lv.x * h, 0, h))
        B.tube(bark, [(0, 0, -0.3), (0, 0, 0.3), top * 0.5, top], [tr * 1.7, tr * 1.2, tr * 0.7, 0.02], 7)
        tiers = (6, 8, 10)[detail]; arms = (4, 5, 7)[detail]
        for i in range(tiers):
            t = 0.2 + 0.78 * i / tiers; R = h * 0.2 * (1 - t) + 0.3; c0 = Vector((lv.x * h * t, 0, h * t))
            for j in range(arms):
                a = 6.2832 * j / arms + i * 1.3 + r.uniform(-0.3, 0.3); d = Vector((math.cos(a), math.sin(a), 0))
                c = c0 + d * R * 0.62 - Vector((0, 0, R * 0.18))
                if detail: B.seg(bark, c0, c - d * R * 0.2, tr * 0.25, 0.01, 4)
                _lump(B, leaves, c, R * r.uniform(0.52, 0.64), (1.0, 0.72, 0.5), seed * 53 + i * 9 + j, 1, 0.55, a, math.radians(r.uniform(14, 30)))
                for k in range(detail * 2):
                    p = c + d * R * r.uniform(0.3, 0.6) + Vector((0, 0, r.uniform(-0.1, 0.15)))
                    _spray(B, leaves, p, d + Vector((0, 0, 0.6)), min(0.6, R * 0.35), r)
        _lump(B, leaves, top - Vector((0, 0, 0.25)), 0.35, (0.6, 0.6, 1.4), seed, 1)
        return B.done()
    # broadleaf and dead: a trunk forking into limbs that reach for leaf lobes
    fork = h * r.uniform(0.24, 0.34)
    fk = Vector((lv.x * fork, 0, fork))
    wob = lambda k: Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)) * tr * k
    B.tube(bark, [(0, 0, -0.4), (0, 0, 0.12), Vector((0, 0, 0.35)) + wob(0.3), fk * 0.6 + wob(0.8), fk],
           [tr * 1.9, tr * 1.55, tr * 1.12, tr, tr * 0.85], (6, 8, 9)[detail])
    for k in range(3 + detail * 2):   # root flare: buttresses running into the ground
        a = 6.2832 * k / (3 + detail * 2) + r.uniform(-0.3, 0.3); d = Vector((math.cos(a), math.sin(a), 0))
        B.tube(bark, [d * tr * 0.6 + Vector((0, 0, 0.5)), d * tr * 1.8 + Vector((0, 0, 0.05)), d * tr * 3.2 - Vector((0, 0, 0.12))], [tr * 0.45, tr * 0.38, tr * 0.12], 5)
    cc = Vector((lv.x * h * 0.62, 0, h * 0.6)); R = h * r.uniform(0.3, 0.38); Rz = h * r.uniform(0.27, 0.32)
    K = (4, 6, 8)[detail] if kind != "dead" else r.randint(4, 6)
    per = (4, 3, 4)[detail]; spr = (2, 12, 16)[detail]
    for i in range(K):
        a = 6.2832 * i / K + r.uniform(-0.45, 0.45); e = r.uniform(-0.55, 0.75) if i % 2 else r.uniform(-0.2, 0.3)
        c = cc + Vector((math.cos(a) * math.cos(e) * R * 0.66, math.sin(a) * math.cos(e) * R * 0.66, math.sin(e) * Rz * 0.62))
        if i == K - 1: c = cc + Vector((r.uniform(-0.2, 0.2) * R, r.uniform(-0.2, 0.2) * R, Rz * 0.62))
        start = fk + Vector((0, 0, r.uniform(-0.05, 0.25) * h * 0.2))
        mid = start.lerp(c, 0.5) + Vector((r.uniform(-1, 1) * 0.06 * h, r.uniform(-1, 1) * 0.06 * h, h * 0.03))
        end = start.lerp(c, 0.95)
        B.tube(bark, [start, mid, end], [tr * 0.62, tr * 0.4, tr * 0.16], (4, 5, 6)[detail])
        lr = R * r.uniform(0.5, 0.64)
        for j in range(1 + detail):
            q = mid.lerp(end, r.uniform(0.2, 0.8)); tip = c + _rdir(r, 0.2) * lr * (0.9 if kind == "dead" else 0.65)
            B.tube(bark, [q, q.lerp(tip, 0.5) + Vector((0, 0, 0.1 * lr)), tip], [tr * 0.2, tr * 0.12, tr * 0.04], 4)
        if kind != "dead":
            _leaves(B, leaves, c, lr, (1.0, 1.0, 0.78), r, per + (1 if i == K - 1 else 0), per * spr, 1 if detail else 0, seed * 13 + i)
    return B.done()


def shrub(name, loc, size, leaves, seed=0, detail=1, stems=None):
    """A shrub or bush (size: its radius, m) sitting on the ground: crumpled leaf lumps with leaf sprays, flat
    beneath, never a smooth ball. stems: an optional bark material for a few stems showing at the base."""
    r = random.Random(seed); x, y = loc[0], loc[1]; z = ground(x, y)
    B = _B(name, (x, y, z), r.uniform(0, 360))
    n = (3, 5, 7)[max(0, min(2, int(detail)))]
    _leaves(B, leaves, (0, 0, size * 0.55), size * 0.85, (1.2, 1.05, 0.7), r, n, n * (3, 6, 9)[max(0, min(2, int(detail)))], 1, seed)
    if stems is not None:
        for k in range(4):
            a = r.uniform(0, 6.28); d = Vector((math.cos(a), math.sin(a), 0))
            B.seg(stems, Vector((0, 0, -0.1)) + d * 0.05, d * size * 0.4 + Vector((0, 0, size * 0.6)), 0.025, 0.008, 4)
    return B.done()


def hedge(name, points, leaves, height=1.8, width=1.3, seed=0, gaps=(), near=(0.0, 0.0), stems=None, detail=1):
    """A hedgerow along a line of (x, y) points (smoothed into a curve), following the ground: an irregular,
    overgrown leaf mass with an uneven top, lumps and leaf sprays, thinning at the foot. gaps: [(x, y, width)]
    left open (for a gate or stile). Detail falls off with distance from `near` (the reader). stems: an optional
    bark material for stems showing at its foot. About 110 tris/m within 18 m of near, 45 beyond, 15 at detail 0. Keeps groundcover off it."""
    r = random.Random(seed); B = _B(name)
    smp = _spline(points, (1.0, 0.6, 0.45)[max(0, min(2, int(detail)))])
    _keep_clear(smp, width * 0.55)
    o = Vector((seed * 3.1, seed * 1.7, 4.0)); nprof = 9 if detail else 7
    run = []
    def flush():
        if len(run) < 2: run.clear(); return
        bm = B.bm(leaves); rings = []
        for p, tg, s, hgt, wid in run:
            nrm = Vector((-tg.y, tg.x)); ring = []
            for k in range(nprof):
                th = math.pi * k / (nprof - 1)   # 0 at one foot, pi at the other, over the top
                cx, cz = math.cos(th), math.sin(th)
                rr = 1 + 0.4 * noise.noise(Vector((p.x * 0.7, p.y * 0.7, th * 1.1)) + o) + 0.25 * noise.noise(Vector((p.x * 2.2, p.y * 2.2, th * 2.6)) + o)
                foot = 0.72 + 0.28 * min(1.0, cz * 3)   # narrower at the base
                lx = cx * wid * 0.5 * rr * foot; lz = cz * hgt * (0.78 + 0.22 * rr) - 0.12
                zg = ground(p.x + nrm.x * lx, p.y + nrm.y * lx)
                ring.append(bm.verts.new(B.M @ Vector((p.x + nrm.x * lx, p.y + nrm.y * lx, zg + max(-0.15, lz)))))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for k in range(nprof - 1):
                f = bm.faces.new((a[k], a[k + 1], b[k + 1], b[k])); f.smooth = True
        # end caps so a gap shows a rounded end rather than a hole
        for ring, sgn in ((rings[0], 1), (rings[-1], -1)):
            c = sum((v.co for v in ring), Vector()) / len(ring)
            cv = bm.verts.new(c + Vector((run[0][1].x, run[0][1].y, 0)) * (-0.25 if sgn > 0 else 0.25))
            for k in range(nprof - 1):
                bm.faces.new((ring[k + 1], ring[k], cv) if sgn > 0 else (ring[k], ring[k + 1], cv))
        run.clear()
    lumps = []
    for p, tg, s in smp:
        if _in_gap(p, gaps): flush(); continue
        hgt = height * (0.85 + 0.3 * noise.noise(Vector((s * 0.12, seed, 1.0)))); wid = width * (0.85 + 0.3 * noise.noise(Vector((s * 0.2, seed, 2.0))))
        run.append((p, tg, s, hgt, wid)); lumps.append((p, tg, hgt, wid))
    flush()
    nx, ny = near
    for i, (p, tg, hgt, wid) in enumerate(lumps):
        d = math.hypot(p.x - nx, p.y - ny); k = 1.0 if d < 18 else (0.35 if d < 40 else 0.1)
        if detail == 0: k *= 0.4
        nrm = Vector((-tg.y, tg.x, 0)); zg = ground(p.x, p.y)
        for j in range(int(0.6 * k + r.random() * 0.5)):   # an occasional bulge proud of the clipped line
            side = r.choice((-1, 1)); th = r.uniform(0.0, 1.0) * math.pi / 2
            th = math.pi / 2 * (1 - r.random() ** 1.6)   # more of them on the top
            c = Vector((p.x, p.y, zg)) + nrm * side * math.cos(th) * wid * 0.3 + Vector((tg.x, tg.y, 0)) * r.uniform(-0.25, 0.25) + Vector((0, 0, max(0.3, math.sin(th) * hgt * 0.74)))
            _lump(B, leaves, c, r.uniform(0.32, 0.5) * (1.0 if k == 1.0 else 1.4), (1.3, 1.3, 0.75), seed * 7 + i * 5 + j, 0, 0.5)
        for j in range(int(16 * k + r.random() + (6 if detail == 2 else 0))):   # leaf sprays all over the surface
            side = r.choice((-1, 1)); th = (1 - r.random() ** 1.5) * math.pi / 2
            q = Vector((p.x, p.y, zg)) + nrm * side * math.cos(th) * wid * 0.55 + Vector((tg.x, tg.y, 0)) * r.uniform(-0.2, 0.2) + Vector((0, 0, math.sin(th) * hgt * 1.0))
            _spray(B, leaves, q, nrm * side * math.cos(th) + Vector((0, 0, math.sin(th))), r.uniform(0.14, 0.26), r)
        if stems is not None and k == 1.0 and r.random() < 0.35:
            side = r.choice((-1, 1)); q = Vector((p.x, p.y, zg - 0.05)) + nrm * side * wid * 0.3
            B.seg(stems, q, q + nrm * side * 0.08 + Vector((0, 0, 0.5)), 0.03, 0.015, 4)
    return B.done()


def _limb(name, p0, p1, r0, r1, material, sides=7):
    d = p1 - p0
    o = cylinder(name, r0, d.length, (0, 0, 0), material, sides=sides, top_radius=r1)
    o.location = p0; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    return o


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
        if _clear and _cleared(x, y): continue
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
        if _clear and _cleared(x, y): continue
        out.append((x, y))
    return out


# ---------------------------------------------------------------- field boundaries, paths

def wall(name, points, material, height=1.2, kind="drystone", thickness=0.55, seed=0, gaps=(), near=(0.0, 0.0),
         coping=None):
    """A field or garden wall along (x, y) points, following the ground. kind "drystone": coursed rough stones
    (each its own block, battered inward) with upright coping stones; "brick": a brick wall with piers, plinth and
    a coping (give a kind="brick" material). gaps: [(x, y, width)] left open. Stones grow coarser away from
    `near`. coping: optional material for the top. About 170 tris/m near (drystone), 60 far."""
    r = random.Random(seed); B = _B(name); cop = coping or material
    smp = _spline(points, 0.25); _keep_clear(smp, thickness * 0.7)
    if kind == "brick":
        runs, cur = [], []
        for p, tg, s in smp:
            if _in_gap(p, gaps): (runs.append(cur) if cur else None); cur = []; continue
            cur.append((p, tg, s))
        if cur: runs.append(cur)
        for run in runs:
            step = max(1, int(2.0 / 0.25)); idx = list(range(0, len(run), step))
            if idx[-1] != len(run) - 1: idx.append(len(run) - 1)
            for i0, i1 in zip(idx, idx[1:]):
                a, b = run[i0][0], run[i1][0]; m = (a + b) / 2; d = b - a; yaw = math.degrees(math.atan2(d.y, d.x))
                zg = min(ground(a.x, a.y), ground(b.x, b.y)) - 0.25
                top = max(ground(a.x, a.y), ground(b.x, b.y)) + height
                B.box(material, (d.length + 0.02, thickness * 0.42, top - zg), (m.x, m.y, zg), (0, 0, yaw))
                B.box(cop, (d.length + 0.02, thickness * 0.42 + 0.08, 0.08), (m.x, m.y, top), (0, 0, yaw), bevel=0.012)
                B.box(material, (d.length + 0.02, thickness * 0.42 + 0.06, 0.4), (m.x, m.y, zg), (0, 0, yaw))
            for i in idx:
                p, tg, _ = run[i]; yaw = math.degrees(math.atan2(tg.y, tg.x)); zg = ground(p.x, p.y)
                B.box(material, (0.45, thickness * 0.42 + 0.2, height + 0.25 + 0.15), (p.x, p.y, zg - 0.25), (0, 0, yaw))
                B.box(cop, (0.55, thickness * 0.42 + 0.3, 0.1), (p.x, p.y, zg + height + 0.15), (0, 0, yaw), bevel=0.02)
        return B.done()
    nx, ny = near; s_end = smp[-1][2] if smp else 0
    pts = smp
    # lay courses: walk along the line laying stones of varied length, coarser with distance
    def at_s(sv):
        for (p, tg, s0), (q, _, s1) in zip(pts, pts[1:]):
            if s0 <= sv <= s1: t = (sv - s0) / max(s1 - s0, 1e-6); return p.lerp(q, t), tg
        return pts[-1][0], pts[-1][1]
    body = height - 0.28
    sv = 0.0
    while sv < s_end:
        p, tg = at_s(sv); dist = math.hypot(p.x - nx, p.y - ny)
        coarse = 1.0 if dist < 15 else (1.7 if dist < 40 else 2.6)
        L = r.uniform(0.32, 0.55) * coarse
        if _in_gap(p, gaps): sv += 0.25; continue
        q, _ = at_s(min(s_end, sv + L)); mid = (p + q) / 2; d = q - p
        if d.length < 0.05: break
        yaw = math.degrees(math.atan2(d.y, d.x)); zg = ground(mid.x, mid.y) - 0.12
        zc = zg; ch = r.uniform(0.15, 0.22) * coarse * 0.8
        k = 0
        while zc < zg + body + 0.12 - ch * 0.5:
            hh = min(ch * r.uniform(0.75, 1.25), zg + body + 0.12 - zc)
            f = (zc - zg) / max(body, 0.1); th = thickness * (1 - 0.32 * f)   # battered: thinner toward the top
            off = (r.uniform(-0.07, 0.07) if k % 2 else 0) * L
            ll = L * r.uniform(0.85, 1.05)
            c = mid + d.normalized() * off
            B.box(material, (ll, th * r.uniform(0.94, 1.06), hh * 0.97), (c.x, c.y, zc), (r.uniform(-2.5, 2.5), r.uniform(-3, 3), yaw + r.uniform(-3, 3)))
            zc += hh; k += 1
        # coping: stones set on edge across the top
        cs = 0.0
        while cs < L:
            w = r.uniform(0.09, 0.15) * coarse * (1 if coarse == 1.0 else 1.5); cp = p.lerp(q, min(1.0, (cs + w / 2) / L))
            B.box(cop, (w * 0.85, thickness * 0.62 * r.uniform(0.9, 1.1), r.uniform(0.22, 0.32)), (cp.x, cp.y, zc - 0.02), (r.uniform(-4, 4), r.uniform(-12, 12), yaw))
            cs += w
        sv += L
    return B.done()


def fence(name, points, material, height=1.15, kind="rail", spacing=2.4, seed=0, gaps=()):
    """A wooden fence along (x, y) points, following the ground: kind "rail" (split posts and three weathered
    rails, slightly out of true) or "paling" (close upright pales on two rails). gaps: [(x, y, width)]."""
    r = random.Random(seed); B = _B(name)
    smp = _spline(points, spacing, smooth=True); _keep_clear(smp, 0.2)
    posts = []
    for p, tg, s in smp:
        if _in_gap(p, gaps): posts.append(None); continue
        zg = ground(p.x, p.y); yaw = math.degrees(math.atan2(tg.y, tg.x))
        lean = (r.uniform(-3, 3), r.uniform(-3, 3))
        B.box(material, (0.13, 0.11, height + 0.45), (p.x, p.y, zg - 0.45), (lean[0], lean[1], yaw + r.uniform(-8, 8)), bevel=0.015)
        posts.append((p, zg))
    rails = (0.35, 0.68, 1.0) if kind == "rail" else (0.3, height - 0.2)
    for a, b in zip(posts, posts[1:]):
        if a is None or b is None: continue
        (p, za), (q, zb) = a, b; d = q - p; yaw = math.degrees(math.atan2(d.y, d.x)); m = (p + q) / 2
        pitch = -math.degrees(math.atan2(zb - za, d.length))
        for k, hz in enumerate(rails):
            hz = hz * height / 1.15 if kind == "rail" else hz
            sag = r.uniform(-0.04, 0.02)
            B.box(material, (d.length + 0.12, 0.05, r.uniform(0.08, 0.11)), (m.x + r.uniform(-0.02, 0.02), m.y, (za + zb) / 2 + hz + sag),
                  (r.uniform(-3, 3), pitch + r.uniform(-1.5, 1.5), yaw), bevel=0.01)
        if kind == "paling":
            n = int(d.length / 0.13)
            for i in range(n):
                t = (i + 0.5) / n; c = p.lerp(q, t); zg = ground(c.x, c.y); off = Vector((-d.y, d.x)).normalized() * 0.05
                B.box(material, (0.09, 0.025, height * r.uniform(0.95, 1.03) + 0.05), (c.x + off.x, c.y + off.y, zg - 0.05), (r.uniform(-1.5, 1.5), 0, yaw))
    return B.done()


def stile(name, loc, material, rot=0, kind="step"):
    """A wooden stile across a field boundary at loc (x, y); rot = the boundary's direction in degrees. kind
    "step": two posts, a top rail and a worn step plank on both sides; "ladder": an A-frame of steps over a wall."""
    x, y = loc[0], loc[1]; z = ground(x, y); r = random.Random(int(x * 7 + y * 13)); B = _B(name, (x, y, z), rot)
    if kind == "ladder":
        for sx in (-0.35, 0.35):
            for sy in (-1, 1):
                B.box(material, (0.08, 0.08, 1.75), (sx, sy * 0.55, -0.1), (sy * 28, 0, 0), bevel=0.01)
        for i in range(4):
            for sy in (-1, 1):
                B.box(material, (0.78, 0.2, 0.04), (0, sy * (0.55 - i * 0.14 - 0.06), 0.3 + i * 0.32), (0, 0, 0), bevel=0.008)
        B.box(material, (0.8, 0.32, 0.05), (0, 0, 1.45), bevel=0.01)
        return B.done()
    for sx in (-0.5, 0.5):
        B.box(material, (0.13, 0.13, 1.6), (sx, 0, -0.4), (r.uniform(-3, 3), r.uniform(-3, 3), r.uniform(-6, 6)), bevel=0.015)
    B.box(material, (1.25, 0.07, 0.11), (0, 0, 1.0), (r.uniform(-2, 2), 0, 0), bevel=0.01)
    B.box(material, (1.15, 0.06, 0.09), (0, 0.0, 0.62), (0, 0, 0), bevel=0.01)
    for sy in (-1, 1):   # step planks on stub posts, both sides, one end dipped with wear
        for sx in (-0.38, 0.38):
            B.box(material, (0.1, 0.1, 0.75), (sx, sy * 0.28, -0.35), (0, 0, r.uniform(-5, 5)), bevel=0.01)
        B.box(material, (1.0, 0.24, 0.055), (0, sy * 0.28, 0.38), (r.uniform(-3, 3), 0, r.uniform(-3, 3)), bevel=0.012)
    return B.done()


def gate(name, loc, material, rot=0, width=3.0, open_deg=0.0, iron=None):
    """A five-bar field gate centred at loc (x, y) across an opening of `width`, rot = the boundary's direction:
    hanging and shutting posts, heel and head stiles, five bars with a diagonal brace; open_deg swings it open
    about its hinge. iron: optional material for hinges and latch."""
    x, y = loc[0], loc[1]; z = ground(x, y); B = _B(name, (x, y, z), rot)
    hw = width / 2
    for sx in (-hw - 0.12, hw + 0.12):
        B.box(material, (0.2, 0.2, 2.0), (sx, 0, -0.6), bevel=0.02)
        B.box(material, (0.24, 0.24, 0.06), (sx, 0, 1.4), bevel=0.02)
    L = width - 0.06
    G = _B(name + ".leaf", tuple(B.at(-hw, 0, 0)), rot - open_deg)
    G.box(material, (0.1, 0.07, 1.22), (0.05, 0, 0.12), bevel=0.01)          # heel
    G.box(material, (0.08, 0.06, 1.15), (L - 0.04, 0, 0.14), bevel=0.01)     # head
    for k, hz in enumerate((0.18, 0.4, 0.62, 0.86, 1.18)):
        G.box(material, (L - 0.04, 0.05 if k < 4 else 0.08, 0.09 if k < 4 else 0.11), (L / 2, 0, hz), bevel=0.008)
    dl = math.hypot(L * 0.62, 1.0); ang = math.degrees(math.atan2(1.0, L * 0.62))
    G.box(material, (dl, 0.04, 0.08), (0.06 + L * 0.31, 0.05, 0.2 + 0.5 - 0.04), (0, -ang, 0), bevel=0.008)
    if iron is not None:
        for hz in (0.35, 1.15):
            G.box(iron, (0.5, 0.075, 0.035), (0.25, 0, hz))
        G.box(iron, (0.16, 0.08, 0.04), (L, 0, 1.05))
    return B.done() + G.done()


def footpath(name, points, material, width=1.0, ruts=False, puddles=None, seed=0, wear=0.3):
    """A trodden footpath or cart track along (x, y) points (smoothed into a curve), lying on the ground with
    ragged worn edges where the grass meets it (wear: edge raggedness 0-1). ruts: two wheel ruts and a grassy
    crown, for a lane. puddles: a water material for rain puddles in the low spots. Keeps groundcover off it."""
    r = random.Random(seed); B = _B(name)
    smp = _spline(points, 0.45 if width < 2 else 0.6); _keep_clear(smp, width * 0.5)
    o = Vector((seed * 2.3, seed * 1.1, 7.0))
    prof = ([-1.0, -0.8, -0.55, -0.3, 0.0, 0.3, 0.55, 0.8, 1.0] if ruts else [-1.0, -0.7, -0.3, 0.0, 0.3, 0.7, 1.0])
    bm = B.bm(material); rings = []
    for p, tg, s in smp:
        nrm = Vector((-tg.y, tg.x)); ring = []
        hw = width * 0.5 * (1 + wear * 0.6 * noise.noise(Vector((p.x * 0.35, p.y * 0.35, 0)) + o))
        for u in prof:
            e = abs(u)
            ragged = hw * (1 + wear * 0.45 * noise.noise(Vector((p.x * 2.1, p.y * 2.1, u * 3)) + o)) if e == 1.0 else hw
            q = p + nrm * u * ragged
            dz = 0.03
            if e == 1.0: dz = -0.04          # edges sink under the grass: a ragged, worn border
            elif e >= 0.75: dz = 0.02
            if ruts and abs(e - 0.55) < 0.01: dz = -0.005   # wheel ruts
            if ruts and e == 0.0: dz = 0.05
            dz += 0.012 * noise.noise(Vector((q.x * 1.7, q.y * 1.7, 3.0)) + o)
            ring.append(bm.verts.new((q.x, q.y, ground(q.x, q.y) + dz)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(len(prof) - 1):
            f = bm.faces.new((a[k], b[k], b[k + 1], a[k + 1])); f.smooth = True
    if puddles is not None:
        pb = B.bm(puddles)
        for i in range(0, len(smp), 1):
            if r.random() > (0.22 if ruts else 0.12): continue
            p, tg, s = smp[i]; nrm = Vector((-tg.y, tg.x))
            u = r.choice((-0.55, 0.55)) if ruts else r.uniform(-0.3, 0.3)
            c = p + nrm * u * width * 0.5; L = r.uniform(0.3, 1.1) * (1.0 if ruts else 0.8); W = min(width * (0.22 if ruts else 0.6), L * r.uniform(0.4, 0.8))
            zc = ground(c.x, c.y) + 0.035
            vs = []
            for k in range(10):
                a = 6.2832 * k / 10; rr = 1 + 0.3 * noise.noise(Vector((math.cos(a) * 2 + i, math.sin(a) * 2, s)))
                q = c + (tg * math.cos(a) * L * 0.5 + nrm * math.sin(a) * W * 0.5) * rr
                vs.append(pb.verts.new((q.x, q.y, zc)))
            pb.faces.new(vs)
    return B.done()


# ---------------------------------------------------------------- buildings and rooms

def room(name, width, depth, height, walls, floor, ceiling=None, openings=(), thickness=0.18, centre=(0.0, 0.0)):
    """A rectangular room with real openings; returns its name (pass it to panelling, windows, doors). Walls are named n, s, e, w (+y, -y, +x, -x). openings: dicts
    {"wall": "s", "at": 0.0 (offset along the wall from its middle, m), "width": 1.0, "height": 2.1, "sill": 0.0}
    for doors (sill 0) and windows. ceiling None leaves it open to the sky. Registers the floor as ground."""
    cx, cy = centre; hw, hd = width / 2, depth / 2
    _rooms[name] = dict(cx=cx, cy=cy, w=width, d=depth, h=height, t=thickness, openings=[dict(o) for o in openings])
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
    return name

def _wall(R, wn, along, off, z=0.0):
    """World point and yaw (local +y into the wall) for a room wall: along = offset as in room() openings,
    off = distance out from the wall face into the room."""
    cx, cy, hw, hd = R["cx"], R["cy"], R["w"] / 2, R["d"] / 2
    if wn == "n": return (cx + along, cy + hd - off, z), 0
    if wn == "s": return (cx + along, cy - hd + off, z), 180
    if wn == "e": return (cx + hw - off, cy + along, z), -90
    return (cx - hw + off, cy + along, z), 90


def _room(room):
    if room in _rooms: return _rooms[room]
    if room is None and len(_rooms) == 1: return next(iter(_rooms.values()))
    raise ValueError(f"no room named {room!r}: pass the name given to kit.room (it also returns it)")


def _wlen(R, wn): return R["w"] if wn in ("n", "s") else R["d"]


def _spans(R, wn, z0, z1, avoid=()):
    """Free stretches [(a, b)] of a wall between z0 and z1, skipping its openings and `avoid` [(wall, at, width)]."""
    L = _wlen(R, wn); cuts = []
    for o in R["openings"]:
        if o["wall"] != wn: continue
        sill = o.get("sill", 0.0); top = sill + o["height"]
        if sill < z1 and top > z0: cuts.append((o.get("at", 0) - o["width"] / 2 - 0.12, o.get("at", 0) + o["width"] / 2 + 0.12))
    for a in avoid:
        if a[0] == wn: cuts.append((a[1] - a[2] / 2, a[1] + a[2] / 2))
    out = []; x = -L / 2
    for a, b in sorted(cuts):
        if a - x > 0.05: out.append((x, a))
        x = max(x, b)
    if L / 2 - x > 0.05: out.append((x, L / 2))
    return out


def _wbox(B, R, wn, m, a, b, z, h, proud, off=0.0, bevel=0.0):
    (x, y, _), yaw = _wall(R, wn, (a + b) / 2, off + proud / 2)
    B.box(m, (b - a, proud, h), (x, y, z), (0, 0, yaw), bevel=bevel)


def panelling(room, material, dado=0.9, skirting=0.2, cornice=0.24, panels=True, upper=False, picture_rail=0.0,
              avoid=()):
    """Georgian joinery round every wall of a room made by room(): skirting with a moulded top, a dado rail,
    raised and fielded panels below it (also under windows), a stepped cornice at the ceiling, an optional
    picture rail (height in m) and optional tall moulded panels above the dado (upper=True). Openings are left
    clear; avoid: [(wall, at, width)] stretches to leave plain (a fireplace, a bookcase)."""
    R = _room(room); room = room or next(iter(_rooms)); B = _B(room + ".joinery"); H = R["h"]
    for wn in "nsew":
        for a, b in _spans(R, wn, 0.0, skirting):
            _wbox(B, R, wn, material, a, b, 0.0, skirting, 0.022)
            _wbox(B, R, wn, material, a, b, skirting - 0.03, 0.035, 0.034)
        if dado:
            for a, b in _spans(R, wn, dado - 0.05, dado + 0.05):
                _wbox(B, R, wn, material, a, b, dado - 0.02, 0.05, 0.042, bevel=0.01)
                _wbox(B, R, wn, material, a, b, dado - 0.07, 0.05, 0.024)
        if picture_rail:
            for a, b in _spans(R, wn, picture_rail - 0.03, picture_rail + 0.03):
                _wbox(B, R, wn, material, a, b, picture_rail, 0.04, 0.03, bevel=0.008)
        L = _wlen(R, wn)
        for k, (pr, hh) in enumerate(((0.025, cornice), (0.06, cornice * 0.62), (0.1, cornice * 0.36), (0.13, cornice * 0.14))):
            _wbox(B, R, wn, material, -L / 2, L / 2, H - hh, hh, pr)
        def panel_row(a, b, z0, z1, width_target):
            l = b - a; n = max(1, int(round(l / width_target)))
            pw = l / n
            for i in range(n):
                p0, p1 = a + i * pw + 0.07, a + (i + 1) * pw - 0.07
                if p1 - p0 < 0.12 or z1 - z0 < 0.12: continue
                _wbox(B, R, wn, material, p0 + 0.04, p1 - 0.04, z0 + 0.04, z1 - z0 - 0.08, 0.016)          # raised field
                for (q0, q1, zz, hh) in ((p0, p1, z0, 0.03), (p0, p1, z1 - 0.03, 0.03), (p0, p0 + 0.03, z0, z1 - z0), (p1 - 0.03, p1, z0, z1 - z0)):
                    _wbox(B, R, wn, material, q0, q1, zz, hh, 0.026)                                        # moulding
        if panels and dado:
            for a, b in _spans(R, wn, skirting, dado - 0.08):
                panel_row(a, b, skirting + 0.07, dado - 0.1, 0.85)
            for o in R["openings"]:   # a panel under each window
                sill = o.get("sill", 0.0)
                if o["wall"] == wn and sill > skirting + 0.3:
                    a0 = o.get("at", 0) - o["width"] / 2; b0 = o.get("at", 0) + o["width"] / 2
                    panel_row(a0, b0, skirting + 0.07, min(dado, sill) - 0.12, 1.5)
        if upper and dado:
            for a, b in _spans(R, wn, dado + 0.1, H - cornice - 0.1, avoid):
                panel_row(a, b, dado + 0.18, H - cornice - 0.2, 1.3)
    return B.done()


def windows(room, frame, glass, curtain=None, pelmet=None, panes=(3, 2), drawn=0.55, tiebacks=True):
    """Dress every window opening of a room made by room(): a sash window set in the reveal (frame, meeting rail,
    glazing bars: panes = (across, up) per sash), architrave and window board, and if curtain is given, full-length
    curtains with real folds, gathered to the sides (drawn: 0 shut .. 1 fully drawn back) under a pelmet (material)
    or on a pole. Light from outside still comes in through the glass."""
    R = _room(room); room = room or next(iter(_rooms)); B = _B(room + ".windows"); t = R["t"]; r = random.Random(len(R["openings"]) * 7)
    for o in R["openings"]:
        sill = o.get("sill", 0.0)
        if sill <= 0.01: continue
        wn = o["wall"]; at_ = o.get("at", 0); w = o["width"]; h = o["height"]; top = sill + h
        def wb(m, a, b, z, hh, proud, off, bev=0.0): _wbox(B, R, wn, m, at_ + a, at_ + b, z, hh, proud, off, bev)
        # architrave round the opening and a window board
        for sx in (-1, 1): wb(frame, sx * (w / 2 + 0.06) - 0.06, sx * (w / 2 + 0.06) + 0.06, sill - 0.02, h + 0.14, 0.03, 0.0, 0.006)
        wb(frame, -w / 2 - 0.12, w / 2 + 0.12, top, 0.12, 0.03, 0.0, 0.006)
        wb(frame, -w / 2 - 0.08, w / 2 + 0.08, sill - 0.035, 0.035, t * 0.5 + 0.05, -t * 0.5, 0.006)
        # the sash, set back in the reveal
        so = -t * 0.55
        wb(glass, -w / 2, w / 2, sill, h, 0.012, so - 0.02)
        for a, b, z, hh in ((-w / 2, -w / 2 + 0.06, sill, h), (w / 2 - 0.06, w / 2, sill, h), (-w / 2, w / 2, sill, 0.07), (-w / 2, w / 2, top - 0.06, 0.06),
                            (-w / 2, w / 2, sill + h / 2 - 0.025, 0.05)):
            wb(frame, a, b, z, hh, 0.05, so)
        nx_, ny_ = panes
        for i in range(1, nx_):
            u = -w / 2 + 0.06 + (w - 0.12) * i / nx_; wb(frame, u - 0.012, u + 0.012, sill, h, 0.035, so + 0.005)
        for half in (0, 1):
            z0 = sill + 0.07 + half * (h / 2 - 0.04); hh = h / 2 - 0.07
            for j in range(1, ny_):
                zz = z0 + hh * j / ny_; wb(frame, -w / 2, w / 2, zz - 0.012, 0.024, 0.035, so + 0.005)
        if curtain is None: continue
        ctop = top + 0.25
        if pelmet is not None:
            wb(pelmet, -w / 2 - 0.42, w / 2 + 0.42, ctop - 0.05, 0.32, 0.2, 0.0, 0.025)
        else:
            B.seg(frame, _wall(R, wn, at_ - w / 2 - 0.5, 0.14, ctop)[0], _wall(R, wn, at_ + w / 2 + 0.5, 0.14, ctop)[0], 0.022, 0.022, 8)
            for sx in (-1, 1): B.ball(frame, 0.04, _wall(R, wn, at_ + sx * (w / 2 + 0.52), 0.14, ctop)[0], sub=1)
        for sx in (-1, 1):
            cw = 0.32 + (1 - drawn) * w / 2; outer = sx * (w / 2 + 0.38); inner = outer - sx * cw
            cols = max(8, int(cw / 0.035)); rows = 7; bmc = B.bm(curtain); grid = []
            for j in range(rows + 1):
                zf = j / rows; z = 0.0 + (ctop - 0.02) * zf; row = []
                pinch = 1 - (0.45 * math.exp(-((z - 1.0) / 0.6) ** 2) if tiebacks and drawn > 0.25 else 0)
                for i in range(cols + 1):
                    u = i / cols; a = outer + (inner - outer) * u * pinch
                    fold = 0.032 * math.sin(u * cw / 0.12 * 6.2832 + sx) * (0.75 + 0.4 * (1 - zf)) + r.uniform(-0.003, 0.003)
                    puddle = 0.05 * max(0.0, 0.08 - z) / 0.08
                    (wx, wy, _), yaw = _wall(R, wn, at_ + a, 0.13 + fold + puddle)
                    row.append(bmc.verts.new((wx, wy, max(0.003, z))))
                grid.append(row)
            yawr = math.radians(_wall(R, wn, 0, 0)[1]); inward = Vector((math.sin(yawr), -math.cos(yawr), 0))
            e1 = grid[0][1].co - grid[0][0].co; flip = e1.cross(Vector((0, 0, 1))).dot(inward) < 0
            for j in range(rows):
                for i in range(cols):
                    q = (grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])
                    f = bmc.faces.new(tuple(reversed(q)) if flip else q); f.smooth = True
    return B.done()


def doors(room, frame, leaf, open_deg=0.0):
    """Dress every door opening (sill 0) of a room made by room(): a moulded architrave with an overdoor
    cornice and a six-panel door leaf hung in it, open by open_deg (swinging into the room)."""
    R = _room(room); room = room or next(iter(_rooms)); B = _B(room + ".doors"); t = R["t"]; out = []
    for o in R["openings"]:
        if o.get("sill", 0.0) > 0.01: continue
        wn = o["wall"]; at_ = o.get("at", 0); w = o["width"]; h = o["height"]
        def wb(m, a, b, z, hh, proud, off, bev=0.0): _wbox(B, R, wn, m, at_ + a, at_ + b, z, hh, proud, off, bev)
        for sx in (-1, 1):
            wb(frame, sx * (w / 2 + 0.07) - 0.07, sx * (w / 2 + 0.07) + 0.07, 0, h + 0.14, 0.03, 0.0, 0.006)
            wb(frame, sx * (w / 2 + 0.15) - 0.015, sx * (w / 2 + 0.15) + 0.015, 0, h + 0.16, 0.045, 0.0)
        wb(frame, -w / 2 - 0.16, w / 2 + 0.16, h, 0.16, 0.03, 0.0)
        wb(frame, -w / 2 - 0.22, w / 2 + 0.22, h + 0.2, 0.12, 0.12, 0.0, 0.01)
        wb(frame, -w / 2 - 0.26, w / 2 + 0.26, h + 0.32, 0.05, 0.16, 0.0, 0.01)
        for sx in (-1, 1): wb(frame, sx * w / 2 - 0.03, sx * w / 2 + 0.03, 0, h, t, -t)    # linings
        wb(frame, -w / 2, w / 2, h - 0.03, 0.03, t, -t)
        # hinge where the frame's local +x starts (the wall's 'at' runs the other way on s and e walls)
        (hx, hy, _), yaw = _wall(R, wn, at_ - w / 2 + 0.02 if wn in "nw" else at_ + w / 2 - 0.02, 0.02)
        G = _B(f"{room}.door{len(out)}", (hx, hy, 0.005), yaw - open_deg)
        lw = w - 0.04; G.box(leaf, (lw, 0.045, h - 0.01), (lw / 2, -0.0225, 0), bevel=0.004)
        for (pz, ph) in ((0.12, 0.42), (0.6, 0.85), (1.52, 0.42)):
                for px in (0.25, 0.75):
                    G.box(leaf, (lw * 0.36, 0.06, (h / 2.2) * ph), (lw * px, -0.0225, (h / 2.2) * pz), bevel=0.01)
        G.ball(frame, 0.03, (lw - 0.08, -0.07, h * 0.45), sub=1)
        out += G.done()
    return B.done() + out


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


def house(name, loc, size, walls, roof, trim, glass, storeys=3, rot=0, roof_kind="hipped", bays=None,
          storey_height=3.1, door=None, chimneys=2, pitch=None, detail=1, seed=0):
    """A period house or cottage (front facing -y before rot) on a stone plinth: walls with real window reveals,
    sash windows with glazing bars, sills and flat-arch lintels, a doorcase with pediment, fanlight and steps,
    a string course, quoins, a cornice, a hipped / gable / flat (parapet) roof, chimney stacks with pots.
    size (width, depth) m; bays: windows across the front (default from width). A Georgian country house:
    storeys=3, bays=7, roof_kind="hipped"; a cottage: storeys=2, storey_height=2.6, roof_kind="gable", pitch=45.
    detail 0 for houses >80 m away (~2k tris), 1 (front detailed, ~5k), 2 near (all faces, ~10k). Returns its objects."""
    r = random.Random(seed); W, D = size; x, y = loc[0], loc[1]
    c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    zs = [ground(x + lx * c - ly * s_, y + lx * s_ + ly * c) for lx in (-W / 2, 0, W / 2) for ly in (-D / 2, 0, D / 2)]
    zlo, zhi = min(zs), max(zs); gl = zhi + 0.45
    B = _B(name, (x, y, gl), rot)
    inner = mat("house interior", (0.07, 0.065, 0.06), kind="fabric")
    sh = storey_height; H = storeys * sh + 0.15; t = 0.22
    pitch = pitch if pitch is not None else (32 if roof_kind == "hipped" else 40)
    cottage = storeys <= 2 and sh < 2.9
    # the dark interior block, seen only through the glass; the walls are built around it with real reveals
    B.box(inner, (W - 2 * t + 0.02, D - 2 * t + 0.02, H), (0, 0, -0.05))
    plinth = 0.45 + (gl - 0.45 - zlo) + 0.3
    B.box(trim, (W + 0.12, D + 0.12, plinth), (0, 0, -plinth + 0.45 - 0.45), bevel=0.02)
    nb = bays or max(3, int(round(W / 2.4)) | 1)
    win_w = 0.95 if not cottage else 0.8
    def storey_win(k):   # (sill, height) of storey k's windows
        zb = 0.0 + k * sh
        if k == storeys - 1 and storeys >= 3: return zb + 0.6, sh * 0.42
        return zb + (0.75 if k == 0 else 0.55), sh * (0.58 if not cottage else 0.45)
    door_col = nb // 2
    def face(L, n, origin, yaw, front):
        fd = detail if front or detail >= 2 else 0
        # origin: local position of the face's centre at floor level; local x along, -y out of the house
        F = _B("", tuple(B.M @ Vector(origin)), rot + yaw); F.parts = B.parts
        cols = [-L / 2 + L * (i + 0.5) / n for i in range(n)] if n else []
        edges = [-L / 2] + [v for cx in cols for v in (cx - win_w / 2, cx + win_w / 2)] + [L / 2]
        for a, b in zip(edges[0::2], edges[1::2]):
            if b - a > 0.01: F.box(walls, (b - a, t, H + 0.05), ((a + b) / 2, -t / 2 + 0.0, -0.05))
        for i, cx in enumerate(cols):
            holes = []
            for k in range(storeys):
                if front and k == 0 and i == door_col:
                    holes.append((0.0, 2.55 if not cottage else 2.0, True))
                else:
                    sl, hh = storey_win(k); holes.append((sl, hh, False))
            zc = -0.05
            for sl, hh, isdoor in holes:
                if sl - zc > 0.01: F.box(walls, (win_w + 0.002, t, sl - zc), (cx, -t / 2, zc))
                zc = sl + hh
            if H - zc > 0.01: F.box(walls, (win_w + 0.002, t, H - zc), (cx, -t / 2, zc))
            for sl, hh, isdoor in holes:
                if isdoor:
                    dw = win_w
                    F.box(door or trim, (dw, 0.06, hh * 0.78), (cx, -0.03, sl))
                    if detail:
                        for pz in (0.15, 0.85):
                            for px in (-0.22, 0.22):
                                F.box(door or trim, (dw * 0.36, 0.08, hh * 0.3), (cx + px * dw, -0.04, sl + hh * 0.78 * pz - hh * 0.15 + (0.05 if pz < 0.5 else 0)))
                    F.box(glass, (dw, 0.03, hh * 0.22), (cx, -0.02, sl + hh * 0.78))
                    if detail:
                        for k in (-1, 0, 1): F.box(trim, (0.025, 0.05, hh * 0.22), (cx + k * dw * 0.25, -0.04, sl + hh * 0.78), (0, k * 25, 0))
                    pw = 0.2 if not cottage else 0.12
                    for sx in (-1, 1):
                        F.box(trim, (pw, 0.14, hh + 0.05), (cx + sx * (dw / 2 + pw / 2), -t - 0.07, sl - 0.02))
                    F.box(trim, (dw + 2 * pw + 0.25, 0.3, 0.28), (cx, -t - 0.1, sl + hh + 0.03), bevel=0.02)
                    if detail and not cottage:
                        pv = [(-dw / 2 - pw - 0.12, 0, 0), (dw / 2 + pw + 0.12, 0, 0), (0, 0, 0.55)]
                        F.mesh(trim, [(cx + px, -t - 0.25, sl + hh + 0.31 + pz) for px, _, pz in pv] + [(cx + px, -t + 0.05, sl + hh + 0.31 + pz) for px, _, pz in pv],
                               [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)])
                    for st in range(3):   # steps down to the ground
                        F.box(trim, (dw + 0.9 - st * 0.2, 0.42 + st * 0.38, 0.15), (cx, -t - 0.21 - st * 0.19, -0.15 * (st + 1)), bevel=0.01)
                    continue
                F.box(glass, (win_w, 0.03, hh), (cx, -0.035, sl))
                if fd:   # meeting rail and glazing bars (six over six)
                    F.box(trim, (win_w, 0.06, 0.05), (cx, -0.07, sl + hh * 0.5 - 0.025))
                    for k in (-1, 1): F.box(trim, (0.03, 0.05, hh), (cx + k * win_w / 6, -0.07, sl))
                    for fz in (0.25, 0.75): F.box(trim, (win_w, 0.05, 0.03), (cx, -0.07, sl + hh * fz))
                F.box(trim, (win_w + 0.2, 0.12, 0.07), (cx, -t - 0.03, sl - 0.07))     # sill
                if fd and not (storeys >= 3 and sl > (storeys - 1) * sh):
                    F.box(trim, (win_w + 0.24, 0.04, 0.22), (cx, -t - 0.015, sl + hh + 0.02))      # flat-arch lintel
                    F.box(trim, (0.16, 0.07, 0.26), (cx, -t - 0.03, sl + hh + 0.01))               # keystone
        # string course and quoins
        if detail and storeys >= 2:
            F.box(trim, (L + 0.1, 0.06, 0.16), (0, -t - 0.02, sh - 0.12))
        if fd and (front or detail >= 2):
            zq = -0.05; k = 0
            while zq < H - 0.4:
                ql = 0.62 if k % 2 == 0 else 0.38
                for sx in (-1, 1): F.box(trim, (ql, 0.04, 0.27), (sx * (L / 2 - ql / 2 + 0.02), -t - 0.01, zq))
                zq += 0.3; k += 1
    face(W, nb, (0, -D / 2 + t, 0), 0, True)
    face(W, nb if detail or nb < 6 else nb, (0, D / 2 - t, 0), 180, False)
    ns = max(0, int(round((D - 1.5) / 3.0)))
    face(D - 0.0, ns, (W / 2 - t, 0, 0), 90, False)
    face(D - 0.0, ns, (-W / 2 + t, 0, 0), -90, False)
    # cornice (stepped), eaves
    ez = H
    if roof_kind != "gable" or detail:
        for k, (o_, hh) in enumerate(((0.04, 0.22), (0.14, 0.12), (0.26, 0.1))):
            B.box(trim, (W + 2 * o_, D + 2 * o_, hh), (0, 0, ez - 0.32 + sum((0.22, 0.12, 0.1)[:k])))
    o = 0.4 if roof_kind != "flat" else 0.0
    ex, ey = W / 2 + o, D / 2 + o; tp = math.tan(math.radians(pitch))
    if roof_kind == "flat":
        for sx, sy, w_, d_ in ((0, -1, W, 0.25), (0, 1, W, 0.25), (-1, 0, 0.25, D), (1, 0, 0.25, D)):
            B.box(walls, (w_, d_, 0.9), (sx * (W / 2 - 0.125), sy * (D / 2 - 0.125), ez))
            B.box(trim, (w_ + 0.06, d_ + 0.06, 0.1), (sx * (W / 2 - 0.125), sy * (D / 2 - 0.125), ez + 0.9))
        B.box(roof, (W - 0.4, D - 0.4, 0.3), (0, 0, ez + 0.1))
        ridge_z = ez + 0.9
    elif roof_kind == "gable":
        rise = ey * tp; ridge_z = ez + rise
        for sy in (-1, 1):
            B.mesh(roof, [(-ex, sy * ey, ez - 0.12), (ex, sy * ey, ez - 0.12), (ex, 0, ez + rise), (-ex, 0, ez + rise),
                          (-ex, sy * ey, ez - 0.28), (ex, sy * ey, ez - 0.28), (ex, 0, ez + rise - 0.18), (-ex, 0, ez + rise - 0.18)],
                   [(0, 1, 2, 3) if sy < 0 else (3, 2, 1, 0), (5, 4, 7, 6) if sy < 0 else (6, 7, 4, 5), (4, 5, 1, 0) if sy < 0 else (0, 1, 5, 4),
                    (0, 3, 7, 4) if sy < 0 else (4, 7, 3, 0), (1, 5, 6, 2) if sy < 0 else (2, 6, 5, 1)])
        for sx in (-1, 1):
            B.mesh(walls, [(sx * W / 2, -D / 2, ez - 0.2), (sx * W / 2, D / 2, ez - 0.2), (sx * W / 2, 0, ez + (D / 2) * tp)], [(0, 1, 2) if sx > 0 else (2, 1, 0)])
            B.mesh(walls, [(sx * (W / 2 - t), -D / 2, ez - 0.2), (sx * (W / 2 - t), D / 2, ez - 0.2), (sx * (W / 2 - t), 0, ez + (D / 2) * tp)], [(2, 1, 0) if sx > 0 else (0, 1, 2)])
        B.box(roof, (2 * ex + 0.04, 0.22, 0.16), (0, 0, ridge_z - 0.08), bevel=0.02)
    else:   # hipped
        long_x = W >= D; a_, b_ = (ex, ey) if long_x else (ey, ex)
        rise = b_ * tp; ridge_z = ez + rise; hr = max(0.0, a_ - b_)
        def P(u, v, zz): return (u, v, zz) if long_x else (v, u, zz)
        top = [P(-a_, -b_, ez - 0.1), P(a_, -b_, ez - 0.1), P(a_, b_, ez - 0.1), P(-a_, b_, ez - 0.1), P(-hr, 0, ez + rise), P(hr, 0, ez + rise),
               P(-a_, -b_, ez - 0.28), P(a_, -b_, ez - 0.28), P(a_, b_, ez - 0.28), P(-a_, b_, ez - 0.28)]
        fs = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4), (6, 7, 1, 0), (7, 8, 2, 1), (8, 9, 3, 2), (9, 6, 0, 3), (9, 8, 7, 6)]
        if not long_x: fs = [tuple(reversed(f)) for f in fs]
        B.mesh(roof, top, fs)
        if detail:
            B.seg(roof, P(-hr, 0, ez + rise + 0.03), P(hr + 0.001, 0, ez + rise + 0.03), 0.09, 0.09, 6)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    B.seg(roof, P(sx * a_, sy * b_, ez - 0.05), P(sx * hr, 0, ez + rise + 0.03), 0.07, 0.07, 5)
    if detail >= 2 and roof_kind != "flat":   # slate courses: shallow steps that catch the light
        n = int(((ridge_z - ez) / tp) / 0.45)
        for k in range(1, n):
            f = k / n; zz = ez - 0.1 + (ridge_z - ez) * f
            if roof_kind == "gable":
                for sy in (-1, 1): B.box(roof, (2 * ex, 0.05, 0.025), (0, sy * ey * (1 - f), zz), (sy * pitch, 0, 0))
    for i in range(chimneys):   # stacks on the side walls (hipped) or gable ends, with a cap and pots
        sx = -1 if i % 2 == 0 else 1
        if roof_kind == "gable": cx_, cy_ = sx * (W / 2 - 0.4), 0.0
        else: cx_, cy_ = sx * (W / 2 - 1.6 - (i // 2) * 2.5), (D * 0.12 if i // 2 == 0 else -D * 0.12)
        top_z = ridge_z + (0.9 if roof_kind != "flat" else 1.0)
        cw = 1.4 if not cottage else 0.8
        B.box(walls, (cw, 0.7, top_z - ez + 0.2), (cx_, cy_, ez - 0.2))
        B.box(trim, (cw + 0.16, 0.86, 0.14), (cx_, cy_, top_z - 0.1))
        for k in range(3 if not cottage else 2):
            B.cyl(walls, 0.13, 0.45 + r.uniform(-0.05, 0.1), (cx_ + (k - (1 if not cottage else 0.5)) * 0.4, cy_, top_z + 0.04), sides=8, r1=0.1)
    return B.done()


def table(name, loc, material, size=(1.2, 0.75, 0.76), rot=0, legs="tapered"):
    """A table (size: length, width, height) with a moulded top, an apron and tapered square legs (legs
    "turned" for round ones). loc (x, y) on the floor or (x, y, z). Returns its objects."""
    x, y = loc[0], loc[1]; z = ground(x, y) if len(loc) < 3 else loc[2]
    L, Wd, Ht = size; B = _B(name, (x, y, z), rot)
    B.box(material, (L, Wd, 0.032), (0, 0, Ht - 0.032), bevel=0.01)
    B.box(material, (L - 0.04, Wd - 0.04, 0.02), (0, 0, Ht - 0.05))
    ap = min(0.11, Ht * 0.15)
    for sy in (-1, 1): B.box(material, (L - 0.14, 0.022, ap), (0, sy * (Wd / 2 - 0.06), Ht - 0.05 - ap))
    for sx in (-1, 1): B.box(material, (0.022, Wd - 0.14, ap), (sx * (L / 2 - 0.06), 0, Ht - 0.05 - ap))
    for dx in (-1, 1):
        for dy in (-1, 1):
            p = (dx * (L / 2 - 0.06), dy * (Wd / 2 - 0.06), 0)
            if legs == "turned":
                B.cyl(material, 0.018, Ht - 0.05, p, sides=10, r1=0.03)
                B.ball(material, 0.034, (p[0], p[1], Ht * 0.55), (1, 1, 1.4), sub=1)
            else:
                B.cyl(material, 0.022, Ht - 0.05, p, rot=(0, 0, 45), sides=4, r1=0.034, smooth=False)
    return B.done()


def chair(name, loc, material, rot=0, fabric=None):
    """A Regency side chair (seat top 0.48 m, back toward +y before rot): turned front legs, sabre back legs
    sweeping up into the back, a curved top rail and a cross rail; fabric: an optional upholstered drop-in seat."""
    x, y = loc[0], loc[1]; z = ground(x, y); B = _B(name, (x, y, z), rot)
    B.box(material, (0.44, 0.42, 0.05), (0, 0, 0.42), bevel=0.008)
    if fabric is not None: B.box(fabric, (0.4, 0.38, 0.05), (0, -0.005, 0.44), bevel=0.02, seg=2, smooth=True)
    for dx in (-1, 1):
        B.cyl(material, 0.016, 0.42, (dx * 0.19, -0.18, 0), sides=8, r1=0.022)
        B.tube(material, [(dx * 0.19, 0.26, 0.0), (dx * 0.19, 0.2, 0.22), (dx * 0.19, 0.185, 0.44), (dx * 0.19, 0.22, 0.7), (dx * 0.19, 0.26, 0.9)],
               [0.016, 0.019, 0.02, 0.018, 0.016], 6)
    B.tube(material, [(-0.22, 0.25, 0.86), (0, 0.28, 0.87), (0.22, 0.25, 0.86)], [0.035, 0.035, 0.035], 6)
    B.box(material, (0.38, 0.018, 0.04), (0, 0.215, 0.68), (12, 0, 0))
    for sy in (-0.18, 0.18): B.box(material, (0.36, 0.02, 0.03), (0, sy, 0.12))
    return B.done()


def shelf(name, loc, material, book_materials=(), width=1.0, height=1.8, depth=0.32, rot=0, seed=0, cornice=True):
    """A bookcase (back toward +y before rot) with plinth, cornice and shelves, filled when book_materials are
    given: runs of books in sets of matching height and colour, a leaning book at a run's end, flat stacks and
    gaps, pushed to the front edge at slightly different depths."""
    x, y = loc[0], loc[1]; z = ground(x, y); r = random.Random(seed); B = _B(name, (x, y, z), rot)
    B.box(material, (width, 0.02, height), (0, depth / 2 - 0.01, 0))
    for side in (-1, 1): B.box(material, (0.03, depth, height), (side * (width / 2 - 0.015), 0, 0))
    B.box(material, (width + 0.02, depth + 0.02, 0.09), (0, 0.0, 0.0))
    if cornice:
        B.box(material, (width + 0.06, depth + 0.04, 0.05), (0, -0.01, height - 0.02), bevel=0.01)
        B.box(material, (width + 0.1, depth + 0.07, 0.04), (0, -0.02, height + 0.03), bevel=0.01)
    n = max(2, int((height - 0.09) / 0.34)); gap = (height - 0.09 - 0.025) / n
    for i in range(n + 1):
        sz = 0.09 + i * gap
        B.box(material, (width - 0.06, depth - 0.02, 0.025), (0, 0.0, sz - (0.025 if i == n else 0)))
        if not book_materials or i == n: continue
        bx = -width / 2 + 0.035; end = width / 2 - 0.035; top = gap - 0.04
        while bx < end - 0.03:
            roll = r.random()
            if roll < 0.06:   # a gap
                bx += r.uniform(0.05, 0.14); continue
            if roll < 0.13 and end - bx > 0.3:   # a flat stack
                bw = r.uniform(0.17, 0.24); bd = r.uniform(0.13, depth - 0.06); zz = sz + 0.025
                for k in range(r.randint(2, 5)):
                    th = r.uniform(0.025, 0.05)
                    if zz + th > sz + top: break
                    B.box(r.choice(book_materials), (bw, bd, th), (bx + bw / 2 + r.uniform(-0.01, 0.01), -depth / 2 + bd / 2 + 0.02, zz), (0, 0, r.uniform(-4, 4)))
                    zz += th
                bx += bw + 0.01; continue
            m = r.choice(book_materials); hh = min(top, r.uniform(0.19, 0.3)); dd = min(depth - 0.05, r.uniform(0.15, 0.24))
            for k in range(r.randint(2, 7)):   # a set: same colour and height
                bw = r.uniform(0.025, 0.05)
                if bx + bw > end: break
                B.box(m, (bw, dd + r.uniform(-0.01, 0.01), hh * r.uniform(0.98, 1.0)), (bx + bw / 2, -depth / 2 + dd / 2 + 0.015 + r.uniform(0, 0.012), sz + 0.025), (0, 0, 0))
                bx += bw + 0.0015
            if r.random() < 0.18 and end - bx > 0.12:   # one leaning on the run
                bw = r.uniform(0.025, 0.04); hl = min(top - 0.01, r.uniform(0.18, 0.26)); ang = r.uniform(10, 22)
                bx += hl * math.sin(math.radians(ang))
                B.box(r.choice(book_materials), (bw, dd, hl), (bx, -depth / 2 + dd / 2 + 0.02, sz + 0.025), (0, -ang, 0))
                bx += bw + 0.02
    return B.done()


def fireplace(name, loc, surround, rot=0, width=1.5, height=1.2, fire=True, hearth_stone=None, breast=None,
              breast_height=None):
    """A Georgian chimneypiece against a wall: loc (x, y) is the middle of its foot on the wall face, rot turns
    its back to the wall (0 = a north/+y wall, 180 south, -90 east, 90 west). Pilasters, a frieze with a centre
    tablet and a moulded mantel shelf (surround, e.g. marble), a dark cast-iron register grate with glowing coals
    and their light, a hearth slab (hearth_stone) and, with breast (a wall material), a chimney breast."""
    x, y = loc[0], loc[1]; z = ground(x, y); B = _B(name, (x, y, z), rot)
    iron = mat("cast iron", (0.07, 0.07, 0.07), kind="metal", rough=0.6)
    yf = 0.0
    if breast is not None:
        bh = breast_height or next((R["h"] for R in _rooms.values() if abs(x - R["cx"]) <= R["w"] / 2 + 0.3 and abs(y - R["cy"]) <= R["d"] / 2 + 0.3), 3.0)
        B.box(breast, (width + 0.9, 0.4, bh), (0, 0.2 - 0.4, 0)); yf = -0.4
        sk = next((m for m in (hearth_stone, surround) if m is not None), surround)
        for sx in (-1, 1): B.box(sk, (0.02, 0.4, 0.2), (sx * (width / 2 + 0.46), -0.2, 0))
        B.box(sk, (width + 0.94, 0.02, 0.2), (0, -0.41, 0))
    ow = width * 0.6; oh = height * 0.72; pw = (width - ow) / 2
    B.box(iron, (ow + 0.02, 0.04, oh), (0, yf - 0.03, 0))                      # fireback
    for sx in (-1, 1): B.box(iron, (0.03, 0.2, oh), (sx * (ow / 2 - 0.015), yf - 0.12, 0), (0, 0, sx * 12))
    B.box(iron, (ow, 0.2, 0.04), (0, yf - 0.12, oh - 0.04))
    for sx in (-1, 1):   # pilasters with bases and capitals
        px = sx * (ow / 2 + pw / 2)
        B.box(surround, (pw, 0.2, height - 0.2), (px, yf - 0.1, 0), bevel=0.008)
        B.box(surround, (pw + 0.04, 0.24, 0.12), (px, yf - 0.12, 0), bevel=0.01)
        B.box(surround, (pw * 0.6, 0.04, height - 0.42), (px, yf - 0.21, 0.14), bevel=0.006)
        B.box(surround, (pw + 0.03, 0.23, 0.08), (px, yf - 0.115, height - 0.28), bevel=0.01)
    B.box(surround, (width, 0.2, height - oh), (0, yf - 0.1, oh), bevel=0.006)    # frieze
    B.box(surround, (0.32, 0.04, (height - oh) * 0.6), (0, yf - 0.215, oh + (height - oh) * 0.2), bevel=0.008)
    B.box(surround, (width + 0.1, 0.25, 0.04), (0, yf - 0.12, height - 0.04), bevel=0.01)
    B.box(surround, (width + 0.2, 0.3, 0.045), (0, yf - 0.15, height), bevel=0.015)   # mantel shelf
    B.box(hearth_stone or surround, (width + 0.35, 0.5, 0.03), (0, yf - 0.25 - 0.2, 0), bevel=0.008)
    # register grate: front bars on short legs, the basket full of coals
    gw = ow * 0.62
    for k in range(4): B.box(iron, (gw, 0.02, 0.018), (0, yf - 0.22, 0.12 + k * 0.07))
    for sx in (-1, 1): B.box(iron, (0.035, 0.18, 0.36), (sx * gw / 2, yf - 0.15, 0.0))
    B.box(iron, (gw + 0.4, 0.02, 0.06), (0, yf - 0.52, 0.0))   # fender
    if fire:
        f = mat("fire", (1.0, 0.45, 0.12), kind="fabric", emission=6.0)
        rr = random.Random(int(x * 10 + y))
        for k in range(7):
            B.ball(f if k % 3 else iron, rr.uniform(0.035, 0.06), (rr.uniform(-gw / 2.6, gw / 2.6), yf - 0.13 + rr.uniform(-0.04, 0.04), 0.3 + rr.uniform(0, 0.08)), (1.2, 1, 0.8), sub=1)
        lamp(name + ".fire", tuple(B.at(0, yf - 0.35, 0.45)), power=160, color=(1.0, 0.55, 0.25), radius=0.2)
    return B.done()


def picture(name, loc, size, frame, canvas, rot=0, depth=0.06):
    """A framed picture or looking glass hung on a wall: loc (x, y, z) is its centre on the wall face, rot as in
    fireplace() (0 = north wall). size (w, h) m. A stepped, moulded gilt or wood frame round the canvas
    (a painting material, or a mirror material for a glass)."""
    x, y, z = loc; B = _B(name, (x, y, z), rot); w, h = size
    fw = min(0.11, 0.1 * min(w, h) + 0.03)
    for (a0, a1, z0, hh) in ((-w / 2, w / 2, -h / 2, fw), (-w / 2, w / 2, h / 2 - fw, fw), (-w / 2, -w / 2 + fw, -h / 2, h), (w / 2 - fw, w / 2, -h / 2, h)):
        B.box(frame, (a1 - a0, depth, hh), ((a0 + a1) / 2, -depth / 2, z0), bevel=0.008)
    i = fw * 0.55
    for (a0, a1, z0, hh) in ((-w / 2 + i, w / 2 - i, -h / 2 + i, 0.022), (-w / 2 + i, w / 2 - i, h / 2 - i - 0.022, 0.022),
                             (-w / 2 + i, -w / 2 + i + 0.022, -h / 2 + i, h - 2 * i), (w / 2 - i - 0.022, w / 2 - i, -h / 2 + i, h - 2 * i)):
        B.box(frame, (a1 - a0, depth + 0.016, hh), ((a0 + a1) / 2, -depth / 2 - 0.008, z0), bevel=0.005)
    B.box(canvas, (w - 2 * fw + 0.02, 0.02, h - 2 * fw + 0.02), (0, -0.015, -h / 2 + fw - 0.01))
    return B.done()


def sofa(name, loc, frame, fabric, rot=0, length=1.9, cushions=None):
    """A Regency settee (back toward +y before rot; seat 0.45 m): scroll arms, a show-wood seat rail and top
    rail, a tight back, a plump seat cushion, bolsters and tapered legs on brass-cupped feet. cushions: an
    optional material for two loose cushions."""
    x, y = loc[0], loc[1]; z = ground(x, y); B = _B(name, (x, y, z), rot); L = length
    for sx in (-1, 1):
        for sy in (-1, 1):
            B.cyl(frame, 0.02, 0.17, (sx * (L / 2 - 0.08), sy * 0.3, 0), (sy * -6, sx * 6, 0), sides=8, r1=0.03)
    B.box(frame, (L, 0.74, 0.09), (0, 0, 0.16), bevel=0.012)
    B.box(fabric, (L - 0.06, 0.72, 0.14), (0, 0.0, 0.25), bevel=0.03, seg=2, smooth=True)
    B.box(fabric, (L - 0.3, 0.6, 0.11), (0, -0.05, 0.37), bevel=0.045, seg=3, smooth=True)
    B.box(fabric, (L - 0.06, 0.16, 0.5), (0, 0.29, 0.36), (-9, 0, 0), bevel=0.05, seg=2, smooth=True)
    B.tube(frame, [(-L / 2 + 0.05, 0.36, 0.85), (0, 0.39, 0.88), (L / 2 - 0.05, 0.36, 0.85)], [0.028, 0.028, 0.028], 8)
    for sx in (-1, 1):
        ax = sx * (L / 2 - 0.07)
        B.box(fabric, (0.12, 0.7, 0.3), (ax, -0.01, 0.36), bevel=0.03, seg=2, smooth=True)
        B.cyl(fabric, 0.1, 0.72, (ax + sx * 0.02, -0.37, 0.7), (-90, 0, 0), sides=14)
        B.cyl(frame, 0.104, 0.02, (ax + sx * 0.02, -0.38, 0.7), (-90, 0, 0), sides=14)
        B.cyl(fabric, 0.085, 0.42, (sx * (L / 2 - 0.36), -0.04, 0.56), (-90, 0, 0), sides=12)
    if cushions is not None:
        for sx in (-1, 1):
            B.box(cushions, (0.4, 0.13, 0.38), (sx * (L / 2 - 0.62), 0.12, 0.47), (-18, 0, sx * -8), bevel=0.06, seg=3, smooth=True)
    return B.done()


def armchair(name, loc, frame, fabric, rot=0, kind="bergere"):
    """An upholstered armchair (back toward +y before rot): "bergere" (show-wood frame, padded arms on
    turned supports) or "wing" (deep wings, scroll arms). Seat about 0.45 m."""
    x, y = loc[0], loc[1]; z = ground(x, y); B = _B(name, (x, y, z), rot)
    W = 0.74 if kind == "bergere" else 0.82
    for sx in (-1, 1):
        for sy in (-1, 1): B.cyl(frame, 0.018, 0.2, (sx * (W / 2 - 0.06), sy * 0.28, 0), sides=8, r1=0.026)
    B.box(frame, (W, 0.68, 0.08), (0, 0, 0.19), bevel=0.012)
    B.box(fabric, (W - 0.16, 0.56, 0.14), (0, -0.05, 0.27), bevel=0.05, seg=3, smooth=True)
    bh = 0.62 if kind == "bergere" else 0.82
    B.box(fabric, (W - 0.04, 0.14, bh), (0, 0.29, 0.27), (-10, 0, 0), bevel=0.05, seg=2, smooth=True)
    if kind == "bergere":
        B.tube(frame, [(-W / 2 + 0.03, 0.36, 0.85), (0, 0.41, 0.9), (W / 2 - 0.03, 0.36, 0.85)], [0.026, 0.026, 0.026], 8)
        for sx in (-1, 1):
            B.box(fabric, (0.1, 0.46, 0.08), (sx * (W / 2 - 0.06), -0.03, 0.6), bevel=0.03, seg=2, smooth=True)
            B.cyl(frame, 0.02, 0.36, (sx * (W / 2 - 0.06), -0.27, 0.25), sides=8, r1=0.016)
            B.box(fabric, (0.05, 0.4, 0.26), (sx * (W / 2 - 0.04), 0.0, 0.32), bevel=0.02, smooth=True)
    else:
        for sx in (-1, 1):
            B.box(fabric, (0.12, 0.62, 0.32), (sx * (W / 2 - 0.06), -0.01, 0.3), bevel=0.04, seg=2, smooth=True)
            B.cyl(fabric, 0.08, 0.62, (sx * (W / 2 - 0.05), -0.33, 0.63), (-90, 0, 0), sides=12)
            B.box(fabric, (0.12, 0.32, 0.55), (sx * (W / 2 - 0.05), 0.2, 0.6), (0, 0, sx * -12), bevel=0.05, seg=2, smooth=True)
    return B.done()


def desk(name, loc, wood, rot=0, size=(1.2, 0.65, 0.76), top=None, kind="writing", knobs=None):
    """A writing table (kind "writing": frieze drawers on tapered legs) or a pedestal desk (kind "pedestal":
    two banks of drawers), front toward -y before rot, with a tooled leather top inset (top material) and
    knobs (e.g. brass)."""
    x, y = loc[0], loc[1]; z = ground(x, y); B = _B(name, (x, y, z), rot); L, Wd, Ht = size; kn = knobs or wood
    B.box(wood, (L, Wd, 0.032), (0, 0, Ht - 0.032), bevel=0.01)
    if top is not None: B.box(top, (L - 0.12, Wd - 0.12, 0.004), (0, 0, Ht))
    fh = 0.13
    B.box(wood, (L - 0.04, Wd - 0.04, fh), (0, 0, Ht - 0.032 - fh))
    nd = 3 if L > 1.0 else 2
    for i in range(nd):
        dx = -L / 2 + 0.02 + (L - 0.04) * (i + 0.5) / nd
        B.box(wood, ((L - 0.04) / nd - 0.03, 0.012, fh - 0.03), (dx, -Wd / 2 + 0.014, Ht - 0.032 - fh + 0.015), bevel=0.004)
        B.ball(kn, 0.014, (dx, -Wd / 2 + 0.0, Ht - 0.032 - fh / 2), sub=1)
    if kind == "pedestal":
        pw = L * 0.3
        for sx in (-1, 1):
            px = sx * (L / 2 - pw / 2 - 0.02)
            B.box(wood, (pw, Wd - 0.06, Ht - 0.032 - fh), (px, 0, 0), bevel=0.006)
            B.box(wood, (pw + 0.03, Wd - 0.03, 0.08), (px, 0, 0), bevel=0.006)
            n = 3; dh = (Ht - 0.032 - fh - 0.1) / n
            for k in range(n):
                B.box(wood, (pw - 0.05, 0.012, dh - 0.03), (px, -Wd / 2 + 0.024, 0.1 + k * dh + 0.015), bevel=0.004)
                B.ball(kn, 0.014, (px, -Wd / 2 + 0.01, 0.1 + k * dh + dh / 2), sub=1)
    else:
        for dx in (-1, 1):
            for dy in (-1, 1):
                B.cyl(wood, 0.018, Ht - 0.032 - fh, (dx * (L / 2 - 0.05), dy * (Wd / 2 - 0.05), 0), rot=(0, 0, 45), sides=4, r1=0.032, smooth=False)
    return B.done()


def side_table(name, loc, wood, rot=0, size=0.55, height=0.7, round=True):
    """A small table: round = a tripod tea table (turned pillar, three splayed legs, dished top), otherwise a
    square lamp table with a drawer and tapered legs. size = top diameter / width (m)."""
    x, y = loc[0], loc[1]; z = ground(x, y); B = _B(name, (x, y, z), rot)
    if round:
        B.cyl(wood, size / 2, 0.025, (0, 0, height - 0.025), sides=24)
        B.cyl(wood, size / 2 - 0.02, 0.012, (0, 0, height - 0.003), sides=24, r1=size / 2 - 0.012)
        B.cyl(wood, 0.035, height - 0.2, (0, 0, 0.18), sides=10, r1=0.025)
        B.ball(wood, 0.055, (0, 0, 0.26), (1, 1, 1.5), sub=1)
        B.ball(wood, 0.04, (0, 0, height - 0.08), (1, 1, 1.2), sub=1)
        for k in range(3):
            a = 6.2832 * k / 3; d = Vector((math.cos(a), math.sin(a), 0))
            B.tube(wood, [Vector((0, 0, 0.24)) + d * 0.03, Vector((0, 0, 0.12)) + d * 0.14, Vector((0, 0, 0.02)) + d * 0.24], [0.026, 0.02, 0.014], 6)
        return B.done()
    B.box(wood, (size, size, 0.025), (0, 0, height - 0.025), bevel=0.008)
    B.box(wood, (size - 0.05, size - 0.05, 0.1), (0, 0, height - 0.125))
    B.box(wood, (size - 0.12, 0.012, 0.07), (0, -size / 2 + 0.022, height - 0.11), bevel=0.003)
    B.ball(wood, 0.012, (0, -size / 2 + 0.01, height - 0.075), sub=1)
    for dx in (-1, 1):
        for dy in (-1, 1):
            B.cyl(wood, 0.014, height - 0.125, (dx * (size / 2 - 0.04), dy * (size / 2 - 0.04), 0), rot=(0, 0, 45), sides=4, r1=0.026, smooth=False)
    return B.done()


def clutter(name, loc, kind, materials, rot=0, seed=0):
    """Small things arranged on a surface at loc (x, y, z): kind "books" (materials: cover colours; a stack and
    an open book), "writing" ([paper, metal]: letters, an inkstand, a quill), "tea" ([china, tray]: tray,
    teapot, cups and saucers, sugar bowl), "mantel" ([gilt, china]: a bracket clock, a pair of vases,
    candlesticks). Each fills about 0.5 x 0.35 m."""
    x, y, z = loc; r = random.Random(seed); B = _B(name, (x, y, z), rot); m = list(materials)
    pages = mat("pages", (0.86, 0.82, 0.71), kind="paper")
    if kind == "books":
        zz = 0.0; bx = r.uniform(-0.15, -0.08)
        for k in range(r.randint(2, 4)):
            th = r.uniform(0.025, 0.05); bw, bd = r.uniform(0.16, 0.24), r.uniform(0.11, 0.17)
            B.box(m[k % len(m)], (bw, bd, th), (bx + r.uniform(-0.02, 0.02), r.uniform(-0.02, 0.02), zz), (0, 0, r.uniform(-14, 14)))
            B.box(pages, (bw - 0.01, bd - 0.012, th - 0.008), (bx + 0.004, 0.0, zz + 0.004), (0, 0, 0))
            zz += th
        # an open book: two page blocks bowed up from the spine
        ox = 0.14; ang = r.uniform(-20, 20)
        B.box(m[-1], (0.3, 0.2, 0.006), (ox, 0.02, 0), (0, 0, ang))
        for sx in (-1, 1):
            B.box(pages, (0.135, 0.19, 0.012), (ox + sx * 0.068 * math.cos(math.radians(ang)), 0.02 + sx * 0.068 * math.sin(math.radians(ang)), 0.006), (0, sx * -5, ang), bevel=0.004)
    elif kind == "writing":
        paper, metal = m[0], m[-1]
        for k in range(r.randint(3, 5)):
            B.box(paper, (0.21, 0.3, 0.002), (r.uniform(-0.15, 0.1), r.uniform(-0.05, 0.05), k * 0.0021), (0, 0, r.uniform(-25, 25)))
        B.box(metal, (0.26, 0.16, 0.015), (0.16, 0.08, 0), bevel=0.004)
        for sx in (-1, 1): B.cyl(metal, 0.028, 0.055, (0.16 + sx * 0.07, 0.08, 0.015), sides=10, r1=0.022)
        B.poly(paper, [(0.13, 0.06, 0.06), (0.15, 0.07, 0.1), (0.02, -0.05, 0.03), (0.03, -0.06, 0.025)])
    elif kind == "tea":
        china, tray = m[0], m[-1]
        B.box(tray, (0.5, 0.34, 0.012), (0, 0, 0), bevel=0.006)
        for sx in (-1, 1): B.box(tray, (0.5 if sx else 0.34, 0.012, 0.03), (0, sx * 0.165, 0.012))
        B.ball(china, 0.075, (-0.1, 0.05, 0.085), (1, 1, 0.85), sub=2)
        B.cyl(china, 0.04, 0.02, (-0.1, 0.05, 0.012), sides=12)
        B.seg(china, (-0.04, 0.05, 0.07), (0.03, 0.05, 0.13), 0.014, 0.007, 6)
        B.tube(china, [(-0.17, 0.05, 0.12), (-0.21, 0.05, 0.1), (-0.17, 0.05, 0.06)], [0.008, 0.008, 0.008], 5)
        B.ball(china, 0.016, (-0.1, 0.05, 0.16), sub=1)
        for k, (cx, cy) in enumerate(((0.1, -0.08), (0.17, 0.06), (-0.02, -0.11))):
            B.cyl(china, 0.06, 0.008, (cx, cy, 0.012), sides=14, r1=0.07)
            B.cyl(china, 0.028, 0.05, (cx, cy, 0.02), sides=12, r1=0.04)
        B.cyl(china, 0.04, 0.05, (0.0, 0.1, 0.012), sides=12, r1=0.05)
    else:   # mantel
        gilt, china = m[0], m[-1]
        B.box(gilt, (0.24, 0.14, 0.04), (0, 0, 0), bevel=0.006)
        B.box(gilt, (0.2, 0.12, 0.26), (0, 0, 0.04), bevel=0.01)
        B.ball(gilt, 0.1, (0, 0, 0.3), (1, 0.6, 0.45), sub=1)
        B.cyl(china, 0.06, 0.006, (0, -0.06, 0.16), (90, 0, 0), sides=16)
        for sx in (-1, 1):
            B.cyl(china, 0.045, 0.06, (sx * 0.38, 0, 0), sides=12, r1=0.06)
            B.ball(china, 0.07, (sx * 0.38, 0, 0.13), (1, 1, 1.2), sub=2)
            B.cyl(china, 0.035, 0.08, (sx * 0.38, 0, 0.2), sides=12, r1=0.05)
            B.cyl(gilt, 0.05, 0.02, (sx * 0.62, 0, 0), sides=10)
            B.cyl(gilt, 0.012, 0.22, (sx * 0.62, 0, 0.02), sides=8, r1=0.016)
            B.cyl(gilt, 0.025, 0.03, (sx * 0.62, 0, 0.24), sides=10, r1=0.02)
    return B.done()


def candelabra(name, loc, metal, wax, arms=3, power=10):
    """A branched candelabrum standing at loc (x, y, z): a stepped foot, a baluster stem and curving arms (arms
    2-5 plus a centre light), each with a lit candle."""
    x, y, z = loc; B = _B(name, (x, y, z), 0)
    B.cyl(metal, 0.075, 0.02, (0, 0, 0), sides=14); B.ball(metal, 0.06, (0, 0, 0.035), (1, 1, 0.45), sub=1)
    B.cyl(metal, 0.012, 0.3, (0, 0, 0.04), sides=8, r1=0.016); B.ball(metal, 0.03, (0, 0, 0.16), (1, 1, 1.3), sub=1)
    B.ball(metal, 0.024, (0, 0, 0.33), sub=1)
    tops = [(0.0, 0.0, 0.36)]
    for k in range(arms):
        a = 6.2832 * k / arms; d = Vector((math.cos(a), math.sin(a), 0)); R = 0.15
        B.tube(metal, [Vector((0, 0, 0.32)), d * R * 0.5 + Vector((0, 0, 0.27)), d * R + Vector((0, 0, 0.3)), d * R + Vector((0, 0, 0.34))], [0.008, 0.008, 0.008, 0.008], 6)
        tops.append(tuple(d * R + Vector((0, 0, 0.34))))
    out = B.done()
    for i, tp in enumerate(tops):
        p = Vector((x, y, z)) + Vector(tp)
        cup = _B(f"{name}.cup{i}", tuple(p), 0); cup.cyl(metal, 0.02, 0.025, (0, 0, 0), sides=10, r1=0.028); out += cup.done()
        out.append(candle(f"{name}.c{i}", (p.x, p.y, p.z + 0.02), wax, power=power if i else power * 0.7, height=0.16))
    return out


def chandelier(name, loc, metal, wax, arms=8, power=12, drops=None, drop=0.9):
    """A candle chandelier hanging from the ceiling point loc (x, y, z): ceiling rose, chain, baluster body,
    a ring of S-scroll arms with lit candles; drops: an optional glass material for festoons of crystal drops.
    drop: hanging length (m) from the ceiling to the arms."""
    x, y, zc = loc; B = _B(name, (x, y, zc), 0); za = -drop
    B.cyl(metal, 0.16, 0.03, (0, 0, -0.03), sides=16)
    for k in range(int(drop / 0.08)):
        B.ball(metal, 0.022, (0, 0, -0.06 - k * 0.075), (0.5, 1, 1.4) if k % 2 else (1, 0.5, 1.4), sub=1)
    B.ball(metal, 0.09, (0, 0, za - 0.02), (1, 1, 1.4), sub=2)
    B.ball(metal, 0.05, (0, 0, za - 0.2), (1, 1, 1.2), sub=1)
    B.cyl(metal, 0.012, 0.4, (0, 0, za - 0.3), sides=8)
    tips = []
    for k in range(arms):
        a = 6.2832 * k / arms; d = Vector((math.cos(a), math.sin(a), 0)); R = 0.42
        pts = [Vector((0, 0, za - 0.12)) + d * 0.05, d * R * 0.35 + Vector((0, 0, za - 0.22)), d * R * 0.75 + Vector((0, 0, za - 0.2)),
               d * R + Vector((0, 0, za - 0.1)), d * R + Vector((0, 0, za - 0.02))]
        B.tube(metal, pts, [0.01] * 5, 6)
        B.cyl(metal, 0.02, 0.03, tuple(d * R + Vector((0, 0, za - 0.02))), sides=10, r1=0.032)
        tips.append(d * R + Vector((0, 0, za + 0.01)))
        if drops is not None:   # festoons from arm to arm and a pendant under each
            d2 = Vector((math.cos(a + 6.2832 / arms), math.sin(a + 6.2832 / arms), 0))
            for j in range(1, 6):
                t = j / 6; p = (d * R).lerp(d2 * R, t) * 0.97 + Vector((0, 0, za - 0.04 - 0.12 * math.sin(math.pi * t)))
                B.ball(drops, 0.012, tuple(p), sub=0)
            B.ball(drops, 0.018, tuple(d * R + Vector((0, 0, za - 0.1))), (1, 1, 2.2), sub=0)
    out = B.done()
    for i, tp in enumerate(tips):
        p = Vector((x, y, zc)) + tp
        out.append(candle(f"{name}.c{i}", (p.x, p.y, p.z), wax, power=power, height=0.14))
    return out


def bed(name, loc, frame, linen, rot=0, size=(1.4, 2.0)):
    """A bed (size: width, length; head toward +y before rot) with frame, mattress, headboard and pillow."""
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


def rug(name, loc, size, material, rot=0, border=None):
    """A flat rug of size (x, y) on the floor; border: an optional material for a border band."""
    if border is not None:
        x, y = loc[0], loc[1]; z = ground(x, y)
        B = _B(name, (x, y, z), rot); bw = min(size) * 0.09
        B.box(border, (size[0], size[1], 0.012), (0, 0, 0.001), bevel=0.004)
        B.box(material, (size[0] - 2 * bw, size[1] - 2 * bw, 0.004), (0, 0, 0.012))
        return B.done()
    x, y = loc[0], loc[1]
    return box(name, (size[0], size[1], 0.012), (x, y, ground(x, y) + 0.001), material, rot=(0, 0, rot), bevel=0.004)


def candle(name, loc, wax, power=12, flame=True, height=0.18):
    """A wax candle standing at loc (x, y, z) with a small glowing flame and its light (power in watts)."""
    x, y, z = loc
    p = cylinder(name, 0.022, height, (x, y, z), wax, sides=8)
    if flame:
        f = mat("candle flame", (1.0, 0.8, 0.5), kind="paper", emission=14.0, emission_color=(1.0, 0.72, 0.4))
        blob(name + ".flame.glow", 0.009, (x, y, z + height + 0.022), f, squash=(1, 1, 2.4), roughness=0.0, detail=1)
    lamp(name + ".flame", (x, y, z + height + 0.04), power=power, color=(1.0, 0.68, 0.36), radius=0.02)
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
