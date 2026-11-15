"""
Fable: the Spy-glass tavern on the Bristol docks (Treasure Island, chapter 8, "At the Sign of the Spy-glass").

"It was a bright enough little place of entertainment. The sign was newly painted; the windows had neat red curtains;
the floor was cleanly sanded. There was a street on each side and an open door on both, which made the large, low
room pretty clear to see in, in spite of clouds of tobacco smoke."
"... a little tavern with a large brass telescope for a sign." "... along the quays ... the great multitude of ships
of all sizes and rigs and nations ... figureheads that had all been far over the ocean." (chapter 7)

The moment: a bright, fair morning before the day's customers. The large, low room: whitewashed walls, heavy oak
beams close overhead, the floor scrubbed and freshly sanded; rough elm tables and benches with the seamen's pewter
pots, a pipe and a pack of cards left from last night; the bar with its casks, bottles and pewter at the back; a small
fire in the side hearth; the windows on the quay with neat red curtains stirring in the air from the open doors. Through
the doors: the cobbled quay, bollards and a moored ship's bow with her figurehead, the harbour water, the forest of
masts beyond and the warehouses across the water; the side street through the west door. Outside the quay door hangs
the sign: a large brass telescope on an iron bracket. No people.

Living scene (docs/LIVING_SCENES.md): water.ocean.harbour (vertex colour G = foam where it slaps the quay wall and the
ships), cloth.curtain.window1/2/3 (R = billow weight, 0 at the rod), cloth.flag.ship (a pennant at the masthead),
fx.fire.tavern, fx.lantern.beam1/2 (unlit by day but trimmed: they flicker only if Unity lights them), sound.crowd.bar,
sound.gulls.quay, sound.rigging.ship, sound.fire.tavern.

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet on the sanded floor (z = 0)
  anchor.reader.look      eye height 1.55 m, 1 m ahead (north, the quay door ahead and to the right)
  anchor.scene.centre     the floor centre
  anchor.tavern.quayDoor, anchor.tavern.streetDoor, anchor.tavern.bar, anchor.tavern.sign, anchor.quay.ship
  light.sun (SUN, morning, low over the harbour), light.sky (SUN, shadowless fill), light.tavernFire (POINT)
  SkyDome, far.* (the far side of the harbour and the masts: backdrop), MESH_Glass (panes)
Register as Outdoor in FableBuild (the sun comes in through the doors and windows, as for ithaca-hall).

Axes: metres, Blender +Z up. Room x -5..5, y -3.5..3.5, 2.7 m to the beams' soffit. The quay door is in the +y wall, which
faces south-south-east over the harbour (the morning sun comes in through it); the street door in the -x wall, the bar
along the -y wall, the hearth in the +x wall.

Run headless (one Blender at a time):
  blender -b -P blender/build_spyglass_tavern.py -- --out out/spyglass-tavern --render --quick --res 640
  blender -b -P blender/build_spyglass_tavern.py -- --out out/spyglass-tavern --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, treasure_kit as K
importlib.reload(K)
from treasure_kit import F, smooth, lerp, fbm, new_mat, plain, noisy, box, cyl, mesh_obj, from_pydata, lathe, Builder, \
    anchor, living_empty, light_obj, camera, sharpen_by_angle

args = K.parse_args("out/spyglass-tavern")
OUT = args.out
scene, COLL = K.reset_scene("SpyglassTavern", args, bounces=8, diffuse=5, clamp=8.0)
random.seed(1759)

# ----------------------------------------------------------------------------- dimensions
X0, X1, Y0, Y1 = -5.0, 5.0, -3.5, 3.5
H = 2.95                                   # ceiling boards; the beams hang 0.25 below
WT = 0.6
EYE = 1.55
READER = Vector((-0.6, -1.2, 0.0))
LOOK_AT = Vector((-0.9, 3.5, 0.0))
QDOOR_X, QDOOR_W, QDOOR_H = 1.9, 1.3, 2.35       # the quay door (north wall)
SDOOR_Y, SDOOR_W = 0.4, 1.15                     # the street door (west wall)
WINS_N = (-2.6, 4.0)                             # windows on the quay
WIN_E = None
WIN_W, WIN_SILL, WIN_HEAD = 1.7, 0.8, 2.3
QUAY_Y = Y1 + WT + 7.5                           # the quay edge (the street is 7.5 m wide)
SL = -2.2                                        # harbour water level below the quay
# the quay side faces south-east across the harbour (+y is south-south-east here), so the morning sun comes in over
# the water, through the quay door and windows; the hearth is at the west end (+x)
_az, _el = math.radians(-38.0), math.radians(22.0)     # angle from +y towards -x, elevation
SUN_DIR = Vector((math.sin(_az) * math.cos(_el), math.cos(_az) * math.cos(_el), math.sin(_el))).normalized()

# ----------------------------------------------------------------------------- materials
def whitewash_mat(name):
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    n1, _ = g.noise(P, 1.5, 5)
    n2, _ = g.noise(P, 16.0, 3)
    col = g.ramp(n1 * 0.6 + n2 * 0.4, [(0.3, (0.56, 0.54, 0.49)), (0.7, (0.66, 0.64, 0.59))])
    smoke = g.ss(z, 1.9, 2.9)
    col = g.mul(col, g.mix(smoke * 0.5, (1, 1, 1), (0.72, 0.66, 0.55)))           # tobacco smoke yellows the top
    scuff = (1.0 - g.ss(z, 0.15, 0.6)) * g.ss(n2, 0.4, 0.7)
    col = g.mix(scuff * 0.5, col, (0.30, 0.26, 0.20))
    col = g.mul(col, g.ao(0.3), 0.6)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.92
    g.bump(b, n2 * 0.6 + n1 * 0.4, 0.4, 0.006)
    return m

def sanded_floor_mat(name):
    """Deal boards scrubbed pale and strewn with clean sand, thicker by the doors and swept into the corners."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    bw = 0.22
    row = (x / bw).floor()
    rh, _ = g.white(g.comb(row, 0.3, 0.0))
    L = 2.8 + rh * 1.5
    seg = ((y + rh * 5.0) / L).floor()
    bid, _ = g.white(g.comb(row, seg, 1.0))
    fu = (x / bw).fract(); fv = ((y + rh * 5.0) / L).fract()
    seam = (1.0 - g.ss(fu.min(1.0 - fu), 0.0, 0.03)).max(1.0 - g.ss(fv.min(1.0 - fv) * L, 0.0, 0.006))
    n1, _ = g.noise(g.comb(x * 6.0, y * 0.3 + bid * 9.0, z), 3.0, 5, 0.6, 1.0)
    col = g.ramp(n1, [(0.2, (0.26, 0.20, 0.13)), (0.5, (0.36, 0.29, 0.20)), (0.85, (0.44, 0.37, 0.27))])
    col = g.mul(col, g.comb(0.85 + bid * 0.3, 0.85 + bid * 0.28, 0.85 + bid * 0.25))
    col = g.mix(seam * 0.7, col, (0.10, 0.08, 0.05))
    sn, _ = g.noise(P, 1.2, 4)
    grains, _ = g.white(g.scale(P, 900.0))
    sand = g.ss(sn, 0.45, 0.7) * 0.55 + seam * 0.5
    col = g.mix(sand * g.ss(grains, 0.3, 0.9), col, (0.52, 0.45, 0.33))
    col = g.mul(col, g.ao(0.25), 0.6)
    g.set(b.inputs["Base Color"], col)
    g.set(b.inputs["Roughness"], 0.85 + sand * 0.1)
    g.bump(b, n1 * 0.3 - seam * 1.0 + grains * sand * 0.3, 0.35, 0.003)
    return m

def oak_mat(name, base=(0.09, 0.06, 0.035), dark=(0.03, 0.02, 0.012), light=(0.14, 0.10, 0.06), axis='X', rough=0.7, adze=True):
    """Old adzed oak, darkened by smoke."""
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

