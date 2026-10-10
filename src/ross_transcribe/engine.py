"""Decoding (ffmpeg) and transcription (faster-whisper).

Audio is decoded with the system ``ffmpeg`` instead of PyAV: some PyAV builds
don't match the faster-whisper version pip resolves (``metadata_errors``
TypeError), and ffmpeg also reads any container — WhatsApp voice notes, mp3,
m4a, even the audio track of a video.
"""

from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16_000
MODELS = ("tiny", "base", "small", "medium", "large-v3-turbo", "large-v3")
DEFAULT_MODEL = "small"


class TranscribeError(RuntimeError):
    """A problem the user can act on (missing ffmpeg, unreadable file…)."""


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


@dataclass
class Result:
    path: Path
    language: str
    duration: float
    segments: list[Segment] = field(default_factory=list)


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise TranscribeError("ffmpeg")


def decode(path: Path) -> np.ndarray:
    """Return mono 16 kHz float32 samples in [-1, 1]."""
    require_ffmpeg()
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-vn",
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0 or not proc.stdout:
        detail = proc.stderr.decode(errors="replace").strip().splitlines()
        raise TranscribeError(detail[-1] if detail else "decode")
    return np.frombuffer(proc.stdout, np.int16).astype(np.float32) / 32768.0


def probe_duration(path: Path) -> float | None:
    """Duration in seconds via ffprobe, or None if it can't be read."""
    if shutil.which("ffprobe") is None:
        return None
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
        return float(out)
    except (ValueError, subprocess.TimeoutExpired, OSError):
        return None


def _cuda_available() -> bool:
    """A GPU is visible *and* the CUDA math library can actually be loaded.

    Checking cuBLAS up front avoids loading the model on the GPU only to fail
    on the first transcription (and a warning on every run) on machines that
    have an NVIDIA card but not the CUDA libraries.
    """
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() == 0:
            return False
    except Exception:
        return False
    if sys.platform.startswith("linux"):
        try:
            ctypes.CDLL("libcublas.so.12")
        except OSError:
            return False
    return True


def _is_cuda_runtime_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("cuda", "cublas", "cudnn", "libcu"))


class Transcriber:
    """Loads the model lazily and falls back from GPU to CPU when needed.

    With ``device="auto"`` the GPU is tried first. A GPU can be *visible* while
    the CUDA libraries (cuBLAS/cuDNN) are missing: the model loads fine and
    only the first transcription fails. That failure is caught once and the
    model is reloaded on the CPU.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        device: str = "auto",
        on_fallback: Callable[[str], None] | None = None,
    ) -> None:
        self.model_name = model
        self.requested_device = device
        self.device = ("cuda" if _cuda_available() else "cpu") if device == "auto" else device
        self.on_fallback = on_fallback
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            compute_type = "float16" if self.device == "cuda" else "int8"
            self._model = WhisperModel(
                self.model_name, device=self.device, compute_type=compute_type
            )
        return self._model

    def _fall_back_to_cpu(self, exc: Exception) -> None:
        self.device = "cpu"
        self._model = None
        if self.on_fallback:
            self.on_fallback(str(exc).splitlines()[0])

    def load(self) -> None:
        try:
            self._load()
        except Exception as exc:
            if self.requested_device == "auto" and self.device == "cuda":
                self._fall_back_to_cpu(exc)
                self._load()
            else:
                raise

    def transcribe(
        self,
        path: Path,
        language: str | None = None,
        on_segment: Callable[[Segment, float], None] | None = None,
    ) -> Result:
        """Transcribe ``path``. ``language=None`` lets Whisper detect it.

        ``on_segment(segment, duration)`` is called as each segment is ready,
        which drives the live progress bar.
        """
        audio = decode(path)
        duration = len(audio) / SAMPLE_RATE
        self.load()
        try:
            return self._run(path, audio, duration, language, on_segment)
        except RuntimeError as exc:
            if (
                self.requested_device == "auto"
                and self.device == "cuda"
                and _is_cuda_runtime_error(exc)
            ):
                self._fall_back_to_cpu(exc)
                self.load()
                return self._run(path, audio, duration, language, on_segment)
            raise

    def _run(self, path, audio, duration, language, on_segment) -> Result:
        segments_iter, info = self._load().transcribe(audio, language=language)
        result = Result(path=path, language=info.language, duration=duration)
        for s in segments_iter:
            seg = Segment(start=s.start, end=s.end, text=s.text.strip())
            result.segments.append(seg)
            if on_segment:
                on_segment(seg, duration)
        return result
