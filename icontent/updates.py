"""Phiên bản mới: kiểm tra Releases công khai của UPDATE_REPO trên GitHub, giống iNew của cùng tác giả (dienmoc86/iNew-releases).

Bộ cài (iContent-Setup-x.y.z.exe) là tệp đính kèm của release có tag "vX.Y.Z", nội dung release là phần "có gì mới".
Kiểm tra lúc mở và mỗi 12 giờ ở luồng nền; trang chỉ đọc kết quả đã lưu, mất mạng không làm chậm trang nào.

Cập nhật một chạm (chỉ bản cài bằng Setup.exe trên Windows): tải bộ cài về %LOCALAPPDATA%\\iContent\\updates, so SHA-256
GitHub công bố, chạy bộ cài ở chế độ im lặng (/SILENT, chỉ hiện thanh tiến độ) với /RELAUNCH=1 để cài xong tự mở lại iContent,
rồi đóng cửa sổ và tắt máy chủ (bộ cài cần chép đè file và chạy lại setup.ps1). Video, cài đặt, key và kích hoạt giữ nguyên.
Bản chạy từ mã nguồn (máy tác giả, có .git) chỉ được báo có bản mới, không tự cài đè.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from . import __version__
from .util import ROOT, log

UPDATE_REPO = "dienmoc86/iContent-releases"
CHECK_INTERVAL = 12 * 3600
FIRST_CHECK = 20          # giây sau khi mở: để máy chủ nạp xong trước
API = "https://api.github.com/repos/{repo}/releases/latest"

_lock = threading.Lock()
_state: dict = {"available": False, "latest": None, "url": None, "download_url": None, "size": 0, "sha256": "",
                "notes": "", "checked_at": None, "error": None,
                "dl": {"state": "idle", "done": 0, "total": 0, "path": "", "error": ""}}


def version_tuple(v: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", v or "")
    return tuple(int(n) for n in nums[:4]) or (0,)


def is_newer(latest: str, current: str) -> bool:
    return version_tuple(latest) > version_tuple(current)


def _pick_asset(assets: list) -> dict | None:
    """Bộ cài cho máy này. Windows: file .exe. Chưa có bộ cài cho hệ điều hành khác thì None (chỉ mở trang release)."""
    if not sys.platform.startswith("win"):
        return None
    exes = [a for a in assets or [] if str(a.get("name", "")).lower().endswith(".exe")]
    return exes[0] if exes else None


def installed_build() -> bool:
    """Bản cài bằng Setup.exe (có Python kèm theo và thông tin đóng gói), không phải thư mục mã nguồn của tác giả."""
    from .license import _build_info
    return sys.platform.startswith("win") and _build_info() is not None and (ROOT / "runtime" / "python").is_dir() \
        and not (ROOT / ".git").exists()


def update_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or ROOT) / "iContent" / "updates"


def snapshot() -> dict:
    with _lock:
        d = json.loads(json.dumps(_state))
    d.update(current=__version__, enabled=bool(UPDATE_REPO), can_install=installed_build())
    return d


def plain_notes(body: str) -> str:
    """Nội dung release viết kiểu Markdown của GitHub -> chữ thường cho khung "Có gì mới" (hiện dạng chữ thô).
    Bỏ phần "Tải về" trở đi: trong app đã có nút cập nhật."""
    out = []
    for line in str(body or "").replace("\r\n", "\n").split("\n"):
        t = re.sub(r"\*\*|__|`", "", line).rstrip()
        t = re.sub(r"^#{1,6}\s*", "", t)
        if t.strip().lower().rstrip(":") in ("tải về", "download", "downloads"):
            break
        out.append(t)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()[:4000]


def apply_release(data: dict) -> None:
    """Ghi kết quả từ JSON của GitHub (tách riêng để kiểm thử không cần mạng)."""
    tag = str(data.get("tag_name") or "")
    asset = _pick_asset(data.get("assets") or []) or {}
    digest = str(asset.get("digest") or "")
    with _lock:
        newer = is_newer(tag, __version__)
        if _state["latest"] != (tag.lstrip("vV") or None):      # bản khác bản đã tải dở: bỏ phần tải cũ
            _state["dl"] = {"state": "idle", "done": 0, "total": 0, "path": "", "error": ""}
        _state.update(available=newer, latest=tag.lstrip("vV") or None, url=data.get("html_url"),
                      download_url=asset.get("browser_download_url"), size=int(asset.get("size") or 0),
                      sha256=digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else "",
                      notes=plain_notes(data.get("body") or ""), error=None)


def check_now(timeout: float = 10.0) -> dict:
    if not UPDATE_REPO:
        return snapshot()
    req = urllib.request.Request(API.format(repo=UPDATE_REPO), headers={
        "Accept": "application/vnd.github+json", "User-Agent": f"iContent/{__version__}"})
    try:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                apply_release(json.loads(r.read().decode("utf-8")))
        except urllib.error.HTTPError as e:
            if e.code != 404:      # 404: chưa đăng bản nào
                raise
            with _lock:
                _state.update(available=False, latest=None, url=None, download_url=None, notes="", error=None)
    except Exception as e:      # noqa: BLE001 — mất mạng, GitHub chặn tần suất: coi như chưa biết, lần sau thử lại
        with _lock:
            _state["error"] = f"{type(e).__name__}: {e}"[:200]
    with _lock:
        _state["checked_at"] = time.time()
    return snapshot()


def start_background() -> None:
    def loop() -> None:
        time.sleep(FIRST_CHECK)
        while True:
            check_now()
            s = snapshot()
            if s["available"]:
                log("ui", f"Đã có iContent {s['latest']} (đang dùng {__version__})")
            time.sleep(CHECK_INTERVAL)

    threading.Thread(target=loop, daemon=True, name="ui-update-check").start()


# ------------------------------------------------------------------ tải và cài
def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _download(url: str, size: int, sha: str, dst: Path) -> None:
    part = dst.with_name(dst.name + ".part")
    dst.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": f"iContent/{__version__}"})
    with urllib.request.urlopen(req, timeout=30) as r, open(part, "wb") as f:
        total = int(r.headers.get("Content-Length") or size or 0)
        with _lock:
            _state["dl"].update(total=total, done=0)
        while True:
            b = r.read(256 * 1024)
            if not b:
                break
            f.write(b)
            with _lock:
                _state["dl"]["done"] += len(b)
    got = part.stat().st_size
    if total and got != total:
        raise RuntimeError(f"Tải chưa đủ ({got // 1_000_000}/{total // 1_000_000} MB). Kiểm tra mạng rồi bấm Cập nhật lại.")
    if sha and _sha256(part) != sha:
        part.unlink(missing_ok=True)
        raise RuntimeError("Bộ cài tải về không khớp mã kiểm tra của bản phát hành (có thể bị hỏng trên đường tải). Bấm Cập nhật lại.")
    part.replace(dst)


def start_download() -> dict:
    s = snapshot()
    if not s["available"] or not s["download_url"]:
        raise ValueError("Chưa có bản mới để tải.")
    if s["dl"]["state"] in ("downloading", "ready"):
        return s
    dst = update_dir() / f"iContent-Setup-{s['latest']}.exe"
    with _lock:
        _state["dl"] = {"state": "downloading", "done": 0, "total": s["size"], "path": str(dst), "error": ""}

    def run() -> None:
        try:
            if dst.exists() and (not s["sha256"] or _sha256(dst) == s["sha256"]) and (not s["size"] or dst.stat().st_size == s["size"]):
                pass      # đã tải từ lần trước
            else:
                _download(s["download_url"], s["size"], s["sha256"], dst)
            with _lock:
                _state["dl"].update(state="ready", done=dst.stat().st_size, total=dst.stat().st_size)
            for old in update_dir().glob("iContent-Setup-*.exe"):      # bộ cài các bản cũ hơn: không còn dùng
                if old != dst:
                    old.unlink(missing_ok=True)
        except Exception as e:      # noqa: BLE001
            with _lock:
                _state["dl"].update(state="error", error=str(e)[:300])
            log("ui", f"Tải bản cập nhật lỗi: {e}")

    threading.Thread(target=run, daemon=True, name="ui-update-download").start()
    return snapshot()


def installer_cmd(exe: Path) -> list[str]:
    """/SILENT: không hỏi gì, chỉ hiện thanh tiến độ (cả bước cài thư viện). /RELAUNCH=1: cài xong tự mở lại iContent
    (bộ cài thêm mục [Run] riêng cho tham số này; bản thường vẫn để khách tự bấm "Mở iContent ngay")."""
    return [str(exe), "/SILENT", "/SP-", "/NOCANCEL", "/NORESTART", "/RELAUNCH=1"]


def launch_installer() -> Path:
    s = snapshot()
    if not s["can_install"]:
        raise ValueError("Bản này chạy từ mã nguồn, không tự cài đè được. Tải bộ cài ở trang phát hành.")
    exe = Path(s["dl"]["path"] or "")
    if s["dl"]["state"] != "ready" or not exe.is_file():
        raise ValueError("Bộ cài chưa tải xong.")
    flags = 0
    if os.name == "nt":      # tách khỏi iContent: iContent tắt thì bộ cài vẫn chạy tiếp
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | 0x01000000      # CREATE_BREAKAWAY_FROM_JOB
    try:
        subprocess.Popen(installer_cmd(exe), cwd=str(exe.parent), creationflags=flags, close_fds=True)
    except OSError:
        if not flags:
            raise
        subprocess.Popen(installer_cmd(exe), cwd=str(exe.parent), creationflags=flags & ~0x01000000, close_fds=True)
    log("ui", f"Đang cài iContent {s['latest']}: {exe.name}")
    return exe


def close_windows() -> int:
    """Đóng cửa sổ iContent (Edge/Chrome chế độ ứng dụng) trước khi bộ cài chạy: không để lại cửa sổ báo mất kết nối."""
    if os.name != "nt":
        return 0
    import ctypes
    from ctypes import wintypes

    from .appwin import TITLE_MARKS
    user32 = ctypes.windll.user32
    hwnds: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd)
        if n and user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            cls = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, cls, 64)
            if cls.value.startswith("Chrome_WidgetWin") and any(m in buf.value for m in TITLE_MARKS):      # chỉ cửa sổ Edge/Chrome
                hwnds.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    for h in hwnds:
        user32.PostMessageW(h, 0x0010, 0, 0)      # WM_CLOSE
    return len(hwnds)
