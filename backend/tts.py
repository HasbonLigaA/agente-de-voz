import edge_tts

from backend.config import TTS_VOICE
from backend.tts_prepare import prepare_text_for_speech


async def synthesize_speech(text: str, voice: str | None = None) -> bytes:
    voice = (voice or TTS_VOICE).strip()
    if not voice:
        raise RuntimeError("TTS_VOICE no configurado en .env")
    speak_text = prepare_text_for_speech(text)
    communicate = edge_tts.Communicate(speak_text, voice, rate="+8%")
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)
