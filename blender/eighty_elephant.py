"""
Fable: Kiouni, the Asian elephant of Around the World in Eighty Days (chapters 11-13), for build_pillaji_forest.py.

An adult male Asian elephant (Elephas maximus indicus) standing at rest, about 2.7 m at the shoulder: the back
convex and highest at the middle, the twin domes of the head with the dent between them, the small, fold-topped ears
(their edges rolled, the lower lobe pointed), the trunk hanging with its single finger at the tip and a slight curl,
short tushes rather than long tusks, pillar legs with broad round feet, five nails on the fore feet and four behind,
a long tail with a tuft. The skin is grey-brown, wrinkled, dusted with red earth below the knees, and freckled with the
pink depigmentation Asian elephants show on the trunk, the forehead and the ear edges.

On his back, as the book has it: "a sort of saddle-cloth, to which were attached on each side some curiously
uncomfortable howdahs" - a quilted red-and-gold saddle-cloth (jhool) over a pad, held by girths and a crupper, with a
wooden pannier-seat hung on each flank.

Built from metaballs (one smooth skin), converted to a mesh, remeshed and decimated to the triangle budget; the
saddle-cloth and girths are shrink-wrapped onto that skin. Local frame: the elephant faces +X, standing on z = 0.
"""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Quaternion, noise
import pride_kit as K
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       plain, noisy, box, sphere, lathe, tube, mesh_from, link)


