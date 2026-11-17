"""
Fable step-in room: the upstairs bedroom at the Spouter-Inn, New Bedford (Moby-Dick, chapter 4, "The Counterpane").

"Upon waking next morning about daylight, I found Queequeg's arm thrown over me ... The counterpane was of patchwork,
full of odd little parti-coloured squares and triangles" ... (chapter 3) "a small room, cold as a clam, and furnished,
sure enough, with a prodigious bed, almost big enough indeed for any four harpooneers to sleep abreast" ... "the rest of
the apartment ... there was no fire-place ... a papered fireboard representing a man striking a whale" ... "a rude
shelf; the four walls, and a papered fireboard" ... "a hammock lashed up, and thrown upon the floor in one corner; also
a large seaman's bag ... a parcel of outlandish bone fish hooks on the shelf over the fire-place, and a tall harpoon
standing at the head of the bed" ... "There were no curtains to the window, and the street being very narrow, the house
opposite commanded a plain view into the room".

The "second floor back" of the inn, a Sunday dawn in December, c.1840s: about 4 x 4.5 m under a low ceiling, bare wide
pine boards, old lime plaster gone grey and scaling, a low chair-rail. The prodigious bed (head against the north wall),
its patchwork counterpane rumpled and thrown back; the crazy old sea chest under the window doing duty as washstand and
centre table, with a basin, a ewer and a guttered tallow candle; the papered fireboard closing the fireplace on the west
wall, the man striking the whale printed on it, bone fish-hooks on the shelf above; Queequeg's tall harpoon at the head
of the bed, his hammock lashed up in a corner, the seaman's bag, his heavy grego over a chair, his tall beaver hat and
boots on the floor. No people, no embalmed head.

Light: cold, pale dawn through the uncurtained east window (blue-grey sky over the house opposite, a little pink low on
the horizon); the candle is out.
Reader: by the foot of the bed, facing it (north); the window on the right, the fireboard on the left.

  blender -b -P blender/build_spouter_inn_bedroom.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_spouter_inn_bedroom.py -- --render --samples 48 --res 1400 --cams reader,left,right,behind,bed
  blender -b -P blender/build_spouter_inn_bedroom.py -- --export
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b5 as S
import pride_kit as K
import pride_interior as I
import mobydick_kit as MK
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, Canvas, anchor, sound, light_obj)

SID = "spouter-inn-bedroom"
ARGS = S.setup(SID, seed=1851)
scene = K.scene
scene.cycles.max_bounces = 8; scene.cycles.diffuse_bounces = 5
rng = random.Random(1851)

R = I.Room(-2.0, 2.0, -2.25, 2.25, 2.3, t=0.3)
READER = Vector((0.25, -1.45, 0))
WIN_Y = 0.6                          # window centre on the east wall

# ----------------------------------------------------------------------------- materials
def plaster(name="M_OldPlaster"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1500, -400))
    n = noise_(nt, co, 1.3, 6, 0.6, loc=(-1200, 0)); n2 = noise_(nt, co, 8.0, 5, 0.65, loc=(-1200, -200))
    stain = noise_(nt, co, 0.5, 4, 0.6, distortion=0.8, loc=(-1200, 200))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1000, 0)), c4(K.srgb((0.66, 0.63, 0.56))), c4(K.srgb((0.76, 0.73, 0.66))), (-800, 0))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, stain.outputs["Fac"], 0.55, 0.75, 0, 0.35, (-1000, 200)), col, (0.62, 0.52, 0.38, 1), (-650, 0))
    n4 = noise_(nt, co, 2.2, 5, 0.6, loc=(-1300, -350))
    scale = maprange(nt, n4.outputs["Fac"], 0.66, 0.7, 0, 0.6, (-1000, -200))       # patches where the skim has flaked
    col = mix_rgb(nt, 'MIX', scale, col, c4(K.srgb((0.58, 0.54, 0.47))), (-500, 0))
    low = maprange(nt, s.outputs["Z"], 0.0, 0.6, 0.25, 0.0, (-1000, -400))
    col = mix_rgb(nt, 'MULTIPLY', low, col, (0.5, 0.46, 0.4, 1), (-400, 0))
    col = K.ao_mul(nt, col, 0.3, 0.45, (-300, -500))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    bump_from(nt, b, math_(nt, 'ADD', n2.outputs["Fac"], math_(nt, 'MULTIPLY', scale, 0.6, (-900, -600)), (-700, -600)), 0.3, 0.005)
    return m

M_PLASTER = plaster()
M_FLOOR = I.boards_mat("M_PineBoards", light=(0.30, 0.22, 0.13), dark=(0.13, 0.09, 0.05), width=0.3, axis='Y', wax=0.75)
M_TIMBER = MK.timber_mat("M_OldTimber", base=(0.13, 0.09, 0.055), dark=(0.04, 0.028, 0.018), light=(0.22, 0.16, 0.10), along='X', rough=(0.5, 0.85), grime=0.5)
M_BEDWOOD = MK.timber_mat("M_BedWood", base=(0.16, 0.10, 0.055), dark=(0.05, 0.03, 0.018), light=(0.26, 0.17, 0.10), along='Z', rough=(0.4, 0.75), grime=0.4, polish=0.15)
M_CHEST = MK.timber_mat("M_SeaChest", base=(0.20, 0.17, 0.12), dark=(0.06, 0.05, 0.035), light=(0.32, 0.27, 0.19), along='X', rough=(0.55, 0.85), grime=0.6, salt=0.25)
M_IRON = MK.iron_mat("M_Iron", rust=0.5)
M_LINEN = noisy("M_Sheets", [K.srgb((0.82, 0.79, 0.72)), K.srgb((0.74, 0.71, 0.64))], scale=40, rough=0.9, bump=0.2, bump_dist=0.001)
M_CANVAS = noisy("M_Canvas", [K.srgb((0.58, 0.54, 0.44)), K.srgb((0.48, 0.44, 0.35)), K.srgb((0.62, 0.58, 0.48))], scale=14, rough=0.92, bump=0.5, bump_dist=0.002)
M_ROPE = noisy("M_Rope", [K.srgb((0.46, 0.38, 0.24)), K.srgb((0.36, 0.29, 0.18))], scale=80, rough=0.9, stretch=(1, 1, 6), bump=0.6)
M_GREGO = noisy("M_Grego", [K.srgb((0.10, 0.10, 0.11)), K.srgb((0.15, 0.14, 0.14)), K.srgb((0.08, 0.08, 0.09))], scale=18, rough=0.95, bump=0.8, bump_dist=0.003, sheen=0.5)
M_BEAVER = noisy("M_Beaver", [K.srgb((0.07, 0.05, 0.04)), K.srgb((0.12, 0.09, 0.07))], scale=30, rough=0.6, bump=0.3, sheen=0.8)
M_BOOT = noisy("M_Boots", [K.srgb((0.09, 0.06, 0.04)), K.srgb((0.16, 0.11, 0.07))], scale=14, rough=(0.45, 0.8), bump=0.4)
M_BONE = noisy("M_Bone", [K.srgb((0.82, 0.77, 0.64)), K.srgb((0.70, 0.64, 0.52))], scale=40, rough=0.5, bump=0.2)
M_CROCK = noisy("M_Crockery", [K.srgb((0.86, 0.85, 0.80)), K.srgb((0.78, 0.77, 0.72))], scale=30, rough=0.2, bump=0.05)
M_TALLOW = plain("M_Tallow", K.srgb((0.86, 0.80, 0.62)), rough=0.5)
M_PANE = new_mat("M_Pane")[0]
nt = M_PANE.node_tree
for n_ in list(nt.nodes): nt.nodes.remove(n_)
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (0.92, 0.94, 0.95, 1)
nt.links.new(tr.outputs["BSDF"], o_.inputs["Surface"])
M_SASH = I.joinery_mat("M_SashPaint", K.srgb((0.70, 0.68, 0.62)), rough=0.5)


def patchwork(name="M_Patchwork"):
    """'odd little parti-coloured squares and triangles': a grid of 9 cm squares, about half split on a diagonal,
    each patch its own faded cotton (turkey red, indigo, buff, brown, chintz green, sprigged white), seams darker."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    mp = node(nt, "ShaderNodeMapping", (-1700, 0)); mp.inputs["Scale"].default_value = (11.0, 11.0, 11.0); nt.links.new(co, mp.inputs["Vector"])
    sp = sep_xyz(nt, mp.outputs["Vector"], (-1500, 0))
    fx = math_(nt, 'FRACT', sp.outputs["X"], None, (-1300, 100)); fy = math_(nt, 'FRACT', sp.outputs["Y"], None, (-1300, -50))
    cx = math_(nt, 'FLOOR', sp.outputs["X"], None, (-1300, 250)); cy = math_(nt, 'FLOOR', sp.outputs["Y"], None, (-1300, 400))
    cell = node(nt, "ShaderNodeCombineXYZ", (-1150, 300)); nt.links.new(cx, cell.inputs["X"]); nt.links.new(cy, cell.inputs["Y"])
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1000, 300), noise_dimensions='3D'); nt.links.new(cell.outputs[0], wn.inputs["Vector"])
    cell2 = node(nt, "ShaderNodeCombineXYZ", (-1150, 500)); nt.links.new(cx, cell2.inputs["X"]); nt.links.new(cy, cell2.inputs["Y"]); cell2.inputs["Z"].default_value = 7.3
    wn2 = node(nt, "ShaderNodeTexWhiteNoise", (-1000, 500), noise_dimensions='3D'); nt.links.new(cell2.outputs[0], wn2.inputs["Vector"])
    # which side of the diagonal (only in cells that are split: wn2 > 0.45)
    diag = math_(nt, 'GREATER_THAN', fx, fy, (-1100, 0))
    split = math_(nt, 'GREATER_THAN', wn2.outputs["Value"], 0.45, (-850, 500))
    pick = math_(nt, 'FRACT', math_(nt, 'ADD', wn.outputs["Value"], math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', diag, split, (-850, 100)), 0.37, (-750, 100)), (-650, 200)), None, (-550, 200))
    pal = ramp(nt, [(0.0, c4(K.srgb((0.56, 0.16, 0.12)))), (0.14, c4(K.srgb((0.20, 0.24, 0.40)))), (0.28, c4(K.srgb((0.70, 0.62, 0.44)))), (0.42, c4(K.srgb((0.36, 0.24, 0.14)))),
                    (0.56, c4(K.srgb((0.34, 0.42, 0.30)))), (0.70, c4(K.srgb((0.80, 0.76, 0.66)))), (0.84, c4(K.srgb((0.62, 0.36, 0.26)))), (1.0, c4(K.srgb((0.30, 0.34, 0.46))))],
               (-400, 200), interp='CONSTANT')
    nt.links.new(pick, pal.inputs["Fac"])
    # small print within patches
    pr = noise_(nt, co, 90.0, 2, 0.5, loc=(-700, -200))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, pal.outputs["Color"], maprange(nt, pr.outputs["Fac"], 0.3, 0.7, 0.8, 1.1, (-500, -200)), (-200, 200))
    # seams: dark lines at the cell edges and on the diagonal of split cells
    ex = math_(nt, 'MINIMUM', math_(nt, 'MINIMUM', fx, math_(nt, 'SUBTRACT', 1.0, fx, (-1100, -250)), (-950, -250)),
               math_(nt, 'MINIMUM', fy, math_(nt, 'SUBTRACT', 1.0, fy, (-1100, -400)), (-950, -400)), (-800, -300))
    dd = math_(nt, 'MULTIPLY', math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', fx, fy, (-1100, -550)), None, (-950, -550)), 0.7071, (-850, -550))
    dd = math_(nt, 'ADD', dd, math_(nt, 'SUBTRACT', 1.0, split, (-850, -700)), (-750, -600))
    seam = maprange(nt, math_(nt, 'MINIMUM', ex, dd, (-650, -400)), 0.0, 0.04, 0.55, 1.0, (-500, -400))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, seam, (-50, 200))
    fade = noise_(nt, co, 1.5, 3, 0.5, loc=(-700, -800))
    col = mix_rgb(nt, 'MIX', maprange(nt, fade.outputs["Fac"], 0.3, 0.7, 0.1, 0.3, (-400, -800)), col, (0.7, 0.66, 0.58, 1), (100, 200))
    col = K.ao_mul(nt, col, 0.15, 0.5, (150, -500))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.92; b.inputs["Sheen Weight"].default_value = 0.4
    bump_from(nt, b, seam, 0.4, 0.003)
    return m
M_QUILT = patchwork()


def fireboard_image(W=768, H=640):
    """A cheap coloured woodcut print pasted on the fireboard: a whaleboat in a green-grey swell, a man standing in the
    bow darting his harpoon into a great dark sperm whale breaching alongside, spray; a border; then smoke-dulled,
    foxed, and the paper torn and peeling at one corner."""
    cv = Canvas(W, H, bg=(0.80, 0.74, 0.60, 1))
    # sky and sea
    for y in range(0, int(H * 0.45), 6):
        cv.line((0, y), (W, y), 3.2, 3.2, (0.62 + 0.0004 * y, 0.66, 0.66, 0.5))
    for y in range(int(H * 0.45), H, 5):
        t = (y - H * 0.45) / (H * 0.55)
        cv.line((0, y), (W, y + 6 * math.sin(y * 0.3)), 2.6, 2.6, (0.30 - 0.1 * t, 0.40 - 0.1 * t, 0.36 - 0.08 * t, 0.85))
    # swell crests
    r = random.Random(3)
    for k in range(40):
        x = r.uniform(0, W); y = r.uniform(H * 0.48, H * 0.95)
        cv.line((x - 30, y), (x + 30, y - 6), 2, 1, (0.85, 0.86, 0.80, 0.8))
    # the whale: a long dark body rising out of the sea to the right, blunt square head toward the boat, flukes behind
    cv.ellipse(W * 0.66, H * 0.52, W * 0.27, H * 0.11, math.radians(-12), (0.10, 0.10, 0.11, 1))
    cv.ellipse(W * 0.47, H * 0.47, W * 0.09, H * 0.1, math.radians(-12), (0.10, 0.10, 0.11, 1))
    cv.line((W * 0.88, H * 0.55), (W * 0.95, H * 0.36), 16, 6, (0.10, 0.10, 0.11, 1))
    cv.ellipse(W * 0.93, H * 0.31, 40, 12, math.radians(-30), (0.10, 0.10, 0.11, 1))
    cv.ellipse(W * 0.98, H * 0.36, 34, 10, math.radians(25), (0.10, 0.10, 0.11, 1))
    cv.ellipse(W * 0.44, H * 0.47, 7, 5, 0, (0.88, 0.86, 0.8, 1))      # eye
    cv.line((W * 0.40, H * 0.53), (W * 0.52, H * 0.55), 2, 2, (0.75, 0.74, 0.68, 1))   # jaw line
    # spout and spray
    for k in range(14):
        a = math.radians(r.uniform(-120, -60)); L = r.uniform(30, 80)
        cv.line((W * 0.5, H * 0.38), (W * 0.5 + math.cos(a) * L, H * 0.38 + math.sin(a) * L), 3, 1, (0.92, 0.92, 0.88, 0.8))
    # the boat: a long low hull, oars, the harpooneer standing in the bow
    cv.ellipse(W * 0.23, H * 0.62, W * 0.17, H * 0.035, math.radians(4), (0.38, 0.25, 0.14, 1))
    cv.line((W * 0.07, H * 0.6), (W * 0.40, H * 0.63), 3, 3, (0.78, 0.74, 0.62, 1))
    for k in range(5):
        x = W * (0.1 + 0.05 * k); cv.line((x, H * 0.61), (x - 40, H * 0.72), 2.5, 2.0, (0.55, 0.45, 0.30, 1))
        cv.ellipse(x - 2, H * 0.575, 7, 9, 0, (0.20, 0.18, 0.18, 1))      # rowers' heads
    # harpooneer: legs, body leaning back, arm up, the iron flying toward the whale with its line
    bx, by = W * 0.36, H * 0.6
    cv.line((bx, by), (bx - 4, by - 40), 4, 4, (0.15, 0.14, 0.14, 1)); cv.line((bx + 8, by), (bx + 2, by - 40), 4, 4, (0.15, 0.14, 0.14, 1))
    cv.line((bx - 1, by - 40), (bx - 8, by - 82), 7, 6, (0.30, 0.28, 0.40, 1))
    cv.ellipse(bx - 9, by - 92, 9, 10, 0, (0.70, 0.55, 0.45, 1))
    cv.line((bx - 6, by - 78), (bx + 18, by - 112), 3, 3, (0.30, 0.28, 0.40, 1))
    cv.line((bx + 18, by - 112), (W * 0.43, H * 0.46), 1.8, 1.4, (0.20, 0.18, 0.15, 1))
    cv.line((bx + 18, by - 108), (bx + 10, by - 120), 2, 2, (0.30, 0.25, 0.18, 1))
    for k in range(20):
        t = k / 20; cv.line((bx + 18 + (W * 0.43 - bx - 18) * t, by - 112 + 30 * math.sin(t * 3)), (bx + 18 + (W * 0.43 - bx - 18) * (t + 0.05), by - 112 + 30 * math.sin((t + 0.05) * 3)), 0.8, 0.8, (0.3, 0.25, 0.2, 1))
    a = cv.a
    # border, smoke, foxing, the torn corner
    yy, xx = cv.yy, cv.xx
    border = (np.minimum(np.minimum(xx, W - xx), np.minimum(yy, H - yy)) < 22)
    a[border, :3] = np.array([0.32, 0.22, 0.14])
    inner = (np.minimum(np.minimum(xx, W - xx), np.minimum(yy, H - yy)) < 28) & ~border
    a[inner, :3] = np.array([0.78, 0.72, 0.58])
    nz = MK_fbm(H, W)
    a[..., :3] *= (0.62 + 0.3 * nz)[..., None] * np.array([1.0, 0.95, 0.85])
    fox = np.random.RandomState(5).rand(H, W) > 0.9985
    for (y, x) in zip(*np.nonzero(fox)):
        cv.ellipse(x, y, 4 + (x % 7), 4 + (y % 5), 0, (0.45, 0.30, 0.18, 0.4))
    tear = (xx > W * 0.8) & (yy < H * 0.18) & ((xx - W * 0.8) * 0.9 > (yy - 0) * 1.2 - 10)
    a[tear, :3] = np.array([0.42, 0.38, 0.30])
    a[..., 3] = 1
    return K.np_image("A_Fireboard", np.clip(a, 0, 1))


def MK_fbm(H, W):
    out = np.zeros((H, W), np.float32); rs = np.random.RandomState(9); amp = 1; tot = 0
    for o in range(5):
        g = rs.rand(4 * 2 ** o + 1, 4 * 2 ** o + 1).astype(np.float32)
        ys = np.linspace(0, g.shape[0] - 1, H); xs = np.linspace(0, g.shape[1] - 1, W)
        y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int); y1 = np.minimum(y0 + 1, g.shape[0] - 1); x1 = np.minimum(x0 + 1, g.shape[1] - 1)
        fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
        out += amp * (g[y0][:, x0] * (1 - fx) * (1 - fy) + g[y0][:, x1] * fx * (1 - fy) + g[y1][:, x0] * (1 - fx) * fy + g[y1][:, x1] * fx * fy)
        tot += amp; amp *= 0.5
    return out / tot


