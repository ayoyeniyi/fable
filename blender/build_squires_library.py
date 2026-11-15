"""
Fable: Squire Trelawney's library at the Hall (Treasure Island, chapter 6, "The Captain's Papers").

"The servant led us down a matted passage and showed us at the end into a great library, all lined with bookcases
and busts upon the top of them, where the squire and Doctor Livesey sat, pipe in hand, on either side of a bright
fire." ... "up the long, leafless, moonlit avenue to where the white line of the Hall buildings looked on either hand
on great old gardens."

The moment: late on a cold, clear January night, just after the oilskin packet has been opened. The bright fire burns
in the grate; the two chairs stand either side of it; on the table near the hearth lie the opened packet, the
captain's account book and the map of the island with its three red crosses, between two lit candles. Moonlight
comes in cold through the tall sash windows; outside, the leafless avenue and the pale wings of the Hall. No people.

What is here: an oak-floored Georgian library, 8 m x 6.5 m and 4.2 m high: mahogany bookcases on every wall to 3 m
(about two thousand books in calf, morocco and vellum), marble busts on their cornice, a white marble Palladian
chimneypiece with an iron dog-grate and a landscape over the mantel, two green leather wing chairs, the library table
with the papers, a tripod table with pipes, decanter and glass, a Turkey carpet, a terrestrial globe, library steps,
a longcase clock, two tall sash windows with shutters folded into the reveals and slate-blue curtains, and the door
ajar onto the matted passage.

Colour and light: the walls above the cases, the ceiling and the window bays are a cool stone grey and the moonlight
blue; the firelight and candles are warm but not orange-saturated; the exposure keeps both detail in the dark
corners and in the fire.

Living scene (docs/LIVING_SCENES.md): fx.fire.hearth (radius 0.28 m), fx.candle.table1/2, fx.candle.mantel1/2,
sound.fire.hearth, sound.clock.longcase. No wind (the windows are shut).

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet on the floor (z = 0), on the carpet's edge between the table and the room
  anchor.reader.look      eye height 1.55 m, 1 m ahead (towards the north bookcases, the fire on the left)
  anchor.scene.centre     the floor centre
  anchor.library.hearth, anchor.library.table, anchor.library.window, anchor.library.door
  Lamp.fire (POINT in the grate), Lamp.candles (POINT over the table), Lamp.moon (SUN, cool, through the windows):
  "Lamp" names are baked by FableBuild's indoor rule (which tints every Lamp warm: Lamp.moon wants its own cool colour)
  MESH_Flame (emissive flames), MESH_Glass (window panes: transparent), SkyDome / far.garden / far.avenue (outside)
Register as an indoor room (Room = true, not Outdoor).

Axes: metres, Blender +Z up. Room x -4..4, y -3.25..3.25; fire in the west wall (-x), windows in the east wall (+x),
the door in the south wall (-y). The reader faces north (+y).

Run headless (one Blender at a time):
  blender -b -P blender/build_squires_library.py -- --out out/squires-library --render --quick --res 640
  blender -b -P blender/build_squires_library.py -- --out out/squires-library --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, treasure_kit as K
importlib.reload(K)
from treasure_kit import F, smooth, lerp, fbm, new_mat, plain, noisy, box, cyl, mesh_obj, from_pydata, lathe, Builder, \
    anchor, living_empty, light_obj, camera, sharpen_by_angle

args = K.parse_args("out/squires-library")
OUT = args.out
scene, COLL = K.reset_scene("SquiresLibrary", args, bounces=8, diffuse=5, clamp=6.0)
random.seed(1756)

# ----------------------------------------------------------------------------- dimensions
X0, X1, Y0, Y1, H = -4.0, 4.0, -3.25, 3.25, 4.2
WT = 0.55                                  # wall thickness (deep Georgian reveals)
EYE = 1.55
READER = Vector((0.45, -1.15, 0.0))
LOOK_AT = Vector((-0.35, 3.25, 0.0))
CASE_H, CASE_D = 3.0, 0.40                 # bookcases: height, depth
BREAST_X = X0 + 0.45                       # chimney-breast face
FIRE_Y = 0.25
WIN_YS = (-1.45, 1.45); WIN_W, WIN_SILL, WIN_HEAD = 1.15, 0.72, 3.35
DOOR_X, DOOR_W, DOOR_H = 2.45, 1.0, 2.35
_maz, _mel = math.radians(118.0), math.radians(28.0)      # the moon: east-south-east, 28 degrees up (+x east, +y north)
MOON_DIR = Vector((math.sin(_maz) * math.cos(_mel), math.cos(_maz) * math.cos(_mel), math.sin(_mel))).normalized()

# ----------------------------------------------------------------------------- materials
def wood_mat(name, base, dark, light, scale=1.0, axis='X', rough=(0.35, 0.6), coat=0.2, ao=0.25):
    """Figured mahogany / oak: long grain along the axis, growth rings, pores, a waxed sheen, dust in the corners."""
    m, nt, b, g = new_mat(name)
    P = g.pos()
    st = {'X': (0.12, 2.5, 2.5), 'Y': (2.5, 0.12, 2.5), 'Z': (2.5, 2.5, 0.12)}[axis]
    Q = g.stretch(P, st[0] * scale, st[1] * scale, st[2] * scale)
    n1, _ = g.noise(Q, 3.0, 5, 0.6, 2.0)
    rings = g.n("ShaderNodeTexWave", wave_type='BANDS', bands_direction='Z' if axis != 'Z' else 'X', wave_profile='SAW')
    g.set(rings.inputs["Vector"], Q); rings.inputs["Scale"].default_value = 4.0; rings.inputs["Distortion"].default_value = 6.0
    rings.inputs["Detail"].default_value = 3.0
    rf = F(g, rings.outputs["Fac"])
    col = g.ramp(n1 * 0.6 + rf * 0.4, [(0.15, dark), (0.5, base), (0.85, light)])
    pores, _ = g.noise(g.stretch(P, st[0] * 8, st[1] * 8, st[2] * 8), 40.0, 2)
    col = g.mul(col, g.ramp(pores, [(0.4, (0.8, 0.8, 0.8)), (0.6, (1, 1, 1))]), 0.5)
    if ao: col = g.mul(col, g.ao(0.15), ao * 2)
    g.set(b.inputs["Base Color"], col)
    g.set(b.inputs["Roughness"], rough[0] + (rough[1] - rough[0]) * n1)
    b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.35
    g.bump(b, rf * 0.3 + pores * 0.3, 0.15, 0.002)
    return m

def floor_mat(name):
    """Wide oak boards, scrubbed and waxed, greyed with age, running east-west; nail heads, worn paths."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    bw = 0.24
    row = (y / bw).floor()
    rh, _ = g.white(g.comb(row, 0.3, 0.0))
    L = 2.2 + rh * 2.0
    seg = ((x + rh * 7.0) / L).floor()
    bid, bidc = g.white(g.comb(row, seg, 1.0))
    fu = ((x + rh * 7.0) / L).fract(); fv = (y / bw).fract()
    seam = (1.0 - g.ss(fv.min(1.0 - fv), 0.0, 0.025)).max(1.0 - g.ss((fu.min(1.0 - fu)) * L, 0.0, 0.006))
    Q = g.comb(x * 0.25 + bid * 13.0, y * 6.0, z)
    n1, _ = g.noise(Q, 4.0, 5, 0.6, 1.5)
    col = g.ramp(n1, [(0.2, (0.075, 0.055, 0.04)), (0.5, (0.13, 0.10, 0.072)), (0.85, (0.19, 0.15, 0.11))])
    col = g.mul(col, g.comb(0.8 + bid * 0.4, 0.8 + bid * 0.38, 0.8 + bid * 0.35))
    col = g.mix(seam * 0.85, col, (0.02, 0.015, 0.012))
    nail = 1.0 - g.ss(g.vor(g.comb(fu * L * 4.0, fv * 4.0, bid), 1.0), 0.03, 0.06)
    col = g.mix(nail * g.ss(fu, 0.02, 0.03) * 0.0, col, (0.02, 0.02, 0.02))
    col = g.mul(col, g.ao(0.2), 0.7)
    g.set(b.inputs["Base Color"], col)
    g.set(b.inputs["Roughness"], 0.45 + n1 * 0.2 + seam * 0.3)
    b.inputs["Coat Weight"].default_value = 0.15
    g.bump(b, n1 * 0.2 - seam * 1.0, 0.4, 0.003)
    return m

def plaster_mat(name, col0=(0.42, 0.42, 0.40), col1=(0.50, 0.50, 0.48), rough=0.85):
    m, nt, b, g = new_mat(name)
    P = g.pos()
    n1, _ = g.noise(P, 1.2, 5)
    n2, _ = g.noise(P, 14.0, 3)
    col = g.ramp(n1 * 0.7 + n2 * 0.3, [(0.3, col0), (0.7, col1)])
    _, _, z = g.sep(P)
    col = g.mul(col, g.ramp(g.ss(z, 2.6, 4.2), [(0.0, (1, 1, 1)), (1.0, (0.86, 0.85, 0.84))]))    # a little smoke near the ceiling
    col = g.mul(col, g.ao(0.4), 0.7)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = rough
    g.bump(b, n2, 0.15, 0.003)
    return m

def marble_mat(name, base=(0.62, 0.61, 0.58), vein=(0.30, 0.31, 0.32), rough=0.28):
    """White statuary marble with grey veins."""
    m, nt, b, g = new_mat(name)
    P = g.pos()
    n1, _ = g.noise(P, 1.6, 6, 0.65, 3.0)
    v = 1.0 - g.ss((n1 - 0.5).abs(), 0.0, 0.03)
    n2, _ = g.noise(P, 6.0, 5, 0.6, 2.0)
    v2 = 1.0 - g.ss((n2 - 0.5).abs(), 0.0, 0.015)
    col = g.mix(v * 0.6 + v2 * 0.3, base, vein)
    col = g.mul(col, g.ao(0.12), 0.6)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Subsurface Weight"].default_value = 0.0
    return m

