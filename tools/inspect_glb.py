import bpy, sys
from mathutils import Vector
path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3); tris = 0
for o in bpy.data.objects:
    if o.type == "MESH":
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v); mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
        tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
print("OBJS", len([o for o in bpy.data.objects if o.type == "MESH"]), "TRIS", tris)
print("BBOX", tuple(round(x, 3) for x in mn), tuple(round(x, 3) for x in mx))
for m in bpy.data.materials:
    users = [o.name for o in bpy.data.objects if o.type == "MESH" and m.name in [s.material.name for s in o.material_slots if s.material]]
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.node_tree else None
    col = tuple(round(c, 2) for c in b.inputs["Base Color"].default_value[:3]) if b else None
    tex = b and b.inputs["Base Color"].is_linked
    print("MAT", m.name, "| col", col, "| tex", tex, "| n", len(users), users[:3])
