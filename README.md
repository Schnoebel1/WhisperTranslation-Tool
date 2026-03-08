# WhisperTranslation Tool

A local, offline speech-to-text desktop app for Windows. Press a global hotkey to record, transcribe with Whisper, and automatically copy the result to your clipboard.

**No cloud. No API keys. No browser. Just fast, local transcription.**

---

## Features

- 🎙️ **Global hotkey** (`Ctrl+Alt+Space`) to start/stop recording
- 🧠 **Local Whisper transcription** via `faster-whisper`
- ⚡ **GPU-accelerated** (NVIDIA CUDA) with automatic CPU fallback
- 📋 **Auto-copy** transcript to clipboard
- 📌 **Optional auto-paste** into the active text field
- 🔔 **Windows toast notifications** for status feedback
- 🟢 **System tray** icon with color-coded state (idle/recording/transcribing/done)
- ⚙️ **Configurable** via `settings.json` (model, language, hotkey, device, etc.)
- 📝 **Logging** with rotation for diagnostics

---

## Project Structure

```
WhisperTranslation Tool/
├── app.py                 # Main tray app entry point
├── cli_test.py            # Phase 1 CLI test harness
├── config.py              # Configuration loading & validation
├── logger_setup.py        # Logging setup with rotation
├── audio_recorder.py      # Microphone recording (sounddevice)
├── transcriber.py         # Whisper transcription (faster-whisper)
├── text_processing.py     # Light transcript cleaning
├── clipboard_manager.py   # Clipboard copy (pyperclip)
├── paste_manager.py       # Optional auto-paste (pyautogui)
├── hotkeys.py             # Global hotkey manager (keyboard)
├── tray.py                # System tray icon & menu (pystray)
├── notifications.py       # Windows toast notifications (winotify)
├── settings.json          # User configuration
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

---

### Installation & Weitergabe

Es gibt zwei Wege, wie du das Tool auf deinem eigenen PC installieren oder an Freunde weitergeben kannst.

#### Methode 1: Die schnelle `.bat` Installation (Empfohlen für Freunde)
Der beste Weg, um das Tool an Freunde weiterzugeben, ist das Mitschicken der Installations-Datei.
Das spart dir hunderte Megabyte beim Verschicken, da die KI-Modelle und Bibliotheken erst beim Freund heruntergeladen werden.

1. Lösche den `venv/` Ordner (falls vorhanden, da dieser nur für deinen PC gilt).
2. Packe den kompletten Projektordner in eine ZIP-Datei und schicke sie deinem Freund.
3. Dein Freund entpackt die ZIP-Datei und führt **`Install-Whisper-Tool.bat`** per Doppelklick aus.
4. Das Skript installiert automatisch Python (falls nötig), lädt alle benötigten Bibliotheken herunter und erstellt eine Verknüpfung auf dem Desktop.

#### Methode 2: Die Standalone `.exe` bauen (PyInstaller)
Wenn du möchtest, dass Freunde überhaupt gar nichts installieren müssen (auch kein Python), kannst du eine eigenständige `.exe` bauen.
*Warnung: Der Build wird extrem groß (ca. 300+ MB) und Virenscanner schlagen bei solchen gesammelten KI-Programmen oft fälschlicherweise Alarm.*

1. Führe die Datei **`build_exe.bat`** per Doppelklick aus.
2. Warte, bis der Build-Prozess abgeschlossen ist.
3. Im Projektordner entsteht ein neuer Ordner namens **`dist/app`**.
4. Kopiere diesen gesamten Ordner (du kannst ihn z.B. in `WhisperTool` umbenennen), packe ihn in eine ZIP-Datei und verschicke ihn.
5. Dein Freund muss die ZIP entpacken und einfach die **`app.exe`** ausführen.

#### Methode 3: Manuelle Installation für Entwickler

```powershell
cd "C:\Users\YourName\Desktop\SoftwareEntwicklungen\WhisperTranslation Tool"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4: CUDA / GPU Setup (Optional but Recommended)

For GPU acceleration on your NVIDIA RTX 4070:

