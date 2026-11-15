"""
Fable: paint an aged-parchment, hand-drawn map from a layout JSON (the scroll maps of docs/MAPS.md).

  python3 tools/draw_map.py <layout.json> <out.jpg> [--height <out.height.png>] [--preview <small.jpg>]
  python3 tools/draw_map.py --overlay <map.json> <view-id> <out.png>   # debug: pins + names over a scroll image

Needs numpy, scipy and Pillow (e.g. a venv: pip install numpy scipy pillow). Fonts: EB Garamond (SIL OFL 1.1),
read from unity/Fable/Assets/Fable/Fonts. Deterministic: the same layout and seed give the same image.

Generic on purpose: the layouts for Fable's own drawn maps live in content/maps/<slug>/<view>.layout.json, and the
server can later render a Claude-written layout for an uploaded book with the same script.

LAYOUT FORMAT
-------------
Every position is [u, v]: 0..1 from the image's left and top edges. Sizes given as fractions are fractions of
the image height (so they look the same at any resolution). Every key except "size" is optional.

{
  "size": [2048, 1536],          output pixels (long side <= 4096)
  "seed": 7,                     random seed (wobble, stipple, glyph scatter)
  "background": "sea" | "land",  what lies outside the "land" polygons (default "land": the whole sheet is land)
  "palette": {"paper": "#e9d8ac", "ink": "#3a2716", "sea": "#9fb2a6", "land": "#e2cf9a"},   optional overrides
  "land":    [{"poly": [[u,v],...], "rough": 0.5}],             coastlines (closed); rough 0..1 = fractal detail
  "regions": [{"poly": [...], "tint": "#7a9a5a", "border": "dashed"|"solid"|"none", "rough": 0.2, "alpha": 0.45,
               "smooth": 3}],                                     smooth = corner-rounding passes (0 keeps shared edges exact)
                                                                  watercolour washes (countries, gardens)
  "water":   [{"poly": [...], "rough": 0.3}],                     lakes and pools, drawn like the sea
  "deserts": [{"poly": [...], "hole": [[u,v],...]}],              stippled sand (an optional hole: a ring of desert)
  "fields":  [{"poly": [...], "glyph": "flower"|"grass"|"crop", "color": "#b03020"}],
  "forests": [{"poly": [...], "density": 1.0, "kind": "round"|"pine"|"mixed"}],
  "hills":   [{"poly": [...], "density": 1.0}],                    hachured hillocks
  "mountains": [{"path": [[u,v],...], "size": 0.05}],              a ridge of peaks along a path
  "rivers":  [{"path": [...], "width": 0.004}],                    widens from the first point to the last
  "roads":   [{"path": [...], "style": "dashed"|"dotted"|"solid"|"band", "color": "#d8b23a", "width": 0.006}],
  "places":  [{"id": "pool-of-tears", "label": "The Pool of Tears", "u": 0.3, "v": 0.4,
               "glyph": "dot"|"town"|"city"|"house"|"castle"|"tower"|"palace"|"cave"|"door"|"hole"|"tree"|
                        "mushroom"|"table"|"tent"|"gate"|"star"|"cross"|"none",
               "size": 1.0, "labelPos": "right"|"left"|"above"|"below"|"center" (glyph none: center), "labelSize": 0.024, "italic": false}],
  "labels":  [{"text": "MUNCHKIN COUNTRY", "u": .., "v": .., "size": 0.04, "angle": 0, "spacing": 0.3,
               "italic": false, "alpha": 0.8}],                   free lettering (regions, seas); spacing in em
  "title":   {"text": "Wonderland", "sub": "drawn after Lewis Carroll", "u": 0.8, "v": 0.1, "size": 0.05},
  "compass": {"u": 0.9, "v": 0.85, "r": 0.07, "angle": 0},
  "decor":   {"tufts": 1.0, "trees": 0.5},                        sparse grass tufts / lone trees on open land
  "border":  true                                                 ruled double frame with a scale bar edge
}

"places" carry an "id" so a map.json can take its u,v from the layout (the place id in map.json). The height map
(--height) is grayscale: sea and water 0, land low, hills and forests a little higher, mountains highest; blurred,
long side 1024.
"""
import json, math, os, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FONT_DIR = os.path.join(ROOT, "unity", "Fable", "Assets", "Fable", "Fonts")
FONT_REG = os.path.join(FONT_DIR, "EBGaramond-Regular.ttf")
FONT_ITA = os.path.join(FONT_DIR, "EBGaramond-Italic.ttf")
SS = 2  # supersampling: draw at twice the size, then downsample (Pillow lines are not antialiased)

PALETTE = {"paper": "#e8d6a8", "ink": "#3a2716", "sea": "#93acb4", "land": "#e6d3a0", "water": "#8fa9b3"}


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


# ----------------------------------------------------------------------------- noise and geometry

def value_noise(shape, scale, rng, octaves=4):
    """Smooth fractal noise in 0..1 (bilinear-upsampled random grids)."""
    h, w = shape
    out = np.zeros(shape, np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale * (2 ** o)))
        g = rng.random((s + 1, int(s * w / h) + 2)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * np.asarray(im, np.float32) / 255.0
        tot += amp
        amp *= 0.5
    return out / tot


def chaikin(pts, closed, it=2):
    pts = [tuple(p) for p in pts]
    for _ in range(it):
        out = []
        n = len(pts)
        rng_ = range(n) if closed else range(n - 1)
        if not closed:
            out.append(pts[0])
        for i in rng_:
            a, b = pts[i], pts[(i + 1) % n]
            out.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            out.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        if not closed:
            out.append(pts[-1])
        pts = out
    return pts


def fractal(pts, closed, rough, rng, depth=5):
    """Midpoint displacement: coastline detail proportional to segment length."""
    if rough <= 0:
        return pts
    pts = list(pts)
    for _ in range(depth):
        out = []
        n = len(pts)
        for i in range(n if closed else n - 1):
            a, b = pts[i], pts[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy)
            off = (rng.random() - 0.5) * rough * 0.45 * L
            m = ((a[0] + b[0]) / 2 - dy / (L + 1e-9) * off, (a[1] + b[1]) / 2 + dx / (L + 1e-9) * off)
            out += [a, m]
        if not closed:
            out.append(pts[-1])
        pts = out
    return pts


def densify(pts, closed, step):
    out = []
    n = len(pts)
    for i in range(n if closed else n - 1):
        a, b = pts[i], pts[(i + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, int(L / step))
        for j in range(k):
            t = j / k
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    if not closed:
        out.append(pts[-1])
    return out


def wobble(pts, closed, amp, rng, step=5.0, wave=60.0):
    """Hand tremor: displace a densified line along its normal by a smooth random signal."""
    p = densify(pts, closed, step)
    if len(p) < 3 or amp <= 0:
        return p
    n = len(p)
    s = np.cumsum([0] + [math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) for i in range(1, n)])
    sig = np.zeros(n)
    for k in range(3):
        f = (k + 1) / wave
        sig += rng.normal() / (k + 1) * np.sin(2 * math.pi * f * s + rng.random() * 6.28)
    sig *= amp / max(1e-6, np.abs(sig).max())
    out = []
    for i in range(n):
        a, b = p[i - 1] if (i > 0 or closed) else p[i], p[(i + 1) % n] if (i < n - 1 or closed) else p[i]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) + 1e-9
        out.append((p[i][0] - dy / L * sig[i], p[i][1] + dx / L * sig[i]))
    return out


