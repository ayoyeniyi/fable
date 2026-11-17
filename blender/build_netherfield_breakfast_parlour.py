"""
Fable step-in room: the breakfast parlour at Netherfield Park (Pride and Prejudice, chapter 9).

"Elizabeth passed the chief of the night in her sister's room, and in the morning ... Mrs. Bennet, accompanied by her
two youngest girls, reached Netherfield soon after the family breakfast" ... "they all attended her into the breakfast
parlour. Bingley met them with hopes that Mrs. Bennet had not found Miss Bennet worse than she expected" ... "'You have a
sweet room here, Mr. Bingley, and a charming prospect over that gravel walk.'"

The morning room of a fashionable rented country house, c.1811, about 7 x 5 m under a 3.5 m ceiling: pale primrose
walls over a white dado, a deep white cornice, polished oak boards with a carpet; three tall sash windows on the south
wall look over the raked gravel walk, the lawn, the shrubbery and the autumn trees of the park; a white statuary-marble
chimney-piece on the east wall with a small fire; the round mahogany breakfast table just cleared (a cloth folded back,
a silver tea urn and a few cups waiting on the sideboard), sabre-legged chairs set back, a striped sofa where the
visitors sit, a mahogany sideboard on the north wall, a six-panel door on the west wall. No loo table, no evening candles,
no ball preparations. No people.

Light: clear soft morning daylight from the south windows (low autumn sun from the south-east), the small fire a warm
accent. Reader: by the middle window, facing into the room (north).

  blender -b -P blender/build_netherfield_breakfast_parlour.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_netherfield_breakfast_parlour.py -- --render --samples 32 --res 1280 --cams reader,left,right,behind,table
  blender -b -P blender/build_netherfield_breakfast_parlour.py -- --export
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b5 as S
import pride_kit as K
import pride_interior as I
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, anchor, sound, light_obj, camera)

SID = "netherfield-breakfast-parlour"
ARGS = S.setup(SID, seed=1812)
scene = K.scene
scene.cycles.max_bounces = 8; scene.cycles.diffuse_bounces = 5
rng = random.Random(1812)

R = I.Room(-3.5, 3.5, -2.5, 2.5, 3.5, t=0.45)

# ----------------------------------------------------------------------------- materials
M_WALL = I.paint_mat("M_WallPaint", K.srgb((0.86, 0.82, 0.64)), rough=0.85, dirt=0.05)
M_DADO = I.paint_mat("M_DadoPaint", K.srgb((0.88, 0.87, 0.82)), rough=0.6, dirt=0.06)
M_JOIN = I.joinery_mat("M_Joinery", K.srgb((0.84, 0.82, 0.74)))
M_CEIL = I.paint_mat("M_Ceiling", K.srgb((0.86, 0.85, 0.80)), rough=0.9, dirt=0.0)
M_FLOOR = I.boards_mat("M_FloorBoards", light=(0.33, 0.22, 0.12), dark=(0.15, 0.09, 0.045), width=0.21)
M_CARPET = I.carpet_mat("M_Carpet", 0.0, 0.3, 2.6, 1.9, field=(0.07, 0.10, 0.12), ground2=(0.20, 0.06, 0.04), border=(0.05, 0.035, 0.03), buff=(0.40, 0.33, 0.20))
M_MAHOG = wood("M_Mahogany", base=(0.11, 0.035, 0.016), dark=(0.035, 0.011, 0.006), light=(0.20, 0.075, 0.035), scale=1.4, rough=(0.35, 0.6),
               grain_dir=(1, 1, 10), coat=0.15, ao=0.25, bump=0.15)
M_BRASS = plain("M_Brass", (0.70, 0.52, 0.27), rough=0.32, metallic=1.0)
M_IRON = noisy("M_Iron", [(0.025, 0.025, 0.027), (0.05, 0.05, 0.05), (0.035, 0.032, 0.03)], scale=30, rough=(0.45, 0.7), metallic=0.6)
M_SOOT = plain("M_Soot", (0.012, 0.011, 0.01), rough=0.95)
M_WAX = plain("M_Wax", K.srgb((0.93, 0.91, 0.85)), rough=0.45)
M_PANE = new_mat("M_Pane")[0]
M_SOFA = I.silk("M_SofaStripe", K.srgb((0.36, 0.48, 0.56)), K.srgb((0.82, 0.80, 0.70)), stripes=1.0, stripe_w=0.035, axis='X', sheen=0.5, rough=0.7)
M_CHINTZ = None
M_SEAT = I.silk("M_ChairSeat", K.srgb((0.34, 0.44, 0.52)), K.srgb((0.42, 0.52, 0.60)), damask=0.5, sheen=0.4, rough=0.75)
M_LAND = I.landscape_mat("M_Landscape", 3)
M_CLOCKFACE = plain("M_ClockFace", K.srgb((0.82, 0.78, 0.68)), rough=0.4)
M_PAGES = noisy("M_BookPages", [K.srgb((0.80, 0.76, 0.64)), K.srgb((0.72, 0.68, 0.56))], scale=200, rough=0.85, stretch=(1, 1, 30), bump=0.0)
M_CALF = noisy("M_Calf", [K.srgb((0.36, 0.20, 0.11)), K.srgb((0.46, 0.27, 0.15)), K.srgb((0.30, 0.16, 0.09))], scale=14, rough=(0.4, 0.65), bump=0.3, bump_dist=0.001)
M_STRAWX = noisy("M_Straw", [K.srgb((0.78, 0.66, 0.42)), K.srgb((0.66, 0.53, 0.30)), K.srgb((0.84, 0.74, 0.50))], scale=60, rough=0.75,
                stretch=(1, 1, 1), bump=0.5, bump_dist=0.0015)
M_RIBBONX = plain("M_Ribbon", K.srgb((0.30, 0.44, 0.58)), rough=0.35, sheen=0.6)
M_RIBBONXX2 = plain("M_RibbonRose", K.srgb((0.72, 0.42, 0.42)), rough=0.35, sheen=0.6)
M_STEEL = plain("M_Steel", (0.55, 0.55, 0.56), rough=0.25, metallic=1.0)
M_LINEN = noisy("M_Linen", [K.srgb((0.88, 0.86, 0.80)), K.srgb((0.80, 0.78, 0.72))], scale=90, rough=0.85, bump=0.2, bump_dist=0.0008)


def chintz(name="M_Chintz"):
    """Block-printed cotton chintz for the curtains: a cream ground with trailing sprigs in faded rose and green."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 7.0, 'F1', (-1200, 200))
    n = noise_(nt, co, 14.0, 4, 0.6, distortion=1.2, loc=(-1200, -100))
    bloom = maprange(nt, v.outputs["Distance"], 0.08, 0.16, 1, 0, (-950, 200))
    leaf = maprange(nt, n.outputs["Fac"], 0.56, 0.6, 0, 1, (-950, -100))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', leaf, 0.7, (-800, -100)), c4(K.srgb((0.86, 0.82, 0.70))), c4(K.srgb((0.46, 0.55, 0.40))), (-700, 0))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', bloom, 0.85, (-800, 200)), col, c4(K.srgb((0.74, 0.44, 0.42))), (-550, 0))
    col = K.ao_mul(nt, col, 0.1, 0.4, (-400, -400))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.6; b.inputs["Sheen Weight"].default_value = 0.4
    return m
