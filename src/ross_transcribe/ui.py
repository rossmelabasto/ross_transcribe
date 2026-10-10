"""Interactive mode: pick files and options, then watch the transcript appear."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import questionary
from questionary import Choice, Style
from rich.console import Console
from rich.theme import Theme

from ross_transcribe import finder
from ross_transcribe.engine import probe_duration
from ross_transcribe.formats import clock
from ross_transcribe.i18n import get_lang, t

# Catppuccin Mocha
MAUVE, GREEN, BLUE, PEACH, RED = "#cba6f7", "#a6e3a1", "#89b4fa", "#fab387", "#f38ba8"
TEXT, SUBTEXT, OVERLAY, BASE = "#cdd6f4", "#a6adc8", "#6c7086", "#1e1e2e"

THEME = Theme(
    {
        "accent": MAUVE,
        "ok": GREEN,
        "info": BLUE,
        "warn": PEACH,
        "err": RED,
        "dim": OVERLAY,
        "badge": f"bold {BASE} on {MAUVE}",
    }
)

QSTYLE = Style(
    [
        ("qmark", f"fg:{MAUVE} bold"),
        ("question", f"fg:{TEXT} bold"),
        ("answer", f"fg:{GREEN} bold"),
        ("pointer", f"fg:{MAUVE} bold"),
        ("highlighted", f"fg:{MAUVE} bold noreverse"),
        ("selected", f"fg:{GREEN} noreverse"),
        ("separator", f"fg:{OVERLAY}"),
        ("instruction", f"fg:{OVERLAY} italic"),
        ("text", f"fg:{TEXT}"),
        ("disabled", f"fg:{OVERLAY} italic"),
        ("meta", f"fg:{OVERLAY}"),
        ("search_success", f"fg:{GREEN}"),
        ("search_none", f"fg:{RED}"),
    ]
)

SEARCH_ALL = "__search_all__"
BROWSE = "__browse__"


def make_console() -> Console:
    return Console(theme=THEME, highlight=False, soft_wrap=True)


@dataclass
class Job:
    files: list[Path]
    language: str | None  # None = auto-detect
    timestamps: bool = False
    screen: bool = True
    txt: bool = False
    srt: bool = False
    out_dir: Path | None = None


def ago(mtime: float, now: float | None = None) -> str:
    """Relative age of a file, in the interface language."""
    delta = (now or time.time()) - mtime
    if delta < 60:
        return t("ago_now")
    if delta < 3600:
        return t("ago_min", n=int(delta // 60))
    if delta < 86400:
        return t("ago_h", n=int(delta // 3600))
    days = int(delta // 86400)
    return t("ago_yesterday") if days == 1 else t("ago_days", n=days)


def short_path(path: Path) -> str:
    home = str(Path.home())
    s = str(path)
    return "~" + s[len(home) :] if s.startswith(home + os.sep) else s


def middle_truncate(text: str, width: int) -> str:
    """``~/Downloads/a/b/c/audio.ogg`` → ``~/Downloads/…/audio.ogg`` (keeps the name)."""
    if len(text) <= width:
        return text
    name = text.rsplit("/", 1)[-1]
    keep_end = len(name) + 1 if len(name) + 1 <= width - 8 else max(width // 2, width - 20)
    keep_start = width - keep_end - 1
    return text[:keep_start] + "…" + text[-keep_end:]


def _file_choice(path: Path, duration: float | None, name_width: int, full: bool) -> Choice:
    label = middle_truncate(short_path(path) if full else path.name, name_width)
    try:
        when = ago(path.stat().st_mtime)
    except OSError:
        when = ""
    length = clock(duration) if duration else ""
    # Plain string on purpose: questionary's search filter only works on str titles.
    title = f"{label.ljust(name_width)}  {length:>7}  {when}"
    return Choice(title=title, value=path)


def _with_durations(paths: list[Path]) -> list[tuple[Path, float | None]]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(zip(paths, pool.map(probe_duration, paths), strict=True))


def _answered(console: Console, message: str, answer: str) -> None:
    """Echo a checkbox answer ourselves: questionary's own summary is English-only
    ("done (2 selections)") and would repeat the duration/age columns."""
    console.print(f"[accent]?[/] [bold]{message}[/] [ok]{answer}[/]")


def _summary(paths: list) -> str:
    names = [p.name for p in paths if isinstance(p, Path)]
    extra = [p for p in paths if not isinstance(p, Path)]
    text = ", ".join(names[:2]) + (f" +{len(names) - 2}" if len(names) > 2 else "")
    if extra:
        text = (text + " " if text else "") + "…"
    return text


def _checkbox(message: str, choices: list, console: Console):
    picked = questionary.checkbox(
        message,
        choices=choices,
        instruction=f"({t('q_files_hint')})",
        use_search_filter=True,
        use_jk_keys=False,
        style=QSTYLE,
        qmark="?",
        erase_when_done=True,
    ).ask()
    if picked is not None:
        _answered(console, message, _summary(picked))
    return picked


def _pick_from(
    paths: list[Path], console: Console, full: bool, durations: bool
) -> list[Path] | None:
    if not paths:
        console.print(f"[warn]{t('none_found')}[/]")
        return []
    pairs = _with_durations(paths) if durations else [(p, None) for p in paths]
    width = min(max(len(short_path(p) if full else p.name) for p in paths), 60)
    choices = [_file_choice(p, d, width, full) for p, d in pairs]
    return _checkbox(t("q_files"), choices, console)


def _search_all(console: Console) -> list[Path] | None:
    with console.status(f"[info]{t('searching')}[/]", spinner="dots"):
        found = finder.search_media()
    console.print(f"[dim]{t('found_n', n=len(found))}[/]")
    return _pick_from(found, console, full=True, durations=False)


def _browse(console: Console) -> list[Path] | None:
    raw = questionary.path(t("q_path"), style=QSTYLE, qmark="?").ask()
    if raw is None:
        return None
    target = Path(raw).expanduser()
    if target.is_dir():
        return _pick_from(
            finder.recent_media(target, limit=500), console, full=False, durations=True
        )
    return [target] if target.exists() else []


def choose_files(console: Console, start_dir: Path | None = None) -> list[Path] | None:
    start_dir = start_dir or finder.downloads_dir()
    recent = finder.recent_media(start_dir)
    pairs = _with_durations(recent)
    width = min(max((len(p.name) for p in recent), default=20), 60)
    choices: list = [_file_choice(p, d, width, full=False) for p, d in pairs]
    choices += [
        Choice(title=t("opt_search_all"), value=SEARCH_ALL),
        Choice(title=t("opt_browse"), value=BROWSE),
    ]
    picked = _checkbox(t("q_files"), choices, console)
    if picked is None:
        return None
    files = [p for p in picked if isinstance(p, Path)]
    for action, handler in ((SEARCH_ALL, _search_all), (BROWSE, _browse)):
        if action in picked:
            more = handler(console)
            if more is None:
                return None
            files += [p for p in more if p not in files]
    return files


def _select(message: str, options: list[tuple[str, object]], default: object):
    choices = [Choice(title=label, value=value) for label, value in options]
    default_choice = next((c for c in choices if c.value == default), choices[0])
    return questionary.select(
        message,
        choices=choices,
        default=default_choice,
        style=QSTYLE,
        qmark="?",
        use_shortcuts=False,
        instruction=" ",
    ).ask()


def ask(console: Console, default_language: str) -> Job | None:
    """Run the whole questionnaire. Returns None if the user cancels."""
    files = choose_files(console)
    if files is None:
        return None
    if not files:
        console.print(f"[warn]{t('nothing_selected')}[/]")
        return None

    if default_language == "auto":
        default_language = get_lang()
    language = _select(
        t("q_lang"),
        [(t("lang_es"), "es"), (t("lang_en"), "en"), (t("lang_auto"), "auto")],
        default_language if default_language in ("es", "en") else "auto",
    )
    if language is None:
        return None

    timestamps = _select(t("q_timestamps"), [(t("yes"), True), (t("no"), False)], True)
    if timestamps is None:
        return None

    outputs = questionary.checkbox(
        t("q_output"),
        choices=[
            Choice(t("out_screen"), "screen", checked=True),
            Choice(t("out_txt"), "txt", checked=True),
            Choice(t("out_srt"), "srt"),
        ],
        style=QSTYLE,
        qmark="?",
        instruction=" ",
        erase_when_done=True,
    ).ask()
    if outputs is None:
        return None
    labels = {"screen": t("out_screen"), "txt": t("out_txt"), "srt": t("out_srt")}
    _answered(console, t("q_output"), ", ".join(labels[o] for o in outputs) or "—")

    out_dir = None
    if "txt" in outputs or "srt" in outputs:
        where = _select(
            t("q_where"), [(t("where_next"), "next"), (t("where_pick"), "pick")], "next"
        )
        if where is None:
            return None
        if where == "pick":
            raw = questionary.path(
                t("q_folder"), only_directories=True, style=QSTYLE, qmark="?"
            ).ask()
            if raw is None:
                return None
            out_dir = Path(raw).expanduser()

    return Job(
        files=files,
        language=None if language == "auto" else language,
        timestamps=timestamps,
        screen="screen" in outputs,
        txt="txt" in outputs,
        srt="srt" in outputs,
        out_dir=out_dir,
    )
