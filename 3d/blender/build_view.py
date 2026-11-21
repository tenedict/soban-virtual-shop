"""창밖 풍경(광안리)을 Blender 로 지어 360° 그림 한 장으로 뽑는다.  Blender -b -P build_view.py

사진이 아니라 방과 같은 3D 로 만든 풍경이다: 백사장과 바다, 광안대교, 멀리 마린시티와 산, 하늘.
가게가 바닷가 건물 4층쯤(바다에서 13.6m 위)에 있다고 보고, 방 한가운데 눈높이에서 사방을 찍는다.
결과 ../assets/sky.jpg 를 쇼룸이 배경으로 쓴다(아주 멀리 있는 풍경이라 걸어 다녀도 움직이지 않는다).

좌표는 Blender 기준이다. 쇼룸(three.js)의 (x, y, z) 는 여기서 (x, -z, y).
바다는 두 창이 함께 바라보는 쪽(쇼룸의 -x · -z 사이)에 있고, 해는 방 안 빛을 구울 때와 같은 자리에 둔다.
"""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, '..', 'assets'))
DRAFT = os.environ.get('QUALITY', 'final') == 'draft'
random.seed(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'; prefs.get_devices()
    for d in prefs.devices: d.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print('GPU 를 쓰지 못한다:', e)
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4

SEA, EYE = -12.0, 1.6
D = Vector((-1, 1, 0)).normalized()       # 바다 쪽
T = Vector((1, 1, 0)).normalized()        # 해안선 · 다리가 놓인 방향 (바다를 볼 때 오른쪽이 +T)
Z = Vector((0, 0, 1))
FRAME = Matrix((T, D, Z)).transposed()    # 열: 길이(T) · 폭(D) · 높이
SUN = Vector((-.62, .52, .58)).normalized()   # 해가 있는 쪽(build_room.py 의 햇빛과 같다)
at = lambda d, t, z=0.0: D * d + T * t + Z * z

def lin(hex_color):
    """#rrggbb(sRGB) → Blender 가 쓰는 선형 값"""
    c = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c)

HAZE = lin('#cfe0ec')
def hazed(hex_color, amount):
    """멀리 있는 것은 하늘빛 쪽으로 흐려진다"""
    c = lin(hex_color)
    return tuple(c[i] * (1 - amount) + HAZE[i] * amount for i in range(3))

def material(name, color, rough=.8, metallic=0.0, glow=0.0):
    """glow: 해를 등진 면이 까맣게 죽지 않게 제 색으로 조금 빛나게 한다(먼 풍경이 대기 속에서 밝아 보이는 것)"""
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metallic
    if glow:
        b.inputs['Emission Color'].default_value = (*color, 1); b.inputs['Emission Strength'].default_value = glow
    return m

def add_box(bm, center, frame, sx, sy, sz):
    for v in bmesh.ops.create_cube(bm, size=1.0)['verts']:
        v.co = center + frame @ Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))

def add_segment(bm, p0, p1, thick):
    """두 점을 잇는 가는 막대(케이블)"""
    x = (p1 - p0); length = x.length; x.normalize()
    z = x.cross(D).normalized()
    add_box(bm, (p0 + p1) / 2, Matrix((x, D, z)).transposed(), length, thick, thick)

def finish(bm, name, mat):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob); me.materials.append(mat)
    return ob

