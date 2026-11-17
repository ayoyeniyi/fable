"""
Fable step-in room: the great cabin of the schooner Hispaniola at anchor off Bristol (Treasure Island, chapter 9,
"Powder and Arms").

"The Hispaniola lay some way out, and we went under the figureheads and round the sterns of many other ships ... we
got alongside ... The captain ... 'I don't like this cruise' ... 'Well, then,' said he, 'here it is: they are putting
the powder and the arms in the fore hold. Now, you have a good place under the cabin; why not put them there?'" ...
"The crew and the officers were ... six berths had been made astern out of the after part of the main hold" ... "the
captain ... shut the door behind him".

The great cabin aft, about 5 x 4 m, deck beams overhead at little more than head height: panelling painted a pale
stone colour with varnished oak mouldings, a fixed table on its pillar with lockers along the sides for seats and a
couple of chairs, the five stern windows with their leaded lights looking out on the harbour (water reflections play on
the deckhead), a hanging lantern lit for warmth, brass fittings, curtained berths opening off the sides; in the deck,
the hatch to the space under the cabin where the powder is to go; through the door forward, in the steerage, kegs of
powder and racks of muskets being brought aft. No treasure map, no apple barrel, no island, no weapons drawn. No people.

Light: afternoon daylight through the stern windows (sun on the water behind), the lantern a warm accent.
Reader: just inside the cabin door, facing aft to the table, as Captain Smollett did when he came in.

  blender -b -P blender/build_hispaniola_cabin.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_hispaniola_cabin.py -- --render --samples 32 --res 1280 --cams reader,left,right,behind,windows
  blender -b -P blender/build_hispaniola_cabin.py -- --export
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b5 as S
import pride_kit as K
import pride_interior as I
import mobydick_kit as MK
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, anchor, sound, light_obj)

SID = "hispaniola-cabin"
ARGS = S.setup(SID, seed=1752)
scene = K.scene
scene.cycles.max_bounces = 8; scene.cycles.diffuse_bounces = 5
rng = random.Random(1752)

# frame: +Y aft (toward the stern windows), x across (+X starboard). Deck (floor) z = 0.
Y0, Y1 = -2.4, 2.6          # forward bulkhead (door) .. stern
HALF = lambda y: 2.05 - 0.35 * K.smoothstep(0.5, 2.6, y)       # the cabin narrows toward the stern
BEAM_Z = 1.88; DECKHEAD = 2.02
WL = -1.1                    # the harbour water below the stern windows
READER = Vector((0.3, -1.65, 0))
TABLE = Vector((0.0, 0.85, 0))

# ----------------------------------------------------------------------------- materials
M_PANEL = I.joinery_mat("M_PanelPaint", K.srgb((0.78, 0.74, 0.62)), rough=0.45)
M_OAK = MK.timber_mat("M_Varnished", base=(0.22, 0.12, 0.05), dark=(0.07, 0.04, 0.015), light=(0.34, 0.20, 0.09), along='X', rough=(0.25, 0.5), grime=0.25, polish=0.35)
M_OAKZ = MK.timber_mat("M_VarnishedZ", base=(0.22, 0.12, 0.05), dark=(0.07, 0.04, 0.015), light=(0.34, 0.20, 0.09), along='Z', rough=(0.25, 0.5), grime=0.25, polish=0.35)
M_BEAM = MK.timber_mat("M_DeckBeams", base=(0.62, 0.58, 0.48), dark=(0.40, 0.36, 0.28), light=(0.74, 0.70, 0.60), along='X', rough=(0.5, 0.75), grime=0.3)
M_DECKHEAD = MK.timber_mat("M_Deckhead", base=(0.70, 0.66, 0.56), dark=(0.48, 0.44, 0.36), light=(0.80, 0.77, 0.68), along='Y', rough=(0.6, 0.8), grime=0.3, seams=('X', 0.15))
M_FLOOR = MK.timber_mat("M_DeckPlanks", base=(0.42, 0.34, 0.24), dark=(0.20, 0.15, 0.10), light=(0.56, 0.47, 0.34), along='Y', rough=(0.5, 0.8), grime=0.4, seams=('X', 0.16))
M_BRASS = plain("M_Brass", K.srgb((0.70, 0.52, 0.26)), rough=0.3, metallic=1.0)
M_IRON = MK.iron_mat("M_Iron", rust=0.3)
M_CANVAS = noisy("M_Canvas", [K.srgb((0.72, 0.68, 0.58)), K.srgb((0.64, 0.60, 0.50))], scale=20, rough=0.9, bump=0.3)
M_CURTAIN = noisy("M_Cushion", [K.srgb((0.46, 0.20, 0.16)), K.srgb((0.38, 0.16, 0.13)), K.srgb((0.52, 0.26, 0.20))], scale=12, rough=0.85, sheen=0.5, bump=0.2)
M_BCURT = noisy("M_BerthCurtain", [K.srgb((0.50, 0.24, 0.18)), K.srgb((0.42, 0.18, 0.14))], scale=12, rough=0.85, sheen=0.5, bump=0.2)
M_BLANKET = noisy("M_Blanket", [K.srgb((0.30, 0.32, 0.40)), K.srgb((0.24, 0.26, 0.34))], scale=14, rough=0.95, sheen=0.4, bump=0.3)
M_KEG = MK.timber_mat("M_PowderKeg", base=(0.40, 0.30, 0.18), dark=(0.16, 0.11, 0.06), light=(0.52, 0.40, 0.26), along='Z', rough=(0.5, 0.8), grime=0.4)
M_STOCK = MK.timber_mat("M_MusketStock", base=(0.24, 0.13, 0.06), dark=(0.08, 0.04, 0.02), light=(0.36, 0.20, 0.10), along='Y', rough=(0.3, 0.6), grime=0.2)
M_LEAD = noisy("M_LeadCame", [K.srgb((0.20, 0.20, 0.21)), K.srgb((0.28, 0.28, 0.29))], scale=20, rough=0.5)
M_GLOW = plain("M_LanternGlow", (0.0, 0.0, 0.0), rough=0.5, emission=(1.0, 0.68, 0.34), strength=4.0)
M_PANE = new_mat("M_Pane")[0]
nt = M_PANE.node_tree
for n_ in list(nt.nodes): nt.nodes.remove(n_)
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (0.9, 0.92, 0.88, 1)
nt.links.new(tr.outputs["BSDF"], o_.inputs["Surface"])
M_WATER = new_mat("M_HarbourWater")[0]
bw = M_WATER.node_tree.nodes["Principled BSDF"]; bw.inputs["Base Color"].default_value = (0.05, 0.07, 0.06, 1); bw.inputs["Roughness"].default_value = 0.12
nw = noise_(M_WATER.node_tree, obj_coords(M_WATER.node_tree), 1.5, 4, 0.6, loc=(-700, -200)); bump_from(M_WATER.node_tree, bw, nw.outputs["Fac"], 0.25, 0.05)


def harbour_view(name="M_HarbourView"):
    """beyond the stern: Bristol's crowded river harbour on a bright afternoon - pale sky, the far quays with warehouses
    and the masts of ships at anchor, the town's roofs and towers rising behind."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1700, 0)); x, z = s.outputs["X"], s.outputs["Z"]
    sky = mix_rgb(nt, 'MIX', maprange(nt, z, 0.0, 14.0, 0, 1, (-1400, 400)), (0.86, 0.85, 0.80, 1), (0.52, 0.64, 0.82, 1), (-1200, 400))
    cl = noise_(nt, co, 0.12, 5, 0.6, loc=(-1400, 650)); sky = mix_rgb(nt, 'MIX', maprange(nt, cl.outputs["Fac"], 0.5, 0.68, 0, 0.6, (-1200, 650)), sky, (0.96, 0.95, 0.92, 1), (-1000, 400))
    rn = noise_(nt, co, 0.15, 3, 0.5, loc=(-1500, 100))
    town_top = math_(nt, 'ADD', 2.0, math_(nt, 'MULTIPLY', rn.outputs["Fac"], 4.0, (-1300, 100)), (-1200, 100))
    town = maprange(nt, math_(nt, 'SUBTRACT', town_top, z, (-1100, 100)), 0, 0.05, 0, 1, (-1000, 100))
    tn = noise_(nt, co, 1.6, 4, 0.6, loc=(-1300, -100))
    tc = mix_rgb(nt, 'MIX', maprange(nt, tn.outputs["Fac"], 0.3, 0.7, 0, 1, (-1100, -100)), (0.40, 0.34, 0.30, 1), (0.62, 0.52, 0.44, 1), (-950, -100))
    tc = mix_rgb(nt, 'MIX', maprange(nt, z, 0.0, 2.0, 0.5, 0.0, (-1100, -250)), tc, (0.70, 0.72, 0.74, 1), (-800, -150))     # haze low down
    col = mix_rgb(nt, 'MIX', town, sky, tc, (-700, 300))
    # masts of ships at anchor: thin dark verticals with yards
    mx = math_(nt, 'FRACT', math_(nt, 'DIVIDE', x, 1.7, (-1500, -500)), None, (-1400, -500))
    mn = noise_(nt, co, 0.9, 2, 0.5, loc=(-1500, -650))
    has = maprange(nt, mn.outputs["Fac"], 0.5, 0.55, 0, 1, (-1300, -650))
    mast = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', mx, 0.5, (-1300, -500)), None, (-1200, -500)), 0.0, 0.02, 1, 0, (-1100, -500)), has, (-1000, -550))
    mast = math_(nt, 'MULTIPLY', mast, maprange(nt, z, 8.0, 8.3, 1, 0, (-1100, -800)), (-900, -650))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', mast, 0.85, (-800, -650)), col, (0.18, 0.16, 0.14, 1), (-500, 300))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1); b.inputs["Emission Strength"].default_value = 1.0
    return m
