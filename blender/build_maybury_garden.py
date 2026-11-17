"""
Fable: the narrator's garden and summerhouse on Maybury Hill, Woking (The War of the Worlds, book I, chapter IX,
"The Fighting Begins"). A chapter step-in room: built ahead of time, served from the server, downloaded by the headset.

"... as I sat at tea with my wife in the summerhouse ..." "The sun, shining through the smoke ... seemed blood red, and
threw an unfamiliar lurid light upon everything." "... the trees about the Oriental College burst into smoky red flame,
and the tower of the little church beside it slid down into ruin. The pinnacle of the mosque had vanished, and the
roof-line of the college itself looked as if a hundred-ton gun had been at work upon it. One of our chimneys cracked as
if a shot had hit it, flew, and a piece of it came clattering down the tiles and made a heap of broken red fragments
upon the flower bed by my study window." (chapter IX)

The moment: about six on a hot Saturday evening at the end of June 1898, a moment after the chimney was hit. The reader
stands on the mown lawn just outside the summerhouse (tea laid on its wicker table, the china, a chair pushed back), and
faces over the paling fence and the neighbour's strawberry beds to the treetops about the Oriental College, burning in
smoky red flame a few hundred yards off, the mosque's dome without its pinnacle beside them and the broken stump of the
church tower; the sun a red disc in the smoke. On the right the back of the red-brick villa, tiled roof, the study
window and below it the flower bed with the heap of broken red chimney pot and brick, the cracked stack above. A side
gate in the fence on the left. No people, no Martian machines, no red weed.

Living scene (docs/LIVING_SCENES.md): veg.grass.lawn, veg.flowers.bed, veg.crop.strawberries, veg.crown.garden,
cloth.curtain.study, sound.birds.garden, sound.fire.college, sound.wind-trees.garden.

Node names: anchor.reader.entrance, anchor.reader.look, anchor.scene.centre (the burning treetops' direction, 40 m
out), anchor.maybury.summerhouse, anchor.maybury.flowerbed, anchor.maybury.college; light.sun (SUN, low, red through
smoke), light.sky (SUN, warm brown fill); SkyDome, far.college, far.smoke.

Axes: metres, +Z up, reader at the origin facing +Y; the house on the right (+X), the summerhouse behind-left.

Run headless (one Blender at a time, CPU):
  blender -b -P blender/build_maybury_garden.py -- --cpu --render --quick --res 900 --cams reader
  blender -b -P blender/build_maybury_garden.py -- --cpu --render --samples 40 --res 1280 --captures captures/blender/maybury-garden
  blender -b -P blender/build_maybury_garden.py -- --cpu --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
ARGS = K.setup("maybury-garden", "out/maybury-garden", 1898, "MayburyGarden", default_samples=40)
import scene_kit_b2 as B
from scene_kit_b2 import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound,
                          light_obj, camera, smoothstep, lerp, n2, fbm2, link, card, tree, blob, set_card_normals, spray_atlas)
OUT = K.OUT; scene = K.scene
rng = random.Random(1898)

EYE_H = 1.55
SUN_DIR = Vector((-0.55, 0.80, 0.16)).normalized()       # low in the west-north-west, ahead-left, through the smoke
FENCE_Y = 9.0
HOUSE_X = 7.5
COLLEGE = Vector((40.0, 330.0))                            # the Oriental College trees, ahead and a little right, downhill
NEAR = 30.0

def H(x, y): return 0.06 * fbm2(x, y, 8.0, 3, 0.2) - 0.012 * y
def gz(x, y): return H(x, y) - H(0, 0)
B.set_ground(gz, (0.0, 0.0, EYE_H))

# ----------------------------------------------------------------------------- atlases and materials
print("painting atlases ...", flush=True)
LG = [(0.05, 0.11, 0.02), (0.07, 0.14, 0.03), (0.045, 0.10, 0.02), (0.09, 0.15, 0.035), (0.06, 0.12, 0.025)]
LT = [(0.16, 0.22, 0.06), (0.20, 0.25, 0.08), (0.14, 0.20, 0.05)]
IMG_LAWN = B.meadow_atlas("A_LawnCards", greens=LG, tips=LT, dry=0.12, seed=41,
                          flowers=[((0.85, 0.20, 0.15), (0.2, 0.1, 0.05), 'cup'), ((0.95, 0.85, 0.80), (0.8, 0.7, 0.2), 'daisy'),
                                   ((0.55, 0.30, 0.70), (0.4, 0.2, 0.5), 'spike'), ((0.95, 0.70, 0.15), (0.6, 0.4, 0.1), 'cup')])
B.SPRAY_KINDS["strawberry"] = ([(0.06, 0.13, 0.03), (0.08, 0.16, 0.04), (0.05, 0.11, 0.025)], 5, 12.0, 'broad', (0.5, [(0.62, 0.04, 0.03), (0.70, 0.08, 0.04)], 5.0))
IMG_TREES = spray_atlas("A_GardenSprays", "lime", 51)
IMG_STRAW = spray_atlas("A_StrawberrySprays", "strawberry", 52, S=512)
M_LAWN_C = image_mat("M_LawnCards", IMG_LAWN, rough=0.8, alpha=True, spec=0.2)
M_TREE_L = image_mat("M_GardenSprays", IMG_TREES, rough=0.6, alpha=True, spec=0.3)
M_STRAW = image_mat("M_StrawberrySprays", IMG_STRAW, rough=0.6, alpha=True, spec=0.3)
M_BARK = B.bark_mat("M_GardenBark", base=(0.16, 0.14, 0.12), dark=(0.06, 0.05, 0.045), light=(0.26, 0.24, 0.21), fissure=False, green=0.2)
def lawn_mat(name="M_Lawn"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2000, 0)); s = sep_xyz(nt, co, (-1800, -600)); x = s.outputs["X"]; y = s.outputs["Y"]
    n1 = noise_(nt, co, 0.3, 5, 0.6, loc=(-1500, 300))
    mpb = node(nt, "ShaderNodeMapping", (-1700, -100)); mpb.inputs["Scale"].default_value = (80.0, 80.0, 20.0); nt.links.new(co, mpb.inputs["Vector"])
    fine = noise_(nt, mpb.outputs["Vector"], 1.0, 6, 0.8, loc=(-1500, -100))
    stripe = math_(nt, 'MULTIPLY', math_(nt, 'GREATER_THAN', math_(nt, 'FRACT', math_(nt, 'DIVIDE', x, 1.2, (-1500, 500)), None, (-1350, 500)), 0.5, (-1200, 500)), 0.12, (-1050, 500))
    g = ramp(nt, [(0.0, c4((0.05, 0.09, 0.02))), (0.5, c4((0.08, 0.13, 0.03))), (0.85, c4((0.14, 0.16, 0.05))), (1.0, c4((0.22, 0.20, 0.08)))], (-1100, 200))
    f = math_(nt, 'ADD', math_(nt, 'ADD', math_(nt, 'MULTIPLY', n1.outputs["Fac"], 0.75, (-1300, 300)), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.35, (-1300, 150)), (-1200, 200)), stripe, (-1150, 300))
    nt.links.new(f, g.inputs["Fac"])
    # the flower bed under the study window, the neighbour's strawberry beds beyond the fence: brown soil
    soil = ramp(nt, [(0.3, c4((0.07, 0.045, 0.025))), (0.7, c4((0.11, 0.07, 0.04)))], (-1100, -300)); nt.links.new(fine.outputs["Fac"], soil.inputs["Fac"])
    bed = math_(nt, 'MULTIPLY', maprange(nt, x, HOUSE_X - 1.6, HOUSE_X - 1.4, 0.0, 1.0, (-1300, -500)), maprange(nt, y, 2.0, 2.2, 0.0, 1.0, (-1300, -650)), (-1150, -550))
    bed = math_(nt, 'MULTIPLY', bed, maprange(nt, y, 6.8, 7.0, 1.0, 0.0, (-1300, -800)), (-1000, -600))
    beyond = maprange(nt, math_(nt, 'FRACT', math_(nt, 'DIVIDE', x, 1.4, (-1500, -1000)), None, (-1350, -1000)), 0.55, 0.62, 0.0, 1.0, (-1200, -1000))
    beyond = math_(nt, 'MULTIPLY', maprange(nt, y, FENCE_Y + 0.4, FENCE_Y + 0.6, 0.0, 1.0, (-1200, -1150)), math_(nt, 'SUBTRACT', 1.0, beyond, (-1100, -1050)), (-1000, -1100))
    path = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', x, HOUSE_X - 2.6, (-1500, -1300)), None, (-1350, -1300)), 0.5, 0.6, 1.0, 0.0, (-1200, -1300)),
                 maprange(nt, y, -6.0, -5.8, 0.0, 1.0, (-1200, -1450)), (-1050, -1350))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MAXIMUM', bed, beyond, (-900, -700)), g.outputs["Color"], soil.outputs["Color"], (-700, 100))
    col = mix_rgb(nt, 'MIX', path, col, c4((0.30, 0.25, 0.18)), (-500, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, fine.outputs["Fac"], 0.2, 0.01, (0, -400))
    return m
M_LAWN = lawn_mat()
def brick_mat(name="M_RedBrick"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-1600, 0)); s = sep_xyz(nt, co, (-1400, 0))
    cv = node(nt, "ShaderNodeCombineXYZ", (-1200, 0)); nt.links.new(math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-1300, 100)), cv.inputs["X"]); nt.links.new(s.outputs["Z"], cv.inputs["Y"])
    br = node(nt, "ShaderNodeTexBrick", (-1000, 0), offset=0.5); nt.links.new(cv.outputs[0], br.inputs["Vector"])
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 0.225; br.inputs["Row Height"].default_value = 0.075
    br.inputs["Mortar Size"].default_value = 0.008; br.inputs["Color1"].default_value = (0.30, 0.08, 0.04, 1); br.inputs["Color2"].default_value = (0.38, 0.12, 0.06, 1)
    br.inputs["Mortar"].default_value = (0.42, 0.38, 0.32, 1)
    n = noise_(nt, co, 3.0, 4, 0.6, loc=(-1000, -300))
    col = mix_rgb(nt, 'MULTIPLY', 0.4, br.outputs["Color"], n.outputs["Color"], (-700, 0))
    col = K.ao_mul(nt, col, 0.2, 0.4, (-500, -300))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, br.outputs["Fac"], 0.4, 0.004, (-300, -500))
    return m
M_BRICK = brick_mat()
M_TILE = noisy("M_RoofTiles", [(0.20, 0.07, 0.04), (0.28, 0.10, 0.06), (0.24, 0.09, 0.05)], scale=6, rough=0.6, bump=0.6, stretch=(1, 1, 3), ao=0.4)
M_WHITE = noisy("M_WhitePaint", [(0.66, 0.65, 0.60), (0.74, 0.73, 0.68)], scale=8, rough=0.45, bump=0.1, ao=0.4)
M_GLASS = plain("M_Glass", (0.03, 0.035, 0.04), rough=0.04)
M_PALING = wood("M_Palings", base=(0.22, 0.17, 0.12), dark=(0.10, 0.08, 0.06), light=(0.32, 0.26, 0.19), scale=1.0, rough=(0.7, 0.9))
M_WICKER = noisy("M_Wicker", [(0.40, 0.30, 0.16), (0.52, 0.40, 0.22)], scale=40, rough=0.75, bump=0.8, bump_dist=0.003, stretch=(1, 1, 8))
M_CHINA = plain("M_China", (0.82, 0.82, 0.80), rough=0.15, coat=0.6)
M_CHINABLUE = plain("M_ChinaBlue", (0.15, 0.22, 0.50), rough=0.15, coat=0.6)
M_CLOTH = noisy("M_TableCloth", [(0.80, 0.79, 0.74), (0.86, 0.85, 0.80)], scale=50, rough=0.85, bump=0.05)
M_CURTAIN = noisy("M_StudyCurtain", [(0.30, 0.25, 0.14), (0.38, 0.32, 0.18)], scale=20, rough=0.9, bump=0.1)
M_POT = noisy("M_ChimneyPot", [(0.38, 0.14, 0.07), (0.48, 0.20, 0.10)], scale=8, rough=0.8, bump=0.3)
M_HEDGE = noisy("M_HedgeMass", [(0.02, 0.05, 0.015), (0.04, 0.08, 0.025), (0.06, 0.10, 0.03)], scale=6, rough=0.85, bump=0.7, bump_dist=0.04)
M_FARTREES = noisy("M_FarTrees", [(0.02, 0.025, 0.015), (0.035, 0.04, 0.025)], scale=0.6, rough=0.9, bump=0.0)
M_FIRE = plain("M_TreeFire", (0.1, 0.03, 0.01), rough=1.0, emission=(0.85, 0.11, 0.015), strength=1.0)
M_SMOKE = noisy("M_Smoke", [(0.08, 0.06, 0.05), (0.14, 0.10, 0.08), (0.22, 0.14, 0.10)], scale=0.08, rough=1.0, bump=0.0)
M_FARSTONE = noisy("M_FarStone", [(0.12, 0.10, 0.09), (0.18, 0.15, 0.13)], scale=0.3, rough=0.9, bump=0.0)

def smoke_sky_mat(name="M_SkyDome"):
    """a hot, hazy evening fouled by the smoke from the common: yellow-brown haze, a red sun disc low in the west,
    smoke banks rolling up from the north-north-east (ahead), dull orange from beneath."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0)); nv = node(nt, "ShaderNodeVectorMath", (-2200, 0), operation='NORMALIZE'); nt.links.new(co, nv.inputs[0]); d = nv.outputs[0]
    s = sep_xyz(nt, d, (-2000, 0)); el = s.outputs["Z"]
    base = ramp(nt, [(0.0, c4((0.42, 0.24, 0.12))), (0.1, c4((0.46, 0.32, 0.18))), (0.35, c4((0.30, 0.26, 0.22))), (1.0, c4((0.16, 0.18, 0.24)))], (-1500, 400))
    nt.links.new(maprange(nt, el, 0.0, 1.0, 0, 1, (-1700, 400)), base.inputs["Fac"])
    sd = node(nt, "ShaderNodeVectorMath", (-1700, 800), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(SUN_DIR); nt.links.new(d, sd.inputs[0])
    glow = math_(nt, 'POWER', maprange(nt, sd.outputs["Value"], 0.75, 1.0, 0, 1, (-1500, 800)), 3.0, (-1350, 800))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', glow, 0.6, (-1200, 850)), base.outputs["Color"], (0.9, 0.35, 0.10, 1), (-1000, 400))
    disc = maprange(nt, sd.outputs["Value"], 0.99955, 0.99975, 0, 1, (-1500, 1000))
    col = mix_rgb(nt, 'MIX', disc, col, (1.6, 0.35, 0.10, 1), (-800, 500))
    # smoke: big rolling masses, thickest ahead (north-north-east), lit orange low down
    sm = noise_(nt, node(nt, "ShaderNodeVectorMath", (-1900, -300), operation='SCALE').outputs[0], 1.0, 6, 0.6, 0.5, (-1500, -300))
    vs = sm.inputs["Vector"].links[0].from_node; nt.links.new(d, vs.inputs[0]); vs.inputs["Scale"].default_value = 2.5
    dirn = node(nt, "ShaderNodeVectorMath", (-1700, -500), operation='DOT_PRODUCT'); dirn.inputs[1].default_value = (0.12, 0.99, 0.0); nt.links.new(d, dirn.inputs[0])
    where = math_(nt, 'MULTIPLY', maprange(nt, dirn.outputs["Value"], 0.2, 0.9, 0.15, 1.0, (-1500, -500)), maprange(nt, el, 0.45, 0.0, 0.2, 1.0, (-1500, -650)), (-1300, -550))
    cov = math_(nt, 'MULTIPLY', maprange(nt, sm.outputs["Fac"], 0.28, 0.58, 0.0, 1.0, (-1300, -300)), where, (-1150, -400))
    scol = mix_rgb(nt, 'MIX', maprange(nt, el, 0.0, 0.25, 1.0, 0.0, (-1100, -700)), c4((0.12, 0.10, 0.10)), c4((0.40, 0.14, 0.05)), (-950, -650))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', cov, 0.9, (-900, -400)), col, scol, (-600, 300))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1); b.inputs["Emission Strength"].default_value = 1.0
    return m
M_SKY = smoke_sky_mat()

# ----------------------------------------------------------------------------- the lawn and the garden ground
print("terrain ...", flush=True)
verts = []; uvs = []; XS = [-NEAR + i * 1.0 for i in range(int(2 * NEAR) + 1)]; YS = [-14.0 + i * 1.0 for i in range(int(NEAR + 14) + 1)]
for yy in YS:
    for xx in XS: verts.append((xx, yy, gz(xx, yy))); uvs.append(((xx - XS[0]) / (XS[-1] - XS[0]), (yy - YS[0]) / (YS[-1] - YS[0])))
nx = len(XS) - 1
faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(len(YS) - 1) for i in range(nx)]
mesh_from("GroundNear", verts, faces, M_LAWN, smooth=True, uvs=uvs)

