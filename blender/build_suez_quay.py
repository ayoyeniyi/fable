"""
Fable: the quay at Suez on the morning of 9 October 1872 (Around the World in Eighty Days, chapters 6 and 8).

"Among the crowd ... one moved backwards and forwards ... on the quay ... Fix ... was watching ... the steamer
Mongolia." "A jetty pier, some two thousand yards along, extended into the roadstead." "... numerous fishing-smacks
and coasting boats, some retaining the fantastic fashion of ancient galleys ..." "The minarets of the town ..."
"The weather was clear, and slightly chilly." "... the pale rays of the sun ..."

The reader stands on the stone quay near the landing steps where Fix waits, facing the water and the roadstead. On the
quay: bollards, bales in sacking and rope, crates, coal sacks, a hand-cart, a capstan. Below the steps, ship's boats
and a felucca lie moored; out in the roadstead, coasting dhows with their great lateen sails, fishing smacks, and
in the middle distance the P&O iron steamer Mongolia at anchor, smoke from her funnel; off to the right the long jetty
pier runs out into the roadstead, on and on. Behind, the town: flat-roofed whitewashed and mud-brick houses with
canvas awnings and shuttered windows, the British consulate on the corner of the square, a clock on the harbour
office, minarets over the roofs. Clear, slightly chilly morning; a low pale sun. No people (the quay crowd is a sound).

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py.

Node names the runtime relies on:
  anchor.reader.entrance (feet on the quay, facing +Y: the roadstead), anchor.reader.look, anchor.scene.centre (the
  landing steps), anchor.road.mongolia
  light.sun (SUN, low morning sun from the east), light.sky (SUN, clear-sky fill)
  water.ocean.roadstead (COLOR_0.G foam at the quay foot), cloth.sail.* (lateen sails), cloth.flag.* (ensigns, the
  P&O house flag), cloth.curtain.awnings
  sound.crowd.quay, sound.gulls.0, sound.wind.0, sound.clock.office, sound.surf.steps
  SkyDome, far.Shore (the Sinai shore across the gulf)

Run headless:
  blender -b -P blender/build_suez_quay.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_suez_quay.py -- --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b1 as S
from scene_kit_b1 import (K, E8, new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound, light_obj, camera,
                          link, smoothstep, lerp, n2, fbm2, orient, card, plant, set_card_normals, az_dir, TWO_PI)

ARGS = S.setup("suez-quay", 1872, "SuezQuay", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
SUN_AZ, SUN_EL = 72.0, 16.0
SUN_DIR = (az_dir(SUN_AZ) * math.cos(math.radians(SUN_EL)) + Vector((0, 0, math.sin(math.radians(SUN_EL))))).normalized()
QUAY_Y = 4.2                 # the quay's edge
SEA = -1.9                   # the water below the quay's top
STEPS_X = (1.4, 3.4)         # the landing steps cut into the quay face

def H(x, y):
    if y < QUAY_Y: return 0.01 * n2(x, y, 4.0, 2.0) - 0.004 * max(0.0, -y - 10)
    return SEA - 3.0
Z0 = 0.0
def gz(x, y): return H(x, y)
S.set_ground(gz)

def quay_mat(name="M_QuayStone"):
    """the quay's paving: big sun-bleached limestone slabs in courses (brick texture at slab scale), worn smooth,
    sand and coal dust in the joints, oil and water stains, a darker band of damp toward the edge."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    br = node(nt, "ShaderNodeTexBrick", (-1400, 0)); br.offset = 0.5
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 1.1; br.inputs["Row Height"].default_value = 0.65
    br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Color1"].default_value = (1, 1, 1, 1); br.inputs["Color2"].default_value = (0, 0, 0, 1)
    sx = sep_xyz(nt, co, (-1800, 0))
    hv = node(nt, "ShaderNodeCombineXYZ", (-1600, 0)); nt.links.new(math_(nt, 'ADD', sx.outputs["X"], sx.outputs["Z"], (-1700, 100)), hv.inputs["X"]); nt.links.new(sx.outputs["Y"], hv.inputs["Y"])
    nt.links.new(hv.outputs[0], br.inputs["Vector"])
    bs = node(nt, "ShaderNodeSeparateColor", (-1200, 0)); nt.links.new(br.outputs["Color"], bs.inputs["Color"])
    slab = ramp(nt, [(0.0, c4(K.srgb((0.66, 0.60, 0.50)))), (0.5, c4(K.srgb((0.74, 0.68, 0.57)))), (1.0, c4(K.srgb((0.62, 0.57, 0.48))))], (-1000, 0))
    nt.links.new(bs.outputs[0], slab.inputs["Fac"])
    n = noise_(nt, co, 1.2, 5, 0.6, loc=(-1400, -300)); fine = noise_(nt, co, 25.0, 3, 0.6, loc=(-1400, -500))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, slab.outputs["Color"], maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.78, 1.06, (-1200, -300)), (-800, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0.9, 1.05, (-1200, -500)), (-650, 0))
    stain = maprange(nt, noise_(nt, co, 0.6, 4, 0.6, loc=(-1400, -700)).outputs["Fac"], 0.6, 0.7, 0, 0.5, (-1200, -700))
    col = mix_rgb(nt, 'MIX', stain, col, c4(K.srgb((0.30, 0.27, 0.22))), (-500, 0))
    col = mix_rgb(nt, 'MIX', br.outputs["Fac"], col, c4(K.srgb((0.28, 0.25, 0.20))), (-400, 0))
    col = K.ao_mul(nt, col, 0.3, 0.4, (-300, -900))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    b.inputs["Specular IOR Level"].default_value = 0.25
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', br.outputs["Fac"], -1.0, (-600, -1100)), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.3, (-600, -1200)), (-450, -1150)), 0.4, 0.01)
    return m

