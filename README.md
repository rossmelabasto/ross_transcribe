<div align="center">

# transcribe

**Local, offline transcription from your terminal.**<br/>
Pick voice notes, recordings or videos from an interactive menu (or pass them as arguments) and get the text — with timestamps and `.srt` subtitles if you want them. Nothing leaves your computer.

[![CI](https://github.com/rossmelabasto/ross_transcribe/actions/workflows/ci.yml/badge.svg)](https://github.com/rossmelabasto/ross_transcribe/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-a3e635.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-%E2%89%A53.10-6b4dff.svg)
![Offline](https://img.shields.io/badge/runs-offline-6b4dff.svg)

[Install](#install) · [Usage](#usage) · [Models & hardware](#models--hardware) · [How it works](docs/ARCHITECTURE.md) · [Changelog](CHANGELOG.md) · [Español](README.es.md)

<img src="docs/demo.gif" alt="transcribe: picking two audio files, auto-detecting Spanish and English, and saving .txt and .srt files" width="900" />

</div>

## Features

- **Interactive picker.** Run `transcribe` with no arguments: your Downloads folder is listed newest first with each file's duration and age. Type to filter, space to select several, enter to go.
- **Search the whole machine.** One option searches your home folder and mounted drives (USB sticks, extra disks) for any audio or video, skipping hidden folders, caches and `node_modules`. Uses [`fd`](https://github.com/sharkdp/fd) when available.
- **Any format ffmpeg reads.** WhatsApp/Telegram voice notes (`.ogg`/`.opus`), `.mp3`, `.m4a`, `.wav`, `.flac`… and the audio track of videos (`.mp4`, `.mkv`, `.mov`).
- **Timestamps and subtitles.** `[0:05]` markers per line, and `.srt` files ready for any video player or editor.
- **Spanish, English or automatic.** Force the spoken language or let Whisper detect it per file — handy for mixed folders.
- **Live progress.** The transcript appears line by line while a progress bar shows how much is left.
- **Bilingual interface.** Menus and messages in English or Spanish, following your system locale.
- **Scriptable.** Every option is also a flag, so it works in scripts, cron jobs and file-manager actions.
- **Private and free.** Runs [faster-whisper](https://github.com/SYSTRAN/faster-whisper) on your CPU (or NVIDIA GPU). No accounts, no API keys, no uploads.

## Install

You need **Python 3.10+** and **ffmpeg**.

```bash
# 1. ffmpeg (pick your system)
sudo pacman -S ffmpeg        # Arch
sudo apt install ffmpeg      # Debian/Ubuntu
brew install ffmpeg          # macOS

# 2. transcribe (pick one)
pipx install git+https://github.com/rossmelabasto/ross_transcribe
uv tool install git+https://github.com/rossmelabasto/ross_transcribe
```

Optional: install [`fd`](https://github.com/sharkdp/fd) for much faster whole-machine search.

The first run downloads the Whisper model (~460 MB for the default `small`) from Hugging Face; after that everything works offline.

## Usage

### Interactive

```bash
transcribe
```

1. **Audio files** — pick from Downloads, or choose *Search the whole machine…* / *Type a path…* (a file or a folder).
2. **Language** — Spanish, English or detect automatically.
3. **Timestamps** — yes / no.
4. **Output** — screen, `.txt`, `.srt` (any combination).
5. **Save to** — next to each audio, or a folder you choose.

> Tip: in path prompts the first <kbd>Enter</kbd> accepts the highlighted autocompletion; press it again to confirm.

### Direct

```bash
transcribe voice-note.ogg                    # print the transcript
transcribe *.ogg -o                          # also save a .txt next to each file
transcribe interview.m4a -t -o ~/notes       # timestamps, .txt into ~/notes
transcribe lecture.mp4 --srt -l en           # English subtitles next to the video
transcribe call.wav -l auto -q --srt -o out  # detect language, save only, no printing
```

| Flag | What it does |
|---|---|
| `-o`, `--output [DIR]` | Save a `.txt` next to each file, or inside `DIR` |
| `-t`, `--timestamps` | Prefix each line with its time, like `[0:05]` |
| `--srt` | Also write `.srt` subtitles (same folder logic as `-o`) |
| `-l`, `--lang LANG` | Spoken language: `es`, `en`, any Whisper code, or `auto` (default) |
| `-m`, `--model NAME` | `tiny`, `base`, `small` (default), `medium`, `large-v3-turbo`, `large-v3` |
| `--device` | `auto` (default), `cpu` or `cuda` |
| `-q`, `--quiet` | Don't print the transcript (only save files) |
| `--ui-lang` | Interface language: `en` or `es` (default: system locale) |

Existing `.txt`/`.srt` files with the same name are overwritten.

### Configuration

| Variable | Effect |
|---|---|
| `TRANSCRIBE_LANG` | Default spoken language (e.g. `es`), instead of `auto` |
| `TRANSCRIBE_UI_LANG` | Force the interface language (`en`/`es`) |
| `HF_HOME` | Where models are cached (default `~/.cache/huggingface`) |

A Spanish shortcut, for example:

```bash
# ~/.local/bin/transcribir
#!/bin/sh
TRANSCRIBE_UI_LANG=es TRANSCRIBE_LANG=es exec transcribe "$@"
```

## Models & hardware

| Model | Download | Notes |
|---|---|---|
| `tiny` / `base` | 75 / 145 MB | Fastest, noticeably less accurate |
| **`small`** | 460 MB | **Default.** Good accuracy for voice notes; fast on a modern CPU |
| `medium` | 1.5 GB | More accurate, ~3× slower on CPU |
| `large-v3-turbo` | 1.6 GB | Near `large-v3` quality; best with a GPU |
| `large-v3` | 3.1 GB | Most accurate; slow without a GPU |

On a laptop CPU (Intel Core Ultra 7 255HX) the default `small` model transcribes about **8–10× faster than real time**: a 30-second voice note takes ~3 s, a 1-minute one ~6 s.

**GPU:** with `--device auto`, an NVIDIA GPU is used when CTranslate2 sees it **and** the CUDA 12 libraries (cuBLAS, cuDNN 9) can be loaded — see [faster-whisper's GPU notes](https://github.com/SYSTRAN/faster-whisper#gpu). Otherwise it quietly runs on the CPU. If the GPU fails mid-way, it falls back to the CPU and tells you why.

**Accuracy tip:** even large models can miss nicknames or words said very fast. If a word matters, double-check it against the audio — the timestamps make that quick.

## Privacy

Audio is decoded and transcribed on your machine. The only network access is the one-time model download from Hugging Face. Transcripts are written only where you choose.

## Development

```bash
git clone https://github.com/rossmelabasto/ross_transcribe && cd ross_transcribe
uv venv && uv pip install -e ".[dev]"     # or: python -m venv .venv && pip install -e ".[dev]"
.venv/bin/pytest -q                        # tests use a fake model: no download needed
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Credits

- Speech recognition: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) and OpenAI's [Whisper](https://github.com/openai/whisper) models.
- Interface: [questionary](https://github.com/tmbo/questionary) and [Rich](https://github.com/Textualize/rich), in [Catppuccin Mocha](https://catppuccin.com) colors.
- Demo audio is in the public domain — see [docs/demo/CREDITS.md](docs/demo/CREDITS.md).

## License

[MIT](LICENSE) © Rossmel Abasto — [portfolio.rossmel.top](https://portfolio.rossmel.top)
