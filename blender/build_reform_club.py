"""
Fable: the card-room of the Reform Club, Pall Mall, on the evening of 2 October 1872 (Around the World in Eighty Days,
chapters 3 and 37).

"Phileas Fogg ... went to the Reform Club ... At half-past seven ... the whist-table" ... "'I will bet twenty thousand
pounds against anyone who wishes, that I will make the tour of the world in eighty days or less' ... The clock
indicated twenty minutes to nine." And on his return: "the clock of the great saloon pointed to a quarter before nine".

A tall first-floor club room in Barry's palazzo, on an October evening just after the gas has been lit, as if the
whist party has only stepped through to the saloon. Polished oak wainscot to 1.4 m with fielded panels, crimson
damask above, a coffered plaster ceiling; a black-and-white veined marble chimney-piece with a coal fire and a gilt
overmantel glass on the west wall; two tall plate-glass sash windows to Pall Mall on the east wall, the crimson
curtains half drawn, the street outside in blue twilight with the gas lamps lit and the club-houses opposite showing
lamplit windows; on the north wall a long mahogany sideboard with the evening papers under a dark marine painting,
and a mahogany longcase clock with a white dial at a quarter to nine. The whist table stands left of the reader under
the six-light gasolier, the cards left mid-rubber, the trump turned; two buttoned leather club chairs face the fire;
a third, with a dropped newspaper, stands near the reader. Behind: the door and a wall of books. No people.

Light: the gasolier (warm white, the brightest), two gas brackets beside the chimney-piece, the fire (low, orange),
and cool twilight at the windows. Exposure is set for the page; the corners stay in a warm, readable gloom.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet (floor, z = 0), facing +Y (north)
  anchor.reader.look      eye height (1.55 m), 1 m ahead
  anchor.scene.centre     the whist table
  anchor.room.fireplace, anchor.room.whistTable, anchor.room.clock, anchor.room.window, anchor.room.door
  Lamp.gasolier, Lamp.bracketN, Lamp.bracketS, Lamp.fire, Lamp.dusk   (POINT; FableBuild's indoor block keeps "Lamp*")
  fx.fire.hearth (base of the coal fire; custom property radius)
  sound.fire.hearth, sound.clock.longcase
  MESH_Embers (emissive coals), MESH_GasGlobes (emissive globes), WindowGlass_* (plate glass, FableBuild glass),
  far.PallMall (the street seen through the windows: an emissive painted backdrop 30 m outside; hidden as backdrop in diorama)

Register the scene as indoor (not Outdoor). Axes: metres, Blender +Z up, the reader faces +Y.

Run headless:
  blender -b -P blender/build_reform_club.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_reform_club.py -- --render --samples 48 --res 1400 --captures captures/blender/reform-club
  blender -b -P blender/build_reform_club.py -- --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
import pride_interior as I
import eighty_kit as E8
from eighty_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                        wood, noisy, plain, image_mat, np_image, box, cyl, sphere, lathe, tube, sweep, mesh_from, Frame,
                        anchor, fx, sound, light_obj, camera, link)

ARGS = K.setup("reform-club", "out/reform-club", 1872, "ReformClub", default_samples=48)
OUT = K.OUT; scene = K.scene
rng = random.Random(1872)
scene.cycles.max_bounces = 10; scene.cycles.diffuse_bounces = 6

EYE = 1.55
R = I.Room(-4.2, 4.4, -3.2, 5.6, 4.8, t=0.45)
READER = Vector((0.55, -0.85, 0.0))
WAINSCOT = 1.42

# ----------------------------------------------------------------------------- materials
M_DAMASK = I.silk("M_WallDamask", K.srgb((0.30, 0.065, 0.06)), K.srgb((0.36, 0.10, 0.08)), damask=0.4, sheen=0.3, rough=0.8)
M_OAK = wood("M_OakPanelling", base=(0.16, 0.085, 0.035), dark=(0.05, 0.025, 0.01), light=(0.27, 0.15, 0.065), scale=1.1, rough=(0.3, 0.5),
             grain_dir=(1, 1, 9), coat=0.25, ao=0.3, bump=0.12)
M_PLASTER = I.joinery_mat("M_Plaster", K.srgb((0.80, 0.74, 0.60)), rough=0.6)
M_CEIL = I.paint_mat("M_CeilingPanels", K.srgb((0.70, 0.64, 0.52)), rough=0.85, dirt=0.0)
M_GILT = I.gilt("M_Gilt")
M_MAHOG = I.mahogany("M_Mahogany")
M_FLOOR = I.boards_mat("M_FloorBoards", light=(0.22, 0.13, 0.06), dark=(0.09, 0.05, 0.02))
M_CARPET = I.carpet_mat("M_TurkeyCarpet", -0.2, 1.3, 3.2, 3.0, field=(0.13, 0.022, 0.016), ground2=(0.018, 0.03, 0.065),
                        border=(0.022, 0.032, 0.07), buff=(0.20, 0.13, 0.07))
M_MARBLE = I.marble("M_BlackMarble", base=(0.035, 0.034, 0.033), vein=(0.42, 0.41, 0.39))
M_IRON = noisy("M_Iron", [(0.010, 0.010, 0.011), (0.022, 0.021, 0.021), (0.016, 0.015, 0.014)], scale=30, rough=(0.45, 0.7), metallic=0.35)
M_SOOT = plain("M_Soot", (0.012, 0.011, 0.01), rough=0.95)
M_BRASS = plain("M_Brass", (0.70, 0.52, 0.27), rough=0.28, metallic=1.0)
M_MIRROR = plain("M_Mirror", (0.70, 0.70, 0.68), rough=0.05, metallic=1.0)
M_GLASS = plain("M_WindowGlass", (0.85, 0.88, 0.90), rough=0.02, transmission=1.0)
M_BAIZE = noisy("M_Baize", [K.srgb((0.08, 0.24, 0.12)), K.srgb((0.10, 0.28, 0.14)), K.srgb((0.07, 0.21, 0.11))], scale=60, rough=0.95, bump=0.1, sheen=0.5)
M_CHAIRLEATHER = noisy("M_ChairLeather", [K.srgb((0.22, 0.10, 0.06)), K.srgb((0.30, 0.14, 0.08)), K.srgb((0.18, 0.08, 0.05))], scale=18, rough=(0.4, 0.6), bump=0.15, bump_dist=0.001)
M_DIAL = plain("M_ClockDial", K.srgb((0.86, 0.84, 0.78)), rough=0.35)
M_BLACK = plain("M_BlackPaint", (0.012, 0.011, 0.01), rough=0.4)
M_PAPERBLANK = plain("M_ScoreCard", K.srgb((0.86, 0.83, 0.74)), rough=0.85)


def leather_mat(name="M_ClubLeather"):
    """Buttoned oxblood hide on the club chairs: deep-buttoned diamonds (voronoi), creased and rubbed paler on the
    high spots, darker in the folds, a waxed low sheen."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 13.0, 'F1', (-1200, 0))
    hollow = maprange(nt, v.outputs["Distance"], 0.0, 0.32, 0, 1, (-1000, 0), 'SMOOTHSTEP')
    n = noise_(nt, co, 7.0, 6, 0.6, loc=(-1200, -300))
    cr = noise_(nt, co, 40.0, 4, 0.65, distortion=1.5, loc=(-1200, -550))
    base = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-900, -300)), c4(K.srgb((0.19, 0.06, 0.035))), c4(K.srgb((0.26, 0.085, 0.045))), (-800, -200))
    rub = math_(nt, 'MULTIPLY', maprange(nt, hollow, 0.55, 1.0, 0, 1, (-800, 100)), maprange(nt, n.outputs["Fac"], 0.45, 0.7, 0.0, 0.5, (-800, 250)), (-650, 150))
    col = mix_rgb(nt, 'MIX', rub, base, c4(K.srgb((0.34, 0.16, 0.09))), (-500, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, hollow, 0.0, 0.35, 0.45, 1.0, (-650, -100)), (-350, 0))
    col = K.ao_mul(nt, col, 0.1, 0.5, (-250, -600))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, rub, 0, 0.5, 0.42, 0.3, (-300, -250)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'ADD', hollow, math_(nt, 'MULTIPLY', cr.outputs["Fac"], 0.25, (-500, -550)), (-350, -500)), 0.35, 0.008)
    return m
M_LEATHER = leather_mat()


