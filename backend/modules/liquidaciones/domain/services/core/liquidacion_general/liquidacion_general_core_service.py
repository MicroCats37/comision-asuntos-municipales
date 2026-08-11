"""
LiquidacionGeneralCoreService — sync ORM operations for general liquidacion entities.

PURE ORM — no business logic, no conditionals.
Handles: Entidad, Proyecto, LiquidacionGeneral.
"""
from decimal import Decimal
from typing import Optional
from datetime import date
import uuid

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.finanzas.domain.models.impuestos import UIT, IGV
from modules.entidades.domain.models import Entidad
from modules.liquidaciones.domain.constants import EstadoLiquidacion, TipoLiquidacion
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel


class LiquidacionGeneralCoreService:
    """
    Core sync service for general liquidacion ORM operations.
    Pure ORM — no business logic.
    """

    def get_uit_vigente(self) -> Optional[UIT]:
        return UIT.objects.vigente()

    def get_igv_vigente(self) -> Optional[IGV]:
        return IGV.objects.vigente()

    def create_entidad(
        self,
        tipo_documento: str,
        numero_documento: str,
    ) -> Entidad:
        """
        Creates or returns existing Entidad by numero_documento.
        Note: razon_social and direccion belong to Proyecto, not Entidad.
        """
        existente = Entidad.objects.filter(numero_documento=numero_documento).first()
        if existente:
            return existente
        return Entidad.objects.create(
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
        )

    def create_proyecto(
        self,
        proyecto_data: dict,
        entidad: Optional[Entidad] = None,
    ) -> Proyecto:
        """
        Creates a new Proyecto with denormalized entity data.
        """
        return Proyecto.objects.create(
            entidad=entidad,
            denominacion=proyecto_data["denominacion"],
            nombre_propietario=proyecto_data["nombre_propietario"],
            entidad_razon_social=proyecto_data.get("entidad_razon_social"),
            entidad_tipo_documento=proyecto_data.get("entidad_tipo_documento"),
            entidad_numero_documento=proyecto_data.get("entidad_numero_documento"),
            direccion=proyecto_data.get("direccion"),
            urbanizacion=proyecto_data.get("urbanizacion"),
            distrito_id=proyecto_data.get("distrito_id"),
        )

    def create_liquidacion_general(
        self,
        municipalidad_id: str,
        expediente: str,
        observacion: Optional[str],
        proyecto: Proyecto,
        tipo_liquidacion: str,
        numero_revision: int = 1,
    ) -> LiquidacionGeneral:
        """
        Creates a LiquidacionGeneral base record.
        Resolves tipo_liquidacion string/enum to TipoLiquidacion FK instance.
        """
        if isinstance(tipo_liquidacion, TipoLiquidacionModel):
            tipo_liq_obj = tipo_liquidacion
        else:
            tipo_liq_obj = TipoLiquidacionModel.objects.get(codigo=tipo_liquidacion)
        return LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad_id=municipalidad_id,
            expediente=expediente,
            observacion=observacion,
            estado=EstadoLiquidacion.PENDIENTE,
            tipo_liquidacion=tipo_liq_obj,
            numero_revision=numero_revision,
            sub_total=Decimal("0"),
            total=Decimal("0"),
        )

    def list_liquidaciones_by_type_paginated(
        self,
        tipo_liquidacion: str,
        page: int,
        page_size: int,
    ) -> tuple:
        """
        Returns paginated LiquidacionGeneral queryset for the given tipo_liquidacion.

        Uses select_related and prefetch_related to avoid N+1 queries.
        Returns (queryset, total_count).
        """
        qs = LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=tipo_liquidacion
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'edificaciones',
            'liquidacion_porcentaje_obra',
            'liquidacion_porcentaje_obra__detalles',
            'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
            'liquidacion_porcentaje_obra__detalles__especialidad',
            'liquidacion_porcentaje_obra__derecho_aplicado',
        ).order_by('-fecha_registro')

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_hu_paginated(
        self,
        page: int,
        page_size: int,
    ) -> tuple:
        """
        Returns paginated LiquidacionGeneral queryset for Habilitación Urbana.

        Uses select_related and prefetch_related to avoid N+1 queries.
        Prefetch chain specific to HU (M2 calculation type).
        Returns (queryset, total_count).
        """
        qs = LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.HABILITACION_URBANA
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'habilitacion_urbana',
            'liquidacion_m2',
            'liquidacion_m2__tarifa_aplicada',
            'liquidacion_m2__derecho',
        ).order_by('-fecha_registro')

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_ms_paginated(
        self,
        page: int,
        page_size: int,
    ) -> tuple:
        """
        Returns paginated LiquidacionGeneral queryset for Mecánica de Suelos.

        Uses select_related and prefetch_related to avoid N+1 queries.
        Prefetch chain specific to MS (M2 calculation type).
        Returns (queryset, total_count).
        """
        qs = LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.MECANICA_SUELOS
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'liquidacion_m2',
            'liquidacion_m2__tarifa_aplicada',
            'liquidacion_m2__derecho',
            'mecanica_suelos',
        ).order_by('-fecha_registro')

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_taludes_paginated(
        self,
        page: int,
        page_size: int,
    ) -> tuple:
        """
        Returns paginated LiquidacionGeneral queryset for Taludes.

        Uses select_related and prefetch_related to avoid N+1 queries.
        Prefetch chain mirrors Edificaciones/IV (PorcentajeObra calculation type):
        - 'liquidacion_porcentaje_obra' + nested relations
        - 'taludes' identity wrapper
        Returns (queryset, total_count).
        """
        qs = LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.TALUDES
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'taludes',
            'liquidacion_porcentaje_obra',
            'liquidacion_porcentaje_obra__detalles',
            'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
            'liquidacion_porcentaje_obra__detalles__especialidad',
            'liquidacion_porcentaje_obra__derecho_aplicado',
        ).order_by('-fecha_registro')

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_io_paginated(
        self,
        page: int,
        page_size: int,
    ) -> tuple:
        """
        Returns paginated LiquidacionGeneral queryset for Inspección de Obra.

        Uses select_related and prefetch_related to avoid N+1 queries.
        Prefetch chain for Visitas calculation type:
        - 'liquidacion_visitas' for calculation data
        - 'liquidacion_visitas__tarifa_aplicada' for tariff
        - 'inspeccion_obra' identity wrapper
        Returns (queryset, total_count).
        """
        qs = LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.INSPECCION_OBRA
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'inspeccion_obra',
            'liquidacion_visitas',
            'liquidacion_visitas__tarifa_aplicada',
        ).order_by('-fecha_registro')

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_iv_paginated(
        self,
        page: int,
        page_size: int,
    ) -> tuple:
        """
        Returns paginated LiquidacionGeneral queryset for Impacto Vial.

        Uses select_related and prefetch_related to avoid N+1 queries.
        Prefetch chain mirrors Edificaciones (PorcentajeObra calculation type):
        - 'liquidacion_porcentaje_obra' + nested relations
        - 'impacto_vial' identity wrapper
        Returns (queryset, total_count).
        """
        qs = LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.IMPACTO_VIAL
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'impacto_vial',
            'liquidacion_porcentaje_obra',
            'liquidacion_porcentaje_obra__detalles',
            'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
            'liquidacion_porcentaje_obra__detalles__especialidad',
            'liquidacion_porcentaje_obra__derecho_aplicado',
        ).order_by('-fecha_registro')

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    # ── Detail (GET /{id}) methods ─────────────────────────────────────────────────

    def get_liquidacion_edificacion_by_id(self, liquidacion_id: int) -> LiquidacionGeneral:
        """
        Returns a single LiquidacionGeneral for Edificaciones by ID.

        Uses the same prefetch chain as list_liquidaciones_by_type_paginated for EDIFICACION.
        Raises LiquidacionGeneral.DoesNotExist if not found.
        """
        return LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.EDIFICACION
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'edificaciones',
            'liquidacion_porcentaje_obra',
            'liquidacion_porcentaje_obra__detalles',
            'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
            'liquidacion_porcentaje_obra__detalles__especialidad',
            'liquidacion_porcentaje_obra__derecho_aplicado',
        ).get(id=liquidacion_id)

    def get_liquidacion_edificaciones_by_id(self, liquidacion_id: uuid.UUID) -> LiquidacionGeneral:
        """
        Returns a single LiquidacionGeneral for Edificaciones by UUID.

        Uses the EXACT SAME select_related and prefetch_related chain as
        list_liquidaciones_by_type_paginated for EDIFICACION.
        Raises LiquidacionGeneral.DoesNotExist if not found.
        """
        return LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.EDIFICACION
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'edificaciones',
            'liquidacion_porcentaje_obra',
            'liquidacion_porcentaje_obra__detalles',
            'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
            'liquidacion_porcentaje_obra__detalles__especialidad',
            'liquidacion_porcentaje_obra__derecho_aplicado',
        ).get(id=liquidacion_id)

    def get_liquidacion_hu_by_id(self, liquidacion_id: uuid.UUID) -> LiquidacionGeneral:
        """
        Returns a single LiquidacionGeneral for Habilitación Urbana by UUID.

        Uses the EXACT SAME select_related and prefetch_related chain as
        list_liquidaciones_hu_paginated.
        Raises LiquidacionGeneral.DoesNotExist if not found.
        """
        return LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.HABILITACION_URBANA
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'habilitacion_urbana',
            'liquidacion_m2',
            'liquidacion_m2__tarifa_aplicada',
            'liquidacion_m2__derecho',
        ).get(id=liquidacion_id)

    def get_liquidacion_ms_by_id(self, liquidacion_id: uuid.UUID) -> LiquidacionGeneral:
        """
        Returns a single LiquidacionGeneral for Mecánica de Suelos by UUID.

        Uses the EXACT SAME select_related and prefetch_related chain as
        list_liquidaciones_ms_paginated.
        Raises LiquidacionGeneral.DoesNotExist if not found.
        """
        return LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.MECANICA_SUELOS
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'liquidacion_m2',
            'liquidacion_m2__tarifa_aplicada',
            'liquidacion_m2__derecho',
            'mecanica_suelos',
        ).get(id=liquidacion_id)

    def get_liquidacion_taludes_by_id(self, liquidacion_id: uuid.UUID) -> LiquidacionGeneral:
        """
        Returns a single LiquidacionGeneral for Taludes by UUID.

        Uses the EXACT SAME select_related and prefetch_related chain as
        list_liquidaciones_taludes_paginated.
        Raises LiquidacionGeneral.DoesNotExist if not found.
        """
        return LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.TALUDES
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'taludes',
            'liquidacion_porcentaje_obra',
            'liquidacion_porcentaje_obra__detalles',
            'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
            'liquidacion_porcentaje_obra__detalles__especialidad',
            'liquidacion_porcentaje_obra__derecho_aplicado',
        ).get(id=liquidacion_id)

    def get_liquidacion_io_by_id(self, liquidacion_id: uuid.UUID) -> LiquidacionGeneral:
        """
        Returns a single LiquidacionGeneral for Inspección de Obra by UUID.

        Uses the EXACT SAME select_related and prefetch_related chain as
        list_liquidaciones_io_paginated.
        Raises LiquidacionGeneral.DoesNotExist if not found.
        """
        return LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.INSPECCION_OBRA
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'inspeccion_obra',
            'liquidacion_visitas',
            'liquidacion_visitas__tarifa_aplicada',
        ).get(id=liquidacion_id)

    def get_liquidacion_iv_by_id(self, liquidacion_id: uuid.UUID) -> LiquidacionGeneral:
        """
        Returns a single LiquidacionGeneral for Impacto Vial by UUID.

        Uses the same prefetch chain as list_liquidaciones_iv_paginated.
        Raises LiquidacionGeneral.DoesNotExist if not found.
        """
        return LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.IMPACTO_VIAL
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'impacto_vial',
            'liquidacion_porcentaje_obra',
            'liquidacion_porcentaje_obra__detalles',
            'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
            'liquidacion_porcentaje_obra__detalles__especialidad',
            'liquidacion_porcentaje_obra__derecho_aplicado',
        ).get(id=liquidacion_id)
