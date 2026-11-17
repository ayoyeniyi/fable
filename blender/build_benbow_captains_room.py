"""
Fable: the captain's room upstairs at the Admiral Benbow (Treasure Island, chapter 4, "The Sea-chest"). A chapter
step-in room: built ahead of time, served from the server, downloaded by the headset.

"... the little room where he had slept so long" ... "a strong old sea-chest, with the initial 'B' burned on the top of
it with a hot iron, and the corners somewhat smashed and broken as by long, rough usage." ... "a suit of very good
clothes, carefully brushed and folded" ... "a quadrant, a tin canikin, several sticks of tobacco, two brace of very
handsome pistols, a piece of bar silver, an old Spanish watch and some other trinkets of little value and mostly of
foreign make, a pair of compasses mounted with brass, and five or six curious West Indian shells" ... "an old boat-cloak,
whitened with sea-salt" ... "a bundle tied up in oilcloth, and looking like papers, and a canvas bag that gave forth, at
a touch, the jingle of gold" ... "doubloons, and louis d'ors, and guineas, and pieces of eight" (chapter 4).

The moment: a frosty January evening. The small front bedroom under the roof (4 x 3.5 m): rough whitewashed plaster,
the ceiling sloping down to the eaves on the road side, smoke-dark rafters and collar beams, bare scrubbed boards. The
captain's narrow oak bed with its pillow and blanket against the end wall; his patched blue coat on a peg; a stool with
thread and big sailmaker's needles. In the middle of the floor the sea-chest stands open, its lid thrown back: the
burned "B" on the lid, the iron bands and battered corners; the folded suit, the quadrant, the canikin, tobacco, the
pistols, the bar silver, the watch, the compasses and shells laid out on the boards beside it; the salt-whitened boat
cloak half drawn out; the oilcloth bundle tied with tarry twine and the canvas bag of mixed coin, a few coins spilled. A
single tallow candle stands on the floor by the chest and is the only warm light; cold blue moonlight through fog at the
small window over the road. The door to the stair landing stands ajar. No people.

Living scene (docs/LIVING_SCENES.md): fx.candle.floor (radius extra), cloth.curtain.window, sound.clock.below,
sound.wind.window.

Node names: anchor.reader.entrance (feet, floor z = 0), anchor.reader.look (eye height, facing the chest),
anchor.scene.centre / anchor.room.chest, anchor.room.window, anchor.room.door, anchor.room.bed;
light.candle (POINT), light.moon (AREA at the window, cool), light.landing (POINT, a little warmth up the stair).

Axes: metres, +Z up. Room x -2..2, y -1.75..1.75; the eaves (low side) and the window over the road on the north (+y),
the door in the south wall, the bed against the west wall. The reader stands south of the chest facing north.

Run headless (one Blender at a time):
  blender -b -P blender/build_benbow_captains_room.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_benbow_captains_room.py -- --render --samples 48 --res 1400 --captures captures/blender/benbow-captains-room
  blender -b -P blender/build_benbow_captains_room.py -- --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import treasure_kit as K
from treasure_kit import F, smooth, lerp, new_mat, plain, noisy, box, cyl, mesh_obj, from_pydata, lathe, Builder, \
    anchor, living_empty, light_obj, camera
import scene_kit_b2 as B

CAPTURES = sys.argv[sys.argv.index("--captures") + 1] if "--captures" in sys.argv else ""
USE_CPU = "--cpu" in sys.argv
if CAPTURES: i = sys.argv.index("--captures"); del sys.argv[i:i + 2]
if USE_CPU: sys.argv.remove("--cpu")
SAMPLES_GIVEN = "--samples" in sys.argv
args = K.parse_args("out/benbow-captains-room")
if not SAMPLES_GIVEN: args.samples = 48
OUT = args.out
scene, COLL = K.reset_scene("BenbowCaptainsRoom", args, bounces=8, diffuse=5, clamp=8.0)
if USE_CPU: scene.cycles.device = 'CPU'
rb = random.Random(1756)

# ----------------------------------------------------------------------------- dimensions
X0, X1, Y0, Y1 = -2.0, 2.0, -1.75, 1.75
H = 2.45                    # flat ceiling (under the collar beams)
EAVE_Z = 1.25               # the wall plate on the road side
SLOPE_Y = 0.15              # where the slope meets the flat ceiling
WT = 0.45
EYE = 1.55
CHEST = Vector((0.25, 0.35, 0))
READER = Vector((0.05, -1.05, 0.0))
LOOK_AT = Vector((0.3, 1.2, 0.0))
WIN_X, WIN_W, WIN_Z0, WIN_Z1 = 0.55, 0.7, 0.75, 1.2      # a small window low in the eaves wall (north)
DOOR_X, DOOR_W, DOOR_H = -1.35, 0.8, 1.9

# ----------------------------------------------------------------------------- materials
def whitewash_mat(name):
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    n1, _ = g.noise(P, 1.3, 5); n2, _ = g.noise(P, 14.0, 3)
    col = g.ramp(n1 * 0.6 + n2 * 0.4, [(0.3, (0.50, 0.49, 0.45)), (0.7, (0.60, 0.58, 0.53))])
    lumps, _ = g.noise(P, 4.0, 4)
    damp = g.ss(n1, 0.55, 0.7) * (1.0 - g.ss(z, 0.0, 0.6)) * 0.4
    col = g.mix(damp, col, (0.36, 0.35, 0.30))
    col = g.mul(col, g.ao(0.3), 0.6)
    g.set(b.inputs["Base Color"], col); b.inputs["Roughness"].default_value = 0.94
    g.bump(b, lumps * 0.6 + n2 * 0.4, 0.6, 0.008)
    return m

def boards_mat(name):
    """bare deal boards scrubbed grey, wide and uneven, nail heads, a worn path from the door to the bed."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    bw = 0.24
    row = (x / bw).floor()
    rh, _ = g.white(g.comb(row, 0.3, 0.0))
    L = 2.2 + rh * 1.6
    seg = ((y + rh * 5.0) / L).floor()
    bid, _ = g.white(g.comb(row, seg, 1.0))
    fu = (x / bw).fract(); fv = ((y + rh * 5.0) / L).fract()
    seam = (1.0 - g.ss(fu.min(1.0 - fu), 0.0, 0.025)).max(1.0 - g.ss(fv.min(1.0 - fv) * L, 0.0, 0.006))
    n1, _ = g.noise(g.comb(x * 6.0, y * 0.3 + bid * 9.0, z), 3.0, 5, 0.6, 1.0)
    col = g.ramp(n1, [(0.2, (0.17, 0.13, 0.09)), (0.5, (0.25, 0.20, 0.14)), (0.85, (0.32, 0.27, 0.20))])
    col = g.mul(col, g.comb(0.85 + bid * 0.3, 0.85 + bid * 0.28, 0.85 + bid * 0.25))
    col = g.mix(seam * 0.8, col, (0.04, 0.03, 0.02))
    col = g.mul(col, g.ao(0.25), 0.6)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.85
    g.bump(b, n1 * 0.3 - seam * 1.0, 0.4, 0.003)
    return m

