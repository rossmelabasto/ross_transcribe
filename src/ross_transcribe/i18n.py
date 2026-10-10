"""Interface strings in English and Spanish, picked from the system locale."""

from __future__ import annotations

import os
from collections.abc import Mapping

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "description": "Transcribe audio and video locally (offline) with faster-whisper. "
        "Run it without files to open the interactive picker.",
        "help_files": "audio or video files to transcribe",
        "help_output": "save a .txt next to each file, or inside DIR",
        "help_timestamps": "prefix each line with its time, like [0:05]",
        "help_srt": "also write .srt subtitles",
        "help_lang": "spoken language: es, en, … or auto (default: %(default)s)",
        "help_model": "Whisper model (default: %(default)s)",
        "help_device": "where to run the model (default: %(default)s)",
        "help_ui_lang": "interface language (default: from the system)",
        "help_quiet": "don't print the transcript (only save files)",
        "subtitle": "local · offline",
        "q_files": "Audio files",
        "q_files_hint": "space selects · type to search · enter confirms",
        "opt_search_all": "↳ Search the whole machine…",
        "opt_browse": "↳ Type a path…",
        "searching": "Searching for audio and video files…",
        "found_n": "{n} files found",
        "none_found": "No audio or video files found.",
        "q_path": "Path to a file or folder",
        "q_lang": "Language",
        "lang_es": "Spanish",
        "lang_en": "English",
        "lang_auto": "Detect automatically",
        "q_timestamps": "Timestamps",
        "yes": "Yes",
        "no": "No",
        "q_output": "Output",
        "out_screen": "Screen",
        "out_txt": ".txt",
        "out_srt": ".srt (subtitles)",
        "q_where": "Save to",
        "where_next": "Next to the audio",
        "where_pick": "Choose folder…",
        "q_folder": "Folder",
        "nothing_selected": "Nothing selected.",
        "loading_model": "Loading model {model} ({device})…",
        "gpu_fallback": "GPU not usable ({reason}); using the CPU.",
        "saved": "saved",
        "detected": "detected language: {lang}",
        "took": "{audio} of audio in {secs:.1f} s",
        "err_ffmpeg": "ffmpeg is not installed. Install it (e.g. `sudo pacman -S ffmpeg`, "
        "`sudo apt install ffmpeg`, `brew install ffmpeg`) and try again.",
        "err_missing": "File not found: {path}",
        "err_not_media": "Not an audio/video file: {path}",
        "err_decode": "Could not read {path}: {detail}",
        "err_no_tty": "No files given. Pass files, or run it in a terminal for the "
        "interactive mode.",
        "cancelled": "Cancelled.",
        "summary": "{ok} of {total} transcribed",
        "ago_now": "just now",
        "ago_min": "{n} min ago",
        "ago_h": "{n} h ago",
        "ago_yesterday": "yesterday",
        "ago_days": "{n} days ago",
    },
    "es": {
        "description": "Transcribe audio y video en local (sin internet) con faster-whisper. "
        "Ejecútalo sin archivos para abrir el selector interactivo.",
        "help_files": "archivos de audio o video a transcribir",
        "help_output": "guarda un .txt junto a cada archivo, o dentro de DIR",
        "help_timestamps": "antepone a cada línea su tiempo, como [0:05]",
        "help_srt": "genera también subtítulos .srt",
        "help_lang": "idioma hablado: es, en, … o auto (por defecto: %(default)s)",
        "help_model": "modelo de Whisper (por defecto: %(default)s)",
        "help_device": "dónde correr el modelo (por defecto: %(default)s)",
        "help_ui_lang": "idioma de la interfaz (por defecto: el del sistema)",
        "help_quiet": "no imprime la transcripción (solo guarda archivos)",
        "subtitle": "local · sin internet",
        "q_files": "Audios",
        "q_files_hint": "espacio marca · escribe para buscar · enter confirma",
        "opt_search_all": "↳ Buscar en toda la máquina…",
        "opt_browse": "↳ Escribir una ruta…",
        "searching": "Buscando archivos de audio y video…",
        "found_n": "{n} archivos encontrados",
        "none_found": "No se encontraron archivos de audio ni video.",
        "q_path": "Ruta de un archivo o carpeta",
        "q_lang": "Idioma",
        "lang_es": "Español",
        "lang_en": "Inglés",
        "lang_auto": "Detectar solo",
        "q_timestamps": "Marcas de tiempo",
        "yes": "Sí",
        "no": "No",
        "q_output": "Salida",
        "out_screen": "Pantalla",
        "out_txt": ".txt",
        "out_srt": ".srt (subtítulos)",
        "q_where": "Guardar en",
        "where_next": "Junto al audio",
        "where_pick": "Elegir carpeta…",
        "q_folder": "Carpeta",
        "nothing_selected": "No elegiste nada.",
        "loading_model": "Cargando el modelo {model} ({device})…",
        "gpu_fallback": "La GPU no se puede usar ({reason}); sigo con la CPU.",
        "saved": "guardado",
        "detected": "idioma detectado: {lang}",
        "took": "{audio} de audio en {secs:.1f} s",
        "err_ffmpeg": "ffmpeg no está instalado. Instálalo (p. ej. `sudo pacman -S ffmpeg`, "
        "`sudo apt install ffmpeg`, `brew install ffmpeg`) y vuelve a intentar.",
        "err_missing": "No existe el archivo: {path}",
        "err_not_media": "No es un archivo de audio/video: {path}",
        "err_decode": "No se pudo leer {path}: {detail}",
        "err_no_tty": "No pasaste archivos. Pásalos como argumentos, o ejecútalo en una "
        "terminal para el modo interactivo.",
        "cancelled": "Cancelado.",
        "summary": "{ok} de {total} transcritos",
        "ago_now": "recién",
        "ago_min": "hace {n} min",
        "ago_h": "hace {n} h",
        "ago_yesterday": "ayer",
        "ago_days": "hace {n} días",
    },
}

_current = "en"


def detect(env: Mapping[str, str] | None = None) -> str:
    """``es`` if the locale is Spanish (es_BO.UTF-8, es…), otherwise ``en``."""
    env = os.environ if env is None else env
    for var in ("TRANSCRIBE_UI_LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        value = env.get(var, "")
        if value:
            return "es" if value.lower().startswith("es") else "en"
    return "en"


def set_lang(lang: str) -> None:
    global _current
    _current = lang if lang in STRINGS else "en"


def get_lang() -> str:
    return _current


def t(key: str, **kwargs: object) -> str:
    text = STRINGS[_current].get(key) or STRINGS["en"][key]
    return text.format(**kwargs) if kwargs else text
