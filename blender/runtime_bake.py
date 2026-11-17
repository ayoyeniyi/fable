"""
Fable runtime bake: make a hand-built room loadable at runtime (a downloadable scene room, docs/SCENE_ROOMS_PIPELINE.md).

  blender -b -P blender/runtime_bake.py -- out/<id> [--wind 0.4] [--wind-toward 90] [--ambience "birds:0.6+wind-grass:0.5"]
                                                    [--indoor] [--light-max 1024] [--samples 96] [--exposure-stops 0]

A room built for Unity gets its light from Unity's lightmapper, which cannot run on the headset; a room downloaded at
runtime has none. This bakes the room's light in Blender instead, the way blender/roomgen.py lights generated rooms,
but keeps the albedo's detail: it opens the kit's out/<id>/<name>_baked.blend (meshes merged per material, baked
albedo textures, the lights still there), gives every lit mesh a second UV set and bakes Cycles diffuse irradiance
(direct + indirect: sun, sky, lamps, bounce, contact shadows; cut-out cards shadow with their alpha) into a light
texture on it. One exposure for the whole room comes from a linear render at the reader's eye.

Output in out/<id>/runtime/:
  room.gltf, room.bin, textures/   per material: base colour (UV 0, alpha kept for cut-out cards) and the light texture
                                   as the emissive texture on UV 1. No roughness or normal maps. Sky, far.* backdrops and
                                   emissive surfaces: unlit (KHR_materials_unlit), drawn as they are. water.*: base colour.
                                   The headset draws base x light x lightScale with a soft highlight roll-off
                                   (Unity: Fable/SceneRoom shader, SceneRoomView.cs).
  room.json                        anchors, wind, ambience, exposure, lightScale, sizes, living names
  view.jpg                         the reader's view rendered in Blender (the chapter card's picture)
The last line printed is  FABLE_RUNTIME {json}.
"""
import bpy, sys, os, json, math, time, argparse, glob
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("room", help="out/<id>: the kit's export folder, with <name>_baked.blend")
ap.add_argument("--blend", default="", help="the baked .blend (default: the one *_baked.blend in the room folder)")
ap.add_argument("--out", default="", help="default <room>/runtime")
ap.add_argument("--wind", type=float, default=-1.0, help="0 calm .. 2 gale (default 0.35 outdoors, 0 indoors)")
ap.add_argument("--wind-toward", type=float, default=60.0, help="compass degrees the wind blows toward, Blender frame (0 = +Y)")
ap.add_argument("--ambience", default="", help="kind:volume+kind:volume from the sound library")
ap.add_argument("--indoor", action="store_true")
ap.add_argument("--light-max", type=int, default=1024)
ap.add_argument("--base-max", type=int, default=2048)
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--exposure-stops", type=float, default=0.0)
ap.add_argument("--no-view", action="store_true")
args = ap.parse_args(argv)

T0 = time.time(); timings = {}
room = os.path.abspath(args.room); rid = os.path.basename(room.rstrip("/"))
blend = args.blend or next(iter(sorted(glob.glob(os.path.join(room, "*_baked.blend")))), "")
if not blend or not os.path.exists(blend):
    print("FABLE_RUNTIME " + json.dumps({"ok": False, "problems": [f"no *_baked.blend in {room}: export the room with its kit's bake_and_export first"]})); sys.exit(1)
out = os.path.abspath(args.out or os.path.join(room, "runtime"))
os.makedirs(os.path.join(out, "textures"), exist_ok=True)
for f in glob.glob(os.path.join(out, "textures", "*")): os.remove(f)
bpy.ops.wm.open_mainfile(filepath=blend)
scene = bpy.context.scene
EYE = 1.55

def find(name): return bpy.data.objects.get(name)
ent, look = find("anchor.reader.entrance"), find("anchor.reader.look")
problems = []
if not ent: problems.append("no anchor.reader.entrance")
if not look: problems.append("no anchor.reader.look")
if problems:
    print("FABLE_RUNTIME " + json.dumps({"ok": False, "problems": problems})); sys.exit(1)
