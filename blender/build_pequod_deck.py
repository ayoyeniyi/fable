"""
Fable: the Pequod's quarter-deck, alongside a Nantucket wharf on a cold December noon (Moby-Dick, chapter 16,
"The Ship").

"She was a ship of the old school, rather small if anything; with an old-fashioned claw-footed look about her. Long
seasoned and weather-stained in the typhoons and calms of all four oceans, her old hull's complexion was darkened like
a French grenadier's ... Her masts ... stood stiffly up like the spines of the three old kings of Cologne. Her
ancient decks were worn and wrinkled ... All round, her unpanelled, open bulwarks were garnished like one continuous
jaw, with the long sharp teeth of the sperm whale, inserted there for pins, to fasten her old hempen thews and tendons
to. ... Scorning a turnstile wheel at her reverend helm, she sported there a tiller; and that tiller was in one mass,
curiously carved from the long narrow lower jaw of her hereditary foe."
"... a strange sort of tent, or rather wigwam, pitched a little behind the mainmast. ... It was of a conical shape,
some ten feet high; consisting of the long, huge slabs of limber black bone taken from the middle and highest part of
the jaws of the right-whale. Planted with their broad ends on the deck, a circle of these slabs laced together,
mutually sloped towards each other, and at the apex united in a tufted point, where the loose hairy fibres waved to
and fro ... A triangular opening faced towards the bows of the ship"

No people. Noon in December, "the ship's work suspended": the Pequod lies port side to the wharf, her sails furled
on the yards, her rigging still. The reader stands on the quarter-deck to starboard of the whale-jaw tiller, facing
forward over the starboard bow (Blender -Y): the bow points 32 degrees to the reader's left, so the page has the open
harbour behind it (grey-green water, the low snowy sand of the far shore, ships at anchor) while the deck, the
wigwam, the masts and the wharf frame its left. The sun is low (24 degrees) behind the reader's right shoulder.
A little old snow lies in the deck's waterways and on the wharf and roofs.

Everything is procedural (no downloaded models, textures or HDRIs). Shared helpers: blender/mobydick_kit.py.

Node names Unity relies on:
  anchor.reader.entrance (feet, deck z=0), anchor.reader.look, anchor.scene.centre (the mainmast foot),
  anchor.ship.tiller, anchor.ship.wigwam, anchor.ship.mainmast, anchor.ship.bow, anchor.wharf.edge
  light.sun, light.sky (SUN)
  water.ocean.harbour  the harbour water round the hull and along the wharf: its own mesh, dense near the reader
                       (about 0.5 m) and coarser out to 130 m; UV = world metres / 10; COLOR_0 G = foam (1 at the
                       hull's waterline and the wharf's piles, fading over about 2.5 m)
  far.Sea (static water beyond 125 m), far.Shore, far.Town, far.Ships, SkyDome (unlit backdrop)
  cloth.sail.furled    the sails furled on the yards and the spanker (R: 0 at the yard, up to 0.35 at the bunt)
  cloth.flag.tuft      the wigwam's tufted point (R: 0 where lashed, 1 at the fibres' ends)
  sound.gulls.wharf, sound.gulls.harbour, sound.rigging.main, sound.surf.wharf, sound.surf.hull
Register as outdoor (Outdoor = true): a low winter sun, cold sky.

Axes: metres, Blender +Z up, the reader at the world origin facing -Y. The ship is built in its own frame (forward
-Y, port +X, the quarter-deck at the reader z=0) and turned into place at the end. The water is at z = WL.

Run headless:
  blender -b -P blender/build_pequod_deck.py -- --out out/pequod-deck --render --quick --res 900
  blender -b -P blender/build_pequod_deck.py -- --out out/pequod-deck --render --samples 96 --res 1400
  blender -b -P blender/build_pequod_deck.py -- --out out/pequod-deck --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, Euler, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mobydick_kit import *

args = parse_args("out/pequod-deck")
scene, COLL = reset_scene("PequodDeck", args)
random.seed(1851)
SID = "pequod-deck"

EYE = 1.55
SHIP_YAW = math.radians(32.0)            # the bow points 32 degrees to the reader's left of the look direction
RX, RY = -1.30, 0.0                      # the reader in the ship frame (starboard of the tiller)
WL = -2.15                               # the water, relative to the quarter-deck at the reader
RAIL_H = 1.02                            # rail above the deck at the side
MAIN_Y, MIZ_Y, FORE_Y = -11.5, -4.3, -20.6
SUN_DIR = Vector((-0.645, 0.645, 0.407)).normalized()  # towards the sun: low, behind the reader's right shoulder
SKY_R = 480.0
NEAR_R = 130.0
WHARF_X = 4.75                           # the wharf's face (ship frame), the ship's port side lies against its fenders
WHARF_Z = WL + 1.55

def interp1(table, x):
    xs = [p[0] for p in table]; ys = [p[1] for p in table]
    if x <= xs[0]: return ys[0]
    if x >= xs[-1]: return ys[-1]
    i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
    x0, x1 = xs[i], xs[i + 1]; y0, y1 = ys[i], ys[i + 1]
    def slope(k):
        a, b_ = max(0, k - 1), min(len(xs) - 1, k + 1)
        return (ys[b_] - ys[a]) / (xs[b_] - xs[a])
    h = x1 - x0; t = (x - x0) / h
    m0, m1 = slope(i) * h, slope(i + 1) * h
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * m1

# hull lines (ship frame): half-breadth at the deck, deck height at the side, keel
Y_BOW, Y_STERN = -27.4, 3.0
BEAM = [(-27.4, 0.08), (-26.6, 1.25), (-25.0, 2.35), (-22.0, 3.3), (-17.0, 3.85), (-11.0, 4.0), (-6.0, 3.92), (-2.0, 3.62),
        (0.5, 3.25), (2.2, 2.75), (3.0, 2.45)]
SHEER = [(-27.4, 1.05), (-25.0, 0.62), (-20.0, 0.18), (-14.0, -0.12), (-9.0, -0.2), (-4.0, -0.12), (0.0, 0.0), (3.0, 0.22)]
KEEL_Z = WL - 4.3
CAMBER = 0.12
def beam(y): return max(0.05, interp1(BEAM, y))
def sheer(y): return interp1(SHEER, y)
def keel(y):
    # the forefoot and the run: the keel rises at the ends
    return KEEL_Z + 2.6 * smoothstep(-24.5, -27.4, y) ** 1.5 + 1.2 * smoothstep(0.5, 3.0, y)
def sect(s): return (1.0 - (1.0 - max(0.0, min(1.0, s))) ** 2.6) ** 0.5
def rail_z(y): return sheer(y) + RAIL_H
def hb(y, z):
    """Half-breadth of the outer planking at (y, z) (a little tumblehome above the deck)."""
    k, top = keel(y), rail_z(y)
    s = (z - k) / max(1e-3, top - k)
    tum = 1.0 - 0.045 * smoothstep(0.78, 1.0, s)
    return max(0.0, beam(y) * 1.03 * sect(s / 0.86) * tum)
def deck_z(x, y):
    b = max(0.3, hb(y, sheer(y)))
    return sheer(y) + CAMBER * (1.0 - min(1.0, (x / b) ** 2))
_dz0 = deck_z(RX, RY)
SHEER = [(y, z - _dz0) for (y, z) in SHEER]          # the deck under the reader's feet is z = 0

SHIP_M = Matrix.Translation((0, 0, 0)) @ Matrix.Rotation(SHIP_YAW, 4, 'Z') @ Matrix.Translation((-RX, -RY, 0))
SHIP_O = SHIP_M @ Vector((0, 0, 0))
def ship_w(p): return SHIP_M @ Vector(p)

# ============================================================================= materials
def sh_timber(name, base, dark, light, along='Y', **kw):
    return timber_mat(name, base, dark, light, along=along, yaw=SHIP_YAW, origin=tuple(SHIP_O), **kw)

def hull_mat(name="M_HullOuter"):
    """Old black paint gone brown-grey on the topsides, salt and rust streaks, a pale wale, copper sheathing gone green
    below a weedy waterline."""
    m, nt, b = new_mat(name)
    mp, m1 = frame_coords(nt, SHIP_YAW, tuple(SHIP_O), (1, 1, 1))
    sx = sep_xyz(nt, m1.outputs["Vector"], (-1300, 600))
    z = sx.outputs["Z"]
    strakes = math_n(nt, 'FRACT', math_n(nt, 'MULTIPLY', z, 1 / 0.19, (-1150, 600)), None, (-1050, 600))
    seam = ramp(nt, [(0.0, (0.5, 0.5, 0.5, 1)), (0.05, (1, 1, 1, 1)), (0.95, (1, 1, 1, 1)), (1.0, (0.6, 0.6, 0.6, 1))], (-900, 600))
    nt.links.new(strakes, seam.inputs["Fac"])
    gr, _ = frame_coords(nt, SHIP_YAW, tuple(SHIP_O), (0.08, 0.6, 3.0), (-1600, 300))
    grain = noise_tex(nt, gr.outputs["Vector"], 5.0, 6, 0.6, loc=(-1000, 300))
    big = noise_tex(nt, m1.outputs["Vector"], 0.35, 5, 0.6, loc=(-1000, 0))
    paint = ramp(nt, [(0.25, (0.022, 0.020, 0.018, 1)), (0.5, (0.04, 0.036, 0.031, 1)), (0.8, (0.075, 0.066, 0.055, 1))], (-800, 300))
    nt.links.new(mix_f(nt, grain.outputs["Fac"], big.outputs["Fac"], 0.55, (-900, 200)), paint.inputs["Fac"])
    col = mix_rgb(nt, paint.outputs["Color"], seam.outputs["Color"], 1.0, 'MULTIPLY', (-600, 300))
    # vertical streaks: salt (pale) and rust (from the chain plates and bolts)
    st, _ = frame_coords(nt, SHIP_YAW, tuple(SHIP_O), (2.5, 2.5, 0.12), (-1600, -200))
    sn = noise_tex(nt, st.outputs["Vector"], 3.0, 4, 0.55, loc=(-1000, -200))
    salt = map_range(nt, sn.outputs["Fac"], 0.58, 0.72, 0.0, 0.5, (-800, -200))
    col = mix_rgb(nt, col, (0.19, 0.18, 0.165, 1), salt, 'MIX', (-450, 300))
    rn = noise_tex(nt, st.outputs["Vector"], 5.0, 4, 0.55, loc=(-1000, -400))
    rust = map_range(nt, rn.outputs["Fac"], 0.66, 0.76, 0.0, 0.45, (-800, -400))
    col = mix_rgb(nt, col, (0.11, 0.045, 0.02, 1), rust, 'MIX', (-350, 300))
    # the wale: a band of paler, worn wood a little below the deck
    wz = math_n(nt, 'SUBTRACT', z, 0.0, (-1100, -600))
    # copper below the waterline, green-brown; weed and slime just at it
    cu = map_range(nt, z, WL + 0.12, WL + 0.02, 0.0, 1.0, (-800, -700))
    cn = noise_tex(nt, m1.outputs["Vector"], 2.0, 5, 0.6, loc=(-1000, -800))
    cuc = ramp(nt, [(0.3, (0.06, 0.09, 0.06, 1)), (0.6, (0.10, 0.12, 0.07, 1)), (0.8, (0.16, 0.10, 0.05, 1))], (-700, -800)); nt.links.new(cn.outputs["Fac"], cuc.inputs["Fac"])
    col = mix_rgb(nt, col, cuc.outputs["Color"], cu, 'MIX', (-250, 300))
    weed = map_range(nt, z, WL + 0.45, WL + 0.08, 0.0, 1.0, (-800, -1000))
    weed = math_n(nt, 'MULTIPLY', weed, map_range(nt, cn.outputs["Fac"], 0.35, 0.6, 0.3, 0.9, (-800, -1100)), (-600, -1000))
    col = mix_rgb(nt, col, (0.035, 0.04, 0.018, 1), weed, 'MIX', (-150, 300))
    col = ao_mult(nt, col, 0.3, (0.5, 0.5, 0.5))
    nt.links.new(col, b.inputs["Base Color"])
    wet = map_range(nt, z, WL + 0.5, WL + 0.05, 0.0, 1.0, (-300, -500))
    nt.links.new(mix_f(nt, map_range(nt, big.outputs["Fac"], 0.3, 0.7, 0.55, 0.8, (-300, -300)), 0.25, wet, (-150, -300)), b.inputs["Roughness"])
    h = math_n(nt, 'MULTIPLY_ADD', grain.outputs["Fac"], 0.4, (-300, -700)); nt.links.new(seam.outputs["Color"], h.node.inputs[2])
    bump_from(nt, b, h, 0.35, 0.006)
    return m

def baleen_mat(name="M_Baleen"):
    """Right-whale bone (baleen): black-brown, fibrous along its length, a horn-like sheen, frayed paler edges."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    st = node(nt, "ShaderNodeMapping", (-1200, 200)); st.inputs["Scale"].default_value = (30.0, 30.0, 0.7)
    nt.links.new(mp.outputs["Vector"], st.inputs["Vector"])
    n = noise_tex(nt, st.outputs["Vector"], 2.0, 6, 0.6, loc=(-1000, 200))
    r = ramp(nt, [(0.3, (0.012, 0.010, 0.009, 1)), (0.55, (0.03, 0.024, 0.02, 1)), (0.8, (0.07, 0.055, 0.04, 1))], (-700, 200))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    col = ao_mult(nt, r.outputs["Color"], 0.4, (0.4, 0.4, 0.4))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.42
    bump_from(nt, b, n.outputs["Fac"], 0.4, 0.002)
    return m