A_FIRE = fireboard_image()
M_FIREBOARD = K.image_mat("M_Fireboard", A_FIRE, rough=0.8)

# ----------------------------------------------------------------------------- walls, window, door, floor, ceiling and beams
WIN = I.sash_window("Win", R, 'E', WIN_Y - R.y0, 0.85, 0.8, 1.2, M_SASH, M_PANE, M_SASH, panes=(2, 3), curtain_mat=None)
I.six_panel_door("Door", R, 'S', 1.25 - R.x0, 0.78, 1.95, M_TIMBER, M_TIMBER, M_IRON, open_deg=0, hinge_left=True)
I.build_walls(R, M_PLASTER)
box("Floor", (R.x1 - R.x0 + 0.6, R.y1 - R.y0 + 0.6, 0.04), (0, 0, -0.02), M_FLOOR)
box("Ceiling", (R.x1 - R.x0 + 0.6, R.y1 - R.y0 + 0.6, 0.04), (0, 0, R.h + 0.02), M_PLASTER)
for k, y in enumerate((-1.3, 0.1, 1.5)):
    box(f"Beam{k}", (R.x1 - R.x0, 0.2, 0.18), (0, y, R.h - 0.18), M_TIMBER, bevel=0.015)
I.moulding_runs(R, "Skirting", [(0.0, 0.0), (0.025, 0.0), (0.025, 0.16), (0.0, 0.16)], 0.0, M_TIMBER)
I.moulding_runs(R, "ChairRail", [(0.0, 0.0), (0.02, 0.0), (0.02, 0.06), (0.0, 0.06)], 0.86, M_TIMBER, z_band=(0.86, 0.92))

