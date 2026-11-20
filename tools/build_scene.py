# Blender 5.x headless:  blender -b --factory-startup --python tools/build_scene.py [-- --preview]
# Postaví garáž (vlastná tvorba) + osadí auto Škoda Octavia IV RS (DR1KING100K, CC BY 4.0) a exportuje models/garage.glb
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "models", "garage.glb")
TEXDIR = os.path.join(ROOT, "tools", "tex")
SRC_CAR = os.path.join(ROOT, "tools", "src", "skoda_octavia_mk4_rs.glb")
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
    "body": mat("CarPaint", (0.40, 0.010, 0.014), 0.72, 0.30, coat=1.0),      # červená metalíza
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
    # dielňa – skrine, náradie, drobnosti
    "cabYellow": mat("YellowCabinet", (0.95, 0.60, 0.02), 0.35, 0.33, coat=0.6),
    "cabDark": mat("CabinetDark", (0.06, 0.06, 0.065), 0.5, 0.5),
    "cavity": mat("DrawerCavity", (0.01, 0.01, 0.012), 0.0, 0.9),
    "chrome": mat("ToolChrome", (0.80, 0.80, 0.83), 1.0, 0.16),
    "gripRed": mat("GripRed", (0.70, 0.04, 0.03), 0.0, 0.55),
    "gripYellow": mat("GripYellow", (0.95, 0.72, 0.04), 0.0, 0.5),
    "gripBlue": mat("GripBlue", (0.04, 0.18, 0.65), 0.0, 0.5),
    "rubber": mat("RubberBlack", (0.025, 0.025, 0.028), 0.0, 0.8),
    "cardboard": mat("Cardboard", (0.52, 0.37, 0.21), 0.0, 0.92),
    "rag": mat("ShopRag", (0.55, 0.07, 0.05), 0.0, 1.0),
    "rag2": mat("ShopRagGrey", (0.16, 0.15, 0.14), 0.0, 1.0),
    "oil": mat("OilStain", (0.012, 0.011, 0.009), 0.0, 0.12),
    "paper": mat("Paper", (0.88, 0.88, 0.86), 0.0, 0.8),
    "screen": mat("TabletScreen", (0.05, 0.25, 0.5), 0.0, 0.2, emit=(0.15, 0.55, 1.0), emit_strength=1.6),
    "jack": mat("JackRed", (0.55, 0.03, 0.02), 0.45, 0.38, coat=0.3),
    "mug": mat("MugWhite", (0.85, 0.85, 0.83), 0.0, 0.25),
    "conduit": mat("Conduit", (0.45, 0.46, 0.48), 0.9, 0.4),
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
text3d("SignPChar", "PLS", 0.21, (-2.4, SY - 0.08, 2.375), M["white"], sg, extrude=0.012)   # biele PLS ako favicon
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
for sx in (-1, 1):    # sokel len vedľa vrát – otvor ostáva voľný
    box(f"Plinth{sx}", (sw - 0.2, 0.12, 0.45), (sx * (OW / 2 + 0.2 + (sw - 0.2) / 2), FF - 0.1, 0.2), M["beam"], fs)
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

# ================================================================== DIELŇA – náradie a drobnosti
def ring(name, R, r, loc, material, parent, rot=(0, 0, 0), seg=20):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg, minor_segments=6)
    o = bpy.context.object; o.name = name
    o.data.materials.append(material)
    for p in o.data.polygons: p.use_smooth = True
    o.parent = parent; o.location = loc; o.rotation_euler = rot
    return o

