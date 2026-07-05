"""
NuevosPresenters — transforma resultados domain a schemas HTTP para los nuevos formularios.
"""
import uuid
from typing import Optional, Union

from modules.liquidaciones.domain.schemas_nuevos import (
    LiquidacionHabilitacionUrbanaResult,
    LiquidacionMecanicaSuelosResult,
    LiquidacionImpactoVialResult,
    LiquidacionTaludesResult,
    LiquidacionInspeccionObraResult,
    LiquidacionM2CalculoData,
    LiquidacionVisitasCalculoData,
    CotizacionM2QuoteData,
    CotizacionVisitasQuoteData,
    CotizacionM2RevisionData,
    CotizacionVisitasRevisionData,
)
from modules.liquidaciones.presentation.schemas_nuevos import (
    LiquidacionHabilitacionUrbanaOut,
    LiquidacionMecanicaSuelosOut,
    LiquidacionImpactoVialOut,
    LiquidacionTaludesOut,
    LiquidacionInspeccionObraOut,
    LiquidacionM2CalculoOut,
    LiquidacionVisitasCalculoOut,
    TarifaM2Out,
    TarifaVisitasOut,
    TotalesOut,
    EntidadOut,
    ProyectoOut,
    LiquidacionOut,
    MunicipalidadesSnapshotOut,
    CotizacionM2QuoteOut,
    CotizacionM2RevisionOut,
    CotizacionM2MetadataOut,
    CotizacionVisitasQuoteOut,
    CotizacionVisitasRevisionOut,
    CotizacionVisitasMetadataOut,
    # Alias para evitar renombrar el base
    LiquidacionNuevaBaseOut,
)


