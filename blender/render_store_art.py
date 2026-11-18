"""
Fable: store art (the Meta dashboard's cover images) rendered from the real lobby: the shelf of ten classics, lamp-lit,
with the title set in EB Garamond. Not part of the APK; the APK's icon is made from the square cover.

  blender -b -P blender/render_store_art.py -- <out.png> <width>x<height> [--lens 20] [--samples 64] [--title-scale 1]

Cycles on the CPU (denoised). The lobby glTF is the one the Unity build uses.
"""
import math, os, sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(argv[0]); w, h = (int(x) for x in argv[1].split("x"))
opts = {"--lens": "20", "--samples": "64", "--title-scale": "1", "--exposure": "-1.6"}
for i in range(2, len(argv) - 1, 2): opts[argv[i]] = argv[i + 1]
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(root, "unity/Fable/Assets/Fable/Models/Lobby/lobby.gltf"))
scene = bpy.context.scene

# lamps: glTF light units arrive tiny in Blender; bring them to a warm room's level
for o in bpy.data.objects:
    if o.type == "LIGHT":
        o.data.energy = 1.0 if o.data.type == "SUN" else max(o.data.energy, 25.0)
# a soft warm fill from behind the camera so the covers read
fill = bpy.data.lights.new("fill", "AREA"); fill.energy = 40; fill.size = 2.5; fill.color = (1.0, 0.82, 0.62)
fo = bpy.data.objects.new("fill", fill); scene.collection.objects.link(fo); fo.location = (0, -0.4, 2.3)
fo.rotation_euler = (Vector((0, 2.1, 1.2)) - fo.location).to_track_quat("-Z", "Y").to_euler()

world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.035, 0.025, 1); world.node_tree.nodes["Background"].inputs[1].default_value = 0.08

# camera in front of the shelf (glTF z -2.1 is Blender y 2.1), eye a little above the book line
cam_data = bpy.data.cameras.new("cover"); cam_data.lens = float(opts["--lens"]); cam_data.clip_end = 100
cam = bpy.data.objects.new("cover", cam_data); scene.collection.objects.link(cam); scene.camera = cam
cam.location = (0, -0.35, 1.30)
target = Vector((0, 2.0, 1.22))
cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()

# the title, floating between the camera and the shelf in the upper part of the frame
font = bpy.data.fonts.load(os.path.join(root, "unity/Fable/Assets/Fable/Fonts/EBGaramond-Regular.ttf"))
ink = bpy.data.materials.new("title"); ink.use_nodes = True; nt = ink.node_tree
for n in list(nt.nodes):
    if n.type != "OUTPUT_MATERIAL": nt.nodes.remove(n)
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (1.0, 0.86, 0.62, 1); em.inputs["Strength"].default_value = 14.0
nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])

def text(body, size, up):
    td = bpy.data.curves.new(body, "FONT"); td.body = body; td.font = font; td.size = size * float(opts["--title-scale"])
    td.align_x = "CENTER"; td.align_y = "CENTER"
    o = bpy.data.objects.new(body, td); scene.collection.objects.link(o); o.data.materials.append(ink)
    o.visible_shadow = False
    o.parent = cam; o.location = (0, up, -1.0); o.rotation_euler = (0, 0, 0)
    return o

aspect = h / w
top = 0.62 * min(1.0, aspect) if aspect <= 1 else 0.62 + 0.25 * (aspect - 1)
text("Fable", 0.34, top)
text("stand inside the classics", 0.075, top - 0.23)

scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = int(opts["--samples"]); scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = w, h, 100
scene.view_settings.view_transform = "AgX" if "AgX" in [v.identifier for v in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
scene.view_settings.exposure = float(opts["--exposure"])
scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_mode = "RGB"
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("FABLE_STORE_ART", out, w, h)
