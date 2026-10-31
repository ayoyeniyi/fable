#!/usr/bin/env python3
"""Turn a Standard Ebooks EPUB or a Project Gutenberg plain-text file into Fable's normalised book JSON.

    python3 tools/ingest_book.py all                 # every book in tools/books.json
    python3 tools/ingest_book.py alice odyssey       # some of them
    python3 tools/ingest_book.py oz --source my.epub # use a local file instead of downloading

Writes content/books/<slug>/book.json and content/books/<slug>/SOURCE.md. Downloads are cached in
out/sources/ (git-ignored); the SHA-256 of the exact file used goes into SOURCE.md.

book.json:
  { slug, title, author, translator?, year, source{...}, stats{...},
    chapters: [ { id, index, kind: front|chapter, label, title, subtitle?, part?,
                  paragraphs: [ { id, style: prose|verse|heading, sentences: [ {id, text, lineBefore?} ] } ] } ] }

Ids are <slug>:<chapter>.p<nnn>.s<nn>, e.g. alice:c01.p004.s02 (front matter uses f01, f02...).
They depend only on the source text, so re-running on the same file gives the same ids.

What is kept: the author's text, including the author's own prefaces, introductions and epigraphs.
What is dropped: title pages, imprints, colophons, licence blocks, lists of illustrations,
translators' and editors' prefaces, and all footnotes/endnotes with their reference marks.
Only the Python standard library is used.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "tools", "books.json")
CACHE = os.path.join(ROOT, "out", "sources")
OUT = os.path.join(ROOT, "content", "books")

XHTML = "{http://www.w3.org/1999/xhtml}"
EPUB_TYPE = "{http://www.idpf.org/2007/ops}type"
OPF = "{http://www.idpf.org/2007/opf}"
DC = "{http://purl.org/dc/elements/1.1/}"

DOT = "․"  # placeholder for a full stop that does not end a sentence (abbreviations)

# --------------------------------------------------------------------------- text helpers

def clean(s):
    s = s.replace("﻿", "").replace("⁠", "")    # SE word joiners around dashes
    s = s.replace(" ", " ").replace(" ", " ")  # hair and no-break spaces
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    return s.strip()

ABBREVIATIONS = ["Mr", "Mrs", "Messrs", "Dr", "St", "Capt", "Col", "Gen", "Lieut", "Sir", "Rev", "Mt", "vol", "viz", "ch",
                 "i.e", "e.g", "etc", "cf", "ibid", "Esq"]
ABBR_RE = re.compile(r"\b(" + "|".join(re.escape(a) for a in ABBREVIATIONS) + r")\.(?=\s|$)")
INITIAL_RE = re.compile(r"\b([A-HJ-Z])\.(?=\s?[A-Z])")  # L. Frank, J. R. (not "I.", which ends sentences)
NUMBER_RE = re.compile(r"\bNo\.(?=\s?\d)")                # No. 7, but "No. If..." is a sentence

OPENERS = "“‘\"'(["
CLOSERS = "”’\"')]"
SPLIT_RE = re.compile(r"([.!?…]+[" + re.escape(CLOSERS) + r"]*)(\s+)(?=[" + re.escape(OPENERS) + r"]*[A-Z0-9])")

def protect(s):
    s = ABBR_RE.sub(lambda m: m.group(1) + DOT, s)
    s = INITIAL_RE.sub(lambda m: m.group(1) + DOT, s)
    s = NUMBER_RE.sub("No" + DOT, s)
    return s

def sentences(text):
    """Split a paragraph into sentences. A break needs terminal punctuation, optional closing quotes,
    whitespace, then a capital (or an opening quote before one): “Oh!” said Alice stays one sentence."""
    return [t for t, _ in sentences_with_breaks(text)]

def sentences_with_breaks(text):
    """As sentences(), but also says whether a line break (verse) came before each sentence."""
    s = protect(text)
    parts, last, brk = [], 0, False
    for m in SPLIT_RE.finditer(s):
        parts.append((s[last:m.end(1)], brk))
        brk = "\n" in m.group(2)
        last = m.end(2)
    parts.append((s[last:], brk))
    out = []
    for p, b in parts:
        p = p.replace(DOT, ".").strip()
        if not p:
            continue
        if out and len(p) < 3:          # stray punctuation: attach to the previous sentence
            out[-1] = (out[-1][0] + p, out[-1][1])
        else:
            out.append((p, b))
    return out

# --------------------------------------------------------------------------- Standard Ebooks EPUB

SKIP_FILES = {"titlepage", "imprint", "halftitlepage", "frontispiece", "loi", "colophon", "uncopyright", "endnotes", "toc"}
KEEP_FRONT = {"epigraph", "introduction", "preface", "foreword", "dedication", "prologue"}

def etype(el):
    return (el.get(EPUB_TYPE) or "").split()

def tag(el):
    return el.tag.replace(XHTML, "")

def inline_text(el):
    """Text of an inline subtree: abbreviation dots protected, note references dropped, <br> as newline."""
    parts = []
    def walk(e, in_abbr=False):
        t = tag(e)
        if t == "a" and ("noteref" in etype(e) or e.get("role") == "doc-noteref"):
            if e.tail:
                parts.append(e.tail)
            return
        if t == "br":
            parts.append("\n")
        abbr = in_abbr or t == "abbr"
        if e.text:
            parts.append(e.text.replace(".", DOT) if abbr else e.text)
        for c in e:
            walk(c, abbr)
        if e.tail and e is not el:
            parts.append(e.tail)
    walk(el)
    return "".join(parts)

def verse_text(p):
    lines = []
    for c in p:
        if tag(c) == "span":
            lines.append(clean(inline_text(c).replace("\n", " ")))
    if not lines:
        return clean(inline_text(p))
    return "\n".join(l for l in lines if l)

def header_info(section):
    """Label (I, II...), title and subtitle from a section's <header>/<hgroup>/<h*>."""
    label = title = subtitle = None
    for h in section.iter():
        t = tag(h)
        types = etype(h)
        if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            ord_span = [c for c in h.iter() if "z3998:ordinal" in etype(c)]
            if "z3998:ordinal" in types or ord_span:
                label = clean(inline_text(ord_span[0] if ord_span else h)).replace(DOT, ".")
            elif title is None:
                title = clean(inline_text(h)).replace(DOT, ".")
        elif t == "p" and "title" in types and title is None:
            title = clean(inline_text(h)).replace(DOT, ".")
        elif t == "p" and ("subtitle" in types or h.get("role") == "doc-subtitle" or "se:bridgehead" in types):
            subtitle = clean(inline_text(h)).replace(DOT, ".")
    return label, title, subtitle

