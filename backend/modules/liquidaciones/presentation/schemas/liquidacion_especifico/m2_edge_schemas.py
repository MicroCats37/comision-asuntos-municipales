"""
M2 Edge input schemas — manual/edge liquidations for M2 types (Habilitación Urbana, Mecánica de Suelos).

Payload structure:
- liquidacion_general: same as primera-revision (municipalidad, expediente, proyecto, contacto)
- subtotal_manual: Decimal > 0 — pre-IGV subtotal
- area_m2: Decimal > 0 — area for traceability
- numero_revision: int in {1, 3, 5}

No tarifas, no costo_por_m2, no derecho — backend calculates IGV and total
from subtotal_manual and persists with modo_calculo=MANUAL.
"""
from decimal import Decimal
from ninja import Field
from core.types import BaseSchema
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralRevisionIn,
)


class M2EdgeIn(BaseSchema):
    """
    Input schema for M2 edge endpoints (/edge).

    Payload:
    - liquidacion_general: standard general header (same as primera-revision)
    - subtotal_manual: Decimal > 0 — pre-IGV subtotal
    - area_m2: Decimal > 0 — area for traceability
    - numero_revision: int in {1, 3, 5}

    Backend resolves IGV vigentes, calculates total from subtotal_manual,
    and persists with modo_calculo=MANUAL and null tarifa/derecho fields.
    """
    liquidacion_general: LiquidacionGeneralRevisionIn
    subtotal_manual: Decimal = Field(
        ...,
        description="Subtotal pre-IGV. Must be greater than 0.",
    )
    area_m2: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description="Área solicitada en metros cuadrados. Must be 0 or greater.",
    )
    numero_revision: int = Field(
        ...,
        ge=1,
        le=5,
        description="Revision number: 1, 3, or 5.",
    )
