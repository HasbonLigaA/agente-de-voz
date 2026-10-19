"""Corrige transcripciones de voz antes del chat (Ollama)."""

from __future__ import annotations

import logging
import re

from backend.config import (
    STT_POLISH_NUM_CTX,
    STT_POLISH_PROMPT,
    STT_POLISH_TEMPERATURE,
    STT_POLISH_WITH_LLM,
)
from backend.llm import chat

logger = logging.getLogger(__name__)


def polish_transcript(raw: str) -> str:
    raw = raw.strip()
    prompt = STT_POLISH_PROMPT.strip()
    if not raw or not STT_POLISH_WITH_LLM or not prompt:
        return raw
    try:
        fixed = chat(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Transcripción cruda:\n{raw}"},
            ],
            temperature=STT_POLISH_TEMPERATURE,
            num_ctx=STT_POLISH_NUM_CTX,
        )
        fixed = re.sub(r"\s+", " ", fixed).strip().strip('"').strip("'")
        if len(fixed) < 3:
            return raw
        logger.info("STT polish: %r → %r", raw[:80], fixed[:80])
        return fixed
    except Exception as exc:
        logger.warning("No se pudo pulir transcripción (%s).", exc)
        return raw
