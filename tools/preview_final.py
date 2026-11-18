import bpy, math
from mathutils import Vector as V
bpy.ops.wm.open_mainfile(filepath=r"C:/Users/cipka/projekt4/tools/garage.blend")
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 20; sc.cycles.device = "CPU"
sc.render.resolution_x, sc.render.resolution_y = 960, 450
sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.3, 0.3, 0.35)
bpy.ops.object.light_add(type="AREA", location=(0, 0, 2.6)); bpy.context.object.data.energy = 500; bpy.context.object.data.size = 3
car = bpy.data.objects["Car"]
for name, yaw, loc, tgt in (("front", 0, (0, -5.0, 1.3), (0, -1.0, 0.8)), ("final", -1.31, (-2.15, -2.95, 1.45), (0.35, 0.3, 0.6))):
    car.rotation_euler = (0, 0, yaw)
    for o in bpy.data.objects:
        if o.name.startswith(("FrontL","FrontR","FrontHeader","Frame","Door")): o.hide_render = (name == "front")
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object; cam.rotation_euler = (V(tgt) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "VERTICAL"; cam.data.angle = math.radians(62 if name == "final" else 42)
    sc.camera = cam
    sc.render.filepath = r"C:/Users/cipka/AppData/Local/Temp/claude/6cc8f2f0f834b907/9d0466c3-f3f9-4f03-9fbf-49c9e04e986e/scratchpad/m4_" + name + ".png"
    bpy.ops.render.render(write_still=True)
