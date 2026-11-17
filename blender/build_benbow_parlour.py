"""
Fable: the parlour of the Admiral Benbow inn, Black Hill Cove (Treasure Island, chapters 1-3). A chapter step-in room:
built ahead of time, served from the server, downloaded by the headset.

"... he sat in a corner of the parlour next the fire, and drank rum and water very strong." "... he would slap his
hand on the table for a silence all round" (chapter 1). "... the captain had risen earlier than usual ... his breakfast
table was laid" ... "laying it bare before him on the table" (the cutlass) ... "Draw down the blind, Jim" ... "the very
ticking of the clock" (chapters 2-3).

The moment: a bitter January morning, grey daylight and frost outside, the parlour empty. One low public room,
whitewashed, under smoke-dark oak beams, with a stone-flagged floor. In the far corner the coal fire burns in its iron
grate; next to it, the captain's corner: a high-backed oak settle and his table, laid for breakfast with a napkin, a
rum glass and the pewter, a clay pipe, his brass telescope, and the cutlass lying bare; his stick "like a handspike"
leans against the settle. A longcase clock ticks against the far wall; the window beside it has its blind half drawn.
On the right the inn door stands open on the frosty road and the big signboard on its post; on the left the foot of
"our old stairs"; behind the reader the curtained door from the passage; to one side the doorway into the bar. Plain
country tables, benches and chairs about the room, a couple of candles still burning from the night. No people.

Living scene (docs/LIVING_SCENES.md): fx.fire.grate (radius extra), fx.candle.table1/2, cloth.curtain.door (the
curtained door) and cloth.curtain.blind, sound.fire.grate, sound.clock.longcase, sound.wind.door.

Node names: anchor.reader.entrance (feet, floor z = 0), anchor.reader.look (eye height, facing the fire corner),
anchor.scene.centre, anchor.parlour.fire, anchor.parlour.captainTable, anchor.parlour.clock, anchor.parlour.innDoor,
anchor.parlour.barDoor, anchor.parlour.stairs, anchor.parlour.sign; light.daylight (SUN, grey and soft),
light.window / light.door (AREA, skylight at the openings), light.fire (POINT, warm), light.candle1/2 (POINT, small).
SkyDome (unlit fog backdrop).

Axes: metres, +Z up. Room x -3..3, y -2.5..2.5; the fire in the north (+y) wall, the inn door in the east (+x) wall,
the bar door in the south wall, the stairs against the west wall; the reader near the curtained door (south-west).

Run headless (one Blender at a time):
  blender -b -P blender/build_benbow_parlour.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_benbow_parlour.py -- --render --samples 48 --res 1400 --captures captures/blender/benbow-parlour
  blender -b -P blender/build_benbow_parlour.py -- --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import treasure_kit as K
from treasure_kit import F, smooth, lerp, fbm, new_mat, plain, noisy, box, cyl, mesh_obj, from_pydata, lathe, Builder, \
    anchor, living_empty, light_obj, camera
import scene_kit_b2 as B

CAPTURES = sys.argv[sys.argv.index("--captures") + 1] if "--captures" in sys.argv else ""
USE_CPU = "--cpu" in sys.argv
if CAPTURES: i = sys.argv.index("--captures"); del sys.argv[i:i + 2]
if USE_CPU: sys.argv.remove("--cpu")
SAMPLES_GIVEN = "--samples" in sys.argv
args = K.parse_args("out/benbow-parlour")
if not SAMPLES_GIVEN: args.samples = 48
OUT = args.out
scene, COLL = K.reset_scene("BenbowParlour", args, bounces=8, diffuse=5, clamp=8.0)
if USE_CPU: scene.cycles.device = 'CPU'
random.seed(1755)
rb = random.Random(4)

# ----------------------------------------------------------------------------- dimensions
X0, X1, Y0, Y1 = -3.0, 3.0, -2.5, 2.5
H = 2.45                                   # ceiling boards; beams hang below
WT = 0.55
EYE = 1.55
READER = Vector((-1.55, -1.45, 0.0))
LOOK_AT = Vector((1.3, 2.2, 0.0))
FIRE_X = 1.35                               # fireplace centre on the north wall
WIN_N_X, WIN_W, WIN_SILL, WIN_HEAD = -1.45, 0.95, 0.9, 1.85
IDOOR_Y, IDOOR_W, IDOOR_H = -0.55, 1.0, 1.95  # the inn door to the road, east wall
BDOOR_X, BDOOR_W = 1.35, 0.9                # the bar doorway, south wall
CDOOR_Y = -1.75                             # the curtained door from the passage, west wall (behind-left of the reader)
CLOCK_X = 0.05
SUN_DIR = Vector((0.6, 0.55, 0.30)).normalized()    # the low January sun, veiled: from the east-north-east

# ----------------------------------------------------------------------------- materials
def whitewash_mat(name):
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    n1, _ = g.noise(P, 1.5, 5)
    n2, _ = g.noise(P, 16.0, 3)
    col = g.ramp(n1 * 0.6 + n2 * 0.4, [(0.3, (0.55, 0.53, 0.48)), (0.7, (0.64, 0.62, 0.57))])
    smoke = g.ss(z, 1.6, 2.45)
    col = g.mul(col, g.mix(smoke * 0.6, (1, 1, 1), (0.70, 0.64, 0.54)))
    scuff = (1.0 - g.ss(z, 0.12, 0.5)) * g.ss(n2, 0.4, 0.7)
    col = g.mix(scuff * 0.55, col, (0.28, 0.25, 0.20))
    damp = (1.0 - g.ss(z, 0.0, 0.35)) * g.ss(n1, 0.45, 0.6)
    col = g.mix(damp * 0.4, col, (0.36, 0.36, 0.30))
    col = g.mul(col, g.ao(0.3), 0.6)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.93
    g.bump(b, n2 * 0.6 + n1 * 0.4, 0.45, 0.006)
    return m

def flags_mat(name):
    """worn sandstone/slate flags in random courses, dark joints, a hearth-side scorch and a path worn by the door."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    br = g.n("ShaderNodeTexBrick", offset=0.37)
    g.set(br.inputs["Vector"], g.comb(x, y, 0.0))
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 0.71; br.inputs["Row Height"].default_value = 0.53
    br.inputs["Mortar Size"].default_value = 0.012; br.inputs["Mortar Smooth"].default_value = 0.4; br.inputs["Bias"].default_value = 0.0
    br.inputs["Color1"].default_value = (0.7, 0.72, 0.75, 1); br.inputs["Color2"].default_value = (1.15, 1.08, 0.98, 1)
    br.inputs["Mortar"].default_value = (0.35, 0.33, 0.30, 1)
    n1, _ = g.noise(P, 1.6, 5)
    n2, _ = g.noise(P, 22.0, 3)
    col = g.mul(g.ramp(n1 * 0.6 + n2 * 0.4, [(0.25, (0.08, 0.075, 0.07)), (0.6, (0.13, 0.12, 0.105)), (0.9, (0.18, 0.165, 0.14))]), br.outputs["Color"])
    wear = g.ss(n1, 0.5, 0.75) * 0.3
    col = g.mix(wear, col, (0.20, 0.18, 0.15))
    col = g.mul(col, g.ao(0.2), 0.6)
    g.set(b.inputs["Base Color"], col)
    g.set(b.inputs["Roughness"], 0.7 + n2 * 0.25)
    g.bump(b, F(g, br.outputs["Fac"]) * -1.0 + n2 * 0.25 + n1 * 0.2, 0.6, 0.01)
    return m

