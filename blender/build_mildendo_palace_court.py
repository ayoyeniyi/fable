"""
Fable step-in room `mildendo-palace-court`: the inmost court of the emperor's palace at Mildendo (Gulliver's Travels,
Part I, Chapter IV).

"The emperor's palace is in the centre of the city where the two great streets meet ... The outward court is a
square of forty feet, and includes two other courts: in the inmost are the royal apartments ... the buildings of the
outer court were at least five feet high ... the walls were strongly built of hewn stone, and four inches thick ...
Of these trees I made two stools, each about three feet high ... I stepped over the building very conveniently from
one stool to the other, and drew up the first after me with a hooked stick. By this contrivance I got into the
inmost court; and, lying down upon my side, I applied my face to the windows of the middle stories, which were left
open on purpose, and discovered the most splendid apartments that can be imagined."

The reader is Gulliver-size: everything is built at 1/12 (a Lilliputian storey is about 0.35 m, a man about 0.15 m).
They stand in the inmost court, a paved square about 8 x 8 m, beside one of Gulliver's two rough stools of
royal-park timber (0.9 m high), the hooked stick leaning on it, the other stool across the court. Ahead, the range of
the royal apartments: hewn pale stone, a rusticated arcade, a piano nobile whose tall windows stand open at knee to
waist height showing gilded, damask-hung rooms lit warm, a second storey and attic, a balustrade and a slate mansard
with dormers, a pedimented centre. Lower ranges east and west (over whose roofs the outer court's ranges show), the
gate range behind with its carved gate 18 inches high, corner pavilions with gilt-capped domes and flags, a little
fountain and four parterre beds of clipped box and flowers. Mid-morning sun, short shadows.
No people (the empress and princes are not modelled), no fire damage (chapter V), no fleet, no coat.

Run (from the repo root):
  blender -b -P blender/build_mildendo_palace_court.py -- --cpu --render --samples 40 --res 1280
  blender -b -P blender/build_mildendo_palace_court.py -- --export
  then blender/runtime_bake.py and tools/publish_scene_room.py (docs/SCENE_ROOMS_PIPELINE.md)
Axes: metres, +Z up; the reader faces +Y (north), the royal apartments' facade is y = 4.5.
"""
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_kit_b3 as K
import roomkit as rk
import alice_foliage as af
import pride_kit as pk

ARGS = K.setup("mildendo-palace-court", seed=1726, samples=40)
if ARGS.cpu: bpy.context.scene.cycles.device = 'CPU'
R = random.Random(1726)


