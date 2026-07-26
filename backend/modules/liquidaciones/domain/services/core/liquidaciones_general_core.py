"""
Liquidaciones General Core — operaciones sync para liquidaciones generales.

Provee métodos para listar y obtener detalles de liquidaciones
independientemente del tipo (EDIFICACION, HABILITACION_URBANA, etc.).

NO usa transaction.atomic internamente — el flujo lo provee si es necesario.
"""
import uuid as _uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from django.db.models import QuerySet, Prefetch

from modules.liquidaciones.models import LiquidacionGeneral
from modules.liquidaciones.domain.schemas import (
    LiquidacionGeneralPaginatedResult,
    LiquidacionGeneralListItem,
    LiquidacionGeneralResult,
    ProyectoListItemInfo,
    EntidadListItemInfo,
    MunicipalidadInfo,
    ValoresListItemInfo,
    ProyectistaListItemData,
    DelegadoListItemData,
    ContactoListItemData,
    TarifaRevisionData,
    EspecialidadRevisionData,
    RevisionListItemData,
)


# M² liquidacion types — IGV must NOT be added to total_a_pagar
# NOTA: IMPACTO_VIAL y TALUDES fueron migrados a cálculo porcentual (Edificaciones-style) con IGV
M2_LIQUIDACION_TYPES = frozenset({
    "HABILITACION_URBANA",
    "MECANICA_SUELOS",
})


