"""
Fable step-in room: the waist of the schooner Hispaniola on the last evening of the outward voyage (Treasure Island,
chapter 10 "The Voyage" / chapter 11 "What I Heard in the Apple Barrel").

"... it was just after sundown when all my work was over and I was on my way to my berth, it occurred to me that I
should like an apple. I ran on deck. The watch was all forward looking out for the island. The man at the helm was
watching the luff of the sail and whistling away gently to himself, and that was the only sound excepting the swish of
the sea against the bows and around the sides of the ship. In I got bodily into the apple barrel, and found there was
scarce an apple left" ... "there was a barrel of apples standing broached in the waist" ... "All was drawing alow and
aloft" ... "The Hispaniola ... the bowsprit sometimes tasting a little of the spray" ... "Long John's earrings" (the
lines rigged across the deck for him to swing along in a seaway) ... "a long brass nine" (chapter 9).

The main deck of a topsail schooner of some two hundred tons, running before a steady trade wind on the open sea just
after sundown: holystoned planking, oak bulwarks with their rail and timberheads, the main and fore masts with their
gaff sails drawing and the fore topsail and jibs set, tarred shrouds and ratlines, coils on the pins; the broached apple
barrel by the mainmast with scarce an apple left, its lid leaning against it; the long brass nine on its pivot
amidships; the main hatch with its grating, the jolly-boat in its chocks; aft, the companion and the tiller; forward,
the windlass and the bowsprit lifting to the swell. The sea darkens to a deep blue; the western sky still burns low
behind the reader's left shoulder; the first lanterns are lit. No island, no Jolly Roger, no people.

Reader: beside the apple barrel, facing forward along the deck toward the bows.

Living-scene nodes: water.ocean.sea (COLOR_0 G = foam along the hull), cloth.sail.* (R = 0 at the spars, 1 in the
belly), cloth.flag.pennant, fx.lantern.companion, fx.lantern.fore, sound.surf.bow, sound.rigging.main, sound.wind.deck.

  blender -b -P blender/build_hispaniola_deck.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_hispaniola_deck.py -- --render --samples 32 --res 1280 --cams reader,left,right,behind,barrel
  blender -b -P blender/build_hispaniola_deck.py -- --export
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b5 as S
import pride_kit as K
import mobydick_kit as MK
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, MB, anchor, sound, light_obj)

SID = "hispaniola-deck"
ARGS = S.setup(SID, seed=1753)
scene = K.scene
rng = random.Random(1753)

# ship frame = world: +Y forward, +X starboard, deck at the reader z = 0. Water at WL.
Y_STERN, Y_BOW = -13.5, 12.5
WL = -1.75
RAIL = 1.0
MAIN_Y, FORE_Y = -2.6, 6.6
READER = Vector((-1.25, -1.6, 0))
BARREL = Vector((-2.0, -1.05, 0))


def lerp(a, b, t): return a + (b - a) * t
def beam(y):
    """half-breadth at the deck: full amidships, fining to the bow, a broad transom aft"""
    t = (y - Y_STERN) / (Y_BOW - Y_STERN)
    if t > 0.55: return 3.3 * math.sqrt(max(0.0, 1 - ((t - 0.55) / 0.45) ** 2.2)) + 0.08
    return 3.3 - 0.9 * ((0.55 - t) / 0.55) ** 2
def sheer(y): return (0.005 if y > 0 else 0.0025) * y * y
def deck_z(x, y): return sheer(y) + 0.08 * (1 - min(1.0, (x / max(0.3, beam(y))) ** 2))
_z0 = deck_z(READER.x, READER.y)
def dz(x, y): return deck_z(x, y) - _z0
def hb(y, z):
    """half-breadth of the hull at height z (relative to the deck at the side)"""
    s = (z - (WL - 2.6)) / (dz(beam(y), y) + RAIL - (WL - 2.6))
    s = max(0.0, min(1.0, s))
    return beam(y) * (1 - (1 - s) ** 2.4) ** 0.45 * (1 - 0.04 * K.smoothstep(0.85, 1.0, s))

# ----------------------------------------------------------------------------- materials
M_DECK = MK.timber_mat("M_Holystoned", base=(0.62, 0.56, 0.46), dark=(0.36, 0.31, 0.24), light=(0.74, 0.68, 0.58), along='Y', rough=(0.6, 0.85), grime=0.35, seams=('X', 0.14))
M_BULW = MK.timber_mat("M_Bulwark", base=(0.30, 0.24, 0.16), dark=(0.12, 0.09, 0.06), light=(0.42, 0.34, 0.24), along='Y', rough=(0.45, 0.75), grime=0.4)
M_HULL = MK.timber_mat("M_HullBlack", base=(0.05, 0.045, 0.04), dark=(0.02, 0.018, 0.016), light=(0.09, 0.08, 0.07), along='Y', rough=(0.35, 0.6), grime=0.2, seams=('Z', 0.2))
M_RAILC = MK.timber_mat("M_RailCap", base=(0.26, 0.15, 0.07), dark=(0.09, 0.05, 0.025), light=(0.38, 0.24, 0.12), along='Y', rough=(0.3, 0.55), grime=0.2, polish=0.3)
M_SPAR = MK.timber_mat("M_Spars", base=(0.46, 0.34, 0.20), dark=(0.20, 0.14, 0.08), light=(0.58, 0.46, 0.30), along='Z', rough=(0.4, 0.7), grime=0.3)
M_TAR = noisy("M_Tarred", [K.srgb((0.06, 0.05, 0.04)), K.srgb((0.10, 0.08, 0.06))], scale=60, rough=0.6, stretch=(1, 1, 8))
M_MANILA = noisy("M_Manila", [K.srgb((0.56, 0.46, 0.30)), K.srgb((0.46, 0.37, 0.23))], scale=80, rough=0.85, stretch=(1, 1, 8), bump=0.4)
M_IRON = MK.iron_mat("M_Iron", rust=0.3)
M_BRASS = plain("M_GunBrass", K.srgb((0.66, 0.48, 0.22)), rough=0.3, metallic=1.0)
M_BARREL = MK.timber_mat("M_BarrelStaves", base=(0.42, 0.32, 0.20), dark=(0.18, 0.12, 0.07), light=(0.54, 0.43, 0.29), along='Z', rough=(0.5, 0.8), grime=0.4, seams=('X', 0.09))
M_APPLE = noisy("M_Apples", [K.srgb((0.58, 0.20, 0.10)), K.srgb((0.70, 0.46, 0.14)), K.srgb((0.46, 0.14, 0.08))], scale=12, rough=0.45)
M_GLOW = plain("M_LanternGlow", (0.0, 0.0, 0.0), rough=0.5, emission=(1.0, 0.68, 0.34), strength=4.0)


def sail_mat(name="M_Sail"):
    """weathered canvas: cloths (vertical panels) with darker seams, a little grime toward the foot."""
    m, nt, b = new_mat(name)
    uv = node(nt, "ShaderNodeUVMap", (-1500, 0)); s = sep_xyz(nt, uv.outputs["UV"], (-1300, 0))
    fr = math_(nt, 'FRACT', math_(nt, 'MULTIPLY', s.outputs["X"], 18.0, (-1100, 100)), None, (-1000, 100))
    seam = maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', fr, 0.5, (-900, 100)), None, (-800, 100)), 0.44, 0.5, 1.0, 0.82, (-700, 100))
    n = noise_(nt, obj_coords(nt, (-1500, -300)), 0.6, 5, 0.6, loc=(-1100, -300))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-900, -300)), c4(K.srgb((0.82, 0.78, 0.68))), c4(K.srgb((0.90, 0.87, 0.78))), (-700, -200))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, seam, (-500, 0))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, s.outputs["Y"], 0.0, 0.25, 0.25, 0.0, (-700, -500)), col, (0.7, 0.66, 0.58, 1), (-350, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    b.inputs["Sheen Weight"].default_value = 0.3
    m.use_backface_culling = False
    return m
M_SAIL = sail_mat()


def sea_mat(name="M_Sea"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    a = node(nt, "ShaderNodeAttribute", (-900, 300)); a.attribute_name = "sway"
    sp = node(nt, "ShaderNodeSeparateColor", (-700, 300)); nt.links.new(a.outputs["Color"], sp.inputs[0])
    n = noise_(nt, co, 0.08, 4, 0.6, loc=(-900, 0))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-700, 0)), (0.010, 0.025, 0.05, 1), (0.02, 0.04, 0.07, 1), (-500, 0))
    col = mix_rgb(nt, 'MIX', sp.outputs["Green"], col, (0.6, 0.64, 0.66, 1), (-300, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.08
    w = noise_(nt, co, 0.5, 5, 0.6, loc=(-900, -300)); bump_from(nt, b, w.outputs["Fac"], 0.35, 0.2)
    return m
M_SEA = sea_mat()

# ----------------------------------------------------------------------------- hull, deck, bulwarks
NY = 52
ys = [lerp(Y_STERN, Y_BOW, (1 - math.cos(math.pi * i / NY)) / 2) for i in range(NY + 1)]
# the deck
dv = []; df = []
NX = 10
for y in ys:
    w = beam(y) - 0.12
    for i in range(NX + 1):
        x = lerp(-w, w, i / NX); dv.append((x, y, dz(x, y)))
for j in range(NY):
    for i in range(NX): df.append((j * (NX + 1) + i, j * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i))
mesh_from("Deck", dv, df, M_DECK)
# the outer hull (seen over the rail and from the bulwark top), both sides, the transom
for side in (-1, 1):
    hv = []; hf = []
    NS = 8
    for y in ys:
        top = dz(beam(y), y) + RAIL
        for j in range(NS + 1):
            z = lerp(WL - 2.6, top, j / NS)
            hv.append((side * hb(y, z), y, z))
    for i in range(NY):
        for j in range(NS):
            a = i * (NS + 1) + j; b2 = a + NS + 1
            hf.append((a, b2, b2 + 1, a + 1) if side > 0 else (a, a + 1, b2 + 1, b2))
    mesh_from(f"Hull{side}", hv, hf, M_HULL, smooth=True)
    # inside face of the bulwarks, the rail cap, timberheads, pin rails
    iv = []; iff = []
    for y in ys[1:-1]:
        b_ = beam(y) - 0.1
        iv += [(side * b_, y, dz(b_, y) - 0.02), (side * b_, y, dz(b_, y) + RAIL - 0.06)]
    for i in range(len(ys) - 3): iff.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) if side < 0 else (2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    mesh_from(f"BulwarkInner{side}", iv, iff, M_BULW)
    rail = [Vector((side * (beam(y) - 0.06), y, dz(beam(y), y) + RAIL)) for y in ys[1:-1]]
    tube(f"RailCap{side}", rail, 0.07, M_RAILC, sides=4)
    y = Y_STERN + 0.8
    while y < Y_BOW - 1.2:
        b_ = beam(y) - 0.12
        box(f"Timberhead{side}{y:.1f}", (0.12, 0.12, RAIL), (side * b_, y, dz(b_, y) + (RAIL) / 2), M_BULW)
        y += 1.1
    for my, n_ in ((MAIN_Y, 7), (FORE_Y, 6)):
        b_ = beam(my + 0.5) - 0.22
        box(f"PinRail{side}{my}", (0.14, 2.0, 0.06), (side * b_, my + 0.6, dz(b_, my) + 0.62), M_RAILC)
        for k in range(n_):
            cyl(f"Pin{side}{my}{k}", 0.014, 0.3, (side * b_, my - 0.3 + 0.3 * k, dz(b_, my) + 0.62), M_RAILC, verts=6)
            if k % 2 == 0:   # a coil hanging on the pin
                lathe(f"Coil{side}{my}{k}", [(0.0, 0.0), (0.13, 0.0), (0.14, 0.02), (0.13, 0.04), (0.0, 0.04)], (side * (b_ - 0.06), my - 0.3 + 0.3 * k, dz(b_, my) + 0.25),
                      M_MANILA, steps=10, rot=(0, math.pi / 2, 0))
tv = []
for z in (WL - 0.6, dz(beam(Y_STERN), Y_STERN) + RAIL + 0.1):
    w = hb(Y_STERN, min(z, dz(beam(Y_STERN), Y_STERN) + RAIL))
    tv += [(-w, Y_STERN, z), (w, Y_STERN, z)]
mesh_from("Transom", tv, [(0, 1, 3, 2)], M_HULL)
box("TaffrailInner", (2 * beam(Y_STERN) - 0.3, 0.08, RAIL), (0, Y_STERN + 0.06, dz(0, Y_STERN) + (RAIL) / 2), M_BULW)

# ----------------------------------------------------------------------------- masts, booms, gaffs, bowsprit
def mast(name, y, d, h, rake=0.06):
    base = Vector((0, y, dz(0, y) - 0.1)); top = base + Vector((0, -h * rake, h))
    tube(name, [base, base.lerp(top, 0.5), top], [d / 2, d * 0.45, d * 0.32], M_SPAR, sides=12)
    for k in range(3): cyl(f"{name}Hoop{k}", d / 2 + 0.01, 0.04, tuple(base.lerp(top, 0.06 + 0.04 * k)), M_IRON, verts=12)
    return base, top
MB_, MT = mast("MainMast", MAIN_Y, 0.42, 22.0)
FB_, FT = mast("ForeMast", FORE_Y, 0.38, 19.0)
cyl("ForeTopmast", 0.1, 8.0, tuple(FT + Vector((0, -0.2, 3.2))), M_SPAR, verts=8, r2=0.06)
FTT = FT + Vector((0, -0.25, 7.2))
cyl("MainTopmast", 0.09, 6.0, tuple(MT + Vector((0, -0.2, 2.4))), M_SPAR, verts=8, r2=0.05)
MTT = MT + Vector((0, -0.25, 5.4))
box("MainTrestle", (1.1, 0.5, 0.08), tuple(MT + Vector((0, 0, -0.7))), M_SPAR)
box("ForeTrestle", (1.0, 0.45, 0.08), tuple(FT + Vector((0, 0, -0.7))), M_SPAR)
BOW_TIP = Vector((0, Y_BOW + 8.0, dz(0, Y_BOW) + 2.2))
tube("Bowsprit", [Vector((0, Y_BOW - 2.0, dz(0, Y_BOW - 2) + 0.4)), Vector((0, Y_BOW + 2.0, dz(0, Y_BOW) + 1.2)), BOW_TIP], [0.2, 0.17, 0.08], M_SPAR, sides=10)
# booms and gaffs swung out to starboard (the wind on the port quarter); main boom over the taffrail
SWING = math.radians(28)
def spar(name, a, length, ang_out, rise, r0, r1):
    d = Vector((math.sin(ang_out), -math.cos(ang_out), rise)).normalized()
    b_ = a + d * length
    tube(name, [a, a.lerp(b_, 0.5), b_], [r0, r0 * 0.9, r1], M_SPAR, sides=8)
    return b_
MBOOM0 = MB_ + Vector((0, -0.25, 2.3)); MBOOM1 = spar("MainBoom", MBOOM0, 13.0, SWING, 0.05, 0.12, 0.09)
MGAFF0 = MB_ + Vector((0, -0.25 - 21.0 * 0.06 * 0.85, 18.0)); MGAFF1 = spar("MainGaff", MGAFF0, 9.5, SWING + 0.12, 0.42, 0.1, 0.06)
FBOOM0 = FB_ + Vector((0, -0.25, 2.2)); FBOOM1 = spar("ForeBoom", FBOOM0, 7.4, SWING, 0.03, 0.1, 0.08)
FGAFF0 = FB_ + Vector((0, -0.25 - 19 * 0.06 * 0.8, 15.5)); FGAFF1 = spar("ForeGaff", FGAFF0, 6.5, SWING + 0.12, 0.4, 0.09, 0.06)
# the fore topsail yard (square), braced round
YD_C = FT + Vector((0, -0.25, 3.8)); yd = Vector((math.cos(SWING * 0.8), math.sin(SWING * 0.8), 0))
tube("ForeTopsailYard", [YD_C - yd * 5.2, YD_C, YD_C + yd * 5.2], [0.05, 0.1, 0.05], M_SPAR, sides=8)
YD2 = FT + Vector((0, -0.25, 0.4))
tube("ForeYard", [YD2 - yd * 6.4, YD2, YD2 + yd * 6.4], [0.06, 0.13, 0.06], M_SPAR, sides=8)

# ----------------------------------------------------------------------------- sails, drawing: curved cloth surfaces between their spars (cloth.sail)
def sail(name, corners, belly, normal_side, nu=10, nv=10, uv_flip=False):
    """corners: (tack/foot-forward, clew/foot-aft, peak/head-aft, throat/head-forward) as world points; a bilinear patch
    pushed out by `belly` (max metres) along normal_side * the patch normal, most in the middle and toward the leech."""
    A, B_, C, D = [Vector(c) for c in corners]
    vs = []; fs = []; uvs = []; ws = []
    nrm = (B_ - A).cross(D - A).normalized() * normal_side
    for j in range(nv + 1):
        v = j / nv
        for i in range(nu + 1):
            u = i / nu
            p = (A.lerp(B_, u)).lerp(D.lerp(C, u), v)
            w = math.sin(math.pi * u) ** 0.9 * math.sin(math.pi * min(1.0, v * 0.95 + 0.05)) ** 0.7
            p = p + nrm * belly * w
            vs.append(tuple(p)); uvs.append((u, v)); ws.append(w)
    for j in range(nv):
        for i in range(nu): fs.append((j * (nu + 1) + i, j * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i))
    o = mesh_from(name, vs, fs, M_SAIL, smooth=True, uvs=uvs)
    o.data.uv_layers[0].name = "UVMap"
    ca = o.data.color_attributes.new("sway", 'BYTE_COLOR', 'POINT')
    for i, w in enumerate(ws): ca.data[i].color = (w, 1, 1, 1)
    return o
mast_x = lambda base, top, t: base.lerp(top, t)
sail("SailMain", (MBOOM0 + Vector((0, 0, 0.15)), MBOOM1 + Vector((0, 0, 0.15)), MGAFF1, MGAFF0 - Vector((0, 0, 0.2))), 1.3, 1)
sail("SailFore", (FBOOM0 + Vector((0, 0, 0.15)), FBOOM1 + Vector((0, 0, 0.15)), FGAFF1, FGAFF0 - Vector((0, 0, 0.2))), 0.9, 1)
sail("SailForeTopsail", (YD2 - yd * 6.0 + Vector((0, 0, 0.1)), YD2 + yd * 6.0 + Vector((0, 0, 0.1)), YD_C + yd * 5.0, YD_C - yd * 5.0), 1.0, 1)
JIB_HEAD = FT + Vector((0, 0, -0.3))
sail("SailJib", (BOW_TIP - Vector((0, 0.6, 0.15)), Vector((2.4, FORE_Y + 3.0, dz(0, FORE_Y) + 2.2)), JIB_HEAD + Vector((0.05, 0.1, 0)), JIB_HEAD), 0.7, -1)
sail("SailForestaysail", (Vector((0, Y_BOW - 0.4, dz(0, Y_BOW) + 1.0)), Vector((1.6, FORE_Y + 0.9, dz(0, FORE_Y) + 1.8)), FT + Vector((0.05, 0.3, -2.5)), FT + Vector((0, 0.25, -2.6))), 0.55, -1)
# a pennant at the main truck streaming forward (cloth.flag)
pv = []; pf = []
for i in range(9):
    t = i / 8; p = MTT + Vector((0.25 * math.sin(t * 3), 3.2 * t, -0.25 * t + 0.08 * math.sin(t * 7)))
    w = 0.22 * (1 - t) + 0.02
    pv += [tuple(p + Vector((0, 0, w / 2))), tuple(p - Vector((0, 0, w / 2)))]
    if i: pf.append((2 * i - 2, 2 * i, 2 * i + 1, 2 * i - 1))
pen = mesh_from("Pennant", pv, pf, plain("M_Pennant", K.srgb((0.62, 0.12, 0.10)), rough=0.8))
K.add_sway(pen, lambda p: min(1.0, max(0.0, (p.y - MTT.y) / 3.2)))
pen.data.materials[0].use_backface_culling = False

# ----------------------------------------------------------------------------- standing and running rigging
def rope(name, a, b_, r=0.016, sag=0.0, mat=None):
    a = Vector(a); b_ = Vector(b_); m_ = (a + b_) / 2 - Vector((0, 0, sag))
    return tube(name, [a, m_, b_] if sag else [a, b_], r, mat or M_TAR, sides=4, caps=False)
for nm, base, top, n_ in (("Main", MB_, MT, 4), ("Fore", FB_, FT, 4)):
    for side in (-1, 1):
        ends = []
        for i in range(n_):
            y = base.y - 0.6 + 0.55 * i
            foot = Vector((side * (beam(y) + 0.18), y, dz(beam(y), y) + 0.35))
            head = top + Vector((side * 0.22, 0, -0.9))
            rope(f"{nm}Shroud{side}{i}", foot, head, 0.022)
            cyl(f"{nm}Deadeye{side}{i}", 0.07, 0.06, tuple(foot - Vector((0, 0, 0.12))), M_BULW, verts=8, rot=(0, math.pi / 2, 0))
            ends.append((foot, head))
        box(f"{nm}Channel{side}", (0.3, 2.6, 0.08), (side * (beam(base.y) + 0.15), base.y + 0.3, dz(beam(base.y), base.y) + 0.12), M_BULW)
        L = (ends[0][1] - ends[0][0]).length; h = 0.45
        while h < L * 0.8:
            t = h / L; pts = [a.lerp(b2, t) for (a, b2) in ends]
            tube(f"{nm}Ratline{side}{h:.1f}", pts, 0.008, M_TAR, sides=3, caps=False)
            h += 0.42
rope("ForeStay", FT + Vector((0, 0, -0.8)), BOW_TIP + Vector((0, -2.0, -0.6)), 0.028, 0.1)
rope("JibStay", FT + Vector((0, 0, -0.3)), BOW_TIP, 0.02, 0.15)
rope("MainStay", MT + Vector((0, 0, -0.8)), FB_ + Vector((0, 0, 2.6)), 0.026, 0.2)
rope("TopmastStay", MTT, FTT + Vector((0, 0, -0.8)), 0.016, 0.2)
rope("ForeTopStay", FTT, BOW_TIP, 0.016, 0.3)
for side in (-1, 1):
    rope(f"MainBackstay{side}", MTT, Vector((side * (beam(MAIN_Y - 4) + 0.15), MAIN_Y - 4.0, dz(beam(MAIN_Y - 4), MAIN_Y - 4) + 0.4)), 0.014)
# sheets, halliards, topping lifts, braces (manila)
rope("MainSheet", MBOOM1 + Vector((0, 0, -0.05)), Vector((0.6, Y_STERN + 1.5, dz(0, Y_STERN + 1.5) + 0.3)), 0.014, 0.4, M_MANILA)
rope("ForeSheet", FBOOM1, Vector((beam(FORE_Y - 6) - 0.3, FORE_Y - 6.0, dz(0, FORE_Y - 6) + 0.6)), 0.012, 0.3, M_MANILA)
rope("MainPeakHalliard", MT + Vector((0, 0, -0.4)), MGAFF0.lerp(MGAFF1, 0.6), 0.012, 0.0, M_MANILA)
rope("MainThroatHalliard", MT + Vector((0, 0, -0.6)), MGAFF0, 0.012, 0.0, M_MANILA)
rope("MainTopLift", MT + Vector((0, 0, -0.5)), MBOOM1, 0.01, 0.0, M_MANILA)
rope("ForePeakHalliard", FT + Vector((0, 0, -0.4)), FGAFF0.lerp(FGAFF1, 0.6), 0.012, 0.0, M_MANILA)
rope("JibSheet", Vector((2.4, FORE_Y + 3.0, dz(0, FORE_Y) + 2.2)), Vector((beam(FORE_Y + 1) - 0.2, FORE_Y + 1.0, dz(0, FORE_Y) + 1.0)), 0.01, 0.1, M_MANILA)
for side in (-1, 1):
    rope(f"TopsailBrace{side}", YD_C + yd * side * 5.0, Vector((side * (beam(MAIN_Y) - 0.15), MAIN_Y - 0.5, dz(0, MAIN_Y) + RAIL)), 0.01, 0.6, M_MANILA)
    rope(f"YardBrace{side}", YD2 + yd * side * 6.2, Vector((side * (beam(MAIN_Y + 1) - 0.15), MAIN_Y + 1.0, dz(0, MAIN_Y) + RAIL)), 0.012, 0.5, M_MANILA)
# "Long John's earrings": lines rigged across the deck, a little slack, between the bulwarks
for k, y in enumerate((0.8, 3.2, -5.5)):
    rope(f"Earring{k}", Vector((-(beam(y) - 0.08), y, dz(0, y) + RAIL + 0.05)), Vector((beam(y) - 0.08, y + 0.2, dz(0, y) + RAIL + 0.05)), 0.013, 0.35, M_MANILA)

# ----------------------------------------------------------------------------- deck furniture: the apple barrel, the long brass nine, hatch, boat, windlass, companion, tiller
# the barrel: staves bulging, iron hoops, broached (head off, leaning against it), scarce an apple left
BH = 1.05
lathe("AppleBarrel", [(0.0, 0.02), (0.30, 0.0), (0.34, 0.15), (0.37, 0.5), (0.36, 0.8), (0.32, BH), (0.29, BH), (0.33, 0.8), (0.34, 0.5), (0.31, 0.15), (0.26, 0.06), (0.0, 0.06)],
      tuple(BARREL), M_BARREL, steps=24)
for k, z in enumerate((0.08, 0.25, 0.8, 0.97)):
    r_ = 0.3 + 0.07 * math.sin(math.pi * z / BH) + 0.012
    tube(f"BarrelHoop{k}", [tuple(BARREL + Vector((r_ * math.cos(a), r_ * math.sin(a), z))) for a in [2 * math.pi * q / 20 for q in range(21)]], 0.012, M_IRON, sides=4)
for k in range(4):
    a = rng.uniform(0, 6.28); rr = rng.uniform(0.0, 0.18)
    sphere(f"Apple{k}", 0.04, tuple(BARREL + Vector((rr * math.cos(a), rr * math.sin(a), 0.1))), M_APPLE, seg=10)
HD = Frame((BARREL.x - 0.15, BARREL.y + 0.45), math.radians(25))
cyl("BarrelHead", 0.29, 0.04, HD.p(0, 0, 0.3), M_BARREL, verts=20, rot=(math.radians(75), 0, HD.yaw))
anchor("scene.appleBarrel", tuple(BARREL))
# the main hatch with its grating, forward of the mainmast
HX, HY = 0.0, MAIN_Y + 2.6
box("HatchCoaming", (1.7, 1.5, 0.32), (HX, HY, dz(0, HY) - 0.05 + (0.32) / 2), M_BULW, bevel=0.02)
for k in range(9): box(f"GratingX{k}", (1.6, 0.03, 0.05), (HX, HY - 0.64 + 0.16 * k, dz(0, HY) + 0.27), M_RAILC)
for k in range(10): box(f"GratingY{k}", (0.03, 1.4, 0.04), (HX - 0.72 + 0.16 * k, HY, dz(0, HY) + 0.27), M_RAILC)
# the jolly-boat in its chocks on the hatch's after side? (amidships, to starboard)
BT = Vector((1.5, MAIN_Y + 5.0, dz(0, MAIN_Y + 5) + 0.25))
bv = []; bf = []
for i in range(11):
    t = i / 10; y = BT.y - 2.0 + 4.0 * t; w = 0.65 * math.sin(math.pi * min(1, 0.08 + t * 0.92)) ** 0.6
    for j in range(5):
        a = math.pi * j / 4; bv.append((BT.x + w * math.cos(a) * -1, y, BT.z + 0.55 - 0.5 * math.sin(a) * (0.5 + 0.5 * math.sin(math.pi * t))))
for i in range(10):
    for j in range(4): bf.append((i * 5 + j, i * 5 + j + 1, (i + 1) * 5 + j + 1, (i + 1) * 5 + j))
bo = mesh_from("JollyBoat", bv, bf, plain("M_BoatPaint", K.srgb((0.30, 0.36, 0.30)), rough=0.6), smooth=True); bo.modifiers.new("S", 'SOLIDIFY').thickness = 0.03
for k in range(3): box(f"BoatThwart{k}", (1.0, 0.18, 0.04), (BT.x, BT.y - 1.0 + k, BT.z + 0.35), M_BULW)
for k in (-1.2, 1.2): box(f"Chock{k}", (1.2, 0.2, 0.25), (BT.x, BT.y + k, BT.z - 0.25 + (0.25) / 2), M_BULW)
# the long brass nine on its pivot carriage amidships, to port
GN = Frame((-1.0, MAIN_Y + 4.3), math.radians(-90 + 15), z=dz(0, MAIN_Y + 4.3))
GN.box("GunSlide", (0.5, 2.0, 0.18), (0, 0, 0.05 + (0.18) / 2), M_BULW, bevel=0.02)
GN.box("GunCarriage", (0.5, 0.8, 0.35), (0, 0.1, 0.23 + (0.35) / 2), M_BULW, bevel=0.02)
cyl("GunPivot", 0.1, 0.1, GN.p(0, -0.6, 0.0), M_IRON, verts=10)
gb = [Vector(GN.p(0, -0.45, 0.68)), Vector(GN.p(0, 0.6, 0.66)), Vector(GN.p(0, 1.85, 0.64))]
tube("GunBarrel", gb, [0.19, 0.15, 0.11], M_BRASS, sides=14)
sphere("GunCascabel", 0.06, GN.p(0, -0.6, 0.68), M_BRASS, seg=10)
for k, t in enumerate((0.15, 0.55, 0.98)): cyl(f"GunReinforce{k}", 0.17 - 0.04 * t, 0.06, tuple(gb[0].lerp(gb[2], t)), M_BRASS, verts=14, rot=(math.pi / 2, 0, GN.yaw))
anchor("ship.longNine", GN.p(0, 0, 0))
# the windlass forward, the companion and the tiller aft, water casks lashed by the mainmast
WD = Vector((0, Y_BOW - 3.2, dz(0, Y_BOW - 3.2)))
tube("Windlass", [WD + Vector((-1.1, 0, 0.5)), WD + Vector((1.1, 0, 0.5))], 0.2, M_BULW, sides=8)
for sx in (-1, 1): box(f"WindlassBitt{sx}", (0.25, 0.3, 0.9), tuple(WD + Vector((sx * 1.2, 0, 0.45))), M_BULW, bevel=0.02)
CP = Vector((0, -8.5, dz(0, -8.5)))
box("Companion", (1.3, 1.5, 1.2), tuple(CP + Vector((0, 0, 0.6))), M_BULW, bevel=0.02)
box("CompanionHood", (1.4, 1.6, 0.12), tuple(CP + Vector((0, 0, 1.26))), M_RAILC, bevel=0.03)
box("CompanionDoor", (0.6, 0.04, 1.0), tuple(CP + Vector((0, 0.76, 0.55))), M_RAILC)
box("Skylight", (1.0, 1.3, 0.45), tuple(CP + Vector((0, -2.0, 0.225))), M_BULW, bevel=0.02)
box("SkylightLid", (1.1, 1.4, 0.08), tuple(CP + Vector((0, -2.0, 0.49))), plain("M_SkylightGlass", K.srgb((0.1, 0.12, 0.13)), rough=0.1), bevel=0.01)
TL = Vector((0, Y_STERN + 0.8, dz(0, Y_STERN + 0.8)))
cyl("RudderHead", 0.16, 0.6, tuple(TL + Vector((0, 0, 0.3))), M_BULW, verts=10)
tube("Tiller", [TL + Vector((0, 0, 0.55)), TL + Vector((0.05, 1.4, 0.75)), TL + Vector((0.12, 2.6, 0.82))], [0.07, 0.055, 0.04], M_RAILC, sides=8)
box("Binnacle", (0.5, 0.4, 0.95), tuple(TL + Vector((0, 3.4, 0.475))), M_RAILC, bevel=0.03)
LANT_C = CP + Vector((0.5, 0.85, 1.05)); LANT_F = Vector((-(beam(FORE_Y) - 0.3), FORE_Y, dz(0, FORE_Y) + 1.7))
for k, p in enumerate((LANT_C, LANT_F, TL + Vector((0, 3.4, 1.05)))):
    lathe(f"Lantern{k}", [(0.0, 0.0), (0.07, 0.0), (0.06, 0.22), (0.04, 0.28), (0.0, 0.3)], tuple(p), M_IRON, steps=8)
    cyl(f"LanternGlow{k}", 0.055, 0.16, tuple(p + Vector((0, 0, 0.11))), M_GLOW, verts=8)
for k in range(3):
    c = Vector((1.0, MAIN_Y - 0.9 - 0.75 * k, dz(1.0, MAIN_Y)))
    lathe(f"WaterCask{k}", [(0.0, 0.0), (0.24, 0.0), (0.29, 0.25), (0.24, 0.5), (0.0, 0.5)], tuple(c + Vector((0, 0, 0.26))), M_BARREL, steps=14, rot=(0, math.pi / 2, 0))
lathe("RopeCoilDeck", [(0.0, 0.0), (0.4, 0.0), (0.42, 0.05), (0.4, 0.1), (0.2, 0.1), (0.0, 0.08)], (-0.6, MAIN_Y - 1.2, dz(-0.6, MAIN_Y - 1.2)), M_MANILA, steps=16)

# ----------------------------------------------------------------------------- the sea: a broad disc round the ship with foam along the hull (water.ocean)
sv = []; sf = []; foam = []
NA = 72; rings = [0.0, 0.6, 1.5, 3, 6, 12, 25, 50, 100, 220, 450, 900]
def hull_d(x, y):
    yy = max(Y_STERN, min(Y_BOW, y)); return abs(x) - hb(yy, WL) if Y_STERN <= y <= Y_BOW + 0.5 else math.hypot(abs(x) - 0, (y - (Y_BOW if y > 0 else Y_STERN)))
for j, rr in enumerate(rings):
    for i in range(NA):
        a = 2 * math.pi * i / NA
        # an ellipse round the hull, expanding outward
        x = (3.5 + rr) * math.cos(a); y = 0.5 + (14.5 + rr) * math.sin(a)
        z = WL + 0.25 * math.sin(x * 0.12 + y * 0.05) * K.smoothstep(4, 30, rr)
        sv.append((x, y, z)); foam.append(math.exp(-rr / 2.0) * (1.0 if j < 4 else 0.0))
for j in range(len(rings) - 1):
    for i in range(NA): sf.append((j * NA + i, j * NA + (i + 1) % NA, (j + 1) * NA + (i + 1) % NA, (j + 1) * NA + i))
sea = mesh_from("water.ocean.sea", sv, sf, M_SEA, smooth=True)
ul = sea.data.uv_layers.new(name="UVMap")
for li, l in enumerate(sea.data.loops): ul.data[li].uv = (sv[l.vertex_index][0] / 10, sv[l.vertex_index][1] / 10)
ca = sea.data.color_attributes.new("sway", 'BYTE_COLOR', 'POINT')
for i, f_ in enumerate(foam): ca.data[i].color = (0.0, f_, 0.0, 1)
# a little bow wave
for side in (-1, 1):
    wv = []; wf = []
    for i in range(8):
        t = i / 7; y = Y_BOW - 1.0 - 6 * t; x = side * (hb(y, WL) + 0.05 + 0.6 * t)
        wv += [(side * (hb(y, WL) - 0.02), y, WL + 0.03), (x, y - 0.3, WL + 0.12 * (1 - t) + 0.01)]
        if i: wf.append((2 * i - 2, 2 * i, 2 * i + 1, 2 * i - 1))
    mesh_from(f"BowWave{side}", wv, wf, plain("M_Foam", K.srgb((0.78, 0.80, 0.80)), rough=0.6) if side < 0 else bpy.data.materials["M_Foam"])

# ----------------------------------------------------------------------------- the dusk sky, the afterglow, light
SUNSET = Vector((-0.75, -0.62, -0.04)).normalized()          # just below the horizon behind the reader's left shoulder
M_SKY = S.sky_mat("M_SkyDome", SUNSET, zenith=(0.05, 0.08, 0.20), mid=(0.16, 0.22, 0.40), horizon=(0.62, 0.44, 0.40), cloud=0.35,
                  cloud_lit=(0.95, 0.52, 0.36), cloud_shade=(0.20, 0.20, 0.30), sun_glow=(1.0, 0.45, 0.18), haze_low=(0.30, 0.28, 0.34), clear_dir=(0, 1, 0.2))
S.sky_dome(M_SKY, radius=1000.0)
light_obj("Lamp.afterglow", 'SUN', 0.5, (1.0, 0.62, 0.42), (0, 0, 40), direction=tuple(-Vector((SUNSET.x, SUNSET.y, 0.08)).normalized()), angle=math.radians(8))
for k, p in enumerate((LANT_C, LANT_F, TL + Vector((0, 3.4, 1.05)))):
    light_obj(f"Lamp.lantern{k}", 'POINT', 6.0, (1.0, 0.66, 0.34), tuple(p + Vector((0, 0, 0.12))), shadow_soft_size=0.05)
world = bpy.data.worlds.new("Dusk"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.16, 0.20, 0.34, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8

# ----------------------------------------------------------------------------- anchors, sources
S.reader(READER, (0, 1))
anchor("scene.centre", (0, MAIN_Y, 0))
anchor("ship.bow", (0, Y_BOW, 0)); anchor("ship.helm", tuple(TL))
S.fx("fx.lantern.companion", tuple(LANT_C + Vector((0, 0, 0.12))), 0.04)
S.fx("fx.lantern.fore", tuple(LANT_F + Vector((0, 0, 0.12))), 0.04)
S.fx("fx.lantern.binnacle", tuple(TL + Vector((0, 3.4, 1.17))), 0.04)
sound("surf", "bow", (0.0, Y_BOW + 1.0, WL))
sound("surf", "side", (-3.6, -2.0, WL))
sound("rigging", "main", (0.0, MAIN_Y, 8.0))
sound("wind", "deck", (0.0, 4.0, 3.0))
page = S.page_preview()
K.apply_transforms()

E = READER + Vector((0, 0, S.EYE))
cams = S.eye_cams([("Reader", 0), ("Left", -80), ("Right", 80), ("Behind", 180)], dz=0.6, dist=8.0, extra=[
    ("Page", E, E + Vector((0, 8, 0.6)), 17),
    ("Barrel", BARREL + Vector((1.2, 1.4, 1.6)), BARREL + Vector((0, 0, 0.7)), 26),
    ("Up", E, E + Vector((1.5, 4.0, 6.0)), 17),
])
probs = S.check_reader(ignore=("PagePreview",))
K.print_budget(exclude=("PagePreview",))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=1.2, captures_dir=ARGS.captures)

if ARGS.export or ARGS.bake:
    S.export(SID, cams, page=page, unlit_emit=("M_LanternGlow",),
             keep_names={"M_Sea": "water.ocean.sea", "M_Sail": "cloth.sail.set", "M_Pennant": "cloth.flag.pennant", "M_LanternGlow": "MESH_LanternGlow"},
             size_for={"M_Holystoned": (2048, 128, 1024), "M_Bulwark": (1024, 64, 512), "M_HullBlack": (1024, 64, 512), "M_RailCap": (1024, 64, 512),
                       "M_Spars": (1024, 64, 512), "M_Sail": (2048, 64, 512), "M_SkyDome": (2048,), "M_Sea": (1024, 32, 256), "M_BarrelStaves": (512, 64, 256),
                       "M_Tarred": (256, 32, 64), "M_Manila": (256, 32, 64)},
             default_size=(256, 32, 128))
print("DONE")