def blocks(el, out, in_poem=False):
    """Collect paragraphs (style, text) from a section, in reading order."""
    for c in el:
        t = tag(c)
        types = etype(c)
        if t in ("header", "hgroup"):
            continue
        if t.startswith("h") and t[1:].isdigit() and tag(el) == "section":
            continue        # the section's own title, already in header_info
        if t == "section":
            continue        # nested sections are their own chapters
        poem = in_poem or any(x in types for x in ("z3998:poem", "z3998:verse", "z3998:song", "z3998:hymn"))
        if t == "p":
            if "se:bridgehead" in types:
                continue
            txt = verse_text(c) if poem else clean(inline_text(c))
            if txt:
                out.append(("verse" if poem else "prose", txt))
        elif t in ("blockquote", "div", "footer", "figure"):
            if t == "figure":
                continue
            blocks(c, out, poem)
        elif t in ("ol", "ul"):
            for li in c:
                txt = clean(inline_text(li))
                if txt:
                    out.append(("prose", txt))
        elif t == "table":
            for tr in c.iter(XHTML + "tr"):
                cells = [clean(inline_text(td)) for td in tr if tag(td) in ("td", "th")]
                cells = [x for x in cells if x]
                if cells:
                    out.append(("prose", " — ".join(cells)))
        elif t in ("hr",):
            continue
        elif t.startswith("h") and t[1:].isdigit():
            out.append(("heading", clean(inline_text(c))))

