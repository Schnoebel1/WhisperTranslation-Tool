"""
hotkeys.py – Global hotkey registration for Windows.

Uses the 'keyboard' library for reliable system-wide hotkey capture.
"""

import logging
import threading
from typing import Callable, Optional

import keyboard

logger = logging.getLogger(__name__)


class HotkeyManager:
    """Manages global hotkey registration and callbacks."""

    def __init__(self):
        self._registered_hotkeys: list[str] = []
        self._running = False

    def register(self, hotkey: str, callback: Callable[[], None]) -> bool:
        """
        Register a global hotkey.

        Args:
            hotkey: Key combination string, e.g. 'ctrl+alt+space'.
            callback: Function to call when hotkey is pressed.

        Returns:
            True if registration succeeded, False otherwise.
        """
        try:
            keyboard.add_hotkey(hotkey, callback, suppress=False)
            self._registered_hotkeys.append(hotkey)
            logger.info("Hotkey registered: %s", hotkey)
            return True
        except Exception as e:
            logger.error("Failed to register hotkey '%s': %s", hotkey, e)
            return False

    def unregister_all(self) -> None:
        """Unregister all hotkeys."""
        for hk in self._registered_hotkeys:
            try:
                keyboard.remove_hotkey(hk)
                logger.debug("Hotkey unregistered: %s", hk)
            except Exception as e:
                logger.warning("Error unregistering hotkey '%s': %s", hk, e)
        self._registered_hotkeys.clear()
        logger.info("All hotkeys unregistered")

    def wait(self) -> None:
        """Block and wait for hotkey events (useful for standalone testing)."""
        self._running = True
        logger.info("Hotkey listener active, waiting for events...")
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the hotkey listener."""
        self._running = False
        self.unregister_all()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        logger.info("Hotkey manager stopped")
