"""
LiquidacionPorCategoriaVisitasPresenter — Presenter reutilizable para cálculos de Visitas.
"""
import uuid
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorCategoriaVisitas,
)
from modules.finanzas.domain.models.impuestos import UIT
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionVisitasResult
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
    TarifasVigentesPorCategoriaVisitasOutputSchema,
    TarifaVigenteVisitasDatos,
    CotizarPorCategoriaVisitasOutputSchema,
    CotizarPorCategoriaVisitasDatosOutputSchema,
    CotizarPorCategoriaVisitasTarifaOut,
    CotizarPorCategoriaVisitasCalculoOutputSchema,
    LiquidacionPorCategoriaVisitasIn,
    LiquidacionPorCategoriaVisitasDatosIn,
    LiquidacionPorCategoriaVisitasTarifaIn,
)


class LiquidacionPorCategoriaVisitasPresenter:
    """
    Presenter reutilizable para cualquier especialidad basada en cálculo por Visitas.
    """

    @staticmethod
    def present_tarifas_vigentes(
        tarifas: list[TarifaPorCategoriaVisitas],
        uit_vigente: UIT,
    ) -> TarifasVigentesPorCategoriaVisitasOutputSchema:
        """Transforms vigente models to Visitas vigentes output schema."""
        tarifas_out = []
        for tarifa in tarifas:
            costo = float(tarifa.porcentaje_uit) * float(uit_vigente.valor)
            tarifas_out.append(
                TarifaVigenteVisitasDatos(
                    id=tarifa.id,
                    costo_por_visita=costo,
                    categoria=tarifa.categoria_visitas,
                )
            )

        return TarifasVigentesPorCategoriaVisitasOutputSchema(
            tarifas=tarifas_out,
        )

    @staticmethod
    def present_cotizacion(result: CotizacionVisitasResult) -> CotizarPorCategoriaVisitasOutputSchema:
        """Transforms domain cotizacion result to Visitas cotizar output schema."""
        entrada = LiquidacionPorCategoriaVisitasIn(
            datos=LiquidacionPorCategoriaVisitasDatosIn(
                cantidad_visitas=result.cantidad_visitas,
                categoria=result.categoria,
            ),
            tarifa=LiquidacionPorCategoriaVisitasTarifaIn(tarifa_visitas_id=uuid.UUID(result.tarifa_id)),
        )

        tarifa = CotizarPorCategoriaVisitasTarifaOut(
            id=uuid.UUID(result.tarifa_id),
            costo_por_visita=result.costo_por_visita,
        )

        from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import VariablesFinancierasBasicasOut
        
        variables_financieras = VariablesFinancierasBasicasOut(
            igv=result.igv,
            uit=result.uit,
        )

        datos = CotizarPorCategoriaVisitasDatosOutputSchema(
            entrada=entrada,
            tarifa=tarifa,
            variables_financieras=variables_financieras,
        )

        calculo = CotizarPorCategoriaVisitasCalculoOutputSchema(
            monto_bruto=result.monto_bruto,
            subtotal=result.subtotal,
            total=result.total,
        )

        return CotizarPorCategoriaVisitasOutputSchema(
            datos=datos,
            calculo=calculo,
        )
