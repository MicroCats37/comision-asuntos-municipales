"""
MecanicaSuelosPresenter — transforma resultados domain a schemas HTTP para Mecánica de Suelos.
"""
import uuid as _uuid
from typing import Optional, Union

from modules.liquidaciones.domain.schemas.mecanica_suelos import (
    LiquidacionMecanicaSuelosResult,
)
from modules.liquidaciones.domain.schemas.shared import (
    LiquidacionM2CalculoData,
    CotizacionM2QuoteData,
)
from modules.liquidaciones.domain.schemas import LiquidacionGeneralListItem, LiquidacionGeneralResult
from modules.liquidaciones.presentation.schemas.mecanica_suelos_schemas import (
    LiquidacionMecanicaSuelosOut,
    TarifaM2Out,
    LiquidacionM2CalculoOut,
    TotalesOut,
    EntidadOut,
    ProyectoOut,
    LiquidacionOut,
    MunicipalidadesSnapshotOut,
    CotizacionM2QuoteOut,
    CotizacionM2RevisionOut,
    CotizacionM2MetadataOut,
    LiquidacionM2ListItemOut,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import (
    EntidadListItemOut,
    ProyectoListItemOut,
    MunicipalidadListItemOut,
    ValoresM2CleanOut,
    ProyectistaListItemOut,
    DelegadoListItemOut,
    ContactoListItemOut,
    TarifaRevisionOut,
    EspecialidadRevisionOut,
    RevisionListItemCleanOut,
)


class MecanicaSuelosPresenter:
    """Transforma objetos de resultado del dominio a esquemas de respuesta HTTP para Mecánica de Suelos."""

    # =============================================================================
    # Helpers privados
    # =============================================================================

    @staticmethod
    def _build_entidad(result: LiquidacionMecanicaSuelosResult) -> Optional[EntidadOut]:
        """Construir entidad anidada si existe."""
        if result.proyecto_entidad_id:
            return EntidadOut(
                id=result.proyecto_entidad_id,
                tipo=result.proyecto_entidad_tipo,
                nombre=result.proyecto_entidad_nombre,
                ruc=result.proyecto_entidad_ruc,
            )
        return None

    @staticmethod
    def _build_proyecto(result: LiquidacionMecanicaSuelosResult) -> ProyectoOut:
        """Construir proyecto anidado."""
        return ProyectoOut(
            id=result.proyecto_id,
            public_id=result.proyecto_public_id,
            nombre=result.proyecto_nombre,
            direccion=result.proyecto_direccion,
            entidad=MecanicaSuelosPresenter._build_entidad(result),
        )

    @staticmethod
    def _build_municipalidad(result: LiquidacionMecanicaSuelosResult) -> MunicipalidadesSnapshotOut:
        """Construir municipalidad anidada (básica, sin detalle de provincia/distrito)."""
        return MunicipalidadesSnapshotOut(
            id=result.municipalidad_id,
            nombre=result.municipalidad_nombre,
            codigo=None,
        )

    @staticmethod
    def _build_liquidacion(result: LiquidacionMecanicaSuelosResult) -> LiquidacionOut:
        """Construir liquidacion anidada."""
        return LiquidacionOut(
            id=result.liquidacion_id,
            public_id=result.liquidacion_public_id,
            estado=result.estado,
            fecha_creacion=result.fecha_creacion,
            proyecto=MecanicaSuelosPresenter._build_proyecto(result),
            municipalidad=MecanicaSuelosPresenter._build_municipalidad(result),
            expediente=getattr(result, "expediente", None),
            observacion=result.observacion or "",
        )

    @staticmethod
    def _build_totales(result: LiquidacionMecanicaSuelosResult) -> TotalesOut:
        """Construir totales."""
        return TotalesOut(
            subtotal=float(result.totales_subtotal),
            igv=float(result.totales_igv),
            total=float(result.totales_total_liquidacion),
            liquidacion_total=float(result.totales_total_liquidacion),
            total_a_pagar=float(result.totales_total_a_pagar),
        )

    @staticmethod
    def _build_tarifa_m2(calculo: LiquidacionM2CalculoData) -> TarifaM2Out:
        """Construir tarifa M2 desde dato de cálculo."""
        return TarifaM2Out(
            id=calculo.tarifa.id,
            costo_por_m2=float(calculo.tarifa.costo_por_m2),
            area_m2=float(calculo.tarifa.area_m2),
            derecho_minimo=float(calculo.tarifa.derecho_minimo),
            derecho_maximo=float(calculo.tarifa.derecho_maximo) if calculo.tarifa.derecho_maximo else None,
        )

    @staticmethod
    def _build_calculo_m2(calculo_data: LiquidacionM2CalculoData) -> LiquidacionM2CalculoOut:
        """Construir salida de cálculo M2."""
        return LiquidacionM2CalculoOut(
            area_solicitada=float(calculo_data.area_solicitada),
            area_base_calculo=float(calculo_data.area_base_calculo),
            derecho=float(calculo_data.derecho),
            tarifa=MecanicaSuelosPresenter._build_tarifa_m2(calculo_data),
        )

    @staticmethod
    def _get_tramite_accion(result: LiquidacionMecanicaSuelosResult) -> str:
        """Obtener tramite_accion desde el resultado."""
        return getattr(result, "tramite_accion", "PRIMERA_REVISION")

    # =============================================================================
    # Presenter principal
    # =============================================================================

    @staticmethod
    def present(
        result: LiquidacionMecanicaSuelosResult,
        calculo_m2: LiquidacionM2CalculoData,
    ) -> LiquidacionMecanicaSuelosOut:
        """
        Transforma un LiquidacionMecanicaSuelosResult a LiquidacionMecanicaSuelosOut.
        """
        return LiquidacionMecanicaSuelosOut(
            liquidacion=MecanicaSuelosPresenter._build_liquidacion(result),
            tipo_liquidacion="MECANICA_SUELOS",
            tramite_accion=MecanicaSuelosPresenter._get_tramite_accion(result),
            calculo_m2=MecanicaSuelosPresenter._build_calculo_m2(calculo_m2),
            totales=MecanicaSuelosPresenter._build_totales(result),
        )

    # =============================================================================
    # Presenter para Cotización M2
    # =============================================================================

    @staticmethod
    def present_cotizacion(result: CotizacionM2QuoteData) -> CotizacionM2QuoteOut:
        """
        Transforma un CotizacionM2QuoteData a CotizacionM2QuoteOut.
        """
        calculo_rev = result.calculo_m2
        return CotizacionM2QuoteOut(
            numero_revision=result.numero_revision,
            calculo_m2=CotizacionM2RevisionOut(
                area_solicitada=float(calculo_rev.area_solicitada),
                area_base_calculo=float(calculo_rev.area_base_calculo),
                derecho=float(calculo_rev.derecho),
                tarifa=TarifaM2Out(
                    id=calculo_rev.tarifa.id,
                    costo_por_m2=float(calculo_rev.tarifa.costo_por_m2),
                    area_m2=float(calculo_rev.tarifa.area_m2),
                    derecho_minimo=float(calculo_rev.tarifa.derecho_minimo),
                    derecho_maximo=float(calculo_rev.tarifa.derecho_maximo) if calculo_rev.tarifa.derecho_maximo else None,
                ),
            ),
            totales=TotalesOut(
                subtotal=float(result.totales.subtotal),
                igv=float(result.totales.igv),
                total=float(result.totales.total),
                liquidacion_total=float(result.totales.liquidacion_total),
                total_a_pagar=float(result.totales.total_a_pagar),
            ),
            metadata=CotizacionM2MetadataOut(
                igv_valor=float(result.metadata.igv_valor),
                uit_valor=float(result.metadata.uit_valor),
                area_solicitada=float(result.metadata.area_solicitada) if result.metadata.area_solicitada else None,
            ),
        )

    # =============================================================================
    # Presenter para Lista
    # =============================================================================

    @staticmethod
    def _build_entidad_list(result: LiquidacionGeneralListItem) -> Optional[EntidadListItemOut]:
        """Construir entidad anidada para list item."""
        if not result.entidad or not result.entidad.id:
            return None
        return EntidadListItemOut(
            id=result.entidad.id,
            tipo=result.entidad.tipo,
            nombre=result.entidad.nombre,
            ruc=result.entidad.ruc,
        )

    @staticmethod
    def _build_proyecto_list(result: LiquidacionGeneralListItem) -> ProyectoListItemOut:
        """Construir proyecto anidado para list item."""
        return ProyectoListItemOut(
            id=result.proyecto.id,
            public_id=result.proyecto.public_id,
            nombre=result.proyecto.nombre,
            direccion=result.proyecto.direccion,
            valor_proyecto=result.proyecto.valor_proyecto,
            entidad=MecanicaSuelosPresenter._build_entidad_list(result),
        )

    @staticmethod
    def present_list_item(result: LiquidacionGeneralListItem) -> LiquidacionM2ListItemOut:
        """
        Transforma un LiquidacionGeneralListItem a LiquidacionM2ListItemOut.
        """
        return LiquidacionM2ListItemOut(
            id=result.id,
            public_id=result.public_id,
            tipo_liquidacion=result.tipo_liquidacion,
            estado=result.estado,
            numero_revision=result.numero_revision,
            fecha_registro=result.fecha_registro,
            proyecto=MecanicaSuelosPresenter._build_proyecto_list(result),
            entidad=MecanicaSuelosPresenter._build_entidad_list(result),
            municipalidad=MunicipalidadListItemOut(
                id=result.municipalidad.id,
                nombre=result.municipalidad.nombre,
                codigo=result.municipalidad.codigo,
                provincia=result.municipalidad.provincia,
                distrito=result.municipalidad.distrito,
            ),
            valores=ValoresM2CleanOut(
                subtotal=result.valores.subtotal,
                total_a_pagar=result.valores.total_a_pagar,
            ),
            proyectistas=[
                ProyectistaListItemOut(
                    id=p.id,
                    perfil_ingeniero_id=p.perfil_ingeniero_id,
                    perfil_ingeniero_nombres=p.perfil_ingeniero_nombres,
                    perfil_ingeniero_apellidos=p.perfil_ingeniero_apellidos,
                    perfil_ingeniero_cip=p.perfil_ingeniero_cip,
                    especialidad_id=p.especialidad_id,
                    especialidad_nombre=p.especialidad_nombre,
                    descripcion=p.descripcion,
                ) for p in result.proyectistas
            ],
            delegados=[
                DelegadoListItemOut(
                    id=d.id,
                    perfil_ingeniero_id=d.perfil_ingeniero_id,
                    perfil_ingeniero_nombres=d.perfil_ingeniero_nombres,
                    perfil_ingeniero_apellidos=d.perfil_ingeniero_apellidos,
                    perfil_ingeniero_cip=d.perfil_ingeniero_cip,
                    especialidad_id=d.especialidad_id,
                    especialidad_nombre=d.especialidad_nombre,
                    tipo=d.tipo,
                ) for d in result.delegados
            ],
            contactos=[
                ContactoListItemOut(
                    id=c.id,
                    nombres=c.nombres,
                    apellidos=c.apellidos,
                    dni=c.dni,
                    cargo=c.cargo,
                    telefono=c.telefono,
                    celular=c.celular,
                    email=c.email,
                    direccion=c.direccion,
                    principal=c.principal,
                    descripcion=c.descripcion,
                ) for c in result.contactos
            ],
            revisiones=[
                RevisionListItemCleanOut(
                    id=r.id,
                    especialidades=[
                        EspecialidadRevisionOut(id=e.id, nombre=e.nombre)
                        for e in r.especialidades
                    ],
                    tarifa=TarifaRevisionOut(**r.tarifa.model_dump()) if r.tarifa else None,
                ) for r in result.revisiones
            ],
        )

    @staticmethod
    def present_list(
        results: list[LiquidacionGeneralListItem],
    ) -> list[LiquidacionM2ListItemOut]:
        """
        Transforma una lista de LiquidacionGeneralListItem a lista de LiquidacionM2ListItemOut.
        """
        return [MecanicaSuelosPresenter.present_list_item(r) for r in results]

    # =============================================================================
    # Presenter para Detalle (desde LiquidacionGeneralResult plano)
    # =============================================================================

    @staticmethod
    def _build_entidad_detail(result: LiquidacionGeneralResult) -> Optional[EntidadListItemOut]:
        """Construir entidad anidada para detail item desde campos planos."""
        if not result.entidad_id:
            return None
        return EntidadListItemOut(
            id=result.entidad_id,
            tipo=result.entidad_tipo,
            nombre=result.entidad_nombre,
            ruc=result.entidad_ruc,
        )

    @staticmethod
    def _build_proyecto_detail(result: LiquidacionGeneralResult) -> ProyectoListItemOut:
        """Construir proyecto anidado para detail item desde campos planos."""
        return ProyectoListItemOut(
            id=result.proyecto_id or _uuid.UUID('00000000-0000-0000-0000-000000000000'),
            public_id=result.proyecto_public_id or '',
            nombre=result.proyecto_nombre or '',
            direccion=result.proyecto_direccion,
            valor_proyecto=0.0,
            entidad=MecanicaSuelosPresenter._build_entidad_detail(result),
        )

    @staticmethod
    def present_detail_item(result: LiquidacionGeneralResult) -> LiquidacionM2ListItemOut:
        """
        Transforma un LiquidacionGeneralResult (DTO plano) a LiquidacionM2ListItemOut.

        Args:
            result: LiquidacionGeneralResult con campos planos del detalle

        Returns:
            LiquidacionM2ListItemOut schema para respuesta HTTP de detalle
        """
        subtotal = float(result.subtotal) if result.subtotal else 0.0
        total_a_pagar = float(result.total_a_pagar) if result.total_a_pagar else 0.0

        return LiquidacionM2ListItemOut(
            id=result.id,
            public_id=result.public_id,
            tipo_liquidacion=result.tipo_liquidacion,
            estado=result.estado,
            numero_revision=result.numero_revision,
            fecha_registro=result.fecha_registro,
            proyecto=MecanicaSuelosPresenter._build_proyecto_detail(result),
            entidad=MecanicaSuelosPresenter._build_entidad_detail(result),
            municipalidad=MunicipalidadListItemOut(
                id=result.municipalidad_id or _uuid.UUID('00000000-0000-0000-0000-000000000000'),
                nombre=result.municipalidad_nombre or '',
                codigo=None,
                provincia=None,
                distrito=None,
            ),
            valores=ValoresM2CleanOut(
                subtotal=subtotal,
                total_a_pagar=total_a_pagar,
            ),
            proyectistas=[],
            delegados=[],
            contactos=[],
            revisiones=[],
        )
