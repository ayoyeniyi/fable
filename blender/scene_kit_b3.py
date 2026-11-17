"""
Fable: shared set-up, foliage, living-scene markers, captures and export for the chapter step-in rooms built by
room builder 3 (docs/SCENE_ROOMS.md): build_ithaca_assembly.py, build_saville_row_house.py, build_archangel_quay.py,
build_mildendo_palace_court.py, build_scotland_yard_office.py, build_blefuscu_harbour_channel.py,
build_duchess_kitchen.py, build_alcinous_hall.py, build_bristol_quays.py, build_brobdingnag_farmhouse_table.py,
build_cyclops_cave.py.

It glues three existing kits together rather than copying them:
  * pride_kit  - the scene set-up (Cycles, AgX, Metal), the stamped "Blender render" stills, anchors and lights;
  * roomkit    - noise-varied PBR materials at a believable texture scale, the part builder (_B), terrain, rocks;
  * alice_foliage - real branching trees with painted leaf-spray cards (alpha MASK) and a 'sway' colour attribute.

Export (until docs/SCENE_ROOMS_PIPELINE.md says otherwise): meshes are joined by material; procedural materials are
baked to BaseColor + Roughness textures (CPU, 1 sample); painted atlases are kept; living-scene names survive the
merge (veg.*, cloth.*, water.*), fx.* / sound.* / anchor.* empties carry their custom properties (export_extras), and
lights are exported so the runtime can decide what to keep. Output: out/<id>/<id_underscored>.gltf + .bin + textures/.

Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os, json
import numpy as np
from mathutils import Vector, Matrix, Euler, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as pk
import roomkit as rk
import alice_foliage as af

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ID = None
ARGS = None
OUT = None
CAMS = []
KEEP = {}            # material name -> living-scene object name kept after the merge
SIZE = {}            # material name -> (basecolor, roughness) bake sizes


def setup(scene_id, seed=1, samples=48):
    """Empty scene, Cycles on the GPU, a world, the kits wired to one collection. Returns the parsed args."""
    global ID, ARGS, OUT
    ID = scene_id
    ARGS = pk.setup(scene_id, os.path.join(REPO, "out", scene_id), seed, scene_id, default_samples=samples)
    OUT = pk.OUT
    sc = bpy.context.scene
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 2
    rk.COLL = pk.COLL; rk._rng = random.Random(seed)
    rk._ground.clear(); rk._mats.clear(); rk._clear.clear(); rk._rooms.clear()
    w = bpy.data.worlds.new("World"); sc.world = w; w.use_nodes = True
    af.init(OUT, pk.link)
    return ARGS


def link(o): return pk.link(o)


# ----------------------------------------------------------------------------- materials
def mat(name, color, kind="plaster", rough=None, emission=0.0, emission_color=None):
    return rk.mat(name, color, kind, rough, emission, emission_color)


def stone_mat(name, base, dark=None, lichen=None, scale=1.0, rough=0.88, bump=0.6, kind="limestone"):
    """Weathered stone: two noise scales of colour, voronoi pits and fine cracks, darker grime low down and in the
    pits, optional lichen spots; object-space, so joined objects keep it (world-aligned in practice: origins at 0)."""
    m = bpy.data.materials.new("M_" + name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); b = N("ShaderNodeBsdfPrincipled"); L(b.outputs["BSDF"], out.inputs["Surface"])
    tc = N("ShaderNodeTexCoord")
    def noi(sc_, det=6.0, dist=0.0):
        n = N("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = sc_ * scale; n.inputs["Detail"].default_value = det
        n.inputs["Distortion"].default_value = dist; L(tc.outputs["Object"], n.inputs["Vector"]); return n
    n1 = noi(1.3, 6, 0.3); n2 = noi(9.0, 8); n3 = noi(0.25, 3)
    vo = N("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 14.0 * scale; L(tc.outputs["Object"], vo.inputs["Vector"])
    vc = N("ShaderNodeTexVoronoi"); vc.feature = 'DISTANCE_TO_EDGE'; vc.inputs["Scale"].default_value = 3.5 * scale; L(n1.outputs["Color"], vc.inputs["Vector"])
    c0 = Vector(rk.lin(base)); cd = Vector(rk.lin(dark)) if dark else c0 * 0.55
    ramp = N("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
    e[0].position = 0.25; e[0].color = tuple(c0 * 0.78) + (1,); e[1].position = 0.75; e[1].color = tuple(Vector([min(1, x * 1.12) for x in c0])) + (1,)
    L(n1.outputs["Fac"], ramp.inputs["Fac"])
    col = ramp.outputs["Color"]
    def mix(a, bcol, fac, blend='MIX'):
        mx = N("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = blend
        L(fac, mx.inputs["Factor"]); L(a, mx.inputs["A"])
        if isinstance(bcol, tuple): mx.inputs["B"].default_value = bcol
        else: L(bcol, mx.inputs["B"])
        return mx.outputs["Result"]
    # broad patches
    pr = N("ShaderNodeMapRange"); pr.inputs["From Min"].default_value = 0.4; pr.inputs["From Max"].default_value = 0.7; pr.inputs["To Max"].default_value = 0.5
    L(n3.outputs["Fac"], pr.inputs["Value"]); col = mix(col, tuple(cd) + (1,), pr.outputs["Result"])
    # pits
    pt = N("ShaderNodeMapRange"); pt.inputs["From Min"].default_value = 0.0; pt.inputs["From Max"].default_value = 0.12; pt.inputs["To Min"].default_value = 0.6; pt.inputs["To Max"].default_value = 0.0
    L(vo.outputs["Distance"], pt.inputs["Value"]); col = mix(col, tuple(cd * 0.7) + (1,), pt.outputs["Result"])
    # cracks
    ck = N("ShaderNodeMapRange"); ck.inputs["From Min"].default_value = 0.0; ck.inputs["From Max"].default_value = 0.012; ck.inputs["To Min"].default_value = 0.45; ck.inputs["To Max"].default_value = 0.0
    L(vc.outputs["Distance"], ck.inputs["Value"]); col = mix(col, tuple(cd * 0.75) + (1,), ck.outputs["Result"])
    if lichen:
        nl = noi(3.0, 4); lr = N("ShaderNodeMapRange"); lr.inputs["From Min"].default_value = 0.62; lr.inputs["From Max"].default_value = 0.68; lr.inputs["To Max"].default_value = 0.85
        L(nl.outputs["Fac"], lr.inputs["Value"]); col = mix(col, tuple(rk.lin(lichen)) + (1,), lr.outputs["Result"])
    # grime low down
    sp = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sp.inputs["Vector"])
    gr = N("ShaderNodeMapRange"); gr.inputs["From Min"].default_value = -0.4; gr.inputs["From Max"].default_value = 0.35; gr.inputs["To Min"].default_value = 0.0; gr.inputs["To Max"].default_value = 0.0
    col = col
    L(col, b.inputs["Base Color"])
    rr = N("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = rough - 0.08; rr.inputs["To Max"].default_value = min(1, rough + 0.08)
    L(n2.outputs["Fac"], rr.inputs["Value"]); L(rr.outputs["Result"], b.inputs["Roughness"])
    hb = N("ShaderNodeMath"); hb.operation = 'ADD'; L(n2.outputs["Fac"], hb.inputs[0]); L(ck.outputs["Result"], hb.inputs[1])
    bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = 0.01
    hn = N("ShaderNodeMath"); hn.operation = 'SUBTRACT'; L(hb.outputs[0], hn.inputs[0]); L(pt.outputs["Result"], hn.inputs[1])
    L(hn.outputs[0], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    m["base"] = list(c0)
    rk._mats[name] = m
    return m


def patchy_mat(name, base, patches=(), rough=0.92, bump=0.3, scale=1.0):
    """Ground that is not uniform: a base colour with fine noise, and patches [(colour, noise scale per m, coverage 0-1)]
    laid over it (dry grass, scrub, bare rock, trodden earth)."""
    m = bpy.data.materials.new("M_" + name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); b = N("ShaderNodeBsdfPrincipled"); L(b.outputs["BSDF"], out.inputs["Surface"])
    tc = N("ShaderNodeTexCoord")
    c0 = Vector(rk.lin(base))
    n0 = N("ShaderNodeTexNoise"); n0.inputs["Scale"].default_value = 3.0 * scale; n0.inputs["Detail"].default_value = 8; L(tc.outputs["Object"], n0.inputs["Vector"])
    ramp = N("ShaderNodeValToRGB"); e = ramp.color_ramp.elements
    e[0].position = 0.3; e[0].color = tuple(c0 * 0.8) + (1,); e[1].position = 0.7; e[1].color = tuple(Vector([min(1, x * 1.15) for x in c0])) + (1,)
    L(n0.outputs["Fac"], ramp.inputs["Fac"]); col = ramp.outputs["Color"]
    for i, (pc, sc_, cov) in enumerate(patches):
        n = N("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = sc_; n.inputs["Detail"].default_value = 5; n.inputs["Roughness"].default_value = 0.65
        n.noise_dimensions = '4D'; n.inputs["W"].default_value = i * 3.7; L(tc.outputs["Object"], n.inputs["Vector"])
        mr = N("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 1.0 - cov - 0.03; mr.inputs["From Max"].default_value = 1.0 - cov + 0.05
        L(n.outputs["Fac"], mr.inputs["Value"])
        nm = N("ShaderNodeMix"); nm.data_type = 'RGBA'; L(mr.outputs["Result"], nm.inputs["Factor"]); L(col, nm.inputs["A"])
        pm = N("ShaderNodeMix"); pm.data_type = 'RGBA'; pm.blend_type = 'MULTIPLY'; pm.inputs["Factor"].default_value = 1.0
        pm.inputs["A"].default_value = rk.lin(pc) + (1,); L(n0.outputs["Color"], pm.inputs["B"])
        bri = N("ShaderNodeMix"); bri.data_type = 'RGBA'; bri.inputs["Factor"].default_value = 0.6; bri.inputs["A"].default_value = rk.lin(pc) + (1,)
        L(pm.outputs["Result"], bri.inputs["B"])
        L(bri.outputs["Result"], nm.inputs["B"]); col = nm.outputs["Result"]
    L(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = 0.02
    n2 = N("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 25.0; L(tc.outputs["Object"], n2.inputs["Vector"])
    L(n2.outputs["Fac"], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    m["base"] = list(c0); rk._mats[name] = m
    return m


def scrub(B, m, centre, radius, height, seed=0):
    """A low distant bush: a squashed, noise-pushed icosahedron (20-80 tris), sitting into the ground."""
    rk._lump(B, m, (centre[0], centre[1], centre[2] + height * 0.35), radius, (1.0, 1.0, height / radius), seed, sub=0, rough=0.35)


def ashlar_mat(name, base, block=(0.05, 0.025), mortar=(0.70, 0.66, 0.58), rough=0.82, joint=0.04, var=0.10, dark_low=True, floor=False):
    """Hewn stone at 1/12: brick-texture coursing on the wall plane (along the wall, height), each block a little
    different in tone, fine noise, grime toward the ground."""
    m = bpy.data.materials.new("M_" + name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); b = N("ShaderNodeBsdfPrincipled"); L(b.outputs["BSDF"], out.inputs["Surface"])
    tc = N("ShaderNodeTexCoord"); sp = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sp.inputs["Vector"])
    ad = N("ShaderNodeMath"); ad.operation = 'ADD'; L(sp.outputs["X"], ad.inputs[0]); L(sp.outputs["Y"], ad.inputs[1])
    cb = N("ShaderNodeCombineXYZ")
    if floor: L(sp.outputs["X"], cb.inputs["X"]); L(sp.outputs["Y"], cb.inputs["Y"])
    else: L(ad.outputs[0], cb.inputs["X"]); L(sp.outputs["Z"], cb.inputs["Y"])
    bt = N("ShaderNodeTexBrick"); L(cb.outputs["Vector"], bt.inputs["Vector"])
    bt.inputs["Scale"].default_value = 1.0; bt.inputs["Mortar Size"].default_value = block[1] * joint
    bt.inputs["Brick Width"].default_value = block[0]; bt.inputs["Row Height"].default_value = block[1]
    bt.offset = 0.5; bt.squash = 1.0
    c0 = rk.lin(base)
    bt.inputs["Color1"].default_value = tuple(x * (1 - var) for x in c0) + (1,)
    bt.inputs["Color2"].default_value = tuple(min(1, x * (1 + var * 0.6)) for x in c0) + (1,)
    bt.inputs["Mortar"].default_value = rk.lin(mortar) + (1,)
    bt.inputs["Bias"].default_value = 0.0
    n1 = N("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 30.0; n1.inputs["Detail"].default_value = 6
    L(tc.outputs["Object"], n1.inputs["Vector"])
    mx = N("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs["Factor"].default_value = 0.35
    L(bt.outputs["Color"], mx.inputs["A"]); L(n1.outputs["Color"], mx.inputs["B"])
    col = mx.outputs["Result"]
    n2 = N("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 2.0; n2.inputs["Detail"].default_value = 3
    L(tc.outputs["Object"], n2.inputs["Vector"])
    mr = N("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.45; mr.inputs["From Max"].default_value = 0.7; mr.inputs["To Max"].default_value = 0.25
    L(n2.outputs["Fac"], mr.inputs["Value"])
    m2 = N("ShaderNodeMix"); m2.data_type = 'RGBA'; L(mr.outputs["Result"], m2.inputs["Factor"]); L(col, m2.inputs["A"])
    m2.inputs["B"].default_value = tuple(x * 0.72 for x in c0) + (1,); col = m2.outputs["Result"]
    if dark_low:
        gr = N("ShaderNodeMapRange"); gr.inputs["From Min"].default_value = 0.0; gr.inputs["From Max"].default_value = 0.25
        gr.inputs["To Min"].default_value = 0.35; gr.inputs["To Max"].default_value = 0.0; L(sp.outputs["Z"], gr.inputs["Value"])
        m3 = N("ShaderNodeMix"); m3.data_type = 'RGBA'; m3.blend_type = 'MULTIPLY'; L(gr.outputs["Result"], m3.inputs["Factor"])
        L(col, m3.inputs["A"]); m3.inputs["B"].default_value = (0.55, 0.52, 0.47, 1); col = m3.outputs["Result"]
    L(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5; bp.inputs["Distance"].default_value = 0.002; bp.invert = True
    L(bt.outputs["Fac"], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    m["base"] = list(c0); rk._mats[name] = m
    return m


def emit_mat(name, color, strength):
    m = bpy.data.materials.new("M_" + name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = rk.lin(color) + (1,); e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs["Emission"], o.inputs["Surface"])
    m["emit_only"] = 1
    return m


def keep(material, living_name, size=None):
    """After the merge, the object of this material is named living_name (veg.*, cloth.*, water.*)."""
    KEEP[material.name] = living_name
    if size: SIZE[material.name] = size


def size(material, base, rough=None):
    SIZE[material.name] = (base,) if rough is None else (base, rough)


# ----------------------------------------------------------------------------- ground
def polar_terrain(name, h, material, centre=(0.0, 0.0), r_max=800.0, near_step=0.6, k=0.12, ns=72, r_min=0.0):
    """Ground as rings round the reader: fine near them, coarse far away (the reader never walks). h(x, y) -> z.
    Registers itself with roomkit.ground()."""
    cx, cy = centre; rs = [r_min] if r_min > 0 else [0.0]
    while rs[-1] < r_max:
        r = rs[-1]; rs.append(r + max(near_step, r * k))
    bm = bmesh.new(); rings = []
    if rs[0] == 0.0:
        c = bm.verts.new((cx, cy, h(cx, cy))); start = 1
    else:
        c = None; start = 0
    for r in rs[start:]:
        ring = []
        for i in range(ns):
            a = 2 * math.pi * (i + 0.5 * (len(rings) % 2)) / ns
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            ring.append(bm.verts.new((x, y, h(x, y))))
        rings.append(ring)
    if c is not None:
        for i in range(ns): bm.faces.new((c, rings[0][i], rings[0][(i + 1) % ns]))
    for a_, b_ in zip(rings, rings[1:]):
        for i in range(ns):
            bm.faces.new((a_[i], b_[i], b_[(i + 1) % ns], a_[(i + 1) % ns]))
    o = rk._obj(name, bm, material, smooth=True)
    rk._ground.append(lambda x, y: h(x, y) if math.hypot(x - cx, y - cy) <= r_max else None)
    return o


def fbm(x, y, s, oct=4, off=0.0):
    return noise.fractal(Vector((x / s + off, y / s + off * 0.7, off * 0.3)), 0.55, 2.0, oct)


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)


def water_plane(name, material, z, radius=900.0, centre=(0.0, 0.0), rings=10, ns=48, foam=None):
    """A flat water disc (water.ocean.* etc.) with vertex colour G = foam from foam(x, y) (0 by default)."""
    bm = bmesh.new(); rs = [radius * (i / rings) ** 2 for i in range(1, rings + 1)]
    c = bm.verts.new((centre[0], centre[1], z)); prev = None; allv = [c]
    for r in rs:
        ring = [bm.verts.new((centre[0] + r * math.cos(2 * math.pi * i / ns), centre[1] + r * math.sin(2 * math.pi * i / ns), z)) for i in range(ns)]
        if prev is None:
            for i in range(ns): bm.faces.new((c, ring[i], ring[(i + 1) % ns]))
        else:
            for i in range(ns): bm.faces.new((prev[i], ring[i], ring[(i + 1) % ns], prev[(i + 1) % ns]))
        prev = ring; allv += ring
    o = rk._obj(name, bm, material, smooth=True)
    me = o.data; ca = me.color_attributes.new("foam", 'BYTE_COLOR', 'POINT')
    col = np.ones((len(me.vertices), 4), np.float32); col[:, 1] = 0.0
    if foam:
        for i, v in enumerate(me.vertices): col[i, 1] = max(0.0, min(1.0, foam(v.co.x, v.co.y)))
    ca.data.foreach_set("color", col.ravel()); me.color_attributes.active_color = ca
    o["living_keep_colour"] = 1
    return o


def rough_block(B, m, size, loc, rot=(0, 0, 0), amp=0.018, seed=0, cuts=1, bevel=0.03):
    """A hewn stone: a box cut along each edge, its corners and edges knocked about by noise (chipped arrises,
    uneven faces). size (x, y, z), base centre at loc (B's local frame), rot in degrees."""
    t = bmesh.new(); bmesh.ops.create_cube(t, size=1.0)
    if cuts: bmesh.ops.subdivide_edges(t, edges=list(t.edges), cuts=cuts, use_grid_fill=True)
    o = Vector((seed * 3.1, seed * 1.7, seed * 0.3)); T = _mx_(loc, rot)
    for v in t.verts:
        n = v.co.copy()
        p = Vector((n.x * size[0], n.y * size[1], (n.z + 0.5) * size[2]))
        d = noise.noise(p * 4.0 + o) * amp + noise.noise(p * 11.0 + o) * amp * 0.4
        edge = (abs(n.x) > 0.49) + (abs(n.y) > 0.49) + (abs(n.z) > 0.49)
        k = 1.6 if edge >= 2 else 1.0
        nn = n.normalized()
        p += nn * d * k - (nn * amp * 0.7 if edge >= 3 else Vector())
        v.co = T @ p
    vs = [tuple(v.co) for v in t.verts]; fs = [tuple(v.index for v in f.verts) for f in t.faces]; t.free()
    B.mesh(m, vs, fs)


def _mx_(loc, rot):
    return Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot]).to_matrix().to_4x4()


