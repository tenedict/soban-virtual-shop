"""내려받은 재질을 방에 맞게 손질한다(fetch_assets.py 다음에 한 번).  python3 prepare_textures.py <에셋 폴더>
  proc/wall_diff.jpg        미장 벽을 더 밝고 덜 누렇게
  proc/marble_diff.jpg      대리석 밝기를 0.9배로(너무 흰 바닥은 빛을 과하게 되튕긴다)
  proc/marble_rough.jpg     대리석을 더 매끈하게
  proc/travertine_rough.jpg 트래버틴을 광택 없는 마감으로
  proc/sky.jpg              창밖 풍경을 4096 × 2048 로"""
import os, sys
from PIL import Image, ImageEnhance

src = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
os.chdir(src); os.makedirs('proc', exist_ok=True)

wall = ImageEnhance.Color(Image.open('textures/beige_wall_001/diff.jpg').convert('RGB')).enhance(.7)
Image.blend(wall, Image.new('RGB', wall.size, (246, 240, 230)), .5).save('proc/wall_diff.jpg', quality=90)
Image.open('textures/Marble019/diff.jpg').convert('RGB').point(lambda v: int(v * .9)).save('proc/marble_diff.jpg', quality=90)
Image.open('textures/Marble019/rough.jpg').convert('L').point(lambda v: int(v * .55)).save('proc/marble_rough.jpg', quality=90)
Image.open('textures/Travertine009/rough.jpg').convert('L').point(lambda v: min(255, int(v * .6 + 135))).save('proc/travertine_rough.jpg', quality=90)
Image.open('hdri/symmetrical_garden_02_tonemapped.jpg').resize((4096, 2048), Image.LANCZOS).save('proc/sky.jpg', quality=82)
print('done')
