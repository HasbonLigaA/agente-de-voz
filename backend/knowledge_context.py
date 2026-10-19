"""Catálogo completo serializado para respuestas ancladas al conocimiento."""

from __future__ import annotations

import json

from backend.knowledge.institution import CONTACTO, INSTITUTION, INSTITUTION_SOURCE_URL
from backend.knowledge.plan_liga import PLAN_LIGA, PLAN_LIGA_SOURCE_URL
from backend.knowledge.specialties import (
    SPECIALISTS_SOURCE_URL,
    SPECIALTY_AREAS_COUNT,
    SPECIALTY_CATALOG,
    TOTAL_SPECIALISTS_LABEL,
)


def build_knowledge_json() -> str:
    payload = {
        "institucion": INSTITUTION,
        "plan_liga": PLAN_LIGA,
        "especialidades": {
            "total_especialistas_etiqueta": TOTAL_SPECIALISTS_LABEL,
            "numero_areas": SPECIALTY_AREAS_COUNT,
            "catalogo": list(SPECIALTY_CATALOG),
            "nota": (
                "Solo existen estas áreas en el directorio publicado. "
                "Oncología u otras no listadas no deben inventarse."
            ),
        },
        "contacto": CONTACTO,
        "fuentes_oficiales": {
            "institucion": INSTITUTION_SOURCE_URL,
            "plan_liga": PLAN_LIGA_SOURCE_URL,
            "especialistas": SPECIALISTS_SOURCE_URL,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