def read_epub(path):
    z = zipfile.ZipFile(path)
    container = ET.fromstring(z.read("META-INF/container.xml"))
    opf_path = next(e.get("full-path") for e in container.iter() if e.get("full-path"))
    base = os.path.dirname(opf_path)
    opf = ET.fromstring(z.read(opf_path))
    manifest = {i.get("id"): i.get("href") for i in opf.iter(OPF + "item")}
    spine = [manifest[r.get("idref")] for r in opf.iter(OPF + "itemref")]
    meta = {
        "identifier": next((e.text for e in opf.iter(DC + "identifier")), None),
        "dcSources": [e.text for e in opf.iter(DC + "source")],
        "modified": next((e.text for e in opf.iter(OPF + "meta") if e.get("property") == "dcterms:modified"), None),
        "revision": next((e.text for e in opf.iter(OPF + "meta") if e.get("property") == "se:revision-number"), None),
        "rights": next((e.text for e in opf.iter(DC + "rights")), None),
    }
    colophon = None
    chapters, part = [], None
    for href in spine:
        name = os.path.splitext(os.path.basename(href))[0]
        doc = ET.fromstring(z.read(os.path.join(base, href).replace("\\", "/")))
        if name == "colophon":
            colophon = re.sub(r"\s+", " ", " ".join(inline_text(p).replace(DOT, ".") for p in doc.iter(XHTML + "p"))).strip()
            rev = re.search(r"based on revision (\w+)", colophon)
            if rev and not meta.get("revision"):
                meta["revision"] = rev.group(1)
        if name in SKIP_FILES:
            continue
        body = doc.find(XHTML + "body")
        btypes = etype(body)
        for section in body.iter(XHTML + "section"):
            stypes = etype(section)
            if "part" in stypes or section.get("role") == "doc-part":
                label, title, _ = header_info(section)
                part = " ".join(x for x in (("Part " + label) if label else None, title) if x)
                if not any(tag(c) not in ("hgroup", "header") for c in section):
                    continue
            front = "frontmatter" in btypes
            if front and not (KEEP_FRONT & set(stypes) or section.get("id") in KEEP_FRONT):
                continue
            if "backmatter" in btypes:
                continue
            label, title, subtitle = header_info(section)
            paras = []
            blocks(section, paras)
            if not paras:
                continue
            if section.get("id") == "epigraph" and not title:
                title = "Epigraph"
            chapters.append({"front": front, "label": label, "title": title, "subtitle": subtitle,
                             "part": None if front else part, "paras": paras})
    return chapters, meta, colophon

# --------------------------------------------------------------------------- Gutenberg plain text

ROMAN = re.compile(r"^(BOOK|CHAPTER|PART)\s+([IVXLC]+)\.?\s*$")