# ----------------------------------------------------------------------------- foliage
_LEAF = {}


def leaf_mat(kind, seed=7, palette=None, name=None, per_cell=3):
    """A painted leaf-spray atlas material of one kind (lime, beech, oak, privet, yew, rose); palette overrides the
    kind's colours (e.g. a grey-green olive from the privet's opposite-leaved sprays)."""
    key = name or kind
    if key in _LEAF: return _LEAF[key]
    old = af.PALETTES[kind]
    if palette: af.PALETTES[kind] = palette
    img = af.spray_atlas("A_" + key, kind, seed, S=1024, per_cell=per_cell)
    af.PALETTES[kind] = old
    m = af.image_mat("M_leaf_" + key, img, rough=0.62, alpha=True, translucency=0.06)
    pk.IMAGE_MATS.add(m.name)
    _LEAF[key] = m
    return m


def tree(name, base, height, spread, bark, leaves, seed=0, trunk_frac=0.42, r0=None, nlimbs=6, detail=1.0, card=1.0,
         fill=50, lobes=5, flat=0.75, lean=(0.0, 0.0), sway0=0.3, branch_per_limb=4, cards_per_tip=2):
    """A branching tree with leaf cards: trunk to trunk_frac of the height, a lobed crown above (spread = crown
    radius). Grounded at roomkit.ground(base)."""
    R = random.Random(seed)
    z = rk.ground(base[0], base[1]) if len(base) == 2 else base[2]
    b = Vector((base[0], base[1], z))
    top = b + Vector((lean[0] * height, lean[1] * height, height * trunk_frac))
    crown = af.auto_crown(R, top, height * (1 - trunk_frac), spread, nlobes=lobes, flat=flat)
    return af.grow_tree(name, R, b, crown, bark, leaves, top, r0 or height * 0.03, nlimbs=nlimbs, detail=detail,
                        card_size=card, fill=fill, sway0=sway0, branch_per_limb=branch_per_limb, cards_per_tip=cards_per_tip)


