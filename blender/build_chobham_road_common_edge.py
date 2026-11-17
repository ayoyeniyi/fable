"""
Fable: the road onto Horsell Common at twilight (The War of the Worlds, book I, chapter 6, "The Heat-Ray in the
Chobham Road").

"... the road from Horsell ... runs out at last upon the common"; "Where the road grows narrow and black between the
high banks"; "the beech trees that line the road"; "the house nearest the corner". A Friday evening in August, about
half past eight: the shop people of Woking have walked out to see the Thing, and have just fled.

The reader stands in the middle of a sandy, rutted lane between high banks topped with hawthorn hedges, under the
beeches that line the road, beside the corner house (a red-brick villa with a gable, sash windows and a slate roof).
Ahead the lane opens onto the heath, a heathery hummock of sand between the road and the pits; far across the
darkening common the sand pits, and above them, a thin mast with the Martians' spinning mirror, a silhouette only.
In the lane, the traces of the crowd that ran: a straw boater, a bowler, a dropped parasol, hoof prints and wheel
ruts in the sand. Twilight after sunset: a deep blue sky with the first stars, a greenish afterglow low in the west.
No tripods, no Martians, no soldiers, no street lamps.

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py.

Node names the runtime relies on:
  anchor.reader.entrance (feet in the lane, facing +Y: north, up the lane to the common), anchor.reader.look,
  anchor.scene.centre (the lane's mouth), anchor.common.mirror (the mirror on its mast over the pits)
  light.dusk (SUN, the afterglow from the west, no hard shadow), light.sky (SUN, sky fill), Lamp.villa (POINT, a lamp
  lit in the villa's front room)
  veg.crown.beech, veg.shrub.hedge (cards), veg.grass.bank, MESH_HedgeMass (opaque), veg.shrub.heather
  sound.wind-trees.beeches, sound.crowd.distant (the crowd fled toward Woking), sound.birds.dusk
  SkyDome, far.Heath (backdrop)

Run headless:
  blender -b -P blender/build_chobham_road_common_edge.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_chobham_road_common_edge.py -- --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b1 as S
from scene_kit_b1 import (K, E8, new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound, light_obj, camera,
                          link, smoothstep, lerp, n2, fbm2, orient, card, plant, set_card_normals, az_dir, TWO_PI)

ARGS = S.setup("chobham-road-common-edge", 1898, "ChobhamRoad", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
DUSK_AZ, DUSK_EL = 300.0, 12.0            # the afterglow, west-north-west, low
DUSK_DIR = (az_dir(DUSK_AZ) * math.cos(math.radians(DUSK_EL)) + Vector((0, 0, math.sin(math.radians(DUSK_EL))))).normalized()
LANE_HALF = 2.5
MOUTH = 13.0                              # the lane opens onto the common here
PIT = Vector((-30.0, 260.0, 0))

def lane_cx(y): return 0.25 * math.sin(y * 0.06)
def bank_h(y): return 1.5 * smoothstep(MOUTH + 4.0, MOUTH - 2.0, y)        # the high banks fall away at the mouth
def H(x, y):
    d = abs(x - lane_cx(y))
    z = 0.0
    bh = bank_h(y)
    z += bh * smoothstep(LANE_HALF + 0.2, LANE_HALF + 1.4, d)                  # the banks
    z += 0.3 * n2(x, y, 3.0, 2.0) * smoothstep(LANE_HALF, LANE_HALF + 1.5, d)
    # the common beyond: gentle heath, the hummock of heathery sand ahead-left
    common = smoothstep(MOUTH - 4, MOUTH + 6, y)
    z += common * (0.6 * n2(x, y, 18.0, 4.0) + 0.25 * n2(x, y, 5.0, 7.0))
    z += 2.2 * math.exp(-(((x + 9.0) / 9.0) ** 2 + ((y - 34.0) / 7.0) ** 2))
    z -= 0.06 * smoothstep(0.6, 0.1, abs(abs(x - lane_cx(y)) - 0.8)) * (1 - common)   # cart ruts
    return z
Z0 = H(0, 0)
def gz(x, y): return H(x, y) - Z0
S.set_ground(gz)

def lane_fn(x, y): return smoothstep(LANE_HALF + 0.6, LANE_HALF - 0.2, abs(x - lane_cx(y))) * smoothstep(MOUTH + 25, MOUTH + 10, y) + \
    smoothstep(1.6, 0.8, abs(x - lane_cx(y))) * smoothstep(MOUTH + 10, MOUTH + 25, y) * smoothstep(120, 80, y)
def heath_fn(x, y): return smoothstep(MOUTH - 3, MOUTH + 5, y) * (1 - lane_fn(x, y))
def rut_fn(x, y): return smoothstep(0.35, 0.05, abs(abs(x - lane_cx(y)) - 0.8)) * lane_fn(x, y)

def ground_mat(name="M_LaneGround"):
    """the lane: soft yellow-grey Bagshot sand and gravel, rutted, scattered with pebbles, hoof prints along the
    middle; the banks: dry grass, moss, bare sand where they're cut; the heath: purple-brown ling, sand showing in
    paths. Colour by the 'lane' and 'heath' attributes."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    al = node(nt, "ShaderNodeAttribute", (-2000, 700)); al.attribute_name = "lane"
    ah = node(nt, "ShaderNodeAttribute", (-2000, 550)); ah.attribute_name = "heath"
    ar = node(nt, "ShaderNodeAttribute", (-2000, 400)); ar.attribute_name = "rut"
    lane, heath, rut = al.outputs["Fac"], ah.outputs["Fac"], ar.outputs["Fac"]
    n = noise_(nt, co, 0.6, 5, 0.6, loc=(-1800, 200))
    fine = noise_(nt, co, 30.0, 3, 0.7, loc=(-1800, 0))
    peb = voronoi_(nt, co, 18.0, 'F1', (-1800, -200))
    psep = node(nt, "ShaderNodeSeparateColor", (-1600, -200)); nt.links.new(peb.outputs["Color"], psep.inputs["Color"])
    pebble = math_(nt, 'MULTIPLY', maprange(nt, peb.outputs["Distance"], 0.22, 0.12, 0, 1, (-1500, -250)), maprange(nt, psep.outputs[0], 0.75, 0.8, 0, 1, (-1500, -350)), (-1350, -300))
    sand = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1600, 200)), c4(K.srgb((0.52, 0.45, 0.33))), c4(K.srgb((0.64, 0.56, 0.42))), (-1400, 200))
    sand = mix_rgb(nt, 'MULTIPLY', 1.0, sand, maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0.85, 1.08, (-1600, 0)), (-1250, 150))
    sand = mix_rgb(nt, 'MIX', pebble, sand, c4(K.srgb((0.42, 0.36, 0.30))), (-1100, 150))
    sand = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', rut, 0.35, (-1200, 400)), sand, (0.7, 0.66, 0.6, 1), (-950, 150))
    # hoof prints: little dark crescents along the middle of the lane
    hv = voronoi_(nt, co, 3.0, 'F1', (-1800, -500))
    hoof = math_(nt, 'MULTIPLY', maprange(nt, hv.outputs["Distance"], 0.09, 0.05, 0, 1, (-1600, -500)), math_(nt, 'MULTIPLY', lane, maprange(nt, rut, 0.3, 0.0, 0, 1, (-1600, -650)), (-1450, -600)), (-1350, -550))
    sand = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', hoof, 0.5, (-1200, -550)), sand, (0.55, 0.5, 0.45, 1), (-850, 150))
    # bank turf: blade streaks, dry
    mp = node(nt, "ShaderNodeMapping", (-1800, 900)); mp.inputs["Scale"].default_value = (12.0, 3.0, 12.0); mp.inputs["Rotation"].default_value = (0, 0, 0.5)
    nt.links.new(co, mp.inputs["Vector"])
    bl = noise_(nt, mp.outputs["Vector"], 8.0, 3, 0.6, 1.2, (-1600, 900))
    turf = ramp(nt, [(0.0, c4(K.srgb((0.14, 0.16, 0.07)))), (0.5, c4(K.srgb((0.30, 0.32, 0.14)))), (0.8, c4(K.srgb((0.50, 0.46, 0.26)))), (1.0, c4(K.srgb((0.60, 0.54, 0.34))))], (-1400, 900))
    nt.links.new(bl.outputs["Fac"], turf.inputs["Fac"])
    heathc = ramp(nt, [(0.0, c4(K.srgb((0.14, 0.11, 0.10)))), (0.5, c4(K.srgb((0.30, 0.20, 0.24)))), (0.8, c4(K.srgb((0.42, 0.28, 0.34)))), (1.0, c4(K.srgb((0.30, 0.30, 0.16))))], (-1400, 1100))
    hn = noise_(nt, co, 4.0, 5, 0.7, loc=(-1600, 1100)); nt.links.new(hn.outputs["Fac"], heathc.inputs["Fac"])
    col = mix_rgb(nt, 'MIX', heath, turf.outputs["Color"], heathc.outputs["Color"], (-1000, 900))
    col = mix_rgb(nt, 'MIX', lane, col, sand, (-700, 500))
    col = K.ao_mul(nt, col, 0.3, 0.35, (-500, -900))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
    b.inputs["Specular IOR Level"].default_value = 0.2
    hgt = mix_f(nt, lane, math_(nt, 'ADD', bl.outputs["Fac"], hn.outputs["Fac"], (-800, -1200)), math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', pebble, 0.6, (-800, -1300)), hoof, (-700, -1300)), (-500, -1250))
    bump_from(nt, b, hgt, 0.4, 0.015)
    return m

print("materials ...", flush=True)
M_GROUND = ground_mat()
M_BEECHBARK = K.noisy("M_BeechBark", [K.srgb((0.40, 0.40, 0.38)), K.srgb((0.48, 0.48, 0.46)), K.srgb((0.30, 0.31, 0.29)), K.srgb((0.35, 0.38, 0.30))], scale=3, rough=0.7, bump=0.08)
M_HEDGEMASS = S.crown_mass_mat("M_HedgeMass", (0.06, 0.10, 0.04), (0.17, 0.25, 0.08), (0.28, 0.36, 0.13), scale=6.0)
M_BEECHMASS = S.crown_mass_mat("M_BeechMass", (0.05, 0.08, 0.03), (0.12, 0.19, 0.06), (0.20, 0.28, 0.09), scale=2.5)
M_BEECH = image_mat("M_BeechLeaves", S.spray_atlas("A_BeechSprays", "beech", 61), rough=0.55, alpha=True)
M_HEDGE = image_mat("M_HedgeSprays", S.spray_atlas("A_HawthornSprays", "hawthorn", 62), rough=0.6, alpha=True)
IMG_PLANTS, CELLS = S.plant_atlas("A_BankPlants", ["tussock", "tallgrass", "fern", "dock", "weed", "grass", "straw", "flowers"], seed=1898,
                                  greens=[(0.16, 0.20, 0.07), (0.22, 0.26, 0.09), (0.28, 0.30, 0.11), (0.14, 0.18, 0.06)],
                                  straw=[(0.55, 0.48, 0.30), (0.48, 0.42, 0.26), (0.62, 0.55, 0.36)])
M_BANKGRASS = image_mat("M_BankGrass", IMG_PLANTS, rough=0.6, alpha=True)
M_HEATHERMASS = S.crown_mass_mat("M_HeatherMass", (0.09, 0.06, 0.07), (0.24, 0.16, 0.20), (0.36, 0.24, 0.30), scale=10.0)
M_BRICK = None
def brick_mat(name="M_VillaBrick"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    br = node(nt, "ShaderNodeTexBrick", (-1200, 0)); br.offset = 0.5
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 0.225; br.inputs["Row Height"].default_value = 0.075
    br.inputs["Mortar Size"].default_value = 0.01
    br.inputs["Color1"].default_value = c4(K.srgb((0.52, 0.22, 0.14))); br.inputs["Color2"].default_value = c4(K.srgb((0.42, 0.17, 0.11)))
    br.inputs["Mortar"].default_value = c4(K.srgb((0.62, 0.58, 0.52)))
    # mapped on X/Z and Y/Z (walls run along both axes): use the larger of the two planar mappings by summing x+y
    sx = sep_xyz(nt, co, (-1600, 0))
    hv = node(nt, "ShaderNodeCombineXYZ", (-1400, 0)); nt.links.new(math_(nt, 'ADD', sx.outputs["X"], sx.outputs["Y"], (-1500, 100)), hv.inputs["X"]); nt.links.new(sx.outputs["Z"], hv.inputs["Y"])
    nt.links.new(hv.outputs[0], br.inputs["Vector"])
    n = noise_(nt, co, 2.0, 4, 0.6, loc=(-1200, -300))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, br.outputs["Color"], maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.75, 1.1, (-1000, -300)), (-800, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    bump_from(nt, b, math_(nt, 'SUBTRACT', 1.0, br.outputs["Fac"], (-700, -500)), 0.4, 0.008)
    return m
M_BRICK = brick_mat()
M_SLATE = K.noisy("M_Slate", [K.srgb((0.20, 0.21, 0.24)), K.srgb((0.26, 0.27, 0.30)), K.srgb((0.16, 0.17, 0.19))], scale=12, rough=0.6, bump=0.2, stretch=(1, 1, 3))
M_WHITE = K.noisy("M_PaintedWood", [K.srgb((0.82, 0.80, 0.74)), K.srgb((0.74, 0.72, 0.66))], scale=10, rough=0.55, bump=0.05)
M_GLASS = plain("M_WindowGlass", (0.03, 0.035, 0.04), rough=0.08)
M_LITGLASS = plain("M_LitWindow", (0.9, 0.62, 0.30), rough=0.3, emission=(1.0, 0.62, 0.28), strength=3.0)
M_STRAW = K.noisy("M_StrawHat", [K.srgb((0.82, 0.72, 0.48)), K.srgb((0.70, 0.60, 0.38))], scale=60, rough=0.8, bump=0.3, stretch=(1, 1, 0.2))
M_FELT = K.noisy("M_FeltHat", [K.srgb((0.06, 0.055, 0.05)), K.srgb((0.10, 0.09, 0.08))], scale=30, rough=0.85, bump=0.1)
M_RIBBON = plain("M_HatBand", K.srgb((0.12, 0.14, 0.30)), rough=0.6)
M_PARASOL = K.noisy("M_Parasol", [K.srgb((0.85, 0.80, 0.78)), K.srgb((0.78, 0.70, 0.70))], scale=40, rough=0.8, bump=0.1)
M_IRON = plain("M_Iron", (0.03, 0.03, 0.03), rough=0.5, metallic=0.8)
M_FAR = K.noisy("M_FarHeath", [K.srgb((0.10, 0.08, 0.09)), K.srgb((0.14, 0.11, 0.12))], scale=0.05, rough=1.0, bump=0.0)
M_PITSAND = K.noisy("M_PitSand", [K.srgb((0.50, 0.44, 0.34)), K.srgb((0.40, 0.35, 0.28))], scale=0.3, rough=1.0, bump=0.0)
M_MAST = plain("M_MirrorMast", (0.05, 0.05, 0.05), rough=0.4, metallic=0.9)
M_MIRROR = plain("M_Mirror", (0.6, 0.62, 0.66), rough=0.08, metallic=1.0)

# ----------------------------------------------------------------------------- terrain
print("ground ...", flush=True)
GROUND = S.ground("Lane", M_GROUND, 120.0, r0=2.2, NA=112, NR=34, attrs={"lane": lane_fn, "heath": heath_fn, "rut": rut_fn})
FAR = S.ring_band("FarHeath", M_FAR, 119.0, 700.0, lambda x, y: gz(x, y) - 0.05, gz(0, 0) - 1.0, seg=72)
# the sand pits far ahead: raw heaps of flung sand on the horizon, the mast and the spinning mirror above
R = random.Random(8)
for k in range(9):
    a = R.uniform(-1, 1)
    sphere(f"PitHeap{k}", 1.0, (PIT.x + a * 26 + R.gauss(0, 3), PIT.y + R.gauss(0, 6), gz(0, 0) - 1.6), M_PITSAND, seg=12,
           scale=(R.uniform(8, 14), R.uniform(5, 9), R.uniform(2.0, 3.5)))
MAST_TOP = Vector((PIT.x, PIT.y, gz(0, 0) + 13.0))
tube("MirrorMast", [Vector((PIT.x, PIT.y, gz(0, 0) - 1.0)), MAST_TOP], [0.12, 0.06], M_MAST, sides=6)
o = cyl("MirrorDisc", 1.3, 0.05, tuple(MAST_TOP + Vector((0, 0, 0.6))), M_MIRROR, verts=20)
o.rotation_euler = (math.radians(80), 0, math.radians(30))

# ----------------------------------------------------------------------------- the banks: hedges on top, beeches
print("hedges ...", flush=True)
HMASS = MB(); HCARDS = MB(); BMASS = MB()
for sd in (-1, 1):
    y = -22.0
    while y < MOUTH - 2.5:
        x = lane_cx(y) + sd * (LANE_HALF + 1.9)
        z = gz(x, y) + 0.2
        if bank_h(y) > 0.3:
            S.lumps(HMASS, Vector((x, y, z + 0.6)), 0.9, 1.15, 4, R, int(y * 10) + sd, sub=1, sway=(0.0, 0.2), flat_bottom=z - 0.45, stretch=(1.0, 1.6))
            # spray cards on the lane side and the top, breaking the clipped line
            for c in range(9 if abs(y) < 20 else 3):
                q = Vector((x - sd * R.uniform(0.6, 0.9), y + R.uniform(-0.8, 0.8), z + R.uniform(0.3, 1.6)))
                out = Vector((-sd, R.gauss(0, 0.3), R.uniform(0.0, 0.6))).normalized()
                tang = out.cross(Vector((0, 0, 1))).normalized(); up = out.cross(tang).normalized()
                sz = R.uniform(0.7, 1.0)
                card(HCARDS, q - up * sz * 0.5, tang * sz, up * sz + out * 0.2, R.choice(S.QUAD), 0.2, 0.8)
        y += R.uniform(1.4, 1.9)
# a continuous low body along each hedge's foot, so no sky shows between the lumps
for sd in (-1, 1):
    pts = []
    for k in range(40):
        y = -22.0 + (MOUTH - 2.5 + 22.0) * k / 39
        x = lane_cx(y) + sd * (LANE_HALF + 1.9)
        pts.append(Vector((x, y, gz(x, y) + 0.35)))
    tube(f"HedgeBase{sd}", pts, [0.75] * len(pts), M_HEDGEMASS, sides=8)
HM = HMASS.build("HedgeMass", M_HEDGEMASS, sway=False)
HC = HCARDS.build("HedgeSprays", M_HEDGE); set_card_normals(HC, lambda p: Vector((0, 0, 1)))
# beeches lining the road, on the banks: great smooth grey trunks, crowns meeting over the lane
for k, (x, y, h, s_) in enumerate(((-4.6, -4.0, 20.0, 7.0), (4.8, 3.0, 22.0, 7.5), (-4.4, 10.0, 21.0, 7.0), (4.6, -12.0, 19.0, 6.5),
                                   (-4.8, -20.0, 20.0, 7.0), (5.0, 15.0, 18.0, 6.5), (-5.0, 24.0, 17.0, 7.0))):
    near = abs(y) < 16
    S.tree(f"Beech{k}", x, y, h, s_, "plane", 900 + k, M_BEECHBARK, "beech", nlimbs=6 if near else 5, detail=1.0 if near else 0.6,
           cards_per_tip=2, card_size=2.6, fill=120 if near else 70, roots=False)
S.build_crowns({"beech": M_BEECH}, names={"beech": "CrownsBeech"})
# grass and ferns on the banks and the lane's verges
GMB = MB(); HEATH = MB()
placed = 0
for i in range(40000):
    x = R.uniform(-9, 9); y = R.uniform(-22, MOUTH + 3)
    d = abs(x - lane_cx(y))
    if d < LANE_HALF - 0.2 or d > LANE_HALF + 1.8: continue
    if math.hypot(x, y) < 1.0: continue
    kind = R.choices(["tussock", "tallgrass", "fern", "dock", "weed", "grass", "flowers"], weights=[3, 2, 2, 1, 1, 3, 0.6])[0]
    h = {"tussock": 0.6, "tallgrass": 0.8, "fern": 0.7, "dock": 0.5, "weed": 0.8, "grass": 0.35, "flowers": 0.45}[kind] * R.uniform(0.8, 1.3)
    plant(GMB, x, y, h, CELLS[kind], R, n=2 if abs(y) < 10 else 1, segs=2, wk=0.6)
    placed += 1
    if placed > 520: break
GO = GMB.build("BankGrass", M_BANKGRASS); set_card_normals(GO, lambda p: Vector((0, 0, 1)))
# the heath beyond the mouth: opaque heather cushions, gorse-dark clumps, thinning into the far land
for k in range(260):
    x = R.uniform(-60, 60); y = R.uniform(MOUTH + 1, 115)
    if lane_fn(x, y) > 0.3 or math.hypot(x, y) > 118: continue
    z = gz(x, y); w = R.uniform(0.6, 1.4) * (1 + y / 80); hh = R.uniform(0.3, 0.6)
    S.lumps(HEATH, Vector((x, y, z + hh * 0.2)), w, hh, 2, R, 3000 + k, sub=1, sway=(0.0, 0.2), flat_bottom=z - 0.05)
HEATH.build("HeatherMass", M_HEATHERMASS, sway=False)

# ----------------------------------------------------------------------------- the corner house: a red-brick villa with a gable to the lane
print("villa ...", flush=True)
VX, VY = -9.0, 6.5                      # front wall along the lane (facing +X), set back behind the bank and hedge
def villa():
    zb = gz(VX - 4, VY) - 0.3
    W, D, EAVE = 9.0, 8.0, 5.8         # W along y (front), D back along -x
    box("VillaBody", (D, W, EAVE), (VX - D / 2, VY, zb + EAVE / 2), M_BRICK)
    # the gable bay toward the lane, rising into a front gable
    box("VillaBay", (1.2, 3.6, EAVE + 0.4), (VX + 0.6, VY + 1.6, zb + (EAVE + 0.4) / 2), M_BRICK)
    rise = 2.4
    gv = [(VX + 1.2, VY + 1.6 - 1.9, zb + EAVE + 0.4), (VX + 1.2, VY + 1.6 + 1.9, zb + EAVE + 0.4), (VX + 1.2, VY + 1.6, zb + EAVE + 0.4 + rise),
          (VX - 1.0, VY + 1.6 - 1.9, zb + EAVE + 0.4), (VX - 1.0, VY + 1.6 + 1.9, zb + EAVE + 0.4), (VX - 1.0, VY + 1.6, zb + EAVE + 0.4 + rise)]
    mesh_from("VillaGable", gv, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1)], M_BRICK)
    for sd in (-1, 1):
        a = Vector((VX + 1.45, VY + 1.6 + sd * 2.15, zb + EAVE + 0.2)); b_ = Vector((VX + 1.45, VY + 1.6, zb + EAVE + 0.4 + rise + 0.15))
        c = Vector((VX - 1.2, VY + 1.6, zb + EAVE + 0.4 + rise + 0.15)); d = Vector((VX - 1.2, VY + 1.6 + sd * 2.15, zb + EAVE + 0.2))
        mesh_from(f"VillaGableRoof{sd}", [a, b_, c, d], [(0, 1, 2, 3)], M_SLATE)
    # the main hipped roof
    zr = zb + EAVE; top = zr + 3.2
    ov = 0.4
    v = [(VX + ov, VY - W / 2 - ov, zr), (VX + ov, VY + W / 2 + ov, zr), (VX - D - ov, VY + W / 2 + ov, zr), (VX - D - ov, VY - W / 2 - ov, zr),
         (VX - D / 2, VY - W / 2 + D / 2, top), (VX - D / 2, VY + W / 2 - D / 2, top)]
    o = mesh_from("VillaRoof", v, [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)], M_SLATE)
    orient(o, lambda c: (c - Vector((VX - D / 2, VY, zr))))
    for cy in (VY - 3.0, VY + 3.2):
        box("VillaChimney", (0.7, 0.9, 2.4), (VX - D / 2, cy, top - 0.4), M_BRICK)
        for k in range(2): cyl("ChimneyPot", 0.12, 0.45, (VX - D / 2, cy - 0.2 + k * 0.4, top + 1.0), M_BRICK, verts=8)
    # sash windows: white painted frames, glass; the front room lit
    def sash(c, lit=False, w=1.0, h=1.7):
        c = Vector(c)
        box("SashGlass", (0.04, w, h), tuple(c), M_LITGLASS if lit else M_GLASS)
        for dz in (-h / 2, 0.0, h / 2):
            box("SashRail", (0.08, w + 0.1, 0.06 if dz else 0.05), tuple(c + Vector((0.03, 0, dz))), M_WHITE)
        for dy in (-w / 2, 0.0, w / 2):
            box("SashStile", (0.08, 0.06 if dy else 0.04, h), tuple(c + Vector((0.03, dy, 0))), M_WHITE)
        box("SashSill", (0.25, w + 0.25, 0.08), tuple(c + Vector((0.08, 0, -h / 2 - 0.06))), M_WHITE)
    sash((VX + 1.21, VY + 1.6, zb + 1.6), lit=True, w=1.4)
    sash((VX + 1.21, VY + 1.6, zb + 4.1), w=1.2, h=1.5)
    sash((VX + 0.01, VY - 2.4, zb + 1.6))
    sash((VX + 0.01, VY - 2.4, zb + 4.1), h=1.5)
    box("VillaDoor", (0.06, 1.0, 2.2), (VX + 0.02, VY + 4.0, zb + 1.1 + 0.3), M_SLATE)
    return Vector((VX + 0.3, VY + 1.6, zb + 1.6))
