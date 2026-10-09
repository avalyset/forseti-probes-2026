"""Diff et snapshot mot det forrige og returner de endrede tekstblokkene.

Blokk = en setning eller et listepunkt i den tagg-strippede teksten.
"""
from __future__ import annotations

import difflib
import html
import re
from typing import List, Tuple

BLOCK = re.compile(r"(?<=[.!?])\s+|\n+")


def to_text(raw: bytes | str) -> str:
    s = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(re.sub(r"[ \t ]+", " ", s))


def blocks(text: str) -> List[str]:
    return [b.strip() for b in BLOCK.split(text) if len(b.strip()) > 2]


def changed_blocks(old: bytes | str, new: bytes | str) -> Tuple[List[str], List[str]]:
    """(lagt til / endret, fjernet). Blokker som star uendret er utelatt."""
    a, b = blocks(to_text(old)), blocks(to_text(new))
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    added, removed = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "insert"):
            added += b[j1:j2]
        if tag in ("replace", "delete"):
            removed += a[i1:i2]
    return added, removed
