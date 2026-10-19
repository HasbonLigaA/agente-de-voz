"""Respuestas solo con datos autorizados (sin conocimiento externo ni Ollama libre)."""

from __future__ import annotations

import re
import unicodedata

from backend.brand import sanitize_institution_name
from backend.config import (
    GREETING_REPLY,
    GROUNDED_ONLY,
    IN_SCOPE_HELP_REPLY,
    OUT_OF_SCOPE_REPLY,
)
from backend.contact_reply import answer_contact
from backend.knowledge import (
    is_plan_liga_query,
    is_specialties_list_query,
    is_specialty_detail_query,
)
from backend.plan_liga_reply import answer_plan_liga
from backend.specialties_reply import answer_specialties, answer_specialty_topic

_GREETING_RE = re.compile(
    r"(?i)^\s*("
    r"hola|buenos?\s+d[ií]as|buenas?\s+tardes|buenas?\s+noches|"
    r"gracias|muchas\s+gracias|adi[oó]s|chao|ok|vale"
    r")\s*[.!?]*\s*$"
)

_HELP_RE = re.compile(
    r"(?i)\b("
    r"en\s+que\s+me\s+puedes?\s+ayudar|que\s+puedes?\s+hacer|"
    r"qu[eé]\s+informaci[oó]n\s+tienes|temas\s+disponibles|ayuda"
    r")\b"
)

_CONTACT_RE = re.compile(
    r"(?i)\b("
    r"citas?\s+m[eé]dicas?|tel[eé]fono|whatsapp|contacto|"
    r"direcci[oó]n|ubicaci[oó]n|correo|email|c[oó]mo\s+llegar|"
    r"n[uú]mero\s+para\s+citas"
    r")\b"
)


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def answer_grounded(user_text: str, history: list[dict[str, str]]) -> str:
    text = user_text.strip()
    if not text:
        return OUT_OF_SCOPE_REPLY

    if _GREETING_RE.match(text) and GREETING_REPLY.strip():
        return sanitize_institution_name(GREETING_REPLY.strip())

    if _HELP_RE.search(_norm(text)) and IN_SCOPE_HELP_REPLY.strip():
        return sanitize_institution_name(IN_SCOPE_HELP_REPLY.strip())

    if is_plan_liga_query(text):
        return answer_plan_liga(text)

    if is_specialty_detail_query(text):
        detail = answer_specialty_topic(text)
        if detail:
            return detail

    if is_specialties_list_query(text, history):
        return answer_specialties(text)

    if _CONTACT_RE.search(_norm(text)):
        return answer_contact()

    if GROUNDED_ONLY:
        return sanitize_institution_name(OUT_OF_SCOPE_REPLY)

    # Reservado: modo no recomendado (Ollama libre)
    from backend.llm import build_messages, chat

    return chat(build_messages(history))