ent_p = ent.matrix_world.translation.copy(); look_p = look.matrix_world.translation.copy()
outdoor = not args.indoor and any(o.type == 'LIGHT' and o.data.type == 'SUN' for o in scene.objects)
wind = args.wind if args.wind >= 0 else (0.35 if outdoor else 0.0)

for o in list(scene.objects):
    if o.type == 'CAMERA': bpy.data.objects.remove(o, do_unlink=True)
meshes = [o for o in scene.objects if o.type == 'MESH' and o.data.materials and o.visible_get()]
# one material per mesh (the kits merge by material); a material shared by two meshes is copied so each gets its own light
seen = set()
for o in meshes:
    m = o.data.materials[0]
    if m.name in seen: o.data.materials[0] = m.copy()
    seen.add(o.data.materials[0].name)

def bsdf_of(m): return next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m.use_nodes else None
def is_unlit(o):
    n = o.name
    if n.startswith("SkyDome") or n.startswith("far.") or "Sky" in n: return True
    b = bsdf_of(o.data.materials[0])
    if b is None: return True
    return b.inputs["Emission Strength"].default_value > 0.5 and (b.inputs["Emission Color"].is_linked or sum(b.inputs["Emission Color"].default_value[:3]) > 0.5)
water = [o for o in meshes if o.name.startswith("water.")]
unlit = [o for o in meshes if o not in water and is_unlit(o)]
lit = [o for o in meshes if o not in water and o not in unlit]

def use_gpu():
    if os.environ.get("FABLE_CYCLES_DEVICE", "").upper() == "CPU": return "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dt in ("METAL", "OPTIX", "CUDA", "HIP"):
            try:
                prefs.compute_device_type = dt; prefs.get_devices()
                if any(d.type == dt for d in prefs.devices):
                    for d in prefs.devices: d.use = True
                    scene.cycles.device = 'GPU'; return dt
            except Exception: continue
    except Exception: pass
    return "CPU"
scene.render.engine = 'CYCLES'; device = use_gpu()

# ---------------------------------------------------------------- 1. exposure, and the reader's view
cam_data = bpy.data.cameras.new("rb_cam"); cam = bpy.data.objects.new("rb_cam", cam_data); scene.collection.objects.link(cam); scene.camera = cam
cam_data.angle = math.radians(78); cam_data.clip_end = 2000; cam_data.clip_start = 0.05
eye = ent_p + Vector((0, 0, EYE)); fwd = look_p - eye
if fwd.length < 1e-3: fwd = Vector((0, 1, 0))
cam.location = eye; cam.rotation_mode = 'QUATERNION'; cam.rotation_quaternion = fwd.normalized().to_track_quat('-Z', 'Y')
t = time.time()
scene.view_settings.view_transform = 'Standard'; scene.view_settings.exposure = 0.0; scene.view_settings.look = 'None'
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 240, 150, 100
scene.cycles.samples = 16; scene.cycles.use_denoising = False; scene.render.film_transparent = False
lin_path = os.path.join(out, "exposure.exr"); scene.render.image_settings.file_format = 'OPEN_EXR'; scene.render.filepath = lin_path
bpy.ops.render.render(write_still=True)
im = bpy.data.images.load(lin_path); va = np.empty(len(im.pixels), np.float32); im.pixels.foreach_get(va); va = va.reshape(-1, 4)
vl = 0.2126 * va[:, 0] + 0.7152 * va[:, 1] + 0.0722 * va[:, 2]; vl = vl[vl > 1e-5]
view_logavg = float(np.exp(np.mean(np.log(vl)))) if vl.size else 0.18
bpy.data.images.remove(im); os.remove(lin_path)
exposure = 0.22 / max(view_logavg, 1e-4) * (2.0 ** args.exposure_stops)
WHITE = 3.0
if not args.no_view:
    scene.view_settings.view_transform = 'AgX'; scene.view_settings.exposure = math.log2(exposure / 0.18 * 0.18)   # same multiplier as the bake
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.cycles.samples = 64; scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = 'JPEG'; scene.render.image_settings.quality = 86
    scene.render.filepath = os.path.join(out, "view.jpg"); bpy.ops.render.render(write_still=True)
