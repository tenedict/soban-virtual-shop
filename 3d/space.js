// 매장 공간의 고정된 부분 — 쇼룸(index.html)과 관리자 페이지(admin.html)가 같이 쓴다. 단위는 m.
// Room A: z 0 ~ 8, Room B: z -8 ~ 0, 폭 x -4 ~ 4. 두 방 사이 벽(z = 0)에 문(|x| < DOOR).
export const W = 4, DEPTH = 8, H = 3.2, DOOR = 0.9;

// kind: table = 다리 있는 테이블, block = 통으로 된 대리석 장. h = 윗면 높이
export const FURNITURE = [
  { id: 'tableA', kind: 'table', x: 0, z: 3.6, w: 2.8, d: 1.2, h: .76, label: 'Room A 테이블' },
  { id: 'counterA', kind: 'block', x: 3.35, z: 5.3, w: .9, d: 2.0, h: 1.04, label: '포장 카운터' },
  { id: 'shelfA', kind: 'block', x: -3.6, z: 1.6, w: .7, d: 1.8, h: .9, label: '낮은 장' },
  { id: 'tableB', kind: 'table', x: 0, z: -4, w: 2.2, d: 1.1, h: .76, label: 'Room B 테이블' },
  { id: 'sideB', kind: 'table', x: 3.2, z: -2.6, w: .9, d: 1.4, h: .8, label: '옆 테이블' },
  { id: 'lowB', kind: 'block', x: -.6, z: -7.45, w: 1.8, d: .7, h: .62, label: '낮은 수납장' }
];
export const PLANTS = [[-3.4, 7.4], [3.4, -7.3], [3.4, 1.0]];
// 걸어서 지나갈 수 없는 소품(라운지 의자 · 옆 탁자 · 바구니). 모양은 Blender 에서 만든 방(assets/room.glb)에 들어 있다
export const DECOR_BLOCKS = [
  { x: -2.75, z: 6.55, w: 1.0, d: 1.0, label: '라운지 의자' },
  { x: -3.4, z: 5.55, w: .55, d: .55, label: '옆 탁자' },
  { x: 3.35, z: -6.0, w: .5, d: .5, label: '바구니' }
];

// 바닥에 놓은 물건 밑에 저절로 생기는 받침대
export const PLINTH = { w: .42, h: .9 };

export const furnitureAt = (x, z) => FURNITURE.find(f => Math.abs(x - f.x) <= f.w / 2 && Math.abs(z - f.z) <= f.d / 2) || null;
export const roomOf = z => (z >= 0 ? 'A' : 'B');