1. **Install CUDA Toolkit 12.x** from [developer.nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads)
2. **Install cuDNN** matching your CUDA version from [developer.nvidia.com/cudnn](https://developer.nvidia.com/cudnn)
3. `faster-whisper` uses `ctranslate2` under the hood, which includes its own CUDA runtime. In most cases, **having the NVIDIA driver up-to-date is sufficient**.

> **Tip:** If CUDA fails at runtime, the app automatically falls back to CPU. Check `whisper_tool.log` for details.

### Step 5: First Model Download

The Whisper model is downloaded automatically on first use (cached in `~/.cache/huggingface`):

| Model   | Size    | Speed  | Quality |
|---------|---------|--------|---------|
| `base`  | ~150 MB | Fast   | Basic   |
| `small` | ~500 MB | Medium | Good    |
| `medium`| ~1.5 GB | Slower | Great   |

Default is `medium` – change in `settings.json` if needed.

---

## Usage

### CLI Test Mode (Phase 1)

Validate that recording + transcription work on your system:

```powershell
.\venv\Scripts\activate
python cli_test.py
```

1. Press **Enter** to start recording
2. Speak into your microphone
3. Press **Enter** to stop
4. The transcript appears in the console and is copied to your clipboard

### Full Tray App (Production)

```powershell
.\venv\Scripts\activate
python app.py
```

1. A **tray icon** appears in the system tray (🟢 green = ready)
2. Press **Ctrl+Alt+Space** to start recording (icon turns 🔴 red)
3. Speak
4. Press **Ctrl+Alt+Space** again to stop (icon turns 🟠 orange during transcription)
5. Transcript is **copied to clipboard** (icon turns 🔵 blue briefly)
6. A **toast notification** shows a preview of the text

---

## Configuration

Edit `settings.json` to customize:

```json
{
    "model_size": "medium",
    "language": "de",
    "device_preference": "cuda",
    "compute_type_gpu": "float16",
    "compute_type_cpu": "int8",
    "auto_copy": true,
    "auto_paste": false,
    "hotkey": "ctrl+alt+space",
    "save_logs": true,
    "log_level": "INFO",
    "delete_temp_files": true,
    "microphone": null,
    "sample_rate": 16000,
    "channels": 1,
    "min_recording_seconds": 0.5,
    "beam_size": 5,
    "vad_filter": true
}
```

| Setting | Description |
|---------|-------------|
| `model_size` | Whisper model: `base`, `small`, `medium` |
| `language` | `de`, `en`, or `auto` for auto-detection |
| `device_preference` | `cuda` (GPU) or `cpu` |
| `compute_type_gpu` | `float16` is optimal for RTX 4070 |
| `compute_type_cpu` | `int8` for best CPU speed |
| `auto_copy` | Auto-copy transcript to clipboard |
| `auto_paste` | Auto-paste into active text field (use with caution) |
| `hotkey` | Global hotkey combination |
| `microphone` | `null` = system default, or a device name substring |
| `vad_filter` | Voice Activity Detection – filters silence |

---

## GPU / CPU Fallback

The app handles GPU availability gracefully:

1. **Preferred**: Loads model on `cuda` with `float16` compute type
2. **If CUDA fails**: Automatically falls back to `cpu` with `int8`
3. **Notification**: You get a toast telling you which device is active
4. **Logging**: All fallback events are logged to `whisper_tool.log`

The app **never crashes** due to CUDA issues – it always tries CPU as backup.

---

## Troubleshooting

### "No microphone found"
- Check Windows Sound Settings → Input
- Ensure your mic is not disabled or muted
- Try setting `"microphone": "your device name"` in `settings.json`

### Model loading very slow
- First run downloads the model (~1.5 GB for `medium`)
- Subsequent runs use the cached model
- Try `"model_size": "small"` for faster loading

### CUDA not detected
- Update your NVIDIA driver: [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx)
- The app falls back to CPU automatically – check `whisper_tool.log`
- Verify: `python -c "import ctranslate2; print(ctranslate2.get_cuda_device_count())"`

### Hotkey not working
- Some key combos may conflict with other apps
- Try a different hotkey in `settings.json`, e.g. `"ctrl+shift+f9"`
- The `keyboard` library may need to be run as administrator for some hotkeys

### Transcript is empty
- Check your microphone input level
- Speak clearly and for at least 1 second
- Ensure `vad_filter` is not filtering your speech (try `false`)

### Toast notifications not appearing
- Check Windows notification settings for the app
- Ensure "Do Not Disturb" / Focus Assist is off

---

## Known Risks / Limitations

1. **Hotkey conflicts**: `Ctrl+Alt+Space` may conflict with other apps – configurable
2. **Auto-paste reliability**: `pyautogui` paste may not work in all applications (kept optional)
3. **`keyboard` library**: May require elevated privileges for some key combinations
4. **First-run latency**: Initial model download takes time; subsequent starts are faster
5. **Medium model on CPU**: Can be slow (5-15s for a 10s recording) – GPU strongly recommended
6. **No streaming**: Transcription happens after recording stops (batch mode, not real-time)

---

## V2 Improvements

- [ ] Settings GUI window (model/language/device selection)
- [ ] Transcript history (last N results, searchable)
- [ ] Recording duration indicator in tray tooltip
- [ ] Audio level meter during recording
- [ ] Multi-language quick-switch hotkey
- [ ] PyInstaller packaging for single-exe distribution
- [ ] Startup with Windows (optional)
- [ ] Noise suppression pre-processing
- [ ] Real-time streaming transcription mode

---

## License

Personal/internal use. No cloud integration, no data collection.
