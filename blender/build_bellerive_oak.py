"""
Fable: the old oak before the house at Bellerive, in the thunderstorm (Frankenstein, chapter I of Victor's narrative,
book c06). A chapter step-in room: built ahead of time, served from the server, downloaded by the headset.

"When I was about fifteen years old we had retired to our house near Bellerive, when we witnessed a most violent and
terrible thunderstorm. It advanced from behind the mountains of Jura; and the thunder burst at once with frightful
loudness from various quarters of the heavens. I remained, while the storm lasted, watching its progress with curiosity
and delight. As I stood at the door, on a sudden I beheld a stream of fire issue from an old and beautiful oak, which
stood about twenty yards from our house ..."

The moment: the storm at its height, a moment before the strike. The reader stands at the open front door of the
Frankensteins' country house on the eastern shore of the Lake of Geneva, on the top step under the stone door-case,
looking across the wet lawn to the old oak, about twenty yards off, and beyond it the grey, wind-ruffled lake and the
long dark wall of the Jura under the storm, a lit gap in the cloud where the lightning plays behind the mountains.
The house: pale stucco, grey stone dressings, green-painted shutters, stone steps; a gravel sweep, clipped box, a low
wall and a line of poplars at the lake's edge. Everything wet. No people.

Living scene (docs/LIVING_SCENES.md): water.pond.lake (the lake, still-water ripples), veg.crown.oak, veg.crown.poplar,
veg.grass.lawn, veg.shrub.box, cloth.curtain.door (a curtain inside the open door), sound.rain.porch,
sound.wind-trees.oak, sound.wind.lake.

Node names: anchor.reader.entrance (feet on the top step), anchor.reader.look, anchor.scene.centre / anchor.bellerive.oak,
anchor.bellerive.door, anchor.bellerive.jura; light.storm (SUN, very dim, from behind the Jura), light.sky (SUN, cold
fill), light.hall (POINT, a candle-warm glow in the hall behind the reader); SkyDome, far.jura, far.shore.

Axes: metres, +Z up; the reader at the house door facing +Y (across the lake, north-west in the world). The house
front is along y = 0 behind the reader.

Run headless (one Blender at a time):
  blender -b -P blender/build_bellerive_oak.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_bellerive_oak.py -- --render --samples 48 --res 1400 --captures captures/blender/bellerive-oak
  blender -b -P blender/build_bellerive_oak.py -- --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
ARGS = K.setup("bellerive-oak", "out/bellerive-oak", 1780, "BelleriveOak", default_samples=48)
import scene_kit_b2 as B
from scene_kit_b2 import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound,
                          light_obj, camera, smoothstep, lerp, n2, fbm2, link, card, tree, blob, set_card_normals, spray_atlas)
OUT = K.OUT; scene = K.scene
rng = random.Random(1780)

EYE_H = 1.55
STEP_Z = 0.62                      # the top step / door sill above the lawn
READER_XY = (0.0, 0.55)
OAK = Vector((1.8, 18.8))
LAKE_Y = 33.0
NEAR = 40.0
SKY_R = 1080.0
STORM_DIR = Vector((0.15, 1.0, 0.12)).normalized()         # the lit gap in the cloud over the Jura

def H(x, y):
    h = 0.12 * fbm2(x, y, 14.0, 3, 0.7)
    h -= 0.03 * max(0.0, y - 2)                                # the lawn falls gently to the lake
    h -= 0.7 * smoothstep(LAKE_Y - 3.0, LAKE_Y + 1.0, y)
    return h
def gz(x, y): return H(x, y) - H(0, 2)
B.set_ground(gz, (READER_XY[0], READER_XY[1], STEP_Z + EYE_H))

# ----------------------------------------------------------------------------- materials and atlases
print("painting atlases ...", flush=True)
WETG = [(0.04, 0.09, 0.025), (0.05, 0.11, 0.03), (0.035, 0.08, 0.02), (0.06, 0.12, 0.035), (0.045, 0.10, 0.028)]
WETT = [(0.10, 0.17, 0.05), (0.12, 0.19, 0.06), (0.09, 0.15, 0.045)]
IMG_LAWN = B.meadow_atlas("A_LawnCards", greens=WETG, tips=WETT, dry=0.03, seed=21,
                          flowers=[((0.80, 0.78, 0.74), (0.75, 0.6, 0.1), 'daisy'), ((0.70, 0.55, 0.08), (0.5, 0.35, 0.05), 'cup'),
                                   ((0.35, 0.30, 0.55), (0.25, 0.2, 0.4), 'spike'), ((0.80, 0.78, 0.74), (0.8, 0.8, 0.7), 'umbel')])
IMG_OAK = spray_atlas("A_OakSprays", "oaksummer", 81)
IMG_POPLAR = spray_atlas("A_PoplarSprays", "beech", 82, S=512)
M_LAWN_C = image_mat("M_LawnCards", IMG_LAWN, rough=0.55, alpha=True, spec=0.4)
M_OAKL = image_mat("M_OakSprays", IMG_OAK, rough=0.5, alpha=True, spec=0.4)
M_POPL = image_mat("M_PoplarSprays", IMG_POPLAR, rough=0.5, alpha=True, spec=0.4)
M_OAKBARK = B.bark_mat("M_OakBark", base=(0.09, 0.085, 0.075), dark=(0.03, 0.028, 0.025), light=(0.15, 0.14, 0.12), fissure=True, green=0.15, scale=1.6)
M_POPBARK = B.bark_mat("M_PoplarBark", base=(0.11, 0.105, 0.095), dark=(0.04, 0.038, 0.035), light=(0.17, 0.16, 0.15), fissure=True, green=0.1, scale=2.6)
def ground_mat(name="M_Ground"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2000, 0)); s = sep_xyz(nt, co, (-1800, -600)); x = s.outputs["X"]; y = s.outputs["Y"]
    n1 = noise_(nt, co, 0.3, 5, 0.6, loc=(-1500, 300))
    mpb = node(nt, "ShaderNodeMapping", (-1700, -100)); mpb.inputs["Scale"].default_value = (80.0, 80.0, 20.0); nt.links.new(co, mpb.inputs["Vector"])
    fine = noise_(nt, mpb.outputs["Vector"], 1.0, 6, 0.8, loc=(-1500, -100))
    g = ramp(nt, [(0.0, c4((0.018, 0.040, 0.010))), (0.45, c4((0.035, 0.070, 0.018))), (0.8, c4((0.05, 0.085, 0.025))), (1.0, c4((0.07, 0.09, 0.035)))], (-1100, 200))
    nt.links.new(math_(nt, 'ADD', math_(nt, 'MULTIPLY', n1.outputs["Fac"], 0.7, (-1300, 300)), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.4, (-1300, 150)), (-1200, 200)), g.inputs["Fac"])
    # the gravel sweep before the house (y < 4.5) and the path, wet, with puddled hollows
    gr = voronoi_(nt, co, 60.0, 'F1', (-1500, -500))
    grc = ramp(nt, [(0.0, c4((0.14, 0.13, 0.11))), (0.5, c4((0.22, 0.21, 0.18))), (1.0, c4((0.30, 0.28, 0.24)))], (-1100, -500))
    nt.links.new(gr.outputs["Distance"], grc.inputs["Fac"])
    sweep = maprange(nt, math_(nt, 'ADD', y, math_(nt, 'MULTIPLY', n1.outputs["Fac"], 0.4, (-1300, -800)), (-1200, -800)), 4.3, 4.7, 1.0, 0.0, (-1000, -800))
    patch = noise_(nt, co, 1.4, 4, 0.7, loc=(-1500, 600))
    gcol = mix_rgb(nt, 'MULTIPLY', maprange(nt, patch.outputs["Fac"], 0.3, 0.7, 0.0, 0.55, (-1300, 600)), g.outputs["Color"], c4((0.45, 0.55, 0.40)), (-1100, 600))
    leafv = voronoi_(nt, co, 9.0, 'F1', (-1500, 900))
    lwn = node(nt, "ShaderNodeTexWhiteNoise", (-1300, 900)); lwn.noise_dimensions = '3D'; nt.links.new(leafv.outputs["Position"], lwn.inputs["Vector"])
    leaf = math_(nt, 'MULTIPLY', maprange(nt, leafv.outputs["Distance"], 0.12, 0.07, 0.0, 1.0, (-1100, 900)), math_(nt, 'GREATER_THAN', lwn.outputs["Value"], 0.82, (-1100, 1000)), (-950, 950))
    gcol = mix_rgb(nt, 'MIX', leaf, gcol, c4((0.10, 0.11, 0.03)), (-850, 700))
    wetp = maprange(nt, noise_(nt, co, 0.6, 3, 0.5, loc=(-1500, 1200)).outputs["Fac"], 0.6, 0.66, 0.0, 1.0, (-1200, 1200))
    gcol = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', wetp, 0.7, (-1000, 1200)), gcol, c4((0.04, 0.05, 0.05)), (-700, 700))
    col = mix_rgb(nt, 'MIX', sweep, gcol, grc.outputs["Color"], (-600, 100))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(math_(nt, 'MINIMUM', maprange(nt, sweep, 0, 1, 0.55, 0.25, (-500, -300)), maprange(nt, wetp, 0, 1, 0.6, 0.05, (-500, -450)), (-350, -350)), b.inputs["Roughness"])
    bump_from(nt, b, fine.outputs["Fac"], 0.2, 0.01, (0, -400))
    return m
M_GROUND = ground_mat()
M_STUCCO = noisy("M_Stucco", [(0.44, 0.42, 0.37), (0.52, 0.50, 0.45), (0.58, 0.56, 0.51)], scale=3.0, rough=0.85, bump=0.3, ao=0.4)
M_DRESS = noisy("M_GreyStone", [(0.24, 0.24, 0.23), (0.32, 0.32, 0.30), (0.38, 0.38, 0.36)], scale=4.0, rough=0.7, bump=0.4, ao=0.3)
M_SHUTTER = noisy("M_Shutters", [(0.07, 0.14, 0.10), (0.10, 0.18, 0.13)], scale=8.0, rough=0.5, bump=0.1, stretch=(1, 1, 8))
M_DOOR = wood("M_DoorWood", base=(0.14, 0.08, 0.04), dark=(0.05, 0.03, 0.015), light=(0.20, 0.12, 0.06), scale=1.2, rough=(0.3, 0.5), coat=0.2)
M_GLASS = plain("M_Glass", (0.02, 0.025, 0.03), rough=0.05)
M_ROOF = noisy("M_RoofTiles", [(0.12, 0.07, 0.05), (0.18, 0.10, 0.07), (0.15, 0.09, 0.06)], scale=6.0, rough=0.6, bump=0.5, stretch=(1, 1, 3))
M_BOX = noisy("M_BoxHedge", [(0.02, 0.05, 0.015), (0.04, 0.08, 0.025)], scale=25.0, rough=0.7, bump=0.8, bump_dist=0.01)
M_HALL = noisy("M_HallInterior", [(0.20, 0.17, 0.12), (0.28, 0.24, 0.17)], scale=3.0, rough=0.8, bump=0.0)
M_CURTAIN = noisy("M_HallCurtain", [(0.25, 0.07, 0.05), (0.32, 0.10, 0.07)], scale=20.0, rough=0.9, bump=0.1, sheen=0.4)
M_WALL = noisy("M_LowWall", [(0.18, 0.17, 0.15), (0.26, 0.25, 0.22)], scale=2.0, rough=0.85, bump=0.6, bump_dist=0.02)
def lake_mat(name="M_Lake"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-1200, 0)); n = noise_(nt, co, 0.3, 4, 0.6, loc=(-900, 0))
    r = ramp(nt, [(0.0, c4((0.02, 0.03, 0.035))), (1.0, c4((0.05, 0.06, 0.065)))], (-600, 0)); nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.12
    fine = noise_(nt, co, 3.0, 4, 0.6, loc=(-900, -300)); bump_from(nt, b, fine.outputs["Fac"], 0.3, 0.05, (0, -300))
    return m
M_LAKE = lake_mat()
M_JURA = noisy("M_Jura", [(0.035, 0.04, 0.05), (0.05, 0.055, 0.065), (0.065, 0.07, 0.08)], scale=0.02, rough=0.95, bump=0.0)
M_SHORE = noisy("M_FarShore", [(0.03, 0.04, 0.03), (0.05, 0.06, 0.045)], scale=0.05, rough=0.95, bump=0.0)

def storm_sky_mat(name="M_SkyDome"):
    """a thunderstorm advancing from the Jura: a low, heavy, slate-dark deck, ragged rolls of cloud, paler in a band
    over the lake, and one lit gap above the mountains where the lightning plays."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-2200, 0), operation='NORMALIZE'); nt.links.new(co, nv.inputs[0]); d = nv.outputs[0]
    s = sep_xyz(nt, d, (-2000, 0)); el = s.outputs["Z"]
    base = ramp(nt, [(0.0, c4((0.30, 0.32, 0.34))), (0.08, c4((0.24, 0.26, 0.28))), (0.4, c4((0.13, 0.14, 0.16))), (1.0, c4((0.08, 0.085, 0.10)))], (-1500, 400))
    nt.links.new(maprange(nt, el, 0.0, 1.0, 0, 1, (-1700, 400)), base.inputs["Fac"])
    zk = math_(nt, 'ADD', math_(nt, 'MAXIMUM', el, 0.0, (-1800, -200)), 0.05, (-1650, -200))
    px = math_(nt, 'DIVIDE', s.outputs["X"], zk, (-1500, -150)); py = math_(nt, 'DIVIDE', s.outputs["Y"], zk, (-1500, -300))
    cvv = node(nt, "ShaderNodeCombineXYZ", (-1350, -200)); nt.links.new(px, cvv.inputs["X"]); nt.links.new(py, cvv.inputs["Y"]); cvv.inputs["Z"].default_value = 7.7
    n1 = noise_(nt, cvv.outputs[0], 0.4, 7, 0.62, 0.6, (-1100, -200))
    rolls = ramp(nt, [(0.3, c4((0.05, 0.055, 0.07))), (0.55, c4((0.14, 0.15, 0.17))), (0.75, c4((0.24, 0.25, 0.27)))], (-900, -200))
    nt.links.new(n1.outputs["Fac"], rolls.inputs["Fac"])
    col = mix_rgb(nt, 'MIX', maprange(nt, el, 0.01, 0.15, 0.2, 0.9, (-900, 0)), base.outputs["Color"], rolls.outputs["Color"], (-700, 300))
    sd = node(nt, "ShaderNodeVectorMath", (-1700, 800), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(STORM_DIR); nt.links.new(d, sd.inputs[0])
    gap = math_(nt, 'POWER', maprange(nt, sd.outputs["Value"], 0.93, 1.0, 0, 1, (-1500, 800)), 2.0, (-1350, 800))
    gap = math_(nt, 'MULTIPLY', gap, maprange(nt, n1.outputs["Fac"], 0.45, 0.65, 0.2, 1.0, (-1200, 900)), (-1100, 850))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', gap, 0.9, (-1000, 850)), col, (0.62, 0.62, 0.78, 1), (-500, 400))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 0.8
    return m
M_SKY = storm_sky_mat()

# ----------------------------------------------------------------------------- terrain, lake, far shore and the Jura
print("terrain ...", flush=True)
def axis_coords(lo, hi, focus, fine, coarse):
    out = [lo]; x = lo
    while x < hi:
        d = min(abs(x - f) for f in focus); x = min(hi, x + lerp(fine, coarse, smoothstep(2.0, 14.0, d))); out.append(x)
    return out
XS = axis_coords(-NEAR, NEAR, [0.0, OAK.x], 0.7, 3.5)
YS = axis_coords(-6.0, LAKE_Y + 4.0, [3.0, OAK.y], 0.7, 3.0)
verts = []; uvs = []
for y in YS:
    for x in XS:
        verts.append((x, y, gz(x, y))); uvs.append(((x - XS[0]) / (XS[-1] - XS[0]), (y - YS[0]) / (YS[-1] - YS[0])))
nx = len(XS) - 1
faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(len(YS) - 1) for i in range(nx)]
mesh_from("GroundNear", verts, faces, M_GROUND, smooth=True, uvs=uvs)
LZ = gz(0, LAKE_Y) + 0.15
lv = []; lf = []
for j, yy in enumerate([LAKE_Y - 2, LAKE_Y + 10, LAKE_Y + 40, LAKE_Y + 160, 1000.0]):
    for i in range(17):
        lv.append((-1100 + i * 2200 / 16, yy, LZ))
