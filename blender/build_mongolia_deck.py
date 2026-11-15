"""
Fable: the poop-deck of the P&O steamer Mongolia in the Gulf of Aden, on a hot October afternoon in 1872 (Around the
World in Eighty Days, chapters 8-9).

"The Mongolia ... one of the fastest steamers belonging to the company ... she rapidly crossed the Red Sea ...
Passepartout ... lounged on the deck ... Meanwhile Passepartout, who had been on deck, ... The weather was hot, and
the passengers took shelter under the awning ... The Mongolia was to put in at Aden ... and she entered the Gulf of
Aden ... with the coast of Arabia on her left."

An iron screw steamer of the 1860s under way at twelve knots, sails furled, smoke from her one tall black funnel. The
reader stands under the canvas awning on the poop, a step in from the starboard rail, looking out over the starboard
bow: the open sea to the horizon ahead and to the right, the long deck, the funnel, the masts and their rigging to
the left, the awning's edge and valance framing the top of the view. Steamer chairs (one with a rug and a sola topi
left on it), the saloon skylight, life-buoys on the rail; behind, the wheel and binnacle and the red ensign streaming
aft over the wake. Far off on the port side the bare brown mountains of the Arabian coast lie in the heat haze; a
dhow's lateen sail stands on the starboard beam. No people.

Light: one high afternoon sun behind the reader's right shoulder (azimuth 160 degrees from the bow, 58 degrees up),
a pale hot hazy sky; the awning throws the reader and the page into soft shade while the deck forward is in sun.

Everything procedural (no downloaded models, textures or HDRIs). Helpers: blender/eighty_kit.py (pride_kit.py).

Node names Unity relies on:
  anchor.reader.entrance (feet, poop deck z=0), anchor.reader.look, anchor.scene.centre (the funnel's foot),
  anchor.ship.funnel, anchor.ship.mainmast, anchor.ship.wheel, anchor.ship.stern
  light.sun, light.sky (SUN)
  water.ocean.sea     the sea round the ship: its own mesh, dense near the hull (about 0.6 m) and coarser out to 150 m;
                      UV = world metres / 10; COLOR_0 G = foam (the wash along the hull, the bow wave, the wake astern
                      with its Kelvin arms)
  far.Sea (static water beyond 145 m), far.Coast (the Arabian mountains), far.Dhow, SkyDome (unlit backdrop)
  cloth.sail.awning   the awning canvas (R: 0 at the ridge and the stanchions, up to 0.3 mid-panel)
  cloth.flag.valance  the awning's scalloped side curtains (R: 0 at the top, 1 at the hem)
  cloth.flag.ensign   the red ensign at the stern (R: 0 at the staff, 1 at the fly)
  cloth.sail.furled   the sails furled on the yards and the boom (R small)
  sound.surf.side, sound.surf.wake, sound.rigging.main, sound.gulls.astern
Register as outdoor (Outdoor = true): a high hot sun, a pale hazy sky.

Axes: metres, Blender +Z up. The ship is axis-aligned: bow +Y, starboard +X, the poop deck at z=0. The reader stands
at (4.7, -31.0) and looks 27 degrees to starboard of the bow (anchor.reader.look). The water is at z = WL.

Run headless:
  blender -b -P blender/build_mongolia_deck.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_mongolia_deck.py -- --render --samples 48 --res 1400 --captures captures/blender/mongolia-deck
  blender -b -P blender/build_mongolia_deck.py -- --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
import pride_interior as I
import eighty_kit as E8
from eighty_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                        wood, noisy, plain, box, cyl, sphere, lathe, tube, sweep, mesh_from, Frame, anchor, sound, light_obj, camera,
                        link, smoothstep, lerp, add_sway, orient, interp1)

ARGS = K.setup("mongolia-deck", "out/mongolia-deck", 1865, "MongoliaDeck", default_samples=48)
OUT = K.OUT; scene = K.scene
rng = random.Random(1865)

EYE = 1.55
RX, RY = 4.7, -31.0
LOOK_YAW = math.radians(27.0)
LOOK = Vector((math.sin(LOOK_YAW), math.cos(LOOK_YAW), 0.0))
WL = -5.6
POOP_Z, MAIN_Z, FOC_Z = 0.0, -2.3, -0.3
Y_STERN, Y_BOW = -40.6, 56.0
BREAK_Y, FOC_Y = -20.0, 45.0
CAMBER = 0.10
SUN_DIR = Vector((math.sin(math.radians(160)) * math.cos(math.radians(58)), math.cos(math.radians(160)) * math.cos(math.radians(58)), math.sin(math.radians(58)))).normalized()
SKY_R = 480.0
NEAR_R = 150.0

BEAM = [(-40.6, 0.3), (-40.3, 2.0), (-39.6, 3.4), (-38.0, 4.7), (-35.0, 5.6), (-30.0, 6.1), (-22.0, 6.3), (28.0, 6.3), (36.0, 5.9),
        (42.0, 5.0), (47.0, 3.9), (51.0, 2.6), (54.0, 1.3), (56.0, 0.15)]
def beam(y): return max(0.05, interp1(BEAM, y))
def top(y):
    """the top of the hull's side: the poop deck's edge aft, the bulwark forward of the break, the foc'sle bulwark."""
    poop = POOP_Z + 0.12; main = MAIN_Z + 1.15; foc = FOC_Z + 1.0 + 0.5 * smoothstep(50, 56, y)
    z = lerp(poop, main, smoothstep(BREAK_Y - 0.3, BREAK_Y + 0.3, y))
    return lerp(z, foc, smoothstep(FOC_Y - 0.3, FOC_Y + 0.3, y))
def hb(y, z):
    """half-breadth of the hull at (y, z): wall-sided amidships, a little bilge below the water, the clipper bow raked
    forward (the stem is further aft at the waterline than at the rail)."""
    t = max(0.0, min(1.0, (top(y) - z) / (top(y) - (WL - 2.5))))
    yy = y + 4.5 * t * smoothstep(38.0, 56.0, y) - 0.8 * t * smoothstep(-34.0, -40.6, y)
    return beam(yy) * (1.0 - 0.10 * smoothstep(WL + 0.5, WL - 2.5, z))
def deck_z(x, y, base):
    w = max(0.3, hb(y, base)); return base + CAMBER * (1.0 - min(1.0, (x / w) ** 2))

# ============================================================================= materials
def paint_mat(name, color, rough=0.45, grime=0.15, streaks=0.0, scale=1.0):
    """ship's paint: a soft gloss, brush texture, grime in the corners, salt and rust streaks running down."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1600, -300))
    n = noise_(nt, co, 2.0 * scale, 5, 0.6, loc=(-1200, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, c4(color), maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.93, 1.04, (-1000, 0)), (-800, 0))
    if streaks:
        mp = node(nt, "ShaderNodeMapping", (-1400, -500)); mp.inputs["Scale"].default_value = (3.0, 3.0, 0.15); nt.links.new(co, mp.inputs["Vector"])
        sn = noise_(nt, mp.outputs["Vector"], 4.0, 4, 0.55, loc=(-1200, -500))
        st = maprange(nt, sn.outputs["Fac"], 0.6, 0.75, 0, streaks, (-1000, -500))
        col = mix_rgb(nt, 'MIX', st, col, (0.20, 0.09, 0.04, 1), (-600, 0))
    col = K.ao_mul(nt, col, 0.3, grime, (-400, -700))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.7, rough - 0.08, rough + 0.1, (-400, -200)), b.inputs["Roughness"])
    fine = noise_(nt, co, 80.0, 3, 0.6, loc=(-1200, -900))
    bump_from(nt, b, fine.outputs["Fac"], 0.06, 0.001)
    return m

def hull_mat(name="M_HullPaint"):
    """black topsides, a gilt cove line under the rail, salt bloom and rust weeping from the ports and chain plates, a
    red-brown boot-top at the waterline, wet and darker in the last half metre."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1600, 0)); z = s.outputs["Z"]
    n = noise_(nt, co, 0.6, 5, 0.6, loc=(-1300, 300))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0, 1, (-1100, 300)), (0.018, 0.018, 0.02, 1), (0.04, 0.038, 0.037, 1), (-900, 300))
    mp = node(nt, "ShaderNodeMapping", (-1400, -300)); mp.inputs["Scale"].default_value = (2.5, 2.5, 0.12); nt.links.new(co, mp.inputs["Vector"])
    sn = noise_(nt, mp.outputs["Vector"], 3.0, 4, 0.55, loc=(-1200, -300))
    col = mix_rgb(nt, 'MIX', maprange(nt, sn.outputs["Fac"], 0.6, 0.74, 0, 0.45, (-1000, -300)), col, (0.22, 0.21, 0.19, 1), (-750, 300))
    rn = noise_(nt, mp.outputs["Vector"], 5.0, 4, 0.55, loc=(-1200, -550))
    col = mix_rgb(nt, 'MIX', maprange(nt, rn.outputs["Fac"], 0.66, 0.76, 0, 0.5, (-1000, -550)), col, (0.13, 0.05, 0.02, 1), (-650, 300))
    boot = maprange(nt, z, WL + 0.45, WL + 0.4, 0, 1, (-1000, -800))
    col = mix_rgb(nt, 'MIX', boot, col, (0.16, 0.04, 0.025, 1), (-500, 300))
    nt.links.new(K.ao_mul(nt, col, 0.3, 0.3, (-350, -900)), b.inputs["Base Color"])
    wet = maprange(nt, z, WL + 0.8, WL + 0.1, 0.42, 0.15, (-500, -300))
    nt.links.new(wet, b.inputs["Roughness"])
    bump_from(nt, b, n.outputs["Fac"], 0.1, 0.01)
    return m

