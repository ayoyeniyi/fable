"""
Fable: the Battery, Manhattan, on a breezy Sunday afternoon in early autumn (Moby-Dick, chapter 1, "Loomings").

"There now is your insular city of the Manhattoes, belted round by wharves as Indian isles by coral reefs - commerce
surrounds it with her surf. ... Its extreme downtown is the battery, where that noble mole is washed by waves, and
cooled by breezes, which a few hours previous were out of sight of land. Look at the crowds of water-gazers there.
Circumambulate the city of a dreamy Sabbath afternoon. ... Posted like silent sentinels all around the town, stand
thousands upon thousands of mortal men fixed in ocean reveries. Some leaning against the spiles; some seated upon the
pier-heads; some looking over the bulwarks of ships from China ... loitering under the shady lee of yonder warehouses
will not suffice."

No people (the crowds of water-gazers are only implied: empty benches, a distant murmur). The 1840s-50s Battery: a
broad promenade along the granite sea wall (the mole) with an iron railing, elms behind it, gas lamps and wooden
benches. The reader stands at the railing at the southern tip, facing south down the Upper Bay towards the Narrows
(Blender -Y): behind the page is open water and the low blue hills of Staten Island, far off. To the left, Governors
Island with the round red fort of Castle Williams, ships at anchor, and nearer, the East River piers with a forest
of masts; to the right, Castle Garden (the old round fort, now a hall, with its roof and flag) on its pier and
footbridge, Bedloe's Island and the Jersey shore. Behind: the elms and lawns of the Battery and the brick houses of
State Street. The sun is in the west-south-west at about 4 pm, 30 degrees up, ahead to the right; a fresh breeze from
the sea (south-south-west) sets the elms and the flags moving and the bay in small waves.

Everything is procedural (no downloaded models, textures or HDRIs). Shared helpers: blender/mobydick_kit.py.

Node names Unity relies on:
  anchor.reader.entrance (feet, promenade z=0), anchor.reader.look, anchor.scene.centre (the railing in front),
  anchor.battery.castleGarden, anchor.battery.castleWilliams
  light.sun, light.sky (SUN)
  water.ocean.bay      the bay: its own mesh, dense along the sea wall (about 0.5 m) and coarser out to 150 m;
                       UV = world metres / 10; COLOR_0 G = foam where the waves wash the mole and Castle Garden
  far.Sea, far.Land, far.Town, far.Ships, SkyDome (unlit backdrop)
  veg.crown.elms       the elms' leaf crowns (R: 0 near the trunk, 1 at the crown's rim)
  cloth.flag.castle    Castle Garden's flag (R: 0 at the hoist, 1 at the fly); cloth.flag.ships the pennants
  sound.surf.mole, sound.surf.castle, sound.wind-trees.elms, sound.gulls.bay, sound.crowd.promenade
Register as outdoor (Outdoor = true), wind from the south-south-west (from the sea, ahead-right of the reader).

Axes: metres, Blender +Z up, the reader at the world origin facing -Y (bearing 185, a little west of south). The
water is at z = WL. Distant places are placed by true bearing and scaled into the 600 m backdrop.

Run headless:
  blender -b -P blender/build_battery_waterfront.py -- --out out/battery-waterfront --render --quick --res 900
  blender -b -P blender/build_battery_waterfront.py -- --out out/battery-waterfront --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, Euler, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mobydick_kit import *

args = parse_args("out/battery-waterfront")
scene, COLL = reset_scene("BatteryWaterfront", args)
random.seed(1851)
SID = "battery-waterfront"

EYE = 1.55
WL = -2.25
FACING = 185.0                                   # true bearing of the look direction (-Y)
SKY_R = 600.0
NEAR_R = 150.0
SUN_DIR = None                                   # set below from bearing/elevation

def geo(bearing, dist, z=0.0):
    """World point at a true bearing (degrees) and distance from the reader."""
    r = math.radians(bearing - FACING)
    return Vector((-math.sin(r) * dist, -math.cos(r) * dist, z))
def bearing_dir(bearing, el):
    r = math.radians(bearing - FACING); e = math.radians(el)
    return Vector((-math.sin(r) * math.cos(e), -math.cos(r) * math.cos(e), math.sin(e))).normalized()
SUN_DIR = bearing_dir(248.0, 30.0)
WIND_FROM = 200.0

def wall_y(x):
    """The sea wall's face line: the Battery bulges south at its tip and curves away north on both sides."""
    return -1.75 + 0.0024 * x * x + 0.15 * noise.noise(Vector((x * 0.05, 0.5, 0.5)))
WALL_X0, WALL_X1 = -112.0, 95.0

# ============================================================================= materials
def granite_mat(name="M_Granite", wet_below=None):
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    n = noise_tex(nt, mp.outputs["Vector"], 3.0, 10, 0.62, 0.3, (-1000, 300))
    sp = noise_tex(nt, mp.outputs["Vector"], 60.0, 2, 0.5, loc=(-1000, 100))
    r = ramp(nt, [(0.3, (0.20, 0.195, 0.185, 1)), (0.5, (0.30, 0.29, 0.275, 1)), (0.75, (0.40, 0.39, 0.37, 1))], (-700, 300))
    nt.links.new(mix_f(nt, n.outputs["Fac"], sp.outputs["Fac"], 0.35, (-850, 250)), r.inputs["Fac"])
    col = r.outputs["Color"]
    rnd = attr(nt, "rnd", (-1000, 550))
    tone = ramp(nt, [(0.0, (0.82, 0.82, 0.85, 1)), (1.0, (1.12, 1.08, 1.02, 1))], (-800, 550)); nt.links.new(rnd, tone.inputs["Fac"])
    col = mix_rgb(nt, col, tone.outputs["Color"], 1.0, 'MULTIPLY', (-500, 300))
    if wet_below is not None:
        z = world_z(nt)
        wet = map_range(nt, z, wet_below + 0.9, wet_below + 0.05, 0.0, 1.0, (-800, -600))
        weed = map_range(nt, z, wet_below + 0.4, wet_below - 0.1, 0.0, 1.0, (-800, -750))
        col = mix_rgb(nt, col, (0.06, 0.06, 0.05, 1), math_n(nt, 'MULTIPLY', wet, 0.65, (-650, -600)), 'MIX', (-350, 300))
        col = mix_rgb(nt, col, (0.04, 0.055, 0.025, 1), weed, 'MIX', (-250, 300))
        rough = mix_f(nt, map_range(nt, n.outputs["Fac"], 0.3, 0.7, 0.85, 0.7, (-500, -200)), 0.3, wet, (-300, -200))
    else:
        rough = map_range(nt, n.outputs["Fac"], 0.3, 0.7, 0.85, 0.7, (-500, -200))
    col = ao_mult(nt, col, 0.25, (0.45, 0.45, 0.45))
    nt.links.new(col, b.inputs["Base Color"]); nt.links.new(rough, b.inputs["Roughness"])
    bump_from(nt, b, mix_f(nt, n.outputs["Fac"], sp.outputs["Fac"], 0.3, (-300, -400)), 0.4, 0.01)
    return m

def gravel_mat(name="M_Gravel"):
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 200)); v.inputs["Scale"].default_value = 55.0; nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    n = noise_tex(nt, mp.outputs["Vector"], 0.8, 6, 0.6, loc=(-1000, 0))
    r = ramp(nt, [(0.2, (0.11, 0.10, 0.085, 1)), (0.5, (0.18, 0.165, 0.14, 1)), (0.8, (0.25, 0.23, 0.195, 1))], (-700, 200))
    nt.links.new(mix_f(nt, v.outputs["Color"] if False else v.outputs["Distance"], n.outputs["Fac"], 0.5, (-850, 150)), r.inputs["Fac"])
    col = ao_mult(nt, r.outputs["Color"], 0.4, (0.5, 0.5, 0.5))
    # trodden lighter along the walk, scattered leaves fallen early
    lv = noise_tex(nt, mp.outputs["Vector"], 2.5, 3, 0.5, loc=(-1000, -300))
    col = mix_rgb(nt, col, (0.20, 0.12, 0.04, 1), map_range(nt, lv.outputs["Fac"], 0.66, 0.72, 0.0, 0.6, (-800, -300)), 'MIX', (-300, 300))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.93
    bump_from(nt, b, v.outputs["Distance"], 0.8, 0.012)
    return m

