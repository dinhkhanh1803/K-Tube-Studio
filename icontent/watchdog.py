"""Hệ thống theo dõi kênh tự động (Watchdog Channel Monitor).

Tự động quét các kênh Douyin, TikTok, YouTube theo chu kỳ.
Khi có video mới: tự động thông báo qua Telegram và kích hoạt pipeline xử lý.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import load_config
from .util import log


class WatchdogService:
    """Service theo dõi kênh tự động định kỳ."""

    def __init__(self, config_path: str = r"D:\K-Tube-Studio\config.yaml"):
        self.config_path = config_path
        self.cfg = load_config(config_path)
        self._thread: threading.Thread | None = None
        self._running = False
        self.history_file = Path(self.cfg.work_dir) / "watchdog_history.json"
        self.history: dict[str, Any] = self._load_history()

    def _load_history(self) -> dict[str, Any]:
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"seen_ids": [], "seen_urls": [], "last_check": None}

    def _save_history(self) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_file.write_text(
            json.dumps(self.history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        if self.is_running():
            return True
        self.cfg = load_config(self.config_path)
        channels = self.cfg.watchdog.get("channels") or []
        if not channels:
            log("watchdog", "Chưa có kênh nào được cấu hình trong watchdog.channels")
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="WatchdogMonitor")
        self._thread.start()
        log("watchdog", f"Khởi động Watchdog theo dõi {len(channels)} kênh")
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        log("watchdog", "Đã dừng Watchdog")

    def check_channels_once(self) -> list[dict]:
        """Quét 1 lượt tất cả kênh và trả về danh sách video mới phát hiện."""
        import yt_dlp

        self.cfg = load_config(self.config_path)
        channels = self.cfg.watchdog.get("channels") or []
        new_videos = []

        opts = {
            "extract_flat": True,
            "playlistend": 3,
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        seen_ids = set(self.history.get("seen_ids", []))

        for ch_url in channels:
            ch_url = ch_url.strip()
            if not ch_url:
                continue
            log("watchdog", f"Đang quét kênh: {ch_url} ...")
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(ch_url, download=False)
                    entries = info.get("entries") or []
                    for e in entries:
                        if not e:
                            continue
                        vid_id = str(e.get("id") or "")
                        vid_url = e.get("url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "")
                        title = e.get("title") or "Video mới"
                        if vid_id and vid_id not in seen_ids:
                            log("watchdog", f"🔥 Phát hiện video MỚI: {title} ({vid_url})")
                            seen_ids.add(vid_id)
                            new_videos.append({
                                "id": vid_id,
                                "url": vid_url,
                                "title": title,
                                "channel": ch_url,
                                "timestamp": datetime.now().isoformat(),
                            })
            except Exception as e:
                log("watchdog", f"Lỗi quét kênh {ch_url}: {e}")

        self.history["seen_ids"] = list(seen_ids)
        self.history["last_check"] = datetime.now().isoformat()
        self._save_history()

        return new_videos

    def _loop(self) -> None:
        while self._running:
            try:
                new_vids = self.check_channels_once()
                if new_vids:
                    from .telegram_bot import get_telegram_service
                    tg = get_telegram_service()
                    auto_render = self.cfg.watchdog.get("auto_render", True)

                    for vid in new_vids:
                        vid_url = vid["url"]
                        vid_title = vid["title"]

                        # Báo tin nhắn qua Telegram nếu bot đang chạy
                        if tg.is_running() and tg.client:
                            admin_ids = self.cfg.telegram.get("admin_chat_ids") or []
                            alert_msg = (
                                f"🔔 *Watchdog: Phát hiện video mới!*\n\n"
                                f"🎬 *Tiêu đề:* {vid_title}\n"
                                f"🔗 *Link:* `{vid_url}`\n"
                                f"🚀 Tự động kích hoạt quy trình sản xuất..."
                            )
                            for aid in admin_ids:
                                try:
                                    tg.client.send_message(aid, alert_msg)
                                except Exception:
                                    pass

                        # Chạy pipeline nếu auto_render = True
                        if auto_render and vid_url:
                            try:
                                from .pipeline import run_job
                                log("watchdog", f"Tự động render video từ watchdog: {vid_url}")
                                out_file = run_job(vid_url, self.cfg)
                                if tg.is_running() and tg.client and out_file and out_file.exists():
                                    done_msg = f"✅ *Watchdog:* Đã hoàn tất render video mới: `{out_file.name}`"
                                    for aid in (self.cfg.telegram.get("admin_chat_ids") or []):
                                        try:
                                            tg.client.send_message(aid, done_msg)
                                        except Exception:
                                            pass
                            except Exception as pe:
                                log("watchdog", f"Lỗi pipeline tự động từ watchdog: {pe}")

            except Exception as e:
                log("watchdog", f"Lỗi vòng lặp watchdog: {e}")

            # Chờ theo chu kỳ
            interval_min = int(self.cfg.watchdog.get("interval_minutes", 30))
            sleep_sec = max(60, interval_min * 60)
            end_t = time.time() + sleep_sec
            while self._running and time.time() < end_t:
                time.sleep(2.0)


_watchdog_instance: WatchdogService | None = None


def get_watchdog_service() -> WatchdogService:
    global _watchdog_instance
    if _watchdog_instance is None:
        _watchdog_instance = WatchdogService()
    return _watchdog_instance