M_VIEW = harbour_view()

# ----------------------------------------------------------------------------- the cabin shell: deck, sides (with a little tumblehome), stern, forward bulkhead, beams
NY = 12
ys = [Y0 + (Y1 - Y0) * i / NY for i in range(NY + 1)]
fv = []; ff = []
for y in ys: fv += [(-HALF(y), y, 0.0), (HALF(y), y, 0.0)]
for i in range(NY): ff.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
fl = mesh_from("Deck", fv, ff, M_FLOOR)
for side in (-1, 1):
    sv = []; sf = []
    for y in ys:
        for z in (0.0, 0.9, DECKHEAD + 0.05):
            tum = 1.0 - 0.04 * (z / DECKHEAD)
            sv.append((side * HALF(y) * tum, y, z))
    for i in range(NY):
        for j in range(2):
            a = i * 3 + j; b_ = (i + 1) * 3 + j
            sf.append((a, b_, b_ + 1, a + 1) if side > 0 else (a, a + 1, b_ + 1, b_))
    mesh_from(f"Side{side}", sv, sf, M_PANEL)
    # panelling: rails and stiles on the sides (varnished mouldings over painted fields)
    for z in (0.12, 0.85, 1.75):
        pts = [Vector((side * (HALF(y) - 0.02) * (1 - 0.04 * z / DECKHEAD), y, z)) for y in ys]
        tube(f"Rail{side}{z}", pts, 0.025, M_OAK, sides=4)
    for k, y in enumerate(ys[1:-1:2]):
        box(f"Stile{side}{k}", (0.03, 0.06, 1.65), (side * (HALF(y) - 0.02), y, 0.12 + (1.65) / 2), M_OAKZ)
