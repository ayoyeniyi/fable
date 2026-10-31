"""
Fable: Glumdalclitch's room in Brobdingnag (Gulliver's Travels, Part II, chapters I-III). The reader stands at
Gulliver's size, on top of the farmer's daughter's work table, in an ordinary early-18th-century country bedroom built
at twelve times human scale ("the table, which was thirty feet high from the floor").

What the text gives, and what is here (no person or animal is modelled):
  - "very dexterous at her needle": her sewing left on the table: a length of coarse linen ("coarser than sackcloth",
    from which "she made me seven shirts") half hanging over the table edge, a needle and thread, a spool, a
    pincushion with pins, open scissors, and a thimble ("a thimble filled with liquor, which Glumdalclitch had given me
    for a cup").
  - "the cradle was put into a small drawer of a cabinet": the doll's (baby's) cradle in a drawer taken out of the
    cabinet, which stands across the room with that drawer's slot empty, and "the quilt of her baby's bed" in it.
  - "The box was close on every side, with a little door for me to go in and out, and a few gimlet holes to let in
    air": the travelling box, its door ajar, lined with a quilt.
  - "My little nurse stood on a low stool close to the table": a joint stool beside the table.
  - the bed with its curtains, a ladder-back chair, a panelled door, a leaded casement window, a chamber candlestick.

Scale: everything in the room is 12x an ordinary room (the table top is 9 m above the floor; boards, grain, weave and
stitches are all 12x coarser). Only the reader is human size.

Builds the room procedurally with PBR node materials and lamp light, then (by flag) renders Cycles stills, bakes
materials to textures, merges static meshes by material and exports .gltf + .bin + textures/ for Unity.

Lights: names starting "Lamp" are the ones Unity bakes (indoor convention): Lamp0_Light (candle flame, POINT),
Lamp1_Window (daylight through the casement, SPOT: glTF cannot carry AREA lights), Lamp2_WindowFill (wide soft
skylight spill, SPOT).

Run headless:
  blender -b -P blender/build_glumdalclitchs_room.py -- --out out/glumdalclitchs-room --render --quick --res 1200
  blender -b -P blender/build_glumdalclitchs_room.py -- --out out/glumdalclitchs-room --bake --export --tex 2048
"""
import bpy, bmesh, math, random, sys, os, argparse
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="out/glumdalclitchs-room")
ap.add_argument("--render", action="store_true")
ap.add_argument("--bake", action="store_true")
ap.add_argument("--export", action="store_true")
ap.add_argument("--samples", type=int, default=160)
ap.add_argument("--res", type=int, default=1600)
ap.add_argument("--tex", type=int, default=2048)
ap.add_argument("--quick", action="store_true", help="low samples for iteration")
ap.add_argument("--cams", default="", help="comma list of camera names to render (default all)")
args = ap.parse_args(argv)
OUT = os.path.abspath(args.out)
os.makedirs(OUT, exist_ok=True)
random.seed(1726)

# ----------------------------------------------------------------------------- dimensions (metres, Z up)
S = 12.0                                         # Brobdingnag : reader
ROOM_W, ROOM_D, ROOM_H = 48.0, 60.0, 31.2        # a 4 x 5 x 2.6 m room at 12x; x across, y deep (bed wall at +y)
hx, hy = ROOM_W / 2, ROOM_D / 2
WALL_T = 3.0                                     # a 25 cm farmhouse wall
TABLE_H = 9.0                                    # "thirty feet high from the floor"
TOP_T = 0.42
TX, TY, TW, TL = 10.0, -8.0, 7.8, 13.2           # table centre and top size (x, y)
TX0, TX1, TY0, TY1 = TX - TW / 2, TX + TW / 2, TY - TL / 2, TY + TL / 2
Z = TABLE_H                                      # the walkable surface
READER = (9.3, -11.8)                            # where the reader stands, facing +y
WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1 = -5.0, 8.2, 10.8, 27.6   # the casement in the east wall
DOOR_Y, DOOR_W, DOOR_H = 9.0, 10.8, 24.0         # the door in the west wall

# ----------------------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24 if args.quick else args.samples
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'; prefs.get_devices()
    for d in prefs.devices: d.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print("Metal not available, CPU render:", e)
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 0.0

COLL = bpy.data.collections.new("GlumdalclitchsRoom")
scene.collection.children.link(COLL)
def link(obj):
    COLL.objects.link(obj); return obj

# ----------------------------------------------------------------------------- material helpers
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, bsdf

def node(nt, kind, loc=(0, 0), **props):
    n = nt.nodes.new(kind); n.location = loc
    for k, v in props.items(): setattr(n, k, v)
    return n

def ramp(nt, stops, loc=(0, 0)):
    r = nt.nodes.new("ShaderNodeValToRGB"); r.location = loc
    cr = r.color_ramp
    while len(cr.elements) > 1: cr.elements.remove(cr.elements[-1])
    cr.elements[0].position, cr.elements[0].color = stops[0]
    for pos, col in stops[1:]:
        e = cr.elements.new(pos); e.color = col
    return r

def math_(nt, op, a, b=None, loc=(0, 0)):
    """Math node; a/b are sockets or numbers."""
    n = node(nt, "ShaderNodeMath", loc, operation=op)
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]

def mixc(nt, a, b, fac, blend='MIX', loc=(0, 0)):
    """RGBA mix; a/b sockets or colours, fac socket or number."""
    n = node(nt, "ShaderNodeMix", loc, data_type='RGBA', blend_type=blend)
    for sock, v in ((n.inputs["Factor"], fac), (n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, (int, float)): sock.default_value = v
        elif isinstance(v, tuple): sock.default_value = v if len(v) == 4 else (*v, 1)
        else: nt.links.new(v, sock)
    return n.outputs[2]

def texcoord_obj(nt, loc=(-1400, 0), scale=(1, 1, 1)):
    tc = node(nt, "ShaderNodeTexCoord", loc); mp = node(nt, "ShaderNodeMapping", (loc[0] + 200, loc[1]))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); mp.inputs["Scale"].default_value = scale
    return mp

def bump_from(nt, b, height, strength, dist):
    bp = node(nt, "ShaderNodeBump", (50, -300)); bp.inputs["Strength"].default_value = strength; bp.inputs["Distance"].default_value = dist
    nt.links.new(height, bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return bp

def ao_mult(nt, col, dist, amount):
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-700, -550)); ao.inputs["Distance"].default_value = dist
    return mixc(nt, col, ao.outputs["Color"], amount, 'MULTIPLY')

def rings(nt, vec, axis, spacing, distortion=5.0, loc=(-1000, 200)):
    """Annual rings around an axis (a log's pith): SAW profile = soft earlywood ramping into a sharp latewood line.
    Blender's wave: phase = |p| * 20 * scale, so the ring spacing in metres is 0.314 / scale."""
    w = node(nt, "ShaderNodeTexWave", loc, wave_type='RINGS', rings_direction=axis, wave_profile='SAW')
    sc = 0.314 / spacing
    w.inputs["Scale"].default_value = sc; w.inputs["Distortion"].default_value = distortion
    w.inputs["Detail"].default_value = 3.0; w.inputs["Detail Scale"].default_value = 0.6 / sc; w.inputs["Detail Roughness"].default_value = 0.5
    nt.links.new(vec, w.inputs["Vector"])
    return w.outputs["Fac"]

def pores(nt, vec, axis, loc=(-1000, -150)):
    """Fine streaks running with the grain."""
    sc = {"X": (0.6, 30, 30), "Y": (30, 0.6, 30), "Z": (30, 30, 0.6)}[axis]
    mp = node(nt, "ShaderNodeMapping", (loc[0] - 200, loc[1])); mp.inputs["Scale"].default_value = sc
    nt.links.new(vec, mp.inputs["Vector"])
    n = node(nt, "ShaderNodeTexNoise", loc); n.inputs["Scale"].default_value = 1.0; n.inputs["Detail"].default_value = 6; n.inputs["Roughness"].default_value = 0.6
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    return n.outputs["Fac"]

def wood_colour(nt, fac, base, dark, light, loc=(-450, 100)):
    r = ramp(nt, [(0.0, (*light, 1)), (0.55, (*base, 1)), (0.86, (*base, 1)), (0.95, (*dark, 1)), (1.0, (*dark, 1))], loc)
    nt.links.new(fac, r.inputs["Fac"])
    return r.outputs["Color"]