VILLA_LAMP = villa()
# its front-garden gate in the hedge gap and a low wall
box("GateWall", (0.4, 2.0, 0.9), (lane_cx(6.5) - LANE_HALF - 2.6, 4.2, gz(-5.1, 4.2) + 0.2), M_BRICK)

# ----------------------------------------------------------------------------- the crowd's traces in the lane
print("traces ...", flush=True)
def boater(c, rot):
    o1 = lathe("Boater", [(0.0, 0.08), (0.10, 0.08), (0.10, 0.012), (0.18, 0.01), (0.19, 0.0), (0.0, 0.0)], tuple(c), M_STRAW, steps=24)
    o1.rotation_euler = rot
    o2 = lathe("BoaterBand", [(0.102, 0.012), (0.102, 0.045)], tuple(c), M_RIBBON, steps=24); o2.rotation_euler = rot
def bowler(c, rot):
    o1 = lathe("Bowler", [(0.0, 0.13), (0.06, 0.128), (0.095, 0.10), (0.10, 0.03), (0.13, 0.01), (0.15, 0.025), (0.15, 0.015), (0.0, 0.0)], tuple(c), M_FELT, steps=24)
    o1.rotation_euler = rot
bx, by = 0.9, 4.2;  boater(Vector((bx, by, gz(bx, by) + 0.005)), (0.05, 0.0, 0.3))
bx, by = -1.5, 7.6; bowler(Vector((bx, by, gz(bx, by) + 0.13)), (math.radians(160), 0.2, 0.5))      # upturned
bx, by = 1.6, 9.8;  boater(Vector((bx, by, gz(bx, by) + 0.05)), (math.radians(70), 0.0, 1.2))      # on its edge against the rut
# a dropped parasol, half open, lying in the lane
PX, PY = -0.9, 2.6
pz = gz(PX, PY)
pd = Vector((math.cos(0.5), math.sin(0.5), 0))
tip = Vector((PX, PY, pz + 0.04)); ferrule = tip + pd * 0.85 + Vector((0, 0, 0.14))
tube("ParasolShaft", [tip, ferrule], [0.008, 0.008], M_IRON, sides=5)
tube("ParasolHandle", [ferrule, ferrule + pd * 0.12 + Vector((0, 0, -0.03)), ferrule + pd * 0.14 + Vector((0, 0, -0.08))], [0.012] * 3, M_WHITE, sides=6)
cone = lathe("ParasolCanopy", [(0.0, 0.0), (0.06, -0.04), (0.18, -0.16), (0.26, -0.32), (0.29, -0.42)], (0, 0, 0), M_PARASOL, steps=8)
cone.matrix_world = Matrix.Translation(tip + pd * 0.12) @ (Vector((0, 0, 1)).rotation_difference(-pd.normalized() + Vector((0, 0, 0.16)))).to_matrix().to_4x4()
cone.data.update()

