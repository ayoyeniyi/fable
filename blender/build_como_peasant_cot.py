"""
Fable scene room: A peasant cottage by the Lake of Como (Frankenstein, Chapter I) - como-peasant-cot.

"During one of their walks a poor cot in the foldings of a vale attracted their notice as being singularly
disconsolate, while the number of half-clothed children gathered about it spoke of penury in its worst shape ...
she found a peasant and his wife, hard working, bent down by care and labour, distributing a scanty meal to five
hungry babes. Among these there was one which attracted my mother far above all the rest ... she appeared of a
different stock ... her hair was the brightest living gold ... She appeared ... fairer than a garden rose among
dark-leaved brambles."

A poor cottage of rough fieldstone in a fold of the hills above the lake, about 1770: a low single room under a roof
of stone slabs (piode), a chestnut-plank door standing open on the dim room within - a rough table with five wooden
bowls, a dark loaf, a pot, a bench and stools, the hearth with a low fire on the floor of the back wall, straw in a
corner, a shelf, chestnut beams; a patched shirt and a child's smock on a line by the door; a woodpile and a split
chestnut log for a seat; dark-leaved brambles heaped against the wall and over the terrace edge with a wild rose in
flower in them by the door; the trodden dooryard; dry-stone terrace walls stepping down the slope; sweet chestnuts
above and around; behind the reader, below, the lake between steep wooded mountains. People are left out.

Light: a warm, clear Italian afternoon in summer, the sun in the south-west behind the reader's right shoulder,
lighting the cottage front; the room within dim beyond the door.

Axes: metres, +Z up, +Y north (up the vale, toward the cottage); the lake lies south, below. Reader in the dooryard
facing north at the open door.

Run headless:
  blender -b -P blender/build_como_peasant_cot.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_como_peasant_cot.py -- --cpu --render --samples 32 --res 1280 --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b4 as S
from scene_kit_b4 import (K, new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, np_image, Canvas, box, cyl, lathe, tube, MB, anchor, sound, light_obj, smoothstep, n2, srgb,
                          mb_box, mb_quad, card, set_card_normals)

ARGS = S.setup("como-peasant-cot", 1770, "ComoPeasantCot", default_samples=48)
rng = random.Random(1770)
EYE = S.EYE
SUN_DIR = Vector((-0.55, -0.62, 0.56)).normalized()       # toward the sun: south-west, ~34 degrees up
HX0, HX1, HY0, HY1 = -3.6, 3.6, 4.2, 9.2                  # the cottage's outer walls
WALL_T = 0.55; WALL_H = 2.9
DOOR_X, DOOR_W, DOOR_H = 0.2, 0.95, 1.85
LAKE_Z = -95.0

# ----------------------------------------------------------------------------- the ground: the dooryard terrace, the slope, the vale
def gz(x, y):
    """The dooryard is a level terrace (z ~ 0) cut into a slope that rises north; below it to the south the terraces
    step down toward the lake; the vale's sides rise east and west."""
    r = math.hypot(x, y)
    slope = 0.0
    if y > HY1 + 0.4: slope = (y - HY1 - 0.4) * 0.32
    elif y < -3.2:
        d = -3.2 - y
        steps = math.floor(d / 4.5); f = (d / 4.5) - steps
        slope = -(steps * 1.6 + 1.6 * smoothstep(0.0, 0.18, f)) - d * 0.05
        slope += -max(0.0, d - 25) * 0.22
    side = 0.012 * (abs(x) ** 1.6) * smoothstep(6, 30, abs(x))
    z = slope + side
    z += 0.04 * noise.noise(Vector((x * 0.9, y * 0.9, 0.3))) + 0.6 * noise.noise(Vector((x * 0.05, y * 0.05, 1.3))) * smoothstep(8, 30, r)
    return z
Z0 = gz(0, 0)
def h(x, y): return gz(x, y) - Z0

