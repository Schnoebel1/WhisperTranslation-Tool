"""
cli_test.py – Phase 1 CLI test harness.

Interactive loop: press Enter to start/stop recording, transcribe, and copy to clipboard.
This validates the core flow without hotkeys or tray.
"""

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config
from logger_setup import setup_logging
from audio_recorder import AudioRecorder, RecordingError
from transcriber import Transcriber, ModelLoadError, TranscriptionError
from text_processing import clean_transcript
from clipboard_manager import copy_to_clipboard


def main():
    # ── Initialize ──────────────────────────────────────────────────────
    config = load_config()
    setup_logging(level=config.log_level, save_to_file=config.save_logs)

    print("=" * 60)
    print("  WhisperTranslation Tool – CLI Test (Phase 1)")
    print("=" * 60)
    print()

    # List available microphones
    recorder = AudioRecorder(
        sample_rate=config.sample_rate,
        channels=config.channels,
        device=config.microphone,
        min_duration=config.min_recording_seconds,
        delete_temp=config.delete_temp_files,
    )

    print("Available microphones:")
    for dev in recorder.list_devices():
        print(f"  [{dev['index']}] {dev['name']} (ch={dev['channels']})")
    print()

    # Load Whisper model
    print(f"Loading Whisper model '{config.model_size}' "
          f"(preferred device: {config.device_preference})...")
    print("This may take a moment on first run (model download)...\n")

    transcriber = Transcriber(
        model_size=config.model_size,
        device_preference=config.device_preference,
        compute_type_gpu=config.compute_type_gpu,
        compute_type_cpu=config.compute_type_cpu,
        language=config.language,
        beam_size=config.beam_size,
        vad_filter=config.vad_filter,
    )

    try:
        transcriber.load_model()
    except ModelLoadError as e:
        print(f"\n[ERROR] Could not load model: {e}")
        print("Please check your installation and CUDA setup.")
        sys.exit(1)

    print(f"Model loaded: {transcriber.device_info}")
    print()
    print("-" * 60)
    print("  Ready! Press Enter to START recording.")
    print("  Press Enter again to STOP and transcribe.")
    print("  Type 'quit' or 'q' to exit.")
    print("-" * 60)
    print()

    # ── Main loop ───────────────────────────────────────────────────────
    while True:
        user_input = input(">> Press Enter to START recording (or 'q' to quit): ").strip()
        if user_input.lower() in ("q", "quit", "exit"):
            print("Goodbye!")
            break

        # Start recording
        try:
            recorder.start_recording()
            print("🎙️  RECORDING... Press Enter to STOP.")
        except RecordingError as e:
            print(f"[ERROR] {e}")
            continue

        # Wait for stop
        input()

        # Stop recording
        wav_path = recorder.stop_recording()

        if wav_path is None:
            print("[WARNING] Recording too short or empty. Try again.\n")
            continue

        print(f"Audio saved: {wav_path}")
        print("Transcribing...")

        # Transcribe
        try:
            raw_text = transcriber.transcribe(wav_path)
        except TranscriptionError as e:
            print(f"[ERROR] Transcription failed: {e}\n")
            recorder.cleanup_file(wav_path)
            continue

        # Clean text
        text = clean_transcript(raw_text)

        if not text:
            print("[INFO] No speech detected in recording.\n")
            recorder.cleanup_file(wav_path)
            continue

        # Output
        print()
        print("=" * 60)
        print("  TRANSCRIPT:")
        print("-" * 60)
        print(text)
        print("=" * 60)
        print()

        # Copy to clipboard
        if config.auto_copy:
            if copy_to_clipboard(text):
                print("✅ Copied to clipboard!")
            else:
                print("[WARNING] Could not copy to clipboard.")

        # Cleanup
        recorder.cleanup_file(wav_path)
        print()


if __name__ == "__main__":
    main()
