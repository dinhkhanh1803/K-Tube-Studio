"""Trợ lí AI 24/7 qua Telegram Bot điều khiển K-Tube Studio từ xa.

Cho phép người dùng gửi link video (Douyin, TikTok, Facebook, YouTube...) từ điện thoại,
bot tự động tải sạch không watermark, dịch, lồng tiếng CapCut AI và gửi lại thành phẩm.
"""
from __future__ import annotations

import json
import mimetypes
import os
import queue
import re
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from .config import load_config
from .download import extract_url
from .util import log


class TelegramBotClient:
    """Client giao tiếp Telegram Bot API chuẩn, không phụ thuộc thư viện ngoài."""

    def __init__(self, token: str):
        self.token = token.strip()
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def _api_call(self, method: str, data: dict | None = None, timeout: float = 30.0) -> dict:
        url = f"{self.base_url}/{method}"
        headers = {"User-Agent": "KTubeStudio-TelegramBot/1.0"}
        body = None
        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if not res.get("ok"):
                raise RuntimeError(f"Telegram API error {method}: {res.get('description')}")
            return res.get("result", {})

    def get_me(self) -> dict:
        return self._api_call("getMe")

    def get_updates(self, offset: int | None = None, timeout: int = 25) -> list[dict]:
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        url = f"{self.base_url}/getUpdates?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "KTubeStudio-TelegramBot/1.0"})
        with urllib.request.urlopen(req, timeout=timeout + 10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return res.get("result", [])

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "Markdown",
        reply_to_message_id: int | None = None,
    ) -> dict:
        data: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        return self._api_call("sendMessage", data)

    def send_chat_action(self, chat_id: int | str, action: str = "typing") -> dict:
        return self._api_call("sendChatAction", {"chat_id": chat_id, "action": action})

    def send_video(
        self,
        chat_id: int | str,
        video_path: Path,
        caption: str = "",
        parse_mode: str = "Markdown",
        reply_to_message_id: int | None = None,
    ) -> dict:
        """Gửi video file multipart lên Telegram (hỗ trợ file <= 50MB)."""
        import requests

        url = f"{self.base_url}/sendVideo"
        data: dict[str, Any] = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        with open(video_path, "rb") as f:
            files = {"video": (video_path.name, f, "video/mp4")}
            resp = requests.post(url, data=data, files=files, timeout=300)
            res = resp.json()
            if not res.get("ok"):
                raise RuntimeError(f"Telegram sendVideo error: {res.get('description')}")
            return res.get("result", {})