timings["view"] = round(time.time() - t, 1)

# ---------------------------------------------------------------- 2. bake diffuse irradiance into a light texture per lit mesh
t = time.time()
scene.cycles.samples = args.samples; scene.cycles.use_denoising = False
scene.render.bake.margin = 6
irr = {}
for o in lit:
    m = o.data.materials[0]; nt = m.node_tree
    area = sum(p.area for p in o.data.polygons)
    size = 1 << max(6, min(int(math.log2(args.light_max)), int(math.log2(max(64.0, math.sqrt(area) * 12.0)) + 0.5)))
    uvs = o.data.uv_layers
    if not uvs: uvs.new(name="UVMap")
    base_uv = uvs[0]; base_uv.active_render = True
    lu = uvs.get("Light") or uvs.new(name="Light")
    uvs.active = lu
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.006)
    bpy.ops.object.mode_set(mode='OBJECT')
    # texture lookups of the albedo keep UV 0 whatever is active (explicit UV Map node)
    for n in [n for n in nt.nodes if n.type == 'TEX_IMAGE' and not n.inputs["Vector"].is_linked]:
        uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = base_uv.name; nt.links.new(uvn.outputs["UV"], n.inputs["Vector"])
    img = bpy.data.images.new("L_" + o.name, size, size, alpha=False, float_buffer=True)
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.name = "rb_light"
    for n in nt.nodes: n.select = False
    tex.select = True; nt.nodes.active = tex
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=6, use_clear=True, uv_layer="Light")
    a = np.empty(size * size * 4, np.float32); img.pixels.foreach_get(a); a = a.reshape(size, size, 4)[:, :, :3]
    if float(a.max()) < 1e-5 and scene.cycles.device == 'GPU':
        print("black bake on the GPU for", o.name, "- baking again on the CPU", flush=True); scene.cycles.device = 'CPU'
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=6, use_clear=True, uv_layer="Light")
        a2 = np.empty(size * size * 4, np.float32); img.pixels.foreach_get(a2); a = a2.reshape(size, size, 4)[:, :, :3]
        scene.cycles.device = 'GPU'
    # a light 1-2-1 blur takes the bake's sample noise off (irradiance is smooth; the margin keeps island edges)
    k = np.array([0.25, 0.5, 0.25], np.float32)
    b = a.copy()
    for ax in (0, 1):
        b = k[0] * np.roll(b, 1, axis=ax) + k[1] * b + k[2] * np.roll(b, -1, axis=ax)
    irr[o.name] = (o, tex, img, b * exposure)
    print("baked light", o.name, size, "mean", float(b.mean()), flush=True)
timings["bake"] = round(time.time() - t, 1)

# one scale for every light texture: 8-bit holds exposed irradiance / lightScale (the 99.5th percentile, 1..8)
allv = np.concatenate([v[3].reshape(-1, 3).max(axis=1)[::7] for v in irr.values()] or [np.array([1.0])])
allv = allv[allv > 1e-5]
light_scale = float(np.clip(np.percentile(allv, 99.5) if allv.size else 1.0, 1.0, 8.0))
def srgb(x): return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.maximum(x, 0), 1 / 2.4) - 0.055).astype(np.float32)

def first_image(nt, sock):
    """the image node feeding a BSDF input (through UV/normal nodes), or None"""
    if not sock.is_linked: return None
    n = sock.links[0].from_node
    while n and n.type != 'TEX_IMAGE':
        ins = [i for i in n.inputs if i.is_linked]
        n = ins[0].links[0].from_node if ins else None
    return n

