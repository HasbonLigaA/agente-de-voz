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

TRAEFIK_HOST = os.getenv("TRAEFIK_HOST", "agente-voz.laliga.org.co").strip()


def app_public_https_url() -> str:
    """URL HTTPS donde el navegador puede usar getUserMedia (micrófono en celular)."""
    explicit = os.getenv("APP_PUBLIC_HTTPS_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    host = os.getenv("PUBLIC_HTTPS_HOST", "seguimiento.laliga.org.co").strip()
    if not host:
        return ""
    tls_port = _env_int("TLS_PORT", "8768")
    if tls_port == 443:
        return f"https://{host}"
    return f"https://{host}:{tls_port}"


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
    "Solo puedo informarte con los datos que tengo: quiénes somos, Plan Liga, "
    "especialidades médicas y contacto para citas. Para otras consultas, citas médicas: +57 606 333 3340.",
)

GREETING_REPLY = os.getenv(
    "GREETING_REPLY",
    "Hola, soy el asistente de La Liga Ama Salvar Vidas. "
    "Puedo contarte sobre el Plan Liga, las especialidades disponibles o cómo contactar citas médicas.",
)

IN_SCOPE_HELP_REPLY = os.getenv(
    "IN_SCOPE_HELP_REPLY",
    "Puedo informarte sobre: quiénes somos, misión, visión e historia de La Liga Ama Salvar Vidas; "
    "el Plan Liga; las 13 especialidades con descripción y número de especialistas; "
    "y contacto para citas.",
)

TTS_VOICE = os.getenv("TTS_VOICE", "")

WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", "")

# STT
# auto = Google (es-CO) primero si hay internet; si falla, Whisper local
# google = solo Google (rápido, requiere red) | whisper = solo local
STT_ENGINE = os.getenv("STT_ENGINE", "auto").strip().lower()
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "es-CO")
STT_FALLBACK_GOOGLE = _env_bool("STT_FALLBACK_GOOGLE", "false")
STT_FALLBACK_ON_LOW_CONFIDENCE = _env_bool("STT_FALLBACK_ON_LOW_CONFIDENCE", "false")

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "int8")
WHISPER_CPU_THREADS = _env_int("WHISPER_CPU_THREADS", "0")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "es").strip().lower() or "es"
WHISPER_BEAM_SIZE = _env_int("WHISPER_BEAM_SIZE", "1")
WHISPER_VAD_FILTER = _env_bool("WHISPER_VAD_FILTER", "false")
WHISPER_FAST_FFMPEG = _env_bool("WHISPER_FAST_FFMPEG", "true")
WHISPER_INITIAL_PROMPT = os.getenv(
    "WHISPER_INITIAL_PROMPT",
    "Español colombiano. La Liga Ama Salvar Vidas. Plan Liga, membresía, citas médicas.",
)

STT_POLISH_WITH_LLM = _env_bool("STT_POLISH_WITH_LLM", "false")
STT_POLISH_PROMPT = os.getenv("STT_POLISH_PROMPT", "")
STT_POLISH_TEMPERATURE = _env_float("STT_POLISH_TEMPERATURE", "0.15")
STT_POLISH_NUM_CTX = _env_int("STT_POLISH_NUM_CTX", "2048")

# Plan Liga: plantilla sin Ollama = respuesta casi instantánea
PLAN_LIGA_USE_LLM = _env_bool("PLAN_LIGA_USE_LLM", "false")

# Interpreta cualquier mensaje con Ollama + catálogo completo (recomendado)
GROUNDED_ANSWER_WITH_LLM = _env_bool("GROUNDED_ANSWER_WITH_LLM", "true")
GROUNDED_ANSWER_TEMPERATURE = _env_float("GROUNDED_ANSWER_TEMPERATURE", "0.15")
GROUNDED_ANSWER_PROMPT = os.getenv("GROUNDED_ANSWER_PROMPT", "")

# Respaldo si falla Ollama: clasificador + plantillas
ROUTING_USE_LLM = _env_bool("ROUTING_USE_LLM", "true")

# Devuelve texto al cliente y genera voz en segundo plano (/api/speech)
CHAT_TEXT_FIRST = _env_bool("CHAT_TEXT_FIRST", "true")

# CORS (front servido desde el mismo host suele no hacer falta; útil en pruebas)
CORS_ALLOW_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    if o.strip()
]

STATIC_DIR = _ROOT / "frontend"
