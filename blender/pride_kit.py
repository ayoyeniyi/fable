"""
Fable: shared helpers for the three hand-built Pride and Prejudice rooms
(build_fields_to_netherfield.py, build_netherfield_drawing_room.py, build_longbourn_library.py).

The helpers are the ones the earlier hand-built rooms copy from script to script (build_ithaca_hall.py,
build_poppy_field.py, build_emerald_throne_room.py): node-material builders, primitive and tube geometry, a card mesh
builder, anchors, the camera/still loop and the bake + merge-by-material + glTF export for Unity's FableBuild. Kept in
one module here so the three rooms stay consistent. Additions for docs/LIVING_SCENES.md:

  * fx(...) / sound(...) empties named fx.fire.*, fx.candle.*, sound.<kind>.*
  * meshes whose material is listed in KEEP_NAMES keep a living-scene name after the merge (veg.grass.*, veg.leaves.*,
    water.puddle.*, cloth.curtain.* ...); veg.* and cloth.* meshes carry a "sway" colour attribute whose R channel is
    the sway weight (0 at the root, 1 at the tip) and export it as glTF COLOR_0. Every other mesh has its colour
    attributes removed before export.
  * "image" materials (foliage cards, grass palettes) are not baked: their numpy-painted RGBA atlases are exported as
    they are, with alpha clipping (glTF alphaMode MASK) where the card needs a cut-out silhouette.

Everything here is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os, argparse, json
import numpy as np
from mathutils import Vector, Matrix, noise

COLL = None
scene = None
ARGS = None
OUT = None
SCENE_ID = None


# ----------------------------------------------------------------------------- set-up
def setup(scene_id, default_out, seed, coll_name, default_samples=64):
    global COLL, scene, ARGS, OUT, SCENE_ID
    SCENE_ID = scene_id
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=default_out)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--bake", action="store_true")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--samples", type=int, default=default_samples)
    ap.add_argument("--res", type=int, default=1400)
    ap.add_argument("--tex", type=int, default=2048)
    ap.add_argument("--quick", action="store_true", help="low samples for iteration")
    ap.add_argument("--cams", default="", help="comma list of camera names to render (default all)")
    ap.add_argument("--captures", default="", help="also copy stills here (e.g. captures/blender/<id>)")
    ap.add_argument("--nosave", action="store_true", help="skip saving the source .blend")
    ap.add_argument("--cpu", action="store_true", help="render on the CPU (the shared GPU is short of memory)")
    ARGS = ap.parse_args(argv)
    OUT = os.path.abspath(ARGS.out)
    os.makedirs(OUT, exist_ok=True)
    random.seed(seed)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16 if ARGS.quick else ARGS.samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 12
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.cycles.sample_clamp_indirect = 6.0
    try:
        if ARGS.cpu: raise RuntimeError("--cpu")
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
    return ARGS


def link(obj):
    COLL.objects.link(obj); return obj


# ----------------------------------------------------------------------------- small maths
def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t)

def lerp(a, b, t): return a + (b - a) * t

def n2(x, y, s, off=0.0):
    return noise.noise(Vector((x / s + off, y / s - off * 0.7, off * 0.31)))

def fbm2(x, y, s, octaves=4, off=0.0):
    v, a, f = 0.0, 1.0, 1.0
    for i in range(octaves):
        v += a * noise.noise(Vector((x * f / s + off + i * 17.3, y * f / s - off * 0.7 + i * 5.1, off * 0.3 + i)))
        a *= 0.5; f *= 2.03
    return v

def srgb(c):
    """sRGB 0-1 (as colours are picked) to linear."""
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3])


# ----------------------------------------------------------------------------- material helpers (from build_ithaca_hall.py)
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

def ramp(nt, stops, loc=(0, 0), interp=None):
    r = nt.nodes.new("ShaderNodeValToRGB"); r.location = loc
    cr = r.color_ramp
    if interp: cr.interpolation = interp
    while len(cr.elements) > 1: cr.elements.remove(cr.elements[-1])
    cr.elements[0].position, cr.elements[0].color = stops[0]
    for pos, col in stops[1:]:
        e = cr.elements.new(pos); e.color = col
    return r

def obj_coords(nt, loc=(-1800, 0)):
    tc = node(nt, "ShaderNodeTexCoord", loc); return tc.outputs["Object"]

def texcoord_obj(nt, loc=(-1400, 0)):
    tc = node(nt, "ShaderNodeTexCoord", loc); mp = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    return mp

def sep_xyz(nt, vec, loc=(0, 0)):
    s = node(nt, "ShaderNodeSeparateXYZ", loc); nt.links.new(vec, s.inputs["Vector"]); return s

def math_(nt, op, a, b=None, loc=(0, 0), c=None):
    n = node(nt, "ShaderNodeMath", loc, operation=op)
    for i, v in enumerate((a, b, c)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]

def mix_rgb(nt, blend, fac, a, b, loc=(0, 0)):
    n = node(nt, "ShaderNodeMix", loc, data_type='RGBA', blend_type=blend)
    for sock, v in ((n.inputs["Factor"], fac), (n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, (int, float)): sock.default_value = v
        elif isinstance(v, tuple): sock.default_value = v if len(v) == 4 else (v[0], v[1], v[2], 1)
        else: nt.links.new(v, sock)
    return n.outputs[2]

def mix_f(nt, fac, a, b, loc=(0, 0)):
    n = node(nt, "ShaderNodeMix", loc, data_type='FLOAT')
    for sock, v in ((n.inputs[0], fac), (n.inputs[2], a), (n.inputs[3], b)):
        if isinstance(v, (int, float)): sock.default_value = v
        else: nt.links.new(v, sock)
    return n.outputs[0]

def maprange(nt, val, f0, f1, t0=0.0, t1=1.0, loc=(0, 0), interp='LINEAR'):
    n = node(nt, "ShaderNodeMapRange", loc, interpolation_type=interp)
    n.inputs["From Min"].default_value = f0; n.inputs["From Max"].default_value = f1
    n.inputs["To Min"].default_value = t0; n.inputs["To Max"].default_value = t1
    nt.links.new(val, n.inputs["Value"])
    return n.outputs["Result"]

def noise_(nt, vec, scale, detail=6.0, rough=0.6, distortion=0.0, loc=(0, 0)):
    n = node(nt, "ShaderNodeTexNoise", loc); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough; n.inputs["Distortion"].default_value = distortion
    nt.links.new(vec, n.inputs["Vector"])
    return n

def voronoi_(nt, vec, scale, feature='F1', loc=(0, 0), rand=1.0):
    v = node(nt, "ShaderNodeTexVoronoi", loc, feature=feature); v.inputs["Scale"].default_value = scale
    v.inputs["Randomness"].default_value = rand
    nt.links.new(vec, v.inputs["Vector"])
    return v

def bump_from(nt, b, height_socket, strength, distance, loc=(50, -300)):
    bump = node(nt, "ShaderNodeBump", loc); bump.inputs["Strength"].default_value = strength; bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return bump

def c4(c): return (c[0], c[1], c[2], 1)

def ao_mul(nt, col, dist=0.15, amount=0.35, loc=(0, -600)):
    ao = node(nt, "ShaderNodeAmbientOcclusion", loc); ao.inputs["Distance"].default_value = dist
    return mix_rgb(nt, 'MULTIPLY', amount, col, ao.outputs["Color"], (loc[0] + 250, loc[1]))

def wood(name, base=(0.32, 0.17, 0.08), dark=(0.09, 0.045, 0.02), light=(0.55, 0.33, 0.15), scale=1.0, rough=(0.35, 0.7),
         grain_dir=(1, 1, 14), bands='Z', coat=0.0, ao=0.3, bump=0.3):
    """Wood grain: wave bands distorted by noise, fine fibre noise, optional clear coat (French polish)."""
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt)
    mp.inputs["Scale"].default_value = tuple(g * scale for g in grain_dir)
    wave = node(nt, "ShaderNodeTexWave", (-1000, 200), wave_type='BANDS', bands_direction=bands)
    wave.inputs["Scale"].default_value = 1.2; wave.inputs["Distortion"].default_value = 9.0
    wave.inputs["Detail"].default_value = 6.0; wave.inputs["Detail Scale"].default_value = 1.5
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    fine = noise_(nt, mp.outputs["Vector"], 60.0, 8.0, 0.7, loc=(-1000, -150))
    mix = node(nt, "ShaderNodeMix", (-700, 100), data_type='FLOAT'); mix.inputs["Factor"].default_value = 0.22
    nt.links.new(wave.outputs["Fac"], mix.inputs[2]); nt.links.new(fine.outputs["Fac"], mix.inputs[3])
    mid = tuple((x + y) / 2 for x, y in zip(base, light)); lite = tuple((x + y) / 2 for x, y in zip(mid, light))
    r = ramp(nt, [(0.0, c4(dark)), (0.2, c4(base)), (0.5, c4(mid)), (0.72, c4(lite)), (0.9, c4(base))], (-450, 100))
    nt.links.new(mix.outputs[0], r.inputs["Fac"])
    col = ao_mul(nt, r.outputs["Color"], 0.12, ao, (-300, -550)) if ao else r.outputs["Color"]
    nt.links.new(col, b.inputs["Base Color"])
    rr = maprange(nt, wave.outputs["Fac"], 0, 1, rough[1], rough[0], (-150, -200))
    nt.links.new(rr, b.inputs["Roughness"])
    if bump: bump_from(nt, b, mix.outputs[0], bump, 0.002)
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.25
    return m

def noisy(name, colors, scale=8.0, rough=0.8, bump=0.2, bump_dist=0.003, detail=6.0, stretch=(1, 1, 1), sheen=0.0, metallic=0.0,
          warp=0.0, coat=0.0, ao=0.0):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt); mp.inputs["Scale"].default_value = stretch
    n = noise_(nt, mp.outputs["Vector"], scale, detail, 0.6, warp, (-1000, 0))
    stops = [(i / max(1, len(colors) - 1) * 0.6 + 0.2, c4(c)) for i, c in enumerate(colors)]
    r = ramp(nt, stops, (-700, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    col = r.outputs["Color"]
    if ao: col = ao_mul(nt, col, 0.12, ao)
    nt.links.new(col, b.inputs["Base Color"])
    if isinstance(rough, tuple):
        nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.7, rough[0], rough[1], (-400, -200)), b.inputs["Roughness"])
    else:
        b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if sheen: b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.4
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.1
    if bump:
        fine = noise_(nt, mp.outputs["Vector"], scale * 6, 4, 0.6, loc=(-1000, -350))
        bump_from(nt, b, fine.outputs["Fac"], bump, bump_dist)
    return m

def plain(name, color, rough=0.5, metallic=0.0, emission=None, strength=0.0, coat=0.0, transmission=0.0, sheen=0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = c4(color); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if emission: b.inputs["Emission Color"].default_value = c4(emission); b.inputs["Emission Strength"].default_value = strength
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.05
    if transmission: b.inputs["Transmission Weight"].default_value = transmission
    if sheen: b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.5
    return m

def vcol_mat(name, rough=0.6, sheen=0.0, attr="tone", bump=0.0, bump_scale=200.0, metallic=0.0, coat=0.0):
    """Base colour from a per-corner colour attribute (many small parts sharing one material: book spines, cards)."""
    m, nt, b = new_mat(name)
    a = node(nt, "ShaderNodeAttribute", (-600, 0)); a.attribute_name = attr
    nt.links.new(a.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if sheen: b.inputs["Sheen Weight"].default_value = sheen
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.2
    if bump:
        n = noise_(nt, obj_coords(nt, (-1000, -300)), bump_scale, 4, 0.6, loc=(-700, -300))
        bump_from(nt, b, n.outputs["Fac"], bump, 0.001)
    return m


# ----------------------------------------------------------------------------- numpy-painted image atlases (foliage cards, palettes)
IMAGE_MATS = set()        # materials whose textures are painted here (not baked)
ALPHA_MATS = set()

def np_image(name, arr, noncolor=False):
    """arr: (H, W, 4) float 0-1, row 0 = top of the picture. Saved as PNG into OUT/textures and packed."""
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    if noncolor: img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1].astype(np.float32)).ravel())
    d = os.path.join(OUT, "textures"); os.makedirs(d, exist_ok=True)
    img.filepath_raw = os.path.join(d, name + ".png"); img.file_format = 'PNG'; img.save(); img.pack()
    return img

def image_mat(name, img, rough=0.6, alpha=False, sheen=0.0, translucent=0.0, spec=0.5, normal_img=None):
    """A card material that reads its painted atlas directly. alpha=True: clipped at 0.5 (glTF alphaMode MASK)."""
    m, nt, b = new_mat(name)
    uv = node(nt, "ShaderNodeUVMap", (-900, 0)); uv.uv_map = "UVMap"
    t = node(nt, "ShaderNodeTexImage", (-600, 0)); t.image = img; t.interpolation = 'Linear'
    nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = spec
    if sheen: b.inputs["Sheen Weight"].default_value = sheen
    if translucent:
        # thin leaves pass a little light (render only; Unity ignores it)
        b.inputs["Subsurface Weight"].default_value = 0.0
        b.inputs["Transmission Weight"].default_value = 0.0
    if alpha:
        r = math_(nt, 'ROUND', t.outputs["Alpha"], None, (-250, -250))
        nt.links.new(r, b.inputs["Alpha"])
        ALPHA_MATS.add(name)
    if normal_img is not None:
        tn = node(nt, "ShaderNodeTexImage", (-600, -400)); tn.image = normal_img
        nt.links.new(uv.outputs["UV"], tn.inputs["Vector"])
        nm = node(nt, "ShaderNodeNormalMap", (-250, -450)); nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    m.use_backface_culling = False
    IMAGE_MATS.add(name)
    return m

class Canvas:
    """A float RGBA canvas with antialiased ellipses, polylines and polygons (for leaf sprays, twigs, haws, palettes)."""
    def __init__(self, w, h=None, bg=(0, 0, 0, 0)):
        h = h or w; self.w, self.h = w, h
        self.a = np.zeros((h, w, 4), np.float32); self.a[:] = bg
        self.yy, self.xx = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
        self.clip = None
    def _comp(self, x0, x1, y0, y1, cov, color):
        cx0, cy0, cx1, cy1 = self.clip if self.clip else (0, 0, self.w, self.h)
        x0 = max(cx0, int(x0)); y0 = max(cy0, int(y0)); x1 = min(cx1, int(x1) + 1); y1 = min(cy1, int(y1) + 1)
        if x1 <= x0 or y1 <= y0: return
        c = cov(self.xx[y0:y1, x0:x1], self.yy[y0:y1, x0:x1])
        c = np.clip(c, 0, 1)[..., None]
        reg = self.a[y0:y1, x0:x1]
        col = np.array(color[:3], np.float32); al = color[3] if len(color) > 3 else 1.0
        c = c * al
        reg[..., :3] = reg[..., :3] * (1 - c) + col * c
        reg[..., 3:4] = reg[..., 3:4] * (1 - c) + c
    def ellipse(self, cx, cy, rx, ry, ang, color, soft=1.0, tip=0.0):
        """tip > 0 sharpens one end (a leaf shape)."""
        ca, sa = math.cos(ang), math.sin(ang); R = max(rx, ry) + 2
        def cov(x, y):
            dx, dy = x - cx, y - cy
            u = (dx * ca + dy * sa) / rx; v = (-dx * sa + dy * ca) / ry
            if tip: v = v / np.clip(1.0 - tip * np.clip(u, 0, 1) ** 1.5 + 0.0001, 0.05, 1.5)
            d = np.sqrt(u * u + v * v)
            return (1.0 - d) * min(rx, ry) / soft + 0.5
        self._comp(cx - R, cx + R, cy - R, cy + R, cov, color)
    def line(self, p0, p1, w0, w1, color):
        x0, y0 = p0; x1, y1 = p1; L2 = max(1e-6, (x1 - x0) ** 2 + (y1 - y0) ** 2); R = max(w0, w1) + 2
        def cov(x, y):
            t = np.clip(((x - x0) * (x1 - x0) + (y - y0) * (y1 - y0)) / L2, 0, 1)
            px, py = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
            d = np.sqrt((x - px) ** 2 + (y - py) ** 2); w = w0 + (w1 - w0) * t
            return w - d + 0.5
        self._comp(min(x0, x1) - R, max(x0, x1) + R, min(y0, y1) - R, max(y0, y1) + R, cov, color)
    def tint(self, fn):
        self.a[..., :3] = fn(self.a[..., :3], self.xx, self.yy)
    def bleed(self, n=4):
        """Spread colour into transparent pixels (no dark fringes under mip-mapping); alpha unchanged."""
        a = self.a; col = a[..., :3] * a[..., 3:4]; w = a[..., 3:4].copy()
        for _ in range(n):
            c2 = col.copy(); w2 = w.copy()
            cp = np.pad(col, ((1, 1), (1, 1), (0, 0)), mode='edge'); wp = np.pad(w, ((1, 1), (1, 1), (0, 0)), mode='edge')
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c2 += cp[1 + dy:cp.shape[0] - 1 + dy, 1 + dx:cp.shape[1] - 1 + dx]; w2 += wp[1 + dy:wp.shape[0] - 1 + dy, 1 + dx:wp.shape[1] - 1 + dx]
            col, w = c2 / 5, w2 / 5
        fill = col / np.maximum(w, 1e-5)
        m = a[..., 3:4] < 0.5
        a[..., :3] = np.where(m, fill, a[..., :3])


# ----------------------------------------------------------------------------- geometry helpers (from build_ithaca_hall.py / build_poppy_field.py)
def _finish(o, mat, smooth=False):
    o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = 1; md.limit_method = 'ANGLE'
    return _finish(o, mat)

def cyl(name, r, h, loc, mat, verts=16, rot=(0, 0, 0), r2=None, smooth=True):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat, smooth=smooth)

def sphere(name, r, loc, mat, seg=12, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(4, seg // 2), radius=r, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, mat, smooth=True)

def lathe(name, profile, loc, mat, steps=16, jitter=0.0, seed=0, rot=(0, 0, 0)):
    """profile: list of (radius, z) from bottom to top; revolve around Z (radius 0 = a pole)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for j, (r, z) in enumerate(profile):
        if r < 1e-5: rings.append([bm.verts.new((0, 0, z))]); continue
        ring = []
        for i in range(steps):
            a = 2 * math.pi * i / steps
            rr = r * (1 + jitter * noise.noise(Vector((math.cos(a) * 1.7 + seed, math.sin(a) * 1.7, j * 0.37)))) if jitter else r
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
        rings.append(ring)
    for a, b_ in zip(rings, rings[1:]):
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
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot; me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def tube(name, pts, radii, mat, sides=8, caps=True, smooth=True):
    """A tube along a polyline, parallel-transported frames."""
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
        v = d.cross(u); u_prev = u
        rings.append([bm.verts.new(p + (u * math.cos(2 * math.pi * k / sides) + v * math.sin(2 * math.pi * k / sides)) * radii[i]) for k in range(sides)])
    for a, b_ in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b_[j], b_[k]))
    if caps: bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return link(o)

