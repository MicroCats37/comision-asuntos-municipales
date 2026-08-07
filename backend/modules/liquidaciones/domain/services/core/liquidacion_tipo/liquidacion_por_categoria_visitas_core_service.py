"""
Core Service para el motor de Liquidación por Categoría de Visitas.
Maneja la lógica matemática y la persistencia de la tabla de Tipo.
"""
from typing import Optional
from decimal import Decimal
from injector import inject
from pydantic import BaseModel

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.finanzas.domain.models.impuestos import UIT, IGV
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_visitas_data import (
    LiquidacionTipoVisitasData,
)


class CotizacionVisitasResult(BaseModel):
    cantidad_visitas: int
    categoria: str
    tarifa_id: str
    porcentaje_uit: float
    monto_bruto: float
    subtotal: float
    total: float


class LiquidacionPorCategoriaVisitasCoreService:
    @inject
    def __init__(self):
        pass

    def get_tarifas_vigentes(self) -> list[TarifaPorCategoriaVisitas]:
        """Obtiene todas las tarifas vigentes para la categoría de visitas."""
        return list(TarifaPorCategoriaVisitas.objects.filter(vigente=True))

    def get_tarifa_por_id(self, tarifa_id: str) -> TarifaPorCategoriaVisitas:
        """Busca y retorna una tarifa específica por ID."""
        return TarifaPorCategoriaVisitas.objects.get(id=tarifa_id)

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
    ) -> CotizacionVisitasResult:
        try:
            tarifa = self.get_tarifa_por_id(tarifa_visitas_id)
        except TarifaPorCategoriaVisitas.DoesNotExist:
            from ninja.errors import HttpError
            raise HttpError(400, f"No se encontró una tarifa válida para ID {tarifa_visitas_id}")
            
        subtotal = self.calcular_subtotal_visitas(cantidad_visitas, tarifa, uit_vigente)
        total = subtotal
        
        return CotizacionVisitasResult(
            cantidad_visitas=cantidad_visitas,
            categoria=tarifa.categoria,
            tarifa_id=str(tarifa.id),
            porcentaje_uit=float(tarifa.porcentaje_uit),
            monto_bruto=float(subtotal),
            subtotal=float(subtotal),
            total=float(subtotal),
        )

    def crear_liquidacion_tipo_visitas(
        self,
        liquidacion_general: LiquidacionGeneral,
        data: LiquidacionTipoVisitasData,
    ) -> LiquidacionPorCategoriaVisitas:
        """
        Guarda la instancia de LiquidacionPorCategoriaVisitas (El motor de Tipo).
        NOTA: No lleva @transaction.atomic porque eso lo controla el Flujo.
        """
        tarifa = self.get_tarifa_por_id(data.tarifa.tarifa_visitas_id)
        
        liquidacion_visitas = LiquidacionPorCategoriaVisitas.objects.create(
            liquidacion_general=liquidacion_general,
            cantidad_visitas=data.datos.cantidad_visitas,
            porcentaje_uit=tarifa.porcentaje_uit,
            categoria=data.datos.categoria,
            tarifa_aplicada=tarifa,
        )
        return liquidacion_visitas
