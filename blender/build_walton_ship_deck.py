"""
Fable scene room: The deck of Walton's ship among drifting ice (Frankenstein, Letter III) - walton-ship-deck.

"I write a few lines in haste to say that I am safe - and well advanced on my voyage."
"Our good ship ... the southern gales, which blow us speedily towards the northern regions" "We have already reached
a very high latitude; but it is the height of summer ... the floating sheets of ice that continually pass us,
indicating the dangers of the region towards which we are advancing" "No incidents have hitherto befallen us ... the
springing of a leak is an accident which experienced navigators scarcely remember to record"

A hired merchant ship of the 1790s, some 300 tons and three-masted, running north before a southern gale: the reader
stands at the starboard rail amidships on the scrubbed oak deck, facing forward over the bow. Every square sail is
set and filled ahead of the wind; tarred shrouds and ratlines run down to the channels beside the reader; the main
hatch with the ship's boat on its chocks, the brake pump by the mainmast (the leak), coils of rope, water casks, the
windlass and the bowsprit ahead; aft, the wheel and binnacle. Outside the rail, white floes and broken sheets of ice
drift past on a grey-blue sea, thicker toward the north; the low polar-summer sun stands a few degrees above the
horizon ahead-left, gilding the sails and the ice. The red ensign of the period (union without St Patrick's saltire)
flies from the mizzen peak.

No people, no pack ice closing in, no sledge, no Victor or creature, no steam or modern equipment.

Axes: metres, +Z up (deck at amidships z = 0, the sea at z = -2.6), +Y forward (north). The reader at the starboard
(+X) rail amidships.

Run headless:
  blender -b -P blender/build_walton_ship_deck.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_walton_ship_deck.py -- --cpu --render --samples 32 --res 1280 --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b4 as S
from scene_kit_b4 import (K, new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, lathe, tube, MB, anchor, sound, smoothstep, n2, srgb,
                          mb_box, mb_quad)

ARGS = S.setup("walton-ship-deck", 1796, "WaltonShipDeck", default_samples=48)
rng = random.Random(1796)
EYE = S.EYE
SEA = -2.6
L_AFT, L_FWD = -15.5, 16.5
SUN_DIR = Vector((-0.55, 0.83, 0.12)).normalized()      # toward the sun: north-north-west, ~7 degrees up
MASTS = {"fore": 8.8, "main": -2.2, "mizzen": -10.6}

# ----------------------------------------------------------------------------- hull lines
def hb(y):
    """half breadth at the rail."""
    if y >= 0: t = y / L_FWD; return 3.75 * max(0.0, 1 - t ** 2.2) ** 0.62
    t = -y / -L_AFT; return 3.75 * (1 - 0.30 * t ** 2.4)
def sheer(y):
    if y >= 0: return 0.85 * (y / L_FWD) ** 2
    return 0.6 * (y / L_AFT) ** 2
def deck_z(x, y): return sheer(y) + 0.10 * (1 - (x / max(0.3, hb(y))) ** 2)      # camber
BUL = 1.15                                                                         # bulwark height above deck

# ----------------------------------------------------------------------------- materials
def deck_mat(name):
    """Scrubbed oak deck: pale grey-brown planks about 0.2 m wide along the ship, butt joints staggered, black pitch
    in the seams, holystoned pale on the walkways, darker damp by the waterways."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0)); s = sep_xyz(nt, co, (-2200, 0))
    px = math_(nt, 'DIVIDE', s.outputs["X"], 0.2, (-2000, 200))
    seam_u = math_(nt, 'FRACT', px, None, (-1850, 200))
    seam = maprange(nt, seam_u, 0.0, 0.05, 1, 0, (-1700, 200))
    plank = node(nt, "ShaderNodeMath", (-1850, 400), operation='FLOOR'); nt.links.new(px, plank.inputs[0])
    off = math_(nt, 'MULTIPLY', plank.outputs[0], 2.37, (-1700, 400))
    py = math_(nt, 'DIVIDE', math_(nt, 'ADD', s.outputs["Y"], off, (-1600, 500)), 6.0, (-1500, 500))
    butt = maprange(nt, math_(nt, 'FRACT', py, None, (-1400, 500)), 0.0, 0.006, 1, 0, (-1250, 500))
    cv = node(nt, "ShaderNodeCombineXYZ", (-1650, 700)); nt.links.new(plank.outputs[0], cv.inputs["X"])
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1500, 700)); wn.noise_dimensions = '3D'; nt.links.new(cv.outputs[0], wn.inputs["Vector"])
    gm = node(nt, "ShaderNodeMapping", (-1900, -300)); gm.inputs["Scale"].default_value = (20.0, 0.6, 20.0); nt.links.new(co, gm.inputs["Vector"])
    grain = noise_(nt, gm.outputs["Vector"], 4.0, 6, 0.6, loc=(-1600, -300))
    tone = math_(nt, 'ADD', math_(nt, 'MULTIPLY', wn.outputs["Value"], 0.5), math_(nt, 'MULTIPLY', grain.outputs["Fac"], 0.5), (-1200, 100))
    col = ramp(nt, [(0.0, c4(srgb((0.50, 0.43, 0.34)))), (0.5, c4(srgb((0.64, 0.57, 0.46)))), (1.0, c4(srgb((0.74, 0.68, 0.57))))], (-1000, 100))
    nt.links.new(tone, col.inputs["Fac"])
    c = col.outputs["Color"]
    dmp = maprange(nt, noise_(nt, co, 0.5, 3, 0.5, loc=(-1300, -600)).outputs["Fac"], 0.5, 0.7, 0, 0.35, (-1100, -600))
    c = mix_rgb(nt, 'MULTIPLY', dmp, c, c4(srgb((0.6, 0.58, 0.55))), (-800, 100))
    joint = math_(nt, 'MAXIMUM', seam, butt, (-1000, 400))
    c = mix_rgb(nt, 'MIX', joint, c, c4(srgb((0.06, 0.05, 0.04))), (-600, 100))
    nt.links.new(c, b.inputs["Base Color"])
    nt.links.new(maprange(nt, joint, 0, 1, 0.78, 0.45, (-500, -200)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', grain.outputs["Fac"], 0.3), joint, (-400, -400)), 0.4, 0.004, (0, -500))
    return m


def sail_mat(name):
    """Weathered flax canvas: cloths about 0.6 m wide with darker seams, faint stains, a little translucence."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2000, 0)); s = sep_xyz(nt, co, (-1800, 0))
    sx = math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-1700, 200)), 0.62, (-1600, 200)), None, (-1450, 200))
    seam = maprange(nt, sx, 0.0, 0.035, 1, 0, (-1300, 200))
    n1 = noise_(nt, co, 0.6, 5, 0.6, loc=(-1500, -100))
    col = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.3, 0.7, 0, 1), c4(srgb((0.80, 0.75, 0.64))), c4(srgb((0.90, 0.86, 0.76))), (-1000, 0))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', seam, 0.4), col, c4(srgb((0.6, 0.55, 0.45))), (-700, 0))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9; b.inputs["Sheen Weight"].default_value = 0.2
    return m


def ensign_atlas():
    """The red ensign of the 1790s: a red field with the first union (St George's cross over St Andrew's saltire,
    before St Patrick's of 1801) in the canton. 512 x 256, row 0 at the top."""
    W, H = 512, 256; yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    a = np.zeros((H, W, 4), np.float32); a[..., 3] = 1
    a[..., :3] = (0.62, 0.08, 0.07)
    cw, ch = 256, 128
    can = (xx < cw) & (yy < ch)
    a[can, :3] = (0.05, 0.10, 0.32)
    for sgn in (1, -1):
        dd = np.abs((xx - cw / 2) * ch / cw * sgn - (yy - ch / 2)) / math.hypot(1, ch / cw)
        a[can & (dd < 13), :3] = (0.92, 0.92, 0.90)
    a[can & (np.abs(xx - cw / 2) < 21), :3] = (0.92, 0.92, 0.90); a[can & (np.abs(yy - ch / 2) < 21), :3] = (0.92, 0.92, 0.90)
    a[can & (np.abs(xx - cw / 2) < 13), :3] = (0.70, 0.08, 0.08); a[can & (np.abs(yy - ch / 2) < 13), :3] = (0.70, 0.08, 0.08)
    return np_image("A_Ensign", a)


def sea_mat(name):
    """Cold grey-blue northern sea under a clear sky: darker in the troughs, wind-streaked, paler toward the sun."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-1800, 0))
    n1 = noise_(nt, co, 0.08, 4, 0.55, loc=(-1400, 200)); n2_ = noise_(nt, co, 0.9, 6, 0.65, loc=(-1400, -100))
    col = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.3, 0.7, 0, 1), c4(srgb((0.07, 0.13, 0.17))), c4(srgb((0.12, 0.20, 0.25))), (-1000, 100))
    att = node(nt, "ShaderNodeAttribute", (-1200, -400)); att.attribute_name = "Col"
    sg = sep_xyz(nt, att.outputs["Color"], (-1000, -400))
    col = mix_rgb(nt, 'MIX', maprange(nt, math_(nt, 'MULTIPLY', sg.outputs["Y"], n2_.outputs["Fac"]), 0.15, 0.4, 0, 1, (-800, -300)), col, c4(srgb((0.82, 0.86, 0.88))), (-600, 100))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.2; b.inputs["Specular IOR Level"].default_value = 0.5
    bump_from(nt, b, n2_.outputs["Fac"], 0.8, 0.25, (0, -500))
    return m


def ice_mat(name):
    """Sea ice: snow-crusted white tops, blue-green wet edges and underwater skirts, grey melt patches."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-1800, 0)); s = sep_xyz(nt, co, (-1600, 0))
    n1 = noise_(nt, co, 0.7, 5, 0.6, loc=(-1300, 200)); n2_ = noise_(nt, co, 5.0, 4, 0.6, loc=(-1300, -100))
    top = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.35, 0.7, 0, 1), c4(srgb((0.78, 0.82, 0.84))), c4(srgb((0.95, 0.96, 0.96))), (-900, 200))
    edge = mix_rgb(nt, 'MIX', maprange(nt, s.outputs["Z"], SEA - 0.8, SEA - 0.02, 0, 1, (-1100, -300)), c4(srgb((0.06, 0.24, 0.28))), c4(srgb((0.40, 0.62, 0.66))), (-900, -200))
    k = maprange(nt, s.outputs["Z"], SEA - 0.02, SEA + 0.06, 0, 1, (-800, 0))
    col = mix_rgb(nt, 'MIX', k, edge, top, (-600, 100))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.7
    bump_from(nt, b, n2_.outputs["Fac"], 0.6, 0.06, (0, -500))
    return m


M_DECK = deck_mat("M_Deck")
M_HULL = noisy("M_HullPlanks", [srgb((0.13, 0.10, 0.08)), srgb((0.19, 0.15, 0.11)), srgb((0.10, 0.08, 0.06))], scale=2.0, rough=(0.5, 0.8), bump=0.15, stretch=(3.0, 0.2, 3.0))
M_BUL = noisy("M_Bulwark", [srgb((0.44, 0.39, 0.32)), srgb((0.54, 0.48, 0.40)), srgb((0.38, 0.33, 0.27)), srgb((0.58, 0.53, 0.45))], scale=3.0, rough=(0.6, 0.85), bump=0.15, stretch=(5.0, 0.25, 5.0))
M_PAINT = noisy("M_RailPaint", [srgb((0.10, 0.10, 0.09)), srgb((0.14, 0.13, 0.12)), srgb((0.08, 0.08, 0.08))], scale=8.0, rough=(0.4, 0.65), bump=0.05)
M_SPAR = noisy("M_Spars", [srgb((0.46, 0.34, 0.21)), srgb((0.56, 0.42, 0.27)), srgb((0.40, 0.29, 0.18))], scale=2.0, rough=(0.45, 0.7), bump=0.05, coat=0.1)
M_TAR = noisy("M_TarredRope", [srgb((0.07, 0.06, 0.05)), srgb((0.11, 0.09, 0.07)), srgb((0.05, 0.04, 0.04))], scale=60.0, rough=0.7, bump=0.0)
M_HEMP = noisy("M_Hemp", [srgb((0.58, 0.49, 0.35)), srgb((0.48, 0.40, 0.28)), srgb((0.66, 0.57, 0.42))], scale=120.0, rough=0.85, bump=0.4, bump_dist=0.004)
M_BRASS = plain("M_Brass", srgb((0.78, 0.58, 0.30)), rough=0.25, metallic=1.0)
M_IRON = noisy("M_Iron", [srgb((0.06, 0.06, 0.06)), srgb((0.16, 0.10, 0.07)), srgb((0.04, 0.04, 0.04))], scale=20.0, rough=(0.5, 0.8), metallic=0.6)
M_CASK = noisy("M_Casks", [srgb((0.40, 0.29, 0.18)), srgb((0.48, 0.36, 0.23)), srgb((0.32, 0.23, 0.14))], scale=4.0, rough=(0.55, 0.85), bump=0.1, stretch=(8.0, 8.0, 0.4))
M_SAIL = sail_mat("M_Sails")
M_SEA = sea_mat("M_Sea")
M_ICE = ice_mat("M_Ice")
M_BOAT = noisy("M_BoatPaint", [srgb((0.62, 0.60, 0.54)), srgb((0.55, 0.53, 0.47)), srgb((0.70, 0.68, 0.62))], scale=6.0, rough=0.6, bump=0.05)
IMG_ENS = ensign_atlas()
M_ENS = image_mat("M_Ensign", IMG_ENS, rough=0.85)
M_SKY = S.sky_mat(zenith=srgb((0.36, 0.54, 0.78)), horizon=srgb((0.92, 0.88, 0.80)), ground=srgb((0.30, 0.38, 0.42)), sun_dir=SUN_DIR,
                  glow=srgb((1.0, 0.78, 0.48)), glow_k=1.1, glow_pow=9.0, clouds=0.18, cloud_col=srgb((0.98, 0.92, 0.84)),
                  cloud_dark=srgb((0.70, 0.74, 0.80)), cloud_scale=0.5, land=srgb((0.86, 0.90, 0.94)), land_h=0.004, strength=1.0)

# ----------------------------------------------------------------------------- hull, deck, bulwarks, rail
print("hull ...", flush=True)
YS = [L_AFT + (L_FWD - L_AFT) * (i / 48) for i in range(49)]
hull = MB()
NZ = 8
rows = []
for y in YS:
    b0 = hb(y); zr = sheer(y) + BUL
    ring = []
    for k in range(NZ + 1):
        t = k / NZ; z = SEA - 0.6 + (zr - (SEA - 0.6)) * t
        tumble = 1.0 - 0.05 * t ** 2          # tumblehome toward the rail
        under = 1.0 - 0.18 * (1 - t) ** 2
        ring.append((b0 * tumble * under, z))
    rows.append(ring)
for side in (-1, 1):
    vs = [[hull.vert(Vector((side * max(0.02, x), y, z)), (y, z)) for (x, z) in ring] for y, ring in zip(YS, rows)]
    for j in range(len(YS) - 1):
        for k in range(NZ):
            f = (vs[j][k], vs[j + 1][k], vs[j + 1][k + 1], vs[j][k + 1])
            hull.face(*(f if side > 0 else f[::-1]))
# the transom
tr = [hull.vert(Vector((side * hb(L_AFT) * 0.97, L_AFT, z)), (0, 0)) for (side, z) in ((-1, SEA - 0.6), (1, SEA - 0.6), (1, sheer(L_AFT) + BUL), (-1, sheer(L_AFT) + BUL))]
hull.face(*tr)
hull.build("Hull", M_HULL, sway=False)
# a black wale band and the rail cap
wal = MB(); rail = MB()
for side in (-1, 1):
    for j in range(len(YS) - 1):
        y0, y1 = YS[j], YS[j + 1]
        for (za, zb_, mbx, off) in ((sheer(y0) - 0.55, sheer(y0) - 0.25, wal, 0.03),):
            p = [Vector((side * (hb(y0) * 0.995 + off), y0, sheer(y0) - 0.55)), Vector((side * (hb(y1) * 0.995 + off), y1, sheer(y1) - 0.55)),
                 Vector((side * (hb(y1) * 0.995 + off), y1, sheer(y1) - 0.25)), Vector((side * (hb(y0) * 0.995 + off), y0, sheer(y0) - 0.25))]
            mb_quad(mbx, p if side > 0 else [p[1], p[0], p[3], p[2]])
        # rail cap: a flat plank 0.16 wide on the bulwark top, with a rounded outer edge
        for (x0f, x1f, z0f, z1f) in ((-0.16, 0.03, 0.0, 0.0), (0.03, 0.03, 0.0, -0.07), (-0.16, -0.16, -0.07, 0.0)):
            p = [Vector((side * (hb(y0) * 0.95 + x0f), y0, sheer(y0) + BUL + z0f)), Vector((side * (hb(y1) * 0.95 + x0f), y1, sheer(y1) + BUL + z0f)),
                 Vector((side * (hb(y1) * 0.95 + x1f), y1, sheer(y1) + BUL + z1f)), Vector((side * (hb(y0) * 0.95 + x1f), y0, sheer(y0) + BUL + z1f))]
            mb_quad(rail, p if side < 0 else [p[1], p[0], p[3], p[2]])
wal.build("Wale", M_PAINT, sway=False)
rail.build("RailCap", M_SPAR, sway=False)
# deck surface
dk = MB(); NX = 14
drows = []
for y in YS:
    w = hb(y) * 0.94 - 0.18
    drows.append([dk.vert(Vector((-w + 2 * w * i / NX, y, deck_z(-w + 2 * w * i / NX, y))), (0, 0)) for i in range(NX + 1)])
for j in range(len(YS) - 1):
    for i in range(NX): dk.face(drows[j][i], drows[j][i + 1], drows[j + 1][i + 1], drows[j + 1][i])
dk.build("Deck", M_DECK, sway=False)
# bulwark inner face (planked, pale), waterway, stanchions
bw = MB(); stn = MB()
for side in (-1, 1):
    for j in range(len(YS) - 1):
        y0, y1 = YS[j], YS[j + 1]
        p = [Vector((side * (hb(y0) * 0.94 - 0.18), y0, deck_z(side * (hb(y0) * 0.94 - 0.18), y0) - 0.02)), Vector((side * (hb(y1) * 0.94 - 0.18), y1, deck_z(side * (hb(y1) * 0.94 - 0.18), y1) - 0.02)),
             Vector((side * (hb(y1) * 0.95 - 0.14), y1, sheer(y1) + BUL - 0.06)), Vector((side * (hb(y0) * 0.95 - 0.14), y0, sheer(y0) + BUL - 0.06))]
        mb_quad(bw, p if side < 0 else [p[1], p[0], p[3], p[2]])
    y = L_AFT + 0.6
    while y < L_FWD - 1.5:
        x = side * (hb(y) * 0.945 - 0.2)
        mb_box(stn, (x, y, sheer(y) + BUL / 2), (0.12, 0.14, BUL), skip=(0,))
        y += 1.1
bw.build("BulwarkInner", M_BUL, sway=False)
stn.build("Stanchions", M_BUL, sway=False)

# ----------------------------------------------------------------------------- masts, yards, sails, rigging
print("rig ...", flush=True)
SAIL_SETS = {"fore": [(13.5, 7.6, 12.5), (20.5, 14.2, 9.5), (26.0, 20.9, 6.8)],   # (yard z, foot z, yard span) for course, topsail, t'gallant
             "main": [(15.0, 8.2, 14.0), (23.0, 15.7, 10.6), (29.0, 23.4, 7.4)],
             "mizzen": [(18.5, 13.0, 8.2), (23.5, 18.9, 5.6)]}
sails = MB(); spars = []; ropes = []
def sail_sheet(cy, ztop, zfoot, span_top, span_foot, belly, nu=9, nv=7, roach=0.25):
    rows_ = []
    for j in range(nv + 1):
        v = j / nv; z = zfoot + (ztop - zfoot) * v
        sp = span_foot + (span_top - span_foot) * v
        row = []
        for i in range(nu + 1):
            u = i / nu; x = (u - 0.5) * sp
            bul = belly * math.sin(math.pi * u) * math.sin(math.pi * (0.15 + 0.85 * v)) ** 0.8
            zz = z + (roach * math.sin(math.pi * u) if j == 0 else 0.0)
            w = (1 - v) * (0.4 + 0.6 * math.sin(math.pi * u))
            row.append(sails.vert(Vector((x, cy + 0.35 + bul, zz)), (u, v), w))
        rows_.append(row)
    for j in range(nv):
        for i in range(nu): sails.face(rows_[j][i], rows_[j][i + 1], rows_[j + 1][i + 1], rows_[j + 1][i])

for mname, my in MASTS.items():
    top = {"fore": 32.0, "main": 35.5, "mizzen": 26.0}[mname]
    d0 = {"fore": 0.30, "main": 0.33, "mizzen": 0.24}[mname]
    lower = {"fore": 17.5, "main": 19.5, "mizzen": 15.5}[mname]
    tube(f"Mast_{mname}_lower", [Vector((0, my, -0.5)), Vector((0, my, lower + 1.5))], [d0, d0 * 0.8], M_SPAR, sides=10, caps=True)
    tube(f"Mast_{mname}_top", [Vector((0, my + 0.35, lower - 0.5)), Vector((0, my + 0.3, top))], [d0 * 0.62, d0 * 0.32], M_SPAR, sides=8, caps=True)
    box(f"Top_{mname}", (2.6 if mname != "mizzen" else 2.0, 1.7, 0.12), (0, my - 0.1, lower - 0.6), M_SPAR)     # the top (platform)
    box(f"Cap_{mname}", (0.5, 0.9, 0.3), (0, my + 0.15, lower + 1.4), M_PAINT)
    # mast partners on the deck
    lathe(f"Partner_{mname}", [(d0 + 0.18, 0.0), (d0 + 0.12, 0.25), (d0 + 0.02, 0.4)], (0, my, deck_z(0, my) - 0.02), M_BUL, steps=10)
    for k, (zy, zf, span) in enumerate(SAIL_SETS[mname]):
        tube(f"Yard_{mname}{k}", [Vector((-span / 2 - 0.6, my + 0.35, zy + 0.25)), Vector((0, my + 0.35, zy + 0.28)), Vector((span / 2 + 0.6, my + 0.35, zy + 0.25))],
             [0.08, 0.17 - 0.03 * k, 0.08], M_SPAR, sides=8, caps=True)
        nxt = SAIL_SETS[mname][k - 1][2] if k > 0 else span * 1.12
        sail_sheet(my, zy + 0.15, zf, span * 0.96, (nxt * 0.98 if k > 0 else span * 1.05), belly=1.0 + 0.3 * (2 - k), roach=0.0)
        # braces and sheets: from the yardarms aft and down
        for sx in (-1, 1):
            ropes.append(([Vector((sx * (span / 2 + 0.4), my + 0.35, zy + 0.2)), Vector((sx * hb(my - 6) * 0.95, my - 6.0, sheer(my - 6) + BUL))], 0.012, M_HEMP))
            if k == 0: ropes.append(([Vector((sx * span * 0.52, my + 1.2, zf)), Vector((sx * hb(my - 4.5) * 0.93, my - 4.5, sheer(my - 4.5) + BUL))], 0.018, M_HEMP))
    # shrouds with ratlines from below the top down to the channels outboard of the rail
    for sx in (-1, 1):
        heads = []
        for k in range(5 if mname != "mizzen" else 4):
            yb = my - 1.4 + k * 0.75
            foot = Vector((sx * (hb(yb) + 0.45), yb, sheer(yb) + BUL - 0.25))
            head = Vector((sx * 0.55, my - 0.1 + 0.05 * k, lower - 0.7))
            ropes.append(([foot, head], 0.022, M_TAR)); heads.append((foot, head))
            # deadeyes and the chain plate
            lathe(f"Deadeye_{mname}{sx}{k}", [(0.0, -0.06), (0.11, -0.04), (0.12, 0.0), (0.11, 0.04), (0.0, 0.06)], tuple(foot + Vector((0, 0, 0.25))), M_PAINT, steps=8,
                  rot=(0, math.pi / 2, 0))
            tube(f"Chain_{mname}{sx}{k}", [foot + Vector((0, 0, 0.18)), foot + Vector((-sx * 0.05, 0, -1.0))], 0.02, M_IRON, sides=4, caps=False)
        f0, h0 = heads[0]; f1, h1 = heads[-1]
        for r in range(1, 24):
            t = r * 0.38 / (lower - 1.0)
            if t > 0.92: break
            a = f0.lerp(h0, t); b_ = f1.lerp(h1, t)
            ropes.append(([a, b_], 0.008, M_TAR))
        # the channel (a ledge outboard taking the deadeyes)
        yc = my - 1.4 + 1.5
        box(f"Channel_{mname}{sx}", (0.5, 4.0, 0.12), (sx * (hb(yc) + 0.25), yc, sheer(yc) + BUL - 0.3), M_PAINT)
# stays: fore-and-aft
stays = [((0, MASTS["fore"], 31.5), (0, 24.5, 3.6)), ((0, MASTS["fore"], 17.0), (0, 21.0, 2.3)), ((0, MASTS["main"], 34.5), (0, MASTS["fore"] + 0.3, 21.5)),
         ((0, MASTS["main"], 18.5), (0, MASTS["fore"], 2.0)), ((0, MASTS["mizzen"], 25.0), (0, MASTS["main"] + 0.3, 24.0)), ((0, MASTS["mizzen"], 14.8), (0, MASTS["main"], 3.0))]
for a, b_ in stays: ropes.append(([Vector(a), Vector(b_)], 0.028, M_TAR))
for mname, my in MASTS.items():   # backstays
    top = {"fore": 30.5, "main": 34.0, "mizzen": 24.5}[mname]
    for sx in (-1, 1): ropes.append(([Vector((0, my + 0.2, top)), Vector((sx * (hb(my - 4.5) + 0.4), my - 4.5, sheer(my - 4.5) + BUL - 0.25))], 0.02, M_TAR))
# bowsprit and jibboom, jibs filled ahead
tube("Bowsprit", [Vector((0, 13.5, 0.9)), Vector((0, L_FWD + 0.2, 2.0)), Vector((0, 24.5, 3.7))], [0.3, 0.26, 0.13], M_SPAR, sides=10, caps=True)
tube("Jibboom", [Vector((0, 22.0, 3.3)), Vector((0, 29.0, 4.9))], [0.13, 0.07], M_SPAR, sides=8, caps=True)
def jib(head, tack, clew, belly=0.9, n=8):
    head, tack, clew = Vector(head), Vector(tack), Vector(clew)
    rows_ = []
    for j in range(n + 1):
        v = j / n
        a = tack.lerp(head, v); b_ = clew.lerp(head, v)
        row = []
        for i in range(n + 1):
            u = i / n; p = a.lerp(b_, u)
            bul = belly * math.sin(math.pi * u) * math.sin(math.pi * min(1, v + 0.1)) * (1 - v)
            p = p + Vector((0.35 * bul, 0.6 * bul, 0))
            row.append(sails.vert(p, (u, v), (1 - v) * math.sin(math.pi * u) + 0.1 * (1 - v)))
        rows_.append(row)
    for j in range(n):
        for i in range(n): sails.face(rows_[j][i], rows_[j][i + 1], rows_[j + 1][i + 1], rows_[j + 1][i])
jib((0, MASTS["fore"] + 0.6, 30.0), (0, 28.6, 4.8), (2.8, MASTS["fore"] + 6.0, 4.6), belly=1.1)
jib((0, MASTS["fore"] + 0.6, 22.5), (0, 24.2, 3.6), (2.5, MASTS["fore"] + 4.5, 3.4), belly=1.0)
# the spanker on the mizzen: gaff and boom, set to starboard a little
tube("Gaff", [Vector((0, MASTS["mizzen"] - 0.3, 13.0)), Vector((1.8, MASTS["mizzen"] - 7.2, 15.6))], [0.12, 0.08], M_SPAR, sides=8)
tube("Boom", [Vector((0, MASTS["mizzen"] - 0.3, 2.4)), Vector((2.6, MASTS["mizzen"] - 9.6, 2.9))], [0.14, 0.1], M_SPAR, sides=8)
rows_ = []
for j in range(8):
    v = j / 7
    a = Vector((0, MASTS["mizzen"] - 0.35, 2.6 + (13.0 - 2.6) * v)); b_ = Vector((2.6, MASTS["mizzen"] - 9.6, 3.0)).lerp(Vector((1.8, MASTS["mizzen"] - 7.2, 15.5)), v)
    rows_.append([sails.vert(a.lerp(b_, i / 8) + Vector((0.9 * math.sin(math.pi * i / 8) * math.sin(math.pi * (0.1 + 0.8 * v)), 0, 0)), (i / 8, v), math.sin(math.pi * i / 8) * 0.8) for i in range(9)])
for j in range(7):
    for i in range(8): sails.face(rows_[j][i], rows_[j][i + 1], rows_[j + 1][i + 1], rows_[j + 1][i])
sails.build("cloth.sail.set", M_SAIL)
rp = {}
for pts, r, mat in ropes:
    mb_ = rp.setdefault(mat.name, (MB(), mat))[0]
    a, b_ = pts[0], pts[-1]; n = 6 if (a - b_).length > 6 else 2
    sag = 0.012 * (a - b_).length if mat is M_HEMP else 0.004 * (a - b_).length
    q = [a.lerp(b_, i / n) - Vector((0, 0, sag * math.sin(math.pi * i / n))) for i in range(n + 1)]
    sides = 4 if r > 0.015 else 3

    up = None
    rings_ = []
    for i, p in enumerate(q):
        d = (q[min(i + 1, n)] - q[max(i - 1, 0)]).normalized()
        if up is None: ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0)); up = d.cross(ref).normalized()
        else: up = (up - d * up.dot(d)).normalized()
        vv = d.cross(up)
        rings_.append([mb_.vert(p + (up * math.cos(2 * math.pi * k / sides) + vv * math.sin(2 * math.pi * k / sides)) * r, (k / sides, i)) for k in range(sides)])
    for ra, rb in zip(rings_, rings_[1:]):
        for k in range(sides): mb_.face(ra[k], ra[(k + 1) % sides], rb[(k + 1) % sides], rb[k])
