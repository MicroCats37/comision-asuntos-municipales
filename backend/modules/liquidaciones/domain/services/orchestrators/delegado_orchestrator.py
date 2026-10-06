"""
DelegadoOrchestrator — construye DTOs de Dominio a partir de objetos ORM.

Valida entrada, llama a Core, mapea ORM → Resultado de Dominio.
"""
import uuid
import math
from datetime import date
from typing import Optional

from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.services.core.delegado.delegado_core_service import (
    DelegadoCoreService,
)
from modules.liquidaciones.domain.results.delegado.delegado_result import (
    PerfilIngenieroResult,
    DelegadoResult,
    DelegadoListResult,
    MunicipalidadesAsignadasResult,
    DelegadoMunicipalidadesResult,
    DelegadoForMunicipalidadResult,
    DelegadosPorMunicipalidadResult,
    EspecialidadResult,
    CapituloResult,
    MunicipalidadBasicResult,
    DelegadoCandidatasResult,
    DelegadoCandidatasPaginatedResult,
    CandidataResult,
    LiquidacionDelegadoDelegadoMinimal,
    TipoLiquidacionMinimalResult,
    EspecialidadRevisionResult,
    DelegadoOperatividadesVigentesResult,
    DelegadoOperacionVigenteResult,
    ComprobanteActivoMinimal,
)


