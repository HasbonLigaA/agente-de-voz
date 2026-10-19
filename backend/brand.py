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


_WEB_DEFLECT = re.compile(
    r"(?im)^[^\n]*("
    r"visita(?:r)?\s+(?:la\s+)?(?:p[aá]gina|web|sitio)|"
    r"revisa(?:r)?\s+(?:la\s+)?(?:p[aá]gina|web|sitio)|"
    r"mira(?:r)?\s+(?:en\s+)?(?:la\s+)?(?:p[aá]gina|web)|"
    r"consulta(?:r)?\s+(?:la\s+)?(?:p[aá]gina|web|sitio)|"
    r"puedes?\s+ver(?:las|los)?\s+(?:completas?|en\s+la\s+web)"
    r")[^\n]*\n?"
)


def sanitize_institution_name(text: str) -> str:
    if not text:
        return text
    out = text
    for pattern, repl in _REPLACEMENTS:
        out = pattern.sub(repl, out)
    out = _WEB_DEFLECT.sub("", out)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out
