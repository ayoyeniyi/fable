"""
Fable: before Circe's house on Aeaea (The Odyssey, Book X).

"When they reached Circe's house they found it built of cut stones, on a site that could be seen from far, in the
middle of the forest. There were wild mountain wolves and lions prowling all round it ..." "... they heard Circe
within, singing most beautifully as she worked at her loom, making a web so fine, so soft, and of such dazzling
colours as no one but a goddess could weave." "She set them upon benches and seats and mixed them a mess with cheese,
honey, meal, and Pramnian wine ..." "... and shut them up in her pigsties."

The reader stands in the forest clearing just outside the open gates of the court, facing the open doorway of the
hall: a house of dressed, cut stone, its timber doors standing open, inside a fire on the hearth, benches and seats,
a bronze mixing bowl with cheese, honey and meal on a table, and Circe's great upright loom with its bright web
catching the light by the door. To one side of the court, the stone pigsty with its gate shut (empty: the pigs
are only heard). Oaks close round the clearing; dappled daylight through the canopy. The beasts are left out
(a missing figure is better than a toy-like one): their tracks are in the dust of the court.

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py.

Node names the runtime relies on:
  anchor.reader.entrance (feet in the clearing outside the gates, facing +Y: the doorway and the loom),
  anchor.reader.look, anchor.scene.centre (the doorway), anchor.circe.loom
  light.sun (SUN, high morning sun through the canopy), light.sky (SUN, green-filtered fill), Lamp.hearth (POINT)
  fx.fire.hearth (the hall's fire), veg.crown.oak, veg.shrub.under, veg.grass.court, cloth.curtain.web (the web)
  sound.fire.hearth, sound.wind-trees.0, sound.birds.0
  SkyDome

Run headless:
  blender -b -P blender/build_circes_house.py -- --render --quick --cpu --res 900 --cams reader
  blender -b -P blender/build_circes_house.py -- --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b1 as S
from scene_kit_b1 import (K, E8, new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound, light_obj, camera,
                          link, smoothstep, lerp, n2, fbm2, orient, card, plant, set_card_normals, az_dir, TWO_PI)

ARGS = S.setup("circes-house", 1200, "CircesHouse", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
SUN_DIR = (az_dir(140.0) * math.cos(math.radians(48)) + Vector((0, 0, math.sin(math.radians(48))))).normalized()
GATE_Y = 4.0            # the court's gateway
HALL_Y = 10.5           # the hall's front wall
HALL_W, HALL_D, HALL_H = 10.0, 9.0, 4.2
DOOR_W, DOOR_H = 2.2, 3.0

def H(x, y):
    z = 0.25 * n2(x, y, 10.0, 3.0) + 0.06 * n2(x, y, 2.0, 7.0)
    z *= 1 - 0.85 * smoothstep(9.5, 7.0, max(abs(x) * 0.9, abs(y - 8.0)))      # the court is level
    return z
Z0 = H(0, 0)
def gz(x, y): return H(x, y) - Z0
S.set_ground(gz)
def court_fn(x, y): return smoothstep(0.5, -0.5, max(abs(x) - 6.5, GATE_Y - 0.2 - y, y - HALL_Y))
def path_fn(x, y): return smoothstep(1.4, 0.6, abs(x)) * smoothstep(-4.0, -1.0, y) * smoothstep(HALL_Y + 0.5, HALL_Y - 0.5, y)

def ground_mat(name="M_CourtGround"):
    """outside: oak-wood floor of leaf litter, moss and grass; the trodden path to the gate; inside the court, packed
    pale earth swept, with paw marks of the beasts in the dust."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    ac = node(nt, "ShaderNodeAttribute", (-2000, 700)); ac.attribute_name = "court"
    ap = node(nt, "ShaderNodeAttribute", (-2000, 550)); ap.attribute_name = "path"
    court, path = ac.outputs["Fac"], ap.outputs["Fac"]
    v1 = voronoi_(nt, co, 9.0, 'F1', (-1800, 200))
    l1 = node(nt, "ShaderNodeSeparateColor", (-1600, 200)); nt.links.new(v1.outputs["Color"], l1.inputs["Color"])
    litter = ramp(nt, [(0.0, c4(K.srgb((0.22, 0.15, 0.08)))), (0.4, c4(K.srgb((0.36, 0.25, 0.13)))), (0.75, c4(K.srgb((0.46, 0.34, 0.18)))), (1.0, c4(K.srgb((0.30, 0.22, 0.12))))], (-1400, 200))
    nt.links.new(l1.outputs[0], litter.inputs["Fac"])
    edge = maprange(nt, v1.outputs["Distance"], 0.0, 0.15, 0.6, 1.0, (-1400, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, litter.outputs["Color"], edge, (-1200, 200))
    n = noise_(nt, co, 0.6, 4, 0.6, loc=(-1800, -300))
    moss = mix_rgb(nt, 'MIX', maprange(nt, noise_(nt, co, 10.0, 4, 0.6, loc=(-1800, -500)).outputs["Fac"], 0.3, 0.7, 0, 1, (-1600, -500)), c4(K.srgb((0.16, 0.24, 0.07))), c4(K.srgb((0.30, 0.38, 0.12))), (-1400, -500))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.55, 0.65, 0, 0.8, (-1400, -300)), col, moss, (-1000, 200))
    earth = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1400, -800)), c4(K.srgb((0.50, 0.42, 0.32))), c4(K.srgb((0.60, 0.52, 0.40))), (-1200, -800))
    pv = voronoi_(nt, co, 5.0, 'F1', (-1800, -1000))
    paw = math_(nt, 'MULTIPLY', maprange(nt, pv.outputs["Distance"], 0.07, 0.04, 0, 1, (-1600, -1000)), maprange(nt, noise_(nt, co, 0.8, 2, 0.5, loc=(-1800, -1150)).outputs["Fac"], 0.5, 0.6, 0, 1, (-1600, -1150)), (-1450, -1050))
    earth = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', paw, 0.4, (-1300, -1050)), earth, (0.6, 0.55, 0.5, 1), (-1100, -900))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MAXIMUM', court, path, (-1000, -600)), col, earth, (-800, 200))
    col = K.ao_mul(nt, col, 0.3, 0.4, (-500, -900))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
    b.inputs["Specular IOR Level"].default_value = 0.2
    bump_from(nt, b, math_(nt, 'MULTIPLY', edge, math_(nt, 'SUBTRACT', 1.0, court, (-700, -1300)), (-600, -1300)), 0.4, 0.01)
    return m