# ----------------------------------------------------------------------------- sky and light: deep blue, a green afterglow low in the west, first stars
M_SKY = S.gradient_sky_mat("M_SkyDome", [(0.0, (0.09, 0.10, 0.13)), (0.06, (0.11, 0.14, 0.20)), (0.2, (0.06, 0.09, 0.20)), (0.5, (0.03, 0.05, 0.14)), (1.0, (0.015, 0.025, 0.08))],
                           sun_dir=DUSK_DIR, glow=((0.30, 0.34, 0.20), 5.0), clouds=0.0, strength=1.0)
# stars: tiny emissive points on the dome would cost geometry; a speckle in the sky material instead
nt = M_SKY.node_tree; bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
src = bsdf.inputs["Emission Color"].links[0].from_socket
co = obj_coords(nt, (-2400, -1400))
st = voronoi_(nt, co, 220.0, 'F1', (-1600, -1400))
ss = node(nt, "ShaderNodeSeparateColor", (-1400, -1400)); nt.links.new(st.outputs["Color"], ss.inputs["Color"])
nrm = node(nt, "ShaderNodeVectorMath", (-1800, -1600), operation='NORMALIZE'); nt.links.new(co, nrm.inputs[0])
zz = sep_xyz(nt, nrm.outputs[0], (-1600, -1600))
star = math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', maprange(nt, st.outputs["Distance"], 0.05, 0.0, 0, 1, (-1200, -1450)), maprange(nt, ss.outputs[0], 0.965, 0.975, 0, 1, (-1200, -1550)), (-1000, -1500)),
             maprange(nt, zz.outputs["Z"], 0.25, 0.6, 0, 1.5, (-1200, -1650)), (-850, -1550))
