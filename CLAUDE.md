# VinylFlow — Claude Code Context

## Project Purpose
Desktop app to digitize vinyl records: upload a WAV/AIFF recording of a vinyl side, detect track boundaries via silence analysis, search Discogs for metadata, and export split + tagged FLAC/MP3/AIFF files.

---

## Stack

| Layer | Technology |
|-------|-----------|
| GUI | PySide6 (Qt 6 widgets, Fusion style + QSS dark theme) — **Windows only** |
| Waveform | QGraphicsView with custom items (bars, draggable regions, cursor) |
| System tray | QSystemTrayIcon (built-in) |
| Audio processing | FFmpeg (via subprocess) + Mutagen (tagging) + Pillow (cover art) |
| Discogs API | `discogs-client` Python library |
| Bundling | PyInstaller (`VinylFlow.spec`) |
| Installer | Inno Setup (`installer/VinylFlow.iss`) |
| CI/CD | GitHub Actions (`.github/workflows/`) |

---

## Directory Structure

```
vinylflow/
├── main.py                     # Entry point — QApplication, single-instance, env setup
├── audio_processor.py          # Silence detection, track splitting, ffmpeg wrappers
├── metadata_handler.py         # Discogs fetch, cover art download, audio tagging
├── config.py                   # Config management (settings.json > .env > env vars)
├── updater.py                  # GitHub release auto-update checker
├── version.py                  # __version__ constant
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # QMainWindow — layout orchestration + signal wiring
│   ├── styles.py               # QSS stylesheet + color constants
│   ├── file_panel.py           # Drag-drop upload zone + queue list
│   ├── waveform_widget.py      # QGraphicsView waveform + draggable regions
│   ├── tracks_panel.py         # Detected tracks list with preview/edit
│   ├── search_panel.py         # Discogs search + release card results
│   ├── mapping_panel.py        # Track mapping table + format selector + process button
│   ├── settings_dialog.py      # Settings QDialog
│   ├── setup_dialog.py         # First-run Discogs token setup
│   └── tray.py                 # QSystemTrayIcon wrapper
├── workers/
│   ├── __init__.py
│   ├── analyze_worker.py       # QThread: silence detection
│   ├── process_worker.py       # QThread: full processing pipeline
│   ├── search_worker.py        # QThread: Discogs API + cover art
│   ├── waveform_worker.py      # QThread: FFmpeg peak generation
│   └── preview_worker.py       # QThread: preview MP3 generation
├── assets/VinylFlow.ico        # App icon
├── VinylFlow.spec              # PyInstaller spec (PySide6, no pywebview/pythonnet)
├── installer/VinylFlow.iss     # Inno Setup script (no WebView2 bootstrapper)
├── rthooks/rthook_vinylflow.py # PyInstaller runtime hook (SSL certs only)
├── version_info.txt            # Windows EXE version metadata
├── requirements.txt
└── README.md
```

---

## Architecture & Data Flow

```
QMainWindow (ui/main_window.py)
        │  Qt signals/slots
   ┌────┴──────────────┬────────────────┬────────────────┐
   ▼                   ▼                ▼                ▼
QThread workers     UI panels        config.py      Discogs API
(workers/*.py)     (ui/*.py)        (settings)    (discogs-client)
   │
   ├── AnalyzeWorker    → audio_processor.py (ffmpeg subprocess)
   ├── WaveformWorker   → audio_processor.py (ffmpeg + numpy)
   ├── PreviewWorker    → audio_processor.py (ffmpeg)
   ├── SearchWorker     → metadata_handler.py (discogs-client)
   ├── CoverArtWorker   → requests (HTTP download)
   └── ProcessWorker    → audio_processor.py + metadata_handler.py
```

**Processing pipeline** (ProcessWorker in `workers/process_worker.py`):
1. Fetch release from Discogs
2. Apply user's track→position mapping (A1, B2, etc.)
3. Create output folder: `{Artist} - {Album}/`
4. Download + embed cover art
5. For each track: ffmpeg extract → convert to format → tag → rename
6. Emit completion signal

**Upload session storage:**
- Source file: `VINYLFLOW_UPLOAD_DIR/{file_id}/source.{ext}`
- Output: `DEFAULT_OUTPUT_DIR/{Artist} - {Album}/{position}-{title}.{fmt}`

---

## Environment Variables

All set by `main.py:configure_desktop_environment()`. **Never hardcode paths in audio_processor.py.**