def wood(name, base=(0.32, 0.17, 0.08), dark=(0.09, 0.045, 0.02), light=(0.55, 0.33, 0.15), rough=(0.35, 0.6),
         axis='Z', spacing=0.045, coat=0.15):
    """Wood whose grain runs along `axis`, with rings 12x wider than life (it was cut from Brobdingnagian trees)."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1800, 0))
    # put the pith ~1 m off the member and tilt it a little, so faces show arcs (cathedrals) rather than bullseyes
    tilt = {"X": (0, 0.06, 0.04), "Y": (0.06, 0, 0.04), "Z": (0.05, 0.04, 0)}[axis]
    mp = node(nt, "ShaderNodeMapping", (-1600, 0)); mp.inputs["Location"].default_value = (0.9, 1.3, 0.7); mp.inputs["Rotation"].default_value = tilt
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    fac = rings(nt, mp.outputs["Vector"], axis, spacing)
    po = pores(nt, tc.outputs["Object"], axis)
    col = wood_colour(nt, fac, base, dark, light)
    big = node(nt, "ShaderNodeTexNoise", (-1000, -450)); big.inputs["Scale"].default_value = 0.4; big.inputs["Detail"].default_value = 3
    nt.links.new(tc.outputs["Object"], big.inputs["Vector"])
    col = mixc(nt, col, tuple(c * 0.75 for c in base), math_(nt, 'MULTIPLY', big.outputs["Fac"], 0.5))
    col = mixc(nt, col, po, 0.22, 'MULTIPLY')
    nt.links.new(ao_mult(nt, col, 0.8, 0.3), b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", (-150, -200))
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough[0], rough[1]
    nt.links.new(fac, rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    h = math_(nt, 'ADD', math_(nt, 'MULTIPLY', fac, 0.6), math_(nt, 'MULTIPLY', po, 0.4))
    bump_from(nt, b, h, 0.25, 0.02)
    b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.3
    return m

def painted(name, paint, rough=0.55, wear=(0.42, 0.30, 0.18)):
    """Paint over wood, rubbed through on the high spots; brush strokes at giant scale."""
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt, scale=(1 / S, 1 / S, 6 / S))
    strokes = node(nt, "ShaderNodeTexNoise", (-1000, 100)); strokes.inputs["Scale"].default_value = 6; strokes.inputs["Detail"].default_value = 6
    nt.links.new(mp.outputs["Vector"], strokes.inputs["Vector"])
    big = node(nt, "ShaderNodeTexNoise", (-1000, -150)); big.inputs["Scale"].default_value = 1.2; big.inputs["Detail"].default_value = 4
    nt.links.new(mp.outputs["Vector"], big.inputs["Vector"])
    w = ramp(nt, [(0.0, (0, 0, 0, 1)), (0.66, (0, 0, 0, 1)), (0.72, (1, 1, 1, 1))], (-700, -150)); nt.links.new(big.outputs["Fac"], w.inputs["Fac"])
    col = mixc(nt, tuple(c * 0.8 for c in paint), paint, strokes.outputs["Fac"])
    col = mixc(nt, col, wear, w.outputs["Color"])
    nt.links.new(ao_mult(nt, col, 0.5, 0.35), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    bump_from(nt, b, strokes.outputs["Fac"], 0.12, 0.02)
    return m

def planks(name, board_w, tones, grain_spacing=0.04, butt=None, seam_w=0.025, coat=0.25, rough=0.45, knots=True):
    """Boards running along y, each its own tone, grain offset per board; optional staggered butt joints."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1800, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1600, 0))
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    across = math_(nt, 'DIVIDE', sep.outputs["X"], board_w)
    idx = math_(nt, 'FLOOR', across); fr = math_(nt, 'FRACT', across)
    seam_in = fr
    bid = idx
    if butt:
        wn0 = node(nt, "ShaderNodeTexWhiteNoise", (-1200, 400), noise_dimensions='1D'); nt.links.new(idx, wn0.inputs["W"])
        along = math_(nt, 'DIVIDE', math_(nt, 'ADD', sep.outputs["Y"], math_(nt, 'MULTIPLY', wn0.outputs["Value"], butt)), butt)
        fr2 = math_(nt, 'FRACT', along)
        bid = math_(nt, 'ADD', idx, math_(nt, 'MULTIPLY', math_(nt, 'FLOOR', along), 37.0))
        seam2 = ramp(nt, [(0.0, (0, 0, 0, 1)), (seam_w * board_w / butt, (1, 1, 1, 1)), (1 - seam_w * board_w / butt, (1, 1, 1, 1)), (1.0, (0, 0, 0, 1))], (-800, 500))
        nt.links.new(fr2, seam2.inputs["Fac"])
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-1000, 100), noise_dimensions='1D'); nt.links.new(bid, wn.inputs["W"])
    seam = ramp(nt, [(0.0, (0, 0, 0, 1)), (seam_w, (1, 1, 1, 1)), (1 - seam_w, (1, 1, 1, 1)), (1.0, (0, 0, 0, 1))], (-800, 300))
    nt.links.new(seam_in, seam.inputs["Fac"])
    seams = seam.outputs["Color"]
    if butt: seams = mixc(nt, seams, seam2.outputs["Color"], 1.0, 'MULTIPLY')
    tone = ramp(nt, [(0.0, (*tones[0], 1)), (0.5, (*tones[1], 1)), (1.0, (*tones[2], 1))], (-600, 100))
    nt.links.new(wn.outputs["Value"], tone.inputs["Fac"])
    # grain: each board is flat-sawn from its own log: rings around a pith that runs along y, 1.5-3 m below the face
    # (12-36 cm in life), off-centre and slightly tilted, so the face shows cathedral arches
    wn2 = node(nt, "ShaderNodeTexWhiteNoise", (-1000, -100), noise_dimensions='1D'); nt.links.new(math_(nt, 'ADD', bid, 0.37), wn2.inputs["W"])
    sep2 = node(nt, "ShaderNodeSeparateColor", (-800, -100)); nt.links.new(wn2.outputs["Color"], sep2.inputs["Color"])
    # pith beside and below the board: mostly rift-sawn straight grain, the odd long cathedral where it passes close
    side = math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', math_(nt, 'GREATER_THAN', sep2.outputs[0], 0.5), 2.0), 1.0)
    cx = math_(nt, 'ADD', math_(nt, 'MULTIPLY', math_(nt, 'ADD', idx, 0.5), board_w),
               math_(nt, 'MULTIPLY', side, math_(nt, 'ADD', 0.4 * board_w, math_(nt, 'MULTIPLY', sep2.outputs[1], 1.2 * board_w))))
    gx = math_(nt, 'SUBTRACT', sep.outputs["X"], cx)
    depth = math_(nt, 'ADD', 0.4 * board_w, math_(nt, 'MULTIPLY', sep2.outputs[1], 0.4 * board_w))
    tilt = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', sep2.outputs[2], 0.5), 0.12)
    gz = math_(nt, 'ADD', math_(nt, 'ADD', sep.outputs["Z"], depth), math_(nt, 'MULTIPLY', sep.outputs["Y"], tilt))
    gy = math_(nt, 'ADD', sep.outputs["Y"], math_(nt, 'MULTIPLY', sep2.outputs[0], 50.0))
    cmb = node(nt, "ShaderNodeCombineXYZ", (-600, -300)); nt.links.new(gx, cmb.inputs[0]); nt.links.new(gy, cmb.inputs[1]); nt.links.new(gz, cmb.inputs[2])
    fac = rings(nt, cmb.outputs[0], 'Y', grain_spacing, distortion=7.0, loc=(-400, -300))
    po = pores(nt, tc.outputs["Object"], 'Y')
    lite = tuple(min(1, c * 1.25) for c in tones[1]); drk = tuple(c * 0.45 for c in tones[1])
    rcol = ramp(nt, [(0.0, (1.05, 1.05, 1.05, 1)), (0.75, (0.95, 0.95, 0.95, 1)), (0.9, (0.82, 0.82, 0.82, 1)), (0.97, (0.5, 0.5, 0.5, 1)), (1.0, (0.55, 0.55, 0.55, 1))], (-200, -300))
    nt.links.new(fac, rcol.inputs["Fac"])
    col = mixc(nt, tone.outputs["Color"], rcol.outputs["Color"], 1.0, 'MULTIPLY')
    # streaky colour running with the board, and open pores
    st = texcoord_obj(nt, (-1500, -1300), scale=(2.5, 0.12, 2.5))
    stn = node(nt, "ShaderNodeTexNoise", (-1000, -1300)); stn.inputs["Scale"].default_value = 1.5; stn.inputs["Detail"].default_value = 5
    nt.links.new(st.outputs["Vector"], stn.inputs["Vector"])
    stc = ramp(nt, [(0.3, (0.8, 0.8, 0.8, 1)), (0.7, (1.08, 1.08, 1.08, 1))], (-700, -1300)); nt.links.new(stn.outputs["Fac"], stc.inputs["Fac"])
    col = mixc(nt, col, stc.outputs["Color"], 1.0, 'MULTIPLY')
    pc = ramp(nt, [(0.35, (0.75, 0.75, 0.75, 1)), (0.65, (1, 1, 1, 1))], (-700, -1500)); nt.links.new(po, pc.inputs["Fac"])
    col = mixc(nt, col, pc.outputs["Color"], 1.0, 'MULTIPLY')
    wave = rcol  # for roughness and bump below
    if knots:
        vor = node(nt, "ShaderNodeTexVoronoi", (-1000, -700)); vor.inputs["Scale"].default_value = 0.35
        kv = texcoord_obj(nt, (-1500, -700), scale=(1.0, 0.35, 1.0)); nt.links.new(kv.outputs["Vector"], vor.inputs["Vector"])
        kn = ramp(nt, [(0.0, (0.25, 0.25, 0.25, 1)), (0.035, (0.55, 0.55, 0.55, 1)), (0.06, (1, 1, 1, 1))], (-700, -700))
        nt.links.new(vor.outputs["Distance"], kn.inputs["Fac"])
        col = mixc(nt, col, kn.outputs["Color"], 1.0, 'MULTIPLY')
    # long scratches and rubbed wear
    sc = texcoord_obj(nt, (-1500, -1000), scale=(3.0, 0.08, 1.0))
    scn = node(nt, "ShaderNodeTexNoise", (-1000, -1000)); scn.inputs["Scale"].default_value = 9; scn.inputs["Detail"].default_value = 3
    nt.links.new(sc.outputs["Vector"], scn.inputs["Vector"])
    scr = ramp(nt, [(0.0, (0, 0, 0, 1)), (0.62, (0, 0, 0, 1)), (0.66, (1, 1, 1, 1))], (-700, -1000)); nt.links.new(scn.outputs["Fac"], scr.inputs["Fac"])
    col = mixc(nt, col, tuple(min(1, c * 1.35) for c in tones[1]), math_(nt, 'MULTIPLY', scr.outputs["Color"], 0.12), 'MIX')
    col = mixc(nt, col, seams, 0.85, 'MULTIPLY')
    nt.links.new(ao_mult(nt, col, 1.0, 0.35), b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", (-150, -200)); rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough + 0.12, rough - 0.08
    nt.links.new(fac, rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    h = mixc(nt, seams, wave.outputs["Color"], 0.25, 'MULTIPLY')
    bump_from(nt, b, h, 0.5, 0.04)
    b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.3
    return m

def limewash(name, color=(0.80, 0.76, 0.66)):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt, scale=(0.25, 0.25, 0.25))
    n = node(nt, "ShaderNodeTexNoise", (-900, 0)); n.inputs["Scale"].default_value = 3; n.inputs["Detail"].default_value = 10; n.inputs["Roughness"].default_value = 0.6
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    n2 = node(nt, "ShaderNodeTexNoise", (-900, -250)); n2.inputs["Scale"].default_value = 40; n2.inputs["Detail"].default_value = 4
    nt.links.new(mp.outputs["Vector"], n2.inputs["Vector"])
    r = ramp(nt, [(0.3, (color[0] * 0.82, color[1] * 0.80, color[2] * 0.74, 1)), (0.7, (*color, 1))], (-600, 0))
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(ao_mult(nt, r.outputs["Color"], 3.0, 0.4), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
    bump_from(nt, b, n2.outputs["Fac"], 0.2, 0.05)
    return m

def metal(name, color, rough=(0.2, 0.45), dimples=0.0, tarnish=0.5):
    m, nt, b = new_mat(name)
    b.inputs["Metallic"].default_value = 1.0
    mp = texcoord_obj(nt)
    n1 = node(nt, "ShaderNodeTexNoise", (-900, 0)); n1.inputs["Scale"].default_value = 90 / S; n1.inputs["Detail"].default_value = 6
    nt.links.new(mp.outputs["Vector"], n1.inputs["Vector"])
    rr = node(nt, "ShaderNodeMapRange", (-350, 0)); rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = rough
    nt.links.new(n1.outputs["Fac"], rr.inputs["Value"]); nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    ao = node(nt, "ShaderNodeAmbientOcclusion", (-600, -500)); ao.inputs["Distance"].default_value = 0.3
    inv = node(nt, "ShaderNodeInvert", (-350, -500)); nt.links.new(ao.outputs["Color"], inv.inputs["Color"])
    fac = math_(nt, 'MULTIPLY', inv.outputs["Color"], tarnish)
    col = mixc(nt, color, (color[0] * 0.4, color[1] * 0.33, color[2] * 0.25), fac)
    nt.links.new(col, b.inputs["Base Color"])
    if dimples > 0:   # a thimble's knurling: rows of pits, 1 mm in life, 12 mm here
        vor = node(nt, "ShaderNodeTexVoronoi", (-900, -800)); vor.inputs["Scale"].default_value = dimples
        nt.links.new(mp.outputs["Vector"], vor.inputs["Vector"])
        pit = ramp(nt, [(0.0, (0, 0, 0, 1)), (0.35, (1, 1, 1, 1))], (-600, -800)); nt.links.new(vor.outputs["Distance"], pit.inputs["Fac"])
        bump_from(nt, b, pit.outputs["Color"], 0.8, 0.01)
    else:
        bump_from(nt, b, n1.outputs["Fac"], 0.05, 0.005)
    return m

def flat(name, color, rough=0.6, metallic=0.0, emission=None, strength=0.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metallic
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1); b.inputs["Emission Strength"].default_value = strength
    return m

def weave(name, color, thread=0.012, slub=0.25, rough=0.85, sheen=0.3, rest_uv=True):
    """Plain-woven linen 12x coarse: a 1 mm thread in life is a 12 mm cord here. rest_uv: use the cloth's RestUV (metres)."""
    m, nt, b = new_mat(name)
    if rest_uv:
        uv = node(nt, "ShaderNodeUVMap", (-1800, 0), uv_map="RestUV"); vec = uv.outputs["UV"]
    else:
        tc = node(nt, "ShaderNodeTexCoord", (-1800, 0)); vec = tc.outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1600, 0)); nt.links.new(vec, sep.inputs["Vector"])
    u = math_(nt, 'DIVIDE', sep.outputs["X"], thread); v = math_(nt, 'DIVIDE', sep.outputs["Y"] if rest_uv else sep.outputs["Z"], thread)
    # threads: |sin| ridges across u (warp) and v (weft); checker of over/under picks which shows
    warp = math_(nt, 'ABSOLUTE', math_(nt, 'SINE', math_(nt, 'MULTIPLY', u, math.pi)))
    weft = math_(nt, 'ABSOLUTE', math_(nt, 'SINE', math_(nt, 'MULTIPLY', v, math.pi)))
    cu = math_(nt, 'FLOOR', u); cv = math_(nt, 'FLOOR', v)
    chk = math_(nt, 'MODULO', math_(nt, 'ADD', cu, cv), 2.0)
    chk = math_(nt, 'ABSOLUTE', chk)
    h = node(nt, "ShaderNodeMix", (-600, 0), data_type='FLOAT'); nt.links.new(chk, h.inputs["Factor"]); nt.links.new(warp, h.inputs[2]); nt.links.new(weft, h.inputs[3])
    hgt = math_(nt, 'POWER', h.outputs[0], 0.6)
    # slubs: thick and thin places in hand-spun thread
    sl = node(nt, "ShaderNodeTexNoise", (-900, -300)); sl.inputs["Scale"].default_value = 3.0; sl.inputs["Detail"].default_value = 4
    nt.links.new(vec, sl.inputs["Vector"])
    col = mixc(nt, tuple(c * 0.72 for c in color), color, hgt)
    col = mixc(nt, col, tuple(c * 0.85 for c in color), math_(nt, 'MULTIPLY', sl.outputs["Fac"], slub * 2))
    nt.links.new(ao_mult(nt, col, 0.4, 0.4), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Sheen Weight"].default_value = sheen
    bump_from(nt, b, hgt, 0.6, 0.006)
    return m

def quilt(name, ground, print_cols, diamond=0.5, stitch=0.03, rest_uv=False, axes=("X", "Y")):
    """Whole-cloth quilt: a printed cotton ground with sprigs, quilted in diamonds (puffy between the stitch lines)."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1900, 0))
    vec = tc.outputs["Object"]
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1700, 0)); nt.links.new(vec, sep.inputs["Vector"])
    a, c = sep.outputs[axes[0]], sep.outputs[axes[1]]
    p = math_(nt, 'DIVIDE', math_(nt, 'ADD', a, c), diamond); q = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', a, c), diamond)
    def tri(x):   # 0 at stitch line, 1 mid-diamond
        return math_(nt, 'MULTIPLY', math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', x), 0.5)), 2.0)
    puff = math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, tri(p)), math_(nt, 'SUBTRACT', 1.0, tri(q)))
    puff = math_(nt, 'POWER', puff, 0.35)
    # sprig print: voronoi cells, small blossoms at cell centres
    vor = node(nt, "ShaderNodeTexVoronoi", (-1200, -400)); vor.inputs["Scale"].default_value = 3.0 / diamond
    nt.links.new(vec, vor.inputs["Vector"])
    blossom = ramp(nt, [(0.0, (1, 1, 1, 1)), (0.18, (1, 1, 1, 1)), (0.22, (0, 0, 0, 1))], (-900, -400)); nt.links.new(vor.outputs["Distance"], blossom.inputs["Fac"])
    pick = ramp(nt, [(0.0, (*print_cols[0], 1)), (0.5, (*print_cols[1], 1)), (1.0, (*print_cols[2], 1))], (-900, -700))
    pick.color_ramp.interpolation = 'CONSTANT'; nt.links.new(vor.outputs["Color"], pick.inputs["Fac"])
    col = mixc(nt, ground, pick.outputs["Color"], blossom.outputs["Color"])
    shade = ramp(nt, [(0.0, (0.55, 0.55, 0.55, 1)), (1.0, (1, 1, 1, 1))], (-600, 200)); nt.links.new(puff, shade.inputs["Fac"])
    col = mixc(nt, col, shade.outputs["Color"], 1.0, 'MULTIPLY')
    nt.links.new(ao_mult(nt, col, 0.6, 0.35), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85; b.inputs["Sheen Weight"].default_value = 0.4
    bump_from(nt, b, puff, 0.7, 0.05)
    return m

def wool(name, color, rough=0.9):
    """Worsted moreen bed hangings: a faint watered figure and a coarse twill, giant scale."""
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt, scale=(0.2, 0.2, 0.2))
    wv = node(nt, "ShaderNodeTexWave", (-900, 0), wave_type='RINGS'); wv.inputs["Scale"].default_value = 3; wv.inputs["Distortion"].default_value = 12; wv.inputs["Detail"].default_value = 3
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    tw = texcoord_obj(nt, (-1400, -300), scale=(1, 1, 1))
    tww = node(nt, "ShaderNodeTexWave", (-900, -300), wave_type='BANDS', bands_direction='DIAGONAL'); tww.inputs["Scale"].default_value = 30
    nt.links.new(tw.outputs["Vector"], tww.inputs["Vector"])
    col = mixc(nt, tuple(c * 0.8 for c in color), color, wv.outputs["Fac"])
    col = mixc(nt, col, tww.outputs["Color"], 0.15, 'MULTIPLY')
    nt.links.new(ao_mult(nt, col, 2.0, 0.45), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Sheen Weight"].default_value = 0.7; b.inputs["Sheen Tint"].default_value = (1.0, 0.85, 0.8, 1)
    bump_from(nt, b, tww.outputs["Fac"], 0.15, 0.02)
    return m

def rug_mat(name="M_RagRug"):
    """A braided rag rug: concentric braids of mixed rags (the rug object is centred at its origin)."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1400, 0)); nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    r = math_(nt, 'SQRT', math_(nt, 'ADD', math_(nt, 'POWER', math_(nt, 'DIVIDE', sep.outputs["X"], 1.4), 2.0), math_(nt, 'POWER', sep.outputs["Y"], 2.0)))
    ring = math_(nt, 'DIVIDE', r, 0.55)
    idx = math_(nt, 'FLOOR', ring); fr = math_(nt, 'FRACT', ring)
    wn = node(nt, "ShaderNodeTexWhiteNoise", (-900, 100), noise_dimensions='1D'); nt.links.new(idx, wn.inputs["W"])
    pal = ramp(nt, [(0.0, (0.30, 0.10, 0.07, 1)), (0.25, (0.12, 0.16, 0.24, 1)), (0.5, (0.42, 0.34, 0.18, 1)), (0.75, (0.18, 0.22, 0.12, 1)), (1.0, (0.45, 0.40, 0.33, 1))], (-700, 100))
    pal.color_ramp.interpolation = 'CONSTANT'; nt.links.new(wn.outputs["Value"], pal.inputs["Fac"])
    # braid chevrons along each ring
    ang = node(nt, "ShaderNodeMath", (-1100, -200), operation='ARCTAN2'); nt.links.new(sep.outputs["Y"], ang.inputs[0]); nt.links.new(sep.outputs["X"], ang.inputs[1])
    chev = math_(nt, 'FRACT', math_(nt, 'ADD', math_(nt, 'MULTIPLY', ang.outputs[0], 40.0), math_(nt, 'MULTIPLY', math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', fr, 0.5)), 2.0)))
    ridge = math_(nt, 'SINE', math_(nt, 'MULTIPLY', fr, math.pi))
    hgt = math_(nt, 'MULTIPLY', ridge, math_(nt, 'ADD', 0.6, math_(nt, 'MULTIPLY', chev, 0.4)))
    col = mixc(nt, pal.outputs["Color"], (0.0, 0.0, 0.0), math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', 1.0, hgt), 0.6))
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.95; b.inputs["Sheen Weight"].default_value = 0.5
    bump_from(nt, b, hgt, 0.8, 0.1)
    return m

def sampler_mat(name="M_Sampler"):
    """A girl's needlework sampler: bands of cross-stitch on linen (3 mm stitches in life, 36 mm here)."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1800, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1600, 0)); nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    st = 0.09
    gx = math_(nt, 'FLOOR', math_(nt, 'DIVIDE', sep.outputs["X"], st)); gz = math_(nt, 'FLOOR', math_(nt, 'DIVIDE', sep.outputs["Z"], st))
    band = math_(nt, 'FLOOR', math_(nt, 'DIVIDE', gz, 9.0)); inband = math_(nt, 'MODULO', gz, 9.0)
    # motif: a different sine lattice per band, thresholded into stitched cells
    wnb = node(nt, "ShaderNodeTexWhiteNoise", (-1100, 300), noise_dimensions='1D'); nt.links.new(band, wnb.inputs["W"])
    fq = math_(nt, 'ADD', 0.3, math_(nt, 'MULTIPLY', wnb.outputs["Value"], 0.9))
    motif = math_(nt, 'MULTIPLY', math_(nt, 'SINE', math_(nt, 'MULTIPLY', gx, fq)), math_(nt, 'SINE', math_(nt, 'MULTIPLY', math_(nt, 'SUBTRACT', inband, 4.0), 0.7)))
    on = math_(nt, 'GREATER_THAN', math_(nt, 'ABSOLUTE', motif), 0.35)
    gap = math_(nt, 'GREATER_THAN', inband, 0.5)
    on = math_(nt, 'MULTIPLY', on, gap)
    pal = ramp(nt, [(0.0, (0.35, 0.06, 0.06, 1)), (0.33, (0.08, 0.20, 0.12, 1)), (0.66, (0.10, 0.12, 0.30, 1)), (1.0, (0.45, 0.30, 0.08, 1))], (-700, 300))
    pal.color_ramp.interpolation = 'CONSTANT'; nt.links.new(wnb.outputs["Value"], pal.inputs["Fac"])
    col = mixc(nt, (0.68, 0.60, 0.45), pal.outputs["Color"], on)
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
    bump_from(nt, b, on, 0.4, 0.02)
    return m

def window_glass(name="M_WindowGlass"):
    """Leaded diamond quarries (lead 1 cm in life, 12 cm here) over a bright morning sky; emissive so it reads as day."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1800, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1600, 0)); nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    d = 1.5
    p = math_(nt, 'DIVIDE', math_(nt, 'ADD', sep.outputs["Y"], math_(nt, 'MULTIPLY', sep.outputs["Z"], 0.62)), d)
    q = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', sep.outputs["Y"], math_(nt, 'MULTIPLY', sep.outputs["Z"], 0.62)), d)
    def edge(x):
        return math_(nt, 'ABSOLUTE', math_(nt, 'SUBTRACT', math_(nt, 'FRACT', x), 0.5))
    e = math_(nt, 'MAXIMUM', edge(p), edge(q))
    lead = math_(nt, 'GREATER_THAN', e, 0.455)
    sky = ramp(nt, [(0.0, (0.95, 0.90, 0.78, 1)), (0.5, (0.75, 0.84, 0.95, 1)), (1.0, (0.55, 0.70, 0.95, 1))], (-700, 300))
    zz = math_(nt, 'DIVIDE', math_(nt, 'SUBTRACT', sep.outputs["Z"], -8.0), 16.0); nt.links.new(zz, sky.inputs["Fac"])
    wob = node(nt, "ShaderNodeTexNoise", (-900, -300)); wob.inputs["Scale"].default_value = 0.8; nt.links.new(tc.outputs["Object"], wob.inputs["Vector"])
    col = mixc(nt, sky.outputs["Color"], (0.8, 0.85, 0.75), math_(nt, 'MULTIPLY', wob.outputs["Fac"], 0.35))
    col = mixc(nt, col, (0.03, 0.03, 0.035), lead)
    nt.links.new(col, b.inputs["Base Color"]); nt.links.new(col, b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 2.5; b.inputs["Roughness"].default_value = 0.15
    return m

def wax(name="M_Wax"):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (0.86, 0.80, 0.64, 1); b.inputs["Roughness"].default_value = 0.4
    b.inputs["Subsurface Weight"].default_value = 0.6; b.inputs["Subsurface Radius"].default_value = (0.5, 0.35, 0.2); b.inputs["Subsurface Scale"].default_value = 0.1
    return m

def rush(name="M_Rush"):
    """A rush seat: twisted rush in four woven triangles (object coords, chair seat centred at its origin)."""
    m, nt, b = new_mat(name)
    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0)); sep = node(nt, "ShaderNodeSeparateXYZ", (-1400, 0)); nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    ax = math_(nt, 'ABSOLUTE', sep.outputs["X"]); ay = math_(nt, 'ABSOLUTE', sep.outputs["Y"])
    rr = math_(nt, 'MAXIMUM', ax, ay)
    tw = math_(nt, 'ABSOLUTE', math_(nt, 'SINE', math_(nt, 'MULTIPLY', rr, 22.0)))
    tw2 = math_(nt, 'ABSOLUTE', math_(nt, 'SINE', math_(nt, 'MULTIPLY', math_(nt, 'ADD', ax, ay), 9.0)))
    h = math_(nt, 'MULTIPLY', tw, math_(nt, 'ADD', 0.7, math_(nt, 'MULTIPLY', tw2, 0.3)))
    col = mixc(nt, (0.22, 0.17, 0.07), (0.55, 0.45, 0.22), h)
    nt.links.new(col, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.75
    bump_from(nt, b, h, 0.7, 0.05)
    return m

def velvet(name, color):
    m, nt, b = new_mat(name)
    mp = texcoord_obj(nt, scale=(1, 1, 1))
    n = node(nt, "ShaderNodeTexNoise", (-900, 0)); n.inputs["Scale"].default_value = 8; n.inputs["Detail"].default_value = 6
    nt.links.new(mp.outputs["Vector"], n.inputs["Vector"])
    col = mixc(nt, tuple(c * 0.75 for c in color), color, n.outputs["Fac"])
    nt.links.new(ao_mult(nt, col, 0.2, 0.5), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.85; b.inputs["Sheen Weight"].default_value = 1.0; b.inputs["Sheen Tint"].default_value = (1.0, 0.8, 0.75, 1)
    bump_from(nt, b, n.outputs["Fac"], 0.1, 0.01)
    return m

M_TABLETOP = planks("M_TableTop", 2.6, [(0.20, 0.11, 0.05), (0.26, 0.15, 0.07), (0.31, 0.185, 0.09)], grain_spacing=0.04, coat=0.15, rough=0.5)
M_FLOOR = planks("M_Floor", 2.2, [(0.15, 0.085, 0.042), (0.21, 0.125, 0.06), (0.27, 0.16, 0.08)], grain_spacing=0.05, butt=40.0, coat=0.1, rough=0.55)
_tf = dict(base=(0.26, 0.145, 0.065), dark=(0.09, 0.045, 0.02), light=(0.38, 0.23, 0.11))
M_TABLEFRAME = wood("M_TableFrame", axis='Z', **_tf)
M_TABLEFRAMEH = wood("M_TableFrameH", axis='X', **_tf)
_oak = dict(base=(0.19, 0.10, 0.045), dark=(0.06, 0.03, 0.012), light=(0.30, 0.17, 0.08), coat=0.3)
M_OAK = wood("M_Oak", axis='Z', **_oak)
M_OAKH = wood("M_OakH", axis='X', **_oak)
M_TIMBER = wood("M_Timber", base=(0.13, 0.075, 0.038), dark=(0.04, 0.02, 0.01), light=(0.20, 0.12, 0.06), axis='X', spacing=0.06, coat=0.0, rough=(0.55, 0.8))
M_PINE = wood("M_Pine", base=(0.50, 0.34, 0.18), dark=(0.28, 0.15, 0.07), light=(0.62, 0.46, 0.27), axis='X', spacing=0.05, coat=0.05)
M_WALL = limewash("M_Limewash")
M_CEILING = limewash("M_Ceiling", (0.70, 0.66, 0.56))
M_CRADLE = painted("M_CradlePaint", (0.30, 0.09, 0.06), wear=(0.36, 0.22, 0.11))
M_GLASS = window_glass()
M_BRASS = metal("M_Brass", (0.80, 0.56, 0.24))
M_STEEL = metal("M_Steel", (0.62, 0.62, 0.64), rough=(0.18, 0.35), tarnish=0.35)
M_THIMBLE = metal("M_Thimble", (0.85, 0.84, 0.82), rough=(0.2, 0.35), dimples=110.0, tarnish=0.6)
M_IRON = metal("M_Iron", (0.09, 0.085, 0.08), rough=(0.5, 0.75), tarnish=0.1)
M_LINEN = weave("M_Linen", (0.50, 0.44, 0.32), thread=0.014)
M_PILLOW = weave("M_BedLinen", (0.86, 0.84, 0.78), thread=0.012, slub=0.1, rest_uv=False)
M_THREAD = weave("M_Thread", (0.52, 0.46, 0.34), thread=0.01, rest_uv=False)
M_QUILT = quilt("M_CradleQuilt", (0.74, 0.66, 0.50), [(0.50, 0.14, 0.12), (0.16, 0.24, 0.38), (0.30, 0.38, 0.18)], diamond=0.26)
M_COVERLET = quilt("M_Coverlet", (0.62, 0.50, 0.36), [(0.50, 0.30, 0.20), (0.40, 0.36, 0.28), (0.56, 0.44, 0.26)], diamond=1.1)
M_CURTAIN = wool("M_BedHangings", (0.20, 0.25, 0.14))
M_RUG = rug_mat()
M_SAMPLER = sampler_mat()
M_RUSH = rush()
M_CUSHION = velvet("M_Pincushion", (0.25, 0.022, 0.03))
M_WAX = wax()
M_FLAME = flat("M_Flame", (1, 0.75, 0.4), emission=(1.0, 0.62, 0.25), strength=40)
M_VOID = flat("M_Shadow", (0.012, 0.009, 0.006), rough=0.9)
M_CORDIAL = flat("M_Cordial", (0.28, 0.03, 0.04), rough=0.05)
M_CRUST = painted("M_Crust", (0.55, 0.33, 0.13), rough=0.8, wear=(0.80, 0.68, 0.45))

# ----------------------------------------------------------------------------- geometry helpers
def _finish(o, mat, smooth=False):
    o.data.materials.append(mat)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    for c in o.users_collection: c.objects.unlink(o)
    return link(o)

def box(name, size, loc, mat, bevel=0.0, rot=(0, 0, 0), seg=1):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        md = o.modifiers.new("Bevel", 'BEVEL'); md.width = bevel; md.segments = seg; md.limit_method = 'ANGLE'
        if seg > 1: md.harden_normals = False
    return _finish(o, mat, smooth=seg > 1)

def cyl(name, r, h, loc, mat, verts=16, rot=(0, 0, 0), r2=None, smooth=True):
    if r2 is None: bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    else: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o = _finish(o, mat, smooth)
    if smooth:   # flat caps, smooth sides
        o.data.polygons.foreach_set("use_smooth", [len(p.vertices) == 4 for p in o.data.polygons])
    return o

def sphere(name, r, loc, mat, seg=12, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(4, seg // 2), radius=r, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return _finish(o, mat, True)

def torus(name, R, r, loc, mat, rot=(0, 0, 0), seg=20, rseg=6):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=rseg, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _finish(o, mat, True)

def lathe(name, profile, loc, mat, steps=20, rot=(0, 0, 0)):
    """profile: (radius, z) bottom to top, revolved about local Z; r == 0 collapses to a pole vertex."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for (r, z) in profile:
        if r < 1e-5: rings.append([bm.verts.new((0, 0, z))]); continue
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / steps), r * math.sin(2 * math.pi * i / steps), z)) for i in range(steps)])
    for a, b_ in zip(rings, rings[1:]):
        if len(a) == 1 and len(b_) == 1: continue
        for i in range(steps):
            j = (i + 1) % steps
            if len(a) == 1: bm.faces.new((a[0], b_[i], b_[j]))
            elif len(b_) == 1: bm.faces.new((a[i], a[j], b_[0]))
            else: bm.faces.new((a[i], a[j], b_[j], b_[i]))
    if len(rings[0]) > 1: bm.faces.new(list(reversed(rings[0])))
    if len(rings[-1]) > 1: bm.faces.new(rings[-1])
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot; me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def prism(name, pts, t, loc, mat, rot=(0, 0, 0)):
    """Extrude a 2D outline (counter-clockwise, in local XY) by t along local Z, centred."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bot = [bm.verts.new((x, y, -t / 2)) for x, y in pts]; top = [bm.verts.new((x, y, t / 2)) for x, y in pts]
    bm.faces.new(list(reversed(bot))); bm.faces.new(top)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot; me.materials.append(mat)
    return link(o)

def arc_band(R0, R1, a0, a1, n=12, cx=0.0, cy=0.0):
    outer = [(cx + R1 * math.cos(a0 + (a1 - a0) * i / n), cy + R1 * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    inner = [(cx + R0 * math.cos(a0 + (a1 - a0) * i / n), cy + R0 * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    return outer + list(reversed(inner))

def catmull(pts, sub=5):
    """Catmull-Rom through the points: a smooth path for thread."""
    P = [Vector(p) for p in pts]; out = []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for k in range(sub):
            t = k / sub; t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1]); return out

def tube(name, pts, r, mat, sides=6):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    pts = [Vector(p) for p in pts]; rings = []
    up = Vector((0, 0, 1))
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = t.cross(up)
        if a.length < 1e-4: a = t.cross(Vector((1, 0, 0)))
        a.normalize(); b_ = t.cross(a).normalized()
        rings.append([bm.verts.new(p + r * (math.cos(2 * math.pi * k / sides) * a + math.sin(2 * math.pi * k / sides) * b_)) for k in range(sides)])
    for ra, rb in zip(rings, rings[1:]):
        for k in range(sides):
            l = (k + 1) % sides; bm.faces.new((ra[k], ra[l], rb[l], rb[k]))
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def sheet(name, nu, nv, W, L, fn, mat):
    """A cloth grid: rest coords (u in [0,W], v in [0,L]) mapped by fn(u, v) -> (x, y, z). RestUV holds the rest
    coordinates in metres so a woven material keeps its thread spacing through folds and drapes."""
    me = bpy.data.meshes.new(name)
    verts = [fn(W * i / nu, L * j / nv) for j in range(nv + 1) for i in range(nu + 1)]
    faces = [(j * (nu + 1) + i, j * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i) for j in range(nv) for i in range(nu)]
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name="RestUV")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index; i, j = vi % (nu + 1), vi // (nu + 1)
            uv.data[li].uv = (W * i / nu, L * j / nv)
    me.validate(); me.update()
    o = bpy.data.objects.new(name, me); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)

def anchor(aid, loc):
    e = bpy.data.objects.new("anchor." + aid, None); e.empty_display_size = 0.3; e.location = loc; link(e)
    return e

def lerp(a, b, t): return a + (b - a) * t

# ----------------------------------------------------------------------------- room shell
box("Floor", (ROOM_W + 2 * WALL_T, ROOM_D + 2 * WALL_T, 1.0), (0, 0, -0.5), M_FLOOR)
box("Ceiling", (ROOM_W + 2 * WALL_T, ROOM_D + 2 * WALL_T, 1.0), (0, 0, ROOM_H + 0.5), M_CEILING)
WT = WALL_T
box("Wall_N", (ROOM_W + 2 * WT, WT, ROOM_H), (0, hy + WT / 2, ROOM_H / 2), M_WALL)
box("Wall_S", (ROOM_W + 2 * WT, WT, ROOM_H), (0, -hy - WT / 2, ROOM_H / 2), M_WALL)
# west wall around the door
ex = -hx - WT / 2
box("Wall_W_a", (WT, (DOOR_Y - DOOR_W / 2) + hy, ROOM_H), (ex, (-hy + DOOR_Y - DOOR_W / 2) / 2, ROOM_H / 2), M_WALL)
box("Wall_W_b", (WT, hy - (DOOR_Y + DOOR_W / 2), ROOM_H), (ex, (hy + DOOR_Y + DOOR_W / 2) / 2, ROOM_H / 2), M_WALL)
box("Wall_W_head", (WT, DOOR_W, ROOM_H - DOOR_H), (ex, DOOR_Y, (ROOM_H + DOOR_H) / 2), M_WALL)
# east wall around the casement
ex = hx + WT / 2
box("Wall_E_a", (WT, WIN_Y0 + hy, ROOM_H), (ex, (-hy + WIN_Y0) / 2, ROOM_H / 2), M_WALL)
box("Wall_E_b", (WT, hy - WIN_Y1, ROOM_H), (ex, (hy + WIN_Y1) / 2, ROOM_H / 2), M_WALL)
box("Wall_E_sill", (WT, WIN_Y1 - WIN_Y0, WIN_Z0), (ex, (WIN_Y0 + WIN_Y1) / 2, WIN_Z0 / 2), M_WALL)
box("Wall_E_head", (WT, WIN_Y1 - WIN_Y0, ROOM_H - WIN_Z1), (ex, (WIN_Y0 + WIN_Y1) / 2, (ROOM_H + WIN_Z1) / 2), M_WALL)
# the casement: glass set in the outer half of the deep reveal, oak frame, a mullion and a transom
WY, WW, WZ, WH = (WIN_Y0 + WIN_Y1) / 2, WIN_Y1 - WIN_Y0, (WIN_Z0 + WIN_Z1) / 2, WIN_Z1 - WIN_Z0
glass = box("WindowGlass", (0.1, WW, WH), (hx + 2.0, WY, WZ), M_GLASS)
glass.visible_shadow = False                         # the glazing must not shade the daylight that comes through it
FR = 0.9
for nm, size, loc in [("Win_FrameTop", (0.8, WW, FR), (hx + 1.8, WY, WIN_Z1 - FR / 2)), ("Win_FrameBot", (0.8, WW, FR), (hx + 1.8, WY, WIN_Z0 + FR / 2)),
                      ("Win_FrameL", (0.8, FR, WH), (hx + 1.8, WIN_Y0 + FR / 2, WZ)), ("Win_FrameR", (0.8, FR, WH), (hx + 1.8, WIN_Y1 - FR / 2, WZ)),
                      ("Win_Mullion", (0.8, 0.8, WH), (hx + 1.8, WY, WZ)), ("Win_Transom", (0.8, WW, 0.8), (hx + 1.8, WY, WIN_Z0 + WH * 0.68))]:
    box(nm, size, loc, M_TIMBER, bevel=0.08)
box("Win_SillBoard", (3.6, WW + 1.6, 0.5), (hx + 0.9, WY, WIN_Z0 - 0.25), M_OAKH, bevel=0.1)
# casement leaves' iron stays
box("Win_Stay", (0.12, 3.0, 0.12), (hx + 1.5, WY + 3.0, WIN_Z0 + 0.4), M_IRON)

# skirting, timber posts at the corners, and the ceiling: a summer beam with joists
SK = 1.8
for nm, size, loc in [("Skirt_N", (ROOM_W, 0.35, SK), (0, hy - 0.175, SK / 2)), ("Skirt_S", (ROOM_W, 0.35, SK), (0, -hy + 0.175, SK / 2)),
                      ("Skirt_E", (0.35, ROOM_D, SK), (hx - 0.175, 0, SK / 2)),
                      ("Skirt_Wa", (0.35, DOOR_Y - DOOR_W / 2 - 1.2 + hy, SK), (-hx + 0.175, (-hy + DOOR_Y - DOOR_W / 2 - 1.2) / 2, SK / 2)),
                      ("Skirt_Wb", (0.35, hy - DOOR_Y - DOOR_W / 2 - 1.2, SK), (-hx + 0.175, (hy + DOOR_Y + DOOR_W / 2 + 1.2) / 2, SK / 2))]:
    box(nm, size, loc, M_TIMBER)
for sx in (-1, 1):
    for sy in (-1, 1):
        box(f"Post_{sx}{sy}", (2.2, 2.2, ROOM_H), (sx * (hx - 1.1), sy * (hy - 1.1), ROOM_H / 2), M_TIMBER, bevel=0.15)
box("SummerBeam", (2.6, ROOM_D, 3.0), (0, 0, ROOM_H - 1.5), M_TIMBER, bevel=0.2)
box("WallPlate_E", (1.6, ROOM_D, 1.8), (hx - 0.8, 0, ROOM_H - 0.9), M_TIMBER, bevel=0.1)
box("WallPlate_W", (1.6, ROOM_D, 1.8), (-hx + 0.8, 0, ROOM_H - 0.9), M_TIMBER, bevel=0.1)
for i in range(-4, 5):
    y = i * 6.4
    box(f"Joist_{i}", (ROOM_W, 1.0, 1.3), (0, y, ROOM_H - 0.65), M_TIMBER)
box("Lintel_E", (1.2, WW + 3.0, 1.4), (hx - 0.6, WY, WIN_Z1 + 0.7), M_TIMBER)

# the door: a six-panel oak door in a heavy frame, iron latch, standing a little open
dx = -hx
for nm, size, loc in [("DoorCase_L", (1.0, 1.2, DOOR_H + 1.2), (dx + 0.5, DOOR_Y - DOOR_W / 2 - 0.6, (DOOR_H + 1.2) / 2)),
                      ("DoorCase_R", (1.0, 1.2, DOOR_H + 1.2), (dx + 0.5, DOOR_Y + DOOR_W / 2 + 0.6, (DOOR_H + 1.2) / 2)),
                      ("DoorCase_T", (1.0, DOOR_W + 2.4, 1.2), (dx + 0.5, DOOR_Y, DOOR_H + 0.6))]:
    box(nm, size, loc, M_TIMBER, bevel=0.1)
box("DoorBeyond", (0.2, DOOR_W, DOOR_H), (dx - WT + 0.2, DOOR_Y, DOOR_H / 2), M_VOID)   # the dark passage beyond
DOOR_OPEN = math.radians(24)
hinge = Vector((dx + 0.25, DOOR_Y + DOOR_W / 2, 0))
def door_pt(along, out, z):
    """along: from the hinge towards the latch edge; out: into the room."""
    c, s = math.cos(DOOR_OPEN), math.sin(DOOR_OPEN)
    return (hinge.x + along * s + out * c, hinge.y - along * c + out * s, z)
dl = box("Door_Leaf", (0.55, DOOR_W, DOOR_H), door_pt(DOOR_W / 2, 0.3, DOOR_H / 2), M_OAK, rot=(0, 0, DOOR_OPEN))
for row, (z0, z1) in enumerate([(1.5, 7.5), (8.7, 15.9), (17.1, 22.8)]):
    for col in range(2):
        a0, a1 = 1.2 + col * (DOOR_W - 1.2) / 2, (col + 1) * (DOOR_W - 1.2) / 2
        box(f"Door_Panel{row}{col}", (0.25, a1 - a0 - 0.2, z1 - z0), door_pt((a0 + a1) / 2, 0.65, (z0 + z1) / 2), M_OAK, bevel=0.2, rot=(0, 0, DOOR_OPEN))
box("Door_Latch", (0.2, 1.6, 0.25), door_pt(DOOR_W - 1.2, 0.7, 12.0), M_IRON, rot=(0, 0, DOOR_OPEN))
cyl("Door_LatchKnob", 0.18, 0.5, door_pt(DOOR_W - 1.0, 0.9, 11.5), M_IRON, verts=8, rot=(0, math.radians(90), DOOR_OPEN))
for z in (3.0, 20.5):
    box(f"Door_Strap{z}", (0.12, 4.5, 0.6), door_pt(2.25, 0.62, z), M_IRON, rot=(0, 0, DOOR_OPEN))

# ----------------------------------------------------------------------------- the work table (the reader stands on its top)
box("TableTop", (TW, TL, TOP_T), (TX, TY, Z - TOP_T / 2), M_TABLETOP, bevel=0.06)
AP = 1.4
LEG = 0.8
for s in (-1, 1):
    box(f"Apron_X{s}", (TW - 0.8, 0.3, AP), (TX, TY + s * (TL / 2 - 0.6), Z - TOP_T - AP / 2), M_TABLEFRAMEH, bevel=0.04)
    box(f"Apron_Y{s}", (0.3, TL - 1.2, AP), (TX + s * (TW / 2 - 0.6), TY, Z - TOP_T - AP / 2), M_TABLEFRAMEH, bevel=0.04)
for sx in (-1, 1):
    for sy in (-1, 1):
        lx, ly = TX + sx * (TW / 2 - 0.75), TY + sy * (TL / 2 - 0.75)
        # turned baluster legs: block at the apron, vase-and-ring turning, block foot
        box(f"LegBlock{sx}{sy}", (LEG, LEG, AP + 0.2), (lx, ly, Z - TOP_T - AP / 2), M_TABLEFRAME, bevel=0.04)
        h0, h1 = 1.0, Z - TOP_T - AP - 0.1
        lathe(f"LegTurn{sx}{sy}", [(0.40, h0), (0.30, h0 + 0.3), (0.26, h0 + 1.2), (0.34, h0 + 2.3), (0.36, h0 + 2.9), (0.28, h0 + 3.6), (0.2, h0 + 4.4),
                                    (0.24, h1 - 0.7), (0.34, h1 - 0.4), (0.36, h1 - 0.2), (0.40, h1)], (lx, ly, 0), M_TABLEFRAME, steps=14)
        box(f"LegFoot{sx}{sy}", (LEG, LEG, 1.0), (lx, ly, 0.5), M_TABLEFRAME, bevel=0.04)
for s in (-1, 1):   # low stretchers
    box(f"Stretcher_Y{s}", (0.4, TL - 1.5, 0.6), (TX + s * (TW / 2 - 0.75), TY, 1.3), M_TABLEFRAMEH)
box("Stretcher_X", (TW - 1.5, 0.4, 0.6), (TX, TY, 1.3), M_TABLEFRAMEH)
# the table's own drawer under the top, facing the reader's side of the room
box("TableDrawerFront", (3.2, 0.15, AP - 0.4), (TX, TY0 + 0.52, Z - TOP_T - AP / 2), M_TABLEFRAMEH, bevel=0.05)
cyl("TableDrawerKnob", 0.16, 0.3, (TX, TY0 + 0.32, Z - TOP_T - AP / 2), M_BRASS, verts=10, rot=(math.radians(90), 0, 0))

# ----------------------------------------------------------------------------- the cabinet drawer with the doll's cradle (Gulliver's bed)
DRW_X0, DRW_Y0, DW, DD, DH, DT = 10.1, -6.9, 3.6, 3.0, 0.55, 0.15
dcx, dcy = DRW_X0 + DW / 2, DRW_Y0 + DD / 2
box("Drawer_Bottom", (DW - 0.1, DD - 0.1, 0.12), (dcx, dcy, Z + 0.06), M_PINE)
box("Drawer_Back", (DW - 0.2, DT, DH * 0.92), (dcx, DRW_Y0 + DD - DT / 2, Z + DH * 0.46), M_PINE, bevel=0.02)
for s in (-1, 1):
    box(f"Drawer_Side{s}", (DT, DD - 0.22, DH), (dcx + s * (DW / 2 - DT / 2), dcy + 0.05, Z + DH / 2), M_PINE, bevel=0.02)
box("Drawer_Front", (DW + 0.12, 0.22, DH + 0.08), (dcx, DRW_Y0 + 0.11, Z + (DH + 0.08) / 2), M_OAKH, bevel=0.05)
lathe("Drawer_Knob", [(0.09, 0), (0.07, 0.08), (0.12, 0.16), (0.10, 0.22), (0.0, 0.24)], (dcx, DRW_Y0, Z + 0.32), M_BRASS, steps=12, rot=(math.radians(90), 0, 0))
# the cradle: a hooded doll's cradle, long axis along x, hood at the east end, on two rockers
CX0, CY0, CZ0 = dcx, dcy + 0.05, Z + 0.12
def cpt(x, y, z): return (CX0 + x, CY0 + y, CZ0 + z)
CL, CWD = 2.2, 0.92
for i, rx in enumerate((-0.85, 0.85)):
    prism(f"Cradle_Rocker{i}", arc_band(1.05, 1.22, math.radians(240), math.radians(300), n=10, cy=1.24), 0.09, cpt(rx, 0, 0), M_CRADLE, rot=(math.radians(90), 0, math.radians(90)))
box("Cradle_Floor", (CL, CWD - 0.1, 0.07), cpt(0, 0, 0.28), M_CRADLE)
for s in (-1, 1):
    box(f"Cradle_Side{s}", (CL, 0.07, 0.56), cpt(0, s * CWD / 2, 0.55), M_CRADLE, bevel=0.02, rot=(s * math.radians(-8), 0, 0))
box("Cradle_Foot", (0.07, CWD + 0.08, 0.6), cpt(-CL / 2, 0, 0.56), M_CRADLE, bevel=0.02)
box("Cradle_Head", (0.07, CWD + 0.1, 1.06), cpt(CL / 2, 0, 0.78), M_CRADLE, bevel=0.02)
for s in (-1, 1):
    sphere(f"Cradle_Finial{s}", 0.07, cpt(-CL / 2, s * (CWD / 2 + 0.02), 0.92), M_CRADLE, seg=8)
# the hood: an arched canopy over the head end, open towards the foot
me = bpy.data.meshes.new("Cradle_Hood"); bm = bmesh.new()
hw = CWD / 2 + 0.07
prof = [(-hw, 0.62), (-hw, 1.08)] + [(-hw * math.cos(math.pi * k / 10), 1.08 + 0.26 * math.sin(math.pi * k / 10)) for k in range(1, 10)] + [(hw, 1.08), (hw, 0.62)]
cols = [[bm.verts.new((CL / 2 - 0.72 + 0.74 * t, y, z)) for (y, z) in prof] for t in (0, 1)]
for i in range(len(prof) - 1): bm.faces.new((cols[0][i], cols[0][i + 1], cols[1][i + 1], cols[1][i]))
bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.06)
bm.to_mesh(me); bm.free()
ho = bpy.data.objects.new("Cradle_Hood", me); ho.location = cpt(0, 0, 0); me.materials.append(M_CRADLE); link(ho)
tube("Cradle_HoodRim", [cpt(CL / 2 - 0.72, y, z) for (y, z) in prof], 0.04, M_CRADLE, sides=6)
# bedding: the quilt of her baby's bed, a pillow, a turned-down sheet
box("Cradle_Quilt", (CL - 0.55, CWD - 0.12, 0.2), cpt(-0.25, 0, 0.42), M_QUILT, bevel=0.07, seg=3)
sphere("Cradle_Pillow", 0.3, cpt(CL / 2 - 0.33, 0, 0.5), M_PILLOW, seg=12, scale=(0.75, 1.4, 0.38))
box("Cradle_SheetTurn", (0.3, CWD - 0.1, 0.06), cpt(0.33, 0, 0.53), M_PILLOW, bevel=0.025, seg=2)

# ----------------------------------------------------------------------------- the travelling box ("a little door for me to go in and out, and a few gimlet holes")
BX0, BY0, BW, BD, BH, BT = 7.0, -3.5, 2.1, 1.75, 1.75, 0.09
bcx, bcy = BX0 + BW / 2, BY0 + BD / 2
DW2, DH2, DXO = 0.82, 1.32, -0.25              # the little door (in the south face, facing the reader), offset from centre
box("Box_Bottom", (BW, BD, BT), (bcx, bcy, Z + BT / 2), M_PINE, bevel=0.02)
box("Box_Top", (BW + 0.08, BD + 0.08, BT), (bcx, bcy, Z + BH - BT / 2), M_PINE, bevel=0.03)
box("Box_Back", (BW, BT, BH - 2 * BT), (bcx, BY0 + BD - BT / 2, Z + BH / 2), M_PINE)
for s in (-1, 1):
    box(f"Box_Side{s}", (BT, BD - 2 * BT, BH - 2 * BT), (bcx + s * (BW / 2 - BT / 2), bcy, Z + BH / 2), M_PINE)
dx0, dx1 = bcx + DXO - DW2 / 2, bcx + DXO + DW2 / 2
box("Box_FrontL", (dx0 - BX0, BT, BH - 2 * BT), ((BX0 + dx0) / 2, BY0 + BT / 2, Z + BH / 2), M_PINE)
box("Box_FrontR", (BX0 + BW - dx1, BT, BH - 2 * BT), ((dx1 + BX0 + BW) / 2, BY0 + BT / 2, Z + BH / 2), M_PINE)
box("Box_FrontT", (DW2, BT, BH - 2 * BT - DH2), (bcx + DXO, BY0 + BT / 2, Z + BT + DH2 + (BH - 2 * BT - DH2) / 2), M_PINE)
box("Box_Lining", (BW - 2 * BT - 0.02, BD - 2 * BT - 0.02, 0.18), (bcx, bcy, Z + BT + 0.09), M_QUILT, bevel=0.06, seg=2)
box("Box_Interior", (BW - 2 * BT - 0.01, 0.02, BH - 2 * BT - 0.01), (bcx, BY0 + BD - BT - 0.02, Z + BH / 2), M_VOID)
BOX_DOOR = math.radians(-150)
hp = Vector((dx0, BY0, 0))
cdr, sdr = math.cos(BOX_DOOR), math.sin(BOX_DOOR)
def bdoor(a, o, z): return (hp.x + a * cdr - o * sdr, hp.y + a * sdr + o * cdr, z)
box("Box_Door", (DW2 - 0.02, 0.06, DH2 - 0.02), bdoor(DW2 / 2, -0.03, Z + BT + DH2 / 2), M_PINE, bevel=0.015, rot=(0, 0, BOX_DOOR))
sphere("Box_DoorKnob", 0.045, bdoor(DW2 - 0.12, -0.1, Z + BT + DH2 * 0.55), M_BRASS, seg=8)
for z in (0.25, DH2 - 0.25):
    box(f"Box_Hinge{z:.2f}", (0.2, 0.03, 0.08), (dx0 - 0.02, BY0 - 0.015, Z + BT + z), M_IRON)
# gimlet holes (3 mm in their world, ~4 cm to the reader)
for face, (ox, oy, nrm) in {"S": (None, BY0 - 0.005, (0, 1)), "E": (BX0 + BW + 0.005, None, (1, 0)), "W": (BX0 - 0.005, None, (1, 0))}.items():
    for k in range(5):
        hz = Z + BH - 0.32 - (k % 2) * 0.18
        if face == "S":
            hx_ = dx1 + 0.18 + k * 0.17
            if hx_ > BX0 + BW - 0.1: continue
            cyl(f"Box_Hole{face}{k}", 0.025, 0.02, (hx_, oy, hz), M_VOID, verts=8, rot=(math.radians(90), 0, 0), smooth=False)
        else:
            cyl(f"Box_Hole{face}{k}", 0.025, 0.02, (ox, BY0 + 0.3 + k * 0.29, hz), M_VOID, verts=8, rot=(0, math.radians(90), 0), smooth=False)
# the carrying ring on the lid, and a leather girdle strap
box("Box_Staple", (0.12, 0.1, 0.12), (bcx, bcy, Z + BH + 0.05), M_IRON)
torus("Box_Ring", 0.2, 0.035, (bcx, bcy, Z + BH + 0.28), M_IRON, rot=(math.radians(90), 0, 0), seg=16)
for s in (-1, 1):
    box(f"Box_Corner{s}", (0.14, 0.14, BH + 0.02), (bcx + s * (BW / 2), BY0, Z + BH / 2), M_BRASS, bevel=0.02)

# ----------------------------------------------------------------------------- the chamber candlestick (Lamp0)
KX, KY = 8.0, -5.6
lathe("Lamp0_Candlestick", [(0.0, 0.0), (0.86, 0.0), (0.88, 0.05), (0.86, 0.15), (0.80, 0.16), (0.76, 0.08), (0.24, 0.07), (0.2, 0.12), (0.26, 0.2),
                            (0.17, 0.28), (0.14, 0.5), (0.2, 0.56), (0.21, 0.62), (0.17, 0.64), (0.165, 0.95), (0.22, 0.97), (0.22, 1.0), (0.15, 1.0), (0.0, 0.98)],
      (KX, KY, Z), M_BRASS, steps=28)
torus("Lamp0_Handle", 0.2, 0.045, (KX + 0.98, KY, Z + 0.28), M_BRASS, rot=(math.radians(90), 0, 0), seg=16)
box("Lamp0_HandleTab", (0.3, 0.12, 0.06), (KX + 0.84, KY, Z + 0.14), M_BRASS)
CAND_TOP = Z + 2.6
lathe("Lamp0_Candle", [(0.0, Z + 0.9), (0.13, Z + 0.9), (0.13, CAND_TOP - 0.05), (0.12, CAND_TOP), (0.07, CAND_TOP - 0.03), (0.0, CAND_TOP - 0.04)], (KX, KY, 0), M_WAX, steps=16)
for i, (a, zz, ln) in enumerate([(0.4, 2.35, 0.32), (2.3, 2.2, 0.5), (4.1, 2.42, 0.2)]):
    sphere(f"Lamp0_Drip{i}", 0.04, (KX + 0.125 * math.cos(a), KY + 0.125 * math.sin(a), Z + zz), M_WAX, seg=8, scale=(1, 1, ln / 0.08))
cyl("Lamp0_Wick", 0.012, 0.14, (KX, KY, CAND_TOP + 0.04), M_VOID, verts=6, rot=(0.15, 0, 0))
FLAME_Z = CAND_TOP + 0.26
sphere("Lamp0_Flame", 0.06, (KX, KY, FLAME_Z), M_FLAME, seg=10, scale=(1, 1, 3.2))

# ----------------------------------------------------------------------------- her sewing: linen, needle and thread, spool, pincushion, pins, scissors, thimble
# the linen (a shirt in the making), lying on the table and hanging over its west edge; RestUV keeps the weave true
LIN_X1, LIN_Y0, LIN_W, LIN_L = 9.3, -9.6, 6.6, 3.8     # u runs west from x = LIN_X1, across the edge and down
EDGE_R = 0.12
def linen_fn(u, v):
    on_top = LIN_X1 - TX0                     # length of cloth that lies on the table
    y = LIN_Y0 + v
    wav = 0.07 * math.sin(v * 2.1 + u * 0.7) + 0.05 * math.sin(u * 3.3 - v * 1.3) + 0.03 * math.sin(u * 7.1 + v * 4.3)
    # two loose folds running along v across the top part
    fold = 0.28 * math.exp(-((u - 1.4) / 0.4) ** 2) * (0.6 + 0.4 * math.sin(v * 1.4)) + 0.16 * math.exp(-((u - 2.6) / 0.3) ** 2) * (0.5 + 0.5 * math.sin(v * 2.0 + 1))
    corner = max(0.0, (0.9 - v) / 0.9) * max(0.0, 1 - u / 2.0) * 0.3       # a corner lifted, turned back
    if u <= on_top:
        return (LIN_X1 - u, y, Z + 0.015 + max(0.0, wav) + fold + corner)
    s = u - on_top                            # distance past the edge: round the arris, then hang
    if s < EDGE_R * math.pi / 2:
        a = s / EDGE_R
        return (TX0 - EDGE_R * math.sin(a) + 0.02, y, Z + 0.015 - EDGE_R * (1 - math.cos(a)))
    d = s - EDGE_R * math.pi / 2
    pleat = 0.16 * math.sin(v * 2.6 + 0.5) * min(1.0, d / 0.8) + 0.06 * math.sin(v * 6.1) * min(1.0, d / 1.5)
    return (TX0 - EDGE_R - 0.02 - pleat - 0.04 * d, y + 0.08 * d * math.sin(v * 1.7), Z + 0.015 - EDGE_R - d)
sheet("Linen", 48, 26, LIN_W, LIN_L, linen_fn, M_LINEN)
# rolled hems on the three free edges (a 3 mm hem in life)
tube("LinenHem0", [linen_fn(LIN_W * i / 48, 0.0) for i in range(49)], 0.025, M_THREAD, sides=5)
tube("LinenHem1", [linen_fn(LIN_W * i / 48, LIN_L) for i in range(49)], 0.025, M_THREAD, sides=5)
tube("LinenHem2", [linen_fn(0.0, LIN_L * j / 26) for j in range(27)], 0.025, M_THREAD, sides=5)
# a second, folded piece: cut shirt parts, stacked
for i in range(3):
    box(f"LinenFolded{i}", (1.5 - i * 0.12, 1.1 - i * 0.08, 0.07), (12.6 + i * 0.03, -12.9 + i * 0.05, Z + 0.035 + i * 0.07), M_PILLOW, bevel=0.03, seg=2,
        rot=(0, 0, math.radians(8 - i * 5)))
# the needle, lying across the cloth (5 cm in life: 60 cm and 1.2 cm thick here), threaded
NX, NY = 8.6, -8.2
NEEDLE_YAW = math.radians(-24)
def linen_z(x, y): return linen_fn(LIN_X1 - x, y - LIN_Y0)[2]
_nd = Vector((math.cos(NEEDLE_YAW), math.sin(NEEDLE_YAW), 0))
NZ = max(linen_z(NX + _nd.x * t, NY + _nd.y * t) for t in (-0.3, -0.15, 0, 0.15, 0.3)) + 0.014
lathe("Needle", [(0.0, -0.31), (0.004, -0.29), (0.011, -0.2), (0.012, 0.22), (0.009, 0.28), (0.011, 0.3), (0.0, 0.31)], (NX, NY, NZ), M_STEEL, steps=8,
      rot=(0, math.radians(90), NEEDLE_YAW))
eye = Vector((NX, NY, NZ)) + 0.29 * _nd
# the spool, standing near the reader's left, with thread running out to the needle's eye
SPX, SPY = 7.3, -11.6
lathe("Spool", [(0.0, 0.0), (0.21, 0.0), (0.22, 0.05), (0.18, 0.07), (0.12, 0.08), (0.12, 0.52), (0.18, 0.53), (0.22, 0.55), (0.21, 0.6), (0.06, 0.6), (0.06, 0.55), (0.0, 0.55)],
      (SPX, SPY, Z), M_PINE, steps=18)
cyl("SpoolThread", 0.17, 0.43, (SPX, SPY, Z + 0.3), M_THREAD, verts=18)
tp = [(SPX + 0.17, SPY + 0.02, Z + 0.42), (SPX + 0.34, SPY + 0.12, Z + 0.12), (SPX + 0.55, SPY + 0.3, Z + 0.012), (SPX + 0.9, SPY + 0.55, Z + 0.012),
      (SPX + 1.2, SPY + 1.0, Z + 0.012), (SPX + 1.15, SPY + 1.5, Z + 0.012), (SPX + 0.95, SPY + 1.9, Z + 0.018), (SPX + 1.0, SPY + 2.25, Z + 0.035),
      (eye.x - 0.25, eye.y - 0.3, Z + 0.05), (eye.x - 0.08, eye.y - 0.06, Z + 0.06), tuple(eye)]
tube("Thread", catmull(tp), 0.006, M_THREAD, sides=5)
tube("ThreadTail", [tuple(eye), (eye.x + 0.06, eye.y + 0.12, Z + 0.06), (eye.x - 0.1, eye.y + 0.4, Z + 0.05), (eye.x - 0.3, eye.y + 0.5, Z + 0.045)], 0.006, M_THREAD, sides=5)
# the pincushion (a tomato of red velvet, 9 cm across in life) with brass pins (pins of their world: 40 cm, 8 mm thick here)
PX, PY, PR = 10.75, -8.5, 0.55
po = sphere("Pincushion", PR, (PX, PY, Z + PR * 0.5), M_CUSHION, seg=24, scale=(1, 1, 0.55))
for v in po.data.vertices:
    rel = v.co - Vector((PX, PY, Z + PR * 0.5)); ang = math.atan2(rel.y, rel.x)
    k = 1 - 0.07 * abs(math.sin(4 * ang)) * max(0.0, 1 - abs(rel.z) / (PR * 0.6))
    v.co = Vector((PX, PY, Z + PR * 0.5)) + Vector((rel.x * k, rel.y * k, rel.z))
torus("PincushionCord", 0.1, 0.03, (PX, PY, Z + PR * 1.05), M_BRASS, seg=12, rot=(0, 0, 0))
for i in range(11):
    a = random.uniform(0, 2 * math.pi); rr = random.uniform(0.1, 0.4); tilt = random.uniform(0.15, 0.6)
    base = Vector((PX + rr * math.cos(a), PY + rr * math.sin(a), Z + PR * 0.5 + PR * 0.5 * math.sqrt(max(0, 1 - (rr / PR) ** 2))))
    d = Vector((math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt)))
    top = base + d * random.uniform(0.18, 0.28)
    tube(f"Pin{i}", [tuple(base - d * 0.12), tuple(top)], 0.008, M_STEEL, sides=5)
    sphere(f"PinHead{i}", 0.026, tuple(top), M_BRASS, seg=6)
# a pin dropped on the table
tube("PinLoose", [(11.3, -10.1, Z + 0.01), (11.66, -10.25, Z + 0.01)], 0.008, M_STEEL, sides=5)
sphere("PinLooseHead", 0.026, (11.68, -10.26, Z + 0.026), M_BRASS, seg=6)
# the thimble, filled with cordial: "a thimble filled with liquor ... for a cup"
THX, THY = 8.2, -10.0
lathe("Thimble", [(0.0, 0.0), (0.11, 0.0), (0.114, 0.012), (0.114, 0.03), (0.108, 0.04), (0.104, 0.2), (0.095, 0.24), (0.07, 0.265), (0.0, 0.272)],
      (THX, THY, Z), M_THIMBLE, steps=24, rot=(math.pi, 0, 0))
o = bpy.data.objects["Thimble"]; o.location = (THX, THY, Z + 0.272)
cyl("ThimbleCordial", 0.098, 0.01, (THX, THY, Z + 0.23), M_CORDIAL, verts=20)
# open scissors lying by the folded linen: blades on a pivot, two bows
SCX, SCY, SCYAW = 11.7, -11.9, math.radians(70)
def blade(name, ang):
    pts = [(-0.1, -0.06), (0.15, -0.075), (0.75, -0.03), (0.9, 0.0), (0.7, 0.03), (0.15, 0.06), (-0.1, 0.05)]
    prism(name, pts, 0.03, (SCX, SCY, Z + 0.02 + (0.03 if ang > 0 else 0)), M_STEEL, rot=(0, 0, SCYAW + ang))
    shank = [(SCX + 0.0, SCY), (SCX - 0.35 * math.cos(SCYAW + ang), SCY - 0.35 * math.sin(SCYAW + ang))]
    tube(name + "_Shank", [(shank[0][0], shank[0][1], Z + 0.03), (shank[1][0], shank[1][1], Z + 0.03)], 0.025, M_STEEL, sides=6)
    cx_, cy_ = SCX - 0.5 * math.cos(SCYAW + ang), SCY - 0.5 * math.sin(SCYAW + ang)
    torus(name + "_Bow", 0.14, 0.03, (cx_, cy_, Z + 0.03), M_STEEL, seg=16)
blade("ScissorBladeA", math.radians(14)); blade("ScissorBladeB", math.radians(-14))
cyl("ScissorPivot", 0.04, 0.09, (SCX, SCY, Z + 0.045), M_BRASS, verts=8)
# a crust of bread ("I happened to stumble against a crust")
sphere("Crust", 0.3, (12.9, -1.9, Z + 0.1), M_CRUST, seg=10, scale=(1.3, 0.7, 0.4), rot=(0, 0, 0.6))

# ----------------------------------------------------------------------------- the girl's bed: four-poster with curtains, head to the north wall
BEDX0, BEDX1, BEDY0, BEDY1 = -3.0, 11.4, 7.4, 29.6
BX, BYc = (BEDX0 + BEDX1) / 2, (BEDY0 + BEDY1) / 2
BWID, BLEN = BEDX1 - BEDX0, BEDY1 - BEDY0
POST_H, TESTER_Z = 26.4, 25.2
MAT_TOP = 7.2
for px in (BEDX0 + 0.6, BEDX1 - 0.6):
    for py in (BEDY0 + 0.6, BEDY1 - 0.6):
        foot = py < BYc
        box(f"BedPostBase{px:.0f}{py:.0f}", (1.3, 1.3, 4.2), (px, py, 2.1), M_OAK, bevel=0.08)
        if foot:   # turned foot posts
            lathe(f"BedPost{px:.0f}{py:.0f}", [(0.62, 4.2), (0.5, 4.8), (0.62, 5.6), (0.42, 7.0), (0.35, 9.5), (0.55, 12.5), (0.6, 13.5), (0.45, 14.5), (0.32, 17.0), (0.28, 22.0), (0.36, 24.6), (0.3, POST_H)],
                  (px, py, 0), M_OAK, steps=12)
        else:
            box(f"BedPost{px:.0f}{py:.0f}", (0.8, 0.8, POST_H - 4.2), (px, py, (POST_H + 4.2) / 2), M_OAK, bevel=0.05)
# rails, headboard, tester frame, cornice
box("BedRail_L", (0.6, BLEN - 1.2, 1.6), (BEDX0 + 0.6, BYc, 4.2), M_OAKH)
box("BedRail_R", (0.6, BLEN - 1.2, 1.6), (BEDX1 - 0.6, BYc, 4.2), M_OAKH)
box("BedRail_F", (BWID - 1.2, 0.6, 1.6), (BX, BEDY0 + 0.6, 4.2), M_OAKH)
box("BedHeadboard", (BWID - 1.2, 0.5, 9.0), (BX, BEDY1 - 0.7, MAT_TOP + 3.0), M_OAKH, bevel=0.1)
for i in range(3):
    box(f"BedHeadPanel{i}", (3.4, 0.2, 5.5), (BEDX0 + 2.6 + i * 4.6, BEDY1 - 0.98, MAT_TOP + 3.4), M_OAKH, bevel=0.15)
for nm, size, loc in [("Tester_F", (BWID + 0.4, 0.7, 1.4), (BX, BEDY0 + 0.6, TESTER_Z + 0.7)), ("Tester_B", (BWID + 0.4, 0.7, 1.4), (BX, BEDY1 - 0.6, TESTER_Z + 0.7)),
                      ("Tester_L", (0.7, BLEN, 1.4), (BEDX0 + 0.6, BYc, TESTER_Z + 0.7)), ("Tester_R", (0.7, BLEN, 1.4), (BEDX1 - 0.6, BYc, TESTER_Z + 0.7))]:
    box(nm, size, loc, M_OAKH, bevel=0.08)
box("TesterCloth", (BWID - 0.6, BLEN - 0.6, 0.12), (BX, BYc, TESTER_Z + 1.3), M_CURTAIN)
# mattress, coverlet hanging to near the floor, bolster and pillows
box("BedMattress", (BWID - 1.4, BLEN - 2.0, 2.4), (BX, BYc, MAT_TOP - 1.2), M_PILLOW, bevel=0.5, seg=3)
CV_R = 0.6
def roll(d):
    """Cloth running d metres past a rounded mattress edge: (outward, downward)."""
    if d <= 0: return 0.0, 0.0
    if d < CV_R * math.pi / 2:
        a = d / CV_R; return CV_R * math.sin(a), CV_R * (1 - math.cos(a))
    return CV_R, CV_R + d - CV_R * math.pi / 2
CV_TW = BWID - 1.4 - 2 * CV_R                 # flat top width
CV_TL = BLEN - 2.0 - CV_R                     # flat top length (head end tucked under the bolster)
CV_D = MAT_TOP - 1.4
def coverlet_fn(u, v):
    xr = u - (CV_TW / 2 + CV_D)
    side = abs(xr) - CV_TW / 2
    so, sd = roll(side)
    fo, fd = roll(v - CV_TL)
    xx = BX + math.copysign(min(abs(xr), CV_TW / 2) + so, xr)
    yy = BEDY1 - 1.0 - min(v, CV_TL) - fo
    zz = MAT_TOP + 0.08 + 0.1 * math.sin(v * 0.5 + u * 0.3) * (1 if side <= 0 else 0.3) - sd - fd
    if side > 0.8: xx += math.copysign(0.25 * math.sin(v * 1.3) * min(1.0, (side - 0.8) / 2.0), xr)
    if v - CV_TL > 0.8: yy -= 0.25 * math.sin(u * 1.1) * min(1.0, (v - CV_TL - 0.8) / 2.0)
    return (xx, yy, max(zz, 1.4))
sheet("BedCoverlet", 44, 40, CV_TW + 2 * CV_D, CV_TL + CV_D, coverlet_fn, M_COVERLET)
box("BedBolster", (BWID - 2.4, 1.8, 1.5), (BX, BEDY1 - 2.3, MAT_TOP + 0.9), M_PILLOW, bevel=0.65, seg=4)
for s in (-1, 1):
    sphere(f"BedPillow{s}", 1.6, (BX + s * 3.0, BEDY1 - 3.8, MAT_TOP + 1.4), M_PILLOW, seg=16, scale=(1.75, 1.0, 0.45), rot=(math.radians(-25), 0, 0))
# a white handkerchief laid on the coverlet ("covered me with a clean white handkerchief")
def hank_fn(u, v):
    return (BX - 1.0 + u + 0.06 * math.sin(v * 3), BEDY0 + 6.0 + v, MAT_TOP + 0.42 + 0.05 * math.sin(u * 2.3) + 0.12 * math.exp(-((u - 1.6) / 0.5) ** 2))
sheet("Handkerchief", 10, 10, 3.6, 3.6, hank_fn, M_LINEN)
# hangings: head cloth, and four curtains: the foot pair tied back at the posts, the head pair hanging straight
box("BedHeadCloth", (BWID - 1.6, 0.12, TESTER_Z - MAT_TOP - 9.0 + 3.0), (BX, BEDY1 - 0.5, (TESTER_Z + MAT_TOP + 6.0) / 2), M_CURTAIN)
def curtain(name, x_post, y0, y1, tie_z, tie_frac, gather_side, folds=9, amp=0.45):
    """A curtain hung from the tester rail along y (y0..y1) at x_post, drawn towards gather_side (-1 = towards y0)."""
    L = y1 - y0
    def fn(u, v):            # u along the rail, v down from the tester
        t = u / L
        z = TESTER_Z - v
        # gathering: above the tie the curtain spreads to full width, at the tie it narrows to tie_frac
        h = TESTER_Z - tie_z
        if v < h: g = lerp(1.0, tie_frac, (v / h) ** 1.6)
        else: g = lerp(tie_frac, tie_frac * 1.8, min(1.0, (v - h) / max(1.0, z - 1.0 + (v - h))))
        anchor_y = y0 if gather_side < 0 else y1
        yy = anchor_y + (u - (0 if gather_side < 0 else L)) * g
        a = amp * (1.0 + 2.0 * (1 - g))
        xx = x_post + a * math.sin(t * folds * math.pi * 2)
        return (xx, yy, max(z, 0.4))
    return sheet(name, 40, 18, L, TESTER_Z - 0.4, fn, M_CURTAIN)
curtain("BedCurtain_FL", BEDX0 + 0.7, BEDY0 + 0.8, BEDY0 + 7.0, 13.0, 0.3, -1)
curtain("BedCurtain_FR", BEDX1 - 0.7, BEDY0 + 0.8, BEDY0 + 7.0, 13.0, 0.3, -1)
curtain("BedCurtain_HL", BEDX0 + 0.7, BEDY1 - 7.5, BEDY1 - 0.8, 30.0, 0.55, 1, folds=7)
curtain("BedCurtain_HR", BEDX1 - 0.7, BEDY1 - 7.5, BEDY1 - 0.8, 30.0, 0.55, 1, folds=7)
for s, px in ((0, BEDX0 + 0.7), (1, BEDX1 - 0.7)):
    torus(f"BedTieBack{s}", 0.75, 0.16, (px, BEDY0 + 0.8 + 0.6, 13.0), M_BRASS, seg=12, rot=(0, math.radians(90), 0))
# valances along the tester
for nm, size, loc in [("Valance_F", (BWID + 0.6, 0.15, 2.4), (BX, BEDY0 + 0.15, TESTER_Z - 0.2)), ("Valance_L", (0.15, BLEN, 2.4), (BEDX0 + 0.15, BYc, TESTER_Z - 0.2)),
                      ("Valance_R", (0.15, BLEN, 2.4), (BEDX1 - 0.15, BYc, TESTER_Z - 0.2))]:
    box(nm, size, loc, M_CURTAIN)
for i in range(13):
    box(f"ValanceFringe{i}", (0.3, 0.2, 0.6), (BEDX0 + 0.5 + i * BWID / 12.4, BEDY0 + 0.13, TESTER_Z - 1.7), M_BRASS)

# braided rag rug by the bed, under the table's north end
rug = cyl("RagRug", 6.0, 0.2, (2.0, 3.2, 0.1), M_RUG, verts=40, smooth=False)
rug.data.transform(Matrix.Diagonal((1.4, 1.0, 1.0, 1.0)))

# ----------------------------------------------------------------------------- the cabinet (chest of drawers on a stand) on the north wall: one small drawer gone
CAX0, CAX1, CAD = -21.0, -8.6, 6.0
cax, caw = (CAX0 + CAX1) / 2, CAX1 - CAX0
CY_FRONT = hy - CAD
STAND_H, CHEST_H = 6.6, 13.2
box("Cab_Stand", (caw, CAD, 1.6), (cax, hy - CAD / 2, STAND_H - 0.8), M_OAKH, bevel=0.08)
for sx in (-1, 1):
    for sy in (0, 1):
        lathe(f"Cab_Leg{sx}{sy}", [(0.35, 0.0), (0.5, 0.4), (0.3, 1.2), (0.6, 2.8), (0.3, 4.2), (0.4, 5.0), (0.4, STAND_H - 1.6)],
              (cax + sx * (caw / 2 - 0.7), CY_FRONT + 0.7 + sy * (CAD - 1.4), 0), M_OAK, steps=12)
box("Cab_Stretcher", (caw - 1.4, CAD - 1.4, 0.4), (cax, hy - CAD / 2, 0.8), M_OAKH)
box("Cab_Chest", (caw - 0.4, CAD - 0.3, CHEST_H), (cax, hy - (CAD - 0.3) / 2, STAND_H + CHEST_H / 2), M_OAKH, bevel=0.06)
box("Cab_Cornice", (caw + 0.6, CAD + 0.3, 1.0), (cax, hy - CAD / 2 - 0.1, STAND_H + CHEST_H + 0.5), M_OAKH, bevel=0.15)
yf = CY_FRONT + 0.3 - 0.12
# top row: three small drawers (each the size of the one on the table); the middle one is missing
sw = (caw - 0.4 - 4 * 0.5) / 3
for i in range(3):
    x = CAX0 + 0.2 + 0.5 + sw / 2 + i * (sw + 0.5)
    zc = STAND_H + CHEST_H - 0.6 - 1.5
    if i == 1:
        box("Cab_EmptySlot", (DW, 0.2, DH + 0.6), (x, yf + 0.18, zc), M_VOID)
        continue
    box(f"Cab_SmallDrawer{i}", (sw, 0.24, 2.6), (x, yf, zc), M_OAKH, bevel=0.06)
    lathe(f"Cab_SmallKnob{i}", [(0.09, 0), (0.07, 0.08), (0.12, 0.16), (0.10, 0.22), (0.0, 0.24)], (x, yf - 0.12, zc), M_BRASS, steps=10, rot=(math.radians(90), 0, 0))
for r in range(3):
    zc = STAND_H + 0.6 + 1.6 + r * 3.4
    box(f"Cab_LongDrawer{r}", (caw - 1.4, 0.24, 3.0), (cax, yf, zc), M_OAKH, bevel=0.06)
    for s in (-1, 1):
        box(f"Cab_Plate{r}{s}", (0.9, 0.06, 0.7), (cax + s * caw / 4, yf - 0.15, zc), M_BRASS)
        torus(f"Cab_Bail{r}{s}", 0.35, 0.05, (cax + s * caw / 4, yf - 0.2, zc - 0.3), M_BRASS, seg=12, rot=(math.radians(90), 0, 0))
# on the cabinet: a pewter candlestick-free top, just her workbasket lid and a folded cloth
box("Cab_TopCloth", (5.0, 3.5, 0.15), (cax - 2.0, hy - 3.0, STAND_H + CHEST_H + 1.08), M_PILLOW, bevel=0.07, seg=2)
# the sampler above it
box("Sampler_Frame", (6.6, 0.4, 8.0), (cax, hy - 0.2, 24.6), M_TIMBER, bevel=0.1)
box("Sampler", (5.6, 0.1, 7.0), (cax, hy - 0.45, 24.6), M_SAMPLER)

# ----------------------------------------------------------------------------- ladder-back chair pulled up to the table's west side, and the low stool
def chair(cx, cy, yaw):
    """Rush-seated ladder-back chair; local front towards +x."""
    parts = []
    SH, SW_, SD = 5.4, 5.4, 4.8
    c, s = math.cos(yaw), math.sin(yaw)
    def P(x, y, z): return (cx + x * c - y * s, cy + x * s + y * c, z)
    for sy in (-1, 1):
        lathe(f"Chair_FrontLeg{sy}", [(0.33, 0.0), (0.3, SH - 0.4), (0.38, SH + 0.1), (0.2, SH + 0.5), (0.0, SH + 0.65)], P(SD / 2 - 0.35, sy * (SW_ / 2 - 0.35), 0), M_OAK, steps=10)
        lathe(f"Chair_BackPost{sy}", [(0.35, 0.0), (0.32, SH), (0.3, 11.4), (0.38, 11.9), (0.25, 12.4), (0.0, 12.6)], P(-SD / 2 + 0.35, sy * (SW_ / 2 - 0.35), 0), M_OAK, steps=10)
        for zz in (1.4, 3.0):
            box(f"Chair_SideStr{sy}{zz}", (SD - 0.7, 0.2, 0.2), P(0, sy * (SW_ / 2 - 0.35), zz), M_OAKH, rot=(0, 0, yaw))
    for zz in (1.4, 3.0):
        box(f"Chair_FrontStr{zz}", (0.2, SW_ - 0.7, 0.2), P(SD / 2 - 0.35, 0, zz), M_OAKH, rot=(0, 0, yaw))
    for i, zz in enumerate((7.0, 8.8, 10.6)):
        box(f"Chair_Slat{i}", (0.18, SW_ - 0.7, 1.0 - i * 0.1), P(-SD / 2 + 0.35, 0, zz), M_OAKH, bevel=0.06, rot=(0, 0, yaw))
    seat = box("Chair_Seat", (SD - 0.3, SW_ - 0.3, 0.45), P(0, 0, SH - 0.1), M_RUSH, bevel=0.15, seg=2, rot=(0, 0, yaw))
chair(3.0, -2.6, 0.0)
# the low stool she stood on, close to the table's east side
STX, STY = 17.2, -11.4
box("Stool_Top", (5.4, 3.6, 0.5), (STX, STY, 5.75), M_OAKH, bevel=0.1)
box("Stool_Apron", (4.6, 2.8, 0.9), (STX, STY, 5.05), M_OAKH)
for sx in (-1, 1):
    for sy in (-1, 1):
        lathe(f"Stool_Leg{sx}{sy}", [(0.32, 0.0), (0.28, 1.2), (0.36, 1.6), (0.24, 2.6), (0.36, 3.6), (0.3, 4.6)], (STX + sx * 2.1, STY + sy * 1.2, 0), M_OAK, steps=10)
    box(f"Stool_Str{sx}", (0.25, 2.4, 0.3), (STX + sx * 2.1, STY, 0.8), M_OAKH)
box("Stool_StrMid", (4.2, 0.25, 0.3), (STX, STY, 0.8), M_OAKH)

# ----------------------------------------------------------------------------- lights (names starting "Lamp" are baked in Unity)
def point(name, loc, watts, color=(1.0, 0.70, 0.40), radius=0.1):
    ld = bpy.data.lights.new(name, 'POINT'); ld.energy = watts; ld.color = color; ld.shadow_soft_size = radius
    lo = bpy.data.objects.new(name, ld); lo.location = loc; link(lo); return lo
def spot(name, loc, aim, watts, angle=60, color=(1.0, 0.92, 0.80), blend=0.6, radius=0.5):
    ld = bpy.data.lights.new(name, 'SPOT'); ld.energy = watts; ld.color = color; ld.spot_size = math.radians(angle); ld.spot_blend = blend; ld.shadow_soft_size = radius
    lo = bpy.data.objects.new(name, ld); lo.location = loc; link(lo)
    lo.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return lo
L_CANDLE = point("Lamp0_Light", (KX, KY, FLAME_Z), 900)
WIN_LIGHT_POS = (hx + 0.3, WY, 22.0)
L_WINDOW = spot("Lamp1_Window", WIN_LIGHT_POS, (TX - 1.0, TY - 1.0, Z), 30000, angle=70, blend=0.9, radius=4.0)
L_FILL = spot("Lamp2_WindowFill", (hx + 0.5, WY, WZ), (-hx, WY + 6, 6.0), 60000, angle=150, color=(0.80, 0.88, 1.0), blend=1.0, radius=6.0)

world = bpy.data.worlds.new("Room"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.02, 0.02, 0.025, 1); bg.inputs["Strength"].default_value = 1.0

# ----------------------------------------------------------------------------- anchors
RX, RY = READER
anchor("reader.entrance", (RX, RY, Z))
look_dir = Vector((dcx - RX, dcy - RY, 0)).normalized()
anchor("reader.look", (RX + look_dir.x * 2.0, RY + look_dir.y * 2.0, Z + 1.5))
anchor("scene.centre", (TX, TY, Z))

# ----------------------------------------------------------------------------- cameras (reader eye 1.6 m above the table top)
def camera(name, loc, look_at, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 400
    co = bpy.data.objects.new(name, cd); co.location = loc; link(co)
    co.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return co
EYE = Z + 1.6
cams = [
    camera("Cam_Reader", (RX, RY, EYE), (RX + 1.2, RY + 10.0, EYE - 0.9), lens=16),
    camera("Cam_Cradle", (RX + 0.6, RY + 3.0, EYE - 0.1), (dcx + 0.3, dcy + 0.2, Z + 0.5), lens=26),
    camera("Cam_Sewing", (RX - 0.3, RY - 0.4, EYE - 0.2), (8.4, -8.6, Z - 0.3), lens=18),
    camera("Cam_Edge", (TX0 + 0.7, -12.6, EYE), (-2.0, -9.0, 0.0), lens=16),
    camera("Cam_Room", (-17.0, -27.0, 17.0), (6.0, -2.0, 9.0), lens=16),
]
if args.cams:
    want = set(args.cams.split(","))
    cams_r = [c for c in cams if c.name in want or c.name[4:].lower() in want]
else:
    cams_r = cams

def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "glumdalclitchs_room_source.blend"))

# pre-export budget (also printed in quick runs)
_dg = bpy.context.evaluated_depsgraph_get(); _cat = {}
for _o in [o for o in COLL.objects if o.type == 'MESH']:
    _e = _o.evaluated_get(_dg); _me = _e.to_mesh(); _t = sum(len(p.vertices) - 2 for p in _me.polygons); _e.to_mesh_clear()
    _k = _o.data.materials[0].name if _o.data.materials else "?"; _cat[_k] = _cat.get(_k, 0) + _t
print(f"PRE-MERGE materials={len(_cat)} tris={sum(_cat.values())}")
for _k, _v in sorted(_cat.items(), key=lambda kv: -kv[1]): print(f"  BUDGET {_k:24s} {_v}")

if args.render:
    scene.render.resolution_x = args.res; scene.render.resolution_y = int(args.res * 9 / 16)
    scene.render.image_settings.file_format = 'PNG'
    for c in cams_r:
        scene.camera = c
        scene.render.filepath = os.path.join(OUT, f"render_{c.name[4:].lower()}.png")
        try:
            bpy.ops.render.render(write_still=True)
        except RuntimeError as e:                  # the GPU is shared with other renders: fall back to the CPU
            print("GPU render failed, retrying on CPU:", e)
            scene.cycles.device = 'CPU'
            bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)

# ----------------------------------------------------------------------------- bake + merge + export for Unity
def bake_and_export():
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target='MESH')                       # apply modifiers everywhere
    bpy.ops.object.select_all(action='DESELECT')
    meshes = [o for o in COLL.objects if o.type == 'MESH']
    for o in meshes:                                            # every mesh is static: unparent, keep world transform
        if o.parent is not None:
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    groups = {}
    for o in meshes:
        if not o.data.materials: continue
        groups.setdefault(o.data.materials[0].name, []).append(o)
    merged = []
    for mname, objs in groups.items():
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active; o.name = "MESH_" + mname[2:]
        merged.append(o); bpy.ops.object.select_all(action='DESELECT')
    scene.cycles.samples = 1
    scene.render.bake.margin = 6
    scene.render.bake.use_selected_to_active = False
    T = args.tex
    size_for = {"M_TableTop": min(4096, T * 2), "M_Floor": T, "M_TableFrame": T, "M_Linen": T, "M_Limewash": T, "M_Oak": T, "M_BedHangings": T,
                "M_Coverlet": T, "M_CradlePaint": T // 2, "M_Pine": T // 2, "M_Timber": T // 2, "M_CradleQuilt": T // 2, "M_BedLinen": T // 2,
                "M_Ceiling": T // 2, "M_Brass": T // 2, "M_RagRug": T // 2, "M_Pincushion": T // 4, "M_Thimble": T // 4, "M_Steel": T // 4,
                "M_Sampler": T // 2, "M_Rush": T // 4, "M_WindowGlass": T // 2}
    tiny = {"M_Flame", "M_Shadow", "M_Cordial"}
    tex_dir = os.path.join(OUT, "bake_png")                     # lossless bake masters; the export writes JPEGs to textures/
    os.makedirs(tex_dir, exist_ok=True)
    for o in merged:
        m = o.data.materials[0]; nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        size = 64 if m.name in tiny else size_for.get(m.name, T // 4)
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
        # a fresh UV map for the bake; RestUV (cloth thread coordinates) stays readable by the material during the bake
        uvb = o.data.uv_layers.new(name="BakeUV")
        o.data.uv_layers.active = uvb; uvb.active_render = True
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
        bpy.ops.object.mode_set(mode='OBJECT')
        baked = {}
        for pass_name, btype, extra, noncolor in [("BaseColor", 'DIFFUSE', {"pass_filter": {'COLOR'}}, False), ("Roughness", 'ROUGHNESS', {}, True), ("Normal", 'NORMAL', {}, True)]:
            if m.name in tiny and pass_name != "BaseColor": continue
            img = bpy.data.images.new(f"T_{m.name[2:]}_{pass_name}", size, size, alpha=False)
            if noncolor: img.colorspace_settings.name = 'Non-Color'
            tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
            for n in nt.nodes: n.select = False
            tex.select = True; nt.nodes.active = tex
            bpy.ops.object.bake(type=btype, margin=6, use_clear=True, **extra)
            img.filepath_raw = os.path.join(tex_dir, img.name + ".png")
            img.file_format = 'PNG'; img.save(); img.pack()
            baked[pass_name] = tex
            print("baked", img.name, size)
        metallic = bsdf.inputs["Metallic"].default_value
        emis = bsdf.inputs["Emission Strength"].default_value; ecol = tuple(bsdf.inputs["Emission Color"].default_value)
        elinked = bsdf.inputs["Emission Color"].is_linked
        rough_c = bsdf.inputs["Roughness"].default_value
        for n in list(nt.nodes):
            if n not in baked.values(): nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial"); nb = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(nb.outputs["BSDF"], out.inputs["Surface"])
        nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Base Color"])
        if "Roughness" in baked:
            nt.links.new(baked["Roughness"].outputs["Color"], nb.inputs["Roughness"])
            nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(baked["Normal"].outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], nb.inputs["Normal"])
        else:
            nb.inputs["Roughness"].default_value = rough_c
        nb.inputs["Metallic"].default_value = metallic
        if emis > 0:
            nb.inputs["Emission Strength"].default_value = min(emis, 8.0)
            if elinked: nt.links.new(baked["BaseColor"].outputs["Color"], nb.inputs["Emission Color"])
            else: nb.inputs["Emission Color"].default_value = ecol
        # keep only the bake UV
        for uvl in [l for l in o.data.uv_layers if l.name != "BakeUV"]: o.data.uv_layers.remove(uvl)
    for c in cams: bpy.data.objects.remove(c)
    gl = os.path.join(OUT, "glumdalclitchs_room.gltf")   # .gltf + textures/: Unity imports the images as compressed (ASTC) textures
    bpy.ops.export_scene.gltf(filepath=gl, export_format='GLTF_SEPARATE', export_texture_dir='textures', export_apply=True, export_yup=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90, export_lights=True, export_cameras=False)
    tris = sum(tri_count(o) for o in merged)
    verts = sum(len(o.data.vertices) for o in merged)
    print(f"EXPORT {gl} meshes={len(merged)} verts={verts} tris={tris}")
    with open(os.path.join(OUT, "export_stats.txt"), "w") as f:
        f.write(f"meshes={len(merged)}\nverts={verts}\ntris={tris}\n")
        for o in sorted(merged, key=lambda o: -tri_count(o)):
            img = next((n.image for n in o.data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE'), None)
            f.write(f"{o.name} verts={len(o.data.vertices)} tris={tri_count(o)} tex={img.size[0] if img else 0}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "glumdalclitchs_room_baked.blend"))

if args.bake or args.export:
    bake_and_export()
print("DONE")
