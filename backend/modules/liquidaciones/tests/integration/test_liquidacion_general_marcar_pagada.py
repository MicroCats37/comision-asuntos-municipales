"""
Integration tests for LiquidacionGeneral POST /{id}/marcar-pagada endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- PENDIENTE -> PAGADA transition
- PAGADA -> PAGADA idempotent success (no error)
- Output includes estado=PAGADA
- PATCH blocked after marking PAGADA

Fixtures are shared via conftest.py (tests/conftest.py).
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.constants import EstadoLiquidacion


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture
def liquidacion_pendiente(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
    tipo_edificacion,
):
    """
    Create a persisted LiquidacionGeneral in PENDIENTE state for testing
    the marcar-pagada endpoint.
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PAGAR-001",
        observacion="Test liquidation for marcar-pagada",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    edif = LiquidacionEdificacion.objects.create(
        liquidacion=lg,
        numero=1,
    )

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )

    return lg


@pytest.fixture
def liquidacion_pagada(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
    tipo_edificacion,
):
    """
    Create a persisted LiquidacionGeneral already in PAGADA state for testing
    idempotency.
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PAGADA-IDEM-001",
        observacion="Test liquidation already PAGADA",
        estado=EstadoLiquidacion.PAGADA,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    edif = LiquidacionEdificacion.objects.create(
        liquidacion=lg,
        numero=1,
    )

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )

    return lg


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_marcar_pagada_returns_200(
    auth_client,
    liquidacion_pendiente,
):
    """
    POST /liquidaciones/generales/{liquidacion_id}/marcar-pagada
    returns 200 for valid liquidacion in PENDIENTE state.
    """
    liquidacion_id = liquidacion_pendiente.id
    response = auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_marcar_pagada_transitions_estado_to_pagada(
    auth_client,
    liquidacion_pendiente,
):
    """
    After calling marcar-pagada, the liquidacion estado is PAGADA.
    """
    liquidacion_id = liquidacion_pendiente.id

    # Verify initial state
    lg_before = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg_before.estado == EstadoLiquidacion.PENDIENTE

    # Call endpoint
    response = auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")
    assert response.status_code == 200

    # Verify state changed
    lg_after = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg_after.estado == EstadoLiquidacion.PAGADA


@pytest.mark.django_db
def test_marcar_pagada_output_includes_estado_pagada(
    auth_client,
    liquidacion_pendiente,
):
    """
    The response output includes estado=PAGADA.
    """
    liquidacion_id = liquidacion_pendiente.id
    response = auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    assert response.status_code == 200
    data = response.json()
    result = data["data"]

    assert "estado" in result, "Response should include 'estado' field"
    assert result["estado"] == "PAGADA", \
        f"Expected estado='PAGADA', got '{result.get('estado')}'"


@pytest.mark.django_db
def test_marcar_pagada_idempotent_returns_200(
    auth_client,
    liquidacion_pagada,
):
    """
    Calling marcar-pagada on an already-PAGADA liquidacion returns 200 (idempotent).
    No error is raised.
    """
    liquidacion_id = liquidacion_pagada.id
    response = auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    assert response.status_code == 200, \
        f"Expected 200 (idempotent), got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_marcar_pagada_idempotent_keeps_estado_pagada(
    auth_client,
    liquidacion_pagada,
):
    """
    Calling marcar-pagada on an already-PAGADA liquidacion returns success
    and estado remains PAGADA.
    """
    liquidacion_id = liquidacion_pagada.id

    # Verify initial state
    lg_before = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg_before.estado == EstadoLiquidacion.PAGADA

    # Call endpoint (idempotent)
    response = auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")
    assert response.status_code == 200

    # Verify state unchanged
    lg_after = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg_after.estado == EstadoLiquidacion.PAGADA

    # Verify response output
    data = response.json()
    result = data["data"]
    assert result["estado"] == "PAGADA"


@pytest.mark.django_db
def test_marcar_pagada_returns_404_for_nonexistent(
    auth_client,
):
    """
    POST /liquidaciones/generales/{liquidacion_id}/marcar-pagada
    returns 404 for non-existent liquidacion ID.
    """
    import uuid
    fake_id = uuid.uuid4()
    response = auth_client.post(f"/liquidaciones/generales/{fake_id}/marcar-pagada")

    assert response.status_code == 404, \
        f"Expected 404 for non-existent ID, got {response.status_code}"


@pytest.mark.django_db
def test_patch_blocked_after_marking_pagada(
    auth_client,
    liquidacion_pendiente,
):
    """
    After marking a liquidacion as PAGADA, the PATCH endpoint returns 409.
    """
    liquidacion_id = liquidacion_pendiente.id

    # First, mark as PAGADA
    response = auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")
    assert response.status_code == 200

    # Verify state is PAGADA
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.estado == EstadoLiquidacion.PAGADA

    # Now try to PATCH (should be blocked)
    patch_payload = {
        "expediente": "EXP-MODIFIED-AFTER-PAGO",
    }
    patch_response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )

    assert patch_response.status_code == 409, \
        f"Expected 409 (Conflict) after marking PAGADA, got {patch_response.status_code}: {patch_response.content}"


@pytest.mark.django_db
def test_eliminar_liquidacion_marks_deleted_and_nulls_specific_numero(
    auth_client,
    liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/generales/{id}/eliminar marks the general row as
    eliminated and clears the specific liquidation number.
    """
    liquidacion_id = liquidacion_pendiente.id

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}/eliminar",
        json={"motivo": "Registro creado por error en prueba"},
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.eliminado is True
    assert lg.fecha_eliminacion is not None
    assert lg.motivo_eliminacion == "Registro creado por error en prueba"

    specific = LiquidacionEdificacion.objects.get(liquidacion=lg)
    assert specific.numero is None

    data = response.json()["data"]
    assert data["eliminado"] is True
    assert data["motivo_eliminacion"] == "Registro creado por error en prueba"
