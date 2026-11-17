"""
Fable scene room: New Bedford thoroughfare near the docks, Sunday morning (Moby-Dick, chapter VI) - new-bedford-dock-street.

"In thoroughfares nigh the docks, any considerable seaport will frequently offer to view the queerest looking
nondescripts from foreign parts." "In bespeaking his sea-outfit, he orders bell-buttons to his waistcoats; straps to
his canvas trousers." "Go and gaze upon the iron emblematical harpoons round yonder lofty mansion ... all these brave
houses and flowery gardens came from the Atlantic, Pacific, and Indian oceans." "In summer time, the town is sweet to
see; full of fine maples - long avenues of green and gold."

A December Sunday morning of the 1840s, the night's frost packed hard on the street: a broad street running down to
the wharves, white clapboard and red brick houses and stores with green shutters and fanlit doors, an outfitter's and
a ship chandler's with small-paned shop windows and painted signboards, granite kerbs, brick footways scraped of
snow, leafless maples along both sides; sea chests and casks left at a store door and a hand-cart; uphill behind the
reader the lofty mansion in its garden behind a fence of iron emblematical harpoons; downhill the street turns to
frozen cobbles at the wharf, the spiles, a whale-ship and a brig lying alongside with their sails furled and an
ensign at the peak, and the river's far shore. No people.

Light: a low, clear, sunny cold morning, the sun in the south-east ahead-right of the reader, long shadows up the
street. No sleet yet, no gas or electric lights, no modern signs.

Axes: metres, +Z up, +Y east (down the street to the docks), +X south. The reader mid-street facing downhill.

Run headless:
  blender -b -P blender/build_new_bedford_dock_street.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_new_bedford_dock_street.py -- --cpu --render --samples 32 --res 1280 --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b4 as S
from scene_kit_b4 import (K, new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, lathe, tube, MB, anchor, sound, smoothstep, n2, srgb,
                          mb_box, mb_quad, text_mesh, card, set_card_normals)

ARGS = S.setup("new-bedford-dock-street", 1840, "NewBedfordDockStreet", default_samples=48)
rng = random.Random(1840)
EYE = S.EYE
RX = 5.2            # roadway half width
FX = 8.0            # house fronts
SLOPE = 0.055       # the street falls toward the docks
WHARF_Y = 66.0      # the wharf's edge
SEA = -WHARF_Y * SLOPE - 2.0
SUN_DIR = Vector((0.50, 0.78, 0.30)).normalized()     # toward the sun: south-east, ~17 degrees up
READER = Vector((-1.2, 0.0, 0.0)); YAW = 4.0
ROAD_Z = -0.15

def street_z(y): return -SLOPE * min(y, WHARF_Y) - 0.01 * max(0.0, y - WHARF_Y)

# ----------------------------------------------------------------------------- materials (snow and the window atlas as in build_petersburg_street.py)
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




def clapboard_mat(name, colour):
    """Painted clapboard: lapped boards about 11 cm to the weather, each lower edge throwing a thin shadow line, the
    paint chalky and a little weathered, faint vertical butt joints."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2200, 0)); s = sep_xyz(nt, co, (-2000, 0))
    fr = math_(nt, 'FRACT', math_(nt, 'DIVIDE', s.outputs["Z"], 0.11, (-1800, 0)), None, (-1650, 0))
    lap = maprange(nt, fr, 0.0, 0.12, 1, 0, (-1500, 0))
    n = noise_(nt, co, 2.0, 5, 0.6, loc=(-1500, 300))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 0.12, (-1200, 300)), c4(srgb(colour)), (0.75, 0.74, 0.70, 1), (-1000, 100))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', lap, 0.35), col, (0.45, 0.45, 0.45, 1), (-800, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.7
    bump_from(nt, b, math_(nt, 'SUBTRACT', fr, math_(nt, 'MULTIPLY', lap, 0.3), (-700, -300)), 0.5, 0.008, (0, -400))
    return m


def brick_mat(name, scale=1.0, paving=False):
    """Red brick in running bond with pale lime joints (walls), or laid flat for footways (paving=True)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2200, 0)); s = sep_xyz(nt, co, (-2000, 0))
    vec = node(nt, "ShaderNodeCombineXYZ", (-1800, 0))
    if paving: nt.links.new(s.outputs["X"], vec.inputs["X"]); nt.links.new(s.outputs["Y"], vec.inputs["Y"])
    else:
        nt.links.new(math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-1900, 100)), vec.inputs["X"]); nt.links.new(s.outputs["Z"], vec.inputs["Y"])
    br = node(nt, "ShaderNodeTexBrick", (-1500, 0))
    br.inputs["Scale"].default_value = 1.0 / scale; br.inputs["Mortar Size"].default_value = 0.010
    br.inputs["Brick Width"].default_value = 0.205; br.inputs["Row Height"].default_value = 0.068
    br.inputs["Color1"].default_value = c4(srgb((0.52, 0.22, 0.15))); br.inputs["Color2"].default_value = c4(srgb((0.42, 0.18, 0.13)))
    br.inputs["Mortar"].default_value = c4(srgb((0.66, 0.62, 0.55))); br.inputs["Bias"].default_value = 0.0
    nt.links.new(vec.outputs[0], br.inputs["Vector"])
    n = noise_(nt, co, 3.0, 5, 0.6, loc=(-1500, 300))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 0.25, (-1200, 300)), br.outputs["Color"], (0.6, 0.55, 0.5, 1), (-1000, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, math_(nt, 'SUBTRACT', 1.0, br.outputs["Fac"], (-900, -300)), 0.4, 0.006, (0, -400))
    return m


def cobble_mat(name):
    """Granite setts by the wharf: rounded grey stones, frost and old snow in the joints."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2000, 0))
    mp = node(nt, "ShaderNodeMapping", (-1800, 0)); mp.inputs["Scale"].default_value = (5.0, 7.0, 5.0); nt.links.new(co, mp.inputs["Vector"])
    v = voronoi_(nt, mp.outputs["Vector"], 1.0, 'DISTANCE_TO_EDGE', (-1500, 0))
    vc = voronoi_(nt, mp.outputs["Vector"], 1.0, 'F1', (-1500, -300))
    joint = maprange(nt, v.outputs["Distance"], 0.0, 0.12, 1, 0, (-1300, 0))
    st = ramp(nt, [(0.0, c4(srgb((0.34, 0.33, 0.32)))), (0.5, c4(srgb((0.46, 0.44, 0.42)))), (1.0, c4(srgb((0.55, 0.50, 0.46))))], (-1200, -300))
    nt.links.new(sep_xyz(nt, vc.outputs["Color"], (-1350, -400)).outputs["X"], st.inputs["Fac"])
    sn = maprange(nt, noise_(nt, co, 0.5, 3, 0.5, loc=(-1500, 400)).outputs["Fac"], 0.35, 0.6, 0.4, 1.0, (-1200, 400))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', joint, sn, (-1000, 200)), st.outputs["Color"], c4(srgb((0.86, 0.88, 0.92))), (-800, 0))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, joint, 0, 1, 0.55, 0.8, (-600, -300)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'SUBTRACT', 1.0, joint), 0.6, 0.02, (0, -400))
    return m


