"""
ConsultaPresenter — transforma resultados de consulta externa a esquemas HTTP.

Transforma SunatInstitucionResult y ReniecPersonaResult a schemas de respuesta HTTP.
"""

from modules.entidades.domain.results import SunatInstitucionResult, ReniecPersonaResult
from modules.entidades.presentation.schemas.consulta_schemas import (
    InstitucionSunatOut,
    PersonaReniecOut,
)


class ConsultaPresenter:
    """
    Transforma objetos de resultado de consulta externa a esquemas de respuesta HTTP.

    Patrón: Controller → Orchestrator → Presenter → HTTP Schema
    """

    @staticmethod
    def present_sunat(result: SunatInstitucionResult) -> InstitucionSunatOut:
        """
        Transforma el resultado de consulta SUNAT a esquema HTTP.

        Args:
            result: SunatInstitucionResult del orchestrator

        Returns:
            InstitucionSunatOut schema para respuesta HTTP
        """
        return InstitucionSunatOut(
            ruc=result.ruc,
            razon_social=result.razon_social,
            nombre_comercial=result.nombre_comercial,
            estado=result.estado,
            tipo_contribuyente=result.tipo_contribuyente,
            direccion=result.direccion,
            departamento=result.departamento,
            provincia=result.provincia,
            distrito=result.distrito,
        )

    @staticmethod
    def present_reniec(result: ReniecPersonaResult) -> PersonaReniecOut:
        """
        Transforma el resultado de consulta RENIEC a esquema HTTP.

        Args:
            result: ReniecPersonaResult del orchestrator

        Returns:
            PersonaReniecOut schema para respuesta HTTP
        """
        return PersonaReniecOut(
            dni=result.dni,
            nombres=result.nombres,
            apellidos=result.apellidos,
            nombre_completo=result.nombre_completo,
            genero=result.genero,
            fecha_nacimiento=result.fecha_nacimiento,
            direccion=result.direccion,
            ubigeo=result.ubigeo,
        )