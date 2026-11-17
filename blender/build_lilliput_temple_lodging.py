"""
Fable step-in room: inside Gulliver's temple house at Lilliput (Gulliver's Travels, Part I, chapters 6 and 7).

"... an ancient temple, esteemed to be the largest in the whole kingdom; which having been polluted some years before
by an unnatural murder, was ... stripped of all its ornaments and furniture" (chapter 1) ... "The great gate fronting
to the north was about four feet high, and almost two feet wide" ... "Six hundred beds of the common measure were
brought in carriages and worked up in my house; a hundred and fifty of their beds, sewn together, made up the breadth
and length; and these were four double ... The same computation they made for my sheets, blankets, and coverlets" ...
"my table ... was set on the floor, and a table and chair ... made out of the largest trees in the royal park" ...
"I had a table placed upon the same at the top of my house"? no: "my dinner was brought ... on a table" ... "a
movable rim quite round, of five inches high, to prevent accidents" ... "the dishes and barrels drawn up by certain
cords, as we draw the bucket up a well" ... "they quilted ... my shirts" ... (chapter 7) "the lord's close chair".

The inside of the Lilliputian temple, now Gulliver's lodging, at dusk: a long low hall of grey dressed stone under a
shallow stone vault that clears his head by little (2.3 m at the crown), the empty niches where the images were taken
out, two small barred windows letting in the last of the sun, the north gate (a little door to him) shut. His bed of
six hundred Lilliputian beds sewn together, four deep, with quilted sheets and coverlets along the west wall; the table
and chair hewn from the largest trees of the royal park, the table with its five-inch movable rim; on it, a handful of
tiny chairs of state set out, a little coach without its horses, Lilliputian dishes, cups and casks, the cords and
pulley-blocks they are drawn up by; his quilted shirts folded on a stool-like log, his coat with its deep pockets over
the chair; a few tiny lanterns lit along the walls. No people, no horses.

Reader: standing by the chair, facing the rimmed table; the closed north gate to the left.

  blender -b -P blender/build_lilliput_temple_lodging.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_lilliput_temple_lodging.py -- --render --samples 32 --res 1280 --cams reader,left,right,behind,table
  blender -b -P blender/build_lilliput_temple_lodging.py -- --export
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b5 as S
import pride_kit as K
import mobydick_kit as MK
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, anchor, sound, light_obj)

SID = "lilliput-temple-lodging"
ARGS = S.setup(SID, seed=1726)
scene = K.scene
scene.cycles.max_bounces = 8; scene.cycles.diffuse_bounces = 5
rng = random.Random(1726)

X0, X1, Y0, Y1 = -3.0, 3.0, -2.6, 2.6
WALL_H, CROWN = 1.85, 2.3
READER = Vector((0.55, -1.35, 0))
TABLE = Vector((0.4, 0.95, 0))


def ashlar(name="M_Ashlar"):
    """dressed grey limestone in Lilliputian courses (a 0.065 m course, blocks about 0.13 m long: small to Gulliver), fine pocked surface, darker joints,
    soot and damp low down."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1700, 0))
    z = s.outputs["Z"]
    row = math_(nt, 'FLOOR', math_(nt, 'DIVIDE', z, 0.065, (-1500, 300)), None, (-1400, 300))
    fz = math_(nt, 'FRACT', math_(nt, 'DIVIDE', z, 0.065, (-1500, 450)), None, (-1400, 450))
    along = math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-1500, 150))
    off = math_(nt, 'MULTIPLY', math_(nt, 'FRACT', math_(nt, 'MULTIPLY', row, 0.618, (-1400, 0)), None, (-1300, 0)), 0.13, (-1200, 0))
    fa = math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', along, off, (-1100, 100)), 0.13, (-1000, 100)), None, (-900, 100))
    jz = maprange(nt, math_(nt, 'MINIMUM', fz, math_(nt, 'SUBTRACT', 1.0, fz, (-1300, 500)), (-1200, 500)), 0.0, 0.05, 0, 1, (-1100, 500))
    ja = maprange(nt, math_(nt, 'MINIMUM', fa, math_(nt, 'SUBTRACT', 1.0, fa, (-800, 200)), (-700, 200)), 0.0, 0.03, 0, 1, (-600, 200))
    joint = math_(nt, 'MULTIPLY', jz, ja, (-500, 300))
    cell = node(nt, "ShaderNodeCombineXYZ", (-800, 600)); nt.links.new(row, cell.inputs["X"]); nt.links.new(math_(nt, 'FLOOR', math_(nt, 'DIVIDE', math_(nt, 'ADD', along, off, (-1000, 700)), 0.13, (-900, 700)), None, (-850, 700)), cell.inputs["Y"])
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-650, 600), noise_dimensions='3D'); nt.links.new(cell.outputs[0], wn.inputs["Vector"])
    tone = ramp(nt, [(0.0, c4(K.srgb((0.50, 0.48, 0.44)))), (0.5, c4(K.srgb((0.60, 0.58, 0.53)))), (1.0, c4(K.srgb((0.66, 0.63, 0.56))))], (-450, 600))
    nt.links.new(wn.outputs["Value"], tone.inputs["Fac"])
    n = noise_(nt, co, 25.0, 5, 0.7, loc=(-700, -200))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, tone.outputs["Color"], maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.85, 1.08, (-500, -200)), (-300, 400))
    col = mix_rgb(nt, 'MIX', math_(nt, 'SUBTRACT', 1.0, joint, (-300, 200)), col, c4(K.srgb((0.30, 0.28, 0.25))), (-150, 400))
    low = maprange(nt, z, 0.0, 0.5, 0.25, 0.0, (-500, -400))
    col = mix_rgb(nt, 'MULTIPLY', low, col, (0.55, 0.52, 0.46, 1), (0, 400))
    col = K.ao_mul(nt, col, 0.3, 0.45, (100, -300))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, math_(nt, 'ADD', joint, math_(nt, 'MULTIPLY', n.outputs["Fac"], 0.2, (-300, -500)), (-200, -500)), 0.6, 0.006)
    return m


