import os
import time

from ross_transcribe import finder


def _touch(path, age):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    t = time.time() - age
    os.utime(path, (t, t))
    return path


def test_is_media_is_case_insensitive(tmp_path):
    assert finder.is_media(tmp_path / "a.OGG")
    assert finder.is_media(tmp_path / "clip.mp4")
    assert not finder.is_media(tmp_path / "notes.txt")


def test_recent_media_newest_first_and_not_recursive(tmp_path):
    old = _touch(tmp_path / "old.mp3", 500)
    new = _touch(tmp_path / "new.ogg", 10)
    _touch(tmp_path / "doc.pdf", 1)
    _touch(tmp_path / "sub" / "deep.wav", 1)
    assert finder.recent_media(tmp_path) == [new, old]


def test_search_skips_hidden_and_excluded_dirs(tmp_path, monkeypatch):
    keep = _touch(tmp_path / "music" / "song.flac", 100)
    newer = _touch(tmp_path / "videos" / "clip.mkv", 5)
    _touch(tmp_path / ".cache" / "beep.ogg", 1)
    _touch(tmp_path / "proj" / "node_modules" / "x.mp3", 1)
    for use_fd in (True, False):
        if not use_fd:
            monkeypatch.setattr(finder.shutil, "which", lambda _name: None)
        assert finder.search_media([tmp_path]) == [newer, keep]


def test_search_roots_adds_mounts_outside_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    mounts = tmp_path / "mounts"
    mounts.write_text(
        "/dev/nvme1n1p2 / ext4 rw 0 0\n"
        "/dev/sda1 /run/media/user/USB\\040Stick vfat rw 0 0\n"
        "/dev/nvme0n1p1 /mnt/data ext4 rw 0 0\n"
        "proc /proc proc rw 0 0\n"
    )
    roots = finder.search_roots(mounts)
    assert [str(r) for r in roots] == [
        str(tmp_path / "home"),
        "/run/media/user/USB Stick",
        "/mnt/data",
    ]
