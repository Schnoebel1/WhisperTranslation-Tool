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
        """Load the app icon and draw a status indicator badge."""
        size = 64
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        
        try:
            base_img = Image.open(icon_path).convert("RGBA")
            base_img = base_img.resize((size, size), Image.Resampling.LANCZOS)
        except Exception as e:
            logger.warning("Could not load icon.png: %s", e)
            base_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(base_img)
            draw.ellipse([4, 4, size - 4, size - 4], fill="#333333", outline="#FFFFFF")

        # In IDLE state, just show the logo
        if state == AppState.IDLE:
            return base_img

        # For other states, draw a badge in the bottom-right corner
        badge_radius = 12
        badge_center_x = size - badge_radius - 2
        badge_center_y = size - badge_radius - 2
        
        color = STATE_COLORS.get(state, "#4CAF50")
        
        draw = ImageDraw.Draw(base_img)
        draw.ellipse(
            [
                badge_center_x - badge_radius,
                badge_center_y - badge_radius,
                badge_center_x + badge_radius,
                badge_center_y + badge_radius
            ],
            fill=color,
            outline="#FFFFFF",
            width=2,
        )

        return base_img

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