def bone_mat(name="M_JawBone"):
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    st = node(nt, "ShaderNodeMapping", (-1200, 200)); st.inputs["Scale"].default_value = (2.0, 2.0, 2.0)
    nt.links.new(mp.outputs["Vector"], st.inputs["Vector"])
    n = noise_tex(nt, st.outputs["Vector"], 4.0, 8, 0.65, 0.5, (-1000, 200))
    r = ramp(nt, [(0.25, (0.17, 0.145, 0.10, 1)), (0.5, (0.27, 0.235, 0.17, 1)), (0.75, (0.36, 0.32, 0.24, 1))], (-700, 200))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    pores = node(nt, "ShaderNodeTexVoronoi", (-1000, -200)); pores.inputs["Scale"].default_value = 70.0
    nt.links.new(mp.outputs["Vector"], pores.inputs["Vector"])
    col = mix_rgb(nt, r.outputs["Color"], map_range(nt, pores.outputs["Distance"], 0.0, 0.25, 0.7, 1.0, (-800, -200)), 1.0, 'MULTIPLY', (-450, 200))
    col = ao_mult(nt, col, 0.15, (0.35, 0.3, 0.25))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.5
    bump_from(nt, b, mix_f(nt, n.outputs["Fac"], pores.outputs["Distance"], 0.5, (-300, -400)), 0.35, 0.003)
    return m

def cask_mat(name="M_Cask"):
    """Oak staves gone grey, black iron hoops (local z bands), oily stains."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1500, 0)); s_ = sep_xyz(nt, tc.outputs["Object"], (-1300, 0))
    az = node(nt, "ShaderNodeMath", (-1150, 100), operation='ARCTAN2'); nt.links.new(s_.outputs["Y"], az.inputs[0]); nt.links.new(s_.outputs["X"], az.inputs[1])
    stave = math_n(nt, 'FRACT', math_n(nt, 'MULTIPLY', az.outputs[0], 18 / (2 * math.pi), (-1000, 100)), None, (-900, 100))
    sv = ramp(nt, [(0.0, (0.5, 0.5, 0.5, 1)), (0.06, (1, 1, 1, 1)), (0.94, (1, 1, 1, 1)), (1.0, (0.5, 0.5, 0.5, 1))], (-750, 100)); nt.links.new(stave, sv.inputs["Fac"])
    zz = s_.outputs["Z"]
    hoop = math_n(nt, 'MAXIMUM', math_n(nt, 'MAXIMUM', map_range(nt, math_n(nt, 'ABSOLUTE', math_n(nt, 'SUBTRACT', zz, 0.10, (-1100, -200)), None, (-1000, -200)), 0.03, 0.022, 0, 1, (-900, -200)),
                                                       map_range(nt, math_n(nt, 'ABSOLUTE', math_n(nt, 'SUBTRACT', zz, 0.66, (-1100, -300)), None, (-1000, -300)), 0.03, 0.022, 0, 1, (-900, -300)), (-750, -250)),
                  math_n(nt, 'MAXIMUM', map_range(nt, math_n(nt, 'ABSOLUTE', math_n(nt, 'SUBTRACT', zz, 0.27, (-1100, -400)), None, (-1000, -400)), 0.025, 0.018, 0, 1, (-900, -400)),
                         map_range(nt, math_n(nt, 'ABSOLUTE', math_n(nt, 'SUBTRACT', zz, 0.49, (-1100, -500)), None, (-1000, -500)), 0.025, 0.018, 0, 1, (-900, -500)), (-750, -450)), (-600, -350))
    n = noise_tex(nt, tc.outputs["Object"], 6.0, 6, 0.6, loc=(-1000, 400))
    wood = ramp(nt, [(0.3, (0.13, 0.10, 0.07, 1)), (0.6, (0.21, 0.17, 0.12, 1)), (0.8, (0.27, 0.23, 0.17, 1))], (-700, 400)); nt.links.new(n.outputs["Fac"], wood.inputs["Fac"])
    col = mix_rgb(nt, wood.outputs["Color"], sv.outputs["Color"], 1.0, 'MULTIPLY', (-500, 300))
    rnd = attr(nt, "rnd", (-1000, 650))
    tone = ramp(nt, [(0.0, (0.75, 0.75, 0.78, 1)), (1.0, (1.15, 1.08, 1.0, 1))], (-800, 650)); nt.links.new(rnd, tone.inputs["Fac"])
    col = mix_rgb(nt, col, tone.outputs["Color"], 1.0, 'MULTIPLY', (-400, 300))
    col = mix_rgb(nt, col, (0.03, 0.028, 0.026, 1), hoop, 'MIX', (-250, 300))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, 0.8, 0.5, hoop, (-250, -100)), b.inputs["Roughness"])
    bump_from(nt, b, mix_f(nt, sv.outputs["Color"], hoop, 0.5, (-300, -500)), 0.4, 0.004)
    return m

def ground_mat(name="M_WharfGround"):
    """The wharf's top: frozen packed earth and gravel, trodden planks of the old cartway, old snow lying in patches
    (more in the lee of the casks and sheds), oil stains."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    n = noise_tex(nt, mp.outputs["Vector"], 1.2, 8, 0.6, 0.4, (-1000, 300))
    g = node(nt, "ShaderNodeTexVoronoi", (-1000, 0)); g.inputs["Scale"].default_value = 28.0; nt.links.new(mp.outputs["Vector"], g.inputs["Vector"])
    r = ramp(nt, [(0.3, (0.075, 0.068, 0.058, 1)), (0.55, (0.12, 0.11, 0.095, 1)), (0.8, (0.17, 0.155, 0.13, 1))], (-700, 300))
    nt.links.new(mix_f(nt, n.outputs["Fac"], g.outputs["Distance"], 0.35, (-850, 200)), r.inputs["Fac"])
    col = r.outputs["Color"]
    oil = noise_tex(nt, mp.outputs["Vector"], 0.5, 4, 0.5, loc=(-1000, -300))
    col = mix_rgb(nt, col, (0.03, 0.027, 0.022, 1), map_range(nt, oil.outputs["Fac"], 0.6, 0.7, 0.0, 0.7, (-800, -300)), 'MIX', (-450, 300))
    sn = noise_tex(nt, mp.outputs["Vector"], 0.45, 6, 0.65, 0.3, (-1000, -600))
    snow = map_range(nt, sn.outputs["Fac"], 0.56, 0.62, 0.0, 1.0, (-800, -600))
    snow = math_n(nt, 'MAXIMUM', snow, attr(nt, "snow", (-1000, -800)), (-650, -650))
    col = mix_rgb(nt, col, (0.62, 0.64, 0.68, 1), snow, 'MIX', (-250, 300))
    col = ao_mult(nt, col, 0.6, (0.4, 0.4, 0.4))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, 0.92, 0.6, snow, (-200, -200)), b.inputs["Roughness"])
    bump_from(nt, b, mix_f(nt, g.outputs["Distance"], n.outputs["Fac"], 0.5, (-300, -500)), 0.6, 0.02)
    return m

def wharf_timber_mat(name="M_WharfTimber"):
    m = timber_mat(name, base=(0.17, 0.155, 0.135), dark=(0.05, 0.045, 0.04), light=(0.30, 0.285, 0.26), along='Z', rough=(0.6, 0.9), grime=0.5, salt=0.25, yaw=SHIP_YAW, origin=tuple(SHIP_O))
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    col = b.inputs["Base Color"].links[0].from_socket
    z = world_z(nt, (-1400, -1300))
    wet = map_range(nt, z, WL + 0.9, WL + 0.05, 0.0, 1.0, (-1200, -1300))
    weed = map_range(nt, z, WL + 0.45, WL + 0.0, 0.0, 1.0, (-1200, -1450))
    col = mix_rgb(nt, col, (0.04, 0.045, 0.03, 1), math_n(nt, 'MULTIPLY', wet, 0.7, (-1050, -1300)), 'MIX', (-900, -1300))
    col = mix_rgb(nt, col, (0.05, 0.06, 0.025, 1), weed, 'MIX', (-800, -1300))
    nt.links.new(col, b.inputs["Base Color"])
    return m

