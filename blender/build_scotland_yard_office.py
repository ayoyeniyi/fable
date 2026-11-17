"""
Fable step-in room `scotland-yard-office`: the office of Rowan, Commissioner of Police, Scotland Yard, at nine
o'clock one October evening in 1872 (Around the World in Eighty Days, chapter 5).

"The commissioner of police was sitting in his office at nine o'clock one evening, when the following telegraphic
dispatch was put into his hands: Suez to London. Rowan, Commissioner of Police, Scotland Yard: I've found the bank
robber, Phileas Fogg. Send without delay warrant of arrest to Bombay. Fix, Detective."

A modest official room: plain distempered walls over a dark oak dado, a cast-iron fireplace with a low coal fire, one
sash window on the dark street (a gas lamp in the wet, the buildings opposite unlit), a door to the corridor. The
commissioner's big oak pedestal desk under a gas reading lamp: the buff telegraph form laid square in front of the
reader, the evening's papers on the wager (The Times, the Standard, the Morning Post and the Daily News), the
Geographical Society's bulletin, the Illustrated London News open at the portrait of Fogg, the file with the robber's
description, an inkstand and pens, a blotter. Behind the desk the empty leather chair, a pigeon-hole cabinet and
shelves of ledgers, a wall clock at nine. No people; no warrant, no telephone or typewriter, no electric light.

Run (from the repo root):
  blender -b -P blender/build_scotland_yard_office.py -- --cpu --render --samples 40 --res 1280 --captures captures/blender/scotland-yard-office
  blender -b -P blender/build_scotland_yard_office.py -- --export --tex 2048
  then blender/runtime_bake.py (--indoor) and tools/publish_scene_room.py (docs/SCENE_ROOMS_PIPELINE.md)
Axes: metres, +Z up; the reader stands south of the desk facing +Y (north), the window is in the west wall.
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
import pride_interior as I
import eighty_kit as E8
from eighty_kit import (new_mat, node, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                        wood, noisy, plain, image_mat, np_image, box, cyl, sphere, lathe, tube, mesh_from, Frame,
                        anchor, sound, light_obj, camera)

ARGS = K.setup("scotland-yard-office", "out/scotland-yard-office", 1872, "ScotlandYard", default_samples=40)
OUT = K.OUT; scene = K.scene
rng = random.Random(9)
scene.cycles.max_bounces = 8; scene.cycles.diffuse_bounces = 5

EYE = 1.55
R = I.Room(-2.0, 2.0, -2.6, 2.4, 3.3, t=0.4)
READER = Vector((0.0, -1.25, 0.0))
DADO = 1.0

# ----------------------------------------------------------------------------- materials
M_WALL = I.paint_mat("M_Distemper", K.srgb((0.62, 0.55, 0.40)), rough=0.85, dirt=0.12)
M_OAK = wood("M_DarkOak", base=(0.10, 0.06, 0.03), dark=(0.035, 0.02, 0.01), light=(0.17, 0.10, 0.05), scale=1.1, rough=(0.35, 0.55),
             grain_dir=(1, 1, 9), coat=0.2, ao=0.3, bump=0.1)
M_CEIL = I.paint_mat("M_Ceiling", K.srgb((0.66, 0.62, 0.52)), rough=0.9, dirt=0.15)
M_FLOOR = I.boards_mat("M_FloorBoards", light=(0.17, 0.10, 0.05), dark=(0.07, 0.04, 0.02))
M_RUG = I.carpet_mat("M_Drugget", 0.0, -0.2, 1.4, 1.6, field=(0.10, 0.04, 0.03), ground2=(0.03, 0.04, 0.03),
                     border=(0.02, 0.025, 0.02), buff=(0.18, 0.13, 0.07))
M_IRON = noisy("M_Iron", [(0.010, 0.010, 0.011), (0.022, 0.021, 0.021), (0.016, 0.015, 0.014)], scale=30, rough=(0.45, 0.7), metallic=0.35)
M_SOOT = plain("M_Soot", (0.012, 0.011, 0.01), rough=0.95)
M_BRASS = plain("M_Brass", (0.66, 0.48, 0.24), rough=0.3, metallic=1.0)
M_GLASS = plain("M_WindowGlass", (0.85, 0.88, 0.90), rough=0.02, transmission=1.0)
M_LEATHER = noisy("M_ChairLeather", [K.srgb((0.20, 0.08, 0.05)), K.srgb((0.26, 0.11, 0.07)), K.srgb((0.16, 0.06, 0.04))], scale=18, rough=(0.4, 0.6), bump=0.15, bump_dist=0.001)
M_DESKLEATHER = noisy("M_DeskLeather", [K.srgb((0.08, 0.14, 0.09)), K.srgb((0.10, 0.17, 0.11)), K.srgb((0.06, 0.11, 0.07))], scale=25, rough=(0.45, 0.6), bump=0.1, bump_dist=0.001)
M_DIAL = plain("M_ClockDial", K.srgb((0.86, 0.84, 0.78)), rough=0.35)
M_BLACK = plain("M_BlackPaint", (0.012, 0.011, 0.01), rough=0.4)
M_INK = plain("M_InkGlass", (0.02, 0.03, 0.05), rough=0.05)
M_BLOTTER = plain("M_Blotter", K.srgb((0.30, 0.10, 0.12)), rough=0.95)
M_BUFF = plain("M_TelegraphForm", K.srgb((0.80, 0.72, 0.55)), rough=0.9)
M_FILE = plain("M_FileBoard", K.srgb((0.42, 0.30, 0.18)), rough=0.85)
M_PAPERW = plain("M_WritingPaper", K.srgb((0.84, 0.82, 0.76)), rough=0.9)
M_GLOBE = plain("M_GasGlobes", (0.95, 0.92, 0.84), rough=0.4, emission=(1.0, 0.82, 0.55), strength=5.0)
M_LEDGER = noisy("M_Ledgers", [K.srgb((0.22, 0.12, 0.08)), K.srgb((0.30, 0.20, 0.12)), K.srgb((0.16, 0.18, 0.12)), K.srgb((0.35, 0.10, 0.08))], scale=6, rough=0.6, bump=0.05)


def newsprint_mat(name="M_Newsprint"):
    """Newsprint seen from a metre: columns of grey text lines with gutters and rules, headings, a few advertisements."""
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
    ink = math_(nt, 'ADD', 0.30, math_(nt, 'MULTIPLY', ln, 0.35, (-900, -100)), (-850, -100))
    ink = math_(nt, 'MAXIMUM', ink, math_(nt, 'MULTIPLY', heads, 0.85, (-900, -400)), (-800, -200))
    ink = math_(nt, 'MULTIPLY', ink, gutter, (-700, -100))
    paper = c4(K.srgb((0.78, 0.75, 0.66)))
    col = mix_rgb(nt, 'MIX', ink, paper, (0.06, 0.06, 0.06, 1), (-500, 200))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
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
    nt.links.new(ec, b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 3.0
    b.inputs["Roughness"].default_value = 0.9
    return m
M_EMBERS = embers_mat()


# ----------------------------------------------------------------------------- painted images: the night street, the ILN portrait
def paint_street_night(W=2048, H=1024):
    """Whitehall Place at nine on an October night from a first-floor window: a gas lamp on its post at the kerb,
    its glow on the wet setts and on the stock-brick front opposite (two windows faintly lit), a dark sky.
    Plane: y -15..15 m (u), z -7..13 m (v), 14 m beyond the window wall."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    z = 13.0 - yy / H * 20.0; y = -15.0 + xx / W * 30.0
    rs = np.random.RandomState(3)
    img = np.zeros((H, W, 4), np.float32); img[..., 3] = 1
    img[..., :3] = np.array([0.012, 0.015, 0.025]) + (np.clip((z - 8) / 5, 0, 1) * 0.0)[..., None]
    front = (z < 9.0) & (z > -4.2)
    nb = rs.rand(H, W).astype(np.float32)
    img[front, :3] = (np.array([0.030, 0.026, 0.022]) * (0.85 + 0.3 * nb[front])[..., None])
    for yc in np.arange(-13.0, 15.0, 2.6):
        for (zb, zt) in ((-2.6, -0.2), (1.0, 3.6), (5.0, 7.2)):
            m = (np.abs(y - yc) < 0.55) & (z > zb) & (z < zt)
            lit = rs.rand() < 0.12
            img[m, :3] = np.array([0.40, 0.26, 0.10]) * rs.uniform(0.4, 0.8) if lit else np.array([0.008, 0.009, 0.012])
    street = z <= -4.2
    img[street, :3] = np.array([0.012, 0.012, 0.014]) * (0.8 + 0.4 * nb[street])[..., None]
    for (yl, zl) in ((-3.0, -1.8), (9.5, -1.6)):
        d2 = (y - yl) ** 2 + (z - zl) ** 2
        halo = np.exp(-d2 / 1.5) * 0.10 + np.exp(-d2 / 0.03) * 1.6
        img[..., :3] += halo[..., None] * np.array([1.0, 0.80, 0.48])
        post = (np.abs(y - yl) < 0.07) & (z < zl - 0.25) & (z > -4.4)
        img[post, :3] = np.array([0.01, 0.01, 0.01])
        pool = front * np.exp(-((y - yl) ** 2) / 10.0) * np.exp(-((z - zl) ** 2) / 8.0) * 0.08
        img[..., :3] += pool[..., None] * np.array([1.0, 0.75, 0.45])
        refl = street * np.exp(-((y - yl) ** 2) / 0.2) * np.exp(-((z + 4.2) ** 2) / 3.0) * 0.4
        img[..., :3] += refl[..., None] * np.array([1.0, 0.75, 0.4])
    return np_image("A_StreetNight", np.clip(img, 0, 4))


