"""
Fable: Regency interior pieces shared by the Netherfield drawing-room and Mr Bennet's library
(build_netherfield_drawing_room.py, build_longbourn_library.py). Builds on pride_kit.py.

Period: a gentleman's house of the 1790s-1810s. Painted walls above a panelled dado, moulded skirtings, chair rails and
cornices, six-panel doors in moulded architraves, tall sash windows with glazing bars and folding shutters in the
reveals, a marble chimney-piece round a cast-iron register grate, mahogany furniture (sabre-legged chairs, a pedestal
loo table, a scroll-ended sofa), silver or brass candlesticks with wax candles, calf- and vellum-bound books.
Everything procedural; no logos, no identifiable people (paintings are landscapes).

Living-scene names (docs/LIVING_SCENES.md): candlesticks return the wick top for fx.candle.*; fireplaces return the
fire base for fx.fire.*. Flames are render-only meshes (RenderOnly_*), deleted before export: Unity draws its own.
"""
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix, noise
import pride_kit as K
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, mix_f, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       texcoord_obj, wood, noisy, plain, box, cyl, sphere, lathe, tube, sweep, mesh_from, Frame, link, smoothstep)

RENDER_ONLY = []


# ----------------------------------------------------------------------------- materials
def paint_mat(name, color, rough=0.75, dirt=0.06, distemper=True):
    """Flat oil or distemper paint on plaster: faint trowel undulation, slightly greyer towards the skirting."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1500, -400))
    n = noise_(nt, co, 1.4, 5, 0.55, loc=(-1200, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, c4(color), maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.94, 1.04, (-1000, 0)), (-800, 0))
    low = maprange(nt, s.outputs["Z"], 0.0, 0.5, dirt, 0.0, (-1000, -400))
    col = mix_rgb(nt, 'MULTIPLY', low, col, (0.7, 0.68, 0.64, 1), (-600, 0))
    col = K.ao_mul(nt, col, 0.35, 0.35, (-400, -500))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    fine = noise_(nt, co, 60.0, 4, 0.6, loc=(-1200, -700))
    bump_from(nt, b, math_(nt, 'ADD', fine.outputs["Fac"], math_(nt, 'MULTIPLY', n.outputs["Fac"], 2.0, (-900, -800)), (-700, -750)), 0.08, 0.002)
    return m

def joinery_mat(name, color=(0.70, 0.69, 0.64), rough=0.38):
    """Lead-white oil paint on deal joinery, a soft satin, slightly yellowed, brush marks running along the grain."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    n = noise_(nt, co, 3.0, 4, 0.6, loc=(-1200, 0))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, c4(color), maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.95, 1.03, (-1000, 0)), (-800, 0))
    col = K.ao_mul(nt, col, 0.08, 0.45, (-500, -400))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.7, rough - 0.06, rough + 0.08, (-500, -150)), b.inputs["Roughness"])
    mp = node(nt, "ShaderNodeMapping", (-1300, -600)); mp.inputs["Scale"].default_value = (90, 90, 6); nt.links.new(co, mp.inputs["Vector"])
    br = noise_(nt, mp.outputs["Vector"], 2.0, 3, 0.5, loc=(-1100, -600))
    bump_from(nt, b, br.outputs["Fac"], 0.05, 0.001)
    return m

def boards_mat(name, light=(0.30, 0.19, 0.10), dark=(0.13, 0.075, 0.035), width=0.19, axis='X', wax=0.45):
    """Waxed oak floorboards, each board its own tone, dark joints, grain, a duller traffic path."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1600, 0))
    across = s.outputs["Y"] if axis == 'X' else s.outputs["X"]
    along = s.outputs["X"] if axis == 'X' else s.outputs["Y"]
    idx = math_(nt, 'DIVIDE', across, width, (-1400, 200))
    fl = math_(nt, 'FLOOR', idx, None, (-1200, 200)); fr = math_(nt, 'FRACT', idx, None, (-1200, 350))
    # board ends: staggered butt joints every 2-4 m
    endk = math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', along, math_(nt, 'MULTIPLY', fl, 1.37, (-1200, 500)), (-1100, 500)), 3.1, (-1000, 500)), None, (-900, 500))
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1000, 200), noise_dimensions='2D')
    cmb = node(nt, "ShaderNodeCombineXYZ", (-1100, 250)); nt.links.new(fl, cmb.inputs["X"]); nt.links.new(math_(nt, 'FLOOR', math_(nt, 'DIVIDE', math_(nt, 'ADD', along, math_(nt, 'MULTIPLY', fl, 1.37, (-1250, 600)), (-1150, 600)), 3.1, (-1050, 600)), None, (-950, 600)), cmb.inputs["Y"])
    nt.links.new(cmb.outputs[0], wn.inputs["Vector"])
    seam = ramp(nt, [(0.0, (0.25, 0.25, 0.25, 1)), (0.025, (1, 1, 1, 1)), (0.975, (1, 1, 1, 1)), (1.0, (0.25, 0.25, 0.25, 1))], (-1000, 400))
    nt.links.new(fr, seam.inputs["Fac"])
    endseam = maprange(nt, endk, 0.0, 0.003, 0.4, 1.0, (-800, 600))
    tone = ramp(nt, [(0.0, c4(dark)), (0.5, c4(tuple((a + b_) / 2 for a, b_ in zip(light, dark)))), (1.0, c4(light))], (-800, 200))
    nt.links.new(wn.outputs["Value"], tone.inputs["Fac"])
    mp = node(nt, "ShaderNodeMapping", (-1500, -400)); nt.links.new(co, mp.inputs["Vector"])
    mp.inputs["Scale"].default_value = (1.5, 40, 40) if axis == 'X' else (40, 1.5, 40)
    g = noise_(nt, mp.outputs["Vector"], 1.0, 10, 0.65, 0.8, (-1200, -400))
    gr = ramp(nt, [(0.3, (0.6, 0.6, 0.6, 1)), (0.5, (1, 1, 1, 1)), (0.7, (0.82, 0.82, 0.82, 1))], (-1000, -400))
    nt.links.new(g.outputs["Fac"], gr.inputs["Fac"])
    col = mix_rgb(nt, 'MULTIPLY', 0.55, tone.outputs["Color"], gr.outputs["Color"], (-600, 100))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, seam.outputs["Color"], (-400, 100))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, endseam, (-250, 100))
    col = K.ao_mul(nt, col, 0.2, 0.4, (-150, -500))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, g.outputs["Fac"], 0.3, 0.7, wax - 0.08, wax + 0.12, (-300, -200)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'MULTIPLY', seam.outputs["Color"], endseam, (-200, -300)), 0.4, 0.002)
    return m

def mahogany(name="M_Mahogany", rough=(0.28, 0.5), coat=0.35):
    return wood(name, base=(0.17, 0.055, 0.025), dark=(0.055, 0.016, 0.008), light=(0.30, 0.11, 0.05), scale=1.4, rough=rough,
                grain_dir=(1, 1, 10), coat=coat, ao=0.25, bump=0.15)

def gilt(name="M_Gilt"):
    m, nt, b = new_mat(name)
    co = obj_coords(nt); n = noise_(nt, co, 25.0, 5, 0.6, loc=(-900, 0))
    col = mix_rgb(nt, 'MIX', maprange(nt, n.outputs["Fac"], 0.35, 0.7, 0, 1, (-700, 0)), (0.52, 0.36, 0.14, 1), (0.78, 0.60, 0.30, 1), (-500, 0))
    col = K.ao_mul(nt, col, 0.04, 0.6, (-400, -300))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Metallic"].default_value = 1.0
    nt.links.new(maprange(nt, n.outputs["Fac"], 0.3, 0.7, 0.25, 0.45, (-500, -200)), b.inputs["Roughness"])
    return m

def marble(name="M_Marble", base=(0.78, 0.77, 0.74), vein=(0.42, 0.42, 0.42)):
    """Statuary marble: warm white, soft grey veins, honed (not glassy)."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt)
    w = noise_(nt, co, 2.2, 8, 0.6, distortion=3.5, loc=(-1100, 0))
    v = maprange(nt, w.outputs["Fac"], 0.47, 0.5, 0, 1, (-850, 0))
    v2 = maprange(nt, w.outputs["Fac"], 0.5, 0.53, 1, 0, (-850, -150))
    vm = math_(nt, 'MULTIPLY', v, v2, (-700, -50))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', vm, 0.7, (-550, -50)), c4(base), c4(vein), (-400, 0))
    col = K.ao_mul(nt, col, 0.06, 0.5, (-300, -400))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.22
    b.inputs["Subsurface Weight"].default_value = 0.0
    return m

