"""
Tipos fixtures — TipoLiquidacion for all liquidacion types.

Re-exports: tipo_edificacion, tipo_habilitacion_urbana, tipo_mecanica_suelos,
            tipo_impacto_vial, tipo_taludes, tipo_inspeccion_obra
"""
import pytest
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel


@pytest.fixture
def tipo_edificacion(db):
    """Get or create TipoLiquidacion for EDIFICACION."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="EDIFICACION", defaults={"nombre": "Edificaciones"})[0]


@pytest.fixture
def tipo_habilitacion_urbana(db):
    """Get or create TipoLiquidacion for HABILITACION_URBANA."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="HABILITACION_URBANA", defaults={"nombre": "Habilitación Urbana"})[0]


@pytest.fixture
def tipo_mecanica_suelos(db):
    """Get or create TipoLiquidacion for MECANICA_SUELOS."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="MECANICA_SUELOS", defaults={"nombre": "Mecánica de Suelos"})[0]


@pytest.fixture
def tipo_impacto_vial(db):
    """Get or create TipoLiquidacion for IMPACTO_VIAL."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="IMPACTO_VIAL", defaults={"nombre": "Impacto Vial"})[0]


@pytest.fixture
def tipo_taludes(db):
    """Get or create TipoLiquidacion for TALUDES."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="TALUDES", defaults={"nombre": "Taludes"})[0]


@pytest.fixture
def tipo_inspeccion_obra(db):
    """Get or create TipoLiquidacion for INSPECCION_OBRA."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="INSPECCION_OBRA", defaults={"nombre": "Inspección de Obra"})[0]
