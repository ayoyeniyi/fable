"""
Fable: the sacrifice on the shore at Pylos at sunrise (The Odyssey, Book III).

"But as the sun was rising from the fair sea into the firmament of heaven ... they reached Pylos the city of Neleus.
Now the people of Pylos were gathered on the sea shore to offer sacrifice of black bulls to Neptune lord of the
Earthquake. There were nine guilds ... As they were eating the inward meats and burning the thigh bones on the embers
in the name of Neptune, Telemachus and his crew arrived, furled their sails, brought their ship to anchor, and went
ashore." "There they found Nestor sitting with his sons, while his company round him were busy getting dinner ready,
and putting pieces of meat on to the spits ... [they] gave them places on some soft sheepskins that were lying on the
sands ... and gave them a golden cup."

The reader stands on the sheepskins by Nestor's fire on a strip of pale sand between the dunes and the sea, facing the
sea and the sunrise. At the fire: forked stakes and bronze spits with pieces of meat, thigh bones burning on the
embers, a bronze mixing-bowl, the golden cup on a fleece. Along the shore the other guilds' fires smoke at intervals
(three burn close enough to flicker; the rest are banked embers). Ahead-left, in the shallows, Telemachus's black
ship rides at anchor, its sail furled on the yard, oars shipped, anchor stones down. Behind, the dunes with marram and
the black bull-hides and horns of the sacrifice laid over driftwood; beyond, the high citadel of Pylos on its hill.
No people (the feasters are only implied).

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py.

Node names the runtime relies on:
  anchor.reader.entrance (feet on the fleeces, facing +Y: the sea, east), anchor.reader.look, anchor.scene.centre
  (Nestor's fire), anchor.shore.ship
  light.sun (SUN, just risen over the sea), light.sky (SUN, cool fill), Lamp.fire.* (POINT, the fires)
  fx.fire.nestor, fx.fire.guild1, fx.fire.guild2 (custom property radius)
  water.ocean.sea (COLOR_0.G foam at the shore), veg.grass.marram, cloth.sail.furled
  sound.surf.shore, sound.fire.nestor, sound.gulls.0, sound.crowd.guilds
  SkyDome, far.Hills, far.Citadel (backdrop)

Run headless:
  blender -b -P blender/build_pylos_shore.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_pylos_shore.py -- --render --samples 48 --res 1400
  blender -b -P blender/build_pylos_shore.py -- --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b1 as S
from scene_kit_b1 import (K, E8, new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound, light_obj, camera,
                          link, smoothstep, lerp, n2, fbm2, orient, card, plant, set_card_normals, az_dir, TWO_PI)

ARGS = S.setup("pylos-shore", 1200, "PylosShore", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
SEA = -1.05                      # sea level below the reader's sand
SUN_AZ, SUN_EL = 14.0, 4.0
SUN_DIR = (az_dir(SUN_AZ) * math.cos(math.radians(SUN_EL)) + Vector((0, 0, math.sin(math.radians(SUN_EL))))).normalized()

# ----------------------------------------------------------------------------- the beach
def shore_y(x): return 8.0 + 1.2 * math.sin(x * 0.05 + 0.6) + 0.4 * n2(x, 0, 8.0, 3.0)
def H(x, y):
    d = y - shore_y(x)                            # >0 in the sea
    z = SEA + 0.0
    if d < 0: z += min(-d, 12.0) * 0.105 + 0.03 * n2(x, y, 1.5, 2.0)
    else: z -= d * 0.09 + 0.6 * smoothstep(0, 30, d)
    # the dunes behind: a ridge 3-4 m high from 10 m back, hummocky
    dune = smoothstep(-7.0, -13.0, y) * (2.6 + 1.0 * n2(x, y, 7.0, 5.0) + 0.5 * n2(x, y, 2.5, 9.0))
    z += dune
    # wind ripples and small undulation on the beach
    z += 0.05 * n2(x, y, 3.0, 11.0) * smoothstep(-1, -4, d)
    return z
Z0 = H(0, 0)
def gz(x, y): return H(x, y) - Z0
SEA_Z = SEA - Z0
S.set_ground(gz)

def wet_fn(x, y):
    d = y - shore_y(x)
    return smoothstep(-2.4, -0.4, d)
def trodden_fn(x, y):
    """the sand round the fires is trodden, ashy; paths between fires."""
    v = 0.0
    for (fx_, fy_, r) in FIRES_ALL:
        v = max(v, smoothstep(r + 3.5, r + 0.6, math.hypot(x - fx_, y - fy_)))
    return v
def ash_fn(x, y):
    v = 0.0
    for (fx_, fy_, r) in FIRES_ALL:
        v = max(v, smoothstep(r + 0.8, r * 0.6, math.hypot(x - fx_, y - fy_)))
    return v

FIRES = [(1.75, 2.35, 0.45, "nestor"), (-8.5, 1.2, 0.5, "guild1"), (10.0, 0.4, 0.5, "guild2")]
EMBERS = [(-19.0, 0.5, 0.55), (21.0, -0.4, 0.55), (-30.0, 1.5, 0.6), (32.0, 0.8, 0.6)]
FIRES_ALL = [(x, y, r) for (x, y, r, _) in FIRES] + EMBERS

def sand_mat(name="M_Sand"):
    """pale Messenian sand: fine warm grey-gold grains, wind ripples, darker and glossy where wet from the sea, a
    strand line of dried weed and shells, trodden and grey with ash round the fires."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    aw = node(nt, "ShaderNodeAttribute", (-1900, 600)); aw.attribute_name = "wet"
    at = node(nt, "ShaderNodeAttribute", (-1900, 450)); at.attribute_name = "trodden"
    aa = node(nt, "ShaderNodeAttribute", (-1900, 300)); aa.attribute_name = "ash"
    wet, trod, ash = aw.outputs["Fac"], at.outputs["Fac"], aa.outputs["Fac"]
    n = noise_(nt, co, 0.5, 5, 0.6, loc=(-1700, 200))
    fine = noise_(nt, co, 60.0, 3, 0.7, loc=(-1700, 0))
    mp = node(nt, "ShaderNodeMapping", (-1700, -250)); mp.inputs["Scale"].default_value = (0.6, 4.0, 1.0); mp.inputs["Rotation"].default_value = (0, 0, 0.3)
    nt.links.new(co, mp.inputs["Vector"])
    rip = node(nt, "ShaderNodeTexWave", (-1500, -250)); rip.inputs["Scale"].default_value = 2.2; rip.inputs["Distortion"].default_value = 4.0
    rip.inputs["Detail"].default_value = 2.0; nt.links.new(mp.outputs["Vector"], rip.inputs["Vector"])
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1500, 200)), c4(K.srgb((0.66, 0.58, 0.46))), c4(K.srgb((0.76, 0.69, 0.56))), (-1300, 200))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0.86, 1.08, (-1500, 0)), (-1150, 150))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', rip.outputs["Fac"], 0.12, (-1300, -250)), col, (0.7, 0.68, 0.64, 1), (-1000, 150))
    # strand line: a band just above the wet sand
    band = maprange(nt, wet, 0.0, 0.08, 0, 1, (-1500, -500))
    band = math_(nt, 'MULTIPLY', band, maprange(nt, wet, 0.18, 0.08, 0, 1, (-1500, -600)), (-1350, -550))
    weed = maprange(nt, noise_(nt, co, 9.0, 4, 0.6, loc=(-1500, -750)).outputs["Fac"], 0.5, 0.62, 0, 1, (-1300, -700))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', band, weed, (-1150, -650)), col, c4(K.srgb((0.20, 0.17, 0.12))), (-850, 150))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', trod, 0.5, (-1000, -900)), col, c4(K.srgb((0.56, 0.52, 0.46))), (-700, 150))
    col = mix_rgb(nt, 'MIX', ash, col, c4(K.srgb((0.20, 0.19, 0.18))), (-550, 150))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', wet, 0.65, (-700, -400)), col, (0.55, 0.50, 0.44, 1), (-400, 150))
    col = K.ao_mul(nt, col, 0.3, 0.3, (-300, -900))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, wet, 0.9, 0.3, (-400, -300)), b.inputs["Roughness"])
    b.inputs["Specular IOR Level"].default_value = 0.2
    hgt = math_(nt, 'ADD', math_(nt, 'MULTIPLY', rip.outputs["Fac"], math_(nt, 'SUBTRACT', 1.0, trod, (-900, -1300)), (-750, -1300)),
                math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.3, (-900, -1400)), (-600, -1350))
    bump_from(nt, b, hgt, 0.3, 0.01)
    return m