def oak_mat(name, base=(0.09, 0.06, 0.035), dark=(0.03, 0.02, 0.012), light=(0.14, 0.10, 0.06), axis='X', rough=0.7, adze=True):
    m, nt, b, g = new_mat(name)
    P = g.pos()
    st = {'X': (0.15, 3.0, 3.0), 'Y': (3.0, 0.15, 3.0), 'Z': (3.0, 3.0, 0.15)}[axis]
    Q = g.stretch(P, *st)
    n1, _ = g.noise(Q, 3.0, 6, 0.65, 2.5)
    n2, _ = g.noise(Q, 30.0, 3)
    col = g.ramp(n1 * 0.7 + n2 * 0.3, [(0.2, dark), (0.5, base), (0.85, light)])
    col = g.mul(col, g.ao(0.12), 0.6)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = rough
    hgt = n2 * 0.4 + n1 * 0.4
    if adze:
        ad = g.vor(g.stretch(P, *(s * 0.5 for s in st)), 4.0, feature='F1')
        hgt = hgt + ad * 0.6
    g.bump(b, hgt, 0.5, 0.004)
    return m

def cloth_mat(name, a, b_, sheen=0.4):
    m, nt, b, g = new_mat(name)
    P = g.pos()
    n1, _ = g.noise(P, 4.0, 4); n2, _ = g.noise(P, 120.0, 2)
    col = g.ramp(n1 * 0.7 + n2 * 0.3, [(0.3, a), (0.7, b_)])
    col = g.mul(col, g.ao(0.1), 0.6)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.9; b.inputs["Sheen Weight"].default_value = sheen
    g.bump(b, n2, 0.2, 0.001)
    return m

def frost_mat(name):
    """the frosty road: rutted grey-brown earth, white hoar in the hollows and on the verges."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    n1, _ = g.noise(P, 0.8, 5); n2, _ = g.noise(P, 9.0, 4)
    col = g.ramp(n1 * 0.6 + n2 * 0.4, [(0.3, (0.16, 0.14, 0.12)), (0.7, (0.26, 0.24, 0.21))])
    frost = g.ss(n2 * 0.5 + n1 * 0.5, 0.42, 0.62)
    col = g.mix(frost * 0.85, col, (0.62, 0.64, 0.66))
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.8
    g.bump(b, n2, 0.4, 0.02)
    return m

def fog_sky_mat(name="M_SkyDome"):
    """frost fog in the cove: a pale, luminous grey, brighter low towards the veiled sun, the far hillside and the
    road's hedges dissolving into it."""
    m, nt, b, g = new_mat(name)
    nv = g.n("ShaderNodeVectorMath", operation='NORMALIZE'); g.set(nv.inputs[0], g.pos())
    d = nv.outputs[0]; dx, dy, el = g.sep(d)
    col = g.ramp(g.ss(el, -0.05, 0.7), [(0.0, (0.42, 0.43, 0.43)), (0.12, (0.66, 0.68, 0.70)), (1.0, (0.54, 0.57, 0.62))])
    sd = g.n("ShaderNodeVectorMath", operation='DOT_PRODUCT'); g.set(sd.inputs[0], d); sd.inputs[1].default_value = tuple(SUN_DIR)
    col = g.mix(g.ss(F(g, sd.outputs["Value"]), 0.6, 1.0).pow(2.0) * 0.5, col, (0.95, 0.88, 0.76))
    hn, _ = g.noise(g.comb(dx * 3.0, dy * 3.0, 0.0), 1.0, 4)
    hill = g.ss(hn, 0.3, 0.7) * 0.06 + 0.01
    land = 1.0 - g.ss(el - hill, 0.0, 0.01)
    col = g.mix(land * 0.35, col, (0.30, 0.32, 0.30))
    g.set(b.inputs["Emission Color"], col); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0
    return m

M_WALL = whitewash_mat("M_Whitewash")
M_FLOOR = flags_mat("M_Flags")
M_BEAM = oak_mat("M_Beams")
M_CEILB = oak_mat("M_CeilingBoards", base=(0.10, 0.075, 0.05), light=(0.15, 0.11, 0.075), adze=False)
M_TABLE = oak_mat("M_Tables", base=(0.20, 0.14, 0.085), dark=(0.09, 0.06, 0.035), light=(0.28, 0.21, 0.13), rough=0.7)
M_SETTLE = oak_mat("M_Settle", base=(0.10, 0.065, 0.035), light=(0.17, 0.11, 0.06), axis='Z', rough=0.45)
M_IRON = noisy("M_Iron", [(0.02, 0.02, 0.02), (0.05, 0.045, 0.04), (0.10, 0.06, 0.035)], scale=20, rough=0.6, metallic=0.6, bump=0.3)
M_PEWTER = noisy("M_Pewter", [(0.30, 0.30, 0.29), (0.42, 0.42, 0.40), (0.50, 0.50, 0.48)], scale=8, rough=0.35, metallic=0.7, bump=0.1)
M_BRASS = noisy("M_Brass", [(0.40, 0.27, 0.08), (0.55, 0.40, 0.14), (0.66, 0.50, 0.22)], scale=10, rough=0.25, metallic=0.8, bump=0.05)
M_STEEL = noisy("M_Steel", [(0.35, 0.36, 0.37), (0.48, 0.49, 0.50)], scale=30, rough=0.3, metallic=0.8, bump=0.05, stretch=(1, 1, 8))
M_GLASS = plain("M_Glass", (0.6, 0.65, 0.65), rough=0.05, alpha=0.12)
M_RUMGLASS = plain("M_RumGlass", (0.35, 0.22, 0.10), rough=0.05, transmission=0.6)
M_LINEN = cloth_mat("M_Linen", (0.62, 0.60, 0.55), (0.72, 0.70, 0.64), sheen=0.2)
M_CURTAIN = cloth_mat("M_DoorCurtain", (0.10, 0.12, 0.08), (0.16, 0.18, 0.12))
M_BLIND = cloth_mat("M_Blind", (0.50, 0.46, 0.36), (0.58, 0.54, 0.44), sheen=0.1)
M_STONE = noisy("M_HearthStone", [(0.20, 0.19, 0.17), (0.28, 0.27, 0.24), (0.34, 0.32, 0.29)], scale=3, rough=0.85, bump=0.5, bump_dist=0.01)
M_SOOT = noisy("M_Soot", [(0.012, 0.011, 0.01), (0.03, 0.027, 0.024)], scale=6, rough=0.95)
M_COAL = noisy("M_Coal", [(0.01, 0.01, 0.01), (0.035, 0.033, 0.03)], scale=30, rough=0.4, bump=0.8, bump_dist=0.01)
M_EMBERS = plain("M_Embers", (0.05, 0.02, 0.01), rough=0.9, emission=(1.0, 0.32, 0.06), strength=6.0)
M_FLAME = plain("M_Flame", (0.0, 0.0, 0.0), rough=1.0, emission=(1.0, 0.55, 0.2), strength=10.0)
M_WAX = plain("M_Tallow", (0.72, 0.66, 0.50), rough=0.5)
M_CLAY = noisy("M_ClayPipe", [(0.55, 0.52, 0.46), (0.62, 0.60, 0.54)], scale=20, rough=0.6, bump=0.05)
M_STONEWARE = noisy("M_Stoneware", [(0.32, 0.26, 0.17), (0.42, 0.35, 0.24)], scale=8, rough=0.3, coat=0.5, bump=0.05)
M_CLOCKFACE = noisy("M_ClockFace", [(0.62, 0.58, 0.48), (0.70, 0.66, 0.55)], scale=10, rough=0.4, bump=0.0)
M_ROAD = frost_mat("M_FrostRoad")
M_SIGN = noisy("M_SignPaint", [(0.05, 0.08, 0.12), (0.08, 0.12, 0.18)], scale=4, rough=0.5, bump=0.1)
M_SIGNFIG = noisy("M_SignFigure", [(0.55, 0.42, 0.18), (0.62, 0.20, 0.12), (0.70, 0.62, 0.45)], scale=6, rough=0.5, bump=0.0)
M_HEDGE = noisy("M_FrostHedge", [(0.12, 0.13, 0.10), (0.30, 0.32, 0.30), (0.50, 0.52, 0.52)], scale=2.5, rough=0.95, bump=0.8, bump_dist=0.05)
M_SKY = fog_sky_mat()
M_BAR = oak_mat("M_BarWood", base=(0.10, 0.065, 0.035), light=(0.17, 0.11, 0.06), axis='Z', rough=0.5)

