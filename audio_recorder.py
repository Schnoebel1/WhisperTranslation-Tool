"""
audio_recorder.py – Microphone recording with sounddevice.

Provides start/stop recording and saves WAV files.
Thread-safe design: recording runs in a sounddevice callback thread.
"""

import logging
import os
import tempfile
import threading
import time
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Records audio from the microphone and saves to WAV."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device: Optional[str | int] = None,
        min_duration: float = 0.5,
        delete_temp: bool = True,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device  # None = system default
        self.min_duration = min_duration
        self.delete_temp = delete_temp

        self._stream: Optional[sd.InputStream] = None
        self._chunks: list[np.ndarray] = []
        self._is_recording = False
        self._lock = threading.Lock()
        self._start_time: float = 0.0

    # ── Public API ──────────────────────────────────────────────────────

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start_recording(self) -> None:
        """Start recording from the microphone."""
        with self._lock:
            if self._is_recording:
                logger.warning("Recording already in progress")
                return

            self._chunks = []
            device_to_use = self._resolve_device()

            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="float32",
                    device=device_to_use,
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._is_recording = True
                self._start_time = time.time()
                logger.info(
                    "Recording started (device=%s, rate=%d, ch=%d)",
                    device_to_use or "default",
                    self.sample_rate,
                    self.channels,
                )
            except sd.PortAudioError as e:
                logger.error("Failed to start recording: %s", e)
                raise RecordingError(f"Could not start recording: {e}") from e

    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and save to a temporary WAV file.

        Returns:
            Path to the WAV file, or None if recording was too short / empty.
        """
        with self._lock:
            if not self._is_recording:
                logger.warning("No recording in progress")
                return None

            duration = time.time() - self._start_time
            self._is_recording = False

            # Stop and close stream
            try:
                if self._stream is not None:
                    self._stream.stop()
                    self._stream.close()
                    self._stream = None
            except Exception as e:
                logger.error("Error stopping audio stream: %s", e)

        logger.info("Recording stopped (duration=%.1fs)", duration)

        # Check minimum duration
        if duration < self.min_duration:
            logger.warning(
                "Recording too short (%.2fs < %.2fs), discarding",
                duration,
                self.min_duration,
            )
            return None

        # Check for actual audio data
        if not self._chunks:
            logger.warning("No audio data captured")
            return None

        return self._save_wav()

    def list_devices(self) -> list[dict]:
        """List available audio input devices."""
        devices = sd.query_devices()
        input_devices = []
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                input_devices.append({
                    "index": i,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": dev["default_samplerate"],
                })
        return input_devices

    # ── Private ─────────────────────────────────────────────────────────

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Called by sounddevice for each audio block."""
        if status:
            logger.debug("Audio callback status: %s", status)
        self._chunks.append(indata.copy())

    def _resolve_device(self) -> Optional[int]:
        """Resolve device name to index, or return None for default."""
        if self.device is None:
            return None

        if isinstance(self.device, int):
            return self.device

        # Search by name substring
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if (
                self.device.lower() in dev["name"].lower()
                and dev["max_input_channels"] > 0
            ):
                logger.info("Matched microphone: '%s' (index %d)", dev["name"], i)
                return i

        logger.warning(
            "Microphone '%s' not found, using system default", self.device
        )
        return None

    def _save_wav(self) -> Optional[str]:
        """Concatenate chunks and save to a temporary WAV file."""
        try:
            audio_data = np.concatenate(self._chunks, axis=0)
        except ValueError as e:
            logger.error("Failed to concatenate audio chunks: %s", e)
            return None

        # Check for silence / empty
        if np.max(np.abs(audio_data)) < 1e-6:
            logger.warning("Recording appears to be silence")
            # Still save it – Whisper can handle silence gracefully

        try:
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            fd, wav_path = tempfile.mkstemp(suffix=".wav", dir=temp_dir)
            os.close(fd)

            sf.write(wav_path, audio_data, self.sample_rate)
            logger.info("Audio saved: %s (%.1f MB)", wav_path, os.path.getsize(wav_path) / (1024 * 1024))
            return wav_path

        except (OSError, sf.SoundFileError) as e:
            logger.error("Failed to save WAV file: %s", e)
            return None

    def cleanup_file(self, wav_path: str) -> None:
        """Delete a temporary WAV file if configured to do so."""
        if self.delete_temp and wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
                logger.debug("Temp file deleted: %s", wav_path)
            except OSError as e:
                logger.warning("Could not delete temp file %s: %s", wav_path, e)


class RecordingError(Exception):
    """Raised when recording fails to start."""
    pass