M_STONE = ashlar()
M_FLOOR = noisy("M_FloorFlags", [K.srgb((0.42, 0.40, 0.36)), K.srgb((0.50, 0.48, 0.43)), K.srgb((0.36, 0.35, 0.32))], scale=1.5, rough=0.6, bump=0.3, warp=0.3)
M_LOG = MK.timber_mat("M_RoughTimber", base=(0.30, 0.22, 0.14), dark=(0.10, 0.07, 0.045), light=(0.42, 0.32, 0.21), along='X', rough=(0.55, 0.85), grime=0.4)
M_LOGY = MK.timber_mat("M_RoughTimberY", base=(0.30, 0.22, 0.14), dark=(0.10, 0.07, 0.045), light=(0.42, 0.32, 0.21), along='Z', rough=(0.55, 0.85), grime=0.4)
M_BARK = noisy("M_OakBark", [K.srgb((0.18, 0.15, 0.12)), K.srgb((0.28, 0.24, 0.19)), K.srgb((0.12, 0.10, 0.08))], scale=8, rough=0.9, stretch=(1, 1, 0.25), bump=0.9, bump_dist=0.01)
M_DOOR = MK.timber_mat("M_GateTimber", base=(0.22, 0.15, 0.09), dark=(0.07, 0.05, 0.03), light=(0.32, 0.22, 0.14), along='Z', rough=(0.5, 0.8), grime=0.5)
M_IRON = MK.iron_mat("M_Iron", rust=0.4)