# ----------------------------------------------------------------------------- materials
def stone_wall_mat(name, mortar=0.5):
    """Rough fieldstone laid in lime: rounded grey-ochre stones (gneiss and limestone of the lake shore), recessed
    pale lime joints, lichen and soot, the base darker with damp and splashed earth."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0)); s = sep_xyz(nt, co, (-2200, 0))
    mp = node(nt, "ShaderNodeMapping", (-2000, 0)); mp.inputs["Scale"].default_value = (6.0, 6.0, 9.5); nt.links.new(co, mp.inputs["Vector"])
    wn = node(nt, "ShaderNodeTexNoise", (-2000, -300)); wn.inputs["Scale"].default_value = 3.0; wn.inputs["Detail"].default_value = 3.0
    nt.links.new(co, wn.inputs["Vector"])
    wv = node(nt, "ShaderNodeVectorMath", (-1900, -100), operation='MULTIPLY_ADD'); wv.inputs[1].default_value = (0.35, 0.35, 0.35)
    nt.links.new(wn.outputs["Color"], wv.inputs[0]); nt.links.new(mp.outputs["Vector"], wv.inputs[2])
    v = voronoi_(nt, wv.outputs[0], 1.0, 'DISTANCE_TO_EDGE', (-1800, 0))
    vc = voronoi_(nt, wv.outputs[0], 1.0, 'F1', (-1800, -300))
    joint = maprange(nt, v.outputs["Distance"], 0.0, 0.05, 1, 0, (-1500, 0))
    stone = ramp(nt, [(0.0, c4(srgb((0.36, 0.34, 0.31)))), (0.25, c4(srgb((0.50, 0.47, 0.42)))), (0.5, c4(srgb((0.58, 0.52, 0.42)))), (0.75, c4(srgb((0.44, 0.43, 0.40)))), (1.0, c4(srgb((0.62, 0.58, 0.50))))], (-1400, -300))
    nt.links.new(sep_xyz(nt, vc.outputs["Color"], (-1600, -400)).outputs["X"], stone.inputs["Fac"])
    n = noise_(nt, co, 6.0, 5, 0.6, loc=(-1600, 300))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.0, 0.3, (-1200, 300)), stone.outputs["Color"], (0.6, 0.58, 0.52, 1), (-1000, -200))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', joint, mortar), col, c4(srgb((0.56, 0.53, 0.47))), (-800, -100))
    lich = maprange(nt, noise_(nt, co, 3.0, 4, 0.6, loc=(-1300, 600)).outputs["Fac"], 0.62, 0.72, 0, 0.6, (-1100, 600))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', lich, math_(nt, 'SUBTRACT', 1.0, joint)), col, c4(srgb((0.55, 0.56, 0.38))), (-600, -100))
    damp = maprange(nt, s.outputs["Z"], 0.0, 0.6, 0.45, 0.0, (-1100, -800))
    col = mix_rgb(nt, 'MULTIPLY', damp, col, c4(srgb((0.42, 0.38, 0.32))), (-400, -100))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, joint, 0, 1, 0.8, 0.95, (-400, -400)), b.inputs["Roughness"])
    hgt = math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', n.outputs["Fac"], 0.25), joint, (-500, -600))
    bump_from(nt, b, hgt, 0.25, 0.012, (0, -600))
    return m


def earth_mat(name):
    """The dooryard and the terraces: trodden dry earth and grit, chestnut husks and leaf litter, short dry grass
    toward the edges, a path worn to the door."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0)); s = sep_xyz(nt, co, (-2200, 0))
    n1 = noise_(nt, co, 0.6, 5, 0.6, loc=(-1800, 300)); n2_ = noise_(nt, co, 5.0, 6, 0.6, loc=(-1800, 0)); n3 = noise_(nt, co, 40.0, 4, 0.6, loc=(-1800, -300))
    earth = ramp(nt, [(0.0, c4(srgb((0.28, 0.22, 0.15)))), (0.5, c4(srgb((0.38, 0.31, 0.22)))), (1.0, c4(srgb((0.47, 0.40, 0.30))))], (-1300, 200))
    nt.links.new(math_(nt, 'ADD', math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.6), math_(nt, 'MULTIPLY', n3.outputs["Fac"], 0.4)), earth.inputs["Fac"])
    grass = ramp(nt, [(0.0, c4(srgb((0.22, 0.28, 0.10)))), (0.5, c4(srgb((0.33, 0.37, 0.15)))), (1.0, c4(srgb((0.46, 0.45, 0.24))))], (-1300, -200))
    nt.links.new(n3.outputs["Fac"], grass.inputs["Fac"])
    att = node(nt, "ShaderNodeAttribute", (-1500, 700)); att.attribute_name = "worn"; att.attribute_type = 'GEOMETRY'
    gw = maprange(nt, math_(nt, 'ADD', math_(nt, 'MULTIPLY', n1.outputs["Fac"], 0.6), math_(nt, 'SUBTRACT', 0.0, att.outputs["Fac"])), 0.12, 0.28, 0, 1, (-1000, 500))
    col = mix_rgb(nt, 'MIX', gw, earth.outputs["Color"], grass.outputs["Color"], (-800, 100))
    vor = voronoi_(nt, co, 9.0, 'F1', (-1500, -800))
    husk = math_(nt, 'MULTIPLY', maprange(nt, vor.outputs["Distance"], 0.1, 0.04, 0, 1, (-1300, -800)), 0.7, (-1100, -800))
    col = mix_rgb(nt, 'MIX', husk, col, c4(srgb((0.30, 0.20, 0.10))), (-500, 100))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95; b.inputs["Specular IOR Level"].default_value = 0.25
    bump_from(nt, b, math_(nt, 'ADD', n3.outputs["Fac"], math_(nt, 'MULTIPLY', husk, 0.5)), 0.45, 0.012, (0, -500))
    return m