M_CHINTZ = chintz()


def embers_mat(name="M_Embers"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 28.0, 'DISTANCE_TO_EDGE', (-900, 0))
    glow = maprange(nt, v.outputs["Distance"], 0.0, 0.08, 1, 0, (-700, 0))
    n = noise_(nt, co, 9.0, 4, 0.6, loc=(-900, -250))
    glow = math_(nt, 'MULTIPLY', glow, maprange(nt, n.outputs["Fac"], 0.35, 0.65, 0.2, 1.0, (-700, -250)), (-500, -100))
    col = mix_rgb(nt, 'MIX', glow, (0.02, 0.018, 0.016, 1), (0.9, 0.28, 0.05, 1), (-300, 0))
    nt.links.new(col, b.inputs["Base Color"])
    ec = mix_rgb(nt, 'MULTIPLY', 1.0, (1.0, 0.33, 0.06, 1), glow, (-300, -300))
    nt.links.new(ec, b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 4.0
    b.inputs["Roughness"].default_value = 0.9
    return m
M_EMBERS = embers_mat()

# window glass: clear for the render and the bake (lets the sun in); not exported
nt = M_PANE.node_tree
for n_ in list(nt.nodes): nt.nodes.remove(n_)
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (0.96, 0.97, 0.96, 1)
nt.links.new(tr.outputs["BSDF"], o_.inputs["Surface"])


# ----------------------------------------------------------------------------- the view through the windows (painted backdrop, baked as emission)
def view_mat(name="M_WindowView"):
    """Painted from the windows' point of view on a curved backdrop outside the south wall: a pale autumn morning sky,
    the gravel sweep, the lawn, a shrubbery and the hedge of the lane, elms and a beech in October colour beyond, the
    roofs of the village to the right. z: height above the outside ground; x: across."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1900, 0))
    z = math_(nt, 'ADD', s.outputs["Z"], 0.7, (-1750, 100)); xx = s.outputs["X"]
    sky = mix_rgb(nt, 'MIX', maprange(nt, z, 2.0, 9.0, 0, 1, (-1500, 500)), (0.86, 0.85, 0.80, 1), (0.52, 0.64, 0.80, 1), (-1300, 500))
    cl = noise_(nt, co, 0.28, 6, 0.62, 0.4, (-1500, 750))
    sky = mix_rgb(nt, 'MIX', maprange(nt, cl.outputs["Fac"], 0.5, 0.68, 0, 0.6, (-1300, 750)), sky, (0.95, 0.93, 0.88, 1), (-1100, 500))
    # trees: a billowy skyline, crowns of mixed colour with dark gaps, trunks below
    tn = noise_(nt, co, 0.45, 6, 0.7, 0.5, (-1500, 200))
    top = math_(nt, 'ADD', 3.2, math_(nt, 'MULTIPLY', tn.outputs["Fac"], 4.8, (-1350, 200)), (-1250, 200))
    is_tree = maprange(nt, math_(nt, 'SUBTRACT', top, z, (-1150, 200)), 0.0, 0.12, 0, 1, (-1050, 200))
    leaf = noise_(nt, co, 5.0, 6, 0.65, 0.3, (-1350, -50))
    hue = noise_(nt, co, 0.7, 2, 0.5, loc=(-1350, -250))
    tc = mix_rgb(nt, 'MIX', maprange(nt, hue.outputs["Fac"], 0.35, 0.65, 0, 1, (-1150, -250)), (0.30, 0.30, 0.12, 1), (0.62, 0.38, 0.12, 1), (-1000, -200))
    tc = mix_rgb(nt, 'MIX', maprange(nt, leaf.outputs["Fac"], 0.42, 0.62, 0, 1, (-1150, -50)), (0.07, 0.07, 0.04, 1), tc, (-900, -100))
    col = mix_rgb(nt, 'MIX', is_tree, sky, tc, (-800, 300))
    # village roofs (right): old tile, a chimney
    rf = math_(nt, 'MULTIPLY', maprange(nt, xx, 7.5, 7.6, 0, 1, (-1350, -500)), maprange(nt, xx, 9.0, 9.1, 1, 0, (-1350, -600)), (-1200, -550))
    rh = math_(nt, 'SUBTRACT', 3.4, math_(nt, 'MULTIPLY', math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', xx, 5.0, (-1350, -750)), None, (-1250, -750)), 0.55, (-1150, -750)), (-1050, -750))
    inroof = math_(nt, 'MULTIPLY', rf, maprange(nt, math_(nt, 'SUBTRACT', rh, z, (-950, -750)), 0.0, 0.04, 0, 1, (-850, -750)), (-750, -650))
    inwall = math_(nt, 'MULTIPLY', rf, maprange(nt, z, 2.7, 2.75, 1, 0, (-950, -900)), (-750, -850))
    col = mix_rgb(nt, 'MIX', inroof, col, (0.30, 0.15, 0.10, 1), (-650, 300))
    col = mix_rgb(nt, 'MIX', inwall, col, (0.62, 0.55, 0.45, 1), (-550, 300))
    # the hedge of the lane (dark green, uneven top) and the lane itself (pale, a band)
    hn = noise_(nt, co, 1.6, 4, 0.6, loc=(-1350, -1100))
    htop = math_(nt, 'ADD', 1.7, math_(nt, 'MULTIPLY', hn.outputs["Fac"], 0.7, (-1250, -1100)), (-1150, -1100))
    hedge = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'SUBTRACT', htop, z, (-1050, -1100)), 0, 0.05, 0, 1, (-950, -1100)), maprange(nt, z, 1.0, 1.05, 0, 1, (-950, -1200)), (-850, -1150))
    hc = mix_rgb(nt, 'MIX', maprange(nt, leaf.outputs["Fac"], 0.4, 0.6, 0, 1, (-950, -1300)), (0.06, 0.09, 0.04, 1), (0.20, 0.24, 0.10, 1), (-800, -1300))
    col = mix_rgb(nt, 'MIX', hedge, col, hc, (-450, 300))
    lane = math_(nt, 'MULTIPLY', maprange(nt, z, 1.0, 1.04, 1, 0, (-1350, -1500)), maprange(nt, z, 0.78, 0.8, 0, 1, (-1350, -1600)), (-1200, -1550))
    col = mix_rgb(nt, 'MIX', lane, col, (0.55, 0.50, 0.40, 1), (-350, 300))
    # lawn, with a shrubbery of laurel and a few yellowing lilacs
    lawn = maprange(nt, z, 0.78, 0.8, 1, 0, (-1350, -1800))
    gn = noise_(nt, co, 3.0, 4, 0.5, loc=(-1350, -1950))
    lc = mix_rgb(nt, 'MIX', maprange(nt, gn.outputs["Fac"], 0.35, 0.65, 0, 1, (-1150, -1950)), (0.20, 0.27, 0.10, 1), (0.30, 0.36, 0.14, 1), (-1000, -1950))
    col = mix_rgb(nt, 'MIX', lawn, col, lc, (-250, 300))
    sb = noise_(nt, co, 0.9, 5, 0.65, loc=(-1350, -2150))
    stop = math_(nt, 'MULTIPLY', maprange(nt, sb.outputs["Fac"], 0.45, 0.7, 0, 1.6, (-1150, -2150)), maprange(nt, xx, -3.0, -1.0, 1, 0.2, (-1150, -2300)), (-1000, -2200))
    shrub = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'SUBTRACT', stop, z, (-900, -2200)), 0, 0.04, 0, 1, (-800, -2200)), maprange(nt, z, 0.0, 0.02, 0, 1, (-800, -2300)), (-700, -2250))
    sc = mix_rgb(nt, 'MIX', maprange(nt, leaf.outputs["Fac"], 0.4, 0.62, 0, 1, (-800, -2400)), (0.04, 0.07, 0.03, 1), (0.22, 0.28, 0.10, 1), (-650, -2400))
    col = mix_rgb(nt, 'MIX', shrub, col, sc, (-150, 300))
    # the gravel sweep under the windows
    grav = maprange(nt, z, 0.32, 0.36, 1, 0, (-1350, -2600))
    gr = noise_(nt, co, 40.0, 3, 0.6, loc=(-1350, -2750))
    gc = mix_rgb(nt, 'MIX', maprange(nt, gr.outputs["Fac"], 0.3, 0.7, 0, 1, (-1150, -2750)), (0.48, 0.42, 0.32, 1), (0.66, 0.60, 0.48, 1), (-1000, -2750))
    col = mix_rgb(nt, 'MIX', grav, col, gc, (-50, 300))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0
    return m
M_VIEW = view_mat()


M_MARBLE = I.marble("M_Marble")
M_SILVER = plain("M_Silver", (0.80, 0.80, 0.78), rough=0.2, metallic=1.0)
M_GILT = I.gilt("M_Gilt")
M_DAMASK = noisy("M_TableCloth", [K.srgb((0.92, 0.91, 0.87)), K.srgb((0.86, 0.85, 0.80))], scale=40, rough=0.8, bump=0.1)
# ----------------------------------------------------------------------------- openings, walls, floor, ceiling, mouldings
WIN_X = (-2.3, 0.0, 2.3)
for k, x in enumerate(WIN_X):
    I.sash_window(f"Win{k}", R, 'S', x - R.x0, 1.15, 0.5, 2.5, M_JOIN, M_PANE, M_JOIN, panes=(3, 6), curtain_mat=None)
DOOR_Y = 1.2
M_DOOR = I.mahogany("M_DoorMahogany", rough=(0.3, 0.55), coat=0.2)
I.six_panel_door("Door", R, 'W', R.y1 - DOOR_Y, 1.0, 2.5, M_DOOR, M_JOIN, M_BRASS, open_deg=0, hinge_left=True)
I.build_walls(R, M_WALL)
K.box("Floor", (R.x1 - R.x0 + 0.9, R.y1 - R.y0 + 0.9, 0.04), (0, 0, -0.02), M_FLOOR)
box("Carpet", (5.2, 3.8, 0.012), (0.0, 0.3, 0.006), M_CARPET, bevel=0.004)
box("Ceiling", (R.x1 - R.x0 + 0.9, R.y1 - R.y0 + 0.9, 0.05), (0, 0, R.h + 0.025), M_CEIL)
lathe("CeilingRose", [(0.0, -0.0), (0.42, 0.0), (0.4, -0.02), (0.34, -0.03), (0.3, -0.05), (0.2, -0.055), (0.12, -0.075), (0.05, -0.09), (0.0, -0.09)], (0.0, 0.3, R.h), M_CEIL, steps=32)
I.moulding_runs(R, "Skirting", I.skirting_profile(0.26), 0.0, M_JOIN)
I.moulding_runs(R, "ChairRail", I.rail_profile(), 0.92, M_JOIN, z_band=(0.88, 0.96))
I.dado_panels(R, M_JOIN, rail_z=0.92, skirt=0.26)
I.moulding_runs(R, "Cornice", I.cornice_profile(0.26, 0.3), R.h, M_JOIN, z_band=(R.h - 0.3, R.h))
for w in ('S', 'E', 'N', 'W'):
    o, a, n, L = R.wall_frame(w)
    for k, (u0, u1) in enumerate(I.runs(R, w, 0.26, 0.9)):
        c = o + a * ((u0 + u1) / 2) + n * 0.002 + Vector((0, 0, 0.58))
        box(f"Dado{w}{k}", (abs(a.x) * (u1 - u0) + abs(n.x) * 0.004, abs(a.y) * (u1 - u0) + abs(n.y) * 0.004, 0.64), tuple(c), M_DADO)
# curtains (chintz, open, tied back) on gilt poles under a simple cornice
CURT = []
for k, x in enumerate(WIN_X):
    o, a, n, L = R.wall_frame('S'); base = o + a * (x - R.x0)
    rod_z = 0.5 + 2.5 + 0.25
    cyl(f"Pole{k}", 0.022, 1.15 + 0.8, tuple(base + n * 0.12 + Vector((0, 0, rod_z))), M_GILT, verts=10, rot=(0, math.pi / 2, 0))
    for sx in (-1, 1):
        outer = sx * 0.95; inner = sx * 0.6
        c = I.curtain_panel(f"Curtain{k}{sx}", base, a, n, outer, inner, rod_z - 0.03, -0.01, M_CHINTZ, folds=4, depth=0.05)
        for v in c.data.vertices:
            zz = v.co.z; u = (v.co - base).dot(a)
            t = max(0.0, 1.0 - abs(zz - 1.05) / 1.3)
            v.co += a * ((outer - u) * 0.35 * t)
        CURT.append(c)
for c in CURT:
    K.add_sway(c, lambda p: max(0.0, min(1.0, (3.2 - p.z) / 3.2)) * 0.5)
# the view: the backdrop arc outside the south wall
vv = []; vf = []
NU, NV = 24, 6
for j in range(NV + 1):
    for i in range(NU + 1):
        a_ = math.radians(-72 + 144 * i / NU); r = 9.0
        vv.append((r * math.sin(a_) * 1.4, R.y0 - 0.6 - r * math.cos(a_) * 0.75, -0.7 + 12.0 * j / NV))
for j in range(NV):
    for i in range(NU): vf.append((j * (NU + 1) + i, j * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i))
view = mesh_from("WindowView", vv, vf, M_VIEW)
view.visible_shadow = False; view.visible_diffuse = False; view.visible_glossy = False
box("OutsideGround", (14, 4, 0.05), (0, R.y0 - R.t - 2.0, -0.72), noisy("M_Gravel", [K.srgb((0.62, 0.56, 0.46)), K.srgb((0.72, 0.66, 0.54))], scale=50, rough=0.9))

# ----------------------------------------------------------------------------- the white marble chimney-piece (east wall), register grate, small fire
F = Frame((R.x1, 0.3), math.pi / 2)       # local +Y = -X world (into the room)
def FP(x, y, z): return F.p(x, y, z)
OW, OH = 0.9, 0.9
F.box("HearthStone", (1.75, 0.52, 0.04), (0, 0.26, 0.02), M_MARBLE, bevel=0.004)
for sx in (-1, 1):
    F.box(f"Jamb{sx}", (0.26, 0.16, OH + 0.02), (sx * (OW / 2 + 0.13), 0.08, (OH + 0.02) / 2), M_MARBLE, bevel=0.006)
    for r_ in range(3):
        F.box(f"Reed{sx}{r_}", (0.022, 0.02, OH - 0.1), (sx * (OW / 2 + 0.13) + (r_ - 1) * 0.06, 0.165, OH / 2 + 0.02), M_MARBLE, bevel=0.009)
    F.box(f"CornerBlock{sx}", (0.28, 0.18, 0.27), (sx * (OW / 2 + 0.13), 0.09, OH + 0.135), M_MARBLE, bevel=0.008)
    cyl(f"Roundel{sx}", 0.07, 0.025, FP(sx * (OW / 2 + 0.13), 0.185, OH + 0.135), M_MARBLE, verts=16, rot=(math.pi / 2, 0, F.yaw))
F.box("Frieze", (OW, 0.15, 0.25), (0, 0.075, OH + 0.125), M_MARBLE, bevel=0.004)
F.box("Tablet", (0.36, 0.03, 0.17), (0, 0.16, OH + 0.135), M_MARBLE, bevel=0.006)
F.box("Shelf", (1.82, 0.26, 0.05), (0, 0.12, OH + 0.295), M_MARBLE, bevel=0.012)
F.box("GratePlate", (OW, 0.03, OH), (0, 0.012, OH / 2), M_IRON)
F.box("GrateMouth", (OW * 0.62, 0.03, OH * 0.52), (0, 0.02, OH * 0.40), M_SOOT)
F.box("BasketFloor", (0.56, 0.24, 0.03), (0, 0.13, 0.15), M_IRON)
for k in range(5):
    F.box(f"BasketBar{k}", (0.56, 0.014, 0.014), (0, 0.255, 0.17 + k * 0.045), M_IRON, bevel=0.003)
cr = random.Random(5)
for k in range(18):
    lx = cr.uniform(-0.2, 0.2); ly = cr.uniform(0.06, 0.22); lz = 0.18 + cr.uniform(0, 0.07) * (1 - abs(lx) / 0.25)
    sphere(f"Coal{k}", cr.uniform(0.025, 0.045), FP(lx, ly, lz), M_EMBERS if lz < 0.23 or cr.random() < 0.4 else M_IRON, seg=6,
           scale=(cr.uniform(0.8, 1.3), cr.uniform(0.8, 1.3), cr.uniform(0.6, 0.9)))
FIRE_BASE = Vector(FP(0, 0.14, 0.21))
F.box("FenderFront", (1.5, 0.012, 0.09), (0, 0.5, 0.045 + 0.04), M_BRASS, bevel=0.004)
for sx in (-1, 1): F.box(f"FenderSide{sx}", (0.012, 0.36, 0.09), (sx * 0.75, 0.33, 0.045 + 0.04), M_BRASS, bevel=0.004)
SHELF_Z = OH + 0.32
F.box("MirrorGlass", (1.3, 0.02, 1.15), (0, 0.03, SHELF_Z + 0.75), plain("M_Mirror", (0.62, 0.64, 0.64), rough=0.04, metallic=1.0))
for (fx_, fz, sw, sh) in ((0, SHELF_Z + 0.75 + 0.62, 1.48, 0.09), (0, SHELF_Z + 0.75 - 0.62, 1.48, 0.09), (-0.695, SHELF_Z + 0.75, 0.09, 1.15), (0.695, SHELF_Z + 0.75, 0.09, 1.15)):
    F.box(f"MirrorFrame{fx_}{fz}", (sw, 0.06, sh), (fx_, 0.05, fz), M_GILT, bevel=0.015)
F.box("ClockCase", (0.26, 0.15, 0.32), (0, 0.11, SHELF_Z + 0.16), M_MAHOG, bevel=0.008)
cyl("ClockArch", 0.13, 0.15, FP(0, 0.11, SHELF_Z + 0.32), M_MAHOG, verts=16, rot=(math.pi / 2, 0, F.yaw))
cyl("ClockDial", 0.085, 0.01, FP(0, 0.19, SHELF_Z + 0.2), M_CLOCKFACE, verts=24, rot=(math.pi / 2, 0, F.yaw))
for k, ang in enumerate((math.radians(-60), math.radians(20))):     # twenty to ten in the morning
    ln = 0.055 if k == 0 else 0.07
    F.box(f"ClockHand{k}", (0.005, 0.004, ln), (math.sin(ang) * ln / 2, 0.197, SHELF_Z + 0.2 + math.cos(ang) * ln / 2), M_IRON, ry=-ang)
M_CHINA = plain("M_China", K.srgb((0.90, 0.90, 0.88)), rough=0.12, coat=0.5)
for sx in (-1, 1):
    lathe(f"Vase{sx}", [(0.0, 0.0), (0.05, 0.0), (0.07, 0.08), (0.05, 0.2), (0.07, 0.26), (0.0, 0.26)], FP(sx * 0.6, 0.12, SHELF_Z), M_CHINA, steps=14)
anchor("room.fireplace", FP(0, 0.4, 0))

# ----------------------------------------------------------------------------- the round breakfast table just cleared, chairs set back
def face(pos, target): return math.atan2(-(target[0] - pos[0]), target[1] - pos[1])
TABLE = Vector((-0.3, 0.75, 0))
top = I.pedestal_table("BreakfastTable", (TABLE.x, TABLE.y), M_MAHOG, M_MAHOG, radius=0.66, height=0.73, feet=4)
# the cloth folded back to one side, a bread basket and a single cup and saucer forgotten
box("ClothFolded", (0.5, 0.32, 0.03), (TABLE.x + 0.25, TABLE.y + 0.3, top[2] + 0.015), M_DAMASK, bevel=0.01, rot=(0, 0, 0.3))
lathe("Cup", [(0.0, 0.0), (0.03, 0.0), (0.045, 0.05), (0.04, 0.055), (0.0, 0.005)], (TABLE.x - 0.25, TABLE.y - 0.12, top[2] + 0.008), M_CHINA, steps=14)
lathe("Saucer", [(0.0, 0.0), (0.06, 0.0), (0.075, 0.012), (0.0, 0.006)], (TABLE.x - 0.25, TABLE.y - 0.12, top[2]), M_CHINA, steps=16)
for k, (ang, push) in enumerate(((20, 0.3), (110, 0.15), (200, 0.4), (290, 0.25))):
    a = math.radians(ang); pos = TABLE + Vector((math.cos(a), math.sin(a), 0)) * (0.78 + push)
    if (pos - Vector((0.3, -1.6, 0))).length < 1.0: pos = TABLE + Vector((math.cos(a), math.sin(a), 0)) * 0.75
    I.sabre_chair(f"Chair{k}", (pos.x, pos.y), face(pos, TABLE) + rng.uniform(-0.3, 0.3), M_MAHOG, M_SEAT)
anchor("room.breakfastTable", tuple(TABLE))

# the sideboard on the north wall: urn, tea caddy, cups, a dish of fruit; knife boxes
SB = Frame((-0.6, R.y1 - 0.34), math.pi)
SB.box("SideboardTop", (1.9, 0.62, 0.03), (0, 0, 0.92), M_MAHOG, bevel=0.006)
SB.box("SideboardBody", (1.8, 0.56, 0.26), (0, 0, 0.66 + (0.26) / 2), M_MAHOG, bevel=0.005)
for k in range(3): SB.box(f"SideboardDrawer{k}", (0.56, 0.01, 0.2), (-0.6 + 0.6 * k, 0.285, 0.69), M_MAHOG, bevel=0.003)
for sx in (-0.85, -0.3, 0.3, 0.85):
    SB.cyl(f"SideboardLeg{sx}", 0.026, 0.66, (sx, 0.22, 0.33), M_MAHOG, verts=8, r2=0.018)
lathe("TeaUrn", [(0.0, 0.0), (0.07, 0.0), (0.06, 0.04), (0.03, 0.08), (0.03, 0.12), (0.11, 0.18), (0.13, 0.28), (0.11, 0.38), (0.06, 0.42), (0.03, 0.46), (0.0, 0.47)],
      SB.p(0.0, 0.0, 0.95), M_SILVER, steps=18)
for k in range(5):
    lathe(f"SBCup{k}", [(0.0, 0.0), (0.03, 0.0), (0.045, 0.05), (0.04, 0.055), (0.0, 0.005)], SB.p(-0.7 + 0.12 * k, 0.12, 0.95), M_CHINA, steps=12)
lathe("FruitDish", [(0.0, 0.0), (0.06, 0.0), (0.06, 0.04), (0.16, 0.08), (0.0, 0.06)], SB.p(0.62, 0.0, 0.95), M_CHINA, steps=16)
for k in range(6):
    sphere(f"Apple{k}", 0.035, SB.p(0.62 + rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 1.03 + 0.03 * (k > 3)), plain("M_Apple", K.srgb((0.62, 0.28, 0.12)), rough=0.4) if k == 0 else bpy.data.materials["M_Apple"], seg=10)
for sx in (-1, 1):
    SB.box(f"KnifeBox{sx}", (0.22, 0.26, 0.36), (sx * 0.8, 0.0, 0.95 + (0.36) / 2), M_MAHOG, bevel=0.02)
I.picture("PicN1", R, 'N', R.x1 - (-0.6), 2.2, 1.1, 0.8, M_GILT, I.landscape_mat("M_Land1", 2))
I.picture("PicN2", R, 'N', R.x1 - 2.2, 2.0, 0.6, 0.75, M_GILT, I.landscape_mat("M_Land2", 4))

# the sofa against the north-east, a work table and a pair of chairs by the fire
def scroll_sofa(name, x, y, yaw, length=2.0):
    F_ = Frame((x, y), yaw)
    F_.box(f"{name}Rail", (length, 0.68, 0.15), (0, 0, 0.3), M_MAHOG, bevel=0.01)
    F_.box(f"{name}Seat", (length - 0.22, 0.6, 0.12), (0, 0.03, 0.43), M_SOFA, bevel=0.04)
    F_.box(f"{name}Back", (length - 0.08, 0.16, 0.48), (0, -0.27, 0.66), M_SOFA, bevel=0.05, rx=-0.12)
    F_.box(f"{name}BackRail", (length, 0.05, 0.05), (0, -0.32, 0.92), M_MAHOG, bevel=0.012)
    for sx in (-1, 1):
        F_.box(f"{name}ArmPad{sx}", (0.12, 0.6, 0.3), (sx * (length / 2 - 0.06), 0.0, 0.56), M_SOFA, bevel=0.04)
        cyl(f"{name}Bolster{sx}", 0.09, 0.55, F_.p(sx * (length / 2 - 0.17), 0.02, 0.58), M_SOFA, verts=12, rot=(math.pi / 2, 0, F_.yaw))
        for sy in (-1, 1):
            tube(f"{name}Leg{sx}{sy}", [F_.p(sx * (length / 2 - 0.05), sy * 0.3, 0.22), F_.p(sx * (length / 2 - 0.02) + sx * 0.04, sy * 0.33, 0.1),
                                        F_.p(sx * (length / 2 + 0.05), sy * 0.35, 0.0)], [0.024, 0.02, 0.015], M_MAHOG, sides=6)
scroll_sofa("Sofa", 1.95, R.y1 - 0.45, math.pi)
I.sabre_chair("ChairFire1", (2.3, -0.9), face((2.3, -0.9), (R.x1, 0.3)) + 0.3, M_MAHOG, M_SEAT)
I.sabre_chair("ChairWall1", (R.x0 + 0.32, -0.6), -math.pi / 2, M_MAHOG, M_SEAT)
I.sabre_chair("ChairWall2", (R.x0 + 0.32, 0.2), -math.pi / 2, M_MAHOG, M_SEAT)
PT = Frame((-1.15, R.y0 + 0.24), 0.0)       # pier table between the west and middle windows
PT.box("PierTop", (0.8, 0.38, 0.03), (0, 0, 0.82), M_MARBLE, bevel=0.006)
PT.box("PierApron", (0.76, 0.34, 0.08), (0, 0, 0.76), M_GILT, bevel=0.008)
for sx in (-1, 1): PT.cyl(f"PierLeg{sx}", 0.02, 0.72, (sx * 0.34, -0.1, 0.36), M_GILT, verts=8, r2=0.013)

# ----------------------------------------------------------------------------- light: clear autumn morning sun from the south-east, sky through three windows, the fire
READER = Vector((0.35, -1.55, 0))
sun_dir = Vector((-0.55, 0.78, -0.30)).normalized()
light_obj("Lamp.sun", 'SUN', 4.5, (1.0, 0.93, 0.82), (0, -6, 6), direction=tuple(sun_dir), angle=math.radians(1.5))
for k, x in enumerate(WIN_X):
    ld = bpy.data.lights.new(f"Lamp.windowSky{k}", 'AREA'); ld.energy = 140.0; ld.color = (0.82, 0.88, 1.0); ld.shape = 'RECTANGLE'; ld.size = 1.1; ld.size_y = 2.4
    wl = bpy.data.objects.new(f"Lamp.windowSky{k}", ld); wl.location = (x, R.y0 - 0.1, 1.75); K.link(wl)
    wl.rotation_euler = Vector((0.0, 1.0, -0.3)).to_track_quat('-Z', 'Y').to_euler()
light_obj("Lamp.fire", 'POINT', 20.0, (1.0, 0.5, 0.22), tuple(FIRE_BASE + Vector((-0.25, 0, 0.1))), shadow_soft_size=0.15)
world = bpy.data.worlds.new("Morning"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.62, 0.70, 0.82, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.2

# ----------------------------------------------------------------------------- anchors and living-scene sources
S.reader(READER, (0, 1))
anchor("scene.centre", tuple(TABLE))
anchor("room.door", tuple(R.at('W', R.y1 - DOOR_Y)))
S.fx("fx.fire.hearth", tuple(FIRE_BASE), 0.2)
sound("fire", "hearth", tuple(FIRE_BASE + Vector((-0.2, 0, 0.1))))
sound("clock", "mantel", FP(0, 0.15, SHELF_Z + 0.2))
sound("birds", "park", (0.0, R.y0 - 7.0, 3.0))
page = S.page_preview()
K.apply_transforms()

E = READER + Vector((0, 0, S.EYE))
cams = S.eye_cams([("Reader", 0), ("Left", -75), ("Right", 75), ("Behind", 180)], dz=-0.5, dist=5.0, extra=[
    ("Page", E, E + Vector((0, 5, -0.5)), 17),
    ("Table", TABLE + Vector((0.9, -1.0, 1.4)), TABLE + Vector((0, 0, 0.72)), 26),
    ("Corner", Vector((-3.0, -2.0, 1.9)), Vector((1.5, 1.2, 0.9)), 17),
])
probs = S.check_reader(ignore=("PagePreview", "WindowView"))
K.print_budget(exclude=("PagePreview",))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.0, captures_dir=ARGS.captures)

if ARGS.export or ARGS.bake:
    S.export(SID, cams, page=page, unlit_emit=("M_WindowView",),
             remove=[o.name for o in bpy.data.objects if o.name.startswith("WindowGlass_")],
             keep_names={"M_Chintz": "cloth.curtain.windows", "M_Embers": "MESH_Embers", "M_WindowView": "far.windowView"},
             size_for={"M_WallPaint": (1024, 64, 512), "M_FloorBoards": (1024, 128, 1024), "M_Carpet": (2048, 64, 512), "M_Ceiling": (512, 32, 128),
                       "M_Joinery": (2048, 64, 512), "M_DadoPaint": (512, 32, 256), "M_Mahogany": (2048, 256, 1024), "M_Chintz": (1024, 64, 512),
                       "M_SofaStripe": (512, 64, 256), "M_ChairSeat": (512, 64, 256), "M_WindowView": (1024,), "M_DoorMahogany": (512, 64, 256),
                       "M_Marble": (512, 64, 256), "M_Land1": (256, 32), "M_Land2": (256, 32)},
             default_size=(256, 64, 128))
print("DONE")
