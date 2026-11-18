import bpy, sys, os
path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
for m in bpy.data.materials:
    if not m.node_tree: continue
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b and b.inputs["Base Color"].is_linked:
        n = b.inputs["Base Color"].links[0].from_node
        while n.type != "TEX_IMAGE" and n.inputs and any(i.is_linked for i in n.inputs):
            n = next(i for i in n.inputs if i.is_linked).links[0].from_node
        img = getattr(n, "image", None)
        print("TEX", m.name, img.name if img else None, img.size[:] if img else None)
for o in bpy.data.objects:
    if o.type=="MESH" and ("dff" in o.name):
        print("JUNK", o.name, tuple(round(d,2) for d in o.dimensions))
