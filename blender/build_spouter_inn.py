"""
Fable: the Spouter-Inn, New Bedford, on a December night (Moby-Dick, chapter 3, "The Spouter-Inn").

"Entering that gable-ended Spouter-Inn, you found yourself in a wide, low, straggling entry with old-fashioned
wainscots, reminding one of the bulwarks of some condemned old craft. On one side hung a very large oil-painting so
thoroughly besmoked, and every way defaced, that in the unequal cross-lights by which you viewed it, it was only by
diligent study ... that you could anyway arrive at an understanding of its purpose."
"The opposite wall of this entry was hung all over with a heathenish array of monstrous clubs and spears. Some were
thickly set with glittering teeth resembling ivory saws; others were tufted with knots of human hair; and one was
sickle-shaped ... Mixed with these were rusty old whaling lances and harpoons all broken and deformed."
"Crossing this dusky entry, and on through yon low-arched way - cut through what in old times must have been a great
central chimney with fireplaces all round - you enter the public room. A still duskier place is this, with such low
ponderous beams above, and such old wrinkled planks beneath ... On one side stood a long, low, shelf-like table
covered with cracked glass cases, filled with dusty rarities ... Projecting from the further angle of the room stands
a dark-looking den - the bar - a rude attempt at a right whale's head. ... there stands the vast arched bone of the
whale's jaw ... Within are shabby shelves, ranged round with old decanters, bottles, flasks"
"... throwing them into the great stove in the middle of the room"

No people. About nine o'clock on a bitter, windy December night. The reader stands in the entry, just inside the
front door, facing the low arch through the old central chimney (Blender -Y). To the left hangs the smoke-blackened
painting (the foundering Cape-Horner and the leaping whale, painted procedurally into a texture by this script), to
the right the wall of South Sea clubs and spears, the rusty lances and harpoons, and an old carved settle under them.
Behind: the front door, the little window at the back of the entry, a tall clock. Through the wide, low arch: the
duskier public room, its great iron box stove burning with its door open, the bar built into a right whale's jaw in
the far corner, the long table of cracked glass cases, a table with two tallow candles.

Everything is procedural (no downloaded models, textures or HDRIs). Shared helpers: blender/mobydick_kit.py.

Node names Unity relies on:
  anchor.reader.entrance (feet, z=0), anchor.reader.look (eye height, 1 m ahead), anchor.scene.centre (the arch),
  anchor.inn.painting, anchor.inn.clubs, anchor.inn.stove, anchor.inn.bar
  Lamp.* POINT lights (FableBuild's indoor block bakes lights whose names start with "Lamp")
  fx.fire.stove (the stove's fire, radius 0.16), fx.lantern.entry, fx.lantern.bar, fx.candle.table1/2, fx.candle.door
  sound.fire.stove, sound.wind.door (the draught under the front door and window), sound.crowd.kitchen (muffled
  voices behind the public room's back door), sound.clock.entry
  MESH_* static meshes merged by material; glass materials contain "Glass" (FableBuild makes them transparent).

Register as indoor (Outdoor = false): no sun or sky; FableBuild zeroes lights whose names do not start with "Lamp".

Axes: metres, Blender +Z up, the reader at the world origin facing -Y. The entry spans x -2.2..2.2, y -2.2..3.6
(ceiling 2.25 m); the chimney y -3.1..-2.2 with the arch x -2.0..1.2; the public room x -4.4..3.8, y -11.2..-3.1.

Run headless:
  blender -b -P blender/build_spouter_inn.py -- --out out/spouter-inn --render --quick --res 900
  blender -b -P blender/build_spouter_inn.py -- --out out/spouter-inn --render --samples 96 --res 1400
  blender -b -P blender/build_spouter_inn.py -- --out out/spouter-inn --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, Euler, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mobydick_kit import *
import numpy as np

args = parse_args("out/spouter-inn")
scene, COLL = reset_scene("SpouterInn", args)
random.seed(1851)
SID = "spouter-inn"

EYE = 1.55
EX0, EX1, EY0, EY1, ECEIL = -2.2, 2.2, -2.2, 3.6, 2.25         # the entry
CY0, CY1 = -3.1, -2.2                                         # the chimney (y)
AX0, AX1, A_SPRING, A_CROWN = -2.0, 1.2, 1.48, 1.95           # the low arch through it
PX0, PX1, PY0, PY1, PCEIL = -4.4, 3.8, -11.2, -3.1, 2.40      # the public room
WALL_T = 0.16
STOVE = Vector((-2.3, -5.9, 0.0))
BAR_C = Vector((-3.2, -9.0, 0.0))                             # the jaw's foot line centre (front of the den)

# ============================================================================= painting texture (numpy)
def fbm(h, w, octaves, seed, base=4):
    rng = np.random.default_rng(seed); out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        gh, gw = base * 2 ** o + 1, int(base * 2 ** o * w / h) + 1
        g = rng.random((gh, gw)).astype(np.float32)
        ys = np.linspace(0, gh - 1, h); xs = np.linspace(0, gw - 1, w)
        y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
        y1 = np.minimum(y0 + 1, gh - 1); x1 = np.minimum(x0 + 1, gw - 1)
        fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
        fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
        a = g[y0][:, x0]; b = g[y0][:, x1]; c = g[y1][:, x0]; d = g[y1][:, x1]
        out += amp * (a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy)
        tot += amp; amp *= 0.55
    return out / tot

def blur(a, r):
    """Separable box blur, three passes (about Gaussian), radius r pixels, edges clamped."""
    for _ in range(3):
        for ax in (0, 1):
            pad = [(0, 0)] * a.ndim; pad[ax] = (r + 1, r)
            c = np.cumsum(np.pad(a, pad, mode='edge'), axis=ax)
            n = a.shape[ax]
            a = (np.take(c, range(2 * r + 1, 2 * r + 1 + n), axis=ax) - np.take(c, range(0, n), axis=ax)) / (2 * r + 1)
    return a

def soft_seg(u, v, a, b_, w, asp):
    """Soft mask of a stroke from a to b (u, v in 0..1, asp = W/H), half-width w (in v units)."""
    ax, ay = a; bx, by = b_
    px, py = (u - ax) * asp, v - ay; dx, dy = (bx - ax) * asp, by - ay
    t = np.clip((px * dx + py * dy) / (dx * dx + dy * dy), 0, 1)
    d = np.sqrt((px - t * dx) ** 2 + (py - t * dy) ** 2)
    return np.clip(1 - d / w, 0, 1)

def painting_image(W=1024, H=640):
    """"Chaos bewitched": a half-foundered ship weltering in a great hurricane off Cape Horn, three dismantled masts
    alone visible; an exasperated whale purposing to spring clean over the craft, in the enormous act of impaling
    himself upon the three mast-heads. Painted soft, as though through smoke; then besmoked, varnish gone brown, crazed."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = xx / W; v = yy / H                      # Blender image rows start at the bottom: v is up
    asp = W / H
    n1 = fbm(H, W, 6, 11); n2 = fbm(H, W, 5, 23, 3); n3 = fbm(H, W, 7, 37, 6); n4 = fbm(H, W, 4, 41, 2)
    horizon = 0.42 + 0.07 * (n2 - 0.5) + 0.04 * np.sin(u * 7.0 + 1.0)
    sky_t = np.clip((v - horizon) / (1 - horizon), 0, 1)
    rent = np.exp(-(((u - 0.24) / 0.17) ** 2 + ((v - 0.80) / 0.11) ** 2)) * (0.5 + 0.9 * n1)
    sky = np.stack([0.17 + 0.12 * n1, 0.16 + 0.11 * n1, 0.12 + 0.08 * n1], -1) * (1.0 - 0.45 * sky_t[..., None])
    sky += rent[..., None] * np.array([0.42, 0.38, 0.27])
    # driving scud: dark diagonal streaks of cloud
    scud = np.clip((fbm(H, W, 5, 61, 3) - 0.5) * 3 + np.sin((u * 3 - v * 2) * 6) * 0.2, 0, 1)
    sky *= (1 - 0.35 * scud)[..., None]
    sea = np.stack([0.05 + 0.06 * n3, 0.07 + 0.07 * n3, 0.055 + 0.05 * n3], -1)
    crests = np.clip((n3 - 0.6) * 4.0, 0, 1) * np.clip(1 - np.abs(v - horizon + 0.15) * 2.5, 0, 1)
    sea += crests[..., None] * np.array([0.30, 0.30, 0.24])
    img = np.where((v > horizon)[..., None], sky, sea)
    img = blur(img, 3)
    # the ship: a heeled, half-sunk black hull just above the waterline at centre, three dismantled masts
    hull = np.zeros((H, W), np.float32)
    for t in np.linspace(0, 1, 9):
        hx = 0.36 + 0.24 * t; hy = 0.36 + 0.07 * t - 0.05 * np.sin(np.pi * t)
        hull = np.maximum(hull, soft_seg(u, v, (hx - 0.02, hy), (hx + 0.02, hy + 0.004), 0.035 - 0.02 * abs(t - 0.45), asp))
    masts = np.zeros((H, W), np.float32)
    tips = []
    for (bx, by, tx, ty) in ((0.41, 0.36, 0.38, 0.62), (0.48, 0.37, 0.475, 0.70), (0.55, 0.39, 0.585, 0.60)):
        masts = np.maximum(masts, soft_seg(u, v, (bx, by), (tx, ty), 0.006, asp))
        masts = np.maximum(masts, soft_seg(u, v, (bx - 0.03, by + (ty - by) * 0.55), (bx + 0.035, by + (ty - by) * 0.62), 0.004, asp) * 0.8)
        tips.append((tx, ty))
    # the whale: a long, limber, portentous black mass arched over the mast-heads, blunt head down at the right
    whale = np.zeros((H, W), np.float32)
    pts = [(0.27, 0.62), (0.35, 0.71), (0.45, 0.75), (0.55, 0.73), (0.64, 0.66), (0.70, 0.57)]
    wid = [0.012, 0.03, 0.05, 0.062, 0.07, 0.066]
    for (a, b_), (wa, wb) in zip(zip(pts, pts[1:]), zip(wid, wid[1:])):
        for k in range(4):
            f = k / 4
            pa = (a[0] + (b_[0] - a[0]) * f, a[1] + (b_[1] - a[1]) * f); pb = (a[0] + (b_[0] - a[0]) * (f + 0.25), a[1] + (b_[1] - a[1]) * (f + 0.25))
            whale = np.maximum(whale, soft_seg(u, v, pa, pb, wa + (wb - wa) * f, asp) ** 0.5)
    whale = np.maximum(whale, soft_seg(u, v, (0.21, 0.66), (0.27, 0.62), 0.016, asp) ** 0.5)       # the flukes
    whale = np.maximum(whale, soft_seg(u, v, (0.24, 0.56), (0.27, 0.62), 0.014, asp) ** 0.5)
    spout = np.exp(-(((u - 0.74) / 0.03) ** 2 + ((v - 0.62) / 0.05) ** 2)) * 0.5
    dark = np.array([0.02, 0.018, 0.016])
    for mask, k in ((hull, 0.85), (masts, 0.8), (whale, 0.9)):
        mk = blur(mask, 2)[..., None]
        img = img * (1 - mk * k) + dark * mk * k
    img += spout[..., None] * np.array([0.25, 0.24, 0.20])
    # brushwork: directional strokes
    strokes = blur(fbm(H, W, 3, 81, 80), 1)
    img *= (0.88 + 0.24 * strokes)[..., None]
    # besmoked: everything sinks towards brown-black, darker at the top where the smoke rose; yellow-brown varnish
    soot = 0.5 + 0.35 * n4 + 0.3 * v
    img = img * (1.3 - 0.6 * soot)[..., None]
    vign = np.clip(1 - (((u - 0.5) / 0.62) ** 2 + ((v - 0.5) / 0.58) ** 2), 0, 1) ** 0.6
    img = img * (0.35 + 0.65 * vign)[..., None]
    img = img * np.array([1.0, 0.84, 0.55]) + np.array([0.010, 0.007, 0.002])
    cr = fbm(H, W, 3, 77, 48)
    crack = np.clip(1 - np.abs(cr - 0.5) * 70, 0, 1) * 0.45
    img = img * (1 - crack)[..., None]
    weave = 0.97 + 0.03 * np.sin(xx * 1.9) * np.sin(yy * 1.9)
    img = img * weave[..., None]
    img = np.clip(img * 2.0, 0, 1) ** 1.05
    rgba = np.concatenate([img, np.ones((H, W, 1), np.float32)], -1)
    img = image_from_array("IMG_SpouterPainting", rgba)
    try:
        img.filepath_raw = os.path.join(S["out"], "painting_texture.png"); img.file_format = 'PNG'; img.save(); img.pack()
    except Exception as e: print("painting save:", e)
    return img

