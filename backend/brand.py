"""Nombre institucional y filtro de texto en respuestas."""

from __future__ import annotations

import re
import unicodedata

INSTITUTION_NAME = "La Liga Ama Salvar Vidas"

_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"liga\s+contra\s+(el\s+)?c[aá]ncer",
            re.IGNORECASE,
        ),
        INSTITUTION_NAME,
    ),
    (
        re.compile(r"fundaci[oó]n\s+contra\s+(el\s+)?c[aá]ncer", re.IGNORECASE),
        INSTITUTION_NAME,
    ),
)


def sanitize_institution_name(text: str) -> str:
    if not text:
        return text
    out = text
    for pattern, repl in _REPLACEMENTS:
        out = pattern.sub(repl, out)
    return out