def shrub(name, base, radius, height, bark, leaves, seed=0, card=0.45, fill=30):
    """A low many-stemmed bush: short stems from the ground into a squat crown of leaf cards."""
    R = random.Random(seed)
    z = rk.ground(base[0], base[1]); b = Vector((base[0], base[1], z))
    crown = af.Crown([(b + Vector((0, 0, height * 0.55)), (radius, radius * 0.9, height * 0.5)),
                      (b + Vector((radius * 0.4, -radius * 0.2, height * 0.45)), (radius * 0.7, radius * 0.6, height * 0.4))])
    limbs = []
    for i in range(5):
        a = R.uniform(0, 6.283); d = Vector((math.cos(a), math.sin(a), 0))
        limbs.append((b + d * 0.05, b + d * radius * R.uniform(0.5, 0.8) + Vector((0, 0, height * R.uniform(0.6, 0.95))), 0.025, 0.008))
    return af.grow_tree(name, R, b, crown, bark, leaves, b + Vector((0, 0, 0.1)), 0.03, limbs=limbs, detail=0.7, card_size=card,
                        fill=fill, flare=False, sway0=0.15, branch_per_limb=2, cards_per_tip=2)


def grass_cards(name, area, count, height, material, seed=0, avoid=(), near=None, near_k=0.0, clusters=0, spread=1.2):
    """Clumps of crossed grass-blade cards (painted atlas) over area (x0, y0, x1, y1), on the ground, with sway."""
    R = random.Random(seed); mb = af.MB()
    x0, y0, x1, y1 = area; placed = 0; tries = 0
    while placed < count and tries < count * 20:
        tries += 1
        if clusters:
            if tries == 1: cs = [(R.uniform(x0, x1), R.uniform(y0, y1)) for _ in range(clusters)]
            cx_, cy_ = R.choice(cs); x, y = cx_ + R.gauss(0, spread), cy_ + R.gauss(0, spread)
        else:
            x, y = R.uniform(x0, x1), R.uniform(y0, y1)
        if any(math.hypot(x - ax, y - ay) < ar for ax, ay, ar in avoid): continue
        if near is not None and R.random() < near_k * min(1.0, math.hypot(x - near[0], y - near[1]) / 20.0): continue
        z = rk.ground(x, y); h = height * R.uniform(0.6, 1.3); w = h * R.uniform(0.9, 1.4)
        for k in range(2):
            a = R.uniform(0, math.pi) + k * math.pi / 2
            right = Vector((math.cos(a), math.sin(a), 0)) * w
            up = Vector((R.gauss(0, 0.12), R.gauss(0, 0.12), 1.0)) * h
            af.card(mb, Vector((x, y, z - 0.02)), right, up, R.choice(af.QUAD), 0.0, 1.0)
        placed += 1
    return mb.build(name, material, sway=True, normals=lambda p: Vector((0, 0, 1)))


