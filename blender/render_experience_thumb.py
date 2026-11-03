"""
Fable: the Blender stage of chapter-experience preparation. Renders the thumbnail of an adapted environment from
where the reader stands, so the experience tile shows the place as it will be (its mood and haze), not a stock image.

  blender -b -P blender/render_experience_thumb.py -- <environment.gltf> <out.png> [--mood as-built|dawn|day|dusk|night|storm]
          [--fog 0..1] [--eye anchor.reader.entrance] [--look anchor.reader.look] [--height 1.55] [--size 640x400]

The environment is the same glTF the Unity build uses (unity/Fable/Assets/Fable/Models/<Room>/<room>.gltf), with
its own lights. The mood scales those lights and tints the world the way Unity's ChapterExperience.ApplyMood does,
so the thumbnail and the headset agree. EEVEE, a few seconds. Prints one JSON line: {"ok", "seconds", "meanLuma"}.
"""
import json, math, sys, time

import bpy
from mathutils import Vector

t0 = time.time()
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) < 2:
    sys.exit("usage: -- <environment.gltf> <out.png> [--mood m] [--fog f] [--eye anchor] [--look anchor]")
import os
src, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
opts = {"--mood": "as-built", "--fog": "0", "--eye": "anchor.reader.entrance", "--look": "anchor.reader.look", "--height": "1.55", "--size": "640x400"}
for i in range(2, len(argv) - 1, 2):
    opts[argv[i]] = argv[i + 1]

# the same table as Unity's ChapterExperience.Moods: light scale, world colour (linear), world strength
MOODS = {
    "as-built": (1.00, (0.20, 0.18, 0.16), 0.6),
    "dawn":     (0.70, (0.55, 0.42, 0.40), 0.7),
    "day":      (1.25, (0.55, 0.62, 0.72), 1.0),
    "dusk":     (0.65, (0.45, 0.28, 0.22), 0.5),
    "night":    (0.40, (0.04, 0.05, 0.10), 0.25),
    "storm":    (0.55, (0.25, 0.28, 0.30), 0.45),
}
mood = MOODS.get(opts["--mood"], MOODS["as-built"])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
scene = bpy.context.scene

def find(name):
    for o in bpy.data.objects:
        if o.name == name or o.name.split(".")[0:3] == name.split(".")[0:3] and o.name.startswith(name):
            return o
    return None

eye = find(opts["--eye"]) or find("anchor.reader.entrance") or next((o for o in bpy.data.objects if o.name.startswith("anchor.reader.")), None)
look = find(opts["--look"]) or find("anchor.scene.centre") or find("anchor.hall.centre") or find("anchor.lobby.shelf")
if eye is None:
    sys.exit("no reader anchor in " + src)
p = eye.matrix_world.translation.copy()
p.z += float(opts["--height"])
target = look.matrix_world.translation.copy() if look else p + Vector((0, 1, 0))
target.z = max(target.z, p.z - 0.4) if look is None or (target - p).length > 3 else target.z
cam_data = bpy.data.cameras.new("thumb"); cam_data.lens = 18; cam_data.clip_end = 400
cam = bpy.data.objects.new("thumb", cam_data); scene.collection.objects.link(cam); scene.camera = cam
cam.location = p
d = target - p
cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
# a reader looks a little down into a room, not along the floor
cam.rotation_euler.x = max(cam.rotation_euler.x, math.radians(80))

scale, world_col, world_strength = mood
for o in bpy.data.objects:
    if o.type == "LIGHT":
        # glTF light units arrive tiny (lux / 683): bring suns to daylight and lamps to a room lamp, then apply the mood
        if o.data.type == "SUN": o.data.energy = max(o.data.energy, 4.0)
        else: o.data.energy = max(o.data.energy, 120.0 * max(1.0, o.matrix_world.translation.length / 6.0))
        o.data.energy *= scale
        if opts["--mood"] in ("dusk", "dawn"):
            o.data.color = (1.0, 0.78, 0.6)
        elif opts["--mood"] in ("night", "storm"):
            o.data.color = (0.75, 0.82, 1.0)
world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (*world_col, 1); bg.inputs[1].default_value = world_strength
fog = float(opts["--fog"])
if fog > 0.01:
    vol = world.node_tree.nodes.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.004 + 0.04 * fog
    world.node_tree.links.new(vol.outputs[0], world.node_tree.nodes["World Output"].inputs["Volume"])

w, h = (int(x) for x in opts["--size"].split("x"))
if os.environ.get("FABLE_THUMB_ENGINE", "").upper() == "CYCLES":
    # a server with no GPU has no OpenGL for EEVEE: Cycles on the CPU, few samples, denoised (docs/BACKEND.md)
    scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = 24; scene.cycles.use_denoising = True
else:
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = w, h, 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX" if "AgX" in [v.identifier for v in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
scene.render.filepath = out

def render_luma():
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(out, check_existing=False); px = img.pixels[:]
    n = len(px) // 4; step = max(1, n // 4000); idx = range(0, n, step)
    l = sum(0.2126 * px[i * 4] + 0.7152 * px[i * 4 + 1] + 0.0722 * px[i * 4 + 2] for i in idx) / len(idx)
    bpy.data.images.remove(img)
    return l

# auto-exposure: rooms are lit for Unity's baker, and their glTF lights come in weak or strong in Blender's units.
# Re-render (at most twice) aiming at a mid-grey mean, keeping the mood's relative darkness (night stays darker).
aim = {"night": 0.10, "storm": 0.14, "dusk": 0.16}.get(opts["--mood"], 0.20)
luma = render_luma(); passes = 1
while passes < 3 and (luma < aim * 0.6 or luma > aim * 1.8):
    scene.view_settings.exposure += max(-4.0, min(6.0, math.log2(aim / max(luma, 1e-4)) * 0.8))
    luma = render_luma(); passes += 1
print("FABLE_THUMB " + json.dumps({"ok": True, "seconds": round(time.time() - t0, 2), "meanLuma": round(luma, 4), "exposure": round(scene.view_settings.exposure, 2), "passes": passes, "eye": eye.name, "look": look.name if look else None}))
