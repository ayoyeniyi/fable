"""
Fable: the gate room of the Emerald City (The Wonderful Wizard of Oz, chapter 10, "The Guardian of the Gate").

"In front of them, and at the end of the road of yellow brick, was a big gate, all studded with emeralds ... There was
a bell beside the gate ..." "... they found themselves in a high arched room, the walls of which glistened with
countless emeralds." "Then he opened a big box ... it was filled with spectacles of every size and shape. All of them
had green glasses in them." "... two golden bands fastened to them that passed around the back of the head, where they
were locked together by a little key ..." "... the Guardian of the Gates ... took a big golden key from a peg on the
wall ..."

The reader stands just inside the great gate (behind them, its emerald-studded leaves and the bell pull beside it),
in a high arched room of green marble whose walls glisten with countless set emeralds, gold fillets on the mouldings,
afternoon light falling green from high lunette windows. Ahead, the Guardian's bench and his large green box, its lid
open on rows of green spectacles with golden bands; on the wall the big golden key hangs from its peg; beyond, the
inner portal to the city, its doors shut (no streets in view). No Guardian, no Oz, no throne room.

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py.

Node names the runtime relies on:
  anchor.reader.entrance (feet just inside the gate, facing +Y: the box and the inner portal), anchor.reader.look,
  anchor.scene.centre (the box of spectacles), anchor.gate.key
  light.lunette.* (AREA, afternoon daylight through the high windows), light.sky (SUN, fill, no shadow)

Run headless:
  blender -b -P blender/build_emerald_city_gate.py -- --render --quick --cpu --res 900 --cams reader
  blender -b -P blender/build_emerald_city_gate.py -- --export --tex 2048
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

ARGS = S.setup("emerald-city-gate", 1900, "EmeraldGate", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
W2, Y0, Y1, WALL_H, VAULT = 4.5, -1.6, 9.4, 5.2, 4.5         # half-width, ends, wall height, vault rise

def jewelled_mat(name, base, dark, light, cell=7.0, gem=(0.05, 0.55, 0.22), gem_k=0.35):
    """green marble set with countless small emeralds: veined marble, and in a lattice of cells (voronoi) little cut
    stones: a deep green body, a bright facet highlight (emission-free: the gloss does it), a gold collet round each."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    w = noise_(nt, co, 1.6, 8, 0.6, distortion=3.0, loc=(-1700, 400))
    vein = math_(nt, 'MULTIPLY', maprange(nt, w.outputs["Fac"], 0.47, 0.5, 0, 1, (-1500, 450)), maprange(nt, w.outputs["Fac"], 0.5, 0.53, 1, 0, (-1500, 350)), (-1350, 400))
    marble = mix_rgb(nt, 'MIX', maprange(nt, noise_(nt, co, 0.8, 4, 0.6, loc=(-1700, 200)).outputs["Fac"], 0.3, 0.7, 0, 1, (-1500, 200)), c4(K.srgb(base)), c4(K.srgb(light)), (-1300, 200))
    marble = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', vein, 0.6, (-1200, 400)), marble, c4(K.srgb(dark)), (-1100, 250))
    v = voronoi_(nt, co, cell, 'F1', (-1700, -200))
    vs = node(nt, "ShaderNodeSeparateColor", (-1500, -200)); nt.links.new(v.outputs["Color"], vs.inputs["Color"])
    stone = maprange(nt, v.outputs["Distance"], 0.20, 0.16, 0, 1, (-1400, -300))
    collet = math_(nt, 'MULTIPLY', maprange(nt, v.outputs["Distance"], 0.26, 0.22, 0, 1, (-1400, -400)), math_(nt, 'SUBTRACT', 1.0, stone, (-1400, -500)), (-1250, -450))
    present = maprange(nt, vs.outputs[0], 1.0 - gem_k, 1.0 - gem_k + 0.02, 0, 1, (-1400, -600))
    stone = math_(nt, 'MULTIPLY', stone, present, (-1150, -300)); collet = math_(nt, 'MULTIPLY', collet, present, (-1150, -450))
    gemc = mix_rgb(nt, 'MIX', vs.outputs[1], c4(K.srgb((0.02, 0.30, 0.12))), c4(K.srgb(gem)), (-1100, -200))
    col = mix_rgb(nt, 'MIX', collet, marble, c4(K.srgb((0.85, 0.66, 0.28))), (-900, 200))
    col = mix_rgb(nt, 'MIX', stone, col, gemc, (-700, 200))
    col = K.ao_mul(nt, col, 0.2, 0.3, (-500, -900))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, stone, mix_f(nt, collet, 0.25, 0.3, (-700, -600)), 0.05, (-500, -600)), b.inputs["Roughness"])
    nt.links.new(mix_f(nt, collet, 0.0, 1.0, (-700, -750)), b.inputs["Metallic"])
    hgt = math_(nt, 'ADD', math_(nt, 'MULTIPLY', stone, maprange(nt, v.outputs["Distance"], 0.0, 0.2, 1.0, 0.3, (-900, -1000)), (-750, -1000)), math_(nt, 'MULTIPLY', collet, 0.5, (-750, -1100)), (-600, -1050))
    bump_from(nt, b, hgt, 0.6, 0.01)
    return m

