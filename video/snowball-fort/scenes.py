"""Blender (bpy) scene builder for the snowball-fort short.

Usage:  python3 scenes.py <shot> <out_dir> [still|anim] [samples]
Builds the shot from scratch with primitives (stylised 3D kids, studio stage,
props, snowy backyard) and renders a PNG still or a PNG sequence.
"""
import bpy, bmesh, math, sys, random
from mathutils import Vector

SHOT = sys.argv[1]; OUT = sys.argv[2]
MODE = sys.argv[3] if len(sys.argv) > 3 else "still"
SAMPLES = int(sys.argv[4]) if len(sys.argv) > 4 else 32
FRAMES = {"s01": 88, "s02": 86, "s03": 77, "s04": 102, "s05": 54, "s06": 87, "s07": 97,
          "s08": 118, "s09": 42, "s10": 124, "s11": 47, "s12": 46, "s13": 56, "s14": 26, "s15": 65}
NF = FRAMES[SHOT]
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2
sc.cycles.transmission_bounces = 4; sc.cycles.volume_bounces = 0
sc.render.resolution_x = 720; sc.render.resolution_y = 1280
sc.render.fps = 30
sc.frame_start = 1; sc.frame_end = NF
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "Medium High Contrast"
sc.render.use_persistent_data = True
sc.cycles.adaptive_threshold = 0.05
RES = float(sys.argv[5]) if len(sys.argv) > 5 else 0.75
sc.render.resolution_percentage = int(RES * 100)
sc.render.film_transparent = False

# ---------------------------------------------------------------- materials
_mats = {}
def mat(name, col, rough=0.5, sss=0.0, metal=0.0, trans=0.0, emit=0.0, spec=0.5, coat=0.0):
    if name in _mats: return _mats[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*col, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Transmission Weight"].default_value = trans
    p.inputs["Coat Weight"].default_value = coat
    if sss:
        p.inputs["Subsurface Weight"].default_value = sss
        p.inputs["Subsurface Radius"].default_value = (0.3, 0.15, 0.08)
        p.inputs["Subsurface Scale"].default_value = 0.05
    if emit:
        p.inputs["Emission Color"].default_value = (*col, 1)
        p.inputs["Emission Strength"].default_value = emit
    _mats[name] = m; return m

def snow_mat():
    if "snow" in _mats: return _mats["snow"]
    m = mat("snow", (0.86, 0.9, 0.96), rough=0.55, sss=0.35)
    nt = m.node_tree; p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 18; nz.inputs["Detail"].default_value = 8
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], p.inputs["Normal"])
    p.inputs["Subsurface Radius"].default_value = (0.6, 0.7, 0.9)
    return m

SKIN = mat("skin", (0.8, 0.5, 0.36), rough=0.45, sss=0.25)
DARK = mat("dark", (0.01, 0.01, 0.012), rough=0.15, spec=0.8)
WHITE = mat("white", (0.95, 0.95, 0.95), rough=0.3)
JEANS = mat("jeans", (0.08, 0.14, 0.32), rough=0.8)
SHOE = mat("shoe", (0.92, 0.92, 0.94), rough=0.5)
SOLE = mat("sole", (0.2, 0.2, 0.22), rough=0.6)
LIP = mat("lip", (0.35, 0.08, 0.07), rough=0.4)

# ---------------------------------------------------------------- helpers
def link(o):
    bpy.context.collection.objects.link(o) if o.name not in bpy.context.collection.objects else None
    return o

def finish(o, m=None, sub=2, smooth=True, parent=None, bevel=0):
    if m: o.data.materials.append(m)
    if bevel:
        b = o.modifiers.new("bv", "BEVEL"); b.width = bevel; b.segments = 3
    if sub:
        s = o.modifiers.new("ss", "SUBSURF"); s.levels = sub; s.render_levels = sub
    if smooth:
        for poly in o.data.polygons: poly.use_smooth = True
    if parent: o.parent = parent
    return o

def sphere(loc, r, m=None, scale=(1, 1, 1), parent=None, sub=1, seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc)
    o = bpy.context.object; o.scale = scale
    return finish(o, m, sub, parent=parent)

def cyl(loc, r, depth, m=None, rot=(0, 0, 0), scale=(1, 1, 1), parent=None, sub=0, verts=32, bevel=0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = scale
    return finish(o, m, sub, parent=parent, bevel=bevel)

def box(loc, size, m=None, rot=(0, 0, 0), parent=None, bevel=0.0, sub=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, m, sub, parent=parent, bevel=bevel)

def empty(name, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None); link(e)
    e.parent = parent; e.location = loc; e.rotation_euler = rot
    return e

def capsule(a, b, r, m, parent=None):
    """cylinder with rounded ends between local points a,b (in parent space)"""
    a = Vector(a); b = Vector(b); d = b - a; L = d.length
    e = empty("cap", loc=a, parent=parent)
    e.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    cyl((0, 0, L / 2), r, L, m, parent=e, verts=24)
    sphere((0, 0, 0), r, m, parent=e); sphere((0, 0, L), r, m, parent=e)
    return e

def curve_line(pts, r, m, name="cord", parent=None):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = r; cu.bevel_resolution = 4; cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts): p.co = (*c, 1)
    o = bpy.data.objects.new(name, cu); link(o); o.data.materials.append(m); o.parent = parent
    return o, sp

