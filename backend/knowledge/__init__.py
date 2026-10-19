from __future__ import annotations

import json
import re
import unicodedata

from backend.knowledge.plan_liga import PLAN_LIGA, PLAN_LIGA_SOURCE_URL
from backend.knowledge.specialties import find_specialty_in_text

_PLAN_LIGA_RE = re.compile(
    r"(?i)\b("
    r"plan\s*liga|membres[ií]a|beneficiarios?|titular|"
    r"499\s*000|cu[aá]nto\s+(cuesta|vale|cobran)|precio\s+del\s+plan|"
    r"activar\s+(el\s+)?plan|comprobante\s+de\s+pago"
    r")\b"
)

_LIST_SPECIALTIES_RE = re.compile(
    r"(?i)\b("
    r"especialidades?\s+(hay|tiene|manejan|ofrecen|disponibles)|"
    r"que\s+especialidades|cuales\s+especialidades|cu[aá]ntas\s+especialidades|"
    r"lista\s+(de\s+)?especialidades?|"
    r"dimelas?\s+(todas?|completas?)|todas?\s+las?\s+especialidades|"
    r"dime\s+todas?\s+las?\s+especialidades|"
    r"cu[aá]ntos?\s+especialistas\s+(hay|tiene|en\s+total)"
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

_DETAIL_SPECIALTY_RE = re.compile(
    r"(?i)\b("
    r"para\s+que\s+sirve|que\s+es|qu[eé]\s+es|"
    r"hablame\s+de|cu[eé]ntame|explicame|"
    r"cu[aá]ntos?\s+especialistas\s+(en|de|hay)"
    r")\b"
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
        if "especialidad" in low or find_specialty_in_text(content):
            return True
    return False


def is_specialties_list_query(text: str, history: list[dict[str, str]] | None = None) -> bool:
    low = _norm(text)
    if find_specialty_in_text(text) and _DETAIL_SPECIALTY_RE.search(low):
        return False
    if find_specialty_in_text(text) and not _LIST_SPECIALTIES_RE.search(low):
        return False
    if _LIST_SPECIALTIES_RE.search(low):
        return True
    if _FOLLOWUP_ALL_RE.match(low) and history and _history_mentions_specialties(history):
        return True
    if re.search(r"dimelas?\s+todas|dime\s+todas|lista\s+completa", low) and history:
        if _history_mentions_specialties(history):
            return True
    return False


def is_specialty_detail_query(text: str) -> bool:
    low = _norm(text)
    if re.search(r"\boncolog", low):
        return True
    if find_specialty_in_text(text) and (
        _DETAIL_SPECIALTY_RE.search(low) or re.search(r"especialidad", low)
    ):
        return True
    return bool(find_specialty_in_text(text) and _DETAIL_SPECIALTY_RE.search(low))


def plan_liga_context_json() -> str:
    return json.dumps(
        {"plan_liga": PLAN_LIGA, "fuente_oficial": PLAN_LIGA_SOURCE_URL},
        ensure_ascii=False,
        indent=2,
    )
