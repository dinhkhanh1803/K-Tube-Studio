/* K-Tube Studio - Lịch sử cập nhật qua các phiên bản (Changelog) */
import { $, el, icon, modalHead, openModal } from './core.js';
import { openUpdate } from './update.js';

export const CHANGELOG_DATA = [
  {
    version: '0.6.3',
    date: '15/11/2026',
    tag: 'Bản mới nhất',
    tagColor: 'var(--color-primary)',
    badge: 'Mới',
    highlights: [
      {
        title: '🎬 Kho Phim Bản Quyền Internet Archive (archive.org)',
        desc: 'Tích hợp trực tiếp kho phim Public Domain và CC BY vào tab Khám phá. Duyệt, tìm kiếm và 1-click tải trọn bộ phim kinh điển (Phim truyện, Hài, Kinh dị, Hoạt hình, Phim tài liệu, Blender 3D...) an toàn bản quyền để lồng tiếng / reup.'
      },
      {
        title: '🎵 Tách Nhạc Nền Bằng UVR MDX-Net ONNX',
        desc: 'Viết lại toàn bộ thuật toán STFT và lọc âm bằng NumPy thuần chạy trực tiếp trên ONNX Runtime (UVR-MDX-NET-Inst_HQ_3.onnx, 67 MB). Hoàn toàn không cần PyTorch hay audio-separator (nhẹ hơn 95%, không còn lỗi "chưa cài audio-separator").'
      },
      {
        title: '🌐 Tối ưu nhận diện & dịch cho chữ Latinh',
        desc: 'Bổ sung hệ số LATIN_CHAR_FACTOR = 2.5 cho video tiếng Anh, Pháp, Tây Ban Nha... tránh câu thoại bị cắt vụn, bản dịch liền mạch tự nhiên. Tự động nhận diện ngôn ngữ gốc (src_lang) để dịch đa chiều.'
      },
      {
        title: '⏱️ Cơ chế thăm dò AI tự động (_offline_with_ai_probe)',
        desc: 'Khi dịch phim dài, nếu gặp lúc Gemini/Claude quá tải, hệ thống tự động gọi thử lại AI chính mỗi 90s thay vì rớt toàn bộ phim sang dịch offline.'
      },
      {
        title: '🔍 QC thông minh cho phim dài',
        desc: 'Tự động nhận diện video dài (FILM_MIN = 1200s), không bắt lỗi sai các đoạn đen chuyển cảnh hoặc khoảng lặng âm thanh tự nhiên của phim truyện.'
      }
    ]
  },
  {
    version: '0.6.2',
    date: '14/11/2026',
    tag: 'K-Tube Studio Pro AI',
    tagColor: '#10b981',
    badge: 'Siêu nâng cấp',
    highlights: [
      {
        title: '🎙️ Engine Giọng Đọc CapCut TTS 24 Giọng Hot Trend',
        desc: 'Tích hợp trọn bộ 24 giọng đọc TikTok/CapCut hot trend (Thanh Niên Tự Tin, Nhỏ Ngọt Ngào, Nam Trầm Review Phim, Nữ Sang Trọng...) miễn phí 100%, không tốn API token.'
      },
      {
        title: '🎭 Tự Động Phân Vai Nam - Nữ (Dialogue Auto-Assign)',
        desc: 'Mô hình CAM++ tự động phân tích cao độ và giọng điệu để chia vai Nam - Nữ thông minh trong video có nhiều người đối thoại.'
      },
      {
        title: '✂️ Băm Nhỏ Video Thành Tập (Auto Episodic Splitter)',
        desc: 'Tự động cắt video dài 5–30 phút thành các clip ngắn 60s/90s theo điểm ngắt câu tự nhiên, tự động gắn huy hiệu [Tập X/Y] chuẩn TikTok/Reels.'
      },
      {
        title: '🌐 Render Song Song Đa Ngôn Ngữ (Multi-market Export)',
        desc: '1 video gốc xuất đồng thời ra nhiều thứ tiếng (Việt, Anh, Thái, Indo, Trung, Nhật, Hàn...) với phụ đề và giọng đọc localized độc lập.'
      },
      {
        title: '📥 Clean Downloader Không Watermark',
        desc: 'Tự động bóc tách link gốc và tải video siêu sạch không logo từ Douyin, TikTok, Xiaohongshu (Rednote), Facebook Reels.'
      },
      {
        title: '🤖 Trợ Lý AI Telegram 24/7 & Watchdog Giám Sát Kênh',
        desc: 'Điều khiển trạm sản xuất từ xa qua điện thoại (gửi link -> tự làm -> gửi lại video thành phẩm) và tự động bắt video mới khi kênh đăng tải. Có giao diện quản trị riêng trên Web UI (#/bot).'
      }
    ]
  },
  {
    version: '0.6.1',
    date: '10/11/2026',
    tag: 'Ổn định',
    tagColor: '#6366f1',
    badge: 'Cải tiến',
    highlights: [
      {
        title: '✨ Cải tiến tính năng Kể chuyện (Story)',
        desc: 'Tối ưu AI viết kịch bản và sinh hình ảnh tự động theo từng cảnh.'
      },
      {
        title: '🧽 Nâng cấp xóa phụ đề gốc bằng RapidOCR',
        desc: 'Hỗ trợ Inpaint và Blur thông minh, đặt phụ đề tiếng Việt đè chính xác lên vùng phụ đề gốc đã che.'
      },
      {
        title: '📝 Phong cách phụ đề TikTok Highlight',
        desc: 'Bổ sung kiểu phụ đề TikTok nhấn sáng từng từ (karaoke word-level) bắt mắt.'
      }
    ]
  },
  {
    version: '0.6.0',
    date: '01/11/2026',
    tag: 'Khởi đầu',
    tagColor: '#8b5cf6',
    badge: 'Nền tảng',
    highlights: [
      {
        title: '🎬 Ra mắt giao diện Studio trực quan',
        desc: 'Dòng thời gian đa lớp (Timeline), chỉnh sửa câu thoại, timeline và nghe thử giọng lồng tiếng tức thì.'
      },
      {
        title: '🗣️ Tích hợp VieNeu-TTS & Edge-TTS',
        desc: 'Hỗ trợ giọng đọc tiếng Việt chất lượng cao ngay trên máy tính.'
      },
      {
        title: '🎯 Nhận dạng giọng nói faster-whisper',
        desc: 'Tự động tạo phụ đề và đồng bộ thời gian chuẩn xác theo từng từ.'
      }
    ]
  }
];

