"""Băm nhỏ video dài thành nhiều tập ngắn (Reels, TikTok, Shorts).
Tự động tìm điểm cắt tự nhiên theo khoảng lặng kết thúc câu phụ đề (không bao giờ cắt giữa chừng lời nói).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

from .models import Segment
from .util import ffmpeg, log, probe


def find_cut_points(segs: List[Segment], total_duration: float, target_duration: float = 60.0,
                    min_duration: float = 30.0) -> List[tuple[float, float, int]]:
    """Tìm danh sách khoảng thời gian [start, end, part_num] bám theo kết thúc câu thoại.
    Không bao giờ cắt ngang một câu thoại."""
    effective_min = min(min_duration, target_duration * 0.5)
    if not segs:
        # Nếu không có phụ đề, cắt đều theo thời gian
        cuts = []
        cur = 0.0
        part = 1
        while cur < total_duration:
            nxt = min(cur + target_duration, total_duration)
            if total_duration - nxt < effective_min:
                nxt = total_duration
            cuts.append((cur, nxt, part))
            part += 1
            cur = nxt
        return cuts

    cuts = []
    part = 1
    part_start = 0.0

    for i, s in enumerate(segs):
        cur_len = s.end - part_start
        remaining = total_duration - s.end
        if cur_len >= target_duration and remaining >= effective_min:
            cuts.append((part_start, s.end, part))
            part += 1
            part_start = s.end

    # Phần cuối cùng còn lại
    if part_start < total_duration:
        cuts.append((part_start, total_duration, part))

    return cuts


def split_video(
    video_path: Path,
    out_dir: Path,
    segs: List[Segment] | None = None,
    target_duration: float = 60.0,
    title_prefix: str = "Tập",
    add_badge: bool = True
) -> List[Dict[str, Any]]:
    """Cắt video thành các tập và lưu vào out_dir.
    Trả về danh sách thông tin từng tập: [{part: 1, file: Path, duration: float, start: float, end: float}]."""
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = probe(video_path)
    total_dur = meta.get("duration") or 0.0
    if total_dur <= 0:
        raise ValueError(f"Không lấy được thời lượng của video: {video_path}")

    cuts = find_cut_points(segs or [], total_dur, target_duration=target_duration)
    total_parts = len(cuts)
    log("split", f"Băm video {total_dur:.1f}s thành {total_parts} tập (mục tiêu ~{target_duration}s/tập)")

    results = []
    for start, end, part in cuts:
        part_name = f"{title_prefix}_{part:02d}.mp4"
        out_file = out_dir / part_name
        dur = end - start

        # Bộ lọc FFmpeg: nếu bật add_badge thì chèn text Tập X / Tổng số tập
        cmd = [
            "-y",
            "-ss", f"{start:.3f}",
            "-to", f"{end:.3f}",
            "-i", str(video_path),
        ]

        if add_badge:
            badge_text = f"{title_prefix} {part}"
            if part < total_parts:
                badge_text += f"/{total_parts}"
            # Drawtext badge ở góc trên
            vf = (
                f"drawtext=text='{badge_text}':fontcolor=white:fontsize=36:"
                f"box=1:boxcolor=black@0.6:boxborderw=8:x=(w-text_w)/2:y=60"
            )
            cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "aac"]
        else:
            # Cắt nhanh không encode lại nếu không cần badge
            cmd += ["-c", "copy"]

        cmd.append(str(out_file))
        try:
            ffmpeg(cmd)
            results.append({
                "part": part,
                "name": part_name,
                "file": str(out_file),
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(dur, 2),
                "badge": f"{title_prefix} {part}/{total_parts}"
            })
            log("split", f"  ✓ Xong {part_name}: {dur:.1f}s ({start:.1f}s -> {end:.1f}s)")
        except Exception as e:
            log("split", f"  ✗ Lỗi cắt tập {part}: {e}")

    # Ghi manifest parts.json
    manifest_path = out_dir / "parts.json"
    manifest_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results
