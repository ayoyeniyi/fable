"""
Fable: Ogilvy's observatory at Ottershaw (The War of the Worlds, book I, chapter 1, "The Eve of the War").

"In spite of all that has happened since, I still remember that vigil very distinctly: the black and silent
observatory, the shadowed lantern throwing a feeble glow upon the floor in the corner, the steady ticking of the
clockwork of the telescope, the little slit in the roof - an oblong profundity with the stardust streaked across it."
"Looking through the telescope, one saw a circle of deep blue and the little round planet swimming in the field."
"... to the little table where the siphon stood."

A small private observatory of the 1890s: a round drum 4.8 m across of varnished pitch-pine matchboarding, a
timber dome painted inside an old cream, carried on an iron rail and rollers, with its shutter slid back so a slit
0.7 m wide runs from low in the east-south-east up past the zenith. Through it, a midnight sky in August: deep blue,
the Milky Way streaked across the slit, Mars a small ruddy star low in the slit. On a cast-iron pier in the middle,
a six-inch brass refractor on a German equatorial mount points up through the slit; its weight-driven clock drive
(a governor of two brass balls, the drive rod to the worm on the right-ascension wheel) is the ticking. A dark
bull's-eye lantern stands on the floor in the north-east corner of the drum, its shutter half closed, throwing a
feeble pool of light along the boards. A little round tripod table holds the soda siphon and two tumblers; a writing
desk with the observing book, a star atlas and an inkstand stands against the west wall; an observing chair stands
by the eyepiece. No people (Ogilvy and the narrator are left out).

Builds the room procedurally (no downloaded models, textures or HDRIs) with PBR node materials, the lantern and a
faint starlight from the slit, then (by flag) renders Cycles stills, bakes materials to textures, merges static
meshes by material and exports a .gltf + .bin + textures/ for Unity (helpers in wotw_kit.py).

Node names Unity relies on:
  anchor.reader.entrance  the reader's feet (floor, z=0), north-north-west of the pier, near the wall
  anchor.reader.look      eye height (1.55 m), 2 m ahead (east-south-east): the slit and telescope rise to the right
  anchor.scene.centre     the floor at the foot of the pier
  anchor.room.telescope (the eyepiece), anchor.room.slit (the slit's centre), anchor.room.lantern, anchor.room.siphon,
  anchor.room.door
  Lamp.lantern (SPOT, the lantern's half-shuttered beam along the floor), Lamp.lanternglow (POINT, faint spill from
  the lantern's vents), Lamp.starlight (SPOT, wide and soft, the faint sky light down through the slit; FableBuild colours all Lamp*
  lights warm unless the scene overrides it: this one wants a cool 0.55, 0.65, 1.0 at a tenth of the lantern)
  Living scenes (docs/LIVING_SCENES.md): fx.lantern.0 (the flame inside the lantern), sound.clock.0 (the clock drive)
  far.sky (the night sky seen through the slit: emissive, unlit; named far.* so it is treated as backdrop)

Axes: metres, Blender +Z up, +Y north, +X east. The pier stands on the origin.

Run headless:
  blender -b -P blender/build_ogilvys_observatory.py -- --out out/ogilvys-observatory --render --quick --res 800
  blender -b -P blender/build_ogilvys_observatory.py -- --out out/ogilvys-observatory --bake --export --tex 2048
  blender -b -P blender/build_ogilvys_observatory.py -- --out captures/blender/ogilvys-observatory --prefix blender-render_ --render --res 1400 --samples 128
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wotw_kit as K
from wotw_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, bump_from, c4, obj_xyz, noise_tex, white,
                      combine, tone_ramp, wood, planks, paint, metal, fabric, glass, plain, box, cyl, sphere, torus, lathe,
                      orient, grid_surface, tube, sweep_rect, mesh_from, anchor, marker, Frame, camera, TWO_PI)

args, scene = K.begin("OgilvysObservatory", "out/ogilvys-observatory")
OUT = K.OUT
rnd = random.Random(1894)

# ----------------------------------------------------------------------------- dimensions (metres)
R = 2.85                 # drum inner radius (a 19 ft observatory)
WH = 2.10                # drum wall height to the curb
CURB_H = 0.16
ZD = WH + 0.30           # the dome springs here (rollers and the dome's own ring between)
RO = R + 0.07            # dome outer skin
HW = 0.36                # slit half width
PHI0, PHI1 = math.radians(11.25), math.radians(105.0)
EYE = 1.55
LAT = math.radians(51.37)

def az_dir(az_deg):
    """Compass azimuth (0 = north, 90 = east) -> unit vector in the floor plane."""
    a = math.radians(az_deg); return Vector((math.sin(a), math.cos(a), 0.0))

SLIT_AZ = 118.0
H = az_dir(SLIT_AZ); SIDE = Vector((H.y, -H.x, 0.0)); UP = Vector((0, 0, 1))
DC = Vector((0, 0, ZD))
READER = -H * 0.55 + SIDE * 1.75          # beside the telescope, south-west of the pier, the tube off to the left
LOOK_AZ = 97.0                             # the slit rises straight ahead above the page; the tube climbs on the left
LOOK = az_dir(LOOK_AZ)

def dome_pt(x, phi, r=R):
    """The dome in slit coordinates: x across the slit, phi from the slit's horizon (0) over the top (pi)."""
    s = math.sqrt(max(r * r - x * x, 0.0))
    return DC + SIDE * x + (H * math.cos(phi) + UP * math.sin(phi)) * s

# ----------------------------------------------------------------------------- materials
def floor_wear(nt, X, Y, Z):
    """Feet wear round the pier and the eyepiece side, and the path from the door."""
    rr = node(nt, "ShaderNodeVectorMath", operation='LENGTH'); nt.links.new(combine(nt, X, Y, 0.0), rr.inputs[0])
    ring = maprange(nt, rr.outputs["Value"], 1.4, 0.45, 0.0, 0.55, 'SMOOTHSTEP')
    n = noise_tex(nt, combine(nt, X, Y, 0.0), 2.5, 4.0, 0.6)
    return math_(nt, 'MULTIPLY', ring, maprange(nt, n.outputs["Fac"], 0.35, 0.65, 0.3, 1.0))

M_FLOOR = planks("M_Floorboards", 0.165, 2.6, [(0.30, 0.19, 0.10), (0.36, 0.23, 0.12), (0.27, 0.17, 0.09), (0.33, 0.215, 0.115), (0.40, 0.26, 0.14)],
                 (0.05, 0.035, 0.025), along='X', rough=0.62, wear=floor_wear, seed=1.0)
DADO = 1.05
M_WALL = planks("M_Matchboard", 0.095, 9.0, [(0.30, 0.175, 0.08), (0.32, 0.19, 0.088), (0.285, 0.165, 0.075), (0.31, 0.18, 0.082)],
                (0.09, 0.05, 0.025), along='Z', rough=0.42, seed=2.0, gap_w=0.025, bumpk=0.4, grain_k=0.35,
                coords=lambda nt, xyz, X, Y, Z: (Z, math_(nt, 'MULTIPLY', math_(nt, 'ARCTAN2', X, Y), R)))


def dome_coords(nt, xyz, X, Y, Z):
    """Dome boards run in horizontal courses round the dome: along = arc round, across = arc up from the springing."""
    rxy = node(nt, "ShaderNodeVectorMath", operation='LENGTH'); nt.links.new(combine(nt, X, Y, 0.0), rxy.inputs[0])
    el = math_(nt, 'ARCTAN2', math_(nt, 'SUBTRACT', Z, ZD), rxy.outputs["Value"])
    return math_(nt, 'MULTIPLY', math_(nt, 'ARCTAN2', X, Y), R), math_(nt, 'MULTIPLY', el, R)

def dome_paint():
    """Old cream paint on the dome's boards: the courses show through, the paint yellowed and a little smoky toward
    the top, streaks of grime below the slit where rain has come in."""
    m = planks("M_DomePaint", 0.11, 3.2, [(0.52, 0.48, 0.38), (0.55, 0.50, 0.40), (0.50, 0.46, 0.37), (0.54, 0.505, 0.41)],
               (0.20, 0.17, 0.12), rough=0.72, seed=3.0, grain_k=0.12, gap_w=0.04, bumpk=0.3, coords=dome_coords)
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    xyz, X, Y, Z = obj_xyz(nt)
    src = b.inputs["Base Color"].links[0].from_socket
    hi = maprange(nt, Z, ZD + 0.6, ZD + R, 0.0, 0.3)
    st = noise_tex(nt, combine(nt, math_(nt, 'MULTIPLY', X, 6.0), math_(nt, 'MULTIPLY', Y, 6.0), math_(nt, 'MULTIPLY', Z, 0.6)), 3.0, 5.0, 0.6)
    streak = math_(nt, 'MULTIPLY', maprange(nt, st.outputs["Fac"], 0.55, 0.75, 0.0, 0.35), maprange(nt, Z, ZD + 1.6, ZD + 0.2, 0.0, 1.0))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'ADD', hi, streak), src, (0.55, 0.50, 0.42, 1))
    nt.links.new(col, b.inputs["Base Color"])
    return m
