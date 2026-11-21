"""OHANAE 3D 쇼룸의 방을 Blender 로 짓고, 빛을 구워서 웹용 파일로 내보낸다.

실행:  Blender -b -P build_room.py            (완성본)
       QUALITY=draft Blender -b -P build_room.py   (빠른 확인용)

만드는 것 (../assets/):
  room.glb        방 · 가구 · 소품. UV0 = 재질, UV1 = 구운 빛
  lm_<묶음>.jpg    묶음(shell · wood · furn)별 구운 빛(직접광 + 간접광). 값은 1/LM_SCALE 로 줄여 sRGB 로 담는다
  env_a.hdr · env_b.hdr   방마다 한가운데서 찍은 360° 사진(반사 · 움직이는 물건의 조명용)
  preview_*.jpg   확인용 그림

창밖 풍경(sky.jpg)은 build_view.py 가 따로 만든다. 굽는 빛은 정원 하늘 사진(HDRI)에서 온다.
치수와 가구 자리는 space.json(= space.js 에서 뽑은 것)을 따른다. 좌표는 three.js 기준(x, y 위, z)으로 적고
P() 로 Blender 좌표(x, -z, y)로 바꾼다. 재질 · 소품은 Poly Haven · ambientCG 의 CC0 에셋이다.
"""
import bpy, bmesh, json, math, os, random
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('SHOWROOM_SRC', '/Users/tenedict/Desktop/휘재/showroom-assets-src')
OUT = os.path.normpath(os.path.join(HERE, '..', 'assets'))
DRAFT = os.environ.get('QUALITY', 'final') == 'draft'
ONLY_PREVIEW = os.environ.get('ONLY_PREVIEW') == '1'
SAMPLES = 24 if DRAFT else 192
LM_SIZE = {'shell': 1024, 'wood': 512, 'furn': 1024, 'decor': 512} if DRAFT else {'shell': 2048, 'wood': 1024, 'furn': 2048, 'decor': 1024}
LM_SCALE = 3.0
os.makedirs(OUT, exist_ok=True)

space = json.load(open(os.path.join(HERE, 'space.json')))
W, DEPTH, H, DOOR = space['W'], space['DEPTH'], space['H'], space['DOOR']
FURN = {f['id']: f for f in space['FURNITURE']}
random.seed(7)

def P(x, y, z):
    return Vector((x, -z, y))

# ───────── 빈 장면 · 렌더 설정 ─────────
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for d in prefs.devices: d.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print('GPU 를 쓰지 못해 CPU 로 굽는다:', e)
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
scene.cycles.diffuse_bounces = 5

# ───────── 재질 ─────────
def new_mat(name):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    return m, m.node_tree, m.node_tree.nodes['Principled BSDF']

