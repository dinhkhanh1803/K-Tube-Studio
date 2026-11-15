"""K-Tube Studio - Standalone 24/7 Telegram Bot & Channel Watchdog Runner.

Khởi động hệ thống trợ lý điều khiển từ xa và tự động giám sát kênh.
Chạy độc lập không cần mở trình duyệt web.
"""
import signal
import sys
import time
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from icontent.config import load_config
from icontent.telegram_bot import get_telegram_service
from icontent.util import log
from icontent.watchdog import get_watchdog_service


def main():
    print("=" * 65)
    print("   K-TUBE STUDIO - 24/7 AI TELEGRAM BOT & WATCHDOG ASSISTANT   ")
    print("=" * 65)

    cfg = load_config(str(ROOT / "config.yaml"))

    bot_token = (cfg.telegram.get("bot_token") or "").strip()
    if not bot_token:
        print("\n[!] CHÚ Ý: Chưa cấu hình telegram.bot_token trong config.yaml!")
        print("    Vui lòng mở config.yaml hoặc Web UI -> Cài đặt Telegram Bot để nhập token.")
        print("    Cách lấy token miễn phí:")
        print("    1. Mở Telegram, tìm bot @BotFather")
        print("    2. Gõ /newbot và làm theo hướng dẫn")
        print("    3. Dán token nhận được vào config.yaml tại mục telegram.bot_token\n")

    tg = get_telegram_service()
    wd = get_watchdog_service()

    tg_ok = tg.start() if bot_token else False
    wd_ok = wd.start()

    if tg_ok:
        print(f"[+] Telegram Bot @{tg.bot_info.get('username')} dang hoat dong 24/7...")
    else:
        print("[-] Telegram Bot tam tat (chua co token hoac loi ket noi).")

    if wd_ok:
        channels = cfg.watchdog.get("channels") or []
        print(f"[+] Watchdog Channel Monitor dang chay (theo doi {len(channels)} kenh)...")

    print("\nHe thong san sang! Nhan Ctrl+C de dung.\n" + "-" * 65)

    stop_requested = False

    def _sig_handler(sig, frame):
        nonlocal stop_requested
        print("\nDang dung dich vu Telegram Bot & Watchdog...")
        stop_requested = True
        tg.stop()
        wd.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    while not stop_requested:
        time.sleep(1.0)


if __name__ == "__main__":
    main()

