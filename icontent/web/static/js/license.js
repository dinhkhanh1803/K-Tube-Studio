/* K-Tube Studio - Bản quyền */
import { el, icon } from './core.js';

export function showLicenseGate(st) {
  // Bản quyền K-Tube Studio luôn mở
}

export function licensePanel(st) {
  return el('div', { class: 'lic-panel' },
    el('div', { class: 'lic-status ok' },
      icon('check'),
      el('b', { text: 'K-Tube Studio Pro - Bản quyền vĩnh viễn (Trọn đời)' })),
    el('div', { class: 'small dim', text: 'Toàn quyền sử dụng, tùy biến và phát triển không giới hạn thiết bị.' })
  );
}

export function renewBanner(st) {
  return null;
}