def grass_mat(name="M_Lawn"):
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    n = noise_tex(nt, mp.outputs["Vector"], 0.25, 6, 0.6, 0.5, (-1000, 300))
    f = noise_tex(nt, mp.outputs["Vector"], 40.0, 4, 0.7, loc=(-1000, 0))
    r = ramp(nt, [(0.25, (0.035, 0.06, 0.018, 1)), (0.5, (0.06, 0.095, 0.03, 1)), (0.75, (0.11, 0.13, 0.05, 1))], (-700, 300))
    nt.links.new(mix_f(nt, n.outputs["Fac"], f.outputs["Fac"], 0.45, (-850, 250)), r.inputs["Fac"])
    col = r.outputs["Color"]
    worn = attr(nt, "worn", (-1000, 600))
    col = mix_rgb(nt, col, (0.16, 0.13, 0.09, 1), worn, 'MIX', (-400, 300))
    col = ao_mult(nt, col, 0.5, (0.5, 0.5, 0.5))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.92
    bump_from(nt, b, f.outputs["Fac"], 0.8, 0.01)
    return m

def bark_mat(name="M_ElmBark"):
    """Elm bark: grey-brown, deeply furrowed in long interlacing ridges."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1500, 0)); mp = node(nt, "ShaderNodeMapping", (-1300, 0)); mp.inputs["Scale"].default_value = (6.0, 6.0, 0.9)
    g = node(nt, "ShaderNodeNewGeometry", (-1700, 0)); nt.links.new(g.outputs["Position"], mp.inputs["Vector"])
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 200), feature='DISTANCE_TO_EDGE'); v.inputs["Scale"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    n = noise_tex(nt, mp.outputs["Vector"], 4.0, 6, 0.6, loc=(-1000, 0))
    r = ramp(nt, [(0.0, (0.03, 0.025, 0.02, 1)), (0.08, (0.10, 0.09, 0.075, 1)), (0.3, (0.19, 0.175, 0.15, 1)), (0.6, (0.25, 0.235, 0.21, 1))], (-700, 200))
    nt.links.new(mix_f(nt, v.outputs["Distance"], n.outputs["Fac"], 0.25, (-850, 150)), r.inputs["Fac"])
    col = ao_mult(nt, r.outputs["Color"], 0.2, (0.5, 0.5, 0.5))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
    bump_from(nt, b, v.outputs["Distance"], 1.0, 0.03)
    return m

def leaf_mat(name="M_ElmLeaves"):
    """Elm leaves at the turn of the season: mid green, sun-yellowed at the crown's top, a few gone yellow, darker in."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    v = node(nt, "ShaderNodeTexVoronoi", (-1000, 200)); v.inputs["Scale"].default_value = 14.0; nt.links.new(mp.outputs["Vector"], v.inputs["Vector"])
    n = noise_tex(nt, mp.outputs["Vector"], 0.6, 5, 0.6, loc=(-1000, 0))
    r = ramp(nt, [(0.2, (0.035, 0.06, 0.016, 1)), (0.45, (0.07, 0.11, 0.028, 1)), (0.7, (0.12, 0.16, 0.045, 1)), (0.9, (0.26, 0.23, 0.07, 1))], (-700, 200))
    nt.links.new(mix_f(nt, v.outputs["Color"] if False else v.outputs["Distance"], n.outputs["Fac"], 0.55, (-850, 150)), r.inputs["Fac"])
    col = r.outputs["Color"]
    yl = noise_tex(nt, mp.outputs["Vector"], 1.6, 3, 0.5, loc=(-1000, -300))
    col = mix_rgb(nt, col, (0.30, 0.22, 0.04, 1), map_range(nt, yl.outputs["Fac"], 0.64, 0.7, 0.0, 0.7, (-800, -300)), 'MIX', (-400, 300))
    col = ao_mult(nt, col, 0.8, (0.5, 0.55, 0.45))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.7
    b.inputs["Subsurface Weight"].default_value = 0.1; b.inputs["Subsurface Radius"].default_value = (0.2, 0.4, 0.05)
    bump_from(nt, b, v.outputs["Distance"], 1.0, 0.05)
    return m

def facade_mat(name="M_Facades"):
    """Federal-style brick houses: soft red brick, white stone lintels and sills, dark sash windows (from world x/z)."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True); s_ = sep_xyz(nt, mp.outputs["Vector"], (-1300, 0))
    along = math_n(nt, 'ADD', s_.outputs["X"], s_.outputs["Y"], (-1150, 100))
    wx = math_n(nt, 'FRACT', math_n(nt, 'DIVIDE', along, 2.6, (-1050, 100)), None, (-950, 100))
    wz = math_n(nt, 'FRACT', math_n(nt, 'DIVIDE', math_n(nt, 'SUBTRACT', s_.outputs["Z"], 0.6, (-1150, -50)), 3.1, (-1050, -50)), None, (-950, -50))
    winx = math_n(nt, 'MULTIPLY', map_range(nt, wx, 0.30, 0.32, 0, 1, (-850, 150)), map_range(nt, wx, 0.70, 0.68, 0, 1, (-850, 50)), (-700, 100))
    winz = math_n(nt, 'MULTIPLY', map_range(nt, wz, 0.25, 0.27, 0, 1, (-850, -50)), map_range(nt, wz, 0.80, 0.78, 0, 1, (-850, -150)), (-700, -50))
    win = math_n(nt, 'MULTIPLY', winx, winz, (-550, 50))
    lint = math_n(nt, 'MULTIPLY', winx, math_n(nt, 'MULTIPLY', map_range(nt, wz, 0.80, 0.81, 0, 1, (-850, -250)), map_range(nt, wz, 0.87, 0.86, 0, 1, (-850, -350)), (-700, -300)), (-550, -250))
    n = noise_tex(nt, mp.outputs["Vector"], 2.0, 5, 0.6, loc=(-1000, 400))
    brick = ramp(nt, [(0.3, (0.17, 0.065, 0.04, 1)), (0.7, (0.25, 0.10, 0.06, 1))], (-700, 400)); nt.links.new(n.outputs["Fac"], brick.inputs["Fac"])
    rnd = attr(nt, "rnd", (-1000, 650))
    tone = ramp(nt, [(0.0, (0.7, 0.75, 0.8, 1)), (0.45, (1, 1, 1, 1)), (0.8, (1.3, 1.1, 0.9, 1)), (0.86, (2.4, 2.4, 2.3, 1)), (1.0, (2.0, 1.9, 1.7, 1))], (-800, 650)); nt.links.new(rnd, tone.inputs["Fac"])
    col = mix_rgb(nt, brick.outputs["Color"], tone.outputs["Color"], 1.0, 'MULTIPLY', (-450, 400))
    col = mix_rgb(nt, col, (0.02, 0.025, 0.03, 1), win, 'MIX', (-300, 300))
    col = mix_rgb(nt, col, (0.45, 0.43, 0.40, 1), lint, 'MIX', (-200, 300))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, 0.85, 0.2, win, (-200, -100)), b.inputs["Roughness"])
    return m

def sky_mat(name="M_SkyDome"):
    """A clear, breezy September afternoon: deep blue overhead, paler and hazy along the horizon, scattered fair-weather
    cumulus well above the horizon and a few low ones over the land, the sun's glow ahead to the right."""
    m, nt, b = new_mat(name)
    g = node(nt, "ShaderNodeNewGeometry", (-2000, 0))
    nv = node(nt, "ShaderNodeVectorMath", (-1800, 0), operation='NORMALIZE'); nt.links.new(g.outputs["Position"], nv.inputs[0])
    sep = sep_xyz(nt, nv.outputs[0], (-1600, 0)); el = sep.outputs["Z"]
    base = ramp(nt, [(0.0, (0.62, 0.68, 0.74, 1)), (0.08, (0.66, 0.72, 0.78, 1)), (0.13, (0.52, 0.63, 0.77, 1)), (0.3, (0.32, 0.48, 0.72, 1)),
                     (0.6, (0.20, 0.36, 0.64, 1)), (1.0, (0.14, 0.28, 0.58, 1))], (-1200, 300))
    nt.links.new(map_range(nt, el, -0.1, 1.0, 0.0, 1.0, (-1400, 300)), base.inputs["Fac"])
    col = base.outputs["Color"]
    zk = math_n(nt, 'ADD', math_n(nt, 'MAXIMUM', el, 0.0, (-1400, -100)), 0.05, (-1250, -100))
    px = math_n(nt, 'DIVIDE', sep.outputs["X"], zk, (-1100, -50)); py = math_n(nt, 'DIVIDE', sep.outputs["Y"], zk, (-1100, -200))
    cv = node(nt, "ShaderNodeCombineXYZ", (-950, -100)); nt.links.new(px, cv.inputs["X"]); nt.links.new(py, cv.inputs["Y"])
    mp = node(nt, "ShaderNodeMapping", (-800, -100)); mp.inputs["Scale"].default_value = (0.9, 0.9, 1); mp.inputs["Location"].default_value = (3.1, 7.7, 0)
    nt.links.new(cv.outputs[0], mp.inputs["Vector"])
    cl = noise_tex(nt, mp.outputs["Vector"], 0.55, 10, 0.55, 0.2, (-600, -100))
    dens = map_range(nt, cl.outputs["Fac"], 0.56, 0.66, 0.0, 1.0, (-400, -100))
    shade = noise_tex(nt, mp.outputs["Vector"], 1.4, 6, 0.6, loc=(-600, -350))
    ccol = ramp(nt, [(0.3, (0.58, 0.60, 0.65, 1)), (0.6, (0.86, 0.87, 0.89, 1)), (0.8, (0.96, 0.95, 0.93, 1))], (-400, -350)); nt.links.new(shade.outputs["Fac"], ccol.inputs["Fac"])
    cmask = map_range(nt, el, 0.04, 0.2, 0.0, 1.0, (-400, -550))
    col = mix_rgb(nt, col, ccol.outputs["Color"], math_n(nt, 'MULTIPLY', dens, cmask, (-250, -200)), 'MIX', (-100, 100))
    sd = node(nt, "ShaderNodeVectorMath", (-1400, 600), operation='DOT_PRODUCT'); sd.inputs[1].default_value = tuple(SUN_DIR)
    nt.links.new(nv.outputs[0], sd.inputs[0])
    glow = map_range(nt, sd.outputs["Value"], 0.8, 1.0, 0.0, 0.6, (-1200, 600))
    col = mix_rgb(nt, col, (1.0, 0.96, 0.86, 1), glow, 'MIX', (150, 100))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Strength"].default_value = 1.0; b.inputs["Roughness"].default_value = 1.0
    return m