def newsprint_mat(name="M_Newsprint"):
    """Evening papers seen from a metre or two: off-white newsprint, six columns of grey text lines with gutters and
    rules, headings and a few block advertisements (lines run along world X; the papers lie square to the room)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1600, 0))
    col_f = math_(nt, 'FRACT', math_(nt, 'DIVIDE', s.outputs["X"], 0.062, (-1400, 200)), None, (-1300, 200))
    gutter = maprange(nt, col_f, 0.0, 0.06, 0, 1, (-1200, 200))
    line_f = math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', s.outputs["Y"], s.outputs["Z"], (-1450, 0)), 0.0036, (-1400, 0)), None, (-1300, 0))
    ln = maprange(nt, line_f, 0.2, 0.35, 1, 0, (-1200, 0))
    words = noise_(nt, co, 700.0, 2, 0.5, loc=(-1300, -200))
    ln = math_(nt, 'MULTIPLY', ln, maprange(nt, words.outputs["Fac"], 0.4, 0.48, 0.0, 1.0, (-1100, -200)), (-1000, -100))
    blocks = noise_(nt, co, 14.0, 2, 0.5, loc=(-1300, -450))
    heads = maprange(nt, blocks.outputs["Fac"], 0.70, 0.71, 0, 1, (-1100, -450))
    rule = maprange(nt, math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', s.outputs["Y"], s.outputs["Z"], (-1450, -650)), 0.11, (-1350, -650)), None, (-1250, -650)), 0.0, 0.02, 1, 0, (-1100, -650))
    heads = math_(nt, 'MAXIMUM', heads, math_(nt, 'MULTIPLY', rule, 0.6, (-1000, -650)), (-950, -500))
    ink = math_(nt, 'ADD', 0.30, math_(nt, 'MULTIPLY', ln, 0.35, (-900, -100)), (-850, -100))
    ink = math_(nt, 'MAXIMUM', ink, math_(nt, 'MULTIPLY', heads, 0.85, (-900, -400)), (-800, -200))
    ink = math_(nt, 'MULTIPLY', ink, gutter, (-700, -100))
    yel = noise_(nt, co, 3.0, 3, 0.5, loc=(-1300, 400))
    paper = mix_rgb(nt, 'MIX', maprange(nt, yel.outputs["Fac"], 0.35, 0.65, 0, 1, (-1100, 400)), c4(K.srgb((0.80, 0.77, 0.68))), c4(K.srgb((0.74, 0.70, 0.60))), (-900, 400))
    col = mix_rgb(nt, 'MIX', ink, paper, (0.06, 0.06, 0.06, 1), (-500, 200))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
    b.inputs["Sheen Weight"].default_value = 0.2
    return m
M_NEWS = newsprint_mat()


def embers_mat(name="M_Embers"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 28.0, 'DISTANCE_TO_EDGE', (-900, 0))
    glow = maprange(nt, v.outputs["Distance"], 0.0, 0.08, 1, 0, (-700, 0))
    n = noise_(nt, co, 9.0, 4, 0.6, loc=(-900, -250))
    glow = math_(nt, 'MULTIPLY', glow, maprange(nt, n.outputs["Fac"], 0.35, 0.65, 0.2, 1.0, (-700, -250)), (-500, -100))
    col = mix_rgb(nt, 'MIX', glow, (0.02, 0.018, 0.016, 1), (0.9, 0.28, 0.05, 1), (-300, 0))
    nt.links.new(col, b.inputs["Base Color"])
    ec = mix_rgb(nt, 'MULTIPLY', 1.0, (1.0, 0.33, 0.06, 1), glow, (-300, -300))
    nt.links.new(ec, b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 3.5
    b.inputs["Roughness"].default_value = 0.9
    return m
M_EMBERS = embers_mat()
M_GLOBE = plain("M_GasGlobes", (0.95, 0.90, 0.80), rough=0.4, emission=(1.0, 0.84, 0.60), strength=4.5)

# ----------------------------------------------------------------------------- painted images: the street outside, the marine painting
def paint_pallmall(W=2048, H=1024):
    """Pall Mall at dusk from a first-floor window: the club-houses opposite (stone, three storeys and an attic
    balustrade, tall windows, several lit), the gas lamps along the pavement, wet setts with their reflections, and
    the blue twilight sky above. Plane: y -30..30 m (u), z -9..21 m (v), 30 m beyond the window wall."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    z = 21.0 - yy / H * 30.0                      # metres relative to the room floor (street at -5.5)
    y = -30.0 + xx / W * 60.0
    img = np.zeros((H, W, 4), np.float32); img[..., 3] = 1.0
    # sky: deep blue overhead, paler and greener near the skyline, a last pink-amber band low to the west (left)
    t = np.clip((z - 9.0) / 12.0, 0, 1)
    sky = (np.array([0.11, 0.15, 0.26]) * (1 - t)[..., None] + np.array([0.025, 0.04, 0.10]) * t[..., None])
    west = np.clip((-y - 5.0) / 25.0, 0, 1) * np.clip(1 - (z - 9.0) / 6.0, 0, 1)
    sky = sky + west[..., None] * np.array([0.10, 0.05, 0.03])
    img[..., :3] = sky
    rs = np.random.RandomState(4)
    # the club-houses: two fronts with a lane between, parapets at 10.5-11.5 m, cornices, rusticated ground floor
    top = np.where(y < 4.0, 11.2, 10.4) + np.where((y > 3.0) & (y < 6.5), -16.0, 0.0)
    stone = (z < top) & (z > -5.5)
    hz = np.clip((z + 5.5) / 16.0, 0, 1)
    sc = np.array([0.050, 0.050, 0.058]) * (1 - hz)[..., None] * 0.6 + np.array([0.040, 0.044, 0.060])
    n = (np.sin(xx * 0.9) * 0.0 + rs.rand(H, W) * 0.006)
    img[..., :3] = np.where(stone[..., None], sc + n[..., None], img[..., :3])
    # string courses and cornices (pale lines)
    for zc in (-0.6, 4.6, 9.6):
        band = stone & (np.abs(z - zc) < 0.18)
        img[band, :3] = np.array([0.075, 0.078, 0.092])
    # windows: tall, regular, a few lit warm (gaslight behind blinds), the rest dark glass reflecting the sky
    for (y0, y1, pitch) in ((-30.0, 3.0, 3.1), (6.5, 30.0, 3.4)):
        k = 0; yc = y0 + 1.6
        while yc < y1 - 1.0:
            for (zb, zt) in ((-4.2, -1.4), (0.6, 3.8), (5.6, 8.6)):
                m = (np.abs(y - yc) < 0.62) & (z > zb) & (z < zt)
                lit = rs.rand() < (0.45 if zb < 5 else 0.25)
                if lit:
                    warm = np.array([0.95, 0.62, 0.28]) * rs.uniform(0.5, 1.0)
                    glow = warm * (0.65 + 0.35 * np.clip((zt - z) / (zt - zb), 0, 1))[..., None]
                    img[m, :3] = glow[m]
                    # glazing bars
                    bars = m & ((np.abs(y - yc) < 0.04) | (np.abs(z - (zb + zt) / 2) < 0.05))
                    img[bars, :3] *= 0.2
                else:
                    img[m, :3] = np.array([0.025, 0.035, 0.07]) + (rs.rand() * 0.02)
                # pediment / hood over each window
                hood = (np.abs(y - yc) < 0.85) & (np.abs(z - (zt + 0.3)) < 0.12)
                img[hood, :3] = np.array([0.07, 0.072, 0.085])
            yc += pitch; k += 1
    # the street and the far pavement: wet, dark, reflecting the lamps
    street = z <= -5.5
    img[street, :3] = np.array([0.020, 0.022, 0.030])
    # the gas lamps along the near and far kerbs: glowing lanterns with soft halos, and their reflections
    for yl in np.arange(-27.0, 30.0, 9.5):
        for (zl, scale) in ((-1.6, 1.0),):
            d2 = (y - yl) ** 2 + (z - zl) ** 2
            halo = np.exp(-d2 / 0.5) * 0.18 + np.exp(-d2 / 0.012) * 1.6
            img[..., :3] += halo[..., None] * np.array([1.0, 0.78, 0.45])
            post = (np.abs(y - yl) < 0.06) & (z < zl - 0.2) & (z > -5.5)
            img[post, :3] = np.array([0.015, 0.015, 0.018])
            refl = street * np.exp(-((y - yl) ** 2) / 0.15) * np.exp(-((z + 5.5) ** 2) / 4.0) * 0.5
            img[..., :3] += refl[..., None] * np.array([1.0, 0.75, 0.4])
            # light pooled on the stone behind
            pool = stone * np.exp(-((y - yl) ** 2) / 8.0) * np.exp(-((z - zl) ** 2) / 10.0) * 0.06
            img[..., :3] += pool[..., None] * np.array([1.0, 0.75, 0.45])
    img[..., :3] = np.clip(img[..., :3], 0, 4.0)
    return np_image("A_PallMall", img)


