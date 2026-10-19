"""Respuestas sobre La Liga Ama Salvar Vidas (datos de nuestra-institucion)."""

from __future__ import annotations

from backend.knowledge.institution import INSTITUTION
from backend.reply_format import bullet_list, finish_blocks, labeled_bullets

_ASPECTS = frozenset({"mission", "vision", "values", "history", "purpose", "general"})


def answer_institution(_user_message: str, aspect: str | None = None) -> str:
    name = INSTITUTION["nombre"]
    key = (aspect or "general").lower().strip()
    if key not in _ASPECTS:
        key = "general"

    if key == "mission":
        return finish_blocks([f"Misión de {name}", INSTITUTION["mision_voz"]])

    if key == "vision":
        return finish_blocks([f"Visión de {name}", INSTITUTION["vision_voz"]])

    if key == "values":
        pairs = [(k, v) for k, v in INSTITUTION["valores"].items()]
        return finish_blocks([f"Valores de {name}", labeled_bullets(pairs)])

    if key == "history":
        return finish_blocks([f"Historia de {name}", INSTITUTION["historia_voz"]])

    if key == "purpose":
        return finish_blocks(
            [
                f"¿Para qué sirve {name}?",
                INSTITUTION["para_que_sirve_voz"],
            ]
        )

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
            f"Sede: {INSTITUTION['sede']}.",
        ]
    )
