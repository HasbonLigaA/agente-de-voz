"""Clasificación de intención por significado (LLM + respaldo semántico)."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from backend.config import OLLAMA_TEXT_MODEL, ROUTING_USE_LLM
from backend.knowledge.specialties import SPECIALTIES, find_specialty_in_text

logger = logging.getLogger(__name__)

VALID_TOPICS = frozenset(
    {
        "greeting",
        "help",
        "plan_liga",
        "institution",
        "specialties",
        "specialty_detail",
        "contact",
        "out_of_scope",
    }
)

_TOPIC_SEMANTICS: dict[str, str] = {
    "plan_liga": (
        "Membresía anual Plan Liga: precio, beneficios, titular y beneficiarios, "
        "activación con comprobante de pago, tarifas preferenciales en servicios de salud."
    ),
    "institution": (
        "La Liga Ama Salvar Vidas como fundación: quiénes somos, misión, visión, valores, "
        "historia desde 1976, qué hace la institución en salud en Pereira."
    ),
    "specialties": (
        "Listado de especialidades médicas disponibles, cuántas áreas hay, "
        "directorio de especialistas de la institución."
    ),
    "specialty_detail": (
        "Información de una especialidad médica concreta: para qué sirve, "
        "cuántos especialistas hay en esa área."
    ),
    "contact": (
        "Teléfonos, WhatsApp, correos, dirección física, citas médicas, "
        "cómo contactar a la institución."
    ),
    "help": "Qué temas puede responder el asistente, en qué ayuda el chat.",
}

_CLASSIFIER_SYSTEM = """Eres un clasificador de intención para el chat de La Liga Ama Salvar Vidas.
Interpreta el SIGNIFICADO del mensaje y del historial reciente, no palabras exactas.
Responde SOLO un JSON válido (sin markdown).

Temas (campo "topic"):
- plan_liga: membresía Plan Liga (precio, beneficios, pago, activación, tarifas, titular/beneficiarios)
- institution: la fundación (misión, visión, valores, historia, qué es / qué hace)
- specialties: listar o enumerar especialidades médicas del directorio
- specialty_detail: detalle de UNA especialidad (usa specialty_name si la nombran o se infiere del contexto)
- contact: teléfonos, WhatsApp, correo, dirección, citas
- help: qué puede hacer el asistente
- greeting: saludo o despedida breve sin pregunta de fondo
- out_of_scope: fuera de esos temas (citas clínicas personales, diagnósticos, otros servicios no catalogados)

Campos opcionales:
- plan_liga_aspect: benefits | price | activation | tariffs | eligibility | general | null
- institution_aspect: mission | vision | values | history | purpose | general | null
- specialties_mode: list | explain_all | detail | null
- specialty_name: nombre exacto del catálogo o null

Catálogo de especialidades (solo estos nombres en specialty_name):
""" + ", ".join(SPECIALTIES) + """