box("DeckheadPlanks", (4.4, Y1 - Y0 + 0.2, 0.04), (0, (Y0 + Y1) / 2, DECKHEAD + (0.04) / 2), M_DECKHEAD)
for k in range(8):
    y = Y0 + 0.35 + k * 0.62
    w = 2 * HALF(y)
    box(f"Beam{k}", (w, 0.14, DECKHEAD - BEAM_Z), (0, y, BEAM_Z + (DECKHEAD - BEAM_Z) / 2), M_BEAM, bevel=0.01)
    for side in (-1, 1):   # hanging knees
        kv = [(side * (HALF(y) - 0.02), y - 0.06, BEAM_Z), (side * (HALF(y) - 0.32), y - 0.06, BEAM_Z), (side * (HALF(y) - 0.02), y - 0.06, BEAM_Z - 0.4)]
        mesh_from(f"Knee{side}{k}", kv, [(0, 1, 2)], M_BEAM).modifiers.new("S", 'SOLIDIFY').thickness = 0.12
# a skylight in the deckhead over the table
SKY_Y = TABLE.y
box("SkylightWell", (0.9, 0.7, 0.3), (0, SKY_Y, DECKHEAD - 0.02), M_OAK) if False else None

# the stern: raked, five windows with leaded lights in a varnished frame
SB = 0.95; ST = 1.75             # sill and head heights of the stern windows
stern_y = Y1
sw = 2 * HALF(stern_y)
box("SternBelow", (sw, 0.12, SB), (0, stern_y + 0.06, 0 + (SB) / 2), M_PANEL)
box("SternAbove", (sw, 0.12, DECKHEAD - ST + 0.05), (0, stern_y + 0.06, ST + (DECKHEAD - ST + 0.05) / 2), M_PANEL)
box("SternSill", (sw, 0.3, 0.06), (0, stern_y - 0.08, SB - 0.06 + (0.06) / 2), M_OAK, bevel=0.01)
box("SternSeat", (sw - 0.1, 0.5, 0.42), (0, stern_y - 0.3, 0.0 + (0.42) / 2), M_OAK, bevel=0.01)
box("SternCushion", (sw - 0.2, 0.46, 0.06), (0, stern_y - 0.3, 0.42 + (0.06) / 2), M_CURTAIN, bevel=0.02)
nw_ = 5; mull = 0.09
lw = (sw - (nw_ + 1) * mull) / nw_
for k in range(nw_ + 1):
    x = -sw / 2 + mull / 2 + k * (lw + mull)
    box(f"SternMullion{k}", (mull, 0.14, ST - SB), (x, stern_y + 0.03, SB + (ST - SB) / 2), M_OAK)