def book_mat(name):
    """Book spines: each book its own leather (tint) with raised bands, gilt fillets and a title label; page edges on
    top. 'bk' holds each book's bottom, height and a seed so the bands sit right on every spine."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    at = g.attr("tint"); bk = g.attr("bk")
    b0, bh, bs = g.sep(bk.outputs["Color"])
    v = (z - b0) / bh
    tint = at.outputs["Color"]
    n1, _ = g.noise(P, 30.0, 4)
    n2, _ = g.noise(P, 3.0, 3)
    leather = g.mul(tint, g.ramp(n1 * 0.6 + n2 * 0.4, [(0.25, (0.7, 0.7, 0.7)), (0.6, (1.0, 1.0, 1.0)), (0.85, (1.25, 1.2, 1.15))]))
    # bands: 4 or 5 raised bands, each with a gilt fillet either side (some books plain: vellum, boards)
    nb = 4.0 + (bs * 7.0).floor().min(1.0)
    bandp = (v * (nb + 1.0)).fract()
    band = 1.0 - g.ss((bandp - 0.5).abs(), 0.03, 0.06)
    fil = (1.0 - g.ss(((bandp - 0.5).abs() - 0.085).abs(), 0.0, 0.012))
    fancy = g.ss(F(g, at.outputs["Alpha"]), 0.25, 0.3)
    label = g.ss(v, 0.69, 0.70) * (1.0 - g.ss(v, 0.79, 0.80)) * fancy
    labc = g.mix(g.ss(bs, 0.5, 0.52), (0.13, 0.02, 0.015), (0.02, 0.02, 0.018))
    col = g.mul(leather, g.comb(1.0 - band * 0.35, 1.0 - band * 0.35, 1.0 - band * 0.35))
    col = g.mix(label, col, labc)
    gilt = (fil * fancy * (1.0 - label)).max(label * (1.0 - g.ss(((v - 0.745).abs()), 0.0, 0.012)) * 0.8)
    headtail = (1.0 - g.ss(v, 0.025, 0.035)).max(g.ss(v, 0.965, 0.975)) * fancy
    gilt = gilt.max(headtail * 0.8)
    col = g.mix(gilt * g.ss(n1, 0.25, 0.4), col, (0.42, 0.30, 0.10))
    # page edges on top
    nz = g.nz()
    pages = g.ss(nz, 0.6, 0.8)
    pl, _ = g.noise(g.stretch(P, 1, 1, 1), 200.0, 2)
    col = g.mix(pages, col, g.ramp(pl, [(0.3, (0.33, 0.29, 0.21)), (0.7, (0.42, 0.37, 0.28))]))
    col = g.mul(col, g.ao(0.08), 0.8)
    g.set(b.inputs["Base Color"], col)
    g.set(b.inputs["Roughness"], 0.55 - gilt * 0.3 + pages * 0.3)
    g.set(b.inputs["Metallic"], gilt * 0.7)
    g.bump(b, band * 1.0 + n1 * 0.2, 0.5, 0.002)
    return m

def carpet_mat(name, cx, cy, hw, hd):
    """A Turkey carpet: madder-red field with indigo and ivory lattice, indigo borders with guard stripes, worn
    paler in front of the hearth."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    u = (x - cx) / hw; v = (y - cy) / hd
    du = 1.0 - u.abs(); dv = 1.0 - v.abs()
    e = (du * hw).min(dv * hd)                      # distance to the carpet edge in metres
    n1, _ = g.noise(P, 6.0, 4)
    n2, _ = g.noise(P, 60.0, 3)
    red = g.ramp(n1, [(0.3, (0.13, 0.025, 0.02)), (0.7, (0.19, 0.04, 0.03))])
    indigo = g.ramp(n1, [(0.3, (0.02, 0.03, 0.065)), (0.7, (0.035, 0.045, 0.09))])
    ivory = (0.40, 0.36, 0.27); gold = (0.30, 0.20, 0.06)
    # field lattice of lozenges
    lu = (x - cx) * 3.2; lv = (y - cy) * 3.2
    a1 = ((lu + lv) * 0.7071).fract(); a2 = ((lu - lv) * 0.7071).fract()
    lat = (1.0 - g.ss((a1 - 0.5).abs(), 0.40, 0.46)).max(1.0 - g.ss((a2 - 0.5).abs(), 0.40, 0.46))
    lat = 1.0 - lat
    cellc = ((lu + lv) * 0.7071).floor() + ((lu - lv) * 0.7071).floor() * 3.0
    ch, _ = g.white(g.comb(cellc, 0.1, 0.2))
    rosette = 1.0 - g.ss((((a1 - 0.5) ** 2) + ((a2 - 0.5) ** 2) if False else ((a1 - 0.5).abs() + (a2 - 0.5).abs())), 0.08, 0.14)
    col = g.mix(lat, red, indigo)
    col = g.mix(rosette * 0.9, col, g.mix(g.ss(ch, 0.5, 0.52), ivory, gold))
    # central medallion
    md = (u * u * 1.0 + v * v * 2.2).sqrt()
    med = 1.0 - g.ss(md, 0.32, 0.34)
    col = g.mix(med, col, indigo)
    col = g.mix((1.0 - g.ss((md - 0.24).abs(), 0.01, 0.02)) * med, col, ivory)
    # borders
    bmain = (1.0 - g.ss(e, 0.30, 0.31)) * g.ss(e, 0.08, 0.09)
    bpat = ((e * 40.0).sin() * (((x + y) * 18.0).sin()) * 0.5 + 0.5)
    bcol = g.mix(g.ss(bpat, 0.55, 0.7), indigo, gold)
    col = g.mix(bmain, col, bcol)
    guard = (1.0 - g.ss((e - 0.05).abs(), 0.012, 0.018)).max(1.0 - g.ss((e - 0.335).abs(), 0.012, 0.018))
    col = g.mix(guard, col, ivory)
    col = g.mix(1.0 - g.ss(e, 0.0, 0.02), col, red)
    col = g.mul(col, g.ramp(n2, [(0.3, (0.8, 0.8, 0.8)), (0.7, (1.1, 1.1, 1.1))]))
    wear = (1.0 - g.ss(((x - (X0 + 1.6)) ** 2 if False else (x - (X0 + 1.6)).abs()), 0.3, 1.0)) * 0.3
    col = g.mix(wear * g.ss(n1, 0.4, 0.7), col, (0.25, 0.20, 0.16))
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.95
    b.inputs["Sheen Weight"].default_value = 0.6; b.inputs["Sheen Roughness"].default_value = 0.4
    g.bump(b, n2, 0.4, 0.002)
    return m