def red_cloth_mat(name):
    m, nt, b, g = new_mat(name)
    P = g.pos()
    n1, _ = g.noise(P, 4.0, 4)
    n2, _ = g.noise(P, 120.0, 2)
    col = g.ramp(n1 * 0.7 + n2 * 0.3, [(0.3, (0.24, 0.025, 0.02)), (0.7, (0.34, 0.045, 0.03))])
    col = g.mul(col, g.ao(0.1), 0.6)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.9
    b.inputs["Sheen Weight"].default_value = 0.4
    g.bump(b, n2, 0.2, 0.001)
    return m

def cobble_mat(name):
    """Pennant-stone setts of the quay, worn, with dung and straw in the joints; the quay edge of big granite blocks."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    br = g.n("ShaderNodeTexBrick", offset=0.5)
    g.set(br.inputs["Vector"], g.comb(x, y, 0.0))
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 0.22; br.inputs["Row Height"].default_value = 0.13
    br.inputs["Mortar Size"].default_value = 0.012; br.inputs["Mortar Smooth"].default_value = 0.6
    br.inputs["Color1"].default_value = (0.8, 0.8, 0.8, 1); br.inputs["Color2"].default_value = (1.15, 1.1, 1.05, 1)
    br.inputs["Mortar"].default_value = (0.25, 0.22, 0.18, 1)
    n1, _ = g.noise(P, 2.0, 5)
    n2, _ = g.noise(P, 25.0, 3)
    col = g.mul(g.ramp(n1 * 0.6 + n2 * 0.4, [(0.3, (0.13, 0.12, 0.11)), (0.6, (0.19, 0.18, 0.16)), (0.85, (0.24, 0.22, 0.19))]), br.outputs["Color"])
    dirt = g.ss(n1, 0.55, 0.75) * 0.5
    col = g.mix(dirt, col, (0.11, 0.08, 0.05))
    col = g.mul(col, g.ao(0.2), 0.6)
    g.set(b.inputs["Base Color"], col)
    g.set(b.inputs["Roughness"], 0.75 + n2 * 0.2)
    g.bump(b, F(g, br.outputs["Fac"]) * -1.0 + n2 * 0.3, 0.8, 0.02)
    return m

def brick_mat(name, far=False):
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    br = g.n("ShaderNodeTexBrick", offset=0.5)
    g.set(br.inputs["Vector"], g.comb(x + y, z, 0.0))
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 0.23; br.inputs["Row Height"].default_value = 0.075
    br.inputs["Mortar Size"].default_value = 0.01
    br.inputs["Color1"].default_value = (0.25, 0.10, 0.06, 1); br.inputs["Color2"].default_value = (0.33, 0.15, 0.09, 1)
    br.inputs["Mortar"].default_value = (0.35, 0.32, 0.27, 1)
    n1, _ = g.noise(P, 1.0, 4)
    col = g.mul(br.outputs["Color"], g.ramp(n1, [(0.3, (0.8, 0.8, 0.8)), (0.7, (1.1, 1.05, 1.0))]))
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.9
    g.bump(b, F(g, br.outputs["Fac"]) * -1.0, 0.5, 0.01)
    return m

def hull_mat(name):
    """A merchantman's side: tarred black wales and ochre-yellow strakes between, paint weathered, weed at the
    waterline."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    n1, _ = g.noise(P, 2.0, 5)
    n2, _ = g.noise(g.stretch(P, 0.2, 1.0, 1.0), 20.0, 3)
    band = g.ss(z, SL + 2.2, SL + 2.25) * (1.0 - g.ss(z, SL + 3.0, SL + 3.05))
    band2 = g.ss(z, SL + 4.4, SL + 4.45) * (1.0 - g.ss(z, SL + 4.9, SL + 4.95))
    col = g.ramp(n1, [(0.3, (0.025, 0.022, 0.02)), (0.7, (0.05, 0.045, 0.04))])
    col = g.mix(band.max(band2), col, g.ramp(n1, [(0.3, (0.32, 0.22, 0.07)), (0.7, (0.42, 0.30, 0.10))]))
    plank = ((z * (2 * math.pi / 0.22)).sin() * 0.5 + 0.5)
    col = g.mul(col, g.ramp(plank, [(0.0, (0.75, 0.75, 0.75)), (0.15, (1, 1, 1))]))
    weed = 1.0 - g.ss(z, SL + 0.15, SL + 0.45 + n2 * 0.1)
    col = g.mix(weed, col, (0.04, 0.05, 0.02))
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.6
    g.bump(b, plank * 0.6 + n2 * 0.3, 0.4, 0.01)
    return m

def harbour_mat(name):
    m, nt, b, g = new_mat(name)
    P = g.pos()
    wt = g.attr("Color"); _, foam, _ = g.sep(wt.outputs["Color"])
    n1, _ = g.noise(g.stretch(P, 1.0, 0.4, 1.0), 1.2, 4)
    n2, _ = g.noise(P, 8.0, 3)
    col = g.mix(foam * g.ss(n2, 0.45, 0.6) * 0.7, (0.03, 0.04, 0.035), (0.40, 0.40, 0.37))
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.08
    b.inputs["IOR"].default_value = 1.33
    g.bump(b, n1 * 0.7 + n2 * 0.3, 0.3, 0.05)
    return m

def day_sky_mat(name="M_SkyDome"):
    """A bright fair morning over Bristol: clear blue with fair-weather cumulus, a little coal-smoke haze low down."""
    m, nt, b, g = new_mat(name)
    nv = g.n("ShaderNodeVectorMath", operation='NORMALIZE'); g.set(nv.inputs[0], g.pos())
    d = nv.outputs[0]; dx, dy, el = g.sep(d)
    col = g.ramp(g.ss(el, -0.02, 0.9), [(0.0, (0.62, 0.62, 0.60)), (0.06, (0.55, 0.62, 0.72)), (0.3, (0.30, 0.45, 0.72)), (1.0, (0.16, 0.30, 0.62))])
    sd = g.n("ShaderNodeVectorMath", operation='DOT_PRODUCT'); g.set(sd.inputs[0], d); sd.inputs[1].default_value = tuple(SUN_DIR)
    sdot = F(g, sd.outputs["Value"])
    col = g.mix(g.ss(sdot, 0.7, 1.0).pow(2.0) * 0.6, col, (1.2, 1.1, 0.95))
    zk = el.max(0.0) + 0.1
    px, py = dx / zk, dy / zk
    c1, _ = g.noise(g.comb(px * 0.5, py * 0.5, 2.0), 1.0, 6, 0.55, 0.2)
    cover = g.ss(c1, 0.58, 0.68) * g.ss(el, 0.02, 0.1)
    shade = g.ss(c1, 0.6, 0.8)
    ccol = g.mix(shade, (0.62, 0.64, 0.68), (1.05, 1.03, 1.0))
    col = g.mix(cover, col, ccol)
    col = g.mix(1.0 - g.ss(el, -0.01, 0.0), col, (0.3, 0.32, 0.33))
    g.set(b.inputs["Emission Color"], col); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0
    return m

