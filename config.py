"""
config.py – Configuration loading and validation.

Loads settings from settings.json, applies defaults for missing keys,
and provides a simple Config object for the rest of the application.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

# ── Defaults ────────────────────────────────────────────────────────────────

DEFAULTS = {
    "model_size": "medium",
    "language": "de",
    "device_preference": "cuda",
    "compute_type_gpu": "float16",
    "compute_type_cpu": "int8",
    "auto_copy": True,
    "auto_paste": False,
    "notifications": True,
    "play_sound": True,
    "hotkey": "ctrl+alt+space",
    "save_logs": True,
    "log_level": "INFO",
    "delete_temp_files": True,
    "microphone": None,
    "sample_rate": 16000,
    "channels": 1,
    "min_recording_seconds": 0.5,
    "beam_size": 5,
    "vad_filter": True,
}

VALID_MODEL_SIZES = {"tiny", "base", "small", "medium", "large-v2", "large-v3"}
VALID_LANGUAGES = {"de", "en", "auto"}
VALID_DEVICES = {"cuda", "cpu"}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


# ── Config class ────────────────────────────────────────────────────────────

class Config:
    """Application configuration with validated values."""

    def __init__(self, data: dict):
        self.model_size: str = data.get("model_size", DEFAULTS["model_size"])
        self.language: str = data.get("language", DEFAULTS["language"])
        self.device_preference: str = data.get("device_preference", DEFAULTS["device_preference"])
        self.compute_type_gpu: str = data.get("compute_type_gpu", DEFAULTS["compute_type_gpu"])
        self.compute_type_cpu: str = data.get("compute_type_cpu", DEFAULTS["compute_type_cpu"])
        self.auto_copy: bool = data.get("auto_copy", DEFAULTS["auto_copy"])
        self.auto_paste: bool = data.get("auto_paste", DEFAULTS["auto_paste"])
        self.notifications: bool = data.get("notifications", DEFAULTS["notifications"])
        self.play_sound: bool = data.get("play_sound", DEFAULTS["play_sound"])
        self.hotkey: str = data.get("hotkey", DEFAULTS["hotkey"])
        self.save_logs: bool = data.get("save_logs", DEFAULTS["save_logs"])
        self.log_level: str = data.get("log_level", DEFAULTS["log_level"])
        self.delete_temp_files: bool = data.get("delete_temp_files", DEFAULTS["delete_temp_files"])
        self.microphone: str | None = data.get("microphone", DEFAULTS["microphone"])
        self.sample_rate: int = data.get("sample_rate", DEFAULTS["sample_rate"])
        self.channels: int = data.get("channels", DEFAULTS["channels"])
        self.min_recording_seconds: float = data.get("min_recording_seconds", DEFAULTS["min_recording_seconds"])
        self.beam_size: int = data.get("beam_size", DEFAULTS["beam_size"])
        self.vad_filter: bool = data.get("vad_filter", DEFAULTS["vad_filter"])

    def validate(self) -> list[str]:
        """Validate configuration values. Returns list of warning messages."""
        warnings = []

        if self.model_size not in VALID_MODEL_SIZES:
            warnings.append(f"Invalid model_size '{self.model_size}', falling back to 'medium'")
            self.model_size = "medium"

        if self.language not in VALID_LANGUAGES:
            warnings.append(f"Invalid language '{self.language}', falling back to 'de'")
            self.language = "de"

        if self.device_preference not in VALID_DEVICES:
            warnings.append(f"Invalid device_preference '{self.device_preference}', falling back to 'cuda'")
            self.device_preference = "cuda"

        if self.log_level not in VALID_LOG_LEVELS:
            warnings.append(f"Invalid log_level '{self.log_level}', falling back to 'INFO'")
            self.log_level = "INFO"

        if self.sample_rate not in (8000, 16000, 22050, 44100, 48000):
            warnings.append(f"Unusual sample_rate {self.sample_rate}, using 16000")
            self.sample_rate = 16000

        if self.channels not in (1, 2):
            warnings.append(f"Invalid channels {self.channels}, using 1")
            self.channels = 1

        if self.min_recording_seconds < 0.1:
            warnings.append("min_recording_seconds too low, using 0.5")
            self.min_recording_seconds = 0.5

        return warnings

    def __repr__(self) -> str:
        return (
            f"Config(model={self.model_size}, lang={self.language}, "
            f"device={self.device_preference}, hotkey={self.hotkey})"
        )
        
    def save(self) -> None:
        """Save mutable settings back to settings.json file."""
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
            
        data["auto_copy"] = self.auto_copy
        data["auto_paste"] = self.auto_paste
        data["notifications"] = self.notifications
        data["play_sound"] = self.play_sound
        
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.debug("Settings saved to disk.")
        except Exception as e:
            logger.error("Failed to save settings: %s", e)


# ── Loading ─────────────────────────────────────────────────────────────────

def load_config(path: str | None = None) -> Config:
    """Load configuration from JSON file. Creates default file if missing."""
    path = path or SETTINGS_PATH

    if not os.path.exists(path):
        logger.warning("Settings file not found at %s – creating default", path)
        _create_default_settings(path)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read settings file: %s – using defaults", e)
        data = {}

    config = Config(data)
    warnings = config.validate()
    for w in warnings:
        logger.warning(w)

    logger.info("Configuration loaded: %s", config)
    return config


def _create_default_settings(path: str) -> None:
    """Write default settings.json to disk."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULTS, f, indent=4, ensure_ascii=False)
        logger.info("Default settings created at %s", path)
    except OSError as e:
        logger.error("Could not create default settings file: %s", e)