def sky_mat(name="M_SkyDome"):
    """A cold, clear winter noon over Nantucket: pale blue overhead, a milky white-blue haze along the horizon, thin
    high cirrostratus, a band of grey snow-cloud low over the land to the north (left of the bow), the low sun's glow
    behind the reader's right shoulder."""
    m, nt, b = new_mat(name)
    g = node(nt, "ShaderNodeNewGeometry", (-2000, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-1800, 0), operation='NORMALIZE'); nt.links.new(g.outputs["Position"], nv.inputs[0])
    sep = sep_xyz(nt, nv.outputs[0], (-1600, 0)); el = sep.outputs["Z"]
    base = ramp(nt, [(0.0, (0.60, 0.64, 0.68, 1)), (0.09, (0.66, 0.70, 0.74, 1)), (0.14, (0.56, 0.63, 0.72, 1)), (0.3, (0.40, 0.52, 0.68, 1)),
                     (0.6, (0.28, 0.42, 0.63, 1)), (1.0, (0.22, 0.36, 0.60, 1))], (-1200, 300))
    nt.links.new(map_range(nt, el, -0.12, 1.0, 0.0, 1.0, (-1400, 300)), base.inputs["Fac"])
    col = base.outputs["Color"]
    zk = math_n(nt, 'ADD', math_n(nt, 'MAXIMUM', el, 0.0, (-1400, -100)), 0.06, (-1250, -100))
    px = math_n(nt, 'DIVIDE', sep.outputs["X"], zk, (-1100, -50)); py = math_n(nt, 'DIVIDE', sep.outputs["Y"], zk, (-1100, -200))
    cv = node(nt, "ShaderNodeCombineXYZ", (-950, -100)); nt.links.new(px, cv.inputs["X"]); nt.links.new(py, cv.inputs["Y"])
    mp = node(nt, "ShaderNodeMapping", (-800, -100)); mp.inputs["Scale"].default_value = (0.3, 1.2, 1); mp.inputs["Rotation"].default_value = (0, 0, 0.9)
    nt.links.new(cv.outputs[0], mp.inputs["Vector"])
    cl = noise_tex(nt, mp.outputs["Vector"], 0.8, 8, 0.62, 0.8, (-600, -100))
    cr = map_range(nt, cl.outputs["Fac"], 0.5, 0.72, 0.0, 0.42, (-400, -100))
    cmask = map_range(nt, el, 0.12, 0.35, 0.0, 1.0, (-400, -300))
    col = mix_rgb(nt, col, (0.82, 0.84, 0.87, 1), math_n(nt, 'MULTIPLY', cr, cmask, (-250, -200)), 'MIX', (-100, 100))
    # the low grey bank to the north-west (towards the land, left of the bow)
    hz = node(nt, "ShaderNodeCombineXYZ", (-1500, 900)); nt.links.new(sep.outputs["X"], hz.inputs["X"]); nt.links.new(sep.outputs["Y"], hz.inputs["Y"])
    hn = node(nt, "ShaderNodeVectorMath", (-1350, 900), operation='NORMALIZE'); nt.links.new(hz.outputs["Vector"], hn.inputs[0])
    bank_dir = Vector((math.sin(math.radians(70)), -math.cos(math.radians(70)), 0))
    cd = node(nt, "ShaderNodeVectorMath", (-1200, 900), operation='DOT_PRODUCT'); cd.inputs[1].default_value = tuple(bank_dir)
    nt.links.new(hn.outputs[0], cd.inputs[0])
    bn = noise_tex(nt, nv.outputs[0], 6.0, 6, 0.6, 0.6, (-1400, 1100))
    btop = math_n(nt, 'ADD', 0.10, math_n(nt, 'MULTIPLY', bn.outputs["Fac"], 0.08, (-1200, 1100)), (-1100, 1100))
    bmask = math_n(nt, 'MULTIPLY', map_range(nt, cd.outputs["Value"], 0.1, 0.6, 0.0, 1.0, (-1000, 900)),
                   map_range(nt, math_n(nt, 'SUBTRACT', el, btop, (-1000, 1150)), 0.0, -0.04, 0.0, 1.0, (-850, 1150)), (-700, 1000))
    col = mix_rgb(nt, col, (0.52, 0.54, 0.57, 1), math_n(nt, 'MULTIPLY', bmask, 0.85, (-600, 1000)), 'MIX', (50, 100))
    sd = node(nt, "ShaderNodeVectorMath", (-1400, 600), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(SUN_DIR)
    nt.links.new(nv.outputs[0], sd.inputs[0])
    glow = map_range(nt, sd.outputs["Value"], 0.75, 1.0, 0.0, 0.55, (-1200, 600))
    col = mix_rgb(nt, col, (1.0, 0.95, 0.85, 1), glow, 'MIX', (150, 100))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m

def water_mat(name="M_HarbourWater"):
    """Blender preview only: dark green-grey harbour water with small wind ripples. The export replaces it with a plain
    colour; Unity's water material does the moving surface."""
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (0.012, 0.024, 0.024, 1); b.inputs["Roughness"].default_value = 0.1
    b.inputs["IOR"].default_value = 1.33
    mp = coords(nt, world=True)
    sm = node(nt, "ShaderNodeMapping", (-1200, -300)); sm.inputs["Scale"].default_value = (1.0, 2.2, 1.0); sm.inputs["Rotation"].default_value = (0, 0, 0.7)
    nt.links.new(mp.outputs["Vector"], sm.inputs["Vector"])
    r1 = noise_tex(nt, sm.outputs["Vector"], 1.4, 6, 0.6, loc=(-1000, -300))
    r2 = noise_tex(nt, mp.outputs["Vector"], 0.15, 3, 0.5, loc=(-1000, -500))
    bump_from(nt, b, mix_f(nt, r1.outputs["Fac"], r2.outputs["Fac"], 0.4, (-600, -400)), 0.6, 0.15)
    a = attr(nt, "Col", (-1000, 300))
    ca = node(nt, "ShaderNodeVertexColor", (-1000, 500)); ca.layer_name = "Col"
    sp = node(nt, "ShaderNodeSeparateColor", (-800, 500)); nt.links.new(ca.outputs["Color"], sp.inputs["Color"])
    foam_n = noise_tex(nt, mp.outputs["Vector"], 3.0, 4, 0.6, loc=(-1000, 700))
    foam = math_n(nt, 'MULTIPLY', sp.outputs["Green"], map_range(nt, foam_n.outputs["Fac"], 0.45, 0.65, 0.0, 0.8, (-800, 700)), (-600, 600))
    col = mix_rgb(nt, (0.012, 0.024, 0.024, 1), (0.45, 0.47, 0.46, 1), foam, 'MIX', (-300, 300))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, 0.1, 0.6, foam, (-300, 0)), b.inputs["Roughness"])
    return m

M_HULL = hull_mat()
M_BULWARK = sh_timber("M_Bulwark", base=(0.13, 0.105, 0.08), dark=(0.04, 0.032, 0.024), light=(0.22, 0.19, 0.15), along='Y', rough=(0.6, 0.85), grime=0.5, salt=0.2, seams=('Z', 0.19))
M_DECK = sh_timber("M_DeckPlanks", base=(0.24, 0.21, 0.17), dark=(0.07, 0.06, 0.05), light=(0.38, 0.35, 0.30), along='Y', rough=(0.55, 0.85), grime=0.55, salt=0.35, seams=('X', 0.14))
M_RAIL = sh_timber("M_RailCap", base=(0.20, 0.155, 0.11), dark=(0.06, 0.045, 0.03), light=(0.34, 0.28, 0.21), along='Y', rough=(0.4, 0.75), grime=0.3, salt=0.2)
M_SPAR = sh_timber("M_Spar", base=(0.17, 0.12, 0.075), dark=(0.05, 0.035, 0.022), light=(0.28, 0.21, 0.14), along='Z', rough=(0.45, 0.75), grime=0.4)
M_YARD = sh_timber("M_Yard", base=(0.10, 0.08, 0.06), dark=(0.03, 0.025, 0.02), light=(0.18, 0.15, 0.11), along='X', rough=(0.45, 0.75), grime=0.4)
M_FITTING = sh_timber("M_Fittings", base=(0.15, 0.11, 0.075), dark=(0.04, 0.03, 0.02), light=(0.26, 0.2, 0.14), along='X', rough=(0.5, 0.8), grime=0.5, salt=0.2)
M_TEETH = noisy("M_Teeth", [(0.26, 0.23, 0.17), (0.36, 0.33, 0.25), (0.44, 0.41, 0.32)], scale=30, rough=0.4, bump=0.1)
M_JAW = bone_mat()
M_BALEEN = baleen_mat()
M_TARRED = noisy("M_TarredRope", [(0.018, 0.015, 0.012), (0.035, 0.03, 0.023), (0.05, 0.043, 0.033)], scale=60, rough=0.75, bump=0.5, bump_dist=0.002)
M_MANILA = noisy("M_ManilaRope", [(0.15, 0.12, 0.08), (0.24, 0.20, 0.14), (0.32, 0.27, 0.19)], scale=50, rough=0.9, bump=0.5, bump_dist=0.002)
M_SAIL = noisy("M_Sail", [(0.33, 0.31, 0.26), (0.42, 0.40, 0.34), (0.50, 0.48, 0.41)], scale=4.0, rough=0.92, bump=0.4, bump_dist=0.01, sheen=0.4, world=True, ao=(0.15, (0.45, 0.43, 0.4)))
M_IRON = iron_mat("M_Iron", rust=0.35)
M_BRICK = noisy("M_TryworksBrick", [(0.12, 0.05, 0.03), (0.18, 0.08, 0.05), (0.24, 0.12, 0.08)], scale=14, rough=0.9, bump=0.5, bump_dist=0.006, world=True, ao=(0.2, (0.4, 0.4, 0.4)))
M_CASK = cask_mat()
M_GROUND = ground_mat()
M_WHARF = wharf_timber_mat()
M_CLAP = timber_mat("M_Clapboard", base=(0.21, 0.20, 0.18), dark=(0.07, 0.065, 0.06), light=(0.33, 0.32, 0.30), along='X', rough=(0.7, 0.9), grime=0.4, seams=('Z', 0.16), yaw=SHIP_YAW, origin=tuple(SHIP_O))
M_SHINGLE = noisy("M_Shingles", [(0.13, 0.125, 0.12), (0.22, 0.21, 0.20), (0.55, 0.57, 0.60)], scale=3.0, rough=0.85, bump=0.6, bump_dist=0.01, world=True)
M_SNOW = noisy("M_Snow", [(0.58, 0.60, 0.64), (0.66, 0.68, 0.71), (0.72, 0.73, 0.76)], scale=5, rough=0.7, bump=0.3, bump_dist=0.01, world=True, sss=0.1)
M_WINDOW = noisy("M_DarkWindow", [(0.015, 0.018, 0.022), (0.03, 0.035, 0.04), (0.05, 0.055, 0.06)], scale=8, rough=0.15, bump=0.0)
M_CHAIR = sh_timber("M_ChairOak", base=(0.12, 0.08, 0.05), dark=(0.035, 0.025, 0.016), light=(0.22, 0.15, 0.09), along='Z', rough=(0.35, 0.6), grime=0.4)
M_WATER = water_mat()
M_FARSEA = noisy("M_FarSea", [(0.10, 0.13, 0.14), (0.13, 0.16, 0.17), (0.16, 0.19, 0.20)], scale=0.02, rough=0.3, bump=0.0, world=True)
M_FARSHORE = noisy("M_FarShore", [(0.36, 0.34, 0.30), (0.46, 0.45, 0.42), (0.62, 0.63, 0.65)], scale=0.03, rough=1.0, bump=0.0, world=True)
M_FARTOWN = noisy("M_FarTown", [(0.13, 0.12, 0.11), (0.22, 0.20, 0.18), (0.36, 0.34, 0.32)], scale=0.15, rough=1.0, bump=0.0, world=True)
M_FARSHIP = noisy("M_FarShips", [(0.04, 0.035, 0.03), (0.07, 0.06, 0.05), (0.12, 0.11, 0.09)], scale=0.4, rough=0.9, bump=0.0, world=True)
M_SKY = sky_mat()

# ============================================================================= THE SHIP (ship frame)
_before_ship = set(COLL.objects)

def hull_surface(name="Hull", NY=50, NS=12):
    """Outer planking from the keel to the rail, both sides; the stern is closed by the transom (separate)."""
    verts = []; faces = []
    ys = [lerp(Y_BOW + 0.05, Y_STERN, (1 - math.cos(math.pi * i / NY)) / 2) for i in range(NY + 1)]
    for side in (1, -1):
        base = len(verts)
        for y in ys:
            k, top = keel(y), rail_z(y)
            for j in range(NS + 1):
                t = j / NS
                z = lerp(k, top, 1 - (1 - t) ** 1.6)
                verts.append((side * max(0.02, hb(y, z)), y, z))
        for i in range(NY):
            for j in range(NS):
                a = base + i * (NS + 1) + j; b2 = a + NS + 1
                faces.append((a, a + 1, b2 + 1, b2) if side > 0 else (a, b2, b2 + 1, a + 1))
    # keel strip: join the two sides along the bottom
    o = mesh_from(name, verts, faces, M_HULL)
    return orient(o, lambda c: (c.x, 0.0, -0.3))