def silk(name, a, b_, stripes=0.0, stripe_w=0.06, axis='Z', sheen=0.6, rough=0.55, damask=0.0):
    """Silk or worsted upholstery: optional Regency stripe (along `axis`) or a damask figure, sheen, a fine weave."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1500, -300))
    col = c4(a)
    if stripes:
        coord = s.outputs["X"] if axis == 'X' else (s.outputs["Y"] if axis == 'Y' else s.outputs["Z"])
        fr = math_(nt, 'FRACT', math_(nt, 'DIVIDE', math_(nt, 'ADD', coord, math_(nt, 'MULTIPLY', s.outputs["Z"], 0.0, (-1300, -500)), (-1250, -400)), stripe_w * 2, (-1150, -300)), None, (-1000, -300))
        sm = maprange(nt, fr, 0.48, 0.52, 0, 1, (-850, -300))
        col = mix_rgb(nt, 'MIX', sm, c4(a), c4(b_), (-600, 0))
    if damask:
        v = voronoi_(nt, co, 9.0, 'SMOOTH_F1', (-1200, 200))
        n = noise_(nt, co, 18.0, 3, 0.5, distortion=2.0, loc=(-1200, 450))
        fig = maprange(nt, math_(nt, 'ADD', v.outputs["Distance"], math_(nt, 'MULTIPLY', n.outputs["Fac"], 0.4, (-1000, 450)), (-900, 300)), 0.45, 0.55, 0, damask, (-750, 300))
        col = mix_rgb(nt, 'MIX', fig, col, c4(b_), (-450, 0))
    col = K.ao_mul(nt, col, 0.1, 0.45, (-300, -500))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.35
    mp = node(nt, "ShaderNodeMapping", (-1300, -800)); mp.inputs["Scale"].default_value = (400, 400, 400); nt.links.new(co, mp.inputs["Vector"])
    wv = noise_(nt, mp.outputs["Vector"], 1.0, 2, 0.5, loc=(-1100, -800))
    bump_from(nt, b, wv.outputs["Fac"], 0.12, 0.0005)
    return m

def carpet_mat(name, cx, cy, hx, hy, field=(0.20, 0.035, 0.03), ground2=(0.05, 0.075, 0.07), border=(0.035, 0.06, 0.07), buff=(0.42, 0.33, 0.20)):
    """A Brussels/Axminster carpet of the period: a buff-outlined lattice of rosettes on a crimson field, a dark blue-green
    border with a guard stripe, worn paler where people walk. (cx, cy) centre, (hx, hy) half sizes."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-1800, 0))
    dx = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', s.outputs["X"], cx, (-1600, 200)), None, (-1450, 200))
    dy = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', s.outputs["Y"], cy, (-1600, 50)), None, (-1450, 50))
    ex = math_(nt, 'SUBTRACT', hx, dx, (-1300, 200)); ey = math_(nt, 'SUBTRACT', hy, dy, (-1300, 50))
    edge = math_(nt, 'MINIMUM', ex, ey, (-1150, 120))        # distance in from the carpet's edge
    bd = maprange(nt, edge, 0.34, 0.36, 1, 0, (-1000, 120))   # inside the border = 0
    guard = math_(nt, 'MULTIPLY', maprange(nt, edge, 0.05, 0.065, 0, 1, (-1000, 300)), maprange(nt, edge, 0.085, 0.10, 1, 0, (-1000, 400)), (-850, 350))
    guard2 = math_(nt, 'MULTIPLY', maprange(nt, edge, 0.30, 0.315, 0, 1, (-1000, 500)), maprange(nt, edge, 0.335, 0.35, 1, 0, (-1000, 600)), (-850, 550))
    # field lattice: a diamond grid with rosettes
    rot = node(nt, "ShaderNodeVectorRotate", (-1500, -300), rotation_type='Z_AXIS'); rot.inputs["Angle"].default_value = math.radians(45)
    nt.links.new(co, rot.inputs["Vector"])
    mp = node(nt, "ShaderNodeMapping", (-1350, -300)); mp.inputs["Scale"].default_value = (4.2, 4.2, 1); nt.links.new(rot.outputs[0], mp.inputs["Vector"])
    sp = sep_xyz(nt, mp.outputs["Vector"], (-1200, -300))
    fx = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', sp.outputs["X"], None, (-1050, -250)), 0.5, (-950, -250)), None, (-850, -250))
    fy = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', sp.outputs["Y"], None, (-1050, -400)), 0.5, (-950, -400)), None, (-850, -400))
    lat = maprange(nt, math_(nt, 'MAXIMUM', fx, fy, (-750, -300)), 0.44, 0.47, 0, 1, (-650, -300))
    ros = maprange(nt, math_(nt, 'ADD', math_(nt, 'MULTIPLY', fx, fx, (-750, -500)), math_(nt, 'MULTIPLY', fy, fy, (-750, -600)), (-650, -550)), 0.012, 0.02, 1, 0, (-550, -550))
    ros2 = maprange(nt, math_(nt, 'ADD', math_(nt, 'MULTIPLY', fx, fx, (-750, -700)), math_(nt, 'MULTIPLY', fy, fy, (-750, -800)), (-650, -750)), 0.004, 0.007, 1, 0, (-550, -750))
    col = c4(field)
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', lat, 0.55, (-450, -350)), col, c4(buff), (-400, -300))
    col = mix_rgb(nt, 'MIX', ros, col, c4(ground2), (-300, -400))
    col = mix_rgb(nt, 'MIX', ros2, col, c4(buff), (-200, -500))
    # border: dark ground with a running scroll (noise threshold), guard stripes in buff
    bn = noise_(nt, co, 9.0, 3, 0.5, distortion=1.5, loc=(-900, 800))
    scroll = maprange(nt, bn.outputs["Fac"], 0.52, 0.56, 0, 1, (-700, 800))
    bcol = mix_rgb(nt, 'MIX', scroll, c4(border), c4(field), (-500, 700))
    col = mix_rgb(nt, 'MIX', bd, col, bcol, (-100, 0))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MAXIMUM', guard, guard2, (-400, 450)), col, c4(buff), (50, 0))
    # wear and fluff
    wn = noise_(nt, co, 0.8, 3, 0.5, loc=(-900, -1000))
    col = mix_rgb(nt, 'MIX', maprange(nt, wn.outputs["Fac"], 0.55, 0.7, 0, 0.18, (-600, -1000)), col, c4(buff), (200, 0))
    pile = noise_(nt, co, 260.0, 3, 0.6, loc=(-900, -1250))
    col = mix_rgb(nt, 'MULTIPLY', 1.0, col, maprange(nt, pile.outputs["Fac"], 0.3, 0.7, 0.85, 1.08, (-600, -1250)), (350, 0))
    col = K.ao_mul(nt, col, 0.25, 0.4, (400, -500))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.92
    b.inputs["Sheen Weight"].default_value = 0.4
    bump_from(nt, b, pile.outputs["Fac"], 0.25, 0.001)
    return m

