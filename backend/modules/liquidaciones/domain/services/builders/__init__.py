"""
Builders — constructores de DTOs de resultado para la capa de dominio.

Cada builder encapsula la lógica de construcción de un DTO de salida,
separándola del flujo que coordina los pasos del caso de uso.
"""
from .liquidacion_edificaciones_result_builder import LiquidacionEdificacionesResultBuilder

__all__ = ["LiquidacionEdificacionesResultBuilder"]
