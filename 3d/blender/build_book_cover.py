"""북커버를 사진 재질로 새로 짓는다(앞뒤 표지 · 둥근 등 · 책장 · 여밈 끈 · 금속 단추).
  Blender -b -P build_book_cover.py -- <book_cover_texture.py 의 폴더> <../models/brown-lace-book-cover.glb>
앞은 -Y, 등은 -X, 밑은 z=0. 그 뒤 `npx @gltf-transform/cli@4 meshopt <파일> <파일>` 로 압축한다.
"""
import bmesh, bpy, json, math, os, sys

args = sys.argv[sys.argv.index('--') + 1:]
folder, dst = args[0], args[1]
S = json.load(open(os.path.join(folder, 'book.json')))
W, H, D, T, R, CORNER = 1.30, 1.66, .30, .034, .09, .07
XL = -W / 2 + R
AT = S['atlas']


def atlas(rect, u, v):
    return ((rect[0] + u * (rect[2] - rect[0])) / AT, 1 - (rect[1] + v * (rect[3] - rect[1])) / AT)


def face_uv(rect):
    return lambda c: atlas(rect, (c.x + W / 2) / W, (H - c.z) / H)


def cloth_uv(c):
    return atlas(S['fabric'], (c.x + c.y * .5 + W / 2 + .1) / (W + .5), (c.z + c.y * .5 + .2) / (H + .4))


def add(bm, uvl, verts, fn, mat=0):
    f = bm.faces.new(verts); f.material_index = mat
    for loop in f.loops:
        loop[uvl].uv = fn(loop.vert.co)
    return f


def panel_outline():
    pts = [(XL, 0)]
    for cx, cz, a0 in ((W / 2 - CORNER, CORNER, -90), (W / 2 - CORNER, H - CORNER, 0)):
        for i in range(9):
            a = math.radians(a0 + i * 90 / 8)
            pts.append((cx + CORNER * math.cos(a), cz + CORNER * math.sin(a)))
    pts.append((XL, H))
    return pts


def prism(bm, uvl, pts, y0, y1, cap0, cap1):
    a = [bm.verts.new((x, y0, z)) for x, z in pts]
    b = [bm.verts.new((x, y1, z)) for x, z in pts]
    add(bm, uvl, a, cap0); add(bm, uvl, list(reversed(b)), cap1)
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        add(bm, uvl, [a[j], a[i], b[i], b[j]], cloth_uv)


def spine(bm, uvl, n=18):
    def ring(rx, ry, z):
        return [bm.verts.new((XL - rx * math.cos(t), ry * math.sin(t), z))
                for t in (math.radians(-90 + 180 * i / n) for i in range(n + 1))]
    ob, ot = ring(R, D / 2, 0), ring(R, D / 2, H)
    ib, it = ring(R - T, D / 2 - T, 0), ring(R - T, D / 2 - T, H)
    for i in range(n):
        s0, s1 = i / n, (i + 1) / n
        f = bm.faces.new((ob[i], ob[i + 1], ot[i + 1], ot[i]))
        for loop, (s, z) in zip(f.loops, ((s0, 0), (s1, 0), (s1, H), (s0, H))):
            loop[uvl].uv = atlas(S['spine'], 1 - z / H, 1 - s)
        add(bm, uvl, [ib[i + 1], ib[i], it[i], it[i + 1]], cloth_uv)
        add(bm, uvl, [ob[i + 1], ob[i], ib[i], ib[i + 1]], cloth_uv)
        add(bm, uvl, [ot[i], ot[i + 1], it[i + 1], it[i]], cloth_uv)


def pages(bm, uvl):
    x0, x1, y0, y1, z0, z1 = -W / 2 + .05, W / 2 - .055, -D / 2 + T, D / 2 - T, .035, H - .035
    v = {k: bm.verts.new(k) for k in ((x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1))}
    def page(along):
        return lambda c: atlas(S['pages'], along(c), (c.y - y0) / (y1 - y0))
    q = lambda *keys: [v[k] for k in keys]
    add(bm, uvl, q((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)), page(lambda c: c.z / H))
    add(bm, uvl, q((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)), page(lambda c: c.z / H))
    add(bm, uvl, q((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)), page(lambda c: (c.x + W / 2) / W))
    add(bm, uvl, q((x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)), page(lambda c: (c.x + W / 2) / W))
    add(bm, uvl, q((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)), cloth_uv)
    add(bm, uvl, q((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)), cloth_uv)