hull = hull_surface()

def transom(name="Transom"):
    y = Y_STERN; k = keel(y) + 0.15; top = rail_z(y) + 0.12
    N = 10; verts = []; faces = []
    for j in range(N + 1):
        z = lerp(k, top, j / N); w = hb(y, min(z, rail_z(y)))
        verts += [(-w, y, z), (w, y, z)]
    for j in range(N):
        a = 2 * j; faces.append((a, a + 1, a + 3, a + 2))
    o = orient(mesh_from(name, verts, faces, M_HULL, smooth=False), lambda c: (0, 1, 0))
    # inside face of the stern bulwark
    box("TransomInner", (2 * hb(y, rail_z(y)) - 0.2, 0.06, RAIL_H), (0, y - 0.08, sheer(y) + RAIL_H / 2), M_BULWARK)
    # stern windows (the cabin's lights), with their frames
    for x in (-1.1, -0.35, 0.35, 1.1):
        box(f"SternWindow{x}", (0.42, 0.02, 0.32), (x, y + 0.012, sheer(y) - 0.75), M_WINDOW)
        box(f"SternWinFrame{x}", (0.5, 0.03, 0.4), (x, y + 0.004, sheer(y) - 0.75), M_FITTING)
    return o
transom()

def deck(name="Deck", NY=60, NX=12):
    verts = []; faces = []
    ys = [lerp(Y_BOW + 0.9, Y_STERN - 0.05, i / NY) for i in range(NY + 1)]
    for y in ys:
        w = hb(y, sheer(y)) - 0.06
        for i in range(NX + 1):
            x = lerp(-w, w, i / NX)
            n = 0.012 * noise.noise(Vector((x * 0.9, y * 0.35, 3.3)))     # worn and wrinkled
            verts.append((x, y, deck_z(x, y) + n))
    for j in range(NY):
        for i in range(NX):
            a = j * (NX + 1) + i; b2 = a + NX + 1
            faces.append((a, a + 1, b2 + 1, b2))
    return orient(mesh_from(name, verts, faces, M_DECK), lambda c: (0, 0, 1))
deck()

def bulwark_inner(name="Bulwark", NY=56):
    """The inside of the open bulwarks: the planking's inner face, with timberheads (stanchions) at intervals."""
    for side in (1, -1):
        verts = []; faces = []
        ys = [lerp(Y_BOW + 0.9, Y_STERN - 0.1, i / NY) for i in range(NY + 1)]
        for y in ys:
            z0 = sheer(y) - 0.02; z1 = rail_z(y) - 0.04
            for z in (z0, z1):
                verts.append((side * (hb(y, z) - 0.07), y, z))
        for i in range(NY):
            a = 2 * i
            faces.append((a, a + 2, a + 3, a + 1) if side > 0 else (a, a + 1, a + 3, a + 2))
        orient(mesh_from(f"{name}{side}", verts, faces, M_BULWARK), lambda c: (-c.x, 0, 0))
        # waterway: a heavy plank along the deck edge, where old snow lies
        pts = [Vector((side * (hb(y, sheer(y)) - 0.2), y, sheer(y) + CAMBER * 0.02)) for y in ys[::4]]
        tube(f"Waterway{side}", pts, (0.0, 0.0), M_RAIL, rect=(0.28, 0.07), n=2)
        snow = [p + Vector((side * 0.05, 0, 0.045)) for p in pts]
        tube(f"WaterwaySnow{side}", snow, (0.0, 0.0), M_SNOW, rect=(0.14, 0.035), n=2)
        # timberheads, the rail cap with sperm-whale teeth for pins
        y = Y_BOW + 2.2; k = 0
        while y < Y_STERN - 0.4:
            z0 = sheer(y); x = side * (hb(y, z0 + RAIL_H * 0.5) - 0.14)
            box(f"Timberhead{side}_{k}", (0.15, 0.15, RAIL_H + 0.06), (x, y, z0 + (RAIL_H + 0.06) / 2), M_BULWARK,
                rot=(0, 0, 0))
            y += 0.92; k += 1
        rail = [Vector((side * (hb(y, rail_z(y)) - 0.1), y, rail_z(y) + 0.04)) for y in ys[2:-1:2]]
        tube(f"RailCap{side}", rail, (0.0, 0.0), M_RAIL, rect=(0.3, 0.085), n=3)
        y = Y_BOW + 2.6; k = 0
        while y < Y_STERN - 0.5:
            p = Vector((side * (hb(y, rail_z(y)) - 0.1), y, rail_z(y) + 0.085))
            ht = random.uniform(0.10, 0.15)
            o = cyl(f"Tooth{side}_{k}", 0.024, ht, tuple(p + Vector((0, 0, ht / 2))), M_TEETH, verts=5, r2=0.006, smooth=False)
            o.rotation_euler = (random.uniform(-0.12, 0.12), side * random.uniform(0.05, 0.25), 0)
            y += random.uniform(0.36, 0.44); k += 1
bulwark_inner()

def stem_and_bowsprit():
    pts = [Vector((0, Y_BOW - 0.05, keel(Y_BOW) + 0.3)), Vector((0, Y_BOW - 0.25, WL + 0.5)), Vector((0, Y_BOW - 0.35, rail_z(Y_BOW) + 0.4))]
    tube("Stem", pts, (0.0, 0.0), M_FITTING, rect=(0.3, 0.35), n=3)
    a = Vector((0, Y_BOW + 1.5, rail_z(Y_BOW) - 0.2)); d = Vector((0, -math.cos(math.radians(16)), math.sin(math.radians(16))))
    tube("Bowsprit", [a, a + d * 5.0, a + d * 10.5], (0.25, 0.14), M_SPAR, sides=10, n=2)
    tube("JibBoom", [a + d * 8.5, a + d * 16.0], (0.12, 0.07), M_SPAR, sides=8, n=1)
    return a + d * 10.0, a + d * 15.5
BOWSPRIT_END, JIBBOOM_END = stem_and_bowsprit()

# --- masts, tops, yards, furled sails
SAILS = []
def mast(name, y, d0, lower_h, top_h, tg_h, yards):
    """yards: [(height above deck, length)]. Returns (lower masthead, topmast head, top-gallant head) points."""
    z0 = deck_z(0, y) - 0.05
    cyl(name + "Lower", d0 / 2, lower_h + 0.3, (0, y, z0 + (lower_h + 0.3) / 2), M_SPAR, verts=14, r2=d0 * 0.4)
    for k in range(4):   # iron bands round the lower mast
        torus(f"{name}Band{k}", d0 / 2 * (1 - 0.15 * k / 6) + 0.006, 0.012, (0, y, z0 + 1.2 + k * lower_h / 5), M_IRON, seg=12, mseg=3)
    lh = z0 + lower_h
    # the top (platform) and the trestle-trees, the cap
    box(name + "Top", (2.8 * d0 / 0.6, 1.9 * d0 / 0.6, 0.1), (0, y + 0.15, lh - 0.4), M_FITTING, bevel=0.02)
    box(name + "Cap", (0.45, 0.8, 0.22), (0, y - 0.2, lh + 0.15), M_FITTING, bevel=0.02)
    cyl(name + "Topmast", d0 * 0.32, top_h + 2.0, (0, y - 0.35, lh - 1.6 + (top_h + 2.0) / 2), M_SPAR, verts=10, r2=d0 * 0.22)
    th = lh - 1.6 + top_h + 2.0
    box(name + "Crosstrees", (1.8 * d0 / 0.6, 0.5, 0.08), (0, y - 0.35, th - 1.0), M_FITTING)
    cyl(name + "TopGallant", d0 * 0.2, tg_h + 1.4, (0, y - 0.45, th - 1.2 + (tg_h + 1.4) / 2), M_SPAR, verts=8, r2=d0 * 0.1)
    tgh = th - 1.2 + tg_h + 1.4
    cyl(name + "Truck", d0 * 0.16, 0.12, (0, y - 0.45, tgh + 0.06), M_FITTING, verts=8)
    for k, (h, L) in enumerate(yards):
        yz = z0 + h; yy = y - 0.45 - (0.1 if k else 0.0)
        r0 = 0.20 * L / 17.0 + 0.04
        tube(f"{name}Yard{k}", [Vector((-L / 2, yy, yz)), Vector((-L / 4, yy, yz)), Vector((0, yy, yz)), Vector((L / 4, yy, yz)), Vector((L / 2, yy, yz))],
             [r0 * 0.4] * 3 + [r0 * 0.75] * 4 + [r0] * 4 + [r0 * 0.75] * 4 + [r0 * 0.4] * 2, M_YARD, sides=6, n=4)
        # the furled sail: a lumpy roll lashed on top of the yard, deeper at the bunt (middle)
        pts = []; rr = []
        for i in range(25):
            t = i / 24; x = lerp(-L / 2 + 0.7, L / 2 - 0.7, t)
            bunt = math.exp(-((t - 0.5) / 0.18) ** 2)
            pts.append(Vector((x, yy + 0.05 + 0.08 * bunt, yz + r0 + 0.10 + 0.12 * bunt + 0.02 * noise.noise(Vector((x * 2.0, k, 1.0))))))
            rr.append(0.13 + 0.17 * bunt + 0.035 * noise.noise(Vector((x * 3.1, k * 2.0, 4.0))))
        s = tube(f"Sail{name}{k}", pts, rr, M_SAIL, sides=6, n=1)
        s["merge"] = "cloth.sail.furled"; SAILS.append((s, yz))
        # gaskets: rope turns round sail and yard
        for gx in [lerp(-L / 2 + 1.5, L / 2 - 1.5, i / 3) for i in range(4)]:
            torus(f"{name}Gasket{k}_{gx:.1f}", r0 + 0.2, 0.012, (gx, yy + 0.03, yz + 0.13), M_TARRED, rot=(0, math.pi / 2, 0), seg=6, mseg=3)
    return Vector((0, y, lh)), Vector((0, y - 0.35, th)), Vector((0, y - 0.45, tgh))

MAIN = mast("Main", MAIN_Y, 0.62, 16.5, 10.5, 6.5, [(15.2, 17.5), (22.8, 13.5), (28.6, 9.5)])
FORE = mast("Fore", FORE_Y, 0.58, 15.5, 10.0, 6.0, [(14.2, 16.5), (21.4, 12.8), (27.0, 9.0)])
MIZ = mast("Mizzen", MIZ_Y, 0.44, 12.5, 8.0, 5.0, [(11.4, 12.5), (17.4, 9.5)])

# the spanker: a gaff and a long boom reaching over the quarter-deck, the sail furled on the boom
mz0 = deck_z(0, MIZ_Y)
tube("SpankerBoom", [Vector((0, MIZ_Y + 0.35, mz0 + 2.75)), Vector((0, 0.0, mz0 + 2.85)), Vector((0, Y_STERN + 1.6, mz0 + 2.95))], (0.13, 0.09), M_SPAR, sides=10, n=3)
tube("SpankerGaff", [Vector((0, MIZ_Y + 0.35, mz0 + 9.6)), Vector((0, MIZ_Y + 4.2, mz0 + 10.9)), Vector((0, MIZ_Y + 7.2, mz0 + 11.9))], (0.11, 0.07), M_SPAR, sides=8, n=2)
pts = [Vector((0.02 * math.sin(i), lerp(MIZ_Y + 0.8, Y_STERN + 1.0, i / 16), mz0 + 3.0 + 0.004 * i + 0.04 * noise.noise(Vector((i * 0.7, 2, 2))))) for i in range(17)]
spk = tube("SailSpanker", pts, [0.15 + 0.05 * noise.noise(Vector((i * 0.9, 5, 5))) for i in range(17)], M_SAIL, sides=8, n=1)
spk["merge"] = "cloth.sail.furled"; SAILS.append((spk, mz0 + 2.85))
# the boom crutch at the taffrail
for s in (-1, 1):
    tube(f"BoomCrutch{s}", [Vector((s * 0.25, Y_STERN - 0.4, sheer(Y_STERN - 0.4))), Vector((0, Y_STERN - 0.4, mz0 + 2.75))], (0.05, 0.05), M_FITTING, sides=6, n=1)

