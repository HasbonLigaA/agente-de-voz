"""Contacto institucional (solo datos del catálogo)."""

from __future__ import annotations

from backend.knowledge.institution import CONTACTO
from backend.reply_format import bullet_list, finish_blocks


def answer_contact() -> str:
    c = CONTACTO
    lines = [
        f"{c['nombre_institucion']} — {c['ciudad']}",
        f"Dirección: {c['direccion']}",
        f"PBX administrativo: {c['pbx_administrativo']}",
        f"Citas médicas: {c['citas_medicas']} — {c['correo_citas']}",
        f"WhatsApp comercial: {c['whatsapp_comercial']}",
        f"WhatsApp activación Plan Liga: {c['whatsapp_activacion']}",
        f"Correo comercial: {c['correo_comercial']}",
        f"Notificaciones judiciales: {c['notificaciones_judiciales']}",
    ]
    return finish_blocks(
        [
            "Contacto de La Liga Ama Salvar Vidas",
            bullet_list(lines),
        ]
    )
