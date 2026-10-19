"""Respuestas sobre Plan Liga (plantillas desde catálogo)."""

from __future__ import annotations

from backend.knowledge.plan_liga import PLAN_LIGA
from backend.reply_format import bullet_list, finish_blocks, numbered_list

_ASPECTS = frozenset(
    {"benefits", "price", "activation", "tariffs", "eligibility", "general"}
)


def _blocks_for_aspect(aspect: str) -> list[str]:
    nombre = PLAN_LIGA["nombre"]
    aspect = aspect if aspect in _ASPECTS else "general"

    if aspect == "benefits":
        return [
            f"El {nombre} es una membresía anual de salud de La Liga Ama Salvar Vidas.\n"
            f"{PLAN_LIGA['resumen']}",
            "Beneficios exclusivos:\n" + bullet_list(PLAN_LIGA["beneficios"]),
            f"Precio: {PLAN_LIGA['precio_anual_texto']}.\nUsuarios: {PLAN_LIGA['beneficiarios']}.",
            f"Activación: WhatsApp {PLAN_LIGA['contacto']['whatsapp_activacion']}.",
        ]

    if aspect == "price":
        return [
            f"El {nombre} cuesta {PLAN_LIGA['precio_anual_texto']}.",
            f"Usuarios incluidos: {PLAN_LIGA['beneficiarios']}.",
            "Beneficios:\n" + bullet_list(PLAN_LIGA["beneficios"]),
            f"Activación: WhatsApp {PLAN_LIGA['contacto']['whatsapp_activacion']}.",
        ]

    if aspect == "activation":
        return [
            f"Pasos para activar el {nombre}:",
            numbered_list(PLAN_LIGA["activacion_pasos"]),
            f"Citas médicas: {PLAN_LIGA['contacto']['citas_medicas']}.\n"
            f"Dudas comerciales: WhatsApp {PLAN_LIGA['contacto']['whatsapp_comercial']} o "
            f"{PLAN_LIGA['contacto']['correo_comercial']}.",
        ]

    if aspect == "tariffs":
        return [
            f"Tarifas de referencia del {nombre} (sobre tarifa ordinaria):",
            bullet_list(PLAN_LIGA["tarifas_referencia"]),
            "Incluye todo el portafolio de servicios de La Liga con tarifa diferencial.\n"
            f"Membresía: {PLAN_LIGA['precio_anual_texto']}.",
        ]

    if aspect == "eligibility":
        return [
            f"¿Quiénes pueden adquirir el {nombre}?",
            f"• {PLAN_LIGA['quien_puede']}.",
            f"• {PLAN_LIGA['beneficiarios']}.",
            "Beneficios:\n" + bullet_list(PLAN_LIGA["beneficios"]),
        ]

    return [
        f"¿Qué es el {nombre}?",
        PLAN_LIGA["resumen"],
        "Beneficios:\n" + bullet_list(PLAN_LIGA["beneficios"]),
        f"Precio: {PLAN_LIGA['precio_anual_texto']}.\nUsuarios: {PLAN_LIGA['beneficiarios']}.",
        f"Activación: WhatsApp {PLAN_LIGA['contacto']['whatsapp_activacion']}.",
    ]


def format_plan_liga(_user_message: str, aspect: str | None = None) -> str:
    normalized = (aspect or "general").lower().strip()
    return finish_blocks(_blocks_for_aspect(normalized))


def answer_plan_liga(user_message: str, aspect: str | None = None) -> str:
    return format_plan_liga(user_message, aspect=aspect)