def plaster_mat(name, base, dirt=(0.45, 0.40, 0.32), scale=1.0):
    """whitewash over mud-brick: patchy, flaking to the brown brick at the foot and the corners, streaked."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1600, -400))
    n = noise_(nt, co, 1.5 * scale, 6, 0.65, loc=(-1400, 200))
    fine = noise_(nt, co, 14.0, 4, 0.6, loc=(-1400, 0))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1200, 200)), c4(K.srgb(base)), c4(K.srgb(tuple(min(1, c * 1.08) for c in base))), (-1000, 200))
    flake = math_(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.62, 0.66, 0, 1, (-1200, -100)), maprange(nt, s.outputs["Z"], 2.5, 0.3, 0.3, 1.0, (-1200, -250)), (-1000, -150))
    col = mix_rgb(nt, 'MIX', flake, col, c4(K.srgb((0.52, 0.40, 0.28))), (-800, 200))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, s.outputs["Z"], 1.2, 0.0, 0, 0.6, (-1000, -400)), col, c4(K.srgb(dirt)), (-600, 200))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0.9, 1.05, (-1000, -550)), (-450, 200))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
    bump_from(nt, b, math_(nt, 'ADD', flake, math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.3, (-600, -900)), (-450, -900)), 0.3, 0.01)
    return m

print("materials ...", flush=True)
M_QUAY = quay_mat()
M_QUAYFACE = S.stone_mat("M_QuayFace", (0.60, 0.55, 0.46), (0.30, 0.28, 0.24), (0.70, 0.64, 0.54), scale=1.5, wet_z=SEA + 0.6, wet_k=0.7, moss=0.0, lichen=0.0, rough=0.8, bump=0.3, strata=0.6)
M_WALLW = plaster_mat("M_Whitewash", (0.84, 0.80, 0.70))
M_WALLO = plaster_mat("M_Ochre", (0.72, 0.58, 0.40))
M_ROOFS = K.noisy("M_RoofEdge", [K.srgb((0.60, 0.54, 0.44)), K.srgb((0.50, 0.44, 0.36))], scale=2, rough=0.9, bump=0.1)
M_SHUTTER = K.noisy("M_Shutters", [K.srgb((0.20, 0.32, 0.30)), K.srgb((0.30, 0.40, 0.36)), K.srgb((0.40, 0.36, 0.28))], scale=6, rough=0.75, bump=0.1, stretch=(1, 1, 6))
M_DARKWIN = plain("M_DarkOpening", (0.02, 0.018, 0.015), rough=1.0)
M_AWNING = K.noisy("M_Awning", [K.srgb((0.82, 0.76, 0.62)), K.srgb((0.70, 0.52, 0.40)), K.srgb((0.78, 0.72, 0.58))], scale=4, rough=0.9, bump=0.1, stretch=(8, 1, 1))
M_TIMBER = S.bark_mat("M_Timber", (0.40, 0.34, 0.26), (0.20, 0.17, 0.13), (0.50, 0.44, 0.34), scale=3.0, fissure=0.3, moss=0.0)
M_IRON = plain("M_Iron", (0.04, 0.04, 0.04), rough=0.5, metallic=0.7)
M_SACK = K.noisy("M_Sacking", [K.srgb((0.62, 0.52, 0.36)), K.srgb((0.52, 0.42, 0.28)), K.srgb((0.70, 0.60, 0.42))], scale=60, rough=0.95, bump=0.4)
M_COALSACK = K.noisy("M_CoalSack", [K.srgb((0.16, 0.14, 0.12)), K.srgb((0.24, 0.21, 0.17))], scale=50, rough=0.95, bump=0.4)
M_ROPE = K.noisy("M_Rope", [K.srgb((0.55, 0.46, 0.32)), K.srgb((0.45, 0.37, 0.25))], scale=80, rough=0.9, bump=0.5, stretch=(1, 1, 10))
M_HULLW = K.noisy("M_BoatHull", [K.srgb((0.70, 0.66, 0.58)), K.srgb((0.36, 0.42, 0.44)), K.srgb((0.55, 0.50, 0.42))], scale=2, rough=0.7, bump=0.1)
M_STEAMER = K.noisy("M_SteamerHull", [K.srgb((0.05, 0.05, 0.05)), K.srgb((0.09, 0.09, 0.09))], scale=1, rough=0.5, bump=0.05)
M_FUNNEL = plain("M_Funnel", K.srgb((0.06, 0.05, 0.04)), rough=0.5)
M_SAIL = K.noisy("M_Sails", [K.srgb((0.86, 0.80, 0.68)), K.srgb((0.78, 0.72, 0.60))], scale=5, rough=0.9, bump=0.1)
M_FLAG = plain("M_Flags", K.srgb((0.70, 0.10, 0.10)), rough=0.8)
M_SEA = S.water_mat("M_Sea", deep=(0.03, 0.10, 0.12), rough=0.06, ripple=0.4)
M_FAR = K.noisy("M_FarShore", [K.srgb((0.72, 0.58, 0.46)), K.srgb((0.64, 0.50, 0.40))], scale=0.02, rough=1.0, bump=0.0)
M_CLOCK = plain("M_ClockFace", K.srgb((0.88, 0.86, 0.80)), rough=0.5)
M_SMOKE = K.noisy("M_Smoke", [K.srgb((0.30, 0.29, 0.28)), K.srgb((0.40, 0.39, 0.38))], scale=1, rough=1.0, bump=0.0)
M_SKY = S.gradient_sky_mat("M_SkyDome", [(0.0, (0.82, 0.78, 0.70)), (0.08, (0.74, 0.78, 0.84)), (0.3, (0.48, 0.62, 0.84)), (1.0, (0.24, 0.42, 0.75))],
                           sun_dir=SUN_DIR, glow=((1.0, 0.85, 0.6), 14.0), clouds=0.15, cloud_col=(0.9, 0.88, 0.85))

# ----------------------------------------------------------------------------- the quay and the water
print("quay ...", flush=True)
S.ground("Quay", M_QUAY, 60.0, r0=2.0, NA=96, NR=26, skip=lambda x, y: y > QUAY_Y)
# the quay's face: a stone wall from the paving down into the water, the landing steps cut into it
FACE = []
for k in range(40):
    x0 = -60 + k * 3.0; x1 = x0 + 3.0
    if x1 <= STEPS_X[0] or x0 >= STEPS_X[1]:
        FACE.append(box(f"QuayFace{k}", (3.0, 1.0, 4.5), ((x0 + x1) / 2, QUAY_Y + 0.5, -2.25), M_QUAYFACE))
    else:
        for (a, b_) in ((x0, STEPS_X[0]), (STEPS_X[1], x1)):
            if b_ - a > 0.05: box(f"QuayFaceP{k}{a}", (b_ - a, 1.0, 4.5), ((a + b_) / 2, QUAY_Y + 0.5, -2.25), M_QUAYFACE)
for (a, b_) in ((-60.0, STEPS_X[0]), (STEPS_X[1], 60.0)):
    box("Coping", (b_ - a, 0.9, 0.3), ((a + b_) / 2, QUAY_Y + 0.35, -0.05), M_QUAYFACE)
for k in range(9):    # the steps going down to the water along the face
    z = -0.22 * (k + 1); y = QUAY_Y + 0.05 + k * 0.3
    box(f"Step{k}", (STEPS_X[1] - STEPS_X[0], 0.32, 0.22 * (k + 1) + 2.5), ((STEPS_X[0] + STEPS_X[1]) / 2, y + 0.15, z - (0.22 * (k + 1) + 2.5) / 2 + 0.22 * (k + 1) - 0.22 * (k + 1)), M_QUAYFACE)
SEA_N = S.water_surface("SeaNear", M_SEA, SEA, lambda x, y: y > QUAY_Y + 0.3 and y < 120, extent=240.0, step=4.0, centre=(0.0, 60.0))
SEA_F = S.water_surface("SeaFar", M_SEA, SEA - 0.05, lambda x, y: y > 100, extent=2400.0, step=80.0, centre=(0.0, 1150.0))
for o in (SEA_N, SEA_F): E8.water_attrs(o, lambda p: max(0.0, 1.0 - (p.y - QUAY_Y - 0.9) / 1.2) * 0.7)
# the far shore of the gulf (the Sinai hills, low and tawny), as a band at the horizon
def far_shore():
    verts = []; faces = []; N = 64; Rr = 1150.0
    for i in range(N + 1):
        a = math.radians(-70 + 140 * i / N)
        x, y = Rr * math.sin(a) + 0.0, Rr * math.cos(a)
        h = 12 + 30 * (0.5 + 0.5 * n2(i, 0, 6.0, 1.0)) + 25 * smoothstep(20, 70, abs(math.degrees(a)))
        verts += [(x, y, SEA + h), (x, y, SEA - 1)]
    for i in range(N):
        q = 2 * i; faces.append((q, q + 2, q + 3, q + 1))
    o = mesh_from("FarShore", verts, faces, M_FAR); orient(o, lambda c: (-c.x, -c.y, 0)); return o
far_shore()

# ----------------------------------------------------------------------------- quay furniture
print("quay goods ...", flush=True)
R = random.Random(9)
for k, x in enumerate((-14.0, -7.5, -2.2, 5.6, 12.5, 19.0)):
    lathe(f"Bollard{k}", [(0.0, 0.0), (0.17, 0.0), (0.15, 0.35), (0.12, 0.55), (0.18, 0.62), (0.17, 0.68), (0.0, 0.7)], (x, QUAY_Y - 0.45, 0.0), M_IRON, steps=14)
# bales of cotton/goods in sacking, roped, stacked; crates; coal sacks; a hand cart; coils of rope
def bale(x, y, z, yaw, s=(0.9, 0.6, 0.55)):
    o = box("Bale", s, (x, y, z + s[2] / 2), M_SACK, bevel=0.08); o.rotation_euler = (0, 0, yaw)
    for t in (-0.25, 0.25):
        r_ = box("BaleRope", (0.03, s[1] + 0.02, s[2] + 0.02), (x + math.cos(yaw) * t * s[0], y + math.sin(yaw) * t * s[0], z + s[2] / 2), M_ROPE)
        r_.rotation_euler = (0, 0, yaw)
for (x, y) in ((-5.5, -1.0), (-5.5, -1.7), (-4.6, -1.3)):
    for lvl in range(2 if x < -5 else 1):
        bale(x, y, lvl * 0.56, R.uniform(-0.1, 0.1))
bale(-5.2, -1.3, 1.12, 0.3)
for (x, y, s) in ((4.8, -0.8, 0.6), (5.5, -0.6, 0.5), (5.1, -0.4, 0.45), (5.0, -0.6, 0.6)):
    z = 0.0 if s != 0.45 else 0.6
    o = box("Crate", (s, s * 0.8, s * 0.7), (x, y, z + s * 0.35), M_TIMBER, bevel=0.01); o.rotation_euler = (0, 0, R.uniform(-0.2, 0.2))
for k in range(7):
    x, y = -10.0 + R.uniform(-0.8, 0.8), -0.5 + R.uniform(-0.6, 0.6)
    sphere(f"CoalSack{k}", 1.0, (x, y, 0.22 + (0.3 if k > 4 else 0.0)), M_COALSACK, seg=10, scale=(0.42, 0.3, 0.24))
for k, (x, y) in enumerate(((-2.2, 3.4), (7.0, 3.5))):
    for t in range(5):
        lathe(f"RopeCoil{k}{t}", [(0.12 + t * 0.03, 0.0), (0.14 + t * 0.03, 0.02), (0.12 + t * 0.03, 0.05)], (x, y, t * 0.0), M_ROPE, steps=16)
# hand cart
cx_, cy_ = 9.0, 0.5
box("CartBed", (1.6, 0.9, 0.08), (cx_, cy_, 0.55), M_TIMBER)
for sd in (-1, 1):
    o = cyl(f"CartWheel{sd}", 0.42, 0.06, (cx_, cy_ + sd * 0.5, 0.42), M_TIMBER, verts=16); o.rotation_euler = (math.pi / 2, 0, 0)
    tube(f"CartShaft{sd}", [Vector((cx_ + 0.8, cy_ + sd * 0.35, 0.55)), Vector((cx_ + 1.9, cy_ + sd * 0.35, 0.05))], [0.03, 0.03], M_TIMBER, sides=5)
bale(cx_ - 0.2, cy_, 0.6, 0.0, (0.8, 0.55, 0.45))
# a capstan by the steps
lathe("Capstan", [(0.0, 0.0), (0.3, 0.0), (0.22, 0.15), (0.2, 0.6), (0.28, 0.72), (0.28, 0.85), (0.0, 0.88)], (-3.4, QUAY_Y - 1.0, 0.0), M_IRON, steps=16)

# ----------------------------------------------------------------------------- boats
print("boats ...", flush=True)
def hull(name, c, yaw, L, B, D, mat, rise=0.3, stern_flat=False, steps=(16, 10)):
    M = Matrix.Translation(c) @ Matrix.Rotation(yaw, 4, 'Z')
    NS, NU = steps
    verts = []; faces = []
    def sheer(t): return D * 0.55 + rise * (abs(t) ** 2.2)
    def keel(t): return -D * 0.45 + 0.2 * D * abs(t) ** 3
    def hb(t):
        if stern_flat and t < 0: return B / 2 * (1 - abs(t) ** 4) ** 0.5 * 0.85 + B * 0.08
        return B / 2 * (1 - abs(t) ** 2.2) ** 0.7 + 0.01
    for i in range(NS + 1):
        t = -1 + 2 * i / NS
        for j in range(NU + 1):
            s = -1 + 2 * j / NU; ph = s * math.pi / 2
            y = hb(t) * math.sin(ph); z = sheer(t) - (sheer(t) - keel(t)) * math.cos(ph) ** 1.3
            verts.append(tuple(M @ Vector((t * L / 2, y, z))))
    for i in range(NS):
        for j in range(NU):
            a = i * (NU + 1) + j; faces.append((a, a + 1, a + NU + 2, a + NU + 1))
    o = mesh_from(name, verts, faces, mat, smooth=True)
    orient(o, lambda p: (p - Vector(c)) * Vector((1, 1, 0.2)) + Vector((0, 0, 0.01)))
    o.modifiers.new("Solid", 'SOLIDIFY').thickness = 0.04 * max(1.0, L / 10)
    return M, sheer, hb
def lateen(name, M, mast_at, mast_h, yard_len, sail=True):
    """a dhow's rig: a raked mast, the long yard slung slanting, the triangular lateen sail (cloth.sail)."""
    base = M @ Vector((mast_at, 0, 0.3)); top = M @ Vector((mast_at + mast_h * 0.12, 0, mast_h))
    tube(f"{name}Mast", [base, top], [0.09, 0.05], M_TIMBER, sides=6)
    fwd = (M.to_3x3() @ Vector((1, 0, 0))).normalized()
    y0 = top + fwd * yard_len * 0.55 - Vector((0, 0, yard_len * 0.38)); y1 = top - fwd * yard_len * 0.45 + Vector((0, 0, yard_len * 0.22))
    tube(f"{name}Yard", [y0, top - Vector((0, 0, 0.3)), y1], [0.05, 0.06, 0.03], M_TIMBER, sides=5)
    if sail:
        side = fwd.cross(Vector((0, 0, 1))).normalized()
        clew = M @ Vector((mast_at - yard_len * 0.35, 0, 0.9)) + side * 0.6
        mb = MB()
        N = 6
        for i in range(N):
            for j in range(N - i):
                pass
        # a gently bellied triangle as a small grid
        pts = {}
        for i in range(N + 1):
            for j in range(N + 1 - i):
                u, v = i / N, j / N
                p = y0 * (1 - u - v) + y1 * u + clew * v
                p += side * 0.35 * math.sin(math.pi * u) * math.sin(math.pi * min(1, v + 0.0001)) * (1 - u - v + 0.3)
                w = min(1.0, v * 1.5 + 0.1 * u)
                pts[(i, j)] = mb.vert(p, (u, v), w)
        for i in range(N):
            for j in range(N - i):
                mb.face(pts[(i, j)], pts[(i + 1, j)], pts[(i, j + 1)])
                if j + 1 <= N - i - 1: mb.face(pts[(i + 1, j)], pts[(i + 1, j + 1)], pts[(i, j + 1)])
        o = mb.build(f"{name}Sail", M_SAIL)
        o.modifiers.new("Solid", 'SOLIDIFY').thickness = 0.01
