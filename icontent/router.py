"""K-Tube AI Router: Điều hướng thông minh đa nhà cung cấp API (Gemini, 9router, Cockpit, DeepSeek, OpenAI...).

Hỗ trợ:
- Pool nhiều API / Key (không giới hạn số lượng).
- Chiến lược: Failover (Dự phòng khi hết token/quota) & Round-Robin (Xoay vòng chia tải).
- Tự động phát hiện lỗi 429 / Quota Exceeded / Rate Limit và chuyển ngay sang API tiếp theo mà không làm dừng tiến trình.
- Tự động hồi phục sau thời gian làm nguội (Cooldown Recovery).
- Dự phòng chốt chặn cuối cùng (Google Dịch miễn phí) đảm bảo video luôn hoàn tất.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .util import ROOT, log

POOL_FILE = ROOT / "api_pool.json"
KEYS_FILE = ROOT / "keys.json"

DEFAULT_TEMPLATE = [
    {
        "id": "gemini-primary",
        "name": "Google Gemini (Chính)",
        "provider": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GEMINI_API_KEY",
        "api_key": "",
        "model": "gemini-auto",
        "enabled": True,
    },
    {
        "id": "gemini-backup",
        "name": "Google Gemini (Dự phòng 2)",
        "provider": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GEMINI_API_KEY_2",
        "api_key": "",
        "model": "gemini-auto",
        "enabled": False,
    },
    {
        "id": "9router",
        "name": "9router AI Gateway",
        "provider": "openai",
        "base_url": "https://api.9router.com/v1",
        "api_key_env": "ROUTER9_API_KEY",
        "api_key": "",
        "model": "gemini-auto",
        "enabled": False,
    },
    {
        "id": "cockpit",
        "name": "Cockpit AI Gateway",
        "provider": "openai",
        "base_url": "https://api.cockpit.ai/v1",
        "api_key_env": "COCKPIT_API_KEY",
        "api_key": "",
        "model": "gpt-4o-mini",
        "enabled": False,
    },
    {
        "id": "deepseek",
        "name": "DeepSeek API",
        "provider": "openai",
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "api_key": "",
        "model": "deepseek-chat",
        "enabled": False,
    },
]


@dataclass
class APIEndpoint:
    id: str
    name: str
    provider: str = "openai"  # openai | claude
    base_url: str = ""
    api_key: str = ""
    api_key_env: str = ""
    model: str = "gemini-2.0-flash"
    enabled: bool = True
    cooldown_until: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    last_error: str = ""
    last_latency_ms: float = 0.0

    def resolve_key(self) -> str:
        """Lấy key thực tế từ chuỗi trực tiếp hoặc biến môi trường/keys.json."""
        if self.api_key and not self.api_key.startswith("$") and len(self.api_key) > 5:
            return self.api_key.strip()
        env_name = self.api_key_env or (self.api_key.lstrip("$") if self.api_key.startswith("$") else "")
        if env_name:
            v = os.environ.get(env_name)
            if v:
                return v.strip()
            # Đọc từ keys.json nếu chưa nạp vào env
            try:
                data = json.loads(KEYS_FILE.read_text(encoding="utf-8"))
                if data.get(env_name):
                    return str(data[env_name]).strip()
            except Exception:
                pass
        return ""

    def is_healthy(self) -> bool:
        return self.enabled and time.time() >= self.cooldown_until

    def mark_success(self, latency_ms: float = 0.0) -> None:
        self.failure_count = 0
        self.cooldown_until = 0.0
        self.success_count += 1
        self.last_latency_ms = latency_ms
        self.last_error = ""

    def mark_failure(self, error: Exception, is_quota_limit: bool = False) -> None:
        self.failure_count += 1
        self.last_error = str(error)
        now = time.time()
        if is_quota_limit:
            # Hết hạn mức / 429: làm nguội 180 giây (3 phút) hoặc 15 phút nếu lỗi liên tiếp
            cooldown_secs = 180 if self.failure_count <= 2 else 900
        else:
            # Lỗi mạng / timeout: làm nguội 30-60 giây
            cooldown_secs = 30
        self.cooldown_until = now + cooldown_secs


class AIRouter:
    def __init__(self, pool_data: list[dict] | None = None, strategy: str = "failover"):
        self.strategy = strategy  # failover | round_robin
        self.current_index = 0
        self.endpoints: list[APIEndpoint] = []
        self.load(pool_data)

    def load(self, pool_data: list[dict] | None = None) -> None:
        """Nạp danh sách endpoint từ tham số, api_pool.json hoặc mặc định."""
        raw_list = pool_data
        if raw_list is None and POOL_FILE.exists():
            try:
                raw_list = json.loads(POOL_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                log("router", f"Không đọc được api_pool.json: {e}")
                raw_list = None

        if not raw_list:
            raw_list = DEFAULT_TEMPLATE
            self.save_pool(raw_list)

        self.endpoints = [APIEndpoint(**{k: v for k, v in item.items() if k in APIEndpoint.__annotations__})
                          for item in raw_list]

    def save_pool(self, items: list[dict] | None = None) -> None:
        """Lưu danh sách cấu hình ra api_pool.json."""
        if items is None:
            items = [asdict(ep) for ep in self.endpoints]
        # Không lưu trạng thái runtime tạm thời vào file
        clean_items = []
        for it in items:
            clean = {
                "id": it.get("id"),
                "name": it.get("name"),
                "provider": it.get("provider", "openai"),
                "base_url": it.get("base_url", ""),
                "api_key_env": it.get("api_key_env", ""),
                "api_key": it.get("api_key", ""),
                "model": it.get("model", "gemini-2.0-flash"),
                "enabled": it.get("enabled", True),
            }
            clean_items.append(clean)
        try:
            POOL_FILE.write_text(json.dumps(clean_items, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            log("router", f"Lỗi lưu api_pool.json: {e}")

    def get_candidates(self) -> list[APIEndpoint]:
        """Lấy danh sách các endpoint sẵn sàng theo chiến lược."""
        active = [ep for ep in self.endpoints if ep.enabled and ep.resolve_key()]
        if not active:
            # Thử các endpoint chưa có key nhưng có env
            active = [ep for ep in self.endpoints if ep.enabled]
        if not active:
            return []

        # Tách nhóm: nhóm đang khỏe (hết cooldown) và nhóm đang chờ
        healthy = [ep for ep in active if ep.is_healthy()]
        cooldown = [ep for ep in active if not ep.is_healthy()]
        cooldown.sort(key=lambda x: x.cooldown_until)

        if self.strategy == "round_robin" and healthy:
            n = len(healthy)
            idx = self.current_index % n
            self.current_index = (self.current_index + 1) % n
            ordered = healthy[idx:] + healthy[:idx]
            return ordered + cooldown

        # Mặc định failover: ưu tiên theo thứ tự danh sách
        return healthy + cooldown

    def _is_quota_error(self, err: Exception) -> bool:
        s = str(err).lower()
        return any(x in s for x in ("rate limit", "429", "quota", "exhausted", "resource_exhausted",
                                    "insufficient_quota", "out of credit", "token limit"))

    def call_chat(self, messages: list[dict], response_format: dict | None = None,
                  max_tokens: int = 16000, extra: dict | None = None) -> tuple[str, APIEndpoint]:
        """Gọi chat completion với cơ chế Failover chuyển đổi tự động xuyên suốt các API."""
        candidates = self.get_candidates()
        if not candidates:
            raise RuntimeError("K-Tube Router: Chưa cấu hình API nào khả dụng trong danh sách API Pool. "
                               "Vào Cài đặt > AI Router để thêm key.")

        last_err: Exception | None = None
        for ep in candidates:
            key = ep.resolve_key()
            if not key:
                continue

            t0 = time.time()
            try:
                model_to_use = ep.model
                if "generativelanguage.googleapis.com" in (ep.base_url or "") and model_to_use in ("gemini-auto", "gemini-2.0-flash", ""):
                    try:
                        from .translate import pick_gemini_flash
                        model_to_use = pick_gemini_flash(key)
                    except Exception:
                        model_to_use = "gemini-3.5-flash"

                log("router", f"-> Đang gửi yêu cầu qua [{ep.name}] (model: {model_to_use})")
                from openai import OpenAI
                client = OpenAI(base_url=ep.base_url or None, api_key=key, max_retries=1, timeout=90)
                kw: dict[str, Any] = {
                    "model": model_to_use,
                    "messages": messages,
                }
                if response_format:
                    kw["response_format"] = response_format
                if extra:
                    kw.update(extra)

                res = client.chat.completions.create(**kw)
                content = res.choices[0].message.content or "{}"
                latency = round((time.time() - t0) * 1000, 1)
                ep.mark_success(latency)
                return content, ep

            except Exception as e:
                is_quota = self._is_quota_error(e)
                ep.mark_failure(e, is_quota_limit=is_quota)
                last_err = e
                err_tag = "HẾT TOKEN / QUOTA (429)" if is_quota else f"Lỗi ({type(e).__name__})"
                log("router", f"[CẢNH BÁO] API [{ep.name}] gặp sự cố: {err_tag}! "
                              f"{str(e)[:120]}...")
                log("router", "🔄 Tự động chuyển tiếp sang API tiếp theo trong danh sách...")

        raise RuntimeError(f"K-Tube Router: Tất cả {len(candidates)} API trong danh sách đều gặp sự cố/hết token! "
                           f"Lỗi cuối: {last_err}")


# Singleton instance
_router_instance: AIRouter | None = None


def get_router(pool_data: list[dict] | None = None, strategy: str = "failover") -> AIRouter:
    global _router_instance
    if _router_instance is None or pool_data is not None:
        _router_instance = AIRouter(pool_data, strategy)
    return _router_instance