for k in range(nw_):
    xc = -sw / 2 + mull + lw / 2 + k * (lw + mull)
    box(f"WindowGlass_Stern{k}", (lw, 0.01, ST - SB), (xc, stern_y + 0.06, SB + (ST - SB) / 2), M_PANE)
    for j in range(1, 5): box(f"Came{k}H{j}", (lw, 0.015, 0.012), (xc, stern_y + 0.05, SB + (ST - SB) * j / 5), M_LEAD)
    for j in range(1, 3): box(f"Came{k}V{j}", (0.012, 0.015, ST - SB), (xc - lw / 2 + lw * j / 3, stern_y + 0.05, SB), M_LEAD)
# the forward bulkhead with the door (open: the reader came through it) into the steerage
DOOR_X, DOOR_W, DOOR_H = -0.9, 0.7, 1.78
bw_ = 2 * HALF(Y0)
for (a, b_) in ((-bw_ / 2, DOOR_X - DOOR_W / 2), (DOOR_X + DOOR_W / 2, bw_ / 2)):
    box(f"Bulkhead{a:.1f}", (b_ - a, 0.08, DECKHEAD), ((a + b_) / 2, Y0 - 0.04, 0.0 + (DECKHEAD) / 2), M_PANEL)
box("BulkheadOverDoor", (DOOR_W, 0.08, DECKHEAD - DOOR_H), (DOOR_X, Y0 - 0.04, DOOR_H + (DECKHEAD - DOOR_H) / 2), M_PANEL)
for sx in (-1, 1): box(f"DoorCasing{sx}", (0.06, 0.1, DOOR_H), (DOOR_X + sx * (DOOR_W / 2 + 0.03), Y0, 0.0 + (DOOR_H) / 2), M_OAKZ)
box("DoorHead", (DOOR_W + 0.18, 0.1, 0.07), (DOOR_X, Y0, DOOR_H + (0.07) / 2), M_OAK)
DF = Frame((DOOR_X - DOOR_W / 2, Y0 - 0.02), math.radians(-100))
DF.box("DoorLeaf", (0.04, DOOR_W - 0.02, DOOR_H - 0.03), (0.0, DOOR_W / 2, 0.01 + (DOOR_H - 0.03) / 2), M_OAK, bevel=0.004)
sphere("DoorKnob", 0.025, DF.p(0.04, DOOR_W - 0.1, 1.0), M_BRASS, seg=8)
# the steerage beyond: a low space, the powder kegs and the muskets being brought aft
box("SteerageDeck", (3.6, 3.0, 0.02), (0, Y0 - 1.6, -0.01 + (0.02) / 2), M_FLOOR)
box("SteerageHead", (3.6, 3.0, 0.04), (0, Y0 - 1.6, DECKHEAD + (0.04) / 2), M_DECKHEAD)
for sx in (-1, 1): box(f"SteerageSide{sx}", (0.08, 3.0, DECKHEAD), (sx * 1.8, Y0 - 1.6, 0 + (DECKHEAD) / 2), M_BEAM)
box("SteerageEnd", (3.6, 0.1, DECKHEAD), (0, Y0 - 3.1, 0 + (DECKHEAD) / 2), M_BEAM)
for k in range(9):
    x = DOOR_X + rng.uniform(-0.8, 0.9); y = Y0 - rng.uniform(0.5, 2.3)
    lv = k > 6
    lathe(f"Keg{k}", [(0.0, 0.0), (0.16, 0.0), (0.19, 0.12), (0.2, 0.22), (0.19, 0.32), (0.16, 0.44), (0.0, 0.44)], (x, y, 0.0 if not lv else 0.0), M_KEG, steps=12,
          rot=(math.pi / 2 if lv else 0, 0, rng.uniform(0, 3)))
    for j, zz in enumerate((0.05, 0.39)):
        if not lv: cyl(f"KegHoop{k}{j}", 0.172, 0.03, (x, y, zz), M_IRON, verts=12)
