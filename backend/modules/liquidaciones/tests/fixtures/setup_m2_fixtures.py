"""
Setup fixtures for M2 (Por Metro Cuadrado) motor — habilitación urbana, mecánica de suelos.

Usage:
    def test_something(m2_base_setup, make_payload_m2):
        client = m2_base_setup['auth_client']
        ...
"""
import pytest


@pytest.fixture
def m2_base_setup(
    db,
    auth_client,
    municipalidad,
    ubigeo_distrito,
    igv_vigente,
    uit_vigente,
    tarifa_m2_hu,
    tarifa_liquidacion_base_hu,
    derecho_m2_vigente,
):
    """Composite setup: all base fixtures for M2 (HU/MS) tests.

    Returns a dict with references to all created objects so tests can build payloads.
    """
    return {
        "auth_client": auth_client,
        "municipalidad": municipalidad,
        "ubigeo_distrito": ubigeo_distrito,
        "igv_vigente": igv_vigente,
        "uit_vigente": uit_vigente,
        "tarifa_m2_hu": tarifa_m2_hu,
        "tarifa_liquidacion_base_hu": tarifa_liquidacion_base_hu,
        "derecho_m2_vigente": derecho_m2_vigente,
    }
