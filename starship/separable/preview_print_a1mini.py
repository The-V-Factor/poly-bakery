"""Render the assembled and opened print model, preserving its assembly positions."""
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent / "printing" / "a1mini"
bpy.ops.wm.open_mainfile(filepath=str(OUT / "Starship_Opening_Print.blend"))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1200, 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.media_type = "IMAGE"
scene.world.color = (.15, .15, .15)
scene.view_settings.view_transform = "AgX"


def aim(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()


bpy.ops.object.camera_add(location=(.18, -.46, .245))
camera = bpy.context.object
camera.name = "Print preview camera"
camera.data.type, camera.data.ortho_scale = "ORTHO", .24
camera.data.clip_start = .001
aim(camera, (.015, 0, .101))
scene.camera = camera
for name, location, power, size in [
    ("Key", (.10, -.17, .25), 7, .18),
    ("Fill", (-.14, -.06, .16), 4, .16),
    ("Rim", (.04, .13, .22), 8, .12),
]:
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name, light.data.energy, light.data.shape, light.data.size = name, power, "DISK", size
    aim(light, (0, 0, .1))
for name in ("Fit_Pin", "Fit_Sockets"):
    bpy.data.objects[name].hide_render = True
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Starship_Opening_Print.blend"))
scene.render.filepath = str(OUT / "closed.png")
bpy.ops.render.render(write_still=True)
for name in ("Starship_Cover", "SuperHeavy_Cover"):
    bpy.data.objects[name].location = (.035, -.014, 0)
scene.render.filepath = str(OUT / "opened.png")
bpy.ops.render.render(write_still=True)
