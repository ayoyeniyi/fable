"""
Fable: the gulf across the road of yellow brick, in the forest of the Kalidahs (The Wonderful Wizard of Oz, chapter VII,
"The Journey to the Great Oz"). A chapter step-in room: built ahead of time, served from the server, downloaded by the
headset.

"... they came to a great ditch that crossed the road and divided the forest as far as they could see on either side.
It was a very wide ditch, and when they crept up to the edge and looked into it they could see it was also very deep,
and there were many big, jagged rocks at the bottom. The sides were so steep that none of them could climb down ..."
"Here is a great tree, standing close to the ditch. If the Tin Woodman can chop it down, so that it will fall to the
other side, we can walk across it easily." ... "it fell with a crash across the ditch, with its top branches on the
other side." (chapter VII)

The moment: just after the tree has fallen. The reader stands on the near side of the gulf by the fresh, axe-cut stump,
wood chips strewn on the yellow bricks and the leaf litter, looking along the felled trunk to the far bank where its top
branches lie crushed among the undergrowth and the road of yellow brick runs on into the forest. The gulf is wide and
deep, with steep sides of raw rock and broken earth and big jagged rocks at the bottom in cold, dim light. The forest
is thick and dark and gloomy on this side; the canopy lets through only a few shafts of daylight. No Kalidahs and no
travellers are modelled; the strange noises are a sound.

Living scene (docs/LIVING_SCENES.md): veg.crown.forest, veg.leaves.felled (the felled crown), veg.shrub.under,
veg.grass.verge, sound.wind-trees.canopy, sound.wind-trees.far, sound.wind.gulf.

Node names: anchor.reader.entrance (feet, on the bricks by the stump), anchor.reader.look, anchor.scene.centre (the
middle of the bridge), anchor.gulf.stump, anchor.gulf.farbank; light.sun (SUN, weak, through the canopy), light.sky
(SUN, cool fill), light.gulf (AREA, cold light down in the chasm); SkyDome.

Axes: metres, +Z up, the reader near the origin facing +Y along the road; the gulf crosses the road from y ~3.5 to ~10.

Run headless (one Blender at a time, CPU):
  blender -b -P blender/build_kalidah_gulf.py -- --cpu --render --quick --res 900 --cams reader
  blender -b -P blender/build_kalidah_gulf.py -- --cpu --render --samples 40 --res 1280 --captures captures/blender/kalidah-gulf
  blender -b -P blender/build_kalidah_gulf.py -- --cpu --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
ARGS = K.setup("kalidah-gulf", "out/kalidah-gulf", 1900, "KalidahGulf", default_samples=40)
import scene_kit_b2 as B
from scene_kit_b2 import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          wood, noisy, plain, image_mat, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound,
                          light_obj, camera, smoothstep, lerp, n2, fbm2, link, card, tree, blob, set_card_normals, spray_atlas)
OUT = K.OUT; scene = K.scene
rng = random.Random(1907)

EYE_H = 1.55
G0, G1 = 3.6, 10.2                 # the gulf's near and far lips (y), along the road
DEPTH = 5.5
ROAD_W = 2.6
SUN_DIR = Vector((0.35, 0.25, 0.9)).normalized()
NEAR = 34.0
STUMP = Vector((1.75, 2.55))
FAR_END = Vector((-1.1, 14.8))

def gulf_edge(x):
    """the gulf's two lips wander a little along its length"""
    return (G0 + 0.6 * noise.noise(Vector((x * 0.15, 1.3, 0.0))) + 0.25 * noise.noise(Vector((x * 0.6, 2.1, 0.0))),
            G1 + 0.6 * noise.noise(Vector((x * 0.15, 4.7, 0.0))) + 0.25 * noise.noise(Vector((x * 0.6, 5.3, 0.0))))