# ============================================================================= materials
def plaster_mat(name="M_Plaster"):
    """Old lime plaster, yellowed and smoke-stained: darker towards the ceiling and above the lamps, streaks."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    n = noise_tex(nt, mp.outputs["Vector"], 1.6, 8, 0.6, 0.3, (-1000, 300))
    r = ramp(nt, [(0.3, (0.30, 0.26, 0.185, 1)), (0.55, (0.37, 0.32, 0.235, 1)), (0.8, (0.43, 0.38, 0.28, 1))], (-700, 300))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    z = world_z(nt)
    smoke = map_range(nt, z, 1.1, 2.3, 0.05, 0.62, (-800, -100))
    sn = noise_tex(nt, mp.outputs["Vector"], 0.7, 4, 0.5, 0.6, (-1000, -300))
    smoke = math_n(nt, 'MULTIPLY', smoke, map_range(nt, sn.outputs["Fac"], 0.3, 0.7, 0.6, 1.2, (-800, -300)), (-600, -200))
    col = mix_rgb(nt, r.outputs["Color"], (0.085, 0.065, 0.045, 1), smoke, 'MIX', (-400, 200))
    st = node(nt, "ShaderNodeMapping", (-1200, -600)); st.inputs["Scale"].default_value = (6.0, 6.0, 0.35)
    nt.links.new(mp.outputs["Vector"], st.inputs["Vector"])
    streak = noise_tex(nt, st.outputs["Vector"], 2.0, 3, 0.5, loc=(-1000, -600))
    col = mix_rgb(nt, col, (0.16, 0.12, 0.08, 1), map_range(nt, streak.outputs["Fac"], 0.55, 0.75, 0.0, 0.35, (-800, -600)), 'MIX', (-250, 200))
    col = ao_mult(nt, col, 0.4, (0.35, 0.32, 0.28))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.93
    fine = noise_tex(nt, mp.outputs["Vector"], 18.0, 6, 0.6, loc=(-1000, -900))
    bump_from(nt, b, mix_f(nt, n.outputs["Fac"], fine.outputs["Fac"], 0.5, (-300, -700)), 0.25, 0.01)
    return m

def brick_mat(name="M_Brick"):
    """Old soft red brick in lime mortar, soot-black round the arch and above the stove-pipe thimble."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    bt = node(nt, "ShaderNodeTexBrick", (-1000, 300)); bt.offset = 0.5; bt.squash = 1.0
    bt.inputs["Scale"].default_value = 1.0; bt.inputs["Mortar Size"].default_value = 0.012; bt.inputs["Brick Width"].default_value = 0.21
    bt.inputs["Row Height"].default_value = 0.068; bt.inputs["Bias"].default_value = 0.0; bt.inputs["Mortar Smooth"].default_value = 0.2
    rot = node(nt, "ShaderNodeMapping", (-1200, 300)); rot.inputs["Rotation"].default_value = (math.pi / 2, 0, 0)
    nt.links.new(mp.outputs["Vector"], rot.inputs["Vector"])
    # bricks lie in x (faces at constant y) and in y (faces at constant x): use x + y along the course
    sxyz = sep_xyz(nt, mp.outputs["Vector"], (-1400, 500))
    gn = node(nt, "ShaderNodeNewGeometry", (-1600, 700)); ns = sep_xyz(nt, gn.outputs["Normal"], (-1450, 700))
    flat = map_range(nt, math_n(nt, 'ABSOLUTE', ns.outputs["Z"], None, (-1350, 700)), 0.55, 0.75, 0.0, 1.0, (-1250, 700))
    alongc = math_n(nt, 'ADD', sxyz.outputs["X"], mix_f(nt, sxyz.outputs["Y"], 0.0, flat, (-1300, 550)), (-1250, 500))
    rows = mix_f(nt, sxyz.outputs["Z"], sxyz.outputs["Y"], flat, (-1250, 400))
    cv = node(nt, "ShaderNodeCombineXYZ", (-1100, 500)); nt.links.new(alongc, cv.inputs["X"]); nt.links.new(rows, cv.inputs["Y"])
    nt.links.new(cv.outputs["Vector"], bt.inputs["Vector"])
    bt.inputs["Color1"].default_value = (0.13, 0.052, 0.032, 1); bt.inputs["Color2"].default_value = (0.075, 0.035, 0.024, 1)
    bt.inputs["Mortar"].default_value = (0.13, 0.115, 0.095, 1)
    n = noise_tex(nt, mp.outputs["Vector"], 9.0, 6, 0.6, loc=(-1000, 0))
    pb = noise_tex(nt, cv.outputs["Vector"], 7.0, 2, 0.5, loc=(-1000, -150))       # brick-sized blotches: each brick fired differently
    vr = ramp(nt, [(0.3, (0.55, 0.55, 0.58, 1)), (0.5, (0.95, 0.9, 0.85, 1)), (0.7, (1.35, 1.2, 1.05, 1))], (-800, 0))
    nt.links.new(mix_f(nt, n.outputs["Fac"], pb.outputs["Fac"], 0.6, (-900, -50)), vr.inputs["Fac"])
    col = mix_rgb(nt, bt.outputs["Color"], vr.outputs["Color"], 1.0, 'MULTIPLY', (-600, 300))
    z = world_z(nt)
    sn = noise_tex(nt, mp.outputs["Vector"], 1.1, 5, 0.6, 0.8, (-1000, -400))
    soot = math_n(nt, 'MULTIPLY', map_range(nt, z, 0.6, 2.2, 0.3, 0.9, (-800, -300)), map_range(nt, sn.outputs["Fac"], 0.35, 0.65, 0.5, 1.2, (-800, -450)), (-600, -350))
    col = mix_rgb(nt, col, (0.025, 0.02, 0.017, 1), soot, 'MIX', (-350, 300))
    col = ao_mult(nt, col, 0.25, (0.4, 0.38, 0.36))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(map_range(nt, bt.outputs["Fac"], 0.0, 1.0, 0.85, 0.97, (-300, -200)), b.inputs["Roughness"])
    bump_from(nt, b, math_n(nt, 'ADD', math_n(nt, 'MULTIPLY', bt.outputs["Fac"], -1.0, (-400, -600)), math_n(nt, 'MULTIPLY', n.outputs["Fac"], 0.3, (-400, -700)), (-250, -650)), 0.5, 0.008)
    return m

def bone_mat(name="M_JawBone"):
    """Old whale jawbone: grey-ivory, porous, streaked brown with years of tobacco smoke and hands."""
    m, nt, b = new_mat(name)
    mp = coords(nt, world=True)
    st = node(nt, "ShaderNodeMapping", (-1200, 200)); st.inputs["Scale"].default_value = (3.0, 3.0, 0.6)
    nt.links.new(mp.outputs["Vector"], st.inputs["Vector"])
    n = noise_tex(nt, st.outputs["Vector"], 3.0, 8, 0.65, 0.5, (-1000, 200))
    r = ramp(nt, [(0.25, (0.22, 0.19, 0.14, 1)), (0.5, (0.36, 0.32, 0.25, 1)), (0.75, (0.46, 0.42, 0.34, 1))], (-700, 200))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    pores = node(nt, "ShaderNodeTexVoronoi", (-1000, -200)); pores.inputs["Scale"].default_value = 90.0
    nt.links.new(mp.outputs["Vector"], pores.inputs["Vector"])
    pr = map_range(nt, pores.outputs["Distance"], 0.0, 0.25, 0.75, 1.0, (-800, -200))
    col = mix_rgb(nt, r.outputs["Color"], pr, 1.0, 'MULTIPLY', (-450, 200))
    col = ao_mult(nt, col, 0.3, (0.35, 0.3, 0.25))
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.62
    bump_from(nt, b, mix_f(nt, n.outputs["Fac"], pores.outputs["Distance"], 0.5, (-300, -400)), 0.35, 0.004)
    return m

def painting_mat(img, name="M_Painting"):
    m, nt, b = new_mat(name)
    t = node(nt, "ShaderNodeTexImage", (-600, 200)); t.image = img
    uv = node(nt, "ShaderNodeUVMap", (-800, 200)); nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    n = noise_tex(nt, coords(nt).outputs["Vector"], 40.0, 4, 0.6, loc=(-600, -200))
    nt.links.new(map_range(nt, n.outputs["Fac"], 0.3, 0.7, 0.55, 0.8, (-300, -200)), b.inputs["Roughness"])
    bump_from(nt, b, n.outputs["Fac"], 0.08, 0.002)
    return m

def tallow_mat(name="M_Tallow"):
    m, nt, b = new_mat(name)
    mp = coords(nt)
    n = noise_tex(nt, mp.outputs["Vector"], 20.0, 4, 0.5, loc=(-800, 0))
    r = ramp(nt, [(0.3, (0.50, 0.44, 0.30, 1)), (0.7, (0.62, 0.56, 0.40, 1))], (-500, 0)); nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.55
    b.inputs["Subsurface Weight"].default_value = 0.3; b.inputs["Subsurface Radius"].default_value = (0.4, 0.25, 0.1); b.inputs["Subsurface Scale"].default_value = 0.01
    return m

