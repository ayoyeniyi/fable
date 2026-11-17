"""
Fable: the Tin Woodman's clearing in the forest (The Wonderful Wizard of Oz, chapter 5, "The Rescue of the Tin
Woodman").

"When Dorothy awoke the sun was shining through the trees ..." "They left the cottage and walked through the trees
until they found a little spring of clear water ..." "Dorothy discovered something shining in a ray of sunshine that
fell between the trees ... One of the big trees had been partly chopped through, and standing beside it, with an
uplifted axe in his hands, was a man made entirely of tin. His head and arms and legs were jointed upon his body, but
he stood perfectly motionless, as if he could not stir at all." "You will find an oilcan on a shelf in my cottage."

The reader stands at the edge of a small clearing in deep old forest, by a little spring of clear water among mossy
stones, in the morning. Ahead, one of the big trees has been partly chopped through, a deep pale notch in its trunk
and fresh chips scattered round its foot; beside it the Tin Woodman stands motionless with his axe raised over his
shoulder, rusted at the joints, a ray of sunshine falling between the trees onto him so that he shines. To the left,
the little cottage built of logs and branches, its door open (a bed of dried leaves inside, the oilcan on a shelf by
the door). Huge rough-barked trees close round; leaf litter, ferns and moss on the floor. No Lion, no Kalidahs, no
poppies; the Woodman has no heart yet.

The Tin Woodman is the one figure, made as he is in the book: tin cylinders, cones and a funnel hat, jointed and
riveted. Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py.

Node names the runtime relies on:
  anchor.reader.entrance (feet by the spring, facing +Y: the chopped tree and the Woodman), anchor.reader.look,
  anchor.scene.centre (the Woodman), anchor.clearing.oilcan
  light.sun (SUN, morning, through a gap in the canopy), light.sky (SUN, green-filtered sky fill)
  water.pond.spring, veg.crown.forest, veg.shrub.fern, veg.grass.floor
  sound.birds.0, sound.birds.1, sound.wind-trees.0
  SkyDome (only seen through the canopy)

Run headless:
  blender -b -P blender/build_woodman_forest_clearing.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_woodman_forest_clearing.py -- --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b1 as S
from scene_kit_b1 import (K, E8, new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound, light_obj, camera,
                          link, smoothstep, lerp, n2, fbm2, orient, card, plant, set_card_normals, az_dir, TWO_PI)

ARGS = S.setup("woodman-forest-clearing", 1900, "WoodmanClearing", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
SUN_AZ, SUN_EL = 115.0, 38.0
SUN_DIR = (az_dir(SUN_AZ) * math.cos(math.radians(SUN_EL)) + Vector((0, 0, math.sin(math.radians(SUN_EL))))).normalized()
TREE_C = Vector((1.3, 7.2, 0)); TREE_R = 0.62
TIN = Vector((-0.35, 6.3, 0))
SPRING = Vector((-1.5, 0.9, 0))
COTTAGE = Vector((-7.5, 8.0, 0))

def H(x, y):
    z = 0.25 * n2(x, y, 9.0, 3.0) + 0.08 * n2(x, y, 2.5, 6.0) + 0.02 * n2(x, y, 0.6, 9.0)
    z += 0.6 * smoothstep(10, 30, math.hypot(x, y - 5)) * n2(x, y, 15.0, 2.0)
    z -= 0.25 * smoothstep(0.9, 0.2, (Vector((x, y)) - SPRING.xy).length)      # the spring's hollow
    return z
Z0 = H(0, 0)
def gz(x, y): return H(x, y) - Z0
S.set_ground(gz)
def clear_fn(x, y): return smoothstep(7.5, 4.0, math.hypot(x - 0.0, y - 5.5))
def chips_fn(x, y): return smoothstep(2.0, 0.7, (Vector((x, y)) - TREE_C.xy).length)
def moss_fn(x, y): return smoothstep(1.4, 0.6, (Vector((x, y)) - SPRING.xy).length)

def floor_mat(name="M_ForestFloor"):
    """old-forest floor: brown leaf litter (oak and beech leaves as cells), twigs, moss in drifts; in the clearing
    short grass and moss with litter; pale fresh wood chips round the chopped tree; wet moss round the spring."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    ac = node(nt, "ShaderNodeAttribute", (-2000, 700)); ac.attribute_name = "clear"
    ah = node(nt, "ShaderNodeAttribute", (-2000, 550)); ah.attribute_name = "chips"
    am = node(nt, "ShaderNodeAttribute", (-2000, 400)); am.attribute_name = "moss"
    clr, chips, moss = ac.outputs["Fac"], ah.outputs["Fac"], am.outputs["Fac"]
    v1 = voronoi_(nt, co, 9.0, 'F1', (-1700, 200)); v2 = voronoi_(nt, co, 16.0, 'F1', (-1700, 0))
    l1 = node(nt, "ShaderNodeSeparateColor", (-1500, 200)); nt.links.new(v1.outputs["Color"], l1.inputs["Color"])
    l2 = node(nt, "ShaderNodeSeparateColor", (-1500, 0)); nt.links.new(v2.outputs["Color"], l2.inputs["Color"])
    leafy = ramp(nt, [(0.0, c4(K.srgb((0.20, 0.13, 0.07)))), (0.35, c4(K.srgb((0.32, 0.20, 0.10)))), (0.7, c4(K.srgb((0.44, 0.30, 0.15)))), (1.0, c4(K.srgb((0.26, 0.17, 0.09))))], (-1300, 200))
    nt.links.new(math_(nt, 'ADD', math_(nt, 'MULTIPLY', l1.outputs[0], 0.6, (-1400, 300)), math_(nt, 'MULTIPLY', l2.outputs[1], 0.4, (-1400, 100)), (-1350, 200)), leafy.inputs["Fac"])
    edge = maprange(nt, math_(nt, 'MINIMUM', v1.outputs["Distance"], math_(nt, 'MULTIPLY', v2.outputs["Distance"], 1.4, (-1400, -50)), (-1300, 0)), 0.0, 0.15, 0.6, 1.0, (-1200, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, leafy.outputs["Color"], edge, (-1100, 200))
    n = noise_(nt, co, 0.5, 4, 0.6, loc=(-1700, -300))
    mosscol = mix_rgb(nt, 'MIX', maprange(nt, noise_(nt, co, 12.0, 4, 0.6, loc=(-1700, -500)).outputs["Fac"], 0.3, 0.7, 0, 1, (-1500, -500)),
                      c4(K.srgb((0.14, 0.22, 0.06))), c4(K.srgb((0.30, 0.38, 0.10))), (-1300, -500))
    mk = math_(nt, 'MAXIMUM', maprange(nt, n.outputs["Fac"], 0.55, 0.65, 0, 0.8, (-1500, -300)), math_(nt, 'MAXIMUM', moss, math_(nt, 'MULTIPLY', clr, 0.55, (-1500, -700)), (-1400, -650)), (-1300, -350))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', mk, maprange(nt, l1.outputs[2], 0.0, 1.0, 0.6, 1.0, (-1300, -800)), (-1150, -500)), col, mosscol, (-900, 200))
    chipc = mix_rgb(nt, 'MIX', l2.outputs[2], c4(K.srgb((0.70, 0.58, 0.40))), c4(K.srgb((0.82, 0.70, 0.50))), (-1100, -1000))
    chipk = math_(nt, 'MULTIPLY', chips, maprange(nt, l2.outputs[0], 0.35, 0.4, 0, 1, (-1200, -1100)), (-1000, -1050))
    col = mix_rgb(nt, 'MIX', chipk, col, chipc, (-700, 200))
    col = K.ao_mul(nt, col, 0.3, 0.4, (-500, -900))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    b.inputs["Specular IOR Level"].default_value = 0.25
    bump_from(nt, b, math_(nt, 'ADD', edge, chipk, (-600, -1300)), 0.4, 0.008)
    return m

def tin_mat(name="M_Tin"):
    """tinplate: bright, a little dented and smeared (roughness patches), with rust: orange-brown blooms creeping out
    from the joints and seams (by object position: the joints are rings at known heights), streaks running down."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    at = node(nt, "ShaderNodeAttribute", (-1600, 500)); at.attribute_name = "rust"
    n = noise_(nt, co, 14.0, 6, 0.7, loc=(-1400, 200))
    n2_ = noise_(nt, co, 3.0, 4, 0.6, loc=(-1400, 0))
    rust = math_(nt, 'MULTIPLY', at.outputs["Fac"], maprange(nt, n.outputs["Fac"], 0.35, 0.6, 0.2, 1.0, (-1200, 200)), (-1000, 300))
    rustc = mix_rgb(nt, 'MIX', n2_.outputs["Fac"], c4(K.srgb((0.42, 0.20, 0.08))), c4(K.srgb((0.58, 0.32, 0.12))), (-900, 0))
    tinc = mix_rgb(nt, 'MIX', maprange(nt, n2_.outputs["Fac"], 0.3, 0.7, 0, 1, (-1100, -200)), c4((0.62, 0.64, 0.66)), c4((0.78, 0.80, 0.82)), (-900, -200))
    col = mix_rgb(nt, 'MIX', rust, tinc, rustc, (-600, 0))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, rust, 1.0, 0.0, (-600, -300)), b.inputs["Metallic"])
    nt.links.new(mix_f(nt, rust, maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.18, 0.4, (-900, -400)), 0.85, (-600, -400)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'ADD', rust, math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.3, (-700, -700)), (-550, -700)), 0.25, 0.004)
    return m

print("materials ...", flush=True)
M_FLOOR = floor_mat()
M_TIN = tin_mat()
M_BARK = S.bark_mat("M_OldBark", (0.24, 0.20, 0.16), (0.08, 0.07, 0.05), (0.34, 0.30, 0.24), scale=1.6, fissure=0.8, moss=0.35)
M_LOGS = S.bark_mat("M_CottageLogs", (0.26, 0.21, 0.15), (0.10, 0.08, 0.06), (0.36, 0.30, 0.22), scale=1.6, fissure=0.6, moss=0.25)
M_HEARTWOOD = K.noisy("M_Heartwood", [K.srgb((0.78, 0.64, 0.44)), K.srgb((0.70, 0.55, 0.36)), K.srgb((0.82, 0.70, 0.50))], scale=12, rough=0.8, bump=0.2, stretch=(1, 1, 6))
M_STONE = S.stone_mat("M_SpringStones", (0.36, 0.36, 0.33), (0.18, 0.18, 0.17), (0.48, 0.47, 0.43), scale=2.5, wet_z=gz(SPRING.x, SPRING.y) - 0.12, wet_k=0.6, moss=0.7, lichen=0.2, rough=0.8, bump=0.25)
M_WATER = S.water_mat("M_Spring", deep=(0.03, 0.05, 0.04), rough=0.02)
M_AXEHEAD = plain("M_AxeHead", (0.30, 0.30, 0.31), rough=0.35, metallic=1.0)
M_HANDLE = K.noisy("M_AxeHandle", [K.srgb((0.55, 0.42, 0.26)), K.srgb((0.45, 0.33, 0.20))], scale=20, rough=0.6, bump=0.05, stretch=(1, 1, 8))
M_THATCH = K.noisy("M_BranchRoof", [K.srgb((0.30, 0.24, 0.16)), K.srgb((0.20, 0.16, 0.11)), K.srgb((0.26, 0.30, 0.14))], scale=6, rough=0.95, bump=0.6, stretch=(1, 1, 0.3))
M_LEAFBED = K.noisy("M_LeafBed", [K.srgb((0.45, 0.30, 0.14)), K.srgb((0.36, 0.22, 0.10)), K.srgb((0.52, 0.38, 0.18))], scale=18, rough=0.9, bump=0.5)
M_DARK = plain("M_CottageDark", (0.02, 0.018, 0.015), rough=1.0)
M_FOREST = image_mat("M_ForestLeaves", S.spray_atlas("A_OakSprays", "oak", 71), rough=0.6, alpha=True)
M_CANOPYMASS = S.crown_mass_mat("M_CanopyMass", (0.04, 0.07, 0.02), (0.10, 0.17, 0.05), (0.18, 0.26, 0.08), scale=2.0)
IMG_PLANTS, CELLS = S.plant_atlas("A_FloorPlants", ["fern", "fern", "grass", "dock", "sedge", "tussock", "weed", "flowers"], seed=1901,
                                  greens=[(0.14, 0.22, 0.06), (0.18, 0.27, 0.07), (0.22, 0.30, 0.09), (0.12, 0.19, 0.05)])
M_FERN = image_mat("M_Ferns", IMG_PLANTS, rough=0.6, alpha=True)
M_FLOORGRASS = image_mat("M_FloorGrass", IMG_PLANTS, rough=0.6, alpha=True)
M_SKY = S.gradient_sky_mat("M_SkyDome", [(0.0, (0.70, 0.78, 0.80)), (0.3, (0.50, 0.66, 0.88)), (1.0, (0.30, 0.48, 0.80))], sun_dir=SUN_DIR, glow=((1.2, 1.1, 0.9), 40.0))

# ----------------------------------------------------------------------------- ground and the spring
print("ground ...", flush=True)
S.ground("Floor", M_FLOOR, 60.0, r0=2.0, NA=96, NR=30, attrs={"clear": clear_fn, "chips": chips_fn, "moss": moss_fn})
SPZ = gz(SPRING.x, SPRING.y) + 0.12
S.water_surface("Spring", M_WATER, SPZ, lambda x, y: (Vector((x, y)) - SPRING.xy).length < 0.8, extent=2.0, step=0.1, centre=(SPRING.x, SPRING.y))
R = random.Random(3)
specs = []
for k in range(14):
    a = TWO_PI * k / 14 + R.uniform(-0.2, 0.2); r = R.uniform(0.6, 0.9)
    specs.append((SPRING.x + math.cos(a) * r, SPRING.y + math.sin(a) * r, R.uniform(0.1, 0.24), 30 + k, {"sub": 2, "bury": 0.45, "facet": 0.1, "squash": (1.0, 0.8, 0.6)}))
for k in range(8):
    x, y = R.uniform(-12, 12), R.uniform(-6, 16)
    if math.hypot(x, y - 5) < 6: continue
    specs.append((x, y, R.uniform(0.3, 0.7), 60 + k, {"sub": 2, "bury": 0.5, "facet": 0.15, "squash": (1.0, 0.8, 0.55)}))
S.rocks("Stones", specs, M_STONE)

# ----------------------------------------------------------------------------- the big trees round the clearing, the canopy
print("trees ...", flush=True)
FR = random.Random(17)
BIG = [(-5.0, 12.5), (6.5, 11.0), (-9.5, 3.0), (8.0, 2.0), (-4.0, -5.5), (5.0, -6.0), (11.0, 8.5), (-11.0, 10.0), (0.0, 15.5), (13.0, -2.0), (-13.0, -3.0),
       (3.5, 19.0), (-7.0, 19.0), (10.0, 16.0), (-15.0, 16.0), (15.0, 13.0), (0.0, -11.0), (-9.0, -12.0), (9.0, -12.0)]
for k, (x, y) in enumerate(BIG):
    near = math.hypot(x, y - 4) < 13
    h = FR.uniform(22, 28); sp = FR.uniform(6.5, 8.5)
    S.tree(f"Big{k}", x, y, h, sp, "oak", 400 + k, M_BARK, "forest", nlimbs=6 if near else 5, detail=1.0 if near else 0.5,
           cards_per_tip=2, card_size=2.8, fill=70 if near else 45, roots=True)
for k in range(52):
    a = FR.uniform(0, TWO_PI); r = FR.uniform(18, 34); x, y = r * math.sin(a), 5 + r * math.cos(a)
    S.tree(f"Far{k}", x, y, FR.uniform(20, 26), FR.uniform(6, 8), "far", 500 + k, M_BARK, "forest", nlimbs=4, detail=0.3, cards_per_tip=0, card_size=6.5, fill=60, roots=False)
S.build_crowns({"forest": M_FOREST}, names={"forest": "CrownsForest"})

# the chopped tree: a big trunk with a deep notch on the Woodman's side, its pale wood showing, chips at the foot
trunk = lathe("ChoppedTrunk", [(0.0, -0.3), (TREE_R * 1.5, -0.3), (TREE_R * 1.15, 0.3), (TREE_R, 1.2), (TREE_R * 0.95, 4.0), (TREE_R * 0.85, 9.0), (TREE_R * 0.7, 14.0), (0.0, 14.0)],
              (TREE_C.x, TREE_C.y, gz(TREE_C.x, TREE_C.y) - 0.1), M_BARK, steps=20, jitter=0.06, seed=3)
NOTCH_Z = gz(TREE_C.x, TREE_C.y) + 0.85
cutter = box("NotchCutter", (1.2, 1.2, 1.2), (TREE_C.x - 0.33, TREE_C.y - 0.62, NOTCH_Z), M_HEARTWOOD)
cutter.rotation_euler = (math.radians(45), 0, math.radians(25))
bpy.context.view_layer.update()
bo = trunk.modifiers.new("Notch", 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.object = cutter; bo.solver = 'EXACT'; bo.use_self = False
bpy.context.view_layer.objects.active = trunk; trunk.select_set(True)
bpy.ops.object.modifier_apply(modifier="Notch"); trunk.select_set(False)
# the cut faces are new faces: give them the pale wood (material slot 1)
trunk.data.materials.append(M_HEARTWOOD)
bm = bmesh.new(); bm.from_mesh(trunk.data); bm.faces.ensure_lookup_table()
mw = trunk.matrix_world
for f in bm.faces:
    c = mw @ f.calc_center_median()
    lc = (cutter.matrix_world.inverted() @ c)
    if max(abs(lc.x), abs(lc.y), abs(lc.z)) < 0.62: f.material_index = 1
bm.to_mesh(trunk.data); bm.free()
bpy.data.objects.remove(cutter, do_unlink=True)
# split the heartwood faces into their own object (one material per object for the merge)
bpy.ops.object.select_all(action='DESELECT'); trunk.select_set(True); bpy.context.view_layer.objects.active = trunk
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.separate(type='MATERIAL'); bpy.ops.object.mode_set(mode='OBJECT')
for o in list(K.COLL.objects):
    if o.name.startswith("ChoppedTrunk") and o.data.materials and len(o.data.materials) > 1:
        keep = o.data.materials[o.data.polygons[0].material_index] if o.data.polygons else o.data.materials[0]
        o.data.materials.clear(); o.data.materials.append(keep)
        for p in o.data.polygons: p.material_index = 0
# the trunk's crown above (the tree is one of the forest giants)
S.tree("ChoppedCrown", TREE_C.x, TREE_C.y, 26.0, 8.0, "oak", 777, M_BARK, "forest", nlimbs=6, detail=0.6, cards_per_tip=1, card_size=2.6, fill=30, roots=False)
# chips at the foot
for k in range(70):
    a = R.uniform(0, TWO_PI); r = TREE_R + R.uniform(0.1, 1.6) ** 1.3
    x, y = TREE_C.x + math.cos(a) * r, TREE_C.y + math.sin(a) * r
    o = box(f"Chip{k}", (R.uniform(0.04, 0.11), R.uniform(0.02, 0.05), 0.012), (x, y, gz(x, y) + 0.01), M_HEARTWOOD)
    o.rotation_euler = (R.uniform(-0.3, 0.3), R.uniform(-0.3, 0.3), R.uniform(0, 3))

# ----------------------------------------------------------------------------- the Tin Woodman
print("tin woodman ...", flush=True)
TZ = gz(TIN.x, TIN.y)
TY = math.radians(-62)                 # he faces the tree (to his right of the reader's view), turned a little toward the reader
TM = Matrix.Translation((TIN.x, TIN.y, TZ)) @ Matrix.Rotation(TY, 4, 'Z')
TIN_PARTS = []
def T(p): return TM @ Vector(p)
def tin_lathe(nm, prof, at, rot=Matrix.Identity(3), steps=20):
    o = lathe(nm, prof, (0, 0, 0), M_TIN, steps=steps)
    o.matrix_world = Matrix.Translation(T(at)) @ (Matrix.Rotation(TY, 4, 'Z') @ rot.to_4x4())
    TIN_PARTS.append(o); return o
def limb(nm, p0, p1, r0, r1, steps=16):
    """a tin tube between two local points, with a rolled rim at each end (the joints)."""
    p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0; L = d.length
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix()
    tin_lathe(nm, [(0.0, 0.0), (r0 * 0.92, 0.0), (r0 * 1.08, 0.012), (r0 * 1.08, 0.03), (r0, 0.04), (r1, L - 0.04), (r1 * 1.08, L - 0.03), (r1 * 1.08, L - 0.012),
                   (r1 * 0.92, L), (0.0, L)], p0, rot, steps)
    return p1
# legs: tapering stovepipes with knee rings; boots like funnels
for sd in (-1, 1):
    hip = (sd * 0.12, 0.0, 0.92); knee = (sd * 0.13, 0.03, 0.50); ankle = (sd * 0.14, 0.0, 0.10)
    limb(f"Thigh{sd}", hip, knee, 0.075, 0.065)
    limb(f"Shin{sd}", knee, ankle, 0.065, 0.058)
    sphere(f"Knee{sd}", 0.07, tuple(T(knee)), M_TIN, seg=12); TIN_PARTS.append(K.COLL.objects[f"Knee{sd}"])
    tin_lathe(f"Boot{sd}", [(0.0, 0.0), (0.09, 0.0), (0.10, 0.02), (0.075, 0.11), (0.06, 0.12), (0.0, 0.12)], (ankle[0], ankle[1] + 0.05, -0.02),
              Matrix.Diagonal((1.0, 1.6, 1.0)))
# body: a tin barrel with a seam and rivets, a cone at the hips, a shoulder ring
tin_lathe("Body", [(0.0, 0.86), (0.14, 0.86), (0.19, 0.92), (0.21, 1.00), (0.215, 1.30), (0.21, 1.42), (0.19, 1.47), (0.12, 1.50), (0.0, 1.50)], (0, 0, 0))
tin_lathe("BodyBand", [(0.218, 1.15), (0.225, 1.155), (0.225, 1.175), (0.218, 1.18)], (0, 0, 0))
for k in range(10):
    a = TWO_PI * k / 10
    sphere(f"Rivet{k}", 0.012, tuple(T((math.cos(a) * 0.222, math.sin(a) * 0.222, 1.165))), M_TIN, seg=6)
tin_lathe("Neck", [(0.0, 1.49), (0.05, 1.49), (0.045, 1.58), (0.0, 1.58)], (0, 0, 0))
# head: a tin can with a funnel for a hat (point up), a cone nose, rivet eyes, a slot mouth
tin_lathe("Head", [(0.0, 1.57), (0.10, 1.57), (0.115, 1.59), (0.115, 1.78), (0.10, 1.80), (0.0, 1.80)], (0, 0, 0))
tin_lathe("Funnel", [(0.0, 1.79), (0.13, 1.79), (0.15, 1.81), (0.045, 1.93), (0.03, 2.02), (0.0, 2.02)], (0, 0, 0))
nose = cyl("Nose", 0.025, 0.08, tuple(T((0.0, 0.14, 1.70))), M_TIN, verts=10, r2=0.004)
nose.rotation_euler = Euler((math.radians(-90), 0, TY)); TIN_PARTS.append(nose)
for sd in (-1, 1):
    sphere(f"TinEye{sd}", 0.016, tuple(T((sd * 0.045, 0.11, 1.74))), M_DARK, seg=8)
box("TinMouth", (0.06, 0.01, 0.008), tuple(T((0.0, 0.112, 1.635))), M_DARK, rot=(0, 0, TY))
# arms raised: both hands up by the right shoulder gripping the axe, the axe head back over the shoulder
SH_R, SH_L = (0.25, 0.0, 1.42), (-0.25, 0.0, 1.42)
EL_R, EL_L = (0.36, 0.12, 1.66), (-0.08, 0.30, 1.62)
HAND_R, HAND_L = (0.30, 0.18, 1.98), (0.18, 0.24, 1.86)
limb("UpperArmR", SH_R, EL_R, 0.055, 0.05); limb("ForearmR", EL_R, HAND_R, 0.05, 0.045)
limb("UpperArmL", SH_L, EL_L, 0.055, 0.05); limb("ForearmL", EL_L, HAND_L, 0.05, 0.045)
for nm, p in (("ShoulderR", SH_R), ("ShoulderL", SH_L), ("ElbowR", EL_R), ("ElbowL", EL_L)):
    sphere(nm, 0.06, tuple(T(p)), M_TIN, seg=12)
for nm, p in (("HandR", HAND_R), ("HandL", HAND_L)):
    sphere(nm, 0.05, tuple(T(p)), M_TIN, seg=10, scale=(1.0, 1.0, 1.25))
# the axe: a long ash handle through both hands, the head behind and above the right shoulder
ax0 = Vector(T((0.16, 0.30, 1.78))); ax1 = Vector(T((0.30, -0.15, 2.55)))
tube("AxeHandle", [ax0 + (ax0 - ax1).normalized() * 0.12, ax0.lerp(ax1, 0.5) + Vector((0, 0, 0.02)), ax1], [0.022, 0.02, 0.024], M_HANDLE, sides=8)
hd = (ax1 - ax0).normalized()
side = hd.cross(Vector((0, 0, 1))).normalized(); bladedir = side.cross(hd).normalized()
blade = [ax1 - bladedir * 0.07 + hd * 0.06, ax1 - bladedir * 0.07 - hd * 0.08, ax1 + bladedir * 0.30 - hd * 0.16, ax1 + bladedir * 0.32 + hd * 0.14]
bm = bmesh.new()
vf = [bm.verts.new(p + side * 0.022) for p in blade]; vb = [bm.verts.new(p - side * 0.022 * (0.2 if i >= 2 else 1.0)) for i, p in enumerate(blade)]
bm.faces.new(vf); bm.faces.new(list(reversed(vb)))
for i in range(4):
    j = (i + 1) % 4; bm.faces.new((vf[i], vf[j], vb[j], vb[i]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("AxeHead"); bm.to_mesh(me); bm.free()
ao_ = bpy.data.objects.new("AxeHead", me); me.materials.append(M_AXEHEAD); link(ao_)
# rust weights on the tin: high near the joints (knees, hips, elbows, shoulders, neck)
JOINTS = [T(p) for p in ((0.12, 0, 0.92), (-0.12, 0, 0.92), (0.13, 0.03, 0.5), (-0.13, 0.03, 0.5), (0.14, 0, 0.1), (-0.14, 0, 0.1), SH_R, SH_L, EL_R, EL_L, (0, 0, 1.53), (0, 0, 1.16))]
K.apply_transforms()
for o in K.COLL.objects:
    if o.type == 'MESH' and o.data.materials and o.data.materials[0] == M_TIN:
        me = o.data; at = me.attributes.get("rust") or me.attributes.new("rust", 'FLOAT', 'POINT')
        vals = []
        for v in me.vertices:
            p = o.matrix_world @ v.co
            d = min((p - j).length for j in JOINTS)
            vals.append(max(0.15, smoothstep(0.16, 0.03, d)) if p.z - TZ > 0.2 else 0.5)
        at.data.foreach_set("value", vals)

# ----------------------------------------------------------------------------- the cottage of logs and branches
print("cottage ...", flush=True)
CY = math.radians(-35)                  # its door faces the clearing
CM = Matrix.Translation((COTTAGE.x, COTTAGE.y, gz(COTTAGE.x, COTTAGE.y) - 0.1)) @ Matrix.Rotation(CY, 4, 'Z')
def C(p): return CM @ Vector(p)
CW, CD, CH = 3.6, 3.2, 1.9
for k in range(9):                       # log courses: front/back logs alternate with side logs (notched corners)
    z = 0.14 + k * 0.21
    if k % 2 == 0:
        for sy in (-CD / 2, CD / 2):
            if sy < 0 and k < 8:   # the door gap in the front wall
                tube(f"LogF{k}a", [C((-CW / 2 - 0.25, sy, z)), C((-0.45, sy, z))], [0.12, 0.11], M_LOGS, sides=8)
                tube(f"LogF{k}b", [C((0.45, sy, z)), C((CW / 2 + 0.25, sy, z))], [0.11, 0.12], M_LOGS, sides=8)
            else:
                tube(f"LogF{k}", [C((-CW / 2 - 0.25, sy, z)), C((CW / 2 + 0.25, sy, z))], [0.12, 0.11], M_LOGS, sides=8)
    else:
        for sx in (-CW / 2, CW / 2):
            tube(f"LogS{k}", [C((sx, -CD / 2 - 0.25, z)), C((sx, CD / 2 + 0.25, z))], [0.12, 0.11], M_LOGS, sides=8)
# the roof: a gable of branches and brush, sagging a little
ROOF_TOP = 2.9
for sd in (-1, 1):
    v = [C((-CW / 2 - 0.4, sd * (CD / 2 + 0.45), CH)), C((CW / 2 + 0.4, sd * (CD / 2 + 0.45), CH)), C((CW / 2 + 0.4, 0, ROOF_TOP)), C((-CW / 2 - 0.4, 0, ROOF_TOP))]
    o = mesh_from(f"Roof{sd}", v, [(0, 1, 2, 3)], M_THATCH)
    o.modifiers.new("Solid", 'SOLIDIFY').thickness = 0.18
    for k in range(9):
        t = k / 8
        tube(f"RoofBranch{sd}{k}", [C((-CW / 2 - 0.5 + t * (CW + 1.0) + R.gauss(0, 0.05), sd * (CD / 2 + 0.5), CH + 0.08)),
                                    C((-CW / 2 - 0.5 + t * (CW + 1.0) + R.gauss(0, 0.1), 0, ROOF_TOP + 0.15))], [0.05, 0.03], M_LOGS, sides=5)
for sx in (-1, 1):   # gable ends: brush packed between upright sticks
    v = [C((sx * CW / 2, -CD / 2, CH)), C((sx * CW / 2, CD / 2, CH)), C((sx * CW / 2, 0, ROOF_TOP))]
    mesh_from(f"Gable{sx}", v, [(0, 1, 2)], M_THATCH).modifiers.new("Solid", 'SOLIDIFY').thickness = 0.1
# inside: dark, a bed of dried leaves along the back wall, the oilcan on a shelf beside the door
box("CottageInside", (CW - 0.2, CD - 0.2, 0.02), tuple(C((0, 0, 0.12))), M_DARK)
box("LeafBed", (1.9, 0.9, 0.25), tuple(C((0.5, CD / 2 - 0.6, 0.22))), M_LEAFBED, bevel=0.08)
box("Shelf", (0.5, 0.2, 0.03), tuple(C((-0.85, -CD / 2 + 0.22, 1.25))), M_LOGS, rot=(0, 0, CY))
OIL = C((-0.85, -CD / 2 + 0.22, 1.265))
oc = lathe("Oilcan", [(0.0, 0.0), (0.07, 0.0), (0.075, 0.01), (0.075, 0.07), (0.03, 0.11), (0.015, 0.13), (0.0, 0.13)], tuple(OIL), M_TIN, steps=14)
sp = OIL + Vector((0, 0, 0.06))
tube("OilSpout", [sp, sp + (C((0.2, -0.05, 0.1)) - C((0, 0, 0))).normalized() * 0.16 + Vector((0, 0, 0.1))], [0.012, 0.004], M_TIN, sides=6)

# ----------------------------------------------------------------------------- ferns and floor plants
FMB = MB(); GMB = MB()
placed = 0
for i in range(30000):
    r = 22.0 * R.random() ** 1.1 + 0.5; a = R.uniform(0, TWO_PI); x, y = r * math.sin(a), r * math.cos(a)
    if math.hypot(x, y) < 1.0 or (abs(x) < 0.5 and 0 < y < 2.0): continue
    if (Vector((x, y)) - SPRING.xy).length < 0.95: continue
    if (Vector((x, y)) - TREE_C.xy).length < 1.6 or (Vector((x, y)) - TIN.xy).length < 1.0: continue
    if (Vector((x, y)) - COTTAGE.xy).length < 3.0: continue
    if (Vector((x, y)) - Vector((0.2, 4.0))).length < 2.2: continue          # the way from the spring to the Woodman is open
    cl = clear_fn(x, y)
    if R.random() > 0.35 + 0.4 * (1 - cl) * (0.5 + 0.5 * n2(x, y, 3.0, 4.0)): continue
    if cl > 0.4:
        kind = R.choice(("grass", "flowers", "sedge", "tussock")); h = R.uniform(0.25, 0.5); mb = GMB
    else:
        kind = R.choice(("fern", "fern", "dock", "weed")); h = R.uniform(0.6, 1.2); mb = FMB
    plant(mb, x, y, h, CELLS[kind], R, n=2 if r < 10 else 1, segs=2, wk=0.65)
    placed += 1
    if placed > 650: break
for nm, mb, mat in (("Ferns", FMB, M_FERN), ("FloorGrass", GMB, M_FLOORGRASS)):
    o = mb.build(nm, mat)
    if o: set_card_normals(o, lambda p: Vector((0, 0, 1)))
# fallen branches and a log
for k in range(10):
    x, y = R.uniform(-10, 10), R.uniform(-5, 15)
    if math.hypot(x, y - 5) < 4.5 and abs(x) < 3: continue
    a = R.uniform(0, math.pi); d = Vector((math.cos(a), math.sin(a), 0)); L = R.uniform(0.8, 2.5)
    p0 = Vector((x, y, gz(x, y) + 0.04)); p1 = p0 + d * L; p1.z = gz(p1.x, p1.y) + 0.04
    tube(f"Branch{k}", [p0, p0.lerp(p1, 0.5) + Vector((0, 0, 0.05)), p1], [0.05, 0.035, 0.015], M_LOGS, sides=5)

# ----------------------------------------------------------------------------- sky and light
SKY = E8.sky_dome("SkyDome", M_SKY, 500.0, seg=40, rings=12, el_min=-6.0)
SKY.visible_shadow = False
light_obj("light.sun", 'SUN', 5.5, (1.0, 0.90, 0.72), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(1.5))
skl = light_obj("light.sky", 'SUN', 1.1, (0.62, 0.78, 0.66), (0, 0, 30), direction=(0.1, 0.2, -1.0), angle=math.radians(85))
skl.data.use_shadow = False
# "a ray of sunshine that fell between the trees": a narrow beam onto the Woodman through the canopy
beam_from = Vector((TIN.x, TIN.y, TZ + 1.2)) + SUN_DIR * 22.0
sb = light_obj("light.sunbeam", 'SPOT', 9000.0, (1.0, 0.92, 0.75), tuple(beam_from), direction=-SUN_DIR)
sb.data.spot_size = math.radians(9.0); sb.data.spot_blend = 0.6; sb.data.use_shadow = False; sb.data.shadow_soft_size = 0.5
world = bpy.data.worlds.new("Morning"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.40, 0.50, 0.46, 1); bg.inputs["Strength"].default_value = 1.0

sound("birds", "0", (-6.0, 10.0, 9.0)); sound("birds", "1", (7.0, -4.0, 11.0)); sound("wind-trees", "0", (8.0, 10.0, 15.0))
S.reader_anchors(0.0)
anchor("scene.centre", (TIN.x, TIN.y, TZ + 1.0))
anchor("clearing.oilcan", tuple(OIL))
S.check_clear(look_yaw=0.0)
EZ = gz(0, 0) + EYE
E = Vector((0, 0, EZ))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EZ - 0.6), 17),
    ("Cam_Woodman", (TIN.x - 1.6, TIN.y - 2.6, TZ + 1.4), (TIN.x, TIN.y, TZ + 1.25), 30),
    ("Cam_Cottage", (-3.0, 3.5, EZ), tuple(C((0, 0, 1.0))), 24),
], pitch=-2.0)
S.finish("woodman-forest-clearing", "woodman_forest_clearing", cams,
         keep_names={"M_Spring": "water.pond.spring", "M_ForestLeaves": "veg.crown.forest", "M_Ferns": "veg.shrub.fern", "M_FloorGrass": "veg.grass.floor",
                     "M_ForestFloor": "GroundNear", "M_SkyDome": "SkyDome"},
         keep_uv={"M_ForestFloor"},
         size_for={"M_ForestFloor": (2048, 256, 1024), "M_Tin": (1024, 256, 512), "M_OldBark": (1024, 128, 512), "M_CottageLogs": (1024, 64, 512),
                   "M_Heartwood": (256, 32, 128), "M_SpringStones": (512, 64, 256), "M_AxeHead": (64, 32), "M_AxeHandle": (128, 32), "M_BranchRoof": (512, 64, 256),
                   "M_LeafBed": (256, 32, 128), "M_CottageDark": (32,), "M_CanopyMass": (1024, 64, 512), "M_SkyDome": (512,)},
         page=page, default_exposure=0.3, water_colour={"M_Spring": (0.03, 0.05, 0.04)})
