# Blender 5.x headless:  blender -b --factory-startup --python tools/build_scene.py [-- --preview]
# Postaví garáž (vlastná tvorba) + osadí auto BMW M4 F82 (vecarz, CC BY 4.0) a exportuje models/garage.glb
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "models", "garage.glb")
TEXDIR = os.path.join(ROOT, "tools", "tex")
SRC_CAR = os.path.join(ROOT, "tools", "src", "bmw_m4_f82_razor.glb")
PREVIEW = "--preview" in sys.argv
os.makedirs(TEXDIR, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
rng = np.random.default_rng(7)

# ================================================================== textúry (procedurálne → JPG)
def upsample(a, n):
    s = a.shape[0]
    x = np.linspace(0, s - 1, n)
    i0 = np.floor(x).astype(int); i1 = np.minimum(i0 + 1, s - 1); f = x - i0
    r = a[i0] * (1 - f)[:, None] + a[i1] * f[:, None]
    return r[:, i0] * (1 - f)[None, :] + r[:, i1] * f[None, :]

def fbm(n, octaves=(4, 8, 16, 32, 64, 128), amps=(1, .7, .5, .35, .25, .18)):
    out = np.zeros((n, n))
    for o, a in zip(octaves, amps):
        out += upsample(rng.random((o + 1, o + 1)), n) * a
    out -= out.min(); out /= out.max()
    return out

def save_tex(name, rgb):
    n = rgb.shape[0]
    img = bpy.data.images.new(name, n, n, alpha=False)
    rgba = np.concatenate([np.clip(rgb, 0, 1), np.ones((n, n, 1))], axis=2)[::-1]
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    path = os.path.join(TEXDIR, name + ".jpg")
    img.filepath_raw = path; img.file_format = "JPEG"
    scene = bpy.context.scene
    scene.render.image_settings.quality = 82
    img.save()
    bpy.data.images.remove(img)
    return bpy.data.images.load(path)

N = 1024
yy, xx = np.mgrid[0:N, 0:N]
def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    n = np.stack([-dx, dy, np.ones_like(h)], axis=2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5
def save_normal(name, h, strength):
    img = save_tex(name, normal_from_height(h, strength))
    img.colorspace_settings.name = "Non-Color"
    return img

# biele tehly – dlaždica 1 m × 1 m: 16 radov po 6.25 cm, tehla 25 cm, väzba na polovicu
RH, BW, MO = 64, 256, 6
row = yy // RH
off = (row % 2) * (BW // 2)
bx = (xx + off) % BW; by = yy % RH
edge = np.minimum.reduce([bx - MO, BW - bx, by - MO, RH - by]).astype(float)
mortar = edge <= 0
bid = (row * 7 + (xx + off) // BW) % 4096
tint = rng.random(4096)[bid]
noise = fbm(N, (16, 32, 64, 128), (1, .7, .5, .3))
chips = rng.random((N, N)) > 0.996
col = 0.84 + tint * 0.08 + (noise - 0.5) * 0.07 - chips * 0.10
col = np.where(mortar, 0.66 + (noise - 0.5) * 0.05, col)
TEX_WALL = save_tex("white_brick", np.stack([col, col * 0.995, col * 0.985], axis=2))
hgt = np.clip(edge / 5.0, 0, 1) + (noise - 0.5) * 0.25 + tint[..., None][..., 0] * 0.1
TEX_WALL_N = save_normal("white_brick_n", hgt, 2.2)

# epoxidová podlaha s vločkami
f = fbm(N, (8, 16, 32), (1, .6, .4)) * 0.035 + 0.055
fl = rng.random((N, N))
f = np.where(fl > 0.985, f + 0.12, f)
f = np.where(fl < 0.008, f + 0.05, f)
TEX_FLOOR = save_tex("epoxy_floor", np.stack([f, f * 1.02, f * 1.06], axis=2))

# dezén pneumatiky (u = obvod, v = šírka behúňa)
TN = 512
ty, tx = np.mgrid[0:TN, 0:TN]
vc = np.abs(ty - TN / 2)
lat = ((tx + vc * 0.9) % 64) < 9
lat &= (vc > 34) & (vc < 236)
circ = (np.abs(vc - 34) < 6) | (np.abs(vc - 120) < 5)
sip = ((tx + vc * 0.9) % 32 < 2) & (vc > 40) & (vc < 115)
th = 1.0 - lat * 1.0 - circ * 1.0 - sip * 0.5
tc = 0.045 + (th - 1) * 0.03 + (fbm(TN, (8, 16, 32), (1, .6, .4)) - 0.5) * 0.01
TEX_TREAD = save_tex("tyre_tread", np.stack([tc, tc, tc * 1.05], axis=2))
TEX_TREAD_N = save_normal("tyre_tread_n", th, 1.6)

# ================================================================== materiály
def mat(name, color, metallic=0.0, rough=0.5, emit=None, emit_strength=0.0, coat=0.0, tex=None, normal=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if tex is not None:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = tex
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if normal is not None:
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = normal
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if coat:
        for k in ("Coat Weight", "Clearcoat"):
            if k in b.inputs: b.inputs[k].default_value = coat
        for k in ("Coat Roughness", "Clearcoat Roughness"):
            if k in b.inputs: b.inputs[k].default_value = 0.05
    if emit:
        for k in ("Emission Color", "Emission"):
            if k in b.inputs: b.inputs[k].default_value = (*emit, 1)
        if "Emission Strength" in b.inputs: b.inputs["Emission Strength"].default_value = emit_strength
    return m

M = {
    "wall": mat("WhiteBrick", (1, 1, 1), 0.0, 0.8, tex=TEX_WALL, normal=TEX_WALL_N),
    "floor": mat("Floor", (1, 1, 1), 0.15, 0.32, tex=TEX_FLOOR),
    "ceil": mat("Ceiling", (0.30, 0.31, 0.32), 0.0, 0.9),
    "lining": mat("WallLining", (0.20, 0.21, 0.22), 0.7, 0.42),
    "beam": mat("SteelBeam", (0.11, 0.115, 0.12), 0.8, 0.45),
    "orange": mat("Orange", (1.0, 0.33, 0.08), 0.0, 0.45),
    "orangeGlow": mat("OrangeGlow", (1.0, 0.33, 0.08), 0.0, 0.4, emit=(1.0, 0.32, 0.06), emit_strength=6.0),
    "white": mat("SignWhite", (0.92, 0.92, 0.92), 0.0, 0.4),
    "line": mat("FloorLine", (0.55, 0.56, 0.58), 0.0, 0.6),
    "asphalt": mat("Asphalt", (0.07, 0.07, 0.075), 0.0, 0.95),
    "concrete": mat("Concrete", (0.30, 0.30, 0.29), 0.0, 0.95),
    "door": mat("DoorPanel", (0.13, 0.135, 0.14), 0.6, 0.42),
    "red": mat("RedCabinet", (0.62, 0.03, 0.03), 0.55, 0.38, coat=0.6),
    "redDark": mat("RedDark", (0.30, 0.02, 0.02), 0.4, 0.5),
    "steel": mat("Steel", (0.62, 0.63, 0.65), 1.0, 0.3),
    "dark": mat("DarkSteel", (0.05, 0.05, 0.055), 0.6, 0.5),
    "top": mat("Worktop", (0.12, 0.12, 0.13), 0.5, 0.45),
    "wood": mat("Wood", (0.42, 0.27, 0.15), 0.0, 0.6),
    "tire": mat("Rubber", (0.016, 0.016, 0.018), 0.0, 0.72),
    "tread": mat("TyreTread", (1, 1, 1), 0.0, 0.8, tex=TEX_TREAD, normal=TEX_TREAD_N),
    "alloy": mat("Alloy", (0.62, 0.63, 0.66), 1.0, 0.22),
    "alloyDark": mat("AlloyDark", (0.10, 0.10, 0.11), 0.9, 0.35),
    "glassDark": mat("WindowGlass", (0.02, 0.025, 0.03), 0.6, 0.06),
    "signGlow": mat("SignWhiteGlow", (1, 1, 1), 0.0, 0.3, emit=(1, 1, 1), emit_strength=2.2),
    "rim": mat("Rim", (0.42, 0.43, 0.46), 1.0, 0.28),
    "body": mat("CarPaint", (0.17, 0.18, 0.20), 0.85, 0.30, coat=1.0),
    "plate": mat("PlateBlank", (0.78, 0.78, 0.78), 0.0, 0.5),
    "ledpanel": mat("LedPanel", (1, 1, 0.95), 0.0, 0.3, emit=(1, 0.98, 0.92), emit_strength=4.0),
    "lamp": mat("WallLamp", (1, 1, 0.95), 0.0, 0.3, emit=(1, 0.95, 0.85), emit_strength=3.0),
    "shelf": mat("Shelf", (0.16, 0.17, 0.19), 0.7, 0.5),
    "turn": mat("Turntable", (0.07, 0.075, 0.08), 0.85, 0.35),
    "turnTop": mat("TurntableTop", (0.16, 0.165, 0.17), 0.9, 0.3),
    "canBlue": mat("CanBlue", (0.05, 0.18, 0.55), 0.2, 0.4),
    "canYellow": mat("CanYellow", (0.85, 0.62, 0.05), 0.2, 0.4),
    "canGreen": mat("CanGreen", (0.05, 0.38, 0.12), 0.2, 0.4),
    "extRed": mat("ExtinguisherRed", (0.7, 0.02, 0.02), 0.3, 0.3),
}

# ================================================================== geometria – pomocníci
def link(o, parent=None):
    bpy.context.scene.collection.objects.link(o)
    if parent is not None:
        o.parent = parent
    return o

def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    return link(o, parent)

def world_uv(bm, offset, tile):
    """Box-projection UV in meters (tile = meters per texture repeat)."""
    uv = bm.loops.layers.uv.new()
    ox, oy, oz = offset
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            p = l.vert.co
            x, y, z = p.x + ox, p.y + oy, p.z + oz
            if ax == 0: u, v = y, z
            elif ax == 1: u, v = x, z
            else: u, v = x, y
            l[uv].uv = (u / tile[0], v / tile[1])

def from_bm(name, bm, material=None, parent=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    link(o, parent)
    if material is not None:
        o.data.materials.append(material)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return o

def box(name, size, loc, material, parent=None, bevel=0.0, rot=(0, 0, 0), uv=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bm.normal_update()
    if uv:
        world_uv(bm, loc, uv)
    o = from_bm(name, bm, material, parent, smooth=False)
    o.location = loc; o.rotation_euler = rot
    if bevel > 0:
        m = o.modifiers.new("bv", "BEVEL"); m.width = bevel; m.segments = 2; m.limit_method = "ANGLE"
    return o

def cyl(name, r, depth, loc, material, parent=None, axis="Z", verts=32, caps=True, r2=None, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=verts, radius1=r, radius2=(r if r2 is None else r2), depth=depth)
    o = from_bm(name, bm, material, parent, smooth=True)
    if axis == "X": o.rotation_euler = (0, math.pi / 2, 0)
    elif axis == "Y": o.rotation_euler = (math.pi / 2, 0, 0)
    if rot: o.rotation_euler = rot
    o.location = loc
    return o

def torus(name, R, r, loc, material, parent=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=96, minor_segments=8, location=loc)
    o = bpy.context.object; o.name = name
    o.data.materials.append(material)
    if parent: o.parent = parent
    return o

def text3d(name, body, size, loc, material, parent=None, extrude=0.02, rot=(math.pi / 2, 0, 0), align="CENTER"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body; cu.size = size; cu.extrude = extrude; cu.align_x = align
    try:
        cu.font = bpy.data.fonts.load(r"C:\Windows\Fonts\arialbd.ttf")
    except Exception:
        pass
    o = bpy.data.objects.new(name, cu)
    link(o)
    o.location = loc; o.rotation_euler = rot
    bpy.context.view_layer.objects.active = o
    for s in bpy.context.selected_objects: s.select_set(False)
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.object
    o.data.materials.clear(); o.data.materials.append(material)
    if parent:
        mw = o.matrix_world.copy(); o.parent = parent; o.matrix_world = mw
    return o

from mathutils import Matrix
_MESH = {}
def tyre_mesh(r, w):
    key = ("tyre", r, w)
    if key in _MESH: return _MESH[key]
    prof = [(0.62, -0.44), (0.66, -0.49), (0.72, -0.505), (0.76, -0.495), (0.78, -0.505), (0.86, -0.515), (0.93, -0.49), (0.968, -0.44), (0.99, -0.38), (1.0, -0.31),
            (1.0, -0.1), (1.0, 0.1), (1.0, 0.31), (0.99, 0.38), (0.968, 0.44), (0.93, 0.49), (0.86, 0.515),
            (0.78, 0.505), (0.76, 0.495), (0.72, 0.505), (0.66, 0.49), (0.62, 0.44), (0.60, 0.30), (0.60, -0.30)]
    segs = 72
    bm = bmesh.new(); uv = bm.loops.layers.uv.new()
    rings = [[bm.verts.new((rf * r * math.cos(2 * math.pi * k / segs), rf * r * math.sin(2 * math.pi * k / segs), zf * w)) for k in range(segs + 1)] for rf, zf in prof]
    np_ = len(prof)
    for i in range(np_):
        j = (i + 1) % np_
        for k in range(segs):
            f = bm.faces.new((rings[i][k], rings[i][k + 1], rings[j][k + 1], rings[j][k]))
            tread = 8 <= i <= 14
            f.material_index = 1 if tread else 0
            for l, (ii, kk) in zip(f.loops, ((i, k), (i, k + 1), (j, k + 1), (j, k))):
                l[uv].uv = (kk / segs * 14, prof[ii][1] + 0.5)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6) if False else None
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("TyreMesh"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(M["tire"]); me.materials.append(M["tread"])
    _MESH[key] = me
    return me

def rim_mesh(r, w):
    key = ("rim", r, w)
    if key in _MESH: return _MESH[key]
    bm = bmesh.new()
    def add(fn, mi):
        before = set(bm.faces); fn(); 
        for f in set(bm.faces) - before: f.material_index = mi
    R = r * 0.62
    add(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=R * 0.97, radius2=R * 0.97, depth=w * 0.7), 1)          # barrel
    add(lambda: bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=R * 1.03, radius2=R * 0.99, depth=0.035,
                                      matrix=Matrix.Translation((0, 0, w * 0.36))), 0)                                                  # lip
    add(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=R * 0.22, radius2=R * 0.18, depth=0.05,
                                      matrix=Matrix.Translation((0, 0, w * 0.34))), 0)                                                  # hub
    add(lambda: bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=R * 0.95, radius2=R * 0.95, depth=0.01,
                                      matrix=Matrix.Translation((0, 0, w * 0.18))), 1)                                                  # tmavé pozadie disku
    for i in range(5):                                                                                                                   # 5 širokých ramien (Y-profil)
        for d in (-0.16, 0.16):
            a = 2 * math.pi * i / 5 + d
            m = Matrix.Translation((math.cos(a) * R * 0.56, math.sin(a) * R * 0.56, w * 0.3)) @ Matrix.Rotation(a, 4, "Z") @ Matrix.Rotation(0.18, 4, "Y")                 @ Matrix.Diagonal((R * 0.78, R * 0.13, 0.04, 1))
            add(lambda m=m: bmesh.ops.create_cube(bm, size=1.0, matrix=m), 0)
    for i in range(5):                                                                                                                   # matice
        a = 2 * math.pi * (i + 0.5) / 5
        add(lambda a=a: bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.011, radius2=0.011, depth=0.02,
                                               matrix=Matrix.Translation((math.cos(a) * R * 0.13, math.sin(a) * R * 0.13, w * 0.37))), 1)
    me = bpy.data.meshes.new("RimMesh"); bm.to_mesh(me); bm.free()
    me.materials.append(M["alloy"]); me.materials.append(M["alloyDark"])
    _MESH[key] = me
    return me

def tire(name, loc, parent, r=0.34, w=0.24, axis="Z", rim=True, flip=False):
    o = bpy.data.objects.new(name, tyre_mesh(r, w)); link(o, parent)
    o.location = loc
    if axis == "X": o.rotation_euler = (0, math.pi / 2 * (-1 if flip else 1), 0)
    elif axis == "Y": o.rotation_euler = (math.pi / 2, 0, 0)
    if rim:
        ro = bpy.data.objects.new(name + "_rim", rim_mesh(r, w)); link(ro, o)
    return o

# ================================================================== GARÁŽ
GW, GD, GH = 7.6, 7.8, 3.2        # vnútro: šírka (x), hĺbka (y), výška (z)
T = 0.3                           # hrúbka steny
OW, OH = 4.8, 2.8                 # otvor vrát
FY = -GD / 2                      # vnútorná strana prednej steny
WALL_UV = (1.0, 1.0)
G = empty("Garage")

# podlaha, okolie
box("Floor", (GW, GD, 0.1), (0, 0, -0.05), M["floor"], G, uv=(2.0, 2.0))
box("Ground", (70, 46, 0.1), (0, -26 - GD / 2, -0.07), M["asphalt"], G)
box("Apron", (17.0, 6.5, 0.06), (0, FY - T - 2.95, -0.03), M["concrete"], G)   # dosiahne až po podlahu garáže (bez medzery pod vrátami)
# bezpečnostné čiary pri stenách
for nm, s, l in (("LineL", (0.06, GD - 0.8, 0.004), (-GW / 2 + 0.75, 0, 0.002)),
                 ("LineR", (0.06, GD - 0.8, 0.004), (GW / 2 - 0.75, 0, 0.002)),
                 ("LineB", (GW - 1.5, 0.06, 0.004), (0, GD / 2 - 0.95, 0.002))):
    box(nm, s, l, M["line"], G)
box("Drain", (1.6, 0.14, 0.006), (0, FY + 0.55, 0.003), M["dark"], G)

# strop + nosníky + LED
box("Ceiling", (GW + 2 * T, GD + 2 * T, T), (0, 0, GH + T / 2), M["ceil"], G)
for i, y in enumerate((-2.6, 0.0, 2.6)):
    box(f"Beam{i}", (GW, 0.22, 0.32), (0, y, GH - 0.16), M["beam"], G)
for i, y in enumerate((-1.3, 1.3)):
    for j, x in enumerate((-1.6, 1.6)):
        box(f"Led{i}{j}", (2.6, 0.2, 0.04), (x, y, GH - 0.02), M["ledpanel"], G)
for i, y in enumerate((-3.4, 3.4)):
    box(f"LedEdge{i}", (4.0, 0.14, 0.04), (0, y, GH - 0.02), M["ledpanel"], G)

# steny (betónové panely)
H = GH + 0.3
box("WallBack", (GW + 2 * T, T, H), (0, GD / 2 + T / 2, H / 2 - 0.05), M["wall"], G, uv=WALL_UV)
box("WallLeft", (T, GD + 2 * T, H), (-GW / 2 - T / 2, 0, H / 2 - 0.05), M["wall"], G, uv=WALL_UV)
box("WallRight", (T, GD + 2 * T, H), (GW / 2 + T / 2, 0, H / 2 - 0.05), M["wall"], G, uv=WALL_UV)
sideW = (GW + 2 * T - OW) / 2
box("FrontL", (sideW, T, H), (-(OW / 2 + sideW / 2), FY - T / 2, H / 2 - 0.05), M["wall"], G, uv=WALL_UV)
box("FrontR", (sideW, T, H), ((OW / 2 + sideW / 2), FY - T / 2, H / 2 - 0.05), M["wall"], G, uv=WALL_UV)
box("FrontHeader", (OW, T, H - OH), (0, FY - T / 2, OH + (H - OH) / 2 - 0.05), M["wall"], G, uv=WALL_UV)

# spodný plechový obklad (rebrovaný) + oranžový pás
def lining(name, length, axis, pos, inward):
    g = empty(name, (0, 0, 0), G)
    LH = 1.15
    if axis == "x":
        box(name + "_p", (length, 0.03, LH), (0, pos, LH / 2), M["lining"], g)
        n = int(length / 0.16)
        for i in range(n):
            box(name + "_r", (0.035, 0.02, LH - 0.04), (-length / 2 + 0.08 + i * 0.16, pos + inward * 0.02, LH / 2), M["lining"], g)
        box(name + "_s", (length, 0.035, 0.07), (0, pos + inward * 0.015, LH + 0.035), M["orange"], g)
    else:
        box(name + "_p", (0.03, length, LH), (pos, 0, LH / 2), M["lining"], g)
        n = int(length / 0.16)
        for i in range(n):
            box(name + "_r", (0.02, 0.035, LH - 0.04), (pos + inward * 0.02, -length / 2 + 0.08 + i * 0.16, LH / 2), M["lining"], g)
        box(name + "_s", (0.035, length, 0.07), (pos + inward * 0.015, 0, LH + 0.035), M["orange"], g)
lining("LiningBack", GW, "x", GD / 2 - 0.015, -1)
lining("LiningLeft", GD, "y", -GW / 2 + 0.015, 1)
lining("LiningRight", GD, "y", GW / 2 - 0.015, -1)

# oceľové stĺpy na bočných stenách
for i, y in enumerate((-2.6, 0.0, 2.6)):
    for sx in (-1, 1):
        box(f"Col{i}{'L' if sx < 0 else 'R'}", (0.22, 0.26, GH), (sx * (GW / 2 - 0.11), y, GH / 2), M["beam"], G)
        box(f"ColCap{i}{sx}", (0.24, 0.28, 0.06), (sx * (GW / 2 - 0.11), y, 1.2), M["orange"], G)

# ---- logo PLS GROUP na zadnej stene (podsvietená tabuľa)
sg = empty("BackSign", (0, 0, 0), G)
SY = GD / 2 - 0.06
box("SignBoard", (3.2, 0.05, 0.75), (-1.15, SY, 2.45), M["beam"], sg, bevel=0.01)
box("SignGlow", (3.3, 0.02, 0.03), (-1.15, SY - 0.03, 2.06), M["orangeGlow"], sg)
box("SignP", (0.5, 0.06, 0.5), (-2.4, SY - 0.04, 2.45), M["orange"], sg)
text3d("SignPChar", "P", 0.44, (-2.4, SY - 0.08, 2.29), M["beam"], sg, extrude=0.012)
text3d("SignText", "PLS GROUP", 0.42, (-0.9, SY - 0.06, 2.31), M["white"], sg, extrude=0.02)
text3d("SignSub", "AUTOSERVIS", 0.13, (-0.9, SY - 0.06, 2.13), M["orange"], sg, extrude=0.01)

# ---- vráta (pivot hore – JS ich "zroluje" nahor)
DW = OW - 0.03
door = empty("Door", (0, FY - T + 0.11, OH - 0.004), G)
n_pan = 7
ph = OH / n_pan
for i in range(n_pan):
    z = -(i + 0.5) * ph
    box(f"DoorPanel{i}", (DW, 0.06, ph - 0.01), (0, 0, z), M["door"], door, bevel=0.01)
    box(f"DoorRib{i}", (DW - 0.12, 0.012, 0.03), (0, -0.034, z + ph * 0.22), M["dark"], door)
box("DoorStripe", (DW, 0.064, 0.05), (0, -0.002, -OH * 0.5), M["orange"], door)
box("DoorBacking", (DW, 0.01, OH - 0.01), (0, 0.037, -OH / 2), M["dark"], door)

# ---- fasáda: veľká tehlová budova, podsvietený nápis, okná, svetlá
FF = FY - T                     # vonkajšia plocha prednej steny
FW, FH = 17.0, 5.8              # šírka a výška fasády (budova pôsobí väčšia než samotná garáž)
fs = empty("Facade", (0, 0, 0), G)
sw = FW / 2 - OW / 2
box("FacadeL", (sw, 0.08, FH), (-(OW / 2 + sw / 2), FF - 0.04, FH / 2 - 0.05), M["wall"], fs, uv=(1.0, 1.0))
box("FacadeR", (sw, 0.08, FH), ((OW / 2 + sw / 2), FF - 0.04, FH / 2 - 0.05), M["wall"], fs, uv=(1.0, 1.0))
box("FacadeTop", (OW, 0.08, FH - OH), (0, FF - 0.04, OH + (FH - OH) / 2 - 0.05), M["wall"], fs, uv=(1.0, 1.0))
box("Plinth", (FW, 0.12, 0.45), (0, FF - 0.1, 0.2), M["beam"], fs)
box("Cornice", (FW + 0.3, 0.4, 0.3), (0, FF - 0.12, FH - 0.05), M["beam"], fs)
for sx in (-1, 1):
    box(f"Pilaster{sx}", (0.35, 0.18, FH), (sx * (FW / 2 - 0.17), FF - 0.12, FH / 2 - 0.05), M["beam"], fs)
# rám vrát
for nm, s_, l in (("FrameL", (0.17, 0.115, OH + 0.165), (-OW / 2 - 0.09, FF - 0.135, (OH + 0.165) / 2 + 0.003)),
                  ("FrameR", (0.17, 0.115, OH + 0.165), (OW / 2 + 0.09, FF - 0.135, (OH + 0.165) / 2 + 0.003)),
                  ("FrameT", (OW + 0.35, 0.115, 0.165), (0, FF - 0.135, OH + 0.088))):
    box(nm, s_, l, M["orange"], fs)
# veľká svetelná tabuľa nad vrátami
SZ = OH + 1.05
box("Fascia", (9.6, 0.16, 1.35), (0, FF - 0.14, SZ), M["beam"], fs, bevel=0.02)
box("FasciaGlow", (9.7, 0.05, 0.05), (0, FF - 0.2, SZ - 0.7), M["orangeGlow"], fs)
box("FacadeSignP", (1.0, 0.1, 1.0), (-4.05, FF - 0.25, SZ), M["orange"], fs, bevel=0.01)
text3d("FacadeSignPChar", "P", 0.95, (-4.05, FF - 0.31, SZ - 0.34), M["beam"], fs, extrude=0.02)
text3d("FacadeSignText", "PLS GROUP", 0.92, (-3.35, FF - 0.24, SZ - 0.18), M["signGlow"], fs, extrude=0.04, align="LEFT")
text3d("FacadeSignSub", "AUTOSERVIS  ·  BRATISLAVA", 0.24, (-3.33, FF - 0.24, SZ - 0.52), M["orangeGlow"], fs, extrude=0.015, align="LEFT")
# okná kancelárie a vchod
for sx in (-1, 1):
    x = sx * 5.6
    box(f"Win{sx}", (2.2, 0.06, 1.5), (x, FF - 0.06, 1.75), M["glassDark"], fs)
    box(f"WinFrameT{sx}", (2.36, 0.12, 0.08), (x, FF - 0.1, 2.54), M["beam"], fs)
    box(f"WinFrameB{sx}", (2.36, 0.18, 0.08), (x, FF - 0.12, 0.96), M["beam"], fs)
    box(f"WinFrameL{sx}", (0.08, 0.12, 1.6), (x - 1.14, FF - 0.1, 1.75), M["beam"], fs)
    box(f"WinFrameR{sx}", (0.08, 0.12, 1.6), (x + 1.14, FF - 0.1, 1.75), M["beam"], fs)
    box(f"WinMull{sx}", (0.05, 0.1, 1.5), (x, FF - 0.09, 1.75), M["beam"], fs)
box("EntryDoor", (1.05, 0.08, 2.25), (3.55, FF - 0.06, 1.125), M["glassDark"], fs)
box("EntryFrame", (1.2, 0.12, 2.35), (3.55, FF - 0.03, 1.175), M["beam"], fs)
box("EntryHandle", (0.04, 0.06, 0.7), (3.2, FF - 0.13, 1.1), M["orange"], fs)
box("EntryCanopy", (1.6, 0.9, 0.08), (3.55, FF - 0.45, 2.55), M["beam"], fs)
for i, x in enumerate((-(OW / 2 + 1.3), (OW / 2 + 1.3) - 0.0, -7.2, 7.2)):
    box(f"FacadeLamp{i}", (0.42, 0.16, 0.08), (x, FF - 0.12, OH + 0.1 if abs(x) < 6 else 3.2), M["lamp"], fs)
# predpolie: obrubník, stĺpiky, vodorovné čiary
box("Curb", (FW, 0.25, 0.12), (0, FF - 6.2, 0.03), M["concrete"], fs)
for sx in (-1, 1):
    cyl(f"Bollard{sx}", 0.09, 0.9, (sx * (OW / 2 + 0.55), FF - 0.55, 0.45), M["beam"], fs, verts=20)
    cyl(f"BollardTop{sx}", 0.095, 0.1, (sx * (OW / 2 + 0.55), FF - 0.55, 0.85), M["orange"], fs, verts=20)
for i in range(6):
    box(f"Park{i}", (0.1, 4.2, 0.005), (-8.5 + i * 2.6 if i < 3 else 3.3 + (i - 3) * 2.6, FF - 9.5, 0.002), M["white"], fs)

# ---- zadná stena: červené skrine so šuflíkmi
def drawer_unit(name, x0, x1, h, n, y_back=GD / 2 - 0.05, depth=0.65, top=True):
    w = x1 - x0; cx = (x0 + x1) / 2; cy = y_back - depth / 2
    g = empty(name, (0, 0, 0), G)
    box(name + "_carcass", (w, depth, h), (cx, cy, h / 2 + 0.06), M["redDark"], g, bevel=0.01)
    dh = (h - 0.1) / n
    for i in range(n):
        z = 0.06 + 0.06 + dh * (i + 0.5)
        box(f"{name}_d{i}", (w - 0.05, 0.04, dh - 0.018), (cx, y_back - depth - 0.015, z), M["red"], g, bevel=0.008)
        box(f"{name}_h{i}", (w * 0.55, 0.03, 0.024), (cx, y_back - depth - 0.05, z + dh * 0.22), M["steel"], g, bevel=0.006)
    if top:
        box(name + "_top", (w + 0.04, depth + 0.04, 0.05), (cx, cy, h + 0.085), M["top"], g)
    for sx in (-w / 2 + 0.07, w / 2 - 0.07):
        cyl(f"{name}_wheel", 0.045, 0.03, (cx + sx, cy, 0.045), M["dark"], g, axis="X", verts=12)
    return g

drawer_unit("CabA", -3.55, -2.4, 1.0, 5)
drawer_unit("CabB", -2.4, -1.25, 1.0, 5)
drawer_unit("CabC", -1.25, -0.1, 1.0, 5)
drawer_unit("TallD", 0.1, 1.45, 1.9, 9)
drawer_unit("TallE", 1.5, 2.3, 1.9, 7)
box("Pegboard", (3.4, 0.03, 0.7), (-1.83, GD / 2 - 0.06, 1.55), M["shelf"], G)
for i in range(9):
    box(f"Tool{i}", (0.045, 0.02, 0.22 + 0.04 * (i % 3)), (-3.3 + i * 0.37, GD / 2 - 0.085, 1.52), M["steel"], G)
box("Vise", (0.22, 0.18, 0.14), (-0.6, GD / 2 - 0.35, 1.19), M["dark"], G, bevel=0.01)

# ---- ľavá stena: regál s pneumatikami
rg = empty("TyreRack", (0, 0, 0), G)
rx = -GW / 2 + 0.38
for y in (-3.3, -1.2, 1.2, 3.0):
    for dx in (-0.22, 0.22):
        box("RackPost", (0.05, 0.05, 2.2), (rx + dx, y, 1.1), M["shelf"], rg)
for z in (0.05, 1.08, 2.15):
    for dx in (-0.22, 0.22):
        box("RackBeam", (0.05, 6.35, 0.05), (rx + dx, -0.15, z), M["shelf"], rg)
for lv, z in enumerate((0.40, 1.43)):
    y = -3.15
    i = 0
    while y < 3.2:
        if not (lv == 1 and 8 <= i <= 10):
            tire(f"RackTyre{lv}_{i}", (rx, y, z), rg, 0.33, 0.235, "Y", rim=(lv == 0 and i % 6 < 2))
        y += 0.245 + (0.06 if i % 4 == 3 else 0.0)
        i += 1

# ---- pravá stena: police s olejmi, kompresor, hasiaci prístroj, stohy pneumatík
sh = empty("RightShelf", (0, 0, 0), G)
SX = GW / 2 - 0.3
for z in (1.55, 2.05):
    box("ShelfBoard", (0.35, 2.2, 0.04), (SX, 1.0, z), M["shelf"], sh)
cans = [M["canBlue"], M["canYellow"], M["canGreen"], M["red"]]
for lv, z in enumerate((1.57, 2.07)):
    for i in range(9):
        cm = cans[(i + lv) % 4]
        hh = 0.26 if i % 3 else 0.32
        box(f"Can{lv}_{i}", (0.16, 0.14, hh), (SX - 0.02, 0.05 + i * 0.22, z + hh / 2 + 0.02), cm, sh, bevel=0.01)
cyl("Extinguisher", 0.08, 0.5, (GW / 2 - 0.12, FY + 0.6, 0.85), M["extRed"], G, verts=16)
cyl("ExtinguisherTop", 0.03, 0.08, (GW / 2 - 0.12, FY + 0.6, 1.14), M["dark"], G, verts=10)
box("ExtSign", (0.02, 0.22, 0.22), (GW / 2 - 0.02, FY + 0.6, 1.45), M["red"], G)
def stack(name, x, y, n, r=0.34, w=0.24):
    g = empty(name, (0, 0, 0), G)
    for i in range(n):
        tire(f"{name}_{i}", (x + 0.012 * ((i * 7) % 3 - 1), y + 0.01 * ((i * 5) % 3 - 1), w / 2 + i * w), g, r, w, "Z", rim=False)
stack("StackR1", 3.15, 2.25, 6)
stack("StackR2", 3.15, -0.3, 4)
stack("StackB", 2.95, 3.1, 5)

# ---- otočná plošina (podstava statická, horný kruh sa točí s autom)
TT_R = 2.85
cyl("TurntableBase", TT_R + 0.08, 0.06, (0, 0, 0.03), M["turn"], G, verts=96)
torus("TurntableRing", TT_R + 0.06, 0.018, (0, 0, 0.055), M["orangeGlow"], G)
CAR = empty("Car", (0, 0, 0.065), G)       # JS otáča týmto uzlom
cyl("TurntableTop", TT_R, 0.03, (0, 0, -0.005), M["turnTop"], CAR, verts=96)
for i in range(24):
    a = 2 * math.pi * i / 24
    b = box(f"TTGroove{i}", (0.012, TT_R - 0.5, 0.004), (0, 0, 0.012), M["turn"], CAR)
    b.rotation_euler = (0, 0, a)
    b.location = (math.sin(-a) * (TT_R / 2 + 0.25) * -1 * -1, math.cos(a) * (TT_R / 2 + 0.25), 0.012)
torus("TurntableInner", 0.9, 0.012, (0, 0, 0.012), M["turn"], CAR)

# ================================================================== AUTO
CAR_LEN = 4.72
def import_car():
    """BMW M4 F82 Razor 2014 by vecarz (Sketchfab, CC BY 4.0) – vyčistené: bez log, nálepiek a ŠPZ."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SRC_CAR)
    new = [o for o in bpy.data.objects if o not in before]
    for o in list(new):
        mats = [s.material.name for s in o.material_slots if s.material] if o.type == "MESH" else []
        if o.type == "MESH" and ("dff" in o.name or "spoon" in mats):
            new.remove(o); bpy.data.objects.remove(o, do_unlink=True)
    paint, rubber = M["body"], M["tire"]
    for o in new:
        if o.type != "MESH":
            continue
        for slot in o.material_slots:
            n = slot.material.name if slot.material else ""
            if n in ("chassis.009", "chassis.9", "chassis.013", "chassis.017"):   # livrea, nálepky, logá BMW/M4
                slot.material = paint
            elif n == "plate_ok.0":                                               # ŠPZ → čistá
                slot.material = M["plate"]
            elif n == "wheel.009":                                                # bok pneumatiky s nápismi
                slot.material = rubber
    bpy.context.view_layer.update()
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in new:
        if o.type == "MESH":
            for v in o.bound_box:
                w = o.matrix_world @ Vector(v); mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
    size = mx - mn; s = CAR_LEN / size.y
    holder = empty("CarModel", (0, 0, 0), CAR)
    pivot = empty("CarModelPivot", (0, 0, 0), holder)
    for o in [o for o in new if o.parent is None or o.parent not in new]:
        mw = o.matrix_world.copy(); o.parent = pivot
        o.matrix_parent_inverse = pivot.matrix_world.inverted(); o.matrix_world = mw
    cc = (mn + mx) / 2
    pivot.location = (-cc.x, -cc.y, -mn.z)
    holder.scale = (s, s, s)
    holder.rotation_euler = (0, 0, math.pi)        # nos do -y (k vrátam)
    bpy.context.view_layer.update()
    return [o for o in new if o.name in bpy.data.objects and o.type == "MESH"]

car_meshes = import_car()

# ---- body pre bubliny: vypočítané z geometrie auta (súradnice Car uzla; nos -y, pravý bok +x)
inv = CAR.matrix_world.inverted()
pts = []
for o in car_meshes:
    me = o.data
    co = np.empty(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(inv @ o.matrix_world)
    pts.append(co @ mw[:3, :3].T + mw[:3, 3])
P = np.concatenate(pts)
ymin, ymax = P[:, 1].min(), P[:, 1].max(); xmax = P[:, 0].max(); ztop = P[:, 2].max()
def top_z(y0, x0=0.0, r=0.12):
    m = (abs(P[:, 1] - y0) < r) & (abs(P[:, 0] - x0) < r)
    return float(P[m, 2].max()) if m.any() else 0.9
def obj_center(pred):
    sel = [o for o in car_meshes if pred(o)]
    if not sel: return None
    a = np.concatenate([np.array([inv @ o.matrix_world @ Vector(v) for v in o.bound_box]) for o in sel])
    return (a.min(0) + a.max(0)) / 2, a.min(0), a.max(0)
# kolesá: objekty s pneumatikou (wheel.009) – rozdeliť podľa kvadrantu
wheels = []
for o in car_meshes:
    if any(s.material == M["tire"] for s in o.material_slots):
        a = np.array([inv @ o.matrix_world @ Vector(v) for v in o.bound_box]); wheels.append((a.min(0) + a.max(0)) / 2)
wheels = np.array(wheels) if wheels else np.array([[0.85, -1.45, 0.34], [0.85, 1.45, 0.34]])
fr = min((w for w in wheels if w[0] > 0), key=lambda w: w[1])
rr = max((w for w in wheels if w[0] > 0), key=lambda w: w[1])
_ws = []
for o in car_meshes:
    if "windscreen" in o.name:
        a = np.array([inv @ o.matrix_world @ Vector(v) for v in o.bound_box]); _ws.append((a.min(0) + a.max(0)) / 2)
ws_c = min(_ws, key=lambda c: c[1]) if _ws else np.array([0, -0.5, 1.05])     # predné (nie zadné) sklo
hood_y = ymin + (ws_c[1] - ymin) * 0.45
# výfuk: najnižšie zadné body vpravo od stredu
rear = P[(P[:, 1] > ymax - 0.18) & (P[:, 2] < 0.45) & (P[:, 0] > 0.25) & (P[:, 0] < 0.75)]
ex = rear.mean(0) if len(rear) else np.array([0.45, ymax, 0.3])
ANCH = {
    "klima": (0.0, ymin + 0.02, 0.36),                       # kondenzátor za predným nárazníkom
    "motor": (0.0, hood_y, top_z(hood_y) + 0.06),            # kapota
    "sklo": (ws_c[0], ws_c[1] + 0.12, ws_c[2] + 0.24),              # čelné sklo
    "pneu": (fr[0] + 0.14, fr[1], fr[2]),                    # predné koleso
    "servis": (rr[0] + 0.14, rr[1], rr[2]),                  # zadné koleso – brzdy, olej, podvozok
    "diag": (0.62, ws_c[1] + 0.55, 0.95),                    # kabína – diagnostická zásuvka pri palubovke
    "odtah": (xmax - 0.05, ymin + 0.25, 0.24),               # ťažné oko vpredu vpravo
    "stk": (float(ex[0]), ymax + 0.04, float(ex[2])),        # výfuk – emisná kontrola
}
for k, v in ANCH.items():
    empty("AN_" + k, tuple(float(x) for x in v), CAR)
    print("ANCHOR", k, tuple(round(float(x), 3) for x in v))
print("CAR_BOX", round(float(xmax), 3), round(float(ymin), 3), round(float(ymax), 3), round(float(ztop), 3))

# ================================================================== export
for o in bpy.data.objects:
    if o.type == "MESH" and o.modifiers:
        bpy.context.view_layer.objects.active = o
        for s in bpy.context.selected_objects: s.select_set(False)
        o.select_set(True)
        for m in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "tools", "garage.blend"))
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_image_format="AUTO")
print("EXPORTED", OUT, os.path.getsize(OUT))