M_FLOOR = timber_mat("M_FloorPlanks", base=(0.15, 0.10, 0.06), dark=(0.045, 0.03, 0.02), light=(0.26, 0.19, 0.12), along='Y', rough=(0.45, 0.8), grime=0.6)
M_WAIN = timber_mat("M_Wainscot", base=(0.075, 0.05, 0.032), dark=(0.025, 0.017, 0.012), light=(0.14, 0.095, 0.06), along='X', rough=(0.35, 0.7), grime=0.5, seams=('Z', 0.19))
M_BEAM = timber_mat("M_Beams", base=(0.09, 0.062, 0.04), dark=(0.025, 0.018, 0.012), light=(0.16, 0.11, 0.07), along='X', rough=(0.6, 0.9), grime=0.7, scale=0.7)
M_JOIST = timber_mat("M_Joists", base=(0.10, 0.07, 0.045), dark=(0.03, 0.02, 0.014), light=(0.17, 0.12, 0.08), along='Y', rough=(0.6, 0.9), grime=0.7)
M_CEIL = timber_mat("M_CeilingBoards", base=(0.11, 0.08, 0.05), dark=(0.03, 0.022, 0.015), light=(0.17, 0.12, 0.08), along='Y', rough=(0.7, 0.9), grime=0.8)
M_FURN = timber_mat("M_Furniture", base=(0.12, 0.075, 0.042), dark=(0.035, 0.022, 0.014), light=(0.22, 0.15, 0.09), along='X', rough=(0.35, 0.65), grime=0.4, polish=0.2)
M_DOOR = timber_mat("M_DoorPlanks", base=(0.11, 0.08, 0.055), dark=(0.035, 0.025, 0.018), light=(0.19, 0.14, 0.09), along='Z', rough=(0.5, 0.85), grime=0.5)
M_CLUB = timber_mat("M_ClubWood", base=(0.05, 0.03, 0.018), dark=(0.012, 0.008, 0.006), light=(0.12, 0.07, 0.04), along='Z', rough=(0.3, 0.55), grime=0.3, polish=0.3, scale=2.0)
M_PLASTER = plaster_mat()
M_BRICK = brick_mat()
M_BONE = bone_mat()
M_IRON = iron_mat("M_CastIron", rust=0.04)
M_RUST = iron_mat("M_RustyIron", rust=0.9, base=(0.05, 0.035, 0.025), rough=(0.6, 0.9))
M_TEETH = noisy("M_Teeth", [(0.42, 0.39, 0.31), (0.55, 0.52, 0.43), (0.62, 0.59, 0.50)], scale=30, rough=0.45, bump=0.1)
M_HAIR = noisy("M_Hair", [(0.012, 0.010, 0.009), (0.03, 0.024, 0.02), (0.05, 0.04, 0.032)], scale=40, rough=0.8, bump=0.6, bump_dist=0.004, stretch=(1, 1, 8), sheen=0.5)
M_FRAME = noisy("M_PaintingFrame", [(0.035, 0.026, 0.015), (0.075, 0.055, 0.025), (0.14, 0.10, 0.045)], scale=14, rough=0.5, bump=0.2, metallic=0.0, ao=(0.05, (0.3, 0.3, 0.3)))
M_PAINT = painting_mat(painting_image())
M_BOTTLE = glass_mat("M_BottleGlass", tint=(0.12, 0.22, 0.10), rough=0.08, dirt=0.25)
M_GREENGLASS = glass_mat("M_TumblerGlass", tint=(0.35, 0.48, 0.30), rough=0.06, dirt=0.2)
M_CASEGLASS = glass_mat("M_CaseGlass", tint=(0.7, 0.72, 0.66), rough=0.12, dirt=0.4)
M_PANE = noisy("M_NightPane", [(0.004, 0.006, 0.010), (0.008, 0.011, 0.018), (0.015, 0.019, 0.028)], scale=6, rough=0.08, bump=0.15, bump_dist=0.002)
M_TALLOW = tallow_mat()
M_CURIO = noisy("M_Curios", [(0.20, 0.16, 0.11), (0.34, 0.28, 0.20), (0.50, 0.43, 0.33)], scale=14, rough=0.7, bump=0.3, world=True, ao=(0.1, (0.4, 0.4, 0.4)))
M_CORAL = noisy("M_Coral", [(0.45, 0.30, 0.22), (0.55, 0.40, 0.30), (0.62, 0.50, 0.40)], scale=30, rough=0.85, bump=0.6, bump_dist=0.002)
M_PEWTER = noisy("M_Pewter", [(0.20, 0.20, 0.19), (0.30, 0.30, 0.28), (0.40, 0.39, 0.36)], scale=20, rough=0.45, metallic=0.85, bump=0.1)
M_BRASS = noisy("M_Brass", [(0.30, 0.20, 0.07), (0.45, 0.32, 0.12), (0.55, 0.42, 0.18)], scale=12, rough=0.4, metallic=0.9, bump=0.05)
M_EMBERS = emit_mat("M_Embers", (1.0, 0.33, 0.06), 6.0)
M_HEARTH = noisy("M_Ash", [(0.04, 0.035, 0.03), (0.09, 0.08, 0.07), (0.16, 0.15, 0.13)], scale=10, rough=0.95, bump=0.5, bump_dist=0.01, world=True)
M_CLOTH = noisy("M_Oilskin", [(0.035, 0.032, 0.014), (0.06, 0.055, 0.025), (0.09, 0.08, 0.04)], scale=6, rough=0.5, bump=0.4, bump_dist=0.01, sheen=0.3, ao=(0.1, (0.3, 0.3, 0.3)))
M_LAMPGLASS = glass_mat("M_LampGlass", (0.95, 0.93, 0.88), 0.0)
M_FLAME = emit_mat("PREVIEW_FlameMat", (1.0, 0.62, 0.25), 12.0)

# ============================================================================= shell: floors, walls, ceilings, beams
def floor_planks(x0, x1, y0, y1, width, name):
    """Old wide planks along Y, each tilted and dished a little (worn, 'wrinkled'), staggered butt joints."""
    x = x0; k = 0
    while x < x1 - 0.01:
        w = min(width * random.uniform(0.8, 1.25), x1 - x)
        y = y0 - random.uniform(0, 2.0)
        while y < y1:
            L = random.uniform(2.6, 4.2); ya, yb = max(y, y0), min(y + L, y1)
            if yb - ya > 0.05:
                o = box(f"{name}{k}", (w - 0.006, yb - ya - 0.004, 0.04), (x + w / 2, (ya + yb) / 2, -0.02 + random.uniform(-0.004, 0.003)), M_FLOOR,
                        rot=(random.uniform(-0.006, 0.006), random.uniform(-0.012, 0.012), 0))
                k += 1
            y += L
        x += w

def wall(name, a, b_, z0, z1, mat, t=WALL_T, holes=()):
    """A wall face from a to b (2D points) between z0 and z1, outward thickness t, with rectangular holes
    [(s0, s1, z0, z1)] along it (s from a)."""
    a = Vector((a[0], a[1], 0)); b_ = Vector((b_[0], b_[1], 0)); L = (b_ - a).length; d = (b_ - a) / L
    nrm = Vector((-d.y, d.x, 0))          # the room side (walls are given anticlockwise round the room)
    cuts = sorted(holes); segs = []
    s = 0.0
    for (h0, h1, hz0, hz1) in cuts:
        if h0 > s: segs.append((s, h0, z0, z1))
        if hz0 > z0: segs.append((h0, h1, z0, hz0))
        if hz1 < z1: segs.append((h0, h1, hz1, z1))
        s = h1
    if s < L: segs.append((s, L, z0, z1))
    out = []
    for i, (s0, s1, za, zb) in enumerate(segs):
        c = a + d * ((s0 + s1) / 2) - nrm * (t / 2)
        o = box(f"{name}{i}", (s1 - s0, t, zb - za), (c.x, c.y, (za + zb) / 2), mat, rot=(0, 0, math.atan2(d.y, d.x)))
        out.append(o)
    return out

def wainscot(name, a, b_, h=0.95, holes=()):
    """Bulwark-like wainscot: overlapping horizontal boards leaning back a touch, a heavy cap rail and a base board."""
    a = Vector((a[0], a[1], 0)); b_ = Vector((b_[0], b_[1], 0)); L = (b_ - a).length; d = (b_ - a) / L
    nrm = Vector((-d.y, d.x, 0)); yaw = math.atan2(d.y, d.x)
    spans = []; s = 0.0
    for (h0, h1) in sorted(holes):
        if h0 > s: spans.append((s, h0))
        s = h1
    if s < L: spans.append((s, L))
    k = 0
    for (s0, s1) in spans:
        if s1 - s0 < 0.05: continue
        z = 0.0; nb = 5
        for j in range(nb):
            bh = h / nb
            c = a + d * ((s0 + s1) / 2) + nrm * (0.022 + 0.004 * (nb - j))
            box(f"{name}B{k}", (s1 - s0, 0.024, bh + 0.02), (c.x, c.y, z + bh / 2 + 0.01), M_WAIN, rot=(-0.03, 0, yaw), bevel=0.004)
            k += 1; z += bh
        c = a + d * ((s0 + s1) / 2) + nrm * 0.045
        box(f"{name}Cap{k}", (s1 - s0, 0.085, 0.05), (c.x, c.y, h + 0.03), M_WAIN, rot=(0, 0, yaw), bevel=0.01)
        c = a + d * ((s0 + s1) / 2) + nrm * 0.035
        box(f"{name}Base{k}", (s1 - s0, 0.03, 0.12), (c.x, c.y, 0.06), M_WAIN, rot=(0, 0, yaw), bevel=0.004)

def beams_and_ceiling(x0, x1, y0, y1, ceil, beam_ys, beam_under, name, joist_pitch=0.62):
    for k, by in enumerate(beam_ys):
        bw, bd = random.uniform(0.25, 0.30), ceil - beam_under
        o = box(f"{name}Beam{k}", (x1 - x0, bw, bd), ((x0 + x1) / 2, by, beam_under + bd / 2), M_BEAM, bevel=0.025,
                rot=(random.uniform(-0.01, 0.01), 0, random.uniform(-0.004, 0.004)))
    # joists along Y between the beams, ceiling boards above
    jx = x0 + joist_pitch / 2; k = 0
    while jx < x1:
        box(f"{name}Joist{k}", (0.11, y1 - y0, 0.15), (jx, (y0 + y1) / 2, ceil - 0.075), M_JOIST, bevel=0.01, rot=(0, random.uniform(-0.004, 0.004), 0))
        jx += joist_pitch * random.uniform(0.9, 1.1); k += 1
    x = x0; k = 0
    while x < x1 - 0.01:
        w = min(random.uniform(0.22, 0.34), x1 - x)
        box(f"{name}Board{k}", (w - 0.004, y1 - y0, 0.03), (x + w / 2, (y0 + y1) / 2, ceil + 0.015), M_CEIL)
        x += w; k += 1

