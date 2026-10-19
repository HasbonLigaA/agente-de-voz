"""Respuestas ancladas al catálogo institucional."""

from __future__ import annotations

import logging

from backend.brand import sanitize_institution_name
from backend.config import (
    GREETING_REPLY,
    GROUNDED_ANSWER_WITH_LLM,
    GROUNDED_ONLY,
    IN_SCOPE_HELP_REPLY,
    OLLAMA_TEXT_MODEL,
    OUT_OF_SCOPE_REPLY,
)
from backend.contact_reply import answer_contact
from backend.grounded_llm import answer_from_catalog, is_short_greeting
from backend.institution_reply import answer_institution
from backend.intent_router import RoutedIntent, route_user_message
from backend.plan_liga_reply import answer_plan_liga
from backend.reply_format import bullet_list, finish_blocks
from backend.specialties_reply import answer_specialties

logger = logging.getLogger(__name__)


def _help_reply() -> str:
    intro = IN_SCOPE_HELP_REPLY.strip() or "Puedo informarte sobre:"
    if not intro.endswith(":"):
        intro = intro.rstrip(".") + ":"
    return finish_blocks(
        [
            intro,
            bullet_list(
                [
                    "La Liga Ama Salvar Vidas: misión, visión, valores e historia",
                    "Plan Liga: beneficios, precio, activación y tarifas",
                    "13 especialidades médicas con descripción y especialistas",
                    "Contacto para citas médicas e información institucional",
                ]
            ),
        ]
    )


def _dispatch(intent: RoutedIntent, user_text: str) -> str:
    match intent.topic:
        case "greeting":
            return sanitize_institution_name(GREETING_REPLY.strip() or _help_reply())
        case "help":
            return _help_reply()
        case "plan_liga":
            return answer_plan_liga(user_text, aspect=intent.plan_liga_aspect)
        case "institution":
            return answer_institution(user_text, aspect=intent.institution_aspect)
        case "specialty_detail":
            return answer_specialties(
                user_text,
                mode="detail",
                specialty_name=intent.specialty_name,
            )
        case "specialties":
            return answer_specialties(
                user_text,
                mode=intent.specialties_mode or "list",
                specialty_name=intent.specialty_name,
            )
        case "contact":
            return answer_contact()
        case _:
            return sanitize_institution_name(OUT_OF_SCOPE_REPLY)


def _answer_with_templates(user_text: str, history: list[dict[str, str]]) -> str:
    prior = history[:-1] if history and history[-1].get("role") == "user" else history
    intent = route_user_message(user_text, prior)
    reply = _dispatch(intent, user_text)
    if intent.topic == "out_of_scope" and not GROUNDED_ONLY:
        from backend.llm import build_messages, chat

        return chat(build_messages(history))
    return reply


def answer_grounded(user_text: str, history: list[dict[str, str]]) -> str:
    text = user_text.strip()
    if not text:
        return OUT_OF_SCOPE_REPLY

    if is_short_greeting(text) and GREETING_REPLY.strip():
        return sanitize_institution_name(GREETING_REPLY.strip())

    use_llm = GROUNDED_ANSWER_WITH_LLM and bool(OLLAMA_TEXT_MODEL)
    if use_llm:
        try:
            return answer_from_catalog(history)
        except Exception as exc:
            logger.warning("Respuesta con catálogo LLM falló (%s); usando plantillas.", exc)

    return _answer_with_templates(text, history)