def canvas_mat(name, base=(0.80, 0.78, 0.71), seams_axis='X', seam_pitch=0.61):
    """cotton duck awning: off-white, cloth widths sewn together (darker seam lines), weathered and water-marked."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1600, 0))
    ax = s.outputs[seams_axis]
    fr = math_(nt, 'FRACT', math_(nt, 'DIVIDE', ax, seam_pitch, (-1400, 200)), None, (-1300, 200))
    seam = maprange(nt, math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', fr, 0.5, (-1200, 200)), None, (-1100, 200)), 0.47, 0.49, 0, 1, (-1000, 200))
    n = noise_(nt, co, 1.2, 6, 0.6, loc=(-1300, -100))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, c4(base), maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.86, 1.03, (-1000, -100)), (-800, 0))
    col = mix_rgb(nt, 'MULTIPLY', math_(nt, 'MULTIPLY', seam, 0.25, (-900, 200)), col, (0.55, 0.52, 0.46, 1), (-600, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
    b.inputs["Sheen Weight"].default_value = 0.3
    wv = noise_(nt, co, 300.0, 2, 0.5, loc=(-1200, -500))
    bump_from(nt, b, math_(nt, 'ADD', wv.outputs["Fac"], seam, (-900, -500)), 0.15, 0.001)
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    tr = node(nt, "ShaderNodeBsdfTranslucent", (300, -250)); nt.links.new(col, tr.inputs["Color"])
    mx = node(nt, "ShaderNodeMixShader", (500, -100)); mx.inputs["Fac"].default_value = 0.18
    nt.links.new(b.outputs["BSDF"], mx.inputs[1]); nt.links.new(tr.outputs["BSDF"], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m

def ensign_mat(name="M_Ensign"):
    """the red ensign (world coords on the flag at rest: u = fly from the staff along -Y, v = up from the foot): red
    field, the Union in the canton: blue, white saltire, red cross with its white fimbriation."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1800, 0))
    u = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', s.outputs["Y"], ENS_Y, (-1600, 100)), -1.0, (-1500, 100))
    v = math_(nt, 'SUBTRACT', s.outputs["Z"], ENS_Z0, (-1600, -100))
    cw, chh = ENS_W / 2, ENS_H / 2
    inc = math_(nt, 'MULTIPLY', maprange(nt, u, cw - 0.005, cw, 1, 0, (-1300, 300)), maprange(nt, v, chh, chh + 0.005, 0, 1, (-1300, 200)), (-1150, 250))
    cu = math_(nt, 'SUBTRACT', u, cw / 2, (-1300, 0)); cv = math_(nt, 'SUBTRACT', v, chh * 1.5, (-1300, -100))
    acu = math_(nt, 'ABSOLUTE', cu, None, (-1200, 0)); acv = math_(nt, 'ABSOLUTE', cv, None, (-1200, -100))
    # saltire: |cu/cw*chh| ~ |cv|
    d1 = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', acu, chh / cw, (-1100, -200)), acv, (-1000, -200)), None, (-900, -200))
    salt = maprange(nt, d1, 0.03, 0.025, 0, 1, (-800, -200))
    cross_w = math_(nt, 'MAXIMUM', maprange(nt, acu, 0.06, 0.055, 0, 1, (-1000, -400)), maprange(nt, acv, 0.06, 0.055, 0, 1, (-1000, -500)), (-850, -450))
    cross_r = math_(nt, 'MAXIMUM', maprange(nt, acu, 0.036, 0.031, 0, 1, (-1000, -600)), maprange(nt, acv, 0.036, 0.031, 0, 1, (-1000, -700)), (-850, -650))
    red = (0.42, 0.03, 0.03, 1)
    can = mix_rgb(nt, 'MIX', salt, (0.02, 0.04, 0.16, 1), (0.82, 0.80, 0.76, 1), (-700, -200))
    can = mix_rgb(nt, 'MIX', cross_w, can, (0.82, 0.80, 0.76, 1), (-600, -300))
    can = mix_rgb(nt, 'MIX', cross_r, can, red, (-500, -400))
    col = mix_rgb(nt, 'MIX', inc, red, can, (-300, 0))
    n = noise_(nt, co, 4.0, 4, 0.6, loc=(-800, 300))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.85, 1.05, (-400, 300)), (-150, 0))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85; b.inputs["Sheen Weight"].default_value = 0.4
    return m

def sky_mat(name="M_SkyDome"):
    """a hot afternoon over the Gulf of Aden: a pale, dusty white-blue haze along the horizon, deepening to a soft blue
    overhead, thin high cirrus, the sun's glare behind the reader (no disc in view)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt, (-2400, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-2200, 0), operation='NORMALIZE'); nt.links.new(co, nv.inputs[0]); d = nv.outputs[0]
    s = sep_xyz(nt, d, (-2000, 0)); el = s.outputs["Z"]
    base = ramp(nt, [(0.0, c4((0.62, 0.62, 0.60))), (0.10, c4((0.80, 0.80, 0.78))), (0.16, c4((0.70, 0.75, 0.80))), (0.35, c4((0.45, 0.58, 0.78))),
                     (0.7, c4((0.30, 0.46, 0.74))), (1.0, c4((0.24, 0.40, 0.70)))], (-1500, 400))
    nt.links.new(maprange(nt, el, -0.1, 1.0, 0, 1, (-1700, 400)), base.inputs["Fac"])
    col = base.outputs["Color"]
    zk = math_(nt, 'ADD', math_(nt, 'MAXIMUM', el, 0.0, (-1800, -200)), 0.08, (-1650, -200))
    px = math_(nt, 'DIVIDE', s.outputs["X"], zk, (-1500, -150)); py = math_(nt, 'DIVIDE', s.outputs["Y"], zk, (-1500, -300))
    cv = node(nt, "ShaderNodeCombineXYZ", (-1350, -200)); nt.links.new(px, cv.inputs["X"]); nt.links.new(py, cv.inputs["Y"])
    mp = node(nt, "ShaderNodeMapping", (-1200, -200)); mp.inputs["Scale"].default_value = (0.25, 1.4, 1); mp.inputs["Rotation"].default_value = (0, 0, 0.5)
    nt.links.new(cv.outputs[0], mp.inputs["Vector"])
    cl = noise_(nt, mp.outputs["Vector"], 0.9, 8, 0.62, 0.8, (-1000, -200))
    cr = maprange(nt, cl.outputs["Fac"], 0.55, 0.75, 0.0, 0.35, (-800, -200))
    cmask = maprange(nt, el, 0.1, 0.4, 0.0, 1.0, (-800, -400))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', cr, cmask, (-600, -300)), col, (0.86, 0.87, 0.88, 1), (-400, 200))
    sd = node(nt, "ShaderNodeVectorMath", (-1700, 800), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(SUN_DIR); nt.links.new(d, sd.inputs[0])
    glow = math_(nt, 'POWER', maprange(nt, sd.outputs["Value"], 0.4, 1.0, 0, 1, (-1500, 800)), 3.0, (-1350, 800))
    col = mix_rgb(nt, 'ADD', math_(nt, 'MULTIPLY', glow, 0.5, (-1200, 850)), col, (1.0, 0.95, 0.85, 1), (-200, 300))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m

def water_mat(name="M_Sea"):
    """Blender preview only: deep blue open water with a small wind chop and foam from the vertex colour G. The export
    replaces it with a plain colour; Unity's water material does the moving surface."""
    m, nt, b = new_mat(name)
    b.inputs["Roughness"].default_value = 0.06; b.inputs["IOR"].default_value = 1.33
    co = obj_coords(nt)
    sm = node(nt, "ShaderNodeMapping", (-1200, -300)); sm.inputs["Scale"].default_value = (1.0, 1.8, 1.0); sm.inputs["Rotation"].default_value = (0, 0, 0.4)
    nt.links.new(co, sm.inputs["Vector"])
    r1 = noise_(nt, sm.outputs["Vector"], 0.9, 6, 0.6, loc=(-1000, -300))
    r2 = noise_(nt, co, 0.08, 3, 0.5, loc=(-1000, -500))
    bump_from(nt, b, mix_f(nt, 0.4, r1.outputs["Fac"], r2.outputs["Fac"], (-600, -400)), 0.5, 0.25)
    ca = node(nt, "ShaderNodeVertexColor", (-1000, 500)); ca.layer_name = "Col"
    sp = node(nt, "ShaderNodeSeparateColor", (-800, 500)); nt.links.new(ca.outputs["Color"], sp.inputs["Color"])
    fn = noise_(nt, co, 1.6, 5, 0.65, loc=(-1000, 700))
    foam = math_(nt, 'MULTIPLY', sp.outputs["Green"], maprange(nt, fn.outputs["Fac"], 0.35, 0.6, 0.15, 1.0, (-800, 700)), (-600, 600))
    col = mix_rgb(nt, 'MIX', foam, (0.006, 0.030, 0.060, 1), (0.62, 0.66, 0.66, 1), (-300, 300))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, foam, 0.06, 0.6, (-300, 0)), b.inputs["Roughness"])
    return m

