"""Turning segments into plain text, timestamped text and SRT subtitles."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ross_transcribe.engine import Segment


def clock(seconds: float) -> str:
    """``65.2`` → ``1:05``; ``3725`` → ``1:02:05``."""
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def srt_time(seconds: float) -> str:
    """``5.12`` → ``00:00:05,120`` (SRT uses a comma before milliseconds)."""
    ms = round(max(seconds, 0.0) * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_text(segments: Iterable[Segment], timestamps: bool = False) -> str:
    segments = [s for s in segments if s.text]
    if timestamps:
        return "\n".join(f"[{clock(s.start)}] {s.text}" for s in segments) + "\n"
    return " ".join(s.text for s in segments) + "\n"


def to_srt(segments: Iterable[Segment]) -> str:
    blocks = []
    for i, s in enumerate((s for s in segments if s.text), start=1):
        blocks.append(f"{i}\n{srt_time(s.start)} --> {srt_time(s.end)}\n{s.text}\n")
    return "\n".join(blocks)


def output_path(media: Path, suffix: str, out_dir: Path | None = None) -> Path:
    """Where ``media``'s transcript goes: next to it, or inside ``out_dir``."""
    folder = out_dir if out_dir is not None else media.parent
    return folder / f"{media.stem}{suffix}"
