"""CC0 에셋 내려받기 — Poly Haven(재질 · 모델 · HDRI)과 ambientCG(대리석 · 트래버틴 · 러그).
에셋을 둘 폴더에서 돌린다:  cd <에셋 폴더> && python3 fetch_assets.py   (약 95MB)"""
import json, os, sys, urllib.request, zipfile, io
UA = {'User-Agent': 'Mozilla/5.0 (showroom prototype asset fetch)'}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
def save(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0: return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(get(url)); print('  +', path, os.path.getsize(path) // 1024, 'KB')

PH_TEX = {'beige_wall_001': '1k', 'oak_veneer_01': '1k', 'rough_linen': '1k'}
PH_MODELS = ['mid_century_lounge_chair', 'side_table_01', 'ceramic_vase_01', 'ceramic_vase_02', 'ceramic_vase_04',
             'potted_plant_02', 'potted_plant_04', 'wicker_basket_01', 'wooden_bowl_01', 'modern_ceiling_lamp_01']
ACG = {'Marble019': '2K', 'Travertine009': '1K', 'Carpet016': '1K'}
HDRI = 'symmetrical_garden_02'

for name, res in PH_TEX.items():
    print('texture', name)
    files = json.loads(get(f'https://api.polyhaven.com/files/{name}'))
    for key, out in (('Diffuse', 'diff'), ('nor_gl', 'nor'), ('Rough', 'rough')):
        if key in files: save(files[key][res]['jpg']['url'], f'textures/{name}/{out}.jpg')
        else: print('  (no', key, ')', list(files.keys()))
for name in PH_MODELS:
    print('model', name)
    files = json.loads(get(f'https://api.polyhaven.com/files/{name}'))
    g = files['gltf']['1k']['gltf']
    save(g['url'], f'models/{name}/{name}.gltf')
    for rel, inc in g.get('include', {}).items(): save(inc['url'], f'models/{name}/{rel}')
for name, res in ACG.items():
    print('ambientCG', name)
    d = f'textures/{name}'
    if not os.path.exists(f'{d}/diff.jpg'):
        z = zipfile.ZipFile(io.BytesIO(get(f'https://ambientcg.com/get?file={name}_{res}-JPG.zip')))
        os.makedirs(d, exist_ok=True)
        for n in z.namelist():
            for key, out in (('_Color.', 'diff'), ('_NormalGL.', 'nor'), ('_Roughness.', 'rough')):
                if key in n: open(f'{d}/{out}.jpg', 'wb').write(z.read(n)); print('  +', f'{d}/{out}.jpg')
print('hdri', HDRI)
files = json.loads(get(f'https://api.polyhaven.com/files/{HDRI}'))
save(files['hdri']['2k']['hdr']['url'], f'hdri/{HDRI}_2k.hdr')
save(files['tonemapped']['url'], f'hdri/{HDRI}_tonemapped.jpg')
print('done')