# --- the entry
floor_planks(EX0, EX1, EY0 - 0.2, EY1, 0.30, "EntryPlank")
DOOR_X0, DOOR_X1, DOOR_H = -0.15, 0.85, 1.92
WIN_X0, WIN_X1, WIN_Z0, WIN_Z1 = -1.75, -1.05, 1.02, 1.72
wall("EntryWallBack", (EX1, EY1), (EX0, EY1), 0, ECEIL, M_PLASTER, holes=[(EX1 - DOOR_X1, EX1 - DOOR_X0, 0, DOOR_H), (EX1 - WIN_X1, EX1 - WIN_X0, WIN_Z0, WIN_Z1)])
wall("EntryWallLeft", (EX1, EY0), (EX1, EY1), 0, ECEIL, M_PLASTER)
wall("EntryWallRight", (EX0, EY1), (EX0, EY0), 0, ECEIL, M_PLASTER)
wainscot("WainL", (EX1, EY0), (EX1, EY1))
wainscot("WainR", (EX0, EY1), (EX0, EY0))
wainscot("WainBack", (EX1, EY1), (EX0, EY1), holes=[(EX1 - DOOR_X1 - 0.08, EX1 - DOOR_X0 + 0.08)])
beams_and_ceiling(EX0, EX1, EY0, EY1, ECEIL, [-1.95, 1.45], 1.97, "Entry")

# --- the chimney with the low arch (entry face y = CY1, public-room face y = CY0)
def arch_z(x):
    """A low segmental arch between AX0 and AX1."""
    c = (AX0 + AX1) / 2; hw = (AX1 - AX0) / 2; rise = A_CROWN - A_SPRING
    R = (hw * hw + rise * rise) / (2 * rise); zc = A_CROWN - R
    return zc + math.sqrt(max(0.0, R * R - (x - c) ** 2))

def chimney_face(name, y, x0, x1, top, facing):
    """A brick face at y from x0..x1 up to top, with the arch cut out; facing = +1 (normal +Y) or -1."""
    N = 24; verts = []; faces = []
    segs = [[(x0, 0.0), (AX0, 0.0)], [(lerp(AX0, AX1, i / N), arch_z(lerp(AX0, AX1, i / N))) for i in range(N + 1)], [(AX1, 0.0), (x1, 0.0)]]
    for seg in segs:
        base = len(verts)
        for (x, zb) in seg: verts.append((x, y, zb)); verts.append((x, y, top))
        for i in range(len(seg) - 1):
            a, b2 = base + 2 * i, base + 2 * (i + 1)
            faces.append((a, a + 1, b2 + 1, b2) if facing > 0 else (a, b2, b2 + 1, a + 1))
    return mesh_from(name, verts, faces, M_BRICK, smooth=False)

def arch_reveal(name):
    """The soffit and the two reveals of the passage, from the entry face to the public-room face."""
    N = 24; verts = []; faces = []
    pts = [(AX0, 0.0)] + [(lerp(AX0, AX1, i / N), arch_z(lerp(AX0, AX1, i / N))) for i in range(N + 1)] + [(AX1, 0.0)]
    pts[1] = (AX0, A_SPRING); pts[-2] = (AX1, A_SPRING)
    for (x, z) in pts:
        verts.append((x, CY1, z)); verts.append((x, CY0, z))
    for i in range(len(pts) - 1):
        a, b2 = 2 * i, 2 * (i + 1)
        faces.append((a, b2, b2 + 1, a + 1))
    return mesh_from(name, verts, faces, M_BRICK, smooth=False)

chimney_face("ChimneyEntryFace", CY1, EX0, EX1, ECEIL + 0.02, +1)
chimney_face("ChimneyRoomFace", CY0, -3.0, 2.2, PCEIL + 0.02, -1)
arch_reveal("ArchReveal")
# a worn stone threshold under the arch, and the arch's old timber lintel-ring of soot
box("ArchSill", (AX1 - AX0 + 0.1, CY1 - CY0 + 0.06, 0.05), ((AX0 + AX1) / 2, (CY0 + CY1) / 2, 0.005), noisy("M_SillStone", [(0.12, 0.115, 0.10), (0.20, 0.19, 0.17), (0.26, 0.25, 0.22)], scale=5, rough=0.7, bump=0.3, world=True), bevel=0.012)
# the bricked-up old fireplace on the public-room face, right of the arch (its arch of headers, the infill darker)
for i in range(9):
    a = math.pi * (i + 0.5) / 9
    box(f"OldFireHeader{i}", (0.07, 0.03, 0.10), (-2.55 + 0.32 * math.cos(a), CY0 - 0.012, 1.0 + 0.22 * math.sin(a)), M_BRICK, rot=(0, -(a - math.pi / 2), 0))

# partition walls each side of the chimney in the public room, and the room's other walls
PWIN = [(-5.9, -4.9), (-8.9, -8.0)]                      # windows in the right wall (y ranges)
wall("RoomWallBackL", (PX1, PY1), (2.2, PY1), 0, PCEIL, M_PLASTER)
wall("RoomWallBackR", (-3.0, PY1), (PX0, PY1), 0, PCEIL, M_PLASTER)
wall("RoomWallLeft", (PX1, PY0), (PX1, PY1), 0, PCEIL, M_PLASTER)
wall("RoomWallRight", (PX0, PY1), (PX0, PY0), 0, PCEIL, M_PLASTER, holes=[(PY1 - yb, PY1 - ya, 0.95, 1.85) for (ya, yb) in PWIN])
KDOOR = (0.2, 1.15)
wall("RoomWallFar", (PX0, PY0), (PX1, PY0), 0, PCEIL, M_PLASTER, holes=[(KDOOR[0] - PX0, KDOOR[1] - PX0, 0, 1.9)])
floor_planks(PX0, PX1, PY0, PY1 + 0.05, 0.32, "RoomPlank")
box("ArchFloor", (AX1 - AX0, CY1 - CY0, 0.04), ((AX0 + AX1) / 2, (CY0 + CY1) / 2, -0.02), M_FLOOR)
wainscot("PWainL", (PX1, PY0), (PX1, PY1), h=0.85)
wainscot("PWainR", (PX0, PY1), (PX0, PY0), h=0.85)
wainscot("PWainFar", (PX0, PY0), (PX1, PY0), h=0.85, holes=[(KDOOR[0] - PX0 - 0.06, KDOOR[1] - PX0 + 0.06)])
beams_and_ceiling(PX0, PX1, PY0, PY1, PCEIL, [-4.6, -7.0, -9.5], 2.02, "Room", joist_pitch=0.66)
# the great summer beam along the room, resting on the chimney
box("SummerBeam", (0.34, PY1 - PY0, 0.30), (-0.4, (PY0 + PY1) / 2, 2.02 + 0.15), M_BEAM, bevel=0.03)

# ============================================================================= doors and windows
def plank_door(name, x0, x1, y, h, swing=0.0, facing=1):
    w = x1 - x0; n = 4
    hinge = Vector((x0, y, 0))
    parts = []
    for i in range(n):
        parts.append(box(f"{name}P{i}", (w / n - 0.004, 0.045, h - 0.01), (x0 + (i + 0.5) * w / n, y, h / 2), M_DOOR, bevel=0.004))
    for zb in (0.25, h - 0.3):
        parts.append(box(f"{name}Ledge{zb:.1f}", (w - 0.08, 0.03, 0.12), ((x0 + x1) / 2, y + 0.035 * facing, zb), M_DOOR, bevel=0.006))
        parts.append(box(f"{name}Strap{zb:.1f}", (w * 0.7, 0.008, 0.045), (x0 + w * 0.35, y - 0.027 * facing, zb), M_RUST))
    parts.append(box(f"{name}Latch", (0.14, 0.02, 0.025), (x1 - 0.12, y - 0.03 * facing, h * 0.52), M_RUST))
    # frame
    box(f"{name}JambL", (0.09, 0.2, h + 0.08), (x0 - 0.045, y, (h + 0.08) / 2), M_WAIN)
    box(f"{name}JambR", (0.09, 0.2, h + 0.08), (x1 + 0.045, y, (h + 0.08) / 2), M_WAIN)
    box(f"{name}Head", (w + 0.18, 0.2, 0.1), ((x0 + x1) / 2, y, h + 0.05), M_WAIN)
    return parts

def window(name, x0, x1, z0, z1, y=None, x=None, rows=3, cols=2):
    """A small sash window with small panes (night: dark glass, a little snow on the outer sill)."""
    along_x = y is not None
    w = x1 - x0; h = z1 - z0
    def P(s, z, off=0.0):
        return ((x0 + s, y + off, z) if along_x else (x + off, x0 + s, z))
    rot = (0, 0, 0) if along_x else (0, 0, math.pi / 2)
    c = P(w / 2, (z0 + z1) / 2)
    box(f"{name}Pane", (w, 0.01, h), c, M_PANE, rot=rot)
    for i in range(cols + 1):
        box(f"{name}Stile{i}", (0.035 if 0 < i < cols else 0.06, 0.05, h), P(w * i / cols, (z0 + z1) / 2), M_WAIN, rot=rot)
    for j in range(rows + 1):
        box(f"{name}Rail{j}", (w, 0.05, 0.035 if 0 < j < rows else 0.06), P(w / 2, z0 + h * j / rows), M_WAIN, rot=rot)
    box(f"{name}Sill", (w + 0.16, 0.16, 0.04), P(w / 2, z0 - 0.03, 0.0), M_WAIN, rot=rot)

plank_door("FrontDoor", DOOR_X0, DOOR_X1, EY1 - 0.05, DOOR_H, facing=-1)
window("EntryWindow", WIN_X0, WIN_X1, WIN_Z0, WIN_Z1, y=EY1 - 0.06)
for k, (ya, yb) in enumerate(PWIN):
    window(f"RoomWindow{k}", yb, ya, 0.95, 1.85, x=PX0 + 0.06, rows=3, cols=2)
plank_door("KitchenDoor", KDOOR[0], KDOOR[1], PY0 + 0.05, 1.88, facing=1)

# ============================================================================= the painting (left wall of the entry)
PAINT_C = Vector((EX1 - 0.015, -0.35, 1.58)); PW_, PH_ = 2.55, 1.05
def painting():
    me = bpy.data.meshes.new("Painting")
    hw, hh = PW_ / 2, PH_ / 2
    verts = [(PAINT_C.x - 0.03, PAINT_C.y + hw, PAINT_C.z - hh), (PAINT_C.x - 0.03, PAINT_C.y - hw, PAINT_C.z - hh),
             (PAINT_C.x - 0.03, PAINT_C.y - hw, PAINT_C.z + hh), (PAINT_C.x - 0.03, PAINT_C.y + hw, PAINT_C.z + hh)]
    me.from_pydata(verts, [], [(0, 1, 2, 3)]); me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for li, loop in enumerate(me.loops): uvl.data[li].uv = [(0, 0), (1, 0), (1, 1), (0, 1)][loop.vertex_index]
    o = bpy.data.objects.new("Painting", me); me.materials.append(M_PAINT); link(o)
    # the frame: a heavy, once-gilt moulding gone black
    fw = 0.11
    for (cy, cz, sy, sz) in ((PAINT_C.y, PAINT_C.z + hh + fw / 2, PW_ + 2 * fw, fw), (PAINT_C.y, PAINT_C.z - hh - fw / 2, PW_ + 2 * fw, fw),
                             (PAINT_C.y + hw + fw / 2, PAINT_C.z, fw, PH_), (PAINT_C.y - hw - fw / 2, PAINT_C.z, fw, PH_)):
        box("PaintFrame", (0.06, sy, sz), (PAINT_C.x - 0.03, cy, cz), M_FRAME, bevel=0.018)
    return o
