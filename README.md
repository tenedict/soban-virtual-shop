# OHANAE 가상 쇼룸

오하나에의 실제 상품을 실사형 두 개의 공간에서 둘러볼 수 있는 2D 가상 쇼룸입니다.

- 테이블 매트와 코스터를 전시한 Room A
- 숄더백, 티슈 케이스, 파우치, 북커버와 랜턴 커버를 전시한 Room B
- 바닥 화살표를 통한 공간 이동
- 브라우저 저장소를 사용하는 장바구니
- 각 상품의 오하나에 공식 판매 페이지 연결

GitHub Pages에서 정적 사이트로 배포됩니다.

## 3D 쇼룸 (시제품)

`3d/` 는 같은 상품을 1인칭으로 걸어 다니며 보는 3D 시제품입니다. 바닥을 누르면 그 자리로 걸어가고, 상품을 누르면 다가가서 엽니다.

- `3d/index.html` — 쇼룸. 무엇을 어디에 놓는지는 `3d/layout.json` 이 정합니다. 상품 이름 · 가격 · 크기 · 소개 글은 [ohanae.kr](https://ohanae.kr) 의 것을 그대로 담았고, 구매는 그 사이트의 상품 페이지로 넘깁니다.
  효과음(발소리 · 상품 창 · 담기 · 방 옮기기)은 소리 파일 없이 브라우저가 그때그때 만들어 냅니다.
- `3d/admin.html` — 관리자 페이지. 지도에서 물건을 끌어 놓고, 상품과 3D 모델(.glb)을 관리합니다.
  고친 내용은 그 브라우저의 초안으로만 남고, 「내보내기」로 받은 `layout.json` 을 `3d/` 에 올려야 모두에게 보입니다.
- `3d/models/` — 올려 둔 3D 모델 파일.
- `3d/space.js` · `3d/store.js` — 쇼룸과 관리자 페이지가 같이 쓰는 공간 정보와 저장 코드.

### 방은 Blender 로 만듭니다

방 · 가구 · 소품은 코드로 그리지 않고, Blender 에서 실제 재질로 만든 뒤 빛(햇빛 · 조명 · 벽에 번지는 간접광)을 미리 계산해 그림으로 구워 둡니다.
쇼룸은 그 결과(`3d/assets/`)를 불러오기만 해서, 실시간 조명 계산이 없고 폰에서도 가볍습니다.

- `3d/assets/room.glb` — 방의 모양과 재질 · `lm_*.jpg` — 구운 빛 · `env_*.hdr` — 방마다 찍은 360° 사진(반사용) · `sky.jpg` — 창밖 풍경(3D 로 지은 광안리)
- `3d/blender/build_room.py` — 방을 짓고 굽는 스크립트. 가구 자리는 `space.js` 에서 뽑은 `blender/space.json` 을 따릅니다.

방을 고쳐 다시 만들려면(Blender 5 이상, 15분쯤 걸립니다):

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b -P 3d/blender/build_room.py
npx @gltf-transform/cli@4 meshopt 3d/assets/room.glb 3d/assets/room.glb    # 모양 데이터를 압축(7MB → 4MB)
```

원본 에셋은 `3d/blender/fetch_assets.py` 로 받고 `prepare_textures.py` 로 손질합니다. `QUALITY=draft` 를 앞에 붙이면 2분 안에 거친 결과가 나옵니다. 스크립트는 내려받아 둔 원본 에셋 폴더(`SHOWROOM_SRC`, 기본값은 스크립트 안에 있음)를 읽습니다.

창밖 풍경은 사진이 아니라 `3d/blender/build_view.py` 가 지은 3D 광안리(바다 · 백사장 · 광안대교 · 마린시티 · 산)를 360° 로 찍은 그림입니다. 다시 만들려면 `Blender -b -P 3d/blender/build_view.py` (약 1분).

재질과 소품은 모두 CC0(자유 사용)입니다 — [Poly Haven](https://polyhaven.com)의 재질 · 가구 · 화분 · 화병 · 등 · 하늘 사진, [ambientCG](https://ambientcg.com)의 대리석 · 트래버틴 · 러그.
