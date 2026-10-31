"""
Fable: the four book covers for the lobby shelf (content/covers/<slug>.jpg, 1400x2100).

Alice, Oz and Gulliver: the Standard Ebooks cover, taken unchanged from the edition's EPUB (out/sources/<slug>.epub,
written by tools/ingest_book.py). SE releases its cover designs under CC0; the paintings are public domain.

The Odyssey (Butler's translation, Gutenberg #1727) has no SE edition, so its cover is composed here in the same
layout: a 2:3 crop of a public-domain painting with a dark title band set in League Spartan Bold (SIL OFL 1.1,
content/covers/fonts). The painting is downloaded once from Wikimedia Commons and checked against a recorded hash.

Run headless (Blender renders the composed cover so no imaging library is needed):
  blender -b -P tools/make_covers.py
Sources and licences: content/covers/SOURCE.md.
"""
import bpy, hashlib, os, sys, urllib.request, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "content", "covers")
SRC = os.path.join(ROOT, "out", "sources")
os.makedirs(OUT, exist_ok=True)

for slug in ("alice", "oz", "gulliver"):
    epub = os.path.join(SRC, slug + ".epub")
    with zipfile.ZipFile(epub) as z:
        data = z.read("epub/images/cover.jpg")
    open(os.path.join(OUT, slug + ".jpg"), "wb").write(data)
    print(f"[covers] {slug}: SE cover.jpg from {os.path.relpath(epub, ROOT)} ({len(data)} bytes)")

# ----------------------------------------------------------------------------- the Odyssey
PAINTING_URL = ("https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Arnold_B%C3%B6cklin_008.jpg/"
                "3840px-Arnold_B%C3%B6cklin_008.jpg")
PAINTING_SHA256 = "a01342ed6de42d291bff8c563feb44754f6df0cacdda5e5fd790662cc9e24e6d"
painting = os.path.join(SRC, "covers", "bocklin-ulysses-and-calypso-3840.jpg")
if not os.path.exists(painting):
    os.makedirs(os.path.dirname(painting), exist_ok=True)
    req = urllib.request.Request(PAINTING_URL, headers={"User-Agent": "FableBuild/1.0 (https://github.com/ayoyeniyi/fable)"})
    open(painting, "wb").write(urllib.request.urlopen(req).read())
got = hashlib.sha256(open(painting, "rb").read()).hexdigest()
if got != PAINTING_SHA256:
    sys.exit(f"painting hash mismatch: {got} (expected {PAINTING_SHA256}); check the source before using it")

W, H = 1400, 2100                     # SE cover size
BAND = (52, 1617, 1348, 2040)         # SE title band in pixels (left, top, right, bottom), measured on the SE covers
CROP_LEFT = 0.0                       # crop from the left edge: Odysseus on the rocks looking out to sea (Book V)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.use_denoising = False
sc.cycles.filter_width = 0.8
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 92
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0, 0, 0)

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = H / 1000          # 1 unit = 1000 px; ortho scale spans the longer side
cam.location = (W / 2000, H / 2000, 5)

def px(x, y): return (x / 1000, (H - y) / 1000)                    # pixel (top-left origin) to scene units

def emission_mat(name, color=None, image=None, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(image); tex.interpolation = "Cubic"
        nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = (*color, 1)
    if alpha < 1:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = alpha
        nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
    else:
        nt.links.new(em.outputs[0], out.inputs[0])
    return m

def quad(name, x0, y0, x1, y1, z, mat, uv=None):
    a, b = px(x0, y1), px(x1, y0)                                    # bottom-left, top-right
    me = bpy.data.meshes.new(name)
    me.from_pydata([(a[0], a[1], z), (b[0], a[1], z), (b[0], b[1], z), (a[0], b[1], z)], [], [(0, 1, 2, 3)])
    if uv:
        layer = me.uv_layers.new(); u0, v0, u1, v1 = uv
        for i, (u, v) in enumerate([(u0, v0), (u1, v0), (u1, v1), (u0, v1)]): layer.data[i].uv = (u, v)
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); ob.data.materials.append(mat)
    return ob

# the painting, cropped to 2:3 at full height
img = bpy.data.images.load(painting); pw, ph = img.size
crop_w = ph * W / H / pw                                            # crop width as a fraction of the painting's width
u0 = CROP_LEFT; u1 = u0 + crop_w
quad("painting", 0, 0, W, H, 0, emission_mat("painting", image=painting), uv=(u0, 0, u1, 1))
quad("band", *BAND, 0.01, emission_mat("band", color=(0, 0, 0), alpha=0.75))

font = bpy.data.fonts.load(os.path.join(OUT, "fonts", "LeagueSpartan-Bold.ttf"))
def text(body, size_px, centre_y_px, spacing=1.0):
    cu = bpy.data.curves.new(body, "FONT"); cu.body = body; cu.font = font
    cu.size = size_px / 1000; cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.space_character = spacing
    ob = bpy.data.objects.new(body, cu); sc.collection.objects.link(ob)
    x, y = px(W / 2, centre_y_px); ob.location = (x, y, 0.02)
    ob.data.materials.append(emission_mat("ink", color=(0.95, 0.95, 0.95)))
    return ob

band_mid = (BAND[1] + BAND[3]) / 2
text("THE ODYSSEY", 176, band_mid - 47, spacing=1.04)
text("HOMER", 80, band_mid + 92, spacing=1.10)

sc.render.filepath = os.path.join(OUT, "odyssey.jpg")
bpy.ops.render.render(write_still=True)
print(f"[covers] odyssey: composed from {os.path.relpath(painting, ROOT)} (crop u {u0:.3f}-{u1:.3f})")