M_WALL = stone_wall_mat("M_FieldStone")
M_TERRACE = stone_wall_mat("M_TerraceStone", mortar=0.0)
M_EARTH = earth_mat("M_Earth")
M_FLOOR = noisy("M_EarthFloor", [srgb((0.22, 0.18, 0.13)), srgb((0.30, 0.25, 0.18)), srgb((0.18, 0.15, 0.11))], scale=4.0, rough=0.95, bump=0.3)
M_SLAB = noisy("M_RoofSlabs", [srgb((0.40, 0.39, 0.37)), srgb((0.50, 0.48, 0.44)), srgb((0.33, 0.32, 0.30)), srgb((0.46, 0.46, 0.38))], scale=3.0, rough=0.85, bump=0.6, bump_dist=0.02)
M_CHESTNUT = noisy("M_ChestnutTimber", [srgb((0.30, 0.22, 0.15)), srgb((0.40, 0.31, 0.21)), srgb((0.24, 0.18, 0.12))], scale=3.0, rough=(0.6, 0.85), bump=0.3, stretch=(6, 6, 0.3))
M_PLANK = noisy("M_DoorPlanks", [srgb((0.36, 0.28, 0.19)), srgb((0.46, 0.37, 0.26)), srgb((0.30, 0.23, 0.16))], scale=3.0, rough=(0.6, 0.85), bump=0.3, stretch=(6, 6, 0.25))
M_IRON = noisy("M_Iron", [srgb((0.06, 0.06, 0.06)), srgb((0.14, 0.09, 0.06)), srgb((0.04, 0.04, 0.04))], scale=20.0, rough=(0.5, 0.8), metallic=0.5)
M_POT = noisy("M_Terracotta", [srgb((0.55, 0.30, 0.18)), srgb((0.62, 0.36, 0.22)), srgb((0.45, 0.24, 0.14))], scale=20.0, rough=0.8, bump=0.1)
M_BREAD = noisy("M_Bread", [srgb((0.40, 0.26, 0.14)), srgb((0.50, 0.33, 0.18))], scale=40.0, rough=0.8, bump=0.4)
M_STRAW = noisy("M_Straw", [srgb((0.70, 0.60, 0.36)), srgb((0.60, 0.50, 0.28)), srgb((0.78, 0.68, 0.44))], scale=80.0, rough=0.9, bump=0.8, bump_dist=0.01, warp=2.0)
M_LINEN = noisy("M_PatchedLinen", [srgb((0.82, 0.78, 0.68)), srgb((0.70, 0.66, 0.56)), srgb((0.52, 0.44, 0.34))], scale=3.0, rough=0.9, bump=0.1)
M_SOOT = plain("M_Soot", (0.02, 0.018, 0.016), rough=0.95)
M_LAKE = noisy("M_Lake", [srgb((0.12, 0.20, 0.22)), srgb((0.16, 0.25, 0.27)), srgb((0.10, 0.18, 0.20))], scale=0.02, rough=0.08, bump=0.05, bump_dist=0.1)

