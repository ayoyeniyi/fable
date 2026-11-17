"""
Fable scene room: Fitting out the boat at Blefuscu (Gulliver's Travels, Part I, Chapter VIII) - blefuscu-shore-boat.

"I observed, about half a league off in the sea, somewhat that looked like a boat overturned ... I found it to be a
real boat, which I supposed might by some tempest have been driven from a ship ... I had the good fortune ... to turn
it on its bottom, and found it was but little damaged." "I had fifty workmen ... five hundred workmen were employed to
make two sails to my boat, according to my directions, by quilting thirteen folds of their strongest linen together.
I was at the pains of making ropes and cables, by twisting ten, twenty, or thirty of the thickest and strongest of
theirs. A great stone that I happened to find, after a long search, by the sea-shore, served me for an anchor. I had
the tallow of three hundred cows, for greasing my boat, and other uses. I was at incredible pains in cutting down
some of the largest timber-trees, for oars and masts"

The reader is Gulliver-size on the royal port's beach, where everything of Blefuscu is built at one twelfth. Beside
the reader lies the full-size ship's boat, right way up on the sand on rollers and blocks, half fitted: a rough new
mast of a Blefuscudian "timber-tree" stepped and stayed with Gulliver's twisted ropes, the first quilted sail bent to
its yard and brailed up, the second laid out on the sand with the thirteen-fold quilting stitched in rows, oars and
paddles shaped from the largest trees, the great anchor stone in a sling of cable with the cable coiled beside it,
the three hundred cows' tallow in a stack of little barrels, the boat's seams half paid with it, and the tiny
scaffolds, ladders and trestles of the ship-carpenters against the hull. Out on the water lie a few of the tallest
Blefuscudian ships (nine feet long) at anchor; on the right, the harbour mole and the walled port town. No people.

Light: a clear early morning (as on the day of sailing), the sun low in the east over the sea, a light breeze.

Axes: metres, +Z up, +Y out to sea (east). The reader by the boat's bow facing the sea; the town on the right (south).

Run headless:
  blender -b -P blender/build_blefuscu_shore_boat.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_blefuscu_shore_boat.py -- --cpu --render --samples 32 --res 1024 --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b4 as S
from scene_kit_b4 import (K, new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, lathe, tube, MB, anchor, sound, smoothstep, n2, srgb,
                          mb_box, mb_quad, card, set_card_normals)

ARGS = S.setup("blefuscu-shore-boat", 1701, "BlefuscuShoreBoat", default_samples=48)
rng = random.Random(1701)
EYE = S.EYE
SUN_DIR = Vector((-0.40, 0.88, 0.36)).normalized()    # toward the sun: east-north-east over the sea, ~20 degrees up
SEA = -0.55
SHORE_Y = 9.0         # the waterline
YAW = -8.0
BOAT = Vector((-1.6, 2.4, 0.0)); BOAT_YAW = math.radians(-12)    # boat's bow toward the sea (+Y)
TOWN = Vector((42.0, 30.0, 0.0))

def shore(x): return SHORE_Y + 2.5 * math.sin(x / 23.0) + 1.2 * math.sin(x / 9.0) + (0.0 if x < 24 else (x - 24) * 0.35)
def gz(x, y):
    d = shore(x) - y        # distance inland from the waterline
    if d > 0: z = SEA + 0.07 * d * (1 + 0.6 * smoothstep(12, 30, d)) - 0.0
    else: z = SEA + 0.10 * d
    z += 0.03 * noise.noise(Vector((x * 0.6, y * 0.6, 0.3))) + 0.35 * noise.noise(Vector((x * 0.06, y * 0.06, 1.3))) * smoothstep(10, 30, d)
    z += 1.6 * smoothstep(22, 45, d)       # the dunes and the down behind
    return z
Z0 = gz(0, 0)
def h(x, y): return gz(x, y) - Z0
SEA_Z = SEA - Z0

# ----------------------------------------------------------------------------- materials
def sand_mat(name):
    """Beach sand: pale and dry up the beach with wind ripples, darker and smooth where the tide has been, a line of
    weed and shell grit at the high-water mark; wet sand shiny."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2200, 0)); s = sep_xyz(nt, co, (-2000, 0))
    wet = node(nt, "ShaderNodeAttribute", (-1800, 600)); wet.attribute_name = "wet"; wet.attribute_type = 'GEOMETRY'
    n1 = noise_(nt, co, 0.8, 5, 0.6, loc=(-1700, 300)); n2_ = noise_(nt, co, 12.0, 5, 0.6, loc=(-1700, 0))
    rp = node(nt, "ShaderNodeTexWave", (-1700, -300)); rp.inputs["Scale"].default_value = 4.0; rp.inputs["Distortion"].default_value = 4.0; rp.bands_direction = 'Y'
    nt.links.new(co, rp.inputs["Vector"])
    dry = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.3, 0.7, 0, 1), c4(srgb((0.74, 0.66, 0.50))), c4(srgb((0.82, 0.75, 0.60))), (-1300, 200))
    wetc = mix_rgb(nt, 'MIX', maprange(nt, n2_.outputs["Fac"], 0.3, 0.7, 0, 1), c4(srgb((0.48, 0.42, 0.32))), c4(srgb((0.56, 0.49, 0.38))), (-1300, -100))
    w = maprange(nt, wet.outputs["Fac"], 0.3, 0.7, 0, 1, (-1300, 500))
    col = mix_rgb(nt, 'MIX', w, dry, wetc, (-1000, 100))
    tide = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', wet.outputs["Fac"], 0.75), None, (-1400, 800)), (-1250, 800)), 1.0)
    weed = math_(nt, 'MULTIPLY', maprange(nt, tide, 0.92, 0.98, 0, 1, (-1100, 800)), maprange(nt, n2_.outputs["Fac"], 0.45, 0.6, 0, 1, (-1100, 950)), (-900, 850))
    col = mix_rgb(nt, 'MIX', weed, col, c4(srgb((0.18, 0.16, 0.10))), (-700, 100))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, w, 0, 1, 0.9, 0.35, (-600, -200)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', rp.outputs["Fac"], math_(nt, 'SUBTRACT', 1.0, w)), math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.4)), 0.25, 0.01, (0, -500))
    return m