# ----------------------------------------------------------------------------- the prodigious bed
BW, BL = 2.3, 2.05                    # wide enough for four harpooneers abreast
B0 = Vector((-0.15, R.y1 - BL / 2 - 0.05, 0))
BF = Frame((B0.x, B0.y), math.pi)     # local +Y toward the foot (-Y world)
for sx in (-1, 1):
    BF.box(f"BedPostHead{sx}", (0.09, 0.09, 1.2), (sx * (BW / 2 + 0.02), -BL / 2, 0 + (1.2) / 2), M_BEDWOOD, bevel=0.01)
    BF.box(f"BedPostFoot{sx}", (0.09, 0.09, 0.62), (sx * (BW / 2 + 0.02), BL / 2, 0 + (0.62) / 2), M_BEDWOOD, bevel=0.01)
    BF.box(f"BedRailSide{sx}", (0.05, BL, 0.16), (sx * (BW / 2 + 0.02), 0, 0.22 + (0.16) / 2), M_BEDWOOD, bevel=0.006)
    sphere(f"BedKnob{sx}", 0.05, BF.p(sx * (BW / 2 + 0.02), BL / 2, 0.66), M_BEDWOOD, seg=10)
BF.box("BedHeadBoard", (BW, 0.05, 0.6), (0, -BL / 2, 0.45 + (0.6) / 2), M_BEDWOOD, bevel=0.006)
BF.box("BedHeadRail", (BW + 0.1, 0.07, 0.07), (0, -BL / 2, 1.08), M_BEDWOOD, bevel=0.01)
BF.box("BedFootBoard", (BW, 0.05, 0.3), (0, BL / 2, 0.24 + (0.3) / 2), M_BEDWOOD, bevel=0.006)
BF.box("BedFootRail", (BW + 0.08, 0.06, 0.06), (0, BL / 2, 0.55), M_BEDWOOD, bevel=0.01)
# a straw tick and feather bed, sagging in the middle
mv = []; mf = []
NX, NY = 14, 12
for j in range(NY + 1):
    for i in range(NX + 1):
        u = i / NX - 0.5; v = j / NY - 0.5
        z = 0.5 - 0.05 * math.cos(math.pi * u) * math.cos(math.pi * v) * 0.0 - 0.04 * (1 - (2 * u) ** 2) * (1 - (2 * v) ** 2)
        mv.append(BF.p(u * BW * 0.98, v * BL * 0.97, z))