painting()
anchor("inn.painting", tuple(PAINT_C))

# ============================================================================= the heathenish array (right wall of the entry)
CLUB_X = EX0 + 0.05
def club_on_wall(name, y, z, length, angle, kind, rng):
    """A club or spear hung flat on the wall: angle in the wall plane (0 = up)."""
    d = Vector((0, -math.sin(angle), math.cos(angle))); base = Vector((CLUB_X + 0.03 + rng.uniform(0, 0.03), y, z))
    tip = base + d * length
    if kind == "spear":
        tube(name, [base, base + d * length * 0.5, tip - d * 0.25], (0.026, 0.02), M_CLUB, sides=6, n=2)
        head = tube(name + "Head", [tip - d * 0.30, tip - d * 0.12, tip], (0.05, 0.002), M_CLUB, sides=4, n=2)
        if rng.random() < 0.5:   # barbs of shark's teeth along the head
            side = Vector((0, d.z, -d.y))
            for k in range(6):
                p = tip - d * (0.26 - k * 0.035)
                for sgn in (-1, 1):
                    o = cyl(f"{name}Tooth{k}{sgn}", 0.008, 0.035, tuple(p + side * sgn * 0.03), M_TEETH, verts=4, r2=0.0005, smooth=False)
                    o.rotation_euler = (side * sgn).to_track_quat('Z', 'X').to_euler()
    elif kind == "saw":
        # a flat paddle-club thickly set along both edges with teeth "resembling ivory saws"
        pts = [base, base + d * length * 0.45, base + d * length * 0.8, tip]
        tube(name, pts, [0.03] * 2 + [0.05] * 4 + [0.07] * 4 + [0.055] * 3 + [0.025], M_CLUB, sides=6, n=4)
        side = Vector((0, d.z, -d.y))
        for k in range(20):
            t = 0.42 + k * 0.028
            p = base + d * length * t
            wdt = 0.07 if t > 0.6 else 0.05
            for sgn in (-1, 1):
                q = p + side * sgn * (wdt + 0.012)
                o = cyl(f"{name}T{k}{sgn}", 0.009, 0.032, tuple(q), M_TEETH, verts=4, r2=0.001, smooth=False)
                o.rotation_euler = (side * sgn).to_track_quat('Z', 'X').to_euler()
    elif kind == "knob":
        tube(name, [base, base + d * length * 0.6, tip - d * 0.08], (0.032, 0.05), M_CLUB, sides=7, n=2)
        blob(name + "Knob", tuple(tip - d * 0.08), 0.115, M_CLUB, scale=(0.85, 1, 1.15), subdiv=2, amp=0.38, freq=4.5, seed=rng.random() * 9)
        if rng.random() < 0.6:   # tufted with knots of hair
            for k in range(3):
                blob(f"{name}Hair{k}", tuple(base + d * length * (0.55 + 0.04 * k) + Vector((0.02, 0, 0))), 0.035, M_HAIR,
                     scale=(0.6, 0.8, 2.2), subdiv=1, amp=0.4, seed=k * 3.1 + rng.random())
    elif kind == "paddle":
        tube(name, [base, base + d * length * 0.55], (0.03, 0.034), M_CLUB, sides=6, n=2)
        blade = blob(name + "Blade", tuple(base + d * length * 0.76), 0.27, M_CLUB, scale=(0.12, 0.55, 1.0), subdiv=2, amp=0.05, seed=rng.random())
        blade.rotation_euler = (angle, 0, 0)
    elif kind == "sickle":
        # "one was sickle-shaped, with a vast handle sweeping round like the segment made in the new-mown grass"
        pts = [base + d * length * t + Vector((0, 0, 0)) + Vector((0, math.cos(angle), math.sin(angle))) * (0.55 * math.sin(math.pi * t) ** 1.2) * length * 0.35 for t in (0, 0.2, 0.4, 0.6, 0.8, 1.0)]
        tube(name, pts, (0.03, 0.014), M_CLUB, sides=6, n=4)
        tube(name + "Blade", [pts[-2], pts[-1], pts[-1] + Vector((0, -0.16, -0.2))], (0.06, 0.004), M_CLUB, sides=4, n=3)

def harpoon(name, base, d, length, bend=0.0, broken=False):
    d = Vector(d).normalized(); side = Vector((0, d.z, -d.y))
    shank_end = base + d * (length * (0.6 if broken else 1.0))
    mid = base + d * length * 0.3 + side * bend
    tube(name, [base, mid, shank_end], (0.011, 0.009), M_RUST, sides=5, n=3)
    if not broken:
        h = shank_end
        tube(name + "Head", [h, h + d * 0.07 + side * 0.05, h + d * 0.16], (0.012, 0.003), M_RUST, sides=4, n=2)
        tube(name + "Barb", [h + d * 0.16, h + d * 0.06 - side * 0.05], (0.010, 0.003), M_RUST, sides=4, n=1)
    # the wooden pole socket stub
    tube(name + "Pole", [base - d * 0.55, base], (0.026, 0.024), M_CLUB, sides=6, n=1)

def heathenish_array():
    rng = random.Random(7)
    # a sunburst of clubs and spears, two crossed groups, paddles, the sickle; lances and harpoons mixed in
    # "hung all over": tall spears standing nearly upright, heavy clubs slanting every way, crossed pairs, paddles
    items = [(-1.85, 1.0, -0.05, 1.15, "spear"), (-1.62, 1.05, 0.38, 0.95, "knob"), (-1.48, 1.0, -0.42, 0.98, "saw"),
             (-1.25, 1.0, 0.04, 1.15, "spear"), (-1.02, 1.08, 0.55, 0.85, "paddle"), (-0.95, 1.12, -0.6, 0.8, "knob"),
             (-0.62, 1.0, 0.1, 1.12, "saw"), (-0.32, 1.02, -0.18, 1.13, "spear"), (0.02, 1.15, 0.7, 0.75, "knob"),
             (0.12, 1.0, 0.02, 1.15, "spear"), (0.36, 1.05, -0.45, 0.9, "saw"), (0.52, 1.0, 0.3, 0.98, "paddle"),
             (0.78, 1.04, -0.08, 1.12, "spear"), (-1.3, 1.62, 1.35, 0.7, "knob"), (-0.2, 1.68, -1.4, 0.65, "saw"), (0.55, 1.7, 1.5, 0.6, "knob")]
    for i, (y, z, ang, L, k) in enumerate(items):
        club_on_wall(f"Club{i}", y, z, L, ang + rng.uniform(-0.04, 0.04), k, rng)
    # a second layer hung over the first: crossed pairs and short heavy clubs filling the gaps
    more = [(-1.75, 1.35, 0.9, 0.75, "paddle"), (-1.1, 1.3, -1.0, 0.7, "knob"), (-0.48, 1.25, 0.95, 0.8, "spear"),
            (-0.05, 1.3, -0.95, 0.72, "paddle"), (0.42, 1.3, 1.05, 0.7, "saw"), (0.85, 1.4, -1.1, 0.6, "knob"),
            (-1.55, 1.75, -0.3, 0.38, "knob"), (-0.75, 1.72, 0.25, 0.4, "knob"), (0.25, 1.75, -0.2, 0.36, "knob")]
    global CLUB_X
    CLUB_X += 0.05
    for i, (y, z, ang, L, k) in enumerate(more):
        club_on_wall(f"ClubB{i}", y, z, L, ang + rng.uniform(-0.04, 0.04), k, rng)
    CLUB_X -= 0.05
    club_on_wall("Sickle", -0.5, 1.0, 1.1, 0.2, "sickle", rng)
    # horizontal lances and harpoons racked on pegs above the clubs, "all broken and deformed"
    for k, (z, bend, broken) in enumerate([(2.03, 0.0, False), (1.93, 0.05, False), (1.84, 0.0, True)]):
        y0 = 1.75 - k * 0.15
        harpoon(f"Harpoon{k}", Vector((CLUB_X + 0.06, y0, z)), (0, -1, 0.02 * (k - 1)), 2.6 - 0.4 * k, bend=bend, broken=broken)
    for y in (-1.6, 0.0, 1.5):
        cyl(f"RackPeg{y}", 0.014, 0.1, (CLUB_X + 0.05, y, 1.89), M_DOOR, verts=6, rot=(0, math.pi / 2, 0))
    # a long whaling lance leaning in the corner by the arch, its iron rusted and bent
    harpoon("LanceCorner", Vector((EX0 + 0.12, EY0 + 0.15, 0.02)), (0.02, 0.06, 1.0), 2.15, bend=0.08)
heathenish_array()
anchor("inn.clubs", (CLUB_X, 0.0, 1.5))

# ============================================================================= the settle, the clock, pegs (entry)
def settle(name, x, y0, y1, facing=1):
    """An old high-backed wooden settle, carved all over (relief panels in the back), against the wall."""
    L = y1 - y0; yc = (y0 + y1) / 2; sx = 1 if facing > 0 else -1
    box(name + "Seat", (0.46, L, 0.05), (x + sx * 0.25, yc, 0.44), M_FURN, bevel=0.01)
    box(name + "Back", (0.05, L, 1.25), (x + sx * 0.04, yc, 0.44 + 0.62), M_FURN, bevel=0.01)
    for k in range(4):
        yy = y0 + (k + 0.5) * L / 4
        hw = L / 8 - 0.06; xf = x + sx * 0.078
        # a carved round-headed arcade on each panel, a lozenge boss inside, a guilloche band below
        arc = [Vector((xf, yy - hw, 0.98))] + [Vector((xf, yy - hw * math.cos(math.pi * t / 8), 1.28 + hw * 0.9 * math.sin(math.pi * t / 8))) for t in range(9)] + [Vector((xf, yy + hw, 0.98))]
        tube(f"{name}Arcade{k}", arc, (0.014, 0.014), M_FURN, sides=5, n=2)
        blob(f"{name}Boss{k}", (xf, yy, 1.15), 0.05, M_FURN, scale=(0.4, 0.8, 1.4), subdiv=2, amp=0.25, freq=3.0, seed=k * 3.0)
        tube(f"{name}Guilloche{k}", [Vector((xf, yy - hw + i * hw / 4, 0.86 + 0.025 * math.sin(i * 1.6))) for i in range(9)], (0.011, 0.011), M_FURN, sides=5, n=3)
    for yy in (y0 + 0.03, y1 - 0.03):
        box(f"{name}End{yy:.2f}", (0.5, 0.05, 1.0), (x + sx * 0.25, yy, 0.5), M_FURN, bevel=0.01)
        tube(f"{name}Arm{yy:.2f}", [(x + sx * 0.05, yy, 0.98), (x + sx * 0.35, yy, 0.86), (x + sx * 0.5, yy, 0.72)], (0.03, 0.025), M_FURN, sides=6, n=3)
    box(name + "Apron", (0.03, L, 0.3), (x + sx * 0.47, yc, 0.27), M_FURN, bevel=0.006)
    crest = [Vector((x + sx * 0.04, y0 + L * t / 12, 1.69 + 0.05 * math.sin(math.pi * t / 12) + 0.025 * math.sin(t * 2.1))) for t in range(13)]
    tube(name + "Crest", crest, (0.035, 0.035), M_FURN, rect=(0.06, 0.1), n=2)
