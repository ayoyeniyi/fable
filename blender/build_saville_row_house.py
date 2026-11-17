"""
Fable step-in room `saville-row-house`: Phileas Fogg's sitting room, No. 7 Saville Row, on the late morning of
Wednesday 2 October 1872 (Around the World in Eighty Days, chapters 1, 2 and 4).

"Phileas Fogg was seated squarely in his armchair, his feet close together like those of a grenadier on parade, his
hands resting on his knees, his body straight, his head erect; he was steadily watching a complicated clock which
indicated the hours, the minutes, the seconds, the days, the months, and the years." (ch. 1)
"So clean, well-arranged, solemn a mansion pleased him; it seemed to him like a snail's shell, lighted and warmed by
gas ... Electric bells and speaking-tubes afforded communication with the lower stories" (ch. 2). "There was no study,
nor were there books ... neither arms nor hunting weapons; everything betrayed the most tranquil and peaceable habits."
"A moderate-sized safe ... constructed so as to defy fire as well as burglars." (ch. 2)

The moment: half-past eleven, Passepartout just shown in; Fogg has gone out to the Reform Club. The first-floor
sitting room is papered in dark green, with a mahogany dado, a white marble chimney-piece with a gas fire burning low
and gas brackets either side, a Turkey carpet, one tall sash window onto Saville Row (grey London daylight, the houses
opposite), and the door through to the bedroom standing open: the green-painted iron safe and the tall wardrobe are
seen beyond. Fogg's leather wing armchair faces the great regulator clock on the north wall: silvered dial with hours
and minutes, a seconds dial, day and month dials and a year aperture. By the door to the landing: the electric bell
push and the speaking-tube mouthpiece. On a side table the carpet-bag, the red Bradshaw and Fogg's hat; his
mackintosh over a chair. No books (besides Bradshaw), no arms, no trunks, no maps, no electric light. No people.

Run (from the repo root):
  blender -b -P blender/build_saville_row_house.py -- --render --samples 48 --res 1280 --captures captures/blender/saville-row-house
  blender -b -P blender/build_saville_row_house.py -- --export --tex 2048
  then blender/runtime_bake.py and tools/publish_scene_room.py (docs/SCENE_ROOMS_PIPELINE.md)
Axes: metres, +Z up. The window is in the west wall, the clock on the north wall, the fire on the east wall, the
landing door in the south wall; the reader stands just inside it facing north-east.
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

ARGS = K.setup("saville-row-house", "out/saville-row-house", 1872, "SavilleRow", default_samples=48)
OUT = K.OUT; scene = K.scene
rng = random.Random(1872)
scene.cycles.max_bounces = 8; scene.cycles.diffuse_bounces = 5

EYE = 1.55
R = I.Room(-2.7, 2.7, -3.1, 3.1, 3.5, t=0.4)
READER = Vector((-1.6, -2.3, 0.0))
DADO = 0.95

# ----------------------------------------------------------------------------- materials
M_PAPER = I.silk("M_Wallpaper", K.srgb((0.11, 0.16, 0.11)), K.srgb((0.15, 0.21, 0.14)), damask=0.55, sheen=0.05, rough=0.9)
M_DADOWOOD = wood("M_DadoMahogany", base=(0.13, 0.05, 0.025), dark=(0.04, 0.015, 0.008), light=(0.22, 0.09, 0.04), scale=1.1, rough=(0.3, 0.5),
                  grain_dir=(1, 1, 9), coat=0.25, ao=0.3, bump=0.1)
M_PLASTER = I.joinery_mat("M_Plaster", K.srgb((0.84, 0.80, 0.70)), rough=0.6)
M_CEIL = I.paint_mat("M_Ceiling", K.srgb((0.80, 0.77, 0.68)), rough=0.85, dirt=0.0)
M_MAHOG = I.mahogany("M_Mahogany")
M_GILT = I.gilt("M_Gilt")
M_FLOOR = I.boards_mat("M_FloorBoards", light=(0.22, 0.13, 0.06), dark=(0.09, 0.05, 0.02))
M_CARPET = I.carpet_mat("M_TurkeyCarpet", 0.1, 0.35, 1.8, 2.1, field=(0.15, 0.025, 0.018), ground2=(0.018, 0.03, 0.065),
                        border=(0.022, 0.032, 0.07), buff=(0.22, 0.15, 0.08))
M_MARBLE = I.marble("M_WhiteMarble", base=(0.62, 0.61, 0.58), vein=(0.36, 0.36, 0.36))
M_IRON = noisy("M_Iron", [(0.010, 0.010, 0.011), (0.022, 0.021, 0.021), (0.016, 0.015, 0.014)], scale=30, rough=(0.45, 0.7), metallic=0.35)
M_SOOT = plain("M_Soot", (0.012, 0.011, 0.01), rough=0.95)
M_BRASS = plain("M_Brass", (0.70, 0.52, 0.27), rough=0.28, metallic=1.0)
M_GLASS = plain("M_WindowGlass", (0.85, 0.88, 0.90), rough=0.02, transmission=1.0)
M_DIAL = plain("M_SilverDial", K.srgb((0.78, 0.78, 0.75)), rough=0.3, metallic=0.6)
M_BLACK = plain("M_BlackPaint", (0.012, 0.011, 0.01), rough=0.4)
M_SAFE = noisy("M_SafeGreen", [K.srgb((0.10, 0.17, 0.12)), K.srgb((0.12, 0.20, 0.14)), K.srgb((0.08, 0.14, 0.10))], scale=12, rough=(0.35, 0.55), bump=0.05)
M_BRADSHAW = noisy("M_RedCloth", [K.srgb((0.45, 0.06, 0.05)), K.srgb((0.52, 0.09, 0.07)), K.srgb((0.40, 0.05, 0.04))], scale=40, rough=0.7, bump=0.1)
M_PAGES = plain("M_Pages", K.srgb((0.82, 0.78, 0.68)), rough=0.9)
M_HAT = noisy("M_HatSilk", [(0.012, 0.012, 0.013), (0.02, 0.02, 0.022), (0.008, 0.008, 0.009)], scale=20, rough=(0.25, 0.4), sheen=0.6)
M_MAC = noisy("M_Mackintosh", [K.srgb((0.20, 0.19, 0.15)), K.srgb((0.24, 0.22, 0.17)), K.srgb((0.17, 0.16, 0.13))], scale=25, rough=(0.45, 0.6), bump=0.1)
M_BEDLINEN = plain("M_Bedlinen", K.srgb((0.80, 0.79, 0.74)), rough=0.85)
M_PORCELAIN = plain("M_Porcelain", K.srgb((0.88, 0.87, 0.83)), rough=0.2)


def leather_mat(name="M_ChairLeather"):
    """Buttoned dark-green hide on Fogg's wing chair: deep-buttoned diamonds, rubbed paler on the high spots."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 13.0, 'F1', (-1200, 0))
    hollow = maprange(nt, v.outputs["Distance"], 0.0, 0.32, 0, 1, (-1000, 0), 'SMOOTHSTEP')
    n = noise_(nt, co, 7.0, 6, 0.6, loc=(-1200, -300))
    cr = noise_(nt, co, 40.0, 4, 0.65, distortion=1.5, loc=(-1200, -550))
    base = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-900, -300)), c4(K.srgb((0.06, 0.12, 0.07))), c4(K.srgb((0.09, 0.16, 0.09))), (-800, -200))
    rub = math_(nt, 'MULTIPLY', maprange(nt, hollow, 0.55, 1.0, 0, 1, (-800, 100)), maprange(nt, n.outputs["Fac"], 0.45, 0.7, 0.0, 0.5, (-800, 250)), (-650, 150))
    col = mix_rgb(nt, 'MIX', rub, base, c4(K.srgb((0.16, 0.22, 0.13))), (-500, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, hollow, 0.0, 0.35, 0.45, 1.0, (-650, -100)), (-350, 0))
    col = K.ao_mul(nt, col, 0.1, 0.5, (-250, -600))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, rub, 0, 0.5, 0.42, 0.3, (-300, -250)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'ADD', hollow, math_(nt, 'MULTIPLY', cr.outputs["Fac"], 0.25, (-500, -550)), (-350, -500)), 0.35, 0.008)
    return m
