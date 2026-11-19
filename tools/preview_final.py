import bpy, math
from mathutils import Vector as V
bpy.ops.wm.open_mainfile(filepath=r"C:/Users/cipka/projekt4/tools/garage.blend")
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 20; sc.cycles.device = "CPU"
sc.render.resolution_x, sc.render.resolution_y = 960, 450
sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.06, 0.07, 0.09)
for x, y in ((-1.6, 1.3), (1.6, 1.3), (-1.6, -1.3), (1.6, -1.3)):
    bpy.ops.object.light_add(type="AREA", location=(x, y, 3.1)); bpy.context.object.data.energy = 160; bpy.context.object.data.size = 2
bpy.ops.object.light_add(type="SPOT", location=(2.5, -11, 5)); L = bpy.context.object; L.data.energy = 6000; L.data.spot_size = 1.6
L.rotation_euler = (V((0, -4.2, 1.6)) - V((2.5, -11, 5))).to_track_quat("-Z", "Y").to_euler()
car = bpy.data.objects["Car"]
for name, yaw, loc, tgt, fov in (("start", 0, (0, -14.0, 1.15), (0, -4.2, 2.75), 46), ("front", 0, (0, -6.6, 1.4), (0, -1.0, 0.75), 42), ("tyres", 0, (-2.2, -0.2, 1.0), (-3.4, -1.2, 0.75), 50), ("stack", 0, (1.6, 0.6, 1.0), (3.15, 2.25, 0.7), 45)):
    car.rotation_euler = (0, 0, yaw)
    for o in bpy.data.objects:
        if o.name.startswith(("DoorPanel", "DoorRib", "DoorStripe", "DoorBacking")): o.hide_render = (name != "start")
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object; cam.rotation_euler = (V(tgt) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "VERTICAL"; cam.data.angle = math.radians(fov)
    sc.camera = cam
    sc.render.filepath = r"C:/Users/cipka/AppData/Local/Temp/claude/6cc8f2f0f834b907/9d0466c3-f3f9-4f03-9fbf-49c9e04e986e/scratchpad/g2_" + name + ".png"
    bpy.ops.render.render(write_still=True)