settle("Settle", EX0 + 0.04, 0.95, 2.85)

def tall_clock(name, x, y):
    box(name + "Base", (0.30, 0.48, 0.55), (x, y, 0.275), M_FURN, bevel=0.01)
    box(name + "Trunk", (0.24, 0.38, 1.05), (x, y, 0.55 + 0.525), M_FURN, bevel=0.008)
    box(name + "Hood", (0.30, 0.48, 0.48), (x, y, 1.6 + 0.24), M_FURN, bevel=0.01)
    box(name + "Bonnet", (0.32, 0.52, 0.08), (x, y, 2.12), M_FURN, bevel=0.015)
    cyl(name + "Dial", 0.15, 0.01, (x - 0.155, y, 1.84), noisy("M_ClockDial", [(0.32, 0.29, 0.22), (0.42, 0.38, 0.29), (0.48, 0.44, 0.34)], scale=10, rough=0.6, bump=0.05, ao=(0.04, (0.6, 0.6, 0.6))), verts=20, rot=(0, math.pi / 2, 0))
    for k in range(12):
        a = 2 * math.pi * k / 12
        box(f"{name}Tick{k}", (0.004, 0.008, 0.022), (x - 0.162, y + 0.125 * math.sin(a), 1.84 + 0.125 * math.cos(a)), M_IRON, rot=(-a, 0, 0))
    box(name + "HandH", (0.004, 0.008, 0.07), (x - 0.164, y - 0.025, 1.84 + 0.02), M_IRON, rot=(math.radians(-55), 0, 0))
    box(name + "HandM", (0.004, 0.006, 0.11), (x - 0.165, y + 0.0, 1.84 + 0.055), M_IRON, rot=(math.radians(8), 0, 0))
    torus(name + "Bezel", 0.155, 0.008, (x - 0.158, y, 1.84), M_BRASS, rot=(0, math.pi / 2, 0), seg=20, mseg=4)
CLOCK = Vector((EX1 - 0.2, 2.75, 0))
tall_clock("Clock", CLOCK.x, CLOCK.y)

# peg rail by the door with an oilskin and a sou'wester
box("PegRail", (0.05, 1.2, 0.09), (EX1 - 0.05, 1.45, 1.72), M_WAIN, bevel=0.01)
for k in range(4): cyl(f"Peg{k}", 0.014, 0.12, (EX1 - 0.12, 0.98 + k * 0.3, 1.72), M_DOOR, verts=6, rot=(0, math.pi / 2, 0))
# a coil of old rope hung on one peg, a sou'wester on another
for k in range(5):
    torus(f"RopeCoil{k}", 0.17 + 0.008 * k, 0.012, (EX1 - 0.1, 1.28 + 0.004 * k, 1.5 - 0.01 * k), noisy("M_Rope", [(0.10, 0.08, 0.05), (0.17, 0.14, 0.09), (0.24, 0.20, 0.13)], scale=40, rough=0.9, bump=0.5, bump_dist=0.002) if k == 0 else bpy.data.materials["M_Rope"], rot=(0.15 * k, math.pi / 2, 0), seg=20, mseg=5)
lathe("Souwester", [(0.0, 0.0), (0.16, 0.0), (0.17, 0.015), (0.10, 0.03), (0.085, 0.12), (0.0, 0.13)], (EX1 - 0.17, 1.88, 1.6), M_CLOTH, steps=14, wobble=0.1, rot=(0.0, -0.5, 0.0))

# the entry's lantern on an iron bracket by the arch (right wall): the cross-light on the painting
def wall_lantern(name, base, out_dir):
    out_dir = Vector(out_dir).normalized()
    tube(name + "Arm", [base, base + out_dir * 0.18 + Vector((0, 0, 0.06)), base + out_dir * 0.24 + Vector((0, 0, 0.0))], (0.008, 0.008), M_IRON, sides=5, n=3)
    c = base + out_dir * 0.24 - Vector((0, 0, 0.18))
    cyl(name + "Top", 0.075, 0.06, tuple(c + Vector((0, 0, 0.17))), M_IRON, verts=8, r2=0.02)
    cyl(name + "Glass", 0.06, 0.2, tuple(c + Vector((0, 0, 0.04))), M_LAMPGLASS, verts=10)
    cyl(name + "Font", 0.07, 0.06, tuple(c - Vector((0, 0, 0.09))), M_BRASS, verts=10)
    for k in range(4):
        a = k * math.pi / 2
        cyl(f"{name}Wire{k}", 0.004, 0.24, tuple(c + Vector((0.062 * math.cos(a), 0.062 * math.sin(a), 0.04))), M_IRON, verts=4)
    return c + Vector((0, 0, 0.0))
L_ENTRY = wall_lantern("EntryLantern", Vector((EX0 + 0.02, -1.45, 1.86)), (1, 0, 0))

def hanging_lamp(name, c, ceil):
    """A whale-oil hanging lamp: a tin reservoir with a glass chimney under a smoke bell, on a chain."""
    lathe(name + "Font", [(0.0, 0.0), (0.06, 0.005), (0.085, 0.04), (0.06, 0.07), (0.02, 0.08), (0.0, 0.08)], tuple(c - Vector((0, 0, 0.1))), M_PEWTER, steps=12)
    lathe(name + "Chimney", [(0.0, 0.0), (0.03, 0.0), (0.045, 0.05), (0.02, 0.15), (0.0, 0.15)], tuple(c - Vector((0, 0, 0.03))), M_LAMPGLASS, steps=10)
    lathe(name + "Bell", [(0.0, 0.0), (0.07, 0.0), (0.03, 0.05), (0.012, 0.07), (0.0, 0.07)], tuple(c + Vector((0, 0, 0.2))), M_PEWTER, steps=10)
    cyl(name + "Chain", 0.004, ceil - (c.z + 0.27), (c.x, c.y, (ceil + c.z + 0.27) / 2), M_IRON, verts=4)
    return c + Vector((0, 0, 0.03))
L_HANG = hanging_lamp("EntryHangLamp", Vector((0.25, 0.95, 1.84)), ECEIL)
L_ROOM = hanging_lamp("RoomHangLamp", Vector((1.6, -7.0, 1.62)), 2.02)

# a tin candle sconce by the door
SC = Vector((EX1 - 0.05, 2.25, 1.38))
box("SconceBack", (0.01, 0.12, 0.22), (SC.x, SC.y, SC.z + 0.06), M_PEWTER)
cyl("SconcePan", 0.05, 0.015, (SC.x - 0.06, SC.y, SC.z - 0.04), M_PEWTER, verts=10)
cyl("SconceCandle", 0.011, 0.11, (SC.x - 0.06, SC.y, SC.z + 0.02), M_TALLOW, verts=8)