M_WALL = whitewash_mat("M_Whitewash")
M_FLOOR = sanded_floor_mat("M_SandedFloor")
M_BEAM = oak_mat("M_Beams")
M_CEILB = oak_mat("M_CeilingBoards", base=(0.12, 0.09, 0.06), light=(0.17, 0.13, 0.085), adze=False)
M_TABLE = oak_mat("M_ElmTables", base=(0.22, 0.16, 0.10), dark=(0.10, 0.07, 0.04), light=(0.30, 0.23, 0.15), rough=0.75)
M_BAR = oak_mat("M_BarWood", base=(0.10, 0.065, 0.035), light=(0.17, 0.11, 0.06), axis='Z', rough=0.5)
M_CASK = oak_mat("M_Casks", base=(0.17, 0.11, 0.06), light=(0.25, 0.17, 0.10), axis='Z', rough=0.7, adze=False)
M_IRON = noisy("M_Iron", [(0.02, 0.02, 0.02), (0.05, 0.045, 0.04), (0.10, 0.06, 0.035)], scale=20, rough=0.6, metallic=0.6, bump=0.3)
M_PEWTER = noisy("M_Pewter", [(0.30, 0.30, 0.29), (0.42, 0.42, 0.40), (0.50, 0.50, 0.48)], scale=8, rough=0.35, metallic=0.9, bump=0.1)
M_BRASS = noisy("M_Brass", [(0.40, 0.27, 0.08), (0.55, 0.40, 0.14), (0.66, 0.50, 0.22)], scale=10, rough=0.25, metallic=1.0, bump=0.05)
M_BOTTLE = plain("M_BottleGlass", (0.04, 0.12, 0.06), rough=0.08, transmission=0.6)
M_GLASS = plain("M_Glass", (0.6, 0.65, 0.65), rough=0.05, alpha=0.12)
M_CURTAIN = red_cloth_mat("M_RedCurtain")
M_STONE = noisy("M_HearthStone", [(0.20, 0.19, 0.17), (0.28, 0.27, 0.24), (0.34, 0.32, 0.29)], scale=3, rough=0.85, bump=0.5, bump_dist=0.01)
M_SOOT = noisy("M_Soot", [(0.012, 0.011, 0.01), (0.03, 0.027, 0.024)], scale=6, rough=0.95)
M_LOGS = noisy("M_Logs", [(0.03, 0.02, 0.012), (0.08, 0.055, 0.035)], scale=14, rough=0.9, stretch=(0.2, 1, 1), bump=0.6)
M_EMBERS = plain("M_Embers", (0.05, 0.02, 0.01), rough=0.9, emission=(1.0, 0.30, 0.06), strength=5.0)
M_FLAME = plain("M_Flame", (0.0, 0.0, 0.0), rough=1.0, emission=(1.0, 0.55, 0.2), strength=10.0)
M_STONEWARE = noisy("M_Stoneware", [(0.32, 0.26, 0.17), (0.42, 0.35, 0.24)], scale=8, rough=0.3, coat=0.5, bump=0.05)
M_CLAY = noisy("M_ClayPipe", [(0.55, 0.52, 0.46), (0.62, 0.60, 0.54)], scale=20, rough=0.6, bump=0.05)
M_CARDS = noisy("M_Cards", [(0.55, 0.52, 0.45), (0.60, 0.57, 0.50)], scale=30, rough=0.5, bump=0.0)
M_ROPE = noisy("M_Rope", [(0.16, 0.12, 0.07), (0.24, 0.19, 0.12)], scale=60, rough=0.9, stretch=(1, 1, 8), bump=0.6)
M_COBBLE = cobble_mat("M_Quay")
M_QUAYWALL = noisy("M_QuayWall", [(0.12, 0.11, 0.09), (0.20, 0.18, 0.15), (0.27, 0.25, 0.21)], scale=1.5, rough=0.85, bump=0.6, bump_dist=0.02)
M_BRICK = brick_mat("M_Brick")
M_HULL = hull_mat("M_Hull")
M_SPAR = oak_mat("M_Spars", base=(0.20, 0.14, 0.08), light=(0.28, 0.20, 0.12), axis='Z', rough=0.6, adze=False)
M_RIG = plain("M_Rigging", (0.025, 0.02, 0.015), rough=0.8)
M_SAIL = noisy("M_FurledSail", [(0.38, 0.35, 0.28), (0.48, 0.45, 0.37)], scale=6, rough=0.9, bump=0.4)
M_FIG = noisy("M_Figurehead", [(0.45, 0.38, 0.22), (0.58, 0.50, 0.30), (0.20, 0.25, 0.40)], scale=4, rough=0.45, coat=0.3, bump=0.2)
M_FLAG = plain("M_Pennant", (0.35, 0.03, 0.025), rough=0.8)
M_WATER = harbour_mat("M_Harbour")
M_FARB = brick_mat("M_FarWarehouses", far=True)
M_FARMAST = plain("M_FarMasts", (0.10, 0.08, 0.06), rough=0.8)
M_SIGNP = noisy("M_SignPaint", [(0.02, 0.06, 0.04), (0.03, 0.08, 0.05)], scale=4, rough=0.35, coat=0.6, bump=0.0)
M_SKY = day_sky_mat()
M_FARWIN = plain("M_FarWindow", (0.02, 0.02, 0.025), rough=0.2)
M_DECK = oak_mat("M_Deck", base=(0.22, 0.18, 0.12), dark=(0.12, 0.09, 0.06), light=(0.30, 0.25, 0.17), adze=False)

# ----------------------------------------------------------------------------- the room shell
box("Floor", (X1 - X0 + 2 * WT, Y1 - Y0 + 2 * WT, 0.1), (0, 0, -0.05), M_FLOOR)
box("Ceiling", (X1 - X0, Y1 - Y0, 0.06), (0, 0, H + 0.03), M_CEILB)
def wall_y(name, y, x0, x1, openings, mat, sy):
    xs = [x0]
    for (xc, w, z0, z1) in sorted(openings): xs += [xc - w / 2, xc + w / 2]
    xs.append(x1)
    yc = y + sy * WT / 2
    for i in range(0, len(xs), 2):
        if xs[i + 1] - xs[i] > 0.001: box(f"{name}_pier{i}", (xs[i + 1] - xs[i], WT, H), ((xs[i] + xs[i + 1]) / 2, yc, H / 2), mat)
    for (xc, w, z0, z1) in openings:
        if z0 > 0.001: box(f"{name}_below{xc}", (w, WT, z0), (xc, yc, z0 / 2), mat)
        box(f"{name}_above{xc}", (w, WT, H - z1), (xc, yc, (H + z1) / 2), mat)
def wall_x(name, x, y0, y1, openings, mat, sx):
    ys_ = [y0]
    for (yc, w, z0, z1) in sorted(openings): ys_ += [yc - w / 2, yc + w / 2]
    ys_.append(y1)
    xc = x + sx * WT / 2
    for i in range(0, len(ys_), 2):
        if ys_[i + 1] - ys_[i] > 0.001: box(f"{name}_pier{i}", (WT, ys_[i + 1] - ys_[i], H), (xc, (ys_[i] + ys_[i + 1]) / 2, H / 2), mat)
    for (yc, w, z0, z1) in openings:
        if z0 > 0.001: box(f"{name}_below{yc}", (WT, w, z0), (xc, yc, z0 / 2), mat)
        box(f"{name}_above{yc}", (WT, w, H - z1), (xc, yc, (H + z1) / 2), mat)
wall_y("WallN", Y1, X0 - WT, X1 + WT, [(QDOOR_X, QDOOR_W, 0.0, QDOOR_H)] + [(wx, WIN_W, WIN_SILL, WIN_HEAD) for wx in WINS_N], M_WALL, 1)
wall_y("WallS", Y0, X0 - WT, X1 + WT, [], M_WALL, -1)
wall_x("WallW", X0, Y0, Y1, [(SDOOR_Y, SDOOR_W, 0.0, QDOOR_H), (-2.0, WIN_W, WIN_SILL, WIN_HEAD)], M_WALL, -1)
wall_x("WallE", X1, Y0, Y1, [], M_WALL, 1)
# beams: two big summer beams east-west and joists across
for by in (-1.2, 1.3):
    box(f"Beam{by}", (X1 - X0, 0.30, 0.30), (0, by, H - 0.15), M_BEAM, bevel=0.02)
for k in range(13):
    x = X0 + 0.4 + k * (X1 - X0 - 0.8) / 12
    box(f"Joist{k}", (0.14, Y1 - Y0, 0.14), (x, 0, H - 0.07), M_BEAM, bevel=0.01)
for (nm, size, loc) in [("PostA", (0.25, 0.25, H), (-1.6, -1.2, H / 2)), ("PostB", (0.25, 0.25, H), (1.8, 1.3, H / 2))]:
    box(nm, size, loc, M_BEAM, bevel=0.02)
