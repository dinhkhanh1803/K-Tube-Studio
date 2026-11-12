# K-Tube Studio

Nền tảng AI sản xuất video tự động đa nền tảng (Douyin, TikTok, YouTube Shorts, Reels, Bilibili...) chạy hoàn toàn trên máy tính local qua giao diện Web.

---

## ⚡ Cài đặt nhanh (Dành cho người mới clone repo)

### 1. Yêu cầu hệ thống
- Hệ điều hành: **Windows 10 / 11 (64-bit)**
- **Python 3.10 - 3.12** (khi cài đặt nhớ tích chọn **"Add python.exe to PATH"**)
- **FFmpeg** (công cụ xử lý âm thanh/video)

### 2. Cài đặt tự động (1-Click Setup)
Bạn chỉ cần bấm đúp vào file:
```text
setup.cmd
```
*(Hoặc bấm trực tiếp `K-Tube Studio (Web).cmd` — hệ thống sẽ tự động phát hiện và chạy cài đặt nếu máy chưa có môi trường)*

Script sẽ tự động:
- Khởi tạo môi trường ảo Python (`.venv`)
- Cài đặt toàn bộ các thư viện cần thiết từ `requirements.txt`
- Kiểm tra FFmpeg (hướng dẫn cài qua `winget install Gyan.FFmpeg` nếu thiếu)
- Khởi tạo sẵn file `keys.json` từ `keys.example.json`

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

### Cách 3: Chạy qua lệnh (CLI / NPM)
```bash
npm start
# hoặc
pnpm start
# hoặc
ktube.cmd ui
```

---

## 🔑 Cấu hình API Key AI
Bạn có thể cấu hình API Key bằng một trong 2 cách:
1. **Nhập trực tiếp trên Web UI:** Vào mục **Cài đặt** trên giao diện Web (`http://localhost:8765`), nhập Gemini API Key hoặc OpenAI Key rồi bấm Lưu.
2. **Cấu hình file `keys.json`:** Mở file `keys.json` ở thư mục gốc và dán key của bạn vào:
```json
{
  "GEMINI_API_KEY": "AIzaSy..."
}
```

---

## 🛠️ Cấu trúc dự án
- `setup.cmd`: Script tự động cài đặt môi trường và thư viện 1-click.
- `icontent/`: Bộ mã nguồn Python chính:
  - `web/`: Backend FastAPI + Frontend HTML/CSS/JS (giao diện web tại `icontent/web/static/`).
  - `download.py`: Module tải video đa nền tảng (tích hợp chữ ký Douyin `x-secsdk-web-signature`).
  - `asr.py`: Module nhận dạng giọng nói bằng Faster-Whisper.
  - `translate.py`: Module dịch thuật theo ngữ cảnh qua LLM (Gemini, OpenAI, Claude...).
  - `tts.py`: Module lồng tiếng tự nhiên bằng VieNeu-TTS.
  - `render.py`: Module xóa sub gốc và đóng phụ đề động (TikTok style).
- `tools/`: Các công cụ nhị phân hỗ trợ (FFmpeg).
- `workspace/`: Nơi lưu trữ video tải về và các dự án dựng video.
- `config.example.yaml`: File cấu hình mẫu của hệ thống.
- `keys.example.json`: File mẫu lưu trữ API Key AI.

---

## 🌟 Tính năng nổi bật
1. **Bản quyền vĩnh viễn (K-Tube Studio Pro):** Đã gỡ bỏ toàn bộ ràng buộc license, mã máy và bot Telegram.
2. **Hỗ trợ tải video Douyin mượt mà:** Tự động tạo chữ ký bảo mật để tải video không bị chặn (HTTP 403).
3. **Làm chủ mã nguồn 100%:** Dễ dàng can thiệp, bổ sung API mới, thay đổi giao diện web theo ý muốn.