# a stand of muskets against the steerage side, more lying in a chest
for k in range(6):
    x = -1.7 + 0.01 * k; y = Y0 - 0.7 - 0.12 * k
    tube(f"MusketBarrel{k}", [Vector((x + 0.06, y, 0.62)), Vector((x + 0.2, y, 1.55))], 0.011, M_IRON, sides=5)
    tube(f"MusketStock{k}", [Vector((x + 0.0, y, 0.02)), Vector((x + 0.04, y, 0.4)), Vector((x + 0.07, y, 0.7))], [0.04, 0.028, 0.02], M_STOCK, sides=5)
box("MusketChest", (1.0, 0.45, 0.4), (0.6, Y0 - 1.9, 0.0 + (0.4) / 2), M_KEG, bevel=0.01)
anchor("room.steerage", (DOOR_X, Y0 - 1.2, 0))

# ----------------------------------------------------------------------------- the fixed table, lockers, chairs; the hatch in the deck
TF = Frame((TABLE.x, TABLE.y), 0.0)
TF.box("TableTop", (0.95, 1.45, 0.05), (0, 0, 0.72 + (0.05) / 2), M_OAK, bevel=0.01)
for sy in (-1, 1): TF.box(f"TableFiddle{sy}", (0.95, 0.02, 0.03), (0, sy * 0.72, 0.77 + (0.03) / 2), M_OAK)
for sx in (-1, 1): TF.box(f"TableFiddleX{sx}", (0.02, 1.45, 0.03), (sx * 0.47, 0, 0.77 + (0.03) / 2), M_OAK)
TF.box("TablePillar", (0.16, 0.16, 0.7), (0, 0, 0.0 + (0.7) / 2), M_OAKZ, bevel=0.02)
TF.box("TableFoot", (0.5, 0.5, 0.06), (0, 0, 0.0 + (0.06) / 2), M_OAK, bevel=0.01)
for sx in (-1, 1):
    lx = sx * (HALF(TABLE.y) - 0.28)
    box(f"Locker{sx}", (0.5, 1.9, 0.44), (lx, TABLE.y + 0.1, 0.0 + (0.44) / 2), M_OAK, bevel=0.01)
    box(f"LockerCushion{sx}", (0.46, 1.85, 0.05), (lx, TABLE.y + 0.1, 0.44 + (0.05) / 2), M_CURTAIN, bevel=0.02)