def ashlar_mat(name="M_CutStone"):
    """dressed limestone ashlar: courses of squared blocks of differing tone, fine tooling, weathered edges, a little
    green at the foot."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1800, -400))
    br = node(nt, "ShaderNodeTexBrick", (-1400, 0)); br.offset = 0.5
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 0.85; br.inputs["Row Height"].default_value = 0.42
    br.inputs["Mortar Size"].default_value = 0.012; br.inputs["Color1"].default_value = (1, 1, 1, 1); br.inputs["Color2"].default_value = (0, 0, 0, 1)
    hv = node(nt, "ShaderNodeCombineXYZ", (-1600, 0)); nt.links.new(math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-1700, 100)), hv.inputs["X"]); nt.links.new(s.outputs["Z"], hv.inputs["Y"])
    nt.links.new(hv.outputs[0], br.inputs["Vector"])
    bs = node(nt, "ShaderNodeSeparateColor", (-1200, 0)); nt.links.new(br.outputs["Color"], bs.inputs["Color"])
    tone = ramp(nt, [(0.0, c4(K.srgb((0.62, 0.58, 0.50)))), (0.5, c4(K.srgb((0.72, 0.68, 0.58)))), (1.0, c4(K.srgb((0.66, 0.60, 0.50))))], (-1000, 0))
    nt.links.new(bs.outputs[0], tone.inputs["Fac"])
    n = noise_(nt, co, 3.0, 5, 0.6, loc=(-1400, -300)); fine = noise_(nt, co, 40.0, 3, 0.6, loc=(-1400, -500))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, tone.outputs["Color"], maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.82, 1.06, (-1200, -300)), (-800, 0))
    col = mix_rgb(nt, 'MIX', br.outputs["Fac"], col, c4(K.srgb((0.36, 0.33, 0.28))), (-650, 0))
    green = maprange(nt, s.outputs["Z"], 0.8, 0.0, 0, 0.5, (-1200, -700))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', green, maprange(nt, n.outputs["Fac"], 0.45, 0.6, 0, 1, (-1200, -850)), (-1000, -750)), col, c4(K.srgb((0.30, 0.36, 0.18))), (-500, 0))
    col = K.ao_mul(nt, col, 0.15, 0.4, (-350, -900))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', br.outputs["Fac"], -1.0, (-600, -1000)), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.25, (-600, -1100)), (-450, -1050)), 0.5, 0.01)
    return m

def web_image(W=512, Hh=768, seed=8):
    """Circe's web on the loom: a tapestry woven in dazzling colours, bands of meander and rosettes in saffron,
    purple, sea-blue and crimson, the woven part rising from the bottom bar to about two-thirds up; above it the
    bare warp threads."""
    R = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:Hh, 0:W].astype(np.float32); u = xx / W; v = 1 - yy / Hh
    img = np.zeros((Hh, W, 4), np.float32); img[..., 3] = 1
    cols = np.array([[0.85, 0.55, 0.08], [0.42, 0.10, 0.40], [0.08, 0.30, 0.55], [0.70, 0.08, 0.08], [0.90, 0.80, 0.55], [0.10, 0.42, 0.30]])
    band = np.floor(v * 14).astype(int) % len(cols)
    base = cols[band]
    meander = ((np.floor(u * 24) + np.floor(v * 56)) % 3 == 0)
    rose = (np.hypot((u * 8) % 1 - 0.5, (v * 14) % 1 - 0.5) < 0.28)
    alt = cols[(band + 2) % len(cols)]
    c = np.where(meander[..., None], alt, base)
    c = np.where(rose[..., None] & (band % 3 == 0)[..., None], cols[(band + 4) % len(cols)], c)
    weave = 0.85 + 0.15 * ((np.floor(xx / 2) + np.floor(yy / 2)) % 2)[..., None]
    c = c * weave
    woven = v < 0.68
    warp = ((np.floor(u * 160) % 2) == 0)
    warpc = np.array([0.85, 0.80, 0.68])
    out = np.where(woven[..., None], c, np.where(warp[..., None], warpc, 0.0))
    img[..., :3] = out
    img[..., 3] = np.where(woven | warp, 1.0, 0.0)
    return img
print("materials ...", flush=True)
M_GROUND = ground_mat()
M_STONE = ashlar_mat()
M_TIMBER = S.bark_mat("M_OakTimber", (0.34, 0.26, 0.18), (0.14, 0.10, 0.07), (0.44, 0.34, 0.24), scale=3.0, fissure=0.3, moss=0.0)
M_BARK = S.bark_mat("M_OakBark", (0.24, 0.22, 0.18), (0.08, 0.07, 0.06), (0.34, 0.31, 0.26), scale=0.8, fissure=0.8, moss=0.35)
M_ROOF = K.noisy("M_Thatch", [K.srgb((0.42, 0.34, 0.20)), K.srgb((0.32, 0.25, 0.15)), K.srgb((0.50, 0.42, 0.26))], scale=8, rough=0.95, bump=0.6, stretch=(1, 1, 0.2))
M_DARK = plain("M_HallDark", (0.03, 0.025, 0.02), rough=1.0)
M_HEARTH = K.noisy("M_HearthEmbers", [K.srgb((0.08, 0.06, 0.05)), K.srgb((0.9, 0.35, 0.08))], scale=12, rough=0.9, bump=0.3)
M_BRONZE = K.noisy("M_Bronze", [K.srgb((0.55, 0.38, 0.18)), K.srgb((0.42, 0.30, 0.15))], scale=6, rough=0.35, bump=0.05, metallic=1.0)
M_CHEESE = plain("M_Cheese", K.srgb((0.88, 0.82, 0.62)), rough=0.7)
M_HONEY = plain("M_Honey", K.srgb((0.75, 0.45, 0.08)), rough=0.15)
M_CLAY = K.noisy("M_Clay", [K.srgb((0.62, 0.36, 0.20)), K.srgb((0.52, 0.30, 0.16))], scale=10, rough=0.8, bump=0.1)
M_WEB = image_mat("M_Web", np_image("A_CirceWeb", web_image()), rough=0.8, alpha=True)
M_OAK = image_mat("M_OakLeaves", S.spray_atlas("A_OakSprays", "oak", 91), rough=0.6, alpha=True)
M_CANOPY = S.crown_mass_mat("M_CanopyMass", (0.04, 0.07, 0.02), (0.10, 0.17, 0.05), (0.18, 0.26, 0.08), scale=2.0)
IMG_PLANTS, CELLS = S.plant_atlas("A_WoodPlants", ["fern", "fern", "grass", "dock", "tussock", "flowers", "weed", "grass"], seed=91)
M_UNDER = image_mat("M_Undergrowth", IMG_PLANTS, rough=0.6, alpha=True)
M_GRASS = image_mat("M_CourtGrass", IMG_PLANTS, rough=0.6, alpha=True)
M_SKY = S.gradient_sky_mat("M_SkyDome", [(0.0, (0.75, 0.80, 0.80)), (0.3, (0.52, 0.66, 0.88)), (1.0, (0.30, 0.48, 0.82))], sun_dir=SUN_DIR, glow=((1.0, 0.95, 0.8), 40.0))

# ----------------------------------------------------------------------------- ground, the court wall and gates, the hall
print("court ...", flush=True)
S.ground("Clearing", M_GROUND, 70.0, r0=2.0, NA=96, NR=30, attrs={"court": court_fn, "path": path_fn})
# the court wall: dressed stone, 2 m high, round the court, the gateway in front
WALL_T = 0.6
def wallseg(name, a, b_, h=2.1):
    a = Vector(a); b_ = Vector(b_); d = b_ - a; c = (a + b_) / 2
    box(name, (d.length + WALL_T, WALL_T, h), (c.x, c.y, gz(c.x, c.y) + h / 2 - 0.1), M_STONE, rot=(0, 0, math.atan2(d.y, d.x)))
    box(name + "Cope", (d.length + WALL_T + 0.1, WALL_T + 0.12, 0.14), (c.x, c.y, gz(c.x, c.y) + h - 0.03), M_STONE, rot=(0, 0, math.atan2(d.y, d.x)))
GW = 3.0
wallseg("CourtWallFL", (-7.0, GATE_Y), (-GW / 2 - 0.4, GATE_Y)); wallseg("CourtWallFR", (GW / 2 + 0.4, GATE_Y), (7.0, GATE_Y))
wallseg("CourtWallL", (-7.0, GATE_Y), (-7.0, HALL_Y)); wallseg("CourtWallR", (7.0, GATE_Y), (7.0, HALL_Y))
for sd in (-1, 1):   # gate piers and the two open gate leaves swung inward
    box(f"GatePier{sd}", (0.8, 0.8, 2.6), (sd * (GW / 2 + 0.4), GATE_Y, gz(0, GATE_Y) + 1.2), M_STONE, bevel=0.02)
    leaf = box(f"GateLeaf{sd}", (GW / 2, 0.1, 2.2), (0, 0, 0), M_TIMBER)
    hinge = Vector((sd * GW / 2, GATE_Y + 0.15, gz(0, GATE_Y) + 1.1))
    ang = sd * math.radians(-72)
    leaf.matrix_world = Matrix.Translation(hinge) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Translation((-sd * GW / 4, 0, 0))
# the hall: cut-stone walls, a high doorway with open timber doors, a thatched hip roof on oak rafters, a smoke-hole
HZ = gz(0, HALL_Y) - 0.1
for sd in (-1, 1):
    box(f"HallFront{sd}", ((HALL_W - DOOR_W) / 2, 0.7, HALL_H), (sd * (DOOR_W / 2 + (HALL_W - DOOR_W) / 4), HALL_Y, HZ + HALL_H / 2), M_STONE)
    box(f"HallSide{sd}", (0.7, HALL_D, HALL_H), (sd * (HALL_W / 2 - 0.35), HALL_Y + HALL_D / 2, HZ + HALL_H / 2), M_STONE)
box("HallLintel", (DOOR_W + 0.6, 0.8, 0.5), (0, HALL_Y, HZ + DOOR_H + 0.25), M_STONE)
box("HallAbove", (DOOR_W, 0.7, HALL_H - DOOR_H - 0.5), (0, HALL_Y, HZ + DOOR_H + 0.5 + (HALL_H - DOOR_H - 0.5) / 2), M_STONE)
box("HallBack", (HALL_W, 0.7, HALL_H), (0, HALL_Y + HALL_D, HZ + HALL_H / 2), M_STONE)
box("HallFloor", (HALL_W - 1.2, HALL_D - 0.8, 0.1), (0, HALL_Y + HALL_D / 2, HZ + 0.05), M_STONE)
box("Threshold", (DOOR_W + 0.2, 0.9, 0.18), (0, HALL_Y, HZ + 0.09), M_STONE)
for sd in (-1, 1):
    leaf = box(f"HallDoor{sd}", (DOOR_W / 2, 0.1, DOOR_H), (0, 0, 0), M_TIMBER)
    hinge = Vector((sd * DOOR_W / 2, HALL_Y + 0.4, HZ + DOOR_H / 2 + 0.1))
    leaf.matrix_world = Matrix.Translation(hinge) @ Matrix.Rotation(sd * math.radians(-80), 4, 'Z') @ Matrix.Translation((-sd * DOOR_W / 4, 0, 0))
RZ = HZ + HALL_H
rv = [(-HALL_W / 2 - 0.8, HALL_Y - 0.8, RZ), (HALL_W / 2 + 0.8, HALL_Y - 0.8, RZ), (HALL_W / 2 + 0.8, HALL_Y + HALL_D + 0.8, RZ), (-HALL_W / 2 - 0.8, HALL_Y + HALL_D + 0.8, RZ),
      (-1.6, HALL_Y + HALL_D / 2, RZ + 3.4), (1.6, HALL_Y + HALL_D / 2, RZ + 3.4)]
ro = mesh_from("Roof", rv, [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)], M_ROOF)
ro.modifiers.new("Solid", 'SOLIDIFY').thickness = 0.35
orient(ro, lambda c: (c - Vector((0, HALL_Y + HALL_D / 2, RZ))))
box("HallCeilingDark", (HALL_W - 1.2, HALL_D - 0.8, 0.05), (0, HALL_Y + HALL_D / 2, RZ - 0.02), M_DARK)
for k in range(6):
    box(f"Rafter{k}", (HALL_W - 1.0, 0.18, 0.22), (0, HALL_Y + 0.9 + k * 1.4, RZ - 0.2), M_TIMBER)
# inside: the hearth with its fire, benches and seats, a table with the mess of cheese, honey, meal and wine
HEARTH = Vector((-1.6, HALL_Y + 5.4, HZ + 0.12))
for k in range(12):
    a = TWO_PI * k / 12
    sphere("HearthStone", 0.14, tuple(HEARTH + Vector((math.cos(a) * 0.75, math.sin(a) * 0.75, 0.02))), M_STONE, seg=8, scale=(1.2, 1.0, 0.7))
sphere("HearthBed", 1.0, tuple(HEARTH), M_HEARTH, seg=12, scale=(0.65, 0.65, 0.1))
for k in range(4):
    a = k * 0.8
    tube("HearthLog", [HEARTH + Vector((math.cos(a) * -0.5, math.sin(a) * -0.5, 0.08)), HEARTH + Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, 0.16))], [0.07, 0.06], M_TIMBER, sides=6)
for sd in (-1, 1):
    box(f"Bench{sd}", (0.45, 4.0, 0.08), (sd * 3.4, HALL_Y + 4.8, HZ + 0.48), M_TIMBER)
    for yy in (-1.7, 0.0, 1.7): box(f"BenchLeg{sd}", (0.4, 0.08, 0.44), (sd * 3.4, HALL_Y + 4.8 + yy, HZ + 0.22), M_TIMBER)
box("Thronos", (0.8, 0.7, 0.5), (0.0, HALL_Y + 7.9, HZ + 0.25), M_TIMBER)
box("ThronosBack", (0.8, 0.1, 1.4), (0.0, HALL_Y + 8.25, HZ + 0.7), M_TIMBER)
TABLE = Vector((-2.4, HALL_Y + 2.4, HZ))
box("Table", (1.4, 0.8, 0.06), tuple(TABLE + Vector((0, 0, 0.74))), M_TIMBER)
for (dx, dy) in ((-0.6, -0.33), (0.6, -0.33), (-0.6, 0.33), (0.6, 0.33)): box("TableLeg", (0.07, 0.07, 0.74), tuple(TABLE + Vector((dx, dy, 0.37))), M_TIMBER)
lathe("MixingBowl", [(0.0, 0.0), (0.1, 0.0), (0.12, 0.04), (0.08, 0.1), (0.22, 0.24), (0.26, 0.34), (0.24, 0.35), (0.0, 0.3)], tuple(TABLE + Vector((-0.3, 0, 0.77))), M_BRONZE, steps=20)
cyl("Cheese", 0.11, 0.07, tuple(TABLE + Vector((0.25, -0.1, 0.81))), M_CHEESE, verts=14)
lathe("HoneyPot", [(0.0, 0.0), (0.06, 0.0), (0.08, 0.06), (0.05, 0.12), (0.06, 0.14), (0.0, 0.14)], tuple(TABLE + Vector((0.4, 0.2, 0.77))), M_CLAY, steps=12)
cyl("Honey", 0.05, 0.005, tuple(TABLE + Vector((0.4, 0.2, 0.907))), M_HONEY, verts=12)
# the loom by the door inside: an upright warp-weighted loom leaning on the wall, the bright web on it
LOOM = Vector((0.75, HALL_Y + 2.4, HZ))
for sd in (-1, 1):
    tube(f"LoomUpright{sd}", [LOOM + Vector((sd * 0.9, 0.3, 0)), LOOM + Vector((sd * 0.9, -0.1, 2.5))], [0.05, 0.045], M_TIMBER, sides=6)
tube("LoomBeam", [LOOM + Vector((-1.05, -0.1, 2.35)), LOOM + Vector((1.05, -0.1, 2.35))], [0.06, 0.06], M_TIMBER, sides=8)
tube("LoomShed", [LOOM + Vector((-0.95, 0.05, 1.4)), LOOM + Vector((0.95, 0.05, 1.4))], [0.025, 0.025], M_TIMBER, sides=6)
WB = MB()
card(WB, LOOM + Vector((0, 0.18, 0.3)), Vector((1.7, 0, 0)), Vector((0, -0.26, 2.0)), (0, 0, 1, 1), 0.0, 0.3, segs=4)
web = WB.build("Web", M_WEB)
for k in range(14):   # loom weights hanging from the warp
    x = -0.8 + k * 0.123
    sphere("LoomWeight", 0.04, tuple(LOOM + Vector((x, 0.22, 0.22))), M_CLAY, seg=8, scale=(1, 0.7, 1.3))
# the pigsty against the court wall on the left: low stone walls, a slatted gate (shut), a trough, mud
PS = Vector((-5.2, 7.0, 0))
for (a, b_) in (((-6.6, 5.6), (-3.8, 5.6)), ((-3.8, 5.6), (-3.8, 8.6)), ((-6.6, 8.6), (-3.8, 8.6))):
    if a == (-3.8, 5.6): continue
    a = Vector(a); b_ = Vector(b_); d = b_ - a; c = (a + b_) / 2
    box("StyWall", (d.length + 0.4, 0.4, 1.1), (c.x, c.y, gz(c.x, c.y) + 0.45), M_STONE, rot=(0, 0, math.atan2(d.y, d.x)))
for k in range(7):   # the slatted gate on the court side (x = -3.8)
    box(f"StySlat{k}", (0.06, 0.1, 1.0), (-3.8, 6.0 + k * 0.38, gz(-3.8, 7.1) + 0.5), M_TIMBER)
for z in (0.3, 0.85): box("StyRail", (0.06, 2.8, 0.1), (-3.8, 7.1, gz(-3.8, 7.1) + z), M_TIMBER)
box("Trough", (1.4, 0.4, 0.3), (-5.6, 8.2, gz(-5.6, 8.2) + 0.15), M_STONE)
for k in range(10):   # acorns and beech mast scattered in the sty
    sphere("Acorn", 0.012, (-5.6 + random.uniform(-0.8, 0.8), 7.0 + random.uniform(-1, 1), gz(-5.5, 7.0) + 0.01), M_TIMBER, seg=6, scale=(1, 1, 1.4))
STY_MUD = box("StyMud", (2.6, 2.8, 0.02), (-5.2, 7.1, gz(-5.2, 7.1) + 0.005), plain("M_StyMud", K.srgb((0.22, 0.17, 0.12)), rough=0.4))

# ----------------------------------------------------------------------------- the oaks round the clearing, undergrowth
print("trees ...", flush=True)
FR = random.Random(17)
for k, (x, y) in enumerate(((-11, -2), (10, -3), (-13, 8), (12, 7), (-9, 16), (9, 17), (0, 22), (-16, 1), (16, 0), (-5, -8), (6, -9), (-18, 14), (18, 15),
                            (-3, -14), (12, -12), (-12, -13))):
    near = math.hypot(x, y) < 14
    S.tree(f"Oak{k}", x, y, FR.uniform(18, 24), FR.uniform(6.5, 8), "oak", 300 + k, M_BARK, "oak", nlimbs=6 if near else 5, detail=1.0 if near else 0.5,
           cards_per_tip=1, card_size=2.5, fill=40 if near else 26, roots=True)
for k in range(22):
    a = FR.uniform(0, TWO_PI); r = FR.uniform(22, 34); x, y = r * math.sin(a), 4 + r * math.cos(a)
    S.tree(f"Far{k}", x, y, FR.uniform(18, 24), FR.uniform(6, 8), "far", 600 + k, M_BARK, "oak", nlimbs=4, detail=0.3, cards_per_tip=0, card_size=5.0, fill=18, roots=False)
CMB = MB()
for (key, C, a_, c_) in list(S.CROWNS):
    S.lumps(CMB, C + Vector((0, 0, c_ * 0.3)), a_ * 0.55, c_ * 0.45, 3, FR, int(C.x * 7 + C.y), sub=1, sway=(0.1, 0.4))
CMB.build("CanopyMass", M_CANOPY, sway=False)
S.build_crowns({"oak": M_OAK}, names={"oak": "CrownsOak"})
UMB = MB(); GMB = MB(); placed = 0
for i in range(30000):
    r = 24.0 * FR.random() ** 1.1 + 0.5; a = FR.uniform(0, TWO_PI); x, y = r * math.sin(a), r * math.cos(a)
    if court_fn(x, y) > 0.2 or path_fn(x, y) > 0.3 or math.hypot(x, y) < 1.0: continue
    if abs(x) < 7.5 and GATE_Y - 0.5 < y < HALL_Y + HALL_D + 1.0: continue
    if FR.random() > 0.5: continue
    kind = FR.choice(("fern", "fern", "dock", "weed", "tussock", "grass", "flowers"))
    h = FR.uniform(0.4, 1.0) if kind in ("fern", "weed", "dock") else FR.uniform(0.25, 0.5)
    plant(UMB if kind in ("fern", "weed", "dock") else GMB, x, y, h, CELLS[kind], FR, n=2 if r < 10 else 1, segs=2, wk=0.6)
    placed += 1
    if placed > 600: break
for nm, mb, mat in (("Undergrowth", UMB, M_UNDER), ("CourtGrass", GMB, M_GRASS)):
    o = mb.build(nm, mat)
    if o: set_card_normals(o, lambda p: Vector((0, 0, 1)))

SKY = E8.sky_dome("SkyDome", M_SKY, 500.0, seg=40, rings=12, el_min=-6.0); SKY.visible_shadow = False
K.apply_transforms()
light_obj("light.sun", 'SUN', 4.5, (1.0, 0.93, 0.80), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(1.5))
skl = light_obj("light.sky", 'SUN', 0.4, (0.60, 0.78, 0.65), (0, 0, 30), direction=(0.1, 0.2, -1.0), angle=math.radians(85))
skl.data.use_shadow = False
light_obj("Lamp.hearth", 'POINT', 260.0, (1.0, 0.55, 0.22), tuple(HEARTH + Vector((0, 0, 0.6))), shadow_soft_size=0.3)
world = bpy.data.worlds.new("Forest"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.40, 0.50, 0.45, 1); bg.inputs["Strength"].default_value = 0.5

E8.fx("fx.fire.hearth", tuple(HEARTH + Vector((0, 0, 0.1))), 0.5)
sound("fire", "hearth", tuple(HEARTH + Vector((0, 0, 0.5)))); sound("wind-trees", "0", (8.0, 6.0, 14.0)); sound("birds", "0", (-9.0, 4.0, 10.0))
S.reader_anchors(0.0)
anchor("scene.centre", (0.0, HALL_Y, HZ + 1.5))
anchor("circe.loom", tuple(LOOM + Vector((0, 0.1, 1.3))))
S.check_clear(look_yaw=0.0)
EZ = gz(0, 0) + EYE
E = Vector((0, 0, EZ))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EZ - 0.3), 17),
    ("Cam_Door", (0.3, 7.6, EZ), (0.75, HALL_Y + 2.4, HZ + 1.3), 24),
    ("Cam_Sty", (-1.8, 4.6, EZ), (-5.2, 7.1, gz(-5.2, 7.1) + 0.4), 24),
], pitch=0.0)
S.finish("circes-house", "circes_house", cams,
         keep_names={"M_OakLeaves": "veg.crown.oak", "M_Undergrowth": "veg.shrub.under", "M_CourtGrass": "veg.grass.court", "M_Web": "cloth.curtain.web",
                     "M_CourtGround": "GroundNear", "M_SkyDome": "SkyDome"},
         keep_uv={"M_CourtGround"},
         size_for={"M_CourtGround": (2048, 256, 1024), "M_CutStone": (2048, 128, 1024), "M_OakTimber": (1024, 64, 512), "M_OakBark": (1024, 128, 512),
                   "M_Thatch": (1024, 64, 512), "M_HallDark": (32,), "M_HearthEmbers": (128, 32), "M_Bronze": (128, 32, 64), "M_Cheese": (32,), "M_Honey": (32,),
                   "M_Clay": (128, 32, 64), "M_CanopyMass": (1024, 64, 512), "M_StyMud": (64,), "M_SkyDome": (512,)},
         page=page, default_exposure=0.3)