M_DOME = dome_paint()
M_RIBS = wood("M_DomeRibs", (0.20, 0.12, 0.06), (0.10, 0.06, 0.03), rough=0.55, along='Z', scale=1.0, seed=1.3, ring=9.0, contrast=0.4)
M_TRIM = wood("M_PineTrim", (0.30, 0.17, 0.075), (0.15, 0.08, 0.035), rough=0.45, along='Z', seed=2.2, ring=9.0, contrast=0.35)
M_DOOR = planks("M_DoorBoards", 0.12, 9.0, [(0.20, 0.11, 0.05), (0.24, 0.135, 0.06), (0.18, 0.10, 0.045)], (0.03, 0.02, 0.012),
                along='Z', rough=0.5, seed=4.0, gap_w=0.05)
M_IRON = metal("M_CastIron", (0.035, 0.040, 0.036), rough=0.48, tarnish=(0.05, 0.045, 0.04), scale=5.0, metallic=0.55)
M_BRASS = metal("M_Brass", (0.72, 0.50, 0.22), rough=0.30, tarnish=(0.42, 0.30, 0.13), scale=6.0)
M_BLACK = metal("M_Ebonite", (0.012, 0.011, 0.010), rough=0.35, metallic=0.0, scale=10.0)
M_MAHOG = wood("M_Mahogany", (0.20, 0.07, 0.035), (0.09, 0.03, 0.015), rough=0.32, along='X', seed=0.7, ring=7.0, contrast=0.45)
M_OAK = wood("M_Oak", (0.36, 0.24, 0.12), (0.20, 0.12, 0.06), rough=0.5, along='Z', seed=3.3, ring=4.0, contrast=0.5)
M_PAPER = paint("M_Paper", (0.50, 0.46, 0.37), rough=0.85, mottle=0.08, scale=6.0, bumpk=0.02)
M_LEATHER = fabric("M_Leather", (0.11, 0.05, 0.03), rough=0.55, sheen=0.15, weave=False, var=0.3)
M_GLASS = glass("M_SiphonGlass", (0.72, 0.86, 0.85), rough=0.03)
M_PEWTER = metal("M_Pewter", (0.42, 0.42, 0.40), rough=0.38, tarnish=(0.25, 0.25, 0.23))
M_TIN = metal("M_Japanned", (0.025, 0.02, 0.016), rough=0.4, metallic=0.3, tarnish=(0.08, 0.06, 0.04), scale=12.0)
M_LENS = plain("M_LanternLens", (1.0, 0.72, 0.38), rough=0.2, emission=(1.0, 0.62, 0.28), strength=6.0)
M_ROPE = fabric("M_Rope", (0.32, 0.25, 0.15), rough=0.95, scale=60.0, sheen=0.0)
M_RUG = fabric("M_Rug", (0.16, 0.06, 0.04), rough=0.95, scale=220.0, var=0.25)
M_STONE = paint("M_PierStone", (0.36, 0.34, 0.30), rough=0.85, mottle=0.2, scale=8.0, bumpk=0.2)

def books_mat(name):
    """Cloth- and leather-bound spines: each book its own colour, gilt bands near head and foot."""
    m, nt, b = new_mat(name)
    xyz, X, Y, Z = obj_xyz(nt)
    cell = combine(nt, math_(nt, 'FLOOR', math_(nt, 'DIVIDE', X, 0.032)), math_(nt, 'FLOOR', math_(nt, 'DIVIDE', Y, 0.032)), math_(nt, 'FLOOR', math_(nt, 'DIVIDE', Z, 0.3)))
    w = white(nt, cell)
    col = tone_ramp(nt, w.outputs["Value"], [(0.09, 0.025, 0.02), (0.05, 0.07, 0.04), (0.14, 0.09, 0.05), (0.04, 0.04, 0.07), (0.12, 0.03, 0.025), (0.17, 0.13, 0.08), (0.06, 0.05, 0.04)])
    zf = math_(nt, 'FRACT', math_(nt, 'DIVIDE', Z, 0.3))
    band = math_(nt, 'MAXIMUM', maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', zf, 0.18)), 0.012, 0.004, 0.0, 1.0),
                 maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', zf, 0.62)), 0.010, 0.003, 0.0, 1.0))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', band, 0.7), col, (0.45, 0.32, 0.12, 1))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.7
    return m
M_BOOKS = books_mat("M_Books")

# ----------------------------------------------------------------------------- the night sky through the slit (numpy)
SKY_R = 14.0
A_HALF = 0.62                       # across the slit, radians each side
E0, E1 = math.radians(-6.0), math.radians(122.0)
MARS_DIR = None                      # set below with the telescope

def sky_dir(a, e):
    return (H * math.cos(e) + UP * math.sin(e)) * math.cos(a) + SIDE * math.sin(a)

def gen_night_sky(W=1024, Hh=2048, seed=7):
    """A midnight sky in August from Surrey: deep blue (the eye's 'oblong profundity'), a faint glow low down, the
    Milky Way streaked across the slit with its dark rifts, a few thousand stars with a natural brightness spread,
    and Mars a small ruddy star. Row 0 = bottom (e = E0)."""
    rs = np.random.RandomState(seed)
    a = (-A_HALF + (np.arange(W) + 0.5) / W * 2 * A_HALF).astype(np.float32)
    e = (E0 + (np.arange(Hh) + 0.5) / Hh * (E1 - E0)).astype(np.float32)
    AA, EE = np.meshgrid(a, e)
    # true elevation of each texel's direction (the slit frame tilts nothing: e is elevation for a = 0)
    elev = np.arcsin(np.clip(np.sin(EE) * np.cos(AA), -1, 1))
    eld = np.degrees(elev)
    zen = np.array([0.0045, 0.0085, 0.030], np.float32)
    hor = np.array([0.020, 0.026, 0.050], np.float32)
    f = np.clip(eld / 35.0, 0, 1) ** 0.6
    col = hor[None, None, :] * (1 - f[..., None]) + zen[None, None, :] * f[..., None]
    # Milky Way: a band crossing the slit diagonally, patchy, with dark lanes (the Cygnus rift)
    band_c = 0.85 + 0.55 * AA                       # its centre line in e (radians), slanting across
    d = (EE - band_c) / 0.16
    patch = K.fbm(AA * 9.0 + 3.0, EE * 9.0, 6, seed=21)
    rift = K.sstep(0.55, 0.72, K.fbm(AA * 14.0 + 7.0, EE * 5.0 + 1.0, 5, seed=33)) * np.exp(-((EE - band_c - 0.02) / 0.05) ** 2)
    mw = np.exp(-d * d) * (0.45 + 0.9 * patch) * (1.0 - 0.75 * rift)
    col += mw[..., None] * np.array([0.020, 0.022, 0.030], np.float32)[None, None, :]
    # unresolved star dust in the band
    dust = (rs.random_sample((Hh, W)) ** 18.0) * np.exp(-d * d) * 0.25
    col += dust[..., None] * np.array([0.9, 0.9, 1.0], np.float32)
    # stars: magnitudes with a natural count law; brighter ones are 2x2 soft points; density x2 in the band
    n = 5200
    sa = rs.uniform(-A_HALF, A_HALF, n); se = rs.uniform(E0, E1, n)
    keep = rs.random_sample(n) < (0.45 + 0.55 * np.exp(-((se - (0.85 + 0.55 * sa)) / 0.2) ** 2))
    sa, se = sa[keep], se[keep]
    mag = 6.5 - 5.0 * (rs.random_sample(len(sa)) ** 2.6)
    flux = 10 ** (-0.4 * (mag - 1.0)) * 0.9
    tint = rs.random_sample(len(sa))
    for x_, y_, fl, t in zip(sa, se, flux, tint):
        px = (x_ + A_HALF) / (2 * A_HALF) * W - 0.5; py = (y_ - E0) / (E1 - E0) * Hh - 0.5
        ix, iy = int(math.floor(px)), int(math.floor(py)); fx, fy = px - ix, py - iy
        c = np.array([1.0, 0.92, 0.78]) if t < 0.18 else np.array([0.80, 0.88, 1.0]) if t > 0.8 else np.array([1.0, 1.0, 1.0])
        sp = 1.0 if fl > 0.4 else 0.0
        for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            X_, Y_ = ix + dx, iy + dy
            if 0 <= X_ < W and 0 <= Y_ < Hh: col[Y_, X_] += c * fl * (0.35 + 0.65 * wgt)
        if sp:
            for dx, dy in ((-1, 0), (2, 0), (0, -1), (0, 2)):
                X_, Y_ = ix + dx, iy + dy
                if 0 <= X_ < W and 0 <= Y_ < Hh: col[Y_, X_] += c * fl * 0.12
    # Mars: low in the slit, a small steady ruddy point
    ma, me = MARS_AE
    px = (ma + A_HALF) / (2 * A_HALF) * W; py = (me - E0) / (E1 - E0) * Hh
    yy, xx = np.mgrid[0:Hh, 0:W]
    col += (np.exp(-(((xx - px) ** 2 + (yy - py) ** 2) / 2.2)))[..., None] * np.array([2.6, 1.15, 0.5], np.float32) * 0.9
    # the dark tops of the pines on the far side of the common, if the slit is seen low enough
    ridge = 0.6 + 2.2 * K.fbm(AA * 30.0, np.zeros_like(AA), 4, seed=5) + 1.6 * K.sstep(0.6, 0.85, K.fbm(AA * 70.0, np.zeros_like(AA) + 3.0, 3, seed=9))
    trees = K.sstep(0.15, -0.15, eld - ridge)
    col = col * (1 - trees[..., None]) + np.array([0.003, 0.004, 0.006], np.float32) * trees[..., None]
    rgba = np.ones((Hh, W, 4), np.float32); rgba[..., :3] = np.clip(col * 0.6, 0, 1)
    return rgba

