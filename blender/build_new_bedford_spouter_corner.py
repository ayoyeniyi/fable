"""
Fable: the bleak corner before the Spouter Inn, New Bedford, a Saturday night in December (Moby-Dick, chapter 2,
"The Carpet-Bag").

"Such dreary streets! blocks of blackness, not houses, on either hand, and here and there a candle, like a candle
moving about in a tomb." "... the congealed frost lay ten inches thick in a hard, asphaltic pavement ... the flinty
projections." "Moving on, I at last came to a dim sort of light not far from the docks, and heard a forlorn creaking in
the air; and looking up, saw a swinging sign over the door with a white painting upon it, faintly representing a tall
straight jet of misty spray, and these words underneath - 'The Spouter Inn:- Peter Coffin.'" "It was a queer sort of
place - a gable-ended old house, one side palsied as it were, and leaning over sadly. It stood on a sharp bleak corner,
where that tempestuous wind Euroclydon kept up a worse howling than ever."

The reader stands in the middle of the frozen street, carpet-bag height, a few metres from the inn, facing it. The
Spouter is a small, dilapidated, two-storey clapboard house with its gable end to the street, leaning over to one
side; its door stands open on a dim porch (an ash-box just inside), two ground-floor windows give a dim, smoky light
through frosted glass, and over the door an iron bracket holds the swinging sign. The street turns past the inn's
right-hand side and runs down a lane to the wharf: spiles, a little black water and the masts and yards of whalers
against the stars. Behind and either side, dark clapboard houses ("blocks of blackness") with snow on their roofs, one
candle in an upper window; far back up the street the red windows of the Sword-Fish Inn. The street is ten inches of
packed, rutted ice and dirty snow; plank sidewalks, a granite curb before the inn's door. A clear, bitter starlit sky,
Orion rising over the harbour. No figures, no gas lamps, no named ships.

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/scene_kit_b1.py.

Node names the runtime relies on:
  anchor.reader.entrance (feet on the street, facing +Y toward the inn), anchor.reader.look, anchor.scene.centre
  (the inn's door), anchor.inn.sign
  light.moon (SUN, starlight: very dim, cool), light.sky (SUN, cool fill, no shadow), Lamp.inn.* (POINT, the inn's
  windows and porch), Lamp.swordfish (POINT, red windows far up the street), Lamp.candle (POINT)
  fx.lantern.porch (the porch lamp), fx.candle.window (the candle in an upper window across the street)
  water.ocean.harbour (the black water at the wharf)
  sound.wind.corner (Euroclydon at the corner), sound.surf.wharf, sound.rigging.wharf
  SkyDome (the starry night), far.* (none)

Run headless:
  blender -b -P blender/build_new_bedford_spouter_corner.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_new_bedford_spouter_corner.py -- --render --samples 48 --res 1400
  blender -b -P blender/build_new_bedford_spouter_corner.py -- --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b1 as S
from scene_kit_b1 import (K, E8, new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                          plain, image_mat, np_image, Canvas, box, cyl, sphere, lathe, tube, mesh_from, MB, anchor, sound, light_obj, camera,
                          link, smoothstep, lerp, n2, fbm2, orient, card, set_card_normals, az_dir, TWO_PI)

ARGS = S.setup("new-bedford-spouter-corner", 1841, "SpouterCorner", samples=48)
OUT = K.OUT; scene = K.scene
EYE = 1.55
R0 = random.Random(1841)

# ----------------------------------------------------------------------------- the lie of the land: the street falls toward the harbour (+Y, then +X down the lane)
LANE = [(1.5, 10.0), (8.0, 13.0), (16.0, 17.0), (24.0, 21.0), (30.0, 24.0)]
WHARF = 28.0        # distance along the lane where the wharf's edge is
def H(x, y):
    z = -0.035 * y - 0.03 * max(0.0, x - 2.0)
    d = S.seg_dist(x, y, LANE)
    z -= 0.0
    z += 0.02 * n2(x, y, 3.0, 2.0)
    return z
Z0 = H(0, 0)
def gz(x, y): return H(x, y) - Z0
S.set_ground(gz)

def street_mask(x, y):
    """1 on the trafficked ice of the street and the lane (ruts, dirt), 0 under the house fronts and sidewalks."""
    on_main = smoothstep(4.0, 3.2, abs(x)) * smoothstep(9.5, 8.0, y)
    on_lane = smoothstep(3.6, 2.6, S.seg_dist(x, y, LANE))
    return max(on_main, on_lane)

def rut_fn(x, y):
    """two wheel ruts down the middle of the street, and on into the lane."""
    if y < 9.0:
        return max(smoothstep(0.35, 0.05, abs(x - 0.75 - 0.1 * math.sin(y * 0.3))), smoothstep(0.35, 0.05, abs(x + 0.75 - 0.1 * math.sin(y * 0.3 + 1))))
    d = S.seg_dist(x, y, LANE)
    return max(smoothstep(0.35, 0.05, abs(d - 0.75)), 0.0)

def street_mat(name="M_StreetIce"):
    """'congealed frost ten inches thick in a hard, asphaltic pavement': packed snow gone to grey ice, trodden and
    rutted, dirty with ash, cinders and horse droppings in the ruts, crusted lumps ('flinty projections'), cleaner
    drifted snow at the edges, against the walls."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    at_s = node(nt, "ShaderNodeAttribute", (-1900, 600)); at_s.attribute_name = "street"
    at_r = node(nt, "ShaderNodeAttribute", (-1900, 450)); at_r.attribute_name = "rut"
    st = at_s.outputs["Fac"]; rut = at_r.outputs["Fac"]
    n = noise_(nt, co, 0.8, 5, 0.6, loc=(-1700, 200))
    fine = noise_(nt, co, 9.0, 5, 0.65, loc=(-1700, 0))
    v = voronoi_(nt, co, 4.0, 'F1', (-1700, -200))
    lumps = maprange(nt, v.outputs["Distance"], 0.0, 0.5, 1, 0, (-1500, -200))
    snow = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1500, 200)), c4(K.srgb((0.70, 0.72, 0.76))), c4(K.srgb((0.82, 0.83, 0.86))), (-1300, 200))
    ice = mix_rgb(nt, 'MIX', maprange(nt, fine.outputs["Fac"], 0.3, 0.7, 0, 1, (-1500, 0)), c4(K.srgb((0.44, 0.45, 0.47))), c4(K.srgb((0.60, 0.61, 0.63))), (-1300, 0))
    dirt = noise_(nt, co, 2.5, 4, 0.6, loc=(-1700, -400))
    grime = math_(nt, 'MULTIPLY', maprange(nt, dirt.outputs["Fac"], 0.4, 0.7, 0.0, 1.0, (-1500, -400)), rut, (-1300, -400))
    col = mix_rgb(nt, 'MIX', st, snow, ice, (-1100, 100))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', grime, 0.75, (-1100, -400)), col, c4(K.srgb((0.22, 0.20, 0.18))), (-900, 100))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', lumps, 0.25, (-1100, -200)), col, (0.8, 0.8, 0.82, 1), (-700, 100))
    big = noise_(nt, co, 0.35, 4, 0.6, loc=(-900, -600))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', st, 0.8, (-700, -600)), col, mix_rgb(nt, 'MIX', maprange(nt, big.outputs["Fac"], 0.35, 0.65, 0, 1, (-700, -700)), c4(K.srgb((0.55, 0.50, 0.45))), (1, 1, 1, 1), (-600, -650)), (-450, 100))
    col = K.ao_mul(nt, col, 0.3, 0.4, (-500, -800))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, st, 0.85, 0.5, (-600, -300)), b.inputs["Roughness"])
    hgt = math_(nt, 'ADD', math_(nt, 'MULTIPLY', lumps, 0.5, (-900, -900)), math_(nt, 'MULTIPLY', fine.outputs["Fac"], 0.5, (-900, -1000)), (-700, -950))
    hgt = math_(nt, 'SUBTRACT', hgt, math_(nt, 'MULTIPLY', rut, 0.8, (-900, -1100)), (-550, -1000))
    bump_from(nt, b, hgt, 0.8, 0.03)
    return m

