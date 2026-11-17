"""
Fable: shared helpers for the chapter step-in rooms built by room builder 5 (docs/SCENE_ROOMS.md):
longbourn-drawing-room, munchkin-cornfield, white-rabbit-house, spouter-inn-bedroom, caterpillar-mushroom,
benbow-road-bridge, lilliput-temple-lodging, netherfield-breakfast-parlour, ingolstadt-lecture-room,
hispaniola-cabin, hispaniola-deck.

Builds on pride_kit.py (materials, geometry, cameras, stills) and pride_interior.py (Regency joinery). Adds:

  * setup(scene_id): out/<id>, captures/blender/<id> by default.
  * fx(...) empties with the custom property `radius` (exported with export_extras=True, docs/LIVING_SCENES.md).
  * reader(entrance, look): anchor.reader.entrance (feet) and anchor.reader.look (eye height, ahead).
  * check_reader(): the reader stands on open floor (>= 1.5 m clear ahead, 0.4 m around).
  * export(): step 1 of docs/SCENE_ROOMS_PIPELINE.md (pride_kit.bake_and_export -> out/<id>/<id_underscored>.gltf and
    the _baked.blend that blender/runtime_bake.py lights for the headset).

Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os, json, time
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EYE = 1.55
READER = {}


def setup(scene_id, seed=1, samples=48):
    args = K.setup(scene_id, os.path.join(REPO, "out", scene_id), seed, scene_id.replace("-", "_"), default_samples=samples)
    if not args.captures and args.render and not args.quick:
        args.captures = os.path.join(REPO, "captures", "blender", scene_id)
    return args


def fx(name, loc, radius):
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'SPHERE'; e.empty_display_size = radius
    e.location = loc; e["radius"] = float(radius); K.link(e)
    return e


def reader(entrance, look_dir, eye=EYE):
    """entrance: the reader's feet on the floor; look_dir: horizontal facing direction."""
    e = Vector(entrance); d = Vector((look_dir[0], look_dir[1], 0)).normalized()
    K.anchor("reader.entrance", tuple(e))
    K.anchor("reader.look", tuple(e + d + Vector((0, 0, eye))))
    READER.update(entrance=e, dir=d, eye=eye)
    return e, d


def check_reader(ignore=("PagePreview",)):
    """Ray checks: 1.5 m clear ahead at knee, waist and eye height; 0.4 m clear all round at knee and waist."""
    if not READER: return []
    scene = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get()
    hidden = []
    for n in ignore:
        o = bpy.data.objects.get(n)
        if o and not o.hide_viewport: o.hide_viewport = True; hidden.append(o)
    dg.update()
    e, d, eye = READER["entrance"], READER["dir"], READER["eye"]
    problems = []
    for z in (0.3, 0.9, eye):
        for off in (-0.2, 0.0, 0.2):
            side = Vector((-d.y, d.x, 0)) * off
            hit, loc, nrm, idx, ob, mx = scene.ray_cast(dg, e + side + Vector((0, 0, z)), d, distance=1.5)
            if hit: problems.append(f"ahead blocked at z={z} off={off}: {ob.name} {round((loc - e).length, 2)} m")
    for k in range(12):
        a = 2 * math.pi * k / 12; v = Vector((math.cos(a), math.sin(a), 0))
        for z in (0.3, 0.9):
            hit, loc, nrm, idx, ob, mx = scene.ray_cast(dg, e + Vector((0, 0, z)), v, distance=0.4)
            if hit: problems.append(f"around blocked dir {k * 30} deg z={z}: {ob.name}")
    hit, loc, nrm, idx, ob, mx = scene.ray_cast(dg, e + Vector((0, 0, eye)), Vector((0, 0, -1)), distance=3)
    if not hit or abs(loc.z - e.z) > 0.08: problems.append(f"floor under reader at {loc.z if hit else None} (feet {e.z})")
    for o in hidden: o.hide_viewport = False
    print("READER CHECK", "ok" if not problems else problems, flush=True)
    return problems


def eye_cams(yaws, lens=17, dist=5.0, dz=-0.55, extra=()):
    """Cameras from the reader's eye: yaws in degrees relative to the facing direction (+ = right)."""
    e = READER["entrance"] + Vector((0, 0, READER["eye"])); d = READER["dir"]
    cams = []
    for name, yaw in yaws:
        a = math.radians(-yaw); v = Matrix.Rotation(a, 3, 'Z') @ d
        cams.append(K.camera("Cam_" + name, tuple(e), tuple(e + v * dist + Vector((0, 0, dz))), lens=lens))
    for name, loc, at, ln in extra:
        cams.append(K.camera("Cam_" + name, tuple(loc), tuple(at), lens=ln))
    for c in cams: c.data.clip_end = 1600
    return cams


