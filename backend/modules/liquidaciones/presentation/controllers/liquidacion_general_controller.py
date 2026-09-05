"""
LiquidacionGeneralController — Single unified HTTP controller for general liquidaciones.

NO business logic. Only parses input, calls orchestrator, maps via presenter.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject
from ninja import Query, Path
from typing import Optional
import uuid

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
    LiquidacionGeneralUpdateIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.comprobante_schemas import (
    LiquidacionComprobanteCreateIn,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_general_orchestrator import (
    LiquidacionGeneralOrchestrator,
)
from modules.liquidaciones.presentation.presenters.liquidacion_general.liquidacion_general_presenter import (
    LiquidacionGeneralPresenter,
)


@api_controller("/liquidaciones/generales", tags=["Liquidaciones Generales"], permissions=[AllowAny])
class LiquidacionGeneralController:
    """
    Unified controller for general liquidaciones endpoints.
    """

    @inject
    def __init__(
        self,
        orchestrator: LiquidacionGeneralOrchestrator,
        presenter: LiquidacionGeneralPresenter,
    ):
        self.orchestrator = orchestrator
        self.presenter = presenter

    @route.get(
        "/",
        response={200: ApiResponse[PaginatedData[LiquidacionGeneralOutput]]},
    )
    def list_liquidaciones(
        self,
        page: int = Query(default=1, ge=1, description="Page number"),
        page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
        tipo: str = Query(default=None, description="Filter by tipo liquidacion codigo (e.g. EDIFICACION, HABILITACION_URBANA)"),
        documento: str = Query(default=None, description="Filter by proyecto entity numero documento (icontains)"),
        razon_social: str = Query(default=None, description="Filter by proyecto entidad razon social (icontains)"),
        propietario: str = Query(default=None, description="Filter by proyecto nombre propietario (icontains)"),
        expediente: str = Query(default=None, description="Filter by expediente numero (icontains)"),
        nombre_propietario: str = Query(default=None, description="Filter by proyecto nombre propietario — equivalent to 'propietario', both filter the same field"),
    ):
        """
        Returns a paginated list of all liquidaciones (any tipo) with optional filters.
        """
        liquidaciones, total = self.orchestrator.listar_liquidaciones_generales(
            page=page,
            page_size=page_size,
            tipo=tipo,
            documento=documento,
            razon_social=razon_social,
            propietario=propietario,
            expediente=expediente,
            nombre_propietario=nombre_propietario,
        )
        result = self.presenter.present_list(
            liquidaciones=liquidaciones,
            total=total,
            page=page,
            page_size=page_size,
        )
        return success_response(result)

    @route.get(
        "/ultimas-revisiones",
        response={200: ApiResponse[PaginatedData[LiquidacionGeneralOutput]]},
    )
    def list_ultimas_liquidaciones(
        self,
        page: int = Query(default=1, ge=1, description="Page number"),
        page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
        tipo: str = Query(default=None, description="Filter by tipo liquidacion codigo (e.g. EDIFICACION, HABILITACION_URBANA)"),
        documento: str = Query(default=None, description="Filter by proyecto entity numero documento (icontains)"),
        razon_social: str = Query(default=None, description="Filter by proyecto entidad razon social (icontains)"),
        propietario: str = Query(default=None, description="Filter by proyecto nombre propietario (icontains)"),
        expediente: str = Query(default=None, description="Filter by expediente numero (icontains)"),
        nombre_propietario: str = Query(default=None, description="Filter by proyecto nombre propietario — equivalent to 'propietario', both filter the same field"),
        numero: int = Query(default=None, ge=1, description="Filter by liquidacion numero (autoincremental per type, independent sequences across types)"),
    ):
        """
        Returns a paginated list of the latest liquidaciones (one per proyecto+tipo_liquidacion pair)
        with optional filters.
        """
        liquidaciones, total = self.orchestrator.listar_ultimas_liquidaciones_generales(
            page=page,
            page_size=page_size,
            tipo=tipo,
            documento=documento,
            razon_social=razon_social,
            propietario=propietario,
            expediente=expediente,
            nombre_propietario=nombre_propietario,
            numero=numero,
        )
        result = self.presenter.present_list(
            liquidaciones=liquidaciones,
            total=total,
            page=page,
            page_size=page_size,
        )
        return success_response(result)

    @route.patch(
        "/{liquidacion_id}",
        response={200: ApiResponse[LiquidacionGeneralOutput]},
    )
    def actualizar_liquidacion_general(
        self,
        liquidacion_id: uuid.UUID = Path(..., description="ID de la liquidación general"),
        data: LiquidacionGeneralUpdateIn = ...,
    ):
        """
        Actualiza campos editables de una LiquidacionGeneral.

        Solo editable cuando estado == PENDIENTE.
        Si estado == PAGADA, retorna 409 Conflict.

        Campos siempre editables: expediente, observacion, retencion, contacto.

        Campos condicionalmente editables (requieren revision rule):
        - municipalidad_id: solo si numero_revision == 1 y no hay liquidaciones previas
        - proyecto: campos editables solo si numero_revision == 1 y no hay liquidaciones previas

        Campos NO editables en este endpoint (deferred a otros paquetes):
        - estado (gestionado por transiciones de estado explícitas)
        - campos de cálculo tipo-específicos (PO/M2/Visitas)
        """
        # Build contacto_data if provided
        contacto_data = None
        if data.contacto is not None:
            contacto_data = {
                "nombres": data.contacto.nombres,
                "apellidos": data.contacto.apellidos,
                "dni": data.contacto.dni,
                "cargo": data.contacto.cargo,
                "telefono": data.contacto.telefono,
                "celular": data.contacto.celular,
                "email": data.contacto.email,
            }

        # Route: proyecto update needs dedicated method with revision guard.
        # municipalidad_id alone also goes through that path.
        # Generic fields (expediente, observacion, etc.) go through the general method.
        # When BOTH generic + proyecto fields are sent, we need both updates applied.
        has_proyecto_fields = data.proyecto is not None
        has_municipalidad = data.municipalidad_id is not None
        has_only_generic = not has_proyecto_fields and not has_municipalidad

        if has_only_generic:
            # General fields only — use existing method
            result = self.orchestrator.actualizar_liquidacion_general(
                liquidacion_id=liquidacion_id,
                expediente=data.expediente,
                observacion=data.observacion,
                retencion=data.retencion,
                denominacion_de_proyecto=data.denominacion_de_proyecto,
                contacto_data=contacto_data,
            )
        else:
            # Has proyecto or municipalidad fields — build proyecto_data and route
            proyecto_data = None
            if data.proyecto is not None:
                proyecto_data = {
                    "nombre_propietario": data.proyecto.nombre_propietario,
                    "direccion": data.proyecto.direccion,
                    "urbanizacion": data.proyecto.urbanizacion,
                    "distrito_id": data.proyecto.distrito_id,
                }
                if data.proyecto.entidad is not None:
                    proyecto_data["entidad"] = {
                        "tipo_documento": data.proyecto.entidad.tipo_documento,
                        "numero_documento": data.proyecto.entidad.numero_documento,
                        "razon_social": data.proyecto.entidad.razon_social,
                    }

            result = self.orchestrator.actualizar_liquidacion_general_proyecto_municipalidad(
                liquidacion_id=liquidacion_id,
                municipalidad_id=data.municipalidad_id,
                proyecto_data=proyecto_data,
                expediente=data.expediente,
                observacion=data.observacion,
                retencion=data.retencion,
                denominacion_de_proyecto=data.denominacion_de_proyecto,
                contacto_data=contacto_data,
            )

        output = self.presenter.present_liquidacion_general(result)
        return success_response(output)

    @route.post(
        "/{liquidacion_id}/marcar-pagada",
        response={200: ApiResponse[LiquidacionGeneralOutput]},
    )
    def marcar_liquidacion_como_pagada(
        self,
        liquidacion_id: uuid.UUID = Path(..., description="ID de la liquidación general"),
    ):
        """
        Marca una LiquidacionGeneral como PAGADA.

        Método idempotente: si ya está PAGADA, retorna success sin error.

        Este endpoint es el punto de integración para el futuro agente LiquidacionComprobante:
        después de registrar comprobante/factura, llama a este método para marcar la liquidación como pagada.

        Reglas de negocio:
        - Idempotente: si estado == PAGADA, retorna éxito sin error.
        - Si estado == PENDIENTE, transiciona a PAGADA.
        - No hay máquina de estados compleja.
        """
        result = self.orchestrator.marcar_como_pagada(liquidacion_id=liquidacion_id)
        output = self.presenter.present_liquidacion_general(result)
        return success_response(output)

    @route.post(
        "/{liquidacion_id}/comprobante",
        response={200: ApiResponse[LiquidacionGeneralOutput]},
    )
    def agregar_comprobante(
        self,
        liquidacion_id: uuid.UUID = Path(..., description="ID de la liquidación general"),
        data: LiquidacionComprobanteCreateIn = ...,
    ):
        """
        Agrega o reemplaza un comprobante en una LiquidacionGeneral.

        Si ya existe un comprobante activo, lo desactiva y crea uno nuevo con activo=True.
        El comprobante anterior queda en el historial (activo=False).

        Este endpoint NO maneja archivo/foto — eso queda para un futuro paquete.

        Datos básicos del comprobante:
        - tipo_comprobante (requerido): FACTURA, BOLETA, NOTA_CREDITO, NOTA_DEBITO
        - serie (opcional)
        - numero (opcional)
        - fecha_emision (opcional, YYYY-MM-DD)
        - monto (opcional)
        - motivo_reemplazo (opcional)
        """
        result = self.orchestrator.agregar_comprobante(
            liquidacion_id=liquidacion_id,
            tipo_comprobante=data.tipo_comprobante,
            serie=data.serie,
            numero=data.numero,
            fecha_emision=data.fecha_emision,
            monto=data.monto,
            motivo_reemplazo=data.motivo_reemplazo,
        )
        output = self.presenter.present_liquidacion_general(result)
        return success_response(output)