def clapboard_mat(name, base, light, dark, paint=0.5, pitch=0.11, along='X'):
    """weathered lapped clapboards: horizontal boards (a shadow line under each lap), flaking grey paint over silvered
    wood, streaks of weather, dirt rising from the street."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1900, -300))
    zf = math_(nt, 'FRACT', math_(nt, 'DIVIDE', s.outputs["Z"], pitch, (-1700, 0)), None, (-1550, 0))
    lap = maprange(nt, zf, 0.0, 0.18, 0.25, 1.0, (-1400, 0))              # dark just under each board's lap
    boardid = math_(nt, 'FLOOR', math_(nt, 'DIVIDE', s.outputs["Z"], pitch, (-1700, -150)), None, (-1550, -150))
    mp = node(nt, "ShaderNodeMapping", (-1700, 300)); mp.inputs["Scale"].default_value = (0.6, 0.6, 30.0); nt.links.new(co, mp.inputs["Vector"])
    grain = noise_(nt, mp.outputs["Vector"], 3.0, 5, 0.65, loc=(-1500, 300))
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1400, -150)); wn.noise_dimensions = '1D'; nt.links.new(boardid, wn.inputs["W"])
    wood_c = mix_rgb(nt, 'MIX', maprange(nt, grain.outputs["Fac"], 0.3, 0.7, 0, 1, (-1300, 300)), c4(K.srgb(dark)), c4(K.srgb(base)), (-1100, 300))
    wood_c = mix_rgb(nt, 'MULTIPLY', 1.0, wood_c, maprange(nt, wn.outputs["Value"], 0, 1, 0.82, 1.12, (-1250, -150)), (-950, 250))
    pn = noise_(nt, co, 2.2, 6, 0.7, loc=(-1500, -400))
    flake = maprange(nt, pn.outputs["Fac"], 0.62 + paint * 0.08, 0.66 + paint * 0.08, 1, 0, (-1300, -400))
    col = mix_rgb(nt, 'MIX', flake, wood_c, c4(K.srgb(light)), (-800, 250))
    streak_m = node(nt, "ShaderNodeMapping", (-1700, -650)); streak_m.inputs["Scale"].default_value = (4.0, 4.0, 0.25); nt.links.new(co, streak_m.inputs["Vector"])
    streak = noise_(nt, streak_m.outputs["Vector"], 2.0, 3, 0.5, loc=(-1500, -650))
    col = mix_rgb(nt, 'MULTIPLY', maprange(nt, streak.outputs["Fac"], 0.45, 0.7, 0, 0.35, (-1300, -650)), col, (0.55, 0.55, 0.55, 1), (-650, 250))
    low = maprange(nt, s.outputs["Z"], 0.9, 0.0, 0, 0.5, (-1300, -850))
    col = mix_rgb(nt, 'MULTIPLY', low, col, (0.45, 0.42, 0.40, 1), (-500, 250))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, lap, (-350, 250))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
    hgt = math_(nt, 'ADD', zf, math_(nt, 'MULTIPLY', grain.outputs["Fac"], 0.15, (-900, -1000)), (-700, -1000))
    bump_from(nt, b, hgt, 0.5, 0.015)
    return m

def shingle_mat(name, base=(0.22, 0.21, 0.20), dark=(0.10, 0.10, 0.10)):
    """cedar shingles gone grey-black, in courses (mapped on world X/Z and Y/Z: works on any roof slope)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1900, -300))
    zf = math_(nt, 'FRACT', math_(nt, 'DIVIDE', s.outputs["Z"], 0.07, (-1700, 0)), None, (-1550, 0))
    row = math_(nt, 'FLOOR', math_(nt, 'DIVIDE', s.outputs["Z"], 0.07, (-1700, -150)), None, (-1550, -150))
    xs = math_(nt, 'ADD', math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-1700, -300)), math_(nt, 'MULTIPLY', row, 0.37, (-1550, -300)), (-1400, -300))
    sh = math_(nt, 'FLOOR', math_(nt, 'DIVIDE', xs, 0.18, (-1300, -300)), None, (-1150, -300))
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1000, -300)); wn.noise_dimensions = '2D'
    cv = node(nt, "ShaderNodeCombineXYZ", (-1100, -400)); nt.links.new(sh, cv.inputs["X"]); nt.links.new(row, cv.inputs["Y"]); nt.links.new(cv.outputs[0], wn.inputs["Vector"])
    gap = math_(nt, 'FRACT', math_(nt, 'DIVIDE', xs, 0.18, (-1300, -450)), None, (-1150, -450))
    gapk = maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', gap, 0.5, (-1000, -500)), None, (-900, -500)), 0.46, 0.5, 1, 0.5, (-800, -500))
    col = mix_rgb(nt, 'MIX', wn.outputs["Value"], c4(K.srgb(dark)), c4(K.srgb(base)), (-700, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, zf, 0.0, 0.25, 0.5, 1.0, (-900, 0)), (-500, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, gapk, (-350, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
    bump_from(nt, b, math_(nt, 'MULTIPLY', zf, gapk, (-500, -700)), 0.6, 0.01)
    return m

def snow_mat(name="M_Snow"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    n = noise_(nt, co, 2.0, 5, 0.6, loc=(-900, 0))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-700, 0)), c4(K.srgb((0.80, 0.82, 0.86))), c4(K.srgb((0.90, 0.91, 0.94))), (-500, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.75
    bump_from(nt, b, n.outputs["Fac"], 0.3, 0.02)
    return m

def frost_glass(name, lit=None, strength=0.0):
    """window glass furred with frost ('from a glass window where the frost is all on the outside'): pale crystalline
    feathers creeping in from the frame; lit windows glow through it."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    v = voronoi_(nt, co, 40.0, 'F1', (-1000, 0))
    fr = noise_(nt, co, 25.0, 6, 0.7, 2.0, (-1000, -250))
    frost = maprange(nt, math_(nt, 'ADD', fr.outputs["Fac"], math_(nt, 'MULTIPLY', v.outputs["Distance"], 0.3, (-800, 0)), (-700, -100)), 0.45, 0.75, 0, 1, (-550, -100))
    base = c4((0.02, 0.025, 0.03)) if lit is None else c4(lit)
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', frost, 0.8, (-450, 0)), base, c4(K.srgb((0.55, 0.58, 0.62))) if lit is None else c4(tuple(min(1, c * 1.2 + 0.1) for c in lit)), (-300, 0))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, frost, 0.05, 0.6, (-300, -300)), b.inputs["Roughness"])
    if lit is not None:
        nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = strength
    return m

print("materials ...", flush=True)
M_STREET = street_mat()
M_INNBOARD = clapboard_mat("M_InnBoards", (0.36, 0.33, 0.29), (0.52, 0.51, 0.48), (0.20, 0.18, 0.16), paint=0.3)
M_BOARDS = clapboard_mat("M_Clapboard", (0.30, 0.28, 0.25), (0.40, 0.40, 0.39), (0.16, 0.15, 0.13), paint=0.6)
M_SHINGLE = shingle_mat("M_Shingles")
M_SNOW = snow_mat()
M_TRIM = K.noisy("M_Trim", [K.srgb((0.30, 0.29, 0.27)), K.srgb((0.38, 0.37, 0.35)), K.srgb((0.22, 0.21, 0.20))], scale=6, rough=0.8, bump=0.1, stretch=(1, 1, 8))
M_GLASS = frost_glass("M_FrostGlass")
M_INNGLASS = frost_glass("M_InnWindow", lit=(0.55, 0.32, 0.12), strength=1.6)
M_REDGLASS = frost_glass("M_RedWindow", lit=(0.65, 0.12, 0.05), strength=3.0)
M_CANDLEGLASS = frost_glass("M_CandleWindow", lit=(0.45, 0.28, 0.10), strength=1.2)
M_BRICK = K.noisy("M_Brick", [K.srgb((0.30, 0.15, 0.11)), K.srgb((0.38, 0.20, 0.14)), K.srgb((0.24, 0.12, 0.09))], scale=14, rough=0.9, bump=0.3, bump_dist=0.005)
M_GRANITE = S.stone_mat("M_Granite", (0.42, 0.42, 0.42), (0.20, 0.20, 0.21), (0.55, 0.55, 0.55), scale=6.0, rough=0.8, bump=0.15)
M_PLANK = K.noisy("M_Planks", [K.srgb((0.26, 0.23, 0.19)), K.srgb((0.33, 0.30, 0.25)), K.srgb((0.18, 0.16, 0.13))], scale=5, rough=0.85, bump=0.2, stretch=(1, 10, 1))
M_IRON = plain("M_Iron", (0.03, 0.03, 0.03), rough=0.55, metallic=0.8)
M_PILE = S.bark_mat("M_Spiles", (0.20, 0.18, 0.15), (0.08, 0.07, 0.06), (0.28, 0.26, 0.22), scale=2.0, fissure=0.5, moss=0.15)
M_SPAR = K.noisy("M_Spars", [K.srgb((0.16, 0.13, 0.10)), K.srgb((0.22, 0.18, 0.14))], scale=4, rough=0.7, bump=0.05, stretch=(1, 1, 10))
M_ROPE = plain("M_Rigging", (0.05, 0.045, 0.04), rough=0.9)
M_SEA = S.water_mat("M_Harbour", deep=(0.006, 0.008, 0.012), rough=0.05)
M_INTERIOR = K.noisy("M_PorchInside", [K.srgb((0.20, 0.14, 0.09)), K.srgb((0.26, 0.19, 0.12))], scale=3, rough=0.9, bump=0.1)
M_ASH = K.noisy("M_Ash", [K.srgb((0.42, 0.40, 0.38)), K.srgb((0.30, 0.29, 0.28))], scale=30, rough=1.0, bump=0.2)
M_SIGN = K.noisy("M_SignBoard", [K.srgb((0.10, 0.12, 0.13)), K.srgb((0.14, 0.15, 0.16)), K.srgb((0.08, 0.08, 0.09))], scale=8, rough=0.75, bump=0.15, stretch=(6, 1, 1))
M_SIGNPAINT = plain("M_SignPaint", K.srgb((0.78, 0.78, 0.74)), rough=0.8)
M_FLAME = plain("M_LampFlame", (1.0, 0.7, 0.35), emission=(1.0, 0.62, 0.28), strength=20.0)

# ----------------------------------------------------------------------------- the street surface
print("ground ...", flush=True)
GROUND = S.ground("Street", M_STREET, 70.0, r0=3.0, NA=96, NR=30, attrs={"street": street_mask, "rut": rut_fn})

# ----------------------------------------------------------------------------- houses
def gable_house(name, origin, yaw, w, d, eave, pitch_deg, walls, lean=0.0, ridge_along='front', windows=(), door=None,
                chimney=None, snow=True, overhang=0.25, wall_lit=None):
    """A clapboard house in a local frame: front wall at local y=0 facing -y, x across [-w/2, w/2], depth d to +y,
    floor at the ground under the origin. ridge_along='front': gable end to the front (the ridge runs back);
    'side': eaves to the front. lean: shear in x per metre of height (the palsied side). windows: list of
    (wall, u, z, ww, hh, glass_mat) with wall in 'front','back','left','right', u = offset along the wall."""
    O = Vector((origin[0], origin[1], gz(origin[0], origin[1]) - 0.15))
    Ry = Matrix.Rotation(yaw, 3, 'Z')
    def P(x, y, z): return O + Ry @ Vector((x + lean * z, y, z))
    pitch = math.radians(pitch_deg)
    objs = []
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    hw = w / 2
    if ridge_along == 'front':
        rise = hw * math.tan(pitch)
        prof = [(-hw, 0), (hw, 0), (hw, eave), (0, eave + rise), (-hw, eave)]           # x, z of the gable ends
        f0 = [bm.verts.new(P(x, 0, z)) for x, z in prof]; f1 = [bm.verts.new(P(x, d, z)) for x, z in prof]
        bm.faces.new(f0); bm.faces.new(list(reversed(f1)))
        for i in range(len(prof)):
            j = (i + 1) % len(prof); bm.faces.new((f0[i], f1[i], f1[j], f0[j]))
    else:
        rise = (d / 2) * math.tan(pitch)
        prof = [(0, 0), (d, 0), (d, eave), (d / 2, eave + rise), (0, eave)]              # y, z of the gable ends (left/right)
        f0 = [bm.verts.new(P(-hw, y, z)) for y, z in prof]; f1 = [bm.verts.new(P(hw, y, z)) for y, z in prof]
        bm.faces.new(f0); bm.faces.new(list(reversed(f1)))
        for i in range(len(prof)):
            j = (i + 1) % len(prof); bm.faces.new((f0[i], f1[i], f1[j], f0[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(walls); link(o)
    # roof slabs (with overhang), snow on top
    t = 0.12; ov = overhang
    def slab(nm, corners, mat, th):
        bm2 = bmesh.new()
        vs = [bm2.verts.new(c) for c in corners]
        n = (Vector(corners[1]) - Vector(corners[0])).cross(Vector(corners[3]) - Vector(corners[0])).normalized()
        if n.z < 0: n = -n
        vs2 = [bm2.verts.new(Vector(c) + n * th) for c in corners]
        bm2.faces.new(vs); bm2.faces.new(list(reversed(vs2)))
        for i in range(4):
            j = (i + 1) % 4; bm2.faces.new((vs[i], vs[j], vs2[j], vs2[i]))
        bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
        me2 = bpy.data.meshes.new(nm); bm2.to_mesh(me2); bm2.free()
        ob = bpy.data.objects.new(nm, me2); me2.materials.append(mat); link(ob); return ob
    if ridge_along == 'front':
        ex = ov / math.cos(pitch)
        for sd in (-1, 1):
            a = P(sd * (hw + ov), -ov, eave - ov * math.tan(pitch)); bb = P(0, -ov, eave + rise + 0.02)
            c = P(0, d + ov, eave + rise + 0.02); dd = P(sd * (hw + ov), d + ov, eave - ov * math.tan(pitch))
            slab(f"{name}_roof{sd}", [a, bb, c, dd], M_SHINGLE, t)
            if snow:
                k = 0.85
                a2 = Vector(a).lerp(Vector(bb), 0.04); b2 = Vector(a).lerp(Vector(bb), 0.98); c2 = Vector(dd).lerp(Vector(c), 0.98); d2 = Vector(dd).lerp(Vector(c), 0.04)
                nrm = (b2 - a2).cross(d2 - a2).normalized()
                if nrm.z < 0: nrm = -nrm
                slab(f"{name}_snow{sd}", [a2 + nrm * t, b2 + nrm * t, c2 + nrm * t, d2 + nrm * t], M_SNOW, 0.08)
    else:
        for sd in (0, 1):
            y_e = -ov if sd == 0 else d + ov
            a = P(-hw - ov, y_e, eave - ov * math.tan(pitch)); bb = P(-hw - ov, d / 2, eave + rise + 0.02)
            c = P(hw + ov, d / 2, eave + rise + 0.02); dd = P(hw + ov, y_e, eave - ov * math.tan(pitch))
            slab(f"{name}_roof{sd}", [a, bb, c, dd], M_SHINGLE, t)
            if snow:
                a2 = Vector(a).lerp(Vector(bb), 0.04); b2 = Vector(a).lerp(Vector(bb), 0.98); c2 = Vector(dd).lerp(Vector(c), 0.98); d2 = Vector(dd).lerp(Vector(c), 0.04)
                nrm = (b2 - a2).cross(d2 - a2).normalized()
                if nrm.z < 0: nrm = -nrm
                slab(f"{name}_snow{sd}", [a2 + nrm * t, b2 + nrm * t, c2 + nrm * t, d2 + nrm * t], M_SNOW, 0.08)
    # corner boards
    for (cx, cy) in ((-hw, 0), (hw, 0), (-hw, d), (hw, d)):
        p0 = P(cx, cy, 0); p1 = P(cx, cy, eave)
        sx = 0.012 if cx > 0 else -0.012; sy = -0.012 if cy == 0 else 0.012
        tube(f"{name}_corner{cx}{cy}", [Vector(p0) + Ry @ Vector((sx, sy, 0)), Vector(p1) + Ry @ Vector((sx, sy, 0))], [0.07, 0.07], M_TRIM, sides=4)
    # windows: a frame, sash bars (6 over 6), glass
    def wall_frame(wall, u, z):
        if wall == 'front': return P(u, -0.02, z), Ry @ Vector((1, 0, 0)), Ry @ Vector((0, -1, 0))
        if wall == 'back': return P(-u, d + 0.02, z), Ry @ Vector((-1, 0, 0)), Ry @ Vector((0, 1, 0))
        if wall == 'left': return P(-hw - 0.02, u, z), Ry @ Vector((0, 1, 0)), Ry @ Vector((-1, 0, 0))
        return P(hw + 0.02, d - u, z), Ry @ Vector((0, -1, 0)), Ry @ Vector((1, 0, 0))
    for wi, (wall, u, z, ww, hh, gm) in enumerate(windows):
        c, right, out = wall_frame(wall, u, z)
        c = Vector(c); up = Vector((0, 0, 1))
        gq = [c - right * ww / 2, c + right * ww / 2, c + right * ww / 2 + up * hh, c - right * ww / 2 + up * hh]
        mesh_from(f"{name}_glass{wi}", gq, [(0, 1, 2, 3)], gm)
        fw = 0.07
        c = c + out * 0.02
        for (p0, p1) in ((c - right * (ww / 2 + fw / 2), c - right * (ww / 2 + fw / 2) + up * hh), (c + right * (ww / 2 + fw / 2), c + right * (ww / 2 + fw / 2) + up * hh),
                         (c - right * (ww / 2 + fw) + up * (hh + fw / 2), c + right * (ww / 2 + fw) + up * (hh + fw / 2)),
                         (c - right * (ww / 2 + fw) - up * 0.03 + out * 0.03, c + right * (ww / 2 + fw) - up * 0.03 + out * 0.03)):
            tube(f"{name}_wf{wi}", [p0, p1], [fw * 0.6, fw * 0.6], M_TRIM, sides=4)
        for k in (1, 2):
            p = c + right * (ww * (k / 3 - 0.5)) + out * 0.012
            tube(f"{name}_mv{wi}{k}", [p, p + up * hh], [0.012, 0.012], M_TRIM, sides=4, caps=False)
        for k in (1, 2, 3):
            p = c + up * (hh * k / 4) + out * 0.012
            tube(f"{name}_mh{wi}{k}", [p - right * ww / 2, p + right * ww / 2], [0.014 if k == 2 else 0.01] * 2, M_TRIM, sides=4, caps=False)
        # snow on the sill
        box(f"{name}_sillsnow{wi}", (ww + 0.1, 0.06, 0.03), tuple(c - up * 0.01 + out * 0.06), M_SNOW, rot=(0, 0, yaw))
    if door is not None:
        wall, u, dw, dh = door[:4]
        c, right, out = wall_frame(wall, u, 0.15)
        c = Vector(c)
        box(f"{name}_door", (dw, 0.06, dh), tuple(c - out * 0.04 + Vector((0, 0, dh / 2))), M_TRIM, rot=(0, 0, yaw))
        box(f"{name}_step", (dw + 0.5, 0.45, 0.18), tuple(c + out * 0.22 + Vector((0, 0, -0.06))), M_GRANITE, rot=(0, 0, yaw))
    if chimney is not None:
        cxu, cyu = chimney
        top = eave + (hw * math.tan(pitch) if ridge_along == 'front' else (d / 2) * math.tan(pitch)) + 0.9
        p = P(cxu, cyu, 0)
        box(f"{name}_chimney", (0.6, 0.5, top - eave + 0.6), (p[0] + lean * (eave + 0.3), p[1], p[2] + eave - 0.3 + (top - eave + 0.6) / 2), M_BRICK, rot=(0, 0, yaw))
        box(f"{name}_chimcap", (0.72, 0.62, 0.08), (p[0] + lean * (eave + 0.3), p[1], p[2] + top + 0.3), M_SNOW, rot=(0, 0, yaw))
    return P

print("houses ...", flush=True)
# the Spouter: small, old, gable end to the street, leaning to the right (the palsied side), door open
INN_O = (-1.6, 7.6); INN_W, INN_D = 6.4, 8.0
inn_windows = [('front', -1.9, 1.0, 0.85, 1.25, M_INNGLASS), ('front', 1.9, 1.0, 0.85, 1.25, M_INNGLASS),
               ('front', -1.5, 3.35, 0.8, 1.1, M_GLASS), ('front', 1.5, 3.35, 0.8, 1.1, M_GLASS), ('front', 0.0, 5.3, 0.55, 0.7, M_GLASS),
               ('right', 1.6, 1.0, 0.85, 1.25, M_INNGLASS), ('right', 5.0, 1.0, 0.85, 1.25, M_GLASS), ('right', 2.5, 3.35, 0.8, 1.1, M_GLASS)]
P_INN = gable_house("Inn", INN_O, 0.0, INN_W, INN_D, 4.4, 42.0, M_INNBOARD, lean=0.10, ridge_along='front', windows=inn_windows,
                    door=None, chimney=(-1.8, 5.5), overhang=0.3)
# the open door: a dark opening with a dim porch behind it, the door leaf swung in, an ash-box just inside
DOOR_W, DOOR_H = 1.0, 2.05
dc = Vector(P_INN(0, 0, 0.15))
box("InnDoorStep", (1.6, 0.6, 0.2), tuple(dc + Vector((0, -0.32, -0.05))), M_GRANITE)
box("InnCurb", (5.0, 0.3, 0.25), tuple(Vector((dc.x, dc.y - 1.6, gz(dc.x, dc.y - 1.6) - 0.02))), M_GRANITE)
cutter = box("DoorCutter", (DOOR_W, 0.6, DOOR_H), tuple(Vector(P_INN(0, 0, 0.15)) + Vector((0.07 * (DOOR_H / 2 + 0.15), 0, DOOR_H / 2 + 0.15))), M_TRIM)
inn_walls = bpy.data.objects["Inn"]
bo = inn_walls.modifiers.new("Door", 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.object = cutter; bo.solver = 'EXACT'
bpy.context.view_layer.objects.active = inn_walls; inn_walls.select_set(True)
bpy.ops.object.modifier_apply(modifier="Door"); inn_walls.select_set(False)
bpy.data.objects.remove(cutter, do_unlink=True)
# porch interior: cut the doorway by laying a dark porch box in front of the wall (its front face is the doorway's depth)
porch = box("InnPorch", (DOOR_W, 1.6, DOOR_H), tuple(Vector(P_INN(0, 0.82, 0.15)) + Vector((0, 0, DOOR_H / 2 + 0.15))), M_INTERIOR)
# flip the porch box inside-out so we see its inner faces through the doorway, and remove its front face
bm = bmesh.new(); bm.from_mesh(porch.data); bm.faces.ensure_lookup_table()
front = [f for f in bm.faces if f.normal.y < -0.9]
bmesh.ops.delete(bm, geom=front, context='FACES')
bmesh.ops.reverse_faces(bm, faces=bm.faces)
bm.to_mesh(porch.data); bm.free()
pc = Vector(P_INN(0, 0, 0.15))
for (p0, p1) in ((pc + Vector((-DOOR_W / 2 - 0.05, -0.04, 0)), pc + Vector((-DOOR_W / 2 - 0.05 + 0.05 * DOOR_H, -0.04, DOOR_H + 0.05))),
                 (pc + Vector((DOOR_W / 2 + 0.05, -0.04, 0)), pc + Vector((DOOR_W / 2 + 0.05 + 0.05 * DOOR_H, -0.04, DOOR_H + 0.05))),
                 (pc + Vector((-DOOR_W / 2 - 0.1 + 0.05 * DOOR_H, -0.04, DOOR_H + 0.08)), pc + Vector((DOOR_W / 2 + 0.1 + 0.05 * DOOR_H, -0.04, DOOR_H + 0.08)))):
    tube("InnDoorFrame", [p0, p1], [0.06, 0.06], M_TRIM, sides=4)
leaf = box("InnDoorLeaf", (0.05, DOOR_W * 0.95, DOOR_H - 0.05), tuple(pc + Vector((DOOR_W / 2 - 0.03, 0.5, DOOR_H / 2))), M_TRIM)
leaf.rotation_euler = (0, 0, math.radians(-20))
ab = Vector(P_INN(-0.25, 0.5, 0.15))
box("AshBox", (0.45, 0.35, 0.32), tuple(ab + Vector((0, 0, 0.16))), M_PLANK, bevel=0.01)
box("Ashes", (0.40, 0.30, 0.04), tuple(ab + Vector((0, 0, 0.31))), M_ASH)
# the porch lamp on the inside wall, seen through the door
PORCH_LAMP = Vector(P_INN(0.38, 1.4, 1.95))
cyl("PorchLampBody", 0.07, 0.22, tuple(PORCH_LAMP), M_IRON, verts=8)
cyl("PorchLampFlame", 0.025, 0.06, tuple(PORCH_LAMP + Vector((0, 0, -0.02))), M_FLAME, verts=6)
# the dim inn light inside the ground-floor windows (lamps behind the frosted glass)
INN_LAMPS = [Vector(P_INN(-1.9, 1.2, 1.6)), Vector(P_INN(1.9, 1.2, 1.6)), PORCH_LAMP + Vector((0, -0.6, -0.1))]

# the sign: an iron bracket from the inn's right-hand front corner (the bleak corner itself), out over the lane's
# mouth, the board hanging from two rings and facing down the street toward the reader, swung a little by the wind
br0 = Vector(P_INN(INN_W / 2 + 0.02, -0.06, 3.05)); xdir = Vector((1, 0, 0))
br1 = br0 + xdir * 1.35 + Vector((0, 0, 0.04))
tube("SignBracket", [br0, br1], [0.028, 0.02], M_IRON, sides=6)
tube("SignBrace", [br0 + Vector((0, 0, -0.6)), br0.lerp(br1, 0.7)], [0.018, 0.015], M_IRON, sides=6)
for k in range(9):   # a scroll in the angle between bracket and brace
    a0 = k / 9 * math.pi * 1.5; a1 = (k + 1) / 9 * math.pi * 1.5; rr0 = 0.16 * (1 - k / 12); rr1 = 0.16 * (1 - (k + 1) / 12)
    c0 = br0 + Vector((0.22, 0, -0.2))
    tube(f"SignScroll{k}", [c0 + Vector((math.cos(a0) * rr0, 0, math.sin(a0) * rr0)), c0 + Vector((math.cos(a1) * rr1, 0, math.sin(a1) * rr1))], [0.01, 0.01], M_IRON, sides=4)
SIGN_C = br0.lerp(br1, 0.58) + Vector((0, 0, -0.52))
for dx in (-0.36, 0.36):
    tube("SignChain", [br0.lerp(br1, 0.58) + Vector((dx, 0, 0)), SIGN_C + Vector((dx, 0, 0.36))], [0.008, 0.008], M_IRON, sides=4)
sign = box("SignBoard", (1.0, 0.045, 0.72), tuple(SIGN_C), M_SIGN, bevel=0.012)
def sign_text(nm, body, size, off, back=False):
    cu = bpy.data.curves.new(nm, 'FONT'); cu.body = body; cu.size = size; cu.extrude = 0.002; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    o = bpy.data.objects.new(nm, cu); link(o)
    o.rotation_euler = (math.pi / 2, 0, math.pi if back else 0.0)
    o.location = Vector((SIGN_C.x, SIGN_C.y + (0.025 if back else -0.025), SIGN_C.z)) + off
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH'); o.data.materials.append(M_SIGNPAINT)
    return o
for back in (False, True):
    sign_text(f"SignText1{back}", "The Spouter Inn:\u2014", 0.082, Vector((0, 0, -0.16)), back)
    sign_text(f"SignText2{back}", "Peter Coffin.", 0.08, Vector((0, 0, -0.27)), back)
# the white painting: a tall straight jet of misty spray, a narrow column that opens into a soft plume at the top
spray_mb = MB()
for back in (False, True):
    yy = SIGN_C.y + (0.024 if back else -0.024)
    def quad(p0, p1, w0, w1):
        i0 = spray_mb.vert(p0 + Vector((-w0 / 2, 0, 0))); i1 = spray_mb.vert(p0 + Vector((w0 / 2, 0, 0)))
        i2 = spray_mb.vert(p1 + Vector((w1 / 2, 0, 0))); i3 = spray_mb.vert(p1 + Vector((-w1 / 2, 0, 0)))
        if back: spray_mb.face(i0, i1, i2, i3)
        else: spray_mb.face(i3, i2, i1, i0)
    base = Vector((SIGN_C.x, yy, SIGN_C.z - 0.07))
    for k in range(5):
        dx = (k - 2) * 0.008
        quad(base + Vector((dx, 0, 0)), base + Vector((dx * 2.2, 0, 0.27)), 0.007, 0.012)
    for k in range(9):   # the plume: small diamonds scattered round the top of the jet
        a = k / 9 * TWO_PI; r = 0.035 + 0.02 * (k % 3)
        c = base + Vector((math.cos(a) * r * 1.4, 0, 0.30 + math.sin(a) * r * 0.8))
        quad(c - Vector((0, 0, 0.025)), c + Vector((0, 0, 0.025)), 0.05, 0.0)
        quad(c + Vector((0, 0, 0.025)), c - Vector((0, 0, 0.025)), 0.0, 0.05)
spray_mb.build("SignSpray", M_SIGNPAINT, sway=False)
SIGN_PARTS = [sign] + [o for o in K.COLL.objects if o.name.startswith(("SignText", "SignSpray"))]
pivot = SIGN_C + Vector((0, 0, 0.36))
Mrot = Matrix.Translation(pivot) @ (Matrix.Rotation(math.radians(-9), 4, 'Z') @ Matrix.Rotation(math.radians(5), 4, 'X')) @ Matrix.Translation(-pivot)
bpy.context.view_layer.update()
for o in SIGN_PARTS:
    o.matrix_world = Mrot @ o.matrix_world

# the other houses: blocks of blackness either side of the street, along the lane, and up the street behind
HOUSES = [
    # name, origin, yaw, w, d, eave, pitch, ridge, windows(lit), chimney
    ("HouseL1", (-5.8, 1.0), math.radians(90), 7.5, 7.0, 5.0, 38, 'side'),
    ("HouseL2", (-5.8, -7.0), math.radians(90), 7.0, 7.5, 5.6, 35, 'front'),
    ("HouseL3", (-5.8, -15.0), math.radians(90), 7.5, 8.0, 5.2, 40, 'side'),
    ("HouseL4", (-5.8, -23.5), math.radians(90), 8.0, 7.5, 6.0, 36, 'side'),
    ("HouseL5", (-5.8, -32.0), math.radians(90), 7.5, 8.0, 5.4, 38, 'front'),
    ("HouseR1", (5.8, -1.0), math.radians(-90), 7.0, 7.5, 5.4, 40, 'side'),
    ("HouseR2", (5.8, -9.5), math.radians(-90), 8.0, 8.0, 5.0, 36, 'front'),
    ("HouseR3", (5.8, -18.0), math.radians(-90), 7.5, 7.5, 5.8, 38, 'side'),
    ("HouseR4", (5.8, -26.5), math.radians(-90), 8.0, 8.0, 5.2, 40, 'side'),
    ("HouseR5", (5.8, -35.0), math.radians(-90), 7.5, 7.5, 6.2, 34, 'front'),
    ("HouseR0", (5.8, 5.4), math.radians(-90), 4.4, 6.0, 4.8, 40, 'side'),
    ("HouseN1", (6.6, 16.6), math.radians(26), 8.0, 8.0, 5.6, 38, 'side'),     # across the lane, beyond the corner
    ("HouseN2", (14.6, 20.6), math.radians(26), 7.5, 7.5, 5.0, 40, 'side'),
    ("HouseS1", (10.2, 9.0), math.radians(206), 7.5, 8.0, 5.0, 36, 'side'),     # the lane's south side
    ("HouseS2", (18.4, 13.0), math.radians(206), 7.0, 7.5, 4.6, 38, 'front'),
    ("Behind", (-5.8, 19.5), 0.0, 8.0, 7.0, 5.4, 38, 'side'),
    ("NextDoor", (-9.4, 8.4), 0.0, 7.0, 8.0, 5.2, 38, 'side'),
    ("NextDoor2", (-16.6, 9.0), 0.0, 7.0, 8.0, 5.8, 36, 'front'),                   # behind the inn
]
R = random.Random(9)
CANDLE = None
for (nm, o_, yaw, w, d, eave, pitch, ridge) in HOUSES:
    wins = []
    for fl, z in ((0, 1.0), (1, 3.4)):
        if eave < 3.4 + 1.3 and fl == 1: continue
        nwin = 2 if w < 7.6 else 3
        for i in range(nwin):
            u = (i - (nwin - 1) / 2) * (w / nwin)
            wins.append(('front', u, z, 0.85, 1.3 if fl == 0 else 1.15, M_GLASS))
    if nm == "HouseR1":   # the candle in an upper window across the street: "like a candle moving about in a tomb"
        wins = [wn if not (wn[2] > 3 and wn[1] > 0) else (wn[0], wn[1], wn[2], wn[3], wn[4], M_CANDLEGLASS) for wn in wins]
    lean = R.uniform(-0.012, 0.012)
    Pf = gable_house(nm, o_, yaw, w, d, eave, pitch, M_BOARDS, lean=lean, ridge_along=ridge, windows=wins,
                     door=('front', R.choice((-1, 1)) * w * 0.18, 0.95, 2.0), chimney=(R.uniform(-1.5, 1.5), d * 0.5), overhang=0.25)
    if nm == "HouseR1":
        u = [wn for wn in wins if wn[5] is M_CANDLEGLASS][0][1]
        CANDLE = Vector(Pf(u, 0.4, 3.4 + 0.5))
# the Sword-Fish Inn far back up the street, its red windows
SF = gable_house("SwordFish", (-5.8, -43.0), math.radians(90), 9.0, 8.0, 5.6, 36, M_BOARDS, ridge_along='side',
                 windows=[('front', -2.6, 1.0, 1.0, 1.4, M_REDGLASS), ('front', 0.0, 1.0, 1.0, 1.4, M_REDGLASS), ('front', 2.6, 1.0, 1.0, 1.4, M_REDGLASS),
                          ('front', -2.0, 3.4, 0.9, 1.2, M_GLASS), ('front', 2.0, 3.4, 0.9, 1.2, M_GLASS)], chimney=(1.0, 4.0))
SF_LAMP = Vector(SF(0.0, -1.5, 1.6))
# far up the street the houses go on into the dark (cheap blocks, roofs with snow)
for k in range(8):
    side = -1 if k % 2 == 0 else 1; y = -50 - (k // 2) * 9
    gable_house(f"Far{k}", (side * 5.8, y), math.radians(90 * side), 8.0, 8.0, R.uniform(5, 6.5), R.uniform(34, 42), M_BOARDS,
                ridge_along=R.choice(('side', 'front')), windows=(), chimney=None)

# plank sidewalks along the house fronts, half under drifted snow
for sd in (-1, 1):
    for k in range(64):
        y = 6.0 - k * 0.6
        box(f"Walk{sd}_{k}", (1.6, 0.56, 0.05), (sd * 5.0 + R.gauss(0, 0.01), y, gz(sd * 5.0, y) + 0.03), M_PLANK, rot=(0, 0, R.gauss(0, 0.01)))
# drifted snow against the walls and over the sidewalks' outer edges
SNOW = []
for sd in (-1, 1):
    for k in range(26):
        y = 6.5 - k * 1.6 + R.gauss(0, 0.3)
        sphere(f"Drift{sd}_{k}", 1.0, (sd * R.uniform(4.2, 4.5), y, gz(sd * 4.3, y) - 0.05), M_SNOW, seg=10,
               scale=(R.uniform(0.25, 0.45), R.uniform(0.9, 1.4), R.uniform(0.16, 0.24)))
# lumps of frozen snow and ice ('flinty projections') on the street
for k in range(40):
    x, y = R.uniform(-3.6, 3.6), R.uniform(-14, 6)
    if math.hypot(x, y) < 1.2 or (abs(x) < 0.6 and 0 < y < 3): continue
    sphere(f"IceLump{k}", 1.0, (x, y, gz(x, y) - 0.02), M_SNOW if R.random() < 0.5 else M_GRANITE if False else M_SNOW, seg=8,
           scale=(R.uniform(0.06, 0.18), R.uniform(0.06, 0.16), R.uniform(0.03, 0.07)))

# ----------------------------------------------------------------------------- the wharf at the bottom of the lane: spiles, black water, masts
print("wharf ...", flush=True)
WH = Vector((27.0, 22.0, 0))
wharf_dir = Vector((0.9, 0.44, 0)).normalized()        # down the lane
wside = Vector((-wharf_dir.y, wharf_dir.x, 0))
edge = WH + wharf_dir * 2.0
for k in range(22):
    p = edge + wside * (k - 11) * 1.1
    tube(f"Spile{k}", [p + Vector((0, 0, -3.5)), p + Vector((R.gauss(0, 0.03), R.gauss(0, 0.03), gz(p.x, p.y) + R.uniform(0.6, 1.3)))], [0.16, 0.14], M_PILE, sides=7)
    if R.random() < 0.6:
        box(f"SpileSnow{k}", (0.3, 0.3, 0.08), (p.x, p.y, gz(p.x, p.y) + 1.0), M_SNOW)
box("WharfCap", (0.3, 24.0, 0.25), tuple(edge + Vector((0, 0, gz(edge.x, edge.y) + 0.1))), M_PILE, rot=(0, 0, math.atan2(wside.y, wside.x) - math.pi / 2))
WATER_C = edge + wharf_dir * 40
S.water_surface("Harbour", M_SEA, gz(edge.x, edge.y) - 1.8, lambda x, y: (Vector((x, y, 0)) - edge).dot(wharf_dir) > 0.2, extent=200.0, step=6.0, centre=(WATER_C.x, WATER_C.y))
# masts and yards of whalers lying at the wharf beyond (hulls below the wharf's edge, unseen)
for k, (along, side, h) in enumerate(((6.0, -6.0, 26.0), (6.5, 4.0, 24.0), (18.0, -14.0, 28.0), (16.0, 12.0, 22.0))):
    base = edge + wharf_dir * along + wside * side
    for m_, (off, hh) in enumerate(((-7.0, h * 0.85), (0.0, h), (7.0, h * 0.8))):
        mb_ = base + wside.cross(Vector((0, 0, 1))) * 0 + wharf_dir.cross(Vector((0, 0, 1))) * 0 + wside * 0 + Vector(wside) * 0
        mpos = base + Vector((wharf_dir.y, -wharf_dir.x, 0)) * 0 + wside * off * 0 + Vector(wharf_dir) * 0
        mpos = base + Vector(wside) * off
        z0 = gz(edge.x, edge.y) - 1.0
        tube(f"Mast{k}_{m_}", [mpos + Vector((0, 0, z0)), mpos + Vector((0, 0, z0 + hh))], [0.22, 0.09], M_SPAR, sides=6)
        for yk, frac in enumerate((0.45, 0.68, 0.86)):
            yl = (hh * 0.42) * (1 - yk * 0.22)
            c = mpos + Vector((0, 0, z0 + hh * frac))
            tube(f"Yard{k}_{m_}_{yk}", [c - wharf_dir * yl / 2, c + wharf_dir * yl / 2], [0.07, 0.07], M_SPAR, sides=4)
        # shrouds: a few lines down to each side
        for sdd in (-1, 1):
            for q in range(3):
                tube(f"Shroud{k}_{m_}", [mpos + Vector((0, 0, z0 + hh * 0.7)), mpos + wharf_dir * sdd * 1.8 + Vector(wside) * (q - 1) * 0.5 + Vector((0, 0, z0 + 0.8))],
                     [0.012, 0.012], M_ROPE, sides=3, caps=False)
    # stays between the masts
    tube(f"Stay{k}", [base + Vector(wside) * -7 + Vector((0, 0, gz(edge.x, edge.y) - 1 + h * 0.8)), base + Vector((0, 0, gz(edge.x, edge.y) - 1 + h * 0.98)),
                      base + Vector(wside) * 7 + Vector((0, 0, gz(edge.x, edge.y) - 1 + h * 0.75))], [0.015] * 3, M_ROPE, sides=3, caps=False)

# ----------------------------------------------------------------------------- the night sky: stars, the Milky Way faint, Orion rising over the harbour
def star_sky(W=4096, Hh=1024, seed=3):
    """equirectangular-ish dome texture: u = azimuth (0 at +Y, clockwise), v = elevation^0.6 mapping as the dome.
    Orion's belt, shoulders and feet placed by hand over the harbour (east-north-east of the reader's view)."""
    img = np.zeros((Hh, W, 4), np.float32); img[..., 3] = 1
    v = (np.arange(Hh) + 0.5) / Hh
    el = -8 + (89.5 + 8) * v ** (1 / 1.15)
    base = np.interp(el, [-8, 0, 6, 25, 90], [0.03, 0.06, 0.04, 0.016, 0.008])
    img[..., 0] = (base * 0.75)[:, None]; img[..., 1] = (base * 0.85)[:, None]; img[..., 2] = (base * 1.25)[:, None]
    R = np.random.RandomState(seed)
    def put(u, e, mag, col=(1, 1, 1)):
        vv = ((e + 8) / 97.5) ** 1.15
        x = u * W; y = vv * Hh
        r = 0.6 + 2.4 * mag
        xi, yi = int(x), int(y)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                xx, yy = (xi + dx) % W, yi + dy
                if 0 <= yy < Hh:
                    w = math.exp(-((dx + xi - x) ** 2 + (dy + yi - y) ** 2) / (r * r * 0.5))
                    img[yy, xx, :3] += np.array(col, np.float32) * mag * w * 1.4
    for k in range(5000):
        u = R.rand(); e = math.degrees(math.asin(R.rand()))
        if e < 2: continue
        mag = R.rand() ** 6 * 0.9 + 0.05
        # the Milky Way: a band of fainter stars
        put(u, e, mag * (0.6 + 0.4 * R.rand()), (0.9 + 0.1 * R.rand(), 0.92, 1.0))
    # Orion: centred at azimuth ~72 deg, elevation ~24 deg
    oc_u, oc_e, sc = 72 / 360.0, 24.0, 1.0
    orion = [(-1.0, 6.0, 0.95, (1.0, 0.75, 0.55)), (2.5, 5.5, 0.75, (0.9, 0.95, 1.0)),         # Betelgeuse, Bellatrix
             (-0.8, 0.4, 0.75, (0.9, 0.95, 1.0)), (0.0, 0.0, 0.75, (0.9, 0.95, 1.0)), (0.8, -0.4, 0.75, (0.9, 0.95, 1.0)),   # the belt
             (-2.2, -6.5, 0.7, (0.9, 0.95, 1.0)), (2.4, -5.8, 0.95, (0.85, 0.9, 1.0)),         # Saiph, Rigel
             (0.1, -2.5, 0.45, (0.9, 0.9, 1.0)), (0.6, 9.0, 0.4, (0.9, 0.9, 1.0))]               # the sword, the head
    for (dx, de, mag, col) in orion:
        put(oc_u + dx / 360.0, oc_e + de, mag, col)
    put(oc_u + 22 / 360.0, oc_e - 16, 1.0, (0.85, 0.9, 1.0))                                   # Sirius, low, rising
    img[..., :3] = np.clip(img[..., :3], 0, 1.5)
    return img[::-1]
SKY_R = 600.0
print("sky ...", flush=True)
sky_img = K.np_image("A_NightSky", np.clip(star_sky(), 0, 1))
M_SKY = image_mat("M_SkyDome", sky_img, rough=1.0)
mb_ = next(n for n in M_SKY.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
texn = next(n for n in M_SKY.node_tree.nodes if n.type == 'TEX_IMAGE')
M_SKY.node_tree.links.new(texn.outputs["Color"], mb_.inputs["Emission Color"]); mb_.inputs["Emission Strength"].default_value = 1.0
mb_.inputs["Base Color"].default_value = (0, 0, 0, 1)
for l in list(M_SKY.node_tree.links):
    if l.to_socket == mb_.inputs["Base Color"]: M_SKY.node_tree.links.remove(l)
SKY = E8.sky_dome("SkyDome", M_SKY, SKY_R, seg=48, rings=14, el_min=-8.0)
# the dome's UV: u round from +Y clockwise, v up -> match star_sky's mapping
me = SKY.data; uvl = me.uv_layers[0]
for li, loop in enumerate(me.loops):
    p = me.vertices[loop.vertex_index].co
    az = (math.degrees(math.atan2(p.x, p.y)) % 360.0) / 360.0
    el = math.degrees(math.asin(max(-1, min(1, p.z / SKY_R))))
    uvl.data[li].uv = (az, ((el + 8) / 97.5) ** 1.15)
# fix the seam: faces spanning u 1 -> 0
for poly in me.polygons:
    us = [uvl.data[li].uv[0] for li in poly.loop_indices]
    if max(us) - min(us) > 0.5:
        for li in poly.loop_indices:
            if uvl.data[li].uv[0] < 0.5: uvl.data[li].uv = (uvl.data[li].uv[0] + 1.0, uvl.data[li].uv[1])
texn.extension = 'REPEAT'

# ----------------------------------------------------------------------------- lights
K.apply_transforms()
MOON_DIR = (az_dir(110.0) * math.cos(math.radians(35)) + Vector((0, 0, math.sin(math.radians(35))))).normalized()
light_obj("light.moon", 'SUN', 0.16, (0.62, 0.70, 1.0), tuple(MOON_DIR * 30), direction=-MOON_DIR, angle=math.radians(8.0))
skl = light_obj("light.sky", 'SUN', 0.05, (0.45, 0.55, 0.85), (0, 0, 30), direction=(0.1, -0.2, -1.0), angle=math.radians(85))
skl.data.use_shadow = False
for k, p in enumerate(INN_LAMPS):
    light_obj(f"Lamp.inn.{k}", 'POINT', 60.0 if k < 2 else 25.0, (1.0, 0.58, 0.26), tuple(p), shadow_soft_size=0.3)
light_obj("Lamp.innspill", 'AREA', 90.0, (1.0, 0.6, 0.3), tuple(Vector(P_INN(0, -0.3, 1.2))), direction=(0, -1, -0.3), size=1.4)
light_obj("Lamp.sign", 'POINT', 8.0, (1.0, 0.6, 0.3), tuple(SIGN_C + Vector((-0.6, -0.5, -0.6))), shadow_soft_size=0.2)
light_obj("Lamp.swordfish", 'POINT', 220.0, (1.0, 0.25, 0.10), tuple(SF_LAMP), shadow_soft_size=0.5)
if CANDLE is not None: light_obj("Lamp.candle", 'POINT', 6.0, (1.0, 0.62, 0.3), tuple(CANDLE), shadow_soft_size=0.05)
world = bpy.data.worlds.new("Night"); scene.world = world
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.010, 0.013, 0.022, 1); bg.inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- markers, anchors
E8.fx("fx.lantern.porch", tuple(PORCH_LAMP), 0.05)
if CANDLE is not None: E8.fx("fx.candle.window", tuple(CANDLE), 0.02)
sound("wind", "corner", tuple(Vector(P_INN(INN_W / 2 + 0.5, -0.5, 3.0))))
sound("surf", "wharf", tuple(edge + wharf_dir * 3 + Vector((0, 0, 0.0))))
sound("rigging", "wharf", tuple(edge + wharf_dir * 10 + Vector((0, 0, 8.0))))
S.reader_anchors(0.0)
anchor("scene.centre", tuple(Vector(P_INN(0, 0, 0.15))))
anchor("inn.sign", tuple(SIGN_C))
S.check_clear(look_yaw=0.0)

EZ = gz(0, 0) + EYE
E = Vector((0, 0, EZ))
page = S.page_preview(E, 0.0)
cams = S.ring_cams(E, 0.0, extra=[
    ("Cam_Page", tuple(E), (0, 10, EZ + 0.6), 17),
    ("Cam_Sign", (SIGN_C.x + 1.6, SIGN_C.y - 3.2, EZ), tuple(SIGN_C), 35),
    ("Cam_Lane", (2.0, 5.0, EZ), (27.0, 22.0, 3.0), 22),
], pitch=4.0)
S.finish("new-bedford-spouter-corner", "new_bedford_spouter_corner", cams,
         keep_names={"M_Harbour": "water.ocean.harbour", "M_StreetIce": "GroundNear", "M_SkyDome": "SkyDome"},
         keep_uv={"M_StreetIce"},
         size_for={"M_StreetIce": (2048, 512, 1024), "M_InnBoards": (2048, 256, 1024), "M_Clapboard": (2048, 256, 1024), "M_Shingles": (1024, 128, 512),
                   "M_Snow": (1024, 64, 256), "M_Trim": (1024, 64, 256), "M_FrostGlass": (512, 128), "M_InnWindow": (256, 64), "M_RedWindow": (128, 32),
                   "M_CandleWindow": (64, 32), "M_Brick": (256, 64, 128), "M_Granite": (512, 64, 256), "M_Planks": (1024, 64, 256), "M_Iron": (64, 32),
                   "M_Spiles": (256, 64, 128), "M_Spars": (256, 32), "M_Rigging": (32,), "M_PorchInside": (256, 32), "M_Ash": (64, 32),
                   "M_SignBoard": (256, 64, 128), "M_SignPaint": (32,), "M_LampFlame": (32,)},
         page=page, default_exposure=1.0, water_colour={"M_Harbour": (0.006, 0.008, 0.012)}, unlit_emit={"M_LampFlame", "M_InnWindow", "M_RedWindow", "M_CandleWindow"})