def quilt_mat(name, base, seam, cell=(0.14, 0.08)):
    """the Lilliputian beds or sheets sewn edge to edge: a grid of little quilted panels, each slightly different."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1500, 0))
    fx = math_(nt, 'FRACT', math_(nt, 'DIVIDE', s.outputs["Y"], cell[0], (-1300, 100)), None, (-1200, 100))
    fy = math_(nt, 'FRACT', math_(nt, 'DIVIDE', s.outputs["X"], cell[1], (-1300, -50)), None, (-1200, -50))
    e = math_(nt, 'MINIMUM', math_(nt, 'MINIMUM', fx, math_(nt, 'SUBTRACT', 1.0, fx, (-1100, 150)), (-1000, 150)),
              math_(nt, 'MINIMUM', fy, math_(nt, 'SUBTRACT', 1.0, fy, (-1100, -100)), (-1000, -100)), (-900, 50))
    puff = maprange(nt, e, 0.0, 0.18, 0, 1, (-800, 50))
    cx = math_(nt, 'FLOOR', math_(nt, 'DIVIDE', s.outputs["Y"], cell[0], (-1300, 300)), None, (-1200, 300))
    cy = math_(nt, 'FLOOR', math_(nt, 'DIVIDE', s.outputs["X"], cell[1], (-1300, 450)), None, (-1200, 450))
    cc = node(nt, "ShaderNodeCombineXYZ", (-1050, 350)); nt.links.new(cx, cc.inputs["X"]); nt.links.new(cy, cc.inputs["Y"])
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-900, 350), noise_dimensions='3D'); nt.links.new(cc.outputs[0], wn.inputs["Vector"])
    col = mix_rgb(nt, 'MULTIPLY', 1.0, c4(base), maprange(nt, wn.outputs["Value"], 0, 1, 0.9, 1.06, (-750, 350)), (-600, 200))
    col = mix_rgb(nt, 'MIX', maprange(nt, puff, 0.0, 0.3, 1, 0, (-650, 0)), col, c4(seam), (-450, 200))
    col = K.ao_mul(nt, col, 0.12, 0.45, (-300, -300))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9; b.inputs["Sheen Weight"].default_value = 0.5
    bump_from(nt, b, puff, 0.6, 0.008)
    return m


M_TICK = quilt_mat("M_BedTicking", K.srgb((0.72, 0.66, 0.52)), K.srgb((0.45, 0.40, 0.30)))
M_SHEET = quilt_mat("M_QuiltedSheet", K.srgb((0.86, 0.84, 0.78)), K.srgb((0.66, 0.63, 0.56)), cell=(0.1, 0.06))
M_COVER = quilt_mat("M_Coverlet", K.srgb((0.46, 0.20, 0.16)), K.srgb((0.28, 0.12, 0.10)), cell=(0.12, 0.09))
M_COAT = noisy("M_CoatCloth", [K.srgb((0.18, 0.20, 0.26)), K.srgb((0.24, 0.26, 0.32)), K.srgb((0.14, 0.15, 0.20))], scale=12, rough=0.95, bump=0.6, bump_dist=0.002, sheen=0.4)
M_BRASSB = plain("M_Buttons", K.srgb((0.62, 0.48, 0.24)), rough=0.35)
M_PEWTER = noisy("M_Pewter", [K.srgb((0.56, 0.56, 0.54)), K.srgb((0.66, 0.66, 0.63))], scale=40, rough=0.4)
M_TINYWOOD = MK.timber_mat("M_TinyFurniture", base=(0.24, 0.12, 0.06), dark=(0.08, 0.04, 0.02), light=(0.36, 0.20, 0.10), along='X', rough=(0.3, 0.6), grime=0.2, scale=6.0)
M_VELVET = noisy("M_StateVelvet", [K.srgb((0.42, 0.08, 0.10)), K.srgb((0.52, 0.12, 0.14))], scale=60, rough=0.7, sheen=0.9)
M_GILT = plain("M_TinyGilt", K.srgb((0.75, 0.58, 0.26)), rough=0.3)
M_CORD = noisy("M_Cord", [K.srgb((0.62, 0.54, 0.38)), K.srgb((0.50, 0.42, 0.28))], scale=200, rough=0.9, stretch=(1, 1, 8))
M_GLOW = plain("M_LanternGlow", (0.0, 0.0, 0.0), rough=0.5, emission=(1.0, 0.70, 0.36), strength=4.0)
M_SKYVIEW = plain("M_DuskView", (0.0, 0.0, 0.0), rough=0.5, emission=(0.98, 0.70, 0.46), strength=1.2)

# ----------------------------------------------------------------------------- the hall: walls with niches, windows, the north gate; a shallow vault
def wall_panel(name, a, b_, z0, z1, t=0.5):
    a = Vector(a); b_ = Vector(b_); d = b_ - a; L = d.length; c = (a + b_) / 2
    yaw = math.atan2(d.y, d.x)
    box(name, (L, t, z1 - z0), (c.x - math.sin(yaw) * t / 2 * 0, c.y, z0), M_STONE, rot=(0, 0, yaw))
# walls as boxes round openings: N wall has the gate (x -1.6, 0.6 wide, 1.2 high), two windows high in the S? no: windows on the east and west walls
GATE_X, GATE_W, GATE_H = -1.7, 0.62, 1.22
WINS = [('E', 0.5, 0.42, 1.0, 1.5), ('W', -0.2, 0.42, 1.0, 1.5)]      # wall, along-centre, width, z0, z1
T = 0.6
def run(wall, fixed, a0, a1, holes):
    """holes: (centre, width, z0, z1)"""
    cuts = sorted([a0, a1] + [c - w / 2 for c, w, *_ in holes] + [c + w / 2 for c, w, *_ in holes])
    for i in range(len(cuts) - 1):
        u0, u1 = cuts[i], cuts[i + 1]
        hz = [(z0, z1) for c, w, z0, z1 in holes if u0 >= c - w / 2 - 1e-6 and u1 <= c + w / 2 + 1e-6]
        spans = [(0.0, WALL_H + 0.02)] if not hz else [(0.0, hz[0][0]), (hz[0][1], WALL_H + 0.02)]
        for (z0, z1) in spans:
            if z1 - z0 < 1e-3: continue
            if wall in ('N', 'S'):
                box(f"Wall{wall}{i}{z0:.1f}", (u1 - u0, T, z1 - z0), ((u0 + u1) / 2, fixed, z0 + (z1 - z0) / 2), M_STONE)
            else:
                box(f"Wall{wall}{i}{z0:.1f}", (T, u1 - u0, z1 - z0), (fixed, (u0 + u1) / 2, z0 + (z1 - z0) / 2), M_STONE)
run('N', Y1 + T / 2, X0 - T, X1 + T, [(GATE_X, GATE_W, 0.0, GATE_H)])
run('S', Y0 - T / 2, X0 - T, X1 + T, [])
run('E', X1 + T / 2, Y0, Y1, [(w[1], w[2], w[3], w[4]) for w in WINS if w[0] == 'E'])
run('W', X0 - T / 2, Y0, Y1, [(w[1], w[2], w[3], w[4]) for w in WINS if w[0] == 'W'])
# the vault: a shallow segmental barrel along Y, springing from the side walls
vv = []; vf = []
NV = 14
for j, y in enumerate((Y0 - T, Y1 + T)):
    for i in range(NV + 1):
        t = i / NV; x = X0 + (X1 - X0) * t
        z = WALL_H + (CROWN - WALL_H) * math.sin(math.pi * t) ** 0.8
        vv.append((x, y, z))
for i in range(NV): vf.append((i, NV + 1 + i, NV + 1 + i + 1, i + 1))
vault = mesh_from("Vault", vv, vf, M_STONE, smooth=True); vault.modifiers.new("S", 'SOLIDIFY').thickness = -0.25
# the end walls up into the vault (lunettes)
for y, sgn in ((Y1, 1), (Y0, -1)):
    lv = [(X0 - T, y + sgn * T / 2, WALL_H)] + [(X0 + (X1 - X0) * i / NV, y + sgn * T / 2, WALL_H + (CROWN - WALL_H) * math.sin(math.pi * i / NV) ** 0.8) for i in range(NV + 1)] + [(X1 + T, y + sgn * T / 2, WALL_H)]
    lo = mesh_from(f"Lunette{sgn}", lv, [tuple(range(len(lv)))], M_STONE); lo.modifiers.new("S", 'SOLIDIFY').thickness = T
# springing course and transverse ribs
for k, y in enumerate((-1.3, 0.0, 1.3)):
    rv = []
    for i in range(NV + 1):
        t = i / NV; x = X0 + (X1 - X0) * t; z = WALL_H + (CROWN - WALL_H) * math.sin(math.pi * t) ** 0.8 - 0.02
        rv.append((x, y, z))
    tube(f"Rib{k}", rv, 0.08, M_STONE, sides=4)
for sx, x in ((-1, X0), (1, X1)):
    box(f"Springing{sx}", (0.12, Y1 - Y0, 0.12), (x - sx * 0.04, 0, WALL_H - 0.12 + (0.12) / 2), M_STONE, bevel=0.02)
box("Floor", (X1 - X0 + 1.4, Y1 - Y0 + 1.4, 0.06), (0, 0, -0.06 + (0.06) / 2), M_FLOOR)
# empty niches: shallow round-headed recesses in the side walls where the images stood (a dark back, a sill)
M_NICHE = noisy("M_NicheBack", [K.srgb((0.30, 0.29, 0.27)), K.srgb((0.38, 0.36, 0.33))], scale=10, rough=0.9, bump=0.3)
for k, (wall, u) in enumerate((('E', -1.6), ('E', 1.7), ('W', 1.4), ('W', -1.7), ('S', -1.5), ('S', 1.6))):
    if wall == 'E': c = Vector((X1 - 0.01, u, 0.55)); yaw = math.pi / 2
    elif wall == 'W': c = Vector((X0 + 0.01, u, 0.55)); yaw = -math.pi / 2
    else: c = Vector((u, Y0 + 0.01, 0.55)); yaw = 0.0
    F = Frame((c.x, c.y), yaw, z=0.0)
    F.box(f"NicheBack{k}", (0.42, 0.02, 0.85), (0, 0.0, 0.55 + (0.85) / 2), M_NICHE)
    F.box(f"NicheSill{k}", (0.5, 0.1, 0.05), (0, 0.04, 0.5 + (0.05) / 2), M_STONE, bevel=0.01)
    F.box(f"NicheJambL{k}", (0.05, 0.08, 0.85), (-0.24, 0.035, 0.55 + (0.85) / 2), M_STONE, bevel=0.01)
    F.box(f"NicheJambR{k}", (0.05, 0.08, 0.85), (0.24, 0.035, 0.55 + (0.85) / 2), M_STONE, bevel=0.01)
    hv = [F.p(0.26 * math.cos(math.pi * i / 10), 0.035, 1.4 + 0.24 * math.sin(math.pi * i / 10)) for i in range(11)]
    tube(f"NicheArch{k}", hv, 0.035, M_STONE, sides=5)
    # pale outline on the back where a statue's base stood
    F.box(f"NicheMark{k}", (0.3, 0.005, 0.06), (0, 0.012, 0.56), noisy("M_StoneScar", [K.srgb((0.60, 0.58, 0.54)), K.srgb((0.66, 0.64, 0.6))], scale=20, rough=0.9) if k == 0 else bpy.data.materials["M_StoneScar"])
# the north gate (shut): a heavy little door of planks with iron straps, in a moulded stone surround
F = Frame((GATE_X, Y1), math.pi)
F.box("GateLeaf", (GATE_W, 0.08, GATE_H - 0.02), (0, 0.12, 0.0 + (GATE_H - 0.02) / 2), M_DOOR, bevel=0.005)
for z in (0.25, 0.95): F.box(f"GateStrap{z}", (GATE_W - 0.04, 0.012, 0.05), (0, 0.17, z), M_IRON)
sphere("GateRing", 0.03, F.p(0.18, 0.18, 0.6), M_IRON, seg=8, scale=(1, 0.3, 1))
for sx in (-1, 1): F.box(f"GateJamb{sx}", (0.08, 0.1, GATE_H + 0.1), (sx * (GATE_W / 2 + 0.04), 0.02, 0.0 + (GATE_H + 0.1) / 2), M_STONE, bevel=0.01)
F.box("GateLintel", (GATE_W + 0.25, 0.12, 0.14), (0, 0.02, GATE_H + (0.14) / 2), M_STONE, bevel=0.01)
anchor("room.northGate", F.p(0, 0.3, 0))
# the windows: small, deep, with stone mullions; a dusky sky and treetops beyond (unlit backdrop)
for wall, u, w, z0, z1 in WINS:
    sgn = 1 if wall == 'E' else -1
    x = X1 if wall == 'E' else X0
    box(f"WinBar{wall}", (0.05, 0.05, z1 - z0), (x + sgn * T * 0.5, u, z0 + (z1 - z0) / 2), M_IRON)
    box(f"WinBarH{wall}", (0.05, w, 0.04), (x + sgn * T * 0.5, u, (z0 + z1) / 2), M_IRON)
    vv = [(x + sgn * 2.5, u - 2.2, z0 - 1.5), (x + sgn * 2.5, u + 2.2, z0 - 1.5), (x + sgn * 2.5, u + 2.2, z1 + 1.5), (x + sgn * 2.5, u - 2.2, z1 + 1.5)]
    o = mesh_from(f"far.duskView{wall}", vv, [(0, 1, 2, 3)], M_SKYVIEW)
    o.visible_shadow = False; o.visible_diffuse = False

# ----------------------------------------------------------------------------- Gulliver's bed: 150 Lilliputian beds a layer, four deep, quilted sheets and coverlets
BED = Frame((X0 + 0.62, 0.15), -math.pi / 2)          # along the west wall, head to the north
bed_w, bed_l = 1.05, 2.15
for k in range(4):
    BED.box(f"BedLayer{k}", (bed_l, bed_w, 0.07), (0, 0, 0.005 + 0.072 * k + (0.07) / 2), M_TICK, bevel=0.02)
# sheets and the coverlet, turned back at the head, falling a little over the side
sv = []; sf = []
NX, NY = 18, 10
for j in range(NY + 1):
    for i in range(NX + 1):
        u = (i / NX - 0.5) * (bed_l - 0.1); v = (j / NY - 0.5) * (bed_w + 0.12)
        z = 0.31 + 0.03 * noise.noise(Vector((u * 2, v * 2, 0.3)))
        if abs(v) > bed_w / 2: z -= (abs(v) - bed_w / 2) * 2.0; v = math.copysign(bed_w / 2 + 0.01, v)
        if u < -bed_l / 2 + 0.6: z += 0.0
        sv.append(BED.p(u + 0.0, v, z))
for j in range(NY):
    for i in range(NX):
        if i < 5: continue          # the coverlet starts 0.6 m from the head (turned back)
        sf.append((j * (NX + 1) + i, j * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i))
cov = mesh_from("Coverlet", sv, sf, M_COVER, smooth=True); cov.modifiers.new("S", 'SOLIDIFY').thickness = 0.03
BED.box("SheetTop", (bed_l - 0.05, bed_w - 0.02, 0.012), (0, 0, 0.292 + (0.012) / 2), M_SHEET)
BED.box("CoverletFold", (0.2, bed_w, 0.05), (-bed_l / 2 + 0.62, 0, 0.3 + (0.05) / 2), M_COVER, bevel=0.02)
for k, v in enumerate((-0.22, 0.22)):      # bolsters made of many little pillows
    BED.box(f"Bolster{k}", (0.32, 0.42, 0.1), (-bed_l / 2 + 0.22, v, 0.3 + (0.1) / 2), M_SHEET, bevel=0.04)
anchor("room.bed", BED.p(0, 0, 0))

# ----------------------------------------------------------------------------- the table and chair from the largest trees in the royal park
TF = Frame((TABLE.x, TABLE.y), 0.0)
TT = 0.74
TF.box("TableTop", (1.35, 0.8, 0.07), (0, 0, TT - 0.07 + (0.07) / 2), M_LOG, bevel=0.01)
for sx in (-1, 1):
    for sy in (-1, 1):
        tube(f"TableLeg{sx}{sy}", [TF.p(sx * 0.56, sy * 0.3, 0.0), TF.p(sx * 0.55, sy * 0.3, TT - 0.07)], [0.07, 0.06], M_BARK, sides=7)
TF.box("TableRailX", (1.1, 0.06, 0.08), (0, 0, 0.18 + (0.08) / 2), M_LOG)
# the movable rim, five Lilliputian inches high (a low wooden fence round the edge)
for sy in (-1, 1): TF.box(f"RimY{sy}", (1.33, 0.012, 0.035), (0, sy * 0.385, TT + (0.035) / 2), M_TINYWOOD)
for sx in (-1, 1): TF.box(f"RimX{sx}", (0.012, 0.78, 0.035), (sx * 0.66, 0, TT + (0.035) / 2), M_TINYWOOD)
for k in range(24):
    t = k / 24
    if t < 0.5: x = -0.66 + 1.32 * (t / 0.5); y = 0.385
    else: x = 0.66 - 1.32 * ((t - 0.5) / 0.5); y = -0.385
    TF.box(f"RimPost{k}", (0.008, 0.008, 0.04), (x, y, TT + (0.04) / 2), M_TINYWOOD)
# Lilliputian things on the table: chairs of state, a coach without its horses, dishes, cups and casks
def tiny_chair(name, x, y, yaw, state=False):
    F = Frame(TF.p(x, y, 0)[:2], yaw, z=TT)
    s = 1.5 if state else 1.0
    F.box(f"{name}Seat", (0.038 * s, 0.035 * s, 0.006), (0, 0, 0.035 * s + (0.006) / 2), M_VELVET if state else M_TINYWOOD)
    F.box(f"{name}Back", (0.038 * s, 0.005, 0.05 * s), (0, -0.016 * s, 0.038 * s + (0.05 * s) / 2), M_VELVET if state else M_TINYWOOD)
    if state: F.box(f"{name}Crest", (0.044 * s, 0.006, 0.01), (0, -0.016 * s, 0.09 * s + (0.01) / 2), M_GILT)
    for sx in (-1, 1):
        for sy in (-1, 1): F.box(f"{name}Leg{sx}{sy}", (0.004, 0.004, 0.035 * s), (sx * 0.016 * s, sy * 0.014 * s, 0.0 + (0.035 * s) / 2), M_GILT if state else M_TINYWOOD)
for k, (x, y) in enumerate(((-0.42, 0.22), (-0.32, 0.25), (-0.22, 0.24), (-0.12, 0.26))):
    tiny_chair(f"StateChair{k}", x, y, math.pi + rng.uniform(-0.2, 0.2), state=True)
for k, (x, y) in enumerate(((-0.5, -0.1), (-0.45, -0.22), (0.45, 0.25))):
    tiny_chair(f"TinyChair{k}", x, y, rng.uniform(0, 6.28))
# the coach: a little box body on four wheels, its pole lying on the table
CF = Frame(TF.p(0.32, -0.16, 0)[:2], 0.6, z=TT)
CF.box("CoachBody", (0.09, 0.15, 0.08), (0, 0, 0.035 + (0.08) / 2), M_VELVET, bevel=0.006)
CF.box("CoachRoof", (0.1, 0.16, 0.01), (0, 0, 0.115 + (0.01) / 2), M_GILT)
for sx in (-1, 1):
    for sy, r_ in ((-1, 0.032), (1, 0.024)):
        cyl(f"CoachWheel{sx}{sy}", r_, 0.006, CF.p(sx * 0.055, sy * 0.06, r_), M_TINYWOOD, verts=12, rot=(0, math.pi / 2, CF.yaw))
CF.box("CoachPole", (0.006, 0.16, 0.006), (0, 0.14, 0.018), M_TINYWOOD)
# dishes: a ring of pewter plates and covered dishes, cups, two casks (a Lilliputian hogshead)
for k in range(9):
    x = rng.uniform(-0.1, 0.25); y = rng.uniform(-0.05, 0.2)
    lathe(f"Dish{k}", [(0.0, 0.0), (0.025, 0.0), (0.035, 0.006), (0.0, 0.004)], TF.p(x, y, TT), M_PEWTER, steps=12)
for k in range(4):
    lathe(f"CoverDish{k}", [(0.0, 0.0), (0.03, 0.0), (0.03, 0.015), (0.02, 0.03), (0.004, 0.035), (0.0, 0.04)], TF.p(-0.05 + 0.08 * k, -0.18, TT), M_PEWTER, steps=12)
for k in range(5):
    lathe(f"Cup{k}", [(0.0, 0.0), (0.006, 0.0), (0.008, 0.015), (0.0, 0.015)], TF.p(0.15 + 0.02 * k, 0.05 - 0.01 * k, TT), M_PEWTER, steps=8)
for k in range(2):
    lathe(f"Cask{k}", [(0.0, 0.0), (0.025, 0.0), (0.032, 0.035), (0.025, 0.07), (0.0, 0.07)], TF.p(0.52, -0.1 + 0.08 * k, TT), M_TINYWOOD, steps=12)
# the cords they draw things up by: from a pulley block on the rim down to the floor, a cask on the floor tied ready
for k, (x, y) in enumerate(((0.62, -0.2), (0.62, 0.15))):
    p_top = Vector(TF.p(x + 0.05, y, TT + 0.05)); p_bot = Vector(TF.p(x + 0.3, y + 0.05 * k, 0.02))
    tube(f"Cord{k}", [p_top, p_top.lerp(p_bot, 0.5) + Vector((0, 0, -0.02)), p_bot], 0.003, M_CORD, sides=4)
    box(f"PulleyBlock{k}", (0.03, 0.02, 0.03), tuple(p_top), M_TINYWOOD)
    lathe(f"FloorCask{k}", [(0.0, 0.0), (0.03, 0.0), (0.038, 0.04), (0.03, 0.08), (0.0, 0.08)], tuple(p_bot + Vector((0.04, 0, -0.02))), M_TINYWOOD, steps=12)
anchor("room.table", tuple(TABLE))

# Gulliver's chair: a massive slab seat on log legs, a plank back; his coat with deep pockets over it
CHF = Frame((TABLE.x - 0.95, TABLE.y - 0.55), math.radians(-60))
CHF.box("ChairSeat", (0.55, 0.5, 0.07), (0, 0, 0.43 + (0.07) / 2), M_LOG, bevel=0.01)
for sx in (-1, 1):
    for sy in (-1, 1):
        tube(f"ChairLeg{sx}{sy}", [CHF.p(sx * 0.22, sy * 0.2, 0.0), CHF.p(sx * 0.21, sy * 0.19, 0.43)], [0.05, 0.045], M_BARK, sides=6)
CHF.box("ChairBack", (0.5, 0.06, 0.5), (0, -0.24, 0.5 + (0.5) / 2), M_LOGY, bevel=0.01, rx=-0.1)
# the coat: hung over the back, skirts down the back, one sleeve hanging, the deep pockets with their flaps
cv = []; cf = []
for j in range(8):
    for i in range(7):
        u = (i / 6 - 0.5) * 0.56; t = j / 7
        y = -0.26 - 0.08 * t - 0.02 * math.sin(i * 1.3); z = 1.02 - t * 0.95
        if t < 0.15: y = -0.24 + 0.1 * (0.15 - t) / 0.15; z = 1.02 + 0.03
        cv.append(CHF.p(u * (1 + 0.15 * t), y - 0.03 * noise.noise(Vector((u * 4, t * 4, 0))), z))
for j in range(7):
    for i in range(6): cf.append((j * 7 + i, (j + 1) * 7 + i, (j + 1) * 7 + i + 1, j * 7 + i + 1))
co_ = mesh_from("Coat", cv, cf, M_COAT, smooth=True); co_.modifiers.new("S", 'SOLIDIFY').thickness = 0.02
for sx in (-1, 1):
    CHF.box(f"PocketFlap{sx}", (0.16, 0.02, 0.07), (sx * 0.15, -0.36, 0.42), M_COAT, bevel=0.01)
    for k in range(3): sphere(f"PocketButton{sx}{k}", 0.008, CHF.p(sx * 0.15 - 0.05 + 0.05 * k, -0.375, 0.39), M_BRASSB, seg=6)
tube("CoatSleeve", [CHF.p(0.28, -0.22, 0.98), CHF.p(0.33, -0.15, 0.7), CHF.p(0.34, -0.1, 0.45)], [0.06, 0.055, 0.05], M_COAT, sides=8)
for k in range(5): sphere(f"CoatButton{k}", 0.009, CHF.p(-0.02, -0.33, 0.95 - 0.12 * k), M_BRASSB, seg=6)
anchor("room.chair", CHF.p(0, 0, 0))
# a log stool with his quilted shirts folded on it, by the bed
SH = Frame((X0 + 0.55, -1.75), 0.3)
cyl("LogStool", 0.22, 0.4, SH.p(0, 0, 0.2), M_BARK, verts=10)
cyl("LogStoolTop", 0.215, 0.01, SH.p(0, 0, 0.405), M_LOG, verts=16)
for k in range(3):
    SH.box(f"Shirt{k}", (0.3 - 0.02 * k, 0.24, 0.045), (0.0, 0.0, 0.41 + 0.045 * k + (0.045) / 2), M_SHEET, bevel=0.015)

# ----------------------------------------------------------------------------- tiny lanterns along the walls (Lilliputian lanterns, lit at dusk)
LANT = []
for k, (x, y, z) in enumerate(((X1 - 0.08, -0.9, 1.35), (X1 - 0.08, 1.6, 1.35), (X0 + 0.08, -1.05, 1.35), (X0 + 0.08, 1.95, 1.35), (TABLE.x + 0.55, TABLE.y + 0.3, TT))):
    lathe(f"Lantern{k}", [(0.0, 0.0), (0.02, 0.0), (0.02, 0.005), (0.016, 0.006), (0.016, 0.04), (0.02, 0.045), (0.006, 0.06), (0.0, 0.065)], (x, y, z), M_IRON, steps=8)
    cyl(f"LanternGlow{k}", 0.014, 0.03, (x, y, z + 0.022), M_GLOW, verts=8)
    if k < 4: box(f"LanternBracket{k}", (0.12 if abs(x) > 2 else 0.02, 0.01, 0.01), (x + (0.05 if x < 0 else -0.05), y, z + 0.065), M_IRON)
    LANT.append(Vector((x, y, z + 0.03)))

# ----------------------------------------------------------------------------- light: the last of the sun through the west window, sky through both, the lanterns
light_obj("Lamp.sun", 'SUN', 3.0, (1.0, 0.70, 0.45), (-10, 0, 3), direction=(1.0, 0.25, -0.16), angle=math.radians(1.5))
for wall, u, w, z0, z1 in WINS:
    sgn = 1 if wall == 'E' else -1; x = X1 if wall == 'E' else X0
    ld = bpy.data.lights.new(f"Lamp.windowSky{wall}", 'AREA'); ld.energy = 22.0; ld.color = (0.95, 0.75, 0.6); ld.size = 0.4; ld.shape = 'RECTANGLE'; ld.size_y = 0.5
    wl = bpy.data.objects.new(f"Lamp.windowSky{wall}", ld); wl.location = (x + sgn * 0.1, u, (z0 + z1) / 2); K.link(wl)
    wl.rotation_euler = Vector((-sgn, 0, -0.2)).to_track_quat('-Z', 'Y').to_euler()
for k, p in enumerate(LANT):
    light_obj(f"Lamp.lantern{k}", 'POINT', 3.0, (1.0, 0.66, 0.34), tuple(p), shadow_soft_size=0.02)
world = bpy.data.worlds.new("Dusk"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.42, 0.40, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

# ----------------------------------------------------------------------------- anchors, sources
S.reader(READER, (TABLE.x - READER.x, TABLE.y - READER.y))
anchor("scene.centre", (0, 0, 0))
for k, p in enumerate(LANT): S.fx(f"fx.lantern.{k}", tuple(p), 0.012)
sound("crowd", "outside", (GATE_X, Y1 + 3.0, 0.5))
sound("wind", "window", (X1 + 0.5, 0.5, 1.2))
page = S.page_preview()
K.apply_transforms()

E = READER + Vector((0, 0, S.EYE))
fwd = (TABLE - READER).normalized()
cams = S.eye_cams([("Reader", 0), ("Left", -75), ("Right", 75), ("Behind", 180)], dz=-0.8, dist=4.0, extra=[
    ("Page", E, E + fwd * 4 + Vector((0, 0, -0.8)), 17),
    ("Table", Vector((TABLE.x - 0.2, TABLE.y - 0.75, 1.25)), TABLE + Vector((0, 0.05, TT)), 30),
])
probs = S.check_reader(ignore=("PagePreview",))
K.print_budget(exclude=("PagePreview",))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.6, captures_dir=ARGS.captures)

if ARGS.export or ARGS.bake:
    S.export(SID, cams, page=page, unlit_emit=("M_LanternGlow", "M_DuskView"),
             keep_names={"M_LanternGlow": "MESH_LanternGlow", "M_DuskView": "far.duskView"},
             size_for={"M_Ashlar": (2048, 64, 1024), "M_FloorFlags": (1024, 64, 512), "M_RoughTimber": (1024, 64, 512), "M_RoughTimberY": (512, 64, 256),
                       "M_OakBark": (512, 64, 256), "M_BedTicking": (1024, 64, 512), "M_Coverlet": (1024, 64, 512), "M_QuiltedSheet": (512, 64, 256),
                       "M_CoatCloth": (512, 64, 256), "M_TinyFurniture": (512, 64, 128), "M_GateTimber": (256, 32, 128)},
             default_size=(256, 32, 128))
print("DONE")
