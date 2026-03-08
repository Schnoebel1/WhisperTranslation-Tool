"""
tray.py – System tray icon and menu using pystray.

Provides status indication via icon color and a right-click menu.
"""

import logging
import os
import threading
from enum import Enum
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

try:
    import pystray
    from pystray import MenuItem, Menu
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    logger.warning("pystray not available – tray will not be shown")


class AppState(Enum):
    """Application states reflected in the tray icon."""
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    COPIED = "copied"
    ERROR = "error"
    LOADING = "loading"


# Color map for each state
STATE_COLORS = {
    AppState.IDLE: "#4CAF50",        # Green
    AppState.RECORDING: "#F44336",   # Red
    AppState.TRANSCRIBING: "#FF9800",# Orange
    AppState.COPIED: "#2196F3",      # Blue
    AppState.ERROR: "#9E9E9E",       # Grey
    AppState.LOADING: "#FFC107",     # Amber
}

STATE_TOOLTIPS = {
    AppState.IDLE: "WhisperTranslation – Ready",
    AppState.RECORDING: "WhisperTranslation – Recording...",
    AppState.TRANSCRIBING: "WhisperTranslation – Transcribing...",
    AppState.COPIED: "WhisperTranslation – Copied!",
    AppState.ERROR: "WhisperTranslation – Error",
    AppState.LOADING: "WhisperTranslation – Loading model...",
}


class TrayApp:
    """System tray application with status-based icon and menu."""

    def __init__(
        self,
        config,
        on_toggle_recording: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ):
        self._config = config
        self._on_toggle_recording = on_toggle_recording
        self._on_quit = on_quit
        self._hotkey_label = config.hotkey.upper()
        self._icon = None
        self._state = AppState.LOADING
        self._thread: Optional[threading.Thread] = None

    @property
    def state(self) -> AppState:
        return self._state

    def update_state(self, state: AppState) -> None:
        """Update the tray icon to reflect the new state."""
        self._state = state
        if self._icon is not None:
            try:
                self._icon.icon = self._create_icon(state)
                self._icon.title = STATE_TOOLTIPS.get(state, "WhisperTranslation")
            except Exception as e:
                logger.warning("Failed to update tray icon: %s", e)

    def run(self) -> None:
        """Start the tray icon (blocking – run in a thread)."""
        if not PYSTRAY_AVAILABLE:
            logger.warning("pystray not available, skipping tray")
            return

        menu = Menu(
            MenuItem(
                lambda text: f"Status: {self._state.value.capitalize()}",
                action=None,
                enabled=False,
            ),
            Menu.SEPARATOR,
            MenuItem(
                f"Toggle Recording ({self._hotkey_label})",
                self._handle_toggle,
            ),
            Menu.SEPARATOR,
            MenuItem(
                "Settings",
                Menu(
                    MenuItem(
                        "Windows Notifications",
                        self._toggle_notifications,
                        checked=lambda item: getattr(self._config, "notifications", True),
                    ),
                    MenuItem(
                        "Sound Feedback",
                        self._toggle_sound,
                        checked=lambda item: getattr(self._config, "play_sound", True),
                    ),
                    MenuItem(
                        "Auto-Paste Text",
                        self._toggle_auto_paste,
                        checked=lambda item: getattr(self._config, "auto_paste", False),
                    ),
                )
            ),
            Menu.SEPARATOR,
            MenuItem("Quit", self._handle_quit),
        )

        self._icon = pystray.Icon(
            name="WhisperTranslation",
            icon=self._create_icon(self._state),
            title=STATE_TOOLTIPS.get(self._state, "WhisperTranslation"),
            menu=menu,
        )

        logger.info("Tray icon starting...")
        self._icon.run()

    def run_threaded(self) -> None:
        """Start the tray icon in a background thread."""
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the tray icon."""
        if self._icon is not None:
            try:
                self._icon.stop()
                logger.info("Tray icon stopped")
            except Exception as e:
                logger.warning("Error stopping tray: %s", e)

    # ── Private ─────────────────────────────────────────────────────────

    def _create_icon(self, state: AppState) -> Image.Image:
        """Generate a simple colored circle icon for the given state."""
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = STATE_COLORS.get(state, "#4CAF50")
        margin = 4
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=color,
            outline="#FFFFFF",
            width=2,
        )

        # Add a letter indicator
        letter = {
            AppState.IDLE: "W",
            AppState.RECORDING: "●",
            AppState.TRANSCRIBING: "⏳",
            AppState.COPIED: "✓",
            AppState.ERROR: "!",
            AppState.LOADING: "…",
        }.get(state, "W")

        try:
            # Use a basic font; may fall back to default
            font = ImageFont.truetype("arial.ttf", 24)
        except (OSError, IOError):
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), letter, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (size - text_w) // 2
        y = (size - text_h) // 2 - 2
        draw.text((x, y), letter, fill="#FFFFFF", font=font)

        return img

    def _handle_toggle(self, icon=None, item=None) -> None:
        if self._on_toggle_recording:
            self._on_toggle_recording()

    def _toggle_notifications(self, icon=None, item=None) -> None:
        if hasattr(self._config, "notifications"):
            self._config.notifications = not self._config.notifications
            self._config.save()

    def _toggle_sound(self, icon=None, item=None) -> None:
        if hasattr(self._config, "play_sound"):
            self._config.play_sound = not self._config.play_sound
            self._config.save()

    def _toggle_auto_paste(self, icon=None, item=None) -> None:
        if hasattr(self._config, "auto_paste"):
            self._config.auto_paste = not self._config.auto_paste
            self._config.save()

    def _handle_quit(self, icon=None, item=None) -> None:
        logger.info("Quit requested from tray")
        if self._on_quit:
            self._on_quit()
        self.stop()
        os._exit(0)  # Force exit to kill any hanging daemon threads (e.g. keyboard listener)
