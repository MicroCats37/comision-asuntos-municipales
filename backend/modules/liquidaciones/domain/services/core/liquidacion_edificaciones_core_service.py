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
    LiquidacionEdificacion,
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    EspecialidadesLiquidacion,
    LiquidacionProyectista,
    Proyecto,
)
from ...schemas import VariablesFinancierasResult, EdificacionRevisionData, TarifaEdificacionData, EspecialidadData, EspecialidadBasicaResult, LiquidacionEdificacionesPaginatedResult, LiquidacionEdificacionesListItem, RevisionVigenteResult, RevisionConTarifaData, RevisionCalculoData, CotizacionRevisionData, TarifaCalculoData
from modules.entidades.models import Municipalidad
from ...schemas_proyecto import ProyectoInlineData


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

    def _obtener_revisiones_vigencias_raw(
        self,
        tipo_tramite: str | None = None,
        tramite_accion: str | None = None,
    ) -> QuerySet:
        """
        Obtiene todas las TarifaLiquidacionBase vigentes (habilitadas) para el tipo
        de liquidación EDIFICACION - QuerySet lazy.

        Una TarifaLiquidacionBase vigente tiene:
        - periodo_fin IS NULL (abierta/sin vencimiento)
        - tipo_liquidacion = EDIFICACION

        Si tipo_tramite y tramite_accion son provistos, filtra usando ReglaTarifaEdificacion.

        Nota: La FK hacia TarifaPorcentajeObra ahora vive en TarifaPorcentajeObra
        (OneToOne: TarifaPorcentajeObra.tarifa_base -> TarifaLiquidacionBase).
        Se usa prefetch_related('detalle_porcentual') para obtener el detalle porcentual.
        """
        from ...constants import TipoLiquidacion
        from ...models import ReglaTarifaEdificacion

        qs = TarifaLiquidacionBase.objects.filter(
            periodo_fin__isnull=True,
            tipo_liquidacion=TipoLiquidacion.EDIFICACION,
        ).prefetch_related('especialidades', 'detalle_porcentual')

        # Si se proveen tipo_tramite y tramite_accion, filtrar usando ReglaTarifaEdificacion
        if tipo_tramite is not None and tramite_accion is not None:
            # Filtrar tarifas que tienen una regla para esta combinación
            regla_ids = ReglaTarifaEdificacion.objects.filter(
                tipo_tramite=tipo_tramite,
                tramite_accion=tramite_accion,
            ).values_list('tarifa_base_id', flat=True)
            qs = qs.filter(id__in=regla_ids)

        return qs

    def _obtener_revisiones_vigentes(self) -> list:
        """Materializa el QuerySet en contexto sync - obligatorio antes de sync_to_async."""
        qs = self._obtener_revisiones_vigentes_raw()
        # Materializar ANTES de retornar - el QuerySet se evalúa aquí en contexto sync
        return list(qs)

    def _obtener_revisiones_vigentes_result(
        self,
        tipo_tramite: str | None = None,
        tramite_accion: str | None = None,
    ) -> list[RevisionVigenteResult]:
        """
        Obtiene todas las tarifas base vigentes con sus tarifas porcentuales y especialidades
        (devuelve result objects para TarifaLiquidacionBase + TarifaPorcentajeObra).

        Si tipo_tramite y tramite_accion son provistos, filtra usando ReglaTarifaEdificacion.

        NOTE: Con M2M especialidades, una tarifa base puede tener múltiples especialidades.
        Se devuelve la lista completa de especialidades para cada tarifa.
        El flujo completo de cálculo (que es 1 fila = 1 cargo) no necesita expand by specialty.

        Una TarifaLiquidacionBase representa UNA configuración de porcentaje para un conjunto
        de especialidades. Por ejemplo:
        - TarifaBase con especialidades [A,B,C] y porcentaje 0.0015 (0.15%) -> primera revisión
        - TarifaBase con especialidad [A] y porcentaje 0.0005 (0.05%) -> especialidad individual
        """
        from modules.liquidaciones.domain.schemas import EspecialidadBasicaResult
        from core.utils import esta_vigente

        tarifa_bases_qs = self._obtener_revisiones_vigencias_raw(
            tipo_tramite=tipo_tramite,
            tramite_accion=tramite_accion,
        )

        result = []
        for tb in tarifa_bases_qs:
            # M2M: obtener todas las especialidades de la tarifa base
            especialidades_orm = tb.especialidades.all()
            especialidades = [
                EspecialidadBasicaResult(
                    id=esp.id,
                    nombre=esp.nombre,
                )
                for esp in especialidades_orm
            ]
            # Obtener la tarifa porcentual asociada (ahora via reverse OneToOne)
            # tarifa_base = OneToOneField en TarifaPorcentajeObra -> TarifaLiquidacionBase
            tarifa_pct = tb.detalle_porcentual  # Related name del OneToOne
            # Verificar si la tarifa base está vigente
            habilitada = esta_vigente(tb.periodo_inicio, tb.periodo_fin)

            result.append(RevisionVigenteResult(
                id=str(tb.id),
                especialidades=especialidades,
                tarifa_id=str(tarifa_pct.id),
                porcentaje_liquidacion=tarifa_pct.porcentaje_liquidacion,
                derecho_minimo=tarifa_pct.derecho_minimo,
                derecho_maximo=tarifa_pct.derecho_maximo,
                porcentaje_minimo_uit=tarifa_pct.porcentaje_minimo_uit,
                habilitada=habilitada,
            ))
        return result

    def _obtener_revisiones_por_ids_raw(self, ids: list[str]) -> QuerySet:
        """
        Obtiene TarifasLiquidacionBase por lista de IDs (QuerySet lazy).

        NOTE: Aquí ids son IDs de TarifaLiquidacionBase, no del sistema antiguo.
        Nota: La FK hacia TarifaPorcentajeObra ahora vive en TarifaPorcentajeObra
        (OneToOne: TarifaPorcentajeObra.tarifa_base -> TarifaLiquidacionBase).
        """
        return TarifaLiquidacionBase.objects.filter(
            id__in=ids
        ).prefetch_related('especialidades', 'detalle_porcentual')

    def _obtener_revisiones_por_ids(self, ids: list[str]) -> list[EdificacionRevisionData]:
        """
        Obtiene tarifas base por IDs (devuelve result objects).

        NOTE: Con M2M especialidades, cada tarifa base puede tener múltiples especialidades.
        Se devuelve la lista completa de especialidades en el campo `especialidades`
        (además de `especialidad` con la primera para compatibilidad del API).
        """
        from core.utils import esta_vigente

        tarifa_bases_qs = self._obtener_revisiones_por_ids_raw(ids)

        result = []
        for tb in tarifa_bases_qs:
            # M2M: obtener TODAS las especialidades
            especialidades_orm = list(tb.especialidades.all())
            primera_esp = especialidades_orm[0] if especialidades_orm else None
            todas_especialidades = [
                EspecialidadData(
                    id=esp.id,
                    nombre=esp.nombre,
                )
                for esp in especialidades_orm
            ]
            # Obtener la tarifa porcentual (ahora via reverse OneToOne)
            tarifa_pct = tb.detalle_porcentual
            # Verificar si está vigente
            habilitada = esta_vigente(tb.periodo_inicio, tb.periodo_fin)

            # Si no hay especialidad (caso excepcional dado que validación exige al menos 1),
            # usar la primera especialidad de todas_especialidades o fallar con mensaje claro.
            if primera_esp is None and todas_especialidades:
                primera_esp_data = todas_especialidades[0]
            elif primera_esp is None:
                # No debería ocurrir si la validación de tarifas se cumple,
                # pero por seguridad se usa la primera disponible de la lista.
                primera_esp_data = todas_especialidades[0] if todas_especialidades else None
                if primera_esp_data is None:
                    raise ValueError(
                        f"La tarifa base {tb.id} no tiene especialidades asociadas. "
                        f"Cada tarifa debe tener al menos una especialidad."
                    )
            else:
                primera_esp_data = EspecialidadData(id=primera_esp.id, nombre=primera_esp.nombre)

            result.append(EdificacionRevisionData(
                id=tb.id,
                especialidad=primera_esp_data,
                especialidades=todas_especialidades,
                tarifa=TarifaEdificacionData(
                    id=tarifa_pct.id,
                    derecho_minimo=tarifa_pct.derecho_minimo,
                    derecho_maximo=tarifa_pct.derecho_maximo,
                    porcentaje_minimo_uit=tarifa_pct.porcentaje_minimo_uit,
                ),
                porcentaje_liquidacion=tarifa_pct.porcentaje_liquidacion,
                habilitada=habilitada,
            ))
        return result

    def _existe_primera_revision_proyecto(self, proyecto_id: str) -> bool:
        """
        Verifica si existe primera revisión para el proyecto.

        NOTE: numero_revision ahora vive en LiquidacionGeneral, no en LiquidacionEdificacion.
        """
        return LiquidacionGeneral.objects.filter(
            proyecto_id=proyecto_id,
            numero_revision=1,
            edificaciones__isnull=False,  # Solo liquidaciones de edificaciones
        ).exists()

    def _existe_revision_numero_proyecto(self, proyecto_id: str, numero_revision: int) -> bool:
        """
        Verifica si existe una revisión con ese número para el proyecto.

        NOTE: numero_revision ahora vive en LiquidacionGeneral, no en LiquidacionEdificacion.
        """
        return LiquidacionGeneral.objects.filter(
            proyecto_id=proyecto_id,
            numero_revision=numero_revision,
            edificaciones__isnull=False,  # Solo liquidaciones de edificaciones
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
        Genera un public_id único para una LiquidacionEdificacion.

        Formato: LIQ-EDIF-{year}-{count:05d}

        Returns:
            public_id generado
        """
        year = timezone.now().year
        count = LiquidacionEdificacion.objects.filter(
            public_id__startswith=f"LIQ-EDIF-{year}-"
        ).count()
        return f"LIQ-EDIF-{year}-{count + 1:05d}"

    def _crear_liquidacion_general(
        self,
        proyecto: Proyecto,
        municipalidad: Municipalidad,
        expediente: Optional[str],
        observacion: Optional[str],
        liquidacion_previa: Optional[LiquidacionGeneral] = None,
        numero_revision: int = 1,
    ) -> LiquidacionGeneral:
        """
        Crea una LiquidacionGeneral con la cadena de liquidaciones previas.

        Args:
            proyecto: Proyecto asociado
            municipalidad: Municipaliddad asociada
            expediente: Número de expediente (opcional)
            observacion: Observaciones (opcional)
            liquidacion_previa: Liquidación previa si es una revisión
            numero_revision: Número de revisión (default 1 para primera)
        """
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
        liquidacion = LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            igv=igv,
            uit=uit,
            expediente=expediente,
            observacion=observacion,
            public_id=public_id,
            numero_revision=numero_revision,
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
        tipo_tramite: str,
        tramite_accion: str,
        proyectistas_ids: Optional[list[str]] = None,
    ) -> LiquidacionEdificacion:
        """
        Crea una LiquidacionEdificacion.

        Nota: numero_revision vive en LiquidacionGeneral, no en LiquidacionEdificacion.
        Los valores de cálculo (valor_proyecto, valor_base_calculo) viven en
        LiquidacionPorcentajeObra (creado por el flujo).
        """
        public_id = self._generar_public_id_liquidacion_edificaciones()
        liq_edif = LiquidacionEdificacion.objects.create(
            liquidacion=liquidacion,
            tipo_tramite=tipo_tramite,
            tramite_accion=tramite_accion,
            public_id=public_id,
        )
        if proyectistas_ids:
            from modules.liquidaciones.domain.models import Proyectista, LiquidacionProyectista
            proyectistas = Proyectista.objects.filter(id__in=proyectistas_ids)
            for p in proyectistas:
                LiquidacionProyectista.objects.create(
                    liquidacion_general=liquidacion,
                    proyectista=p,
                )
        return liq_edif

    def _asociar_revisiones(
        self,
        liquidacion_edificaciones: LiquidacionEdificacion,
        revisiones_ids: list[str],
    ) -> None:
        """
        Asocia revisiones a la liquidación de edificaciones.

        NOTE: En el nuevo diseño, ya NO se usa M2M entre LiquidacionEdificacion
        y TarifaLiquidacionBase. El cálculo de tarifas se maneja a través
        de LiquidacionPorcentajeObra que referencia a TarifaPorcentajeObra.

        Este método se mantiene por compatibilidad pero es un no-op en el nuevo flujo.
        """
        # En el nuevo diseño, las revisiones (TarifaLiquidacionBase) no se asocian via M2M.
        # El cálculo de la liquidación se persiste en LiquidacionPorcentajeObra con
        # referencia a TarifaPorcentajeObra.
        pass

    def _todas_revisiones_habilitadas(self, revisiones_ids: list[str]) -> bool:
        """
        Verifica que todas las tarifas base (TarifaLiquidacionBase) estén habilitadas.

        Una tarifa base está habilitada si su fecha de hoy está dentro del período
        de vigencia (periodo_inicio <= hoy AND (periodo_fin IS NULL OR periodo_fin >= hoy)).

        Raises:
            ValueError: Si alguno de los IDs no corresponde a una TarifaLiquidacionBase.
        """
        from core.utils import esta_vigente
        from datetime import date

        today = date.today()
        tarifa_bases = TarifaLiquidacionBase.objects.filter(id__in=revisiones_ids)
        found_ids = {str(tb.id) for tb in tarifa_bases}
        requested_ids = {str(id_) for id_ in revisiones_ids}

        missing_ids = requested_ids - found_ids
        if missing_ids:
            raise ValueError(
                f"Uno o más IDs en revisiones_ids no corresponden a TarifasLiquidacionBase: {missing_ids}. "
                f"¿Está enviando IDs de especialidad en lugar de IDs de tarifa base?"
            )

        for tb in tarifa_bases:
            if not esta_vigente(tb.periodo_inicio, tb.periodo_fin):
                return False
        return True

    def _listar_liquidaciones_paginado(
        self,
        page: int,
        page_size: int,
        proyecto_public_id: str | None = None,
    ) -> tuple[list[dict], int]:
        """
        Lista liquidaciones de edificaciones con paginación.
        Retorna (lista_de_datos_materializados, total).
        Todo el ORM se ejecuta aquí en contexto sync.

        Args:
            page: Número de página (1-indexed)
            page_size: Elementos por página
            proyecto_public_id: Filtro opcional por ID público del proyecto (ej. PROY-2026-00001)
        """
        qs = LiquidacionGeneral.objects.filter(
            edificaciones__isnull=False
        )

        # Filtro opcional por public_id del proyecto
        if proyecto_public_id:
            qs = qs.filter(proyecto__public_id=proyecto_public_id)

        qs = qs.select_related(
            'proyecto', 'proyecto__entidad', 'municipalidad'
        ).prefetch_related(
            'edificaciones'
        ).order_by('-created_at')
        total = qs.count()
        offset = (page - 1) * page_size
        qs = qs[offset:offset + page_size]

        # Evaluar QuerySet y obtener IDs
        liquidaciones = list(qs)
        if not liquidaciones:
            return [], total

        items = []
        for liq in liquidaciones:
            # Calcular total desde LiquidacionPorcentajeObra (cálculos persistidos)
            total_liquidacion = 0.0
            if liq.liquidacion_porcentaje_obra.exists():
                lpo = liq.liquidacion_porcentaje_obra.first()
                # Calcular IGV y total desde los valores persistidos
                subtotal = float(lpo.tarifa_aplicada.derecho_minimo) if lpo.tarifa_aplicada and lpo.tarifa_aplicada.derecho_minimo is not None else 0.0
                # Por ahora usamos el valor guardado en sub_total de LiquidacionGeneral
                total_liquidacion = float(liq.sub_total) if liq.sub_total else 0.0
                # Agregar IGV si tenemos igv
                if hasattr(liq, 'igv') and liq.igv:
                    total_liquidacion = total_liquidacion * (1 + float(liq.igv.valor))

            items.append({
                'id': str(liq.id),
                'public_id': str(liq.public_id) if liq.public_id else None,
                # NOTE: numero_revision ahora vive en LiquidacionGeneral, no en LiquidacionEdificaciones
                'numero_revision': liq.numero_revision if liq.edificaciones else 0,
                'estado': liq.estado,
                # valor_proyecto viene de LiquidacionPorcentajeObra, no de LiquidacionEdificacion
                'valor_proyecto': float(liq.liquidacion_porcentaje_obra.first().valor_proyecto) if liq.liquidacion_porcentaje_obra.exists() else 0.0,
                'proyecto_public_id': str(liq.proyecto.public_id) if liq.proyecto.public_id else '',
                'proyecto_denominacion': liq.proyecto.denominacion,
                'fecha_registro': liq.created_at.isoformat() if liq.created_at else '',
                'total': total_liquidacion,
                # Campos de municipalidad (disponibles via select_related)
                'municipalidad_id': str(liq.municipalidad.id) if liq.municipalidad else None,
                'municipalidad_nombre': liq.municipalidad.nombre if liq.municipalidad else None,
                # Campos de edificaciones (disponibles via prefetch)
                'tipo_tramite': liq.edificaciones.tipo_tramite if liq.edificaciones else None,
                'tramite_accion': liq.edificaciones.tramite_accion if liq.edificaciones else None,
            })
        return items, total

    def _listar_liquidaciones_paginado_result(
        self,
        page: int,
        page_size: int,
        proyecto_public_id: str | None = None,
    ) -> LiquidacionEdificacionesPaginatedResult:
        """Lista liquidaciones paginadas con datos para tabla (retorna result object)."""
        items_data, total = self._listar_liquidaciones_paginado(page, page_size, proyecto_public_id)

        items = [
            LiquidacionEdificacionesListItem(**item)
            for item in items_data
        ]
        return LiquidacionEdificacionesPaginatedResult(items=items, total=total)

    def _obtener_liquidacion_edificacion_para_detalle(
        self,
        liquidacion_id: str,
    ) -> Optional[dict]:
        """
        Obtiene una liquidación de edificación con todos los datos relacionados
        para construir LiquidacionEdificacionesResult y retornar via presenter.

        Args:
            liquidacion_id: UUID de la LiquidacionGeneral

        Returns:
            Dict con todos los datos necesarios para el presenter, o None si no existe.
        """
        try:
            liquidacion = LiquidacionGeneral.objects.select_related(
                'proyecto',
                'proyecto__entidad',
                'municipalidad',
                'igv',
                'uit',
            ).prefetch_related(
                'edificaciones',
                'liquidacion_porcentaje_obra__tarifa_aplicada__tarifa_base__especialidades',
            ).get(id=liquidacion_id)
        except LiquidacionGeneral.DoesNotExist:
            return None

        # Obtener LiquidacionEdificacion
        liq_edif = liquidacion.edificaciones
        if not liq_edif:
            return None

        # Obtener proyectistas desde LiquidacionProyectista
        from modules.liquidaciones.models import LiquidacionProyectista
        edificaciones_proyectistas = [
            lp.proyectista for lp in LiquidacionProyectista.objects.filter(
                liquidacion_general=liquidacion
            ).select_related('proyectista__perfil_ingeniero', 'proyectista__especialidad')
        ]

        # Obtener delegados
        edificaciones_delegados = list(
            liquidacion.liquidacion_delegados.select_related(
                'delegado__perfil_ingeniero', 'delegado__especialidad'
            ).all()
        )

        # Obtener contactos
        from modules.liquidaciones.models import LiquidacionContacto
        contactos_orm = list(
            liquidacion.contactos.select_related('contacto').all()
        )

        # Obtener variables financieras (IGV/UIT)
        variables = self._obtener_variables_financieras_vigentes()

        # Reconstruir revision_results desde LiquidacionPorcentajeObra persistida
        revision_results = []
        lpo_list = list(liquidacion.liquidacion_porcentaje_obra.all())

        # Las revisiones que cobran son 1, 3, 5
        REVISIONES_COBRAN = {1, 3, 5}
        cobra = liquidacion.numero_revision in REVISIONES_COBRAN

        for lpo in lpo_list:
            tarifa = lpo.tarifa_aplicada
            # Obtener especialidades de la tarifa — ahora via tarifa_base (OneToOne) -> TarifaLiquidacionBase
            # El prefetch related incluye tarifa_base__especialidades
            if tarifa and hasattr(tarifa, 'tarifa_base') and tarifa.tarifa_base:
                especialidades_orm = list(tarifa.tarifa_base.especialidades.all())
            else:
                especialidades_orm = []
            primera_esp = especialidades_orm[0] if especialidades_orm else None

            revision_results.append({
                'id': str(lpo.id),
                'tarifa': {
                    'id': str(tarifa.id) if tarifa else '',
                    'derecho_minimo': float(tarifa.derecho_minimo) if tarifa and tarifa.derecho_minimo is not None else None,
                    'derecho_maximo': float(tarifa.derecho_maximo) if tarifa and tarifa.derecho_maximo is not None else None,
                    'porcentaje_minimo_uit': float(tarifa.porcentaje_minimo_uit) if tarifa and tarifa.porcentaje_minimo_uit is not None else None,
                },
                'especialidad_nombre': primera_esp.nombre if primera_esp else '',
                'especialidades': [{'id': str(esp.id), 'nombre': esp.nombre} for esp in especialidades_orm],
                'monto_base': float(lpo.valor_base_calculo) if lpo.valor_base_calculo else 0.0,
                'cobra': cobra,
                'numero_revision': liquidacion.numero_revision,
            })

        # Obtener valor_proyecto y valor_base_calculo
        valor_proyecto = Decimal('0')
        valor_base_calculo = Decimal('0')
        if lpo_list:
            lpo = lpo_list[0]
            valor_proyecto = lpo.valor_proyecto
            valor_base_calculo = lpo.valor_base_calculo if lpo.valor_base_calculo else valor_proyecto

        # Calcular totales desde datos persistidos
        subtotal = liquidacion.sub_total if liquidacion.sub_total else Decimal('0')
        igv_monto = subtotal * variables.igv_valor
        total_liquidacion = subtotal + igv_monto
        total_a_pagar = total_liquidacion

        return {
            'liquidacion': liquidacion,
            'proyecto': liquidacion.proyecto,
            'revision_results': revision_results,
            'subtotal': subtotal,
            'igv_monto': igv_monto,
            'total_liquidacion': total_liquidacion,
            'total_a_pagar': total_a_pagar,
            'variables': variables,
            'cobra': cobra,
            'liq_edif': liq_edif,
            'edificaciones_proyectistas': edificaciones_proyectistas,
            'edificaciones_delegados': edificaciones_delegados,
            'contactos_orm': contactos_orm,
            'valor_proyecto': valor_proyecto,
            'valor_base_calculo': valor_base_calculo,
        }

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
        valor_base_calculo: Decimal,
        porcentaje_liquidacion: Decimal,
    ) -> Decimal:
        """
        Calcula el monto base: valor_base_calculo * porcentaje_liquidacion.

        Args:
            valor_base_calculo: Valor base de cálculo (puede ser valor_proyecto o un valor alternativo)
            porcentaje_liquidacion: Porcentaje de liquidación (ej: 0.05 para 5%)

        Returns:
            Decimal con el monto base calculado
        """
        return Decimal(str(valor_base_calculo)) * porcentaje_liquidacion

    def calcular_revisiones(
        self,
        valor_base_calculo: Decimal,
        revisiones_data: list,
        cobra: bool,
        igv_valor: Decimal,
        numero_revision: Optional[int] = None,
    ) -> tuple[list, Decimal, Decimal, Decimal]:
        """
        Calcula el monto base, derecho y totales para una lista de revisiones.

        Args:
            valor_base_calculo: Valor base de cálculo para el cálculo (valor_proyecto o alternativo)
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
            # Support both EdificacionRevisionData (with .especialidades list)
            # and RevisionConTarifaData (with .especialidad_nombre string)
            if hasattr(rev_data, 'especialidades'):
                # EdificacionRevisionData style — M2M list of EspecialidadData
                especialidades_list = [
                    EspecialidadBasicaResult(id=esp.id, nombre=esp.nombre)
                    for esp in rev_data.especialidades
                ] if rev_data.especialidades else []
            else:
                # RevisionConTarifaData style — single especialidad_nombre string
                # Build list from the single specialty name
                especialidades_list = []

            monto_base = self.calcular_monto_base(
                valor_base_calculo,
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
                # For RevisionConTarifaData, build single-item especialidades list
                if not hasattr(rev_data, 'especialidades') and hasattr(rev_data, 'especialidad_nombre'):
                    especialidades_list = [EspecialidadBasicaResult(
                        id=rev_data.id,  # Use revision id as placeholder (no real specialty id in this path)
                        nombre=rev_data.especialidad_nombre,
                    )]
                revision_results.append(RevisionCalculoData(
                    id=str(rev_data.id),
                    numero_revision=numero_revision,
                    especialidad=rev_data.especialidad_nombre if hasattr(rev_data, 'especialidad_nombre') else (especialidades_list[0].nombre if especialidades_list else ""),
                    especialidades=especialidades_list,
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
                # For RevisionConTarifaData, build single-item especialidades list
                if not hasattr(rev_data, 'especialidades') and hasattr(rev_data, 'especialidad_nombre'):
                    especialidades_list = [EspecialidadBasicaResult(
                        id=rev_data.id,
                        nombre=rev_data.especialidad_nombre,
                    )]
                revision_results.append(CotizacionRevisionData(
                    id=rev_data.id,
                    especialidades=especialidades_list,
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
        # M2M: RevisionVigenteResult.especialidades es una lista;
        # RevisionConTarifaData.especialidad_nombre espera un string.
        # Se toma la primera especialidad (igual que _obtener_revisiones_por_ids).
        primera_esp = rev.especialidades[0] if rev.especialidades else None
        especialidad_nombre = primera_esp.nombre if primera_esp else ""

        return RevisionConTarifaData(
            id=rev.id,
            porcentaje_liquidacion=rev.porcentaje_liquidacion,
            tarifa=TarifaCalculoData(
                id=rev.tarifa_id,
                derecho_minimo=rev.derecho_minimo,
                derecho_maximo=rev.derecho_maximo,
                porcentaje_minimo_uit=rev.porcentaje_minimo_uit,
            ),
            especialidad_nombre=especialidad_nombre,
        )

    def _crear_proyecto_inline(self, data: ProyectoInlineData) -> Proyecto:
        """
        Crea un proyecto desde datos inline (proyecto_inline).

        Se usa cuando el proyecto no existe y se crea en línea durante
        la primera revisión de una liquidación de edificación.

        Implementa upsert de Entidad por numero_documento:
        - Si no existe, crea una nueva Entidad con los datos proporcionados.
        - Si existe, actualiza tipo_documento y razon_social si cambian.

        Luego crea el Proyecto con FK a la Entidad y copia los campos
        denormalizados entidad_razon_social, entidad_tipo_documento,
        entidad_numero_documento desde la Entidad resultante.

        Args:
            data: Datos inline del proyecto (denominacion, direccion, distrito_id, entidad)

        Returns:
            Proyecto creado
        """
        from modules.entidades.models import Entidad

        # Upsert Entidad por numero_documento
        entidad, created = Entidad.objects.update_or_create(
            numero_documento=data.entidad.numero_documento,
            defaults={
                'tipo_documento': data.entidad.tipo_documento,
                'razon_social': data.entidad.razon_social,
            }
        )

        # Generar public_id con el mismo formato que ProyectoService
        public_id = self._generar_public_id_proyecto()

        # Copiar campos denormalizados de entidad para preservar histórico
        # (estos campos en Proyecto son para queries rápidas y no dependen de la FK)
        entidad_razon_social = entidad.razon_social
        entidad_tipo_documento = entidad.tipo_documento
        entidad_numero_documento = entidad.numero_documento

        # Usar nombre_propietario del payload (viene a nivel proyecto_inline, no de entidad)
        nombre_propietario = data.nombre_propietario

        proyecto = Proyecto(
            denominacion=data.denominacion,
            direccion=data.direccion,
            distrito_id=data.distrito_id,
            entidad=entidad,
            entidad_razon_social=entidad_razon_social,
            entidad_tipo_documento=entidad_tipo_documento,
            entidad_numero_documento=entidad_numero_documento,
            nombre_propietario=nombre_propietario,
            public_id=public_id,
        )
        proyecto.save()
        return proyecto

    def _generar_public_id_proyecto(self) -> str:
        """
        Genera un public_id único para un proyecto.

        Formato: PROY-{year}-{count:05d}

        Returns:
            public_id generado
        """
        year = timezone.now().year
        count = Proyecto.objects.filter(
            public_id__startswith=f"PROY-{year}-"
        ).count()
        return f"PROY-{year}-{count + 1:05d}"

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
        4. Si se provee revision_id (ID de TarifaLiquidacionBase), la especialidad del delegado debe:
           a. Estar en el grupo EspecialidadesLiquidacion vigente para EDIFICACION
           b. Estar en las especialidades de la TarifaLiquidacionBase seleccionada
        5. Si se provee categoria, filtra por esa categoría en MunicipalidadesDelegado

        Args:
            municipalidad_id: UUID de la municipalidad
            fecha: Fecha actual para validar periodo
            revision_id: UUID opcional de TarifaLiquidacionBase para filtrar por especialidades
            categoria: Categoría del delegado (Edificaciones o Habilitaciones Urbanas)

        Returns:
            Lista de DelegadoVigenteResult con datos del delegado:
            id, nombre_completo, cip, especialidad: {id, nombre}, tipo
        """
        from django.db.models import Q, OuterRef, Subquery
        from ...models import Delegado, PeriodoDelegado, EspecialidadesLiquidacion, TarifaLiquidacionBase, MunicipalidadDelegado
        from ...constants import DelegadoStatus, TipoLiquidacion
        from ...schemas import DelegadoVigenteResult, EspecialidadBasicaResult
        from core.utils import esta_vigente

        # Annotate tipo and categoria from the specific MunicipalidadDelegado for this municipalidad
        # This replaces Delegado.tipo which was per-delegado; now tipo y categoria son per-assignment
        tipo_subquery = MunicipalidadDelegado.objects.filter(
            delegado=OuterRef('pk'),
            municipalidad_id=municipalidad_id,
        ).values_list('tipo', flat=True)[:1]

        categoria_subquery = MunicipalidadDelegado.objects.filter(
            delegado=OuterRef('pk'),
            municipalidad_id=municipalidad_id,
        ).values_list('categoria', flat=True)[:1]

        # Query: Join MunicipalidadesDelegado -> Delegado -> PeriodoDelegado
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

        # Si se provee revision_id (ID de TarifaLiquidacionBase), aplicar filtro adicional por especialidades
        if revision_id:
            # Obtener grupo de especialidades vigente para EDIFICACION
            grupo_vigente = EspecialidadesLiquidacion.objects.filter(
                tipo_liquidacion=TipoLiquidacion.EDIFICACION,
                periodo_inicio__lte=fecha,
            ).filter(
                Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha)
            ).first()

            if grupo_vigente:
                # Especialidades del grupo vigente (EspecialidadesLiquidacion)
                especialidades_vigente_ids = set(
                    grupo_vigente.especialidades.values_list('id', flat=True)
                )

                # Especialidades de la tarifa base seleccionada (TarifaLiquidacionBase)
                try:
                    tarifa_base = TarifaLiquidacionBase.objects.prefetch_related(
                        'especialidades'
                    ).get(id=revision_id)
                    tarifa_base_especialidades_ids = set(
                        tarifa_base.especialidades.values_list('id', flat=True)
                    )
                except TarifaLiquidacionBase.DoesNotExist:
                    tarifa_base_especialidades_ids = set()

                # Interseccion: vigentes que tambien estan en la tarifa base
                allowed_especialidades = especialidades_vigente_ids & tarifa_base_especialidades_ids

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

    def _validar_tarifa_por_tipo_tramite(
        self,
        tarifas_ids: list[str],
        tipo_tramite: str | None = None,
        tramite_accion: str | None = None,
    ) -> list:
        """
        Valida que cada tarifa en tarifas_ids exista, esté vigente, sea EDIFICACION
        y tenga detalle TarifaPorcentajeObra.

        Si tipo_tramite y tramite_accion son provistos, también valida que exista
        una ReglaTarifaEdificacion para esa combinación.

        Args:
            tarifas_ids: Lista de IDs de TarifaLiquidacionBase a validar.
            tipo_tramite: Tipo de trámite (opcional, para validar regla).
            tramite_accion: Acción de trámite (opcional, para validar regla).

        Returns:
            Lista de TarifaLiquidacionBase validadas.

        Raises:
            ValueError: Si alguna tarifa no existe, no está vigente, no es EDIFICACION,
                       o no tiene detalle TarifaPorcentajeObra, o no tiene regla para
                       la combinación tipo_tramite/tramite_accion.
        """
        from core.utils import esta_vigente
        from ...constants import TipoLiquidacion
        from ...models import ReglaTarifaEdificacion

        if not tarifas_ids:
            return []

        today = date.today()
        tarifa_bases = TarifaLiquidacionBase.objects.filter(id__in=tarifas_ids)
        found_ids = {str(tb.id) for tb in tarifa_bases}
        requested_ids = {str(id_) for id_ in tarifas_ids}

        missing_ids = requested_ids - found_ids
        if missing_ids:
            raise ValueError(
                f"Una o más tarifas en tarifas_ids no existen: {missing_ids}. "
                f"Verifique que está enviando IDs de TarifaLiquidacionBase válidos."
            )

        resultado = []
        for tb in tarifa_bases:
            # Validar tipo_liquidacion = EDIFICACION
            if tb.tipo_liquidacion != TipoLiquidacion.EDIFICACION:
                raise ValueError(
                    f"La tarifa {tb.id} no es de tipo_liquidacion=EDIFICACION "
                    f"(tipo actual: {tb.tipo_liquidacion}). "
                    f"Solo tarifas de Edificación son válidas para este trámite."
                )

            # Validar vigencia
            if not esta_vigente(tb.periodo_inicio, tb.periodo_fin):
                raise ValueError(
                    f"La tarifa {tb.id} no está vigente "
                    f"(periodo: {tb.periodo_inicio} - {tb.periodo_fin}). "
                    f"Verifique que la fecha actual esté dentro del período de vigencia."
                )

            # Validar que tenga detalle TarifaPorcentajeObra (relación OneToOne)
            try:
                detalle = tb.detalle_porcentual
                if detalle is None:
                    raise ValueError(
                        f"La tarifa {tb.id} no tiene detalle TarifaPorcentajeObra asociado. "
                        f"Verifique que la tarifa tenga su porcentaje configurado."
                    )
            except TarifaPorcentajeObra.DoesNotExist:
                raise ValueError(
                    f"La tarifa {tb.id} no tiene detalle TarifaPorcentajeObra asociado. "
                    f"Verifique que la tarifa tenga su porcentaje configurado."
                )

            # Validar que tenga al menos una especialidad asociada
            especialidades_count = tb.especialidades.count()
            if especialidades_count == 0:
                raise ValueError(
                    f"La tarifa {tb.id} no tiene especialidades asociadas. "
                    f"Cada tarifa debe tener al menos una especialidad para poder ser usada "
                    f"en liquidaciones de primera revisión. "
                    f"Verifique que la tarifa tenga especialidades configuradas en su grupo."
                )

            # Si se provee tipo_tramite y tramite_accion, validar regla
            if tipo_tramite is not None and tramite_accion is not None:
                regla_existe = ReglaTarifaEdificacion.objects.filter(
                    tarifa_base=tb,
                    tipo_tramite=tipo_tramite,
                    tramite_accion=tramite_accion,
                ).exists()
                if not regla_existe:
                    raise ValueError(
                        f"La tarifa {tb.id} no tiene una ReglaTarifaEdificacion para "
                        f"tipo_tramite={tipo_tramite} y tramite_accion={tramite_accion}. "
                        f"Verifique que la tarifa esté configurada para este tipo de trámite."
                    )

            resultado.append(tb)

        return resultado
