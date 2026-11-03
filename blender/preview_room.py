"""
Render an exported generated room (room.gltf from roomgen.py) the way the headset shows it: unlit, baked textures
only, no lights, Standard view transform, from the reader's eyes (anchor.reader.entrance + 1.55 m, toward
anchor.reader.look). These images are Blender renders of the export, labelled as such.

  blender -b --factory-startup -P blender/preview_room.py -- room.gltf out_prefix [--res 1200]
"""
import bpy, sys, math, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
gl, prefix = argv[0], argv[1]
res = int(argv[argv.index("--res") + 1]) if "--res" in argv else 1200
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=gl)
sc = bpy.context.scene
ent = bpy.data.objects.get("anchor.reader.entrance"); look = bpy.data.objects.get("anchor.reader.look")
eye = ent.matrix_world.translation + Vector((0, 0, 1.55)); tgt = look.matrix_world.translation
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
# Workbench, flat light, texture colour: exactly an unlit textured render, as glTFast's unlit shader draws it
sc.render.engine = 'BLENDER_WORKBENCH'; sh = sc.display.shading
sh.light = 'FLAT'; sh.color_type = 'TEXTURE'; sh.background_type = 'VIEWPORT'; sh.background_color = (0, 0, 0)
sc.display.render_aa = '8'
sc.view_settings.view_transform = 'Standard'
cd = bpy.data.cameras.new("c"); cd.angle = math.radians(90); cd.clip_end = 500
cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = res, int(res * 0.6)
fwd = tgt - eye; yaw = math.atan2(fwd.y, fwd.x)
for name, dyaw, pitch in (("reading", 0, -0.05), ("left", 90, -0.05), ("right", -90, -0.05), ("behind", 180, -0.05), ("down", 20, -0.8)):
    y = yaw + math.radians(dyaw)
    d = Vector((math.cos(y) * math.cos(pitch), math.sin(y) * math.cos(pitch), math.sin(pitch)))
    cam.location = eye; cam.rotation_mode = 'QUATERNION'; cam.rotation_quaternion = d.to_track_quat('-Z', 'Y')
    sc.render.filepath = f"{prefix}{name}.png"; bpy.ops.render.render(write_still=True)
print("PREVIEW done", prefix)
