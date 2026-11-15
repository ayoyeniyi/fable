"""
Shared helpers for the three hand-built Frankenstein rooms (build_ingolstadt_garret.py, build_mer_de_glace.py,
build_arctic_ice.py).

Everything in blender/wotw_kit.py (node-material shorthands, mesh primitives, numpy painting, foliage CardMesh,
anchors, cameras, the bake -> merge-by-material step) is re-exported from here, so a room script imports one module.
Additions for these rooms:

  * fx(): fx.fire.* / fx.candle.* / fx.lantern.* empties carrying a custom property `radius` (glTF extras), and
    sound(): sound.<kind>.* empties (docs/LIVING_SCENES.md)
  * light(): a point / spot / sun light named for FableBuild's per-scene overrides (Lamp.* indoors, light.* outdoors)
  * sky_dome(): an unlit dome whose UV v follows a caller's elevation mapping (rows packed toward the horizon)
  * polar_ground(): a terrain disc in rings round the reader, its UVs in log-polar layout so a numpy-painted ground
    texture has its finest texels at the reader's feet (as Horsell Common)
  * render_stills(): Cycles stills stamped "Blender render - <room> - <view>" in the corner
  * bake_and_export(): wotw_kit's step, exported with export_extras=True (so the fx radius reaches Unity)

Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, os, json
import numpy as np
from mathutils import Vector, Matrix
import wotw_kit as K
from wotw_kit import *          # noqa: F401,F403  (re-export the shared helpers)


def fx(name, loc, radius=0.05):
    """fx.fire.* / fx.candle.* / fx.lantern.* empty: display size and custom property `radius` = flame radius (m)."""
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'SPHERE'; e.empty_display_size = radius
    e.location = loc; e["radius"] = float(radius); K.link(e)
    return e


def sound(name, loc):
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'CONE'; e.empty_display_size = 0.3
    e.location = loc; K.link(e)
    return e


def light(name, kind, energy, color, loc, size=0.05, aim=None, spot=None, shadow=True, angle=None):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    if kind == 'SUN':
        ld.angle = angle if angle is not None else math.radians(1.0)
    else:
        ld.shadow_soft_size = size
    if spot: ld.spot_size, ld.spot_blend = spot
    ld.use_shadow = shadow
    lo = bpy.data.objects.new(name, ld); lo.location = loc
    if aim is not None:
        lo.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    K.link(lo)
    return lo


def sun(name, energy, color, direction_to_sun, angle_deg=1.0, shadow=True):
    d = Vector(direction_to_sun).normalized()
    return light(name, 'SUN', energy, color, tuple(d * 40), aim=(0, 0, 0), shadow=shadow, angle=math.radians(angle_deg))


def sky_dome(name, mat, radius, el0, v_of, seg=64, rings=14, centre=(0, 0, 0)):
    """Inward-facing dome from elevation el0 (deg, below the horizon) to the zenith; u = compass azimuth / 360
    (north = 0, east = 0.25), v = v_of(elevation deg)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    els = [el0 + (89.0 - el0) * (j / rings) ** 1.6 for j in range(rings + 1)]
    C = Vector(centre); grid = []
    for el in els:
        e = math.radians(el)
        grid.append([bm.verts.new(C + Vector((radius * math.cos(e) * math.sin(TWO_PI * i / seg), radius * math.cos(e) * math.cos(TWO_PI * i / seg),
                                              radius * math.sin(e)))) for i in range(seg + 1)])
    pole = bm.verts.new(C + Vector((0, 0, radius)))
    for j in range(rings):
        for i in range(seg):
            f_ = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for l, uv in zip(f_.loops, [(i / seg, v_of(els[j])), ((i + 1) / seg, v_of(els[j])), ((i + 1) / seg, v_of(els[j + 1])), (i / seg, v_of(els[j + 1]))]):
                l[uvl].uv = uv
    for i in range(seg):
        f_ = bm.faces.new((grid[-1][i], grid[-1][i + 1], pole))
        for l, uv in zip(f_.loops, [(i / seg, v_of(els[-1])), ((i + 1) / seg, v_of(els[-1])), ((i + 0.5) / seg, 1.0)]):
            l[uvl].uv = uv
    bm.normal_update()
    for f_ in bm.faces:
        if f_.normal.dot(f_.calc_center_median() - C) > 0: f_.normal_flip()
        f_.smooth = True
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat); K.link(o)
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False; o.visible_transmission = False
    K.KEEP_UV.add(mat.name)
    return o


