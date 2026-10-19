"""Respuestas sobre La Liga Ama Salvar Vidas (datos de nuestra-institucion)."""

from __future__ import annotations

import re
import unicodedata

from backend.knowledge.institution import INSTITUTION
from backend.reply_format import bullet_list, finish_blocks, labeled_bullets


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def answer_institution(user_message: str) -> str:
    low = _norm(user_message)
    name = INSTITUTION["nombre"]

    if re.search(r"\b(mision)\b", low):
        return finish_blocks(
            [
                f"Misión de {name}",
                INSTITUTION["mision_voz"],
            ]
        )

    if re.search(r"\b(vision)\b", low):
        return finish_blocks(
            [
                f"Visión de {name}",
                INSTITUTION["vision_voz"],
            ]
        )

    if re.search(r"\b(valores?)\b", low):
        pairs = [(k, v) for k, v in INSTITUTION["valores"].items()]
        return finish_blocks(
            [
                f"Valores de {name}",
                labeled_bullets(pairs),
            ]
        )

    if re.search(r"\b(historia)\b", low):
        return finish_blocks(
            [
                f"Historia de {name}",
                INSTITUTION["historia_voz"],
            ]
        )

    if re.search(
        r"\b(para\s+que\s+sirve|para\s+que\s+sirven|a\s+que\s+se\s+dedican)\b", low
    ):
        return finish_blocks(
            [
                f"¿Para qué sirve {name}?",
                INSTITUTION["para_que_sirve_voz"],
            ]
        )

    if re.search(r"\b(que\s+hacen|que\s+hace|de\s+que\s+se\s+trata)\b", low):
        return finish_blocks(
            [
                name,
                INSTITUTION["pitch_voz"],
                "Servicios principales:\n"
                + bullet_list(
                    [
                        "Diagnóstico y tratamiento con enfoque integral",
                        "Prevención y acompañamiento a pacientes y familias",
                        "Voluntariado, tecnología y responsabilidad social",
                    ]
                ),
            ]
        )

    return finish_blocks(
        [
            name,
            INSTITUTION["pitch_voz"],
            f"Sede: {INSTITUTION['sede']}.",
        ]
    )