for j in range(4):
    for i in range(16): lf.append((j * 17 + i, j * 17 + i + 1, (j + 1) * 17 + i + 1, (j + 1) * 17 + i))
mesh_from("water.pond.lake", lv, lf, M_LAKE, uvs=[((v[0] + 1100) / 2200, (v[1]) / 1000) for v in lv])
# far shore (the Savoy / Vaud side, low and wooded) and the long dark wall of the Jura beyond
def ridge(name, r_y, x0, x1, h0, h1, mat, n=64, seed=0.0):
    vs = []; fs = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        h = h0 + (h1 - h0) * (0.5 + 0.35 * noise.noise(Vector((x * 0.0025 + seed, seed, 0.0))) + 0.25 * noise.noise(Vector((x * 0.009, seed, 0.5)))) + h1 * 0.06 * noise.noise(Vector((x * 0.04, seed, 1.0)))
        vs.append((x, r_y, LZ - 0.2)); vs.append((x, r_y + 30, LZ + h))
    for i in range(n): fs.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    return mesh_from(name, vs, fs, mat, smooth=True)
ridge("FarShore", 360.0, -900, 900, 4, 12, M_SHORE, seed=2.0)
ridge("Jura", 950.0, -1150, 1150, 40, 95, M_JURA, n=140, seed=5.0)
B.sky_dome("SkyDome", M_SKY, SKY_R, el_min=-6.0)

