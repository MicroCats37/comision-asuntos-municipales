"""
EntidadesController — controladores HTTP ligeros.

薄 — solo delega a EntidadesOrchestrator y retorna vía EntidadPresenter.
"""
import uuid
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Query
from typing import Optional

from core.responses import ApiResponse, success_response
from ..schemas.entidad_schemas import (
    EntidadInstitucionIn,
    EntidadPersonaNaturalIn,
    EntidadOut,
    EntidadUpsertResponseOut,
    DistritosResponseOut,
    MunicipalidadesResponseOut,
)
from ..presenters.entidad_presenter import EntidadPresenter
from ...domain.services.orchestrators.entidad_orchestrator import EntidadesOrchestrator


@api_controller("/entidades", tags=["Entidades"], permissions=[AllowAny])
class EntidadesController:
    """
    Controlador para Entidades.

   薄 — delega todo formatting de respuesta a EntidadPresenter.

    Endpoints:
    - POST /instituciones: Crear o actualizar institución (RUC)
    - POST /personas-naturales: Crear o actualizar persona natural (DNI)
    - GET /buscar: Buscar entidad por número de documento
    - GET /ubigeo/distritos: Listar distritos con filtros
    - GET /municipalidades: Listar municipalidades para selector
    """

    @inject
    def __init__(
        self,
        orchestrator: EntidadesOrchestrator,
        presenter: EntidadPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.post("/instituciones", response={200: ApiResponse[EntidadUpsertResponseOut]}, auth=None)
    async def crear_institucion(self, payload: EntidadInstitucionIn):
        """
        Crear o actualizar una institución (entidad con RUC).

        Si el RUC ya existe, actualiza los datos.
        Si no existe, crea una nueva institución.
        """
        result, creado = await self.orchestrator.upsert_entidad(
            tipo_documento=payload.tipo_documento,
            numero_documento=payload.numero_documento,
            razon_social=payload.razon_social,
            nombres=None,
            apellidos=None,
            nombre_comercial=payload.nombre_comercial,
            direccion=payload.direccion,
            distrito_id=payload.distrito_id,
        )
        return success_response(
            self.presenter.present_upsert(result, creado)
        )

    @route.post("/personas-naturales", response={200: ApiResponse[EntidadUpsertResponseOut]}, auth=None)
    async def crear_persona_natural(self, payload: EntidadPersonaNaturalIn):
        """
        Crear o actualizar una persona natural (entidad con DNI).

        Si el DNI ya existe, actualiza los datos.
        Si no existe, crea una nueva persona natural.
        """
        result, creado = await self.orchestrator.upsert_entidad(
            tipo_documento=payload.tipo_documento,
            numero_documento=payload.numero_documento,
            razon_social=None,
            nombres=payload.nombres,
            apellidos=payload.apellidos,
            nombre_comercial=None,
            direccion=payload.direccion,
            distrito_id=payload.distrito_id,
        )
        return success_response(
            self.presenter.present_upsert(result, creado)
        )

    @route.get("/buscar", response={200: ApiResponse[EntidadOut]}, auth=None)
    async def buscar_por_documento(self, numero_documento: str):
        """
        Buscar una entidad por su número de documento (RUC o DNI).
        """
        result = await self.orchestrator.buscar_por_documento(numero_documento)
        return success_response(
            self.presenter.present_buscar(result)
        )

    @route.get("/ubigeo/distritos", response={200: ApiResponse[DistritosResponseOut]}, auth=None)
    async def obtener_distritos(
        self,
        search: Optional[str] = Query(None, description="Texto para filtrar por nombre de distrito"),
        provincia_id: Optional[str] = Query(None, description="ID de provincia para filtrar"),
        departamento_id: Optional[str] = Query(None, description="ID de departamento para filtrar"),
    ):
        """
        Obtiene lista de distritos con filtros opcionales.

        Args:
            search: Texto para filtrar por nombre de distrito
            provincia_id: ID de provincia para filtrar
            departamento_id: ID de departamento para filtrar

        Returns:
            Lista de distritos con información de provincia y departamento
        """
        distritos = await self.orchestrator.obtener_distritos(
            search=search,
            provincia_id=provincia_id,
            departamento_id=departamento_id,
        )
        return success_response(
            self.presenter.present_distritos(distritos)
        )

    @route.get("/municipalidades", response={200: ApiResponse[list[MunicipalidadesResponseOut]]}, auth=None)
    async def obtener_municipalidades(self):
        """Obtiene lista de todas las municipalidades."""
        municipalidades = await self.orchestrator.obtener_municipalidades()
        return success_response(
            self.presenter.present_municipalidades(municipalidades)
        )