def poly_mask(shape, pts):
    m = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(m).polygon([tuple(q) for q in pts], fill=255)
    return np.asarray(m) > 127


# ----------------------------------------------------------------------------- the painter

class Painter:
    def __init__(self, layout):
        self.L = layout
        W, H = layout.get("size", [2048, 1536])
        self.W, self.H = W, H
        self.w, self.h = W * SS, H * SS
        self.rng = np.random.default_rng(layout.get("seed", 7))
        pal = dict(PALETTE, **layout.get("palette", {}))
        self.pal = {k: hexrgb(v) for k, v in pal.items()}
        shape = (self.h, self.w)
        self.mult = np.ones(shape + (3,), np.float32)  # watercolour washes, multiplied onto the paper
        self.inkimg = Image.new("L", (self.w, self.h), 0)
        self.ink = ImageDraw.Draw(self.inkimg)
        self.height = np.zeros(shape, np.float32)
        self.landmask = np.ones(shape, bool) if layout.get("background", "land") == "land" else np.zeros(shape, bool)

    # -- helpers
    def P(self, uv):
        return (uv[0] * self.w, uv[1] * self.h)

    def U(self, f):  # a fraction of the image height, in supersampled px
        return f * self.h

    def shape_pts(self, item, closed=True, rough_default=0.0, smooth=2):
        pts = [self.P(q) for q in item.get("poly") or item.get("path")]
        rough = item.get("rough", rough_default)
        if rough:
            pts = fractal(pts, closed, rough, self.rng, depth=3)
        pts = chaikin(pts, closed, smooth)
        return wobble(pts, closed, self.U(0.0012), self.rng, step=4 * SS, wave=40 * SS)

    def wash(self, mask, rgb, alpha, edge=0.35, blur=1.5):
        m = mask.astype(np.float32)
        soft = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur * SS)),
                          np.float32) / 255
        wide = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9 * SS)),
                          np.float32) / 255
        rim = np.clip(soft - wide, 0, 1) * 2  # watercolour pools at the edge of a wash
        a = np.clip(soft * alpha * (0.75 + 0.5 * self.grain) + rim * edge * alpha, 0, 1)
        t = np.clip(rgb / 235.0, 0, 1)
        self.mult *= 1 - a[..., None] * (1 - t)

    def line(self, pts, width, fill=255):
        if len(pts) > 1:
            self.ink.line([tuple(map(float, q)) for q in pts], fill=fill, width=max(1, int(round(width))), joint="curve")

    def erase(self, pts):
        self.ink.polygon([tuple(q) for q in pts], fill=0)

    def lw(self, f=1.0):
        return max(1, int(round(1.6 * SS * f * self.H / 1536)))

    # -- layers
    def paper(self):
        rng = self.rng
        self.grain = value_noise((self.h, self.w), 6, rng, 5)
        base = self.pal["paper"]
        n2 = value_noise((self.h, self.w), 2, rng, 3)
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        r = np.sqrt(((xx / self.w - 0.5) / 0.5) ** 2 + ((yy / self.h - 0.5) / 0.5) ** 2)
        vign = np.clip((r - 0.55) / 0.9, 0, 1) ** 1.5
        shade = 1 - 0.10 * (self.grain - 0.5) - 0.12 * (n2 - 0.5) - 0.38 * vign
        self.paperrgb = base[None, None, :] * shade[..., None]
        # stains: a few soft tea rings and blotches
        st = np.zeros((self.h, self.w), np.float32)
        for _ in range(int(rng.integers(4, 8))):
            cx, cy, rad = rng.random() * self.w, rng.random() * self.h, (0.04 + rng.random() * 0.12) * self.h
            d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / rad
            ring = np.exp(-((d - 1) / 0.03) ** 2) * 0.18 + np.clip(1 - d, 0, 1) ** 0.7 * 0.3
            st += ring * (0.4 + 0.6 * rng.random())
        st *= np.clip(n2 * 1.8 - 0.4, 0, 1.4) * (0.5 + self.grain)
        tea = hexrgb("#9b7442")
        a = np.clip(st * 0.22, 0, 0.35)[..., None]
        self.paperrgb = self.paperrgb * (1 - a) + tea * a * 0.95
        del xx, yy

    def build_land(self):
        if self.L.get("background", "land") == "sea":
            for it in self.L.get("land", []):
                pts = self.shape_pts(it, True, 0.5)
                it["_pts"] = pts
                self.landmask |= poly_mask((self.h, self.w), pts)
        self.watermask = np.zeros((self.h, self.w), bool)
        for it in self.L.get("water", []):
            pts = self.shape_pts(it, True, 0.3)
            it["_pts"] = pts
            self.watermask |= poly_mask((self.h, self.w), pts)
        self.wet = (~self.landmask) | self.watermask

    def sea(self):
        wet = self.wet
        if not wet.any():
            return
        self.wash(wet, self.pal["sea"], 0.55, edge=0.5, blur=2)
        dist = ndimage.distance_transform_edt(wet).astype(np.float32)
        # engraved ripple lines following the shore
        ripple = np.zeros_like(dist)
        for k, d in enumerate([5, 11, 19, 30, 44]):
            dd = d * SS * self.H / 1536
            ripple = np.maximum(ripple, np.clip(1 - np.abs(dist - dd) / (0.6 * SS), 0, 1) * (1 - k * 0.17))
        # broken up: ripple lines fade in and out along the shore
        ripple *= np.clip(self.grain * 2.2 - 0.35, 0, 1)
        # stipple dots, dense near the shore
        p = 0.012 * np.exp(-dist / (40 * SS)) + 0.0012
        dots = (self.rng.random(dist.shape) < p * 0.35) & wet
        dots = ndimage.binary_dilation(dots, iterations=1)
        inkarr = np.asarray(self.inkimg, np.float32)
        inkarr = np.maximum(inkarr, ripple * 200 * wet)
        inkarr = np.maximum(inkarr, dots * 150)
        self.inkimg = Image.fromarray(inkarr.astype(np.uint8))
        self.ink = ImageDraw.Draw(self.inkimg)

    def land_tint(self):
        land = self.landmask & ~self.watermask
        if self.L.get("background", "land") == "sea":
            self.wash(land, self.pal["land"], 0.35, edge=0.6)
        self.height += land * 0.25

    def regions(self):
        for it in self.L.get("regions", []):
            pts = self.shape_pts(it, True, 0.1, smooth=it.get("smooth", 3))
            m = poly_mask((self.h, self.w), pts) & self.landmask
            self.wash(m, hexrgb(it.get("tint", "#8a9a5a")), it.get("alpha", 0.45), edge=0.6, blur=4)
            b = it.get("border", "dashed")
            if b == "solid":
                self.line(pts + [pts[0]], self.lw(0.8), 200)
            elif b == "dashed":
                d = densify(pts + [pts[0]], False, 3 * SS)
                seg = 6
                for i in range(0, len(d) - seg, seg * 2):
                    self.line(d[i:i + seg + 1], self.lw(0.7), 190)

    def deserts(self):
        for it in self.L.get("deserts", []):
            pts = self.shape_pts(it, True, 0.2)
            m = poly_mask((self.h, self.w), pts) & self.landmask
            if it.get("hole"):
                m &= ~poly_mask((self.h, self.w), self.shape_pts({"poly": it["hole"], "rough": it.get("rough", 0.3)}, True))
            self.wash(m, hexrgb(it.get("tint", "#d9b877")), 0.3)
            dots = (self.rng.random(m.shape) < 0.004) & m
            dots = ndimage.binary_dilation(dots, iterations=1)
            arr = np.maximum(np.asarray(self.inkimg, np.float32), dots * 140)
            self.inkimg = Image.fromarray(arr.astype(np.uint8))
            self.ink = ImageDraw.Draw(self.inkimg)

    def scatter(self, m, spacing, jitter=0.45):
        """Jittered grid points inside a mask, sorted back to front."""
        ys, xs = np.nonzero(m)
        if len(xs) == 0:
            return []
        pts = []
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        sy = spacing * 0.75
        row = 0
        y = y0 + sy / 2
        while y < y1:
            x = x0 + (spacing / 2 if row % 2 else 0) + spacing / 2
            while x < x1:
                px = x + (self.rng.random() - 0.5) * spacing * jitter * 2
                py = y + (self.rng.random() - 0.5) * sy * jitter * 2
                ix, iy = int(px), int(py)
                if 0 <= iy < self.h and 0 <= ix < self.w and m[iy, ix]:
                    pts.append((px, py))
                x += spacing
            y += sy
            row += 1
        pts.sort(key=lambda p: p[1])
        return pts

    def fields(self):
        for it in self.L.get("fields", []):
            pts = self.shape_pts(it, True, 0.2)
            m = poly_mask((self.h, self.w), pts) & self.landmask
            col = hexrgb(it.get("color", "#7f9a4c"))
            self.wash(m, col, 0.22)
            g = it.get("glyph", "grass")
            sp = self.U(0.016)
            for (x, y) in self.scatter(m, sp, 0.5):
                s = sp * 0.35
                if g == "flower":
                    r = s * 0.45
                    self.ink.ellipse([x - r, y - r, x + r, y + r], outline=200, width=self.lw(0.5))
                    self.line([(x, y + r), (x, y + s * 1.3)], self.lw(0.5), 180)
                    mm = np.zeros((self.h, self.w), bool)
                    yy, xx = int(y), int(x)
                    rr = int(r * 1.1)
                    mm[max(0, yy - rr):yy + rr, max(0, xx - rr):xx + rr] = True
                    self._spot(x, y, r * 1.2, col, 0.85)
                elif g == "crop":
                    self.line([(x - s, y), (x + s, y)], self.lw(0.5), 150)
                else:
                    for dx in (-0.6, 0, 0.6):
                        self.line([(x + dx * s * 0.6, y), (x + dx * s, y - s)], self.lw(0.45), 170)

    def _spot(self, x, y, r, rgb, alpha):
        x0, y0, x1, y1 = int(max(0, x - r)), int(max(0, y - r)), int(min(self.w, x + r + 1)), int(min(self.h, y + r + 1))
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = np.sqrt((xx - x) ** 2 + (yy - y) ** 2) / r
        a = np.clip(1 - d, 0, 1) ** 0.6 * alpha
        t = np.clip(rgb / 235.0, 0, 1)
        self.mult[y0:y1, x0:x1] *= 1 - a[..., None] * (1 - t)

    def rivers(self):
        for it in self.L.get("rivers", []):
            pts = [self.P(q) for q in it["path"]]
            pts = chaikin(fractal(pts, False, it.get("rough", 0.15), self.rng, 3), False, 3)
            pts = wobble(pts, False, self.U(0.001), self.rng, step=3 * SS)
            wmax = self.U(it.get("width", 0.004))
            n = len(pts)
            for i in range(n - 1):
                t = i / max(1, n - 2)
                w = max(self.lw(0.5), wmax * 0.45 * (0.3 + 0.7 * t))
                self.line([pts[i], pts[i + 1]], w, 190)
            # a pale water channel down the middle of the wider part
            m = Image.new("L", (self.w, self.h), 0)
            ImageDraw.Draw(m).line(pts, fill=255, width=int(wmax * 1.6), joint="curve")
            self.wash(np.asarray(m) > 127, self.pal["water"], 0.45, edge=0.2, blur=1)
            it["_pts"] = pts

    def coasts(self):
        for group in ("land", "water"):
            for it in self.L.get(group, []):
                pts = it.get("_pts")
                if pts:
                    self.line(pts + [pts[0]], self.lw(1.5), 235)

    def hills(self):
        for it in self.L.get("hills", []):
            pts = self.shape_pts(it, True, 0.2)
            m = poly_mask((self.h, self.w), pts) & self.landmask & ~self.watermask
            sp = self.U(0.034) / it.get("density", 1.0)
            for (x, y) in self.scatter(m, sp, 0.4):
                self.hill(x, y, sp * (0.5 + 0.25 * self.rng.random()))

    def hill(self, x, y, s):
        n = 14
        arc = [(x - s + 2 * s * i / n, y - s * 0.55 * math.sin(math.pi * i / n) ** 0.8) for i in range(n + 1)]
        arc = wobble(arc, False, s * 0.03, self.rng, step=2 * SS, wave=15 * SS)
        self.erase(arc + [(x + s, y + 1), (x - s, y + 1)])
        self.line(arc, self.lw(0.9), 230)
        for k in range(4):  # hachures on the shaded (right) flank
            t = 0.55 + 0.11 * k
            px = x - s + 2 * s * t
            py = y - s * 0.55 * math.sin(math.pi * t) ** 0.8
            self.line([(px, py + s * 0.08), (px + s * 0.05, py + s * 0.38 * (1 - k * 0.15))], self.lw(0.55), 180)
        self._bump(x, y - s * 0.2, s * 1.4, 0.35)

    def _bump(self, x, y, r, amt):
        x0, y0, x1, y1 = int(max(0, x - r)), int(max(0, y - r)), int(min(self.w, x + r + 1)), int(min(self.h, y + r + 1))
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d2 = ((xx - x) ** 2 + (yy - y) ** 2) / (r * r)
        self.height[y0:y1, x0:x1] = np.maximum(self.height[y0:y1, x0:x1], 0.25 + amt * np.exp(-d2 * 2.5))

    def mountains(self):
        for it in self.L.get("mountains", []):
            pts = densify([self.P(q) for q in it["path"]], False, self.U(it.get("size", 0.05)) * 0.7)
            for i, (x, y) in enumerate(sorted(pts, key=lambda p: p[1])):
                s = self.U(it.get("size", 0.05)) * (0.75 + 0.5 * self.rng.random())
                self.peak(x + (self.rng.random() - 0.5) * s * 0.3, y + (self.rng.random() - 0.5) * s * 0.2, s)

    def peak(self, x, y, s):
        top = (x + (self.rng.random() - 0.5) * s * 0.15, y - s * 0.9)
        left, right = (x - s * 0.6, y), (x + s * 0.6, y)
        lft = wobble([left, top], False, s * 0.025, self.rng, step=2 * SS, wave=12 * SS)
        rgt = wobble([top, right], False, s * 0.025, self.rng, step=2 * SS, wave=12 * SS)
        self.erase([left, top, right])
        self.line(lft + rgt, self.lw(1.0), 235)
        for k in range(1, 7):  # shade the east face
            t = k / 7
            a = (top[0] + (right[0] - top[0]) * t, top[1] + (right[1] - top[1]) * t)
            b = (top[0] + (x - top[0]) * t * 0.9 + s * 0.04, top[1] + (y - top[1]) * t)
            self.line([a, b], self.lw(0.5), 170)
        self._bump(x, y - s * 0.35, s * 0.9, 0.75)

    def forests(self):
        for it in self.L.get("forests", []):
            pts = self.shape_pts(it, True, 0.45)
            m = poly_mask((self.h, self.w), pts) & self.landmask & ~self.watermask
            self.wash(m, hexrgb(it.get("tint", "#6f8a4a")), 0.16, edge=0.15, blur=7)
            sp = self.U(0.03) / it.get("density", 1.0)
            kind = it.get("kind", "round")
            for (x, y) in self.scatter(m, sp, 0.45):
                if self.grain[int(y), int(x)] < 0.42 and self.rng.random() < 0.7:
                    continue
                k = kind if kind != "mixed" else ("pine" if self.rng.random() < 0.4 else "round")
                self.tree(x, y, sp * (0.55 + 0.2 * self.rng.random()), k)
                self._bump(x, y, sp, 0.12)

    def tree(self, x, y, s, kind="round"):
        if kind == "pine":
            tri = [(x - s * 0.38, y - s * 0.15), (x, y - s * 1.25), (x + s * 0.38, y - s * 0.15)]
            tri = wobble(tri, True, s * 0.02, self.rng, step=2 * SS, wave=8 * SS)
            self.erase(tri)
            self.line(tri + [tri[0]], self.lw(0.7), 225)
            self.line([(x, y - s * 0.15), (x, y + s * 0.1)], self.lw(0.7), 225)
            for k in range(1, 4):
                yy = y - s * 0.15 - s * 1.1 * k / 4
                self.line([(x + s * 0.05, yy), (x + s * 0.38 * (1 - k / 4.5), yy + s * 0.12)], self.lw(0.45), 160)
            return
        r = s * 0.45
        cy = y - s * 0.6
        n = 18
        crown = []
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = r * (1 + 0.12 * math.sin(a * 5 + self.rng.random()))
            crown.append((x + rr * math.cos(a), cy + rr * 0.9 * math.sin(a)))
        crown = wobble(crown, True, r * 0.05, self.rng, step=2 * SS, wave=10 * SS)
        self.erase(crown + [crown[0]])
        self.line(crown + [crown[0]], self.lw(0.7), 225)
        self.line([(x, cy + r * 0.85), (x, y + s * 0.05)], self.lw(0.75), 225)
        for k in range(3):
            a = 0.1 + k * 0.45
            px, py = x + r * 0.55 * math.cos(a), cy + r * 0.5 * math.sin(a)
            self.line([(px - r * 0.15, py - r * 0.1), (px + r * 0.15, py + r * 0.1)], self.lw(0.45), 160)

    def decor(self):
        """Sparse grass tufts and lone trees over open land, so empty country does not look blank."""
        d = self.L.get("decor")
        if not d:
            return
        free = self.landmask & ~self.wet
        mg = int(self.U(0.06))
        free[:mg], free[-mg:], free[:, :mg], free[:, -mg:] = False, False, False, False
        for it in self.L.get("forests", []) + self.L.get("hills", []):
            free &= ~poly_mask((self.h, self.w), [self.P(q) for q in it["poly"]])
        ink = np.asarray(self.inkimg)
        sp = self.U(0.03)
        for (x, y) in self.scatter(free, sp, 0.5):
            ix, iy = int(x), int(y)
            if ink[max(0, iy - 12):iy + 12, max(0, ix - 12):ix + 12].max() > 60:
                continue  # keep clear of lines already drawn
            r = self.rng.random()
            if r < d.get("trees", 0.0) * 0.08:
                self.tree(x, y, sp * 0.6, "round" if self.rng.random() < 0.7 else "pine")
            elif r < d.get("tufts", 0.0) * 0.35:
                s_ = sp * 0.18
                for k in (-1, 0, 1):
                    self.line([(x + k * s_ * 0.5, y), (x + k * s_ * 0.9, y - s_ * (1.2 - 0.3 * abs(k)))], self.lw(0.45), 150)

    def roads(self):
        for it in self.L.get("roads", []):
            pts = [self.P(q) for q in it["path"]]
            pts = chaikin(pts, False, 3)
            pts = wobble(pts, False, self.U(0.0012), self.rng, step=3 * SS, wave=50 * SS)
            st = it.get("style", "dashed")
            w = self.U(it.get("width", 0.006))
            if st == "band":
                m = Image.new("L", (self.w, self.h), 0)
                ImageDraw.Draw(m).line(pts, fill=255, width=int(w), joint="curve")
                mm = np.asarray(m) > 127
                self.wash(mm, hexrgb(it.get("color", "#d8b23a")), 0.75, edge=0.3, blur=0.8)
                # edges: offset lines either side
                for side in (-1, 1):
                    off = []
                    for i in range(len(pts)):
                        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
                        dx, dy = b[0] - a[0], b[1] - a[1]
                        L = math.hypot(dx, dy) + 1e-9
                        off.append((pts[i][0] - dy / L * w / 2 * side, pts[i][1] + dx / L * w / 2 * side))
                    self.line(off, self.lw(0.6), 200)
                # brick ticks across the band
                d = densify(pts, False, w * 0.9)
                for i in range(1, len(d) - 1):
                    a, b = d[i - 1], d[i + 1]
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    L = math.hypot(dx, dy) + 1e-9
                    nx, ny = -dy / L * w / 2, dx / L * w / 2
                    self.line([(d[i][0] - nx, d[i][1] - ny), (d[i][0] + nx, d[i][1] + ny)], self.lw(0.4), 130)
            elif st == "solid":
                self.line(pts, self.lw(0.9), 210)
            else:
                d = densify(pts, False, 2 * SS)
                on = 7 if st == "dashed" else 1
                off = 5 if st == "dashed" else 4
                i = 0
                while i < len(d) - 1:
                    if st == "dotted":
                        x, y = d[i]
                        r = self.lw(0.6)
                        self.ink.ellipse([x - r, y - r, x + r, y + r], fill=210)
                    else:
                        self.line(d[i:i + on + 1], self.lw(0.85), 210)
                    i += on + off

    # -- place glyphs
    def glyph(self, g, x, y, s):
        lw, L = self.lw(0.85), self.line
        if g == "dot":
            r = s * 0.22
            self.ink.ellipse([x - r, y - r, x + r, y + r], outline=235, width=lw)
            r2 = r * 0.45
            self.ink.ellipse([x - r2, y - r2, x + r2, y + r2], fill=235)
        elif g == "town":
            for dx, dy, k in ((-0.32, 0.05, 0.8), (0.0, -0.1, 1.0), (0.3, 0.08, 0.75)):
                self.house(x + dx * s, y + dy * s, s * 0.42 * k)
        elif g == "house":
            self.house(x, y, s * 0.6)
        elif g == "city":
            r = s * 0.55
            self.erase([(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)])
            self.ink.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], outline=235, width=lw)
            for k in range(8):
                a = 2 * math.pi * k / 8
                tx, ty = x + r * math.cos(a), y + r * 0.8 * math.sin(a)
                self.ink.rectangle([tx - s * 0.06, ty - s * 0.12, tx + s * 0.06, ty + s * 0.02], fill=235)
            for dx in (-0.2, 0.0, 0.2):
                self.tower(x + dx * s, y + s * 0.2, s * 0.35, spire=True)
        elif g in ("castle", "palace"):
            k = 1.0 if g == "castle" else 1.2
            b = [(x - s * 0.45 * k, y), (x + s * 0.45 * k, y), (x + s * 0.45 * k, y - s * 0.4), (x - s * 0.45 * k, y - s * 0.4)]
            self.erase(b)
            L(b + [b[0]], lw, 235)
            for i in range(5):  # crenellations
                cx = x - s * 0.45 * k + (i + 0.5) * s * 0.18 * k
                if i % 2 == 0:
                    self.ink.rectangle([cx - s * 0.045, y - s * 0.48, cx + s * 0.045, y - s * 0.4], fill=235)
            self.tower(x - s * 0.5 * k, y, s * 0.75, spire=(g == "palace"))
            self.tower(x + s * 0.5 * k, y, s * 0.75, spire=(g == "palace"))
            if g == "palace":
                self.tower(x, y - s * 0.38, s * 0.55, spire=True)
            self.ink.chord([x - s * 0.1, y - s * 0.25, x + s * 0.1, y - s * 0.05], 180, 360, fill=235)
            self.ink.rectangle([x - s * 0.1, y - s * 0.15, x + s * 0.1, y], fill=235)
        elif g == "tower":
            self.tower(x, y, s * 0.9, spire=False)
        elif g in ("cave", "hole"):
            r = s * 0.35
            if g == "hole":
                self.ink.ellipse([x - r, y - r * 0.55, x + r, y + r * 0.55], fill=235)
                for k in range(6):
                    a = math.pi + k * math.pi / 5
                    L([(x + r * 1.1 * math.cos(a), y + r * 0.6 * math.sin(a) - 1),
                       (x + r * 1.45 * math.cos(a), y + r * 0.85 * math.sin(a) - 1)], self.lw(0.5), 180)
            else:
                self.hill(x, y + s * 0.1, s * 0.7)
                self.ink.chord([x - r * 0.5, y - r * 0.6, x + r * 0.5, y + r * 0.5], 180, 360, fill=235)
        elif g == "door":
            w, h = s * 0.28, s * 0.55
            self.erase([(x - w, y), (x + w, y), (x + w, y - h), (x - w, y - h)])
            self.ink.rectangle([x - w, y - h * 0.7, x + w, y], outline=235, width=lw)
            self.ink.arc([x - w, y - h, x + w, y - h * 0.4], 180, 360, fill=235, width=lw)
            self.ink.ellipse([x + w * 0.4, y - h * 0.35, x + w * 0.6, y - h * 0.25], fill=235)
        elif g == "tree":
            self.tree(x, y, s * 1.1, "round")
        elif g == "mushroom":
            r = s * 0.42
            cap = [(x - r + 2 * r * i / 16, y - s * 0.35 - r * 0.8 * math.sin(math.pi * i / 16)) for i in range(17)]
            self.erase(cap + [(x + r, y - s * 0.3), (x + r * 0.25, y), (x - r * 0.25, y), (x - r, y - s * 0.3)])
            L(cap + [cap[0]], lw, 235)
            L([(x - r * 0.22, y - s * 0.35), (x - r * 0.25, y), (x + r * 0.25, y), (x + r * 0.22, y - s * 0.35)], lw, 235)
            for dx, dy in ((-0.45, -0.55), (0.1, -0.85), (0.5, -0.5)):
                rr = r * 0.12
                self.ink.ellipse([x + dx * r - rr, y - s * 0.35 + dy * r * 0.8 - rr, x + dx * r + rr,
                                  y - s * 0.35 + dy * r * 0.8 + rr], outline=200, width=self.lw(0.5))
        elif g == "table":
            w = s * 0.55
            self.erase([(x - w, y - s * 0.35), (x + w, y - s * 0.35), (x + w, y), (x - w, y)])
            self.ink.ellipse([x - w, y - s * 0.42, x + w, y - s * 0.22], outline=235, width=lw)
            L([(x - w * 0.8, y - s * 0.3), (x - w * 0.8, y)], lw, 235)
            L([(x + w * 0.8, y - s * 0.3), (x + w * 0.8, y)], lw, 235)
            for dx in (-0.45, 0.0, 0.45):  # teacups
                cx = x + dx * w
                self.ink.rectangle([cx - s * 0.06, y - s * 0.46, cx + s * 0.06, y - s * 0.36], fill=235)
        elif g == "tent":
            tri = [(x - s * 0.4, y), (x, y - s * 0.6), (x + s * 0.4, y)]
            self.erase(tri)
            L(tri + [tri[0]], lw, 235)
            L([(x, y - s * 0.6), (x, y)], self.lw(0.5), 200)
        elif g == "gate":
            self.tower(x - s * 0.3, y, s * 0.7)
            self.tower(x + s * 0.3, y, s * 0.7)
            self.ink.arc([x - s * 0.22, y - s * 0.5, x + s * 0.22, y - s * 0.05], 180, 360, fill=235, width=lw)
        elif g == "star":
            pts = []
            for k in range(10):
                a = -math.pi / 2 + k * math.pi / 5
                rr = s * (0.32 if k % 2 == 0 else 0.13)
                pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
            self.ink.polygon(pts, fill=235)
        elif g == "cross":
            r = s * 0.25
            L([(x - r, y - r), (x + r, y + r)], self.lw(1.3), 235)
            L([(x - r, y + r), (x + r, y - r)], self.lw(1.3), 235)

    def house(self, x, y, s):
        w, h = s * 0.5, s * 0.45
        body = [(x - w, y), (x + w, y), (x + w, y - h), (x, y - h - s * 0.4), (x - w, y - h)]
        self.erase(body)
        self.line(body + [body[0]], self.lw(0.8), 235)
        self.line([(x - w, y - h), (x + w, y - h)], self.lw(0.6), 210)
        self.ink.rectangle([x - w * 0.2, y - h * 0.55, x + w * 0.2, y], fill=220)
        for k in range(3):
            self.line([(x + w * 0.3 + k * w * 0.2, y - h - s * 0.4 * (1 - (0.3 + k * 0.2))), (x + w * 0.3 + k * w * 0.2, y - h)],
                      self.lw(0.4), 150)

    def tower(self, x, y, s, spire=False):
        w = s * 0.16
        b = [(x - w, y), (x + w, y), (x + w, y - s * 0.75), (x - w, y - s * 0.75)]
        self.erase(b)
        self.line(b + [b[0]], self.lw(0.75), 235)
        if spire:
            sp = [(x - w * 1.2, y - s * 0.75), (x, y - s * 1.15), (x + w * 1.2, y - s * 0.75)]
            self.erase(sp)
            self.line(sp + [sp[0]], self.lw(0.7), 235)
            self.line([(x, y - s * 1.15), (x, y - s * 1.3)], self.lw(0.5), 220)
        else:
            for i in range(3):
                cx = x - w + i * w
                self.ink.rectangle([cx - w * 0.25, y - s * 0.86, cx + w * 0.25, y - s * 0.75], fill=235)
        self.ink.rectangle([x - w * 0.25, y - s * 0.55, x + w * 0.25, y - s * 0.45], fill=200)

    # -- lettering
    def font(self, size, italic=False):
        return ImageFont.truetype(FONT_ITA if italic else FONT_REG, max(6, int(size)))

    def text(self, txt, x, y, size, angle=0.0, italic=False, spacing=0.0, alpha=1.0, anchor="mm", halo=True):
        f = self.font(size, italic)
        sp = spacing * size
        widths = [f.getlength(ch) for ch in txt]
        tw = sum(widths) + sp * max(0, len(txt) - 1)
        asc, desc = f.getmetrics()
        th = asc + desc
        pad = int(size * 0.6)
        im = Image.new("L", (int(tw) + 2 * pad, th + 2 * pad), 0)
        d = ImageDraw.Draw(im)
        cx = pad
        for ch, wch in zip(txt, widths):
            d.text((cx, pad), ch, font=f, fill=int(255 * alpha))
            cx += wch + sp
        if halo:
            hal = im.filter(ImageFilter.MaxFilter(5 if size > 30 else 3)).filter(ImageFilter.GaussianBlur(size * 0.12))
        if angle:
            im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
            if halo:
                hal = hal.rotate(angle, resample=Image.BICUBIC, expand=True)
        ax = {"l": 0.0, "m": 0.5, "r": 1.0}[anchor[0]]
        ay = {"t": 0.0, "m": 0.5, "b": 1.0}[anchor[1]]
        if angle == 0:
            ox = x - pad - tw * ax
            oy = y - pad - th * ay
        else:
            ox, oy = x - im.width / 2, y - im.height / 2
        ox, oy = int(ox), int(oy)
        if halo:  # knock the ink and colour back under the letters so they stay legible
            self._halo.append((hal, ox, oy))
        cur = self.inkimg.crop((ox, oy, ox + im.width, oy + im.height))
        self._letters.append((im, ox, oy))
        return tw, th

    def place_labels(self):
        for p in self.L.get("places", []):
            x, y = self.P((p["u"], p["v"]))
            s = self.U(0.045) * p.get("size", 1.0)
            self.glyph(p.get("glyph", "dot"), x, y, s)
            lab = p.get("label")
            if not lab:
                continue
            size = self.U(p.get("labelSize", 0.024))
            pos = p.get("labelPos", "right")
            gap = s * 0.45
            gy = y - s * 0.25 if p.get("glyph", "dot") not in ("dot", "star", "cross", "hole") else y
            if p.get("glyph", "dot") == "none":
                pos = p.get("labelPos", "center")
            lines = lab.split("\n")
            n = len(lines)
            for i, ln in enumerate(lines):
                dy = (i - (n - 1) / 2) * size * 1.05
                if pos == "right":
                    self.text(ln, x + gap, gy + dy, size, italic=p.get("italic", False), anchor="lm")
                elif pos == "left":
                    self.text(ln, x - gap, gy + dy, size, italic=p.get("italic", False), anchor="rm")
                elif pos == "above":
                    self.text(ln, x, y - s * 0.9 - (n - 1 - i) * size * 1.05, size, italic=p.get("italic", False), anchor="mb")
                elif pos == "center":
                    self.text(ln, x, y + dy, size, italic=p.get("italic", False), anchor="mm")
                else:
                    self.text(ln, x, y + s * 0.3 + i * size * 1.05, size, italic=p.get("italic", False), anchor="mt")

    def free_labels(self):
        for lb in self.L.get("labels", []):
            x, y = self.P((lb["u"], lb["v"]))
            self.text(lb["text"], x, y, self.U(lb.get("size", 0.035)), angle=lb.get("angle", 0), italic=lb.get("italic", False),
                      spacing=lb.get("spacing", 0.0), alpha=lb.get("alpha", 0.85), halo=lb.get("halo", False))

    def cartouche(self):
        t = self.L.get("title")
        if not t:
            return
        x, y = self.P((t["u"], t["v"]))
        size = self.U(t.get("size", 0.05))
        f = self.font(size)
        tw = f.getlength(t["text"])
        sub = t.get("sub")
        ssize = size * 0.42
        sw = self.font(ssize, True).getlength(sub) if sub else 0
        w = max(tw, sw) / 2 + size * 0.9
        h = size * (0.95 if not sub else 1.35)
        box = [(x - w, y - h), (x + w, y - h), (x + w, y + h), (x - w, y + h)]
        self.erase(box)
        self._cartouche = (int(x - w), int(y - h), int(x + w), int(y + h))
        self.ink.rectangle([x - w, y - h, x + w, y + h], outline=235, width=self.lw(1.4))
        g = size * 0.18
        self.ink.rectangle([x - w + g, y - h + g, x + w - g, y + h - g], outline=200, width=self.lw(0.6))
        for sx in (-1, 1):  # curled ends
            for sy in (-1, 1):
                cx, cy = x + sx * w, y + sy * h
                r = size * 0.32
                self.ink.arc([cx - r, cy - r, cx + r, cy + r], 0, 360, fill=220, width=self.lw(0.8))
                self.ink.ellipse([cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3], fill=220)
        ty = y - (size * 0.25 if sub else 0)
        self.text(t["text"], x, ty, size, anchor="mm", halo=False)
        if sub:
            self.text(sub, x, y + size * 0.62, ssize, italic=True, anchor="mm", halo=False)
            self.line([(x - w * 0.5, y + size * 0.3), (x + w * 0.5, y + size * 0.3)], self.lw(0.5), 180)

    def compass(self):
        c = self.L.get("compass")
        if not c:
            return
        x, y = self.P((c["u"], c["v"]))
        r = self.U(c.get("r", 0.07))
        rot = math.radians(c.get("angle", 0))
        self.erase([(x - r * 1.1, y - r * 1.1), (x + r * 1.1, y - r * 1.1), (x + r * 1.1, y + r * 1.1), (x - r * 1.1, y + r * 1.1)])
        self.ink.ellipse([x - r * 0.72, y - r * 0.72, x + r * 0.72, y + r * 0.72], outline=220, width=self.lw(0.8))
        self.ink.ellipse([x - r * 0.66, y - r * 0.66, x + r * 0.66, y + r * 0.66], outline=180, width=self.lw(0.5))
        for k in range(32):
            a = rot + 2 * math.pi * k / 32
            l0 = 0.66 if k % 4 else 0.58
            self.line([(x + r * l0 * math.sin(a), y - r * l0 * math.cos(a)), (x + r * 0.72 * math.sin(a), y - r * 0.72 * math.cos(a))],
                      self.lw(0.4), 180)
        for k in range(8):
            a = rot + k * math.pi / 4
            ln = r * (1.0 if k % 2 == 0 else 0.55)
            wd = r * (0.13 if k % 2 == 0 else 0.1)
            tip = (x + ln * math.sin(a), y - ln * math.cos(a))
            l = (x + wd * math.sin(a - math.pi / 2), y - wd * math.cos(a - math.pi / 2))
            rr = (x + wd * math.sin(a + math.pi / 2), y - wd * math.cos(a + math.pi / 2))
            self.erase([l, tip, rr, (x, y)])
            self.ink.polygon([(x, y), tip, l], fill=230)
            self.line([(x, y), tip, rr, (x, y)], self.lw(0.6), 230)
        size = r * 0.42
        a = rot
        self.text("N", x + r * 1.18 * math.sin(a), y - r * 1.18 * math.cos(a), size, halo=False)

    def border(self):
        if not self.L.get("border", True):
            return
        m = self.U(0.022)
        g = self.U(0.012)
        self.ink.rectangle([m, m, self.w - m, self.h - m], outline=235, width=self.lw(1.6))
        self.ink.rectangle([m + g, m + g, self.w - m - g, self.h - m - g], outline=220, width=self.lw(0.7))
        # alternating scale-bar blocks between the two rules
        step = self.U(0.05)
        for side in range(4):
            length = self.w - 2 * m if side % 2 == 0 else self.h - 2 * m
            n = int(length / step)
            for i in range(n):
                if i % 2:
                    continue
                a0, a1 = m + i * step, m + min((i + 1) * step, length)
                if side == 0:
                    box = [a0, m, a1, m + g]
                elif side == 1:
                    box = [self.w - m - g, a0, self.w - m, a1]
                elif side == 2:
                    box = [a0, self.h - m - g, a1, self.h - m]
                else:
                    box = [m, a0, m + g, a1]
                self.ink.rectangle(box, fill=150)

    # -- compose
    def render(self):
        self._halo, self._letters, self._cartouche = [], [], None
        self.paper()
        self.build_land()
        self.land_tint()
        self.sea()
        self.regions()
        self.deserts()
        self.fields()
        self.rivers()
        self.coasts()
        self.hills()
        self.mountains()
        self.forests()
        self.decor()
        self.roads()
        self.place_labels()
        self.free_labels()
        self.cartouche()
        self.compass()
        self.border()
        ink = np.asarray(self.inkimg, np.float32) / 255
        # halos: clear ink and colour under place labels
        if self._halo:
            hl = Image.new("L", (self.w, self.h), 0)
            for im, ox, oy in self._halo:
                hl.paste(255, (ox, oy), im)
            hm = np.asarray(hl.filter(ImageFilter.GaussianBlur(1.2 * SS)), np.float32) / 255
            ink = ink * (1 - hm * 0.9)
            self.mult = 1 - (1 - self.mult) * (1 - hm[..., None] * 0.5)
        if self._cartouche:
            x0, y0, x1, y1 = self._cartouche
            sub = self.mult[max(0, y0):y1, max(0, x0):x1]
            self.mult[max(0, y0):y1, max(0, x0):x1] = 1 - (1 - sub) * 0.1
        let = Image.new("L", (self.w, self.h), 0)
        for im, ox, oy in self._letters:
            let.paste(im, (ox, oy), im)
        ink = np.maximum(ink, np.asarray(let, np.float32) / 255)
        # uneven ink: thin where the grain is high, a slight bleed
        inkb = np.asarray(Image.fromarray((ink * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6 * SS)), np.float32) / 255
        ink = np.clip(0.75 * ink + 0.35 * inkb, 0, 1) * (0.78 + 0.3 * self.grain)
        ink = np.clip(ink, 0, 1)
        paper = self.paperrgb
        img = paper * self.mult
        img = img * (1 - ink[..., None]) + self.pal["ink"] * ink[..., None]
        # a final darkening at the very edge, as if handled
        out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((self.W, self.H), Image.LANCZOS)
        return out

    def height_map(self):
        hgt = self.height.copy()
        hgt[self.wet] = 0
        im = Image.fromarray((np.clip(hgt, 0, 1) * 255).astype(np.uint8))
        sc = 1024 / max(self.W, self.H)
        im = im.resize((max(1, round(self.W * sc)), max(1, round(self.H * sc))), Image.BILINEAR)
        return im.filter(ImageFilter.GaussianBlur(12))


