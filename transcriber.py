"""
transcriber.py – Whisper transcription wrapper using faster-whisper.

Handles model initialization with GPU/CPU fallback and transcription.
The model is loaded once and reused across transcriptions.
"""

import logging
import os
import site
from typing import Optional

logger = logging.getLogger(__name__)


class Transcriber:
    """Wrapper around faster-whisper for local speech-to-text."""

    def __init__(
        self,
        model_size: str = "medium",
        device_preference: str = "cuda",
        compute_type_gpu: str = "float16",
        compute_type_cpu: str = "int8",
        language: str = "de",
        beam_size: int = 5,
        vad_filter: bool = True,
    ):
        self.model_size = model_size
        self.device_preference = device_preference
        self.compute_type_gpu = compute_type_gpu
        self.compute_type_cpu = compute_type_cpu
        self.language = language
        self.beam_size = beam_size
        self.vad_filter = vad_filter

        self._model = None
        self._actual_device: Optional[str] = None
        self._actual_compute_type: Optional[str] = None
        self._dll_directory_handles: list[object] = []
        self._dll_paths_patched = False

    # ── Public API ──────────────────────────────────────────────────────

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def device_info(self) -> str:
        if self._actual_device:
            return f"{self._actual_device} ({self._actual_compute_type})"
        return "not loaded"

    def _patch_nvidia_library_paths(self) -> None:
        """
        Ensure pip-installed NVIDIA runtime DLL folders are visible on Windows.

        This is required for ctranslate2/faster-whisper when CUDA libs come
        from Python wheels (nvidia-* packages) instead of a full system install.
        """
        if self._dll_paths_patched or os.name != "nt":
            return

        self._dll_paths_patched = True
        add_dll_directory = getattr(os, "add_dll_directory", None)

        try:
            site_packages = list(site.getsitepackages())
        except Exception:
            site_packages = []

        try:
            user_site = site.getusersitepackages()
            if user_site:
                site_packages.append(user_site)
        except Exception:
            pass

        discovered_bins: list[str] = []
        for sp in site_packages:
            nvidia_base = os.path.join(sp, "nvidia")
            if not os.path.isdir(nvidia_base):
                continue
            try:
                entries = list(os.scandir(nvidia_base))
            except OSError:
                continue
            for entry in entries:
                if not entry.is_dir():
                    continue
                lib_bin = os.path.join(entry.path, "bin")
                if os.path.isdir(lib_bin):
                    discovered_bins.append(lib_bin)

        # Deduplicate while preserving order.
        unique_bins: list[str] = []
        seen: set[str] = set()
        for lib_bin in discovered_bins:
            normalized = os.path.normcase(os.path.normpath(lib_bin))
            if normalized in seen:
                continue
            seen.add(normalized)
            unique_bins.append(lib_bin)

        path_parts = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
        path_known = {os.path.normcase(os.path.normpath(p)) for p in path_parts}

        for lib_bin in unique_bins:
            normalized = os.path.normcase(os.path.normpath(lib_bin))
            if normalized not in path_known:
                path_parts.insert(0, lib_bin)
                path_known.add(normalized)
                logger.debug("Added NVIDIA lib to PATH: %s", lib_bin)

            if add_dll_directory is not None:
                try:
                    handle = add_dll_directory(lib_bin)
                except OSError as e:
                    logger.debug("Could not register DLL directory '%s': %s", lib_bin, e)
                else:
                    # Keep handles alive for process lifetime.
                    self._dll_directory_handles.append(handle)
                    logger.debug("Registered DLL directory: %s", lib_bin)

        if path_parts:
            os.environ["PATH"] = os.pathsep.join(path_parts)

    @staticmethod
    def _is_missing_cuda_runtime_error(error: Exception) -> bool:
        message = str(error).lower()
        return ".dll" in message and any(
            marker in message for marker in ("cublas", "cudnn", "cudart", "nvcuda")
        )

    def load_model(self) -> None:
        """
        Load the Whisper model. Tries GPU first, falls back to CPU.

        This should be called once at startup (potentially in a background thread).
        """
        if self._model is not None:
            logger.info("Model already loaded, skipping reload")
            return

        if self.device_preference == "cuda":
            self._patch_nvidia_library_paths()

        import numpy as np
        from faster_whisper import WhisperModel

        # Try GPU first
        if self.device_preference == "cuda":
            try:
                logger.info(
                    "Loading model '%s' on CUDA (compute_type=%s)...",
                    self.model_size,
                    self.compute_type_gpu,
                )
                self._model = WhisperModel(
                    self.model_size,
                    device="cuda",
                    compute_type=self.compute_type_gpu,
                )
                
                # Run one short inference pass to verify CUDA is truly usable.
                # Creating the model object alone is not enough for validation.
                logger.debug("Verifying CUDA inference with dummy audio...")
                dummy_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
                segments, _ = self._model.transcribe(
                    dummy_audio,
                    beam_size=1,
                    vad_filter=False,
                )
                for _ in segments:
                    pass

                self._actual_device = "cuda"
                self._actual_compute_type = self.compute_type_gpu
                logger.info("Model loaded and verified successfully on CUDA")
                return
            except Exception as e:
                if self._is_missing_cuda_runtime_error(e):
                    logger.info("CUDA runtime libraries are unavailable: %s", e)
                else:
                    logger.warning("CUDA initialization/verification failed: %s", e)
                logger.info("Falling back to CPU...")
                # Reset model in case it was partially loaded
                self._model = None

        # CPU fallback
        try:
            logger.info(
                "Loading model '%s' on CPU (compute_type=%s)...",
                self.model_size,
                self.compute_type_cpu,
            )
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type=self.compute_type_cpu,
            )
            self._actual_device = "cpu"
            self._actual_compute_type = self.compute_type_cpu
            logger.info("Model loaded successfully on CPU")
        except Exception as e:
            logger.error("Failed to load model on CPU: %s", e)
            raise ModelLoadError(
                f"Could not load Whisper model '{self.model_size}' on any device: {e}"
            ) from e

    def transcribe(self, wav_path: str) -> str:
        """
        Transcribe an audio file.

        Args:
            wav_path: Path to WAV file.

        Returns:
            Transcribed text (may be empty string if nothing recognized).

        Raises:
            TranscriptionError: If transcription fails.
            ModelLoadError: If model is not loaded.
        """
        if self._model is None:
            raise ModelLoadError("Model not loaded. Call load_model() first.")

        if not os.path.exists(wav_path):
            raise TranscriptionError(f"Audio file not found: {wav_path}")

        try:
            logger.info("Transcribing: %s", os.path.basename(wav_path))

            # Set language (None for auto-detect)
            lang = None if self.language == "auto" else self.language

            segments, info = self._model.transcribe(
                wav_path,
                language=lang,
                beam_size=self.beam_size,
                vad_filter=self.vad_filter,
            )

            # Collect all segment texts
            texts = []
            for segment in segments:
                texts.append(segment.text)
                logger.debug(
                    "[%.1fs -> %.1fs] %s",
                    segment.start,
                    segment.end,
                    segment.text.strip(),
                )

            full_text = " ".join(texts)

            logger.info(
                "Transcription complete (lang=%s, prob=%.2f, duration=%.1fs): %d chars",
                info.language,
                info.language_probability,
                info.duration,
                len(full_text),
            )

            return full_text

        except Exception as e:
            logger.error("Transcription failed: %s", e)
            raise TranscriptionError(f"Transcription failed: {e}") from e


class ModelLoadError(Exception):
    """Raised when the Whisper model cannot be loaded."""
    pass


class TranscriptionError(Exception):
    """Raised when transcription fails."""
    pass