def water_mat(name="M_BayWater"):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (0.016, 0.034, 0.036, 1); b.inputs["Roughness"].default_value = 0.06; b.inputs["IOR"].default_value = 1.33
    mp = coords(nt, world=True)
    sm = node(nt, "ShaderNodeMapping", (-1200, -300)); sm.inputs["Scale"].default_value = (0.5, 1.4, 1.0); sm.inputs["Rotation"].default_value = (0, 0, 0.25)
    nt.links.new(mp.outputs["Vector"], sm.inputs["Vector"])
    w1 = node(nt, "ShaderNodeTexWave", (-1000, -300), wave_type='BANDS', bands_direction='Y'); w1.inputs["Scale"].default_value = 0.35
    w1.inputs["Distortion"].default_value = 3.0; w1.inputs["Detail"].default_value = 3
    nt.links.new(sm.outputs["Vector"], w1.inputs["Vector"])
    r1 = noise_tex(nt, mp.outputs["Vector"], 1.1, 6, 0.6, loc=(-1000, -500))
    r3 = noise_tex(nt, sm.outputs["Vector"], 0.45, 4, 0.55, 0.8, (-1000, -700))
    bump_from(nt, b, mix_f(nt, r3.outputs["Fac"], r1.outputs["Fac"], 0.45, (-600, -400)), 0.35, 0.12)
    ca = node(nt, "ShaderNodeVertexColor", (-1000, 500)); ca.layer_name = "Col"
    sp = node(nt, "ShaderNodeSeparateColor", (-800, 500)); nt.links.new(ca.outputs["Color"], sp.inputs["Color"])
    fn_ = noise_tex(nt, mp.outputs["Vector"], 2.0, 4, 0.6, loc=(-1000, 700))
    foam = math_n(nt, 'MULTIPLY', sp.outputs["Green"], map_range(nt, fn_.outputs["Fac"], 0.4, 0.62, 0.0, 0.9, (-800, 700)), (-600, 600))
    # whitecaps here and there on the breezy bay
    wc = noise_tex(nt, sm.outputs["Vector"], 3.0, 3, 0.5, loc=(-1000, 900))
    foam = math_n(nt, 'MAXIMUM', foam, map_range(nt, wc.outputs["Fac"], 0.74, 0.8, 0.0, 0.5, (-800, 900)), (-500, 700))
    col = mix_rgb(nt, (0.016, 0.034, 0.036, 1), (0.55, 0.57, 0.56, 1), foam, 'MIX', (-300, 300))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(mix_f(nt, 0.06, 0.7, foam, (-300, 0)), b.inputs["Roughness"])
    return m

def flag_mat(name="M_Flag"):
    """The flag of the 1850s: thirteen stripes, a blue canton with rows of stars (from UV: u along the fly)."""
    m, nt, b = new_mat(name)
    uv = node(nt, "ShaderNodeUVMap", (-1400, 0)); s_ = sep_xyz(nt, uv.outputs["UV"], (-1200, 0))
    st = math_n(nt, 'FRACT', math_n(nt, 'MULTIPLY', s_.outputs["Y"], 6.5, (-1050, 100)), None, (-950, 100))
    red = math_n(nt, 'LESS_THAN', st, 0.5, (-850, 100))
    canton = math_n(nt, 'MULTIPLY', math_n(nt, 'LESS_THAN', s_.outputs["X"], 0.4, (-1050, -100)), math_n(nt, 'GREATER_THAN', s_.outputs["Y"], 0.462, (-1050, -200)), (-900, -150))
    stars = node(nt, "ShaderNodeTexVoronoi", (-1050, -400)); stars.inputs["Scale"].default_value = 9.0; stars.inputs["Randomness"].default_value = 0.0
    sm = node(nt, "ShaderNodeMapping", (-1250, -400)); sm.inputs["Scale"].default_value = (2.0, 1.15, 1.0); nt.links.new(uv.outputs["UV"], sm.inputs["Vector"])
    nt.links.new(sm.outputs["Vector"], stars.inputs["Vector"])
    star = map_range(nt, stars.outputs["Distance"], 0.16, 0.12, 0.0, 1.0, (-850, -400))
    col = mix_rgb(nt, (0.55, 0.53, 0.48, 1), (0.36, 0.035, 0.03, 1), red, 'MIX', (-600, 100))
    col = mix_rgb(nt, col, (0.04, 0.05, 0.16, 1), canton, 'MIX', (-450, 100))
    col = mix_rgb(nt, col, (0.55, 0.53, 0.48, 1), math_n(nt, 'MULTIPLY', canton, star, (-600, -300)), 'MIX', (-300, 100))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85; b.inputs["Sheen Weight"].default_value = 0.4
    return m