def H(x, y):
    h = 0.25 * fbm2(x, y, 9.0, 3, 0.4) + 0.4 * fbm2(x, y, 25.0, 2, 1.7)
    a, b = gulf_edge(x)
    if a - 0.3 < y < b + 0.3:
        t = min(y - a, b - y)          # distance in from the nearer lip
        drop = smoothstep(-0.3, 1.6, t) * DEPTH
        jag = 0.9 * noise.noise(Vector((x * 0.7, y * 0.7, 3.3))) + 0.5 * noise.noise(Vector((x * 1.9, y * 1.9, 1.1)))
        h = h - drop + jag * smoothstep(0.0, 1.0, t) * (1.0 - smoothstep(2.0, 3.0, t) * 0.4)
    # the road is a little raised and level
    if abs(x) < ROAD_W / 2 + 0.4: h = lerp(h, 0.05 * fbm2(x, y, 6.0, 2), 1.0 - smoothstep(ROAD_W / 2, ROAD_W / 2 + 0.4, abs(x))) if not (a - 0.3 < y < b + 0.3) else h
    return h
Z0 = H(0.25, 1.45)
def gz(x, y): return H(x, y) - Z0
READER = Vector((0.25, 1.45))
B.set_ground(gz, (READER.x, READER.y, gz(READER.x, READER.y) + EYE_H))

# ----------------------------------------------------------------------------- atlases and materials
print("painting atlases ...", flush=True)
DG = [(0.03, 0.07, 0.02), (0.04, 0.09, 0.025), (0.025, 0.06, 0.018), (0.05, 0.10, 0.03), (0.035, 0.08, 0.022)]
DT = [(0.08, 0.14, 0.04), (0.10, 0.16, 0.05), (0.07, 0.12, 0.035)]
IMG_UNDER = B.meadow_atlas("A_UnderCards", greens=DG, tips=DT, dry=0.12, seed=31,
                           flowers=[((0.25, 0.30, 0.12), (0.2, 0.25, 0.1), 'umbel'), ((0.20, 0.22, 0.10), (0.2, 0.2, 0.1), 'spike'),
                                    ((0.55, 0.52, 0.40), (0.4, 0.35, 0.2), 'umbel'), ((0.22, 0.28, 0.12), (0.2, 0.25, 0.1), 'cup')])