# ----------------------------------------------------------------------------- the floor
def floor_mesh():
    """Floor boards: an annulus from the pier's isolating gap to the wall."""
    prof = [(0.36, 0.0), (R + 0.02, 0.0)]
    me = bpy.data.meshes.new("Floor"); bm = bmesh.new(); N = 72
    rings = []
    for r in (0.36, 0.9, 1.6, R + 0.02):
        rings.append([bm.verts.new((r * math.cos(TWO_PI * i / N), r * math.sin(TWO_PI * i / N), 0.0)) for i in range(N)])
    for a, b_ in zip(rings, rings[1:]):
        for i in range(N):
            j = (i + 1) % N; bm.faces.new((a[i], b_[i], b_[j], a[j]))
    bm.normal_update()
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Floor", me); me.materials.append(M_FLOOR); K.link(o)
    # the pier's stone cap, a finger's width below the boards, and the boards' edge round it
    lathe("PierCap", [(0.0, -0.012), (0.345, -0.012), (0.345, -0.10)], (0, 0, 0), M_STONE, steps=32)
    lathe("FloorEdge", [(0.36, 0.0), (0.36, -0.025)], (0, 0, 0), M_FLOOR, steps=32, smooth=False)
floor_mesh()

# ----------------------------------------------------------------------------- the drum wall, door, skirting, curb
DOOR_AZ = 214.0
DOOR_W, DOOR_H = 0.80, 1.86
def drum_wall():
    N = 96; dw = DOOR_W / R
    da = math.radians(90.0 - DOOR_AZ)            # compass -> math angle
    ts = sorted(set([TWO_PI * i / N for i in range(N)] + [(da - dw / 2) % TWO_PI, (da + dw / 2) % TWO_PI]))
    def in_door(t):
        d = (t - da + math.pi) % TWO_PI - math.pi; return abs(d) < dw / 2 - 1e-6
    def band(name, zs, mat):
        me = bpy.data.meshes.new(name); bm = bmesh.new()
        grid = [[bm.verts.new((R * math.cos(t), R * math.sin(t), z)) for t in ts] for z in zs]
        for j in range(len(zs) - 1):
            for i in range(len(ts)):
                i2 = (i + 1) % len(ts)
                tm = ts[i] + (((ts[i2] - ts[i]) % TWO_PI) / 2)
                if zs[j + 1] <= DOOR_H + 1e-6 and in_door(tm % TWO_PI): continue
                bm.faces.new((grid[j][i], grid[j][i2], grid[j + 1][i2], grid[j + 1][i]))
        bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); me.materials.append(mat); K.link(o)
        orient(o, lambda c: -Vector((c.x, c.y, 0)))
    band("Wainscot", [0.0, 0.5, DADO], M_WALL)
    band("WallUpper", [DADO, 1.5, DOOR_H, WH], M_WALL)
    lathe("DadoRail", [(R + 0.001, DADO - 0.035), (R - 0.018, DADO - 0.035), (R - 0.026, DADO - 0.01), (R - 0.026, DADO + 0.012), (R - 0.012, DADO + 0.03), (R + 0.001, DADO + 0.03)], (0, 0, 0), M_TRIM, steps=96, sharp=30)
    # door: frame (architraves), the ledged plank door shut in its opening, iron latch and hinges
    fr = Frame(tuple(az_dir(DOOR_AZ) * (R - 0.0)), math.radians(-DOOR_AZ) + math.pi, 0.0)
    for sx in (-1, 1):
        fr.box(f"DoorArch{sx}", (0.075, 0.025, DOOR_H + 0.075), (sx * (DOOR_W / 2 + 0.035), 0.012, (DOOR_H + 0.075) / 2), M_TRIM, bevel=0.006)
        fr.box(f"DoorJamb{sx}", (0.03, 0.12, DOOR_H), (sx * (DOOR_W / 2 - 0.012), -0.05, DOOR_H / 2), M_TRIM)
    fr.box("DoorHead", (DOOR_W + 0.15, 0.03, 0.08), (0, 0.014, DOOR_H + 0.04), M_TRIM, bevel=0.006)
    fr.box("DoorLeaf", (DOOR_W - 0.03, 0.035, DOOR_H - 0.01), (0, -0.07, DOOR_H / 2), M_DOOR)
    for zz in (0.25, 0.95, 1.62):
        fr.box(f"DoorLedge{zz}", (DOOR_W - 0.1, 0.025, 0.15), (0, -0.04, zz), M_DOOR, bevel=0.004)
    for zz in (0.25, 1.62):
        fr.box(f"DoorHinge{zz}", (0.42, 0.006, 0.035), (-DOOR_W / 2 + 0.24, -0.026, zz), M_IRON)
    fr.box("DoorLatchBar", (0.16, 0.012, 0.016), (DOOR_W / 2 - 0.14, -0.02, 1.0), M_IRON)
    fr.cyl("DoorLatchKnob", 0.015, 0.05, (DOOR_W / 2 - 0.2, -0.03, 1.0), M_IRON, verts=8, rot=(math.pi / 2, 0, 0))
    # skirting and the top moulding under the curb
    lathe("Skirting", [(R + 0.001, 0.0), (R - 0.022, 0.0), (R - 0.022, 0.14), (R - 0.012, 0.165), (R + 0.001, 0.17)], (0, 0, 0), M_TRIM, steps=96, sharp=30)
    lathe("WallTop", [(R + 0.001, WH - 0.10), (R - 0.025, WH - 0.10), (R - 0.03, WH - 0.04), (R + 0.001, WH)], (0, 0, 0), M_TRIM, steps=96)
drum_wall()

