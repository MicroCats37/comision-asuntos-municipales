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
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
    LiquidacionDelegadoEnGeneralResult,
    ProyectoResult,
    EntidadResult,
    UsuarioCreadorResult,
    ContactoResult,
    MunicipalidadResult,
    IgvResult,
    UitResult,
    DistritoResult,
    ProvinciaResult,
    DepartamentoResult,
    TipoLiquidacionResult,
)


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

    # ── PREFETCH CHAINS & NUMERO FILTER FIELD MAPS ─────────────────────────────────

    # Maps tipo_liquidacion codigo → prefetch_related arguments
    _PREFETCH_MAP = {
        TipoLiquidacion.EDIFICACION: [
            'edificaciones',
            'liquidacion_porcentaje_obra',
            'liquidacion_porcentaje_obra__detalles',
            'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
            'liquidacion_porcentaje_obra__detalles__especialidad',
            'liquidacion_porcentaje_obra__derecho_aplicado',
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
        ],
        TipoLiquidacion.HABILITACION_URBANA: [
            'habilitacion_urbana',
            'liquidacion_m2',
            'liquidacion_m2__tarifa_aplicada',
            'liquidacion_m2__derecho',
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
        ],
        TipoLiquidacion.MECANICA_SUELOS: [
            'liquidacion_m2',
            'liquidacion_m2__tarifa_aplicada',
            'liquidacion_m2__derecho',
            'mecanica_suelos',
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
        ],
        TipoLiquidacion.TALUDES: [
            'taludes',
            'liquidacion_porcentaje_obra',
            'liquidacion_porcentaje_obra__detalles',
            'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
            'liquidacion_porcentaje_obra__detalles__especialidad',
            'liquidacion_porcentaje_obra__derecho_aplicado',
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
        ],
        TipoLiquidacion.INSPECCION_OBRA: [
            'inspeccion_obra',
            'liquidacion_visitas',
            'liquidacion_visitas__tarifa_aplicada',
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
        ],
        TipoLiquidacion.IMPACTO_VIAL: [
            'impacto_vial',
            'liquidacion_porcentaje_obra',
            'liquidacion_porcentaje_obra__detalles',
            'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
            'liquidacion_porcentaje_obra__detalles__especialidad',
            'liquidacion_porcentaje_obra__derecho_aplicado',
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
        ],
    }

    # Maps tipo_liquidacion codigo → reverse lookup field for numero filter
    _NUMERO_FILTER_FIELD_MAP = {
        TipoLiquidacion.EDIFICACION: 'edificaciones__numero',
        TipoLiquidacion.HABILITACION_URBANA: 'habilitacion_urbana__numero',
        TipoLiquidacion.MECANICA_SUELOS: 'mecanica_suelos__numero',
        TipoLiquidacion.TALUDES: 'taludes__numero',
        TipoLiquidacion.INSPECCION_OBRA: 'inspeccion_obra__numero',
        TipoLiquidacion.IMPACTO_VIAL: 'impacto_vial__numero',
    }

    def list_liquidaciones_paginated(
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
        Unified paginated queryset for LiquidacionGeneral, selected by tipo_liquidacion.

        Applies the same filter set and pagination as the 6 legacy methods
        (municipalidad_id, propietario, razon_social, creador_username, fecha_desde,
        fecha_hasta, numero, numero_revision).
        Uses conditional prefetch_related based on tipo_liquidacion.
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
            *self._PREFETCH_MAP[tipo_liquidacion]
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
            qs = qs.filter(**{self._NUMERO_FILTER_FIELD_MAP[tipo_liquidacion]: numero})
        if numero_revision is not None:
            qs = qs.filter(numero_revision=numero_revision)

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

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
        Thin delegation to list_liquidaciones_paginated.
        """
        return self.list_liquidaciones_paginated(
            tipo_liquidacion=tipo_liquidacion,
            page=page,
            page_size=page_size,
            municipalidad_id=municipalidad_id,
            propietario=propietario,
            razon_social=razon_social,
            creador_username=creador_username,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero=numero,
            numero_revision=numero_revision,
        )

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
        Thin delegation to list_liquidaciones_paginated.
        """
        return self.list_liquidaciones_paginated(
            tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
            page=page,
            page_size=page_size,
            municipalidad_id=municipalidad_id,
            propietario=propietario,
            razon_social=razon_social,
            creador_username=creador_username,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero=numero,
            numero_revision=numero_revision,
        )

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
        Thin delegation to list_liquidaciones_paginated.
        """
        return self.list_liquidaciones_paginated(
            tipo_liquidacion=TipoLiquidacion.MECANICA_SUELOS,
            page=page,
            page_size=page_size,
            municipalidad_id=municipalidad_id,
            propietario=propietario,
            razon_social=razon_social,
            creador_username=creador_username,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero=numero,
            numero_revision=numero_revision,
        )

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
        Thin delegation to list_liquidaciones_paginated.
        """
        return self.list_liquidaciones_paginated(
            tipo_liquidacion=TipoLiquidacion.TALUDES,
            page=page,
            page_size=page_size,
            municipalidad_id=municipalidad_id,
            propietario=propietario,
            razon_social=razon_social,
            creador_username=creador_username,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero=numero,
            numero_revision=numero_revision,
        )

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
        Thin delegation to list_liquidaciones_paginated.
        """
        return self.list_liquidaciones_paginated(
            tipo_liquidacion=TipoLiquidacion.INSPECCION_OBRA,
            page=page,
            page_size=page_size,
            municipalidad_id=municipalidad_id,
            propietario=propietario,
            razon_social=razon_social,
            creador_username=creador_username,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero=numero,
            numero_revision=numero_revision,
        )

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
        Thin delegation to list_liquidaciones_paginated.
        """
        return self.list_liquidaciones_paginated(
            tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL,
            page=page,
            page_size=page_size,
            municipalidad_id=municipalidad_id,
            propietario=propietario,
            razon_social=razon_social,
            creador_username=creador_username,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero=numero,
            numero_revision=numero_revision,
        )

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
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
        ).get(id=liquidacion_id)

    def get_liquidacion_previa_para_io(self, liquidacion_id: uuid.UUID) -> LiquidacionGeneral:
        """
        Returns a LiquidacionGeneral usable as previa for Inspección de Obra.

        A previa de IO debe ser de tipo EDIFICACION o HABILITACION_URBANA.
        Raises LiquidacionGeneral.DoesNotExist if not found.

        Incluye prefetch_related de liquidacion_delegados para evitar N+1
        cuando se construye el resultado general (build_general_result).
        """
        return LiquidacionGeneral.objects.select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        ).prefetch_related(
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
        ).get(
            id=liquidacion_id,
            tipo_liquidacion__codigo__in=[
                TipoLiquidacion.EDIFICACION,
                TipoLiquidacion.HABILITACION_URBANA,
            ],
        )

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
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
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
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
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
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
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
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
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
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
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
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
        ).get(id=liquidacion_id)

    def list_ultimas_revisiones_por_proyecto(
        self,
        tipo_liquidacion: str,
        page: int,
        page_size: int,
        razon_social=None,
        numero_documento=None,
        numero=None,
        fecha_desde=None,
        fecha_hasta=None,
    ) -> tuple:
        """
        Returns paginated LiquidacionGeneral queryset containing only the latest revision
        per project for the given tipo_liquidacion.

        Applies optional filters and returns only the liquidacion with the highest
        numero_revision for each proyecto.
        Uses select_related and prefetch_related with dynamic prefetch based on tipo_liquidacion.
        Returns (queryset, total_count).
        """
        from django.db.models import Max, OuterRef, Subquery

        # Base queryset with dynamic prefetch based on tipo_liquidacion (FIX: was hardcoded to Edificaciones only)
        qs = LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=tipo_liquidacion
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        )

        # Dynamic prefetch based on tipo_liquidacion (matching the pattern in list_liquidaciones_generales_paginated)
        if tipo_liquidacion == TipoLiquidacion.EDIFICACION:
            qs = qs.prefetch_related(
                'edificaciones',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo_liquidacion == TipoLiquidacion.HABILITACION_URBANA:
            qs = qs.prefetch_related(
                'habilitacion_urbana',
                'liquidacion_m2',
                'liquidacion_m2__tarifa_aplicada',
                'liquidacion_m2__derecho',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo_liquidacion == TipoLiquidacion.MECANICA_SUELOS:
            qs = qs.prefetch_related(
                'liquidacion_m2',
                'liquidacion_m2__tarifa_aplicada',
                'liquidacion_m2__derecho',
                'mecanica_suelos',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo_liquidacion == TipoLiquidacion.TALUDES:
            qs = qs.prefetch_related(
                'taludes',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo_liquidacion == TipoLiquidacion.INSPECCION_OBRA:
            qs = qs.prefetch_related(
                'inspeccion_obra',
                'liquidacion_visitas',
                'liquidacion_visitas__tarifa_aplicada',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo_liquidacion == TipoLiquidacion.IMPACTO_VIAL:
            qs = qs.prefetch_related(
                'impacto_vial',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        else:
            # Fallback: prefetch all relations
            qs = qs.prefetch_related(
                'edificaciones',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'habilitacion_urbana',
                'liquidacion_m2',
                'liquidacion_m2__tarifa_aplicada',
                'liquidacion_m2__derecho',
                'mecanica_suelos',
                'inspeccion_obra',
                'liquidacion_visitas',
                'liquidacion_visitas__tarifa_aplicada',
                'taludes',
                'impacto_vial',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )

        # Apply filters
        if razon_social:
            qs = qs.filter(proyecto__entidad_razon_social__icontains=razon_social)
        if numero_documento:
            qs = qs.filter(proyecto__entidad_numero_documento=numero_documento)
        if numero is not None:
            qs = qs.filter(**{self._NUMERO_FILTER_FIELD_MAP[tipo_liquidacion]: numero})
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
            'liquidacion_delegados',
            'liquidacion_delegados__delegado',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__especialidad_revision',
        )
        # El tipo_liquidacion siempre viene validado por el orquestador.
        qs = qs.filter(tipo_liquidacion__codigo=tipo_liquidacion)
        return qs.order_by('-numero_revision').first()

    def list_liquidaciones_generales_paginated(
        self,
        page: int,
        page_size: int,
        tipo=None,
        documento=None,
        razon_social=None,
        propietario=None,
        expediente=None,
        nombre_propietario=None,
        **kwargs
    ) -> tuple:
        """
        Returns paginated LiquidacionGeneral queryset for ALL tipos (no filter by tipo_liquidacion).
        Applies optional filters for tipo, documento, razon_social, propietario.
        Uses select_related and prefetch_related to avoid N+1 queries.

        Prefetch strategy: when `tipo` is provided, only prefetches the relation
        corresponding to that tipo. When `tipo` is None (general listing), prefetches
        all 6 relations (acceptable price for unfiltered general listing).
        Returns (queryset, total_count).
        """
        qs = LiquidacionGeneral.objects.all().select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        )

        # Conditional prefetch based on tipo filter to avoid N+1
        # When tipo is specified, only prefetch the specific relation
        if tipo == TipoLiquidacion.EDIFICACION:
            qs = qs.prefetch_related(
                'edificaciones',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo == TipoLiquidacion.HABILITACION_URBANA:
            qs = qs.prefetch_related(
                'habilitacion_urbana',
                'liquidacion_m2',
                'liquidacion_m2__tarifa_aplicada',
                'liquidacion_m2__derecho',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo == TipoLiquidacion.MECANICA_SUELOS:
            qs = qs.prefetch_related(
                'liquidacion_m2',
                'liquidacion_m2__tarifa_aplicada',
                'liquidacion_m2__derecho',
                'mecanica_suelos',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo == TipoLiquidacion.TALUDES:
            qs = qs.prefetch_related(
                'taludes',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo == TipoLiquidacion.INSPECCION_OBRA:
            qs = qs.prefetch_related(
                'inspeccion_obra',
                'liquidacion_visitas',
                'liquidacion_visitas__tarifa_aplicada',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo == TipoLiquidacion.IMPACTO_VIAL:
            qs = qs.prefetch_related(
                'impacto_vial',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        else:
            # No tipo filter: prefetch all relations (general listing)
            qs = qs.prefetch_related(
                'edificaciones',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'habilitacion_urbana',
                'liquidacion_m2',
                'liquidacion_m2__tarifa_aplicada',
                'liquidacion_m2__derecho',
                'mecanica_suelos',
                'inspeccion_obra',
                'liquidacion_visitas',
                'liquidacion_visitas__tarifa_aplicada',
                'taludes',
                'impacto_vial',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )

        qs = qs.order_by('-fecha_registro')

        # Apply filters (only for non-None params)
        if tipo:
            qs = qs.filter(tipo_liquidacion__codigo=tipo)
        if documento:
            qs = qs.filter(proyecto__entidad_numero_documento__icontains=documento)
        if razon_social:
            qs = qs.filter(proyecto__entidad_razon_social__icontains=razon_social)
        if propietario:
            qs = qs.filter(proyecto__nombre_propietario__icontains=propietario)
        # expediente: filters the LiquidacionGeneral.expediente field directly
        if expediente:
            qs = qs.filter(expediente__icontains=expediente)
        # nombre_propietario: explicit alias for 'propietario' — both filter proyecto__nombre_propietario__icontains
        if nombre_propietario:
            qs = qs.filter(proyecto__nombre_propietario__icontains=nombre_propietario)

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_ultimas_generales_paginated(
        self,
        page: int,
        page_size: int,
        tipo=None,
        documento=None,
        razon_social=None,
        propietario=None,
        expediente=None,
        nombre_propietario=None,
        **kwargs
    ) -> tuple:
        """
        Returns paginated LiquidacionGeneral queryset containing only the latest revision
        per (proyecto, tipo_liquidacion) pair.

        Uses subquery with Max('numero_revision') grouped by (proyecto_id, tipo_liquidacion__codigo)
        to identify the latest revision per project+tipo.
        Applies same optional filters as list_liquidaciones_generales_paginated.
        Uses conditional prefetch based on tipo filter (same strategy as list_liquidaciones_generales_paginated).
        Returns (queryset, total_count).
        """
        from django.db.models import Max, OuterRef, Subquery

        # Base queryset
        qs = LiquidacionGeneral.objects.all().select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
        )

        # Conditional prefetch based on tipo filter (same strategy as list_liquidaciones_generales_paginated)
        if tipo == TipoLiquidacion.EDIFICACION:
            qs = qs.prefetch_related(
                'edificaciones',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo == TipoLiquidacion.HABILITACION_URBANA:
            qs = qs.prefetch_related(
                'habilitacion_urbana',
                'liquidacion_m2',
                'liquidacion_m2__tarifa_aplicada',
                'liquidacion_m2__derecho',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo == TipoLiquidacion.MECANICA_SUELOS:
            qs = qs.prefetch_related(
                'liquidacion_m2',
                'liquidacion_m2__tarifa_aplicada',
                'liquidacion_m2__derecho',
                'mecanica_suelos',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo == TipoLiquidacion.TALUDES:
            qs = qs.prefetch_related(
                'taludes',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo == TipoLiquidacion.INSPECCION_OBRA:
            qs = qs.prefetch_related(
                'inspeccion_obra',
                'liquidacion_visitas',
                'liquidacion_visitas__tarifa_aplicada',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        elif tipo == TipoLiquidacion.IMPACTO_VIAL:
            qs = qs.prefetch_related(
                'impacto_vial',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )
        else:
            # No tipo filter: prefetch all relations (general listing)
            qs = qs.prefetch_related(
                'edificaciones',
                'liquidacion_porcentaje_obra',
                'liquidacion_porcentaje_obra__detalles',
                'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
                'liquidacion_porcentaje_obra__detalles__especialidad',
                'liquidacion_porcentaje_obra__derecho_aplicado',
                'habilitacion_urbana',
                'liquidacion_m2',
                'liquidacion_m2__tarifa_aplicada',
                'liquidacion_m2__derecho',
                'mecanica_suelos',
                'inspeccion_obra',
                'liquidacion_visitas',
                'liquidacion_visitas__tarifa_aplicada',
                'taludes',
                'impacto_vial',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
            )

        qs = qs.order_by('-fecha_registro')

        # Apply filters (only for non-None params)
        if tipo:
            qs = qs.filter(tipo_liquidacion__codigo=tipo)
        if documento:
            qs = qs.filter(proyecto__entidad_numero_documento__icontains=documento)
        if razon_social:
            qs = qs.filter(proyecto__entidad_razon_social__icontains=razon_social)
        if propietario:
            qs = qs.filter(proyecto__nombre_propietario__icontains=propietario)
        # expediente: filters the LiquidacionGeneral.expediente field directly
        if expediente:
            qs = qs.filter(expediente__icontains=expediente)
        # nombre_propietario: explicit alias for 'propietario' — both filter proyecto__nombre_propietario__icontains
        if nombre_propietario:
            qs = qs.filter(proyecto__nombre_propietario__icontains=nombre_propietario)

        # Subquery to get max numero_revision per (proyecto_id, tipo_liquidacion__codigo)
        max_rev_subquery = LiquidacionGeneral.objects.filter(
            proyecto_id=OuterRef('proyecto_id'),
            tipo_liquidacion__codigo=OuterRef('tipo_liquidacion__codigo'),
        ).order_by().values('proyecto_id', 'tipo_liquidacion__codigo').annotate(
            max_rev=Max('numero_revision')
        ).values('max_rev')[:1]

        qs = qs.filter(numero_revision=Subquery(max_rev_subquery))

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    # ── Result Builders (ORM → Domain Result) ──────────────────────────────────

    def build_general_result(
        self,
        liquidacion_general,
        usuario_id: int,
        contacto_result: Optional[ContactoResult] = None,
        revisiones_previas: Optional[list] = None,
        delegados: Optional[list] = None,
        fecha_registro: Optional[str] = None,
    ) -> LiquidacionGeneralResult:
        """
        Builds a complete LiquidacionGeneralResult from an ORM LiquidacionGeneral instance.

        PURE MAPPING — no validation, no business logic.
        All optional fields default to safe values (None/[]) when not provided.

        Args:
            liquidacion_general: ORM LiquidacionGeneral instance (already saved/refreshed).
            usuario_id: ID of the creating user.
            contacto_result: Optional ContactoResult; None if not provided.
            revisiones_previas: Optional list of LiquidacionPreviaResult; defaults to [].
            delegados: Optional list of LiquidacionDelegadoEnGeneralResult; defaults to [].
            fecha_registro: Optional ISO string; if None, uses liquidacion_general.created_at.isoformat().
        """
        if fecha_registro is None:
            fecha_registro = liquidacion_general.created_at.isoformat()

        entidad_result = self._build_entidad_result(liquidacion_general.proyecto)
        proyecto_result = self._build_proyecto_result(liquidacion_general.proyecto, entidad_result)

        return LiquidacionGeneralResult(
            id=str(liquidacion_general.id),
            municipalidad=MunicipalidadResult(
                id=str(liquidacion_general.municipalidad.id),
                codigo=liquidacion_general.municipalidad.codigo,
                nombre=liquidacion_general.municipalidad.nombre,
            ),
            usuario_creador=UsuarioCreadorResult(
                id=str(usuario_id),
                nombres=getattr(liquidacion_general.usuario_creador, "nombres", None),
                apellidos=getattr(liquidacion_general.usuario_creador, "apellidos", None),
                email=getattr(liquidacion_general.usuario_creador, "email", None),
                dni=getattr(liquidacion_general.usuario_creador, "dni", None),
                username=getattr(liquidacion_general.usuario_creador, "username", None),
            ),
            fecha_registro=fecha_registro,
            expediente=liquidacion_general.expediente,
            observacion=liquidacion_general.observacion,
            numero_revision=liquidacion_general.numero_revision,
            sub_total=float(liquidacion_general.sub_total),
            total=float(liquidacion_general.total),
            retencion=liquidacion_general.retencion,
            igv=(
                IgvResult(
                    id=str(liquidacion_general.igv_id.id),
                    valor=float(liquidacion_general.igv_id.valor),
                    periodo_inicio=(
                        liquidacion_general.igv_id.periodo_inicio.isoformat()
                        if liquidacion_general.igv_id.periodo_inicio
                        else None
                    ),
                )
                if liquidacion_general.igv_id
                else None
            ),
            uit=(
                UitResult(
                    id=str(liquidacion_general.uit_id.id),
                    valor=float(liquidacion_general.uit_id.valor),
                    periodo_inicio=(
                        liquidacion_general.uit_id.periodo_inicio.isoformat()
                        if liquidacion_general.uit_id.periodo_inicio
                        else None
                    ),
                )
                if liquidacion_general.uit_id
                else None
            ),
            proyecto=proyecto_result,
            contacto=contacto_result,
            revisiones_previas=revisiones_previas if revisiones_previas is not None else [],
            delegados=delegados if delegados is not None else [],
            tipo_liquidacion=(
                TipoLiquidacionResult(
                    codigo=liquidacion_general.tipo_liquidacion.codigo,
                    nombre=liquidacion_general.tipo_liquidacion.nombre,
                )
                if liquidacion_general.tipo_liquidacion
                else None
            ),
        )

    def _build_entidad_result(self, proyecto) -> Optional[EntidadResult]:
        """Builds EntidadResult from denormalized fields on the proyecto ORM."""
        if (
            hasattr(proyecto, "entidad_razon_social")
            and proyecto.entidad_razon_social
        ):
            return EntidadResult(
                razon_social=proyecto.entidad_razon_social,
                tipo_documento=getattr(proyecto, "entidad_tipo_documento", None) or "",
                numero_documento=getattr(proyecto, "entidad_numero_documento", None) or "",
            )
        return None

    def _build_proyecto_result(
        self, proyecto, entidad_result: Optional[EntidadResult]
    ) -> ProyectoResult:
        """Builds ProyectoResult including nested distrito (with provincia/departamento)."""
        distrito_result = self._build_distrito_result(proyecto)
        return ProyectoResult(
            id=str(proyecto.id),
            denominacion=proyecto.denominacion,
            nombre_propietario=proyecto.nombre_propietario,
            direccion=proyecto.direccion,
            distrito=distrito_result,
            entidad=entidad_result,
        )

    def _build_distrito_result(self, proyecto) -> Optional[DistritoResult]:
        """Builds DistritoResult with nested provincia and departamento from ORM."""
        if not getattr(proyecto, "distrito_id", None):
            return None
        distrito = proyecto.distrito
        if not distrito:
            return None
        return DistritoResult(
            id=str(distrito.id),
            nombre=distrito.nombre,
            ubigeo=getattr(distrito, "ubigeo", None),
            provincia=(
                ProvinciaResult(
                    id=str(distrito.provincia.id),
                    nombre=distrito.provincia.nombre,
                    departamento=(
                        DepartamentoResult(
                            id=str(distrito.provincia.departamento.id),
                            nombre=distrito.provincia.departamento.nombre,
                        )
                        if distrito.provincia.departamento
                        else None
                    ),
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

    def build_delegados_result(self, liquidacion_general) -> list[LiquidacionDelegadoEnGeneralResult]:
        """
        Builds a list of LiquidacionDelegadoEnGeneralResult from liquidacion_delegados prefetch.
        Returns [] if no delegados are present.
        """
        return [
            LiquidacionDelegadoEnGeneralResult(
                id=str(ld.id),
                liquidacion_id=str(liquidacion_general.id),
                delegado_id=str(ld.delegado_id),
                especialidad_revision_id=str(ld.especialidad_revision_id),
                especialidad_revision_nombre=ld.especialidad_revision.nombre,
                delegado_cip=ld.delegado.perfil_ingeniero.cip,
                delegado_dni=ld.delegado.perfil_ingeniero.dni,
                delegado_nombre_completo=ld.delegado.perfil_ingeniero.nombre_completo,
                periodo=ld.periodo,
                dictamen_revision=ld.dictamen_revision,
                fecha_presentacion=(
                    ld.fecha_presentacion.isoformat() if ld.fecha_presentacion else None
                ),
                fecha_revision=(
                    ld.fecha_revision.isoformat() if ld.fecha_revision else None
                ),
            )
            for ld in getattr(liquidacion_general, "liquidacion_delegados", []).all()
        ]