# --- standing rigging: shrouds with ratlines, stays, backstays (tarred, dark)
def rope(name, a, b_, r=0.022, sag=0.0, mat=None, sides=4):
    a, b_ = Vector(a), Vector(b_); mid = (a + b_) / 2 - Vector((0, 0, sag))
    return tube(name, [a, mid, b_], (r, r), mat or M_TARRED, sides=sides, n=3 if sag else 1, caps=False)

def shrouds(name, mast_head, y_base, n, spread, ratlines=True):
    for side in (1, -1):
        ends = []
        for i in range(n):
            y = y_base + spread * (i - (n - 1) / 2) / max(1, n - 1) * 2 + 0.6
            z = rail_z(y) - 0.25
            foot = Vector((side * (hb(y, z) + 0.28), y, z))
            # the channel (chainwale) outboard, deadeyes
            head = mast_head + Vector((side * 0.32, 0.2, -0.3))
            rope(f"{name}Shroud{side}_{i}", foot + Vector((0, 0, 0.55)), head, 0.026)
            cyl(f"{name}Deadeye{side}_{i}", 0.09, 0.07, tuple(foot + Vector((0, 0, 0.42))), M_FITTING, verts=8, rot=(0, math.pi / 2, 0))
            rope(f"{name}Lanyard{side}_{i}", foot, foot + Vector((0, 0, 0.4)), 0.012, mat=M_MANILA, sides=3)
            ends.append((foot + Vector((0, 0, 0.55)), head))
        y0 = y_base - spread - 0.2; y1 = y_base + spread + 1.4
        box(f"{name}Channel{side}", (0.34, y1 - y0, 0.09), (side * (hb((y0 + y1) / 2, rail_z(y_base) - 0.3) + 0.12), (y0 + y1) / 2, rail_z(y_base) - 0.3), M_FITTING, bevel=0.01)
        if ratlines:
            L = (ends[0][1] - ends[0][0]).length
            h = 0.5
            while h < L * 0.86:
                t = h / L
                pts = [a.lerp(b2, t) for (a, b2) in ends]
                tube(f"{name}Ratline{side}_{h:.2f}", pts, (0.009, 0.009), M_TARRED, sides=3, n=1, caps=False)
                h += 0.48

shrouds("Main", MAIN[0], MAIN_Y, 5, 1.5)
shrouds("Fore", FORE[0], FORE_Y, 5, 1.4, ratlines=False)
shrouds("Miz", MIZ[0], MIZ_Y, 4, 1.0)
for nm, (lh, th, tgh), y in (("Main", MAIN, MAIN_Y), ("Fore", FORE, FORE_Y), ("Miz", MIZ, MIZ_Y)):
    for side in (1, -1):
        for i in range(2):   # topmast backstays and top-gallant backstays to the side, abaft the shrouds
            yy = y + 2.6 + 1.0 * i; z = rail_z(yy) - 0.25
            rope(f"{nm}Backstay{side}{i}", Vector((side * (hb(yy, z) + 0.25), yy, z + 0.5)), (th if i == 0 else tgh) + Vector((side * 0.12, 0, -0.2)), 0.02)
        for i in range(3):   # topmast shrouds from the top's rim
            rope(f"{nm}TopShroud{side}{i}", lh + Vector((side * 0.85, 0.15 + 0.3 * (i - 1), -0.35)), th + Vector((side * 0.12, 0, -0.9)), 0.015)
# stays
rope("ForeStay", FORE[0] + Vector((0, -0.2, -0.2)), BOWSPRIT_END, 0.035, sag=0.15)
rope("ForeTopStay", FORE[1], JIBBOOM_END, 0.025, sag=0.2)
rope("MainStay", MAIN[0] + Vector((0, -0.2, -0.2)), Vector((0, FORE_Y + 0.6, deck_z(0, FORE_Y) + 0.4)), 0.035, sag=0.2)
rope("MainTopStay", MAIN[1], FORE[0] + Vector((0, 0, -0.3)), 0.025, sag=0.2)
rope("MainTGStay", MAIN[2], FORE[1], 0.018, sag=0.25)
rope("MizStay", MIZ[0] + Vector((0, -0.2, -0.2)), Vector((0, MAIN_Y + 0.5, deck_z(0, MAIN_Y) + 1.2)), 0.03, sag=0.2)
rope("MizTopStay", MIZ[1], MAIN[0] + Vector((0, 0, -0.5)), 0.02, sag=0.2)
rope("ForeTGStay", FORE[2], JIBBOOM_END + Vector((0, 1.0, 0)), 0.015, sag=0.3)
# running rigging: lifts, braces, buntlines and halliards down to the pin rails (manila, paler)
for nm, (lh, th, tgh), y, L in (("Main", MAIN, MAIN_Y, 17.5), ("Fore", FORE, FORE_Y, 16.5), ("Miz", MIZ, MIZ_Y, 12.5)):
    yz = deck_z(0, y) + {"Main": 15.2, "Fore": 14.2, "Miz": 11.4}[nm]
    for side in (1, -1):
        arm = Vector((side * (L / 2 - 0.3), y - 0.45, yz))
        rope(f"{nm}Lift{side}", arm, lh + Vector((side * 0.3, 0, 0.3)), 0.012, mat=M_MANILA, sides=3)
        yb = y + (6.0 if nm != "Miz" else 3.8); zb = rail_z(yb) + 0.1
        rope(f"{nm}Brace{side}", arm, Vector((side * (hb(yb, zb) - 0.1), yb, zb)), 0.012, sag=0.6, mat=M_MANILA, sides=3)
        for i in range(2):
            rope(f"{nm}Clew{side}{i}", Vector((side * (1.5 + 2.5 * i), y - 0.4, yz + 0.2)), Vector((side * (hb(y + 1.0, rail_z(y)) - 0.1), y + 1.0 + 0.5 * i, rail_z(y + 1) + 0.1)), 0.01, mat=M_MANILA, sides=3)

# --- the tiller, carved from the long narrow lower jaw of a sperm whale
def tiller():
    rh = Vector((0, Y_STERN - 0.55, deck_z(0, Y_STERN - 0.55)))
    cyl("RudderHead", 0.2, 0.8, tuple(rh + Vector((0, 0, 0.35))), M_FITTING, verts=10)
    box("RudderCoat", (0.7, 0.7, 0.12), tuple(rh + Vector((0, 0, 0.06))), M_FITTING, bevel=0.03)
    pts = [rh + Vector((0, 0, 0.62)), rh + Vector((0.02, -1.0, 0.70)), rh + Vector((0.06, -2.1, 0.80)), rh + Vector((0.10, -3.0, 0.86)), rh + Vector((0.12, -3.55, 0.88))]
    N = len(catmull(pts, 4))
    radii = [lerp(0.095, 0.04, (i / (N - 1)) ** 0.8) for i in range(N)]
    t = tube("Tiller", pts, radii, M_JAW, sides=8, n=4)
    t.scale = (1.0, 1.0, 1.0)
    # the teeth still set along the jaw's upper edge, worn down; carved bands
    for i in range(14):
        f = 0.15 + i * 0.055
        p = catmull(pts, 4)[int(f * (N - 1))]
        for s in (-1, 1):
            cyl(f"TillerTooth{i}{s}", 0.016, 0.05, tuple(p + Vector((s * 0.035, 0, lerp(0.12, 0.05, f) * 0.9))), M_TEETH, verts=5, r2=0.005)
    for i, f in enumerate((0.12, 0.45, 0.8)):
        p = catmull(pts, 4)[int(f * (N - 1))]
        torus(f"TillerBand{i}", lerp(0.13, 0.05, f) + 0.004, 0.012, tuple(p), M_JAW, rot=(math.pi / 2, 0, 0), seg=12, mseg=4)
    # tiller ropes leading to the sides
    end = pts[-1]
    for s in (-1, 1):
        rope(f"TillerRope{s}", end + Vector((0, 0.05, 0)), Vector((s * (hb(-0.6, rail_z(-0.6)) - 0.15), -0.6, sheer(-0.6) + 0.5)), 0.014, sag=0.15, mat=M_MANILA, sides=4)
    return pts[2]
TILLER = tiller()

# --- the quarter-deck: companionway, skylight, a harness cask, coils of rope
def companion(x, y):
    z = deck_z(x, y)
    box("CompanionBody", (1.0, 1.1, 0.75), (x, y, z + 0.37), M_FITTING, bevel=0.02)
    box("CompanionSlide", (1.08, 0.7, 0.06), (x, y + 0.25, z + 0.78), M_RAIL, bevel=0.01)
    box("CompanionDoors", (0.7, 0.03, 0.6), (x, y - 0.56, z + 0.36), M_RAIL, bevel=0.005)
    box("CompanionSnow", (0.92, 0.5, 0.03), (x, y - 0.2, z + 0.765), M_SNOW, bevel=0.01)
companion(1.35, -1.2)
def skylight(x, y):
    z = deck_z(x, y)
    box("SkylightCoaming", (1.1, 1.4, 0.4), (x, y, z + 0.2), M_FITTING, bevel=0.02)
    for s in (-1, 1):
        box(f"SkylightLid{s}", (0.62, 1.42, 0.05), (x + s * 0.27, y, z + 0.5), M_RAIL, bevel=0.01, rot=(0, s * 0.42, 0))
        for k in range(3):
            box(f"SkylightGlass{s}{k}", (0.42, 0.34, 0.012), (x + s * 0.27, y - 0.45 + k * 0.45, z + 0.535 - 0.005), M_WINDOW, rot=(0, s * 0.42, 0))
    box("SkylightRidge", (0.08, 1.45, 0.08), (x, y, z + 0.63), M_FITTING)
skylight(0.0, -2.6)
def coil(name, x, y, r=0.35, turns=6, mat=None):
    z = deck_z(x, y)
    for k in range(turns):
        torus(f"{name}{k}", r - k * 0.035, 0.022, (x, y, z + 0.022 + 0.012 * (k % 2)), mat or M_MANILA, seg=12, mseg=3)
coil("CoilA", -2.6, -1.6); coil("CoilB", 2.4, -6.2, 0.4); coil("CoilC", -2.2, -13.6, 0.45, 7)
# water and harness casks lashed by the mizzen
def cask(name, p, s=1.0, lying=False, rot=0.0):
    prof = [(0.0, 0.0), (0.24 * s, 0.0), (0.27 * s, 0.1 * s), (0.30 * s, 0.38 * s), (0.27 * s, 0.66 * s), (0.24 * s, 0.76 * s), (0.0, 0.76 * s)]
    if lying:
        o = lathe(name, prof, (p.x, p.y, p.z + 0.3 * s), M_CASK, steps=8, rot=(0, math.pi / 2, rot))
        o.location.x -= 0.38 * s * math.cos(rot); o.location.y -= 0.38 * s * math.sin(rot)
    else:
        o = lathe(name, prof, tuple(p), M_CASK, steps=8, rot=(0, 0, rot))
    return o
for k, (x, y) in enumerate(((-2.7, -4.0), (-2.65, -4.75), (-2.1, -4.35))):
    cask(f"DeckCask{k}", Vector((x, y, deck_z(x, y))), 0.85, rot=k)