M_LEATHER = leather_mat()


def carpetbag_mat(name="M_CarpetBag"):
    """Tapestry carpet-bag stuff: a small repeating floral lozenge in red, green and buff on dark ground."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 38.0, 'F1', (-1200, 0))
    w = noise_(nt, co, 90.0, 3, 0.5, loc=(-1200, -300))
    f = maprange(nt, v.outputs["Distance"], 0.1, 0.35, 0, 1, (-1000, 0))
    col = mix_rgb(nt, 'MIX', f, c4(K.srgb((0.42, 0.10, 0.07))), c4(K.srgb((0.09, 0.10, 0.06))), (-800, 0))
    col = mix_rgb(nt, 'MIX', maprange(nt, w.outputs["Fac"], 0.55, 0.6, 0, 0.7, (-900, -300)), col, c4(K.srgb((0.40, 0.33, 0.18))), (-600, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
    bump_from(nt, b, w.outputs["Fac"], 0.2, 0.002)
    return m
M_BAG = carpetbag_mat()


def gasfire_mat(name="M_GasFireClay"):
    """Fireclay radiants of a gas fire glowing orange from the burner up, cooler and darker at the tops."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1400, 0))
    n = noise_(nt, co, 60.0, 4, 0.6, loc=(-1200, -250))
    glow = maprange(nt, s.outputs["Z"], 0.16, 0.48, 1.0, 0.15, (-1100, 0))
    glow = math_(nt, 'MULTIPLY', glow, maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.6, 1.1, (-1000, -250)), (-850, -100))
    nt.links.new(mix_rgb(nt, 'MIX', glow, (0.12, 0.07, 0.05, 1), (0.9, 0.35, 0.08, 1), (-600, 0)), b.inputs["Base Color"])
    nt.links.new(mix_rgb(nt, 'MULTIPLY', 1.0, (1.0, 0.38, 0.08, 1), glow, (-600, -300)), b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 4.0; b.inputs["Roughness"].default_value = 0.95
    return m
M_GASFIRE = gasfire_mat()
M_GLOBE = plain("M_GasGlobes", (0.95, 0.92, 0.84), rough=0.4, emission=(1.0, 0.86, 0.64), strength=3.0)


# ----------------------------------------------------------------------------- the street outside: Saville Row on a grey October morning
def paint_saville(W=2048, H=1024):
    """The houses opposite seen from a first-floor window: four-storey Georgian brick fronts (London stock brick,
    sooty), white-painted sash windows with dark glass, stucco ground floors and area railings, a parapet and chimney
    stacks against a flat grey sky. Plane: y -20..20 m (u), z -8..16 m (v), 16 m beyond the window wall."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    z = 16.0 - yy / H * 24.0
    y = -20.0 + xx / W * 40.0
    rs = np.random.RandomState(7)
    img = np.zeros((H, W, 4), np.float32); img[..., 3] = 1.0
    t = np.clip((z - 8.0) / 8.0, 0, 1)
    img[..., :3] = np.array([0.62, 0.63, 0.64]) * (1 - t)[..., None] + np.array([0.52, 0.54, 0.57]) * t[..., None]
    roof = 9.6 + np.where((y > -2) & (y < 9), 0.6, 0.0)
    brick = (z < roof) & (z > -5.0)
    noise_b = rs.rand(H, W).astype(np.float32)
    course = (np.mod(z * 13.3, 1.0) < 0.12)
    bc = np.array([0.26, 0.22, 0.17]) * (0.85 + 0.3 * noise_b)[..., None]
    bc = np.where(course[..., None], bc * 0.8, bc)
    # soot streaks
    soot = 0.75 + 0.25 * np.sin(y * 1.7 + np.sin(y * 0.37) * 3)[..., None]
    img[..., :3] = np.where(brick[..., None], bc * soot, img[..., :3])
    # stucco ground floor and the first-floor band
    stucco = brick & (z < -1.2)
    img[stucco, :3] = np.array([0.58, 0.56, 0.50]) * (0.92 + 0.08 * noise_b[stucco])[..., None]
    for zc in (-1.1, 9.4):
        band = (np.abs(z - zc) < 0.15) & (z > -5.0)
        img[band, :3] = np.array([0.66, 0.64, 0.58])
    # party-wall lines between houses (every ~6 m) and chimney stacks on them
    for yp in np.arange(-19.0, 20.0, 6.2):
        stack = (np.abs(y - yp) < 0.5) & (z >= roof) & (z < roof + 1.6)
        img[stack, :3] = np.array([0.22, 0.19, 0.15])
        for k in range(3):
            pot = (np.abs(y - (yp - 0.3 + k * 0.3)) < 0.09) & (z >= roof + 1.6) & (z < roof + 2.0)
            img[pot, :3] = np.array([0.40, 0.25, 0.17])
        # three windows per floor per house
        for k in range(3):
            yc = yp + 1.2 + k * 1.9
            for (zb, zt) in ((-0.2, 2.6), (3.4, 5.6), (6.4, 8.2)):
                m = (np.abs(y - yc) < 0.55) & (z > zb) & (z < zt)
                img[m, :3] = np.array([0.07, 0.08, 0.09]) + 0.04 * rs.rand()
                # reflected sky in the upper panes
                refl = m & (z > (zb + zt) / 2 + 0.3) & (np.abs(y - yc + 0.2) < 0.15)
                img[refl, :3] += 0.08
                bars = m & ((np.abs(y - yc) < 0.03) | (np.abs(z - (zb + zt) / 2) < 0.04) | (np.abs(y - yc) > 0.48) | (z < zb + 0.07) | (z > zt - 0.07))
                img[bars, :3] = np.array([0.72, 0.71, 0.66])
            door = (np.abs(y - (yp + 0.4)) < 0.55) & (z > -5.0) & (z < -2.4)
            img[door, :3] = np.array([0.05, 0.05, 0.05])
    # area railings along the pavement and the street
    rail = (z > -5.6) & (z < -4.6) & (np.mod(y * 8.0, 1.0) < 0.18)
    img[rail, :3] = np.array([0.03, 0.03, 0.03])
    street = z <= -5.6
    img[street, :3] = np.array([0.22, 0.21, 0.20]) * (0.9 + 0.1 * noise_b[street])[..., None]
    # a faint haze (London air)
    img[..., :3] = img[..., :3] * 0.85 + np.array([0.56, 0.57, 0.58]) * 0.15
    return np_image("A_SavilleRow", np.clip(img, 0, 1))


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
M_STREET = emissive_image_mat("M_SavilleRowView", paint_saville(), 1.0)
M_PICTURE = I.landscape_mat("M_Landscape", seed=3)

# ----------------------------------------------------------------------------- openings, then walls
WIN_Y = 0.2                          # west wall: u = y1 - y
M_CURTAIN = I.silk("M_Curtains", K.srgb((0.20, 0.09, 0.06)), K.srgb((0.26, 0.12, 0.08)), damask=0.25, sheen=0.4, rough=0.85)
I.sash_window("Win", R, 'W', R.y1 - WIN_Y, 1.3, 0.62, 2.45, M_PLASTER, M_GLASS, M_DADOWOOD, panes=(2, 4),
              curtain_mat=M_CURTAIN, pelmet_mat=M_GILT, drawn=0.25)
DOOR_X = -1.6                        # south wall: u = x - x0 (the landing door, behind the reader)
I.six_panel_door("Door", R, 'S', DOOR_X - R.x0, 1.0, 2.45, M_MAHOG, M_DADOWOOD, M_BRASS, open_deg=0.0, hinge_left=True)
BED_X = -1.55                        # north wall: u = x1 - x (the bedroom door, open)
I.six_panel_door("BedDoor", R, 'N', R.x1 - BED_X, 0.95, 2.4, M_MAHOG, M_DADOWOOD, M_BRASS, open_deg=78.0, hinge_left=False)
I.build_walls(R, M_PAPER)
FP_Y = 0.55                          # east wall: u = y - y0
R.openings['E'].append((FP_Y - R.y0, 1.72, 0.0, 1.22, "chimneypiece"))

# the street, 16 m outside the window wall (an unlit backdrop)
SX = R.x0 - R.t - 16.0
mesh_from("SavilleRowView", [(SX, 20.0, -8.0), (SX, -20.0, -8.0), (SX, -20.0, 16.0), (SX, 20.0, 16.0)], [(0, 3, 2, 1)], M_STREET,
          uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])

# floor, carpet, ceiling, mouldings
box("Floor", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.04), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, -0.02), M_FLOOR)
box("Carpet", (3.9, 4.6, 0.012), (0.1, 0.35, 0.006), M_CARPET, bevel=0.004)
box("Ceiling", (R.x1 - R.x0 + 0.1, R.y1 - R.y0 + 0.1, 0.05), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, R.h + 0.025), M_CEIL)
I.moulding_runs(R, "Skirting", I.skirting_profile(0.24), 0.0, M_DADOWOOD)
for w in ('S', 'E', 'N', 'W'):
    o, a, n, L = R.wall_frame(w)
    for k, (u0, u1) in enumerate(I.runs(R, w, 0.0, DADO)):
        c = o + a * ((u0 + u1) / 2) + n * 0.012 + Vector((0, 0, DADO / 2))
        box(f"Dado{w}{k}", (abs(a.x) * (u1 - u0) + abs(n.x) * 0.024, abs(a.y) * (u1 - u0) + abs(n.y) * 0.024, DADO), tuple(c), M_DADOWOOD)
I.dado_panels(R, M_DADOWOOD, rail_z=DADO, skirt=0.24, step=0.85)
I.moulding_runs(R, "DadoRail", [(0.0, -0.06), (0.03, -0.06), (0.045, -0.035), (0.05, 0.0), (0.04, 0.025), (0.0, 0.03)], DADO, M_DADOWOOD, z_band=(DADO - 0.06, DADO + 0.03))
I.moulding_runs(R, "Cornice", I.cornice_profile(0.26, 0.32), R.h, M_PLASTER, z_band=(R.h - 0.32, R.h))
I.moulding_runs(R, "PictureRail", [(0.0, -0.02), (0.025, -0.02), (0.03, 0.0), (0.0, 0.01)], R.h - 0.5, M_DADOWOOD, z_band=(R.h - 0.52, R.h - 0.49))
lathe("CeilingRose", [(0.0, 0.0), (0.42, 0.0), (0.38, -0.03), (0.3, -0.05), (0.18, -0.07), (0.07, -0.09), (0.0, -0.09)], (0.1, 0.35, R.h), M_PLASTER, steps=32)

# ----------------------------------------------------------------------------- the chimney-piece and the gas fire (east wall)
F = Frame((R.x1, FP_Y), math.atan2(1, 0))      # local +Y -> world -X (into the room)
def FP(x, y, z): return F.p(x, y, z)
OW, OH = 0.86, 0.92
F.box("HearthStone", (1.8, 0.55, 0.04), (0, 0.27, 0.02), M_MARBLE, bevel=0.004)
for sx in (-1, 1):
    F.box(f"Jamb{sx}", (0.26, 0.16, OH + 0.04), (sx * (OW / 2 + 0.13), 0.08, (OH + 0.04) / 2), M_MARBLE, bevel=0.006)
    F.box(f"Pilaster{sx}", (0.16, 0.05, OH - 0.1), (sx * (OW / 2 + 0.13), 0.17, OH / 2), M_MARBLE, bevel=0.01)
    F.box(f"Plinth{sx}", (0.3, 0.22, 0.11), (sx * (OW / 2 + 0.13), 0.11, 0.055), M_MARBLE, bevel=0.01)
    F.box(f"Corbel{sx}", (0.2, 0.12, 0.12), (sx * (OW / 2 + 0.13), 0.2, OH + 0.02), M_MARBLE, bevel=0.03)
F.box("Frieze", (OW + 0.52, 0.15, 0.24), (0, 0.075, OH + 0.12), M_MARBLE, bevel=0.006)
F.box("Shelf", (1.85, 0.3, 0.05), (0, 0.14, OH + 0.265), M_MARBLE, bevel=0.015)
F.box("GratePlate", (OW, 0.03, OH), (0, 0.012, OH / 2), M_IRON)
F.box("GrateMouth", (OW * 0.66, 0.03, OH * 0.6), (0, 0.02, OH * 0.40), M_SOOT)
# the gas fire: an iron frame with a row of fireclay columns over a burner bar, a brass trim
F.box("GasFrame", (0.62, 0.2, 0.5), (0, 0.10, 0.25), M_IRON, bevel=0.01)
for k in range(7):
    F.box(f"Radiant{k}", (0.055, 0.04, 0.32), (-0.24 + k * 0.08, 0.2, 0.17), M_GASFIRE, bevel=0.012)
F.box("Burner", (0.6, 0.06, 0.04), (0, 0.22, 0.14), M_BRASS, bevel=0.01)
F.box("GasFender", (1.5, 0.014, 0.09), (0, 0.5, 0.045), M_BRASS, bevel=0.004)
for sx in (-1, 1): F.box(f"GasFenderSide{sx}", (0.014, 0.34, 0.09), (sx * 0.75, 0.33, 0.045), M_BRASS, bevel=0.004)
GAS_TAP = FP(0.55, 0.3, 0.1)
lathe("GasTap", [(0.0, 0.0), (0.018, 0.0), (0.018, 0.06), (0.03, 0.07), (0.0, 0.08)], GAS_TAP, M_BRASS, steps=8)
FIRE_BASE = Vector(FP(0, 0.21, 0.16))
SHELF_Z = OH + 0.29
# overmantel mirror in a gilt frame, a pair of plain vases and a bronze mantel clock (no souvenirs)
M_MIRROR = plain("M_Mirror", (0.20, 0.21, 0.22), rough=0.05, metallic=1.0)
M_MIRROR["runtime_albedo"] = 1
F.box("MirrorGlass", (1.3, 0.02, 1.25), (0, 0.03, SHELF_Z + 0.75), M_MIRROR)
for (fx_, fz, sw, sh) in ((0, SHELF_Z + 0.75 + 0.67, 1.48, 0.09), (0, SHELF_Z + 0.75 - 0.67, 1.48, 0.09), (-0.695, SHELF_Z + 0.75, 0.09, 1.25), (0.695, SHELF_Z + 0.75, 0.09, 1.25)):
    F.box(f"MirrorFrame{fx_}{fz}", (sw, 0.06, sh), (fx_, 0.05, fz), M_GILT, bevel=0.018)
for sx in (-1, 1):
    lathe(f"Vase{sx}", [(0.0, 0.0), (0.05, 0.0), (0.05, 0.015), (0.03, 0.04), (0.07, 0.12), (0.05, 0.22), (0.03, 0.25), (0.045, 0.27), (0.0, 0.27)],
          FP(sx * 0.7, 0.15, SHELF_Z), M_PORCELAIN, steps=14)
anchor("room.fireplace", FP(0, 0.5, 0))

# gas brackets either side of the overmantel, burning low
BRACKETS = {}
for tag, sx in (("N", -1), ("S", 1)):
    b0 = Vector(FP(sx * 0.98, 0.0, 1.95))
    lathe(f"BracketRose{tag}", [(0.0, 0.0), (0.05, 0.0), (0.045, 0.02), (0.0, 0.025)], tuple(b0), M_BRASS, steps=10, rot=(0, math.pi / 2, 0))
    d = Vector(F.v(0, 1, 0))
    arm = [b0, b0 + d * 0.16 + Vector((0, 0, -0.06)), b0 + d * 0.28 + Vector((0, 0, 0.0)), b0 + d * 0.31 + Vector((0, 0, 0.1))]
    tube(f"BracketArm{tag}", arm, 0.010, M_BRASS, sides=6)
    lathe(f"BracketGallery{tag}", [(0.0, 0.0), (0.028, 0.0), (0.045, 0.03), (0.0, 0.03)], tuple(arm[-1]), M_BRASS, steps=10)
    sphere(f"BracketGlobe{tag}", 0.07, tuple(arm[-1] + Vector((0, 0, 0.085))), M_GLOBE, seg=14, scale=(1, 1, 1.1))
    BRACKETS[tag] = arm[-1] + Vector((0, 0, 0.085))

# ----------------------------------------------------------------------------- the complicated clock (north wall)
CX = 0.55
CLK = Frame((CX, R.y1 - 0.18), math.pi)
CLK.box("ClockPlinth", (0.66, 0.34, 0.36), (0, 0, 0.18), M_MAHOG, bevel=0.01)
CLK.box("ClockBaseMould", (0.70, 0.37, 0.05), (0, 0, 0.385), M_MAHOG, bevel=0.012)
CLK.box("ClockTrunk", (0.52, 0.27, 1.02), (0, 0, 0.92), M_MAHOG, bevel=0.008)
CLK.box("ClockTrunkGlass", (0.36, 0.02, 0.8), (0, 0.13, 0.94), plain("M_TrunkGlass", (0.05, 0.05, 0.05), rough=0.05), bevel=0.01)
CLK.box("ClockWaist", (0.66, 0.35, 0.06), (0, 0, 1.46), M_MAHOG, bevel=0.012)
CLK.box("ClockHood", (0.66, 0.34, 0.86), (0, 0, 1.86), M_MAHOG, bevel=0.01)
CLK.box("ClockHoodCornice", (0.74, 0.40, 0.07), (0, 0, 2.30), M_MAHOG, bevel=0.015)
CLK.box("ClockPediment", (0.6, 0.30, 0.10), (0, 0, 2.40), M_MAHOG, bevel=0.03)
lathe("ClockFinial", [(0.0, 0.0), (0.025, 0.0), (0.035, 0.05), (0.02, 0.09), (0.01, 0.13), (0.0, 0.15)], CLK.p(0, 0.0, 2.48), M_BRASS, steps=10)
# the trunk shows the pendulum: a long rod and a brass bob
CLK.box("PendulumRod", (0.012, 0.01, 0.62), (0, 0.10, 0.82), M_BRASS)
cyl("PendulumBob", 0.075, 0.03, CLK.p(0, 0.10, 0.62), M_BRASS, verts=20, rot=(math.pi / 2, 0, CLK.yaw))
for sx in (-1, 1):
    CLK.cyl(f"ClockColumn{sx}", 0.025, 0.7, (sx * 0.30, 0.15, 1.53), M_MAHOG, verts=10)
    CLK.cyl(f"ClockColCap{sx}", 0.034, 0.035, (sx * 0.30, 0.15, 2.22), M_BRASS, verts=10)
    CLK.cyl(f"ClockColBase{sx}", 0.034, 0.035, (sx * 0.30, 0.15, 1.50), M_BRASS, verts=10)
DIAL_Z = 1.94
DIAL_C = Vector(CLK.p(0, 0.175, DIAL_Z))
CLK.box("ClockDialPlate", (0.52, 0.012, 0.76), (0, 0.172, 1.76), M_DIAL)
cyl("ClockChapterRing", 0.19, 0.004, CLK.p(0, 0.18, DIAL_Z), plain("M_Enamel", K.srgb((0.90, 0.89, 0.85)), rough=0.25), verts=40, rot=(math.pi / 2, 0, CLK.yaw))
MAIN = (0, DIAL_Z)
for k in range(60):
    a = 2 * math.pi * k / 60
    rr_ = 0.168 if k % 5 == 0 else 0.176
    ln = 0.028 if k % 5 == 0 else 0.007
    CLK.box(f"ClockMark{k}", (0.006 if k % 5 == 0 else 0.0025, 0.002, ln), (MAIN[0] + math.sin(a) * rr_, 0.184, MAIN[1] + math.cos(a) * rr_), M_BLACK, ry=-a)
for k in range(12):
    a = 2 * math.pi * k / 12
    CLK.box(f"ClockNumeral{k}", (0.011, 0.002, 0.026), (MAIN[0] + math.sin(a) * 0.132, 0.184, MAIN[1] + math.cos(a) * 0.132), M_BLACK, ry=-a)
for k, (deg, ln, wd) in enumerate(((345.0, 0.10, 0.011), (180.0, 0.16, 0.007))):   # half-past eleven
    a = math.radians(deg)
    CLK.box(f"ClockHand{k}", (wd, 0.003, ln), (MAIN[0] + math.sin(a) * ln * 0.42, 0.188 + 0.002 * k, MAIN[1] + math.cos(a) * ln * 0.42), M_BLACK, ry=-a)
# subsidiary dials: seconds (top), day of the week (left), day of the month (right), month (bottom left), year (aperture)
for k, (dx, dz, r_, hand) in enumerate(((0.0, 0.075, 0.038, 200), (-0.14, -0.31, 0.055, 120), (0.14, -0.31, 0.055, 30), (0.0, -0.39, 0.04, 270))):
    cyl(f"SubDial{k}", r_, 0.003, CLK.p(dx, 0.181, DIAL_Z + dz), plain("M_Enamel", (0.9, 0.89, 0.85), rough=0.25), verts=24, rot=(math.pi / 2, 0, CLK.yaw))
    for j in range(12):
        a = 2 * math.pi * j / 12
        CLK.box(f"SubMark{k}_{j}", (0.002, 0.002, 0.01), (dx + math.sin(a) * r_ * 0.82, 0.185, DIAL_Z + dz + math.cos(a) * r_ * 0.82), M_BLACK, ry=-a)
    a = math.radians(hand)
    CLK.box(f"SubHand{k}", (0.004, 0.002, r_ * 0.8), (dx + math.sin(a) * r_ * 0.35, 0.187, DIAL_Z + dz + math.cos(a) * r_ * 0.35), M_BLACK, ry=-a)
CLK.box("YearAperture", (0.14, 0.004, 0.05), (0.0, 0.181, DIAL_Z - 0.235), M_BLACK)
CLK.box("YearFigures", (0.11, 0.004, 0.028), (0.0, 0.183, DIAL_Z - 0.235), plain("M_Enamel", (0.9, 0.89, 0.85), rough=0.25))
anchor("room.clock", tuple(DIAL_C))


# ----------------------------------------------------------------------------- Fogg's armchair, facing the clock
def wing_chair(name, x, y, yaw):
    """a deep-buttoned leather wing armchair on short turned mahogany legs."""
    F2 = Frame((x, y), yaw)
    F2.box(f"{name}Seat", (0.78, 0.74, 0.16), (0, 0.02, 0.30), M_LEATHER, bevel=0.04)
    F2.box(f"{name}Cushion", (0.58, 0.62, 0.11), (0, 0.06, 0.44), M_LEATHER, bevel=0.05)
    F2.box(f"{name}Back", (0.74, 0.18, 0.78), (0, -0.30, 0.46), M_LEATHER, bevel=0.06, rx=-0.10)
    for sx in (-1, 1):
        F2.box(f"{name}Wing{sx}", (0.10, 0.36, 0.48), (sx * 0.36, -0.18, 0.74), M_LEATHER, bevel=0.04)
        F2.box(f"{name}Arm{sx}", (0.13, 0.66, 0.26), (sx * 0.355, 0.05, 0.40), M_LEATHER, bevel=0.04)
        tube(f"{name}ArmRoll{sx}", [Vector(F2.p(sx * 0.37, -0.25, 0.66)), Vector(F2.p(sx * 0.38, 0.1, 0.665)), Vector(F2.p(sx * 0.37, 0.38, 0.66))], 0.06, M_LEATHER, sides=10)
        for sy in (-1, 1):
            lathe(f"{name}Leg{sx}{sy}", [(0.0, 0.0), (0.022, 0.0), (0.03, 0.06), (0.025, 0.12), (0.035, 0.18), (0.035, 0.23), (0.0, 0.23)],
                  F2.p(sx * 0.33, sy * 0.3, 0.0), M_MAHOG, steps=8)
    return F2
CHAIR = (CX - 0.05, 0.95)
CH = wing_chair("FoggChair", CHAIR[0], CHAIR[1], 0.0)          # faces +Y, toward the clock
# a small pedestal table at the chair's side with the day's Times folded square
I.pedestal_table("ChairTable", (CHAIR[0] + 0.85, CHAIR[1] + 0.35), M_MAHOG, M_MAHOG, radius=0.3, height=0.68, feet=3)
M_NEWS = plain("M_Newsprint", K.srgb((0.76, 0.73, 0.64)), rough=0.9)
box("Times", (0.28, 0.38, 0.012), (CHAIR[0] + 0.85, CHAIR[1] + 0.35, 0.69), M_NEWS, rot=(0, 0, 0.3))

# ----------------------------------------------------------------------------- side table by the window: carpet-bag, Bradshaw, hat; mackintosh on a chair
ST = Frame((R.x0 + 0.38, -1.25), -math.pi / 2)      # its back to the west wall, facing +X
ST.box("SideTop", (1.1, 0.5, 0.03), (0, 0, 0.75), M_MAHOG, bevel=0.008)
ST.box("SideApron", (1.0, 0.42, 0.1), (0, 0, 0.65), M_MAHOG, bevel=0.004)
for sx in (-1, 1):
    for sy in (-1, 1):
        lathe(f"SideLeg{sx}{sy}", [(0.0, 0.0), (0.016, 0.0), (0.02, 0.1), (0.026, 0.4), (0.03, 0.55), (0.03, 0.65), (0.0, 0.65)],
              ST.p(sx * 0.47, sy * 0.18, 0), M_MAHOG, steps=8)
# Bradshaw: a fat red book, and the top hat beside it
ST.box("Bradshaw", (0.15, 0.21, 0.045), (-0.25, 0.02, 0.788), M_BRADSHAW, bevel=0.006)
ST.box("BradshawPages", (0.14, 0.205, 0.035), (-0.245, 0.022, 0.788), M_PAGES)
lathe("TopHat", [(0.0, 0.0), (0.16, 0.0), (0.17, 0.008), (0.15, 0.012), (0.10, 0.015), (0.095, 0.02), (0.092, 0.08), (0.094, 0.15), (0.098, 0.165), (0.0, 0.168)],
      ST.p(0.22, 0.0, 0.765), M_HAT, steps=24)
# the carpet-bag on the floor against the table leg
CB = Frame(ST.p(-0.15, 0.42, 0.0), ST.yaw + 0.25)
CB.box("BagBody", (0.46, 0.22, 0.30), (0, 0, 0.15), M_BAG, bevel=0.07)
CB.box("BagFrame", (0.48, 0.05, 0.03), (0, 0, 0.30), M_BRASS, bevel=0.01)
for sx in (-1, 1):
    tube(f"BagHandle{sx}", [Vector(CB.p(sx * 0.12, 0.0, 0.31)), Vector(CB.p(sx * 0.08, 0.0, 0.42)), Vector(CB.p(-sx * 0.0, 0.0, 0.44)) , Vector(CB.p(-sx * 0.08, 0.0, 0.42)), Vector(CB.p(-sx * 0.12, 0.0, 0.31))],
         0.011, plain("M_BagLeather", K.srgb((0.20, 0.11, 0.06)), rough=0.5), sides=6)
# a chair by the table with the mackintosh and the travelling-cloak thrown over its back
CHR = (R.x0 + 0.62, -2.15)
I.sabre_chair("MacChair", CHR, -math.pi / 2 - 0.35, M_MAHOG, M_LEATHER)
MF = Frame(CHR, -math.pi / 2 - 0.35)
verts = []; faces = []; uvs = []
nu, nv = 14, 12
for j in range(nv + 1):
    tv = j / nv
    for i in range(nu + 1):
        tu = i / nu; xx = (tu - 0.5) * 0.62
        # over the top rail (y -0.2, z 0.86) and falling front and back
        if tv < 0.45:
            s = tv / 0.45; yy = -0.20 + 0.07 * math.sin(s * 3.1416) - 0.09 * s; zz = 0.88 - 0.62 * (1 - s) * 0 - (0.6 * (1 - s)) + 0.0
            zz = 0.88 - 0.62 * (1 - s)
            yy = -0.27 + 0.0 * s
        else:
            s = (tv - 0.45) / 0.55; yy = -0.27 + 0.42 * s; zz = 0.88 - 0.42 * s * s
        fold = 0.025 * math.sin(tu * 15 + tv * 2) * (0.4 + tv)
        verts.append(MF.p(xx * (1 + 0.15 * tv), yy + fold, zz + 0.012)); uvs.append((tu, tv))
for j in range(nv):
    for i in range(nu):
        faces.append((j * (nu + 1) + i, j * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i))
mesh_from("Mackintosh", verts, faces, M_MAC, smooth=True, uvs=uvs)

# ----------------------------------------------------------------------------- bell push and speaking tube by the landing door
BP = R.at('S', DOOR_X - R.x0 + 0.85, 1.35, 0.0)
cyl("BellPlate", 0.045, 0.012, tuple(BP + Vector((0, 0.006, 0))), M_BRASS, verts=16, rot=(math.pi / 2, 0, 0))
sphere("BellButton", 0.012, tuple(BP + Vector((0, 0.016, 0))), M_PORCELAIN, seg=10)
ST_ = R.at('S', DOOR_X - R.x0 + 0.85, 1.55, 0.0)
tube("SpeakingTube", [ST_ + Vector((0, 0.03, -1.5)), ST_ + Vector((0, 0.03, 0.0)), ST_ + Vector((0, 0.10, 0.05))], 0.014, M_BRASS, sides=8)
lathe("SpeakingMouth", [(0.0, 0.0), (0.018, 0.0), (0.03, 0.03), (0.036, 0.06), (0.0, 0.06)], tuple(ST_ + Vector((0, 0.10, 0.05))), M_BRASS, steps=12, rot=(-math.pi / 2, 0, 0))
anchor("room.door", R.at('S', DOOR_X - R.x0))

# a landscape over the chair table side of the room (east wall, north of the fire), on cords from the picture rail
I.picture("Landscape", R, 'E', 4.95, 2.0, 0.7, 0.5, M_GILT, M_PICTURE)

# ----------------------------------------------------------------------------- the bedroom beyond the open door
BY0 = R.y1 + R.t
BX0, BX1, BY1 = R.x0, R.x0 + 3.2, BY0 + 3.4
box("BedFloor", (BX1 - BX0, BY1 - BY0, 0.04), ((BX0 + BX1) / 2, (BY0 + BY1) / 2, -0.02), M_FLOOR)
box("BedCeiling", (BX1 - BX0, BY1 - BY0, 0.05), ((BX0 + BX1) / 2, (BY0 + BY1) / 2, R.h + 0.025), M_CEIL)
box("BedWallN", (BX1 - BX0 + 0.4, 0.2, R.h + 0.1), ((BX0 + BX1) / 2, BY1 + 0.1, R.h / 2), M_PAPER)
box("BedWallW", (0.2, BY1 - BY0, R.h + 0.1), (BX0 - 0.1, (BY0 + BY1) / 2, R.h / 2), M_PAPER)
box("BedWallE", (0.2, BY1 - BY0, R.h + 0.1), (BX1 + 0.1, (BY0 + BY1) / 2, R.h / 2), M_PAPER)
for w_, x_, y_, L_, rot_ in (("N", (BX0 + BX1) / 2, BY1 - 0.01, BX1 - BX0, 0), ("W", BX0 + 0.01, (BY0 + BY1) / 2, BY1 - BY0, 90), ("E", BX1 - 0.01, (BY0 + BY1) / 2, BY1 - BY0, 90)):
    box(f"BedDado{w_}", (L_, 0.02, DADO), (x_, y_, DADO / 2), M_DADOWOOD, rot=(0, 0, math.radians(rot_)))
# the safe (green-painted iron, brass escutcheon and handle) against the far wall, seen through the door
SF = Frame((BED_X + 0.05, BY1 - 0.38), math.pi)
SF.box("SafePlinth", (0.72, 0.62, 0.08), (0, 0, 0.04), M_MAHOG, bevel=0.01)
SF.box("SafeBody", (0.66, 0.58, 0.98), (0, 0, 0.57), M_SAFE, bevel=0.025)
SF.box("SafeDoor", (0.54, 0.03, 0.84), (0, 0.29, 0.57), M_SAFE, bevel=0.02)
SF.box("SafeBand", (0.56, 0.035, 0.03), (0, 0.29, 0.93), M_GILT)
SF.box("SafePlate", (0.12, 0.04, 0.05), (0, 0.31, 0.86), M_BRASS, bevel=0.01)
cyl("SafeKeyhole", 0.03, 0.02, SF.p(0.16, 0.30, 0.55), M_BRASS, verts=12, rot=(math.pi / 2, 0, SF.yaw))
tube("SafeHandle", [Vector(SF.p(-0.16, 0.31, 0.62)), Vector(SF.p(-0.16, 0.36, 0.58)), Vector(SF.p(-0.16, 0.36, 0.46)), Vector(SF.p(-0.16, 0.31, 0.42))], 0.012, M_BRASS, sides=6)
# the wardrobe of numbered clothes to its left, doors shut
WD = Frame((BX0 + 0.35, BY1 - 1.35), -math.pi / 2)
WD.box("WardrobeBody", (1.5, 0.62, 2.25), (0, 0, 1.225), M_MAHOG, bevel=0.01)
WD.box("WardrobePlinth", (1.56, 0.66, 0.12), (0, 0, 0.06), M_MAHOG, bevel=0.01)
WD.box("WardrobeCornice", (1.62, 0.70, 0.1), (0, 0, 2.40), M_MAHOG, bevel=0.02)
for k in (-1, 1):
    WD.box(f"WardrobeDoor{k}", (0.68, 0.03, 1.9), (k * 0.37, 0.31, 1.25), M_MAHOG, bevel=0.015)
    sphere(f"WardrobeKnob{k}", 0.015, WD.p(k * 0.06, 0.34, 1.25), M_BRASS, seg=8)
# the foot of the bed, just in view on the right
box("BedEnd", (1.3, 0.06, 0.95), (BX1 - 0.9, BY0 + 0.9, 0.475), M_MAHOG, bevel=0.01)
box("BedLinen", (1.25, 1.9, 0.18), (BX1 - 0.9, BY0 + 1.9, 0.6), M_BEDLINEN, bevel=0.05)
box("BedRails", (1.3, 2.0, 0.22), (BX1 - 0.9, BY0 + 1.9, 0.4), M_MAHOG, bevel=0.01)
# daylight in the bedroom (its own window, out of sight on the west)
box("BedWindowGlow", (0.02, 1.0, 1.8), (BX0 + 0.005, BY0 + 2.6, 1.8), plain("M_BedWindow", (0.7, 0.72, 0.75), rough=1.0, emission=(0.62, 0.65, 0.70), strength=1.4))

# ----------------------------------------------------------------------------- lights
light_obj("Lamp.window", 'AREA', 420.0, (0.86, 0.90, 1.0), (R.x0 - 0.5, WIN_Y, 1.9), direction=(1, 0, -0.15), shape='RECTANGLE', size=1.3, size_y=2.4)
light_obj("Lamp.windowSky", 'AREA', 160.0, (0.80, 0.86, 1.0), (R.x0 + 0.2, WIN_Y, 3.0), direction=(1, 0, -0.6), shape='RECTANGLE', size=1.2, size_y=1.6)
for tag, p in BRACKETS.items():
    light_obj(f"Lamp.bracket{tag}", 'POINT', 14.0, (1.0, 0.80, 0.56), tuple(Vector(p) + Vector((-0.05, 0, 0))), shadow_soft_size=0.07)
light_obj("Lamp.fire", 'POINT', 22.0, (1.0, 0.48, 0.20), tuple(FIRE_BASE + Vector((-0.3, 0, 0.15))), shadow_soft_size=0.2)
light_obj("Lamp.bedroom", "AREA", 240.0, (0.85, 0.89, 1.0), (BX0 + 0.3, BY0 + 2.6, 1.8), direction=(1, -0.2, -0.2), shape='RECTANGLE', size=1.0, size_y=1.6)
world = bpy.data.worlds.new("Overcast"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.45, 0.50, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors and living-scene sources
LOOK_AT = Vector((CX, R.y1, 0))
fwd = (LOOK_AT - READER); fwd.z = 0; fwd.normalize()
anchor("reader.entrance", tuple(READER))
anchor("reader.look", tuple(READER + fwd + Vector((0, 0, EYE))))
anchor("scene.centre", (CHAIR[0], CHAIR[1], 0))
anchor("room.window", R.at('W', R.y1 - WIN_Y, 1.6))
anchor("room.bedroomSafe", SF.p(0, 0.4, 0))
E8.fx("fx.fire.gasfire", tuple(FIRE_BASE), 0.2)
sound("fire", "gasfire", tuple(FIRE_BASE + Vector((-0.2, 0, 0.1))))
sound("clock", "regulator", tuple(DIAL_C))

page = box("PagePreview", (0.4, 0.004, 0.55), tuple(READER + fwd * 0.6 + Vector((0, 0, EYE - 0.05))), plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9, emission=(0.80, 0.77, 0.69), strength=0.15),
           rot=(0, 0, math.atan2(fwd.y, fwd.x) - math.pi / 2))
K.apply_transforms()
for o in K.COLL.objects:
    if o.type == 'MESH' and o.data.materials and o.data.materials[0].name in ("M_SavilleRowView",):
        o.visible_shadow = False; o.visible_diffuse = False

# ----------------------------------------------------------------------------- cameras
EP = READER + Vector((0, 0, EYE))
def yawed(deg, dist=5.0, dz=-0.6):
    a = math.atan2(fwd.x, fwd.y) + math.radians(deg); return tuple(EP + Vector((math.sin(a), math.cos(a), 0)) * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(EP), yawed(0, 6, -0.6), lens=17),
    camera("Cam_Left", tuple(EP), yawed(-70, 6, -0.6), lens=17),
    camera("Cam_Right", tuple(EP), yawed(70, 6, -0.5), lens=17),
    camera("Cam_Behind", tuple(EP), yawed(180, 6, -0.5), lens=17),
    camera("Cam_Clock", (CX - 0.9, -0.4, 1.5), tuple(DIAL_C + Vector((0, 0, -0.35))), lens=26),
    camera("Cam_Bedroom", (BED_X + 0.6, 0.6, 1.5), (BED_X, BY1, 0.9), lens=24),
]
budget = K.print_budget(exclude=("PagePreview",) + tuple(o.name for o in I.RENDER_ONLY))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams=set(), default_exposure=0.4, captures_dir=ARGS.captures)

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
        "saville_row_house.gltf", cams, page=page,
        keep_names={"M_WindowGlass": "WindowGlass_plate", "M_GasGlobes": "MESH_GasGlobes", "M_SavilleRowView": "far.SavilleRow",
                    "M_Curtains": "cloth.curtain.window", "M_GasFireClay": "MESH_GasFire"},
        size_for={"M_FloorBoards": (1024, 256), "M_TurkeyCarpet": (2048, 128), "M_Wallpaper": (2048, 128), "M_Ceiling": (512, 64),
                  "M_Plaster": (1024, 128), "M_DadoMahogany": (1024, 256), "M_Mahogany": (1024, 256), "M_WhiteMarble": (1024, 256),
                  "M_Curtains": (1024, 256), "M_ChairLeather": (1024, 256), "M_Gilt": (512, 128), "M_SafeGreen": (512, 128),
                  "M_Brass": (256, 64), "M_Iron": (256, 128), "M_SilverDial": (256, 64), "M_Enamel": (128, 32), "M_CarpetBag": (512, 64),
                  "M_Mackintosh": (512, 64), "M_Landscape": (512, 64), "M_GasFireClay": (256, 64)},
        default_size=(256, 64))
print("DONE")