def page_preview():
    e = READER["entrance"]; d = READER["dir"]
    return K.box("PagePreview", (abs(d.y) * 0.4 + abs(d.x) * 0.004, abs(d.x) * 0.4 + abs(d.y) * 0.004, 0.55),
                 tuple(e + d * 0.6 + Vector((0, 0, READER["eye"] - 0.05))), K.plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9))


# ----------------------------------------------------------------------------- export (docs/SCENE_ROOMS_PIPELINE.md)
def export(scene_id, cams, page=None, keep_names=None, size_for=None, default_size=(512, 64, 256), unlit_emit=(), remove=()):
    """Step 1 of the scene-room pipeline: pride_kit's bake_and_export (merge per material, baked albedo, the lights kept
    in out/<id>/<id_underscored>_baked.blend). Then, from the shell:
      Blender -b -P blender/runtime_bake.py -- out/<id> [--wind .. --wind-toward .. --ambience ..] [--indoor]
      python3 tools/publish_scene_room.py out/<id>
    size_for values: (base, roughness, normal) sizes or a single int (base only)."""
    for n in remove:
        if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n])
    # metals bake to black albedo (a diffuse-colour bake sees no diffuse in a metal): export them as dielectrics of the
    # same colour, a little glossy, so the runtime light texture shows them
    for m in bpy.data.materials:
        if not m.use_nodes: continue
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED' and not n.inputs["Metallic"].is_linked and n.inputs["Metallic"].default_value > 0.3:
                n.inputs["Metallic"].default_value = 0.0
    sf = {k: (v if isinstance(v, tuple) else (v, 64, max(64, v // 2))) for k, v in (size_for or {}).items()}
    gl = K.bake_and_export(scene_id.replace("-", "_") + ".gltf", cams, page=page, keep_names=keep_names or {}, size_for=sf,
                           default_size=default_size, unlit_emit=tuple(unlit_emit))
    print("EXPORTED", gl, flush=True)
    return gl


# ----------------------------------------------------------------------------- outdoor: sky dome, polar ground, grass
def sky_mat(name, sun_dir, zenith=(0.12, 0.26, 0.62), mid=(0.32, 0.50, 0.78), horizon=(0.70, 0.76, 0.82), cloud=0.5,
            cloud_lit=(1.0, 0.98, 0.94), cloud_shade=(0.58, 0.62, 0.70), sun_glow=(0.9, 0.75, 0.5), haze_low=(0.62, 0.66, 0.66),
            cloud_scale=0.3, clear_dir=None, stars=False, hills=None):
    """An emissive sky (display colours): a gradient, a glow round the sun, a cumulus deck in perspective lit on the sun
    side. cloud = cover 0..1. clear_dir: a direction kept clearer (behind the reading page)."""
    m, nt, b = K.new_mat(name)
    tc = K.node(nt, "ShaderNodeTexCoord", (-2200, 0))
    nv = K.node(nt, "ShaderNodeVectorMath", (-2000, 0), operation='NORMALIZE'); nt.links.new(tc.outputs["Object"], nv.inputs[0])
    d = nv.outputs[0]
    sep = K.sep_xyz(nt, d, (-1800, 0)); el = sep.outputs["Z"]
    base = K.ramp(nt, [(0.0, K.c4(haze_low)), (0.11, K.c4(horizon)), (0.2, K.c4(mid)), (0.55, K.c4(zenith)), (1.0, K.c4(zenith))], (-1300, 400))
    nt.links.new(K.maprange(nt, el, -0.1, 1.0, 0.0, 1.0, (-1500, 400)), base.inputs["Fac"])
    col = base.outputs["Color"]
    sd = K.node(nt, "ShaderNodeVectorMath", (-1600, 800), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(Vector(sun_dir).normalized()); nt.links.new(d, sd.inputs[0])
    halo = K.math_(nt, 'POWER', K.maprange(nt, sd.outputs["Value"], 0.6, 1.0, 0.0, 1.0, (-1400, 800)), 3.0, (-1250, 800))
    col = K.mix_rgb(nt, 'ADD', K.math_(nt, 'MULTIPLY', halo, 0.5, (-1100, 850)), col, K.c4(sun_glow), (-900, 400))
    zk = K.math_(nt, 'ADD', K.math_(nt, 'MAXIMUM', el, 0.0, (-1600, -200)), 0.06, (-1450, -200))
    px = K.math_(nt, 'DIVIDE', sep.outputs["X"], zk, (-1300, -150)); py = K.math_(nt, 'DIVIDE', sep.outputs["Y"], zk, (-1300, -300))
    cv = K.node(nt, "ShaderNodeCombineXYZ", (-1150, -200)); nt.links.new(px, cv.inputs["X"]); nt.links.new(py, cv.inputs["Y"])
    mpc = K.node(nt, "ShaderNodeMapping", (-1000, -200)); mpc.inputs["Scale"].default_value = (cloud_scale, cloud_scale, 1); mpc.inputs["Location"].default_value = (4.1, 2.7, 0.3)
    nt.links.new(cv.outputs[0], mpc.inputs["Vector"])
    c1 = K.noise_(nt, mpc.outputs["Vector"], 1.0, 9, 0.58, 0.25, (-800, -200))
    sv = Vector(sun_dir).normalized()
    so = K.node(nt, "ShaderNodeVectorMath", (-900, -500), operation='ADD'); so.inputs[1].default_value = (sv.x * 0.07, sv.y * 0.07, 0.0)
    nt.links.new(mpc.outputs["Vector"], so.inputs[0])
    c2 = K.noise_(nt, so.outputs["Vector"], 1.0, 9, 0.58, 0.25, (-700, -500))
    big = K.noise_(nt, mpc.outputs["Vector"], 0.18, 2, 0.5, 0.0, (-800, -800))
    cov = K.maprange(nt, el, 0.6, 0.12, 0.3, 1.0, (-800, -1300))
    if clear_dir is not None:
        cd = K.node(nt, "ShaderNodeVectorMath", (-1000, -1100), operation='DOT_PRODUCT'); cd.inputs[1].default_value = tuple(Vector(clear_dir).normalized()); nt.links.new(d, cd.inputs[0])
        cov = K.math_(nt, 'MULTIPLY', cov, K.maprange(nt, cd.outputs["Value"], 0.6, 0.95, 1.0, 0.45, (-800, -1100)), (-600, -1200))
    thr = K.math_(nt, 'ADD', K.math_(nt, 'MULTIPLY', big.outputs["Fac"], 0.25, (-600, -800)), c1.outputs["Fac"], (-450, -700))
    lo = 0.66 - 0.2 * cloud
    cm = K.maprange(nt, K.math_(nt, 'MULTIPLY', thr, cov, (-350, -800)), lo, lo + 0.14, 0.0, 1.0, (-200, -800))
    cm = K.math_(nt, 'MULTIPLY', cm, K.maprange(nt, el, 0.01, 0.06, 0.0, 1.0, (-350, -1300)), (-100, -900))
    lit = K.maprange(nt, K.math_(nt, 'SUBTRACT', c1.outputs["Fac"], c2.outputs["Fac"], (-450, -500)), -0.04, 0.05, 0.0, 1.0, (-250, -500))
    ccol = K.mix_rgb(nt, 'MIX', lit, K.c4(cloud_shade), K.c4(cloud_lit), (-100, -500))
    col = K.mix_rgb(nt, 'MIX', K.math_(nt, 'MULTIPLY', cm, 0.95, (0, -800)), col, ccol, (-600, 400))
    if hills:      # (height in elevation-sine units, near colour, far colour): a band of far hills along the horizon
        hh, hc0, hc1 = hills
        az = K.math_(nt, 'ARCTAN2', sep.outputs["Y"], sep.outputs["X"], (-1600, -1600))
        azv = K.node(nt, "ShaderNodeCombineXYZ", (-1450, -1600)); nt.links.new(K.math_(nt, 'COSINE', az, None, (-1500, -1700)), azv.inputs["X"]); nt.links.new(K.math_(nt, 'SINE', az, None, (-1500, -1800)), azv.inputs["Y"])
        hn = K.noise_(nt, azv.outputs[0], 2.4, 5, 0.55, 0.0, (-1300, -1650))
        top = K.math_(nt, 'MULTIPLY_ADD', hn.outputs["Fac"], hh, (-1100, -1650), c=-hh * 0.35)
        hm = K.maprange(nt, K.math_(nt, 'SUBTRACT', top, el, (-950, -1800)), 0.0, 0.003, 0.0, 1.0, (-800, -1800))
        hcol = K.mix_rgb(nt, 'MIX', K.maprange(nt, K.math_(nt, 'SUBTRACT', top, el, (-950, -1950)), 0.0, hh * 0.6, 0.0, 1.0, (-800, -1950)), K.c4(hc1), K.c4(hc0), (-650, -1900))
        col = K.mix_rgb(nt, 'MIX', hm, col, hcol, (-400, 400))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m


def sky_dome(mat, radius=900.0, seg=48, rings=14, el_min=-0.15, centre=(0, 0, 0), name="SkyDome"):
    """A dome (normals inward), never lit or shadowing: emission only."""
    vs = []; fs = []
    els = [el_min + (math.pi / 2 - el_min) * (j / rings) ** 1.4 for j in range(rings + 1)]
    for j, e in enumerate(els):
        for i in range(seg):
            a = 2 * math.pi * i / seg
            vs.append((centre[0] + radius * math.cos(e) * math.cos(a), centre[1] + radius * math.cos(e) * math.sin(a), centre[2] + radius * math.sin(e)))
    for j in range(rings):
        for i in range(seg):
            a, b_ = j * seg + i, j * seg + (i + 1) % seg
            fs.append((a, j * seg + seg + i, j * seg + seg + (i + 1) % seg, b_))
    o = K.mesh_from(name, vs, fs, mat, smooth=True)
    o.visible_shadow = False; o.visible_diffuse = False; o.visible_glossy = False
    return o


def polar_ground(name, mat, H, r0=0.0, r1=600.0, nr=40, na=96, expo=2.2, centre=(0.0, 0.0), keep=None):
    """A ground disc/annulus displaced by H(x, y); rings denser near the centre. keep(x, y) -> False drops a face."""
    rs = [r0 + (r1 - r0) * (j / nr) ** expo for j in range(nr + 1)]
    vs = []; fs = []
    for j, r in enumerate(rs):
        for i in range(na):
            a = 2 * math.pi * i / na; x = centre[0] + r * math.cos(a); y = centre[1] + r * math.sin(a)
            vs.append((x, y, H(x, y)))
    for j in range(nr):
        for i in range(na):
            q = (j * na + i, j * na + (i + 1) % na, (j + 1) * na + (i + 1) % na, (j + 1) * na + i)
            if keep is not None:
                cx = sum(vs[k][0] for k in q) / 4; cy = sum(vs[k][1] for k in q) / 4
                if not keep(cx, cy): continue
            fs.append(q)
    return K.mesh_from(name, vs, fs, mat, smooth=True)


def grid_ground(name, mat, H, x0, x1, y0, y1, step, keep=None, chunk=None):
    """A rectangular ground patch displaced by H. chunk (metres): split into disconnected chunks so the bake's smart
    project packs them as separate islands (better texel use than one long strip)."""
    nx = max(1, int(round((x1 - x0) / step))); ny = max(1, int(round((y1 - y0) / step)))
    vs = []; fs = []; idx = {}
    def V(i, j, tag):
        k = (i, j, tag)
        if k not in idx:
            x = x0 + (x1 - x0) * i / nx; y = y0 + (y1 - y0) * j / ny
            idx[k] = len(vs); vs.append((x, y, H(x, y)))
        return idx[k]
    for j in range(ny):
        for i in range(nx):
            cx = x0 + (x1 - x0) * (i + 0.5) / nx; cy = y0 + (y1 - y0) * (j + 0.5) / ny
            if keep is not None and not keep(cx, cy): continue
            tag = (int((cx - x0) // chunk), int((cy - y0) // chunk)) if chunk else 0
            fs.append((V(i, j, tag), V(i + 1, j, tag), V(i + 1, j + 1, tag), V(i, j + 1, tag)))
    return K.mesh_from(name, vs, fs, mat, smooth=True)


def grass_clumps(mb, pts, H, rng, height=(0.25, 0.55), blades=(5, 9), lean=0.35, width=0.012, tint=None):
    """Tufts of bent blades (2 triangles per blade segment, 2 segments) into a pride_kit.MB with sway weights."""
    for (x, y) in pts:
        n = rng.randint(*blades); z0 = H(x, y)
        for k in range(n):
            a = rng.uniform(0, 2 * math.pi); h = rng.uniform(*height) * rng.uniform(0.7, 1.1)
            d = Vector((math.cos(a), math.sin(a), 0)); lean_k = rng.uniform(0.15, lean)
            base = Vector((x + d.x * rng.uniform(0, 0.05), y + d.y * rng.uniform(0, 0.05), z0 - 0.01))
            side = Vector((-d.y, d.x, 0)) * width * rng.uniform(0.8, 1.3)
            mid = base + Vector((0, 0, h * 0.55)) + d * h * lean_k * 0.35
            tip = base + Vector((0, 0, h * (1 - 0.35 * lean_k))) + d * h * lean_k
            t = tint(x, y) if tint else (rng.uniform(0.0, 1.0), rng.uniform(0.0, 1.0))
            a0 = mb.vert(base - side, (0.1, 0.0), 0.0, t); a1 = mb.vert(base + side, (0.9, 0.0), 0.0, t)
            b0 = mb.vert(mid - side * 0.7, (0.2, 0.55), 0.45, t); b1 = mb.vert(mid + side * 0.7, (0.8, 0.55), 0.45, t)
            c = mb.vert(tip, (0.5, 1.0), 1.0, t)
            mb.face(a0, a1, b1, b0); mb.face(b0, b1, c)