# ----------------------------------------------------------------------------- the room shell
box("Floor", (X1 - X0 + 2 * WT, Y1 - Y0 + 2 * WT, 0.1), (0, 0, -0.05), M_FLOOR)
box("Ceiling", (X1 - X0, Y1 - Y0, 0.06), (0, 0, H + 0.03), M_CEILB)
def wall_y(name, y, x0, x1, openings, mat, sy):
    xs = [x0]
    for (xc, w, z0, z1) in sorted(openings): xs += [xc - w / 2, xc + w / 2]
    xs.append(x1); yc = y + sy * WT / 2
    for i in range(0, len(xs), 2):
        if xs[i + 1] - xs[i] > 0.001: box(f"{name}_pier{i}", (xs[i + 1] - xs[i], WT, H), ((xs[i] + xs[i + 1]) / 2, yc, H / 2), mat)
    for (xc, w, z0, z1) in openings:
        if z0 > 0.001: box(f"{name}_below{xc}", (w, WT, z0), (xc, yc, z0 / 2), mat)
        box(f"{name}_above{xc}", (w, WT, H - z1), (xc, yc, (H + z1) / 2), mat)
def wall_x(name, x, y0, y1, openings, mat, sx):
    ys_ = [y0]
    for (yc, w, z0, z1) in sorted(openings): ys_ += [yc - w / 2, yc + w / 2]
    ys_.append(y1); xc = x + sx * WT / 2
    for i in range(0, len(ys_), 2):
        if ys_[i + 1] - ys_[i] > 0.001: box(f"{name}_pier{i}", (WT, ys_[i + 1] - ys_[i], H), (xc, (ys_[i] + ys_[i + 1]) / 2, H / 2), mat)
    for (yc, w, z0, z1) in openings:
        if z0 > 0.001: box(f"{name}_below{yc}", (WT, w, z0), (xc, yc, z0 / 2), mat)
        box(f"{name}_above{yc}", (WT, w, H - z1), (xc, yc, (H + z1) / 2), mat)
wall_y("WallN", Y1, X0 - WT, X1 + WT, [(WIN_N_X, WIN_W, WIN_SILL, WIN_HEAD)], M_WALL, 1)
wall_y("WallS", Y0, X0 - WT, X1 + WT, [(BDOOR_X, BDOOR_W, 0.0, IDOOR_H)], M_WALL, -1)
wall_x("WallW", X0, Y0, Y1, [(CDOOR_Y, 0.85, 0.0, IDOOR_H)], M_WALL, -1)
wall_x("WallE", X1, Y0, Y1, [(IDOOR_Y, IDOOR_W, 0.0, IDOOR_H), (1.35, 0.7, 1.0, 1.7)], M_WALL, 1)
# beams: a great summer beam east-west and joists across, a post by the stairs
box("SummerBeam", (X1 - X0, 0.32, 0.30), (0, 0.15, H - 0.15), M_BEAM, bevel=0.02)
for k in range(9):
    x = X0 + 0.35 + k * (X1 - X0 - 0.7) / 8
    box(f"Joist{k}", (0.13, Y1 - Y0, 0.13), (x, 0, H - 0.065), M_BEAM, bevel=0.01)
box("StairPost", (0.2, 0.2, H), (X0 + 1.05, 0.55, H / 2), M_BEAM, bevel=0.02)

# ----------------------------------------------------------------------------- doors
def door_frame(name, c, w, h, axis):
    if axis == 'y':
        for s in (-1, 1): box(f"{name}_Jamb{s}", (0.11, WT + 0.04, h), (c.x + s * (w / 2 + 0.055), c.y, h / 2), M_BEAM)
        box(f"{name}_Head", (w + 0.32, WT + 0.04, 0.15), (c.x, c.y, h + 0.075), M_BEAM)
    else:
        for s in (-1, 1): box(f"{name}_Jamb{s}", (WT + 0.04, 0.11, h), (c.x, c.y + s * (w / 2 + 0.055), h / 2), M_BEAM)
        box(f"{name}_Head", (WT + 0.04, w + 0.32, 0.15), (c.x, c.y, h + 0.075), M_BEAM)
def ledged_leaf(name, hinge, d, w, h, mat):
    ang = math.atan2(d.y, d.x); n = Vector((-d.y, d.x, 0))
    for i in range(5):
        u = (i + 0.5) * w / 5
        box(f"{name}_Board{i}", (w / 5 - 0.004, 0.035, h - 0.03), tuple(hinge + d * u + Vector((0, 0, h / 2))), mat, rot=(0, 0, ang))
    for k, z in enumerate((0.25, h * 0.5, h - 0.25)):
        box(f"{name}_Ledge{k}", (w - 0.08, 0.03, 0.13), tuple(hinge + d * w / 2 + Vector((0, 0, z)) - n * 0.03), mat, rot=(0, 0, ang))
    box(f"{name}_Latch", (0.15, 0.015, 0.025), tuple(hinge + d * (w - 0.12) + Vector((0, 0, 1.05)) - n * 0.05), M_IRON, rot=(0, 0, ang))