M_GRANITE = granite_mat(wet_below=WL)
M_COPING = granite_mat("M_Coping")
M_GRAVEL = gravel_mat()
M_LAWN = grass_mat()
M_IRON = iron_mat("M_CastIron", rust=0.1, base=(0.02, 0.022, 0.024), rough=(0.45, 0.7))
M_BENCH = timber_mat("M_BenchWood", base=(0.17, 0.12, 0.08), dark=(0.05, 0.035, 0.024), light=(0.30, 0.23, 0.15), along='X', rough=(0.45, 0.75), grime=0.35)
M_BARK = bark_mat()
M_LEAVES = leaf_mat()
M_FACADE = facade_mat()
M_ROOF = noisy("M_Roofs", [(0.06, 0.06, 0.065), (0.10, 0.10, 0.11), (0.14, 0.14, 0.15)], scale=2.0, rough=0.7, bump=0.3, bump_dist=0.02, world=True)
M_SANDSTONE = noisy("M_Sandstone", [(0.20, 0.10, 0.07), (0.27, 0.14, 0.10), (0.34, 0.20, 0.15)], scale=1.5, rough=0.85, bump=0.4, bump_dist=0.03, world=True, ao=(0.5, (0.5, 0.5, 0.5)))
M_TIMBER = timber_mat("M_PierTimber", base=(0.16, 0.145, 0.125), dark=(0.05, 0.045, 0.04), light=(0.28, 0.26, 0.23), along='Z', rough=(0.6, 0.9), grime=0.5, salt=0.2)
M_HULLS = noisy("M_ShipHulls", [(0.025, 0.022, 0.02), (0.045, 0.04, 0.035), (0.08, 0.07, 0.06)], scale=1.2, rough=0.6, bump=0.2, bump_dist=0.02, world=True)
M_SPARS = noisy("M_ShipSpars", [(0.10, 0.075, 0.05), (0.16, 0.12, 0.08), (0.22, 0.17, 0.12)], scale=3.0, rough=0.7, bump=0.0, world=True)
M_SAILS = noisy("M_ShipSails", [(0.42, 0.40, 0.35), (0.52, 0.50, 0.44), (0.60, 0.58, 0.52)], scale=2.0, rough=0.9, bump=0.0, world=True)
M_FLAG = flag_mat()
M_WATER = water_mat()
M_FARSEA = noisy("M_FarSea", [(0.10, 0.14, 0.17), (0.13, 0.17, 0.20), (0.17, 0.21, 0.24)], scale=0.02, rough=0.3, bump=0.0, world=True)
M_FARLAND = noisy("M_FarLand", [(0.17, 0.21, 0.20), (0.22, 0.26, 0.25), (0.30, 0.33, 0.32)], scale=0.03, rough=1.0, bump=0.0, world=True)
M_FARTOWN = noisy("M_FarTown", [(0.20, 0.17, 0.15), (0.28, 0.25, 0.22), (0.38, 0.35, 0.31)], scale=0.2, rough=1.0, bump=0.0, world=True)
M_FARSHIPS = noisy("M_FarShips", [(0.05, 0.045, 0.04), (0.09, 0.08, 0.07), (0.14, 0.13, 0.11)], scale=0.4, rough=0.9, bump=0.0, world=True)
M_SKY = sky_mat()

# ============================================================================= the mole: sea wall, coping, railing, promenade
def sea_wall():
    xs = [lerp(WALL_X0, WALL_X1, i / 120) for i in range(121)]
    # the wall face: granite ashlar from below the water up to the coping, with a slight batter
    verts = []; faces = []
    for x in xs:
        y = wall_y(x)
        for z in (WL - 2.5, WL - 0.6, WL + 0.4, 0.0):
            verts.append((x, y - (0.0 - z) * 0.04, z))
    for i in range(len(xs) - 1):
        for j in range(3):
            a = i * 4 + j; faces.append((a, a + 4, a + 5, a + 1))
    o = orient(mesh_from("SeaWall", verts, faces, M_GRANITE), lambda c: (0, -1, 0))
    # coping stones: individual blocks along the top, a little proud, joints between them
    x = -36.0; k = 0
    xs3 = [lerp(WALL_X0, -36.0, i / 30) for i in range(31)]
    tube("CopingWest", [Vector((xx, wall_y(xx) + 0.26, 0.10)) for xx in xs3], (0, 0), M_COPING, rect=(0.62, 0.32), n=1)
    xs3 = [lerp(36.0, WALL_X1, i / 24) for i in range(25)]
    tube("CopingEast", [Vector((xx, wall_y(xx) + 0.26, 0.10)) for xx in xs3], (0, 0), M_COPING, rect=(0.62, 0.32), n=1)
    while x < 36.0:
        L = random.uniform(1.0, 1.6); L = min(L, 36.0 - x + 0.01); xm = x + L / 2; y = wall_y(xm)
        ang = math.atan2(wall_y(x + L) - wall_y(x), L)
        box(f"Coping{k}", (L - 0.012, 0.62, 0.32), (xm, y + 0.26, 0.10 + random.uniform(-0.006, 0.006)), M_COPING, bevel=0.02, rot=(random.uniform(-0.004, 0.004), random.uniform(-0.005, 0.005), ang))
        x += L; k += 1
    # the iron railing on the coping: posts with ball tops, two rails, a bottom rail
    posts = []
    x = WALL_X0 + 0.5
    while x < WALL_X1 - 0.5:
        y = wall_y(x) + 0.32; posts.append(Vector((x, y, 0.26)))
        cyl(f"RailPost{x:.1f}", 0.032, 1.0, (x, y, 0.26 + 0.5), M_IRON, verts=6 if abs(x) < 30 else 4, smooth=False)
        if abs(x) < 30: lathe(f"RailKnob{x:.1f}", [(0.0, 0.0), (0.045, 0.01), (0.05, 0.05), (0.03, 0.09), (0.0, 0.1)], (x, y, 1.26), M_IRON, steps=8)
        x += 2.4
    for z, r in ((1.18, 0.022), (0.72, 0.016), (0.36, 0.016)):
        tube(f"Rail{z}", [p + Vector((0, 0, z - 0.26)) for p in posts], (r, r), M_IRON, sides=4, n=1, caps=False)
    # the promenade: gravel with a granite curb at the lawn's edge; the lawn behind with worn paths
    verts = []; faces = []
    NX, NY = 64, 8
    for j in range(NY + 1):
        for i in range(NX + 1):
            x = lerp(WALL_X0, WALL_X1, i / NX); y = wall_y(x) + 0.55 + 7.0 * j / NY
            verts.append((x, y, 0.0 + 0.015 * noise.noise(Vector((x * 0.5, y * 0.5, 1.0)))))
    for j in range(NY):
        for i in range(NX):
            a = j * (NX + 1) + i; faces.append((a, a + 1, a + NX + 2, a + NX + 1))
    orient(mesh_from("Promenade", verts, faces, M_GRAVEL), lambda c: (0, 0, 1))
    xs2 = [lerp(WALL_X0, WALL_X1, i / 60) for i in range(61)]
    tube("Curb", [Vector((x, wall_y(x) + 7.6, 0.04)) for x in xs2], (0, 0), M_COPING, rect=(0.25, 0.14), n=1)
    # the lawn
    verts = []; faces = []; worn = []
    NX, NY = 40, 18
    for j in range(NY + 1):
        for i in range(NX + 1):
            x = lerp(WALL_X0 + 10, WALL_X1 - 10, i / NX); y0 = wall_y(x) + 7.7
            y = y0 + 70.0 * (j / NY) ** 1.3
            z = 0.06 + 0.25 * smoothstep(0, 30, y - y0) + 0.08 * noise.noise(Vector((x * 0.06, y * 0.06, 2.0)))
            verts.append((x, y, z))
            # a gravel walk winding back through the trees (worn into the grass)
            px = 6.0 * math.sin(y * 0.05) - 2.0
            worn.append(max(smoothstep(1.6, 0.9, abs(x - px)), smoothstep(1.3, 0.6, abs(y - y0 - 0.0))))
    for j in range(NY):
        for i in range(NX):
            a = j * (NX + 1) + i; faces.append((a, a + 1, a + NX + 2, a + NX + 1))
    o = orient(mesh_from("Lawn", verts, faces, M_LAWN), lambda c: (0, 0, 1))
    set_attr(o, "worn", worn)
sea_wall()
anchor("scene.centre", (0.0, wall_y(0.0) + 0.32, 0.26))

