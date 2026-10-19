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

_TUNNEL_URL_FILE = Path("/tunnel/public_https_url")


def _read_tunnel_url_file() -> str:
    try:
        if _TUNNEL_URL_FILE.is_file():
            return _TUNNEL_URL_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return ""


TRAEFIK_HOST = os.getenv("TRAEFIK_HOST", "agente-voz.laliga.org.co").strip()


def public_https_url() -> str:
    """URL HTTPS para micrófono (env o túnel Cloudflare escrito en volumen compartido)."""
    env_url = os.getenv("PUBLIC_HTTPS_URL", "").strip()
    if env_url:
        return env_url
    return _read_tunnel_url_file()

# Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL") or os.getenv("OLLAMA_MODEL") or ""
OLLAMA_TIMEOUT = _env_float("OLLAMA_TIMEOUT", "120")
OLLAMA_TEMPERATURE = _env_float("OLLAMA_TEMPERATURE", "0.7")
OLLAMA_NUM_CTX = _env_int("OLLAMA_NUM_CTX", "8192")
OLLAMA_NUM_PREDICT = _env_int("OLLAMA_NUM_PREDICT", "256")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

AGENT_SYSTEM_PROMPT = os.getenv("AGENT_SYSTEM_PROMPT", "")

# Solo respuestas desde catálogos / plantillas (sin inventar con Ollama)
GROUNDED_ONLY = _env_bool("GROUNDED_ONLY", "true")

OUT_OF_SCOPE_REPLY = os.getenv(
    "OUT_OF_SCOPE_REPLY",
    "Solo puedo informarte con los datos que tengo: Plan Liga, especialidades médicas "
    "y contacto para citas. Si tu pregunta es otra, un asesor en citas médicas puede ayudarte al +57 606 333 3340.",
)

GREETING_REPLY = os.getenv(
    "GREETING_REPLY",
    "Hola, soy el asistente de La Liga Ama Salvar Vidas. "
    "Puedo contarte sobre el Plan Liga, las especialidades disponibles o cómo contactar citas médicas.",
)

IN_SCOPE_HELP_REPLY = os.getenv(
    "IN_SCOPE_HELP_REPLY",
    "Puedo informarte sobre: el Plan Liga (precio, beneficios y activación), "
    "la lista completa de especialidades médicas, y teléfonos, WhatsApp y dirección de La Liga Ama Salvar Vidas.",
)

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

STT_POLISH_WITH_LLM = _env_bool("STT_POLISH_WITH_LLM", "false")
STT_POLISH_PROMPT = os.getenv("STT_POLISH_PROMPT", "")
STT_POLISH_TEMPERATURE = _env_float("STT_POLISH_TEMPERATURE", "0.15")
STT_POLISH_NUM_CTX = _env_int("STT_POLISH_NUM_CTX", "2048")

# Plan Liga: plantilla sin Ollama = respuesta casi instantánea
PLAN_LIGA_USE_LLM = _env_bool("PLAN_LIGA_USE_LLM", "false")

# Devuelve texto al cliente y genera voz en segundo plano (/api/speech)
CHAT_TEXT_FIRST = _env_bool("CHAT_TEXT_FIRST", "true")

# CORS (front servido desde el mismo host suele no hacer falta; útil en pruebas)
CORS_ALLOW_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    if o.strip()
]

STATIC_DIR = _ROOT / "frontend"
