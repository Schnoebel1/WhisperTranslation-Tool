"""
clipboard_manager.py – Clipboard operations.

Copies text to the system clipboard using pyperclip.
"""

import logging

import pyperclip

logger = logging.getLogger(__name__)


def copy_to_clipboard(text: str) -> bool:
    """
    Copy text to the system clipboard.

    Args:
        text: The text to copy.

    Returns:
        True on success, False on failure.
    """
    if not text:
        logger.warning("Nothing to copy – text is empty")
        return False

    try:
        pyperclip.copy(text)
        logger.info("Text copied to clipboard (%d chars)", len(text))
        return True
    except pyperclip.PyperclipException as e:
        logger.error("Clipboard error: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected clipboard error: %s", e)
        return False