# the inn door: open inwards against the east wall
door_frame("InnDoor", Vector((X1 + WT / 2, IDOOR_Y, 0)), IDOOR_W, IDOOR_H, 'x')
ledged_leaf("InnDoorLeaf", Vector((X1 - 0.04, IDOOR_Y + IDOOR_W / 2 - 0.02, 0.0)), Vector((-0.1, 1.0, 0)).normalized(), IDOOR_W - 0.04, IDOOR_H - 0.02, M_BAR)
# the bar doorway (no leaf; a step down into the bar, which is lit by its own window)
door_frame("BarDoor", Vector((BDOOR_X, Y0 - WT / 2, 0)), BDOOR_W, IDOOR_H, 'y')
# the curtained door (west wall, behind the reader's left): door leaf ajar and a heavy curtain on a rod
door_frame("ParlourDoor", Vector((X0 - WT / 2, CDOOR_Y, 0)), 0.85, IDOOR_H, 'x')
cyl("CurtainRod", 0.013, 1.25, (X0 + 0.06, CDOOR_Y, IDOOR_H + 0.12), M_IRON, verts=8, rot=(math.pi / 2, 0, 0))
def drape(name, mat, origin, U, Nin, u0, u1, z0, z1, folds, depth, gather_bottom=1.0, out=0.0, rows=8):
    C = Builder(name, mat, living=True); n = folds * 4; vs, ws, fs = [], [], []
    for j in range(rows + 1):
        tz = j / rows; zz = z1 - (z1 - z0) * tz; g_ = lerp(1.0, gather_bottom, tz)
        for i in range(n + 1):
            t = i / n; uu = lerp(u0, u1, 0.5) + (lerp(u0, u1, t) - lerp(u0, u1, 0.5)) * g_
            wv = depth * math.sin(t * folds * 2 * math.pi) * (0.6 + 0.4 * tz)
            vs.append(origin + U * uu + Nin * (wv + out * tz) + Vector((0, 0, zz))); ws.append((tz ** 1.2, 0.0, 0.0, 1.0))
    for j in range(rows):
        for i in range(n):
            a = j * (n + 1) + i; fs.append([a, a + 1, a + n + 2, a + n + 1])
    C.add(vs, fs, (1, 1, 1, 1), ws)
    return C.finish(smooth_=True)
drape("cloth.curtain.door", M_CURTAIN, Vector((X0 + 0.08, CDOOR_Y, 0)), Vector((0, 1, 0)), Vector((1, 0, 0)), -0.62, 0.30, 0.02, IDOOR_H + 0.1, 6, 0.045, gather_bottom=0.8)

# ----------------------------------------------------------------------------- windows: the north window with its blind, a small east window
def window(name, c, U, Nin, w, sill, head, bars=(3, 3)):
    zc = (sill + head) / 2
    sz = lambda a, t, h: (abs(U.x) * a + abs(Nin.x) * t, abs(U.y) * a + abs(Nin.y) * t, h)
    box(f"{name}_Glass", sz(w, 0.006, head - sill), tuple(c + Vector((0, 0, zc))), M_GLASS)
    for k in range(bars[0] + 1):
        t = -w / 2 + k * w / bars[0]
        box(f"{name}_V{k}", sz(0.035, 0.04, head - sill), tuple(c + U * t + Nin * 0.01 + Vector((0, 0, zc))), M_BEAM)
    for k in range(bars[1] + 1):
        box(f"{name}_H{k}", sz(w, 0.04, 0.03), tuple(c + Nin * 0.01 + Vector((0, 0, sill + k * (head - sill) / bars[1]))), M_BEAM)
    box(f"{name}_Sill", sz(w + 0.16, 0.22, 0.05), tuple(c + Nin * (WT / 2) + Vector((0, 0, sill - 0.025))), M_BEAM)
WNc = Vector((WIN_N_X, Y1 + WT / 2, 0))
window("WinN", WNc, Vector((1, 0, 0)), Vector((0, -1, 0)), WIN_W, WIN_SILL, WIN_HEAD)
window("WinE", Vector((X1 + WT / 2, 1.35, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0)), 0.7, 1.0, 1.7, bars=(2, 3))
# the blind ("Draw down the blind, Jim"): a linen roller blind half drawn, on its wooden roller in the reveal
cyl("BlindRoller", 0.03, WIN_W + 0.1, (WIN_N_X, Y1 + 0.06, WIN_HEAD + 0.02), M_BEAM, verts=10, rot=(0, math.pi / 2, 0))
Bv = []; Bw = []; Bf = []
rows = 6; cols = 6
for j in range(rows + 1):
    t = j / rows; z = WIN_HEAD - 0.02 - t * 0.52
    for i in range(cols + 1):
        u = -WIN_W / 2 + 0.02 + i * (WIN_W - 0.04) / cols
        Bv.append(Vector((WIN_N_X + u, Y1 + 0.03 - 0.008 * math.sin(u * 9) * t, z))); Bw.append((t, 0, 0, 1))
for j in range(rows):
    for i in range(cols):
        a = j * (cols + 1) + i; Bf.append([a, a + 1, a + cols + 2, a + cols + 1])
CB = Builder("cloth.curtain.blind", M_BLIND, living=True); CB.add(Bv, Bf, (1, 1, 1, 1), Bw); CB.finish(smooth_=True)
box("BlindPull", (0.006, 0.006, 0.16), (WIN_N_X, Y1 + 0.03, WIN_HEAD - 0.62), M_ROPE if False else M_LINEN)

# ----------------------------------------------------------------------------- the fireplace: stone surround, iron basket grate with coal
FX_ = Vector((FIRE_X, Y1, 0))
for s_ in (-1, 1): box(f"Chimney_Pier{s_}", (0.3, 0.42, H), (FIRE_X + s_ * 0.71, Y1 - 0.21, H / 2), M_WALL)
box("Chimney_Top", (1.12, 0.42, H - 1.0), (FIRE_X, Y1 - 0.21, (H + 1.0) / 2), M_WALL)
box("Hearth_Ceiling", (1.0, 0.4, 0.04), (FIRE_X, Y1 - 0.2, 0.99), M_SOOT)
box("Hearth_Back", (1.1, 0.05, 1.0), (FIRE_X, Y1 - 0.04, 0.5), M_SOOT)
for s in (-1, 1): box(f"Hearth_Cheek{s}", (0.06, 0.38, 0.98), (FIRE_X + s * 0.53, Y1 - 0.22, 0.49), M_SOOT)
for s in (-1, 1): box(f"Hearth_Jamb{s}", (0.2, 0.08, 1.0), (FIRE_X + s * 0.66, Y1 - 0.45, 0.5), M_STONE, bevel=0.012)
box("Hearth_Lintel", (1.52, 0.10, 0.2), (FIRE_X, Y1 - 0.46, 1.1), M_STONE, bevel=0.012)
box("Mantel_Shelf", (1.75, 0.24, 0.06), (FIRE_X, Y1 - 0.5, 1.27), M_BEAM, bevel=0.01)
box("Hearth_Stone", (1.6, 0.55, 0.05), (FIRE_X, Y1 - 0.68, 0.025), M_STONE, bevel=0.01)
# the grate: an iron basket on legs, front bars, full of coal glowing at its heart
G0 = Vector((FIRE_X, Y1 - 0.22, 0.22))
box("Grate_Floor", (0.62, 0.26, 0.02), tuple(G0), M_IRON)
for k in range(7): cyl(f"Grate_Bar{k}", 0.009, 0.62, (FIRE_X, Y1 - 0.45, 0.25 + k * 0.035), M_IRON, verts=6, rot=(0, math.pi / 2, 0))
for s in (-1, 1):
    box(f"Grate_Leg{s}", (0.03, 0.03, 0.24), (FIRE_X + s * 0.29, Y1 - 0.44, 0.12), M_IRON)
    lathe(f"Grate_Finial{s}", [(0, 0), (0.025, 0), (0.03, 0.04), (0.012, 0.08), (0, 0.1)], (FIRE_X + s * 0.33, Y1 - 0.45, 0.46), M_BRASS, steps=8)
