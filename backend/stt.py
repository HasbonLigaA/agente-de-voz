from __future__ import annotations

import importlib.util
import logging
import re
import shutil
import subprocess
import tempfile
import threading
from collections import Counter
from pathlib import Path

from backend.config import (
    STT_ENGINE,
    STT_FALLBACK_GOOGLE,
    STT_FALLBACK_ON_LOW_CONFIDENCE,
    STT_LANGUAGE,
    WHISPER_BEAM_SIZE,
    WHISPER_COMPUTE,
    WHISPER_DEVICE,
    WHISPER_INITIAL_PROMPT,
    WHISPER_MODEL_SIZE,
)

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()


def stt_available() -> bool:
    if STT_ENGINE in ("google",):
        return importlib.util.find_spec("speech_recognition") is not None
    if STT_ENGINE in ("whisper", "auto"):
        return importlib.util.find_spec("faster_whisper") is not None
    return importlib.util.find_spec("faster_whisper") is not None


def _ffmpeg_executable() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _bytes_to_wav_file(data: bytes, suffix: str) -> Path:
    """Normaliza grabación del navegador (webm/opus) a WAV mono 16 kHz."""
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    ffmpeg = _ffmpeg_executable()
    webm_path = wav_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            webm_path = Path(tmp.name)
        wav_path = webm_path.with_suffix(".wav")
        # dynaudnorm ayuda micrófonos de portátil (volumen bajo / ruido de ventilador).
        af = "highpass=f=100,lowpass=f=7800,dynaudnorm=f=60:g=12:p=0.9"
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(webm_path),
            "-af",
            af,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(wav_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, check=False)
        if proc.returncode != 0 or not wav_path.is_file() or wav_path.stat().st_size < 2000:
            err = proc.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(err or "No se pudo convertir el audio a WAV.")
        return wav_path
    finally:
        if webm_path is not None:
            webm_path.unlink(missing_ok=True)


def _normalize_words(text: str) -> list[str]:
    return re.findall(r"[a-záéíóúüñ]+", text.lower(), flags=re.IGNORECASE)


def looks_hallucinated(text: str) -> bool:
    words = _normalize_words(text)
    if len(words) < 2:
        return len(words) == 0
    word, count = Counter(words).most_common(1)[0]
    if count >= 2 and len(words) <= 4:
        return True
    if count >= 3 and count / len(words) >= 0.45:
        return True
    junk = (
        "gracias por ver",
        "suscríbete",
        "subtítulos",
        "amara.org",
        "www.",
        "http",
    )
    low = text.lower()
    if any(j in low for j in junk):
        return True
    return False


def warm_whisper_model() -> None:
    """Precarga el modelo en arranque para que la primera transcripción no espere."""
    if STT_ENGINE == "google" or not stt_available():
        return
    _load_whisper()


def _load_whisper():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from faster_whisper import WhisperModel

        logger.info(
            "Cargando Whisper %s (%s, %s)…",
            WHISPER_MODEL_SIZE,
            WHISPER_DEVICE,
            WHISPER_COMPUTE,
        )
        _model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE,
        )
        return _model


def _transcribe_google_wav(wav_path: Path) -> str:
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold = 300
    recognizer.pause_threshold = 0.8
    with sr.AudioFile(str(wav_path)) as source:
        audio = recognizer.record(source)
    lang = STT_LANGUAGE.replace("_", "-")
    text = ""
    for attempt_lang in (lang, "es-ES", "es-MX", "es"):
        try:
            text = recognizer.recognize_google(audio, language=attempt_lang)
            if text.strip():
                break
        except sr.UnknownValueError:
            continue
        except sr.RequestError as exc:
            raise RuntimeError("STT Google no disponible (revisa internet/firewall).") from exc
    if not text.strip():
        raise RuntimeError("Google no entendió el audio. Habla más claro y cerca del micrófono.")
    return text.strip()


def _transcribe_whisper_wav(wav_path: Path) -> tuple[str, float | None]:
    model = _load_whisper()
    whisper_kw: dict = {
        "language": "es",
        "task": "transcribe",
        "beam_size": max(1, WHISPER_BEAM_SIZE),
        "best_of": 1,
        "vad_filter": True,
        "vad_parameters": {
            "min_silence_duration_ms": 400,
            "speech_pad_ms": 350,
            "threshold": 0.45,
        },
        "condition_on_previous_text": False,
        "no_speech_threshold": 0.55,
        "log_prob_threshold": -1.2,
        "compression_ratio_threshold": 2.4,
    }
    if WHISPER_INITIAL_PROMPT.strip():
        whisper_kw["initial_prompt"] = WHISPER_INITIAL_PROMPT.strip()
    segments, _info = model.transcribe(str(wav_path), **whisper_kw)
    parts: list[str] = []
    logprobs: list[float] = []
    for seg in segments:
        t = seg.text.strip()
        if t:
            parts.append(t)
        if seg.avg_logprob is not None:
            logprobs.append(float(seg.avg_logprob))
    text = re.sub(r"\s+", " ", " ".join(parts)).strip()
    avg_lp = sum(logprobs) / len(logprobs) if logprobs else None
    return text, avg_lp


def _whisper_low_confidence(avg_logprob: float | None) -> bool:
    if avg_logprob is None:
        return True
    return avg_logprob < -0.85


def transcribe_audio_bytes(data: bytes, *, suffix: str = ".webm") -> str:
    if not data:
        raise ValueError("Audio vacío.")
    suffix = suffix if suffix.startswith(".") else f".{suffix}"

    wav_path: Path | None = None
    try:
        wav_path = _bytes_to_wav_file(data, suffix)
        engines: list[str]
        if STT_ENGINE == "auto":
            engines = ["whisper", "google"]
        elif STT_ENGINE == "google":
            engines = ["google"]
        else:
            engines = ["whisper"]

        last_err: Exception | None = None
        for engine in engines:
            try:
                if engine == "google":
                    if importlib.util.find_spec("speech_recognition") is None:
                        continue
                    text = _transcribe_google_wav(wav_path)
                    logger.info("STT [google] %d bytes → %r", len(data), text[:120])
                else:
                    text, avg_lp = _transcribe_whisper_wav(wav_path)
                    logger.info(
                        "STT [whisper] %d bytes avg_logprob=%s → %r",
                        len(data),
                        avg_lp,
                        text[:120],
                    )
                    needs_google = not text or looks_hallucinated(text)
                    if STT_FALLBACK_ON_LOW_CONFIDENCE and _whisper_low_confidence(avg_lp):
                        needs_google = True
                    if (
                        STT_FALLBACK_GOOGLE
                        and STT_ENGINE in ("whisper", "auto")
                        and needs_google
                        and importlib.util.find_spec("speech_recognition") is not None
                    ):
                        logger.info("Whisper poco fiable; probando Google STT…")
                        text = _transcribe_google_wav(wav_path)
                        logger.info("STT [google-fallback] → %r", text[:120])
            except Exception as exc:
                last_err = exc
                logger.warning("STT %s falló: %s", engine, exc)
                continue

            if not text:
                last_err = RuntimeError("No se detectó voz en la grabación.")
                continue
            if looks_hallucinated(text):
                last_err = RuntimeError(
                    "Transcripción poco fiable. Repite más despacio o escribe el mensaje."
                )
                continue
            return text

        if last_err:
            raise last_err
        raise RuntimeError("No se pudo transcribir el audio.")
    finally:
        if wav_path is not None:
            wav_path.unlink(missing_ok=True)
