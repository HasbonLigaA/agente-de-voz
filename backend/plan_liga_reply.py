"""Respuestas sobre Plan Liga (plantilla rápida; LLM opcional)."""

from __future__ import annotations

import re
import unicodedata

from backend.knowledge.plan_liga import PLAN_LIGA
from backend.reply_format import bullet_list, finish_blocks, numbered_list


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def format_plan_liga(user_message: str) -> str:
    low = _norm(user_message)
    nombre = PLAN_LIGA["nombre"]
    blocks: list[str] = []

    if re.search(
        r"beneficio|beneficios|que trae|incluye|ventaja|para\s+que\s+sirve|que\s+ofrece",
        low,
    ):
        blocks.append(
            f"El {nombre} es una membresía anual de salud de La Liga Ama Salvar Vidas.\n"
            f"{PLAN_LIGA['resumen']}"
        )
        blocks.append("Beneficios exclusivos:\n" + bullet_list(PLAN_LIGA["beneficios"]))
        blocks.append(
            f"Precio: {PLAN_LIGA['precio_anual_texto']}.\n"
            f"Usuarios: {PLAN_LIGA['beneficiarios']}."
        )
        blocks.append(
            f"Para activar, envía tu comprobante de pago al WhatsApp "
            f"{PLAN_LIGA['contacto']['whatsapp_activacion']}."
        )

    elif re.search(r"precio|cuesta|vale|cobran|499|cuanto\s+es", low):
        blocks.append(f"El {nombre} cuesta {PLAN_LIGA['precio_anual_texto']}.")
        blocks.append(f"Usuarios incluidos: {PLAN_LIGA['beneficiarios']}.")
        blocks.append("Beneficios:\n" + bullet_list(PLAN_LIGA["beneficios"]))
        blocks.append(
            f"Activación: envía comprobante al WhatsApp "
            f"{PLAN_LIGA['contacto']['whatsapp_activacion']}."
        )

    elif re.search(r"activar|comprobante|pago|afili|como\s+compro|comprar", low):
        blocks.append(f"Pasos para activar el {nombre}:")
        blocks.append(numbered_list(PLAN_LIGA["activacion_pasos"]))
        blocks.append(
            f"Citas médicas: {PLAN_LIGA['contacto']['citas_medicas']}.\n"
            f"Dudas comerciales: WhatsApp {PLAN_LIGA['contacto']['whatsapp_comercial']} o "
            f"{PLAN_LIGA['contacto']['correo_comercial']}."
        )

    elif re.search(r"tarifa|consulta\s+desde|subespecialidad|resonancia|laboratorio", low):
        blocks.append(f"Tarifas de referencia del {nombre} (sobre tarifa ordinaria):")
        blocks.append(bullet_list(PLAN_LIGA["tarifas_referencia"]))
        blocks.append(
            "Incluye todo el portafolio de servicios de La Liga con tarifa diferencial.\n"
            f"Membresía: {PLAN_LIGA['precio_anual_texto']}."
        )

    elif re.search(r"quien\s+puede|requisito|edad|consanguinidad|titular", low):
        blocks.append(f"¿Quiénes pueden adquirir el {nombre}?")
        blocks.append(f"• {PLAN_LIGA['quien_puede']}.")
        blocks.append(f"• {PLAN_LIGA['beneficiarios']}.")
        blocks.append("Beneficios:\n" + bullet_list(PLAN_LIGA["beneficios"]))

    elif re.search(r"que\s+es|que\s+es\s+el|informacion|info|cuentame|explicame", low):
        blocks.append(f"¿Qué es el {nombre}?")
        blocks.append(PLAN_LIGA["resumen"])
        blocks.append("Beneficios:\n" + bullet_list(PLAN_LIGA["beneficios"]))
        blocks.append(
            f"Precio: {PLAN_LIGA['precio_anual_texto']}.\n"
            f"Usuarios: {PLAN_LIGA['beneficiarios']}."
        )

    else:
        blocks.append(f"{nombre}")
        blocks.append(PLAN_LIGA["resumen"])
        blocks.append("Beneficios:\n" + bullet_list(PLAN_LIGA["beneficios"]))
        blocks.append(
            f"Precio: {PLAN_LIGA['precio_anual_texto']}.\n"
            f"Usuarios: {PLAN_LIGA['beneficiarios']}.\n"
            f"Activación: WhatsApp {PLAN_LIGA['contacto']['whatsapp_activacion']}."
        )

    return finish_blocks(blocks)


def answer_plan_liga(user_message: str) -> str:
    return format_plan_liga(user_message)
