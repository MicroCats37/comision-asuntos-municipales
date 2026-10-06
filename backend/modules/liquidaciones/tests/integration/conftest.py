"""
conftest.py for liquidaciones integration tests.

Loads fixtures from the fixtures/ subpackage so pytest can discover them.
This conftest.py is in tests/integration/ which is a proper conftest discovery path.

Usage:
    All fixtures from fixtures/* are automatically available.
    For factories, import directly:
        from modules.liquidaciones.tests.fixtures.factories import make_payload_po
"""
# Import all fixture modules to register their @pytest.fixture definitions with pytest.
# pytest discovers fixtures defined in conftest.py and its imported modules.
from modules.liquidaciones.tests.fixtures import (
    usuarios_fixtures,
    ubigeo_fixtures,
    finanzas_fixtures,
    tipos_fixtures,
    tarifas_po_fixtures,
    tarifas_m2_fixtures,
    tarifas_io_fixtures,
    setup_po_fixtures,
    setup_m2_fixtures,
    setup_io_fixtures,
)
