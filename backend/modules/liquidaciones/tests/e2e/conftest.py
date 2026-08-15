"""
conftest.py for liquidaciones e2e tests.

Loads fixtures from the fixtures/ subpackage so pytest can discover them.
"""
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
