"""
Fable: validate the book maps (content/maps/<slug>/map.json) against docs/MAPS.md.

  python3 tools/check_maps.py                 # check all books; exit 1 on any error
  python3 tools/check_maps.py treasure oz     # only these books
  python3 tools/check_maps.py --fill treasure # rewrite each place's firstSentence to its earliest mention
  python3 tools/check_maps.py --find treasure "Spy-glass" "Bristol"   # list sentences that mention a phrase

Standard library only. Checks: the schema (fields, types, enums), unique ids, view references, files on disk,
image aspect ratios (JPEG/PNG headers read directly), lat/lon ranges, u/v in 0..1, every alias occurring in the
book text, and firstSentence being a real sentence id that is the place's earliest mention (the headset hides a
place until the reader reaches it, so a later firstSentence would hide a place the reader has already met, and an
earlier one would be a spoiler).

Phrase matching here is the one docs/MAPS.md gives for the headset (normalise, whole words), with one extra rule
for finding mentions in the text: a single-word phrase that starts with a capital letter must match with that
capital (so "Bath" does not match "a bath"); everything else matches case-insensitively.
"""
import json, os, re, struct, sys, unicodedata

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONTENT = os.path.join(ROOT, "content")
SLUGS = ["alice", "oz", "odyssey", "gulliver", "pride", "mobydick", "worlds", "treasure"]
LOCATED = {"geocoded", "book", "approximate", "traditional", "drawn", "scan"}
KINDS = {"city", "town", "village", "house", "building", "street", "region", "country", "island", "sea", "coast",
         "harbour", "river", "lake", "mountain", "forest", "road", "field", "garden", "room", "ship-position", "place"}
