"""
Fable: shared helpers for the three hand-built Around the World in Eighty Days rooms (build_reform_club.py,
build_mongolia_deck.py, build_pillaji_forest.py).

Builds on pride_kit.py (node materials, primitives, the MB card builder, numpy-painted atlases, Cycles stills stamped
"Blender render") and pride_interior.py (room shell, mouldings, sash windows, candlesticks, books, pictures). What it
adds, for docs/LIVING_SCENES.md:

  * fx(name, loc, radius): fx.fire.* / fx.torch.* / fx.candle.* empties that carry the custom property "radius" (glTF
    extras; the export runs with export_extras=True) as well as the display size.
  * water.ocean.* meshes: never baked or re-unwrapped; UV = world metres / 10 (U = x/10, V = y/10 in Blender's frame);
    COLOR_0 = (0, foam, 1, 1) with foam in G (1 at the hull, the wake); a plain dark water colour as material. Unity's
    water material does the moving surface (FableLiving).
  * bake_and_export(): pride_kit's join-by-material, bake and glTF export, plus the water handling above, the living
    colour attribute kept on veg.* / cloth.* / water.* meshes, glTF extras and the SUN intensity patch.

Everything procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, os, json
import numpy as np
from mathutils import Vector, Matrix, noise
import pride_kit as K
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       texcoord_obj, wood, noisy, plain, vcol_mat, image_mat, np_image, Canvas, box, sphere, lathe, tube, sweep,
                       mesh_from, MB, Frame, anchor, sound, light_obj, camera, link, smoothstep, lerp, n2, fbm2, add_sway)

LIVING = ("veg.", "cloth.", "water.")


def cyl(name, r, h, loc, mat, verts=16, rot=(0, 0, 0), r2=None, smooth=True):
    """pride_kit.cyl with an edge split, so the smooth-shaded sides do not smear across the flat caps."""
    o = K.cyl(name, r, h, loc, mat, verts=verts, rot=rot, r2=r2, smooth=smooth)
    if smooth: o.modifiers.new("EdgeSplit", 'EDGE_SPLIT').split_angle = math.radians(50)
    return o


def fx(name, loc, radius):
    """fx.fire.* (base of the flame), fx.torch.* / fx.lantern.* (the flame), fx.candle.* (top of the wick)."""
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'SPHERE'; e.empty_display_size = radius; e.location = loc
    e["radius"] = float(radius)
    return link(e)


def water_attrs(o, foam_fn):
    """water.ocean.*: COLOR_0 (0, foam, 1, 1) per vertex and UV = world metres / 10."""
    me = o.data; mw = o.matrix_world
    for an in [a.name for a in me.color_attributes]: me.color_attributes.remove(me.color_attributes[an])
    ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
    vals = []
    for v in me.vertices:
        p = mw @ v.co; vals += [0.0, max(0.0, min(1.0, foam_fn(p))), 1.0, 1.0]
    ca.data.foreach_set("color", vals)
    me.color_attributes.active_color = ca
    try: me.color_attributes.render_color_index = me.color_attributes.active_color_index
    except Exception: pass
    while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    uvl = me.uv_layers.new(name="UVMap")
    for li, loop in enumerate(me.loops):
        p = mw @ me.vertices[loop.vertex_index].co; uvl.data[li].uv = (p.x / 10.0, p.y / 10.0)


def ao_mul(nt, col, dist=0.15, amount=0.35, loc=(0, -600)):
    return K.ao_mul(nt, col, dist, amount, loc)


def bake_and_export(gltf_name, cams, page=None, keep_names=None, keep_uv=(), size_for=None, default_size=None, sky_names=("SkyDome",),
                    unlit_emit=(), water_colour=None):
    """pride_kit.bake_and_export with water.* meshes kept unbaked (COLOR_0 foam, world UVs), the living colour attribute
    kept on veg.* / cloth.* / water.*, and glTF extras (the fx radius)."""
    ARGS, OUT, COLL, scene = K.ARGS, K.OUT, K.COLL, K.scene
    keep_names = keep_names or {}; size_for = size_for or {}; water_colour = water_colour or {}
    T_ = ARGS.tex; default_size = default_size or (T_ // 4, T_ // 4, T_ // 4)
    if page is not None and page.name in bpy.data.objects: bpy.data.objects.remove(page)
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
        living = keep_names.get(mname, "").startswith(LIVING)
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
        if o.name.startswith("water."):
            col = water_colour.get(m.name, (0.02, 0.05, 0.07))
            for n in list(nt.nodes): nt.nodes.remove(n)
            out = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
            nt.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
            nb.inputs["Base Color"].default_value = c4(col); nb.inputs["Roughness"].default_value = 0.08
            tex_sizes[o.name] = 0
            continue
        if m.name in K.IMAGE_MATS:
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
                              export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_extras=True)
    K.patch_sun_intensities(gl)
    with open(gl) as f: g = json.load(f)
    tris = sum(K.tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    used = set(im.get("uri") for im in g.get("images", []))
    tex_bytes = sum(os.path.getsize(os.path.join(OUT, u)) for u in used if u and os.path.exists(os.path.join(OUT, u)))
    gpu_bytes = 0
    for im in bpy.data.images:
        if im.size[0] > 0 and (im.name.startswith("T_") or im.name.startswith("A_")):
            gpu_bytes += int(im.size[0] * im.size[1] * 1.33)
    alpha_modes = {mt["name"]: mt.get("alphaMode", "OPAQUE") for mt in g.get("materials", [])}
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris} textures_on_disk={tex_bytes / 1e6:.1f}MB")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\ntextures_on_disk_MB={tex_bytes / 1e6:.2f}\n"
                f"textures_gpu_estimate_MB(~1 byte/texel compressed + mips)={gpu_bytes / 1e6:.2f}\n")
        f.write(f"alpha_mask_materials={[k for k, v in alpha_modes.items() if v != 'OPAQUE']}\n")
        f.write("nodes=" + ", ".join(sorted(n.get("name", "") for n in g.get("nodes", []) if not n.get("name", "").startswith("MESH_"))) + "\n")
        for o in sorted(merged, key=lambda o: -K.tri_count(o)):
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={K.tri_count(o)} tex={tex_sizes.get(o.name, 0)} "
                    f"colour_attr={'yes' if o.data.color_attributes else 'no'}\n")
        f.write("empties:\n")
        for o in COLL.objects:
            if o.type == 'EMPTY': f.write(f"  {o.name} {tuple(round(x, 3) for x in o.location)} radius={o.get('radius', '')}\n")
            if o.type == 'LIGHT': f.write(f"  LIGHT {o.name} {o.data.type} {o.data.energy:.1f} {tuple(round(x, 3) for x in o.location)}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, gltf_name.replace(".gltf", "_baked.blend")))
    return gl


def orient(o, dir_fn):
    """Flip faces so their normals agree with dir_fn(face centre) -> wanted direction (Unity culls back faces)."""
    me = o.data; bm = bmesh.new(); bm.from_mesh(me)
    bm.normal_update()
    flip = [f for f in bm.faces if f.normal.dot(Vector(dir_fn(o.matrix_world @ f.calc_center_median()))) < 0]
    if flip: bmesh.ops.reverse_faces(bm, faces=flip)
    bm.to_mesh(me); bm.free(); me.update()
    return o


def interp1(table, x):
    """Monotone cubic (Hermite with central slopes) through [(x, y), ...]."""
    xs = [p[0] for p in table]; ys = [p[1] for p in table]
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
    x0, x1 = xs[i], xs[i + 1]; y0, y1 = ys[i], ys[i + 1]
    def slope(k):
        a, b_ = max(0, k - 1), min(len(xs) - 1, k + 1)
        return (ys[b_] - ys[a]) / (xs[b_] - xs[a])
    h = x1 - x0; t = (x - x0) / h
    m0, m1 = slope(i) * h, slope(i + 1) * h
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * m1


def sky_dome(name, mat, radius, seg=48, rings=16, el_min=-8.0):
    """An inward-facing dome with UVs (u round, v up), invisible to diffuse/shadow rays in Cycles (the world lights)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    rows = []
    for j in range(rings + 1):
        e = math.radians(el_min + (89.5 - el_min) * (j / rings) ** 1.15)
        rows.append([bm.verts.new((radius * math.cos(e) * math.sin(2 * math.pi * i / seg), radius * math.cos(e) * math.cos(2 * math.pi * i / seg), radius * math.sin(e))) for i in range(seg)])
    for j in range(rings):
        for i in range(seg):
            i2 = (i + 1) % seg
            f = bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            for l, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uvl].uv = (uu / seg, vv / rings)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.dot(f.calc_center_median()) > 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    o.visible_diffuse = False; o.visible_shadow = False; o.visible_transmission = False
    return link(o)
