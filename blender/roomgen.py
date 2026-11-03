"""
Fable roomgen: build one generated reading room from a room script, check it, bake its light and export it.

  blender -b --factory-startup -P blender/roomgen.py -- --script room.py --out out/rooms/<book>/r1 [--tex 1024]
  blender -b --factory-startup -P blender/roomgen.py -- --script room.py --check      (validate the script only)

The room script is written by Claude (interpreter/internal/rooms) and is untrusted. Before it runs:
- its syntax tree is checked: no import statements, no names or attributes beginning with "_", no file, process or
  evaluation builtins, and none of the bpy areas that touch files, add-ons, handlers or preferences;
- it runs with only roomkit (as `kit`), bpy, bmesh, math, random, Vector, Euler, Matrix and noise in scope, and a
  short list of harmless builtins.
roomgen itself, not the script, writes the output files.

The output is an unlit glTF: Cycles bakes each material group's full lighting (sun, sky, lamps, bounce, contact
shadows) into its colour texture, so the headset shows the light of the render without lighting anything at runtime
(and without Unity's lightmapper, which cannot run on the headset). The last line printed is
  FABLE_ROOM {json}   with ok, problems, triangles, meshes, textures, luma per check view, anchors and timings.
"""
import bpy, bmesh, math, random, sys, os, json, time, ast, argparse
from mathutils import Vector, Matrix, Euler, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import roomkit as kit

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--script", required=True)
ap.add_argument("--out", default="")
ap.add_argument("--tex", type=int, default=1024)
ap.add_argument("--samples", type=int, default=48)
ap.add_argument("--check", action="store_true")
ap.add_argument("--seed", type=int, default=1)
args = ap.parse_args(argv)

MAX_TRIS, MAX_MESHES, TARGET_TRIS = 65000, 50, 35000
T0 = time.time(); timings = {}


def done(ok, problems, **extra):
    print("FABLE_ROOM " + json.dumps(dict(ok=ok, problems=problems, seconds=timings, **extra)))
    sys.stdout.flush()
    os._exit(0)


# ---------------------------------------------------------------- 1. check the script

ALLOWED_CALLS = {"range", "len", "min", "max", "abs", "round", "int", "float", "sum", "enumerate", "zip", "list", "tuple",
                 "dict", "set", "sorted", "reversed", "any", "all", "print", "isinstance", "bool", "str", "map", "filter"}
BAD_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr", "delattr",
             "input", "help", "breakpoint", "exit", "quit", "memoryview", "object", "type", "super", "classmethod",
             "staticmethod", "property", "os", "sys", "subprocess", "socket", "shutil", "pathlib", "importlib", "ctypes"}
BAD_ATTRS = {"ops.wm", "ops.script", "ops.preferences", "ops.text", "ops.file", "ops.export_scene", "ops.import_scene",
             "ops.export_mesh", "ops.import_mesh", "ops.render", "ops.image", "ops.sound", "ops.outliner", "ops.ed",
             "data.texts", "data.libraries", "data.images", "app", "utils", "context.preferences", "path", "props"}


def dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr); node = node.value
    if isinstance(node, ast.Name): parts.append(node.id)
    return ".".join(reversed(parts))


def check(src):
    problems = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [f"syntax error line {e.lineno}: {e.msg}"]
    if len(src) > 60000: problems.append("script longer than 60 kB")
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)): problems.append(f"line {n.lineno}: import is not allowed (everything is already in scope)")
        elif isinstance(n, (ast.Global, ast.Nonlocal, ast.AsyncFunctionDef, ast.Await, ast.With, ast.AsyncWith, ast.Try, ast.Raise, ast.ClassDef)):
            problems.append(f"line {n.lineno}: {type(n).__name__} is not allowed")
        elif isinstance(n, ast.Name) and (n.id.startswith("_") or n.id in BAD_NAMES):
            problems.append(f"line {n.lineno}: the name {n.id} is not allowed")
        elif isinstance(n, ast.Attribute):
            if n.attr.startswith("_"): problems.append(f"line {n.lineno}: attribute {n.attr} is not allowed")
            d = dotted(n)
            if d.startswith("bpy."):
                rest = d[4:]
                if any(rest == b or rest.startswith(b + ".") for b in BAD_ATTRS): problems.append(f"line {n.lineno}: bpy.{rest} is not allowed")
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) > 2000:
            problems.append(f"line {n.lineno}: string constant too long")
    return sorted(set(problems))[:20]


