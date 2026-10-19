"""Lista completa de especialidades (sin inventar ni remitir a la web)."""

from __future__ import annotations

from backend.brand import sanitize_institution_name
from backend.knowledge.specialties import SPECIALTIES


def format_all_specialties() -> str:
    n = len(SPECIALTIES)
    joined = ", ".join(SPECIALTIES)
    return sanitize_institution_name(
        f"En La Liga Ama Salvar Vidas contamos con {n} especialidades médicas. "
        f"La lista completa es: {joined}. "
        f"Para agendar una cita en cualquiera de ellas, llama a citas médicas al +57 606 333 3340."
    )


def answer_specialties(_user_message: str) -> str:
    return format_all_specialties()
