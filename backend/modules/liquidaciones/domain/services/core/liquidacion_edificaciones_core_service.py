"""
Liquidaciones Edificaciones Service — operaciones sync.
"""
from datetime import date
from decimal import Decimal
from typing import Optional
from django.db.models import QuerySet
from django.utils import timezone

from ...models import (
    LiquidacionGeneral,
    LiquidacionEdificaciones,
    LiquidacionSnapshot,
    EdificacionesRevision,
    EdificacionesTarifa,
    Proyecto,
)
from ...schemas import VariablesFinancierasResult, EdificacionRevisionData, TarifaEdificacionData, EspecialidadData, LiquidacionEdificacionesPaginatedResult, LiquidacionEdificacionesListItem, LiquidacionSnapshotResult, RevisionVigenteResult, RevisionConTarifaData, RevisionCalculoData, CotizacionRevisionData, TarifaCalculoData
from modules.entidades.models import Municipalidad


class LiquidacionesEdificacionesService:
    """
    Servicio core sync para operaciones de Liquidaciones Edificaciones.
    NO usa transaction.atomic() internamente — el flujo lo provee si es necesario.
    """

    def _obtener_variables_financieras_vigentes(self) -> VariablesFinancierasResult:
        """Obtiene IGV y UIT vigentes. Lanza error si no están configurados."""
        from modules.finanzas.models import IGV, UIT

        igv = IGV.objects.vigente()
        uit = UIT.objects.vigente()

        if igv is None:
            raise ValueError(
                "No hay IGV vigente configurado. Ejecute: python manage.py seed_finanzas"
            )
        if uit is None:
            raise ValueError(
                "No hay UIT vigente configurada. Ejecute: python manage.py seed_finanzas"
            )

        return VariablesFinancierasResult(
            igv_valor=igv.valor,
            igv_periodo_inicio=igv.periodo_inicio,
            uit_valor=Decimal(uit.valor),
            uit_periodo_inicio=uit.periodo_inicio,
        )

    def _obtener_proyecto_por_public_id(self, public_id: str) -> Optional[Proyecto]:
        """Obtiene proyecto por public_id."""
        try:
            return Proyecto.objects.get(public_id=public_id)
        except Proyecto.DoesNotExist:
            return None

    def _obtener_liquidacion_por_id(self, liquidacion_id: str) -> Optional[LiquidacionGeneral]:
        """Obtiene liquidación por ID."""
        try:
            return LiquidacionGeneral.objects.select_related(
                'proyecto', 'proyecto__entidad', 'igv', 'uit'
            ).get(id=liquidacion_id)
        except LiquidacionGeneral.DoesNotExist:
            return None

    def _obtener_revisiones_vigencias_raw(self) -> QuerySet:
        """Obtiene todas las EdificacionesRevision vigentes (habilitadas) - QuerySet lazy."""
        return EdificacionesRevision.objects.filter(
            periodo_fin__isnull=True
        ).select_related('tarifa').prefetch_related('especialidades')

    def _obtener_revisiones_vigentes(self) -> list:
        """Materializa el QuerySet en contexto sync - obligatorio antes de sync_to_async."""
        qs = self._obtener_revisiones_vigentes_raw()
        # Materializar ANTES de retornar - el QuerySet se evalúa aquí en contexto sync
        return list(qs)

    def _obtener_revisiones_vigentes_result(self) -> list[RevisionVigenteResult]:
        """
        Obtiene todas las revisiones vigentes con sus tarifas y especialidades (devuelve result objects).

        NOTE: Con M2M especialidades, una revisión puede tener múltiples especialidades.
        Se devuelve la lista completa de especialidades para cada revisión.
        El flujo completo de cálculo (que es 1 fila = 1 cargo) no necesita expand by specialty.
        """
        from modules.liquidaciones.domain.schemas import EspecialidadBasicaResult
        revisions_list = self._obtener_revisiones_vigencias_raw()

        result = []
        for rev in revisions_list:
            # M2M: obtener todas las especialidades de la revisión
            especialidades_orm = rev.especialidades.all()
            especialidades = [
                EspecialidadBasicaResult(
                    id=esp.id,
                    nombre=esp.nombre,
                )
                for esp in especialidades_orm
            ]
            result.append(RevisionVigenteResult(
                id=str(rev.id),
                especialidades=especialidades,
                tarifa_id=str(rev.tarifa.id),
                porcentaje_liquidacion=rev.porcentaje_liquidacion,
                derecho_minimo=rev.tarifa.derecho_minimo,
                derecho_maximo=rev.tarifa.derecho_maximo,
                porcentaje_minimo_uit=rev.tarifa.porcentaje_minimo_uit,
                habilitada=rev.habilitada,
            ))
        return result

    def _obtener_revisiones_por_ids_raw(self, ids: list[str]) -> QuerySet:
        """Obtiene revisiones por lista de IDs (QuerySet lazy)."""
        return EdificacionesRevision.objects.filter(id__in=ids).select_related('tarifa').prefetch_related('especialidades')

    def _obtener_revisiones_por_ids(self, ids: list[str]) -> list[EdificacionRevisionData]:
        """Obtiene revisiones por IDs (devuelve result objects)."""
        revisions_qs = self._obtener_revisiones_por_ids_raw(ids)

        result = []
        for rev in revisions_qs:
            # M2M: obtener primera especialidad para compatibilidad
            especialidades = list(rev.especialidades.all())
            primera_esp = especialidades[0] if especialidades else None
            result.append(EdificacionRevisionData(
                id=rev.id,
                especialidad=EspecialidadData(
                    id=str(primera_esp.id) if primera_esp else None,
                    nombre=primera_esp.nombre if primera_esp else None,
                ),
                tarifa=TarifaEdificacionData(
                    id=rev.tarifa.id,
                    derecho_minimo=rev.tarifa.derecho_minimo,
                    derecho_maximo=rev.tarifa.derecho_maximo,
                    porcentaje_minimo_uit=rev.tarifa.porcentaje_minimo_uit,
                ),
                porcentaje_liquidacion=rev.porcentaje_liquidacion,
                habilitada=rev.habilitada,
            ))
        return result

    def _existe_primera_revision_proyecto(self, proyecto_id: str) -> bool:
        """Verifica si existe primera revisión para el proyecto."""
        return LiquidacionEdificaciones.objects.filter(
            liquidacion__proyecto_id=proyecto_id,
            numero_revision=1
        ).exists()

    def _existe_revision_numero_proyecto(self, proyecto_id: str, numero_revision: int) -> bool:
        """Verifica si existe una revisión con ese número para el proyecto."""
        return LiquidacionEdificaciones.objects.filter(
            liquidacion__proyecto_id=proyecto_id,
            numero_revision=numero_revision
        ).exists()

    def _generar_public_id_liquidacion_general(self) -> str:
        """
        Genera un public_id único para una LiquidacionGeneral.

        Formato: LIQ-{year}-{count:05d}

        Returns:
            public_id generado
        """
        year = timezone.now().year
        count = LiquidacionGeneral.objects.filter(
            public_id__startswith=f"LIQ-{year}-"
        ).count()
        return f"LIQ-{year}-{count + 1:05d}"

    def _generar_public_id_liquidacion_edificaciones(self) -> str:
        """
        Genera un public_id único para una LiquidacionEdificaciones.

        Formato: LIQ-EDIF-{year}-{count:05d}

        Returns:
            public_id generado
        """
        year = timezone.now().year
        count = LiquidacionEdificaciones.objects.filter(
            public_id__startswith=f"LIQ-EDIF-{year}-"
        ).count()
        return f"LIQ-EDIF-{year}-{count + 1:05d}"

    def _crear_liquidacion_general(
        self,
        proyecto: Proyecto,
        municipalidad: Municipalidad,
        valor_proyecto: Decimal,
        observacion: Optional[str],
        liquidacion_previa: Optional[LiquidacionGeneral] = None,
        valor_base_calculo: Optional[Decimal] = None,
    ) -> LiquidacionGeneral:
        """Crea una LiquidacionGeneral con la cadena de liquidaciones previas."""
        from modules.finanzas.models import IGV, UIT

        # Obtener IGV y UIT vigentes
        igv = IGV.objects.vigente()
        uit = UIT.objects.vigente()

        if igv is None:
            raise ValueError(
                "No hay IGV vigente configurado. Ejecute: python manage.py seed_finanzas"
            )
        if uit is None:
            raise ValueError(
                "No hay UIT vigente configurada. Ejecute: python manage.py seed_finanzas"
            )

        public_id = self._generar_public_id_liquidacion_general()
        # valor_base_calculo: si no se proporciona, usar valor_proyecto
        if valor_base_calculo is None:
            valor_base_calculo = valor_proyecto
        liquidacion = LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            igv=igv,
            uit=uit,
            valor_proyecto=valor_proyecto,
            valor_base_calculo=valor_base_calculo,
            observacion=observacion,
            public_id=public_id,
        )
        if liquidacion_previa:
            # Agregar tanto la inmediata previa como toda su cadena
            liquidacion.liquidaciones_previas.add(liquidacion_previa)
            for prev in liquidacion_previa.liquidaciones_previas.all():
                liquidacion.liquidaciones_previas.add(prev)
        return liquidacion

    def _crear_liquidacion_edificaciones(
        self,
        liquidacion: LiquidacionGeneral,
        numero_revision: int,
        tipo_tramite: str,
        tramite_accion: str,
        proyectistas_ids: Optional[list[str]] = None,
    ) -> LiquidacionEdificaciones:
        """Crea una LiquidacionEdificaciones."""
        public_id = self._generar_public_id_liquidacion_edificaciones()
        liq_edif = LiquidacionEdificaciones.objects.create(
            liquidacion=liquidacion,
            numero_revision=numero_revision,
            tipo_tramite=tipo_tramite,
            tramite_accion=tramite_accion,
            public_id=public_id,
        )
        if proyectistas_ids:
            from modules.liquidaciones.domain.models import Proyectista
            proyectistas = Proyectista.objects.filter(id__in=proyectistas_ids)
            for p in proyectistas:
                liq_edif.proyectistas.add(p)
        return liq_edif

    def _asociar_revisiones(
        self,
        liquidacion_edificaciones: LiquidacionEdificaciones,
        revisiones_ids: list[str],
    ) -> None:
        """Asocia revisiones a la liquidación de edificaciones."""
        revisiones = EdificacionesRevision.objects.filter(id__in=revisiones_ids)
        for rev in revisiones:
            liquidacion_edificaciones.revisiones.add(rev)

    def _crear_snapshot(
        self,
        liquidacion: LiquidacionGeneral,
        data: LiquidacionSnapshotResult,
    ) -> LiquidacionSnapshot:
        """Crea un snapshot de la liquidación. Convierte el schema a dict solo para el JSONField."""
        return LiquidacionSnapshot.objects.create(
            liquidacion=liquidacion,
            data=data.model_dump(mode='json'),
        )

    def _obtener_snapshot_liquidacion(self, liquidacion_id: str) -> Optional[LiquidacionSnapshot]:
        """Obtiene el snapshot de una liquidación."""
        try:
            return LiquidacionSnapshot.objects.get(liquidacion_id=liquidacion_id)
        except LiquidacionSnapshot.DoesNotExist:
            return None

    def _todas_revisiones_habilitadas(self, revisiones_ids: list[str]) -> bool:
        """Verifica que todas las revisiones estén habilitadas."""
        revisions = EdificacionesRevision.objects.filter(id__in=revisiones_ids)
        for rev in revisions:
            if not rev.habilitada:
                return False
        return True

    def _listar_liquidaciones_paginado(
        self,
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        """
        Lista liquidaciones de edificaciones con paginación.
        Retorna (lista_de_datos_materializados, total).
        Todo el ORM se ejecuta aquí en contexto sync.
        """
        qs = LiquidacionGeneral.objects.filter(
            edificaciones__isnull=False
        ).select_related(
            'proyecto', 'proyecto__entidad'
        ).prefetch_related(
            'edificaciones'
        ).order_by('-created_at')
        total = qs.count()
        offset = (page - 1) * page_size
        qs = qs[offset:offset + page_size]

        # Evaluar QuerySet y obtener IDs para bulk-fetch de snapshots
        liquidaciones = list(qs)
        if not liquidaciones:
            return [], total

        liquidacion_ids = [liq.id for liq in liquidaciones]
        snapshots = {
            s.liquidacion_id: s
            for s in LiquidacionSnapshot.objects.filter(liquidacion_id__in=liquidacion_ids)
        }

        items = []
        for liq in liquidaciones:
            snapshot = snapshots.get(liq.id)
            total_liquidacion = 0.0
            if snapshot and snapshot.data:
                totales = snapshot.data.get('totales', {})
                total_liquidacion = totales.get('total_a_pagar', 0.0)

            items.append({
                'id': str(liq.id),
                'numero_revision': liq.edificaciones.numero_revision if liq.edificaciones else 0,
                'estado': liq.estado,
                'valor_proyecto': float(liq.valor_proyecto),
                'proyecto_public_id': str(liq.proyecto.public_id) if liq.proyecto.public_id else '',
                'proyecto_denominacion': liq.proyecto.denominacion,
                'fecha_registro': liq.created_at.isoformat() if liq.created_at else '',
                'total': total_liquidacion,
            })
        return items, total

    def _listar_liquidaciones_paginado_result(
        self,
        page: int,
        page_size: int,
    ) -> LiquidacionEdificacionesPaginatedResult:
        """Lista liquidaciones paginadas con datos para tabla (retorna result object)."""
        items_data, total = self._listar_liquidaciones_paginado(page, page_size)

        items = [
            LiquidacionEdificacionesListItem(**item)
            for item in items_data
        ]
        return LiquidacionEdificacionesPaginatedResult(items=items, total=total)

    def _listar_snapshots_paginado(
        self,
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        """
        Lista liquidaciones con datos completos de snapshot (proyecto, entidad,
        edificaciones/revisiones, totales, proyectistas) usando prefetch/select_related
        para evitar N+1.
        Retorna (lista_de_dicts_nested, total).

        NOTE: La construcción de cada item de la lista está Delegada al
        LiquidacionEdificacionesResultBuilder.build_snapshot_list_item()
        para mantener el core service enfocado en query/paginación y
        separar la responsabilidad de construcción de DTOs.
        """
        from ..builders import LiquidacionEdificacionesResultBuilder

        qs = LiquidacionGeneral.objects.filter(
            edificaciones__isnull=False
        ).select_related(
            'proyecto__entidad',
            'proyecto__distrito__provincia',
            'municipalidad__provincia',
            'municipalidad__distrito__provincia',
        ).prefetch_related(
            'edificaciones__revisiones__tarifa',
            'edificaciones__revisiones__especialidades',
            'edificaciones__proyectistas__perfil_ingeniero',
            'edificaciones__proyectistas__especialidad',
        ).order_by('-created_at')
        total = qs.count()
        offset = (page - 1) * page_size
        qs = qs[offset:offset + page_size]

        liquidaciones = list(qs)
        if not liquidaciones:
            return [], total

        liquidacion_ids = [liq.id for liq in liquidaciones]

        # Bulk fetch de snapshots
        snapshots = {
            s.liquidacion_id: s
            for s in LiquidacionSnapshot.objects.filter(liquidacion_id__in=liquidacion_ids)
        }

        # Bulk fetch de edificaciones con sus revisiones y tarifas y proyectistas
        edificaciones_qs = LiquidacionEdificaciones.objects.filter(
            liquidacion_id__in=liquidacion_ids
        ).prefetch_related(
            'revisiones__tarifa', 'revisiones__especialidades',
            'proyectistas__perfil_ingeniero', 'proyectistas__especialidad',
        )
        edificaciones_by_liquidacion = {ed.liquidacion_id: ed for ed in edificaciones_qs}

        # Bulk fetch de proyectistas por edificacion para pasar al builder
        # NOTE: Ya viene en el prefetch de edificaciones, pero extraemos la lista
        # para pasarla directamente al builder que sabe cómo construir el DTO.
        items = []
        for liq in liquidaciones:
            snapshot = snapshots.get(liq.id)
            edificacion = edificaciones_by_liquidacion.get(liq.id)
            # Obtener proyectistas desde edificacion con relaciones preloadadas
            proyectistas_list = []
            if edificacion:
                proyectistas_list = list(
                    edificacion.proyectistas.select_related('perfil_ingeniero', 'especialidad').all()
                )
            # Delegar construcción del item al builder
            item = LiquidacionEdificacionesResultBuilder.build_snapshot_list_item(
                liquidacion_orm=liq,
                edificacion_orm=edificacion,
                snapshot_orm=snapshot,
                proyectistas_orm_list=proyectistas_list,
            )
            items.append(item)

        return items, total

    # =============================================================================
    # Calculation helpers — sync operations for reusable domain calculations
    # Moved from flujo per Django architecture contract (P2, P6)
    # =============================================================================

    def calcular_derecho(
        self,
        monto_base: Decimal,
        derecho_minimo: Decimal,
        derecho_maximo: Optional[Decimal],
    ) -> Decimal:
        """
        Calcula el derecho aplicando mínimo y máximo.

        Args:
            monto_base: Monto base para el cálculo
            derecho_minimo: Valor mínimo del derecho
            derecho_maximo: Valor máximo del derecho (None = sin máximo)

        Returns:
            Decimal con el derecho calculado
        """
        derecho = monto_base
        if derecho < derecho_minimo:
            derecho = derecho_minimo
        if derecho_maximo is not None and derecho > derecho_maximo:
            derecho = derecho_maximo
        return derecho

    def calcular_monto_base(
        self,
        valor_proyecto: Decimal,
        porcentaje_liquidacion: Decimal,
    ) -> Decimal:
        """
        Calcula el monto base: valor_proyecto * porcentaje_liquidacion.

        Args:
            valor_proyecto: Valor total del proyecto
            porcentaje_liquidacion: Porcentaje de liquidación (ej: 0.05 para 5%)

        Returns:
            Decimal con el monto base calculado
        """
        return Decimal(str(valor_proyecto)) * porcentaje_liquidacion

    def calcular_revisiones(
        self,
        valor_proyecto: Decimal,
        revisiones_data: list,
        cobra: bool,
        igv_valor: Decimal,
        numero_revision: Optional[int] = None,
    ) -> tuple[list, Decimal, Decimal, Decimal]:
        """
        Calcula el monto base, derecho y totales para una lista de revisiones.

        Args:
            valor_proyecto: Valor del proyecto para el cálculo
            revisiones_data: Lista de revisiones (con .tarifa y .porcentaje_liquidacion,
                             o RevisionConTarifaData para compatibilidad)
            cobra: Si True aplica derecho, si False todo es 0
            igv_valor: Valor del IGV (ej: Decimal('0.18'))
            numero_revision: Si se proporciona, retorna RevisionCalculoData con este número;
                            si no, retorna CotizacionRevisionData (sin numero_revision por item)

        Returns:
            Tuple of (revision_results, subtotal, igv_monto, total_liquidacion)
        """
        subtotal = Decimal('0')
        revision_results = []

        for rev_data in revisiones_data:
            # Support both EdificacionRevisionData (with .especialidad.nombre)
            # and RevisionConTarifaData (with .especialidad_nombre string)
            if hasattr(rev_data, 'especialidad_nombre'):
                # RevisionConTarifaData style
                especialidad_nombre = rev_data.especialidad_nombre
            else:
                # EdificacionRevisionData style
                especialidad_nombre = rev_data.especialidad.nombre

            monto_base = self.calcular_monto_base(
                valor_proyecto,
                rev_data.porcentaje_liquidacion,
            )

            if cobra:
                derecho = self.calcular_derecho(
                    monto_base,
                    rev_data.tarifa.derecho_minimo,
                    rev_data.tarifa.derecho_maximo,
                )
            else:
                derecho = Decimal('0')
                monto_base = Decimal('0')

            if numero_revision is not None:
                # Create flow: RevisionCalculoData con numero_revision por item
                revision_results.append(RevisionCalculoData(
                    id=str(rev_data.id),
                    numero_revision=numero_revision,
                    especialidad=especialidad_nombre,
                    tarifa=TarifaCalculoData(
                        id=str(rev_data.tarifa.id),
                        derecho_minimo=rev_data.tarifa.derecho_minimo,
                        derecho_maximo=rev_data.tarifa.derecho_maximo,
                        porcentaje_minimo_uit=rev_data.tarifa.porcentaje_minimo_uit,
                    ),
                    monto_base=monto_base,
                    cobra=cobra,
                    derecho=derecho,
                ))
            else:
                # Cotizar flow: CotizacionRevisionData sin numero_revision por item
                revision_results.append(CotizacionRevisionData(
                    id=rev_data.id,
                    especialidad=especialidad_nombre,
                    tarifa=TarifaCalculoData(
                        id=rev_data.tarifa.id,
                        derecho_minimo=rev_data.tarifa.derecho_minimo,
                        derecho_maximo=rev_data.tarifa.derecho_maximo,
                        porcentaje_minimo_uit=rev_data.tarifa.porcentaje_minimo_uit,
                    ),
                    monto_base=monto_base,
                    cobra=cobra,
                    derecho=derecho,
                ))
            subtotal += derecho

        # Calcular totales
        igv_monto = subtotal * igv_valor
        total_liquidacion = subtotal + igv_monto

        return revision_results, subtotal, igv_monto, total_liquidacion

    def to_revision_con_tarifa(self, rev: RevisionVigenteResult) -> RevisionConTarifaData:
        """
        Transforma RevisionVigenteResult (flat) en RevisionConTarifaData con
        estructura anidada (.tarifa y .especialidad_nombre).

        Reemplaza el helper _to_revision_calculo_data con fake inline class.

        Args:
            rev: RevisionVigenteResult con campos planos

        Returns:
            RevisionConTarifaData con estructura anidada
        """
        return RevisionConTarifaData(
            id=rev.id,
            porcentaje_liquidacion=rev.porcentaje_liquidacion,
            tarifa=TarifaCalculoData(
                id=rev.tarifa_id,
                derecho_minimo=rev.derecho_minimo,
                derecho_maximo=rev.derecho_maximo,
                porcentaje_minimo_uit=rev.porcentaje_minimo_uit,
            ),
            especialidad_nombre=rev.especialidad_nombre,
        )

    def _obtener_delegados_vigentes(
        self,
        municipalidad_id: str,
        fecha: date,
        revision_id: str | None = None,
        categoria: str | None = None,
    ) -> list:
        """
        Obtiene delegados vigentes para una municipalidad y fecha.

        Un delegado está vigente si:
        1. Existe en MunicipalidadesDelegado con activo=True para la municipalidad
        2. El Delegado tiene status='activo'
        3. Existe PeriodoDelegado con periodo_inicio <= fecha <= periodo_fin
        4. Si se provee revision_id, la especialidad del delegado debe:
           a. Estar en el grupo EdificacionesEspecialidades vigente
           b. Estar en las especialidades de la EdificacionesRevision seleccionada
        5. Si se provee categoria, filtra por esa categoría en MunicipalidadesDelegado

        Args:
            municipalidad_id: UUID de la municipalidad
            fecha: Fecha actual para validar periodo
            revision_id: UUID opcional de EdificacionesRevision para filtrar por especialidades
            categoria: Categoría del delegado (Edificaciones o Habilitaciones Urbanas)

        Returns:
            Lista de DelegadoVigenteResult con datos del delegado:
            id, nombre_completo, cip, especialidad: {id, nombre}, tipo
        """
        from django.db.models import Q, OuterRef, Subquery
        from ...models import Delegado, PeriodoDelegado, EdificacionesEspecialidades, EdificacionesRevision, MunicipalidadDelegado
        from ...constants import DelegadoStatus
        from ...schemas import DelegadoVigenteResult, EspecialidadBasicaResult

        # Annotate tipo and categoria from the specific MunicipalidadDelegado for this municipalidad
        # This replaces Delegado.tipo which was per-delegado; now tipo and categoria are per-assignment
        tipo_subquery = MunicipalidadDelegado.objects.filter(
            delegado=OuterRef('pk'),
            municipalidad_id=municipalidad_id,
        ).values_list('tipo', flat=True)[:1]

        categoria_subquery = MunicipalidadDelegado.objects.filter(
            delegado=OuterRef('pk'),
            municipalidad_id=municipalidad_id,
        ).values_list('categoria', flat=True)[:1]

        # Query: Join MunicipalidadDelegado -> Delegado -> PeriodoDelegado
        # Filtros:
        # - municipalidad_id
        # - ProvinciaDelegado.activo = True
        # - Delegado.status = 'activo'
        # - PeriodoDelegado.periodo_inicio <= fecha
        # - PeriodoDelegado.periodo_fin >= fecha OR periodo_fin IS NULL (vigente/open-ended)
        queryset = (
            Delegado.objects
            .select_related('perfil_ingeniero', 'especialidad')
            .annotate(municipalidad_tipo=Subquery(tipo_subquery))
            .filter(
                Q(periodos_asignados__periodo_fin__gte=fecha) | Q(periodos_asignados__periodo_fin__isnull=True),
                distritos_asignados__municipalidad_id=municipalidad_id,
                distritos_asignados__activo=True,
                status=DelegadoStatus.ACTIVO,
                periodos_asignados__periodo_inicio__lte=fecha,
            )
            .distinct()
        )

        # Si se provee categoria, filtrar por esa categoria en MunicipalidadesDelegado
        if categoria:
            queryset = queryset.filter(distritos_asignados__categoria=categoria)

        # Si se provee revision_id, aplicar filtro adicional por especialidades
        if revision_id:
            # Obtener grupo de especialidades vigente
            grupo_vigente = EdificacionesEspecialidades.objects.filter(
                periodo_inicio__lte=fecha,
            ).filter(
                Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha)
            ).first()

            if grupo_vigente:
                # Especialidades del grupo vigente
                especialidades_vigente_ids = set(
                    grupo_vigente.especialidades.values_list('id', flat=True)
                )

                # Especialidades de la revision seleccionada
                try:
                    revision = EdificacionesRevision.objects.prefetch_related('especialidades').get(id=revision_id)
                    revision_especialidades_ids = set(
                        revision.especialidades.values_list('id', flat=True)
                    )
                except EdificacionesRevision.DoesNotExist:
                    revision_especialidades_ids = set()

                # Interseccion: vigentes que tambien estan en la revision
                allowed_especialidades = especialidades_vigente_ids & revision_especialidades_ids

                # Filtrar queryset por especialidades en la interseccion
                if allowed_especialidades:
                    queryset = queryset.filter(especialidad_id__in=allowed_especialidades)
                else:
                    # No hay interseccion - retornar lista vacia
                    return []
            else:
                # No hay grupo vigente - retornar lista vacia
                return []

        items = []
        for dele in queryset:
            perfil = dele.perfil_ingeniero
            especialidad_data = None
            if dele.especialidad:
                especialidad_data = EspecialidadBasicaResult(
                    id=dele.especialidad.id,
                    nombre=dele.especialidad.nombre,
                )
            items.append(DelegadoVigenteResult(
                id=dele.id,
                nombre_completo=perfil.nombre_completo if perfil else '',
                cip=perfil.cip if perfil else '',
                especialidad=especialidad_data,
                tipo=dele.municipalidad_tipo,
            ))
        return items
