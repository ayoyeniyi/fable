"""
Fable scene room: A snowy street in St Petersburg (Frankenstein, Letter I) - petersburg-street.

"I am already far north of London, and as I walk in the streets of Petersburgh, I feel a cold northern breeze play
upon my cheeks, which braces my nerves and fills me with delight."
"I prefer [a sledge journey]; the cold is not excessive, if you are wrapped in furs - a dress which I have already
adopted ... They fly quickly over the snow in their sledges; the motion is pleasant."
"I shall depart for the latter town [Archangel] in a fortnight or three weeks" (the post-road).

A winter street of the 1790s: packed-snow roadway rutted by sledge runners between snow-banked granite kerbs and
trodden pavements; stuccoed neoclassical town houses (ochre, pale yellow, white) with tall sash windows, rusticated
ground floors, pilasters, cornices and snow-laden roofs; iron lamp posts with oil lanterns (unlit by day); the
posting house on the right with its carriage gateway and signboard, a covered post-sledge (kibitka) ready for the
Archangel road before it, two hired sledges with fur rugs drawn up at the kerb (their horses not modelled), a cross
street on the left where the low sun cuts across the road, and far down the street the gilded spire.

Time: a clear cold winter day, the sun low in the south-south-west behind the reader (about 8 degrees up): the street
in long blue shadow, the upper storeys of the right-hand houses and the cross street in warm sun.
No people or horses, no ships or ice, no modern vehicles, tramlines or electric light.

Axes: metres, +Z up, +Y north (down the street). Reader on the west pavement facing north.

Run headless:
  blender -b -P blender/build_petersburg_street.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_petersburg_street.py -- --cpu --render --samples 32 --res 1280 --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b4 as S
from scene_kit_b4 import (K, new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, lathe, tube, MB, anchor, sound, smoothstep, n2, srgb,
                          mb_box, mb_quad, text_mesh)

ARGS = S.setup("petersburg-street", 1797, "PetersburgStreet", default_samples=48)
rng = random.Random(1797)
EYE = S.EYE
RX = 4.6           # roadway half width
FX = 6.8           # facade line
ROAD_Z = -0.14     # the roadway below the pavements
SUN_DIR = Vector((-0.33, -0.93, 0.14)).normalized()      # toward the sun: south-south-west, ~8 degrees up
READER = Vector((-5.25, 0.0, 0.0)); YAW = 12.0
CROSS = (9.0, 23.0)          # the cross street on the left (west), y range
Y0, Y1 = -70.0, 175.0

# ----------------------------------------------------------------------------- materials
def snow_mat(name, base=(0.86, 0.89, 0.93), dirt=0.0, ruts=False):
    """Snow: blue-white, soft sparkle-free roughness, gentle drifts; packed roadway snow greyer, with sledge-runner
    grooves along the street, dung-stained and yellowed lines and scattered straw."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0)); s = sep_xyz(nt, co, (-2200, 0))
    n1 = noise_(nt, co, 0.4, 4, 0.55, loc=(-1800, 300)); n2_ = noise_(nt, co, 6.0, 6, 0.6, loc=(-1800, 0)); n3 = noise_(nt, co, 60.0, 3, 0.6, loc=(-1800, -300))
    col0 = srgb(base); col1 = srgb(tuple(c * 0.86 for c in base))
    col = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.3, 0.7, 0, 1), c4(col1), c4(col0), (-1300, 300))
    hgt = math_(nt, 'ADD', math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.7), math_(nt, 'MULTIPLY', n3.outputs["Fac"], 0.3), (-1300, -200))
    if ruts:
        # runner grooves: many narrow lines along y, densest in the two driving lanes
        wx = math_(nt, 'ADD', s.outputs["X"], math_(nt, 'MULTIPLY', noise_(nt, co, 0.15, 2, 0.5, loc=(-2000, -700)).outputs["Fac"], 1.2), (-1800, -700))
        wv = node(nt, "ShaderNodeTexWave", (-1600, -700), wave_type='BANDS', bands_direction='X'); wv.inputs["Scale"].default_value = 1.1
        wv.inputs["Distortion"].default_value = 0.8; wv.inputs["Detail"].default_value = 2.0
        cx = node(nt, "ShaderNodeCombineXYZ", (-1700, -700)); nt.links.new(wx, cx.inputs["X"]); nt.links.new(s.outputs["Y"], cx.inputs["Y"]); nt.links.new(cx.outputs[0], wv.inputs["Vector"])
        groove = maprange(nt, wv.outputs["Fac"], 0.93, 1.0, 0, 1, (-1400, -700))
        ax = math_(nt, 'ABSOLUTE', s.outputs["X"], None, (-1700, -1000))
        lanew = math_(nt, 'MULTIPLY', maprange(nt, ax, 0.3, 1.2, 0.4, 1.0, (-1500, -1000)), maprange(nt, ax, 3.0, 4.0, 1.0, 0.15, (-1500, -1150)), (-1300, -1000))
        groove = math_(nt, 'MULTIPLY', groove, lanew, (-1200, -800))
        grey = mix_rgb(nt, 'MIX', maprange(nt, n2_.outputs["Fac"], 0.35, 0.65, 0, 1), c4(srgb((0.62, 0.62, 0.62))), c4(srgb((0.70, 0.66, 0.58))), (-1100, -500))
        col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', lanew, 0.75, (-1000, -400)), col, grey, (-900, 100))
        col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', groove, 0.16, (-900, -700)), col, c4(srgb((0.55, 0.50, 0.42))), (-700, 100))
        # dung and straw specks
        vor = voronoi_(nt, co, 3.0, 'F1', (-1600, -1300))
        speck = math_(nt, 'MULTIPLY', maprange(nt, vor.outputs["Distance"], 0.07, 0.03, 0, 1, (-1400, -1300)), lanew, (-1200, -1300))
        col = mix_rgb(nt, 'MIX', speck, col, c4(srgb((0.36, 0.28, 0.18))), (-500, 100))
        groove = math_(nt, 'MULTIPLY', groove, maprange(nt, noise_(nt, co, 0.25, 2, 0.5, loc=(-1400, -1500)).outputs["Fac"], 0.4, 0.6, 0.2, 1.0, (-1200, -1500)), (-1000, -800))
        hgt = math_(nt, 'SUBTRACT', hgt, math_(nt, 'MULTIPLY', groove, 0.12), (-1000, -200))
    if dirt:
        col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n2_.outputs["Fac"], 0.4, 0.75, 0, dirt, (-1100, 600)), col, c4(srgb((0.6, 0.58, 0.55))), (-400, 100))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.62; b.inputs["Specular IOR Level"].default_value = 0.35
    b.inputs["Subsurface Weight"].default_value = 0.0
    bump_from(nt, b, hgt, 0.25, 0.02, (0, -500))
    return m


