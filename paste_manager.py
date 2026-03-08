"""
paste_manager.py – Optional auto-paste functionality.

Simulates Ctrl+V to paste clipboard content into the active text field.
This is opt-in and guarded by the auto_paste setting.
"""

import logging
import time

logger = logging.getLogger(__name__)


def auto_paste(delay: float = 0.3) -> bool:
    """
    Simulate Ctrl+V to paste from clipboard into the active window.

    Args:
        delay: Seconds to wait before pasting (gives time for focus to settle).

    Returns:
        True if paste was attempted, False on error.
    """
    try:
        import pyautogui

        time.sleep(delay)
        pyautogui.hotkey("ctrl", "v")
        logger.info("Auto-paste executed (Ctrl+V)")
        return True

    except ImportError:
        logger.warning("pyautogui not installed – auto-paste unavailable")
        return False
    except Exception as e:
        logger.error("Auto-paste failed: %s", e)
        return False
