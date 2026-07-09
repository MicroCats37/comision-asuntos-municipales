"""
MecanicaSuelosPresenter — transforma resultados domain a schemas HTTP para Mecánica de Suelos.
"""
from typing import Optional, Union

from modules.liquidaciones.domain.schemas.mecanica_suelos import (
    LiquidacionMecanicaSuelosResult,
)
from modules.liquidaciones.domain.schemas.shared import (
    LiquidacionM2CalculoData,
    CotizacionM2QuoteData,
)
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
            area_minima=float(calculo.tarifa.area_minima),
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
                    area_minima=float(calculo_rev.tarifa.area_minima),
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