# ----------------------------------------------------------------------------- the house front behind the reader: steps, door-case, open door, shutters
print("house ...", flush=True)
HW_ = 7.0
box("HouseFront_L", (HW_ - 0.75, 0.6, 7.5), (-(HW_ - 0.75) / 2 - 0.75, -0.3, 3.75 + STEP_Z - 0.1), M_STUCCO)
box("HouseFront_R", (HW_ - 0.75, 0.6, 7.5), ((HW_ - 0.75) / 2 + 0.75, -0.3, 3.75 + STEP_Z - 0.1), M_STUCCO)
box("HouseFront_T", (1.5, 0.6, 7.5 - 2.5), (0, -0.3, STEP_Z + 2.4 + (7.5 - 2.5) / 2 - 0.1), M_STUCCO)
box("Plinth", (2 * HW_, 0.7, STEP_Z + 0.1), (0, -0.28, (STEP_Z + 0.1) / 2 - 0.1), M_DRESS)
box("Cornice", (2 * HW_ + 0.3, 0.9, 0.3), (0, -0.25, STEP_Z + 7.4), M_DRESS, bevel=0.05)
box("Roof", (2 * HW_ + 0.5, 6.0, 0.3), (0, -2.6, STEP_Z + 8.2), M_ROOF, rot=(0.45, 0, 0))
# the door-case: stone architrave, a fanlight, the doors open inwards
for s in (-1, 1): box(f"DoorCase{s}", (0.22, 0.7, 2.6), (s * 0.86, -0.25, STEP_Z + 1.3), M_DRESS, bevel=0.02)
box("DoorLintel", (2.0, 0.72, 0.35), (0, -0.25, STEP_Z + 2.55), M_DRESS, bevel=0.03)
box("DoorCornice", (2.3, 0.85, 0.12), (0, -0.2, STEP_Z + 2.78), M_DRESS, bevel=0.02)
for s in (-1, 1):
    box(f"DoorLeaf{s}", (0.72, 0.06, 2.3), (s * 0.75, -0.95 + 0.0, STEP_Z + 1.15), M_DOOR, rot=(0, 0, s * math.radians(80)) if False else (0, 0, 0)) if False else None
    hinge = Vector((s * 0.75, -0.6, STEP_Z)); d = Vector((0, -1, 0))
    box(f"DoorLeaf{s}", (0.06, 0.72, 2.3), tuple(hinge + d * 0.36 + Vector((0, 0, 1.15))), M_DOOR)
    for k, z in enumerate((0.5, 1.4, 2.0)): box(f"DoorPanel{s}{k}", (0.07, 0.5, 0.5 if k < 2 else 0.3), tuple(hinge + d * 0.36 + Vector((-s * 0.01, 0, z))), M_DOOR, bevel=0.02)
