#!/usr/bin/env python3
"""A Step In for every chapter. For each chapter of a book that has no staged passage of its own, cut a short,
stageable excerpt (about a dozen sentences) straight from content/books/<slug>/book.json, link every sentence to
its book sentence, and set the passage's bookFrom/bookTo to the WHOLE chapter so the page offers "Step in" anywhere
in it (stepping in from a page before the excerpt starts at its first beat, after it at its last). Each new passage
is staged in one of the three built rooms, so it also gets a manifest: a copy of that room's manifest under its own id.

    python3 tools/chapter_passages.py          # rewrites book/passages.json and schema/manifest.<id>.json files

Run tools/map_passages.py first if the three original passages need re-linking; this tool widens their bookFrom/bookTo
to their chapters afterwards. Scripts for the new passages come from the interpreter:
    for id in ...; do interpreter/out/fable-interpreter generate --scene $id --out scripts/$id.baseline.json; done
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASSAGES = os.path.join(ROOT, "book", "passages.json")
ROOMS = {"hall": "hall-of-doors", "tea": "mad-tea-party", "garden": "queens-croquet-ground"}

# chapter id -> (passage id, title, room, phrase that opens the excerpt, sentences to take)
EXCERPTS = {
    "alice:c02": ("pool-of-tears", "The Pool of Tears", "hall", "Curiouser and curiouser", 13),
    "alice:c03": ("caucus-race", "A Caucus-Race", "garden", "the best way to explain it is to do it", 13),
    "alice:c04": ("rabbits-house", "The Rabbit Sends in a Little Bill", "garden", "It was the White Rabbit, trotting slowly back again", 13),
    "alice:c05": ("caterpillar", "Advice from a Caterpillar", "garden", "The Caterpillar and Alice looked at each other", 13),
    "alice:c06": ("cheshire-cat", "The Cheshire Cat", "garden", "The Cat only grinned when it saw Alice", 13),
    "alice:c09": ("mock-turtle", "The Mock Turtle's Story", "garden", "They very soon came upon a Gryphon", 13),
    "alice:c10": ("lobster-quadrille", "The Lobster Quadrille", "garden", "You may not have lived much under the sea", 13),
    "alice:c11": ("the-trial", "Who Stole the Tarts?", "tea", "The King and Queen of Hearts were seated on their throne", 13),
    "alice:c12": ("alices-evidence", "Alice's Evidence", "tea", "cried Alice, quite forgetting in the flurry", 13),
}
EXISTING_ROOM = {"hall-of-doors": "hall-of-doors", "mad-tea-party": "mad-tea-party", "queens-croquet-ground": "queens-croquet-ground"}

def norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')).strip().lower()

def main():
    data = json.load(open(PASSAGES, encoding="utf-8"))
    slug = "alice"
    book = json.load(open(os.path.join(ROOT, "content", "books", slug, "book.json"), encoding="utf-8"))
    chapters = {c["id"]: c for c in book["chapters"]}
    flat = []   # (sentence id, text, paragraph id, chapter id)
    for c in book["chapters"]:
        for p in c["paragraphs"]:
            for s in p["sentences"]:
                flat.append((s["id"], s["text"], p["id"], c["id"]))
    by_id = {f[0]: i for i, f in enumerate(flat)}

    def chapter_range(cid):
        ids = [f[0] for f in flat if f[3] == cid]
        return ids[0], ids[-1]

    def chapter_label(c):
        return (c.get("label") + ". " if c.get("label") else "") + c["title"]

    existing = {sc["id"]: sc for sc in data["scenes"]}
    # widen the original passages to their chapters
    for sc in data["scenes"]:
        if sc["id"] in EXISTING_ROOM and sc.get("bookFrom") in by_id:
            cid = flat[by_id[sc["bookFrom"]]][3]
            sc["bookFrom"], sc["bookTo"] = chapter_range(cid)
            sc.setdefault("room", EXISTING_ROOM[sc["id"]])

    added = []
    for cid, (pid, title, room, phrase, count) in EXCERPTS.items():
        if cid not in chapters:
            sys.exit("no chapter " + cid)
        start = next((i for i, f in enumerate(flat) if f[3] == cid and norm(phrase) in norm(f[1])), None)
        if start is None:
            sys.exit("phrase not found in %s: %s" % (cid, phrase))
        taken = [f for f in flat[start:start + count] if f[3] == cid]
        paragraphs, cur, cur_pid = [], [], None
        for n, (sid, text, para, _) in enumerate(taken):
            if para != cur_pid and cur:
                paragraphs.append(cur); cur = []
            cur_pid = para
            cur.append({"id": "%s:%03d" % (pid, n), "text": text, "bookSentence": sid})
        if cur:
            paragraphs.append(cur)
        before = [f[1] for f in flat[max(0, start - 10):start] if f[3] == cid]
        first, last = chapter_range(cid)
        scene = {
            "id": pid, "title": title, "chapter": chapter_label(chapters[cid]), "paragraphs": paragraphs,
            "sentenceCount": len(taken), "contextBefore": before, "book": slug, "bookFrom": first, "bookTo": last,
            "room": ROOMS[room],
        }
        if pid in existing:
            existing[pid].update(scene)
        else:
            data["scenes"].append(scene); existing[pid] = scene
        added.append((pid, cid, len(taken), ROOMS[room]))
        # the room's manifest under the passage's own id
        src = json.load(open(os.path.join(ROOT, "schema", "manifest.%s.json" % ROOMS[room]), encoding="utf-8"))
        src["sceneId"] = pid
        with open(os.path.join(ROOT, "schema", "manifest.%s.json" % pid), "w", encoding="utf-8") as f:
            json.dump(src, f, ensure_ascii=False, indent=2); f.write("\n")

    with open(PASSAGES, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2); f.write("\n")
    for pid, cid, n, room in added:
        print("%-18s %s  %2d sentences  staged in %s" % (pid, cid, n, room))
    print("%d passages in all" % len(data["scenes"]))

if __name__ == "__main__":
    main()
