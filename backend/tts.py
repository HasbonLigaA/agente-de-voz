from collections.abc import AsyncIterator

import edge_tts

from backend.config import TTS_RATE, TTS_VOICE
from backend.tts_prepare import prepare_text_for_speech


def _voice_and_text(text: str, voice: str | None) -> tuple[str, str]:
    voice = (voice or TTS_VOICE).strip()
    if not voice:
        raise RuntimeError("TTS_VOICE no configurado en .env")
    speak_text = prepare_text_for_speech(text)
    return voice, speak_text


async def iter_speech_audio(text: str, voice: str | None = None) -> AsyncIterator[bytes]:
    voice, speak_text = _voice_and_text(text, voice)
    communicate = edge_tts.Communicate(speak_text, voice, rate=TTS_RATE)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]


async def synthesize_speech(text: str, voice: str | None = None) -> bytes:
    chunks: list[bytes] = []
    async for part in iter_speech_audio(text, voice=voice):
        chunks.append(part)
    return b"".join(chunks)
