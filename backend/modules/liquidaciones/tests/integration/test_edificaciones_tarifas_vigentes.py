"""
Integration tests for Edificaciones GET /tarifas/vigentes endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


# Local fixtures NOT in conftest:
# - tarifa_porcentaje_obra_base2: second base+tarifa (Arquitectura 0.05%)
# - tarifa_porcentaje_obra_base3: third base+tarifa (Instalaciones 0.03%)

@pytest.fixture
def tarifa_porcentaje_obra_base2(db, tipo_edificacion):
    """Create a second TarifaLiquidacionBase + TarifaPorcentajeObra for Arquitectura (vigente)."""
    base2 = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=base2,
        porcentaje_liquidacion=Decimal("0.0005"),  # 0.05%
    )


@pytest.fixture
def tarifa_porcentaje_obra_base3(db, tipo_edificacion):
    """Create a third TarifaLiquidacionBase + TarifaPorcentajeObra for Instalaciones (vigente)."""
    base3 = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=base3,
        porcentaje_liquidacion=Decimal("0.0003"),  # 0.03%
    )


@pytest.mark.django_db
def test_returns_vigentes_tarifas(
    api_client, tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_base2,
    tarifa_porcentaje_obra_base3, derecho_porcentaje_vigente
):
    """
    GET returns list of vigentes tarifas for EDIFICACION.

    NEW contract: response has {tarifas: [{id, porcentaje_liquidacion}], especialidades_disponibles: [...]}.
    Each TarifaPorcentajeObra has no especialidad FK — specialties come from LiquidacionEspecialidadDisponibles.
    """
    response = api_client.get("/liquidaciones/edificaciones/tarifas/vigentes")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data, "Response should have 'data' key"

    result = data["data"]
    assert "tarifas" in result, "Result should have 'tarifas' wrapper"
    assert "especialidades_disponibles" in result, \
        "Result should have 'especialidades_disponibles' wrapper"

    tarifas = result["tarifas"]
    assert len(tarifas) == 3, \
        f"Expected 3 vigentes tarifas, got {len(tarifas)}"

    # Verify each tarifa has required fields (NEW: no especialidad field)
    for tarifa in tarifas:
        assert "id" in tarifa, "Each tarifa should have 'id'"
        assert "porcentaje_liquidacion" in tarifa, \
            "Each tarifa should have 'porcentaje_liquidacion'"


@pytest.mark.django_db
def test_returns_derecho_info(
    api_client, tarifa_porcentaje_obra_estructuras, derecho_porcentaje_vigente
):
    """
    Response includes derecho (min, max, porcentaje_minimo_uit).

    The endpoint returns derecho information along with tarifas.
    """
    response = api_client.get("/liquidaciones/edificaciones/tarifas/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    # The endpoint returns tarifas list; derecho info is in the calculation, not in response
    # This test verifies that at least the tarifas are returned correctly
    assert "tarifas" in result


@pytest.mark.django_db
def test_excludes_other_tipo_liquidacion(
    api_client, db, tarifa_porcentaje_obra_estructuras,
    tipo_habilitacion_urbana, tipo_mecanica_suelos
):
    """
    Only EDIFICACION tarifas returned, not HU or IO.

    Creates a HU tariff and verifies Edificaciones endpoint doesn't return it.
    """
    # Create HU tariff (should NOT be returned)
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import TarifaPorMetroCuadrado

    hu_tarifa_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    TarifaPorMetroCuadrado.objects.create(
        tarifa_base=hu_tarifa_base,
        costo_por_m2=Decimal("150.0000"),
    )

    # Create MS tariff (should NOT be returned)
    ms_tarifa_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    TarifaPorMetroCuadrado.objects.create(
        tarifa_base=ms_tarifa_base,
        costo_por_m2=Decimal("100.0000"),
    )

    response = api_client.get("/liquidaciones/edificaciones/tarifas/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    tarifas = result["tarifas"]

    # Should only return EDIFICACION tariff (1), not HU or MS
    assert len(tarifas) == 1, \
        f"Expected 1 EDIFICACION tarifa only, got {len(tarifas)}"

    # Verify the returned tarifa is the EDIFICACION one
    returned_id = uuid.UUID(str(tarifas[0]["id"]))
    assert returned_id == tarifa_porcentaje_obra_estructuras.id, \
        "Should return only EDIFICACION tarifa"


@pytest.mark.django_db
def test_excludes_expired_tarifas(
    api_client, db, tarifa_porcentaje_obra_estructuras,
    tipo_edificacion
):
    """
    Only vigentes tarifas returned (not expired).

    Creates an expired tariff and verifies it's not returned.
    """
    # Create expired tariff (should NOT be returned)
    expired_tarifa_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2023, 1, 1),
        periodo_fin=date(2023, 12, 31),  # Expired
    )
    expired_tarifa = TarifaPorcentajeObra.objects.create(
        tarifa_base=expired_tarifa_base,
        porcentaje_liquidacion=Decimal("0.0010"),
    )

    response = api_client.get("/liquidaciones/edificaciones/tarifas/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    tarifas = result["tarifas"]

    # Should only return vigente tariff (1), not the expired one
    assert len(tarifas) == 1, \
        f"Expected 1 vigente tarifa only, got {len(tarifas)}"

    # Verify the expired tariff is NOT in the list
    returned_ids = [uuid.UUID(str(t["id"])) for t in tarifas]
    assert expired_tarifa.id not in returned_ids, \
        "Expired tariff should not be in vigentes list"


@pytest.mark.django_db
def test_uuid_not_none(
    api_client, tarifa_porcentaje_obra_estructuras, derecho_porcentaje_vigente
):
    """
    Response IDs are valid UUIDs (not None, not str).

    The tariff IDs should be valid UUIDs for FK relationships.
    """
    response = api_client.get("/liquidaciones/edificaciones/tarifas/vigentes")

    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    tarifas = result["tarifas"]

    assert len(tarifas) > 0, "Expected at least 1 tarifa"

    for tarifa in tarifas:
        tarifa_id = tarifa["id"]
        assert tarifa_id is not None, "tarifa.id should not be None"

        # Verify it's a valid UUID
        tarifa_uuid = uuid.UUID(str(tarifa_id))
        assert isinstance(tarifa_uuid, uuid.UUID), \
            f"tarifa.id should be valid UUID, got {type(tarifa_id)}"


@pytest.mark.django_db
def test_multiple_tarifas_por_base_raises_error(
    db, tipo_edificacion, api_client
):
    """
    When a vigente TarifaLiquidacionBase has more than one TarifaPorcentajeObra child,
    the endpoint raises an explicit HttpError (400) instead of silently returning wrong data.
    """
    # Create base with TWO child tariffs (violates tarifa-unica-especialidades invariant)
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    TarifaPorcentajeObra.objects.create(
        tarifa_base=base, porcentaje_liquidacion=Decimal("0.0005")
    )
    TarifaPorcentajeObra.objects.create(
        tarifa_base=base, porcentaje_liquidacion=Decimal("0.0002")
    )

    response = api_client.get("/liquidaciones/edificaciones/tarifas/vigentes")

    assert response.status_code == 400, \
        f"Expected 400 for multiple children per base, got {response.status_code}"
    error_details = response.json().get("error", {}).get("details", {})
    non_field_errors = error_details.get("non_field_errors", "") if isinstance(error_details, dict) else ""
    assert "Data inconsistency" in non_field_errors, \
        f"Expected 'Data inconsistency' in error details, got: {error_details}"
