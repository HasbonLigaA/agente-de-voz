import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=True)


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes")


def _env_float(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _env_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


# Servidor HTTP (uvicorn)
PORT = _env_int("PORT", "8767")

# Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL") or os.getenv("OLLAMA_MODEL") or ""
OLLAMA_TIMEOUT = _env_float("OLLAMA_TIMEOUT", "120")
OLLAMA_TEMPERATURE = _env_float("OLLAMA_TEMPERATURE", "0.7")
OLLAMA_NUM_CTX = _env_int("OLLAMA_NUM_CTX", "8192")
OLLAMA_NUM_PREDICT = _env_int("OLLAMA_NUM_PREDICT", "256")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

AGENT_SYSTEM_PROMPT = os.getenv("AGENT_SYSTEM_PROMPT", "")

TTS_VOICE = os.getenv("TTS_VOICE", "")

WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "")

# STT
STT_ENGINE = os.getenv("STT_ENGINE", "whisper").strip().lower()
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "es-CO")
STT_FALLBACK_GOOGLE = _env_bool("STT_FALLBACK_GOOGLE", "true")
WHISPER_INITIAL_PROMPT = os.getenv("WHISPER_INITIAL_PROMPT", "")

STT_POLISH_WITH_LLM = _env_bool("STT_POLISH_WITH_LLM", "true")
STT_POLISH_PROMPT = os.getenv("STT_POLISH_PROMPT", "")
STT_POLISH_TEMPERATURE = _env_float("STT_POLISH_TEMPERATURE", "0.15")
STT_POLISH_NUM_CTX = _env_int("STT_POLISH_NUM_CTX", "2048")

# CORS (front servido desde el mismo host suele no hacer falta; útil en pruebas)
CORS_ALLOW_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    if o.strip()
]

STATIC_DIR = _ROOT / "frontend"
