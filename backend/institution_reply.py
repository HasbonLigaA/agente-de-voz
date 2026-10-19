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
        return sanitize_institution_name(
            f"Misión de {name}: {INSTITUTION['mision']}"
        )

    if re.search(r"\b(vision)\b", low):
        return sanitize_institution_name(
            f"Visión de {name}: {INSTITUTION['vision']}"
        )

    if re.search(r"\b(valores?)\b", low):
        partes = [f"{k}: {v}" for k, v in INSTITUTION["valores"].items()]
        return sanitize_institution_name(
            f"Valores de {name}: " + "; ".join(partes) + "."
        )

    if re.search(r"\b(historia)\b", low):
        return sanitize_institution_name(
            f"Historia de {name}: {INSTITUTION['historia_resumen']}"
        )

    if re.search(r"\b(politica\s+de\s+calidad|calidad)\b", low):
        return sanitize_institution_name(
            f"Política de calidad de {name}: {INSTITUTION['politica_calidad_resumen']}"
        )

    # Quiénes somos / qué hace (general)
    return sanitize_institution_name(
        f"{name} es una {INSTITUTION['tipo']} con sede en {INSTITUTION['sede']}.\n\n"
        f"{INSTITUTION['historia_resumen']}\n\n"
        f"Qué hace: {INSTITUTION['que_hace']}\n\n"
        f"Misión: {INSTITUTION['mision']}\n\n"
        f"Visión: {INSTITUTION['vision']}"
    )
