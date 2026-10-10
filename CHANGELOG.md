# Changelog

## 0.1.0 — 2026-10-10 — First public release

- Interactive mode: pick files from Downloads (newest first, with duration and age), search the whole machine (home + mounted drives) or type a path; type-to-filter and multi-select.
- Options for language (Spanish, English, auto-detect), timestamps, output (screen, `.txt`, `.srt`) and destination folder.
- Direct mode with the same options as flags: `-o [DIR]`, `-t`, `--srt`, `-l`, `-m`, `--device`, `-q`, `--ui-lang`.
- Live transcript with a progress bar; summary of time taken and detected language.
- Decoding through the system ffmpeg (any audio format, and the audio of videos).
- `--device auto`: uses an NVIDIA GPU only when the CUDA libraries load; falls back to the CPU otherwise.
- English and Spanish interface following the system locale; Catppuccin Mocha colors.
- Tests with a fake model, GitHub Actions CI, README in English and Spanish.
