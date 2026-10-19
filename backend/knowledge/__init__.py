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

_SPECIALTIES_RE = re.compile(
    r"(?i)\b("
    r"especialidades?|subespecialidades?|"
    r"que\s+especialidades|cuales\s+especialidades|cu[aá]ntas\s+especialidades|"
    r"lista\s+(de\s+)?especialidades?|"
    r"dimelas?\s+(todas?|completas?)|todas?\s+las?\s+especialidades|"
    r"dime\s+todas?\s+las?\s+especialidades"
    r")\b"
)

_FOLLOWUP_ALL_RE = re.compile(
    r"(?i)^\s*("
    r"dimelas?\s+(todas?|completas?)|"
    r"todas?\s+las?\s+(especialidades?)?|"
    r"la\s+lista\s+completa|"
    r"completas?|"
    r"enumera\s+todas?"
    r")\s*[.!?]*\s*$"
)


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def is_plan_liga_query(text: str) -> bool:
    return bool(_PLAN_LIGA_RE.search(_norm(text)))


def _history_mentions_specialties(messages: list[dict[str, str]]) -> bool:
    for msg in messages[-8:]:
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        low = _norm(content)
        if "especialidad" in low:
            return True
        if msg.get("role") == "assistant" and re.search(
            r"medicina familiar|neurocirug|dermatolog|gastroenterolog", low
        ):
            return True
    return False


def is_specialties_query(text: str, history: list[dict[str, str]] | None = None) -> bool:
    low = _norm(text)
    if _SPECIALTIES_RE.search(low):
        return True
    if _FOLLOWUP_ALL_RE.match(low) and history and _history_mentions_specialties(history):
        return True
    if re.search(r"dimelas?\s+todas|dime\s+todas|lista\s+completa", low) and history:
        if _history_mentions_specialties(history):
            return True
    return False


def plan_liga_context_json() -> str:
    return json.dumps(
        {"plan_liga": PLAN_LIGA, "fuente_oficial": PLAN_LIGA_SOURCE_URL},
        ensure_ascii=False,
        indent=2,
    )
