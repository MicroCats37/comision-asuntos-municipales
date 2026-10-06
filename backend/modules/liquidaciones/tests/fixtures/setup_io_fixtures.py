"""
Setup fixtures for IO (Inspección de Obra) motor.

Usage:
    def test_something(io_base_setup, make_payload_io):
        client = io_base_setup['auth_client']
        ...
"""
import pytest


@pytest.fixture
def io_base_setup(
    db,
    auth_client,
    municipalidad,
    ubigeo_distrito,
    igv_vigente,
    uit_vigente,
    tarifa_visitas_io,
    tarifa_liquidacion_base_io,
):
    """Composite setup: all base fixtures for IO tests.

    Returns a dict with references to all created objects so tests can build payloads.
    """
    return {
        "auth_client": auth_client,
        "municipalidad": municipalidad,
        "ubigeo_distrito": ubigeo_distrito,
        "igv_vigente": igv_vigente,
        "uit_vigente": uit_vigente,
        "tarifa_visitas_io": tarifa_visitas_io,
        "tarifa_liquidacion_base_io": tarifa_liquidacion_base_io,
    }