# door frames, the open doors, window frames and panes, sills
def door(name, cx, cy, w, axis, open_dir):
    if axis == 'y':
        for s in (-1, 1): box(f"{name}_Jamb{s}", (0.12, WT + 0.04, QDOOR_H), (cx + s * (w / 2 + 0.06), cy, QDOOR_H / 2), M_BEAM)
        box(f"{name}_Head", (w + 0.36, WT + 0.04, 0.16), (cx, cy, QDOOR_H + 0.08), M_BEAM)
        hinge = Vector((cx - w / 2 + 0.03, cy - WT / 2 + 0.05, 0))
        d = Vector((-0.2, -1.0, 0)).normalized()
    else:
        for s in (-1, 1): box(f"{name}_Jamb{s}", (WT + 0.04, 0.12, QDOOR_H), (cx, cy + s * (w / 2 + 0.06), QDOOR_H / 2), M_BEAM)
        box(f"{name}_Head", (WT + 0.04, w + 0.36, 0.16), (cx, cy, QDOOR_H + 0.08), M_BEAM)
        hinge = Vector((cx + WT / 2 - 0.05, cy - w / 2 + 0.03, 0))
        d = Vector((1.0, -0.15, 0)).normalized()
    ang = math.atan2(d.y, d.x)
    box(f"{name}_Leaf", (w - 0.04, 0.05, QDOOR_H - 0.03), tuple(hinge + d * (w - 0.04) / 2 + Vector((0, 0, QDOOR_H / 2))), M_BAR, rot=(0, 0, ang))
    for k in range(3):
        box(f"{name}_Ledge{k}", (w - 0.1, 0.03, 0.14), tuple(hinge + d * (w - 0.04) / 2 + Vector((0, 0, 0.3 + k * 0.85)) + Vector((-d.y, d.x, 0)) * 0.04 * (1 if axis == 'y' else -1)), M_BAR, rot=(0, 0, ang))
door("QuayDoor", QDOOR_X, Y1 + WT / 2, QDOOR_W, 'y', 1)
door("StreetDoor", X0 - WT / 2, SDOOR_Y, SDOOR_W, 'x', 1)
CURTAINS = []
def window(name, cx, cy, axis):
    U = Vector((1, 0, 0)) if axis == 'y' else Vector((0, 1, 0))
    Nin = Vector((0, -1, 0)) if axis == 'y' else Vector((1, 0, 0))
    plane = Vector((cx, cy, 0)) - Nin * 0.0
    zc = (WIN_SILL + WIN_HEAD) / 2
    box(f"{name}_Glass", (WIN_W * abs(U.x) + 0.005 * abs(U.y), WIN_W * abs(U.y) + 0.005 * abs(U.x), WIN_HEAD - WIN_SILL), tuple(plane + Vector((0, 0, zc))), M_GLASS)
    for k in range(5):
        t = -WIN_W / 2 + k * WIN_W / 4
        p = plane + U * t + Vector((0, 0, zc)) + Nin * 0.01
        box(f"{name}_V{k}", (abs(U.x) * 0.035 + abs(U.y) * 0.04, abs(U.y) * 0.035 + abs(U.x) * 0.04, WIN_HEAD - WIN_SILL), tuple(p), M_BEAM)
    for k in range(5):
        p = plane + Vector((0, 0, WIN_SILL + k * (WIN_HEAD - WIN_SILL) / 4)) + Nin * 0.01
        box(f"{name}_H{k}", (abs(U.x) * WIN_W + abs(U.y) * 0.04, abs(U.y) * WIN_W + abs(U.x) * 0.04, 0.03), tuple(p), M_BEAM)
    p = plane + Nin * (WT / 2) + Vector((0, 0, WIN_SILL - 0.03))
    box(f"{name}_Sill", (abs(U.x) * (WIN_W + 0.2) + abs(U.y) * 0.18, abs(U.y) * (WIN_W + 0.2) + abs(U.x) * 0.18, 0.06), tuple(p), M_BEAM)
    # the neat red curtains: a half-curtain on a brass rod across the lower panes, two side curtains tied back
    rod = plane + Nin * (WT / 2 + 0.05)
    cyl(f"{name}_Rod", 0.012, WIN_W + 0.3, tuple(rod + Vector((0, 0, WIN_SILL + 0.62))), M_BRASS, verts=8, rot=(0, math.pi / 2, 0) if axis == 'y' else (math.pi / 2, 0, 0))
    cyl(f"{name}_Rod2", 0.012, WIN_W + 0.6, tuple(rod + Vector((0, 0, WIN_HEAD + 0.1))), M_BRASS, verts=8, rot=(0, math.pi / 2, 0) if axis == 'y' else (math.pi / 2, 0, 0))
    C = Builder(f"cloth.curtain.{name}", M_CURTAIN, living=True)
    def drape(u0, u1, z0, z1, folds, depth, gather_bottom=1.0, out=0.0):
        n = folds * 4
        vs, ws, fs = [], [], []
        rows = 6
        for j in range(rows + 1):
            tz = j / rows; zz = z1 - (z1 - z0) * tz
            g_ = lerp(1.0, gather_bottom, tz)
            for i in range(n + 1):
                t = i / n
                uu = lerp(u0, u1, 0.5) + (lerp(u0, u1, t) - lerp(u0, u1, 0.5)) * g_
                wv = depth * math.sin(t * folds * 2 * math.pi) * (0.6 + 0.4 * tz)
                vs.append(rod + U * uu + Nin * (wv + out * tz) + Vector((0, 0, zz))); ws.append((tz ** 1.2, 0.0, 0.0, 1.0))
        for j in range(rows):
            for i in range(n):
                a = j * (n + 1) + i; fs.append([a, a + 1, a + n + 2, a + n + 1])
        C.add(vs, fs, (1, 1, 1, 1), ws)
    drape(-WIN_W / 2 - 0.05, WIN_W / 2 + 0.05, WIN_SILL + 0.02, WIN_SILL + 0.62, 7, 0.025)
    for s in (-1, 1):
        drape(s * (WIN_W / 2 + 0.28) - 0.15, s * (WIN_W / 2 + 0.28) + 0.15, WIN_SILL - 0.1, WIN_HEAD + 0.1, 3, 0.04, gather_bottom=0.55, out=0.02)
    o = C.finish(smooth_=True)
    CURTAINS.append(o)
for i, wx in enumerate(WINS_N): window(f"window{i + 1}", wx, Y1 + WT / 2, 'y')
window("window3", X0 - WT / 2, -2.0, 'x')

# ----------------------------------------------------------------------------- the bar along the south wall: counter, casks, shelves
box("Bar_Counter", (4.6, 0.6, 1.05), (0.9, Y0 + 1.25, 0.525), M_BAR, bevel=0.01)
box("Bar_Top", (4.75, 0.7, 0.05), (0.9, Y0 + 1.25, 1.075), M_BAR, bevel=0.01)
for k in range(9): box(f"Bar_Panel{k}", (0.42, 0.02, 0.7), (-1.15 + k * 0.51, Y0 + 1.56, 0.5), M_BAR, bevel=0.01)
for k in range(3):
    box(f"Shelf{k}", (4.2, 0.28, 0.035), (0.9, Y0 + 0.16, 1.45 + k * 0.42), M_BAR)
def cask(name, x, y, z, r=0.30, L=0.75, axis='x'):
    prof = [(r * 0.86, -L / 2), (r * 0.95, -L / 4), (r, 0.0), (r * 0.95, L / 4), (r * 0.86, L / 2)]
    pr = [(0.0, -L / 2)] + prof + [(0.0, L / 2)]
    o = lathe(name, [(rr, zz) for rr, zz in pr], (x, y, z), M_CASK, steps=14,
              rot=(0, math.pi / 2, 0) if axis == 'x' else (math.pi / 2, 0, 0))
    for zz in (-L * 0.38, -L * 0.2, L * 0.2, L * 0.38):
        rr = r * (0.9 + 0.1 * (1 - abs(zz) / (L / 2)))
        t = lathe(name + f"_hoop{zz}", [(0, -0.02), (rr + 0.006, -0.02), (rr + 0.006, 0.02), (0, 0.02)], (x, y, z), M_IRON, steps=14,
                  rot=(0, math.pi / 2, 0) if axis == 'x' else (math.pi / 2, 0, 0))
        t.location = Vector((x, y, z)) + (Vector((zz, 0, 0)) if axis == 'x' else Vector((0, -zz, 0)))
    return o