# ----------------------------------------------------------------------------- the villa's back (right): brick, tiled roof, chimney stacks, the study window
print("house ...", flush=True)
HZ = gz(HOUSE_X, 2.0)
box("HouseWall", (0.4, 14.0, 7.0), (HOUSE_X + 0.2, 1.0, HZ + 3.5), M_BRICK)
box("HousePlinth", (0.5, 14.0, 0.4), (HOUSE_X + 0.2, 1.0, HZ + 0.2), plain("M_Plinth", (0.10, 0.08, 0.07), rough=0.8))
roof = mesh_from("HouseRoof", [(HOUSE_X - 0.3, -6.2, HZ + 7.0), (HOUSE_X - 0.3, 8.2, HZ + 7.0), (HOUSE_X + 4.5, 8.2, HZ + 10.4), (HOUSE_X + 4.5, -6.2, HZ + 10.4)],
                 [(0, 1, 2, 3)], M_TILE, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
box("Gutter", (0.12, 14.4, 0.1), (HOUSE_X - 0.3, 1.0, HZ + 6.95), M_WHITE)
# the chimney stacks on the ridge; the near one cracked, a pot gone
for k, (yy, intact) in enumerate(((-3.5, True), (4.6, False))):
    box(f"Stack{k}", (0.9, 1.4, 2.2 if intact else 1.7), (HOUSE_X + 4.2, yy, HZ + 11.2 if intact else HZ + 10.95), M_BRICK)
    box(f"StackCap{k}", (1.0, 1.5, 0.15), (HOUSE_X + 4.2, yy, HZ + 12.35 if intact else HZ + 11.85), M_BRICK) if intact else None
    if intact:
        for j in range(2): lathe(f"Pot{k}{j}", [(0, 0), (0.16, 0), (0.13, 0.5), (0.15, 0.55), (0.0, 0.55)], (HOUSE_X + 4.2, yy - 0.35 + j * 0.7, HZ + 12.42), M_POT, steps=10)
    else:
        for j in range(5): box(f"Broken{j}", (0.25, 0.3, 0.2), (HOUSE_X + 4.2 + rng.uniform(-0.3, 0.3), yy + rng.uniform(-0.5, 0.5), HZ + 11.85 + rng.uniform(0, 0.15)), M_BRICK, rot=(rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), rng.uniform(0, 3)))
        lathe("PotStump", [(0, 0), (0.16, 0), (0.15, 0.18), (0.0, 0.18)], (HOUSE_X + 4.2, yy + 0.3, HZ + 11.8), M_POT, steps=10)