for j in range(NY):
    for i in range(NX): mf.append((j * (NX + 1) + i, j * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i))
BF.box("Tick", (BW * 0.98, BL * 0.97, 0.2), (0, 0, 0.28 + (0.2) / 2), M_LINEN, bevel=0.06)
mesh_from("Sheet", mv, mf, M_LINEN, smooth=True)
# pillows (two, dented)
for k, x in enumerate((-0.55, 0.5)):
    p = sphere(f"Pillow{k}", 0.3, BF.p(x, -BL / 2 + 0.3, 0.6), M_LINEN, seg=14, scale=(1.0, 0.55, 0.22))
    for v in p.data.vertices: v.co.z -= 0.02 * math.exp(-((v.co.x) ** 2 + (v.co.y) ** 2) / 0.02)
# the counterpane: thrown back from the head, falling over the foot and sides, rumpled
cv_ = []; cf = []
NX, NY = 26, 22
for j in range(NY + 1):
    for i in range(NX + 1):
        u = (i / NX - 0.5) * (BW + 0.5); v = (j / NY) * (BL + 0.45) - BL / 2 + 0.55   # from 0.55 m below the head to over the foot
        z = 0.53
        over_x = abs(u) - BW / 2
        if over_x > 0: z = 0.53 - over_x * 1.6; u = math.copysign(BW / 2 + 0.03 + over_x * 0.15, u)
        over_y = v - BL / 2
        if over_y > 0: z = min(z, 0.53 - over_y * 1.6); v = BL / 2 + 0.04 + over_y * 0.15
        # rumples: lumps where a body lay and a turned-back fold at the top edge
        z += 0.05 * noise.noise(Vector((u * 1.6, v * 1.6, 0.4))) + 0.035 * noise.noise(Vector((u * 4.1, v * 4.1, 2.0)))
        if j == 0: z += 0.06
        if j == 1: z += 0.03
        cv_.append(BF.p(u, v, max(0.12, z)))