for k, (mb_, mat) in rp.items(): mb_.build("Rig_" + k[2:], mat, sway=False)

# ----------------------------------------------------------------------------- deck furniture
print("deck furniture ...", flush=True)
dz0 = deck_z(0, 0)
# main hatch with gratings and coaming, the long-boat on chocks over it
box("HatchCoaming", (2.4, 3.2, 0.42), (0, 3.6, deck_z(0, 3.6) + 0.18), M_BUL)
gr = MB()
for k in range(11): mb_box(gr, (-1.1 + k * 0.22, 3.6, deck_z(0, 3.6) + 0.41), (0.06, 3.0, 0.05))
for k in range(14): mb_box(gr, (0, 2.2 + k * 0.215, deck_z(0, 3.6) + 0.43), (2.2, 0.05, 0.04))
gr.build("Gratings", M_SPAR, sway=False)
# the boat: clinker hull upside down? no: right way up on chocks, covered thwarts
boat = MB(); bl, bb = 6.4, 1.8
brows = []
for j in range(13):
    t = j / 12; yb = 3.6 - bl / 2 + bl * t
    w = bb / 2 * math.sin(math.pi * (0.06 + 0.88 * t)) ** 0.7
    ring = []
    for k in range(7):
        a = math.pi * k / 6
        ring.append(boat.vert(Vector((-math.cos(a) * w, yb, deck_z(0, 3.6) + 1.05 - math.sin(a) * 0.7 * (0.4 + 0.6 * math.sin(math.pi * t)) + 0.15 * (2 * t - 1) ** 4)), (k / 6, t)))
    brows.append(ring)