class NuevosPresenters:
    """
    Transforma objetos de resultado del dominio a esquemas de respuesta HTTP
    para los 5 nuevos formularios de liquidación.
    """

    # =============================================================================
    # Helpers privados
    # =============================================================================

    @staticmethod
    def _build_entidad(result: Union[
        LiquidacionHabilitacionUrbanaResult,
        LiquidacionMecanicaSuelosResult,
        LiquidacionImpactoVialResult,
        LiquidacionTaludesResult,
        LiquidacionInspeccionObraResult,
    ]) -> Optional[EntidadOut]:
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
    def _build_proyecto(result: Union[
        LiquidacionHabilitacionUrbanaResult,
        LiquidacionMecanicaSuelosResult,
        LiquidacionImpactoVialResult,
        LiquidacionTaludesResult,
        LiquidacionInspeccionObraResult,
    ]) -> ProyectoOut:
        """Construir proyecto anidado."""
        return ProyectoOut(
            id=result.proyecto_id,
            public_id=result.proyecto_public_id,
            nombre=result.proyecto_nombre,
            direccion=result.proyecto_direccion,
            entidad=NuevosPresenters._build_entidad(result),
        )

    @staticmethod
    def _build_municipalidad(result: Union[
        LiquidacionHabilitacionUrbanaResult,
        LiquidacionMecanicaSuelosResult,
        LiquidacionImpactoVialResult,
        LiquidacionTaludesResult,
        LiquidacionInspeccionObraResult,
    ]) -> MunicipalidadesSnapshotOut:
        """Construir municipalidad anidada (básica, sin detalle de provincia/distrito)."""
        return MunicipalidadesSnapshotOut(
            id=result.municipalidad_id,
            nombre=result.municipalidad_nombre,
            codigo=None,
        )

    @staticmethod
    def _build_liquidacion(result: Union[
        LiquidacionHabilitacionUrbanaResult,
        LiquidacionMecanicaSuelosResult,
        LiquidacionImpactoVialResult,
        LiquidacionTaludesResult,
        LiquidacionInspeccionObraResult,
    ]) -> LiquidacionOut:
        """Construir liquidacion anidada."""
        return LiquidacionOut(
            id=result.liquidacion_id,
            public_id=result.liquidacion_public_id,
            estado=result.estado,
            fecha_creacion=result.fecha_creacion,
            proyecto=NuevosPresenters._build_proyecto(result),
            municipalidad=NuevosPresenters._build_municipalidad(result),
            expediente=getattr(result, "expediente", None),
            observacion=result.observacion or "",
        )

    @staticmethod
    def _build_totales(result: Union[
        LiquidacionHabilitacionUrbanaResult,
        LiquidacionMecanicaSuelosResult,
        LiquidacionImpactoVialResult,
        LiquidacionTaludesResult,
        LiquidacionInspeccionObraResult,
    ]) -> TotalesOut:
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
    def _build_calculo_m2(
        calculo_data: LiquidacionM2CalculoData,
    ) -> LiquidacionM2CalculoOut:
        """Construir salida de cálculo M2."""
        return LiquidacionM2CalculoOut(
            area_solicitada=float(calculo_data.area_solicitada),
            area_base_calculo=float(calculo_data.area_base_calculo),
            derecho=float(calculo_data.derecho),
            tarifa=NuevosPresenters._build_tarifa_m2(calculo_data),
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
    def _build_calculo_visitas(
        calculo_data: LiquidacionVisitasCalculoData,
    ) -> LiquidacionVisitasCalculoOut:
        """Construir salida de cálculo visitas."""
        return LiquidacionVisitasCalculoOut(
            cantidad_visitas=calculo_data.cantidad_visitas,
            visitas_base_calculo=calculo_data.visitas_base_calculo,
            derecho=float(calculo_data.derecho),
            categoria=calculo_data.categoria,
            tarifa=NuevosPresenters._build_tarifa_visitas(calculo_data),
        )

    @staticmethod
    def _get_tipo_liquidacion(result: Union[
        LiquidacionHabilitacionUrbanaResult,
        LiquidacionMecanicaSuelosResult,
        LiquidacionImpactoVialResult,
        LiquidacionTaludesResult,
        LiquidacionInspeccionObraResult,
    ]) -> str:
        """Obtener tipo_liquidacion desde el resultado."""
        # Se almacena como campo en cada result específico
        return getattr(result, "tipo_liquidacion", "UNKNOWN")

    @staticmethod
    def _get_tramite_accion(result: Union[
        LiquidacionHabilitacionUrbanaResult,
        LiquidacionMecanicaSuelosResult,
        LiquidacionImpactoVialResult,
        LiquidacionTaludesResult,
        LiquidacionInspeccionObraResult,
    ]) -> str:
        """Obtener tramite_accion desde el resultado."""
        return getattr(result, "tramite_accion", "PRIMERA_REVISION")

    # =============================================================================
    # Presenters para los 5 formularios M2 (HU, MS, IV, TAL)
    # =============================================================================

    @staticmethod
    def present_habilitacion_urbana(
        result: LiquidacionHabilitacionUrbanaResult,
        calculo_m2: LiquidacionM2CalculoData,
    ) -> LiquidacionHabilitacionUrbanaOut:
        """
        Transforma un LiquidacionHabilitacionUrbanaResult a LiquidacionHabilitacionUrbanaOut.

        Args:
            result: Resultado completo de la liquidación
            calculo_m2: Datos del cálculo por M2

        Returns:
            LiquidacionHabilitacionUrbanaOut schema para respuesta HTTP
        """
        return LiquidacionHabilitacionUrbanaOut(
            liquidacion=NuevosPresenters._build_liquidacion(result),
            tipo_liquidacion="HABILITACION_URBANA",
            tramite_accion=NuevosPresenters._get_tramite_accion(result),
            calculo_m2=NuevosPresenters._build_calculo_m2(calculo_m2),
            totales=NuevosPresenters._build_totales(result),
        )

    @staticmethod
    def present_mecanica_suelos(
        result: LiquidacionMecanicaSuelosResult,
        calculo_m2: LiquidacionM2CalculoData,
    ) -> LiquidacionMecanicaSuelosOut:
        """
        Transforma un LiquidacionMecanicaSuelosResult a LiquidacionMecanicaSuelosOut.
        """
        return LiquidacionMecanicaSuelosOut(
            liquidacion=NuevosPresenters._build_liquidacion(result),
            tipo_liquidacion="MECANICA_SUELOS",
            tramite_accion=NuevosPresenters._get_tramite_accion(result),
            calculo_m2=NuevosPresenters._build_calculo_m2(calculo_m2),
            totales=NuevosPresenters._build_totales(result),
        )

    @staticmethod
    def present_impacto_vial(
        result: LiquidacionImpactoVialResult,
        calculo_m2: LiquidacionM2CalculoData,
    ) -> LiquidacionImpactoVialOut:
        """
        Transforma un LiquidacionImpactoVialResult a LiquidacionImpactoVialOut.
        """
        return LiquidacionImpactoVialOut(
            liquidacion=NuevosPresenters._build_liquidacion(result),
            tipo_liquidacion="IMPACTO_VIAL",
            tramite_accion=NuevosPresenters._get_tramite_accion(result),
            calculo_m2=NuevosPresenters._build_calculo_m2(calculo_m2),
            totales=NuevosPresenters._build_totales(result),
        )

    @staticmethod
    def present_taludes(
        result: LiquidacionTaludesResult,
        calculo_m2: LiquidacionM2CalculoData,
    ) -> LiquidacionTaludesOut:
        """
        Transforma un LiquidacionTaludesResult a LiquidacionTaludesOut.
        """
        return LiquidacionTaludesOut(
            liquidacion=NuevosPresenters._build_liquidacion(result),
            tipo_liquidacion="TALUDES",
            tramite_accion=NuevosPresenters._get_tramite_accion(result),
            calculo_m2=NuevosPresenters._build_calculo_m2(calculo_m2),
            totales=NuevosPresenters._build_totales(result),
        )

    # =============================================================================
    # Presenter para Inspección de Obra
    # =============================================================================

    @staticmethod
    def present_inspeccion_obra(
        result: LiquidacionInspeccionObraResult,
        calculo_visitas: LiquidacionVisitasCalculoData,
    ) -> LiquidacionInspeccionObraOut:
        """
        Transforma un LiquidacionInspeccionObraResult a LiquidacionInspeccionObraOut.
        """
        return LiquidacionInspeccionObraOut(
            liquidacion=NuevosPresenters._build_liquidacion(result),
            tipo_liquidacion="INSPECCION_OBRA",
            tramite_accion=NuevosPresenters._get_tramite_accion(result),
            calculo_m2=None,
            calculo_visitas=NuevosPresenters._build_calculo_visitas(calculo_visitas),
            totales=NuevosPresenters._build_totales(result),
        )

    # =============================================================================
    # Presenters para Cotización M2
    # =============================================================================

    @staticmethod
    def present_cotizacion_m2(
        result: CotizacionM2QuoteData,
    ) -> CotizacionM2QuoteOut:
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

    # =============================================================================
    # Presenters para Cotización Visitas
    # =============================================================================

    @staticmethod
    def present_cotizacion_visitas(
        result: CotizacionVisitasQuoteData,
    ) -> CotizacionVisitasQuoteOut:
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
