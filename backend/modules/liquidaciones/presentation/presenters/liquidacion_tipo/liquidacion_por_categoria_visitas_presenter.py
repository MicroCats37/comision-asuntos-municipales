"""
LiquidacionPorCategoriaVisitasPresenter — Presenter reutilizable para cálculos de Visitas.
"""
import uuid
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorCategoriaVisitas,
)
from modules.finanzas.domain.models.impuestos import UIT
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionVisitasResult
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraCotizarContinuidadOut,
    LiquidacionInspeccionObraCotizarOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
    TarifasVigentesPorCategoriaVisitasOutputSchema,
    TarifaVigenteVisitasDatos,
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
        from decimal import Decimal
        tarifas_out = []
        for tarifa in tarifas:
            costo = tarifa.porcentaje_uit * uit_vigente.valor
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
    def present_cotizacion(result: CotizacionVisitasResult) -> LiquidacionInspeccionObraCotizarOutput:
        """Transforms domain cotizacion result to the IO cotizar output schema.

        Proyecta el ECO del modo (`modo_cotizacion`, siempre presente) y el
        bloque autoritativo de continuidad (`continuidad`, null en NORMAL). NO
        hace aritmética monetaria: todas las cifras vienen del servidor.

        NO consulta la base de datos (contrato api-wrapper-presenter §3).
        """
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

        continuidad = None
        if result.continuidad is not None:
            bloque = result.continuidad
            continuidad = LiquidacionInspeccionObraCotizarContinuidadOut(
                total_pagado_previa=bloque.total_pagado_previa,
                valor_completo_neto=bloque.valor_completo_neto,
                valor_completo_bruto=bloque.valor_completo_bruto,
                credito_neto=bloque.credito_neto,
                credito_bruto=bloque.credito_bruto,
                diferencia_neto=bloque.diferencia_neto,
                diferencia_bruto=bloque.diferencia_bruto,
                igv_porcentaje=bloque.igv_porcentaje,
            )

        return LiquidacionInspeccionObraCotizarOutput(
            datos=datos,
            calculo=calculo,
            modo_cotizacion=result.modo_cotizacion,
            continuidad=continuidad,
        )
