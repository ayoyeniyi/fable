# Ishmael's room at the Spouter-Inn, second floor: cold early daylight from a narrow street,
# the prodigious bed to the right, fireplace and sea gear to the left.
r = kit.rng()
wall_m = kit.mat("wall", (0.58, 0.56, 0.51), kind="plaster")
ceil_m = kit.mat("ceiling", (0.62, 0.60, 0.55), kind="plaster")
floor_m = kit.mat("boards", (0.34, 0.27, 0.20), kind="bark", rough=0.75)
seam_m = kit.mat("seams", (0.14, 0.11, 0.08), kind="bark", rough=0.9)
trim_m = kit.mat("trim", (0.42, 0.38, 0.33), kind="plaster", rough=0.6)
leaf_m = kit.mat("door", (0.40, 0.33, 0.25), kind="plaster", rough=0.6)
glass_m = kit.mat("glass", (0.66, 0.72, 0.76), kind="plaster", rough=0.05)
bedwood = kit.mat("bedwood", (0.30, 0.22, 0.15), kind="bark", rough=0.6)
linen = kit.mat("linen", (0.74, 0.71, 0.64), kind="fabric")
p_red = kit.mat("patch_red", (0.46, 0.27, 0.22), kind="fabric")
p_ind = kit.mat("patch_indigo", (0.27, 0.30, 0.38), kind="fabric")
p_och = kit.mat("patch_ochre", (0.58, 0.49, 0.32), kind="fabric")
p_crm = kit.mat("patch_cream", (0.70, 0.66, 0.56), kind="fabric")
p_grn = kit.mat("patch_green", (0.34, 0.37, 0.28), kind="fabric")
p_brn = kit.mat("patch_brown", (0.40, 0.31, 0.24), kind="fabric")
chest_m = kit.mat("seachest", (0.33, 0.27, 0.20), kind="bark", rough=0.65)
iron = kit.mat("iron", (0.18, 0.17, 0.16), kind="rock", rough=0.5)
soap = kit.mat("soap", (0.66, 0.60, 0.44), kind="plaster")
china = kit.mat("china", (0.78, 0.77, 0.73), kind="plaster", rough=0.2)
surround = kit.mat("surround", (0.36, 0.34, 0.31), kind="rock")
hearth_m = kit.mat("hearthstone", (0.24, 0.23, 0.22), kind="rock")
paper = kit.mat("fireboard", (0.56, 0.51, 0.40), kind="plaster")
sea_m = kit.mat("painted_sea", (0.30, 0.38, 0.40), kind="plaster")
whale_m = kit.mat("whale", (0.16, 0.16, 0.18), kind="plaster")
frame_m = kit.mat("frame", (0.28, 0.22, 0.16), kind="bark")
mirror_m = kit.mat("mirror", (0.62, 0.66, 0.70), kind="plaster", rough=0.05)
bone = kit.mat("bone", (0.78, 0.74, 0.62), kind="plaster")
shaft_m = kit.mat("shaft", (0.45, 0.37, 0.26), kind="bark", rough=0.6)
canvas = kit.mat("canvas", (0.58, 0.54, 0.45), kind="fabric")
wool = kit.mat("peacoat", (0.17, 0.18, 0.21), kind="fabric")
wax = kit.mat("tallow", (0.80, 0.76, 0.62), kind="plaster")
rug_m = kit.mat("ragrug", (0.30, 0.24, 0.20), kind="fabric")
house_w = kit.mat("house_opp", (0.44, 0.35, 0.30), kind="brick")
roof_m = kit.mat("slate", (0.26, 0.27, 0.29), kind="rock")
street_m = kit.mat("street", (0.32, 0.31, 0.29), kind="rock")

W, D, H = 5.0, 4.4, 2.5
room = kit.room("room", W, D, H, wall_m, floor_m, ceiling=ceil_m,
                openings=[{"wall": "e", "at": -0.9, "width": 1.0, "height": 1.35, "sill": 0.85},
                          {"wall": "s", "at": 1.5, "width": 0.85, "height": 2.0, "sill": 0.0}])
kit.panelling(room, trim_m, dado=0.85, skirting=0.18, cornice=0.12, panels=False, avoid=[("w", 0.0, 1.6)])
kit.windows(room, trim_m, glass_m, panes=(3, 2))
kit.doors(room, trim_m, leaf_m, open_deg=12)
for i, x in enumerate((-1.6, 0.0, 1.6)):
    kit.box(f"beam{i}", (0.16, D, 0.14), (x + r.uniform(-0.05, 0.05), 0, H - 0.14), bedwood)