def embers_mat(name="M_Embers"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 22.0, 'DISTANCE_TO_EDGE', (-900, 0))
    glow = maprange(nt, v.outputs["Distance"], 0.0, 0.08, 1, 0, (-700, 0))
    col = mix_rgb(nt, 'MIX', glow, (0.03, 0.025, 0.02, 1), (0.9, 0.3, 0.06, 1), (-300, 0))
    nt.links.new(col, b.inputs["Base Color"])
    ec = mix_rgb(nt, 'MULTIPLY', 1.0, (1.0, 0.35, 0.07, 1), glow, (-300, -300))
    nt.links.new(ec, b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 3.0
    return m
M_EMBERS = embers_mat()

print("painting atlases ...", flush=True)
CHESTNUT_PAL = [(0.26, 0.36, 0.12), (0.30, 0.40, 0.14), (0.22, 0.31, 0.10), (0.35, 0.42, 0.16), (0.40, 0.42, 0.14)]
IMG_CHESTNUT = S.spray_atlas("A_ChestnutSprays", CHESTNUT_PAL, 41, S=1024, per_cell=3, nper=4, size=22.0, shape='long')
M_CHESTNUT_L = image_mat("M_ChestnutLeaves", IMG_CHESTNUT, rough=0.75, alpha=True, spec=0.35)
BRAMBLE_PAL = [(0.12, 0.20, 0.08), (0.15, 0.24, 0.09), (0.10, 0.17, 0.07), (0.20, 0.25, 0.10), (0.30, 0.18, 0.12)]
IMG_BRAMBLE = S.spray_atlas("A_BrambleRose", BRAMBLE_PAL, 42, S=1024, per_cell=4, nper=5, size=11.0, shape='ellipse', bark=(0.30, 0.16, 0.12),
                            flowers=[(0.95, 0.72, 0.78), (0.98, 0.85, 0.88), (0.92, 0.62, 0.70), (0.96, 0.94, 0.92)], flower_p=0.18)
M_BRAMBLE = image_mat("M_BrambleRose", IMG_BRAMBLE, rough=0.6, alpha=True, spec=0.4)
GREENS = [(0.36, 0.40, 0.16), (0.42, 0.44, 0.19), (0.32, 0.36, 0.14), (0.48, 0.47, 0.22)]
TIPS = [(0.58, 0.55, 0.30), (0.62, 0.58, 0.34), (0.54, 0.50, 0.28)]
STRAW = [(0.72, 0.64, 0.42), (0.66, 0.58, 0.38)]
IMG_GRASS = S.grass_atlas("A_GrassCards", GREENS, TIPS, STRAW, seed=17, dead_share=0.3, flowers=[(0.90, 0.80, 0.20), (0.85, 0.85, 0.90), (0.60, 0.45, 0.80)])
M_GRASS = image_mat("M_GrassCards", IMG_GRASS, rough=0.85, alpha=True, spec=0.25)
M_BARK = S.bark_mat("M_ChestnutBark", base=srgb((0.30, 0.26, 0.21)), dark=srgb((0.12, 0.10, 0.08)), light=srgb((0.42, 0.38, 0.32)), scale=0.7, green=0.2)
M_SKY = S.sky_mat(zenith=srgb((0.24, 0.45, 0.80)), horizon=srgb((0.80, 0.84, 0.88)), ground=srgb((0.24, 0.32, 0.30)), sun_dir=SUN_DIR,
                  glow=srgb((1.0, 0.92, 0.78)), glow_k=0.5, glow_pow=8.0, clouds=0.25, cloud_col=srgb((0.98, 0.97, 0.95)),
                  cloud_dark=srgb((0.70, 0.74, 0.80)), cloud_scale=0.7, land=srgb((0.36, 0.44, 0.46)), land_h=0.16, strength=1.0, land_detail=0.06, land_scale=1.6)

# ----------------------------------------------------------------------------- terrain
print("terrain ...", flush=True)
near = S.polar_terrain("GroundNear", h, M_EARTH, r_max=14.0, r0=0.08, rings=34, seg=80, uv_disc=True)
far = S.polar_terrain("FarLand", h, M_EARTH.copy(), r_max=160.0, r0=14.0, rings=16, seg=80, r_min=14.0, uv_disc=True)
far.data.materials[0].name = "M_FarLand"
for o in (near, far):
    me = o.data; at = me.attributes.new("worn", 'FLOAT', 'POINT')
    vals = []
    for v in me.vertices:
        x, y = v.co.x, v.co.y
        w = 1.0 - smoothstep(1.2, 3.8, math.hypot(x * 0.8, (y - 1.8) * 0.9))           # the trodden yard before the door
        w = max(w, 1.0 - smoothstep(0.3, 0.9, abs(x - 0.3 + 0.2 * math.sin(y * 0.4))) if -14 < y < 1 else 0.0)  # path down the terraces
        vals.append(w)
    at.data.foreach_set("value", vals)

# terrace walls stepping down to the south, dry stone, and the lake far below between mountains
tw = MB()
for k in range(5):
    y = -3.2 - k * 4.5
    for xa, xb in ((-26.0, -0.5), (1.1, 26.0)):
        n = int((xb - xa) / 0.8)
        for i in range(n):
            x0, x1 = xa + (xb - xa) * i / n, xa + (xb - xa) * (i + 1) / n
            top0 = h(x0, y + 0.05); top1 = h(x1, y + 0.05); bot = h((x0 + x1) / 2, y - 0.5) - 0.1
            p = [Vector((x0, y, bot)), Vector((x1, y, bot)), Vector((x1, y - 0.1, top1 + 0.05)), Vector((x0, y - 0.1, top0 + 0.05))]
            mb_quad(tw, [p[1], p[0], p[3], p[2]], ((x1, bot), (x0, bot), (x0, top0), (x1, top1)))
tw.build("TerraceWalls", M_TERRACE, sway=False)
lake = S.polar_terrain("water.pond.lake", lambda x, y: LAKE_Z, M_LAKE, r_max=1100.0, r0=60.0, rings=8, seg=48, centre=(0.0, -380.0))
mt = MB()

# ----------------------------------------------------------------------------- the cottage
print("cottage ...", flush=True)
cz = h(0, HY0)
WM = MB()
def wall_box(c, size):
    mb_box(WM, c, size)
# south wall with the door and a small window; the other walls whole
for (xa, xb) in ((HX0 + WALL_T, DOOR_X - DOOR_W / 2), (DOOR_X + DOOR_W / 2, HX1 - WALL_T)):
    wall_box(Vector(((xa + xb) / 2, HY0 + WALL_T / 2, cz + WALL_H / 2 - 0.2)), (xb - xa, WALL_T, WALL_H + 0.4))
wall_box(Vector((DOOR_X, HY0 + WALL_T / 2, cz + (DOOR_H + WALL_H + 0.2) / 2)), (DOOR_W, WALL_T, WALL_H + 0.2 - DOOR_H))
wall_box(Vector((0.0, HY1 - WALL_T / 2, cz + WALL_H / 2 - 0.2 + 0.5)), (HX1 - HX0 - 2 * WALL_T, WALL_T, WALL_H + 1.4))
for x in (HX0 + WALL_T / 2, HX1 - WALL_T / 2):
    wall_box(Vector((x, (HY0 + HY1) / 2, cz + WALL_H / 2 - 0.2)), (WALL_T, HY1 - HY0, WALL_H + 0.4))
WM.build("CottageWalls", M_WALL, sway=False)
gb = MB()
for x, sgn in ((HX0, -1), (HX1, 1)):
    p = [Vector((x, HY0 - 0.1, cz + WALL_H)), Vector((x, HY1 + 0.1, cz + WALL_H)), Vector((x, (HY0 + HY1) / 2, cz + WALL_H + 1.25))]
    vs = [gb.vert(q) for q in p]; gb.face(*(vs if sgn > 0 else vs[::-1]))
    p2 = [q + Vector((-sgn * WALL_T, 0, 0)) for q in p]
    vs2 = [gb.vert(q) for q in p2]; gb.face(*(vs2[::-1] if sgn > 0 else vs2))
gb.build("Gables", M_WALL, sway=False)
# the window: a small square opening with a crude plank shutter half open
WX = -2.0
box("WindowRecess", (0.55, WALL_T + 0.02, 0.5), (WX, HY0 + WALL_T / 2, cz + 1.45), M_SOOT)
box("WindowShutter", (0.03, 0.55, 0.52), (WX - 0.3, HY0 - 0.25, cz + 1.45), M_PLANK, rot=(0, 0, math.radians(-30)))
box("WindowLintel", (0.85, 0.3, 0.14), (WX, HY0 + 0.12, cz + 1.78), M_CHESTNUT)
box("DoorLintel", (DOOR_W + 0.5, 0.35, 0.18), (DOOR_X, HY0 + 0.14, cz + DOOR_H + 0.09), M_CHESTNUT)
box("DoorSill", (DOOR_W + 0.1, WALL_T + 0.1, 0.1), (DOOR_X, HY0 + WALL_T / 2, cz + 0.03), noisy("M_SillStone", [srgb((0.5, 0.48, 0.44)), srgb((0.42, 0.40, 0.37))], scale=6, rough=0.8, bump=0.3))
# the door, open inward against the wall
dl = box("Door", (0.05, DOOR_W - 0.06, DOOR_H - 0.06), (DOOR_X - DOOR_W / 2 + 0.06, HY0 + WALL_T + (DOOR_W - 0.06) / 2 - 0.05, cz + DOOR_H / 2), M_PLANK)
dl.rotation_euler = (0, 0, math.radians(-12))
for zz in (0.35, 1.45): box(f"DoorStrap{zz}", (0.06, DOOR_W - 0.2, 0.05), (DOOR_X - DOOR_W / 2 + 0.03, HY0 + WALL_T + (DOOR_W - 0.06) / 2 - 0.05, cz + zz), M_IRON, rot=(0, 0, math.radians(-12)))
# roof: stone slabs (piode) on chestnut rafters, low pitch, eaves projecting
ridge_z = cz + WALL_H + 1.25
rs = MB(); R2 = random.Random(3)
for sgn in (-1, 1):   # the two slopes: north (+1) and south (-1)
    y_eave = HY0 - 0.5 if sgn < 0 else HY1 + 0.5
    y_ridge = (HY0 + HY1) / 2
    rows_n = 9
    for r in range(rows_n):
        t0 = r / rows_n; t1 = (r + 1.35) / rows_n
        ya = y_eave + (y_ridge - y_eave) * t0; yb = y_eave + (y_ridge - y_eave) * min(1.0, t1)
        za = cz + WALL_H - 0.12 + (ridge_z - (cz + WALL_H - 0.12)) * t0; zb = cz + WALL_H - 0.12 + (ridge_z - (cz + WALL_H - 0.12)) * min(1.0, t1)
        x = HX0 - 0.45
        while x < HX1 + 0.45:
            w = R2.uniform(0.45, 0.9); x1 = min(HX1 + 0.45, x + w)
            th = R2.uniform(0.04, 0.07)
            jit = R2.uniform(-0.03, 0.03)
            c = Vector(((x + x1) / 2, (ya + yb) / 2, (za + zb) / 2 + th / 2 + r * 0.004 + jit * 0.3))
            L = math.hypot(yb - ya, zb - za)
            ang = math.atan2(zb - za, yb - ya) * (1 if sgn > 0 else 1)
            mb_box(rs, c, (x1 - x - 0.02, L, th), tilt=((-ang if sgn > 0 else ang), R2.uniform(-0.02, 0.02)))
            x = x1
rs.build("RoofSlabs", M_SLAB, sway=False)
for k in range(9):    # rafter ends under the eaves
    x = HX0 + 0.2 + k * (HX1 - HX0 - 0.4) / 8
    for sgn, y_e in ((-1, HY0 - 0.45), (1, HY1 + 0.45)):
        box(f"Rafter{k}{sgn}", (0.12, 0.7, 0.12), (x, y_e - sgn * 0.3, cz + WALL_H - 0.18 + 0.12), M_CHESTNUT, rot=(sgn * math.radians(-26), 0, 0))
box("Chimney", (0.7, 0.7, 1.2), (HX0 + 1.2, HY1 - 0.4, ridge_z - 0.1), M_WALL)
box("ChimneyCap", (0.9, 0.9, 0.08), (HX0 + 1.2, HY1 - 0.4, ridge_z + 0.55), M_SLAB)

# ----------------------------------------------------------------------------- the room within: dim, earth floor, table, bowls, hearth
ix0, ix1, iy0, iy1 = HX0 + WALL_T, HX1 - WALL_T, HY0 + WALL_T, HY1 - WALL_T
box("RoomFloor", (ix1 - ix0, iy1 - iy0, 0.04), ((ix0 + ix1) / 2, (iy0 + iy1) / 2, cz - 0.02), M_FLOOR)
box("RoomCeiling", (ix1 - ix0, iy1 - iy0, 0.05), ((ix0 + ix1) / 2, (iy0 + iy1) / 2, cz + WALL_H + 0.02), M_CHESTNUT)
for k in range(4): box(f"Beam{k}", (ix1 - ix0, 0.2, 0.22), ((ix0 + ix1) / 2, iy0 + 0.6 + k * 1.15, cz + WALL_H - 0.1), M_CHESTNUT)
TB = Vector((0.4, 6.4, cz))
box("TableTop", (1.6, 0.75, 0.07), (TB.x, TB.y, cz + 0.74), M_CHESTNUT)
for sx in (-1, 1):
    for sy in (-1, 1): box(f"TableLeg{sx}{sy}", (0.08, 0.08, 0.72), (TB.x + sx * 0.68, TB.y + sy * 0.28, cz + 0.36), M_CHESTNUT, rot=(sy * 0.04, sx * 0.04, 0))
box("Bench", (1.4, 0.28, 0.06), (TB.x, TB.y - 0.62, cz + 0.44), M_CHESTNUT)
for sx in (-1, 1): box(f"BenchLeg{sx}", (0.06, 0.24, 0.42), (TB.x + sx * 0.55, TB.y - 0.62, cz + 0.21), M_CHESTNUT)
for k, (dx, dy) in enumerate(((-1.2, 0.1), (1.25, -0.2), (1.1, 0.75))):
    lathe(f"Stool{k}", [(0.0, 0.0), (0.03, 0.0), (0.03, 0.36), (0.16, 0.37), (0.17, 0.42), (0.0, 0.43)], (TB.x + dx, TB.y + dy, cz), M_CHESTNUT, steps=10)
for k in range(5):     # five wooden bowls of thin soup, a dark loaf, a pot
    a = -0.6 + k * 0.3
    bx, by = TB.x - 0.6 + k * 0.3, TB.y + (0.18 if k % 2 else -0.18)
    lathe(f"Bowl{k}", [(0.0, 0.0), (0.04, 0.0), (0.07, 0.03), (0.075, 0.055), (0.068, 0.055), (0.06, 0.03), (0.0, 0.015)], (bx, by, cz + 0.775), M_CHESTNUT, steps=12)
K.sphere("Loaf", 0.11, (TB.x + 0.45, TB.y + 0.05, cz + 0.82), M_BREAD, seg=10, scale=(1.2, 1.0, 0.55))
lathe("Pot", [(0.0, 0.0), (0.09, 0.0), (0.13, 0.08), (0.13, 0.16), (0.10, 0.22), (0.11, 0.24), (0.0, 0.24)], (TB.x - 0.05, TB.y + 0.02, cz + 0.775), M_POT, steps=14)
# the hearth on the back wall: a raised stone floor, a low fire, a chain and pot, a smoke-blackened hood
HZ = Vector((-1.9, iy1 - 0.45, cz))
box("HearthStone", (1.3, 0.8, 0.2), (HZ.x, HZ.y, cz + 0.1), M_TERRACE)
box("HearthHood", (1.4, 0.55, 0.9), (HZ.x, iy1 - 0.25, cz + 1.75), M_SOOT)
box("HearthBack", (1.3, 0.04, 1.4), (HZ.x, iy1 - 0.02, cz + 0.85), M_SOOT)
cr = random.Random(9)
for k in range(10):
    p = (HZ.x + cr.uniform(-0.25, 0.25), HZ.y + cr.uniform(-0.15, 0.15), cz + 0.22 + cr.uniform(0, 0.05))
    K.sphere(f"Ember{k}", cr.uniform(0.03, 0.05), p, M_EMBERS, seg=6, scale=(1.4, 1.0, 0.6))
for k in range(3): tube(f"Log{k}", [Vector((HZ.x - 0.35 + 0.05 * k, HZ.y - 0.1 + 0.1 * k, cz + 0.24)), Vector((HZ.x + 0.35, HZ.y + 0.08 - 0.08 * k, cz + 0.27))], 0.04, M_CHESTNUT, sides=6)
tube("PotChain", [Vector((HZ.x, HZ.y, cz + 1.3)), Vector((HZ.x, HZ.y, cz + 0.62))], 0.008, M_IRON, sides=4)
lathe("Cauldron", [(0.0, 0.0), (0.12, 0.02), (0.17, 0.1), (0.17, 0.2), (0.15, 0.24), (0.0, 0.24)], (HZ.x, HZ.y, cz + 0.38), M_IRON, steps=12)
FIRE = Vector((HZ.x, HZ.y, cz + 0.22))
box("Shelf", (1.2, 0.25, 0.04), (ix1 - 0.2, 7.6, cz + 1.6), M_CHESTNUT, rot=(0, 0, math.pi / 2))
for k in range(3): lathe(f"Jug{k}", [(0.0, 0.0), (0.05, 0.0), (0.07, 0.08), (0.05, 0.16), (0.035, 0.2), (0.0, 0.2)], (ix1 - 0.2, 7.2 + k * 0.35, cz + 1.62), M_POT, steps=10)
# straw heaped in a corner (the children's bed)
st = MB()
for k in range(40):
    p = Vector((ix1 - 0.6 + rng.gauss(0, 0.25), iy0 + 0.6 + rng.gauss(0, 0.25), cz + 0.02))
    mb_box(st, p, (rng.uniform(0.3, 0.6), 0.008, 0.008), yaw=rng.uniform(0, 3.14), tilt=(0, rng.uniform(-0.3, 0.3)))
st.build("StrawLoose", M_STRAW, sway=False)
K.sphere("StrawHeap", 0.6, (ix1 - 0.65, iy0 + 0.65, cz - 0.05), M_STRAW, seg=10, scale=(1.0, 0.9, 0.38))
light_obj("Lamp.fill", 'POINT', 18.0, (1.0, 0.9, 0.78), (DOOR_X, HY0 + WALL_T + 0.6, cz + 1.6), shadow_soft_size=0.5)
light_obj("Lamp.hearth", 'POINT', 60.0, (1.0, 0.5, 0.22), tuple(FIRE + Vector((0.2, -0.3, 0.25))), shadow_soft_size=0.2)

# ----------------------------------------------------------------------------- the dooryard: woodpile, log seat, washing line, barrel
for k in range(18):          # split chestnut logs stacked against the wall, right of the door
    row = k // 6; i = k % 6
    tube(f"Woodpile{k}", [Vector((2.0 + i * 0.22, HY0 - 0.15, cz + 0.12 + row * 0.2)), Vector((2.0 + i * 0.22 + rng.gauss(0, 0.02), HY0 - 0.85, cz + 0.12 + row * 0.2))],
         0.1 + rng.uniform(-0.02, 0.02), M_CHESTNUT, sides=6)
tube("LogSeat", [Vector((-1.6, 2.9, h(-1.6, 2.9) + 0.2)), Vector((-0.6, 3.25, h(-0.6, 3.25) + 0.2))], 0.21, M_BARK, sides=9)
lathe("Barrel", [(0.0, 0.0), (0.26, 0.0), (0.30, 0.3), (0.26, 0.7), (0.0, 0.7)], (-3.0, HY0 - 0.5, cz), M_CHESTNUT, steps=12)
# the washing line from the cottage corner to a pole, with a patched shirt and a child's smock
pole = Vector((-6.5, 1.8, h(-6.5, 1.8)))
tube("LinePole", [pole, pole + Vector((0, 0, 1.95))], 0.04, M_CHESTNUT, sides=6)
a = Vector((HX0 - 0.05, HY0 + 0.2, cz + 1.9)); b_ = pole + Vector((0, 0, 1.9))
tube("Line", [a, a.lerp(b_, 0.5) - Vector((0, 0, 0.12)), b_], 0.005, M_STRAW, sides=3)
wm = MB()
for (t0, t1, drop) in ((0.22, 0.42, 0.75), (0.55, 0.68, 0.5)):
    p0 = a.lerp(b_, t0) - Vector((0, 0, 0.12 * math.sin(math.pi * t0) * 0.9)); p1 = a.lerp(b_, t1) - Vector((0, 0, 0.12 * math.sin(math.pi * t1) * 0.9))
    nu, nv = 6, 6
    rows_ = []
    for j in range(nv + 1):
        v = j / nv
        rows_.append([wm.vert(p0.lerp(p1, i / nu) - Vector((0, 0, drop * v)) + Vector((0, 0.04 * math.sin(i * 1.3 + j), 0)), (i / nu, v), v) for i in range(nu + 1)])
    for j in range(nv):
        for i in range(nu): wm.face(rows_[j][i], rows_[j][i + 1], rows_[j + 1][i + 1], rows_[j + 1][i])
wm.build("cloth.washing.line", M_LINEN)

# ----------------------------------------------------------------------------- vegetation: brambles and the wild rose, grass, chestnut trees
print("vegetation ...", flush=True)
br = MB(); RB = random.Random(11)
def bramble_mound(cx, cy, rx, ry, hgt, n):
    for k in range(n):
        a = RB.uniform(0, 2 * math.pi); d = math.sqrt(RB.random())
        x = cx + math.cos(a) * rx * d; y = cy + math.sin(a) * ry * d
        z = h(x, y) + hgt * (1 - d * d) * RB.uniform(0.5, 1.0)
        out = Vector((math.cos(a), math.sin(a), 0.9 * (1 - d) + 0.3)).normalized()
        tang = out.cross(Vector((0, 0, 1)));
        if tang.length < 0.1: tang = Vector((1, 0, 0))
        tang.normalize(); bit = out.cross(tang).normalized(); roll = RB.uniform(-math.pi, math.pi)
        sz = RB.uniform(0.45, 0.75)
        right = (tang * math.cos(roll) + bit * math.sin(roll)) * sz
        up = (bit * math.cos(roll) - tang * math.sin(roll)) * sz + out * sz * 0.35
        card(br, Vector((x, y, z)) - up * 0.5, right, up, RB.choice(S.QUAD), 0.3, 1.0)
bramble_mound(-1.2, HY0 - 0.45, 0.8, 0.4, 0.9, 55)             # by the door, with the wild rose
bramble_mound(-3.6, 3.0, 1.4, 0.9, 1.1, 70)
bramble_mound(3.6, -2.6, 2.2, 0.8, 0.9, 70)                    # over the terrace edge
bramble_mound(-4.2, -2.9, 1.8, 0.7, 0.8, 55)
bramble_mound(5.0, 6.0, 1.2, 1.6, 1.2, 60)
bo = br.build("veg.shrub.brambles", M_BRAMBLE)
set_card_normals(bo, lambda p: Vector((0, -0.3, 1)).normalized())
# rose canes arching out of the bramble by the door
for k in range(5):
    p0 = Vector((-1.2 + rng.uniform(-0.3, 0.3), HY0 - 0.35, cz))
    p1 = p0 + Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.6, -0.2), rng.uniform(1.2, 1.7)))
    p2 = p1 + Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.5, 0.0), -0.3))
    tube(f"RoseCane{k}", [p0, p0.lerp(p1, 0.6) + Vector((0, 0, 0.2)), p1, p2], [0.012, 0.01, 0.008, 0.005], M_CHESTNUT, sides=4)