def tex_mat(name, diff, rough, nor, normal_strength=1.0):
    m, nt, b = new_mat(name)
    def img(path, cs):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(path); n.image.colorspace_settings.name = cs; return n
    nt.links.new(img(diff, 'sRGB').outputs['Color'], b.inputs['Base Color'])
    nt.links.new(img(rough, 'Non-Color').outputs['Color'], b.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal_strength
    nt.links.new(img(nor, 'Non-Color').outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m

def flat_mat(name, color, rough=.8, metallic=0.0, emission=0.0, emission_color=None):
    m, nt, b = new_mat(name)
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metallic
    if emission:
        b.inputs['Emission Color'].default_value = (*(emission_color or color), 1)
        b.inputs['Emission Strength'].default_value = emission
    return m

T = lambda *p: os.path.join(SRC, *p)
MAT = {
    'marble': tex_mat('marble', T('proc', 'marble_diff.jpg'), T('proc', 'marble_rough.jpg'), T('textures', 'Marble019', 'nor.jpg'), .4),
    'travertine': tex_mat('travertine', T('textures', 'Travertine009', 'diff.jpg'), T('proc', 'travertine_rough.jpg'), T('textures', 'Travertine009', 'nor.jpg'), .6),
    'oak': tex_mat('oak', T('textures', 'oak_veneer_01', 'diff.jpg'), T('textures', 'oak_veneer_01', 'rough.jpg'), T('textures', 'oak_veneer_01', 'nor.jpg'), .7),
    'wall': tex_mat('wall', T('proc', 'wall_diff.jpg'), T('textures', 'beige_wall_001', 'rough.jpg'), T('textures', 'beige_wall_001', 'nor.jpg'), .5),
    'rug': tex_mat('rug', T('textures', 'Carpet016', 'diff.jpg'), T('textures', 'Carpet016', 'rough.jpg'), T('textures', 'Carpet016', 'nor.jpg'), 1.0),
    'ceiling': flat_mat('ceiling', (.9, .88, .84), .95),
    'grout': flat_mat('grout', (.5, .47, .43), .9),
    'metal': flat_mat('metal', (.03, .028, .026), .42, .8),
    'backing': flat_mat('backing', (.09, .07, .05), .9),
    'strip': flat_mat('strip', (1, .86, .66), .5, emission=70.0),
    'spot': flat_mat('spot', (1, .9, .76), .5, emission=40.0),
    'shade': flat_mat('shade', (1, .93, .82), .9, emission=6.0, emission_color=(1, .84, .62)),
}

# ───────── 만들기 도우미 ─────────
def cube_uv(ob, size, swap=False):
    """세계 좌표로 상자 투영 — 1 UV = size m. swap 이면 결 방향을 바꾼다."""
    me = ob.data
    uvl = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co + ob.location
            u, v = (co.y, co.z) if ax == 0 else (co.x, co.z) if ax == 1 else (co.x, co.y)
            if swap: u, v = v, u
            uvl.data[li].uv = (u / size, v / size)

def link(ob, group):
    scene.collection.objects.link(ob); ob['group'] = group; return ob

def box(name, x0, x1, y0, y1, z0, z1, mat, group, bevel=0.0, uv=1.0, swap=False):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * (x1 - x0), v.co.y * (z1 - z0), v.co.z * (y1 - y0)))
    if bevel: bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2, affect='EDGES', profile=.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me), group)
    ob.location = P((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    me.materials.append(mat)
    cube_uv(ob, uv, swap)
    return ob

def cylinder(name, x, y, z, radius, depth, mat, group, axis='y', segments=48, uv=1.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=radius, radius2=radius, depth=depth)
    if axis == 'z': bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me), group)
    ob.location = P(x, y, z); me.materials.append(mat)
    cube_uv(ob, uv)
    return ob

def cut(ob, cutters):
    """cutters 를 ob 에서 파낸다(창 · 문)."""
    for c in cutters:
        mod = ob.modifiers.new('cut', 'BOOLEAN'); mod.object = c; mod.operation = 'DIFFERENCE'; mod.solver = 'EXACT'
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data; ob.modifiers.clear(); ob.data = me; bpy.data.meshes.remove(old)
    for c in cutters: bpy.data.objects.remove(c, do_unlink=True)

def cull(ob, keep):
    """keep(가운데 좌표, 법선) 이 거짓인 면을 지운다(둘 다 three.js 좌표). 안 보이는 면에 빛 굽는 자리를 쓰지 않으려는 것."""
    me = ob.data; bm = bmesh.new(); bm.from_mesh(me)
    dead = []
    for f in bm.faces:
        c = ob.location + f.calc_center_median(); n = f.normal
        if not keep((c.x, c.z, -c.y), (n.x, n.z, -n.y)): dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bm.to_mesh(me); bm.free()