# ship's boats and a felucca at the foot of the steps
for k, (x, y, yaw, L) in enumerate(((0.2, 6.2, 0.15, 5.0), (5.6, 6.4, -0.1, 5.5), (-3.6, 6.5, 0.05, 4.5))):
    M, sh, hb_ = hull(f"Boat{k}", Vector((x, y, SEA + 0.15)), yaw, L, 1.6, 0.8, M_HULLW, rise=0.25, stern_flat=True)
    for t in (-0.4, 0.0, 0.35):
        box(f"BoatThwart{k}", (0.2, hb_(t) * 2 - 0.1, 0.04), tuple(M @ Vector((t * L / 2, 0, sh(t) - 0.2))), M_TIMBER, rot=(0, 0, yaw))
    for sd in (-1, 1):
        tube(f"BoatOar{k}{sd}", [M @ Vector((-L * 0.35, sd * 0.25, sh(0) - 0.15)), M @ Vector((L * 0.4, sd * 0.2, sh(0) - 0.12))], [0.03, 0.025], M_TIMBER, sides=5)
    a = M @ Vector((-L / 2, 0, sh(-1))); b_ = Vector((x + R.uniform(-0.5, 0.5), QUAY_Y - 0.2, 0.3))
    tube(f"Painter{k}", [a, (a + b_) / 2 - Vector((0, 0, 0.4)), b_], [0.015] * 3, M_ROPE, sides=4, caps=False)
