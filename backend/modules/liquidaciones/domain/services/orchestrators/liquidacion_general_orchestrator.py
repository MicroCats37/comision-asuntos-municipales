"""
LiquidacionGeneralOrchestrator — sync facade for general liquidacion listing and update.

Thin sync facade. Validates input and delegates to Core for ORM operations.
"""
import math
from typing import List, Optional
import uuid
from injector import inject

from core.exceptions import ConflictError, NotFoundError
from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
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
    LiquidacionPreviaResult,
    ContactoResult,
)
from core.pagination import PaginatedData


class LiquidacionGeneralOrchestrator:
    """
    Sync facade for general liquidacion listing.

    Responsibilities:
    - Input validation (pagination boundaries)
    - Delegates to Core service for ORM operations
    - Maps ORM objects to domain Results
    """

    @inject
    def __init__(
        self,
        general_core_service: LiquidacionGeneralCoreService,
    ):
        self.general_core_service = general_core_service

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
    ) -> tuple[List[LiquidacionGeneralResult], int]:
        """
        Returns paginated LiquidacionGeneralResult list.
        Applies pagination defaults/boundaries, iterates ORM objects to build domain DTOs.
        Returns (List[LiquidacionGeneralResult], total_count).
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
        )

        # Batch resolve codigo_cta for all tipo_liquidacion.codigos present in this page
        tipo_codigos = list({
            lg.tipo_liquidacion.codigo
            for lg in orm_objects
            if lg.tipo_liquidacion
        })
        codigo_cta_map = self.general_core_service.get_codigo_cta_map(tipo_codigos)

        # Build LiquidacionGeneralResult domain DTOs from ORM objects
        domain_results: List[LiquidacionGeneralResult] = []
        for lg in orm_objects:
            codigo_cta = codigo_cta_map.get(lg.tipo_liquidacion.codigo) if lg.tipo_liquidacion else None
            domain_results.append(self._build_general_result(lg, codigo_cta))

        return domain_results, total

    def _build_general_result(self, lg, codigo_cta: Optional[str] = None) -> LiquidacionGeneralResult:
        """
        Maps a LiquidacionGeneral ORM object to LiquidacionGeneralResult domain DTO.
        """
        proyecto = lg.proyecto

        # La razon social/tipo/numero viven DENORMALIZADOS en Proyecto
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

        # Build contacto
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

        # Build revisions previas
        revisiones_previas = self.general_core_service.build_revisiones_previas_result(lg)

        # Build delegados (FK adjunta liquidacion_delegados)
        delegados = self.general_core_service.build_delegados_result(lg)

        # Build comprobantes list
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
            revisiones_previas=revisiones_previas,
            delegados=delegados,
            codigo_cta=codigo_cta,
            comprobantes=comprobantes,
            denominacion_de_proyecto=lg.denominacion_de_proyecto,
        )

    def listar_ultimas_liquidaciones_generales(
        self,
        page: int,
        page_size: int,
        tipo=None,
        documento=None,
        razon_social=None,
        propietario=None,
        expediente=None,
        nombre_propietario=None,
        numero=None,
    ) -> tuple[List[LiquidacionGeneralResult], int]:
        """
        Returns paginated LiquidacionGeneralResult list containing only the latest revision
        per (proyecto, tipo_liquidacion) pair.
        Applies pagination defaults/boundaries, iterates ORM objects to build domain DTOs.
        Returns (List[LiquidacionGeneralResult], total_count).
        """
        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.general_core_service.list_liquidaciones_ultimas_generales_paginated(
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

        # Batch resolve codigo_cta for all tipo_liquidacion.codigos present in this page
        tipo_codigos = list({
            lg.tipo_liquidacion.codigo
            for lg in orm_objects
            if lg.tipo_liquidacion
        })
        codigo_cta_map = self.general_core_service.get_codigo_cta_map(tipo_codigos)

        # Build LiquidacionGeneralResult domain DTOs from ORM objects
        domain_results: List[LiquidacionGeneralResult] = []
        for lg in orm_objects:
            codigo_cta = codigo_cta_map.get(lg.tipo_liquidacion.codigo) if lg.tipo_liquidacion else None
            domain_results.append(self._build_general_result(lg, codigo_cta))

        return domain_results, total

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
        Updates editable generic fields (expediente, observacion, retencion, denominacion_de_proyecto, contacto)
        on a LiquidacionGeneral.

        Business rule: only allowed when estado == PENDIENTE (ConflictError if PAGADA).

        Args:
            liquidacion_id: UUID of the liquidacion to update.
            expediente: New expediente value (None = no change).
            observacion: New observacion value (None = no change).
            retencion: New retencion value (None = no change).
            denominacion_de_proyecto: New denominacion value (None = no change).
            contacto_data: Contacto upsert data dict.

        Returns:
            LiquidacionGeneralResult with updated values.

        Raises:
            NotFoundError: If liquidacion_id does not exist.
            ConflictError: If estado == PAGADA.
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
        Determines if proyecto and municipalidad edits are allowed for a liquidacion.

        Rule: editable only when numero_revision == 1 AND no liquidaciones_previas.

        Args:
            liquidacion: LiquidacionGeneral ORM instance.

        Returns:
            True if proyecto/municipalidad edits are allowed.
        """
        if liquidacion.numero_revision != 1:
            return False
        # Check if there are any previous revisions (liquidaciones_previas)
        has_previas = getattr(liquidacion, 'liquidaciones_previas', []).exists() if hasattr(liquidacion, 'liquidaciones_previas') else False
        return not has_previas

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
        Updates proyecto/municipalidad fields AND optionally generic fields on a LiquidacionGeneral.

        This method handles the case where both generic fields (expediente, etc.) AND
        proyecto/municipalidad fields are sent in the same PATCH request.

        Business rules (enforced here, not in controller):
        - Only allowed when estado == PENDIENTE (ConflictError if PAGADA).
        - Only allowed when numero_revision == 1 AND no liquidaciones_previas (ConflictError otherwise).
        - Entidad updates: never mutate existing Entidad row.

        Args:
            liquidacion_id: UUID of the liquidacion to update (ignored if liquidacion is provided).
            municipalidad_id: New municipalidad UUID (None = no change).
            proyecto_data: Dict with optional proyecto fields:
                - denominacion, nombre_propietario, direccion, urbanizacion, distrito_id
                - entidad: dict with tipo_documento, numero_documento, razon_social
            expediente: New expediente value (None = no change).
            observacion: New observacion value (None = no change).
            retencion: New retencion value (None = no change).
            denominacion_de_proyecto: New denominacion value (None = no change).
            contacto_data: Contacto upsert data dict (None = no change).
            liquidacion: Pre-fetched LiquidacionGeneral ORM instance (optional, avoids re-fetch).

        Returns:
            LiquidacionGeneralResult with updated values.

        Raises:
            NotFoundError: If liquidacion_id does not exist and no liquidacion provided.
            ConflictError: If estado == PAGADA or revision rule not satisfied.
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
        Marks a LiquidacionGeneral as PAGADA.

        Business rules:
        - Idempotent: if already PAGADA, returns success without error.
        - If PENDIENTE, transitions to PAGADA.
        - No complex state machine.

        This method is the integration point for the future LiquidacionComprobante agent:
        after registering comprobante/factura, it calls this method to mark the liquidation paid.

        Args:
            liquidacion_id: UUID of the liquidacion to mark as paid.

        Returns:
            LiquidacionGeneralResult with estado=PAGADA.

        Raises:
            NotFoundError: If liquidacion_id does not exist.
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
        Adds a new comprobante to a LiquidacionGeneral, replacing any existing active one.

        Business rules:
        - Deactivates any existing active comprobante for this liquidacion.
        - Creates a new comprobante with activo=True.
        - Runs inside transaction.atomic() for atomicity.

        Args:
            liquidacion_id: UUID of the liquidacion.
            tipo_comprobante: Type of comprobante (FACTURA, BOLETA, etc.).
            serie: Optional serie.
            numero: Optional numero.
            fecha_emision: Optional fecha emision as ISO string (YYYY-MM-DD).
            monto: Optional monto.
            motivo_reemplazo: Optional motivo for replacement.

        Returns:
            LiquidacionGeneralResult with the updated comprobantes list (new active comprobante included).

        Raises:
            NotFoundError: If liquidacion_id does not exist.
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
