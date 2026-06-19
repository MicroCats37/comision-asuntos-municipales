"""
Liquidaciones Edificaciones Service — operaciones sync.
"""
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
from ...schemas import VariablesFinancierasResult, EdificacionRevisionData, TarifaEdificacionData, EspecialidadData, LiquidacionEdificacionesPaginatedResult, LiquidacionEdificacionesListItem, LiquidacionSnapshotResult, RevisionVigenteResult


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
        ).select_related('tarifa', 'especialidad')

    def _obtener_revisiones_vigentes(self) -> list:
        """Materializa el QuerySet en contexto sync - obligatorio antes de sync_to_async."""
        qs = self._obtener_revisiones_vigentes_raw()
        # Materializar ANTES de retornar - el QuerySet se evalúa aquí en contexto sync
        return list(qs)

    def _obtener_revisiones_vigentes_result(self) -> list[RevisionVigenteResult]:
        """Obtiene todas las revisiones vigentes con sus tarifas y especialidades (devuelve result objects)."""
        revisions_list = self._obtener_revisiones_vigencias_raw()

        result = []
        for rev in revisions_list:
            result.append(RevisionVigenteResult(
                id=str(rev.id),
                especialidad_id=str(rev.especialidad.id),
                especialidad_nombre=rev.especialidad.nombre,
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
        return EdificacionesRevision.objects.filter(id__in=ids).select_related('tarifa', 'especialidad')

    def _obtener_revisiones_por_ids(self, ids: list[str]) -> list[EdificacionRevisionData]:
        """Obtiene revisiones por IDs (devuelve result objects)."""
        revisions_qs = self._obtener_revisiones_por_ids_raw(ids)

        result = []
        for rev in revisions_qs:
            result.append(EdificacionRevisionData(
                id=rev.id,
                especialidad=EspecialidadData(
                    id=rev.especialidad.id,
                    nombre=rev.especialidad.nombre,
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
        municipalidad: 'entidades.Municipalidad',
        igv: 'finanzas.IGV',
        uit: 'finanzas.UIT',
        valor_proyecto: Decimal,
        observacion: Optional[str],
        liquidacion_previa: Optional[LiquidacionGeneral] = None,
    ) -> LiquidacionGeneral:
        """Crea una LiquidacionGeneral con la cadena de liquidaciones previas."""
        public_id = self._generar_public_id_liquidacion_general()
        liquidacion = LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            igv=igv,
            uit=uit,
            valor_proyecto=valor_proyecto,
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
        """
        qs = LiquidacionGeneral.objects.filter(
            edificaciones__isnull=False
        ).select_related(
            'proyecto__entidad'
        ).prefetch_related(
            'edificaciones__revisiones__tarifa',
            'edificaciones__revisiones__especialidad',
            'edificaciones__proyectistas',
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
            'revisiones__tarifa', 'revisiones__especialidad', 'proyectistas'
        )
        edificaciones_by_liquidacion = {ed.liquidacion_id: ed for ed in edificaciones_qs}

        items = []
        for liq in liquidaciones:
            snapshot = snapshots.get(liq.id)
            edificacion = edificaciones_by_liquidacion.get(liq.id)
            numero_revision = edificacion.numero_revision if edificacion else 0

            # Construir proyecto anidado
            proyecto = liq.proyecto
            entidad_data = None
            if proyecto.entidad:
                entidad_data = {
                    'id': str(proyecto.entidad.id),
                    'tipo': proyecto.entidad.tipo_documento,
                    'nombre': proyecto.entidad.nombre_completo,
                    'ruc': proyecto.entidad.numero_documento if hasattr(proyecto.entidad, 'numero_documento') else None,
                }

            # NOTE: proyectista ya no está en proyecto — ahora vive en LiquidacionEdificaciones.proyectistas
            proyecto_data = {
                'id': str(proyecto.id),
                'public_id': str(proyecto.public_id) if proyecto.public_id else '',
                'nombre': proyecto.denominacion,
                'direccion': proyecto.direccion,
                'valor_proyecto': float(liq.valor_proyecto),
                'entidad': entidad_data,
            }

            # Construir proyectistas desde edificacion
            proyectistas_data = []
            if edificacion:
                for p in edificacion.proyectistas.all():
                    proyectistas_data.append({
                        'id': str(p.id),
                        'cip': p.cip,
                        'dni': p.dni,
                        'cap': p.cap,
                        'nombres': p.nombres,
                        'apellidos': p.apellidos,
                    })

            # Construir edificaciones con revisiones
            revisiones_data = []
            if snapshot and snapshot.data:
                edificaciones_snapshot = snapshot.data.get('edificaciones', {})
                numero_revision = edificaciones_snapshot.get('numero_revision', numero_revision)
                revisions_snapshot = edificaciones_snapshot.get('revisiones', [])
                if revisions_snapshot:
                    # Usar datos del snapshot
                    revisiones_data = [{
                        'id': str(rev.get('id', '')),
                        'numero_revision': rev.get('numero_revision', 0),
                        'especialidad': rev.get('especialidad', ''),
                        'tarifa': rev.get('tarifa', {}),
                        'monto_base': float(rev.get('monto_base', 0)),
                        'cobra': rev.get('cobra', True),
                    } for rev in revisions_snapshot]
                # Tomar proyectistas del snapshot si existen
                if 'proyectistas' in edificaciones_snapshot:
                    proyectistas_data = edificaciones_snapshot.get('proyectistas', [])
            elif edificacion:
                # Fallback a ORM cuando no hay snapshot
                for rev in edificacion.revisiones.all():
                    revisiones_data.append({
                        'id': str(rev.id),
                        'numero_revision': rev.numero_revision if hasattr(rev, 'numero_revision') else 0,
                        'especialidad': rev.especialidad.nombre if rev.especialidad else '',
                        'tarifa': {
                            'id': str(rev.tarifa.id),
                            'derecho_minimo': float(rev.tarifa.derecho_minimo),
                            'derecho_maximo': float(rev.tarifa.derecho_maximo) if rev.tarifa.derecho_maximo else None,
                            'porcentaje_minimo_uit': float(rev.tarifa.porcentaje_minimo_uit),
                        },
                        'monto_base': float(getattr(rev, 'monto_base', 0)),
                        'cobra': getattr(rev, 'cobra', True),
                    })

            # Construir totales desde snapshot JSON
            totales_data = {
                'subtotal': 0.0,
                'igv': 0.0,
                'total': 0.0,
                'liquidacion_total': 0.0,
                'total_a_pagar': 0.0,
            }
            if snapshot and snapshot.data:
                totales_data = snapshot.data.get('totales', totales_data)

            # Construir data de edificaciones (incluye numero_revision y proyectistas)
            # Extraer public_id, tipo_tramite, tramite_accion de snapshot o fallback del ORM
            edificacion_public_id = ""
            edificacion_tipo_tramite = ""
            edificacion_tramite_accion = ""
            if snapshot and snapshot.data:
                edificaciones_snapshot = snapshot.data.get('edificaciones', {})
                edificacion_public_id = edificaciones_snapshot.get('public_id', '')
                edificacion_tipo_tramite = edificaciones_snapshot.get('tipo_tramite', '')
                edificacion_tramite_accion = edificaciones_snapshot.get('tramite_accion', '')
            if not edificacion_public_id and edificacion:
                edificacion_public_id = edificacion.public_id or ''
            if not edificacion_tipo_tramite and edificacion:
                edificacion_tipo_tramite = edificacion.tipo_tramite or ''
            if not edificacion_tramite_accion and edificacion:
                edificacion_tramite_accion = edificacion.tramite_accion or ''

            edificaciones_data = {
                'public_id': edificacion_public_id,
                'numero_revision': numero_revision,
                'tipo_tramite': edificacion_tipo_tramite,
                'tramite_accion': edificacion_tramite_accion,
                'proyectistas': proyectistas_data,
                'revisiones': revisiones_data,
            }

            # Extraer public_id y municipalidad de liquidacion
            liquidacion_public_id = ""
            municipalidad_id = None
            municipalidad_nombre = ""
            if snapshot and snapshot.data:
                liquidacion_snapshot = snapshot.data.get('liquidacion', {})
                liquidacion_public_id = liquidacion_snapshot.get('public_id', '')
                municipalidad_id = liquidacion_snapshot.get('municipalidad_id')
                municipalidad_nombre = liquidacion_snapshot.get('municipalidad_nombre', '')
            if not liquidacion_public_id:
                liquidacion_public_id = liq.public_id or ''
            if not municipalidad_id and liq.municipalidad:
                municipalidad_id = str(liq.municipalidad.id)
                municipalidad_nombre = liq.municipalidad.nombre

            items.append({
                'liquidacion_id': str(liq.id),
                'public_id': liquidacion_public_id,
                'numero_liquidacion': f"LIQ-EDIF-{numero_revision}",
                'estado': liq.estado,
                'fecha_registro': liq.fecha_registro.isoformat() if liq.fecha_registro else '',
                'municipalidad_id': municipalidad_id,
                'municipalidad_nombre': municipalidad_nombre,
                'observacion': liq.observacion,
                'proyecto': proyecto_data,
                'edificaciones': edificaciones_data,
                'totales': totales_data,
            })

        return items, total