for j in range(NY):
    for i in range(NX): cf.append((j * (NX + 1) + i, j * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i))
cp = mesh_from("Counterpane", cv_, cf, M_QUILT, smooth=True)
cp.modifiers.new("Solid", 'SOLIDIFY').thickness = 0.015
# the turned-back top fold
fv = []; ff = []
for i in range(NX + 1):
    u = (i / NX - 0.5) * BW * 0.96
    for k, (dv, dz) in enumerate(((0.55, 0.6), (0.35, 0.64), (0.25, 0.6))):
        fv.append(BF.p(u, -BL / 2 + dv + 0.02 * noise.noise(Vector((u * 3, k, 0))), dz + 0.02 * noise.noise(Vector((u * 2, k, 1)))))
for i in range(NX):
    for k in range(2): ff.append((i * 3 + k, i * 3 + k + 1, (i + 1) * 3 + k + 1, (i + 1) * 3 + k))
mesh_from("CounterpaneFold", fv, ff, M_QUILT, smooth=True)
anchor("room.bed", tuple(B0))

# ----------------------------------------------------------------------------- the tall harpoon at the head of the bed (north-east corner)
HP = Vector(BF.p(-(BW / 2 + 0.2), -BL / 2 + 0.05, 0))
HP = Vector((B0.x + BW / 2 + 0.25, R.y1 - 0.12, 0))
lean = Vector((-0.04, -0.03, 1)).normalized()
tube("HarpoonPole", [HP, HP + lean * 1.85], [0.022, 0.018], plain("M_HickoryPole", K.srgb((0.42, 0.33, 0.22)), rough=0.6), sides=7)
shank0 = HP + lean * 1.85
tube("HarpoonShank", [shank0, shank0 + lean * 0.42], [0.009, 0.008], M_IRON, sides=6)
tip = shank0 + lean * 0.42
side = Vector((1, 0, 0))
hv = [tuple(tip - side * 0.035 - lean * 0.02), tuple(tip + lean * 0.16), tuple(tip + side * 0.008), tuple(tip - side * 0.035 - lean * 0.06)]
mesh_from("HarpoonHead", hv, [(0, 1, 2), (0, 2, 3)], M_IRON).modifiers.new("Solid", 'SOLIDIFY').thickness = 0.006
for k in range(4):
    tube(f"HarpoonWhip{k}", [HP + lean * (1.84 + k * 0.012) + Vector((0.024, 0, 0)), HP + lean * (1.84 + k * 0.012) + Vector((-0.024, 0.0, 0))], 0.004, M_ROPE, sides=4)
anchor("room.harpoon", tuple(HP))

# ----------------------------------------------------------------------------- the crazy old sea chest under the window, washstand and centre table
SC = Frame((R.x1 - 0.42, WIN_Y), math.pi / 2)        # local +Y toward -X (into the room)
SC.box("ChestBody", (0.95, 0.5, 0.45), (0, 0, 0.02 + (0.45) / 2), M_CHEST, bevel=0.012)
SC.box("ChestLid", (0.98, 0.53, 0.06), (0, 0, 0.47 + (0.06) / 2), M_CHEST, bevel=0.015)
for sx in (-1, 1):
    SC.box(f"ChestBecket{sx}", (0.03, 0.12, 0.05), (sx * 0.5, 0, 0.32), M_ROPE, bevel=0.01)
    SC.box(f"ChestCleat{sx}", (0.06, 0.5, 0.04), (sx * 0.4, 0, 0.0 + (0.04) / 2), M_CHEST, bevel=0.008)