M_HULL = hull_mat()
M_DECK = I.boards_mat("M_DeckPlanks", light=(0.48, 0.41, 0.31), dark=(0.41, 0.34, 0.25), width=0.14, axis='Y', wax=0.62)
M_TEAK = noisy("M_Teak", [(0.20, 0.11, 0.05), (0.28, 0.16, 0.075), (0.34, 0.20, 0.10)], scale=9.0, rough=(0.3, 0.5), bump=0.15, bump_dist=0.001, stretch=(6.0, 0.4, 6.0), coat=0.25, ao=0.3)
M_WHITE = paint_mat("M_WhitePaint", (0.72, 0.70, 0.64), rough=0.42, grime=0.25, streaks=0.25)
M_STONE = paint_mat("M_StonePaint", (0.55, 0.47, 0.34), rough=0.45, grime=0.25)
M_BLACK = paint_mat("M_BlackPaint", (0.025, 0.024, 0.023), rough=0.4, grime=0.1, streaks=0.2)
M_SPAR = wood("M_Spar", base=(0.36, 0.25, 0.14), dark=(0.16, 0.10, 0.05), light=(0.48, 0.36, 0.22), scale=0.6, rough=(0.4, 0.65), grain_dir=(10, 10, 1), bands='Z', coat=0.15, ao=0.3, bump=0.1)
M_ROPE = noisy("M_TarredRope", [(0.018, 0.015, 0.012), (0.035, 0.03, 0.023), (0.05, 0.043, 0.033)], scale=60, rough=0.75, bump=0.4, bump_dist=0.002)
M_MANILA = noisy("M_ManilaRope", [(0.28, 0.22, 0.14), (0.36, 0.29, 0.19), (0.44, 0.36, 0.24)], scale=50, rough=0.9, bump=0.5, bump_dist=0.002)
M_SAIL = canvas_mat("M_Sail", base=(0.66, 0.63, 0.55))
M_COVER = canvas_mat("M_BoatCover", base=(0.58, 0.57, 0.52))
M_AWNING = canvas_mat("M_Awning", base=(0.72, 0.70, 0.63), seams_axis='Y', seam_pitch=0.61)
M_VALANCE = canvas_mat("M_Valance", base=(0.70, 0.68, 0.61), seams_axis='Z', seam_pitch=9.0)
M_BRASS = plain("M_Brass", (0.75, 0.56, 0.28), rough=0.22, metallic=1.0)
M_IRON = noisy("M_Iron", [(0.03, 0.03, 0.03), (0.05, 0.048, 0.045), (0.04, 0.035, 0.03)], scale=25, rough=(0.45, 0.7), metallic=0.4)
M_GLASS = plain("M_SkylightGlass", (0.55, 0.62, 0.60), rough=0.05, transmission=0.6)
M_DARK = plain("M_DarkPorts", (0.015, 0.018, 0.02), rough=0.15)
M_CANE = noisy("M_Cane", [K.srgb((0.62, 0.50, 0.30)), K.srgb((0.70, 0.58, 0.36)), K.srgb((0.55, 0.43, 0.25))], scale=120, rough=0.6, bump=0.4, bump_dist=0.0015)
M_RUG = I.silk("M_TravelRug", K.srgb((0.20, 0.30, 0.22)), K.srgb((0.45, 0.12, 0.08)), stripes=1.0, stripe_w=0.05, axis='X', sheen=0.3, rough=0.9)
M_TOPI = noisy("M_Topi", [K.srgb((0.82, 0.78, 0.66)), K.srgb((0.76, 0.72, 0.60))], scale=40, rough=0.8, bump=0.1)
M_BUOY = plain("M_LifeBuoy", K.srgb((0.82, 0.80, 0.74)), rough=0.6)
M_RED = plain("M_RedPaint", K.srgb((0.55, 0.08, 0.05)), rough=0.5)
M_SEA = water_mat()
M_FARSEA = plain("M_FarSea", (0.008, 0.036, 0.070), rough=0.12)
M_COAST = noisy("M_FarCoast", [(0.17, 0.15, 0.14), (0.21, 0.19, 0.18), (0.25, 0.23, 0.22)], scale=0.05, rough=1.0, bump=0.0)
M_DHOW = noisy("M_FarDhow", [(0.30, 0.24, 0.17), (0.62, 0.58, 0.50), (0.70, 0.66, 0.58)], scale=0.6, rough=0.9, bump=0.0)
M_SKY = sky_mat()

# ============================================================================= the hull, decks, bulwarks and rails
def hull():
    ys = sorted(set([lerp(Y_STERN + 0.02, Y_BOW - 0.02, (1 - math.cos(math.pi * i / 80)) / 2) for i in range(81)] +
                    [BREAK_Y + d for d in (-0.5, -0.3, -0.1, 0.1, 0.3, 0.5)] + [FOC_Y + d for d in (-0.5, -0.3, -0.1, 0.1, 0.3, 0.5)]))
    NZ = 9
    for side in (1, -1):
        verts = []; faces = []
        for y in ys:
            t0 = top(y); zb = WL - 2.0
            for j in range(NZ + 1):
                z = lerp(zb, t0, (j / NZ) ** 0.8)
                verts.append((side * max(0.02, hb(y, z)), y, z))
        for i in range(len(ys) - 1):
            for j in range(NZ):
                a = i * (NZ + 1) + j; b2 = a + NZ + 1
                faces.append((a, a + 1, b2 + 1, b2))
        o = mesh_from(f"Hull{side}", verts, faces, M_HULL, smooth=True)
        orient(o, lambda c, side=side: (side, 0.0, 0.0) if abs(c.x) > 0.3 else (0.0, 1.0 if c.y > 0 else -1.0, 0.0))
    # a gilt cove line under the rail and a row of side lights (ports)
    for side in (1, -1):
        pts = [Vector((side * (hb(y, top(y) - 0.35) + 0.012), y, top(y) - 0.35)) for y in np.linspace(Y_STERN + 1.2, Y_BOW - 2.5, 70)]
        tube(f"CoveLine{side}", pts, 0.015, plain("M_CoveGilt", (0.62, 0.46, 0.18), rough=0.35, metallic=1.0) if side > 0 else bpy.data.materials["M_CoveGilt"], sides=4, caps=False)
        for y in np.arange(-38.0, 42.0, 3.2):
            if abs(y - BREAK_Y) < 1.0: continue
            zp = (POOP_Z - 1.4) if y < BREAK_Y else (MAIN_Z - 1.2)
            cyl(f"Port{side}_{y:.1f}", 0.15, 0.06, (side * (hb(y, zp) + 0.0), y, zp), M_DARK, verts=8, rot=(0, math.pi / 2, 0), smooth=False)
hull()

def deck(name, y0, y1, base, NY, NX=12, inset=0.07):
    verts = []; faces = []
    ys = [lerp(y0, y1, i / NY) for i in range(NY + 1)]
    for y in ys:
        w = max(0.05, hb(y, base) - inset)
        for i in range(NX + 1):
            x = lerp(-w, w, i / NX)
            verts.append((x, y, deck_z(x, y, base) + 0.006 * noise.noise(Vector((x * 0.7, y * 0.3, 1.7)))))
    for j in range(NY):
        for i in range(NX):
            a = j * (NX + 1) + i; faces.append((a, a + 1, a + NX + 2, a + NX + 1))
    return orient(mesh_from(name, verts, faces, M_DECK, smooth=True), lambda c: (0, 0, 1))
deck("PoopDeck", Y_STERN + 0.15, BREAK_Y, POOP_Z, 30)
deck("MainDeck", BREAK_Y - 0.05, FOC_Y + 0.05, MAIN_Z, 40)
deck("FocsleDeck", FOC_Y, Y_BOW - 0.4, FOC_Z, 10)

# the break of the poop: a panelled bulkhead with the saloon doors, two ladders down to the main deck
wb = hb(BREAK_Y, POOP_Z)
box("PoopBreak", (2 * wb - 0.1, 0.12, POOP_Z - MAIN_Z + 0.02), (0, BREAK_Y - 0.06, (POOP_Z + MAIN_Z) / 2), M_WHITE)
for k, x in enumerate((-2.2, 2.2)):
    box(f"SaloonDoor{k}", (0.9, 0.04, 1.95), (x, BREAK_Y + 0.01, MAIN_Z + 0.975), M_TEAK, bevel=0.01)
for k, x in enumerate((-4.6, -3.4, 3.4, 4.6)):
    box(f"BreakWindow{k}", (0.55, 0.03, 0.55), (x, BREAK_Y + 0.01, MAIN_Z + 1.35), M_DARK)
    box(f"BreakWindowFrame{k}", (0.65, 0.025, 0.65), (x, BREAK_Y + 0.005, MAIN_Z + 1.35), M_TEAK)
for k, x in enumerate((-5.2, 5.2)):
    for sx in (-1, 1):
        box(f"Ladder{k}Stringer{sx}", (0.06, 0.14, 3.0), (x + sx * 0.32, BREAK_Y + 0.8, (MAIN_Z + POOP_Z) / 2), M_TEAK, rot=(math.radians(-50), 0, 0))
    for j in range(8):
        t = (j + 0.5) / 8
        box(f"Ladder{k}Tread{j}", (0.6, 0.18, 0.03), (x, BREAK_Y + 1.6 - t * 1.75, MAIN_Z + t * (POOP_Z - MAIN_Z)), M_TEAK)
# the foc'sle bulkhead
box("FocsleBreak", (2 * hb(FOC_Y, FOC_Z) - 0.1, 0.12, FOC_Z - MAIN_Z), (0, FOC_Y + 0.06, (FOC_Z + MAIN_Z) / 2), M_WHITE)

def bulwark_inner(y0, y1, zlo, NY=40, tag="Main"):
    for side in (1, -1):
        verts = []; faces = []
        ys = [lerp(y0, y1, i / NY) for i in range(NY + 1)]
        for y in ys:
            for z in (zlo, top(y) - 0.04):
                verts.append((side * (hb(y, z) - 0.08), y, z))
        for i in range(NY):
            a = 2 * i; faces.append((a, a + 2, a + 3, a + 1))
        orient(mesh_from(f"Bulwark{tag}{side}", verts, faces, M_WHITE), lambda c: (-c.x, 0, 0))
        pts = [Vector((side * (hb(y, top(y)) - 0.06), y, top(y) + 0.03)) for y in ys[::2]]
        sweep(f"BulwarkRail{tag}{side}", [(-0.09, 0.0), (0.09, 0.0), (0.09, 0.06), (-0.09, 0.06)], pts if side < 0 else pts[::-1], M_TEAK, cap=True)
        y = y0 + 0.8
        while y < y1 - 0.4:
            box(f"BulwarkStay{tag}{side}_{y:.1f}", (0.06, 0.12, top(y) - zlo - 0.1), (side * (hb(y, zlo + 0.5) - 0.13), y, (zlo + top(y)) / 2 - 0.05), M_WHITE)
            y += 1.9
bulwark_inner(BREAK_Y + 0.05, FOC_Y - 0.05, MAIN_Z, NY=44, tag="Main")
bulwark_inner(FOC_Y + 0.1, Y_BOW - 1.2, FOC_Z, NY=10, tag="Foc")

