"""
Fable step-in room `cyclops-cave`: Polyphemus's cave in the land of the Cyclopes, in the evening (The Odyssey,
Book IX, Butler's translation).

"We soon reached his cave, but he was out shepherding, so we went inside and took stock of all that we could see.
His cheese-racks were loaded with cheeses, and he had more lambs and kids than his pens could hold. They were kept in
separate flocks; first there were the hoggets, then the oldlings, and lastly the very young ones all kept apart from
one another; as for his dairy, all the vessels, bowls, and milk pails into which he milked, were swimming with whey
... he had brought in a huge load of dry firewood to light the fire for his supper ... he rolled a huge stone to the
mouth of the cave - so huge that two and twenty strong four-wheeled waggons would not be enough to draw it ...
The Cyclops had a great club which was lying near one of the sheep pens; it was of green olive wood."

One great limestone cavern about 14 x 10 m under a vault 8 m high, everything in it at the giant's scale: wattle
pens taller than a man, deep in straw and dung (the flocks are not modelled: no animals, as a toy-like animal is worse
than an empty pen), racks of woven withies loaded with cheeses a metre across, wooden milk bowls and wicker
strainers swimming with whey, the great club of green olive wood lying by a pen, a heap of dry firewood thrown down
by the hearth and a small fire, and the mouth blocked by the huge stone with a thin line of evening daylight round
it. The reader stands among the pens at the back of the cave, facing the fire and the blocked mouth.
No dead men or gore, no stake, no metal tools.

Run (from the repo root), one Blender job at a time through the shared slot wrapper:
  blender_slot.sh -b -P blender/build_cyclops_cave.py -- --cpu --render --samples 40 --res 1280
  blender_slot.sh -b -P blender/build_cyclops_cave.py -- --export
  then blender/runtime_bake.py (--indoor) and tools/publish_scene_room.py (docs/SCENE_ROOMS_PIPELINE.md)
Axes: metres, +Z up; the mouth is in the south (-Y), the reader at the back faces south.
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, Euler, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b3 as K
import roomkit as rk
import pride_kit as pk

ARGS = K.setup("cyclops-cave", seed=909, samples=40)
if ARGS.cpu: bpy.context.scene.cycles.device = 'CPU'
R = random.Random(909)

# ----------------------------------------------------------------------------- materials
ROCK = K.stone_mat("cave_limestone", (0.50, 0.46, 0.40), dark=(0.30, 0.27, 0.23), lichen=None, scale=0.9, rough=0.9, bump=0.8)
SOOTROCK = K.stone_mat("smoked_limestone", (0.30, 0.27, 0.24), dark=(0.16, 0.14, 0.12), scale=0.9, rough=0.9, bump=0.8)
FLOOR = K.patchy_mat("dung_earth", (0.30, 0.25, 0.19), patches=[((0.48, 0.42, 0.26), 0.5, 0.35), ((0.16, 0.13, 0.10), 1.2, 0.3), ((0.40, 0.36, 0.30), 0.2, 0.2)], rough=0.95, bump=0.5)
STRAW = K.patchy_mat("straw", (0.66, 0.56, 0.32), patches=[((0.45, 0.38, 0.22), 3.0, 0.35), ((0.30, 0.24, 0.16), 1.0, 0.25)], rough=0.95, bump=0.6)
WATTLE = K.mat("wattle", (0.40, 0.32, 0.22), "bark", rough=0.9)
STAKE = K.mat("stakes", (0.30, 0.24, 0.17), "bark", rough=0.9)
OLIVE = K.mat("green_olive", (0.34, 0.36, 0.26), "bark", rough=0.85)
OLIVEWOOD = K.mat("olive_heartwood", (0.62, 0.55, 0.38), "wood", rough=0.7)
CHEESE = K.mat("cheese_rind", (0.80, 0.70, 0.46), "soil", rough=0.8)
WOODB = K.mat("bowl_wood", (0.42, 0.30, 0.18), "wood", rough=0.6)
WHEY = K.mat("whey", (0.86, 0.85, 0.76), "water", rough=0.15)
WICKER = K.mat("wicker", (0.62, 0.52, 0.34), "bark", rough=0.85)
DRYWOOD = K.mat("dry_firewood", (0.40, 0.33, 0.24), "bark", rough=0.9)
EMBER = K.emit_mat("embers", (1.0, 0.36, 0.08), 4.0)
FLAME = K.emit_mat("flame", (1.0, 0.62, 0.24), 6.0)
DAYLIGHT = K.emit_mat("evening_daylight", (1.0, 0.82, 0.60), 3.0)
K.size(ROCK, 2048, 256); K.size(FLOOR, 2048, 128); K.size(STRAW, 1024, 64)

# ----------------------------------------------------------------------------- the cavern: a vaulted shell of rock, the earth floor
AX, AY, AZ = 7.6, 6.2, 8.2
MOUTH_W, MOUTH_H = 5.6, 5.4
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=56, v_segments=28, radius=1.0)
off = Vector((3.1, 1.7, 0.4))
for v in bm.verts:
    n = v.co.normalized()
    d = 1.0 + 0.16 * noise.fractal(n * 2.2 + off, 0.55, 2.0, 4) + 0.06 * noise.noise(n * 7.0 + off)
    p = Vector((n.x * AX, n.y * AY, n.z * AZ)) * d
    if p.z < 0.0: p.z *= 0.15
    v.co = p
bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
# open the mouth in the south wall
kill = [f for f in bm.faces if (lambda c: c.y < -AY * 0.55 and (c.x / (MOUTH_W / 2)) ** 2 + (max(c.z, 0.0) / MOUTH_H) ** 2 < 1.0)(f.calc_center_median())]
bmesh.ops.delete(bm, geom=kill, context='FACES')
# keep only what is above the floor (the floor is its own mesh)
low = [f for f in bm.faces if max(v.co.z for v in f.verts) < -0.2]
bmesh.ops.delete(bm, geom=low, context='FACES')
cave = rk._obj("cave_shell", bm, ROCK, smooth=True)
# soot over the hearth: a darker skin on the vault above the fire
HC = Vector((0.4, -1.6, 0.0))
sb = bmesh.new(); bmesh.ops.create_uvsphere(sb, u_segments=20, v_segments=8, radius=1.0)
for v in sb.verts:
    n = v.co.normalized()
    if n.z < 0.55: continue
for v in sb.verts:
    n = v.co.normalized()
    d = 1.0 + 0.16 * noise.fractal(Vector((n.x * AX, n.y * AY, n.z * AZ)).normalized() * 2.2 + off, 0.55, 2.0, 4)
    v.co = Vector((n.x * AX, n.y * AY, n.z * AZ)) * d * 0.985
bmesh.ops.delete(sb, geom=[f for f in sb.faces if f.calc_center_median().normalized().z < 0.72 or (f.calc_center_median() - Vector((HC.x, HC.y, AZ))).length > 4.0], context='FACES')
bmesh.ops.reverse_faces(sb, faces=list(sb.faces))
rk._obj("vault_soot", sb, SOOTROCK, smooth=True)


def floor_h(x, y):
    return 0.06 * K.fbm(x, y, 1.5, 3, 2.0) + 0.04 * K.fbm(x, y, 0.4, 2, 5.0)


K.polar_terrain("cave_floor", floor_h, FLOOR, centre=(0.0, 0.0), r_max=9.5, near_step=0.35, k=0.12, ns=64)
# the threshold beyond the stone: earth sloping out, the daylit evening outside (seen only through the gaps)
rk.box("outside_glow", (MOUTH_W + 3.0, 0.3, MOUTH_H + 2.0), (0.0, -AY * 1.05 - 3.0, -0.5), DAYLIGHT)
# the door-stone: a huge rough boulder filling the mouth, a hand's breadth short of the rock all round
st = bmesh.new(); bmesh.ops.create_icosphere(st, subdivisions=3, radius=1.0)
so = Vector((7.7, 2.2, 5.1))
for v in st.verts:
    n = v.co.normalized()
    d = 1.0 + 0.12 * noise.fractal(n * 1.8 + so, 0.5, 2.0, 4)
    v.co = Vector((n.x * (MOUTH_W / 2 + 0.45), n.y * 1.8, n.z * (MOUTH_H / 2 + 0.35))) * d + Vector((0.0, -AY * 0.86, MOUTH_H / 2 - 0.25))
rk._obj("door_stone", st, ROCK, smooth=True)

# ----------------------------------------------------------------------------- the hearth, its small fire, the heap of firewood
F = rk._B("hearth")
for k in range(11):
    a = 2 * math.pi * k / 11
    K.rough_block(F, SOOTROCK, (0.6, 0.45, 0.35), (HC.x + math.cos(a) * 1.2, HC.y + math.sin(a) * 1.0, -0.12), (0, 0, math.degrees(a)), amp=0.06, seed=k)
for k in range(5):
    a = R.uniform(0, 3.14)
    d = Vector((math.cos(a), math.sin(a), 0))
    F.seg(DRYWOOD, tuple(HC - d * 0.6 + Vector((0, 0, 0.08))), tuple(HC + d * 0.6 + Vector((0, 0, 0.18))), 0.09, 0.08, 7)
for k in range(14):
    F.ball(EMBER, R.uniform(0.05, 0.1), (HC.x + R.uniform(-0.5, 0.5), HC.y + R.uniform(-0.4, 0.4), 0.05), squash=(1.3, 1.0, 0.5), sub=0)
F.done()
WD = rk._B("firewood")
for k in range(34):
    c = Vector((HC.x + 3.0 + R.uniform(-1.2, 1.2), HC.y + R.uniform(-1.0, 1.2), 0.15 + R.uniform(0, 0.9) * (1 - abs(R.uniform(-1, 1)))))
    a = R.uniform(0, 3.14); L = R.uniform(2.0, 4.5); d = Vector((math.cos(a), math.sin(a), R.uniform(-0.15, 0.15)))
    WD.seg(DRYWOOD, tuple(c - d * L / 2), tuple(c + d * L / 2), R.uniform(0.1, 0.22), R.uniform(0.07, 0.14), 6)
WD.done()

# ----------------------------------------------------------------------------- the pens: giant wattle hurdles, deep straw
PE = rk._B("pens")


def hurdle(a, b_, h=2.6):
    """A wattle hurdle from a to b: stakes every 0.5 m, withies woven between them in and out."""
    a, b_ = Vector((a[0], a[1], 0.0)), Vector((b_[0], b_[1], 0.0)); L = (b_ - a).length; d = (b_ - a).normalized(); n = Vector((-d.y, d.x, 0))
    ns = max(2, int(L / 0.55))
    for i in range(ns + 1):
        p = a + d * (L * i / ns)
        PE.seg(STAKE, (p.x, p.y, -0.2), (p.x + R.gauss(0, 0.03), p.y + R.gauss(0, 0.03), h + R.uniform(0.0, 0.25)), 0.07, 0.055, 6)
    for j in range(int(h / 0.15)):
        z = 0.2 + j * 0.15
        pts = []
        for i in range(ns * 2 + 1):
            p = a + d * (L * i / (ns * 2)) + n * (0.055 if (i + j) % 2 else -0.055)
            pts.append(Vector((p.x, p.y, z + R.gauss(0, 0.02))))
        PE.tube(WATTLE, pts, [0.05] * len(pts), 4)


# three pens across the back of the cave, the reader standing in the gangway between them
hurdle((-6.4, 1.4), (-1.6, 1.4)); hurdle((-1.6, 1.4), (-1.6, 4.6)); hurdle((-4.0, 1.4), (-4.0, 4.0))
hurdle((1.6, 1.6), (6.4, 1.6)); hurdle((1.6, 1.6), (1.6, 4.8))
hurdle((-1.0, 5.4), (1.2, 5.4), h=2.2)
PE.done()
SW = rk._B("straw")
for (x0, x1, y0, y1) in ((-6.2, -1.8, 1.6, 5.2), (1.8, 6.2, 1.8, 5.2)):
    for k in range(26):
        x, y = R.uniform(x0, x1), R.uniform(y0, y1)
        if math.hypot(x / AX, y / AY) > 0.95: continue
        rr = R.uniform(0.6, 1.2)
        K.scrub(SW, STRAW, (x, y, -0.05), rr, rr * 0.5, seed=k)
SW.done()
# the great club of green olive wood, lying along the right-hand pen, its bark on, a few lopped branch stubs
CL = rk._B("club")
ca, cb = Vector((2.2, 1.0, 0.35)), Vector((10.0, 0.0, 0.0)) * 0 + Vector((6.0, -2.6, 0.3))
pts = [ca.lerp(cb, t) + Vector((0.0, 0.0, 0.05 * math.sin(t * 9.0))) for t in np.linspace(0, 1, 8)]
CL.tube(OLIVE, pts, [0.38 - 0.15 * t for t in np.linspace(0, 1, 8)], 10)
CL.cyl(OLIVEWOOD, 0.38, 0.02, tuple(ca + Vector((0, 0, -0.38))), sides=10)
for t in (0.25, 0.5, 0.72):
    p = ca.lerp(cb, t); d = (cb - ca).normalized()
    CL.seg(OLIVE, tuple(p), tuple(p + Vector((-d.y, d.x, 0.6)) * 0.45), 0.09, 0.07, 6)
CL.done()

# ----------------------------------------------------------------------------- the dairy: cheese racks, milk bowls, strainers
RK = rk._B("cheese_racks", (AX * 0.84, -0.6, 0.0), 90)
for sx in (-1, 1):
    for sy in (-1, 1): RK.seg(STAKE, (sx * 2.2, sy * 0.55, -0.1), (sx * 2.2, sy * 0.55, 4.6), 0.1, 0.09, 6)
for k, zz in enumerate((0.9, 2.0, 3.1, 4.2)):
    for j in range(9):
        RK.seg(WICKER, (-2.3, -0.6 + j * 0.15, zz), (2.3, -0.6 + j * 0.15, zz), 0.035, 0.035, 4)
    x = -1.7
    while x < 1.8:
        rr = R.uniform(0.42, 0.55)
        if R.random() < 0.85:
            RK.cyl(CHEESE, rr, R.uniform(0.25, 0.35), (x, R.uniform(-0.1, 0.1), zz + 0.04), sides=18)
        x += rr * 2 + R.uniform(0.05, 0.15)
RK.done()
for k, (x, y, r) in enumerate(((-AX * 0.72, -1.0, 0.85), (-AX * 0.64, -2.8, 0.7), (-AX * 0.78, 0.8, 0.75))):
    pk.lathe(f"MilkBowl{k}", [(0.0, 0.0), (r * 0.6, 0.0), (r, r * 0.4), (r * 1.05, r * 0.7), (r * 0.98, r * 0.72), (r * 0.9, r * 0.45), (0.0, r * 0.12)], (x, y, 0.0), WOODB, steps=24)
    pk.cyl(f"Whey{k}", r * 0.92, 0.02, (x, y, r * 0.58), WHEY, verts=20)
for k, (x, y) in enumerate(((-AX * 0.6, 1.2), (-AX * 0.55, -0.2))):
    pk.lathe(f"Strainer{k}", [(0.0, 0.0), (0.35, 0.0), (0.7, 0.55), (0.72, 0.6), (0.66, 0.6), (0.3, 0.06), (0.0, 0.06)], (x, y, 0.0), WICKER, steps=16, rot=(0.0, 0.0, 0.0))
pk.lathe("MilkPail", [(0.0, 0.0), (0.5, 0.0), (0.55, 0.9), (0.5, 0.9), (0.45, 0.06), (0.0, 0.06)], (-AX * 0.5, -3.4, 0.0), WOODB, steps=20)

# ----------------------------------------------------------------------------- light, sound, reader
rk.lamp("fire", (HC.x, HC.y, 0.7), power=380, color=(1.0, 0.62, 0.34), radius=0.35)
rk.area_light("mouth_gap", (0.0, -AY * 0.7, MOUTH_H * 0.9), (MOUTH_W, 0.4), 60, color=(1.0, 0.82, 0.6), aim=(0, 1, 0.05))
rk.lamp("fill", (0.0, 1.0, 5.5), power=50, color=(0.70, 0.74, 0.85), radius=2.5)
w = bpy.context.scene.world
for n in list(w.node_tree.nodes): w.node_tree.nodes.remove(n)
bg = w.node_tree.nodes.new("ShaderNodeBackground"); out = w.node_tree.nodes.new("ShaderNodeOutputWorld")
bg.inputs["Color"].default_value = (0.01, 0.01, 0.01, 1); w.node_tree.links.new(bg.outputs[0], out.inputs[0])
K.fx("fire", "hearth", (HC.x, HC.y, 0.12), 0.5)
K.sound("fire", "hearth", (HC.x, HC.y, 0.4))
K.sound("wind", "mouth", (0.0, -AY * 0.9, 1.5))
E, D = K.reader((0.0, 3.0), (0.2, -6.0))
K.reader_cams()
K.cam("cave", (-4.5, -3.8, 2.4), (2.5, 2.5, 1.0), lens=16)
K.cam("door_stone", (0.8, 0.5, 1.6), (0.0, -AY, 2.2), lens=24)
K.finish()