def grass_atlas_mat(name, palette, seed=3, dry=0.0):
    """A 2x2 atlas of grass tufts: many thin blades fanning from the bottom middle of each cell."""
    S = 1024; cv = pk.Canvas(S, S); R = random.Random(seed); h = S // 2
    for (cx, cy) in ((0, 0), (h, 0), (0, h), (h, h)):
        cv.clip = (cx + 1, cy + 1, cx + h - 1, cy + h - 1)
        for i in range(70):
            bx = cx + h * 0.5 + R.gauss(0, h * 0.09); by = cy + h - 2
            a = R.gauss(0, 0.32); L = h * R.uniform(0.35, 0.95)
            col = R.choice(palette)
            if R.random() < dry: col = (0.55, 0.50, 0.33)
            k = R.uniform(0.75, 1.15); col = tuple(min(1, c * k) for c in col)
            px, py = bx, by; segs = 5; ang = a
            for s in range(segs):
                ang += a * 0.25 + R.gauss(0, 0.04)
                nx = px + math.sin(ang) * L / segs; ny = py - math.cos(ang) * L / segs
                wd = 3.2 * (1 - s / segs) + 0.6
                cv.line((px, py), (nx, ny), wd, wd * 0.8, col + (1.0,))
                px, py = nx, ny
    cv.clip = None; cv.bleed(6)
    img = af.np_image("A_" + name, cv.a)
    m = af.image_mat("M_" + name, img, rough=0.8, alpha=True, translucency=0.05)
    pk.IMAGE_MATS.add(m.name)
    return m


