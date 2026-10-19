"""Respuestas de especialidades (solo catálogo autorizado)."""

from __future__ import annotations

import re
import unicodedata

from backend.brand import sanitize_institution_name
from backend.knowledge.specialties import (
    SPECIALISTS_SOURCE_URL,
    SPECIALTY_AREAS_COUNT,
    SPECIALTY_BY_NAME,
    SPECIALTY_CATALOG,
    SPECIALTIES,
    TOTAL_SPECIALISTS_LABEL,
    find_specialty_in_text,
    is_known_specialty,
)

_DETAIL_RE = re.compile(
    r"(?i)\b("
    r"para\s+que\s+sirve|que\s+es|qu[eé]\s+es|"
    r"hablame\s+de|cu[eé]ntame\s+sobre|explicame|"
    r"cu[aá]ntos?\s+especialistas|"
    r"informaci[oó]n\s+(de|sobre)\s+la\s+especialidad"
    r")\b"
)


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def is_specialty_detail_query(text: str) -> bool:
    return bool(_DETAIL_RE.search(_norm(text)) or find_specialty_in_text(text))


def format_all_specialties() -> str:
    lines = [
        f"La Liga Ama Salvar Vidas tiene {TOTAL_SPECIALISTS_LABEL} especialistas "
        f"en {SPECIALTY_AREAS_COUNT} áreas de atención médica.",
        "Listado completo con número de especialistas por área:",
    ]
    for item in SPECIALTY_CATALOG:
        lines.append(f"{item['nombre']}: {item['especialistas']} especialista(s).")
    lines.append(
        "Para agendar cita en cualquier especialidad, llama a citas médicas al +57 606 333 3340."
    )
    return sanitize_institution_name("\n\n".join(lines))


def format_specialty_detail(name: str) -> str:
    item = SPECIALTY_BY_NAME[name]
    n = int(item["especialistas"])
    desc = str(item["descripcion"])
    plural = "especialistas" if n != 1 else "especialista"
    return sanitize_institution_name(
        f"{name}: {desc}\n\n"
        f"En La Liga Ama Salvar Vidas hay {n} {plural} en esta área.\n\n"
        f"Citas médicas: +57 606 333 3340."
    )


def format_specialty_not_in_catalog(mentioned: str) -> str:
    lista = ", ".join(SPECIALTIES)
    return sanitize_institution_name(
        f"En el directorio oficial de La Liga Ama Salvar Vidas no aparece la especialidad "
        f"«{mentioned}» como una de las {SPECIALTY_AREAS_COUNT} áreas publicadas "
        f"({TOTAL_SPECIALISTS_LABEL} especialistas en total).\n\n"
        f"Las áreas disponibles son: {lista}.\n\n"
        f"Si buscas orientación sobre citas, llama al +57 606 333 3340."
    )


def answer_specialties(user_message: str) -> str:
    name = find_specialty_in_text(user_message)
    if name and is_known_specialty(name):
        if is_specialty_detail_query(user_message) or name:
            return format_specialty_detail(name)
    if name and not is_known_specialty(name):
        raw = _extract_mentioned_specialty(user_message)
        return format_specialty_not_in_catalog(raw or "esa especialidad")
    return format_all_specialties()


def _extract_mentioned_specialty(text: str) -> str | None:
    low = _norm(text)
    m = re.search(
        r"(oncolog[ií]a|cardiolog[ií]a|pediatr[ií]a|neurolog[ií]a|psiquiatr[ií]a)",
        low,
    )
    if m:
        return m.group(1).capitalize()
    return find_specialty_in_text(text)


def answer_specialty_topic(user_message: str) -> str | None:
    """Una especialidad concreta o aviso si no está en catálogo."""
    low = _norm(user_message)
    onc = re.search(r"\boncolog", low)
    if onc:
        return format_specialty_not_in_catalog("Oncología")

    name = find_specialty_in_text(user_message)
    if not name:
        return None
    if is_known_specialty(name):
        return format_specialty_detail(name)
    return format_specialty_not_in_catalog(name)
