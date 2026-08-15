"""
Finanzas fixtures — IGV and UIT vigente.

Re-exports: igv_vigente, uit_vigente
"""
import pytest
from decimal import Decimal
from datetime import date
from modules.finanzas.domain.models.impuestos import UIT, IGV


@pytest.fixture
def igv_vigente(db):
    """Create an IGV vigente for testing."""
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def uit_vigente(db):
    """Create a UIT vigente for testing."""
    return UIT.objects.create(
        valor=Decimal("5150.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
