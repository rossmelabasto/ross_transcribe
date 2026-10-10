"""Command line entry point: ``transcribe [files…] [options]``.

With files it runs straight away; without files (in a terminal) it opens the
interactive picker.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeRemainingColumn

from ross_transcribe import __version__, i18n
from ross_transcribe.engine import (
    DEFAULT_MODEL,
    MODELS,
    Segment,
    TranscribeError,
    Transcriber,
    require_ffmpeg,
)
from ross_transcribe.finder import is_media
from ross_transcribe.formats import clock, output_path, to_srt, to_text
from ross_transcribe.i18n import t
from ross_transcribe.ui import GREEN, MAUVE, Job, make_console, short_path


def _ui_lang_from_argv(argv: list[str]) -> str | None:
    for i, arg in enumerate(argv):
        if arg.startswith("--ui-lang="):
            return arg.split("=", 1)[1]
        if arg == "--ui-lang" and i + 1 < len(argv):
            return argv[i + 1]
    return None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="transcribe", description=t("description"))
    p.add_argument("files", nargs="*", type=Path, help=t("help_files"))
    p.add_argument(
        "-o", "--output", nargs="?", const="", default=None, metavar="DIR", help=t("help_output")
    )
    p.add_argument("-t", "--timestamps", action="store_true", help=t("help_timestamps"))
    p.add_argument("--srt", action="store_true", help=t("help_srt"))
    p.add_argument(
        "-l", "--lang", default=os.environ.get("TRANSCRIBE_LANG", "auto"), help=t("help_lang")
    )
    p.add_argument("-m", "--model", default=DEFAULT_MODEL, choices=MODELS, help=t("help_model"))
    p.add_argument(
        "--device", default="auto", choices=("auto", "cpu", "cuda"), help=t("help_device")
    )
    p.add_argument("-q", "--quiet", action="store_true", help=t("help_quiet"))
    p.add_argument("--ui-lang", choices=("en", "es"), help=t("help_ui_lang"))
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return p


def job_from_args(args: argparse.Namespace) -> Job:
    files = list(args.files)
    out_dir: Path | None = None
    if args.output:
        candidate = Path(args.output).expanduser()
        # `transcribe -o audio.ogg`: the "DIR" is really the first file.
        if candidate.is_file() or (not candidate.exists() and is_media(candidate)):
            files.insert(0, candidate)
        else:
            out_dir = candidate
    lang = args.lang.lower()
    return Job(
        files=files,
        language=None if lang == "auto" else lang,
        timestamps=args.timestamps,
        screen=not args.quiet,
        txt=args.output is not None,
        srt=args.srt,
        out_dir=out_dir,
    )


def validate(job: Job, console: Console) -> list[Path]:
    ok = []
    for f in job.files:
        f = f.expanduser()
        if not f.is_file():
            console.print(f"[err]✗[/] {t('err_missing', path=f)}")
        elif not is_media(f):
            console.print(f"[err]✗[/] {t('err_not_media', path=f)}")
        else:
            ok.append(f)
    return ok


def header(console: Console, model: str) -> None:
    console.print(
        f"[badge] transcribe [/] [dim]─[/] faster-whisper [accent]{model}[/] "
        f"[dim]· {t('subtitle')}[/]"
    )
    console.print()


def run(job: Job, console: Console, transcriber: Transcriber) -> int:
    files = validate(job, console)
    if not files:
        return 1
    if job.out_dir is not None:
        job.out_dir.mkdir(parents=True, exist_ok=True)

    device_label = "GPU" if transcriber.device == "cuda" else "CPU"
    with console.status(
        f"[info]{t('loading_model', model=transcriber.model_name, device=device_label)}[/]",
        spinner="dots",
    ):
        transcriber.load()

    done = 0
    for path in files:
        progress = Progress(
            TextColumn("[accent]▸[/] {task.description}"),
            BarColumn(complete_style=MAUVE, finished_style=GREEN),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        )
        started = time.monotonic()
        try:
            with progress:
                task = progress.add_task(path.name, total=None)

                def on_segment(seg: Segment, duration: float, task=task, progress=progress) -> None:
                    progress.update(task, total=duration or None, completed=min(seg.end, duration))
                    if job.screen and seg.text:
                        stamp = f"[dim][{clock(seg.start)}][/] " if job.timestamps else ""
                        progress.console.print(f"{stamp}{escape(seg.text)}")

                console.print(f"[accent]==[/] [bold]{path.name}[/]")
                result = transcriber.transcribe(path, language=job.language, on_segment=on_segment)
        except TranscribeError as exc:
            if str(exc) == "ffmpeg":
                console.print(f"[err]✗[/] {t('err_ffmpeg')}")
                return 1
            console.print(f"[err]✗[/] {t('err_decode', path=path.name, detail=exc)}")
            continue

        elapsed = time.monotonic() - started
        info = [t("took", audio=clock(result.duration), secs=elapsed)]
        if job.language is None:
            info.append(t("detected", lang=result.language))
        console.print(f"[dim]{' · '.join(info)}[/]")
        if job.txt:
            dest = output_path(path, ".txt", job.out_dir)
            dest.write_text(to_text(result.segments, job.timestamps), encoding="utf-8")
            console.print(f"[ok]✓[/] {t('saved')} [info]{escape(short_path(dest))}[/]")
        if job.srt:
            dest = output_path(path, ".srt", job.out_dir)
            dest.write_text(to_srt(result.segments), encoding="utf-8")
            console.print(f"[ok]✓[/] {t('saved')} [info]{escape(short_path(dest))}[/]")
        console.print()
        done += 1

    if len(files) > 1:
        console.print(f"[ok]{t('summary', ok=done, total=len(files))}[/]")
    return 0 if done == len(files) else 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    i18n.set_lang(_ui_lang_from_argv(argv) or i18n.detect())
    args = build_parser().parse_args(argv)
    console = make_console()

    try:
        require_ffmpeg()
    except TranscribeError:
        console.print(f"[err]✗[/] {t('err_ffmpeg')}")
        return 1

    def on_fallback(reason: str) -> None:
        console.print(f"[warn]! {t('gpu_fallback', reason=reason)}[/]")

    transcriber = Transcriber(model=args.model, device=args.device, on_fallback=on_fallback)

    try:
        if args.files or args.output:
            job = job_from_args(args)
            if not job.files:
                console.print(f"[err]✗[/] {t('err_no_tty')}")
                return 2
        else:
            if not (sys.stdin.isatty() and sys.stdout.isatty()):
                console.print(f"[err]✗[/] {t('err_no_tty')}")
                return 2
            header(console, args.model)
            from ross_transcribe.ui import ask

            job = ask(console, args.lang.lower())
            if job is None:
                console.print(f"[dim]{t('cancelled')}[/]")
                return 130
            console.print()
        return run(job, console, transcriber)
    except KeyboardInterrupt:
        console.print(f"\n[dim]{t('cancelled')}[/]")
        return 130