def key(o, f, loc=None, rot=None, scl=None):
    if loc is not None: o.location = loc; o.keyframe_insert("location", frame=f)
    if rot is not None: o.rotation_euler = rot; o.keyframe_insert("rotation_euler", frame=f)
    if scl is not None: o.scale = scl; o.keyframe_insert("scale", frame=f)

def r(deg): return math.radians(deg)

# ---------------------------------------------------------------- characters
def kid(name, hoodie, hair=(0.09, 0.05, 0.03), loc=(0, 0, 0), rot_z=0.0, pose=None, smile=1.0, lid=0.0, look=(0, 0)):
    """Stylised ~1.45 m kid. Faces -Y. pose: dict of shoulder/elbow eulers in degrees."""
    pose = pose or {}
    HO = mat("hood_" + name, hoodie, rough=0.85, sss=0.05)
    HA = mat("hair_" + name, hair, rough=0.55)
    root = empty(name, loc=loc, rot=(0, 0, rot_z))
    # legs + shoes
    for s in (-1, 1):
        capsule((s * 0.095, 0, 0.12), (s * 0.095, 0, 0.62), 0.078, JEANS, root)
        box((s * 0.1, -0.05, 0.05), (0.13, 0.27, 0.1), SHOE, parent=root, bevel=0.035)
        box((s * 0.1, -0.05, 0.008), (0.135, 0.275, 0.02), SOLE, parent=root, bevel=0.008)
    # torso hoodie
    sphere((0, 0, 0.84), 1.0, HO, scale=(0.215, 0.15, 0.3), parent=root, sub=2)
    cyl((0, 0, 0.6), 0.2, 0.08, HO, scale=(1, 0.72, 1), parent=root, sub=1)
    box((0, -0.135, 0.72), (0.2, 0.04, 0.13), HO, parent=root, bevel=0.02)  # pocket
    bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.045, location=(0, 0.04, 1.06), rotation=(r(-20), 0, 0))
    finish(bpy.context.object, HO, 1, parent=root)
    for s in (-1, 1):  # drawstrings
        cyl((s * 0.04, -0.15, 0.98), 0.007, 0.14, WHITE, parent=root)
    cyl((0, 0, 1.1), 0.06, 0.1, SKIN, parent=root)
    # head
    head = empty(name + "_head", loc=(0, 0, 1.3), rot=(r(look[1]), 0, r(look[0])), parent=root)
    sphere((0, 0, 0), 0.205, SKIN, scale=(1, 0.95, 1.06), parent=head, sub=2)
    sphere((0, -0.06, -0.1), 0.15, SKIN, scale=(1, 0.95, 0.8), parent=head, sub=2)  # cheeks/jaw
    for s in (-1, 1):
        sphere((s * 0.2, 0.0, 0.0), 0.05, SKIN, scale=(0.5, 1, 1.2), parent=head)
        # eyes
        sphere((s * 0.075, -0.168, 0.025), 0.045, WHITE, parent=head, scale=(1, 0.6, 1.15))
        sphere((s * 0.075, -0.19, 0.02), 0.028, DARK, parent=head, scale=(1, 0.5, 1.1))
        sphere((s * 0.07, -0.205, 0.035), 0.007, mat("hl", (1, 1, 1), emit=3), parent=head, sub=0)
        if lid > 0:
            lidz = 0.07 - 0.06 * lid
            sphere((s * 0.075, -0.17, lidz), 0.05, SKIN, parent=head, scale=(1.05, 0.65, 0.5 + 0.4 * lid))
        # brows
        cyl((s * 0.08, -0.185, 0.1), 0.012, 0.075, HA, rot=(0, r(90), r(s * -8)), parent=head, sub=1)
    sphere((0, -0.205, -0.03), 0.026, SKIN, parent=head, scale=(1, 1.1, 0.9))  # nose
    # mouth arc
    pts = []
    for i in range(7):
        a = r(-50 + i * 100 / 6)
        pts.append((math.sin(a) * 0.07, -0.207 + 0.03 * abs(math.sin(a)), -0.095 + smile * (0.03 - math.cos(a) * 0.03) + (1 - smile) * 0.0))
    curve_line(pts, 0.011, LIP, parent=head)
    # hair cap
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.222, location=(0, 0.012, 0.03))
    hc = bpy.context.object; bm = bmesh.new(); bm.from_mesh(hc.data)
    kill = [v for v in bm.verts if v.co.z < (0.07 if v.co.y < -0.1 else (-0.02 if abs(v.co.x) > 0.17 else -0.12)) + max(0, -v.co.y) * 0.25]
    bmesh.ops.delete(bm, geom=kill, context="VERTS"); bm.to_mesh(hc.data); bm.free()
    hc.scale = (1.03, 1.05, 0.98)
    sol = hc.modifiers.new("so", "SOLIDIFY"); sol.thickness = 0.03
    finish(hc, HA, 2, parent=head)
    for i in range(7):  # tufts
        a = r(-60 + i * 20)
        o = sphere((math.sin(a) * 0.14, -0.12 - 0.04 * math.cos(a), 0.15 - 0.02 * abs(i - 3)), 0.07, HA,
                   scale=(0.8, 1.2, 0.55), parent=head)
        o.rotation_euler = (r(-30), 0, a * 0.4)
    # arms
    arms = {}
    for s, side in ((-1, "R"), (1, "L")):
        sh = empty(name + "_sh" + side, loc=(s * 0.215, 0, 1.0), parent=root)
        pr = pose.get("sh" + side, (0, s * 8, 0)); sh.rotation_euler = tuple(r(x) for x in pr)
        capsule((0, 0, 0), (0, 0, -0.27), 0.068, HO, sh)
        el = empty(name + "_el" + side, loc=(0, 0, -0.27), parent=sh)
        pe = pose.get("el" + side, (0, 0, 0)); el.rotation_euler = tuple(r(x) for x in pe)
        capsule((0, 0, 0), (0, 0, -0.2), 0.06, HO, el)
        cyl((0, 0, -0.21), 0.062, 0.04, HO, parent=el)
        sphere((0, 0, -0.27), 0.055, SKIN, parent=el, scale=(0.8, 1, 1.1))
        sphere((0, -0.035, -0.25), 0.022, SKIN, parent=el)  # thumb
        arms[side] = (sh, el)
    return root, arms

