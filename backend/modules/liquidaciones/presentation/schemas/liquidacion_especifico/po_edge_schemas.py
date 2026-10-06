"""
PO Edge input schemas — manual/edge liquidations for PO types (Edificaciones, Taludes, Impacto Vial).

Payload structure:
- liquidacion_general: same as primera-revision (municipalidad, expediente, proyecto, contacto)
- subtotal_manual: Decimal > 0 — pre-IGV subtotal distributed among specialties
- numero_revision: int in {1, 3, 5}

No tarifas, no valor_declarado — backend resolves vigente specialties and distributes subtotal.
"""
from decimal import Decimal
from ninja import Field
from core.types import BaseSchema
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralRevisionIn,
)


class POEdgeIn(BaseSchema):
    """
    Input schema for PO edge endpoints (/edge).

    Payload:
    - liquidacion_general: standard general header (same as primera-revision)
    - subtotal_manual: Decimal > 0 — pre-IGV subtotal distributed equally among vigentes specialties
    - numero_revision: int in {1, 3, 5}

    Backend resolves vigente/habilitada specialties internally, distributes subtotal equally,
    calculates IGV and total, and persists with modo_calculo=MANUAL.
    """
    liquidacion_general: LiquidacionGeneralRevisionIn
    subtotal_manual: Decimal = Field(
        ...,
        description="Subtotal pre-IGV. Must be greater than 0.",
    )
    numero_revision: int = Field(
        ...,
        ge=1,
        le=5,
        description="Revision number: 1, 3, or 5.",
    )