B.SPRAY_KINDS["forest"] = ([(0.06, 0.12, 0.03), (0.08, 0.15, 0.04), (0.05, 0.10, 0.025), (0.10, 0.16, 0.05)], 5, 13.0, 'broad', None)
B.SPRAY_KINDS["felled"] = ([(0.08, 0.13, 0.04), (0.11, 0.16, 0.05), (0.14, 0.15, 0.06), (0.09, 0.12, 0.04)], 5, 14.0, 'broad', None)
IMG_FOREST = spray_atlas("A_ForestSprays", "forest", 41)
IMG_FELLED = spray_atlas("A_FelledSprays", "felled", 42)
M_UNDER = image_mat("M_UnderCards", IMG_UNDER, rough=0.7, alpha=True, spec=0.3)
M_CANOPY = image_mat("M_ForestSprays", IMG_FOREST, rough=0.6, alpha=True, spec=0.3)
M_FELLED = image_mat("M_FelledSprays", IMG_FELLED, rough=0.6, alpha=True, spec=0.3)
M_BARK = B.bark_mat("M_ForestBark", base=(0.07, 0.065, 0.055), dark=(0.02, 0.018, 0.015), light=(0.12, 0.11, 0.09), fissure=True, green=0.5, scale=1.2)
M_FELLBARK = B.bark_mat("M_FelledBark", base=(0.09, 0.08, 0.065), dark=(0.03, 0.025, 0.02), light=(0.15, 0.13, 0.10), fissure=True, green=0.3, scale=2.4)
M_MASS = noisy("M_CanopyMass", [(0.015, 0.035, 0.01), (0.03, 0.06, 0.018), (0.045, 0.08, 0.025)], scale=3.0, rough=0.85, bump=0.6, bump_dist=0.05)
M_FRESHWOOD = noisy("M_FreshWood", [(0.50, 0.38, 0.22), (0.62, 0.48, 0.30), (0.42, 0.30, 0.16)], scale=40, rough=0.8, bump=0.3, stretch=(1, 1, 1))
M_CHIPS = noisy("M_WoodChips", [(0.45, 0.34, 0.20), (0.58, 0.45, 0.28)], scale=30, rough=0.85, bump=0.2)
def ground_mat(name="M_Ground"):
    """forest floor: dark leaf litter, moss and roots; the road of yellow brick, worn and mossy at the joints; raw
    rock and broken brown earth down the gulf's sides."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0)); s = sep_xyz(nt, co, (-2200, -600)); x = s.outputs["X"]; y = s.outputs["Y"]; z = s.outputs["Z"]
    n1 = noise_(nt, co, 0.4, 5, 0.6, loc=(-1900, 300)); n2_ = noise_(nt, co, 4.0, 6, 0.65, loc=(-1900, 100))
    lit = ramp(nt, [(0.0, c4((0.025, 0.018, 0.010))), (0.4, c4((0.05, 0.035, 0.018))), (0.7, c4((0.08, 0.055, 0.03))), (1.0, c4((0.04, 0.06, 0.02)))], (-1500, 300))
    nt.links.new(math_(nt, 'ADD', math_(nt, 'MULTIPLY', n1.outputs["Fac"], 0.5, (-1700, 300)), math_(nt, 'MULTIPLY', n2_.outputs["Fac"], 0.6, (-1700, 200)), (-1600, 250)), lit.inputs["Fac"])
    # bricks: running bond along Y, yellow with ochre and cream, dark mossy joints
    br = node(nt, "ShaderNodeTexBrick", (-1700, -300), offset=0.5)
    cv = node(nt, "ShaderNodeCombineXYZ", (-1900, -300)); nt.links.new(y, cv.inputs["X"]); nt.links.new(x, cv.inputs["Y"])
    nt.links.new(cv.outputs[0], br.inputs["Vector"])
    br.inputs["Scale"].default_value = 1.0; br.inputs["Brick Width"].default_value = 0.22; br.inputs["Row Height"].default_value = 0.11
    br.inputs["Mortar Size"].default_value = 0.01; br.inputs["Color1"].default_value = (0.52, 0.38, 0.07, 1); br.inputs["Color2"].default_value = (0.62, 0.47, 0.12, 1)
    br.inputs["Mortar"].default_value = (0.04, 0.05, 0.02, 1)
    bcol = mix_rgb(nt, 'MULTIPLY', 1.0, br.outputs["Color"], maprange(nt, n2_.outputs["Fac"], 0.3, 0.7, 0.55, 1.05, (-1500, -500)), (-1300, -300))
    moss = maprange(nt, n1.outputs["Fac"], 0.55, 0.75, 0.0, 0.55, (-1500, -700))
    bcol = mix_rgb(nt, 'MIX', moss, bcol, c4((0.06, 0.09, 0.03)), (-1100, -300))
    road = maprange(nt, math_(nt, 'ABSOLUTE', x, None, (-1700, -900)), ROAD_W / 2 - 0.05, ROAD_W / 2 + 0.15, 1.0, 0.0, (-1500, -900))
    road = math_(nt, 'MULTIPLY', road, maprange(nt, z, -0.6, -0.25, 0.0, 1.0, (-1500, -1050)), (-1300, -950))
    road = math_(nt, 'MULTIPLY', road, maprange(nt, n2_.outputs["Fac"], 0.2, 0.32, 0.4, 1.0, (-1300, -1100)), (-1150, -1000))
    col = mix_rgb(nt, 'MIX', road, lit.outputs["Color"], bcol, (-800, 100))
    rock = ramp(nt, [(0.2, c4((0.06, 0.055, 0.05))), (0.5, c4((0.12, 0.10, 0.08))), (0.8, c4((0.18, 0.15, 0.12)))], (-1100, -1300)); nt.links.new(n2_.outputs["Fac"], rock.inputs["Fac"])
    earth = c4((0.10, 0.06, 0.03))
    wall = maprange(nt, z, -0.5, -1.5, 0.0, 1.0, (-1100, -1500))
    rc = mix_rgb(nt, 'MIX', maprange(nt, z, -1.0, -2.2, 0.0, 1.0, (-900, -1500)), earth, rock.outputs["Color"], (-800, -1400))
    col = mix_rgb(nt, 'MIX', wall, col, rc, (-500, 100))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, road, 0, 1, 0.85, 0.6, (-300, -300)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'ADD', n2_.outputs["Fac"], math_(nt, 'MULTIPLY', br.outputs["Fac"], math_(nt, 'MULTIPLY', road, -0.6, (-700, -800)), (-600, -800)), (-400, -700)), 0.5, 0.02, (0, -400))
    return m
M_GROUND = ground_mat()
M_ROCK = noisy("M_GulfRocks", [(0.05, 0.05, 0.045), (0.10, 0.095, 0.085), (0.16, 0.15, 0.13)], scale=1.5, rough=0.85, bump=0.8, bump_dist=0.03, warp=1.0)
M_SKY = B.clear_sky_mat("M_SkyDome", SUN_DIR, zenith=(0.30, 0.38, 0.50), horizon=(0.45, 0.50, 0.52), cloud=0.6, strength=0.8)

# ----------------------------------------------------------------------------- the ground with the gulf
print("terrain ...", flush=True)
def axis_coords(lo, hi, focus, fine, coarse):
    out = [lo]; v = lo
    while v < hi:
        d = min(abs(v - f) for f in focus); v = min(hi, v + lerp(fine, coarse, smoothstep(2.0, 12.0, d))); out.append(v)
    return out
XS = axis_coords(-NEAR, NEAR, [0.0], 0.35, 2.8)
YS = axis_coords(-NEAR * 0.6, NEAR, [G0, G1, (G0 + G1) / 2, 0.5], 0.3, 2.8)
verts = []; uvs = []
for yy in YS:
    for xx in XS:
        verts.append((xx, yy, gz(xx, yy))); uvs.append(((xx - XS[0]) / (XS[-1] - XS[0]), (yy - YS[0]) / (YS[-1] - YS[0])))
nx = len(XS) - 1
faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(len(YS) - 1) for i in range(nx)]
mesh_from("GroundNear", verts, faces, M_GROUND, smooth=True, uvs=uvs)
print("ground grid", len(XS), len(YS), flush=True)
# big jagged rocks at the bottom of the gulf and fallen blocks on its sides
RK = MB(); rr = random.Random(12)
for i in range(70):
    xx = rr.uniform(-16, 16); a, b = gulf_edge(xx); yy = rr.uniform(a + 1.4, b - 1.4)
    r_ = rr.uniform(0.4, 1.3)
    B.blob(RK, (xx, yy, gz(xx, yy) + r_ * 0.25), (r_ * rr.uniform(0.8, 1.4), r_, r_ * rr.uniform(0.7, 1.3)), 100 + i, sub=1, rough=0.45)
for i in range(30):                 # boulders and outcrops at the lips
    xx = rr.uniform(-14, 14); a, b = gulf_edge(xx); yy = rr.choice((a - 0.2, b + 0.2)) + rr.gauss(0, 0.3)
    if abs(xx) < ROAD_W / 2 + 0.6: continue
    r_ = rr.uniform(0.3, 0.8)
    B.blob(RK, (xx, yy, gz(xx, yy)), (r_ * 1.3, r_, r_ * 0.7), 200 + i, sub=1, rough=0.35)
RK.build("GulfRocks", M_ROCK, sway=False)

# ----------------------------------------------------------------------------- the stump, the chips and the felled tree across the gulf
print("felled tree ...", flush=True)
SZ = gz(STUMP.x, STUMP.y)
lathe("Stump", [(0.0, -0.3), (0.62, -0.3), (0.55, 0.0), (0.47, 0.18), (0.44, 0.42), (0.43, 0.55), (0.0, 0.55)], (STUMP.x, STUMP.y, SZ), M_FELLBARK, steps=18, jitter=0.06, seed=2)
lathe("StumpCut", [(0.0, 0.55), (0.42, 0.55), (0.42, 0.57), (0.0, 0.575)], (STUMP.x, STUMP.y, SZ), M_FRESHWOOD, steps=18)
box("StumpHinge", (0.18, 0.5, 0.2), (STUMP.x - 0.02, STUMP.y + 0.32, SZ + 0.65), M_FRESHWOOD, rot=(0.6, 0, 0.1))     # torn hinge wood
CH = MB(); rc = random.Random(4)
for i in range(70):
    a = rc.uniform(0, 2 * math.pi); r = rc.uniform(0.5, 2.4) ** 1.2; xx = STUMP.x + r * math.cos(a); yy = STUMP.y + r * math.sin(a) * 0.8
    if yy > gulf_edge(xx)[0] - 0.2: continue
    s_ = rc.uniform(0.04, 0.10); c_ = Vector((xx, yy, gz(xx, yy) + 0.012)); yaw = rc.uniform(0, 3.14)
    d = Vector((math.cos(yaw), math.sin(yaw), 0)); e = Vector((-d.y, d.x, 0))
    v0 = CH.vert(c_ - d * s_ - e * s_ * 0.4); v1 = CH.vert(c_ + d * s_ - e * s_ * 0.3); v2 = CH.vert(c_ + d * s_ * 0.8 + e * s_ * 0.4 + Vector((0, 0, 0.01))); v3 = CH.vert(c_ - d * s_ + e * s_ * 0.35)
    CH.face(v0, v1, v2, v3)
CH.build("WoodChips", M_CHIPS, sway=False)
# the trunk: from beside the stump (its butt on the near bank) across the gulf; the top lies on the far bank
butt = Vector((STUMP.x + 0.1, STUMP.y + 0.75, SZ + 0.45))
top = Vector((FAR_END.x, FAR_END.y, gz(FAR_END.x, FAR_END.y) + 0.5))
pts = [butt.lerp(top, t) + Vector((0.15 * math.sin(t * 5.0), 0, -0.25 * math.sin(t * math.pi) * 0.2)) for t in [i / 10 for i in range(11)]]
tube("FelledTrunk", pts, [0.46 - 0.32 * (i / 10) for i in range(11)], M_FELLBARK, sides=12)
lathe("FelledButt", [(0.0, 0.0), (0.46, 0.0), (0.46, 0.02), (0.0, 0.025)], (0, 0, 0), M_FRESHWOOD, steps=14).matrix_world = \
    Matrix.Translation(butt) @ (pts[0] - pts[1]).normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
# the crown crushed on the far bank: limbs splayed along the ground and up, leaf sprays wilting
FM = MB(); rf = random.Random(7)
for k in range(9):
    base_t = rf.uniform(0.65, 0.95); bp = butt.lerp(top, base_t)
    dirv = (top - butt).normalized() * rf.uniform(0.4, 1.0) + Vector((rf.uniform(-1, 1), rf.uniform(-0.2, 0.6), rf.uniform(0.0, 0.9)))
    dirv.normalize(); L = rf.uniform(2.0, 4.5)
    ep = bp + dirv * L; ep.z = max(ep.z, gz(ep.x, ep.y) + 0.2)
    tube(f"FelledLimb{k}", [bp, bp.lerp(ep, 0.5) + Vector((0, 0, 0.2)), ep], [0.14, 0.08, 0.03], M_FELLBARK, sides=6)
    for j in range(16):
        q = bp.lerp(ep, rf.uniform(0.35, 1.0)) + Vector((rf.gauss(0, 0.5), rf.gauss(0, 0.5), rf.uniform(-0.2, 0.6)))
        out = Vector((rf.gauss(0, 1), rf.gauss(0, 1), rf.uniform(0.2, 1.0))).normalized()
        tang = out.cross(Vector((0, 0, 1))); tang = tang.normalized() if tang.length > 0.1 else Vector((1, 0, 0))
        sz = rf.uniform(1.0, 1.6)
        card(FM, q - out * 0.2, tang * sz, out.cross(tang).normalized() * sz, rf.choice(B.QUAD), 0.4, 1.0)
fo = FM.build("FelledCrown", M_FELLED)

# ----------------------------------------------------------------------------- the forest: thick and dark, tall trunks, a heavy canopy
print("forest ...", flush=True)
TR = []
def place(x, y):
    a, b = gulf_edge(x)
    if a - 1.2 < y < b + 1.2: return False
    if abs(x) < ROAD_W / 2 + 1.0: return False
    if (Vector((x, y)) - STUMP).length < 2.5 or (Vector((x, y)) - FAR_END).length < 3.0: return False
    return all((Vector((x, y)) - t).length > 2.6 for t in TR)
for i in range(400):
    x = rng.uniform(-22, 22); y = rng.uniform(-16, 26)
    if not place(x, y): continue
    TR.append(Vector((x, y)))
    near = math.hypot(x - READER.x, y - READER.y) < 11
    h = rng.uniform(11, 24)
    tree(f"Tree{i}", x, y, h, rng.uniform(3.5, 6.0), rng.choice(("ash", "elm", "oak", "oak")), 300 + i, M_BARK, M_CANOPY,
         nlimbs=5 if near else 4, detail=0.8 if near else 0.5, cards_per_tip=0, card_size=3.6 if near else 4.4, fill=38 if near else 22,
         mass=M_MASS, mass_k=0.62, nblobs=3, mass_sub=1)
    if len(TR) >= 46: break
print("trees", len(TR), flush=True)
# the forest wall beyond: a closed ring of dark foliage and trunks (opaque, low-poly) so no sky shows between the trunks
FW = MB(); NW = 72; rw = random.Random(21)
rows = []
for j, (rr_, zz) in enumerate(((27.0, -1.0), (27.5, 5.0), (27.0, 9.0), (26.0, 12.0))):
    row = []
    for i in range(NW):
        a = 2 * math.pi * i / NW
        x, y = READER.x + rr_ * math.cos(a), READER.y + 4 + rr_ * math.sin(a)
        jit = 2.5 * noise.noise(Vector((math.cos(a) * 3, math.sin(a) * 3, j * 0.7))) if j >= 2 else 0.0
        row.append(FW.vert((x, y, gz(x, y) + zz + jit)))
    rows.append(row)
for j in range(len(rows) - 1):
    for i in range(NW):
        i2 = (i + 1) % NW; FW.face(rows[j][i], rows[j + 1][i], rows[j + 1][i2], rows[j][i2])
FW.build("ForestWall", M_MASS, sway=False)
# undergrowth: ferns and shrubs (cards) along the road edges and the lips of the gulf, sparse elsewhere
def under_ok(x, y):
    a, b = gulf_edge(x)
    if a - 0.4 < y < b + 0.4: return 0.0
    if abs(x) < ROAD_W / 2 - 0.1: return 0.0
    edge = 1.0 - smoothstep(ROAD_W / 2, ROAD_W / 2 + 2.5, abs(x))
    lip = 1.0 - smoothstep(0.4, 2.0, min(abs(y - a), abs(y - b)))
    if (Vector((x, y)) - READER).length < 1.0: return 0.0
    return 0.25 + 0.6 * max(edge, lip)
mb = MB(); R = random.Random(5)
B.scatter_cards(mb, None, R, 30000, 0.5, 14.0, under_ok, B.MEADOW_LONG + B.MEADOW_FLOWER, height=0.55, width=0.6, solid_from=99, maxcards=900, segs=2,
                centre=(READER.x, READER.y + 3.0))
go = mb.build("UnderCards", M_UNDER); set_card_normals(go, lambda p: Vector((0, 0, 1)))

# ----------------------------------------------------------------------------- sky, light, anchors
B.sky_dome("SkyDome", M_SKY, 120.0)
light_obj("light.sun", 'SUN', 4.5, (1.0, 0.93, 0.80), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(2.0))
sl = light_obj("light.sky", 'SUN', 0.7, (0.55, 0.68, 0.75), (0, 0, 40), direction=(0.1, 0.1, -1.0), angle=math.radians(90)); sl.data.use_shadow = False
light_obj("light.gulf", 'AREA', 90.0, (0.6, 0.72, 0.85), (0.0, (G0 + G1) / 2, gz(0, 6) + 1.0), direction=(0, 0, -1), size=6.0, shape='RECTANGLE', size_y=4.0)
B.world_sky(zen=(0.20, 0.26, 0.32), hor=(0.16, 0.20, 0.18), ground=(0.03, 0.04, 0.02), strength=1.0)
vol = scene.world.node_tree.nodes.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.006; vol.inputs["Color"].default_value = (0.55, 0.62, 0.55, 1)
pass   # no world volume: an infinite haze in Cycles swallows the sun (Unity has its own fog)
E = Vector((READER.x, READER.y, gz(READER.x, READER.y) + EYE_H))
fwd = Vector((-0.08, 1.0, 0)).normalized()
B.reader_anchors((READER.x, READER.y, gz(READER.x, READER.y)), tuple(E + fwd))
mid = butt.lerp(top, 0.45)
anchor("scene.centre", tuple(mid)); anchor("gulf.stump", (STUMP.x, STUMP.y, SZ)); anchor("gulf.farbank", tuple(top))
sound("wind-trees", "canopy", (3.0, -2.0, 14.0)); sound("wind-trees", "far", (-8.0, 18.0, 14.0)); sound("wind", "gulf", (0.0, 7.0, gz(0, 7) + 1.0))
page = B.page_preview(E, fwd)
K.apply_transforms()
cams = B.view_cams(E, fwd, extra=[("Cam_Gulf", E + Vector((-1.5, 2.0, 0.2)), (2.0, 7.0, gz(2.0, 7.0)), 20),
                                  ("Cam_Stump", E + Vector((0.6, 0.0, -0.3)), (STUMP.x, STUMP.y, SZ + 0.4), 28)])
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "kalidah_gulf_source.blend"))
K.print_budget()
if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=1.0, captures_dir=ARGS.captures)
if ARGS.bake or ARGS.export:
    scene.world.node_tree.nodes.remove(vol)
    B.export_room("kalidah_gulf.gltf", cams, page=page,
                  keep_names={"M_UnderCards": "veg.shrub.under", "M_ForestSprays": "veg.crown.forest", "M_FelledSprays": "veg.leaves.felled",
                              "M_SkyDome": "SkyDome", "M_Ground": "GroundNear"},
                  keep_uv={"M_Ground", "M_SkyDome"},
                  size_for={"M_Ground": (2048, 512, 2048), "M_SkyDome": (1024,), "M_GulfRocks": (1024, 256, 1024), "M_ForestBark": (1024, 128, 512),
                            "M_FelledBark": (1024, 256, 512), "M_CanopyMass": (512, 64, 256), "M_FreshWood": (256, 64, 128), "M_WoodChips": (128, 32, 64)},
                  default_size=(128, 64, 128))
print("DONE")
