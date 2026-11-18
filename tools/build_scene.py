# Blender 5.x headless:  blender -b --factory-startup --python tools/build_scene.py
# Builds the garage + BMW M style coupe (own model, no third-party assets) and exports models/garage.glb
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "models", "garage.glb")
PREVIEW = "--preview" in sys.argv

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ------------------------------------------------------------------ helpers
def mat(name, color, metallic=0.0, rough=0.5, emit=None, emit_strength=0.0, coat=0.0, double=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if coat:
        for k in ("Coat Weight", "Clearcoat"):
            if k in b.inputs:
                b.inputs[k].default_value = coat
        for k in ("Coat Roughness", "Clearcoat Roughness"):
            if k in b.inputs:
                b.inputs[k].default_value = 0.05
    if emit:
        for k in ("Emission Color", "Emission"):
            if k in b.inputs:
                b.inputs[k].default_value = (*emit, 1)
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = emit_strength
    if double:
        m.use_backface_culling = False
    return m

M = {
    "wall": mat("Wall", (0.62, 0.63, 0.64), 0.0, 0.85),
    "wall2": mat("WallDark", (0.40, 0.41, 0.42), 0.0, 0.8),
    "floor": mat("Floor", (0.035, 0.037, 0.04), 0.1, 0.38),
    "line": mat("FloorLine", (0.9, 0.7, 0.05), 0.0, 0.6),
    "ceil": mat("Ceiling", (0.72, 0.73, 0.74), 0.0, 0.9),
    "asphalt": mat("Asphalt", (0.08, 0.08, 0.085), 0.0, 0.95),
    "concrete": mat("Concrete", (0.34, 0.34, 0.33), 0.0, 0.95),
    "door": mat("DoorPanel", (0.10, 0.105, 0.11), 0.6, 0.45),
    "doorAcc": mat("DoorAccent", (1.0, 0.35, 0.09), 0.0, 0.5),
    "red": mat("RedCabinet", (0.62, 0.03, 0.03), 0.55, 0.38, coat=0.6),
    "redDark": mat("RedDark", (0.30, 0.02, 0.02), 0.4, 0.5),
    "steel": mat("Steel", (0.62, 0.63, 0.65), 1.0, 0.3),
    "dark": mat("DarkSteel", (0.05, 0.05, 0.055), 0.6, 0.5),
    "top": mat("Worktop", (0.12, 0.12, 0.13), 0.5, 0.45),
    "tire": mat("Rubber", (0.018, 0.018, 0.02), 0.0, 0.85),
    "rim": mat("Rim", (0.42, 0.43, 0.46), 1.0, 0.28),
    "rimDark": mat("RimDark", (0.06, 0.06, 0.07), 0.9, 0.4),
    "caliper": mat("Caliper", (0.75, 0.02, 0.02), 0.3, 0.35),
    "disc": mat("Disc", (0.35, 0.35, 0.37), 1.0, 0.5),
    "body": mat("CarPaint", (0.17, 0.18, 0.20), 0.85, 0.30, coat=1.0),
    "glass": mat("Glass", (0.01, 0.015, 0.02), 0.0, 0.04),
    "black": mat("TrimBlack", (0.008, 0.008, 0.009), 0.2, 0.35),
    "chrome": mat("DarkChrome", (0.25, 0.26, 0.28), 1.0, 0.18),
    "lamp": mat("Headlamp", (1, 1, 1), 0.0, 0.1, emit=(1, 1, 1), emit_strength=3.0),
    "tail": mat("Taillamp", (0.6, 0.0, 0.0), 0.0, 0.2, emit=(1, 0.02, 0.0), emit_strength=2.5),
    "mb": mat("M_LightBlue", (0.35, 0.65, 0.95), 0.0, 0.4),
    "md": mat("M_DarkBlue", (0.08, 0.12, 0.55), 0.0, 0.4),
    "mr": mat("M_Red", (0.8, 0.05, 0.05), 0.0, 0.4),
    "plate": mat("Plate", (0.55, 0.55, 0.55), 0.0, 0.5),
    "ledpanel": mat("LedPanel", (1, 1, 0.95), 0.0, 0.3, emit=(1, 0.98, 0.92), emit_strength=4.0),
    "shelf": mat("Shelf", (0.16, 0.17, 0.19), 0.7, 0.5),
}

def link(o, parent=None, collection=None):
    if o.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(o)
    if parent is not None:
        o.parent = parent
    return o

def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    link(o, parent)
    return o

def from_bm(name, bm, material=None, parent=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    link(o, parent)
    if material is not None:
        o.data.materials.append(material)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return o

def box(name, size, loc, material, parent=None, bevel=0.0, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    o = from_bm(name, bm, material, parent, smooth=False)
    o.location = loc
    o.rotation_euler = rot
    if bevel > 0:
        m = o.modifiers.new("bv", "BEVEL")
        m.width = bevel
        m.segments = 2
        m.limit_method = "ANGLE"
    return o

def cyl(name, r, depth, loc, material, parent=None, axis="X", verts=32, caps=True, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=verts, radius1=r, radius2=(r if r2 is None else r2), depth=depth)
    # cone is along Z
    o = from_bm(name, bm, material, parent, smooth=True)
    if axis == "X":
        o.rotation_euler = (0, math.pi / 2, 0)
    elif axis == "Y":
        o.rotation_euler = (math.pi / 2, 0, 0)
    o.location = loc
    return o

def apply_modifiers(o):
    bpy.context.view_layer.objects.active = o
    for o2 in bpy.context.selected_objects:
        o2.select_set(False)
    o.select_set(True)
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)

# ------------------------------------------------------------------ GARAGE
GW, GD, GH = 6.0, 6.2, 2.8       # interior width (x), depth (y), height (z)
T = 0.25                          # wall thickness
OW, OH = 3.4, 2.3                 # door opening
FY = -GD / 2                      # front wall inner face y
G = empty("Garage")

# floor + ground
box("Floor", (GW, GD, 0.1), (0, 0, -0.05), M["floor"], G)
box("FloorLine1", (0.07, GD - 0.6, 0.004), (-1.6, 0, 0.002), M["line"], G)
box("FloorLine2", (0.07, GD - 0.6, 0.004), (1.6, 0, 0.002), M["line"], G)
box("Ground", (60, 40, 0.1), (0, -23 - GD / 2, -0.06), M["asphalt"], G)
box("Apron", (GW + 4, 6, 0.06), (0, FY - 3.0, -0.03), M["concrete"], G)
# ceiling / roof
box("Ceiling", (GW + 2 * T, GD + 2 * T, T), (0, 0, GH + T / 2), M["ceil"], G)
# walls
box("WallBack", (GW + 2 * T, T, GH + 0.3), (0, GD / 2 + T / 2, (GH + 0.3) / 2 - 0.05), M["wall"], G)
box("WallLeft", (T, GD + 2 * T, GH + 0.3), (-GW / 2 - T / 2, 0, (GH + 0.3) / 2 - 0.05), M["wall"], G)
box("WallRight", (T, GD + 2 * T, GH + 0.3), (GW / 2 + T / 2, 0, (GH + 0.3) / 2 - 0.05), M["wall"], G)
# front wall with opening
sideW = (GW + 2 * T - OW) / 2
box("FrontL", (sideW, T, GH + 0.3), (-(OW / 2 + sideW / 2), FY - T / 2, (GH + 0.3) / 2 - 0.05), M["wall"], G)
box("FrontR", (sideW, T, GH + 0.3), ((OW / 2 + sideW / 2), FY - T / 2, (GH + 0.3) / 2 - 0.05), M["wall"], G)
box("FrontHeader", (OW, T, GH + 0.3 - OH), (0, FY - T / 2, OH + (GH + 0.3 - OH) / 2 - 0.05), M["wall"], G)
# accent stripe on facade + frame around opening
box("FrameL", (0.1, 0.06, OH), (-OW / 2 - 0.05, FY - T - 0.0, OH / 2), M["doorAcc"], G)
box("FrameR", (0.1, 0.06, OH), (OW / 2 + 0.05, FY - T - 0.0, OH / 2), M["doorAcc"], G)
box("FrameT", (OW + 0.2, 0.06, 0.1), (0, FY - T - 0.0, OH + 0.05), M["doorAcc"], G)
# skirting inside
for nm, s, l in (("SkB", (GW, 0.03, 0.12), (0, GD / 2 - 0.015, 0.06)),
                 ("SkL", (0.03, GD, 0.12), (-GW / 2 + 0.015, 0, 0.06)),
                 ("SkR", (0.03, GD, 0.12), (GW / 2 - 0.015, 0, 0.06))):
    box(nm, s, l, M["wall2"], G)
# dark lower wall band (workshop look)
box("BandB", (GW, 0.02, 0.0001 + 0.9), (0, GD / 2 - 0.01, 0.57), M["wall2"], G)
# LED ceiling panels
for i, y in enumerate((-1.8, 0.0, 1.8)):
    box(f"Led{i}", (2.4, 0.22, 0.03), (0, y, GH - 0.015), M["ledpanel"], G)

# ---- door (pivot at top so JS can scale it upward = roll-up)
door = empty("Door", (0, FY - T + 0.04, OH), G)
n_pan = 6
ph = OH / n_pan
for i in range(n_pan):
    z = -(i + 0.5) * ph
    box(f"DoorPanel{i}", (OW, 0.06, ph - 0.025), (0, 0, z), M["door"], door, bevel=0.01)
    box(f"DoorRib{i}", (OW - 0.1, 0.012, 0.03), (0, -0.034, z + ph * 0.22), M["dark"], door)
box("DoorStripe", (OW, 0.064, 0.05), (0, -0.002, -OH * 0.5), M["doorAcc"], door)

# ---- red drawer cabinets (back wall)
def drawer_unit(name, x0, x1, h, n, y_back=GD / 2 - 0.02, depth=0.65, z0=0.0, top=True):
    w = x1 - x0
    cx = (x0 + x1) / 2
    cy = y_back - depth / 2
    g = empty(name, (0, 0, 0), G)
    box(name + "_carcass", (w, depth, h), (cx, cy, z0 + h / 2), M["redDark"], g, bevel=0.01)
    dh = (h - 0.1) / n
    for i in range(n):
        z = z0 + 0.06 + dh * (i + 0.5)
        box(f"{name}_d{i}", (w - 0.05, 0.04, dh - 0.018), (cx, y_back - depth - 0.015, z), M["red"], g, bevel=0.008)
        box(f"{name}_h{i}", (w * 0.55, 0.03, 0.024), (cx, y_back - depth - 0.05, z + dh * 0.22), M["steel"], g, bevel=0.006)
    if top:
        box(name + "_top", (w + 0.04, depth + 0.04, 0.05), (cx, cy, z0 + h + 0.025), M["top"], g)
    for sx in (-w / 2 + 0.07, w / 2 - 0.07):
        cyl(f"{name}_wheel", 0.045, 0.03, (cx + sx, cy, z0 + 0.0), M["dark"], g, axis="X", verts=12)
    return g

drawer_unit("CabA", -2.95, -1.85, 1.0, 5)
drawer_unit("CabB", -1.85, -0.75, 1.0, 5)
drawer_unit("CabC", -0.75, 0.35, 1.0, 5)
drawer_unit("TallD", 0.45, 1.75, 1.85, 9, top=True)
# wall panels / pegboard over worktop
box("Pegboard", (3.3, 0.03, 0.85), (-1.3, GD / 2 - 0.02, 1.62), M["wall2"], G)
for i in range(6):
    box(f"Tool{i}", (0.05, 0.02, 0.28 + 0.03 * (i % 3)), (-2.7 + i * 0.52, GD / 2 - 0.045, 1.58), M["steel"], G)
box("ShelfTop", (1.3, 0.34, 0.04), (1.1, GD / 2 - 0.2, 2.25), M["shelf"], G)

# ---- tyres
def tire(name, loc, parent, r=0.34, w=0.24, axis="Z", rim=True):
    """Realistic-ish tyre: lathe profile. axis Z => lying flat (stack)."""
    bm = bmesh.new()
    prof = [(r * 0.66, -w / 2), (r * 0.88, -w / 2), (r * 0.985, -w * 0.38), (r, -w * 0.18), (r, w * 0.18),
            (r * 0.985, w * 0.38), (r * 0.88, w / 2), (r * 0.66, w / 2), (r * 0.64, w * 0.3), (r * 0.64, -w * 0.3)]
    segs = 36
    rings = []
    for (rr, zz) in prof:
        ring = []
        for k in range(segs):
            a = 2 * math.pi * k / segs
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), zz)))
        rings.append(ring)
    for i in range(len(rings)):
        a, b = rings[i], rings[(i + 1) % len(rings)]
        for k in range(segs):
            try:
                bm.faces.new((a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k]))
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = from_bm(name, bm, M["tire"], parent, smooth=True)
    o.location = loc
    if axis == "X":
        o.rotation_euler = (0, math.pi / 2, 0)
    elif axis == "Y":
        o.rotation_euler = (math.pi / 2, 0, 0)
    if rim:
        rr = cyl(name + "_rim", r * 0.68, w * 0.7, (0, 0, 0), M["rim"], o, axis="Z", verts=24)
        rr.rotation_euler = (0, 0, 0)
    return o