def chair(name, x, y, yaw):
    F = Frame((x, y), yaw)
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = 0.44 if sy > 0 else 0.98
            F.cyl(f"{name}Leg{sx}{sy}", 0.018, h, (sx * 0.2, sy * 0.19, h / 2), M_OAK, verts=8)
    F.box(f"{name}Seat", (0.44, 0.42, 0.04), (0, 0, 0.43 + (0.04) / 2), M_OAK, bevel=0.008)
    F.box(f"{name}Splat", (0.16, 0.025, 0.42), (0, -0.19, 0.5 + (0.42) / 2), M_OAKZ, bevel=0.006)
    F.box(f"{name}Crest", (0.44, 0.04, 0.07), (0, -0.19, 0.92 + (0.07) / 2), M_OAK, bevel=0.01)
chair("ChairFwd", 0.62, TABLE.y - 0.62, 0.9)
chair("ChairAft", -0.1, TABLE.y + 1.05, math.pi - 0.2)
# on the table: a pewter jug and two cups, a closed log-book, a pair of dividers on a sea-chart folded away (not the map)
M_PEWTER = noisy("M_Pewter", [K.srgb((0.52, 0.52, 0.50)), K.srgb((0.62, 0.62, 0.60))], scale=40, rough=0.35)
lathe("Jug", [(0.0, 0.0), (0.05, 0.0), (0.06, 0.06), (0.045, 0.14), (0.05, 0.18), (0.0, 0.18)], TF.p(-0.2, 0.3, 0.745), M_PEWTER, steps=14)
for k in range(2): lathe(f"Tankard{k}", [(0.0, 0.0), (0.04, 0.0), (0.038, 0.11), (0.0, 0.11)], TF.p(-0.05 + 0.25 * k, -0.25 + 0.1 * k, 0.745), M_PEWTER, steps=12)
M_BOOKC = noisy("M_LogBook", [K.srgb((0.30, 0.18, 0.10)), K.srgb((0.36, 0.22, 0.12))], scale=20, rough=0.6)
M_PAGES = noisy("M_BookPages", [K.srgb((0.80, 0.76, 0.64)), K.srgb((0.72, 0.68, 0.56))], scale=200, rough=0.85, stretch=(1, 1, 30), bump=0.0)
I.book("LogBook", TF.p(0.2, 0.25, 0.745 + 0.02), (0.04, 0.24, 0.34), 0.2, M_BOOKC, M_PAGES, roll=math.pi / 2)
lathe("Inkhorn", [(0.0, 0.0), (0.025, 0.0), (0.02, 0.05), (0.0, 0.05)], TF.p(0.3, -0.1, 0.745), M_PEWTER, steps=10)
# the hatch in the deck to the space under the cabin (closed, a ring in it)
HT = Vector((0.0, -0.45, 0))
box("Hatch", (0.8, 0.7, 0.03), tuple(HT), M_OAK, bevel=0.006)
for sx in (-1, 1): box(f"HatchCoaming{sx}", (0.04, 0.74, 0.04), (HT.x + sx * 0.42, HT.y, 0.0 + (0.04) / 2), M_BEAM)
for sy in (-1, 1): box(f"HatchCoamingY{sy}", (0.88, 0.04, 0.04), (HT.x, HT.y + sy * 0.37, 0.0 + (0.04) / 2), M_BEAM)
tube("HatchRing", [tuple(HT + Vector((0.05 * math.cos(a), 0.05 * math.sin(a), 0.035))) for a in [2 * math.pi * k / 10 for k in range(11)]], 0.006, M_IRON, sides=4)
anchor("room.hatch", tuple(HT))