box("HallFloor", (3.0, 4.0, 0.05), (0, -2.6, STEP_Z - 0.03), M_DRESS)
box("HallBack", (3.0, 0.1, 3.5), (0, -4.6, STEP_Z + 1.7), M_HALL)
for s in (-1, 1): box(f"HallSide{s}", (0.1, 4.0, 3.5), (s * 1.5, -2.6, STEP_Z + 1.7), M_HALL)
box("HallCeil", (3.0, 4.0, 0.05), (0, -2.6, STEP_Z + 3.4), M_HALL)
cv = []; cw = []; cf = []
for j in range(7):
    t = j / 6; zz = STEP_Z + 2.4 - t * 2.35
    for i in range(13):
        u = i / 12; cv.append((-0.7 + u * 0.55, -0.9 - 0.04 * math.sin(u * 26), zz)); cw.append(t)
for j in range(6):
    for i in range(12): cf.append((j * 13 + i, j * 13 + i + 1, (j + 1) * 13 + i + 1, (j + 1) * 13 + i))
co_ = mesh_from("cloth.curtain.door", cv, cf, M_CURTAIN, smooth=True)
K.add_sway(co_, lambda p: max(0.0, min(1.0, (STEP_Z + 2.4 - p.z) / 2.35)))
# the steps down to the gravel: three stone treads, the top one the landing the reader stands on
for k in range(3):
    w = 2.4 + k * 0.5; d = 1.15 + k * 0.35
    box(f"Step{k}", (w, d, STEP_Z / 3 + 0.05), (0, d / 2 - 0.05, STEP_Z - k * STEP_Z / 3 - (STEP_Z / 3) / 2 + 0.025), M_DRESS, bevel=0.015)