for j in range(12):
    for k in range(6): boat.face(brows[j][k], brows[j][k + 1], brows[j + 1][k + 1], brows[j + 1][k])
boat.build("LongBoat", M_BOAT, sway=False)
for k in range(3): box(f"Thwart{k}", (1.55, 0.22, 0.04), (0, 2.0 + k * 1.5, deck_z(0, 3.6) + 0.85), M_SPAR)
for yy in (1.7, 5.5): box(f"Chock{yy}", (1.6, 0.25, 0.4), (0, yy, deck_z(0, yy) + 0.62), M_BUL)
# the brake pump by the mainmast (the leak): two barrels of elm, a cross beam and long brakes
for sx in (-0.45, 0.45):
    cyl(f"PumpDale{sx}", 0.13, 1.1, (sx, MASTS["main"] - 1.2, dz0 + 0.55), M_BUL, verts=10)
    cyl(f"PumpSpout{sx}", 0.03, 0.3, (sx + 0.12 * (1 if sx > 0 else -1), MASTS["main"] - 1.2, dz0 + 0.95), M_IRON, verts=6, rot=(0, math.pi / 2, 0))
tube("PumpBrake", [Vector((-2.2, MASTS["main"] - 1.2, dz0 + 1.25)), Vector((0, MASTS["main"] - 1.2, dz0 + 1.12)), Vector((2.2, MASTS["main"] - 1.2, dz0 + 0.95))], 0.04, M_SPAR, sides=6)
box("PumpTrestle", (0.15, 0.15, 1.15), (0, MASTS["main"] - 1.2, dz0 + 0.6), M_BUL)
# a shallow wash of water by the pump scupper
# coils of rope (flemished down) and belaying pins along the rail
def coil(x, y, r=0.32, turns=5):
    z = deck_z(x, y) + 0.02
    pts = []
    for k in range(turns * 14 + 1):
        a = 2 * math.pi * k / 14; rr = r * (1 - 0.65 * k / (turns * 14))
        pts.append(Vector((x + math.cos(a) * rr, y + math.sin(a) * rr, z + 0.012 * (k % 2))))
    tube(f"Coil{x:.1f}{y:.1f}", pts, 0.017, M_HEMP, sides=4, caps=False)