COAL = Builder("Coals", M_COAL)
EMB = Builder("EmberCoals", M_EMBERS)
rc = random.Random(11)
for k in range(46):
    x = FIRE_X + rc.uniform(-0.27, 0.27); y = Y1 - 0.3 + rc.uniform(-0.12, 0.12); z = 0.25 + rc.uniform(0, 0.16) * (1 - abs(x - FIRE_X) / 0.4)
    r_ = rc.uniform(0.025, 0.05)
    hot = (abs(x - FIRE_X) < 0.18 and z < 0.36 and rc.random() < 0.6)
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r_)
    for v in bm.verts: v.co = Vector((v.co.x * rc.uniform(0.7, 1.3), v.co.y * rc.uniform(0.7, 1.3), v.co.z * rc.uniform(0.6, 1.0))) + Vector((x, y, z))
    (EMB if hot else COAL).add([v.co.copy() for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces]); bm.free()
COAL.finish(smooth_=False); EMB.finish(smooth_=False)
FL = Builder("Flames", M_FLAME)
for k in range(6):
    cx_, cy_ = FIRE_X + rc.uniform(-0.16, 0.16), Y1 - 0.3 + rc.uniform(-0.05, 0.05); hh = rc.uniform(0.10, 0.2); ww = rc.uniform(0.04, 0.07)
    for a in (0.0, math.pi / 2):
        d = Vector((math.cos(a), math.sin(a), 0)) * ww; z0 = 0.36
        FL.add([Vector((cx_, cy_, z0)) - d, Vector((cx_, cy_, z0)) + d, Vector((cx_, cy_, z0 + hh * 0.45)) + d * 0.8, Vector((cx_, cy_, z0 + hh)), Vector((cx_, cy_, z0 + hh * 0.45)) - d * 0.8], [[0, 1, 2, 3, 4]])
FL.finish(smooth_=False)
# fire irons, a coal scuttle, pewter plates and brass candlesticks on the mantel
for k, dx in enumerate((-0.05, 0.0, 0.05)):
    cyl(f"FireIron{k}", 0.008, 0.72, (FIRE_X + 0.82 + dx, Y1 - 0.55, 0.38), M_IRON, verts=6, rot=(0.12, -0.06 + dx, 0))
lathe("CoalScuttle", [(0, 0), (0.14, 0), (0.17, 0.12), (0.16, 0.26), (0.12, 0.32), (0, 0.32)], (FIRE_X - 0.92, Y1 - 0.62, 0.0), M_IRON, steps=12)
for k in range(3): lathe(f"MantelPlate{k}", [(0, 0), (0.11, 0), (0.12, 0.018), (0, 0.018)], (FIRE_X - 0.5 + k * 0.5, Y1 - 0.45, 1.42), M_PEWTER, steps=14, rot=(1.35, 0, 0))
for k, dx in enumerate((-0.75, 0.75)):
    lathe(f"MantelStick{k}", [(0, 0), (0.05, 0), (0.05, 0.015), (0.015, 0.04), (0.012, 0.16), (0.03, 0.18), (0, 0.185)], (FIRE_X + dx, Y1 - 0.5, 1.30), M_BRASS, steps=10)
    cyl(f"MantelCandle{k}", 0.011, 0.14, (FIRE_X + dx, Y1 - 0.5, 1.55), M_WAX, verts=8)

# ----------------------------------------------------------------------------- the captain's corner: settle, table, his things
SET_Y = 0.55
# a high-backed oak settle along the fire's east side, its back to the inn door's draught
SX = FIRE_X + 1.1
box("Settle_Seat", (0.45, 1.35, 0.05), (SX + 0.08, SET_Y + 0.25, 0.45), M_SETTLE, bevel=0.005)
box("Settle_Back", (0.05, 1.35, 1.45), (SX + 0.32, SET_Y + 0.25, 0.9), M_SETTLE, bevel=0.005)
for s in (-1, 1): box(f"Settle_End{s}", (0.5, 0.05, 1.12), (SX + 0.1, SET_Y + 0.25 + s * 0.68, 0.56), M_SETTLE, bevel=0.005)
box("Settle_Front", (0.04, 1.35, 0.38), (SX - 0.13, SET_Y + 0.25, 0.22), M_SETTLE)
for k in range(5): box(f"Settle_Panel{k}", (0.02, 0.22, 0.5), (SX + 0.29, SET_Y - 0.25 + k * 0.25, 1.1), M_SETTLE, bevel=0.005)
# the captain's table, laid for breakfast
CT = Vector((FIRE_X + 0.42, SET_Y + 0.25, 0))
box("CTable_Top", (0.85, 1.05, 0.045), (CT.x, CT.y, 0.73), M_TABLE, bevel=0.006)
for (lx, ly) in ((-0.36, -0.46), (0.36, -0.46), (-0.36, 0.46), (0.36, 0.46)):
    lathe(f"CTable_Leg{lx}{ly}", [(0.03, 0), (0.03, 0.12), (0.04, 0.16), (0.03, 0.22), (0.032, 0.6), (0.032, 0.71), (0, 0.71)], (CT.x + lx, CT.y + ly, 0.0), M_TABLE, steps=8)
box("CTable_Rail", (0.7, 0.9, 0.08), (CT.x, CT.y, 0.66), M_TABLE)
# napkin, plate with the end of the breakfast, rum glass, pewter jug, the clay pipe, telescope, the bare cutlass
box("Napkin", (0.36, 0.36, 0.004), (CT.x - 0.08, CT.y - 0.18, 0.755), M_LINEN, rot=(0, 0, 0.25))
lathe("CPlate", [(0, 0), (0.1, 0), (0.12, 0.015), (0, 0.015)], (CT.x - 0.08, CT.y - 0.18, 0.757), M_PEWTER, steps=16)
lathe("RumGlass", [(0, 0), (0.035, 0), (0.035, 0.008), (0.012, 0.02), (0.01, 0.05), (0.04, 0.07), (0.042, 0.12), (0, 0.12)], (CT.x + 0.2, CT.y - 0.3, 0.755), M_RUMGLASS, steps=12)
lathe("RumJug", [(0, 0), (0.06, 0), (0.08, 0.07), (0.075, 0.15), (0.045, 0.2), (0.05, 0.22), (0, 0.22)], (CT.x + 0.25, CT.y + 0.05, 0.755), M_STONEWARE, steps=12)
lathe("Tankard", [(0, 0), (0.045, 0), (0.048, 0.02), (0.042, 0.11), (0.048, 0.13), (0, 0.13)], (CT.x - 0.25, CT.y + 0.2, 0.755), M_PEWTER, steps=12)
cyl("ClayPipeStem", 0.004, 0.32, (CT.x + 0.05, CT.y + 0.32, 0.762), M_CLAY, verts=5, rot=(0, math.pi / 2, 0.5))
lathe("ClayPipeBowl", [(0, 0), (0.012, 0), (0.016, 0.03), (0.012, 0.04), (0, 0.04)], (CT.x - 0.09, CT.y + 0.24, 0.758), M_CLAY, steps=8)
# the brass telescope, closed, lying across the far side of the table
for k, (r, L, off) in enumerate(((0.032, 0.30, 0.0), (0.027, 0.22, 0.24), (0.022, 0.16, 0.42))):
    cyl(f"Telescope{k}", r, L, (CT.x + 0.15 - off * 0.5, CT.y + 0.4, 0.785), M_BRASS, verts=14, rot=(0, math.pi / 2, 0.08))