def map_mat(name, cx, cy, w, d):
    """The map: yellowed paper, the island drawn in brown ink like a fat dragon standing up, its hills hatched, the
    soundings, the compass, and three crosses of red ink (two in the north, one in the south-west)."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    u = (x - cx) / w; v = (y - cy) / d                          # -0.5..0.5 across the sheet
    n1, _ = g.noise(P, 8.0, 5)
    n2, _ = g.noise(P, 50.0, 3)
    paper = g.ramp(n1 * 0.7 + n2 * 0.3, [(0.2, (0.40, 0.33, 0.20)), (0.6, (0.50, 0.43, 0.28)), (0.9, (0.55, 0.48, 0.33))])
    fold = 1.0 - g.ss((u).abs(), 0.0, 0.006)
    fold = fold.max(1.0 - g.ss(v.abs(), 0.0, 0.006))
    paper = g.mix(fold * 0.5, paper, (0.30, 0.24, 0.14))
    edge = g.ss((0.5 - u.abs()).min(0.5 - v.abs()), 0.0, 0.05)
    paper = g.mul(paper, g.comb(0.7 + edge * 0.3, 0.68 + edge * 0.32, 0.62 + edge * 0.38))
    # the island: an elongated blob, the land a little darker
    iu = u / 0.34; iv = (v + 0.08 * (u * 9.0).sin()) / 0.24
    isn, _ = g.noise(g.comb(u * 7.0, v * 7.0, 4.2), 1.0, 6, 0.62, 0.6)
    isn2, _ = g.noise(g.comb(u * 22.0, v * 22.0, 1.3), 1.0, 3)
    r = (iu * iu + iv * iv).sqrt() + (isn - 0.5) * 1.1 + (isn2 - 0.5) * 0.25
    land = 1.0 - g.ss(r, 0.99, 1.0)
    coast = 1.0 - g.ss((r - 0.995).abs(), 0.0, 0.012)
    hill, _ = g.noise(g.comb(iu * 5.0, iv * 5.0, 9.0), 1.0, 3)
    hatch = ((u * 260.0 + v * 140.0).sin() * 0.5 + 0.5)
    hills = g.ss(hill, 0.6, 0.64) * land * g.ss(hatch, 0.7, 0.85) * 0.6
    snd = (1.0 - land) * g.ss((((r * 25.0).sin()) * 0.5 + 0.5), 0.94, 0.98) * (1.0 - g.ss(r, 1.05, 1.25)) * 0.5
    ink = (0.07, 0.045, 0.03)
    col = g.mix(land * 0.18, paper, (0.33, 0.25, 0.14))
    col = g.mix((coast + hills * 0.7 + snd).min(1.0), col, ink)
    border = 1.0 - g.ss(((0.5 - u.abs()).min(0.5 - v.abs()) - 0.03).abs(), 0.0, 0.003)
    col = g.mix(border, col, ink)
    # the three red crosses
    for (pu, pv) in ((-0.06, 0.16), (0.08, 0.20), (-0.13, -0.17)):
        a = ((u - pu) + (v - pv)).abs(); c_ = ((u - pu) - (v - pv)).abs()
        inbox = 1.0 - g.ss(((u - pu).abs()).max((v - pv).abs()), 0.026, 0.03)
        cross = (1.0 - g.ss(a.min(c_), 0.004, 0.009)) * inbox
        col = g.mix(cross, col, (0.42, 0.03, 0.02))
    # compass rose
    cu, cv = u - 0.33, v + 0.30
    cr_ = (cu * cu + cv * cv).sqrt()
    star = (1.0 - g.ss(cu.abs().min(cv.abs()), 0.0, 0.002)) * (1.0 - g.ss(cr_, 0.05, 0.052))
    ring = 1.0 - g.ss((cr_ - 0.035).abs(), 0.0, 0.002)
    col = g.mix(star.max(ring), col, ink)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.8
    g.bump(b, n2 * 0.5 + fold * -1.0, 0.25, 0.001)
    return m

def painting_mat(name, cx, cz, w, hh, axis='y'):
    """A landscape in the manner of the 1740s over the mantel: a dark wooded foreground, a pale river and distant
    blue hills, a warm evening sky, under old varnish."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    u = ((y if axis == 'y' else x) - cx) / w + 0.5; v = (z - cz) / hh + 0.5
    n1, _ = g.noise(g.comb(u * 4.0, v * 4.0, 1.0), 1.0, 5)
    n2, _ = g.noise(g.comb(u * 30.0, v * 30.0, 2.0), 1.0, 3)
    sky = g.ramp(v, [(0.4, (0.40, 0.33, 0.20)), (0.7, (0.30, 0.30, 0.25)), (1.0, (0.17, 0.20, 0.22))])
    hills = 0.42 + (u * 5.0 + 1.0).sin() * 0.04 + n1 * 0.05
    col = g.mix(1.0 - g.ss(v, hills - 0.005, hills + 0.005), sky, (0.17, 0.19, 0.20))
    ground = 0.30 + (u * 3.0).sin() * 0.05
    col = g.mix(1.0 - g.ss(v, ground - 0.01, ground + 0.01), col, g.ramp(n2, [(0.3, (0.05, 0.05, 0.025)), (0.7, (0.10, 0.09, 0.04))]))
    riv = (1.0 - g.ss((v - 0.27 - (u * 6.0).sin() * 0.02).abs(), 0.0, 0.02)) * g.ss(u, 0.3, 0.4)
    col = g.mix(riv * 0.8, col, (0.32, 0.30, 0.24))
    trees = (1.0 - g.ss(u, 0.18 + n1 * 0.1, 0.25 + n1 * 0.1)) * (1.0 - g.ss(v, 0.75 + n2 * 0.1, 0.8 + n2 * 0.1))
    col = g.mix(trees, col, g.ramp(n2, [(0.3, (0.025, 0.03, 0.015)), (0.7, (0.06, 0.06, 0.03))]))
    col = g.mul(col, (0.85, 0.80, 0.62))                       # old varnish
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.35
    g.bump(b, n2, 0.2, 0.001)
    return m

def leather_mat(name, base=(0.035, 0.055, 0.04), hi=(0.07, 0.09, 0.06)):
    m, nt, b, g = new_mat(name)
    P = g.pos()
    n1, _ = g.noise(P, 8.0, 5)
    n2, _ = g.noise(P, 90.0, 3)
    col = g.ramp(n1, [(0.3, base), (0.7, hi)])
    col = g.mul(col, g.ao(0.12), 0.8)
    g.set(b.inputs["Base Color"], col)
    g.set(b.inputs["Roughness"], 0.38 + n1 * 0.2)
    b.inputs["Coat Weight"].default_value = 0.2
    g.bump(b, n2, 0.3, 0.001)
    return m