# ───────── 바닥: 1m 대리석 판 8 × 16 장. 판마다 무늬 자리를 달리한다 ─────────
def build_floor():
    me = bpy.data.meshes.new('floor'); bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap'); lm = bm.loops.layers.uv.new('lm')
    nx, nz = int(W * 2), int(DEPTH * 2)
    verts = [[bm.verts.new(P(-W + i, 0, -DEPTH + j)) for j in range(nz + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(nz):
            f = bm.faces.new((verts[i][j], verts[i][j + 1], verts[i + 1][j + 1], verts[i + 1][j]))
            ou, ov, rot = random.random(), random.random(), random.randrange(4)
            corners = [(0, 0), (0, .5), (.5, .5), (.5, 0)]
            corners = corners[rot:] + corners[:rot]
            for loop, (cu, cv) in zip(f.loops, corners):
                loop[uv].uv = (ou + cu, ov + cv)
                co = loop.vert.co
                loop[lm].uv = ((co.x + W) / (DEPTH * 2), (-co.y + DEPTH) / (DEPTH * 2))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if bm.faces[0].normal.z < 0: bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new('floor', me), 'floor')
    me.materials.append(MAT['marble'])
    # 줄눈: 판 사이의 가는 어두운 선
    g = .004
    top = lambda c, n: n[1] > .5
    for i in range(1, nx): cull(box(f'grout_x{i}', -W + i - g / 2, -W + i + g / 2, .0002, .0006, -DEPTH, DEPTH, MAT['grout'], 'shell'), top)
    for j in range(1, nz): cull(box(f'grout_z{j}', -W, W, .0002, .0006, -DEPTH + j - g / 2, -DEPTH + j + g / 2, MAT['grout'], 'shell'), top)

# ───────── 벽 · 천장 ─────────
WIN_A = dict(z=4.2, w=3.2, y0=.45, y1=2.75)     # Room A 왼쪽 벽
WIN_B = dict(x=2.6, w=1.7, y0=.45, y1=2.75)     # Room B 안쪽 벽
ARCH = 1.9

def build_shell():
    t = .2
    left = box('wall_left', -W - t, -W, 0, H, -DEPTH - t, DEPTH + t, MAT['wall'], 'shell', uv=2)
    right = box('wall_right', W, W + t, 0, H, -DEPTH - t, DEPTH + t, MAT['wall'], 'shell', uv=2)
    front = box('wall_front', -W, W, 0, H, DEPTH, DEPTH + t, MAT['wall'], 'shell', uv=2)
    back = box('wall_back', -W, W, 0, H, -DEPTH - t, -DEPTH, MAT['wall'], 'shell', uv=2)
    mid = box('wall_mid', -W, W, 0, H, -.1, .1, MAT['wall'], 'shell', uv=2)
    ceiling = box('ceiling', -W - t, W + t, H, H + t, -DEPTH - t, DEPTH + t, MAT['ceiling'], 'shell')
    a, b = WIN_A, WIN_B
    cut(left, [box('c', -W - t - .1, -W + .1, a['y0'], a['y1'], a['z'] - a['w'] / 2, a['z'] + a['w'] / 2, MAT['wall'], 'tmp')])
    cut(back, [box('c', b['x'] - b['w'] / 2, b['x'] + b['w'] / 2, b['y0'], b['y1'], -DEPTH - t - .1, -DEPTH + .1, MAT['wall'], 'tmp')])
    cut(mid, [box('c', -DOOR, DOOR, -.1, ARCH, -.3, .3, MAT['wall'], 'tmp'),
              cylinder('c2', 0, ARCH, 0, DOOR, .6, MAT['wall'], 'tmp', axis='z', segments=64)])
    # 방 안에서 안 보이는 면(바깥 면 · 바닥과 천장에 맞닿은 면)은 지운다. 남은 안쪽 면만으로도 빛은 새지 않는다
    def inner(c, n):
        if abs(c[0]) > W + t - .005 or abs(c[2]) > DEPTH + t - .005: return False
        if c[1] < .005 and n[1] < -.5: return False
        if c[1] > H - .005 and n[1] > .5: return False
        return True
    for ob in (left, right, front, back, mid): cull(ob, inner)
    cull(ceiling, lambda c, n: n[1] < -.5)
    for ob in (left, back, mid): cube_uv(ob, 2)

    # 창틀: 가는 검은 철제
    m = MAT['metal']
    def frame_x(x, z, w, y0, y1):          # x 벽에 난 창
        for k in range(int(round(w / .8)) + 1):
            zz = z - w / 2 + k * w / int(round(w / .8)); box('wf', x - .03, x + .03, y0, y1, zz - .018, zz + .018, m, 'furn')
        for yy in (y0, y1): box('wf', x - .03, x + .03, yy - .018, yy + .018, z - w / 2, z + w / 2, m, 'furn')
    def frame_z(x, z, w, y0, y1):
        for k in range(int(round(w / .8)) + 1):
            xx = x - w / 2 + k * w / int(round(w / .8)); box('wf', xx - .018, xx + .018, y0, y1, z - .03, z + .03, m, 'furn')
        for yy in (y0, y1): box('wf', x - w / 2, x + w / 2, yy - .018, yy + .018, z - .03, z + .03, m, 'furn')
    frame_x(-W - t / 2, a['z'], a['w'], a['y0'], a['y1'])
    frame_z(b['x'], -DEPTH - t / 2, b['w'], b['y0'], b['y1'])

    # 내린 천장과 간접 조명: 방마다 천장 판을 10cm 띄워 달고, 판 위 가장자리에 빛 띠를 숨긴다
    for z0, z1 in ((.5, DEPTH - .4), (-DEPTH + .4, -.5)):
        x0, x1, top = -W + .38, W - .38, H - .1
        box('panel', x0, x1, top - .08, top, z0, z1, MAT['ceiling'], 'shell')
        s = .06
        box('strip', x0 + s, x0 + s + .03, top, top + .015, z0 + s, z1 - s, MAT['strip'], 'emit')
        box('strip', x1 - s - .03, x1 - s, top, top + .015, z0 + s, z1 - s, MAT['strip'], 'emit')
        box('strip', x0 + s, x1 - s, top, top + .015, z0 + s, z0 + s + .03, MAT['strip'], 'emit')
        box('strip', x0 + s, x1 - s, top, top + .015, z1 - s - .03, z1 - s, MAT['strip'], 'emit')

def build_slats():
    """세로 살 오크 벽: 입구 쪽 벽 전체, Room B 안쪽 벽의 왼쪽 5m."""
    pitch, sw, sd = .05, .032, .022
    box('slat_back_a', -W, W, 0, H, DEPTH - .006, DEPTH, MAT['backing'], 'wood')
    box('slat_back_b', -W, 1.0, 0, H, -DEPTH, -DEPTH + .006, MAT['backing'], 'wood')
    n = int(W * 2 / pitch)
    for i in range(n):
        x = -W + pitch / 2 + i * pitch
        box('slat', x - sw / 2, x + sw / 2, 0, H, DEPTH - .006 - sd, DEPTH - .006, MAT['oak'], 'wood', uv=1.6)
        if x < 1.0: box('slat', x - sw / 2, x + sw / 2, 0, H, -DEPTH + .006, -DEPTH + .006 + sd, MAT['oak'], 'wood', uv=1.6)

# ───────── 가구 (space.json 의 자리 그대로) ─────────
def build_furniture():
    for f in space['FURNITURE']:
        x, z, w, d, h = f['x'], f['z'], f['w'], f['d'], f['h']
        if f['kind'] == 'table':    # 두꺼운 오크 상판을 트래버틴 판 다리 둘이 받친다
            along = w >= d
            box(f['id'] + '_top', x - w / 2, x + w / 2, h - .06, h, z - d / 2, z + d / 2, MAT['oak'], 'furn', bevel=.006, uv=1.4, swap=along)
            for s in (-1, 1):
                if along: box(f['id'] + '_leg', x + s * (w / 2 - .32) - .07, x + s * (w / 2 - .32) + .07, 0, h - .06, z - d / 2 + .08, z + d / 2 - .08, MAT['travertine'], 'furn', bevel=.008, uv=1.2)
                else: box(f['id'] + '_leg', x - w / 2 + .08, x + w / 2 - .08, 0, h - .06, z + s * (d / 2 - .32) - .07, z + s * (d / 2 - .32) + .07, MAT['travertine'], 'furn', bevel=.008, uv=1.2)
            if max(w, d) > 2:       # 큰 테이블 밑 둥근 러그
                cylinder(f['id'] + '_rug', x, .007, z, max(w, d) / 2 + .55, .014, MAT['rug'], 'furn', segments=96, uv=.9)
        else:
            box(f['id'], x - w / 2, x + w / 2, 0, h, z - d / 2, z + d / 2, MAT['travertine'], 'furn', bevel=.01, uv=1.2)

# ───────── 소품 (Poly Haven 모델) ─────────
def import_model(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=T('models', name, name + '.gltf'))
    bpy.context.view_layer.update()
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    for o in meshes:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = Matrix.Identity(4); o.data.transform(mw)
        while len(o.data.uv_layers) > 1: o.data.uv_layers.remove(o.data.uv_layers[-1])
        if o.data.uv_layers: o.data.uv_layers[0].name = 'UVMap'
    for o in new:
        if o.type != 'MESH': bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    ob = meshes[0]; ob.name = name
    for c in list(ob.users_collection): c.objects.unlink(ob)
    # 밑바닥 가운데가 원점이 되게 옮긴다
    cos = [v.co for v in ob.data.vertices]
    lo = Vector((min(c.x for c in cos), min(c.y for c in cos), min(c.z for c in cos)))
    hi = Vector((max(c.x for c in cos), max(c.y for c in cos), max(c.z for c in cos)))
    ob.data.transform(Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    ob['size'] = tuple(hi - lo)
    # 웹에서 가볍게 돌도록 삼각형 수를 줄인다(가까이서 봐도 티 나지 않는 선까지)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    target = next((n for key, n in TRI_BUDGET.items() if key in name), 4000)
    if tris > target:
        scene.collection.objects.link(ob)
        mod = ob.modifiers.new('decimate', 'DECIMATE'); mod.ratio = target / tris
        bpy.context.view_layer.update()
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        old = ob.data; ob.modifiers.clear(); ob.data = me; bpy.data.meshes.remove(old)
        scene.collection.objects.unlink(ob)
    after = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print(f'model {name}: {tuple(round(v, 2) for v in (hi - lo))}  tris {tris} -> {after}')
    return ob

TRI_BUDGET = {'potted_plant_02': 14000, 'lounge_chair': 12000, 'wicker_basket': 8000, 'wooden_bowl': 3500,
              'ceramic_vase': 3000, 'side_table': 2500, 'potted_plant_04': 4000, 'ceiling_lamp': 3000}

MODELS = {}
def place(name, x, y, z, rot=0, scale=1.0, hang=False):
    """rot: 바라보는 쪽(도, 0 = +z). hang 이면 y 가 꼭대기 높이."""
    src = MODELS.get(name) or MODELS.setdefault(name, import_model(name))
    ob = src.copy(); ob.data = src.data.copy(); link(ob, 'decor')
    height = src['size'][2] * scale
    ob.location = P(x, y - height if hang else y, z)
    ob.rotation_euler = (0, 0, math.radians(rot)); ob.scale = (scale, scale, scale)
    return ob

def build_decor():
    for x, z in space['PLANTS']: place('potted_plant_02', x, 0, z, rot=random.uniform(0, 360), scale=1.25)
    place('mid_century_lounge_chair', -2.75, 0, 6.55, rot=127)
    place('side_table_01', -3.4, 0, 5.55, rot=90)
    place('potted_plant_04', -3.4, MODELS['side_table_01']['size'][2], 5.55, rot=40)
    s = FURN['shelfA']
    place('ceramic_vase_01', s['x'], s['h'], 1.05, rot=20)
    place('ceramic_vase_04', s['x'] - .02, s['h'], 1.72, rot=200)
    place('wooden_bowl_01', s['x'] + .02, s['h'], 2.2, rot=75)
    place('ceramic_vase_02', .02, FURN['lowB']['h'], FURN['lowB']['z'], rot=0)
    place('wicker_basket_01', 3.35, 0, -6.0, rot=15)
    # 테이블 위 등: 모델 꼭대기를 천장 판에 붙이고, 갓 아래에 실제 빛을 둔다
    for x, z in ((0, FURN['tableA']['z']), (0, FURN['tableB']['z'])):
        lamp = place('modern_ceiling_lamp_01', x, H - .18, z, hang=True)
        bottom = H - .18 - MODELS['modern_ceiling_lamp_01']['size'][2]
        light = bpy.data.lights.new('pendant', 'POINT'); light.energy = 140; light.color = (1, .82, .6); light.shadow_soft_size = .12
        lo = bpy.data.objects.new('pendant', light); scene.collection.objects.link(lo); lo.location = P(x, bottom - .12, z)

# ───────── 빛 ─────────
def build_lights():
    world = bpy.data.worlds.new('world'); scene.world = world
    try: world.use_nodes = True
    except Exception: pass
    nt = world.node_tree; bg = nt.nodes['Background']
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(T('hdri', 'symmetrical_garden_02_2k.hdr'))
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.5
    # 해: 왼쪽 창과 안쪽 창으로 비껴 들어와 바닥에 떨어진다
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 4.5; sun.color = (1, .9, .76); sun.angle = math.radians(1.5)
    so = bpy.data.objects.new('sun', sun); scene.collection.objects.link(so)
    travel = P(.62, -.58, .52).normalized()                  # 빛이 가는 방향
    so.rotation_euler = (-travel).to_track_quat('Z', 'Y').to_euler()
    # 천장 매입등: 방마다 3 × 3, 아래로 넓게 비춘다
    for zs in ((1.5, 3.6, 5.9), (-1.9, -4.0, -6.2)):
        for z in zs:
            for x in (-2.5, 0, 2.5):
                if x == 0 and z in (3.6, -4.0): continue      # 가운데는 테이블 위 등이 맡는다
                y = H - .18
                cylinder('spot', x, y - .004, z, .045, .008, MAT['spot'], 'emit', segments=24)
                sp = bpy.data.lights.new('spot', 'SPOT'); sp.energy = 110; sp.color = (1, .87, .7)
                sp.spot_size = math.radians(95); sp.spot_blend = .6; sp.shadow_soft_size = .05
                spo = bpy.data.objects.new('spot', sp); scene.collection.objects.link(spo); spo.location = P(x, y - .02, z)

# ───────── 빛 굽기 ─────────
def join_group(group):
    obs = [o for o in scene.objects if o.type == 'MESH' and o.get('group') == group]
    if not obs: return None
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
        if not o.data.uv_layers.get('UVMap'): o.data.uv_layers.new(name='UVMap')
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1: bpy.ops.object.join()
    ob = obs[0]; ob.name = group
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return ob

def unwrap_lightmap(ob, keep=None):
    """둘째 UV(lm)를 편다. keep 은 이미 lm 을 가진 물체(바닥) — 합친 뒤 크기를 맞춰 함께 채운다."""
    me = ob.data
    lm = me.uv_layers.get('lm') or me.uv_layers.new(name='lm')
    me.uv_layers.active = lm
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    if keep:
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); keep.select_set(True)
        bpy.context.view_layer.objects.active = ob; bpy.ops.object.join()
        me = ob.data; me.uv_layers.active = me.uv_layers['lm']
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    try: bpy.ops.uv.select_all(action='SELECT')
    except Exception as e: print('uv.select_all:', e)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(margin=.004)
    bpy.ops.object.mode_set(mode='OBJECT')
    me.uv_layers['UVMap'].active_render = True
    me.uv_layers.active = me.uv_layers['lm']

def bake(ob, group):
    size = LM_SIZE[group]
    img = bpy.data.images.new('lm_' + group, size, size, alpha=False, float_buffer=True)
    for slot in ob.material_slots:
        nt = slot.material.node_tree
        node = nt.nodes.get('BAKE') or nt.nodes.new('ShaderNodeTexImage'); node.name = 'BAKE'
        node.image = img
        for n in nt.nodes: n.select = False
        node.select = True; nt.nodes.active = node
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    print(f'bake {group} {size}px …', flush=True)
    scene.cycles.samples = SAMPLES
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, uv_layer='lm', margin=max(4, size // 256), use_clear=True)
    px = denoise(img, size)
    # 1/LM_SCALE 로 줄이고 sRGB 로 바꿔 8비트 JPEG 로 담는다
    rgb = np.clip(px[:, :3] / LM_SCALE, 0, 1)
    srgb = np.where(rgb <= .0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - .055)
    out = bpy.data.images.new('out_' + group, size, size, alpha=False)
    buf = np.ones((size * size, 4), dtype=np.float32); buf[:, :3] = srgb
    out.pixels.foreach_set(buf.ravel())
    out.filepath_raw = os.path.join(OUT, f'lm_{group}.jpg'); out.file_format = 'JPEG'
    scene.render.image_settings.quality = 92
    out.save()
    print(f'  mean {rgb.mean() * LM_SCALE:.3f}  max {px[:, :3].max():.2f}', flush=True)

def denoise(img, size):
    """구운 그림의 알갱이를 Blender 의 노이즈 제거(OpenImageDenoise)로 지운다. Cycles 굽기는 이걸 해 주지 않는다.
    합성기에서 그림 → 노이즈 제거 → EXR 로 한 번 그려 내고, 그 결과를 (픽셀 수, 4) 배열로 돌려준다."""
    tree = bpy.data.node_groups.new('denoise', 'CompositorNodeTree')
    scene.compositing_node_group = tree
    src = tree.nodes.new('CompositorNodeImage'); src.image = img
    den = tree.nodes.new('CompositorNodeDenoise')
    tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    dst = tree.nodes.new('NodeGroupOutput')
    tree.links.new(src.outputs['Image'], den.inputs['Image']); tree.links.new(den.outputs['Image'], dst.inputs['Image'])
    tmp = os.path.join(bpy.app.tempdir, 'lm_denoised.exr')
    scene.view_settings.view_transform = 'Standard'
    cam = scene.camera
    render_to(tmp, 'OPEN_EXR', size, size, 1)
    scene.camera = cam
    scene.compositing_node_group = None
    bpy.data.node_groups.remove(tree)
    res = bpy.data.images.load(tmp)
    px = np.empty(size * size * 4, dtype=np.float32); res.pixels.foreach_get(px)
    bpy.data.images.remove(res)
    return px.reshape(-1, 4)

# ───────── 확인용 그림 · 360° 사진 ─────────
def render_to(path, fmt, w, h, samples):
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = w, h, 100
    scene.cycles.samples = samples
    s = scene.render.image_settings
    try: s.media_type = 'IMAGE'
    except Exception: pass
    s.file_format = fmt
    if fmt == 'JPEG': s.quality = 88
    if fmt == 'OPEN_EXR': s.color_depth = '32'
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def preview(name, pos, yaw_deg):
    cam = bpy.data.cameras.new('cam'); cam.lens_unit = 'FOV'; cam.angle = math.radians(88)
    co = bpy.data.objects.new('cam', cam); scene.collection.objects.link(co)
    co.location = P(*pos); co.rotation_euler = (math.radians(86), 0, math.radians(yaw_deg))
    scene.camera = co
    scene.view_settings.view_transform = 'AgX'; scene.view_settings.exposure = 0
    render_to(os.path.join(OUT, f'preview_{name}.jpg'), 'JPEG', 1280, 720, 48 if DRAFT else 128)
    bpy.data.objects.remove(co, do_unlink=True)

def probe(name, pos):
    """방 한가운데 눈높이에서 찍는 360° 사진. 그림 가운데가 +x(three)를 보게 놓는다."""
    cam = bpy.data.cameras.new('probe'); cam.type = 'PANO'
    try: cam.panorama_type = 'EQUIRECTANGULAR'
    except Exception: cam.cycles.panorama_type = 'EQUIRECTANGULAR'
    co = bpy.data.objects.new('probe', cam); scene.collection.objects.link(co)
    co.location = P(*pos); co.rotation_euler = (math.radians(90), 0, math.radians(-90))
    scene.camera = co
    scene.view_settings.view_transform = 'Standard'
    render_to(os.path.join(OUT, f'env_{name}.hdr'), 'HDR', 512 if DRAFT else 1024, 256 if DRAFT else 512, 32 if DRAFT else 96)
    bpy.data.objects.remove(co, do_unlink=True)

# ───────── 순서대로 ─────────
build_floor(); build_shell(); build_slats(); build_furniture(); build_decor(); build_lights()
for o in [o for o in scene.objects if o.get('group') == 'tmp']: bpy.data.objects.remove(o, do_unlink=True)
bpy.context.view_layer.update()

preview('a', (0, 1.6, 7.2), 0)          # 입구에서 Room A
preview('b', (0, 1.6, -1.0), 0)         # 문 앞에서 Room B
if ONLY_PREVIEW:
    raise SystemExit

floor = next(o for o in scene.objects if o.get('group') == 'floor')
for group in ('shell', 'wood', 'furn'):
    ob = join_group(group)
    unwrap_lightmap(ob, keep=floor if group == 'shell' else None)
    bake(ob, group)
# 소품(decor)과 빛나는 것(emit)은 굽지 않는다. 소품은 쇼룸에서 360° 사진의 빛을 받고, 바닥에 드리운 그림자는 위에서 이미 구워졌다
join_group('decor'); join_group('emit')

probe('a', (0, 1.6, 4.4)); probe('b', (0, 1.6, -4.4))

# 내보내기: 조명 · 카메라는 빼고 방만
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if o.type == 'MESH': o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'room.glb'), export_format='GLB', use_selection=True,
                          export_apply=True, export_texcoords=True, export_normals=True, export_materials='EXPORT',
                          export_image_format='WEBP', export_image_quality=80, export_yup=True, export_extras=False)
for f in sorted(os.listdir(OUT)): print(f'{f:24s} {os.path.getsize(os.path.join(OUT, f)) // 1024:7d} KB')
print('DONE')