def cap(img_node, limit):
    if img_node and img_node.image and max(img_node.image.size) > limit:
        w, h = img_node.image.size; s = limit / max(w, h); img_node.image.scale(max(1, int(w * s)), max(1, int(h * s)))

# ---------------------------------------------------------------- 3. materials for export
for o in meshes:
    m = o.data.materials[0]; nt = m.node_tree; b = bsdf_of(m)
    base_sock = b.inputs["Base Color"] if b else None
    base_img = first_image(nt, base_sock) if b else None
    if b is not None and base_img is None and b.inputs["Emission Color"].is_linked: base_img = first_image(nt, b.inputs["Emission Color"])
    base_col = tuple(base_sock.default_value) if base_sock is not None else (0.8, 0.8, 0.8, 1)
    alpha_img = first_image(nt, b.inputs["Alpha"]) if b and b.inputs["Alpha"].is_linked else None
    alpha_from = b.inputs["Alpha"].links[0].from_socket.name if alpha_img else None
    cap(base_img, args.base_max)
    keep = {n for n in (base_img, alpha_img) if n}
    lightn = nt.nodes.get("rb_light") if o in lit else None
    if lightn: keep.add(lightn)
    for n in list(nt.nodes):
        if n not in keep: nt.nodes.remove(n)
    mo = nt.nodes.new("ShaderNodeOutputMaterial")
    if o in lit and lightn:
        _, _, img, v = irr[o.name]
        size = img.size[0]
        enc = srgb(np.clip(v / light_scale, 0, 1)).reshape(-1, 3)
        out_img = bpy.data.images.new("T_" + o.name + "_Light", size, size, alpha=False)
        out_img.pixels.foreach_set(np.concatenate([enc, np.ones((enc.shape[0], 1), np.float32)], axis=1).ravel()); out_img.update()
        out_img.filepath_raw = os.path.join(out, "textures", out_img.name + ".png"); out_img.file_format = 'PNG'; out_img.save(); out_img.pack()
        lightn.image = out_img; bpy.data.images.remove(img)
        luv = nt.nodes.new("ShaderNodeUVMap"); luv.uv_map = "Light"; nt.links.new(luv.outputs["UV"], lightn.inputs["Vector"])
        nb = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(nb.outputs["BSDF"], mo.inputs["Surface"])
        nb.inputs["Roughness"].default_value = 1.0; nb.inputs["Metallic"].default_value = 0.0
        nt.links.new(lightn.outputs["Color"], nb.inputs["Emission Color"]); nb.inputs["Emission Strength"].default_value = 1.0
        if base_img:
            buv = nt.nodes.new("ShaderNodeUVMap"); buv.uv_map = o.data.uv_layers[0].name; nt.links.new(buv.outputs["UV"], base_img.inputs["Vector"])
            nt.links.new(base_img.outputs["Color"], nb.inputs["Base Color"])
        else: nb.inputs["Base Color"].default_value = base_col
        if alpha_img: nt.links.new(alpha_img.outputs[alpha_from if alpha_from in alpha_img.outputs else "Alpha"], nb.inputs["Alpha"])
    elif o in water:
        nb = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(nb.outputs["BSDF"], mo.inputs["Surface"])
        if base_img: nt.links.new(base_img.outputs["Color"], nb.inputs["Base Color"])
        else: nb.inputs["Base Color"].default_value = base_col
        nb.inputs["Roughness"].default_value = 0.08
    else:
        # unlit: exported as KHR_materials_unlit (a Background shader straight to the output)
        bg = nt.nodes.new("ShaderNodeBackground"); nt.links.new(bg.outputs["Background"], mo.inputs["Surface"])
        if base_img: nt.links.new(base_img.outputs["Color"], bg.inputs["Color"])
        else: bg.inputs["Color"].default_value = base_col
        if alpha_img:   # an unlit cut-out (a distant tree line): mix with transparency so the exporter keeps the alpha
            tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
            nt.links.new(alpha_img.outputs[alpha_from if alpha_from in alpha_img.outputs else "Alpha"], mx.inputs[0])
            nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(bg.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], mo.inputs["Surface"])
    # drop UV layers nothing reads (keep UV 0 and the light UV)
    keepuv = {o.data.uv_layers[0].name, "Light"} if o.data.uv_layers else set()
    for u in [u.name for u in o.data.uv_layers if u.name not in keepuv]: o.data.uv_layers.remove(o.data.uv_layers[u])
    if o.data.uv_layers.get("Light") is not None and o not in lit: o.data.uv_layers.remove(o.data.uv_layers["Light"])
    if o.data.uv_layers: o.data.uv_layers.active = o.data.uv_layers[0]

