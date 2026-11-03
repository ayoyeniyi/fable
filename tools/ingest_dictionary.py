#!/usr/bin/env python3
"""Build the offline dictionary behind Define from Webster's Unabridged Dictionary (1913), Project Gutenberg #29765.

    python3 tools/ingest_dictionary.py            # writes content/dictionary/webster1913.json and SOURCE.md

Only headwords that Fable’s eight books use are kept (the full dictionary is 29 MB). Each entry keeps the part of speech
and the first three senses, trimmed, without etymologies or quotations. The reader looks a highlighted word up
directly, then by stripping inflections (curtsied -> curtsy, keys -> key), which is why the forms the books use are
indexed with the headword they reduce to.

Stdlib only. The download is cached in out/sources/webster/.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://www.gutenberg.org/cache/epub/29765/pg29765.txt"
PAGE = "https://www.gutenberg.org/ebooks/29765"
CACHE = os.path.join(ROOT, "out", "sources", "webster", "pg29765.txt")
DEST = os.path.join(ROOT, "content", "dictionary")
BOOKS = ["alice", "oz", "odyssey", "gulliver", "pride", "mobydick", "worlds", "treasure"]
SENSES, SENSE_CHARS = 3, 240

HEAD = re.compile(r"^[A-Z][A-Z' \-;]*[A-Z]$|^[A-Z]$")
POS = re.compile(r"[,\s]\s*((?:n|v|a|adv|prep|conj|interj|pron)\b\.?(?:\s*(?:t|i|pl|sing)\.)*(?:\s*&\s*(?:t|i)\.)?)(?=\s|$|\[)")


def book_words():
    words = {}
    for slug in BOOKS:
        b = json.load(open(os.path.join(ROOT, "content", "books", slug, "book.json"), encoding="utf-8"))
        for c in b["chapters"]:
            for p in c["paragraphs"]:
                for s in p["sentences"]:
                    for w in re.findall(r"[A-Za-z][A-Za-z’'\-]*[A-Za-z]|[A-Za-z]", s["text"]):
                        w = w.lower().replace("’", "'")
                        words[w] = words.get(w, 0) + 1
    return words


def lemmas(w):
    """The word itself and the plain forms it may reduce to, most likely first (mirrored in Dictionary.cs)."""
    out = [w]
    if w.endswith("'s"): out.append(w[:-2])
    for suf, rep in (("ies", "y"), ("ied", "y"), ("ier", "y"), ("iest", "y"), ("ily", "y"), ("ves", "f"), ("ves", "fe"),
                     ("sses", "ss"), ("ches", "ch"), ("shes", "sh"), ("xes", "x"), ("es", ""), ("s", ""),
                     ("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"), ("d", ""), ("ly", ""), ("er", ""), ("est", ""), ("ness", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 2:
            stem = w[: len(w) - len(suf)] + rep
            out.append(stem)
            if suf in ("ing", "ed", "er", "est") and len(stem) > 2 and stem[-1] == stem[-2]:
                out.append(stem[:-1])   # stopped -> stop, bigger -> big
    if "-" in w: out.append(w.replace("-", ""))
    seen, res = set(), []
    for x in out:
        if x not in seen: seen.add(x); res.append(x)
    return res


def fetch():
    if not os.path.exists(CACHE):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        print("downloading", URL)
        urllib.request.urlretrieve(URL, CACHE)
    return open(CACHE, encoding="utf-8").read()


def body(text):
    a = text.find("*** START OF")
    b = text.find("*** END OF")
    a = text.find("\n", a) + 1 if a >= 0 else 0
    return text[a: b if b > 0 else len(text)]


def tidy(s):
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^(\([A-Z][^)]{0,30}\)\s*)+", "", s)          # subject labels: (Zoöl.), (Metal. & Manuf.)
    # a definition is followed by quotations and their authors ("... before him. Jer. xxxvi. 22."): keep the first sentence
    m = re.search(r"[a-z\)\]]\.\s+(?=[A-Z\"'])", s[25:])
    if m: s = s[: 25 + m.start() + 2]
    s = re.split(r"\s\(b\)\s", s)[0]
    if len(s) < 4 or s.startswith("See ") or s.endswith(":"): return ""
    s = re.sub(r"\s*See (?:Illust|Note|under)\b.*$", "", s)
    if len(s) > SENSE_CHARS:
        cut = s.rfind(";", 0, SENSE_CHARS)
        if cut < SENSE_CHARS // 2: cut = s.rfind(" ", 0, SENSE_CHARS)
        s = s[:cut].rstrip(" ,;:") + "…"
    return s


def parse(text):
    """headword (lower case) -> list of {pos, senses}"""
    lines = body(text).split("\n")
    entries = {}
    i, n = 0, len(lines)
    while i < n:
        line = lines[i].rstrip()
        if HEAD.match(line) and i + 1 < n and lines[i + 1].strip() and not HEAD.match(lines[i + 1].rstrip()):
            heads = [h.strip().lower() for h in line.split(";") if h.strip()]
            j = i + 1
            # gather the entry's block up to the next headword
            block = []
            while j < n:
                l = lines[j].rstrip()
                if HEAD.match(l) and j + 1 < n and lines[j + 1].strip() and (j == 0 or not lines[j - 1].strip()) and not HEAD.match(lines[j + 1].rstrip()):
                    break
                block.append(l); j += 1
            e = entry(block)
            for head in heads:
                entries.setdefault(head, []).append(e)
            i = j
            continue
        i += 1
    return entries


def entry(block):
    first = block[0] if block else ""
    m = POS.search(first)
    pos = m.group(1).strip() if m else ""
    if pos and not pos.endswith("."): pos += "."
    paras, cur = [], []
    for l in block[1:]:
        if not l.strip():
            if cur: paras.append(" ".join(cur)); cur = []
        else:
            cur.append(l.strip())
    if cur: paras.append(" ".join(cur))
    senses = []
    for p in paras:
        if p.startswith("Defn:"):
            senses.append(p[5:])
        elif re.match(r"^\d+\.\s", p):
            t = re.sub(r"^\d+\.\s*(\([A-Za-z. ]+\)\s*)?", "", p)
            if t.startswith("Defn:"): t = t[5:]
            if t and not re.match(r"^\(a\)", t): senses.append(t)
        elif senses and p.startswith("Note:"):
            continue
        if len(senses) >= SENSES: break
    senses = [t for t in (tidy(x) for x in senses) if t]
    # obsolete senses only when nothing current is left
    cur = [t for t in senses if "[Obs.]" not in t and "[R.]" not in t]
    senses = cur or senses
    return {"pos": pos, "senses": senses[:SENSES]}


def rank(es):
    """Most useful entry first: a real part of speech, current senses, more of them; pointers ("imp. of Reave") last."""
    def key(e):
        first = e["senses"][0] if e["senses"] else ""
        pointer = bool(re.match(r"^(imp\.|p\. p\.|pl\.|obs\.|of |a variant|same as|see )", first, re.I))
        return (pointer, -len(e["senses"]), e["pos"] == "")
    return sorted(es, key=key)


def main():
    raw = fetch()
    sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    entries = parse(raw)
    words = book_words()
    keep, forms = {}, {}
    for w in words:
        for cand in lemmas(w):
            if cand in entries:
                es = [e for e in entries[cand] if e["senses"]]
                if not es: continue
                keep[cand] = rank(es)[:3]
                if cand != w: forms[w] = cand
                break
    os.makedirs(DEST, exist_ok=True)
    out = {"source": "Webster's Unabridged Dictionary (1913), Project Gutenberg #29765", "entries": dict(sorted(keep.items())), "forms": dict(sorted(forms.items()))}
    path = os.path.join(DEST, "webster1913.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    distinct = len(words)
    covered = sum(1 for w in words if w in keep or w in forms)
    with open(os.path.join(DEST, "SOURCE.md"), "w", encoding="utf-8") as f:
        f.write(f"""# Dictionary — source