for (x, y) in [(2.5, 2.2), (2.6, -3.4), (-2.4, -3.0), (-2.5, 6.2), (2.2, 8.0), (1.6, -6.5), (-1.7, 10.5)]: coil(x, y)
pins = MB()
for side in (-1, 1):
    for (y0, y1) in ((-4.0, -0.6), (6.0, 9.6)):
        x = side * (hb((y0 + y1) / 2) * 0.94 - 0.32)
        mb_box(pins, (x, (y0 + y1) / 2, sheer(y0) + 0.75), (0.16, y1 - y0, 0.08))
        for k in range(int((y1 - y0) / 0.32)):
            yy = y0 + 0.16 + k * 0.32
            mb_box(pins, (x, yy, sheer(y0) + 0.78), (0.035, 0.035, 0.32))
            # a rope hanging from each pin in a loose bight

pins.build("PinRails", M_SPAR, sway=False)
hang = MB()
for side in (-1, 1):
    for (y0, y1) in ((-4.0, -0.6), (6.0, 9.6)):
        x = side * (hb((y0 + y1) / 2) * 0.94 - 0.32)
        for k in range(int((y1 - y0) / 0.32)):
            if rng.random() < 0.3: continue
            yy = y0 + 0.16 + k * 0.32
            top = Vector((x - side * 0.04, yy, sheer(y0) + 0.86)); n = 6; ln = rng.uniform(0.45, 0.6)
            pts = [top + Vector((-side * 0.05 * math.sin(math.pi * i / n), 0.03 * math.sin(2 * math.pi * i / n), -ln * math.sin(math.pi * i / n * 0.5) ** 0.7)) for i in range(n + 1)]
            pts += [p + Vector((-side * 0.02, 0.06, 0)) for p in pts[::-1]][1:]
            rings_ = []
            up = None
            for i, p in enumerate(pts):
                d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
                if up is None: up = d.cross(Vector((1, 0, 0))).normalized()
                else: up = (up - d * up.dot(d)).normalized()
                vv = d.cross(up)
                rings_.append([hang.vert(p + (up * math.cos(2 * math.pi * q / 3) + vv * math.sin(2 * math.pi * q / 3)) * 0.012) for q in range(3)])
            for ra, rb in zip(rings_, rings_[1:]):
                for q in range(3): hang.face(ra[q], ra[(q + 1) % 3], rb[(q + 1) % 3], rb[q])