def cut_door_ring(o):
    """Delete the faces of a ring moulding that cross the door opening (skirting)."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    dd = az_dir(DOOR_AZ)
    kill = [f for f in bm.faces if Vector((f.calc_center_median().x, f.calc_center_median().y, 0)).normalized().dot(dd) > math.cos((DOOR_W / 2 + 0.07) / R) and f.calc_center_median().z < DOOR_H]
    bmesh.ops.delete(bm, geom=kill, context='FACES'); bm.to_mesh(o.data); bm.free()
cut_door_ring(bpy.data.objects["Skirting"]); cut_door_ring(bpy.data.objects["DadoRail"])

# curb (the fixed wall plate), the iron rail, rollers, and the dome's own ring above
lathe("Curb", [(R + 0.12, WH), (R - 0.10, WH), (R - 0.10, WH + CURB_H), (R + 0.12, WH + CURB_H)], (0, 0, 0), M_RIBS, steps=96, closed=True, smooth=True, sharp=30)
lathe("Rail", [(R - 0.035, WH + CURB_H), (R - 0.065, WH + CURB_H), (R - 0.06, WH + CURB_H + 0.03), (R - 0.04, WH + CURB_H + 0.03)], (0, 0, 0), M_IRON, steps=96, closed=True)
lathe("DomeRing", [(R + 0.08, ZD - 0.10), (R - 0.09, ZD - 0.10), (R - 0.09, ZD + 0.02), (R + 0.08, ZD + 0.02)], (0, 0, 0), M_RIBS, steps=96, closed=True, sharp=30)
lathe("RackRing", [(R - 0.09, ZD - 0.10), (R - 0.12, ZD - 0.10), (R - 0.12, ZD - 0.13), (R - 0.09, ZD - 0.13)], (0, 0, 0), M_IRON, steps=96, closed=True)
for k in range(10):
    t = TWO_PI * (k + 0.5) / 10
    p = Vector((math.cos(t), math.sin(t), 0)) * (R - 0.05)
    cyl(f"Roller{k}", 0.045, 0.035, (p.x, p.y, WH + CURB_H + 0.075), M_IRON, verts=12, rot=(math.pi / 2, 0, t + math.pi / 2))
    cyl(f"RollerAxle{k}", 0.012, 0.09, (p.x, p.y, WH + CURB_H + 0.075), M_IRON, verts=6, rot=(math.pi / 2, 0, t + math.pi / 2))

# ----------------------------------------------------------------------------- the dome: shell with the slit, jambs, girders, ribs
def dome_shell():
    nx_side, nphi = 14, 48
    th0 = math.asin(HW / R)
    xs_side = [R * math.sin(th0 + (math.radians(88.5) - th0) * k / nx_side) for k in range(nx_side + 1)]
    xs = sorted(set([-x for x in xs_side] + xs_side + [-HW / 2, 0.0, HW / 2]))
    phis = [math.pi * j / nphi for j in range(nphi + 1)]
    me = bpy.data.meshes.new("Dome"); bm = bmesh.new()
    V = [[bm.verts.new(dome_pt(x, p)) for x in xs] for p in phis]
    for j in range(nphi):
        for i in range(len(xs) - 1):
            xm = (xs[i] + xs[i + 1]) / 2; pm = (phis[j] + phis[j + 1]) / 2
            if abs(xm) < HW - 1e-6 and PHI0 < pm < PHI1: continue
            bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
    for f in bm.faces: f.smooth = True
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Dome", me); me.materials.append(M_DOME); K.link(o)
    orient(o, lambda c: DC - c)
    # the slit's jambs, sill and head: the thickness of the dome skin, boarded
    n = 28
    for sx in (-1, 1):
        pts_in = [dome_pt(sx * HW, PHI0 + (PHI1 - PHI0) * k / n) for k in range(n + 1)]
        pts_out = [dome_pt(sx * HW, PHI0 + (PHI1 - PHI0) * k / n, RO) for k in range(n + 1)]
        vs = pts_in + pts_out
        faces = [(k, k + 1, n + 1 + k + 1, n + 1 + k) for k in range(n)]
        jo = mesh_from(f"SlitJamb{sx}", vs, faces, M_TRIM)
        orient(jo, lambda c, sx=sx: -SIDE * sx)
    for nm, ph in (("SlitSill", PHI0), ("SlitHead", PHI1)):
        vs = [dome_pt(-HW, ph), dome_pt(HW, ph), dome_pt(HW, ph, RO), dome_pt(-HW, ph, RO)]
        so = mesh_from(nm, vs, [(0, 1, 2, 3)], M_TRIM)
        mid = dome_pt(0, (PHI0 + PHI1) / 2)
        orient(so, lambda c, mid=mid: mid - c)
dome_shell()

def inward(p): return (DC - Vector(p)).normalized()
# the two arched girders that flank the slit, from springing to springing
GW = 0.09
for sx in (-1, 1):
    x = sx * (HW + GW / 2)
    pts = [dome_pt(x, math.pi * k / 40) for k in range(41)]
    sweep_rect(f"Girder{sx}", pts, [inward(p) for p in pts], GW, 0.13, M_RIBS)
# meridian ribs, each stopping at a girder
for k in range(16):
    az = SLIT_AZ + 11.25 + 22.5 * k
    dvec = az_dir(az); lat = dvec.dot(SIDE)
    if abs(lat) * R < HW + GW + 0.05: continue
    tmax = math.acos(min(1.0, (HW + GW) / (abs(lat) * R)))
    pts = [DC + (dvec * math.cos(t) + UP * math.sin(t)) * R for t in [tmax * i / 20 for i in range(21)]]
    sweep_rect(f"Rib{k}", pts, [inward(p) for p in pts], 0.06, 0.08, M_RIBS)
# a purlin ring half way up (stops at the girders)
def ring_arc(name, el, w, d, mat):
    pts_all = []
    for sx in (-1, 1):
        rr = R * math.cos(el)
        pts = []
        for i in range(73):
            t = TWO_PI * i / 72
            p = DC + Vector((math.cos(t) * rr, math.sin(t) * rr, R * math.sin(el)))
            pts.append(p)
        seg = []
        for p in pts:
            if abs((p - DC).dot(SIDE)) > HW + GW and ((p - DC).dot(SIDE) * sx > 0):
                seg.append(p)
        if len(seg) > 2: sweep_rect(f"{name}{sx}", seg, [inward(p) for p in seg], w, d, mat)
ring_arc("Purlin", math.radians(38), 0.06, 0.07, M_RIBS)

# the shutter's track and the rope wheel that turns the dome (the rope hangs down the drum by the slit)
for sx in (-1, 1):
    pts = [dome_pt(sx * (HW + GW + 0.02), PHI0 + (PHI1 - PHI0) * k / 24, R - 0.13) for k in range(25)]
    tube(f"ShutterRod{sx}", pts, 0.008, M_IRON, sides=6)
wheel_c = DC + H * (R - 0.62) - SIDE * (HW + 1.15) - UP * 0.12
torus("RopeWheel", 0.20, 0.018, tuple(wheel_c), M_IRON, rot=(math.pi / 2, 0, math.atan2(H.y, H.x) + math.pi / 2), seg=24, rseg=6)
for k in range(4):
    t = math.pi * k / 4
    dvec = (UP * math.cos(t) + SIDE * math.sin(t))
    tube(f"WheelSpoke{k}", [tuple(wheel_c - dvec * 0.2), tuple(wheel_c + dvec * 0.2)], 0.008, M_IRON, sides=6)
for side in (-1, 1):
    side_v = H.cross(UP).normalized()  # horizontal, along the wall
    start = wheel_c + side_v * (0.2 * side)
    end = Vector((start.x, start.y, 0.55 + (0.12 if side > 0 else 0.0)))
    pts = [start + (end - start) * (i / 10) + Vector((0.01 * math.sin(i), 0.008 * math.cos(i * 1.3), 0)) for i in range(11)]
    tube(f"DomeRope{side}", pts, 0.009, M_ROPE, sides=6)

# ----------------------------------------------------------------------------- the telescope
PIER_TOP = 1.16
pier = lathe("Pier", [(0.0, 0.0), (0.30, 0.0), (0.30, 0.04), (0.25, 0.06), (0.20, 0.12), (0.155, 0.22), (0.14, 0.30), (0.13, 0.32),
                      (0.12, 1.02), (0.13, 1.06), (0.17, 1.10), (0.18, PIER_TOP - 0.02), (0.17, PIER_TOP), (0.0, PIER_TOP)],
             (0, 0, 0), M_IRON, steps=28, sharp=35)
for k in range(8):
    t = TWO_PI * k / 8
    cyl(f"PierBolt{k}", 0.018, 0.03, (math.cos(t) * 0.26, math.sin(t) * 0.26, 0.055), M_IRON, verts=6)
P = Vector((0, math.cos(LAT), math.sin(LAT)))                            # polar axis (points at the pole, due north)
PT = Vector((0, 0, PIER_TOP + 0.05))
MARS_EL = math.radians(24.0)
D = (H * math.cos(MARS_EL) + UP * math.sin(MARS_EL)).normalized()        # the tube points at Mars, low in the slit
A = P.cross(D).normalized()
if A.z < 0: A = -A                                                      # tube above the axis, counterweight hanging below
def along(name, prof, base, axis, mat, steps=20, smooth=True, sharp=40):
    rot = Vector((0, 0, 1)).rotation_difference(axis).to_matrix()
    return lathe(name, prof, tuple(base), mat, steps=steps, rot=rot, smooth=smooth, sharp=sharp)

# the head casting on the pier, the polar axis housing, the right-ascension wheel and hour circle
box("MountHead", (0.22, 0.30, 0.10), (0, 0.02, PIER_TOP + 0.04), M_IRON, bevel=0.015, rot=(LAT * 0.5, 0, 0))
along("PolarAxis", [(0.0, -0.20), (0.065, -0.20), (0.065, 0.32), (0.05, 0.34), (0.0, 0.34)], PT, P, M_IRON, steps=20)
RAW = PT - P * 0.13
along("RAWheel", [(0.0, -0.012), (0.175, -0.012), (0.175, 0.012), (0.0, 0.012)], RAW, P, M_BRASS, steps=48)
along("RAWheelTeeth", [(0.172, -0.010), (0.184, -0.007), (0.184, 0.007), (0.172, 0.010)], RAW, P, M_BRASS, steps=96, smooth=False)
along("HourCircle", [(0.0, -0.008), (0.12, -0.008), (0.12, 0.008), (0.0, 0.008)], PT + P * 0.04, P, M_BRASS, steps=40)
HEAD = PT + P * 0.36
along("DecAxis", [(0.0, -0.18), (0.052, -0.18), (0.052, 0.20), (0.0, 0.20)], HEAD, A, M_IRON, steps=18)
along("DecCircle", [(0.0, -0.007), (0.10, -0.007), (0.10, 0.007), (0.0, 0.007)], HEAD + A * 0.13, A, M_BRASS, steps=36)
along("CounterShaft", [(0.0, -0.62), (0.018, -0.62), (0.018, -0.15), (0.0, -0.15)], HEAD, A, M_IRON, steps=10)
along("CounterWeight", [(0.0, -0.10), (0.03, -0.10), (0.075, -0.09), (0.08, -0.07), (0.08, 0.05), (0.075, 0.07), (0.03, 0.08), (0.0, 0.08)], HEAD - A * 0.48, A, M_IRON, steps=20)
TC = HEAD + A * 0.27                                                       # the tube's balance point
along("Cradle", [(0.0, -0.01), (0.12, -0.01), (0.12, 0.01), (0.0, 0.01)], HEAD + A * 0.205, A, M_IRON, steps=16)
for s in (-0.22, 0.22):
    along(f"TubeRing{s}", [(0.079, -0.022), (0.097, -0.022), (0.097, 0.022), (0.079, 0.022)], TC + D * s, D, M_IRON, steps=24, smooth=True)
    tube(f"RingStem{s}", [tuple(HEAD + A * 0.2 + D * s), tuple(TC + D * s - A * 0.09)], 0.018, M_IRON, sides=8)
L_TUBE = 2.30
EYE_END = TC - D * 0.90
along("Tube", [(r * 0.9, z * 0.84) for r, z in [(0.0, -0.205), (0.0075, -0.205), (0.0075, -0.16), (0.0135, -0.155), (0.0135, -0.12), (0.022, -0.12), (0.022, 0.0),
               (0.034, 0.0), (0.034, 0.075), (0.040, 0.08), (0.089, 0.15), (0.089, 0.17), (0.084, 0.18),
               (0.084, 0.80), (0.090, 0.81), (0.090, 0.84), (0.084, 0.85), (0.084, 1.55), (0.090, 1.56), (0.090, 1.59), (0.084, 1.60),
               (0.084, 2.04), (0.096, 2.05), (0.096, 2.12), (0.100, 2.13), (0.100, 2.42), (0.094, 2.42), (0.094, 2.16), (0.0, 2.16)]],
      EYE_END, D, M_BRASS, steps=28, sharp=50)
along("Eyepiece", [(0.0, -0.215), (0.012, -0.215), (0.014, -0.205), (0.014, -0.17), (0.0, -0.17)], EYE_END, D, M_BLACK, steps=16)
along("ObjectiveDark", [(0.0, 1.81), (0.084, 1.81), (0.0, 1.811)], EYE_END, D, M_BLACK, steps=24)
# focusing pinion knobs
PERP = D.cross(A).normalized()
for s in (-1, 1):
    tube(f"FocusKnob{s}", [tuple(EYE_END + D * 0.03 + A * 0.03 * s), tuple(EYE_END + D * 0.03 + A * 0.075 * s)], 0.012, M_BRASS, sides=10)
# finder telescope on two brackets
FB = EYE_END + D * 0.30 + PERP * 0.125
along("Finder", [(0.0, 0.0), (0.008, 0.0), (0.008, 0.03), (0.016, 0.04), (0.016, 0.50), (0.022, 0.51), (0.022, 0.58), (0.0, 0.58)], FB, D, M_BRASS, steps=14)
for s in (0.12, 0.42):
    tube(f"FinderBracket{s}", [tuple(EYE_END + D * (0.30 + s) + PERP * 0.076), tuple(FB + D * s - PERP * 0.016)], 0.01, M_BRASS, sides=6)

# the clock drive: a cast-iron case on the pier, the governor's balls on top, a driving weight on a cord, and the
# drive rod up to the worm on the right-ascension wheel
CLK = Vector((0.0, -0.21, PIER_TOP - 0.36))
box("ClockCase", (0.20, 0.13, 0.24), tuple(CLK), M_IRON, bevel=0.01)
box("ClockDoor", (0.16, 0.005, 0.19), tuple(CLK + Vector((0, -0.067, 0))), M_BRASS, bevel=0.003)
box("ClockBracket", (0.08, 0.10, 0.05), tuple(CLK + Vector((0, 0.10, 0.06))), M_IRON, bevel=0.006)
cyl("GovSpindle", 0.006, 0.16, tuple(CLK + Vector((0.04, 0, 0.20))), M_BRASS, verts=6)
cyl("GovCollar", 0.016, 0.02, tuple(CLK + Vector((0.04, 0, 0.18))), M_BRASS, verts=10)
for s in (-1, 1):
    top = CLK + Vector((0.04, 0, 0.27)); ball = top + Vector((s * 0.07, 0, -0.06))
    tube(f"GovArm{s}", [tuple(top), tuple(ball)], 0.003, M_BRASS, sides=5)
    sphere(f"GovBall{s}", 0.02, tuple(ball), M_BRASS, seg=12)
cyl("GovCap", 0.01, 0.015, tuple(CLK + Vector((0.04, 0, 0.28))), M_BRASS, verts=8)
worm = RAW + Vector((0, -0.16, -0.02))
tube("DriveRod", [tuple(CLK + Vector((-0.05, 0, 0.12))), tuple(CLK + Vector((-0.05, 0, 0.22))), tuple(worm + Vector((-0.05, 0, 0)))], 0.006, M_BRASS, sides=6)
cyl("Worm", 0.018, 0.07, tuple(worm), M_BRASS, verts=10, rot=(0, math.pi / 2, 0))
tube("WeightCord", [tuple(CLK + Vector((0.05, -0.02, -0.12))), tuple(CLK + Vector((0.05, -0.02, -0.55)))], 0.0025, M_ROPE, sides=4, cap=False)
cyl("DriveWeight", 0.035, 0.16, tuple(CLK + Vector((0.05, -0.02, -0.64))), M_IRON, verts=12)

# ----------------------------------------------------------------------------- the observing chair (by the eyepiece)
def observing_chair(origin, yaw):
    f = Frame(origin, yaw)
    for sx in (-1, 1):
        x = sx * 0.21
        tube(f"ChairStile{sx}", [f.p(x, 0.0, 0.0), f.p(x, -0.42, 1.62)], 0.022, M_OAK, sides=6)
        tube(f"ChairProp{sx}", [f.p(x * 1.15, -0.85, 0.0), f.p(x, -0.36, 1.40)], 0.018, M_OAK, sides=6)
        for k in range(9):
            z = 0.32 + k * 0.13; y = -0.42 * z / 1.62
            f.box(f"ChairNotch{sx}{k}", (0.03, 0.03, 0.012), (x - sx * 0.022, y + 0.015, z), M_OAK)
    for z in (0.12, 1.55):
        y = -0.42 * z / 1.62
        tube(f"ChairRung{z}", [f.p(-0.21, y, z), f.p(0.21, y, z)], 0.014, M_OAK, sides=6)
    tube("ChairStretch", [f.p(-0.24, -0.85, 0.10), f.p(0.24, -0.85, 0.10)], 0.013, M_OAK, sides=6)
    zs = 0.62; ys = -0.42 * zs / 1.62
    f.box("ChairSeat", (0.40, 0.30, 0.03), (0, ys + 0.13, zs), M_OAK, bevel=0.008)
    f.box("ChairSeatPad", (0.36, 0.26, 0.025), (0, ys + 0.13, zs + 0.026), M_LEATHER, bevel=0.01, seg=2)
    for sx in (-1, 1):
        tube(f"ChairSeatBrace{sx}", [f.p(sx * 0.19, ys + 0.25, zs - 0.01), f.p(sx * 0.19, ys + 0.03, zs - 0.18)], 0.01, M_IRON, sides=5)
observing_chair(tuple(EYE_END + PERP * 0.0 - A * 0.0 + (Vector((EYE_END.x, EYE_END.y, 0)) - Vector((0, 0, 0))).normalized() * 0.35)[:2],
                math.atan2(-(EYE_END.x), (EYE_END.y)) + math.pi)

# ----------------------------------------------------------------------------- the lantern in the corner (north-east)
LANT_AZ = 150.0
LANT = az_dir(LANT_AZ) * (R - 0.32)
LANT_YAW = math.radians(-(LANT_AZ + 180.0 + 0.0))           # its bull's-eye faces along the wall, into the corner's floor
def lantern():
    f = Frame((LANT.x, LANT.y), LANT_YAW)
    f.lathe("LanternBody", [(0.0, 0.0), (0.072, 0.0), (0.075, 0.01), (0.075, 0.19), (0.07, 0.20), (0.05, 0.215), (0.04, 0.24), (0.0, 0.24)], (0, 0, 0), M_TIN, steps=20)
    f.lathe("LanternChimney", [(0.0, 0.235), (0.028, 0.235), (0.028, 0.30), (0.04, 0.31), (0.04, 0.325), (0.0, 0.33)], (0, 0, 0), M_TIN, steps=14)
    # the bull's-eye: a brass rim and the glowing lens on the front (+y), the shutter half across it
    rot = Matrix.Rotation(LANT_YAW, 3, 'Z') @ Matrix.Rotation(-math.pi / 2, 3, 'X')
    lathe("LanternRim", [(0.044, 0.0), (0.052, 0.0), (0.052, 0.025), (0.044, 0.025)], f.p(0, 0.068, 0.11), M_BRASS, steps=20, rot=rot, closed=True)
    lathe("LanternLens", [(0.0, 0.032), (0.03, 0.026), (0.045, 0.012), (0.045, 0.0)], f.p(0, 0.068, 0.11), M_LENS, steps=20, rot=rot)
    sh = f.lathe("LanternShutter", [(0.078, 0.0), (0.081, 0.0), (0.081, 0.16), (0.078, 0.16)], (0, 0, 0.03), M_TIN, steps=20, closed=True)
    bm = bmesh.new(); bm.from_mesh(sh.data)
    kill = [v for v in bm.verts if (Vector(v.co) - Vector(f.p(0, 0, 0))).normalized().dot(Matrix.Rotation(LANT_YAW, 3, 'Z') @ Vector((-0.6, 1, 0)).normalized()) > 0.55
            or (Vector(v.co) - Vector(f.p(0, 0, 0))).normalized().dot(Matrix.Rotation(LANT_YAW, 3, 'Z') @ Vector((0, -1, 0))) > 0.2]
    bmesh.ops.delete(bm, geom=kill, context='VERTS'); bm.to_mesh(sh.data); bm.free()
    tube("LanternHandle", [f.p(-0.06, 0, 0.17), f.p(-0.07, 0, 0.30), f.p(0, 0, 0.36), f.p(0.07, 0, 0.30), f.p(0.06, 0, 0.17)], 0.005, M_TIN, sides=5)
    for k in range(6):
        t = TWO_PI * k / 6
        f.box(f"LanternVent{k}", (0.012, 0.004, 0.02), (0.045 * math.cos(t), 0.045 * math.sin(t), 0.225), M_LENS)
    return f
LF = lantern()
LAMP_FLAME = Vector(LF.p(0, 0.0, 0.11))
K.marker("fx.lantern.0", tuple(LAMP_FLAME), size=0.03)

# ----------------------------------------------------------------------------- the little table with the siphon (north)
TAB_AZ = 2.0
TAB = az_dir(TAB_AZ) * (R - 0.48)
def siphon_table():
    f = Frame((TAB.x, TAB.y), math.radians(-TAB_AZ))
    f.lathe("TableTop", [(0.0, 0.70), (0.27, 0.70), (0.285, 0.69), (0.285, 0.675), (0.27, 0.668), (0.0, 0.668)], (0, 0, 0), M_MAHOG, steps=40, sharp=30)
    f.lathe("TableColumn", [(0.0, 0.15), (0.05, 0.15), (0.055, 0.19), (0.035, 0.24), (0.03, 0.40), (0.045, 0.46), (0.03, 0.52), (0.026, 0.62), (0.04, 0.655), (0.06, 0.668), (0.0, 0.668)],
            (0, 0, 0), M_MAHOG, steps=16)
    for k in range(3):
        t = TWO_PI * k / 3 + 0.3
        d = Vector((math.cos(t), math.sin(t), 0))
        pts = [Vector(f.p(0, 0, 0)) + d * (0.04 + 0.26 * u) + Vector((0, 0, 0.17 - 0.16 * (u ** 0.6))) for u in [i / 6 for i in range(7)]]
        tube(f"TableFoot{k}", [tuple(p) for p in pts], [0.022 - 0.008 * i / 6 for i in range(7)], M_MAHOG, sides=6)
    # the siphon: a tall glass body with a pewter head, lever and spout
    sx, sy = 0.06, -0.02
    f.lathe("SiphonGlass", [(0.0, 0.70), (0.042, 0.70), (0.046, 0.71), (0.046, 0.90), (0.040, 0.93), (0.024, 0.955), (0.02, 0.97), (0.0, 0.97)], (sx, sy, 0), M_GLASS, steps=20)
    f.lathe("SiphonHead", [(0.0, 0.965), (0.026, 0.965), (0.028, 0.985), (0.022, 1.03), (0.016, 1.05), (0.0, 1.055)], (sx, sy, 0), M_PEWTER, steps=16)
    tube("SiphonSpout", [f.p(sx, sy - 0.015, 1.03), f.p(sx, sy - 0.06, 1.025), f.p(sx, sy - 0.075, 1.005)], 0.006, M_PEWTER, sides=6)
    tube("SiphonLever", [f.p(sx, sy + 0.012, 1.05), f.p(sx, sy + 0.04, 1.06), f.p(sx, sy + 0.07, 1.04)], 0.005, M_PEWTER, sides=5)
    tube("SiphonTube", [f.p(sx, sy, 0.705), f.p(sx, sy, 0.97)], 0.003, M_PEWTER, sides=4)
    for k, (gx, gy) in enumerate(((-0.10, -0.07), (-0.04, 0.12))):
        f.lathe(f"Tumbler{k}", [(0.0, 0.70), (0.030, 0.70), (0.034, 0.79), (0.031, 0.79), (0.027, 0.706), (0.0, 0.706)], (gx, gy, 0), M_GLASS, steps=16)
    return f
siphon_table()
SIPHON = Vector(Frame((TAB.x, TAB.y), math.radians(-TAB_AZ)).p(0.06, -0.02, 0.85))

# ----------------------------------------------------------------------------- the writing desk (west) and its chair, the book shelf
DESK_AZ = 268.0
def desk():
    pos = az_dir(DESK_AZ) * (R - 0.36)
    f = Frame((pos.x, pos.y), math.radians(-DESK_AZ) + math.pi)     # +y faces into the room, back to the wall
    f.box("DeskTop", (1.05, 0.55, 0.03), (0, 0, 0.75), M_MAHOG, bevel=0.008)
    for sx in (-1, 1):
        f.box(f"DeskPed{sx}", (0.34, 0.50, 0.70), (sx * 0.34, 0.0, 0.37), M_MAHOG, bevel=0.006)
        for k in range(3):
            z = 0.62 - k * 0.21
            f.box(f"DeskDrawer{sx}{k}", (0.30, 0.012, 0.17), (sx * 0.34, 0.252, z), M_MAHOG, bevel=0.004)
            f.cyl(f"DeskKnob{sx}{k}", 0.011, 0.02, (sx * 0.34, 0.265, z), M_BRASS, verts=8, rot=(math.pi / 2, 0, 0))
        f.box(f"DeskPlinth{sx}", (0.35, 0.51, 0.04), (sx * 0.34, 0.0, 0.02), M_MAHOG)
    f.box("DeskBackRail", (1.05, 0.03, 0.10), (0, -0.26, 0.815), M_MAHOG, bevel=0.005)
    f.box("DeskLeather", (0.80, 0.40, 0.003), (0, 0.02, 0.766), M_LEATHER)
    # the observing book open, a star atlas shut, the inkstand and pen, a candlestick (unlit, the lantern lights)
    f.box("BookOpenL", (0.21, 0.29, 0.012), (-0.11, 0.05, 0.773), M_PAPER, rot=(0, -0.04, 0))
    f.box("BookOpenR", (0.21, 0.29, 0.012), (0.11, 0.05, 0.773), M_PAPER, rot=(0, 0.04, 0))
    f.box("BookCover", (0.44, 0.30, 0.006), (0, 0.05, 0.768), M_LEATHER)
    f.box("Atlas", (0.36, 0.48, 0.04), (0.33, -0.02, 0.787), M_LEATHER, bevel=0.004, rot=(0, 0, 0.12))
    f.box("AtlasPages", (0.35, 0.47, 0.034), (0.333, -0.016, 0.787), M_PAPER, rot=(0, 0, 0.12))
    f.box("InkStand", (0.22, 0.12, 0.025), (-0.33, -0.12, 0.778), M_MAHOG, bevel=0.004)
    for k in (-1, 1):
        f.lathe(f"InkPot{k}", [(0.0, 0.79), (0.025, 0.79), (0.025, 0.83), (0.012, 0.84), (0.0, 0.845)], (-0.33 + k * 0.05, -0.12, 0), M_GLASS, steps=10)
    tube("Pen", [f.p(-0.25, 0.05, 0.772), f.p(-0.08, 0.16, 0.772)], 0.004, M_BLACK, sides=5)
    f.lathe("Candlestick", [(0.0, 0.765), (0.05, 0.765), (0.05, 0.775), (0.015, 0.79), (0.012, 0.93), (0.022, 0.94), (0.0, 0.945)], (-0.40, 0.12, 0), M_BRASS, steps=12)
    f.cyl("CandleStub", 0.011, 0.06, (-0.40, 0.12, 0.975), M_PAPER, verts=8)
    # the desk chair, pushed in a little askew
    c = Frame(f.p(0.05, 0.62, 0), math.radians(-DESK_AZ) + math.pi + 0.25)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c.box(f"DChairLeg{sx}{sy}", (0.035, 0.035, 0.45), (sx * 0.19, sy * 0.18, 0.225), M_MAHOG)
        c.box(f"DChairBack{sx}", (0.035, 0.03, 0.48), (sx * 0.19, 0.19, 0.69), M_MAHOG)
    c.box("DChairSeat", (0.44, 0.42, 0.04), (0, 0, 0.46), M_MAHOG, bevel=0.01)
    c.box("DChairPad", (0.40, 0.38, 0.03), (0, 0, 0.49), M_LEATHER, bevel=0.012, seg=2)
    for z in (0.78, 0.62):
        c.box(f"DChairRail{z}", (0.40, 0.025, 0.06 if z > 0.7 else 0.035), (0, 0.19, z), M_MAHOG, bevel=0.005)
    # a worn rug under the chair
    f.box("Rug", (1.2, 0.85, 0.006), (0, 0.55, 0.003), M_RUG)
desk()

def shelves():
    pos = az_dir(300.0) * (R - 0.16)
    f = Frame((pos.x, pos.y), math.radians(-300.0) + math.pi)
    for k, z in enumerate((0.95, 1.33, 1.70)):
        f.box(f"Shelf{k}", (0.78, 0.22, 0.022), (0, 0.0, z), M_TRIM, bevel=0.004)
        x = -0.36
        rb = random.Random(30 + k)
        while x < 0.33:
            w = rb.uniform(0.022, 0.05); hgt = rb.uniform(0.19, 0.27) if k < 2 else rb.uniform(0.16, 0.22)
            lean = 0.0 if rb.random() > 0.12 else rb.uniform(0.08, 0.2)
            if rb.random() < 0.08: x += 0.06; continue
            f.box(f"Book{k}_{x:.3f}", (w, rb.uniform(0.15, 0.2), hgt), (x + w / 2, -0.01, z + 0.011 + hgt / 2), M_BOOKS, rot=(0, lean, 0))
            x += w + 0.002
    for sx in (-1, 1):
        f.box(f"ShelfBracket{sx}", (0.02, 0.20, 0.85), (sx * 0.38, 0.0, 1.33), M_TRIM)
    # a brass spectroscope case and a chronometer box on the top shelf
    f.box("InstrumentCase", (0.26, 0.15, 0.12), (0.18, 0.0, 1.78), M_MAHOG, bevel=0.006)
shelves()


# ----------------------------------------------------------------------------- the wall furniture: star chart, sidereal clock, chest, stool
def star_chart_img(W=512, Hh=384, seed=11):
    """A printed star map pinned above the desk: cream paper foxed at the edges, black stars by magnitude, the
    constellation lines faint, a ruled border and a grid of right ascension and declination."""
    rs = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:Hh, 0:W].astype(np.float32)
    u, v = xx / W, yy / Hh
    paper = np.array([0.26, 0.235, 0.17], np.float32)
    fox = K.fbm(u * 6, v * 6, 5, seed=3)
    edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    col = paper[None, None, :] * (0.92 + 0.12 * fox[..., None]) * (1 - 0.35 * K.sstep(0.06, 0.0, edge)[..., None])
    ink = np.zeros((Hh, W), np.float32)
    for k in range(1, 12): ink = np.maximum(ink, (np.abs(u - k / 12) < 0.0012).astype(np.float32) * 0.35 * ((edge > 0.05)))
    for k in range(1, 8): ink = np.maximum(ink, (np.abs(v - k / 8) < 0.0016).astype(np.float32) * 0.35 * ((edge > 0.05)))
    ink = np.maximum(ink, ((np.abs(edge - 0.05) < 0.002)).astype(np.float32))
    ink = np.maximum(ink, ((np.abs(edge - 0.04) < 0.0012)).astype(np.float32) * 0.8)
    pts = rs.uniform(0.07, 0.93, (260, 2)); mags = rs.uniform(0.3, 1.0, 260) ** 3
    for (px, py), m in zip(pts, mags):
        r = 1.0 + 3.5 * m
        d2 = (xx - px * W) ** 2 + (yy - py * Hh) ** 2
        ink = np.maximum(ink, np.clip(r - np.sqrt(d2), 0, 1))
    for i in range(0, 40, 4):
        a, b_ = pts[i], pts[i + 1]
        t = np.clip(((xx / W - a[0]) * (b_[0] - a[0]) + (yy / Hh - a[1]) * (b_[1] - a[1])) / max(1e-6, (b_[0] - a[0]) ** 2 + (b_[1] - a[1]) ** 2), 0, 1)
        dd = np.hypot(xx / W - (a[0] + t * (b_[0] - a[0])), yy / Hh - (a[1] + t * (b_[1] - a[1])))
        ink = np.maximum(ink, (dd < 0.0015).astype(np.float32) * 0.4)
    col = col * (1 - 0.88 * ink[..., None])
    rgba = np.ones((Hh, W, 4), np.float32); rgba[..., :3] = col
    return rgba
M_CHART = K.card_material("M_StarChart", K.image_from("T_StarChart", star_chart_img()), rough=0.85, clip=False)
def wall_items():
    # the chart above the desk
    pos = az_dir(DESK_AZ) * (R - 0.012)
    f = Frame((pos.x, pos.y), math.radians(-DESK_AZ) + math.pi)
    w, h = 0.62, 0.465
    vs = [f.p(-w / 2, 0, 1.30), f.p(w / 2, 0, 1.30), f.p(w / 2, 0, 1.30 + h), f.p(-w / 2, 0, 1.30 + h)]
    mesh_from("StarChart", vs, [(0, 1, 2, 3)], M_CHART, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    K.KEEP_UV.add("M_StarChart")
    for sx in (-1, 1):
        for zz in (1.30 + 0.02, 1.30 + h - 0.02):
            f.cyl(f"ChartPin{sx}{zz}", 0.005, 0.006, (sx * (w / 2 - 0.02), 0.004, zz), M_BRASS, verts=6, rot=(math.pi / 2, 0, 0))
    # the sidereal clock: a long-case regulator on the wall to the north-west of the desk
    pos = az_dir(242.0) * (R - 0.11)
    c = Frame((pos.x, pos.y), math.radians(-242.0) + math.pi)
    c.box("RegCase", (0.36, 0.18, 1.18), (0, 0, 0.98 + 0.59), M_MAHOG, bevel=0.01)
    c.box("RegHood", (0.42, 0.21, 0.08), (0, 0, 2.20), M_MAHOG, bevel=0.012)
    c.box("RegPlinth", (0.40, 0.20, 0.06), (0, 0, 0.95), M_MAHOG, bevel=0.01)
    c.box("RegBack", (0.26, 0.004, 0.74), (0, 0.091, 1.45), M_BLACK)
    for sx in (-1, 1): c.box(f"RegDoorStile{sx}", (0.04, 0.02, 0.84), (sx * 0.15, 0.10, 1.45), M_MAHOG, bevel=0.004)
    for zz in (1.05, 1.85): c.box(f"RegDoorRail{zz}", (0.34, 0.02, 0.04), (0, 0.10, zz), M_MAHOG, bevel=0.004)
    c.lathe("RegDial", [(0.0, 0.0), (0.12, 0.0), (0.125, 0.005), (0.0, 0.006)], (0, 0.0, 0), M_CHART, steps=24)
    bpy.data.objects["RegDial"].rotation_euler = (math.pi / 2, 0, math.radians(-242.0) + math.pi)
    bpy.data.objects["RegDial"].location = c.p(0, 0.093, 1.95)
    tube("RegRod", [c.p(0, 0.10, 1.82), c.p(0, 0.10, 1.20)], 0.004, M_BRASS, sides=5)
    c.cyl("RegBob", 0.06, 0.025, (0, 0.105, 1.18), M_BRASS, verts=20, rot=(math.pi / 2, 0, 0))
    for k in range(2): c.cyl(f"RegWeight{k}", 0.022, 0.2, (-0.08 + 0.16 * k, 0.11, 1.62 - 0.12 * k), M_BRASS, verts=12)
    # a deal chest by the lantern, a box of eyepieces on it; a little step-stool by the pier
    pos = az_dir(176.0) * (R - 0.30)
    ch = Frame((pos.x, pos.y), math.radians(-176.0) + math.pi)
    ch.box("Chest", (0.80, 0.42, 0.44), (0, 0, 0.22), M_OAK, bevel=0.01)
    ch.box("ChestLid", (0.83, 0.45, 0.04), (0, 0, 0.46), M_OAK, bevel=0.01)
    for sx in (-1, 1):
        ch.box(f"ChestStrap{sx}", (0.04, 0.455, 0.45), (sx * 0.27, 0, 0.235), M_IRON)
        ch.box(f"ChestHandle{sx}", (0.012, 0.12, 0.03), (sx * 0.41, 0, 0.33), M_IRON)
    ch.box("EyepieceBox", (0.22, 0.14, 0.07), (0.15, 0.03, 0.515), M_MAHOG, bevel=0.006)
    for k in range(3): ch.cyl(f"Eyepiece{k}", 0.014, 0.05, (0.08 + 0.05 * k, 0.04, 0.565), M_BRASS, verts=10)
    ch.box("Notebook", (0.17, 0.23, 0.02), (-0.18, 0.0, 0.49), M_LEATHER, rot=(0, 0, 0.2))
    st = Frame((-0.62, 0.55), 0.6)
    st.box("StoolTop", (0.36, 0.26, 0.03), (0, 0, 0.32), M_OAK, bevel=0.006)
    for sx in (-1, 1): st.box(f"StoolSide{sx}", (0.03, 0.24, 0.305), (sx * 0.15, 0, 0.152), M_OAK)
    st.box("StoolRail", (0.28, 0.02, 0.05), (0, -0.1, 0.24), M_OAK)
wall_items()

# ----------------------------------------------------------------------------- the sky patch beyond the slit
MARS_AE = (0.0 + 0.012, MARS_EL + 0.02)
SKY_IMG = K.image_from("T_NightSky", gen_night_sky())
M_SKY = K.card_material("M_NightSky", SKY_IMG, rough=1.0, clip=False, emissive=True)
def sky_patch():
    nu, nv = 16, 48
    def fn(u, v):
        a = -A_HALF + 2 * A_HALF * u; e = E0 + (E1 - E0) * v
        return tuple(DC + sky_dir(a, e) * SKY_R)
    o = grid_surface("SkyPatch", fn, nu, nv, M_SKY, wrap_u=False, smooth=True)
    orient(o, lambda c: DC - c)
    return o
sky_patch()

# ----------------------------------------------------------------------------- lights (names starting "Lamp" are baked in Unity)
sd = bpy.data.lights.new("Lamp.lantern", 'SPOT'); sd.energy = 55.0; sd.color = (1.0, 0.66, 0.34); sd.shadow_soft_size = 0.03
sd.spot_size = math.radians(95); sd.spot_blend = 0.65
L1 = bpy.data.objects.new("Lamp.lantern", sd); L1.location = tuple(Vector(LF.p(0, 0.075, 0.11)))
L1.rotation_euler = (Vector(LF.p(0, 1.0, -0.7)) - Vector(LF.p(0, 0, 0.11))).to_track_quat('-Z', 'Y').to_euler(); K.link(L1)
pd = bpy.data.lights.new("Lamp.lanternglow", 'POINT'); pd.energy = 14.0; pd.color = (1.0, 0.62, 0.30); pd.shadow_soft_size = 0.05
L2 = bpy.data.objects.new("Lamp.lanternglow", pd); L2.location = tuple(Vector(LF.p(0, 0, 0.26))); K.link(L2)
ad = bpy.data.lights.new("Lamp.starlight", 'SPOT'); ad.energy = 25.0; ad.color = (0.55, 0.65, 1.0); ad.shadow_soft_size = 0.5
ad.spot_size = math.radians(120); ad.spot_blend = 1.0
L3 = bpy.data.objects.new("Lamp.starlight", ad)
sc = dome_pt(0, (PHI0 + PHI1) / 2, RO + 0.05); L3.location = tuple(sc)
L3.rotation_euler = (DC - sc).to_track_quat('-Z', 'Y').to_euler(); K.link(L3)

world = bpy.data.worlds.new("Night"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.004, 0.006, 0.014, 1); bg.inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors and living-scene markers
anchor("reader.entrance", (READER.x, READER.y, 0.0))
anchor("reader.look", tuple(Vector((READER.x, READER.y, EYE)) + LOOK * 2.0))
anchor("scene.centre", (0.0, 0.0, 0.0))
anchor("room.telescope", tuple(EYE_END - D * 0.2))
anchor("room.slit", tuple(dome_pt(0, (PHI0 + PHI1) / 2)))
anchor("room.lantern", tuple(LAMP_FLAME))
anchor("room.siphon", tuple(SIPHON))
anchor("room.door", tuple(az_dir(DOOR_AZ) * (R - 0.1)))
K.marker("sound.clock.0", tuple(CLK), size=0.15)

K.apply_all_transforms()

# ----------------------------------------------------------------------------- cameras (reader eye 1.55 m; lens 18 ~ the headset's 90 deg)
E = Vector((READER.x, READER.y, EYE))
def ahead(yaw_deg, pitch_deg=0.0, d=4.0):
    a = math.radians(LOOK_AZ - yaw_deg); p = math.radians(pitch_deg)
    return tuple(E + Vector((math.sin(a) * math.cos(p), math.cos(a) * math.cos(p), math.sin(p))) * d)
cams = [
    camera("Cam_Reader", tuple(E), ahead(0, 9)),
    camera("Cam_Left", tuple(E), ahead(70, -8)),
    camera("Cam_Right", tuple(E), ahead(-55, 8)),
    camera("Cam_Behind", tuple(E), ahead(180, -6)),
    camera("Cam_Up", tuple(E), ahead(-22, 58)),
    camera("Cam_Down", tuple(E), ahead(20, -60), lens=16),
    camera("Cam_Telescope", tuple(E + Vector((0.3, -0.5, -0.1))), tuple(TC), lens=26),
    camera("Cam_Lantern", tuple(Vector(LF.p(0.3, 1.2, 0.9))), tuple(Vector(LF.p(0, 0, 0.12))), lens=30),
    camera("Cam_Overview", tuple(az_dir(300) * (R - 0.3) + Vector((0, 0, 2.3))), (0.6, -0.4, 1.0), lens=14),
    camera("Cam_Siphon", tuple(Vector(Frame((TAB.x, TAB.y), math.radians(-TAB_AZ)).p(0.0, -0.75, 1.15))), tuple(SIPHON), lens=35),
]
EXPOSURE = {}

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "ogilvys_observatory_source.blend"))
K.budget_report()

if args.render:
    K.render_stills(scene, cams, EXPOSURE, default_exp=2.4)

if args.bake or args.export:
    T_ = args.tex
    size_for = {"M_Floorboards": (T_, T_ // 2, T_ // 2), "M_Matchboard": (T_, T_ // 2, T_ // 2),  "M_DomePaint": (T_, T_ // 4, T_ // 2),
                "M_DomeRibs": (T_ // 2, T_ // 8, T_ // 4), "M_PineTrim": (T_ // 2, T_ // 8, T_ // 4), "M_DoorBoards": (T_ // 4, T_ // 8, T_ // 4),
                "M_CastIron": (T_ // 2, T_ // 4, T_ // 4), "M_Brass": (T_ // 2, T_ // 4, T_ // 4), "M_Mahogany": (T_ // 2, T_ // 8, T_ // 4),
                "M_Oak": (T_ // 4, T_ // 8), "M_Books": (T_ // 4, T_ // 16), "M_Paper": (T_ // 4,), "M_Leather": (T_ // 4, T_ // 8),
                "M_SiphonGlass": (64,), "M_Pewter": (T_ // 8,), "M_Japanned": (T_ // 8, T_ // 16), "M_LanternLens": (64,),
                "M_Rope": (T_ // 16,), "M_Rug": (T_ // 4, T_ // 16, T_ // 8), "M_PierStone": (T_ // 8,), "M_Ebonite": (64,)}
    K.bake_and_export(scene, "ogilvys_observatory.gltf", size_for, keep_names={"M_NightSky": "far.sky"}, cams=cams,
                      blend_name="ogilvys_observatory_baked.blend")
print("DONE")