# painted board wainscot below the dado, with board joints
WZ0, WZ1 = 0.18, 0.84
def wainscot(tag, a0, a1, axis, fixed, inward):
    L = a1 - a0
    mid = (a0 + a1) / 2
    if axis == "x":
        kit.box(f"wsc_{tag}", (L, 0.01, WZ1 - WZ0), (mid, fixed + inward * 0.005, WZ0), trim_m)
    else:
        kit.box(f"wsc_{tag}", (0.01, L, WZ1 - WZ0), (fixed + inward * 0.005, mid, WZ0), trim_m)
    t = a0 + r.uniform(0.08, 0.12)
    k = 0
    while t < a1 - 0.04:
        if axis == "x":
            kit.box(f"wsj_{tag}{k}", (0.008, 0.006, WZ1 - WZ0 - 0.02), (t, fixed + inward * 0.012, WZ0 + 0.01), seam_m)
        else:
            kit.box(f"wsj_{tag}{k}", (0.006, 0.008, WZ1 - WZ0 - 0.02), (fixed + inward * 0.012, t, WZ0 + 0.01), seam_m)
        t += r.uniform(0.10, 0.13)
        k += 1
wainscot("n", -2.45, 2.45, "x", D / 2, -1)
wainscot("s0", -2.45, 1.0, "x", -D / 2, 1)
wainscot("s1", 1.98, 2.45, "x", -D / 2, 1)
wainscot("e", -2.15, 2.15, "y", W / 2, -1)
wainscot("w0", -2.15, -0.75, "y", -W / 2, 1)
wainscot("w1", 0.75, 2.15, "y", -W / 2, 1)

# floorboard seams
x = -W / 2 + 0.17
i = 0
while x < W / 2 - 0.05:
    kit.box(f"seam{i}", (0.012, D - 0.02, 0.003), (x, 0, 0), seam_m)
    x += r.uniform(0.17, 0.23)
    i += 1
for i in range(6):
    sx = -2.2 + i * 0.8 + r.uniform(-0.2, 0.2)
    kit.box(f"butt{i}", (0.2, 0.012, 0.003), (sx, r.uniform(-1.8, 1.8), 0), seam_m)

# dim landing beyond the door
land = kit.room("landing", 2.4, 1.6, H, wall_m, floor_m, ceiling=ceil_m, centre=(1.5, -3.36),
                openings=[{"wall": "n", "at": 0.0, "width": 0.85, "height": 2.0, "sill": 0.0}])
kit.panelling(land, trim_m, dado=0.85, skirting=0.18, cornice=0.12, panels=False)
kit.box("threshold", (0.85, 0.42, 0.02), (1.5, -2.38, 0), floor_m)
kit.box("banister", (0.05, 1.2, 0.05), (2.3, -3.4, 0.9), bedwood)
for i in range(4):
    kit.box(f"baluster{i}", (0.03, 0.03, 0.9), (2.3, -3.9 + i * 0.32, 0), bedwood)
kit.lamp("landing_glow", (1.4, -3.5, 2.1), power=12, color=(0.85, 0.9, 1.0), radius=0.3)

# the prodigious bed
bx0, bx1, by0, by1 = 0.35, 2.35, 0.0, 2.1
cx = (bx0 + bx1) / 2
kit.box("headboard", (2.05, 0.06, 1.0), (cx, by1, 0), bedwood)
kit.box("footboard", (2.05, 0.06, 0.48), (cx, by0, 0), bedwood)
for i, (px, py, h) in enumerate([(bx0, by0, 0.72), (bx1, by0, 0.72), (bx0, by1, 1.12), (bx1, by1, 1.12)]):
    kit.cylinder(f"post{i}", 0.05, h, (px, py, 0), bedwood, sides=8)
for i, px in enumerate((bx0, bx1)):
    kit.box(f"rail{i}", (0.06, 2.1, 0.22), (px, 1.05, 0.12), bedwood)
kit.box("mattress", (1.94, 2.02, 0.30), (cx, 1.05, 0.28), linen, bevel=0.05)
kit.blob("pillow0", 0.3, (0.95, 1.83, 0.64), linen, squash=(1.2, 0.6, 0.35), seed=1)
kit.blob("pillow1", 0.3, (1.78, 1.86, 0.64), linen, squash=(1.2, 0.6, 0.35), seed=2)

