# Obrázok na zdieľanie (assets/og-image.jpg, 1200×630) a ikona pre iPhone (assets/apple-touch-icon.png, 180×180)
# Spustenie: blender -b --factory-startup --python tools/render_og.py [-- --icon-only | --reuse-bg]
# 1) render garáže s autom presne z uhla, kde sa zastaví úvodná jazda (pohľad "wide"), 2) poskladanie textov v ortografickej scéne (Cycles, emisné materiály).
import bpy, math, os, re, json, sys, tempfile
from mathutils import Vector as V

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
F_HEAD = os.path.join(FONTS, "ARIALNB.TTF")     # Arial Narrow Bold – najbližšie k Barlow Condensed
F_BLACK = os.path.join(FONTS, "ariblk.ttf")     # Arial Black – logo PLS
F_TEXT = os.path.join(FONTS, "segoeuib.ttf")    # Segoe UI Bold – menšie texty
ORANGE = (1.0, 0.102, 0.013)                    # #ff5a1f v lineárnych farbách
DARK = (0.0060, 0.0060, 0.0060)                 # #121212
TMP = os.path.join(tempfile.gettempdir(), "pls_og_bg.png")
icon_only = "--icon-only" in sys.argv

# ---------- 1) pozadie: garáž (-- --reuse-bg = použiť už vyrenderované pozadie) ----------
if not icon_only and not ("--reuse-bg" in sys.argv and os.path.exists(TMP)):
    views_src = open(os.path.join(ROOT, "js", "views.js"), encoding="utf-8").read()
    v = json.loads(re.search(r"= /\*JSON\*/(.*?)/\*END\*/", views_src, re.S).group(1))["wide"]
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "tools", "garage.blend"))
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.samples = 96; sc.cycles.device = "CPU"; sc.cycles.use_denoising = True
    sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = False; sc.world.color = (0.045, 0.05, 0.06)
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    for o in bpy.data.objects:
        if o.name.startswith(("DoorPanel", "DoorRib", "DoorStripe", "DoorBacking")): o.hide_render = True
    for x, y in ((-1.6, 1.3), (1.6, 1.3), (-1.6, -1.3), (1.6, -1.3)):
        bpy.ops.object.light_add(type="AREA", location=(x, y, 3.1)); bpy.context.object.data.energy = 220; bpy.context.object.data.size = 2.4
    bpy.ops.object.light_add(type="SPOT", location=(0.4, -0.6, 3.1)); L = bpy.context.object
    L.data.energy = 900; L.data.spot_size = 1.7; L.data.spot_blend = 0.6
    b3 = lambda p: V((p[0], -p[2], p[1]))
    bpy.data.objects["Car"].rotation_euler = (0, 0, v["yaw"])
    loc, tgt = b3(v["pos"]), b3(v["tgt"])
    bpy.ops.object.camera_add(location=loc); cam = bpy.context.object
    cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "HORIZONTAL"; cam.data.angle = math.radians(v["hfov"]); cam.data.clip_start = 0.15   # rovnaký záber ako 3D
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1200, 630, 100
    sc.render.image_settings.file_format = "PNG"; sc.render.filepath = TMP
    bpy.ops.render.render(write_still=True)

# ---------- 2) skladanie ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.device = "CPU"; sc.cycles.use_denoising = False
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
sc.render.film_transparent = False
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = False; sc.world.color = (0, 0, 0)

def emis(name, color=(1, 1, 1), alpha=1.0, image=None, ramp=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
    em.inputs["Color"].default_value = (*color, 1)
    if image:
        tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(image)
        tx.image.colorspace_settings.name = "sRGB"
        nt.links.new(tx.outputs["Color"], em.inputs["Color"])
    if ramp is None and alpha >= 1:
        nt.links.new(em.outputs[0], out.inputs[0]); return m
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
    if ramp:                                      # priehľadnosť podľa X: [(pozícia, krytie), ...]
        tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        cr = nt.nodes.new("ShaderNodeValToRGB"); el = cr.color_ramp.elements
        el[0].position, el[0].color = ramp[0][0], (ramp[0][1],) * 3 + (1,)
        el[1].position, el[1].color = ramp[-1][0], (ramp[-1][1],) * 3 + (1,)
        for p, a in ramp[1:-1]: e = el.new(p); e.color = (a,) * 3 + (1,)
        nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs[ramp_axis[0]], cr.inputs[0])
        nt.links.new(cr.outputs["Color"], mx.inputs[0])
    else:
        mx.inputs[0].default_value = alpha
    return m