hang.build("PinRopes", M_HEMP, sway=False)
# water casks lashed by the foremast, the windlass in the bows, the galley chimney
def cask(name, p, lying=False, rot=0.0, s=1.0):
    prof = [(0.26 * s, 0.0), (0.30 * s, 0.2 * s), (0.31 * s, 0.4 * s), (0.30 * s, 0.6 * s), (0.26 * s, 0.8 * s)]
    o = lathe(name, prof, p, M_CASK, steps=14)
    if lying: o.rotation_euler = (math.pi / 2, 0, rot); o.location.z += 0.3 * s
    for k, zz in enumerate((0.1, 0.7)):
        hp = lathe(f"{name}_h{k}", [(0.29 * s, (zz - 0.025) * s), (0.305 * s, zz * s), (0.29 * s, (zz + 0.025) * s)], p, M_IRON, steps=14)
        if lying: hp.rotation_euler = (math.pi / 2, 0, rot); hp.location.z += 0.3 * s
for k in range(4): cask(f"Cask{k}", (-2.0 + 0.0 * k, 6.7 + k * 0.66, deck_z(-2.0, 6.7 + k * 0.66)), lying=True, rot=math.pi / 2)
for k in range(2): cask(f"CaskU{k}", (2.4, -6.0 + k * 0.7, deck_z(2.4, -6.0)))
cyl("WindlassBarrel", 0.26, 4.2, (0, 13.2, sheer(13.2) + 0.55), M_SPAR, verts=8, rot=(0, math.pi / 2, 0))
for sx in (-1.9, 1.9): box(f"WindlassBitt{sx}", (0.3, 0.4, 1.0), (sx, 13.2, sheer(13.2) + 0.45), M_BUL)
box("Galley", (2.0, 2.4, 1.6), (0, 11.0, deck_z(0, 11.0) + 0.75), M_BUL)
box("GalleyRoof", (2.2, 2.6, 0.08), (0, 11.0, deck_z(0, 11.0) + 1.58), M_PAINT)
cyl("GalleyFlue", 0.12, 1.1, (0.5, 11.3, deck_z(0, 11.0) + 2.1), M_IRON, verts=8)
# aft: the binnacle and the wheel, the companion
bz = deck_z(0, -12.5)
box("Binnacle", (0.7, 0.55, 1.0), (0, -12.0, bz + 0.5), M_SPAR)
lathe("BinnacleHood", [(0.24, 0.0), (0.24, 0.18), (0.18, 0.3), (0.0, 0.34)], (0, -12.0, bz + 1.0), M_BRASS, steps=12)
wc = Vector((0, -13.3, bz + 1.25))

