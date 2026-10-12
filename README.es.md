<div align="center">

# transcribe

**Transcripción local y sin internet desde tu terminal.**<br/>
Elige notas de voz, grabaciones o videos desde un menú interactivo (o pásalos como argumentos) y obtén el texto, con marcas de tiempo y subtítulos `.srt` si los quieres. Nada sale de tu computadora.

[![CI](https://github.com/rossmelabasto/ross_transcribe/actions/workflows/ci.yml/badge.svg)](https://github.com/rossmelabasto/ross_transcribe/actions/workflows/ci.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-a3e635.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-%E2%89%A53.10-6b4dff.svg)
![Sin internet](https://img.shields.io/badge/funciona-sin%20internet-6b4dff.svg)

[Instalación](#instalación) · [Uso](#uso) · [Modelos y hardware](#modelos-y-hardware) · [Cómo funciona](docs/ARCHITECTURE.md) · [Cambios](CHANGELOG.md) · [English](README.md)

<img src="docs/demo-es.gif" alt="transcribe: eligiendo dos audios, detectando español e inglés y guardando .txt y .srt" width="900" />

</div>

## Funciones

- **Selector interactivo.** Ejecuta `transcribe` sin argumentos: aparece tu carpeta de Descargas, de lo más nuevo a lo más viejo, con la duración y la antigüedad de cada archivo. Escribe para filtrar, espacio para marcar varios, enter para empezar.
- **Buscar en toda la máquina.** Una opción busca audios y videos en tu carpeta personal y en los discos montados (memorias USB, discos extra), saltando carpetas ocultas, cachés y `node_modules`. Usa [`fd`](https://github.com/sharkdp/fd) si está instalado.
- **Cualquier formato que lea ffmpeg.** Notas de voz de WhatsApp/Telegram (`.ogg`/`.opus`), `.mp3`, `.m4a`, `.wav`, `.flac`… y el audio de videos (`.mp4`, `.mkv`, `.mov`).
- **Marcas de tiempo y subtítulos.** `[0:05]` en cada línea y archivos `.srt` listos para cualquier reproductor o editor de video.
- **Español, inglés o automático.** Fija el idioma hablado o deja que Whisper lo detecte en cada archivo; útil para carpetas mezcladas.
- **Avance en vivo.** El texto aparece línea por línea mientras una barra muestra cuánto falta.
- **Interfaz bilingüe.** Menús y mensajes en español o inglés, según el idioma de tu sistema.
- **Para scripts.** Cada opción también es un flag, así que sirve en scripts, tareas programadas y acciones del explorador de archivos.
- **Privado y gratis.** Corre [faster-whisper](https://github.com/SYSTRAN/faster-whisper) en tu CPU (o GPU NVIDIA). Sin cuentas, sin claves de API, sin subir nada.

## Instalación

Necesitas **Python 3.10+** y **ffmpeg**.

```bash
# 1. ffmpeg (según tu sistema)
sudo pacman -S ffmpeg        # Arch
sudo apt install ffmpeg      # Debian/Ubuntu
brew install ffmpeg          # macOS

# 2. transcribe (una de las dos)
pipx install git+https://github.com/rossmelabasto/ross_transcribe
uv tool install git+https://github.com/rossmelabasto/ross_transcribe
```

Opcional: instala [`fd`](https://github.com/sharkdp/fd) para que la búsqueda en toda la máquina sea mucho más rápida.

La primera vez descarga el modelo de Whisper (~460 MB el `small`, que viene por defecto) desde Hugging Face; después todo funciona sin internet.

## Uso

### Interactivo

```bash
transcribe
```

1. **Audios**: elige de Descargas, o usa *Buscar en toda la máquina…* / *Escribir una ruta…* (un archivo o una carpeta).
2. **Idioma**: español, inglés o detectar solo.
3. **Marcas de tiempo**: sí / no.
4. **Salida**: pantalla, `.txt`, `.srt` (cualquier combinación).
5. **Guardar en**: junto a cada audio o en una carpeta que elijas.

> Tip: al escribir una ruta, el primer <kbd>Enter</kbd> acepta la sugerencia de autocompletado; el segundo confirma.

### Directo

```bash
transcribe nota-de-voz.ogg                   # muestra el texto
transcribe *.ogg -o                          # además guarda un .txt junto a cada uno
transcribe entrevista.m4a -t -o ~/apuntes    # marcas de tiempo, .txt en ~/apuntes
transcribe clase.mp4 --srt -l es             # subtítulos en español junto al video
transcribe llamada.wav -l auto -q --srt -o salida  # detecta idioma, solo guarda
```

| Flag | Qué hace |
|---|---|
| `-o`, `--output [DIR]` | Guarda un `.txt` junto a cada archivo, o dentro de `DIR` |
| `-t`, `--timestamps` | Antepone a cada línea su tiempo, como `[0:05]` |
| `--srt` | Genera también subtítulos `.srt` (misma carpeta que `-o`) |
| `-l`, `--lang IDIOMA` | Idioma hablado: `es`, `en`, cualquier código de Whisper o `auto` (por defecto) |
| `-m`, `--model NOMBRE` | `tiny`, `base`, `small` (por defecto), `medium`, `large-v3-turbo`, `large-v3` |
| `--device` | `auto` (por defecto), `cpu` o `cuda` |
| `-q`, `--quiet` | No muestra el texto (solo guarda archivos) |
| `--ui-lang` | Idioma de la interfaz: `en` o `es` (por defecto: el del sistema) |

Si ya existe un `.txt`/`.srt` con el mismo nombre, se reemplaza.

### Configuración

| Variable | Efecto |
|---|---|
| `TRANSCRIBE_LANG` | Idioma hablado por defecto (p. ej. `es`) en vez de `auto` |
| `TRANSCRIBE_UI_LANG` | Fuerza el idioma de la interfaz (`en`/`es`) |
| `HF_HOME` | Dónde se guardan los modelos (por defecto `~/.cache/huggingface`) |

Por ejemplo, un atajo en español:

```bash
# ~/.local/bin/transcribir
#!/bin/sh
TRANSCRIBE_UI_LANG=es TRANSCRIBE_LANG=es exec transcribe "$@"
```

## Modelos y hardware

| Modelo | Descarga | Notas |
|---|---|---|
| `tiny` / `base` | 75 / 145 MB | Los más rápidos, bastante menos precisos |
| **`small`** | 460 MB | **Por defecto.** Buena precisión para notas de voz; rápido en una CPU moderna |
| `medium` | 1,5 GB | Más preciso, ~3× más lento en CPU |
| `large-v3-turbo` | 1,6 GB | Casi la calidad de `large-v3`; ideal con GPU |
| `large-v3` | 3,1 GB | El más preciso; lento sin GPU |

En la CPU de una laptop (Intel Core Ultra 7 255HX), `small` transcribe unas **8–10 veces más rápido que el tiempo real**: una nota de voz de 30 segundos tarda ~3 s y una de 1 minuto ~6 s.

**GPU:** con `--device auto` se usa una GPU NVIDIA cuando CTranslate2 la ve **y** se pueden cargar las librerías de CUDA 12 (cuBLAS, cuDNN 9); ver las [notas de GPU de faster-whisper](https://github.com/SYSTRAN/faster-whisper#gpu). Si no, corre en la CPU sin avisar. Si la GPU falla a mitad de camino, pasa a la CPU y te dice por qué.

**Sobre la precisión:** incluso los modelos grandes pueden fallar con apodos o palabras dichas muy rápido. Si una palabra importa, compárala con el audio; las marcas de tiempo lo hacen rápido.

## Privacidad

El audio se decodifica y transcribe en tu máquina. El único acceso a la red es la descarga del modelo desde Hugging Face, una sola vez. Las transcripciones se guardan solo donde tú elijas.

## Desarrollo

```bash
git clone https://github.com/rossmelabasto/ross_transcribe && cd ross_transcribe
uv venv && uv pip install -e ".[dev]"     # o: python -m venv .venv && pip install -e ".[dev]"
.venv/bin/pytest -q                        # los tests usan un modelo falso: no descargan nada
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

Ver [CONTRIBUTING.md](CONTRIBUTING.md) y [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Créditos

- Reconocimiento de voz: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) y los modelos [Whisper](https://github.com/openai/whisper) de OpenAI.
- Interfaz: [questionary](https://github.com/tmbo/questionary) y [Rich](https://github.com/Textualize/rich), con colores [Catppuccin Mocha](https://catppuccin.com).
- Los audios de la demo son de dominio público; ver [docs/demo/CREDITS.md](docs/demo/CREDITS.md).

## Licencia

[MIT](LICENSE) © Rossmel Abasto — [portfolio.rossmel.com](https://portfolio.rossmel.com)