# windows with their green shutters folded back, either side of the door
for s in (-1, 1):
    for k, x in enumerate((2.6, 5.0)):
        wx = s * x
        box(f"Win{s}{k}", (1.0, 0.05, 1.9), (wx, 0.02, STEP_Z + 1.55), M_GLASS)
        box(f"WinSurround{s}{k}", (1.25, 0.08, 0.15), (wx, 0.03, STEP_Z + 2.55), M_DRESS)
        box(f"WinSill{s}{k}", (1.3, 0.2, 0.08), (wx, 0.08, STEP_Z + 0.55), M_DRESS)
        for t in (-1, 1): box(f"Shutter{s}{k}{t}", (0.5, 0.04, 1.95), (wx + t * 0.78, 0.04, STEP_Z + 1.55), M_SHUTTER)
        for j in range(3): box(f"WinBar{s}{k}{j}", (0.03, 0.06, 1.9), (wx - 0.33 + j * 0.33, 0.03, STEP_Z + 1.55), M_DRESS)
        box(f"UpWin{s}{k}", (1.0, 0.05, 1.5), (wx, 0.02, STEP_Z + 4.6), M_GLASS)
        for t in (-1, 1): box(f"UpShutter{s}{k}{t}", (0.5, 0.04, 1.55), (wx + t * 0.78, 0.04, STEP_Z + 4.6), M_SHUTTER)