Si el usuario hace seguimiento ("¿y el precio?", "cuéntame más"), usa el historial para el topic correcto.
"""


@dataclass(frozen=True)
class RoutedIntent:
    topic: str
    plan_liga_aspect: str | None = None
    institution_aspect: str | None = None
    specialties_mode: str | None = None
    specialty_name: str | None = None
    source: str = "fallback"


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _history_snippet(history: list[dict[str, str]], *, max_turns: int = 6) -> str:
    lines: list[str] = []
    for msg in history[-max_turns:]:
        role = msg.get("role") or "user"
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        label = "Usuario" if role == "user" else "Asistente"
        lines.append(f"{label}: {content[:400]}")
    return "\n".join(lines)


def _extract_json_object(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object in model output")
    return json.loads(raw[start : end + 1])


def _clean_optional(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s or s in ("null", "none", "n/a"):
        return None
    return s


_PLAN_ASPECT_ALIASES = {
    "benefits": "benefits",
    "beneficios": "benefits",
    "beneficio": "benefits",
    "price": "price",
    "precio": "price",
    "activation": "activation",
    "activacion": "activation",
    "tariffs": "tariffs",
    "tarifas": "tariffs",
    "eligibility": "eligibility",
    "requisitos": "eligibility",
    "general": "general",
}

_INST_ASPECT_ALIASES = {
    "mission": "mission",
    "mision": "mission",
    "vision": "vision",
    "values": "values",
    "valores": "values",
    "history": "history",
    "historia": "history",
    "purpose": "purpose",
    "general": "general",
}

_SPEC_MODE_ALIASES = {
    "list": "list",
    "lista": "list",
    "explain_all": "explain_all",
    "detalle": "explain_all",
    "detail": "detail",
}


def _map_aspect(raw: str | None, table: dict[str, str]) -> str | None:
    if not raw:
        return None
    return table.get(raw.lower(), raw.lower())


def _resolve_specialty(candidate: str | None, user_text: str, history: list[dict[str, str]]) -> str | None:
    if candidate:
        cn = _norm(candidate)
        for name in SPECIALTIES:
            if _norm(name) == cn:
                return name
        for name in SPECIALTIES:
            nk = _norm(name)
            if cn in nk or nk in cn:
                return name
    combined = user_text + "\n" + _history_snippet(history, max_turns=4)
    return find_specialty_in_text(combined)


def _intent_from_dict(data: dict, user_text: str, history: list[dict[str, str]]) -> RoutedIntent:
    topic = _clean_optional(data.get("topic")) or "out_of_scope"
    if topic not in VALID_TOPICS:
        topic = "out_of_scope"

    plan_aspect = _map_aspect(_clean_optional(data.get("plan_liga_aspect")), _PLAN_ASPECT_ALIASES)
    inst_aspect = _map_aspect(_clean_optional(data.get("institution_aspect")), _INST_ASPECT_ALIASES)
    spec_mode = _map_aspect(_clean_optional(data.get("specialties_mode")), _SPEC_MODE_ALIASES)
    raw_spec = data.get("specialty_name")
    spec_candidate = None if raw_spec is None else str(raw_spec).strip()
    if spec_candidate and spec_candidate.lower() in ("null", "none"):
        spec_candidate = None
    spec_name = _resolve_specialty(spec_candidate, user_text, history)

    if spec_name and topic in ("specialties", "out_of_scope"):
        topic = "specialty_detail"
        spec_mode = spec_mode or "detail"
    if topic == "specialty_detail" and not spec_name:
        topic = "specialties"
        spec_mode = spec_mode or "list"

    return RoutedIntent(
        topic=topic,
        plan_liga_aspect=plan_aspect,
        institution_aspect=inst_aspect,
        specialties_mode=spec_mode,
        specialty_name=spec_name,
        source="llm",
    )


def _semantic_fallback(user_text: str, history: list[dict[str, str]]) -> RoutedIntent:
    context = _norm(user_text + " " + _history_snippet(history, max_turns=4))
    scores = {
        topic: SequenceMatcher(None, context, _norm(desc)).ratio()
        for topic, desc in _TOPIC_SEMANTICS.items()
    }
    best_topic = max(scores, key=scores.get)
    best_score = scores[best_topic]

    spec = find_specialty_in_text(user_text) or find_specialty_in_text(
        _history_snippet(history, max_turns=4)
    )
    if spec:
        detail_hints = SequenceMatcher(
            None, context, _norm(_TOPIC_SEMANTICS["specialty_detail"])
        ).ratio()
        list_hints = SequenceMatcher(
            None, context, _norm(_TOPIC_SEMANTICS["specialties"])
        ).ratio()
        if detail_hints >= list_hints - 0.05:
            return RoutedIntent(
                topic="specialty_detail",
                specialty_name=spec,
                specialties_mode="detail",
                source="fallback",
            )

    if best_score < 0.22:
        return RoutedIntent(topic="out_of_scope", source="fallback")

    if best_topic == "specialties":
        explain = SequenceMatcher(
            None, context, _norm("explicar describir detalle cada especialidad")
        ).ratio()
        return RoutedIntent(
            topic="specialties",
            specialties_mode="explain_all" if explain > 0.35 else "list",
            source="fallback",
        )

    if best_topic == "plan_liga":
        aspect_desc = {
            "benefits": "beneficios ventajas que incluye que trae membresia",
            "price": "precio cuesta vale cuanto pagar costo 499",
            "activation": "activar comprobante pago afiliar comprar",
            "tariffs": "tarifas consultas examenes resonancia",
            "eligibility": "quien puede titular beneficiarios requisitos edad",
        }
        aspect = max(
            aspect_desc,
            key=lambda k: SequenceMatcher(None, context, _norm(aspect_desc[k])).ratio(),
        )
        return RoutedIntent(topic="plan_liga", plan_liga_aspect=aspect, source="fallback")

    if best_topic == "institution":
        aspect_desc = {
            "mission": "mision",
            "vision": "vision",
            "values": "valores principios",
            "history": "historia fundacion 1976",
            "purpose": "para que sirve que hace dedicacion",
        }
        aspect = max(
            aspect_desc,
            key=lambda k: SequenceMatcher(None, context, _norm(aspect_desc[k])).ratio(),
        )
        return RoutedIntent(topic="institution", institution_aspect=aspect, source="fallback")

    return RoutedIntent(topic=best_topic, source="fallback")


def _classify_with_llm(user_text: str, history: list[dict[str, str]]) -> RoutedIntent | None:
    if not ROUTING_USE_LLM or not OLLAMA_TEXT_MODEL:
        return None
    hist = _history_snippet(history)
    user_block = f"Historial reciente:\n{hist or '(sin historial)'}\n\nMensaje actual:\n{user_text}"
    messages = [
        {"role": "system", "content": _CLASSIFIER_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    try:
        from backend.llm import chat

        raw = chat(
            messages,
            temperature=0.05,
            num_predict=120,
            num_ctx=4096,
        )
        data = _extract_json_object(raw)
        return _intent_from_dict(data, user_text, history)
    except Exception as exc:
        logger.warning("Clasificador LLM falló (%s); usando respaldo semántico.", exc)
        return None


_GREETING_ONLY = re.compile(
    r"(?i)^\s*(hola|buenos?\s+d[ií]as|buenas?\s+tardes|buenas?\s+noches|"
    r"gracias|adi[oó]s|chao|ok|vale)\s*[.!?]*\s*$"
)


def route_user_message(
    user_text: str,
    history: list[dict[str, str]],
    *,
    use_llm: bool | None = None,
) -> RoutedIntent:
    text = user_text.strip()
    if not text:
        return RoutedIntent(topic="out_of_scope", source="rules")

    if _GREETING_ONLY.match(text):
        return RoutedIntent(topic="greeting", source="rules")

    routing_llm = ROUTING_USE_LLM if use_llm is None else use_llm
    llm_intent = _classify_with_llm(text, history) if routing_llm else None
    if llm_intent is not None:
        logger.info(
            "Intent [%s] topic=%s plan=%s inst=%s spec=%s mode=%s",
            llm_intent.source,
            llm_intent.topic,
            llm_intent.plan_liga_aspect,
            llm_intent.institution_aspect,
            llm_intent.specialty_name,
            llm_intent.specialties_mode,
        )
        return llm_intent

    fallback = _semantic_fallback(text, history)
    logger.info("Intent [fallback] topic=%s", fallback.topic)
    return fallback
