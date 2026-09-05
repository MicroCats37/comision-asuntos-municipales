"""
LiquidacionPorMetroCuadradoPresenter — Presenter reutilizable para cálculos M2.

Mapea tarifas vigentes y cotizaciones M2 a sus schemas de salida.
Consumido por cualquier controller de especialidad que use M2 (HU, Mecánica de Suelos, etc.)
NO business logic.
"""
import uuid
from decimal import Decimal
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import CotizacionM2Result
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    TarifasVigentesPorMetroCuadradoOutputSchema,
    TarifaVigentePorMetroCuadradoWrapper,
    TarifaVigentePorMetroCuadradoDatos,
    DerechoVigentePorMetroCuadradoWrapper,
    DerechoVigentePorMetroCuadradoDatos,
    CotizarPorMetroCuadradoOutputSchema,
    CotizarPorMetroCuadradoDatosOutputSchema,
    CotizarPorMetroCuadradoTarifaOut,
    CotizarPorMetroCuadradoDerechoOut,
    CotizarPorMetroCuadradoCalculoOutputSchema,
    LiquidacionPorMetroCuadradoIn,
    LiquidacionPorMetroCuadradoDatosIn,
    LiquidacionPorMetroCuadradoTarifaIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import VariablesFinancierasNulasOut


class LiquidacionPorMetroCuadradoPresenter:
    """
    Presenter reutilizable para cualquier especialidad basada en cálculo M2.
    """

    @staticmethod
    def present_tarifas_vigentes(
        tarifa: TarifaPorMetroCuadrado | None,
        derecho: DerechoPorMetroCuadrado | None,
    ) -> TarifasVigentesPorMetroCuadradoOutputSchema:
        """Transforms vigente models to M2 vigentes output schema."""
        if tarifa is not None:
            tarifa_datos = TarifaVigentePorMetroCuadradoDatos(
                id=tarifa.id,
                costo_por_m2=tarifa.costo_por_m2,
            )
            tarifa_vigente = TarifaVigentePorMetroCuadradoWrapper(datos=tarifa_datos)
        else:
            tarifa_vigente = TarifaVigentePorMetroCuadradoWrapper(
                datos=TarifaVigentePorMetroCuadradoDatos(
                    id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                    costo_por_m2=Decimal("0"),
                )
            )

        if derecho is not None:
            derecho_datos = DerechoVigentePorMetroCuadradoDatos(
                id=derecho.id,
                derecho_minimo=derecho.derecho_minimo,
                derecho_maximo=derecho.derecho_maximo,
            )
            derecho_vigente = DerechoVigentePorMetroCuadradoWrapper(datos=derecho_datos)
        else:
            derecho_vigente = DerechoVigentePorMetroCuadradoWrapper(
                datos=DerechoVigentePorMetroCuadradoDatos(
                    id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                    derecho_minimo=Decimal("0"),
                    derecho_maximo=Decimal("0"),
                )
            )

        return TarifasVigentesPorMetroCuadradoOutputSchema(
            tarifa_vigente=tarifa_vigente,
            derecho_vigente=derecho_vigente,
        )

    @staticmethod
    def present_cotizacion(result: CotizacionM2Result) -> CotizarPorMetroCuadradoOutputSchema:
        """Transforms domain cotizacion result to M2 cotizar output schema."""
        entrada = LiquidacionPorMetroCuadradoIn(
            datos=LiquidacionPorMetroCuadradoDatosIn(area_solicitada=result.area_m2),
            tarifa=LiquidacionPorMetroCuadradoTarifaIn(tarifa_m2_id=uuid.UUID(result.tarifa_id)),
        )

        tarifa = CotizarPorMetroCuadradoTarifaOut(
            id=uuid.UUID(result.tarifa_id),
            costo_por_m2=result.costo_por_m2,
        )

        derecho = CotizarPorMetroCuadradoDerechoOut(
            id=uuid.UUID(result.derecho_id),
            derecho_minimo=result.minimo,
            derecho_maximo=result.maximo if result.maximo is not None else Decimal("0"),
        )

        variables = VariablesFinancierasNulasOut(igv=None, uit=None)

        datos = CotizarPorMetroCuadradoDatosOutputSchema(
            entrada=entrada,
            tarifa=tarifa,
            derecho=derecho,
            variables_financieras=variables,
        )

        calculo = CotizarPorMetroCuadradoCalculoOutputSchema(
            monto_bruto=result.monto_bruto,
            subtotal=result.subtotal,
            total=result.total,
        )

        return CotizarPorMetroCuadradoOutputSchema(
            datos=datos,
            calculo=calculo,
        )
