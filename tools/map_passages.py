#!/usr/bin/env python3
"""Link every Step In passage sentence (book/passages.json, ids like hall-of-doors:004) to the sentence of the
full book it comes from (content/books/<slug>/book.json, ids like alice:c01.p012.s01).

    python3 tools/map_passages.py            # writes bookSentence on each passage sentence, bookFrom/bookTo per scene

The passages were cut from the Gutenberg text and the book is the Standard Ebooks edition, so the wording differs
in small ways (to-day / today, punctuation). Matching is fuzzy, in reading order, and fails loudly below 0.75.
"""
import difflib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASSAGES = os.path.join(ROOT, "book", "passages.json")
BOOK_OF = {"alice": ["hall-of-doors", "mad-tea-party", "queens-croquet-ground"]}

def norm(s):
    s = s.lower().replace("-", "").replace("’", "'")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def main():
    data = json.load(open(PASSAGES, encoding="utf-8"))
    for slug, scene_ids in BOOK_OF.items():
        book = json.load(open(os.path.join(ROOT, "content", "books", slug, "book.json"), encoding="utf-8"))
        flat = [(s["id"], norm(s["text"])) for c in book["chapters"] for p in c["paragraphs"] for s in p["sentences"]]
        for scene in data["scenes"]:
            if scene["id"] not in scene_ids:
                continue
            pos, first, last, worst = 0, None, None, 1.0
            for para in scene["paragraphs"]:
                for sent in para:
                    t = norm(sent["text"])
                    best, best_i = 0.0, None
                    # a passage sentence may be a fragment of a longer book sentence (or the reverse): score the overlap
                    for i in range(pos, min(len(flat), pos + 4000)):
                        b = flat[i][1]
                        if not b or (t[:12] not in b and b[:12] not in t and difflib.SequenceMatcher(None, t[:40], b[:40]).ratio() < 0.6):
                            continue
                        r = difflib.SequenceMatcher(None, t, b).ratio()
                        if t in b or b in t:
                            r = max(r, 0.95)
                        if r > best:
                            best, best_i = r, i
                        if r > 0.97:
                            break
                    if best_i is None or best < 0.75:
                        sys.exit("no match for %s (best %.2f): %s" % (sent["id"], best, sent["text"][:80]))
                    sent["bookSentence"] = flat[best_i][0]
                    worst = min(worst, best)
                    first = first or flat[best_i][0]
                    last = flat[best_i][0]
                    pos = best_i
            scene["book"] = slug
            scene["bookFrom"], scene["bookTo"] = first, last
            print("%-24s %s .. %s   (weakest match %.2f)" % (scene["id"], first, last, worst))
    with open(PASSAGES, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

if __name__ == "__main__":
    main()
