"""Datos oficiales del Plan Liga (membresía de salud).

Fuente: https://laligaamasalvarvidas.org.co/contenido/membresia-plan-liga/215
"""

from __future__ import annotations

PLAN_LIGA_SOURCE_URL = (
    "https://laligaamasalvarvidas.org.co/contenido/membresia-plan-liga/215"
)

PLAN_LIGA: dict = {
    "nombre": "Plan Liga Ama Salvar Vidas",
    "organizacion": "La Liga Ama Salvar Vidas (Pereira, Risaralda, Colombia)",
    "tipo": "Membresía anual de salud (NO es streaming, fútbol ni entretenimiento)",
    "resumen": (
        "Membresía anual con acceso preferencial al portafolio de servicios de La Liga, "
        "tarifas preferenciales y atención oportuna en salud."
    ),
    "precio_anual_cop": 499_000,
    "precio_anual_texto": "$499.000 COP al año (pago único, sin cuotas de manejo)",
    "beneficiarios": "1 titular + 4 beneficiarios (hasta 5 usuarios), sin exigencia de grado de consanguinidad",
    "beneficios": [
        "Tarifas preferenciales en consultas, exámenes y procedimientos",
        "Hasta 5 usuarios: 1 titular y 4 beneficiarios",
        "Prioridad en programación de citas y servicios diagnósticos",
        "Acceso al portafolio integral de servicios de La Liga",
    ],
    "activacion_pasos": [
        "Realizar el pago en línea o presencial",
        "Enviar comprobante al WhatsApp 310 575 8450 para activar titular y beneficiarios",
        "Solicitar cita inicial y usar los beneficios (tarjeta física opcional en caja principal)",
    ],
    "quien_puede": "Personas de cualquier edad, sin restricciones médicas para afiliarse",
    "tarifas_referencia": [
        "Consulta especializada desde $89.900",
        "Subespecialidades (neurocirugía, oncología, etc.) desde $129.900 a $144.900",
        "Resonancia, rayos X, TAC, laboratorio, mamografía, ecografía y demás servicios con tarifa diferencial",
    ],
    "contacto": {
        "citas_medicas": "+57 606 333 3340",
        "whatsapp_comercial": "310 203 1639",
        "whatsapp_activacion": "310 575 8450",
        "correo_comercial": "ejecutiva.comercial@laliga.org.co",
        "direccion": "Carrera 4 # 23-55, Pereira, Risaralda",
    },
}
