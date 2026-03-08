"""
text_processing.py – Light transcript post-processing.

Cleans Whisper output without aggressive rewriting.
"""

import re


def clean_transcript(text: str | None) -> str:
    """
    Lightly clean a transcript string.

    - Strip leading/trailing whitespace
    - Collapse multiple spaces into one
    - Return empty string for None or whitespace-only input
    """
    if not text or not text.strip():
        return ""

    cleaned = text.strip()

    # Collapse multiple spaces
    cleaned = re.sub(r" {2,}", " ", cleaned)

    # Remove leading/trailing spaces around punctuation artifacts
    cleaned = re.sub(r"\s+([.,!?;:])", r"\1", cleaned)

    return cleaned
