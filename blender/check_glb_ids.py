#!/usr/bin/env python3
"""
Check that an exported Fable environment GLB carries every id its manifest and baseline script
reference, as node names, and report triangle / mesh / texture counts.

  python3 blender/check_glb_ids.py out/mad-tea-party/mad_tea_party.glb \
      --manifest schema/manifest.mad-tea-party.json --baseline scripts/mad-tea-party.baseline.json

Expected node names (the SceneRegistry convention):
  anchors          "anchor.<id>"   (plus "anchor.scene.centre", the miniature pivot)
  assets / clips   "<id>"          (prop.*, char.*, fx.* ... exactly the manifest id)
  lights           "<id>" or "<id>.<n>" or a child of an empty named "<id>"
Sounds, ambiences, clip names and the environment prefab are not GLB nodes and are not checked.
Exit code 0 when everything is present, 1 otherwise. Standard library only.
"""
import argparse, json, struct, sys


def read_glb(path):
    """Reads a .glb, or a .gltf (size = the .gltf plus its buffers and images)."""
    if path.endswith(".gltf"):
        import os
        with open(path) as f:
            doc = json.load(f)
        base = os.path.dirname(path)
        uris = [b.get("uri") for b in doc.get("buffers", [])] + [i.get("uri") for i in doc.get("images", [])]
        size = os.path.getsize(path) + sum(os.path.getsize(os.path.join(base, u)) for u in uris if u and not u.startswith("data:"))
        return doc, size
    with open(path, "rb") as f:
        data = f.read()
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67:
        sys.exit(f"{path}: not a GLB")
    off = 12
    doc = None
    while off < length:
        clen, ctype = struct.unpack_from("<II", data, off)
        if ctype == 0x4E4F534A:
            doc = json.loads(data[off + 8: off + 8 + clen])
        off += 8 + clen
    return doc, len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--baseline")
    a = ap.parse_args()
    doc, size = read_glb(a.glb)
    man = json.load(open(a.manifest))
    nodes = doc.get("nodes", [])
    names = [n.get("name", "") for n in nodes]
    nameset = set(names)
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i

    # light nodes: nodes carrying KHR_lights_punctual, or whose parent does
    light_nodes = set()
    for i, n in enumerate(nodes):
        if "KHR_lights_punctual" in n.get("extensions", {}):
            light_nodes.add(i)

    def light_present(lid):
        for i in light_nodes:
            chain, j = [], i
            while j is not None:
                chain.append(names[j]); j = parent.get(j)
            if any(c == lid or c.startswith(lid + ".") or c.startswith(lid + "_") for c in chain):
                return True
        return False

    required = []   # (kind, id, node name expected)
    for aid in man.get("anchors", {}):
        required.append(("anchor", aid, "anchor." + aid))
    required.append(("anchor", "scene.centre", "anchor.scene.centre"))
    for asset in man.get("assets", {}):
        required.append(("asset", asset, asset))
    for target in man.get("clips", {}):
        required.append(("clip target", target, target))
    if a.baseline:
        bl = json.load(open(a.baseline))
        for beat in bl.get("beats", []):
            if beat.get("focus"):
                required.append(("baseline focus", beat["focus"], "anchor." + beat["focus"]))
            for act in beat.get("actions", []):
                for key, kind in (("asset", "baseline asset"), ("target", "baseline target")):
                    if act.get(key): required.append((kind, act[key], act[key]))
                if act.get("anchor"):
                    required.append(("baseline anchor", act["anchor"], "anchor." + act["anchor"]))
                if act.get("light"):
                    required.append(("baseline light", act["light"], None))

    missing = []
    seen = set()
    for kind, rid, nm in required:
        if (kind, rid) in seen: continue
        seen.add((kind, rid))
        ok = (nm in nameset) if nm else light_present(rid)
        if not ok: missing.append((kind, rid, nm))
    for lid in man.get("lights", []):
        if not light_present(lid): missing.append(("light", lid, lid))
        seen.add(("light", lid))

    # mesh / triangle stats
    meshes = doc.get("meshes", [])
    acc = doc.get("accessors", [])
    tris = 0
    prims = 0
    for m in meshes:
        for p in m.get("primitives", []):
            prims += 1
            mode = p.get("mode", 4)
            if "indices" in p: n = acc[p["indices"]]["count"]
            else: n = acc[p["attributes"]["POSITION"]]["count"]
            tris += n // 3 if mode == 4 else 0
    mesh_nodes = sum(1 for n in nodes if "mesh" in n)
    imgs = doc.get("images", [])
    print(f"GLB {a.glb}  {size / 1e6:.1f} MB")
    print(f"nodes={len(nodes)} mesh_nodes={mesh_nodes} meshes={len(meshes)} primitives={prims} triangles={tris} materials={len(doc.get('materials', []))} images={len(imgs)}")
    print(f"lights: {[names[i] for i in sorted(light_nodes)]}")
    print(f"checked {len(seen)} ids (manifest anchors/assets/clip targets/lights + baseline references + anchor.scene.centre)")
    if missing:
        print("MISSING:")
        for kind, rid, nm in missing: print(f"  {kind:16s} {rid:22s} expected node {nm or rid + ' (light)'}")
        sys.exit(1)
    print("OK: every id present")


if __name__ == "__main__":
    main()