# ----------------------------------------------------------------------------- the berths astern on both sides: curtained openings, a bunk with blankets visible
for sx in (-1, 1):
    bx = sx * (HALF(1.6) - 0.02)
    for k, by in enumerate((-0.9, 1.8)):
        if k == 0 and sx < 0: continue
        F = Frame((bx, by), -sx * math.pi / 2)        # local +Y into the cabin
        F.box(f"BerthFrame{sx}{k}", (0.95, 0.06, 0.05), (0, 0.0, 1.7 + (0.05) / 2), M_OAK)
        for ex in (-1, 1): F.box(f"BerthPost{sx}{k}{ex}", (0.06, 0.06, 1.7), (ex * 0.45, 0.0, 0.0 + (1.7) / 2), M_OAKZ)
        F.box(f"BerthBoard{sx}{k}", (0.9, 0.06, 0.18), (0, 0.0, 0.45 + (0.18) / 2), M_OAK)
        F.box(f"BerthBlanket{sx}{k}", (0.85, 0.4, 0.08), (0, -0.25, 0.5 + (0.08) / 2), M_BLANKET, bevel=0.03)
        # the berth recess behind (dark) and a curtain drawn half across on a rod
        F.box(f"BerthBack{sx}{k}", (0.95, 0.04, 1.75), (0, -0.62, 0.0 + (1.75) / 2), M_PANEL)
        cyl(f"BerthRod{sx}{k}", 0.008, 0.9, F.p(0, 0.04, 1.6), M_BRASS, verts=6, rot=(0, math.pi / 2, F.yaw))
        cv = []; cf = []
        for i in range(9):
            u = -0.45 + 0.5 * i / 8
            for z in (1.58, 0.5):
                cv.append(F.p(u, 0.05 + 0.025 * math.sin(i * 2.1), z))
            if i: cf.append((2 * i - 2, 2 * i, 2 * i + 1, 2 * i - 1))
        c = mesh_from(f"BerthCurtain{sx}{k}", cv, cf, M_BCURT, smooth=True)
        K.add_sway(c, lambda p: max(0.0, min(1.0, (1.6 - p.z) / 1.1)) * 0.3)

# ----------------------------------------------------------------------------- the hanging lantern (lit), a barometer, the rudder head trunk
LT = Vector((TABLE.x + 0.05, TABLE.y - 0.05, BEAM_Z - 0.45))
tube("LanternChain", [LT + Vector((0, 0, 0.3)), Vector((LT.x, LT.y, BEAM_Z))], 0.005, M_BRASS, sides=4)
lathe("Lantern", [(0.0, 0.0), (0.07, 0.0), (0.07, 0.02), (0.06, 0.03), (0.06, 0.2), (0.07, 0.21), (0.04, 0.27), (0.01, 0.3), (0.0, 0.3)], tuple(LT), M_BRASS, steps=8)
cyl("LanternGlass", 0.058, 0.16, tuple(LT + Vector((0, 0, 0.11))), M_GLOW, verts=8)
cyl("RudderTrunk", 0.18, 0.9, (0.0, Y1 - 0.75, 0.45), M_OAKZ, verts=10) if False else None
lathe("Barometer", [(0.0, 0.0), (0.04, 0.0), (0.04, 0.7), (0.07, 0.75), (0.07, 0.9), (0.0, 0.92)], (HALF(0.0) - 0.08, 0.0, 0.85), M_OAKZ, steps=10)

# ----------------------------------------------------------------------------- outside the stern: harbour water (water.ocean) and the far quays (backdrop)
wv = []; wf = []; wc = []
NA = 24
for j, r in enumerate((0.3, 4, 12, 30, 70)):
    for i in range(NA + 1):
        a = math.radians(-80 + 160 * i / NA)
        wv.append((r * math.sin(a), Y1 + 0.2 + r * math.cos(a), WL))
for j in range(4):
    for i in range(NA): wf.append((j * (NA + 1) + i, j * (NA + 1) + i + 1, (j + 1) * (NA + 1) + i + 1, (j + 1) * (NA + 1) + i))
wat = mesh_from("water.ocean.harbour", wv, wf, M_WATER)
ul = wat.data.uv_layers.new(name="UVMap")
for li, l in enumerate(wat.data.loops): ul.data[li].uv = (wv[l.vertex_index][0] / 10, wv[l.vertex_index][1] / 10)
# the ship's own counter below the windows (outside), so the water does not meet the windows
box("CounterOutside", (sw + 0.3, 0.2, 2.2), (0, Y1 + 0.2, WL - 0.3), M_BEAM)
vv = []; vf = []
for j in range(4):
    for i in range(17):
        a = math.radians(-75 + 150 * i / 16); r = 75
        vv.append((r * math.sin(a), Y1 + r * math.cos(a), WL - 0.5 + 24 * j / 3))
for j in range(3):
    for i in range(16): vf.append((j * 17 + i, j * 17 + i + 1, (j + 1) * 17 + i + 1, (j + 1) * 17 + i))
view = mesh_from("HarbourView", vv, vf, M_VIEW)
view.visible_shadow = False; view.visible_diffuse = False; view.visible_glossy = False