# ----------------------------------------------------------------------------- living-scene markers
def fx(kind, tag, loc, radius):
    """fx.fire / fx.candle / fx.torch / fx.lantern empty with the radius custom property (export_extras)."""
    e = bpy.data.objects.new(f"fx.{kind}.{tag}", None); e.empty_display_type = 'SPHERE'; e.empty_display_size = radius
    e.location = loc; e["radius"] = float(radius); link(e)
    return e


def sound(kind, tag, loc):
    return pk.sound(kind, tag, loc)


def anchor(aid, loc):
    return pk.anchor(aid, loc)


def reader(entrance, look_xy, eye=1.55, look_z=None):
    """anchor.reader.entrance on the floor, anchor.reader.look at eye height toward look_xy (or look_z)."""
    x, y = entrance[0], entrance[1]; z = entrance[2] if len(entrance) > 2 else rk.ground(x, y)
    a = anchor("reader.entrance", (x, y, z))
    d = Vector((look_xy[0] - x, look_xy[1] - y, 0)).normalized()
    lz = z + eye if look_z is None else look_z
    b = anchor("reader.look", (x + d.x * 1.0, y + d.y * 1.0, lz))
    anchor("scene.centre", (x, y, z))
    rk.READER.update(entrance=Vector((x, y, z)), look=Vector(b.location), eye=eye)
    return Vector((x, y, z)), d


