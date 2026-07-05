"""
Liquidaciones General Core — operaciones sync para liquidaciones generales.

Provee métodos para listar y obtener detalles de liquidaciones
independientemente del tipo (EDIFICACION, HABILITACION_URBANA, etc.).

NO usa transaction.atomic internamente — el flujo lo provee si es necesario.
"""
from decimal import Decimal
from typing import Optional
from django.db.models import QuerySet

from modules.liquidaciones.models import LiquidacionGeneral
from modules.liquidaciones.domain.schemas import (
    LiquidacionGeneralPaginatedResult,
    LiquidacionGeneralListItem,
    LiquidacionGeneralResult,
)


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
    ) -> tuple[list[dict], int]:
        """
        Lista liquidaciones generales con paginación.

        Args:
            page: Número de página (1-indexed)
            page_size: Elementos por página
            tipo_liquidacion: Filtro opcional por tipo de liquidación

        Returns:
            (lista_de_datos_materializados, total)
        """
        from modules.liquidaciones.domain.constants import TIPO_LIQUIDACION_TO_KIND_SLUG

        qs = LiquidacionGeneral.objects.all()

        # Filtro opcional por tipo de liquidación
        if tipo_liquidacion:
            qs = qs.filter(tipo_liquidacion=tipo_liquidacion)

        qs = qs.select_related(
            'proyecto', 'proyecto__entidad', 'municipalidad'
        ).prefetch_related(
            'liquidacion_m2', 'liquidacion_visitas'
        ).order_by('-created_at')

        total = qs.count()
        offset = (page - 1) * page_size
        qs = qs[offset:offset + page_size]

        liquidaciones = list(qs)
        if not liquidaciones:
            return [], total

        items = []
        for liq in liquidaciones:
            # Obtener total desde sub_total
            subtotal_val = float(liq.sub_total) if liq.sub_total else 0.0
            igv_valor = float(liq.igv.valor) if liq.igv and liq.igv.valor else 0.0
            igv_amount = subtotal_val * igv_valor
            total_liquidacion = subtotal_val + igv_amount
            total_a_pagar = total_liquidacion  # total_a_pagar = total_liquidacion en este contexto

            # Obtener valor_caracteristico según tipo
            valor_caracteristico = None
            tipo_liq_slug = TIPO_LIQUIDACION_TO_KIND_SLUG.get(liq.tipo_liquidacion, liq.tipo_liquidacion)

            if tipo_liq_slug in ("habilitacion-urbana", "mecanica-suelos", "impacto-vial", "taludes"):
                # M2 types - get area_solicitada from liquidacion_m2
                m2_data = getattr(liq, 'liquidacion_m2', None)
                if m2_data:
                    try:
                        m2_obj = m2_data.first()
                        if m2_obj:
                            valor_caracteristico = float(m2_obj.area_solicitada)
                    except Exception:
                        pass
            elif tipo_liq_slug == "inspeccion-obra":
                # IO type - get cantidad_visitas from liquidacion_visitas
                io_data = getattr(liq, 'liquidacion_visitas', None)
                if io_data:
                    try:
                        io_obj = io_data.first()
                        if io_obj:
                            valor_caracteristico = float(io_obj.cantidad_visitas)
                    except Exception:
                        pass

            items.append({
                'id': str(liq.id),
                'public_id': liq.public_id or '',
                'estado': liq.estado,
                'tipo_liquidacion': tipo_liq_slug,  # Convertido a slug
                'numero_revision': liq.numero_revision,
                'proyecto_denominacion': liq.proyecto.denominacion if liq.proyecto else '',
                'proyecto_public_id': str(liq.proyecto.public_id) if liq.proyecto and liq.proyecto.public_id else '',
                'fecha_registro': liq.created_at.isoformat() if liq.created_at else '',
                'total': total_liquidacion,
                # Campos adicionales para no-edificación
                'expediente': liq.expediente,
                'observacion': liq.observacion,
                'municipalidad_id': liq.municipalidad.id if liq.municipalidad else None,
                'municipalidad_nombre': liq.municipalidad.nombre if liq.municipalidad else None,
                'valor_caracteristico': valor_caracteristico,
                'subtotal': subtotal_val,
                'igv': igv_amount,
                'total_a_pagar': total_a_pagar,
            })
        return items, total

    def _listar_liquidaciones_paginado_result(
        self,
        page: int,
        page_size: int,
        tipo_liquidacion: Optional[str] = None,
    ) -> LiquidacionGeneralPaginatedResult:
        """Lista liquidaciones paginadas con datos para tabla (retorna result object)."""
        items_data, total = self._listar_liquidaciones_paginado(page, page_size, tipo_liquidacion)

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

        total_liquidacion = float(subtotal) if subtotal else 0.0
        igv_amount = total_liquidacion * float(igv_valor) if igv_valor else 0.0
        total_a_pagar = total_liquidacion + igv_amount

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
            subtotal=Decimal(str(total_liquidacion)) if total_liquidacion else Decimal('0'),
            igv=Decimal(str(igv_amount)) if igv_amount else Decimal('0'),
            total=Decimal(str(total_liquidacion + igv_amount)) if total_liquidacion or igv_amount else Decimal('0'),
            total_a_pagar=Decimal(str(total_a_pagar)) if total_a_pagar else Decimal('0'),
        )
