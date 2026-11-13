/* Trang Phim AI (#/film): tạo phim chuyển động & khớp khẩu hình tiết kiệm (< 5.000đ/video). */
import {
  S, api, busy, confirmDialog, debounce, effEngine, el, emptyState, enc, fillVoiceSelect, fmtAgo,
  icon, pollSoon, put, queueListeners, toast, videoModal, voiceHooks,
} from './core.js';
import { waitTask } from './story.js';

const USD_VND = 25500;
const MODE_INFO = {
  hybrid: {
    name: 'Lip-Sync Fal.ai/Replicate (< 5.000đ)',
    desc: 'Khớp khẩu hình AI cho cảnh có nhân vật (~250đ/cảnh) + Video nền quay thật miễn phí cho cảnh bối cảnh (0đ).',
  },
  gemini_hybrid: {
    name: 'AI chuyển động bằng Key Gemini sẵn có + Nền 0đ',
    desc: 'Dùng chính GEMINI_API_KEY (gói trả phí, 360p ~586đ/giây) làm clip chuyển động thật cho cảnh chính + Video nền 0đ.',
  },
  free: {
    name: 'Miễn phí 100% (chỉ cần OpenAI/Gemini viết & vẽ)',
    desc: 'Không cần Fal.ai: dùng Video nền quay thật miễn phí + ảnh AI + chuyển động máy quay mượt + giọng 0đ.',
  },
  lipsync_all: {
    name: 'Khớp khẩu hình toàn bộ cảnh (Fal.ai)',
    desc: 'Mọi cảnh có lời dẫn & nhân vật đều chạy Lip-Sync nhép môi 1:1 (~250đ/cảnh).',
  },
};