cyl("TelescopeCap", 0.036, 0.04, (CT.x + 0.31, CT.y + 0.41, 0.785), M_BRASS, verts=14, rot=(0, math.pi / 2, 0.08))
# the cutlass, bare, lying before his seat: curved blade, brass shell guard, wooden grip
CUT0 = Vector((CT.x + 0.30, CT.y - 0.05, 0.758))
blade = []; bw = []
for i in range(9):
    t = i / 8; p = CUT0 + Vector((-0.62 * t, 0.06 * math.sin(t * 2.6), 0.0))
    w = 0.036 * (1 - 0.55 * t ** 2)
    blade += [p + Vector((0, -w / 2, 0)), p + Vector((0, w / 2, 0.003))]
bf = [[2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2] for i in range(8)]
from_pydata("CutlassBlade", blade, bf, M_STEEL)
lathe("CutlassGuard", [(0, 0), (0.06, 0.0), (0.065, 0.015), (0.03, 0.03), (0, 0.03)], tuple(CUT0 + Vector((0.01, 0.0, 0.0))), M_BRASS, steps=12, rot=(0, math.pi / 2, 0))
cyl("CutlassGrip", 0.014, 0.12, tuple(CUT0 + Vector((0.09, 0, 0.012))), M_SETTLE, verts=8, rot=(0, math.pi / 2, 0))
lathe("CutlassPommel", [(0, 0), (0.017, 0), (0.017, 0.02), (0, 0.025)], tuple(CUT0 + Vector((0.15, 0, 0.012))), M_BRASS, steps=8, rot=(0, math.pi / 2, 0))
# his stick, "like a handspike", leaning against the settle end
cyl("Handspike", 0.028, 1.3, (SX - 0.12, SET_Y - 0.48, 0.63), M_SETTLE, verts=8, rot=(0.0, -0.18, 0), r2=0.02)
# a chair pulled back from the table on the reader's side
def chair(name, cx, cy, yaw, mat=M_TABLE):
    R_ = Matrix.Rotation(yaw, 3, 'Z'); c = Vector((cx, cy, 0))
    box(f"{name}_Seat", (0.42, 0.40, 0.04), tuple(c + Vector((0, 0, 0.45))), mat, rot=(0, 0, yaw))
    for (lx, ly) in ((-0.18, -0.17), (0.18, -0.17), (-0.18, 0.17), (0.18, 0.17)):
        box(f"{name}_Leg{lx}{ly}", (0.035, 0.035, 0.45), tuple(c + R_ @ Vector((lx, ly, 0.225))), mat, rot=(0, 0, yaw))
    for lx in (-0.18, 0.18): box(f"{name}_Post{lx}", (0.035, 0.035, 0.5), tuple(c + R_ @ Vector((lx, 0.18, 0.72))), mat, rot=(0, 0, yaw))
    for k, z in enumerate((0.72, 0.9)): box(f"{name}_Rail{k}", (0.38, 0.025, 0.06), tuple(c + R_ @ Vector((0, 0.18, z))), mat, rot=(0, 0, yaw))
    for k in range(2): box(f"{name}_Stretch{k}", (0.36, 0.02, 0.02), tuple(c + R_ @ Vector((0, -0.17 + k * 0.34, 0.15))), mat, rot=(0, 0, yaw))
chair("CChair", CT.x + 0.05, CT.y - 0.85, math.radians(170))

# ----------------------------------------------------------------------------- the longcase clock against the north wall
CL = Vector((CLOCK_X, Y1 - 0.14, 0))
box("Clock_Plinth", (0.52, 0.28, 0.42), (CL.x, CL.y, 0.21), M_SETTLE, bevel=0.01)
box("Clock_Trunk", (0.40, 0.22, 1.05), (CL.x, CL.y, 0.94), M_SETTLE, bevel=0.01)
box("Clock_TrunkDoor", (0.26, 0.02, 0.8), (CL.x, CL.y - 0.115, 0.95), M_SETTLE, bevel=0.005)
box("Clock_Hood", (0.50, 0.28, 0.52), (CL.x, CL.y, 1.73), M_SETTLE, bevel=0.01)
box("Clock_Cornice", (0.56, 0.32, 0.06), (CL.x, CL.y, 2.02), M_SETTLE, bevel=0.01)
box("Clock_Dial", (0.34, 0.01, 0.34), (CL.x, CL.y - 0.142, 1.72), M_CLOCKFACE)
for k in range(12):
    a = 2 * math.pi * k / 12
    box(f"Clock_Hour{k}", (0.012, 0.004, 0.03), (CL.x + math.sin(a) * 0.13, CL.y - 0.149, 1.72 + math.cos(a) * 0.13), M_SOOT, rot=(0, a, 0))
box("Clock_HandH", (0.012, 0.004, 0.08), (CL.x + 0.02, CL.y - 0.152, 1.75), M_SOOT, rot=(0, 0.6, 0))
box("Clock_HandM", (0.008, 0.004, 0.115), (CL.x - 0.03, CL.y - 0.154, 1.76), M_SOOT, rot=(0, -0.5, 0))
for s in (-1, 1): cyl(f"Clock_Column{s}", 0.015, 0.44, (CL.x + s * 0.22, CL.y - 0.12, 1.72), M_BRASS, verts=8)
for s in (-1, 0, 1): lathe(f"Clock_Finial{s}", [(0, 0), (0.025, 0), (0.02, 0.05), (0, 0.1)], (CL.x + s * 0.22, CL.y - 0.05, 2.05), M_BRASS, steps=8)

# ----------------------------------------------------------------------------- the other furniture: tables, benches, chairs
def trestle_table(name, cx, cy, L=1.5, D=0.7, yaw=0.0, benches=(-1, 1)):
    R_ = Matrix.Rotation(yaw, 3, 'Z'); c = Vector((cx, cy, 0))
    box(f"{name}_Top", (L, D, 0.05), tuple(c + Vector((0, 0, 0.74))), M_TABLE, rot=(0, 0, yaw), bevel=0.008)
    for s in (-1, 1):
        box(f"{name}_Trestle{s}", (0.07, D * 0.8, 0.70), tuple(c + R_ @ Vector((s * (L / 2 - 0.22), 0, 0.36))), M_TABLE, rot=(0, 0, yaw))
        box(f"{name}_Foot{s}", (0.09, D * 0.9, 0.07), tuple(c + R_ @ Vector((s * (L / 2 - 0.22), 0, 0.035))), M_TABLE, rot=(0, 0, yaw))
    box(f"{name}_Stretcher", (L - 0.45, 0.05, 0.07), tuple(c + Vector((0, 0, 0.22))), M_TABLE, rot=(0, 0, yaw))
    for s in benches:
        bc = c + R_ @ Vector((0, s * (D / 2 + 0.28), 0))
        box(f"{name}_Bench{s}", (L - 0.1, 0.26, 0.045), tuple(bc + Vector((0, 0, 0.44))), M_TABLE, rot=(0, 0, yaw + rb.uniform(-0.03, 0.03)), bevel=0.005)
        for e in (-1, 1): box(f"{name}_BenchLeg{s}{e}", (0.05, 0.22, 0.42), tuple(bc + R_ @ Vector((e * (L / 2 - 0.22), 0, 0.21))), M_TABLE, rot=(0, 0, yaw))
    return c