src = open(args.script, encoding="utf-8").read()
problems = check(src)
if problems or args.check:
    done(not problems, problems)

# ---------------------------------------------------------------- 2. run it

SAFE_BUILTINS = {k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k) for k in ALLOWED_CALLS}
SAFE_BUILTINS.update(ValueError=ValueError, Exception=Exception)
scope = {"__builtins__": SAFE_BUILTINS, "kit": kit, "bpy": bpy, "bmesh": bmesh, "math": math, "random": random,
         "Vector": Vector, "Euler": Euler, "Matrix": Matrix, "noise": noise}
kit.begin(args.seed)
t = time.time()
try:
    exec(compile(src, "room.py", "exec"), scope)
except Exception as e:
    import traceback
    tb = traceback.extract_tb(e.__traceback__)
    where = next((f"line {f.lineno}" for f in reversed(tb) if f.filename == "room.py"), "")
    done(False, [f"the script failed {where}: {type(e).__name__}: {e}"])
timings["build"] = round(time.time() - t, 2)

scene = bpy.context.scene
objs = [o for o in kit.COLL.objects if o.type == 'MESH']
problems = []
if not kit.READER: problems.append("no reader position: call kit.reader(entrance, look)")
if not any(o.name == "SkyDome" for o in objs): problems.append("no sky: call kit.sky(zenith, horizon)")
if not any(o.type == 'LIGHT' for o in kit.COLL.objects): problems.append("no light: call kit.sun(...) or kit.lamp(...)")
for o in objs:
    if not o.data.materials: problems.append(f"{o.name} has no material")
dg = bpy.context.evaluated_depsgraph_get()


def tri_count(o):
    e = o.evaluated_get(dg); me = e.to_mesh(); n = sum(len(p.vertices) - 2 for p in me.polygons); e.to_mesh_clear(); return n


tris = sum(tri_count(o) for o in objs if o.name != "SkyDome")
groups = {}
for o in objs:
    if o.data.materials: groups.setdefault(o.data.materials[0].name, []).append(o)
if tris > MAX_TRIS: problems.append(f"{tris} triangles: over the {MAX_TRIS} limit (target {TARGET_TRIS})")
if len(groups) > MAX_MESHES: problems.append(f"{len(groups)} materials: over the {MAX_MESHES} limit (each material is one mesh)")
if kit.READER:
    eye = kit.READER["entrance"] + Vector((0, 0, kit.READER["eye"]))
    # nothing solid between the eye and 0.9 m toward the look point (the page sits there)
    d = (kit.READER["look"] - eye); d.z = 0
    if d.length < 0.5: problems.append("the look point is too close to the reader (put it at least a few metres away)")
    hit, loc, *_ = scene.ray_cast(dg, eye, (kit.READER["look"] - eye).normalized(), distance=1.2)
    if hit: problems.append("something solid is within 1.2 m in front of the reader's eyes, where the page goes")
    hit, loc, *_ = scene.ray_cast(dg, eye, Vector((0, 0, -1)), distance=3.0)
    if hit and (eye.z - loc.z) < 1.2: problems.append("the reader is standing inside or on top of something (eye less than 1.2 m above the surface below)")
if problems:
    done(False, problems, triangles=tris, meshes=len(groups))

# ---------------------------------------------------------------- 3. check views

def use_gpu():
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dt in ("METAL", "OPTIX", "CUDA", "HIP"):
            try:
                prefs.compute_device_type = dt; prefs.get_devices()
                if any(d.type == dt for d in prefs.devices):
                    for d in prefs.devices: d.use = True
                    scene.cycles.device = 'GPU'; return dt
            except Exception:
                continue
    except Exception:
        pass
    return "CPU"


