"""
Domain results package — DTOs internos para Finanzas.

Results heredan de pydantic BaseModel (no BaseSchema).
"""
from modules.finanzas.domain.results.recibo_honorario_result import CalculoHonorarioResult
from modules.finanzas.domain.results.rh_inspector_mensual_result import (
    RHInspectorCotizarItemResult,
    RHInspectorCotizarResult,
    RHInspectorTotalesResult,
)
from modules.finanzas.domain.results.rh_inspector_candidatos_result import (
    InspectorCandidataItemResult,
    InspectorCandidatosResult,
)
from modules.finanzas.domain.results.rh_delegado_mensual_result import (
    RHDelegadoCotizarItemResult,
    RHDelegadoCotizarResult,
    RHDelegadoTotalesResult,
)

__all__ = [
    "CalculoHonorarioResult",
    "RHInspectorCotizarItemResult",
    "RHInspectorCotizarResult",
    "RHInspectorTotalesResult",
    "InspectorCandidataItemResult",
    "InspectorCandidatosResult",
    "RHDelegadoCotizarItemResult",
    "RHDelegadoCotizarResult",
    "RHDelegadoTotalesResult",
]
