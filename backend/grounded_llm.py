"""Interpreta cualquier mensaje del usuario y responde solo con el catálogo."""

from __future__ import annotations

import logging
import re

from backend.brand import sanitize_institution_name
from backend.config import (
    GROUNDED_ANSWER_PROMPT,
    GROUNDED_ANSWER_TEMPERATURE,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TEXT_MODEL,
    OUT_OF_SCOPE_REPLY,
)
from backend.knowledge_context import build_knowledge_json
from backend.llm import chat

logger = logging.getLogger(__name__)

_DEFAULT_INSTRUCTIONS = """Eres el asistente virtual de La Liga Ama Salvar Vidas (Pereira, Colombia).

Debajo está KNOWLEDGE: la única fuente de verdad. No uses internet ni conocimiento general.

Tu trabajo:
1. Leer el mensaje actual y el historial.
2. Entender qué necesita la persona aunque escriba mal, hable coloquial, deje frases a medias,
   use sinónimos o no sepa qué término usar.
3. Responder en español claro con los datos exactos que apliquen del KNOWLEDGE.

Reglas obligatorias:
- No inventes cifras, teléfonos, especialidades, beneficios ni pasos que no estén en KNOWLEDGE.
- Plan Liga = membresía de SALUD anual; no es fútbol ni entretenimiento.
- Si la consulta no puede responderse con KNOWLEDGE, responde EXACTAMENTE (sin añadir nada):
""" + OUT_OF_SCOPE_REPLY.strip() + """
- Si listas varios puntos (beneficios, especialidades, valores, pasos), usa viñetas «•» y líneas
  separadas; evita un solo bloque de texto.
- En seguimientos («¿y eso?», «¿cuánto?», «más info»), usa el historial para saber el tema.
- Nombre correcto: La Liga Ama Salvar Vidas.

KNOWLEDGE:
"""


def _system_content() -> str:
    extra = GROUNDED_ANSWER_PROMPT.strip()
    base = _DEFAULT_INSTRUCTIONS + build_knowledge_json()
    if extra:
        return base + "\n\nInstrucciones adicionales:\n" + extra
    return base


def answer_from_catalog(history: list[dict[str, str]]) -> str:
    if not OLLAMA_TEXT_MODEL:
        raise RuntimeError("OLLAMA_TEXT_MODEL no configurado")
    if not history:
        raise ValueError("Historial vacío")

    messages = [{"role": "system", "content": _system_content()}, *history]
    text = chat(
        messages,
        temperature=GROUNDED_ANSWER_TEMPERATURE,
        num_ctx=max(OLLAMA_NUM_CTX, 8192),
        num_predict=min(OLLAMA_NUM_PREDICT, 640),
    )
    text = sanitize_institution_name(text.strip())
    if not text:
        raise RuntimeError("Respuesta vacía del modelo")
    return text


_GREETING_ONLY = re.compile(
    r"(?i)^\s*(hola|buenos?\s+d[ií]as|buenas?\s+tardes|buenas?\s+noches|"
    r"gracias|adi[oó]s|chao)\s*[.!?]*\s*$"
)


def is_short_greeting(text: str) -> bool:
    return bool(_GREETING_ONLY.match(text.strip()))