# patchwork counterpane
pm = [p_red, p_ind, p_och, p_crm, p_grn, p_brn]
groups = {m.name: (m, [], []) for m in pm}
def add_poly(m, pts):
    g = groups[m.name]
    n = len(g[1])
    g[1].extend(pts)
    g[2].append(tuple(range(n, n + len(pts))))
nx, ny = 13, 10
x0, x1, y0, y1 = 0.37, 2.33, 0.04, 1.62
dx, dy = (x1 - x0) / nx, (y1 - y0) / ny
zt = 0.588
for i in range(nx):
    for j in range(ny):
        ax, ay = x0 + i * dx, y0 + j * dy
        z = zt + 0.004 * math.sin(i * 1.3 + j * 0.7)
        a, b, c, d = (ax, ay, z), (ax + dx, ay, z), (ax + dx, ay + dy, z), (ax, ay + dy, z)
        if r.random() < 0.45:
            m1 = r.choice(pm)
            m2 = r.choice([m for m in pm if m is not m1])
            if r.random() < 0.5:
                add_poly(m1, [a, b, c]); add_poly(m2, [a, c, d])
            else:
                add_poly(m1, [a, b, d]); add_poly(m2, [b, c, d])
        else:
            add_poly(r.choice(pm), [a, b, c, d])
for j in range(ny):
    ay = y0 + j * dy
    add_poly(r.choice(pm), [(0.372, ay, zt), (0.372, ay + dy, zt), (0.364, ay + dy, 0.36), (0.364, ay, 0.36)])
    add_poly(r.choice(pm), [(2.328, ay, zt), (2.336, ay, 0.36), (2.336, ay + dy, 0.36), (2.328, ay + dy, zt)])
for key in groups:
    m, vs, fs = groups[key]
    if fs:
        kit.mesh(f"counterpane_{key}", vs, fs, m)

# harpoon leaning at the head of the bed
hr = (-6, 0, 0)
hb = Vector((0.2, 1.85, 0.0))
hd = Euler((math.radians(-6), 0, 0)).to_matrix() @ Vector((0, 0, 1))
kit.cylinder("harpoon_shaft", 0.022, 2.2, tuple(hb), shaft_m, rot=hr, sides=6)
kit.cylinder("harpoon_socket", 0.03, 0.12, tuple(hb + hd * 2.12), iron, rot=hr, sides=6)
kit.cylinder("harpoon_head", 0.04, 0.3, tuple(hb + hd * 2.22), iron, rot=hr, sides=6, top_radius=0.002)

# fireplace with an upright papered fireboard: a man in a boat striking a whale
kit.fireplace("fireplace", (-W / 2, 0.0), surround, rot=90, width=1.3, height=1.15, fire=False, hearth_stone=hearth_m)
FX = -2.28
kit.box("fireboard", (0.02, 0.72, 0.62), (FX, 0.0, 0.03), paper)
PX = FX + 0.016
kit.box("fb_sea", (0.008, 0.68, 0.18), (PX, 0.0, 0.06), sea_m)
wv = []
cyw, czw = 0.10, 0.30
for k in range(14):
    t = 2 * math.pi * k / 14
    wv.append((PX + 0.006, cyw + 0.17 * math.cos(t), czw + 0.065 * math.sin(t) * (1.2 if math.cos(t) > 0 else 0.9)))
wf = [tuple(range(14))]
n0 = len(wv)
wv += [(PX + 0.006, -0.05, 0.30), (PX + 0.006, -0.15, 0.39), (PX + 0.006, -0.12, 0.30), (PX + 0.006, -0.15, 0.22)]
wf += [(n0, n0 + 1, n0 + 2), (n0, n0 + 2, n0 + 3)]
n1 = len(wv)
wv += [(PX + 0.006, 0.22, 0.36), (PX + 0.006, 0.20, 0.44), (PX + 0.006, 0.24, 0.44)]
wf += [(n1, n1 + 1, n1 + 2)]
n2 = len(wv)
wv += [(PX + 0.006, -0.34, 0.23), (PX + 0.006, -0.16, 0.23), (PX + 0.006, -0.19, 0.18), (PX + 0.006, -0.31, 0.18)]
wf += [(n2, n2 + 1, n2 + 2, n2 + 3)]
n3 = len(wv)
wv += [(PX + 0.006, -0.27, 0.23), (PX + 0.006, -0.23, 0.23), (PX + 0.006, -0.235, 0.37), (PX + 0.006, -0.265, 0.37)]
wf += [(n3, n3 + 1, n3 + 2, n3 + 3)]
n4 = len(wv)
wv += [(PX + 0.006, -0.25, 0.40), (PX + 0.006, -0.235, 0.41), (PX + 0.006, 0.0, 0.33), (PX + 0.006, -0.005, 0.32)]
wf += [(n4, n4 + 1, n4 + 2, n4 + 3)]
kit.mesh("fireboard_picture", wv, wf, whale_m)