# --- the wigwam: slabs of black right-whale bone in a cone, laced, a tufted point, a triangular door to the bows
WIG = Vector((1.15, MAIN_Y + 3.1, 0.0)); WIG.z = deck_z(WIG.x, WIG.y)
def wigwam():
    c = WIG; R = 1.35; H = 3.05; apex = c + Vector((0, 0, H))
    n = 17
    for i in range(n):
        a = 2 * math.pi * i / n + math.pi / 2
        ang_from_front = math.atan2(math.sin(a - (-math.pi / 2)), math.cos(a - (-math.pi / 2)))
        if abs(ang_from_front) < 0.33: continue   # the triangular opening faces the bows (-Y)
        foot = c + Vector((R * math.cos(a), R * math.sin(a), 0.0))
        tang = Vector((-math.sin(a), math.cos(a), 0))
        w0 = random.uniform(0.26, 0.34)
        verts = []; faces = []
        NS = 8
        for j in range(NS + 1):
            t = j / NS
            p = foot.lerp(apex + Vector((0.04 * math.cos(a), 0.04 * math.sin(a), -0.1)), t)
            out = Vector((math.cos(a), math.sin(a), 0)) * (0.06 * math.sin(math.pi * t) + 0.012 * noise.noise(Vector((i, t * 4, 1))))
            w = w0 * (1 - t) ** 0.9 + 0.02
            for s in (-1, 1): verts.append(tuple(p + out + tang * s * w / 2))
        for j in range(NS):
            a0 = 2 * j; faces.append((a0, a0 + 1, a0 + 3, a0 + 2))
        o = mesh_from(f"Baleen{i}", verts, faces, M_BALEEN)
        sol = o.modifiers.new("Thick", 'SOLIDIFY'); sol.thickness = 0.025; sol.offset = 0
    # lacing: rope rings round the cone
    for k, h in enumerate((0.5, 1.1, 1.7, 2.3)):
        r = R * (1 - h / H) + 0.07
        pts = [c + Vector((r * math.cos(t), r * math.sin(t), h)) for t in [(-math.pi / 2 + 0.38) + (2 * math.pi - 0.76) * q / 16 for q in range(17)]]
        tube(f"WigwamLacing{k}", pts, (0.011, 0.011), M_MANILA, sides=4, n=1, caps=False)
    # the tufted point: loose hairy fibres of the bone, lashed at the apex, waving
    tuft = []
    for k in range(22):
        a = 2 * math.pi * k / 22 + random.uniform(-0.1, 0.1); el = random.uniform(0.4, 1.3)
        d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        L = random.uniform(0.25, 0.45)
        o = tube(f"Tuft{k}", [apex + Vector((0, 0, -0.08)), apex + d * L * 0.5 + Vector((0, 0, 0.0)), apex + d * L + Vector((0, 0, -0.12 * L))], (0.012, 0.002), M_BALEEN, sides=3, n=2)
        o["merge"] = "cloth.flag.tuft"; tuft.append(o)
    torus("TuftLashing", 0.07, 0.02, tuple(apex + Vector((0, 0, -0.18))), M_MANILA, seg=10, mseg=4)
    # Captain Peleg's old oaken chair inside, wriggling all over with carving, its bottom of interlaced bone
    ch = c + Vector((0.0, 0.25, 0))
    box("PelegSeat", (0.5, 0.46, 0.05), tuple(ch + Vector((0, 0, 0.45))), M_BALEEN)
    box("PelegSeatFrame", (0.56, 0.52, 0.06), tuple(ch + Vector((0, 0, 0.42))), M_CHAIR, bevel=0.01)
    for dx in (-1, 1):
        for dy in (-1, 1):
            tube(f"PelegLeg{dx}{dy}", [ch + Vector((dx * 0.24, dy * 0.21, 0.0)), ch + Vector((dx * 0.25, dy * 0.22, 0.2)), ch + Vector((dx * 0.24, dy * 0.21, 0.42))], (0.03, 0.03), M_CHAIR, sides=6, n=2)
    for k in range(5):
        tube(f"PelegBack{k}", [ch + Vector((-0.22 + k * 0.11, 0.22, 0.45)), ch + Vector((-0.22 + k * 0.11 + 0.02 * math.sin(k), 0.27, 0.8)), ch + Vector((-0.22 + k * 0.11, 0.25, 1.05))], (0.022, 0.018), M_CHAIR, sides=6, n=3)
    tube("PelegCrest", [ch + Vector((-0.28, 0.25, 1.05)), ch + Vector((0, 0.27, 1.15)), ch + Vector((0.28, 0.25, 1.05))], (0.035, 0.035), M_CHAIR, sides=6, n=3)
    return tuft
TUFT = wigwam()

# --- the try-works between the main and fore masts, the main hatch, the windlass
TRY_Y = FORE_Y + 3.3
z = deck_z(0, TRY_Y)
box("TryworksBase", (2.9, 2.6, 1.05), (0, TRY_Y, z + 0.52), M_BRICK, bevel=0.03)
box("TryworksCurb", (3.1, 2.8, 0.1), (0, TRY_Y, z + 0.05), M_FITTING, bevel=0.01)
for s in (-1, 1):
    cyl(f"TryPotLid{s}", 0.62, 0.08, (s * 0.72, TRY_Y + 0.2, z + 1.08), M_FITTING, verts=16)
    box(f"TryworksChimney{s}", (0.45, 0.45, 0.9), (s * 0.72, TRY_Y - 1.0, z + 1.45), M_BRICK, bevel=0.02)
box("TryworksHatch", (3.0, 0.9, 0.08), (0, TRY_Y + 1.6, z + 0.45), M_FITTING, bevel=0.01)
HATCH_Y = MAIN_Y - 2.7
z = deck_z(0, HATCH_Y)
box("MainHatchCoaming", (2.2, 2.6, 0.4), (0, HATCH_Y, z + 0.2), M_FITTING, bevel=0.02)
for k in range(5):
    box(f"MainHatchCover{k}", (2.1, 0.5, 0.06), (0, HATCH_Y - 1.0 + k * 0.5, z + 0.42), M_RAIL, bevel=0.008)
