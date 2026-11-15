/* K-Tube Studio - Trợ lý AI Telegram 24/7 & Giám sát kênh Watchdog */
import { api, busy, el, icon, toast } from './core.js';

export async function viewBot(main, alive) {
  let statusData = null;
  try {
    statusData = await api('GET', '/api/bot/status');
  } catch (e) {
    statusData = { telegram: {}, watchdog: {} };
  }
  if (!alive()) return null;

  main.append(
    el('div', { class: 'page-head' },
      el('div', { class: 'page-head-text' },
        el('div', { class: 'eyebrow', text: 'Tự động hóa 24/7' }),
        el('h1', { text: 'Trợ lý Telegram & Giám sát kênh' }),
        el('p', { text: 'Ra lệnh sản xuất video từ xa qua điện thoại, tự động tải sạch không watermark và tự bắt video kênh mới.' })
      )
    ),
    botDashboard(statusData)
  );
  return null;
}

export function botDashboard(initialData = null) {
  const container = el('div', { class: 'bot-dashboard-container', style: { display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '1000px' } });

  let state = initialData || {
    telegram: { running: false, bot_info: {}, bot_token: '', admin_chat_ids: [], send_video: true, notify_progress: true },
    watchdog: { running: false, channels: [], interval_minutes: 30, auto_render: true, seen_count: 0 }
  };

  async function refreshStatus() {
    try {
      state = await api('GET', '/api/bot/status');
      render();
    } catch (e) {
      toast('Lỗi cập nhật trạng thái bot: ' + e.message, 'error');
    }
  }

  function render() {
    container.replaceChildren();

    const tg = state.telegram || {};
    const wd = state.watchdog || {};
    const isRunning = tg.running || wd.running;

    // 1. Live Status Card
    const statusPill = el('span', {
      class: 'pill ' + (isRunning ? 'ok' : 'warn'),
      style: { fontSize: '13px', padding: '4px 12px', fontWeight: '600' },
      text: isRunning ? '🟢 Đang hoạt động 24/7' : '⚪ Đang tạm dừng'
    });

    const toggleBtn = el('button', {
      type: 'button',
      class: 'btn ' + (isRunning ? 'btn-danger' : 'btn-primary'),
      style: { padding: '8px 18px', fontWeight: '600' },
      onclick: () => busy(toggleBtn, async () => {
        if (isRunning) {
          await api('POST', '/api/bot/stop');
          toast('Đã dừng Trợ lý Telegram & Watchdog', 'success');
        } else {
          const r = await api('POST', '/api/bot/start');
          if (r.telegram_started) {
            toast('Đã khởi động Trợ lý Telegram 24/7 thành công!', 'success');
          } else {
            toast('Watchdog đã bật, nhưng Telegram Bot chưa có token hợp lệ.', 'warn');
          }
        }
        await refreshStatus();
      })
    }, icon(isRunning ? 'pause' : 'play'), isRunning ? ' Dừng Trợ lý 24/7' : ' Khởi động Trợ lý 24/7');

    const botName = tg.bot_info && tg.bot_info.username
      ? el('a', {
          href: `https://t.me/${tg.bot_info.username}`,
          target: '_blank',
          class: 'mono',
          style: { color: 'var(--color-primary)', fontWeight: 'bold' },
          text: `@${tg.bot_info.username}`
        })
      : el('span', { class: 'muted', text: 'Chưa kết nối bot' });

    const topBanner = el('div', {
      class: 'panel',
      style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', background: 'var(--bg-panel)' }
    },
      el('div', { style: { display: 'flex', alignItems: 'center', gap: '16px' } },
        statusPill,
        el('div', null,
          el('div', { style: { fontSize: '14px', fontWeight: '600' } }, 'Telegram Bot: ', botName),
          el('div', { class: 'dim small' },
            `Hàng đợi: ${tg.queue_size || 0} video | Kênh theo dõi: ${(wd.channels || []).length} kênh`
          )
        )
      ),
      toggleBtn
    );

    // 2. Telegram Configuration Panel
    const tokenInp = el('input', {
      class: 'input mono',
      type: 'text',
      placeholder: 'Dán Token bot lấy từ @BotFather (vd: 7123456789:AAH...)',
      value: tg.bot_token || '',
      style: { width: '100%' }
    });

    const adminInp = el('input', {
      class: 'input mono',
      type: 'text',
      placeholder: 'Nhập Chat ID của bạn (vd: 123456789). Nhiều ID cách nhau bằng dấu phẩy',
      value: (tg.admin_chat_ids || []).join(', '),
      style: { width: '100%' }
    });

    const sendVideoCheck = el('input', {
      type: 'checkbox',
      checked: tg.send_video !== false
    });

    const notifyCheck = el('input', {
      type: 'checkbox',
      checked: tg.notify_progress !== false
    });

    const testOut = el('span', { class: 'test-out small', style: { marginLeft: '10px' } });

    const testBtn = el('button', {
      type: 'button',
      class: 'btn btn-sm',
      onclick: () => busy(testBtn, async () => {
        testOut.className = 'test-out small muted';
        testOut.textContent = 'Đang kiểm tra bot...';
        try {
          const ids = adminInp.value.split(',').map(s => s.trim()).filter(Boolean);
          const r = await api('POST', '/api/bot/test', {
            token: tokenInp.value.trim(),
            admin_chat_ids: ids
          });
          testOut.className = 'test-out small ok';
          testOut.textContent = `✓ Bot @${r.bot.username} hoạt động tốt! Đã gửi tin nhắn đến ${r.notified_admins} admin.`;
        } catch (e) {
          testOut.className = 'test-out small err';
          testOut.textContent = `✗ Lỗi: ${e.message}`;
        }
      })
    }, icon('send'), ' Gửi tin nhắn thử nghiệm');

    const saveTgBtn = el('button', {
      type: 'button',
      class: 'btn btn-sm btn-primary',
      onclick: () => busy(saveTgBtn, async () => {
        const ids = adminInp.value.split(',').map(s => s.trim()).filter(Boolean);
        await api('POST', '/api/bot/config', {
          telegram: {
            bot_token: tokenInp.value.trim(),
            admin_chat_ids: ids,
            send_video: sendVideoCheck.checked,
            notify_progress: notifyCheck.checked,
            enabled: isRunning
          },
          restart: isRunning
        });
        toast('Đã lưu cấu hình Telegram thành công!', 'success');
        await refreshStatus();
      })
    }, icon('save'), ' Lưu cấu hình Telegram');

    const tgPanel = el('div', { class: 'panel' },
      el('div', { class: 'panel-head' },
        icon('spark'),
        el('h3', { text: 'Cấu hình Trợ lý Telegram' })
      ),
      el('div', { style: { display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '12px' } },
        el('div', null,
          el('label', { style: { fontWeight: '600', display: 'block', marginBottom: '6px' }, text: 'Telegram Bot Token:' }),
          tokenInp,
          el('div', { class: 'dim small', style: { marginTop: '4px' } },
            'Tạo bot miễn phí bằng cách chat với ',
            el('a', { href: 'https://t.me/BotFather', target: '_blank', text: '@BotFather' }),
            ' trên Telegram (gõ lệnh /newbot).'
          )
        ),
        el('div', null,
          el('label', { style: { fontWeight: '600', display: 'block', marginBottom: '6px' }, text: 'Admin Chat IDs (Bảo mật quyền điều khiển):' }),
          adminInp,
          el('div', { class: 'dim small', style: { marginTop: '4px' } },
            'Chỉ những Chat ID này mới có quyền ra lệnh xử lý video. Chat với ',
            el('a', { href: 'https://t.me/userinfobot', target: '_blank', text: '@userinfobot' }),
            ' để lấy ID của bạn. Để trống = Cho phép mọi người dùng.'
          )
        ),
        el('div', { style: { display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'center' } },
          el('label', { style: { display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' } },
            sendVideoCheck,
            el('span', { text: 'Tự động gửi video kết quả về chat (nếu dung lượng <= 50MB)' })
          ),
          el('label', { style: { display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' } },
            notifyCheck,
            el('span', { text: 'Báo tiến trình render chi tiết qua tin nhắn' })
          )
        ),
        el('div', { style: { display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' } },
          saveTgBtn,
          testBtn,
          testOut
        )
      )
    );

    // 3. Watchdog Channel Monitor Panel
    const channelsInp = el('textarea', {
      class: 'input mono',
      rows: 4,
      placeholder: 'Dán link các kênh cần theo dõi (mỗi dòng 1 link):\nhttps://www.youtube.com/@ChannelName\nhttps://www.douyin.com/user/...\nhttps://www.tiktok.com/@creator',
      style: { width: '100%', resize: 'vertical' },
      value: (wd.channels || []).join('\n')
    });

    const intervalSel = el('select', {
      class: 'input',
      style: { width: 'auto', minWidth: '150px' }
    },
      el('option', { value: '15', selected: String(wd.interval_minutes) === '15', text: '15 phút' }),
      el('option', { value: '30', selected: String(wd.interval_minutes) === '30', text: '30 phút' }),
      el('option', { value: '60', selected: String(wd.interval_minutes) === '60', text: '1 tiếng' }),
      el('option', { value: '120', selected: String(wd.interval_minutes) === '120', text: '2 tiếng' }),
      el('option', { value: '360', selected: String(wd.interval_minutes) === '360', text: '6 tiếng' })
    );

    const autoRenderCheck = el('input', {
      type: 'checkbox',
      checked: wd.auto_render !== false
    });

    const scanMsg = el('span', { class: 'test-out small', style: { marginLeft: '10px' } });

    const scanBtn = el('button', {
      type: 'button',
      class: 'btn btn-sm',
      onclick: () => busy(scanBtn, async () => {
        scanMsg.className = 'test-out small muted';
        scanMsg.textContent = 'Đang quét các kênh...';
        try {
          const r = await api('POST', '/api/watchdog/scan');
          scanMsg.className = 'test-out small ok';
          scanMsg.textContent = `✓ Đã quét xong. Phát hiện ${r.count} video mới!`;
        } catch (e) {
          scanMsg.className = 'test-out small err';
          scanMsg.textContent = `✗ Lỗi quét kênh: ${e.message}`;
        }
      })
    }, icon('target'), ' Quét kênh ngay lập tức');

    const saveWdBtn = el('button', {
      type: 'button',
      class: 'btn btn-sm btn-primary',
      onclick: () => busy(saveWdBtn, async () => {
        const lines = channelsInp.value.split('\n').map(s => s.trim()).filter(Boolean);
        await api('POST', '/api/bot/config', {
          watchdog: {
            channels: lines,
            interval_minutes: parseInt(intervalSel.value, 10),
            auto_render: autoRenderCheck.checked,
            enabled: isRunning
          },
          restart: isRunning
        });
        toast('Đã lưu cấu hình theo dõi kênh thành công!', 'success');
        await refreshStatus();
      })
    }, icon('save'), ' Lưu kênh theo dõi');

    const wdPanel = el('div', { class: 'panel' },
      el('div', { class: 'panel-head' },
        icon('flame'),
        el('h3', { text: 'Theo dõi Kênh Tự Động (Watchdog Channel Monitor)' })
      ),
      el('div', { style: { display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '12px' } },
        el('div', null,
          el('label', { style: { fontWeight: '600', display: 'block', marginBottom: '6px' }, text: 'Danh sách kênh nguồn theo dõi:' }),
          channelsInp,
          el('div', { class: 'dim small', style: { marginTop: '4px' } },
            'Hỗ trợ link kênh YouTube, TikTok và Douyin. Khi kênh đăng video mới, hệ thống tự động tải và kích hoạt quy trình.'
          )
        ),
        el('div', { style: { display: 'flex', gap: '24px', alignItems: 'center', flexWrap: 'wrap' } },
          el('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
            el('label', { style: { fontWeight: '600' }, text: 'Chu kỳ quét:' }),
            intervalSel
          ),
          el('label', { style: { display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' } },
            autoRenderCheck,
            el('span', { text: 'Tự động dịch, lồng tiếng CapCut và render xuất bản khi có video mới' })
          )
        ),
        el('div', { style: { display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' } },
          saveWdBtn,
          scanBtn,
          scanMsg
        )
      )
    );

    // 4. Quick Usage Instructions
    const guidePanel = el('div', { class: 'panel' },
      el('div', { class: 'panel-head' },
        icon('safe'),
        el('h3', { text: 'Hướng dẫn ra lệnh điều khiển từ điện thoại' })
      ),
      el('div', { style: { fontSize: '13px', lineHeight: '1.7', color: 'var(--text-muted)' } },
        el('p', null, el('b', { text: '1. Gửi link video:' }), ' Mở Telegram từ điện thoại, dán link Douyin, TikTok, Facebook Reel hoặc YouTube vào bot. Bot sẽ tự động tải sạch (không watermark) và xử lý từ A-Z.'),
        el('p', null, el('b', { text: '2. Lệnh kiểm tra:' }), ' Gõ ', el('code', { text: '/status' }), ' để xem tình trạng máy chủ và tiến độ render.'),
        el('p', null, el('b', { text: '3. Xem giọng đọc:' }), ' Gõ ', el('code', { text: '/voices' }), ' để xem danh mục giọng CapCut AI đang được hỗ trợ.'),
        el('p', null, el('b', { text: '4. Khởi động 1-Click:' }), ' Bạn cũng có thể nhấp đúp file ', el('code', { text: 'run_bot.cmd' }), ' trong thư mục dự án để bot chạy ngầm độc lập 24/7 mà không cần mở trình duyệt!')
      )
    );

    container.append(topBanner, tgPanel, wdPanel, guidePanel);
  }

  render();
  return container;
}

