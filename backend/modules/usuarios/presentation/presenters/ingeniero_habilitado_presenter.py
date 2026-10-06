"""
IngenieroHabilitadoPresenter — transforma IngenieroHabilitadoResult a esquema HTTP IngenieroHabilitadoOut.

Cumple con el contrato de arquitectura (sección 4.9: presenters).
"""
from modules.usuarios.domain.schemas.ingeniero_habilitado_schemas import IngenieroHabilitadoResult
from modules.usuarios.presentation.schemas.ingeniero_habilitado_schemas import IngenieroHabilitadoOut


class IngenieroHabilitadoPresenter:
    """
    Presenter para transformación de resultados de dominio a esquemas HTTP.

    Responsabilidad: transformar explícitamente IngenieroHabilitadoResult
    (dominio completo) → IngenieroHabilitadoOut (respuesta HTTP simplificada para frontend).
    """

    @staticmethod
    def _build_nombres(nombre1: str, nombre2: str | None) -> str:
        """
        Construye el campo nombres combinando nombre1 + nombre2.

        Args:
            nombre1: Primer nombre
            nombre2: Segundo nombre (puede ser None o vacío)

        Returns:
            Nombres combinados sin espacios extra
        """
        parts = [p.strip() for p in [nombre1, nombre2] if p and p.strip()]
        return " ".join(parts) if parts else ""

    @staticmethod
    def _build_apellidos(paterno: str, materno: str) -> str:
        """
        Construye el campo apellidos combinando paterno + materno.

        Args:
            paterno: Apellido paterno
            materno: Apellido materno

        Returns:
            Apellidos combinados sin espacios extra
        """
        parts = [p.strip() for p in [paterno, materno] if p and p.strip()]
        return " ".join(parts) if parts else ""

    @staticmethod
    def present(result: IngenieroHabilitadoResult) -> IngenieroHabilitadoOut:
        """
        Transforma IngenieroHabilitadoResult (dominio) a IngenieroHabilitadoOut (HTTP simplificado).

        Mapeo:
        - cip → cip
        - nombre1 + nombre2 → nombres (trim spaces, ignore null/empty)
        - paterno + materno → apellidos (trim spaces, ignore null/empty)
        - condicion == '1' → habilitado (bool)
        - capitulo.descripcion → capitulo (string)

        Args:
            result: IngenieroHabilitadoResult del orchestrator

        Returns:
            IngenieroHabilitadoOut listo para success_response()
        """
        # Extraer descripción del capítulo como string
        capitulo_desc = None
        if result.capitulo and result.capitulo.descripcion:
            capitulo_desc = result.capitulo.descripcion.strip()

        return IngenieroHabilitadoOut(
            cip=result.cip,
            nombres=IngenieroHabilitadoPresenter._build_nombres(result.nombre1, result.nombre2),
            apellidos=IngenieroHabilitadoPresenter._build_apellidos(result.paterno, result.materno),
            habilitado=result.habilitado,
            capitulo=capitulo_desc,
        )