# ----------------------------------------------------------------------------- debug overlay

def overlay(map_json, view_id, out):
    m = json.load(open(map_json, encoding="utf-8"))
    view = next(v for v in m["views"] if v["id"] == view_id)
    content = os.path.join(ROOT, "content")
    im = Image.open(os.path.join(content, view["image"])).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT_REG, max(12, H // 70))
    fb = ImageFont.truetype(FONT_REG, max(14, H // 45))
    for p in m["places"]:
        if p["view"] != view_id:
            continue
        x, y = p["u"] * W, p["v"] * H
        r = max(5, H // 160)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(220, 30, 30), outline=(255, 255, 255), width=2)
        d.text((x + r + 3, y), p["id"], font=f, fill=(200, 0, 0), anchor="lm", stroke_width=2, stroke_fill=(255, 255, 255))
    d.rectangle([0, 0, W, H // 30 + 8], fill=(0, 0, 0))
    d.text((8, 4), f"map overlay (not headset): {m['book']} / {view_id}", font=fb, fill=(255, 255, 0))
    im.save(out)


def main(argv):
    if argv[:1] == ["--overlay"]:
        overlay(argv[1], argv[2], argv[3])
        return 0
    if len(argv) < 2:
        print(__doc__)
        return 2
    layout = json.load(open(argv[0], encoding="utf-8"))
    p = Painter(layout)
    img = p.render()
    img.save(argv[1], quality=88, optimize=True)
    if "--height" in argv:
        p.height_map().save(argv[argv.index("--height") + 1], optimize=True)
    if "--preview" in argv:
        sm = img.copy()
        sm.thumbnail((1200, 1200))
        sm.save(argv[argv.index("--preview") + 1], quality=85)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