def stucco_mat(name, colour, rough=0.85):
    """Lime stucco washed in one colour: soft mottling, darker grime streaks running down from ledges, frost-paled
    near the ground; rustication grooves on the ground floor (below 4.1 m) every 0.5 m."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0)); s = sep_xyz(nt, co, (-2200, 0))
    n1 = noise_(nt, co, 0.8, 5, 0.6, loc=(-1800, 300)); n3 = noise_(nt, co, 30.0, 4, 0.6, loc=(-1800, -300))
    st = node(nt, "ShaderNodeMapping", (-1900, -600)); st.inputs["Scale"].default_value = (1.2, 1.2, 0.35); nt.links.new(co, st.inputs["Vector"])
    streak = noise_(nt, st.outputs["Vector"], 3.0, 4, 0.6, loc=(-1600, -600))
    c0 = srgb(colour); c1 = srgb(tuple(c * 0.88 for c in colour)); c2 = srgb(tuple(min(1, c * 1.06) for c in colour))
    col = ramp(nt, [(0.0, c4(c1)), (0.5, c4(c0)), (1.0, c4(c2))], (-1300, 300)); nt.links.new(n1.outputs["Fac"], col.inputs["Fac"])
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, streak.outputs["Fac"], 0.6, 0.85, 0, 0.08, (-1300, -600)), col.outputs["Color"], c4(srgb((0.62, 0.58, 0.52))), (-1000, 200))
    # rustication: horizontal grooves on the ground floor
    zz = math_(nt, 'MULTIPLY', s.outputs["Z"], 2.0, (-1900, -1000))
    fr = math_(nt, 'FRACT', zz, None, (-1750, -1000))
    groove = math_(nt, 'MULTIPLY', maprange(nt, fr, 0.0, 0.06, 1, 0, (-1600, -1000)), maprange(nt, s.outputs["Z"], 4.0, 4.1, 1, 0, (-1600, -1150)), (-1400, -1050))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', groove, 0.45), col, c4(srgb((0.5, 0.46, 0.40))), (-800, 200))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Specular IOR Level"].default_value = 0.3
    bump_from(nt, b, math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', n3.outputs["Fac"], 0.3), groove, (-500, -500)), 0.4, 0.01, (0, -500))
    return m


def window_atlas():
    """512 x 1024: left half a six-over-six sash window (white glazing bars, crown glass reflecting the pale sky and
    the houses opposite, a muslin curtain behind some panes), right half a panelled double door with a fanlight."""
    W, H = 512, 1024; a = np.zeros((H, W, 4), np.float32); a[..., 3] = 1
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # glass: dark interior with a vertical sky reflection gradient and wavy crown-glass distortion
    wav = 0.04 * np.sin(xx * 0.09 + yy * 0.013) + 0.03 * np.sin(yy * 0.05)
    t = yy / H
    glass = np.stack([0.20 + 0.35 * (1 - t) + wav, 0.23 + 0.38 * (1 - t) + wav, 0.28 + 0.42 * (1 - t) + wav], -1)
    a[..., :3] = glass
    frame = np.array([0.90, 0.89, 0.85]); bar = np.array([0.86, 0.85, 0.80])
    # window cell: x 0..255
    def rect(x0, x1, y0, y1, c): a[int(y0):int(y1), int(x0):int(x1), :3] = c
    rect(0, 256, 0, 22, frame); rect(0, 256, H - 22, H, frame); rect(0, 18, 0, H, frame); rect(238, 256, 0, H, frame)
    rect(0, 256, H // 2 - 10, H // 2 + 10, frame)   # meeting rails
    for k in (1, 2):
        x = 18 + k * (220 / 3); rect(x - 4, x + 4, 0, H, bar)
    for half in (0, 1):
        for k in (1, 2):
            y = 22 + half * (H // 2 - 12) + k * ((H // 2 - 32) / 3); rect(0, 256, y - 4, y + 4, bar)
    # muslin curtain, half drawn, in the lower sash
    cur = (xx < 110) & (yy > H // 2 + 10) & (yy < H - 22) & (xx > 18)
    a[cur, :3] = a[cur, :3] * 0.3 + np.array([0.80, 0.78, 0.72]) * 0.7 * (0.85 + 0.15 * np.sin(xx[cur] * 0.35))[:, None]
    # door cell: x 256..511: fanlight at top, two leaves with raised panels, dark green paint
    d = np.array([0.13, 0.20, 0.16]); dl = np.array([0.18, 0.27, 0.21]); dd = np.array([0.08, 0.12, 0.10])
    rect(256, 512, 0, H, d)
    rect(256, 512, 0, 240, glass[0:240, 256:512].mean(axis=(0, 1)))
    fan = (yy < 240) & (((xx - 384) ** 2 / 128 ** 2 + (yy - 240) ** 2 / 230 ** 2) < 1)
    a[(yy < 240) & ~fan, :3] = np.array([0.88, 0.86, 0.80])
    for k in range(7):
        ang = math.pi * (k + 1) / 8
        ln = (np.abs((xx - 384) * math.cos(ang) + (yy - 240) * math.sin(ang)) < 3) & fan & (yy < 240)
        a[ln, :3] = frame
    rect(256, 512, 236, 252, frame); rect(380, 388, 252, H, dd)
    for lx in (270, 396):
        for (py0, py1) in ((300, 600), (640, 990)):
            rect(lx, lx + 104, py0, py1, dd); rect(lx + 6, lx + 98, py0 + 6, py1 - 6, dl)
    return np_image("A_WindowsDoors", a)   # painted with row 0 at the top, as np_image wants


def sign_mat():
    m = plain("M_SignBoard", srgb((0.07, 0.08, 0.07)), rough=0.5)
    return m


M_SNOW = snow_mat("M_Snow")
M_ROAD = snow_mat("M_RoadSnow", base=(0.80, 0.80, 0.80), ruts=True)
M_PAVE = snow_mat("M_PavementSnow", base=(0.82, 0.84, 0.87), dirt=0.25)
M_OCHRE = stucco_mat("M_StuccoOchre", (0.80, 0.60, 0.33))
M_YELLOW = stucco_mat("M_StuccoYellow", (0.90, 0.80, 0.52))
M_WHITE = stucco_mat("M_StuccoWhite", (0.88, 0.86, 0.80))
M_TRIM = stucco_mat("M_StuccoTrim", (0.93, 0.92, 0.88))
M_GRANITE = noisy("M_Granite", [srgb((0.42, 0.33, 0.30)), srgb((0.55, 0.45, 0.40)), srgb((0.30, 0.25, 0.24)), srgb((0.62, 0.55, 0.50))], scale=40.0, rough=0.7, bump=0.3)
M_ROOFIRON = noisy("M_RoofIron", [srgb((0.25, 0.32, 0.27)), srgb((0.20, 0.26, 0.22)), srgb((0.30, 0.30, 0.26))], scale=4.0, rough=0.6, metallic=0.3, bump=0.1)
M_IRON = noisy("M_Iron", [srgb((0.06, 0.06, 0.06)), srgb((0.10, 0.09, 0.08)), srgb((0.04, 0.04, 0.04))], scale=30.0, rough=(0.4, 0.7), metallic=0.7, bump=0.05)
M_GLASS = plain("M_LanternGlass", srgb((0.75, 0.78, 0.76)), rough=0.08, transmission=0.0)
M_SLEDGE = wood("M_SledgeWood", base=srgb((0.30, 0.13, 0.08)), dark=srgb((0.14, 0.05, 0.03)), light=srgb((0.42, 0.20, 0.10)), scale=3.0, rough=(0.3, 0.6), coat=0.3, ao=0.0)
M_PLAIN_WOOD = wood("M_Timber", base=srgb((0.45, 0.36, 0.25)), dark=srgb((0.26, 0.20, 0.13)), light=srgb((0.56, 0.46, 0.33)), scale=4.0, rough=(0.6, 0.85), ao=0.0)
M_FUR = noisy("M_Fur", [srgb((0.40, 0.31, 0.22)), srgb((0.52, 0.42, 0.30)), srgb((0.30, 0.23, 0.16))], scale=90.0, rough=0.95, bump=0.8, bump_dist=0.006, sheen=0.6, warp=1.5)
M_LEATHER = noisy("M_Leather", [srgb((0.13, 0.10, 0.08)), srgb((0.18, 0.13, 0.10)), srgb((0.09, 0.07, 0.06))], scale=12.0, rough=(0.45, 0.7), bump=0.2)
M_GILT = plain("M_Gilt", srgb((0.85, 0.65, 0.30)), rough=0.3, metallic=1.0)
M_FLAG = plain("M_Flag", srgb((0.92, 0.92, 0.90)), rough=0.85, sheen=0.3)
M_FLAGB = plain("M_FlagStripes", srgb((0.20, 0.28, 0.62)), rough=0.85)
M_SIGN = sign_mat()
M_GATE = wood("M_GateWood", base=srgb((0.24, 0.17, 0.11)), dark=srgb((0.12, 0.08, 0.05)), light=srgb((0.33, 0.24, 0.16)), scale=2.0, rough=(0.6, 0.85), grain_dir=(14, 1, 1), ao=0.0)
IMG_WIN = window_atlas()
M_WIN = image_mat("M_WindowsDoors", IMG_WIN, rough=0.15, spec=0.6)
M_SKY = S.sky_mat(zenith=srgb((0.36, 0.52, 0.76)), horizon=srgb((0.86, 0.85, 0.86)), ground=srgb((0.78, 0.80, 0.84)), sun_dir=SUN_DIR,
                  glow=srgb((1.0, 0.80, 0.58)), glow_k=0.9, glow_pow=10.0, clouds=0.12, cloud_col=srgb((0.97, 0.94, 0.92)),
                  cloud_dark=srgb((0.75, 0.78, 0.84)), cloud_scale=0.6, strength=1.0)

# ----------------------------------------------------------------------------- ground: roadway, kerbs, pavements, snow banks
print("ground ...", flush=True)
def ys_list(y0, y1):
    ys = [0.0]; y = 0.0; step = 0.5
    while y < y1: y += step; step = min(6.0, step * 1.09); ys.append(y)
    y = 0.0; step = 0.5; neg = []
    while y > y0: y -= step; step = min(6.0, step * 1.12); neg.append(y)
    return sorted(neg + ys)
YS = ys_list(Y0, Y1)
def road_z(x, y): return ROAD_Z + 0.02 * noise.noise(Vector((x * 0.7, y * 0.7, 0.3))) + 0.025 * (1 - (abs(x) / RX) ** 2)
mb = MB()
XS = [-RX + 2 * RX * i / 12 for i in range(13)]
rows = [[mb.vert(Vector((x, y, road_z(x, y))), (x, y)) for x in XS] for y in YS]
for j in range(len(YS) - 1):
    for i in range(len(XS) - 1): mb.face(rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i])
mb.build("Roadway", M_ROAD, sway=False)
pv = MB()
def pave_z(x, y): return 0.01 * noise.noise(Vector((x * 1.3, y * 1.3, 2.3))) + 0.04 * smoothstep(5.9, 6.8, abs(x))   # snow drifted against the walls
for side in (-1, 1):
    xs = [side * (RX + 0.18 + (FX - RX - 0.18) * i / 5) for i in range(6)]
    if side < 0: xs = xs[::-1]
    rws = []
    for y in YS:
        if side < 0 and CROSS[0] + 0.5 < y < CROSS[1] - 0.5: rws.append(None); continue
        rws.append([pv.vert(Vector((x, y, pave_z(x, y))), (x, y)) for x in xs])
    for j in range(len(YS) - 1):
        if rws[j] is None or rws[j + 1] is None: continue
        for i in range(5): pv.face(rws[j][i], rws[j][i + 1], rws[j + 1][i + 1], rws[j + 1][i])
# the cross street's roadway and pavements (west), out to 70 m
for j, (xa, xb) in enumerate([(-70.0, -RX)]):
    yl = [CROSS[0] + 0.5 + (CROSS[1] - CROSS[0] - 1) * k / 6 for k in range(7)]
    xl = [xa + (xb - xa) * k / 14 for k in range(15)]
    rw = [[pv.vert(Vector((x, y, ROAD_Z + 0.06 * (1 - ((y - sum(CROSS) / 2) / 7) ** 2) + 0.12 * smoothstep(-RX - 0.4, -RX, x) * 0)), (x, y)) for x in xl] for y in yl]
    for a_ in range(6):
        for b_ in range(14): pv.face(rw[a_][b_], rw[a_][b_ + 1], rw[a_ + 1][b_ + 1], rw[a_ + 1][b_])
pv.build("Pavements", M_PAVE, sway=False)
# a big snow plane under the far square and behind everything
box("SnowField", (400, 520, 0.2), (0, 190, ROAD_Z - 0.12), M_SNOW)

# granite kerbs (only their tops and street faces show between the banks)
kb = MB()
for side in (-1, 1):
    y = Y0
    while y < Y1:
        L = rng.uniform(1.2, 2.2)
        if not (side < 0 and CROSS[0] < y + L / 2 < CROSS[1]):
            mb_box(kb, (side * (RX + 0.09), y + L / 2, -0.06), (0.22, L - 0.012, 0.22), yaw=rng.gauss(0, 0.004))
        y += L
kb.build("Kerbs", M_GRANITE, sway=False)

# snow banks along the kerbs, shovelled from the pavements: lumpy ridges with gaps at crossings and gateways
banks = MB()
def bank(side, ya, yb, hmax):
    n = max(3, int((yb - ya) / (0.35 if abs(ya) < 25 else 0.7))); prof = 8; rows_ = []
    for i in range(n + 1):
        y = ya + (yb - ya) * i / n; taper = max(0.0, math.sin(math.pi * i / n)) ** 0.5
        hh = hmax * taper * (0.75 + 0.25 * noise.noise(Vector((side * 3.1, y * 0.6, 0.2)))) + 0.02
        w = 0.55 + 0.15 * noise.noise(Vector((side, y * 0.4, 1.4)))
        ring = []
        for k in range(prof + 1):
            u = k / prof; ang = math.pi * u
            xo = -math.cos(ang) * w; zo = max(0.0, math.sin(ang)) ** 1.3 * hh
            xo += 0.07 * noise.noise(Vector((y * 2.0, u * 3.0, side)))
            zo += 0.09 * hh * noise.noise(Vector((y * 1.6, u * 5.0, side + 3.0))) * math.sin(ang)
            x = side * (RX - 0.55) + side * xo
            ring.append(banks.vert(Vector((x, y, ROAD_Z + zo + (0.12 if side * xo > 0.1 else 0.0) * u)), (u, y)))
        rows_.append(ring)
    for ra, rb in zip(rows_, rows_[1:]):
        for k in range(prof): banks.face(ra[k], ra[k + 1], rb[k + 1], rb[k])
for side in (-1, 1):
    y = -40.0
    while y < 75:
        L = rng.uniform(4.0, 11.0)
        ya, yb = y, y + L
        if side < 0 and not (yb < CROSS[0] - 1 or ya > CROSS[1] + 1): y = CROSS[1] + 1.5; continue
        if side > 0 and 15.5 < (ya + yb) / 2 < 22.0: y += L + 1.0; continue      # the posting-house gateway
        bank(side, ya, yb, rng.uniform(0.35, 0.65) * (1.0 if abs(ya) < 60 else 0.8))
        y = yb + rng.uniform(0.8, 2.0)
banks.build("SnowBanks", M_SNOW, sway=False)

# ----------------------------------------------------------------------------- town houses
print("houses ...", flush=True)
F = {m.name: MB() for m in (M_OCHRE, M_YELLOW, M_WHITE, M_TRIM, M_SNOW, M_ROOFIRON, M_WIN, M_GRANITE)}
MATS = {m.name: m for m in (M_OCHRE, M_YELLOW, M_WHITE, M_TRIM, M_SNOW, M_ROOFIRON, M_WIN, M_GRANITE)}
WIN_UV = ((0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)); DOOR_UV = ((0.5, 0.0), (1.0, 0.0), (1.0, 1.0), (0.5, 1.0))

def tb(mbx, c, size, **kw):
    """a moulding box on the facade: no face against the wall, no underside."""
    mb_box(mbx, c, size, skip=(0, 4 if SIDE[0] > 0 else 5), **kw)
SIDE = [1]

def fpt(side, y, out, z):
    """a point on the facade plane of the given side: out = metres proud of the wall (toward the street)."""
    return Vector((side * (FX - out), y, z))

def window(side, y, z0, w, hgt, uv=WIN_UV, depth=0.16, pediment=None, sill_snow=True, detail=True):
    # the glass and frame, just proud of the wall, inside a moulded architrave (the reveal's depth is implied)
    a, b_ = y - w / 2, y + w / 2
    if side < 0: a, b_ = b_, a
    mb_quad(F["M_WindowsDoors"], [fpt(side, a, 0.012, z0), fpt(side, b_, 0.012, z0), fpt(side, b_, 0.012, z0 + hgt), fpt(side, a, 0.012, z0 + hgt)], uv)
    if not detail: return
    T = F["M_StuccoTrim"]; SIDE[0] = side
    for yy in (y - w / 2 - 0.07, y + w / 2 + 0.07):
        tb(T, fpt(side, yy, 0.04, z0 + hgt / 2), (0.08, 0.14, hgt + 0.1))
    # architrave and sill
    tb(T, fpt(side, y, 0.03, z0 - 0.06), (0.10, w + 0.3, 0.1))
    tb(T, fpt(side, y, 0.02, z0 + hgt + 0.08), (0.06, w + 0.22, 0.14))
    if sill_snow: tb(F["M_Snow"], fpt(side, y, 0.03, z0 + 0.02), (0.13, w + 0.24, 0.05))
    if pediment == "cornice":
        tb(T, fpt(side, y, 0.10, z0 + hgt + 0.32), (0.22, w + 0.5, 0.12))
        tb(F["M_Snow"], fpt(side, y, 0.12, z0 + hgt + 0.41), (0.24, w + 0.5, 0.07))
    elif pediment == "triangle":
        pe = F["M_StuccoTrim"]; zb = z0 + hgt + 0.24; ww = w / 2 + 0.3
        P = [fpt(side, y - ww, 0.14, zb), fpt(side, y + ww, 0.14, zb), fpt(side, y, 0.14, zb + 0.42)]
        Q = [fpt(side, y - ww, 0.0, zb), fpt(side, y + ww, 0.0, zb), fpt(side, y, 0.0, zb + 0.42)]
        vs = [pe.vert(p) for p in P]; pe.face(*(vs if side > 0 else vs[::-1]))
        for i in range(3):
            j = (i + 1) % 3; q = [pe.vert(P[i]), pe.vert(P[j]), pe.vert(Q[j]), pe.vert(Q[i])]; pe.face(*q)
        mb_box(pe, fpt(side, y, 0.08, zb - 0.04), (0.18, 2 * ww + 0.05, 0.08))
        for sg in (-1, 1):   # snow on the raking cornices
            p0 = fpt(side, y + sg * ww, 0.10, zb + 0.03); p1 = fpt(side, y, 0.10, zb + 0.45)
            c = (p0 + p1) / 2; L = (p1 - p0).length
            mb_box(F["M_Snow"], c, (0.2, L, 0.06), tilt=(-sg * math.atan2(0.42, ww) * (1 if side > 0 else -1), 0.0))

def house(side, ya, yb, storeys, mat, style, gate=None, far=False):
    """A stuccoed town house fronting the street between ya and yb (along y): rusticated ground floor 4.1 m, upper
    storeys of 3.7 / 3.5 / 3.0 m, string course, pilasters (style 'pilasters'), main cornice, attic, a snow-laden iron
    roof with chimneys. gate: (y, width) of a carriage gateway."""
    W = yb - ya; yc = (ya + yb) / 2; D = 14.0
    hts = [4.1, 3.7, 3.5, 3.0][:storeys]; H = sum(hts)
    body = F[mat.name]
    mb_box(body, (side * (FX + D / 2), yc, (H + 0.6) / 2 - 0.6), (D, W, H + 0.6))
    T = F["M_StuccoTrim"]
    # plinth (granite) and string course
    mb_box(F["M_Granite"], (side * (FX + 0.02), yc, -0.2), (0.12, W, 0.7))
    mb_box(T, fpt(side, yc, 0.08, 4.1), (0.24, W, 0.2))
    mb_box(F["M_Snow"], fpt(side, yc, 0.10, 4.22), (0.24, W, 0.05))
    # main cornice with snow and the roof
    mb_box(T, fpt(side, yc, 0.22, H - 0.1), (0.5, W + 0.02, 0.35))
    mb_box(F["M_Snow"], fpt(side, yc, 0.25, H + 0.12), (0.52, W + 0.02, 0.1))
    pitch = math.radians(24); rh = (D / 2) * math.tan(pitch)
    for k, (x0, x1) in enumerate(((FX - 0.3, FX + D / 2), (FX + D + 0.3, FX + D / 2))):
        p = [Vector((side * x0, ya - 0.05, H + 0.02)), Vector((side * x0, yb + 0.05, H + 0.02)), Vector((side * x1, yb + 0.05, H + rh)), Vector((side * x1, ya - 0.05, H + rh))]
        mb_quad(F["M_Snow"], [q + Vector((0, 0, 0.12)) for q in p], ((0, 0), (W, 0), (W, D / 2), (0, D / 2)))
        mb_quad(F["M_RoofIron"], [p[0], p[1], p[1] + Vector((0, 0, 0.12)), p[0] + Vector((0, 0, 0.12))])
    for e_y in (ya, yb):   # gable ends (party walls), mostly hidden
        vs = [body.vert(Vector((side * FX, e_y, H))), body.vert(Vector((side * (FX + D), e_y, H))), body.vert(Vector((side * (FX + D / 2), e_y, H + rh)))]
        body.face(*vs)
    for k in range(max(1, int(W / 9))):   # chimneys with snow caps
        cy = ya + (k + 0.5) * W / max(1, int(W / 9)) + rng.uniform(-1, 1); cx = side * (FX + rng.uniform(3.5, 6.0))
        ch = H + (abs(cx) - FX) * math.tan(pitch) + 1.0
        mb_box(body, (cx, cy, ch - 0.6), (0.7, 1.0, 1.8))
        mb_box(F["M_Snow"], (cx, cy, ch + 0.33), (0.78, 1.08, 0.1))
    # bays
    nb = max(2, int(round(W / 2.8))); bw = W / nb
    gate_bays = set()
    if gate:
        gy, gw = gate
        for i in range(nb):
            if abs(ya + (i + 0.5) * bw - gy) < gw / 2 + 0.2: gate_bays.add(i)
    for i in range(nb):
        y = ya + (i + 0.5) * bw
        z = 0.0
        for s_, hgt in enumerate(hts):
            if s_ == 0:
                if i in gate_bays: z += hgt; continue
                if style == "shop" and i % 3 == 1:
                    window(side, y, 0.05, 1.3, 3.0, uv=DOOR_UV, depth=0.2, sill_snow=False, detail=not far)
                else:
                    window(side, y, 1.1, 1.15, 2.0, depth=0.18, detail=not far)
            else:
                wh = {1: 2.45, 2: 2.1, 3: 1.4}[s_]; z0 = z + (0.55 if s_ < 3 else 0.6)
                ped = ("triangle" if (style == "pilasters" and i % 2 == 0) else "cornice") if s_ == 1 and not far else None
                window(side, y, z0, 1.2 if s_ < 3 else 1.0, wh, pediment=ped, detail=not far)
            z += hgt
        if style == "pilasters" and not far:   # pilasters between bays through the upper storeys
            for yy in (ya + i * bw,) + ((yb,) if i == nb - 1 else ()):
                SIDE[0] = side; tb(T, fpt(side, yy, 0.07, 4.2 + (H - 4.4) / 2), (0.14, 0.5, H - 4.4))
                tb(T, fpt(side, yy, 0.10, H - 0.5), (0.2, 0.62, 0.25))
    if gate:   # carriage arch through the ground floor
        gy, gw = gate
        a, b_ = gy - gw / 2, gy + gw / 2
        if side < 0: a, b_ = b_, a
        GT = MB()
        mb_quad(GT, [fpt(side, a, 0.02, 0.0), fpt(side, b_, 0.02, 0.0), fpt(side, b_, 0.02, 3.6), fpt(side, a, 0.02, 3.6)], ((0, 0), (gw, 0), (gw, 3.6), (0, 3.6)))
        GT.build("GatewayLeaves", M_GATE, sway=False)
        a, b_ = gy - gw / 2, gy + gw / 2
        mb_box(T, fpt(side, gy, 0.12, 3.75), (0.3, gw + 0.8, 0.4))
        for yy in (a - 0.25, b_ + 0.25): mb_box(T, fpt(side, yy, 0.12, 1.85), (0.3, 0.5, 3.7))
    return H


# west side (left): from behind the reader to the cross street, then beyond it
west = [(-70, -48, 3, M_WHITE, "plain"), (-48, -30, 3, M_OCHRE, "pilasters"), (-30, -12, 3, M_YELLOW, "plain"), (-12, CROSS[0], 3, M_OCHRE, "pilasters"),
        (CROSS[1], 40, 4, M_WHITE, "pilasters"), (40, 58, 3, M_YELLOW, "plain"), (58, 80, 3, M_OCHRE, "plain"), (80, 104, 4, M_YELLOW, "pilasters"),
        (104, 130, 3, M_WHITE, "plain"), (130, 160, 3, M_OCHRE, "plain")]
east = [(-70, -44, 3, M_YELLOW, "plain"), (-44, -20, 3, M_WHITE, "pilasters"), (-20, -2, 3, M_OCHRE, "shop"), (-2, 12, 3, M_WHITE, "plain"),
        (12, 30, 2, M_YELLOW, "posting"), (30, 52, 4, M_OCHRE, "pilasters"), (52, 70, 3, M_WHITE, "plain"), (70, 96, 3, M_YELLOW, "plain"),
        (96, 124, 4, M_WHITE, "pilasters"), (124, 160, 3, M_OCHRE, "plain")]
for (ya, yb, st, m, style) in west:
    house(-1, ya, yb, st, m, style, far=abs((ya + yb) / 2) > 55)
for (ya, yb, st, m, style) in east:
    if style == "posting": house(1, ya, yb, st, m, "plain", gate=(19.0, 3.4))
    else: house(1, ya, yb, st, m, style, far=abs((ya + yb) / 2) > 55)
# the cross street's houses (west), seen through the gap in the sun
for (y_side, mat_) in ((CROSS[0] - 7.0, M_YELLOW), (CROSS[1] + 7.0, M_WHITE)):
    mb_box(F[mat_.name], (-51.0, y_side, 7.5), (59.0, 14.0, 15.0))
    for k in range(19):
        x = -23.5 - k * 2.9
        for zz in (1.1, 4.7, 8.4):
            yy = y_side + (7.0 if y_side < CROSS[0] else -7.0)
            sgn = 1 if y_side < CROSS[0] else -1
            a, b_ = x - 0.6, x + 0.6
            P = [Vector((a, yy + 0.01 * sgn, zz)), Vector((b_, yy + 0.01 * sgn, zz)), Vector((b_, yy + 0.01 * sgn, zz + 2.1)), Vector((a, yy + 0.01 * sgn, zz + 2.1))]
            mb_quad(F["M_WindowsDoors"], P if sgn > 0 else [P[1], P[0], P[3], P[2]], WIN_UV)
    mb_box(F["M_Snow"], (-51.0, y_side, 15.1), (59.0, 14.2, 0.25))
# the far end: a square, and the gilded spire beyond it
mb_box(F["M_StuccoYellow"], (0.0, 330.0, 9.0), (90.0, 30.0, 18.0))
mb_box(F["M_StuccoTrim"], (0.0, 314.5, 9.0), (60.0, 1.0, 14.0))
mb_box(F["M_Snow"], (0.0, 330.0, 18.15), (90.4, 30.4, 0.3))
for k, mname in F.items(): F[k].build("H_" + k[2:], MATS[k], sway=False)
tw = MB()
mb_box(tw, (0, 336, 25), (14, 14, 14))
mb_box(tw, (0, 336, 35), (9, 9, 8))
tw.build("SpireTower", M_WHITE, sway=False)
cyl("SpireDrum", 3.6, 5.0, (0, 336, 41.5), M_GILT, verts=16)
cyl("SpireNeedle", 2.4, 30.0, (0, 336, 59.0), M_GILT, verts=12, r2=0.15)

# ----------------------------------------------------------------------------- the posting house: signboard, flag
text_mesh("PostSign", "ПОЧТОВЫЙ ДВОРЪ", (FX - 0.10, 19.0, 4.45), 0.42, M_GILT, rot=(math.pi / 2, 0, -math.pi / 2))
box("SignBoard", (0.05, 4.6, 0.62), (FX - 0.06, 19.0, 4.45), M_SIGN)
fp = Vector((FX - 0.3, 24.0, 7.9))
cyl("FlagPole", 0.04, 3.2, tuple(fp + Vector((-0.6, 0, 0.9))), M_IRON, verts=6, rot=(0, math.radians(-35), 0))
fm = MB(); fb = MB()
top = fp + Vector((-1.5, 0, 2.2))
for i in range(8):
    t0, t1 = i / 8, (i + 1) / 8
    for band in range(3):     # white, blue, red: the merchant flag of the period
        z0, z1 = 0.0 - band * 0.3, -0.3 - band * 0.3
        def P(t, z): return top + Vector((-0.04 * math.sin(t * 6), 1.3 * t, z - 0.15 * t * t))
        tgt = fm if band == 0 else fb
        vs = [tgt.vert(P(t0, z0), (t0, 0), t0), tgt.vert(P(t1, z0), (t1, 0), t1), tgt.vert(P(t1, z1), (t1, 1), t1), tgt.vert(P(t0, z1), (t0, 1), t0)]
        tgt.face(*vs)
M_FLAGR = plain("M_FlagRed", srgb((0.70, 0.12, 0.10)), rough=0.85)
fm.build("cloth.flag.post", M_FLAG)
# blue and red bands: two materials in one billowing mesh is not possible per material merge; build red separately
fr = MB()
for i in range(8):
    t0, t1 = i / 8, (i + 1) / 8
    def P(t, z): return top + Vector((-0.04 * math.sin(t * 6), 1.3 * t, z - 0.15 * t * t))
    vs = [fr.vert(P(t0, -0.6), (t0, 0), t0), fr.vert(P(t1, -0.6), (t1, 0), t1), fr.vert(P(t1, -0.9), (t1, 1), t1), fr.vert(P(t0, -0.9), (t0, 1), t0)]
    fr.face(*vs)
fb2 = MB()
for i in range(8):
    t0, t1 = i / 8, (i + 1) / 8
    def P(t, z): return top + Vector((-0.04 * math.sin(t * 6), 1.3 * t, z - 0.15 * t * t))
    vs = [fb2.vert(P(t0, -0.3), (t0, 0), t0), fb2.vert(P(t1, -0.3), (t1, 0), t1), fb2.vert(P(t1, -0.6), (t1, 1), t1), fb2.vert(P(t0, -0.6), (t0, 1), t0)]
    fb2.face(*vs)
fb2.build("cloth.flag.postblue", M_FLAGB)
fr.build("cloth.flag.postred", M_FLAGR)

# ----------------------------------------------------------------------------- lamp posts (oil lanterns, unlit by day)
lamp = MB(); glass = MB()
def lamppost(x, y):
    z = 0.0
    pts = [Vector((x, y, z - 0.1)), Vector((x, y, z + 0.25)), Vector((x, y, z + 2.9))]
    K.tube(f"Post{y:.0f}", pts, [0.075, 0.055, 0.045], M_IRON, sides=8, caps=True)
    K.lathe(f"PostBase{y:.0f}", [(0.12, 0.0), (0.12, 0.25), (0.08, 0.32), (0.06, 0.45)], (x, y, z - 0.05), M_IRON, steps=8)
    c = Vector((x, y, z + 3.2))
    for sx in (-1, 1):
        for sy in (-1, 1): K.tube(f"LF{y:.0f}{sx}{sy}", [c + Vector((sx * 0.13, sy * 0.13, -0.28)), c + Vector((sx * 0.17, sy * 0.17, 0.2))], 0.009, M_IRON, sides=4, caps=False)
    K.lathe(f"LTop{y:.0f}", [(0.22, 0.2), (0.24, 0.23), (0.0, 0.42)], tuple(c), M_IRON, steps=4)
    K.lathe(f"LBot{y:.0f}", [(0.0, -0.36), (0.14, -0.28), (0.15, -0.26)], tuple(c), M_IRON, steps=4)
    K.lathe(f"LGlass{y:.0f}", [(0.15, -0.27), (0.21, 0.2)], tuple(c), M_GLASS, steps=4)
    box(f"LSnow{y:.0f}", (0.26, 0.26, 0.05), tuple(c + Vector((0, 0, 0.44))), M_SNOW, rot=(0, 0, math.radians(45)))
for (x, y) in [(-RX - 0.38, 7.0), (-RX - 0.38, 31.0), (-RX - 0.38, 55.0), (RX + 0.38, -4.0), (RX + 0.38, 25.0), (RX + 0.38, 49.0), (RX + 0.38, 73.0), (-RX - 0.38, -17.0)]:
    lamppost(x, y)

# ----------------------------------------------------------------------------- sledges
print("sledges ...", flush=True)
def runner(name, base, yaw, L, gauge, up=0.55, mat=None):
    """a pair of bent-wood runners shod with iron, curling up at the front."""
    R_ = Matrix.Rotation(yaw, 3, 'Z')
    for sx in (-1, 1):
        pts = []
        for i in range(10):
            t = i / 9
            if t < 0.78: p = Vector((sx * gauge / 2, -L / 2 + L * t / 0.78 * 0.78, 0.02))
            else:
                a = (t - 0.78) / 0.22 * math.pi * 0.62
                p = Vector((sx * gauge / 2, -L / 2 + L * 0.78 + math.sin(a) * up * 0.6, 0.02 + (1 - math.cos(a)) * up))
            pts.append(Vector(base) + R_ @ p)
        K.tube(f"{name}_r{sx}", pts, 0.028, mat or M_SLEDGE, sides=6, caps=True)
        for t in (0.15, 0.45, 0.7):   # stanchions
            p = Vector(base) + R_ @ Vector((sx * gauge / 2, -L / 2 + L * t, 0.0))
            K.tube(f"{name}_st{sx}{t}", [p + Vector((0, 0, 0.03)), p + Vector((0, 0, 0.32))], 0.02, M_SLEDGE, sides=5, caps=False)

def izvozchik(name, base, yaw, rug_col=None, shafts=True):
    """a hired town sledge: low curved body on runners, high back, a bearskin rug over the seat and hanging behind."""
    R_ = Matrix.Rotation(yaw, 3, 'Z'); B = Vector(base)
    def P(x, y, z): return B + R_ @ Vector((x, y, z))
    runner(name, B, yaw, 2.0, 0.75)
    # body: floor, sides, curved dash, high back
    sb = MB()
    mb_box(sb, P(0, -0.15, 0.36), (0.78, 1.25, 0.05), yaw=yaw)
    for sx in (-1, 1):
        mb_box(sb, P(sx * 0.38, -0.1, 0.52), (0.04, 1.3, 0.3), yaw=yaw)
    mb_box(sb, P(0, -0.72, 0.62), (0.82, 0.06, 0.55), yaw=yaw, tilt=(math.radians(28), 0))
    for k in range(5):   # the swept dash at the front
        a = k / 4 * math.pi / 2
        mb_box(sb, P(0, 0.52 + math.sin(a) * 0.25, 0.42 + (1 - math.cos(a)) * 0.35), (0.76, 0.06, 0.12), yaw=yaw, tilt=(-a, 0))
    o = sb.build(name + "_body", M_SLEDGE, sway=False)
    # the fur rug: draped over the seat and the back, hanging down behind
    fr_ = MB(); nu, nv = 8, 10
    rows_ = []
    for j in range(nv + 1):
        v = j / nv
        # path: from the dash floor, over the seat, up the back, over and down behind
        if v < 0.35: yy, zz = 0.45 - v / 0.35 * 0.95, 0.41 + 0.06 * math.sin(v * 9)
        elif v < 0.7: t = (v - 0.35) / 0.35; yy, zz = -0.5 - 0.40 * t, 0.43 + 0.50 * t
        else: t = (v - 0.7) / 0.3; yy, zz = -0.92 - 0.12 * math.sin(t * math.pi / 2), 0.92 - 0.35 * t
        row = []
        for i in range(nu + 1):
            u = i / nu; xx = (u - 0.5) * 0.86 * (1.0 if v < 0.7 else 1.0 + 0.12 * t)
            zz2 = zz + 0.02 * noise.noise(Vector((u * 4, v * 4, 1.0))) + (0.03 if v < 0.35 else 0)
            row.append(fr_.vert(P(xx, yy - 0.02 * (abs(u - 0.5) * 2) ** 2, zz2), (u, v)))
        rows_.append(row)
    for j in range(nv):
        for i in range(nu): fr_.face(rows_[j][i], rows_[j][i + 1], rows_[j + 1][i + 1], rows_[j + 1][i])
    fr_.build(name + "_rug", M_FUR, sway=False)
    if shafts:   # the shafts, unharnessed, resting on the snow ahead
        for sx in (-1, 1):
            p0 = P(sx * 0.42, 0.45, 0.4); p1 = P(sx * 0.55, 2.9, 0.06)
            K.tube(f"{name}_sh{sx}", [p0, p0.lerp(p1, 0.5) + Vector((0, 0, 0.05)), p1], [0.035, 0.03, 0.026], M_PLAIN_WOOD, sides=6, caps=True)

def kibitka(name, base, yaw):
    """a covered post-sledge for the long road: a deep box body on runners, a hooped leather hood over the back half,
    trunks roped on behind, straw in the well."""
    R_ = Matrix.Rotation(yaw, 3, 'Z'); B = Vector(base)
    def P(x, y, z): return B + R_ @ Vector((x, y, z))
    runner(name, B, yaw, 3.2, 1.1, up=0.7)
    sb = MB()
    mb_box(sb, P(0, -0.1, 0.38), (1.15, 2.6, 0.06), yaw=yaw)
    for sx in (-1, 1): mb_box(sb, P(sx * 0.56, -0.1, 0.65), (0.05, 2.6, 0.55), yaw=yaw)
    mb_box(sb, P(0, 1.18, 0.62), (1.15, 0.05, 0.5), yaw=yaw, tilt=(math.radians(-25), 0))
    mb_box(sb, P(0, -1.38, 0.7), (1.15, 0.05, 0.65), yaw=yaw)
    sb.build(name + "_body", M_PLAIN_WOOD, sway=False)
    hd = MB(); nu = 10
    rows_ = []
    for j in range(7):
        yy = -1.38 + j * 0.24
        rows_.append([hd.vert(P(-0.6 * math.cos(math.pi * i / nu), yy, 0.9 + 0.75 * math.sin(math.pi * i / nu) - 0.04 * j * (j > 4)), (i / nu, j / 6)) for i in range(nu + 1)])
    for j in range(6):
        for i in range(nu): hd.face(rows_[j][i], rows_[j][i + 1], rows_[j + 1][i + 1], rows_[j + 1][i])
    hd.build(name + "_hood", M_LEATHER, sway=False)
    cap = MB()
    for j in range(6):
        yy = -1.38 + j * 0.24
        rows2 = [cap.vert(P(-0.62 * math.cos(math.pi * i / nu), yy, 0.92 + 0.78 * math.sin(math.pi * i / nu) + 0.04), (i / nu, 0)) for i in range(nu + 1)]
        rows3 = [cap.vert(P(-0.62 * math.cos(math.pi * i / nu), yy + 0.18, 0.92 + 0.78 * math.sin(math.pi * i / nu) + 0.04), (i / nu, 1)) for i in range(nu + 1)]
        for i in range(nu):
            if 2 <= i < nu - 2: cap.face(rows2[i], rows2[i + 1], rows3[i + 1], rows3[i])
    cap.build(name + "_snow", M_SNOW, sway=False)
    box(name + "_trunk", (0.9, 0.5, 0.45), tuple(P(0, -1.75, 0.6)), M_LEATHER, rot=(0, 0, yaw))
    box(name + "_trunk2", (0.8, 0.45, 0.35), tuple(P(0.02, -1.72, 1.0)), M_PLAIN_WOOD, rot=(0, 0.03, yaw + 0.05))
    for sx in (-1, 1):
        p0 = P(sx * 0.5, 1.2, 0.45); p1 = P(sx * 0.62, 3.9, ROAD_Z + 0.06 - B.z)
        K.tube(f"{name}_sh{sx}", [p0, p0.lerp(p1, 0.5) + Vector((0, 0, 0.06)), p1], [0.04, 0.035, 0.03], M_PLAIN_WOOD, sides=6, caps=True)

izvozchik("SledgeA", (-3.35, 5.2, ROAD_Z), math.radians(-3))
izvozchik("SledgeB", (-3.1, 12.4, ROAD_Z), math.radians(2))
kibitka("Kibitka", (3.1, 17.8, ROAD_Z), math.radians(178))

# ----------------------------------------------------------------------------- sky, light, anchors, sounds
SKY = S.sky_dome(M_SKY, radius=900.0)
S.world(SUN_DIR, sun_energy=3.6, sun_col=(1.0, 0.80, 0.60), sun_angle=0.6,
        sky_cols=(srgb((0.70, 0.72, 0.76)), srgb((0.80, 0.82, 0.88)), srgb((0.36, 0.52, 0.80))), sky_strength=1.3)
eye, fwd = S.reader((READER.x, READER.y, pave_z(READER.x, READER.y)), YAW)
anchor("scene.centre", (0.0, 12.0, ROAD_Z))
anchor("posting.house", (FX, 19.0, 0.0))
sound("wind", "street", (0.0, 30.0, 3.0))
sound("wind", "crossstreet", (-14.0, 16.0, 2.0))
sound("crowd", "posting", (FX - 1.0, 19.0, 1.5))
sound("crowd", "street", (-2.0, 60.0, 1.5))

page = S.page_preview(eye, fwd)
cams = S.view_cams(eye, YAW, extra=[
    ("Cam_Page", eye, eye + fwd * 10 + Vector((0, 0, -1.2)), 17),
    ("Cam_Sledge", Vector((-1.5, 1.0, 1.5)), Vector((-3.3, 5.3, 0.3)), 24),
    ("Cam_Posting", Vector((-2.0, 6.0, 1.6)), Vector((5.5, 19.0, 3.0)), 24),
    ("Cam_Up", eye, eye + Vector((0.2, 1.0, 0.6)) * 10, 17),
])
S.finish(ARGS, cams, "petersburg_street.gltf", page=page,
         keep_names={"M_Flag": "cloth.flag.post", "M_FlagStripes": "cloth.flag.postblue", "M_FlagRed": "cloth.flag.postred"},
         size_for={"M_RoadSnow": (2048, 256, 1024), "M_PavementSnow": (1024, 128, 512), "M_Snow": (1024, 128, 512), "M_StuccoOchre": (1024, 128, 512),
                   "M_StuccoYellow": (1024, 128, 512), "M_StuccoWhite": (1024, 128, 512), "M_StuccoTrim": (1024, 128, 512), "M_Granite": (512, 64, 256),
                   "M_RoofIron": (256, 64), "M_Iron": (256, 64, 128), "M_SledgeWood": (512, 64, 256), "M_Timber": (256, 64, 128), "M_Fur": (512, 64, 256),
                   "M_Leather": (256, 64, 128), "M_Gilt": (64,), "M_SkyDome": (1024,), "M_LanternGlass": (32,), "M_SignBoard": (32,),
                   "M_Flag": (32,), "M_FlagStripes": (32,), "M_FlagRed": (32,)},
         default_size=(256, 64, 128), no_shadow={"M_SkyDome"})