export function openChangelog() {
  let m = null;

  const content = el('div', { class: 'changelog-modal-content', style: { maxHeight: '72vh', overflowY: 'auto', padding: '16px 20px' } });

  CHANGELOG_DATA.forEach((ver, idx) => {
    const card = el('div', {
      class: 'panel',
      style: {
        marginBottom: '16px',
        padding: '16px 18px',
        borderLeft: `4px solid ${ver.tagColor}`,
        background: 'var(--bg-panel)'
      }
    });

    const header = el('div', {
      style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }
    },
      el('div', { style: { display: 'flex', alignItems: 'center', gap: '10px' } },
        el('h3', { style: { margin: 0, fontSize: '16px', fontWeight: 'bold' }, text: `Phiên bản v${ver.version}` }),
        el('span', {
          class: 'pill',
          style: { background: ver.tagColor, color: '#fff', fontSize: '11px', padding: '2px 8px', borderRadius: '12px', fontWeight: '600' },
          text: ver.tag
        })
      ),
      el('span', { class: 'dim small', text: ver.date })
    );

    const list = el('div', { style: { display: 'flex', flexDirection: 'column', gap: '10px' } });
    ver.highlights.forEach(h => {
      list.append(
        el('div', null,
          el('div', { style: { fontWeight: '600', fontSize: '13px', color: 'var(--text-main)', marginBottom: '2px' }, text: h.title }),
          el('div', { class: 'dim small', style: { lineHeight: '1.5', paddingLeft: '14px' }, text: h.desc })
        )
      );
    });

    card.append(header, list);
    content.append(card);
  });

  const footer = el('div', {
    style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px', borderTop: '1px solid var(--border)', background: 'var(--bg-sub)' }
  },
    el('button', {
      type: 'button',
      class: 'btn btn-sm',
      onclick: () => {
        if (m) m.close();
        openUpdate();
      }
    }, icon('refresh'), ' Kiểm tra cập nhật mới'),
    el('button', {
      type: 'button',
      class: 'btn btn-sm btn-primary',
      onclick: () => { if (m) m.close(); }
    }, 'Đóng')
  );

  m = openModal([
    modalHead('clock', 'Lịch sử cập nhật qua các phiên bản', () => m),
    content,
    footer
  ], { cls: 'modal-changelog', style: { maxWidth: '780px' } });
}