def read_gutenberg(path):
    raw = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n")
    start = re.search(r"^\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*$", raw, re.M)
    end = re.search(r"^\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*$", raw, re.M)
    if not start or not end:
        sys.exit("gutenberg: licence markers not found")
    body = raw[start.end():end.start()]
    notes = re.search(r"^FOOTNOTES:\s*$", body, re.M)       # Butler's notes follow the text
    marks = set()
    if notes:
        marks = set(re.findall(r"^\[(\d+)\]", body[notes.start():], re.M))
        body = body[:notes.start()]
    # footnote marks are bare numbers, usually glued to the word ("sea24"), sometimes alone after
    # punctuation ("wine.” 137"); only numbers that name a real footnote are removed
    body = re.sub(r"(?<=[A-Za-z’”.,;:!?)\]])(\d{1,3})(?!\d)", lambda m: "" if m.group(1) in marks else m.group(1), body)
    body = re.sub(r"(?<=[.,;:”’])([ \n])(\d{1,3})(?=\s)", lambda m: m.group(1) if m.group(2) in marks else m.group(0), body)
    lines = body.split("\n")
    # the text starts at the last "BOOK I" heading: earlier ones belong to the table of contents,
    # and everything before it (translator's prefaces) is dropped
    firsts = [i for i, l in enumerate(lines) if ROMAN.match(l.strip()) and ROMAN.match(l.strip()).group(2) == "I"]
    if not firsts:
        sys.exit("gutenberg: no BOOK/CHAPTER I heading found")
    first = firsts[-1]
    chapters, cur, buf = [], None, []
    def flush():
        if buf and cur is not None:
            text = " ".join(x.strip() for x in buf)
            text = re.sub(r"\s*\[\d+\]", "", text)               # footnote markers
            text = re.sub(r"_([^_]+)_", r"\1", text)              # _italic_
            text = clean(text)
            if text:
                if cur["subtitle"] is None and text.isupper():
                    cur["subtitle"] = text.rstrip(".")
                else:
                    cur["paras"].append(("prose", text))
        buf.clear()
    for l in lines[first:]:
        m = ROMAN.match(l.strip())
        if m:
            flush()
            cur = {"front": False, "label": m.group(2), "title": m.group(1).title() + " " + m.group(2),
                   "subtitle": None, "part": None, "paras": []}
            chapters.append(cur)
        elif not l.strip():
            flush()
        else:
            buf.append(l)
    flush()
    header = raw[:start.start()]
    meta = {"releaseLine": next((l.strip() for l in header.split("\n") if l.startswith("Release date")), None),
            "updatedLine": next((l.strip() for l in header.split("\n") if "updated" in l.lower()), None),
            "credits": next((l.strip() for l in header.split("\n") if l.startswith("Credits")), None)}
    return chapters, meta, None

# --------------------------------------------------------------------------- output

def build(slug, cfg, chapters):
    out_ch, stats = [], {"chapters": 0, "paragraphs": 0, "sentences": 0, "words": 0}
    nf = nc = 0
    for ch in chapters:
        if ch["front"]:
            nf += 1; cid = "f%02d" % nf
        else:
            nc += 1; cid = "c%02d" % nc
        paras = []
        if ch["paras"] and ch["paras"][0][1][:1].islower():   # Gutenberg drops the small-caps opening capital
            st, tx = ch["paras"][0]; ch["paras"][0] = (st, tx[0].upper() + tx[1:])
        if not ch["title"] and ch["label"]:
            ch["title"] = "Chapter " + ch["label"]
        for pi, (style, text) in enumerate(ch["paras"], 1):
            pid = "%s:%s.p%03d" % (slug, cid, pi)
            sb = [(text, False)] if style == "heading" else sentences_with_breaks(text)
            ss = [t for t, _ in sb]
            sents = []
            for si, (t, b) in enumerate(sb, 1):
                sent = {"id": "%s.s%02d" % (pid, si), "text": t}
                if b and si > 1:
                    sent["lineBefore"] = True     # verse: this sentence starts a new line
                sents.append(sent)
            paras.append({"id": pid, "style": style, "sentences": sents})
            stats["sentences"] += len(sents)
            stats["words"] += sum(len(s.split()) for s in ss)
        stats["paragraphs"] += len(paras)
        c = {"id": "%s:%s" % (slug, cid), "index": len(out_ch), "kind": "front" if ch["front"] else "chapter",
             "label": ch["label"], "title": ch["title"]}
        if ch.get("subtitle"): c["subtitle"] = ch["subtitle"]
        if ch.get("part"): c["part"] = ch["part"]
        c["paragraphs"] = paras
        out_ch.append(c)
    stats["chapters"] = nc
    return out_ch, stats

