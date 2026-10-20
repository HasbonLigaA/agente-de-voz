from __future__ import annotations

import importlib.util
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from collections import Counter
from pathlib import Path

from backend.config import (
    STT_ENGINE,
    STT_FALLBACK_GOOGLE,
    STT_FALLBACK_ON_LOW_CONFIDENCE,
    STT_LANGUAGE,
    WHISPER_BEAM_SIZE,
    WHISPER_COMPUTE,
    WHISPER_CPU_THREADS,
    WHISPER_DEVICE,
    WHISPER_FAST_FFMPEG,
    WHISPER_INITIAL_PROMPT,
    WHISPER_LANGUAGE,
    WHISPER_MODEL_SIZE,
    WHISPER_VAD_FILTER,
)

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()


def stt_available() -> bool:
    if STT_ENGINE == "google":
        return importlib.util.find_spec("speech_recognition") is not None
    if STT_ENGINE in ("whisper", "auto"):
        if importlib.util.find_spec("faster_whisper") is not None:
            return True
        return importlib.util.find_spec("speech_recognition") is not None
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
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(webm_path),
        ]
        if not WHISPER_FAST_FFMPEG:
            cmd.extend(["-af", "highpass=f=100,lowpass=f=7800,dynaudnorm=f=60:g=12:p=0.9"])
        cmd.extend(
            [
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(wav_path),
            ]
        )
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
        "thank you for watching",
        "subscribe",
    )
    low = text.lower()
    if any(j in low for j in junk):
        return True
    return False


def warm_whisper_model() -> None:
    if STT_ENGINE == "google" or not importlib.util.find_spec("faster_whisper"):
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

        model_name = WHISPER_MODEL_SIZE
        if re.search(r"\.en\b|english", model_name, re.I):
            logger.warning(
                "Modelo Whisper '%s' parece solo inglés. Usa base/small/tiny multilingüe y WHISPER_LANGUAGE=es.",
                model_name,
            )
        cpu_threads = WHISPER_CPU_THREADS or min(8, (os.cpu_count() or 4))
        logger.info(
            "Cargando Whisper %s (%s, %s, threads=%s, idioma=%s)…",
            model_name,
            WHISPER_DEVICE,
            WHISPER_COMPUTE,
            cpu_threads,
            WHISPER_LANGUAGE,
        )
        _model = WhisperModel(
            model_name,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE,
            cpu_threads=cpu_threads,
            num_workers=1,
        )
        return _model


def _transcribe_google_wav(wav_path: Path) -> str:
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold = 300
    recognizer.pause_threshold = 0.65
    with sr.AudioFile(str(wav_path)) as source:
        audio = recognizer.record(source)
    lang = STT_LANGUAGE.replace("_", "-")
    text = ""
    for attempt_lang in (lang, "es-CO", "es-419", "es-ES", "es-MX", "es"):
        try:
            text = recognizer.recognize_google(audio, language=attempt_lang)
            if text.strip():
                logger.info("STT Google idioma=%s", attempt_lang)
                break
        except sr.UnknownValueError:
            continue
        except sr.RequestError as exc:
            raise RuntimeError("STT Google no disponible (revisa internet/firewall).") from exc
    if not text.strip():
        raise RuntimeError("Google no entendió el audio. Habla más claro y cerca del micrófono.")
    return text.strip()


def _transcribe_whisper_wav(wav_path: Path) -> tuple[str, float | None, str | None]:
    model = _load_whisper()
    lang = WHISPER_LANGUAGE if WHISPER_LANGUAGE != "auto" else "es"
    whisper_kw: dict = {
        "language": lang,
        "task": "transcribe",
        "beam_size": max(1, WHISPER_BEAM_SIZE),
        "best_of": 1,
        "condition_on_previous_text": False,
        "without_timestamps": True,
        "no_speech_threshold": 0.5,
        "log_prob_threshold": -1.0,
        "compression_ratio_threshold": 2.4,
    }
    if WHISPER_VAD_FILTER:
        whisper_kw["vad_filter"] = True
        whisper_kw["vad_parameters"] = {
            "min_silence_duration_ms": 300,
            "speech_pad_ms": 200,
            "threshold": 0.45,
        }
    else:
        whisper_kw["vad_filter"] = False

    if WHISPER_INITIAL_PROMPT.strip():
        whisper_kw["initial_prompt"] = WHISPER_INITIAL_PROMPT.strip()

    segments, info = model.transcribe(str(wav_path), **whisper_kw)
    detected = getattr(info, "language", None)
    if detected and str(detected).lower() not in (lang, "es", "spa"):
        logger.warning(
            "Whisper detectó idioma %s (forzado %s). Revisa WHISPER_MODEL_SIZE (evita modelos .en).",
            detected,
            lang,
        )

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
    return text, avg_lp, detected


def _whisper_low_confidence(avg_logprob: float | None) -> bool:
    if avg_logprob is None:
        return True
    return avg_logprob < -0.85


def _engine_order() -> list[str]:
    if STT_ENGINE == "google":
        return ["google"]
    if STT_ENGINE == "whisper":
        return ["whisper"]
    # auto: Google primero (rápido + español nativo en la nube), Whisper como respaldo offline
    return ["google", "whisper"]


def transcribe_audio_bytes(data: bytes, *, suffix: str = ".webm") -> str:
    if not data:
        raise ValueError("Audio vacío.")
    suffix = suffix if suffix.startswith(".") else f".{suffix}"

    t0 = time.perf_counter()
    wav_path: Path | None = None
    try:
        wav_path = _bytes_to_wav_file(data, suffix)
        t_wav = time.perf_counter()
        engines = _engine_order()
        last_err: Exception | None = None

        for engine in engines:
            try:
                if engine == "google":
                    if importlib.util.find_spec("speech_recognition") is None:
                        continue
                    text = _transcribe_google_wav(wav_path)
                    logger.info(
                        "STT [google] %d bytes en %.2fs → %r",
                        len(data),
                        time.perf_counter() - t_wav,
                        text[:120],
                    )
                else:
                    if importlib.util.find_spec("faster_whisper") is None:
                        continue
                    text, avg_lp, detected = _transcribe_whisper_wav(wav_path)
                    logger.info(
                        "STT [whisper/%s] %d bytes en %.2fs lang=%s avg_logprob=%s → %r",
                        WHISPER_MODEL_SIZE,
                        len(data),
                        time.perf_counter() - t_wav,
                        detected or WHISPER_LANGUAGE,
                        avg_lp,
                        text[:120],
                    )
                    needs_google = not text or looks_hallucinated(text)
                    if STT_FALLBACK_ON_LOW_CONFIDENCE and _whisper_low_confidence(avg_lp):
                        needs_google = True
                    if (
                        STT_FALLBACK_GOOGLE
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
            logger.info("STT total %.2fs (ffmpeg %.2fs)", time.perf_counter() - t0, t_wav - t0)
            return text

        if last_err:
            raise last_err
        raise RuntimeError("No se pudo transcribir el audio.")
    finally:
        if wav_path is not None:
            wav_path.unlink(missing_ok=True)