def strap(bm, uvl, bx, bz, hw=.06, th=.018):
    def path(xo, yo, rho):
        p = [(bx - .03, -yo)]
        for cy, a0 in ((-yo + rho, -90), (yo - rho, 0)):
            for i in range(7):
                a = math.radians(a0 + i * 90 / 6)
                p.append((xo - rho + rho * math.cos(a), cy + rho * math.sin(a)))
        p.append((W / 2 - .2, yo))
        return p
    Xo, Yo = W / 2 + .018, D / 2 + .016
    out, inn = path(Xo, Yo, .055), path(Xo - th, Yo - th, .055 - th)
    O0, O1 = [[bm.verts.new((x, y, z)) for x, y in out] for z in (bz - hw, bz + hw)]
    I0, I1 = [[bm.verts.new((x, y, z)) for x, y in inn] for z in (bz - hw, bz + hw)]
    for i in range(len(out) - 1):
        add(bm, uvl, [O0[i], O0[i + 1], O1[i + 1], O1[i]], cloth_uv)
        add(bm, uvl, [I0[i + 1], I0[i], I1[i], I1[i + 1]], cloth_uv)
        add(bm, uvl, [O0[i + 1], O0[i], I0[i], I0[i + 1]], cloth_uv)
        add(bm, uvl, [O1[i], O1[i + 1], I1[i + 1], I1[i]], cloth_uv)
    for e in (0, -1):
        vs = [O0[e], O1[e], I1[e], I0[e]]
        add(bm, uvl, vs if e == 0 else list(reversed(vs)), cloth_uv)


def button(bm, uvl, bx, bz, rb, n=48):
    base = -D / 2 - .03
    prof = [(1, 0), (1, -.016), (.93, -.027), (.72, -.036), (.4, -.041), (.12, -.043)]
    rings = [[bm.verts.new((bx + rb * r * math.cos(2 * math.pi * i / n), base + h, bz + rb * r * math.sin(2 * math.pi * i / n)))
              for i in range(n)] for r, h in prof]
    uv = face_uv(S['front'])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            add(bm, uvl, [a[i], a[j], b[j], b[i]], uv, 1)
    add(bm, uvl, list(reversed(rings[-1])), uv, 1)
    add(bm, uvl, rings[0], cloth_uv, 1)


def material(name, color, normal, rough, metal):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexImage'); tc.image = color
    nt.links.new(tc.outputs['Color'], b.inputs['Base Color'])
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = normal
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = .45
    nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    return m


bpy.ops.wm.read_factory_settings(use_empty=True)
color = bpy.data.images.load(os.path.join(folder, 'book_color.png'))
normal = bpy.data.images.load(os.path.join(folder, 'book_normal.png')); normal.colorspace_settings.name = 'Non-Color'
color.scale(1536, 1536); normal.scale(1536, 1536)   # 레이스가 뭉개지지 않는 선에서 파일을 줄인다

me = bpy.data.meshes.new('BookCover'); ob = bpy.data.objects.new('BookCover', me)
bpy.context.scene.collection.objects.link(ob); bpy.context.view_layer.objects.active = ob; ob.select_set(True)
me.materials.append(material('Cloth', color, normal, .9, 0)); me.materials.append(material('Metal', color, normal, .36, .75))

bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
bu, bv, br = S['button']
bx, bz, rb = -W / 2 + bu * W, H * (1 - bv), br * W
outline = panel_outline()
prism(bm, uvl, outline, -D / 2, -D / 2 + T, face_uv(S['front']), cloth_uv)
prism(bm, uvl, outline, D / 2, D / 2 - T, face_uv(S['back']), cloth_uv)
spine(bm, uvl); pages(bm, uvl); strap(bm, uvl, bx, bz); button(bm, uvl, bx, bz, rb)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(me); bm.free()

bev = ob.modifiers.new('soft', 'BEVEL'); bev.limit_method = 'ANGLE'; bev.angle_limit = math.radians(35)
bev.width = .005; bev.segments = 2; bev.harden_normals = False
bpy.ops.object.modifier_apply(modifier='soft')
me.polygons.foreach_set('use_smooth', [True] * len(me.polygons)); me.update()
me.set_sharp_from_angle(angle=math.radians(38))

os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', use_selection=True, export_apply=True,
                          export_image_format='WEBP', export_image_quality=86, export_yup=True)
print('DONE tris', sum(len(p.vertices) - 2 for p in me.polygons), os.path.getsize(dst) // 1024, 'KB')