def fetch(slug, cfg):
    os.makedirs(CACHE, exist_ok=True)
    ext = ".epub" if cfg["format"] == "se-epub" else ".txt"
    path = os.path.join(CACHE, slug + ext)
    if not os.path.exists(path):
        print("  downloading", cfg["url"])
        req = urllib.request.Request(cfg["url"], headers={"User-Agent": "fable-ingest/1.0 (book pipeline)"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
            f.write(r.read())
    return path

def write_source(slug, cfg, path, sha, meta, colophon, stats, dest):
    fmt = "Standard Ebooks EPUB" if cfg["format"] == "se-epub" else "Project Gutenberg plain text (UTF-8)"
    lines = ["# %s — source" % cfg["title"], "",
             "- **Work:** %s, %s%s (%d)" % (cfg["title"], cfg["author"], ", translated by " + cfg["translator"] if cfg.get("translator") else "", cfg["year"]),
             "- **Edition used:** %s" % fmt,
             "- **Edition page:** %s" % cfg["page"],
             "- **File downloaded:** %s" % cfg["url"],
             "- **SHA-256 of that file:** `%s`" % sha,
             "- **Ingested:** %s by `tools/ingest_book.py`" % datetime.now(timezone.utc).strftime("%Y-%m-%d")]
    if cfg["format"] == "se-epub":
        lines += ["- **Standard Ebooks identifier:** %s" % meta.get("identifier"),
                  "- **Revision / last modified:** %s / %s" % (meta.get("revision"), meta.get("modified")),
                  "- **Transcription sources (dc:source):** " + "; ".join(x for x in meta.get("dcSources", []) if x),
                  "- **Licence:** the text is in the public domain in the United States. Standard Ebooks releases its own edits, markup and cover design under CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/); see the edition page.",
                  ""]
        if colophon:
            lines += ["## Colophon (from the EPUB)", "", colophon, ""]
    else:
        lines += ["- **Project Gutenberg eBook:** #%d (%s)" % (cfg["gutenberg"], meta.get("releaseLine") or ""),
                  "- **%s**" % (meta.get("updatedLine") or ""),
                  "- **%s**" % (meta.get("credits") or ""),
                  "- **Licence:** the text is in the public domain in the United States. The Project Gutenberg header, footer and licence are removed, which the Project Gutenberg licence permits for public-domain texts; after that the text is not distributed as a Project Gutenberg eBook and the name appears here only to credit the source.",
                  ""]
    if cfg.get("note"):
        lines += ["**Note:** " + cfg["note"], ""]
    lines += ["## What `book.json` keeps", "",
              "The author's text, cover to cover, including the author's own prefaces, introductions and epigraphs. Dropped: title pages, imprints, colophons, licence blocks, lists of illustrations, translators' and editors' prefaces, and all footnotes/endnotes with their reference marks.", "",
              "## Counts", "",
              "%d chapters, %d paragraphs, %d sentences, %d words." % (stats["chapters"], stats["paragraphs"], stats["sentences"], stats["words"]), ""]
    with open(os.path.join(dest, "SOURCE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def ingest(slug, cfg, source=None):
    print(slug)
    path = source or fetch(slug, cfg)
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if cfg["format"] == "se-epub":
        chapters, meta, colophon = read_epub(path)
    else:
        chapters, meta, colophon = read_gutenberg(path)
    out_ch, stats = build(slug, cfg, chapters)
    book = {"slug": slug, "title": cfg["title"], "author": cfg["author"]}
    if cfg.get("translator"): book["translator"] = cfg["translator"]
    book.update({"year": cfg["year"],
                 "source": {"format": cfg["format"], "page": cfg["page"], "url": cfg["url"], "sha256": sha},
                 "stats": stats, "chapters": out_ch})
    dest = os.path.join(OUT, slug)
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "book.json"), "w", encoding="utf-8") as f:
        json.dump(book, f, ensure_ascii=False, indent=1)
        f.write("\n")
    write_source(slug, cfg, path, sha, meta, colophon, stats, dest)
    print("  %(chapters)d chapters, %(paragraphs)d paragraphs, %(sentences)d sentences, %(words)d words" % stats)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("books", nargs="+", help="slugs from tools/books.json, or 'all'")
    ap.add_argument("--source", help="local file to ingest instead of downloading (one book only)")
    a = ap.parse_args()
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    slugs = list(cfg) if a.books == ["all"] else a.books
    if a.source and len(slugs) != 1:
        sys.exit("--source takes exactly one book")
    for s in slugs:
        if s not in cfg:
            sys.exit("unknown book %r (see tools/books.json)" % s)
        ingest(s, cfg[s], a.source)

if __name__ == "__main__":
    main()