def sweep(name, profile, path, mat, closed_path=False, cap=False, smooth=False):
    """Extrude a 2D profile [(across, up), ...] along a horizontal polyline path [(x, y, z), ...]. 'across' points to the
    left of the direction of travel (for a wall run counter-clockwise seen from above, left = into the room). Mitred
    corners. Used for cornices, skirtings, dado rails, architraves, chimney-piece mouldings."""
    P = [Vector(p) for p in path]; n = len(P)
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for i in range(n):
        if closed_path:
            d0 = (P[i] - P[i - 1]); d1 = (P[(i + 1) % n] - P[i])
        else:
            d0 = (P[i] - P[i - 1]) if i > 0 else (P[1] - P[0]); d1 = (P[i + 1] - P[i]) if i < n - 1 else d0
        d0.z = 0; d1.z = 0; d0.normalize(); d1.normalize()
        l0 = Vector((-d0.y, d0.x, 0)); l1 = Vector((-d1.y, d1.x, 0))
        mit = (l0 + l1); mit.normalize()
        k = 1.0 / max(0.3, mit.dot(l1))
        rings.append([bm.verts.new(P[i] + mit * (a * k) + Vector((0, 0, u))) for a, u in profile])
    segs = n if closed_path else n - 1
    for i in range(segs):
        a, b_ = rings[i], rings[(i + 1) % n]
        for k in range(len(profile) - 1):
            bm.faces.new((a[k], a[k + 1], b_[k + 1], b_[k]))
    if cap and not closed_path:
        try: bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
        except ValueError: pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return link(o)

