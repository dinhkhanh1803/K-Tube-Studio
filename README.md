# K-Tube Studio

Nền tảng AI sản xuất video tự động đa nền tảng (Douyin, TikTok, YouTube Shorts, Reels, Bilibili...) chạy hoàn toàn trên máy tính local qua giao diện Web.

---

## 🚀 Cách khởi động

### Cách 1: Chạy bản Web trên trình duyệt (Khuyên dùng)
Bấm đúp file:
```text
K-Tube Studio (Web).cmd
```
Hệ thống sẽ khởi động máy chủ FastAPI ngầm và tự động mở trình duyệt (Chrome/Edge/Brave) tại địa chỉ:
👉 **`http://localhost:8765`**

### Cách 2: Chạy bản cửa sổ ứng dụng Windows (App Mode)
Bấm đúp file:
```text
K-Tube Studio (App).cmd
```

---

## 🛠️ Cấu trúc dự án
- `icontent/`: Bộ mã nguồn Python chính:
  - `web/`: Backend FastAPI + Frontend HTML/CSS/JS (giao diện web tại `icontent/web/static/`).
  - `download.py`: Module tải video đa nền tảng (tích hợp chữ ký Douyin `x-secsdk-web-signature`).
  - `asr.py`: Module nhận dạng giọng nói bằng Faster-Whisper.
  - `translate.py`: Module dịch thuật theo ngữ cảnh qua LLM (Gemini, OpenAI, Claude...).
  - `tts.py`: Module lồng tiếng tự nhiên bằng VieNeu-TTS.
  - `render.py`: Module xóa sub gốc và đóng phụ đề động (TikTok style).
- `tools/`: Các công cụ nhị phân hỗ trợ (FFmpeg).
- `workspace/`: Nơi lưu trữ video tải về và các dự án dựng video.
- `config.yaml`: File cấu hình chung của hệ thống.
- `cookies.txt`: Cookie phiên hỗ trợ tải video Douyin/TikTok.
- `keys.json`: Lưu trữ các API key AI (Gemini, OpenAI,...).

---

## 🌟 Tính năng nổi bật
1. **Bản quyền vĩnh viễn (K-Tube Studio Pro):** Đã gỡ bỏ toàn bộ ràng buộc license, mã máy và bot Telegram.
2. **Hỗ trợ tải video Douyin mượt mà:** Tự động tạo chữ ký bảo mật để tải video không bị chặn (HTTP 403).
3. **Làm chủ mã nguồn 100%:** Dễ dàng can thiệp, bổ sung API mới, thay đổi giao diện web theo ý muốn.