class LiquidacionesGeneralService:
    """
    Servicio core sync para operaciones de Liquidaciones Generales.

    Lista y obtiene detalles de liquidaciones de cualquier tipo.
    """

    def _listar_liquidaciones_paginado(
        self,
        page: int,
        page_size: int,
        tipo_liquidacion: Optional[str] = None,
        liquidacion_id: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        """
        Lista liquidaciones generales con paginación y datos ricos.

        Args:
            page: Número de página (1-indexed)
            page_size: Elementos por página
            tipo_liquidacion: Filtro opcional por tipo de liquidación
            liquidacion_id: Filtro opcional por ID de liquidación (para obtener un solo item)

        Returns:
            (lista_de_datos_materializados, total)
        """
        from modules.liquidaciones.models import LiquidacionProyectista, LiquidacionDelegado, LiquidacionContacto

        qs = LiquidacionGeneral.objects.all()

        if tipo_liquidacion:
            qs = qs.filter(tipo_liquidacion=tipo_liquidacion)

        if liquidacion_id:
            qs = qs.filter(id=liquidacion_id)

        qs = qs.select_related(
            'proyecto', 'proyecto__entidad', 'municipalidad', 'igv',
        ).prefetch_related(
            'liquidacion_m2',
            'liquidacion_visitas',
            'edificaciones',
            'liquidacion_porcentaje_obra__tarifa_aplicada__tarifa_base__especialidades',
            Prefetch(
                'liquidacion_proyectistas',
                queryset=LiquidacionProyectista.objects.select_related(
                    'proyectista__perfil_ingeniero', 'proyectista__especialidad'
                )
            ),
            Prefetch(
                'liquidacion_delegados',
                queryset=LiquidacionDelegado.objects.select_related(
                    'delegado__perfil_ingeniero', 'delegado__especialidad'
                )
            ),
            Prefetch(
                'contactos',
                queryset=LiquidacionContacto.objects.select_related('contacto')
            ),
        ).order_by('-created_at')

        total = qs.count()
        offset = (page - 1) * page_size
        qs = qs[offset:offset + page_size]

        liquidaciones = list(qs)
        if not liquidaciones:
            return [], total

        items = []
        for liq in liquidaciones:
            subtotal_val = float(liq.sub_total) if liq.sub_total else 0.0
            igv_valor = float(liq.igv.valor) if liq.igv and liq.igv.valor else 0.0
            igv_amount = subtotal_val * igv_valor

            tipo_liq_slug = (
                liq.tipo_liquidacion.lower().replace('_', '-')
                if liq.tipo_liquidacion else 'edificacion'
            )

            # M² types must not add IGV to total_a_pagar
            is_m2 = liq.tipo_liquidacion in M2_LIQUIDACION_TYPES
            if is_m2:
                igv_amount = 0.0
                total_a_pagar = subtotal_val
                total_liquidacion = subtotal_val  # M2: total does not include IGV
            else:
                total_a_pagar = subtotal_val + igv_amount
                total_liquidacion = total_a_pagar

            # --- Proyecto ---
            valor_proyecto = 0.0
            lpo_list = list(liq.liquidacion_porcentaje_obra.all())
            if lpo_list and lpo_list[0].valor_proyecto:
                valor_proyecto = float(lpo_list[0].valor_proyecto)

            proyecto_dict = {
                'id': str(liq.proyecto.id) if liq.proyecto else '',
                'public_id': str(liq.proyecto.public_id) if liq.proyecto and liq.proyecto.public_id else '',
                'nombre': liq.proyecto.denominacion if liq.proyecto else '',
                'direccion': liq.proyecto.direccion if liq.proyecto else None,
                'valor_proyecto': valor_proyecto,
                'entidad_id': str(liq.proyecto.entidad.id) if liq.proyecto and liq.proyecto.entidad else None,
                'entidad_tipo': liq.proyecto.entidad.tipo_documento if liq.proyecto and liq.proyecto.entidad else None,
                'entidad_nombre': liq.proyecto.entidad.razon_social if liq.proyecto and liq.proyecto.entidad else None,
                'entidad_ruc': liq.proyecto.entidad.numero_documento if liq.proyecto and liq.proyecto.entidad else None,
            }

            # --- Entidad ---
            entidad_dict = None
            if liq.proyecto and liq.proyecto.entidad:
                entidad_dict = {
                    'id': str(liq.proyecto.entidad.id),
                    'tipo': liq.proyecto.entidad.tipo_documento,
                    'nombre': liq.proyecto.entidad.razon_social,
                    'ruc': liq.proyecto.entidad.numero_documento,
                }

            # --- Municipalidad ---
            muni_dict = {
                'id': str(liq.municipalidad.id) if liq.municipalidad else '',
                'nombre': liq.municipalidad.nombre if liq.municipalidad else '',
                'codigo': None,
                'provincia': None,
                'distrito': None,
            }

            # --- Valores ---
            valores_dict = {
                'subtotal': subtotal_val,
                'igv': igv_amount,
                'total': total_liquidacion,
                'total_a_pagar': total_a_pagar,
            }

            # --- Proyectistas ---
            proyectistas_list = []
            for lp in liq.liquidacion_proyectistas.all():
                p = lp.proyectista
                perfil = p.perfil_ingeniero if p else None
                esp = p.especialidad if p else None
                proyectistas_list.append({
                    'id': str(p.id) if p else '',
                    'perfil_ingeniero_id': str(perfil.id) if perfil else None,
                    'perfil_ingeniero_nombres': perfil.nombres if perfil else None,
                    'perfil_ingeniero_apellidos': f"{perfil.apellido_paterno or ''} {perfil.apellido_materno or ''}".strip() or None if perfil else None,
                    'perfil_ingeniero_cip': perfil.cip if perfil else None,
                    'especialidad_id': str(esp.id) if esp else None,
                    'especialidad_nombre': esp.nombre if esp else None,
                    'descripcion': p.descripcion if p and p.descripcion else '',
                })

            # --- Delegados ---
            delegados_list = []
            for ld in liq.liquidacion_delegados.all():
                d = ld.delegado
                perfil = d.perfil_ingeniero if d else None
                esp = d.especialidad if d else None
                delegados_list.append({
                    'id': str(d.id) if d else '',
                    'perfil_ingeniero_id': str(perfil.id) if perfil else None,
                    'perfil_ingeniero_nombres': perfil.nombres if perfil else None,
                    'perfil_ingeniero_apellidos': f"{perfil.apellido_paterno or ''} {perfil.apellido_materno or ''}".strip() or None if perfil else None,
                    'perfil_ingeniero_cip': perfil.cip if perfil else None,
                    'especialidad_id': str(esp.id) if esp else None,
                    'especialidad_nombre': esp.nombre if esp else None,
                    'tipo': ld.periodo if ld.periodo else None,
                })

            # --- Contactos ---
            contactos_list = []
            for lc in liq.contactos.all():
                c = lc.contacto
                contactos_list.append({
                    'id': str(c.id) if c else '',
                    'nombres': c.nombres if c else None,
                    'apellidos': c.apellidos if c else None,
                    'dni': getattr(c, 'dni', None),
                    'cargo': getattr(c, 'cargo', None),
                    'telefono': getattr(c, 'telefono', None),
                    'celular': getattr(c, 'celular', None),
                    'email': getattr(c, 'email', None),
                    'direccion': getattr(c, 'direccion', None),
                    'principal': lc.principal,
                    'descripcion': lc.descripcion,
                })

            # --- Revisiones ---
            revisiones_list = []
            tipo_enum = liq.tipo_liquidacion

            if tipo_enum == 'EDIFICACION':
                for lpo in lpo_list:
                    tarifa = lpo.tarifa_aplicada
                    especialidades_list = []
                    if tarifa and tarifa.tarifa_base:
                        for esp in tarifa.tarifa_base.especialidades.all():
                            especialidades_list.append({
                                'id': str(esp.id),
                                'nombre': esp.nombre,
                            })
                    # All tariff fields from TarifaPorcentajeObra
                    revisiones_list.append({
                        'id': str(lpo.id),
                        'especialidades': especialidades_list,
                        'tarifa': {
                            'id': str(tarifa.id) if tarifa else '',
                            'derecho_minimo': float(tarifa.derecho_minimo) if tarifa and tarifa.derecho_minimo is not None else None,
                            'derecho_maximo': float(tarifa.derecho_maximo) if tarifa and tarifa.derecho_maximo is not None else None,
                            'porcentaje_minimo_uit': float(tarifa.porcentaje_minimo_uit) if tarifa and tarifa.porcentaje_minimo_uit is not None else None,
                            'porcentaje_liquidacion': float(tarifa.porcentaje_liquidacion) if tarifa and tarifa.porcentaje_liquidacion is not None else None,
                        },
                    })
            elif tipo_enum in ('IMPACTO_VIAL', 'TALUDES'):
                # IMPACTO_VIAL y TALUDES ahora usan LiquidacionPorcentajeObra (Edificaciones-style)
                for lpo in lpo_list:
                    tarifa = lpo.tarifa_aplicada
                    especialidades_list = []
                    if tarifa and tarifa.tarifa_base:
                        for esp in tarifa.tarifa_base.especialidades.all():
                            especialidades_list.append({
                                'id': str(esp.id),
                                'nombre': esp.nombre,
                            })
                    # All tariff fields from TarifaPorcentajeObra
                    revisiones_list.append({
                        'id': str(lpo.id),
                        'especialidades': especialidades_list,
                        'tarifa': {
                            'id': str(tarifa.id) if tarifa else '',
                            'derecho_minimo': float(tarifa.derecho_minimo) if tarifa and tarifa.derecho_minimo is not None else None,
                            'derecho_maximo': float(tarifa.derecho_maximo) if tarifa and tarifa.derecho_maximo is not None else None,
                            'porcentaje_minimo_uit': float(tarifa.porcentaje_minimo_uit) if tarifa and tarifa.porcentaje_minimo_uit is not None else None,
                            'porcentaje_liquidacion': float(tarifa.porcentaje_liquidacion) if tarifa and tarifa.porcentaje_liquidacion is not None else None,
                        },
                    })
            elif tipo_enum in ('HABILITACION_URBANA', 'MECANICA_SUELOS'):
                # Iterate over ALL liquidacion_m2 records, not just first
                for m2_data in liq.liquidacion_m2.all():
                    if not m2_data.tarifa_aplicada:
                        continue
                    t = m2_data.tarifa_aplicada
                    especialidades_list = []
                    if t.tarifa_base:
                        for esp in t.tarifa_base.especialidades.all():
                            especialidades_list.append({
                                'id': str(esp.id),
                                'nombre': esp.nombre,
                            })
                    # Get completo M2 fields from TarifaPorMetroCuadrado (direct attributes)
                    costo_por_m2 = float(t.costo_por_m2) if t.costo_por_m2 is not None else None
                    area_m2 = float(t.area_m2) if t.area_m2 is not None else None
                    derecho_minimo = float(t.derecho_minimo) if t.derecho_minimo is not None else None
                    derecho_maximo = float(t.derecho_maximo) if t.derecho_maximo is not None else None
                    area_solicitada = float(m2_data.area_solicitada) if m2_data.area_solicitada is not None else None
                    revisiones_list.append({
                        'id': str(m2_data.id),
                        'especialidades': especialidades_list,
                        'tarifa': {
                            'id': str(t.id),
                            'costo_por_m2': costo_por_m2,
                            'area_m2': area_m2,
                            'area_solicitada': area_solicitada,
                            'derecho_minimo': derecho_minimo,
                            'derecho_maximo': derecho_maximo,
                        },
                    })
            elif tipo_enum == 'INSPECCION_OBRA':
                # Iterate over ALL liquidacion_visitas records, not just first
                for v_data in liq.liquidacion_visitas.all():
                    if not v_data.tarifa_aplicada:
                        continue
                    t = v_data.tarifa_aplicada
                    especialidades_list = []
                    if t.tarifa_base:
                        for esp in t.tarifa_base.especialidades.all():
                            especialidades_list.append({
                                'id': str(esp.id),
                                'nombre': esp.nombre,
                            })
                    # Get completo IO fields from TarifaPorCategoriaVisitas (direct attributes)
                    costo_por_visita = float(t.costo_por_visita) if t.costo_por_visita is not None else None
                    visitas_minimas = t.visitas_minimas
                    revisiones_list.append({
                        'id': str(v_data.id),
                        'especialidades': especialidades_list,
                        'tarifa': {
                            'id': str(t.id),
                            'costo_por_visita': costo_por_visita,
                            'visitas_minimas': visitas_minimas,
                            'cantidad_visitas': v_data.cantidad_visitas,
                            'categoria': v_data.categoria,
                        },
                    })

            # --- tramite_accion y tipo_tramite ---
            tramite_accion = None
            tipo_tramite = None
            if tipo_enum == 'EDIFICACION' and liq.edificaciones:
                tramite_accion = liq.edificaciones.tramite_accion
                tipo_tramite = liq.edificaciones.tipo_tramite
            elif tipo_enum in ('IMPACTO_VIAL', 'TALUDES'):
                # IMPACTO_VIAL y TALUDES ahora usan LiquidacionPorcentajeObra
                # pero aún tienen extension models con tramite_accion
                type_attr_map = {
                    'IMPACTO_VIAL': 'impacto_vial',
                    'TALUDES': 'taludes',
                }
                attr_name = type_attr_map.get(tipo_enum)
                if attr_name:
                    ext_model = getattr(liq, attr_name, None)
                    if ext_model:
                        tramite_accion = getattr(ext_model, 'tramite_accion', None)
            elif tipo_enum in ('HABILITACION_URBANA', 'MECANICA_SUELOS'):
                type_attr_map = {
                    'HABILITACION_URBANA': 'habilitacion_urbana',
                    'MECANICA_SUELOS': 'mecanica_suelos',
                }
                attr_name = type_attr_map.get(tipo_enum)
                if attr_name:
                    ext_model = getattr(liq, attr_name, None)
                    if ext_model:
                        tramite_accion = getattr(ext_model, 'tramite_accion', None)
            elif tipo_enum == 'INSPECCION_OBRA':
                ext_model = getattr(liq, 'inspeccion_obra', None)
                if ext_model:
                    tramite_accion = getattr(ext_model, 'tramite_accion', None)

            items.append({
                'id': str(liq.id),
                'public_id': liq.public_id or '',
                'estado': liq.estado,
                'tipo_liquidacion': tipo_liq_slug,
                'numero_revision': liq.numero_revision,
                'fecha_registro': liq.created_at.isoformat() if liq.created_at else '',
                'tramite_accion': tramite_accion,
                'tipo_tramite': tipo_tramite,
                'expediente': liq.expediente,
                'observacion': liq.observacion,
                'proyecto': proyecto_dict,
                'entidad': entidad_dict,
                'municipalidad': muni_dict,
                'valores': valores_dict,
                'proyectistas': proyectistas_list,
                'delegados': delegados_list,
                'contactos': contactos_list,
                'revisiones': revisiones_list,
                'subtotal': subtotal_val,
                'igv': igv_amount,
                'total': total_liquidacion,
                'total_a_pagar': total_a_pagar,
            })
        return items, total

    def _listar_liquidaciones_paginado_result(
        self,
        page: int,
        page_size: int,
        tipo_liquidacion: Optional[str] = None,
        liquidacion_id: Optional[str] = None,
    ) -> LiquidacionGeneralPaginatedResult:
        """Lista liquidaciones paginadas con datos para tabla (retorna result object)."""
        items_data, total = self._listar_liquidaciones_paginado(
            page, page_size, tipo_liquidacion, liquidacion_id
        )

        items = [
            LiquidacionGeneralListItem(**item)
            for item in items_data
        ]
        return LiquidacionGeneralPaginatedResult(items=items, total=total)

    def _obtener_liquidacion_por_id(self, liquidacion_id: str) -> Optional[LiquidacionGeneral]:
        """
        Obtiene una LiquidacionGeneral por ID con relaciones preload.

        Args:
            liquidacion_id: UUID de la liquidación

        Returns:
            LiquidacionGeneral con select_related o None si no existe
        """
        try:
            return LiquidacionGeneral.objects.select_related(
                'proyecto', 'proyecto__entidad', 'municipalidad', 'igv', 'uit'
            ).prefetch_related(
                'liquidacion_porcentaje_obra'
            ).get(id=liquidacion_id)
        except LiquidacionGeneral.DoesNotExist:
            return None

    def _obtener_liquidacion_por_id_result(self, liquidacion_id: str) -> Optional[LiquidacionGeneralResult]:
        """
        Obtiene el resultado de una liquidación por ID como DTO.

        Args:
            liquidacion_id: UUID de la liquidación

        Returns:
            LiquidacionGeneralResult o None si no existe
        """
        liquidacion = self._obtener_liquidacion_por_id(liquidacion_id)
        if not liquidacion:
            return None

        # Obtener totales desde liquidacion_porcentaje_obra si existe
        subtotal = liquidacion.sub_total
        igv_valor = Decimal('0')
        if liquidacion.igv and liquidacion.igv.valor:
            igv_valor = liquidacion.igv.valor

        subtotal_val = float(subtotal) if subtotal else 0.0
        igv_amount = subtotal_val * float(igv_valor) if igv_valor else 0.0
        # M² types must not add IGV to total_a_pagar
        is_m2 = liquidacion.tipo_liquidacion in M2_LIQUIDACION_TYPES
        if is_m2:
            igv_amount = 0.0
            total_a_pagar = subtotal_val
            total_liquidacion = subtotal_val  # M2: total does not include IGV
        else:
            total_a_pagar = subtotal_val + igv_amount
            total_liquidacion = total_a_pagar

        # Obtener nombre de municipalidad
        municipalidad_nombre = None
        if liquidacion.municipalidad:
            municipalidad_nombre = liquidacion.municipalidad.nombre

        return LiquidacionGeneralResult(
            id=liquidacion.id,
            public_id=liquidacion.public_id or '',
            estado=liquidacion.estado,
            tipo_liquidacion=liquidacion.tipo_liquidacion,
            numero_revision=liquidacion.numero_revision,
            fecha_registro=liquidacion.created_at.isoformat() if liquidacion.created_at else '',
            expediente=liquidacion.expediente,
            observacion=liquidacion.observacion,
            # Entidad
            entidad_id=liquidacion.proyecto.entidad.id if liquidacion.proyecto and liquidacion.proyecto.entidad else None,
            entidad_tipo=liquidacion.proyecto.entidad.tipo_documento if liquidacion.proyecto and liquidacion.proyecto.entidad else None,
            entidad_nombre=liquidacion.proyecto.entidad.razon_social if liquidacion.proyecto and liquidacion.proyecto.entidad else None,
            entidad_ruc=liquidacion.proyecto.entidad.numero_documento if liquidacion.proyecto and liquidacion.proyecto.entidad else None,
            # Proyecto
            proyecto_id=liquidacion.proyecto.id if liquidacion.proyecto else None,
            proyecto_public_id=str(liquidacion.proyecto.public_id) if liquidacion.proyecto and liquidacion.proyecto.public_id else None,
            proyecto_nombre=liquidacion.proyecto.denominacion if liquidacion.proyecto else None,
            proyecto_direccion=liquidacion.proyecto.direccion if liquidacion.proyecto else None,
            # Municipalidad
            municipalidad_id=liquidacion.municipalidad.id if liquidacion.municipalidad else None,
            municipalidad_nombre=municipalidad_nombre,
            # Campos financieros
            subtotal=Decimal(str(subtotal_val)) if subtotal_val else Decimal('0'),
            igv=Decimal(str(igv_amount)) if igv_amount else Decimal('0'),
            total=Decimal(str(total_liquidacion)) if total_liquidacion else Decimal('0'),
            total_a_pagar=Decimal(str(total_a_pagar)) if total_a_pagar else Decimal('0'),
        )

    def _obtener_delegados_vigentes(
        self,
        municipalidad_id: str,
        fecha: date,
        tipo_liquidacion: str,
        revision_id: str,
        categoria: str | None = None,
    ) -> list:
        from django.db.models import Q, OuterRef, Subquery, Exists
        from ...models import Delegado, EspecialidadesLiquidacion, TarifaLiquidacionBase
        from ...models.delegado import MunicipalidadDelegado
        from ...constants import DelegadoStatus
        from ...schemas import DelegadoVigenteResult, EspecialidadBasicaResult

        tipo_subquery = MunicipalidadDelegado.objects.filter(
            delegado=OuterRef('pk'),
            municipalidad_id=municipalidad_id,
        ).values_list('tipo', flat=True)[:1]

        muni_filter = MunicipalidadDelegado.objects.filter(
            delegado=OuterRef('pk'),
            municipalidad_id=municipalidad_id,
            activo=True,
        )
        if categoria:
            muni_filter = muni_filter.filter(categoria=categoria)

        queryset = (
            Delegado.objects
            .select_related('perfil_ingeniero', 'especialidad')
            .annotate(municipalidad_tipo=Subquery(tipo_subquery))
            .filter(
                Q(periodos_asignados__periodo_fin__gte=fecha) | Q(periodos_asignados__periodo_fin__isnull=True),
                status=DelegadoStatus.ACTIVO,
                periodos_asignados__periodo_inicio__lte=fecha,
            )
            .filter(Exists(muni_filter))
            .distinct()
        )

        grupo_vigente = EspecialidadesLiquidacion.objects.filter(
            tipo_liquidacion=tipo_liquidacion,
            periodo_inicio__lte=fecha,
        ).filter(
            Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha)
        ).first()

        if grupo_vigente:
            especialidades_vigente_ids = set(
                grupo_vigente.especialidades.values_list('id', flat=True)
            )

            tarifa_base = None
            try:
                tarifa_base = TarifaLiquidacionBase.objects.prefetch_related(
                    'especialidades'
                ).get(id=revision_id)
            except TarifaLiquidacionBase.DoesNotExist:
                try:
                    from ...models import LiquidacionPorcentajeObra
                    lpo = LiquidacionPorcentajeObra.objects.select_related(
                        'tarifa_aplicada__tarifa_base'
                    ).get(id=revision_id)
                    tarifa_base = lpo.tarifa_aplicada.tarifa_base
                except (LiquidacionPorcentajeObra.DoesNotExist, AttributeError):
                    pass

            if tarifa_base:
                tarifa_base_especialidades_ids = set(
                    tarifa_base.especialidades.values_list('id', flat=True)
                )
            else:
                tarifa_base_especialidades_ids = set()

            allowed_especialidades = especialidades_vigente_ids & tarifa_base_especialidades_ids

            if allowed_especialidades:
                queryset = queryset.filter(especialidad_id__in=allowed_especialidades)
            else:
                return []
        else:
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