def oak_mat(name, base=(0.09, 0.06, 0.035), dark=(0.03, 0.02, 0.012), light=(0.14, 0.10, 0.06), axis='X', rough=0.7, adze=True):
    m, nt, b, g = new_mat(name)
    P = g.pos()
    st = {'X': (0.15, 3.0, 3.0), 'Y': (3.0, 0.15, 3.0), 'Z': (3.0, 3.0, 0.15)}[axis]
    Q = g.stretch(P, *st)
    n1, _ = g.noise(Q, 3.0, 6, 0.65, 2.5); n2, _ = g.noise(Q, 30.0, 3)
    col = g.ramp(n1 * 0.7 + n2 * 0.3, [(0.2, dark), (0.5, base), (0.85, light)])
    col = g.mul(col, g.ao(0.12), 0.6)
    g.set(b.inputs["Base Color"], col); b.inputs["Roughness"].default_value = rough
    hgt = n2 * 0.4 + n1 * 0.4
    if adze:
        ad = g.vor(g.stretch(P, *(s * 0.5 for s in st)), 4.0, feature='F1'); hgt = hgt + ad * 0.6
    g.bump(b, hgt, 0.5, 0.004)
    return m

def chest_mat(name="M_SeaChest"):
    """the sea-chest: weathered, tarred and salt-stained oak, the initial B burned into the lid (a scorched letter on the
    lid's top face), battered corners lighter where the tar has worn off."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    Q = g.stretch(P, 0.2, 3.0, 3.0)
    n1, _ = g.noise(Q, 3.0, 6, 0.65, 2.0); n2, _ = g.noise(P, 7.0, 4)
    col = g.ramp(n1 * 0.6 + n2 * 0.4, [(0.25, (0.05, 0.035, 0.02)), (0.55, (0.12, 0.085, 0.05)), (0.85, (0.20, 0.15, 0.09))])
    salt = g.ss(n2, 0.62, 0.78) * 0.5
    col = g.mix(salt, col, (0.42, 0.40, 0.36))
    col = g.mul(col, g.ao(0.1), 0.6)
    g.set(b.inputs["Base Color"], col); b.inputs["Roughness"].default_value = 0.75
    g.bump(b, n1 * 0.5 + n2 * 0.3, 0.5, 0.004)
    return m

M_WALL = whitewash_mat("M_RoughPlaster")
M_FLOOR = boards_mat("M_Boards")
M_BEAM = oak_mat("M_Rafters")
M_OAK = oak_mat("M_OakFurniture", base=(0.14, 0.09, 0.05), dark=(0.05, 0.03, 0.018), light=(0.22, 0.15, 0.09), rough=0.6, adze=False)
M_CHEST = chest_mat()
M_BRAND = plain("M_BurnedB", (0.012, 0.008, 0.005), rough=0.9)
M_IRON = noisy("M_Iron", [(0.02, 0.02, 0.02), (0.06, 0.045, 0.035), (0.12, 0.06, 0.03)], scale=20, rough=0.7, metallic=0.5, bump=0.4)
M_BRASS = noisy("M_Brass", [(0.40, 0.27, 0.08), (0.55, 0.40, 0.14), (0.66, 0.50, 0.22)], scale=10, rough=0.3, metallic=0.8, bump=0.05)
M_SILVER = noisy("M_BarSilver", [(0.42, 0.42, 0.42), (0.58, 0.58, 0.57)], scale=12, rough=0.35, metallic=0.8, bump=0.2)
M_GOLD = noisy("M_CoinGold", [(0.55, 0.38, 0.10), (0.72, 0.52, 0.18)], scale=40, rough=0.3, metallic=0.85, bump=0.1)
M_TIN = noisy("M_Tin", [(0.35, 0.35, 0.34), (0.48, 0.47, 0.45)], scale=14, rough=0.45, metallic=0.6, bump=0.15)
M_WOOL = noisy("M_BlueCoat", [(0.03, 0.04, 0.09), (0.05, 0.06, 0.13)], scale=60, rough=0.95, bump=0.15)
M_PATCH = noisy("M_CoatPatch", [(0.08, 0.07, 0.06), (0.12, 0.10, 0.08)], scale=60, rough=0.95, bump=0.15)
M_SUIT = noisy("M_GoodSuit", [(0.10, 0.06, 0.04), (0.14, 0.09, 0.06)], scale=80, rough=0.9, bump=0.1)
M_CLOAK = noisy("M_BoatCloak", [(0.22, 0.22, 0.20), (0.42, 0.41, 0.38), (0.55, 0.54, 0.50)], scale=8, rough=0.95, bump=0.3)
M_LINEN = noisy("M_Bedding", [(0.42, 0.40, 0.35), (0.50, 0.48, 0.42)], scale=30, rough=0.9, bump=0.15)
M_BLANKET = noisy("M_Blanket", [(0.16, 0.12, 0.08), (0.24, 0.18, 0.12)], scale=40, rough=0.95, bump=0.2)
M_CANVAS = noisy("M_CanvasBag", [(0.36, 0.31, 0.22), (0.46, 0.40, 0.29)], scale=60, rough=0.9, bump=0.3)
M_OILCLOTH = noisy("M_Oilcloth", [(0.06, 0.06, 0.04), (0.12, 0.11, 0.07)], scale=10, rough=0.35, bump=0.2)
M_TWINE = plain("M_Twine", (0.10, 0.07, 0.04), rough=0.8)
M_TOBACCO = noisy("M_Tobacco", [(0.05, 0.03, 0.015), (0.09, 0.05, 0.025)], scale=40, rough=0.7, bump=0.3)
M_SHELL = noisy("M_Shells", [(0.62, 0.52, 0.42), (0.75, 0.62, 0.50), (0.55, 0.30, 0.25)], scale=30, rough=0.3, coat=0.4, bump=0.2)
M_WAX = plain("M_Tallow", (0.68, 0.62, 0.46), rough=0.5)
M_FLAME = plain("M_Flame", (0.0, 0.0, 0.0), rough=1.0, emission=(1.0, 0.55, 0.2), strength=12.0)
M_GLASS = plain("M_Glass", (0.6, 0.65, 0.65), rough=0.05, alpha=0.12)
M_FOG = plain("M_FogNight", (0.0, 0.0, 0.0), rough=1.0, emission=(0.10, 0.13, 0.20), strength=1.0)
M_CURTAIN = noisy("M_WindowCloth", [(0.20, 0.18, 0.14), (0.26, 0.24, 0.19)], scale=40, rough=0.95, bump=0.1)
M_WATCHFACE = plain("M_WatchFace", (0.62, 0.58, 0.48), rough=0.3)

# ----------------------------------------------------------------------------- the room shell under the roof
box("Floor", (X1 - X0 + 2 * WT, Y1 - Y0 + 2 * WT, 0.1), (0, 0, -0.05), M_FLOOR)
# walls: west and east (gable ends, full height, the sloping top filled), south (full), north (the low eaves wall with the window)
def wall_box(nm, size, loc, mat=M_WALL): box(nm, size, loc, mat)
wall_box("WallS_L", ((DOOR_X - DOOR_W / 2) - (X0 - WT), WT, H + 0.2), (((DOOR_X - DOOR_W / 2) + (X0 - WT)) / 2, Y0 - WT / 2, (H + 0.2) / 2))
wall_box("WallS_R", ((X1 + WT) - (DOOR_X + DOOR_W / 2), WT, H + 0.2), (((DOOR_X + DOOR_W / 2) + (X1 + WT)) / 2, Y0 - WT / 2, (H + 0.2) / 2))
wall_box("WallS_T", (DOOR_W, WT, H + 0.2 - DOOR_H), (DOOR_X, Y0 - WT / 2, (H + 0.2 + DOOR_H) / 2))
wall_box("WallN_L", ((WIN_X - WIN_W / 2) - (X0 - WT), WT, EAVE_Z), (((WIN_X - WIN_W / 2) + (X0 - WT)) / 2, Y1 + WT / 2, EAVE_Z / 2))
wall_box("WallN_R", ((X1 + WT) - (WIN_X + WIN_W / 2), WT, EAVE_Z), (((WIN_X + WIN_W / 2) + (X1 + WT)) / 2, Y1 + WT / 2, EAVE_Z / 2))
wall_box("WallN_B", (WIN_W, WT, WIN_Z0), (WIN_X, Y1 + WT / 2, WIN_Z0 / 2))
wall_box("WallN_T", (WIN_W, WT, EAVE_Z - WIN_Z1), (WIN_X, Y1 + WT / 2, (EAVE_Z + WIN_Z1) / 2))
for sx, xc in ((-1, X0 - WT / 2), (1, X1 + WT / 2)):
    wall_box(f"WallG{sx}", (WT, Y1 - Y0 + 2 * WT, H + 0.2), (xc, 0, (H + 0.2) / 2))
# the sloping ceiling from the eaves up to the flat, plastered between rafters; the flat ceiling under the collars
SL = math.atan2(H - EAVE_Z, Y1 - SLOPE_Y)
sl_len = math.hypot(H - EAVE_Z, Y1 - SLOPE_Y)
box("SlopeCeiling", (X1 - X0 + 0.02, sl_len + 0.1, 0.05), (0, (Y1 + SLOPE_Y) / 2, (EAVE_Z + H) / 2 + 0.02), M_WALL, rot=(-SL, 0, 0))
box("FlatCeiling", (X1 - X0 + 0.02, SLOPE_Y - Y0 + 0.02, 0.05), (0, (SLOPE_Y + Y0) / 2, H + 0.025), M_WALL)
for k in range(6):
    x = X0 + 0.2 + k * (X1 - X0 - 0.4) / 5
    box(f"Rafter{k}", (0.1, sl_len + 0.1, 0.13), (x, (Y1 + SLOPE_Y) / 2, (EAVE_Z + H) / 2 - 0.05), M_BEAM, rot=(-SL, 0, 0), bevel=0.008)
    box(f"Collar{k}", (0.1, SLOPE_Y - Y0, 0.12), (x, (SLOPE_Y + Y0) / 2, H - 0.06), M_BEAM, bevel=0.008)
box("WallPlate", (X1 - X0, 0.18, 0.14), (0, Y1 - 0.06, EAVE_Z + 0.02), M_BEAM, bevel=0.01)
# the door: frame, the leaf ajar into the room, the dark landing beyond with a faint glow up the stair
for s in (-1, 1): box(f"DoorJamb{s}", (0.09, WT + 0.04, DOOR_H), (DOOR_X + s * (DOOR_W / 2 + 0.045), Y0 - WT / 2, DOOR_H / 2), M_BEAM)
box("DoorHead", (DOOR_W + 0.26, WT + 0.04, 0.12), (DOOR_X, Y0 - WT / 2, DOOR_H + 0.06), M_BEAM)
hinge = Vector((DOOR_X - DOOR_W / 2 + 0.02, Y0 + 0.02, 0)); dd = Vector((math.cos(math.radians(62)), math.sin(math.radians(62)), 0))
for i in range(4):
    u = (i + 0.5) * (DOOR_W - 0.04) / 4
    box(f"DoorBoard{i}", ((DOOR_W - 0.04) / 4 - 0.004, 0.03, DOOR_H - 0.03), tuple(hinge + dd * u + Vector((0, 0, DOOR_H / 2))), M_OAK, rot=(0, 0, math.radians(62)))
for k, z in enumerate((0.3, 1.55)):
    box(f"DoorLedge{k}", (DOOR_W - 0.1, 0.025, 0.12), tuple(hinge + dd * DOOR_W / 2 + Vector((0, 0, z)) + Vector((dd.y, -dd.x, 0)) * 0.03), M_OAK, rot=(0, 0, math.radians(62)))
box("Landing", (1.6, 1.6, 0.1), (DOOR_X, Y0 - WT - 0.8, -0.05), M_FLOOR)
box("LandingWall", (1.8, 0.1, 2.4), (DOOR_X, Y0 - WT - 1.6, 1.2), M_WALL)
box("LandingSide", (0.1, 1.6, 2.4), (DOOR_X - 0.8, Y0 - WT - 0.8, 1.2), M_WALL)
box("LandingCeil", (1.8, 1.8, 0.05), (DOOR_X, Y0 - WT - 0.8, 2.4), M_WALL)
# the window: a small casement low in the eaves wall, fog and moonlight outside, a scrap of curtain
box("WinGlass", (WIN_W, 0.006, WIN_Z1 - WIN_Z0), (WIN_X, Y1 + 0.08, (WIN_Z0 + WIN_Z1) / 2), M_GLASS)
for k in range(3): box(f"WinV{k}", (0.03, 0.035, WIN_Z1 - WIN_Z0), (WIN_X - WIN_W / 2 + k * WIN_W / 2, Y1 + 0.07, (WIN_Z0 + WIN_Z1) / 2), M_BEAM)
for k in range(3): box(f"WinH{k}", (WIN_W, 0.035, 0.03), (WIN_X, Y1 + 0.07, WIN_Z0 + k * (WIN_Z1 - WIN_Z0) / 2), M_BEAM)
box("WinSill", (WIN_W + 0.1, 0.3, 0.04), (WIN_X, Y1 + 0.1, WIN_Z0 - 0.02), M_BEAM)
box("FogOutside", (3.0, 0.05, 2.0), (WIN_X, Y1 + WT + 1.5, 1.0), M_FOG)
CT = Builder("cloth.curtain.window", M_CURTAIN, living=True)
cv, cw, cf = [], [], []
for j in range(6):
    t = j / 5; zz = WIN_Z1 + 0.08 - t * 0.5
    for i in range(9):
        u = i / 8
        cv.append(Vector((WIN_X - WIN_W / 2 - 0.12 + u * 0.32, Y1 - 0.03 - 0.02 * math.sin(u * 12), zz))); cw.append((t, 0, 0, 1))
for j in range(5):
    for i in range(8):
        a = j * 9 + i; cf.append([a, a + 1, a + 10, a + 9])
CT.add(cv, cf, (1, 1, 1, 1), cw); CT.finish(smooth_=True)
cyl("CurtainRod", 0.008, WIN_W + 0.4, (WIN_X, Y1 - 0.04, WIN_Z1 + 0.09), M_IRON, verts=6, rot=(0, math.pi / 2, 0))

# ----------------------------------------------------------------------------- the captain's narrow bed (west wall), stool, coat on its peg
BX = X0 + 0.45
for (lx, ly) in ((-0.38, -0.95), (0.38, -0.95), (-0.38, 0.95), (0.38, 0.95)):
    box(f"BedPost{lx}{ly}", (0.07, 0.07, 0.55 if ly < 0 else 0.85), (BX + lx, 0.25 + ly, (0.55 if ly < 0 else 0.85) / 2), M_OAK, bevel=0.005)
for s in (-1, 1): box(f"BedRail{s}", (0.05, 1.9, 0.14), (BX + s * 0.38, 0.25, 0.32), M_OAK)
box("BedHead", (0.76, 0.04, 0.4), (BX, 1.2, 0.6), M_OAK)
box("BedFoot", (0.76, 0.04, 0.2), (BX, -0.7, 0.42), M_OAK)
box("Mattress", (0.72, 1.86, 0.14), (BX, 0.25, 0.44), M_LINEN, bevel=0.04)
box("Blanket", (0.78, 1.25, 0.05), (BX, -0.08, 0.53), M_BLANKET, bevel=0.02, rot=(0.0, 0.03, 0.02))
box("BlanketDrop", (0.03, 1.2, 0.3), (BX + 0.4, -0.08, 0.38), M_BLANKET, bevel=0.01)
box("Pillow", (0.55, 0.32, 0.12), (BX, 0.95, 0.56), M_LINEN, bevel=0.05)
# the stool with thread and needles
SX, SY = X1 - 0.55, -0.7
cyl("Stool", 0.18, 0.04, (SX, SY, 0.44), M_OAK, verts=14)
for e in range(3):
    a = 2 * math.pi * e / 3
    cyl(f"StoolLeg{e}", 0.018, 0.44, (SX + math.cos(a) * 0.12, SY + math.sin(a) * 0.12, 0.22), M_OAK, verts=6, rot=(math.sin(a) * 0.15, -math.cos(a) * 0.15, 0))
cyl("ThreadReel", 0.025, 0.05, (SX + 0.05, SY, 0.485), M_TWINE, verts=10)
for k in range(3): cyl(f"Needle{k}", 0.002, 0.11, (SX - 0.06, SY - 0.03 + k * 0.02, 0.463), M_IRON, verts=4, rot=(0, math.pi / 2, 0.2 * k))
# the patched blue coat on a peg on the east wall
box("Peg", (0.12, 0.03, 0.03), (X1 - 0.06, 0.95, 1.75), M_OAK)
coat = Builder("BlueCoat", M_WOOL)
cvs, cfs = [], []
for j in range(8):
    t = j / 7; zz = 1.74 - t * 0.95; w = 0.12 + 0.25 * min(1.0, t * 2.2)
    for i in range(9):
        u = i / 8
        cvs.append(Vector((X1 - 0.07 - 0.06 * math.sin(u * math.pi) * (0.4 + t), 0.95 + (u - 0.5) * 2 * w, zz)))
for j in range(7):
    for i in range(8):
        a = j * 9 + i; cfs.append([a, a + 1, a + 10, a + 9])
coat.add(cvs, cfs); coat.finish(smooth_=True)
box("CoatPatch", (0.01, 0.12, 0.1), (X1 - 0.1, 0.88, 1.2), M_PATCH)
box("CoatPatch2", (0.01, 0.09, 0.08), (X1 - 0.1, 1.08, 1.0), M_PATCH)

# ----------------------------------------------------------------------------- the sea-chest, open, the lid thrown back
CW, CD, CH = 1.0, 0.55, 0.5
yaw_c = math.radians(-6); Rc = Matrix.Rotation(yaw_c, 3, 'Z')
def cp(x, y, z): return tuple(CHEST + Rc @ Vector((x, y, z)))
T_ = 0.035
for nm, size, loc in (("Chest_Front", (CW, T_, CH), (0, -CD / 2 + T_ / 2, CH / 2)), ("Chest_Back", (CW, T_, CH), (0, CD / 2 - T_ / 2, CH / 2)),
                      ("Chest_L", (T_, CD - 2 * T_, CH), (-CW / 2 + T_ / 2, 0, CH / 2)), ("Chest_R", (T_, CD - 2 * T_, CH), (CW / 2 - T_ / 2, 0, CH / 2)),
                      ("Chest_Bottom", (CW - 2 * T_, CD - 2 * T_, 0.03), (0, 0, 0.06))):
    box(nm, size, cp(*loc), M_CHEST, rot=(0, 0, yaw_c), bevel=0.006)
for s in (-1, 1): box(f"Chest_Skid{s}", (CW, 0.06, 0.05), cp(0, s * (CD / 2 - 0.05), 0.025), M_CHEST, rot=(0, 0, yaw_c))
# iron bands round the box and its battered corners (lighter, chipped blocks)
for k, u in enumerate((-0.3, 0.3)):
    box(f"Chest_BandF{k}", (0.04, 0.006, CH), cp(u, -CD / 2 - 0.003, CH / 2), M_IRON, rot=(0, 0, yaw_c))
    box(f"Chest_BandB{k}", (0.04, 0.006, CH), cp(u, CD / 2 + 0.003, CH / 2), M_IRON, rot=(0, 0, yaw_c))
for sx in (-1, 1):
    for sy in (-1, 1):
        box(f"Chest_Corner{sx}{sy}", (0.06, 0.06, 0.07), cp(sx * (CW / 2 - 0.02), sy * (CD / 2 - 0.02), CH - 0.03 + rb.uniform(-0.01, 0.0)), M_CHEST, rot=(0.08 * sy, 0.1 * sx, yaw_c + rb.uniform(-0.2, 0.2)))
# rope beckets at the ends
for s in (-1, 1):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.07, minor_radius=0.013, major_segments=12, minor_segments=5, location=cp(s * (CW / 2 + 0.02), 0, CH * 0.62), rotation=(0, math.pi / 2, yaw_c))
    K._finish(bpy.context.active_object, M_TWINE, smooth_=True)
# the lid, hinged at the back and thrown open, resting against... standing a little past upright
LID_ANG = math.radians(108)
hinge_c = Vector(cp(0, CD / 2, CH))
Rl = Rc @ Matrix.Rotation(-LID_ANG, 3, 'X')
def lp(x, y, z): return tuple(hinge_c + Rl @ Vector((x, y, z)))
lid_rot = (Rc @ Matrix.Rotation(-LID_ANG, 3, 'X')).to_euler()
box("Chest_Lid", (CW + 0.02, CD + 0.02, 0.04), lp(0, -CD / 2, 0.02), M_CHEST, rot=tuple(lid_rot), bevel=0.006)
for k, u in enumerate((-0.3, 0.3)): box(f"Chest_LidBand{k}", (0.04, CD + 0.03, 0.006), lp(u, -CD / 2, 0.043), M_IRON, rot=tuple(lid_rot))
# the burned B on the lid's top face: two stacked bowls and a stem, as scorched strokes
for nm, (x, y, w, h) in {"BStem": (-0.08, -CD / 2, 0.025, 0.2), "BTop": (-0.03, -CD / 2 - 0.05, 0.1, 0.022), "BMid": (-0.03, -CD / 2, 0.11, 0.022),
                         "BBot": (-0.03, -CD / 2 + 0.05 + 0.04, 0.12, 0.022), "BUpper": (0.02, -CD / 2 - 0.025, 0.025, 0.07), "BLower": (0.035, -CD / 2 + 0.045, 0.025, 0.09)}.items():
    yy = y if nm != "BBot" else -CD / 2 + 0.095
    box(f"Lid_{nm}", (w, h, 0.004), lp(x, yy, 0.0425 + 0.002), M_BRAND, rot=tuple(lid_rot))
# inside: the boat-cloak at the bottom, half drawn out over the front
cloak = Builder("BoatCloak", M_CLOAK)
cvs, cfs = [], []
for j in range(7):
    t = j / 6
    for i in range(10):
        u = i / 9
        x = (u - 0.5) * (CW - 0.12)
        if t < 0.5: yy = (0.5 - t) * (CD - 0.1); zz = 0.1 + 0.03 * math.sin(u * 9)
        else: yy = -CD / 2 - (t - 0.5) * 0.25; zz = CH - (t - 0.5) * 2 * (CH - 0.02) + 0.02 * math.sin(u * 7)
        if 0.45 < t < 0.6: zz = CH + 0.02; yy = -CD / 2 + 0.01
        cvs.append(Vector(cp(x, yy, zz)))
for j in range(6):
    for i in range(9):
        a = j * 10 + i; cfs.append([a, a + 1, a + 11, a + 10])
cloak.add(cvs, cfs); cloak.finish(smooth_=True)
# beside the chest on the boards: the folded suit, quadrant, canikin, tobacco, pistols, bar silver, watch, compasses, shells
def fl(x, y): return Vector((CHEST.x + x, CHEST.y + y, 0))
p = fl(-0.95, -0.15); box("Suit", (0.42, 0.34, 0.09), (p.x, p.y, 0.045), M_SUIT, rot=(0, 0, 0.15), bevel=0.02)
box("Suit2", (0.4, 0.3, 0.06), (p.x + 0.01, p.y + 0.01, 0.12), M_SUIT, rot=(0, 0, 0.2), bevel=0.02)
# the quadrant: a brass-bound wooden sector with an arc, lying flat
q = fl(0.85, -0.45)
qv = [Vector((q.x, q.y, 0.012))] + [Vector((q.x + 0.32 * math.cos(a), q.y + 0.32 * math.sin(a), 0.012)) for a in [math.radians(10 + 90 * t / 8) for t in range(9)]]
from_pydata("QuadrantFrame", qv, [[0, i, i + 1] for i in range(1, 9)], M_OAK)
for t in range(9):
    a = math.radians(10 + 90 * t / 8)
    if t in (0, 8): box(f"QuadArm{t}", (0.32, 0.02, 0.016), (q.x + 0.16 * math.cos(a), q.y + 0.16 * math.sin(a), 0.02), M_BRASS, rot=(0, 0, a))
lathe("Canikin", [(0, 0), (0.05, 0), (0.05, 0.1), (0.053, 0.11), (0, 0.11)], tuple(fl(0.7, -0.05)), M_TIN, steps=14)
for k in range(5): cyl(f"Tobacco{k}", 0.012, 0.18, tuple(fl(0.55 + k * 0.03, -0.8 + k * 0.01) + Vector((0, 0, 0.012))), M_TOBACCO, verts=6, rot=(0, math.pi / 2, 0.3 + k * 0.05))
def pistol(name, c, ang):
    Rp = Matrix.Rotation(ang, 3, 'Z')
    def pp(x, y, z): return tuple(c + Rp @ Vector((x, y, z)))
    cyl(f"{name}_Barrel", 0.011, 0.26, pp(0.13, 0, 0.022), M_BRASS, verts=8, rot=(0, math.pi / 2, ang))
    box(f"{name}_Stock", (0.22, 0.035, 0.03), pp(0.0, 0, 0.02), M_OAK, rot=(0, 0, ang), bevel=0.006)
    box(f"{name}_Butt", (0.1, 0.045, 0.05), pp(-0.13, 0.025, 0.025), M_OAK, rot=(0, 0, ang + 0.4), bevel=0.01)
    box(f"{name}_Lock", (0.06, 0.04, 0.015), pp(0.0, 0.0, 0.04), M_IRON, rot=(0, 0, ang))
for k, (x, y, a) in enumerate(((-0.55, -0.62, 0.3), (-0.4, -0.72, 0.25), (-0.75, -0.55, 2.9), (-0.2, -0.75, -0.2))):
    pistol(f"Pistol{k}", fl(x, y), a)
box("BarSilver", (0.16, 0.05, 0.035), tuple(fl(0.35, -0.55) + Vector((0, 0, 0.0175))), M_SILVER, rot=(0, 0, 0.6), bevel=0.008)
wp = fl(0.15, -0.68); cyl("SpanishWatch", 0.026, 0.012, (wp.x, wp.y, 0.006), M_GOLD, verts=16); cyl("WatchFace", 0.021, 0.002, (wp.x, wp.y, 0.013), M_WATCHFACE, verts=16)
cp0 = fl(0.6, -0.3)
for k, a in enumerate((0.2, 0.55)): box(f"Compass{k}", (0.15, 0.008, 0.008), (cp0.x + 0.07 * math.cos(a), cp0.y + 0.07 * math.sin(a), 0.006), M_BRASS, rot=(0, 0, a))
for k in range(6):
    sp_ = fl(0.95 + rb.uniform(-0.15, 0.15), 0.1 + rb.uniform(-0.2, 0.2))
    o = lathe(f"Shell{k}", [(0, 0), (0.03, 0.0), (0.025, 0.03), (0.012, 0.055), (0, 0.07)], (sp_.x, sp_.y, 0.02), M_SHELL, steps=10)
    o.rotation_euler = (math.pi / 2, 0, rb.uniform(0, 6.28))
# the oilcloth bundle, tied, on the cloak at the front edge; the canvas bag of coin, a few spilled
ob = fl(-0.05, -0.5); box("OilclothBundle", (0.22, 0.16, 0.06), (ob.x, ob.y, 0.03), M_OILCLOTH, rot=(0, 0, -0.2), bevel=0.02)
box("BundleTwine", (0.235, 0.008, 0.065), (ob.x, ob.y, 0.032), M_TWINE, rot=(0, 0, -0.2))
box("BundleTwine2", (0.008, 0.175, 0.065), (ob.x, ob.y, 0.032), M_TWINE, rot=(0, 0, -0.2))
bag = fl(-0.6, 0.0)
bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.14)
for v in bm.verts: v.co = Vector((v.co.x * 1.1, v.co.y * 0.9, max(v.co.z, -0.1) * 0.75 + 0.075 + 0.05 * max(0, v.co.z) * 2))
mesh_obj("CoinBag", bm, M_CANVAS, smooth_=True).location = (bag.x, bag.y, 0.0)
for k in range(9):
    c = bag + Vector((rb.uniform(0.1, 0.3), rb.uniform(-0.2, 0.05), 0))
    cyl(f"Coin{k}", 0.014, 0.003, (c.x, c.y, 0.002 + 0.003 * (k % 2)), M_GOLD if k % 3 else M_SILVER, verts=10, rot=(rb.uniform(-0.1, 0.1), 0, 0))
# the candle, left on the floor by the chest in an iron chamberstick
CN = fl(-0.05, -0.62) + Vector((0.55, 0.0, 0))
lathe("Chamberstick", [(0, 0), (0.07, 0), (0.07, 0.012), (0.015, 0.018), (0.014, 0.05), (0.025, 0.055), (0, 0.06)], (CN.x, CN.y, 0.0), M_IRON, steps=12)
cyl("FloorCandle", 0.013, 0.13, (CN.x, CN.y, 0.06 + 0.065), M_WAX, verts=8)
TIP = Vector((CN.x, CN.y, 0.205))
FLc = Builder("CandleFlame", M_FLAME)
for a in (0.0, math.pi / 2):
    d = Vector((math.cos(a), math.sin(a), 0)) * 0.006
    FLc.add([TIP - d, TIP + d, TIP + Vector((0, 0, 0.025)) + d * 0.6, TIP + Vector((0, 0, 0.042)), TIP + Vector((0, 0, 0.025)) - d * 0.6], [[0, 1, 2, 3, 4]])
FLc.finish(smooth_=False)

# ----------------------------------------------------------------------------- lights, world, living empties, anchors
light_obj("light.candle", 'POINT', 22.0, (1.0, 0.58, 0.28), tuple(TIP + Vector((0, 0, 0.03))), shadow_soft_size=0.02)
light_obj("light.moon", 'AREA', 26.0, (0.55, 0.68, 1.0), (WIN_X, Y1 + 0.3, (WIN_Z0 + WIN_Z1) / 2), direction=(0, -1, -0.35), size=WIN_W, shape='RECTANGLE', size_y=WIN_Z1 - WIN_Z0)
light_obj("light.landing", 'POINT', 8.0, (1.0, 0.6, 0.32), (DOOR_X - 0.3, Y0 - WT - 1.0, 0.4), shadow_soft_size=0.1)
world = bpy.data.worlds.new("Night"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.035, 0.05, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
living_empty("fx.candle.floor", tuple(TIP), 0.012)
living_empty("sound.clock.below", (0.0, -0.5, -0.5), 0.3)
living_empty("sound.wind.window", (WIN_X, Y1 + 0.3, 1.0), 0.3)

anchor("reader.entrance", (READER.x, READER.y, 0.0))
fwd = (LOOK_AT - READER); fwd.z = 0; fwd.normalize()
anchor("reader.look", tuple(READER + fwd + Vector((0, 0, EYE))))
anchor("scene.centre", tuple(CHEST)); anchor("room.chest", tuple(CHEST))
anchor("room.window", (WIN_X, Y1, WIN_Z0)); anchor("room.door", (DOOR_X, Y0, 0.0)); anchor("room.bed", (BX, 0.25, 0.0))

E = READER + Vector((0, 0, EYE))
page = box("PagePreview", (0.4, 0.004, 0.55), tuple(E + fwd * 0.6 - Vector((0, 0, 0.05))), plain("M_PagePreview", (0.80, 0.76, 0.66), rough=0.9), rot=(0, 0, math.atan2(fwd.y, fwd.x) - math.pi / 2))
K.apply_all_transforms()
def yawed(deg, dist=3.0, dz=-0.5):
    d = Matrix.Rotation(math.radians(deg), 3, 'Z') @ fwd
    return tuple(E + d * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(E), yawed(0, 3.0, -1.0), lens=17),
    camera("Cam_Page", tuple(E), yawed(0, 3.0, -1.0), lens=17),
    camera("Cam_Left", tuple(E), yawed(70, 3.0, -0.5), lens=17),
    camera("Cam_Right", tuple(E), yawed(-70, 3.0, -0.5), lens=17),
    camera("Cam_Behind", tuple(E), yawed(180, 3.0, -0.4), lens=17),
    camera("Cam_Chest", (CHEST.x - 0.2, CHEST.y - 1.25, 1.15), (CHEST.x, CHEST.y - 0.2, 0.15), lens=24),
]
if not args.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "benbow_captains_room_source.blend"))
K.budget()
if args.render:
    B.render_stamped(scene, cams, "benbow-captains-room", OUT, args.res, args.cams, page=page, page_cams={"Cam_Page"}, default_exposure=1.4,
                     captures_dir=CAPTURES)
if args.bake or args.export:
    T_ = min(args.tex, 2048)
    stats = K.bake_and_export(
        "benbow_captains_room",
        keep_names={"M_WindowCloth": "cloth.curtain.window", "M_FogNight": "far.fog"},
        size_for={"M_Boards": (T_, T_ // 4, T_), "M_RoughPlaster": (T_, 0, T_ // 2), "M_Rafters": (T_ // 2, T_ // 8, T_ // 2), "M_SeaChest": (T_ // 2, T_ // 8, T_ // 2),
                  "M_OakFurniture": (T_ // 4, 0, T_ // 4), "M_BoatCloak": (T_ // 4, 0, T_ // 4), "M_Bedding": (T_ // 4, 0, T_ // 8), "M_BlueCoat": (T_ // 4, 0, T_ // 8),
                  "M_Brass": (T_ // 8, 0, 0), "M_Iron": (T_ // 8, 0, T_ // 8)},
        keep_uv=set(), emit_only={"M_FogNight"}, remove=[page], default_div=16)
    print("STATS", stats)
print("DONE")