- **Work:** Webster's Unabridged Dictionary (G. & C. Merriam, 1913 edition text as transcribed for Project Gutenberg)
- **Edition page:** {PAGE}
- **File downloaded:** {URL}
- **SHA-256 of that file:** `{sha}`
- **Ingested:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')} by `tools/ingest_dictionary.py`
- **Licence:** the dictionary text is in the public domain in the United States. The Project Gutenberg header, footer and licence are removed, which the Project Gutenberg licence permits for public-domain texts; after that the text is not distributed as a Project Gutenberg eBook and the name appears here only to credit the source.

## What `webster1913.json` keeps

Only headwords Fable’s eight books use: {len(keep)} headwords, plus {len(forms)} inflected forms pointing at them. For each, the part of speech and the first {SENSES} senses, each cut to about {SENSE_CHARS} characters. Etymologies, pronunciations, quotations and compound phrases are dropped.

Coverage: {covered} of the {distinct} distinct words in Fable’s eight books ({100 * covered / distinct:.0f}%). The rest are mostly names (Dorothy, Telemachus, Lilliput) and coinages; Define says so instead of guessing.

The 1913 definitions are a century old. That suits these books, but some senses read oddly to a modern reader, and a few entries carry the prejudices of their time.
""")
    print(f"{len(keep)} headwords, {len(forms)} forms, {covered}/{distinct} book words covered, {os.path.getsize(path) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
