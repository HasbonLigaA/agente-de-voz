"""Datos de contacto institucional (misma fuente que Plan Liga)."""

from __future__ import annotations

from backend.knowledge.plan_liga import PLAN_LIGA

CONTACTO = {
    **PLAN_LIGA["contacto"],
    "nombre_institucion": "La Liga Ama Salvar Vidas",
    "ciudad": "Pereira, Risaralda",
}