# --- benches and gas lamps on the promenade
def bench(name, x, facing_deg=0.0):
    y = wall_y(x) + 2.6; R = Matrix.Rotation(math.radians(facing_deg), 3, 'Z')
    def P(dx, dy, z): q = R @ Vector((dx, dy, 0)); return (x + q.x, y + q.y, z)
    for k in range(4):
        box(f"{name}Slat{k}", (2.0, 0.09, 0.035), P(0, -0.2 + k * 0.11, 0.44), M_BENCH, bevel=0.006, rot=(0, 0, math.radians(facing_deg)))
    for k in range(3):
        box(f"{name}Back{k}", (2.0, 0.035, 0.09), P(0, 0.2 + 0.03 * k, 0.6 + k * 0.13), M_BENCH, bevel=0.006, rot=(math.radians(-12), 0, math.radians(facing_deg)))
    for dx in (-0.85, 0.85):
        tube(f"{name}End{dx}", [Vector(P(dx, -0.25, 0.0)), Vector(P(dx, -0.2, 0.42)), Vector(P(dx, 0.22, 0.44)), Vector(P(dx, 0.3, 0.9))], (0.025, 0.02), M_IRON, sides=6, n=3)
        tube(f"{name}Leg{dx}", [Vector(P(dx, 0.22, 0.44)), Vector(P(dx, 0.25, 0.0))], (0.025, 0.025), M_IRON, sides=6, n=1)
bench("BenchA", -4.2); bench("BenchB", 7.5, 4.0); bench("BenchC", -16.0, -6.0)
def gas_lamp(name, x):
    y = wall_y(x) + 1.3
    lathe(name + "Post", [(0.0, 0.0), (0.16, 0.0), (0.16, 0.12), (0.09, 0.25), (0.06, 0.6), (0.045, 2.4), (0.06, 2.5), (0.0, 2.52)], (x, y, 0.0), M_IRON, steps=10)
    box(name + "Arm", (0.5, 0.03, 0.03), (x, y, 2.3), M_IRON)
    lathe(name + "Lantern", [(0.0, 0.0), (0.07, 0.0), (0.16, 0.36), (0.13, 0.38), (0.19, 0.42), (0.04, 0.52), (0.0, 0.6)], (x, y, 2.5), M_IRON, steps=4)
gas_lamp("LampA", -9.0); gas_lamp("LampB", 10.5)

# ============================================================================= elms (veg.crown.elms swaying, trunks static)
CROWNS = []
def elm(name, x, y, H, seed):
    rng = random.Random(seed)
    z0 = 0.06 + 0.25 * smoothstep(0, 30, y - (wall_y(x) + 7.7))
    base = Vector((x, y, z0 - 0.15))
    split = H * rng.uniform(0.28, 0.36)
    trunk_top = base + Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), split))
    r0 = 0.018 * H + 0.12
    tube(f"{name}Trunk", [base, base + Vector((0, 0, 0.6)), base.lerp(trunk_top, 0.6), trunk_top], [r0 * 1.5, r0 * 1.2, r0 * 1.05, r0, r0 * 0.95, r0 * 0.9, r0 * 0.85, r0 * 0.82, r0 * 0.8, r0 * 0.78], M_BARK, sides=10, n=3)
    # the root flare
    for k in range(5):
        a = 2 * math.pi * k / 5 + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        tube(f"{name}Root{k}", [base + Vector((0, 0, 0.5)), base + d * r0 * 1.3 + Vector((0, 0, 0.1)), base + d * r0 * 2.4 + Vector((0, 0, -0.05))], (r0 * 0.45, r0 * 0.12), M_BARK, sides=5, n=2)
    tips = []
    nl = rng.randint(3, 4)
    for k in range(nl):
        a = 2 * math.pi * k / nl + rng.uniform(-0.4, 0.4)
        lean = rng.uniform(0.35, 0.6)
        d = Vector((math.cos(a) * lean, math.sin(a) * lean, 1.0)).normalized()
        L = H * rng.uniform(0.38, 0.48)
        mid = trunk_top + d * L * 0.5 + Vector((0, 0, L * 0.05))
        end = trunk_top + d * L + Vector((math.cos(a), math.sin(a), 0)) * L * 0.18
        tube(f"{name}Limb{k}", [trunk_top, mid, end], (r0 * 0.62, r0 * 0.22), M_BARK, sides=6, n=3)
        for j in range(2):
            b0 = trunk_top.lerp(end, rng.uniform(0.55, 0.9))
            aa = a + rng.uniform(-1.0, 1.0)
            bd = Vector((math.cos(aa) * 0.9, math.sin(aa) * 0.9, rng.uniform(0.2, 0.7))).normalized()
            bl = H * rng.uniform(0.15, 0.25)
            be = b0 + bd * bl
            tube(f"{name}Branch{k}{j}", [b0, b0 + bd * bl * 0.5 + Vector((0, 0, 0.3)), be], (r0 * 0.2, r0 * 0.06), M_BARK, sides=5, n=2)
            tips.append(be)
        tips.append(end)
    # the crown: leaf clumps at the branch tips and between, each a lumpy shell fringed with leaf sprays
    centre = Vector((x, y, z0 + H * 0.7)); Rc = H * 0.38
    cr = []
    for i, t in enumerate(tips):
        rr = rng.uniform(0.11, 0.15) * H
        if i % 3 == 0 or i == len(tips) - 1:
            cr.append(blob(f"{name}Clump{i}", tuple(t + Vector((0, 0, rr * 0.2))), rr * 1.35, M_LEAVES, scale=(1.2, 1.2, 0.8), subdiv=2, amp=0.3, freq=3.2, seed=seed + i * 1.7))
    for i in range(3):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0.2, 0.75) * Rc
        p = centre + Vector((math.cos(a) * r, math.sin(a) * r, rng.uniform(-0.15, 0.25) * H))
        cr.append(blob(f"{name}Inner{i}", tuple(p), rng.uniform(0.14, 0.19) * H, M_LEAVES, scale=(1.2, 1.2, 0.75), subdiv=2, amp=0.3, freq=3.0, seed=seed + 40 + i))
    # sprays: small leaf-cards poking out of each clump to break the silhouette
    verts = []; faces = []
    bpy.context.view_layer.update()
    for c_ in cr:
        mwc = c_.matrix_world; me = c_.data
        vs = rng.sample(list(me.vertices), min(len(me.vertices), 40))
        for v in vs:
            p = mwc @ v.co; nrm = (mwc.to_3x3() @ v.normal).normalized()
            s = rng.uniform(0.3, 0.5)
            tng = nrm.cross(Vector((0, 0, 1))); tng = tng.normalized() if tng.length > 1e-3 else Vector((1, 0, 0))
            bt = nrm.cross(tng)
            # a spray of leaves lying across the clump's surface, tilted out a little, so the silhouette breaks up
            tw = rng.uniform(0, math.pi); tng, bt = tng * math.cos(tw) + bt * math.sin(tw), bt * math.cos(tw) - tng * math.sin(tw)
            up_ = (bt * 0.75 + nrm * 0.45).normalized()
            q0 = p + nrm * 0.02
            k0 = len(verts)
            verts += [tuple(q0 - tng * s * 0.5 - up_ * s * 0.2), tuple(q0 + tng * s * 0.5 - up_ * s * 0.2), tuple(q0 + tng * s * 0.35 + up_ * s * 0.6), tuple(q0 - tng * s * 0.35 + up_ * s * 0.6)]
            faces.append((k0, k0 + 1, k0 + 2, k0 + 3))
    sp = mesh_from(f"{name}Sprays", verts, faces, M_LEAVES)
    cr.append(sp)
    for c_ in cr:
        c_["merge"] = "veg.crown.elms"
        CROWNS.append((c_, Vector((x, y, z0)), split, H, Rc))
for k, (x, y, H) in enumerate(((-6.5, 9.0, 17.0), (7.0, 11.0, 19.0), (-15.0, 12.5, 15.0), (16.0, 10.0, 16.0), (0.5, 22.0, 20.0), (-25.0, 17.0, 17.0))):
    elm(f"Elm{k}", x, y, H, 100 + k * 13)

