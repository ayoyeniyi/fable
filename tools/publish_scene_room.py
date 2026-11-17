#!/usr/bin/env python3
"""Publish a runtime-baked scene room for download (docs/SCENE_ROOMS_PIPELINE.md).

  python3 tools/publish_scene_room.py out/<id>                      # a room planned in schema/scene_rooms.json
  python3 tools/publish_scene_room.py out/arctic-ice --as sr-arctic-ice --book frankenstein --title "..." --no-chapters

Takes out/<id>/runtime/ (written by blender/runtime_bake.py), checks the budget and the names, and writes
  content/scene-rooms/<id>/room-<sha8>.zip    room.gltf, room.bin, textures/, room.json (deterministic zip)
  content/scene-rooms/<id>/manifest.json      id, version, title, book, chapters, zip, bytes, sha256, sizes, anchors
  content/scene-rooms/<id>/view.jpg           the reader's view (the chapter card's picture)
and adds or updates the room's environment in schema/environments.json ("delivery": "download"). The packages are
not committed (content/scene-rooms/ is git-ignored); deploy/deploy.sh copies them to the server.
"""
import argparse, hashlib, io, json, os, re, shutil, struct, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOFT_MB, HARD_MB, MAX_TEX, MAX_TRIS, MAX_MESHES = 15, 25, 2048, 65000, 50


def jpeg_size(path):
    with open(path, "rb") as f:
        data = f.read()
    i = 2
    while i < len(data):
        if data[i] != 0xFF: i += 1; continue
        m = data[i + 1]
        if m in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", data[i + 5:i + 9]); return w, h
        i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return 0, 0


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24]) if head[:8] == b"\x89PNG\r\n\x1a\n" else (0, 0)


