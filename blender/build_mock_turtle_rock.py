"""
Fable: the Mock Turtle's ledge of rock by the sea (Alice's Adventures in Wonderland, chapters 9 and 10, "The Mock
Turtle's Story", "The Lobster Quadrille").

"They had not gone far before they saw the Mock Turtle in the distance, sitting sad and lonely on a little ledge of
rock ..." "They very soon came upon a Gryphon, lying fast asleep in the sun." "So they sat down, and nobody spoke for
some minutes." "... you may SIT down ..." "... we went to school in the sea ..." "... the shingle ..."
"... the breeze that followed them ..."

The reader stands on the shingle at the top of a small beach, facing a low ledge of grey weathered rock (knee to
waist high, lichened, a flat sitting place on its top where the Mock Turtle sat, and a lower flat stone beside it where
Alice and the Gryphon sat down) with the calm sea beyond it, glittering in a warm, low afternoon sun. Rounded
shingle slopes down to wet dark sand at the waterline; seaweed and shells along the strand line; behind the reader,
a sunny patch of turf with coarse grass where the Gryphon lay asleep, and far off, the dark clipped hedges of the
Queen's garden. Open shingle round about for the dance. No creatures, no lobsters, no boats or piers, no tureen.

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py.

Node names the runtime relies on:
  anchor.reader.entrance (feet on the shingle, facing +Y: the ledge and the sea), anchor.reader.look,
  anchor.scene.centre (the ledge's seat)
  light.sun (SUN, warm afternoon, low), light.sky (SUN, fill)
  water.ocean.sea (COLOR_0.G foam at the waterline), veg.grass.turf
  sound.surf.shore, sound.gulls.0, sound.wind.0
  SkyDome, far.Headland, far.Hedges

Run headless:
  blender -b -P blender/build_mock_turtle_rock.py -- --render --quick --cpu --res 900 --cams reader
  blender -b -P blender/build_mock_turtle_rock.py -- --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b1 as S
from scene_kit_b1 import (K, E8, new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound, light_obj, camera,
                          link, smoothstep, lerp, n2, fbm2, orient, card, plant, set_card_normals, az_dir, TWO_PI)

ARGS = S.setup("mock-turtle-rock", 1865, "MockTurtleRock", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
SUN_AZ, SUN_EL = 235.0, 22.0       # afternoon, from the right-front over the sea, low enough for long shadows
SUN_DIR = (az_dir(SUN_AZ) * math.cos(math.radians(SUN_EL)) + Vector((0, 0, math.sin(math.radians(SUN_EL))))).normalized()
SUN_DIR = Vector((-0.55, 0.65, 0.38)).normalized()     # from ahead-left, over the sea (glitter in view, shadows toward the reader)
SEA = -1.6
LEDGE = Vector((0.4, 4.6, 0))

def shore_y(x): return 13.0 + 1.0 * math.sin(x * 0.07) + 0.3 * n2(x, 0, 6.0, 2.0)
def H(x, y):
    d = y - shore_y(x)
    if d < 0: z = SEA + min(-d, 16.0) * 0.105
    else: z = SEA - d * 0.08 - 0.5 * smoothstep(0, 25, d)
    z += 0.6 * smoothstep(-2.0, -10.0, y) + 0.8 * smoothstep(-8, -22, y) * (0.5 + 0.5 * n2(x, y, 9.0, 3.0))   # turf rising behind
    z += 0.04 * n2(x, y, 1.6, 7.0)
    return z
Z0 = H(0, 0)
def gz(x, y): return H(x, y) - Z0
SEA_Z = SEA - Z0
S.set_ground(gz)
def wet_fn(x, y): return smoothstep(-3.0, -0.6, y - shore_y(x))
def turf_fn(x, y): return smoothstep(-1.5, -4.5, y + 0.6 * n2(x, y, 4.0, 2.0))
def sand_fn(x, y): return smoothstep(-5.0, -2.0, y - shore_y(x))

def beach_mat(name="M_Shingle"):
    """rounded shingle (voronoi pebbles in greys, buff and slate-blue, each its own tone, dark gaps), going to coarse
    sand and wet dark sand at the waterline; a strand line of dried wrack and shells; turf with sandy patches behind."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    aw = node(nt, "ShaderNodeAttribute", (-2000, 700)); aw.attribute_name = "wet"
    at = node(nt, "ShaderNodeAttribute", (-2000, 550)); at.attribute_name = "turf"
    asd = node(nt, "ShaderNodeAttribute", (-2000, 400)); asd.attribute_name = "sand"
    wet, turf, sand = aw.outputs["Fac"], at.outputs["Fac"], asd.outputs["Fac"]
    v = voronoi_(nt, co, 9.0, 'F1', (-1800, 200)); v2 = voronoi_(nt, co, 22.0, 'F1', (-1800, 0))
    vs = node(nt, "ShaderNodeSeparateColor", (-1600, 200)); nt.links.new(v.outputs["Color"], vs.inputs["Color"])
    peb = ramp(nt, [(0.0, c4(K.srgb((0.42, 0.42, 0.42)))), (0.25, c4(K.srgb((0.58, 0.55, 0.50)))), (0.5, c4(K.srgb((0.68, 0.64, 0.56)))), (0.7, c4(K.srgb((0.40, 0.44, 0.50)))),
                    (0.85, c4(K.srgb((0.75, 0.72, 0.66)))), (1.0, c4(K.srgb((0.30, 0.29, 0.28))))], (-1400, 200))
    nt.links.new(vs.outputs[0], peb.inputs["Fac"])
    gap = maprange(nt, v.outputs["Distance"], 0.32, 0.5, 1.0, 0.35, (-1400, 0))
    gap2 = maprange(nt, v2.outputs["Distance"], 0.35, 0.5, 1.0, 0.6, (-1400, -150))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, peb.outputs["Color"], math_(nt, 'MULTIPLY', gap, gap2, (-1300, -50)), (-1100, 200))
    sandc = mix_rgb(nt, 'MIX', maprange(nt, noise_(nt, co, 3.0, 4, 0.6, loc=(-1600, -400)).outputs["Fac"], 0.3, 0.7, 0, 1, (-1400, -400)),
                    c4(K.srgb((0.62, 0.56, 0.44))), c4(K.srgb((0.72, 0.66, 0.52))), (-1200, -400))
    col = mix_rgb(nt, 'MIX', sand, col, sandc, (-900, 200))
    # strand line of wrack
    band = math_(nt, 'MULTIPLY', maprange(nt, wet, 0.0, 0.08, 0, 1, (-1400, -650)), maprange(nt, wet, 0.2, 0.1, 0, 1, (-1400, -750)), (-1250, -700))
    wr = maprange(nt, noise_(nt, co, 7.0, 4, 0.6, loc=(-1600, -850)).outputs["Fac"], 0.48, 0.6, 0, 1, (-1400, -850))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', band, wr, (-1100, -750)), col, c4(K.srgb((0.16, 0.13, 0.08))), (-750, 200))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', wet, 0.6, (-900, -900)), col, (0.55, 0.52, 0.48, 1), (-600, 200))
    # turf
    mp = node(nt, "ShaderNodeMapping", (-1800, 1000)); mp.inputs["Scale"].default_value = (12.0, 3.0, 12.0); mp.inputs["Rotation"].default_value = (0, 0, 0.4)
    nt.links.new(co, mp.inputs["Vector"])
    bl = noise_(nt, mp.outputs["Vector"], 8.0, 3, 0.6, 1.2, (-1600, 1000))
    tc = ramp(nt, [(0.0, c4(K.srgb((0.18, 0.22, 0.08)))), (0.5, c4(K.srgb((0.34, 0.40, 0.15)))), (0.8, c4(K.srgb((0.52, 0.52, 0.28)))), (1.0, c4(K.srgb((0.66, 0.60, 0.40))))], (-1400, 1000))
    nt.links.new(bl.outputs["Fac"], tc.inputs["Fac"])
    col = mix_rgb(nt, 'MIX', turf, col, tc.outputs["Color"], (-450, 200))
    col = K.ao_mul(nt, col, 0.15, 0.35, (-300, -1000))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, wet, 0.7, 0.25, (-400, -300)), b.inputs["Roughness"])
    b.inputs["Specular IOR Level"].default_value = 0.3
    hgt = mix_f(nt, turf, math_(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', gap, gap2, (-700, -1300)), math_(nt, 'SUBTRACT', 1.0, sand, (-800, -1400)), (-600, -1350)), bl.outputs["Fac"], (-450, -1350))
    bump_from(nt, b, hgt, 0.7, 0.03)
    return m

print("materials ...", flush=True)
M_BEACH = beach_mat()
M_LEDGE = S.stone_mat("M_LedgeRock", (0.36, 0.36, 0.34), (0.16, 0.16, 0.16), (0.48, 0.47, 0.44), scale=2.2, wet_z=SEA_Z + 0.5, wet_k=0.5,
                      moss=0.0, lichen=0.55, rough=0.82, bump=0.45, strata=1.0, cracks=0.25)
M_PEBBLE = S.stone_mat("M_Pebbles", (0.50, 0.48, 0.45), (0.30, 0.30, 0.30), (0.62, 0.60, 0.56), scale=3.0, wet_z=SEA_Z + 0.25, wet_k=0.5, lichen=0.0, rough=0.55, bump=0.08)
M_WRACK = K.noisy("M_Wrack", [K.srgb((0.20, 0.17, 0.08)), K.srgb((0.28, 0.24, 0.10)), K.srgb((0.12, 0.10, 0.05))], scale=10, rough=0.4, bump=0.3)
M_SHELL = K.noisy("M_Shells", [K.srgb((0.85, 0.80, 0.72)), K.srgb((0.70, 0.62, 0.55)), K.srgb((0.40, 0.42, 0.55))], scale=40, rough=0.4, bump=0.2)
M_SEA = S.water_mat("M_Sea", deep=(0.03, 0.09, 0.11), rough=0.05, ripple=0.3)
M_HEADLAND = K.noisy("M_Headland", [K.srgb((0.40, 0.42, 0.30)), K.srgb((0.50, 0.48, 0.38)), K.srgb((0.32, 0.36, 0.24))], scale=0.06, rough=1.0, bump=0.0)
M_HEDGE = S.crown_mass_mat("M_FarHedges", (0.03, 0.06, 0.02), (0.08, 0.14, 0.04), (0.14, 0.20, 0.07), scale=1.5)
IMG_PLANTS, CELLS = S.plant_atlas("A_TurfPlants", ["tussock", "tussock", "grass", "flowers", "sedge", "weed", "straw", "grass"], seed=1866,
                                  greens=[(0.28, 0.34, 0.14), (0.34, 0.40, 0.17), (0.40, 0.44, 0.20), (0.24, 0.30, 0.11)],
                                  straw=[(0.66, 0.58, 0.38), (0.58, 0.50, 0.32), (0.74, 0.66, 0.46)])
M_TURF = image_mat("M_TurfGrass", IMG_PLANTS, rough=0.6, alpha=True)
M_SKY = S.gradient_sky_mat("M_SkyDome", [(0.0, (0.86, 0.80, 0.70)), (0.06, (0.66, 0.74, 0.84)), (0.25, (0.38, 0.55, 0.82)), (1.0, (0.18, 0.36, 0.72))],
                           sun_dir=SUN_DIR, glow=((1.4, 1.0, 0.6), 20.0), clouds=0.35, cloud_col=(0.96, 0.90, 0.82))

# ----------------------------------------------------------------------------- ground and sea
print("ground ...", flush=True)
S.ground("Beach", M_BEACH, 90.0, r0=2.2, NA=96, NR=32, attrs={"wet": wet_fn, "turf": turf_fn, "sand": sand_fn})
SEAN = S.water_surface("SeaNear", M_SEA, SEA_Z, lambda x, y: gz(x, y) < SEA_Z + 0.3 and y < 70, extent=180.0, step=3.0, centre=(0.0, 40.0))
SEAF = S.water_surface("SeaFar", M_SEA, SEA_Z - 0.05, lambda x, y: y > 55, extent=2200.0, step=80.0, centre=(0.0, 1000.0))
for o in (SEAN, SEAF): E8.water_attrs(o, lambda p: max(0.0, 1.0 - (p.y - shore_y(p.x)) / 1.8) * 0.8)

# ----------------------------------------------------------------------------- the ledge of rock: layered, lichened, a flat seat on top, a lower flat stone beside
print("ledge ...", flush=True)
R = random.Random(9)
specs = []
UPPER = []
# the main ledge: a long low outcrop of bedded blocks running across the beach, its top a flat seat
for k in range(10):   # fallen blocks and outliers
    a = R.uniform(0, TWO_PI); r = R.uniform(2.8, 6.5)
    x, y = LEDGE.x + math.cos(a) * r * 1.3, LEDGE.y + math.sin(a) * r * 0.6 + 1.0
    if math.hypot(x, y) < 2.4: continue
    specs.append((x, y, R.uniform(0.25, 0.6), 60 + k, {"sub": 2, "bury": 0.45, "facet": 0.3, "squash": (1.0, 0.8, 0.55)}))
S.rocks("Ledge", specs, M_LEDGE, sub=3)
def ledge_outcrop(name, c, half, h, yaw, seed):
    """one continuous outcrop of bedded rock: a subdivided block pushed about by noise, its sides stepped into beds
    (strata) and its top left nearly flat (the Mock Turtle's seat), sunk into the shingle."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=8, use_grid_fill=True)
    Ry = Matrix.Rotation(yaw, 3, 'Z'); off = Vector((seed * 3.7, seed * 1.3, 0))
    for v in bm.verts:
        p = v.co.copy()
        zt = (p.z + 1) / 2                                   # 0 bottom .. 1 top
        # plan shape: rounded rectangle tapering a little upward, ragged outline
        k = 1.0 + 0.22 * noise.noise(Vector((p.x * 1.3, p.y * 1.3, zt * 2.0)) + off) - 0.18 * zt
        x, y = p.x * half[0] * k, p.y * half[1] * k
        # beds: the side steps in by bed (every 0.16 m), each bed's edge a little different
        bed = math.floor(zt * h / 0.16)
        inset = 0.06 * bed + 0.05 * noise.noise(Vector((bed * 1.7, seed, 0.5)))
        if abs(p.x) > 0.99 or abs(p.y) > 0.99:
            d = Vector((x, y, 0)); L = d.length
            if L > 1e-6: d = d / L * max(0.0, L - inset)
            x, y = d.x, d.y
        z = zt * h + (0.03 * noise.noise(Vector((x * 2, y * 2, 4.0)) + off) if zt > 0.99 else 0.0)
        w = Ry @ Vector((x, y, 0))
        v.co = Vector((c.x + w.x, c.y + w.y, gz(c.x + w.x, c.y + w.y) - 0.18 + z))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_LEDGE); link(o)
    for p_ in me.polygons: p_.use_smooth = True
    o.modifiers.new("EdgeSplit", 'EDGE_SPLIT').split_angle = math.radians(40)
    return o
ledge_outcrop("LedgeMain", LEDGE, (2.6, 0.95), 0.85, 0.08, 1)
ledge_outcrop("LedgeEnd", LEDGE + Vector((2.9, 0.6, 0)), (1.0, 0.8), 0.6, 0.5, 2)
ledge_outcrop("LedgeSeat", LEDGE + Vector((-1.5, -1.3, 0)), (0.6, 0.45), 0.42, 0.6, 3)
# shingle: loose pebbles on the beach surface near the reader (the texture carries the rest)
pspecs = []
for k in range(260):
    r = 9.0 * R.random() ** 0.8 + 0.5; a = R.uniform(0, TWO_PI); x, y = r * math.sin(a), r * math.cos(a)
    if turf_fn(x, y) > 0.3 or (abs(x) < 0.45 and 0 < y < 1.6): continue
    pspecs.append((x, y, R.uniform(0.025, 0.07), 1000 + k, {"sub": 1, "bury": 0.4, "facet": 0.0, "squash": (1.0, R.uniform(0.6, 0.9), R.uniform(0.35, 0.55))}))
S.rocks("Shingle", pspecs, M_PEBBLE, sub=1)
# wrack and shells along the strand line
WMB = MB()
for k in range(70):
    x = R.uniform(-14, 14); y = shore_y(x) - 2.6 + R.gauss(0, 0.3)
    if y < 1.6: continue
    a = R.uniform(0, math.pi); L = R.uniform(0.2, 0.7); d = Vector((math.cos(a), math.sin(a), 0))
    p0 = Vector((x, y, gz(x, y) + 0.01)); p1 = p0 + d * L; p1.z = gz(p1.x, p1.y) + 0.01
    tube(f"Wrack{k}", [p0, p0.lerp(p1, 0.5) + Vector((R.gauss(0, 0.05), R.gauss(0, 0.05), 0.02)), p1], [0.03, 0.025, 0.01], M_WRACK, sides=4)
for k in range(30):
    x = R.uniform(-8, 8); y = R.uniform(1.0, shore_y(0) - 1.0)
    if abs(x) < 0.5 and y < 2: continue
    o = sphere(f"Shell{k}", 0.025, (x, y, gz(x, y) + 0.006), M_SHELL, seg=8, scale=(1.0, 0.8, 0.35))
    o.rotation_euler = (0, 0, R.uniform(0, 3))
# turf behind with coarse grass tufts (the Gryphon's sunny patch)
GMB = MB(); placed = 0
for i in range(30000):
    x = R.uniform(-30, 30); y = R.uniform(-30, 0)
    if turf_fn(x, y) < 0.5 or math.hypot(x, y) > 30 or math.hypot(x, y) < 1.4: continue
    if R.random() > 0.45 * (0.5 + 0.5 * n2(x, y, 3.0, 4.0)): continue
    kind = R.choice(("tussock", "grass", "grass", "flowers", "sedge", "straw"))
    plant(GMB, x, y, R.uniform(0.25, 0.6), CELLS[kind], R, n=2 if abs(y) < 8 else 1, segs=2, wk=0.6)
    placed += 1
    if placed > 520: break
GO = GMB.build("TurfGrass", M_TURF); set_card_normals(GO, lambda p: Vector((0, 0, 1)))

# ----------------------------------------------------------------------------- far: headlands either side of the bay, the garden's hedges inland
def headland(name, cx, cy, rx, ry, h, seed):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for v in bm.verts:
        d = v.co.normalized(); w = 1 + 0.15 * noise.noise(d * 2.5 + Vector((seed, 0, 0)))
        v.co = Vector((cx + d.x * rx * w, cy + d.y * ry * w, SEA_Z - 3 + max(-0.05, d.z) * h * w))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_HEADLAND); link(o)
    for p in me.polygons: p.use_smooth = True
    return o
headland("HeadlandL", -230.0, 260.0, 200.0, 90.0, 38.0, 1)
headland("HeadlandR", 260.0, 330.0, 220.0, 100.0, 30.0, 2)
HMB = MB()
for k in range(30):
    x = -60 + k * 4.2; y = -70 + 3 * math.sin(k)
    S.lumps(HMB, Vector((x, y, gz(x * 0.5, -28) + 1.6)), 2.4, 1.8, 2, R, 500 + k, sub=1, sway=(0, 0.1), stretch=(1.6, 0.8))
HMB.build("FarHedges", M_HEDGE, sway=False)

SKY = E8.sky_dome("SkyDome", M_SKY, 1150.0, seg=48, rings=14, el_min=-4.0); SKY.visible_shadow = False
K.apply_transforms()
light_obj("light.sun", 'SUN', 4.2, (1.0, 0.86, 0.66), tuple(SUN_DIR * 50), direction=-SUN_DIR, angle=math.radians(1.0))
skl = light_obj("light.sky", 'SUN', 0.6, (0.60, 0.70, 0.95), (0, 0, 30), direction=(0.1, -0.2, -1.0), angle=math.radians(85))
skl.data.use_shadow = False
world = bpy.data.worlds.new("Afternoon"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.55, 0.62, 0.78, 1); bg.inputs["Strength"].default_value = 0.6

sound("surf", "shore", (0.0, shore_y(0) + 0.5, SEA_Z + 0.2)); sound("gulls", "0", (-14.0, 30.0, 14.0)); sound("wind", "0", (6.0, 4.0, 2.0))
S.reader_anchors(0.0)
anchor("scene.centre", (LEDGE.x, LEDGE.y, gz(LEDGE.x, LEDGE.y) + 0.8))
S.check_clear(look_yaw=0.0)
EZ = gz(0, 0) + EYE
E = Vector((0, 0, EZ))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EZ - 0.6), 17),
    ("Cam_Ledge", (2.5, 1.5, EZ - 0.2), (LEDGE.x, LEDGE.y, gz(LEDGE.x, LEDGE.y) + 0.5), 24),
], pitch=-5.0)
S.finish("mock-turtle-rock", "mock_turtle_rock", cams,
         keep_names={"M_Sea": "water.ocean.sea", "M_TurfGrass": "veg.grass.turf", "M_Shingle": "GroundNear", "M_SkyDome": "SkyDome",
                     "M_Headland": "far.Headland", "M_FarHedges": "far.Hedges"},
         keep_uv={"M_Shingle"},
         size_for={"M_Shingle": (2048, 256, 2048), "M_LedgeRock": (2048, 256, 1024), "M_Pebbles": (512, 64, 256), "M_Wrack": (128, 32, 64), "M_Shells": (64, 32),
                   "M_Headland": (512, 32), "M_FarHedges": (256, 32, 128), "M_SkyDome": (1024,)},
         page=page, default_exposure=0.0, water_colour={"M_Sea": (0.03, 0.09, 0.11)})
