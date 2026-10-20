"""Interpreta cualquier mensaje del usuario y responde solo con el catálogo."""

from __future__ import annotations

import logging
import re

from backend.brand import sanitize_institution_name
from collections.abc import Iterator

from backend.config import (
    GROUNDED_ANSWER_PROMPT,
    GROUNDED_ANSWER_TEMPERATURE,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TEXT_MODEL,
    OUT_OF_SCOPE_REPLY,
    VOICE_GROUNDED_NUM_PREDICT,
    VOICE_GROUNDED_PROMPT,
)
from backend.knowledge_context import build_knowledge_json
from backend.llm import chat, chat_stream

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
- Precios siempre en pesos colombianos (COP). No uses dólares ni USD. Ejemplo: 499.000 pesos colombianos.

KNOWLEDGE:
"""


def _system_content(*, for_voice: bool = False) -> str:
    extra = GROUNDED_ANSWER_PROMPT.strip()
    base = _DEFAULT_INSTRUCTIONS + build_knowledge_json()
    if extra:
        base = base + "\n\nInstrucciones adicionales:\n" + extra
    if for_voice:
        voice_extra = VOICE_GROUNDED_PROMPT.strip()
        if voice_extra:
            base = base + "\n\n" + voice_extra
    return base


def _catalog_messages(history: list[dict[str, str]], *, for_voice: bool = False) -> list[dict[str, str]]:
    return [{"role": "system", "content": _system_content(for_voice=for_voice)}, *history]


def _num_predict_for_voice(for_voice: bool) -> int:
    if for_voice:
        return min(OLLAMA_NUM_PREDICT, VOICE_GROUNDED_NUM_PREDICT)
    return min(OLLAMA_NUM_PREDICT, 640)


def answer_from_catalog(history: list[dict[str, str]], *, for_voice: bool = False) -> str:
    if not OLLAMA_TEXT_MODEL:
        raise RuntimeError("OLLAMA_TEXT_MODEL no configurado")
    if not history:
        raise ValueError("Historial vacío")

    messages = _catalog_messages(history, for_voice=for_voice)
    text = chat(
        messages,
        temperature=GROUNDED_ANSWER_TEMPERATURE,
        num_ctx=max(OLLAMA_NUM_CTX, 8192),
        num_predict=_num_predict_for_voice(for_voice),
    )
    text = sanitize_institution_name(text.strip())
    if not text:
        raise RuntimeError("Respuesta vacía del modelo")
    return text


def stream_answer_from_catalog(history: list[dict[str, str]], *, for_voice: bool = False) -> Iterator[str]:
    if not OLLAMA_TEXT_MODEL:
        raise RuntimeError("OLLAMA_TEXT_MODEL no configurado")
    if not history:
        raise ValueError("Historial vacío")
    messages = _catalog_messages(history, for_voice=for_voice)
    yield from chat_stream(
        messages,
        temperature=GROUNDED_ANSWER_TEMPERATURE,
        num_ctx=max(OLLAMA_NUM_CTX, 8192),
        num_predict=_num_predict_for_voice(for_voice),
    )


_GREETING_ONLY = re.compile(
    r"(?i)^\s*(hola|buenos?\s+d[ií]as|buenas?\s+tardes|buenas?\s+noches|"
    r"gracias|adi[oó]s|chao)\s*[.!?]*\s*$"
)


def is_short_greeting(text: str) -> bool:
    return bool(_GREETING_ONLY.match(text.strip()))
