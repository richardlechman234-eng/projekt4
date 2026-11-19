# Úvodný obrázok (poster) – rovnaký záber ako 3D scéna pri p = 0; zobrazí sa hneď, kým sa načíta 3D.
import bpy, math, os
from mathutils import Vector as V
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "tools", "garage.blend"))
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 48; sc.cycles.device = "CPU"; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.045, 0.055, 0.07)
sc.view_settings.view_transform = "Standard"
for x, y in ((-1.6, 1.3), (1.6, 1.3), (-1.6, -1.3), (1.6, -1.3)):
    bpy.ops.object.light_add(type="AREA", location=(x, y, 3.1)); bpy.context.object.data.energy = 160; bpy.context.object.data.size = 2
bpy.ops.object.light_add(type="SPOT", location=(0, -13.5, 7.0)); L = bpy.context.object
L.data.energy = 2600; L.data.spot_size = 1.9; L.data.spot_blend = 0.75
L.rotation_euler = (V((0, -4.2, 2.4)) - V(L.location)).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.light_add(type="SUN", location=(0, 0, 10)); S = bpy.context.object; S.data.energy = 0.35
S.rotation_euler = (V((0, 0, 0)) - V((-5, -14, 7))).to_track_quat("-Z", "Y").to_euler()
loc, tgt = (0, -14.0, 1.15), (0, -4.2, 2.75)
bpy.ops.object.camera_add(location=loc); cam = bpy.context.object
cam.rotation_euler = (V(tgt) - V(loc)).to_track_quat("-Z", "Y").to_euler()
cam.data.sensor_fit = "VERTICAL"; cam.data.angle = math.radians(46)
sc.camera = cam
sc.render.image_settings.file_format = "WEBP"; sc.render.image_settings.quality = 78
sc.render.filepath = os.path.join(ROOT, "assets", "poster.webp")
bpy.ops.render.render(write_still=True)