def hull_mat(name="M_Hull"):
    """a black ship: planking paid with pitch, glossy where fresh, dull and salt-grey at the waterline, worn pale on the
    gunwale; strakes run along the hull (world X along the ship after it is placed: object coords)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1800, -300))
    zf = math_(nt, 'FRACT', math_(nt, 'DIVIDE', s.outputs["Z"], 0.2, (-1600, 0)), None, (-1450, 0))
    seam = maprange(nt, zf, 0.0, 0.06, 0.55, 1.0, (-1300, 0))
    n = noise_(nt, co, 3.0, 5, 0.6, loc=(-1600, 300))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1400, 300)), c4(K.srgb((0.035, 0.032, 0.03))), c4(K.srgb((0.08, 0.07, 0.06))), (-1100, 300))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, seam, (-900, 300))
    salt = maprange(nt, s.outputs["Z"], 0.5, 0.15, 0, 0.6, (-1300, -400))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', salt, maprange(nt, n.outputs["Fac"], 0.4, 0.6, 0.4, 1.0, (-1300, -550)), (-1100, -450)), col, c4(K.srgb((0.30, 0.29, 0.27))), (-700, 300))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.3, 0.6, (-700, -100)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'ADD', seam, math_(nt, 'MULTIPLY', n.outputs["Fac"], 0.3, (-700, -700)), (-550, -700)), 0.3, 0.01)
    return m

def fleece_mat(name="M_Fleece"):
    """sheepskin: cream to dirty-white curly wool locks (voronoi cells with a twist), grey tips, dusted with sand."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 55.0, 'F1', (-1200, 0))
    v2 = voronoi_(nt, co, 140.0, 'F1', (-1200, -200))
    lock = maprange(nt, v.outputs["Distance"], 0.0, 0.5, 1, 0, (-1000, 0))
    n = noise_(nt, co, 4.0, 4, 0.6, loc=(-1200, 300))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1000, 300)), c4(K.srgb((0.62, 0.56, 0.46))), c4(K.srgb((0.80, 0.75, 0.64))), (-800, 300))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, lock, 0, 1, 0.6, 1.05, (-850, 0)), (-600, 300))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.95
    b.inputs["Sheen Weight"].default_value = 0.6
    bump_from(nt, b, math_(nt, 'ADD', lock, math_(nt, 'MULTIPLY', maprange(nt, v2.outputs["Distance"], 0, 0.5, 1, 0, (-900, -200)), 0.4, (-750, -200)), (-600, -100)), 0.7, 0.015)
    return m

def hide_mat(name="M_BullHide"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    mp = node(nt, "ShaderNodeMapping", (-1300, 0)); mp.inputs["Scale"].default_value = (30.0, 30.0, 4.0); nt.links.new(co, mp.inputs["Vector"])
    hair = noise_(nt, mp.outputs["Vector"], 8.0, 3, 0.6, 1.0, (-1100, 0))
    n = noise_(nt, co, 2.0, 4, 0.6, loc=(-1100, 300))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-900, 300)), c4(K.srgb((0.035, 0.03, 0.028))), c4(K.srgb((0.09, 0.07, 0.06))), (-700, 300))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, hair.outputs["Fac"], 0.3, 0.7, 0.75, 1.2, (-900, 0)), (-500, 300))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.7
    bump_from(nt, b, hair.outputs["Fac"], 0.3, 0.005)
    return m

