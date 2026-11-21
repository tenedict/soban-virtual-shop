"""다듬은 모델(.glb)을 앞 · 비스듬한 쪽에서 찍어 한눈에 확인한다.
  Blender -b -P preview_model.py -- <찍은 그림을 둘 폴더> <모델.glb> [<모델.glb> ...]
모델마다 <이름>_front.png, <이름>_side.png 두 장이 나온다. 앞은 쇼룸에서 손님을 보는 쪽(Blender 의 -Y)이다.
"""
import bpy, sys, os, math
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
out, files = args[0], args[1:]
os.makedirs(out, exist_ok=True)

for path in files:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
    sc.render.resolution_x = sc.render.resolution_y = 480
    sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new('w'); sc.world.color = (.55, .55, .55)
    pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type == 'MESH' for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    mid, r = (lo + hi) / 2, (hi - lo).length / 2
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 60
    name = os.path.splitext(os.path.basename(path))[0]
    for tag, d in (('front', Vector((0, -1, .18))), ('side', Vector((.75, -.6, .5)))):
        d = d.normalized()
        cam.location = mid + d * r * 3.6
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(out, f'{name}_{tag}.png')
        bpy.ops.render.render(write_still=True)
    print('PREVIEW', name, 'size', tuple(round(v, 3) for v in (hi - lo)))