nt.links.new(mix_rgb(nt, 'ADD', star, src, (1.0, 1.0, 1.0, 1), (-600, -1300)), bsdf.inputs["Emission Color"])
SKY = E8.sky_dome("SkyDome", M_SKY, 900.0, seg=48, rings=14, el_min=-6.0)
K.apply_transforms()
light_obj("light.dusk", 'SUN', 0.6, (0.70, 0.80, 0.85), tuple(DUSK_DIR * 50), direction=-DUSK_DIR, angle=math.radians(25.0))
skl = light_obj("light.sky", 'SUN', 0.6, (0.40, 0.50, 0.85), (0, 0, 30), direction=(0.1, 0.2, -1.0), angle=math.radians(85))
skl.data.use_shadow = False
light_obj("Lamp.villa", 'POINT', 60.0, (1.0, 0.62, 0.28), tuple(VILLA_LAMP + Vector((-0.8, 0, 0.3))), shadow_soft_size=0.2)
world = bpy.data.worlds.new("Dusk"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.05, 0.07, 0.14, 1); bg.inputs["Strength"].default_value = 1.6

sound("wind-trees", "beeches", (0.0, 3.0, 12.0))
sound("crowd", "distant", (0.0, -60.0, 2.0))
sound("birds", "dusk", (-6.0, -10.0, 8.0))
S.reader_anchors(0.0)
anchor("scene.centre", (lane_cx(MOUTH), MOUTH, gz(lane_cx(MOUTH), MOUTH)))
anchor("common.mirror", tuple(MAST_TOP + Vector((0, 0, 0.6))))
for o in K.COLL.objects:
    if o.type == 'MESH' and o.data.materials and o.data.materials[0].name in ("M_SkyDome", "M_FarHeath"): o.visible_shadow = False
