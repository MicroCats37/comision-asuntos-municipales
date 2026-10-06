"""
LiquidacionGeneralOrchestrator — fachada síncrona para listado y actualización de liquidaciones generales.

Fachada síncrona delgada. Valida entrada y delega a Core para operaciones ORM.
"""
import math
from typing import List, Optional
import uuid
from injector import inject

from core.exceptions import ConflictError, NotFoundError
from ninja.errors import HttpError
from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
    LiquidacionRelacionCoreService,
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
    ContactoResult,
)
from core.pagination import PaginatedData


class LiquidacionGeneralOrchestrator:
    """
    Fachada síncrona para listado de liquidaciones generales.

    Responsabilidades:
    - Validación de entrada (límites de paginación)
    - Delega al servicio Core las operaciones ORM
    - Mapea objetos ORM a Resultados de dominio
    """

    @inject
    def __init__(
        self,
        general_core_service: LiquidacionGeneralCoreService,
        relacion_core_service: LiquidacionRelacionCoreService,
    ):
        self.general_core_service = general_core_service
        self.relacion_core_service = relacion_core_service

    def listar_liquidaciones_generales(
        self,
        page: int,
        page_size: int,
        tipo=None,
        documento=None,
        razon_social=None,
        propietario=None,
        expediente=None,
        nombre_propietario=None,
        direccion=None,
    ) -> tuple[List[LiquidacionGeneralResult], int]:
        """
        Retorna lista paginada de LiquidacionGeneralResult.
        Aplica límites de paginación, itera objetos ORM para construir DTOs de dominio.
        Retorna (List[LiquidacionGeneralResult], total_count).
        """
        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.general_core_service.list_liquidaciones_generales_paginated(
            page=page,
            page_size=page_size,
            tipo=tipo,
            documento=documento,
            razon_social=razon_social,
            propietario=propietario,
            expediente=expediente,
            nombre_propietario=nombre_propietario,
            direccion=direccion,
        )

        # Batch resolve codigo_cta for all tipo_liquidacion.codigos present in this page
        tipo_codigos = list({
            lg.tipo_liquidacion.codigo
            for lg in orm_objects
            if lg.tipo_liquidacion
        })
        codigo_cta_map = self.general_core_service.get_codigo_cta_map(tipo_codigos)

        # Construir DTOs de dominio LiquidacionGeneralResult a partir de objetos ORM
        domain_results: List[LiquidacionGeneralResult] = []
        for lg in orm_objects:
            codigo_cta = codigo_cta_map.get(lg.tipo_liquidacion.codigo) if lg.tipo_liquidacion else None
            domain_results.append(self._build_general_result(lg, codigo_cta))

        return domain_results, total

    def _build_general_result(self, lg, codigo_cta: Optional[str] = None) -> LiquidacionGeneralResult:
        """
        Mapea un objeto ORM LiquidacionGeneral a un DTO de dominio LiquidacionGeneralResult.
        """
        proyecto = lg.proyecto

        # La razon social/tipo/numero viven DENORMALIZADOS en Proyecto
        ent_tipo = proyecto.entidad_tipo_documento if hasattr(proyecto, 'entidad_tipo_documento') else None
        ent_numero = proyecto.entidad_numero_documento if hasattr(proyecto, 'entidad_numero_documento') else None
        ent_razon = proyecto.entidad_razon_social if hasattr(proyecto, 'entidad_razon_social') else None

        # Construir objeto distrito (con provincia/departamento)
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

        # Construir contacto
        contacto_result = None
        if lg.contacto:
            contacto_result = ContactoResult(
                id=str(lg.contacto.id),
                nombres=getattr(lg.contacto, 'nombres', None),
                apellidos=getattr(lg.contacto, 'apellidos', None),
                dni=getattr(lg.contacto, 'dni', None),
                cargo=getattr(lg.contacto, 'cargo', None),
                telefono=getattr(lg.contacto, 'telefono', None),
                celular=getattr(lg.contacto, 'celular', None),
                email=getattr(lg.contacto, 'email', None),
            )

        # Construir delegados (FK adjunta liquidacion_delegados)
        delegados = self.general_core_service.build_delegados_result(lg)

        # Construir lista de comprobantes
        comprobantes = self.general_core_service.build_comprobantes_result(lg)

        return LiquidacionGeneralResult(
            id=str(lg.id),
            estado=lg.estado,
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
                nombre_propietario=proyecto.nombre_propietario or "",
                direccion=proyecto.direccion or "",
                distrito=distrito_result,
                # Denormalized entity fields (safe access via getattr)
                entidad_tipo_documento=getattr(proyecto, 'entidad_tipo_documento', None),
                entidad_numero_documento=getattr(proyecto, 'entidad_numero_documento', None),
                entidad_razon_social=getattr(proyecto, 'entidad_razon_social', None),
                entidad=EntidadResult(
                    tipo_documento=ent_tipo or "",
                    numero_documento=ent_numero or "",
                    razon_social=ent_razon or "",
                ) if (ent_tipo or ent_numero or ent_razon) else None,
            ),
            contacto=contacto_result,
            tipo_liquidacion=(
                TipoLiquidacionResult(
                    codigo=lg.tipo_liquidacion.codigo,
                    nombre=lg.tipo_liquidacion.nombre,
                )
                if lg.tipo_liquidacion
                else None
            ),
            delegados=delegados,
            codigo_cta=codigo_cta,
            comprobantes=comprobantes,
            denominacion_de_proyecto=lg.denominacion_de_proyecto,
            eliminado=lg.eliminado,
            fecha_eliminacion=lg.fecha_eliminacion.isoformat() if lg.fecha_eliminacion else None,
            motivo_eliminacion=lg.motivo_eliminacion,
            modo_calculo=lg.modo_calculo,
        )

    def obtener_liquidacion_por_id(
        self,
        liquidacion_general_id: uuid.UUID,
    ):
        """
        Retorna la liquidación general por su ID con todas sus relaciones completamente
        hidratadas, usando el builder polimórfico correspondiente al tipo de liquidación.

        Cada elemento incluye liquidacion_general, liquidacion_especifica y liquidacion_tipo
        — exactamente como los endpoints GET by ID específicos o ultimas-revisiones.

        Args:
            liquidacion_general_id: UUID de la liquidación general a obtener.

        Returns:
            DTO de dominio polimórfico (LiquidacionEspecificaPrimeraRevisionResult,
            HabilitacionUrbanaPrimeraRevisionResult, etc.).

        Raises:
            NotFoundError: Si no existe la liquidación con ese ID o fue eliminada.
            HttpError 400: Si el tipo de liquidación no es reconocido.
        """
        from modules.liquidaciones.domain.constants import TipoLiquidacion

        try:
            lg = self.general_core_service.get_liquidacion_general_by_id(liquidacion_general_id)
        except Exception:
            raise NotFoundError(
                resource="LiquidacionGeneral",
                detail=f"Liquidación con id={liquidacion_general_id} no encontrada",
            )

        codigo = lg.tipo_liquidacion.codigo if lg.tipo_liquidacion else None
        if codigo == TipoLiquidacion.EDIFICACION:
            builder = self._get_edificaciones_builder()
            return builder(lg)
        elif codigo == TipoLiquidacion.HABILITACION_URBANA:
            builder = self._get_habilitacion_urbana_builder()
            return builder(lg)
        elif codigo == TipoLiquidacion.MECANICA_SUELOS:
            builder = self._get_mecanica_suelos_builder()
            return builder(lg)
        elif codigo == TipoLiquidacion.TALUDES:
            builder = self._get_taludes_builder()
            return builder(lg)
        elif codigo == TipoLiquidacion.IMPACTO_VIAL:
            builder = self._get_impacto_vial_builder()
            return builder(lg)
        elif codigo == TipoLiquidacion.INSPECCION_OBRA:
            builder = self._get_inspeccion_obra_builder()
            return builder(lg)
        else:
            # Fallback to flat general result for unknown types
            codigo_cta_map = self.general_core_service.get_codigo_cta_map([codigo])
            codigo_cta = codigo_cta_map.get(codigo) if codigo else None
            return self._build_general_result(lg, codigo_cta)

    def listar_ultimas_liquidaciones_generales(
        self,
        page: int,
        page_size: int,
        tipo_liquidacion: list[str],
        documento=None,
        razon_social=None,
        propietario=None,
        expediente=None,
        nombre_propietario=None,
        numero=None,
        direccion=None,
    ) -> tuple[List, int]:
        """
        Retorna lista paginada de resultadospolimórficos (LiquidacionEspecificaPrimeraRevisionResult,
        HabilitacionUrbanaPrimeraRevisionResult, etc.) conteniendo únicamente la última revisión
        por cada par (proyecto, tipo_liquidacion).

        Cada elemento incluye liquidacion_general, liquidacion_especifica y liquidacion_tipo
        completamente poblados, exactamente como los endpoints GET by ID específicos.

        NOTE: tipo_liquidacion filter is MANDATORY. Raises HttpError 400 if not provided.
        """
        if not tipo_liquidacion:
            raise HttpError(400, "El filtro tipo_liquidacion es obligatorio para listar últimas revisiones.")

        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        # tipo_liquidacion is a list of codes to filter by
        orm_objects, total = self.general_core_service.list_liquidaciones_ultimas_generales_paginated(
            page=page,
            page_size=page_size,
            tipo=tipo_liquidacion,
            documento=documento,
            razon_social=razon_social,
            propietario=propietario,
            expediente=expediente,
            nombre_propietario=nombre_propietario,
            numero=numero,
            direccion=direccion,
        )

        # Build polymorphic domain DTOs from ORM objects by delegating to specific builders.
        # Circular dep规避: use object.__new__ + set minimal attrs instead of __init__.
        from modules.liquidaciones.domain.constants import TipoLiquidacion
        domain_results: List = []
        for lg in orm_objects:
            codigo = lg.tipo_liquidacion.codigo if lg.tipo_liquidacion else None
            if codigo == TipoLiquidacion.EDIFICACION:
                builder = self._get_edificaciones_builder()
                domain_results.append(builder(lg))
            elif codigo == TipoLiquidacion.HABILITACION_URBANA:
                builder = self._get_habilitacion_urbana_builder()
                domain_results.append(builder(lg))
            elif codigo == TipoLiquidacion.MECANICA_SUELOS:
                builder = self._get_mecanica_suelos_builder()
                domain_results.append(builder(lg))
            elif codigo == TipoLiquidacion.TALUDES:
                builder = self._get_taludes_builder()
                domain_results.append(builder(lg))
            elif codigo == TipoLiquidacion.IMPACTO_VIAL:
                builder = self._get_impacto_vial_builder()
                domain_results.append(builder(lg))
            elif codigo == TipoLiquidacion.INSPECCION_OBRA:
                builder = self._get_inspeccion_obra_builder()
                domain_results.append(builder(lg))
            else:
                # Fallback to flat general result for unknown types
                codigo_cta_map = self.general_core_service.get_codigo_cta_map([codigo])
                codigo_cta = codigo_cta_map.get(codigo) if codigo else None
                domain_results.append(self._build_general_result(lg, codigo_cta))

        return domain_results, total

    def _get_edificaciones_builder(self):
        """Returns a callable that builds LiquidacionEspecificaPrimeraRevisionResult for EDIFICACION."""
        from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_edificaciones_orchestrator import (
            LiquidacionEdificacionesOrchestrator,
        )
        from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_taludes_orchestrator import (
            LiquidacionTaludesOrchestrator,
        )
        from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_impacto_vial_orchestrator import (
            LiquidacionImpactoVialOrchestrator,
        )

        def build(lg):
            # Use object.__new__ to avoid circular dep via __init__
            orch = object.__new__(LiquidacionEdificacionesOrchestrator)
            orch.general_core = self.general_core_service
            orch.general_orchestrator = self
            return orch._build_edificaciones_result(lg)

        return build

    def _get_habilitacion_urbana_builder(self):
        """Returns a callable that builds HabilitacionUrbanaPrimeraRevisionResult for HABILITACION_URBANA."""
        from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_habilitacion_urbana_orchestrator import (
            LiquidacionHabilitacionUrbanaOrchestrator,
        )

        def build(lg):
            orch = object.__new__(LiquidacionHabilitacionUrbanaOrchestrator)
            orch.general_core_service = self.general_core_service
            return orch._build_hu_result(lg)

        return build

    def _get_mecanica_suelos_builder(self):
        """Returns a callable that builds MecanicaSuelosPrimeraRevisionResult for MECANICA_SUELOS."""
        from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_mecanica_suelos_orchestrator import (
            LiquidacionMecanicaSuelosOrchestrator,
        )

        def build(lg):
            orch = object.__new__(LiquidacionMecanicaSuelosOrchestrator)
            orch.general_core_service = self.general_core_service
            return orch._build_ms_result(lg)

        return build

    def _get_taludes_builder(self):
        """Returns a callable that builds LiquidacionEspecificaPrimeraRevisionResult for TALUDES."""
        from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_taludes_orchestrator import (
            LiquidacionTaludesOrchestrator,
        )

        def build(lg):
            orch = object.__new__(LiquidacionTaludesOrchestrator)
            orch.general_core = self.general_core_service
            return orch._build_taludes_result(lg)

        return build

    def _get_impacto_vial_builder(self):
        """Returns a callable that builds LiquidacionEspecificaPrimeraRevisionResult for IMPACTO_VIAL."""
        from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_impacto_vial_orchestrator import (
            LiquidacionImpactoVialOrchestrator,
        )

        def build(lg):
            orch = object.__new__(LiquidacionImpactoVialOrchestrator)
            orch.general_core = self.general_core_service
            return orch._build_iv_result(lg)

        return build

    def _get_inspeccion_obra_builder(self):
        """Returns a callable that builds InspeccionObraPrimeraRevisionResult for INSPECCION_OBRA."""
        from modules.liquidaciones.domain.services.orchestrators.liquidacion_especifico.liquidacion_inspeccion_obra_orchestrator import (
            LiquidacionInspeccionObraOrchestrator,
        )

        def build(lg):
            orch = object.__new__(LiquidacionInspeccionObraOrchestrator)
            orch.general_core = self.general_core_service
            return orch._build_io_result(lg)

        return build

    def actualizar_liquidacion_general(
        self,
        liquidacion_id: uuid.UUID,
        expediente: Optional[str] = None,
        observacion: Optional[str] = None,
        retencion: Optional[bool] = None,
        denominacion_de_proyecto: Optional[str] = None,
        contacto_data: Optional[dict] = None,
    ) -> LiquidacionGeneralResult:
        """
        Actualiza campos genéricos editables (expediente, observacion, retencion, denominacion_de_proyecto, contacto)
        de una LiquidacionGeneral.

        Regla de negocio: solo permitido cuando estado == PENDIENTE (ConflictError si PAGADA).

        Args:
            liquidacion_id: UUID de la liquidación a actualizar.
            expediente: Nuevo valor de expediente (None = sin cambio).
            observacion: Nuevo valor de observación (None = sin cambio).
            retencion: Nuevo valor de retención (None = sin cambio).
            denominacion_de_proyecto: Nuevo valor de denominación (None = sin cambio).
            contacto_data: Dict de datos upsert de Contacto.

        Returns:
            LiquidacionGeneralResult con valores actualizados.

        Raises:
            NotFoundError: Si liquidacion_id no existe.
            ConflictError: Si estado == PAGADA.
        """
        try:
            liquidacion = self.general_core_service.get_liquidacion_general_by_id(liquidacion_id)
        except Exception:
            raise NotFoundError(
                resource="LiquidacionGeneral",
                detail=f"Liquidación con id={liquidacion_id} no encontrada",
            )

        # Guard: only PENDIENTE allows updates
        if liquidacion.estado == EstadoLiquidacion.PAGADA:
            raise ConflictError(
                message="No se puede editar una liquidación en estado PAGADA. Solo las liquidaciones PENDIENTE son editables.",
                code="LIQUIDACION_PAGADA_NOT_EDITABLE",
            )

        # Update generic fields
        self.general_core_service.actualizar_liquidacion_general(
            liquidacion=liquidacion,
            expediente=expediente,
            observacion=observacion,
            retencion=retencion,
            denominacion_de_proyecto=denominacion_de_proyecto,
            contacto_data=contacto_data,
        )

        # Re-fetch with full prefetch for result building
        refreshed = self.general_core_service.get_liquidacion_general_by_id(liquidacion_id)
        codigo_cta_map = self.general_core_service.get_codigo_cta_map(
            [refreshed.tipo_liquidacion.codigo]
        )
        codigo_cta = codigo_cta_map.get(refreshed.tipo_liquidacion.codigo) if refreshed.tipo_liquidacion else None
        return self._build_general_result(refreshed, codigo_cta)

    def _can_edit_proyecto_municipalidad(self, liquidacion) -> bool:
        """
        Determina si las ediciones de proyecto y municipalidad están permitidas para una liquidación.

        Regla: editable solo cuando numero_revision == 1.
        (liquidacion_raiz y LiquidacionRelacionada fueron removidos en desarrollo.)

        Args:
            liquidacion: Instancia ORM de LiquidacionGeneral.

        Returns:
            True si las ediciones de proyecto/municipalidad están permitidas.
        """
        return liquidacion.numero_revision == 1

    def actualizar_liquidacion_general_proyecto_municipalidad(
        self,
        liquidacion_id: Optional[uuid.UUID] = None,
        municipalidad_id: Optional[uuid.UUID] = None,
        proyecto_data: Optional[dict] = None,
        expediente: Optional[str] = None,
        observacion: Optional[str] = None,
        retencion: Optional[bool] = None,
        denominacion_de_proyecto: Optional[str] = None,
        contacto_data: Optional[dict] = None,
        liquidacion: Optional["LiquidacionGeneral"] = None,
    ) -> LiquidacionGeneralResult:
        """
        Actualiza campos de proyecto/municipalidad Y opcionalmente campos genéricos en una LiquidacionGeneral.

        Este método maneja el caso donde ambos campos genéricos (expediente, etc.) Y
        campos de proyecto/municipalidad se envían en la misma solicitud PATCH.

        Reglas de negocio (impuestas aquí, no en el controller):
        - Solo permitido cuando estado == PENDIENTE (ConflictError si PAGADA).
        - Solo permitido cuando numero_revision == 1 (ConflictError si > 1).
        - Actualizaciones de Entidad: nunca mutar la fila Entidad existente.

        Args:
            liquidacion_id: UUID de la liquidacion a actualizar (ignorado si se proporciona liquidacion).
            municipalidad_id: Nuevo UUID de municipalidad (None = sin cambio).
            proyecto_data: Dict con campos opcionales de proyecto:
                - denominacion, nombre_propietario, direccion, urbanizacion, distrito_id
                - entidad: dict con tipo_documento, numero_documento, razon_social
            expediente: Nuevo valor de expediente (None = sin cambio).
            observacion: Nuevo valor de observacion (None = sin cambio).
            retencion: Nuevo valor de retencion (None = sin cambio).
            denominacion_de_proyecto: Nuevo valor de denominacion (None = sin cambio).
            contacto_data: Dict de datos upsert de Contacto (None = sin cambio).
            liquidacion: Instancia ORM de LiquidacionGeneral pre-cargada (opcional, evita re-fetch).

        Returns:
            LiquidacionGeneralResult con valores actualizados.

        Raises:
            NotFoundError: Si liquidacion_id no existe y no se proporcionó liquidacion.
            ConflictError: Si estado == PAGADA o la regla de revisión no se satisface.
        """
        # Fetch the liquidacion — use provided ORM object if given, otherwise fetch by ID
        if liquidacion is None:
            if liquidacion_id is None:
                raise ValueError("Must provide either liquidacion or liquidacion_id")
            try:
                liquidacion = self.general_core_service.get_liquidacion_general_by_id(liquidacion_id)
            except Exception:
                raise NotFoundError(
                    resource="LiquidacionGeneral",
                    detail=f"Liquidación con id={liquidacion_id} no encontrada",
                )

        # Guard: only PENDIENTE allows updates
        if liquidacion.estado == EstadoLiquidacion.PAGADA:
            raise ConflictError(
                message="No se puede editar una liquidación en estado PAGADA. Solo las liquidaciones PENDIENTE son editables.",
                code="LIQUIDACION_PAGADA_NOT_EDITABLE",
            )

        has_proyecto_municipalidad = municipalidad_id is not None or proyecto_data is not None

        # Guard: revision rule — only applies when proyecto/municipalidad are edited.
        # Generic fields remain editable while PENDIENTE regardless of revision chain.
        if has_proyecto_municipalidad and not self._can_edit_proyecto_municipalidad(liquidacion):
            raise ConflictError(
                message=(
                    "No se puede editar el proyecto o municipalidad en esta revisión. "
                    "Solo es editable cuando numero_revision == 1 y no existen liquidaciones previas."
                ),
                code="LIQUIDACION_REVISION_NO_EDITABLE",
            )

        # Update generic fields if any are provided
        has_generic = expediente is not None or observacion is not None or retencion is not None or denominacion_de_proyecto is not None or contacto_data is not None
        if has_generic:
            self.general_core_service.actualizar_liquidacion_general(
                liquidacion=liquidacion,
                expediente=expediente,
                observacion=observacion,
                retencion=retencion,
                denominacion_de_proyecto=denominacion_de_proyecto,
                contacto_data=contacto_data,
            )

        # Update municipalidad if provided
        if municipalidad_id is not None:
            self.general_core_service.actualizar_municipalidad(liquidacion, municipalidad_id)

        # Update proyecto fields if provided
        if proyecto_data:
            proyecto = liquidacion.proyecto

            # Auto-clone if the proyecto is shared (points to a different LiquidacionGeneral).
            # With OneToOneField (post-migration 0037), proyecto.liquidacion returns the single
            # related LiquidacionGeneral. The backfill migration (0036) ensured all existing
            # shared rows are already isolated, so this check is a defensive fallback.
            # Pre-migration (ForeignKey): uses proyecto.liquidaciones.count() > 1
            # Post-migration (OneToOneField): uses proyecto.liquidacion comparison
            try:
                # OneToOneField path: proyecto.liquidacion is the single related object
                other_liq = proyecto.liquidacion
                if other_liq is not None and other_liq.id != liquidacion.id:
                    cloned_proyecto = self.general_core_service.clone_proyecto_for_liquidacion(liquidacion)
                    liquidacion.proyecto = cloned_proyecto
                    liquidacion.save()
                    proyecto = cloned_proyecto
            except AttributeError:
                # ForeignKey path (pre-migration): use count-based check
                if proyecto.liquidaciones.count() > 1:
                    cloned_proyecto = self.general_core_service.clone_proyecto_for_liquidacion(liquidacion)
                    liquidacion.proyecto = cloned_proyecto
                    liquidacion.save()
                    proyecto = cloned_proyecto

            entidad_data = proyecto_data.get("entidad")

            # Update scalar proyecto fields
            self.general_core_service.actualizar_proyecto_fields(
                liquidacion=liquidacion,
                nombre_propietario=proyecto_data.get("nombre_propietario"),
                direccion=proyecto_data.get("direccion"),
                urbanizacion=proyecto_data.get("urbanizacion"),
                distrito_id=proyecto_data.get("distrito_id"),
            )

            # Handle entidad update
            if entidad_data:
                new_tipo = entidad_data.get("tipo_documento")
                new_numero = entidad_data.get("numero_documento")
                new_razon = entidad_data.get("razon_social")

                if new_numero is not None:
                    # Document number changed — find-or-create Entidad and reassign FK
                    # Use new tipo if provided, otherwise use existing
                    tipo = new_tipo if new_tipo is not None else proyecto.entidad_tipo_documento
                    entidad = self.general_core_service.find_or_create_entidad(
                        tipo_documento=tipo,
                        numero_documento=new_numero,
                    )
                    self.general_core_service.reassign_proyecto_entidad(
                        proyecto=proyecto,
                        entidad=entidad,
                    )
                    # Update razon_social snapshot if provided
                    if new_razon is not None:
                        self.general_core_service.actualizar_entidad_snapshot(
                            proyecto=proyecto,
                            entidad_razon_social=new_razon,
                        )
                else:
                    # No document number change — just update snapshot fields
                    self.general_core_service.actualizar_entidad_snapshot(
                        proyecto=proyecto,
                        entidad_tipo_documento=new_tipo,
                        entidad_numero_documento=new_numero,
                        entidad_razon_social=new_razon,
                    )

        # Re-fetch with full prefetch for result building. Specific orchestrators pass a
        # prefetched liquidacion instance, so liquidacion_id can be None here.
        refresh_id = liquidacion_id or liquidacion.id
        refreshed = self.general_core_service.get_liquidacion_general_by_id(refresh_id)

        # Resolve codigo_cta
        codigo_cta_map = self.general_core_service.get_codigo_cta_map(
            [refreshed.tipo_liquidacion.codigo]
        )
        codigo_cta = codigo_cta_map.get(refreshed.tipo_liquidacion.codigo) if refreshed.tipo_liquidacion else None

        return self._build_general_result(refreshed, codigo_cta)

    def marcar_como_pagada(self, liquidacion_id: uuid.UUID) -> LiquidacionGeneralResult:
        """
        Marca una LiquidacionGeneral como PAGADA.

        Reglas de negocio:
        - Idempotente: si ya está PAGADA, retorna éxito sin error.
        - Si está PENDIENTE, transiciona a PAGADA.
        - Sin máquina de estados compleja.

        Este método es el punto de integración para el futuro agente LiquidacionComprobante:
        después de registrar comprobante/factura, llama a este método para marcar la liquidación como pagada.

        Args:
            liquidacion_id: UUID de la liquidacion a marcar como pagada.

        Returns:
            LiquidacionGeneralResult con estado=PAGADA.

        Raises:
            NotFoundError: Si liquidacion_id no existe.
        """
        # Fetch the liquidacion
        try:
            liquidacion = self.general_core_service.get_liquidacion_general_by_id(liquidacion_id)
        except Exception:
            raise NotFoundError(
                resource="LiquidacionGeneral",
                detail=f"Liquidación con id={liquidacion_id} no encontrada",
            )

        # Idempotent: if already PAGADA, just return success with current state
        if liquidacion.estado == EstadoLiquidacion.PAGADA:
            # Re-fetch with full prefetch for consistent result building
            refreshed = self.general_core_service.get_liquidacion_general_by_id(liquidacion_id)
            codigo_cta_map = self.general_core_service.get_codigo_cta_map(
                [refreshed.tipo_liquidacion.codigo]
            )
            codigo_cta = codigo_cta_map.get(refreshed.tipo_liquidacion.codigo) if refreshed.tipo_liquidacion else None
        else:
            # Transition PENDIENTE -> PAGADA
            refreshed = self.general_core_service.marcar_estado_pagada(liquidacion)
            codigo_cta_map = self.general_core_service.get_codigo_cta_map(
                [refreshed.tipo_liquidacion.codigo]
            )
            codigo_cta = codigo_cta_map.get(refreshed.tipo_liquidacion.codigo) if refreshed.tipo_liquidacion else None

        return self._build_general_result(refreshed, codigo_cta)

    def agregar_comprobante(
        self,
        liquidacion_id: uuid.UUID,
        tipo_comprobante: str,
        serie: Optional[str] = None,
        numero: Optional[str] = None,
        fecha_emision: Optional[str] = None,
        monto: Optional[float] = None,
        motivo_reemplazo: Optional[str] = None,
    ) -> LiquidacionGeneralResult:
        """
        Agrega un nuevo comprobante a una LiquidacionGeneral, reemplazando cualquier comprobante activo existente.

        Reglas de negocio:
        - Desactiva cualquier comprobante activo existente para esta liquidación.
        - Crea un nuevo comprobante con activo=True.
        - Se ejecuta dentro de transaction.atomic() para atomicidad.

        Args:
            liquidacion_id: UUID de la liquidación.
            tipo_comprobante: Tipo de comprobante (FACTURA, BOLETA, etc.).
            serie: Serie opcional.
            numero: Número opcional.
            fecha_emision: Fecha de emisión opcional como string ISO (YYYY-MM-DD).
            monto: Monto opcional.
            motivo_reemplazo: Motivo opcional de reemplazo.

        Returns:
            LiquidacionGeneralResult con la lista de comprobantes actualizada (incluye el nuevo comprobante activo).

        Raises:
            NotFoundError: Si liquidacion_id no existe.
        """
        from django.db import transaction

        # Fetch the liquidacion
        try:
            liquidacion = self.general_core_service.get_liquidacion_general_by_id(liquidacion_id)
        except Exception:
            raise NotFoundError(
                resource="LiquidacionGeneral",
                detail=f"Liquidación con id={liquidacion_id} no encontrada",
            )

        # Create comprobante in transaction (deactivates previous + creates new)
        with transaction.atomic():
            self.general_core_service.crear_comprobante(
                liquidacion_general=liquidacion,
                tipo_comprobante=tipo_comprobante,
                serie=serie,
                numero=numero,
                fecha_emision=fecha_emision,
                monto=monto,
                motivo_reemplazo=motivo_reemplazo,
            )

        # Re-fetch with comprobantes prefetch for result building
        refreshed = self.general_core_service.get_liquidacion_general_by_id(liquidacion_id)

        # Resolve codigo_cta
        codigo_cta_map = self.general_core_service.get_codigo_cta_map(
            [refreshed.tipo_liquidacion.codigo]
        )
        codigo_cta = codigo_cta_map.get(refreshed.tipo_liquidacion.codigo) if refreshed.tipo_liquidacion else None

        return self._build_general_result(refreshed, codigo_cta)

    def eliminar_liquidacion(
        self,
        liquidacion_id: uuid.UUID,
        usuario_id: Optional[int] = None,
        motivo: Optional[str] = None,
    ) -> LiquidacionGeneralResult:
        """
        Marca una LiquidacionGeneral como eliminada/anulada.

        Reglas de negocio:
        - Establece eliminado=True, fecha_eliminacion, eliminado_por, motivo_eliminacion.
        - Pone numero=NULL en el modelo específico correspondiente según tipo_liquidacion.
        - No hace hard delete.
        - Elimina físicamente los LiquidacionRelacionMiembro asociados (grupos se retienen).

        Args:
            liquidacion_id: UUID de la liquidación a eliminar.
            usuario_id: ID del usuario que elimina (opcional, para auditabilidad).
            motivo: Motivo de la eliminación (opcional, para auditabilidad).

        Returns:
            LiquidacionGeneralResult con campos de eliminación expuestos.

        Raises:
            NotFoundError: Si liquidacion_id no existe.
        """
        # Fetch the liquidacion
        try:
            liquidacion = self.general_core_service.get_liquidacion_general_by_id(liquidacion_id)
        except Exception:
            raise NotFoundError(
                resource="LiquidacionGeneral",
                detail=f"Liquidación con id={liquidacion_id} no encontrada",
            )

        from django.db import transaction

        # Apply elimination atomically: main row + specific numero must change together.
        # Also physically delete all LiquidacionRelacionMiembro rows for this liquidacion
        # (groups are retained — other members remain; empty groups are a future concern).
        with transaction.atomic():
            self.relacion_core_service.eliminar_miembros_de_liquidacion(liquidacion)
            refreshed = self.general_core_service.eliminar_liquidacion(
                liquidacion=liquidacion,
                user_id=usuario_id,
                motivo=motivo,
            )

        # Resolve codigo_cta
        codigo_cta_map = self.general_core_service.get_codigo_cta_map(
            [refreshed.tipo_liquidacion.codigo]
        )
        codigo_cta = codigo_cta_map.get(refreshed.tipo_liquidacion.codigo) if refreshed.tipo_liquidacion else None

        return self._build_general_result(refreshed, codigo_cta)
