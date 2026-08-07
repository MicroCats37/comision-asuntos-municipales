"""
Domain results package — complex internal return DTOs.

Results are internal DTOs that the orchestrator returns to the controller.
They are NOT exposed directly via HTTP — presenters transform them to Out schemas.

Results inherit from Pydantic BaseModel (not BaseSchema).
"""
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionM2Result

__all__ = [
    "CotizacionM2Result",
]