T1 = trestle_table("TableA", -1.5, 1.45, L=1.5, yaw=0.0, benches=(-1,))
T2 = trestle_table("TableB", -0.1, -0.6, L=1.4, yaw=math.radians(88))
chair("ChairA", -0.85, 1.5, math.radians(90))
chair("ChairB", 0.95, -1.75, math.radians(200))
for (x, y) in ((-1.8, 1.5), (-0.2, -0.3)):
    lathe(f"Pot{x}", [(0, 0), (0.045, 0), (0.048, 0.02), (0.042, 0.11), (0.048, 0.13), (0, 0.13)], (x, y, 0.765), M_PEWTER, steps=10)
# candles left burning from the night, in pewter sticks
CANDLES = []
for k, (x, y, h) in enumerate(((-1.2, 1.35, 0.12), (0.05, -0.85, 0.08))):
    lathe(f"CandleStick{k}", [(0, 0), (0.06, 0), (0.06, 0.012), (0.014, 0.03), (0.012, 0.09), (0.028, 0.1), (0, 0.105)], (x, y, 0.765), M_PEWTER, steps=10)
    cyl(f"Candle{k}", 0.011, h, (x, y, 0.87 + h / 2), M_WAX, verts=8)
    tip = Vector((x, y, 0.87 + h + 0.012)); CANDLES.append(tip)
    FLc = Builder(f"CandleFlame{k}", M_FLAME)
    for a in (0.0, math.pi / 2):
        d = Vector((math.cos(a), math.sin(a), 0)) * 0.006
        FLc.add([tip - d, tip + d, tip + Vector((0, 0, 0.025)) + d * 0.6, tip + Vector((0, 0, 0.04)), tip + Vector((0, 0, 0.025)) - d * 0.6], [[0, 1, 2, 3, 4]])
    FLc.finish(smooth_=False)

# ----------------------------------------------------------------------------- the foot of the old stairs (west wall, rising south to north)
for k in range(7):
    z = (k + 1) * 0.2; y = -0.35 + k * 0.24
    box(f"StairTread{k}", (0.85, 0.27, 0.035), (X0 + 0.43, y, z), M_TABLE, bevel=0.005)
    box(f"StairRiser{k}", (0.85, 0.02, 0.2), (X0 + 0.43, y - 0.125, z - 0.1), M_BEAM)
box("StairString", (0.05, 1.9, 0.28), (X0 + 0.88, 0.37, 0.85), M_BEAM, rot=(math.atan2(1.4, 1.68), 0, 0))
box("StairBox", (0.85, 1.7, 1.4), (X0 + 0.43, 0.65, 0.4), M_WALL)   # boxed in beneath
cyl("Newel", 0.045, 1.05, (X0 + 0.9, -0.5, 0.52), M_BEAM, verts=8)
box("Handrail", (0.05, 2.1, 0.05), (X0 + 0.9, 0.45, 1.6), M_BEAM, rot=(math.atan2(1.4, 1.68), 0, 0))
box("CeilingHatch", (0.9, 1.4, 0.03), (X0 + 0.45, 1.7, H - 0.0), M_SOOT)

# ----------------------------------------------------------------------------- the bar glimpsed through its doorway
box("Bar_Floor", (3.0, 2.2, 0.1), (BDOOR_X, Y0 - WT - 1.1, -0.1), M_FLOOR)
box("Bar_BackWall", (3.0, 0.2, H), (BDOOR_X, Y0 - WT - 2.3, H / 2), M_WALL)
box("Bar_Ceiling", (3.0, 2.4, 0.06), (BDOOR_X, Y0 - WT - 1.1, H + 0.03), M_CEILB)
for s in (-1, 1): box(f"Bar_Side{s}", (0.2, 2.4, H), (BDOOR_X + s * 1.5, Y0 - WT - 1.1, H / 2), M_WALL)
box("Bar_Counter", (1.6, 0.5, 1.0), (BDOOR_X + 0.3, Y0 - WT - 1.4, 0.5), M_BAR, bevel=0.01)
for k in range(3): box(f"Bar_Shelf{k}", (1.8, 0.25, 0.03), (BDOOR_X, Y0 - WT - 2.05, 1.35 + k * 0.35), M_BAR)
for k, x in enumerate((-0.4, 0.15, 0.7)):
    lathe(f"Bar_Cask{k}", [(0, -0.33), (0.25, -0.33), (0.29, 0.0), (0.25, 0.33), (0, 0.33)], (BDOOR_X + x, Y0 - WT - 2.0, 0.32), M_BAR, steps=12, rot=(math.pi / 2, 0, 0))
for k in range(9):
    lathe(f"Bar_Bottle{k}", [(0, 0), (0.035, 0), (0.037, 0.16), (0.013, 0.22), (0, 0.24)], (BDOOR_X - 0.8 + k * 0.2, Y0 - WT - 2.05, 1.715), plain("M_BottleGlass", (0.04, 0.10, 0.05), rough=0.1), steps=7)

# ----------------------------------------------------------------------------- outside the inn door: the frosty road, verge, hedge, the signboard on its post
box("Doorstep", (0.6, 1.2, 0.08), (X1 + WT + 0.3, IDOOR_Y, -0.04), M_STONE)
box("Road", (40.0, 60.0, 0.2), (X1 + WT + 20.6, 0, -0.18), M_ROAD)
# a frost-white hedge bank across the road, low and long, fading into the fog
box("HedgeBank", (1.6, 40.0, 1.3), (X1 + WT + 11.0, 0.0, 0.5), M_HEDGE, bevel=0.4)
# the signboard: a tall post with an arm, the big painted board hanging from two irons, its lower frame notched
SP = Vector((X1 + WT + 3.2, 0.2, 0))
box("SignPost", (0.2, 0.2, 4.2), (SP.x, SP.y, 2.0), M_BEAM, bevel=0.02)
box("SignArm", (0.14, 1.6, 0.14), (SP.x, SP.y - 0.75, 3.85), M_BEAM)
box("SignBrace", (0.1, 0.9, 0.1), (SP.x, SP.y - 0.3, 3.5), M_BEAM, rot=(-0.75, 0, 0))
for s in (-1, 1): cyl(f"SignIron{s}", 0.008, 0.25, (SP.x, SP.y - 0.75 + s * 0.45, 3.67), M_IRON, verts=4)
box("SignBoard", (0.06, 1.15, 0.85), (SP.x, SP.y - 0.75, 3.1), M_SIGN, bevel=0.01)
for s in (-1, 1): box(f"SignFrameV{s}", (0.08, 0.05, 0.92), (SP.x, SP.y - 0.75 + s * 0.6, 3.1), M_BEAM)
box("SignFrameT", (0.08, 1.25, 0.05), (SP.x, SP.y - 0.75, 3.54), M_BEAM)
box("SignFrameB_L", (0.08, 0.55, 0.05), (SP.x, SP.y - 1.07, 2.66), M_BEAM)
box("SignFrameB_R", (0.08, 0.5, 0.05), (SP.x, SP.y - 0.43, 2.66), M_BEAM)    # the notch between them
# the painted figure: an admiral in a blue coat, roughly (a darker oval and a lighter face/hat shape)
for (dy, dz, sy, sz, mat) in ((0.0, -0.1, 0.42, 0.5, M_SIGNFIG), (0.0, 0.22, 0.14, 0.14, M_SIGNFIG)):
    box(f"SignFig{dz}", (0.065, sy, sz), (SP.x - 0.005, SP.y - 0.75 + dy, 3.1 + dz), mat)
