import edge_tts

from backend.config import TTS_VOICE


async def synthesize_speech(text: str, voice: str | None = None) -> bytes:
    voice = (voice or TTS_VOICE).strip()
    if not voice:
        raise RuntimeError("TTS_VOICE no configurado en .env")
    communicate = edge_tts.Communicate(text, voice)
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)
