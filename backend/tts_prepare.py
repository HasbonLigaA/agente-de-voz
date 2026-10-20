"""Texto legible para TTS (pesos colombianos, sin confundir con dólares)."""

from __future__ import annotations

import re


def _cop_amount_phrase(amount: int) -> str:
    if amount <= 0:
        return "cero pesos colombianos"
    if amount < 1000:
        return f"{amount} pesos colombianos"

    millones = amount // 1_000_000
    resto = amount % 1_000_000
    partes: list[str] = []

    if millones == 1:
        partes.append("1 millón")
    elif millones > 1:
        partes.append(f"{millones} millones")

    if resto >= 1000:
        miles = resto // 1000
        unidades = resto % 1000
        if miles == 1:
            partes.append("1 mil")
        elif miles > 1:
            partes.append(f"{miles} mil")
        if unidades > 0:
            partes.append(str(unidades))
    elif resto > 0:
        partes.append(str(resto))

    cuerpo = " ".join(partes) if partes else str(amount)
    return f"{cuerpo} pesos colombianos"


def _parse_colombian_amount(raw: str) -> int:
    cleaned = raw.strip().replace(" ", "")
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", "")
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            cleaned = cleaned.replace(".", "")
        elif len(parts[-1]) == 3:
            cleaned = cleaned.replace(".", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", "")
    return int(cleaned)


def _spoken_amount(raw: str) -> str | None:
    try:
        return _cop_amount_phrase(_parse_colombian_amount(raw))
    except ValueError:
        return None


def _replace_money(match: re.Match[str]) -> str:
    spoken = _spoken_amount(match.group(1))
    return spoken if spoken else match.group(0)


def _dedupe_pesos_colombianos(out: str) -> str:
    out = re.sub(
        r"(?i)(pesos\s+colombianos)(?:\s+\1)+",
        r"\1",
        out,
    )
    out = re.sub(
        r"(?i)(pesos\s+colombianos)\s+(?=\1\b)",
        r"\1 ",
        out,
    )
    return out


def _normalize_money_for_speech(out: str) -> str:
    """Un monto → una sola frase con «pesos colombianos» (sin repetir la moneda)."""

    def range_with_shared_suffix(m: re.Match[str]) -> str:
        a = _spoken_amount(m.group(1))
        b = _spoken_amount(m.group(2))
        if not a or not b:
            return m.group(0)
        return f"{a} a {b}"

    out = re.sub(
        r"([\d][\d.,]*)\s+a\s+([\d][\d.,]*)\s*pesos\s+colombianos",
        range_with_shared_suffix,
        out,
        flags=re.IGNORECASE,
    )

    out = re.sub(
        r"\$\s*([\d][\d.,]*)\s*(?:pesos\s+colombianos|cop\b)?",
        _replace_money,
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"(?<!\d)([\d][\d.,]*)\s*(?:pesos\s+colombianos|cop\b)",
        _replace_money,
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"(?<!\d)(\d{1,3}(?:\.\d{3})+)(?!\d)",
        _replace_money,
        out,
    )
    return _dedupe_pesos_colombianos(out)


def _strip_markup_for_speech(text: str) -> str:
    """Quita markdown y símbolos que el TTS lee en voz alta (asterisco, numeral, etc.)."""
    out = text
    out = re.sub(r"```[\s\S]*?```", " ", out)
    out = re.sub(r"`([^`]*)`", r"\1", out)
    out = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"\1", out)
    out = re.sub(r"__([^_]+)__", r"\1", out)
    out = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"\1", out)
    out = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1", out)
    out = re.sub(r"(?m)^#{1,6}\s*", "", out)
    out = re.sub(r"(?m)^[\t ]*[-*+•·]\s+", "", out)
    out = out.replace("•", " ").replace("·", " ")
    out = re.sub(r"[#*_~`|\\<>{}[\]]", " ", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def prepare_text_for_speech(text: str) -> str:
    if not text:
        return text
    out = _strip_markup_for_speech(text)
    out = re.sub(
        r"(?i)\bd[oó]lares?\s*(estadounidenses|americanos)?\b",
        "pesos colombianos",
        out,
    )
    out = re.sub(r"(?i)\bUSD\b", "pesos colombianos", out)
    out = _normalize_money_for_speech(out)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def compress_reply_for_voice(text: str, max_chars: int = 3200) -> str:
    """Menos pausas y longitud acotada para TTS más ágil en modo voz."""
    if not text:
        return text
    out = re.sub(r"\n+", ". ", text)
    out = re.sub(r"\s+", " ", out).strip()
    if max_chars > 0 and len(out) > max_chars:
        cut = out[: max_chars - 48].rsplit(" ", 1)[0]
        out = f"{cut}… Para más detalle, pregunta por el chat escrito."
    return prepare_text_for_speech(out)
