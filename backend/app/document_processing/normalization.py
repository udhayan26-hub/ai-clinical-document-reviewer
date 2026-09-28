"""Shared text-normalization used by every DocumentProcessor.

Kept separate from any single processor since PDF-extracted text
benefits from exactly the same cleanup as directly-submitted text.
"""

import re

_HORIZONTAL_WHITESPACE_RUN = re.compile(r"[ \t]+")
_SPACE_AROUND_NEWLINE = re.compile(r" *\n *")
_EXCESSIVE_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_whitespace(text: str) -> str:
    """Normalize line endings and collapse excessive whitespace while
    preserving paragraph structure (single blank lines are kept; runs of
    3+ newlines collapse to exactly one blank line).
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _HORIZONTAL_WHITESPACE_RUN.sub(" ", text)
    text = _SPACE_AROUND_NEWLINE.sub("\n", text)
    text = _EXCESSIVE_BLANK_LINES.sub("\n\n", text)
    return text.strip()
