"""
Fable step-in room: the Longbourn family drawing-room (Pride and Prejudice, chapters 1, 2, 4 and 5).

"Mr. Bennet ... was among the earliest of those who waited on Mr. Bingley ... observing his second daughter employed
in trimming a hat, he suddenly addressed her with, 'I hope Mr. Bingley will like it, Lizzy.'" (chapter 2)

The everyday family room of a modest gentleman's house in a Hertfordshire village, c.1811, on an October morning. About
6 x 5 m with a 3 m ceiling. Soft green distemper over a painted dado, a plain plaster cornice, oak boards under a worn
Turkey carpet. Two sash windows on the south wall (chintz curtains tied back) look onto the gravel sweep, the lawn and
shrubbery and the lane with its autumn trees. Opposite them a plain painted-pine chimney-piece with a small coal fire in a
hob grate, a brass fender and fire irons, a mantel clock, two brass candlesticks and an old landscape above. A
scroll-ended sofa on the west wall with a sofa table and a few books (Mary's extracts); a Pembroke work table by the
reader where a straw bonnet is being trimmed, ribbons, scissors and a work box; mahogany chairs of slightly
old-fashioned country taste; a six-panel door on the east wall. No people.

Light: autumn morning sun from the south-east through the two windows (patches on the carpet and the sofa), the pale
sky's fill, the small fire a warm accent. All of it is baked into the textures (the room is downloaded; no lightmapper
at runtime).

Reader: by the work table, facing the fireplace (+Y), sofa to the left, windows behind.

Living-scene nodes: fx.fire.hearth (radius extra), sound.fire.hearth, sound.clock.mantel, sound.birds.garden,
cloth.curtain.windows (sway weight in COLOR_0 R).

  blender -b -P blender/build_longbourn_drawing_room.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_longbourn_drawing_room.py -- --render --samples 48 --res 1400
  blender -b -P blender/build_longbourn_drawing_room.py -- --export
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b5 as S
import pride_kit as K
import pride_interior as I
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, mesh_from, Frame, anchor, sound, light_obj, camera)

SID = "longbourn-drawing-room"
ARGS = S.setup(SID, seed=1811)
scene = K.scene
scene.cycles.max_bounces = 8; scene.cycles.diffuse_bounces = 5
rng = random.Random(1811)

R = I.Room(-3.0, 3.0, -2.5, 2.5, 3.0, t=0.38)

# ----------------------------------------------------------------------------- materials
M_WALL = I.paint_mat("M_WallPaint", K.srgb((0.70, 0.74, 0.62)), rough=0.85, dirt=0.08)
M_DADO = I.paint_mat("M_DadoPaint", K.srgb((0.80, 0.79, 0.70)), rough=0.6, dirt=0.12)
M_JOIN = I.joinery_mat("M_Joinery", K.srgb((0.84, 0.82, 0.74)))
M_CEIL = I.paint_mat("M_Ceiling", K.srgb((0.86, 0.85, 0.80)), rough=0.9, dirt=0.0)
M_FLOOR = I.boards_mat("M_FloorBoards", light=(0.33, 0.22, 0.12), dark=(0.15, 0.09, 0.045), width=0.21)
M_CARPET = I.carpet_mat("M_Carpet", 0.2, 0.2, 2.1, 1.75, field=(0.13, 0.03, 0.02), ground2=(0.035, 0.05, 0.045), border=(0.03, 0.04, 0.045), buff=(0.24, 0.17, 0.10))
M_MAHOG = wood("M_Mahogany", base=(0.11, 0.035, 0.016), dark=(0.035, 0.011, 0.006), light=(0.20, 0.075, 0.035), scale=1.4, rough=(0.35, 0.6),
               grain_dir=(1, 1, 10), coat=0.15, ao=0.25, bump=0.15)
M_BRASS = plain("M_Brass", (0.70, 0.52, 0.27), rough=0.32, metallic=1.0)
M_IRON = noisy("M_Iron", [(0.025, 0.025, 0.027), (0.05, 0.05, 0.05), (0.035, 0.032, 0.03)], scale=30, rough=(0.45, 0.7), metallic=0.6)
M_SOOT = plain("M_Soot", (0.012, 0.011, 0.01), rough=0.95)
M_WAX = plain("M_Wax", K.srgb((0.93, 0.91, 0.85)), rough=0.45)
M_PANE = new_mat("M_Pane")[0]
M_SOFA = I.silk("M_SofaStripe", K.srgb((0.66, 0.60, 0.46)), K.srgb((0.80, 0.76, 0.62)), stripes=1.0, stripe_w=0.035, axis='X', sheen=0.5, rough=0.7)
M_CHINTZ = None
M_SEAT = I.silk("M_ChairSeat", K.srgb((0.40, 0.44, 0.36)), K.srgb((0.48, 0.52, 0.43)), damask=0.5, sheen=0.4, rough=0.75)
M_LAND = I.landscape_mat("M_Landscape", 3)
M_CLOCKFACE = plain("M_ClockFace", K.srgb((0.82, 0.78, 0.68)), rough=0.4)
M_PAGES = noisy("M_BookPages", [K.srgb((0.80, 0.76, 0.64)), K.srgb((0.72, 0.68, 0.56))], scale=200, rough=0.85, stretch=(1, 1, 30), bump=0.0)
M_CALF = noisy("M_Calf", [K.srgb((0.36, 0.20, 0.11)), K.srgb((0.46, 0.27, 0.15)), K.srgb((0.30, 0.16, 0.09))], scale=14, rough=(0.4, 0.65), bump=0.3, bump_dist=0.001)
M_STRAW = noisy("M_Straw", [K.srgb((0.78, 0.66, 0.42)), K.srgb((0.66, 0.53, 0.30)), K.srgb((0.84, 0.74, 0.50))], scale=60, rough=0.75,
                stretch=(1, 1, 1), bump=0.5, bump_dist=0.0015)
M_RIBBON = plain("M_Ribbon", K.srgb((0.30, 0.44, 0.58)), rough=0.35, sheen=0.6)
M_RIBBON2 = plain("M_RibbonRose", K.srgb((0.72, 0.42, 0.42)), rough=0.35, sheen=0.6)
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

# ----------------------------------------------------------------------------- openings, walls, floor, ceiling, mouldings
WIN_X = (-1.45, 1.45)
for k, x in enumerate(WIN_X):
    I.sash_window(f"Win{k}", R, 'S', x - R.x0, 1.05, 0.7, 2.0, M_JOIN, M_PANE, M_JOIN, panes=(3, 4), curtain_mat=None)
DOOR_Y = 1.45
M_DOOR = I.joinery_mat("M_DoorPaint", K.srgb((0.80, 0.78, 0.70)), rough=0.4)
I.six_panel_door("Door", R, 'E', DOOR_Y - R.y0, 0.92, 2.2, M_DOOR, M_JOIN, M_BRASS, open_deg=0, hinge_left=False)
I.build_walls(R, M_WALL)
K.box("Floor", (R.x1 - R.x0 + 0.8, R.y1 - R.y0 + 0.8, 0.04), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, -0.02), M_FLOOR)
box("Carpet", (4.2, 3.5, 0.012), (0.2, 0.2, 0.006), M_CARPET, bevel=0.004)
box("Ceiling", (R.x1 - R.x0 + 0.8, R.y1 - R.y0 + 0.8, 0.05), ((R.x0 + R.x1) / 2, (R.y0 + R.y1) / 2, R.h + 0.025), M_CEIL)
I.moulding_runs(R, "Skirting", I.skirting_profile(0.22), 0.0, M_JOIN)
I.moulding_runs(R, "ChairRail", I.rail_profile(), 0.88, M_JOIN, z_band=(0.84, 0.92))
I.moulding_runs(R, "Cornice", I.cornice_profile(0.16, 0.18), R.h, M_CEIL, z_band=(R.h - 0.18, R.h))
for w in ('S', 'E', 'N', 'W'):
    o, a, n, L = R.wall_frame(w)
    for k, (u0, u1) in enumerate(I.runs(R, w, 0.22, 0.86)):
        c = o + a * ((u0 + u1) / 2) + n * 0.002 + Vector((0, 0, 0.54))
        box(f"Dado{w}{k}", (abs(a.x) * (u1 - u0) + abs(n.x) * 0.004, abs(a.y) * (u1 - u0) + abs(n.y) * 0.004, 0.64), tuple(c), M_DADO)

# curtains: chintz on brass poles, open and tied back to the window sides (cloth.curtain)
CURT = []
for k, x in enumerate(WIN_X):
    o, a, n, L = R.wall_frame('S'); base = o + a * (x - R.x0)
    rod_z = 0.7 + 2.0 + 0.22
    cyl(f"Pole{k}", 0.018, 1.05 + 0.8, tuple(base + n * 0.1 + Vector((0, 0, rod_z))), M_BRASS, verts=10, rot=(0, math.pi / 2, 0))
    for sx in (-1, 1):
        sphere(f"Finial{k}{sx}", 0.035, tuple(base + a * (sx * 0.95) + n * 0.1 + Vector((0, 0, rod_z))), M_BRASS, seg=10)
        outer = sx * 0.9; inner = sx * 0.5
        c = I.curtain_panel(f"Curtain{k}{sx}", base, a, n, outer, inner, rod_z - 0.03, -0.01, M_CHINTZ, folds=4, depth=0.05)
        # gather the panel towards the tie-back at 1.0 m: pull the lower middle in toward the outer edge
        for v in c.data.vertices:
            zz = v.co.z; u = (v.co - base).dot(a)
            t = max(0.0, 1.0 - abs(zz - 1.0) / 1.2)
            v.co += a * ((outer - u) * 0.35 * t)
        CURT.append(c)
        box(f"TieBack{k}{sx}", (0.012, 0.03, 0.03), tuple(base + a * (sx * 0.84) + n * 0.1 + Vector((0, 0, 1.0))), M_BRASS)
for c in CURT:
    K.add_sway(c, lambda p: max(0.0, min(1.0, (2.9 - p.z) / 2.9)) * 0.6)

# the view backdrop: an arc 5-9 m outside the south wall (not seen by the light: no shadow or bounce from it)
vv = []; vf = []
NU, NV = 24, 6
for j in range(NV + 1):
    for i in range(NU + 1):
        a_ = math.radians(-70 + 140 * i / NU); r = 8.0
        vv.append((r * math.sin(a_) * 1.3, R.y0 - 0.6 - r * math.cos(a_) * 0.75, -0.7 + 11.0 * j / NV))
for j in range(NV):
    for i in range(NU): vf.append((j * (NU + 1) + i, j * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i))
view = mesh_from("WindowView", vv, vf, M_VIEW)
for ob_ in (view,):
    ob_.visible_shadow = False; ob_.visible_diffuse = False; ob_.visible_glossy = False
box("OutsideGround", (12, 4, 0.05), (0, R.y0 - R.t - 2.0, -0.72), noisy("M_Gravel", [K.srgb((0.56, 0.47, 0.34)), K.srgb((0.66, 0.58, 0.44))], scale=50, rough=0.9))

# ----------------------------------------------------------------------------- the chimney-piece (north wall): painted pine, a hob grate, small coal fire
F = Frame((0.0, R.y1), math.pi)        # local +Y into the room (-Y world)
def FP(x, y, z): return F.p(x, y, z)
OW, OH = 0.86, 0.86
M_HEARTH = noisy("M_HearthStone", [K.srgb((0.52, 0.50, 0.46)), K.srgb((0.44, 0.42, 0.38)), K.srgb((0.58, 0.56, 0.50))], scale=6, rough=0.75, bump=0.2)
F.box("HearthStone", (1.6, 0.5, 0.035), (0, 0.25, 0.0175), M_HEARTH, bevel=0.004)
F.box("Breast", (1.9, 0.12, R.h), (0, -0.0, R.h / 2), M_WALL)
for sx in (-1, 1):
    F.box(f"Jamb{sx}", (0.22, 0.14, OH), (sx * (OW / 2 + 0.11), 0.12, OH / 2), M_JOIN, bevel=0.006)
    F.box(f"JambBead{sx}", (0.03, 0.02, OH - 0.04), (sx * (OW / 2 + 0.02), 0.2, OH / 2), M_JOIN, bevel=0.008)
    F.box(f"Block{sx}", (0.24, 0.16, 0.22), (sx * (OW / 2 + 0.11), 0.13, OH + 0.11), M_JOIN, bevel=0.008)
    F.box(f"BlockPanel{sx}", (0.15, 0.01, 0.13), (sx * (OW / 2 + 0.11), 0.215, OH + 0.11), M_JOIN, bevel=0.004)
F.box("Frieze", (OW, 0.13, 0.22), (0, 0.12, OH + 0.11), M_JOIN, bevel=0.004)
F.box("Shelf", (1.56, 0.22, 0.045), (0, 0.15, OH + 0.245), M_JOIN, bevel=0.01)
F.box("ShelfBed", (1.48, 0.17, 0.03), (0, 0.13, OH + 0.21), M_JOIN, bevel=0.006)
# the opening: a brick-lined fireplace with a hob grate (cast-iron hobs either side of a barred basket)
F.box("FireBack", (OW, 0.03, OH), (0, 0.065, OH / 2), M_SOOT)
M_BRICK = noisy("M_FireBrick", [K.srgb((0.20, 0.10, 0.07)), K.srgb((0.12, 0.07, 0.05)), K.srgb((0.06, 0.05, 0.04))], scale=12, rough=0.9)
for sx in (-1, 1):
    F.box(f"Cheek{sx}", (0.04, 0.16, OH), (sx * (OW / 2 - 0.02), 0.15, OH / 2), M_BRICK)
    F.box(f"Hob{sx}", (0.2, 0.2, 0.36), (sx * 0.31, 0.15, 0.18), M_IRON, bevel=0.006)
    F.box(f"HobTop{sx}", (0.22, 0.22, 0.02), (sx * 0.31, 0.15, 0.37), M_IRON, bevel=0.004)
F.box("BasketFloor", (0.4, 0.17, 0.02), (0, 0.15, 0.17), M_IRON)
for k in range(4):
    F.box(f"BasketBar{k}", (0.42, 0.012, 0.012), (0, 0.235, 0.19 + k * 0.042), M_IRON, bevel=0.003)
F.box("Throat", (OW - 0.1, 0.12, 0.05), (0, 0.11, OH - 0.04), M_SOOT)
cr = random.Random(5)
for k in range(20):
    lx = cr.uniform(-0.17, 0.17); ly = cr.uniform(0.08, 0.22); lz = 0.2 + cr.uniform(0, 0.08) * (1 - abs(lx) / 0.22)
    sphere(f"Coal{k}", cr.uniform(0.025, 0.045), FP(lx, ly, lz), M_EMBERS if lz < 0.25 or cr.random() < 0.45 else M_IRON, seg=6,
           scale=(cr.uniform(0.8, 1.3), cr.uniform(0.8, 1.3), cr.uniform(0.6, 0.9)))
FIRE_BASE = Vector(FP(0, 0.16, 0.24))
F.box("FenderFront", (1.3, 0.01, 0.085), (0, 0.48, 0.0425 + 0.035), M_BRASS, bevel=0.003)
for sx in (-1, 1): F.box(f"FenderSide{sx}", (0.01, 0.26, 0.085), (sx * 0.65, 0.35, 0.0425 + 0.035), M_BRASS, bevel=0.003)
for k in range(3):
    p0 = Vector(FP(0.58, 0.32 + 0.02 * k, 0.04)); p1 = Vector(FP(0.6 - 0.03 * k, 0.24, 0.66))
    tube(f"FireIron{k}", [p0, p1], 0.007, M_IRON, sides=5)
    sphere(f"FireIronKnob{k}", 0.016, tuple(p1 + Vector((0, 0, 0.01))), M_BRASS, seg=8)
SHELF_Z = OH + 0.268
# mantel clock (a small mahogany balloon clock), two brass candlesticks, a pair of china spill vases
F.box("ClockBase", (0.2, 0.12, 0.03), (0, 0.13, SHELF_Z + 0.015), M_MAHOG, bevel=0.006)
lathe("ClockBody", [(0.0, 0.0), (0.06, 0.0), (0.055, 0.05), (0.05, 0.1), (0.0, 0.1)], FP(0, 0.13, SHELF_Z + 0.03), M_MAHOG, steps=12)
cyl("ClockDrum", 0.1, 0.1, FP(0, 0.11, SHELF_Z + 0.22), M_MAHOG, verts=24, rot=(math.pi / 2, 0, F.yaw))
cyl("ClockDial", 0.072, 0.01, FP(0, 0.165, SHELF_Z + 0.22), M_CLOCKFACE, verts=24, rot=(math.pi / 2, 0, F.yaw))
cyl("ClockBezel", 0.078, 0.006, FP(0, 0.162, SHELF_Z + 0.22), M_BRASS, verts=24, rot=(math.pi / 2, 0, F.yaw))
for k, ang in enumerate((math.radians(-55), math.radians(150))):
    ln = 0.05 if k == 0 else 0.065
    F.box(f"ClockHand{k}", (0.004, 0.004, ln), (math.sin(ang) * ln / 2, 0.172, SHELF_Z + 0.22 + math.cos(ang) * ln / 2), M_IRON, ry=-ang)
sphere("ClockFinial", 0.02, FP(0, 0.11, SHELF_Z + 0.335), M_BRASS, seg=8)
for sx in (-1, 1):
    I.candlestick(f"MantelStick{sx}", FP(sx * 0.55, 0.14, SHELF_Z), M_BRASS, M_WAX, height=0.24, candle_h=0.2, flame=False)
M_CHINA = plain("M_China", K.srgb((0.86, 0.86, 0.84)), rough=0.15, coat=0.6)
for sx in (-1, 1):
    lathe(f"Spill{sx}", [(0.0, 0.0), (0.03, 0.0), (0.035, 0.03), (0.028, 0.1), (0.034, 0.13), (0.0, 0.13)], FP(sx * 0.32, 0.14, SHELF_Z), M_CHINA, steps=12)
# the old landscape above the chimney-piece
I.picture("Overmantel", I.Room(R.x0, R.x1, R.y0, R.y1 - 0.06, R.h), 'N', R.x1 - 0.0, 2.15, 0.95, 0.68, plain("M_Frame", K.srgb((0.42, 0.30, 0.14)), rough=0.4, metallic=0.6), M_LAND)
anchor("room.fireplace", FP(0, 0.4, 0))

# ----------------------------------------------------------------------------- furniture
def face(pos, target): return math.atan2(-(target[0] - pos[0]), target[1] - pos[1])

def scroll_sofa(name, x, y, yaw, length=1.95):
    F = Frame((x, y), yaw)
    F.box(f"{name}Rail", (length, 0.68, 0.15), (0, 0, 0.3), M_MAHOG, bevel=0.01)
    F.box(f"{name}Seat", (length - 0.22, 0.6, 0.12), (0, 0.03, 0.43), M_SOFA, bevel=0.04)
    F.box(f"{name}Back", (length - 0.08, 0.16, 0.48), (0, -0.27, 0.66), M_SOFA, bevel=0.05, rx=-0.12)
    F.box(f"{name}BackRail", (length, 0.05, 0.05), (0, -0.32, 0.92), M_MAHOG, bevel=0.012)
    for sx in (-1, 1):
        F.box(f"{name}ArmPad{sx}", (0.12, 0.6, 0.3), (sx * (length / 2 - 0.06), 0.0, 0.56), M_SOFA, bevel=0.04)
        cyl(f"{name}Bolster{sx}", 0.09, 0.55, F.p(sx * (length / 2 - 0.17), 0.02, 0.58), M_SOFA, verts=12, rot=(math.pi / 2, 0, F.yaw))
        tube(f"{name}ArmWood{sx}", [F.p(sx * length / 2, 0.3, 0.38), F.p(sx * length / 2, 0.3, 0.62), F.p(sx * length / 2 * 1.02, 0.18, 0.75),
                                    F.p(sx * length / 2 * 1.04, 0.05, 0.73), F.p(sx * length / 2 * 1.02, -0.2, 0.71)], 0.032, M_MAHOG, sides=6)
        for sy in (-1, 1):
            tube(f"{name}Leg{sx}{sy}", [F.p(sx * (length / 2 - 0.05), sy * 0.3, 0.22), F.p(sx * (length / 2 - 0.02) + sx * 0.04, sy * 0.33, 0.1),
                                        F.p(sx * (length / 2 + 0.05), sy * 0.35, 0.0)], [0.024, 0.02, 0.015], M_MAHOG, sides=6)
    return F
SOFA = Vector((R.x0 + 0.45, 0.15, 0))
scroll_sofa("Sofa", SOFA.x, SOFA.y, -math.pi / 2)          # against the west wall, facing +X
# a cushion left in the corner of the sofa
sphere("SofaCushion", 0.2, (SOFA.x + 0.05, SOFA.y + 0.62, 0.62), M_SEAT, seg=12, scale=(0.5, 1.0, 0.9))

# sofa table in front of the sofa, with Mary's books and her extract book
ST = Frame((SOFA.x + 0.95, SOFA.y - 0.1), math.pi / 2)
ST.box("SofaTableTop", (1.2, 0.5, 0.03), (0, 0, 0.7), M_MAHOG, bevel=0.006)
ST.box("SofaTableApron", (1.0, 0.42, 0.1), (0, 0, 0.635), M_MAHOG, bevel=0.004)
for sx in (-1, 1):
    ST.box(f"SofaTableEnd{sx}", (0.04, 0.08, 0.5), (sx * 0.42, 0, 0.35), M_MAHOG, bevel=0.01)
    ST.box(f"SofaTableFoot{sx}", (0.05, 0.5, 0.05), (sx * 0.42, 0, 0.05), M_MAHOG, bevel=0.015)
ST.box("SofaTableStretcher", (0.86, 0.04, 0.04), (0, 0, 0.18), M_MAHOG, bevel=0.01)
M_BOARDS = noisy("M_BookBoards", [K.srgb((0.22, 0.26, 0.20)), K.srgb((0.28, 0.32, 0.25))], scale=40, rough=0.7)
zz = 0.715
for k, ((t_, w_, h_), yaw, mat) in enumerate((((0.035, 0.15, 0.23), 0.12, M_CALF), ((0.028, 0.13, 0.2), -0.2, M_BOARDS), ((0.04, 0.16, 0.24), 0.35, M_CALF))):
    I.book(f"Book{k}", ST.p(-0.32 + 0.01 * k, 0.03 * (k % 2), zz + t_ / 2), (t_, w_, h_), ST.yaw + yaw + 0.4, mat, M_PAGES, roll=math.pi / 2)
    zz += t_
# the open extract book, a pen and an inkpot
OB = Vector(ST.p(0.15, 0.0, 0.716))
box("ExtractBookL", (0.16, 0.22, 0.012), tuple(OB + Vector((0.0, -0.085, 0))), M_PAGES, rot=(0, -0.05, 0))
box("ExtractBookR", (0.16, 0.22, 0.012), tuple(OB + Vector((0.0, 0.085, 0))), M_PAGES, rot=(0, 0.05, 0))
box("ExtractCover", (0.17, 0.36, 0.006), tuple(OB + Vector((0, 0, -0.005))), M_BOARDS)
lathe("InkPot", [(0.0, 0.0), (0.03, 0.0), (0.03, 0.035), (0.012, 0.045), (0.012, 0.055), (0.0, 0.055)], ST.p(0.42, -0.1, 0.715), plain("M_InkGlass", (0.02, 0.025, 0.03), rough=0.1), steps=12)
tube("Quill", [Vector(ST.p(0.3, 0.05, 0.722)), Vector(ST.p(0.48, 0.14, 0.73))], [0.003, 0.002], M_LINEN, sides=4)

# the Pembroke work table at the reader's right, with the bonnet being trimmed
READER = Vector((0.55, -0.85, 0))
WT = Vector((1.5, -0.65, 0))
WF = Frame((WT.x, WT.y), math.radians(-12))
WF.box("WorkTop", (0.78, 0.52, 0.025), (0, 0, 0.71), M_MAHOG, bevel=0.005)
for sx in (-1, 1):
    WF.box(f"WorkLeaf{sx}", (0.78, 0.18, 0.02), (0, sx * 0.34, 0.705), M_MAHOG, bevel=0.004)
WF.box("WorkApron", (0.66, 0.44, 0.1), (0, 0, 0.645), M_MAHOG, bevel=0.004)
WF.box("WorkDrawerFront", (0.4, 0.01, 0.07), (0, -0.225, 0.645), M_MAHOG, bevel=0.003)
sphere("WorkKnob", 0.012, WF.p(0, -0.235, 0.645), M_BRASS, seg=8)
for sx in (-1, 1):
    for sy in (-1, 1):
        WF.cyl(f"WorkLeg{sx}{sy}", 0.022, 0.6, (sx * 0.3, sy * 0.19, 0.3), M_MAHOG, verts=8, r2=0.014)
TOPZ = 0.723
# the straw poke bonnet upside down on the table, ribbons loose beside it
BN = Vector(WF.p(-0.08, 0.02, TOPZ))
lathe("BonnetCrown", [(0.0, 0.0), (0.06, 0.0), (0.085, 0.01), (0.095, 0.04), (0.095, 0.11), (0.09, 0.12), (0.0, 0.122)], tuple(BN), M_STRAW, steps=20,
      rot=(0, 0, 0.3))
brim = []; bf = []
for j in range(5):
    for i in range(21):
        a_ = math.radians(-120 + 240 * i / 20); r = 0.095 + 0.12 * j / 4
        lift = 0.005 + 0.03 * (j / 4) ** 1.5 * (0.6 + 0.4 * math.cos(a_))
        brim.append(tuple(BN + Vector((math.cos(a_ + 0.3) * r, math.sin(a_ + 0.3) * r * 0.92, lift + 0.003))))
for j in range(4):
    for i in range(20): bf.append((j * 21 + i, j * 21 + i + 1, (j + 1) * 21 + i + 1, (j + 1) * 21 + i))
o_ = mesh_from("BonnetBrim", brim, bf, M_STRAW, smooth=True)
sm = o_.modifiers.new("Solid", 'SOLIDIFY'); sm.thickness = 0.004
# a ribbon round the crown and its loose ends trailing across the table
tube("BonnetBand", [tuple(BN + Vector((math.cos(a_) * 0.097, math.sin(a_) * 0.097, 0.05))) for a_ in [2 * math.pi * k / 16 for k in range(17)]],
     0.012, M_RIBBON, sides=4)
def ribbon(name, pts, w, mat):
    vs = []; fs = []
    for i, p in enumerate(pts):
        p = Vector(p); d = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])); d.z = 0; d.normalize()
        sd = Vector((-d.y, d.x, 0)) * w / 2
        vs += [tuple(p - sd), tuple(p + sd)]
        if i: fs.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
    return mesh_from(name, vs, fs, mat, smooth=True)
ribbon("RibbonEnd1", [WF.p(-0.0 + 0.04 * k, -0.08 - 0.012 * k + 0.02 * math.sin(k), TOPZ + 0.002 + (0.02 if k < 2 else 0)) for k in range(9)], 0.028, M_RIBBON)
ribbon("RibbonEnd2", [WF.p(0.02 + 0.035 * k, -0.04 + 0.03 * math.sin(k * 0.8), TOPZ + 0.0025) for k in range(8)], 0.028, M_RIBBON)
# a reel of rose ribbon, scissors, a pincushion and a work box with its lid up
cyl("RibbonReel", 0.035, 0.03, WF.p(0.25, 0.12, TOPZ), M_RIBBON2, verts=16)
cyl("ReelCheekA", 0.04, 0.004, WF.p(0.25, 0.12, TOPZ), M_MAHOG, verts=16)
cyl("ReelCheekB", 0.04, 0.004, WF.p(0.25, 0.12, TOPZ + 0.03), M_MAHOG, verts=16)
ribbon("RibbonRoseTail", [WF.p(0.25 - 0.04 * k, 0.08 - 0.01 * k * k, TOPZ + 0.0015) for k in range(6)], 0.022, M_RIBBON2)
for sgn in (-1, 1):
    S_ = Frame((WF.p(0.14, -0.14, 0)[0], WF.p(0.14, -0.14, 0)[1]), WF.yaw + 0.5 + sgn * 0.12)
    S_.box(f"ScissorBlade{sgn}", (0.006, 0.08, 0.002), (0, 0.04, TOPZ + 0.002 + (sgn + 1) * 0.0012), M_STEEL)
    tube(f"ScissorBow{sgn}", [S_.p(sgn * 0.012 + 0.012 * math.cos(t), -0.018 + 0.012 * math.sin(t), TOPZ + 0.003) for t in [2 * math.pi * k / 10 for k in range(11)]],
         0.0018, M_STEEL, sides=4)
sphere("Pincushion", 0.035, WF.p(-0.27, -0.14, TOPZ + 0.015), plain("M_PinVelvet", K.srgb((0.45, 0.20, 0.22)), rough=0.8, sheen=0.8), seg=12, scale=(1, 1, 0.55))
WB = Frame(WF.p(-0.26, 0.14, 0)[:2], WF.yaw + 0.1)
M_SATINWOOD = wood("M_Satinwood", base=(0.55, 0.38, 0.18), dark=(0.32, 0.2, 0.08), light=(0.72, 0.52, 0.28), scale=2.0, rough=(0.3, 0.5), coat=0.3)
WB.box("WorkBox", (0.24, 0.16, 0.08), (0, 0, TOPZ + (0.08) / 2), M_SATINWOOD, bevel=0.004)
WB.box("WorkBoxTray", (0.22, 0.14, 0.01), (0, 0, TOPZ + 0.07 + (0.01) / 2), plain("M_BoxLining", K.srgb((0.52, 0.22, 0.25)), rough=0.8))
WB.box("WorkBoxLid", (0.24, 0.006, 0.16), (0, 0.083, TOPZ + 0.08 + (0.16) / 2), M_SATINWOOD, bevel=0.002, rx=-0.25)
for k in range(4):
    cyl(f"Bobbin{k}", 0.008, 0.02, WB.p(-0.08 + 0.05 * k, -0.02, TOPZ + 0.075), [M_RIBBON, M_RIBBON2, M_LINEN, M_STRAW][k], verts=8)
I.sabre_chair("WorkChair", (WT.x + 0.15, WT.y + 0.55), face((WT.x + 0.15, WT.y + 0.55), (WT.x, WT.y)) + 0.35, M_MAHOG, M_SEAT)
anchor("room.workTable", tuple(WT))

# upright chairs along the walls and by the fire; an armchair by the fire for Mrs Bennet
I.sabre_chair("ChairE1", (R.x1 - 0.32, -0.3), -math.pi / 2 - 0.0 + math.pi, M_MAHOG, M_SEAT)
I.sabre_chair("ChairE2", (R.x1 - 0.32, 0.45), math.pi / 2, M_MAHOG, M_SEAT)
I.sabre_chair("ChairW", (R.x0 + 0.35, -1.65), -math.pi / 2, M_MAHOG, M_SEAT)
I.sabre_chair("ChairFire", (0.95, 1.5), face((0.95, 1.5), (0.0, 2.0)) + 0.6, M_MAHOG, M_SEAT)
def bergere(name, x, y, yaw):
    F = Frame((x, y), yaw)
    F.box(f"{name}Frame", (0.66, 0.6, 0.12), (0, 0, 0.36), M_MAHOG, bevel=0.01)
    F.box(f"{name}Cushion", (0.56, 0.52, 0.11), (0, 0.04, 0.47), M_SEAT, bevel=0.035)
    F.box(f"{name}Back", (0.62, 0.1, 0.55), (0, -0.27, 0.72), M_SEAT, bevel=0.04, rx=-0.1)
    tube(f"{name}TopRail", [F.p(-0.33, -0.3, 0.98), F.p(0, -0.34, 1.0), F.p(0.33, -0.3, 0.98)], 0.02, M_MAHOG, sides=6)
    for sx in (-1, 1):
        F.box(f"{name}Side{sx}", (0.07, 0.52, 0.28), (sx * 0.31, -0.02, 0.56), M_SEAT, bevel=0.025)
        tube(f"{name}Arm{sx}", [F.p(sx * 0.32, -0.28, 0.7), F.p(sx * 0.33, 0.1, 0.71), F.p(sx * 0.33, 0.27, 0.66), F.p(sx * 0.32, 0.29, 0.42)], 0.022, M_MAHOG, sides=6)
        for sy in (-1, 1):
            F.cyl(f"{name}Leg{sx}{sy}", 0.022, 0.32, (sx * 0.28, sy * 0.25, 0.16), M_MAHOG, verts=8, r2=0.016)
bergere("ArmchairFire", -1.15, 1.45, face((-1.15, 1.45), (0.0, 2.2)) - 0.2)
# a pier table between the windows with a work basket; a small bookless side table by the door
PT = Frame((0.0, R.y0 + 0.24), 0.0)
PT.box("PierTop", (0.9, 0.42, 0.03), (0, 0, 0.8), M_MAHOG, bevel=0.006)
PT.box("PierApron", (0.84, 0.38, 0.09), (0, 0, 0.74), M_MAHOG, bevel=0.005)
for sx in (-1, 1):
    for sy in (-1, 1): PT.cyl(f"PierLeg{sx}{sy}", 0.02, 0.7, (sx * 0.38, sy * 0.15, 0.35), M_MAHOG, verts=8, r2=0.013)
lathe("WorkBasket", [(0.0, 0.0), (0.1, 0.0), (0.14, 0.08), (0.145, 0.1), (0.0, 0.1)], PT.p(0.15, 0.0, 0.815), M_STRAW, steps=16)
I.picture("PierGlassFrame", R, 'S', 3.0, 1.75, 0.55, 0.75, plain("M_Frame2", K.srgb((0.42, 0.30, 0.14)), rough=0.4, metallic=0.6),
          plain("M_Mirror", (0.62, 0.64, 0.64), rough=0.05, metallic=1.0))
# two small pictures on the west wall above the sofa, a silhouette pair on the east wall
I.picture("PicW1", R, 'W', R.y1 - SOFA.y - 0.55, 1.75, 0.45, 0.36, plain("M_Frame3", K.srgb((0.12, 0.07, 0.04)), rough=0.4), I.landscape_mat("M_Land2", 5))
I.picture("PicW2", R, 'W', R.y1 - SOFA.y + 0.55, 1.75, 0.45, 0.36, plain("M_Frame3b", K.srgb((0.12, 0.07, 0.04)), rough=0.4), I.landscape_mat("M_Land3", 7))

# ----------------------------------------------------------------------------- light: autumn morning sun from the south-east, sky, the fire
sun_dir = Vector((-0.45, 0.85, -0.42)).normalized()    # travelling north-west and down (from the south-east)
light_obj("Lamp.sun", 'SUN', 4.2, (1.0, 0.92, 0.80), (0, -6, 6), direction=tuple(sun_dir), angle=math.radians(1.5))
for k, x in enumerate(WIN_X):     # sky light through each window, as an area light in the opening (soft daylight)
    ld = bpy.data.lights.new(f"Lamp.windowSky{k}", 'AREA'); ld.energy = 120.0; ld.color = (0.80, 0.86, 1.0); ld.shape = 'RECTANGLE'; ld.size = 1.0; ld.size_y = 1.95
    wl = bpy.data.objects.new(f"Lamp.windowSky{k}", ld); wl.location = (x, R.y0 - 0.1, 1.7); K.link(wl)
    wl.rotation_euler = Vector((0.0, 1.0, -0.35)).to_track_quat('-Z', 'Y').to_euler()
light_obj("Lamp.fire", 'POINT', 22.0, (1.0, 0.5, 0.22), tuple(FIRE_BASE + Vector((0, -0.25, 0.1))), shadow_soft_size=0.15)
world = bpy.data.worlds.new("AutumnMorning"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.62, 0.70, 0.82, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.2

# ----------------------------------------------------------------------------- anchors and living-scene sources
S.reader(READER, (0, 1))
anchor("scene.centre", (0.2, 0.3, 0.0))
anchor("room.door", tuple(R.at('E', DOOR_Y - R.y0)))
S.fx("fx.fire.hearth", tuple(FIRE_BASE), 0.18)
sound("fire", "hearth", tuple(FIRE_BASE + Vector((0, -0.2, 0.1))))
sound("clock", "mantel", FP(0, 0.15, SHELF_Z + 0.22))
sound("birds", "garden", (0.0, R.y0 - 6.0, 3.0))
page = S.page_preview()
K.apply_transforms()

# ----------------------------------------------------------------------------- cameras
E = READER + Vector((0, 0, S.EYE))
cams = S.eye_cams([("Reader", 0), ("Left", -75), ("Right", 70), ("Behind", 180)], extra=[
    ("Page", E, E + Vector((0, 5, -0.55)), 17),
    ("WorkTable", WT + Vector((-0.55, -0.75, 1.25)), WT + Vector((-0.05, 0.05, 0.72)), 30),
    ("Fire", Vector((0.9, 0.2, 1.3)), Vector(FP(0, 0.2, 0.75)), 24),
    ("Corner", Vector((2.5, -2.1, 1.7)), Vector((-1.5, 1.2, 0.8)), 17),
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
                       "M_Joinery": (1024, 64, 512), "M_DadoPaint": (512, 32, 256), "M_Mahogany": (2048, 256, 1024), "M_Chintz": (1024, 64, 512),
                       "M_SofaStripe": (1024, 64, 256), "M_ChairSeat": (512, 64, 256), "M_WindowView": (1024,), "M_DoorPaint": (512, 32, 256),
                       "M_Straw": (512, 64, 256), "M_HearthStone": (256, 64, 128), "M_Landscape": (512, 32), "M_Land2": (256, 32), "M_Land3": (256, 32)},
             default_size=(256, 64, 128))
print("DONE")