# the poop's open rail: teak cap rail on turned iron stanchions with two rails of iron rod, round the stern
def poop_outline():
    pts = []
    for y in np.linspace(BREAK_Y + 0.05, Y_STERN + 2.2, 26):
        pts.append(Vector((hb(y, POOP_Z) - 0.09, y, 0)))
    for k in range(1, 12):
        a = math.pi / 2 * (1 - k / 12)
        ye = Y_STERN + 2.2
        pts.append(Vector((math.sin(a) * (hb(ye, POOP_Z) - 0.09), ye - math.cos(a) * 1.75, 0)))
    pts.append(Vector((0, Y_STERN + 0.45, 0)))
    full = pts + [Vector((-p.x, p.y, 0)) for p in reversed(pts[:-1])]
    return full
OUTL = poop_outline()
def at_z(pts, z): return [Vector((p.x, p.y, z)) for p in pts]
sweep("PoopRailCap", [(-0.07, 0.0), (0.07, 0.0), (0.075, 0.03), (0.06, 0.065), (-0.06, 0.065), (-0.075, 0.03)], at_z(OUTL, POOP_Z + 1.0), M_TEAK, cap=True)
for zr in (0.38, 0.70):
    sweep(f"PoopRailRod{zr}", [(-0.012, -0.012), (0.012, -0.012), (0.012, 0.012), (-0.012, 0.012)], at_z(OUTL, POOP_Z + zr), M_IRON, cap=True)
acc = 0.0; last = OUTL[0]; k = 0
STANCH = []
for p in OUTL:
    acc += (p - last).length; last = p
    if acc >= 1.25 or k == 0:
        acc = 0.0
        lathe(f"Stanchion{k}", [(0.0, 0.0), (0.04, 0.0), (0.035, 0.03), (0.02, 0.06), (0.018, 0.5), (0.026, 0.55), (0.018, 0.6), (0.016, 1.0), (0.0, 1.0)], (p.x, p.y, deck_z(p.x, p.y, POOP_Z) - 0.01), M_IRON, steps=6)
        STANCH.append(p); k += 1
# the rail across the break of the poop, open at the ladders
for (x0, x1) in ((-wb + 0.1, -5.7), (-4.7, 4.7), (5.7, wb - 0.1)):
    sweep(f"BreakRail{x0:.1f}", [(-0.07, 0.0), (0.07, 0.0), (0.07, 0.06), (-0.07, 0.06)], [Vector((x1, BREAK_Y + 0.02, POOP_Z + 1.0)), Vector((x0, BREAK_Y + 0.02, POOP_Z + 1.0))], M_TEAK, cap=True)
    for zr in (0.38, 0.70):
        tube(f"BreakRod{x0:.1f}{zr}", [Vector((x0, BREAK_Y + 0.02, zr)), Vector((x1, BREAK_Y + 0.02, zr))], 0.012, M_IRON, sides=4)
    for x in np.linspace(x0, x1, max(2, int((x1 - x0) / 1.2) + 1)):
        cyl(f"BreakStanchion{x:.1f}", 0.02, 1.0, (x, BREAK_Y + 0.02, 0.5), M_IRON, verts=6)

# ============================================================================= deck furniture on the poop
# the saloon skylight: a teak coaming, two pitched glazed lights with brass guard bars
SK = Vector((0.0, -28.5, 0))
box("SkylightCoaming", (1.7, 3.2, 0.55), (SK.x, SK.y, deck_z(0, SK.y, 0) + 0.27), M_TEAK, bevel=0.02)
z_rim = deck_z(0, SK.y, 0) + 0.55
for sx in (-1, 1):
    q = [(SK.x, SK.y - 1.5, 0.93), (SK.x, SK.y + 1.5, 0.93), (SK.x + sx * 0.8, SK.y + 1.5, z_rim), (SK.x + sx * 0.8, SK.y - 1.5, z_rim)]
    orient(mesh_from(f"SkylightGlass{sx}", q, [(0, 1, 2, 3)], M_GLASS), lambda c: (0, 0, 1))
    for j in range(7):
        tube(f"SkylightBar{sx}{j}", [Vector((SK.x + sx * 0.05, SK.y - 1.4 + j * 0.467, 0.95)), Vector((SK.x + sx * 0.8, SK.y - 1.4 + j * 0.467, z_rim + 0.02))], 0.009, M_BRASS, sides=4)
    for k, yy in enumerate((SK.y - 1.55, SK.y + 1.55)):
        mesh_from(f"SkylightGable{sx}{k}", [(SK.x, yy, 0.93), (SK.x + sx * 0.82, yy, z_rim), (SK.x, yy, z_rim)], [(0, 1, 2)], M_TEAK)
box("SkylightRidge", (0.1, 3.2, 0.06), (SK.x, SK.y, 0.93), M_TEAK)
# the companion to the saloon: a small house with a sliding hatch and a door, port side of the skylight
box("Companion", (1.3, 1.5, 1.85), (-2.6, -24.0, 0.925), M_TEAK, bevel=0.02)
box("CompanionHatch", (1.4, 1.6, 0.08), (-2.6, -24.0, 1.88), M_TEAK, bevel=0.02)
box("CompanionDoor", (0.7, 0.04, 1.6), (-2.6, -23.24, 0.85), M_TEAK, bevel=0.015)
sphere("CompanionKnob", 0.025, (-2.35, -23.21, 0.9), M_BRASS, seg=8)

# the wheel and the binnacle aft
WH = Vector((0.0, -37.4, 0))
box("WheelBox", (1.0, 0.6, 0.85), (WH.x, WH.y - 0.35, 0.42), M_TEAK, bevel=0.02)
for sx in (-1, 1):
    box(f"WheelStand{sx}", (0.08, 0.15, 1.35), (WH.x + sx * 0.35, WH.y + 0.05, 0.67), M_TEAK, bevel=0.01)
cyl("WheelAxle", 0.04, 0.9, (WH.x, WH.y + 0.05, 1.2), M_BRASS, verts=8, rot=(0, math.pi / 2, 0))
WF = Frame((WH.x, WH.y + 0.25), 0.0)
bpy.ops.mesh.primitive_torus_add(major_radius=0.62, minor_radius=0.03, major_segments=28, minor_segments=6, location=(WH.x, WH.y + 0.25, 1.2), rotation=(math.pi / 2, 0, 0))
rim = bpy.context.active_object; rim.name = "WheelRim"; K._finish(rim, M_TEAK, smooth=True)
cyl("WheelHub", 0.1, 0.12, (WH.x, WH.y + 0.25, 1.2), M_BRASS, verts=12, rot=(math.pi / 2, 0, 0))
for k in range(8):
    a = 2 * math.pi * k / 8
    d = Vector((math.cos(a), 0, math.sin(a)))
    c0 = Vector((WH.x, WH.y + 0.25, 1.2))
    lathe(f"WheelSpoke{k}", [(0.0, 0.0), (0.022, 0.0), (0.03, 0.15), (0.02, 0.4), (0.03, 0.55), (0.022, 0.75), (0.0, 0.8)], tuple(c0), M_TEAK, steps=6,
          rot=Vector((0, 0, 1)).rotation_difference(d).to_euler())
lathe("Binnacle", [(0.0, 0.0), (0.22, 0.0), (0.2, 0.08), (0.14, 0.15), (0.13, 0.9), (0.2, 0.95), (0.24, 1.05), (0.2, 1.22), (0.1, 1.32), (0.0, 1.34)], (0.0, -35.8, 0.0), M_BRASS, steps=16)
for sx in (-1, 1):
    sphere(f"BinnacleBall{sx}", 0.09, (sx * 0.38, -35.8, 1.05), M_IRON if sx < 0 else plain("M_GreenBall", (0.05, 0.16, 0.06), rough=0.3), seg=12)
# the ensign staff and the red ensign at the stern, streaming aft
ENS_Y, ENS_Z0, ENS_W, ENS_H = Y_STERN + 0.55, 3.3, 1.9, 0.95
cyl("EnsignStaff", 0.03, 4.5, (0.0, ENS_Y, 2.25), M_TEAK, verts=8, r2=0.02)
sphere("EnsignTruck", 0.05, (0.0, ENS_Y, 4.52), M_BRASS, seg=8)
def ensign():
    nu, nv = 14, 6; verts = []; faces = []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u = i / nu; v = j / nv
            y = ENS_Y - u * ENS_W
            x = 0.12 * math.sin(u * 5.0 + v * 0.8) * u
            z = ENS_Z0 + v * ENS_H - 0.18 * u * u
            verts.append((x, y, z))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i; faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    o = mesh_from("Ensign", verts, faces, None if False else M_ENSIGN, smooth=True)
    return o
M_ENSIGN = ensign_mat()
ENS = ensign()
tube("EnsignHalyard", [Vector((0.03, ENS_Y, 4.45)), Vector((0.03, ENS_Y, 1.0))], 0.005, M_MANILA, sides=3)

# life-buoys on the rail
def buoy(name, p, yaw):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.32, minor_radius=0.07, major_segments=20, minor_segments=8, location=p, rotation=(math.pi / 2, 0, yaw))
    o = bpy.context.active_object; o.name = name; K._finish(o, M_BUOY, smooth=True)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        q = Vector(p) + Matrix.Rotation(yaw, 3, 'Z') @ Vector((math.cos(a) * 0.32, 0, math.sin(a) * 0.32))
        cyl(f"{name}Band{k}", 0.08, 0.1, tuple(q), M_RED, verts=10, rot=(0, -a, yaw))
buoy("BuoyStbd", (hb(-25.5, 0) - 0.16, -25.5, 0.72), math.pi / 2)
buoy("BuoyStern", (2.6, Y_STERN + 1.25, 0.72), -0.55)