for k in range(2): SC.box(f"ChestStrap{k}", (0.03, 0.54, 0.5), (-0.3 + 0.6 * k, 0, 0.02 + (0.5) / 2), M_IRON)
SC.box("ChestHasp", (0.06, 0.02, 0.1), (0, 0.265, 0.38), M_IRON)
CT = 0.53
lathe("Basin", [(0.0, 0.0), (0.08, 0.0), (0.18, 0.08), (0.19, 0.095), (0.18, 0.095), (0.075, 0.01), (0.0, 0.01)], SC.p(-0.18, 0.0, CT), M_CROCK, steps=24)
lathe("Ewer", [(0.0, 0.0), (0.07, 0.0), (0.09, 0.08), (0.085, 0.18), (0.055, 0.25), (0.06, 0.3), (0.0, 0.3)], SC.p(0.25, -0.05, CT), M_CROCK, steps=16)
tube("EwerHandle", [SC.p(0.25, -0.13, CT + 0.25), SC.p(0.25, -0.18, CT + 0.2), SC.p(0.25, -0.16, CT + 0.1)], 0.012, M_CROCK, sides=5)
# the candle, guttered in a tin stick: a stub with a run of tallow down one side
lathe("CandleTin", [(0.0, 0.0), (0.06, 0.0), (0.065, 0.01), (0.015, 0.012), (0.014, 0.05), (0.0, 0.05)], SC.p(0.32, 0.18, CT), M_IRON, steps=14)
lathe("CandleStub", [(0.0, 0.04), (0.012, 0.04), (0.012, 0.09), (0.009, 0.1), (0.0, 0.1)], SC.p(0.32, 0.18, CT), M_TALLOW, steps=10)
sphere("TallowRun", 0.012, SC.p(0.33, 0.19, CT + 0.06), M_TALLOW, seg=6, scale=(0.7, 0.7, 2.0))
SC.box("Towel", (0.012, 0.32, 0.38), (0.5, 0.0, 0.18 + (0.38) / 2), M_LINEN, bevel=0.004)
anchor("room.seaChest", SC.p(0, 0, 0))