export async function viewFilm(root, alive, arg) {
  let opts = {};
  try { opts = await api('GET', '/api/story/options'); } catch (_) { /* mặc định */ }
  if (!alive()) return;

  const hasLs = (opts.lipsync_providers || []).some((p) => p.usable);
  const hasVidAi = (opts.video_providers || []).some((p) => p.usable);
  let stories = [];
  let current = null;
  let filmMode = hasLs ? 'hybrid' : hasVidAi ? 'gemini_hybrid' : 'free';
  let targetSec = 60;
  let runningStep = '';
  let draftIdea = '';
  const lsChecked = new Set();

  const fileUrl = (sid, kind, name) => `/api/stories/${enc(sid)}/file/${enc(kind)}/${enc(name)}`;
  const lsProviders = () => opts.lipsync_providers || [];
  const lsReadyProv = () => lsProviders().find((p) => p.usable) || lsProviders().find((p) => p.ready) || lsProviders()[0];
  const activeJob = () => current && S.queue.find((q) => q.story === current.id && (q.state === 'queued' || q.state === 'running'));

  async function fetchList() {
    try { stories = (await api('GET', '/api/stories')).items || []; } catch (_) { stories = []; }
  }

  async function openProject(sid) {
    if (!sid) { current = null; lsChecked.clear(); paintAll(); return; }
    try {
      current = await api('GET', `/api/stories/${enc(sid)}`);
      if (!current.mode) current.mode = 'film';
      syncDefaultChecks();
    } catch (e) {
      toast(e.message || 'Không mở được dự án', 'error');
      current = null;
    }
    paintAll();
  }

  function syncDefaultChecks() {
    lsChecked.clear();
    if (!current) return;
    for (const sc of current.scenes || []) {
      const hasChar = (sc.characters || []).length > 0 || (current.characters || []).length === 0;
      if ((sc.text || '').trim() && hasChar) lsChecked.add(sc.id);
    }
  }

  const saveDebounced = debounce(async () => {
    if (!current || !current.id) return;
    try {
      const saved = await api('PUT', `/api/stories/${enc(current.id)}`, current);
      current = saved;
    } catch (_) { /* bỏ qua lưu ngầm */ }
  }, 550);

  async function saveNow() {
    saveDebounced.cancel && saveDebounced.cancel();
    if (!current || !current.id) return;
    current = await api('PUT', `/api/stories/${enc(current.id)}`, current);
  }

  async function ensureProject(titleHint, aspect, style) {
    if (current && current.id) {
      await saveNow();
      return current;
    }
    const created = await api('POST', '/api/stories', {
      title: (titleHint || 'Phim AI mới').slice(0, 80),
      aspect: aspect || '9:16',
      style: style || 'cinematic',
      mode: 'film',
    });
    current = created;
    current.mode = 'film';
    history.replaceState(null, '', '#/film/' + enc(current.id));
    await fetchList();
    return current;
  }

  const topWrap = el('div', { class: 'fm-top' });
  const studioWrap = el('div', { class: 'panel fm-setup' });
  const boardWrap = el('div', { class: 'fm-board' });
  const listWrap = el('div', { class: 'fm-projects' });
  const statusEl = el('div', { class: 'fm-progress', hidden: true });

  function setStatus(msg, pct = -1) {
    runningStep = msg;
    if (!msg) { statusEl.hidden = true; return; }
    statusEl.hidden = false;
    put(statusEl,
      el('span', { class: 'spinner' }),
      el('span', { text: msg }),
      pct >= 0 ? el('span', { class: 'mono small dim', text: `${Math.round(pct * 100)}%` }) : null);
  }

  function calcBudget() {
    if (filmMode === 'free') return { count: 0, usd: 0, vnd: 0, label: '' };
    if (filmMode === 'gemini_hybrid') {
      const n = current && (current.scenes || []).length
        ? current.scenes.filter((sc) => lsChecked.has(sc.id) && !sc.clip).length
        : Math.min(3, Math.max(1, Math.round(targetSec / 25)));
      const secs = n * 4;
      const usd = +(secs * 0.023).toFixed(2);
      return { count: n, usd, vnd: Math.round(usd * USD_VND), label: `${n} clip Gemini 360p (~${secs}s)` };
    }
    if (current && (current.scenes || []).length) {
      const n = current.scenes.filter((sc) => lsChecked.has(sc.id) && (sc.text || '').trim() && !sc.clip).length;
      const usd = +(n * 0.01).toFixed(2);
      return { count: n, usd, vnd: Math.round(usd * USD_VND), label: `${n} cảnh Lip-Sync` };
    }
    const estScenes = Math.max(4, Math.round(targetSec / 6));
    const lsScenes = filmMode === 'lipsync_all' ? estScenes : Math.ceil(estScenes * 0.55);
    const usd = +(lsScenes * 0.01).toFixed(2);
    return { count: lsScenes, usd, vnd: Math.round(usd * USD_VND), label: `${lsScenes} cảnh Lip-Sync` };
  }

  function paintTop() {
    const job = activeJob();
    const hasVid = current && !!current.output;
    put(topWrap,
      el('div', { class: 'view-head' },
        el('div', {},
          el('div', { class: 'eyebrow', text: 'Phim AI chuyển động · Tối ưu chi phí' }),
          el('h1', { text: current ? (current.title || 'Phim AI mới') : 'Tạo phim AI dưới 5.000đ' }),
          el('p', { class: 'view-sub', text: 'Kết hợp Khớp khẩu hình AI (~250đ/cảnh nói) + Video nền miễn phí (0đ) + Ảnh AI miễn phí & giọng đọc khớp 1:1.' })),
        el('div', { class: 'btn-row' },
          current ? el('button', {
            class: 'btn btn-sm', onclick: () => { current = null; lsChecked.clear(); history.replaceState(null, '', '#/film'); paintAll(); },
          }, icon('plus'), 'Phim mới') : null,
          current ? el('a', { class: 'btn btn-sm', href: '#/story/' + enc(current.id) }, icon('edit'), 'Mở bên Kể chuyện') : null,
          hasVid ? el('button', {
            class: 'btn btn-sm btn-primary',
            onclick: () => videoModal(`/api/stories/${enc(current.id)}/video?v=${Date.now()}`, current.title || 'Phim AI'),
          }, icon('play'), 'Xem phim') : null,
          job ? el('span', { class: 'pill pill-amber' }, el('span', { class: 'spinner' }), 'Đang xuất phim...') : null,
          el('a', { class: 'btn btn-sm btn-ghost', href: '#/settings' }, icon('sliders'), 'Cài đặt API'))));
  }

  function paintSetup() {
    const lsp = lsReadyProv();
    const titleInp = el('input', {
      class: 'input', placeholder: 'Tên phim (tự đặt hoặc AI đặt theo ý tưởng)',
      value: (current && current.title) || '',
      oninput: () => { if (current) { current.title = titleInp.value; saveDebounced(); } },
    });
    const ideaInp = el('textarea', {
      class: 'input fm-idea', rows: 3, value: draftIdea,
      placeholder: 'Nhập ý tưởng hoặc dán sẵn kịch bản (ví dụ: "Cô gái trẻ kể bí quyết tiết kiệm 5 triệu mỗi tháng tại quán cà phê mưa rơi, giọng tâm sự chân thật")...',
      oninput: () => { draftIdea = ideaInp.value; },
    });

    const secSel = el('select', { class: 'input input-sm', onchange: () => { targetSec = +secSel.value || 60; paintBudget(); } },
      [30, 60, 90, 120].map((v) => el('option', { value: String(v), selected: v === targetSec }, `${v} giây (~${Math.round(v / 5.5)} cảnh)`)));

    const aspectSel = el('select', {
      class: 'input input-sm',
      onchange: () => { if (current) { current.aspect = aspectSel.value; saveDebounced(); } },
    }, [['9:16', '9:16 Dọc (TikTok/Reels)'], ['16:9', '16:9 Ngang (YouTube)'], ['1:1', '1:1 Vuông']].map(([v, l]) =>
      el('option', { value: v, selected: v === ((current && current.aspect) || '9:16') }, l)));

    const styleSel = el('select', {
      class: 'input input-sm',
      onchange: () => { if (current) { current.style = styleSel.value; saveDebounced(); } },
    }, (opts.styles || [{ id: 'cinematic', label: 'Điện ảnh' }, { id: 'realistic', label: 'Chân thực' }]).map((s) =>
      el('option', { value: s.id, selected: s.id === ((current && current.style) || 'cinematic') }, s.label)));

    const vConf = (current && current.voice) || { engine: 'vieneu', voice: '', speed: 1, lang: 'vi' };
    const voiceSel = el('select', {
      class: 'input input-sm',
      onchange: () => {
        if (!current) return;
        current.voice = { ...vConf, engine: effEngine(vConf.engine || 'vieneu', 'vi'), voice: voiceSel.value };
        saveDebounced();
      },
    });
    fillVoiceSelect(voiceSel, effEngine(vConf.engine || 'vieneu', 'vi'), { current: vConf.voice || '', defaultLabel: 'Giọng mặc định (Miễn phí)', lang: 'vi' });

    const modeSel = el('select', {
      class: 'input input-sm',
      onchange: () => { filmMode = modeSel.value; paintBudget(); },
    }, Object.entries(MODE_INFO).map(([k, info]) => el('option', { value: k, selected: k === filmMode }, info.name)));

    const budgetBox = el('div', { class: 'fm-budget' });
    function paintBudget() {
      const b = calcBudget();
      const vp = (opts.video_providers || [])[0];
      const modeDesc = MODE_INFO[filmMode].desc;
      let keyWarn = null;
      if (filmMode === 'gemini_hybrid' && !(vp && vp.usable)) {
        keyWarn = el('div', { class: 'fm-warn small' },
          icon('alert'),
          vp && vp.ready ? ' Key Gemini đã có nhưng đang tắt "Tính năng trả phí" trong Cài đặt → Chi phí (hoặc key thuộc gói miễn phí chưa bật Billing).'
            : ' Chưa có key Gemini đã bật thanh toán: vẫn tạo được phim 0đ bằng ảnh & video nền.');
      } else if ((filmMode === 'hybrid' || filmMode === 'lipsync_all') && (!lsp || !lsp.usable)) {
        keyWarn = el('div', { class: 'fm-warn small' },
          icon('alert'),
          lsp && lsp.ready ? ' Đã có key Lip-Sync nhưng đang tắt "Tính năng trả phí" trong Cài đặt → Chi phí.'
            : ' Không bắt buộc Fal.ai: nếu bạn chỉ có key OpenAI & Gemini, hãy chọn chế độ "Miễn phí 100%" hoặc "AI chuyển động bằng Key Gemini sẵn có".');
      }
      put(budgetBox,
        el('div', { class: 'fm-budget-row' },
          el('span', { class: 'pill ' + (b.vnd <= 5000 ? 'pill-ok' : 'pill-amber') },
            icon('wand'),
            b.count ? ` Dự kiến: ~${b.vnd.toLocaleString('vi-VN')}đ (${b.label} · ${b.usd} USD)` : ' Dự kiến: 0đ (Miễn phí hoàn toàn)'),
          el('span', { class: 'dim small', text: modeDesc })),
        keyWarn);
    }
    paintBudget();

    async function stepWrite() {
      const txt = ideaInp.value.trim();
      if (!txt) { toast('Hãy nhập ý tưởng hoặc dán kịch bản trước', 'info'); ideaInp.focus(); return false; }
      const p = await ensureProject(txt.split(/[\n.]/)[0], aspectSel.value, styleSel.value);
      setStatus('Bước 1/4: AI đang viết kịch bản chia shot ngắn (3–6s)...', 0.1);
      const isLongScript = txt.length > 260 && txt.includes('\n');
      const { task } = await api('POST', `/api/stories/${enc(p.id)}/write`, {
        topic: isLongScript ? '' : txt,
        script: isLongScript ? txt : '',
        seconds: targetSec,
        replace: true,
      });
      await waitTask(task, (t) => setStatus(t.message || 'Đang viết kịch bản...', t.progress ?? 0.2));
      current = await api('GET', `/api/stories/${enc(p.id)}`);
      current.mode = 'film';
      await saveNow();
      syncDefaultChecks();
      return true;
    }

    async function stepImages() {
      if (!current || !(current.scenes || []).length) { toast('Chưa có cảnh nào để vẽ ảnh', 'info'); return false; }
      for (let i = 0; i < (current.characters || []).length; i++) {
        const ch = current.characters[i];
        if ((ch.refs || []).length) continue;
        setStatus(`Bước 2/4: Tạo ảnh mẫu nhân vật ${ch.name || (i + 1)}...`);
        try {
          const { task } = await api('POST', `/api/stories/${enc(current.id)}/characters/${enc(ch.id)}/generate`);
          await waitTask(task);
        } catch (_) { /* tiếp tục vẽ cảnh dù không có ảnh mẫu */ }
      }
      current = await api('GET', `/api/stories/${enc(current.id)}`);
      if (current.scenes.some((sc) => !sc.image && (sc.text || sc.prompt))) {
        setStatus('Bước 2/4: Đang vẽ ảnh gốc từng cảnh...', 0.35);
        const { task } = await api('POST', `/api/stories/${enc(current.id)}/generate`);
        await waitTask(task, (t) => setStatus(t.message || 'Đang vẽ ảnh...', t.progress ?? 0.45));
        current = await api('GET', `/api/stories/${enc(current.id)}`);
      }
      return true;
    }

    async function stepMotion() {
      if (!current || !(current.scenes || []).length) { toast('Chưa có cảnh nào', 'info'); return false; }
      const vp = (opts.video_providers || [])[0];
      if (filmMode === 'gemini_hybrid' && vp && vp.usable) {
        if ((current.video_res || '') !== '360p') { current.video_res = '360p'; await saveNow(); }
        const ids = current.scenes.filter((sc) => lsChecked.has(sc.id) && !sc.clip).map((sc) => sc.id);
        for (let k = 0; k < ids.length; k++) {
          setStatus(`Bước 3/4: Gemini tạo clip chuyển động cảnh ${k + 1}/${ids.length}...`, 0.55 + (0.3 * k) / ids.length);
          try {
            const { task } = await api('POST', `/api/stories/${enc(current.id)}/scenes/${enc(ids[k])}/animate`);
            await waitTask(task, (t) => setStatus(`Cảnh ${k + 1}/${ids.length}: ${t.message || 'Đang dựng clip Gemini...'}`, 0.6));
          } catch (e) {
            toast('Clip Gemini lỗi: ' + e.message, 'error');
            break;
          }
        }
        current = await api('GET', `/api/stories/${enc(current.id)}`);
      } else if ((filmMode === 'hybrid' || filmMode === 'lipsync_all') && lsp && lsp.usable) {
        const ids = current.scenes.filter((sc) => lsChecked.has(sc.id) && !sc.clip && (sc.text || '').trim()).map((sc) => sc.id);
        if (ids.length) {
          setStatus(`Bước 3/4: Khớp khẩu hình AI cho ${ids.length} cảnh (~${(ids.length * 250).toLocaleString('vi-VN')}đ)...`, 0.65);
          try {
            const { task } = await api('POST', `/api/stories/${enc(current.id)}/lipsync`, { scene_ids: ids, only_missing: true });
            await waitTask(task, (t) => setStatus(t.message || 'Đang khớp khẩu hình AI...', t.progress ?? 0.72));
            current = await api('GET', `/api/stories/${enc(current.id)}`);
          } catch (e) {
            toast('Lip-Sync gặp lỗi: ' + e.message, 'error');
          }
        }
      }
      if (current.scenes.some((sc) => !sc.clip)) {
        setStatus('Bước 3/4: Lấy Video nền quay thật miễn phí (Pexels/Pixabay) cho các cảnh còn lại...', 0.85);
        try {
          const { task } = await api('POST', `/api/stories/${enc(current.id)}/stock`, {
            only_missing: true,
            skip_characters: (filmMode === 'hybrid' && !!(lsp && lsp.usable)) || (filmMode === 'gemini_hybrid' && !!(vp && vp.usable)),
          });
          await waitTask(task, (t) => setStatus(t.message || 'Đang lấy video nền miễn phí...', t.progress ?? 0.88));
          current = await api('GET', `/api/stories/${enc(current.id)}`);
        } catch (_) { /* không có stock key vẫn render được bằng ảnh + chuyển động máy quay */ }
      }
      return true;
    }

    async function stepRender() {
      if (!current || !(current.scenes || []).length) { toast('Chưa có cảnh nào để xuất phim', 'info'); return; }
      setStatus('Bước 4/4: Đưa vào hàng đợi dựng & xuất MP4 (giọng + phụ đề + chuyển động)...', 0.95);
      await saveNow();
      await api('POST', `/api/stories/${enc(current.id)}/render`);
      pollSoon();
      toast('Đã đưa phim vào hàng đợi xuất! Xem tiến độ ở thanh trên.', 'success');
    }

    const autoBtn = el('button', {
      class: 'btn btn-primary',
      onclick: () => busy(autoBtn, async () => {
        const b = calcBudget();
        const vp = (opts.video_providers || [])[0];
        const willSpend = (filmMode === 'gemini_hybrid' && vp && vp.usable) || ((filmMode === 'hybrid' || filmMode === 'lipsync_all') && lsp && lsp.usable);
        if (b.vnd > 0 && willSpend) {
          const ok = await confirmDialog('Chạy quy trình Tạo phim AI?',
            `Dự kiến dùng ${b.label} (~${b.vnd.toLocaleString('vi-VN')}đ ≈ ${b.usd} USD) kết hợp Video nền miễn phí 0đ & Giọng đọc 0đ.`,
            { okText: 'Bắt đầu tạo phim' });
          if (!ok) return;
        }
        try {
          if (!current || !(current.scenes || []).length) {
            if (!(await stepWrite())) return;
            paintBoard();
          }
          if (!(await stepImages())) return;
          paintBoard();
          await stepMotion();
          paintBoard();
          await stepRender();
          await fetchList();
          paintAll();
        } finally {
          setStatus('');
        }
      }),
    }, icon('wand'), 'Tạo phim AI tự động (1 nút)');

    const writeBtn = el('button', {
      class: 'btn btn-sm',
      onclick: () => busy(writeBtn, async () => { try { if (await stepWrite()) { await fetchList(); paintAll(); } } finally { setStatus(''); } }),
    }, icon('edit'), '1. Viết kịch bản');

    const imgBtn = el('button', {
      class: 'btn btn-sm', disabled: !(current && (current.scenes || []).length),
      onclick: () => busy(imgBtn, async () => { try { if (await stepImages()) paintBoard(); } finally { setStatus(''); } }),
    }, icon('image'), '2. Vẽ ảnh');

    const motionBtn = el('button', {
      class: 'btn btn-sm', disabled: !(current && (current.scenes || []).length),
      onclick: () => busy(motionBtn, async () => { try { if (await stepMotion()) paintBoard(); } finally { setStatus(''); } }),
    }, icon('film'), '3. Chuyển động & Khớp môi');

    const renderBtn = el('button', {
      class: 'btn btn-sm', disabled: !(current && (current.scenes || []).length),
      onclick: () => busy(renderBtn, async () => { try { await stepRender(); paintTop(); } finally { setStatus(''); } }),
    }, icon('play'), '4. Xuất phim');

    put(studioWrap,
      el('div', { class: 'fm-grid' },
        el('label', { class: 'fm-field' }, el('span', { class: 'small dim', text: 'Tên phim' }), titleInp),
        el('label', { class: 'fm-field' }, el('span', { class: 'small dim', text: 'Thời lượng' }), secSel),
        el('label', { class: 'fm-field' }, el('span', { class: 'small dim', text: 'Khung hình' }), aspectSel),
        el('label', { class: 'fm-field' }, el('span', { class: 'small dim', text: 'Phong cách' }), styleSel),
        el('label', { class: 'fm-field' }, el('span', { class: 'small dim', text: 'Giọng đọc (0đ)' }), voiceSel),
        el('label', { class: 'fm-field' }, el('span', { class: 'small dim', text: 'Chiến lược chuyển động' }), modeSel)),
      el('label', { class: 'fm-field', style: { marginTop: '10px' } },
        el('span', { class: 'small dim', text: 'Ý tưởng hoặc kịch bản sẵn' }), ideaInp),
      budgetBox,
      el('div', { class: 'btn-row', style: { marginTop: '12px', flexWrap: 'wrap' } },
        autoBtn, writeBtn, imgBtn, motionBtn, renderBtn),
      statusEl);
  }

  function paintBoard() {
    if (!current || !(current.scenes || []).length) {
      put(boardWrap, emptyState('Chưa có phân cảnh nào',
        'Nhập ý tưởng phía trên rồi bấm "Tạo phim AI tự động" hoặc "1. Viết kịch bản" để AI chia cảnh ngắn 3–6 giây khớp hành động.'));
      return;
    }
    const lsp = lsReadyProv();
    const vp = (opts.video_providers || [])[0];
    const cards = current.scenes.map((sc, i) => {
      const cm = (sc.clip && (sc.clip_meta || {})[sc.clip]) || null;
      let preview;
      if (sc.clip) {
        preview = el('video', {
          src: fileUrl(current.id, 'clip', sc.clip),
          poster: sc.image ? fileUrl(current.id, 'img', sc.image) : null,
          muted: true, loop: true, playsinline: true, preload: 'metadata',
          onmouseenter: (e) => e.currentTarget.play().catch(() => {}),
          onmouseleave: (e) => e.currentTarget.pause(),
        });
        preview.muted = true;
      } else if (sc.image) {
        preview = el('img', { src: fileUrl(current.id, 'img', sc.image), alt: `Shot ${i + 1}`, loading: 'lazy' });
      } else {
        preview = el('div', { class: 'sy-noimg' }, icon('image'), el('span', { text: 'Chưa có ảnh' }));
      }
      const badgeLabel = cm ? (cm.src === 'lipsync' ? 'Lip-Sync' : cm.src === 'ai' ? 'AI Clip' : (cm.source_name || 'Video nền')) : 'Ảnh';
      const media = el('div', { class: 'fm-shot-media' },
        preview,
        el('span', { class: 'sy-badge ' + (cm ? 'sy-badge-clip' : ''), text: `#${i + 1} · ${badgeLabel}` }));

      const txt = el('textarea', {
        class: 'input input-sm', rows: 3, value: sc.text || '',
        placeholder: 'Lời thoại / thuyết minh của cảnh...',
        oninput: () => { sc.text = txt.value; saveDebounced(); },
      });
      const prm = el('input', {
        class: 'input input-sm', value: sc.prompt || '',
        placeholder: 'Mô tả hình ảnh & chuyển động...',
        oninput: () => { sc.prompt = prm.value; saveDebounced(); },
      });

      const lsChk = el('input', {
        type: 'checkbox', checked: lsChecked.has(sc.id),
        onchange: () => { if (lsChk.checked) lsChecked.add(sc.id); else lsChecked.delete(sc.id); paintSetup(); },
      });

      const lsBtn = el('button', {
        class: 'btn btn-xs' + (lsp && lsp.usable ? '' : ' btn-ghost'),
        disabled: !(lsp && lsp.usable),
        title: lsp && lsp.usable ? `Khớp khẩu hình AI (${lsp.name}, ~250đ)` : 'Cần dán key Fal.ai/Replicate & bật Trả phí trong Cài đặt',
        onclick: () => busy(lsBtn, async () => {
          if (!(sc.text || '').trim()) { toast('Cảnh chưa có lời dẫn', 'info'); return; }
          await saveNow();
          const { task } = await api('POST', `/api/stories/${enc(current.id)}/scenes/${enc(sc.id)}/lipsync`);
          await waitTask(task, (t) => setStatus(`Cảnh ${i + 1}: ${t.message || 'Đang khớp khẩu hình...'}`));
          setStatus('');
          current = await api('GET', `/api/stories/${enc(current.id)}`);
          paintBoard();
        }),
      }, icon('mic'), 'Khớp môi');

      const stkBtn = el('button', {
        class: 'btn btn-xs',
        title: 'Tìm video quay thật miễn phí cho cảnh này',
        onclick: () => busy(stkBtn, async () => {
          await saveNow();
          const res = await api('GET', `/api/stories/${enc(current.id)}/scenes/${enc(sc.id)}/stock`);
          const first = (res.items || [])[0];
          if (!first) { toast('Không tìm thấy video nền hợp, thử mở bên Kể chuyện để gõ từ khóa khác', 'info'); return; }
          const r = await api('POST', `/api/stories/${enc(current.id)}/scenes/${enc(sc.id)}/stock`, { item: first });
          current = r.story || await api('GET', `/api/stories/${enc(current.id)}`);
          paintBoard();
        }),
      }, icon('search'), 'Video nền 0đ');

      const aiBtn = vp && vp.usable ? el('button', {
        class: 'btn btn-xs',
        title: 'AI tạo clip chuyển động (Google Omni/Veo)',
        onclick: () => busy(aiBtn, async () => {
          await saveNow();
          const e = await api('GET', `/api/stories/${enc(current.id)}/animate/estimate?scene=${enc(sc.id)}`);
          if (!(await confirmDialog(`AI làm clip ${e.seconds}s cảnh ${i + 1}?`, `Khoảng ${e.usd} USD.`, { okText: 'Tạo clip' }))) return;
          const { task } = await api('POST', `/api/stories/${enc(current.id)}/scenes/${enc(sc.id)}/animate`);
          await waitTask(task);
          current = await api('GET', `/api/stories/${enc(current.id)}`);
          paintBoard();
        }),
      }, icon('film'), 'AI Clip') : null;

      return el('div', { class: 'fm-shot' },
        media,
        el('div', { class: 'fm-shot-body' },
          txt, prm,
          el('div', { class: 'fm-shot-acts' },
            el('label', { class: 'fm-chk small', title: 'Đưa vào danh sách chạy Khớp khẩu hình tự động' }, lsChk, 'Tự chạy Lip-Sync'),
            lsBtn, stkBtn, aiBtn)));
    });

    put(boardWrap,
      el('div', { class: 'fm-board-head' },
        el('h2', { text: `Bảng phân cảnh (${current.scenes.length} shot)` }),
        el('span', { class: 'dim small', text: 'Rê chuột lên video để xem thử · Tick cảnh nào cần nhân vật nói khớp miệng' })),
      el('div', { class: 'fm-shots' }, ...cards));
  }

  function paintProjects() {
    const films = stories.filter((s) => s.mode === 'film');
    const items = films.length ? films : stories;
    const heading = films.length ? 'Dự án Phim AI đã làm gần đây' : 'Dự án gần đây (Kể chuyện & Phim AI)';
    if (!items.length) {
      put(listWrap, el('h2', { text: 'Dự án Phim AI đã làm gần đây' }),
        el('p', { class: 'dim small', text: 'Chưa có dự án nào. Tạo bộ phim AI đầu tiên của bạn ở phía trên!' }));
      return;
    }
    put(listWrap,
      el('div', { class: 'fm-board-head' },
        el('h2', { text: heading }),
        el('span', { class: 'dim small', text: `${items.length} dự án` })),
      el('div', { class: 'fm-list' }, ...items.map((it) => {
        const thumb = it.cover
          ? el('img', { src: fileUrl(it.id, 'img', it.cover), alt: it.title || 'Film' })
          : el('div', { class: 'fm-thumb-empty' }, icon('film'));
        return el('div', { class: 'fm-row' + (current && current.id === it.id ? ' on' : '') },
          el('div', { class: 'fm-row-thumb' }, thumb),
          el('div', { class: 'fm-row-meta' },
            el('div', { class: 'fm-row-title', text: it.title || 'Phim AI không tên' }),
            el('div', { class: 'dim small', text: `${it.scenes || 0} cảnh · ${it.aspect || '9:16'} · ${it.updated ? fmtAgo(it.updated) : ''}` })),
          el('span', { class: 'pill ' + (it.output ? 'pill-ok' : '') }, it.output ? 'Đã xuất phim' : 'Bản nháp'),
          el('div', { class: 'btn-row' },
            it.output ? el('button', {
              class: 'btn btn-xs btn-primary',
              onclick: () => videoModal(`/api/stories/${enc(it.id)}/video?v=${it.updated || Date.now()}`, it.title || 'Phim AI'),
            }, icon('play'), 'Xem') : null,
            el('button', {
              class: 'btn btn-xs',
              onclick: () => { history.replaceState(null, '', '#/film/' + enc(it.id)); openProject(it.id); },
            }, icon('edit'), 'Mở'),
            el('button', {
              class: 'btn btn-xs btn-ghost', title: 'Xóa dự án',
              onclick: async () => {
                if (!(await confirmDialog('Xóa dự án này?', it.title || 'Phim AI', { okText: 'Xóa', danger: true }))) return;
                await api('DELETE', `/api/stories/${enc(it.id)}`);
                if (current && current.id === it.id) { current = null; history.replaceState(null, '', '#/film'); }
                await fetchList();
                paintAll();
              },
            }, icon('trash'))));
      })));
  }

  function paintAll() {
    paintTop();
    paintSetup();
    paintBoard();
    paintProjects();
  }

  const onQueue = () => {
    paintTop();
    if (current && current.id) {
      const finished = S.queue.find((q) => q.story === current.id && q.state === 'done');
      if (finished && !current.output) openProject(current.id).then(fetchList).then(paintProjects);
    }
  };
  queueListeners.add(onQueue);
  const onVoice = () => paintSetup();
  voiceHooks.add(onVoice);

  put(root, topWrap, studioWrap, boardWrap, listWrap);
  await fetchList();
  if (!alive()) return;
  if (arg) await openProject(arg);
  else paintAll();

  return () => {
    queueListeners.delete(onQueue);
    voiceHooks.delete(onVoice);
  };
}