ramp_axis = ["X"]

def rect(name, x, y, w, h, z, mat):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x + w / 2, y + h / 2, z)); o = bpy.context.object
    o.scale = (w, h, 1); o.name = name; o.data.materials.append(mat); return o

fonts = {}
def text(body, font, size, x, y, z=0.1, color=(1, 1, 1), align="LEFT", spacing=1.0, valign="BOTTOM_BASELINE"):
    if font not in fonts: fonts[font] = bpy.data.fonts.load(font)
    cu = bpy.data.curves.new("T", "FONT"); cu.body = body; cu.font = fonts[font]; cu.size = size
    cu.align_x = align; cu.align_y = valign; cu.space_character = spacing
    o = bpy.data.objects.new("T", cu); o.location = (x, y, z); sc.collection.objects.link(o)
    o.data.materials.append(emis("txt", color)); return o

def camera(w, h):
    cd = bpy.data.cameras.new("C"); cd.type = "ORTHO"; cd.ortho_scale = max(w, h)
    c = bpy.data.objects.new("C", cd); c.location = (0, 0, 10); sc.collection.objects.link(c); sc.camera = c

def clear():
    for o in list(sc.collection.objects): bpy.data.objects.remove(o)

if not icon_only:
    W, H = 12.0, 6.3                              # 1 jednotka = 100 px
    camera(W, H)
    sc.render.resolution_x, sc.render.resolution_y = 1200, 630
    rect("bg", -W / 2, -H / 2, W, H, 0, emis("bg", image=TMP))
    # auto ostáva v strede bez zakrytia; texty iba v ľavom hornom a ľavom dolnom rohu (firma nemá logo → bez štvorca)
    rect("shade", -W / 2, -H / 2, W, H, 0.02, emis("shade", DARK, ramp=[(0.0, 0.8), (0.26, 0.45), (0.42, 0.0)]))
    ramp_axis[0] = "Y"
    rect("shadeT", -W / 2, -H / 2, W, H, 0.03, emis("shadeT", DARK, ramp=[(0.62, 0.0), (1.0, 0.75)]))
    rect("shadeB", -W / 2, -H / 2, W, H, 0.04, emis("shadeB", DARK, ramp=[(0.0, 0.7), (0.2, 0.0)]))
    L = -5.5
    text("PLS GROUP", F_HEAD, 0.95, L - 0.03, 2.2)
    rect("bar", L, 1.9, 1.0, 0.08, 0.05, emis("o2", ORANGE))
    text("AUTOSERVIS · BRATISLAVA – VRAKUŇA", F_HEAD, 0.3, L, 1.42, color=ORANGE, spacing=1.08)
    # tlačidlo s telefónom
    rect("btn", L, -2.85, 3.0, 0.66, 0.05, emis("o3", ORANGE))
    text("Tel. 0902 121 221", F_HEAD, 0.38, L + 1.5, -2.52, color=DARK, align="CENTER", valign="CENTER", spacing=1.04)
    sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 86
    sc.render.filepath = os.path.join(ROOT, "assets", "og-image.jpg")
    bpy.ops.render.render(write_still=True)
    clear()

# ---------- 3) ikona pre iPhone ----------
camera(1.8, 1.8)
sc.render.resolution_x = sc.render.resolution_y = 180
rect("ibg", -0.9, -0.9, 1.8, 1.8, 0, emis("io", ORANGE))
text("PLS", F_BLACK, 0.76, 0, 0.0, align="CENTER", valign="CENTER")
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGB"
sc.render.filepath = os.path.join(ROOT, "assets", "apple-touch-icon.png")
bpy.ops.render.render(write_still=True)
print("OG HOTOVO")