# ───────── 바다 · 백사장 · 산책로 ─────────
def sea():
    bm = bmesh.new(); add_box(bm, at(4200, 0, SEA - .5), FRAME, 16000, 9000, 1.0)
    ob = finish(bm, 'sea', material('sea', lin('#0c2f47'), .06))
    nt = ob.data.materials[0].node_tree; b = nt.nodes['Principled BSDF']
    # 잔물결: 크기가 다른 무늬 둘을 겹쳐 수면을 살짝 울린다
    co = nt.nodes.new('ShaderNodeTexCoord')
    small = nt.nodes.new('ShaderNodeTexNoise'); small.inputs['Scale'].default_value = .55; small.inputs['Detail'].default_value = 5
    big = nt.nodes.new('ShaderNodeTexNoise'); big.inputs['Scale'].default_value = .045; big.inputs['Detail'].default_value = 3
    mix = nt.nodes.new('ShaderNodeMath'); mix.operation = 'ADD'
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .22; bump.inputs['Distance'].default_value = 1.2
    nt.links.new(co.outputs['Object'], small.inputs['Vector']); nt.links.new(co.outputs['Object'], big.inputs['Vector'])
    nt.links.new(small.outputs['Fac'], mix.inputs[0]); nt.links.new(big.outputs['Fac'], mix.inputs[1])
    nt.links.new(mix.outputs['Value'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    # 물가는 옥색, 멀어질수록 짙은 남색
    pos = nt.nodes.new('ShaderNodeNewGeometry')
    out = nt.nodes.new('ShaderNodeVectorMath'); out.operation = 'DOT_PRODUCT'; out.inputs[1].default_value = D
    nt.links.new(pos.outputs['Position'], out.inputs[0])
    depth = nt.nodes.new('ShaderNodeMapRange'); depth.inputs['From Min'].default_value = 62; depth.inputs['From Max'].default_value = 420
    nt.links.new(out.outputs['Value'], depth.inputs['Value'])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); nt.links.new(depth.outputs['Result'], ramp.inputs['Fac'])
    cr = ramp.color_ramp
    cr.elements[0].position = 0; cr.elements[0].color = (*lin('#8fd0cf'), 1)
    cr.elements[1].position = 1; cr.elements[1].color = (*lin('#123f63'), 1)
    cr.elements.new(.12).color = (*lin('#4fa7b8'), 1); cr.elements.new(.4).color = (*lin('#1f6690'), 1)
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])

def wavy_strip(d0, width, z, mat, name, wobble=1.6, length=3600, step=12):
    """해안선을 따라 살짝 구불거리는 띠(젖은 모래 · 파도 거품)"""
    bm = bmesh.new(); rows = []
    phase = random.uniform(0, 6)
    for i in range(int(length / step) + 1):
        t = -length / 2 + i * step
        off = wobble * (math.sin(t * .021 + phase) + .6 * math.sin(t * .053 + phase * 2) + .3 * random.uniform(-1, 1))
        rows.append((bm.verts.new(at(d0 + off, t, z)), bm.verts.new(at(d0 + off + width, t, z))))
    for (a, b), (c, d) in zip(rows, rows[1:]): bm.faces.new((a, c, d, b))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return finish(bm, name, mat)

def shore():
    bm = bmesh.new(); add_box(bm, at(-12, 0, SEA - .2), FRAME, 3600, 60, 1.4)       # 산책로 · 도로
    finish(bm, 'promenade', material('promenade', lin('#a7a299'), .9))
    bm = bmesh.new(); add_box(bm, at(41, 0, SEA - .35), FRAME, 3600, 46, 1.2)       # 백사장
    finish(bm, 'sand', material('sand', lin('#e2cfa9'), .95, glow=.12))
    wavy_strip(60, 9, SEA + .27, material('wet_sand', lin('#c2ab82'), .55, glow=.1), 'wet_sand', wobble=1.2)
    foam = material('foam', lin('#f4f8f8'), .7, glow=.5)
    wavy_strip(66.5, 2.4, SEA + .32, foam, 'foam_1', wobble=1.8); wavy_strip(75, 1.5, SEA + .06, foam, 'foam_2', wobble=2.6)
    wavy_strip(88, 1.0, SEA + .05, foam, 'foam_3', wobble=3.4); wavy_strip(106, .7, SEA + .05, foam, 'foam_4', wobble=4)