PLACE_KEYS = {"id", "name", "aliases", "view", "lat", "lon", "u", "v", "located", "kind", "firstSentence", "note"}
VIEW_KEYS = {"globe": {"id", "kind", "title", "texture", "normal", "focus"},
             "scroll": {"id", "kind", "title", "image", "aspect", "height", "parent", "anchor", "source", "attribution"}}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def norm(s):
    """The headset's normalisation (docs/MAPS.md): NFKC, curly quotes folded, en/em dashes to spaces, hyphens to '-', punctuation other than
    apostrophes and hyphens removed, whitespace collapsed, lower-cased, a leading 'the ' dropped."""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub("[\u2012-\u2015]", " ", s)  # figure, en and em dashes separate words
    s = re.sub("[\u2010\u2011]", "-", s)  # hyphens join them
    s = re.sub(r"[^\w'\- ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    if s.startswith("the "):
        s = s[4:]
    return s


def fold(s):
    """Text form used to search the book: like norm() but keeps case and the leading article."""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'")
    s = re.sub("[\u2012-\u2015]", " ", s)  # figure, en and em dashes separate words
    s = re.sub("[\u2010\u2011]", "-", s)  # hyphens join them
    s = re.sub(r"[^\w'\- ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def phrase_re(phrase):
    p = fold(phrase)
    if p.lower().startswith("the "):
        p = p[4:]
    body = r"\s+".join(re.escape(w) for w in p.split(" "))
    single_cap = " " not in p and p[:1].isupper()
    return re.compile(r"(?<![\w'-])" + body + r"(?![\w-])", 0 if single_cap else re.IGNORECASE)


def load_book(slug):
    b = json.load(open(os.path.join(CONTENT, "books", slug, "book.json"), encoding="utf-8"))
    sents = []
    for c in b["chapters"]:
        for p in c["paragraphs"]:
            for s in p["sentences"]:
                sents.append((s["id"], fold(s["text"])))
    return b, sents


def image_size(path):
    with open(path, "rb") as f:
        head = f.read(32)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", head[16:24])
            return w, h
        if head[:2] != b"\xff\xd8":
            return None
        f.seek(2)
        while True:
            m = f.read(2)
            if len(m) < 2 or m[0] != 0xFF:
                return None
            if m[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                f.read(3)
                h, w = struct.unpack(">HH", f.read(4))
                return w, h
            ln = struct.unpack(">H", f.read(2))[0]
            f.seek(ln - 2, 1)


def phrases(pl):
    out = [pl.get("name", "")] + list(pl.get("aliases", []))
    seen, res = set(), []
    for p in out:
        if p and norm(p) not in seen:
            seen.add(norm(p))
            res.append(p)
    return res


def first_mention(pl, sents):
    regs = [phrase_re(p) for p in phrases(pl)]
    for i, (sid, text) in enumerate(sents):
        if any(r.search(text) for r in regs):
            return i, sid
    return None, None


def check(slug, fill=False):
    errs, warns = [], []
    path = os.path.join(CONTENT, "maps", slug, "map.json")
    if not os.path.exists(path):
        return [f"{slug}: no map.json"], []
    m = json.load(open(path, encoding="utf-8"))
    book, sents = load_book(slug)
    index = {sid: i for i, (sid, _) in enumerate(sents)}
    E = lambda s: errs.append(f"{slug}: {s}")
    W = lambda s: warns.append(f"{slug}: {s}")

    if m.get("version") != 1:
        E("version must be 1")
    if m.get("book") != slug:
        E(f"book must be {slug!r}")
    views = m.get("views") or []
    if not views:
        E("no views")
    vids = {}
    for v in views:
        vid, kind = v.get("id"), v.get("kind")
        if not isinstance(vid, str) or not ID_RE.match(vid):
            E(f"view id {vid!r} must be lower-case-hyphenated")
            continue
        if vid in vids:
            E(f"duplicate view id {vid}")
        vids[vid] = v
        if kind not in VIEW_KEYS:
            E(f"view {vid}: kind must be globe or scroll")
            continue
        extra = set(v) - VIEW_KEYS[kind]
        if extra:
            E(f"view {vid}: unknown keys {sorted(extra)}")
        if not isinstance(v.get("title"), str) or not v["title"]:
            E(f"view {vid}: title required")
        files = ["texture"] if kind == "globe" else ["image", "source"]
        files += [k for k in ("normal", "height") if k in v]
        for k in files:
            f = v.get(k)
            if not isinstance(f, str) or not f.startswith("maps/"):
                E(f"view {vid}: {k} must be a path under maps/")
                continue
            if not os.path.isfile(os.path.join(CONTENT, f)):
                E(f"view {vid}: {k} {f} does not exist")
        if kind == "globe":
            fo = v.get("focus")
            if fo is not None and not (isinstance(fo, dict) and set(fo) == {"lat", "lon"}
                                       and -90 <= fo["lat"] <= 90 and -180 <= fo["lon"] <= 180):
                E(f"view {vid}: focus must be {{lat, lon}} in range")
        if kind == "scroll":
            a = v.get("aspect")
            img = os.path.join(CONTENT, v.get("image", "") or "x")
            if not isinstance(a, (int, float)) or a <= 0:
                E(f"view {vid}: aspect must be a positive number")
            elif os.path.isfile(img):
                sz = image_size(img)
                if not sz:
                    E(f"view {vid}: image is not a JPEG or PNG")
                else:
                    if abs(sz[0] / sz[1] - a) > 0.01:
                        E(f"view {vid}: aspect {a} but image is {sz[0]}x{sz[1]} ({sz[0]/sz[1]:.3f})")
                    if max(sz) > 4096:
                        E(f"view {vid}: image {sz[0]}x{sz[1]} exceeds 4096")
                    hp = v.get("height")
                    if hp and os.path.isfile(os.path.join(CONTENT, hp)):
                        hs = image_size(os.path.join(CONTENT, hp))
                        if not hs or abs(hs[0] / hs[1] - sz[0] / sz[1]) > 0.01 or max(hs) > 1024:
                            E(f"view {vid}: height map {hs} must match the image aspect and be <= 1024")
    for v in views:
        if v.get("kind") != "scroll":
            continue
        par, anc = v.get("parent"), v.get("anchor")
        if (par is None) != (anc is None):
            E(f"view {v.get('id')}: parent and anchor go together")
        if par is not None and par not in vids:
            E(f"view {v.get('id')}: parent {par} is not a view")

    places = m.get("places") or []
    if not places:
        E("no places")
    pids = {}
    owners = {}  # normalised phrase -> place id
    for pl in places:
        pid = pl.get("id")
        if not isinstance(pid, str) or not ID_RE.match(pid):
            E(f"place id {pid!r} must be lower-case-hyphenated")
            continue
        if pid in pids:
            E(f"duplicate place id {pid}")
        pids[pid] = pl
        extra = set(pl) - PLACE_KEYS
        if extra:
            E(f"place {pid}: unknown keys {sorted(extra)}")
        for k in ("name", "note"):
            if not isinstance(pl.get(k), str) or not pl[k].strip():
                E(f"place {pid}: {k} required")
        if len(pl.get("note", "")) > 200:
            W(f"place {pid}: note is {len(pl['note'])} chars (keep to one short line)")
        if not isinstance(pl.get("aliases"), list) or not all(isinstance(a, str) and a for a in pl["aliases"]):
            E(f"place {pid}: aliases must be a list of strings")
            continue
        if pl.get("located") not in LOCATED:
            E(f"place {pid}: located must be one of {sorted(LOCATED)}")
        if pl.get("kind") not in KINDS:
            E(f"place {pid}: kind {pl.get('kind')!r} must be one of {sorted(KINDS)}")
        v = vids.get(pl.get("view"))
        if not v:
            E(f"place {pid}: view {pl.get('view')!r} does not exist")
        elif v["kind"] == "globe":
            if set(pl) & {"u", "v"}:
                E(f"place {pid}: globe place takes lat/lon, not u/v")
            lat, lon = pl.get("lat"), pl.get("lon")
            if not isinstance(lat, (int, float)) or not -90 <= lat <= 90:
                E(f"place {pid}: lat out of range")
            if not isinstance(lon, (int, float)) or not -180 <= lon <= 180:
                E(f"place {pid}: lon out of range")
            if pl.get("located") in ("drawn", "scan"):
                E(f"place {pid}: located {pl['located']} is for scroll places")
        else:
            if set(pl) & {"lat", "lon"}:
                E(f"place {pid}: scroll place takes u/v, not lat/lon")
            for k in ("u", "v"):
                x = pl.get(k)
                if not isinstance(x, (int, float)) or not 0 <= x <= 1:
                    E(f"place {pid}: {k} must be in 0..1")
        for p in phrases(pl):
            n = norm(p)
            if len(n) < 3:
                E(f"place {pid}: phrase {p!r} too short")
            if n in owners and owners[n] != pid:
                E(f"phrase {p!r} belongs to both {owners[n]} and {pid}")
            owners[n] = pid
            if not any(phrase_re(p).search(t) for _, t in sents):
                E(f"place {pid}: alias {p!r} does not occur in the book")
        i, sid = first_mention(pl, sents)
        if sid is None:
            continue
        if fill:
            pl["firstSentence"] = sid
        fs = pl.get("firstSentence")
        if fs not in index:
            E(f"place {pid}: firstSentence {fs!r} is not a sentence id")
        elif fs != sid:
            E(f"place {pid}: firstSentence {fs} but the earliest mention is {sid}: {sents[i][1][:90]!r}")
    for v in views:
        anc = v.get("anchor")
        if anc is not None:
            ap = pids.get(anc)
            if not ap:
                E(f"view {v['id']}: anchor {anc} is not a place")
            elif ap.get("view") != v.get("parent"):
                E(f"view {v['id']}: anchor {anc} must be a place on the parent view {v.get('parent')}")
    used = {pl.get("view") for pl in places}
    for vid in vids:
        if vid not in used:
            W(f"view {vid} has no places")
    if fill and not errs:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return errs, warns


def find(slug, terms):
    _, sents = load_book(slug)
    for t in terms:
        r = phrase_re(t)
        hits = [(sid, txt) for sid, txt in sents if r.search(txt)]
        print(f"== {t!r}: {len(hits)} sentences")
        for sid, txt in hits[:6]:
            mm = r.search(txt)
            a = max(0, mm.start() - 60)
            print(f"  {sid}: ...{txt[a:mm.end() + 60]}...")


def main(argv):
    if argv[:1] == ["--find"]:
        find(argv[1], argv[2:])
        return 0
    fill = "--fill" in argv
    slugs = [a for a in argv if not a.startswith("--")] or SLUGS
    total = 0
    for s in slugs:
        errs, warns = check(s, fill)
        for w in warns:
            print("warn:", w)
        for e in errs:
            print("ERROR:", e)
        total += len(errs)
        if not errs:
            m = json.load(open(os.path.join(CONTENT, "maps", s, "map.json"), encoding="utf-8"))
            print(f"ok: {s}: {len(m['views'])} views, {len(m['places'])} places")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
