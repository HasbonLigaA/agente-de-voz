"""Respuestas sobre Plan Liga usando datos autorizados + Ollama (sin inventar)."""

from __future__ import annotations

from backend.knowledge import plan_liga_context_json
from backend.knowledge.plan_liga import PLAN_LIGA
from backend.llm import chat

_PLAN_LIGA_SYSTEM = """Eres el asistente de voz de La Liga Ama Salvar Vidas (fundación de salud/oncología en Pereira, Colombia).
El usuario pregunta por el PLAN LIGA: membresía anual de SALUD, NO tiene relación con fútbol, LaLiga deportiva ni streaming.

Usa ÚNICAMENTE el JSON "datos_autorizados". No inventes precios, beneficios ni servicios.
Si algo no está en los datos, di que no tienes ese detalle y ofrece contacto de citas o WhatsApp del JSON.

Formato para voz (texto plano):
- Frases cortas, 2–4 bloques separados por línea en blanco.
- Sin markdown, sin viñetas con guiones.
- Español colombiano, tono cálido y claro."""


def _fallback_template() -> str:
    b = PLAN_LIGA["beneficios"]
    pasos = PLAN_LIGA["activacion_pasos"]
    return (
        f"{PLAN_LIGA['nombre']}: {PLAN_LIGA['resumen']}\n\n"
        f"Precio: {PLAN_LIGA['precio_anual_texto']}. "
        f"Cobertura de usuarios: {PLAN_LIGA['beneficiarios']}.\n\n"
        f"Beneficios: {b[0]}; {b[2]}; acceso al portafolio de servicios de La Liga.\n\n"
        f"Para activar: 1) {pasos[0]}. 2) {pasos[1]}. 3) {pasos[2]}.\n\n"
        f"Citas médicas: {PLAN_LIGA['contacto']['citas_medicas']}."
    )


def answer_plan_liga(user_message: str) -> str:
    data = plan_liga_context_json()
    try:
        reply = chat(
            [
                {"role": "system", "content": _PLAN_LIGA_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"datos_autorizados:\n{data}\n\n"
                        f"Pregunta del usuario:\n{user_message.strip()}\n\n"
                        "Responde en español para ser leída en voz alta."
                    ),
                },
            ],
            temperature=0.25,
            num_ctx=4096,
        )
        if reply and len(reply) > 20:
            return reply
    except Exception:
        pass
    return _fallback_template()