# ---------------------------------------------------------------- environments
def studio():
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (-0.5, -0.66, 0); mp.inputs["Scale"].default_value = (1.0, 0.75, 1)
    gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"
    cr = nt.nodes.new("ShaderNodeValToRGB"); el = cr.color_ramp.elements
    el[0].position = 0.0; el[0].color = (0.0, 0.08, 0.16, 1)
    el[1].position = 0.8; el[1].color = (0.45, 0.78, 0.92, 1)
    e2 = el.new(0.45); e2.color = (0.0, 0.3, 0.55, 1)
    nt.links.new(tc.outputs["Window"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], gr.inputs["Vector"])
    nt.links.new(gr.outputs["Fac"], cr.inputs["Fac"])
    lp = nt.nodes.new("ShaderNodeLightPath"); mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.inputs[1].default_value = (0.18, 0.35, 0.48, 1)
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0]); nt.links.new(cr.outputs["Color"], mix.inputs[2])
    nt.links.new(mix.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 1.0
    # floor fading into the backdrop
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); fl = bpy.context.object
    m = bpy.data.materials.new("floor"); m.use_nodes = True; n = m.node_tree
    p = n.nodes["Principled BSDF"]; p.inputs["Base Color"].default_value = (0.02, 0.12, 0.2, 1)
    p.inputs["Roughness"].default_value = 0.55
    tr = n.nodes.new("ShaderNodeBsdfTransparent"); mx = n.nodes.new("ShaderNodeMixShader")
    tcc = n.nodes.new("ShaderNodeTexCoord"); vm = n.nodes.new("ShaderNodeVectorMath"); vm.operation = "LENGTH"
    mr = n.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 5; mr.inputs["From Max"].default_value = 14
    n.links.new(tcc.outputs["Object"], vm.inputs[0]); n.links.new(vm.outputs["Value"], mr.inputs["Value"])
    n.links.new(mr.outputs["Result"], mx.inputs[0]); n.links.new(p.outputs[0], mx.inputs[1]); n.links.new(tr.outputs[0], mx.inputs[2])
    n.links.new(mx.outputs[0], n.nodes["Material Output"].inputs["Surface"])
    fl.data.materials.append(m)
    light("key", (-3, -4, 5), 650, 4, (1, 0.95, 0.88))
    light("fill", (4, -3, 2.5), 160, 5, (0.8, 0.92, 1))
    light("rim", (1, 4, 4), 700, 3, (0.7, 0.95, 1))

def light(name, loc, energy, size, col):
    ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy; ld.size = size; ld.color = col
    o = bpy.data.objects.new(name, ld); link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 0.8)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o

