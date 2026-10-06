"""
Liquidacion resolution helpers for Finanzas domain.

Pure model-field accessors — no DB queries, no side effects.
Used by RH Delegado and RH Inspector flujos.
"""
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
        LiquidacionGeneral,
    )


# Map tipo_liquidacion.codigo to related_name for the OneToOne relation
# that holds the AutoNumeroModel.numero field.
RELATED_NAME_BY_TIPO = {
    "EDIFICACION": "edificaciones",
    "TALUDES": "taludes",
    "HABILITACION_URBANA": "habilitacion_urbana",
    "MECANICA_SUELOS": "mecanica_suelos",
    "INSPECCION_OBRA": "inspeccion_obra",
    "IMPACTO_VIAL": "impacto_vial",
}


def _resolve_liquidacion_especifica_numero(lg: "LiquidacionGeneral") -> int | None:
    """
    Resolve the specific liquidation numero from the LiquidacionGeneral.

    Accesses the one-to-one related specific model (Edificaciones, Taludes, etc.)
    based on tipo_liquidacion.codigo and returns its numero field.

    Returns None for legacy records that don't have a specific relation.
    """
    if not lg or not lg.tipo_liquidacion:
        return None

    codigo = lg.tipo_liquidacion.codigo

    related_name = RELATED_NAME_BY_TIPO.get(codigo)
    if not related_name:
        return None

    specific = getattr(lg, related_name, None)
    if not specific:
        return None

    return getattr(specific, "numero", None)
