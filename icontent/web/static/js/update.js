/* Phiên bản và cập nhật (máy chủ: icontent/updates.py). Số phiên bản ở chân thanh bên, chấm vàng khi có bản mới.
   Bản cài bằng Setup.exe: bấm Cập nhật là tải bộ cài, cài im lặng rồi tự mở lại. Bản chạy từ mã nguồn: chỉ có đường dẫn tải. */
import { $, api, confirmDialog, el, fmtSize, icon, modalHead, openModal, put, showError, toast } from './core.js';

let st = null;
const listeners = new Set();
const TOAST_KEY = 'ic.upd.toast';

function emit() { listeners.forEach((f) => { try { f(st); } catch (_) { /* trang đã đóng */ } }); paintRail(); }

export async function refresh(check = false) {
  st = await api(check ? 'POST' : 'GET', check ? '/api/update/check' : '/api/update');
  emit();
  return st;
}

function paintRail() {
  const b = $('#ver-btn');
  if (!b || !st) return;
  b.querySelector('.ver-num').textContent = 'v' + st.current;
  b.classList.toggle('has-update', !!st.available);
  b.title = st.available ? `Đã có iContent ${st.latest}. Bấm để cập nhật` : `iContent ${st.current}. Bấm để kiểm tra bản mới`;
}

const pct = (d) => (d.total ? Math.min(100, Math.round((d.done / d.total) * 100)) : 0);

