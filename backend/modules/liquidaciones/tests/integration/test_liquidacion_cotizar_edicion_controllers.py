"""
Integration tests for POST /{liquidacion_id}/cotizar-edicion endpoints.

Tests the 3 engine types across all 6 specific liquidacion types:
- PO engine: Edificaciones, Taludes, Impacto Vial
- M2 engine: Habilitación Urbana, Mecánica de Suelos
- Visitas engine: Inspección de Obra

cotizar-edicion is READ-ONLY — it does NOT persist any changes.

Tests verify:
1. Happy-path quotes for representative types (PO, M2, Visitas)
2. Read-only assertion: DB rows unchanged after quote
3. 404 for non-existent liquidacion ID
4. 422 / validation error when liquidacion_tipo is missing
5. Route smoke tests for all 6 endpoints

Scope: HTTP controller + orchestrator + service integration.
"""
import pytest
from decimal import Decimal
from datetime import timedelta
import django.utils.timezone as tz

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
def edifi_cotizar_pendiente(
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
    """Edificaciones liquidacion in PENDIENTE state for cotizar-edicion tests."""
    import django.utils.timezone as tz
    from datetime import timedelta
    user = create_user

    # Use a fecha_registro clearly in the past so vigente query finds tariffs
    past_date = tz.now() - timedelta(days=365)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-COTZ-EDI-001",
        observacion="Test cotizar-edicion Edificaciones",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        fecha_registro=past_date,
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
def taludes_cotizar_pendiente(
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
    """Taludes liquidacion in PENDIENTE state for cotizar-edicion tests."""
    user = create_user

    past_date = tz.now() - timedelta(days=365)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-COTZ-TAL-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_taludes,
        numero_revision=1,
        sub_total=Decimal("600.00"),
        total=Decimal("708.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        fecha_registro=past_date,
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


@pytest.fixture
def iv_cotizar_pendiente(
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
    """Impacto Vial liquidacion in PENDIENTE state for cotizar-edicion tests."""
    user = create_user

    past_date = tz.now() - timedelta(days=365)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-COTZ-IV-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_impacto_vial,
        numero_revision=1,
        sub_total=Decimal("800.00"),
        total=Decimal("944.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        fecha_registro=past_date,
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


# ── M2 Engine Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def hu_cotizar_pendiente(
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
    """Habilitación Urbana liquidacion in PENDIENTE state for cotizar-edicion tests."""
    user = create_user

    past_date = tz.now() - timedelta(days=365)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-COTZ-HU-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("2000.00"),
        total=Decimal("2360.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        fecha_registro=past_date,
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
def ms_cotizar_pendiente(
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
    """Mecánica de Suelos liquidacion in PENDIENTE state for cotizar-edicion tests."""
    user = create_user

    past_date = tz.now() - timedelta(days=365)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-COTZ-MS-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_mecanica_suelos,
        numero_revision=1,
        sub_total=Decimal("1500.00"),
        total=Decimal("1770.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        fecha_registro=past_date,
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
def io_cotizar_pendiente(
    db,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tarifa_visitas_io,
    tipo_inspeccion_obra,
):
    """Inspección de Obra liquidacion in PENDIENTE state for cotizar-edicion tests."""
    user = create_user

    past_date = tz.now() - timedelta(days=365)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-COTZ-IO-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("1200.00"),
        total=Decimal("1416.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        fecha_registro=past_date,
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


# ── Tests: PO Representative — Edificaciones ───────────────────────────────────

@pytest.mark.django_db
def test_edificaciones_cotizar_edicion_returns_200_liquidacion_tipo_only(
    auth_client,
    edifi_cotizar_pendiente,
):
    """
    POST /liquidaciones/edificaciones/{id}/cotizar-edicion returns 200
    when body contains only liquidacion_tipo (no tipo_liquidacion, motor, etc.).
    """
    liquidacion_id = edifi_cotizar_pendiente.id
    lpo = edifi_cotizar_pendiente.liquidacion_porcentaje_obra
    detalle = lpo.detalles.first()

    payload = {
        "liquidacion_tipo": {
            "datos": {
                "valor_declarado": 150000.00,
            },
            "tarifas": [
                {
                    "tarifa_porcentaje_obra_id": str(detalle.tarifa_aplicada_id),
                    "especialidad_id": str(detalle.especialidad_id),
                }
            ],
        }
    }

    response = auth_client.post(
        f"/liquidaciones/edificaciones/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data["success"] is True
    result = data["data"]
    # Response contains calculation fields (not liquidacion_general/liquidacion_especifica)
    assert "valor_declarado" in result
    assert "total" in result
    assert "total_subtotal" in result


@pytest.mark.django_db
def test_edificaciones_cotizar_edicion_read_only_db_unchanged(
    auth_client,
    edifi_cotizar_pendiente,
):
    """
    cotizar-edicion is READ-ONLY. DB rows remain unchanged after quote.
    """
    liquidacion_id = edifi_cotizar_pendiente.id
    lpo = edifi_cotizar_pendiente.liquidacion_porcentaje_obra
    detalle = lpo.detalles.first()

    # Snapshot DB state before
    lg_before = LiquidacionGeneral.objects.get(id=liquidacion_id)
    lpo_before = LiquidacionPorcentajeObra.objects.get(id=lpo.id)
    detalle_before = LiquidacionPorcentajeObraDetalle.objects.get(id=detalle.id)

    payload = {
        "liquidacion_tipo": {
            "datos": {"valor_declarado": 200000.00},
            "tarifas": [
                {
                    "tarifa_porcentaje_obra_id": str(detalle.tarifa_aplicada_id),
                    "especialidad_id": str(detalle.especialidad_id),
                }
            ],
        }
    }

    response = auth_client.post(
        f"/liquidaciones/edificaciones/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 200

    # Refresh from DB
    lg_after = LiquidacionGeneral.objects.get(id=liquidacion_id)
    lpo_after = LiquidacionPorcentajeObra.objects.get(id=lpo.id)
    detalle_after = LiquidacionPorcentajeObraDetalle.objects.get(id=detalle.id)

    # Totals unchanged
    assert lg_after.sub_total == lg_before.sub_total
    assert lg_after.total == lg_before.total
    # valor_declarado unchanged
    assert lpo_after.valor_declarado == lpo_before.valor_declarado
    # detalle subtotal unchanged
    assert detalle_after.subtotal == detalle_before.subtotal


# ── Tests: M2 Representative — Habilitación Urbana ────────────────────────────

@pytest.mark.django_db
def test_habilitacion_urbana_cotizar_edicion_returns_200_liquidacion_tipo_only(
    auth_client,
    hu_cotizar_pendiente,
):
    """
    POST /liquidaciones/habilitacion-urbana/{id}/cotizar-edicion returns 200
    when body contains only liquidacion_tipo.
    """
    liquidacion_id = hu_cotizar_pendiente.id
    lm2 = hu_cotizar_pendiente.liquidacion_m2.first()

    payload = {
        "liquidacion_tipo": {
            "datos": {
                "area_solicitada": 250.00,
            },
            "tarifa": {
                "tarifa_m2_id": str(lm2.tarifa_aplicada_id),
            },
        }
    }

    response = auth_client.post(
        f"/liquidaciones/habilitacion-urbana/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data["success"] is True
    result = data["data"]
    # M2 response has datos and calculo
    assert "datos" in result
    assert "calculo" in result


@pytest.mark.django_db
def test_habilitacion_urbana_cotizar_edicion_read_only_db_unchanged(
    auth_client,
    hu_cotizar_pendiente,
):
    """
    cotizar-edicion is READ-ONLY. DB rows remain unchanged after quote.
    """
    liquidacion_id = hu_cotizar_pendiente.id
    lm2 = hu_cotizar_pendiente.liquidacion_m2.first()

    # Snapshot DB state before
    lg_before = LiquidacionGeneral.objects.get(id=liquidacion_id)
    lm2_before = LiquidacionPorMetroCuadrado.objects.get(id=lm2.id)
    area_before = lm2_before.area_m2

    payload = {
        "liquidacion_tipo": {
            "datos": {"area_solicitada": 500.00},
            "tarifa": {"tarifa_m2_id": str(lm2.tarifa_aplicada_id)},
        }
    }

    response = auth_client.post(
        f"/liquidaciones/habilitacion-urbana/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 200

    # Refresh from DB
    lg_after = LiquidacionGeneral.objects.get(id=liquidacion_id)
    lm2_after = LiquidacionPorMetroCuadrado.objects.get(id=lm2.id)

    # Totals unchanged
    assert lg_after.sub_total == lg_before.sub_total
    assert lg_after.total == lg_before.total
    # area_m2 unchanged
    assert lm2_after.area_m2 == area_before


# ── Tests: Visitas Representative — Inspección de Obra ─────────────────────────

@pytest.mark.django_db
def test_inspeccion_obra_cotizar_edicion_returns_200_liquidacion_tipo_only(
    auth_client,
    io_cotizar_pendiente,
):
    """
    POST /liquidaciones/inspeccion-obra/{id}/cotizar-edicion returns 200
    when body contains only liquidacion_tipo.
    """
    liquidacion_id = io_cotizar_pendiente.id
    lvisitas = io_cotizar_pendiente.liquidacion_visitas.get()

    payload = {
        "liquidacion_tipo": {
            "datos": {
                "cantidad_visitas": 8,
            },
            "tarifa": {
                "tarifa_visitas_id": str(lvisitas.tarifa_aplicada_id),
            },
        }
    }

    response = auth_client.post(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data["success"] is True
    result = data["data"]
    # IO response has datos and calculo
    assert "datos" in result
    assert "calculo" in result


@pytest.mark.django_db
def test_inspeccion_obra_cotizar_edicion_read_only_db_unchanged(
    auth_client,
    io_cotizar_pendiente,
):
    """
    cotizar-edicion is READ-ONLY. DB rows remain unchanged after quote.
    """
    liquidacion_id = io_cotizar_pendiente.id
    lvisitas = io_cotizar_pendiente.liquidacion_visitas.get()

    # Snapshot DB state before
    lg_before = LiquidacionGeneral.objects.get(id=liquidacion_id)
    lvisitas_before = LiquidacionPorCategoriaVisitas.objects.get(id=lvisitas.id)
    cantidad_before = lvisitas_before.cantidad_visitas

    payload = {
        "liquidacion_tipo": {
            "datos": {"cantidad_visitas": 15},
            "tarifa": {"tarifa_visitas_id": str(lvisitas.tarifa_aplicada_id)},
        }
    }

    response = auth_client.post(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 200

    # Refresh from DB
    lg_after = LiquidacionGeneral.objects.get(id=liquidacion_id)
    lvisitas_after = LiquidacionPorCategoriaVisitas.objects.get(id=lvisitas.id)

    # Totals unchanged
    assert lg_after.sub_total == lg_before.sub_total
    assert lg_after.total == lg_before.total
    # cantidad_visitas unchanged
    assert lvisitas_after.cantidad_visitas == cantidad_before


# ── Tests: 404 Non-existent ID ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_edificaciones_cotizar_edicion_returns_404_non_existent(
    auth_client,
    db,
):
    """cotizar-edicion returns 404 for non-existent liquidacion ID."""
    import uuid
    non_existent_id = uuid.uuid4()

    payload = {
        "liquidacion_tipo": {
            "datos": {"valor_declarado": 100000.00},
            "tarifas": [],
        }
    }

    response = auth_client.post(
        f"/liquidaciones/edificaciones/{non_existent_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_habilitacion_urbana_cotizar_edicion_returns_404_non_existent(
    auth_client,
    db,
):
    """cotizar-edicion returns 404 for non-existent liquidacion ID."""
    import uuid
    non_existent_id = uuid.uuid4()

    payload = {
        "liquidacion_tipo": {
            "datos": {"area_solicitada": 100.00},
            "tarifa": {"tarifa_m2_id": str(uuid.uuid4())},
        }
    }

    response = auth_client.post(
        f"/liquidaciones/habilitacion-urbana/{non_existent_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_inspeccion_obra_cotizar_edicion_returns_404_non_existent(
    auth_client,
    db,
):
    """cotizar-edicion returns 404 for non-existent liquidacion ID."""
    import uuid
    non_existent_id = uuid.uuid4()

    payload = {
        "liquidacion_tipo": {
            "datos": {"cantidad_visitas": 5},
            "tarifa": {"tarifa_visitas_id": str(uuid.uuid4())},
        }
    }

    response = auth_client.post(
        f"/liquidaciones/inspeccion-obra/{non_existent_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 404


# ── Tests: Validation — missing liquidacion_tipo ──────────────────────────────

@pytest.mark.django_db
def test_edificaciones_cotizar_edicion_422_missing_liquidacion_tipo(
    auth_client,
    edifi_cotizar_pendiente,
):
    """
    cotizar-edicion returns 422 when body contains liquidacion_general
    but NOT liquidacion_tipo (schema validation failure).
    """
    liquidacion_id = edifi_cotizar_pendiente.id

    # Sending liquidacion_general instead of liquidacion_tipo
    payload = {
        "liquidacion_general": {
            "expediente": "EXP-SHOULD-FAIL",
        }
    }

    response = auth_client.post(
        f"/liquidaciones/edificaciones/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 422, \
        f"Expected 422 for missing liquidacion_tipo, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_habilitacion_urbana_cotizar_edicion_422_missing_liquidacion_tipo(
    auth_client,
    hu_cotizar_pendiente,
):
    """
    cotizar-edicion returns 422 when body contains liquidacion_general
    but NOT liquidacion_tipo.
    """
    liquidacion_id = hu_cotizar_pendiente.id

    payload = {
        "liquidacion_general": {
            "expediente": "EXP-SHOULD-FAIL",
        }
    }

    response = auth_client.post(
        f"/liquidaciones/habilitacion-urbana/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 422, \
        f"Expected 422 for missing liquidacion_tipo, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_inspeccion_obra_cotizar_edicion_422_missing_liquidacion_tipo(
    auth_client,
    io_cotizar_pendiente,
):
    """
    cotizar-edicion returns 422 when body contains liquidacion_general
    but NOT liquidacion_tipo.
    """
    liquidacion_id = io_cotizar_pendiente.id

    payload = {
        "liquidacion_general": {
            "expediente": "EXP-SHOULD-FAIL",
        }
    }

    response = auth_client.post(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 422, \
        f"Expected 422 for missing liquidacion_tipo, got {response.status_code}: {response.content}"


# ── Tests: Route Smoke Tests — All 6 Endpoints ─────────────────────────────────

@pytest.mark.django_db
def test_taludes_cotizar_edicion_returns_200(
    auth_client,
    taludes_cotizar_pendiente,
):
    """
    Smoke test: POST /liquidaciones/taludes/{id}/cotizar-edicion returns 200.
    """
    liquidacion_id = taludes_cotizar_pendiente.id
    lpo = taludes_cotizar_pendiente.liquidacion_porcentaje_obra
    detalle = lpo.detalles.first()

    payload = {
        "liquidacion_tipo": {
            "datos": {"valor_declarado": 80000.00},
            "tarifas": [
                {
                    "tarifa_porcentaje_obra_id": str(detalle.tarifa_aplicada_id),
                    "especialidad_id": str(detalle.especialidad_id),
                }
            ],
        }
    }

    response = auth_client.post(
        f"/liquidaciones/taludes/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_impacto_vial_cotizar_edicion_returns_200(
    auth_client,
    iv_cotizar_pendiente,
):
    """
    Smoke test: POST /liquidaciones/impacto-vial/{id}/cotizar-edicion returns 200.
    """
    liquidacion_id = iv_cotizar_pendiente.id
    lpo = iv_cotizar_pendiente.liquidacion_porcentaje_obra
    detalle = lpo.detalles.first()

    payload = {
        "liquidacion_tipo": {
            "datos": {"valor_declarado": 60000.00},
            "tarifas": [
                {
                    "tarifa_porcentaje_obra_id": str(detalle.tarifa_aplicada_id),
                    "especialidad_id": str(detalle.especialidad_id),
                }
            ],
        }
    }

    response = auth_client.post(
        f"/liquidaciones/impacto-vial/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_mecanica_suelos_cotizar_edicion_returns_200(
    auth_client,
    ms_cotizar_pendiente,
):
    """
    Smoke test: POST /liquidaciones/mecanica-suelos/{id}/cotizar-edicion returns 200.
    """
    liquidacion_id = ms_cotizar_pendiente.id
    lm2 = ms_cotizar_pendiente.liquidacion_m2.first()

    payload = {
        "liquidacion_tipo": {
            "datos": {"area_solicitada": 300.00},
            "tarifa": {"tarifa_m2_id": str(lm2.tarifa_aplicada_id)},
        }
    }

    response = auth_client.post(
        f"/liquidaciones/mecanica-suelos/{liquidacion_id}/cotizar-edicion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