def skin_mat(name="M_ElephantSkin"):
    """grey-brown hide: large-scale tonal variation, deep criss-cross wrinkles (ridged noise and cells), red dust on the
    legs and belly, pink-freckled depigmentation on the trunk base, the forehead and the ear rims (attribute 'pink'),
    a dull, dry sheen."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1800, -600)); z = s.outputs["Z"]
    n = noise_(nt, co, 1.3, 5, 0.6, loc=(-1500, 300))
    base = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1300, 300)), c4(K.srgb((0.25, 0.245, 0.24))), c4(K.srgb((0.33, 0.315, 0.30))), (-1100, 300))
    # wrinkles: two scales of distorted cells, darker in the creases
    w1 = voronoi_(nt, co, 22.0, 'DISTANCE_TO_EDGE', (-1500, 0))
    w2 = noise_(nt, co, 28.0, 6, 0.72, distortion=3.0, loc=(-1500, -200))
    crease = math_(nt, 'MAXIMUM', maprange(nt, w1.outputs["Distance"], 0.0, 0.035, 0.45, 0, (-1300, 0)), maprange(nt, w2.outputs["Fac"], 0.56, 0.62, 0, 0.7, (-1300, -200)), (-1150, -100))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', crease, 0.55, (-1000, -100)), base, (0.35, 0.33, 0.32, 1), (-900, 200))
    # depigmentation (pink freckles) where the attribute 'pink' says
    pa = node(nt, "ShaderNodeAttribute", (-1500, -500)); pa.attribute_name = "pink"
    fr = noise_(nt, co, 40.0, 3, 0.6, loc=(-1500, -700))
    freck = math_(nt, 'MULTIPLY', pa.outputs["Fac"], maprange(nt, fr.outputs["Fac"], 0.45, 0.55, 0, 1, (-1300, -700)), (-1100, -600))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', freck, 0.7, (-1000, -600)), col, c4(K.srgb((0.58, 0.46, 0.41))), (-700, 200))
    # red dust low on the legs and under the belly
    dn = noise_(nt, co, 3.0, 4, 0.6, loc=(-1500, -900))
    dust = math_(nt, 'MULTIPLY', maprange(nt, z, 0.9, 0.2, 0, 1, (-1300, -900)), maprange(nt, dn.outputs["Fac"], 0.3, 0.6, 0.4, 0.9, (-1300, -1050)), (-1100, -950))
    col = mix_rgb(nt, 'MIX', dust, col, c4(K.srgb((0.40, 0.30, 0.22))), (-500, 200))
    col = K.ao_mul(nt, col, 0.25, 0.5, (-350, -900))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, crease, 0, 1, 0.62, 0.85, (-400, -300)), b.inputs["Roughness"])
    b.inputs["Sheen Weight"].default_value = 0.15
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', crease, -1.0, (-700, -1200)), math_(nt, 'MULTIPLY', w2.outputs["Fac"], 0.3, (-700, -1300)), (-550, -1250)), 0.55, 0.012)
    return m


def jhool_mat(name="M_SaddleCloth"):
    """the saddle-cloth: a madder-red quilted cotton with a broad border of gold-yellow braid and a green inner band
    (world z decides the border: the cloth's lower edge is near HEM_Z), stitched in a lozenge quilting."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1800, 0)); z = s.outputs["Z"]
    q = node(nt, "ShaderNodeVectorRotate", (-1600, -300), rotation_type='X_AXIS'); q.inputs["Angle"].default_value = 0.0
    nt.links.new(co, q.inputs["Vector"])
    mp = node(nt, "ShaderNodeMapping", (-1450, -300)); mp.inputs["Rotation"].default_value = (0, 0, 0.785); mp.inputs["Scale"].default_value = (9, 9, 9)
    nt.links.new(q.outputs[0], mp.inputs["Vector"])
    sp = sep_xyz(nt, mp.outputs["Vector"], (-1300, -300))
    lx = maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', math_(nt, 'ADD', sp.outputs["X"], sp.outputs["Z"], (-1200, -250)), None, (-1100, -250)), 0.5, (-1000, -250)), None, (-900, -250)), 0.46, 0.5, 0, 1, (-800, -250))
    ly = maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', math_(nt, 'SUBTRACT', sp.outputs["Y"], sp.outputs["Z"], (-1200, -450)), None, (-1100, -450)), 0.5, (-1000, -450)), None, (-900, -450)), 0.46, 0.5, 0, 1, (-800, -450))
    quilt = math_(nt, 'MAXIMUM', lx, ly, (-650, -350))
    hem = node(nt, "ShaderNodeAttribute", (-1600, 300)); hem.attribute_name = "hem"      # 0 at the spine .. 1 at the hem
    hv = hem.outputs["Fac"]
    gold = math_(nt, 'MULTIPLY', maprange(nt, hv, 0.78, 0.8, 0, 1, (-1300, 300)), maprange(nt, hv, 0.95, 0.97, 1, 0, (-1300, 200)), (-1100, 250))
    green = math_(nt, 'MULTIPLY', maprange(nt, hv, 0.72, 0.735, 0, 1, (-1300, 500)), maprange(nt, hv, 0.765, 0.78, 1, 0, (-1300, 400)), (-1100, 450))
    fringe = maprange(nt, hv, 0.97, 0.98, 0, 1, (-1300, 650))
    n = noise_(nt, co, 6.0, 4, 0.6, loc=(-1300, 800))
    red = mix_rgb(nt, 'MULTIPLY', 1.0, c4(K.srgb((0.52, 0.08, 0.06))), maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.8, 1.05, (-1000, 800)), (-850, 700))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', quilt, 0.35, (-600, -350)), red, (0.5, 0.5, 0.5, 1), (-650, 600))
    col = mix_rgb(nt, 'MIX', green, col, c4(K.srgb((0.12, 0.30, 0.18))), (-500, 600))
    braid = noise_(nt, co, 90.0, 3, 0.6, loc=(-900, 1000))
    goldc = mix_rgb(nt, 'MIX', maprange(nt, braid.outputs["Fac"], 0.4, 0.6, 0, 1, (-700, 1000)), c4(K.srgb((0.62, 0.46, 0.16))), c4(K.srgb((0.80, 0.64, 0.28))), (-500, 1000))
    col = mix_rgb(nt, 'MIX', gold, col, goldc, (-350, 600))
    col = mix_rgb(nt, 'MIX', fringe, col, c4(K.srgb((0.70, 0.52, 0.20))), (-250, 600))
    col = K.ao_mul(nt, col, 0.12, 0.45, (-200, -800))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, gold, 0.85, 0.45, (-200, -200)), b.inputs["Roughness"])
    nt.links.new(mix_f(nt, gold, 0.0, 0.6, (-200, -300)), b.inputs["Metallic"])
    b.inputs["Sheen Weight"].default_value = 0.4
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', quilt, -1.0, (-500, -500)), math_(nt, 'MULTIPLY', braid.outputs["Fac"], gold, (-500, -650)), (-350, -550)), 0.4, 0.006)
    return m