rim = []
for k in range(25):
    a = 2 * math.pi * k / 24; rim.append(wc + Vector((math.cos(a) * 0.72, 0, math.sin(a) * 0.72)))
tube("WheelRim", rim, 0.045, M_SPAR, sides=6, caps=False)
for k in range(10):
    a = 2 * math.pi * k / 10
    tube(f"Spoke{k}", [wc, wc + Vector((math.cos(a) * 0.95, 0, math.sin(a) * 0.95))], [0.035, 0.025], M_SPAR, sides=5)
cyl("WheelHub", 0.13, 0.2, tuple(wc), M_BRASS, verts=10, rot=(math.pi / 2, 0, 0))
for sx in (-0.3, 0.3): box(f"WheelStand{sx}", (0.1, 0.18, 1.3), (sx, -13.3, bz + 0.65), M_SPAR)
box("Companion", (1.4, 1.6, 0.95), (0, -8.2, deck_z(0, -8.2) + 0.45), M_BUL)
box("Skylight", (1.2, 1.4, 0.55), (0, -6.0, deck_z(0, -6.0) + 0.3), M_SPAR)
# the ensign at the mizzen peak (the gaff end)
fm = MB()
top_ = Vector((1.85, MASTS["mizzen"] - 7.35, 15.55))
for i in range(8):
    t0, t1 = i / 8, (i + 1) / 8
    def P(t, z): return top_ + Vector((0.05 * t + 0.25 * math.sin(t * 4) * t, 2.6 * t, z - 0.2 * t))
    vs = [fm.vert(P(t0, 0.0), (t0, 1), t0), fm.vert(P(t1, 0.0), (t1, 1), t1), fm.vert(P(t1, -1.3), (t1, 0), t1), fm.vert(P(t0, -1.3), (t0, 0), t0)]
    fm.face(*vs)