def blob(name, size, loc, material, parent, jitter=0.18, sub=2, rot=(0, 0, 0)):
    """Pokrčená handra / vrecko: deformovaná ikosféra."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=1.0)
    o = bpy.context.object; o.name = name
    for v in o.data.vertices:
        v.co *= 1 + (rng.random() - 0.5) * 2 * jitter
    o.data.materials.append(material)
    for p in o.data.polygons: p.use_smooth = True
    o.parent = parent; o.location = loc; o.scale = size; o.rotation_euler = rot
    return o

def stain(name, r, loc, parent, n=18):
    """Nepravidelná olejová škvrna na podlahe."""
    bm = bmesh.new()
    vs = []
    ph = rng.random(3) * 6.28
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (1 + 0.22 * math.sin(3 * a + ph[0]) + 0.12 * math.sin(5 * a + ph[1]) + 0.08 * math.sin(7 * a + ph[2]))
        vs.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, 0)))
    bm.faces.new(vs)
    o = from_bm(name, bm, M["oil"], parent, smooth=False)
    o.location = loc
    return o

def tool_group(name, loc, rot, parent=G):
    g = empty(name, loc, parent); g.rotation_euler = rot
    return g

# Náradie je modelované v lokálnych osiach: dĺžka = Z, hrúbka = Y (kolmo na stenu), šírka = X.
HANG = lambda tilt=0.0: (0, tilt, 0)                   # visí na stene (rovina XZ)
LIE = lambda yaw: (math.pi / 2, 0, yaw)                # leží naplocho na doske

def wrench(name, L, loc, rot, parent=G):
    g = tool_group(name, loc, rot, parent)
    w, t = 0.012 + L * 0.06, 0.007
    box(name + "_s", (w * 0.72, t, L * 0.62), (0, 0, 0), M["chrome"], g)
    ring(name + "_r", w * 0.62, w * 0.22, (0, 0, L * 0.36), M["chrome"], g, rot=(math.pi / 2, 0, 0), seg=16)
    box(name + "_o", (w * 1.5, t * 1.1, w * 0.5), (0, 0, -L * 0.33), M["chrome"], g)
    for sx in (-1, 1):
        box(name + "_j", (w * 0.4, t * 1.1, w * 0.9), (sx * w * 0.55, 0, -L * 0.33 - w * 0.6), M["chrome"], g, rot=(0, sx * 0.25, 0))
    return g

def adj_wrench(name, L, loc, rot, parent=G):
    g = tool_group(name, loc, rot, parent)
    box(name + "_h", (0.03, 0.01, L * 0.7), (0, 0, -L * 0.12), M["chrome"], g, bevel=0.003)
    box(name + "_head", (0.065, 0.014, 0.05), (0.008, 0, L * 0.3), M["chrome"], g, bevel=0.004)
    box(name + "_jaw", (0.018, 0.014, 0.04), (0.03, 0, L * 0.3 + 0.04), M["chrome"], g)
    cyl(name + "_hole", 0.007, 0.016, (0, 0, -L * 0.44), M["cavity"], g, axis="Y", verts=10)
    return g

def screwdriver(name, L, loc, rot, grip, parent=G):
    g = tool_group(name, loc, rot, parent)
    cyl(name + "_g", 0.014, L * 0.4, (0, 0, L * 0.3), grip, g, verts=12)
    cyl(name + "_g2", 0.010, L * 0.06, (0, 0, L * 0.07), M["rubber"], g, verts=10)
    cyl(name + "_sh", 0.0035, L * 0.55, (0, 0, -L * 0.25), M["chrome"], g, verts=8)
    return g

def hammer(name, loc, rot, parent=G, rubber_head=False):
    g = tool_group(name, loc, rot, parent)
    cyl(name + "_h", 0.013, 0.31, (0, 0, -0.02), M["wood"] if not rubber_head else M["rubber"], g, verts=10)
    if rubber_head:
        cyl(name + "_head", 0.032, 0.12, (0, 0, 0.14), M["rubber"], g, axis="X", verts=16)
    else:
        box(name + "_head", (0.12, 0.026, 0.03), (0.01, 0, 0.145), M["dark"], g, bevel=0.004)
        box(name + "_claw", (0.04, 0.02, 0.02), (-0.06, 0, 0.152), M["dark"], g, rot=(0, -0.4, 0))
    return g

def pliers(name, loc, rot, grip, parent=G):
    g = tool_group(name, loc, rot, parent)
    for sx in (-1, 1):
        box(name + "_jaw", (0.011, 0.008, 0.07), (sx * 0.004, 0, 0.075), M["chrome"], g, rot=(0, -sx * 0.06, 0))
        box(name + "_grip", (0.013, 0.012, 0.12), (sx * 0.016, 0, -0.035), grip, g, rot=(0, sx * 0.16, 0), bevel=0.003)
    cyl(name + "_pin", 0.008, 0.016, (0, 0, 0.035), M["chrome"], g, axis="Y", verts=10)
    return g

def ratchet(name, loc, rot, parent=G):
    g = tool_group(name, loc, rot, parent)
    cyl(name + "_h", 0.009, 0.2, (0, 0, -0.02), M["chrome"], g, verts=10)
    cyl(name + "_grip", 0.012, 0.09, (0, 0, -0.07), M["rubber"], g, verts=10)
    cyl(name + "_head", 0.02, 0.016, (0, 0, 0.09), M["chrome"], g, axis="Y", verts=16)
    cyl(name + "_sq", 0.006, 0.02, (0, 0.015, 0.09), M["chrome"], g, axis="Y", verts=4)
    return g

def socket(name, r, loc, parent=G, h=None):
    return cyl(name, r, h or r * 2.6, loc, M["chrome"], parent, verts=12)

def spray_can(name, loc, rot=(0, 0, 0), parent=G, colors=("canBlue", "canYellow")):
    g = tool_group(name, loc, rot, parent)
    cyl(name + "_b", 0.033, 0.19, (0, 0, 0.095), M[colors[0]], g, verts=16)
    cyl(name + "_band", 0.0335, 0.05, (0, 0, 0.13), M[colors[1]], g, verts=16)
    cyl(name + "_cap", 0.02, 0.03, (0, 0, 0.205), M["dark"], g, verts=12)
    return g

def cardboard_box(name, size, loc, yaw=0.0, parent=G):
    o = box(name, size, loc, M["cardboard"], parent, bevel=0.004, rot=(0, 0, yaw))
    box(name + "_tape", (size[0] + 0.002, 0.05, 0.002), (loc[0], loc[1], loc[2] + size[2] / 2 + 0.001), M["cardboard"], parent, rot=(0, 0, yaw))
    return o

# ---- zadná stena: žlté skrine so šuflíkmi (jeden šuflík vytiahnutý)
def drawer_unit(name, x0, x1, h, n, y_back=GD / 2 - 0.05, depth=0.65, top=True, opened=None):
    opened = opened or {}
    w = x1 - x0; cx = (x0 + x1) / 2; cy = y_back - depth / 2
    g = empty(name, (0, 0, 0), G)
    box(name + "_carcass", (w, depth, h), (cx, cy, h / 2 + 0.06), M["cabDark"], g, bevel=0.01)
    dh = (h - 0.1) / n
    yf = y_back - depth - 0.015
    for i in range(n):
        z = 0.06 + 0.06 + dh * (i + 0.5)
        d = opened.get(i, 0.0)
        if d:
            box(f"{name}_cav{i}", (w - 0.07, 0.006, dh - 0.03), (cx, y_back - depth - 0.004, z), M["cavity"], g)
            tw, tz = w - 0.09, z - dh / 2 + 0.03            # zásuvka: dno + bočnice
            box(f"{name}_tb{i}", (tw, 0.55, 0.008), (cx, yf - d + 0.3, tz), M["cabDark"], g)
            for sx in (-1, 1):
                box(f"{name}_ts{i}", (0.008, 0.55, dh - 0.05), (cx + sx * tw / 2, yf - d + 0.3, z - 0.005), M["cabDark"], g)
            # obsah vytiahnutej zásuvky – nástrčné hlavice a kľúč
            for k in range(7):
                socket(f"{name}_so{i}_{k}", 0.009 + 0.0015 * k, (cx - tw / 2 + 0.06 + k * 0.075, yf - d + 0.07 + (k % 2) * 0.04, tz + 0.02), g)
            wrench(f"{name}_dw{i}", 0.22, (cx + 0.05, yf - d + 0.17, tz + 0.008), LIE(1.48), g)
            wrench(f"{name}_dw2{i}", 0.18, (cx - 0.12, yf - d + 0.2, tz + 0.016), LIE(1.62), g)
        box(f"{name}_d{i}", (w - 0.05, 0.04, dh - 0.018), (cx, yf - d, z), M["cabYellow"], g, bevel=0.008)
        box(f"{name}_h{i}", (w * 0.55, 0.03, 0.024), (cx, yf - d - 0.035, z + dh * 0.22), M["steel"], g, bevel=0.006)
    if top:
        box(name + "_top", (w + 0.04, depth + 0.04, 0.05), (cx, cy, h + 0.085), M["top"], g)
    for sx in (-w / 2 + 0.07, w / 2 - 0.07):
        cyl(f"{name}_wheel", 0.045, 0.03, (cx + sx, cy, 0.045), M["dark"], g, axis="X", verts=12)
    return g

drawer_unit("CabA", -3.55, -2.4, 1.0, 5)
drawer_unit("CabB", -2.4, -1.25, 1.0, 5, opened={3: 0.34})
drawer_unit("CabC", -1.25, -0.1, 1.0, 5, opened={1: 0.12})
drawer_unit("TallD", 0.1, 1.45, 1.9, 9, opened={4: 0.22})
drawer_unit("TallE", 1.5, 2.3, 1.9, 7)
box("Vise", (0.22, 0.18, 0.14), (-0.6, GD / 2 - 0.35, 1.19), M["dark"], G, bevel=0.01)
box("ViseJaw", (0.16, 0.03, 0.07), (-0.6, GD / 2 - 0.47, 1.23), M["dark"], G, bevel=0.005)
cyl("ViseScrew", 0.008, 0.2, (-0.6, GD / 2 - 0.58, 1.21), M["chrome"], G, axis="Y", verts=8)
cyl("ViseBar", 0.006, 0.16, (-0.6, GD / 2 - 0.68, 1.21), M["chrome"], G, axis="X", verts=8)

# ---- perforovaná doska s náradím (visí nad skrinkami)
PN = 256
py_, px_ = np.mgrid[0:PN, 0:PN]
holes = ((px_ % 32 - 16) ** 2 + (py_ % 32 - 16) ** 2) < 20
pb = 0.30 + (fbm(PN, (8, 16), (1, .5)) - 0.5) * 0.03
pb = np.where(holes, 0.03, pb)
TEX_PEG = save_tex("pegboard", np.stack([pb, pb * 1.01, pb * 1.03], axis=2))
M["peg"] = mat("Pegboard", (1, 1, 1), 0.5, 0.5, tex=TEX_PEG)
PY = GD / 2 - 0.06
box("Pegboard", (3.4, 0.03, 0.72), (-1.83, PY, 1.56), M["peg"], G, uv=(0.2, 0.2))
box("PegFrame", (3.44, 0.04, 0.03), (-1.83, PY - 0.005, 1.93), M["beam"], G)
box("PegFrameB", (3.44, 0.04, 0.03), (-1.83, PY - 0.005, 1.19), M["beam"], G)
TY = PY - 0.03                                         # rovina náradia pred doskou
def hook(x, z):
    cyl("Hook", 0.003, 0.05, (x, TY + 0.005, z), M["chrome"], G, axis="Y", verts=6)
# sada očkoplochých kľúčov (odstupňované dĺžky)
for i in range(10):
    L = 0.13 + i * 0.018
    x = -3.42 + i * 0.062
    hook(x, 1.86)
    wrench(f"WallWrench{i}", L, (x, TY, 1.86 - L * 0.36), HANG(0.0 if i != 6 else 0.12))
# kladivá
hook(-2.68, 1.86); hammer("Hammer", (-2.72, TY, 1.70), HANG(0.05))
hook(-2.52, 1.86); hammer("Mallet", (-2.52, TY, 1.69), HANG(-0.04), rubber_head=True)
# lišta so skrutkovačmi
box("DriverRack", (0.5, 0.06, 0.02), (-2.15, TY - 0.02, 1.70), M["beam"], G)
grips = [M["gripRed"], M["gripYellow"], M["gripRed"], M["gripYellow"], M["gripBlue"], M["gripRed"]]
for i, gm in enumerate(grips):
    L = 0.2 + (i % 3) * 0.04
    screwdriver(f"Driver{i}", L, (-2.36 + i * 0.08, TY - 0.03, 1.70 + L * 0.02), HANG(0.0), gm)
# kliešte
for i, (gm, tilt) in enumerate(((M["gripRed"], 0.05), (M["gripBlue"], -0.08), (M["gripRed"], 0.0))):
    hook(-1.75 + i * 0.09, 1.86)
    pliers(f"Pliers{i}", (-1.75 + i * 0.09, TY, 1.74), HANG(tilt), gm)
hook(-1.38, 1.86); adj_wrench("AdjWrench", 0.26, (-1.38, TY, 1.72), HANG(0.08))
hook(-1.22, 1.86); ratchet("WallRatchet", (-1.22, TY, 1.74), HANG(-0.05))
# pílka na kov
sawg = tool_group("Hacksaw", (-0.85, TY, 1.62), HANG(0.0))
box("Saw_top", (0.36, 0.012, 0.014), (0, 0, 0.06), M["gripBlue"], sawg)
box("Saw_blade", (0.33, 0.004, 0.012), (0, 0, -0.04), M["chrome"], sawg)
box("Saw_front", (0.014, 0.012, 0.11), (0.17, 0, 0.01), M["gripBlue"], sawg)
box("Saw_grip", (0.03, 0.02, 0.11), (-0.18, 0, 0.0), M["rubber"], sawg, rot=(0, 0.25, 0), bevel=0.004)
hook(-0.75, 1.86); hook(-0.95, 1.86)
# zvinutý predlžovací kábel na háku
hook(-0.42, 1.86)
for k in range(4):
    ring(f"Cable{k}", 0.11 + k * 0.004, 0.007, (-0.42 + k * 0.004, TY - 0.012 - k * 0.006, 1.74 - k * 0.006), M["gripYellow"], G, rot=(math.pi / 2, 0.15 * k, 0), seg=28)
# papier so servisným záznamom
box("Clipboard", (0.18, 0.006, 0.25), (-0.2, TY, 1.6), M["wood"], G, rot=(0, 0.04, 0))
box("ClipPaper", (0.16, 0.004, 0.2), (-0.2, TY - 0.005, 1.585), M["paper"], G, rot=(0, 0.04, 0))
box("Clip", (0.05, 0.012, 0.02), (-0.2, TY - 0.008, 1.71), M["chrome"], G)

# ---- pracovná doska: veci "len tak položené"
WT = 1.11                                              # horná plocha dosky
adj_wrench("BenchAdj", 0.25, (-2.95, 3.38, WT + 0.007), LIE(0.55))
wrench("BenchWrench", 0.22, (-2.62, 3.30, WT + 0.004), LIE(-0.35))
ratchet("BenchRatchet", (-2.25, 3.42, WT + 0.009), LIE(1.9))
socket("BenchSocket", 0.012, (-2.12, 3.28, WT + 0.016))
# kufrík s hlavicami – otvorený
box("SocketCase", (0.42, 0.26, 0.04), (-1.78, 3.52, WT + 0.02), M["gripBlue"], G, bevel=0.006)
box("SocketCaseIn", (0.39, 0.23, 0.01), (-1.78, 3.52, WT + 0.041), M["rubber"], G)
box("SocketLid", (0.42, 0.04, 0.26), (-1.78, 3.67, WT + 0.15), M["gripBlue"], G, rot=(-0.25, 0, 0), bevel=0.006)
for k in range(12):
    socket(f"CaseSocket{k}", 0.008 + 0.0012 * (k % 6), (-1.94 + (k % 6) * 0.062, 3.46 + (k // 6) * 0.1, WT + 0.06))
blob("Rag", (0.16, 0.12, 0.03), (-1.32, 3.36, WT + 0.02), M["rag"], G, rot=(0, 0, 0.4))
blob("RagFold", (0.07, 0.05, 0.025), (-1.24, 3.30, WT + 0.04), M["rag"], G, jitter=0.25)
# hrnček s kávou
cyl("Mug", 0.04, 0.095, (-1.0, 3.48, WT + 0.048), M["mug"], G, verts=16)
cyl("MugCoffee", 0.036, 0.004, (-1.0, 3.48, WT + 0.09), M["oil"], G, verts=16)
ring("MugHandle", 0.025, 0.007, (-0.955, 3.48, WT + 0.05), M["mug"], G, rot=(math.pi / 2, 0, 0), seg=12)
spray_can("Spray1", (-0.82, 3.62, WT))
spray_can("Spray2", (-1.12, 3.3, WT + 0.033), rot=(0, math.pi / 2, 0.3), colors=("gripRed", "dark"))
# fľaša oleja + lievik
box("OilBottle", (0.12, 0.07, 0.24), (-0.32, 3.62, WT + 0.12), M["canYellow"], G, bevel=0.012)
cyl("OilCap", 0.018, 0.03, (-0.32, 3.62, WT + 0.255), M["dark"], G, verts=10)
cyl("Funnel", 0.07, 0.1, (-0.16, 3.52, WT + 0.06), M["gripRed"], G, verts=16, r2=0.012, caps=False)
# diagnostický tablet
box("Tablet", (0.26, 0.18, 0.012), (-3.3, 3.6, WT + 0.06), M["dark"], G, rot=(-0.55, 0, 0.15), bevel=0.004)
box("TabletScreen", (0.23, 0.15, 0.002), (-3.3, 3.594, WT + 0.065), M["screen"], G, rot=(-0.55, 0, 0.15))
box("TabletStand", (0.2, 0.03, 0.08), (-3.3, 3.65, WT + 0.03), M["dark"], G, rot=(0, 0, 0.15))
cyl("DiagCable", 0.004, 0.5, (-3.0, 3.45, WT + 0.004), M["rubber"], G, axis="X", verts=6, rot=(0, math.pi / 2, 0.6))
# skrutky a matice
for k in range(9):
    cyl(f"Nut{k}", 0.008, 0.007, (-2.0 + rng.random() * 0.25, 3.2 + rng.random() * 0.1, WT + 0.004), M["chrome"], G, verts=6)

# ---- nad vysokými skriňami: krabice, kufor s náradím, navijak hadice
TOPZ = 1.9 + 0.11
cardboard_box("Box1", (0.42, 0.34, 0.26), (0.38, 3.5, TOPZ + 0.13), 0.06)
cardboard_box("Box2", (0.32, 0.28, 0.2), (0.4, 3.5, TOPZ + 0.36), -0.12)
cardboard_box("Box3", (0.36, 0.3, 0.18), (0.85, 3.48, TOPZ + 0.09), 0.2)
box("ToolCase", (0.5, 0.24, 0.2), (1.25, 3.45, TOPZ + 0.1), M["jack"], G, bevel=0.015)
box("ToolCaseHandle", (0.2, 0.03, 0.03), (1.25, 3.45, TOPZ + 0.22), M["dark"], G)
spray_can("SprayTop", (1.7, 3.45, TOPZ))
spray_can("SprayTop2", (1.8, 3.55, TOPZ), colors=("canGreen", "dark"))
# navijak vzduchovej hadice na stene
reel = tool_group("HoseReel", (1.95, GD / 2 - 0.12, 2.55), (0, 0, 0))
cyl("ReelDisc", 0.22, 0.012, (0, -0.01, 0), M["dark"], reel, axis="Y", verts=24)              # zadný kotúč
for k in range(5):                                                                            # navinutá hadica
    ring(f"ReelCoil{k}", 0.15, 0.011, (0, -0.04 - k * 0.026, 0), M["gripYellow"], reel, rot=(math.pi / 2, 0, 0), seg=24)
    ring(f"ReelCoilO{k}", 0.175, 0.011, (0, -0.05 - k * 0.026, 0), M["gripYellow"], reel, rot=(math.pi / 2, 0, 0), seg=24)
cyl("ReelDrum", 0.13, 0.15, (0, -0.1, 0), M["dark"], reel, axis="Y", verts=20)
ring("ReelRim", 0.215, 0.012, (0, -0.19, 0), M["gripRed"], reel, rot=(math.pi / 2, 0, 0), seg=28)   # predný rám – otvorený
for k in range(4):
    sp = box(f"ReelSpoke{k}", (0.42, 0.012, 0.02), (0, -0.19, 0), M["gripRed"], reel)
    sp.rotation_euler = (0, k * math.pi / 4, 0)
cyl("ReelHub", 0.035, 0.05, (0, -0.2, 0), M["chrome"], reel, axis="Y", verts=12)
box("ReelMount", (0.12, 0.06, 0.5), (0, 0.02, 0), M["dark"], reel)
# hadica visí z navijaka dolu k zemi
pts_h = [(0.18, -0.11, -0.05), (0.26, -0.13, -0.35), (0.3, -0.18, -0.75), (0.28, -0.25, -1.1)]
for k in range(len(pts_h) - 1):
    a, b = Vector(pts_h[k]), Vector(pts_h[k + 1]); dvec = b - a
    c = cyl(f"Hose{k}", 0.009, dvec.length, tuple((a + b) / 2), M["gripYellow"], reel, verts=8)
    c.rotation_euler = dvec.to_track_quat("Z", "Y").to_euler()
cyl("HoseCoupler", 0.014, 0.06, pts_h[-1], M["chrome"], reel, verts=8)

# ---- podlaha: zdvihák, stojany, vanička, ležadlo, kužele, kôš, metla
jk = tool_group("FloorJack", (-2.45, 2.45, 0), (0, 0, 0.65))
box("Jack_body", (0.26, 0.62, 0.11), (0, 0, 0.1), M["jack"], jk, bevel=0.012)
box("Jack_arm", (0.12, 0.42, 0.05), (0, 0.18, 0.19), M["jack"], jk, rot=(0.18, 0, 0))
cyl("Jack_saddle", 0.06, 0.03, (0, 0.38, 0.24), M["dark"], jk, verts=14)
for sx in (-1, 1):
    cyl("Jack_wheelF", 0.035, 0.03, (sx * 0.13, 0.27, 0.035), M["dark"], jk, axis="X", verts=12)
    cyl("Jack_wheelB", 0.05, 0.035, (sx * 0.15, -0.26, 0.05), M["dark"], jk, axis="X", verts=12)
hdl = cyl("Jack_handle", 0.014, 1.0, (0, -0.68, 0.42), M["dark"], jk, verts=8)
hdl.rotation_euler = (-0.95, 0, 0)
cyl("Jack_grip", 0.02, 0.14, (0, -1.07, 0.71), M["rubber"], jk, verts=8, rot=(-0.95, 0, 0))
for i, (x, y, yaw) in enumerate(((-2.0, 2.95, 0.3), (-1.65, 2.8, -0.2))):
    st = tool_group(f"JackStand{i}", (x, y, 0), (0, 0, yaw))
    cyl("Stand_base", 0.13, 0.32, (0, 0, 0.16), M["gripRed"], st, verts=4, r2=0.035)
    cyl("Stand_post", 0.022, 0.2, (0, 0, 0.38), M["chrome"], st, verts=10)
    box("Stand_saddle", (0.07, 0.05, 0.025), (0, 0, 0.48), M["dark"], st)
stain("Stain0", 0.22, (-2.3, 2.3, 0.0012), G)
stain("Stain1", 0.12, (-1.9, 2.75, 0.0012), G)
# vanička na olej + škvrny
cyl("DrainPan", 0.3, 0.07, (-2.35, -3.25, 0.035), M["dark"], G, verts=24, r2=0.26)
cyl("DrainOil", 0.25, 0.004, (-2.35, -3.25, 0.065), M["oil"], G, verts=24)
stain("Stain2", 0.3, (-2.05, -2.9, 0.0012), G)
stain("Stain3", 0.14, (-2.75, -2.75, 0.0012), G)
stain("Stain4", 0.18, (1.9, -3.35, 0.0012), G)
# montážne ležadlo
cr = tool_group("Creeper", (2.55, -3.2, 0), (0, 0, 0.32))
box("Creeper_board", (0.46, 0.98, 0.03), (0, 0, 0.1), M["dark"], cr, bevel=0.01)
box("Creeper_pad", (0.4, 0.3, 0.035), (0, 0.32, 0.128), M["rubber"], cr, bevel=0.012)
for sx in (-1, 1):
    for sy in (-0.42, 0, 0.42):
        cyl("Creeper_caster", 0.035, 0.03, (sx * 0.19, sy, 0.04), M["rubber"], cr, axis="X", verts=10)
# kužele
cyl("Cone1", 0.14, 0.45, (3.35, -2.55, 0.225), M["orange"], G, verts=16, r2=0.025)
box("Cone1Base", (0.32, 0.32, 0.03), (3.35, -2.55, 0.015), M["orange"], G)
cn = cyl("Cone2", 0.14, 0.45, (3.05, -2.25, 0.14), M["orange"], G, verts=16, r2=0.025)   # prevrátený
cn.rotation_euler = (math.pi / 2 - 0.3, 0, 0.9)
# kôš na odpad + handra na zemi
cyl("Bin", 0.2, 0.55, (-2.95, -3.55, 0.275), M["gripBlue"], G, verts=20, r2=0.22, caps=True)
cyl("BinRim", 0.225, 0.03, (-2.95, -3.55, 0.55), M["dark"], G, verts=20)
blob("BinRag", (0.1, 0.08, 0.06), (-2.92, -3.5, 0.58), M["rag2"], G)
blob("FloorRag", (0.13, 0.09, 0.012), (-2.6, -2.95, 0.01), M["rag2"], G, jitter=0.3, rot=(0, 0, 0.8))
# metla opretá o pravú stenu
br = tool_group("Broom", (GW / 2 - 0.12, -1.7, 0.0), (0.0, -0.18, 0.0))
cyl("Broom_stick", 0.012, 1.35, (0, 0, 0.75), M["wood"], br, verts=8)
box("Broom_head", (0.06, 0.32, 0.06), (0, 0, 0.06), M["gripRed"], br)
box("Broom_bristle", (0.05, 0.3, 0.06), (0, 0, 0.0), M["rubber"], br)
# vozík s náradím pred vysokými skriňami
cart = tool_group("ToolCart", (1.95, 2.72, 0), (0, 0, -0.18))
box("Cart_body", (0.62, 0.4, 0.62), (0, 0, 0.42), M["cabYellow"], cart, bevel=0.01)
for k in range(3):
    box("Cart_drawer", (0.58, 0.01, 0.17), (0, -0.205, 0.22 + k * 0.19), M["cabDark"], cart)
    box("Cart_pull", (0.3, 0.02, 0.02), (0, -0.215, 0.27 + k * 0.19), M["steel"], cart)
box("Cart_top", (0.66, 0.44, 0.03), (0, 0, 0.745), M["dark"], cart)
box("Cart_handle", (0.03, 0.03, 0.2), (0.33, 0, 0.84), M["chrome"], cart)
for sx in (-0.25, 0.25):
    for sy in (-0.15, 0.15):
        cyl("Cart_wheel", 0.045, 0.03, (sx, sy, 0.045), M["dark"], cart, axis="X", verts=10)
wrench("CartWrench", 0.2, (-0.1, -0.05, 0.765), LIE(0.9), cart)
blob("CartRag", (0.12, 0.09, 0.025), (0.15, 0.08, 0.78), M["rag"], cart)
box("Multimeter", (0.09, 0.16, 0.035), (-0.2, 0.1, 0.78), M["gripYellow"], cart, rot=(0, 0, 0.3), bevel=0.006)

# ---- strop: elektroinštalačné rúrky a káblové žľaby
for i, x in enumerate((-2.9, 2.9)):
    box(f"CableTray{i}", (0.2, GD - 0.4, 0.05), (x, 0, GH - 0.38), M["conduit"], G)
    for y in (-3.0, -1.3, 1.3, 3.0):
        box("TrayHanger", (0.02, 0.02, 0.06), (x, y, GH - 0.33), M["conduit"], G)
for i, z in enumerate((GH - 0.12, GH - 0.18)):
    cyl(f"Conduit{i}", 0.014, GD - 0.2, (-GW / 2 + 0.1 + i * 0.04, 0, z), M["conduit"], G, axis="Y", verts=8)

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
for z in (1.55, 2.05):                 # police sú v prednej časti steny (vzadu visí tabuľa Odťah)
    box("ShelfBoard", (0.35, 2.2, 0.04), (SX, -1.3, z), M["shelf"], sh)
cans = [M["canBlue"], M["canYellow"], M["canGreen"], M["red"]]
for lv, z in enumerate((1.57, 2.07)):
    for i in range(9):
        cm = cans[(i + lv) % 4]
        hh = 0.26 if i % 3 else 0.32
        box(f"Can{lv}_{i}", (0.16, 0.14, hh), (SX - 0.02, -2.25 + i * 0.22, z + hh / 2 + 0.02), cm, sh, bevel=0.01)

# ---- tabuľa ODŤAH: podsvietená, visí na reťaziach pri pravej stene, natočená k vrátam.
# Poloha a natočenie musia sedieť s "sign" v js/views.js (kamera pri detaile Odťahu sa pozerá sem).
TOW_LOC, TOW_YAW = (3.0, 1.0, 2.2), -math.pi / 4      # stred tabule; lícom k (-0.71, -0.71) = šikmo k vrátam
tw = empty("TowSign", (0, 0, 0), G)                   # diely sa stavajú okolo počiatku, natočí sa až na konci
box("TowBoard", (1.5, 0.06, 0.62), (0, 0, 0), M["beam"], tw, bevel=0.01)
box("TowGlow", (1.56, 0.02, 0.03), (0, -0.035, -0.33), M["orangeGlow"], tw)
box("TowGlowL", (0.03, 0.02, 0.6), (-0.765, -0.035, 0), M["orangeGlow"], tw)
FY_T = -0.045                                         # líce piktogramu
# piktogram odťahovky (kabína vľavo, rameno so žeriavom vpravo)
box("TowCab", (0.15, 0.02, 0.14), (-0.6, FY_T, 0.0), M["orangeGlow"], tw)
box("TowCabWin", (0.07, 0.02, 0.055), (-0.62, FY_T - 0.004, 0.025), M["beam"], tw)
box("TowBed", (0.36, 0.02, 0.045), (-0.36, FY_T, -0.07), M["orangeGlow"], tw)
box("TowBoom", (0.26, 0.02, 0.028), (-0.33, FY_T, 0.02), M["orangeGlow"], tw, rot=(0, -0.6, 0))
box("TowCable", (0.01, 0.02, 0.11), (-0.222, FY_T, 0.04), M["orangeGlow"], tw)
box("TowHook", (0.04, 0.02, 0.018), (-0.215, FY_T, -0.015), M["orangeGlow"], tw)
for i, x in enumerate((-0.6, -0.29)):
    cyl(f"TowWheel{i}", 0.048, 0.02, (x, FY_T, -0.115), M["orangeGlow"], tw, axis="Y", verts=20)
    cyl(f"TowHub{i}", 0.018, 0.02, (x, FY_T - 0.006, -0.115), M["beam"], tw, axis="Y", verts=12)
text3d("TowText", "ODŤAH", 0.22, (0.27, -0.05, -0.03), M["white"], tw, extrude=0.015)
text3d("TowSub", "ZAVOLAJTE NÁM", 0.075, (0.27, -0.05, -0.19), M["orange"], tw, extrude=0.008)
for i, x in enumerate((-0.6, 0.6)):                   # reťaze do stropu
    cyl(f"TowChain{i}", 0.006, 0.69, (x, 0, 0.655), M["chrome"], tw, verts=6)
tw.location = TOW_LOC; tw.rotation_euler = (0, 0, TOW_YAW)
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
CAR_LEN = 4.69                                  # Škoda Octavia IV RS
def glass_mat(name, color, alpha, rough=0.04, emit=None, emit_strength=0.0):
    m = mat(name, color, 0.0, rough, emit=emit, emit_strength=emit_strength)
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Alpha"].default_value = alpha
    for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
        try: setattr(m, attr, val)
        except Exception: pass
    return m

CM = {
    "glass": glass_mat("CarGlass", (0.015, 0.02, 0.025), 0.42),
    "lens": glass_mat("HeadlightGlass", (0.8, 0.82, 0.85), 0.14, 0.02),
    "tail": glass_mat("TaillightGlass", (0.06, 0.002, 0.002), 0.9, 0.03),                                  # tmavé (dymové) zadné sklo
    "tailLed": mat("TailLed", (0.10, 0.004, 0.003), 0.0, 0.3, emit=(0.5, 0.01, 0.004), emit_strength=0.2),
    "led": mat("HeadLed", (0.95, 0.96, 1.0), 0.0, 0.2, emit=(0.9, 0.95, 1.0), emit_strength=1.2),
    "amber": mat("SignalAmber", (0.9, 0.45, 0.02), 0.0, 0.3),
    "chrome": mat("CarChrome", (0.85, 0.85, 0.88), 1.0, 0.08),
    "mirror": mat("MirrorChrome", (0.9, 0.9, 0.92), 1.0, 0.02),
    "gloss": mat("BlackGloss", (0.012, 0.012, 0.014), 0.2, 0.12, coat=1.0),
    "matte": mat("BlackMatte", (0.02, 0.02, 0.022), 0.0, 0.7),
    "frit": mat("GlassFrit", (0.005, 0.005, 0.006), 0.0, 0.3),
    "rim": mat("RimAlloy", (0.55, 0.56, 0.58), 1.0, 0.25),
    "caliper": mat("BrakeCaliper", (0.12, 0.12, 0.13), 0.6, 0.4),
    "disc": mat("BrakeDisc", (0.35, 0.35, 0.36), 1.0, 0.45),
    "int": mat("InteriorDark", (0.025, 0.025, 0.027), 0.0, 0.65),
    "seat": mat("SeatFabric", (0.04, 0.04, 0.045), 0.0, 0.9),
    "intChrome": mat("InteriorChrome", (0.6, 0.6, 0.62), 1.0, 0.25),
}
# poradie je dôležité – prvé zhodné pravidlo vyhráva (kľúče = podreťazce názvu objektu, malé písmená)
CAR_RULES = [
    (("logos_badges", "logos_black", "rim_badge", "vrs_logo", "front vrs_sub2", "red_icom", "spz_zaslepka"), None),       # logá Škoda/vRS → preč
    (("ext_tyre",), "tire"), (("brakedisk",), "disc"), (("rim_metal", "bbs_metal"), "caliper"), (("rim_oz",), "rim"),
    (("plate",), "plate"),
    (("windshield",), "frit"), (("glass_mirrors", "type_r_tran"), "mirror"),
    (("taillight_glass", "glass_reflex"), "tail"),
    (("red light", "r_lights", "rt_ch", "rtl_sl"), "tailLed"),
    (("hlglass", "hlsx", "glass_f_fog", "glass_front_bulbs", "hl_glass"), "lens"),
    (("desirefx", "lights_fog", "hl_signal"), "led"), (("mirror_signal",), "amber"),
    (("ext_glass", "roof_light_glass"), "glass"),
    (("ext_body", "body_paint", "carpaint", "boot_paint", "sensors"), "body"),
    (("chrome",), "chrome"),
    (("ext_plastic_lesk", "ext_pl_lesk", "logos_black", "ext_plastic", "frmask", "lpframe"), "gloss"),
    (("matte_black", "black", "rubber", "grill", "fbg", "plastick", "105ee", "#28r", "#40e"), "matte"),
    (("seat", "recaro", "carpet"), "seat"),
]
def car_material(name):
    n = name.lower()
    if n.startswith(("int", "rs4_int", "rs_gau", "sym_", "sw_", "sw ", "dash", "vw_golfgti_06", "polysurface_int", "interior")) or "dasboard" in n or "gauges" in n or "octavia_icon" in n or "int_" in n:
        return CM["intChrome"] if "chrome slot" in n else CM["seat"] if ("seat" in n or "recaro" in n) else CM["int"]
    for keys, key in CAR_RULES:
        if any(k in n for k in keys):
            return "DELETE" if key is None else CM.get(key) or M[key]
    return CM["matte"]

def decimate_ratio(name, mat_, tris):
    if tris < 900: return 1.0
    if mat_ in (CM["int"], CM["seat"], CM["intChrome"]): r = 0.05
    elif mat_ is M["body"]: r = 0.32
    elif mat_ in (CM["glass"], CM["frit"]): r = 0.35
    elif mat_ is CM["rim"]: r = 0.22
    elif mat_ is M["tire"]: r = 1.0
    elif mat_ in (CM["gloss"], CM["matte"]): r = 0.35        # lišty okien – pri silnom zjednodušení robia ostne
    else: r = 0.12
    return max(r, 300 / tris)

def import_car():
    """Škoda Octavia (MK4) RS by DR1KING100K (Sketchfab, CC BY 4.0) – prefarbené na červenú metalízu, bez log, zjednodušené pre web."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SRC_CAR)
    new = [o for o in bpy.data.objects if o not in before]
    stats = {}
    for o in list(new):
        if o.type != "MESH":
            continue
        m = car_material(o.name)
        if m == "DELETE":
            new.remove(o); bpy.data.objects.remove(o, do_unlink=True); continue
        o.data.materials.clear(); o.data.materials.append(m)
        for p in o.data.polygons: p.material_index = 0
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        r = decimate_ratio(o.name, m, tris)
        if r < 1.0:
            d = o.modifiers.new("dec", "DECIMATE"); d.ratio = r; d.use_collapse_triangulate = True
        stats[m.name] = stats.get(m.name, 0) + int(tris * r)
    print("CAR_TRIS", sum(stats.values()), sorted(stats.items(), key=lambda kv: -kv[1]))
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
    holder.rotation_euler = (0, 0, 0)              # model má nos už v -y (k vrátam)
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
    if "windscreen" in o.name.lower() or "windshield" in o.name.lower():
        a = np.array([inv @ o.matrix_world @ Vector(v) for v in o.bound_box]); _ws.append((a.min(0) + a.max(0)) / 2)
