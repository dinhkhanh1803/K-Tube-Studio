"""Tách giọng nói khỏi nhạc nền (UVR/MDX qua thư viện audio-separator) — tùy chọn.

Cài:  pip install "audio-separator[gpu]"   (hoặc [cpu])
Không cài thì pipeline vẫn chạy: tiếng gốc được giữ ở âm lượng thấp dưới giọng lồng.
"""
from __future__ import annotations

from pathlib import Path

from .util import ROOT, log


def available() -> bool:
    try:
        import audio_separator  # noqa: F401
        return True
    except ImportError:
        return False


def separate(audio_wav: Path, job: Path, acfg) -> tuple[Path, Path] | None:
    vocals, bgm = job / "vocals.wav", job / "bgm.wav"
    if vocals.exists() and bgm.exists():
        return vocals, bgm
    if acfg.separate == "off":
        return None
    if not available():
        if acfg.separate == "on":
            raise RuntimeError('audio.separate=on nhưng chưa cài: pip install "audio-separator[gpu]"')
        log("separate", "Chưa cài audio-separator -> bỏ qua tách nhạc nền (giữ tiếng gốc nhỏ)")
        return None

    from audio_separator.separator import Separator

    out_dir = job / "sep"
    out_dir.mkdir(exist_ok=True)
    log("separate", f"Tách giọng bằng {acfg.separator_model} ...")
    sep = Separator(output_dir=str(out_dir), output_format="WAV", model_file_dir=str(ROOT / "models" / "uvr"))
    sep.load_model(model_filename=acfg.separator_model)
    files = [out_dir / Path(f).name for f in sep.separate(str(audio_wav))]
    voc = next((f for f in files if "vocal" in f.name.lower()), None)
    ins = next((f for f in files if "instrument" in f.name.lower()), None)
    if not (voc and ins):
        raise RuntimeError(f"audio-separator trả về file không nhận ra: {files}")
    voc.replace(vocals)
    ins.replace(bgm)
    return vocals, bgm