box("UpWinC", (1.0, 0.05, 1.5), (0, 0.02, STEP_Z + 4.6), M_GLASS)

# ----------------------------------------------------------------------------- the garden: clipped box, low wall and poplars at the lake, the old oak
print("trees ...", flush=True)
for s in (-1, 1):
    for k in range(3):
        B_ = MB(); B.blob(B_, (s * (1.9 + k * 1.5), 1.2, gz(s * (1.9 + k * 1.5), 1.2) + 0.35), (0.55, 0.45, 0.45), 30 + k + (s > 0) * 5, sub=2, rough=0.12)
        B_.build(f"Box{s}{k}", M_BOX, sway=False)
box("LakeWall", (60.0, 0.5, 0.8), (0, LAKE_Y - 2.5, gz(0, LAKE_Y - 2.5) + 0.2), M_WALL, bevel=0.05)
OAK_T = tree("Oak", OAK.x, OAK.y, 17.0, 9.0, "oak", 91, M_OAKBARK, M_OAKL, nlimbs=8, cards_per_tip=1, card_size=2.4, fill=320, lean=(0.4, -0.3))
for i, x in enumerate((-30, -22, -15.0, 15.0, 22.0, 31.0)):
    tree(f"Poplar{i}", x + rng.uniform(-1, 1), LAKE_Y - 3.5 + rng.uniform(-0.6, 0.6), rng.uniform(17, 22), 2.2, "elm", 100 + i, M_POPBARK, M_POPL,
         nlimbs=5, detail=0.6, cards_per_tip=0, card_size=2.6, fill=45)
