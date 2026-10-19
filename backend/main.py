from __future__ import annotations

import asyncio
import base64
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import (
    CORS_ALLOW_ORIGINS,
    OLLAMA_HOST,
    OLLAMA_TEXT_MODEL,
    PORT,
    public_https_url,
    STATIC_DIR,
    STT_ENGINE,
    TRAEFIK_HOST,
    TTS_VOICE,
    WELCOME_MESSAGE,
    WHISPER_MODEL_SIZE,
)
from backend.llm import build_messages, chat
from backend.sessions import create_session, get_session
from backend.stt import stt_available, transcribe_audio_bytes
from backend.voice_polish import polish_transcript
from backend.tts import synthesize_speech

app = FastAPI(title="Agente de voz", version="0.1.0")

# Permite probar desde otro dispositivo (celular en la misma red o tunel HTTPS).
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply_text: str
    audio_base64: str
    audio_mime: str = "audio/mpeg"


class SessionResponse(BaseModel):
    session_id: str


class TranscribeResponse(BaseModel):
    text: str
    raw_text: str | None = None


async def _reply_with_voice(text: str) -> str:
    audio_bytes = await synthesize_speech(text)
    return base64.b64encode(audio_bytes).decode("ascii")


def _lan_urls(port: int | None = None) -> list[str]:
    if port is None:
        port = PORT
    import socket

    skip = ("127.", "169.254.", "192.168.56.", "192.168.122.")
    urls = [f"http://127.0.0.1:{port}"]
    seen: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if any(ip.startswith(p) for p in skip) or ip in seen:
                continue
            seen.add(ip)
            urls.append(f"http://{ip}:{port}")
    except OSError:
        pass
    if len(urls) == 1:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if not any(ip.startswith(p) for p in skip):
                    urls.append(f"http://{ip}:{port}")
        except OSError:
            pass
    return urls


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "app_port": PORT,
        "ollama_host": OLLAMA_HOST,
        "ollama_model": OLLAMA_TEXT_MODEL,
        "tts_voice": TTS_VOICE,
        "stt_available": stt_available(),
        "stt_engine": STT_ENGINE,
        "whisper_model": WHISPER_MODEL_SIZE,
        "lan_urls": _lan_urls(PORT),
        "public_https_url": public_https_url() or None,
        "traefik_host": TRAEFIK_HOST or None,
        "mic_requires_https": True,
    }


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def api_transcribe(audio: UploadFile = File(...)):
    if not stt_available():
        raise HTTPException(
            status_code=503,
            detail="Instala STT: pip install SpeechRecognition python-multipart imageio-ffmpeg",
        )
    raw = await audio.read()
    if len(raw) < 200:
        raise HTTPException(status_code=400, detail="Grabación demasiado corta.")
    suffix = ".webm"
    if audio.filename and "." in audio.filename:
        suffix = "." + audio.filename.rsplit(".", 1)[-1].lower()
    try:
        raw_text = await asyncio.to_thread(transcribe_audio_bytes, raw, suffix=suffix)
        text = await asyncio.to_thread(polish_transcript, raw_text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo transcribir: {exc}") from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="No se entendió el audio.")
    return TranscribeResponse(
        text=text.strip(),
        raw_text=raw_text.strip() if raw_text.strip() != text.strip() else None,
    )


@app.post("/api/session", response_model=SessionResponse)
def new_session():
    session = create_session()
    return SessionResponse(session_id=session.id)


def _is_first_turn(session) -> bool:
    return not any(m.get("role") == "assistant" for m in session.messages)


async def _welcome_chat_response(session) -> ChatResponse:
    welcome = WELCOME_MESSAGE.strip()
    if not welcome:
        raise HTTPException(status_code=500, detail="WELCOME_MESSAGE no configurado en .env")
    session.messages.append({"role": "assistant", "content": welcome})
    try:
        audio_b64 = await _reply_with_voice(welcome)
    except Exception as exc:
        session.messages.pop()
        raise HTTPException(status_code=502, detail=f"Error al generar voz de bienvenida: {exc}") from exc
    return ChatResponse(
        session_id=session.id,
        reply_text=welcome,
        audio_base64=audio_b64,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(body: ChatRequest):
    session = get_session(body.session_id) if body.session_id else None
    if session is None:
        session = create_session()

    user_text = body.message.strip()
    session.messages.append({"role": "user", "content": user_text})

    try:
        reply = chat(build_messages(session.messages))
    except Exception as exc:
        session.messages.pop()
        raise HTTPException(status_code=502, detail=f"No se pudo contactar Ollama: {exc}") from exc

    if not reply:
        session.messages.pop()
        raise HTTPException(status_code=502, detail="Ollama devolvió una respuesta vacía.")

    session.messages.append({"role": "assistant", "content": reply})

    try:
        audio_b64 = await _reply_with_voice(reply)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error al generar voz: {exc}") from exc

    return ChatResponse(
        session_id=session.id,
        reply_text=reply,
        audio_base64=audio_b64,
    )


@app.get("/")
def index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="Interfaz no encontrada.")
    return FileResponse(index_path)


static_assets = STATIC_DIR
if static_assets.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_assets)), name="static")