# windows: the study window (ground floor, by the flower bed), a door, upper windows; white sashes, a curtain stirring
def window(nm, yc, zc, w, h, curtain=False):
    box(f"{nm}_Glass", (0.05, w, h), (HOUSE_X - 0.02, yc, zc), M_GLASS)
    for (dy, dz, sw, sh) in ((0, h / 2 + 0.04, w + 0.12, 0.08), (0, -h / 2 - 0.05, w + 0.2, 0.1), (-w / 2 - 0.04, 0, 0.08, h), (w / 2 + 0.04, 0, 0.08, h), (0, 0, w, 0.05)):
        box(f"{nm}_Frame{dy}{dz}", (0.1, sw, sh), (HOUSE_X - 0.04, yc + dy, zc + dz), M_WHITE)
    box(f"{nm}_Arch", (0.1, w + 0.3, 0.2), (HOUSE_X - 0.02, yc, zc + h / 2 + 0.18), M_BRICK)
    if curtain:
        cv = []; cf = []; cw = []
        for j in range(6):
            t = j / 5
            for i in range(9):
                u = i / 8; cv.append((HOUSE_X + 0.15 - 0.03 * math.sin(u * 14), yc - w / 2 + 0.05 + u * w * 0.4, zc + h / 2 - 0.05 - t * (h - 0.1)))
        for j in range(5):
            for i in range(8): cf.append((j * 9 + i, j * 9 + i + 1, (j + 1) * 9 + i + 1, (j + 1) * 9 + i))
        o = mesh_from("cloth.curtain.study", cv, cf, M_CURTAIN, smooth=True); K.add_sway(o, lambda p: max(0.0, min(1.0, (zc + h / 2 - p.z) / h)))
