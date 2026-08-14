"""
LiquidacionMecanicaSuelosOrchestrator — sync facade for Mecanica de Suelos.

Thin sync facade. Validates input and delegates to Core/Flujo for calculation.
"""
import uuid
from typing import List
from injector import inject
from ninja.errors import HttpError
from django.core.exceptions import ObjectDoesNotExist

from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_metro_cuadrado_core_service import (
    LiquidacionPorMetroCuadradoCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionM2Result
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_mecanica_suelos_flujo import (
    LiquidacionMecanicaSuelosFlujo,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_mecanica_suelos_schemas import (
    LiquidacionMecanicaSuelosInput,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.mecanica_suelos_primera_revision_data import (
    MecanicaSuelosPrimeraRevisionData,
    LiquidacionEspecificaMecanicaSuelosData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.mecanica_suelos_primera_revision_result import (
    MecanicaSuelosPrimeraRevisionResult,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    LiquidacionGeneralData,
    ProyectoData,
    EntidadData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_m2_data import (
    DatosM2,
    TarifaM2,
)
from modules.liquidaciones.domain.exceptions import LiquidacionNotFoundError


class LiquidacionMecanicaSuelosOrchestrator:
    """
    Sync facade for Mecanica de Suelos liquidacion.

    Responsibilities:
    - Input validation (area_solicitada > 0)
    - Delegates to M2 Core service for calculation
    """

    @inject
    def __init__(
        self,
        m2_core_service: LiquidacionPorMetroCuadradoCoreService,
        general_core_service: LiquidacionGeneralCoreService,
        flujo: LiquidacionMecanicaSuelosFlujo,
    ):
        self.m2_core_service = m2_core_service
        self.general_core_service = general_core_service
        self.flujo = flujo

    def crear_primera_revision_proceso(
        self,
        usuario_id: int,
        payload_in: LiquidacionMecanicaSuelosInput,
    ) -> MecanicaSuelosPrimeraRevisionResult:
        """
        Valida y orquesta la creacion de Mecanica de Suelos (Primera Revision).
        """
        area = payload_in.liquidacion_especifica.datos.area_solicitada
        if area <= 0:
            raise HttpError(400, "area_solicitada debe ser mayor a 0")

        # Calculate and clamp M2 cotizacion (same pattern as cotizar_proceso)
        cotizacion = self.m2_core_service.calcular_cotizacion_m2(
            tipo_liquidacion=TipoLiquidacion.MECANICA_SUELOS,
            area_solicitada=area,
            tarifa_m2_id=str(payload_in.liquidacion_especifica.tarifa.tarifa_m2_id),
        )

        # Apply min/max clamping (Orchestrator is the ONLY place this logic lives)
        if cotizacion.subtotal < cotizacion.minimo:
            cotizacion.subtotal = cotizacion.minimo
            cotizacion.total = cotizacion.minimo
        elif cotizacion.maximo is not None and cotizacion.subtotal > cotizacion.maximo:
            cotizacion.subtotal = cotizacion.maximo
            cotizacion.total = cotizacion.maximo

        # Mapear Presentation Schema -> Domain DTO (with pre-clamped cotizacion)
        domain_data = MecanicaSuelosPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(payload_in.liquidacion_general.municipalidad_id),
                expediente=payload_in.liquidacion_general.expediente,
                observacion=payload_in.liquidacion_general.observacion,
                proyecto=ProyectoData(
                    denominacion=payload_in.liquidacion_general.proyecto.denominacion,
                    nombre_propietario=payload_in.liquidacion_general.proyecto.nombre_propietario,
                    direccion=payload_in.liquidacion_general.proyecto.direccion,
                    distrito_id=str(payload_in.liquidacion_general.proyecto.distrito_id),
                    entidad_razon_social=payload_in.liquidacion_general.proyecto.entidad.razon_social,
                    entidad=EntidadData(
                        tipo_documento=payload_in.liquidacion_general.proyecto.entidad.tipo_documento,
                        numero_documento=payload_in.liquidacion_general.proyecto.entidad.numero_documento,
                    )
                )
            ),
            liquidacion_especifica=LiquidacionEspecificaMecanicaSuelosData(
                datos=DatosM2(area_solicitada=area),
                tarifa=TarifaM2(tarifa_m2_id=str(payload_in.liquidacion_especifica.tarifa.tarifa_m2_id)),
            ),
            cotizacion=cotizacion,
        )

        response = self.flujo.ejecutar_primera_revision(usuario_id=usuario_id, data=domain_data)
        
        return response

    def cotizar_proceso(
        self,
        area_solicitada: float,
        tarifa_m2_id: str,
    ) -> CotizacionM2Result:
        """
        Validates area and executes quote calculation with min/max clamping.
        """
        if area_solicitada <= 0:
            raise HttpError(400, "area_solicitada must be greater than 0")

        response = self.m2_core_service.calcular_cotizacion_m2(
            tipo_liquidacion=TipoLiquidacion.MECANICA_SUELOS,
            area_solicitada=area_solicitada,
            tarifa_m2_id=tarifa_m2_id,
        )

        # Apply min/max clamping after getting raw data from Core
        if response.subtotal < response.minimo:
            response.subtotal = response.minimo
            response.total = response.minimo
        elif response.maximo is not None and response.subtotal > response.maximo:
            response.subtotal = response.maximo
            response.total = response.maximo

        return response

    def obtener_tarifas_vigentes_proceso(
        self,
    ) -> tuple[TarifaPorMetroCuadrado, DerechoPorMetroCuadrado]:
        """
        Fetches currently active M2 tariff and derecho for Mecanica de Suelos.
        Returns (tarifa, derecho) tuple.
        """
        tarifa = self.m2_core_service.get_tarifa_m2_vigente(
            tipo_liquidacion=TipoLiquidacion.MECANICA_SUELOS,
        )
        derecho = self.m2_core_service.get_derecho_minimo_m2_vigente()
        return (tarifa, derecho)

    def listar_liquidaciones(
        self, page: int, page_size: int,
        municipalidad_id=None,
        propietario=None,
        razon_social=None,
        creador_username=None,
        fecha_desde=None,
        fecha_hasta=None,
        numero=None,
        numero_revision=None,
    ) -> tuple[List[MecanicaSuelosPrimeraRevisionResult], int]:
        """
        Returns paginated MecanicaSuelosPrimeraRevisionResult list.
        Applies pagination defaults/boundaries, iterates ORM objects to build domain DTOs.
        Returns (List[MecanicaSuelosPrimeraRevisionResult], total_count).
        """
        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.general_core_service.list_liquidaciones_ms_paginated(
            page=page,
            page_size=page_size,
            municipalidad_id=municipalidad_id,
            propietario=propietario,
            razon_social=razon_social,
            creador_username=creador_username,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero=numero,
            numero_revision=numero_revision,
        )

        # Build MecanicaSuelosPrimeraRevisionResult domain DTOs from ORM objects
        domain_results = []
        for lg in orm_objects:
            domain_results.append(self._build_ms_result(lg))

        return domain_results, total

    def _build_ms_result(self, lg) -> MecanicaSuelosPrimeraRevisionResult:
        """
        Maps a LiquidacionGeneral ORM object to MecanicaSuelosPrimeraRevisionResult domain DTO.
        """
        from modules.liquidaciones.domain.results.liquidacion_especifico.mecanica_suelos_primera_revision_result import (
            LiquidacionEspecificaMecanicaSuelosResult,
        )
        from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
            LiquidacionGeneralResult,
            EntidadResult,
            ProyectoResult,
            UsuarioCreadorResult,
            MunicipalidadResult,
            IgvResult,
            UitResult,
            DistritoResult,
            ProvinciaResult,
            DepartamentoResult,
            TipoLiquidacionResult,
        )
        from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_m2_result import (
            LiquidacionM2Result,
        )

        proyecto = lg.proyecto

        # La razon social/tipo/numero viven DENORMALIZADOS en Proyecto
        # (el modelo Entidad no tiene razon_social). Usar siempre los del proyecto.
        ent_tipo = proyecto.entidad_tipo_documento if hasattr(proyecto, 'entidad_tipo_documento') else None
        ent_numero = proyecto.entidad_numero_documento if hasattr(proyecto, 'entidad_numero_documento') else None
        ent_razon = proyecto.entidad_razon_social if hasattr(proyecto, 'entidad_razon_social') else None

        # Build distrito objeto (con provincia/departamento)
        distrito_result = None
        if getattr(proyecto, "distrito_id", None):
            distrito = proyecto.distrito
            if distrito:
                distrito_result = DistritoResult(
                    id=str(distrito.id),
                    nombre=distrito.nombre,
                    ubigeo=getattr(distrito, "ubigeo", None),
                    provincia=(
                        ProvinciaResult(
                            id=str(distrito.provincia.id),
                            nombre=distrito.provincia.nombre,
                        )
                        if distrito.provincia
                        else None
                    ),
                    departamento=(
                        DepartamentoResult(
                            id=str(distrito.provincia.departamento.id),
                            nombre=distrito.provincia.departamento.nombre,
                        )
                        if distrito.provincia and distrito.provincia.departamento
                        else None
                    ),
                )

        general_result = LiquidacionGeneralResult(
            id=str(lg.id),
            municipalidad=MunicipalidadResult(
                id=str(lg.municipalidad.id),
                codigo=lg.municipalidad.codigo,
                nombre=lg.municipalidad.nombre,
            ),
            usuario_creador=UsuarioCreadorResult(
                id=str(lg.usuario_creador.id) if lg.usuario_creador else "00000000-0000-0000-0000-000000000000",
                nombres=getattr(lg.usuario_creador, "nombres", None),
                apellidos=getattr(lg.usuario_creador, "apellidos", None),
                email=getattr(lg.usuario_creador, "email", None),
                dni=getattr(lg.usuario_creador, "dni", None),
                username=getattr(lg.usuario_creador, "username", None),
            ),
            fecha_registro=lg.fecha_registro.isoformat() if lg.fecha_registro else "",
            expediente=lg.expediente or "",
            observacion=lg.observacion,
            numero_revision=lg.numero_revision,
            sub_total=float(lg.sub_total) if lg.sub_total else 0.0,
            total=float(lg.total) if lg.total else 0.0,
            retencion=lg.retencion,
            igv=(
                IgvResult(
                    id=str(lg.igv_id.id),
                    valor=float(lg.igv_id.valor),
                    periodo_inicio=lg.igv_id.periodo_inicio.isoformat() if lg.igv_id.periodo_inicio else None,
                )
                if lg.igv_id
                else None
            ),
            uit=(
                UitResult(
                    id=str(lg.uit_id.id),
                    valor=float(lg.uit_id.valor),
                    periodo_inicio=lg.uit_id.periodo_inicio.isoformat() if lg.uit_id.periodo_inicio else None,
                )
                if lg.uit_id
                else None
            ),
            proyecto=ProyectoResult(
                id=str(proyecto.id),
                denominacion=proyecto.denominacion,
                nombre_propietario=proyecto.nombre_propietario or "",
                direccion=proyecto.direccion or "",
                distrito=distrito_result,
                entidad=EntidadResult(
                    tipo_documento=ent_tipo or "",
                    numero_documento=ent_numero or "",
                    razon_social=ent_razon or "",
                ) if (ent_tipo or ent_numero or ent_razon) else None,
            ),
            tipo_liquidacion=(
                TipoLiquidacionResult(
                    codigo=lg.tipo_liquidacion.codigo,
                    nombre=lg.tipo_liquidacion.nombre,
                )
                if lg.tipo_liquidacion
                else None
            ),
        )

        # Get MS specific data (OneToOne from LiquidacionGeneral)
        mecanica_suelos = lg.mecanica_suelos
        m2 = lg.liquidacion_m2.all()[0] if lg.liquidacion_m2.exists() else None

        # Build LiquidacionEspecificaMecanicaSuelosResult
        especifica_result = LiquidacionEspecificaMecanicaSuelosResult(
            id=str(mecanica_suelos.id),
            numero=mecanica_suelos.numero,
        )

        # Build LiquidacionM2Result from prefetched liquidacion_m2
        tipo_result = LiquidacionM2Result(
            id=str(m2.id),
            area_m2=float(m2.area_m2) if m2.area_m2 else 0.0,
            costo_por_m2=float(m2.costo_por_m2) if m2.costo_por_m2 else 0.0,
            derecho_minimo=float(m2.derecho_minimo) if m2.derecho_minimo else 0.0,
            derecho_maximo=float(m2.derecho_maximo) if m2.derecho_maximo else None,
            derecho_aplicado_id=str(m2.derecho.id) if m2.derecho else "",
            tarifa_aplicada_id=str(m2.tarifa_aplicada.id) if m2.tarifa_aplicada else "",
        )

        return MecanicaSuelosPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=especifica_result,
            liquidacion_tipo=tipo_result,
        )

    def obtener_liquidacion(self, liquidacion_id: uuid.UUID) -> MecanicaSuelosPrimeraRevisionResult:
        """
        Returns a single MecanicaSuelosPrimeraRevisionResult for Mecánica de Suelos by UUID.
        Raises LiquidacionNotFoundError if not found.
        """
        try:
            lg = self.general_core_service.get_liquidacion_ms_by_id(liquidacion_id)
            return self._build_ms_result(lg)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError(f"Liquidación {liquidacion_id} no encontrada")
