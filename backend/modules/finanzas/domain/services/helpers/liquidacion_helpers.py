"""
Liquidacion resolution helpers for Finanzas domain.

Pure model-field accessors — no DB queries, no side effects.
Used by RH Delegado and RH Inspector flujos.
"""
from decimal import Decimal
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


def _resolve_estrategia_po(
    lg: "LiquidacionGeneral",
) -> tuple[Optional[str], Optional[Decimal]]:
    """
    Resolve the PO quotation strategy and its explicit total from the LiquidacionGeneral.

    The strategy (``estrategia_cotizacion``) and the explicit total
    (``total_explicito``) live on ``LiquidacionPorcentajeObra``, the one-to-one
    PO wrapper of the LiquidacionGeneral. Only the PO engine has strategies:
    M2 (HU/MS) and Visitas (IO) have no such wrapper, so both values are
    ``None`` for them.

    ``total_explicito`` is only populated under ``TOTAL_EXPLICITO``; under the
    other strategies it stays ``None`` and the totals come from the details.

    Returns:
        Tuple (estrategia_cotizacion, total_explicito). Both ``None`` when the
        liquidation has no PO wrapper.
    """
    if not lg:
        return None, None

    po = getattr(lg, "liquidacion_porcentaje_obra", None)
    if not po:
        return None, None

    estrategia = getattr(po, "estrategia_cotizacion", None)
    total_explicito = getattr(po, "total_explicito", None)

    return (
        estrategia if isinstance(estrategia, str) and estrategia else None,
        Decimal(str(total_explicito)) if total_explicito is not None else None,
    )