/** Khung phiên bản dùng chung cho hộp thoại và trang Giới thiệu */
export function updatePanel() {
  const box = el('div', { class: 'upd' });
  let timer = null;
  const stop = () => { clearInterval(timer); timer = null; };

  const draw = () => {
    if (!box.isConnected && timer) { stop(); listeners.delete(draw); return; }
    if (!st) { put(box, el('p', { class: 'muted', text: 'Đang đọc phiên bản…' })); return; }
    const head = el('div', { class: 'upd-head' },
      el('div', {}, el('div', { class: 'upd-cur' }, 'Đang dùng ', el('b', { class: 'num', text: 'iContent ' + st.current })),
        el('div', { class: 'small dim', text: st.checked_at ? 'Kiểm tra lần cuối ' + new Date(st.checked_at * 1000).toLocaleString('vi-VN') : 'iContent tự kiểm tra bản mới khi mở và mỗi 12 giờ' })),
      el('button', { class: 'btn btn-sm', onclick: (e) => checkBtn(e.currentTarget) }, icon('refresh'), 'Kiểm tra cập nhật'));
    const kids = [head];
    if (st.available) {
      const d = st.dl || {};
      const action = [];
      if (!st.can_install) {
        action.push(el('a', { class: 'btn btn-primary', href: st.download_url || st.url, target: '_blank', rel: 'noopener' }, icon('download'), 'Tải bộ cài mới'),
          el('p', { class: 'small dim', text: 'Tải về rồi chạy file cài, chọn cài đè lên thư mục cũ. Video, cài đặt và key được giữ nguyên.' }));
      } else if (d.state === 'downloading') {
        action.push(el('div', { class: 'upd-bar' }, el('i', { style: { width: pct(d) + '%' } })),
          el('p', { class: 'small dim num', text: `Đang tải bộ cài ${fmtSize(d.done)}${d.total ? ' / ' + fmtSize(d.total) : ''} (${pct(d)}%)` }));
        if (!timer) timer = setInterval(() => refresh().catch(stop), 800);
      } else if (d.state === 'ready') {
        stop();
        action.push(el('button', { class: 'btn btn-primary', onclick: (e) => install(e.currentTarget) }, icon('check'), 'Cài và mở lại iContent'),
          el('p', { class: 'small dim', text: 'iContent sẽ đóng, cài bản mới (thường dưới 1 phút) rồi tự mở lại. Video, cài đặt, key và kích hoạt giữ nguyên.' }));
      } else {
        stop();
        if (d.state === 'error') action.push(el('p', { class: 'small upd-err', text: d.error }));
        action.push(el('button', { class: 'btn btn-primary', onclick: (e) => download(e.currentTarget) }, icon('download'),
          d.state === 'error' ? 'Tải lại bộ cài' : `Cập nhật lên ${st.latest}`),
        el('p', { class: 'small dim', text: (st.size ? `Bộ cài ${fmtSize(st.size)}. ` : '') + 'Tải xong iContent hỏi trước khi cài, việc đang làm không bị ngắt.' }));
      }
      kids.push(el('div', { class: 'upd-new' },
        el('div', { class: 'upd-new-t' }, icon('download'), el('b', { text: `Đã có iContent ${st.latest}` })),
        st.notes ? el('pre', { class: 'upd-notes', text: st.notes }) : null,
        el('div', { class: 'upd-act' }, action)));
    } else if (st.checked_at && !st.error) {
      kids.push(el('p', { class: 'upd-ok' }, icon('check'), 'Bạn đang dùng bản mới nhất.'));
    } else if (st.error) {
      kids.push(el('p', { class: 'small dim', text: 'Chưa kiểm tra được (có thể do mất mạng). iContent sẽ tự thử lại sau.' }));
    }
    put(box, ...kids);
  };

  async function checkBtn(btn) {
    btn.disabled = true; btn.classList.add('is-busy');
    try {
      await refresh(true);
      if (!st.available && !st.error) toast('Bạn đang dùng bản mới nhất', 'success');
    } catch (e) { showError(e); } finally { btn.disabled = false; btn.classList.remove('is-busy'); }
  }
  async function download(btn) {
    btn.disabled = true;
    try { st = await api('POST', '/api/update/download'); emit(); } catch (e) { btn.disabled = false; showError(e); }
  }
  async function install(btn, force = false) {
    btn.disabled = true;
    try {
      await api('POST', '/api/update/install', { force });
      put(box, el('div', { class: 'upd-going' }, el('span', { class: 'spinner' }),
        el('div', {}, el('b', { text: `Đang cài iContent ${st.latest}…` }),
          el('p', { class: 'small dim', text: 'Cửa sổ này sẽ tự đóng. Cài xong iContent tự mở lại, thường dưới 1 phút.' }))));
    } catch (e) {
      btn.disabled = false;
      if (e.status === 409 && await confirmDialog('Đang có video xử lý', e.message, { okText: 'Vẫn cập nhật', danger: true })) install(btn, true);
      else if (e.status !== 409) showError(e);
    }
  }

  listeners.add(draw);
  draw();
  refresh().catch(() => {});      // mở hộp là đọc lại: có thể máy chủ vừa kiểm tra xong
  return box;
}

export function openUpdate() {
  const m = openModal([modalHead('download', 'Phiên bản và cập nhật', () => m), el('div', { class: 'modal-body' }, updatePanel())], { cls: 'modal-upd' });
}

/** Gắn nút phiên bản ở chân thanh bên, rồi đọc kết quả kiểm tra (máy chủ tự kiểm tra 20 giây sau khi mở) */
export function initUpdate() {
  const b = $('#ver-btn');
  if (b) b.addEventListener('click', openUpdate);
  const poll = async () => {
    try { await refresh(); } catch (_) { return; }
    if (st.available) {
      let seen = '';
      try { seen = localStorage.getItem(TOAST_KEY) || ''; } catch (_) { /* trang riêng tư */ }
      if (seen !== st.latest) {
        try { localStorage.setItem(TOAST_KEY, st.latest); } catch (_) { /* bỏ qua */ }
        toast(`Đã có iContent ${st.latest}. Cập nhật chỉ mất khoảng 1 phút, video và cài đặt giữ nguyên.`, 'info',
          { actions: [{ label: 'Xem bản mới', primary: true, onClick: openUpdate }] });
      }
    }
  };
  poll();
  setTimeout(poll, 30000);      // lần kiểm tra đầu của máy chủ chạy sau khi mở 20 giây
  setInterval(poll, 3 * 3600 * 1000);
}