M, sh, hb_ = hull("Felucca", Vector((-15.0, 17.0, SEA + 0.2)), 0.3, 9.0, 2.6, 1.2, M_HULLW, rise=0.6)
lateen("Felucca", M, 1.0, 8.0, 10.0, sail=False)
# coasting boats and dhows out in the roadstead
for k, (x, y, yaw, L, sail) in enumerate(((-45.0, 70.0, 0.6, 16.0, True), (30.0, 95.0, -0.4, 14.0, True), (-20.0, 140.0, 1.2, 18.0, True),
                                          (60.0, 160.0, 0.2, 12.0, False), (-80.0, 120.0, -0.8, 13.0, True), (15.0, 55.0, 1.4, 10.0, False))):
    M, sh, hb_ = hull(f"Dhow{k}", Vector((x, y, SEA + 0.25)), yaw, L, L * 0.28, L * 0.13, M_HULLW, rise=L * 0.06, steps=(12, 8))
    lateen(f"Dhow{k}", M, L * 0.12, L * 0.9, L * 1.1, sail=sail)
# the P&O steamer Mongolia at anchor in the roadstead: an iron screw steamer, black hull, a funnel, two masts
MONG = Vector((-45.0, 230.0, SEA)); MY = math.radians(12)
M, sh, hb_ = hull("Mongolia", MONG + Vector((0, 0, 1.0)), MY, 100.0, 12.0, 8.0, M_STEAMER, rise=1.0, steps=(24, 10))
box("MongoliaHouse", (30.0, 7.0, 3.0), tuple(M @ Vector((0, 0, 6.6))), M_WALLW, rot=(0, 0, MY))
fz = M @ Vector((-2.0, 0, 6.0))
cyl("MongoliaFunnel", 2.0, 12.0, tuple(fz + Vector((0, 0, 6.0))), M_FUNNEL, verts=14)
for k, at in enumerate((28.0, -28.0)):
    p = M @ Vector((at, 0, 5.0))
    tube(f"MongoliaMast{k}", [p, p + Vector((0, 0, 30.0))], [0.45, 0.2], M_TIMBER, sides=6)
    for f, wdt in ((0.55, 16.0), (0.78, 11.0)):
        c = p + Vector((0, 0, 30 * f)); side = Matrix.Rotation(MY, 3, 'Z') @ Vector((0, 1, 0))
        tube(f"MongoliaYard{k}", [c - side * wdt / 2, c + side * wdt / 2], [0.18, 0.18], M_TIMBER, sides=4)
