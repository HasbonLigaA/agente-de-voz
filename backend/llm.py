from __future__ import annotations

from typing import Any

import ollama

from backend.brand import sanitize_institution_name
from backend.config import (
    AGENT_SYSTEM_PROMPT,
    OLLAMA_HOST,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TEMPERATURE,
    OLLAMA_TEXT_MODEL,
    OLLAMA_TIMEOUT,
)


def chat(
    messages: list[dict[str, str]],
    model: str | None = None,
    *,
    temperature: float | None = None,
    num_ctx: int | None = None,
    num_predict: int | None = None,
) -> str:
    """Envía historial de conversación a Ollama y devuelve el texto del asistente."""
    chat_model = model or OLLAMA_TEXT_MODEL
    if not chat_model:
        raise RuntimeError("OLLAMA_TEXT_MODEL no configurado en .env")
    payload: dict[str, Any] = {
        "model": chat_model,
        "messages": messages,
        "options": {
            "temperature": OLLAMA_TEMPERATURE if temperature is None else temperature,
            "num_ctx": OLLAMA_NUM_CTX if num_ctx is None else num_ctx,
            "num_predict": OLLAMA_NUM_PREDICT if num_predict is None else num_predict,
        },
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }
    try:
        client = ollama.Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)
        response = client.chat(**payload)
    except TypeError:
        response = ollama.chat(**payload)
    text = (response.get("message") or {}).get("content", "").strip()
    return sanitize_institution_name(text)


def build_messages(history: list[dict[str, str]]) -> list[dict[str, str]]:
    system = sanitize_institution_name(AGENT_SYSTEM_PROMPT.strip())
    if not system:
        return list(history)
    return [{"role": "system", "content": system}, *history]