gm = MB(); RG = random.Random(13); placed = 0
for i in range(30000):
    r = 13.0 * RG.random() ** 0.8; a = RG.uniform(0, 2 * math.pi); x, y = r * math.sin(a), r * math.cos(a)
    if HX0 - 0.3 < x < HX1 + 0.3 and HY0 - 0.2 < y < HY1 + 0.6: continue
    worn = 1.0 - smoothstep(1.2, 3.8, math.hypot(x * 0.8, (y - 1.8) * 0.9))
    if RG.random() < worn * 1.2: continue
    if abs(x - 0.3) < 0.8 and y < 1: continue
    if any(abs(y - (-3.2 - k * 4.5)) < 0.2 for k in range(4)): continue
    z = h(x, y); sc = RG.uniform(0.6, 1.1)
    to_r = Vector((-x, -y, 0)).normalized(); ya = math.atan2(to_r.y, to_r.x) + math.pi / 2 + RG.gauss(0, 0.5)
    right = Vector((math.cos(ya), math.sin(ya), 0)) * 0.36 * sc
    long_ = RG.random() < 0.35
    cell = RG.choice(S.GRASS_LONG) if long_ else RG.choice(S.GRASS_SHORT + S.GRASS_ROW3)
    card(gm, (x, y, z - 0.02), right, Vector((0, 0, (0.45 if long_ else 0.22) * sc)), cell, 0.0, 1.0)
    placed += 1
    if placed > 1700: break
