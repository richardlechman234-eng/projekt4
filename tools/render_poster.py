# Statické obrázky scény (rovnaký záber ako 3D) + pozície bublín → assets/poster.webp, assets/poster-m.webp, js/poster-data.js
# Spustenie: blender -b --factory-startup --python tools/render_poster.py [-- --pts-only]   (--pts-only = len pozície bublín, bez renderu)
import bpy, math, os, re, json, sys
from mathutils import Vector as V
from bpy_extras.object_utils import world_to_camera_view

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
views_src = open(os.path.join(ROOT, "js", "views.js"), encoding="utf-8").read()
VIEWS = json.loads(re.search(r"= /\*JSON\*/(.*?)/\*END\*/", views_src, re.S).group(1))

bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "tools", "garage.blend"))
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 64; sc.cycles.device = "CPU"; sc.cycles.use_denoising = True
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = False; sc.world.color = (0.045, 0.05, 0.06)
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
for o in bpy.data.objects:                                   # vráta sú v 3D skryté
    if o.name.startswith(("DoorPanel", "DoorRib", "DoorStripe", "DoorBacking")): o.hide_render = True
for x, y in ((-1.6, 1.3), (1.6, 1.3), (-1.6, -1.3), (1.6, -1.3)):
    bpy.ops.object.light_add(type="AREA", location=(x, y, 3.1)); bpy.context.object.data.energy = 220; bpy.context.object.data.size = 2.4
bpy.ops.object.light_add(type="SPOT", location=(0.4, -0.6, 3.1)); L = bpy.context.object
L.data.energy = 900; L.data.spot_size = 1.7; L.data.spot_blend = 0.6; L.rotation_euler = (0, 0, 0)

b3 = lambda p: V((p[0], -p[2], p[1]))                       # three → Blender
car = bpy.data.objects["Car"]
anchors = {o.name[3:]: o for o in bpy.data.objects if o.name.startswith("AN_")}
out = {}
for key, (w, h, fname) in {"wide": (1600, 900, "poster.webp"), "tall": (900, 1800, "poster-m.webp")}.items():
    v = VIEWS[key]
    aspect = w / h
    vfov = min(v["vmax"], math.degrees(2 * math.atan(math.tan(math.radians(v["hfov"] / 2)) / aspect)))
    car.rotation_euler = (0, 0, v["yaw"])
    bpy.context.view_layer.update()
    loc, tgt = b3(v["pos"]), b3(v["tgt"])
    bpy.ops.object.camera_add(location=loc); cam = bpy.context.object
    cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "VERTICAL"; cam.data.angle = math.radians(vfov); cam.data.clip_start = 0.15
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = w, h
    bpy.context.view_layer.update()
    pts = {}
    for name, o in anchors.items():
        co = o.matrix_world.translation
        if name == "stk":                                    # výfuk je zozadu – na obrázku bublinu dáme nad kufor
            co = car.matrix_world @ V((0.0, o.location.y - 0.35, 1.05))
        p = world_to_camera_view(sc, cam, co)
        pts[name] = [round(p.x, 4), round(1 - p.y, 4)]
    if "odtah" in VIEWS:                                     # Odťah stojí mimo auta na pevnom mieste
        p = world_to_camera_view(sc, cam, b3(VIEWS["odtah"][key]))
        pts["odtah"] = [round(p.x, 4), round(1 - p.y, 4)]
    c = world_to_camera_view(sc, cam, car.matrix_world.translation + V((0, 0, 0.6)))
    out[key] = {"w": w, "h": h, "cx": round(c.x, 4), "pts": pts}
    sc.render.image_settings.file_format = "WEBP"; sc.render.image_settings.quality = 80
    sc.render.filepath = os.path.join(ROOT, "assets", fname)
    if "--pts-only" not in sys.argv and not ("--tall-only" in sys.argv and key != "tall"):   # poster.webp (desktop) = fasáda → tools/render_facade.py
        bpy.ops.render.render(write_still=True)
    print("POSTER", key, vfov, pts)

with open(os.path.join(ROOT, "js", "poster-data.js"), "w", encoding="utf-8") as f:
    f.write("// Vygenerované: tools/render_poster.py – pozície bublín na statických obrázkoch (0–1 od ľavého horného rohu).\n")
    f.write("export const POSTER = " + json.dumps(out, ensure_ascii=False) + ";\n")
