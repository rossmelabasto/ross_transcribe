"""Finding audio and video files: the Downloads folder and the whole machine."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

AUDIO_EXTS = {"ogg", "opus", "oga", "mp3", "m4a", "aac", "wav", "flac", "wma", "amr", "webm"}
VIDEO_EXTS = {"mp4", "mkv", "mov", "avi", "m4v"}
MEDIA_EXTS = AUDIO_EXTS | VIDEO_EXTS

# Folders that are never worth searching: caches, dependencies, system noise.
EXCLUDED_DIRS = {
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    "site-packages",
    "Trash",
    "snap",
    "proc",
    "sys",
}
MOUNT_PREFIXES = ("/mnt/", "/media/", "/run/media/")


def is_media(path: Path) -> bool:
    return path.suffix.lower().lstrip(".") in MEDIA_EXTS


def downloads_dir() -> Path:
    """The user's Downloads folder (XDG-aware: ~/Descargas, ~/Downloads…)."""
    if shutil.which("xdg-user-dir"):
        try:
            out = subprocess.run(
                ["xdg-user-dir", "DOWNLOAD"], capture_output=True, text=True, timeout=5
            ).stdout.strip()
            if out and Path(out).is_dir() and Path(out) != Path.home():
                return Path(out)
        except (OSError, subprocess.TimeoutExpired):
            pass
    for name in ("Downloads", "Descargas"):
        candidate = Path.home() / name
        if candidate.is_dir():
            return candidate
    return Path.home()


def _by_mtime(paths: list[Path]) -> list[Path]:
    def mtime(p: Path) -> float:
        try:
            return p.stat().st_mtime
        except OSError:
            return 0.0

    return sorted(paths, key=mtime, reverse=True)


def recent_media(directory: Path, limit: int = 40) -> list[Path]:
    """Media files directly inside ``directory``, newest first."""
    try:
        files = [p for p in directory.iterdir() if p.is_file() and is_media(p)]
    except OSError:
        return []
    return _by_mtime(files)[:limit]


def search_roots(mounts_file: Path = Path("/proc/mounts")) -> list[Path]:
    """Home plus mounted drives (USB sticks, extra disks) outside it."""
    home = Path.home()
    roots = [home]
    try:
        lines = mounts_file.read_text().splitlines()
    except OSError:
        lines = []
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        mount = Path(parts[1].replace("\\040", " "))
        if str(mount).startswith(MOUNT_PREFIXES) and home not in mount.parents and mount != home:
            roots.append(mount)
    return roots


def _walk(roots: list[Path], limit: int) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in EXCLUDED_DIRS]
            for name in filenames:
                if not name.startswith(".") and is_media(Path(name)):
                    found.append(Path(dirpath) / name)
                    if len(found) >= limit * 5:
                        return found
    return found


def search_media(roots: list[Path] | None = None, limit: int = 1500) -> list[Path]:
    """Every media file under ``roots`` (hidden folders skipped), newest first.

    Uses ``fd`` when installed (much faster); otherwise walks the tree.
    """
    roots = roots or search_roots()
    if shutil.which("fd") or shutil.which("fdfind"):
        exe = shutil.which("fd") or shutil.which("fdfind")
        cmd = [exe, "--type", "f", "--absolute-path", "--no-ignore-vcs"]
        for d in sorted(EXCLUDED_DIRS):
            cmd += ["--exclude", d]
        for ext in sorted(MEDIA_EXTS):
            cmd += ["-e", ext]
        cmd += ["."] + [str(r) for r in roots]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
            found = [Path(line) for line in out.splitlines() if line]
        except (OSError, subprocess.TimeoutExpired):
            found = _walk(roots, limit)
    else:
        found = _walk(roots, limit)
    return _by_mtime(found)[:limit]