window("Study", 4.4, HZ + 1.6, 1.3, 1.9, curtain=True)
window("Dining", -2.2, HZ + 1.6, 1.3, 1.9)
for k, yy in enumerate((-2.2, 1.2, 4.4)): window(f"Upper{k}", yy, HZ + 4.9, 1.1, 1.6)
box("BackDoor", (0.08, 1.0, 2.2), (HOUSE_X - 0.03, 1.2, HZ + 1.1), wood("M_DoorPaint", base=(0.08, 0.14, 0.10), dark=(0.04, 0.07, 0.05), light=(0.12, 0.18, 0.14), scale=1.0, rough=(0.4, 0.55)))
box("DoorStep", (0.6, 1.3, 0.15), (HOUSE_X - 0.3, 1.2, HZ + 0.07), M_FARSTONE)
# the flower bed under the study window: edging tiles, flowers, and the heap of broken red fragments
for k in range(24): box(f"Edging{k}", (0.03, 0.2, 0.16), (HOUSE_X - 1.5, 2.2 + k * 0.2, gz(HOUSE_X - 1.5, 2.2 + k * 0.2) + 0.05), M_POT, rot=(0, 0, 0.05 * math.sin(k)))
FR = MB(); rf = random.Random(6)
for i in range(40):
    c_ = Vector((HOUSE_X - 0.7 + rf.gauss(0, 0.25), 4.6 + rf.gauss(0, 0.4), 0)); c_.z = gz(c_.x, c_.y) + 0.04 + rf.uniform(0, 0.12)
    s_ = rf.uniform(0.05, 0.14); B.blob(FR, c_, (s_ * 1.4, s_, s_ * 0.6), 60 + i, sub=1, rough=0.35)