for k, x in enumerate((-1.0, -0.2, 0.6)):          # casks on the stillage behind the bar, ends to the room
    box(f"Stillage{k}", (0.7, 0.8, 0.12), (x, Y0 + 0.5, 0.95), M_BAR)
    cask(f"Cask{k}", x, Y0 + 0.5, 1.33, axis='y')
    cyl(f"Tap{k}", 0.015, 0.12, (x, Y0 + 0.9 + 0.06, 1.2), M_BRASS, verts=8, rot=(math.pi / 2, 0, 0))
cask("CaskFloor1", -4.2, Y0 + 0.5, 0.32, axis='x')
cask("CaskFloor2", -4.35, Y0 + 1.15, 0.30, axis='x', r=0.27)
lathe("CaskStand", [(0, 0), (0.3, 0), (0.3, 0.75), (0, 0.75)], (4.3, -2.9, 0.0), M_CASK, steps=14)
rb = random.Random(4)
for k in range(3):                                   # pewter and bottles on the shelves
    z = 1.45 + k * 0.42 + 0.02
    x = -1.1
    while x < 3.0:
        if rb.random() < 0.5:
            hh = rb.uniform(0.22, 0.30)
            lathe(f"Bottle{k}{x:.2f}", [(0, 0), (0.04, 0), (0.042, hh * 0.6), (0.016, hh * 0.78), (0.014, hh), (0, hh)], (x, Y0 + 0.16, z), M_BOTTLE, steps=7)
            x += 0.11
        else:
            lathe(f"Pot{k}{x:.2f}", [(0, 0), (0.045, 0), (0.05, 0.03), (0.042, 0.10), (0.05, 0.14), (0, 0.14)], (x, Y0 + 0.16, z), M_PEWTER, steps=7)
            x += 0.13
        x += rb.uniform(0.0, 0.06)
for k in range(6):
    lathe(f"BarPot{k}", [(0, 0), (0.045, 0), (0.05, 0.03), (0.042, 0.10), (0.05, 0.14), (0, 0.14)], (-0.9 + k * 0.17 + rb.uniform(-0.03, 0.03), Y0 + 1.15, 1.10), M_PEWTER, steps=10)

# ----------------------------------------------------------------------------- tables, benches, stools, the seamen's leavings
def table(name, cx, cy, L=1.9, D=0.75, yaw=0.0):
    R = Matrix.Rotation(yaw, 3, 'Z'); c = Vector((cx, cy, 0))
    box(f"{name}_Top", (L, D, 0.06), tuple(c + Vector((0, 0, 0.74))), M_TABLE, rot=(0, 0, yaw), bevel=0.008)
    for s in (-1, 1):
        box(f"{name}_Trestle{s}", (0.08, D * 0.8, 0.70), tuple(c + R @ Vector((s * (L / 2 - 0.25), 0, 0.36))), M_TABLE, rot=(0, 0, yaw))
        box(f"{name}_Foot{s}", (0.10, D * 0.9, 0.08), tuple(c + R @ Vector((s * (L / 2 - 0.25), 0, 0.04))), M_TABLE, rot=(0, 0, yaw))
    box(f"{name}_Stretcher", (L - 0.5, 0.06, 0.08), tuple(c + Vector((0, 0, 0.22))), M_TABLE, rot=(0, 0, yaw))
    for s in (-1, 1):   # benches either side
        bc = c + R @ Vector((0, s * (D / 2 + 0.3), 0))
        box(f"{name}_Bench{s}", (L - 0.1, 0.28, 0.05), tuple(bc + Vector((0, 0, 0.45))), M_TABLE, rot=(0, 0, yaw + rb.uniform(-0.03, 0.03)), bevel=0.005)
        for e in (-1, 1):
            box(f"{name}_BenchLeg{s}{e}", (0.06, 0.24, 0.43), tuple(bc + R @ Vector((e * (L / 2 - 0.25), 0, 0.215))), M_TABLE, rot=(0, 0, yaw))
    return c
TABLES = [table("TableA", -2.6, 1.6, yaw=0.02), table("TableB", 1.6, -0.15, yaw=-0.03), table("TableC", -2.9, -1.2, L=1.6, yaw=0.05), table("TableD", 3.6, 1.9, L=1.5, yaw=1.57)]
def tankard(name, x, y, z, mat=M_PEWTER, tip=False):
    o = lathe(name, [(0, 0), (0.048, 0), (0.05, 0.02), (0.044, 0.11), (0.05, 0.13), (0, 0.13)], (x, y, z), mat, steps=10,
              rot=(math.pi / 2, 0, rb.uniform(0, 6.28)) if tip else (0, 0, 0))
    if not tip:
        bpy.ops.mesh.primitive_torus_add(major_radius=0.035, minor_radius=0.007, major_segments=10, minor_segments=4, location=(x + 0.06, y, z + 0.07), rotation=(math.pi / 2, 0, 0))
        K._finish(bpy.context.active_object, mat, smooth_=True)
for (x, y) in ((-2.9, 1.75), (-2.3, 1.45), (-2.05, 1.8), (1.2, -0.05), (2.0, -0.3), (-3.1, -1.1), (3.5, 2.3)):
    tankard(f"Tankard{x}{y}", x, y, 0.77)
tankard("TankardTipped", 1.75, 0.1, 0.80, tip=True)
for (x, y, a) in ((-2.5, 1.35, 0.4), (1.4, -0.32, -0.8)):
    cyl(f"Pipe{x}", 0.004, 0.30, (x, y, 0.775), M_CLAY, verts=5, rot=(0, math.pi / 2, a))
box("Cards", (0.09, 0.06, 0.012), (-2.75, 1.55, 0.776), M_CARDS, rot=(0, 0, 0.3))
for k in range(5): box(f"Card{k}", (0.09, 0.06, 0.002), (-2.55 + k * 0.05, 1.6 + rb.uniform(-0.05, 0.05), 0.772), M_CARDS, rot=(0, 0, rb.uniform(-1, 1)))
lathe("Jug", [(0, 0), (0.07, 0), (0.1, 0.1), (0.09, 0.2), (0.05, 0.25), (0.06, 0.28), (0, 0.28)], (1.9, 0.1, 0.77), M_STONEWARE, steps=12)
for k, (x, y) in enumerate(((0.2, 1.9), (-0.6, 2.4), (4.2, -1.3))):  # stools
    cyl(f"Stool{k}", 0.17, 0.05, (x, y, 0.47), M_TABLE, verts=12)
    for e in range(3):
        a = 2 * math.pi * e / 3
        cyl(f"StoolLeg{k}{e}", 0.02, 0.48, (x + math.cos(a) * 0.11, y + math.sin(a) * 0.11, 0.23), M_TABLE, verts=6, rot=(math.sin(a) * 0.15, -math.cos(a) * 0.15, 0))
# a sea chest and a coil of rope by the street door, a tarred hat on a peg
box("SeaChest", (0.9, 0.48, 0.45), (-4.3, 2.6, 0.225), M_BAR, bevel=0.02)
box("SeaChestLid", (0.92, 0.5, 0.06), (-4.3, 2.6, 0.47), M_BAR, bevel=0.02)
for s in (-1, 1): box(f"SeaChestBecket{s}", (0.03, 0.16, 0.05), (-4.3 + s * 0.47, 2.6, 0.32), M_ROPE)
for k in range(5):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.24 - k * 0.012, minor_radius=0.022, major_segments=18, minor_segments=5, location=(-3.95, 3.0, 0.024 + k * 0.042))
    K._finish(bpy.context.active_object, M_ROPE, smooth_=True)
for k in range(4): box(f"Peg{k}", (0.03, 0.12, 0.03), (-4.98, -0.9 - k * 0.35, 1.75), M_BEAM)
lathe("Hat", [(0, 0), (0.18, 0), (0.18, 0.012), (0.09, 0.02), (0.085, 0.12), (0, 0.13)], (-4.9, -1.25, 1.62), M_SOOT, steps=12, rot=(0, math.pi / 2 - 0.3, 0))

