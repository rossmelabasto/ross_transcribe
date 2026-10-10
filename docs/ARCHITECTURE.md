# How it works

```
transcribe [files] [flags]                      transcribe   (no files, in a terminal)
        │                                              │
        ▼                                              ▼
  cli.job_from_args ──────────► Job ◄────────── ui.ask  (questionary menus)
                                 │                 ├─ finder.recent_media  (Downloads)
                                 │                 ├─ finder.search_media  (fd / os.walk over home + mounts)
                                 │                 └─ engine.probe_duration (ffprobe, 8 threads)
                                 ▼
                             cli.run
                                 │  for each file:
                                 ├─ engine.decode ─► ffmpeg ─► mono 16 kHz float32
                                 ├─ engine.Transcriber.transcribe ─► faster-whisper (segments, streamed)
                                 │      └─ on_segment ─► Rich progress bar + live text
                                 └─ formats.to_text / to_srt ─► .txt / .srt
```

## Modules

| File | Responsibility |
|---|---|
| `cli.py` | Flags, building a `Job`, running it with progress output. Entry point `transcribe`. |
| `ui.py` | Interactive questionnaire, Catppuccin theme, relative ages, path truncation. |
| `engine.py` | Decoding with ffmpeg, model loading, GPU→CPU fallback, streaming segments. |
| `formats.py` | Plain text, `[m:ss]` timestamps, SRT, output paths. Pure functions. |
| `finder.py` | Media extensions, Downloads folder (XDG-aware), recent files, whole-machine search. |
| `i18n.py` | English/Spanish strings and locale detection. |

## Decisions

**ffmpeg instead of PyAV.** faster-whisper decodes with PyAV by default. Some PyAV builds that pip resolves don't match the faster-whisper version (`TypeError: open() got an unexpected keyword argument 'metadata_errors'`). Decoding with the system ffmpeg into raw PCM avoids that whole class of errors and reads any container — including the audio track of videos. The cost is one runtime dependency that is a package-manager install away.

**GPU only when it can really work.** A machine can have an NVIDIA GPU that CTranslate2 *sees* while the CUDA libraries are missing: the model loads, and only the first transcription fails with `libcublas.so.12 is not found`. `--device auto` therefore checks that cuBLAS can be loaded before choosing the GPU, and still catches CUDA runtime errors once, reloading the model on the CPU. Users without CUDA never see a warning; users whose GPU breaks mid-way get one line explaining the fallback.

**`small` by default.** On a modern laptop CPU it runs ~8–10× faster than real time with `int8`, uses about 1 GB of RAM and no VRAM. Bigger models were evaluated for Spanish voice notes: they fix some words but not the hardest ones (nicknames said fast), so the extra gigabytes aren't worth it as a default. `-m` exposes them for people with a GPU.

**Plain-string menu entries.** questionary's type-to-filter only works on `str` titles, so file entries are padded strings (`name  duration  age`) instead of styled fragments. Long paths are truncated in the middle, keeping the file name.

**Our own answer echo.** questionary summarizes multi-select answers as `done (2 selections)` (English only, and it would repeat the duration/age columns). Checkbox prompts use `erase_when_done=True` and the answer is echoed by the app in the interface language.

**Language defaults.** `-l` defaults to `auto` (or `$TRANSCRIBE_LANG`), which is the safest choice for strangers' audio. In the interactive menu the highlighted option is the interface language, because that's what most people record in.

**Whole-machine search.** "Whole machine" means `$HOME` plus mounts under `/mnt`, `/media` and `/run/media`: that's where people keep recordings. System folders only add app sounds and theme files. Hidden folders, caches and `node_modules` are skipped. `fd` is used when installed (`fdfind` on Debian); otherwise `os.walk`.

## Tests

`pytest` runs without downloading a model: the CLI tests replace `Transcriber` with a fake, and the GPU fallback test fakes `WhisperModel`. `finder` tests run both with and without `fd`. One test calls the real ffmpeg (skipped if it isn't installed) to check that decoding errors become `TranscribeError`.