# the jetty pier: piles and a plank deck running out along the roadstead to the right, on and on
PIER_X = 26.0
for k in range(110):
    y = QUAY_Y + 1.0 + k * 10.0
    for sd in (-1, 1):
        tube(f"PierPile{k}{sd}", [Vector((PIER_X + sd * 2.2, y, SEA - 3.0)), Vector((PIER_X + sd * 2.2, y, 0.0))], [0.18, 0.16], M_TIMBER, sides=5 if k < 20 else 3)
box("PierDeck", (5.0, 1100.0, 0.25), (PIER_X, QUAY_Y + 550.0, 0.0), M_TIMBER)
for sd in (-1, 1):
    box(f"PierRail{sd}", (0.08, 1100.0, 0.08), (PIER_X + sd * 2.4, QUAY_Y + 550.0, 1.0), M_TIMBER)
    for k in range(0, 60):
        box(f"PierPost{sd}{k}", (0.1, 0.1, 1.0), (PIER_X + sd * 2.4, QUAY_Y + 1.0 + k * 5.0, 0.55), M_TIMBER)

# ----------------------------------------------------------------------------- the town behind: flat-roofed houses, awnings, the consulate, the clock, minarets
print("town ...", flush=True)
TOWN = []
def house(x, y, w, d, h, mat, yaw=0.0, awning=False, shutters=2, parapet=True):
    box("House", (w, d, h), (x, y, h / 2 - 0.1), mat, rot=(0, 0, yaw))
    if parapet: box("Parapet", (w + 0.1, d + 0.1, 0.35), (x, y, h + 0.07), M_ROOFS, rot=(0, 0, yaw))
    fy = y + d / 2 + 0.02   # the front faces +Y (the quay)
    for i in range(shutters):
        u = x - w / 2 + w * (i + 0.5) / shutters
        for fl in range(int(h // 3.2)):
            z = 1.3 + fl * 3.2 if fl else 1.4
            box("Window", (0.9, 0.04, 1.4), (u, fy, z + 0.6), M_DARKWIN)
            for sd in (-1, 1):
                o = box("Shutter", (0.45, 0.05, 1.4), (u + sd * 0.45 * 1.05, fy + 0.04 + 0.12, z + 0.6), M_SHUTTER); o.rotation_euler = (0, 0, sd * 0.5)
    box("Door", (1.1, 0.05, 2.2), (x + w * 0.2, fy, 1.1), M_DARKWIN)
    if awning:
        mb = MB(); a0 = Vector((x - w / 2 + 0.3, fy, 3.0)); a1 = Vector((x + w / 2 - 0.3, fy, 3.0))
        card(mb, (a0 + a1) / 2, a1 - a0, Vector((0, 1.6, -0.45)), (0, 0, 1, 1), 0.0, 1.0, segs=3, bend=Vector((0, 0, -0.08)))
        ob = mb.build("Awning", M_AWNING)
        ob.modifiers.new("Solid", 'SOLIDIFY').thickness = 0.01
        for sd in (-1, 1): tube("AwningPole", [Vector((x + sd * (w / 2 - 0.4), fy + 1.6, 0.0)), Vector((x + sd * (w / 2 - 0.4), fy + 1.6, 2.6))], [0.035, 0.03], M_TIMBER, sides=5)
# the frontage behind the quay road (y ~ -9), and roofs climbing behind
FRONT_Y = -10.0
x = -40.0; k = 0
while x < 40:
    w = R.uniform(6, 10); d = R.uniform(7, 10); h = R.choice((5.5, 6.5, 8.5, 9.5))
    mat = M_WALLW if R.random() < 0.6 else M_WALLO
    house(x + w / 2, FRONT_Y - d / 2, w, d, h, mat, awning=(R.random() < 0.5 and abs(x) < 25), shutters=2 if w < 8 else 3)
    x += w + R.uniform(0.0, 0.4); k += 1
for k in range(40):
    x = R.uniform(-90, 90); y = R.uniform(-60, -22)
    w, d, h = R.uniform(6, 12), R.uniform(6, 12), R.uniform(5, 10)
    box("BackHouse", (w, d, h), (x, y, h / 2 + 0.004 * y), M_WALLW if R.random() < 0.6 else M_WALLO, rot=(0, 0, R.uniform(-0.1, 0.1)))
# the British consulate on the corner of the square (left, where the frontage turns): two storeys, a flagstaff
box("Consulate", (12.0, 12.0, 9.0), (-38.0, -4.0, 4.4), M_WALLW)
box("ConsulateCornice", (12.4, 12.4, 0.4), (-38.0, -4.0, 9.0), M_ROOFS)
CSTAFF = Vector((-38.0, -4.0, 9.2))
tube("Flagstaff", [CSTAFF, CSTAFF + Vector((0, 0, 7.0))], [0.06, 0.04], M_TIMBER, sides=6)
fmb = MB(); card(fmb, CSTAFF + Vector((0.9, 0, 6.0)), Vector((1.8, 0, 0)), Vector((0, 0, 0.95)), (0, 0, 1, 1), 0.0, 0.0)
fo = fmb.build("ConsulFlag", M_FLAG); K.add_sway(fo, lambda p: min(1.0, (p.x - CSTAFF.x) / 1.8))
# the harbour office with the port clock (it struck the half-hour), right behind the quay
box("HarbourOffice", (10.0, 8.0, 8.0), (14.0, -14.0, 3.9), M_WALLO)
box("ClockTower", (3.2, 3.2, 6.0), (14.0, -10.6, 10.8), M_WALLW)
box("ClockTowerCap", (3.8, 3.8, 0.4), (14.0, -10.6, 14.0), M_ROOFS)
CLOCK = Vector((14.0, -8.98, 11.5))
o = cyl("ClockFace", 0.9, 0.06, tuple(CLOCK), M_CLOCK, verts=24); o.rotation_euler = (math.pi / 2, 0, 0)
for (ang, L) in ((math.radians(0), 0.6), (math.radians(180 + 15), 0.75)):
    tube("ClockHand", [CLOCK + Vector((0, 0.05, 0)), CLOCK + Vector((math.sin(ang) * L, 0.05, math.cos(ang) * L))], [0.03, 0.015], M_IRON, sides=4)
# minarets over the roofs
for k, (x, y, h) in enumerate(((-22.0, -48.0, 30.0), (35.0, -70.0, 26.0), (-60.0, -85.0, 24.0))):
    lathe(f"Minaret{k}", [(0.0, 0.0), (2.2, 0.0), (2.0, h * 0.55), (2.6, h * 0.58), (2.6, h * 0.62), (1.6, h * 0.64), (1.4, h * 0.88), (1.9, h * 0.9), (1.9, h * 0.92),
                          (1.2, h * 0.94), (0.9, h * 0.98), (0.0, h * 1.08)], (x, y, 0.0), M_WALLW, steps=10)
    box(f"Mosque{k}", (14.0, 14.0, 8.0), (x + 9.0, y, 4.0), M_WALLW)
    sphere(f"Dome{k}", 5.0, (x + 9.0, y, 8.0), M_WALLW, seg=16, scale=(1, 1, 0.8))

# ----------------------------------------------------------------------------- sky, light
SKY = E8.sky_dome("SkyDome", M_SKY, 1180.0, seg=48, rings=14, el_min=-4.0); SKY.visible_shadow = False
K.apply_transforms()
light_obj("light.sun", 'SUN', 4.2, (1.0, 0.90, 0.76), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(1.0))
skl = light_obj("light.sky", 'SUN', 0.7, (0.62, 0.72, 0.95), (0, 0, 30), direction=(-0.1, 0.2, -1.0), angle=math.radians(85))
skl.data.use_shadow = False
world = bpy.data.worlds.new("Morning"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.55, 0.62, 0.78, 1); bg.inputs["Strength"].default_value = 0.6

sound("crowd", "quay", (-6.0, -4.0, 1.6)); sound("gulls", "0", (5.0, 30.0, 12.0)); sound("wind", "0", (0.0, 8.0, 3.0))
sound("clock", "office", tuple(CLOCK)); sound("surf", "steps", ((STEPS_X[0] + STEPS_X[1]) / 2, QUAY_Y + 2.5, SEA + 0.2))
S.reader_anchors(0.0)
anchor("scene.centre", ((STEPS_X[0] + STEPS_X[1]) / 2, QUAY_Y, 0.0))
anchor("road.mongolia", tuple(MONG + Vector((0, 0, 8.0))))
S.check_clear(look_yaw=0.0)
EZ = EYE
E = Vector((0, 0, EZ))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EZ - 0.6), 17),
    ("Cam_Mongolia", tuple(E), tuple(MONG + Vector((0, 0, 8.0))), 45),
    ("Cam_Steps", (0.5, 2.5, 2.0), (2.4, 6.0, SEA), 20),
], pitch=-4.0)
S.finish("suez-quay", "suez_quay", cams,
         keep_names={"M_Sea": "water.ocean.roadstead", "M_Sails": "cloth.sail.lateen", "M_Flags": "cloth.flag.consul", "M_Awning": "cloth.curtain.awnings",
                     "M_QuayStone": "GroundNear", "M_SkyDome": "SkyDome", "M_FarShore": "far.Shore"},
         keep_uv={"M_QuayStone"},
         size_for={"M_QuayStone": (2048, 256, 1024), "M_QuayFace": (1024, 64, 512), "M_Whitewash": (2048, 64, 512), "M_Ochre": (1024, 64, 512),
                   "M_RoofEdge": (256, 32), "M_Shutters": (256, 32, 128), "M_DarkOpening": (32,), "M_Awning": (256, 32, 128), "M_Timber": (1024, 64, 512),
                   "M_Iron": (64, 32), "M_Sacking": (512, 64, 256), "M_CoalSack": (256, 32, 128), "M_Rope": (256, 32, 128), "M_BoatHull": (1024, 64, 256),
                   "M_SteamerHull": (512, 32), "M_Funnel": (32,), "M_Sails": (512, 32, 128), "M_Flags": (32,), "M_FarShore": (512, 32), "M_ClockFace": (64,),
                   "M_Smoke": (64,), "M_SkyDome": (1024,)},
         page=page, default_exposure=0.0, water_colour={"M_Sea": (0.03, 0.10, 0.12)})