def mesh_from(name, verts, faces, mat, smooth=False, uvs=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    if uvs is not None:
        uvl = me.uv_layers.new(name="UVMap")
        for li, l in enumerate(me.loops): uvl.data[li].uv = uvs[l.vertex_index]
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return link(o)

class Frame:
    """Local frame for a piece of furniture: +Y forward, origin on the floor, turned by yaw about Z."""
    def __init__(self, origin, yaw, z=0.0):
        self.o = Vector((origin[0], origin[1], z)); self.yaw = yaw; self.R = Matrix.Rotation(yaw, 3, 'Z')
    def p(self, x, y, z): return tuple(self.o + self.R @ Vector((x, y, z)))
    def v(self, x, y, z): return self.R @ Vector((x, y, z))
    def box(self, name, size, local, mat, bevel=0.0, rx=0.0, ry=0.0): return box(name, size, self.p(*local), mat, bevel=bevel, rot=(rx, ry, self.yaw))
    def cyl(self, name, r, h, local, mat, verts=8, r2=None): return cyl(name, r, h, self.p(*local), mat, verts=verts, rot=(0, 0, self.yaw), r2=r2)
    def lathe(self, name, profile, local, mat, steps=12): return lathe(name, profile, self.p(*local), mat, steps=steps, rot=(0, 0, self.yaw))

class MB:
    """Mesh builder for many small parts in one object: positions, faces, per-corner UVs, a per-vertex sway weight
    (written to the 'sway' colour attribute R; G and B carry an optional tint), all in world space."""
    def __init__(self):
        self.v = []; self.f = []; self.uv = []; self.col = []
    def vert(self, p, uv=(0, 0), sway=0.0, tint=(1.0, 1.0)):
        self.v.append(tuple(p)); self.uv.append(tuple(uv)); self.col.append((sway, tint[0], tint[1], 1.0)); return len(self.v) - 1
    def face(self, *idx): self.f.append(tuple(idx))
    def quad_card(self, c, right, up, uv0=(0, 0), uv1=(1, 1), sway=(0.0, 1.0), bottom_pivot=True):
        """A rectangle: bottom edge centred at c (or centred at c), spanning right (full width) and up (full height)."""
        c = Vector(c); right = Vector(right); up = Vector(up)
        o = c - right * 0.5 if bottom_pivot else c - right * 0.5 - up * 0.5
        a = self.vert(o, (uv0[0], uv0[1]), sway[0]); b = self.vert(o + right, (uv1[0], uv0[1]), sway[0])
        cc = self.vert(o + right + up, (uv1[0], uv1[1]), sway[1]); d = self.vert(o + up, (uv0[0], uv1[1]), sway[1])
        self.face(a, b, cc, d)
    def build(self, name, mat, sway=True, smooth=True):
        if not self.f: return None
        me = bpy.data.meshes.new(name); me.from_pydata(self.v, [], self.f); me.update()
        uvl = me.uv_layers.new(name="UVMap")
        lv = np.zeros(len(me.loops), np.int64); me.loops.foreach_get("vertex_index", lv)
        uva = np.array(self.uv, np.float32)[lv]; uvl.data.foreach_set("uv", uva.ravel())
        if sway:
            ca = me.color_attributes.new("sway", 'BYTE_COLOR', 'CORNER')
            cola = np.array(self.col, np.float32)[lv]; ca.data.foreach_set("color", cola.ravel())
            me.color_attributes.active_color = ca; me.color_attributes.render_color_index = 0
        o = bpy.data.objects.new(name, me); me.materials.append(mat)
        if smooth:
            for p in me.polygons: p.use_smooth = True
        return link(o)

def add_sway(o, fn):
    """Give an existing mesh a 'sway' colour attribute: fn(world_pos) -> R weight 0..1."""
    me = o.data
    ca = me.color_attributes.get("sway") or me.color_attributes.new("sway", 'BYTE_COLOR', 'POINT')
    for i, v in enumerate(me.vertices):
        w = fn(o.matrix_world @ v.co); ca.data[i].color = (w, 1, 1, 1)
    me.color_attributes.active_color = ca


# ----------------------------------------------------------------------------- named empties: anchors, living-scene fx and sound sources
def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.1; e.location = loc; link(e)
    return e

def fx(name, loc, size):
    """fx.fire.* (base of a flame; size = fire radius in metres), fx.candle.* (top of the wick)."""
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'SPHERE'; e.empty_display_size = size; e.location = loc; link(e)
    return e

def sound(kind, tag, loc):
    e = bpy.data.objects.new(f"sound.{kind}.{tag}", None); e.empty_display_type = 'CONE'; e.empty_display_size = 0.3; e.location = loc; link(e)
    return e

def light_obj(name, kind, energy, color, loc, direction=None, **kw):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    for k, v in kw.items(): setattr(ld, k, v)
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if direction is not None: lo.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
    return link(lo)


# ----------------------------------------------------------------------------- cameras and stills
def camera(name, loc, look_at, lens=18):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 400; cd.clip_start = 0.03
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co

def apply_transforms():
    bpy.ops.object.select_all(action='DESELECT')
    for o in COLL.objects:
        if o.type == 'MESH': o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.select_all(action='DESELECT')

def render_stills(cams, page=None, page_cams=(), exposure=None, default_exposure=0.0, captures_dir=""):
    """Every still is labelled a Blender render, in its file name and in a stamp burnt into the image."""
    import shutil
    exposure = exposure or {}
    scene.render.resolution_x = ARGS.res; scene.render.resolution_y = int(ARGS.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    want = set(c.strip().lower() for c in ARGS.cams.split(",") if c.strip())
    spp = scene.cycles.samples
    r = scene.render
    r.use_stamp = True
    for k in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time", "use_stamp_frame", "use_stamp_frame_range", "use_stamp_memory",
              "use_stamp_hostname", "use_stamp_camera", "use_stamp_lens", "use_stamp_scene", "use_stamp_marker", "use_stamp_filename",
              "use_stamp_sequencer_strip", "use_stamp_note", "use_stamp_marker"):
        if hasattr(r, k): setattr(r, k, False)
    r.use_stamp_note = True; r.stamp_font_size = max(12, ARGS.res // 90)
    r.stamp_foreground = (1, 1, 1, 0.85); r.stamp_background = (0, 0, 0, 0.35)
    paths = []
    for c in cams:
        view = c.name[4:].lower()
        if want and view not in want: continue
        scene.camera = c
        if page is not None: page.hide_render = c.name not in page_cams
        scene.view_settings.exposure = exposure.get(c.name, default_exposure)
        r.stamp_note_text = f"Blender render (Cycles {spp} spp) - {SCENE_ID} - {view}"
        fn = f"blender-render_{SCENE_ID}_{view}_cycles-{spp}spp.png"
        r.filepath = os.path.join(OUT, fn)
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:
            print("GPU render failed, retrying on CPU:", e); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", r.filepath, flush=True)
        paths.append(r.filepath)
        if captures_dir:
            os.makedirs(captures_dir, exist_ok=True); shutil.copy(r.filepath, os.path.join(captures_dir, fn))
    r.use_stamp = False
    return paths


# ----------------------------------------------------------------------------- budget, bake, merge and export for Unity
def tri_count(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)

def print_budget(exclude=("PagePreview",)):
    dg = bpy.context.evaluated_depsgraph_get(); cat = {}
    for o in [o for o in COLL.objects if o.type == 'MESH' and o.name not in exclude]:
        e = o.evaluated_get(dg); me = e.to_mesh(); t = sum(len(p.vertices) - 2 for p in me.polygons); e.to_mesh_clear()
        k = o.data.materials[0].name if o.data.materials else "?"
        cat[k] = cat.get(k, 0) + t
    print(f"PRE-MERGE materials={len(cat)} tris={sum(cat.values())}")
    for k, v in sorted(cat.items(), key=lambda kv: -kv[1]): print(f"  BUDGET {k:28s} {v}")
    return sum(cat.values())

def patch_sun_intensities(gltf_path):
    """Blender 5.2.3's glTF exporter writes every SUN light at strength 1 whatever its energy."""
    want = {o.name: o.data.energy * 683.0 for o in COLL.objects if o.type == 'LIGHT' and o.data.type == 'SUN'}
    with open(gltf_path) as f: g = json.load(f)
    for l in g.get("extensions", {}).get("KHR_lights_punctual", {}).get("lights", []):
        if l.get("type") == "directional" and l.get("name") in want: l["intensity"] = want[l["name"]]
    with open(gltf_path, "w") as f: json.dump(g, f, indent=1)

def bake_and_export(gltf_name, cams, page=None, keep_names=None, keep_uv=(), size_for=None, default_size=None, sky_names=("SkyDome",),
                    unlit_emit=()):
    """Join meshes by material, bake each procedural material to BaseColor/Roughness/Normal textures (CPU, 1 sample:
    5.2.3's Metal kernels crashed mid-bake for the croquet ground), keep painted image materials as they are, keep the
    living-scene names and the sway colour attribute, export .gltf + .bin + textures/."""
    keep_names = keep_names or {}; size_for = size_for or {}
    T_ = ARGS.tex; default_size = default_size or (T_ // 4, T_ // 4, T_ // 4)
    if page is not None: bpy.data.objects.remove(page)
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
        living = keep_names.get(mname, "").split(".")[0] in ("veg", "cloth")
        for o in objs:
            if not living:
                for an in [a.name for a in o.data.color_attributes]: o.data.color_attributes.remove(o.data.color_attributes[an])
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active; o.name = keep_names.get(mname, "MESH_" + mname[2:])
        o.data.name = o.name
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    scene.cycles.samples = 1; scene.cycles.device = 'CPU'
    scene.render.bake.margin = 6
    tex_sizes = {}
    for o in merged:
        m = o.data.materials[0]; nt = m.node_tree
        if m.name in IMAGE_MATS:
            tex_sizes[o.name] = max((n.image.size[0] for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image), default=0)
            continue
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        sizes = size_for.get(m.name, default_size)
        tex_sizes[o.name] = sizes[0]
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        if m.name not in keep_uv or not o.data.uv_layers:
            while o.data.uv_layers: o.data.uv_layers.remove(o.data.uv_layers[0])
            o.data.uv_layers.new(name="UVMap")
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
            bpy.ops.object.mode_set(mode='OBJECT')
        passes = [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]
        is_emit = o.name in sky_names or m.name in unlit_emit
        if is_emit: passes = [("BaseColor", 'EMIT', {}, False)]
        passes = passes[:len(sizes)]
        baked = {}
        for (pass_name, btype, extra, noncolor), size in zip(passes, sizes):
            size = max(32, size)
            img = bpy.data.images.new(f"T_{m.name[2:]}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            for n in nt.nodes: n.select = False
            tex.select = True; nt.nodes.active = tex
            bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            img.filepath_raw = os.path.join(OUT, "textures", img.name + ".png"); os.makedirs(os.path.dirname(img.filepath_raw), exist_ok=True)
            img.file_format = 'PNG'; img.save(); img.pack()
            baked[pass_name] = tex
            print("baked", img.name, size, flush=True)
        metallic = bsdf.inputs["Metallic"].default_value
        rough_v = bsdf.inputs["Roughness"].default_value
        emis = bsdf.inputs["Emission Strength"].default_value; ecol = tuple(bsdf.inputs["Emission Color"].default_value)
        elinked = bsdf.inputs["Emission Color"].is_linked
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
        if is_emit:
            nb.inputs["Emission Strength"].default_value = 1.0; nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"])
        elif emis > 0:
            nb.inputs["Emission Strength"].default_value = min(emis, 4.0)
            if elinked: nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"])
            else: nb.inputs["Emission Color"].default_value = ecol
    for c in cams:
        if c.name in bpy.data.objects: bpy.data.objects.remove(c)
    gl = os.path.join(OUT, gltf_name)
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=88, export_lights=True, export_cameras=False,
                              export_vertex_color='ACTIVE', export_all_vertex_colors=False)
    patch_sun_intensities(gl)
    # alpha-tested cards: make sure the painted atlases with alpha stay PNG (JPEG has no alpha) and are MASK
    with open(gl) as f: g = json.load(f)
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    used = set(im.get("uri") for im in g.get("images", []))
    tex_bytes = sum(os.path.getsize(os.path.join(OUT, u)) for u in used if u and os.path.exists(os.path.join(OUT, u)))
    gpu_bytes = 0
    for im in bpy.data.images:
        if im.size[0] > 0 and (im.name.startswith("T_") or im.name.startswith("A_")):
            gpu_bytes += int(im.size[0] * im.size[1] * 1.33 * (1 if im.name.startswith("A_") else 1))  # ASTC/ETC2 ~1 byte/texel + mips
    alpha_modes = {mt["name"]: mt.get("alphaMode", "OPAQUE") for mt in g.get("materials", [])}
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris} textures_on_disk={tex_bytes / 1e6:.1f}MB")
    print("ALPHA MODES", {k: v for k, v in alpha_modes.items() if v != "OPAQUE"})
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\ntextures_on_disk_MB={tex_bytes / 1e6:.2f}\n"
                f"textures_gpu_estimate_MB(~1 byte/texel compressed + mips)={gpu_bytes / 1e6:.2f}\n")
        f.write(f"alpha_mask_materials={[k for k, v in alpha_modes.items() if v != 'OPAQUE']}\n")
        f.write("nodes=" + ", ".join(sorted(n.get("name", "") for n in g.get("nodes", []) if not n.get("name", "").startswith("MESH_"))) + "\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={tex_sizes.get(o.name, 0)} "
                    f"colour_attr={'yes' if o.data.color_attributes else 'no'}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, gltf_name.replace(".gltf", "_baked.blend")))
    return gl
