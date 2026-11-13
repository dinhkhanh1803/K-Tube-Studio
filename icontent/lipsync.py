"""Khớp khẩu hình & biểu cảm khuôn mặt nhân vật theo giọng nói (Lip-Sync AI).

Chi phí tối ưu (~0,01 USD/cảnh = ~250 VNĐ) qua API chính thức:
  fal        Fal.ai SadTalker (fal-ai/sadtalker) - nhanh, tự nhiên, hỗ trợ giữ nguyên bối cảnh ("full").
  replicate  Replicate SadTalker (cjwbw/sadtalker) - chớp mắt, cử động đầu và mấp máy môi khớp WAV.

Cách hoạt động:
  1. Lấy file âm thanh giọng đọc thật của cảnh (WAV/MP3).
  2. Lấy ảnh nhân vật/cảnh đã vẽ.
  3. Gọi API tạo clip chuyển động khuôn mặt khớp 100% thời lượng & nguyên âm của file âm thanh.
"""
from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

PROVIDERS = {
    "fal": {
        "name": "Fal.ai (Khớp khẩu hình SadTalker)",
        "keys": ["FAL_KEY"],
        "price_per_scene": 0.01,
        "get": "fal.ai/dashboard/keys",
        "note": "Chớp mắt, cử động đầu & mấp máy môi khớp 100% giọng nói (~250đ/cảnh)",
    },
    "replicate": {
        "name": "Replicate (Khớp khẩu hình SadTalker)",
        "keys": ["REPLICATE_API_TOKEN"],
        "price_per_scene": 0.01,
        "get": "replicate.com/account/api-tokens",
        "note": "Dự phòng thay thế Fal.ai, khớp khẩu hình trực tiếp từ ảnh & audio",
    },
}


class LipSyncError(RuntimeError):
    pass


def _key(name: str) -> str:
    return os.environ.get(name, "").strip()


def ready(provider: str = "") -> bool:
    if provider:
        p = PROVIDERS.get(provider)
        return bool(p) and all(_key(k) for k in p["keys"])
    return any(ready(k) for k in PROVIDERS)


def pick(provider: str = "") -> str:
    if provider and ready(provider):
        return provider
    for k in ("fal", "replicate"):
        if ready(k):
            return k
    return ""


def usable(provider: str = "") -> bool:
    from .paid import allowed
    return ready(provider) and allowed()


def public() -> list[dict]:
    out = []
    for k, v in PROVIDERS.items():
        out.append({
            "id": k,
            "name": v["name"],
            "ready": ready(k),
            "usable": usable(k),
            "price_per_scene": v["price_per_scene"],
            "keys": v["keys"],
            "get": v["get"],
            "note": v["note"],
        })
    return out