def check_reader():
    """The reader needs open floor: 1.5 m clear ahead and 0.4 m around (rays at knee, waist and eye height)."""
    e = rk.READER["entrance"]; lk = rk.READER["look"]; d = Vector((lk.x - e.x, lk.y - e.y, 0)).normalized()
    sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get(); probs = []
    for hz in (0.3, 0.9, 1.55):
        o = e + Vector((0, 0, hz))
        hit, loc, *_ = sc.ray_cast(dg, o, d, distance=1.5)
        if hit: probs.append(f"blocked ahead at h={hz}: {(loc - o).length:.2f} m")
        for k in range(12):
            a = 2 * math.pi * k / 12; v = Vector((math.cos(a), math.sin(a), 0))
            hit, loc, *_ = sc.ray_cast(dg, o, v, distance=0.4)
            if hit: probs.append(f"blocked around at h={hz} dir {k * 30} deg: {(loc - o).length:.2f} m")
    hit, loc, *_ = sc.ray_cast(dg, e + Vector((0, 0, 1.0)), Vector((0, 0, -1)), distance=2.0)
    if not hit: probs.append("no floor under the reader")
    elif abs(loc.z - e.z) > 0.08: probs.append(f"floor under the reader at {loc.z:.2f}, anchor at {e.z:.2f}")
    print("READER CHECK", "ok" if not probs else probs, flush=True)
    return probs


