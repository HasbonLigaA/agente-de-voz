"""Contacto institucional (solo datos del catálogo)."""

from __future__ import annotations

from backend.brand import sanitize_institution_name
from backend.knowledge.institution import CONTACTO


def answer_contact() -> str:
    c = CONTACTO
    return sanitize_institution_name(
        f"{c['nombre_institucion']}, {c['ciudad']}. "
        f"Dirección: {c['direccion']}. "
        f"PBX administrativo: {c['pbx_administrativo']}. "
        f"Citas médicas: {c['citas_medicas']} — {c['correo_citas']}. "
        f"WhatsApp comercial: {c['whatsapp_comercial']}. "
        f"WhatsApp activación Plan Liga: {c['whatsapp_activacion']}. "
        f"Correo comercial: {c['correo_comercial']}. "
        f"Notificaciones judiciales: {c['notificaciones_judiciales']}."
    )
