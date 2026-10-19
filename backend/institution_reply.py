"""Respuestas sobre La Liga Ama Salvar Vidas (datos de nuestra-institucion)."""

from __future__ import annotations

import re
import unicodedata

from backend.brand import sanitize_institution_name
from backend.knowledge.institution import INSTITUTION


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def answer_institution(user_message: str) -> str:
    low = _norm(user_message)
    name = INSTITUTION["nombre"]

    if re.search(r"\b(mision)\b", low):
        return sanitize_institution_name(f"Misión de {name}: {INSTITUTION['mision_voz']}")

    if re.search(r"\b(vision)\b", low):
        return sanitize_institution_name(f"Visión de {name}: {INSTITUTION['vision_voz']}")

    if re.search(r"\b(valores?)\b", low):
        return sanitize_institution_name(
            f"Valores de {name}: {INSTITUTION['valores_voz']}."
        )

    if re.search(r"\b(historia)\b", low):
        return sanitize_institution_name(f"{INSTITUTION['historia_voz']}")

    if re.search(
        r"\b(para\s+que\s+sirve|para\s+que\s+sirven|a\s+que\s+se\s+dedican)\b", low
    ):
        return sanitize_institution_name(INSTITUTION["para_que_sirve_voz"])

    if re.search(r"\b(que\s+hacen|que\s+hace|de\s+que\s+se\s+trata)\b", low):
        return sanitize_institution_name(INSTITUTION["pitch_voz"])

    return sanitize_institution_name(INSTITUTION["pitch_voz"])