# steamer chairs: teak frames with cane seats, backs raked, the leg rests out
def steamer_chair(name, x, y, yaw, rake=0.62):
    F = Frame((x, y), yaw)
    W = 0.56
    for sx in (-1, 1):
        # side frame: leg rest (front), seat, back, as one bent bar per side
        pts = [Vector(F.p(sx * W / 2, 0.95, 0.22)), Vector(F.p(sx * W / 2, 0.45, 0.36)), Vector(F.p(sx * W / 2, -0.05, 0.36)),
               Vector(F.p(sx * W / 2, -0.05 - 0.75 * math.sin(rake), 0.36 + 0.75 * math.cos(rake)))]
        tube(f"{name}Side{sx}", pts, 0.022, M_TEAK, sides=5)
        for (ly, lz) in ((0.85, 0.2), (0.35, 0.34), (-0.2, 0.34)):
            tube(f"{name}Leg{sx}{ly}", [Vector(F.p(sx * W / 2, ly, lz)), Vector(F.p(sx * W / 2, ly + 0.05, 0.0))], 0.02, M_TEAK, sides=5)
        tube(f"{name}Arm{sx}", [Vector(F.p(sx * (W / 2 + 0.03), -0.25, 0.62)), Vector(F.p(sx * (W / 2 + 0.03), 0.38, 0.6)), Vector(F.p(sx * (W / 2 + 0.03), 0.38, 0.36))], 0.018, M_TEAK, sides=5)
    # cane panels
    seat = [F.p(-W / 2, 0.45, 0.37), F.p(W / 2, 0.45, 0.37), F.p(W / 2, -0.05, 0.37), F.p(-W / 2, -0.05, 0.37)]
    rest = [F.p(-W / 2, 0.93, 0.24), F.p(W / 2, 0.93, 0.24), F.p(W / 2, 0.45, 0.37), F.p(-W / 2, 0.45, 0.37)]
    back = [F.p(-W / 2, -0.05, 0.38), F.p(W / 2, -0.05, 0.38), F.p(W / 2, -0.05 - 0.72 * math.sin(rake), 0.38 + 0.72 * math.cos(rake)), F.p(-W / 2, -0.05 - 0.72 * math.sin(rake), 0.38 + 0.72 * math.cos(rake))]
    for k, q in enumerate((seat, rest, back)):
        o = mesh_from(f"{name}Cane{k}", q, [(0, 1, 2, 3)], M_CANE)
        o.modifiers.new("Solid", 'SOLIDIFY').thickness = 0.012
    for zz, yy in ((0.37, 0.45), (0.37, -0.05), (0.24, 0.93)):
        tube(f"{name}Rung{yy}", [Vector(F.p(-W / 2, yy, zz)), Vector(F.p(W / 2, yy, zz))], 0.016, M_TEAK, sides=5)
    return F
C1 = steamer_chair("ChairA", 2.7, -26.9, math.radians(-100))
C2 = steamer_chair("ChairB", 2.9, -24.6, math.radians(-80))
C3 = steamer_chair("ChairC", 2.0, -34.2, math.radians(-70))
C4 = steamer_chair("ChairD", -3.3, -29.0, math.radians(95))
# a travelling rug thrown over chair B and a sola topi on its seat; a book face down on chair A
rug = []
for j in range(7):
    for i in range(9):
        u = i / 8; v = j / 6
        p = Vector(C2.p(lerp(-0.34, 0.34, u), lerp(0.55, -0.35, v), 0.0))
        zz = 0.40 + 0.03 * math.sin(u * 9 + v * 4) + (0.3 * max(0, -0.05 - lerp(0.55, -0.35, v)) * 1.2 if lerp(0.55, -0.35, v) < -0.05 else 0)
        if abs(lerp(-0.34, 0.34, u)) > 0.29: zz -= 0.12 * (abs(lerp(-0.34, 0.34, u)) - 0.29) / 0.05
        rug.append((p.x, p.y, zz))
faces = [(j * 9 + i, j * 9 + i + 1, (j + 1) * 9 + i + 1, (j + 1) * 9 + i) for j in range(6) for i in range(8)]
mesh_from("Rug", rug, faces, M_RUG, smooth=True)
tp = Vector(C2.p(0.0, 0.25, 0.47))
sphere("TopiCrown", 0.16, tuple(tp + Vector((0, 0, 0.04))), M_TOPI, seg=14, scale=(1.0, 1.2, 0.75))
cyl("TopiBrim", 0.24, 0.012, tuple(tp), M_TOPI, verts=20)
I.book("BookOnChair", tuple(Vector(C1.p(0.02, 0.2, 0.39))), (0.025, 0.13, 0.19), C1.yaw + 0.4, plain("M_BookCloth", K.srgb((0.30, 0.12, 0.08)), rough=0.6),
       plain("M_BookPages", K.srgb((0.82, 0.78, 0.66)), rough=0.85), roll=math.pi / 2)
# coils of rope by the rail and at the mizzen of the wheel box
def coil(name, p, r=0.28, turns=5):
    for k in range(turns):
        bpy.ops.mesh.primitive_torus_add(major_radius=r - k * 0.035, minor_radius=0.018, major_segments=16, minor_segments=4, location=(p[0], p[1], p[2] + 0.018 + k * 0.004))
        o = bpy.context.active_object; o.name = f"{name}{k}"; K._finish(o, M_MANILA, smooth=True)
coil("CoilStern", (-2.4, -37.6, 0.01)); coil("CoilRail", (hb(-21.5, 0) - 0.55, -21.4, 0.01), 0.24)
# the bell on its belfry at the break
for sx in (-1, 1):
    box(f"BelfryPost{sx}", (0.07, 0.07, 1.25), (sx * 0.22, BREAK_Y - 0.3, 0.62), M_TEAK)
box("BelfryBeam", (0.6, 0.1, 0.08), (0, BREAK_Y - 0.3, 1.27), M_TEAK)
lathe("Bell", [(0.0, 0.0), (0.16, 0.0), (0.15, 0.03), (0.12, 0.12), (0.10, 0.22), (0.05, 0.27), (0.0, 0.28)], (0, BREAK_Y - 0.3, 0.92), M_BRASS, steps=16)

# ============================================================================= the awning over the poop
AW_Y0, AW_Y1 = -38.0, -21.0
AW_RIDGE, AW_EDGE = 3.05, 2.55
def aw_xe(y): return hb(y, POOP_Z) - 0.18
STAN_Y = list(np.linspace(AW_Y0, AW_Y1, 6))
def awning():
    nx, ny = 12, 40; verts = []; faces = []; wts = []
    for j in range(ny + 1):
        y = lerp(AW_Y0, AW_Y1, j / ny)
        xe = aw_xe(y)
        sy = min(abs(y - s) for s in STAN_Y) / ((STAN_Y[1] - STAN_Y[0]) / 2)
        for i in range(nx + 1):
            u = -1 + 2 * i / nx; x = u * xe
            sag = 0.10 * math.sin(math.pi * abs(u)) * (0.4 + 0.6 * sy)
            z = AW_EDGE + (AW_RIDGE - AW_EDGE) * (1 - abs(u)) - sag
            verts.append((x, y, z)); wts.append(0.3 * math.sin(math.pi * abs(u)) * (0.3 + 0.7 * sy))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i; faces.append((a, a + nx + 1, a + nx + 2, a + 1))
    o = mesh_from("Awning", verts, faces, M_AWNING, smooth=True)
    orient(o, lambda c: (0, 0, -1))
    return o, wts
AWN, AWN_W = awning()
def valance():
    objs = []
    for side in (1, -1):
        verts = []; faces = []
        ys = np.linspace(AW_Y0, AW_Y1, 137)
        for y in ys:
            xe = aw_xe(y)
            scal = 0.07 * abs(math.sin(math.pi * (y - AW_Y0) / 0.5))
            verts.append((side * (xe + 0.01), y, AW_EDGE + 0.01))
            verts.append((side * (xe + 0.02), y, AW_EDGE - 0.30 - scal))
        for i in range(len(ys) - 1):
            a = 2 * i; faces.append((a, a + 2, a + 3, a + 1))
        o = mesh_from(f"Valance{side}", verts, faces, M_VALANCE, smooth=True)
        orient(o, lambda c, side=side: (-side, 0, 0))
        objs.append(o)
    # across the after end too
    verts = []; faces = []
    xs = np.linspace(-aw_xe(AW_Y0), aw_xe(AW_Y0), 30)
    for x in xs:
        zt = AW_EDGE + (AW_RIDGE - AW_EDGE) * (1 - abs(x) / aw_xe(AW_Y0)) - 0.0
        verts += [(x, AW_Y0 - 0.01, zt), (x, AW_Y0 - 0.02, zt - 0.30 - 0.07 * abs(math.sin(math.pi * x / 0.5)))]
    for i in range(len(xs) - 1):
        a = 2 * i; faces.append((a, a + 2, a + 3, a + 1))
    o = mesh_from("ValanceAft", verts, faces, M_VALANCE, smooth=True); orient(o, lambda c: (0, 1, 0)); objs.append(o)
    return objs
VAL = valance()
# stanchions and ridge spar
for y in STAN_Y:
    for side in (1, -1):
        x = side * aw_xe(y)
        cyl(f"AwningStanchion{side}_{y:.1f}", 0.025, AW_EDGE, (x, y, AW_EDGE / 2), M_IRON, verts=6)
    if y in (STAN_Y[0], STAN_Y[-1], STAN_Y[2]):
        cyl(f"AwningRidgePost{y:.1f}", 0.035, AW_RIDGE, (0, y, AW_RIDGE / 2), M_IRON, verts=8)
tube("AwningRidge", [Vector((0, AW_Y0 - 0.1, AW_RIDGE + 0.04)), Vector((0, AW_Y1 + 0.1, AW_RIDGE + 0.04))], 0.045, M_SPAR, sides=8)
for side in (1, -1):
    tube(f"AwningEdgeRope{side}", [Vector((side * aw_xe(y), y, AW_EDGE + 0.02)) for y in np.linspace(AW_Y0, AW_Y1, 18)], 0.014, M_MANILA, sides=4, caps=False)