# rude shelf with bone fish hooks
kit.box("rude_shelf", (0.18, 1.2, 0.03), (-W / 2 + 0.09, 0.02, 1.48), bedwood, rot=(0, 0, 1.5))
for i in range(6):
    y = -0.45 + i * 0.17 + r.uniform(-0.03, 0.03)
    kit.cylinder(f"hook{i}", 0.012, r.uniform(0.08, 0.14), (-2.43, y, 1.51), bone,
                 rot=(r.uniform(60, 90), 0, r.uniform(-30, 30)), sides=5)
    kit.blob(f"hookbarb{i}", 0.02, (-2.42, y + 0.03, 1.53), bone, squash=(1, 1.5, 0.7), seed=i)

# sea chest as washstand
kit.box("chest", (0.95, 0.52, 0.48), (-1.55, -0.4, 0), chest_m, bevel=0.02)
kit.box("chest_lid", (0.98, 0.55, 0.06), (-1.55, -0.4, 0.48), chest_m, bevel=0.015)
for i, ddx in enumerate((-0.32, 0.32)):
    kit.box(f"chest_band{i}", (0.04, 0.54, 0.49), (-1.55 + ddx, -0.4, 0.02), iron)
kit.cylinder("basin", 0.12, 0.09, (-1.70, -0.36, 0.54), china, sides=20, top_radius=0.19)
kit.cylinder("jug", 0.07, 0.22, (-1.32, -0.28, 0.54), china, sides=14, top_radius=0.05)
kit.box("soap", (0.08, 0.05, 0.03), (-1.30, -0.53, 0.54), soap, rot=(0, 0, 17))
kit.candle("candle_stub", (-1.92, -0.55, 0.54), wax, power=1, flame=False, height=0.07)

# lashed-up hammock: a lumpy bundle leaning in the corner, with lashings
ar = (-8, -8, 0)
ab = Vector((-2.2, 1.9, 0.0))
ad = Euler((math.radians(-8), math.radians(-8), 0)).to_matrix() @ Vector((0, 0, 1))
for i, t in enumerate((0.22, 0.6, 0.98, 1.36, 1.62)):
    p = ab + ad * t
    kit.blob(f"hammock{i}", 0.14 + r.uniform(-0.015, 0.02), tuple(p), canvas,
             squash=(1.0, 0.92, 1.45), roughness=0.3, seed=20 + i)
for i, t in enumerate((0.42, 0.8, 1.18, 1.5)):
    kit.cylinder(f"lashing{i}", 0.155, 0.03, tuple(ab + ad * t), bedwood, rot=ar, sides=10)

# seaman's bag with a drawn neck and cord
kit.blob("seabag", 0.3, (-1.8, 1.8, 0.33), canvas, squash=(0.9, 0.85, 1.2), roughness=0.32, seed=7)
kit.cylinder("seabag_neck", 0.11, 0.14, (-1.79, 1.8, 0.62), canvas, sides=9, top_radius=0.05)
kit.cylinder("seabag_cord", 0.08, 0.025, (-1.79, 1.8, 0.66), bedwood, sides=9)

# hanging coats: a tapered body with shoulders and collar, sleeves at the sides
def coat(name, cxp, wy, face, top, m, w=0.5, length=0.88):
    z0, z1, z2 = top - length, top - 0.14, top
    sk = r.uniform(-0.03, 0.03)
    rings = [(z0, w / 2, 0.13, sk), (z1, 0.24, 0.10, 0.0), (z2, 0.08, 0.05, 0.0)]
    vs = []
    for (z, hw, dp, off) in rings:
        vs += [(cxp - hw + off, wy, z), (cxp + hw + off, wy, z),
               (cxp + hw + off, wy + face * dp, z), (cxp - hw + off, wy + face * dp, z)]
    fs = [(0, 3, 2, 1), (8, 9, 10, 11)]
    for a, b in ((0, 4), (4, 8)):
        for k in range(4):
            fs.append((a + k, a + (k + 1) % 4, b + (k + 1) % 4, b + k))
    kit.mesh(name, vs, fs, m)
    for s, sx in enumerate((-1, 1)):
        kit.box(f"{name}_sleeve{s}", (0.1, 0.09, 0.6), (cxp + sx * 0.26, wy + face * 0.07, top - 0.76), m,
                rot=(0, sx * 3, 0), bevel=0.03)