def paint_iln(W=512, H=704):
    """The Illustrated London News, a page: masthead rule, three columns of type, an engraved oval portrait of a
    gentleman (hatched head and shoulders, light whiskers) captioned below."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rs = np.random.RandomState(7)
    img = np.ones((H, W, 4), np.float32); img[..., :3] = np.array([0.80, 0.77, 0.68])
    def lines(x0, x1, y0, y1):
        for yl in np.arange(y0, y1, 7):
            seg = (xx > x0) & (xx < x1) & (np.abs(yy - yl) < 1.4)
            gaps = rs.rand(W) < 0.12
            img[seg & ~gaps[None, :], :3] *= 0.45
    img[(yy > 18) & (yy < 50), :3] *= np.where(((xx > 40) & (xx < 470))[(yy > 18) & (yy < 50)], 0.25, 1.0)[..., None]
    img[(np.abs(yy - 58) < 1.5) & (xx > 20) & (xx < 492), :3] *= 0.3
    lines(22, 160, 70, 680); lines(352, 490, 70, 680)
    # the oval engraving in the middle column
    cx, cy, rx, ry = 256, 300, 82, 108
    e = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    inside = e < 1
    hatch = (np.sin((xx + yy) * 1.6) > 0.2).astype(np.float32)
    tone = np.full((H, W), 0.82, np.float32)
    head = ((xx - cx) / 34) ** 2 + ((yy - (cy - 30)) / 44) ** 2 < 1
    body = ((yy > cy + 15) & (((xx - cx) / 78) ** 2 + ((yy - (cy + 110)) / 95) ** 2 < 1))
    tone = np.where(body, 0.25, tone); tone = np.where(head, 0.62, tone)
    hair = ((xx - cx) / 36) ** 2 + ((yy - (cy - 58)) / 22) ** 2 < 1
    tone = np.where(hair & (yy < cy - 50), 0.55, tone)
    for sx in (-1, 1):
        wh = ((xx - (cx + sx * 26)) / 9) ** 2 + ((yy - (cy - 18)) / 20) ** 2 < 1
        tone = np.where(wh, 0.58, tone)
    shade = np.clip(1 - tone + 0.15, 0, 1) * hatch
    img[inside, :3] *= (1 - 0.75 * shade[inside])[..., None]
    ring = (e > 1) & (e < 1.08)
    img[ring, :3] *= 0.3
    lines(180, 330, 430, 680)
    img[(np.abs(yy - 418) < 3) & (xx > 200) & (xx < 312), :3] *= 0.35
    return np_image("A_IllustratedLondonNews", np.clip(img, 0, 1))


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
M_STREET = emissive_image_mat("M_StreetNight", paint_street_night(), 1.0)
M_ILN = image_mat("M_IllustratedLondonNews", paint_iln(), rough=0.85)

# ----------------------------------------------------------------------------- openings, walls, floor, ceiling
WIN_Y = 0.6                          # west wall: u = y1 - y
M_BLIND = I.silk("M_Blind", K.srgb((0.42, 0.36, 0.24)), K.srgb((0.46, 0.40, 0.27)), damask=0.0, sheen=0.1, rough=0.9)
I.sash_window("Win", R, 'W', R.y1 - WIN_Y, 1.15, 0.85, 2.0, M_OAK, M_GLASS, M_OAK, panes=(2, 4), curtain_mat=M_BLIND, pelmet_mat=M_OAK, drawn=0.35)
DOOR_X = 1.25                        # south wall: u = x - x0
I.six_panel_door("Door", R, 'S', DOOR_X - R.x0, 0.95, 2.3, M_OAK, M_OAK, M_BRASS, open_deg=0.0, hinge_left=True)
I.build_walls(R, M_WALL)
FP_Y = 0.2
R.openings['E'].append((FP_Y - R.y0, 1.4, 0.0, 1.12, "chimneypiece"))
SXB = R.x0 - R.t - 14.0
mesh_from("StreetNight", [(SXB, 15.0, -7.0), (SXB, -15.0, -7.0), (SXB, -15.0, 13.0), (SXB, 15.0, 13.0)], [(0, 3, 2, 1)], M_STREET,
          uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
box("Floor", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.04), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, -0.02), M_FLOOR)
box("Drugget", (2.8, 3.2, 0.01), (0.0, -0.2, 0.005), M_RUG, bevel=0.003)
box("Ceiling", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.05), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, R.h + 0.025), M_CEIL)
I.moulding_runs(R, "Skirting", I.skirting_profile(0.22), 0.0, M_OAK)
for w in ('S', 'E', 'N', 'W'):
    o, a, n, L = R.wall_frame(w)
    for k, (u0, u1) in enumerate(I.runs(R, w, 0.0, DADO)):
        c = o + a * ((u0 + u1) / 2) + n * 0.012 + Vector((0, 0, DADO / 2))
        box(f"Dado{w}{k}", (abs(a.x) * (u1 - u0) + abs(n.x) * 0.024, abs(a.y) * (u1 - u0) + abs(n.y) * 0.024, DADO), tuple(c), M_OAK)
I.dado_panels(R, M_OAK, rail_z=DADO, skirt=0.22, step=0.8)
I.moulding_runs(R, "DadoRail", [(0.0, -0.05), (0.03, -0.05), (0.04, -0.02), (0.04, 0.0), (0.0, 0.02)], DADO, M_OAK, z_band=(DADO - 0.05, DADO + 0.02))
I.moulding_runs(R, "Cornice", I.cornice_profile(0.16, 0.2), R.h, M_CEIL, z_band=(R.h - 0.2, R.h))

# ----------------------------------------------------------------------------- the cast-iron fireplace, a low coal fire (east wall)
F = Frame((R.x1, FP_Y), math.atan2(1, 0))
def FP(x, y, z): return F.p(x, y, z)
OW, OH = 0.7, 0.85
F.box("HearthStone", (1.4, 0.45, 0.04), (0, 0.22, 0.02), M_SOOT, bevel=0.004)
for sx in (-1, 1):
    F.box(f"Jamb{sx}", (0.2, 0.12, OH + 0.05), (sx * (OW / 2 + 0.1), 0.06, (OH + 0.05) / 2), M_IRON, bevel=0.01)
    F.box(f"Bracket{sx}", (0.12, 0.1, 0.16), (sx * (OW / 2 + 0.1), 0.15, OH - 0.02), M_IRON, bevel=0.02)
F.box("Frieze", (OW + 0.4, 0.12, 0.2), (0, 0.06, OH + 0.1), M_IRON, bevel=0.01)
F.box("Shelf", (1.3, 0.22, 0.04), (0, 0.11, OH + 0.22), M_IRON, bevel=0.01)
F.box("Insert", (OW, 0.03, OH), (0, 0.012, OH / 2), M_IRON)
F.box("Mouth", (OW * 0.6, 0.03, OH * 0.55), (0, 0.02, OH * 0.38), M_SOOT)
F.box("GrateFloor", (0.44, 0.2, 0.025), (0, 0.12, 0.13), M_IRON)
for k in range(4): F.box(f"GrateBar{k}", (0.44, 0.012, 0.012), (0, 0.22, 0.15 + k * 0.045), M_IRON)
cr = random.Random(5)
for k in range(22):
    lx = cr.uniform(-0.19, 0.19); ly = cr.uniform(0.04, 0.2); lz = 0.16 + cr.uniform(0, 0.07)
    sphere(f"Coal{k}", cr.uniform(0.025, 0.045), FP(lx, ly, lz), M_EMBERS if cr.random() < 0.55 else M_IRON, seg=6,
           scale=(cr.uniform(0.8, 1.3), cr.uniform(0.8, 1.3), cr.uniform(0.6, 0.9)))
FIRE_BASE = Vector(FP(0, 0.12, 0.19))
F.box("Fender", (1.2, 0.012, 0.08), (0, 0.42, 0.04), M_IRON, bevel=0.003)
lathe("Scuttle", [(0.0, 0.0), (0.14, 0.0), (0.16, 0.12), (0.15, 0.28), (0.0, 0.28)], FP(0.8, 0.35, 0.0), M_IRON, steps=12)
for k in range(2):
    tube(f"Poker{k}", [Vector(FP(-0.6, 0.3, 0.04)), Vector(FP(-0.62 + 0.04 * k, 0.12, 0.72))], 0.007, M_IRON, sides=5)
# on the mantel: a plain clock-less shelf with a tobacco jar and spills; above, a framed police notice
lathe("TobaccoJar", [(0.0, 0.0), (0.06, 0.0), (0.065, 0.1), (0.05, 0.13), (0.0, 0.14)], FP(0.4, 0.11, OH + 0.24), M_IRON, steps=12)
F.box("NoticeFrame", (0.55, 0.03, 0.7), (0, 0.02, OH + 0.9), M_OAK, bevel=0.01)
F.box("Notice", (0.47, 0.01, 0.62), (0, 0.036, OH + 0.94), M_PAPERW)
anchor("room.fireplace", FP(0, 0.5, 0))

# ----------------------------------------------------------------------------- the desk and what is on it
DESK = Vector((0.0, 0.55, 0.0))
D = Frame((DESK.x, DESK.y), math.pi)          # its front (+Y local) faces the reader (south)
TOP = 0.76
D.box("DeskTop", (1.65, 0.9, 0.04), (0, 0, TOP - 0.02), M_OAK, bevel=0.01)
D.box("DeskInlay", (1.5, 0.75, 0.004), (0, 0, TOP + 0.001), M_DESKLEATHER)
for sx in (-1, 1):
    D.box(f"Pedestal{sx}", (0.5, 0.8, TOP - 0.06), (sx * 0.56, 0, (TOP - 0.06) / 2), M_OAK, bevel=0.008)
    D.box(f"Plinth{sx}", (0.54, 0.84, 0.08), (sx * 0.56, 0, 0.04), M_OAK, bevel=0.006)
    for k in range(3):
        D.box(f"Drawer{sx}{k}", (0.44, 0.02, 0.17), (sx * 0.56, -0.41, 0.14 + k * 0.2), M_OAK, bevel=0.01)
        sphere(f"Knob{sx}{k}", 0.014, D.p(sx * 0.56, -0.43, 0.22 + k * 0.2), M_BRASS, seg=8)
D.box("ModestyPanel", (0.62, 0.02, 0.5), (0, 0.38, 0.4), M_OAK)
D.box("Frieze", (0.62, 0.8, 0.08), (0, 0, TOP - 0.09), M_OAK)
# the telegraph form, square in front of the reader, with Fix's message (the words written in, as a clerk took them down)
TG = Vector((DESK.x - 0.05, DESK.y - 0.25, TOP + 0.004))
box("TelegraphForm", (0.25, 0.19, 0.002), tuple(TG), M_BUFF)
# writing: text objects in the bundled font, ink-black, laid flat
def ink_text(name, body, loc, size, rot_z=0.0):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size; cu.align_x = 'LEFT'
    cu.resolution_u = 2; cu.space_line = 1.15
    o = bpy.data.objects.new(name, cu); o.location = loc; o.rotation_euler = (0, 0, rot_z); K.link(o)
    o.data.materials.append(M_BLACK)
    bpy.context.view_layer.objects.active = o
    for x in bpy.context.view_layer.objects.selected: x.select_set(False)
    o.select_set(True); bpy.ops.object.convert(target='MESH'); o.select_set(False)
    return o
ink_text("TelegramHead", "ELECTRIC TELEGRAPH", (TG.x - 0.105, TG.y + 0.072, TG.z + 0.0012), 0.013)
ink_text("TelegramBody", "Suez to London.\nRowan, Commissioner of Police,\nScotland Yard:\nI've found the bank robber,\nPhileas Fogg. Send without delay\nwarrant of arrest to Bombay.\nFix, Detective.",
         (TG.x - 0.115, TG.y + 0.047, TG.z + 0.0012), 0.0128)
# the papers on the wager, the Geographical Society's bulletin, the Illustrated London News open at the portrait
def paper(name, c, yaw, w=0.38, h=0.55, n=2, mat=None):
    for k in range(n):
        Fp = Frame((c[0] + 0.004 * k, c[1] - 0.003 * k), yaw + 0.02 * k, z=c[2] + k * 0.0025)
        Fp.box(f"{name}{k}", (w - 0.006 * k, h - 0.004 * k, 0.0016), (0, 0, 0.0008), mat or M_NEWS)
paper("Times", (DESK.x - 0.55, DESK.y + 0.05, TOP + 0.003), 0.15, n=3)
paper("Standard", (DESK.x - 0.5, DESK.y + 0.12, TOP + 0.011), -0.25, n=2)
paper("MorningPost", (DESK.x + 0.52, DESK.y + 0.18, TOP + 0.003), 0.35, n=2)
paper("DailyNews", (DESK.x + 0.55, DESK.y + 0.1, TOP + 0.009), -0.1, n=2)
box("RGSBulletin", (0.17, 0.24, 0.006), (DESK.x + 0.3, DESK.y - 0.15, TOP + 0.004), plain("M_BulletinCover", K.srgb((0.55, 0.50, 0.36)), rough=0.85), rot=(0, 0, 0.2))
ink_text("RGSTitle", "Royal Geographical\nSociety", (DESK.x + 0.24, DESK.y - 0.08, TOP + 0.0075), 0.012, rot_z=0.2)
ILN = Frame((DESK.x + 0.18, DESK.y + 0.12), -0.12, z=TOP + 0.004)
mesh_from("ILNPage", [ILN.p(-0.15, -0.205, 0.004), ILN.p(0.15, -0.205, 0.004), ILN.p(0.15, 0.205, 0.004), ILN.p(-0.15, 0.205, 0.004)],
          [(0, 1, 2, 3)], M_ILN, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
ILN.box("ILNUnder", (0.6, 0.41, 0.003), (-0.15, 0, 0.0015), M_NEWS)
# the file with the robber's description, a blotter, the inkstand and pens
box("FileBoards", (0.24, 0.32, 0.012), (DESK.x - 0.32, DESK.y - 0.2, TOP + 0.006), M_FILE, rot=(0, 0, -0.1))
box("FileSheet", (0.21, 0.29, 0.002), (DESK.x - 0.33, DESK.y - 0.19, TOP + 0.013), M_PAPERW, rot=(0, 0, -0.08))
ink_text("FileLabel", "Bank of England\nrobbery: description", (DESK.x - 0.42, DESK.y - 0.08, TOP + 0.0145), 0.0095, rot_z=-0.08)
box("Blotter", (0.48, 0.34, 0.01), (DESK.x + 0.05, DESK.y + 0.22, TOP + 0.005), M_BLOTTER)
IS = Vector((DESK.x - 0.05, DESK.y + 0.33, TOP))
box("InkstandTray", (0.3, 0.16, 0.02), tuple(IS + Vector((0, 0, 0.01))), M_BRASS, bevel=0.005)
for sx in (-1, 1):
    lathe(f"InkPot{sx}", [(0.0, 0.0), (0.03, 0.0), (0.032, 0.05), (0.015, 0.06), (0.018, 0.07), (0.0, 0.07)], tuple(IS + Vector((sx * 0.08, 0, 0.02))), M_INK, steps=10)
    sphere(f"InkLid{sx}", 0.018, tuple(IS + Vector((sx * 0.08, 0, 0.095))), M_BRASS, seg=8, scale=(1, 1, 0.5))
for k in range(2):
    tube(f"Pen{k}", [IS + Vector((-0.06 + 0.02 * k, -0.055, 0.025)), IS + Vector((0.08 + 0.02 * k, -0.06, 0.03))], 0.004, M_BLACK, sides=5)
# the gas reading lamp: a brass column on a weighted foot, a white glass globe, its flexible tube to the wall cock
LMP = Vector((DESK.x + 0.55, DESK.y + 0.28, TOP))
lathe("LampFoot", [(0.0, 0.0), (0.09, 0.0), (0.09, 0.02), (0.05, 0.04), (0.02, 0.06), (0.0, 0.06)], tuple(LMP), M_BRASS, steps=16)
cyl("LampColumn", 0.012, 0.36, tuple(LMP + Vector((0, 0, 0.24))), M_BRASS, verts=8)
lathe("LampGallery", [(0.0, 0.0), (0.04, 0.0), (0.06, 0.03), (0.0, 0.03)], tuple(LMP + Vector((0, 0, 0.42))), M_BRASS, steps=12)
sphere("LampGlobe", 0.075, tuple(LMP + Vector((0, 0, 0.5))), M_GLOBE, seg=14, scale=(1, 1, 1.1))
LAMP_PT = LMP + Vector((0, 0, 0.5))
tube("LampTube", [LMP + Vector((0.06, 0.02, 0.03)), LMP + Vector((0.3, 0.05, -0.05)), Vector((DESK.x + 1.05, R.y1 - 0.05, 0.9)), Vector((DESK.x + 1.05, R.y1 - 0.02, 1.3))], 0.008, plain("M_RubberTube", (0.05, 0.03, 0.02), rough=0.6), sides=5)
anchor("room.desk", tuple(DESK))
anchor("room.dispatch", tuple(TG))

# the commissioner's chair, pushed back a little from the desk
CHF = Frame((DESK.x + 0.1, DESK.y + 0.78), math.pi + 0.15)
CHF.box("ChairSeat", (0.56, 0.52, 0.1), (0, 0, 0.45), M_LEATHER, bevel=0.03)
CHF.box("ChairBack", (0.56, 0.08, 0.55), (0, -0.25, 0.78), M_LEATHER, bevel=0.03, rx=-0.12)
for sx in (-1, 1):
    CHF.box(f"ChairArm{sx}", (0.06, 0.48, 0.05), (sx * 0.29, -0.02, 0.67), M_OAK, bevel=0.01)
    CHF.box(f"ChairArmPost{sx}", (0.04, 0.04, 0.2), (sx * 0.29, 0.19, 0.57), M_OAK)
    for sy in (-1, 1):
        CHF.box(f"ChairLeg{sx}{sy}", (0.04, 0.04, 0.42), (sx * 0.24, sy * 0.2, 0.21), M_OAK)
# a plain chair on the reader's side of the desk, set to one side
I.sabre_chair("VisitorChair", (DESK.x - 0.95, DESK.y - 0.75), 0.6, M_OAK, M_LEATHER)

# ----------------------------------------------------------------------------- the north wall: pigeon-holes, ledger shelves, the wall clock
PH = Frame((-0.9, R.y1 - 0.2), math.pi)
PH.box("PigeonCarcass", (1.0, 0.36, 1.1), (0, 0, 1.45), M_OAK, bevel=0.006)
PH.box("PigeonBase", (1.05, 0.42, 0.9), (0, 0, 0.45), M_OAK, bevel=0.006)
for k in range(2): PH.box(f"PigeonDoor{k}", (0.46, 0.02, 0.76), ((k - 0.5) * 0.5, 0.21, 0.47), M_OAK, bevel=0.01)
for i in range(6):
    for j in range(5):
        PH.box(f"Hole{i}{j}", (0.14, 0.02, 0.17), (-0.4 + i * 0.16, 0.18, 1.1 + j * 0.2), M_SOOT)
        if rng.random() < 0.6:
            PH.box(f"Docket{i}{j}", (0.11, 0.2, 0.05 + rng.random() * 0.06), (-0.4 + i * 0.16, 0.12, 1.03 + j * 0.2), M_PAPERW if rng.random() < 0.7 else M_FILE)
# ledger shelves on the right of the north wall
LS = Frame((0.95, R.y1 - 0.17), math.pi)
for k, zz in enumerate((0.9, 1.35, 1.8, 2.25)):
    LS.box(f"Shelf{k}", (1.1, 0.3, 0.025), (0, 0, zz), M_OAK)
    u = -0.52
    while u < 0.5:
        t = rng.uniform(0.04, 0.07); hh = rng.uniform(0.28, 0.38)
        if rng.random() < 0.08: u += 0.08; continue
        LS.box(f"Ledger{k}_{u:.2f}", (t, 0.26, hh), (u + t / 2, 0.0, zz + 0.0125 + hh / 2), M_LEDGER, bevel=0.004)
        u += t + 0.003
for sx in (-1, 1): LS.box(f"ShelfSide{sx}", (0.03, 0.3, 1.6), (sx * 0.56, 0, 1.6), M_OAK)
# the wall clock at nine, over the door side of the room (it ticks)
CK = Vector((R.x1 - 0.04, -1.5, 2.3))
cyl("ClockCase", 0.2, 0.08, tuple(CK - Vector((0.04, 0, 0))), M_OAK, verts=24, rot=(0, math.pi / 2, 0))
cyl("ClockFace", 0.17, 0.01, tuple(CK - Vector((0.085, 0, 0))), M_DIAL, verts=24, rot=(0, math.pi / 2, 0))
for k in range(12):
    a = 2 * math.pi * k / 12
    box(f"ClockMark{k}", (0.004, 0.006, 0.025), (CK.x - 0.092, CK.y + math.sin(a) * 0.145, CK.z + math.cos(a) * 0.145), M_BLACK, rot=(-a, 0, 0))
box("ClockHourHand", (0.004, 0.09, 0.008), (CK.x - 0.095, CK.y + 0.045, CK.z), M_BLACK)
box("ClockMinHand", (0.004, 0.006, 0.13), (CK.x - 0.097, CK.y, CK.z + 0.06), M_BLACK)
box("ClockTrunk", (0.06, 0.18, 0.5), (CK.x - 0.03, CK.y, CK.z - 0.45), M_OAK, bevel=0.01)

# ----------------------------------------------------------------------------- lights
light_obj("Lamp.desk", 'POINT', 110.0, (1.0, 0.78, 0.50), tuple(LAMP_PT), shadow_soft_size=0.07)
light_obj("Lamp.fire", 'POINT', 45.0, (1.0, 0.45, 0.18), tuple(FIRE_BASE + Vector((-0.35, 0, 0.12))), shadow_soft_size=0.15)
light_obj("Lamp.street", 'AREA', 6.0, (1.0, 0.75, 0.45), (R.x0 - 0.6, WIN_Y, 1.4), direction=(1, 0, 0.15), shape='RECTANGLE', size=1.0, size_y=1.8)
light_obj("Lamp.fill", 'POINT', 22.0, (0.9, 0.8, 0.65), (0.0, -1.5, 2.8), shadow_soft_size=0.6)
world = bpy.data.worlds.new("Night"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.01, 0.012, 0.02, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors and living scene
fwd = Vector((0, 1, 0))
anchor("reader.entrance", tuple(READER))
anchor("reader.look", tuple(READER + fwd + Vector((0, 0, EYE))))
anchor("scene.centre", tuple(DESK))
anchor("room.window", R.at('W', R.y1 - WIN_Y, 1.6))
anchor("room.door", R.at('S', DOOR_X - R.x0))
E8.fx("fx.fire.hearth", tuple(FIRE_BASE), 0.18)
E8.fx("fx.lantern.desklamp", tuple(LAMP_PT), 0.07)
sound("fire", "hearth", tuple(FIRE_BASE + Vector((-0.2, 0, 0.1))))
sound("clock", "wall", tuple(CK))

page = box("PagePreview", (0.4, 0.004, 0.55), tuple(READER + fwd * 0.6 + Vector((0, 0, EYE - 0.05))), plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9, emission=(0.80, 0.77, 0.69), strength=0.15))
K.apply_transforms()
for o in K.COLL.objects:
    if o.type == 'MESH' and o.data.materials and o.data.materials[0].name in ("M_StreetNight",):
        o.visible_shadow = False; o.visible_diffuse = False

# ----------------------------------------------------------------------------- cameras
EP = READER + Vector((0, 0, EYE))
def yawed(deg, dist=5.0, dz=-0.6):
    a = math.radians(deg); return tuple(EP + Vector((math.sin(a), math.cos(a), 0)) * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(EP), yawed(0, 6, -1.0), lens=17),
    camera("Cam_Left", tuple(EP), yawed(-70, 6, -0.6), lens=17),
    camera("Cam_Right", tuple(EP), yawed(70, 6, -0.6), lens=17),
    camera("Cam_Behind", tuple(EP), yawed(180, 6, -0.5), lens=17),
    camera("Cam_Desk", tuple(READER + Vector((0.1, 0.35, 1.3))), tuple(TG), lens=30),
]
K.print_budget(exclude=("PagePreview",) + tuple(o.name for o in I.RENDER_ONLY))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams=set(), default_exposure=0.6, captures_dir=ARGS.captures)

if ARGS.bake or ARGS.export:
    for o in I.RENDER_ONLY:
        if o.name in bpy.data.objects: bpy.data.objects.remove(o)
    # the diffuse-colour bake of a metallic surface is black (the runtime room has no reflections): bake the albedo
    # of brass, gilt, iron and the mirror as a dielectric
    for m in bpy.data.materials:
        b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m.node_tree else None
        if b is None: continue
        for l in list(b.inputs["Metallic"].links): m.node_tree.links.remove(l)
        b.inputs["Metallic"].default_value = 0.0
    E8.bake_and_export(
        "scotland_yard_office.gltf", cams, page=page,
        keep_names={"M_WindowGlass": "WindowGlass_plate", "M_GasGlobes": "MESH_GasGlobes", "M_StreetNight": "far.StreetNight",
                    "M_Embers": "MESH_Embers", "M_Blind": "cloth.curtain.window"},
        size_for={"M_FloorBoards": (1024, 256), "M_Drugget": (1024, 128), "M_Distemper": (1024, 128), "M_Ceiling": (512, 64),
                  "M_DarkOak": (2048, 256), "M_Blind": (512, 128), "M_ChairLeather": (512, 128), "M_DeskLeather": (512, 64),
                  "M_Newsprint": (1024, 64), "M_Iron": (512, 128), "M_Brass": (256, 64), "M_Ledgers": (512, 64), "M_TelegraphForm": (128, 32),
                  "M_BlackPaint": (64, 32), "M_Embers": (256, 64)},
        default_size=(256, 64))
print("DONE")
