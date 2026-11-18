import bpy, sys, math
from mathutils import Vector as V
args = sys.argv[sys.argv.index("--") + 1:]
path, out = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
for o in list(bpy.data.objects):
    if o.type == "MESH" and "dff" in o.name:
        bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene
bpy.ops.object.light_add(type="SUN", rotation=(0.6, 0.2, 0.5)); bpy.context.object.data.energy = 4
sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.5, 0.5, 0.55)
sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.device = "CPU"
sc.render.resolution_x, sc.render.resolution_y = 800, 400
for name, loc in (("a", (6, 6, 2.5)), ("b", (-6, -6, 2.5))):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    cam.rotation_euler = (V((0, 0, 0)) - V(loc)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 40
    sc.camera = cam
    sc.render.filepath = out + "_" + name + ".png"
    bpy.ops.render.render(write_still=True)