for i, (x, y) in enumerate(((-14, 12), (13, 9), (-24, 22))):
    tree(f"Lime{i}", x, y, 13.0, 5.5, "maple", 110 + i, M_POPBARK, M_OAKL, nlimbs=5, detail=0.6, cards_per_tip=0, card_size=3.0, fill=55)
# the lawn: wet grass cards near, none on the gravel sweep
def lawn_ok(x, y):
    if y < 4.6 + 0.4 * n2(x, y, 2.0, 1.0): return 0.0
    if math.hypot(x - OAK.x, y - OAK.y) < 1.1: return 0.0
    if y > LAKE_Y - 3.0: return 0.0
    return 0.6 + 0.4 * (0.5 + 0.5 * n2(x, y, 2.0, 3.0))
mb = MB(); R = random.Random(5)
B.scatter_cards(mb, None, R, 0, 3.5, 9.0, lambda x, y: lawn_ok(x, y) * 0.35 * (0.5 + 0.5 * n2(x, y, 1.5, 7.0)), B.MEADOW_SHORT, height=0.08, width=0.26, solid_from=99, maxcards=700, centre=(0.0, 1.5))
for i in range(160):        # long grass and dock round the oak's foot
    a = R.uniform(0, 2 * math.pi); r = R.uniform(1.2, 2.6); x, y = OAK.x + r * math.cos(a), OAK.y + r * math.sin(a)
    to_r = Vector((-x, -y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + R.gauss(0, 0.4)
    card(mb, (x, y, gz(x, y) - 0.02), Vector((math.cos(ya), math.sin(ya), 0)) * 0.4, Vector((0, 0, 0.45)), R.choice(B.MEADOW_LONG), 0.0, 1.0, segs=2)
go = mb.build("LawnCards", M_LAWN_C); set_card_normals(go, lambda p: Vector((0, 0, 1)))

# ----------------------------------------------------------------------------- lights, anchors
light_obj("light.storm", 'SUN', 1.6, (0.72, 0.76, 0.92), tuple(STORM_DIR * 50), direction=-STORM_DIR, angle=math.radians(25))
sl = light_obj("light.sky", 'SUN', 0.9, (0.55, 0.62, 0.75), (0, 0, 40), direction=(0.05, 0.1, -1.0), angle=math.radians(120)); sl.data.use_shadow = False
light_obj("light.hall", 'POINT', 25.0, (1.0, 0.62, 0.32), (0.2, -2.6, STEP_Z + 2.0), shadow_soft_size=0.2)
B.world_sky(zen=(0.10, 0.11, 0.13), hor=(0.30, 0.32, 0.34), ground=(0.05, 0.06, 0.05), strength=1.2)
vol = scene.world.node_tree.nodes.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.0012; vol.inputs["Color"].default_value = (0.55, 0.58, 0.62, 1)
pass   # no world volume: an infinite haze in Cycles swallows the sun (Unity has its own fog)
E = Vector((READER_XY[0], READER_XY[1], STEP_Z + EYE_H))
B.reader_anchors((READER_XY[0], READER_XY[1], STEP_Z), (READER_XY[0] + 0.1, READER_XY[1] + 1.0, E.z))
anchor("scene.centre", (OAK.x, OAK.y, gz(OAK.x, OAK.y)))
anchor("bellerive.oak", (OAK.x, OAK.y, gz(OAK.x, OAK.y)))
anchor("bellerive.door", (0.0, -0.3, STEP_Z))
anchor("bellerive.jura", (0.0, 520.0, 200.0))
sound("rain", "porch", (0.0, 1.5, STEP_Z + 2.5))
sound("wind-trees", "oak", tuple(OAK_T[1]))
sound("wind", "lake", (0.0, LAKE_Y, LZ + 2))
page = B.page_preview(E, (0.1, 1))
K.apply_transforms()
cams = B.view_cams(E, (0.1, 1), extra=[("Cam_Oak", E + Vector((0.3, 3.0, -0.4)), tuple(OAK_T[1]), 24),
                                       ("Cam_House", Vector((2.5, 12.0, 1.7)), (0.0, 0.0, STEP_Z + 2.0), 24)])
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "bellerive_oak_source.blend"))
K.print_budget()
if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.5, captures_dir=ARGS.captures)
if ARGS.bake or ARGS.export:
    scene.world.node_tree.nodes.remove(vol)
    B.export_room("bellerive_oak.gltf", cams, page=page,
                  keep_names={"M_LawnCards": "veg.grass.lawn", "M_OakSprays": "veg.crown.oak", "M_PoplarSprays": "veg.crown.poplar",
                              "M_Lake": "water.pond.lake", "M_HallCurtain": "cloth.curtain.door", "M_SkyDome": "SkyDome", "M_Jura": "far.jura",
                              "M_FarShore": "far.shore", "M_Ground": "GroundNear", "M_BoxHedge": "veg.shrub.box"},
                  keep_uv={"M_Ground", "M_SkyDome", "M_Lake"},
                  size_for={"M_Ground": (2048, 512, 1024), "M_SkyDome": (2048,), "M_Jura": (256, 32, 64), "M_FarShore": (256, 32, 64), "M_Lake": (512, 64, 256),
                            "M_Stucco": (1024, 128, 512), "M_GreyStone": (1024, 256, 512), "M_OakBark": (1024, 256, 512), "M_PoplarBark": (512, 128, 256),
                            "M_Shutters": (256, 64, 128), "M_DoorWood": (256, 64, 128), "M_BoxHedge": (256, 64, 256), "M_LowWall": (512, 64, 256)},
                  default_size=(128, 64, 128))
print("DONE")