def upsert_env(env):
    """one line per download environment, inserted before the list's end (the file's hand-kept layout is untouched)"""
    path = os.path.join(ROOT, "schema", "environments.json")
    text = open(path, encoding="utf-8").read()
    line = "    " + json.dumps(env, ensure_ascii=False, separators=(", ", ": "))
    pat = re.compile(r'^    \{ ?"id": "' + re.escape(env["id"]) + r'",.*"delivery": "download".*?\}(,?)$', re.M)
    m = pat.search(text)
    if m:
        text = text[:m.start()] + line + m.group(1) + text[m.end():]
    else:
        if any(e["id"] == env["id"] for e in json.loads(text)["environments"]):
            sys.exit(f"environments.json already has a bundled environment {env['id']}: publish with --as <another id>")
        end = text.rindex("\n  ]")
        text = text[:end].rstrip() + ",\n" + line + text[end:]
    json.loads(text)   # still valid
    open(path, "w", encoding="utf-8").write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("room", help="out/<id>")
    ap.add_argument("--as", dest="env_id", default="", help="environment id (default: the room id)")
    ap.add_argument("--book", default=""); ap.add_argument("--title", default=""); ap.add_argument("--place", default="")
    ap.add_argument("--chapters", default="", help="comma-separated chapter ids (default: from schema/scene_rooms.json)")
    ap.add_argument("--no-chapters", action="store_true", help="publish without naming chapters (a stand-in; never planned)")
    ap.add_argument("--no-schema", action="store_true", help="do not touch schema/environments.json")
    ap.add_argument("--dest", default=os.path.join(ROOT, "content", "scene-rooms"))
    a = ap.parse_args()

    room = os.path.abspath(a.room); rid = os.path.basename(room.rstrip("/")); rt = os.path.join(room, "runtime")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", rid): sys.exit(f"bad room id {rid!r}: lower-case letters, digits and hyphens")
    meta_p = os.path.join(rt, "room.json")
    if not os.path.exists(meta_p): sys.exit(f"{meta_p} is missing: run blender/runtime_bake.py first")
    meta = json.load(open(meta_p)); g = json.load(open(os.path.join(rt, "room.gltf")))
    problems, warnings = [], []
    names = {n.get("name", "") for n in g.get("nodes", [])}
    for need in ("anchor.reader.entrance", "anchor.reader.look"):
        if need not in names: problems.append(f"no {need}")
    files = ["room.gltf", "room.json"] + [b["uri"] for b in g.get("buffers", [])] + [im["uri"] for im in g.get("images", [])]
    for f in files:
        p = os.path.join(rt, f)
        if ".." in f or f.startswith("/") or not os.path.exists(p): problems.append(f"missing or unsafe file {f}"); continue
        if f.endswith((".jpg", ".jpeg", ".png")):
            w, h = jpeg_size(p) if f.endswith(("jpg", "jpeg")) else png_size(p)
            if max(w, h) > MAX_TEX: problems.append(f"{f} is {w}x{h}, over {MAX_TEX}")
    if meta.get("triangles", 0) > MAX_TRIS: problems.append(f"{meta['triangles']} triangles, over {MAX_TRIS}")
    if meta.get("meshes", 0) > MAX_MESHES: problems.append(f"{meta['meshes']} meshes, over {MAX_MESHES}")
    if not os.path.exists(os.path.join(rt, "view.jpg")): problems.append("no view.jpg")

    # deterministic zip: sorted names, fixed times, deflated
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(set(files)):
            if not os.path.exists(os.path.join(rt, f)): continue
            zi = zipfile.ZipInfo(f, date_time=(2026, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16
            z.writestr(zi, open(os.path.join(rt, f), "rb").read())
    data = buf.getvalue(); sha = hashlib.sha256(data).hexdigest(); mb = len(data) / 1e6
    if mb > HARD_MB: problems.append(f"the download is {mb:.1f} MB, over the {HARD_MB} MB limit")
    elif mb > SOFT_MB: warnings.append(f"the download is {mb:.1f} MB, over the {SOFT_MB} MB budget")
    if problems:
        sys.exit("not published:\n  " + "\n  ".join(problems))

    plan = json.load(open(os.path.join(ROOT, "schema", "scene_rooms.json"))) if os.path.exists(os.path.join(ROOT, "schema", "scene_rooms.json")) else {"places": []}
    pl = next((p for p in plan["places"] if p["id"] == rid), None)
    book = a.book or (pl or {}).get("book", "")
    title = a.title or (pl or {}).get("name", rid)
    chapters = [] if a.no_chapters else ([c.strip() for c in a.chapters.split(",") if c.strip()] if a.chapters else (pl or {}).get("chapters", []))
    if not book: sys.exit(f"{rid} is not in schema/scene_rooms.json: give --book (and --title, --chapters or --no-chapters)")
    if pl and pl.get("existing"): warnings.append(f"the plan says {rid} is the existing room {pl['existing']}; its chapters are staged there, not here")
    place = a.place or (title + ((": " + " ".join(b for b in pl.get("brief", [])[:3])) if pl and pl.get("brief") else ""))

    dest = os.path.join(a.dest, rid); os.makedirs(dest, exist_ok=True)
    version = sha[:8]; zname = f"room-{version}.zip"
    tmp = os.path.join(dest, zname + ".part"); open(tmp, "wb").write(data); os.replace(tmp, os.path.join(dest, zname))
    shutil.copyfile(os.path.join(rt, "view.jpg"), os.path.join(dest, "view.jpg"))
    manifest = {"id": rid, "version": version, "title": title, "book": book, "chapters": chapters, "zip": zname, "bytes": len(data),
                "sha256": sha, "view": "view.jpg", "triangles": meta.get("triangles", 0), "meshes": meta.get("meshes", 0),
                "unpackedBytes": sum(os.path.getsize(os.path.join(rt, f)) for f in set(files)),
                "anchors": meta.get("anchors"), "wind": meta.get("wind"), "windToward": meta.get("windToward"), "ambience": meta.get("ambience")}
    mt = os.path.join(dest, "manifest.json.part"); json.dump(manifest, open(mt, "w"), indent=1); os.replace(mt, os.path.join(dest, "manifest.json"))
    for f in os.listdir(dest):   # older versions
        if f.startswith("room-") and f.endswith(".zip") and f != zname: os.remove(os.path.join(dest, f))
    if not a.no_schema:
        env = {"id": a.env_id or rid, "unityScene": "LibraryRoom", "staging": "place", "books": [book], "place": place,
               "gltf": "", "eye": "anchor.reader.entrance", "look": "anchor.reader.look", "triangles": meta.get("triangles", 0),
               "meshes": meta.get("meshes", 0), "delivery": "download", "sceneRoom": rid}
        if chapters: env["chapters"] = chapters
        upsert_env(env)
    for w in warnings: print("warning:", w)
    print(f"PUBLISHED {rid} {version}: {mb:.1f} MB zip ({manifest['unpackedBytes'] / 1e6:.1f} MB unpacked), {manifest['triangles']} triangles, "
          f"chapters {', '.join(chapters) or 'none'} -> {os.path.relpath(dest, ROOT)}")


if __name__ == "__main__":
    main()