# ----------------------------------------------------------------------------- the hearth in the east wall, lanterns on the beams, a print of a ship
box("Hearth_Back", (0.05, 1.3, 1.1), (X1 - 0.02, 0.6, 0.55), M_SOOT)
for s in (-1, 1): box(f"Hearth_Jamb{s}", (0.35, 0.3, 1.25), (X1 - 0.15, 0.6 + s * 0.8, 0.625), M_STONE, bevel=0.02)
box("Hearth_Lintel", (0.4, 1.9, 0.3), (X1 - 0.17, 0.6, 1.4), M_BEAM, bevel=0.02)
box("Hearth_Shelf", (0.3, 2.1, 0.06), (X1 - 0.15, 0.6, 1.58), M_BEAM)
box("Hearth_Stone", (0.7, 1.9, 0.04), (X1 - 0.35, 0.6, 0.02), M_STONE)
for k, (a, z) in enumerate(((0.2, 0.09), (-0.25, 0.12), (0.05, 0.17))):
    cyl(f"Log{k}", 0.05, 0.55, (X1 - 0.3, 0.6 + k * 0.02, z), M_LOGS, verts=8, rot=(math.pi / 2, 0, a))
box("Embers", (0.35, 0.6, 0.04), (X1 - 0.3, 0.6, 0.06), M_EMBERS)
FL = Builder("Flames", M_FLAME)
rl = random.Random(2)
for k in range(5):
    cx_, cy_ = X1 - 0.3 + rl.uniform(-0.06, 0.06), 0.6 + rl.uniform(-0.2, 0.2); hh = rl.uniform(0.15, 0.28); ww = rl.uniform(0.06, 0.1)
    for a in (0.0, math.pi / 2):
        d = Vector((math.cos(a), math.sin(a), 0)) * ww; z0 = 0.12
        FL.add([Vector((cx_, cy_, z0)) - d, Vector((cx_, cy_, z0)) + d, Vector((cx_, cy_, z0 + hh * 0.45)) + d * 0.8, Vector((cx_, cy_, z0 + hh)), Vector((cx_, cy_, z0 + hh * 0.45)) - d * 0.8], [[0, 1, 2, 3, 4]])
FL.finish(smooth_=False)
for k in range(4): lathe(f"Plate{k}", [(0, 0), (0.12, 0), (0.13, 0.02), (0, 0.02)], (X1 - 0.12, -0.1 + k * 0.45, 1.61), M_PEWTER, steps=14, rot=(0, -1.35, 0))
LANTERNS = []
for k, (x, y) in enumerate(((-1.6, -1.2), (1.0, 1.3))):
    z = H - 0.3 - 0.45
    cyl(f"LanternHook{k}", 0.006, 0.3, (x, y, H - 0.45), M_IRON, verts=5)
    box(f"Lantern{k}", (0.16, 0.16, 0.26), (x, y, z), M_IRON)
    box(f"LanternGlass{k}", (0.17, 0.17, 0.18), (x, y, z), M_GLASS)
    lathe(f"LanternTop{k}", [(0, 0), (0.11, 0), (0.0, 0.1)], (x, y, z + 0.13), M_IRON, steps=8)
    LANTERNS.append(Vector((x, y, z)))
box("Print", (0.7, 0.02, 0.5), (-0.9, Y1 - 0.01, 1.75), noisy("M_PrintPaper", [(0.40, 0.37, 0.30), (0.10, 0.09, 0.08), (0.45, 0.42, 0.35)], scale=14, rough=0.6, bump=0.0))
box("PrintFrame", (0.78, 0.025, 0.58), (-0.9, Y1 - 0.005, 1.75), M_BEAM)

# ----------------------------------------------------------------------------- outside: the quay, the ship at the quay, the harbour, masts, warehouses
QY0 = Y1 + WT
box("Quay", (60.0, QUAY_Y - QY0 + 0.3, 0.4), (0.0, (QY0 - 0.3 + QUAY_Y) / 2, -0.2), M_COBBLE)
box("QuayEdge", (60.0, 0.6, 0.25), (0.0, QUAY_Y - 0.3, 0.07), M_QUAYWALL)
box("QuayWall", (60.0, 0.8, 4.0), (0.0, QUAY_Y + 0.1, -2.2), M_QUAYWALL)
box("StreetW", (8.0, 30.0, 0.4), (X0 - WT - 4.0, 0.0, -0.2), M_COBBLE)
for k, x in enumerate((-6.0, -1.0, 4.5, 9.5)):
    lathe(f"Bollard{k}", [(0, 0), (0.18, 0), (0.16, 0.45), (0.2, 0.55), (0.0, 0.6)], (x, QUAY_Y - 0.5, 0.0), M_IRON, steps=12)
# the houses along the street (the tavern's neighbours) and across the side street
for k, (x0, x1, hh) in enumerate(((X1 + WT, 30, 8.0),)):
    box(f"Neighbour{k}", (x1 - x0, 6.0, hh), ((x0 + x1) / 2, Y1 + WT - 3.0, hh / 2), M_BRICK)
box("Tavern_Upper", (X1 - X0 + 2 * WT, Y1 - Y0 + 2 * WT, 3.5), (0, 0, H + 1.75 + 0.1), M_BRICK)
box("StreetW_Houses", (14.0, 19.1, 9.0), (X0 - WT - 15.0, -5.45, 4.5), M_BRICK)
# the sign: a large brass telescope on an iron bracket over the quay door, and the newly painted board above the door
SIGN = Vector((QDOOR_X + 0.4, QY0 + 0.9, 3.4))
box("Sign_Bracket", (0.05, 1.3, 0.05), (SIGN.x, QY0 + 0.65, 3.85), M_IRON)
box("Sign_Brace", (0.04, 1.0, 0.04), (SIGN.x, QY0 + 0.5, 3.6), M_IRON, rot=(0.5, 0, 0))
for k, (r, L, off) in enumerate(((0.16, 0.9, 0.0), (0.13, 0.6, 0.72), (0.10, 0.45, 1.22))):
    cyl(f"Sign_Telescope{k}", r, L, (SIGN.x - 0.3 + off, SIGN.y, SIGN.z), M_BRASS, verts=16, rot=(0, math.pi / 2, 0))
for k, x in enumerate((-0.15, 0.45, 0.95)):
    cyl(f"Sign_TelescopeRing{k}", 0.175 - k * 0.03, 0.05, (SIGN.x - 0.3 + x, SIGN.y, SIGN.z), M_BRASS, verts=16, rot=(0, math.pi / 2, 0))
for s in (-0.35, 0.35): cyl(f"Sign_Chain{s}", 0.008, 0.45, (SIGN.x + s, SIGN.y, SIGN.z + 0.3), M_IRON, verts=4)
box("Sign_Board", (2.6, 0.06, 0.45), (QDOOR_X, QY0 + 0.04, QDOOR_H + 0.45), M_SIGNP, bevel=0.01)