def backyard():
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; nt = w.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    cr = nt.nodes.new("ShaderNodeValToRGB"); el = cr.color_ramp.elements
    el[0].position = 0.0; el[0].color = (0.85, 0.8, 0.85, 1); el[1].position = 0.35; el[1].color = (0.25, 0.48, 0.85, 1)
    nt.links.new(sky.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.9
    sd = bpy.data.lights.new("sun", "SUN"); sd.energy = 4.0; sd.angle = r(4); sd.color = (1, 0.88, 0.72)
    so = bpy.data.objects.new("sun", sd); link(so); so.rotation_euler = (r(62), r(8), r(-35))
    # ground with gentle drifts
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=120, y_subdivisions=120, size=70); g = bpy.context.object
    for v in g.data.vertices:
        x, y = v.co.x, v.co.y
        if abs(x) > 3.5 or abs(y) > 3.5:
            v.co.z = 0.12 * math.sin(x * 0.6) * math.cos(y * 0.5) + 0.08 * math.sin(x * 1.7 + y)
    finish(g, snow_mat(), 1)
    # fence
    WOOD = mat("wood", (0.33, 0.2, 0.11), rough=0.8)
    for i in range(-14, 15):
        box((i * 0.32, 7.5, 0.75), (0.26, 0.05, 1.5), WOOD, bevel=0.01)
        box((i * 0.32, 7.47, 1.52), (0.27, 0.07, 0.06), snow_mat(), bevel=0.02)
    box((0, 7.44, 1.2), (9.5, 0.04, 0.1), WOOD)
    box((0, 7.44, 0.4), (9.5, 0.04, 0.1), WOOD)
    # house siding on right
    SID = mat("siding", (0.18, 0.32, 0.38), rough=0.7)
    for k in range(18):
        box((7.5, 2.5, 0.12 + k * 0.17), (0.08, 9, 0.16), SID, rot=(r(4), 0, 0), bevel=0.005)
    # pine trees
    PINE = mat("pine", (0.03, 0.12, 0.06), rough=0.8)
    for (x, y, s) in ((-4.2, 5.5, 1.3), (-2.6, 9.5, 1.6), (3.2, 10, 1.5), (-6, 2.5, 1.1), (5.2, 6.5, 1.2)):
        cyl((x, y, 0.3 * s), 0.1 * s, 0.6 * s, mat("bark", (0.2, 0.12, 0.07)))
        for k in range(4):
            z = (0.5 + k * 0.55) * s; rr = (1.1 - k * 0.24) * s
            bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=rr, depth=0.9 * s, location=(x, y, z)); finish(bpy.context.object, PINE, 0)
            bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=rr * 0.75, depth=0.5 * s, location=(x, y, z + 0.22 * s)); finish(bpy.context.object, snow_mat(), 0)
    # snowy bush
    for k in range(5):
        sphere((-2.2 + k * 0.25, 0.8 + 0.1 * math.sin(k), 0.3), 0.35, mat("bush", (0.05, 0.15, 0.06), rough=0.9), scale=(1, 1, 0.8))
        sphere((-2.2 + k * 0.25, 0.8 + 0.1 * math.sin(k), 0.48), 0.28, snow_mat(), scale=(1, 1, 0.5))

# ---------------------------------------------------------------- props
BIN_M = None
def storage_bin(loc=(0, 0, 0), parent=None, rot=(0, 0, 0), snow=0.0):
    global BIN_M
    BIN_M = BIN_M or mat("bin", (0.15, 0.45, 0.95), rough=0.25, trans=0.55, coat=0.3)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0)); o = bpy.context.object
    o.scale = (0.56, 0.4, 0.32); bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new(); bm.from_mesh(o.data)
    top = [f for f in bm.faces if f.normal.z > 0.9]; bmesh.ops.delete(bm, geom=top, context="FACES")
    for v in bm.verts:   # taper
        if v.co.z < 0: v.co.x *= 0.9; v.co.y *= 0.88
    bm.to_mesh(o.data); bm.free()
    s = o.modifiers.new("so", "SOLIDIFY"); s.thickness = 0.012
    finish(o, BIN_M, 0, bevel=0.01); o.parent = parent; o.location = loc; o.rotation_euler = rot
    bpy.ops.mesh.primitive_cube_add(size=1); rim = bpy.context.object
    rim.scale = (0.6, 0.44, 0.03); bpy.ops.object.transform_apply(scale=True)
    bm = bmesh.new(); bm.from_mesh(rim.data); bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.z) > 0.9], context="FACES")
    bm.to_mesh(rim.data); bm.free(); rim.modifiers.new("so", "SOLIDIFY").thickness = 0.02
    finish(rim, BIN_M, 0, bevel=0.005); rim.parent = o; rim.location = (0, 0, 0.15)
    if snow > 0:
        h = 0.3 * snow
        box((0, 0, -0.155 + h / 2), (0.5, 0.345, h), snow_mat(), parent=o, bevel=0.03)
        if snow >= 1: sphere((0, 0, 0.15), 0.2, snow_mat(), scale=(1.3, 0.85, 0.35), parent=o)
    return o

def brick(loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    o = box(loc, (0.52, 0.36, 0.3), snow_mat(), rot=rot, parent=parent, bevel=0.035)
    return o

def fort_layout(rings=4, n=12, R=1.05, window=True):
    out = []
    for ri in range(rings):
        for i in range(n):
            a = r(-90) + (i + 0.5 * (ri % 2)) * 2 * math.pi / n
            if window and ri == 2 and i == 0: continue
            out.append(((R * math.cos(a), R * math.sin(a), 0.15 + ri * 0.3), (0, 0, a + r(90)), ri, i))
    return out

def fort(loc=(0, 0, 0), rings=4, parent=None):
    root = empty("fort", loc=loc, parent=parent)
    for p, rt, ri, i in fort_layout(rings): brick(p, rt, root)
    sphere((0, 0, 0.02), 0.95, snow_mat(), scale=(1, 1, 0.04), parent=root)
    return root

def noodle_half(length=1.3, color=(1.0, 0.22, 0.02), side=1, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.06, depth=length, end_fill_type="NOTHING")
    o = bpy.context.object; bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x * side < -0.001], context="VERTS")
    bm.to_mesh(o.data); bm.free()
    sol = o.modifiers.new("so", "SOLIDIFY"); sol.thickness = 0.03
    finish(o, mat("noodle%d" % side, color, rough=0.6, sss=0.1), 1)
    o.parent = parent; o.location = loc; o.rotation_euler = rot
    return o

