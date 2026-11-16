"""
CapCut TTS API Python SDK & Package.

Pure Python client for CapCut Text-to-Speech (TTS), Speech-to-Text (STT),
and VOD chunked audio upload workflows.
"""

from icontent.capcut_tts.client import CapCutClient
from icontent.capcut_tts.exceptions import (
    CapCutAPIError,
    CapCutError,
    CapCutSignError,
    CapCutTaskError,
    CapCutUploadError,
)
from icontent.capcut_tts.models import (
    DeviceConfig,
    SubtitleResult,
    UploadResult,
    Utterance,
    VoiceInfo,
    Word,
)
from icontent.capcut_tts.action import TTSConfigurationError, build_tts_action, parse_provider_params

__version__ = "1.5.0"

__all__ = [
    "CapCutClient",
    "DeviceConfig",
    "UploadResult",
    "SubtitleResult",
    "Utterance",
    "Word",
    "VoiceInfo",
    "CapCutError",
    "CapCutAPIError",
    "CapCutUploadError",
    "CapCutSignError",
    "CapCutTaskError",
    "TTSConfigurationError",
    "build_tts_action",
    "parse_provider_params",
    "__version__",
]
