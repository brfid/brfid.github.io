"""ASCII transliteration for vintage (ASCII-only) output targets.

The vintage pipeline feeds text to a 4.3BSD VAX guest that is ASCII-only, so
Unicode in `site.yaml` (em-dashes, curly quotes) must be transliterated before
injection. This is the only remaining consumer; resume rendering moved to Hugo.
"""

from __future__ import annotations

import unicodedata

# Common Unicode -> ASCII substitutions for content fed to ASCII-only vintage guests.
_UNICODE_SUBS: dict[str, str] = {
    "—": "--",  # em dash
    "–": "-",  # en dash
    "‘": "'",  # left single quotation mark
    "’": "'",  # right single quotation mark
    "“": '"',  # left double quotation mark
    "”": '"',  # right double quotation mark
    "…": "...",  # horizontal ellipsis
    " ": " ",  # non-breaking space
    "•": "*",  # bullet
}


def to_ascii(text: str) -> str:
    """Transliterate a Unicode string to ASCII for vintage (ASCII-only) targets.

    Applies a substitution table for common typographic characters, then uses
    NFKD normalization to decompose accented letters, then drops any remaining
    non-ASCII bytes.

    Args:
        text: Input string, possibly containing Unicode.

    Returns:
        ASCII-only string. Non-ASCII characters not covered by the substitution
        table or NFKD decomposition are replaced with '?'.
    """
    for ch, sub in _UNICODE_SUBS.items():
        text = text.replace(ch, sub)
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", errors="replace").decode("ascii")
