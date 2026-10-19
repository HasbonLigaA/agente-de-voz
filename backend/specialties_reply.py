"""Respuestas de especialidades (solo catálogo autorizado)."""

from __future__ import annotations

import re
import unicodedata

from backend.knowledge.specialties import (
    SPECIALTY_AREAS_COUNT,
    SPECIALTY_BY_NAME,
    SPECIALTY_CATALOG,
    SPECIALTIES,
    TOTAL_SPECIALISTS_LABEL,
    find_specialty_in_text,
    is_known_specialty,
)
from backend.reply_format import bullet_list, finish_blocks

_DETAIL_RE = re.compile(
    r"(?i)\b("
    r"para\s+que\s+sirve|que\s+es|qu[eé]\s+es|"
    r"hablame\s+de|cu[eé]ntame\s+sobre|explicame|"
    r"cu[aá]ntos?\s+especialistas|"
    r"informaci[oó]n\s+(de|sobre)\s+la\s+especialidad"
    r")\b"
)

_EXPLAIN_ALL_RE = re.compile(
    r"(?i)\b("
    r"explic(a|ame|ar)|descr(i|í)(be|beme|pcion)|detall(e|ada)|"
    r"para\s+que\s+sirve\s+cada|hablame\s+de\s+(las\s+)?todas"
    r")\b"
)


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def is_specialty_detail_query(text: str) -> bool:
    return bool(_DETAIL_RE.search(_norm(text)) or find_specialty_in_text(text))


def _specialty_line(item: dict[str, str | int], *, with_description: bool) -> str:
    name = str(item["nombre"])
    count = int(item["especialistas"])
    if not with_description:
        return f"{name} ({count} especialista{'s' if count != 1 else ''})"
    desc = str(item["descripcion"])
    return f"{name} ({count}): {desc}"


def format_all_specialties(*, with_descriptions: bool = False) -> str:
    lines = [
        _specialty_line(item, with_description=with_descriptions)
        for item in SPECIALTY_CATALOG
    ]
    title = (
        f"La Liga Ama Salvar Vidas tiene {TOTAL_SPECIALISTS_LABEL} especialistas "
        f"en {SPECIALTY_AREAS_COUNT} áreas:"
    )
    if with_descriptions:
        title = f"Especialidades de La Liga Ama Salvar Vidas ({SPECIALTY_AREAS_COUNT} áreas):"
    return finish_blocks(
        [
            title,
            bullet_list(lines),
            "Citas médicas: +57 606 333 3340.",
        ]
    )


def format_specialty_detail(name: str) -> str:
    item = SPECIALTY_BY_NAME[name]
    n = int(item["especialistas"])
    desc = str(item["descripcion"])
    plural = "especialistas" if n != 1 else "especialista"
    return finish_blocks(
        [
            name,
            f"Descripción: {desc}",
            f"En La Liga Ama Salvar Vidas hay {n} {plural} en esta área.",
            "Citas médicas: +57 606 333 3340.",
        ]
    )


def format_specialty_not_in_catalog(mentioned: str) -> str:
    areas = [
        f"{name} ({SPECIALTY_BY_NAME[name]['especialistas']})"
        for name in SPECIALTIES
    ]
    return finish_blocks(
        [
            f"En el directorio oficial de La Liga Ama Salvar Vidas no aparece "
            f"«{mentioned}» entre las {SPECIALTY_AREAS_COUNT} áreas publicadas "
            f"({TOTAL_SPECIALISTS_LABEL} especialistas en total).",
            "Áreas disponibles:\n" + bullet_list(areas),
            "Para orientación sobre citas: +57 606 333 3340.",
        ]
    )


def answer_specialties(user_message: str) -> str:
    low = _norm(user_message)
    explain_all = bool(_EXPLAIN_ALL_RE.search(low))

    name = find_specialty_in_text(user_message)
    if name and is_known_specialty(name):
        if is_specialty_detail_query(user_message) or name:
            return format_specialty_detail(name)
    if name and not is_known_specialty(name):
        raw = _extract_mentioned_specialty(user_message)
        return format_specialty_not_in_catalog(raw or "esa especialidad")
    return format_all_specialties(with_descriptions=explain_all)


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