box("HatchTarpaulin", (2.3, 2.7, 0.03), (0, HATCH_Y, z + 0.46), M_SAIL, bevel=0.01)
for k in range(4):
    cask(f"HatchCask{k}", Vector((-1.6 + (k % 2) * 0.7, HATCH_Y - 0.6 + (k // 2) * 0.75, z)), 1.0, rot=k * 0.7)
cask("HatchCaskLying", Vector((1.5, HATCH_Y + 0.3, z)), 1.0, lying=True, rot=0.2)
WIN_Y = Y_BOW + 3.4
z = deck_z(0, WIN_Y)
tube("Windlass", [Vector((-1.6, WIN_Y, z + 0.55)), Vector((1.6, WIN_Y, z + 0.55))], (0.22, 0.22), M_FITTING, sides=10, n=1)
for s in (-1, 1): box(f"WindlassBitt{s}", (0.3, 0.4, 1.0), (s * 1.75, WIN_Y, z + 0.5), M_FITTING, bevel=0.02)
# the anchors hung at the cat-heads
for s in (-1, 1):
    y = Y_BOW + 2.2
    p = Vector((s * (hb(y, rail_z(y)) + 0.25), y, rail_z(y) - 0.4))
    tube(f"AnchorShank{s}", [p, p + Vector((0, 0.3, -1.8))], (0.07, 0.06), M_IRON, sides=6, n=1)
    tube(f"AnchorArms{s}", [p + Vector((0, -0.4, -1.65)), p + Vector((0, 0.3, -1.95)), p + Vector((0, 0.95, -1.55))], (0.06, 0.05), M_IRON, sides=6, n=3)
    tube(f"AnchorStock{s}", [p + Vector((-0.9, 0, 0.1)), p + Vector((0.9, 0, 0.1))], (0.08, 0.08), M_FITTING, sides=6, n=1)

# --- two whale-boats on the larboard davits, forward (over the wharf's edge)
def whaleboat(name, cy, cx, cz):
    L, B, D = 8.4, 1.85, 0.72
    verts = []; faces = []; N = 14; M = 6
    for i in range(N + 1):
        t = i / N; y = cy - L / 2 + L * t
        w = B / 2 * math.sin(math.pi * t) ** 0.7
        sh = 0.18 * (2 * t - 1) ** 4
        for j in range(M + 1):
            a = math.pi * j / M
            verts.append((cx + w * math.cos(a), y, cz + sh - D * math.sin(a) * (0.6 + 0.4 * math.sin(math.pi * t)) * 1.0))
    for i in range(N):
        for j in range(M):
            a0 = i * (M + 1) + j; faces.append((a0, a0 + M + 1, a0 + M + 2, a0 + 1))
    o = mesh_from(name, verts, faces, M_FITTING)
    sol = o.modifiers.new("Thick", 'SOLIDIFY'); sol.thickness = 0.03
    for k in range(5):
        box(f"{name}Thwart{k}", (B * 0.85, 0.22, 0.04), (cx, cy - L / 2 + 1.4 + k * 1.4, cz - 0.15), M_RAIL)
    for k in range(5):   # oars and a harpoon crotch, the line tubs
        tube(f"{name}Oar{k}", [Vector((cx + 0.3 - k * 0.15, cy - 3.6, cz - 0.05)), Vector((cx + 0.3 - k * 0.15, cy + 3.8, cz + 0.05))], (0.025, 0.02), M_YARD, sides=5, n=1)
    cask(f"{name}Tub", Vector((cx, cy + 0.6, cz - 0.55)), 0.7)
    return o
for k, cy in enumerate((MAIN_Y - 4.0, FORE_Y + 0.6)):
    zr = rail_z(cy)
    x = hb(cy, zr) + 1.25
    whaleboat(f"Whaleboat{k}", cy, x, zr + 0.85)
    for dy in (-3.4, 3.4):
        y = cy + dy; zr2 = rail_z(y)
        tube(f"Davit{k}{dy}", [Vector(((hb(y, zr2) - 0.1), y, zr2 - 0.6)), Vector(((hb(y, zr2) + 0.2), y, zr2 + 1.6)), Vector((x, y, zr2 + 1.75))], (0.07, 0.06), M_FITTING, sides=6, n=3)
        rope(f"DavitFall{k}{dy}", Vector((x, y, zr2 + 1.7)), Vector((x, y, zr + 0.95)), 0.014, mat=M_MANILA, sides=3)

SHIP_OBJS = [o for o in COLL.objects if o not in _before_ship]

# ============================================================================= THE WHARF (ship frame)
_before_wharf = set(COLL.objects)
WY0, WY1, WX1 = -78.0, 30.0, WHARF_X + 24.0
def wharf():
    # the face: spiles (piles) driven along the edge, walings, a cap-log (stringpiece)
    y = WY0; k = 0
    while y < WY1:
        tilt = (random.uniform(-0.03, 0.03), random.uniform(-0.03, 0.03), 0)
        cyl(f"Spile{k}", random.uniform(0.15, 0.19), WHARF_Z - (WL - 2.5) + 0.25, (WHARF_X + 0.1 + random.uniform(-0.03, 0.05), y, (WHARF_Z + 0.25 + WL - 2.5) / 2), M_WHARF, verts=8, rot=tilt)
        y += random.uniform(1.05, 1.35); k += 1
    for z, h in ((WHARF_Z - 0.12, 0.3), (WL + 0.55, 0.25)):
        box(f"Waling{z:.1f}", (0.25, WY1 - WY0, h), (WHARF_X + 0.32, (WY0 + WY1) / 2, z), M_WHARF, bevel=0.02)
    box("WharfFill", (WX1 - WHARF_X - 0.4, WY1 - WY0, WHARF_Z - (WL - 3.0)), ((WHARF_X + 0.4 + WX1) / 2, (WY0 + WY1) / 2, (WHARF_Z + WL - 3.0) / 2), M_WHARF)
    box("Stringpiece", (0.4, WY1 - WY0, 0.3), (WHARF_X + 0.35, (WY0 + WY1) / 2, WHARF_Z + 0.08), M_WHARF, bevel=0.03)
    # the top: a ground grid (snow attribute from shelter), with the plank cartway along the edge
    NX, NY = 18, 40
    verts = []; faces = []; snow = []
    for j in range(NY + 1):
        for i in range(NX + 1):
            x = lerp(WHARF_X + 0.55, WX1, i / NX) ** 1.0; y = lerp(WY0, WY1, j / NY)
            h = 0.04 * noise.noise(Vector((x * 0.3, y * 0.3, 7.0)))
            verts.append((x, y, WHARF_Z + 0.1 + h)); snow.append(0.0)
    for j in range(NY):
        for i in range(NX):
            a = j * (NX + 1) + i; faces.append((a, a + 1, a + NX + 2, a + NX + 1))
    o = orient(mesh_from("WharfTop", verts, faces, M_GROUND), lambda c: (0, 0, 1))
    set_attr(o, "snow", [smoothstep(WX1 - 7, WX1 - 3.5, v[0]) * 0.8 for v in verts])
    # bollards and a mooring line from the ship
    for k, y in enumerate((-22.0, -3.0, 9.0)):
        cyl(f"Bollard{k}", 0.22, 0.75, (WHARF_X + 1.1, y, WHARF_Z + 0.45), M_WHARF, verts=10)
    rope("BowLine", Vector((hb(-23.0, rail_z(-23)) - 0.1, -23.0, rail_z(-23) + 0.1)), Vector((WHARF_X + 1.1, -22.0 - 3.0, WHARF_Z + 0.7)), 0.03, sag=0.6, mat=M_MANILA)
    rope("SternLine", Vector((hb(1.5, rail_z(1.5)) - 0.1, 1.5, rail_z(1.5) + 0.1)), Vector((WHARF_X + 1.1, 9.0, WHARF_Z + 0.7)), 0.03, sag=0.5, mat=M_MANILA)
    rope("SpringLine", Vector((hb(-8.0, rail_z(-8)) - 0.1, -8.0, rail_z(-8) + 0.1)), Vector((WHARF_X + 1.1, -3.0, WHARF_Z + 0.7)), 0.028, sag=0.35, mat=M_MANILA)
    # fenders between hull and wharf (old spars hung on ropes)
    for k, y in enumerate((-17.0, -9.0, -1.5)):
        tube(f"Fender{k}", [Vector((WHARF_X - 0.12, y, WL + 0.3)), Vector((WHARF_X - 0.12, y, WHARF_Z))], (0.15, 0.15), M_WHARF, sides=8, n=1)
    # oil casks in tiers along the wharf, staves and hoops, a few lying; a try-pot; an anchor
    rng = random.Random(4)
    for k in range(27):
        row = k % 3; col = k // 3
        x = WHARF_X + 3.2 + row * 0.75 + rng.uniform(-0.05, 0.05); y = -36.0 + col * 0.72 + rng.uniform(-0.04, 0.04)
        if rng.random() < 0.12: continue
        o = cask(f"WharfCask{k}", Vector((x, y, WHARF_Z + 0.1)), 1.15, rot=rng.uniform(0, 6))
    for k in range(6):
        cask(f"WharfCaskTop{k}", Vector((WHARF_X + 3.55 + (k % 2) * 0.75, -35.6 + (k // 2) * 1.45, WHARF_Z + 0.1 + 0.88)), 1.15, rot=rng.uniform(0, 6))
    for k in range(5):
        cask(f"WharfCaskLying{k}", Vector((WHARF_X + 6.2, -12.0 + k * 1.0, WHARF_Z + 0.1)), 1.15, lying=True, rot=math.pi / 2 + rng.uniform(-0.1, 0.1))
    # a pile of new staves and hoops for the cooper, a hand-cart
    for k in range(14):
        box(f"Stave{k}", (0.1, 0.95, 0.02), (WHARF_X + 4.0 + rng.uniform(-0.2, 0.2), -6.0 + rng.uniform(-0.3, 0.3), WHARF_Z + 0.12 + k * 0.02), M_FITTING, rot=(0, 0, rng.uniform(-0.3, 0.3)))
    lathe("TryPot", [(0.0, 0.0), (0.45, 0.02), (0.7, 0.25), (0.78, 0.55), (0.8, 0.62), (0.74, 0.62), (0.0, 0.1)], (WHARF_X + 4.4, -18.5, WHARF_Z + 0.1), M_IRON, steps=16)
    # the sheds: a long shingled warehouse and a cooper's shop, roofs whitened with old snow
    def shed(name, x0, x1, y0, y1, wall_h, pitch):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        box(name + "Walls", (x1 - x0, y1 - y0, wall_h), (cx, cy, WHARF_Z + 0.1 + wall_h / 2), M_CLAP)
        rh = (x1 - x0) / 2 * pitch
        verts = [(x0 - 0.3, y0 - 0.3, WHARF_Z + 0.1 + wall_h), (cx, y0 - 0.3, WHARF_Z + 0.1 + wall_h + rh), (x1 + 0.3, y0 - 0.3, WHARF_Z + 0.1 + wall_h),
                 (x0 - 0.3, y1 + 0.3, WHARF_Z + 0.1 + wall_h), (cx, y1 + 0.3, WHARF_Z + 0.1 + wall_h + rh), (x1 + 0.3, y1 + 0.3, WHARF_Z + 0.1 + wall_h)]
        orient(mesh_from(name + "Roof", verts, [(0, 3, 4, 1), (1, 4, 5, 2)], M_SHINGLE, smooth=False), lambda c: (0, 0, 1))
        for (yy, ss) in ((y0 - 0.02, -1), (y1 + 0.02, 1)):
            orient(mesh_from(name + f"Gable{ss}", [(x0, yy, WHARF_Z + 0.1 + wall_h), (cx, yy, WHARF_Z + 0.1 + wall_h + rh), (x1, yy, WHARF_Z + 0.1 + wall_h)], [(0, 1, 2)], M_CLAP, smooth=False), lambda c, ss=ss: (0, ss, 0))
        # doors and windows on the side facing the ship (x0)
        n = int((y1 - y0) / 4.5)
        for i in range(n):
            yy = y0 + (i + 0.5) * (y1 - y0) / n
            if i % 3 == 1: box(f"{name}Door{i}", (0.06, 1.8, 2.3), (x0 - 0.03, yy, WHARF_Z + 0.1 + 1.15), M_FITTING)
            else: box(f"{name}Win{i}", (0.05, 0.8, 1.0), (x0 - 0.03, yy, WHARF_Z + 0.1 + wall_h * 0.6), M_WINDOW)
    shed("Warehouse", WHARF_X + 12.0, WHARF_X + 20.0, -60.0, -18.0, 5.2, 0.55)
    shed("CooperShop", WHARF_X + 11.0, WHARF_X + 17.0, -8.0, 4.0, 3.4, 0.6)
    shed("OilShed", WHARF_X + 12.5, WHARF_X + 19.0, 9.0, 24.0, 4.0, 0.55)
wharf()
WHARF_OBJS = [o for o in COLL.objects if o not in _before_wharf]

# ============================================================================= far scenery (ship frame, then turned with the rest)
_before_far = set(COLL.objects)
def far_ring_patch(name, mat, bearing0, bearing1, dist, height_fn, N=60):
    """A band of distant land between two bearings (ship-frame angle from -Y, positive towards +X), seen from the
    reader; height_fn(t) gives the skyline height above the water."""
    verts = []; faces = []
    for i in range(N + 1):
        t = i / N; a = math.radians(lerp(bearing0, bearing1, t))
        d = Vector((math.sin(a), -math.cos(a), 0))
        p0 = Vector((RX, RY, 0)) + d * dist
        h = height_fn(t)
        verts += [(p0.x, p0.y, WL - 1.0), (p0.x + d.x * 8, p0.y + d.y * 8, WL + h)]
    for i in range(N):
        a0 = 2 * i; faces.append((a0, a0 + 2, a0 + 3, a0 + 1))
    o = orient(mesh_from(name, verts, faces, mat), lambda c: (RX - c.x, RY - c.y, 0.0))
    o["merge"] = name
    return o
# the low sand of the far shore across the harbour (to starboard and ahead), whitened with old snow
far_ring_patch("far.Shore", M_FARSHORE, -150.0, -20.0, 360.0, lambda t: 3.5 + 3.0 * abs(noise.noise(Vector((t * 9, 1, 1)))) + 2.0 * math.sin(t * 7) ** 2)
# Nantucket town on its rise beyond the wharf (to port), roofs and two church towers and a windmill
def town():
    rng = random.Random(9)
    for k in range(70):
        a = math.radians(rng.uniform(22, 150)); dist = rng.uniform(120, 260)
        d = Vector((math.sin(a), -math.cos(a), 0)); p = Vector((RX, RY, 0)) + d * dist
        rise = WHARF_Z + 2.0 + (dist - 120) * 0.12
        w, l, h = rng.uniform(6, 10), rng.uniform(7, 12), rng.uniform(5, 8)
        o = box(f"FarHouse{k}", (w, l, h), (p.x, p.y, rise + h / 2), M_FARTOWN, rot=(0, 0, a + rng.uniform(-0.2, 0.2)))
        o["merge"] = "Town"
        verts = [(-w / 2 - 0.3, -l / 2, 0), (0, -l / 2, h * 0.45), (w / 2 + 0.3, -l / 2, 0), (-w / 2 - 0.3, l / 2, 0), (0, l / 2, h * 0.45), (w / 2 + 0.3, l / 2, 0)]
        r = orient(mesh_from(f"FarRoof{k}", verts, [(0, 3, 4, 1), (1, 4, 5, 2), (0, 1, 2), (3, 5, 4)], M_SNOW, smooth=False), lambda c: (c.x, c.y, 1.0))
        r.location = (p.x, p.y, rise + h); r.rotation_euler = (0, 0, a + rng.uniform(-0.2, 0.2)); r["merge"] = "Town"
    for k, (a, dist, h) in enumerate(((58, 210, 34), (95, 240, 30))):
        aa = math.radians(a); d = Vector((math.sin(aa), -math.cos(aa), 0)); p = Vector((RX, RY, 0)) + d * dist
        rise = WHARF_Z + 2.0 + (dist - 120) * 0.12
        o = box(f"FarTower{k}", (5, 5, h), (p.x, p.y, rise + h / 2), M_FARTOWN); o["merge"] = "Town"
        o = box(f"FarBelfry{k}", (3.6, 3.6, 5), (p.x, p.y, rise + h + 2.5), M_FARTOWN); o["merge"] = "Town"
        o = cyl(f"FarSpire{k}", 2.4, 6 if k == 0 else 3, (p.x, p.y, rise + h + 5 + (3 if k == 0 else 1.5)), M_FARTOWN, verts=8, r2=0.1 if k == 0 else 2.0); o["merge"] = "Town"
    aa = math.radians(128); d = Vector((math.sin(aa), -math.cos(aa), 0)); p = Vector((RX, RY, 0)) + d * 300
    o = cyl("FarMill", 2.5, 11, (p.x, p.y, WHARF_Z + 2 + 22 + 5.5), M_FARTOWN, verts=8, r2=1.8); o["merge"] = "Town"
    for k in range(4):
        o = box(f"FarMillSail{k}", (0.6, 0.3, 9.0), (p.x, p.y - 2.6, WHARF_Z + 2 + 22 + 10), M_FARTOWN, rot=(0, k * math.pi / 2 + 0.4, 0)); o["merge"] = "Town"
    # the land under the town
    far_ring_patch("far.TownLand", M_FARSHORE, 20.0, 155.0, 270.0, lambda t: 22.0 + 6.0 * math.sin(t * 3.0) + 2.0 * noise.noise(Vector((t * 8, 2, 2)))).__setitem__("merge", "far.Shore")
town()
# ships at anchor in the harbour and one across the wharf
def far_ship(name, p, yaw, s=1.0):
    parts = []
    parts.append(box(name + "Hull", (2.0 * s, 9.0 * s, 1.6 * s), (p.x, p.y, WL + 0.6 * s), M_FARSHIP, rot=(0, 0, yaw)))
    for k, dy in enumerate((-2.8, 0.3, 3.0)):
        q = p + Vector((-math.sin(yaw) * dy * s, math.cos(yaw) * dy * s, 0))
        parts.append(cyl(name + f"Mast{k}", 0.12 * s, 10 * s, (q.x, q.y, WL + 1.4 * s + 5 * s), M_FARSHIP, verts=5))
        parts.append(box(name + f"Yard{k}", (5 * s, 0.25 * s, 0.25 * s), (q.x, q.y, WL + 8.5 * s), M_FARSHIP, rot=(0, 0, yaw)))
    for o in parts: o["merge"] = "Ships"
far_ship("FarShipA", Vector((-95.0, -170.0, 0)), 0.5, 2.6)
far_ship("FarShipB", Vector((-170.0, -60.0, 0)), 1.9, 2.4)
far_ship("FarShipC", Vector((40.0, -95.0, 0)), 0.05, 2.9)     # across the wharf, beyond the warehouse
# Brant Point's light at the harbour mouth, far ahead-right
aa = math.radians(-62); d = Vector((math.sin(aa), -math.cos(aa), 0)); p = Vector((RX, RY, 0)) + d * 340
o = cyl("FarLight", 1.6, 9.0, (p.x, p.y, WL + 4.5 + 3.0), M_FARSHORE, verts=8, r2=1.2); o["merge"] = "far.Shore"
o = cyl("FarLightLantern", 1.3, 2.0, (p.x, p.y, WL + 13.0), M_FARSHIP, verts=8, r2=0.4); o["merge"] = "far.Shore"
FAR_OBJS = [o for o in COLL.objects if o not in _before_far]

# ============================================================================= the harbour water (ship frame), far sea, sky
def hull_outline_dist(x, y):
    """Distance (m) outside the hull's waterline (negative inside)."""
    if y < Y_BOW - 0.3 or y > Y_STERN: return min(abs(y - Y_BOW), abs(y - Y_STERN)) + max(0.0, abs(x) - 2.0)
    return abs(x) - hb(y, WL)

def water():
    N = 60; ext = NEAR_R; k = 4.0
    cxy = Vector((RX - 6.0, RY - 6.0, 0))
    def coord(t): return ext * math.sinh(k * t) / math.sinh(k)
    verts = []; faces = []; foam = []
    for j in range(N + 1):
        for i in range(N + 1):
            x = cxy.x + coord(2 * i / N - 1); y = cxy.y + coord(2 * j / N - 1)
            r = math.hypot(x - RX, y - RY)
            if r > NEAR_R:          # pull the corners in to a circle, a touch under the far sea's edge
                x = RX + (x - RX) * NEAR_R / r; y = RY + (y - RY) * NEAR_R / r
            z = WL - (0.06 if r > NEAR_R - 2 else 0.0)
            verts.append((x, y, z))
    def inside(v):
        x, y, _ = v
        return hull_outline_dist(x, y) < -0.35 or (x > WHARF_X + 0.35 and WY0 + 1 < y < WY1 - 1)
    for j in range(N):
        for i in range(N):
            a = j * (N + 1) + i; quad = (a, a + 1, a + N + 2, a + N + 1)
            if all(inside(verts[q]) for q in quad): continue
            faces.append(quad)
    o = orient(mesh_from("water.ocean.harbour", verts, faces, M_WATER), lambda c: (0, 0, 1))
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    return o
WATER = water()
def foam_at(p):
    x, y = p.x, p.y
    d_h = hull_outline_dist(x, y)
    d_w = abs(x - (WHARF_X + 0.1)) if WY0 < y < WY1 else 99.0
    return max(smoothstep(2.5, 0.1, d_h), smoothstep(2.0, 0.1, d_w) * 0.85)

# ============================================================================= turn the ship-frame world into place
for o in list(COLL.objects):
    if o.parent is None:
        o.matrix_world = SHIP_M @ o.matrix_world
bpy.context.view_layer.update()
# water: COLOR_0 (foam in G, computed in the ship frame) and UV = world metres / 10
SHIP_MI = SHIP_M.inverted()
set_weight_colour(WATER, foam_fn=lambda p: foam_at(SHIP_MI @ p), kind="water")
me = WATER.data; uvl = me.uv_layers.new(name="UVMap"); mw = WATER.matrix_world
for li, loop in enumerate(me.loops):
    p = mw @ me.vertices[loop.vertex_index].co; uvl.data[li].uv = (p.x / 10.0, p.y / 10.0)
# sway weights: furled sails barely move (0 at the yard, 0.35 at the bunt's underside); the wigwam's tuft moves freely
for s, yz in SAILS:
    s_mw = s.matrix_world
    zs = [(s_mw @ v.co).z for v in s.data.vertices]; zmax = max(zs); zmin = min(zs)
    set_weight_colour(s, weight_fn=lambda p, zmax=zmax, zmin=zmin: 0.35 * smoothstep(zmax, zmin, p.z) ** 1.5)
apex_w = SHIP_M @ (WIG + Vector((0, 0, 3.05)))
for t in TUFT:
    set_weight_colour(t, weight_fn=lambda p: smoothstep(0.05, 0.4, (p - apex_w).length))

disc_me = None
def far_sea(name="far.Sea"):
    verts = []; faces = []; seg = 96
    for r in (NEAR_R - 4.0, SKY_R - 2.0):
        for i in range(seg):
            a = 2 * math.pi * i / seg; verts.append((r * math.cos(a), r * math.sin(a), WL - 0.03))
    for i in range(seg):
        j = (i + 1) % seg; faces.append((i, j, seg + j, seg + i))
    o = orient(mesh_from(name, verts, faces, M_FARSEA), lambda c: (0, 0, 1)); return o
far_sea()
sky_dome("SkyDome", M_SKY, SKY_R, seg=48, rings=16, el_min=-6.0)

# ============================================================================= markers, sounds, lights, anchors
def W(p): return tuple(SHIP_M @ Vector(p))
sound_empty("sound.gulls.wharf", W((WHARF_X + 8.0, -14.0, WHARF_Z + 9.0)))
sound_empty("sound.gulls.harbour", W((-40.0, -30.0, 14.0)))
sound_empty("sound.rigging.main", W((0.0, MAIN_Y, 12.0)))
sound_empty("sound.surf.wharf", W((WHARF_X + 0.2, -6.0, WL + 0.3)))
sound_empty("sound.surf.hull", W((-(hb(-3.0, WL) + 0.3), -3.0, WL + 0.2)))
anchor("reader.entrance", (0.0, 0.0, 0.0))
anchor("reader.look", (0.0, -1.0, EYE))
anchor("scene.centre", W((0.0, MAIN_Y, deck_z(0, MAIN_Y))))
anchor("ship.tiller", W(tuple(TILLER)))
anchor("ship.wigwam", W(tuple(WIG)))
anchor("ship.mainmast", W((0, MAIN_Y, deck_z(0, MAIN_Y) + 2.0)))
anchor("ship.bow", W((0, Y_BOW, rail_z(Y_BOW))))
anchor("wharf.edge", W((WHARF_X + 0.5, -6.0, WHARF_Z)))

sun = light_obj("light.sun", 'SUN', 3.4, (1.0, 0.93, 0.82), tuple(SUN_DIR * 30), direction=-SUN_DIR, angle=math.radians(1.0))
sky_l = light_obj("light.sky", 'SUN', 0.35, (0.62, 0.74, 1.0), (0, 0, 14), direction=(0.1, -0.15, -1.0), angle=math.radians(60))
sky_l.data.use_shadow = False
world = bpy.data.worlds.new("NantucketWinter"); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]
try:
    skyn = wn.nodes.new("ShaderNodeTexSky"); skyn.sky_type = 'MULTIPLE_SCATTERING'; skyn.sun_disc = False
    skyn.sun_elevation = math.asin(SUN_DIR.z); skyn.sun_rotation = math.atan2(SUN_DIR.x, SUN_DIR.y); skyn.altitude = 50
    wn.links.new(skyn.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.12
except Exception as e:
    print("sky texture unavailable:", e); bg.inputs["Color"].default_value = (0.5, 0.6, 0.75, 1); bg.inputs["Strength"].default_value = 0.6

preview_page(EYE)
E = (0.0, 0.0, EYE)
camera("Cam_Reader", E, (0.0, -10.0, 1.2), clip_end=600)
camera("Cam_Page", E, (0.0, -10.0, 1.4), clip_end=600)
camera("Cam_Left", E, (10.0, -2.0, 1.2), clip_end=600)
camera("Cam_Right", E, (-10.0, -1.5, 1.0), clip_end=600)
camera("Cam_Behind", E, (0.5, 10.0, 1.0), clip_end=600)
camera("Cam_Down", E, (0.2, -1.2, 0.0), lens=16, clip_end=600)
camera("Cam_Up", E, tuple(Vector(W((0, MAIN_Y, 18.0)))), lens=16, clip_end=600)
camera("Cam_Over", (-0.9, -1.2, 1.5), (-4.0, -4.5, WL), lens=20, clip_end=600)
camera("Cam_Wigwam", E, W(tuple(WIG + Vector((0, 0, 1.4)))), lens=35, clip_end=600)
camera("Cam_Bow", E, W((0, -18.0, 3.0)), lens=24, clip_end=600)

if not args.nosave: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(S["out"], "pequod_deck_source.blend"))
print_budget()
if args.render:
    render_cams(SID, exposure={"*": -0.6})
if args.bake or args.export:
    T = args.tex
    size_for = {"M_DeckPlanks": T, "M_HullOuter": T, "M_Bulwark": T // 2, "M_RailCap": T // 2, "M_Spar": T // 2, "M_Yard": T // 4,
                "M_Fittings": T // 2, "M_WharfGround": T, "M_WharfTimber": T // 2, "M_Cask": T // 2, "M_Clapboard": T // 2, "M_Shingles": T // 4,
                "M_JawBone": T // 4, "M_Baleen": T // 4, "M_TarredRope": T // 4, "M_ManilaRope": T // 4, "M_Sail": T // 2, "M_Iron": T // 4,
                "M_TryworksBrick": T // 4, "M_Snow": T // 4, "M_SkyDome": T, "M_FarShore": T // 4, "M_FarSea": T // 8, "M_FarTown": T // 4,
                "M_FarShips": T // 8, "M_ChairOak": T // 8, "M_Teeth": T // 8, "M_DarkWindow": T // 8}
    # backdrop groups use their 'merge' names; their material sizes come from the material
    bake_and_export("pequod_deck.gltf", size_for, default_size=256, keep_names={"M_SkyDome": "SkyDome", "M_FarSea": "far.Sea"},
                    keep_uv={"SkyDome"}, emit_only={"SkyDome"})
print("DONE")