def stack(name, x, y, n, r=0.34, w=0.24, z0=0.0):
    g = empty(name, (0, 0, 0), G)
    for i in range(n):
        t = tire(f"{name}_{i}", (x + 0.012 * ((i * 7) % 3 - 1), y + 0.01 * ((i * 5) % 3 - 1), z0 + w / 2 + i * w), g, r, w, "Z", rim=False)
    return g

stack("StackBL", 2.45, 2.55, 6)
stack("StackBL2", 2.45, 1.85, 4)
stack("StackFR", 2.5, -2.55, 5)
stack("StackFR2", -2.5, -2.6, 3)
# left wall tyre rack (2 levels of standing tyres)
rg = empty("TyreRack", (0, 0, 0), G)
rx = -GW / 2 + 0.26
for y in (-2.7, 2.3):
    for dx in (-0.22, 0.22):
        box("RackPost", (0.05, 0.05, 1.9), (rx + dx, y, 0.95), M["shelf"], rg)
for z in (0.05, 0.98, 1.9):
    box("RackBeamA", (0.05, 5.1, 0.05), (rx - 0.22, -0.2, z), M["shelf"], rg)
    box("RackBeamB", (0.05, 5.1, 0.05), (rx + 0.22, -0.2, z), M["shelf"], rg)