def ensign_atlas():
    """The United States ensign of the 1840s: thirteen stripes and a blue canton with rows of white stars. 512x256, row 0 top."""
    W, H = 512, 256; yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    a = np.zeros((H, W, 4), np.float32); a[..., 3] = 1
    stripe = (np.floor(yy / (H / 13)) % 2 == 0)
    a[..., :3] = np.where(stripe[..., None], np.array([0.62, 0.08, 0.08]), np.array([0.92, 0.91, 0.88]))
    can = (xx < 205) & (yy < H * 7 / 13)
    a[can, :3] = (0.06, 0.10, 0.32)
    for r in range(5):
        for c in range(6):
            cx, cy = 18 + c * 34, 14 + r * 26
            a[((xx - cx) ** 2 + (yy - cy) ** 2 < 25) & can, :3] = (0.92, 0.92, 0.90)
    return np_image("A_Ensign", a)


M_SNOW = snow_mat("M_Snow")
M_ROAD = snow_mat("M_RoadSnow", base=(0.82, 0.82, 0.82), ruts=True)
M_WHITE = clapboard_mat("M_ClapboardWhite", (0.88, 0.87, 0.82))
M_GREY = clapboard_mat("M_ClapboardGrey", (0.66, 0.66, 0.62))
M_YELLOW = clapboard_mat("M_ClapboardYellow", (0.84, 0.74, 0.50))
M_BRICK = brick_mat("M_Brick")
M_FOOTWAY = brick_mat("M_Footway", paving=True)
M_COBBLE = cobble_mat("M_Cobbles")
M_TRIM = noisy("M_WhiteTrim", [srgb((0.90, 0.89, 0.85)), srgb((0.84, 0.83, 0.79))], scale=4.0, rough=0.55, bump=0.05)
M_SHUTTER = noisy("M_Shutters", [srgb((0.10, 0.20, 0.13)), srgb((0.13, 0.24, 0.16))], scale=20.0, rough=0.5, bump=0.1, stretch=(1, 1, 20))
M_GRANITE = noisy("M_Granite", [srgb((0.52, 0.51, 0.49)), srgb((0.62, 0.60, 0.58)), srgb((0.42, 0.41, 0.40))], scale=40.0, rough=0.7, bump=0.3)
M_ROOF = noisy("M_RoofShingle", [srgb((0.25, 0.24, 0.23)), srgb((0.32, 0.30, 0.28))], scale=6.0, rough=0.8, bump=0.2)
M_IRON = noisy("M_Iron", [srgb((0.05, 0.05, 0.05)), srgb((0.09, 0.08, 0.07)), srgb((0.04, 0.04, 0.04))], scale=30.0, rough=(0.4, 0.7), metallic=0.7)
M_TIMBER = noisy("M_WharfTimber", [srgb((0.30, 0.26, 0.21)), srgb((0.38, 0.33, 0.27)), srgb((0.22, 0.19, 0.16))], scale=2.0, rough=(0.6, 0.9), bump=0.3, stretch=(6.0, 0.4, 6.0))
M_TAR = noisy("M_TarredWood", [srgb((0.06, 0.05, 0.05)), srgb((0.10, 0.09, 0.08))], scale=5.0, rough=0.6, bump=0.1)
M_HULL = noisy("M_ShipHull", [srgb((0.08, 0.08, 0.08)), srgb((0.13, 0.12, 0.11))], scale=3.0, rough=0.5, bump=0.1, stretch=(0.3, 6, 6))
M_SPAR = noisy("M_Spars", [srgb((0.46, 0.34, 0.21)), srgb((0.54, 0.41, 0.26))], scale=2.0, rough=0.6, bump=0.05)
M_FURL = noisy("M_FurledSails", [srgb((0.80, 0.76, 0.66)), srgb((0.70, 0.66, 0.56))], scale=10.0, rough=0.9, bump=0.3)
M_ROPE = plain("M_TarredRope", srgb((0.06, 0.05, 0.04)), rough=0.7)
M_CASK = noisy("M_Casks", [srgb((0.40, 0.29, 0.18)), srgb((0.48, 0.36, 0.23)), srgb((0.32, 0.23, 0.14))], scale=4.0, rough=(0.55, 0.85), bump=0.1, stretch=(8.0, 8.0, 0.4))
M_CHEST = noisy("M_SeaChests", [srgb((0.20, 0.28, 0.30)), srgb((0.28, 0.34, 0.34)), srgb((0.36, 0.26, 0.18))], scale=5.0, rough=0.6, bump=0.1)
M_SIGN = plain("M_SignBoard", srgb((0.08, 0.10, 0.09)), rough=0.5)
M_GILT = plain("M_Gilt", srgb((0.85, 0.66, 0.32)), rough=0.3, metallic=1.0)
M_WATER = noisy("M_Harbour", [srgb((0.08, 0.14, 0.17)), srgb((0.11, 0.18, 0.21))], scale=0.1, rough=0.12, bump=0.3, bump_dist=0.1)
M_BARK = S.bark_mat("M_MapleBark", base=srgb((0.28, 0.27, 0.25)), dark=srgb((0.12, 0.12, 0.11)), light=srgb((0.40, 0.39, 0.36)), scale=1.4, green=0.15)
IMG_TWIG = S.spray_atlas("A_BareTwigs", [(0.3, 0.3, 0.3)], 51, S=1024, per_cell=2, shape='bare', bark=(0.22, 0.21, 0.19), depth_max=3, branch_p=0.55)
M_TWIG = image_mat("M_BareTwigs", IMG_TWIG, rough=0.85, alpha=True, spec=0.2)
IMG_WIN = window_atlas()
M_WIN = image_mat("M_WindowsDoors", IMG_WIN, rough=0.15, spec=0.6)
M_ENS = image_mat("M_Ensign", ensign_atlas(), rough=0.85)
M_SKY = S.sky_mat(zenith=srgb((0.24, 0.42, 0.74)), horizon=srgb((0.80, 0.84, 0.88)), ground=srgb((0.36, 0.38, 0.40)), sun_dir=SUN_DIR,
                  glow=srgb((1.0, 0.86, 0.66)), glow_k=0.9, glow_pow=10.0, clouds=0.1, cloud_col=srgb((0.97, 0.96, 0.95)),
                  cloud_dark=srgb((0.74, 0.78, 0.84)), cloud_scale=0.6, land=srgb((0.50, 0.54, 0.56)), land_h=0.012, strength=1.0)

