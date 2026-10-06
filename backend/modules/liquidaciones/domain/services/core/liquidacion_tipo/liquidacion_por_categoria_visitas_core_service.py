"""
Core Service para el motor de Liquidación por Categoría de Visitas.
Maneja la lógica matemática y la persistencia de la tabla de Tipo.
"""
from typing import Optional
from decimal import Decimal
from injector import inject

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.finanzas.domain.models.impuestos import UIT, IGV
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_visitas_data import (
    LiquidacionCategoriaVisitasData,
)


class LiquidacionPorCategoriaVisitasCoreService:
    @inject
    def __init__(self):
        pass

    def get_tarifas_vigentes(self) -> list[TarifaPorCategoriaVisitas]:
        """Obtiene todas las tarifas vigentes para la categoría de visitas."""
        bases = TarifaLiquidacionBase.objects.vigentes().filter(
            tipo_liquidacion__codigo=TipoLiquidacion.INSPECCION_OBRA
        )
        return list(
            TarifaPorCategoriaVisitas.objects.filter(
                tarifa_base__in=bases
            ).select_related("tarifa_base")
        )

    def get_tarifa_por_id(self, tarifa_id: str) -> Optional[TarifaPorCategoriaVisitas]:
        """Busca y retorna una tarifa específica por ID. Returns None if not found."""
        try:
            return TarifaPorCategoriaVisitas.objects.get(id=tarifa_id)
        except TarifaPorCategoriaVisitas.DoesNotExist:
            return None

    def calcular_subtotal_visitas(
        self,
        cantidad_visitas: int,
        tarifa: TarifaPorCategoriaVisitas,
        uit_vigente: UIT,
    ) -> Decimal:
        """
        Fórmula matemática para Visitas: cantidad_visitas * (porcentaje_uit * valor_uit)
        """
        costo_por_visita = tarifa.porcentaje_uit * Decimal(str(uit_vigente.valor))
        return Decimal(str(cantidad_visitas)) * costo_por_visita

    def calcular_cotizacion_visitas(
        self,
        cantidad_visitas: int,
        categoria: str,
        tarifa_visitas_id: str,
        uit_vigente: UIT,
        igv_vigente: "IGV",
    ) -> Optional["CotizacionVisitasResult"]:
        """
        Full calculation of Visitas quote including IGV.
        PURE computation - returns None if tariff not found.
        """
        from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import (
            CotizacionVisitasResult as CotizacionVisitasResultDTO,
        )
        tarifa = self.get_tarifa_por_id(tarifa_visitas_id)
        if not tarifa:
            return None

        subtotal = self.calcular_subtotal_visitas(cantidad_visitas, tarifa, uit_vigente)
        costo_por_visita = tarifa.porcentaje_uit * uit_vigente.valor
        igv_valor = igv_vigente.valor
        total = subtotal * (Decimal("1") + igv_valor)

        return CotizacionVisitasResultDTO(
            cantidad_visitas=cantidad_visitas,
            categoria=tarifa.categoria_visitas,
            costo_por_visita=costo_por_visita,
            tarifa_id=str(tarifa.id),
            monto_bruto=subtotal,
            subtotal=subtotal,
            total=total,
            uit={"id": str(uit_vigente.id), "valor": float(uit_vigente.valor)},
            igv={"id": str(igv_vigente.id), "valor": float(igv_vigente.valor)},
        )

    def crear_liquidacion_tipo_visitas(
        self,
        liquidacion_general: LiquidacionGeneral,
        data: LiquidacionCategoriaVisitasData,
    ) -> LiquidacionPorCategoriaVisitas:
        """
        Guarda la instancia de LiquidacionPorCategoriaVisitas (El motor de Tipo).
        NOTA: No lleva @transaction.atomic porque eso lo controla el Flujo.

        Null-tariff path (legacy/manual IO):
        - When tarifa_visitas_id is None and override totals are provided by caller,
          the flujo passes null categoria/porcentaje_uit.
        - This creates a LiquidacionPorCategoriaVisitas with null FK and null fields,
          which is valid for legacy records with CATEGORIA=0 or unmatched tariffs.
        """
        tarifa = None
        porcentaje_uit = None
        categoria = data.datos.categoria

        if data.tarifa and data.tarifa.tarifa_visitas_id:
            tarifa = self.get_tarifa_por_id(data.tarifa.tarifa_visitas_id)
            if tarifa:
                porcentaje_uit = tarifa.porcentaje_uit
                # Fall back to tariff's categoria if not provided in data
                if not categoria:
                    categoria = tarifa.categoria_visitas

        liquidacion_visitas = LiquidacionPorCategoriaVisitas.objects.create(
            liquidacion_general=liquidacion_general,
            cantidad_visitas=data.datos.cantidad_visitas,
            porcentaje_uit=porcentaje_uit,
            categoria=categoria,
            tarifa_aplicada=tarifa,
        )
        return liquidacion_visitas
