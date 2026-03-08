"""
app.py – Main entry point for the WhisperTranslation Tool.

Combines all modules into the full tray-based speech-to-text application.
Orchestrates: hotkey → record → transcribe → clipboard → notify.
"""

import logging
import os
import sys
import threading
import time
import winsound

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config
from logger_setup import setup_logging
from audio_recorder import AudioRecorder, RecordingError
from transcriber import Transcriber, ModelLoadError, TranscriptionError
from text_processing import clean_transcript
from clipboard_manager import copy_to_clipboard
from paste_manager import auto_paste
from hotkeys import HotkeyManager
from tray import TrayApp, AppState
import notifications

logger = logging.getLogger(__name__)


class WhisperTranslationApp:
    """Main application controller."""

    def __init__(self):
        self.config = load_config()
        setup_logging(level=self.config.log_level, save_to_file=self.config.save_logs)

        logger.info("=" * 60)
        logger.info("  WhisperTranslation Tool starting")
        logger.info("=" * 60)

        # Components
        self.recorder = AudioRecorder(
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            device=self.config.microphone,
            min_duration=self.config.min_recording_seconds,
            delete_temp=self.config.delete_temp_files,
        )

        self.transcriber = Transcriber(
            model_size=self.config.model_size,
            device_preference=self.config.device_preference,
            compute_type_gpu=self.config.compute_type_gpu,
            compute_type_cpu=self.config.compute_type_cpu,
            language=self.config.language,
            beam_size=self.config.beam_size,
            vad_filter=self.config.vad_filter,
        )

        self.hotkey_manager = HotkeyManager()

        self.tray = TrayApp(
            config=self.config,
            on_toggle_recording=self.toggle_recording,
            on_quit=self.shutdown,
        )

        self._transcription_lock = threading.Lock()
        self._shutting_down = False

    # ── Startup ─────────────────────────────────────────────────────────

    def run(self):
        """Start the application."""
        # Show tray icon immediately (in LOADING state)
        self.tray.update_state(AppState.LOADING)

        # Load model in background thread
        model_thread = threading.Thread(target=self._load_model, daemon=True)
        model_thread.start()

        # Register hotkey
        hotkey_ok = self.hotkey_manager.register(
            self.config.hotkey, self.toggle_recording
        )
        if not hotkey_ok:
            logger.error("Could not register hotkey '%s'", self.config.hotkey)
            if getattr(self.config, "notifications", True):
                notifications.notify_error(
                    f"Could not register hotkey: {self.config.hotkey}"
                )

        # Run tray in a background thread so the main thread can catch Ctrl+C
        logger.info("Starting tray application...")
        self.tray.run_threaded()
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.shutdown()
            os._exit(0)
        finally:
            self.shutdown()

    def _load_model(self):
        """Load the Whisper model (runs in background thread)."""
        if getattr(self.config, "notifications", True):
            notifications.notify_model_loading()

        try:
            self.transcriber.load_model()
            self.tray.update_state(AppState.IDLE)
            if getattr(self.config, "notifications", True):
                notifications.notify_model_loaded(self.transcriber.device_info)
            logger.info("Model ready: %s", self.transcriber.device_info)
        except ModelLoadError as e:
            logger.error("Model loading failed: %s", e)
            self.tray.update_state(AppState.ERROR)
            if getattr(self.config, "notifications", True):
                notifications.notify_error(f"Model loading failed: {e}")

    def _play_sound(self, sound_type: str):
        if not getattr(self.config, "play_sound", True):
            return
        sound_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")
        if sound_type == "start":
            sound_path = os.path.join(sound_dir, "start.wav")
            if os.path.exists(sound_path):
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                threading.Thread(target=winsound.Beep, args=(1000, 150), daemon=True).start()
        elif sound_type == "stop":
            sound_path = os.path.join(sound_dir, "stop.wav")
            if os.path.exists(sound_path):
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                threading.Thread(target=winsound.Beep, args=(700, 150), daemon=True).start()

    # ── Recording toggle ────────────────────────────────────────────────

    def toggle_recording(self):
        """Toggle recording on/off. Called by hotkey or tray menu."""
        if self._shutting_down:
            return

        if self.recorder.is_recording:
            self._stop_and_transcribe()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start microphone recording."""
        if not self.transcriber.is_loaded:
            if getattr(self.config, "notifications", True):
                notifications.notify_error("Model not loaded yet – please wait")
            return

        try:
            self.recorder.start_recording()
            self.tray.update_state(AppState.RECORDING)
            self._play_sound("start")
            if getattr(self.config, "notifications", True):
                notifications.notify_recording_started()
        except RecordingError as e:
            logger.error("Failed to start recording: %s", e)
            self.tray.update_state(AppState.ERROR)
            if getattr(self.config, "notifications", True):
                notifications.notify_error(str(e))

    def _stop_and_transcribe(self):
        """Stop recording and transcribe in a background thread."""
        wav_path = self.recorder.stop_recording()
        self.tray.update_state(AppState.TRANSCRIBING)
        self._play_sound("stop")
            
        if getattr(self.config, "notifications", True):
            notifications.notify_recording_stopped()

        if wav_path is None:
            logger.warning("No audio to transcribe")
            if getattr(self.config, "notifications", True):
                notifications.notify_error("Recording too short or empty")
            self.tray.update_state(AppState.IDLE)
            return

        # Run transcription in background thread to keep UI responsive
        thread = threading.Thread(
            target=self._transcribe_and_copy,
            args=(wav_path,),
            daemon=True,
        )
        thread.start()

    def _transcribe_and_copy(self, wav_path: str):
        """Transcribe audio and copy result to clipboard (runs in background)."""
        with self._transcription_lock:
            try:
                if getattr(self.config, "notifications", True):
                    notifications.notify_transcribing()

                raw_text = self.transcriber.transcribe(wav_path)
                text = clean_transcript(raw_text)

                if not text:
                    logger.info("No speech detected")
                    if getattr(self.config, "notifications", True):
                        notifications.notify_error("No speech detected")
                    self.tray.update_state(AppState.IDLE)
                    return

                # Copy to clipboard
                if self.config.auto_copy:
                    if copy_to_clipboard(text):
                        if getattr(self.config, "notifications", True):
                            notifications.notify_success(text)
                        self.tray.update_state(AppState.COPIED)
                    else:
                        if getattr(self.config, "notifications", True):
                            notifications.notify_error("Could not copy to clipboard")
                        self.tray.update_state(AppState.ERROR)

                # Optional auto-paste
                if self.config.auto_paste:
                    auto_paste()

                # Log the result
                logger.info("Transcript: %s", text[:200])

                # Return to idle after a brief pause
                time.sleep(2)
                if self.tray.state == AppState.COPIED:
                    self.tray.update_state(AppState.IDLE)

            except TranscriptionError as e:
                logger.error("Transcription failed: %s", e)
                if getattr(self.config, "notifications", True):
                    notifications.notify_error(f"Transcription failed: {e}")
                self.tray.update_state(AppState.ERROR)
                time.sleep(3)
                self.tray.update_state(AppState.IDLE)

            finally:
                self.recorder.cleanup_file(wav_path)

    # ── Shutdown ────────────────────────────────────────────────────────

    def shutdown(self):
        """Clean shutdown of all components."""
        if self._shutting_down:
            return
        self._shutting_down = True

        logger.info("Shutting down...")

        self.hotkey_manager.stop()

        # Stop recording if active
        if self.recorder.is_recording:
            wav_path = self.recorder.stop_recording()
            if wav_path:
                self.recorder.cleanup_file(wav_path)

        self.tray.stop()
        logger.info("Shutdown complete")


# ── Entry point ─────────────────────────────────────────────────────────

def main():
    app = WhisperTranslationApp()
    app.run()


if __name__ == "__main__":
    main()