device = use_gpu()
scene.render.engine = 'CYCLES'; scene.cycles.use_denoising = True
scene.view_settings.view_transform = 'AgX'
scene.render.film_transparent = False
cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data); scene.collection.objects.link(cam); scene.camera = cam
cam_data.angle = math.radians(78); cam_data.clip_end = 400
eye = kit.READER["entrance"] + Vector((0, 0, kit.READER["eye"]))
fwd = kit.READER["look"] - eye
yaw = math.atan2(fwd.y, fwd.x); pitch = math.atan2(fwd.z, math.hypot(fwd.x, fwd.y))
views = {"thumb": (0, pitch), "left": (70, -0.08), "right": (-70, -0.08), "behind": (180, -0.05), "down": (25, -0.75)}
out = args.out; os.makedirs(os.path.join(out, "views"), exist_ok=True)
luma = {}
t = time.time()
for vname, (dyaw, p) in views.items():
    y = yaw + math.radians(dyaw)
    cam.location = eye
    d = Vector((math.cos(y) * math.cos(p), math.sin(y) * math.cos(p), math.sin(p)))
    cam.rotation_mode = 'QUATERNION'; cam.rotation_quaternion = d.to_track_quat('-Z', 'Y')
    big = vname == "thumb"
    scene.render.resolution_x, scene.render.resolution_y = (960, 600) if big else (480, 300)
    scene.cycles.samples = 48 if big else 16
    path = os.path.join(out, "views", f"{vname}.png")
    scene.render.filepath = path; scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path); px = img.pixels[:]; n = len(px) // 4
    luma[vname] = round(sum(0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2] for i in range(0, len(px), 4 * 7)) / max(1, n // 7), 3)
    bpy.data.images.remove(img)
# the exposure the baked room is shown at: from the linear radiance the reader's eyes receive (not from texture
# averages, which a dark underside or an unlit floor can skew)
y = yaw; d = Vector((math.cos(y) * math.cos(pitch), math.sin(y) * math.cos(pitch), math.sin(pitch)))
cam.rotation_quaternion = d.to_track_quat('-Z', 'Y')
scene.view_settings.view_transform = 'Standard'; scene.render.resolution_x, scene.render.resolution_y = 240, 150; scene.cycles.samples = 16
lin_path = os.path.join(out, "views", "exposure.exr")
scene.render.image_settings.file_format = 'OPEN_EXR'; scene.render.filepath = lin_path
bpy.ops.render.render(write_still=True)
im = bpy.data.images.load(lin_path); import numpy as np
va = np.empty(len(im.pixels), np.float32); im.pixels.foreach_get(va); va = va.reshape(-1, 4)
vl = 0.2126 * va[:, 0] + 0.7152 * va[:, 1] + 0.0722 * va[:, 2]; vl = vl[vl > 1e-5]
view_logavg = float(np.exp(np.mean(np.log(vl)))) if vl.size else 0.18
bpy.data.images.remove(im); scene.view_settings.view_transform = 'AgX'; scene.render.image_settings.file_format = 'PNG'
timings["views"] = round(time.time() - t, 2)
if luma["thumb"] < 0.03: problems.append(f"the reading view is almost black (mean brightness {luma['thumb']}): light the room")
if luma["thumb"] > 0.88: problems.append(f"the reading view is washed out (mean brightness {luma['thumb']}): less light")
if problems:
    done(False, problems, triangles=tris, meshes=len(groups), luma=luma)

# ---------------------------------------------------------------- 4. bake light into textures, export unlit

t = time.time()
bpy.ops.object.select_all(action='DESELECT')
merged = []
for mname, os_ in groups.items():
    for o in os_: o.select_set(True)
    bpy.context.view_layer.objects.active = os_[0]
    bpy.ops.object.convert(target='MESH')
    if len(os_) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = "SkyDome" if mname == "M_SkyDome" else ("MESH_" + mname[2:])
    merged.append(o); bpy.ops.object.select_all(action='DESELECT')
import numpy as np
scene.cycles.samples = args.samples
tex_dir = os.path.join(out, "textures"); os.makedirs(tex_dir, exist_ok=True)
texels = 0; baked = []
cards = [o for o in merged if o.data.materials[0].get("card")]
for o in merged:
    m = o.data.materials[0]; nt = m.node_tree
    if o in cards: continue   # grass and flower blades: too thin to bake; shaded from a gradient below
    area = sum(p.area for p in o.data.polygons)
    size = 1 << max(6, min(11 if o.name != "SkyDome" else 10, int(math.log2(max(64, math.sqrt(area) * 40)) + 0.5)))
    size = min(size, args.tex * (2 if area > 400 else 1))
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.008)
    bpy.ops.object.mode_set(mode='OBJECT')
    img = bpy.data.images.new("H_" + o.name, size, size, alpha=False, float_buffer=True)   # linear HDR radiance
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
    for n in nt.nodes: n.select = False
    tex.select = True; nt.nodes.active = tex
    if o.name == "SkyDome": bpy.ops.object.bake(type='EMIT', margin=8, use_clear=True)
    else: bpy.ops.object.bake(type='COMBINED', margin=8, use_clear=True,
                              pass_filter={'EMIT', 'DIRECT', 'INDIRECT', 'COLOR', 'DIFFUSE', 'GLOSSY', 'TRANSMISSION'})
    # Metal can return a black bake without any error when GPU memory runs short (seen with other Blender jobs
    # running): an all-dark result is baked again on the CPU
    if o.name != "SkyDome":
        chk = np.empty(size * size * 4, np.float32); img.pixels.foreach_get(chk)
        if float(chk.reshape(-1, 4)[:, :3].max()) < 1e-4 and scene.cycles.device == 'GPU':
            print("black bake on the GPU for", o.name, "- baking again on the CPU"); scene.cycles.device = 'CPU'
            bpy.ops.object.bake(type='COMBINED', margin=8, use_clear=True,
                                pass_filter={'EMIT', 'DIRECT', 'INDIRECT', 'COLOR', 'DIFFUSE', 'GLOSSY', 'TRANSMISSION'})
            scene.cycles.device = 'GPU' if device != "CPU" else 'CPU'
    texels += size * size; baked.append((o, tex, img))