# ----------------------------------------------------------------------------- the fireplace closed by the papered fireboard, the shelf with bone fish-hooks (west wall)
FP = Frame((R.x0, -0.35), -math.pi / 2)      # local +Y = +X world (into the room)
FP.box("Breast", (1.3, 0.22, R.h), (0, 0.0, R.h / 2), M_PLASTER)
FP.box("SurroundL", (0.12, 0.05, 0.95), (-0.48, 0.13, 0.0 + (0.95) / 2), M_TIMBER, bevel=0.005)
FP.box("SurroundR", (0.12, 0.05, 0.95), (0.48, 0.13, 0.0 + (0.95) / 2), M_TIMBER, bevel=0.005)
FP.box("SurroundTop", (1.08, 0.05, 0.12), (0, 0.13, 0.95), M_TIMBER, bevel=0.005)
FP.box("HearthStone", (1.15, 0.4, 0.03), (0, 0.3, 0.0 + (0.03) / 2), noisy("M_Hearth", [K.srgb((0.36, 0.34, 0.31)), K.srgb((0.28, 0.27, 0.25))], scale=5, rough=0.8, bump=0.3), bevel=0.005)
# the fireboard: a board filling the opening, the print pasted on its face
fb = FP.box("FireboardBack", (0.86, 0.025, 0.9), (0, 0.125, 0.03 + (0.9) / 2), M_TIMBER)
fbc = Vector(FP.p(0, 0.139, 0.48))
nrm = Vector(FP.v(0, 1, 0)); along = Vector(FP.v(1, 0, 0))
pv = [tuple(fbc - along * 0.42 + Vector((0, 0, -0.43))), tuple(fbc + along * 0.42 + Vector((0, 0, -0.43))), tuple(fbc + along * 0.42 + Vector((0, 0, 0.43))), tuple(fbc - along * 0.42 + Vector((0, 0, 0.43)))]
pr = mesh_from("FireboardPrint", pv, [(0, 1, 2, 3)], M_FIREBOARD, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
pr.data.uv_layers[0].name = "UVMap"
FP.box("Shelf", (1.2, 0.2, 0.035), (0, 0.18, 1.12), M_TIMBER, bevel=0.006)
for sx in (-1, 1): FP.box(f"ShelfBracket{sx}", (0.03, 0.15, 0.12), (sx * 0.5, 0.15, 1.04), M_TIMBER)
# a parcel of outlandish bone fish-hooks: curved bone shanks with points, a few tied in a bundle with sennit
for k in range(9):
    x = -0.4 + 0.07 * k + rng.uniform(-0.02, 0.02); yv = 0.16 + rng.uniform(-0.04, 0.04)
    a = rng.uniform(0, 6.28); d = Vector((math.cos(a), math.sin(a), 0)) * 0.05
    p0 = Vector(FP.p(x, yv, 1.145)); p1 = p0 + d * 1.6; p2 = p1 + Vector((-d.y, d.x, 0)) * 0.6 + Vector((0, 0, 0.004)); p3 = p2 - d * 0.5
    tube(f"Hook{k}", [p0, p0 + d * 0.8, p1, p2, p3], [0.006, 0.006, 0.005, 0.004, 0.002], M_BONE, sides=5)
for k in range(3):
    tube(f"Sennit{k}", [FP.p(0.25 + 0.04 * k, 0.12, 1.15), FP.p(0.27 + 0.04 * k, 0.22, 1.15)], 0.005, M_ROPE, sides=4)
anchor("room.fireboard", FP.p(0, 0.3, 0))

# ----------------------------------------------------------------------------- Queequeg's things: hammock, seaman's bag, grego on a chair, beaver hat, boots
# the hammock lashed up and thrown on the floor in the south-west corner: a long canvas roll with seven turns of lashing
HM = Frame((R.x0 + 0.45, R.y0 + 0.75), math.radians(70))
pts = [HM.p(-0.8, 0, 0.11), HM.p(-0.3, 0.02, 0.12), HM.p(0.3, -0.02, 0.12), HM.p(0.8, 0.03, 0.11)]
tube("HammockRoll", pts, [0.07, 0.11, 0.11, 0.07], M_CANVAS, sides=10)
for k in range(7):
    t = -0.7 + 0.23 * k; c = Vector(HM.p(t, 0, 0.12))
    ring = [tuple(c + Vector(HM.v(0, math.cos(a) * 0.115, math.sin(a) * 0.115))) for a in [2 * math.pi * q / 10 for q in range(11)]]
    tube(f"HammockLashing{k}", ring, 0.008, M_ROPE, sides=4)
for sgn in (-1, 1):
    tube(f"HammockClew{sgn}", [HM.p(sgn * 0.8, 0, 0.1), HM.p(sgn * 1.0, 0.1 * sgn, 0.03), HM.p(sgn * 1.05, 0.25, 0.02)], 0.01, M_ROPE, sides=4)
# the seaman's bag, slumped against the wall by the bed
bag = sphere("SeamansBag", 0.3, (R.x0 + 0.4, R.y1 - 0.45, 0.42), M_CANVAS, seg=14, scale=(0.75, 0.75, 1.45))
for v in bag.data.vertices:
    if v.co.z < -0.25: v.co.z = -0.25 - (v.co.z + 0.25) * 0.15
    v.co.x *= 1 + 0.1 * noise.noise(v.co * 6); v.co.y *= 1 + 0.1 * noise.noise(v.co * 6 + Vector((3, 0, 0)))
tube("BagNeck", [(R.x0 + 0.4, R.y1 - 0.45, 0.82), (R.x0 + 0.42, R.y1 - 0.47, 0.9)], [0.06, 0.08], M_CANVAS, sides=8)
tube("BagLanyard", [(R.x0 + 0.34, R.y1 - 0.45, 0.82), (R.x0 + 0.47, R.y1 - 0.4, 0.83), (R.x0 + 0.45, R.y1 - 0.52, 0.81)], 0.01, M_ROPE, sides=4)
# a chair with the heavy grego (a shaggy pea-coat) thrown over its back
CHX, CHY = 1.55, -0.65
CF = Frame((CHX, CHY), math.radians(200))
for sx in (-1, 1):
    for sy in (-1, 1):
        h = 0.44 if sy > 0 else 0.95
        CF.cyl(f"ChairLeg{sx}{sy}", 0.018, h, (sx * 0.2, sy * 0.19, h / 2), M_TIMBER, verts=8)
CF.box("ChairSeat", (0.44, 0.42, 0.035), (0, 0, 0.43), M_TIMBER, bevel=0.008)
CF.box("ChairBackRail", (0.42, 0.03, 0.08), (0, -0.19, 0.88), M_TIMBER, bevel=0.008)
CF.box("ChairBackRail2", (0.42, 0.025, 0.05), (0, -0.19, 0.68), M_TIMBER, bevel=0.006)
# the grego: draped over the back rail, hanging down behind and onto the seat
gv = []; gf = []
for j in range(9):
    for i in range(9):
        u = (i / 8 - 0.5) * 0.62
        t = j / 8
        if t < 0.5: y = -0.19 - 0.12 * (0.5 - t) * 2; z = 0.92 - (0.5 - t) * 2 * 0.75
        else: y = -0.19 + (t - 0.5) * 2 * 0.36; z = 0.92 - (t - 0.5) * 2 * 0.44
        z += 0.03 * noise.noise(Vector((u * 5, t * 5, 0))); y += 0.025 * noise.noise(Vector((u * 4, t * 4, 3)))
        if 0.45 < t < 0.55: z += 0.03
        gv.append(CF.p(u * (1 + 0.12 * abs(t - 0.5)), y, z))
for j in range(8):
    for i in range(8): gf.append((j * 9 + i, j * 9 + i + 1, (j + 1) * 9 + i + 1, (j + 1) * 9 + i))
gr = mesh_from("Grego", gv, gf, M_GREGO, smooth=True); gr.modifiers.new("Solid", 'SOLIDIFY').thickness = 0.025
for sx in (-1, 1):     # the sleeves hanging down the sides
    tube(f"GregoSleeve{sx}", [CF.p(sx * 0.3, -0.15, 0.88), CF.p(sx * 0.33, -0.08, 0.6), CF.p(sx * 0.31, 0.0, 0.36)], [0.07, 0.065, 0.06], M_GREGO, sides=8)
# the tall beaver hat on the floor by the chair, and the boots
HT = Vector((CHX - 0.15, CHY + 0.5, 0))
lathe("BeaverHat", [(0.0, 0.0), (0.18, 0.0), (0.19, 0.008), (0.1, 0.012), (0.095, 0.05), (0.1, 0.17), (0.105, 0.2), (0.0, 0.2)], tuple(HT), M_BEAVER, steps=20)
for k, (bx, by, yaw, fall) in enumerate(((1.05, -0.25, 0.4, 0.0), (1.2, -0.05, 0.9, 1.35))):
    BF2 = Frame((bx, by), yaw)
    if not fall:
        BF2.cyl(f"BootLeg{k}", 0.06, 0.32, (0, 0, 0.18), M_BOOT, verts=12)
        BF2.box(f"BootFoot{k}", (0.1, 0.27, 0.08), (0, 0.06, 0.0 + (0.08) / 2), M_BOOT, bevel=0.03)
    else:
        tube(f"BootLegFallen{k}", [BF2.p(0, -0.05, 0.065), BF2.p(0, 0.27, 0.07)], [0.06, 0.058], M_BOOT, sides=12)
        BF2.box(f"BootFootFallen{k}", (0.1, 0.08, 0.26), (0, -0.09, 0.0 + (0.26) / 2), M_BOOT, bevel=0.03)

# a rude shelf over the bed's foot side wall with a tinder-box and a pipe? (the brief: "a rude shelf") - on the south wall
RS = Frame((-1.1, R.y0), 0.0)
RS.box("RudeShelf", (0.9, 0.2, 0.03), (0, 0.1, 1.5), M_TIMBER, bevel=0.004)
for sx in (-1, 1): RS.box(f"RudeShelfPeg{sx}", (0.03, 0.17, 0.05), (sx * 0.36, 0.085, 1.45), M_TIMBER)
RS.box("TinderBox", (0.12, 0.08, 0.05), (-0.2, 0.1, 1.515), M_IRON, bevel=0.005)
lathe("ShelfJar", [(0.0, 0.0), (0.04, 0.0), (0.045, 0.08), (0.03, 0.11), (0.0, 0.11)], RS.p(0.2, 0.1, 1.515), M_CROCK, steps=12)
# pegs on the west wall
for k in range(3):
    cyl(f"WallPeg{k}", 0.012, 0.1, (R.x0 + 0.05, 1.0 + 0.3 * k, 1.7), M_TIMBER, verts=6, rot=(0, math.pi / 2, 0))

# ----------------------------------------------------------------------------- outside: the narrow street, the house opposite (clapboard, windows), a dawn sky
STREET = R.x1 + R.t + 3.2
M_CLAP = MK.timber_mat("M_Clapboard", base=(0.42, 0.40, 0.36), dark=(0.20, 0.19, 0.17), light=(0.54, 0.52, 0.47), along='Y', rough=(0.7, 0.9), grime=0.6, seams=('Z', 0.14))
box("HouseOpposite", (0.3, 14.0, 10.0), (STREET + 0.15, 0.0, -3.5 + (10.0) / 2), M_CLAP)
M_DARKPANE = plain("M_DarkPane", (0.02, 0.025, 0.03), rough=0.1)
for k, (yy_, zz_) in enumerate(((-2.0, 1.0), (1.6, 1.0), (-2.0, 3.8), (1.6, 3.8), (5.0, 1.0), (-5.4, 1.0))):
    box(f"OppWin{k}", (0.06, 0.95, 1.35), (STREET - 0.02, yy_, zz_), M_DARKPANE)
    for (dy, dz, sy, sz) in ((0, 0.72, 1.1, 0.1), (0, -0.72, 1.1, 0.12), (0.52, 0, 0.08, 1.35), (-0.52, 0, 0.08, 1.35), (0, 0, 0.04, 1.35), (0, 0.0, 0.95, 0.04)):
        box(f"OppWinFrame{k}{dy}{dz}{sy}", (0.08, sy, sz), (STREET - 0.05, yy_ + dy, zz_ + dz), M_SASH)
box("Street", (STREET - R.x1 + 1, 14, 0.1), ((R.x1 + STREET) / 2, 0, -3.6), noisy("M_Cobbles", [K.srgb((0.30, 0.29, 0.27)), K.srgb((0.22, 0.21, 0.2))], scale=12, rough=0.8))
box("RoofOpposite", (3.0, 14.0, 0.2), (STREET + 1.2, 0.0, 6.6), plain("M_Shingle", K.srgb((0.20, 0.19, 0.19)), rough=0.85), rot=(0, math.radians(-35), 0))
# ice on the panes' bottom corners? (render-only frost would be lost in the bake) - none

# ----------------------------------------------------------------------------- light: cold dawn
M_SKY = S.sky_mat("M_SkyDome", (1.0, -0.2, 0.05), zenith=(0.22, 0.28, 0.40), mid=(0.42, 0.46, 0.55), horizon=(0.80, 0.66, 0.62), cloud=0.6,
                  cloud_lit=(0.86, 0.72, 0.70), cloud_shade=(0.38, 0.40, 0.46), sun_glow=(0.9, 0.55, 0.4), haze_low=(0.5, 0.48, 0.5))
S.sky_dome(M_SKY, radius=200.0)
ld = bpy.data.lights.new("Lamp.windowSky", 'AREA'); ld.energy = 95.0; ld.color = (0.74, 0.80, 0.95); ld.shape = 'RECTANGLE'; ld.size = 0.8; ld.size_y = 1.15
wl = bpy.data.objects.new("Lamp.windowSky", ld); wl.location = (R.x1 + 0.05, WIN_Y, 1.4); K.link(wl)
wl.rotation_euler = Vector((-1.0, 0.0, -0.35)).to_track_quat('-Z', 'Y').to_euler()
light_obj("Lamp.bounceOpposite", 'AREA', 40.0, (0.80, 0.76, 0.78), (STREET - 0.3, WIN_Y, 2.0), direction=(-1, 0, -0.1), size=3.0)
world = bpy.data.worlds.new("Dawn"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.36, 0.40, 0.50, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors, sources
S.reader(READER, (0, 1))
anchor("scene.centre", (0.0, 0.3, 0.0))
anchor("room.window", tuple(R.at('E', WIN_Y - R.y0, 1.4)))
anchor("room.door", tuple(R.at('S', 1.25 - R.x0)))
S.fx("fx.candle.seaChest", SC.p(0.32, 0.18, CT + 0.105), 0.01)
sound("wind", "window", (R.x1 + 0.3, WIN_Y, 1.6))
page = S.page_preview()
K.apply_transforms()

E = READER + Vector((0, 0, S.EYE))
cams = S.eye_cams([("Reader", 0), ("Left", -80), ("Right", 80), ("Behind", 180)], dz=-0.75, dist=4.0, extra=[
    ("Page", E, E + Vector((0, 4, -0.75)), 17),
    ("Bed", Vector((1.3, -0.9, 1.7)), Vector((-0.4, 1.2, 0.5)), 22),
    ("Fireboard", Vector((0.6, -0.6, 1.2)), Vector(FP.p(0, 0.1, 0.65)), 26),
])
probs = S.check_reader(ignore=("PagePreview",))
K.print_budget(exclude=("PagePreview",))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.0, captures_dir=ARGS.captures)

if ARGS.export or ARGS.bake:
    S.export(SID, cams, page=page,
             remove=[o.name for o in bpy.data.objects if o.name.startswith("WindowGlass_")],
             keep_names={},
             size_for={"M_OldPlaster": (2048, 64, 1024), "M_PineBoards": (1024, 128, 1024), "M_OldTimber": (1024, 128, 512), "M_BedWood": (1024, 128, 512),
                       "M_Patchwork": (2048, 64, 512), "M_Sheets": (512, 32, 256), "M_SeaChest": (512, 64, 256), "M_Canvas": (512, 64, 256),
                       "M_Grego": (512, 64, 256), "M_Clapboard": (512, 32, 256), "M_SkyDome": (1024,), "M_SashPaint": (512, 32, 256)},
             default_size=(256, 32, 128))
print("DONE")