class TelegramBotService:
    """Service chạy nền xử lý tin nhắn và điều khiển Studio 24/7."""

    def __init__(self, config_path: str = r"D:\K-Tube-Studio\config.yaml"):
        self.config_path = config_path
        self.cfg = load_config(config_path)
        self.client: TelegramBotClient | None = None
        self._thread: threading.Thread | None = None
        self._worker_thread: threading.Thread | None = None
        self._running = False
        self._queue: queue.Queue = queue.Queue()
        self.current_job: dict | None = None
        self.bot_info: dict = {}

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        if self.is_running():
            return True
        self.cfg = load_config(self.config_path)
        token = (self.cfg.telegram.get("bot_token") or "").strip()
        if not token:
            log("telegram", "Chưa cấu hình telegram.bot_token")
            return False

        try:
            self.client = TelegramBotClient(token)
            self.bot_info = self.client.get_me()
            log("telegram", f"Khởi động Telegram Bot @{self.bot_info.get('username')} thành công")
        except Exception as e:
            log("telegram", f"Không thể kết nối Telegram Bot: {e}")
            return False

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="TelegramBotPoll")
        self._worker_thread = threading.Thread(target=self._process_queue_loop, daemon=True, name="TelegramBotWorker")
        self._thread.start()
        self._worker_thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        log("telegram", "Đã dừng Telegram Bot")

    def _is_authorized(self, chat_id: int | str) -> bool:
        admin_ids = self.cfg.telegram.get("admin_chat_ids") or []
        if not admin_ids:
            return True  # Nếu không giới hạn admin, cho phép mọi người dùng
        str_id = str(chat_id)
        return any(str(a) == str_id for a in admin_ids)

    def _poll_loop(self) -> None:
        offset = None
        while self._running:
            try:
                if not self.client:
                    time.sleep(2)
                    continue
                updates = self.client.get_updates(offset=offset, timeout=15)
                for u in updates:
                    offset = u["update_id"] + 1
                    msg = u.get("message")
                    if msg:
                        self._handle_message(msg)
            except Exception as e:
                if self._running:
                    time.sleep(3)

    def _handle_message(self, msg: dict) -> None:
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = (msg.get("text") or "").strip()
        msg_id = msg.get("message_id")

        if not text or not chat_id:
            return

        # Kiểm tra quyền truy cập
        if not self._is_authorized(chat_id):
            deny_text = (
                f"⛔ *Quyền truy cập bị từ chối!*\n\n"
                f"Tài khoản của bạn chưa được cấp phép điều khiển bot này.\n"
                f"• Chat ID của bạn: `{chat_id}`\n\n"
                f"Vui lòng thêm Chat ID trên vào mục `telegram.admin_chat_ids` trong `config.yaml`."
            )
            self.client.send_message(chat_id, deny_text, reply_to_message_id=msg_id)
            return

        # Xử lý các lệnh Slash
        if text.startswith("/"):
            cmd = text.split()[0].lower()
            if cmd in ("/start", "/help"):
                self._cmd_start(chat_id)
            elif cmd == "/status":
                self._cmd_status(chat_id)
            elif cmd == "/voices":
                self._cmd_voices(chat_id)
            elif cmd == "/cancel":
                self._cmd_cancel(chat_id)
            else:
                self.client.send_message(
                    chat_id,
                    "❓ Lệnh không hợp lệ. Gõ /start hoặc /help để xem hướng dẫn.",
                    reply_to_message_id=msg_id,
                )
            return

        # Xử lý link video gửi đến
        extracted = extract_url(text)
        if extracted.startswith("http://") or extracted.startswith("https://"):
            self._queue.put({"url": extracted, "chat_id": chat_id, "msg_id": msg_id, "text": text})
            q_size = self._queue.qsize()
            ack_text = (
                f"📥 *Đã nhận yêu cầu xử lý video!*\n\n"
                f"🔗 *Link:* `{extracted}`\n"
                f"📊 *Vị trí hàng đợi:* #{q_size}\n\n"
                f"🚀 Bot sẽ bắt đầu xử lý ngay khi tới lượt..."
            )
            self.client.send_message(chat_id, ack_text, reply_to_message_id=msg_id)
        else:
            self.client.send_message(
                chat_id,
                "💡 Hãy gửi một đường link video (TikTok, Douyin, Facebook, YouTube...) để tôi tự động xử lý giúp bạn!",
                reply_to_message_id=msg_id,
            )

    def _cmd_start(self, chat_id: int | str) -> None:
        msg = (
            "🤖 *Chào mừng bạn đến với K-Tube Studio AI 24/7!*\n\n"
            "Tôi là trợ lý tự động hóa reup & dịch video đa nền tảng.\n\n"
            "✨ *Các tính năng chính:*\n"
            "• 📥 *Tự động tải sạch:* Bóc tách video không watermark từ Douyin, TikTok, Facebook, Xiaohongshu...\n"
            "• 🎙️ *Lồng tiếng CapCut AI:* Hỗ trợ hơn 24 giọng đọc hot trend (Thanh Niên, Nhỏ Ngọt Ngào, Nam Trầm...).\n"
            "• 🎭 *Phân vai Nam - Nữ:* Tự động chia vai đọc hội thoại thông minh.\n"
            "• 🎬 *Render xuất bản:* Tự động ghép phụ đề đẹp mắt và nhạc nền sống động.\n\n"
            "📌 *Cách dùng:* Chỉ cần dán link video vào đây, tôi sẽ xử lý từ A-Z!\n\n"
            "⚙️ *Lệnh hỗ trợ:*\n"
            "• /status - Xem trạng thái hoạt động & hàng đợi\n"
            "• /voices - Danh sách giọng đọc AI nổi bật\n"
            "• /cancel - Hủy video đang xử lý\n"
            "• /help - Xem lại hướng dẫn này"
        )
        self.client.send_message(chat_id, msg)

    def _cmd_status(self, chat_id: int | str) -> None:
        q_len = self._queue.qsize()
        curr = self.current_job
        status_text = (
            "📊 *Báo cáo trạng thái K-Tube Studio:*\n\n"
            f"• 🟢 *Bot:* Đang hoạt động 24/7\n"
            f"• 🎙️ *Engine TTS:* `{self.cfg.tts.engine}` (Giọng: `{self.cfg.tts.capcut_voice}`)\n"
            f"• 🌐 *Dịch thuật:* `{self.cfg.translate.provider}` -> `{self.cfg.translate.target_lang}`\n"
            f"• ⏳ *Hàng đợi chờ:* `{q_len}` video\n"
        )
        if curr:
            status_text += f"\n⚙️ *Đang xử lý:* `{curr.get('url', '')[:60]}...`\n⏱️ Bắt đầu lúc: `{curr.get('start_time', '')}`"
        else:
            status_text += "\n💤 *Hệ thống đang rảnh, sẵn sàng nhận video mới!*"
        self.client.send_message(chat_id, status_text)

    def _cmd_voices(self, chat_id: int | str) -> None:
        voices_text = (
            "🎙️ *Danh sách giọng đọc CapCut TTS hot trend:*\n\n"
            "• `BV075_streaming` - Thanh Niên Tự Tin (Review công nghệ, tin tức)\n"
            "• `BV421_vivn_streaming` - Nhỏ Ngọt Ngào (Kể chuyện, ẩm thực, tâm sự)\n"
            "• `multi_male_felipe_uranus_bigtts` - Nam Trầm (Review phim, khám phá)\n"
            "• `multi_female_richgirl_uranus_bigtts` - Nữ Sang Trọng (Review phim new)\n"
            "• `BV074_streaming` - Nữ Nhí Nhảnh (Trend vui nhộn)\n"
            "• `BV004_streaming` - MC Thời Sự (Chuyên nghiệp)\n\n"
            "💡 Giọng đọc mặc định hiện tại: `" + str(self.cfg.tts.capcut_voice) + "`"
        )
        self.client.send_message(chat_id, voices_text)

    def _cmd_cancel(self, chat_id: int | str) -> None:
        if self.current_job:
            self.client.send_message(chat_id, "⚠️ Đang gửi tín hiệu hủy tiến trình hiện tại...")
        else:
            self.client.send_message(chat_id, "ℹ️ Hiện không có tiến trình nào đang chạy.")

    def _process_queue_loop(self) -> None:
        """Vòng lặp lấy job từ queue và chạy pipeline."""
        while self._running:
            try:
                job_req = self._queue.get(timeout=2.0)
            except queue.Empty:
                continue

            url = job_req["url"]
            chat_id = job_req["chat_id"]
            msg_id = job_req.get("msg_id")

            self.current_job = {
                "url": url,
                "chat_id": chat_id,
                "start_time": time.strftime("%H:%M:%S"),
            }

            try:
                self._run_job_flow(url, chat_id, msg_id)
            except Exception as e:
                log("telegram", f"Lỗi xử lý job từ bot: {e}")
                err_text = f"❌ *Xử lý thất bại!*\n\n🔗 *Link:* `{url}`\n⚠️ *Lỗi:* `{str(e)[:400]}`"
                if self.client:
                    self.client.send_message(chat_id, err_text, reply_to_message_id=msg_id)
            finally:
                self.current_job = None
                self._queue.task_done()

    def _run_job_flow(self, url: str, chat_id: int | str, msg_id: int | None) -> None:
        from .pipeline import run_job

        if self.client:
            self.client.send_chat_action(chat_id, "record_video")
            self.client.send_message(
                chat_id,
                f"🚀 *Bắt đầu quy trình tự động:* `{url}`\n"
                f"1️⃣ Tải video sạch (No Watermark)\n"
                f"2️⃣ Nhận diện âm thanh & Dịch sang tiếng Việt\n"
                f"3️⃣ Lồng tiếng AI CapCut\n"
                f"4️⃣ Render xuất bản",
                reply_to_message_id=msg_id,
            )

        start_t = time.time()
        final_video_path = run_job(url, self.cfg)
        elapsed = time.time() - start_t

        if not final_video_path or not final_video_path.exists():
            raise RuntimeError("Pipeline hoàn tất nhưng không tìm thấy file video đích.")

        size_bytes = final_video_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        done_caption = (
            f"✅ *Render hoàn tất!* (⏱️ {elapsed:.1f}s)\n"
            f"🎬 *File:* `{final_video_path.name}`\n"
            f"📦 *Dung lượng:* `{size_mb:.2f} MB`\n"
            f"🎙️ *Giọng:* `{self.cfg.tts.capcut_voice}`"
        )

        send_video = self.cfg.telegram.get("send_video", True)
        # Telegram Bot upload limit là 50MB
        if send_video and size_mb <= 49.5:
            if self.client:
                self.client.send_chat_action(chat_id, "upload_video")
                self.client.send_video(
                    chat_id,
                    final_video_path,
                    caption=done_caption,
                    reply_to_message_id=msg_id,
                )
        else:
            if self.client:
                done_caption += f"\n\n📂 *Đường dẫn lưu trên máy:*\n`{final_video_path}`"
                self.client.send_message(chat_id, done_caption, reply_to_message_id=msg_id)


# Global singleton instance
_bot_instance: TelegramBotService | None = None


def get_telegram_service() -> TelegramBotService:
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TelegramBotService()
    return _bot_instance