FR.build("ChimneyRubble", M_BRICK, sway=False)
for k in range(3): lathe(f"PotShard{k}", [(0.0, 0), (0.15, 0), (0.13, 0.25), (0.0, 0.25)], (HOUSE_X - 0.9 + k * 0.25, 4.2 + k * 0.35, gz(HOUSE_X - 0.9, 4.2) + 0.08), M_POT, steps=8).rotation_euler = (1.3, 0.2 * k, 0.8 * k)

# ----------------------------------------------------------------------------- the summerhouse (behind-left), tea laid on the wicker table
print("summerhouse ...", flush=True)
SH = Vector((-3.6, -1.6)); SZ = gz(SH.x, SH.y)
F = K.Frame((SH.x, SH.y), math.radians(-70), z=SZ)        # its open front faces the reader's left-front (east-north-east)
F.box("SH_Floor", (2.8, 2.4, 0.12), (0, 0, 0.06), M_PALING)
for sx in (-1, 1):
    F.box(f"SH_Side{sx}", (0.08, 2.4, 1.0), (sx * 1.36, 0, 0.62), M_WHITE)
    for sy in (-1, 1): F.box(f"SH_Post{sx}{sy}", (0.1, 0.1, 2.3), (sx * 1.36, sy * 1.16, 1.27), M_WHITE)
F.box("SH_Back", (2.8, 0.08, 2.2), (0, -1.16, 1.22), M_WHITE)
F.box("SH_FrontRail", (2.8, 0.08, 0.1), (0, 1.16, 2.25), M_WHITE)
for k in range(9): F.box(f"SH_Lattice{k}", (0.03, 0.02, 1.2), (-1.36 + 0.0, -1.0 + k * 0.25, 1.7), M_WHITE) if False else None
for sx in (-1, 1):
    for k in range(6): F.box(f"SH_Slat{sx}{k}", (0.02, 2.3, 0.06), (sx * 1.38, 0, 1.25 + k * 0.17), M_WHITE)
