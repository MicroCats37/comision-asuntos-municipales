"""
LiquidacionGeneralCoreService — operaciones ORM síncronas para entidades de liquidación general.

ORM PURO — sin lógica de negocio, sin condicionales.
Maneja: Entidad, Proyecto, LiquidacionGeneral.
"""
from decimal import Decimal
from typing import Optional, Dict, List
from datetime import date, datetime
import uuid

from django.db.models import F, Max, OuterRef, Prefetch, Q, Subquery

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral, LiquidacionCodigo
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
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_comprobante_result import (
    LiquidacionComprobanteResult,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
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

    def get_codigo_cta_map(self, tipo_liquidacion_codigos: List[str]) -> Dict[str, str]:
        """
        Batch fetch codigo_cta for multiple tipo_liquidacion codigos.
        Returns a dict mapping tipo_liquidacion.codigo -> codigo_cta.
        If no codes found for a tipo, it won't be in the dict (caller should treat as None).
        """
        if not tipo_liquidacion_codigos:
            return {}
        codigos = LiquidacionCodigo.objects.filter(
            tipo_liquidacion__codigo__in=tipo_liquidacion_codigos
        ).select_related('tipo_liquidacion')
        return {c.tipo_liquidacion.codigo: c.codigo_cta for c in codigos}

    def get_codigo_cta(self, tipo_liquidacion) -> Optional[str]:
        """
        Resolve codigo_cta for a single TipoLiquidacion (or a LiquidacionGeneral).
        Returns None when the tipo or code is missing.
        """
        tipo_codigo = getattr(tipo_liquidacion, "codigo", None)
        if not tipo_codigo:
            return None
        return self.get_codigo_cta_map([tipo_codigo]).get(tipo_codigo)

    def create_entidad(
        self,
        tipo_documento: Optional[str] = None,
        numero_documento: Optional[str] = None,
    ) -> Optional[Entidad]:
        """
        Creates or returns existing Entidad by numero_documento.
        Note: razon_social and direccion belong to Proyecto, not Entidad.

        If tipo_documento or numero_documento is empty/None, no Entidad row is
        created (returns None) — the caller stores snapshot fields on Proyecto.
        """
        if not tipo_documento or not numero_documento:
            return None
        existente = Entidad.objects.filter(numero_documento=numero_documento).first()
        if existente:
            return existente
        return Entidad.objects.create(
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
        )

    def clone_proyecto_for_liquidacion(self, liquidacion_previa) -> Proyecto:
        """
        Creates a new Proyecto that is a copy of liquidacion_previa.proyecto,
        sharing the SAME Entidad instance (entidad FK is NOT cloned).

        Used when creating a new revision to ensure each LiquidacionGeneral
        has its own isolated Proyecto row, preventing mutations to one revision's
        project from affecting other revisions.

        Args:
            liquidacion_previa: LiquidacionGeneral instance whose proyecto will be cloned.

        Returns:
            A new Proyecto instance with identical field values but its own row,
            sharing the same Entidad as the original.
        """
        original = liquidacion_previa.proyecto
        return Proyecto.objects.create(
            entidad=original.entidad,  # Shared — NOT cloned by business design
            entidad_razon_social=original.entidad_razon_social,
            entidad_tipo_documento=original.entidad_tipo_documento,
            entidad_numero_documento=original.entidad_numero_documento,
            nombre_propietario=original.nombre_propietario,
            direccion=original.direccion,
            urbanizacion=original.urbanizacion,
            distrito_id=original.distrito_id,
            descripcion=original.descripcion,
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
        expediente: Optional[str],
        observacion: Optional[str],
        proyecto: Proyecto,
        tipo_liquidacion: str,
        numero_revision: int = 1,
        contacto=None,
        retencion: bool = False,
        denominacion_de_proyecto: Optional[str] = None,
        descripcion_legacy: Optional[str] = None,
        sub_total: Optional[Decimal] = None,
        total: Optional[Decimal] = None,
        igv_id: Optional[IGV] = None,
        uit_id: Optional[UIT] = None,
        usuario_creador_id: Optional[int] = None,
        fecha_registro: Optional[date] = None,
        modo_calculo: Optional[str] = None,
        legacy: bool = False,
    ) -> LiquidacionGeneral:
        """
        Creates a LiquidacionGeneral base record.
        Resolves tipo_liquidacion string/enum to TipoLiquidacion FK instance.
        """
        if isinstance(tipo_liquidacion, TipoLiquidacionModel):
            tipo_liq_obj = tipo_liquidacion
        else:
            tipo_liq_obj = TipoLiquidacionModel.objects.get(codigo=tipo_liquidacion)
        # Build kwargs conditionally — fecha_registro uses model default when not provided
        kwargs = dict(
            proyecto=proyecto,
            municipalidad_id=municipalidad_id,
            expediente=expediente,
            observacion=observacion,
            retencion=retencion,
            estado=EstadoLiquidacion.PENDIENTE,
            tipo_liquidacion=tipo_liq_obj,
            numero_revision=numero_revision,
            sub_total=sub_total if sub_total is not None else Decimal("0"),
            total=total if total is not None else Decimal("0"),
            contacto=contacto,
            denominacion_de_proyecto=denominacion_de_proyecto,
            descripcion_legacy=descripcion_legacy,
            legacy=legacy,
            igv_id=igv_id,
            uit_id=uit_id,
            usuario_creador_id=usuario_creador_id,
        )
        if fecha_registro is not None:
            kwargs["fecha_registro"] = fecha_registro
        if modo_calculo is not None:
            kwargs["modo_calculo"] = modo_calculo
        return LiquidacionGeneral.objects.create(**kwargs)

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
            'liquidacion_visitas__registros_pago',
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

    # Maps tipo_liquidacion codigo → (specific model class, related_name on LiquidacionGeneral)
    # Used for the direct-lookup optimization: find liquidacion_id from specific table,
    # then filter LiquidacionGeneral by those ids (avoids expensive OR across 6 reverse joins).
    _NUMERO_SPECIFIC_MODEL_MAP = {
        TipoLiquidacion.EDIFICACION: (
            'modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones',
            'LiquidacionEdificacion',
            'edificaciones',
        ),
        TipoLiquidacion.HABILITACION_URBANA: (
            'modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana',
            'LiquidacionHabilitacionUrbana',
            'habilitacion_urbana',
        ),
        TipoLiquidacion.MECANICA_SUELOS: (
            'modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos',
            'LiquidacionMecanicaSuelos',
            'mecanica_suelos',
        ),
        TipoLiquidacion.TALUDES: (
            'modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_taludes',
            'LiquidacionTaludes',
            'taludes',
        ),
        TipoLiquidacion.INSPECCION_OBRA: (
            'modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra',
            'LiquidacionInspeccionObra',
            'inspeccion_obra',
        ),
        TipoLiquidacion.IMPACTO_VIAL: (
            'modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_impacto_vial',
            'LiquidacionImpactoVial',
            'impacto_vial',
        ),
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
        direccion=None,
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
            tipo_liquidacion__codigo=tipo_liquidacion,
            eliminado=False,
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
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
        if direccion:
            qs = qs.filter(proyecto__direccion__icontains=direccion)

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
        direccion=None,
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
            direccion=direccion,
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
        direccion=None,
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
            direccion=direccion,
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
        direccion=None,
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
            direccion=direccion,
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
        direccion=None,
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
            direccion=direccion,
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
        direccion=None,
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
            direccion=direccion,
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
        direccion=None,
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
            direccion=direccion,
        )

    # ── Detail (GET /{id}) methods ─────────────────────────────────────────────────

    def get_liquidacion_edificacion_by_id(self, liquidacion_id: int) -> LiquidacionGeneral:
        """
        Returns a single LiquidacionGeneral for Edificaciones by ID.

        Uses the same prefetch chain as list_liquidaciones_by_type_paginated for EDIFICACION.
        Raises LiquidacionGeneral.DoesNotExist if not found.
        """
        return LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.EDIFICACION,
            eliminado=False,
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
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
            eliminado=False,
        )

    def get_liquidacion_edificaciones_by_id(self, liquidacion_id: uuid.UUID) -> LiquidacionGeneral:
        """
        Returns a single LiquidacionGeneral for Edificaciones by UUID.

        Uses the EXACT SAME select_related and prefetch_related chain as
        list_liquidaciones_by_type_paginated for EDIFICACION.
        Raises LiquidacionGeneral.DoesNotExist if not found.
        """
        return LiquidacionGeneral.objects.filter(
            tipo_liquidacion__codigo=TipoLiquidacion.EDIFICACION,
            eliminado=False,
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
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
            tipo_liquidacion__codigo=TipoLiquidacion.HABILITACION_URBANA,
            eliminado=False,
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
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
            tipo_liquidacion__codigo=TipoLiquidacion.MECANICA_SUELOS,
            eliminado=False,
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
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
            tipo_liquidacion__codigo=TipoLiquidacion.TALUDES,
            eliminado=False,
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
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
            tipo_liquidacion__codigo=TipoLiquidacion.INSPECCION_OBRA,
            eliminado=False,
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
        ).prefetch_related(
            'inspeccion_obra',
            'liquidacion_visitas',
            'liquidacion_visitas__tarifa_aplicada',
            'liquidacion_visitas__registros_pago',
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
            tipo_liquidacion__codigo=TipoLiquidacion.IMPACTO_VIAL,
            eliminado=False,
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
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
            tipo_liquidacion__codigo=tipo_liquidacion,
            eliminado=False,
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
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
                'liquidacion_visitas__registros_pago',
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
        if fecha_desde:
            qs = qs.filter(fecha_registro__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_registro__date__lte=fecha_hasta)

        # Subquery to get max numero_revision per proyecto
        max_rev_subquery = LiquidacionGeneral.objects.filter(
            proyecto_id=OuterRef('proyecto_id'),
            tipo_liquidacion__codigo=tipo_liquidacion,
            eliminado=False,
        ).order_by().values('proyecto_id').annotate(
            max_rev=Max('numero_revision')
        ).values('max_rev')[:1]

        qs = qs.filter(numero_revision=Subquery(max_rev_subquery))

        # numero filter: resolve liquidacion_id directly from specific model to avoid
        # expensive reverse JOIN (edificaciones__numero) on the full LiquidacionGeneral table.
        # Applied AFTER latest-revisions subquery so the id__in filter runs on the
        # small latest-revisions dataset — same strategy as list_liquidaciones_ultimas_generales_paginated.
        if numero is not None:
            if tipo_liquidacion in self._NUMERO_SPECIFIC_MODEL_MAP:
                module_path, _cls_name, _related_name = self._NUMERO_SPECIFIC_MODEL_MAP[tipo_liquidacion]
                from importlib import import_module
                module = import_module(module_path)
                specific_model_cls = getattr(module, _cls_name)
                liquidacion_ids = list(
                    specific_model_cls.objects.filter(numero=numero)
                    .values_list('liquidacion_id', flat=True)
                )
                if liquidacion_ids:
                    qs = qs.filter(id__in=liquidacion_ids)
                else:
                    qs = qs.filter(id__in=[None])
            else:
                qs = qs.filter(**{self._NUMERO_FILTER_FIELD_MAP[tipo_liquidacion]: numero})

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
            eliminado=False,
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
        direccion=None,
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
        qs = LiquidacionGeneral.objects.filter(eliminado=False).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
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
                Prefetch("comprobantes", queryset=LiquidacionComprobante.objects.order_by("-fecha_emision", "-id"), to_attr="comprobantes_prefetched"),
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
                Prefetch("comprobantes", queryset=LiquidacionComprobante.objects.order_by("-fecha_emision", "-id"), to_attr="comprobantes_prefetched"),
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
                Prefetch("comprobantes", queryset=LiquidacionComprobante.objects.order_by("-fecha_emision", "-id"), to_attr="comprobantes_prefetched"),
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
                Prefetch("comprobantes", queryset=LiquidacionComprobante.objects.order_by("-fecha_emision", "-id"), to_attr="comprobantes_prefetched"),
            )
        elif tipo == TipoLiquidacion.INSPECCION_OBRA:
            qs = qs.prefetch_related(
                'inspeccion_obra',
                'liquidacion_visitas',
                'liquidacion_visitas__tarifa_aplicada',
                'liquidacion_visitas__registros_pago',
                'liquidacion_delegados',
                'liquidacion_delegados__delegado',
                'liquidacion_delegados__delegado__perfil_ingeniero',
                'liquidacion_delegados__especialidad_revision',
                Prefetch("comprobantes", queryset=LiquidacionComprobante.objects.order_by("-fecha_emision", "-id"), to_attr="comprobantes_prefetched"),
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
                Prefetch("comprobantes", queryset=LiquidacionComprobante.objects.order_by("-fecha_emision", "-id"), to_attr="comprobantes_prefetched"),
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
                Prefetch("comprobantes", queryset=LiquidacionComprobante.objects.order_by("-fecha_emision", "-id"), to_attr="comprobantes_prefetched"),
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
        if direccion:
            qs = qs.filter(proyecto__direccion__icontains=direccion)

        total = qs.count()
        offset = (page - 1) * page_size
        return qs[offset:offset + page_size], total

    def list_liquidaciones_ultimas_generales_paginated(
        self,
        page: int,
        page_size: int,
        tipo=None,
        tipo_liquidacion=None,
        documento=None,
        razon_social=None,
        propietario=None,
        expediente=None,
        nombre_propietario=None,
        numero=None,
        direccion=None,
        **kwargs
    ) -> tuple:
        """
        Returns paginated LiquidacionGeneral queryset containing latest revisions.

        Related liquidaciones are reduced by (grupo_id, relacion_key). Non-related
        liquidaciones keep the previous fallback by (proyecto_id, tipo_liquidacion).
        """
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_general import (
            LiquidacionRelacionMiembro,
        )

        def normalize_tipos(value):
            if value is None:
                return []
            if isinstance(value, str):
                return [value] if value else []
            return [item for item in value if item]

        tipo_codigos = normalize_tipos(tipo_liquidacion) or normalize_tipos(tipo)

        # Base queryset
        qs = LiquidacionGeneral.objects.filter(eliminado=False).select_related(
            'proyecto',
            'proyecto__entidad',
            'proyecto__distrito',
            'proyecto__distrito__provincia',
            'proyecto__distrito__provincia__departamento',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
        )

        # Conditional prefetch based on requested types. Multiple/no type uses all
        # relations because the presenter dispatcher may need any specific payload.
        if len(tipo_codigos) == 1 and tipo_codigos[0] in self._PREFETCH_MAP:
            qs = qs.prefetch_related(
                *self._PREFETCH_MAP[tipo_codigos[0]],
                Prefetch("comprobantes", queryset=LiquidacionComprobante.objects.order_by("-fecha_emision", "-id"), to_attr="comprobantes_prefetched"),
            )
        else:
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
                Prefetch("comprobantes", queryset=LiquidacionComprobante.objects.order_by("-fecha_emision", "-id"), to_attr="comprobantes_prefetched"),
            )

        qs = qs.order_by('-fecha_registro')

        # Apply filters (only for non-None params)
        if tipo_codigos:
            qs = qs.filter(tipo_liquidacion__codigo__in=tipo_codigos)
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
        if direccion:
            qs = qs.filter(proyecto__direccion__icontains=direccion)

        # Pure ORM subquery deduplication — no Python list materialization.
        # For related liquidaciones: latest per (grupo, relacion_key).
        max_related = LiquidacionRelacionMiembro.objects.filter(
            grupo=OuterRef("relacion_miembros__grupo"),
            relacion_key=OuterRef("relacion_miembros__relacion_key"),
        ).order_by().values("grupo").annotate(max_rev=Max("numero_revision")).values("max_rev")

        # For non-related liquidaciones: latest per (proyecto, tipo_liquidacion).
        max_unrelated = LiquidacionGeneral.objects.filter(
            proyecto=OuterRef("proyecto"),
            tipo_liquidacion=OuterRef("tipo_liquidacion"),
            eliminado=False,
        ).order_by().values("proyecto").annotate(max_rev=Max("numero_revision")).values("max_rev")

        qs = qs.annotate(
            max_rev_related=Subquery(max_related),
            max_rev_unrelated=Subquery(max_unrelated),
        ).filter(
            Q(relacion_miembros__isnull=False, numero_revision=F("max_rev_related"))
            | Q(relacion_miembros__isnull=True, numero_revision=F("max_rev_unrelated"))
        )

        # numero filter: clean ORM Q-object across all reverse relations.
        if numero is not None:
            qs = qs.filter(
                Q(edificaciones__numero=numero)
                | Q(habilitacion_urbana__numero=numero)
                | Q(mecanica_suelos__numero=numero)
                | Q(taludes__numero=numero)
                | Q(impacto_vial__numero=numero)
                | Q(inspeccion_obra__numero=numero)
            )

        total = qs.count()
        offset = (page - 1) * page_size
        qs_paginated = qs[offset:offset + page_size]
        return qs_paginated, total

    # ── General Fetch & Update ──────────────────────────────────────────────────

    def get_liquidacion_general_by_id(self, liquidacion_id: uuid.UUID) -> LiquidacionGeneral:
        """
        Returns a single LiquidacionGeneral by UUID (any tipo).

        Uses the same select_related and full prefetch chain as list_liquidaciones_generales_paginated
        for the unfiltered case to ensure full hydration.
        Raises LiquidacionGeneral.DoesNotExist if not found.
        """
        return LiquidacionGeneral.objects.filter(
            id=liquidacion_id,
            eliminado=False,
        ).select_related(
            'proyecto',
            'proyecto__entidad',
            'municipalidad',
            'usuario_creador',
            'tipo_liquidacion',
            'contacto',
        ).prefetch_related(
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
            'liquidacion_delegados__delegado_operacion',
            'liquidacion_delegados__especialidad_revision',
            Prefetch("comprobantes", queryset=LiquidacionComprobante.objects.order_by("-fecha_emision", "-id"), to_attr="comprobantes_prefetched"),
        ).get(id=liquidacion_id)

    def actualizar_liquidacion_general(
        self,
        liquidacion: LiquidacionGeneral,
        expediente: Optional[str] = None,
        observacion: Optional[str] = None,
        retencion: Optional[bool] = None,
        denominacion_de_proyecto: Optional[str] = None,
        contacto_data: Optional[dict] = None,
    ) -> LiquidacionGeneral:
        """
        Updates editable general fields on a LiquidacionGeneral ORM object.

        PURE ORM — no business logic. Caller is responsible for guard checks
        (e.g. estado == PENDIENTE) before calling this method.

        Args:
            liquidacion: LiquidacionGeneral ORM instance (must be saved by caller).
            expediente: New expediente value (None = no change).
            observacion: New observacion value (None = no change).
            retencion: New retencion value (None = no change).
            denominacion_de_proyecto: New denominacion value (None = no change).
            contacto_data: Contacto upsert data dict; if provided, upserts Contacto
                          and assigns it to liquidacion.contacto.

        Returns:
            The same liquidacion instance (refreshed in-place by .save()).
        """
        if expediente is not None:
            liquidacion.expediente = expediente
        if observacion is not None:
            liquidacion.observacion = observacion
        if retencion is not None:
            liquidacion.retencion = retencion
        if denominacion_de_proyecto is not None:
            liquidacion.denominacion_de_proyecto = denominacion_de_proyecto
        if contacto_data is not None:
            contacto = self.upsert_contacto(contacto_data)
            liquidacion.contacto = contacto
        liquidacion.save()
        return liquidacion

    def marcar_estado_pagada(self, liquidacion: "LiquidacionGeneral") -> "LiquidacionGeneral":
        """
        Marks a LiquidacionGeneral as PAGADA.

        PURE ORM — no business logic. Caller is responsible for guard checks
        (e.g. only call when transitioning from PENDIENTE).

        Args:
            liquidacion: LiquidacionGeneral ORM instance (must be saved by caller).

        Returns:
            The same liquidacion instance with estado updated to PAGADA.
        """
        liquidacion.estado = EstadoLiquidacion.PAGADA
        liquidacion.save(update_fields=["estado"])
        return liquidacion

    def eliminar_liquidacion(
        self,
        liquidacion: "LiquidacionGeneral",
        user_id: Optional[int],
        motivo: Optional[str],
    ) -> "LiquidacionGeneral":
        """
        Marks a LiquidacionGeneral as eliminated/anulled.

        PURE ORM — no business logic. Caller is responsible for guard checks.

        Sets:
        - eliminado=True
        - fecha_eliminacion=timezone.now()
        - eliminado_por=user (SET_NULL if user not provided)
        - motivo_eliminacion=motivo
        - specific model numero=NULL (based on tipo_liquidacion)

        Args:
            liquidacion: LiquidacionGeneral ORM instance.
            user_id: ID of the user performing the elimination (optional).
            motivo: Reason for elimination (optional).

        Returns:
            The same liquidacion instance with elimination fields updated.
        """
        from django.utils import timezone as tz

        liquidacion.eliminado = True
        liquidacion.fecha_eliminacion = tz.now()
        liquidacion.motivo_eliminacion = motivo

        if user_id is not None:
            liquidacion.eliminado_por_id = user_id

        # Set specific model numero=NULL based on tipo_liquidacion
        tipo_codigo = liquidacion.tipo_liquidacion.codigo
        if tipo_codigo == TipoLiquidacion.EDIFICACION:
            specific = getattr(liquidacion, 'edificaciones', None)
            if specific is not None:
                specific.numero = None
                specific.save(update_fields=["numero"])
        elif tipo_codigo == TipoLiquidacion.HABILITACION_URBANA:
            specific = getattr(liquidacion, 'habilitacion_urbana', None)
            if specific is not None:
                specific.numero = None
                specific.save(update_fields=["numero"])
        elif tipo_codigo == TipoLiquidacion.MECANICA_SUELOS:
            specific = getattr(liquidacion, 'mecanica_suelos', None)
            if specific is not None:
                specific.numero = None
                specific.save(update_fields=["numero"])
        elif tipo_codigo == TipoLiquidacion.TALUDES:
            specific = getattr(liquidacion, 'taludes', None)
            if specific is not None:
                specific.numero = None
                specific.save(update_fields=["numero"])
        elif tipo_codigo == TipoLiquidacion.INSPECCION_OBRA:
            specific = getattr(liquidacion, 'inspeccion_obra', None)
            if specific is not None:
                specific.numero = None
                specific.save(update_fields=["numero"])
        elif tipo_codigo == TipoLiquidacion.IMPACTO_VIAL:
            specific = getattr(liquidacion, 'impacto_vial', None)
            if specific is not None:
                specific.numero = None
                specific.save(update_fields=["numero"])

        liquidacion.save(update_fields=[
            "eliminado",
            "fecha_eliminacion",
            "eliminado_por",
            "motivo_eliminacion",
        ])
        return liquidacion

    # ── Proyecto & Entidad Update (Pure ORM) ─────────────────────────────────────

    def find_or_create_entidad(
        self,
        tipo_documento: str,
        numero_documento: str,
    ) -> "Entidad":
        """
        Finds an existing Entidad by tipo+numero_documento, or creates a new one.
        NEVEř mutates an existing Entidad row.

        PURE ORM — no business logic.

        Args:
            tipo_documento: Document type (RUC/DNI).
            numero_documento: Document number (unique on Entidad).

        Returns:
            Existing or newly created Entidad instance.
        """
        existente = Entidad.objects.filter(
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
        ).first()
        if existente:
            return existente
        return Entidad.objects.create(
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
        )

    def actualizar_proyecto_fields(
        self,
        liquidacion: "LiquidacionGeneral",
        nombre_propietario: Optional[str] = None,
        direccion: Optional[str] = None,
        urbanizacion: Optional[str] = None,
        distrito_id: Optional[uuid.UUID] = None,
    ) -> "LiquidacionGeneral":
        """
        Updates editable scalar fields on the Proyecto attached to a LiquidacionGeneral.

        PURE ORM — no business logic. Caller is responsible for guard checks
        (e.g. estado == PENDIENTE, revision rule).

        Args:
            liquidacion: LiquidacionGeneral ORM instance.
            nombre_propietario: New owner name (None = no change).
            direccion: New address (None = no change).
            urbanizacion: New urbanizacion (None = no change).
            distrito_id: New distrito UUID (None = no change).

        Returns:
            The same liquidacion instance (proyecto updated in-place).
        """
        proyecto = liquidacion.proyecto
        if nombre_propietario is not None:
            proyecto.nombre_propietario = nombre_propietario
        if direccion is not None:
            proyecto.direccion = direccion
        if urbanizacion is not None:
            proyecto.urbanizacion = urbanizacion
        if distrito_id is not None:
            proyecto.distrito_id = distrito_id
        proyecto.save()
        return liquidacion

    def actualizar_entidad_snapshot(
        self,
        proyecto: "Proyecto",
        entidad_tipo_documento: Optional[str] = None,
        entidad_numero_documento: Optional[str] = None,
        entidad_razon_social: Optional[str] = None,
    ) -> "Proyecto":
        """
        Updates denormalized entity snapshot fields on a Proyecto.
        Does NOT mutate the Entidad row itself.

        PURE ORM — no business logic.

        Args:
            proyecto: Proyecto ORM instance.
            entidad_tipo_documento: New document type (None = no change).
            entidad_numero_documento: New document number (None = no change).
            entidad_razon_social: New razon social snapshot (None = no change).

        Returns:
            The same proyecto instance (updated in-place).
        """
        if entidad_tipo_documento is not None:
            proyecto.entidad_tipo_documento = entidad_tipo_documento
        if entidad_numero_documento is not None:
            proyecto.entidad_numero_documento = entidad_numero_documento
        if entidad_razon_social is not None:
            proyecto.entidad_razon_social = entidad_razon_social
        proyecto.save()
        return proyecto

    def reassign_proyecto_entidad(
        self,
        proyecto: "Proyecto",
        entidad: "Entidad",
    ) -> "Proyecto":
        """
        Reassigns the entidad FK on a Proyecto and keeps snapshot fields
        congruent with the new Entidad.

        PURE ORM — no business logic. Caller is responsible for guard checks.

        Args:
            proyecto: Proyecto ORM instance.
            entidad: Entidad instance to assign.

        Returns:
            The same proyecto instance (updated in-place).
        """
        proyecto.entidad = entidad
        proyecto.entidad_tipo_documento = entidad.tipo_documento
        proyecto.entidad_numero_documento = entidad.numero_documento
        proyecto.save()
        return proyecto

    def actualizar_municipalidad(
        self,
        liquidacion: "LiquidacionGeneral",
        municipalidad_id: uuid.UUID,
    ) -> "LiquidacionGeneral":
        """
        Updates the municipalidad FK on a LiquidacionGeneral.

        PURE ORM — no business logic. Caller is responsible for guard checks.

        Args:
            liquidacion: LiquidacionGeneral ORM instance.
            municipalidad_id: UUID of the new municipalidad.

        Returns:
            The same liquidacion instance (updated in-place).
        """
        liquidacion.municipalidad_id = municipalidad_id
        liquidacion.save(update_fields=["municipalidad_id"])
        return liquidacion

    # ── Result Builders (ORM → Domain Result) ──────────────────────────────────

    def build_general_result(
        self,
        liquidacion_general,
        usuario_id: int,
        contacto_result: Optional[ContactoResult] = None,
        delegados: Optional[list] = None,
        codigo_cta: Optional[str] = None,
    ) -> LiquidacionGeneralResult:
        """
        Builds a complete LiquidacionGeneralResult from an ORM LiquidacionGeneral instance.

        PURE MAPPING — no validation, no business logic.
        All optional fields default to safe values (None/[]) when not provided.

        Args:
            liquidacion_general: ORM LiquidacionGeneral instance (already saved/refreshed).
            usuario_id: ID of the creating user.
            contacto_result: Optional ContactoResult; None if not provided.
            delegados: Optional list of LiquidacionDelegadoEnGeneralResult; defaults to [].
            codigo_cta: Pre-resolved codigo_cta from batch lookup (optional for backward compat).
        """
        fecha_registro = liquidacion_general.fecha_registro.isoformat()

        entidad_result = self._build_entidad_result(liquidacion_general.proyecto)
        proyecto_result = self._build_proyecto_result(liquidacion_general.proyecto, entidad_result)

        # Si no se proveyeron delegados explícitamente, construirlos desde la
        # relación liquidacion_delegados (comportamiento por defecto centralizado).
        if delegados is None:
            delegados = self.build_delegados_result(liquidacion_general)

        usuario_creador = None
        if liquidacion_general.usuario_creador is not None:
            usuario_creador = UsuarioCreadorResult(
                id=str(usuario_id or liquidacion_general.usuario_creador.id),
                nombres=getattr(liquidacion_general.usuario_creador, "nombres", None),
                apellidos=getattr(liquidacion_general.usuario_creador, "apellidos", None),
                email=getattr(liquidacion_general.usuario_creador, "email", None),
                dni=getattr(liquidacion_general.usuario_creador, "dni", None),
                username=getattr(liquidacion_general.usuario_creador, "username", None),
            )

        return LiquidacionGeneralResult(
            id=str(liquidacion_general.id),
            estado=liquidacion_general.estado,
            municipalidad=MunicipalidadResult(
                id=str(liquidacion_general.municipalidad.id),
                codigo=liquidacion_general.municipalidad.codigo,
                nombre=liquidacion_general.municipalidad.nombre,
            ),
            usuario_creador=usuario_creador,
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
            delegados=delegados if delegados is not None else [],
            tipo_liquidacion=(
                TipoLiquidacionResult(
                    codigo=liquidacion_general.tipo_liquidacion.codigo,
                    nombre=liquidacion_general.tipo_liquidacion.nombre,
                )
                if liquidacion_general.tipo_liquidacion
                else None
            ),
            legacy=liquidacion_general.legacy,
            codigo_cta=codigo_cta,
            comprobantes=self.build_comprobantes_result(liquidacion_general),
            denominacion_de_proyecto=liquidacion_general.denominacion_de_proyecto,
            modo_calculo=liquidacion_general.modo_calculo,
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
            nombre_propietario=proyecto.nombre_propietario,
            direccion=proyecto.direccion,
            urbanizacion=proyecto.urbanizacion,
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

        Extracts `tipo` from delegado_operacion.tipo (TITULAR/ALTERNO) when available.
        Requires liquidacion_delegados__delegado_operacion in the prefetch chain to avoid N+1.
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
                tipo=(
                    ld.delegado_operacion.tipo
                    if ld.delegado_operacion is not None
                    else None
                ),
                periodo=ld.periodo,
                mes=ld.mes,
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

    # ── Comprobante Operations ───────────────────────────────────────────────────

    def build_comprobantes_result(
        self,
        liquidacion_general,
    ) -> list[LiquidacionComprobanteResult]:
        """
        Builds a list of LiquidacionComprobanteResult for all comprobantes on a LiquidacionGeneral.
        Returns an empty list if no comprobantes exist.

        Uses prefetched data (comprobantes_prefetched) when available to avoid N+1.
        Falls back to a safe query when no prefetch is active (e.g., detail views).
        Results are ordered newest-first by fecha_emision then id.
        """
        # First check if we have prefetched data (set by list/detail queries with Prefetch)
        prefetched = getattr(liquidacion_general, "comprobantes_prefetched", None)
        if prefetched is not None:
            # Prefetch is active — use the pre-loaded list (ordered newest-first)
            return [
                LiquidacionComprobanteResult(
                    id=str(c.id),
                    tipo_comprobante=c.tipo_comprobante,
                    serie=c.serie,
                    numero=c.numero,
                    fecha_emision=c.fecha_emision.isoformat() if c.fecha_emision else None,
                    monto=float(c.monto) if c.monto else None,
                    activo=c.activo,
                    motivo_reemplazo=c.motivo_reemplazo,
                )
                for c in prefetched
            ]

        # No prefetch — fall back to a safe query
        qs = getattr(liquidacion_general, "comprobantes", None)
        if qs is None:
            return []
        return [
            LiquidacionComprobanteResult(
                id=str(c.id),
                tipo_comprobante=c.tipo_comprobante,
                serie=c.serie,
                numero=c.numero,
                fecha_emision=c.fecha_emision.isoformat() if c.fecha_emision else None,
                monto=float(c.monto) if c.monto else None,
                activo=c.activo,
                motivo_reemplazo=c.motivo_reemplazo,
            )
            for c in qs.order_by("-fecha_emision", "-id")
        ]

    def crear_comprobante(
        self,
        liquidacion_general,
        tipo_comprobante: str,
        serie: Optional[str] = None,
        numero: Optional[str] = None,
        fecha_emision: Optional[str] = None,
        monto: Optional[float] = None,
        motivo_reemplazo: Optional[str] = None,
    ) -> LiquidacionComprobante:
        """
        Creates a new comprobante for a LiquidacionGeneral, deactivating any existing active one.
        This method should be called inside a transaction.atomic() context from the orchestrator.

        PURE ORM — no business logic.

        Args:
            liquidacion_general: LiquidacionGeneral ORM instance.
            tipo_comprobante: Type of comprobante (FACTURA, BOLETA, etc.).
            serie: Optional serie.
            numero: Optional numero.
            fecha_emision: Optional fecha emision as ISO string (YYYY-MM-DD).
            monto: Optional monto.
            motivo_reemplazo: Optional motivo for replacement.

        Returns:
            The newly created LiquidacionComprobante instance.
        """
        # Deactivate any existing active comprobante
        liquidacion_general.comprobantes.filter(activo=True).update(activo=False)

        # Parse fecha_emision if provided
        parsed_fecha = None
        if fecha_emision:
            parsed_fecha = date.fromisoformat(fecha_emision)

        # Create new comprobante as activo
        return LiquidacionComprobante.objects.create(
            liquidacion_general=liquidacion_general,
            tipo_comprobante=tipo_comprobante,
            serie=serie,
            numero=numero,
            fecha_emision=parsed_fecha,
            monto=Decimal(str(monto)) if monto is not None else None,
            activo=True,
            motivo_reemplazo=motivo_reemplazo,
        )
