"""CLI tests with a fake model — no download, no ffmpeg decoding."""

import subprocess
from pathlib import Path

import pytest

from ross_transcribe import cli, i18n
from ross_transcribe.engine import Result, Segment, TranscribeError, Transcriber
from ross_transcribe.ui import ago, middle_truncate


class FakeTranscriber:
    model_name = "small"
    device = "cpu"

    def __init__(self, *args, **kwargs):
        self.calls = []

    def load(self):
        pass

    def transcribe(self, path, language=None, on_segment=None):
        self.calls.append((path, language))
        segs = [Segment(0.0, 2.0, "hola [mundo]"), Segment(2.0, 4.0, "chau")]
        for s in segs:
            if on_segment:
                on_segment(s, 4.0)
        return Result(path=path, language=language or "es", duration=4.0, segments=segs)


@pytest.fixture
def audio(tmp_path):
    f = tmp_path / "nota.ogg"
    f.write_bytes(b"fake")
    return f


@pytest.fixture(autouse=True)
def fake(monkeypatch):
    monkeypatch.setattr(cli, "Transcriber", FakeTranscriber)
    monkeypatch.setattr(cli, "require_ffmpeg", lambda: None)
    monkeypatch.delenv("TRANSCRIBE_LANG", raising=False)
    i18n.set_lang("en")


def test_prints_transcript(audio, capsys):
    assert cli.main([str(audio), "--ui-lang", "en"]) == 0
    out = capsys.readouterr().out
    assert "hola [mundo]" in out  # brackets are escaped, not eaten as markup
    assert not (audio.parent / "nota.txt").exists()


def test_output_flag_writes_txt_next_to_audio(audio):
    assert cli.main([str(audio), "-o", "-t"]) == 0
    assert (audio.parent / "nota.txt").read_text() == "[0:00] hola [mundo]\n[0:02] chau\n"


def test_output_dir_and_srt(audio, tmp_path):
    out = tmp_path / "out"
    assert cli.main([str(audio), "-o", str(out), "--srt", "-q"]) == 0
    assert (out / "nota.txt").read_text() == "hola [mundo] chau\n"
    assert (out / "nota.srt").read_text().startswith("1\n00:00:00,000 --> 00:00:02,000\n")


def test_dash_o_followed_by_a_file_is_not_a_folder(audio):
    assert cli.main(["-o", str(audio)]) == 0
    assert (audio.parent / "nota.txt").exists()


def test_srt_alone_saves_next_to_audio(audio):
    assert cli.main([str(audio), "--srt", "-q"]) == 0
    assert (audio.parent / "nota.srt").exists()
    assert not (audio.parent / "nota.txt").exists()


def test_language_flag_and_env(audio, monkeypatch):
    seen = []
    original = FakeTranscriber.transcribe

    def spy(self, path, language=None, on_segment=None):
        seen.append(language)
        return original(self, path, language, on_segment)

    monkeypatch.setattr(FakeTranscriber, "transcribe", spy)
    cli.main([str(audio), "-q"])
    cli.main([str(audio), "-q", "-l", "en"])
    monkeypatch.setenv("TRANSCRIBE_LANG", "es")
    cli.main([str(audio), "-q"])
    assert seen == [None, "en", "es"]


def test_missing_and_non_media_files_fail(tmp_path, capsys):
    doc = tmp_path / "doc.pdf"
    doc.write_bytes(b"x")
    assert cli.main([str(tmp_path / "nope.ogg"), str(doc)]) == 1
    out = capsys.readouterr().out
    assert "File not found" in out and "Not an audio/video file" in out


def test_no_files_without_terminal_explains(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert cli.main([]) == 2
    assert "No files given" in capsys.readouterr().out


def test_spanish_interface(audio, capsys):
    assert cli.main([str(audio), "-o", "--ui-lang", "es"]) == 0
    assert "guardado" in capsys.readouterr().out


def test_ago_and_truncate():
    i18n.set_lang("en")
    now = 1_000_000.0
    assert ago(now - 30, now) == "just now"
    assert ago(now - 7200, now) == "2 h ago"
    assert ago(now - 86400 * 1.5, now) == "yesterday"
    assert ago(now - 86400 * 4, now) == "4 days ago"
    long = "~/Downloads/Others/instagram_export/media/other/18100207114801789.mp4"
    short = middle_truncate(long, 40)
    assert len(short) == 40 and short.endswith("18100207114801789.mp4") and "…" in short


def test_gpu_failure_falls_back_to_cpu(monkeypatch, tmp_path):
    """A visible GPU without CUDA libraries must not break transcription."""
    import numpy as np

    from ross_transcribe import engine

    monkeypatch.setattr(engine, "_cuda_available", lambda: True)
    monkeypatch.setattr(engine, "decode", lambda path: np.zeros(16000, np.float32))
    loads = []

    class Info:
        language = "es"

    class FakeModel:
        def __init__(self, name, device, compute_type):
            loads.append(device)
            self.device = device

        def transcribe(self, audio, language=None):
            if self.device == "cuda":
                raise RuntimeError("Library libcublas.so.12 is not found or cannot be loaded")
            return iter([type("S", (), {"start": 0.0, "end": 1.0, "text": " ok"})()]), Info()

    import faster_whisper

    monkeypatch.setattr(faster_whisper, "WhisperModel", FakeModel)
    reasons = []
    tr = Transcriber(device="auto", on_fallback=reasons.append)
    result = tr.transcribe(tmp_path / "a.ogg", language="es")
    assert loads == ["cuda", "cpu"] and tr.device == "cpu"
    assert [s.text for s in result.segments] == ["ok"]
    assert "libcublas" in reasons[0]


def test_decode_reports_ffmpeg_errors(tmp_path):
    from ross_transcribe.engine import decode

    bad = tmp_path / "broken.ogg"
    bad.write_bytes(b"not audio")
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("ffmpeg not installed")
    with pytest.raises(TranscribeError):
        decode(Path(bad))