roof_v = [F.p(-1.6, -1.4, 2.35), F.p(1.6, -1.4, 2.35), F.p(1.6, 1.45, 2.35), F.p(-1.6, 1.45, 2.35), F.p(0, 0, 3.2)]
mesh_from("SH_Roof", roof_v, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], M_TILE)
# wicker table and chairs, the tea things
TC = Vector(F.p(0.0, 0.1, 0.0))
lathe("TeaTable", [(0.0, 0.0), (0.3, 0.0), (0.32, 0.05), (0.1, 0.15), (0.08, 0.6), (0.42, 0.68), (0.42, 0.72), (0.0, 0.72)], (TC.x, TC.y, SZ + 0.12), M_WICKER, steps=20)
lathe("TeaCloth", [(0.0, 0.72), (0.46, 0.72), (0.47, 0.6), (0.46, 0.725), (0.0, 0.73)], (TC.x, TC.y, SZ + 0.12), M_CLOTH, steps=24)
TZ = SZ + 0.12 + 0.735
lathe("Teapot", [(0, 0), (0.06, 0), (0.09, 0.05), (0.085, 0.11), (0.05, 0.14), (0.02, 0.16), (0.025, 0.17), (0, 0.17)], (TC.x + 0.05, TC.y - 0.1, TZ), M_CHINA, steps=16)
cyl("TeapotSpout", 0.012, 0.11, (TC.x + 0.14, TC.y - 0.1, TZ + 0.08), M_CHINA, verts=6, rot=(0, 0.9, 0))
for k, a in enumerate((0.3, 2.4, 4.2)):
    cp = Vector((TC.x + 0.26 * math.cos(a), TC.y + 0.26 * math.sin(a), TZ))
    lathe(f"Saucer{k}", [(0, 0), (0.07, 0), (0.075, 0.01), (0, 0.008)], tuple(cp), M_CHINABLUE, steps=16)
    lathe(f"Cup{k}", [(0, 0.008), (0.03, 0.008), (0.045, 0.05), (0.047, 0.065), (0, 0.02)], tuple(cp), M_CHINA, steps=14)
lathe("CakePlate", [(0, 0), (0.12, 0), (0.13, 0.015), (0, 0.01)], (TC.x - 0.15, TC.y + 0.12, TZ), M_CHINABLUE, steps=16)
box("Cake", (0.12, 0.08, 0.06), (TC.x - 0.15, TC.y + 0.12, TZ + 0.04), noisy("M_Cake", [(0.45, 0.30, 0.12), (0.55, 0.38, 0.16)], scale=20, rough=0.8, bump=0.2))
def wicker_chair(nm, c, yaw):
    Fc = K.Frame((c.x, c.y), yaw, z=SZ + 0.12)
    Fc.box(f"{nm}Seat", (0.48, 0.46, 0.06), (0, 0, 0.44), M_WICKER, bevel=0.02)
    lathe(f"{nm}Base", [(0.0, 0.0), (0.24, 0.0), (0.2, 0.42), (0.0, 0.42)], Fc.p(0, 0, 0), M_WICKER, steps=12)
    Fc.box(f"{nm}Back", (0.52, 0.06, 0.55), (0, -0.24, 0.75), M_WICKER, bevel=0.03, rx=-0.15)
    for sx in (-1, 1): Fc.box(f"{nm}Arm{sx}", (0.06, 0.44, 0.22), (sx * 0.25, 0, 0.58), M_WICKER, bevel=0.02)
wicker_chair("ChairA", Vector(F.p(-0.65, 0.35, 0)), math.radians(-70) - 1.2)
wicker_chair("ChairB", Vector(F.p(0.75, 0.55, 0)), math.radians(-70) + 1.9)   # pushed back as he started out upon the lawn

# ----------------------------------------------------------------------------- the paling fence, side gate, the neighbour's strawberries; garden trees
for k in range(int(30 / 0.15)):
    x = -14.0 + k * 0.15
    if -8.6 < x < -7.6: continue                 # the side gate opening
    if x > HOUSE_X: break
    hgt = 1.5 + 0.03 * math.sin(k * 1.7)
    box(f"Paling{k}", (0.08, 0.025, hgt), (x, FENCE_Y, gz(x, FENCE_Y) + hgt / 2), M_PALING, rot=(0, rng.uniform(-0.02, 0.02), 0))
for k, z in enumerate((0.35, 1.2)): box(f"Rail{k}", (21.5, 0.06, 0.09), (-3.3, FENCE_Y + 0.05, gz(0, FENCE_Y) + z), M_PALING)
for k in range(8): box(f"FencePost{k}", (0.1, 0.1, 1.6), (-14.0 + k * 3.0, FENCE_Y + 0.08, gz(0, FENCE_Y) + 0.8), M_PALING)
gh = Vector((-8.55, FENCE_Y, 0.0)); ga = math.radians(-55)
for k in range(7): box(f"GatePale{k}", (0.08, 0.025, 1.4), tuple(gh + Vector((math.cos(ga), math.sin(ga), 0)) * (0.07 + k * 0.14) + Vector((0, 0, gz(gh.x, gh.y) + 0.72))), M_PALING, rot=(0, 0, ga))
for k, z in enumerate((0.3, 1.1)): box(f"GateRail{k}", (0.95, 0.04, 0.08), tuple(gh + Vector((math.cos(ga), math.sin(ga), 0)) * 0.48 + Vector((0, 0, z))), M_PALING, rot=(0, 0, ga))
# hedges along the sides, garden trees; strawberries beyond the fence (cards in rows)
HM = MB()
for k in range(14):
    B.blob(HM, (-13.5 + rng.gauss(0, 0.2), -12 + k * 1.5, 1.0), (0.9, 1.0, 1.3), 300 + k, sub=2, rough=0.2)