# ============================================================================= the public room
# --- the great iron box stove with its door open, the pipe running back to the chimney
def stove():
    s = STOVE
    W, D, H = 0.95, 0.62, 0.62; z0 = 0.26
    box("StoveBody", (D, W, H), (s.x, s.y, z0 + H / 2), M_IRON, bevel=0.03)
    box("StoveTop", (D + 0.08, W + 0.1, 0.05), (s.x, s.y, z0 + H + 0.025), M_IRON, bevel=0.015)
    box("StoveBase", (D + 0.06, W + 0.08, 0.06), (s.x, s.y, z0 + 0.03), M_IRON, bevel=0.015)
    for i, (dx, dy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        tube(f"StoveLeg{i}", [(s.x + dx * 0.26, s.y + dy * 0.42, z0), (s.x + dx * 0.30, s.y + dy * 0.46, z0 * 0.5), (s.x + dx * 0.29, s.y + dy * 0.50, 0.0)], (0.035, 0.03), M_IRON, sides=6, n=3)
    # the fire door on the end facing the room (+Y side faces the arch; door on the +X side towards the room's middle)
    fy = s.y + W / 2                      # the fire door is in the end towards the arch
    box("StoveDoorFrame", (0.40, 0.03, 0.30), (s.x, fy + 0.012, z0 + 0.30), M_IRON, bevel=0.008)
    box("StoveFireMouth", (0.32, 0.05, 0.22), (s.x, fy - 0.005, z0 + 0.30), M_HEARTH)
    box("StoveEmbers", (0.28, 0.03, 0.08), (s.x, fy - 0.002, z0 + 0.23), M_EMBERS)
    th = math.radians(115); hx = s.x - 0.18
    box("StoveDoor", (0.36, 0.025, 0.26), (hx + 0.18 * math.cos(th), fy + 0.03 + 0.18 * math.sin(th), z0 + 0.30), M_IRON, bevel=0.006, rot=(0, 0, th))
    cyl("StoveDoorKnob", 0.018, 0.04, (hx + 0.33 * math.cos(th), fy + 0.05 + 0.33 * math.sin(th), z0 + 0.30), M_BRASS, verts=8, rot=(math.pi / 2, 0, th))
    # an ornamental urn on the top, a kettle
    lathe("StoveUrn", [(0.0, 0.0), (0.07, 0.0), (0.09, 0.05), (0.06, 0.12), (0.03, 0.16), (0.0, 0.17)], (s.x, s.y + 0.28, z0 + H + 0.05), M_IRON, steps=12)
    lathe("Kettle", [(0.0, 0.0), (0.11, 0.0), (0.13, 0.06), (0.12, 0.13), (0.06, 0.17), (0.035, 0.19), (0.0, 0.19)], (s.x + 0.05, s.y + 0.02, z0 + H + 0.05), M_IRON, steps=14)
    tube("KettleSpout", [(s.x + 0.15, s.y + 0.02, z0 + H + 0.12), (s.x + 0.22, s.y + 0.02, z0 + H + 0.18)], (0.018, 0.01), M_IRON, sides=6, n=1)
    # pipe: up from the back of the top, then a long run back to the chimney thimble, hung on wires from the joists
    p0 = Vector((s.x - 0.05, s.y - 0.28, z0 + H + 0.05)); top = Vector((p0.x, p0.y, 1.88))
    thimble = Vector((-2.55, CY0, 1.88))
    tube("StovePipe", [p0, p0 + Vector((0, 0, 0.6)), top - Vector((0, 0, 0.12)), top + Vector((0, 0.12, 0)), Vector((thimble.x, (top.y + thimble.y) / 2, 1.88)), thimble + Vector((0, 0.05, 0))],
         (0.075, 0.075), M_IRON, sides=12, n=4)
    for k, y in enumerate((-4.6, -3.7)):
        cyl(f"PipeWire{k}", 0.003, PCEIL - 1.95, (thimble.x, y, (PCEIL + 1.95) / 2), M_IRON, verts=4)
    box("Thimble", (0.26, 0.04, 0.26), (thimble.x, CY0 - 0.01, 1.88), M_IRON, bevel=0.01)
    # a zinc stove board on the floor, a wood box and a coal scuttle
    box("StoveBoard", (1.1, 1.6, 0.008), (s.x, s.y + 0.15, 0.004), M_PEWTER, bevel=0.002)
    box("WoodBox", (0.5, 0.42, 0.42), (s.x - 0.75, s.y + 0.55, 0.21), M_DOOR, bevel=0.01)
    for k in range(5):
        cyl(f"Billet{k}", random.uniform(0.04, 0.06), 0.45, (s.x - 0.75 + random.uniform(-0.15, 0.15), s.y + 0.55, 0.40 + k * 0.03), M_FURN, verts=7, rot=(math.pi / 2, 0, random.uniform(-0.2, 0.2)))
    return Vector((s.x, fy - 0.10, z0 + 0.24))
FIRE = stove()
anchor("inn.stove", tuple(STOVE))

# --- the bar: a den built as a rude right whale's head, the vast arched jawbone at its mouth
def jaw_bar():
    c = BAR_C; half = 1.12; H = 2.28
    # two great curved bones rising from the floor and meeting overhead in a pointed arch (front, facing +Y)
    for sgn in (-1, 1):
        pts = [Vector((c.x + sgn * half, c.y, 0.0)), Vector((c.x + sgn * half * 1.02, c.y + 0.02, 0.7)), Vector((c.x + sgn * half * 0.92, c.y + 0.04, 1.45)),
               Vector((c.x + sgn * half * 0.62, c.y + 0.05, 1.98)), Vector((c.x + sgn * half * 0.22, c.y + 0.05, H - 0.04)), Vector((c.x + sgn * 0.02, c.y + 0.05, H))]
        radii = [0.16, 0.15, 0.14, 0.12, 0.10, 0.09, 0.085, 0.08, 0.075, 0.07, 0.065, 0.06, 0.06, 0.055, 0.05, 0.05, 0.045, 0.045, 0.04, 0.04, 0.04]
        o = tube(f"JawBone{sgn}", pts, radii, M_BONE, sides=9, n=4)
    # the den's walls: dark boarding curving back to the corner like the head's sides
    for sgn in (-1, 1):
        x = c.x + sgn * (half + 0.08)
        box(f"DenSide{sgn}", (0.06, c.y - PY0, 2.25), (x, (c.y + PY0) / 2, 1.125), M_DOOR, bevel=0.01)
    box("DenRoof", (2 * half + 0.25, c.y - PY0 + 0.1, 0.05), (c.x, (c.y + PY0) / 2, 2.27), M_DOOR)
    # counter across the mouth with a lifting flap, shabby shelves inside ranged round with bottles
    box("BarCounter", (2 * half - 0.2, 0.42, 0.06), (c.x, c.y - 0.12, 1.02), M_FURN, bevel=0.012)
    box("BarFront", (2 * half - 0.25, 0.05, 1.0), (c.x, c.y + 0.06, 0.5), M_DOOR, bevel=0.006)
    shelf_y = PY0 + 0.18
    for k, z in enumerate((1.05, 1.42, 1.78)):
        box(f"BarShelf{k}", (2 * half - 0.1, 0.24, 0.025), (c.x, shelf_y, z), M_FURN, bevel=0.004, rot=(0, random.uniform(-0.012, 0.012), 0))
        x = c.x - half + 0.12
        while x < c.x + half - 0.1:
            kind = random.random()
            if kind < 0.45:     # square-shouldered gin case bottles and round bottles
                h = random.uniform(0.2, 0.3)
                lathe(f"Bottle{k}_{x:.2f}", [(0.0, 0.0), (0.04, 0.0), (0.042, h * 0.62), (0.016, h * 0.78), (0.013, h), (0.0, h)], (x, shelf_y + random.uniform(-0.04, 0.04), z + 0.013), M_BOTTLE, steps=8)
                x += random.uniform(0.09, 0.14)
            elif kind < 0.75:   # decanters
                lathe(f"Decanter{k}_{x:.2f}", [(0.0, 0.0), (0.045, 0.0), (0.06, 0.06), (0.05, 0.13), (0.02, 0.18), (0.022, 0.22), (0.0, 0.24)], (x, shelf_y, z + 0.013), M_BOTTLE, steps=10)
                x += 0.15
            else:               # flasks lying or a stoneware jug
                lathe(f"Jug{k}_{x:.2f}", [(0.0, 0.0), (0.06, 0.0), (0.075, 0.08), (0.06, 0.17), (0.025, 0.21), (0.0, 0.215)], (x, shelf_y, z + 0.013), M_CURIO, steps=10)
                x += 0.17
    # the "villainous green goggling glasses" on the counter, a pewter measure
    for k in range(5):
        lathe(f"Tumbler{k}", [(0.0, 0.0), (0.033, 0.0), (0.036, 0.11), (0.0, 0.11)], (c.x - 0.7 + k * 0.17 + random.uniform(-0.03, 0.03), c.y - 0.12 + random.uniform(-0.1, 0.1), 1.05), M_GREENGLASS, steps=10)
    lathe("Measure", [(0.0, 0.0), (0.045, 0.0), (0.04, 0.12), (0.045, 0.14), (0.0, 0.14)], (c.x + 0.6, c.y - 0.15, 1.05), M_PEWTER, steps=12)
    # a hanging lantern inside the den
    lc = Vector((c.x + 0.3, c.y - 0.75, 1.88))
    cyl("BarLanternTop", 0.07, 0.05, tuple(lc + Vector((0, 0, 0.14))), M_IRON, verts=8, r2=0.02)
    cyl("BarLanternGlass", 0.055, 0.18, tuple(lc), M_LAMPGLASS, verts=10)
    cyl("BarLanternFont", 0.065, 0.05, tuple(lc - Vector((0, 0, 0.11))), M_BRASS, verts=10)
    cyl("BarLanternChain", 0.004, 2.27 - (lc.z + 0.17), (lc.x, lc.y, (2.27 + lc.z + 0.17) / 2), M_IRON, verts=4)
    return lc
L_BAR = jaw_bar()
anchor("inn.bar", tuple(BAR_C))

# --- the long low shelf-like table of cracked glass cases, along the left wall
def glass_cases():
    x0, x1, y0, y1 = PX1 - 0.78, PX1 - 0.06, -9.9, -5.2
    box("CaseTableTop", (x1 - x0, y1 - y0, 0.05), ((x0 + x1) / 2, (y0 + y1) / 2, 0.72), M_FURN, bevel=0.01)
    box("CaseTableShelf", (x1 - x0 - 0.06, y1 - y0 - 0.1, 0.03), ((x0 + x1) / 2, (y0 + y1) / 2, 0.18), M_FURN)
    for (x, y) in ((x0 + 0.05, y0 + 0.05), (x1 - 0.05, y0 + 0.05), (x0 + 0.05, y1 - 0.05), (x1 - 0.05, y1 - 0.05), (x0 + 0.05, (y0 + y1) / 2)):
        box(f"CaseLeg{x:.1f}{y:.1f}", (0.06, 0.06, 0.70), (x, y, 0.35), M_FURN, bevel=0.006)
    rng = random.Random(3)
    y = y0 + 0.05; k = 0
    while y < y1 - 0.4:
        L = rng.uniform(0.7, 1.1); L = min(L, y1 - 0.05 - y); h = rng.uniform(0.24, 0.34)
        cx, cy = (x0 + x1) / 2, y + L / 2
        box(f"CaseBase{k}", (x1 - x0 - 0.06, L - 0.04, 0.04), (cx, cy, 0.765), M_FURN, bevel=0.006)
        box(f"CaseGlass{k}", (x1 - x0 - 0.1, L - 0.08, h), (cx, cy, 0.785 + h / 2), M_CASEGLASS)
        for (dx, dy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            box(f"CasePost{k}{dx}{dy}", (0.025, 0.025, h), (cx + dx * (x1 - x0 - 0.1) / 2, cy + dy * (L - 0.08) / 2, 0.785 + h / 2), M_FURN)
        box(f"CaseLid{k}", (x1 - x0 - 0.06, L - 0.04, 0.025), (cx, cy, 0.79 + h), M_FURN, bevel=0.005)
        # a crack across one pane (a dark thin line: a sliver of frame-coloured strip)
        if rng.random() < 0.7:
            box(f"CaseCrack{k}", (0.002, L * 0.6, 0.003), (cx - (x1 - x0 - 0.1) / 2 - 0.001, cy, 0.785 + h * 0.6), M_HAIR, rot=(rng.uniform(-0.4, 0.4), 0, 0))
        # dusty rarities: shells, a coral branch, carved teeth, an idol, a small canoe, a spear-head
        for j in range(rng.randint(3, 5)):
            px, py = cx + rng.uniform(-0.2, 0.2), cy + rng.uniform(-L / 2 + 0.12, L / 2 - 0.12)
            kind = rng.random()
            if kind < 0.3: blob(f"Shell{k}{j}", (px, py, 0.81), rng.uniform(0.04, 0.07), M_CURIO, scale=(1.3, 1, 0.6), subdiv=2, amp=0.25, seed=rng.random() * 9)
            elif kind < 0.5:
                b0 = Vector((px, py, 0.79))
                for t in range(4):
                    tube(f"Coral{k}{j}{t}", [b0, b0 + Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0.08)), b0 + Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), rng.uniform(0.12, 0.2)))], (0.012, 0.004), M_CORAL, sides=5, n=2)
            elif kind < 0.7: cyl(f"CarvedTooth{k}{j}", 0.025, 0.14, (px, py, 0.81), M_TEETH, verts=8, r2=0.008, rot=(math.pi / 2, 0, rng.uniform(0, 3)))
            elif kind < 0.85: lathe(f"Idol{k}{j}", [(0, 0), (0.035, 0), (0.03, 0.05), (0.04, 0.09), (0.028, 0.12), (0.034, 0.15), (0, 0.17)], (px, py, 0.79), M_CLUB, steps=8)
            else: blob(f"Canoe{k}{j}", (px, py, 0.8), 0.15, M_CLUB, scale=(0.18, 1.0, 0.12), subdiv=2, amp=0.05, seed=rng.random())
        y += L + 0.04; k += 1
glass_cases()

