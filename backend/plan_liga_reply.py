"""Respuestas sobre Plan Liga (plantilla rápida; LLM opcional)."""

from __future__ import annotations

import re
import unicodedata

from backend.brand import sanitize_institution_name
from backend.knowledge.plan_liga import PLAN_LIGA


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def format_plan_liga(user_message: str) -> str:
    low = _norm(user_message)
    org = PLAN_LIGA["organizacion"]
    lines: list[str] = []

    if re.search(r"beneficio|que trae|incluye|ventaja", low):
        lines.append(
            f"El {PLAN_LIGA['nombre']} de {org} es una membresía anual de salud. "
            f"{PLAN_LIGA['resumen']}"
        )
        ben = "; ".join(PLAN_LIGA["beneficios"])
        lines.append(f"Beneficios principales: {ben}.")
        lines.append(f"Inversión: {PLAN_LIGA['precio_anual_texto']}. {PLAN_LIGA['beneficiarios']}.")
    elif re.search(r"precio|cuesta|vale|cobran|499", low):
        lines.append(
            f"El {PLAN_LIGA['nombre']} cuesta {PLAN_LIGA['precio_anual_texto']}. "
            f"Incluye {PLAN_LIGA['beneficiarios']}."
        )
        lines.append(f"{PLAN_LIGA['resumen']}")
    elif re.search(r"activar|comprobante|pago|afili", low):
        pasos = PLAN_LIGA["activacion_pasos"]
        lines.append(f"Para activar el {PLAN_LIGA['nombre']}:")
        lines.append(f"1) {pasos[0]}. 2) {pasos[1]}. 3) {pasos[2]}.")
        lines.append(f"Citas médicas: {PLAN_LIGA['contacto']['citas_medicas']}.")
    else:
        lines.append(f"{PLAN_LIGA['nombre']}: {PLAN_LIGA['resumen']}")
        lines.append(f"Precio: {PLAN_LIGA['precio_anual_texto']}. {PLAN_LIGA['beneficiarios']}.")
        lines.append(
            "Beneficios: tarifas preferenciales, prioridad en citas y acceso al portafolio de servicios de La Liga."
        )

    lines.append(f"WhatsApp activación: {PLAN_LIGA['contacto']['whatsapp_activacion']}.")
    return sanitize_institution_name("\n\n".join(lines))


def answer_plan_liga(user_message: str) -> str:
    # Siempre plantilla desde PLAN_LIGA; no usar conocimiento externo del modelo.
    return format_plan_liga(user_message)
