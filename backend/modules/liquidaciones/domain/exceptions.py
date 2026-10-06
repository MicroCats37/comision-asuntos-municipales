"""
Excepciones de dominio para Liquidaciones.
"""
from core.exceptions import NotFoundError, ConflictError, BusinessError


class LiquidacionNotFoundError(NotFoundError):
    """Excepción cuando una liquidación no existe."""
    pass


class ProyectoNotFoundError(NotFoundError):
    """Excepción cuando un proyecto no existe."""
    pass


class RevisionNotFoundError(NotFoundError):
    """Excepción cuando una revisión no existe."""
    pass


class LiquidacionYaExisteError(ConflictError):
    """Excepción cuando ya existe una liquidación para el mismo proyecto y número de revisión."""
    pass


class MaximoRevisionAlcanzadoError(BusinessError):
    """Excepción cuando se alcanzó el máximo de revisiones permitidas."""
    pass


class RevisionNoHabilitadaError(BusinessError):
    """Excepción cuando una revisión no está habilitada/vigente."""
    pass


class PrimeraRevisionYaExisteError(ConflictError):
    """Excepción cuando ya existe una primera revisión para el proyecto."""
    pass


class TipoLiquidacionInvalidoError(BusinessError):
    """Excepción cuando se intenta crear una revisión sobre una liquidación que no es de edificaciones."""
    pass


class EspecialidadesGrupoNoEncontradoError(BusinessError):
    """Excepción cuando no se encuentra un grupo de especialidades vigente para la fecha actual."""
    pass


class EspecialidadesSetInvalidoError(BusinessError):
    """Excepción cuando el conjunto de especialidades de las revisiones seleccionadas no coincide exactamente con el grupo vigente."""
    pass


class RevisionesMultipleError(BusinessError):
    """Excepción cuando se intenta crear una nueva revisión con más de una revisión (actualmente se permite exactamente una)."""
    pass


class RevisionIdsInvalidosError(BusinessError):
    """Excepción cuando uno o más IDs en revisiones_ids no corresponden a ninguna TarifaLiquidacionBase."""
    pass
