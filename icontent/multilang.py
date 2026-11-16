"""Xuất video đa ngôn ngữ song song (Multi-Language Batch Exporter).
Từ 1 video nguồn, dịch và lồng tiếng ra nhiều phiên bản: Tiếng Việt, Tiếng Anh, Tiếng Thái, Indo...
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Dict, Any

from .config import with_overrides
from .models import Segment, load_segments, save_segments, write_srt
from .util import log, short_hash


SUPPORTED_MARKETS = [
    {"code": "vi", "name": "Tiếng Việt", "flag": "🇻🇳"},
    {"code": "en", "name": "English", "flag": "🇺🇸"},
    {"code": "id", "name": "Bahasa Indonesia", "flag": "🇮🇩"},
    {"code": "th", "name": "ภาษาไทย (Thái)", "flag": "🇹🇭"},
    {"code": "zh", "name": "中文 (Trung Quốc)", "flag": "🇨🇳"},
    {"code": "ja", "name": "日本語 (Nhật Bản)", "flag": "🇯🇵"},
    {"code": "ko", "name": "한국어 (Hàn Quốc)", "flag": "🇰🇷"},
    {"code": "es", "name": "Español", "flag": "🇪🇸"},
    {"code": "ru", "name": "Русский", "flag": "🇷🇺"},
]


def render_multilang(
    job_dir: Path,
    target_langs: List[str],
    cfg,
    on_progress=None
) -> List[Dict[str, Any]]:
    """Dịch, lồng tiếng và xuất video ra đồng thời các ngôn ngữ trong target_langs."""
    from .translate import translate_segments
    from .tts import build_dub
    from .render import render
    from .pipeline import load_json

    meta = load_json(job_dir / "meta.json") or {}
    base_segs = load_segments(job_dir / "segments.json")
    if not base_segs:
        raise RuntimeError("Chưa có phụ đề nhận dạng gốc để dịch đa ngữ")

    # Nguồn âm thanh nền (nhạc nền / âm thanh gốc đã tách lời)
    bed = job_dir / "bgm.wav"
    bed_is_bgm = True
    if not bed.exists():
        bed = job_dir / "audio.wav"
        bed_is_bgm = False
    if not bed.exists():
        bed = None

    src_lang = meta.get("src_lang") or "zh"
    results = []

    for idx, lang in enumerate(target_langs, 1):
        log("multilang", f"[{idx}/{len(target_langs)}] Bắt đầu xử lý bản ngữ: {lang.upper()}...")
        # Tạo bản clone config riêng cho thứ tiếng này
        lang_cfg = with_overrides(cfg, {"translate": {"target_lang": lang}})

        # 1. Dịch phụ đề sang ngôn ngữ đích
        trans_segs = [Segment(s.id, s.start, s.end, s.text, s.trans, s.speaker, s.gender, s.voice) for s in base_segs]
        if lang == src_lang:
            for s in trans_segs:
                s.trans = s.text
        else:
            trans_segs = translate_segments(trans_segs, src_lang, lang, lang_cfg)

        # Lưu phụ đề theo ngôn ngữ
        lang_segs_path = job_dir / f"segments_{lang}.json"
        save_segments(lang_segs_path, trans_segs)
        write_srt(job_dir / f"subs_{lang}.srt", trans_segs)

        # 2. Lồng tiếng cho ngôn ngữ này
        dub_path = None
        if lang_cfg.tts.enabled:
            dub_out, _ = build_dub(trans_segs, job_dir, lang_cfg, meta)
            # Đổi tên file dub theo ngôn ngữ
            lang_dub = job_dir / f"dub_{lang}.wav"
            if dub_out and dub_out.exists():
                import shutil
                shutil.copy2(dub_out, lang_dub)
                dub_path = lang_dub

        # 3. Render video xuất xưởng
        out_name = f"final_{lang}.mp4"
        out_vid = render(job_dir, trans_segs, meta, lang_cfg, dub_path, bed, bed_is_bgm, out_name=out_name)

        results.append({
            "lang": lang,
            "name": out_name,
            "file": str(out_vid),
            "size": out_vid.stat().st_size if out_vid.exists() else 0,
            "created_at": time.time()
        })
        log("multilang", f"  ✓ Hoàn tất xuất video: {out_name}")
        if on_progress:
            on_progress(idx, len(target_langs))

    # Lưu manifest multilang.json
    (job_dir / "multilang.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results

