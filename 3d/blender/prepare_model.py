"""사진에서 만든 3D 모델(.glb)을 쇼룸에 놓기 좋게 다듬는다.
  Blender -b -P prepare_model.py -- <받은 파일.glb> <../models/이름.glb> [삼각형 수=12000] [그림 크기=1024]

AI 가 사진 한 장으로 만든 모델은 천도 가죽처럼 번들거리게 나오고 파일이 크다(10MB 안팎). 여기서
  - 번들거림을 없애 천처럼 보이게 하고(거칠기를 높이고, 요철은 절반만),
  - 삼각형 수와 그림 크기를 줄이고,
  - 밑바닥 가운데가 원점에 오게 놓는다.
그 뒤 `npx @gltf-transform/cli@4 meshopt <파일> <파일>` 로 한 번 더 압축한다.
"""
import bpy, sys, os
from mathutils import Vector, Matrix

args = sys.argv[sys.argv.index('--') + 1:]
src, dst = args[0], args[1]
tris_target = int(args[2]) if len(args) > 2 else 12000
tex_size = int(args[3]) if len(args) > 3 else 1024

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
bpy.context.view_layer.update()
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in meshes:
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = Matrix.Identity(4); o.data.transform(mw)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
ob = meshes[0]

# 삼각형 수 줄이기
tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
if tris > tris_target:
    mod = ob.modifiers.new('decimate', 'DECIMATE'); mod.ratio = tris_target / tris
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    old = ob.data; ob.modifiers.clear(); ob.data = me; bpy.data.meshes.remove(old)
after = sum(len(p.vertices) - 2 for p in ob.data.polygons)

# 밑바닥 가운데를 원점으로
cos = [v.co for v in ob.data.vertices]
lo = Vector((min(c.x for c in cos), min(c.y for c in cos), min(c.z for c in cos)))
hi = Vector((max(c.x for c in cos), max(c.y for c in cos), max(c.z for c in cos)))
ob.data.transform(Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))

# 천 질감: 금속성 · 번들거림을 걷고, 요철은 절반만
for slot in ob.material_slots:
    nt = slot.material.node_tree; b = nt.nodes.get('Principled BSDF')
    if not b: continue
    for name, value in (('Roughness', .88), ('Metallic', 0.0)):
        for link in list(b.inputs[name].links): nt.links.remove(link)
        b.inputs[name].default_value = value
    for n in nt.nodes:
        if n.type == 'NORMAL_MAP': n.inputs['Strength'].default_value = .5
for img in bpy.data.images:
    if img.size[0] > tex_size: img.scale(tex_size, int(tex_size * img.size[1] / img.size[0]))

os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', use_selection=True, export_apply=True,
                          export_image_format='WEBP', export_image_quality=82, export_yup=True)
print(f'DONE tris {tris} -> {after}  size {tuple(round(v, 3) for v in (hi - lo))}  {os.path.getsize(dst) // 1024} KB')