def ring_radii(near_r, step0=0.35, k=0.075, step_max=2.4):
    rs = [0.0]; r = 0.0
    while r < near_r:
        step = min(step_max, step0 + r * k); r = min(near_r, r + step); rs.append(r)
    return rs


def polar_ground(name, gz, near_r, mat, v_of_r, NS=96, rs=None, centre=(0.0, 0.0)):
    """A terrain disc round `centre` out to near_r: rings (fine near the centre), heights from gz(x, y) (numpy-able),
    UV u = angle / 2pi (from +X, counter-clockwise), v = v_of_r(r). Returns (object, outer ring verts)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rs = rs or ring_radii(near_r); cx, cy = centre
    c = bm.verts.new((cx, cy, float(gz(np.array(cx), np.array(cy)))))
    rings = []
    for r in rs[1:]:
        th = np.arange(NS) / NS * TWO_PI
        xs, ys = cx + r * np.cos(th), cy + r * np.sin(th); zs = gz(xs, ys)
        rings.append([bm.verts.new((float(a), float(b), float(z))) for a, b, z in zip(xs, ys, zs)])
    vr = [float(v_of_r(r)) for r in rs]
    for i in range(NS):
        j = (i + 1) % NS
        f = bm.faces.new((c, rings[0][i], rings[0][j]))
        for lp, uv in zip(f.loops, ((i / NS + 0.5 / NS, 0.0), (i / NS, vr[1]), ((i + 1) / NS, vr[1]))): lp[uvl].uv = uv
    for k in range(len(rings) - 1):
        for i in range(NS):
            j = (i + 1) % NS
            f = bm.faces.new((rings[k][i], rings[k + 1][i], rings[k + 1][j], rings[k][j]))
            for lp, uv in zip(f.loops, ((i / NS, vr[k + 1]), (i / NS, vr[k + 2]), ((i + 1) / NS, vr[k + 2]), ((i + 1) / NS, vr[k + 1]))): lp[uvl].uv = uv
    for f in bm.faces: f.smooth = True
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat); K.link(o)
    K.KEEP_UV.add(mat.name)
    return o, rings[-1]


def polar_uv_grid(N, near_r, r_of_v, centre=(0.0, 0.0)):
    """World (x, y) and texel footprint (m) for each texel of an N x N log-polar ground texture (rows = v, cols = u)."""
    u = (np.arange(N) + 0.5) / N; v = (np.arange(N) + 0.5) / N
    U, V = np.meshgrid(u, v)
    r = r_of_v(V); th = U * TWO_PI
    x = centre[0] + r * np.cos(th); y = centre[1] + r * np.sin(th)
    dr = np.gradient(r, axis=0); fp = np.maximum(np.abs(dr), r * TWO_PI / N)
    return x, y, fp


# ----------------------------------------------------------------------------- stamped stills
def render_stills(scene, cams, exposure=None, default_exp=0.0, label="", res=None):
    exposure = exposure or {}
    r = scene.render
    res = res or K.ARGS.res
    r.resolution_x = res; r.resolution_y = int(res * 9 / 16)
    r.image_settings.file_format = 'PNG'
    r.use_stamp = True
    for f in ("date", "time", "render_time", "frame", "frame_range", "memory", "hostname", "camera", "lens", "scene",
              "marker", "filename", "sequencer_strip", "note"):
        try: setattr(r, "use_stamp_" + f, False)
        except Exception: pass
    r.use_stamp_note = True
    r.stamp_font_size = max(12, res // 70)
    r.stamp_foreground = (0.85, 0.85, 0.85, 1); r.stamp_background = (0, 0, 0, 0.45)
    want = set(c.strip().lower() for c in K.ARGS.cams.split(",") if c.strip())
    for c in cams:
        view = c.name[4:].lower()
        if want and view not in want: continue
        scene.camera = c
        scene.view_settings.exposure = exposure.get(c.name, default_exp)
        r.stamp_note_text = f"Blender render - {label} - {view} - Cycles {scene.cycles.samples} spp"
        r.filepath = os.path.join(K.OUT, f"{K.ARGS.prefix}{view}.png")
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:
            print("GPU render failed, retrying on the CPU:", str(e)[:120]); scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", r.filepath)


# ----------------------------------------------------------------------------- bake + merge + export (extras on)
def bake_and_export(scene, gltf_name, size_for, keep_names=None, cams=(), blend_name=None, unlit=()):
    """As wotw_kit.bake_and_export, with export_extras=True. Meshes are joined by material (MESH_<material> or the
    keep_names living-scene name), procedural materials baked to BaseColor / Roughness / Normal, prebaked cards kept.
    `unlit`: material names whose baked colour is also the emission (backdrops seen through windows)."""
    keep_names = keep_names or {}
    T_ = K.ARGS.tex; OUT = K.OUT
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in K.COLL.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.select_all(action='DESELECT')
    groups = {}
    for o in K.COLL.objects:
        if o.type != 'MESH' or not o.data.materials: continue
        groups.setdefault(o.data.materials[0].name, []).append(o)
    merged = []
    for mname, objs in groups.items():
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active; o.name = keep_names.get(mname, "MESH_" + mname[2:])
        if mname not in K.WEIGHTED:
            for an in [a.name for a in o.data.color_attributes]: o.data.color_attributes.remove(o.data.color_attributes[an])
        else:
            ca = o.data.color_attributes
            for an in [a.name for a in ca if a.name != "Col"]: ca.remove(ca[an])
            if ca.get("Col"): ca.active_color = ca["Col"]
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    scene.cycles.samples = 1; scene.cycles.device = 'CPU'
    scene.render.bake.margin = 6
    tex_sizes = {}
    for o in merged:
        m = o.data.materials[0]; nt = m.node_tree
        if m.name in K.PREBAKED:
            tex_sizes[o.name] = max((n.image.size[0] for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image), default=0); continue
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        sizes = size_for.get(m.name, (T_ // 4,))
        if isinstance(sizes, int): sizes = (sizes,)
        sizes = tuple(max(32, s) for s in sizes)
        tex_sizes[o.name] = sizes[0]
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        if m.name not in K.KEEP_UV or not o.data.uv_layers:
            for uvn in [u.name for u in o.data.uv_layers]: o.data.uv_layers.remove(o.data.uv_layers[uvn])
            o.data.uv_layers.new(name="UVMap")
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
            bpy.ops.object.mode_set(mode='OBJECT')
        metallic = bsdf.inputs["Metallic"].default_value
        transm = bsdf.inputs["Transmission Weight"].default_value
        for sock in ("Metallic", "Transmission Weight", "Sheen Weight", "Coat Weight"):
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
        if m.name in unlit:
            nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"]); nb.inputs["Emission Strength"].default_value = 1.0
        elif emis > 0:
            nb.inputs["Emission Strength"].default_value = min(emis, 1.0)
            if elinked: nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"])
            else: nb.inputs["Emission Color"].default_value = ecol
    for c in cams: bpy.data.objects.remove(c)
    gl = os.path.join(OUT, gltf_name)
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='AUTO', export_lights=True, export_cameras=False,
                              export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_extras=True)
    tris = sum(K.tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    tdir = os.path.join(OUT, "textures")
    with open(gl) as f: gj = json.load(f)
    used = set(os.path.basename(im["uri"]) for im in gj.get("images", []))
    tex_bytes = sum(os.path.getsize(os.path.join(tdir, u)) for u in used if os.path.exists(os.path.join(tdir, u)))
    gpu = 0
    for im in bpy.data.images:
        if im.size[0] and ((im.name + ".png") in used or (im.name + ".jpg") in used):
            gpu += im.size[0] * im.size[1] * (1.0 if im.colorspace_settings.name == 'Non-Color' and 'Normal' in im.name else 0.444) * 1.33
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris} textures_on_disk={tex_bytes / 1e6:.1f}MB astc_est={gpu / 1e6:.1f}MB")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\ntextures_on_disk_mb={tex_bytes / 1e6:.2f}\nastc_estimate_mb={gpu / 1e6:.2f}\n")
        for o in sorted(merged, key=lambda o: -K.tri_count(o)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={K.tri_count(o)} tex={tex_sizes.get(o.name, 0)} colour={'yes' if o.data.color_attributes else 'no'}\n")
    if blend_name: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, blend_name))
    return merged
