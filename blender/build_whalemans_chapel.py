"""
Fable: the Whaleman's Chapel, New Bedford, on a stormy Sunday in December (Moby-Dick, chapters 7-9, "The Chapel",
"The Pulpit", "The Sermon").

"... a small scattered congregation of sailors, and sailors' wives and widows ... steadfastly eyeing several marble
tablets, with black borders, masoned into the wall on either side the pulpit." "... the pulpit ... was a very lofty
one, and since a regular stairs to its altitude would seriously contract the already small area of the chapel, the
architect ... had finished the pulpit without a stairs, substituting a perpendicular side ladder, like those used in
mounting a ship from a boat at sea ... a handsome pair of red worsted man-ropes for this ladder ... the side ladder
... was of cloth-covered rope, only the rounds were of wood ..." "Its panelled front was in the likeness of a ship's
bluff bows, and the Holy Bible rested on a projecting piece of scroll work, fashioned after a ship's fiddle-headed
beak." "... a large painting representing a gallant ship beating against a terrible storm off a lee coast of black
rocks and snowy breakers ... an angel's face ... a little isle of sunlight." "... by the murky light of that
darkened, doleful day ..."

The reader stands near the storm-pelted door at the back of the small whitewashed chapel, in the aisle by the last
bench, facing up the aisle to the lofty pulpit with its rope ladder and red man-ropes, the painting of the ship
in the storm behind it and the black-bordered marble tablets on either side. Plain painted pine benches either side,
worn floorboards, tall windows streaming with sleet giving a grey, murky light; wet hats and coats hang on pegs in
the corner by the door. No figures (the congregation's places are empty), no whale, no stained glass, no organ.

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py, pride_interior.py.

Node names the runtime relies on:
  anchor.reader.entrance (feet in the aisle by the door, facing +Y: the pulpit), anchor.reader.look,
  anchor.scene.centre (the pulpit), anchor.chapel.painting
  light.window.* (AREA: grey daylight at each window), light.sky (SUN, very dim fill, no shadow)
  sound.wind.storm (at the door), sound.rain.windows (the sleet on the east windows)

Run headless:
  blender -b -P blender/build_whalemans_chapel.py -- --render --quick --cpu --res 900 --cams reader
  blender -b -P blender/build_whalemans_chapel.py -- --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b1 as S
from scene_kit_b1 import (K, E8, new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound, light_obj, camera,
                          link, smoothstep, lerp, n2, fbm2, orient, card, set_card_normals, az_dir, TWO_PI)
import pride_interior as PI

ARGS = S.setup("whalemans-chapel", 1841, "WhalemansChapel", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
X0, X1, Y0, Y1, HGT = -5.0, 5.0, -1.6, 12.4, 6.4
R_ = PI.Room(X0, X1, Y0, Y1, HGT, t=0.4)

print("materials ...", flush=True)
M_PLASTER = PI.paint_mat("M_Whitewash", (0.74, 0.73, 0.69), rough=0.85, dirt=0.1)
M_PINE = PI.joinery_mat("M_PaintedPine", color=(0.60, 0.58, 0.52), rough=0.5)
M_FLOOR = PI.boards_mat("M_Floorboards", light=(0.36, 0.28, 0.20), dark=(0.20, 0.15, 0.10), width=0.16, axis='Y', wax=0.6)
M_MAHOG = PI.mahogany("M_Mahogany")
M_MARBLE = PI.marble("M_Marble", base=(0.80, 0.79, 0.76), vein=(0.55, 0.55, 0.55))
M_BLACK = plain("M_BlackMarble", (0.02, 0.02, 0.02), rough=0.25)
M_LETTER = plain("M_Lettering", (0.03, 0.03, 0.03), rough=0.5)
M_RED = K.noisy("M_RedWorsted", [K.srgb((0.55, 0.06, 0.05)), K.srgb((0.45, 0.04, 0.04))], scale=200, rough=0.9, bump=0.3, stretch=(1, 1, 8))
M_ROPE = K.noisy("M_ClothRope", [K.srgb((0.36, 0.18, 0.10)), K.srgb((0.28, 0.13, 0.07))], scale=120, rough=0.85, bump=0.3, stretch=(1, 1, 6))
M_GLASS = plain("M_SleetGlass", (0.30, 0.33, 0.36), rough=0.2, emission=(0.42, 0.46, 0.50), strength=0.6)
M_SASH = PI.joinery_mat("M_Sash", color=(0.68, 0.67, 0.62))
M_BIBLE = K.noisy("M_BibleCalf", [K.srgb((0.18, 0.10, 0.06)), K.srgb((0.25, 0.15, 0.08))], scale=20, rough=0.6, bump=0.2)
M_PAGES = plain("M_Pages", K.srgb((0.82, 0.78, 0.68)), rough=0.8)
M_TARP = K.noisy("M_Tarpaulin", [K.srgb((0.08, 0.08, 0.07)), K.srgb((0.14, 0.13, 0.11))], scale=6, rough=0.3, bump=0.1)
M_PILOT = K.noisy("M_PilotCloth", [K.srgb((0.07, 0.08, 0.12)), K.srgb((0.10, 0.11, 0.15))], scale=60, rough=0.95, bump=0.3)
M_IRON = plain("M_Iron", (0.04, 0.04, 0.04), rough=0.5, metallic=0.8)
M_STOVE = plain("M_Stove", (0.035, 0.033, 0.03), rough=0.6, metallic=0.5)

def storm_painting(W=1024, Hh=768, seed=5):
    """the painting behind the pulpit, in numpy: a dark storm sky with a rift of light (the little isle of sunlight
    with a pale angel's face in it), a black lee shore of rocks to the right with snowy breakers, a ship under
    reduced sail heeling hard, beating off; old varnish."""
    R = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:Hh, 0:W].astype(np.float32); u = xx / W; v = 1 - yy / Hh
    img = np.zeros((Hh, W, 4), np.float32); img[..., 3] = 1
    from scene_kit_b1 import K as _K
    import wotw_kit as WK
    sky_n = WK.fbm(u * 6, v * 4, 5, seed=3)
    sky = np.stack([0.10 + 0.12 * sky_n, 0.11 + 0.12 * sky_n, 0.12 + 0.13 * sky_n], -1)
    rift = np.exp(-(((u - 0.34) / 0.10) ** 2 + ((v - 0.78) / 0.07) ** 2))
    sky = sky * (1 - rift[..., None]) + np.array([0.95, 0.85, 0.55])[None, None] * rift[..., None]
    sea_n = WK.fbm(u * 18, v * 9, 5, seed=7)
    horizon = 0.42 + 0.03 * np.sin(u * 12)
    sea = np.stack([0.06 + 0.1 * sea_n, 0.10 + 0.12 * sea_n, 0.10 + 0.10 * sea_n], -1)
    foam = np.clip((sea_n - 0.62) * 6, 0, 1) * (v < horizon)
    sea = sea * (1 - foam[..., None]) + 0.85 * foam[..., None]
    col = np.where((v > horizon)[..., None], sky, sea)
    # the lee shore: black rocks on the right with breakers bursting white against them
    rocks = (u > 0.66) & (v < horizon + 0.25 * WK.fbm(u * 8, 0 * v, 3, seed=9) * (u - 0.6) * 3)
    col[rocks] = np.array([0.03, 0.03, 0.03])
    burst = np.exp(-(((u - 0.68) / 0.04) ** 2 + ((v - horizon - 0.05) / 0.08) ** 2)) * WK.fbm(u * 30, v * 30, 3, seed=11)
    col = col * (1 - np.clip(burst * 2, 0, 1)[..., None]) + np.clip(burst * 2, 0, 1)[..., None] * 0.9
    # the ship: a dark hull heeled over, two masts under close-reefed topsails
    sx, sy = 0.40, 0.40
    hull = (np.abs((u - sx) * np.cos(0.25) + (v - sy) * np.sin(0.25)) < 0.09) & (np.abs(-(u - sx) * np.sin(0.25) + (v - sy) * np.cos(0.25)) < 0.018)
    col[hull] = np.array([0.04, 0.035, 0.03])
    for mx in (-0.04, 0.03):
        mu = sx + mx; lean = 0.25
        for t in np.linspace(0, 1, 300):
            px = int((mu + t * 0.25 * math.sin(lean)) * W); py = int((1 - (sy + 0.015 + t * 0.25)) * Hh)
            if 0 <= px < W and 0 <= py < Hh: col[max(0, py - 1):py + 1, max(0, px - 1):px + 2] = np.array([0.05, 0.04, 0.03])
        sail = (np.abs(u - (mu + 0.12 * math.sin(lean) + 0.0)) < 0.035) & (v > sy + 0.10) & (v < sy + 0.16)
        col[sail] = np.array([0.62, 0.58, 0.48])
    # the angel's face in the light: a pale oval with soft features
    face = np.exp(-(((u - 0.34) / 0.018) ** 2 + ((v - 0.79) / 0.026) ** 2))
    col = col * (1 - face[..., None]) + face[..., None] * np.array([0.98, 0.90, 0.80])
    # varnish and craquelure
    col = col * np.array([0.92, 0.82, 0.62]) + 0.02 * R.rand(Hh, W, 1)
    img[..., :3] = np.clip(col * 1.8, 0, 1)
    return img
M_PAINTING = image_mat("M_Painting", np_image("A_StormPainting", storm_painting()), rough=0.35)
M_FRAME = PI.gilt("M_Gilt")

# ----------------------------------------------------------------------------- the shell: walls, windows, door, floor, ceiling
print("shell ...", flush=True)
WIN_U = [2.4, 6.4, 10.4]
glasses = []
for w in ('E', 'W'):
    for u in WIN_U:
        uu = u - Y0 if w == 'E' else (Y1 - Y0) - (u - Y0)
        glasses.append(PI.sash_window(f"Win{w}{u}", R_, w, uu, 1.3, 1.5, 3.3, M_SASH, M_GLASS, M_PINE, panes=(3, 6)))
R_.openings['S'].append((5.0, 1.5, 0.0, 2.6, "door"))
PI.build_walls(R_, M_PLASTER)
box("Floor", (X1 - X0, Y1 - Y0, 0.1), ((X0 + X1) / 2, (Y0 + Y1) / 2, -0.05), M_FLOOR)
box("Ceiling", (X1 - X0, Y1 - Y0, 0.1), ((X0 + X1) / 2, (Y0 + Y1) / 2, HGT + 0.05), M_PLASTER)
for k in range(6):   # plain cased beams across the ceiling
    box(f"Beam{k}", (X1 - X0, 0.22, 0.26), (0.0, Y0 + 1.2 + k * 2.4, HGT - 0.13), M_PINE)
PI.dado_panels(R_, M_PINE, rail_z=1.0, skirt=0.2, step=1.1, walls=('E', 'W', 'S'))
for w in ('E', 'W', 'S', 'N'):
    for (u0, u1) in PI.runs(R_, w, 0.0, 1.05):
        o, a, n, L = R_.wall_frame(w)
        c = o + a * ((u0 + u1) / 2) + n * 0.015
        box(f"Rail{w}{u0}", (abs(a.x) * (u1 - u0) + abs(n.x) * 0.04, abs(a.y) * (u1 - u0) + abs(n.y) * 0.04, 0.06), tuple(c + Vector((0, 0, 1.0))), M_PINE)
        box(f"Skirt{w}{u0}", (abs(a.x) * (u1 - u0) + abs(n.x) * 0.03, abs(a.y) * (u1 - u0) + abs(n.y) * 0.03, 0.2), tuple(c + Vector((0, 0, 0.1))), M_PINE)
# the storm-pelted door (shut), in its case
box("Door", (1.4, 0.06, 2.5), (0.0, Y0 - 0.12, 1.25), M_PINE, bevel=0.01)
for (dx, dz, sx, sz) in ((-0.78, 1.3, 0.12, 2.7), (0.78, 1.3, 0.12, 2.7), (0.0, 2.68, 1.7, 0.14)):
    box("DoorCase", (sx, 0.08, sz), (dx, Y0 + 0.02, dz), M_PINE)
for k in range(4):
    box(f"DoorPanel{k}", (0.5, 0.02, 0.9), (-0.32 + (k % 2) * 0.64, Y0 - 0.08, 0.6 + (k // 2) * 1.2), M_PINE, bevel=0.01)

# ----------------------------------------------------------------------------- benches either side of the aisle
print("benches ...", flush=True)
AISLE = 0.75
def bench(x0, x1, y):
    L = x1 - x0; cx = (x0 + x1) / 2
    box("BenchSeat", (L, 0.38, 0.04), (cx, y, 0.44), M_PINE, bevel=0.005)
    box("BenchBack", (L, 0.04, 0.5), (cx, y + 0.2, 0.75), M_PINE, bevel=0.005)
    box("BenchRail", (L, 0.05, 0.06), (cx, y + 0.21, 1.0), M_PINE, bevel=0.01)
    for x in (x0 + 0.03, x1 - 0.03):
        box("BenchEnd", (0.05, 0.5, 1.02), (x, y + 0.04, 0.51), M_PINE, bevel=0.008)
for k in range(9):
    y = 1.4 + k * 0.92
    bench(X0 + 0.35, -AISLE, y); bench(AISLE, X1 - 0.35, y)
# the back bench, beside which the reader stands
bench(X0 + 0.35, -AISLE, 0.35); bench(AISLE + 0.0, X1 - 0.35, 0.35)
# a cast-iron stove on the left, its pipe up to the ceiling
cyl("Stove", 0.3, 0.8, (X0 + 0.9, -0.6, 0.45), M_STOVE, verts=16)
tube("StovePipe", [Vector((X0 + 0.9, -0.6, 0.85)), Vector((X0 + 0.9, -0.6, 4.0)), Vector((X0 + 0.5, -0.6, 4.6)), Vector((X0 + 0.05, -0.6, 4.6))], [0.07] * 4, M_STOVE, sides=10)

# ----------------------------------------------------------------------------- the pulpit: a lofty ship's bow on a column, the side ladder with red man-ropes
print("pulpit ...", flush=True)
PY = Y1 - 1.1; PZ = 3.3
# the bow-shaped front: a lathe half-shell (bluff bows), panelled, mahogany-stained
bow = lathe("PulpitBow", [(0.0, -0.9), (0.55, -0.7), (0.85, -0.2), (0.95, 0.4), (0.98, 1.05), (0.0, 1.05)], (0.0, PY, PZ), M_MAHOG, steps=28)
bow.scale = (1.0, 0.75, 1.0)
bm = bmesh.new(); bm.from_mesh(bow.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > 0.02], context='VERTS')
bm.to_mesh(bow.data); bm.free()
box("PulpitBack", (1.96, 0.1, 2.0), (0.0, PY + 0.05, PZ + 0.05), M_MAHOG)
box("PulpitFloor", (1.9, 0.8, 0.06), (0.0, PY - 0.3, PZ + 0.0), M_MAHOG)
box("PulpitRail", (1.98, 0.75, 0.06), (0.0, PY - 0.33, PZ + 1.08), M_MAHOG, bevel=0.01)
for k in range(5):   # panel mouldings round the bow
    a = math.radians(-70 + 35 * k)
    p = Vector((math.sin(a) * 0.99, PY - math.cos(a) * 0.75 * 0.99, PZ + 0.3))
    o = box(f"BowPanel{k}", (0.32, 0.02, 0.9), tuple(p), M_MAHOG, bevel=0.01); o.rotation_euler = (0, 0, a)
# the column under it and the scroll beak with the Bible
lathe("PulpitColumn", [(0.0, 0.0), (0.45, 0.0), (0.42, 0.2), (0.28, 0.35), (0.25, PZ - 1.2), (0.6, PZ - 0.9), (0.0, PZ - 0.85)], (0.0, PY - 0.25, 0.0), M_MAHOG, steps=16)
beak = [Vector((0.0, PY - 0.72, PZ + 0.95)), Vector((0.0, PY - 1.05, PZ + 1.0)), Vector((0.0, PY - 1.2, PZ + 0.9)), Vector((0.0, PY - 1.12, PZ + 0.78))]
tube("FiddleBeak", beak, [0.09, 0.08, 0.06, 0.05], M_MAHOG, sides=8)
box("BookRest", (0.55, 0.42, 0.04), (0.0, PY - 0.92, PZ + 1.08), M_MAHOG, rot=(math.radians(-14), 0, 0))
BIB = Vector((0.0, PY - 0.92, PZ + 1.13))
for sd in (-1, 1):
    o = box(f"BibleCover{sd}", (0.24, 0.32, 0.03), tuple(BIB + Vector((sd * 0.12, 0, 0))), M_BIBLE); o.rotation_euler = (math.radians(-14), sd * 0.08, 0)
    o = box(f"BiblePages{sd}", (0.22, 0.30, 0.035), tuple(BIB + Vector((sd * 0.115, 0, 0.025))), M_PAGES); o.rotation_euler = (math.radians(-14), sd * 0.1, 0)
# the perpendicular side ladder on the right: cloth-covered rope sides, wooden rounds, red worsted man-ropes
LX = 1.25; LY = PY - 0.45
for sd in (-0.22, 0.22):
    tube(f"LadderSide{sd}", [Vector((LX, LY + sd, 0.0)), Vector((LX + 0.02, LY + sd, PZ + 0.1))], [0.022, 0.022], M_ROPE, sides=6)
for k in range(13):
    z = 0.3 + k * 0.25
    tube(f"Round{k}", [Vector((LX, LY - 0.22, z)), Vector((LX, LY + 0.22, z))], [0.018, 0.018], M_MAHOG, sides=6)
for sd in (-0.32, 0.32):
    top = Vector((LX - 0.15, LY + sd * 0.8, PZ + 1.05))
    tube(f"ManRope{sd}", [Vector((LX + 0.05, LY + sd, 0.15)), Vector((LX + 0.12, LY + sd, PZ * 0.5)), Vector((LX + 0.05, LY + sd, PZ + 0.6)), top],
         [0.03, 0.03, 0.03, 0.03], M_RED, sides=8)
    sphere(f"ManRopeKnot{sd}", 0.05, (LX + 0.05, LY + sd, 0.15), M_RED, seg=8)

# ----------------------------------------------------------------------------- the painting behind the pulpit and the marble tablets
PAINT_W, PAINT_H = 3.6, 2.7
PI.picture("StormPainting", R_, 'N', (X1 - X0) / 2, PZ + 2.2 - 0.6, PAINT_W, PAINT_H, M_FRAME, M_PAINTING)
# the canvas needs UVs for its image: the picture() canvas is a box; give its faces a planar UV
can = bpy.data.objects.get("StormPaintingCanvas")
if can:
    me = can.data; uvl = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    mw = can.matrix_world
    for li, lp in enumerate(me.loops):
        p = mw @ me.vertices[lp.vertex_index].co
        uvl.data[li].uv = ((-(p.x) + PAINT_W / 2) / PAINT_W, (p.z - (PZ + 2.2 - 0.6 - PAINT_H / 2)) / PAINT_H)
TABLETS = [("SACRED\nTO THE MEMORY OF\nJOHN TALBOT,\nLOST OVERBOARD\nNEAR THE ISLE OF DESOLATION,\nNOVEMBER 1ST, 1836.", -2.6),
           ("SACRED\nTO THE MEMORY OF\nA BOAT'S CREW\nOF THE SHIP ELIZA,\nTOWED OUT OF SIGHT BY A WHALE,\nDECEMBER 31ST, 1839.", 2.6),
           ("SACRED\nTO THE MEMORY OF\nCAPTAIN EZEKIEL HARDY,\nKILLED BY A SPERM WHALE\nON THE COAST OF JAPAN,\nAUGUST 3RD, 1833.", -3.9)]
TY_ = Y1 - 0.02
for k, (text, x) in enumerate(TABLETS):
    zc = 2.3 if k < 2 else 3.9
    box(f"TabletBorder{k}", (1.2, 0.05, 1.45), (x, TY_ - 0.025, zc), M_BLACK, bevel=0.01)
    box(f"Tablet{k}", (1.04, 0.06, 1.29), (x, TY_ - 0.035, zc), M_MARBLE, bevel=0.005)
    cu = bpy.data.curves.new(f"Inscription{k}", 'FONT'); cu.body = text; cu.size = 0.055; cu.space_line = 1.05
    cu.align_x = 'CENTER'; cu.align_y = 'CENTER'; cu.extrude = 0.0; cu.resolution_u = 1
    to = bpy.data.objects.new(f"Inscription{k}", cu); link(to)
    to.rotation_euler = (math.pi / 2, 0, math.pi); to.location = (x, TY_ - 0.068, zc)
    bpy.ops.object.select_all(action='DESELECT'); to.select_set(True); bpy.context.view_layer.objects.active = to
    bpy.ops.object.convert(target='MESH'); to.data.materials.append(M_LETTER)
    sc = min(1.0, 0.95 / max(0.01, to.dimensions.x), 1.15 / max(0.01, to.dimensions.y if to.dimensions.y > 0.02 else to.dimensions.z))
    to.scale = (sc, sc, sc)
box("TabletBorder3", (1.2, 0.05, 1.45), (3.9, TY_ - 0.025, 3.9), M_BLACK, bevel=0.01)
box("Tablet3", (1.04, 0.06, 1.29), (3.9, TY_ - 0.035, 3.9), M_MARBLE, bevel=0.005)

# ----------------------------------------------------------------------------- the coat corner by the door: wet tarpaulin hats, pilot-cloth jackets on pegs
box("PegRail", (0.06, 1.6, 0.12), (X1 - 0.05, -0.6, 1.75), M_PINE)
for k in range(4):
    y = -1.25 + k * 0.42
    tube(f"Peg{k}", [Vector((X1 - 0.08, y, 1.75)), Vector((X1 - 0.22, y, 1.8))], [0.015, 0.012], M_PINE, sides=6)
for k, y in enumerate((-1.25, -0.41)):
    # a hanging jacket: a lumpy flattened bag shape off the peg
    sphere(f"Jacket{k}", 1.0, (X1 - 0.2, y, 1.25), M_PILOT, seg=12, scale=(0.14, 0.24, 0.5))
for k, y in enumerate((-0.83, 0.01)):
    o = lathe(f"Sou'wester{k}", [(0.0, 0.16), (0.09, 0.15), (0.11, 0.06), (0.17, 0.0), (0.2, -0.04), (0.0, -0.02)], (X1 - 0.24, y, 1.68), M_TARP, steps=16)
    o.rotation_euler = (0, math.radians(-70), 0)
# wet footprints from the door up the aisle (darker floorboards): a few flat, slightly glossy decals
for k in range(8):
    y = Y0 + 0.4 + k * 0.42; x = (0.12 if k % 2 else -0.12)
    o = box(f"WetPrint{k}", (0.1, 0.24, 0.002), (x, y, 0.001), plain("M_Wet", (0.10, 0.08, 0.06), rough=0.1))

# ----------------------------------------------------------------------------- light: grey storm daylight at the windows, a dim fill
K.apply_transforms()
for w, xs in (('E', X1 + 0.6), ('W', X0 - 0.6)):
    for u in WIN_U:
        L = light_obj(f"light.window.{w}{u}", 'AREA', 650.0 if w == 'E' else 450.0, (0.78, 0.84, 0.92), (xs, u, 3.2), direction=(-1 if w == 'E' else 1, 0, -0.25))
        L.data.shape = 'RECTANGLE'; L.data.size = 1.3; L.data.size_y = 3.2
skl = light_obj("light.sky", 'SUN', 0.06, (0.7, 0.75, 0.85), (0, 0, 20), direction=(0.2, 0.3, -1.0), angle=math.radians(80))
skl.data.use_shadow = False
world = bpy.data.worlds.new("Storm"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.35, 0.38, 0.42, 1); bg.inputs["Strength"].default_value = 0.5

sound("wind", "storm", (0.0, Y0 - 0.5, 2.0))
sound("rain", "windows", (X1 + 0.3, 6.4, 3.0))
S.reader_anchors(0.0)
anchor("scene.centre", (0.0, PY - 0.6, PZ + 1.0))
anchor("chapel.painting", (0.0, Y1 - 0.1, PZ + 1.6))
S.check_clear(look_yaw=0.0)
E = Vector((0, 0, EYE))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EYE + 0.5), 17),
    ("Cam_Pulpit", (0.0, 4.0, 1.7), (0.0, PY - 0.5, PZ + 1.0), 24),
    ("Cam_Tablets", (-1.5, 6.5, 2.0), (-2.6, Y1, 2.6), 28),
    ("Cam_Painting", (0.0, 5.0, 2.5), (0.0, Y1, PZ + 1.6), 30),
], pitch=6.0)
S.finish("whalemans-chapel", "whalemans_chapel", cams, keep_names={"M_Painting": "MESH_Painting"},
         keep_uv=set(),
         size_for={"M_Whitewash": (2048, 64, 512), "M_PaintedPine": (2048, 64, 512), "M_Floorboards": (2048, 256, 1024), "M_Mahogany": (1024, 128, 512),
                   "M_Marble": (512, 64), "M_BlackMarble": (32,), "M_Lettering": (32,), "M_RedWorsted": (128, 32, 64), "M_ClothRope": (128, 32, 64),
                   "M_SleetGlass": (64,), "M_Sash": (512, 32, 128), "M_BibleCalf": (64, 32), "M_Pages": (32,), "M_Tarpaulin": (128, 32), "M_PilotCloth": (128, 32, 64),
                   "M_Iron": (32,), "M_Stove": (128, 32), "M_Gilt": (256, 64, 128), "M_Wet": (32,)},
         page=page, default_exposure=0.5, unlit_emit={"M_SleetGlass"})