# ============================================================================= Castle Garden on its pier, the footbridge, its flag
CG = Vector((-122.0, -6.0, 0.0))
def castle_garden():
    R = 28.0; Hw = 9.0
    verts = []; faces = []; seg = 48
    for i in range(seg):
        a = 2 * math.pi * i / seg
        for z in (WL - 1.0, WL + Hw):
            verts.append((CG.x + R * math.cos(a), CG.y + R * math.sin(a), z))
    for i in range(seg):
        j = (i + 1) % seg; faces.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    orient(mesh_from("CastleWall", verts, faces, M_SANDSTONE), lambda c: (c.x - CG.x, c.y - CG.y, 0))
    # the gun embrasures (now windows) round the wall, in two tiers
    for i in range(0, seg, 2):
        a = 2 * math.pi * (i + 0.5) / seg
        for z in (WL + 3.2, WL + 6.6):
            p = Vector((CG.x + (R + 0.05) * math.cos(a), CG.y + (R + 0.05) * math.sin(a), z))
            box(f"Embrasure{i}_{z:.0f}", (1.1, 0.2, 1.3), tuple(p), M_FARSHIPS, rot=(0, 0, a + math.pi / 2))
    # the great low roof put on when the fort became a hall, with its cupola
    roof = []; rf = []; N = 6
    for j in range(N + 1):
        t = j / N; rr = (R + 0.6) * (1 - t) + 4.0 * t; zz = WL + Hw + 0.3 + 7.0 * math.sin(t * math.pi / 2) ** 1.2
        for i in range(seg):
            a = 2 * math.pi * i / seg; roof.append((CG.x + rr * math.cos(a), CG.y + rr * math.sin(a), zz))
    for j in range(N):
        for i in range(seg):
            k = (i + 1) % seg; rf.append((j * seg + i, j * seg + k, (j + 1) * seg + k, (j + 1) * seg + i))
    orient(mesh_from("CastleRoof", roof, rf, M_ROOF), lambda c: (c.x - CG.x, c.y - CG.y, 3.0))
    cyl("CastleCupola", 3.5, 3.0, (CG.x, CG.y, WL + Hw + 7.3 + 1.5), M_FACADE, verts=12)
    cyl("CastleCupolaRoof", 4.0, 2.2, (CG.x, CG.y, WL + Hw + 7.3 + 4.1), M_ROOF, verts=12, r2=0.3)
    # the flagstaff and the flag, streaming in the sea breeze
    top = Vector((CG.x, CG.y, WL + Hw + 7.3 + 4.1 + 13.0))
    cyl("CastleFlagstaff", 0.18, 14.0, (CG.x, CG.y, top.z - 7.0), M_SPARS, verts=8, r2=0.08)
    wind_to = bearing_dir(WIND_FROM + 180.0, 0.0)
    flag(f"cloth.flag.castle", top - Vector((0, 0, 0.3)), wind_to, 7.0, 3.8)
    # the pier the fort stands on (its old mole) and the footbridge to the Battery on piles
    a0 = Vector((CG.x + 24.0, CG.y + 14.0, 0)); a1 = Vector((-83.0, wall_y(-83.0) + 0.6, 0))
    d = (a1 - a0); L = d.length; dn = d.normalized(); sd = Vector((-dn.y, dn.x, 0))
    yaw = math.atan2(dn.y, dn.x)
    box("FootbridgeDeck", (L, 4.0, 0.25), tuple((a0 + a1) / 2 + Vector((0, 0, -0.35))), M_TIMBER, rot=(0, 0, yaw))
    for k in range(int(L / 4.0) + 1):
        p = a0 + dn * (k * 4.0)
        for s in (-1, 1):
            q = p + sd * s * 1.8
            cyl(f"BridgePile{k}{s}", 0.17, 2.6, (q.x, q.y, WL + 0.5), M_TIMBER, verts=7)
            cyl(f"BridgePost{k}{s}", 0.07, 1.1, (q.x, q.y, 0.2), M_TIMBER, verts=5)
    for s in (-1, 1):
        tube(f"BridgeRail{s}", [a0 + sd * s * 1.8 + Vector((0, 0, 0.75)), a1 + sd * s * 1.8 + Vector((0, 0, 0.75))], (0.05, 0.05), M_TIMBER, rect=(0.08, 0.1), n=1)
    return top

def flag(name, hoist_top, to_dir, L, Hh, nu=14, nv=6):
    """A flag as a waving sheet: u along the fly (to_dir), v down the hoist; a frozen ripple, R weight = u."""
    to_dir = Vector((to_dir.x, to_dir.y, 0)).normalized(); side = Vector((-to_dir.y, to_dir.x, 0))
    verts = []; faces = []; uvs = []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u = i / nu; v = j / nv
            p = hoist_top + to_dir * (u * L) - Vector((0, 0, v * Hh + u * u * 0.4)) + side * (0.35 * u * math.sin(u * 7.0 + v * 1.5))
            verts.append(tuple(p)); uvs.append((u, 1 - v))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i; faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); me.materials.append(M_FLAG); link(o)
    uvl = me.uv_layers.new(name="UVMap")
    for li, loop in enumerate(me.loops): uvl.data[li].uv = uvs[loop.vertex_index]
    for p_ in me.polygons: p_.use_smooth = True
    o["merge"] = name if name.startswith("cloth.") else "cloth.flag.ships"
    FLAGS.append((o, hoist_top, to_dir, L))
    return o
FLAGS = []
CG_TOP = castle_garden()
anchor("battery.castleGarden", tuple(CG))

# ============================================================================= ships at anchor and the East River piers
def ship(name, p, heading_deg, L=34.0, rig="ship", sails_set=False, merge="Ships"):
    """A merchant ship at anchor (sails furled), simplified for 100-400 m: hull, bulwark, masts, yards, a pennant."""
    h = math.radians(heading_deg); fwd = Vector((math.sin(h), math.cos(h), 0)); side = Vector((fwd.y, -fwd.x, 0))
    B = L * 0.24; parts = []
    verts = []; faces = []; N = 10
    for i in range(N + 1):
        t = i / N; w = B / 2 * (math.sin(math.pi * min(1.0, t * 1.15)) ** 0.5 if t < 0.87 else (1 - t) / 0.13 * 0.5 + 0.35)
        w = B / 2 * max(0.05, math.sin(math.pi * t) ** 0.45)
        c = p + fwd * (L * (t - 0.5))
        sh = 0.6 * (2 * t - 1) ** 2
        for (sx, z) in ((-1, WL - 2.0), (-1, WL + 3.0 + sh), (1, WL + 3.0 + sh), (1, WL - 2.0)):
            verts.append(tuple(c + side * (sx * w) + Vector((0, 0, z))))
    for i in range(N):
        for k in range(3):
            a = i * 4 + k; faces.append((a, a + 1, a + 5, a + 4))
    parts.append(orient(mesh_from(name + "Hull", verts, faces, M_HULLS), lambda c, p=p: (c.x - p.x, c.y - p.y, 0.3)))
    masts = [(-0.3, 1.0), (0.05, 1.08), (0.33, 0.85)] if rig == "ship" else ([(-0.15, 1.0), (0.2, 0.95)] if rig == "brig" else [(-0.15, 1.0), (0.18, 1.0)])
    for k, (f, hh) in enumerate(masts):
        q = p + fwd * (f * L)
        mh = L * 0.95 * hh
        parts.append(cyl(f"{name}Mast{k}", 0.3, mh, (q.x, q.y, WL + 3 + mh / 2), M_SPARS, verts=6, r2=0.08))
        if rig in ("ship", "brig"):
            for j, (zf, lf) in enumerate(((0.38, 0.55), (0.62, 0.42), (0.82, 0.3))):
                yl = L * lf * hh
                c = Vector((q.x, q.y, WL + 3 + mh * zf))
                parts.append(tube(f"{name}Yard{k}{j}", [c - side * yl / 2, c + side * yl / 2], (0.12, 0.12), M_SPARS, sides=5, n=1))
                parts.append(tube(f"{name}Furl{k}{j}", [c - side * yl * 0.45 + Vector((0, 0, 0.2)), c + Vector((0, 0, 0.3)), c + side * yl * 0.45 + Vector((0, 0, 0.2))], (0.25, 0.25), M_SAILS, sides=5, n=2))
        else:
            parts.append(tube(f"{name}Boom{k}", [Vector((q.x, q.y, WL + 4.0)), Vector((q.x, q.y, WL + 4.0)) - fwd * L * 0.4], (0.12, 0.1), M_SPARS, sides=5, n=1))
            parts.append(tube(f"{name}BoomSail{k}", [Vector((q.x, q.y, WL + 4.3)), Vector((q.x, q.y, WL + 4.3)) - fwd * L * 0.38], (0.3, 0.25), M_SAILS, sides=5, n=1))
        # shrouds as thin lines to the sides
        for s in (-1, 1):
            for j in range(3):
                a_ = q + side * s * (B / 2) - fwd * (0.8 * (j - 1)) + Vector((0, 0, WL + 3.2))
                parts.append(tube(f"{name}Shroud{k}{s}{j}", [a_, Vector((q.x, q.y, WL + 3 + mh * 0.62))], (0.03, 0.03), M_FARSHIPS, sides=3, n=1, caps=False))
    bs0 = p + fwd * (L * 0.5) + Vector((0, 0, WL + 3.5))
    parts.append(tube(f"{name}Bowsprit", [bs0, bs0 + fwd * L * 0.3 + Vector((0, 0, L * 0.08))], (0.25, 0.1), M_SPARS, sides=5, n=1))
    # stays from the foremast to the bowsprit
    fq = p + fwd * (masts[-1][0] * L)
    parts.append(tube(f"{name}Stay", [Vector((fq.x, fq.y, WL + 3 + L * 0.95 * masts[-1][1] * 0.62)), bs0 + fwd * L * 0.3 + Vector((0, 0, L * 0.08))], (0.04, 0.04), M_FARSHIPS, sides=3, n=1, caps=False))
    for o in parts: o["merge"] = merge
    # a long pennant streaming from the main truck
    mq = p + fwd * (masts[min(1, len(masts) - 1)][0] * L)
    flag(f"{name}Pennant", Vector((mq.x, mq.y, WL + 3 + L * 0.95 * masts[min(1, len(masts) - 1)][1])), bearing_dir(WIND_FROM + 180.0, 0.0), L * 0.18, 0.45, nu=10, nv=1)
    return parts

