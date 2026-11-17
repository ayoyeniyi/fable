"""
Fable: measure the alpha-tested foliage a room asks the Quest's GPU to shade from the reading position.

For every mesh whose material clips by alpha (its Principled BSDF's Alpha input is linked: the painted leaf, grass and
tree-line cards), each card face is clipped to the view frustum and its projected area summed, as a fraction of the
screen. The sum counts every layer (no occlusion), which is what costs on a tile GPU: alpha-tested fragments are
shaded whether or not something nearer hides them. 1.0 = one full screen of alpha cards.

Views: the room's Cam_Reader (its own lens, 16:9), and a cube of six 90-degree views at the reader's eye (the whole
surround a reader can turn to). Also counts card faces and triangles, and card faces within 8 m of the reader.

Run headless on a saved source .blend:
  blender -b out/pillaji-forest/pillaji_forest_source.blend -P blender/measure_alpha_cards.py -- [--json out.json]
"""
import bpy, math, sys, json
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out_json = argv[argv.index("--json") + 1] if "--json" in argv else None


def is_alpha(m):
    if m is None or not m.use_nodes: return False
    for n in m.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED' and n.inputs["Alpha"].is_linked: return True
    return False


def clip_poly(P, plane):
    """Sutherland-Hodgman in homogeneous clip space; plane(v) >= 0 keeps."""
    out = []
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        da, db = plane(a), plane(b)
        if da >= 0: out.append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db); out.append(a + (b - a) * t)
    return out


PLANES = [lambda v: v[3] - v[0], lambda v: v[3] + v[0], lambda v: v[3] - v[1], lambda v: v[3] + v[1]]


def view_area(polys_world, M):
    """polys_world: list of (k,3) arrays. M: 4x4 projection @ view. Returns sum of NDC area / 4 (screen fraction)."""
    tot = 0.0; nfaces = 0
    for P in polys_world:
        H = np.c_[P, np.ones(len(P))] @ M.T
        w = H[:, 3]
        if (w < 0.05).all(): continue
        if (H[:, 0] > w).all() or (H[:, 0] < -w).all() or (H[:, 1] > w).all() or (H[:, 1] < -w).all(): continue
        Q = [h for h in H]
        Q = clip_poly(Q, lambda v: v[3] - 0.05)
        for pl in PLANES:
            if len(Q) < 3: break
            Q = clip_poly(Q, pl)
        if len(Q) < 3: continue
        xy = np.array([[q[0] / q[3], q[1] / q[3]] for q in Q])
        x, y = xy[:, 0], xy[:, 1]
        a = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
        tot += a / 4.0; nfaces += 1
    return tot, nfaces


def proj(fov_x, aspect, near=0.05, far=1000.0):
    f = 1.0 / math.tan(fov_x / 2)
    return np.array([[f, 0, 0, 0], [0, f * aspect, 0, 0], [0, 0, -(far + near) / (far - near), -2 * far * near / (far - near)], [0, 0, -1, 0]])


def main():
    sc = bpy.context.scene
    deps = bpy.context.evaluated_depsgraph_get()
    cam = bpy.data.objects.get("Cam_Reader")
    eye = cam.matrix_world.translation.copy()
    polys = []; pmat = []; tris = 0; near8 = 0; per_mat = {}
    for o in sc.objects:
        if o.type != 'MESH' or o.hide_render: continue
        if not any(is_alpha(s.material) for s in o.material_slots): continue
        ev = o.evaluated_get(deps); me = ev.to_mesh()
        mw = np.array(o.matrix_world)
        V = np.array([v.co for v in me.vertices]).reshape(-1, 3)
        V = V @ mw[:3, :3].T + mw[:3, 3]
        mats = [s.material for s in o.material_slots]
        for p in me.polygons:
            m = mats[p.material_index] if p.material_index < len(mats) else None
            if not is_alpha(m): continue
            P = V[list(p.vertices)]
            polys.append(P); pmat.append(m.name); tris += len(p.vertices) - 2
            c = P.mean(axis=0)
            if math.hypot(c[0] - eye.x, c[1] - eye.y) < 8.0: near8 += 1
            per_mat[m.name] = per_mat.get(m.name, 0) + 1
        ev.to_mesh_clear()
    res = {"card_faces": len(polys), "card_tris": tris, "card_faces_within_8m": near8, "faces_per_material": per_mat}
    # Cam_Reader
    cd = cam.data
    aspect = sc.render.resolution_x / sc.render.resolution_y
    fov_x = 2 * math.atan(cd.sensor_width / 2 / cd.lens) if cd.sensor_fit != 'VERTICAL' else 2 * math.atan(cd.sensor_width * aspect / 2 / cd.lens)
    V_ = np.array(cam.matrix_world.inverted())
    a, n = view_area(polys, proj(fov_x, aspect) @ V_)
    res["reader_view_alpha_screens"] = round(a, 3); res["reader_view_faces"] = n
    Mr = proj(fov_x, aspect) @ V_
    res["reader_view_by_material"] = {k: round(view_area([P for P, mm in zip(polys, pmat) if mm == k], Mr)[0], 3) for k in per_mat}
    dist = [math.hypot(P.mean(axis=0)[0] - eye.x, P.mean(axis=0)[1] - eye.y) for P in polys]
    res["reader_view_by_distance"] = {f"{lo}-{hi}m": round(view_area([P for P, d in zip(polys, dist) if lo <= d < hi], Mr)[0], 3)
                                      for lo, hi in ((0, 4), (4, 8), (8, 15), (15, 30), (30, 999))}
    # cube of six 90-degree views at the eye
    tot = 0.0
    dirs = [Vector((0, 1, 0)), Vector((1, 0, 0)), Vector((0, -1, 0)), Vector((-1, 0, 0)), Vector((0, 0, 1)), Vector((0, 0, -1))]
    for d in dirs:
        up = Vector((0, 0, 1)) if abs(d.z) < 0.5 else Vector((0, 1, 0))
        rot = d.to_track_quat('-Z', 'Y' if abs(d.z) < 0.5 else 'Y').to_matrix().to_4x4()
        if abs(d.z) > 0.5:
            z = -d; x = Vector((1, 0, 0)); y = z.cross(x)
            rot = Matrix((x, y, z)).transposed().to_4x4()
        Mw = Matrix.Translation(eye) @ rot
        a, _ = view_area(polys, proj(math.radians(90), 1.0) @ np.array(Mw.inverted()))
        tot += a
    res["surround_alpha_screens_6x90"] = round(tot, 3)
    print("ALPHA_CARDS", json.dumps(res))
    if out_json:
        with open(out_json, "w") as f: json.dump(res, f, indent=1)


main()