go = gm.build("veg.grass.yard", M_GRASS)
set_card_normals(go, lambda p: Vector((0, 0, 1)))
# sweet chestnuts: two old trees above the cottage and one by the yard, more on the slopes
trees = [(-6.2, 10.5, 13.0, 6.0, 2), (6.5, 12.0, 14.0, 6.5, 2), (-8.5, -1.0, 11.0, 5.0, 2)]
for k in range(10):
    a = rng.uniform(0, 2 * math.pi); d = rng.uniform(22, 60)
    x, y = math.cos(a) * d, abs(math.sin(a)) * d * 0.9 + 6 if rng.random() < 0.7 else math.sin(a) * d
    if abs(x) < 8 and -25 < y < 14: continue
    trees.append((x, y, rng.uniform(10, 15), rng.uniform(4.5, 6.5), 0))
for k, (x, y, H_, sp, near_) in enumerate(trees):
    S.tree(f"Chestnut{k}", (x, y, h(x, y)), H_, sp, "oak" if k % 2 else "lime", 300 + k, M_BARK, M_CHESTNUT_L,
           nlimbs=6 if near_ else 4, detail=1.0 if near_ else 0.3, cards_per_tip=2 if near_ else 1, card_size=1.5 if near_ else 2.8, fill=90 if near_ else 26)

