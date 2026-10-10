from pathlib import Path

from ross_transcribe.engine import Segment
from ross_transcribe.formats import clock, output_path, srt_time, to_srt, to_text

SEGS = [
    Segment(0.0, 6.28, "Hola, buenas noches."),
    Segment(6.28, 12.84, "Esto es una prueba."),
    Segment(12.84, 13.0, ""),
]


def test_clock():
    assert clock(0) == "0:00"
    assert clock(65.9) == "1:05"
    assert clock(3725) == "1:02:05"


def test_srt_time():
    assert srt_time(0) == "00:00:00,000"
    assert srt_time(5.12) == "00:00:05,120"
    assert srt_time(3725.5) == "01:02:05,500"
    assert srt_time(-1) == "00:00:00,000"


def test_plain_text_joins_segments_and_skips_empty():
    assert to_text(SEGS) == "Hola, buenas noches. Esto es una prueba.\n"


def test_text_with_timestamps():
    assert to_text(SEGS, timestamps=True) == (
        "[0:00] Hola, buenas noches.\n[0:06] Esto es una prueba.\n"
    )


def test_srt_blocks_are_numbered():
    assert to_srt(SEGS) == (
        "1\n00:00:00,000 --> 00:00:06,280\nHola, buenas noches.\n\n"
        "2\n00:00:06,280 --> 00:00:12,840\nEsto es una prueba.\n"
    )


def test_output_path_next_to_media_or_in_folder(tmp_path):
    media = Path("/music/nota de voz.ogg")
    assert output_path(media, ".txt") == Path("/music/nota de voz.txt")
    assert output_path(media, ".srt", tmp_path) == tmp_path / "nota de voz.srt"