fm.build("cloth.flag.ensign", M_ENS)

# ----------------------------------------------------------------------------- the sea and the drifting ice
print("sea and ice ...", flush=True)
floes = []
R2 = random.Random(31)
for k in range(150):
    r = 18 + 520 * R2.random() ** 1.6; a = R2.uniform(-math.pi, math.pi)
    x, y = r * math.sin(a), r * math.cos(a)
    if abs(x) < 9 and -30 < y < 40: continue
    north = 0.5 + 0.5 * math.cos(a)
    if R2.random() > 0.25 + 0.75 * north: continue
    size = R2.uniform(2.0, 7.0) * (1 + r / 160) * (0.6 + 0.8 * north)
    floes.append((x, y, size, R2.uniform(0, math.pi)))
floes += [(15.0, 30.0, 6.5, 0.4), (-13.0, 22.0, 4.0, 1.2), (19.0, 9.0, 3.2, 0.9), (24.0, 58.0, 9.0, 2.2), (-26.0, 64.0, 11.0, 0.3), (9.0, 80.0, 7.0, 1.7)]
ice = MB()
def floe(x, y, size, rot, seed):
    n = 16; Rr = random.Random(seed); pts = []
    for i in range(n):
        a = rot + 2 * math.pi * i / n + Rr.uniform(-0.2, 0.2)
        rr = size * Rr.uniform(0.55, 1.0)
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr * Rr.uniform(0.75, 1.0)))
    hgt = Rr.uniform(0.15, 0.5) * (1 + size / 20)
    top = [ice.vert(Vector((px, py, SEA + hgt * Rr.uniform(0.7, 1.2))), (px, py)) for px, py in pts]
    mid = [ice.vert(Vector((x + (px - x) * 0.55, y + (py - y) * 0.55, SEA + hgt + Rr.uniform(0.0, 0.25) * (1 + size / 15))), (px, py)) for px, py in pts]
    c = ice.vert(Vector((x, y, SEA + hgt + Rr.uniform(0.05, 0.5) * (1 + size / 12))), (x, y))
    for i in range(n):
        j = (i + 1) % n; ice.face(c, mid[i], mid[j]); ice.face(mid[i], top[i], top[j], mid[j])
    bot = [ice.vert(Vector((x + (px - x) * 1.12, y + (py - y) * 1.12, SEA - 0.9)), (px, py)) for px, py in pts]
    for i in range(n):
        j = (i + 1) % n; ice.face(top[i], bot[i], bot[j], top[j])