def embers_mat(name="M_Embers"):
    """glowing embers and charcoal: black char with orange-red glow in the cracks (emissive)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 18.0, 'DISTANCE_TO_EDGE', (-1200, 0))
    n = noise_(nt, co, 6.0, 4, 0.6, loc=(-1200, 300))
    glow = math_(nt, 'MULTIPLY', maprange(nt, v.outputs["Distance"], 0.0, 0.08, 1, 0, (-1000, 0)), maprange(nt, n.outputs["Fac"], 0.4, 0.65, 0.15, 1.0, (-1000, 300)), (-800, 100))
    col = mix_rgb(nt, 'MIX', glow, c4(K.srgb((0.05, 0.045, 0.04))), c4((1.0, 0.32, 0.06)), (-600, 100))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_rgb(nt, 'MULTIPLY', glow, (0, 0, 0, 1), (1.0, 0.30, 0.05, 1), (-500, -100)), b.inputs["Emission Color"])
    nt.links.new(maprange(nt, glow, 0, 1, 0, 6.0, (-500, -300)), b.inputs["Emission Strength"])
    b.inputs["Roughness"].default_value = 0.9
    return m

print("materials ...", flush=True)
M_SAND = sand_mat()
M_HULL = hull_mat()
M_FLEECE = fleece_mat()
M_HIDE = hide_mat()
M_EMBERS = embers_mat()
M_BRONZE = K.noisy("M_Bronze", [K.srgb((0.55, 0.38, 0.18)), K.srgb((0.42, 0.30, 0.15)), K.srgb((0.30, 0.32, 0.22))], scale=6, rough=0.35, bump=0.05, metallic=1.0)
M_GOLD = plain("M_Gold", (0.95, 0.70, 0.30), rough=0.18, metallic=1.0)
M_DRIFT = S.bark_mat("M_Driftwood", (0.58, 0.54, 0.48), (0.30, 0.28, 0.25), (0.70, 0.67, 0.61), scale=2.0, fissure=0.5, moss=0.0)
M_STAKE = S.bark_mat("M_Stakes", (0.32, 0.25, 0.17), (0.14, 0.11, 0.08), (0.42, 0.34, 0.24), scale=3.0, fissure=0.4, moss=0.0)
M_CHAR = K.noisy("M_Charred", [K.srgb((0.05, 0.045, 0.04)), K.srgb((0.12, 0.10, 0.08))], scale=10, rough=0.9, bump=0.3)
M_STONE = S.stone_mat("M_HearthStones", (0.34, 0.31, 0.27), (0.14, 0.13, 0.11), (0.42, 0.38, 0.33), scale=3.0, lichen=0.1, rough=0.8, bump=0.25)
M_MEAT = K.noisy("M_Meat", [K.srgb((0.30, 0.14, 0.07)), K.srgb((0.40, 0.22, 0.10)), K.srgb((0.16, 0.08, 0.04))], scale=20, rough=0.45, bump=0.3)
M_BONE = K.noisy("M_FatBone", [K.srgb((0.52, 0.40, 0.26)), K.srgb((0.30, 0.20, 0.12)), K.srgb((0.12, 0.08, 0.05))], scale=12, rough=0.4, bump=0.2)
M_HORN = K.noisy("M_Horn", [K.srgb((0.20, 0.17, 0.13)), K.srgb((0.45, 0.40, 0.32)), K.srgb((0.10, 0.09, 0.08))], scale=4, rough=0.4, bump=0.1, stretch=(1, 1, 6))
M_TIMBER = S.bark_mat("M_ShipTimber", (0.30, 0.22, 0.14), (0.14, 0.10, 0.07), (0.40, 0.31, 0.20), scale=3.0, fissure=0.25, moss=0.0)
M_SAIL = K.noisy("M_Sail", [K.srgb((0.78, 0.72, 0.60)), K.srgb((0.68, 0.62, 0.50))], scale=8, rough=0.9, bump=0.2)
M_ROPE = plain("M_Rope", K.srgb((0.36, 0.30, 0.22)), rough=0.9)
M_EYE = plain("M_ShipEye", K.srgb((0.78, 0.74, 0.66)), rough=0.6)
M_SEA = S.water_mat("M_Sea", deep=(0.02, 0.06, 0.08), rough=0.08, ripple=0.4)
M_CITADEL = S.stone_mat("M_Citadel", (0.62, 0.56, 0.46), (0.35, 0.31, 0.25), (0.72, 0.66, 0.55), scale=0.6, rough=0.9, bump=0.2)
M_HILL = K.noisy("M_Hills", [K.srgb((0.36, 0.34, 0.24)), K.srgb((0.28, 0.27, 0.18)), K.srgb((0.44, 0.40, 0.30))], scale=0.05, rough=1.0, bump=0.0)
M_ROOF = K.noisy("M_Roofs", [K.srgb((0.45, 0.30, 0.22)), K.srgb((0.38, 0.25, 0.18))], scale=0.5, rough=0.9, bump=0.0)
IMG_PLANTS, CELLS = S.plant_atlas("A_DunePlants", ["tussock", "tussock", "sedge", "straw", "weed", "grass", "tallgrass", "straw"], seed=1200,
                                  greens=[(0.36, 0.40, 0.26), (0.42, 0.46, 0.30), (0.30, 0.34, 0.22), (0.48, 0.50, 0.36)],
                                  straw=[(0.62, 0.56, 0.40), (0.55, 0.48, 0.33), (0.70, 0.63, 0.46)])
M_MARRAM = image_mat("M_Marram", IMG_PLANTS, rough=0.65, alpha=True)

# ----------------------------------------------------------------------------- ground and sea
print("ground ...", flush=True)
GROUND = S.ground("Beach", M_SAND, 90.0, r0=2.5, NA=96, NR=32, attrs={"wet": wet_fn, "trodden": trodden_fn, "ash": ash_fn})
SEAO = S.water_surface("Sea", M_SEA, SEA_Z, lambda x, y: gz(x, y) < SEA_Z + 0.3, extent=900.0, step=12.0, centre=(0.0, 380.0))
# refine the sea near the shore: a finer strip (the swell needs vertices; the shore edge is hidden under the sand)
SEAN = S.water_surface("SeaNear", M_SEA, SEA_Z, lambda x, y: gz(x, y) < SEA_Z + 0.3 and y < 62, extent=160.0, step=2.5, centre=(0.0, 30.0))
bpy.data.objects.remove(SEAO, do_unlink=True)
SEAO = S.water_surface("Sea", M_SEA, SEA_Z - 0.06, lambda x, y: (y >= 40 or abs(x) > 60) and gz(x, y) < SEA_Z + 0.3, extent=1600.0, step=50.0, centre=(0.0, 600.0))
def foam_fn(p):
    d = p.y - shore_y(p.x)
    return max(0.0, 1.0 - d / 2.5) * (0.6 + 0.4 * (0.5 + 0.5 * n2(p.x, p.y, 2.0, 4.0)))
for o in (SEAN, SEAO): E8.water_attrs(o, foam_fn)

# ----------------------------------------------------------------------------- Telemachus's ship at anchor
print("ship ...", flush=True)
SHIP_C = Vector((-7.5, 24.0, SEA_Z)); SHIP_YAW = math.radians(18.0)      # bow toward +x' (to the right of the view, a three-quarter view)
L, BEAM, DEPTH = 17.0, 3.0, 1.35
def ship_p(x, y, z): return SHIP_C + Matrix.Rotation(SHIP_YAW, 3, 'Z') @ Vector((x, y, z))
def sheer(t):   # t in -1 (stern) .. 1 (bow): height of the gunwale above the waterline
    return 0.75 + 0.55 * (abs(t) ** 2.5) + (0.25 if t < 0 else 0.0) * abs(t) ** 4
def keel(t): return -0.55 + 0.35 * (abs(t) ** 3)
def halfbeam(t): return BEAM / 2 * (1 - abs(t) ** 2.2) ** 0.7 + 0.02
def hull():
    NS, NU = 28, 12
    verts = []; faces = []; uvs = []
    for i in range(NS + 1):
        t = -1 + 2 * i / NS
        for j in range(NU + 1):
            s = -1 + 2 * j / NU; ph = s * math.pi / 2
            y = halfbeam(t) * math.sin(ph); z = sheer(t) - (sheer(t) - keel(t)) * math.cos(ph) ** 1.3
            verts.append(tuple(ship_p(t * L / 2, y, z)))
    for i in range(NS):
        for j in range(NU):
            a = i * (NU + 1) + j; faces.append((a, a + 1, a + NU + 2, a + NU + 1))
    o = mesh_from("Hull", verts, faces, M_HULL, smooth=True)
    # make the faces face outward (and an inner skin: a hull is seen from inside too)
    orient(o, lambda c: (c - (SHIP_C + Vector((0, 0, 0.2)))) * Vector((1, 1, 0.3)))
    inner = mesh_from("HullInner", [tuple(Vector(v) + (SHIP_C - Vector(v)) * Vector((0.04, 0.04, 0)).length * 0) for v in verts], faces, M_TIMBER, smooth=True)
    # pull the inner skin in by 6 cm
    for v in inner.data.vertices:
        c = Vector((SHIP_C.x, SHIP_C.y, v.co.z)); d = (c - v.co); d.z = 0
        if d.length > 0.08: v.co += d.normalized() * 0.06
    orient(inner, lambda c: (SHIP_C + Vector((0, 0, 0.2)) - c) * Vector((1, 1, 0.3)))
    return o
hull()
# gunwale rails, thwarts, mast and yard with the furled sail, shipped oars, the stern post and the ram
for sd in (-1, 1):
    pts = [ship_p(t * L / 2, sd * halfbeam(t), sheer(t) + 0.03) for t in np.linspace(-0.97, 0.97, 18)]
    tube(f"Gunwale{sd}", pts, [0.06] * len(pts), M_TIMBER, sides=5)
for k in range(10):
    t = -0.65 + k * 0.14
    box(f"Thwart{k}", (0.22, halfbeam(t) * 2 - 0.1, 0.06), tuple(ship_p(t * L / 2, 0, sheer(t) - 0.35)), M_TIMBER, rot=(0, 0, SHIP_YAW))
stern = [ship_p(-L / 2 * 0.98, 0, sheer(-0.98) - 0.2), ship_p(-L / 2 - 0.4, 0, sheer(-1) + 0.6), ship_p(-L / 2 - 0.5, 0, sheer(-1) + 1.4), ship_p(-L / 2 - 0.2, 0, sheer(-1) + 2.0)]
tube("SternPost", stern, [0.14, 0.12, 0.10, 0.06], M_HULL, sides=6)
bow = [ship_p(L / 2 * 0.98, 0, sheer(0.98) - 0.3), ship_p(L / 2 + 0.25, 0, sheer(1) + 0.5), ship_p(L / 2 + 0.2, 0, sheer(1) + 0.9)]
tube("BowPost", bow, [0.13, 0.10, 0.08], M_HULL, sides=6)
tube("Ram", [ship_p(L / 2 * 0.9, 0, 0.0), ship_p(L / 2 + 1.1, 0, -0.05)], [0.16, 0.07], M_HULL, sides=6)
for sd in (-1, 1):   # the painted eye on each bow
    c = ship_p(L / 2 * 0.86, sd * (halfbeam(0.86) + 0.012), 0.55)
    o = sphere(f"Eye{sd}", 0.13, tuple(c), M_EYE, seg=10, scale=(1.6, 0.15, 0.9)); o.rotation_euler = (0, 0, SHIP_YAW)
MAST = ship_p(0.05 * L / 2, 0, 0.0)
MAST_H = 8.5
tube("Mast", [MAST + Vector((0, 0, -0.3)), MAST + Vector((0, 0, MAST_H))], [0.13, 0.07], M_TIMBER, sides=8)
yard_c = MAST + Vector((0, 0, MAST_H - 0.6)); ydir = Matrix.Rotation(SHIP_YAW, 3, 'Z') @ Vector((0, 1, 0))
tube("Yard", [yard_c - ydir * 4.2, yard_c + ydir * 4.2], [0.05, 0.05], M_TIMBER, sides=6)
# the furled sail: a fat lumpy roll lashed under the yard
SAILMB = MB()
NSEG = 22
furl_pts = [yard_c - ydir * 3.8 + ydir * 7.6 * (k / NSEG) + Vector((0, 0, -0.18 - 0.05 * math.sin(k / NSEG * math.pi))) for k in range(NSEG + 1)]
sail = tube("SailFurled", furl_pts, [0.10 + 0.06 * math.sin(k / NSEG * math.pi) + 0.02 * ((k % 3) == 0) for k in range(NSEG + 1)], M_SAIL, sides=8)
K.add_sway(sail, lambda p: 0.15)
for k in range(7):
    q = furl_pts[3 * k + 1] if 3 * k + 1 <= NSEG else furl_pts[-2]
    K.lathe(f"Gasket{k}", [(0.0, -0.05), (0.2, -0.04), (0.2, 0.04), (0.0, 0.05)], tuple(q), M_ROPE, steps=8, rot=(0, math.pi / 2, SHIP_YAW + math.pi / 2))
# stays and halyards
for (a, b_) in ((MAST + Vector((0, 0, MAST_H)), ship_p(L / 2 * 0.95, 0, sheer(0.95))), (MAST + Vector((0, 0, MAST_H)), ship_p(-L / 2 * 0.92, 0, sheer(-0.92))),
                (MAST + Vector((0, 0, MAST_H - 0.3)), ship_p(0.1, halfbeam(0.1), sheer(0.1))), (MAST + Vector((0, 0, MAST_H - 0.3)), ship_p(0.1, -halfbeam(0.1), sheer(0.1)))):
    tube("Stay", [a, (a + b_) / 2 - Vector((0, 0, 0.1)), b_], [0.015] * 3, M_ROPE, sides=3, caps=False)
# oars shipped fore and aft along the thwarts, the steering oar at the stern quarter
for k in range(10):
    sd = -1 if k % 2 else 1
    y = sd * (0.35 + 0.18 * (k // 2) % 3 * 0.25)
    tube(f"Oar{k}", [ship_p(-L * 0.36, y, sheer(-0.7) - 0.22 + 0.02 * k), ship_p(L * 0.34, y + sd * 0.1, sheer(0.68) - 0.2 + 0.02 * k)], [0.035, 0.03], M_TIMBER, sides=5)
st0 = ship_p(-L / 2 * 0.86, -halfbeam(-0.86) - 0.1, sheer(-0.86) + 0.5)
tube("SteeringOar", [st0, ship_p(-L / 2 * 0.98, -halfbeam(-0.86) - 0.45, -0.9)], [0.06, 0.05], M_TIMBER, sides=6)
box("SteeringBlade", (0.9, 0.05, 0.32), tuple(ship_p(-L / 2 * 0.98, -halfbeam(-0.86) - 0.45, -0.75)), M_TIMBER, rot=(0, 0.3, SHIP_YAW))
# anchor stones: ropes from the bow and stern down into the water
for (a, d_) in ((ship_p(L / 2 * 0.9, 0, sheer(0.9)), ship_p(L / 2 + 3.5, 1.0, -1.5)), (ship_p(-L / 2 * 0.9, 0, sheer(-0.9)), ship_p(-L / 2 - 3.5, -0.8, -1.5))):
    tube("AnchorRope", [a, a.lerp(d_, 0.5) - Vector((0, 0, 0.3)), d_], [0.02] * 3, M_ROPE, sides=4, caps=False)

# ----------------------------------------------------------------------------- the fires
print("fires ...", flush=True)
R = random.Random(5)
FIRE_PTS = []
MEAT_SPECS = []
def hearth(name, x, y, r, live=True, spits=True):
    z = gz(x, y)
    # a ring of stones
    specs = []
    for k in range(11):
        a = TWO_PI * k / 11 + R.uniform(-0.15, 0.15)
        specs.append((x + math.cos(a) * (r + 0.12), y + math.sin(a) * (r + 0.12), R.uniform(0.1, 0.17), R.randint(0, 9999), {"sub": 2, "bury": 0.45, "facet": 0.05, "squash": (1.0, 0.8, 0.6)}))
    S.rocks(f"{name}_ring", specs, M_STONE, sub=2)
    # the bed of embers, charred logs, thigh bones wrapped in fat on the embers
    o = sphere(f"{name}_embers", 1.0, (x, y, z - 0.02), M_EMBERS, seg=14, scale=(r, r * 0.9, 0.12))
    for k in range(5):
        a = R.uniform(0, math.pi); d = Vector((math.cos(a), math.sin(a), 0))
        L_ = r * R.uniform(1.4, 1.9)
        tube(f"{name}_log{k}", [Vector((x, y, z + 0.08)) - d * L_ / 2, Vector((x, y, z + 0.08 + 0.05 * R.random())) + d * L_ / 2], [0.06, 0.05], M_CHAR, sides=6)
    if live:
        for k in range(4):
            a = R.uniform(0, TWO_PI); d = Vector((math.cos(a), math.sin(a), 0)); c = Vector((x, y, z + 0.13)) + d * r * R.uniform(0.0, 0.4)
            dd = Vector((math.cos(a + 1.3), math.sin(a + 1.3), 0.0))
            tube(f"{name}_bone{k}", [c - dd * 0.2, c + Vector((0, 0, 0.02)), c + dd * 0.18], [0.045, 0.05, 0.04], M_BONE, sides=7)
    if spits:
        # forked stakes either side, a bronze spit across with pieces of meat, more spits leaning on the stones
        ax = Vector((1, 0.25, 0)).normalized()
        for sd in (-1, 1):
            p = Vector((x, y, z)) + ax * sd * (r + 0.45)
            tube(f"{name}_stake{sd}", [p + Vector((0, 0, -0.2)), p + Vector((0, 0, 0.62))], [0.035, 0.03], M_STAKE, sides=6)
            for f in (-1, 1):
                tube(f"{name}_fork{sd}{f}", [p + Vector((0, 0, 0.58)), p + Vector((0, 0, 0.72)) + Vector((-ax.y, ax.x, 0)) * f * 0.06], [0.022, 0.015], M_STAKE, sides=5)
        for q, hh in ((0.0, 0.66), (0.12, 0.64)):
            off = Vector((-ax.y, ax.x, 0)) * q
            a0 = Vector((x, y, z + hh)) - ax * (r + 0.6) + off; a1 = Vector((x, y, z + hh)) + ax * (r + 0.6) + off
            tube(f"{name}_spit{q}", [a0, a1], [0.009, 0.009], M_BRONZE, sides=5)
            for k in range(5):
                c = a0.lerp(a1, 0.25 + 0.5 * k / 4) + Vector((0, 0, -0.01))
                MEAT_SPECS.append((c, R.uniform(0.035, 0.05), R.randint(0, 9999)))
        # five-pronged forks stuck in the sand by the fire
        for k in range(2):
            a = R.uniform(0, TWO_PI); p = Vector((x, y, z)) + Vector((math.cos(a), math.sin(a), 0)) * (r + 0.9)
            tube(f"{name}_pempo{k}", [p + Vector((0, 0, -0.1)), p + Vector((0.08, 0.05, 1.1))], [0.02, 0.018], M_STAKE, sides=5)
            hd = p + Vector((0.08, 0.05, 1.1))
            for f in range(5):
                tube(f"{name}_prong{k}{f}", [hd, hd + Vector((0.03 * (f - 2), 0.0, 0.22))], [0.006, 0.003], M_BRONZE, sides=3, caps=False)
    FIRE_PTS.append(Vector((x, y, z + 0.15)))
for (x, y, r, nm) in FIRES: hearth(f"Fire_{nm}", x, y, r, live=True, spits=True)
for k, (x, y, r) in enumerate(EMBERS): hearth(f"Embers{k}", x, y, r, live=False, spits=(k < 2))
_bm = bmesh.new()
for (c, sz, sd_) in MEAT_SPECS:
    vs = S.rock_bm(_bm, (0, 0, 0), sz, random.Random(sd_), sub=1, bury=0.0, flat=0.0, facet=0.15, squash=(1.3, 0.9, 0.9))
    for v in vs: v.co += c
_me = bpy.data.meshes.new("Meat"); _bm.to_mesh(_me); _bm.free()
_mo = bpy.data.objects.new("Meat", _me); _me.materials.append(M_MEAT); link(_mo)
for _p in _me.polygons: _p.use_smooth = True

# Nestor's place: sheepskins on the sand round the fire (the reader stands on one), the golden cup, the mixing-bowl
def fleece(name, x, y, rx, ry, yaw, seed):
    Rf = random.Random(seed)
    bm = bmesh.new(); res = bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    Ry = Matrix.Rotation(yaw, 3, 'Z')
    for v in bm.verts:
        p = v.co.copy(); a = math.atan2(p.y, p.x); rr = p.length
        # a skin's outline: leg flaps at four corners, the neck, ragged edge
        edge = 1.0 + 0.18 * math.cos(4 * a + seed) + 0.08 * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, seed)))
        q = Ry @ Vector((p.x * rx * edge, p.y * ry * edge, 0))
        w = Vector((x, y, 0)) + q
        v.co = Vector((w.x, w.y, gz(w.x, w.y) + 0.035 * (1 - rr ** 3) + 0.012 * noise.noise(w * 6.0) + 0.012))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_FLEECE); link(o)
    for p in me.polygons: p.use_smooth = True
    orient(o, lambda c: (0, 0, 1))
    return o
fleece("Fleece0", 0.0, 0.05, 0.75, 0.55, 0.3, 1)
fleece("Fleece1", -1.1, 1.6, 0.7, 0.5, 1.2, 2)
fleece("Fleece2", 0.4, 3.6, 0.7, 0.5, -0.4, 3)
fleece("Fleece3", 2.9, 1.1, 0.65, 0.5, 2.0, 4)
fleece("Fleece4", 3.1, 3.4, 0.7, 0.55, 0.7, 5)
# the golden cup (a two-handled depas) on the fleece at the reader's right hand
CUP = Vector((0.85, 0.95, gz(0.85, 0.95) + 0.045))
lathe("GoldCup", [(0.0, 0.0), (0.035, 0.0), (0.04, 0.006), (0.012, 0.02), (0.012, 0.05), (0.035, 0.07), (0.055, 0.12), (0.06, 0.16), (0.056, 0.162),
                  (0.05, 0.12), (0.03, 0.08), (0.0, 0.075)], tuple(CUP), M_GOLD, steps=20)
for sd in (-1, 1):
    tube(f"CupHandle{sd}", [CUP + Vector((sd * 0.055, 0, 0.15)), CUP + Vector((sd * 0.09, 0, 0.17)), CUP + Vector((sd * 0.07, 0, 0.09))], [0.006] * 3, M_GOLD, sides=5)
# the bronze mixing-bowl (a krater) on its stand beside the fire, two more along the shore
for k, (x, y) in enumerate(((2.9, 2.25), (-7.0, 2.6), (8.6, 1.9))):
    zb = gz(x, y)
    lathe(f"Krater{k}", [(0.0, 0.02), (0.10, 0.0), (0.11, 0.04), (0.06, 0.08), (0.07, 0.13), (0.19, 0.24), (0.23, 0.36), (0.24, 0.42), (0.22, 0.43),
                         (0.20, 0.38), (0.0, 0.36)], (x, y, zb - 0.02), M_BRONZE, steps=24)
    for sd in (-1, 1):
        tube(f"KraterHandle{k}{sd}", [Vector((x + sd * 0.2, y, zb + 0.26)), Vector((x + sd * 0.29, y, zb + 0.33)), Vector((x + sd * 0.24, y, zb + 0.41))], [0.013] * 3, M_BRONZE, sides=5)
# baskets of barley and a stack of split driftwood by Nestor's fire
for k in range(6):
    a = R.uniform(-0.3, 0.3)
    tube(f"Woodpile{k}", [Vector((3.6, 0.2 + k * 0.12, gz(3.6, 0.2) + 0.05 + (k % 3) * 0.07)), Vector((4.5, 0.4 + k * 0.12 + a, gz(4.5, 0.4) + 0.05 + (k % 3) * 0.07))], [0.05, 0.04], M_DRIFT, sides=6)

# ----------------------------------------------------------------------------- the dunes: marram, driftwood, the bull-hides and horns
print("dunes ...", flush=True)
GMB = MB()
placed = 0
for i in range(30000):
    x = R.uniform(-45, 45); y = R.uniform(-30, 3)
    r = math.hypot(x, y)
    if r < 3.5 or r > 45: continue
    dune = smoothstep(-4.0, -9.0, y)
    dens = 0.12 + 0.85 * dune * (0.5 + 0.5 * n2(x, y, 4.0, 8.0))
    if any(math.hypot(x - fx_, y - fy_) < r_ + 2.5 for (fx_, fy_, r_) in FIRES_ALL): continue
    if R.random() > dens: continue
    kind = R.choices(["tussock", "sedge", "straw", "weed", "grass", "tallgrass"], weights=[5, 1.5, 2, 1, 1.5, 2])[0]
    h = {"tussock": 0.9, "sedge": 0.6, "straw": 0.8, "weed": 0.8, "grass": 0.45, "tallgrass": 1.0}[kind] * R.uniform(0.7, 1.3)
    plant(GMB, x, y, h, CELLS[kind], R, n=2 if r < 15 else 1, segs=2 if r < 12 else 1, wk=0.6)
    placed += 1
    if placed > 1000: break
GO = GMB.build("Marram", M_MARRAM); set_card_normals(GO, lambda p: Vector((0, 0, 1)))
# driftwood
for k in range(14):
    x = R.uniform(-30, 30); y = R.choice((R.uniform(-9, -5), shore_y(x) - R.uniform(0.6, 1.6)))
    if math.hypot(x, y) < 3 or any(math.hypot(x - fx_, y - fy_) < r_ + 1.5 for (fx_, fy_, r_) in FIRES_ALL): continue
    a = R.uniform(0, math.pi); d = Vector((math.cos(a), math.sin(a), 0)); Ld = R.uniform(1.0, 3.2)
    p0 = Vector((x, y, gz(x, y) + 0.04)); p1 = p0 + d * Ld; p1.z = gz(p1.x, p1.y) + 0.04
    tube(f"Drift{k}", [p0, p0.lerp(p1, 0.5) + Vector((0, 0, 0.05)), p1], [0.09, 0.07, 0.04], M_DRIFT, sides=6)
# the black hides of the bulls, laid over driftwood logs at the edge of the dunes, with the horns
def hide(name, x, y, yaw, seed):
    Rh = random.Random(seed)
    log0 = Vector((x, y, gz(x, y) + 0.25)); dl = Vector((math.cos(yaw), math.sin(yaw), 0))
    tube(f"{name}_log", [log0 - dl * 1.6, log0 + dl * 1.6], [0.2, 0.16], M_DRIFT, sides=8)
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=14, y_segments=10, size=1.0)
    Ry = Matrix.Rotation(yaw, 3, 'Z')
    for v in bm.verts:
        u, w = v.co.x, v.co.y
        edge = 1.0 + 0.12 * noise.noise(Vector((u * 2, w * 2, seed)))
        lx, ly = u * 1.3 * edge, w * 1.0 * edge
        q = Vector((x, y, 0)) + Ry @ Vector((lx, ly, 0))
        drape = 0.45 * math.exp(-(ly / 0.35) ** 2)        # over the log
        v.co = Vector((q.x, q.y, max(gz(q.x, q.y) + 0.03, gz(x, y) + drape)))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_HIDE); link(o)
    for p in me.polygons: p.use_smooth = True
    orient(o, lambda c: (0, 0, 1))
    # a pair of horns lying beside it
    c = Vector((x, y, 0)) + Ry @ Vector((1.6, 0.9, 0)); c.z = gz(c.x, c.y) + 0.06
    for sd in (-1, 1):
        pts = [c + Ry @ Vector((0, sd * 0.06, 0)), c + Ry @ Vector((0.1, sd * 0.25, 0.04)), c + Ry @ Vector((0.28, sd * 0.38, 0.1)), c + Ry @ Vector((0.42, sd * 0.36, 0.18))]
        tube(f"{name}_horn{sd}", pts, [0.06, 0.045, 0.03, 0.006], M_HORN, sides=8)
for k, (x, y, yaw) in enumerate(((-4.5, -5.6, 0.2), (5.5, -6.2, -0.3), (-13.0, -5.0, 0.6))):
    hide(f"Hide{k}", x, y, yaw, 70 + k)

# ----------------------------------------------------------------------------- far: the hills behind, the citadel of Pylos on its hill, headlands
print("far ...", flush=True)
def far_hills():
    verts = []; faces = []; N = 96; Rr = 420.0
    for i in range(N + 1):
        a = TWO_PI * i / N; az = math.degrees(a) % 360
        behind = smoothstep(70, 115, az) * smoothstep(290, 245, az)        # land only behind and to the sides
        hgt = (25 + 45 * (0.5 + 0.5 * n2(i, 0, 9.0, 3.0)) + 20 * n2(i, 0, 3.0, 5.0)) * behind + 2.0
        x, y = Rr * math.sin(a), Rr * math.cos(a)
        verts += [(x, y, SEA_Z + hgt), (x * 0.45, y * 0.45, SEA_Z - 2.0 + hgt * 0.2 * behind)]
    for i in range(N):
        az = math.degrees(TWO_PI * (i + 0.5) / N) % 360
        if not (75 < az < 285): continue          # no land on the sea horizon ahead
        q = 2 * i; faces.append((q, q + 2, q + 3, q + 1))
    o = mesh_from("FarHills", verts, faces, M_HILL, smooth=True)
    orient(o, lambda c: (-c.x, -c.y, 0.5))
    return o
far_hills()
# the citadel's hill (a mound behind-left) and its walls and halls
CIT = Vector((-60.0, -150.0, 0))
def cit_hill():
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for v in bm.verts:
        d = v.co.normalized(); w = 1 + 0.12 * noise.noise(d * 2.5)
        v.co = Vector((CIT.x + d.x * 75 * w, CIT.y + d.y * 55 * w, SEA_Z - 6 + max(-0.1, d.z) * 34 * w))
        if d.z > 0.55: v.co.z = SEA_Z - 6 + 0.82 * 34      # a flat top for the palace
    me = bpy.data.meshes.new("CitadelHill"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("CitadelHill", me); me.materials.append(M_HILL); link(o)
    for p in me.polygons: p.use_smooth = True
    return SEA_Z - 6 + 0.82 * 34
TOP = cit_hill()
for k in range(28):   # the circuit wall
    a = TWO_PI * k / 28; a2 = TWO_PI * (k + 1) / 28
    p0 = Vector((CIT.x + math.cos(a) * 34, CIT.y + math.sin(a) * 24, TOP)); p1 = Vector((CIT.x + math.cos(a2) * 34, CIT.y + math.sin(a2) * 24, TOP))
    c = (p0 + p1) / 2; d = p1 - p0
    box(f"CitWall{k}", (d.length + 0.3, 1.6, 4.5), tuple(c + Vector((0, 0, 1.0))), M_CITADEL, rot=(0, 0, math.atan2(d.y, d.x)))
for k, (dx, dy, w, d, h) in enumerate(((0, 0, 12, 20, 9), (-14, 6, 10, 8, 6), (14, -4, 9, 10, 6), (-6, -12, 8, 6, 5), (10, 12, 8, 7, 5))):
    p = Vector((CIT.x + dx, CIT.y + dy, TOP))
    box(f"CitHall{k}", (w, d, h), tuple(p + Vector((0, 0, h / 2))), M_CITADEL, rot=(0, 0, 0.3))
    box(f"CitRoof{k}", (w + 0.8, d + 0.8, 0.6), tuple(p + Vector((0, 0, h + 0.3))), M_ROOF, rot=(0, 0, 0.3))

# ----------------------------------------------------------------------------- sky and light
M_SKY = S.gradient_sky_mat("M_SkyDome", [(0.0, (1.0, 0.62, 0.36)), (0.07, (0.98, 0.64, 0.42)), (0.13, (0.80, 0.62, 0.55)), (0.3, (0.40, 0.48, 0.70)), (1.0, (0.16, 0.26, 0.52))],
                           sun_dir=SUN_DIR, glow=((3.0, 1.6, 0.7), 10.0), clouds=0.5, cloud_col=(0.95, 0.62, 0.48), strength=1.0)
SKY = E8.sky_dome("SkyDome", M_SKY, 900.0, seg=48, rings=14, el_min=-6.0)
K.apply_transforms()
light_obj("light.sun", 'SUN', 4.0, (1.0, 0.66, 0.40), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(1.2))
skl = light_obj("light.sky", 'SUN', 0.5, (0.55, 0.65, 0.95), (0, 0, 30), direction=(-0.1, 0.2, -1.0), angle=math.radians(80))
skl.data.use_shadow = False
for k, p in enumerate(FIRE_PTS[:3]):
    light_obj(f"Lamp.fire.{k}", 'POINT', 120.0, (1.0, 0.5, 0.18), tuple(p + Vector((0, 0, 0.35))), shadow_soft_size=0.3)
world = bpy.data.worlds.new("Dawn"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.30, 0.34, 0.45, 1); bg.inputs["Strength"].default_value = 0.6

# ----------------------------------------------------------------------------- markers, anchors, cameras
for (x, y, r, nm), p in zip(FIRES, FIRE_PTS): E8.fx(f"fx.fire.{nm}", tuple(p), r * 0.8)
sound("surf", "shore", (0.0, shore_y(0) + 1.0, SEA_Z + 0.3))
sound("fire", "nestor", tuple(FIRE_PTS[0]))
sound("gulls", "0", (-12.0, 30.0, 12.0))
sound("crowd", "guilds", (-12.0, 0.0, 1.5))
S.reader_anchors(0.0)
anchor("scene.centre", tuple(FIRE_PTS[0]))
anchor("shore.ship", tuple(SHIP_C + Vector((0, 0, 1.0))))
for o in K.COLL.objects:
    if o.type == 'MESH' and o.data.materials and o.data.materials[0].name in ("M_SkyDome",): o.visible_shadow = False
S.check_clear(look_yaw=0.0)

EZ = gz(0, 0) + EYE
E = Vector((0, 0, EZ))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EZ - 0.6), 17),
    ("Cam_Fire", (0.2, 0.6, EZ - 0.3), tuple(FIRE_PTS[0] + Vector((0.3, 0.1, 0.2))), 26),
    ("Cam_Ship", tuple(E), tuple(SHIP_C + Vector((0, 0, 2.5))), 30),
], pitch=-4.0)
S.finish("pylos-shore", "pylos_shore", cams,
         keep_names={"M_Sea": "water.ocean.sea", "M_Marram": "veg.grass.marram", "M_Sail": "cloth.sail.furled", "M_Sand": "GroundNear",
                     "M_SkyDome": "SkyDome", "M_Hills": "far.Hills", "M_Citadel": "far.Citadel", "M_Roofs": "far.Roofs"},
         keep_uv={"M_Sand"},
         size_for={"M_Sand": (2048, 256, 1024), "M_Hull": (1024, 128, 512), "M_ShipTimber": (1024, 64, 256), "M_Fleece": (1024, 64, 512),
                   "M_BullHide": (512, 64, 256), "M_Embers": (512, 64), "M_Bronze": (512, 128, 128), "M_Gold": (64, 32), "M_Driftwood": (512, 64, 256),
                   "M_Stakes": (256, 32, 128), "M_Charred": (256, 32, 128), "M_HearthStones": (512, 64, 256), "M_Meat": (128, 32, 64), "M_FatBone": (128, 32, 64),
                   "M_Horn": (128, 32, 64), "M_Sail": (256, 32, 128), "M_Rope": (32,), "M_ShipEye": (32,), "M_Citadel": (512, 32), "M_Hills": (512, 32),
                   "M_Roofs": (64, 32), "M_SkyDome": (1024,)},
         page=page, default_exposure=0.2, water_colour={"M_Sea": (0.02, 0.06, 0.08)}, unlit_emit={"M_Embers"})
