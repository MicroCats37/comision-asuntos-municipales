"""
InspeccionObraPresenter — transforma resultados domain a schemas HTTP para Inspección de Obra.
"""
import uuid as _uuid
from typing import Optional, Union

from modules.liquidaciones.domain.schemas.inspeccion_obra import (
    LiquidacionInspeccionObraResult,
)
from modules.liquidaciones.domain.schemas.shared import (
    LiquidacionVisitasCalculoData,
    CotizacionVisitasQuoteData,
)
from modules.liquidaciones.domain.schemas import LiquidacionGeneralListItem, LiquidacionGeneralResult
from modules.liquidaciones.presentation.schemas.inspeccion_obra_schemas import (
    LiquidacionInspeccionObraOut,
    TarifaVisitasOut,
    LiquidacionVisitasCalculoOut,
    TotalesOut,
    EntidadOut,
    ProyectoOut,
    LiquidacionOut,
    MunicipalidadesSnapshotOut,
    CotizacionVisitasQuoteOut,
    CotizacionVisitasRevisionOut,
    CotizacionVisitasMetadataOut,
    LiquidacionIOListItemOut,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import (
    EntidadListItemOut,
    ProyectoListItemOut,
    LiquidacionGeneralListItemOut,
    MunicipalidadListItemOut,
    ValoresListItemOut,
    ProyectistaListItemOut,
    DelegadoListItemOut,
    InspectorListItemOut,
    ContactoListItemOut,
    TarifaRevisionOut,
    EspecialidadRevisionOut,
    RevisionListItemOut,
)


class InspeccionObraPresenter:
    """Transforma objetos de resultado del dominio a esquemas de respuesta HTTP para Inspección de Obra."""

    # =============================================================================
    # Helpers privados
    # =============================================================================

    @staticmethod
    def _build_entidad(result: LiquidacionInspeccionObraResult) -> Optional[EntidadOut]:
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
    def _build_proyecto(result: LiquidacionInspeccionObraResult) -> ProyectoOut:
        """Construir proyecto anidado."""
        return ProyectoOut(
            id=result.proyecto_id,
            public_id=result.proyecto_public_id,
            nombre=result.proyecto_nombre,
            direccion=result.proyecto_direccion,
            entidad=InspeccionObraPresenter._build_entidad(result),
        )

    @staticmethod
    def _build_municipalidad(result: LiquidacionInspeccionObraResult) -> MunicipalidadesSnapshotOut:
        """Construir municipalidad anidada (básica, sin detalle de provincia/distrito)."""
        return MunicipalidadesSnapshotOut(
            id=result.municipalidad_id,
            nombre=result.municipalidad_nombre,
            codigo=None,
        )

    @staticmethod
    def _build_liquidacion(result: LiquidacionInspeccionObraResult) -> LiquidacionOut:
        """Construir liquidacion anidada."""
        return LiquidacionOut(
            id=result.liquidacion_id,
            public_id=result.liquidacion_public_id,
            estado=result.estado,
            fecha_creacion=result.fecha_creacion,
            proyecto=InspeccionObraPresenter._build_proyecto(result),
            municipalidad=InspeccionObraPresenter._build_municipalidad(result),
            expediente=getattr(result, "expediente", None),
            observacion=result.observacion or "",
        )

    @staticmethod
    def _build_totales(result: LiquidacionInspeccionObraResult) -> TotalesOut:
        """Construir totales."""
        return TotalesOut(
            subtotal=float(result.totales_subtotal),
            igv=float(result.totales_igv),
            total=float(result.totales_total_liquidacion),
            liquidacion_total=float(result.totales_total_liquidacion),
            total_a_pagar=float(result.totales_total_a_pagar),
        )

    @staticmethod
    def _build_tarifa_visitas(calculo: LiquidacionVisitasCalculoData) -> TarifaVisitasOut:
        """Construir tarifa visitas desde dato de cálculo."""
        return TarifaVisitasOut(
            id=calculo.tarifa.id,
            costo_por_visita=float(calculo.tarifa.costo_por_visita),
            visitas_minimas=calculo.tarifa.visitas_minimas,
        )

    @staticmethod
    def _build_calculo_visitas(calculo_data: LiquidacionVisitasCalculoData) -> LiquidacionVisitasCalculoOut:
        """Construir salida de cálculo visitas."""
        return LiquidacionVisitasCalculoOut(
            cantidad_visitas=calculo_data.cantidad_visitas,
            visitas_base_calculo=calculo_data.visitas_base_calculo,
            derecho=float(calculo_data.derecho),
            categoria=calculo_data.categoria,
            tarifa=InspeccionObraPresenter._build_tarifa_visitas(calculo_data),
        )

    @staticmethod
    def _get_tramite_accion(result: LiquidacionInspeccionObraResult) -> str:
        """Obtener tramite_accion desde el resultado."""
        return getattr(result, "tramite_accion", "PRIMERA_REVISION")

    # =============================================================================
    # Presenter principal
    # =============================================================================

    @staticmethod
    def present(
        result: LiquidacionInspeccionObraResult,
        calculo_visitas: LiquidacionVisitasCalculoData,
    ) -> LiquidacionInspeccionObraOut:
        """
        Transforma un LiquidacionInspeccionObraResult a LiquidacionInspeccionObraOut.
        """
        return LiquidacionInspeccionObraOut(
            liquidacion=InspeccionObraPresenter._build_liquidacion(result),
            tipo_liquidacion="INSPECCION_OBRA",
            tramite_accion=InspeccionObraPresenter._get_tramite_accion(result),
            calculo_m2=None,
            calculo_visitas=InspeccionObraPresenter._build_calculo_visitas(calculo_visitas),
            totales=InspeccionObraPresenter._build_totales(result),
        )

    # =============================================================================
    # Presenter para Cotización Visitas
    # =============================================================================

    @staticmethod
    def present_cotizacion(result: CotizacionVisitasQuoteData) -> CotizacionVisitasQuoteOut:
        """
        Transforma un CotizacionVisitasQuoteData a CotizacionVisitasQuoteOut.
        """
        calculo_rev = result.calculo_visitas
        return CotizacionVisitasQuoteOut(
            numero_revision=result.numero_revision,
            calculo_visitas=CotizacionVisitasRevisionOut(
                cantidad_visitas=calculo_rev.cantidad_visitas,
                visitas_base_calculo=calculo_rev.visitas_base_calculo,
                derecho=float(calculo_rev.derecho),
                categoria=calculo_rev.categoria,
                tarifa=TarifaVisitasOut(
                    id=calculo_rev.tarifa.id,
                    costo_por_visita=float(calculo_rev.tarifa.costo_por_visita),
                    visitas_minimas=calculo_rev.tarifa.visitas_minimas,
                ),
            ),
            totales=TotalesOut(
                subtotal=float(result.totales.subtotal),
                igv=float(result.totales.igv),
                total=float(result.totales.total),
                liquidacion_total=float(result.totales.liquidacion_total),
                total_a_pagar=float(result.totales.total_a_pagar),
            ),
            metadata=CotizacionVisitasMetadataOut(
                igv_valor=float(result.metadata.igv_valor),
                uit_valor=float(result.metadata.uit_valor),
                cantidad_visitas=result.metadata.cantidad_visitas,
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
            entidad=InspeccionObraPresenter._build_entidad_list(result),
        )

    @staticmethod
    def present_list_item(result: LiquidacionGeneralListItem) -> LiquidacionGeneralListItemOut:
        """
        Transforma un LiquidacionGeneralListItem a LiquidacionGeneralListItemOut.

        Retorna la estructura general de lista de liquidaciones (Phase 4+) con
        todos los campos: id, public_id, tipo_liquidacion, estado, numero_revision,
        fecha_registro, proyecto, entidad, municipalidad, valores, proyectistas,
        delegados, contactos, revisiones, más campos financieros al raíz
        (subtotal, igv, total, total_a_pagar).
        """
        return LiquidacionGeneralListItemOut(
            id=result.id,
            public_id=result.public_id,
            tipo_liquidacion=result.tipo_liquidacion,
            estado=result.estado,
            numero_revision=result.numero_revision,
            fecha_registro=result.fecha_registro,
            tramite_accion=result.tramite_accion,
            tipo_tramite=result.tipo_tramite,
            expediente=result.expediente,
            observacion=result.observacion,
            proyecto=InspeccionObraPresenter._build_proyecto_list(result),
            entidad=InspeccionObraPresenter._build_entidad_list(result),
            municipalidad=MunicipalidadListItemOut(
                id=result.municipalidad.id,
                nombre=result.municipalidad.nombre,
                codigo=result.municipalidad.codigo,
                provincia=result.municipalidad.provincia,
                distrito=result.municipalidad.distrito,
            ),
            valores=ValoresListItemOut(
                subtotal=result.valores.subtotal,
                igv=result.valores.igv,
                total=result.valores.total,
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
                RevisionListItemOut(
                    id=r.id,
                    especialidades=[
                        EspecialidadRevisionOut(id=e.id, nombre=e.nombre)
                        for e in r.especialidades
                    ],
                    tarifa=TarifaRevisionOut(**r.tarifa.model_dump()) if r.tarifa else None,
                ) for r in result.revisiones
            ],
            inspectores=[
                InspectorListItemOut(
                    id=p.id,
                    perfil_ingeniero_id=p.perfil_ingeniero_id,
                    perfil_ingeniero_nombres=p.perfil_ingeniero_nombres,
                    perfil_ingeniero_apellidos=p.perfil_ingeniero_apellidos,
                    perfil_ingeniero_cip=p.perfil_ingeniero_cip,
                    especialidad_id=p.especialidad_id,
                    especialidad_nombre=p.especialidad_nombre,
                    tipo_liquidacion=p.tipo_liquidacion,
                    categoria=p.categoria,
                    numero_registro=p.numero_registro,
                    vigencia=str(p.vigencia) if p.vigencia else None,
                ) for p in result.inspectores
            ],
            subtotal=result.subtotal,
            igv=result.igv,
            total=result.total,
            total_a_pagar=result.total_a_pagar,
        )

    @staticmethod
    def present_list(
        results: list[LiquidacionGeneralListItem],
    ) -> list[LiquidacionGeneralListItemOut]:
        """
        Transforma una lista de LiquidacionGeneralListItem a lista de LiquidacionGeneralListItemOut.
        """
        return [InspeccionObraPresenter.present_list_item(r) for r in results]

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
            entidad=InspeccionObraPresenter._build_entidad_detail(result),
        )

    @staticmethod
    def present_detail_item(result: LiquidacionGeneralResult) -> LiquidacionIOListItemOut:
        """
        Transforma un LiquidacionGeneralResult (DTO plano) a LiquidacionIOListItemOut.

        Args:
            result: LiquidacionGeneralResult con campos planos del detalle

        Returns:
            LiquidacionIOListItemOut schema para respuesta HTTP de detalle
        """
        subtotal = float(result.subtotal) if result.subtotal else 0.0
        igv = float(result.igv) if result.igv else 0.0
        total = float(result.total) if result.total else 0.0
        total_a_pagar = float(result.total_a_pagar) if result.total_a_pagar else 0.0

        return LiquidacionIOListItemOut(
            id=result.id,
            public_id=result.public_id,
            tipo_liquidacion=result.tipo_liquidacion,
            estado=result.estado,
            numero_revision=result.numero_revision,
            fecha_registro=result.fecha_registro,
            proyecto=InspeccionObraPresenter._build_proyecto_detail(result),
            entidad=InspeccionObraPresenter._build_entidad_detail(result),
            municipalidad=MunicipalidadListItemOut(
                id=result.municipalidad_id or _uuid.UUID('00000000-0000-0000-0000-000000000000'),
                nombre=result.municipalidad_nombre or '',
                codigo=None,
                provincia=None,
                distrito=None,
            ),
            valores=ValoresListItemOut(
                subtotal=subtotal,
                igv=igv,
                total=total,
                total_a_pagar=total_a_pagar,
            ),
            proyectistas=[],
            delegados=[],
            inspectores=[],
            contactos=[],
            revisiones=[],
        )