ship("ShipA", geo(150.0, 230.0), 20.0, 38.0, "ship")
ship("BrigB", geo(214.0, 330.0), 200.0, 30.0, "brig")
ship("SchoonerC", geo(128.0, 140.0), 205.0, 24.0, "schooner")
ship("ShipD", geo(236.0, 210.0), 15.0, 36.0, "ship")
# the East River piers: wooden piers on piles running out to the south-east with ships from China alongside
def east_piers():
    for k in range(4):
        root = geo(95.0 - k * 9.0, 95.0 + k * 34.0); root.z = 0
        ang = math.radians(150.0 - FACING)          # piers run out SSE
        d = Vector((-math.sin(ang), -math.cos(ang), 0)); sd = Vector((-d.y, d.x, 0))
        L = 55.0
        o = box(f"Pier{k}", (11.0, L, 0.6), tuple(root + d * (L / 2) + Vector((0, 0, -0.5))), M_TIMBER, rot=(0, 0, math.atan2(d.y, d.x) - math.pi / 2))
        o["merge"] = "Piers"
        for j in range(8):
            for s in (-1, 1):
                q = root + d * (j * 7.5) + sd * s * 5.3
                c = cyl(f"PierPile{k}{j}{s}", 0.25, 3.5, (q.x, q.y, WL + 0.8), M_TIMBER, verts=5); c["merge"] = "Piers"
        for s in ((-1,) if k % 2 == 0 else (1,)):
            sp = root + d * 30.0 + sd * s * (5.5 + 4.6)
            ship(f"PierShip{k}{s}", sp, (math.degrees(math.atan2(d.x, d.y))) % 360, 36.0, "ship")
        # a warehouse at the pier's root
        w = box(f"PierShed{k}", (14.0, 10.0, 9.0), tuple(root - d * 12.0 + Vector((0, 0, 4.5))), M_FACADE, rot=(0, 0, math.atan2(d.y, d.x)))
        w["merge"] = "Town"
east_piers()

# ============================================================================= State Street houses, warehouses (behind)
def houses():
    rng = random.Random(21)
    x = -70.0
    while x < 48.0:
        w = rng.uniform(7.5, 10.0); h = rng.uniform(11.0, 15.5); d = 14.0
        y = 62.0 + 0.0025 * x * x * 0.5
        o = box(f"House{x:.0f}", (w - 0.15, d, h), (x + w / 2, y + d / 2, 0.4 + h / 2), M_FACADE)
        o["merge"] = "Town"
        verts = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, 0, d * 0.32), (-w / 2, 0, d * 0.32), (-w / 2, d / 2, 0), (w / 2, d / 2, 0)]
        r = orient(mesh_from(f"HouseRoof{x:.0f}", verts, [(0, 1, 2, 3), (3, 2, 5, 4), (0, 3, 4), (1, 5, 2)], M_ROOF, smooth=False), lambda c: (c.x * 0.2, c.y, 1.0))
        r.location = (x + w / 2, y + d / 2, 0.4 + h); r["merge"] = "Town"
        for s in (-1, 1):
            c = box(f"Chimney{x:.0f}{s}", (0.9, 0.6, 2.0), (x + w / 2 + s * (w / 2 - 0.5), y + d / 2, 0.4 + h + d * 0.32 * 0.6), M_FACADE); c["merge"] = "Town"
        # dormers
        for k in range(2):
            dm = box(f"Dormer{x:.0f}{k}", (1.3, 1.6, 1.5), (x + w * (0.3 + 0.4 * k), y + d * 0.2, 0.4 + h + 1.0), M_ROOF); dm["merge"] = "Town"
        x += w
    # the church tower of Trinity far up Broadway, and warehouses along Whitehall to the left
    t = geo(5.0, 520.0)
    o = box("Trinity", (10, 10, 40), (t.x, t.y, 20), M_FARTOWN); o["merge"] = "far.Town"
    o = cyl("TrinitySpire", 5.5, 30, (t.x, t.y, 55), M_FARTOWN, verts=8, r2=0.2); o["merge"] = "far.Town"
    for k in range(5):
        p = Vector((40.0 + k * 13.0, 30.0 + k * 9.0, 0))
        o = box(f"Warehouse{k}", (12.0, 18.0, rng.uniform(10, 14)), (p.x, p.y, 6.0), M_FACADE, rot=(0, 0, -0.5)); o["merge"] = "Town"
houses()

# ============================================================================= distant shores (scaled into the backdrop)
def far_land(name, b0, b1, dist, hfn, mat, N=50, merge=None):
    verts = []; faces = []
    for i in range(N + 1):
        t = i / N; bb = lerp(b0, b1, t); d = geo(bb, 1.0); d.z = 0
        p0 = d * dist; h = hfn(t)
        verts += [(p0.x, p0.y, WL - 1.0), (p0.x + d.x * 6, p0.y + d.y * 6, WL + h)]
    for i in range(N):
        a = 2 * i; faces.append((a, a + 2, a + 3, a + 1))
    o = orient(mesh_from(name, verts, faces, mat), lambda c: (-c.x, -c.y, 0.0))
    o["merge"] = merge or "far.Land"
    return o
# Staten Island: long low blue hills ahead, far off; the Narrows' gap; Long Island's shore beyond to the left
far_land("StatenIsland", 192.0, 238.0, 585.0, lambda t: 3.0 + 4.0 * math.sin(t * math.pi) ** 0.6 + 1.0 * noise.noise(Vector((t * 7, 1, 1))), M_FARLAND)
far_land("LongIsland", 150.0, 186.0, 585.0, lambda t: 1.5 + 1.5 * t + 0.6 * noise.noise(Vector((t * 9, 2, 1))), M_FARLAND)
# Governors Island with Castle Williams on its point (left, ahead)
far_land("GovernorsIsland", 128.0, 165.0, 470.0, lambda t: 4.0 + 3.0 * math.sin(t * math.pi) + 1.5 * abs(noise.noise(Vector((t * 12, 3, 1)))), M_FARLAND)
cw = geo(160.0, 455.0)
o = cyl("CastleWilliams", 13.0, 7.0, (cw.x, cw.y, WL + 3.5), M_SANDSTONE, verts=20); o["merge"] = "far.Land2"
o = cyl("CastleWilliamsTop", 13.2, 0.8, (cw.x, cw.y, WL + 7.3), M_SANDSTONE, verts=20); o["merge"] = "far.Land2"
anchor("battery.castleWilliams", tuple(cw))
# Bedloe's Island and its star fort (right), the Jersey shore (far right), Brooklyn Heights (left, across the East River)
far_land("Bedloes", 222.0, 228.0, 520.0, lambda t: 2.0 + 2.0 * math.sin(t * math.pi), M_FARLAND)
far_land("JerseyShore", 245.0, 300.0, 590.0, lambda t: 2.0 + 0.8 * noise.noise(Vector((t * 10, 4, 1))), M_FARLAND)
far_land("JerseyTown", 262.0, 292.0, 585.0, lambda t: 3.0 + 2.5 * abs(noise.noise(Vector((t * 40, 5, 1)))), M_FARTOWN, N=60, merge="far.Town2")
far_land("Brooklyn", 60.0, 112.0, 560.0, lambda t: 10.0 + 4.0 * math.sin(t * 2.5) + 3.0 * abs(noise.noise(Vector((t * 30, 6, 1)))), M_FARTOWN, N=60, merge="far.Town2")