S.check_clear(look_yaw=0.0)
EZ = gz(0, 0) + EYE
E = Vector((0, 0, EZ))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EZ - 0.6), 17),
    ("Cam_Villa", (1.5, 1.0, EZ), (VX, VY + 1.0, gz(0, 0) + 3.5), 22),
    ("Cam_Mirror", tuple(E), tuple(MAST_TOP), 50),
    ("Cam_Traces", (0.4, 1.0, EZ - 0.3), (0.0, 5.0, 0.0), 22),
], pitch=2.0)
S.finish("chobham-road-common-edge", "chobham_road_common_edge", cams,
         keep_names={"M_BeechLeaves": "veg.crown.beech", "M_HedgeSprays": "veg.shrub.hedge", "M_BankGrass": "veg.grass.bank",
                     "M_LaneGround": "GroundNear", "M_SkyDome": "SkyDome", "M_FarHeath": "far.Heath", "M_HeatherMass": "veg.shrub.heather"},
         keep_uv={"M_LaneGround"},
         size_for={"M_LaneGround": (2048, 256, 2048), "M_BeechBark": (512, 64, 256), "M_HedgeMass": (1024, 64, 512), "M_BeechMass": (512, 64, 256),
                   "M_HeatherMass": (512, 64, 256), "M_VillaBrick": (1024, 64, 512), "M_Slate": (512, 64, 256), "M_PaintedWood": (128, 32, 64),
                   "M_WindowGlass": (32,), "M_LitWindow": (32,), "M_StrawHat": (128, 32, 128), "M_FeltHat": (64, 32, 64), "M_HatBand": (32,),
                   "M_Parasol": (128, 32, 64), "M_Iron": (32,), "M_FarHeath": (256, 32), "M_PitSand": (128, 32), "M_MirrorMast": (32,), "M_Mirror": (32,),
                   "M_SkyDome": (2048,)},
         page=page, default_exposure=1.2, unlit_emit={"M_LitWindow"})
