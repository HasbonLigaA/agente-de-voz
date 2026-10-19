from __future__ import annotations

import json
import re
import unicodedata

from backend.knowledge.plan_liga import PLAN_LIGA, PLAN_LIGA_SOURCE_URL

_PLAN_LIGA_RE = re.compile(
    r"(?i)\b("
    r"plan\s*liga|membres[ií]a|beneficiarios?|titular|"
    r"499\s*000|cu[aá]nto\s+(cuesta|vale|cobran)|precio\s+del\s+plan|"
    r"activar\s+(el\s+)?plan|comprobante\s+de\s+pago"
    r")\b"
)


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def is_plan_liga_query(text: str) -> bool:
    return bool(_PLAN_LIGA_RE.search(_norm(text)))


def plan_liga_context_json() -> str:
    return json.dumps(
        {"plan_liga": PLAN_LIGA, "fuente_oficial": PLAN_LIGA_SOURCE_URL},
        ensure_ascii=False,
        indent=2,
    )