timings["bake"] = round(time.time() - t, 2)

# one exposure for the whole room (from the log-average radiance of everything but the sky), then a soft
# highlight roll-off and sRGB encoding, so the unlit result reads like the check render rather than clipping
import numpy as np
def srgb(a): return np.where(a <= 0.0031308, a * 12.92, 1.055 * np.power(np.maximum(a, 0), 1 / 2.4) - 0.055).astype(np.float32)
arrs = {}
for o, tex, img in baked:
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32); img.pixels.foreach_get(a); arrs[o.name] = a.reshape(-1, 4)
    print("baked", o.name, img.size[0], "mean", float(arrs[o.name][:, :3].mean()), "max", float(arrs[o.name][:, :3].max()))
lums = np.concatenate([0.2126 * a[::5, 0] + 0.7152 * a[::5, 1] + 0.0722 * a[::5, 2] for k, a in arrs.items() if k != "SkyDome"] or [np.array([0.18])])
lums = lums[lums > 1e-5]   # texels outside every UV island are empty, not dark
if lums.size == 0: lums = np.array([0.18])
logavg = float(np.exp(np.mean(np.log(np.maximum(lums, 1e-4)))))
exposure = 0.22 / max(view_logavg, 1e-4); white = 3.0   # (logavg of all texels kept for the report only)
for o, tex, img in baked:
    # the sky's emission is already a display colour (kit.sky); everything else is radiance to expose
    a = arrs[o.name][:, :3] * (exposure if o.name != "SkyDome" else 0.9)
    if o.name != "SkyDome": a = a * (1 + a / (white * white)) / (1 + a)
    a = srgb(np.clip(a, 0, 1))   # foreach_set stores values as given: encode for the sRGB texture
    outimg = bpy.data.images.new("T_" + o.name, img.size[0], img.size[1], alpha=False)
    rgba = np.concatenate([a, np.ones((a.shape[0], 1), dtype=np.float32)], axis=1).astype(np.float32).ravel()
    outimg.pixels.foreach_set(rgba); outimg.update()   # (setting a colour space now would regenerate it black)
    outimg.filepath_raw = os.path.join(tex_dir, outimg.name + ".png"); outimg.file_format = 'PNG'; outimg.save(); outimg.pack()
    tex.image = outimg; bpy.data.images.remove(img)
    # unlit: the baked colour straight to the output (exported as KHR_materials_unlit)
    nt = o.data.materials[0].node_tree
    keep = tex.name
    for n in list(nt.nodes):
        if n.name != keep: nt.nodes.remove(n)
    tex = nt.nodes[keep]
    bg = nt.nodes.new("ShaderNodeBackground"); mo = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], bg.inputs["Color"]); nt.links.new(bg.outputs["Background"], mo.inputs["Surface"])