# ============================================================================= the deckhouse, funnel, ventilators, boats (main deck)
DH_Y0, DH_Y1, DH_X = -3.0, 16.0, 3.3
DH_TOP = MAIN_Z + 2.35
box("Deckhouse", (2 * DH_X, DH_Y1 - DH_Y0, DH_TOP - MAIN_Z), (0, (DH_Y0 + DH_Y1) / 2, (DH_TOP + MAIN_Z) / 2), M_WHITE)
box("DeckhouseRoof", (2 * DH_X + 0.3, DH_Y1 - DH_Y0 + 0.3, 0.08), (0, (DH_Y0 + DH_Y1) / 2, DH_TOP + 0.04), M_STONE, bevel=0.02)
for side in (1, -1):
    for y in np.arange(DH_Y0 + 1.2, DH_Y1 - 0.8, 1.9):
        box(f"DHWindow{side}_{y:.1f}", (0.03, 0.6, 0.5), (side * (DH_X + 0.01), y, MAIN_Z + 1.5), M_DARK)
        box(f"DHWindowFrame{side}_{y:.1f}", (0.02, 0.72, 0.62), (side * (DH_X + 0.005), y, MAIN_Z + 1.5), M_TEAK)
for k, x in enumerate((-1.4, 1.4)):
    box(f"DHDoor{k}", (0.8, 0.03, 1.9), (x, DH_Y0 - 0.01, MAIN_Z + 0.95), M_TEAK, bevel=0.01)
# engine-room skylight on the house top, aft of the funnel
box("EngineSkylight", (2.2, 3.4, 0.7), (0, 11.0, DH_TOP + 0.35), M_STONE, bevel=0.03)
for sx in (-1, 1):
    box(f"EngineSkylightLid{sx}", (1.15, 3.4, 0.05), (sx * 0.52, 11.0, DH_TOP + 0.82), M_GLASS, rot=(0, sx * math.radians(-18), 0))
# the funnel: elliptical, raked aft, black; a band of soot at the top; the whistle and steam pipe forward
FN = Vector((0, 5.0, DH_TOP))
FN_TOP = 13.6
def funnel():
    verts = []; faces = []; ns = 24; zs = np.linspace(FN.z, FN_TOP, 9)
    for z in zs:
        off = -0.09 * (z - FN.z)
        for i in range(ns):
            a = 2 * math.pi * i / ns
            verts.append((1.15 * math.cos(a), FN.y + off + 1.45 * math.sin(a), z))
    for j in range(len(zs) - 1):
        for i in range(ns):
            i2 = (i + 1) % ns; a = j * ns + i
            faces.append((a, j * ns + i2, (j + 1) * ns + i2, (j + 1) * ns + i))
    o = mesh_from("Funnel", verts, faces, M_BLACK, smooth=True)
    orient(o, lambda c: (c.x, c.y - FN.y + 0.09 * (c.z - FN.z), 0))
    # the inside, seen from below at the lip: a dark disc just inside the top
    off = -0.09 * (FN_TOP - FN.z)
    disc = [(0.0, FN.y + off, FN_TOP - 0.25)] + [(1.1 * math.cos(2 * math.pi * i / ns), FN.y + off + 1.4 * math.sin(2 * math.pi * i / ns), FN_TOP - 0.25) for i in range(ns)]
    mesh_from("FunnelSoot", disc, [(0, i + 1, (i + 1) % ns + 1) for i in range(ns)], plain("M_Soot", (0.008, 0.007, 0.007), rough=0.95))
    for zr in (FN.z + 3.0, FN_TOP - 0.4):
        off = -0.09 * (zr - FN.z)
        tube(f"FunnelHoop{zr:.1f}", [Vector((1.17 * math.cos(2 * math.pi * i / 24), FN.y + off + 1.47 * math.sin(2 * math.pi * i / 24), zr)) for i in range(25)], 0.025, M_BLACK, sides=4, caps=False)
    sp = [Vector((0.0, FN.y + 1.55, FN.z)), Vector((0.0, FN.y + 1.55 - 0.9, FN_TOP + 0.4))]
    tube("SteamPipe", sp, 0.11, M_BLACK, sides=10)
    lathe("Whistle", [(0.0, 0.0), (0.09, 0.0), (0.1, 0.35), (0.07, 0.4), (0.0, 0.42)], (0.0, FN.y + 1.55 - 0.75, FN_TOP - 0.6), M_BRASS, steps=10)
    return o
funnel()
FN_GUY_Z = 10.0
for side in (1, -1):
    for k, y in enumerate((FN.y - 4.5, FN.y, FN.y + 4.0)):
        p0 = Vector((side * 1.0, FN.y - 0.09 * (FN_GUY_Z - FN.z) + (k - 1) * 0.9, FN_GUY_Z))
        p1 = Vector((side * (hb(y, top(y)) - 0.1), y, top(y) + 0.05))
        tube(f"FunnelGuy{side}{k}", [p0, p1], 0.011, M_ROPE, sides=3, caps=False)
# bell-mouthed ventilators about the funnel (white outside; their throats dark)
def ventilator(name, x, y, h, yaw):
    z0 = DH_TOP
    cyl(f"{name}Trunk", 0.26, h, (x, y, z0 + h / 2), M_WHITE, verts=12)
    d = Vector((math.sin(yaw), math.cos(yaw), 0))
    c = Vector((x, y, z0 + h + 0.25)) + d * 0.12
    lathe(f"{name}Cowl", [(0.27, -0.25), (0.3, 0.0), (0.42, 0.25), (0.5, 0.42), (0.47, 0.45)], tuple(c), M_WHITE, steps=14,
          rot=Vector((0, 0, 1)).rotation_difference(d * 0.85 + Vector((0, 0, 0.5))).to_euler())
    cyl(f"{name}Throat", 0.36, 0.02, tuple(c + (d * 0.85 + Vector((0, 0, 0.5))).normalized() * 0.3), M_DARK, verts=12,
        rot=Vector((0, 0, 1)).rotation_difference(d * 0.85 + Vector((0, 0, 0.5))).to_euler(), smooth=False)
for k, (x, y, h) in enumerate(((2.4, FN.y - 2.0, 1.8), (-2.4, FN.y - 2.0, 1.8), (2.3, FN.y + 2.6, 1.4), (-2.3, FN.y + 2.6, 1.4))):
    ventilator(f"Vent{k}", x, y, h, 0.0 if k < 2 else math.pi)
# the boats in their davits: two a side, white, canvas covers
def boat(name, cy, x, z, L=7.0, B=1.9, D=0.8):
    N, M = 14, 6; verts = []; faces = []
    for i in range(N + 1):
        t = i / N; y = cy - L / 2 + L * t
        w = B / 2 * math.sin(math.pi * t) ** 0.6
        sh = 0.22 * (2 * t - 1) ** 4
        for j in range(M + 1):
            a = math.pi * j / M
            verts.append((x + w * math.cos(a), y, z + sh - D * math.sin(a) * (0.55 + 0.45 * math.sin(math.pi * t))))
    for i in range(N):
        for j in range(M):
            a0 = i * (M + 1) + j; faces.append((a0, a0 + M + 1, a0 + M + 2, a0 + 1))
    o = mesh_from(name, verts, faces, M_WHITE, smooth=True)
    orient(o, lambda c: (c.x - x, 0, -1 if c.z < z - 0.2 else 0))
    cov = [(x + B / 2 * 0.9 * math.sin(math.pi * (i / N)) ** 0.6 * (1 - 2 * (k % 2)), cy - L / 2 + L * i / N, z + 0.22 * (2 * i / N - 1) ** 4 + (0.25 if k == 2 else 0.02))
           for i in range(N + 1) for k in range(3)]
    cf = []
    for i in range(N):
        for (k0, k1) in ((0, 2), (2, 1)):
            cf.append((i * 3 + k0, (i + 1) * 3 + k0, (i + 1) * 3 + k1, i * 3 + k1))
    cv_ = mesh_from(name + "Cover", cov, cf, M_COVER, smooth=True); orient(cv_, lambda c: (0, 0, 1))
    for dy in (-L / 2 + 0.8, L / 2 - 0.8):
        y = cy + dy; side = 1 if x > 0 else -1
        p0 = Vector((side * (hb(y, top(y)) - 0.15), y, MAIN_Z + 0.2))
        tube(f"{name}Davit{dy:.1f}", [p0, p0 + Vector((0, 0, 3.4)), Vector((x + side * 0.05, y, z + 2.4)), Vector((x, y, z + 1.95))], [0.07, 0.07, 0.06, 0.05], M_BLACK, sides=6)
        tube(f"{name}Fall{dy:.1f}", [Vector((x, y, z + 1.95)), Vector((x, y, z + 0.1))], 0.016, M_MANILA, sides=3)
for side in (1, -1):
    for k, cy in enumerate((-14.0, 21.5)):
        boat(f"Boat{side}{k}", cy, side * (hb(cy, top(cy)) + 1.05), MAIN_Z + 2.2)

