import bpy, os
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:/Users/cipka/projekt4/tools/src/bmw_m4_f82_razor.glb")
for m in bpy.data.materials:
    if not m.node_tree: continue
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            img = n.image
            fn = os.path.join(r"C:/Users/cipka/AppData/Local/Temp/claude/6cc8f2f0f834b907/9d0466c3-f3f9-4f03-9fbf-49c9e04e986e/scratchpad/tex", (m.name + "__" + img.name).replace(" ", "_") + ".png")
            img.filepath_raw = fn; img.file_format = "PNG"
            try: img.save()
            except Exception as e: print("ERR", e)
            users = [o.name for o in bpy.data.objects if o.type=="MESH" and any(s.material==m for s in o.material_slots)]
            print("T", m.name, img.name, img.size[:], users[:6])