def flame_mat(name="M_RenderFlame", strength=18.0):
    m, nt, b = new_mat(name)
    co = node(nt, "ShaderNodeTexCoord", (-900, 0)); s = sep_xyz(nt, co.outputs["Generated"], (-700, 0))
    col = mix_rgb(nt, 'MIX', s.outputs["Z"], (1.0, 0.42, 0.10, 1), (1.0, 0.80, 0.45, 1), (-400, 0))
    nt.links.new(col, b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = strength
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    return m


# ----------------------------------------------------------------------------- the room shell
class Room:
    """An axis-aligned room: interior x0..x1, y0..y1, floor z = 0, ceiling at h. Walls 'S' (y0), 'N' (y1), 'W' (x0),
    'E' (x1). Openings per wall: list of (centre along the wall, width, z0, z1, kind)."""
    def __init__(self, x0, x1, y0, y1, h, t=0.35):
        self.x0, self.x1, self.y0, self.y1, self.h, self.t = x0, x1, y0, y1, h, t
        self.openings = {'S': [], 'N': [], 'W': [], 'E': []}
    def wall_frame(self, w):
        """origin (start of the wall's inner face), along (unit), inward normal; walls run counter-clockwise."""
        if w == 'S': return Vector((self.x0, self.y0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)), self.x1 - self.x0
        if w == 'E': return Vector((self.x1, self.y0, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0)), self.y1 - self.y0
        if w == 'N': return Vector((self.x1, self.y1, 0)), Vector((-1, 0, 0)), Vector((0, -1, 0)), self.x1 - self.x0
        return Vector((self.x0, self.y1, 0)), Vector((0, -1, 0)), Vector((1, 0, 0)), self.y1 - self.y0
    def at(self, w, u, z=0.0, inset=0.0):
        o, a, n, L = self.wall_frame(w); return o + a * u + n * inset + Vector((0, 0, z))
    def yaw(self, w):
        """yaw for a Frame whose +Y points into the room from wall w."""
        o, a, n, L = self.wall_frame(w); return math.atan2(-n.x, n.y)

def build_walls(R, mat, name="Wall"):
    """Each wall as boxes round its openings (thickness outwards)."""
    for w in ('S', 'E', 'N', 'W'):
        o, a, n, L = R.wall_frame(w)
        ops = sorted(R.openings[w], key=lambda op: op[0])
        cuts = [0.0]
        for (u, wd, z0, z1, kind) in ops: cuts += [u - wd / 2, u + wd / 2]
        cuts.append(L)
        def put(u0, u1, z0, z1, tag):
            if u1 - u0 < 1e-3 or z1 - z0 < 1e-3: return
            ext0 = R.t if u0 <= 1e-6 else 0.0; ext1 = R.t if u1 >= L - 1e-6 else 0.0
            c = o + a * ((u0 - ext0 + u1 + ext1) / 2) - n * (R.t / 2) + Vector((0, 0, (z0 + z1) / 2))
            size = (abs(a.x) * (u1 - u0 + ext0 + ext1) + abs(n.x) * R.t, abs(a.y) * (u1 - u0 + ext0 + ext1) + abs(n.y) * R.t, z1 - z0)
            box(f"{name}{w}{tag}", size, tuple(c), mat)
        for i in range(0, len(cuts), 2):
            put(cuts[i], cuts[i + 1], -0.05, R.h + 0.05, f"_{i}")
        for k, (u, wd, z0, z1, kind) in enumerate(ops):
            put(u - wd / 2, u + wd / 2, -0.05, z0, f"_lo{k}")
            put(u - wd / 2, u + wd / 2, z1, R.h + 0.05, f"_hi{k}")

def runs(R, w, z0, z1, extra=0.0):
    """the spans of wall w not interrupted by an opening between heights z0 and z1: [(u0, u1)]."""
    o, a, n, L = R.wall_frame(w)
    cuts = []
    for (u, wd, oz0, oz1, kind) in R.openings[w]:
        if oz0 < z1 and oz1 > z0: cuts.append((u - wd / 2 - extra, u + wd / 2 + extra))
    cuts.sort(); spans = []; s = 0.0
    for c0, c1 in cuts:
        if c0 > s: spans.append((s, c0))
        s = max(s, c1)
    if s < L: spans.append((s, L))
    return spans

def moulding_runs(R, name, profile, z, mat, z_band=None, extra=0.0, walls=('S', 'E', 'N', 'W'), continuous_ok=True):
    """sweep a profile (across into the room, up from z) along every wall run at height z, stopping at openings."""
    zb = z_band or (z, z + max(p[1] for p in profile))
    for w in walls:
        o, a, n, L = R.wall_frame(w)
        for k, (u0, u1) in enumerate(runs(R, w, zb[0], zb[1], extra)):
            # extend into the corners so mitres meet
            e0 = 0.0 if u0 > 1e-6 else -max(p[0] for p in profile)
            e1 = 0.0 if u1 < L - 1e-6 else max(p[0] for p in profile)
            p0 = o + a * (u0 + e0) + Vector((0, 0, z)); p1 = o + a * (u1 + e1) + Vector((0, 0, z))
            sweep(f"{name}{w}{k}", profile, [p0, p1], mat, cap=True)

def cornice_profile(depth=0.22, height=0.26):
    """a Greek-revival cornice: fillet, cyma, corona, bed moulding."""
    d, h = depth, height
    return [(0.0, -h), (0.03 * d / 0.22, -h), (0.05, -h + 0.03), (0.07, -h + 0.07), (0.12, -h + 0.10), (0.13, -h + 0.13), (0.16, -h + 0.15),
            (d * 0.92, -h + 0.19), (d, -h + 0.21), (d, -0.03), (d * 0.6, -0.02), (0.02, 0.0), (0.0, 0.0)]

def skirting_profile(h=0.24):
    return [(0.0, 0.0), (0.024, 0.0), (0.024, h - 0.04), (0.018, h - 0.025), (0.014, h - 0.01), (0.008, h), (0.0, h)]

def rail_profile():
    return [(0.0, -0.035), (0.012, -0.035), (0.022, -0.02), (0.026, 0.0), (0.02, 0.018), (0.008, 0.03), (0.0, 0.03)]

def dado_panels(R, mat, rail_z=0.92, skirt=0.24, step=1.25, walls=('S', 'E', 'N', 'W'), name="DadoPanel"):
    """sunk panels in the dado between skirting and chair rail: a bolection-like raised moulding frame per panel."""
    for w in walls:
        o, a, n, L = R.wall_frame(w)
        for k, (u0, u1) in enumerate(runs(R, w, skirt, rail_z, 0.08)):
            span = u1 - u0; np_ = max(1, int(round(span / step)))
            if span < 0.5: continue
            pw = span / np_
            for i in range(np_):
                c0 = u0 + i * pw + 0.09; c1 = u0 + (i + 1) * pw - 0.09
                z0 = skirt + 0.1; z1 = rail_z - 0.12
                pts = [o + a * c0 + Vector((0, 0, z0)), o + a * c1 + Vector((0, 0, z0)), o + a * c1 + Vector((0, 0, z1)), o + a * c0 + Vector((0, 0, z1))]
                # a small moulding frame, built as four thin boxes
                for (p, q) in zip(pts, pts[1:] + pts[:1]):
                    mid = (p + q) / 2 + n * 0.008; L2 = (q - p).length
                    horiz = abs(q.z - p.z) < 1e-6
                    size = (abs(a.x) * (L2 if horiz else 0.03) + abs(n.x) * 0.016, abs(a.y) * (L2 if horiz else 0.03) + abs(n.y) * 0.016, 0.03 if horiz else L2)
                    box(f"{name}{w}{k}{i}", size, tuple(mid), mat, bevel=0.004)


def six_panel_door(name, R, w, u, width, height, leaf_mat, frame_mat, knob_mat, open_deg=0.0, hinge_left=True):
    """a six-panel door in a moulded architrave; the leaf may stand a little open (hinged at the left, opening inwards)."""
    o, a, n, L = R.wall_frame(w)
    R.openings[w].append((u, width, 0.0, height, "door"))
    # architrave: a moulded band round the opening
    prof = [(0.0, 0.0), (0.03, 0.0), (0.03, 0.012), (0.024, 0.03), (0.024, 0.09), (0.012, 0.12), (0.0, 0.13)]
    base = o + a * u
    left = base - a * (width / 2); right = base + a * (width / 2)
    for side, p in (("L", left), ("R", right)):
        dirv = -a if side == "L" else a
        pts = [p + Vector((0, 0, 0)), p + Vector((0, 0, height))]
        # profile across = outwards from the opening (along dirv), up = into the room (n)
        bm_prof = [(pp[1], pp[0]) for pp in prof]
        verts = []; faces = []
        for zz in (0.0, height + 0.13):
            ring = [len(verts) + i for i in range(len(prof))]
            for (acr, up) in prof:
                verts.append(tuple(p + dirv * up + n * acr + Vector((0, 0, zz))))
        nP = len(prof)
        for i in range(nP - 1): faces.append((i, i + 1, nP + i + 1, nP + i))
        mesh_from(f"{name}Arch{side}", verts, faces, frame_mat)
    verts = []; faces = []
    for t, uu in enumerate((-width / 2 - 0.13, width / 2 + 0.13)):
        for (acr, up) in prof:
            verts.append(tuple(base + a * uu + n * acr + Vector((0, 0, height + up))))
    nP = len(prof)
    for i in range(nP - 1): faces.append((i, i + 1, nP + i + 1, nP + i))
    mesh_from(f"{name}ArchTop", verts, faces, frame_mat)
    # reveal linings
    for side, p in (("L", left), ("R", right)):
        box(f"{name}Lining{side}", (abs(a.x) * 0.03 + abs(n.x) * R.t, abs(a.y) * 0.03 + abs(n.y) * R.t, height), tuple(p - n * (R.t / 2) + Vector((0, 0, height / 2))), frame_mat)
    box(f"{name}LiningTop", (abs(a.x) * width + abs(n.x) * R.t, abs(a.y) * width + abs(n.y) * R.t, 0.03), tuple(base - n * (R.t / 2) + Vector((0, 0, height - 0.015))), frame_mat)
    # the leaf
    hinge = left if hinge_left else right
    ang = math.radians(open_deg) * (1 if hinge_left else -1)
    along = (a if hinge_left else -a)
    rotm = Matrix.Rotation(-ang if hinge_left else ang, 3, 'Z')
    lw = width - 0.01; th = 0.045
    def P(s, z, d=0.0):    # s along the leaf from the hinge, z up, d towards the room
        v = along * s + n * d
        return tuple(hinge + rotm @ v + Vector((0, 0, z)))
    yaw = math.atan2((rotm @ along).y, (rotm @ along).x)
    box(f"{name}Leaf", (lw, th, height - 0.01), P(lw / 2, height / 2, -0.06), leaf_mat, bevel=0.003, rot=(0, 0, yaw))
    # six raised panels (two small at the top, four tall)
    for row, (z0, z1) in enumerate(((0.12, 0.92), (1.02, 1.82), (1.92, height - 0.12))):
        for col in range(2):
            s0 = 0.12 + col * (lw / 2 - 0.06); s1 = s0 + lw / 2 - 0.18
            for d in (-0.06 + th / 2 + 0.006, -0.06 - th / 2 - 0.006):
                box(f"{name}Panel{row}{col}{d > -0.06}", (s1 - s0, 0.012, z1 - z0), P((s0 + s1) / 2, (z0 + z1) / 2, d), leaf_mat, bevel=0.008, rot=(0, 0, yaw))
    for d in (-0.06 + th / 2 + 0.025, -0.06 - th / 2 - 0.025):
        sphere(f"{name}Knob{d > -0.06}", 0.028, P(lw - 0.09, 1.0, d), knob_mat, seg=10)
        box(f"{name}Rose{d > -0.06}", (0.05, 0.006, 0.05), P(lw - 0.09, 1.0, d * 0.96), knob_mat, rot=(0, 0, yaw))
    return hinge

def sash_window(name, R, w, u, width, sill, height, frame_mat, glass_mat, shutter_mat, panes=(3, 4), curtain=None, curtain_mat=None,
                drawn=1.0, pelmet_mat=None, night=True):
    """A tall sash window in a deep reveal with folding shutters, a stone sill outside and (optionally) curtains on a
    gilt pole, drawn together (drawn = 1) or open. Glass panes go in a mesh named WindowGlass_* (FableBuild draws it)."""
    o, a, n, L = R.wall_frame(w)
    R.openings[w].append((u, width, sill, sill + height, "window"))
    base = o + a * u
    rev = R.t
    # reveal linings and shutters folded into the reveals (panelled)
    for side, sgn in (("L", -1), ("R", 1)):
        p = base + a * (sgn * width / 2)
        box(f"{name}Reveal{side}", (abs(a.x) * 0.03 + abs(n.x) * rev, abs(a.y) * 0.03 + abs(n.y) * rev, height), tuple(p - n * (rev / 2) + Vector((0, 0, sill + height / 2))), frame_mat)
        sh = p - a * (sgn * 0.05) - n * 0.08
        box(f"{name}Shutter{side}", (abs(a.x) * 0.07 + abs(n.x) * 0.16, abs(a.y) * 0.07 + abs(n.y) * 0.16, height - 0.1), tuple(sh + Vector((0, 0, sill + height / 2))), shutter_mat, bevel=0.005)
    box(f"{name}Soffit", (abs(a.x) * width + abs(n.x) * rev, abs(a.y) * width + abs(n.y) * rev, 0.03), tuple(base - n * (rev / 2) + Vector((0, 0, sill + height - 0.015))), frame_mat)
    box(f"{name}Seat", (abs(a.x) * (width + 0.08) + abs(n.x) * (rev + 0.06), abs(a.y) * (width + 0.08) + abs(n.y) * (rev + 0.06), 0.04), tuple(base - n * (rev / 2 - 0.03) + Vector((0, 0, sill - 0.02))), frame_mat, bevel=0.006)
    # the sash frame and glazing bars, set back in the reveal
    fp = base - n * (rev * 0.62)
    th = 0.05
    def fbox(nm, size_along, size_z, along, z):
        box(f"{name}{nm}", (abs(a.x) * size_along + abs(n.x) * th, abs(a.y) * size_along + abs(n.y) * th, size_z), tuple(fp + a * along + Vector((0, 0, z))), frame_mat)
    fbox("FrameL", 0.07, height, -width / 2 + 0.035, sill + height / 2); fbox("FrameR", 0.07, height, width / 2 - 0.035, sill + height / 2)
    fbox("FrameT", width, 0.07, 0, sill + height - 0.035); fbox("FrameB", width, 0.09, 0, sill + 0.045)
    fbox("Meeting", width, 0.045, 0, sill + height / 2)
    nx, nz = panes
    for i in range(1, nx):
        fbox(f"BarV{i}", 0.018, height - 0.1, -width / 2 + width * i / nx, sill + height / 2)
    for half in (0, 1):
        for j in range(1, nz // 2):
            fbox(f"BarH{half}{j}", width - 0.08, 0.018, 0, sill + half * height / 2 + height / 2 * j / (nz // 2))
    gl = box(f"WindowGlass_{name}", (abs(a.x) * width + abs(n.x) * 0.006, abs(a.y) * width + abs(n.y) * 0.006, height), tuple(fp - n * 0.01 + Vector((0, 0, sill + height / 2))), glass_mat)
    if curtain_mat is not None:
        rod_z = sill + height + 0.32
        pole = cyl(f"{name}Pole", 0.025, width + 0.9, tuple(base + n * 0.12 + Vector((0, 0, rod_z))), pelmet_mat or frame_mat, verts=10,
                   rot=(0, math.pi / 2, 0) if abs(a.x) > 0.5 else (math.pi / 2, 0, 0))
        for side, sgn in (("L", -1), ("R", 1)):
            sphere(f"{name}Finial{side}", 0.05, tuple(base + a * (sgn * (width / 2 + 0.48)) + n * 0.12 + Vector((0, 0, rod_z))), pelmet_mat or frame_mat, seg=10)
        # two curtains, each a pleated hanging with deep folds, meeting in the middle when drawn
        cw = (width / 2 + 0.42) * (0.55 + 0.45 * drawn)
        for side, sgn in (("L", -1), ("R", 1)):
            outer = sgn * (width / 2 + 0.45); inner = outer - sgn * cw
            curtain_panel(f"{name}Curtain{side}", base, a, n, outer, inner, rod_z - 0.03, -0.02, curtain_mat, folds=int(cw / 0.12))
        # a swagged pelmet board covered in the same stuff
        box(f"{name}Pelmet", (abs(a.x) * (width + 1.0) + abs(n.x) * 0.2, abs(a.y) * (width + 1.0) + abs(n.y) * 0.2, 0.32), tuple(base + n * 0.12 + Vector((0, 0, rod_z + 0.1))), curtain_mat)
    return gl

def curtain_panel(name, base, a, n, u0, u1, ztop, zbot, mat, folds=10, depth=0.07):
    """a hanging curtain: deep, irregular vertical folds, gathered tight at the top, breaking on the floor."""
    rnd = random.Random(hash(name) & 0xffff)
    nu = folds * 4; nz = 10
    verts = []; faces = []; uvs = []
    phases = [rnd.uniform(0, 1) for _ in range(4)]
    for j in range(nz + 1):
        t = j / nz; z = ztop + (zbot - ztop) * t
        for i in range(nu + 1):
            s = i / nu; u = u0 + (u1 - u0) * s
            amp = depth * (0.75 + 0.25 * math.sin(s * 7 + phases[0])) * (0.85 + 0.3 * t)
            d = amp * math.sin(2 * math.pi * s * folds + 0.4 * math.sin(t * 3 + phases[1]))
            d += 0.03 + (0.04 * t * t if t > 0.92 else 0.0)
            p = base + a * u + n * (0.1 + d) + Vector((0, 0, z))
            if t > 0.96: p += n * 0.05 * (t - 0.96) / 0.04
            verts.append(tuple(p)); uvs.append((s, t))
    W = nu + 1
    for j in range(nz):
        for i in range(nu):
            faces.append((j * W + i, j * W + i + 1, (j + 1) * W + i + 1, (j + 1) * W + i))
    return mesh_from(name, verts, faces, mat, smooth=True, uvs=uvs)


# ----------------------------------------------------------------------------- furniture
def sabre_chair(name, origin, yaw, wood_mat, seat_mat, pushed=0.0, tilt=0.0):
    """a Regency dining or card-room chair: sabre legs front and back, a broad curved tablet top rail, a horizontal mid
    rail, a drop-in upholstered seat."""
    F = Frame(origin, yaw)
    sw, sd, sh = 0.46, 0.44, 0.45
    for sx in (-1, 1):
        # front sabre legs curve forward; back legs sweep back and continue up as the back uprights
        tube(f"{name}FL{sx}", [F.p(sx * sw / 2 * 0.92, sd / 2 + 0.05, 0.0), F.p(sx * sw / 2 * 0.92, sd / 2 + 0.01, 0.2), F.p(sx * sw / 2 * 0.92, sd / 2 - 0.02, sh - 0.05)],
             [0.016, 0.019, 0.021], wood_mat, sides=6)
        tube(f"{name}BL{sx}", [F.p(sx * sw / 2 * 0.9, -sd / 2 - 0.09, 0.0), F.p(sx * sw / 2 * 0.9, -sd / 2 - 0.02, 0.22), F.p(sx * sw / 2 * 0.9, -sd / 2, sh - 0.04),
                                F.p(sx * sw / 2 * 0.88, -sd / 2 - 0.04, 0.68), F.p(sx * sw / 2 * 0.86, -sd / 2 - 0.09, 0.86)],
             [0.017, 0.019, 0.02, 0.018, 0.016], wood_mat, sides=6)
    F.box(f"{name}SeatRail", (sw, sd, 0.06), (0, 0, sh - 0.03), wood_mat, bevel=0.006)
    F.box(f"{name}Seat", (sw - 0.05, sd - 0.04, 0.05), (0, 0.005, sh + 0.02), seat_mat, bevel=0.02)
    # curved tablet top rail and a turned mid rail
    pts = [F.p(-sw / 2 * 0.95, -sd / 2 - 0.09 + 0.01 * k, 0.83) for k in range(1)]
    for k, (z, r, dep) in enumerate(((0.83, 0.03, 0.10), (0.66, 0.012, 0.0))):
        ptsr = []
        for i in range(7):
            s = -1 + 2 * i / 6; ptsr.append(F.p(s * sw / 2 * 0.92, -sd / 2 - 0.06 - 0.045 * (1 - s * s) - (0.03 if k == 0 else -0.015), z))
        if k == 0:
            for i, p in enumerate(ptsr):
                pass
            tube(f"{name}Top", ptsr, 0.012, wood_mat, sides=4)
            F.box(f"{name}Tablet", (sw * 0.95, 0.025, 0.09), (0, -sd / 2 - 0.105, 0.84), wood_mat, bevel=0.008, rx=-0.12)
        else:
            tube(f"{name}Mid", ptsr, r, wood_mat, sides=6)
    return F

def pedestal_table(name, origin, top_mat, wood_mat, radius=0.62, height=0.72, feet=4, cloth=None):
    """a round loo (or breakfast) table on a turned pillar, a platform and splayed sabre feet with brass caps."""
    F = Frame(origin, 0.0)
    lathe(f"{name}Top", [(0.0, height - 0.035), (radius, height - 0.035), (radius + 0.005, height - 0.02), (radius, height), (0.0, height)], F.p(0, 0, 0), top_mat, steps=48)
    lathe(f"{name}Apron", [(radius * 0.97, height - 0.11), (radius * 0.975, height - 0.035), (radius * 0.94, height - 0.035), (radius * 0.94, height - 0.11)], F.p(0, 0, 0), top_mat, steps=48)
    lathe(f"{name}Pillar", [(0.0, 0.16), (0.11, 0.16), (0.12, 0.2), (0.08, 0.25), (0.06, 0.32), (0.075, 0.42), (0.055, 0.52), (0.045, 0.6), (0.07, 0.62), (0.08, height - 0.11), (0.0, height - 0.11)],
          F.p(0, 0, 0), wood_mat, steps=16)
    lathe(f"{name}Platform", [(0.0, 0.10), (0.20, 0.10), (0.22, 0.13), (0.20, 0.17), (0.0, 0.17)], F.p(0, 0, 0), wood_mat, steps=feet * 4)
    for k in range(feet):
        a = 2 * math.pi * (k + 0.5) / feet; d = Vector((math.cos(a), math.sin(a), 0))
        pts = [F.p(*(d * 0.16 + Vector((0, 0, 0.14)))), F.p(*(d * 0.30 + Vector((0, 0, 0.10)))), F.p(*(d * 0.42 + Vector((0, 0, 0.05)))), F.p(*(d * 0.50 + Vector((0, 0, 0.02))))]
        tube(f"{name}Foot{k}", pts, [0.04, 0.032, 0.024, 0.02], wood_mat, sides=6)
    return F.p(0, 0, height)

def candlestick(name, loc, metal, wax, height=0.27, candle_h=0.2, arms=0, flame=True, yaw=0.0):
    """a silver (Sheffield plate) or brass candlestick: a square stepped foot, a column with a knop, a nozzle with a
    drip-pan; arms > 0 makes a two/three-light candelabrum. Returns the wick tops (fx.candle.*)."""
    x, y, z = loc
    lathe(f"{name}Base", [(0.0, 0.0), (0.065, 0.0), (0.066, 0.012), (0.05, 0.02), (0.03, 0.035), (0.0, 0.04)], (x, y, z), metal, steps=16)
    lathe(f"{name}Col", [(0.0, 0.03), (0.016, 0.035), (0.013, 0.08), (0.022, 0.10), (0.012, 0.13), (0.011, height - 0.04), (0.016, height - 0.025), (0.0, height - 0.025)], (x, y, z), metal, steps=12)
    tops = []
    if arms:
        Fr = Frame((x, y), yaw, z=z)
        cups = [Vector((0, 0, height + 0.12))] + [Vector((math.cos(math.pi * k), math.sin(math.pi * k) * 0, 0)) * 0.15 + Vector((0, 0, height + 0.06)) for k in range(arms)]
        for k in range(arms):
            sgn = -1 if k == 0 else 1
            tube(f"{name}Arm{k}", [Fr.p(0, 0, height - 0.03), Fr.p(sgn * 0.06, 0, height + 0.04), Fr.p(sgn * 0.13, 0, height + 0.05), Fr.p(sgn * 0.15, 0, height + 0.06)], 0.007, metal, sides=6)
        cups = [Fr.p(0, 0, height + 0.02)] + [Fr.p(sgn * 0.15, 0, height + 0.06) for sgn in (-1, 1)][:arms]
    else:
        cups = [(x, y, z + height - 0.025)]
    for k, c in enumerate(cups):
        c = Vector(c)
        lathe(f"{name}Nozzle{k}", [(0.0, 0.0), (0.04, 0.0), (0.042, 0.006), (0.02, 0.012), (0.017, 0.04), (0.0, 0.04)], tuple(c), metal, steps=14)
        ch = candle_h * (0.85 + 0.15 * ((hash(name) + k) % 7) / 7)
        lathe(f"{name}Candle{k}", [(0.0, 0.035), (0.0115, 0.035), (0.0115, ch - 0.006), (0.009, ch), (0.0, ch)], tuple(c), wax, steps=10)
        wick = c + Vector((0, 0, ch + 0.006))
        cyl(f"{name}Wick{k}", 0.0012, 0.012, tuple(wick), K_WICK(), verts=4)
        if flame:
            fl = lathe(f"RenderOnly_{name}Flame{k}", [(0.0, 0.0), (0.004, 0.004), (0.006, 0.012), (0.005, 0.022), (0.002, 0.032), (0.0, 0.038)], tuple(wick - Vector((0, 0, 0.002))), K_FLAME(), steps=8)
            RENDER_ONLY.append(fl)
        tops.append(tuple(wick))
    return tops

_W = {}
def K_WICK():
    if "w" not in _W: _W["w"] = plain("M_Wick", (0.02, 0.015, 0.01), rough=0.9)
    return _W["w"]
def K_FLAME():
    if "f" not in _W: _W["f"] = flame_mat()
    return _W["f"]

def book(name, loc, size, yaw, cover_mat, page_mat, pitch=0.0, roll=0.0, open_=False):
    """a bound book: boards slightly proud of the text block, rounded spine (as a half cylinder). size = (w, depth, h)
    lying with its h along local Y if flat. Here: (thickness, width, height) standing; use roll for lying flat."""
    t, w, h = size
    R_ = (Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(pitch, 4, 'X') @ Matrix.Rotation(roll, 4, 'Y'))
    def P(x, y, z): return tuple(Vector(loc) + (R_ @ Vector((x, y, z, 1))).to_3d())
    rot = R_.to_euler()
    box(f"{name}Block", (t - 0.004, w - 0.006, h - 0.008), P(0, 0.002, h / 2), page_mat, rot=tuple(rot))
    for sx in (-1, 1):
        box(f"{name}Board{sx}", (0.0025, w, h), P(sx * (t / 2 - 0.00125), 0.0, h / 2), cover_mat, rot=tuple(rot))
    box(f"{name}Spine", (t, 0.006, h), P(0, -w / 2 + 0.001, h / 2), cover_mat, bevel=t * 0.3, rot=tuple(rot))

def picture(name, R, w, u, zc, width, height, frame_mat, canvas_mat, depth=0.06):
    o, a, n, L = R.wall_frame(w)
    c = o + a * u + n * (depth / 2 + 0.01) + Vector((0, 0, zc))
    fw = 0.075
    for (du, dz, sw, sh) in ((0, height / 2 + fw / 2, width + 2 * fw, fw), (0, -height / 2 - fw / 2, width + 2 * fw, fw), (-width / 2 - fw / 2, 0, fw, height), (width / 2 + fw / 2, 0, fw, height)):
        box(f"{name}Frame{du}{dz}", (abs(a.x) * sw + abs(n.x) * depth, abs(a.y) * sw + abs(n.y) * depth, sh), tuple(c + a * du + Vector((0, 0, dz))), frame_mat, bevel=0.012)
    box(f"{name}Canvas", (abs(a.x) * width + abs(n.x) * 0.01, abs(a.y) * width + abs(n.y) * 0.01, height), tuple(c - n * 0.015), canvas_mat)
    # the picture hangs from a cord on the picture rail / a nail
    return c

def landscape_mat(name, seed=1, warm=0.5):
    """an oil landscape in the manner of the period (no people): a pale sky with cloud, a dark wooded middle ground,
    a lighter distance and water, under old yellowed varnish and craquelure."""
    m, nt, b = new_mat(name)
    co = node(nt, "ShaderNodeTexCoord", (-1800, 0)); g = co.outputs["Generated"]
    s = sep_xyz(nt, g, (-1600, 0))
    # vertical coordinate on the canvas: generated Z (0 bottom .. 1 top)
    v = s.outputs["Z"]; uu = math_(nt, 'ADD', s.outputs["X"], s.outputs["Y"], (-1450, -100))
    n1 = noise_(nt, g, 3.0, 6, 0.6, 1.0, (-1300, 300))
    hor = math_(nt, 'ADD', 0.42 + 0.03 * seed % 0.1, math_(nt, 'MULTIPLY', n1.outputs["Fac"], 0.15, (-1150, 300)), (-1050, 300))
    sky = mix_rgb(nt, 'MIX', maprange(nt, v, 0.4, 1.0, 0, 1, (-1100, 500)), (0.55, 0.50, 0.36, 1), (0.30, 0.36, 0.40, 1), (-900, 500))
    cl = noise_(nt, g, 5.0, 6, 0.6, 0.5, (-1300, 700))
    sky = mix_rgb(nt, 'MIX', maprange(nt, cl.outputs["Fac"], 0.5, 0.65, 0, 0.6, (-1100, 700)), sky, (0.65, 0.60, 0.48, 1), (-750, 500))
    land = mix_rgb(nt, 'MIX', maprange(nt, n1.outputs["Fac"], 0.35, 0.65, 0, 1, (-1100, 100)), (0.05, 0.06, 0.03, 1), (0.16, 0.15, 0.08, 1), (-900, 100))
    trees = noise_(nt, g, 9.0, 6, 0.65, 0.3, (-1300, -200))
    treeline = math_(nt, 'ADD', hor, math_(nt, 'MULTIPLY', maprange(nt, trees.outputs["Fac"], 0.45, 0.7, 0, 1, (-1100, -200)), maprange(nt, uu, 0.2, 0.9, 0.35, 0.02, (-1100, -350)), (-950, -250)), (-850, -250))
    is_land = maprange(nt, math_(nt, 'SUBTRACT', treeline, v, (-750, -250)), 0.0, 0.01, 0, 1, (-650, -250))
    col = mix_rgb(nt, 'MIX', is_land, sky, land, (-500, 300))
    water = math_(nt, 'MULTIPLY', maprange(nt, v, 0.12, 0.2, 1, 0, (-750, -500)), maprange(nt, uu, 0.6, 0.9, 0, 1, (-750, -650)), (-600, -550))
    col = mix_rgb(nt, 'MIX', water, col, (0.32, 0.34, 0.30, 1), (-350, 300))
    varnish = (0.85, 0.72, 0.45, 1)
    col = mix_rgb(nt, 'MULTIPLY', 0.55, col, varnish, (-200, 300))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.32
    cr = voronoi_(nt, g, 60.0, 'DISTANCE_TO_EDGE', (-900, -900))
    bump_from(nt, b, maprange(nt, cr.outputs["Distance"], 0.0, 0.05, 0, 1, (-600, -900)), 0.15, 0.0005)
    return m
