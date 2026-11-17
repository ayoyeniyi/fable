"""
Fable: inside the pagoda on Malabar Hill, Bombay, at sunset on 20 October 1872 (Around the World in Eighty Days,
chapter 10).

"... the noble pagoda on Malabar Hill, with its two polygonal towers ..." "... he happened to espy the splendid
pagoda on Malabar Hill, and was seized with an irresistible desire to see its interior. He was quite ignorant that ...
even the faithful must not go in without first leaving their shoes outside the door." "... soon lost in admiration of
the splendid Brahmin ornamentation which everywhere met his eyes, when of a sudden he found himself sprawling on the
sacred flagging."

The reader stands just inside the threshold of the mandapa (the pillared hall), shod as Passepartout was, facing the
inner shrine at the far end: a dark doorway framed in carved stone, an oil lamp burning before it, marigold
garlands, brass bells hanging from the ceiling. Round about stand the carved pillars, banded with friezes (lotus,
bead and reel, little shrines), on a floor of worn stone flags; brass oil lamps on stands and in niches flicker. Behind,
through the open doorway, the low sun of the evening falls in across the floor, the shoes of the faithful are left on
the step outside, and below lies the city and the bay. No priests, no people.

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py.

Node names the runtime relies on:
  anchor.reader.entrance (feet just inside the threshold, facing +Y: the shrine), anchor.reader.look,
  anchor.scene.centre (the shrine door), anchor.pagoda.door
  light.sun (SUN, the low evening sun through the doorway behind), light.sky (SUN, dim fill), Lamp.oil.* (POINT, lamps)
  fx.candle.* (the oil lamps' wicks), fx.torch.shrine (the large lamp before the shrine)
  cloth.curtain.shrine (the cloth hanging half across the shrine door), veg.flowers.garlands
  sound.crowd.festival (the Parsee festival below), sound.birds.dusk, sound.candle (via fx)
  SkyDome, far.City

Run headless:
  blender -b -P blender/build_malabar_hill_pagoda.py -- --render --quick --cpu --res 900 --cams reader
  blender -b -P blender/build_malabar_hill_pagoda.py -- --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b1 as S
from scene_kit_b1 import (K, E8, new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound, light_obj, camera,
                          link, smoothstep, lerp, n2, fbm2, orient, card, set_card_normals, az_dir, TWO_PI)

ARGS = S.setup("malabar-hill-pagoda", 1872, "MalabarPagoda", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
X0, X1, Y0, Y1, HGT = -4.6, 4.6, -1.2, 9.6, 5.0
SUN_DIR = (az_dir(185.0) * math.cos(math.radians(9)) + Vector((0, 0, math.sin(math.radians(9))))).normalized()   # from behind, low

def carved_mat(name, base, dark, light, scale=1.0, bands=True):
    """carved sandstone/basalt: friezes as horizontal bands of repeated motifs (bead-and-reel, lotus petals, little
    niches) cut into the surface (bump + dark recesses), weathered, darker where hands and lamp smoke have touched."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-2000, -300))
    n = noise_(nt, co, 2.0 * scale, 6, 0.6, loc=(-1800, 300))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1600, 300)), c4(K.srgb(base)), c4(K.srgb(light)), (-1400, 300))
    hgt = math_(nt, 'MULTIPLY', n.outputs["Fac"], 0.2, (-1400, -1000))
    if bands:
        # bands every 0.45 m: within a band, motifs repeat round (atan2 for round pillars, x+y for flat faces)
        zb = math_(nt, 'FRACT', math_(nt, 'DIVIDE', s.outputs["Z"], 0.45, (-1800, 0)), None, (-1650, 0))
        inband = math_(nt, 'MULTIPLY', maprange(nt, zb, 0.12, 0.16, 0, 1, (-1500, 0)), maprange(nt, zb, 0.5, 0.46, 0, 1, (-1500, -100)), (-1350, -50))
        uu = math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-1800, -200))
        motif = math_(nt, 'SINE', math_(nt, 'MULTIPLY', uu, 40.0 * scale, (-1650, -200)), None, (-1500, -200))
        petal = math_(nt, 'SINE', math_(nt, 'ADD', math_(nt, 'MULTIPLY', uu, 20.0 * scale, (-1650, -350)), math_(nt, 'MULTIPLY', zb, 9.0, (-1650, -450)), (-1500, -400)), None, (-1350, -400))
        carve = math_(nt, 'MULTIPLY', inband, maprange(nt, math_(nt, 'MAXIMUM', motif, petal, (-1250, -300)), -0.2, 0.6, 0, 1, (-1150, -300)), (-1000, -200))
        rim = maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', zb, 0.1, (-1500, -600)), None, (-1350, -600)), 0.03, 0.0, 0, 1, (-1200, -600))
        col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', inband, carve, (-900, -250)), 0.55, (-800, -250)), col, c4(K.srgb(dark)), (-700, 300))
        hgt = math_(nt, 'ADD', hgt, math_(nt, 'ADD', carve, math_(nt, 'MULTIPLY', rim, 0.6, (-1000, -700)), (-900, -700)), (-750, -800))
    soot = maprange(nt, s.outputs["Z"], 2.0, 4.8, 0, 0.35, (-1200, -900))
    col = mix_rgb(nt, 'MULTIPLY', soot, col, c4(K.srgb((0.30, 0.26, 0.22))), (-500, 300))
    col = K.ao_mul(nt, col, 0.12, 0.5, (-350, -1100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, hgt, 0.8, 0.012)
    return m

def flagging_mat(name="M_Flagging"):
    """the sacred flagging: big squared stone slabs, worn smooth and darker along the path to the shrine, oiled and
    a little glossy where lamps have stood, joints dark."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1800, -300))
    br = node(nt, "ShaderNodeTexBrick", (-1400, 0)); br.offset = 0.0
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 0.9; br.inputs["Row Height"].default_value = 0.9
    br.inputs["Mortar Size"].default_value = 0.01; br.inputs["Color1"].default_value = (1, 1, 1, 1); br.inputs["Color2"].default_value = (0, 0, 0, 1)
    hv = node(nt, "ShaderNodeCombineXYZ", (-1600, 0)); nt.links.new(s.outputs["X"], hv.inputs["X"]); nt.links.new(s.outputs["Y"], hv.inputs["Y"])
    nt.links.new(hv.outputs[0], br.inputs["Vector"])
    bs = node(nt, "ShaderNodeSeparateColor", (-1200, 0)); nt.links.new(br.outputs["Color"], bs.inputs["Color"])
    slab = ramp(nt, [(0.0, c4(K.srgb((0.30, 0.28, 0.26)))), (0.5, c4(K.srgb((0.40, 0.37, 0.33)))), (1.0, c4(K.srgb((0.34, 0.30, 0.27))))], (-1000, 0))
    nt.links.new(bs.outputs[0], slab.inputs["Fac"])
    n = noise_(nt, co, 1.5, 5, 0.6, loc=(-1400, -300))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, slab.outputs["Color"], maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.8, 1.08, (-1200, -300)), (-800, 0))
    path = maprange(nt, math_(nt, 'ABSOLUTE', s.outputs["X"], None, (-1400, -500)), 0.4, 1.2, 0.75, 1.0, (-1200, -500))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, path, (-650, 0))
    col = mix_rgb(nt, 'MIX', br.outputs["Fac"], col, c4(K.srgb((0.10, 0.09, 0.08))), (-500, 0))
    col = K.ao_mul(nt, col, 0.2, 0.4, (-350, -800))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, path, 0.4, 0.75, (-500, -400)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'ADD', math_(nt, 'MULTIPLY', br.outputs["Fac"], -1.0, (-600, -1000)), math_(nt, 'MULTIPLY', n.outputs["Fac"], 0.3, (-600, -1100)), (-450, -1050)), 0.4, 0.01)
    return m

print("materials ...", flush=True)
M_FLOOR = flagging_mat()
M_PILLAR = carved_mat("M_CarvedPillar", (0.50, 0.40, 0.30), (0.16, 0.12, 0.09), (0.60, 0.50, 0.38), scale=1.0)
M_WALL = carved_mat("M_CarvedWall", (0.46, 0.38, 0.30), (0.15, 0.11, 0.09), (0.56, 0.47, 0.36), scale=0.7)
M_CEIL = carved_mat("M_Ceiling", (0.40, 0.33, 0.26), (0.12, 0.09, 0.07), (0.50, 0.42, 0.32), scale=1.2, bands=False)
M_BASALT = carved_mat("M_Basalt", (0.16, 0.15, 0.14), (0.04, 0.04, 0.04), (0.24, 0.22, 0.20), scale=1.4)
M_BRASS = K.noisy("M_Brass", [K.srgb((0.70, 0.50, 0.22)), K.srgb((0.55, 0.38, 0.15)), K.srgb((0.40, 0.30, 0.15))], scale=10, rough=0.3, bump=0.05, metallic=1.0)
M_OIL = plain("M_LampFlame", (1.0, 0.7, 0.3), emission=(1.0, 0.62, 0.25), strength=25.0)
M_MARIGOLD = K.noisy("M_Marigold", [K.srgb((0.95, 0.55, 0.05)), K.srgb((0.90, 0.40, 0.03)), K.srgb((0.98, 0.70, 0.12))], scale=60, rough=0.8, bump=0.6)
M_CLOTH = K.noisy("M_ShrineCloth", [K.srgb((0.70, 0.12, 0.08)), K.srgb((0.60, 0.08, 0.06)), K.srgb((0.85, 0.55, 0.10))], scale=8, rough=0.85, bump=0.2, stretch=(1, 1, 6))
M_DARK = plain("M_SanctumDark", (0.015, 0.012, 0.01), rough=1.0)
M_LEATHER = K.noisy("M_Sandals", [K.srgb((0.32, 0.20, 0.10)), K.srgb((0.20, 0.12, 0.06))], scale=20, rough=0.6, bump=0.2)
M_KUMKUM = plain("M_Kumkum", K.srgb((0.75, 0.10, 0.06)), rough=0.8)
M_SKY = S.gradient_sky_mat("M_SkyDome", [(0.0, (0.95, 0.55, 0.30)), (0.08, (0.92, 0.66, 0.42)), (0.25, (0.55, 0.55, 0.62)), (1.0, (0.20, 0.30, 0.55))],
                           sun_dir=SUN_DIR, glow=((1.6, 0.8, 0.35), 10.0), clouds=0.3, cloud_col=(0.95, 0.60, 0.45))
M_CITY = K.noisy("M_FarCity", [K.srgb((0.45, 0.35, 0.30)), K.srgb((0.60, 0.48, 0.38)), K.srgb((0.30, 0.25, 0.22))], scale=0.4, rough=1.0, bump=0.0)
M_BAY = S.water_mat("M_Bay", deep=(0.10, 0.10, 0.12), rough=0.1)

# ----------------------------------------------------------------------------- the hall: walls, floor, flat stone ceiling on beams, the doorway behind
print("hall ...", flush=True)
box("Floor", (X1 - X0, Y1 - Y0 + 1.0, 0.2), (0, (Y0 + Y1) / 2 + 0.5, -0.1), M_FLOOR)
box("Plinth", (X1 - X0 + 2, 3.0, 0.5), (0, Y0 - 1.6, -0.35), M_FLOOR)
for sd in (-1, 1):
    box(f"SideWall{sd}", (0.6, Y1 - Y0 + 1.0, HGT), (sd * (X1 + 0.3), (Y0 + Y1) / 2, HGT / 2), M_WALL)
box("Ceiling", (X1 - X0 + 1, Y1 - Y0 + 1.0, 0.3), (0, (Y0 + Y1) / 2, HGT + 0.15), M_CEIL)
# the entrance wall behind with its doorway (the reader has just come in)
DOOR_W, DOOR_H = 2.0, 3.2
for sd in (-1, 1):
    box(f"EntranceWall{sd}", ((X1 - X0 - DOOR_W) / 2, 0.8, HGT), (sd * (DOOR_W / 2 + (X1 - X0 - DOOR_W) / 4), Y0 - 0.4, HGT / 2), M_WALL)
    box(f"DoorJamb{sd}", (0.35, 0.9, DOOR_H), (sd * (DOOR_W / 2 + 0.1), Y0 - 0.4, DOOR_H / 2), M_BASALT)
box("EntranceLintel", (DOOR_W + 0.8, 0.9, HGT - DOOR_H), (0, Y0 - 0.4, DOOR_H + (HGT - DOOR_H) / 2), M_WALL)
box("DoorLintelStone", (DOOR_W + 0.9, 0.95, 0.4), (0, Y0 - 0.4, DOOR_H + 0.2), M_BASALT)
box("Threshold", (DOOR_W, 0.9, 0.12), (0, Y0 - 0.4, 0.06), M_BASALT)
# the far wall with the inner shrine's door (garbhagriha): a dark sanctum behind a carved frame
SH_W, SH_H = 1.4, 2.4
for sd in (-1, 1):
    box(f"ShrineWall{sd}", ((X1 - X0 - SH_W) / 2, 0.8, HGT), (sd * (SH_W / 2 + (X1 - X0 - SH_W) / 4), Y1 + 0.4, HGT / 2), M_WALL)
    for k in range(3):   # the stepped jambs, carved
        box(f"ShrineJamb{sd}{k}", (0.18, 0.25 + k * 0.1, SH_H + 0.2 + k * 0.25), (sd * (SH_W / 2 + 0.09 + k * 0.18), Y1 - 0.05 - k * 0.05, (SH_H + 0.2 + k * 0.25) / 2), M_BASALT)
box("ShrineAbove", (SH_W + 0.8, 0.8, HGT - SH_H), (0, Y1 + 0.4, SH_H + (HGT - SH_H) / 2), M_WALL)
box("ShrineLintel", (SH_W + 1.2, 0.5, 0.45), (0, Y1 - 0.15, SH_H + 0.45), M_BASALT)
box("Sanctum", (SH_W, 1.6, SH_H), (0, Y1 + 1.2, SH_H / 2), M_DARK)
box("ShrineStep", (SH_W + 1.0, 0.6, 0.18), (0, Y1 - 0.35, 0.09), M_BASALT)
# the image within: a dark stone form (a lingam on its yoni base), barely seen, kumkum and flowers on it
lathe("Lingam", [(0.0, 0.0), (0.42, 0.0), (0.42, 0.18), (0.16, 0.2), (0.15, 0.62), (0.08, 0.74), (0.0, 0.76)], (0.0, Y1 + 1.2, 0.0), M_BASALT, steps=18)
# a cloth hung half across the shrine door
CL = MB()
card(CL, (-0.25, Y1 - 0.12, SH_H - 0.05), Vector((0.9, 0, 0)), Vector((0, 0, -1.9)), (0, 0, 1, 1), 0.0, 1.0, segs=4, bend=Vector((0, -0.05, 0)))
co_ = CL.build("ShrineCloth", M_CLOTH)
# a ceiling of carved panels on stone beams resting on the pillars
for k in range(5):
    box(f"Beam{k}", (X1 - X0, 0.4, 0.4), (0, Y0 + 0.9 + k * 2.3, HGT - 0.2), M_BASALT)
for sd in (-1, 1):
    box(f"BeamL{sd}", (0.4, Y1 - Y0, 0.4), (sd * 1.9, (Y0 + Y1) / 2, HGT - 0.2), M_BASALT)

# ----------------------------------------------------------------------------- the pillars: square base, octagonal and round banded shaft, bracket capital
print("pillars ...", flush=True)
PILLARS = [(sx * 1.9, y) for sx in (-1, 1) for y in (1.2, 3.5, 5.8, 8.1)] + [(sx * 3.7, y) for sx in (-1, 1) for y in (2.35, 6.95)]
for k, (x, y) in enumerate(PILLARS):
    box(f"PillarBase{k}", (0.62, 0.62, 0.7), (x, y, 0.35), M_PILLAR, bevel=0.03)
    box(f"PillarBaseMould{k}", (0.7, 0.7, 0.12), (x, y, 0.06), M_BASALT, bevel=0.02)
    lathe(f"PillarShaft{k}", [(0.0, 0.7), (0.26, 0.7), (0.26, 1.2), (0.30, 1.28), (0.30, 1.34), (0.24, 1.42), (0.24, 2.3), (0.29, 2.4), (0.31, 2.5),
                              (0.24, 2.62), (0.22, 3.4), (0.32, 3.55), (0.36, 3.72), (0.30, 3.82), (0.0, 3.82)], (x, y, 0.0), M_PILLAR, steps=8)
    box(f"PillarCap{k}", (0.8, 0.8, 0.3), (x, y, 3.97), M_PILLAR, bevel=0.03)
    for sd in (-1, 1):   # bracket arms (corbels) toward the beams
        box(f"Corbel{k}{sd}", (0.3, 0.9, 0.22), (x, y + sd * 0.55, 4.25), M_BASALT, bevel=0.03)
    box(f"PillarTop{k}", (0.6, 0.6, 0.48), (x, y, 4.56), M_PILLAR)

# ----------------------------------------------------------------------------- lamps, bells, garlands, offerings; the shoes outside
print("lamps ...", flush=True)
LAMPS = []
def deepa(x, y, z0, tall=1.0):
    """a brass standing lamp (samai): a ringed stem on a round foot, a dish of oil with five wicks on top."""
    lathe("Samai", [(0.0, 0.0), (0.16, 0.0), (0.16, 0.03), (0.06, 0.08), (0.03, 0.12), (0.025, 0.9 * tall), (0.05, 0.93 * tall), (0.025, 0.96 * tall),
                    (0.025, 1.08 * tall), (0.14, 1.12 * tall), (0.16, 1.16 * tall), (0.0, 1.13 * tall)], (x, y, z0), M_BRASS, steps=14)
    for k in range(5):
        a = TWO_PI * k / 5
        p = Vector((x + math.cos(a) * 0.13, y + math.sin(a) * 0.13, z0 + 1.17 * tall))
        cyl("Flame", 0.012, 0.05, tuple(p + Vector((0, 0, 0.02))), M_OIL, verts=6, r2=0.002)
        if k == 0: LAMPS.append(p + Vector((0, 0, 0.05)))
deepa(-0.9, Y1 - 0.6, 0.0, 1.0)
deepa(0.9, Y1 - 0.6, 0.0, 1.0)
deepa(-3.2, 4.6, 0.0, 0.85)
deepa(3.2, 4.6, 0.0, 0.85)
# small clay-and-brass oil lamps on the shrine step and in wall niches
for k, (x, y, z) in enumerate(((-0.4, Y1 - 0.35, 0.18), (0.4, Y1 - 0.35, 0.18), (-X1 + 0.08, 2.4, 1.6), (X1 - 0.08, 2.4, 1.6), (-X1 + 0.08, 7.0, 1.6), (X1 - 0.08, 7.0, 1.6))):
    if abs(x) > 4:
        sd = 1 if x > 0 else -1
        box(f"Niche{k}", (0.12, 0.6, 0.7), (sd * (X1 - 0.05), y, z + 0.3), M_DARK)
    lathe(f"Diya{k}", [(0.0, 0.0), (0.05, 0.0), (0.07, 0.03), (0.06, 0.04), (0.0, 0.03)], (x - 0.04 * (1 if x > 0 else -1) * (abs(x) > 4), y, z), M_BRASS, steps=10)
    cyl("Flame", 0.01, 0.04, (x - 0.04 * (1 if x > 0 else -1) * (abs(x) > 4), y, z + 0.06), M_OIL, verts=6, r2=0.002)
    LAMPS.append(Vector((x, y, z + 0.08)))
# brass bells hanging from the beams on chains
for k, (x, y) in enumerate(((-0.8, 0.9), (0.8, 0.9), (0.0, Y1 - 1.3))):
    z = HGT - 0.4
    tube(f"BellChain{k}", [Vector((x, y, z)), Vector((x, y, z - 1.3))], [0.008, 0.008], M_BRASS, sides=4, caps=False)
    lathe(f"TempleBell{k}", [(0.0, 0.0), (0.12, 0.0), (0.13, 0.03), (0.10, 0.12), (0.06, 0.24), (0.03, 0.27), (0.0, 0.28)], (x, y, z - 1.62), M_BRASS, steps=16)
# marigold garlands: swags across the shrine lintel and round the pillars nearest the shrine
GAR = MB()
def garland(name, a, b_, sag, r=0.045, n=26):
    pts = []
    for i in range(n + 1):
        t = i / n; p = a.lerp(b_, t) - Vector((0, 0, sag * math.sin(math.pi * t)))
        pts.append(p)
    o = tube(name, pts, [r] * len(pts), M_MARIGOLD, sides=8)
    return o
garland("GarlandShrine", Vector((-1.2, Y1 - 0.2, SH_H + 0.3)), Vector((1.2, Y1 - 0.2, SH_H + 0.3)), 0.45)
garland("GarlandShrine2", Vector((-0.9, Y1 - 0.25, SH_H + 0.25)), Vector((0.9, Y1 - 0.25, SH_H + 0.25)), 0.25, r=0.035)
for k, (x, y) in enumerate(((-1.9, 8.1), (1.9, 8.1))):
    for j in range(2):
        a0 = j * math.pi
        garland(f"PillarGarland{k}{j}", Vector((x + math.cos(a0) * 0.33, y + math.sin(a0) * 0.33, 2.55)), Vector((x - math.cos(a0) * 0.33, y - math.sin(a0) * 0.33, 2.55)), 0.3, r=0.035)
# offerings on the shrine step: flowers on a brass plate, a kumkum dish
cyl("Thali", 0.18, 0.02, (0.0, Y1 - 0.4, 0.2), M_BRASS, verts=20)
for k in range(10):
    a = k * 0.6
    sphere("Bloom", 0.03, (math.cos(a) * 0.1, Y1 - 0.4 + math.sin(a) * 0.1, 0.23), M_MARIGOLD, seg=8)
sphere("Kumkum", 0.03, (0.06, Y1 - 0.4, 0.22), M_KUMKUM, seg=8, scale=(1, 1, 0.5))
# the shoes of the faithful left on the step outside the door
R = random.Random(20)
for k in range(9):
    x = R.uniform(-1.6, 1.6); y = Y0 - 1.4 + R.uniform(-0.4, 0.4)
    for sd in (-1, 1):
        o = sphere("Sandal", 1.0, (x + sd * 0.06, y, -0.1 + 0.015), M_LEATHER, seg=8, scale=(0.045, 0.12, 0.015))
        o.rotation_euler = (0, 0, R.uniform(-0.6, 0.6))

# ----------------------------------------------------------------------------- outside: the hill falls to the city and the bay in the evening light
print("outside ...", flush=True)
def far_city():
    bm = bmesh.new()
    for k in range(260):
        a = math.radians(R.uniform(140, 220)); r = R.uniform(60, 600)
        x, y = r * math.sin(a), r * math.cos(a) + Y0
        if r < 80 and abs(x) < 20: continue
        w = R.uniform(5, 18); d = R.uniform(5, 18); h = R.uniform(4, 14)
        z0 = -30 - r * 0.03
        res = bmesh.ops.create_cube(bm, size=1.0)
        for v in res["verts"]:
            v.co = Vector((x + v.co.x * w, y + v.co.y * d, z0 + (v.co.z + 0.5) * h))
    me = bpy.data.meshes.new("FarCity"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("FarCity", me); me.materials.append(M_CITY); link(o)
    return o
far_city()
box("HillTop", (14, 7, 2), (0, Y0 - 4.6, -1.2), M_FLOOR)
for k in range(12):   # a low parapet at the terrace edge, the hill falling away below it
    box(f"Parapet{k}", (1.1, 0.4, 0.6), (-6.6 + k * 1.2, Y0 - 7.9, 0.1), M_BASALT, bevel=0.03)
S.water_surface("Bay", M_BAY, -36.0, lambda x, y: True, extent=2000.0, step=200.0, centre=(0.0, -900.0))
SKY = E8.sky_dome("SkyDome", M_SKY, 1100.0, seg=40, rings=12, el_min=-6.0); SKY.visible_shadow = False

# ----------------------------------------------------------------------------- light
K.apply_transforms()
light_obj("light.sun", 'SUN', 4.0, (1.0, 0.62, 0.34), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(1.2))
skl = light_obj("light.sky", 'SUN', 0.15, (0.75, 0.60, 0.50), (0, 0, 30), direction=(0.1, 0.4, -1.0), angle=math.radians(85))
skl.data.use_shadow = False
L = light_obj("light.door", 'AREA', 140.0, (1.0, 0.72, 0.5), (0, Y0 - 1.0, 2.0), direction=(0, 1, -0.2)); L.data.size = 2.0
for k, p in enumerate(LAMPS):
    light_obj(f"Lamp.oil.{k}", 'POINT', 18.0 if k < 4 else 6.0, (1.0, 0.6, 0.25), tuple(p + Vector((0, 0, 0.05))), shadow_soft_size=0.05)
world = bpy.data.worlds.new("Dusk"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.35, 0.28, 0.25, 1); bg.inputs["Strength"].default_value = 0.4

E8.fx("fx.torch.shrine", tuple(LAMPS[0]), 0.06)
for k, p in enumerate(LAMPS[1:7]): E8.fx(f"fx.candle.{k}", tuple(p), 0.02)
sound("crowd", "festival", (0.0, Y0 - 40.0, -20.0)); sound("birds", "dusk", (-6.0, Y0 - 8.0, 4.0))
S.reader_anchors(0.0)
anchor("scene.centre", (0.0, Y1, 1.2))
anchor("pagoda.door", (0.0, Y0 - 0.4, 0.0))
S.check_clear(look_yaw=0.0)
E = Vector((0, 0, EYE))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EYE), 17),
    ("Cam_Shrine", (0.0, 5.5, 1.5), (0.0, Y1, 1.3), 24),
    ("Cam_Pillar", (-0.9, 2.5, 1.7), (-1.9, 3.5, 2.6), 24),
], pitch=0.0)
S.finish("malabar-hill-pagoda", "malabar_hill_pagoda", cams,
         keep_names={"M_ShrineCloth": "cloth.curtain.shrine", "M_Marigold": "MESH_Garlands", "M_SkyDome": "SkyDome", "M_FarCity": "far.City", "M_Bay": "far.Bay"},
         size_for={"M_Flagging": (2048, 256, 1024), "M_CarvedPillar": (2048, 128, 1024), "M_CarvedWall": (2048, 128, 1024), "M_Ceiling": (1024, 64, 512),
                   "M_Basalt": (1024, 64, 512), "M_Brass": (256, 64, 128), "M_LampFlame": (32,), "M_Marigold": (256, 32, 128), "M_ShrineCloth": (256, 32, 128),
                   "M_SanctumDark": (32,), "M_Sandals": (64, 32), "M_Kumkum": (32,), "M_FarCity": (256, 32), "M_SkyDome": (1024,)},
         page=page, default_exposure=0.5, unlit_emit={"M_LampFlame"})
