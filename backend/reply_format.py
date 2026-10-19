"""Formato consistente de respuestas (bloques separados y listas)."""

from __future__ import annotations

from backend.brand import sanitize_institution_name


def bullet_list(items: list[str]) -> str:
    return "\n".join(f"• {item}" for item in items)


def numbered_list(items: list[str]) -> str:
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items, start=1))


def labeled_bullets(pairs: list[tuple[str, str]]) -> str:
    return "\n".join(f"• {label}: {text}" for label, text in pairs)


def finish_blocks(blocks: list[str]) -> str:
    return sanitize_institution_name("\n\n".join(b.strip() for b in blocks if b.strip()))