print("materials ...", flush=True)
M_WALL = jewelled_mat("M_JewelledWall", (0.40, 0.62, 0.48), (0.16, 0.32, 0.22), (0.54, 0.74, 0.60), cell=4.5, gem_k=0.7)
M_VAULT = jewelled_mat("M_JewelledVault", (0.44, 0.66, 0.52), (0.18, 0.36, 0.24), (0.58, 0.78, 0.64), cell=3.5, gem_k=0.55)
M_FLOOR = jewelled_mat("M_FloorMarble", (0.34, 0.54, 0.40), (0.12, 0.24, 0.16), (0.48, 0.66, 0.52), cell=1.6, gem=(0.06, 0.45, 0.20), gem_k=0.12)
M_MARBLE = PI.marble("M_GreenMarble", base=(0.32, 0.52, 0.40), vein=(0.70, 0.82, 0.74))
M_GOLD = PI.gilt("M_Gold")
M_GEM = plain("M_Emerald", (0.02, 0.40, 0.14), rough=0.04)
M_WOOD = K.noisy("M_GreenWood", [K.srgb((0.12, 0.34, 0.18)), K.srgb((0.16, 0.40, 0.22)), K.srgb((0.10, 0.28, 0.15))], scale=6, rough=0.4, bump=0.05, stretch=(1, 1, 8))
M_BOXIN = K.noisy("M_BoxLining", [K.srgb((0.10, 0.30, 0.14)), K.srgb((0.14, 0.36, 0.18))], scale=80, rough=0.9, bump=0.2)
M_LENS = plain("M_GreenLens", (0.08, 0.50, 0.18), rough=0.05)
M_GLASS = plain("M_LunetteGlass", (0.70, 0.90, 0.72), rough=0.2, emission=(0.75, 0.95, 0.78), strength=2.5)
M_IRON = plain("M_Iron", (0.05, 0.06, 0.05), rough=0.5, metallic=0.8)
M_ROPE = K.noisy("M_BellRope", [K.srgb((0.10, 0.36, 0.16)), K.srgb((0.14, 0.42, 0.20))], scale=120, rough=0.9, bump=0.3, stretch=(1, 1, 8))

# ----------------------------------------------------------------------------- the room: walls, barrel vault, floor
print("room ...", flush=True)
box("Floor", (W2 * 2 + 0.6, Y1 - Y0 + 0.6, 0.1), (0, (Y0 + Y1) / 2, -0.05), M_FLOOR)
for sd in (-1, 1):
    box(f"SideWall{sd}", (0.5, Y1 - Y0 + 1.0, WALL_H), (sd * (W2 + 0.25), (Y0 + Y1) / 2, WALL_H / 2), M_WALL)
