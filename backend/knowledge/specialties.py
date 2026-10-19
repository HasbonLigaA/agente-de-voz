"""Catálogo de especialistas (directorio institucional).

Fuente: https://laligaamasalvarvidas.org.co/contenido/nuestros-especialistas/220
Actualizar cuando cambie la web o se conecte Oracle.
"""

from __future__ import annotations

import re
import unicodedata

SPECIALISTS_SOURCE_URL = (
    "https://laligaamasalvarvidas.org.co/contenido/nuestros-especialistas/220"
)

TOTAL_SPECIALISTS_LABEL = "65+"
SPECIALTY_AREAS_COUNT = 13

# Orden y conteos según la página «Nuestros especialistas»
SPECIALTY_CATALOG: tuple[dict[str, str | int], ...] = (
    {
        "nombre": "Medicina Familiar",
        "especialistas": 1,
        "descripcion": (
            "Atención integral y continua para personas y familias, con énfasis en "
            "prevención, diagnóstico y manejo de enfermedades comunes."
        ),
    },
    {
        "nombre": "Fisiatría",
        "especialistas": 2,
        "descripcion": (
            "Rehabilitación física y funcional para recuperar movilidad y calidad de "
            "vida tras lesiones o enfermedades."
        ),
    },
    {
        "nombre": "Neurocirugía",
        "especialistas": 6,
        "descripcion": (
            "Tratamiento de enfermedades del sistema nervioso que pueden requerir "
            "manejo quirúrgico especializado."
        ),
    },
    {
        "nombre": "Cirugía Plástica",
        "especialistas": 3,
        "descripcion": (
            "Procedimientos reconstructivos y estéticos con criterio médico y "
            "seguridad del paciente."
        ),
    },
    {
        "nombre": "Genética",
        "especialistas": 3,
        "descripcion": (
            "Estudio de enfermedades hereditarias y variaciones genéticas para "
            "orientar diagnóstico, consejo y seguimiento familiar."
        ),
    },
    {
        "nombre": "Hematología",
        "especialistas": 3,
        "descripcion": (
            "Enfermedades de la sangre y órganos hematopoyéticos, como anemias y "
            "trastornos de coagulación."
        ),
    },
    {
        "nombre": "Dermatología",
        "especialistas": 16,
        "descripcion": (
            "Diagnóstico y tratamiento de enfermedades de la piel, cabello y uñas."
        ),
    },
    {
        "nombre": "Nutrición",
        "especialistas": 2,
        "descripcion": (
            "Manejo alimentario según la condición de salud, promoviendo hábitos "
            "adecuados y recuperación."
        ),
    },
    {
        "nombre": "Urología",
        "especialistas": 4,
        "descripcion": (
            "Atención del sistema urinario y, en hombres, también del sistema reproductor."
        ),
    },
    {
        "nombre": "Ginecología",
        "especialistas": 4,
        "descripcion": (
            "Salud reproductiva y ginecológica para mujeres en distintas etapas de la vida."
        ),
    },
    {
        "nombre": "Gastroenterología",
        "especialistas": 7,
        "descripcion": (
            "Sistema digestivo, incluyendo estómago, intestino e hígado."
        ),
    },
    {
        "nombre": "Otorrinolaringología",
        "especialistas": 8,
        "descripcion": (
            "Oído, nariz y garganta: audición, voz y vías respiratorias superiores."
        ),
    },
    {
        "nombre": "Endocrinología",
        "especialistas": 6,
        "descripcion": (
            "Trastornos hormonales y metabólicos, como diabetes y enfermedades tiroideas."
        ),
    },
)

SPECIALTIES: tuple[str, ...] = tuple(str(item["nombre"]) for item in SPECIALTY_CATALOG)

SPECIALTY_BY_NAME: dict[str, dict[str, str | int]] = {
    str(item["nombre"]): item for item in SPECIALTY_CATALOG
}

# Alias frecuentes en voz (sin inventar especialidades nuevas)
_ALIAS_TO_CANONICAL: dict[str, str] = {
    "medicina familiar": "Medicina Familiar",
    "fisiatria": "Fisiatría",
    "neurocirugia": "Neurocirugía",
    "cirugia plastica": "Cirugía Plástica",
    "genetica": "Genética",
    "hematologia": "Hematología",
    "dermatologia": "Dermatología",
    "nutricion": "Nutrición",
    "urologia": "Urología",
    "ginecologia": "Ginecología",
    "gastroenterologia": "Gastroenterología",
    "otorrinolaringologia": "Otorrinolaringología",
    "otorrino": "Otorrinolaringología",
    "endocrinologia": "Endocrinología",
    "oncologia": "",  # no está en el directorio oficial de 13 áreas
}


def _normalize_key(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip()


def find_specialty_in_text(user_text: str) -> str | None:
    norm = _normalize_key(user_text)
    if not norm:
        return None

    for alias, canonical in sorted(_ALIAS_TO_CANONICAL.items(), key=lambda x: -len(x[0])):
        if not alias:
            continue
        if re.search(rf"\b{re.escape(alias)}\b", norm):
            return canonical or None

    for name in SPECIALTIES:
        key = _normalize_key(name)
        if re.search(rf"\b{re.escape(key)}\b", norm):
            return name
        first = key.split()[0]
        if len(first) >= 5 and re.search(rf"\b{re.escape(first)}\b", norm):
            return name
    return None


def is_known_specialty(name: str | None) -> bool:
    return bool(name and name in SPECIALTY_BY_NAME)