# ----------------------------------------------------------------------------- lights
def sun(elevation, azimuth, strength=4.0, color=(1.0, 0.95, 0.86), softness=1.5):
    return rk.sun(elevation, azimuth, strength, color, softness)


def point(name, loc, power, color=(1.0, 0.75, 0.45), radius=0.05, shadow=True):
    o = rk.lamp(name, loc, power, color, radius)
    o.data.use_shadow = shadow
    return o


def area(name, loc, size, power, color=(0.9, 0.95, 1.0), aim=(0, 0, -1)):
    return rk.area_light(name, loc, size, power, color, aim)


def sky(zenith, horizon, strength=1.0, radius=600.0, ground_color=None):
    return rk.sky(zenith, horizon, strength, radius, ground_color)


# ----------------------------------------------------------------------------- cameras and stills
def cam(view, loc, look_at, lens=18):
    c = pk.camera("CAM_" + view, loc, look_at, lens)
    c.data.clip_end = 1200
    CAMS.append(c)
    return c


def reader_cams(extra_left=70, extra_right=-70, behind=True, lens=18, eye=1.55):
    """The reader view plus left, right and behind, from the reading position."""
    e = rk.READER["entrance"]; lk = rk.READER["look"]
    eye_p = e + Vector((0, 0, eye)); d = Vector((lk.x - e.x, lk.y - e.y, 0)).normalized()
    pitch = (lk.z - eye_p.z)
    cam("reader", eye_p, eye_p + d * 4 + Vector((0, 0, pitch * 4)), lens)
    for v, a in (("left", extra_left), ("right", extra_right)) + ((("behind", 180),) if behind else ()):
        r = Matrix.Rotation(math.radians(a), 3, 'Z') @ d
        cam(v, eye_p, eye_p + r * 4 + Vector((0, 0, -0.3)), lens)


def render():
    cap = os.path.join(REPO, "captures", "blender", ID) if bpy.context.scene.cycles.samples >= 32 else ""
    return pk.render_stills(CAMS, captures_dir=cap)


def budget():
    return pk.print_budget()


# ----------------------------------------------------------------------------- export
def pipeline_doc():
    p = os.path.join(REPO, "docs", "SCENE_ROOMS_PIPELINE.md")
    return p if os.path.exists(p) else None


