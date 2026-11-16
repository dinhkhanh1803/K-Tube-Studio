/* K-Tube Studio - Giới thiệu */
import { api, el, icon } from './core.js';
import { openChangelog } from './changelog.js';

let about = null;
async function loadAbout() {
  if (!about) about = await api('GET', '/api/about');
  return about;
}

export async function coffeeCard() {
  return el('div', { class: 'coffee', style: 'display:none' });
}

export async function openCoffee() {
  // Không cần mở popup donate
}

export const coffeeLine = () => el('span', { hidden: true });

export async function viewAbout(main) {
  main.append(
    el('div', { class: 'page-head' },
      el('div', { class: 'page-head-text' }, el('div', { class: 'eyebrow', text: 'Giới thiệu' }), el('h1', { text: 'K-Tube Studio' }),
        el('p', { text: 'Nền tảng AI tự động tạo, dịch thuật, lồng tiếng và dựng video đa nền tảng, chạy trực tiếp trên máy của bạn.' }))),
    el('div', { class: 'about-grid' },
      el('div', { class: 'panel' }, el('h3', { text: 'Dữ liệu và quyền riêng tư' }),
        el('p', { class: 'muted', text: 'Tất cả video, phụ đề, mô hình âm thanh và API keys đều được lưu trữ hoàn toàn trên máy tính của bạn.' })),
      el('div', { class: 'panel' }, el('h3', { text: 'Bản quyền phần mềm' }),
        el('p', { class: 'muted', text: 'K-Tube Studio Pro - Phiên bản không giới hạn, toàn quyền sử dụng và tùy biến theo nhu cầu công việc của bạn.' })),
      el('div', { class: 'panel' }, el('h3', { text: 'Lịch sử phiên bản' }),
        el('p', { class: 'muted', text: 'Xem lại toàn bộ tính năng và cải tiến đã được cập nhật qua các phiên bản.' }),
        el('button', { class: 'btn btn-primary btn-sm', style: { marginTop: '8px' }, onclick: () => openChangelog() }, icon('clock'), ' Xem lịch sử cập nhật qua các ver')),
      el('div', { class: 'panel' }, el('h3', { text: 'Công nghệ tích hợp' }),
        el('p', { class: 'muted', text: 'Tích hợp yt-dlp, faster-whisper, RapidOCR, VieNeu-TTS, FFmpeg, OpenCV cùng các mô hình trí tuệ nhân tạo tiên tiến.' }))));
  return null;
}
