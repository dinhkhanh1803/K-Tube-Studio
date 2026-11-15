"""Bộ tải video trực tiếp KHÔNG WATERMARK (Clean Downloader) cho Douyin, TikTok, Xiaohongshu, Facebook.

Tự động bypass watermark / logo bản quyền nền tảng mà không cần API trả phí hay cookies phức tạp.
Khi gặp video riêng tư hoặc nền tảng thay đổi cấu trúc, tự động fallback về yt-dlp một cách mượt mà.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from .util import check_cancel, ffmpeg, log, probe, progress, safe_name, short_hash

UA_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
)


def _http_get(url: str, headers: dict | None = None, timeout: float = 20.0, follow_redirects: bool = True) -> tuple[int, bytes, str]:
    """Gửi GET request và trả về (status_code, body, final_url)."""
    h = {"User-Agent": UA_DESKTOP}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read(), resp.geturl()


def _http_post(url: str, data: dict, headers: dict | None = None, timeout: float = 20.0) -> tuple[int, bytes]:
    """Gửi POST form-encoded request."""
    h = {
        "User-Agent": UA_DESKTOP,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    if headers:
        h.update(headers)
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def stream_download_file(
    stream_url: str,
    dest_path: Path,
    headers: dict | None = None,
    progress_cb: Callable[[float], None] | None = None,
) -> None:
    """Tải file theo chunks và báo tiến độ."""
    h = {"User-Agent": UA_DESKTOP}
    if headers:
        h.update(headers)
    req = urllib.request.Request(stream_url, headers=h)
    with urllib.request.urlopen(req, timeout=30) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        downloaded = 0
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        part_file = dest_path.with_suffix(".part")
        with open(part_file, "wb") as f:
            while True:
                check_cancel()
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0 and progress_cb:
                    progress_cb(min(1.0, downloaded / total))
        if part_file.exists():
            if dest_path.exists():
                dest_path.unlink()
            part_file.rename(dest_path)


# ==============================================================================
# Platform Extractors
# ==============================================================================

def extract_clean_tiktok(url: str) -> dict[str, Any] | None:
    """Bóc tách video TikTok không watermark qua TikWM."""
    try:
        status, body = _http_post("https://www.tikwm.com/api/", {"url": url, "hd": 1})
        data = json.loads(body.decode("utf-8", errors="replace"))
        if data.get("code") == 0 and data.get("data"):
            d = data["data"]
            video_url = d.get("hdplay") or d.get("play")
            if video_url:
                if video_url.startswith("/"):
                    video_url = "https://www.tikwm.com" + video_url
                return {
                    "id": str(d.get("id") or short_hash(url)),
                    "title": str(d.get("title") or "TikTok Video"),
                    "video_url": video_url,
                    "uploader": str(d.get("author", {}).get("nickname") or d.get("author", {}).get("unique_id") or ""),
                    "duration": float(d.get("duration") or 0),
                    "cover": d.get("cover") or d.get("origin_cover") or "",
                    "no_watermark": True,
                }
    except Exception as e:
        log("download", f"TikWM TikTok extractor notice: {e}")
    return None


def extract_clean_douyin(url: str) -> dict[str, Any] | None:
    """Bóc tách video Douyin không watermark (thử TikWM trước, sau đó qua Mobile API)."""
    # 1. Thử TikWM
    res = extract_clean_tiktok(url)
    if res and res.get("video_url"):
        return res

    # 2. Thử Douyin Official Mobile ItemInfo API
    try:
        # Resolve short link (v.douyin.com)
        _, _, resolved_url = _http_get(url, headers={"User-Agent": UA_MOBILE})
        m = re.search(r"/(?:video|note)/(\d{10,})", resolved_url)
        if not m:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(resolved_url).query)
            aweme_id = (q.get("modal_id") or q.get("aweme_id") or [None])[0]
        else:
            aweme_id = m.group(1)

        if aweme_id:
            api = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={aweme_id}"
            _, body, _ = _http_get(api, headers={"User-Agent": UA_MOBILE})
            data = json.loads(body.decode("utf-8", errors="replace"))
            items = data.get("item_list") or []
            if items:
                item = items[0]
                title = item.get("desc") or "Douyin Video"
                uploader = item.get("author", {}).get("nickname") or ""
                url_list = item.get("video", {}).get("play_addr", {}).get("url_list") or []
                if url_list:
                    # Thay playwm -> play để lấy luồng sạch
                    clean_stream = url_list[0].replace("playwm", "play")
                    # Lấy URL cuối cùng sau redirect
                    _, _, real_mp4 = _http_get(clean_stream, headers={"User-Agent": UA_MOBILE})
                    return {
                        "id": str(aweme_id),
                        "title": title,
                        "video_url": real_mp4 or clean_stream,
                        "uploader": uploader,
                        "duration": float(item.get("duration") or 0) / 1000.0,
                        "no_watermark": True,
                    }
    except Exception as e:
        log("download", f"Douyin mobile API notice: {e}")
    return None


def extract_clean_xiaohongshu(url: str) -> dict[str, Any] | None:
    """Bóc tách video Xiaohongshu / Rednote không watermark từ web HTML stream."""
    try:
        _, body, resolved_url = _http_get(url, headers={"User-Agent": UA_DESKTOP})
        html = body.decode("utf-8", errors="replace")

        # Tìm note id
        m_id = re.search(r"/explore/([0-9a-zA-Z]+)", resolved_url)
        note_id = m_id.group(1) if m_id else short_hash(url)

        # 1. Tìm stream video mp4 từ CDN xhscdn.com
        video_matches = re.findall(r'https?://[^\s"\']+xhscdn\.com[^\s"\']+\.mp4[^\s"\']*', html)
        if video_matches:
            # Ưu tiên link có master hoặc 1080p
            clean_url = video_matches[0]
            for v in video_matches:
                if "master" in v or "1080" in v or "origin" in v:
                    clean_url = v
                    break

            # Tìm title
            t_m = re.search(r"<title>(.*?)</title>", html, re.I)
            title = t_m.group(1).split(" - ")[0].strip() if t_m else "Xiaohongshu Video"
            return {
                "id": str(note_id),
                "title": title,
                "video_url": clean_url,
                "uploader": "Xiaohongshu Creator",
                "duration": 0,
                "headers": {"Referer": "https://www.xiaohongshu.com/"},
                "no_watermark": True,
            }
    except Exception as e:
        log("download", f"Xiaohongshu clean extractor notice: {e}")
    return None


def extract_clean_facebook(url: str) -> dict[str, Any] | None:
    """Bóc tách video Reels / Watch Facebook HD/SD trực tiếp."""
    try:
        headers = {
            "User-Agent": UA_DESKTOP,
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Mode": "navigate",
        }
        _, body, _ = _http_get(url, headers=headers)
        html = body.decode("utf-8", errors="replace")

        # Tìm URL stream HD hoặc SD trong payload Facebook
        patterns = [
            r'browser_native_hd_url["\']?\s*:\s*["\'](https:[^"\']+)["\']',
            r'browser_native_sd_url["\']?\s*:\s*["\'](https:[^"\']+)["\']',
            r'playable_url_quality_hd["\']?\s*:\s*["\'](https:[^"\']+)["\']',
            r'["\']playable_url["\']?\s*:\s*["\'](https:[^"\']+)["\']',
        ]
        clean_url = None
        for pat in patterns:
            m = re.search(pat, html)
            if m:
                raw_url = m.group(1)
                # Unescape \u0026 và \/
                clean_url = raw_url.replace(r"\/", "/").replace(r"\u0026", "&")
                break

        if clean_url:
            # Lấy title
            t_m = re.search(r"<title>(.*?)</title>", html, re.I)
            title = t_m.group(1).replace(" | Facebook", "").strip() if t_m else "Facebook Reel"
            m_id = re.search(r"/(?:reel|videos)/(\d+)", url)
            vid = m_id.group(1) if m_id else short_hash(url)
            return {
                "id": vid,
                "title": title,
                "video_url": clean_url,
                "uploader": "Facebook Creator",
                "duration": 0,
                "no_watermark": True,
            }
    except Exception as e:
        log("download", f"Facebook clean extractor notice: {e}")
    return None


# ==============================================================================
# Main Clean Job Handler
# ==============================================================================

def clean_download_job(url: str, plat: str, work: Path, cfg, force: bool = False) -> Path | None:
    """Thử trích xuất và tải video không watermark trực tiếp.
    Trả về thư mục job nếu thành công, None nếu nền tảng không hỗ trợ hoặc cần fallback yt-dlp."""
    extractor_map = {
        "tiktok": extract_clean_tiktok,
        "douyin": extract_clean_douyin,
        "xiaohongshu": extract_clean_xiaohongshu,
        "facebook": extract_clean_facebook,
    }

    extractor = extractor_map.get(plat)
    if not extractor:
        return None

    log("download", f"[{plat}] Đang quét luồng video gốc KHÔNG WATERMARK...")
    info = extractor(url)
    if not info or not info.get("video_url"):
        log("download", f"[{plat}] Không lấy được luồng clean trực tiếp, tự động chuyển sang engine yt-dlp...")
        return None

    vid = safe_name(str(info.get("id") or short_hash(url)), 40)
    job = work / f"{plat}_{vid}"
    job.mkdir(parents=True, exist_ok=True)

    source_mp4 = job / "source.mp4"
    if force:
        source_mp4.unlink(missing_ok=True)
        (job / "meta.json").unlink(missing_ok=True)

    if not source_mp4.exists():
        video_url = info["video_url"]
        log("download", f"[{plat}] Bắt đầu tải video sạch: {info.get('title', '')[:70]} ...")
        custom_headers = info.get("headers") or {}

        def _on_prog(p: float):
            progress("download", p)

        temp_video = job / "download_clean.mp4"
        try:
            stream_download_file(video_url, temp_video, headers=custom_headers, progress_cb=_on_prog)
            # Chuẩn hóa về source.mp4 qua ffmpeg copy
            if temp_video.exists():
                ffmpeg(["-i", temp_video, "-map", "0:v:0", "-map", "0:a:0?", "-c", "copy", source_mp4])
                temp_video.unlink(missing_ok=True)
        except Exception as e:
            temp_video.unlink(missing_ok=True)
            log("download", f"[{plat}] Lỗi tải luồng clean ({e}), fallback sang yt-dlp...")
            return None

    if not (job / "meta.json").exists():
        meta = {
            "source": url,
            "platform": plat,
            "id": info.get("id", vid),
            "title": info.get("title", ""),
            "description": info.get("title", ""),
            "uploader": info.get("uploader", ""),
            "no_watermark": True,
        }
        try:
            probe_info = probe(source_mp4)
            meta.update({k: probe_info[k] for k in ("duration", "width", "height", "has_audio")})
        except Exception:
            pass
        (job / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    log("download", f"[{plat}] ✅ Đã tải video KHÔNG WATERMARK thành công!")
    return job

