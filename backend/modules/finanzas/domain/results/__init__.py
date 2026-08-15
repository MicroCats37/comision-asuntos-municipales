"""
Domain results package — DTOs internos para Finanzas.

Results heredan de pydantic BaseModel (no BaseSchema).
"""
from modules.finanzas.domain.results.recibo_honorario_result import CalculoHonorarioResult

__all__ = [
    "CalculoHonorarioResult",
]
