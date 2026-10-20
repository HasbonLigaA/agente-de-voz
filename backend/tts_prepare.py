"""Texto legible para TTS (pesos colombianos, sin confundir con dólares)."""

from __future__ import annotations

import re


def _cop_amount_phrase(amount: int) -> str:
    if amount <= 0:
        return "cero pesos colombianos"
    if amount < 1000:
        return f"{amount} pesos colombianos"
    miles = amount // 1000
    rest = amount % 1000
    if rest == 0:
        return f"{miles} mil pesos colombianos"
    return f"{miles} mil {rest} pesos colombianos"


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


def _replace_money(match: re.Match[str]) -> str:
    try:
        amount = _parse_colombian_amount(match.group(1))
    except ValueError:
        return match.group(0)
    return _cop_amount_phrase(amount)


def prepare_text_for_speech(text: str) -> str:
    if not text:
        return text
    out = text
    out = re.sub(
        r"(?i)\bd[oó]lares?\s*(estadounidenses|americanos)?\b",
        "pesos colombianos",
        out,
    )
    out = re.sub(r"(?i)\bUSD\b", "pesos colombianos", out)
    out = re.sub(
        r"\$\s*([\d][\d.,]*)",
        _replace_money,
        out,
    )
    out = re.sub(
        r"([\d][\d.,]*)\s*COP\b",
        lambda m: _cop_amount_phrase(_parse_colombian_amount(m.group(1))),
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(r"\s+", " ", out).strip()
    return out