# ───────── 광안대교: 2층 트러스 상판 · 주탑 둘 · 주케이블과 행어 · 앵커 · 교각 ─────────
def bridge():
    d0, span, side, half = 820.0, 250.0, 460.0, 880.0      # 다리까지 거리, 주탑 자리(±), 앵커 자리(±), 양 끝
    low, top, cable_low, tower_top = SEA + 28, SEA + 36, SEA + 40, SEA + 105
    bm = bmesh.new()
    for z in (low, top): add_box(bm, at(d0, 0, z), FRAME, half * 2, 24, 1.2)                       # 위아래 상판
    t = -half
    while t <= half:                                                                              # 트러스 기둥
        for side_d in (-11.4, 11.4): add_box(bm, at(d0 + side_d, t, (low + top) / 2), FRAME, .9, .9, top - low)
        t += 12.5
    for tt in (-span, span):                                                                      # 주탑
        for side_d in (-13.5, 13.5): add_box(bm, at(d0 + side_d, tt, (SEA + tower_top) / 2), FRAME, 5.5, 4.5, tower_top - SEA)
        for z in (SEA + 46, SEA + 74, tower_top - 2): add_box(bm, at(d0, tt, z), FRAME, 5.0, 27, 4.0)
        add_box(bm, at(d0, tt, SEA + 2), FRAME, 34, 44, 6)
    def cable_z(t):
        a = abs(t)
        if a <= span: return cable_low + (tower_top - 2 - cable_low) * (a / span) ** 2
        s = (a - span) / (side - span)
        return (tower_top - 2) - (tower_top - 2 - top - 2) * s ** 1.15
    for side_d in (-12.2, 12.2):
        step, t = 10.0, -side
        while t < side - .01:
            add_segment(bm, at(d0 + side_d, t, cable_z(t)), at(d0 + side_d, t + step, cable_z(t + step)), 1.0)   # 주케이블
            t += step
        t = -side + 12.5
        while t < side:
            if abs(abs(t) - span) > 6: add_box(bm, at(d0 + side_d, t, (cable_z(t) + top) / 2), FRAME, .35, .35, max(.1, cable_z(t) - top))   # 행어
            t += 12.5
    for sign in (-1, 1):
        ta = sign * side                                                                           # 앵커(세모난 콘크리트 덩어리)
        verts = [bm.verts.new(at(d0 + dd, ta + tt, zz)) for dd in (-15, 15) for tt, zz in ((-24, SEA), (24, SEA), (0, SEA + 40))]
        a, b, c, d, e, f = verts
        for face in ((a, b, c), (d, f, e), (a, d, e, b), (b, e, f, c), (c, f, d, a)): bm.faces.new(face)
        tp = sign * 520.0
        while abs(tp) <= half:                                                                     # 접속교 교각
            add_box(bm, at(d0, tp, (SEA + low) / 2), FRAME, 5, 20, low - SEA)
            tp += sign * 55
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    finish(bm, 'bridge', material('bridge', hazed('#f4f5f5', .1), .5, glow=.42))

# ───────── 먼 풍경: 마린시티 고층 건물(왼쪽), 산 능선(오른쪽 · 뒤쪽) ─────────
def skyline():
    bm = bmesh.new()
    for _ in range(34):
        h = random.uniform(110, 300); w = random.uniform(28, 46)
        add_box(bm, at(1420 + random.uniform(-240, 240), -1120 + random.uniform(-300, 300), SEA + h / 2), FRAME, w, w * random.uniform(.8, 1.2), h)
    for _ in range(40):
        h = random.uniform(30, 90); w = random.uniform(30, 70)
        add_box(bm, at(1400 + random.uniform(-300, 300), -1300 + random.uniform(-700, 700), SEA + h / 2), FRAME, w, w, h)
    add_box(bm, at(1420, -1500, SEA + 2), FRAME, 1100, 700, 5)
    finish(bm, 'skyline', material('skyline', hazed('#aebccb', .5), .55, glow=.5))

