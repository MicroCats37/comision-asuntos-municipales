"""
Shared vigencia-overlap validation for orchestrators.
Validation lives in the orchestrator layer (core services are pure ORM).
"""
from ninja.errors import HttpError


def validar_sin_solapamiento(records, contexto: str) -> None:
    """Raises HttpError(400) if more than one vigente record exists (overlap)."""
    if len(records) > 1:
        raise HttpError(
            400,
            f"Solapamiento de vigencias en {contexto}: {len(records)} registros vigentes en la fecha. Revisar la base de datos."
        )


def validar_tarifa_unica_por_base(tarifas, tipo_liquidacion: str) -> None:
    """Raises HttpError(400) if any base has != 1 TarifaPorcentajeObra child."""
    base_children: dict[str, list] = {}
    for child in tarifas:
        base_id = str(child.tarifa_base_id)
        base_children.setdefault(base_id, []).append(child.id)
    for base_id, child_ids in base_children.items():
        if len(child_ids) != 1:
            raise HttpError(
                400,
                f"Data inconsistency: TarifaLiquidacionBase '{base_id}' has {len(child_ids)} "
                f"TarifaPorcentajeObra children (expected exactly 1) for tipo={tipo_liquidacion}. "
                f"Manual cleanup required in admin before proceeding."
            )