ws_c = min(_ws, key=lambda c: c[1]) if _ws else np.array([0, -0.5, 1.05])     # predné (nie zadné) sklo
hood_y = ymin + (ws_c[1] - ymin) * 0.40
# výfuk: najnižšie zadné body vpravo od stredu
rear = P[(P[:, 1] > ymax - 0.18) & (P[:, 2] < 0.45) & (P[:, 0] > 0.25) & (P[:, 0] < 0.75)]
ex = rear.mean(0) if len(rear) else np.array([0.45, ymax, 0.3])
ANCH = {
    "klima": (0.0, ymin + 0.02, 0.36),                       # kondenzátor za predným nárazníkom
    "motor": (-0.38, hood_y, top_z(hood_y, -0.38) + 0.06),        # kapota, ľavá strana (neprekrýva sa so sklom)            # kapota
    "sklo": (0.32, ws_c[1] + 0.12, ws_c[2] + 0.22),              # čelné sklo
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
        if o.data.users > 1:
            o.data = o.data.copy()
        for m in list(o.modifiers):
            try:
                bpy.ops.object.modifier_apply(modifier=m.name)
            except Exception as e:
                print("MODIFIER_FAIL", o.name, m.name, e)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "tools", "garage.blend"))
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_apply=True, export_yup=True,
                          export_cameras=False, export_lights=False, export_image_format="WEBP",
                          export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
                          export_draco_position_quantization=14, export_draco_normal_quantization=10,
                          export_draco_texcoord_quantization=12)
print("EXPORTED", OUT, os.path.getsize(OUT))