class DelegadoOrchestrator:
    """
    Orchestrator para endpoints de Delegado.

    Responsabilidades:
    - Validación de entrada
    - Llama a Core para operaciones ORM
    - Construye Resultados de Dominio a partir de objetos ORM
    - Lanza HttpError si no se encuentra
    """

    @inject
    def __init__(
        self,
        core_service: DelegadoCoreService,
    ):
        self.core_service = core_service

    def _build_perfil_ingeniero_result(self, perfil) -> PerfilIngenieroResult:
        """Construye PerfilIngenieroResult a partir de un objeto ORM."""
        especialidad_result = None
        if getattr(perfil, "especialidad", None):
            especialidad_result = EspecialidadResult(
                id=str(perfil.especialidad.id),
                codigo=perfil.especialidad.codigo,
                nombre=perfil.especialidad.nombre,
            )
        capitulo_result = None
        if getattr(perfil, "capitulo", None):
            capitulo_result = CapituloResult(
                id=str(perfil.capitulo.id),
                registro_id=perfil.capitulo.registro_id,
                abreviacion=perfil.capitulo.abreviacion,
                nombre=perfil.capitulo.nombre,
            )
        return PerfilIngenieroResult(
            id=str(perfil.id),
            cip=perfil.cip or "",
            dni=perfil.dni or "",
            nombres=perfil.nombres or "",
            apellido_paterno=perfil.apellido_paterno or "",
            apellido_materno=perfil.apellido_materno or "",
            nombre_completo=perfil.nombre_completo,
            correo_personal=perfil.correo_personal,
            correo_institucional=perfil.correo_institucional,
            especialidad=especialidad_result,
            capitulo=capitulo_result,
        )

    def _build_municipalidad_asignada_result(self, dm, today: date) -> MunicipalidadesAsignadasResult:
        """Construye MunicipalidadesAsignadasResult a partir de un objeto ORM DelegadoMunicipalidad."""
        return self.core_service.build_municipalidad_asignada_result(dm, today)

    def _build_delegado_result(self, delegado, today: date) -> DelegadoResult:
        """Construye DelegadoResult a partir de un objeto ORM, incluyendo municipalidades y estado."""
        municipalidades = [
            self.core_service.build_municipalidad_asignada_result(dm, today)
            for dm in delegado.municipalidades_asignadas.all()
        ]

        if not municipalidades:
            estado = "sin_asignaciones"
        elif any(m.es_vigente for m in municipalidades):
            estado = "vigente"
        else:
            estado = "sin_vigencia"

        return DelegadoResult(
            id=str(delegado.id),
            perfil_ingeniero=self._build_perfil_ingeniero_result(delegado.perfil_ingeniero),
            municipalidades=municipalidades,
            estado=estado,
        )

    def list_delegados_proceso(
        self,
        page: int = 1,
        page_size: int = 10,
        cip: Optional[str] = None,
        municipalidad_id: Optional[uuid.UUID] = None,
        capitulo_id: Optional[uuid.UUID] = None,
        especialidad_id: Optional[uuid.UUID] = None,
        estado: Optional[str] = None,
    ) -> DelegadoListResult:
        """
        Retorna lista paginada de DelegadoResult con municipalidades y estado.
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.core_service.list_delegados_paginated(
            page=page,
            page_size=page_size,
            cip=cip,
            municipalidad_id=municipalidad_id,
            capitulo_id=capitulo_id,
            especialidad_id=especialidad_id,
        )

        today = date.today()
        domain_results: list[DelegadoResult] = [
            self._build_delegado_result(d, today) for d in orm_objects
        ]

        # Filtro por estado (post-proceso porque es derivado)
        if estado:
            domain_results = [d for d in domain_results if d.estado == estado]

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return DelegadoListResult(
            items=domain_results,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def obtener_municipalidades_proceso(
        self,
        delegado_id: uuid.UUID,
    ) -> DelegadoMunicipalidadesResult:
        """
        Retorna todas las asignaciones de municipalidad de un delegado con estado de vigencia.
        Lanza HttpError 404 si no se encuentra el delegado.
        """
        delegado = self.core_service.get_delegado_by_id(delegado_id)
        if not delegado:
            raise HttpError(404, "Delegado no encontrado")

        dm_list = self.core_service.get_municipalidades_for_delegado(delegado_id)
        today = date.today()

        municipalidades_result: list[MunicipalidadesAsignadasResult] = [
            self._build_municipalidad_asignada_result(dm, today)
            for dm in dm_list
        ]

        return DelegadoMunicipalidadesResult(
            delegado_id=str(delegado.id),
            perfil_ingeniero=self._build_perfil_ingeniero_result(delegado.perfil_ingeniero),
            municipalidades=municipalidades_result,
        )

    def list_delegados_por_municipalidad_proceso(
        self,
        municipalidad_id: uuid.UUID,
        vigente: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> DelegadosPorMunicipalidadResult:
        """
        Retorna todos los delegados para una municipalidad con filtro opcional de vigencia.
        Filtro de vigencia: periodo_inicio <= today AND (periodo_fin IS NULL OR periodo_fin >= today)
        """
        # Normalizar vigente string→bool (el controller pasa el query param sin procesar)
        if isinstance(vigente, str):
            vigente = vigente.lower() == "true"

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        dm_list, total = self.core_service.get_delegados_for_municipalidad(
            municipalidad_id=municipalidad_id,
            vigente=vigente,
            page=page,
            page_size=page_size,
        )

        today = date.today()
        items: list[DelegadoForMunicipalidadResult] = []

        for dm in dm_list:
            items.append(
                self.core_service.build_delegado_for_municipalidad_result(dm, today)
            )

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        # Post-filter: when vigente=False, exclude vigentes (computed in loop above)
        if vigente is False:
            items = [i for i in items if not i.es_vigente]

        return DelegadosPorMunicipalidadResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def list_candidatas_delegado_proceso(
        self,
        cip: Optional[str] = None,
        municipalidad_id: Optional[uuid.UUID] = None,
        tipo_liquidacion_id: Optional[uuid.UUID] = None,
        tipo_delegado: Optional[str] = None,
        delegado_operacion_id: Optional[uuid.UUID] = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> DelegadoCandidatasResult:
        """
        Retorna DelegadoCandidatasResult (DTO de dominio) de liquidaciones candidatas para
        la DelegadoOperacion resuelta.

        Path 1 — SmartField (delegado_operacion_id proporcionado):
          - Resuelve DelegadoOperacion directamente por ID.
          - Valida que pertenece al cip (si se proporcionó cip).
          - Valida que esté vigente (período activo actual).
          - Usa municipalidad/especialidad/tipo de la operación para filtrar candidatas.

        Path 2 — Basado en filtros (delegado_operacion_id NO proporcionado):
          - Resuelve exactamene UNA DelegadoOperacion activa usando:
            cip + municipalidad_id + tipo_liquidacion_id + tipo_delegado + vigencia actual.
          - Lanza 404 si no se encuentra operación. Lanza 409 si múltiples operaciones coinciden.

        El especialidad_revision_id de la operación resuelta se usa internamente para filtrar candidatas.

        Args:
            cip: CIP del delegado (requerido para path basado en filtros).
            municipalidad_id: UUID de la municipalidad (requerido para path basado en filtros).
            tipo_liquidacion_id: UUID del TipoLiquidacion (requerido para path basado en filtros).
            tipo_delegado: TITULAR o ALTERNO (requerido para path basado en filtros).
            delegado_operacion_id: Opcional — si se proporciona, usa esta operación directamente.
            fecha_inicio: Filtro opcional — fecha_registro >= fecha_inicio (inclusivo).
            fecha_fin: Filtro opcional — fecha_registro <= fecha_fin (inclusivo).

        Raises:
            404 si no se encuentra operación o delegado con cip no encontrado.
            409 si múltiples operaciones coinciden (ambigüedad de configuración).
        """
        from modules.liquidaciones.domain.models.delegado import Delegado, DelegadoOperacion

        today = date.today()

        if delegado_operacion_id is not None:
            # ── Path 1: SmartField — resolve operation directly by ID ──────────
            operacion = self.core_service.get_delegado_operacion_by_id(delegado_operacion_id)
            if not operacion:
                raise HttpError(404, f"DelegadoOperacion '{delegado_operacion_id}' no encontrada")

            # If cip provided, validate operation belongs to this delegado
            if cip:
                delegado = Delegado.objects.select_related(
                    "perfil_ingeniero"
                ).filter(perfil_ingeniero__cip=cip).first()
                if not delegado:
                    raise HttpError(404, f"Delegado con CIP '{cip}' no encontrado")
                if str(operacion.delegado_id) != str(delegado.id):
                    raise HttpError(
                        400,
                        f"La operatividad no pertenece al delegado '{cip}'",
                    )
                final_delegado = delegado
            else:
                # No cip validation — get delegado from operation
                final_delegado = operacion.delegado

            # Validate operation is vigente (has current periodo)
            current_periodo = None
            for periodo in operacion.periodos.all():
                if periodo.periodo_inicio <= today and (
                    periodo.periodo_fin is None or periodo.periodo_fin >= today
                ):
                    current_periodo = periodo
                    break
            if current_periodo is None:
                raise HttpError(
                    404,
                    "La operatividad no está vigente",
                )

            # Get candidatas using the operation directly
            candidatas_tuples = self.core_service.get_candidatas_for_delegado(
                final_delegado, today,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                operacion=operacion,
            )

            delegado_dto = LiquidacionDelegadoDelegadoMinimal(
                id=str(final_delegado.id),
                cip=final_delegado.perfil_ingeniero.cip or "",
                dni=final_delegado.perfil_ingeniero.dni or "",
                nombre_completo=final_delegado.perfil_ingeniero.nombre_completo,
            )

        else:
            # ── Path 2: Filter-based — resolve operation from filters ───────────
            if not all([cip, municipalidad_id, tipo_liquidacion_id, tipo_delegado]):
                raise HttpError(
                    400,
                    "Se requiere cip, municipalidad_id, tipo_liquidacion_id y tipo_delegado, "
                    "o delegadow_operacion_id",
                )

            delegado = Delegado.objects.select_related(
                "perfil_ingeniero"
            ).filter(perfil_ingeniero__cip=cip).first()

            if not delegado:
                raise HttpError(404, f"Delegado con CIP '{cip}' no encontrado")

            # Resolve exactly one active DelegadoOperacion matching the given criteria.
            # Raises 404 if none found, 409 if more than one matches (ambiguity).
            operacion = self.core_service.resolve_delegado_operacion(
                delegado=delegado,
                municipalidad_id=municipalidad_id,
                tipo_liquidacion_id=tipo_liquidacion_id,
                tipo_delegado=tipo_delegado,
                fecha=today,
            )

            # Get candidatas filtered by the resolved operation's especialidad.
            candidatas_tuples = self.core_service.get_candidatas_for_delegado(
                delegado, today,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                operacion=operacion,
            )

            delegado_dto = LiquidacionDelegadoDelegadoMinimal(
                id=str(delegado.id),
                cip=delegado.perfil_ingeniero.cip or "",
                dni=delegado.perfil_ingeniero.dni or "",
                nombre_completo=delegado.perfil_ingeniero.nombre_completo,
            )

        # Map tipo_liquidacion.codigo -> related_name for specific OneToOne models
        _TIPO_CODIGO_TO_RELATED_NAME = {
            "EDIFICACION": "edificaciones",
            "HABILITACION_URBANA": "habilitacion_urbana",
            "MECANICA_SUELOS": "mecanica_suelos",
            "IMPACTO_VIAL": "impacto_vial",
            "TALUDES": "taludes",
            "INSPECCION_OBRA": "inspeccion_obra",
        }

        candidatas_list = []
        for liq, especialidad, tipo, op in candidatas_tuples:
            # Extract liquidacion_especifica_numero from the specific OneToOne model
            liq_especifica_numero = None
            if liq.tipo_liquidacion and liq.tipo_liquidacion.codigo:
                _related_name = _TIPO_CODIGO_TO_RELATED_NAME.get(liq.tipo_liquidacion.codigo)
                if _related_name:
                    specific = getattr(liq, _related_name, None)
                    if specific and hasattr(specific, "numero"):
                        liq_especifica_numero = specific.numero

            # Extract comprobante_activo from prefetched comprovantes
            comprobante_activo = None
            for comp in liq.comprobantes.all():
                if comp.activo:
                    comprobante_activo = ComprobanteActivoMinimal(
                        tipo_comprobante=comp.tipo_comprobante,
                        serie=comp.serie,
                        numero=comp.numero,
                        fecha_emision=comp.fecha_emision.isoformat() if comp.fecha_emision else None,
                    )
                    break

            candidatas_list.append(CandidataResult(
                id=str(liq.id),
                expediente=getattr(liq, "expediente", None),
                numero_revision=getattr(liq, "numero_revision", 1),
                sub_total=float(liq.sub_total) if getattr(liq, "sub_total", None) else None,
                total=float(liq.total) if getattr(liq, "total", None) else None,
                municipalidad_nombre=liq.municipalidad.nombre if liq.municipalidad else None,
                proyecto_denominacion=getattr(liq, "denominacion_de_proyecto", None),
                tipo_liquidacion=TipoLiquidacionMinimalResult(
                    codigo=liq.tipo_liquidacion.codigo,
                    nombre=liq.tipo_liquidacion.nombre,
                ) if liq.tipo_liquidacion else None,
                especialidad_candidata=EspecialidadRevisionResult(
                    id=str(especialidad.id),
                    nombre=especialidad.nombre,
                ),
                tipo_delegado=tipo,
                delegado_operacion_id=str(op.id),
                liquidacion_especifica_numero=liq_especifica_numero,
                comprobante_activo=comprobante_activo,
            ))

        return DelegadoCandidatasResult(
            delegado=delegado_dto,
            candidatas=candidatas_list,
            total=len(candidatas_list)
        )

    def list_candidatas_delegado_proceso_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        expediente: str | None = None,
        numero: int | None = None,
        propietario: str | None = None,
        direccion: str | None = None,
        cip: Optional[str] = None,
        municipalidad_id: Optional[uuid.UUID] = None,
        tipo_liquidacion_id: Optional[uuid.UUID] = None,
        tipo_delegado: Optional[str] = None,
        delegado_operacion_id: Optional[uuid.UUID] = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> DelegadoCandidatasPaginatedResult:
        """
        Retorna DelegadoCandidatasPaginatedResult (DTO de dominio) de liquidaciones candidatas
        para la DelegadoOperacion resuelta con paginación y filtros adicionales.

        Path 1 — SmartField (delegado_operacion_id proporcionado):
          - Resuelve DelegadoOperacion directamente por ID.
          - Valida que pertenece al cip (si se proporcionó cip).
          - Valida que esté vigente (período activo actual).
          - Usa municipalidad/especialidad/tipo de la operación para filtrar candidatas.

        Path 2 — Basado en filtros (delegado_operacion_id NO proporcionado):
          - Resuelve exactamene UNA DelegadoOperacion activa usando:
            cip + municipalidad_id + tipo_liquidacion_id + tipo_delegado + vigencia actual.
          - Lanza 404 si no se encuentra operación. Lanza 409 si múltiples operaciones coinciden.

        Filtros adicionales:
        - expediente: icontains sobre LiquidacionGeneral.expediente
        - numero: exact match sobre numero de liquidacion específica por tipo
        - propietario: icontains sobre proyecto.nombre_propietario
        - direccion: icontains sobre proyecto.direccion

        Raises:
            404 si no se encuentra operación o delegado con cip no encontrado.
            409 si múltiples operaciones coinciden (ambigüedad de configuración).
        """
        from modules.liquidaciones.domain.models.delegado import Delegado, DelegadoOperacion

        today = date.today()
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        if delegado_operacion_id is not None:
            # ── Path 1: SmartField — resolve operation directly by ID ──────────
            operacion = self.core_service.get_delegado_operacion_by_id(delegado_operacion_id)
            if not operacion:
                raise HttpError(404, f"DelegadoOperacion '{delegado_operacion_id}' no encontrada")

            if cip:
                delegado = Delegado.objects.select_related(
                    "perfil_ingeniero"
                ).filter(perfil_ingeniero__cip=cip).first()
                if not delegado:
                    raise HttpError(404, f"Delegado con CIP '{cip}' no encontrado")
                if str(operacion.delegado_id) != str(delegado.id):
                    raise HttpError(
                        400,
                        f"La operatividad no pertenece al delegado '{cip}'",
                    )
                final_delegado = delegado
            else:
                final_delegado = operacion.delegado

            # Validate operation is vigente
            current_periodo = None
            for periodo in operacion.periodos.all():
                if periodo.periodo_inicio <= today and (
                    periodo.periodo_fin is None or periodo.periodo_fin >= today
                ):
                    current_periodo = periodo
                    break
            if current_periodo is None:
                raise HttpError(
                    404,
                    "La operatividad no está vigente",
                )

            candidatas_tuples, total = self.core_service.get_candidatas_for_delegado_paginated(
                final_delegado, today,
                operacion=operacion,
                page=page,
                page_size=page_size,
                expediente=expediente,
                numero=numero,
                propietario=propietario,
                direccion=direccion,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
            )

            delegado_dto = LiquidacionDelegadoDelegadoMinimal(
                id=str(final_delegado.id),
                cip=final_delegado.perfil_ingeniero.cip or "",
                dni=final_delegado.perfil_ingeniero.dni or "",
                nombre_completo=final_delegado.perfil_ingeniero.nombre_completo,
            )

        else:
            # ── Path 2: Filter-based — resolve operation from filters ───────────
            if not all([cip, municipalidad_id, tipo_liquidacion_id, tipo_delegado]):
                raise HttpError(
                    400,
                    "Se requiere cip, municipalidad_id, tipo_liquidacion_id y tipo_delegado, "
                    "o delegadow_operacion_id",
                )

            delegado = Delegado.objects.select_related(
                "perfil_ingeniero"
            ).filter(perfil_ingeniero__cip=cip).first()

            if not delegado:
                raise HttpError(404, f"Delegado con CIP '{cip}' no encontrado")

            operacion = self.core_service.resolve_delegado_operacion(
                delegado=delegado,
                municipalidad_id=municipalidad_id,
                tipo_liquidacion_id=tipo_liquidacion_id,
                tipo_delegado=tipo_delegado,
                fecha=today,
            )

            candidatas_tuples, total = self.core_service.get_candidatas_for_delegado_paginated(
                delegado, today,
                operacion=operacion,
                page=page,
                page_size=page_size,
                expediente=expediente,
                numero=numero,
                propietario=propietario,
                direccion=direccion,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
            )

            delegado_dto = LiquidacionDelegadoDelegadoMinimal(
                id=str(delegado.id),
                cip=delegado.perfil_ingeniero.cip or "",
                dni=delegado.perfil_ingeniero.dni or "",
                nombre_completo=delegado.perfil_ingeniero.nombre_completo,
            )

        _TIPO_CODIGO_TO_RELATED_NAME = {
            "EDIFICACION": "edificaciones",
            "HABILITACION_URBANA": "habilitacion_urbana",
            "MECANICA_SUELOS": "mecanica_suelos",
            "IMPACTO_VIAL": "impacto_vial",
            "TALUDES": "taludes",
            "INSPECCION_OBRA": "inspeccion_obra",
        }

        items = []
        for liq, especialidad, tipo, op in candidatas_tuples:
            liq_especifica_numero = None
            if liq.tipo_liquidacion and liq.tipo_liquidacion.codigo:
                _related_name = _TIPO_CODIGO_TO_RELATED_NAME.get(liq.tipo_liquidacion.codigo)
                if _related_name:
                    specific = getattr(liq, _related_name, None)
                    if specific and hasattr(specific, "numero"):
                        liq_especifica_numero = specific.numero

            comprobante_activo = None
            for comp in liq.comprobantes.all():
                if comp.activo:
                    comprobante_activo = ComprobanteActivoMinimal(
                        tipo_comprobante=comp.tipo_comprobante,
                        serie=comp.serie,
                        numero=comp.numero,
                        fecha_emision=comp.fecha_emision.isoformat() if comp.fecha_emision else None,
                    )
                    break

            items.append(CandidataResult(
                id=str(liq.id),
                expediente=getattr(liq, "expediente", None),
                numero_revision=getattr(liq, "numero_revision", 1),
                sub_total=float(liq.sub_total) if getattr(liq, "sub_total", None) else None,
                total=float(liq.total) if getattr(liq, "total", None) else None,
                municipalidad_nombre=liq.municipalidad.nombre if liq.municipalidad else None,
                proyecto_denominacion=getattr(liq, "denominacion_de_proyecto", None),
                tipo_liquidacion=TipoLiquidacionMinimalResult(
                    codigo=liq.tipo_liquidacion.codigo,
                    nombre=liq.tipo_liquidacion.nombre,
                ) if liq.tipo_liquidacion else None,
                especialidad_candidata=EspecialidadRevisionResult(
                    id=str(especialidad.id),
                    nombre=especialidad.nombre,
                ),
                tipo_delegado=tipo,
                delegado_operacion_id=str(op.id),
                liquidacion_especifica_numero=liq_especifica_numero,
                comprobante_activo=comprobante_activo,
            ))

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return DelegadoCandidatasPaginatedResult(
            delegado=delegado_dto,
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def list_tipos_liquidacion_proceso(self) -> list:
        """
        Retorna todos los objetos TipoLiquidacion para el dropdown de selección.
        """
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
        return list(TipoLiquidacion.objects.all().order_by("nombre"))

    def list_operatividades_vigentes_delegado_proceso(
        self,
        cip: str,
    ) -> DelegadoOperatividadesVigentesResult:
        """
        Retorna todas las DelegadoOperacion vigentes para un delegado identificado por CIP.
        Incluye información de municipalidad, tipo_liquidacion, especialidad y período de vigencia.

        Lanza 404 si no se encuentra delegado con ese CIP.
        """
        from modules.liquidaciones.domain.models.delegado import Delegado

        delegado = Delegado.objects.select_related(
            "perfil_ingeniero"
        ).filter(perfil_ingeniero__cip=cip).first()

        if not delegado:
            raise HttpError(404, f"Delegado con CIP '{cip}' no encontrado")

        today = date.today()

        # Get all active operations with vigentes periods
        operaciones = self.core_service.get_operatividades_vigentes_delegado(
            delegado=delegado,
            fecha=today,
        )

        operatividades = []
        for op in operaciones:
            # Extract current periodo dates from the prefetched periodos
            current_periodo = None
            for periodo in op.periodos.all():
                if periodo.periodo_inicio <= today and (
                    periodo.periodo_fin is None or periodo.periodo_fin >= today
                ):
                    current_periodo = periodo
                    break

            periodo_inicio = current_periodo.periodo_inicio if current_periodo else None
            periodo_fin = current_periodo.periodo_fin if current_periodo else None

            tipo_liq_id = str(op.tipo_liquidacion_id) if op.tipo_liquidacion_id else None
            tipo_liq_codigo = op.tipo_liquidacion.codigo if op.tipo_liquidacion else None
            tipo_liq_nombre = op.tipo_liquidacion.nombre if op.tipo_liquidacion else None

            operatividades.append(DelegadoOperacionVigenteResult(
                id=str(op.id),
                municipalidad_id=str(op.municipalidad_id),
                municipalidad_nombre=op.municipalidad.nombre,
                tipo_liquidacion_id=tipo_liq_id,
                tipo_liquidacion_codigo=tipo_liq_codigo,
                tipo_liquidacion_nombre=tipo_liq_nombre,
                especialidad_id=str(op.especialidad_revision_id),
                especialidad_nombre=op.especialidad_revision.nombre,
                tipo=op.tipo,
                periodo_inicio=periodo_inicio,
                periodo_fin=periodo_fin,
            ))

        return DelegadoOperatividadesVigentesResult(
            delegado_id=str(delegado.id),
            cip=delegado.perfil_ingeniero.cip or "",
            nombre_completo=delegado.perfil_ingeniero.nombre_completo,
            operatividades=operatividades,
        )

