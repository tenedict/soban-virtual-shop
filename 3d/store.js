// 배치 정보를 읽고 쓰는 곳 — 쇼룸과 관리자 페이지가 같이 쓴다.
// 공개본은 layout.json, 관리자 페이지에서 고치는 중인 것은 이 브라우저에만 남는 초안이다.
export const DRAFT_KEY = 'ohanae-3d-draft';

export async function loadPublished() {
  const res = await fetch('layout.json', { cache: 'no-store' });
  if (!res.ok) throw new Error('layout.json 을 불러오지 못했어요');
  return res.json();
}
export function readDraft() { try { return JSON.parse(localStorage.getItem(DRAFT_KEY)); } catch (_) { return null; } }
export function writeDraft(layout) { localStorage.setItem(DRAFT_KEY, JSON.stringify(layout)); }
export function clearDraft() { try { localStorage.removeItem(DRAFT_KEY); } catch (_) {} }
export async function loadLayout(useDraft) { return (useDraft && readDraft()) || loadPublished(); }

// 관리자 페이지에서 추가한 3D 모델 파일(.glb)은 용량이 커서 IndexedDB 에 둔다
function open() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('ohanae-3d', 1);
    req.onupgradeneeded = () => req.result.createObjectStore('models');
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function run(mode, work) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('models', mode);
    const req = work(tx.objectStore('models'));
    tx.oncomplete = () => resolve(req.result);
    tx.onerror = () => reject(tx.error);
  });
}
export const putModel = (name, blob) => run('readwrite', s => s.put(blob, name));
export const getModel = name => run('readonly', s => s.get(name));
export const listLocalModels = () => run('readonly', s => s.getAllKeys());
export const deleteModel = name => run('readwrite', s => s.delete(name));

// 이 브라우저에 추가해 둔 파일이 있으면 그것을, 없으면 올려 둔 models/ 폴더의 파일을 쓴다
export async function modelUrl(name) {
  try { const blob = await getModel(name); if (blob) return URL.createObjectURL(blob); } catch (_) {}
  return 'models/' + encodeURIComponent(name);
}