HM.build("HedgeWest", M_HEDGE, sway=False)
TREES = [tree("AppleA", -8.0, 3.5, 6.5, 3.4, "oak", 401, M_BARK, M_TREE_L, nlimbs=5, cards_per_tip=1, card_size=1.3, fill=100),
         tree("LimeB", -11.5, -6.0, 12.0, 4.5, "elm", 402, M_BARK, M_TREE_L, nlimbs=5, detail=0.7, cards_per_tip=0, card_size=2.4, fill=70),
         tree("PearC", 3.5, 12.5, 9.0, 3.0, "elm", 403, M_BARK, M_TREE_L, nlimbs=5, detail=0.6, cards_per_tip=0, card_size=2.2, fill=60),
         tree("BeechD", -6.0, 16.0, 14.0, 6.0, "ash", 404, M_BARK, M_TREE_L, nlimbs=5, detail=0.6, cards_per_tip=0, card_size=3.0, fill=60),
         tree("ElmE", -22.0, 28.0, 15.0, 5.0, "elm", 405, M_BARK, M_TREE_L, nlimbs=5, detail=0.5, cards_per_tip=0, card_size=3.6, fill=45),
         tree("OakF", 22.0, 34.0, 13.0, 6.5, "oak", 406, M_BARK, M_TREE_L, nlimbs=5, detail=0.5, cards_per_tip=0, card_size=3.6, fill=45)]
mb = MB(); R = random.Random(5)
def lawn_ok(x, y):
    if y > FENCE_Y - 0.2 or x > HOUSE_X - 1.6 or x < -13.0: return 0.0
    if (Vector((x, y)) - SH).length < 2.2: return 0.0
    if math.hypot(x, y) < 0.6: return 0.0
    return 0.7