def sea_mat(name):
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-1800, 0))
    n1 = noise_(nt, co, 0.08, 4, 0.55, loc=(-1400, 200)); n2_ = noise_(nt, co, 1.2, 6, 0.65, loc=(-1400, -100))
    col = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.3, 0.7, 0, 1), c4(srgb((0.10, 0.22, 0.26))), c4(srgb((0.16, 0.30, 0.32))), (-1000, 100))
    att = node(nt, "ShaderNodeAttribute", (-1200, -400)); att.attribute_name = "Col"
    sg = sep_xyz(nt, att.outputs["Color"], (-1000, -400))
    col = mix_rgb(nt, 'MIX', maprange(nt, math_(nt, 'MULTIPLY', sg.outputs["Y"], n2_.outputs["Fac"]), 0.15, 0.4, 0, 1, (-800, -300)), col, c4(srgb((0.86, 0.88, 0.88))), (-600, 100))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.1; b.inputs["Specular IOR Level"].default_value = 0.5
    bump_from(nt, b, n2_.outputs["Fac"], 0.5, 0.08, (0, -500))
    return m


def quilt_mat(name):
    """Thirteen folds of the Blefuscudians' strongest linen quilted together: off-white, rows of tiny stitching every
    few centimetres in a diamond grid, slightly puffed between."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2000, 0)); s = sep_xyz(nt, co, (-1800, 0))
    u = math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-1600, 100)); v = math_(nt, 'SUBTRACT', s.outputs["X"], s.outputs["Y"], (-1600, -100))
    u = math_(nt, 'ADD', u, s.outputs["Z"], (-1500, 100))
    q1 = maprange(nt, math_(nt, 'FRACT', math_(nt, 'DIVIDE', u, 0.06), None, (-1400, 100)), 0.0, 0.08, 1, 0, (-1250, 100))
    q2 = maprange(nt, math_(nt, 'FRACT', math_(nt, 'DIVIDE', v, 0.06), None, (-1400, -100)), 0.0, 0.08, 1, 0, (-1250, -100))
    st = math_(nt, 'MAXIMUM', q1, q2, (-1100, 0))
    n = noise_(nt, co, 2.0, 4, 0.6, loc=(-1400, 400))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1), c4(srgb((0.84, 0.81, 0.72))), c4(srgb((0.92, 0.89, 0.81))), (-900, 200))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', st, 0.25), col, (0.6, 0.58, 0.52, 1), (-700, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9; b.inputs["Sheen Weight"].default_value = 0.3
    bump_from(nt, b, math_(nt, 'SUBTRACT', 1.0, st), 0.4, 0.004, (0, -400))
    return m


M_SAND = sand_mat("M_Sand")
M_SEA = sea_mat("M_Sea")
M_QUILT = quilt_mat("M_QuiltedSail")
M_HULL = noisy("M_BoatPlanks", [srgb((0.40, 0.33, 0.25)), srgb((0.50, 0.42, 0.32)), srgb((0.32, 0.26, 0.20)), srgb((0.44, 0.40, 0.34))], scale=2.5, rough=(0.65, 0.9), bump=0.3, stretch=(0.4, 6.0, 0.4))
M_TALLOWED = noisy("M_TallowedSeam", [srgb((0.72, 0.68, 0.56)), srgb((0.62, 0.58, 0.46))], scale=20.0, rough=0.5, bump=0.1)
M_GREENWOOD = noisy("M_NewTimber", [srgb((0.62, 0.52, 0.36)), srgb((0.70, 0.60, 0.43)), srgb((0.52, 0.42, 0.28))], scale=3.0, rough=0.8, bump=0.2, stretch=(0.5, 0.5, 6.0))
M_ROPE = noisy("M_TwistedRope", [srgb((0.62, 0.54, 0.40)), srgb((0.52, 0.44, 0.31)), srgb((0.70, 0.62, 0.48))], scale=60.0, rough=0.85, bump=0.8, bump_dist=0.01, stretch=(1, 1, 6))
M_STONE = noisy("M_AnchorStone", [srgb((0.40, 0.39, 0.36)), srgb((0.50, 0.48, 0.44)), srgb((0.30, 0.30, 0.28))], scale=3.0, rough=0.8, bump=0.6, bump_dist=0.02)
M_TINYWOOD = noisy("M_TinyTimber", [srgb((0.60, 0.50, 0.36)), srgb((0.50, 0.40, 0.28))], scale=12.0, rough=0.8, bump=0.1)
M_CASK = noisy("M_TallowCasks", [srgb((0.46, 0.34, 0.22)), srgb((0.54, 0.41, 0.27))], scale=20.0, rough=0.7, bump=0.1)
M_TOWN = noisy("M_TownStone", [srgb((0.76, 0.70, 0.60)), srgb((0.68, 0.62, 0.52)), srgb((0.82, 0.78, 0.70))], scale=3.0, rough=0.85, bump=0.0)
M_ROOFS = noisy("M_TownRoofs", [srgb((0.55, 0.28, 0.20)), srgb((0.45, 0.24, 0.18)), srgb((0.40, 0.38, 0.36))], scale=2.0, rough=0.8, bump=0.0)
M_SHIPHULL = noisy("M_ShipHulls", [srgb((0.22, 0.17, 0.12)), srgb((0.30, 0.24, 0.17))], scale=4.0, rough=0.6, bump=0.05)
M_SHIPSAIL = plain("M_ShipSails", srgb((0.86, 0.82, 0.72)), rough=0.9)
M_FLAG = plain("M_Pennants", srgb((0.20, 0.30, 0.62)), rough=0.8)
M_IRON = noisy("M_Iron", [srgb((0.08, 0.07, 0.06)), srgb((0.20, 0.12, 0.08))], scale=20.0, rough=0.7, metallic=0.5)
GREENS = [(0.42, 0.46, 0.22), (0.50, 0.50, 0.26), (0.38, 0.42, 0.20), (0.56, 0.54, 0.30)]
TIPS = [(0.66, 0.62, 0.38), (0.70, 0.66, 0.44)]
STRAW = [(0.76, 0.68, 0.48), (0.70, 0.62, 0.42)]
IMG_GRASS = S.grass_atlas("A_DuneGrass", GREENS, TIPS, STRAW, seed=23, dead_share=0.35, short_len=(110, 240), long_len=(300, 500))
M_GRASS = image_mat("M_DuneGrass", IMG_GRASS, rough=0.8, alpha=True, spec=0.25)
M_SKY = S.sky_mat(zenith=srgb((0.32, 0.50, 0.78)), horizon=srgb((0.88, 0.86, 0.80)), ground=srgb((0.30, 0.40, 0.42)), sun_dir=SUN_DIR,
                  glow=srgb((1.0, 0.80, 0.55)), glow_k=1.0, glow_pow=9.0, clouds=0.2, cloud_col=srgb((0.98, 0.93, 0.86)),
                  cloud_dark=srgb((0.72, 0.74, 0.80)), cloud_scale=0.6, land=srgb((0.52, 0.58, 0.62)), land_h=0.006, strength=1.0)

# ----------------------------------------------------------------------------- beach and sea
print("beach ...", flush=True)
near = S.polar_terrain("GroundNear", h, M_SAND, r_max=16.0, r0=0.06, rings=36, seg=88, uv_disc=True)
far = S.polar_terrain("FarLand", h, M_SAND.copy(), r_max=300.0, r0=16.0, rings=18, seg=88, r_min=16.0, uv_disc=True)
far.data.materials[0].name = "M_FarSand"
for o in (near, far):
    me = o.data; at = me.attributes.new("wet", 'FLOAT', 'POINT')
    at.data.foreach_set("value", [1.0 - smoothstep(0.0, 6.0, shore(v.co.x) - v.co.y) for v in me.vertices])
sea = S.polar_terrain("water.ocean.sea", lambda x, y: SEA_Z, M_SEA, r_max=1000.0, r0=2.0, rings=30, seg=72, centre=(0.0, 14.0))
me = sea.data; ca = me.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT'); vals = []
for v in me.vertices:
    d = v.co.y - shore(v.co.x)
    g = math.exp(-max(0.0, d) / 0.7) * (0.45 + 0.35 * noise.noise(Vector((v.co.x * 0.3, 0, 2))))
    vals += [0.0, max(0.0, min(1.0, g)), 0.0, 1.0]
ca.data.foreach_set("color", vals); me.color_attributes.active_color = ca
# dune grass behind the beach
gm = MB(); RG = random.Random(4); placed = 0
for i in range(20000):
    x = RG.uniform(-30, 30); y = RG.uniform(-30, 6)
    d = shore(x) - y
    if d < 13 or math.hypot(x, y) > 28: continue
    if RG.random() > smoothstep(13, 22, d) * (0.6 + 0.4 * n2(x, y, 2.0, 3.0)): continue
    z = h(x, y); sc = RG.uniform(0.7, 1.2)
    to_r = Vector((-x, -y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + RG.gauss(0, 0.5)
    card(gm, (x, y, z - 0.02), Vector((math.cos(ya), math.sin(ya), 0)) * 0.5 * sc, Vector((0, 0, 0.5 * sc)), RG.choice(S.GRASS_LONG), 0.0, 1.0, segs=2,
         bend=Vector((RG.gauss(0, 0.1), RG.gauss(0, 0.1), 0)))
    placed += 1
    if placed > 900: break
go = gm.build("veg.grass.dunes", M_GRASS)
set_card_normals(go, lambda p: Vector((0, 0, 1)))

# ----------------------------------------------------------------------------- the full-size boat
print("boat ...", flush=True)
BL, BB, BD = 6.8, 2.1, 0.85
RB = Matrix.Rotation(BOAT_YAW, 3, 'Z')
def BP(x, y, z): return BOAT + RB @ Vector((x, y, z))
bz0 = max(h(*BP(0, k, 0).xy) for k in (-3, 0, 3)) + 0.18      # on its keel blocks
def half(t):                      # half beam along the length (t 0 stern .. 1 bow)
    return BB / 2 * (math.sin(math.pi * (0.12 + 0.84 * t)) ** 0.75) * (1.0 if t < 0.85 else 1.0 - (t - 0.85) * 2.5) + 0.04
hull = MB(); inside = MB(); seams = MB()
NT, NS = 22, 8
rows_o = []
for j in range(NT + 1):
    t = j / NT; y = -BL / 2 + BL * t
    hw = half(t); sheer_z = BD + 0.18 * (2 * t - 1) ** 2 + 0.08 * t
    ring = []
    for k in range(NS + 1):
        a = math.pi * k / NS          # 0 port gunwale .. pi starboard gunwale through the keel
        x = -math.cos(a) * hw; zz = sheer_z - math.sin(a) * (sheer_z - 0.02 - 0.05 * (1 - math.sin(math.pi * t)))
        x *= (0.55 + 0.45 * ((zz - 0.02) / max(0.1, sheer_z)) ** 0.5)
        ring.append(Vector((x, y, zz)))
    rows_o.append(ring)
for j in range(NT):
    for k in range(NS):
        p = [BP(*rows_o[j][k]) + Vector((0, 0, bz0)), BP(*rows_o[j][k + 1]) + Vector((0, 0, bz0)), BP(*rows_o[j + 1][k + 1]) + Vector((0, 0, bz0)), BP(*rows_o[j + 1][k]) + Vector((0, 0, bz0))]
        mb_quad(hull, [p[1], p[0], p[3], p[2]])
        pin = [q - (q - BP(0, rows_o[j][0].y, rows_o[j][0].z * 0.5) - Vector((0, 0, bz0))).normalized() * 0.03 for q in p]
        mb_quad(inside, pin)
    # clinker lands: a thin strip proud along each strake (the seams paid with tallow on the near side)
for k in range(1, NS):
    for j in range(NT):
        a = rows_o[j][k]; b_ = rows_o[j + 1][k]
        for side in (1,):
            q0 = BP(a.x * 1.015, a.y, a.z) + Vector((0, 0, bz0)); q1 = BP(b_.x * 1.015, b_.y, b_.z) + Vector((0, 0, bz0))
            mb_quad(seams, [q0, q1, q1 + Vector((0, 0, 0.022)), q0 + Vector((0, 0, 0.022))])
hull.build("BoatHull", M_HULL, sway=False)
inside.build("BoatInside", M_HULL, sway=False)
seams.build("BoatSeams", M_TALLOWED, sway=False)
# gunwales, stem, sternpost, transom, thwarts, keel blocks and rollers
for sgn in (0, NS):
    pts = [BP(*rows_o[j][sgn]) + Vector((0, 0, bz0 + 0.02)) for j in range(NT + 1)]
    tube(f"Gunwale{sgn}", pts, 0.035, M_GREENWOOD, sides=5)
tube("Stem", [BP(0, BL / 2 - 0.05, 0.05) + Vector((0, 0, bz0)), BP(0, BL / 2 + 0.12, BD * 0.6) + Vector((0, 0, bz0)), BP(0, BL / 2 + 0.16, BD + 0.42) + Vector((0, 0, bz0))], 0.06, M_HULL, sides=6)
tube("Sternpost", [BP(0, -BL / 2 + 0.05, 0.05) + Vector((0, 0, bz0)), BP(0, -BL / 2 - 0.05, BD + 0.3) + Vector((0, 0, bz0))], 0.06, M_HULL, sides=6)
for k, t in enumerate((0.3, 0.5, 0.7)):
    y = -BL / 2 + BL * t; hw = half(t)
    box(f"Thwart{k}", (hw * 1.8, 0.22, 0.05), tuple(BP(0, y, BD * 0.72) + Vector((0, 0, bz0))), M_HULL, rot=(0, 0, BOAT_YAW))
for k, t in enumerate((0.2, 0.5, 0.8)):
    y = -BL / 2 + BL * t
    box(f"KeelBlock{k}", (0.5, 0.35, 0.3), tuple(BP(0, y, 0) + Vector((0, 0, h(*BP(0, y, 0).xy) + 0.08))), M_GREENWOOD, rot=(0, 0, BOAT_YAW))
for k, t in enumerate((0.35, 0.95)):       # rollers laid toward the sea for the launching
    p = BP(0, -BL / 2 + BL * t + 1.5 * k, 0)
    tube(f"Roller{k}", [Vector((p.x - 1.0, p.y, h(p.x - 1.0, p.y) + 0.12)), Vector((p.x + 1.0, p.y, h(p.x + 1.0, p.y) + 0.12))], 0.12, M_GREENWOOD, sides=8)
# the mast of a Blefuscudian timber-tree, stepped at the forward thwart, the yard with the first quilted sail brailed up
mp0 = BP(0, -BL / 2 + BL * 0.7, 0.1) + Vector((0, 0, bz0)); mtop = mp0 + Vector((0, 0, 5.2))
tube("Mast", [mp0, mtop], [0.09, 0.06], M_GREENWOOD, sides=8)
yard_c = mtop - Vector((0, 0, 0.5))
side_v = RB @ Vector((1, 0, 0))
tube("Yard", [yard_c - side_v * 1.6, yard_c + side_v * 1.6], 0.045, M_GREENWOOD, sides=6)
sl = MB()
n = 10
for i in range(n + 1):
    t = i / n; c = yard_c - side_v * 1.5 + side_v * 3.0 * t + Vector((0, 0, -0.2))
    rr = 0.16 * (1 - 0.3 * abs(2 * t - 1)) + 0.02 * math.sin(i * 1.7)
    ring = [sl.vert(c + RB @ Vector((0, math.cos(a) * rr, 0)) + Vector((0, 0, math.sin(a) * rr)), (t, a), 0.2) for a in np.linspace(0, 2 * math.pi, 9)[:-1]]
    if i > 0:
        for q in range(8): sl.face(prev[q], prev[(q + 1) % 8], ring[(q + 1) % 8], ring[q])
    prev = ring
sl.build("cloth.sail.brailed", M_QUILT)
for sgn in (-1, 1):    # shrouds of Gulliver's twisted ropes to the gunwales
    foot = BP(sgn * half(0.62) * 0.95, -BL / 2 + BL * 0.62, BD) + Vector((0, 0, bz0))
    tube(f"Shroud{sgn}", [mtop - Vector((0, 0, 0.3)), foot], 0.018, M_ROPE, sides=5)
tube("Forestay", [mtop - Vector((0, 0, 0.25)), BP(0, BL / 2 + 0.16, BD + 0.4) + Vector((0, 0, bz0))], 0.018, M_ROPE, sides=5)
# the second sail laid out on the sand being quilted (a little rumpled, one corner turned back)
SC = Vector((2.4, 0.8, 0.0)); sw, sd = 3.2, 2.8
qs = MB(); nn = 12
rows_ = []
for j in range(nn + 1):
    row = []
    for i in range(nn + 1):
        u, v = i / nn, j / nn
        x = SC.x - sw / 2 + sw * u; y = SC.y - sd / 2 + sd * v
        z = h(x, y) + 0.02 + 0.03 * noise.noise(Vector((u * 3, v * 3, 1.0)))
        if u > 0.8 and v > 0.8: z += (u - 0.8) * (v - 0.8) * 8.0
        row.append(qs.vert(Vector((x, y, z)), (u, v)))
    rows_.append(row)
for j in range(nn):
    for i in range(nn): qs.face(rows_[j][i], rows_[j][i + 1], rows_[j + 1][i + 1], rows_[j + 1][i])
qs.build("SailOnSand", M_QUILT, sway=False)
# oars and paddles of new timber, laid against the boat and on the sand
for k in range(3):
    p0 = Vector((-3.4 + k * 0.25, 0.4 + k * 0.4, 0)); p0.z = h(p0.x, p0.y) + 0.06
    p1 = p0 + Vector((0.3, 3.6, 0)); p1.z = h(p1.x, p1.y) + 0.06
    tube(f"Oar{k}", [p0, p1], [0.04, 0.035], M_GREENWOOD, sides=6)
    box(f"OarBlade{k}", (0.16, 0.7, 0.025), tuple(p1 + Vector((0.03, 0.35, 0.0))), M_GREENWOOD, rot=(0, 0, -0.08))
# the great anchor stone in a sling of cable, its cable coiled on the sand
AS = Vector((0.9, 5.6, 0)); AS.z = h(AS.x, AS.y)
K.sphere("AnchorStone", 0.42, (AS.x, AS.y, AS.z + 0.25), M_STONE, seg=12, scale=(1.3, 1.0, 0.75))
for a in (0.0, math.pi / 2):
    ring = [Vector((AS.x + math.cos(t) * 0.58 * math.cos(a), AS.y + math.cos(t) * 0.46 * math.sin(a), AS.z + 0.25 + math.sin(t) * 0.34)) for t in np.linspace(0, 2 * math.pi, 15)]
    tube(f"Sling{a:.1f}", ring, 0.03, M_ROPE, sides=5, caps=False)
cc = Vector((1.9, 4.4, 0)); cc.z = h(cc.x, cc.y) + 0.04
pts = []
for k in range(5 * 18 + 1):
    a = 2 * math.pi * k / 18; rr = 0.55 - 0.08 * (k / 18)
    pts.append(Vector((cc.x + math.cos(a) * rr, cc.y + math.sin(a) * rr, cc.z + 0.05 * (k // 18))))
pts.append(Vector((AS.x + 0.5, AS.y - 0.3, AS.z + 0.15)))
tube("Cable", pts, 0.045, M_ROPE, sides=6, caps=False)
# the tallow of three hundred cows in little barrels (each a Blefuscudian hogshead, mug-sized), stacked in a pyramid
cm = MB()
TC = Vector((-3.8, 4.4, 0))
for layer in range(4):
    for i in range(6 - layer):
        for j in range(5 - layer):
            c = Vector((TC.x + (i - (5 - layer) / 2) * 0.085, TC.y + (j - (4 - layer) / 2) * 0.085, h(TC.x, TC.y) + 0.05 + layer * 0.095))
            for q in range(7):
                a0, a1 = 2 * math.pi * q / 7, 2 * math.pi * (q + 1) / 7
                for (z0, z1, r0_, r1_) in ((-0.05, 0.0, 0.034, 0.04), (0.0, 0.05, 0.04, 0.034)):
                    vs = [cm.vert(c + Vector((math.cos(a0) * r0_, math.sin(a0) * r0_, z0))), cm.vert(c + Vector((math.cos(a1) * r0_, math.sin(a1) * r0_, z0))),
                          cm.vert(c + Vector((math.cos(a1) * r1_, math.sin(a1) * r1_, z1))), cm.vert(c + Vector((math.cos(a0) * r1_, math.sin(a0) * r1_, z1)))]
                    cm.face(*vs)
            top = [cm.vert(c + Vector((math.cos(2 * math.pi * q / 7) * 0.034, math.sin(2 * math.pi * q / 7) * 0.034, 0.05))) for q in range(7)]
            cm.face(*top)
cm.build("TallowCasks", M_CASK, sway=False)
# the ship-carpenters' scaffolds, trestles and ladders (at their scale) against the hull, and their tool-sheds
tw = MB()
def tube_mb(mb, p0, p1, r, sides=4):
    d = (p1 - p0).normalized(); up = d.cross(Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))).normalized(); v = d.cross(up)
    r0 = [mb.vert(p0 + (up * math.cos(2 * math.pi * k / sides) + v * math.sin(2 * math.pi * k / sides)) * r) for k in range(sides)]
    r1 = [mb.vert(p1 + (up * math.cos(2 * math.pi * k / sides) + v * math.sin(2 * math.pi * k / sides)) * r) for k in range(sides)]
    for k in range(sides): mb.face(r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k])
def scaffold(c, yaw, hgt, w=0.5, d=0.25):
    Rm = Matrix.Rotation(yaw, 3, 'Z')
    def P(x, y, z): return c + Rm @ Vector((x, y, z))
    for sx in (-1, 1):
        for sy in (-1, 1): tube_mb(tw, P(sx * w / 2, sy * d / 2, 0), P(sx * w / 2, sy * d / 2, hgt), 0.006)
    for zz in (hgt * 0.5, hgt):
        for k in range(6): mb_box(tw, P(-w / 2 + (k + 0.5) * w / 6, 0, zz), (w / 6 - 0.004, d + 0.02, 0.008), yaw=yaw)
    for sy in (-1, 1): tube_mb(tw, P(-w / 2, sy * d / 2, 0.02), P(w / 2, sy * d / 2, hgt * 0.9), 0.003)
    # its ladder
    f0 = P(w / 2 + 0.15, -d / 2, 0); f1 = P(w / 2, -d / 2, hgt)
    for s_ in (-1, 1): tube_mb(tw, f0 + Rm @ Vector((0, s_ * 0.02, 0)), f1 + Rm @ Vector((0, s_ * 0.02, 0)), 0.003)
    nr = int(hgt / 0.025)
    for r in range(1, nr): q = f0.lerp(f1, r / nr); tube_mb(tw, q - Rm @ Vector((0, 0.02, 0)), q + Rm @ Vector((0, 0.02, 0)), 0.0015, 3)
for k, t in enumerate((0.25, 0.5, 0.75)):
    for sgn in (-1, 1):
        if sgn < 0 and k == 1: continue
        p = BP(sgn * (half(t) + 0.35), -BL / 2 + BL * t, 0); p.z = h(p.x, p.y)
        scaffold(p, BOAT_YAW, 0.55 + 0.1 * k)
tw.build("Scaffolds", M_TINYWOOD, sway=False)
# a carpenters' shed and sawpit with planks (1/12)
box("ShedWalls", (1.2, 0.8, 0.5), (-6.5, -1.5, h(-6.5, -1.5) + 0.25), M_TINYWOOD)
box("ShedRoof", (1.35, 0.95, 0.06), (-6.5, -1.5, h(-6.5, -1.5) + 0.56), M_ROOFS, rot=(0.15, 0, 0))
for k in range(8): box(f"PlankStack{k}", (0.9, 0.08, 0.012), (-5.2, -0.4 + k * 0.0, h(-5.2, -0.4) + 0.01 + k * 0.013), M_TINYWOOD, rot=(0, 0, 0.3 + 0.02 * k))

# ----------------------------------------------------------------------------- the harbour mole and the port town (1/12), ships at anchor
print("town and ships ...", flush=True)
tm = MB(); tr = MB()
def cbox(mb, c, sx, sy, sz, yaw=0.0):
    mb_box(mb, Vector((c.x, c.y, c.z + sz / 2)), (sx, sy, sz), yaw=yaw)
mb_box(tm, Vector((TOWN.x - 14, 27.0, SEA_Z + 0.1)), (1.5, 26.0, 0.9))           # the mole out into the sea, a parapet along it
mb_box(tm, Vector((TOWN.x - 14.6, 27.0, SEA_Z + 0.7)), (0.3, 26.0, 0.35))
cbox(tm, Vector((TOWN.x - 14, 40.5, SEA_Z + 0.55)), 0.9, 0.9, 2.2)               # the light tower at its end
cbox(tr, Vector((TOWN.x - 14, 40.5, SEA_Z + 2.75)), 1.0, 1.0, 0.25)
RT = random.Random(8)
def house(p, sx, sy, sz, yaw):
    cbox(tm, p, sx, sy, sz, yaw)
    Rm = Matrix.Rotation(yaw, 3, 'Z'); top = p + Vector((0, 0, sz)); rh = sy * 0.45
    q = [top + Rm @ Vector((x, y, z)) for (x, y, z) in ((-sx / 2 - 0.05, -sy / 2 - 0.05, 0), (sx / 2 + 0.05, -sy / 2 - 0.05, 0), (sx / 2 + 0.05, 0, rh), (-sx / 2 - 0.05, 0, rh),
                                                            (-sx / 2 - 0.05, sy / 2 + 0.05, 0), (sx / 2 + 0.05, sy / 2 + 0.05, 0))]
    mb_quad(tr, [q[0], q[1], q[2], q[3]]); mb_quad(tr, [q[5], q[4], q[3], q[2]])
    for (a_, b_, c_) in ((0, 3, 4), (1, 5, 2)):
        vs = [tm.vert(q[a_]), tm.vert(q[b_]), tm.vert(q[c_])]; tm.face(*vs)
placed = 0
for k in range(400):
    p = TOWN + Vector((RT.uniform(-14, 20), RT.uniform(-24, 12), 0)); p.z = h(p.x, p.y) - 0.05
    if p.y > shore(p.x) - 1.5: continue
    yaw = 0.2 + (math.pi / 2 if RT.random() < 0.3 else 0.0)
    house(p, RT.uniform(0.7, 1.2), RT.uniform(0.6, 0.9), RT.uniform(0.6, 1.1), yaw)
    placed += 1
    if placed > 110: break
for k in range(12):      # the town wall along the shore with towers, two and a half feet high
    p = TOWN + Vector((-15 + k * 3.0, -25 + k * 0.6, 0)); p.z = h(p.x, p.y)
    cbox(tm, p, 3.0, 0.25, 0.75, 0.2)
    if k % 3 == 0: cbox(tm, p, 0.6, 0.6, 1.4, 0.2); cbox(tr, p + Vector((0, 0, 1.4)), 0.7, 0.7, 0.12, 0.2)
c = TOWN + Vector((4.0, -4.0, 0)); c.z = h(c.x, c.y)
cbox(tm, c, 3.0, 1.6, 1.6, 0.2); cbox(tm, c + Vector((1.6, 0, 0)), 0.9, 0.9, 3.4, 0.2)      # the church and its tower
sp = c + Vector((1.6, 0, 3.4))
for k in range(4):
    a0, a1 = math.pi / 2 * k + 0.2 + math.pi / 4, math.pi / 2 * (k + 1) + 0.2 + math.pi / 4
    vs = [tr.vert(sp + Vector((math.cos(a0) * 0.64, math.sin(a0) * 0.64, 0))), tr.vert(sp + Vector((math.cos(a1) * 0.64, math.sin(a1) * 0.64, 0))), tr.vert(sp + Vector((0, 0, 2.2)))]
    tr.face(*vs)
tm.build("Town", M_TOWN, sway=False)
tr.build("TownRoofs", M_ROOFS, sway=False)
hm = MB(); sm = MB(); fm = MB(); rm = MB()
def tiny_ship(c, yaw, L=2.75):
    Rm = Matrix.Rotation(yaw, 3, 'Z')
    def P(x, y, z): return c + Rm @ Vector((x, y, z))
    rows_ = []
    for j in range(9):
        t = j / 8; y = -L / 2 + L * t; bb = L * 0.13 * math.sin(math.pi * (0.1 + 0.85 * t)) ** 0.7 + 0.02
        rows_.append([hm.vert(P(sg * bb * k_, y, -0.2 + 0.45 * zf + 0.05 * (2 * t - 1) ** 2)) for sg, k_, zf in ((-1, 0.7, 0.0), (-1, 1, 0.6), (-1, 1, 1.0), (1, 1, 1.0), (1, 1, 0.6), (1, 0.7, 0.0))])
    for j in range(8):
        for k in range(5): hm.face(rows_[j][k], rows_[j][k + 1], rows_[j + 1][k + 1], rows_[j + 1][k])
    for k, (my, mh) in enumerate(((0.6, 2.1), (-0.15, 2.3), (-0.85, 1.6))):
        tube_mb(rm, P(0, my, 0.2), P(0, my, 0.2 + mh), 0.02)
        for j, zy in enumerate((0.45, 0.75)):
            span = L * (0.32 - 0.08 * j)
            q0, q1 = P(-span / 2, my + 0.03, 0.2 + mh * zy), P(span / 2, my + 0.03, 0.2 + mh * zy)
            tube_mb(rm, q0, q1, 0.012)
            tube_mb(sm, q0 + Vector((0, 0, -0.03)), q1 + Vector((0, 0, -0.03)), 0.025, 5)
        top = P(0, my, 0.2 + mh)
        vs = [fm.vert(top, (0, 0), 0), fm.vert(top + Rm @ Vector((0, -0.35, -0.03)), (1, 0), 1), fm.vert(top + Vector((0, 0, -0.08)), (0, 1), 0)]
        fm.face(*vs)
    tube_mb(rm, P(0, L / 2 - 0.1, 0.25), P(0, L / 2 + 0.6, 0.55), 0.015)
for k, (x, y, yaw) in enumerate(((22.0, 34.0, 0.4), (14.0, 46.0, 0.6), (28.0, 52.0, 0.3), (4.0, 62.0, 0.8), (33.0, 40.0, 0.2))):
    tiny_ship(Vector((x, y, SEA_Z)), yaw)
hm.build("Ships", M_SHIPHULL, sway=False)
rm.build("ShipSpars", M_TINYWOOD, sway=False)
sm.build("cloth.sail.ships", M_SHIPSAIL, sway=True)
fm.build("cloth.flag.ships", M_FLAG)

# ----------------------------------------------------------------------------- sky, light, anchors, sounds
SKY = S.sky_dome(M_SKY, radius=1050.0)
S.world(SUN_DIR, sun_energy=4.2, sun_col=(1.0, 0.85, 0.65), sun_angle=0.8,
        sky_cols=(srgb((0.40, 0.42, 0.40)), srgb((0.84, 0.84, 0.82)), srgb((0.34, 0.50, 0.80))), sky_strength=1.2)
RD = Vector((3.4, 3.2, h(3.4, 3.2)))      # beside the boat's bow on its right, the sea ahead
eye, fwd = S.reader(tuple(RD), YAW)
anchor("scene.centre", tuple(BOAT + Vector((0, 0, bz0))))
anchor("boat", tuple(BOAT + Vector((0, 0, bz0))))
anchor("town", tuple(TOWN))
sound("surf", "shore", (0.0, shore(0.0), SEA_Z + 0.2))
sound("surf", "mole", (TOWN.x - 14, 24.0, SEA_Z + 0.3))
sound("gulls", "sea", (5.0, 30.0, 8.0))
sound("crowd", "town", tuple(TOWN + Vector((0, 0, 1.0))))
sound("crowd", "yard", (-6.0, -1.0, 0.5))
sound("wind", "beach", (-4.0, 0.0, 1.5))
page = S.page_preview(eye, fwd)
cams = S.view_cams(eye, YAW, extra=[
    ("Cam_Page", eye, eye + fwd * 10 + Vector((0, 0, -1.2)), 17),
    ("Cam_Boat", Vector((3.6, 7.0, h(3.6, 7.0) + 1.7)), tuple(BOAT + Vector((0, 0, 0.8))), 22),
    ("Cam_Stores", Vector((-1.0, 7.5, h(-1.0, 7.5) + 1.5)), Vector((-3.6, 4.0, 0.2)), 26),
    ("Cam_Town", eye, TOWN + Vector((0, 0, 0.5)), 30),
])
S.finish(ARGS, cams, "blefuscu_shore_boat.gltf", page=page,
         keep_names={"M_DuneGrass": "veg.grass.dunes", "M_Sea": "water.ocean.sea", "M_QuiltedSail": "MESH_QuiltedSail",
                     "M_ShipSails": "cloth.sail.ships", "M_Pennants": "cloth.flag.ships", "M_Sand": "GroundNear", "M_FarSand": "far.land"},
         keep_uv={"M_Sand", "M_FarSand"},
         size_for={"M_Sand": (2048, 256, 1024), "M_FarSand": (1024, 128), "M_Sea": (1024, 128, 512), "M_BoatPlanks": (1024, 128, 512),
                   "M_QuiltedSail": (1024, 128, 512), "M_NewTimber": (512, 64, 256), "M_TwistedRope": (512, 64, 256), "M_AnchorStone": (256, 64, 128),
                   "M_TownStone": (256,), "M_TownRoofs": (128,), "M_SkyDome": (1024,)},
         default_size=(256, 64, 128), no_shadow={"M_SkyDome"})