# the ship lying at the quay, bow towards the tavern's end, with her figurehead
SHIP_X, SHIP_Y = 3.0, QUAY_Y + 5.2
def hull(name, cx, cy, L, B, D, yaw, mat=M_HULL, far=False):
    nsec, st = (14, 9) if not far else (8, 6)
    rows = []
    for i in range(nsec):
        t = i / (nsec - 1); u = t * 2 - 1
        bow = max(0.0, u)
        half = B / 2 * (1 - bow ** 1.8) ** 0.7 * (1 - max(0.0, -u) ** 3 * 0.35) + 0.05
        sheer = D * (1 + 0.18 * u * u + 0.1 * bow)
        row = []
        for k in range(st):
            a = math.pi * k / (st - 1)
            row.append(Vector((u * L / 2, -math.cos(a) * half, sheer - math.sin(a) ** 0.6 * D * (1 - 0.3 * bow ** 2))))
        rows.append(row)
    vs = [p for r in rows for p in r]
    fs = [[i * st + k, i * st + k + 1, (i + 1) * st + k + 1, (i + 1) * st + k] for i in range(nsec - 1) for k in range(st - 1)]
    R = Matrix.Rotation(yaw, 3, 'Z')
    o = from_pydata(name, [Vector((cx, cy, SL - D * 0.55)) + R @ p for p in vs], fs, mat, smooth_=True)
    # the deck, inside the bulwarks, planked
    dv = []
    for r in rows: dv += [r[0] * 0.96 + Vector((0, 0, -0.9)), r[-1] * 0.96 + Vector((0, 0, -0.9))]
    dv = [Vector((p.x, p.y * 0.97, p.z)) for p in dv]
    dfs = [[2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1] for i in range(nsec - 1)]
    from_pydata(name + "_Deck", [Vector((cx, cy, SL - D * 0.55)) + R @ p for p in dv], dfs, M_DECK)
    # inner face of the bulwarks
    iv = []
    for r in rows: iv += [r[0] * 0.97 + Vector((0, 0, -0.9)), r[0] * 0.985, r[-1] * 0.97 + Vector((0, 0, -0.9)), r[-1] * 0.985]
    ifs = []
    for i in range(nsec - 1):
        a = 4 * i; ifs += [[a, a + 1, a + 5, a + 4], [a + 2, a + 6, a + 7, a + 3]]
    from_pydata(name + "_Bulwark", [Vector((cx, cy, SL - D * 0.55)) + R @ p for p in iv], ifs, M_DECK)
    return o, R
SHIP_L, SHIP_B, SHIP_D = 28.0, 7.4, 5.2
_, SR = hull("Ship_Hull", SHIP_X, SHIP_Y, SHIP_L, SHIP_B, SHIP_D, math.radians(180))
SC = Vector((SHIP_X, SHIP_Y, SL - SHIP_D * 0.55))
def sp(lx, ly, lz): return SC + SR @ Vector((lx, ly, lz))
DECK = SHIP_D * 0.95
RIG = Builder("Rigging", M_RIG)
def line(p0, p1, w=0.025):
    d = (p1 - p0); n = d.cross(Vector((0, 0, 1)))
    if n.length < 1e-4: n = Vector((1, 0, 0))
    n = n.normalized() * w
    RIG.add([p0 - n, p0 + n, p1 + n, p1 - n], [[0, 1, 2, 3]])
MASTS = [(-8.0, 26.0), (1.0, 30.0), (9.0, 22.0)]           # mizzen, main, fore (local x, height above deck)
flag_top = None
for k, (mx, mh) in enumerate(MASTS):
    base = sp(mx, 0, DECK); topp = sp(mx, 0, DECK + mh)
    cyl(f"Mast{k}", 0.32 if mh > 25 else 0.26, mh, tuple((base + topp) / 2), M_SPAR, verts=10, r2=0.12)
    for j, (hz, yl) in enumerate(((0.38, 0.8), (0.66, 0.6), (0.88, 0.42))):
        yc = sp(mx, 0, DECK + mh * hz)
        cyl(f"Yard{k}{j}", 0.12 * yl + 0.05, SHIP_B * 1.9 * yl, tuple(yc), M_SPAR, verts=8, rot=(math.pi / 2, 0, 0))
        cyl(f"Furled{k}{j}", 0.22 * yl + 0.06, SHIP_B * 1.7 * yl, tuple(yc + Vector((0, 0, -0.25))), M_SAIL, verts=8, rot=(math.pi / 2, 0, 0))
        box(f"Top{k}{j}", (1.8, 2.6, 0.12), tuple(sp(mx, 0, DECK + mh * hz - 0.6)), M_SPAR) if j == 0 else None
    for s in (-1, 1):                 # shrouds to the channels
        for e in range(5):
            line(sp(mx - 1.6 + e * 0.8, s * SHIP_B / 2, DECK + 0.6), sp(mx, s * 0.6, DECK + mh * 0.38))
            line(sp(mx - 0.6 + e * 0.3, s * 1.2, DECK + mh * 0.38), sp(mx, s * 0.3, DECK + mh * 0.66), 0.018)
    if k < 2: line(sp(mx, 0, DECK + mh * 0.95), sp(MASTS[k + 1][0], 0, DECK + MASTS[k + 1][1] * 0.6), 0.03)
    if k == 1: flag_top = sp(mx, 0, DECK + mh)
# bowsprit, forestay, figurehead
bs0 = sp(SHIP_L / 2 - 1.0, 0, DECK + 0.6); bs1 = sp(SHIP_L / 2 + 9.0, 0, DECK + 4.0)
cyl("Bowsprit", 0.28, (bs1 - bs0).length, tuple((bs0 + bs1) / 2), M_SPAR, verts=8, r2=0.1,
    rot=(Vector((0, 0, 1)).rotation_difference(bs1 - bs0)).to_euler())
line(bs1, sp(MASTS[2][0], 0, DECK + MASTS[2][1] * 0.9), 0.03)
line(bs1, sp(MASTS[2][0], 0, DECK + MASTS[2][1] * 0.4), 0.03)
FH = sp(SHIP_L / 2 + 0.4, 0, DECK - 0.4)
lathe("Figurehead", [(0, 0), (0.30, 0.0), (0.38, 0.6), (0.30, 1.3), (0.22, 1.6), (0.14, 1.75), (0.20, 1.95), (0.17, 2.15), (0, 2.25)], tuple(FH), M_FIG, steps=10, rot=(0, -0.9, math.radians(180)))
# the pennant at the main masthead (cloth.flag)
FLAG = Builder("cloth.flag.ship", M_FLAG, living=True)
fv, fw = [], []
for i in range(9):
    t = i / 8
    for zz in (0.0, -0.35 * (1 - t) - 0.02):
        fv.append(flag_top + Vector((0, 0, -0.3 + zz)) + SR @ Vector((t * 4.5, 0.25 * math.sin(t * 5.0), 0))); fw.append((t, 0, 0, 1))
FLAG.add(fv, [[2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1] for i in range(8)], (1, 1, 1, 1), fw)
FLAG.finish(smooth_=True)
# a second ship further along and the forest of masts across the harbour
hull("far.ship2", -24.0, QUAY_Y + 6.0, 24.0, 6.8, 4.6, 0.0, far=True)
FM = Builder("far.masts", M_FARMAST)
rm = random.Random(8)
def mastline(x, y, hh, r=0.18):
    for (a, b_, w) in ((Vector((x, y, -1.0)), Vector((x, y, hh)), r),):
        n = Vector((1, 0, 0)) * w
        FM.add([a - n, a + n, b_ + n * 0.4, b_ - n * 0.4], [[0, 1, 2, 3]])
    for fz in (0.4, 0.65, 0.85):
        yl = (1.0 - fz) * 7.0
        c = Vector((x, y, hh * fz)); n = Vector((0, 0, 0.08))
        FM.add([c + Vector((-yl, 0, 0)) - n, c + Vector((yl, 0, 0)) - n, c + Vector((yl, 0, 0)) + n, c + Vector((-yl, 0, 0)) + n], [[0, 1, 2, 3]])
for k in range(-24, 34):
    if rm.random() < 0.45: continue
    x = k * 2.6 + rm.uniform(-1, 1); y = QUAY_Y + 30.0 + rm.uniform(-4, 6)
    mastline(x, y, rm.uniform(14, 26))
mastline(-24.0 - 6, QUAY_Y + 6.0, 24.0)
mastline(-24.0 + 4, QUAY_Y + 6.0, 27.0)
FM.finish(smooth_=False)
for k in range(5):
    x0 = -40 + k * 17; hh = rm.uniform(8, 12)
    box(f"far.warehouse{k}", (15.0, 10.0, hh), (x0, QUAY_Y + 46.0, hh / 2 - 1.0), M_FARB)
    for j in range(6):
        for zz in range(2, int(hh) - 1, 3):
            box(f"far.whWin{k}{j}{zz}", (0.9, 0.2, 1.3), (x0 - 6 + j * 2.4, QUAY_Y + 40.9, zz), M_FARWIN)