kit.box("pegrail_s", (1.8, 0.03, 0.08), (-0.9, -2.185, 1.70), bedwood)
for i, px in enumerate((-1.6, -1.1, -0.6, -0.15)):
    kit.cylinder(f"peg_s{i}", 0.015, 0.1, (px, -2.17, 1.74), bedwood, rot=(90, 0, 0), sides=6)
coat("peacoat", -1.1, -2.165, 1, 1.74, wool)
kit.blob("bag_hung", 0.16, (-0.15, -2.08, 1.48), canvas, squash=(0.9, 0.5, 1.4), roughness=0.3, seed=12)
kit.cylinder("hat_crown", 0.1, 0.12, (-1.6, -2.07, 1.62), wool, sides=12, top_radius=0.09)
kit.cylinder("hat_brim", 0.16, 0.012, (-1.6, -2.07, 1.62), wool, sides=14)
kit.picture("print_s", (0.5, -D / 2, 1.5), (0.34, 0.26), frame_m, sea_m, rot=180, depth=0.03)
kit.box("pegrail_n", (0.6, 0.03, 0.08), (-0.25, D / 2 - 0.015, 1.72), bedwood)
kit.cylinder("peg_n0", 0.015, 0.1, (-0.05, D / 2 - 0.02, 1.76), bedwood, rot=(-90, 0, 0), sides=6)
coat("oilskin", -0.05, D / 2 - 0.035, -1, 1.76, canvas, w=0.46, length=0.8)

# small things that make it lived in
kit.picture("mirror_glass", (-1.25, D / 2, 1.55), (0.2, 0.26), frame_m, mirror_m, rot=0, depth=0.02)
kit.box("sailing_bill", (0.27, 0.006, 0.36), (1.35, D / 2 - 0.004, 1.45), paper, rot=(0, 3, 0))
kit.box("bill_band", (0.2, 0.004, 0.03), (1.35, D / 2 - 0.009, 1.72), whale_m, rot=(0, 3, 0))
kit.rug("ragrug", (-0.45, -0.75), (1.0, 0.7), rug_m, rot=4, border=p_ind)
kit.chair("chair", (1.9, -1.55), bedwood, rot=200)
kit.blob("jacket", 0.22, (1.88, -1.6, 0.55), canvas, squash=(1.0, 0.8, 0.35), seed=5)
kit.box("boot0", (0.1, 0.26, 0.2), (0.6, -0.35, 0), chest_m, rot=(0, 0, 12), bevel=0.03)
kit.box("boot1", (0.1, 0.26, 0.2), (0.78, -0.4, 0), chest_m, rot=(0, 0, -5), bevel=0.03)

# the inn below, the narrow street far down, the house opposite close by
kit.box("inn_below", (W + 0.6, D + 3.4, 4.25), (0, -0.9, -4.27), house_w)
kit.box("street", (8, 30, 0.1), (5.5, 0, -4.4), street_m)
opp = kit.house("opposite", (9.6, -1.0), (10, 8), house_w, roof_m, trim_m, glass_m, storeys=3, rot=-90,
                roof_kind="gable", detail=1, seed=2)
for o in opp:
    o.location.z -= 4.3

# cold dawn light: sun low in the east, the house opposite shading the window
kit.sky((0.46, 0.58, 0.76), (0.80, 0.83, 0.86), strength=0.7)
kit.sun(9, 10, strength=2.2, color=(1.0, 0.90, 0.78))
kit.area_light("window_light", (2.3, -0.9, 1.5), (1.0, 1.3), 140, color=(0.82, 0.89, 1.0), aim=(-1, 0, -0.25))
kit.area_light("ceiling_fill", (0.0, 0.2, 2.3), (2.0, 2.0), 11, color=(0.86, 0.90, 1.0), aim=(0, 0, -1))
kit.reader((-0.6, -1.2), (-0.6, 2.2, 1.4))
