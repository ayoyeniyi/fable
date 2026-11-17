"""
Fable: the assembly room at Meryton on the night of the ball (Pride and Prejudice, chapter 3). A chapter step-in room:
built ahead of time, served from the server, downloaded by the headset.

"Mr. Bingley ... danced every dance" ... "Elizabeth Bennet had been obliged, by the scarcity of gentlemen, to sit down
for two dances; and during part of that time, Mr. Darcy had been standing near enough for her to overhear a
conversation between him and Mr. Bingley" ... "such an assembly as this" (chapter 3).

The public assembly room of a small Hertfordshire market town, c. 1811: a long, plain room (8 x 14 m), pale painted
plaster between shallow pilasters, a simple cornice, a waxed board floor chalked with a garland pattern for the
dancing (scuffed already by the first sets), forms and chairs along the walls where the ladies sit out, three tall sash
windows on the east wall black with the night behind plain curtains, a little musicians' gallery on a dais at the north
end with music stands, chairs, a bass viol and a fiddle case, the double door from the stairs at the south end and a
refreshment table with a punch bowl, glasses and negus. Light: three brass candle chandeliers down the middle and
two-light sconces on the pilasters; warm, uneven light, dark corners. Country-town, not fashionable: no gilding, no
red coats. The dancers are not modelled (a crowd sound fills the room); the evidence of the ball is left about: shawls
and a fan on the forms, glasses on the side tables.

The reader stands by the west wall among the forms where the ladies sit out (Elizabeth's place), facing across the
dance floor towards the windows, the gallery up to the left.

Living scene (docs/LIVING_SCENES.md): fx.candle.* (every chandelier and sconce candle, radius extra),
cloth.curtain.windows (R = billow weight), sound.crowd.floor, sound.crowd.door.

Node names: anchor.reader.entrance (feet, floor z = 0), anchor.reader.look (eye height), anchor.scene.centre (the middle
of the dance floor), anchor.room.gallery, anchor.room.door, anchor.room.refreshments; light.chandelier1..3,
light.sconces.* (POINT), light.passage.

Axes: metres, Blender +Z up. Room x -4..4, y -3..11; the windows in the east (+x) wall, the gallery at the north (+y) end.

Run headless (one Blender at a time):
  blender -b -P blender/build_meryton_assembly_room.py -- --render --quick --res 900 --cams reader
  blender -b -P blender/build_meryton_assembly_room.py -- --render --samples 48 --res 1400 --captures captures/blender/meryton-assembly-room
  blender -b -P blender/build_meryton_assembly_room.py -- --bake --export --tex 2048
Everything is procedural: no downloaded models, textures or HDRIs.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pride_kit as K
import pride_interior as I
from pride_kit import (new_mat, node, ramp, math_, mix_rgb, maprange, noise_, voronoi_, bump_from, c4, obj_coords, sep_xyz,
                       wood, noisy, plain, box, cyl, sphere, lathe, tube, sweep, mesh_from, Frame, anchor, sound, light_obj, camera, link)
ARGS = K.setup("meryton-assembly-room", "out/meryton-assembly-room", 1811, "MerytonAssembly", default_samples=48)
import scene_kit_b2 as B
OUT = K.OUT; scene = K.scene
scene.cycles.max_bounces = 10; scene.cycles.diffuse_bounces = 6
rng = random.Random(1811)

EYE = 1.55
R = I.Room(-4.0, 4.0, -3.0, 11.0, 4.6, t=0.45)
READER = Vector((-3.05, 1.6, 0.0))
LOOK_AT = Vector((3.5, 4.6, 0.0))
GALLERY_Y = 9.0                       # the dais runs from here to the north wall

# ----------------------------------------------------------------------------- materials
M_WALL = I.paint_mat("M_WallPaint", K.srgb((0.78, 0.76, 0.66)), rough=0.85, dirt=0.1)
M_JOIN = I.joinery_mat("M_Joinery", K.srgb((0.82, 0.80, 0.73)), rough=0.45)
M_CEIL = I.paint_mat("M_Ceiling", K.srgb((0.80, 0.79, 0.74)), rough=0.9, dirt=0.0)
M_DEAL = wood("M_DealWood", base=(0.30, 0.20, 0.11), dark=(0.13, 0.08, 0.04), light=(0.42, 0.30, 0.17), scale=1.2, rough=(0.45, 0.7))
M_FORM = wood("M_FormWood", base=(0.17, 0.10, 0.05), dark=(0.06, 0.035, 0.018), light=(0.25, 0.15, 0.08), scale=1.5, rough=(0.35, 0.55), coat=0.2)
M_BAIZE = noisy("M_FormCover", [K.srgb((0.33, 0.40, 0.33)), K.srgb((0.38, 0.45, 0.37))], scale=60, rough=0.85, bump=0.1, sheen=0.4)
M_BRASS = plain("M_Brass", (0.62, 0.45, 0.20), rough=0.32, metallic=0.85)
M_WAX = plain("M_Wax", K.srgb((0.93, 0.90, 0.82)), rough=0.45)
M_FLAME = plain("M_RenderFlame", (0, 0, 0), rough=1.0, emission=(1.0, 0.62, 0.25), strength=14.0)
M_NIGHT = plain("M_WindowGlassNight", (0.006, 0.008, 0.012), rough=0.05)
M_CURTAIN = I.silk("M_Curtains", K.srgb((0.55, 0.50, 0.38)), K.srgb((0.62, 0.57, 0.45)), damask=0.0, sheen=0.3, rough=0.85)
M_LINEN = noisy("M_TableLinen", [K.srgb((0.86, 0.85, 0.80)), K.srgb((0.80, 0.79, 0.74))], scale=30, rough=0.8, bump=0.1)
M_GLASS = plain("M_Glassware", (0.75, 0.78, 0.76), rough=0.05, transmission=0.8)
M_PUNCH = plain("M_PunchBowl", K.srgb((0.85, 0.84, 0.80)), rough=0.2, coat=0.6)
M_SHAWL1 = noisy("M_ShawlRose", [K.srgb((0.72, 0.45, 0.42)), K.srgb((0.80, 0.55, 0.50))], scale=40, rough=0.9, sheen=0.6, bump=0.05)
M_SHAWL2 = noisy("M_ShawlCream", [K.srgb((0.85, 0.82, 0.70)), K.srgb((0.78, 0.74, 0.60))], scale=40, rough=0.9, sheen=0.6, bump=0.05)
M_PAPER = noisy("M_MusicPaper", [K.srgb((0.85, 0.82, 0.72)), K.srgb((0.30, 0.28, 0.25))], scale=90, rough=0.8, stretch=(1, 1, 20), bump=0.0)
M_VIOL = wood("M_ViolVarnish", base=(0.38, 0.15, 0.05), dark=(0.15, 0.05, 0.02), light=(0.55, 0.25, 0.08), scale=3.0, rough=(0.2, 0.35), coat=0.6)
M_BLACK = plain("M_Ebony", (0.02, 0.018, 0.016), rough=0.35)

def chalked_floor_mat(name="M_ChalkFloor"):
    """waxed deal boards running the length of the room; on the dance floor a chalked design (a border of loops and a
    garland round a centre medallion), already scuffed and half trodden out along the lines of the sets."""
    m, nt, b = new_mat(name)
    co = obj_coords(nt); s = sep_xyz(nt, co, (-2000, 0)); x = s.outputs["X"]; y = s.outputs["Y"]
    # boards: along Y, 0.2 m wide, each board its own tone
    idx = math_(nt, 'FLOOR', math_(nt, 'DIVIDE', x, 0.2, (-1800, 300)), None, (-1650, 300))
    rnd = node(nt, "ShaderNodeTexWhiteNoise", (-1500, 300)); rnd.noise_dimensions = '1D'; nt.links.new(idx, rnd.inputs["W"])
    frac = math_(nt, 'FRACT', math_(nt, 'DIVIDE', x, 0.2, (-1800, 150)), None, (-1650, 150))
    seam = maprange(nt, math_(nt, 'MINIMUM', frac, math_(nt, 'SUBTRACT', 1.0, frac, (-1500, 100)), (-1400, 120)), 0.0, 0.04, 1, 0, (-1250, 120))
    mp = node(nt, "ShaderNodeMapping", (-1700, -100)); mp.inputs["Scale"].default_value = (6.0, 0.25, 1.0); nt.links.new(co, mp.inputs["Vector"])
    grain = noise_(nt, mp.outputs["Vector"], 3.0, 8, 0.65, 2.0, (-1500, -100))
    tone = math_(nt, 'ADD', math_(nt, 'MULTIPLY', rnd.outputs["Value"], 0.5, (-1300, 300)), math_(nt, 'MULTIPLY', grain.outputs["Fac"], 0.6, (-1300, -100)), (-1150, 100))
    r = ramp(nt, [(0.2, c4(K.srgb((0.32, 0.22, 0.13)))), (0.55, c4(K.srgb((0.45, 0.33, 0.20)))), (0.9, c4(K.srgb((0.55, 0.42, 0.27))))], (-1000, 200))
    nt.links.new(tone, r.inputs["Fac"])
    col = mix_rgb(nt, 'MIX', seam, r.outputs["Color"], (0.05, 0.03, 0.015, 1), (-800, 200))
    # the chalk design: ellipse rings and a scalloped border round the dance floor's centre (0, 3.5)
    dx = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', x, 0.0, (-1800, -500)), 2.4, (-1650, -500))
    dy = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', y, 3.5, (-1800, -650)), 4.6, (-1650, -650))
    rr = math_(nt, 'SQRT', math_(nt, 'ADD', math_(nt, 'MULTIPLY', dx, dx, (-1500, -500)), math_(nt, 'MULTIPLY', dy, dy, (-1500, -650)), (-1350, -580)), None, (-1200, -580))
    ang = math_(nt, 'ARCTAN2', dy, dx, (-1350, -750))
    scal = math_(nt, 'MULTIPLY', math_(nt, 'ABSOLUTE', math_(nt, 'SINE', math_(nt, 'MULTIPLY', ang, 18.0, (-1200, -750)), None, (-1050, -750)), None, (-900, -750)), 0.05, (-750, -750))
    def ring(radius, w, loc):
        d = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', rr, radius, (loc[0], loc[1])), None, (loc[0] + 120, loc[1]))
        return maprange(nt, d, w, w * 0.4, 0, 1, (loc[0] + 250, loc[1]))
    r1 = ring(1.0, 0.012, (-1100, -900)); r2 = ring(0.93, 0.008, (-1100, -1050)); r3 = ring(0.35, 0.01, (-1100, -1200))
    scl = math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', rr, math_(nt, 'ADD', 0.82, scal, (-700, -800)), (-600, -820)), None, (-500, -820))
    r4 = maprange(nt, scl, 0.012, 0.005, 0, 1, (-400, -820))
    chalk = math_(nt, 'MAXIMUM', math_(nt, 'MAXIMUM', r1, r2, (-700, -950)), math_(nt, 'MAXIMUM', r3, r4, (-600, -1100)), (-450, -1000))
    wearn = noise_(nt, co, 3.5, 4, 0.6, loc=(-900, -1350))
    trod = maprange(nt, wearn.outputs["Fac"], 0.4, 0.62, 0.0, 0.85, (-700, -1350))
    chalk = math_(nt, 'MULTIPLY', chalk, trod, (-300, -1050))
    col = mix_rgb(nt, 'MIX', math_(nt, 'MULTIPLY', chalk, 0.5, (-200, -900)), col, (0.62, 0.60, 0.55, 1), (-100, 200))
    # a dull traffic band down the middle where the sets go up and down
    traffic = math_(nt, 'MULTIPLY', maprange(nt, math_(nt, 'ABSOLUTE', x, None, (-1300, -1500)), 2.6, 1.2, 0, 1, (-1150, -1500)), 0.25, (-1000, -1500))
    col = mix_rgb(nt, 'MIX', traffic, col, (0.30, 0.24, 0.17, 1), (50, 200))
    col = K.ao_mul(nt, col, 0.25, 0.4, (150, -300))
    nt.links.new(col, b.inputs["Base Color"])
    nt.links.new(maprange(nt, traffic, 0, 0.25, 0.35, 0.6, (100, -500)), b.inputs["Roughness"])
    bump_from(nt, b, math_(nt, 'SUBTRACT', grain.outputs["Fac"], seam, (0, -700)), 0.15, 0.002)
    return m
M_FLOOR = chalked_floor_mat()

# ----------------------------------------------------------------------------- openings and the shell
WIN_Y = [0.6, 4.0, 7.4]                      # east wall: u = y + 3
for k, y in enumerate(WIN_Y):
    I.sash_window(f"Win{k}", R, 'E', y + 3.0, 1.15, 0.75, 2.75, M_JOIN, M_NIGHT, M_JOIN, panes=(3, 6))
DOOR_U = 4.0 - 1.4                           # south wall runs from x0 (u = x + 4): the double door at x = -1.4
I.six_panel_door("Door", R, 'S', 1.4 + 4.0 - 4.0 + 2.6, 1.5, 2.6, M_DEAL, M_JOIN, M_BRASS, open_deg=70, hinge_left=True)
I.build_walls(R, M_WALL)
box("Floor", (R.x1 - R.x0 + 0.2, R.y1 - R.y0 + 0.2, 0.04), (0, (R.y0 + R.y1) / 2, -0.02), M_FLOOR)
box("Ceiling", (R.x1 - R.x0 + 0.2, R.y1 - R.y0 + 0.2, 0.05), (0, (R.y0 + R.y1) / 2, R.h + 0.025), M_CEIL)
# the stair landing beyond the door: dim, a glimpse of a banister
box("LandingFloor", (2.6, 2.4, 0.02), (-1.4, R.y0 - R.t - 1.2, -0.01), M_DEAL)
box("LandingWallS", (2.6, 0.1, 3.2), (-1.4, R.y0 - R.t - 2.4, 1.6), M_WALL)
for s in (-1, 1): box(f"LandingWall{s}", (0.1, 2.4, 3.2), (-1.4 + s * 1.3, R.y0 - R.t - 1.2, 1.6), M_WALL)
box("LandingCeil", (2.8, 2.6, 0.05), (-1.4, R.y0 - R.t - 1.2, 3.2), M_CEIL)
tube("Banister", [(-0.4, R.y0 - R.t - 0.6, 0.95), (-0.4, R.y0 - R.t - 2.3, 0.95)], 0.03, M_FORM, sides=6)
for k in range(6): cyl(f"Baluster{k}", 0.018, 0.9, (-0.4, R.y0 - R.t - 0.7 - k * 0.3, 0.47), M_JOIN, verts=6)

# mouldings: skirting, dado rail, cornice, pilasters
I.moulding_runs(R, "Skirting", I.skirting_profile(0.22), 0.0, M_JOIN)
I.moulding_runs(R, "DadoRail", I.rail_profile(), 0.95, M_JOIN, z_band=(0.91, 0.98))
I.moulding_runs(R, "Cornice", I.cornice_profile(0.22, 0.26), R.h, M_JOIN, z_band=(R.h - 0.26, R.h))
PIL = []
for w, us in (('W', [1.2, 4.6, 8.0, 11.4]), ('E', [1.9, 5.3, 8.7, 12.3])):
    o, a, n, L = R.wall_frame(w)
    for u in us:
        if any(abs(u - op[0]) < op[1] / 2 + 0.2 for op in R.openings[w]): continue
        c = o + a * u + n * 0.04
        box(f"Pilaster{w}{u}", (abs(a.x) * 0.36 + abs(n.x) * 0.08, abs(a.y) * 0.36 + abs(n.y) * 0.08, R.h - 0.5), tuple(c + Vector((0, 0, (R.h - 0.5) / 2 + 0.24))), M_JOIN)
        box(f"PilCap{w}{u}", (abs(a.x) * 0.44 + abs(n.x) * 0.12, abs(a.y) * 0.44 + abs(n.y) * 0.12, 0.1), tuple(c + n * 0.02 + Vector((0, 0, R.h - 0.31))), M_JOIN)
        box(f"PilBase{w}{u}", (abs(a.x) * 0.42 + abs(n.x) * 0.11, abs(a.y) * 0.42 + abs(n.y) * 0.11, 0.24), tuple(c + n * 0.015 + Vector((0, 0, 0.12))), M_JOIN)
        PIL.append((w, u, c, n))
# plain curtains at the windows, hung from a pole, left open (the windows black with the night)
CUR = B.MB() if hasattr(B, "MB") else None
cm = K.MB()
for k, y in enumerate(WIN_Y):
    x = R.x1 - 0.06
    tube(f"CurtainPole{k}", [(x, y - 1.1, 3.62), (x, y + 1.1, 3.62)], 0.022, M_FORM, sides=8)
    for s in (-1, 1):
        ys0 = y + s * 0.62; width = 0.55; nf = 7; rows = 7
        base_i = []
        for j in range(rows + 1):
            t = j / rows; z = 3.6 - t * 3.0
            row = []
            for i in range(nf * 4 + 1):
                u = i / (nf * 4)
                gather = 1.0 - 0.35 * t * (1 - abs(u - 0.5) * 2) * 0.0
                yy = ys0 + (u - 0.5) * width * (1.0 - 0.25 * t)
                xx = x - 0.04 - 0.035 * math.sin(u * nf * 2 * math.pi) * (0.7 + 0.3 * t)
                row.append(cm.vert((xx, yy, z), (u, t), t ** 1.2))
            base_i.append(row)
        for j in range(rows):
            for i in range(nf * 4):
                cm.face(base_i[j][i], base_i[j][i + 1], base_i[j + 1][i + 1], base_i[j + 1][i])
cm.build("cloth.curtain.windows", M_CURTAIN)

# ----------------------------------------------------------------------------- the musicians' dais and gallery rail at the north end
DZ = 0.55
box("Dais", (R.x1 - R.x0, R.y1 - GALLERY_Y, DZ), (0, (GALLERY_Y + R.y1) / 2, DZ / 2), M_DEAL)
box("DaisNosing", (R.x1 - R.x0, 0.06, 0.06), (0, GALLERY_Y + 0.02, DZ - 0.02), M_FORM)
for k in range(3):                             # steps up at the west side
    box(f"DaisStep{k}", (0.9, 0.3, DZ * (k + 1) / 3), (-3.4, GALLERY_Y - 0.9 + k * 0.3, DZ * (k + 1) / 6), M_DEAL)
# a low balustrade along the dais front, with a gap at the steps
for k in range(25):
    x = -2.7 + k * 0.27
    lathe(f"DaisBal{k}", [(0, 0), (0.03, 0), (0.03, 0.05), (0.018, 0.1), (0.035, 0.28), (0.018, 0.5), (0.03, 0.55), (0, 0.56)], (x, GALLERY_Y + 0.12, DZ), M_JOIN, steps=8)
box("DaisRail", (6.75, 0.1, 0.06), (0.65, GALLERY_Y + 0.12, DZ + 0.59), M_FORM)
box("DaisPlinth", (6.75, 0.12, 0.06), (0.65, GALLERY_Y + 0.12, DZ + 0.03), M_JOIN)
# music stands, chairs, a bass viol on its side, a fiddle case open on a chair
def music_stand(name, x, y, yaw):
    F = Frame((x, y), yaw, z=DZ)
    F.cyl(f"{name}Pole", 0.012, 1.0, (0, 0, 0.55), M_FORM, verts=6)
    for k in range(3):
        a = 2 * math.pi * k / 3
        tube(f"{name}Foot{k}", [F.p(0, 0, 0.12), F.p(math.cos(a) * 0.22, math.sin(a) * 0.22, 0.0)], 0.01, M_FORM, sides=4)
    F.box(f"{name}Desk", (0.5, 0.02, 0.36), (0, -0.04, 1.12), M_FORM, rx=0.35)
    F.box(f"{name}Ledge", (0.5, 0.05, 0.02), (0, 0.04, 0.95), M_FORM)
    F.box(f"{name}Music", (0.42, 0.006, 0.3), (0, -0.065, 1.14), M_PAPER, rx=0.35)
for k, (x, y, yaw) in enumerate(((-1.4, 9.9, math.pi + 0.15), (0.0, 9.8, math.pi), (1.4, 9.9, math.pi - 0.2))):
    music_stand(f"Stand{k}", x, y, yaw)
    I.sabre_chair(f"MusicChair{k}", (x + 0.05, y + 0.65), math.pi + rng.uniform(-0.2, 0.2), M_FORM, M_BAIZE)
for o in [o for o in K.COLL.objects if o.name.startswith("MusicChair")]: o.location.z += DZ
# the bass viol (violoncello-like) leaning against the north wall behind the stands
VIOL = Vector((2.4, R.y1 - 0.35, DZ))
prof = [(0.0, 0.0), (0.17, 0.02), (0.21, 0.12), (0.19, 0.26), (0.13, 0.36), (0.15, 0.46), (0.20, 0.6), (0.17, 0.72), (0.08, 0.76), (0.0, 0.77)]
vb = lathe("ViolBody", prof, (0, 0, 0), M_VIOL, steps=18)
vb.scale = (1.0, 0.45, 1.0); vb.rotation_euler = (math.radians(-12), 0, 0); vb.location = VIOL + Vector((0, 0, 0.08))
cyl("ViolNeck", 0.022, 0.62, tuple(VIOL + Vector((0, -0.21, 1.05))), M_BLACK, verts=8, rot=(math.radians(-12), 0, 0))
cyl("ViolPeg", 0.008, 0.1, tuple(VIOL + Vector((0, 0, 0.04))), M_BLACK, verts=6)
# fiddle case on the third chair
box("FiddleCase", (0.22, 0.7, 0.1), (1.45, 10.55, DZ + 0.52), M_BLACK, rot=(0, 0, 0.3), bevel=0.02)

# ----------------------------------------------------------------------------- forms and chairs along the walls (where the ladies sit out)
def form(name, x, y, yaw, L=2.2):
    F = Frame((x, y), yaw)
    F.box(f"{name}Seat", (L, 0.38, 0.07), (0, 0, 0.44), M_BAIZE, bevel=0.025)
    F.box(f"{name}Rail", (L, 0.36, 0.06), (0, 0, 0.38), M_FORM, bevel=0.005)
    for sx in (-1, 1):
        for sy in (-1, 1):
            lathe(f"{name}Leg{sx}{sy}", [(0, 0), (0.022, 0), (0.026, 0.1), (0.02, 0.2), (0.025, 0.35), (0, 0.36)], F.p(sx * (L / 2 - 0.08), sy * 0.14, 0), M_FORM, steps=8)
    F.box(f"{name}Back", (L, 0.04, 0.32), (0, -0.2, 0.75), M_FORM, bevel=0.01, rx=-0.1)
    for k in range(int(L / 0.35)):
        F.box(f"{name}Spindle{k}", (0.02, 0.02, 0.3), (-L / 2 + 0.2 + k * 0.35, -0.19, 0.57), M_FORM)
FORMS = []
for k, y in enumerate((-1.6, 3.25, 6.6)):
    form(f"FormW{k}", R.x0 + 0.32, y, -math.pi / 2, L=2.5); FORMS.append((R.x0 + 0.32, y))
for k, y in enumerate((-1.6, 2.3, 5.7)):
    form(f"FormE{k}", R.x1 - 0.32, y, math.pi / 2, L=1.6); FORMS.append((R.x1 - 0.32, y))
for k, (x, y, yaw) in enumerate(((R.x0 + 0.35, 0.15, -math.pi / 2 + 0.1), (R.x0 + 0.4, 0.75, -math.pi / 2 - 0.25), (R.x0 + 0.35, 5.0, -math.pi / 2 + 0.15),
                                 (R.x1 - 0.4, 0.0, math.pi / 2 - 0.2), (R.x1 - 0.35, 7.6, math.pi / 2 + 0.2), (R.x0 + 0.38, 8.3, -math.pi / 2))):
    I.sabre_chair(f"WallChair{k}", (x, y), yaw, M_FORM, M_BAIZE)
# shawls, a fan, a pair of gloves left on the forms
def drape_shawl(name, x, y, z, yaw, mat, L=0.9):
    F = Frame((x, y), yaw, z=z); vs = []; fs = []
    nu, nv = 10, 6
    for j in range(nv + 1):
        for i in range(nu + 1):
            u = i / nu; v = j / nv
            px = (u - 0.5) * L; py = (v - 0.5) * 0.36
            pz = 0.02 + 0.012 * math.sin(u * 9 + v * 3)
            if v > 0.85: pz -= (v - 0.85) * 1.6; py = 0.18 + (v - 0.85) * 0.2
            vs.append(F.p(px, py, pz))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i; fs.append((a, a + 1, a + nu + 2, a + nu + 1))
    return mesh_from(name, vs, fs, mat, smooth=True)
drape_shawl("ShawlA", R.x0 + 0.32, 3.6, 0.48, -math.pi / 2, M_SHAWL1)
drape_shawl("ShawlB", R.x1 - 0.32, 5.4, 0.48, math.pi / 2, M_SHAWL2, L=0.7)
F_ = Frame((R.x0 + 0.33, 2.6), -math.pi / 2, z=0.485)
for k in range(9):                              # a folded fan, ribs spread a little
    a = -0.5 + k * 0.12
    F_.box(f"FanRib{k}", (0.012, 0.2, 0.003), (math.sin(a) * 0.1, math.cos(a) * 0.1, 0.0), M_SHAWL2, rx=0.0)

# ----------------------------------------------------------------------------- the refreshment table at the south end, by the door
RT = Vector((1.8, -2.3, 0))
box("RTableTop", (2.2, 0.75, 0.04), (RT.x, RT.y, 0.76), M_DEAL)
box("RTableCloth", (2.26, 0.81, 0.02), (RT.x, RT.y, 0.79), M_LINEN)
box("RTableDrop", (2.26, 0.02, 0.5), (RT.x, RT.y + 0.405, 0.55), M_LINEN)
for s in (-1, 1): box(f"RTableDropE{s}", (0.02, 0.81, 0.5), (RT.x + s * 1.13, RT.y, 0.55), M_LINEN)
for (lx, ly) in ((-1.0, -0.3), (1.0, -0.3), (-1.0, 0.3), (1.0, 0.3)): box(f"RTableLeg{lx}{ly}", (0.05, 0.05, 0.74), (RT.x + lx, RT.y + ly, 0.37), M_DEAL)
lathe("PunchBowl", [(0, 0), (0.09, 0), (0.1, 0.03), (0.07, 0.06), (0.22, 0.1), (0.25, 0.2), (0.0, 0.2)], (RT.x - 0.3, RT.y, 0.8), M_PUNCH, steps=24)
lathe("PunchLadle", [(0, 0), (0.04, 0.0), (0.045, 0.03), (0, 0.03)], (RT.x - 0.16, RT.y + 0.05, 1.0), M_BRASS, steps=10)
tube("PunchLadleHandle", [(RT.x - 0.16, RT.y + 0.05, 1.02), (RT.x - 0.05, RT.y + 0.12, 1.2)], 0.006, M_BRASS, sides=4)
for k in range(10):
    x = RT.x + 0.15 + (k % 5) * 0.14; y = RT.y - 0.15 + (k // 5) * 0.2
    lathe(f"Glass{k}", [(0, 0), (0.03, 0), (0.03, 0.006), (0.006, 0.015), (0.005, 0.06), (0.028, 0.08), (0.032, 0.13), (0, 0.13)], (x, y, 0.8), M_GLASS, steps=10)
for k, dx in enumerate((-0.95, 0.95)):
    I.candlestick(f"RTableStick{k}", (RT.x + dx, RT.y + 0.1, 0.8), M_BRASS, M_WAX, height=0.26, candle_h=0.18)

# ----------------------------------------------------------------------------- chandeliers and sconces
CANDLES = []
def chandelier(name, c, arms=8, r=0.55):
    """a plain country brass chandelier: a turned stem with a ball, one tier of S-scrolled arms with drip pans and
    candles, hung on a chain from a ceiling hook."""
    top = c + Vector((0, 0, 1.2))
    for k in range(10):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.025, minor_radius=0.006, major_segments=8, minor_segments=4, location=tuple(Vector((c.x, c.y, R.h - 0.03 - k * 0.04))),
                                         rotation=(0, math.pi / 2 * (k % 2), 0))
        K._finish(bpy.context.active_object, M_BRASS, smooth=True)
    stem_top = R.h - 0.43
    lathe(f"{name}Stem", [(0, 0), (0.06, 0.02), (0.13, 0.1), (0.11, 0.17), (0.04, 0.22), (0.03, 0.4), (0.06, 0.48), (0.03, 0.56), (0.025, 0.8), (0.04, 0.84), (0, 0.86)],
          (c.x, c.y, stem_top - 0.86), M_BRASS, steps=14)
    for k in range(arms):
        a = 2 * math.pi * k / arms; d = Vector((math.cos(a), math.sin(a), 0))
        p0 = Vector((c.x, c.y, stem_top - 0.72)); p3 = p0 + d * r + Vector((0, 0, 0.14))
        tube(f"{name}Arm{k}", [p0, p0 + d * 0.15 - Vector((0, 0, 0.08)), p0 + d * 0.38 - Vector((0, 0, 0.06)), p3 - Vector((0, 0, 0.06)), p3], 0.011, M_BRASS, sides=5)
        lathe(f"{name}Pan{k}", [(0, 0), (0.05, 0.01), (0.055, 0.02), (0.02, 0.02), (0.018, 0.05), (0, 0.05)], tuple(p3), M_BRASS, steps=10)
        h_ = rng.uniform(0.10, 0.2)
        cyl(f"{name}Candle{k}", 0.012, h_, tuple(p3 + Vector((0, 0, 0.05 + h_ / 2))), M_WAX, verts=8)
        CANDLES.append(p3 + Vector((0, 0, 0.05 + h_ + 0.012)))
    return Vector((c.x, c.y, stem_top - 0.6))
CHAND = [chandelier("Chand0", Vector((0.0, 0.2, 0))), chandelier("Chand1", Vector((0.0, 4.0, 0))), chandelier("Chand2", Vector((0.0, 7.8, 0)))]
SCON = []
for (w, u, c, n) in PIL:
    p = c + n * 0.06 + Vector((0, 0, 2.15))
    a = Vector((-n.y, n.x, 0))
    box(f"SconcePlate{w}{u}", (abs(n.x) * 0.02 + abs(a.x) * 0.14, abs(n.y) * 0.02 + abs(a.y) * 0.14, 0.28), tuple(p - n * 0.02), M_BRASS, bevel=0.01)
    for s in (-1, 1):
        q = p + n * 0.16 + a * s * 0.13 + Vector((0, 0, 0.0))
        tube(f"SconceArm{w}{u}{s}", [p, p + n * 0.08 + a * s * 0.05 - Vector((0, 0, 0.06)), q], 0.008, M_BRASS, sides=5)
        lathe(f"SconcePan{w}{u}{s}", [(0, 0), (0.04, 0.008), (0.018, 0.015), (0.015, 0.04), (0, 0.04)], tuple(q), M_BRASS, steps=8)
        cyl(f"SconceCandle{w}{u}{s}", 0.011, 0.15, tuple(q + Vector((0, 0, 0.115))), M_WAX, verts=8)
        CANDLES.append(q + Vector((0, 0, 0.2)))
    SCON.append(p + n * 0.16 + Vector((0, 0, 0.2)))
# render-only flame cards on every candle (Unity draws its own at fx.candle.*)
fl = K.MB()
for t in CANDLES:
    for a in (0.0, math.pi / 2):
        d = Vector((math.cos(a), math.sin(a), 0)) * 0.007
        i0 = fl.vert(t - d); i1 = fl.vert(t + d); i2 = fl.vert(t + Vector((0, 0, 0.03)) + d * 0.5); i3 = fl.vert(t + Vector((0, 0, 0.045))); i4 = fl.vert(t + Vector((0, 0, 0.03)) - d * 0.5)
        fl.face(i0, i1, i2, i3, i4)
FLAMES = fl.build("RenderFlames", M_FLAME, sway=False)
I.RENDER_ONLY.append(FLAMES)

# ----------------------------------------------------------------------------- lights, world, empties, anchors
for k, c in enumerate(CHAND): light_obj(f"light.chandelier{k + 1}", 'POINT', 70.0, (1.0, 0.70, 0.42), tuple(c), shadow_soft_size=0.45)
for k, p in enumerate(SCON): light_obj(f"light.sconce{k + 1}", 'POINT', 9.0, (1.0, 0.68, 0.40), tuple(p), shadow_soft_size=0.1)
light_obj("light.refreshments", 'POINT', 6.0, (1.0, 0.7, 0.42), (RT.x, RT.y + 0.1, 1.2), shadow_soft_size=0.3)
light_obj("light.passage", 'POINT', 12.0, (1.0, 0.68, 0.4), (-1.4, R.y0 - R.t - 1.3, 2.4), shadow_soft_size=0.1)
B.world_flat((0.006, 0.007, 0.01), 1.0)
for k, t in enumerate(CANDLES): B.fx(f"fx.candle.{k}", tuple(t), 0.012)
sound("crowd", "floor", (0.0, 3.5, 1.5))
sound("crowd", "door", (-1.4, R.y0 - 0.5, 1.5))

fwd = (LOOK_AT - READER); fwd.z = 0; fwd.normalize()
E = READER + Vector((0, 0, EYE))
B.reader_anchors(tuple(READER), tuple(E + fwd))
anchor("scene.centre", (0.0, 3.5, 0.0))
anchor("room.gallery", (0.0, 9.9, DZ))
anchor("room.door", (-1.4, R.y0, 0.0))
anchor("room.refreshments", tuple(RT))
page = B.page_preview(E, fwd)
K.apply_transforms()

def yawed(deg, dist=6.0, dz=-0.6):
    d = Matrix.Rotation(math.radians(-deg), 3, 'Z') @ fwd
    return tuple(E + d * dist + Vector((0, 0, dz)))
cams = [camera("Cam_Reader", tuple(E), yawed(0, 6, -0.5), lens=17), camera("Cam_Page", tuple(E), yawed(0, 6, -0.5), lens=17),
        camera("Cam_Left", tuple(E), yawed(-75, 6, -0.4), lens=17), camera("Cam_Right", tuple(E), yawed(75, 6, -0.4), lens=17),
        camera("Cam_Behind", tuple(E), yawed(180, 6, -0.4), lens=17),
        camera("Cam_Gallery", tuple(E + Vector((1.5, 1.0, 0))), (0.0, 10.0, 1.2), lens=22),
        camera("Cam_Long", (0.0, -2.2, 1.7), (0.0, 9.0, 1.4), lens=17)]
if not ARGS.nosave:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "meryton_assembly_room_source.blend"))
K.print_budget(exclude=("PagePreview", "RenderFlames"))
if ARGS.render:
    K.render_stills(cams, page=page, page_cams={"Cam_Page"}, default_exposure=0.8, captures_dir=ARGS.captures)
if ARGS.bake or ARGS.export:
    for o in I.RENDER_ONLY:
        if o.name in bpy.data.objects: bpy.data.objects.remove(o)
    B.export_room("meryton_assembly_room.gltf", cams, page=page,
                  keep_names={"M_Curtains": "cloth.curtain.windows", "M_WindowGlassNight": "WindowGlass_night"},
                  size_for={"M_ChalkFloor": (2048, 256, 1024), "M_WallPaint": (2048, 64, 1024), "M_Ceiling": (512, 32, 128), "M_Joinery": (1024, 128, 512),
                            "M_DealWood": (512, 128, 256), "M_FormWood": (1024, 256, 512), "M_FormCover": (512, 64, 256), "M_Brass": (256, 64, 128),
                            "M_Curtains": (512, 64, 256), "M_TableLinen": (256, 64, 128), "M_ViolVarnish": (256, 64, 128), "M_MusicPaper": (128, 32, 64),
                            "M_Wax": (64, 32), "M_WindowGlassNight": (32, 32), "M_Glassware": (64, 32), "M_PunchBowl": (64, 32), "M_Ebony": (64, 32)},
                  default_size=(128, 64, 128))
print("DONE")