# the harbour water: its own mesh, dense near the quay, foam (G) against the quay wall and round the ship
def harbour():
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    ys_ = [QUAY_Y]
    while ys_[-1] < QUAY_Y + 48: ys_.append(ys_[-1] + min(3.0, 0.35 + 0.12 * (ys_[-1] - QUAY_Y)))
    xs = [-40 + i * 1.25 for i in range(65)]
    grid = [[bm.verts.new((x, y, SL)) for x in xs] for y in ys_]
    for j in range(len(ys_) - 1):
        for i in range(len(xs) - 1):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    for f in bm.faces:
        for l in f.loops: l[uvl].uv = ((l.vert.co.x + 40) / 80, (l.vert.co.y - QUAY_Y) / 48)
    o = mesh_obj("water.ocean.harbour", bm, M_WATER)
    def foam(i, co):
        f = 1.0 - smooth(0.0, 1.2, co.y - QUAY_Y - 0.4)
        ls = SR.inverted() @ (Vector((co.x, co.y, 0)) - Vector((SHIP_X, SHIP_Y, 0)))
        dsh = max(abs(ls.x) - SHIP_L / 2, abs(ls.y) - SHIP_B / 2 * 0.9)
        f = max(f, 0.6 * (1.0 - smooth(0.0, 1.0, dsh)))
        return (0.0, f * (0.6 + 0.4 * noise.noise(Vector((co.x * 0.5, co.y * 0.5, 1.0)))), 0.0, 1.0)
    K.set_color_attr(o.data, foam, "Color")
    return o
harbour()
def sky_dome(name, radius=95.0, seg=36, rings=14):
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
RIG.finish(smooth_=False)

# ----------------------------------------------------------------------------- lights, empties, anchors
light_obj("light.sun", 'SUN', 4.0, (1.0, 0.93, 0.82), tuple(SUN_DIR * 40), direction=-SUN_DIR, angle=math.radians(1.0))
sky_l = light_obj("light.sky", 'SUN', 0.0, (0.70, 0.78, 0.95), (0, 0, 20), direction=(0.1, 0.25, -1.0), angle=math.radians(80))
sky_l.data.use_shadow = False
light_obj("light.tavernFire", 'POINT', 25.0, (1.0, 0.6, 0.3), (X1 - 0.45, 0.6, 0.45), shadow_soft_size=0.2)
world = bpy.data.worlds.new("Morning"); scene.world = world; world.use_nodes = True
wnt = world.node_tree
for n in list(wnt.nodes): wnt.nodes.remove(n)
wg = K.G(wnt); wout = wnt.nodes.new("ShaderNodeOutputWorld"); bg = wnt.nodes.new("ShaderNodeBackground")
wnt.links.new(bg.outputs[0], wout.inputs[0])
wsep = wg.sep(wg.n("ShaderNodeTexCoord").outputs["Generated"])
wg.set(bg.inputs["Color"], wg.ramp(wg.ss(wsep[2], -0.1, 0.8), [(0.0, (0.35, 0.33, 0.30)), (0.15, (0.62, 0.66, 0.72)), (1.0, (0.25, 0.40, 0.75))]))
bg.inputs["Strength"].default_value = 1.6

living_empty("fx.fire.tavern", (X1 - 0.3, 0.6, 0.12), 0.22)
for k, p in enumerate(LANTERNS): living_empty(f"fx.lantern.beam{k + 1}", tuple(p), 0.05)
living_empty("sound.fire.tavern", (X1 - 0.4, 0.6, 0.4), 0.3)
living_empty("sound.crowd.bar", (0.9, Y0 + 1.6, 1.3), 0.3)
living_empty("sound.gulls.quay", (2.0, QUAY_Y + 3.0, 8.0), 0.3)
living_empty("sound.rigging.ship", tuple(sp(1.0, 0, DECK + 8.0)), 0.3)

anchor("reader.entrance", (READER.x, READER.y, 0.0))
fwd = (LOOK_AT - READER); fwd.z = 0; fwd.normalize()
anchor("reader.look", tuple(READER + fwd + Vector((0, 0, EYE))))
anchor("scene.centre", (0.0, 0.0, 0.0))
anchor("tavern.quayDoor", (QDOOR_X, Y1, 0.0))
anchor("tavern.streetDoor", (X0, SDOOR_Y, 0.0))
anchor("tavern.bar", (0.9, Y0 + 1.25, 0.0))
anchor("tavern.sign", tuple(SIGN))
anchor("quay.ship", (SHIP_X, SHIP_Y, SL))

E = READER + Vector((0, 0, EYE))
PAGE_C = E + fwd * 0.6 - Vector((0, 0, 0.05))
page = box("PagePreview", (0.4, 0.004, 0.55), tuple(PAGE_C), plain("M_PagePreview", (0.80, 0.76, 0.66), rough=0.9), rot=(0, 0, math.atan2(fwd.y, fwd.x) - math.pi / 2))
K.apply_all_transforms()

def yawed(deg, dist=5.0, dz=-0.3):
    a = math.radians(deg); d = Matrix.Rotation(a, 3, 'Z') @ fwd
    return tuple(E + d * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(E), yawed(0, 5.0, -0.2), lens=16),
    camera("Cam_Page", tuple(E), yawed(0, 5.0, -0.2), lens=16),
    camera("Cam_Left", tuple(E), yawed(75, 5.0, -0.3), lens=16),
    camera("Cam_Right", tuple(E), yawed(-75, 5.0, -0.3), lens=16),
    camera("Cam_Behind", tuple(E), yawed(180, 5.0, -0.3), lens=16),
    camera("Cam_Down", tuple(E), (READER.x + 0.3, READER.y + 1.4, 0.0), lens=18),
    camera("Cam_Door", (QDOOR_X - 0.6, Y1 - 2.2, EYE), (QDOOR_X + 1.0, QUAY_Y + 8.0, 3.5), lens=20),
    camera("Cam_Quay", (QDOOR_X - 2.5, QUAY_Y - 2.0, EYE), (SHIP_X + 8.0, SHIP_Y, 3.0), lens=18),
]
EXPOSURE = {"Cam_Quay": 0.0, "Cam_Door": 0.9}

if not args.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "spyglass_tavern_source.blend"))
K.budget()
if args.render:
    K.render_cams(cams, OUT, page=page, page_cams={"Cam_Page"}, exposure=EXPOSURE, default_exposure=2.5, prefix=args.prefix)

if args.bake or args.export:
    T_ = args.tex
    stats = K.bake_and_export(
        "spyglass_tavern",
        keep_names={"M_SkyDome": "SkyDome", "M_Harbour": "water.ocean.harbour", "M_RedCurtain": "cloth.curtain.windows", "M_Pennant": "cloth.flag.ship",
                    "M_FarWarehouses": "far.warehouses", "M_FarMasts": "far.masts", "M_FarWindow": "far.windows"},
        size_for={"M_SandedFloor": (T_, T_ // 4, T_), "M_Whitewash": (T_, 0, T_ // 2), "M_Beams": (T_, T_ // 8, T_), "M_CeilingBoards": (T_ // 2, 0, T_ // 2),
                  "M_ElmTables": (T_, T_ // 8, T_ // 2), "M_BarWood": (T_ // 2, T_ // 8, T_ // 2), "M_Casks": (T_ // 2, 0, T_ // 4),
                  "M_RedCurtain": (T_ // 2, 0, T_ // 4), "M_Quay": (T_, 0, T_), "M_QuayWall": (T_ // 4, 0, T_ // 4), "M_Brick": (T_ // 2, 0, T_ // 2),
                  "M_Hull": (T_ // 2, 0, T_ // 4), "M_Spars": (T_ // 4, 0, 0), "M_SkyDome": (T_, 0, 0), "M_Harbour": (128, 0, 0),
                  "M_Pewter": (T_ // 4, T_ // 8, T_ // 4), "M_HearthStone": (T_ // 4, 0, T_ // 4), "M_Brass": (T_ // 4, T_ // 8, T_ // 4)},
        keep_uv={"SkyDome", "water.ocean.harbour"}, emit_only={"M_SkyDome"}, remove=[page], default_div=16)
    print("STATS", stats)
print("DONE")