def snowball(loc, rad=0.075, parent=None):
    return sphere(loc, rad, snow_mat(), parent=parent, sub=1, seg=16)

def periscope(loc=(0, 0, 0), parent=None):
    P = mat("pvc", (0.95, 0.75, 0.05), rough=0.35, coat=0.4)
    root = empty("peri", loc=loc, parent=parent)
    cyl((0, 0, 0.45), 0.055, 0.9, P, parent=root, bevel=0.005)
    sphere((0, 0, 0.92), 0.068, P, parent=root)
    cyl((0, -0.1, 0.92), 0.058, 0.2, P, rot=(r(90), 0, 0), parent=root)
    cyl((0, -0.2, 0.92), 0.068, 0.03, P, rot=(r(90), 0, 0), parent=root)
    cyl((0, -0.212, 0.92), 0.05, 0.01, mat("lens", (0.05, 0.12, 0.18), rough=0.02, metal=0.6), rot=(r(90), 0, 0), parent=root)
    return root

def tape(loc, rot, parent=None):
    return box(loc, (0.05, 0.2, 0.006), mat("tape", (0.55, 0.57, 0.6), rough=0.4, metal=0.3), rot=rot, parent=parent)

# ---------------------------------------------------------------- camera
def camera(loc, target, lens=40, fstop=2.8, ttarget=None):
    cd = bpy.data.cameras.new("cam"); cd.lens = lens; cd.sensor_width = 36
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
    c = bpy.data.objects.new("cam", cd); link(c); sc.camera = c; c.location = loc
    t = empty("tgt", loc=target)
    con = c.constraints.new("TRACK_TO"); con.target = t; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    cd.dof.focus_object = t
    return c, t

def orbit(c, center, radius, z, a0, a1, f0=1, f1=None, steps=6):
    f1 = f1 or NF
    for k in range(steps + 1):
        u = k / steps; a = r(a0 + (a1 - a0) * u); f = f0 + (f1 - f0) * u
        key(c, f, loc=(center[0] + radius * math.sin(a), center[1] - radius * math.cos(a), z))

def ease_all():
    for o in bpy.data.objects:
        ad = o.animation_data
        if ad and ad.action:
            for fc in getattr(ad.action, "fcurves", []) or []:
                for kp in fc.keyframe_points: kp.interpolation = "BEZIER"

def linear(o):
    ad = o.animation_data
    if ad and ad.action:
        try: fcs = ad.action.fcurves
        except AttributeError: fcs = [fc for l in ad.action.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]
        for fc in fcs:
            for kp in fc.keyframe_points: kp.interpolation = "LINEAR"

# ================================================================= SHOTS
POSE_HOLD = {"shR": (-55, 0, -20), "elR": (-50, 0, 10), "shL": (-55, 0, 20), "elL": (-50, 0, -10)}

