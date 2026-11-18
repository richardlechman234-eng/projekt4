import bpy, math
from mathutils import Vector as V
bpy.ops.wm.open_mainfile(filepath="tools/garage.blend")
car = bpy.data.objects["Car"]; car.rotation_euler = (0, 0, -1.31)
loc = V((-2.15, -2.95, 1.45)); tgt = V((0.35, 0.3, 0.6))
bpy.ops.object.camera_add(location=loc)
cam = bpy.context.object; cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
cam.data.sensor_fit = "VERTICAL"; cam.data.angle = math.radians(62)
sc = bpy.context.scene; sc.camera = cam
sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.device = "CPU"
sc.render.resolution_x, sc.render.resolution_y = 960, 450
sc.render.filepath = "tools/prev_final.png"
sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.3, 0.3, 0.35)
bpy.ops.object.light_add(type="AREA", location=(0, 0, 2.6)); bpy.context.object.data.energy = 500; bpy.context.object.data.size = 3
bpy.ops.render.render(write_still=True)