def _el(mb, kind, co, r, size=(1, 1, 1), rot=None, stiff=2.0, neg=False):
    e = mb.elements.new(type=kind); e.co = co; e.radius = r; e.stiffness = stiff
    if kind in ('ELLIPSOID', 'CAPSULE', 'CUBE', 'PLANE'):
        e.size_x, e.size_y, e.size_z = size
    if rot is not None: e.rotation = rot
    e.use_negative = neg
    return e


def _q(axis_dir):
    """the rotation turning +X onto axis_dir (for capsules)."""
    return Vector((1, 0, 0)).rotation_difference(Vector(axis_dir).normalized())


def build(name, origin, yaw, skin, cloth, wood_mat, rope_mat, metal_mat, ivory_mat, nail_mat, eye_mat, target_tris=9000, resolution=0.045):
    """Kiouni at origin (x, y, z) facing yaw (radians from +X, counter-clockwise). Returns (body object, parts list,
    world-space points: 'head', 'back')."""
    mb = bpy.data.metaballs.new(name + "Meta"); mb.resolution = resolution; mb.render_resolution = resolution; mb.threshold = 0.6
    E = lambda *a, **k: _el(mb, *a, **k)
    # --- body: barrel, the back's convex arch, the shoulders, the rump sloping down to the tail, the belly
    E('ELLIPSOID', (0.0, 0.0, 1.78), 1.0, (1.55, 0.92, 0.88))
    E('ELLIPSOID', (0.25, 0.0, 2.05), 0.8, (1.2, 0.85, 0.7))           # the arch of the back
    E('ELLIPSOID', (0.95, 0.0, 1.85), 0.85, (0.75, 1.0, 1.0))          # shoulders
    E('ELLIPSOID', (-0.95, 0.0, 1.72), 0.85, (0.85, 0.98, 0.95))       # haunches
    E('ELLIPSOID', (-1.45, 0.0, 1.62), 0.6, (0.6, 0.9, 0.95))          # rump, falling away
    E('ELLIPSOID', (0.0, 0.0, 1.28), 0.75, (1.6, 1.0, 0.6))            # belly
    # --- neck and head: the head carried low, the twin domes, the forehead, the cheek
    E('ELLIPSOID', (1.55, 0.0, 2.02), 0.7, (0.7, 1.0, 1.0))            # neck
    E('ELLIPSOID', (1.98, 0.0, 2.12), 0.62, (0.95, 0.95, 1.12))        # head mass
    for sy in (-1, 1):
        E('BALL', (1.93, sy * 0.18, 2.56), 0.31)                         # the twin domes
        E('ELLIPSOID', (2.05, sy * 0.33, 2.0), 0.36, (1.0, 0.8, 1.2))   # cheeks
    E('ELLIPSOID', (2.33, 0.0, 2.25), 0.42, (0.7, 1.15, 1.25))          # the forehead, sloping to the trunk
    E('BALL', (2.36, 0.0, 2.55), 0.18, neg=True, stiff=1.0)             # the dent between the domes, in front
    # --- trunk: a chain from the forehead down, hanging slightly forward, the tip curled a little in
    pts = [Vector((2.45, 0.0, 1.95)), Vector((2.55, 0.0, 1.6)), Vector((2.6, 0.0, 1.25)), Vector((2.6, 0.0, 0.9)), Vector((2.56, 0.0, 0.6)),
           Vector((2.52, 0.0, 0.38)), Vector((2.58, 0.0, 0.24)), Vector((2.68, 0.0, 0.2))]
    path = K_catmull(pts, 6)
    for i, p in enumerate(path):
        t = i / (len(path) - 1)
        E('BALL', tuple(p), lerp(0.36, 0.12, t ** 0.8))
    # --- legs: pillar legs, the fore legs straight, the hind with the knee a little forward; round pad feet
    for sy in (-1, 1):
        E('CAPSULE', (0.98, sy * 0.44, 1.15), 0.37, (0.55, 1, 1), rot=_q((0.02, 0, 1)))           # fore upper
        E('CAPSULE', (0.98, sy * 0.44, 0.48), 0.33, (0.42, 1, 1), rot=_q((0, 0, 1)))              # fore lower
        E('ELLIPSOID', (1.0, sy * 0.44, 0.12), 0.32, (1.0, 1.0, 0.45))                           # fore foot
        E('CAPSULE', (-1.02, sy * 0.42, 1.12), 0.39, (0.55, 1, 1), rot=_q((-0.12, 0, 1)))         # hind thigh
        E('CAPSULE', (-0.95, sy * 0.42, 0.48), 0.32, (0.42, 1, 1), rot=_q((0.08, 0, 1)))          # hind shank
        E('ELLIPSOID', (-0.97, sy * 0.42, 0.12), 0.31, (1.05, 1.0, 0.45))
    # --- tail
    tp = K_catmull([Vector((-1.85, 0.0, 1.95)), Vector((-1.98, 0.0, 1.55)), Vector((-2.0, 0.0, 1.15)), Vector((-1.97, 0.0, 0.85))], 4)
    for i, p in enumerate(tp):
        E('BALL', tuple(p), lerp(0.16, 0.08, i / (len(tp) - 1)))
    mo = bpy.data.objects.new(name + "Meta", mb); link(mo)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT'); mo.select_set(True); bpy.context.view_layer.objects.active = mo
    bpy.ops.object.convert(target='MESH')
    body = bpy.context.view_layer.objects.active; body.name = name + "Body"
    for c in body.users_collection: c.objects.unlink(body)
    link(body)
    if name + "Meta" in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[name + "Meta"])
    me = body.data
    # skin texture in the shape: a little lumpiness so the silhouette is not a balloon
    for v in me.vertices:
        p = v.co
        v.co = p + p.normalized() * 0.0 + Vector((0, 0, 0)) + (Vector((noise.noise(p * 1.7), noise.noise(p * 1.7 + Vector((5, 1, 2)))
                                                                          , noise.noise(p * 1.7 + Vector((2, 9, 4))))) * 0.012)
    md = body.modifiers.new("Smooth", 'SMOOTH'); md.factor = 0.5; md.iterations = 4
    bpy.ops.object.modifier_apply(modifier=md.name)
    tri = sum(len(p.vertices) - 2 for p in me.polygons)
    if tri > target_tris:
        dm = body.modifiers.new("Decimate", 'DECIMATE'); dm.ratio = target_tris / tri
        bpy.ops.object.modifier_apply(modifier=dm.name)
    me.materials.append(skin)
    for p in me.polygons: p.use_smooth = True
    # depigmentation: trunk base, forehead and the ear roots
    pk = me.attributes.new("pink", 'FLOAT', 'POINT')
    for i, v in enumerate(me.vertices):
        c = v.co
        f = 0.0
        if c.x > 2.2 and 1.2 < c.z < 2.5: f = max(f, smoothstep(1.2, 1.7, c.z) * (1 - smoothstep(2.25, 2.5, c.z)))
        if c.x > 2.2 and c.z > 2.2: f = max(f, 0.6)
        pk.data[i].value = f
    parts = []
    # --- ears: thin, fold-topped plates, the upper edge rolled forward, the lower lobe pointed, lying back on the neck
    for sy in (-1, 1):
        verts = []; faces = []
        NU, NV = 8, 9
        for j in range(NV + 1):
            v_ = j / NV                                   # 0 at the bottom tip, 1 at the top fold
            for i in range(NU + 1):
                u = i / NU                                # 0 at the root (head), 1 at the free rear edge
                width = 0.52 * math.sin(math.pi * (0.12 + 0.88 * v_)) ** 0.6 * (0.3 + 0.7 * v_)
                x = 1.80 - u * width - 0.12 * (1 - v_)
                z = 1.56 + v_ * 0.80
                # the ear lies back against the neck, bowed outward in the middle, its rear edge turned in
                y = sy * (0.60 + 0.05 * math.sin(math.pi * u) * (0.5 + 0.5 * math.sin(math.pi * v_)) - 0.03 * u * u)
                if v_ > 0.86:                             # the rolled top edge, folded forward and out
                    k = (v_ - 0.86) / 0.14; x += 0.05 * k; y += sy * 0.04 * k; z -= 0.03 * k
                verts.append((x, y, z))
        for j in range(NV):
            for i in range(NU):
                a = j * (NU + 1) + i; faces.append((a, a + 1, a + NU + 2, a + NU + 1))
        ear = mesh_from(f"{name}Ear{sy}", verts, faces, skin, smooth=True)
        sol = ear.modifiers.new("Solid", 'SOLIDIFY'); sol.thickness = 0.03; sol.offset = -sy * 1.0 if False else -1.0
        ea = ear.data.attributes.new("pink", 'FLOAT', 'POINT')
        for i, v in enumerate(ear.data.vertices): ea.data[i].value = 0.7 * smoothstep(0.25, 0.5, (1.86 - v.co.x) / 0.52) if v.co.z < 2.2 else 0.25
        parts.append(ear)
    # --- tushes (short tusks), the eyes, toenails, the tail tuft
    for sy in (-1, 1):
        tp2 = [Vector((2.42, sy * 0.17, 1.72)), Vector((2.62, sy * 0.2, 1.58)), Vector((2.78, sy * 0.21, 1.55)), Vector((2.86, sy * 0.2, 1.6))]
        parts.append(tube(f"{name}Tush{sy}", tp2, [0.065, 0.055, 0.04, 0.012], ivory_mat, sides=8))
        parts.append(sphere(f"{name}Eye{sy}", 0.035, (2.20, sy * 0.47, 2.18), eye_mat, seg=8))
        for k, a in enumerate((-0.9, -0.45, 0.0, 0.45, 0.9)):
            parts.append(sphere(f"{name}NailF{sy}{k}", 0.036, (1.0 + 0.27 * math.cos(a), sy * 0.44 + 0.27 * math.sin(a), 0.055), nail_mat, seg=6, scale=(0.6, 1.0, 0.75)))
        for k, a in enumerate((-0.6, -0.2, 0.2, 0.6)):
            parts.append(sphere(f"{name}NailH{sy}{k}", 0.034, (-0.97 + 0.28 * math.cos(a), sy * 0.42 + 0.28 * math.sin(a), 0.055), nail_mat, seg=6, scale=(0.6, 1.0, 0.75)))
    for k in range(9):
        a = 2 * math.pi * k / 9
        parts.append(tube(f"{name}Tuft{k}", [Vector((-1.97, 0.0, 0.9)), Vector((-1.97 + 0.04 * math.cos(a), 0.04 * math.sin(a), 0.68))], [0.012, 0.004], nail_mat, sides=3))
    # --- the saddle-cloth: a half-cylinder of cloth shrink-wrapped onto the back, hanging down each flank
    verts = []; faces = []; hem = []
    NX, NA = 14, 16
    for i in range(NX + 1):
        x = lerp(-0.9, 0.72, i / NX)
        for j in range(NA + 1):
            a = lerp(-1.0, 1.0, j / NA)                  # -1 port hem .. +1 starboard hem, 0 on the spine
            ang = a * math.radians(96)
            verts.append((x, math.sin(ang) * 1.3, 1.78 + math.cos(ang) * 1.3)); hem.append(abs(a))
    for i in range(NX):
        for j in range(NA):
            q = i * (NA + 1) + j; faces.append((q, q + 1, q + NA + 2, q + NA + 1))
    cl = mesh_from(f"{name}SaddleCloth", verts, faces, cloth, smooth=True)
    sw = cl.modifiers.new("Wrap", 'SHRINKWRAP'); sw.target = body; sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.offset = 0.06
    bpy.ops.object.select_all(action='DESELECT'); cl.select_set(True); bpy.context.view_layer.objects.active = cl
    bpy.ops.object.modifier_apply(modifier=sw.name)
    # let the lower part hang free of the belly's curve: pull the hem verts out and straight down a little
    for k, v in enumerate(cl.data.vertices):
        h = hem[k]
        if h > 0.75:
            t = (h - 0.75) / 0.25
            v.co.y += math.copysign(0.05 * t, v.co.y)
    ha = cl.data.attributes.new("hem", 'FLOAT', 'POINT')
    for k in range(len(cl.data.vertices)): ha.data[k].value = hem[k]
    cl.modifiers.new("Solid", 'SOLIDIFY').thickness = 0.02
    parts.append(cl)
    # girths round the barrel and a breast-band, shrink-wrapped
    for k, x in enumerate((0.55, -0.3)):
        ring = [Vector((x, 1.4 * math.sin(2 * math.pi * i / 28), 1.7 + 1.4 * math.cos(2 * math.pi * i / 28))) for i in range(29)]
        o = tube(f"{name}Girth{k}", ring, 0.035, rope_mat, sides=4, caps=False)
        sw = o.modifiers.new("Wrap", 'SHRINKWRAP'); sw.target = body; sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.offset = 0.085
        parts.append(o)
    # the two howdahs: pannier seats of lashed wood and cane hung on each flank from the pad
    for sy in (-1, 1):
        cx, cy, cz = -0.15, sy * 1.12, 1.95
        F = K.Frame((cx, cy), 0.0, z=0.0)
        F.box(f"{name}HowdahFloor{sy}", (1.0, 0.55, 0.05), (0, sy * 0.05, cz - 0.3), wood_mat)
        F.box(f"{name}HowdahBack{sy}", (1.0, 0.05, 0.62), (0, -sy * 0.2, cz + 0.0), wood_mat)
        F.box(f"{name}HowdahFront{sy}", (1.0, 0.04, 0.32), (0, sy * 0.31, cz - 0.13), wood_mat)
        for sx in (-1, 1):
            F.box(f"{name}HowdahSide{sy}{sx}", (0.04, 0.55, 0.42), (sx * 0.5, sy * 0.05, cz - 0.08), wood_mat)
            tube(f"{name}HowdahRail{sy}{sx}", [Vector((cx + sx * 0.52, cy - sy * 0.2, cz + 0.32)), Vector((cx + sx * 0.52, cy + sy * 0.3, cz + 0.2)), Vector((cx + sx * 0.52, cy + sy * 0.32, cz + 0.05))], 0.02, wood_mat, sides=5)
        tube(f"{name}HowdahTopRail{sy}", [Vector((cx - 0.52, cy - sy * 0.2, cz + 0.32)), Vector((cx + 0.52, cy - sy * 0.2, cz + 0.32))], 0.022, wood_mat, sides=5)
        F.box(f"{name}HowdahCushion{sy}", (0.9, 0.42, 0.08), (0, sy * 0.06, cz - 0.24), cloth)
    # two yokes of bent wood over the back carry the howdahs; ropes lash them down
    for k, x in enumerate((-0.6, 0.3)):
        arc = [Vector((x, 1.3 * math.sin(math.radians(a)), 1.78 + 1.3 * math.cos(math.radians(a)))) for a in range(-75, 76, 10)]
        o = tube(f"{name}Yoke{k}", arc, 0.04, wood_mat, sides=6, caps=True)
        sw = o.modifiers.new("Wrap", 'SHRINKWRAP'); sw.target = body; sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.offset = 0.13
        parts.append(o)
    # a crupper rope from the cloth round under the tail, and the bell on a cord under the neck
    tube(f"{name}Crupper", [Vector((-0.95, 0.35, 2.2)), Vector((-1.6, 0.3, 2.0)), Vector((-1.93, 0.0, 1.85)), Vector((-1.6, -0.3, 2.0)), Vector((-0.95, -0.35, 2.2))], 0.025, rope_mat, sides=4)
    neck = [Vector((1.55, 1.05 * math.sin(2 * math.pi * i / 24), 2.0 + 0.95 * math.cos(2 * math.pi * i / 24))) for i in range(25)]
    o = tube(f"{name}NeckRope", neck, 0.03, rope_mat, sides=4, caps=False)
    sw = o.modifiers.new("Wrap", 'SHRINKWRAP'); sw.target = body; sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.offset = 0.03
    parts.append(o)
    lathe(f"{name}Bell", [(0.0, 0.0), (0.09, 0.0), (0.085, 0.03), (0.07, 0.1), (0.04, 0.16), (0.0, 0.17)], (1.62, 0.0, 0.95), metal_mat, steps=10)
    tube(f"{name}BellCord", [Vector((1.62, 0.0, 1.12)), Vector((1.6, 0.0, 1.08))], 0.01, rope_mat, sides=3)
    # place everything: rotate about z by yaw and move to origin
    M = Matrix.Translation(Vector(origin)) @ Matrix.Rotation(yaw, 4, 'Z')
    objs = [o for o in K.COLL.objects if o.name.startswith(name)]
    bpy.context.view_layer.update()
    for o in objs:
        for md in list(o.modifiers):
            if md.type == 'SHRINKWRAP':
                bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
                bpy.ops.object.modifier_apply(modifier=md.name)
    for o in objs:
        o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    return body, objs, {"head": M @ Vector((2.2, 0, 2.3)), "back": M @ Vector((0.2, 0, 2.9)), "feet": M @ Vector((0, 0, 0))}


def lerp(a, b, t): return a + (b - a) * t
def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)
def K_catmull(pts, n):
    pts = [Vector(p) for p in pts]
    P = [pts[0]] + pts + [pts[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    out.append(pts[-1])
    return out