# ----------------------------------------------------------------------------- light: afternoon sun behind the stern on the water, sky through the windows, the lantern
light_obj("Lamp.sun", 'SUN', 3.5, (1.0, 0.92, 0.80), (0, 30, 20), direction=(0.25, -0.85, -0.45), angle=math.radians(1.5))
ld = bpy.data.lights.new("Lamp.sternSky", 'AREA'); ld.energy = 160.0; ld.color = (0.86, 0.90, 1.0); ld.shape = 'RECTANGLE'; ld.size = sw - 0.2; ld.size_y = ST - SB
wl = bpy.data.objects.new("Lamp.sternSky", ld); wl.location = (0, Y1 + 0.2, (SB + ST) / 2); K.link(wl)
wl.rotation_euler = Vector((0, -1, -0.1)).to_track_quat('-Z', 'Y').to_euler()
# sun glitter off the water thrown up onto the deckhead: a soft warm area light low outside the windows aimed up
ld2 = bpy.data.lights.new("Lamp.waterBounce", 'AREA'); ld2.energy = 60.0; ld2.color = (1.0, 0.94, 0.82); ld2.size = 2.0
wb = bpy.data.objects.new("Lamp.waterBounce", ld2); wb.location = (0, Y1 + 0.6, SB - 0.1); K.link(wb)
wb.rotation_euler = Vector((0, -1, 0.9)).to_track_quat('-Z', 'Y').to_euler()
light_obj("Lamp.lantern", 'POINT', 9.0, (1.0, 0.66, 0.34), tuple(LT + Vector((0, 0, 0.11))), shadow_soft_size=0.04)
light_obj("Lamp.steerage", 'POINT', 12.0, (0.9, 0.85, 0.75), (DOOR_X, Y0 - 1.6, 1.6), shadow_soft_size=0.4)
world = bpy.data.worlds.new("Harbour"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.62, 0.70, 0.82, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors, sources
S.reader(READER, (TABLE.x - READER.x, TABLE.y - READER.y))
anchor("scene.centre", tuple(TABLE))
S.fx("fx.lantern.cabin", tuple(LT + Vector((0, 0, 0.1))), 0.03)
sound("rigging", "deck", (0.0, 0.0, 4.0))
sound("gulls", "harbour", (6.0, Y1 + 20.0, 6.0))
sound("surf", "counter", (0.0, Y1 + 1.0, WL))
page = S.page_preview()
K.apply_transforms()

E = READER + Vector((0, 0, S.EYE))
fwd = (TABLE - READER).normalized()
cams = S.eye_cams([("Reader", 0), ("Left", -75), ("Right", 75), ("Behind", 180)], dz=-0.45, dist=4.0, extra=[
    ("Page", E, E + fwd * 4 + Vector((0, 0, -0.45)), 17),
    ("Windows", Vector((0.6, 0.0, 1.3)), Vector((-0.3, Y1, 1.2)), 22),
])
probs = S.check_reader(ignore=("PagePreview",))
K.print_budget(exclude=("PagePreview",))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.0, captures_dir=ARGS.captures)

if ARGS.export or ARGS.bake:
    S.export(SID, cams, page=page, unlit_emit=("M_HarbourView", "M_LanternGlow"),
             remove=[o.name for o in bpy.data.objects if o.name.startswith("WindowGlass_")],
             keep_names={"M_HarbourView": "far.harbourView", "M_HarbourWater": "water.ocean.harbour", "M_BerthCurtain": "cloth.curtain.berths",
                         "M_LanternGlow": "MESH_LanternGlow"},
             size_for={"M_PanelPaint": (2048, 64, 1024), "M_Varnished": (1024, 128, 512), "M_VarnishedZ": (512, 64, 256), "M_DeckBeams": (1024, 64, 512),
                       "M_Deckhead": (1024, 64, 512), "M_DeckPlanks": (1024, 128, 1024), "M_HarbourView": (1024,), "M_BerthCurtain": (512, 64, 256),
                       "M_PowderKeg": (512, 64, 256), "M_HarbourWater": (512, 32, 256)},
             default_size=(256, 32, 128))
print("DONE")
