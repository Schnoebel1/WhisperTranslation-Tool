"""
notifications.py – Windows toast notifications using winotify.

Provides fire-and-forget desktop notifications for status feedback.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import winotify; graceful fallback if unavailable
try:
    from winotify import Notification, audio
    WINOTIFY_AVAILABLE = True
except ImportError:
    WINOTIFY_AVAILABLE = False
    logger.warning("winotify not available – notifications will be console-only")

APP_ID = "WhisperTranslation Tool"
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")


def notify(title: str, message: str, icon: Optional[str] = None) -> None:
    """
    Show a Windows toast notification.

    Falls back to console output if winotify is unavailable.

    Args:
        title: Notification title.
        message: Notification body text.
        icon: Optional path to an .ico file.
    """
    logger.info("Notification: [%s] %s", title, message)

    if not WINOTIFY_AVAILABLE:
        print(f"[{title}] {message}")
        return

    try:
        toast = Notification(
            app_id=APP_ID,
            title=title,
            msg=message,
            icon=icon if icon and os.path.exists(icon) else "",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception as e:
        logger.warning("Toast notification failed: %s", e)
        # Fallback to console
        print(f"[{title}] {message}")


# ── Convenience shortcuts ───────────────────────────────────────────────

def notify_recording_started() -> None:
    notify("🎙️ Recording", "Microphone recording started...")

def notify_recording_stopped() -> None:
    notify("⏹️ Recording Stopped", "Processing audio...")

def notify_transcribing() -> None:
    notify("⏳ Transcribing", "Running speech-to-text...")

def notify_success(text_preview: str) -> None:
    preview = text_preview[:80] + "..." if len(text_preview) > 80 else text_preview
    notify("✅ Copied to Clipboard", preview)

def notify_error(message: str) -> None:
    notify("❌ Error", message)

def notify_model_loaded(device_info: str) -> None:
    notify("✅ Model Ready", f"Whisper loaded on {device_info}")

def notify_model_loading() -> None:
    notify("⏳ Loading Model", "Preparing Whisper model...")