B.scatter_cards(mb, None, R, 0, 0.3, 5.0, lambda x, y: lawn_ok(x, y) * 0.5, B.MEADOW_SHORT, height=0.05, width=0.22, solid_from=99, maxcards=500)
fb = MB()
for i in range(240):            # the flower bed under the study window
    x = HOUSE_X - R.uniform(0.25, 1.4); y = R.uniform(2.3, 6.8)
    if abs(x - (HOUSE_X - 0.7)) < 0.4 and abs(y - 4.6) < 0.5 and R.random() < 0.8: continue
    to_r = Vector((-x, -y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + R.gauss(0, 0.5)
    card(fb, (x, y, gz(x, y) - 0.02), Vector((math.cos(ya), math.sin(ya), 0)) * 0.42, Vector((0, 0, 0.55)), R.choice(B.MEADOW_FLOWER), 0.0, 1.0)
sb = MB()
for row in range(5):            # the neighbour's strawberry beds beyond the fence
    for i in range(40):
        x = -11.0 + i * 0.45 + R.gauss(0, 0.08); y = FENCE_Y + 1.0 + row * 1.4
        to_r = Vector((-x, -y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2
        card(sb, (x, y, gz(x, y) - 0.02), Vector((math.cos(ya), math.sin(ya), 0)) * 0.45, Vector((0, 0, 0.3)), R.choice(B.QUAD), 0.0, 1.0)
for o_, m_, nm in ((mb, M_LAWN_C, "LawnCards"), (fb, M_LAWN_C, "BedFlowers"), (sb, M_STRAW, "Strawberries")):
    oo = o_.build(nm, m_)
    if oo is not None: set_card_normals(oo, lambda p: Vector((0, 0, 1)))

# ----------------------------------------------------------------------------- the view beyond: trees about the Oriental College in smoky red flame, the mosque, the church tower
print("distance ...", flush=True)
def far_belt(nm, y, x0, x1, h0, h1, mat, seed, burning=None):
    vs = []; fs = []; n = 80
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        hh = h0 + (h1 - h0) * (0.5 + 0.5 * noise.noise(Vector((x * 0.02, seed, 0.0)))) + 3.0 * noise.noise(Vector((x * 0.12, seed, 1.0)))
        vs.append((x, y, -3.0)); vs.append((x, y + 2, hh))
    for i in range(n): fs.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    return mesh_from(nm, vs, fs, mat, smooth=True)
far_belt("FarTreesNear", 120.0, -300, 300, 2, 6, M_FARTREES, 1.0)
far_belt("FarTreesCollege", COLLEGE.y, COLLEGE.x - 160, COLLEGE.x + 160, 14, 24, M_FARTREES, 2.0)
# the burning treetops: emissive flame masses along the college belt's crest, and smoke columns rising off them
FI = MB(); SMK = MB(); rf2 = random.Random(9)
for i in range(22):
    x = COLLEGE.x - 90 + i * 8.5 + rf2.gauss(0, 2.5)
    B.blob(FI, (x, COLLEGE.y - 1.0, 17 + rf2.uniform(-4, 5)), (rf2.uniform(3, 7), 1.5, rf2.uniform(2, 8)), 500 + i, sub=2, rough=0.55)
for i in range(0):
    x = COLLEGE.x - 80 + i * 20 + rf2.gauss(0, 5)
    for j in range(5):
        B.blob(SMK, (x + j * j * 2.0 - 10 * (j > 2), COLLEGE.y + 5 + j * 6, 30 + j * 22), (10 + j * 6, 8 + j * 4, 12 + j * 5), 600 + i * 10 + j, sub=1, rough=0.35)
FI.build("far.fire", M_FIRE, sway=False)
# the mosque's dome (its pinnacle gone) and the college roof-line, the church tower's broken stump
MQ = Vector((COLLEGE.x + 55, COLLEGE.y + 10))
lathe("far.mosqueDome", [(0.0, 0.0), (9.0, 0.0), (9.0, 6.0), (8.5, 10.0), (6.0, 14.0), (2.0, 16.5), (0.0, 17.0)], (MQ.x, MQ.y, 12.0), M_FARSTONE, steps=20)
box("far.mosqueDrum", (16.0, 16.0, 12.0), (MQ.x, MQ.y, 6.0), M_FARSTONE)
box("far.collegeRoof", (60.0, 15.0, 18.0), (COLLEGE.x - 20, COLLEGE.y + 30, 9.0), M_FARSTONE, rot=(0, 0.03, 0))
box("far.churchStump", (7.0, 7.0, 16.0), (COLLEGE.x - 70, COLLEGE.y + 12, 8.0), M_FARSTONE, rot=(0, 0.08, 0.2))

# ----------------------------------------------------------------------------- sky, light, anchors
B.sky_dome("SkyDome", M_SKY, 900.0, el_min=-4.0)
light_obj("light.sun", 'SUN', 2.6, (1.0, 0.42, 0.18), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(6.0))
sl = light_obj("light.sky", 'SUN', 0.45, (0.70, 0.50, 0.35), (0, 0, 40), direction=(0.05, 0.1, -1.0), angle=math.radians(120)); sl.data.use_shadow = False
B.world_sky(zen=(0.18, 0.18, 0.22), hor=(0.48, 0.30, 0.18), ground=(0.06, 0.05, 0.03), strength=0.8)
vol = scene.world.node_tree.nodes.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.003; vol.inputs["Color"].default_value = (0.75, 0.55, 0.40, 1)
pass   # no world volume: an infinite haze in Cycles swallows the sun (Unity has its own fog)
E = Vector((0.0, 0.0, gz(0, 0) + EYE_H))
fwd = Vector((0.12, 1.0, 0)).normalized()
B.reader_anchors((0.0, 0.0, gz(0, 0)), tuple(E + fwd))
anchor("scene.centre", tuple(Vector((0, 0, 0)) + fwd * 40)); anchor("maybury.summerhouse", (SH.x, SH.y, SZ))
anchor("maybury.flowerbed", (HOUSE_X - 0.7, 4.6, gz(HOUSE_X - 0.7, 4.6))); anchor("maybury.college", (COLLEGE.x, COLLEGE.y, 20.0))
sound("birds", "garden", (-8.0, 3.5, 4.0)); sound("fire", "college", (COLLEGE.x * 0.15, 60.0, 8.0)); sound("wind-trees", "garden", (-11.5, -6.0, 8.0))
page = B.page_preview(E, fwd)
K.apply_transforms()
cams = B.view_cams(E, fwd, extra=[("Cam_Summerhouse", E + Vector((1.5, 1.0, -0.1)), (SH.x, SH.y, SZ + 1.0), 24),
                                  ("Cam_Bed", E + Vector((2.0, 0.5, 0.0)), (HOUSE_X - 0.7, 4.6, gz(HOUSE_X - 0.7, 4.6) + 0.3), 26),
                                  ("Cam_College", tuple(E), (COLLEGE.x, COLLEGE.y, 20.0), 45)])
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "maybury_garden_source.blend"))
K.print_budget()
if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.6, captures_dir=ARGS.captures)
if ARGS.bake or ARGS.export:
    scene.world.node_tree.nodes.remove(vol)
    B.export_room("maybury_garden.gltf", cams, page=page,
                  keep_names={"M_LawnCards": "veg.grass.lawn", "M_GardenSprays": "veg.crown.garden", "M_StrawberrySprays": "veg.crop.strawberries",
                              "M_StudyCurtain": "cloth.curtain.study", "M_SkyDome": "SkyDome", "M_Lawn": "GroundNear", "M_FarTrees": "far.trees",
                              "M_TreeFire": "far.fire", "M_Smoke": "far.smoke", "M_FarStone": "far.college"},
                  keep_uv={"M_Lawn", "M_SkyDome"}, unlit_emit=("M_TreeFire",),
                  size_for={"M_Lawn": (2048, 256, 1024), "M_SkyDome": (2048,), "M_RedBrick": (2048, 256, 1024), "M_RoofTiles": (1024, 128, 512),
                            "M_WhitePaint": (512, 64, 256), "M_Palings": (1024, 128, 512), "M_Wicker": (512, 64, 512), "M_GardenBark": (512, 64, 256),
                            "M_HedgeMass": (512, 64, 256), "M_FarTrees": (256, 32, 64), "M_Smoke": (256, 32, 64), "M_FarStone": (256, 32, 64)},
                  default_size=(128, 64, 128))
print("DONE")