# ============================================================================= masts, yards, furled sails, rigging
SAILS = []
def mast(name, y, d0, lower_h, top_h, tg_h, yards, gaff=False):
    z0 = MAIN_Z - 0.05
    cyl(name + "Lower", d0 / 2, lower_h + 0.3, (0, y, z0 + (lower_h + 0.3) / 2), M_SPAR, verts=12, r2=d0 * 0.4)
    lh = z0 + lower_h
    box(name + "Top", (2.4 * d0 / 0.6, 1.7 * d0 / 0.6, 0.1), (0, y - 0.15, lh - 0.4), M_BLACK, bevel=0.02)
    box(name + "Cap", (0.4, 0.75, 0.2), (0, y + 0.2, lh + 0.15), M_BLACK, bevel=0.02)
    cyl(name + "Topmast", d0 * 0.32, top_h + 2.0, (0, y + 0.35, lh - 1.6 + (top_h + 2.0) / 2), M_SPAR, verts=8, r2=d0 * 0.22)
    th = lh - 1.6 + top_h + 2.0
    box(name + "Crosstrees", (1.6 * d0 / 0.6, 0.45, 0.07), (0, y + 0.35, th - 1.0), M_BLACK)
    cyl(name + "TopGallant", d0 * 0.2, tg_h + 1.4, (0, y + 0.45, th - 1.2 + (tg_h + 1.4) / 2), M_SPAR, verts=6, r2=d0 * 0.1)
    tgh = th - 1.2 + tg_h + 1.4
    cyl(name + "Truck", d0 * 0.16, 0.12, (0, y + 0.45, tgh + 0.06), M_BLACK, verts=8)
    for k, (h, L) in enumerate(yards):
        yz = z0 + h; yy = y + 0.45 + (0.1 if k else 0.0)
        r0 = 0.17 * L / 17.0 + 0.035
        tube(f"{name}Yard{k}", [Vector((-L / 2, yy, yz)), Vector((-L / 4, yy, yz)), Vector((0, yy, yz)), Vector((L / 4, yy, yz)), Vector((L / 2, yy, yz))],
             [r0 * 0.4, r0 * 0.8, r0, r0 * 0.8, r0 * 0.4], M_BLACK, sides=6)
        pts = []; rr = []
        for i in range(17):
            t = i / 16; x = lerp(-L / 2 + 0.6, L / 2 - 0.6, t)
            bunt = math.exp(-((t - 0.5) / 0.2) ** 2)
            pts.append(Vector((x, yy - 0.05 - 0.07 * bunt, yz + r0 + 0.09 + 0.1 * bunt)))
            rr.append(0.12 + 0.13 * bunt + 0.025 * noise.noise(Vector((x * 3.1, k * 2.0, 4.0))))
        s = tube(f"Sail{name}{k}", pts, rr, M_SAIL, sides=6); SAILS.append(s)
    if gaff:
        tube(name + "Boom", [Vector((0, y - 0.35, z0 + 2.4)), Vector((0, y - 6.0, z0 + 2.55)), Vector((0, y - 10.5, z0 + 2.7))], [0.11, 0.1, 0.07], M_SPAR, sides=8)
        tube(name + "Gaff", [Vector((0, y - 0.35, lh - 2.5)), Vector((0, y - 4.0, lh - 1.4)), Vector((0, y - 7.2, lh - 0.4))], [0.09, 0.08, 0.06], M_SPAR, sides=8)
        pts = [Vector((0.02 * math.sin(i), y - 0.8 - 9.0 * i / 12, z0 + 2.75 + 0.012 * i)) for i in range(13)]
        s = tube(name + "SailBoom", pts, [0.15 + 0.04 * noise.noise(Vector((i * 0.9, 5, 5))) for i in range(13)], M_SAIL, sides=6); SAILS.append(s)
    return Vector((0, y, lh)), Vector((0, y + 0.35, th)), Vector((0, y + 0.45, tgh))

MAIN_Y, FORE_Y = -10.5, 31.0
MAIN = mast("Main", MAIN_Y, 0.6, 15.0, 9.0, 5.0, [(20.0, 12.0), (24.5, 8.5)], gaff=True)
FORE = mast("Fore", FORE_Y, 0.62, 15.5, 9.5, 5.5, [(13.8, 18.0), (20.4, 14.0), (25.0, 10.0)])
def rope(name, a, b_, r=0.02, sag=0.0, mat=None, sides=4):
    a, b_ = Vector(a), Vector(b_)
    if sag:
        pts = [a.lerp(b_, t) - Vector((0, 0, sag * math.sin(math.pi * t))) for t in (0, 0.25, 0.5, 0.75, 1.0)]
    else:
        pts = [a, b_]
    return tube(name, pts, r, mat or M_ROPE, sides=sides, caps=False)
def shrouds(name, head, y_base, n, spread, ratlines=True):
    for side in (1, -1):
        ends = []
        for i in range(n):
            y = y_base + spread * (i - (n - 1) / 2) / max(1, n - 1) * 2 - 0.5
            z = top(y) - 0.3
            foot = Vector((side * (hb(y, z) + 0.25), y, z))
            hd = head + Vector((side * 0.3, -0.15, -0.3))
            rope(f"{name}Shroud{side}_{i}", foot + Vector((0, 0, 0.5)), hd, 0.022)
            cyl(f"{name}Deadeye{side}_{i}", 0.08, 0.07, tuple(foot + Vector((0, 0, 0.4))), M_BLACK, verts=8, rot=(0, math.pi / 2, 0))
            ends.append((foot + Vector((0, 0, 0.5)), hd))
        y0 = y_base - spread - 0.8; y1 = y_base + spread + 0.3
        box(f"{name}Channel{side}", (0.32, y1 - y0, 0.08), (side * (hb((y0 + y1) / 2, top(y_base) - 0.35) + 0.12), (y0 + y1) / 2, top(y_base) - 0.35), M_BLACK)
        if ratlines:
            L = (ends[0][1] - ends[0][0]).length; h = 0.5
            while h < L * 0.85:
                t = h / L
                tube(f"{name}Ratline{side}_{h:.2f}", [a.lerp(b2, t) for (a, b2) in ends], 0.011, M_ROPE, sides=3, caps=False)
                h += 0.5
shrouds("Main", MAIN[0], MAIN_Y, 4, 1.3)
shrouds("Fore", FORE[0], FORE_Y, 4, 1.4)
for nm, (lh, th, tgh), y in (("Main", MAIN, MAIN_Y), ("Fore", FORE, FORE_Y)):
    for side in (1, -1):
        for i in range(2):
            yy = y - 3.2 - 1.2 * i; z = top(yy) - 0.25
            rope(f"{nm}Backstay{side}{i}", Vector((side * (hb(yy, z) + 0.25), yy, z + 0.5)), (th if i == 0 else tgh) + Vector((side * 0.12, 0, -0.2)), 0.018)
        for i in range(3):
            rope(f"{nm}TopShroud{side}{i}", lh + Vector((side * 0.75, -0.15 + 0.3 * (i - 1), -0.35)), th + Vector((side * 0.12, 0, -0.9)), 0.014)
# bowsprit and stays
BS0 = Vector((0, Y_BOW - 1.2, top(Y_BOW - 1.2) - 0.2)); BSD = Vector((0, math.cos(math.radians(14)), math.sin(math.radians(14))))
tube("Bowsprit", [BS0, BS0 + BSD * 5.0, BS0 + BSD * 9.0], [0.22, 0.16, 0.12], M_SPAR, sides=8)
tube("JibBoom", [BS0 + BSD * 7.5, BS0 + BSD * 14.0], [0.1, 0.06], M_SPAR, sides=6)
rope("ForeStay", FORE[0] + Vector((0, 0.2, -0.2)), BS0 + BSD * 8.6, 0.03, sag=0.1)
rope("ForeTopStay", FORE[1], BS0 + BSD * 13.6, 0.022, sag=0.15)
rope("MainTopStay", MAIN[1], FORE[0] + Vector((0, 0, -0.3)), 0.022, sag=0.2)
rope("MainTGStay", MAIN[2], FORE[1], 0.016, sag=0.2)
for side in (1, -1):
    rope(f"MainStay{side}", MAIN[0] + Vector((side * 0.2, 0.2, -0.2)), Vector((side * DH_X, DH_Y0 + 0.4, DH_TOP + 0.05)), 0.028, sag=0.1)
# the figurehead and the stem
tube("Stem", [Vector((0, Y_BOW - 4.2, WL - 1.0)), Vector((0, Y_BOW - 1.6, WL + 2.5)), Vector((0, Y_BOW + 0.1, top(Y_BOW) - 0.1))], 0.18, M_BLACK, sides=6)
sphere("Figurehead", 0.32, (0, Y_BOW - 0.2, top(Y_BOW) - 0.9), M_WHITE, seg=10, scale=(0.7, 1.4, 1.2))

# ============================================================================= the sea, far sea, coast, dhow, sky
def hull_dist(x, y):
    if y < Y_STERN or y > Y_BOW: return math.hypot(max(0.0, abs(x) - 0.5), min(abs(y - Y_STERN), abs(y - Y_BOW)))
    return abs(x) - hb(y, WL)
def sea():
    N = 62; ext = NEAR_R; k = 3.6
    c0 = Vector((0.0, 0.0, 0))
    def coord(t): return ext * math.sinh(k * t) / math.sinh(k)
    verts = []; faces = []
    for j in range(N + 1):
        for i in range(N + 1):
            x = c0.x + coord(2 * i / N - 1); y = c0.y + coord(2 * j / N - 1) * 1.0
            r = math.hypot(x, y)
            if r > NEAR_R: x, y = x * NEAR_R / r, y * NEAR_R / r
            verts.append((x, y, WL - (0.05 if r > NEAR_R - 2 else 0.0)))
    for j in range(N):
        for i in range(N):
            a = j * (N + 1) + i; q = (a, a + 1, a + N + 2, a + N + 1)
            if all(hull_dist(verts[v][0], verts[v][1]) < -0.4 for v in q): continue
            faces.append(q)
    o = mesh_from("water.ocean.sea", verts, faces, M_SEA, smooth=True)
    return orient(o, lambda c: (0, 0, 1))
SEA = sea()
def foam_at(p):
    x, y = p.x, p.y
    d = hull_dist(x, y)
    f = 0.0
    if Y_STERN - 2 < y < Y_BOW + 2:
        bow = smoothstep(30.0, 52.0, y)
        f = max(f, smoothstep(2.5 + 4.0 * bow, 0.0, d) * (0.55 + 0.45 * bow))
    if y < Y_STERN + 2:
        t = Y_STERN + 2 - y
        w = 2.6 + 0.16 * t
        n = 0.5 + 0.5 * noise.noise(Vector((x * 0.25, y * 0.12, 3.0)))
        f = max(f, smoothstep(w, w * 0.35, abs(x)) * math.exp(-t / 85.0) * (0.55 + 0.45 * n))
    # the Kelvin arms, from the bow back past the stern (19.5 degrees each side)
    t2 = Y_BOW - y
    if t2 > 0:
        arm = abs(abs(x) - 0.354 * t2 - 1.0)
        f = max(f, smoothstep(2.0, 0.0, arm) * 0.25 * math.exp(-max(0.0, t2 - 40.0) / 120.0) * (0.5 + 0.5 * noise.noise(Vector((x * 0.3, y * 0.3, 7.0)))))
    return f
