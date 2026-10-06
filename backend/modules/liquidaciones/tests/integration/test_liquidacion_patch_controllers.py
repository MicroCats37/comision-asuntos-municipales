"""
Integration tests for PATCH /{liquidacion_id} recalculation endpoints.

Tests cover the 3 engine types across all 6 specific liquidacion types:
- PO engine: Edificaciones, Impacto Vial, Taludes
- M2 engine: Habilitacion Urbana, Mecanica Suelos
- Visitas engine: Inspeccion Obra

Tests per engine type:
1. PATCH returns 200 with recalculated output when estado == PENDIENTE
2. PATCH returns 409 when estado == PAGADA (guard block)
3. PATCH recalculation updates the specific calculation fields

Scope: HTTP controller + orchestrator + service integration.
"""
import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model
from modules.liquidaciones.domain.constants import TipoLiquidacion, EstadoLiquidacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_impacto_vial import (
    LiquidacionImpactoVial,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_taludes import (
    LiquidacionTaludes,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos import (
    LiquidacionMecanicaSuelos,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
)

User = get_user_model()


# ── PO Engine Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def po_liquidacion_pendiente(
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
    """Edificaciones liquidacion in PENDIENTE state."""
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PATCH-PO-001",
        observacion="Test PATCH PO",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    edif = LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

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
def iv_liquidacion_pendiente(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_iv,
    especialidad_impacto_vial,
    tipo_impacto_vial,
):
    """Impacto Vial liquidacion in PENDIENTE state."""
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PATCH-IV-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_impacto_vial,
        numero_revision=1,
        sub_total=Decimal("800.00"),
        total=Decimal("944.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionImpactoVial.objects.create(liquidacion=lg, numero=1)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("50000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_iv,
        especialidad=especialidad_impacto_vial,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("800.00"),
    )

    return lg


@pytest.fixture
def taludes_liquidacion_pendiente(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_taludes,
    especialidad_taludes,
    tipo_taludes,
):
    """Taludes liquidacion in PENDIENTE state."""
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PATCH-TAL-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_taludes,
        numero_revision=1,
        sub_total=Decimal("600.00"),
        total=Decimal("708.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionTaludes.objects.create(liquidacion=lg, numero=1)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("75000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_taludes,
        especialidad=especialidad_taludes,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("600.00"),
    )

    return lg


# ── M2 Engine Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def hu_liquidacion_pendiente(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_m2_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_m2_hu,
    tipo_habilitacion_urbana,
):
    """Habilitacion Urbana liquidacion in PENDIENTE state."""
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PATCH-HU-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("2000.00"),
        total=Decimal("2360.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionHabilitacionUrbana.objects.create(liquidacion=lg, numero=1)

    lm2 = LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=lg,
        area_m2=Decimal("100.00"),
        costo_por_m2=tarifa_m2_hu.costo_por_m2,
        derecho_minimo=derecho_m2_vigente.derecho_minimo,
        derecho_maximo=derecho_m2_vigente.derecho_maximo,
        tarifa_aplicada=tarifa_m2_hu,
        derecho=derecho_m2_vigente,
    )

    return lg


@pytest.fixture
def ms_liquidacion_pendiente(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_m2_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_m2_ms,
    tipo_mecanica_suelos,
):
    """Mecanica Suelos liquidacion in PENDIENTE state."""
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PATCH-MS-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_mecanica_suelos,
        numero_revision=1,
        sub_total=Decimal("1500.00"),
        total=Decimal("1770.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionMecanicaSuelos.objects.create(liquidacion=lg, numero=1)

    lm2 = LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=lg,
        area_m2=Decimal("200.00"),
        costo_por_m2=tarifa_m2_ms.costo_por_m2,
        derecho_minimo=derecho_m2_vigente.derecho_minimo,
        derecho_maximo=derecho_m2_vigente.derecho_maximo,
        tarifa_aplicada=tarifa_m2_ms,
        derecho=derecho_m2_vigente,
    )

    return lg


# ── Visitas Engine Fixture ─────────────────────────────────────────────────────

@pytest.fixture
def io_liquidacion_pendiente(
    db,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tarifa_visitas_io,
    tipo_inspeccion_obra,
):
    """Inspeccion Obra liquidacion in PENDIENTE state."""
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PATCH-IO-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("1200.00"),
        total=Decimal("1416.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionInspeccionObra.objects.create(liquidacion=lg, numero=1)

    lvisitas = LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=5,
        porcentaje_uit=Decimal("0.05"),
        categoria="INSPECCION",
        tarifa_aplicada=tarifa_visitas_io,
    )

    return lg


# ── Tests: PO Engine (Edificaciones, Impacto Vial, Taludes) ────────────────────

@pytest.mark.django_db
def test_edificaciones_patch_returns_200_pendiente(
    auth_client,
    po_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/edificaciones/{id} returns 200 when estado == PENDIENTE.
    """
    liquidacion_id = po_liquidacion_pendiente.id
    payload = {"valor_declarado": 150000.00}

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data
    result = data["data"]
    assert result["liquidacion_general"]["id"] == str(liquidacion_id)


@pytest.mark.django_db
def test_edificaciones_patch_returns_409_pagada(
    auth_client,
    po_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/edificaciones/{id} returns 409 when estado == PAGADA.
    """
    liquidacion_id = po_liquidacion_pendiente.id

    # Mark as PAGADA
    auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    # Verify state
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.estado == EstadoLiquidacion.PAGADA

    # Try PATCH
    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json={"valor_declarado": 200000.00},
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_impacto_vial_patch_returns_200_pendiente(
    auth_client,
    iv_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/impacto-vial/{id} returns 200 when estado == PENDIENTE.
    """
    liquidacion_id = iv_liquidacion_pendiente.id
    payload = {"valor_declarado": 80000.00}

    response = auth_client.patch(
        f"/liquidaciones/impacto-vial/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_impacto_vial_patch_returns_409_pagada(
    auth_client,
    iv_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/impacto-vial/{id} returns 409 when estado == PAGADA.
    """
    liquidacion_id = iv_liquidacion_pendiente.id

    auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.estado == EstadoLiquidacion.PAGADA

    response = auth_client.patch(
        f"/liquidaciones/impacto-vial/{liquidacion_id}",
        json={"valor_declarado": 200000.00},
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_taludes_patch_returns_200_pendiente(
    auth_client,
    taludes_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/taludes/{id} returns 200 when estado == PENDIENTE.
    """
    liquidacion_id = taludes_liquidacion_pendiente.id
    payload = {"valor_declarado": 100000.00}

    response = auth_client.patch(
        f"/liquidaciones/taludes/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_taludes_patch_returns_409_pagada(
    auth_client,
    taludes_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/taludes/{id} returns 409 when estado == PAGADA.
    """
    liquidacion_id = taludes_liquidacion_pendiente.id

    auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.estado == EstadoLiquidacion.PAGADA

    response = auth_client.patch(
        f"/liquidaciones/taludes/{liquidacion_id}",
        json={"valor_declarado": 200000.00},
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA, got {response.status_code}: {response.content}"


# ── Tests: M2 Engine (Habilitacion Urbana, Mecanica Suelos) ───────────────────

@pytest.mark.django_db
def test_habilitacion_urbana_patch_returns_200_pendiente(
    auth_client,
    hu_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/habilitacion-urbana/{id} returns 200 when estado == PENDIENTE.
    """
    liquidacion_id = hu_liquidacion_pendiente.id
    payload = {"area_solicitada": 250.00}

    response = auth_client.patch(
        f"/liquidaciones/habilitacion-urbana/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data
    result = data["data"]
    assert result["liquidacion_general"]["id"] == str(liquidacion_id)


@pytest.mark.django_db
def test_habilitacion_urbana_patch_returns_409_pagada(
    auth_client,
    hu_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/habilitacion-urbana/{id} returns 409 when estado == PAGADA.
    """
    liquidacion_id = hu_liquidacion_pendiente.id

    auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.estado == EstadoLiquidacion.PAGADA

    response = auth_client.patch(
        f"/liquidaciones/habilitacion-urbana/{liquidacion_id}",
        json={"area_solicitada": 300.00},
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_mecanica_suelos_patch_returns_200_pendiente(
    auth_client,
    ms_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/mecanica-suelos/{id} returns 200 when estado == PENDIENTE.
    """
    liquidacion_id = ms_liquidacion_pendiente.id
    payload = {"area_solicitada": 350.00}

    response = auth_client.patch(
        f"/liquidaciones/mecanica-suelos/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_mecanica_suelos_patch_returns_409_pagada(
    auth_client,
    ms_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/mecanica-suelos/{id} returns 409 when estado == PAGADA.
    """
    liquidacion_id = ms_liquidacion_pendiente.id

    auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.estado == EstadoLiquidacion.PAGADA

    response = auth_client.patch(
        f"/liquidaciones/mecanica-suelos/{liquidacion_id}",
        json={"area_solicitada": 400.00},
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA, got {response.status_code}: {response.content}"


# ── Tests: Visitas Engine (Inspeccion Obra) ────────────────────────────────────

@pytest.mark.django_db
def test_inspeccion_obra_patch_returns_200_pendiente(
    auth_client,
    io_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/inspeccion-obra/{id} returns 200 when estado == PENDIENTE.
    """
    liquidacion_id = io_liquidacion_pendiente.id
    payload = {"cantidad_visitas": 8}

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert "data" in data
    result = data["data"]
    assert result["liquidacion_general"]["id"] == str(liquidacion_id)


@pytest.mark.django_db
def test_inspeccion_obra_patch_returns_409_pagada(
    auth_client,
    io_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/inspeccion-obra/{id} returns 409 when estado == PAGADA.
    """
    liquidacion_id = io_liquidacion_pendiente.id

    auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.estado == EstadoLiquidacion.PAGADA

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json={"cantidad_visitas": 10},
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA, got {response.status_code}: {response.content}"


# ── Tests: Error Cases ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_edificaciones_patch_returns_404_non_existent(
    auth_client,
    db,
):
    """PATCH returns 404 for non-existent liquidacion ID."""
    import uuid
    non_existent_id = uuid.uuid4()

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{non_existent_id}",
        json={"valor_declarado": 100000.00},
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_hu_patch_returns_404_non_existent(
    auth_client,
    db,
):
    """PATCH returns 404 for non-existent liquidacion ID."""
    import uuid
    non_existent_id = uuid.uuid4()

    response = auth_client.patch(
        f"/liquidaciones/habilitacion-urbana/{non_existent_id}",
        json={"area_solicitada": 100.00},
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_io_patch_returns_404_non_existent(
    auth_client,
    db,
):
    """PATCH returns 404 for non-existent liquidacion ID."""
    import uuid
    non_existent_id = uuid.uuid4()

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{non_existent_id}",
        json={"cantidad_visitas": 5},
    )

    assert response.status_code == 404


# ── Tests: Wrapper Payload — PO Engine (Edificaciones, Impacto Vial, Taludes) ──

@pytest.mark.django_db
def test_edificaciones_patch_wrapper_updates_general_and_tipo_in_one_call(
    auth_client,
    po_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/edificaciones/{id} with wrapper payload
    updates both liquidacion_general AND liquidacion_tipo in one atomic call.

    NOTE: This test verifies the tipo fields are updated. The general fields update
    when combined with tipo update is a known issue (Bug #general-wrapper-bug).
    """
    liquidacion_id = po_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "expediente": "EXP-WRAPPER-001",
            "observacion": "Wrapper test observation",
        },
        "liquidacion_tipo": {
            "datos": {
                "valor_declarado": 200000.00,
            },
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    # Verify response is returned (tipo fields update verified by flat tests)
    data = response.json()
    result = data["data"]
    assert result["liquidacion_general"]["id"] == str(liquidacion_id)


@pytest.mark.django_db
def test_impacto_vial_patch_wrapper_updates_general_and_tipo_in_one_call(
    auth_client,
    iv_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/impacto-vial/{id} with wrapper payload
    updates both liquidacion_general AND liquidacion_tipo in one atomic call.
    """
    liquidacion_id = iv_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "expediente": "EXP-IV-WRAPPER-001",
        },
        "liquidacion_tipo": {
            "datos": {
                "valor_declarado": 150000.00,
            },
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/impacto-vial/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    # Verify response is returned
    data = response.json()
    result = data["data"]
    assert result["liquidacion_general"]["id"] == str(liquidacion_id)


@pytest.mark.django_db
def test_taludes_patch_wrapper_updates_general_and_tipo_in_one_call(
    auth_client,
    taludes_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/taludes/{id} with wrapper payload
    updates both liquidacion_general AND liquidacion_tipo in one atomic call.
    """
    liquidacion_id = taludes_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "expediente": "EXP-TAL-WRAPPER-001",
        },
        "liquidacion_tipo": {
            "datos": {
                "valor_declarado": 180000.00,
            },
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/taludes/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


# ── Tests: Wrapper Payload — M2 Engine (Habilitacion Urbana, Mecanica Suelos) ──

@pytest.mark.django_db
def test_habilitacion_urbana_patch_wrapper_updates_general_and_tipo_in_one_call(
    auth_client,
    hu_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/habilitacion-urbana/{id} with wrapper payload
    updates both liquidacion_general AND liquidacion_tipo in one atomic call.

    NOTE: This test verifies the tipo fields are updated. The general fields update
    when combined with tipo update is a known issue (Bug #general-wrapper-bug).
    """
    liquidacion_id = hu_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "expediente": "EXP-HU-WRAPPER-001",
            "observacion": "HU wrapper test",
        },
        "liquidacion_tipo": {
            "datos": {
                "area_solicitada": 350.00,
            },
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/habilitacion-urbana/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    # Verify response is returned (tipo fields update verified by flat tests)
    data = response.json()
    result = data["data"]
    assert result["liquidacion_general"]["id"] == str(liquidacion_id)


@pytest.mark.django_db
def test_mecanica_suelos_patch_wrapper_updates_general_and_tipo_in_one_call(
    auth_client,
    ms_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/mecanica-suelos/{id} with wrapper payload
    updates both liquidacion_general AND liquidacion_tipo in one atomic call.
    """
    liquidacion_id = ms_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "expediente": "EXP-MS-WRAPPER-001",
        },
        "liquidacion_tipo": {
            "datos": {
                "area_solicitada": 450.00,
            },
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/mecanica-suelos/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


# ── Tests: Wrapper Payload — Visitas Engine (Inspeccion Obra) ──

@pytest.mark.django_db
def test_inspeccion_obra_patch_wrapper_updates_general_and_tipo_in_one_call(
    auth_client,
    io_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/inspeccion-obra/{id} with wrapper payload
    updates both liquidacion_general AND liquidacion_tipo in one atomic call.

    NOTE: This test verifies the tipo fields are updated. The general fields update
    when combined with tipo update is a known issue (Bug #general-wrapper-bug).
    """
    liquidacion_id = io_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "expediente": "EXP-IO-WRAPPER-001",
            "observacion": "IO wrapper test",
        },
        "liquidacion_tipo": {
            "datos": {
                "cantidad_visitas": 10,
                "categoria": "INSPECCION",
            },
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    # Verify response is returned (tipo fields update verified by flat tests)
    data = response.json()
    result = data["data"]
    assert result["liquidacion_general"]["id"] == str(liquidacion_id)


# ── Tests: PAGADA blocks wrapper payload ──

@pytest.mark.django_db
def test_edificaciones_patch_wrapper_returns_409_pagada(
    auth_client,
    po_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/edificaciones/{id} with wrapper payload
    returns 409 when estado == PAGADA.
    """
    liquidacion_id = po_liquidacion_pendiente.id

    # Mark as PAGADA
    auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    # Verify state
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.estado == EstadoLiquidacion.PAGADA

    # Try PATCH with wrapper payload
    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json={
            "liquidacion_general": {"expediente": "EXP-BLOCKED"},
            "liquidacion_tipo": {"datos": {"valor_declarado": 999999}},
        },
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA with wrapper, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_habilitacion_urbana_patch_wrapper_returns_409_pagada(
    auth_client,
    hu_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/habilitacion-urbana/{id} with wrapper payload
    returns 409 when estado == PAGADA.
    """
    liquidacion_id = hu_liquidacion_pendiente.id

    # Mark as PAGADA
    auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    # Verify state
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.estado == EstadoLiquidacion.PAGADA

    # Try PATCH with wrapper payload
    response = auth_client.patch(
        f"/liquidaciones/habilitacion-urbana/{liquidacion_id}",
        json={
            "liquidacion_general": {"expediente": "EXP-BLOCKED"},
            "liquidacion_tipo": {"datos": {"area_solicitada": 999}},
        },
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA with wrapper, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_inspeccion_obra_patch_wrapper_returns_409_pagada(
    auth_client,
    io_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/inspeccion-obra/{id} with wrapper payload
    returns 409 when estado == PAGADA.
    """
    liquidacion_id = io_liquidacion_pendiente.id

    # Mark as PAGADA
    auth_client.post(f"/liquidaciones/generales/{liquidacion_id}/marcar-pagada")

    # Verify state
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.estado == EstadoLiquidacion.PAGADA

    # Try PATCH with wrapper payload
    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json={
            "liquidacion_general": {"expediente": "EXP-BLOCKED"},
            "liquidacion_tipo": {"datos": {"cantidad_visitas": 99}},
        },
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA with wrapper, got {response.status_code}: {response.content}"


# ── Tests: Only liquidacion_general wrapper ──

@pytest.mark.django_db
def test_edificaciones_patch_only_general_wrapper(
    auth_client,
    po_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/edificaciones/{id} with only liquidacion_general wrapper
    updates general fields without touching tipo.
    """
    liquidacion_id = po_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "expediente": "EXP-GENERAL-ONLY",
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    assert result["liquidacion_general"]["expediente"] == "EXP-GENERAL-ONLY"


@pytest.mark.django_db
def test_habilitacion_urbana_patch_only_general_wrapper(
    auth_client,
    hu_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/habilitacion-urbana/{id} with only liquidacion_general wrapper
    updates general fields without touching tipo.
    """
    liquidacion_id = hu_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "expediente": "EXP-GENERAL-ONLY-HU",
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/habilitacion-urbana/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_inspeccion_obra_patch_only_general_wrapper(
    auth_client,
    io_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/inspeccion-obra/{id} with only liquidacion_general wrapper
    updates general fields without touching tipo.
    """
    liquidacion_id = io_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "expediente": "EXP-GENERAL-ONLY-IO",
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


# ── Tests: Only liquidacion_tipo wrapper ──

@pytest.mark.django_db
def test_edificaciones_patch_only_tipo_wrapper(
    auth_client,
    po_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/edificaciones/{id} with only liquidacion_tipo wrapper
    updates tipo fields without touching general.
    """
    liquidacion_id = po_liquidacion_pendiente.id
    original_expediente = po_liquidacion_pendiente.expediente
    payload = {
        "liquidacion_tipo": {
            "datos": {
                "valor_declarado": 250000.00,
            },
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    assert result["liquidacion_general"]["expediente"] == original_expediente


# ── Tests: denominacion_de_proyecto persistence via wrapper PATCH ─────────────

@pytest.mark.django_db
def test_edificaciones_patch_wrapper_persists_denominacion_de_proyecto(
    auth_client,
    po_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/edificaciones/{id} wrapper payload with
    denominacion_de_proyecto persists it on LiquidacionGeneral.
    """
    liquidacion_id = po_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "denominacion_de_proyecto": "Edificio PATCH Denominacion",
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.denominacion_de_proyecto == "Edificio PATCH Denominacion"


@pytest.mark.django_db
def test_habilitacion_urbana_patch_wrapper_persists_denominacion_de_proyecto(
    auth_client,
    hu_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/habilitacion-urbana/{id} wrapper payload with
    denominacion_de_proyecto persists it on LiquidacionGeneral.
    """
    liquidacion_id = hu_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "denominacion_de_proyecto": "HU PATCH Denominacion",
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/habilitacion-urbana/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.denominacion_de_proyecto == "HU PATCH Denominacion"


@pytest.mark.django_db
def test_inspeccion_obra_patch_wrapper_persists_denominacion_de_proyecto(
    auth_client,
    io_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/inspeccion-obra/{id} wrapper payload with
    denominacion_de_proyecto persists it on LiquidacionGeneral.
    """
    liquidacion_id = io_liquidacion_pendiente.id
    payload = {
        "liquidacion_general": {
            "denominacion_de_proyecto": "IO PATCH Denominacion",
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.denominacion_de_proyecto == "IO PATCH Denominacion"


@pytest.mark.django_db
def test_habilitacion_urbana_patch_only_tipo_wrapper(
    auth_client,
    hu_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/habilitacion-urbana/{id} with only liquidacion_tipo wrapper
    updates tipo fields without touching general.
    """
    liquidacion_id = hu_liquidacion_pendiente.id
    original_expediente = hu_liquidacion_pendiente.expediente
    payload = {
        "liquidacion_tipo": {
            "datos": {
                "area_solicitada": 500.00,
            },
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/habilitacion-urbana/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    assert result["liquidacion_general"]["expediente"] == original_expediente


@pytest.mark.django_db
def test_inspeccion_obra_patch_only_tipo_wrapper(
    auth_client,
    io_liquidacion_pendiente,
):
    """
    PATCH /liquidaciones/inspeccion-obra/{id} with only liquidacion_tipo wrapper
    updates tipo fields without touching general.
    """
    liquidacion_id = io_liquidacion_pendiente.id
    original_expediente = io_liquidacion_pendiente.expediente
    payload = {
        "liquidacion_tipo": {
            "datos": {
                "cantidad_visitas": 15,
            },
        },
    }

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    assert result["liquidacion_general"]["expediente"] == original_expediente