def ridge(name, d0, t0, t1, height, color, haze, depth=500, seed=0):
    """능선: 해안선 방향으로 오르내리는 산줄기"""
    rnd = random.Random(seed); phases = [rnd.uniform(0, 6) for _ in range(4)]
    bm = bmesh.new(); rows = []
    n = int((t1 - t0) / 40)
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / n; u = i / n
        h = height * (.35 + .65 * math.sin(math.pi * u) ** .8) * (.62 + .2 * math.sin(u * 9 + phases[0]) + .12 * math.sin(u * 23 + phases[1]) + .06 * math.sin(u * 51 + phases[2]))
        rows.append((bm.verts.new(at(d0, t, SEA)), bm.verts.new(at(d0, t, SEA + max(4, h))), bm.verts.new(at(d0 + depth, t, SEA + max(4, h) * .7)), bm.verts.new(at(d0 + depth, t, SEA))))
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(3): bm.faces.new((r0[k], r1[k], r1[k + 1], r0[k + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    finish(bm, name, material(name, hazed(color, haze), .95, glow=.55))

def far():
    skyline()
    ridge('igidae', 900, 760, 3400, 230, '#6f8c78', .45, seed=1)       # 다리 오른쪽 끝에 이어지는 산
    ridge('hills_back', 2400, -3800, 200, 300, '#7f978f', .68, depth=900, seed=2)   # 마린시티 뒤 장산 쪽
    ridge('horizon_land', 5600, -600, 5200, 70, '#9fb2ba', .86, depth=600, seed=3)

# ───────── 하늘과 해 ─────────
def sky():
    world = bpy.data.worlds.new('sky'); scene.world = world
    try: world.use_nodes = True
    except Exception: pass
    nt = world.node_tree; bg = nt.nodes['Background']
    co = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(co.outputs['Generated'], sep.inputs['Vector'])
    up = nt.nodes.new('ShaderNodeMapRange'); up.inputs['From Min'].default_value = -1; up.inputs['From Max'].default_value = 1
    nt.links.new(sep.outputs['Z'], up.inputs['Value'])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); nt.links.new(up.outputs['Result'], ramp.inputs['Fac'])
    stops = [(0, '#0d2a40'), (.492, '#3e6a8c'), (.5, '#e9eef0'), (.52, '#bcd8ee'), (.6, '#7fb2e6'), (1, '#2f69c2')]
    cr = ramp.color_ramp
    cr.elements[0].position = 0; cr.elements[0].color = (*lin(stops[0][1]), 1)
    cr.elements[1].position = 1; cr.elements[1].color = (*lin(stops[-1][1]), 1)
    for pos, color in stops[1:-1]: cr.elements.new(pos).color = (*lin(color), 1)
    # 해 둘레의 따뜻한 번짐
    dot = nt.nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'; dot.inputs[1].default_value = SUN
    nt.links.new(co.outputs['Generated'], dot.inputs[0])
    clampd = nt.nodes.new('ShaderNodeMath'); clampd.operation = 'MAXIMUM'; clampd.inputs[1].default_value = 0
    nt.links.new(dot.outputs['Value'], clampd.inputs[0])
    def power(exp, gain):
        p = nt.nodes.new('ShaderNodeMath'); p.operation = 'POWER'; p.inputs[1].default_value = exp
        g = nt.nodes.new('ShaderNodeMath'); g.operation = 'MULTIPLY'; g.inputs[1].default_value = gain
        nt.links.new(clampd.outputs['Value'], p.inputs[0]); nt.links.new(p.outputs['Value'], g.inputs[0]); return g
    wide, disc = power(10, .28), power(900, 14)
    glow = nt.nodes.new('ShaderNodeMath'); glow.operation = 'ADD'
    nt.links.new(wide.outputs['Value'], glow.inputs[0]); nt.links.new(disc.outputs['Value'], glow.inputs[1])
    # 옅은 구름: 수평선 조금 위에서 중간 높이까지만
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 2.6; noise.inputs['Detail'].default_value = 7; noise.inputs['Roughness'].default_value = .62
    stretch = nt.nodes.new('ShaderNodeMapping'); stretch.inputs['Scale'].default_value = (1, 1, 3.4)
    nt.links.new(co.outputs['Generated'], stretch.inputs['Vector']); nt.links.new(stretch.outputs['Vector'], noise.inputs['Vector'])
    cloud = nt.nodes.new('ShaderNodeMapRange'); cloud.interpolation_type = 'SMOOTHSTEP'
    cloud.inputs['From Min'].default_value = .54; cloud.inputs['From Max'].default_value = .74
    nt.links.new(noise.outputs['Fac'], cloud.inputs['Value'])
    band = nt.nodes.new('ShaderNodeMapRange'); band.interpolation_type = 'SMOOTHSTEP'
    band.inputs['From Min'].default_value = .03; band.inputs['From Max'].default_value = .22
    nt.links.new(sep.outputs['Z'], band.inputs['Value'])
    amount = nt.nodes.new('ShaderNodeMath'); amount.operation = 'MULTIPLY'
    nt.links.new(cloud.outputs['Result'], amount.inputs[0]); nt.links.new(band.outputs['Result'], amount.inputs[1])
    soft = nt.nodes.new('ShaderNodeMath'); soft.operation = 'MULTIPLY'; soft.inputs[1].default_value = .6
    nt.links.new(amount.outputs['Value'], soft.inputs[0])
    clouds = nt.nodes.new('ShaderNodeMixRGB'); clouds.inputs['Color2'].default_value = (*lin('#ffffff'), 1)
    nt.links.new(soft.outputs['Value'], clouds.inputs['Fac']); nt.links.new(ramp.outputs['Color'], clouds.inputs['Color1'])
    warm = nt.nodes.new('ShaderNodeMixRGB'); warm.blend_type = 'ADD'; warm.inputs['Color2'].default_value = (*lin('#ffe6bf'), 1)
    nt.links.new(glow.outputs['Value'], warm.inputs['Fac']); nt.links.new(clouds.outputs['Color'], warm.inputs['Color1'])
    nt.links.new(warm.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.4; sun.color = lin('#fff0d8'); sun.angle = math.radians(2)
    so = bpy.data.objects.new('sun', sun); scene.collection.objects.link(so)
    so.rotation_euler = SUN.to_track_quat('Z', 'Y').to_euler()

def render(path, w, h, samples, pano):
    cam = bpy.data.cameras.new('cam')
    if pano:
        cam.type = 'PANO'
        try: cam.panorama_type = 'EQUIRECTANGULAR'
        except Exception: cam.cycles.panorama_type = 'EQUIRECTANGULAR'
    else:
        cam.lens_unit = 'FOV'; cam.angle = math.radians(75)
    co = bpy.data.objects.new('cam', cam); scene.collection.objects.link(co)
    co.location = (0, 0, EYE); cam.clip_end = 30000
    # 360° 그림은 가운데가 쇼룸의 +x 를 보게(방 안 360° 사진과 같은 방향), 확인용 그림은 바다 쪽을 보게 놓는다
    co.rotation_euler = (math.radians(90), 0, math.radians(-90)) if pano else (math.radians(88), 0, math.radians(45))
    scene.camera = co
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = w, h, 100
    scene.cycles.samples = samples
    scene.view_settings.view_transform = 'Standard'
    s = scene.render.image_settings
    try: s.media_type = 'IMAGE'
    except Exception: pass
    s.file_format = 'JPEG'; s.quality = 88
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(co, do_unlink=True)

sea(); shore(); bridge(); far(); sky()
render(os.path.join(OUT, 'preview_view.jpg'), 1280, 720, 32 if DRAFT else 96, pano=False)
if os.environ.get('ONLY_PREVIEW') != '1':
    render(os.path.join(OUT, 'sky.jpg'), 2048 if DRAFT else 4096, 1024 if DRAFT else 2048, 32 if DRAFT else 128, pano=True)
print('DONE')