# ----------------------------------------------------------------------------- sky, light, anchors, sounds
SKY = S.sky_dome(M_SKY, radius=1150.0)
S.world(SUN_DIR, sun_energy=4.6, sun_col=(1.0, 0.93, 0.80), sun_angle=0.8,
        sky_cols=(srgb((0.30, 0.30, 0.24)), srgb((0.74, 0.80, 0.86)), srgb((0.28, 0.46, 0.80))), sky_strength=1.15)
eye, fwd = S.reader((1.2, -1.7, h(1.2, -1.7)), -8.0)
anchor("scene.centre", (DOOR_X, HY0, cz))
anchor("door", (DOOR_X, HY0, cz))
anchor("lake", (0.0, -380.0, LAKE_Z))
S.fx("fire", "hearth", tuple(FIRE), 0.22)
sound("fire", "hearth", tuple(FIRE + Vector((0, -0.4, 0.3))))
sound("birds", "chestnuts", (-6.2, 10.5, 8.0))
sound("wind-trees", "chestnut", (6.5, 12.0, 7.0))
sound("birds", "brambles", (3.6, -2.6, 0.8))
page = S.page_preview(eye, fwd)
cams = S.view_cams(eye, -8.0, extra=[
    ("Cam_Page", eye, eye + fwd * 10 + Vector((0, 0, -1.2)), 17),
    ("Cam_Door", Vector((0.3, 2.1, h(0.3, 2.1) + 1.4)), Vector((0.3, 6.4, cz + 0.8)), 24),
    ("Cam_Rose", Vector((-0.2, 1.8, h(-0.2, 1.8) + 1.2)), Vector((-1.2, HY0 - 0.4, cz + 0.8)), 30),
    ("Cam_Lake", eye, eye + Vector((0.1, -1.0, -0.22)) * 10, 22),
])
S.finish(ARGS, cams, "como_peasant_cot.gltf", page=page,
         keep_names={"M_GrassCards": "veg.grass.yard", "M_BrambleRose": "veg.shrub.brambles", "M_ChestnutLeaves": "veg.crown.chestnuts",
                     "M_PatchedLinen": "cloth.washing.line", "M_Lake": "water.pond.lake",
                     "M_Earth": "GroundNear", "M_FarLand": "far.land"},
         keep_uv={"M_Earth", "M_FarLand"},
         size_for={"M_Earth": (2048, 256, 1024), "M_FarLand": (1024, 128), "M_FieldStone": (1024, 256, 1024), "M_TerraceStone": (1024, 128, 512),
                   "M_RoofSlabs": (1024, 128, 512), "M_ChestnutTimber": (512, 128, 256), "M_DoorPlanks": (512, 64, 256), "M_ChestnutBark": (512, 128, 256),
                   "M_EarthFloor": (256, 64, 128), "M_Mountains": (512,), "M_Lake": (256, 64), "M_SkyDome": (1024,), "M_PatchedLinen": (256, 64),
                   "M_Straw": (256, 64, 128), "M_Soot": (32,), "M_Embers": (128, 32), "M_Iron": (128, 64)},
         default_size=(256, 64, 128), no_shadow={"M_SkyDome"})