def far_sea():
    verts = []; faces = []; seg = 96
    for r in (NEAR_R - 5.0, SKY_R - 2.0):
        for i in range(seg):
            a = 2 * math.pi * i / seg; verts.append((r * math.cos(a), r * math.sin(a), WL - 0.04))
    for i in range(seg):
        j = (i + 1) % seg; faces.append((i, j, seg + j, seg + i))
    return orient(mesh_from("FarSea", verts, faces, M_FARSEA), lambda c: (0, 0, 1))
far_sea()
def coast():
    """the Arabian mountains low on the port horizon: bare, folded ridges, hazed almost into the sky."""
    verts = []; faces = []; N = 90
    for i in range(N + 1):
        t = i / N; a = math.radians(lerp(-150.0, -20.0, t))     # bearings from the bow, port side
        d = Vector((math.sin(a), math.cos(a), 0)); p0 = Vector((RX, RY, 0)) + d * 440.0
        h = 7.0 + 9.0 * abs(noise.noise(Vector((t * 7.0, 1.3, 0.0)))) + 6.0 * max(0.0, noise.noise(Vector((t * 2.5, 4.0, 0.0)))) + 3.0 * math.sin(t * 40.0) ** 2
        h *= smoothstep(0.0, 0.12, t) * smoothstep(1.0, 0.8, t) * 0.9 + 0.1
        verts += [(p0.x, p0.y, WL - 1.0), (p0.x + d.x * 6, p0.y + d.y * 6, WL + h)]
    for i in range(N):
        a0 = 2 * i; faces.append((a0, a0 + 2, a0 + 3, a0 + 1))
    return orient(mesh_from("FarCoast", verts, faces, M_COAST), lambda c: (RX - c.x, RY - c.y, 0))
coast()
def dhow():
    a = math.radians(98.0); d = Vector((math.sin(a), math.cos(a), 0)); p = Vector((RX, RY, 0)) + d * 260.0
    fwd = Vector((math.cos(a + 1.2), math.sin(a + 1.2), 0))
    parts = [box("DhowHull", (2.2, 9.0, 1.4), (p.x, p.y, WL + 0.4), M_DHOW, rot=(0, 0, math.atan2(-fwd.x, fwd.y)))]
    mp = p + fwd * 1.0
    parts.append(cyl("DhowMast", 0.12, 8.0, (mp.x, mp.y, WL + 4.5), M_DHOW, verts=5))
    q0 = mp + Vector((0, 0, 8.4)) - fwd * 5.5; q1 = mp + Vector((0, 0, 8.6)) + fwd * 4.0; q2 = mp + Vector((0, 0, 1.6)) + fwd * 3.0; q3 = mp + Vector((0, 0, 1.2)) - fwd * 1.5
    parts.append(mesh_from("DhowSail", [tuple(q0), tuple(q1), tuple(q2), tuple(q3)], [(0, 1, 2, 3)], M_DHOW))
dhow()
SKY = E8.sky_dome("SkyDome", M_SKY, SKY_R, seg=48, rings=16, el_min=-6.0)

# ============================================================================= living weights, markers, lights, cameras
K.apply_transforms()
E8.water_attrs(SEA, foam_at)
add_sway(AWN, lambda p: 0.0)
ca = AWN.data.color_attributes["sway"]
for i, w in enumerate(AWN_W): ca.data[i].color = (w, 1, 1, 1)
for o in VAL:
    zs = [v.co.z for v in o.data.vertices]; zt = max(zs)
    add_sway(o, lambda p, zt=zt: smoothstep(zt, zt - 0.35, p.z))
add_sway(ENS, lambda p: max(0.0, min(1.0, (ENS_Y - p.y) / ENS_W)) ** 0.8)
for s in SAILS:
    zs = [v.co.z for v in s.data.vertices]; zmax = max(zs); zmin = min(zs)
    add_sway(s, lambda p, zmax=zmax, zmin=zmin: 0.3 * smoothstep(zmax, zmin, p.z))

sound("surf", "side", (hb(RY, WL) + 0.6, RY + 2.0, WL + 0.3))
sound("surf", "wake", (0.0, Y_STERN - 6.0, WL + 0.3))
sound("rigging", "main", (0.0, MAIN_Y, 8.0))
sound("gulls", "astern", (6.0, Y_STERN - 40.0, 14.0))
anchor("reader.entrance", (RX, RY, deck_z(RX, RY, 0)))
anchor("reader.look", tuple(Vector((RX, RY, EYE)) + LOOK))
anchor("scene.centre", (0.0, FN.y, DH_TOP))
anchor("ship.funnel", (0.0, FN.y, DH_TOP))
anchor("ship.mainmast", (0.0, MAIN_Y, MAIN_Z + 2.0))
anchor("ship.wheel", tuple(WH + Vector((0, 0.6, 0))))
anchor("ship.stern", (0.0, Y_STERN + 0.5, 1.0))

sun = light_obj("light.sun", 'SUN', 4.6, (1.0, 0.94, 0.84), tuple(SUN_DIR * 40), direction=-SUN_DIR, angle=math.radians(0.8))
sky_l = light_obj("light.sky", 'SUN', 0.5, (0.65, 0.76, 1.0), (0, 0, 30), direction=(0.1, -0.15, -1.0), angle=math.radians(70))
sky_l.data.use_shadow = False
world = bpy.data.worlds.new("GulfOfAden"); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]
try:
    skyn = wn.nodes.new("ShaderNodeTexSky"); skyn.sky_type = 'MULTIPLE_SCATTERING'; skyn.sun_disc = False
    skyn.sun_elevation = math.asin(SUN_DIR.z); skyn.sun_rotation = math.atan2(SUN_DIR.x, SUN_DIR.y); skyn.altitude = 50; skyn.air_density = 2.5; skyn.aerosol_density = 3.0
    wn.links.new(skyn.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.22
except Exception as e:
    print("sky texture unavailable:", e); bg.inputs["Color"].default_value = (0.6, 0.7, 0.8, 1); bg.inputs["Strength"].default_value = 0.8
for o in K.COLL.objects:
    if o.type == 'MESH' and o.name.startswith(("water.", "FarSea")):
        o.visible_shadow = False

EP = Vector((RX, RY, EYE))
page = box("PagePreview", (0.4, 0.004, 0.55), tuple(EP + LOOK * 0.6 - Vector((0, 0, 0.05))), plain("M_PagePreview", (0.80, 0.77, 0.69), rough=0.9, emission=(0.80, 0.77, 0.69), strength=0.15), rot=(0, 0, -LOOK_YAW))
def yawed(deg, dist=10.0, dz=-0.6):
    a = LOOK_YAW + math.radians(deg); return tuple(EP + Vector((math.sin(a), math.cos(a), 0)) * dist + Vector((0, 0, dz)))
cams = [
    camera("Cam_Reader", tuple(EP), yawed(0, 10, -0.8), lens=17),
    camera("Cam_Page", tuple(EP), yawed(0, 10, -0.8), lens=17),
    camera("Cam_Left", tuple(EP), yawed(-62, 10, 0.4), lens=17),
    camera("Cam_Right", tuple(EP), yawed(75, 10, -1.2), lens=17),
    camera("Cam_Behind", tuple(EP), yawed(180, 10, -0.9), lens=17),
    camera("Cam_Down", tuple(EP), tuple(Vector((RX - 1.2, RY + 1.4, 0.0))), lens=17),
    camera("Cam_Rail", tuple(EP + Vector((1.0, 0.3, 0.1))), tuple(Vector((hb(RY - 15, WL) + 4.0, RY - 18.0, WL))), lens=20),
    camera("Cam_Funnel", tuple(EP), (0.0, FN.y, 8.0), lens=35),
]
for c in cams: c.data.clip_end = 900
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "mongolia_deck_source.blend"))
K.print_budget(exclude=("PagePreview",))

if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=-1.0, captures_dir=ARGS.captures)

if ARGS.bake or ARGS.export:
    E8.bake_and_export(
        "mongolia_deck.gltf", cams, page=page,
        keep_names={"M_Sea": "water.ocean.sea", "M_FarSea": "far.Sea", "M_FarCoast": "far.Coast", "M_FarDhow": "far.Dhow", "M_SkyDome": "SkyDome",
                    "M_Awning": "cloth.sail.awning", "M_Valance": "cloth.flag.valance", "M_Ensign": "cloth.flag.ensign", "M_Sail": "cloth.sail.furled",
                    "M_SkylightGlass": "WindowGlass_skylights"},
        keep_uv={"M_SkyDome"},
        size_for={"M_DeckPlanks": (2048, 256, 1024), "M_HullPaint": (2048, 256, 1024), "M_Teak": (1024, 256, 512), "M_WhitePaint": (2048, 256, 1024),
                  "M_StonePaint": (512, 64, 256), "M_BlackPaint": (1024, 128, 512), "M_Spar": (512, 128, 256), "M_TarredRope": (256, 64, 64),
                  "M_ManilaRope": (256, 64, 64), "M_Sail": (512, 64, 256), "M_BoatCover": (256, 64, 128), "M_Awning": (1024, 128, 512), "M_Valance": (512, 64, 256),
                  "M_Ensign": (512, 64), "M_Brass": (128, 64, 64), "M_Iron": (256, 64, 128), "M_SkylightGlass": (32, 32), "M_DarkPorts": (32, 32),
                  "M_Cane": (512, 128, 256), "M_TravelRug": (256, 64, 128), "M_Topi": (128, 64, 64), "M_LifeBuoy": (64, 32), "M_RedPaint": (32, 32),
                  "M_FarSea": (64, 32), "M_FarCoast": (512, 64), "M_FarDhow": (64, 32), "M_SkyDome": (2048,), "M_CoveGilt": (64, 32),
                  "M_Soot": (32, 32), "M_GreenBall": (32, 32), "M_BookCloth": (64, 32), "M_BookPages": (64, 32)},
        default_size=(256, 64, 128), water_colour={"M_Sea": (0.010, 0.045, 0.085)})
print("DONE")
