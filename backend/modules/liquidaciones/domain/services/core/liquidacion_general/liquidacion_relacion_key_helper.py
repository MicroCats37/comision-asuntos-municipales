"""
LiquidacionRelacionMiembro relation_key generator.

Maps a (tipo_liquidacion, optional_subtype) → relacion_key string.

Relation keys are used in LiquidacionRelacionMiembro.relacion_key to identify
the type of the related liquidacion within a group.

Supported mappings:
  - EDIFICACION + tipo_tramite (e.g., OBRA_NUEVA)  → "EDIFICACION-OBRA_NUEVA"
  - EDIFICACION + no subtype                         → "EDIFICACION"
  - HABILITACION_URBANA                             → "HABILITACION_URBANA"
  - MECANICA_SUELOS                                 → "MECANICA_SUELOS"
  - TALUDES                                         → "TALUDES"
  - IMPACTO_VIAL                                    → "IMPACTO_VIAL"
  - INSPECCION_OBRA (IO is exception for delegados — not included here unless needed)

Note: numero_revision is NOT included in relacion_key — it is a separate field.
The (grupo, relacion_key, numero_revision) unique constraint ensures uniqueness
across revisions.

Usage:
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_key_helper import generar_relacion_key
    from modules.liquidaciones.domain.constants import TipoLiquidacion, TipoTramiteEdificaciones

    key = generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA)  # "EDIFICACION-OBRA_NUEVA"
    key = generar_relacion_key(TipoLiquidacion.HABILITACION_URBANA)  # "HABILITACION_URBANA"
"""

from modules.liquidaciones.domain.constants import TipoLiquidacion, TipoTramiteEdificaciones


# Map TipoLiquidacion enum value → base key prefix
# Rule: {tipo_liquidacion.codigo}[-{tipo_tramite}] — full catalog code, no short forms.
_TIPO_BASE_KEY: dict[str, str] = {
    TipoLiquidacion.EDIFICACION: "EDIFICACION",
    TipoLiquidacion.HABILITACION_URBANA: "HABILITACION_URBANA",
    TipoLiquidacion.MECANICA_SUELOS: "MECANICA_SUELOS",
    TipoLiquidacion.TALUDES: "TALUDES",
    TipoLiquidacion.IMPACTO_VIAL: "IMPACTO_VIAL",
    # IO is kept separate — it is the exception tipo for delegados and does not
    # participate in regular relation groups unless explicitly needed.
    # TipoLiquidacion.INSPECCION_OBRA: "IO",
}


def generar_relacion_key(
    tipo_liquidacion: str,
    tipo_tramite: str | None = None,
) -> str:
    """
    Generate a relacion_key for LiquidacionRelacionMiembro.

    Args:
        tipo_liquidacion: A TipoLiquidacion enum value (e.g., "EDIFICACION").
        tipo_tramite: Optional TipoTramiteEdificaciones value (e.g., "OBRA_NUEVA").
                      Only used for EDIFICACION tipo to produce "EDIFICACION-OBRA_NUEVA" style keys.
                      Full tipo_tramite code is preserved — no short forms.

    Returns:
        str: The relation key (e.g., "EDIFICACION-OBRA_NUEVA", "HABILITACION_URBANA", "MECANICA_SUELOS", "TALUDES").

    Raises:
        ValueError: If tipo_liquidacion is not a known TipoLiquidacion value.

    Examples:
        generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA)  # "EDIFICACION-OBRA_NUEVA"
        generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.DEMOLICION)  # "EDIFICACION-DEMOLICION"
        generar_relacion_key(TipoLiquidacion.EDIFICACION)               # "EDIFICACION"
        generar_relacion_key(TipoLiquidacion.HABILITACION_URBANA)      # "HABILITACION_URBANA"
        generar_relacion_key(TipoLiquidacion.MECANICA_SUELOS)          # "MECANICA_SUELOS"
        generar_relacion_key(TipoLiquidacion.TALUDES)                 # "TALUDES"
        generar_relacion_key(TipoLiquidacion.IMPACTO_VIAL)             # "IMPACTO_VIAL"
    """
    if tipo_liquidacion not in _TIPO_BASE_KEY:
        raise ValueError(
            f"tipo_liquidacion '{tipo_liquidacion}' is not supported for relacion_key mapping. "
            f"Supported values: {list(_TIPO_BASE_KEY.keys())}"
        )

    base_key = _TIPO_BASE_KEY[tipo_liquidacion]

    if tipo_liquidacion == TipoLiquidacion.EDIFICACION and tipo_tramite:
        # Preserve full tipo_tramite code — no short forms.
        return f"{base_key}-{tipo_tramite}"

    return base_key
