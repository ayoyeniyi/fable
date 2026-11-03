#!/usr/bin/env python3
"""Copy generated reading rooms from the room service into content/rooms, to ship in the app.

Fable's later books (Pride and Prejudice, Moby-Dick, The War of the Worlds, Treasure Island) have no hand-built rooms.
Their three rooms are made by the same service that makes rooms for uploaded books (interpreter/internal/rooms,
docs/GENERATED_ROOMS.md) and bundled: FableBuild.SyncData copies content/rooms into StreamingAssets/rooms and indexes
them, and the app copies a room out of the APK the first time it is opened (GeneratedRooms.Unpack).

    python3 tools/bundle_rooms.py --service-dir out/books-rooms/out/rooms/worlds --slug worlds
    python3 tools/bundle_rooms.py --service-dir out/rooms/u-fd5194716872 --slug pride --chapter-offset -2

For each room r1..r3 in the service's book folder: the package files (room.gltf, room.bin, textures/*.jpg, thumb.png)
are copied to content/rooms/<slug>/r<N>/, file names are made plain ASCII (spaces become underscores, the glTF's image
URIs follow) so nothing needs escaping inside the APK, and package.json is rewritten with the book's slug and fresh
SHA-256s. The room script and the review notes go to r<N>/source/ (kept for the record, not shipped). plan.json is
copied beside the rooms. --chapter-offset renumbers chapter ids (cNN) when the rooms were planned from another
import of the same text. Only the Python standard library is used.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "content", "rooms")


def plain(name):
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def chapter(cid, slug, offset):
    if not cid:
        return cid
    m = re.match(r"^[^:]+:c(\d+)$", cid)
    if not m:
        return slug + ":" + cid.split(":", 1)[-1]
    return "%s:c%02d" % (slug, int(m.group(1)) + offset)


def bundle_room(src, dst, slug, n, offset):
    pkg = json.load(open(os.path.join(src, "package.json"), encoding="utf-8"))
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(os.path.join(dst, "textures"))
    rename = {}
    for f in pkg["files"]:
        rel = f["path"]
        if sha256(os.path.join(src, rel)) != f["sha256"]:
            sys.exit("%s: %s does not match its package checksum" % (src, rel))
        new = "/".join(plain(p) for p in rel.split("/"))
        rename[rel] = new
        if rel != "room.gltf":
            shutil.copyfile(os.path.join(src, rel), os.path.join(dst, new))
    gltf = json.load(open(os.path.join(src, "room.gltf"), encoding="utf-8"))
    for coll in ("images", "buffers"):
        for item in gltf.get(coll, []):
            uri = item.get("uri")
            if uri and not uri.startswith("data:"):
                item["uri"] = rename.get(urllib.parse.unquote(uri), plain(urllib.parse.unquote(uri)))
                if not os.path.exists(os.path.join(dst, item["uri"])):
                    sys.exit("%s: %s is not in the package" % (src, item["uri"]))
    with open(os.path.join(dst, "room.gltf"), "w", encoding="utf-8") as fh:
        json.dump(gltf, fh, ensure_ascii=False, separators=(",", ":"))
    files, total = [], 0
    for f in pkg["files"]:
        p = rename[f["path"]]
        full = os.path.join(dst, p)
        size = os.path.getsize(full)
        total += size
        files.append({"path": p, "size": size, "sha256": sha256(full)})
    out = dict(pkg)
    out.update({"book": slug, "room": n, "chapter": chapter(pkg.get("chapter"), slug, offset), "files": files, "bytes": total})
    with open(os.path.join(dst, "package.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.makedirs(os.path.join(dst, "source"))
    for keep in ("script.py", "review.txt"):
        if os.path.exists(os.path.join(src, keep)):
            shutil.copyfile(os.path.join(src, keep), os.path.join(dst, "source", keep))
    print("  r%d %s: %d files, %.1f MB, %s triangles" % (n, out.get("title"), len(files), total / 1e6, out.get("triangles")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--service-dir", required=True, help="the service's out/rooms/<book> folder (holds plan.json and r1..r3)")
    ap.add_argument("--slug", required=True, help="the Fable book (content/books/<slug>)")
    ap.add_argument("--chapter-offset", type=int, default=0)
    a = ap.parse_args()
    if not os.path.exists(os.path.join(ROOT, "content", "books", a.slug, "book.json")):
        sys.exit("no book %s in content/books" % a.slug)
    dest = os.path.join(OUT, a.slug)
    os.makedirs(dest, exist_ok=True)
    print(a.slug)
    plan = json.load(open(os.path.join(a.service_dir, "plan.json"), encoding="utf-8"))
    for st in plan:
        st["chapter"] = chapter(st.get("chapter"), a.slug, a.chapter_offset)
    with open(os.path.join(dest, "plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    for n in (1, 2, 3):
        src = os.path.join(a.service_dir, "r%d" % n)
        if os.path.exists(os.path.join(src, "package.json")):
            bundle_room(src, os.path.join(dest, "r%d" % n), a.slug, n, a.chapter_offset)
        else:
            print("  r%d: not built" % n)


if __name__ == "__main__":
    main()
