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

    def upsert_contacto(self, contacto_data: dict):
        """
        Upserts a Contacto by ALL fields (nombres, apellidos, dni, cargo, telefono, celular, email).
        If all fields match an existing Contacto, returns it; otherwise creates a new one.
        """
        from modules.entidades.domain.models.contacto import Contacto

        filtros = {
            "nombres": contacto_data.get("nombres"),
            "apellidos": contacto_data.get("apellidos"),
            "dni": contacto_data.get("dni"),
            "cargo": contacto_data.get("cargo"),
            "telefono": contacto_data.get("telefono"),
            "celular": contacto_data.get("celular"),
            "email": contacto_data.get("email"),
        }
        existente = Contacto.objects.filter(**filtros).first()
        if existente:
            return existente
        return Contacto.objects.create(**filtros)

    def create_contacto(
        self,
        contacto_data: dict,
    ):
        """
        Creates a new Contacto (contacto principal de la liquidación).
        DEPRECATED: Use upsert_contacto instead for nueva revision.
        """
        from modules.entidades.domain.models.contacto import Contacto

        return Contacto.objects.create(
            nombres=contacto_data.get("nombres"),
            apellidos=contacto_data.get("apellidos"),
            dni=contacto_data.get("dni"),
            cargo=contacto_data.get("cargo"),
            telefono=contacto_data.get("telefono"),
            celular=contacto_data.get("celular"),
            email=contacto_data.get("email"),
        )

    def create_liquidacion_general(
        self,
        municipalidad_id: str,
        expediente: str,
        observacion: Optional[str],
        proyecto: Proyecto,
        tipo_liquidacion: str,
        numero_revision: int = 1,
        contacto=None,
        retencion: bool = False,
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
            retencion=retencion,
            estado=EstadoLiquidacion.PENDIENTE,
            tipo_liquidacion=tipo_liq_obj,
            numero_revision=numero_revision,
            sub_total=Decimal("0"),
            total=Decimal("0"),
            contacto=contacto,
        )

    def list_liquidaciones_by_type_paginated(
        self,
        tipo_liquidacion: str,
        page: int,
        page_size: int,
        municipalidad_id=None,
        propietario=None,
        razon_social=None,
        creador_username=None,
        fecha_desde=None,
        fecha_hasta=None,
        numero=None,
        numero_revision=None,
        **kwargs
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

        # Apply filters
        if municipalidad_id:
            qs = qs.filter(municipalidad_id=municipalidad_id)
        if propietario:
            qs = qs.filter(proyecto__nombre_propietario__icontains=propietario)
        if razon_social:
            qs = qs.filter(proyecto__entidad_razon_social__icontains=razon_social)
        if creador_username:
            qs = qs.filter(usuario_creador__username__icontains=creador_username)
        if fecha_desde:
            qs = qs.filter(fecha_registro__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_registro__date__lte=fecha_hasta)
        if numero is not None:
            qs = qs.filter(edificaciones__numero=numero)
        if numero_revision is not None:
            qs = qs.filter(numero_revision=numero_revision)

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_hu_paginated(
        self,
        page: int,
        page_size: int,
        municipalidad_id=None,
        propietario=None,
        razon_social=None,
        creador_username=None,
        fecha_desde=None,
        fecha_hasta=None,
        numero=None,
        numero_revision=None,
        **kwargs
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

        # Apply filters
        if municipalidad_id:
            qs = qs.filter(municipalidad_id=municipalidad_id)
        if propietario:
            qs = qs.filter(proyecto__nombre_propietario__icontains=propietario)
        if razon_social:
            qs = qs.filter(proyecto__entidad_razon_social__icontains=razon_social)
        if creador_username:
            qs = qs.filter(usuario_creador__username__icontains=creador_username)
        if fecha_desde:
            qs = qs.filter(fecha_registro__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_registro__date__lte=fecha_hasta)
        if numero is not None:
            qs = qs.filter(habilitacion_urbana__numero=numero)
        if numero_revision is not None:
            qs = qs.filter(numero_revision=numero_revision)

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_ms_paginated(
        self,
        page: int,
        page_size: int,
        municipalidad_id=None,
        propietario=None,
        razon_social=None,
        creador_username=None,
        fecha_desde=None,
        fecha_hasta=None,
        numero=None,
        numero_revision=None,
        **kwargs
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

        # Apply filters
        if municipalidad_id:
            qs = qs.filter(municipalidad_id=municipalidad_id)
        if propietario:
            qs = qs.filter(proyecto__nombre_propietario__icontains=propietario)
        if razon_social:
            qs = qs.filter(proyecto__entidad_razon_social__icontains=razon_social)
        if creador_username:
            qs = qs.filter(usuario_creador__username__icontains=creador_username)
        if fecha_desde:
            qs = qs.filter(fecha_registro__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_registro__date__lte=fecha_hasta)
        if numero is not None:
            qs = qs.filter(mecanica_suelos__numero=numero)
        if numero_revision is not None:
            qs = qs.filter(numero_revision=numero_revision)

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_taludes_paginated(
        self,
        page: int,
        page_size: int,
        municipalidad_id=None,
        propietario=None,
        razon_social=None,
        creador_username=None,
        fecha_desde=None,
        fecha_hasta=None,
        numero=None,
        numero_revision=None,
        **kwargs
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

        # Apply filters
        if municipalidad_id:
            qs = qs.filter(municipalidad_id=municipalidad_id)
        if propietario:
            qs = qs.filter(proyecto__nombre_propietario__icontains=propietario)
        if razon_social:
            qs = qs.filter(proyecto__entidad_razon_social__icontains=razon_social)
        if creador_username:
            qs = qs.filter(usuario_creador__username__icontains=creador_username)
        if fecha_desde:
            qs = qs.filter(fecha_registro__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_registro__date__lte=fecha_hasta)
        if numero is not None:
            qs = qs.filter(taludes__numero=numero)
        if numero_revision is not None:
            qs = qs.filter(numero_revision=numero_revision)

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_io_paginated(
        self,
        page: int,
        page_size: int,
        municipalidad_id=None,
        propietario=None,
        razon_social=None,
        creador_username=None,
        fecha_desde=None,
        fecha_hasta=None,
        numero=None,
        numero_revision=None,
        **kwargs
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

        # Apply filters
        if municipalidad_id:
            qs = qs.filter(municipalidad_id=municipalidad_id)
        if propietario:
            qs = qs.filter(proyecto__nombre_propietario__icontains=propietario)
        if razon_social:
            qs = qs.filter(proyecto__entidad_razon_social__icontains=razon_social)
        if creador_username:
            qs = qs.filter(usuario_creador__username__icontains=creador_username)
        if fecha_desde:
            qs = qs.filter(fecha_registro__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_registro__date__lte=fecha_hasta)
        if numero is not None:
            qs = qs.filter(inspeccion_obra__numero=numero)
        if numero_revision is not None:
            qs = qs.filter(numero_revision=numero_revision)

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_iv_paginated(
        self,
        page: int,
        page_size: int,
        municipalidad_id=None,
        propietario=None,
        razon_social=None,
        creador_username=None,
        fecha_desde=None,
        fecha_hasta=None,
        numero=None,
        numero_revision=None,
        **kwargs
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

        # Apply filters
        if municipalidad_id:
            qs = qs.filter(municipalidad_id=municipalidad_id)
        if propietario:
            qs = qs.filter(proyecto__nombre_propietario__icontains=propietario)
        if razon_social:
            qs = qs.filter(proyecto__entidad_razon_social__icontains=razon_social)
        if creador_username:
            qs = qs.filter(usuario_creador__username__icontains=creador_username)
        if fecha_desde:
            qs = qs.filter(fecha_registro__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_registro__date__lte=fecha_hasta)
        if numero is not None:
            qs = qs.filter(impacto_vial__numero=numero)
        if numero_revision is not None:
            qs = qs.filter(numero_revision=numero_revision)

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

    def list_ultimas_revisiones_por_proyecto(
        self,
        tipo_liquidacion: str,
        page: int,
        page_size: int,
        razon_social=None,
        numero_documento=None,
        fecha_desde=None,
        fecha_hasta=None,
    ) -> tuple:
        """
        Returns paginated LiquidacionGeneral queryset containing only the latest revision
        per project for the given tipo_liquidacion.

        Applies optional filters and returns only the liquidacion with the highest
        numero_revision for each proyecto.
        Uses select_related and prefetch_related like list_liquidaciones_by_type_paginated.
        Returns (queryset, total_count).
        """
        from django.db.models import Max, OuterRef, Subquery

        # Base queryset with same prefetch chain as list_liquidaciones_by_type_paginated
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
        )

        # Apply filters
        if razon_social:
            qs = qs.filter(proyecto__entidad_razon_social__icontains=razon_social)
        if numero_documento:
            qs = qs.filter(proyecto__entidad_numero_documento=numero_documento)
        if fecha_desde:
            qs = qs.filter(fecha_registro__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_registro__date__lte=fecha_hasta)

        # Subquery to get max numero_revision per proyecto
        max_rev_subquery = LiquidacionGeneral.objects.filter(
            proyecto_id=OuterRef('proyecto_id'),
            tipo_liquidacion__codigo=tipo_liquidacion,
        ).order_by().values('proyecto_id').annotate(
            max_rev=Max('numero_revision')
        ).values('max_rev')[:1]

        qs = qs.filter(numero_revision=Subquery(max_rev_subquery))

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def get_ultima_revision_por_proyecto(
        self,
        proyecto_id: uuid.UUID,
        tipo_liquidacion: str,
    ) -> Optional[LiquidacionGeneral]:
        """
        Returns the LiquidacionGeneral with the highest numero_revision for a given proyecto.
        Optionally filters by tipo_liquidacion.
        Returns None if no liquidacion exists for the proyecto.
        """
        qs = LiquidacionGeneral.objects.filter(
            proyecto_id=proyecto_id,
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
        ).prefetch_related(
            'edificaciones',
            'liquidacion_porcentaje_obra',
            'liquidacion_porcentaje_obra__detalles',
            'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
            'liquidacion_porcentaje_obra__detalles__especialidad',
            'liquidacion_porcentaje_obra__derecho_aplicado',
        )
        # El tipo_liquidacion siempre viene validado por el orquestador.
        qs = qs.filter(tipo_liquidacion__codigo=tipo_liquidacion)
        return qs.order_by('-numero_revision').first()