# ----------------------------------------------------------------------------- the street: snow roadway (cobbles by the wharf), footways, kerbs
print("ground ...", flush=True)
YS = [-46 + 112 * k / 80 for k in range(81)]
def road_z(x, y): return street_z(y) + ROAD_Z + 0.02 * noise.noise(Vector((x * 0.7, y * 0.7, 0.3))) + 0.03 * (1 - (abs(x) / RX) ** 2)
XS = [-RX + 2 * RX * i / 12 for i in range(13)]
for (mat, y0, y1, nm) in ((M_ROAD, -46.0, 50.0, "Roadway"), (M_COBBLE, 49.5, WHARF_Y, "Cobbles")):
    mb = MB(); ys = [y for y in YS if y0 <= y <= y1]
    if ys[0] > y0: ys = [y0] + ys
    if ys[-1] < y1: ys = ys + [y1]
    rows = [[mb.vert(Vector((x, y, road_z(x, y) + (0.004 if mat is M_COBBLE else 0.0))), (x, y)) for x in XS] for y in ys]
    for j in range(len(ys) - 1):
        for i in range(len(XS) - 1): mb.face(rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i])
    mb.build(nm, mat, sway=False)
fw = MB(); kb = MB(); sb = MB()
for side in (-1, 1):
    xs = [side * (RX + 0.2 + (FX - RX - 0.2) * i / 4) for i in range(5)]
    if side < 0: xs = xs[::-1]
    ys = [y for y in YS if y <= WHARF_Y]
    rows = [[fw.vert(Vector((x, y, street_z(y) + 0.01 * noise.noise(Vector((x, y, 4.0))))), (x, y)) for x in xs] for y in ys]
    for j in range(len(ys) - 1):
        for i in range(4): fw.face(rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i])
    y = -46.0
    while y < WHARF_Y:
        L = rng.uniform(1.4, 2.4)
        mb_box(kb, (side * (RX + 0.1), y + L / 2, street_z(y + L / 2) - 0.08), (0.22, L - 0.015, 0.2), yaw=rng.gauss(0, 0.004))
        y += L
    # snow shovelled off the footway into a low ridge along the kerb, and drifted at the house fronts
    for (x0, w, hh, y_end) in ((side * (RX - 0.25), 0.5, 0.28, 48.0), (side * (FX - 0.2), 0.4, 0.16, 60.0)):
        n = 120; rws = []
        for i in range(n + 1):
            y = -46 + (y_end + 46) * i / n
            ht = hh * (0.6 + 0.4 * noise.noise(Vector((side * 3.0 + x0, y * 0.5, 1.0))))
            if (i // 9) % 4 == 3: ht *= 0.15       # crossings and doorways cleared
            ring = []
            for k in range(6):
                u = k / 5; a = math.pi * u
                ring.append(sb.vert(Vector((x0 - math.cos(a) * w, y, (street_z(y) + (ROAD_Z if abs(x0) < RX else 0.0)) + max(0.0, math.sin(a)) * ht - 0.02)), (u, y)))
            rws.append(ring)
        for ra, rb_ in zip(rws, rws[1:]):
            for k in range(5): sb.face(ra[k], ra[k + 1], rb_[k + 1], rb_[k])
fw.build("Footways", M_FOOTWAY, sway=False)
kb.build("Kerbs", M_GRANITE, sway=False)
sb.build("SnowRidges", M_SNOW, sway=False)
box("SnowField", (500, 500, 0.2), (0, 0, -6.0), M_SNOW)

# ----------------------------------------------------------------------------- houses and stores
print("houses ...", flush=True)
MATS = [M_WHITE, M_GREY, M_YELLOW, M_BRICK, M_TRIM, M_SHUTTER, M_SNOW, M_ROOF, M_WIN, M_GRANITE]
F = {m.name: MB() for m in MATS}
WIN_UV = ((0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)); DOOR_UV = ((0.5, 0.0), (1.0, 0.0), (1.0, 1.0), (0.5, 1.0))
def fpt(side, y, out, z): return Vector((side * (FX - out), y, z))
SIDE = [1]
def tb(mbx, c, size, **kw): mb_box(mbx, c, size, skip=(0, 4 if SIDE[0] > 0 else 5), **kw)
def quad_on(side, mat, y, z0, w, hgt, uv, out=0.012):
    a, b_ = y - w / 2, y + w / 2
    if side < 0: a, b_ = b_, a
    mb_quad(F[mat.name], [fpt(side, a, out, z0), fpt(side, b_, out, z0), fpt(side, b_, out, z0 + hgt), fpt(side, a, out, z0 + hgt)], uv)
def window(side, y, z0, w, hgt, shutters=True, detail=True):
    SIDE[0] = side
    quad_on(side, M_WIN, y, z0, w, hgt, WIN_UV)
    if not detail: return
    T = F["M_WhiteTrim"]
    for yy in (y - w / 2 - 0.06, y + w / 2 + 0.06): tb(T, fpt(side, yy, 0.03, z0 + hgt / 2), (0.06, 0.12, hgt + 0.1))
    tb(T, fpt(side, y, 0.04, z0 + hgt + 0.1), (0.08, w + 0.3, 0.16))
    tb(T, fpt(side, y, 0.05, z0 - 0.04), (0.1, w + 0.26, 0.06))
    tb(F["M_Snow"], fpt(side, y, 0.06, z0 + 0.0), (0.12, w + 0.24, 0.04))
    if shutters:
        for sg in (-1, 1): tb(F["M_Shutters"], fpt(side, y + sg * (w / 2 + 0.38), 0.04, z0 + hgt / 2), (0.04, w / 2 + 0.08, hgt))
def house(side, ya, yb, storeys, mat, kind="house", sign=None, far=False):
    """A New England house or store fronting the street: clapboard or brick, a granite underpinning stepping with the
    slope, a fanlit door, sash windows with green louvred shutters (houses) or small-paned shop windows (stores),
    a cornice, a side-gabled roof of shingle under snow, brick chimneys."""
    W = yb - ya; yc = (ya + yb) / 2; D = 12.0
    zb = street_z(yb); zt = street_z(ya)          # the ground falls from ya (uphill) to yb
    hts = [3.4, 3.1, 2.9][:storeys]; H = sum(hts)
    body = F[mat.name]
    mb_box(body, (side * (FX + D / 2), yc, zb + (zt - zb) + H / 2 - 0.3), (D, W, H + 0.6 + (zt - zb)))
    base = zt                                     # floors are level at the uphill ground
    mb_box(F["M_Granite"], (side * (FX + 0.02), yc, (zb + base) / 2 - 0.15), (0.14, W, base - zb + 0.7))
    SIDE[0] = side
    tb(F["M_WhiteTrim"], fpt(side, yc, 0.15, base + H + 0.2), (0.32, W + 0.04, 0.3))
    for yy in (ya + 0.1, yb - 0.1): tb(F["M_WhiteTrim"], fpt(side, yy, 0.04, base + H / 2), (0.08, 0.22, H))
    pitch = math.radians(34); rh = (D / 2) * math.tan(pitch)
    for (x0, x1) in ((FX - 0.35, FX + D / 2), (FX + D + 0.35, FX + D / 2)):
        p = [Vector((side * x0, ya - 0.1, base + H + 0.32)), Vector((side * x0, yb + 0.1, base + H + 0.32)), Vector((side * x1, yb + 0.1, base + H + 0.32 + rh)), Vector((side * x1, ya - 0.1, base + H + 0.32 + rh))]
        mb_quad(F["M_Snow"], [q + Vector((0, 0, 0.1)) for q in p], ((0, 0), (W, 0), (W, D / 2), (0, D / 2)))
        mb_quad(F["M_RoofShingle"], [p[0], p[1], p[1] + Vector((0, 0, 0.1)), p[0] + Vector((0, 0, 0.1))])
    for e_y in (ya, yb):
        vs = [body.vert(Vector((side * FX, e_y, base + H + 0.3))), body.vert(Vector((side * (FX + D), e_y, base + H + 0.3))), body.vert(Vector((side * (FX + D / 2), e_y, base + H + 0.3 + rh)))]
        body.face(*vs)
    for k in range(max(1, int(W / 8))):
        cy = ya + (k + 0.5) * W / max(1, int(W / 8)); cx = side * (FX + D / 2 + rng.choice((-1.5, 1.5)))
        mb_box(F["M_Brick"], (cx, cy, base + H + rh * 0.7), (0.7, 0.9, rh * 1.2 + 1.2))
        mb_box(F["M_Snow"], (cx, cy, base + H + rh * 1.3 + 0.62), (0.76, 0.96, 0.08))
    nb = max(2, int(round(W / 2.4))); bw = W / nb
    door_bay = nb // 2 if kind == "house" else nb - 1
    for i in range(nb):
        y = ya + (i + 0.5) * bw; z = base
        for s_, hgt in enumerate(hts):
            if s_ == 0:
                if i == door_bay:
                    quad_on(side, M_WIN, y, base, 1.1, 2.6, DOOR_UV)
                    SIDE[0] = side
                    for yy in (y - 0.65, y + 0.65): tb(F["M_WhiteTrim"], fpt(side, yy, 0.06, base + 1.35), (0.12, 0.2, 2.7))
                    tb(F["M_WhiteTrim"], fpt(side, y, 0.1, base + 2.78), (0.2, 1.6, 0.18))
                    for k in range(3): mb_box(F["M_Granite"], fpt(side, y, -0.2 - k * 0.32, base - 0.1 - k * 0.18) - Vector((0, 0, 0)) + Vector((side * (-0.0), 0, 0)), (0.34, 1.5, 0.18))
                elif kind == "store":
                    quad_on(side, M_WIN, y, base + 0.5, bw * 0.8, 2.1, WIN_UV)
                    SIDE[0] = side
                    tb(F["M_WhiteTrim"], fpt(side, y, 0.06, base + 0.45), (0.14, bw * 0.84, 0.1))
                else:
                    window(side, y, base + 0.9, 0.95, 1.75, detail=not far)
            else:
                window(side, y, z + 0.6, 0.9, 1.6 if s_ == 1 else 1.4, detail=not far)
            z += hgt
    if sign:
        txt, sy = sign
        SIDE[0] = side
        tb(F["M_WhiteTrim"], fpt(side, yc, 0.08, base + 3.05), (0.1, W - 0.4, 0.6))
        box(f"SignBoard{ya}", (0.04, W - 0.8, 0.46), tuple(fpt(side, yc, 0.15, base + 3.05)), M_SIGN)
        text_mesh(f"Sign{ya}", txt, tuple(fpt(side, yc, 0.175, base + 3.05)), 0.3, M_GILT, rot=(math.pi / 2, 0, -math.pi / 2 if side > 0 else math.pi / 2))
    return H

north = [(-44, -30, 3, M_BRICK, "house", None), (-30, -18, 2, M_WHITE, "house", None), (-18, -6, 2, M_YELLOW, "house", None),
         (-6, 8, 3, M_BRICK, "store", ("SEA OUTFITS", 0)), (8, 20, 2, M_GREY, "store", ("SHIP CHANDLERY", 0)), (20, 32, 2, M_WHITE, "house", None),
         (32, 46, 3, M_BRICK, "store", None), (46, 58, 2, M_GREY, "store", None), (58, 66, 2, M_WHITE, "store", None)]
south = [(-44, -28, 2, M_WHITE, "house", None), (-28, -14, 3, M_BRICK, "house", None), (-14, -2, 2, M_GREY, "house", None),
         (-2, 12, 2, M_WHITE, "store", ("OIL & CANDLES", 0)), (12, 26, 3, M_BRICK, "store", None), (26, 38, 2, M_YELLOW, "house", None),
         (38, 52, 3, M_BRICK, "store", None), (52, 66, 2, M_GREY, "store", None)]
for (ya, yb, st, m, kind, sign) in north: house(-1, ya, yb, st, m, kind, sign, far=abs(ya) > 40)
for (ya, yb, st, m, kind, sign) in south: house(1, ya, yb, st, m, kind, sign, far=abs(ya) > 40)

# the mansion at the head of the street, uphill behind the reader, in its garden behind the harpoon fence
MZ = street_z(-46.0)
mb_box(F["M_Brick"], (0.0, -62.0, MZ + 6.0), (20.0, 12.0, 12.0))
mb_box(F["M_WhiteTrim"], (0.0, -55.9, MZ + 12.1), (20.4, 0.4, 0.5))
for k in range(4):          # a portico of four columns and a pediment
    cyl(f"MansionCol{k}", 0.32, 7.5, (-3.0 + k * 2.0, -54.6, MZ + 0.6 + 3.75), M_TRIM, verts=14)
box("MansionPorch", (8.4, 3.2, 0.6), (0.0, -54.6, MZ + 0.3), M_GRANITE)
pm = MB()
P = [Vector((-4.3, -53.1, MZ + 8.35)), Vector((4.3, -53.1, MZ + 8.35)), Vector((0.0, -53.1, MZ + 10.6))]
mb_quad(pm, [P[0], P[1], P[2], P[2]])
pm.build("MansionPediment", M_TRIM, sway=False)
box("MansionEntab", (8.8, 3.3, 0.6), (0.0, -54.6, MZ + 8.05), M_TRIM)
for r in range(3):
    for c in range(5):
        if r == 0 and c == 2: continue
        x = -8.0 + c * 4.0; z = MZ + 1.6 + r * 3.6
        P = [Vector((x - 0.55, -55.98, z)), Vector((x + 0.55, -55.98, z)), Vector((x + 0.55, -55.98, z + 2.1)), Vector((x - 0.55, -55.98, z + 2.1))]
        mb_quad(F["M_WindowsDoors"], P, WIN_UV)
P = [Vector((-0.65, -55.98, MZ + 0.6)), Vector((0.65, -55.98, MZ + 0.6)), Vector((0.65, -55.98, MZ + 3.6)), Vector((-0.65, -55.98, MZ + 3.6))]
mb_quad(F["M_WindowsDoors"], P, DOOR_UV)
mb_box(F["M_Snow"], (0.0, -62.0, MZ + 12.15), (20.2, 12.2, 0.2))
for k, mname in F.items(): F[k].build("H_" + k[2:], {m.name: m for m in MATS}[k], sway=False)
# the iron emblematical harpoons: a fence of harpoon-headed pickets on a granite curb
hf = MB()
for x in np.arange(-11.0, 11.01, 0.24):
    if abs(x) < 1.0: continue
    z0 = MZ + 0.3; top = z0 + 1.55
    S_t = Vector((x, -46.5, z0)); T_ = Vector((x, -46.5, top))
    mb_box(hf, (S_t + T_) / 2, (0.03, 0.03, top - z0))
    # the head: a flat barbed iron point (a toggle-less two-flued harpoon)
    hb = T_ + Vector((0, 0, 0.0))
    v0 = hf.vert(hb + Vector((-0.07, 0, 0.0))); v1 = hf.vert(hb + Vector((0.07, 0, 0.0))); v2 = hf.vert(hb + Vector((0, 0, 0.22)))
    v3 = hf.vert(hb + Vector((-0.05, 0, -0.05))); v4 = hf.vert(hb + Vector((0.05, 0, -0.05)))
    v5 = hf.vert(hb + Vector((-0.015, 0, 0.02))); v6 = hf.vert(hb + Vector((0.015, 0, 0.02)))
    hf.face(v0, v1, v2); hf.face(v3, v0, v5); hf.face(v1, v4, v6)
for z in (MZ + 0.5, MZ + 1.45): mb_box(hf, (0.0, -46.5, z), (22.0, 0.025, 0.04))
hf.build("HarpoonFence", M_IRON, sway=False)
box("FenceCurb", (22.4, 0.4, 0.4), (0.0, -46.5, MZ + 0.1), M_GRANITE)
box("Garden", (22.0, 8.0, 0.4), (0.0, -51.0, MZ + 0.1), M_SNOW)

# ----------------------------------------------------------------------------- leafless maples along the footways
print("trees ...", flush=True)
for side in (-1, 1):
    for k, y in enumerate(np.arange(-38.0, 54.0, 11.5)):
        yy = y + rng.uniform(-1.2, 1.2) + (4.5 if side > 0 else 0)
        if abs(yy - 0) < 3 and side < 0: continue
        x = side * (RX + 0.75)
        S.tree(f"Maple{side}{k}", (x, yy, street_z(yy)), rng.uniform(9.0, 12.0), rng.uniform(2.6, 3.4), "maple", 600 + k * 7 + (side > 0), M_BARK, M_TWIG,
               nlimbs=5, detail=0.6 if abs(yy) < 30 else 0.3, cards_per_tip=1, card_size=1.5, fill=10)

# ----------------------------------------------------------------------------- props: sea chests and casks at the outfitter's door, a hand-cart
def cask(name, p, lying=False, rot=0.0, s=1.0):
    prof = [(0.26 * s, 0.0), (0.30 * s, 0.2 * s), (0.31 * s, 0.4 * s), (0.30 * s, 0.6 * s), (0.26 * s, 0.8 * s)]
    o = lathe(name, prof, p, M_CASK, steps=14)
    if lying: o.rotation_euler = (math.pi / 2, 0, rot); o.location.z += 0.3 * s
    for k, zz in enumerate((0.1, 0.7)):
        hp = lathe(f"{name}_h{k}", [(0.29 * s, (zz - 0.025) * s), (0.305 * s, zz * s), (0.29 * s, (zz + 0.025) * s)], p, M_IRON, steps=14)
        if lying: hp.rotation_euler = (math.pi / 2, 0, rot); hp.location.z += 0.3 * s
for k, (x, y) in enumerate(((-6.9, 0.3), (-6.7, 0.95), (-7.1, 2.6))):
    cask(f"Cask{k}", (x, y, street_z(y)), s=1.0)
cask("CaskLying", (-6.4, 1.7, street_z(1.7)), lying=True, rot=0.3)
for k, (x, y, yaw, w) in enumerate(((-7.2, -1.5, 0.05, 1.0), (-7.1, -2.4, -0.1, 0.9), (-7.15, -1.9, 0.0, 0.85))):
    z = street_z(y) + (0.0 if k < 2 else 0.5)
    box(f"SeaChest{k}", (0.55, w, 0.48), (x, y, z + 0.24), M_CHEST, rot=(0, 0, yaw))
    box(f"SeaChestLid{k}", (0.57, w + 0.02, 0.06), (x, y, z + 0.5), M_CHEST, rot=(0, 0, yaw))
    for sg in (-1, 1): tube(f"Becket{k}{sg}", [Vector((x, y + sg * (w / 2 + 0.01), z + 0.3)), Vector((x, y + sg * (w / 2 + 0.06), z + 0.24)), Vector((x, y + sg * (w / 2 + 0.01), z + 0.18))], 0.012, M_ROPE, sides=4)
# a two-wheeled hand-cart, shafts down
HC = Vector((3.4, 9.0, 0)); HC.z = street_z(HC.y) + ROAD_Z
box("CartBed", (1.1, 1.6, 0.06), (HC.x, HC.y, HC.z + 0.62), M_TIMBER, rot=(math.radians(-8), 0, 0.25))
for sg in (-1, 1):
    box(f"CartSide{sg}", (0.04, 1.6, 0.25), (HC.x + sg * 0.53 * math.cos(0.25), HC.y + sg * 0.53 * math.sin(0.25), HC.z + 0.76), M_TIMBER, rot=(math.radians(-8), 0, 0.25))
    wc = HC + Vector((sg * 0.62 * math.cos(0.25), sg * 0.62 * math.sin(0.25), 0.45))
    cyl(f"CartWheel{sg}", 0.45, 0.06, tuple(wc), M_TIMBER, verts=16, rot=(0, math.pi / 2, 0.25))
    tube(f"CartShaft{sg}", [HC + Vector((sg * 0.45 * math.cos(0.25) - 0.2, sg * 0.45 * math.sin(0.25) + 0.75, 0.62)), HC + Vector((sg * 0.42 * math.cos(0.25) - 0.6, sg * 0.42 * math.sin(0.25) + 2.1, 0.05))], 0.035, M_TIMBER, sides=6)
box("CartLoad", (0.8, 0.6, 0.4), (HC.x, HC.y - 0.2, HC.z + 0.85), M_CHEST, rot=(0, 0, 0.3))

# ----------------------------------------------------------------------------- the wharf, spiles, the harbour and two ships alongside
print("wharf and ships ...", flush=True)
WZ = street_z(WHARF_Y)
box("WharfDeck", (70.0, 16.0, 0.3), (0.0, WHARF_Y + 8.0, WZ - 0.15), M_TIMBER)
sp = MB()
for x in np.arange(-34.0, 34.1, 1.6):
    for yy in (WHARF_Y + 16.1,):
        p0 = Vector((x, yy, SEA - 1.0)); p1 = Vector((x, yy, WZ + 0.25 + rng.uniform(-0.05, 0.15)))
        for k in range(6):
            a0, a1 = 2 * math.pi * k / 6, 2 * math.pi * (k + 1) / 6
            r = 0.17
            vs = [sp.vert(p0 + Vector((math.cos(a0) * r, math.sin(a0) * r, 0))), sp.vert(p0 + Vector((math.cos(a1) * r, math.sin(a1) * r, 0))),
                  sp.vert(p1 + Vector((math.cos(a1) * r, math.sin(a1) * r, 0))), sp.vert(p1 + Vector((math.cos(a0) * r, math.sin(a0) * r, 0)))]
            sp.face(*vs)
sp.build("Spiles", M_TAR, sway=False)
box("WharfSnow", (70.0, 10.0, 0.06), (0.0, WHARF_Y + 5.5, WZ + 0.03), M_SNOW)
for k in range(9):
    cask(f"WharfCask{k}", (rng.uniform(-14, -4), WHARF_Y + rng.uniform(3, 12), WZ), lying=rng.random() < 0.4, rot=rng.uniform(0, 3), s=1.0)
water = S.polar_terrain("water.ocean.harbour", lambda x, y: SEA, M_WATER, r_max=900.0, r0=20.0, rings=14, seg=48, centre=(0.0, WHARF_Y + 120.0))

def ship(name, cx, cy, L, B, masts, yaw=0.0):
    """A ship lying alongside: a black hull with a white painted band (the whaler's ports), bulwarks, masts with
    topmasts and yards, the sails furled on them, the standing rigging."""
    R_ = Matrix.Rotation(yaw, 3, 'Z'); C = Vector((cx, cy, SEA))
    def P(x, y, z): return C + R_ @ Vector((x, y, z))
    hm = MB(); rows_ = []
    for j in range(17):
        t = j / 16; y = -L / 2 + L * t
        bb = B / 2 * (1 - abs(2 * t - 1) ** 2.4) ** 0.6 + 0.05
        rows_.append([hm.vert(P(sg * bb * (1 - 0.25 * (1 - zf) ** 2), y, -1.5 + 5.0 * zf + 0.6 * (2 * t - 1) ** 2 * zf)) for sg, zf in
                      ((-1, 1.0), (-1, 0.6), (-1, 0.2), (1, 0.2), (1, 0.6), (1, 1.0))])
    for j in range(16):
        for k in range(5): hm.face(rows_[j][k], rows_[j][k + 1], rows_[j + 1][k + 1], rows_[j + 1][k])
    hm.build(name + "Hull", M_HULL, sway=False)
    bandm = MB()
    for j in range(2, 14):
        for sg in (-1, 1):
            t0, t1 = j / 16, (j + 1) / 16
            def bp(t, z):
                bb = B / 2 * (1 - abs(2 * t - 1) ** 2.4) ** 0.6 + 0.07
                return P(sg * bb, -L / 2 + L * t, z + 0.6 * (2 * t - 1) ** 2)
            q = [bp(t0, 2.6), bp(t1, 2.6), bp(t1, 3.0), bp(t0, 3.0)]
            mb_quad(bandm, q if sg > 0 else [q[1], q[0], q[3], q[2]])
    bandm.build(name + "Band", M_TRIM, sway=False)
    box(name + "Deck", (B * 0.8, L * 0.9, 0.1), tuple(P(0, 0, 3.3)), M_TIMBER, rot=(0, 0, yaw))
    sails = MB()
    for k, (my, mh) in enumerate(masts):
        tube(f"{name}Mast{k}", [P(0, my, 3.3), P(0, my, 3.3 + mh)], [0.3, 0.12], M_SPAR, sides=8)
        for j, zy in enumerate((0.42, 0.68, 0.88)):
            span = B * (2.2 - j * 0.5)
            tube(f"{name}Yard{k}{j}", [P(-span / 2, my + 0.3, 3.3 + mh * zy), P(span / 2, my + 0.3, 3.3 + mh * zy)], 0.11 - 0.02 * j, M_SPAR, sides=6)
            # the sail furled on the yard: a lumpy roll of canvas
            n = 10
            ring_prev = None
            for i in range(n + 1):
                t = i / n; xx = -span / 2 * 0.92 + span * 0.92 * t
                rr = 0.18 * (1 - 0.3 * abs(2 * t - 1)) + 0.03 * math.sin(i * 2.1)
                ring = [sails.vert(P(xx, my + 0.3 + math.cos(a) * rr, 3.3 + mh * zy - 0.12 + math.sin(a) * rr), (t, a), 0.1) for a in np.linspace(0, 2 * math.pi, 7)[:-1]]
                if ring_prev:
                    for q in range(6): sails.face(ring_prev[q], ring_prev[(q + 1) % 6], ring[(q + 1) % 6], ring[q])
                ring_prev = ring
        for sg in (-1, 1):
            for q in range(4):
                tube(f"{name}Shroud{k}{sg}{q}", [P(sg * B / 2, my - 1.0 + q * 0.6, 3.4), P(sg * 0.3, my, 3.3 + mh * 0.6)], 0.025, M_ROPE, sides=3)
    tube(f"{name}Bowsprit", [P(0, L / 2 - 1, 4.0), P(0, L / 2 + 7, 6.5)], [0.25, 0.1], M_SPAR, sides=6)
    tube(f"{name}Stay", [P(0, masts[0][0], 3.3 + masts[0][1] * 0.95), P(0, L / 2 + 7, 6.5)], 0.03, M_ROPE, sides=3)
    if len(masts) > 1:
        tube(f"{name}Stay2", [P(0, masts[1][0], 3.3 + masts[1][1] * 0.95), P(0, masts[0][0], 3.3 + masts[0][1] * 0.75)], 0.03, M_ROPE, sides=3)
    sails.build(name + "Furled", M_FURL)
    return P
P1 = ship("Whaler", 8.0, WHARF_Y + 22.5, 32.0, 8.0, [(9.0, 26.0), (-1.0, 28.0), (-10.0, 22.0)], yaw=math.pi / 2)
P2 = ship("Brig", -24.0, WHARF_Y + 21.5, 24.0, 7.0, [(5.0, 22.0), (-4.0, 23.0)], yaw=math.pi / 2 + 0.05)
# the whaler's ensign at the mizzen peak
fm = MB(); top_ = P1(0, -14.5, 3.3 + 22 * 0.9)
for i in range(8):
    t0, t1 = i / 8, (i + 1) / 8
    def Pf(t, z): return top_ + Vector((-2.6 * t, 0.15 * math.sin(t * 5), z - 0.25 * t))
    vs = [fm.vert(Pf(t0, 0.0), (t0, 1), t0), fm.vert(Pf(t1, 0.0), (t1, 1), t1), fm.vert(Pf(t1, -1.4), (t1, 0), t1), fm.vert(Pf(t0, -1.4), (t0, 0), t0)]
    fm.face(*vs)
fm.build("cloth.flag.ensign", M_ENS)

# ----------------------------------------------------------------------------- sky, light, anchors, sounds
SKY = S.sky_dome(M_SKY, radius=1100.0)
S.world(SUN_DIR, sun_energy=4.2, sun_col=(1.0, 0.86, 0.68), sun_angle=0.6,
        sky_cols=(srgb((0.66, 0.68, 0.72)), srgb((0.78, 0.82, 0.88)), srgb((0.26, 0.44, 0.78))), sky_strength=1.25)
eye, fwd = S.reader((READER.x, READER.y, road_z(READER.x, READER.y)), YAW)
anchor("scene.centre", (0.0, 20.0, street_z(20.0)))
anchor("wharf", (0.0, WHARF_Y, WZ))
anchor("mansion", (0.0, -56.0, MZ))
sound("gulls", "wharf", (0.0, WHARF_Y + 15.0, WZ + 8.0))
sound("rigging", "whaler", tuple(P1(0, 0, 15.0)))
sound("crowd", "outfitter", (-FX + 1.0, 1.0, street_z(1.0) + 1.5))
sound("wind", "street", (0.0, 30.0, street_z(30.0) + 3.0))
page = S.page_preview(eye, fwd)
cams = S.view_cams(eye, YAW, extra=[
    ("Cam_Page", eye, eye + fwd * 10 + Vector((0, 0, -1.2)), 17),
    ("Cam_Store", Vector((-3.0, -3.0, eye.z)), Vector((-FX, 2.0, street_z(2.0) + 1.6)), 24),
    ("Cam_Harpoons", Vector((0.0, -40.0, MZ + 1.6)), Vector((0.0, -50.0, MZ + 2.5)), 22),
    ("Cam_Wharf", Vector((2.0, 46.0, street_z(46.0) + 1.6)), Vector((0.0, WHARF_Y + 20.0, WZ + 6.0)), 20),
])
S.finish(ARGS, cams, "new_bedford_dock_street.gltf", page=page,
         keep_names={"M_BareTwigs": "veg.crown.maples", "M_FurledSails": "cloth.sail.furled", "M_Ensign": "cloth.flag.ensign", "M_Harbour": "water.ocean.harbour"},
         size_for={"M_RoadSnow": (2048, 256, 1024), "M_Footway": (1024, 128, 512), "M_Snow": (1024, 128, 512), "M_Cobbles": (1024, 128, 512),
                   "M_ClapboardWhite": (1024, 128, 512), "M_ClapboardGrey": (1024, 128, 512), "M_ClapboardYellow": (1024, 128, 512), "M_Brick": (2048, 128, 1024),
                   "M_WhiteTrim": (1024, 128, 256), "M_Shutters": (512, 64, 256), "M_Granite": (512, 64, 256), "M_RoofShingle": (256, 64),
                   "M_MapleBark": (512, 128, 256), "M_WharfTimber": (512, 64, 256), "M_TarredWood": (256, 64), "M_ShipHull": (512, 64, 256), "M_Spars": (256, 64),
                   "M_FurledSails": (256, 64), "M_Harbour": (512, 64), "M_SkyDome": (1024,), "M_Casks": (256, 64, 128), "M_SeaChests": (256, 64, 128)},
         default_size=(256, 64, 128), no_shadow={"M_SkyDome"})
