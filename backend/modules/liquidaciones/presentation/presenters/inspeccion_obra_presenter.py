"""
InspeccionObraPresenter — transforma resultados domain a schemas HTTP para Inspección de Obra.
"""
from typing import Optional, Union

from modules.liquidaciones.domain.schemas.inspeccion_obra import (
    LiquidacionInspeccionObraResult,
)
from modules.liquidaciones.domain.schemas.shared import (
    LiquidacionVisitasCalculoData,
    CotizacionVisitasQuoteData,
)
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