def _jpeg_data_uri(path: Path, max_side: int = 1024) -> str:
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert("RGB")
        if max(im.size) > max_side:
            im.thumbnail((max_side, max_side), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _audio_data_uri(wav_path: Path) -> str:
    """Nén WAV sang MP3 64kbps (nhẹ gấp 15 lần WAV) để gửi data URI qua API ổn định."""
    from .util import FFMPEG
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
        mp3 = Path(tf.name)
    try:
        cmd = [FFMPEG, "-y", "-i", str(wav_path), "-ar", "16000", "-ac", "1", "-b:a", "64k", str(mp3)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode == 0 and mp3.exists() and mp3.stat().st_size > 100:
            raw = mp3.read_bytes()
            mime = "audio/mpeg"
        else:
            raw = wav_path.read_bytes()
            mime = "audio/wav"
    finally:
        mp3.unlink(missing_ok=True)
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _req(method: str, url: str, headers: dict, body: dict | None = None, timeout: float = 90) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_txt = e.read().decode("utf-8", "replace")[:400]
        if e.code in (401, 403):
            raise LipSyncError("API Key khớp khẩu hình không hợp lệ hoặc chưa nạp tiền.") from None
        if e.code == 402:
            raise LipSyncError("Tài khoản hết credit. Nạp tối thiểu 1-5 USD để tiếp tục.") from None
        raise LipSyncError(f"Lỗi API Lip-Sync HTTP {e.code}: {err_txt}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise LipSyncError(f"Lỗi mạng khi kết nối API Lip-Sync: {e}") from None


def _download(url: str, timeout: float = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "KTubeStudio/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except Exception as e:
        raise LipSyncError(f"Không tải được video kết quả: {e}") from None
    if len(data) < 1000:
        raise LipSyncError("Video trả về bị rỗng hoặc hỏng.")
    return data


def _gen_fal(image: Path, audio: Path, report=None, check_cancel=None) -> bytes:
    key = _key("FAL_KEY")
    headers = {"Authorization": f"Key {key}"}
    payload = {
        "source_image_url": _jpeg_data_uri(image),
        "driven_audio_url": _audio_data_uri(audio),
        "preprocess": "full",
        "still_mode": False,
        "expression_scale": 1.0,
        "face_enhancer": "gfpgan",
    }
    if report:
        report("Đang gửi ảnh & giọng đọc lên Fal.ai SadTalker...")
    q = _req("POST", "https://queue.fal.run/fal-ai/sadtalker", headers, payload, timeout=120)
    status_url = q.get("status_url")
    resp_url = q.get("response_url")
    if not status_url or not resp_url:
        # Một số endpoint trả kết quả đồng bộ
        vid = (q.get("video") or {}).get("url")
        if vid:
            return _download(vid)
        raise LipSyncError(f"Phản hồi từ Fal.ai không hợp lệ: {str(q)[:200]}")

    t0 = time.time()
    while time.time() - t0 < 600:
        for _ in range(6):
            if check_cancel:
                check_cancel()
            time.sleep(0.5)
        st = _req("GET", status_url, headers, timeout=60)
        state = st.get("status")
        if report:
            report(f"Đang khớp khẩu hình ({int(time.time() - t0)}s)...")
        if state == "COMPLETED":
            res = _req("GET", resp_url, headers, timeout=60)
            vid = (res.get("video") or {}).get("url")
            if not vid:
                raise LipSyncError("Fal.ai xong nhưng không tìm thấy URL video.")
            return _download(vid)
        if state in ("FAILED", "ERROR"):
            raise LipSyncError(f"Fal.ai xử lý thất bại: {st.get('error') or 'Lỗi không rõ'}")
    raise LipSyncError("Quá thời gian chờ Fal.ai (10 phút).")


def _gen_replicate(image: Path, audio: Path, report=None, check_cancel=None) -> bytes:
    token = _key("REPLICATE_API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "version": "a519cc0cfebaaeade068b23899165a11ec76aaa1d2b313d40d214f204ec957a3",
        "input": {
            "source_image": _jpeg_data_uri(image),
            "driven_audio": _audio_data_uri(audio),
            "preprocess": "full",
            "still_mode": False,
            "use_enhancer": True,
            "use_eyeblink": True,
            "size_of_image": 512,
        },
    }
    if report:
        report("Đang gửi ảnh & giọng đọc lên Replicate SadTalker...")
    pred = _req("POST", "https://api.replicate.com/v1/predictions", headers, payload, timeout=120)
    get_url = (pred.get("urls") or {}).get("get")
    if not get_url:
        raise LipSyncError(f"Replicate trả về lỗi: {str(pred)[:200]}")

    t0 = time.time()
    while time.time() - t0 < 600:
        for _ in range(6):
            if check_cancel:
                check_cancel()
            time.sleep(0.5)
        st = _req("GET", get_url, headers, timeout=60)
        status_val = st.get("status")
        if report:
            report(f"Đang khớp khẩu hình ({int(time.time() - t0)}s)...")
        if status_val == "succeeded":
            out = st.get("output")
            vid = out[0] if isinstance(out, list) else out
            if not vid:
                raise LipSyncError("Replicate không trả về video.")
            return _download(str(vid))
        if status_val in ("failed", "canceled"):
            raise LipSyncError(f"Replicate thất bại: {st.get('error') or 'Lỗi'}")
    raise LipSyncError("Quá thời gian chờ Replicate.")


def generate(image: Path, audio: Path, provider: str = "", report=None, check_cancel=None) -> bytes:
    """Tạo video khớp khẩu hình từ ảnh + file audio WAV/MP3."""
    from .paid import allowed, block
    if not allowed():
        raise LipSyncError(block("Khớp khẩu hình AI (Lip-Sync, ~250đ/cảnh)", "Ảnh có máy quay chuyển động hoặc video nền miễn phí"))
    prov = pick(provider)
    if not prov:
        raise LipSyncError("Chưa có API Key khớp khẩu hình (FAL_KEY hoặc REPLICATE_API_TOKEN). Dán key ở mục Cài đặt > Khớp khẩu hình AI.")
    if not image.is_file():
        raise LipSyncError("Cảnh chưa có ảnh nhân vật để khớp khẩu hình.")
    if not audio.is_file():
        raise LipSyncError("Không tìm thấy file giọng đọc của cảnh này.")
    if prov == "fal":
        return _gen_fal(image, audio, report=report, check_cancel=check_cancel)
    return _gen_replicate(image, audio, report=report, check_cancel=check_cancel)