# ----------------------------------------------------------------------------- materials
def ashlar_mat(name, base, block=(0.05, 0.025), mortar=(0.70, 0.66, 0.58), rough=0.82, joint=0.04, var=0.10, dark_low=True, floor=False):
    """Hewn stone at 1/12: brick-texture coursing on the wall plane (along the wall, height), each block a little
    different in tone, fine noise, grime toward the ground."""
    m = bpy.data.materials.new("M_" + name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    N = nt.nodes.new; L = nt.links.new
    out = N("ShaderNodeOutputMaterial"); b = N("ShaderNodeBsdfPrincipled"); L(b.outputs["BSDF"], out.inputs["Surface"])
    tc = N("ShaderNodeTexCoord"); sp = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sp.inputs["Vector"])
    ad = N("ShaderNodeMath"); ad.operation = 'ADD'; L(sp.outputs["X"], ad.inputs[0]); L(sp.outputs["Y"], ad.inputs[1])
    cb = N("ShaderNodeCombineXYZ")
    if floor: L(sp.outputs["X"], cb.inputs["X"]); L(sp.outputs["Y"], cb.inputs["Y"])
    else: L(ad.outputs[0], cb.inputs["X"]); L(sp.outputs["Z"], cb.inputs["Y"])
    bt = N("ShaderNodeTexBrick"); L(cb.outputs["Vector"], bt.inputs["Vector"])
    bt.inputs["Scale"].default_value = 1.0; bt.inputs["Mortar Size"].default_value = block[1] * joint
    bt.inputs["Brick Width"].default_value = block[0]; bt.inputs["Row Height"].default_value = block[1]
    bt.offset = 0.5; bt.squash = 1.0
    c0 = rk.lin(base)
    bt.inputs["Color1"].default_value = tuple(x * (1 - var) for x in c0) + (1,)
    bt.inputs["Color2"].default_value = tuple(min(1, x * (1 + var * 0.6)) for x in c0) + (1,)
    bt.inputs["Mortar"].default_value = rk.lin(mortar) + (1,)
    bt.inputs["Bias"].default_value = 0.0
    n1 = N("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 30.0; n1.inputs["Detail"].default_value = 6
    L(tc.outputs["Object"], n1.inputs["Vector"])
    mx = N("ShaderNodeMix"); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs["Factor"].default_value = 0.35
    L(bt.outputs["Color"], mx.inputs["A"]); L(n1.outputs["Color"], mx.inputs["B"])
    col = mx.outputs["Result"]
    n2 = N("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 2.0; n2.inputs["Detail"].default_value = 3
    L(tc.outputs["Object"], n2.inputs["Vector"])
    mr = N("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.45; mr.inputs["From Max"].default_value = 0.7; mr.inputs["To Max"].default_value = 0.25
    L(n2.outputs["Fac"], mr.inputs["Value"])
    m2 = N("ShaderNodeMix"); m2.data_type = 'RGBA'; L(mr.outputs["Result"], m2.inputs["Factor"]); L(col, m2.inputs["A"])
    m2.inputs["B"].default_value = tuple(x * 0.72 for x in c0) + (1,); col = m2.outputs["Result"]
    if dark_low:
        gr = N("ShaderNodeMapRange"); gr.inputs["From Min"].default_value = 0.0; gr.inputs["From Max"].default_value = 0.25
        gr.inputs["To Min"].default_value = 0.35; gr.inputs["To Max"].default_value = 0.0; L(sp.outputs["Z"], gr.inputs["Value"])
        m3 = N("ShaderNodeMix"); m3.data_type = 'RGBA'; m3.blend_type = 'MULTIPLY'; L(gr.outputs["Result"], m3.inputs["Factor"])
        L(col, m3.inputs["A"]); m3.inputs["B"].default_value = (0.55, 0.52, 0.47, 1); col = m3.outputs["Result"]
    L(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    bp = N("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5; bp.inputs["Distance"].default_value = 0.002; bp.invert = True
    L(bt.outputs["Fac"], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    m["base"] = list(c0); rk._mats[name] = m
    return m


STONE = ashlar_mat("hewn_stone", (0.80, 0.75, 0.64))
RUST = ashlar_mat("rusticated", (0.74, 0.69, 0.58), block=(0.08, 0.036), joint=0.12, mortar=(0.40, 0.37, 0.32))
PAVE = ashlar_mat("court_paving", (0.66, 0.63, 0.56), block=(0.075, 0.075), joint=0.07, mortar=(0.42, 0.40, 0.36), var=0.16, dark_low=False, floor=True)
SLATE = ashlar_mat("slate", (0.27, 0.29, 0.33), block=(0.028, 0.022), joint=0.15, mortar=(0.14, 0.15, 0.17), var=0.2, rough=0.55, dark_low=False)
TRIM = K.mat("stone_trim", (0.86, 0.82, 0.72), "stone", rough=0.75)
GILT = K.mat("gilt", (0.83, 0.62, 0.26), "metal", rough=0.3)
GLASS = K.mat("window_glass", (0.06, 0.08, 0.10), "glass", rough=0.06)
FRAME = K.mat("window_paint", (0.86, 0.85, 0.80), "plaster", rough=0.5)
SHUTTER = K.mat("shutter_green", (0.18, 0.30, 0.22), "plaster", rough=0.55)
DAMASK = K.mat("damask", (0.62, 0.12, 0.09), "fabric", rough=0.75)
INTERIOR_DARK = K.mat("interior_shade", (0.20, 0.12, 0.08), "wood", rough=0.7)
LUSTRE = K.emit_mat("chandelier_lights", (1.0, 0.85, 0.6), 6.0)
GATEWOOD = K.mat("gate_oak", (0.32, 0.20, 0.10), "wood", rough=0.6)
TIMBER = K.mat("stool_timber", (0.42, 0.33, 0.22), "bark", rough=0.85)
SAWN = K.mat("stool_endgrain", (0.62, 0.50, 0.34), "wood", rough=0.8)
LEAD = K.mat("lead_roofing", (0.36, 0.38, 0.40), "metal", rough=0.6)
WATER = K.mat("fountain_water", (0.10, 0.15, 0.17), "water", rough=0.05)
FLAGM = K.mat("flag_silk", (0.60, 0.10, 0.12), "fabric", rough=0.7)
SOIL = K.mat("bed_soil", (0.28, 0.21, 0.15), "soil", rough=0.95)
box_leaf = K.mat("box_hedge", (0.17, 0.27, 0.11), "foliage", rough=0.8)
flowers = K.mat("flowers", (0.85, 0.55, 0.62), "fabric", rough=0.7)
K.size(STONE, 2048, 256); K.size(RUST, 1024, 128); K.size(PAVE, 2048, 256); K.size(SLATE, 1024, 128)
K.keep(WATER, "water.pond.fountain"); K.keep(FLAGM, "cloth.flag.palace")

# ----------------------------------------------------------------------------- the court floor
CX0, CX1, CY0, CY1 = -4.0, 4.0, -3.5, 4.5
rk.box("court_floor", (40.0, 40.0, 0.1), (0, 0, -0.1), PAVE)
rk._ground.append(lambda x, y: 0.0)
K.sky((0.33, 0.52, 0.82), (0.80, 0.84, 0.88), strength=1.0, radius=900, ground_color=(0.42, 0.44, 0.36))
# a gentle green countryside beyond, under the far rooftops
K.polar_terrain("countryside", lambda x, y: -0.05 + 6.0 * K.smoothstep(150, 600, math.hypot(x, y)) * (0.6 + 0.4 * K.fbm(x, y, 120, 3, 2.0)),
                K.mat("fields", (0.36, 0.42, 0.22), "grass", rough=0.95), r_min=20.0, r_max=850, near_step=4.0, k=0.2, ns=48)


# ----------------------------------------------------------------------------- facades
def window(B, x, z, w, h, depth, open_=False, shutters=False, pediment=None):
    """A window in the facade plane y = 0 (outward +y): a stone surround (four strips), glass and glazing bars, a
    sill; or, open, its frame lining the opening and the two casements swung out into the court."""
    for sx in (-1, 1): B.box(TRIM, (0.02, 0.012, h + 0.02), (x + sx * (w / 2 + 0.01), 0.006, z - 0.01))
    B.box(TRIM, (w + 0.04, 0.012, 0.02), (x, 0.006, z + h))
    B.box(TRIM, (w + 0.06, 0.03, 0.014), (x, 0.012, z - 0.022))                  # sill
    if pediment == "tri":
        B.mesh(TRIM, [(x - w / 2 - 0.03, 0.014, z + h + 0.02), (x + w / 2 + 0.03, 0.014, z + h + 0.02), (x, 0.014, z + h + 0.07)], [(0, 1, 2)])
        B.box(TRIM, (w + 0.07, 0.02, 0.012), (x, 0.01, z + h + 0.012))
    elif pediment == "flat":
        B.box(TRIM, (w + 0.07, 0.025, 0.016), (x, 0.012, z + h + 0.016))
    if not open_:
        B.box(GLASS, (w, 0.004, h), (x, 0.004, z))
        B.box(FRAME, (w, 0.004, 0.008), (x, 0.007, z + h * 0.62))
        B.box(FRAME, (0.007, 0.004, h), (x, 0.007, z))
        if shutters:
            for sx in (-1, 1): B.box(SHUTTER, (w * 0.5, 0.005, h), (x + sx * (w * 0.75 + 0.022), 0.015, z))
        return
    for sx in (-1, 1):
        B.box(FRAME, (0.012, depth, h), (x + sx * (w / 2 - 0.006), -depth / 2, z))
        hinge = Vector((x + sx * w / 2, 0.0, z))
        L = w / 2
        c = hinge + Vector((-sx * math.cos(math.radians(70)) * L / 2, math.sin(math.radians(70)) * L / 2, 0))
        B.box(FRAME, (L, 0.008, h), (c.x, c.y, z), (0, 0, -sx * 70))
        B.box(GLASS, (L * 0.8, 0.01, h * 0.88), (c.x, c.y, z + h * 0.06), (0, 0, -sx * 70))
    B.box(FRAME, (w, depth, 0.012), (x, -depth / 2, z + h - 0.012))


def royal_room(B, x0, x1, z0, z1, depth):
    """A splendid apartment behind the open windows: damask hangings, gilt dado and cornice, pier glasses, a small
    crystal chandelier and a gilt table, all at 1/12."""
    B.box(DAMASK, (x1 - x0, 0.01, z1 - z0), ((x0 + x1) / 2, -depth, z0))                    # back wall
    for xx in (x0, x1): B.box(DAMASK, (0.01, depth, z1 - z0), (xx, -depth / 2, z0))
    B.box(INTERIOR_DARK, (x1 - x0, depth, 0.01), ((x0 + x1) / 2, -depth / 2, z0 - 0.01))   # parquet
    B.box(STONE, (x1 - x0, depth, 0.01), ((x0 + x1) / 2, -depth / 2, z1))                  # ceiling
    B.box(GILT, (x1 - x0, 0.012, 0.012), ((x0 + x1) / 2, -depth + 0.006, z1 - 0.014))     # cornice
    B.box(GILT, (x1 - x0, 0.008, 0.008), ((x0 + x1) / 2, -depth + 0.006, z0 + 0.07))      # dado rail
    k = 0; xx = x0 + 0.25
    while xx < x1 - 0.2:
        # a gilt-framed pier glass or portrait on the back wall, a console table below it
        B.box(GILT, (0.10, 0.006, 0.16), (xx, -depth + 0.008, z0 + 0.13))
        B.box(GLASS if k % 2 else DAMASK, (0.085, 0.004, 0.14), (xx, -depth + 0.012, z0 + 0.14))
        B.box(GILT, (0.09, 0.04, 0.006), (xx, -depth + 0.03, z0 + 0.065))
        for lx in (-0.035, 0.035): B.box(GILT, (0.004, 0.004, 0.06), (xx + lx, -depth + 0.03, z0 + 0.005))
        xx += 0.42; k += 1
    # chandeliers: a gilt ring of lights hanging from the ceiling
    xx = x0 + 0.42
    while xx < x1 - 0.3:
        c = Vector((xx, -depth * 0.5, z1 - 0.09))
        B.box(GILT, (0.002, 0.002, 0.08), (c.x, c.y, c.z))
        for j in range(6):
            a = 2 * math.pi * j / 6
            B.ball(LUSTRE, 0.005, (c.x + math.cos(a) * 0.025, c.y + math.sin(a) * 0.025, c.z + 0.004), sub=0)
        B.ball(GILT, 0.012, (c.x, c.y, c.z - 0.006), squash=(1, 1, 0.6), sub=0)
        xx += 0.84


def range_front(name, origin, yaw, length, storeys, bay, open_bays=(), centre_bays=0, eave=None, roof=0.45, rust=True,
                depth=1.4, dormers=True, interior=False, balustrade=False):
    """A palace range seen from the court: its facade in the local plane y = 0 (the court side is +y), body behind.
    storeys: [(height, kind)] bottom up; kind 'arcade' (rusticated, arched openings), 'nobile' (tall windows with
    pediments), 'plain', 'attic' (square windows)."""
    B = rk._B(name, origin, yaw)
    nb = int(length / bay); x0 = -nb * bay / 2
    z = 0.0
    zs = []
    for (h, kind) in storeys:
        zs.append((z, h, kind)); z += h
    top = z
    # the body: a solid block behind the facade; where windows stand open, a front skin with piers round them and a
    # gallery recessed behind (built by royal_room)
    if open_bays:
        rec = 0.55
        zn, hn = [(z0, h) for (z0, h, k) in zs if k == "nobile"][0]
        zl, zh = zn + hn * 0.12, zn + hn * 0.12 + hn * 0.72
        w_ = bay * 0.42
        i0, i1 = min(open_bays), max(open_bays)
        xa, xb = x0 + bay * i0, x0 + bay * (i1 + 1)
        B.box(STONE, (length, depth - rec, top), (0, -rec - (depth - rec) / 2, 0.0))
        B.box(STONE, (length, rec, zl), (0, -rec / 2, 0.0))
        B.box(STONE, (length, rec, top - zh), (0, -rec / 2, zh))
        B.box(STONE, (xa + length / 2, rec, zh - zl), ((-length / 2 + xa) / 2, -rec / 2, zl))
        B.box(STONE, (length / 2 - xb, rec, zh - zl), ((length / 2 + xb) / 2, -rec / 2, zl))
        for i in range(i0, i1 + 1):
            xc = x0 + bay * (i + 0.5)
            if i in open_bays:
                for sx in (-1, 1):
                    B.box(STONE, (bay / 2 - w_ / 2, rec, zh - zl), (xc + sx * (bay / 2 + w_ / 2) / 2, -rec / 2, zl))
            else:
                B.box(STONE, (bay, rec, zh - zl), (xc, -rec / 2, zl))
    else:
        B.box(STONE, (length, depth, top), (0, -depth / 2, 0.0))
    if centre_bays:
        cw = centre_bays * bay + 0.06
        if open_bays:
            # the projecting centre, open where its piano-nobile windows are
            B.box(STONE, (cw, 0.06, zl), (0, 0.03, 0.0))
            B.box(STONE, (cw, 0.06, top + 0.08 - zh), (0, 0.03, zh))
            for i in range(nb):
                xc = x0 + bay * (i + 0.5)
                if abs(i - (nb - 1) / 2) >= centre_bays / 2: continue
                for sx in (-1, 1):
                    edge = xc + sx * w_ / 2; far = xc + sx * bay / 2
                    if abs(far) > cw / 2: far = sx * cw / 2
                    B.box(STONE, (abs(far - edge), 0.06, zh - zl), ((far + edge) / 2, 0.03, zl))
        else:
            B.box(STONE, (cw, 0.06, top + 0.08), (0, 0.03, 0.0))
    # storeys
    for (z0, h, kind) in zs:
        if kind == "arcade":
            if rust: B.box(RUST, (length, 0.012, h), (0, 0.006, z0))
        else:
            B.box(TRIM, (length + 0.02, 0.02, 0.018), (0, 0.01, z0 - 0.002))    # string course
        for i in range(nb):
            x = x0 + bay * (i + 0.5)
            inc = abs(i - (nb - 1) / 2) < centre_bays / 2
            yoff = 0.06 if (centre_bays and inc) else 0.0
            if kind == "arcade":
                w_, hh = bay * 0.5, h * 0.72
                B.box(INTERIOR_DARK, (w_, 0.014, hh), (x, 0.004 + yoff, z0))
                B.box(TRIM, (w_ + 0.03, 0.02, 0.025), (x, 0.012 + yoff, z0 + hh))
            elif kind == "nobile":
                w_, hh = bay * 0.42, h * 0.72
                op = i in open_bays
                if op:
                    # cut the opening: a dark gap in the body for the room (built separately)
                    pass
                window(_Shift(B, yoff), x, z0 + h * 0.12, w_, hh, 0.12, open_=op, shutters=False, pediment="tri" if i % 2 == 0 else "flat")
            elif kind == "plain":
                window(_Shift(B, yoff), x, z0 + h * 0.18, bay * 0.38, h * 0.62, 0.1, shutters=True, pediment=None)
            elif kind == "attic":
                window(_Shift(B, yoff), x, z0 + h * 0.2, bay * 0.3, h * 0.48, 0.1)
        # pilasters between bays on the upper storeys
        if kind in ("nobile", "plain"):
            for i in range(nb + 1):
                x = x0 + bay * i
                B.box(TRIM, (0.035, 0.018, h - 0.02), (x, 0.009, z0 + 0.01))
    # cornice, balustrade, roof
    B.box(TRIM, (length + 0.08, 0.07, 0.035), (0, 0.0, top))
    B.box(TRIM, (length + 0.06, 0.05, 0.02), (0, -0.01, top + 0.035))
    bh = 0.075
    B.box(TRIM, (length, 0.04, 0.012), (0, -0.02, top + 0.055 + bh))
    B.box(TRIM, (length, 0.04, 0.012), (0, -0.02, top + 0.055))
    if balustrade:
        nbal = int(length / 0.034)
        for i in range(nbal):
            xx = -length / 2 + 0.017 + i * length / nbal
            if i % 12 == 0: B.box(TRIM, (0.03, 0.04, bh), (xx, -0.02, top + 0.067)); continue
            B.box(TRIM, (0.011, 0.011, bh), (xx, -0.02, top + 0.067), (0, 0, 45))
    else:
        B.box(TRIM, (length, 0.04, bh), (0, -0.02, top + 0.067))
    for i in range(0, nb + 1, 2):
        xx = x0 + bay * i
        B.ball(GILT, 0.012, (xx, -0.02, top + 0.067 + bh + 0.025), sub=0)        # gilt urns on the balustrade
    # mansard of slate, set back behind the balustrade, with dormers and chimneys
    rb = top + 0.06
    B.mesh(SLATE, [(-length / 2, -0.06, rb), (length / 2, -0.06, rb), (length / 2 - 0.1, -0.06 - roof * 0.45, rb + roof),
                   (-length / 2 + 0.1, -0.06 - roof * 0.45, rb + roof)], [(0, 1, 2, 3)])
    B.mesh(LEAD, [(-length / 2 + 0.1, -0.06 - roof * 0.45, rb + roof), (length / 2 - 0.1, -0.06 - roof * 0.45, rb + roof),
                  (length / 2 - 0.1, -depth + 0.1, rb + roof), (-length / 2 + 0.1, -depth + 0.1, rb + roof)], [(0, 1, 2, 3)])
    B.mesh(SLATE, [(length / 2, -depth, rb), (-length / 2, -depth, rb), (-length / 2 + 0.1, -depth + 0.1, rb + roof),
                   (length / 2 - 0.1, -depth + 0.1, rb + roof)], [(0, 1, 2, 3)])
    for sx in (-1, 1):
        B.mesh(SLATE, [(sx * length / 2, -0.06, rb), (sx * length / 2, -depth, rb), (sx * (length / 2 - 0.1), -depth + 0.1, rb + roof),
                       (sx * (length / 2 - 0.1), -0.06 - roof * 0.45, rb + roof)], [(0, 1, 2, 3)] if sx < 0 else [(3, 2, 1, 0)])
    if dormers:
        for i in range(1, nb, 2):
            x = x0 + bay * (i + 0.5)
            dz = rb + roof * 0.25
            B.box(STONE, (bay * 0.34, 0.08, roof * 0.42), (x, -0.06 - roof * 0.12, dz))
            B.box(GLASS, (bay * 0.2, 0.01, roof * 0.26), (x, -0.06 - roof * 0.12 + 0.04, dz + 0.02))
            B.mesh(SLATE, [(x - bay * 0.2, -0.02 - roof * 0.12, dz + roof * 0.42), (x + bay * 0.2, -0.02 - roof * 0.12, dz + roof * 0.42),
                           (x, -0.02 - roof * 0.12, dz + roof * 0.58)], [(0, 1, 2)])
    for xx in (-length * 0.32, length * 0.05, length * 0.36):
        B.box(STONE, (0.12, 0.08, roof * 0.7), (xx, -depth * 0.55, rb + roof * 0.7))
        B.box(TRIM, (0.14, 0.1, 0.02), (xx, -depth * 0.55, rb + roof * 1.4))
    if centre_bays:
        # a pediment over the centre with a gilt cartouche
        cw = centre_bays * bay + 0.06
        B.mesh(TRIM, [(-cw / 2, 0.06, top + 0.04), (cw / 2, 0.06, top + 0.04), (0, 0.06, top + 0.04 + cw * 0.22)], [(0, 1, 2)])
        B.mesh(STONE, [(-cw / 2, -0.2, top + 0.04), (cw / 2, -0.2, top + 0.04), (0, -0.2, top + 0.04 + cw * 0.22)], [(1, 0, 2)])
        B.mesh(SLATE, [(-cw / 2 - 0.02, 0.07, top + 0.04), (0, 0.07, top + 0.05 + cw * 0.22), (0, -0.2, top + 0.05 + cw * 0.22), (-cw / 2 - 0.02, -0.2, top + 0.04)], [(0, 1, 2, 3)])
        B.mesh(SLATE, [(cw / 2 + 0.02, 0.07, top + 0.04), (cw / 2 + 0.02, -0.2, top + 0.04), (0, -0.2, top + 0.05 + cw * 0.22), (0, 0.07, top + 0.05 + cw * 0.22)], [(0, 1, 2, 3)])
        B.ball(GILT, 0.045, (0, 0.065, top + 0.04 + cw * 0.09), squash=(1.3, 0.2, 1.0), sub=1)
        B.ball(GILT, 0.02, (0, 0.06, top + 0.06 + cw * 0.22), sub=0)
    return B, x0, zs, top


class _Shift:
    """A view of a part builder whose local y is pushed out by dy (the projecting centre bays)."""
    def __init__(self, B, dy): self.B = B; self.dy = dy
    def box(self, m, size, loc, rot=(0, 0, 0), **k): self.B.box(m, size, (loc[0], loc[1] + self.dy, loc[2]), rot, **k)
    def mesh(self, m, verts, faces): self.B.mesh(m, [(v[0], v[1] + self.dy, v[2]) for v in verts], faces)


# the royal apartments, north: arcade, piano nobile (open windows), second storey, attic
NB = [(0.36, "arcade"), (0.44, "nobile"), (0.34, "plain"), (0.24, "attic")]
BAY = 0.42
OPEN = {5, 7, 8, 9, 10, 11, 13}
BN, x0n, zsn, topn = range_front("royal_apartments", (0, CY1, 0), 180, 8.0 + 2 * 0.0, NB, BAY, open_bays=OPEN, centre_bays=3, roof=0.5, depth=1.6, balustrade=True)
BN.done()
z_nob = zsn[1][0]
RM = rk._B("royal_rooms", (0, CY1, 0), 180)
# the open run: windows 5..13 centred; the apartment rooms span them, set into a recess 0.5 m deep
xa = x0n + BAY * min(OPEN); xb = x0n + BAY * (max(OPEN) + 1)
royal_room(RM, xa + 0.01, xb - 0.01, z_nob + 0.44 * 0.12 - 0.02, z_nob + 0.44 * 0.9, 0.54)
RM.done()

# east and west ranges, lower: arcade, first floor, second floor, no dormers on the west
BE, *_ = range_front("east_range", (CX1, 0.5, 0), 90, 8.0, [(0.32, "arcade"), (0.34, "plain"), (0.28, "attic")], BAY, roof=0.36, depth=1.4)
BE.done()
BW, *_ = range_front("west_range", (CX0, 0.5, 0), -90, 8.0, [(0.32, "arcade"), (0.34, "plain"), (0.28, "attic")], BAY, roof=0.36, depth=1.4)
BW.done()
# the gate range behind the reader, with the great gate (18 x 7 inches) in the middle
BS, x0s, zss, tops = range_front("gate_range", (0, CY0, 0), 0, 8.0, [(0.34, "arcade"), (0.36, "plain"), (0.26, "attic")], BAY, centre_bays=1, roof=0.42, depth=1.4)
BS.done()
G = rk._B("gate", (0, CY0, 0), 0)
G.box(STONE, (0.36, 0.05, 0.56), (0, 0.025, 0.0))
G.box(GATEWOOD, (0.18, 0.02, 0.46), (0, 0.055, 0.0))
for zz in (0.12, 0.3): G.box(GILT, (0.18, 0.024, 0.008), (0, 0.06, zz))
G.box(TRIM, (0.30, 0.06, 0.04), (0, 0.03, 0.46))
G.ball(GILT, 0.03, (0, 0.06, 0.52), squash=(1.2, 0.3, 1.0), sub=1)
G.done()

# corner pavilions with gilt-capped domes and flags
FL = []
for (cx, cy) in ((CX0 - 0.7, CY1 + 0.8), (CX1 + 0.7, CY1 + 0.8), (CX0 - 0.7, CY0 - 0.7), (CX1 + 0.7, CY0 - 0.7)):
    north = cy > 0
    h = 2.3 if north else 1.9
    P = rk._B("pavilion", (cx, cy, 0), 0)
    P.box(STONE, (1.4, 1.4, h), (0, 0, 0.0))
    P.box(TRIM, (1.48, 1.48, 0.04), (0, 0, h))
    for k in range(4):
        a = k * 90
        for zz in (0.5, 1.0, 1.45) if north else (0.45, 0.9, 1.3):
            Rm = Matrix.Rotation(math.radians(a), 3, 'Z')
            for off in (-0.3, 0.3):
                p = Rm @ Vector((off, -0.705, 0))
                P.box(GLASS, (0.12, 0.012, 0.22), (p.x, p.y, zz), (0, 0, a))
                P.box(TRIM, (0.15, 0.016, 0.02), (p.x, p.y, zz - 0.02), (0, 0, a))
    P.cyl(LEAD, 0.6, 0.25, (0, 0, h + 0.04), sides=16)
    P.ball(LEAD, 0.58, (0, 0, h + 0.29), squash=(1, 1, 1.15), sub=2)
    P.cyl(GILT, 0.06, 0.22, (0, 0, h + 0.9), sides=8)
    P.ball(GILT, 0.07, (0, 0, h + 1.15), sub=1)
    P.cyl(GILT, 0.008, 0.55, (0, 0, h + 1.2), sides=5)
    P.done()
    if north: FL.append(Vector((cx, cy, h + 1.62)))
# the flags: silk pennants hanging from the staff tops in a light air
fb = bmesh.new()
for top in FL:
    nu, nv = 8, 4
    vs = []
    for j in range(nv + 1):
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            vs.append(fb.verts.new(top + Vector((0.55 * u, 0.06 * math.sin(u * 5.0) * u, -0.12 - 0.25 * v * (1 - 0.5 * u) - 0.18 * u * u))))
    for j in range(nv):
        for i in range(nu):
            fb.faces.new((vs[j * (nu + 1) + i], vs[j * (nu + 1) + i + 1], vs[(j + 1) * (nu + 1) + i + 1], vs[(j + 1) * (nu + 1) + i]))
fo = rk._obj("palace_flags", fb, FLAGM, smooth=True)
ca = fo.data.color_attributes.new("sway", 'BYTE_COLOR', 'POINT')
w = np.array([[min(1.0, (Vector(v.co) - FL[0 if v.co.x < 0 else 1]).length / 0.7), 1, 1, 1] for v in fo.data.vertices], np.float32)
ca.data.foreach_set("color", w.ravel())

# the outer court's ranges, seen over the low east and west roofs, and the second court's roofs behind the gate range
OB = rk._B("outer_ranges")
for (cx, cy, L_, yaw) in ((0, 10.2, 18.0, 0), (0, -9.4, 18.0, 180), (9.2, 0.4, 19.0, -90), (-9.2, 0.4, 19.0, 90)):
    Bo = rk._B("outer", (cx, cy, 0), yaw)
    Bo.box(STONE, (L_, 1.6, 1.55), (0, 0, 0))
    Bo.box(TRIM, (L_ + 0.06, 1.66, 0.04), (0, 0, 1.55))
    Bo.mesh(SLATE, [(-L_ / 2, 0.8, 1.58), (L_ / 2, 0.8, 1.58), (L_ / 2, 0.0, 2.05), (-L_ / 2, 0.0, 2.05)], [(0, 1, 2, 3)])
    Bo.mesh(SLATE, [(L_ / 2, -0.8, 1.58), (-L_ / 2, -0.8, 1.58), (-L_ / 2, 0.0, 2.05), (L_ / 2, 0.0, 2.05)], [(0, 1, 2, 3)])
    for k in range(int(L_ / 1.6)):
        xx = -L_ / 2 + 0.8 + k * 1.6
        Bo.box(STONE, (0.1, 0.08, 0.35), (xx, 0.1, 1.85))
        Bo.box(GLASS, (0.16, 0.05, 0.12), (xx + 0.5, 0.45, 1.68))
    Bo.done()
# a cupola over the great hall beyond the apartments, the tallest thing in the palace
CU = rk._B("cupola", (0, CY1 + 3.2, 0), 0)
CU.cyl(STONE, 0.75, 2.6, (0, 0, 0), sides=20)
for k in range(10):
    a = 2 * math.pi * k / 10
    CU.box(GLASS, (0.12, 0.02, 0.28), (math.cos(a) * 0.755, math.sin(a) * 0.755, 2.2), (0, 0, math.degrees(a) + 90))
CU.cyl(TRIM, 0.82, 0.05, (0, 0, 2.6), sides=20)
CU.ball(LEAD, 0.74, (0, 0, 2.62), squash=(1, 1, 0.9), sub=2)
CU.cyl(GILT, 0.1, 0.25, (0, 0, 3.28), sides=8)
CU.ball(GILT, 0.09, (0, 0, 3.6), sub=1)
CU.done()

# ----------------------------------------------------------------------------- the court: fountain, parterres, stools
F_ = Vector((0.0, 2.75, 0.0))
FT = rk._B("fountain", tuple(F_), 0)
FT.cyl(TRIM, 0.52, 0.11, (0, 0, 0), sides=24)
FT.cyl(TRIM, 0.08, 0.32, (0, 0, 0.1), sides=10, r1=0.05)
FT.cyl(TRIM, 0.2, 0.025, (0, 0, 0.32), sides=16, r1=0.24)
FT.ball(GILT, 0.035, (0, 0, 0.37), sub=1)
FT.done()
FW = rk._B("fountain_water", tuple(F_), 0)
FW.cyl(WATER, 0.47, 0.095, (0, 0, 0.0), sides=24)
FW.cyl(WATER, 0.19, 0.012, (0, 0, 0.335), sides=16)
FW.done()
# parterre beds: low clipped box edging round flowers, in the four quarters (clear of the reader)
PB = rk._B("parterre")
for (bx, by) in ((-2.4, 2.6), (2.4, 2.6), (-2.4, -1.6), (2.4, -1.6)):
    bw, bd = 1.6, 1.3
    PB.box(SOIL, (bw, bd, 0.02), (bx, by, 0.0))
    for (sx, sy, L_, rot) in ((0, bd / 2, bw, 0), (0, -bd / 2, bw, 0), (bw / 2, 0, bd, 90), (-bw / 2, 0, bd, 90)):
        PB.box(box_leaf, (L_ + 0.06, 0.06, 0.07), (bx + sx, by + sy, 0.0), (0, 0, rot))
    # an inner scroll: a cross of box, and a clipped cone at the centre
    PB.box(box_leaf, (bw * 0.7, 0.045, 0.05), (bx, by, 0.0))
    PB.box(box_leaf, (0.045, bd * 0.7, 0.05), (bx, by, 0.0))
    PB.cyl(box_leaf, 0.08, 0.24, (bx, by, 0.0), sides=8, r1=0.01)
PB.done()
FLB = bmesh.new()
for (bx, by) in ((-2.4, 2.6), (2.4, 2.6), (-2.4, -1.6), (2.4, -1.6)):
    for k in range(70):
        x = bx + R.uniform(-0.75, 0.75); y = by + R.uniform(-0.6, 0.6)
        if abs(x - bx) < 0.05 or abs(y - by) < 0.05 or math.hypot(x - bx, y - by) < 0.1: continue
        s = R.uniform(0.012, 0.022)
        bmesh.ops.create_icosphere(FLB, subdivisions=0, radius=s, matrix=Matrix.Translation((x, y, 0.02 + R.uniform(0.01, 0.04))))
fo2 = rk._obj("flowers", FLB, flowers, smooth=True)
K.keep(flowers, "veg.flowers.parterre")
# Gulliver's two stools: a sawn slab of royal-park timber on four stout legs, bark still on, 3 feet high
def stool(name, x, y, yaw):
    S = rk._B(name, (x, y, 0), yaw)
    S.cyl(SAWN, 0.36, 0.1, (0, 0, 0.8), sides=14)
    S.cyl(TIMBER, 0.365, 0.08, (0, 0, 0.8), sides=14)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        S.seg(TIMBER, (math.cos(a) * 0.38, math.sin(a) * 0.38, 0.0), (math.cos(a) * 0.22, math.sin(a) * 0.22, 0.82), 0.065, 0.055, 7)
    S.done()
stool("stool_near", 1.05, -0.15, 20)
stool("stool_far", -2.9, 0.4, -15)
HS = rk._B("hooked_stick")
p0 = Vector((1.55, 0.1, 0.0)); p1 = Vector((1.38, -0.05, 0.86))
HS.seg(TIMBER, p0, p1, 0.022, 0.018, 6)
HS.tube(TIMBER, [p1, p1 + Vector((-0.05, 0.0, 0.08)), p1 + Vector((-0.12, 0.0, 0.07)), p1 + Vector((-0.15, 0.0, 0.0))], [0.018, 0.017, 0.016, 0.015], 6)
HS.done()

# ----------------------------------------------------------------------------- light, sound, reader
K.sun(42, -55, strength=3.8, color=(1.0, 0.95, 0.86), softness=1.0)
for lx in (-1.4, 0.0, 1.4): rk.lamp(f"apartments{lx}", (lx, CY1 + 0.45, z_nob + 0.3), power=4.0, color=(1.0, 0.78, 0.5), radius=0.05)
K.sound("crowd", "city", (0.0, -12.0, 1.0))
K.sound("birds", "park", (-10.0, 12.0, 3.0))
K.sound("wind", "roofs", (6.0, 6.0, 2.5))
E, D = K.reader((0.0, 0.6), (0.0, 6.0))
K.reader_cams()
K.cam("windows", (0.6, 2.3, 0.75), (0.2, CY1, 0.6), lens=24)
K.cam("court", (-3.2, -2.9, 1.9), (1.5, 3.5, 0.6), lens=18)
K.finish()