def curtain_mat(name):
    """Slate-blue wool damask with a woven pattern, faded at the leading edges."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    n1, _ = g.noise(P, 3.0, 4)
    pat = ((y * 22.0).sin() * (z * 14.0).sin() * 0.5 + 0.5)
    col = g.mix(g.ss(pat, 0.55, 0.8) * 0.4, (0.045, 0.06, 0.085), (0.075, 0.09, 0.115))
    col = g.mul(col, g.ramp(n1, [(0.3, (0.85, 0.85, 0.85)), (0.7, (1.1, 1.1, 1.1))]))
    col = g.mul(col, g.ao(0.2), 0.8)
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Sheen Weight"].default_value = 0.5
    g.bump(b, pat * 0.3 + n1 * 0.2, 0.3, 0.002)
    return m

def ground_out_mat(name):
    """The moonlit garden: frosted lawns, the gravel of the avenue, clipped yew dark."""
    m, nt, b, g = new_mat(name)
    P = g.pos(); x, y, z = g.sep(P)
    n1, _ = g.noise(P, 0.2, 4)
    n2, _ = g.noise(P, 2.0, 4)
    lawn = g.ramp(n1 * 0.6 + n2 * 0.4, [(0.3, (0.16, 0.18, 0.15)), (0.7, (0.24, 0.26, 0.23))])
    grav = 1.0 - g.ss(y.abs(), 2.2, 2.4)
    col = g.mix(grav, lawn, (0.32, 0.31, 0.28))
    g.set(b.inputs["Base Color"], col)
    b.inputs["Roughness"].default_value = 0.9
    return m

def night_sky_mat(name="M_SkyDome"):
    """A clear winter night: deep blue overhead, paler round the moon (east-south-east), stars, a faint lighter band
    at the horizon."""
    m, nt, b, g = new_mat(name)
    nv = g.n("ShaderNodeVectorMath", operation='NORMALIZE'); g.set(nv.inputs[0], g.pos())
    d = nv.outputs[0]
    dx, dy, el = g.sep(d)
    col = g.ramp(g.ss(el, -0.02, 0.8), [(0.0, (0.035, 0.045, 0.07)), (0.08, (0.025, 0.035, 0.065)), (1.0, (0.006, 0.010, 0.025))])
    sd = g.n("ShaderNodeVectorMath", operation='DOT_PRODUCT'); g.set(sd.inputs[0], d); sd.inputs[1].default_value = tuple(MOON_DIR)
    sdot = F(g, sd.outputs["Value"])
    col = g.mix(g.ss(sdot, 0.85, 1.0).pow(2.0) * 0.6, col, (0.10, 0.12, 0.17))
    col = g.mix(g.ss(sdot, 0.99985, 0.9999), col, (3.0, 3.0, 2.8))
    st = g.white(g.scale(d, 260.0))[0]
    col = g.mix(g.ss(st, 0.996, 0.999) * g.ss(el, 0.05, 0.2), col, (1.2, 1.2, 1.3))
    g.set(b.inputs["Emission Color"], col); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0
    return m

M_FLOOR = floor_mat("M_Floor")
M_PLASTER = plaster_mat("M_Plaster")
M_CEIL = plaster_mat("M_Ceiling", (0.50, 0.50, 0.49), (0.56, 0.56, 0.55), rough=0.9)
M_PANEL = plaster_mat("M_PaintedPanel", (0.26, 0.28, 0.26), (0.30, 0.32, 0.30), rough=0.6)
M_MAHOG = wood_mat("M_Mahogany", (0.10, 0.04, 0.022), (0.035, 0.014, 0.008), (0.16, 0.07, 0.035), axis='Z')
M_MAHOGH = wood_mat("M_MahoganyFurniture", (0.12, 0.05, 0.026), (0.04, 0.016, 0.009), (0.19, 0.085, 0.04), axis='X', coat=0.4)
M_OAK = wood_mat("M_OakDoor", (0.075, 0.045, 0.025), (0.03, 0.018, 0.01), (0.11, 0.07, 0.04), axis='Z', coat=0.2)
M_BOOKS = book_mat("M_Books")
M_MARBLE = marble_mat("M_Marble")
M_BUST = marble_mat("M_BustMarble", base=(0.58, 0.57, 0.54), vein=(0.45, 0.45, 0.44), rough=0.4)
M_IRON = noisy("M_Iron", [(0.012, 0.012, 0.012), (0.03, 0.028, 0.026), (0.05, 0.045, 0.04)], scale=20, rough=0.55, metallic=0.7, bump=0.3)
M_BRASS = noisy("M_Brass", [(0.30, 0.20, 0.06), (0.45, 0.32, 0.12), (0.55, 0.42, 0.18)], scale=12, rough=0.3, metallic=1.0, bump=0.05)
M_GILT = noisy("M_Gilt", [(0.25, 0.16, 0.05), (0.42, 0.30, 0.10), (0.55, 0.42, 0.18)], scale=30, rough=0.35, metallic=0.9, bump=0.2)
M_SOOT = noisy("M_Firebox", [(0.012, 0.011, 0.01), (0.03, 0.026, 0.022), (0.06, 0.05, 0.04)], scale=6, rough=0.95, bump=0.4)
M_LOGS = noisy("M_Logs", [(0.02, 0.014, 0.01), (0.06, 0.04, 0.025), (0.10, 0.07, 0.045)], scale=14, rough=0.9, stretch=(0.2, 1, 1), bump=0.6)
M_EMBERS = plain("M_Embers", (0.05, 0.02, 0.01), rough=0.9, emission=(1.0, 0.30, 0.06), strength=6.0)
M_FLAME = plain("M_Flame", (0.0, 0.0, 0.0), rough=1.0, emission=(1.0, 0.42, 0.10), strength=4.0)
M_WAX = noisy("M_Wax", [(0.62, 0.58, 0.48), (0.68, 0.64, 0.54)], scale=10, rough=0.4, bump=0.05)
M_CARPET = carpet_mat("M_Carpet", -1.15, 0.15, 2.0, 1.45)
M_MAP = map_mat("M_Map", -1.55, 0.05, 0.50, 0.38)
M_PAPER = noisy("M_Paper", [(0.42, 0.37, 0.27), (0.52, 0.47, 0.36)], scale=20, rough=0.85, bump=0.05)
M_OILSKIN = noisy("M_Oilskin", [(0.04, 0.035, 0.02), (0.08, 0.07, 0.04), (0.12, 0.11, 0.06)], scale=6, rough=0.45, bump=0.5, coat=0.3)
M_LEATHER = leather_mat("M_ChairLeather")
M_BOOKBOARD = leather_mat("M_AccountBook", (0.06, 0.03, 0.015), (0.11, 0.06, 0.03))
M_GLASS = plain("M_Glass", (0.6, 0.65, 0.7), rough=0.03, transmission=1.0)
M_DECANT = plain("M_Decanter", (0.25, 0.08, 0.05), rough=0.05, transmission=0.85)
M_CURTAIN = curtain_mat("M_Curtain")
M_PAINT = painting_mat("M_Painting", FIRE_Y, 2.25, 1.15, 0.82)
M_CLAY = noisy("M_ClayPipe", [(0.55, 0.52, 0.46), (0.62, 0.60, 0.54)], scale=20, rough=0.6, bump=0.05)
M_GLOBE = noisy("M_Globe", [(0.30, 0.26, 0.17), (0.38, 0.33, 0.22), (0.20, 0.25, 0.22)], scale=3.0, rough=0.4, coat=0.3, bump=0.05)
M_MATTING = noisy("M_Matting", [(0.18, 0.15, 0.09), (0.26, 0.22, 0.14), (0.32, 0.28, 0.18)], scale=60, rough=0.9, stretch=(1, 6, 1), bump=0.6)
M_CLOCKFACE = noisy("M_ClockFace", [(0.45, 0.40, 0.28), (0.52, 0.47, 0.34)], scale=8, rough=0.3, metallic=0.3)
M_GOUT = ground_out_mat("M_FarGarden")
M_STUCCO = plaster_mat("M_FarStucco", (0.42, 0.43, 0.45), (0.50, 0.51, 0.53), rough=0.9)
M_BARK = noisy("M_FarTrees", [(0.03, 0.03, 0.03), (0.06, 0.06, 0.055)], scale=20, rough=0.9, bump=0.1)
M_SKY = night_sky_mat()
M_CHINA = plain("M_China", (0.50, 0.52, 0.55), rough=0.15, coat=0.6)
M_FARSLATE = plain("M_FarSlate", (0.05, 0.055, 0.065), rough=0.6)
M_FARLIT = plain("M_FarWindowLit", (0.0, 0.0, 0.0), emission=(1.0, 0.66, 0.35), strength=2.0)
M_FARWIN = plain("M_FarWindow", (0.015, 0.018, 0.025), rough=0.1)
M_QUILL = plain("M_Quill", (0.55, 0.52, 0.47), rough=0.6)

# ----------------------------------------------------------------------------- the room shell
box("Floor", (X1 - X0 + 2 * WT, Y1 - Y0 + 2 * WT, 0.1), ((X0 + X1) / 2, (Y0 + Y1) / 2, -0.05), M_FLOOR)
box("Ceiling", (X1 - X0, Y1 - Y0, 0.1), ((X0 + X1) / 2, (Y0 + Y1) / 2, H + 0.05), M_CEIL)
def wall_x(name, x, y0, y1, openings, mat, sx):
    """a wall in the plane x (thickness outward by sx), with rectangular openings (yc, w, z0, z1)"""
    cuts = sorted(openings)
    ys_ = [y0]
    for (yc, w, z0, z1) in cuts: ys_ += [yc - w / 2, yc + w / 2]
    ys_.append(y1)
    xc = x + sx * WT / 2
    for i in range(0, len(ys_), 2):
        a, b_ = ys_[i], ys_[i + 1]
        if b_ - a > 0.001: box(f"{name}_pier{i}", (WT, b_ - a, H), (xc, (a + b_) / 2, H / 2), mat)
    for (yc, w, z0, z1) in cuts:
        if z0 > 0.001: box(f"{name}_below{yc}", (WT, w, z0), (xc, yc, z0 / 2), mat)
        box(f"{name}_above{yc}", (WT, w, H - z1), (xc, yc, (H + z1) / 2), mat)
def wall_y(name, y, x0, x1, openings, mat, sy):
    cuts = sorted(openings)
    xs = [x0]
    for (xc, w, z0, z1) in cuts: xs += [xc - w / 2, xc + w / 2]
    xs.append(x1)
    yc = y + sy * WT / 2
    for i in range(0, len(xs), 2):
        a, b_ = xs[i], xs[i + 1]
        if b_ - a > 0.001: box(f"{name}_pier{i}", (b_ - a, WT, H), ((a + b_) / 2, yc, H / 2), mat)
    for (xc, w, z0, z1) in cuts:
        if z0 > 0.001: box(f"{name}_below{xc}", (w, WT, z0), (xc, yc, z0 / 2), mat)
        box(f"{name}_above{xc}", (w, WT, H - z1), (xc, yc, (H + z1) / 2), mat)
wall_x("WallW", X0, Y0 - WT, Y1 + WT, [], M_PLASTER, -1)
wall_x("WallE", X1, Y0 - WT, Y1 + WT, [(wy, WIN_W, WIN_SILL, WIN_HEAD) for wy in WIN_YS], M_PLASTER, 1)
wall_y("WallN", Y1, X0, X1, [], M_PLASTER, 1)
wall_y("WallS", Y0, X0, X1, [(DOOR_X, DOOR_W, 0.0, DOOR_H)], M_PLASTER, -1)
# cornice, skirting in the window bays, dado rail on the window wall
for (nm, size, loc) in [("CorN", (X1 - X0, 0.22, 0.26), (0, Y1 - 0.11, H - 0.13)), ("CorS", (X1 - X0, 0.22, 0.26), (0, Y0 + 0.11, H - 0.13)),
                        ("CorW", (0.22, Y1 - Y0, 0.26), (X0 + 0.11, 0, H - 0.13)), ("CorE", (0.22, Y1 - Y0, 0.26), (X1 - 0.11, 0, H - 0.13))]:
    box("Cornice" + nm, size, loc, M_CEIL, bevel=0.04)
    box("Cornice2" + nm, tuple(s * (0.55 if i < 2 and s < 1 else 1.0) for i, s in enumerate(size)), (loc[0], loc[1], H - 0.32), M_CEIL)
box("CeilingRose", (0.9, 0.9, 0.05), (0, 0, H - 0.025), M_CEIL, bevel=0.02)
cyl("CeilingRoseBoss", 0.22, 0.08, (0, 0, H - 0.06), M_CEIL, verts=20)
box("SkirtingE", (0.04, Y1 - Y0, 0.22), (X1 - 0.02, 0, 0.11), M_PANEL)
box("DadoE", (0.05, Y1 - Y0, 0.06), (X1 - 0.025, 0, 0.9), M_PANEL)
box("DadoPanelE", (0.025, Y1 - Y0, 0.9), (X1 - 0.012, 0, 0.45), M_PANEL)

# ----------------------------------------------------------------------------- bookcases and books
BOOKS = Builder("Books", M_BOOKS)
LEATHERS = [((0.11, 0.055, 0.028), 0.6), ((0.07, 0.035, 0.018), 0.5), ((0.15, 0.08, 0.04), 0.4), ((0.13, 0.025, 0.02), 0.25),
            ((0.03, 0.05, 0.035), 0.15), ((0.42, 0.37, 0.27), 0.12), ((0.20, 0.12, 0.06), 0.3), ((0.03, 0.025, 0.02), 0.15),
            ((0.06, 0.045, 0.05), 0.08)]
LW = sum(w for _, w in LEATHERS)
rb = random.Random(5)
def pick_leather():
    t = rb.uniform(0, LW)
    for c, w in LEATHERS:
        t -= w
        if t <= 0: return c
    return LEATHERS[0][0]
def frame_of(wall):
    """origin on the wall face, u along the wall, w out into the room"""
    if wall == 'N': return Vector((0, Y1, 0)), Vector((1, 0, 0)), Vector((0, -1, 0))
    if wall == 'S': return Vector((0, Y0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0))
    if wall == 'W': return Vector((X0, 0, 0)), Vector((0, -1, 0)), Vector((1, 0, 0))
    return Vector((X1, 0, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0))
def P_(o, U, W, u, w, z): return o + U * u + W * w + Vector((0, 0, z))
def bookcase(name, wall, u0, u1, base_off=0.0, depth=CASE_D, height=CASE_H, bays=None, busts=True):
    o, U, W = frame_of(wall)
    o = o + W * base_off
    L = u1 - u0
    nb = bays or max(1, round(L / 1.0))
    bw = L / nb
    def bx(nm, uc, wc, zc, su, sw, sz, mat=M_MAHOG):
        c = P_(o, U, W, uc, wc, zc)
        size = (abs(U.x) * su + abs(W.x) * sw, abs(U.y) * su + abs(W.y) * sw, sz)
        box(nm, size, tuple(c), mat)
    bx(name + "_back", (u0 + u1) / 2, 0.01, height / 2, L, 0.02, height)
    bx(name + "_plinth", (u0 + u1) / 2, depth / 2 + 0.02, 0.06, L, depth + 0.02, 0.12)
    # lower cupboards (0.12..0.80) then the shelves
    bx(name + "_cupboard", (u0 + u1) / 2, depth / 2 + 0.015, 0.46, L, depth, 0.68)
    bx(name + "_ledge", (u0 + u1) / 2, depth / 2 + 0.05, 0.82, L + 0.04, depth + 0.08, 0.04)
    bx(name + "_cornice", (u0 + u1) / 2, depth / 2 + 0.06, height - 0.05, L + 0.08, depth + 0.12, 0.10)
    bx(name + "_frieze", (u0 + u1) / 2, depth / 2 + 0.02, height - 0.16, L + 0.02, depth + 0.04, 0.14)
    for i in range(nb + 1):
        bx(f"{name}_up{i}", u0 + i * bw, depth / 2 + 0.01, height / 2, 0.035, depth + 0.02, height)
        if 0 < i:
            for k in (0.25, 0.75):                       # cupboard door panels
                bx(f"{name}_door{i}{k}", u0 + (i - 1) * bw + bw * k, depth + 0.02, 0.46, bw * 0.42, 0.015, 0.52)
    shelves = [0.84, 1.24, 1.60, 1.94, 2.26, 2.56, height - 0.23]
    for i in range(nb):
        ua, ub = u0 + i * bw + 0.02, u0 + (i + 1) * bw - 0.02
        for s in range(len(shelves) - 1):
            z0, z1 = shelves[s], shelves[s + 1]
            if s > 0: bx(f"{name}_sh{i}{s}", (ua + ub) / 2, depth / 2, z0 - 0.012, ub - ua, depth - 0.02, 0.025)
            gap = z1 - z0 - 0.03
            uu = ua + 0.005
            folio = s == 0
            while uu < ub - 0.03:
                if rb.random() < 0.025: uu += rb.uniform(0.04, 0.12); continue
                bwid = rb.uniform(0.022, 0.06) * (1.5 if folio else 1.0)
                if uu + bwid > ub: break
                hgt = gap * rb.uniform(0.70, 0.95) * (1.0 if folio else rb.choice((0.82, 0.9, 1.0)))
                dep = rb.uniform(0.17, 0.25) * (1.3 if folio else 1.0)
                pull = rb.uniform(0.0, 0.025) + (0.06 if rb.random() < 0.02 else 0.0)
                wf = depth - 0.03 - pull
                tint = pick_leather(); fancy = rb.random()
                a0, a1 = uu, uu + bwid
                lean = 0.0
                vs = [P_(o, U, W, a0, wf, z0), P_(o, U, W, a1, wf, z0), P_(o, U, W, a1, wf, z0 + hgt), P_(o, U, W, a0, wf, z0 + hgt),
                      P_(o, U, W, a0, wf - dep, z0 + hgt), P_(o, U, W, a1, wf - dep, z0 + hgt),
                      P_(o, U, W, a0, wf - dep, z0), P_(o, U, W, a1, wf - dep, z0)]
                # spine (rounded a touch by an extra middle column), top, two sides
                fs = [[0, 1, 2, 3], [3, 2, 5, 4], [6, 0, 3, 4], [1, 7, 5, 2]]
                seed = rb.random()
                BOOKS.add(vs, fs, tint + (fancy,), [(z0, hgt, seed, 1.0)] * len(vs))
                uu = a1 + rb.uniform(0.0, 0.003)
    if busts:
        for i in range(nb):
            if i % 2 == 0 and rb.random() < 0.9:
                bust(P_(o, U, W, u0 + (i + 0.5) * bw, depth / 2 + 0.04, height), W)

def bust(base, facing):
    """A marble bust of a classical worthy on a socle (a lathe-turned head and shoulders, unpainted)."""
    s = rb.uniform(0.9, 1.05)
    prof = [(0.0, 0.0), (0.11, 0.0), (0.11, 0.03), (0.08, 0.05), (0.06, 0.10), (0.09, 0.13), (0.10, 0.14), (0.0, 0.14)]
    lathe("BustSocle", [(r * s, z * s) for r, z in prof], tuple(base), M_BUST, steps=12)
    sh = [(0.0, 0.14), (0.16, 0.15), (0.20, 0.20), (0.19, 0.27), (0.13, 0.33), (0.065, 0.36), (0.055, 0.40), (0.0, 0.40)]
    o = lathe("BustShoulders", [(r * s, z * s) for r, z in sh], tuple(base), M_BUST, steps=12)
    o.scale = (1.0, 0.62, 1.0) if abs(facing.y) > 0.5 else (0.62, 1.0, 1.0)
    hd = [(0.0, 0.38), (0.06, 0.39), (0.085, 0.43), (0.09, 0.48), (0.08, 0.53), (0.05, 0.565), (0.0, 0.575)]
    o2 = lathe("BustHead", [(r * s, z * s) for r, z in hd], tuple(base), M_BUST, steps=12)
    o2.scale = (0.9, 1.0, 1.0) if abs(facing.y) > 0.5 else (1.0, 0.9, 1.0)
    nose = base + facing * 0.085 * s + Vector((0, 0, 0.47 * s))
    box("BustNose", (0.02 * s, 0.02 * s, 0.035 * s), tuple(nose), M_BUST)

bookcase("CaseN", 'N', -3.95, 3.95, bays=8)
bookcase("CaseW_S", 'W', 0.95, 2.83, bays=2)                  # west wall, south of the chimney-breast (u runs -y)
bookcase("CaseW_N", 'W', -2.83, -1.55, bays=1)               # north of the breast
bookcase("CaseS_W", 'S', -1.9, 3.95, bays=6)                # south wall, west of the door (u runs -x)
o_ = BOOKS.finish(smooth_=False)
K.set_color_attr(o_.data, lambda i, co: BOOKS.weights[i], "bk")
print("books", len(BOOKS.verts) // 8)

# ----------------------------------------------------------------------------- the chimney-breast, chimneypiece and the fire
BW0, BW1 = FIRE_Y - 1.2, FIRE_Y + 1.2
_OW, _OH = 1.0, 0.95
for s_ in (-1, 1):
    y_a = FIRE_Y + s_ * _OW / 2; y_b = FIRE_Y + s_ * 1.2
    box(f"Breast{s_}", (BREAST_X - X0, abs(y_b - y_a), H), ((X0 + BREAST_X) / 2, (y_a + y_b) / 2, H / 2), M_PANEL)
box("BreastAbove", (BREAST_X - X0, _OW, H - _OH), ((X0 + BREAST_X) / 2, FIRE_Y, (H + _OH) / 2), M_PANEL)
# panelling on the breast: raised fielded panels
for (zc, hh) in ((0.55, 0.0), (2.95, 1.6)):
    if hh: box("BreastPanel", (0.03, 1.9, hh), (BREAST_X + 0.015, FIRE_Y, zc), M_PANEL, bevel=0.01)
OPEN_W, OPEN_H, BOX_D = 1.0, 0.95, 0.42
# firebox recess: sooty back, sides, hearth
box("Firebox_Back", (0.04, OPEN_W, OPEN_H), (BREAST_X - BOX_D, FIRE_Y, OPEN_H / 2), M_SOOT)
for s in (-1, 1):
    box(f"Firebox_Side{s}", (BOX_D, 0.04, OPEN_H), (BREAST_X - BOX_D / 2, FIRE_Y + s * (OPEN_W / 2 - 0.02), OPEN_H / 2), M_SOOT, rot=(0, 0, -s * 0.25))
box("Firebox_Top", (BOX_D, OPEN_W, 0.04), (BREAST_X - BOX_D / 2, FIRE_Y, OPEN_H), M_SOOT)
box("Firebox_Floor", (BOX_D, OPEN_W, 0.02), (BREAST_X - BOX_D / 2, FIRE_Y, 0.01), M_SOOT)
# the Palladian surround: jambs with consoles, frieze with a central tablet, the mantel shelf; hearth slab
for s in (-1, 1):
    box(f"Chimneypiece_Jamb{s}", (0.10, 0.24, 1.15), (BREAST_X + 0.05, FIRE_Y + s * (OPEN_W / 2 + 0.12), 0.575), M_MARBLE, bevel=0.01)
    box(f"Chimneypiece_Console{s}", (0.16, 0.18, 0.28), (BREAST_X + 0.08, FIRE_Y + s * (OPEN_W / 2 + 0.12), 1.0), M_MARBLE, bevel=0.02)
    box(f"Chimneypiece_Plinth{s}", (0.13, 0.28, 0.14), (BREAST_X + 0.065, FIRE_Y + s * (OPEN_W / 2 + 0.12), 0.07), M_MARBLE)
box("Chimneypiece_Lintel", (0.08, OPEN_W + 0.04, 0.2), (BREAST_X + 0.04, FIRE_Y, OPEN_H + 0.1), M_MARBLE)
box("Chimneypiece_Frieze", (0.10, OPEN_W + 0.5, 0.18), (BREAST_X + 0.05, FIRE_Y, OPEN_H + 0.29), M_MARBLE)
box("Chimneypiece_Tablet", (0.03, 0.34, 0.14), (BREAST_X + 0.11, FIRE_Y, OPEN_H + 0.29), M_MARBLE, bevel=0.01)
box("Chimneypiece_Shelf", (0.30, OPEN_W + 0.78, 0.05), (BREAST_X + 0.13, FIRE_Y, OPEN_H + 0.405), M_MARBLE, bevel=0.012)
box("Hearthstone", (0.55, OPEN_W + 0.7, 0.03), (BREAST_X + 0.27, FIRE_Y, 0.015), M_MARBLE)
box("Hearth_Inner", (BOX_D, OPEN_W - 0.06, 0.03), (BREAST_X - BOX_D / 2, FIRE_Y, 0.015), M_MARBLE)
MANTEL_Z = OPEN_H + 0.43
# the overmantel landscape in a carved gilt frame
box("Painting", (0.03, 1.15, 0.82), (BREAST_X + 0.02, FIRE_Y, 2.25), M_PAINT)
for (dy, dz, sy, sz) in ((0, 0.45, 1.33, 0.09), (0, -0.45, 1.33, 0.09), (0.62, 0, 0.09, 0.99), (-0.62, 0, 0.09, 0.99)):
    box("PaintingFrame", (0.06, sy, sz), (BREAST_X + 0.035, FIRE_Y + dy, 2.25 + dz), M_GILT, bevel=0.015)
# the iron dog-grate: a basket on legs with a front of bars, logs, embers and flames
GX = BREAST_X - 0.2
box("Grate_Basket", (0.28, 0.62, 0.03), (GX, FIRE_Y, 0.16), M_IRON)
for k in range(9):
    yy = FIRE_Y - 0.30 + k * 0.075
    box(f"Grate_Bar{k}", (0.015, 0.015, 0.20), (GX + 0.14, yy, 0.26), M_IRON)
for s in (-1, 1):
    box(f"Grate_Rail{s}", (0.3, 0.02, 0.02), (GX, FIRE_Y + s * 0.31, 0.36), M_IRON)
    box(f"Grate_Rail2{s}", (0.02, 0.64, 0.02), (GX + 0.14, FIRE_Y, 0.36 if s > 0 else 0.20), M_IRON)
    for e in (-1, 1):
        cyl(f"Grate_Leg{s}{e}", 0.015, 0.16, (GX + e * 0.12, FIRE_Y + s * 0.28, 0.08), M_IRON, verts=6)
    # the dogs (andirons) with brass finials
    cyl(f"Andiron{s}", 0.02, 0.42, (GX + 0.22, FIRE_Y + s * 0.36, 0.21), M_IRON, verts=8)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.045, location=(GX + 0.22, FIRE_Y + s * 0.36, 0.45))
    K._finish(bpy.context.active_object, M_BRASS, smooth_=True)
rl = random.Random(9)
for k, (y0, y1, z) in enumerate(((FIRE_Y - 0.28, FIRE_Y + 0.22, 0.22), (FIRE_Y - 0.2, FIRE_Y + 0.3, 0.24), (FIRE_Y - 0.25, FIRE_Y + 0.15, 0.32))):
    cyl(f"Log{k}", 0.055 - k * 0.008, y1 - y0, (GX - 0.04 + k * 0.05, (y0 + y1) / 2, z), M_LOGS, verts=8, rot=(math.pi / 2, 0, rl.uniform(-0.25, 0.25)))
box("Embers", (0.24, 0.56, 0.05), (GX, FIRE_Y, 0.19), M_EMBERS)
FL = Builder("Flames", M_FLAME)
for k in range(7):
    cy_ = FIRE_Y + rl.uniform(-0.2, 0.2); hh = rl.uniform(0.12, 0.26); ww = rl.uniform(0.06, 0.1)
    cx_ = GX + rl.uniform(-0.06, 0.06); z0 = 0.25
    for a in (0.0, math.pi / 2):
        d = Vector((math.cos(a), math.sin(a), 0)) * ww
        tip = Vector((cx_ + rl.uniform(-0.02, 0.02), cy_ + rl.uniform(-0.03, 0.03), z0 + hh))
        FL.add([Vector((cx_, cy_, z0)) - d, Vector((cx_, cy_, z0)) + d, Vector((cx_, cy_, z0 + hh * 0.45)) + d * 0.8, tip, Vector((cx_, cy_, z0 + hh * 0.45)) - d * 0.8],
               [[0, 1, 2, 3, 4]])
FL.finish(smooth_=False)
# fender and fire-irons
box("Fender", (0.03, OPEN_W + 0.5, 0.12), (BREAST_X + 0.45, FIRE_Y, 0.09), M_BRASS)
for s in (-1, 1): box(f"FenderEnd{s}", (0.42, 0.03, 0.12), (BREAST_X + 0.24, FIRE_Y + s * (OPEN_W / 2 + 0.25), 0.09), M_BRASS)
for k, dy in enumerate((-0.03, 0.0, 0.03)):
    cyl(f"FireIron{k}", 0.008, 0.72, (BREAST_X + 0.35, FIRE_Y + OPEN_W / 2 + 0.38 + dy, 0.40), M_IRON, verts=6, rot=(0.08 * (k - 1), 0.1, 0))
# on the mantel: two brass candlesticks with candles, a pair of china jars
def candlestick(name, x, y, z, hh=0.24, lit=True, cand=0.16):
    lathe(name, [(0.0, 0.0), (0.065, 0.0), (0.06, 0.02), (0.025, 0.04), (0.018, 0.09), (0.03, 0.12), (0.016, 0.15), (0.02, hh - 0.02),
                 (0.035, hh - 0.01), (0.035, hh), (0.0, hh)], (x, y, z), M_BRASS, steps=12)
    cyl(name + "_Candle", 0.012, cand, (x, y, z + hh + cand / 2), M_WAX, verts=8)
    top = Vector((x, y, z + hh + cand))
    if lit:
        fl = Builder(name + "_Flame", M_FLAME)
        for a in (0.0, math.pi / 2):
            d = Vector((math.cos(a), math.sin(a), 0)) * 0.006
            fl.add([top + Vector((0, 0, 0.005)) - d, top + Vector((0, 0, 0.005)) + d, top + Vector((0, 0, 0.022)) + d * 1.2, top + Vector((0, 0, 0.042)), top + Vector((0, 0, 0.022)) - d * 1.2], [[0, 1, 2, 3, 4]])
        fl.finish(smooth_=False)
    return top
MZ = MANTEL_Z + 0.025
mantel_tops = [candlestick(f"MantelStick{s}", BREAST_X + 0.15, FIRE_Y + s * 0.6, MZ) for s in (-1, 1)]
for s in (-1, 1):
    lathe(f"MantelJar{s}", [(0, 0), (0.05, 0), (0.07, 0.06), (0.075, 0.12), (0.045, 0.2), (0.035, 0.22), (0.0, 0.22)], (BREAST_X + 0.15, FIRE_Y + s * 0.3, MZ), M_CHINA, steps=12)

# ----------------------------------------------------------------------------- the chairs either side of the fire, the tables
def wing_chair(name, cx, cy, yaw):
    R = Matrix.Rotation(yaw, 3, 'Z'); c = Vector((cx, cy, 0))
    def bx(nm, off, size, mat=M_LEATHER, bevel=0.03):
        o = box(f"{name}_{nm}", size, tuple(c + R @ Vector(off)), mat, rot=(0, 0, yaw), bevel=bevel)
        return o
    bx("Seat", (0, 0, 0.42), (0.62, 0.58, 0.14))
    bx("Cushion", (0.03, 0, 0.52), (0.52, 0.52, 0.08))
    bx("Back", (-0.3, 0, 0.86), (0.12, 0.70, 0.86))
    for s in (-1, 1):
        bx(f"Wing{s}", (-0.12, s * 0.34, 0.95), (0.34, 0.08, 0.62))
        bx(f"Arm{s}", (0.05, s * 0.32, 0.6), (0.58, 0.12, 0.2))
    for e in (-1, 1):
        for s in (-1, 1):
            box(f"{name}_Leg{e}{s}", (0.05, 0.05, 0.36), tuple(c + R @ Vector((e * 0.26, s * 0.26, 0.18))), M_MAHOGH, rot=(0, 0, yaw))
    for k in range(12):                                   # brass nail heads along the seat front
        p = c + R @ Vector((0.315, -0.27 + k * 0.049, 0.37))
        box(f"{name}_Nail{k}", (0.012, 0.012, 0.012), tuple(p), M_BRASS)
wing_chair("ChairSquire", BREAST_X + 1.05, FIRE_Y - 1.25, math.radians(125))
wing_chair("ChairDoctor", BREAST_X + 1.05, FIRE_Y + 1.35, math.radians(-125))
# the library table near the hearth
TX, TY, TW_, TD_, TH_ = -1.55, 0.05, 1.5, 0.85, 0.76
box("Table_Top", (TW_, TD_, 0.04), (TX, TY, TH_ - 0.02), M_MAHOGH, bevel=0.01)
box("Table_Frieze", (TW_ - 0.1, TD_ - 0.1, 0.12), (TX, TY, TH_ - 0.1), M_MAHOGH)
for ex in (-1, 1):
    for ey in (-1, 1):
        lathe(f"Table_Leg{ex}{ey}", [(0, 0), (0.03, 0), (0.035, 0.05), (0.025, 0.12), (0.04, 0.3), (0.028, 0.5), (0.03, 0.6), (0.035, 0.62), (0, 0.62)],
              (TX + ex * (TW_ / 2 - 0.08), TY + ey * (TD_ / 2 - 0.08), 0.0), M_MAHOGH, steps=8)
TZ = TH_
# the papers: the map spread out, the oilskin it came in, the account book open, inkstand and quill, candles
box("Map", (0.50, 0.38, 0.002), (-1.55, 0.05, TZ + 0.001), M_MAP)
box("Oilskin", (0.36, 0.30, 0.006), (-1.95, -0.22, TZ + 0.003), M_OILSKIN, rot=(0, 0, 0.35))
box("AccountBook_L", (0.17, 0.24, 0.025), (-1.20, -0.25, TZ + 0.0125), M_BOOKBOARD, rot=(0, 0, -0.2))
box("AccountBook_R", (0.17, 0.24, 0.02), (-1.035, -0.285, TZ + 0.01), M_BOOKBOARD, rot=(0, 0, -0.2))
box("AccountBook_PagesL", (0.16, 0.23, 0.003), (-1.20, -0.25, TZ + 0.026), M_PAPER, rot=(0, 0, -0.2))
box("AccountBook_PagesR", (0.16, 0.23, 0.003), (-1.035, -0.285, TZ + 0.021), M_PAPER, rot=(0, 0, -0.2))
box("Inkstand", (0.22, 0.14, 0.03), (-2.05, 0.30, TZ + 0.015), M_MAHOGH, bevel=0.005)
for s in (-1, 1): cyl(f"Inkwell{s}", 0.025, 0.05, (-2.05 + s * 0.06, 0.30, TZ + 0.055), M_BRASS, verts=10)
cyl("Quill", 0.003, 0.28, (-1.98, 0.33, TZ + 0.09), M_QUILL, verts=5, rot=(0.0, 1.1, 0.4))
table_tops = [candlestick(f"TableStick{s}", -1.55 + s * 0.42, 0.33, TZ, hh=0.20, cand=0.13) for s in (-1, 1)]
# the tripod table by the squire's chair: pipes, tobacco, decanter and a glass
SX, SY = BREAST_X + 1.55, FIRE_Y - 1.95
lathe("TripodTable_Top", [(0, 0), (0.3, 0), (0.31, 0.015), (0.3, 0.03), (0, 0.03)], (SX, SY, 0.66), M_MAHOGH, steps=20)
lathe("TripodTable_Column", [(0, 0), (0.05, 0), (0.06, 0.08), (0.03, 0.2), (0.045, 0.4), (0.03, 0.55), (0.04, 0.66), (0, 0.66)], (SX, SY, 0.0), M_MAHOGH, steps=10)
for k in range(3):
    a = 2 * math.pi * k / 3
    box(f"TripodTable_Foot{k}", (0.32, 0.04, 0.05), (SX + math.cos(a) * 0.16, SY + math.sin(a) * 0.16, 0.06), M_MAHOGH, rot=(0, 0.25, a))
lathe("Decanter", [(0, 0), (0.06, 0), (0.07, 0.04), (0.068, 0.12), (0.03, 0.18), (0.018, 0.24), (0.025, 0.25), (0, 0.25)], (SX - 0.08, SY + 0.06, 0.69), M_DECANT, steps=14)
lathe("WineGlass", [(0, 0), (0.035, 0), (0.005, 0.01), (0.004, 0.07), (0.03, 0.09), (0.035, 0.13), (0.0, 0.13)], (SX + 0.12, SY - 0.02, 0.69), M_GLASS, steps=12)
for k, (dx, dy, a) in enumerate(((0.05, -0.12, 0.4), (-0.12, -0.1, -0.7))):
    cyl(f"ClayPipeStem{k}", 0.004, 0.32, (SX + dx, SY + dy, 0.695), M_CLAY, verts=5, rot=(0, math.pi / 2, a))
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.012, radius2=0.017, depth=0.035,
                                    location=(SX + dx + math.cos(a) * 0.16, SY + dy + math.sin(a) * 0.16, 0.71))
    K._finish(bpy.context.active_object, M_CLAY, smooth_=True)
lathe("TobaccoJar", [(0, 0), (0.05, 0), (0.055, 0.08), (0.05, 0.1), (0.02, 0.11), (0, 0.12)], (SX + 0.1, SY + 0.12, 0.69), M_BRASS, steps=12)

# the Turkey carpet
box("Carpet", (4.0, 2.9, 0.012), (-1.15, 0.15, 0.006), M_CARPET)

# ----------------------------------------------------------------------------- windows: sashes, shutters, curtains; the door; clock, globe, steps
for i, wy in enumerate(WIN_YS):
    xo = X1 + WT          # outer face
    xs_ = X1 + WT * 0.6   # sash plane
    for k in range(2):    # lower and upper sashes, six panes each (3 x 2)
        z0 = WIN_SILL + 0.03 + k * (WIN_HEAD - WIN_SILL - 0.06) / 2; z1 = z0 + (WIN_HEAD - WIN_SILL - 0.06) / 2
        box(f"Win{i}Glass{k}", (0.006, WIN_W - 0.08, z1 - z0 - 0.06), (xs_ + k * 0.05, wy, (z0 + z1) / 2), M_GLASS)
        for b_ in range(4):
            box(f"Win{i}V{k}{b_}", (0.04, 0.025 if 0 < b_ < 3 else 0.05, z1 - z0), (xs_ + k * 0.05, wy - (WIN_W - 0.08) / 2 + b_ * (WIN_W - 0.08) / 3, (z0 + z1) / 2), M_PANEL)
        for b_ in range(3):
            box(f"Win{i}H{k}{b_}", (0.04, WIN_W - 0.06, 0.025 if b_ == 1 else 0.05), (xs_ + k * 0.05, wy, z0 + b_ * (z1 - z0) / 2), M_PANEL)
    box(f"Win{i}Sill", (WT * 0.7, WIN_W + 0.1, 0.04), (X1 + WT * 0.3, wy, WIN_SILL), M_PANEL, bevel=0.01)
    # shutters folded back into the splayed reveals, panelled
    for s in (-1, 1):
        box(f"Win{i}Shutter{s}", (WT * 0.55, 0.03, WIN_HEAD - WIN_SILL - 0.05), (X1 + WT * 0.28, wy + s * (WIN_W / 2 - 0.02), (WIN_SILL + WIN_HEAD) / 2), M_PANEL)
        box(f"Win{i}Architrave{s}", (0.04, 0.12, WIN_HEAD + 0.1), (X1 - 0.02, wy + s * (WIN_W / 2 + 0.06), (WIN_HEAD + 0.1) / 2), M_PANEL, bevel=0.01)
    box(f"Win{i}ArchHead", (0.04, WIN_W + 0.24, 0.12), (X1 - 0.02, wy, WIN_HEAD + 0.06), M_PANEL, bevel=0.01)
    # curtains: heavy folds drawn to the sides, a pelmet over
    for s in (-1, 1):
        nf, wdt, hgt = 9, 0.42, WIN_HEAD + 0.25
        verts, faces = [], []
        for j in range(nf * 2 + 1):
            t = j / (nf * 2)
            yy = wy + s * (WIN_W / 2 + 0.18) - s * wdt / 2 + s * t * wdt - s * 0.0
            for zz in (0.0, hgt):
                gather = 1.0 if zz > 0 else 0.85
                xx = X1 - 0.14 - 0.075 * (0.5 + 0.5 * math.sin(t * nf * 2 * math.pi)) * gather - (0.06 if zz == 0 else 0)
                verts.append((xx, wy + s * (WIN_W / 2 + 0.2) + s * (t - 0.5) * wdt * gather, zz))
        for j in range(nf * 2):
            faces.append([2 * j, 2 * j + 2, 2 * j + 3, 2 * j + 1])
        from_pydata(f"Win{i}Curtain{s}", verts, faces, M_CURTAIN, smooth_=True)
    box(f"Win{i}Pelmet", (0.16, WIN_W + 1.0, 0.28), (X1 - 0.12, wy, WIN_HEAD + 0.36), M_CURTAIN, bevel=0.02)
# the door, ajar, onto the matted passage
DH = Vector((DOOR_X - DOOR_W / 2 + 0.02, Y0 - 0.05, 0))
ang = math.radians(32)
dd = Vector((math.cos(ang), math.sin(ang), 0))
box("Door", (DOOR_W - 0.04, 0.05, DOOR_H - 0.02), tuple(DH + dd * (DOOR_W - 0.04) / 2 + Vector((0, 0, DOOR_H / 2))), M_OAK, rot=(0, 0, ang))
for k in range(3):
    for e in (0.25, 0.75):
        box(f"DoorPanel{k}{e}", (DOOR_W * 0.36, 0.02, 0.55 if k < 2 else 0.4), tuple(DH + dd * (DOOR_W - 0.04) * e + Vector((0, 0, 0.45 + k * 0.72)) - Vector((-dd.y, dd.x, 0)) * 0.03), M_OAK, rot=(0, 0, ang), bevel=0.01)
for s in (-1, 1):
    box(f"DoorArchitrave{s}", (0.13, 0.05, DOOR_H + 0.12), (DOOR_X + s * (DOOR_W / 2 + 0.065), Y0 + 0.025, (DOOR_H + 0.12) / 2), M_PANEL, bevel=0.01)
box("DoorPediment", (DOOR_W + 0.5, 0.08, 0.12), (DOOR_X, Y0 + 0.04, DOOR_H + 0.18), M_PANEL, bevel=0.02)
# the passage beyond: rush matting, plain walls, dim
PY0 = Y0 - WT
box("Passage_Floor", (2.0, 3.5, 0.02), (DOOR_X, PY0 - 1.7, 0.01), M_MATTING)
for s in (-1, 1): box(f"Passage_Wall{s}", (0.1, 3.5, 3.2), (DOOR_X + s * 0.95, PY0 - 1.75, 1.6), M_PLASTER)
box("Passage_End", (2.0, 0.1, 3.2), (DOOR_X, PY0 - 3.5, 1.6), M_PLASTER)
box("Passage_Ceiling", (2.0, 3.5, 0.1), (DOOR_X, PY0 - 1.75, 3.2), M_CEIL)
# the longcase clock in the south-east corner
CX_, CY_ = X1 - 0.35, Y0 + 0.3
box("Clock_Base", (0.48, 0.30, 0.6), (CX_, CY_, 0.3), M_MAHOGH, bevel=0.01)
box("Clock_Trunk", (0.38, 0.24, 1.15), (CX_, CY_, 1.17), M_MAHOGH, bevel=0.01)
box("Clock_TrunkDoor", (0.26, 0.02, 0.85), (CX_, CY_ + 0.13, 1.17), M_MAHOGH, bevel=0.01)
box("Clock_Hood", (0.50, 0.30, 0.55), (CX_, CY_, 2.03), M_MAHOGH, bevel=0.01)
box("Clock_Dial", (0.32, 0.01, 0.32), (CX_, CY_ + 0.155, 2.0), M_CLOCKFACE)
for k in range(2): box(f"Clock_Hand{k}", (0.008, 0.005, 0.12 - k * 0.04), (CX_, CY_ + 0.162, 2.04 - k * 0.01), M_IRON, rot=(0, 0.6 + k * 2.0, 0))
for s in (-1, 0, 1): bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=5, radius=0.03, location=(CX_ + s * 0.18, CY_, 2.36)); K._finish(bpy.context.active_object, M_BRASS, smooth_=True)
# the terrestrial globe on its stand, by the north window
GX_, GY_ = X1 - 0.95, 2.45
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=14, radius=0.26, location=(GX_, GY_, 1.02), rotation=(0.41, 0, 0))
K._finish(bpy.context.active_object, M_GLOBE, smooth_=True)
bpy.ops.mesh.primitive_torus_add(major_radius=0.29, minor_radius=0.012, major_segments=28, minor_segments=4, location=(GX_, GY_, 1.0), rotation=(0, 0, 0))
K._finish(bpy.context.active_object, M_BRASS, smooth_=True)
lathe("Globe_Stand", [(0, 0), (0.06, 0), (0.05, 0.1), (0.03, 0.4), (0.05, 0.7), (0.0, 0.72)], (GX_, GY_, 0.0), M_MAHOGH, steps=10)
for k in range(3):
    a = 2 * math.pi * k / 3 + 0.3
    box(f"Globe_Foot{k}", (0.36, 0.04, 0.05), (GX_ + math.cos(a) * 0.17, GY_ + math.sin(a) * 0.17, 0.05), M_MAHOGH, rot=(0, 0.2, a))
# ----------------------------------------------------------------------------- outside: the moonlit garden and avenue, the Hall's white wings
box("far.ground", (91.0, 120.0, 0.1), (X1 + 45.5, 0.0, -0.6), M_GOUT)
BARK = Builder("far.avenue", M_BARK)
rt = random.Random(3)
def log(p0, p1, r0, r1, sides=5):
    ax = (p1 - p0); ax.normalize(); s1 = ax.orthogonal().normalized(); s2 = ax.cross(s1)
    vs, fs = [], []
    for p, r in ((p0, r0), (p1, r1)):
        for i in range(sides): a = 2 * math.pi * i / sides; vs.append(p + (s1 * math.cos(a) + s2 * math.sin(a)) * r)
    for i in range(sides): j = (i + 1) % sides; fs.append([i, j, sides + j, sides + i])
    BARK.add(vs, fs)
def tree(p0, d, L, r, depth, maxd):
    p1 = p0 + d * L; log(p0, p1, r, r * 0.68, 5 if depth < 2 else 3)
    if depth >= maxd: return
    for k in range(2 if depth == 0 else 3 if depth < 2 else 2):
        nd = (d + Vector((rt.uniform(-1, 1), rt.uniform(-1, 1), rt.uniform(0.0, 0.8)))).normalized()
        tree(p1, nd, L * rt.uniform(0.62, 0.78), r * 0.6, depth + 1, maxd)
for k in range(9):                                   # the avenue of limes, leafless, two rows going east
    for s in (-1, 1):
        x = X1 + 9.0 + k * 7.0; y = s * 5.0
        tree(Vector((x, y, -0.6)), Vector((0, 0, 1)), 5.0, 0.28, 0, 4 if k < 3 else 3)
BARK.finish(smooth_=True)
# the white line of the Hall buildings on either hand (the wings)
for s in (-1, 1):
    wx0, wx1 = X1 + 4.0, X1 + 34.0
    box(f"far.wing{s}", (wx1 - wx0, 9.0, 9.0), ((wx0 + wx1) / 2, s * 22.0, 3.9), M_STUCCO)
    box(f"far.wingRoof{s}", (wx1 - wx0, 9.4, 1.2), ((wx0 + wx1) / 2, s * 22.0, 9.0), M_FARSLATE)
    for k in range(10):
        for zz in (1.5, 5.0):
            lit = (k * 7 + (1 if s > 0 else 3) + int(zz)) % 11 == 0
            box(f"far.wingWin{s}{k}{zz}", (0.8, 0.1, 1.7), (wx0 + 2.0 + k * 2.9, s * 22.0 - s * 4.52, zz),
                M_FARLIT if lit else M_FARWIN)
def sky_dome(name, radius=60.0, seg=32, rings=12):
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

# ----------------------------------------------------------------------------- lights, living-scene empties, anchors
FIRE_P = Vector((GX, FIRE_Y, 0.22))
light_obj("Lamp.fire", 'POINT', 380.0, (1.0, 0.60, 0.32), (GX + 0.12, FIRE_Y, 0.42), shadow_soft_size=0.12)
light_obj("Lamp.candles", 'POINT', 9.0, (1.0, 0.70, 0.45), (-1.55, 0.33, TZ + 0.38), shadow_soft_size=0.05)
light_obj("Lamp.mantel", 'POINT', 5.0, (1.0, 0.70, 0.45), (BREAST_X + 0.15, FIRE_Y, MZ + 0.45), shadow_soft_size=0.05)
light_obj("Lamp.moon", 'SUN', 0.9, (0.60, 0.70, 1.0), (30, -10, 20), direction=-MOON_DIR, angle=math.radians(0.6))
world = bpy.data.worlds.new("Night"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.02, 0.028, 0.05, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

living_empty("fx.fire.hearth", tuple(FIRE_P + Vector((0, 0, 0.03))), 0.28)
for k, t in enumerate(table_tops): living_empty(f"fx.candle.table{k + 1}", tuple(t), 0.02)
for k, t in enumerate(mantel_tops): living_empty(f"fx.candle.mantel{k + 1}", tuple(t), 0.02)
living_empty("sound.fire.hearth", tuple(FIRE_P + Vector((0.1, 0, 0.2))), 0.3)
living_empty("sound.clock.longcase", (CX_, CY_ + 0.1, 1.6), 0.3)

anchor("reader.entrance", (READER.x, READER.y, 0.0))
fwd = (LOOK_AT - READER); fwd.z = 0; fwd.normalize()
anchor("reader.look", tuple(READER + fwd + Vector((0, 0, EYE))))
anchor("scene.centre", (0.0, 0.0, 0.0))
anchor("library.hearth", (BREAST_X, FIRE_Y, 0.0))
anchor("library.table", (TX, TY, TZ))
anchor("library.window", (X1, WIN_YS[1], WIN_SILL))
anchor("library.door", (DOOR_X, Y0, 0.0))

E = READER + Vector((0, 0, EYE))
PAGE_C = E + fwd * 0.6 - Vector((0, 0, 0.05))
page = box("PagePreview", (0.4, 0.004, 0.55), tuple(PAGE_C), plain("M_PagePreview", (0.80, 0.76, 0.66), rough=0.9), rot=(0, 0, math.atan2(fwd.y, fwd.x) - math.pi / 2))

K.apply_all_transforms()

def yawed(deg, dist=5.0, dz=-0.3):
    a = math.radians(deg); d = Matrix.Rotation(a, 3, 'Z') @ fwd
    return tuple(E + d * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(E), yawed(0, 5.0, -0.25), lens=16),
    camera("Cam_Page", tuple(E), yawed(0, 5.0, -0.25), lens=16),
    camera("Cam_Left", tuple(E), yawed(70, 5.0, -0.45), lens=16),
    camera("Cam_Right", tuple(E), yawed(-80, 5.0, -0.1), lens=16),
    camera("Cam_Behind", tuple(E), yawed(180, 5.0, -0.2), lens=16),
    camera("Cam_Down", tuple(E), (TX + 0.35, TY - 0.1, TZ), lens=20),
    camera("Cam_Fire", (BREAST_X + 2.2, FIRE_Y - 0.4, 1.3), (BREAST_X, FIRE_Y + 0.1, 0.9), lens=24),
    camera("Cam_Map", (TX + 0.15, TY - 0.55, TZ + 0.65), (TX, TY + 0.02, TZ), lens=28),
]
EXPOSURE = {"Cam_Fire": 0.4, "Cam_Map": 0.6}

if not args.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "squires_library_source.blend"))
K.budget()
if args.render:
    K.render_cams(cams, OUT, page=page, page_cams={"Cam_Page"}, exposure=EXPOSURE, default_exposure=1.1, prefix=args.prefix)

if args.bake or args.export:
    T_ = args.tex
    stats = K.bake_and_export(
        "squires_library",
        keep_names={"M_SkyDome": "SkyDome", "M_FarGarden": "far.garden", "M_FarTrees": "far.avenue", "M_FarStucco": "far.wings",
                    "M_FarSlate": "far.roofs", "M_FarWindow": "far.windows", "M_FarWindowLit": "far.windowsLit"},
        size_for={"M_Books": (T_, T_ // 4, T_), "M_Floor": (T_, T_ // 4, T_), "M_Mahogany": (T_, T_ // 4, T_ // 2), "M_Plaster": (T_ // 2, 0, T_ // 4),
                  "M_Ceiling": (T_ // 2, 0, 0), "M_PaintedPanel": (T_ // 2, 0, T_ // 4), "M_MahoganyFurniture": (T_ // 2, T_ // 8, T_ // 2),
                  "M_Carpet": (T_, 0, T_ // 4), "M_Map": (T_ // 2, 0, 0), "M_Marble": (T_ // 2, 0, T_ // 4), "M_BustMarble": (T_ // 4, 0, T_ // 4),
                  "M_ChairLeather": (T_ // 2, T_ // 8, T_ // 4), "M_Curtain": (T_ // 2, 0, T_ // 4), "M_Painting": (T_ // 4, 0, 0),
                  "M_SkyDome": (T_ // 2, 0, 0), "M_FarGarden": (256, 0, 0), "M_FarStucco": (256, 0, 0), "M_Gilt": (T_ // 4, T_ // 8, T_ // 4),
                  "M_OakDoor": (T_ // 4, 0, T_ // 4), "M_Firebox": (T_ // 4, 0, T_ // 4)},
        keep_uv={"SkyDome"}, emit_only={"M_SkyDome"}, remove=[page], default_div=16)
    print("STATS", stats)
print("DONE")