# ---------------------------------------------------------------- 4. export
for o in list(scene.objects):
    if o.type in ('LIGHT', 'CAMERA'): bpy.data.objects.remove(o, do_unlink=True)
t = time.time()
gl = os.path.join(out, "room.gltf")
bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                          export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=86, export_lights=False, export_cameras=False,
                          export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_extras=True)
timings["export"] = round(time.time() - t, 1)
# (PNGs the glTF does not reference -- the light intermediates -- are removed below; cut-out atlases stay PNG for alpha)
with open(gl) as f: g = json.load(f)
used = [im.get("uri") for im in g.get("images", []) if im.get("uri")]
for f in os.listdir(os.path.join(out, "textures")):
    if "textures/" + f not in used: os.remove(os.path.join(out, "textures", f))
tex_bytes = sum(os.path.getsize(os.path.join(out, u)) for u in used)
bin_bytes = sum(os.path.getsize(os.path.join(out, b["uri"])) for b in g.get("buffers", []) if b.get("uri"))
light_tc1 = sum(1 for mt in g.get("materials", []) if mt.get("emissiveTexture", {}).get("texCoord") == 1)
if light_tc1 < len(lit): problems.append(f"only {light_tc1} of {len(lit)} lit materials exported their light texture on UV 1")
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
living = sorted(n["name"] for n in g.get("nodes", []) if n.get("name", "").split(".")[0] in ("veg", "cloth", "water", "fx", "sound", "flame"))
names = {n.get("name") for n in g.get("nodes", [])}
for need in ("anchor.reader.entrance", "anchor.reader.look"):
    if need not in names: problems.append(f"{need} was not exported")
# Unity's compass (0 = +Z) is a Blender bearing (0 = +Y) plus 180: the glTF import turns +Y into -Z and mirrors X
meta = {"id": rid, "version": 1, "outdoor": outdoor, "wind": round(wind, 3), "windToward": round((args.wind_toward + 180.0) % 360.0, 1),
        "windTowardBlender": args.wind_toward, "ambience": args.ambience or ("birds:0.6+wind-grass:0.6" if outdoor else "room-tone"),
        "exposure": round(exposure, 4), "lightScale": round(light_scale, 4), "white": WHITE, "eye": EYE,
        "anchors": {"entrance": [round(x, 3) for x in ent_p], "look": [round(x, 3) for x in look_p]},
        "triangles": tris, "meshes": len(meshes), "litMeshes": len(lit), "unlitMeshes": len(unlit), "water": len(water),
        "textureBytes": tex_bytes, "binBytes": bin_bytes, "living": living, "device": device, "timings": timings,
        "source": os.path.relpath(blend, os.path.dirname(os.path.dirname(room))) if room.count(os.sep) > 1 else blend}
with open(os.path.join(out, "room.json"), "w") as f: json.dump(meta, f, indent=1)
timings["total"] = round(time.time() - T0, 1)
print("FABLE_RUNTIME " + json.dumps({"ok": not problems, "problems": problems, "out": out, "triangles": tris, "meshes": len(meshes),
                                    "bytes": tex_bytes + bin_bytes, "lightScale": light_scale, "exposure": exposure, "timings": timings}))