def vault():
    verts = []; faces = []; NU, NV = 28, 24
    for j in range(NV + 1):
        y = Y0 - 0.5 + (Y1 - Y0 + 1.0) * j / NV
        for i in range(NU + 1):
            a = math.pi * i / NU
            verts.append((math.cos(a) * W2, y, WALL_H + math.sin(a) * VAULT))
    for j in range(NV):
        for i in range(NU):
            q = j * (NU + 1) + i; faces.append((q, q + 1, q + NU + 2, q + NU + 1))
    o = mesh_from("Vault", verts, faces, M_VAULT, smooth=True)
    orient(o, lambda c: (-c.x, 0, -(c.z - WALL_H)))
    return o
vault()
# end walls (gate end and portal end), filling the vault's arch above the doorways
def end_wall(name, y, sgn, door_w, door_h):
    verts = []; faces = []
    N = 28
    outline = [(math.cos(math.pi * i / N) * W2, WALL_H + math.sin(math.pi * i / N) * VAULT) for i in range(N + 1)]
    pts = [(W2, 0.0)] + outline + [(-W2, 0.0)]
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, z)) for x, z in pts]
    f = bm.faces.new(vs)
    # cut the doorway with a boolean afterwards
    bmesh.ops.recalc_face_normals(bm, faces=[f])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(M_WALL); link(o)
    sol = o.modifiers.new("Solid", 'SOLIDIFY'); sol.thickness = 0.5; sol.offset = sgn
    bpy.context.view_layer.objects.active = o; o.select_set(True); bpy.ops.object.modifier_apply(modifier="Solid"); o.select_set(False)
    cut = box(f"{name}Cut", (door_w, 2.0, door_h), (0, y, door_h / 2 - 0.05), M_WALL)
    # a round-headed opening: add a half cylinder on top of the cutter
    cc = cyl(f"{name}CutTop", door_w / 2, 2.0, (0, y, door_h - 0.05), M_WALL, verts=24); cc.rotation_euler = (math.pi / 2, 0, 0)
    for c in (cut, cc):
        bo = o.modifiers.new("Door", 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.object = c; bo.solver = 'EXACT'
        bpy.context.view_layer.update()
        bpy.context.view_layer.objects.active = o; o.select_set(True); bpy.ops.object.modifier_apply(modifier="Door"); o.select_set(False)
        bpy.data.objects.remove(c, do_unlink=True)
    orient(o, lambda p: (0, -sgn, 0))
    return o
GATE_W, GATE_H = 3.0, 3.6
end_wall("GateWall", Y0, -1, GATE_W, GATE_H)
end_wall("PortalWall", Y1, 1, 2.4, 3.2)
# gold fillets: a cornice at the vault's springing, pilasters, a dado plinth
for sd in (-1, 1):
    box(f"Cornice{sd}", (0.3, Y1 - Y0, 0.22), (sd * (W2 - 0.1), (Y0 + Y1) / 2, WALL_H), M_MARBLE, bevel=0.03)
    box(f"CorniceGold{sd}", (0.05, Y1 - Y0, 0.05), (sd * (W2 - 0.26), (Y0 + Y1) / 2, WALL_H - 0.08), M_GOLD)
    box(f"Plinth{sd}", (0.12, Y1 - Y0, 0.6), (sd * (W2 - 0.04), (Y0 + Y1) / 2, 0.3), M_MARBLE)
    box(f"PlinthGold{sd}", (0.03, Y1 - Y0, 0.04), (sd * (W2 - 0.1), (Y0 + Y1) / 2, 0.62), M_GOLD)
    for k in range(5):
        y = Y0 + 0.9 + k * 2.2
        box(f"Pilaster{sd}{k}", (0.18, 0.6, WALL_H - 0.6), (sd * (W2 - 0.08), y, 0.6 + (WALL_H - 0.6) / 2), M_MARBLE, bevel=0.02)
        box(f"PilasterCap{sd}{k}", (0.26, 0.74, 0.16), (sd * (W2 - 0.1), y, WALL_H - 0.12), M_GOLD, bevel=0.02)
        # ribs over the vault from each pilaster
        pts = [Vector((math.cos(math.pi * i / 20) * (W2 - 0.04), y, WALL_H + math.sin(math.pi * i / 20) * (VAULT - 0.04))) for i in range(21)] if sd > 0 else None
        if pts: tube(f"Rib{k}", pts, [0.1] * len(pts), M_MARBLE, sides=6)
# real cut emeralds set round the doorways and down the pilasters (the near ones catch the light)
R = random.Random(4)
GEMS = []
def gem(p, r, nrm):
    o = sphere("Gem", r, tuple(p), M_GEM, seg=6, scale=(1.0, 1.0, 1.0))
    o.scale = (1, 1, 1); GEMS.append(o)
    return o
for k in range(18):
    a = math.pi * k / 17
    for (y, s) in ((Y0 + 0.02, 1), (Y1 - 0.02, -1)):
        r = (GATE_W if s > 0 else 2.4) / 2 + 0.22
        h = GATE_H if s > 0 else 3.2
        p = Vector((math.cos(a) * r, y + 0.05 * s, h - 0.05 + math.sin(a) * r))
        sphere("ArchGem", 0.06, tuple(p), M_GEM, seg=6, scale=(1, 0.5, 1))
for sd in (-1, 1):
    for k in range(5):
        y = Y0 + 0.9 + k * 2.2
        for z in np.arange(1.0, WALL_H - 0.4, 0.55):
            sphere("PilasterGem", 0.045, (sd * (W2 - 0.18), y, z), M_GEM, seg=6, scale=(0.5, 1, 1))
# lunette windows high in the end walls' arches (light), and round windows high in the side walls of the vault
for (y, sgn) in ((Y0 + 0.01, 1), (Y1 - 0.01, -1)):
    lw = lathe("Lunette", [(0.0, 0.0), (1.2, 0.0)], (0, y, WALL_H + 1.2), M_GLASS, steps=24)
    lw.rotation_euler = (math.pi / 2 * sgn, 0, 0)
    tor = bpy.ops.mesh.primitive_torus_add(major_radius=1.25, minor_radius=0.07, location=(0, y + 0.03 * sgn, WALL_H + 1.2), rotation=(math.pi / 2, 0, 0))
    to = bpy.context.active_object; to.name = "LunetteRing"; to.data.materials.append(M_GOLD)
    for c in to.users_collection: c.objects.unlink(to)
    link(to)

# ----------------------------------------------------------------------------- the great gate behind (shut), studded with emeralds; the bell
GY = Y0 - 0.3
for sd in (-1, 1):
    leaf = box(f"GateLeaf{sd}", (GATE_W / 2, 0.14, GATE_H + GATE_W / 2 - 0.2), (sd * GATE_W / 4, GY, (GATE_H + GATE_W / 2 - 0.2) / 2), M_WOOD)
    for iz in range(9):
        for ix in range(3):
            z = 0.35 + iz * 0.42; x = sd * (0.25 + ix * 0.42)
            if z > GATE_H + 0.9 - abs(x) * 0.7: continue
            sphere("GateStud", 0.07, (x, GY + 0.09, z), M_GEM, seg=6, scale=(1, 0.5, 1))
            o = cyl("StudCollet", 0.09, 0.02, (x, GY + 0.075, z), M_GOLD, verts=10); o.rotation_euler = (math.pi / 2, 0, 0)
    tube(f"GateHandle{sd}", [Vector((sd * 0.12, GY + 0.1, 1.2)), Vector((sd * 0.12, GY + 0.22, 1.25)), Vector((sd * 0.12, GY + 0.1, 1.3))], [0.02] * 3, M_GOLD, sides=6)
# the bell pull beside the gate (inside: a green rope to a golden bell on a bracket)
BELL = Vector((GATE_W / 2 + 0.7, Y0 + 0.35, 2.9))
tube("BellBracket", [Vector((BELL.x, Y0 + 0.02, BELL.z + 0.5)), BELL + Vector((0, 0, 0.45))], [0.02, 0.02], M_GOLD, sides=6)
lathe("Bell", [(0.0, 0.32), (0.08, 0.3), (0.12, 0.2), (0.15, 0.05), (0.2, 0.0), (0.18, -0.01), (0.0, 0.02)], tuple(BELL), M_GOLD, steps=20)
tube("BellRope", [BELL + Vector((0, 0, 0.02)), BELL + Vector((0.02, 0, -1.6))], [0.012, 0.012], M_ROPE, sides=6)
sphere("BellTassel", 0.05, tuple(BELL + Vector((0.02, 0, -1.65))), M_ROPE, seg=8, scale=(1, 1, 1.6))

# ----------------------------------------------------------------------------- the inner portal ahead (shut)
for sd in (-1, 1):
    box(f"PortalLeaf{sd}", (1.2, 0.12, 4.2), (sd * 0.6, Y1 + 0.3, 2.1), M_WOOD)
    for k in range(4):
        box(f"PortalPanel{sd}{k}", (0.8, 0.03, 0.6), (sd * 0.6, Y1 + 0.22, 0.6 + k * 0.75), M_GOLD, bevel=0.01)
    sphere(f"PortalKnob{sd}", 0.06, (sd * 0.12, Y1 + 0.18, 1.2), M_GOLD, seg=10)

# ----------------------------------------------------------------------------- the Guardian's bench, the big green box of spectacles, the key on its peg
BX = Vector((1.4, 4.6, 0))
box("BenchTop", (2.2, 0.8, 0.06), (BX.x, BX.y, 0.74), M_WOOD, bevel=0.01)
for (dx, dy) in ((-1.0, -0.33), (1.0, -0.33), (-1.0, 0.33), (1.0, 0.33)):
    box("BenchLeg", (0.08, 0.08, 0.72), (BX.x + dx, BX.y + dy, 0.36), M_WOOD)
BOXZ = 0.77
box("SpecBoxBottom", (1.2, 0.6, 0.04), (BX.x, BX.y, BOXZ + 0.02), M_WOOD)
for (dx, dy, sx, sy) in ((0, -0.3, 1.2, 0.04), (0, 0.3, 1.2, 0.04), (-0.6, 0, 0.04, 0.6), (0.6, 0, 0.04, 0.6)):
    box("SpecBoxSide", (sx, sy, 0.24), (BX.x + dx, BX.y + dy, BOXZ + 0.12), M_WOOD)
box("SpecBoxLining", (1.12, 0.52, 0.02), (BX.x, BX.y, BOXZ + 0.05), M_BOXIN)
lid = box("SpecBoxLid", (1.22, 0.04, 0.62), (BX.x, BX.y + 0.32, BOXZ + 0.55), M_WOOD)
lid.rotation_euler = (math.radians(-12), 0, 0)
for (dx, dz) in ((-0.5, 0.25), (0.5, 0.25), (-0.5, -0.25), (0.5, -0.25)):
    sphere("LidStud", 0.025, (BX.x + dx, BX.y + 0.3, BOXZ + 0.55 + dz), M_GEM, seg=6)
# rows of spectacles: two round green lenses in gold rims with a bridge, golden bands folded behind
for row in range(4):
    for k in range(6):
        c = Vector((BX.x - 0.45 + k * 0.18 + R.gauss(0, 0.01), BX.y - 0.18 + row * 0.12, BOXZ + 0.075 + 0.01 * (row % 2)))
        s = R.uniform(0.85, 1.25)
        for sd in (-1, 1):
            lc = c + Vector((sd * 0.035 * s, 0, 0))
            o = cyl("Lens", 0.028 * s, 0.006, tuple(lc), M_LENS, verts=12); o.rotation_euler = (math.radians(70), 0, 0)
            bpy.ops.mesh.primitive_torus_add(major_radius=0.03 * s, minor_radius=0.003, location=tuple(lc), rotation=(math.radians(70), 0, 0), major_segments=12, minor_segments=4)
            t = bpy.context.active_object; t.name = "Rim"; t.data.materials.append(M_GOLD)
            for cc in t.users_collection: cc.objects.unlink(t)
            link(t)
        tube("Band", [c + Vector((-0.065 * s, 0.0, 0.0)), c + Vector((-0.06 * s, 0.05, -0.005)), c + Vector((0.06 * s, 0.05, -0.005)), c + Vector((0.065 * s, 0.0, 0.0))],
             [0.003] * 4, M_GOLD, sides=4, caps=False)
# the big golden key on its peg on the right wall
KEY = Vector((W2 - 0.02, 4.0, 1.75))
tube("KeyPeg", [KEY, KEY + Vector((-0.12, 0, 0.02))], [0.012, 0.012], M_GOLD, sides=6)
bpy.ops.mesh.primitive_torus_add(major_radius=0.05, minor_radius=0.012, location=tuple(KEY + Vector((-0.08, 0, -0.04))), rotation=(0, math.pi / 2, 0), major_segments=14, minor_segments=6)
t = bpy.context.active_object; t.name = "KeyBow"; t.data.materials.append(M_GOLD)
for cc in t.users_collection: cc.objects.unlink(t)
link(t)
tube("KeyShank", [KEY + Vector((-0.08, 0, -0.09)), KEY + Vector((-0.08, 0, -0.32))], [0.011, 0.011], M_GOLD, sides=6)
box("KeyBit", (0.01, 0.05, 0.05), tuple(KEY + Vector((-0.08, 0.025, -0.3))), M_GOLD)
# a green carpet runner from the gate to the portal
box("Runner", (1.6, Y1 - Y0 - 0.4, 0.012), (0.0, (Y0 + Y1) / 2, 0.006), plain("M_Runner", K.srgb((0.08, 0.30, 0.14)), rough=0.95))

# ----------------------------------------------------------------------------- light: afternoon daylight green through the lunettes; a fill
K.apply_transforms()
for (y, sgn, pw) in ((Y0 - 0.6, 1, 900.0), (Y1 + 0.6, -1, 1100.0)):
    L = light_obj(f"light.lunette.{'gate' if sgn > 0 else 'portal'}", 'AREA', pw, (0.82, 1.0, 0.82), (0, y, WALL_H + 1.2), direction=(0, sgn, -0.55))
    L.data.shape = 'DISK'; L.data.size = 2.4
L = light_obj("light.vault", 'AREA', 700.0, (0.85, 1.0, 0.85), (0, (Y0 + Y1) / 2, WALL_H + VAULT - 0.3), direction=(0, 0, -1))
L.data.shape = 'RECTANGLE'; L.data.size = 2.0; L.data.size_y = 6.0
skl = light_obj("light.sky", 'SUN', 0.35, (0.80, 0.95, 0.82), (0, 0, 20), direction=(0.2, 0.3, -1.0), angle=math.radians(80))
skl.data.use_shadow = False
world = bpy.data.worlds.new("Green"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.20, 0.30, 0.22, 1); bg.inputs["Strength"].default_value = 0.4

S.reader_anchors(0.0)
anchor("scene.centre", (BX.x, BX.y, BOXZ + 0.1))
anchor("gate.key", tuple(KEY))
S.check_clear(look_yaw=0.0)
E = Vector((0, 0, EYE))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EYE + 0.3), 17),
    ("Cam_Box", (BX.x - 0.9, BX.y - 1.1, 1.6), (BX.x, BX.y, BOXZ + 0.1), 28),
    ("Cam_Up", tuple(E), (0, 5, WALL_H + VAULT), 17),
], pitch=4.0)
S.finish("emerald-city-gate", "emerald_city_gate", cams, keep_names={},
         size_for={"M_JewelledWall": (2048, 256, 1024), "M_JewelledVault": (2048, 128, 1024), "M_FloorMarble": (2048, 256, 1024), "M_GreenMarble": (1024, 64, 256),
                   "M_Gold": (256, 64, 128), "M_Emerald": (32,), "M_GreenWood": (512, 64, 256), "M_BoxLining": (128, 32, 64), "M_GreenLens": (32,),
                   "M_LunetteGlass": (32,), "M_Iron": (32,), "M_BellRope": (64, 32, 32), "M_Runner": (64,)},
         page=page, default_exposure=0.3, unlit_emit={"M_LunetteGlass"})