# blades: their colour from root (shaded) to tip (lit), at the brightness the bake gave the largest lit surface
ref = max((o for o, _, _ in baked if o.name != "SkyDome"), key=lambda o: sum(p.area for p in o.data.polygons), default=None)
light = 0.8
if ref is not None:
    a = arrs[ref.name][:, :3]; nz = a[a.sum(axis=1) > 1e-5] * exposure; nz = nz * (1 + nz / (white * white)) / (1 + nz)
    base = max(1e-3, float(np.mean(ref.data.materials[0].get("base", [0.3, 0.3, 0.3]))))
    light = float(np.clip(nz.mean() / base, 0.2, 2.5)) if nz.size else 0.8
for o in cards:
    m = o.data.materials[0]; base = np.array(m.get("base", [0.3, 0.4, 0.2]), dtype=np.float32)
    img = bpy.data.images.new("T_" + o.name, 4, 64, alpha=False)
    v = np.linspace(0, 1, 64, dtype=np.float32)[:, None]
    col = srgb(np.clip(base[None, :] * light * (0.42 + 0.68 * v ** 0.8), 0, 1))
    px = np.concatenate([np.repeat(col, 4, axis=0).reshape(64, 4, 3), np.ones((64, 4, 1), np.float32)], axis=2).ravel()
    img.pixels.foreach_set(px); img.update()
    img.filepath_raw = os.path.join(tex_dir, img.name + ".png"); img.file_format = 'PNG'; img.save(); img.pack()
    nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = 'Linear'
    bg = nt.nodes.new("ShaderNodeBackground"); mo = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], bg.inputs["Color"]); nt.links.new(bg.outputs["Background"], mo.inputs["Surface"])
    texels += 256
timings["tonemap"] = round(time.time() - t - timings["bake"], 2)
for o in list(scene.objects):
    if o.type in ('LIGHT', 'CAMERA'): bpy.data.objects.remove(o, do_unlink=True)
t = time.time()
gl = os.path.join(out, "room.gltf")
bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                          export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=88, export_lights=False, export_cameras=False)
timings["export"] = round(time.time() - t, 2)
if not os.environ.get("ROOMGEN_KEEP_PNG"):
    for f in os.listdir(tex_dir):
        if f.endswith(".png"): os.remove(os.path.join(tex_dir, f))
timings["total"] = round(time.time() - T0, 2)
e = kit.READER["entrance"]; l = kit.READER["look"]
done(True, [], triangles=tris, meshes=len(merged), textures=len(merged), texels=texels, luma=luma, device=device, exposure=round(exposure, 3), texel_logavg=round(logavg, 4), view_logavg=round(view_logavg, 4),
     entrance=[e.x, e.y, e.z], look=[l.x, l.y, l.z], over_target=tris > TARGET_TRIS)