tyre_y = [-2.4 + 0.52 * i for i in range(9)]
for lv, z in enumerate((0.45, 1.36)):
    for i, y in enumerate(tyre_y):
        if lv == 1 and i % 3 == 2:
            continue
        tire(f"RackTyre{lv}_{i}", (rx, y, z + 0.0), rg, 0.34, 0.22, "X", rim=(i % 2 == 0))
# right wall: wheels on wall
for i, y in enumerate((-1.2, 0.0, 1.2)):
    pass

# ------------------------------------------------------------------ CAR
CAR = empty("Car", (0, 0.0, 0), G)

SRC_CAR = os.path.join(ROOT, "tools", "src", "bmw_m4_f82_razor.glb")
CAR_LEN = 4.72

def import_car():
    """BMW M4 F82 Razor 2014 by vecarz (Sketchfab, CC BY 4.0) – cleaned & repainted dark grey."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SRC_CAR)
    new = [o for o in bpy.data.objects if o not in before]
    for o in list(new):
        if o.type == "MESH" and ("dff" in o.name):
            new.remove(o)
            bpy.data.objects.remove(o, do_unlink=True)
    paint = M["body"]
    for o in new:
        if o.type != "MESH":
            continue
        for slot in o.material_slots:
            if slot.material and slot.material.name in ("chassis.009", "chassis.9", "chassis.013"):
                slot.material = paint
    bpy.context.view_layer.update()
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in new:
        if o.type == "MESH":
            for v in o.bound_box:
                w = o.matrix_world @ Vector(v)
                mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
    size = mx - mn
    s = CAR_LEN / size.y
    holder = empty("CarModel", (0, 0, 0), CAR)
    pivot = empty("CarModelPivot", (0, 0, 0), holder)
    roots = [o for o in new if o.parent is None or o.parent not in new]
    for o in roots:
        mw = o.matrix_world.copy()
        o.parent = pivot
        o.matrix_parent_inverse = pivot.matrix_world.inverted()
        o.matrix_world = mw
    c = (mn + mx) / 2
    pivot.location = (-c.x, -c.y, -mn.z)
    holder.scale = (s, s, s)
    holder.rotation_euler = (0, 0, math.pi)   # nos do -y (k vrátam)
    bpy.context.view_layer.update()
    print("CAR_DIMS", tuple(round(v * s, 3) for v in size))

if os.path.exists(SRC_CAR):
    import_car()
    WB_F, WB_R, WR, WX = -1.43, 1.43, 0.35, 0.82
else:
    def smooth_interp(table, ys, passes=3):
        arr = np.array(table, dtype=float)
        out = np.stack([np.interp(ys, arr[:, 0], arr[:, k]) for k in range(1, arr.shape[1])], axis=1)
        for _ in range(passes):
            out[1:-1] = 0.25 * out[:-2] + 0.5 * out[1:-1] + 0.25 * out[2:]
        return out

    def rounded_ring(zb, zt, hw, n=32, e=3.2, taper_top=0.82):
        zc, hh = (zb + zt) / 2, (zt - zb) / 2
        pts = []
        for k in range(n):
            a = 2 * math.pi * k / n
            c, s = math.cos(a), math.sin(a)
            x = hw * math.copysign(abs(c) ** (2 / e), c)
            zz = hh * math.copysign(abs(s) ** (2 / e), s)
            if zz > 0:
                x *= 1 - (1 - taper_top) * (zz / hh) ** 2
            pts.append(Vector((x, 0, zc + zz)))
        return pts

    def loft(name, rings, ys, material, parent, cap=True, matfn=None, mats=None):
        bm = bmesh.new()
        R = []
        for ring, y in zip(rings, ys):
            R.append([bm.verts.new((p.x, y, p.z)) for p in ring])
        n = len(R[0])
        for i in range(len(R) - 1):
            for k in range(n):
                f = bm.faces.new((R[i][k], R[i][(k + 1) % n], R[i + 1][(k + 1) % n], R[i + 1][k]))
                if matfn:
                    f.material_index = matfn(i, k, ys[i], ys[i + 1])
        if cap:
            for idx, ring in ((0, R[0]), (-1, R[-1])):
                c = bm.verts.new((sum(v.co.x for v in ring) / n, ring[0].co.y, sum(v.co.z for v in ring) / n))
                for k in range(n):
                    bm.faces.new((c, ring[(k + 1) % n], ring[k]) if idx == 0 else (c, ring[k], ring[(k + 1) % n]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        o = from_bm(name, bm, None, parent, smooth=True)
        for m in (mats or [material]):
            o.data.materials.append(m)
        return o

    # ---- lower body
    TABLE = [  # y, z_bot, z_top, half_width
        (-2.40, 0.32, 0.64, 0.74),
        (-2.36, 0.26, 0.72, 0.84),
        (-2.18, 0.23, 0.81, 0.92),
        (-1.80, 0.22, 0.88, 0.94),
        (-1.20, 0.21, 0.97, 0.955),
        (-0.50, 0.21, 1.02, 0.955),
        (0.60, 0.21, 1.02, 0.955),
        (1.50, 0.21, 1.05, 0.95),
        (2.00, 0.23, 1.06, 0.93),
        (2.30, 0.27, 1.02, 0.88),
        (2.40, 0.36, 0.92, 0.80),
    ]
    ys = np.linspace(-2.40, 2.40, 56)
    vals = smooth_interp(TABLE, ys, passes=3)
    rings = [rounded_ring(v[0], v[1], v[2], n=36, e=3.4, taper_top=0.80) for v in vals]
    body = loft("Body", rings, ys, M["body"], CAR)
    # wheel arches
    WB_F, WB_R, WR, WX = -1.43, 1.43, 0.35, 0.82
    cutters = []
    for sy in (WB_F, WB_R):
        for sx in (-1, 1):
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=0.435, radius2=0.435, depth=0.62)
            c = from_bm("cut", bm, M["black"], None, smooth=False)
            c.rotation_euler = (0, math.pi / 2, 0)
            c.location = (sx * (0.54 + 0.31), sy, WR + 0.0)
            c.parent = CAR
            cutters.append(c)
    bpy.context.view_layer.objects.active = body
    for c in cutters:
        md = body.modifiers.new("arch", "BOOLEAN")
        md.operation = "DIFFERENCE"
        md.object = c
        try:
            md.solver = "EXACT"
        except Exception:
            pass
        try:
            md.material_mode = "TRANSFER"
        except Exception:
            pass
    apply_modifiers(body)
    for c in cutters:
        bpy.data.objects.remove(c, do_unlink=True)

    # ---- greenhouse
    CAB = [  # y, height above beltline
        (-0.64, 0.0), (-0.52, 0.07), (-0.22, 0.22), (0.20, 0.355), (0.60, 0.405), (1.00, 0.395),
        (1.30, 0.33), (1.60, 0.20), (1.80, 0.07), (1.92, 0.0),
    ]
    cy = np.linspace(-0.64, 1.92, 46)
    cv = smooth_interp(CAB, cy, passes=3)[:, 0]
    ZB = 0.995
    WB, WT = 0.80, 0.585
    def cab_ring(h):
        s = min(1.0, h / 0.28)
        wb = WB
        wt = WB - (WB - WT) * s
        wm = (wb + wt) / 2 + 0.035
        z0, z1 = ZB - 0.04, ZB + h
        return [Vector(p) for p in (
            (-wb, 0, z0), (-wb, 0, ZB), (-wm, 0, ZB + h * 0.5), (-wt, 0, z1),
            (-wt * 0.5, 0, z1 + 0.012), (0, 0, z1 + 0.018), (wt * 0.5, 0, z1 + 0.012),
            (wt, 0, z1), (wm, 0, ZB + h * 0.5), (wb, 0, ZB), (wb, 0, z0)
        )]
    cab_rings = [cab_ring(max(h, 0.0005)) for h in cv]
    mats_c = [M["body"], M["glass"]]
    def cab_mat(i, k, y0, y1):
        ym = (y0 + y1) / 2
        # ring segments: 0:(-wb,z0)->(-wb,ZB) skirt, 1: lower side, 2: upper side, 3..6 roof, 7: upper side R, 8 lower side R, 9 skirt R, 10 bottom
        side = k in (1, 2, 7, 8)
        roof = k in (3, 4, 5, 6)
        if side:
            if -0.40 < ym < 0.47 or 0.60 < ym < 1.42:
                return 1 if k in (2, 7) or k in (1, 8) else 0
            return 0
        if roof:
            if ym < 0.02 or ym > 1.12:
                return 1
            return 0
        return 0
    cabin = loft("Cabin", cab_rings, cy, M["body"], CAR, matfn=cab_mat, mats=mats_c)

    # ---- details
    def part(name, size, loc, material, bevel=0.01, rot=(0, 0, 0)):
        return box(name, size, loc, material, CAR, bevel=bevel, rot=rot)

    # kidney grille (two big openings, M-style)
    for sx in (-1, 1):
        part("KidneyFrame", (0.40, 0.045, 0.30), (sx * 0.215, -2.372, 0.50), M["chrome"], 0.03)
        part("Kidney", (0.34, 0.05, 0.24), (sx * 0.215, -2.39, 0.50), M["black"], 0.02)
        for i in range(6):
            part("KidneySlat", (0.30, 0.02, 0.012), (sx * 0.215, -2.405, 0.40 + i * 0.04), M["chrome"], 0.004)
    part("IntakeLower", (1.30, 0.05, 0.14), (0, -2.36, 0.33), M["black"], 0.03)
    part("Splitter", (1.5, 0.08, 0.02), (0, -2.34, 0.245), M["black"], 0.005)
    for sx in (-1, 1):
        part("IntakeSide", (0.30, 0.05, 0.14), (sx * 0.78, -2.27, 0.36), M["black"], 0.03)
        # headlights: dark housing + slim light bar
        part("Headlight", (0.40, 0.04, 0.07), (sx * 0.74, -2.15, 0.70), M["black"], 0.02, rot=(0, 0, sx * 0.30))
        part("DRL", (0.32, 0.02, 0.014), (sx * 0.74, -2.175, 0.705), M["lamp"], 0.004, rot=(0, 0, sx * 0.30))
        # mirrors
        part("Mirror", (0.20, 0.12, 0.09), (sx * 0.98, -0.52, 1.05), M["body"], 0.03)
        # side skirts
        part("Skirt", (0.04, 2.1, 0.07), (sx * 0.958, 0.0, 0.285), M["black"], 0.01)
        # M stripes on front fender
        for i, mm in enumerate((M["mb"], M["md"], M["mr"])):
            part("MStripe", (0.012, 0.045, 0.045), (sx * 0.968, -1.05 + i * 0.05, 0.86), mm, 0.002)
        # door handles
        part("Handle", (0.01, 0.16, 0.025), (sx * 0.963, 0.1, 0.93), M["black"], 0.004)
        part("Handle2", (0.01, 0.16, 0.025), (sx * 0.955, 1.0, 0.93), M["black"], 0.004)
        # tail lights
        part("Taillight", (0.46, 0.05, 0.10), (sx * 0.62, 2.405, 0.89), M["tail"], 0.02, rot=(0, 0, -sx * 0.12))
        # quad exhaust
    for sx in (-1, 1):
        for dx in (0.22, 0.46):
            cyl("Exhaust", 0.055, 0.12, (sx * dx + sx * 0.0, 2.44, 0.31), M["chrome"], CAR, axis="Y", verts=20)
            cyl("ExhaustIn", 0.043, 0.13, (sx * dx, 2.445, 0.31), M["black"], CAR, axis="Y", verts=20)
    part("Diffuser", (1.25, 0.09, 0.16), (0, 2.37, 0.38), M["black"], 0.02)
    part("TrunkLip", (1.30, 0.12, 0.04), (0, 2.22, 1.075), M["body"], 0.015)
    part("RearBumperLow", (1.6, 0.08, 0.05), (0, 2.36, 0.27), M["black"], 0.01)
    # plates (EU-style)
    part("PlateF", (0.52, 0.015, 0.11), (0, -2.43, 0.26), M["plate"], 0.004)
    part("PlateR", (0.52, 0.015, 0.11), (0, 2.435, 0.60), M["plate"], 0.004)
    # hood power-dome lines
    for sx in (-1, 1):
        part("HoodLine", (0.012, 1.3, 0.008), (sx * 0.30, -1.35, 1.012), M["black"], 0.002, rot=(0.02, 0, 0))
    # roof antenna fin
    part("Fin", (0.05, 0.12, 0.03), (0, 1.42, 1.37), M["black"], 0.01)

    # ---- wheels
    def wheel(name, loc, side):
        g = empty(name, loc, CAR)
        s = side
        # tyre
        t = tire(name + "_tyre", (0, 0, 0), g, r=WR, w=0.27, axis="X", rim=False)
        # rim face (5 double spokes), disc, caliper
        cyl(name + "_barrel", 0.245, 0.22, (0, 0, 0), M["rimDark"], g, axis="X", verts=36)
        face = empty(name + "_face", (s * 0.105, 0, 0), g)
        cyl(name + "_hub", 0.05, 0.03, (0, 0, 0), M["rim"], face, axis="X", verts=18)
        for i in range(10):
            a = 2 * math.pi * i / 10 + (0.0 if i % 2 == 0 else 0.0)
            r0 = 0.145
            b = box(name + "_spoke", (0.025, 0.026, 0.19), (0, 0, 0), M["rim"], face, bevel=0.004)
            b.location = (0, math.cos(a) * r0, math.sin(a) * r0)
            b.rotation_euler = (a - math.pi / 2 + (0.18 if i % 2 else -0.18), 0, 0)
        cyl(name + "_lip", 0.255, 0.03, (s * 0.115, 0, 0), M["rim"], g, axis="X", verts=36, caps=False)
        cyl(name + "_disc", 0.215, 0.03, (s * -0.02, 0, 0), M["disc"], g, axis="X", verts=36)
        box(name + "_caliper", (0.07, 0.11, 0.17), (s * 0.04, 0.0 if True else 0, 0.14), M["caliper"], g, bevel=0.02)
        return g

    for nm, y in (("F", WB_F), ("R", WB_R)):
        wheel(f"Wheel{nm}L", (-WX, y, WR), -1)
        wheel(f"Wheel{nm}R", (WX, y, WR), 1)
        # wheel tubs rendered via transferred boolean material

# ------------------------------------------------------------------ export
bpy.ops.object.select_all(action="DESELECT")
# smooth shading + split-normal safe
for o in bpy.data.objects:
    if o.type == "MESH" and o.modifiers:
        pass

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "tools", "garage.blend"))
bpy.ops.export_scene.gltf(
    filepath=OUT, export_format="GLB", export_apply=True, export_yup=True,
    export_cameras=False, export_lights=False, export_extras=False,
)
print("EXPORTED", OUT, os.path.getsize(OUT))

if PREVIEW:
    # quick preview render with Cycles
    sc = bpy.context.scene
    bpy.ops.object.light_add(type="AREA", location=(0, 0, 2.6))
    L = bpy.context.object; L.data.energy = 400; L.data.size = 3
    from mathutils import Vector as V
    tgt = V((0, 0.65, 0.7))
    for nm, loc, lens, out in (
        ("front", (0.0, -2.95, 1.2), 22, "prev_front.png"),
        ("side", (0.0, -2.95, 1.1), 18, "prev_side.png"),
        ("car34", (2.3, -2.9, 1.5), 20, "prev_car34.png"),
    ):
        pass
    for nm, loc, lens, out in (
        ("side", (-7.5, 0.65, 0.75), 55, "prev_side.png"),
        ("front", (0.0, -2.95, 1.2), 22, "prev_front.png"),
        ("car34", (2.3, -2.9, 1.5), 20, "prev_car34.png"),
        ("rear34", (-2.3, 2.6, 1.6), 20, "prev_rear34.png"),
    ):
        for o_ in bpy.data.objects:
            if o_.name.startswith(("WallLeft", "WallRight", "Ceiling", "RackTyre", "Rack", "Stack")):
                o_.hide_render = (nm == "side")
        rot = (tgt - V(loc)).to_track_quat("-Z", "Y").to_euler()
        bpy.ops.object.camera_add(location=loc, rotation=rot)
        cam = bpy.context.object
        cam.data.lens = lens
        sc.camera = cam
        sc.render.engine = "CYCLES"
        sc.cycles.samples = 24
        sc.cycles.device = "CPU"
        sc.render.resolution_x, sc.render.resolution_y = 960, 540
        sc.render.filepath = os.path.join(ROOT, "tools", out)
        sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.3, 0.3, 0.35)
        bpy.ops.render.render(write_still=True)