def paint_marine(W=768, H=512):
    """A dark marine painting under old varnish: a full-rigged ship running before a squall, a grey-green sea with
    white crests, a break of light low on the horizon. No people."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = xx / W; v = 1 - yy / H
    rs = np.random.RandomState(9)
    img = np.zeros((H, W, 4), np.float32); img[..., 3] = 1
    hor = 0.36
    def fbm(scale, oct=5, seed=0):
        acc = np.zeros((H, W), np.float32); amp = 1.0; tot = 0
        r = np.random.RandomState(seed)
        for o in range(oct):
            g = r.rand(int(scale * 2 ** o) + 2, int(scale * 2 ** o * W / H) + 2).astype(np.float32)
            gy = v * (g.shape[0] - 1); gx = u * (g.shape[1] - 1)
            y0 = np.floor(gy).astype(int); x0 = np.floor(gx).astype(int)
            fy = gy - y0; fx = gx - x0; y1 = np.minimum(y0 + 1, g.shape[0] - 1); x1 = np.minimum(x0 + 1, g.shape[1] - 1)
            fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
            val = (g[y0, x0] * (1 - fx) + g[y0, x1] * fx) * (1 - fy) + (g[y1, x0] * (1 - fx) + g[y1, x1] * fx) * fy
            acc += val * amp; tot += amp; amp *= 0.5
        return acc / tot
    cl = fbm(3, 5, 1)
    sky = np.where((v > hor)[..., None], (np.array([0.20, 0.19, 0.15]) + (cl[..., None] - 0.5) * np.array([0.25, 0.23, 0.18])), 0)
    brk = np.exp(-((v - hor - 0.06) ** 2) / 0.002) * np.exp(-((u - 0.7) ** 2) / 0.03)
    sky = sky + (v > hor)[..., None] * brk[..., None] * np.array([0.35, 0.30, 0.18])
    sea_n = fbm(6, 5, 2)
    sea = (v <= hor)[..., None] * (np.array([0.06, 0.08, 0.06]) + (sea_n[..., None] - 0.5) * 0.10)
    crest = (v <= hor) & (sea_n > 0.66)
    img[..., :3] = sky + sea
    img[crest, :3] = img[crest, :3] * 0.4 + np.array([0.42, 0.42, 0.36]) * 0.6
    # the ship: dark hull, three masts with sails (pale, warm), heeling a little
    cx, base = 0.40, hor - 0.02
    hull = (np.abs(u - cx) < 0.11 - (base + 0.035 - v) * 0.6) & (v > base - 0.01) & (v < base + 0.035)
    img[hull, :3] = np.array([0.04, 0.035, 0.03])
    for k, mx in enumerate((cx - 0.07, cx, cx + 0.065)):
        hgt = (0.36, 0.42, 0.33)[k]
        mast = (np.abs(u - (mx + (v - base) * 0.08)) < 0.0025) & (v > base + 0.03) & (v < base + hgt)
        img[mast, :3] = np.array([0.05, 0.04, 0.03])
        for j in range(4):
            sb = base + 0.06 + j * hgt / 4.6; st = sb + hgt / 5.2; w = 0.05 - j * 0.008
            sail = (v > sb) & (v < st) & (np.abs(u - (mx + (v - base) * 0.08) - 0.006) < w * (1 - 0.15 * (v - sb) / (st - sb)))
            shade = 0.55 + 0.45 * np.clip((u - mx + w) / (2 * w), 0, 1)
            img[sail, :3] = (np.array([0.62, 0.56, 0.42]) * shade[..., None])[sail]
    # varnish and craquelure
    img[..., :3] = img[..., :3] * np.array([0.92, 0.80, 0.55])
    img[..., :3] *= (0.92 + 0.08 * rs.rand(H, W))[..., None]
    return np_image("A_MarinePainting", np.clip(img, 0, 1))


def emissive_image_mat(name, img, strength=1.0):
    m, nt, b = new_mat(name)
    uv = node(nt, "ShaderNodeUVMap", (-900, 0)); uv.uv_map = "UVMap"
    t = node(nt, "ShaderNodeTexImage", (-600, 0)); t.image = img; t.extension = 'EXTEND'
    nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    nt.links.new(t.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = strength
    b.inputs["Base Color"].default_value = (0, 0, 0, 1); b.inputs["Roughness"].default_value = 1.0
    K.IMAGE_MATS.add(name)
    return m

print("painting ...", flush=True)
M_PALLMALL = emissive_image_mat("M_PallMall", paint_pallmall(), 1.0)
M_MARINE = image_mat("M_MarinePainting", paint_marine(), rough=0.3)

# ----------------------------------------------------------------------------- openings, then walls
# east wall (runs from y0 north): u = y - y0
WIN_Y = [-0.15, 3.05]
M_CURTAIN = I.silk("M_Curtains", K.srgb((0.36, 0.05, 0.05)), K.srgb((0.44, 0.08, 0.07)), damask=0.0, sheen=0.6, rough=0.8)
for k, y in enumerate(WIN_Y):
    I.sash_window(f"Win{k}", R, 'E', y - R.y0, 1.32, 0.72, 3.0, M_PLASTER, M_GLASS, M_OAK, panes=(2, 4),
                  curtain_mat=M_CURTAIN, pelmet_mat=M_GILT, drawn=0.3)
# south wall (runs from x0 east): u = x - x0; the door to the saloon
DOOR_X = -1.7
I.six_panel_door("Door", R, 'S', DOOR_X - R.x0, 1.15, 2.75, M_MAHOG, M_OAK, M_BRASS, open_deg=0.0, hinge_left=True)
I.build_walls(R, M_DAMASK)
FP_Y = 1.55
R.openings['W'].append((R.y1 - FP_Y, 2.16, 0.0, 1.48, "chimneypiece"))     # after the walls: stops the wainscot, not the wall

# the backdrop: Pall Mall at dusk, 30 m outside the window wall
PM_X = R.x1 + R.t + 30.0
mesh_from("PallMall", [(PM_X, -30.0, -9.0), (PM_X, 30.0, -9.0), (PM_X, 30.0, 21.0), (PM_X, -30.0, 21.0)], [(0, 3, 2, 1)], M_PALLMALL,
          uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])

# floor, carpet, ceiling
box("Floor", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.04), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, -0.02), M_FLOOR)
box("Carpet", (6.4, 6.0, 0.012), (-0.2, 1.3, 0.006), M_CARPET, bevel=0.004)
box("Ceiling", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.05), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, R.h + 0.025), M_CEIL)
# coffers: a grid of deep moulded beams, gilt fillets at their soffits
CX = [R.x0 + 0.35 + i * (R.x1 - R.x0 - 0.7) / 5 for i in range(6)]
CY = [R.y0 + 0.35 + j * (R.y1 - R.y0 - 0.7) / 5 for j in range(6)]
for i, x in enumerate(CX):
    box(f"BeamX{i}", (0.26, R.y1 - R.y0, 0.26), (x, (R.y0 + R.y1) / 2, R.h - 0.13), M_PLASTER, bevel=0.03)
    box(f"BeamXg{i}", (0.06, R.y1 - R.y0 - 0.1, 0.012), (x, (R.y0 + R.y1) / 2, R.h - 0.262), M_GILT)
for j, y in enumerate(CY):
    box(f"BeamY{j}", (R.x1 - R.x0, 0.26, 0.24), ((R.x0 + R.x1) / 2, y, R.h - 0.12), M_PLASTER, bevel=0.03)
    box(f"BeamYg{j}", (R.x1 - R.x0 - 0.1, 0.06, 0.012), ((R.x0 + R.x1) / 2, y, R.h - 0.262), M_GILT)

# mouldings: skirting, wainscot (oak, fielded panels), dado rail, cornice and gilt bead
I.moulding_runs(R, "Skirting", I.skirting_profile(0.28), 0.0, M_OAK)
for w in ('S', 'E', 'N', 'W'):
    o, a, n, L = R.wall_frame(w)
    for k, (u0, u1) in enumerate(I.runs(R, w, 0.0, WAINSCOT)):
        c = o + a * ((u0 + u1) / 2) + n * 0.012 + Vector((0, 0, WAINSCOT / 2))
        box(f"Wainscot{w}{k}", (abs(a.x) * (u1 - u0) + abs(n.x) * 0.024, abs(a.y) * (u1 - u0) + abs(n.y) * 0.024, WAINSCOT), tuple(c), M_OAK)
I.dado_panels(R, M_OAK, rail_z=WAINSCOT, skirt=0.28, step=0.95)
for w in ('S', 'E', 'N', 'W'):
    o, a, n, L = R.wall_frame(w)
    for k, (u0, u1) in enumerate(I.runs(R, w, 0.4, WAINSCOT - 0.1, 0.08)):
        span = u1 - u0; np_ = max(1, int(round(span / 0.95)))
        if span < 0.5: continue
        pw = span / np_
        for i in range(np_):
            c0 = u0 + i * pw + 0.16; c1 = u0 + (i + 1) * pw - 0.16
            c = o + a * ((c0 + c1) / 2) + n * 0.03 + Vector((0, 0, (0.28 + 0.1 + WAINSCOT - 0.12) / 2))
            box(f"Field{w}{k}{i}", (abs(a.x) * (c1 - c0) + abs(n.x) * 0.02, abs(a.y) * (c1 - c0) + abs(n.y) * 0.02, WAINSCOT - 0.12 - 0.38 - 0.12), tuple(c), M_OAK, bevel=0.02)
I.moulding_runs(R, "DadoRail", [(0.0, -0.06), (0.03, -0.06), (0.045, -0.035), (0.05, 0.0), (0.04, 0.025), (0.0, 0.03)], WAINSCOT, M_OAK, z_band=(WAINSCOT - 0.06, WAINSCOT + 0.03))
I.moulding_runs(R, "Cornice", I.cornice_profile(0.34, 0.42), R.h, M_PLASTER, z_band=(R.h - 0.42, R.h))
I.moulding_runs(R, "CorniceBead", [(0.0, -0.03), (0.03, -0.03), (0.035, -0.015), (0.03, 0.0), (0.0, 0.0)], R.h - 0.42, M_GILT, z_band=(R.h - 0.45, R.h - 0.42))

# ----------------------------------------------------------------------------- the chimney-piece, grate and fire (west wall)
F = Frame((R.x0, FP_Y), math.atan2(-1, 0))     # local +Y -> world +X (into the room)
def FP(x, y, z): return F.p(x, y, z)
OW, OH = 0.98, 0.98
F.box("HearthStone", (2.0, 0.6, 0.04), (0, 0.3, 0.02), M_MARBLE, bevel=0.004)
for sx in (-1, 1):
    # consoles: scrolled brackets as stacked blocks, a tall plain jamb behind
    F.box(f"Jamb{sx}", (0.30, 0.18, OH + 0.04), (sx * (OW / 2 + 0.15), 0.09, (OH + 0.04) / 2), M_MARBLE, bevel=0.006)
    F.box(f"Console{sx}", (0.2, 0.12, 0.8), (sx * (OW / 2 + 0.15), 0.22, 0.5), M_MARBLE, bevel=0.03)
    cyl(f"ConsoleScroll{sx}", 0.08, 0.2, FP(sx * (OW / 2 + 0.15), 0.25, OH - 0.02), M_MARBLE, verts=14, rot=(0, math.pi / 2, F.yaw))
    F.box(f"Plinth{sx}", (0.34, 0.24, 0.12), (sx * (OW / 2 + 0.15), 0.12, 0.06), M_MARBLE, bevel=0.01)
F.box("Frieze", (OW + 0.6, 0.17, 0.26), (0, 0.085, OH + 0.13), M_MARBLE, bevel=0.006)
F.box("Shelf", (2.1, 0.32, 0.06), (0, 0.15, OH + 0.29), M_MARBLE, bevel=0.015)
F.box("ShelfBed", (2.0, 0.26, 0.03), (0, 0.12, OH + 0.245), M_MARBLE, bevel=0.006)
F.box("GratePlate", (OW, 0.03, OH), (0, 0.012, OH / 2), M_IRON)
F.box("GrateMouth", (OW * 0.62, 0.03, OH * 0.55), (0, 0.02, OH * 0.42), M_SOOT)
F.box("BasketFloor", (0.6, 0.26, 0.03), (0, 0.14, 0.16), M_IRON)
for k in range(5):
    F.box(f"BasketBar{k}", (0.6, 0.015, 0.015), (0, 0.27, 0.18 + k * 0.048), M_IRON)
for sx in (-1, 1):
    F.box(f"BasketSide{sx}", (0.02, 0.26, 0.24), (sx * 0.3, 0.14, 0.27), M_IRON)
    lathe(f"Firedog{sx}", [(0.0, 0.0), (0.035, 0.0), (0.035, 0.03), (0.022, 0.07), (0.04, 0.12), (0.022, 0.17), (0.0, 0.18)], FP(sx * 0.36, 0.28, 0.0), M_BRASS, steps=10)
cr = random.Random(5)
for k in range(30):
    lx = cr.uniform(-0.26, 0.26); ly = cr.uniform(0.05, 0.26); lz = 0.19 + cr.uniform(0, 0.1) * (1 - abs(lx) / 0.32)
    sphere(f"Coal{k}", cr.uniform(0.028, 0.052), FP(lx, ly, lz), M_EMBERS if lz < 0.26 or cr.random() < 0.5 else M_IRON, seg=6,
           scale=(cr.uniform(0.8, 1.3), cr.uniform(0.8, 1.3), cr.uniform(0.6, 0.9)))
FIRE_BASE = Vector(FP(0, 0.15, 0.23))
F.box("FenderFront", (1.7, 0.014, 0.1), (0, 0.56, 0.05), M_BRASS, bevel=0.004)
for sx in (-1, 1): F.box(f"FenderSide{sx}", (0.014, 0.4, 0.1), (sx * 0.85, 0.36, 0.05), M_BRASS, bevel=0.004)
for k in range(3):
    p0 = Vector(FP(0.72, 0.34, 0.06)); p1 = Vector(FP(0.72 - 0.045 * k, 0.16, 0.74))
    tube(f"FireIron{k}", [p0, p1], 0.008, M_IRON, sides=5)
    sphere(f"FireIronKnob{k}", 0.018, tuple(p1 + Vector((0, 0, 0.01))), M_BRASS, seg=8)
SHELF_Z = OH + 0.32
F.box("MirrorGlass", (1.5, 0.02, 1.55), (0, 0.03, SHELF_Z + 0.95), M_MIRROR)
for (fx_, fz, sw, sh) in ((0, SHELF_Z + 0.95 + 0.82, 1.72, 0.11), (0, SHELF_Z + 0.95 - 0.82, 1.72, 0.11), (-0.805, SHELF_Z + 0.95, 0.11, 1.55), (0.805, SHELF_Z + 0.95, 0.11, 1.55)):
    F.box(f"MirrorFrame{fx_}{fz}", (sw, 0.07, sh), (fx_, 0.05, fz), M_GILT, bevel=0.02)
F.box("MirrorCrest", (0.8, 0.05, 0.18), (0, 0.05, SHELF_Z + 1.86), M_GILT, bevel=0.04)
for sx in (-1, 1):   # bronze urns on the shelf
    lathe(f"Urn{sx}", [(0.0, 0.0), (0.06, 0.0), (0.06, 0.02), (0.03, 0.05), (0.03, 0.08), (0.09, 0.16), (0.08, 0.26), (0.05, 0.3), (0.06, 0.33), (0.0, 0.34)],
          FP(sx * 0.78, 0.15, SHELF_Z), M_IRON, steps=14)
anchor("room.fireplace", FP(0, 0.5, 0))

# gas brackets either side of the overmantel
BRACKETS = {}
for tag, sx in (("N", 1), ("S", -1)):
    b0 = Vector(FP(sx * 1.2, 0.0, 2.15))
    lathe(f"BracketRose{tag}", [(0.0, 0.0), (0.06, 0.0), (0.05, 0.02), (0.0, 0.025)], tuple(b0), M_BRASS, steps=10, rot=(0, math.pi / 2, 0))
    arm = [b0, b0 + Vector((0.18, 0, -0.06)), b0 + Vector((0.32, 0, 0.0)), b0 + Vector((0.36, 0, 0.12))]
    tube(f"BracketArm{tag}", arm, 0.011, M_BRASS, sides=6)
    lathe(f"BracketGallery{tag}", [(0.0, 0.0), (0.03, 0.0), (0.05, 0.03), (0.0, 0.03)], tuple(arm[-1]), M_BRASS, steps=10)
    sphere(f"BracketGlobe{tag}", 0.075, tuple(arm[-1] + Vector((0, 0, 0.09))), M_GLOBE, seg=14, scale=(1, 1, 1.1))
    BRACKETS[tag] = arm[-1] + Vector((0, 0, 0.09))

# ----------------------------------------------------------------------------- the whist table, mid-rubber, under the gasolier
TABLE = Vector((-1.15, 1.85, 0))
def face(pos, target): return math.atan2(-(target[0] - pos[0]), target[1] - pos[1])
TF = Frame((TABLE.x, TABLE.y), 0.12)
TZ = 0.74
TF.box("CardTop", (0.94, 0.94, 0.035), (0, 0, TZ - 0.0175), M_MAHOG, bevel=0.01)
TF.box("CardBaize", (0.80, 0.80, 0.004), (0, 0, TZ + 0.002), M_BAIZE)
TF.box("CardApron", (0.84, 0.84, 0.1), (0, 0, TZ - 0.085), M_MAHOG, bevel=0.004)
for sx in (-1, 1):
    for sy in (-1, 1):
        lathe(f"CardLeg{sx}{sy}", [(0.0, 0.0), (0.02, 0.0), (0.025, 0.05), (0.02, 0.1), (0.028, 0.28), (0.034, 0.42), (0.03, 0.5), (0.036, 0.6), (0.036, TZ - 0.13), (0.0, TZ - 0.13)],
              TF.p(sx * 0.39, sy * 0.39, 0), M_MAHOG, steps=10)
def cards_mat():
    m, nt, b = new_mat("M_PlayingCards")
    a = node(nt, "ShaderNodeAttribute", (-800, 0)); a.attribute_name = "tone"
    nt.links.new(a.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.4
    return m
M_CARDS = cards_mat()
def card_mesh():
    """The rubber left as the players rose: four hands face down at the places in small fans, the last trick face up
    in the middle, the turned trump at the dealer's right, the still pack squared beside the score card (period cards:
    plain dark-blue backs, no corner indices; the faces white with a red or black centre mark for the pips)."""
    vs = []; fs = []; cols = []
    r2 = random.Random(8)
    def slab(c, yaw, w=0.063, h=0.09, face_up=False, red=False, lift=0.0, court=False):
        ca, sa = math.cos(yaw), math.sin(yaw)
        base = len(vs)
        for (px, py) in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
            vs.append((c[0] + px * ca - py * sa, c[1] + px * sa + py * ca, c[2] + lift + 0.0015))
        fs.append((base, base + 1, base + 2, base + 3))
        cols.append((0.80, 0.78, 0.72) if face_up else (0.10, 0.14, 0.30))
        if face_up:
            b2 = len(vs); s = 0.018 if court else 0.011
            for (px, py) in ((-s, -s * 1.4), (s, -s * 1.4), (s, s * 1.4), (-s, s * 1.4)):
                vs.append((c[0] + px * ca - py * sa, c[1] + px * sa + py * ca, c[2] + lift + 0.0019))
            fs.append((b2, b2 + 1, b2 + 2, b2 + 3))
            cols.append((0.55, 0.06, 0.05) if red else ((0.30, 0.22, 0.10) if court else (0.03, 0.03, 0.03)))
    tz = TZ + 0.004
    for k in range(4):
        ang = TF.yaw + math.radians(90 * k - 90)
        hc = Vector((TABLE.x + math.cos(ang) * 0.30, TABLE.y + math.sin(ang) * 0.30, tz))
        n = 4 if k else 3
        for j in range(n):
            slab(hc + Vector((math.cos(ang + 1.57) * (j - n / 2) * 0.02, math.sin(ang + 1.57) * (j - n / 2) * 0.02, 0)), ang + 1.57 + (j - 1.5) * 0.16, lift=j * 0.0006)
    for j in range(4):
        a2 = r2.uniform(0, 6.28); rr = r2.uniform(0.02, 0.09)
        slab((TABLE.x + math.cos(a2) * rr, TABLE.y + math.sin(a2) * rr, tz), r2.uniform(0, 3.14), face_up=True, red=r2.random() < 0.5, lift=j * 0.0006, court=j == 2)
    # the turned trump (a heart) and the still pack
    slab(TF.p(0.24, -0.27, tz), TF.yaw + 0.3, face_up=True, red=True, court=True)
    for j in range(14):
        slab(TF.p(-0.26, -0.28, tz), TF.yaw + 0.05 + r2.gauss(0, 0.02), lift=j * 0.0006)
    o = mesh_from("PlayingCards", vs, fs, M_CARDS)
    ca = o.data.color_attributes.new("tone", 'BYTE_COLOR', 'CORNER')
    for p in o.data.polygons:
        for li in p.loop_indices: ca.data[li].color = (*cols[p.index], 1.0)
    return o
card_mesh()
TF.box("ScoreCard", (0.09, 0.13, 0.002), (-0.12, -0.31, TZ + 0.005), M_PAPERBLANK)
tube("Pencil", [Vector(TF.p(-0.05, -0.36, TZ + 0.008)), Vector(TF.p(0.06, -0.31, TZ + 0.008))], 0.004, M_MAHOG, sides=6)
# four chairs drawn back from the table, leather seats
for k, (ang, push, turn) in enumerate(((0, 0.18, 0.15), (90, 0.05, -0.05), (180, 0.35, 0.4), (270, 0.12, -0.2))):
    a = TF.yaw + math.radians(ang - 90)
    pos = TABLE + Vector((math.cos(a), math.sin(a), 0)) * (0.66 + push)
    I.sabre_chair(f"WhistChair{k}", (pos.x, pos.y), face(pos, TABLE) + turn, M_MAHOG, M_CHAIRLEATHER)
anchor("room.whistTable", tuple(TABLE))

# ----------------------------------------------------------------------------- the gasolier over the table
GZ = 2.85
GC = Vector((TABLE.x, TABLE.y, 0))
lathe("CeilingRose", [(0.0, 0.0), (0.5, 0.0), (0.46, -0.03), (0.38, -0.05), (0.3, -0.06), (0.18, -0.08), (0.08, -0.1), (0.0, -0.1)], (GC.x, GC.y, R.h - 0.26), M_PLASTER, steps=32)
tube("GasolierStem", [Vector((GC.x, GC.y, R.h - 0.3)), Vector((GC.x, GC.y, GZ + 0.2))], 0.018, M_BRASS, sides=8)
for k, zz in enumerate((R.h - 0.6, (R.h + GZ) / 2, GZ + 0.45)):
    sphere(f"StemKnop{k}", 0.04, (GC.x, GC.y, zz), M_BRASS, seg=10, scale=(1, 1, 0.8))
lathe("GasolierCorona", [(0.0, -0.08), (0.05, -0.08), (0.11, -0.03), (0.13, 0.03), (0.09, 0.08), (0.03, 0.12), (0.0, 0.12)], (GC.x, GC.y, GZ + 0.12), M_BRASS, steps=16)
lathe("GasolierDrop", [(0.0, -0.18), (0.02, -0.15), (0.04, -0.08), (0.03, 0.0), (0.0, 0.0)], (GC.x, GC.y, GZ + 0.05), M_BRASS, steps=10)
GLOBES = []
for k in range(6):
    a = 2 * math.pi * k / 6 + 0.26
    d = Vector((math.cos(a), math.sin(a), 0))
    p0 = Vector((GC.x, GC.y, GZ + 0.12)) + d * 0.1
    arm = [p0, p0 + d * 0.18 + Vector((0, 0, -0.10)), p0 + d * 0.36 + Vector((0, 0, -0.05)), p0 + d * 0.44 + Vector((0, 0, 0.04))]
    tube(f"GasolierArm{k}", arm, 0.012, M_BRASS, sides=6)
    lathe(f"GasolierCup{k}", [(0.0, 0.0), (0.03, 0.0), (0.05, 0.035), (0.0, 0.035)], tuple(arm[-1]), M_BRASS, steps=10)
    g = arm[-1] + Vector((0, 0, 0.11))
    sphere(f"GasolierGlobe{k}", 0.082, tuple(g), M_GLOBE, seg=14, scale=(1, 1, 1.1))
    GLOBES.append(g)

# ----------------------------------------------------------------------------- the club chairs: deep-buttoned leather, by the fire and near the reader
def club_chair(name, x, y, yaw):
    """a deep-buttoned Victorian leather club armchair: square seat on a low base, arms level with the seat back's
    shoulders and rolled outwards, the back raked a little, turned mahogany bun feet on castors."""
    F2 = Frame((x, y), yaw)
    F2.box(f"{name}Base", (0.90, 0.84, 0.28), (0, 0, 0.20), M_LEATHER, bevel=0.04)
    F2.box(f"{name}Cushion", (0.58, 0.64, 0.12), (0, 0.07, 0.40), M_LEATHER, bevel=0.05)
    F2.box(f"{name}Back", (0.86, 0.22, 0.56), (0, -0.31, 0.62), M_LEATHER, bevel=0.06, rx=-0.10)
    tube(f"{name}BackRoll", [Vector(F2.p(-0.40, -0.35, 0.89)), Vector(F2.p(0, -0.37, 0.91)), Vector(F2.p(0.40, -0.35, 0.89))], 0.075, M_LEATHER, sides=10)
    for sx in (-1, 1):
        F2.box(f"{name}Arm{sx}", (0.15, 0.80, 0.30), (sx * 0.375, 0.01, 0.48), M_LEATHER, bevel=0.04)
        tube(f"{name}ArmRoll{sx}", [Vector(F2.p(sx * 0.40, -0.36, 0.64)), Vector(F2.p(sx * 0.405, 0.0, 0.645)), Vector(F2.p(sx * 0.40, 0.39, 0.64))], 0.075, M_LEATHER, sides=10)
        for sy in (-1, 1):
            sphere(f"{name}Foot{sx}{sy}", 0.04, F2.p(sx * 0.37, sy * 0.33, 0.035), M_MAHOG, seg=8, scale=(1, 1, 0.9))
    return F2
FIRE_PT = Vector((R.x0 + 0.5, FP_Y, 0))
CH1 = club_chair("ClubChairFire1", -2.95, -0.05, face((-2.95, -0.05), FIRE_PT) + 0.35)
CH2 = club_chair("ClubChairFire2", -2.85, 3.25, face((-2.85, 3.25), FIRE_PT) - 0.35)
CH3 = club_chair("ClubChairReader", 2.2, 0.75, face((2.2, 0.75), (0.0, 2.5)) + 0.2)
# a low table between the fire chairs with the evening papers and a decanter tray
ST = Vector((-2.55, 1.55, 0))
lathe("SideTableTop", [(0.0, 0.52), (0.34, 0.52), (0.35, 0.535), (0.34, 0.55), (0.0, 0.55)], tuple(ST), M_MAHOG, steps=32)
lathe("SideTablePillar", [(0.0, 0.0), (0.18, 0.0), (0.19, 0.05), (0.06, 0.09), (0.05, 0.2), (0.07, 0.3), (0.04, 0.42), (0.06, 0.52), (0.0, 0.52)], tuple(ST), M_MAHOG, steps=12)

def newspaper(name, c, yaw, w=0.40, h=0.58, folds=2, lift=0.0):
    """a folded broadsheet: a stack of slightly offset, slightly sagging leaves."""
    for k in range(folds):
        F3 = Frame((c[0] + 0.004 * k, c[1] - 0.003 * k), yaw + 0.02 * k, z=c[2] + lift + k * 0.0025)
        F3.box(f"{name}Leaf{k}", (w - 0.006 * k, h - 0.004 * k, 0.0016), (0, 0, 0.0008), M_NEWS)
newspaper("PaperSide", (ST.x + 0.05, ST.y - 0.02, 0.552), 0.05)
newspaper("PaperSide2", (ST.x - 0.06, ST.y + 0.08, 0.557), math.pi / 2 + 0.06, folds=1)
newspaper("PaperChair", CH3.p(0.05, 0.08, 0.49), CH3.yaw + 0.25, folds=3, w=0.42, h=0.6)
# a newspaper fallen open on the carpet beside the reader's chair
for k in range(2):
    Fp = Frame(CH3.p(-0.62 + 0.03 * k, 0.35, 0.0), CH3.yaw - 0.4 + 0.25 * k, z=0.013 + 0.002 * k)
    Fp.box(f"PaperFloor{k}", (0.56, 0.4, 0.0016), (0, 0, 0), M_NEWS)

# ----------------------------------------------------------------------------- the north wall: sideboard with papers, the marine painting, the longcase clock
SB = Frame((0.0, R.y1 - 0.3), math.pi)
SB.box("SideboardTop", (2.3, 0.6, 0.04), (0, 0, 0.93), M_MAHOG, bevel=0.008)
SB.box("SideboardCarcass", (2.2, 0.52, 0.66), (0, 0.0, 0.58), M_MAHOG, bevel=0.006)
SB.box("SideboardPlinth", (2.24, 0.55, 0.22), (0, 0.0, 0.11), M_MAHOG, bevel=0.006)
for k in range(3):
    SB.box(f"SideboardDoor{k}", (0.66, 0.02, 0.5), ((k - 1) * 0.72, 0.265, 0.55), M_MAHOG, bevel=0.012)
    SB.box(f"SideboardDrawer{k}", (0.66, 0.02, 0.1), ((k - 1) * 0.72, 0.265, 0.86), M_MAHOG, bevel=0.008)
    sphere(f"SideboardKnob{k}", 0.014, SB.p((k - 1) * 0.72, 0.285, 0.86), M_BRASS, seg=8)
SB.box("SideboardBack", (2.3, 0.04, 0.2), (0, -0.28, 1.05), M_MAHOG, bevel=0.01)
# the papers on the sideboard (The Times, the Morning Chronicle, the Standard...): two piles and one opened out
for k in range(3):
    newspaper(f"PaperSB{k}", SB.p(-0.75 + 0.02 * k, 0.02, 0.951 + 0.004 * k), SB.yaw + rng.uniform(-0.04, 0.04), folds=2)
for k in range(2):
    newspaper(f"PaperSBb{k}", SB.p(0.55 + 0.01 * k, 0.0, 0.951 + 0.005 * k), SB.yaw + math.pi / 2 + rng.uniform(-0.05, 0.05), folds=2)
# a silver tray with a decanter
lathe("Salver", [(0.0, 0.0), (0.2, 0.0), (0.21, 0.015), (0.19, 0.015), (0.0, 0.006)], SB.p(-0.05, 0.0, 0.95), plain("M_Silver", (0.8, 0.8, 0.78), rough=0.2, metallic=1.0), steps=24)
M_DECANT = plain("M_DecanterGlass", (0.35, 0.10, 0.06), rough=0.05, transmission=0.85)
lathe("Decanter", [(0.0, 0.0), (0.07, 0.0), (0.085, 0.06), (0.08, 0.13), (0.03, 0.2), (0.02, 0.26), (0.03, 0.27), (0.0, 0.27)], SB.p(-0.05, 0.0, 0.966), M_DECANT, steps=16)
# the marine painting above, in a heavy gilt frame
PW, PH, PZ = 1.7, 1.13, 2.65
pc = Vector((0.0, R.y1 - 0.06, PZ))
mesh_from("MarineCanvas", [(pc.x + PW / 2, pc.y, PZ - PH / 2), (pc.x - PW / 2, pc.y, PZ - PH / 2), (pc.x - PW / 2, pc.y, PZ + PH / 2), (pc.x + PW / 2, pc.y, PZ + PH / 2)],
          [(0, 1, 2, 3)], M_MARINE, uvs=[(1, 0), (0, 0), (0, 1), (1, 1)])
for (dx, dz, sw, sh) in ((0, PH / 2 + 0.06, PW + 0.24, 0.12), (0, -PH / 2 - 0.06, PW + 0.24, 0.12), (-PW / 2 - 0.06, 0, 0.12, PH), (PW / 2 + 0.06, 0, 0.12, PH)):
    box(f"MarineFrame{dx}{dz}", (sw, 0.08, sh), (pc.x + dx, R.y1 - 0.05, PZ + dz), M_GILT, bevel=0.025)
for k in range(2):   # the hanging chains to the picture rail under the cornice
    tube(f"PictureChain{k}", [Vector((pc.x + (k - 0.5) * 1.2, R.y1 - 0.03, PZ + PH / 2 + 0.12)), Vector((pc.x + (k - 0.5) * 0.4, R.y1 - 0.02, R.h - 0.45))], 0.004, M_BRASS, sides=4)

# the longcase clock: a tall mahogany case, arched hood with brass finials, white painted dial at a quarter to nine
CLK = Frame((3.35, R.y1 - 0.17), math.pi)
CLK.box("ClockPlinth", (0.58, 0.30, 0.42), (0, 0, 0.21), M_MAHOG, bevel=0.01)
CLK.box("ClockBaseMould", (0.62, 0.33, 0.05), (0, 0, 0.445), M_MAHOG, bevel=0.012)
CLK.box("ClockTrunk", (0.44, 0.24, 1.08), (0, 0, 1.01), M_MAHOG, bevel=0.008)
CLK.box("ClockTrunkDoor", (0.32, 0.02, 0.86), (0, 0.125, 1.0), M_MAHOG, bevel=0.014)
CLK.box("ClockWaist", (0.58, 0.31, 0.06), (0, 0, 1.58), M_MAHOG, bevel=0.012)
CLK.box("ClockHood", (0.56, 0.30, 0.54), (0, 0, 1.88), M_MAHOG, bevel=0.01)
cyl("ClockArch", 0.28, 0.30, CLK.p(0, 0, 2.15), M_MAHOG, verts=24, rot=(math.pi / 2, 0, CLK.yaw))
CLK.box("ClockHoodCornice", (0.62, 0.34, 0.05), (0, 0, 2.16), M_MAHOG, bevel=0.012)
for k, dx in enumerate((-0.25, 0.0, 0.25)):
    CLK.box(f"ClockFinialBlock{k}", (0.07, 0.07, 0.07 if k != 1 else 0.1), (dx, 0.05, 2.23 + (0.17 if k == 1 else 0.0)), M_MAHOG)
    lathe(f"ClockFinial{k}", [(0.0, 0.0), (0.02, 0.0), (0.03, 0.04), (0.018, 0.07), (0.008, 0.11), (0.0, 0.13)], CLK.p(dx, 0.05, 2.265 + (0.2 if k == 1 else 0.0)), M_BRASS, steps=8)
for sx in (-1, 1):
    CLK.cyl(f"ClockColumn{sx}", 0.022, 0.5, (sx * 0.245, 0.14, 1.88), M_MAHOG, verts=8)
    CLK.cyl(f"ClockColCap{sx}", 0.03, 0.03, (sx * 0.245, 0.14, 2.14), M_BRASS, verts=8)
    CLK.cyl(f"ClockColBase{sx}", 0.03, 0.03, (sx * 0.245, 0.14, 1.63), M_BRASS, verts=8)
DIAL_C = Vector(CLK.p(0, 0.155, 1.9))
CLK.box("ClockDialPlate", (0.40, 0.012, 0.40), (0, 0.15, 1.9), M_DIAL)
for sx in (-1, 1):   # brass spandrels in the dial corners
    for sz in (-1, 1):
        CLK.box(f"ClockSpandrel{sx}{sz}", (0.05, 0.004, 0.05), (sx * 0.17, 0.158, 1.9 + sz * 0.17), M_GILT, ry=math.radians(45))
cyl("ClockDialArch", 0.155, 0.012, CLK.p(0, 0.15, 2.1), M_DIAL, verts=24, rot=(math.pi / 2, 0, CLK.yaw))
for k in range(60):                      # chapter ring: hour marks and minute dots
    a = 2 * math.pi * k / 60
    rr_ = 0.165 if k % 5 == 0 else 0.172
    ln = 0.03 if k % 5 == 0 else 0.008
    CLK.box(f"ClockMark{k}", (0.006 if k % 5 == 0 else 0.003, 0.002, ln), (math.sin(a) * rr_, 0.158, 1.9 + math.cos(a) * rr_), M_BLACK, ry=-a)
for k in range(12):                      # the hour numerals stand-in: short bars inside the ring
    a = 2 * math.pi * k / 12
    CLK.box(f"ClockNumeral{k}", (0.012, 0.002, 0.028), (math.sin(a) * 0.128, 0.158, 1.9 + math.cos(a) * 0.128), M_BLACK, ry=-a)
for k, (deg, ln, wd) in enumerate(((262.5, 0.095, 0.012), (270.0, 0.15, 0.008))):   # 8:45
    a = math.radians(deg)
    CLK.box(f"ClockHand{k}", (wd, 0.003, ln), (math.sin(a) * ln * 0.42, 0.162 + 0.002 * k, 1.9 + math.cos(a) * ln * 0.42), M_BLACK, ry=-a)
CLK.cyl("ClockBoss", 0.01, 0.01, (0, 0.165, 1.9), M_BRASS, verts=8)
# the moon-phase in the arch: a dark blue disc with a gilt moon
cyl("ClockMoonDisc", 0.09, 0.004, CLK.p(0, 0.157, 2.17), plain("M_MoonBlue", K.srgb((0.10, 0.14, 0.32)), rough=0.4), verts=20, rot=(math.pi / 2, 0, CLK.yaw))
cyl("ClockMoon", 0.032, 0.004, CLK.p(0.035, 0.160, 2.19), M_GILT, verts=12, rot=(math.pi / 2, 0, CLK.yaw))
anchor("room.clock", tuple(DIAL_C))

# a glazed bookcase on the north wall, left of the sideboard (the club's library spills over)
def spines_mat(name="M_BookSpines"):
    m, nt, b = new_mat(name)
    tone = node(nt, "ShaderNodeAttribute", (-1400, 200)); tone.attribute_name = "tone"
    sv = node(nt, "ShaderNodeAttribute", (-1400, -100)); sv.attribute_name = "sv"
    v = node(nt, "ShaderNodeSeparateColor", (-1200, -100)); nt.links.new(sv.outputs["Color"], v.inputs["Color"])
    s = v.outputs[0]
    co = obj_coords(nt)
    n = noise_(nt, co, 90.0, 5, 0.6, loc=(-1200, 400))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, tone.outputs["Color"], maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.8, 1.12, (-1000, 400)), (-900, 200))
    def band(c, w):
        return math_(nt, 'MULTIPLY', maprange(nt, s, c - w, c - w + 0.004, 0, 1, (-1000, -500)), maprange(nt, s, c + w - 0.004, c + w, 1, 0, (-1000, -600)), (-850, -550))
    bands = band(0.14, 0.012)
    for c in (0.34, 0.54, 0.86):
        bands = math_(nt, 'MAXIMUM', bands, band(c, 0.012), (-700, -550))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', band(0.72, 0.06), 0.8, (-550, -700)), col, (0.05, 0.03, 0.02, 1), (-400, 200))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', bands, 0.85, (-550, -850)), col, (0.55, 0.40, 0.17, 1), (-250, 200))
    col = K.ao_mul(nt, col, 0.08, 0.5, (-150, -400))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.5
    bump_from(nt, b, bands, 0.3, 0.001)
    return m
M_SPINES = spines_mat()
BOOK_TONES = [K.srgb(c) for c in [(0.36, 0.20, 0.11), (0.42, 0.25, 0.13), (0.30, 0.17, 0.09), (0.33, 0.12, 0.08), (0.20, 0.25, 0.18),
                                   (0.18, 0.19, 0.24), (0.47, 0.30, 0.17), (0.25, 0.14, 0.08), (0.44, 0.17, 0.10), (0.62, 0.55, 0.42)]]
class Books:
    def __init__(self): self.v = []; self.f = []; self.tone = []; self.sv = []
    def add(self, c, yaw, t, w, h, tone):
        Fm = Matrix.Rotation(yaw, 3, 'Z')
        def P(x, y, z): return tuple(Vector(c) + Fm @ Vector((x, y, z)))
        cs = {(ix, iy, iz): P(ix * t / 2, iy * w, iz * h) for ix in (-1, 1) for iy in (0, 1) for iz in (0, 1)}
        quads = [((-1, 0, 0), (1, 0, 0), (1, 0, 1), (-1, 0, 1)), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
                 ((-1, 1, 0), (-1, 0, 0), (-1, 0, 1), (-1, 1, 1)), ((-1, 0, 1), (1, 0, 1), (1, 1, 1), (-1, 1, 1))]
        for qi, q in enumerate(quads):
            base = len(self.v)
            for k in q:
                self.v.append(cs[k]); self.sv.append((float(k[2]) if qi == 0 else 0.5, 0, 0, 1))
                self.tone.append(tuple(tone) + (1.0,) if qi != 3 else (0.55, 0.50, 0.40, 1.0))
            self.f.append((base, base + 1, base + 2, base + 3))
    def build(self, name):
        o = mesh_from(name, self.v, self.f, M_SPINES)
        for an, data in (("tone", self.tone), ("sv", self.sv)):
            ca = o.data.color_attributes.new(an, 'FLOAT_COLOR', 'POINT')
            ca.data.foreach_set("color", np.array(data, np.float32).ravel())
        return o
BOOKS = Books()
def bookcase(name, x0, x1, ywall, facing, z1=2.45, depth=0.36, shelves=6, seed=0):
    """mahogany bookcase standing against a wall at y = ywall, its front facing `facing` (+1 = +Y), from x0 to x1."""
    rr = random.Random(seed)
    yaw = 0.0 if facing > 0 else math.pi
    fy = ywall + facing * depth
    span = x1 - x0; nb = max(1, int(round(span / 0.9))); bay = span / nb
    for k in range(nb + 1):
        box(f"{name}Up{k}", (0.04, depth, z1), (x0 + k * bay, ywall + facing * depth / 2, z1 / 2), M_MAHOG, bevel=0.004)
    box(f"{name}Back", (span, 0.015, z1), ((x0 + x1) / 2, ywall + facing * 0.008, z1 / 2), M_MAHOG)
    box(f"{name}Plinth", (span + 0.06, depth + 0.03, 0.22), ((x0 + x1) / 2, ywall + facing * (depth + 0.03) / 2, 0.11), M_MAHOG, bevel=0.008)
    box(f"{name}Cornice", (span + 0.1, depth + 0.07, 0.1), ((x0 + x1) / 2, ywall + facing * (depth + 0.07) / 2, z1 + 0.05), M_MAHOG, bevel=0.02)
    rows = [0.42, 0.36, 0.32, 0.30, 0.28, 0.26][:shelves]
    sc = (z1 - 0.24) / sum(rows); rows = [r * sc for r in rows]
    z = 0.22
    for i, rh in enumerate(rows):
        box(f"{name}Shelf{i}", (span, depth - 0.02, 0.025), ((x0 + x1) / 2, ywall + facing * depth / 2, z + 0.012), M_MAHOG)
        for k in range(nb):
            u = x0 + k * bay + 0.03; uend = x0 + (k + 1) * bay - 0.03
            tone = rr.choice(BOOK_TONES); left = 0
            while u < uend - 0.03:
                if left == 0:
                    if rr.random() < 0.08: u += rr.uniform(0.05, 0.18); continue
                    left = rr.choice([1, 2, 3, 4, 6, 8, 10]); tone = rr.choice(BOOK_TONES)
                    hh = min(rh - 0.04, [0.38, 0.3, 0.26, 0.24, 0.22, 0.2][i] * rr.uniform(0.85, 1.0)); ww = min(hh * 0.72, depth - 0.05); tt = rr.uniform(0.03, 0.055)
                t = tt * rr.uniform(0.92, 1.08)
                if u + t > uend: break
                BOOKS.add((u + t / 2, fy - facing * 0.015, z + 0.025), yaw + math.pi, t, ww, hh * rr.uniform(0.97, 1.0), tuple(c * rr.uniform(0.9, 1.08) for c in tone))
                u += t + rr.uniform(0, 0.003); left -= 1
        z += rh
bookcase("CaseN", -3.9, -1.6, R.y1, -1, seed=1)
bookcase("CaseS", 0.0, 3.9, R.y0, 1, seed=2)
BOOKS.build("Books")

# ----------------------------------------------------------------------------- lights (FableBuild's indoor block keeps names starting "Lamp")
light_obj("Lamp.gasolier", 'POINT', 260.0, (1.0, 0.80, 0.56), (GC.x, GC.y, GZ + 0.12), shadow_soft_size=0.45)
for tag, p in BRACKETS.items():
    light_obj(f"Lamp.bracket{tag}", 'POINT', 45.0, (1.0, 0.80, 0.56), tuple(Vector(p) + Vector((0.05, 0, 0))), shadow_soft_size=0.08)
light_obj("Lamp.fire", 'POINT', 70.0, (1.0, 0.50, 0.22), tuple(FIRE_BASE + Vector((0.4, 0, 0.15))), shadow_soft_size=0.25)
light_obj("Lamp.dusk", 'POINT', 70.0, (0.55, 0.65, 1.0), (R.x1 - 0.7, (WIN_Y[0] + WIN_Y[1]) / 2, 2.4), shadow_soft_size=1.2)
world = bpy.data.worlds.new("Dusk"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.045, 0.09, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors and living-scene sources
fwd = Vector((0, 1, 0))
anchor("reader.entrance", tuple(READER))
anchor("reader.look", tuple(READER + fwd + Vector((0, 0, EYE))))
anchor("scene.centre", tuple(TABLE))
anchor("room.window", R.at('E', WIN_Y[0] - R.y0, 1.6))
anchor("room.door", R.at('S', DOOR_X - R.x0))
E8.fx("fx.fire.hearth", tuple(FIRE_BASE), 0.26)
sound("fire", "hearth", tuple(FIRE_BASE + Vector((0.2, 0, 0.1))))
sound("clock", "longcase", tuple(DIAL_C))

page = box("PagePreview", (0.4, 0.004, 0.55), tuple(READER + fwd * 0.6 + Vector((0, 0, EYE - 0.05))), plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9, emission=(0.80, 0.77, 0.69), strength=0.15))
K.apply_transforms()
for o in K.COLL.objects:
    if o.type == 'MESH' and o.data.materials and o.data.materials[0].name in ("M_PallMall",):
        o.visible_shadow = False; o.visible_diffuse = False

# ----------------------------------------------------------------------------- cameras
EP = READER + Vector((0, 0, EYE))
def yawed(deg, dist=5.0, dz=-0.6):
    a = math.radians(deg); return tuple(EP + Vector((math.sin(a), math.cos(a), 0)) * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(EP), yawed(0, 6, -0.5), lens=17),
    camera("Cam_Page", tuple(EP), yawed(0, 6, -0.5), lens=17),
    camera("Cam_Left", tuple(EP), yawed(-72, 6, -0.6), lens=17),
    camera("Cam_Right", tuple(EP), yawed(78, 6, -0.3), lens=17),
    camera("Cam_Behind", tuple(EP), yawed(180, 6, -0.4), lens=17),
    camera("Cam_Down", tuple(EP), tuple(READER + Vector((-0.5, 1.4, 0))), lens=17),
    camera("Cam_Up", tuple(EP), tuple(READER + Vector((-0.8, 2.2, R.h))), lens=17),
    camera("Cam_Table", tuple(TABLE + Vector((0.9, -1.0, 1.45))), tuple(TABLE + Vector((0, 0, 0.74))), lens=28),
    camera("Cam_Fire", (-1.0, 0.4, 1.4), FP(0, 0.2, 0.9), lens=22),
    camera("Cam_Clock", tuple(EP + Vector((1.2, 2.0, 0.1))), tuple(DIAL_C + Vector((0, 0, -0.25))), lens=30),
]
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "reform_club_source.blend"))
K.print_budget(exclude=("PagePreview",) + tuple(o.name for o in I.RENDER_ONLY))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.6, captures_dir=ARGS.captures)

if ARGS.bake or ARGS.export:
    for o in I.RENDER_ONLY:
        if o.name in bpy.data.objects: bpy.data.objects.remove(o)
    E8.bake_and_export(
        "reform_club.gltf", cams, page=page,
        keep_names={"M_Embers": "MESH_Embers", "M_WindowGlass": "WindowGlass_plate", "M_GasGlobes": "MESH_GasGlobes", "M_PallMall": "far.PallMall"},
        size_for={"M_FloorBoards": (1024, 256, 1024), "M_TurkeyCarpet": (2048, 128, 1024), "M_WallDamask": (2048, 128, 1024), "M_CeilingPanels": (1024, 64, 256),
                  "M_Plaster": (1024, 128, 512), "M_OakPanelling": (2048, 256, 1024), "M_Mahogany": (2048, 512, 1024), "M_BlackMarble": (1024, 256, 512),
                  "M_Curtains": (1024, 256, 1024), "M_ClubLeather": (1024, 256, 1024), "M_ChairLeather": (512, 128, 256), "M_Gilt": (512, 256, 256),
                  "M_Brass": (256, 64, 64), "M_Iron": (256, 128, 128), "M_Embers": (256, 64, 128), "M_PlayingCards": (512, 64), "M_Newsprint": (1024, 64, 256),
                  "M_Baize": (512, 64, 256), "M_Mirror": (64, 32), "M_WindowGlass": (32, 32), "M_Soot": (32, 32), "M_ClockDial": (128, 32),
                  "M_BlackPaint": (32, 32), "M_GasGlobes": (64, 32), "M_BookSpines": (1024, 256, 512), "M_ScoreCard": (64, 32), "M_Silver": (64, 32),
                  "M_DecanterGlass": (64, 32), "M_MoonBlue": (32, 32)},
        default_size=(256, 64, 128))
print("DONE")