for k, f in enumerate(floes): floe(*f, k)
ice.build("Ice", M_ICE, sway=False)
# the sea: a disc to 1100 m, finer near the hull; foam (vertex colour G) along the hull, the bow wave and the floe edges
sea = S.polar_terrain("water.ocean.sea", lambda x, y: SEA, M_SEA, r_max=1100.0, r0=1.5, rings=40, seg=96, centre=(0.0, 4.0))
me = sea.data
ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
vals = []
for v in me.vertices:
    x, y = v.co.x, v.co.y
    dh = abs(abs(x) - hb(max(L_AFT, min(L_FWD, y)))) if L_AFT - 2 < y < L_FWD + 3 else 99
    g = math.exp(-dh / 1.5) * (1.3 if y > 8 else 0.8)
    if y > L_FWD - 3 and abs(x) < 6: g += 0.6 * math.exp(-abs(y - L_FWD) / 3)
    if y < L_AFT + 2 and abs(x) < 4 + (L_AFT - y) * 0.25: g += 0.5 * math.exp(-(L_AFT - y) / 12)           # the wake
    for (fx_, fy, fs, _) in floes:
        d = math.hypot(x - fx_, y - fy)
        if d < fs * 1.6: g = max(g, 0.6 * (1 - d / (fs * 1.6)))
    vals += [0.0, min(1.0, g), 0.0, 1.0]
ca.data.foreach_set("color", vals); me.color_attributes.active_color = ca

# ----------------------------------------------------------------------------- sky, light, anchors, sounds
SKY = S.sky_dome(M_SKY, radius=1150.0)
S.world(SUN_DIR, sun_energy=4.0, sun_col=(1.0, 0.80, 0.55), sun_angle=0.7,
        sky_cols=(srgb((0.30, 0.38, 0.44)), srgb((0.86, 0.85, 0.82)), srgb((0.38, 0.55, 0.80))), sky_strength=1.2)
RD = Vector((2.55, 0.6, 0.0)); RD.z = deck_z(RD.x, RD.y)
eye, fwd = S.reader(tuple(RD), -4.0)
anchor("scene.centre", (0.0, 4.0, dz0))
anchor("bow", (0.0, L_FWD, sheer(L_FWD)))
anchor("wheel", tuple(wc))
sound("surf", "bow", (0.0, L_FWD + 1.0, SEA + 0.5))
sound("surf", "starboard", (hb(0) + 1.0, 2.0, SEA + 0.5))
sound("rigging", "main", (0.0, MASTS["main"], 12.0))
sound("rigging", "fore", (0.0, MASTS["fore"], 12.0))
sound("wind", "deck", (0.0, -4.0, 3.0))
sound("gulls", "astern", (6.0, -30.0, 10.0))

page = S.page_preview(eye, fwd)
cams = S.view_cams(eye, -4.0, extra=[
    ("Cam_Page", eye, eye + fwd * 10 + Vector((0, 0, -1.2)), 17),
    ("Cam_Rail", eye, eye + Vector((1.0, 0.5, -0.25)) * 10, 17),
    ("Cam_Sails", eye, eye + Vector((-0.1, 0.6, 0.8)) * 10, 17),
    ("Cam_Helm", Vector((1.6, -7.0, deck_z(1.6, -7.0) + 1.6)), wc + Vector((0, 0, -0.3)), 24),
])
S.finish(ARGS, cams, "walton_ship_deck.gltf", page=page,
         keep_names={"M_Sails": "cloth.sail.set", "M_Ensign": "cloth.flag.ensign", "M_Sea": "water.ocean.sea"},
         keep_uv={"M_Sea"},
         size_for={"M_Deck": (2048, 256, 1024), "M_HullPlanks": (1024, 128, 512), "M_Bulwark": (1024, 128, 512), "M_Sails": (1024, 128, 256),
                   "M_Spars": (1024, 128, 512), "M_TarredRope": (128,), "M_Hemp": (256, 64, 128), "M_Sea": (1024, 128, 512), "M_Ice": (1024, 128, 512),
                   "M_RailPaint": (256, 64), "M_Brass": (64,), "M_Iron": (128, 64), "M_Casks": (512, 64, 256), "M_BoatPaint": (256, 64, 128),
                   "M_SkyDome": (1024,)},
         default_size=(256, 64, 128), no_shadow={"M_SkyDome"})