| Variable | Set by | Purpose |
|----------|--------|---------|
| `VINYLFLOW_CONFIG_DIR` | main.py | Platform config dir (AppData) |
| `VINYLFLOW_UPLOAD_DIR` | main.py | Temp uploads dir |
| `VINYLFLOW_FFMPEG_PATH` | main.py | Absolute path to ffmpeg binary |
| `DEFAULT_OUTPUT_DIR` | main.py | Default output folder |
| `DISCOGS_USER_TOKEN` | user / settings.json | Discogs API token |
| `DISCOGS_USER_AGENT` | user / settings.json | Discogs API user agent |
| `DEFAULT_SILENCE_THRESHOLD` | config | Silence detection threshold (dB) |
| `DEFAULT_MIN_SILENCE_DURATION` | config | Min silence gap (seconds) |
| `DEFAULT_MIN_TRACK_LENGTH` | config | Min track length (seconds) |
| `DEFAULT_FLAC_COMPRESSION` | config | FLAC compression level 0–8 |
| `TEMP_TTL_HOURS` | config | Temp file cleanup timeout |

**Config priority (highest → lowest):** `settings.json` → `.env` → environment vars → code defaults

---

## PyInstaller / Bundling Rules

1. **Collect** `certifi` data files in spec so `cacert.pem` is present → HTTPS to Discogs works.
2. **UPX exclusion** — `ffmpeg.exe` must be in `upx_exclude` (UPX-packed ffmpeg is flagged by Windows Defender).
3. **Runtime hook** `rthooks/rthook_vinylflow.py` sets `SSL_CERT_FILE` + `REQUESTS_CA_BUNDLE` → bundled `cacert.pem`.
4. Bundle `assets/VinylFlow.ico` so the system tray icon is available at runtime.
5. Set `version='version_info.txt'` in `EXE()` so Windows shows version info in file Properties.
6. **Exclude** unused Qt modules (QtWebEngine, Qt3D, QtQuick, etc.) to reduce bundle size.
7. PySide6 hidden imports: `QtCore`, `QtGui`, `QtWidgets`, `QtNetwork`, `QtMultimedia`.

---

## FFmpeg Usage Rules

- `audio_processor.py` **must** call `_ffmpeg()` helper (not hardcode `"ffmpeg"`) — reads `VINYLFLOW_FFMPEG_PATH`.
- Use `encoding='utf-8', errors='replace'` on subprocess calls — **not** `text=True` (breaks on Windows with non-ASCII).
- `main.py` `_bundled_ffmpeg_path()` looks for `ffmpeg.exe` only (Windows-only app).

---

## UI Architecture (PySide6)

- **No build step** — pure Python widgets, no npm/webpack.
- Dark theme with amber/gold accents defined in `ui/styles.py`.
- All background work (FFmpeg, Discogs API) runs in QThread workers to keep UI responsive.
- Workers communicate with UI via Qt signals (progress, finished, error).
- QGraphicsView-based waveform with custom items:
  - `WaveformBarsItem`: vertical bars from numpy peak data
  - `TrackRegionItem`: colored rectangles with draggable left/right handles
  - `PlaybackCursor`: animated vertical line during playback
- Single-instance enforcement via Win32 mutex + QLocalServer/QLocalSocket for file forwarding.
- Window state (position, size) persisted in settings.json.

---

## Deployment Modes

| Mode | Command | Notes |
|------|---------|-------|
| Desktop (installer) | `VinylFlow-Setup.exe` | Inno Setup installer |
| Desktop (portable) | `VinylFlow.exe` | PyInstaller one-folder bundle |
| Local dev | `python main.py` | Opens native Qt window |

---

## GitHub Actions

- **`windows-release.yml`** — Manual trigger with `tag` input. Builds on `windows-latest`, installs FFmpeg + Inno Setup via Chocolatey, runs PyInstaller, builds installer, uploads `VinylFlow-windows-unsigned.zip` and `VinylFlow-Setup-{version}.exe` to the release.
- **`privacy-guard.yml`** — Scans commits for secrets.
- **`release-artifact-scan.yml`** — Scans release assets before publishing.

---

## Audio Formats

- **Input:** `.wav`, `.aiff`, `.aif`, `.flac` — minimum 60 seconds
- **Output:** FLAC (configurable compression 0–8), MP3 (320 kbps), AIFF (PCM 16-bit big-endian)
- **Tagging:** Mutagen handles all three formats; cover art embedded as bytes

---

## Python Dependencies (key ones)

```
PySide6                      # GUI framework (Qt 6 widgets)
mutagen                      # Audio tagging
discogs-client               # Discogs API
requests, certifi            # HTTP + SSL
pillow                       # Cover art processing
numpy                        # Waveform peak generation
python-dotenv                # .env parsing
```

---

## Legacy Files (removed in PySide6 rewrite)

The following files from the FastAPI+pywebview architecture are no longer used:
- `backend/api.py` — replaced by direct function calls from Qt workers
- `backend/static/` (app.js, index.html, vendor/) — replaced by PySide6 widgets
- `desktop_launcher.py` — replaced by `main.py`
- `system_tray.py` — replaced by `ui/tray.py` (QSystemTrayIcon)
