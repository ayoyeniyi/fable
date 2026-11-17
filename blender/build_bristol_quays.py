"""
Fable step-in room `bristol-quays`: the working quays of Bristol on a clear March morning in the 1750s (Treasure
Island, Chapter VII, "I Go to Bristol").

"... the squire, who was lodging at an inn far down the docks ... Our way lay along the quays and beside the great
multitude of ships of all sizes and rigs and nations. In one, sailors were singing at their work; in another there
were men aloft, high over my head, hanging to threads that seemed no thicker than a spider's. Though I had lived by
the shore all my life, I seemed never to have been near the sea till then. The smell of tar and salt was something
new. I saw the most wonderful figureheads, that had all been far over the ocean."

The reader stands on the wet granite setts of the quay, a few metres from its edge, facing the water. The ships lie
moored bow-on to the quay, as at Bristol, close together: their stems, carved and painted heads and bowsprits
reaching out over the quayside above the reader's head, the figureheads (a crowned lion, a scroll-head) looking down,
the rigging and yards rising high overhead; across the harbour, more ships and the warehouses and a church tower of
the far bank. Behind the reader, the brick and timber-framed fronts of warehouses and the squire's large inn, with
its door at the end of the strip; along the quay, a cart, bales, barrels, coils of rope and old cannon set as
bollards. Clear morning light well after dawn. No people (the sailors are heard, not seen), no Spy-glass sign, no
Hispaniola by name, no Silver or parrot, nothing modern.

Run (from the repo root), one Blender job at a time through the shared slot wrapper:
  blender_slot.sh -b -P blender/build_bristol_quays.py -- --cpu --render --samples 40 --res 1280
  blender_slot.sh -b -P blender/build_bristol_quays.py -- --export
  then blender/runtime_bake.py and tools/publish_scene_room.py (docs/SCENE_ROOMS_PIPELINE.md)
Axes: metres, +Z up; the quay edge runs along x at y = 3.5, the water is +Y; the quay top is z = 0, the water z = -1.9.
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b3 as K
import roomkit as rk
import pride_kit as pk

ARGS = K.setup("bristol-quays", seed=1750, samples=40)
if ARGS.cpu: bpy.context.scene.cycles.device = 'CPU'
R = random.Random(1750)
WATER_Z = -1.9
EDGE = 3.5

# ----------------------------------------------------------------------------- materials
SETTS = K.ashlar_mat("granite_setts", (0.42, 0.40, 0.38), block=(0.16, 0.12), joint=0.12, mortar=(0.16, 0.15, 0.14), var=0.25, rough=0.5, dark_low=False, floor=True)
QUAYSTONE = K.stone_mat("quay_wall", (0.50, 0.46, 0.40), dark=(0.20, 0.19, 0.17), lichen=(0.30, 0.34, 0.22), scale=0.8)
BRICK = K.mat("bristol_brick", (0.48, 0.24, 0.17), "brick", rough=0.85)
LIME = K.patchy_mat("limewash", (0.80, 0.76, 0.66), patches=[((0.55, 0.52, 0.45), 0.8, 0.3), ((0.40, 0.38, 0.33), 0.3, 0.15)], rough=0.9)
OAKFRAME = K.mat("black_timber", (0.10, 0.08, 0.07), "wood", rough=0.7)
GLASS = K.mat("small_panes", (0.08, 0.10, 0.12), "glass", rough=0.1)
SASH = K.mat("white_sash", (0.84, 0.82, 0.76), "plaster", rough=0.5)
SLATE = K.mat("roof_slate", (0.24, 0.25, 0.28), "tile", rough=0.6)
TILE = K.mat("pantiles", (0.55, 0.30, 0.20), "brick", rough=0.8)
DOOR = K.mat("inn_door", (0.20, 0.25, 0.18), "planks", rough=0.6)
HULL = K.mat("tarred_hull", (0.08, 0.065, 0.05), "planks", rough=0.55)
TOPSIDE = K.mat("ochre_topsides", (0.62, 0.45, 0.18), "planks", rough=0.6)
BLUE = K.mat("blue_paint", (0.14, 0.22, 0.38), "wood", rough=0.5)
REDP = K.mat("red_paint", (0.50, 0.10, 0.07), "wood", rough=0.5)
GILT = K.mat("gilding", (0.80, 0.60, 0.25), "metal", rough=0.3)
SPAR = K.mat("spars", (0.45, 0.34, 0.22), "wood", rough=0.65)
BLACKSPAR = K.mat("black_spars", (0.06, 0.05, 0.045), "wood", rough=0.6)
SAIL = K.mat("furled_canvas", (0.80, 0.76, 0.66), "fabric", rough=0.9)
ROPE = K.mat("tarred_rope", (0.12, 0.10, 0.08), "fabric", rough=0.8)
HEMP = K.mat("hemp_coils", (0.48, 0.40, 0.28), "fabric", rough=0.9)
CASK = K.mat("cask_staves", (0.40, 0.30, 0.20), "wood", rough=0.7)
IRON = K.mat("iron", (0.07, 0.065, 0.06), "metal", rough=0.6)
BALE = K.mat("sacking", (0.58, 0.50, 0.36), "fabric", rough=0.95)
CARTWOOD = K.mat("cart_wood", (0.35, 0.28, 0.20), "wood", rough=0.75)
WATER = K.mat("harbour_water", (0.10, 0.14, 0.11), "water", rough=0.12)
MUD = K.mat("mud", (0.22, 0.19, 0.15), "soil", rough=0.6)
FLAG = K.mat("ensigns", (0.62, 0.10, 0.10), "fabric", rough=0.7)
K.keep(WATER, "water.ocean.harbour"); K.keep(SAIL, "cloth.sail.furled"); K.keep(FLAG, "cloth.flag.ensigns")
K.size(SETTS, 2048, 256); K.size(BRICK, 1024, 128); K.size(HULL, 2048, 256); K.size(QUAYSTONE, 1024, 128)

# ----------------------------------------------------------------------------- the quay, the harbour, the far bank
QX0, QX1 = -90.0, 90.0
rk.box("quay_top", (QX1 - QX0, 18.0, 0.3), (0.0, EDGE - 9.0, -0.3), SETTS)
rk._ground.append(lambda x, y: 0.0 if y < EDGE else None)
rk.box("quay_face", (QX1 - QX0, 0.6, 2.6), (0.0, EDGE + 0.3 - 0.6, WATER_Z - 0.7), QUAYSTONE)
rk.box("quay_coping", (QX1 - QX0, 0.55, 0.18), (0.0, EDGE - 0.27, -0.12), QUAYSTONE)
rk.box("harbour_bed", (200.0, 120.0, 0.2), (0.0, EDGE + 60.0, WATER_Z - 1.5), MUD)
K.water_plane("water", WATER, WATER_Z, radius=160, centre=(0.0, EDGE + 40.0), rings=8, ns=40)
# mooring rings and old cannon set muzzle-down as bollards along the edge
QB = rk._B("quay_bits")
for x in np.arange(QX0 + 3.0, QX1, 6.5):
    QB.cyl(IRON, 0.16, 0.7, (x, EDGE - 0.6, 0.0), sides=10, r1=0.12)
    QB.ball(IRON, 0.13, (x, EDGE - 0.6, 0.72), sub=1)
    QB.cyl(IRON, 0.19, 0.06, (x, EDGE - 0.6, 0.55), sides=10)
QB.done()
# the far bank 55 m off: a quay wall, warehouses and houses, a church tower
FB = rk._B("far_bank")
FY = EDGE + 58.0
FB.box(QUAYSTONE, (240.0, 4.0, 2.5), (0.0, FY, WATER_Z - 0.6))
x = -110.0
while x < 110.0:
    w = R.uniform(6.0, 11.0); h = R.uniform(9.0, 15.0); d = 10.0
    m = BRICK if R.random() < 0.6 else LIME
    FB.box(m, (w, d, h), (x + w / 2, FY + 2.0 + d / 2, 0.0))
    FB.mesh(SLATE if R.random() < 0.6 else TILE, [(x, FY + 2.0, h), (x + w, FY + 2.0, h), (x + w, FY + 2.0 + d / 2, h + 3.5), (x, FY + 2.0 + d / 2, h + 3.5)], [(0, 1, 2, 3)])
    for f in range(int(h / 3.0)):
        for k in range(int(w / 2.2)):
            FB.box(GLASS, (1.0, 0.1, 1.5), (x + 1.1 + k * 2.2, FY + 1.98, 0.8 + f * 3.0))
    x += w + R.uniform(0.0, 0.4)
FB.box(LIME, (7.0, 7.0, 32.0), (-30.0, FY + 30.0, 0.0))                           # a church tower over the roofs
for sx in (-1, 1):
    for sy in (-1, 1): FB.cyl(LIME, 0.5, 4.0, (-30.0 + sx * 3.2, FY + 30.0 + sy * 3.2, 32.0), sides=6, r1=0.05)
FB.done()
K.sky((0.32, 0.50, 0.80), (0.80, 0.84, 0.88), strength=1.0, radius=600, ground_color=(0.35, 0.36, 0.34))

# ----------------------------------------------------------------------------- the fronts behind the quay: warehouses and the squire's inn
FR = rk._B("fronts")
BY = EDGE - 9.0                                     # the building line, behind the reader


def front(x0, w, h, kind, gable=True):
    m = {"brick": BRICK, "lime": LIME, "timber": LIME}[kind]
    FR.box(m, (w, 8.0, h), (x0 + w / 2, BY - 4.0, 0.0))
    if kind == "timber":
        for u in np.arange(x0 + 0.1, x0 + w, 0.9): FR.box(OAKFRAME, (0.18, 0.06, h), (u, BY + 0.02, 0.0))
        for zz in np.arange(0.0, h, 2.7): FR.box(OAKFRAME, (w, 0.08, 0.22), (x0 + w / 2, BY + 0.03, zz + 2.5))
    # windows: small-paned sashes on the upper floors, a shop or warehouse door below
    nf = int(h / 2.8)
    for f in range(1, nf):
        for k in range(max(1, int(w / 1.9))):
            cx = x0 + 0.95 + k * (w / max(1, int(w / 1.9)))
            FR.box(SASH, (0.95, 0.06, 1.45), (cx, BY + 0.02, f * 2.8 + 0.55))
            FR.box(GLASS, (0.82, 0.08, 1.32), (cx, BY + 0.03, f * 2.8 + 0.61))
            for zz in (0.45, 0.9): FR.box(SASH, (0.82, 0.1, 0.03), (cx, BY + 0.04, f * 2.8 + 0.61 + zz))
            FR.box(SASH, (0.03, 0.1, 1.32), (cx, BY + 0.04, f * 2.8 + 0.61))
    if gable:
        FR.mesh(TILE if kind != "brick" else SLATE, [(x0, BY + 0.3, h), (x0 + w, BY + 0.3, h), (x0 + w, BY - 4.0, h + 4.2), (x0, BY - 4.0, h + 4.2)], [(0, 1, 2, 3)])
    FR.box(OAKFRAME, (w, 0.3, 0.2), (x0 + w / 2, BY + 0.1, h))
x = -26.0; FRONTS = []
for k, (w, h, kind) in enumerate(((7.5, 11.0, "brick"), (5.5, 9.5, "timber"), (8.5, 12.5, "brick"), (6.0, 10.0, "lime"), (9.0, 13.0, "brick"), (5.0, 9.0, "timber"), (7.0, 11.5, "lime"), (8.0, 12.0, "brick"))):
    front(x, w, h, kind)
    FRONTS.append((x, w, h))
    # the ground floor: a warehouse loading door with a hoist above, or a shop window
    cx = x + w / 2
    if kind == "brick":
        FR.box(DOOR, (2.4, 0.1, 2.8), (cx, BY + 0.03, 0.0))
        FR.box(OAKFRAME, (0.25, 1.6, 0.25), (cx, BY + 0.7, h - 0.8))
        FR.box(DOOR, (1.6, 0.1, 1.9), (cx, BY + 0.03, 3.6))
    else:
        FR.box(SASH, (2.6, 0.1, 1.6), (cx, BY + 0.03, 0.7)); FR.box(GLASS, (2.4, 0.12, 1.4), (cx, BY + 0.04, 0.8))
        FR.box(DOOR, (1.0, 0.1, 2.2), (x + 0.8, BY + 0.03, 0.0))
    x += w + 0.1
# the fronts carry on along the quay both ways, plainer with distance
for x0_ in list(np.arange(-90.0, -43.0, 7.0)) + list(np.arange(x, 90.0, 7.0)):
    front(x0_, 6.8, R.uniform(9.0, 13.0), R.choice(("brick", "brick", "lime", "timber")))
# the squire's large inn at the west end: wider, with a porch and a lantern over the door
INN_X = -36.0
front(INN_X, 10.0, 12.0, "lime")
FR.box(DOOR, (1.5, 0.12, 2.5), (INN_X + 5.0, BY + 0.04, 0.0))
for sx in (-1, 1): FR.cyl(SASH, 0.12, 2.9, (INN_X + 5.0 + sx * 1.1, BY + 0.6, 0.0), sides=10)
FR.box(SASH, (2.8, 1.0, 0.25), (INN_X + 5.0, BY + 0.5, 2.9))
FR.done()
LANT = Vector((INN_X + 5.0, BY + 0.9, 3.6))
pk.box("InnLantern", (0.22, 0.22, 0.3), tuple(LANT), K.emit_mat("lantern_glass", (1.0, 0.8, 0.5), 1.2))
pk.tube("InnLanternArm", [Vector((LANT.x, BY + 0.05, 3.85)), Vector((LANT.x, LANT.y, 3.85))], 0.02, IRON, sides=5)

# ----------------------------------------------------------------------------- the ships, moored bow-on to the quay, bowsprits over the setts
S = rk._B("ships"); SS = rk._B("ship_sails"); FG = rk._B("ship_flags")


def ship(cx, L, beam, hullc, head="scroll", masts=3, heading=90.0, detail=1):
    """A three-masted merchantman of the 1750s: tarred bottom, painted topsides, wales, gunport band, the head with
    its rails, cutwater and carved head, bowsprit and jib-boom, catheads, masts with tops, yards with furled sails,
    shrouds and stays. Her stem is at the quay edge; she lies along +Y."""
    stem_y = EDGE + 2.6
    def P(u, v, z): return (cx + v, stem_y + (L - u) if False else stem_y + u, z)
    fb = 2.6; dr = 3.2; nst = 12
    secs = []
    for i in range(nst + 1):
        t = i / nst; u = L * t                     # u = 0 at the stem
        full = 1 - (1 - t) ** 0 if False else (1 - max(0.0, 1 - t / 0.35) ** 2.2) * (1 - max(0.0, (t - 0.8) / 0.2) ** 2 * 0.45)
        wdt = beam / 2 * max(0.05, full)
        rail = fb + 0.9 * (1 - t) ** 2 * 1.2 + (1.4 if t > 0.82 else 0.0)
        sec = [(0.9, rail), (1.0, fb * 0.6), (1.0, 0.0), (0.8, -dr * 0.6), (0.25, -dr)]
        secs.append([P(u, -wdt * k, WATER_Z + z) for k, z in sec] + [P(u, wdt * k, WATER_Z + z) for k, z in reversed(sec)])
    for a, b_ in zip(secs, secs[1:]):
        for k in range(len(a) - 1):
            m = HULL if k in (2, 3, len(a) - 4, len(a) - 3) else hullc
            S.mesh(m, [a[k], b_[k], b_[k + 1], a[k + 1]], [(0, 1, 2, 3)])
    S.mesh(hullc, secs[-1], [tuple(range(len(secs[-1])))])
    # wales and the gunport band
    for side in (-1, 1):
        for zf, r_, m in ((0.15, 0.13, HULL), (0.55, 0.11, HULL), (0.9, 0.08, BLACKSPAR)):
            pts = []
            for t in np.linspace(0.05, 0.97, 10):
                full = (1 - max(0.0, 1 - t / 0.35) ** 2.2) * (1 - max(0.0, (t - 0.8) / 0.2) ** 2 * 0.45)
                pts.append(P(L * t, side * beam / 2 * max(0.05, full) * 1.01, WATER_Z + fb * zf + 0.9 * (1 - t) ** 2 * 1.2 * zf))
            S.tube(m, pts, [r_] * len(pts), 5)
        if detail:
            for t in np.linspace(0.3, 0.8, 6):
                full = (1 - max(0.0, 1 - t / 0.35) ** 2.2) * (1 - max(0.0, (t - 0.8) / 0.2) ** 2 * 0.45)
                q = P(L * t, side * beam / 2 * max(0.05, full) * 1.02, WATER_Z + fb * 0.72)
                S.box(REDP, (0.04, 0.6, 0.55), (q[0], q[1], q[2]), (0, 0, 0))
    # the head: the cutwater, the head rails and the carved figure on the stem
    stem_top = Vector(P(0.0, 0.0, WATER_Z + fb + 1.1))
    K.rough_block(S, hullc, (0.35, 1.9, fb + 1.1 + dr), (cx, stem_y - 0.9, WATER_Z - dr), (0, 0, 0), amp=0.0, seed=1)
    for side in (-1, 1):
        S.tube(GILT if head == "lion" else BLACKSPAR, [Vector(P(1.8, side * beam * 0.36, WATER_Z + fb + 0.7)), Vector(P(0.2, side * 0.6, WATER_Z + fb + 0.5)), Vector(P(-1.7, side * 0.12, WATER_Z + fb + 0.55))], [0.07, 0.06, 0.05], 5)
        S.box(BLACKSPAR, (0.25, 1.4, 0.25), P(0.9, side * beam * 0.42, WATER_Z + fb + 1.2), (0, 0, 0))   # cathead
    fig = Vector(P(-2.15, 0.0, WATER_Z + fb + 0.75))
    if head == "lion":
        # a crowned lion leaning out over the water: a carved, gilded block of a head with mane, jaw and crown
        S.ball(GILT, 0.42, tuple(fig), squash=(1.0, 0.85, 1.0), sub=2)
        S.ball(GILT, 0.26, tuple(fig + Vector((0, -0.38, -0.08))), squash=(0.8, 1.0, 0.75), sub=1)
        S.ball(REDP, 0.08, tuple(fig + Vector((0, -0.58, -0.2))), squash=(1.2, 0.6, 0.5), sub=0)
        for k in range(7):
            a = math.radians(-90 + 30 * k)
            S.ball(GILT, 0.12, tuple(fig + Vector((math.cos(a) * 0.38, 0.12, math.sin(a) * 0.34 + 0.1))), sub=0)
        S.cyl(GILT, 0.2, 0.18, tuple(fig + Vector((0, 0.05, 0.38))), sides=8, r1=0.24)
        for k in range(5):
            a = 2 * math.pi * k / 5
            S.ball(GILT, 0.04, tuple(fig + Vector((math.cos(a) * 0.22, 0.05 + math.sin(a) * 0.22, 0.6))), sub=0)
    else:
        # a scroll-head: a carved volute on the stem, painted blue and picked out in gilt
        pts = [fig + Vector((0, 0.1, -0.4)), fig + Vector((0, -0.25, -0.1)), fig + Vector((0, -0.32, 0.25)), fig + Vector((0, -0.1, 0.42)), fig + Vector((0, 0.1, 0.3)), fig + Vector((0, 0.05, 0.12)), fig + Vector((0, -0.08, 0.18))]
        S.tube(BLUE, pts, [0.10, 0.095, 0.085, 0.075, 0.06, 0.05, 0.04], 7)
        S.tube(GILT, [p + Vector((0.13, 0, 0)) for p in pts[:5]], [0.03] * 5, 4)
    # bowsprit and jib-boom, rising over the quay
    bs0 = Vector(P(1.5, 0.0, WATER_Z + fb + 1.3)); bsd = (Vector(P(-1.0, 0.0, 0)) - Vector(P(0.0, 0.0, 0))).normalized() + Vector((0, 0, 0.62))
    bsd.normalize()
    S.seg(SPAR, tuple(bs0), tuple(bs0 + bsd * 8.0), 0.32, 0.2, 10)
    S.seg(SPAR, tuple(bs0 + bsd * 6.5), tuple(bs0 + bsd * 11.5), 0.14, 0.08, 8)
    S.box(BLACKSPAR, (0.6, 0.6, 0.5), tuple(bs0 + bsd * 7.7 - Vector((0, 0, 0.25))), (0, 0, 0))      # the cap
    bs_end = bs0 + bsd * 7.8; jb_end = bs0 + bsd * 11.3
    # the spritsail yard under the bowsprit, its sail furled
    syd = bs0 + bsd * 5.0 - Vector((0, 0, 0.4))
    # masts, tops, yards, furled courses and topsails
    heads = []
    for k, (u, h, yl) in enumerate(((L * 0.18, 26.0, 16.0), (L * 0.48, 30.0, 19.0), (L * 0.8, 21.0, 12.0))[:masts]):
        base = Vector(P(u, 0.0, WATER_Z + fb))
        top1 = base + Vector((0, 0, h * 0.55)); top2 = base + Vector((0, 0.2, h))
        S.seg(SPAR, tuple(base), tuple(top1 + Vector((0, 0, 1.6))), 0.34, 0.26, 10)
        S.seg(SPAR, tuple(top1 - Vector((0, 0.2, 1.2))), tuple(top2), 0.2, 0.09, 8)
        S.box(BLACKSPAR, (2.8, 2.2, 0.18), tuple(top1 - Vector((0, 0, 0.1))), (0, 0, 0))
        for j, (zf, yf) in enumerate(((0.42, 1.0), (0.72, 0.72), (0.93, 0.5))):
            yz = base + Vector((0, -0.6, h * zf)); half = yl * yf / 2
            S.seg(BLACKSPAR, tuple(yz - Vector((half, 0, 0))), tuple(yz + Vector((half, 0, 0))), 0.16 * yf + 0.04, 0.16 * yf + 0.04, 6)
            SS.tube(SAIL, [yz + Vector((-half * 0.9, -0.15, 0.25)), yz + Vector((0, -0.25, 0.38)), yz + Vector((half * 0.9, -0.15, 0.25))], [0.22 * yf + 0.08, 0.38 * yf + 0.12, 0.22 * yf + 0.08], 6)
        heads.append((base, top1, top2))
        # shrouds to the channels, and a pennant
        if detail:
            for side in (-1, 1):
                for n in range(4):
                    foot = Vector(P(u + (n - 1.5) * 0.7, side * (beam / 2 + 0.3), WATER_Z + fb + 0.5))
                    S.seg(ROPE, tuple(foot), tuple(top1 + Vector((side * 0.4, 0, -0.4))), 0.03, 0.03, 4)
                for zz in np.arange(1.0, h * 0.5, 1.2) if k == 0 else ():
                    t = zz / (h * 0.55)
                    a = Vector(P(u - 1.05, side * (beam / 2 + 0.3), WATER_Z + fb + 0.5)).lerp(top1 + Vector((side * 0.4, 0, -0.4)), t)
                    b_ = Vector(P(u + 1.05, side * (beam / 2 + 0.3), WATER_Z + fb + 0.5)).lerp(top1 + Vector((side * 0.4, 0, -0.4)), t)
                    S.seg(ROPE, tuple(a), tuple(b_), 0.012, 0.012, 3)
        FG.mesh(FLAG, [tuple(top2), tuple(top2 - Vector((0, 0, 0.35))), tuple(top2 + Vector((2.5, 1.5, -0.4)))], [(0, 1, 2)])
    # stays: fore stay to the bowsprit, the jib stay, stays between the masts
    (f0, f1, f2) = heads[0]
    S.seg(ROPE, tuple(f1), tuple(bs_end), 0.05, 0.05, 4); S.seg(ROPE, tuple(f2), tuple(jb_end), 0.03, 0.03, 4)
    S.seg(ROPE, tuple(bs_end), tuple(Vector(P(-1.6, 0, WATER_Z + 0.8))), 0.04, 0.04, 4)            # bobstay
    for a_, b2 in zip(heads[1:], heads[:-1]):
        S.seg(ROPE, tuple(a_[1]), tuple(b2[0] + Vector((0, 0, 1.5))), 0.04, 0.04, 4)
        S.seg(ROPE, tuple(a_[2]), tuple(b2[1]), 0.03, 0.03, 4)
    # an anchor at the cathead and the mooring lines to the quay
    for side in (-1, 1):
        ch = Vector(P(0.9, side * beam * 0.55, WATER_Z + fb + 1.2))
        S.seg(IRON, tuple(ch - Vector((0, 0, 0.2))), tuple(ch - Vector((0, 0, 2.6))), 0.08, 0.08, 6)
        S.seg(IRON, tuple(ch - Vector((0.6, 0, 2.4))), tuple(ch + Vector((0.6, 0, -2.4))), 0.07, 0.07, 6)
        moor = Vector((cx + side * 3.2, EDGE - 0.6, 0.6))
        pts = [Vector(P(0.5, side * beam * 0.45, WATER_Z + fb + 0.3)), (Vector(P(0.5, side * beam * 0.45, WATER_Z + fb + 0.3)) + moor) / 2 - Vector((0, 0, 0.9)), moor]
        S.tube(ROPE, pts, [0.05, 0.05, 0.05], 5)
    return bs0, bs_end


ship(-9.5, 30.0, 8.2, TOPSIDE, head="scroll", detail=0)
SHIP_B = ship(1.8, 32.0, 8.6, BLUE, head="scroll", detail=1)
ship(13.5, 28.0, 7.8, TOPSIDE, head="scroll", detail=1)
ship(25.0, 26.0, 7.4, REDP, head="scroll", detail=0)
S.done(); SS.done(); FG.done()
# ships moored on the far side, smaller in the distance
for k, (x, L) in enumerate(((-40.0, 28.0), (-18.0, 24.0), (6.0, 30.0), (30.0, 26.0))):
    F2 = rk._B(f"far_ship{k}")
    yy = FY - 6.0
    F2.ball(HULL, 1.0, (x, yy, WATER_Z + 0.6), squash=(L / 2, 3.6, 1.6), sub=2)
    for j, (u, h) in enumerate(((-0.3, 22), (0.05, 26), (0.35, 18))):
        F2.seg(SPAR, (x + L * u, yy, WATER_Z + 2.0), (x + L * u, yy, WATER_Z + 2.0 + h), 0.25, 0.1, 6)
        for zf in (0.45, 0.75): F2.seg(BLACKSPAR, (x + L * u, yy - 6.0, WATER_Z + 2.0 + h * zf), (x + L * u, yy + 6.0, WATER_Z + 2.0 + h * zf), 0.12, 0.12, 4)
    F2.done()

# ----------------------------------------------------------------------------- along the quay: a cart, bales, barrels, coils of rope
def cask(name, x, y, lying=False, rot=0.0, s=1.0):
    prof = [(0.0, 0.0), (0.27 * s, 0.0), (0.31 * s, 0.17 * s), (0.33 * s, 0.4 * s), (0.31 * s, 0.63 * s), (0.27 * s, 0.8 * s), (0.0, 0.8 * s)]
    if lying:
        o = pk.lathe(name, [(r_, h - 0.4 * s) for r_, h in prof], (x, y, 0.33 * s), CASK, steps=14)
        o.rotation_euler = (math.pi / 2, 0, rot)
    else:
        pk.lathe(name, prof, (x, y, 0.0), CASK, steps=14)
        for zz in (0.12, 0.68): pk.cyl(name + f"Hoop{zz}", 0.305 * s, 0.03, (x, y, zz * s), IRON, verts=14)
for k, (x, y, ly, r) in enumerate(((-3.2, -1.8, False, 0), (-2.55, -1.95, False, 0), (-2.9, -2.6, False, 0), (-3.4, -0.9, True, 0.2), (3.6, -3.4, False, 0), (4.3, -3.2, True, 1.4))):
    cask(f"Cask{k}", x, y, ly, r)
for k, (x, y, z, r) in enumerate(((5.2, -1.5, 0.0, 0.1), (5.3, -2.4, 0.0, -0.05), (5.25, -1.95, 0.6, 0.3), (-6.0, -4.0, 0.0, 0.5))):
    pk.box(f"Bale{k}", (1.1, 0.75, 0.6), (x, y, z + 0.3), BALE, bevel=0.12, rot=(0, 0, r))
    for dx in (-0.3, 0.3): pk.box(f"BaleCord{k}{dx}", (0.03, 0.78, 0.63), (x + dx * math.cos(r), y + dx * math.sin(r), z + 0.3), ROPE, rot=(0, 0, r))
CO = rk._B("coils")
for k, (x, y, R0) in enumerate(((-1.4, 2.2, 0.5), (2.6, 1.9, 0.42), (-5.0, 2.4, 0.55))):
    for L in range(3):
        for t in range(5):
            rr = R0 - t * 0.075
            ring = [Vector((x + math.cos(a) * rr, y + math.sin(a) * rr, 0.035 + L * 0.066)) for a in np.linspace(0, 2 * math.pi, 15)]
            CO.tube(HEMP, ring, [0.035] * 15, 4)
CO.done()
# a two-wheeled cart, shafts down, loaded with a bale and a cask
CT = rk._B("cart", (7.5, -2.6, 0.0), 75)
CT.box(CARTWOOD, (2.2, 1.3, 0.12), (0, 0, 0.75)); CT.box(CARTWOOD, (2.2, 0.06, 0.4), (0, 0.65, 0.87)); CT.box(CARTWOOD, (2.2, 0.06, 0.4), (0, -0.65, 0.87))
for sy in (-1, 1):
    CT.seg(CARTWOOD, (1.0, sy * 0.45, 0.78), (3.4, sy * 0.4, 0.05), 0.05, 0.04, 5)
    w0 = Vector((0.0, sy * 0.78, 0.68))
    ring = [w0 + Vector((math.cos(a) * 0.66, 0, math.sin(a) * 0.66)) for a in np.linspace(0, 2 * math.pi, 17)]
    CT.tube(CARTWOOD, ring, [0.05] * 17, 5)
    for a in np.linspace(0, 2 * math.pi, 11)[:-1]: CT.seg(CARTWOOD, tuple(w0), tuple(w0 + Vector((math.cos(a) * 0.64, 0, math.sin(a) * 0.64))), 0.025, 0.02, 4)
    CT.cyl(CARTWOOD, 0.12, 0.2, tuple(w0 - Vector((0, 0.1, 0))), (90, 0, 0), sides=8)
CT.done()

# ----------------------------------------------------------------------------- light, sound, reader
K.sun(30, 55, strength=4.2, color=(1.0, 0.93, 0.82), softness=0.9)
K.sound("gulls", "harbour", (0.0, 20.0, 8.0))
K.sound("rigging", "ships", (2.0, 12.0, 6.0))
K.sound("crowd", "quay", (-12.0, -2.0, 1.5))
K.sound("wind", "masts", (8.0, 18.0, 15.0))
K.fx("lantern", "inn", tuple(LANT), 0.12)
E, D = K.reader((0.0, 0.0), (0.0, 10.0))
K.reader_cams()
K.cam("figurehead", (-2.5, 0.5, 2.0), (1.8, EDGE + 0.2, 1.4), lens=24)
K.cam("up", (0.0, 0.0, 1.55), (0.6, 4.0, 9.0), lens=16)
K.finish()