def sky_dome(name, radius=70.0, seg=32, rings=10):
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    els = [math.radians(-8)] + [math.radians(90.0 * (j / rings) ** 1.3) for j in range(rings)] + [math.radians(89.9)]
    grid = [[bm.verts.new((radius * math.cos(e) * math.cos(2 * math.pi * i / seg), radius * math.cos(e) * math.sin(2 * math.pi * i / seg), radius * math.sin(e))) for i in range(seg + 1)] for e in els]
    for j in range(len(els) - 1):
        for i in range(seg):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for l, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): l[uvl].uv = (ii / seg, jj / (len(els) - 1))
    for f in bm.faces:
        f.normal_update()
        if f.normal.dot(f.calc_center_median()) > 0: f.normal_flip()
    o = mesh_obj(name, bm, M_SKY, smooth_=True)
    o.visible_diffuse = False; o.visible_glossy = False; o.visible_shadow = False
    return o
sky_dome("SkyDome")

# ----------------------------------------------------------------------------- lights, world, living empties, anchors
light_obj("light.daylight", 'SUN', 1.2, (0.92, 0.94, 1.0), tuple(SUN_DIR * 30), direction=-SUN_DIR, angle=math.radians(12))
light_obj("light.window", 'AREA', 60.0, (0.85, 0.90, 1.0), (WIN_N_X, Y1 + 0.1, (WIN_SILL + WIN_HEAD) / 2), direction=(0, -1, -0.15), size=WIN_W, shape='RECTANGLE', size_y=WIN_HEAD - WIN_SILL)
light_obj("light.door", 'AREA', 140.0, (0.85, 0.90, 1.0), (X1 + 0.1, IDOOR_Y, 1.0), direction=(-1, 0, -0.1), size=IDOOR_W, shape='RECTANGLE', size_y=IDOOR_H)
light_obj("light.barWindow", 'AREA', 40.0, (0.85, 0.9, 1.0), (BDOOR_X, Y0 - WT - 2.1, 1.8), direction=(0, 1, -0.3), size=1.0)
light_obj("light.fire", 'POINT', 70.0, (1.0, 0.52, 0.22), (FIRE_X, Y1 - 0.55, 0.45), shadow_soft_size=0.15)
for k, p in enumerate(CANDLES): light_obj(f"light.candle{k + 1}", 'POINT', 2.5, (1.0, 0.62, 0.3), tuple(p + Vector((0, 0, 0.03))), shadow_soft_size=0.02)
world = bpy.data.worlds.new("Frost"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.58, 0.62, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

living_empty("fx.fire.grate", (FIRE_X, Y1 - 0.3, 0.3), 0.22)
for k, p in enumerate(CANDLES): living_empty(f"fx.candle.table{k + 1}", tuple(p), 0.012)
for k, dx in enumerate((-0.75, 0.75)): pass
living_empty("sound.fire.grate", (FIRE_X, Y1 - 0.4, 0.4), 0.3)
living_empty("sound.clock.longcase", (CL.x, CL.y - 0.1, 1.2), 0.3)
living_empty("sound.wind.door", (X1 + 0.5, IDOOR_Y, 1.2), 0.3)

anchor("reader.entrance", (READER.x, READER.y, 0.0))
fwd = (LOOK_AT - READER); fwd.z = 0; fwd.normalize()
anchor("reader.look", tuple(READER + fwd + Vector((0, 0, EYE))))
anchor("scene.centre", (0.0, 0.0, 0.0))
anchor("parlour.fire", (FIRE_X, Y1 - 0.4, 0.0))
anchor("parlour.captainTable", (CT.x, CT.y, 0.73))
anchor("parlour.clock", (CL.x, CL.y, 0.0))
anchor("parlour.innDoor", (X1, IDOOR_Y, 0.0))
anchor("parlour.barDoor", (BDOOR_X, Y0, 0.0))
anchor("parlour.stairs", (X0 + 0.43, -0.4, 0.0))
anchor("parlour.sign", (SP.x, SP.y - 0.75, 3.1))

E = READER + Vector((0, 0, EYE))
page = box("PagePreview", (0.4, 0.004, 0.55), tuple(E + fwd * 0.6 - Vector((0, 0, 0.05))), plain("M_PagePreview", (0.80, 0.76, 0.66), rough=0.9), rot=(0, 0, math.atan2(fwd.y, fwd.x) - math.pi / 2))
K.apply_all_transforms()

def yawed(deg, dist=4.0, dz=-0.3):
    a = math.radians(deg); d = Matrix.Rotation(a, 3, 'Z') @ fwd
    return tuple(E + d * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(E), yawed(0, 4.0, -0.45), lens=17),
    camera("Cam_Page", tuple(E), yawed(0, 4.0, -0.45), lens=17),
    camera("Cam_Left", tuple(E), yawed(70, 4.0, -0.3), lens=17),
    camera("Cam_Right", tuple(E), yawed(-70, 4.0, -0.3), lens=17),
    camera("Cam_Behind", tuple(E), yawed(180, 4.0, -0.3), lens=17),
    camera("Cam_Table", tuple(E + fwd * 1.3 + Vector((0.3, 0, -0.25))), (CT.x, CT.y, 0.75), lens=28),
    camera("Cam_Door", (X1 - 2.2, IDOOR_Y - 0.5, EYE), (SP.x, SP.y - 0.75, 2.4), lens=24),
]
if not args.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "benbow_parlour_source.blend"))
K.budget()
if args.render:
    B.render_stamped(scene, cams, "benbow-parlour", OUT, args.res, args.cams, page=page, page_cams={"Cam_Page"}, default_exposure=1.0,
                     exposure={"Cam_Door": 0.3}, captures_dir=CAPTURES)
if args.bake or args.export:
    T_ = min(args.tex, 2048)
    stats = K.bake_and_export(
        "benbow_parlour",
        keep_names={"M_SkyDome": "SkyDome", "M_DoorCurtain": "cloth.curtain.door", "M_Blind": "cloth.curtain.blind"},
        size_for={"M_Flags": (T_, T_ // 4, T_), "M_Whitewash": (T_, 0, T_ // 2), "M_Beams": (T_ // 2, T_ // 8, T_ // 2), "M_CeilingBoards": (T_ // 4, 0, T_ // 4),
                  "M_Tables": (T_ // 2, T_ // 8, T_ // 2), "M_Settle": (T_ // 2, T_ // 8, T_ // 4), "M_BarWood": (T_ // 4, 0, T_ // 4),
                  "M_DoorCurtain": (T_ // 4, 0, T_ // 4), "M_FrostRoad": (T_ // 2, 0, T_ // 4), "M_FrostHedge": (T_ // 4, 0, 0), "M_SkyDome": (T_ // 2, 0, 0),
                  "M_HearthStone": (T_ // 4, 0, T_ // 4), "M_Pewter": (T_ // 8, 0, 0), "M_Brass": (T_ // 8, 0, 0)},
        keep_uv={"SkyDome"}, emit_only={"M_SkyDome"}, remove=[page], default_div=16)
    print("STATS", stats)
print("DONE")