# ============================================================================= the bay: water, far sea, sky
def land_dist(x, y):
    """Signed distance (m) from the water to the Battery's wall line (negative on land), and from Castle Garden."""
    d_wall = (wall_y(x) - y) if WALL_X0 < x < WALL_X1 else 99.0
    d_cg = math.hypot(x - CG.x, y - CG.y) - 28.0
    return d_wall, d_cg
def water():
    N = 64; k = 3.6
    cxy = Vector((0.0, -NEAR_R * 0.75, 0))
    def cx(t): return NEAR_R * 1.1 * math.sinh(k * t) / math.sinh(k)
    def cy(t):        # dense at the wall (t = 1 is the shore end)
        return -NEAR_R * (1.0 - math.sinh(k * t) / math.sinh(k)) + 6.0
    verts = []; faces = []
    for j in range(N + 1):
        for i in range(N + 1):
            x = cx(2 * i / N - 1); y = cy(j / N)
            r = math.hypot(x, y)
            if r > NEAR_R: x, y = x * NEAR_R / r, y * NEAR_R / r
            verts.append((x, y, WL - (0.06 if r > NEAR_R - 2 else 0.0)))
    def inside(v):
        dw, dc = land_dist(v[0], v[1]); return dw < -0.6 or dc < -0.8
    for j in range(N):
        for i in range(N):
            a = j * (N + 1) + i; quad = (a, a + 1, a + N + 2, a + N + 1)
            if all(inside(verts[q]) for q in quad): continue
            faces.append(quad)
    o = orient(mesh_from("water.ocean.bay", verts, faces, M_WATER), lambda c: (0, 0, 1))
    return o
WATER = water()
set_weight_colour(WATER, foam_fn=lambda p: max(smoothstep(2.2, 0.0, land_dist(p.x, p.y)[0]), smoothstep(2.5, 0.0, land_dist(p.x, p.y)[1]) * 0.8), kind="water")
me = WATER.data; uvl = me.uv_layers.new(name="UVMap")
for li, loop in enumerate(me.loops):
    p = me.vertices[loop.vertex_index].co; uvl.data[li].uv = (p.x / 10.0, p.y / 10.0)
def far_sea():
    verts = []; faces = []; seg = 96
    for r in (NEAR_R - 4.0, SKY_R - 2.0):
        for i in range(seg):
            a = 2 * math.pi * i / seg; verts.append((r * math.cos(a), r * math.sin(a), WL - 0.03))
    for i in range(seg):
        j = (i + 1) % seg; faces.append((i, j, seg + j, seg + i))
    orient(mesh_from("far.Sea", verts, faces, M_FARSEA), lambda c: (0, 0, 1))
far_sea()
sky_dome("SkyDome", M_SKY, SKY_R, seg=48, rings=16, el_min=-6.0)

bpy.context.view_layer.update()
# sway weights: the elm crowns move at the rim and top, not near the trunk; flags move along the fly
for (c_, base, split, H, Rc) in CROWNS:
    set_weight_colour(c_, weight_fn=lambda p, base=base, split=split, H=H, Rc=Rc:
                      0.25 + 0.5 * smoothstep(0.1 * Rc, Rc, math.hypot(p.x - base.x, p.y - base.y)) + 0.25 * smoothstep(base.z + split, base.z + H, p.z))
for (o, top, to_dir, L) in FLAGS:
    set_weight_colour(o, weight_fn=lambda p, top=top, to_dir=to_dir, L=L: smoothstep(0.0, L, (p - top).dot(to_dir)))

# ============================================================================= markers, sounds, lights, anchors, cameras
sound_empty("sound.surf.mole", (0.0, wall_y(0.0) - 0.3, WL + 0.4))
sound_empty("sound.surf.castle", (CG.x + 27.0, CG.y + 6.0, WL + 0.3))
sound_empty("sound.wind-trees.elms", (0.0, 12.0, 11.0))
sound_empty("sound.gulls.bay", tuple(geo(205.0, 60.0, 12.0)))
sound_empty("sound.crowd.promenade", (22.0, 6.0, 1.6))
anchor("reader.entrance", (0.0, 0.0, 0.0))
anchor("reader.look", (0.0, -1.0, EYE))
light_obj("light.sun", 'SUN', 4.0, (1.0, 0.93, 0.80), tuple(SUN_DIR * 30), direction=-SUN_DIR, angle=math.radians(1.0))
sky_l = light_obj("light.sky", 'SUN', 0.4, (0.62, 0.74, 1.0), (0, 0, 14), direction=(0.1, -0.15, -1.0), angle=math.radians(60))
sky_l.data.use_shadow = False
world = bpy.data.worlds.new("BayAfternoon"); scene.world = world; world.use_nodes = True
wn = world.node_tree; bg = wn.nodes["Background"]
try:
    skyn = wn.nodes.new("ShaderNodeTexSky"); skyn.sky_type = 'MULTIPLE_SCATTERING'; skyn.sun_disc = False
    skyn.sun_elevation = math.asin(SUN_DIR.z); skyn.sun_rotation = math.atan2(SUN_DIR.x, SUN_DIR.y); skyn.altitude = 50
    wn.links.new(skyn.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.14
except Exception as e:
    print("sky texture unavailable:", e); bg.inputs["Color"].default_value = (0.5, 0.6, 0.75, 1); bg.inputs["Strength"].default_value = 0.6

preview_page(EYE)
E = (0.0, 0.0, EYE)
camera("Cam_Reader", E, (0.0, -10.0, 1.1), clip_end=700)
camera("Cam_Page", E, (0.0, -10.0, 1.4), clip_end=700)
camera("Cam_Left", E, (10.0, -2.5, 1.2), clip_end=700)
camera("Cam_Right", E, (-10.0, -2.0, 1.4), clip_end=700)
camera("Cam_Behind", E, (0.5, 10.0, 2.5), clip_end=700)
camera("Cam_Down", E, (0.0, -1.6, -0.6), lens=16, clip_end=700)
camera("Cam_Castle", E, (CG.x, CG.y, 6.0), lens=35, clip_end=700)
camera("Cam_Over", (0.0, -0.9, 1.6), (0.0, -6.0, WL), lens=18, clip_end=700)

if not args.nosave: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(S["out"], "battery_waterfront_source.blend"))
print_budget()
if args.render:
    render_cams(SID, exposure={"*": -0.6})
if args.bake or args.export:
    T = args.tex
    size_for = {"M_Granite": T, "M_Coping": T // 2, "M_Gravel": T, "M_Lawn": T, "M_CastIron": T // 4, "M_BenchWood": T // 4, "M_ElmBark": T // 2,
                "M_ElmLeaves": T, "M_Facades": T // 2, "M_Roofs": T // 4, "M_Sandstone": T // 4, "M_PierTimber": T // 4, "M_ShipHulls": T // 4,
                "M_ShipSpars": T // 8, "M_ShipSails": T // 8, "M_Flag": T // 4, "M_FarSea": T // 8, "M_FarLand": T // 4, "M_FarTown": T // 4,
                "M_FarShips": T // 8, "M_SkyDome": T}
    bake_and_export("battery_waterfront.gltf", size_for, default_size=256, keep_names={"M_SkyDome": "SkyDome", "M_FarSea": "far.Sea"},
                    keep_uv={"SkyDome", "cloth.flag.castle", "cloth.flag.ships"}, emit_only={"SkyDome"})
print("DONE")
