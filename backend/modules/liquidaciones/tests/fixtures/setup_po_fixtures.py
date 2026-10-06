"""
Setup fixtures for PO (PorcentajeObra) motor — edilaciones, taludes, impacto vial.

Exposes a po_base_setup fixture that aggregates all base dependencies.
Tests can request this fixture and access its attributes (all are proper fixtures
themselves so they can also be requested individually).

Usage:
    def test_something(po_base_setup, make_payload_po):
        client = po_base_setup['auth_client']
        municipalidad = po_base_setup['municipalidad']
        ...

Or request individual fixtures alongside po_base_setup:
    def test_something(po_base_setup, auth_client, municipalidad, ...):
        # All the individual fixtures are still available
        ...
"""
import pytest


@pytest.fixture
def po_base_setup(
    db,
    auth_client,
    municipalidad,
    ubigeo_distrito,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidades_disponibles_edificacion,
    derecho_porcentaje_vigente,
):
    """Composite setup: all base fixtures for PO (Edificaciones/Taludes/Impacto Vial) tests.

    Returns a dict with references to all created objects so tests can build payloads.
    Individual fixtures are still requestable separately.
    """
    return {
        "auth_client": auth_client,
        "municipalidad": municipalidad,
        "ubigeo_distrito": ubigeo_distrito,
        "igv_vigente": igv_vigente,
        "uit_vigente": uit_vigente,
        "tarifa_porcentaje_obra_estructuras": tarifa_porcentaje_obra_estructuras,
        "especialidades_disponibles": especialidades_disponibles_edificacion,
        "derecho_porcentaje_vigente": derecho_porcentaje_vigente,
    }