if SHOT == "s01":   # hook: kid on stage holding a bin, snow pile beside
    studio()
    kid("boy", (0.85, 0.06, 0.05), pose=POSE_HOLD, look=(0, 5))
    storage_bin((0, -0.42, 0.78), rot=(r(-10), 0, 0))
    for k in range(9):
        snowball((0.75 + 0.12 * (k % 3), -0.2 + 0.13 * (k // 3), 0.07))
    sphere((-0.8, 0.1, 0), 0.45, snow_mat(), scale=(1.2, 1, 0.55))
    c, t = camera((0, -4.2, 1.15), (0, 0, 0.95), lens=45)
    key(c, 1, loc=(0.4, -4.4, 1.2)); key(c, NF, loc=(0.1, -3.0, 1.15))

elif SHOT == "s02":  # packing the bin full of snow
    studio()
    kid("boy", (0.85, 0.06, 0.05), loc=(0, 0.45, 0), pose={"shR": (-70, 0, -10), "elR": (-40, 0, 0), "shL": (-60, 0, 25), "elL": (-50, 0, 0)}, look=(0, 25))
    b = storage_bin((0, -0.15, 0.16))
    fill = box((0, -0.15, 0.03), (0.5, 0.345, 0.3), snow_mat(), bevel=0.03)
    key(fill, 1, loc=(0, -0.15, 0.0), scl=(1, 1, 0.1)); key(fill, int(NF * 0.85), loc=(0, -0.15, 0.155), scl=(1, 1, 1))
    mound = sphere((0, -0.15, 0.3), 0.2, snow_mat(), scale=(1.3, 0.85, 0.35))
    key(mound, int(NF * 0.6), scl=(0.01, 0.01, 0.01)); key(mound, NF, scl=(1.3, 0.85, 0.35))
    sphere((-0.75, 0.0, 0), 0.5, snow_mat(), scale=(1.2, 1, 0.6))
    c, t = camera((0, -1.8, 1.2), (0, -0.1, 0.25), lens=35)
    orbit(c, (0, -0.1), 1.7, 1.25, -35, 15)

elif SHOT == "s03":  # flip it over -> perfect snow brick
    studio()
    flip = empty("flip", loc=(0, 0, 0.16))
    b = storage_bin((0, 0, 0), parent=flip)
    brick((0, 0, 0), parent=flip)
    key(flip, 1, rot=(0, 0, 0)); key(flip, 28, rot=(r(180), 0, 0))
    key(b, 32, loc=(0, 0, 0)); key(b, 52, loc=(0, 0, -1.4))
    for k, x in enumerate((-1.2, -0.62, 0.62, 1.2)):
        brick((x, 0.35, 0.15), (0, 0, r(random.uniform(-5, 5))))
    c, t = camera((0, -2.2, 1.3), (0, 0, 0.2), lens=40)
    key(c, 1, loc=(-0.5, -2.4, 1.4)); key(c, NF, loc=(0.2, -1.5, 0.75))

elif SHOT == "s04":  # stack them into a circle with a window
    studio()
    lay = fort_layout()
    lay.sort(key=lambda x: (x[2], (x[3] + 6) % 12))
    for k, (p, rt, ri, i) in enumerate(lay):
        o = brick(p, rt); f0 = 1 + int(k * (NF * 0.72) / len(lay))
        key(o, f0, loc=(p[0], p[1], p[2] + 2.0)); o.scale = (1, 1, 1)
        key(o, f0 + 9, loc=p)
        key(o, 1, scl=(0, 0, 0)); key(o, f0 - 1, scl=(0, 0, 0)); key(o, f0, scl=(1, 1, 1))
    c, t = camera((0, -5, 3), (0, 0, 0.55), lens=38)
    orbit(c, (0, 0), 4.6, 2.6, -60, 10)

elif SHOT == "s05":  # cut a pool noodle in half
    studio()
    L = noodle_half(1.4, side=1, rot=(0, r(90), 0), loc=(0, 0, 0.35))
    R_ = noodle_half(1.4, side=-1, rot=(0, r(90), 0), loc=(0, 0, 0.35))
    # side=+1 keeps +x half -> after rot about y the open sides face up/down
    key(L, 12, loc=(0, 0, 0.35)); key(L, 40, loc=(0, -0.0, 0.47), rot=(0, r(90), 0))
    key(R_, 12, loc=(0, 0, 0.35)); key(R_, 40, loc=(0, -0.18, 0.12), rot=(r(-180), r(90), 0))
    KN = mat("knife", (0.8, 0.82, 0.85), metal=1, rough=0.15)
    kn = box((0, 0, 0.35), (1.0, 0.004, 0.09), KN, bevel=0.002)
    hd = box((0.65, 0, 0.35), (0.35, 0.03, 0.06), mat("handle", (0.05, 0.05, 0.06), rough=0.4), parent=kn, bevel=0.01)
    hd.location = (0.65, 0, 0)
    key(kn, 1, loc=(-1.0, 0, 0.35)); key(kn, 14, loc=(0.05, 0, 0.35)); key(kn, 26, loc=(1.6, 0, 0.6))
    c, t = camera((1.5, -0.9, 0.85), (0.5, 0, 0.32), lens=45, fstop=2.8)
    key(c, 1, loc=(1.7, -1.1, 0.95)); key(c, NF, loc=(1.25, -0.7, 0.7))

elif SHOT in ("s06", "s07"):  # noodle ramp taped inside wall, snowballs roll down
    studio(); fort()
    a = Vector((-0.78, 0.55, 1.18)); bpt = Vector((-0.45, -0.35, 0.22)); d = bpt - a
    rot = d.to_track_quat("Z", "Y").to_euler()
    ramp = empty("ramp", loc=(a + bpt) / 2, rot=rot)
    noodle_half(d.length, side=1, parent=ramp, rot=(0, 0, r(-120)))
    for k in (-0.35, 0, 0.35):
        tape((-0.055, 0.0, k * d.length), (0, 0, r(-30)), parent=ramp)
    kid("boy", (0.85, 0.06, 0.05), loc=(0.25, 0.05, -0.35), rot_z=r(-25),
        pose={"shL": (-60, 0, 35), "elL": (-40, 0, 0), "shR": (-20, 0, -10), "elR": (-30, 0, 0)}, look=(20, 30))
    if SHOT == "s06":
        for k, tt in enumerate((-0.35, 0, 0.35)):
            o = ramp.children[1 + k] if False else None
        c, t = camera((0, -2.2, 2.8), (-0.6, 0.1, 0.65), lens=38)
        orbit(c, (-0.3, 0.1), 2.1, 2.7, -20, 25)
    else:
        n = 7
        for k in range(n):
            ball = snowball(a + Vector((0, 0, 0.1)))
            f0 = 1 + k * 9; f1 = f0 + 14
            key(ball, 1, loc=a + Vector((0, 0, 3))); key(ball, f0, loc=a + Vector((0, 0, 0.12)))
            key(ball, f1, loc=bpt + Vector((0, 0, 0.08)))
            rest = bpt + Vector((0.12 * (k % 3) + 0.05, -0.1 - 0.12 * (k // 3), -0.14))
            key(ball, f1 + 6, loc=rest)
        c, t = camera((-0.3, -1.3, 1.9), (-0.55, 0.0, 0.6), lens=32)
        key(c, 1, loc=(-0.1, -1.4, 2.1)); key(c, NF, loc=(-0.25, -1.0, 1.5))

elif SHOT in ("s08", "s13"):  # bungee slingshot across the window
    if SHOT == "s08": studio()
    else: backyard()
    f = fort()
    wz = 0.15 + 2 * 0.3
    aL = Vector((-0.3, -0.98, wz)); aR = Vector((0.3, -0.98, wz))
    pouch0 = Vector((0, -0.95, wz))
    cords = []
    for col, dz in (((1.0, 0.8, 0.0), 0.04), ((1.0, 0.25, 0.02), -0.04)):
        o, sp = curve_line([aL + Vector((0, 0, dz)), pouch0 + Vector((0, 0, dz)), aR + Vector((0, 0, dz))], 0.012, mat("bungee%f" % dz, col, rough=0.4))
        cords.append(sp)
        for anchor in (aL, aR):
            sphere(anchor + Vector((0, 0, dz)), 0.025, mat("hook", (0.1, 0.1, 0.1), metal=1, rough=0.3))
    pouch = sphere(pouch0, 0.09, mat("pouch", (0.1, 0.1, 0.12), rough=0.7), scale=(1, 0.6, 0.8))
    ball = snowball(pouch0 + Vector((0, 0, 0)), 0.075)
    if SHOT == "s08":
        pull = [(1, 0), (int(NF * 0.35), 0), (int(NF * 0.7), 0.75), (int(NF * 0.75), -0.25), (int(NF * 0.8), 0.12), (int(NF * 0.86), 0)]
        c, t = camera((0.2, -3.0, 1.0), (0, -0.9, 0.75), lens=45)
        key(c, 1, loc=(0.6, -3.2, 1.1)); key(c, NF, loc=(0.0, -2.0, 0.85))
    else:
        pull = [(1, 0), (int(NF * 0.45), 0), (NF, 0.8)]
        kid("boy", (0.85, 0.06, 0.05), loc=(-0.3, 0.05, -0.3), rot_z=r(-10),
            pose={"shR": (-75, 0, -5), "elR": (-20, 0, 0), "shL": (-80, 0, 25), "elL": (-30, 0, 0)})
        c, t = camera((0.45, 0.9, 1.75), (0, -1.0, 0.7), lens=26, fstop=5.6)
        key(c, 1, loc=(0.5, 1.0, 1.8)); key(c, NF, loc=(0.35, 0.6, 1.55))
        bro, _ = kid("bro", (0.1, 0.65, 0.15), loc=(-0.4, -4.0, 0), rot_z=r(170), pose={"shR": (-40, 0, -10), "shL": (-40, 0, 10)})
    for fr, amt in pull:
        p = pouch0 + Vector((0, amt, -0.05 * amt))
        pouch.location = p; pouch.keyframe_insert("location", frame=fr)
        ball.location = p; ball.keyframe_insert("location", frame=fr)
        for sp, dz in zip(cords, (0.04, -0.04)):
            sp.points[1].co = (*(p + Vector((0, 0, dz))), 1); sp.points[1].keyframe_insert("co", frame=fr)

elif SHOT in ("s09", "s10"):  # final touch / periscope
    studio(); fort()
    kid("boy", (0.85, 0.06, 0.05), loc=(0, 0.15, -0.25), pose={"shR": (-150, 0, -5), "elR": (-20, 0, 0), "shL": (-20, 0, 15)}, look=(0, 10))
    pr = periscope((0.15, -0.05, 0.6))
    if SHOT == "s09":
        key(pr, 1, loc=(0.15, -0.05, -0.5))
        c, t = camera((2.5, -4, 3.2), (0, 0, 0.6), lens=36)
        key(c, 1, loc=(3.2, -4.5, 3.8)); key(c, NF, loc=(2.2, -3.6, 2.6))
    else:
        key(pr, 1, loc=(0.15, -0.05, 0.05)); key(pr, int(NF * 0.45), loc=(0.15, -0.05, 0.85))
        key(pr, int(NF * 0.6), rot=(0, 0, 0)); key(pr, int(NF * 0.8), rot=(0, 0, r(-25))); key(pr, NF, rot=(0, 0, r(15)))
        c, t = camera((1.0, -3.2, 1.0), (0.15, -0.1, 1.2), lens=40)
        key(c, 1, loc=(1.2, -3.4, 0.9)); key(c, NF, loc=(0.6, -2.4, 1.9))
        key(t, 1, loc=(0.15, -0.1, 1.0)); key(t, NF, loc=(0.15, -0.1, 1.75))

elif SHOT == "s11":  # brother sneaking up in the backyard
    backyard()
    f = fort((1.4, 0.8, 0)); periscope((1.55, 0.75, 0.85))
    bro, arms = kid("bro", (0.1, 0.65, 0.15), loc=(-2.5, -1.2, -0.12), rot_z=r(117),
                    pose={"shR": (-60, 0, -20), "elR": (-40, 0, 0), "shL": (-60, 0, 20), "elL": (-40, 0, 0)}, look=(10, -5))
    bro.rotation_euler = (0, 0, r(117))
    key(bro, 1, loc=(-2.5, -1.2, -0.12)); key(bro, NF, loc=(-1.6, -1.15, -0.12))
    snowball((0.0, 0.0, 0.0), parent=arms["R"][1]).location = (0, -0.05, -0.33)
    c, t = camera((-0.6, -3.2, 0.7), (-1.8, -1.1, 0.75), lens=40)
    key(c, 1, loc=(-0.9, -3.5, 0.65)); key(c, NF, loc=(0.0, -3.0, 0.75))
    key(t, 1, loc=(-2.3, -1.1, 0.8)); key(t, NF, loc=(-1.4, -1.0, 0.8))

elif SHOT == "s12":  # periscope POV (circular mask added in compositing)
    backyard()
    bro, arms = kid("bro", (0.1, 0.65, 0.15), loc=(-1.0, -2.5, -0.12), rot_z=r(150),
                    pose={"shR": (-60, 0, -20), "elR": (-40, 0, 0), "shL": (-60, 0, 20), "elL": (-40, 0, 0)}, look=(15, -5))
    bro.rotation_euler = (0, 0, r(150))
    key(bro, 1, loc=(-1.2, -2.6, -0.12)); key(bro, NF, loc=(-0.85, -2.45, -0.12))
    c, t = camera((1.4, 1.2, 1.7), (-1.0, -2.4, 0.95), lens=55, fstop=8)
    key(c, 1, loc=(1.4, 1.2, 1.7)); c.data.lens = 50; c.data.keyframe_insert("lens", frame=1)
    c.data.lens = 85; c.data.keyframe_insert("lens", frame=NF)

elif SHOT == "s14":  # fire! snowball flies at the brother
    backyard()
    fort((0.5, 2.5, 0))
    bro, _ = kid("bro", (0.1, 0.65, 0.15), loc=(-0.3, -2.0, 0), rot_z=r(170),
                 pose={"shR": (-30, 0, -40), "shL": (-30, 0, 40)}, look=(0, 0))
    ball = snowball((0.5, 1.5, 0.75), 0.08)
    key(ball, 1, loc=(0.5, 1.45, 0.75)); key(ball, NF, loc=(-0.28, -1.85, 1.3)); linear(ball)
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.8
    c, t = camera((1.6, 0.6, 1.0), (0.5, 1.45, 0.75), lens=28, fstop=5.6)
    key(t, 1, loc=(0.5, 1.45, 0.75)); key(t, NF, loc=(-0.28, -1.85, 1.3))
    key(c, 1, loc=(1.6, 0.8, 1.0)); key(c, NF, loc=(0.9, -1.3, 1.25))

elif SHOT == "s15":  # he never stood a chance
    backyard()
    fort((0.6, 3.0, 0))
    peek, _ = kid("peek", (0.85, 0.06, 0.05), loc=(0.6, 3.1, 0.0), rot_z=r(185), look=(0, 0), smile=1.3)
    bro, _ = kid("bro", (0.1, 0.65, 0.15), loc=(0, 0, 0), rot_z=r(-8), smile=0.0, lid=0.6,
                 pose={"shR": (0, 0, -30), "elR": (0, 0, 0), "shL": (0, 0, 30)}, look=(0, -5))
    random.seed(3)
    splat = empty("splat", loc=(0, -0.19, 1.3))
    for k in range(26):
        a = random.uniform(0, 2 * math.pi); rr = random.uniform(0, 0.13)
        sphere((math.cos(a) * rr, -random.uniform(0.0, 0.05), math.sin(a) * rr * 1.1 + 0.02), random.uniform(0.025, 0.06), snow_mat(), parent=splat, sub=1, seg=12)
    for k in range(10):
        snowball((random.uniform(-0.25, 0.25), random.uniform(-0.3, 0.1), random.uniform(0.85, 1.1)), random.uniform(0.02, 0.04))
    key(bro, 1, rot=(0, r(-4), r(-8))); key(bro, 20, rot=(0, r(4), r(-8))); key(bro, 40, rot=(0, r(-3), r(-8))); key(bro, NF, rot=(0, r(2), r(-8)))
    c, t = camera((0.25, -1.6, 1.4), (0.05, 0, 1.15), lens=40, fstop=2.2)
    key(c, 1, loc=(0.35, -1.9, 1.45)); key(c, NF, loc=(0.18, -1.25, 1.35))

# ---------------------------------------------------------------- render
import os
os.makedirs(OUT, exist_ok=True)
if MODE == "still":
    sc.frame_set(int(NF * 0.6))
    sc.render.filepath = os.path.join(OUT, SHOT + "_still.png")
    bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = os.path.join(OUT, SHOT, "")
    bpy.ops.render.render(animation=True)
print("DONE", SHOT)
