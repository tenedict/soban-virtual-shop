"""북커버 사진을 펴서 모델에 입힐 그림 한 장(앞 · 뒤 · 등 · 책장)과 요철 그림을 만든다.
  python3 book_cover_texture.py <정리한 사진.png> <내보낼 폴더>
뒷면 사진이 없으므로 뒷면은 앞면의 천과 박음질에서 레이스 · 단추만 걷어 만든다.
"""
import json, os, random, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
A = 2048
FRONT, BACK = (0, 0, 1000, 1300), (1024, 0, 2024, 1300)
SPINE, PAGES, FABRIC = (0, 1324, 1300, 1664), (0, 1680, 1300, 1880), (1330, 1330, 2030, 2030)


def perspective(im, quad, size, box):
    A_, b = [], []
    for (x, y), (u, v) in zip(box, quad):
        A_.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A_.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    M = [r + [c] for r, c in zip(A_, b)]
    for i in range(8):
        p = max(range(i, 8), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        for r in range(8):
            if r != i:
                f = M[r][i] / M[i][i]
                M[r] = [a - f * c for a, c in zip(M[r], M[i])]
    return im.transform(size, Image.PERSPECTIVE, [M[i][8] / M[i][i] for i in range(8)], Image.BICUBIC)


def band_mask(size, top, bottom, feather):
    m = Image.new('L', size, 0)
    ImageDraw.Draw(m).rectangle((0, top + feather, size[0], bottom - feather), fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather * .6))


# 1) 표지를 똑바로 편다(사진의 네 모서리 → 직사각형). 위쪽 박음질이 잘리지 않게 24px 여유를 둔다
photo = Image.open(src).convert('RGB')
rect = perspective(photo, [(181, 309), (583, 194), (800, 636), (392, 808)], (1040, 1360),
                   [(0, 24), (1040, 24), (1040, 1360), (0, 1360)])
front = rect.crop((0, 20, 1026, 1286)).resize((FRONT[2], FRONT[3]), Image.LANCZOS)

# 단추 자리(앞면 그림 기준)
bx, by, br = 918, 661, 72

# 2) 모서리에 남은 회색 바닥을 천으로 메운다(단추는 밝아도 건드리지 않는다)
cloth = front.crop((90, 70, 890, 420)).resize(front.size, Image.BICUBIC)
bright = front.convert('L').point(lambda v: 255 if v > 92 else 0)
ImageDraw.Draw(bright).ellipse((bx - br - 14, by - br - 14, bx + br + 14, by + br + 14), fill=0)
bright = bright.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(3))
front = Image.composite(cloth, front, bright)

# 천만 자주빛 보라로 옮긴다. 쇼룸의 따뜻한 조명이 파랑을 약 30% 깎아 붉은 갈색으로 보이게 하므로 그만큼 미리 올린다. 금속 단추는 그대로 둔다
r, g, b = front.split()
plum = Image.merge('RGB', (r, g.point(lambda v: min(255, int(v * .96))), b.point(lambda v: min(255, int(v * 1.6)))))
metal = Image.new('L', front.size, 0)
ImageDraw.Draw(metal).ellipse((bx - br, by - br, bx + br, by + br), fill=255)
front = Image.composite(front, plum, metal.filter(ImageFilter.GaussianBlur(1.5)))

# 3) 뒷면: 레이스 띠 자리를 위 · 아래의 민무늬 천으로 덮는다
back = front.copy()
upper = front.crop((0, 90, 1000, 410))
lower = front.crop((0, 900, 1000, 1190))
for patch, top in ((upper, 400), (lower, 620)):
    layer = back.copy(); layer.paste(patch, (0, top))
    back = Image.composite(layer, back, band_mask(back.size, top, top + patch.height, 26))

# 4) 등: 앞면 왼쪽을 뒤집어 이어 붙여 레이스가 등까지 이어지게 한다
spine = front.crop((70, 0, 410, 1300)).transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90)

# 5) 책장 단면: 종이 결
random.seed(8)
pages = Image.new('RGB', (PAGES[2] - PAGES[0], PAGES[3] - PAGES[1]), (196, 186, 168))
d = ImageDraw.Draw(pages)
for y in range(pages.height):
    if y % 3 == 0:
        t = random.randint(-22, 8)
        d.line((0, y, pages.width, y), fill=(184 + t, 174 + t, 156 + t))

atlas = Image.new('RGB', (A, A), front.resize((1, 1), Image.BOX).getpixel((0, 0)))
atlas.paste(front, FRONT[:2]); atlas.paste(back, BACK[:2]); atlas.paste(spine, SPINE[:2]); atlas.paste(pages, PAGES[:2])
atlas.paste(front.crop((120, 60, 820, 420)).resize((700, 700), Image.BICUBIC), FABRIC[:2])
atlas.save(os.path.join(out, 'book_color.png'))

# 6) 밝기에서 요철을 뽑는다: 레이스 실과 박음질이 도드라지게
L = atlas.convert('L').filter(ImageFilter.GaussianBlur(1.1))
dx = L.filter(ImageFilter.Kernel((3, 3), (1, 0, -1, 2, 0, -2, 1, 0, -1), scale=2, offset=128))
dy = L.filter(ImageFilter.Kernel((3, 3), (-1, -2, -1, 0, 0, 0, 1, 2, 1), scale=2, offset=128))
Image.merge('RGB', (dx, dy, Image.new('L', (A, A), 235))).save(os.path.join(out, 'book_normal.png'))

json.dump({'atlas': A, 'front': FRONT, 'back': BACK, 'spine': SPINE, 'pages': PAGES, 'fabric': FABRIC,
           'button': [bx / FRONT[2], by / FRONT[3], br / FRONT[2]]}, open(os.path.join(out, 'book.json'), 'w'))
print('fabric', front.resize((1, 1), Image.BOX, box=(120, 80, 880, 400)).getpixel((0, 0)),
      'back', back.resize((1, 1), Image.BOX, box=(120, 80, 880, 1200)).getpixel((0, 0)))