# --- a long table and benches in the middle (behind the page: kept plain), a small table with two tallow candles
def table(name, cx, cy, L, W, h=0.74, along='Y'):
    sx, sy = (W, L) if along == 'Y' else (L, W)
    box(name + "Top", (sx, sy, 0.05), (cx, cy, h - 0.025), M_FURN, bevel=0.01, rot=(0, 0, random.uniform(-0.02, 0.02)))
    for dx in (-1, 1):
        for dy in (-1, 1):
            box(f"{name}Leg{dx}{dy}", (0.07, 0.07, h - 0.05), (cx + dx * (sx / 2 - 0.08), cy + dy * (sy / 2 - 0.1), (h - 0.05) / 2), M_FURN, bevel=0.008)
    box(name + "Stretcher", (0.05, sy - 0.25, 0.06) if along == 'Y' else (sx - 0.25, 0.05, 0.06), (cx, cy, 0.16), M_FURN)

def bench(name, cx, cy, L, along='Y'):
    s = (0.3, L, 0.05) if along == 'Y' else (L, 0.3, 0.05)
    box(name + "Seat", s, (cx, cy, 0.45), M_FURN, bevel=0.01, rot=(0, 0, random.uniform(-0.03, 0.03)))
    for d in (-1, 1):
        o = (0, d * (L / 2 - 0.12), 0) if along == 'Y' else (d * (L / 2 - 0.12), 0, 0)
        box(f"{name}Leg{d}", (0.26, 0.05, 0.43) if along == 'Y' else (0.05, 0.26, 0.43), (cx + o[0], cy + o[1], 0.215), M_FURN, bevel=0.006)

table("LongTable", 0.2, -7.9, 2.6, 0.85)
bench("BenchL", 0.85, -7.9, 2.4); bench("BenchR", -0.45, -7.9, 2.4)
for k in range(3):
    lathe(f"Mug{k}", [(0, 0), (0.045, 0), (0.05, 0.12), (0.0, 0.12)], (0.2 + random.uniform(-0.25, 0.25), -7.3 - k * 0.6, 0.74), M_PEWTER, steps=10)
table("CandleTable", 2.05, -5.6, 0.9, 0.7)
CANDLES = []
for k, (dx, dy, h) in enumerate(((-0.15, 0.1, 0.17), (0.12, -0.12, 0.12))):
    p = Vector((2.05 + dx, -5.6 + dy, 0.74))
    lathe(f"CandleStick{k}", [(0, 0), (0.06, 0), (0.06, 0.012), (0.02, 0.025), (0.016, 0.09), (0.03, 0.1), (0.012, 0.11), (0, 0.11)], tuple(p), M_PEWTER, steps=10)
    # tallow candles "each in a winding sheet": guttered, with a long drip down one side
    lathe(f"Candle{k}", [(0, 0), (0.012, 0), (0.0125, h * 0.6), (0.011, h), (0.0, h + 0.004)], tuple(p + Vector((0, 0, 0.1))), M_TALLOW, steps=8, wobble=0.12, seed=k)
    tube(f"CandleSheet{k}", [p + Vector((0.012, 0, 0.1 + h)), p + Vector((0.016, 0.003, 0.1 + h * 0.5)), p + Vector((0.02, 0.004, 0.105))], (0.006, 0.009), M_TALLOW, sides=5, n=2)
    CANDLES.append(p + Vector((0, 0, 0.1 + h + 0.012)))
chair_spots = [(1.5, -6.2, 0.6), (-3.3, -4.2, -2.4)]
for k, (x, y, a) in enumerate(chair_spots):
    box(f"ChairSeat{k}", (0.42, 0.40, 0.04), (x, y, 0.45), M_FURN, bevel=0.008, rot=(0, 0, a))
    R = Matrix.Rotation(a, 3, 'Z')
    for dx in (-1, 1):
        for dy in (-1, 1):
            q = R @ Vector((dx * 0.17, dy * 0.16, 0))
            box(f"ChairLeg{k}{dx}{dy}", (0.035, 0.035, 0.45 if dy < 0 else 0.95), (x + q.x, y + q.y, (0.45 if dy < 0 else 0.95) / 2), M_FURN, rot=(0, 0, a))
    for z in (0.65, 0.8):
        q = R @ Vector((0, 0.16, 0))
        box(f"ChairRail{k}{z}", (0.34, 0.025, 0.05), (x + q.x, y + q.y, z), M_FURN, rot=(0, 0, a))

# ============================================================================= living-scene markers, sounds, lights
fx_empty("fx.fire.stove", tuple(FIRE), 0.16)
fx_empty("fx.lantern.entry", tuple(L_ENTRY + Vector((0, 0, 0.02))), 0.04)
fx_empty("fx.lantern.bar", tuple(L_BAR + Vector((0, 0, 0.01))), 0.04)
fx_empty("fx.lantern.entryHanging", tuple(L_HANG + Vector((0, 0, 0.02))), 0.03)
fx_empty("fx.lantern.roomHanging", tuple(L_ROOM + Vector((0, 0, 0.02))), 0.03)
for k, p in enumerate(CANDLES): fx_empty(f"fx.candle.table{k + 1}", tuple(p), 0.01)
fx_empty("fx.candle.door", (SC.x - 0.06, SC.y, SC.z + 0.085), 0.01)
sound_empty("sound.fire.stove", tuple(FIRE + Vector((0, 0, 0.2))))
sound_empty("sound.wind.door", ((DOOR_X0 + WIN_X1) / 2, EY1 - 0.1, 0.8))
sound_empty("sound.crowd.kitchen", ((KDOOR[0] + KDOOR[1]) / 2, PY0 - 1.0, 1.4))
sound_empty("sound.clock.entry", (CLOCK.x - 0.1, CLOCK.y, 1.6))

# Blender-only flames for the preview renders (Unity draws its own at the fx empties)
def preview_flame(name, p, s=1.0):
    o = blob(name, tuple(p + Vector((0, 0, 0.012 * s))), 0.008 * s, M_FLAME, scale=(1, 1, 2.6), subdiv=1, amp=0.05)
    o.name = "PREVIEW_" + name
for k, p in enumerate(CANDLES): preview_flame(f"FlameC{k}", p)
preview_flame("FlameDoor", Vector((SC.x - 0.06, SC.y, SC.z + 0.085)))
preview_flame("FlameEntryLantern", L_ENTRY - Vector((0, 0, 0.02)), 1.6)
preview_flame("FlameBarLantern", L_BAR - Vector((0, 0, 0.03)), 1.6)
preview_flame("FlameEntryHang", L_HANG, 1.4)
preview_flame("FlameRoomHang", L_ROOM, 1.4)

# lamp glass and preview flames must not block their own light (Cycles has refractive caustics off)
for o in COLL.objects:
    if o.type == 'MESH' and o.data.materials and o.data.materials[0].name in ("M_LampGlass", "PREVIEW_FlameMat"):
        o.visible_shadow = False
WARM = (1.0, 0.60, 0.30); CANDLE_C = (1.0, 0.66, 0.36)
light_obj("Lamp.stove", 'POINT', 22.0, (1.0, 0.45, 0.16), tuple(FIRE + Vector((0, 0.8, 0.3))), shadow_soft_size=0.15)
light_obj("Lamp.entryLantern", 'POINT', 50.0, WARM, tuple(L_ENTRY), shadow_soft_size=0.015)
light_obj("Lamp.entryHanging", 'POINT', 55.0, WARM, tuple(L_HANG), shadow_soft_size=0.012)
light_obj("Lamp.barLantern", 'POINT', 50.0, WARM, tuple(L_BAR), shadow_soft_size=0.015)
light_obj("Lamp.roomHanging", 'POINT', 40.0, WARM, tuple(L_ROOM), shadow_soft_size=0.012)
light_obj("Lamp.candles", 'POINT', 8.0, CANDLE_C, tuple((CANDLES[0] + CANDLES[1]) / 2 + Vector((0, 0, 0.02))), shadow_soft_size=0.02)
light_obj("Lamp.doorCandle", 'POINT', 5.0, CANDLE_C, (SC.x - 0.08, SC.y, SC.z + 0.1), shadow_soft_size=0.02)

world = bpy.data.worlds.new("SpouterNight"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.010, 0.012, 0.020, 1); bg.inputs["Strength"].default_value = 0.8
# the night outside the windows: a faint cold glow (Blender preview only; nothing outside is exported)
for k, (ya, yb) in enumerate(PWIN):
    light_obj(f"PREVIEW_Night{k}", 'AREA', 0.6, (0.55, 0.65, 0.9), (PX0 - 0.6, (ya + yb) / 2, 1.4), direction=(1, 0, -0.3), size=0.8)

# ============================================================================= anchors, page, cameras
anchor("reader.entrance", (0.0, 0.0, 0.0))
anchor("reader.look", (0.0, -1.0, EYE))
anchor("scene.centre", ((AX0 + AX1) / 2, (CY0 + CY1) / 2, 0.0))
preview_page(EYE)
E = (0.0, 0.0, EYE)
camera("Cam_Reader", E, (0.0, -10.0, 1.3))
camera("Cam_Page", E, (0.0, -10.0, 1.4))
camera("Cam_Left", E, (10.0, -1.2, 1.3))
camera("Cam_Right", E, (-10.0, 0.4, 1.3))
camera("Cam_Behind", E, (0.4, 10.0, 1.2))
camera("Cam_Down", E, (0.1, -1.2, 0.0), lens=16)
camera("Cam_Up", E, (0.0, -1.5, 3.2), lens=16)
camera("Cam_Arch", E, (-1.6, -9.0, 1.1), lens=30)
camera("Cam_Painting", (0.3, -0.35, 1.5), (EX1, -0.35, 1.5), lens=24)
camera("Cam_Clubs", (-0.6, 0.0, 1.55), (EX0, 0.0, 1.45), lens=20)

if not args.nosave: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(S["out"], "spouter_inn_source.blend"))
print_budget()
if args.render:
    render_cams(SID, exposure={"*": 1.3})
if args.bake or args.export:
    for o in [o for o in COLL.objects if o.name.startswith("PREVIEW_") and o is not S.get("page")]:
        bpy.data.objects.remove(o)
    size_for = {"M_FloorPlanks": args.tex, "M_Wainscot": args.tex, "M_Plaster": args.tex, "M_Brick": args.tex, "M_Beams": args.tex // 2,
                "M_Joists": args.tex // 2, "M_CeilingBoards": args.tex // 2, "M_Furniture": args.tex // 2, "M_ClubWood": args.tex // 2,
                "M_JawBone": args.tex // 2, "M_CastIron": args.tex // 2, "M_DoorPlanks": args.tex // 2, "M_Painting": args.tex,
                "M_RustyIron": args.tex // 4, "M_PaintingFrame": args.tex // 4, "M_Teeth": args.tex // 8, "M_Hair": args.tex // 8,
                "M_Oilskin": args.tex // 4, "M_Curios": args.tex // 4}
    size_for["M_Painting"] = 1024
    bake_and_export("spouter_inn.gltf", size_for, default_size=128, keep_uv={"MESH_Painting"})
print("DONE")
