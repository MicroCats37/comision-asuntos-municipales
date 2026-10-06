"""
Tarifas IO (Inspección de Obra) fixtures.

Re-exports: tarifa_liquidacion_base_io, tarifa_visitas_io
"""
import pytest
from decimal import Decimal
from datetime import date
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
)


@pytest.fixture
def tarifa_liquidacion_base_io(db, tipo_inspeccion_obra):
    """Create a TarifaLiquidacionBase for Inspección de Obra."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_visitas_io(db, tarifa_liquidacion_base_io):
    """Create a TarifaPorCategoriaVisitas for Inspección de Obra testing."""
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_liquidacion_base_io,
        porcentaje_uit=Decimal("0.05"),  # 5% of UIT
        categoria_visitas="INSPECCION",
    )