def export(default_size=256):
    """Join by material, bake procedural materials to textures, keep painted atlases and living names, export."""
    sc = bpy.context.scene; COLL = pk.COLL
    gltf_name = ID.replace("-", "_") + ".gltf"
    for c in CAMS:
        if c.name in bpy.data.objects: bpy.data.objects.remove(c)
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.select_all(action='DESELECT')
    groups = {}
    for o in COLL.objects:
        if o.type != 'MESH' or not o.data.materials or not o.data.polygons: continue
        groups.setdefault(o.data.materials[0].name, []).append(o)
    merged = []
    for mname, objs in groups.items():
        kn = KEEP.get(mname)
        if mname in pk.IMAGE_MATS and not kn:
            kn = ("veg.leaves." if "leaf" in mname else "veg.grass.") + mname[2:]
        living = bool(kn) and kn.split(".")[0] in ("veg", "cloth", "water")
        attr = "foam" if kn and kn.startswith("water.") else "sway"
        for o in objs:
            if not living:
                for an in [a.name for a in o.data.color_attributes]: o.data.color_attributes.remove(o.data.color_attributes[an])
            else:
                if attr not in o.data.color_attributes:
                    ca = o.data.color_attributes.new(attr, 'BYTE_COLOR', 'POINT')
                    ca.data.foreach_set("color", np.tile(np.array([0, 0, 1, 1] if attr == "foam" else [0, 1, 1, 1], np.float32), len(o.data.vertices)))
                for an in [a.name for a in o.data.color_attributes if a.name != attr]: o.data.color_attributes.remove(o.data.color_attributes[an])
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active
        o.name = "SkyDome" if mname == "M_SkyDome" else (kn or "MESH_" + mname[2:])
        o.data.name = o.name
        if living and attr in o.data.color_attributes:
            o.data.color_attributes.active_color = o.data.color_attributes[attr]
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    sc.cycles.samples = 1; sc.cycles.device = 'CPU'
    sc.render.bake.margin = 6
    tdir = os.path.join(OUT, "textures"); os.makedirs(tdir, exist_ok=True)
    for o in merged:
        m = o.data.materials[0]; nt = m.node_tree
        if m.name in pk.IMAGE_MATS: continue
        emit_only = bool(m.get("emit_only")) or o.name == "SkyDome"
        area_ = sum(p.area for p in o.data.polygons)
        auto = 1 << max(6, min(10, int(math.log2(max(64, math.sqrt(area_) * 48)) + 0.5)))
        sizes = SIZE.get(m.name, (auto, max(64, auto // 4)))
        if emit_only: sizes = sizes[:1]
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        while o.data.uv_layers: o.data.uv_layers.remove(o.data.uv_layers[0])
        o.data.uv_layers.new(name="UVMap")
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
        bpy.ops.object.mode_set(mode='OBJECT')
        passes = [("BaseColor", 'EMIT' if emit_only else 'DIFFUSE', {} if emit_only else {"pass_filter": {'COLOR'}}, False),
                  ("Roughness", 'ROUGHNESS', {}, True)][:len(sizes)]
        baked = {}
        metal0 = 0.0
        if bsdf is not None:
            # the diffuse-colour pass of a metallic surface is black: bake the albedo as a dielectric
            for l in list(bsdf.inputs["Metallic"].links): nt.links.remove(l)
            metal0 = bsdf.inputs["Metallic"].default_value; bsdf.inputs["Metallic"].default_value = 0.0
        for (pn, bt, extra, noncolor), sz in zip(passes, sizes):
            img = bpy.data.images.new(f"T_{m.name[2:]}_{pn}", sz, sz, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            for n in nt.nodes: n.select = False
            tex.select = True; nt.nodes.active = tex
            bpy.ops.object.bake(type=bt, margin=6, use_clear=True, **extra)
            img.filepath_raw = os.path.join(tdir, img.name + ".png"); img.file_format = 'PNG'; img.save(); img.pack()
            baked[pn] = tex
        metallic = metal0 if bsdf else 0.0
        rough_v = bsdf.inputs["Roughness"].default_value if bsdf else 0.9
        emis = bsdf.inputs["Emission Strength"].default_value if bsdf else 0.0
        ecol = tuple(bsdf.inputs["Emission Color"].default_value) if bsdf else (1, 1, 1, 1)
        for n in list(nt.nodes):
            if n not in baked.values(): nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
        nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Base Color"])
        if "Roughness" in baked: nt.links.new(baked["Roughness"].outputs["Color"], nb.inputs["Roughness"])
        else: nb.inputs["Roughness"].default_value = rough_v
        nb.inputs["Metallic"].default_value = metallic
        if emit_only:
            nb.inputs["Emission Strength"].default_value = 1.0; nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"])
        elif emis > 0:
            nb.inputs["Emission Strength"].default_value = min(emis, 4.0); nb.inputs["Emission Color"].default_value = ecol
        print("baked", o.name, sizes, flush=True)
    gl = os.path.join(OUT, gltf_name)
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=86, export_lights=True,
                              export_cameras=False, export_extras=True, export_vertex_color='ACTIVE', export_all_vertex_colors=False)
    pk.patch_sun_intensities(gl)
    with open(gl) as f: g = json.load(f)
    tris = sum(pk.tri_count(o) for o in merged if o.name != "SkyDome")
    used = set(im.get("uri") for im in g.get("images", []))
    tex_bytes = sum(os.path.getsize(os.path.join(OUT, u)) for u in used if u and os.path.exists(os.path.join(OUT, u)))
    binb = sum(os.path.getsize(os.path.join(OUT, b["uri"])) for b in g.get("buffers", []) if os.path.exists(os.path.join(OUT, b.get("uri", ""))))
    # drop leftover PNG bake files the glTF does not use
    for f in os.listdir(tdir):
        if "textures/" + f not in used: os.remove(os.path.join(tdir, f))
    stats = dict(gltf=os.path.relpath(gl, REPO), meshes=len(merged), tris=tris, textures_mb=round(tex_bytes / 1e6, 2), bin_mb=round(binb / 1e6, 2),
                 nodes=sorted(n.get("name", "") for n in g.get("nodes", []) if not n.get("name", "").startswith("MESH_")))
    with open(os.path.join(OUT, "export_stats.json"), "w") as f: json.dump(stats, f, indent=1)
    print("EXPORT", json.dumps(stats), flush=True)
    # the runtime bake (blender/runtime_bake.py, docs/SCENE_ROOMS_PIPELINE.md) starts from this: merged, albedo baked, lights kept
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, gltf_name.replace(".gltf", "_baked.blend")))
    return gl


def finish(render_it=None, export_it=None):
    """Budget print, reader check, stills (--render), export (--export)."""
    budget(); check_reader()
    if ARGS.render if render_it is None else render_it: render()
    if ARGS.export if export_it is None else export_it: export()
