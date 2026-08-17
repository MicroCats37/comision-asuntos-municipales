"""
E2E integration tests for ReciboHonorarioDelegado endpoints.

Tests hit the real HTTP endpoints via Ninja TestClient (auth=None on all endpoints).
Tests use @pytest.mark.django_db for database access.

Covers:
- POST /finanzas/recibos-delegados (PORCENTAJE, M2, IO types)
- POST /finanzas/recibos-delegados 404 for missing id
- GET /finanzas/recibos-delegados (pagination, filters, empty)
"""
import pytest
from decimal import Decimal
from datetime import date
import uuid

from ninja.testing import TestClient
from config.api import api
from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero, EspecialidadRevision
from modules.liquidaciones.domain.models.delegado import Delegado, LiquidacionDelegado
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    DerechoPorcentajeObra,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.finanzas.domain.models.recibo_honorario import ReciboHonorarioDelegado, TASA_RENTA_CIP, TASA_APORTE_CODEMU, TASA_FONDO_COMUN
from django.contrib.auth import get_user_model


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client(db):
    """Ninja TestClient — no auth required on finanzas endpoints."""
    return TestClient(api)


@pytest.fixture
def ubigeo_departamento(db):
    return UbigeoDepartamento.objects.create(nombre="LIMA")


@pytest.fixture
def ubigeo_provincia(db, ubigeo_departamento):
    return UbigeoProvincia.objects.create(departamento=ubigeo_departamento, nombre="LIMA")


@pytest.fixture
def ubigeo_distrito(db, ubigeo_provincia):
    return UbigeoDistrito.objects.create(
        provincia=ubigeo_provincia, nombre="MIRAFLORES", ubigeo="150132"
    )


@pytest.fixture
def usuario_delegado(db):
    User = get_user_model()
    return User.objects.create_user(
        username="delegado_e2e", email="delegado_e2e@test.com",
        password="testpass123", dni="87654321",
    )


@pytest.fixture
def perfil_ingeniero_delegado(db, usuario_delegado):
    return PerfilIngeniero.objects.create(
        usuario=usuario_delegado,
        apellido_paterno="Pérez", apellido_materno="García",
        nombres="Juan", cip="CIP-99999", dni="87654321",
    )


@pytest.fixture
def especialidad_estructuras(db):
    return EspecialidadRevision.objects.create(
        codigo="E01", slug="estructuras", nombre="Estructuras",
    )


@pytest.fixture
def delegado(db, perfil_ingeniero_delegado):
    return Delegado.objects.create(
        perfil_ingeniero=perfil_ingeniero_delegado,
    )


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    return Municipalidad.objects.create(
        codigo="M001", nombre="Municipalidad de Miraflores", distrito=ubigeo_distrito,
    )


@pytest.fixture
def proyecto(db, municipalidad, ubigeo_distrito):
    return Proyecto.objects.create(
        denominacion="Proyecto E2E Test",
        nombre_propietario="Propietario E2E SAC",
        direccion="Av. E2E 123",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario E2E SAC",
    )


@pytest.fixture
def usuario_liquidacion(db):
    User = get_user_model()
    return User.objects.create_user(
        username="liq_e2e", email="liq_e2e@test.com",
        password="testpass123", dni="11223344",
    )


@pytest.fixture
def igv_vigente(db):
    return IGV.objects.create(valor=Decimal("0.18"), periodo_inicio=date(2024, 1, 1), periodo_fin=None)


@pytest.fixture
def uit_vigente(db):
    return UIT.objects.create(valor=Decimal("5150.00"), periodo_inicio=date(2024, 1, 1), periodo_fin=None)


# ── TipoLiquidacion Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def tipo_edificacion(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacion.EDIFICACION, defaults={"nombre": "Edificaciones"}
    )[0]


@pytest.fixture
def tipo_habilitacion_urbana(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacion.HABILITACION_URBANA, defaults={"nombre": "Habilitación Urbana"}
    )[0]


@pytest.fixture
def tipo_inspeccion_obra(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacion.INSPECCION_OBRA, defaults={"nombre": "Inspección de Obra"}
    )[0]


# ── PORCENTAJE-type fixtures (EDIFICACION) ────────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_edificacion(db, tipo_edificacion):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def derecho_porcentaje_vigente(db):
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_porcentaje_obra_estructuras(db, tarifa_liquidacion_base_edificacion):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        porcentaje_liquidacion=Decimal("0.0010"),
    )


@pytest.fixture
def liquidacion_general_porcentaje(
    db, proyecto, municipalidad, tipo_edificacion, usuario_liquidacion, igv_vigente, uit_vigente
):
    """LiquidacionGeneral for EDIFICACION type."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-E2E-POR-001",
        estado="REGISTRADO",
        sub_total=Decimal("5000.00"),
        total=Decimal("5900.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        numero_revision=1,
    )


@pytest.fixture
def liquidacion_porcentaje_obra(db, liquidacion_general_porcentaje, derecho_porcentaje_vigente):
    """LiquidacionPorcentajeObra linked to the EDIFICACION liquidacion."""
    return LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=liquidacion_general_porcentaje,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )


@pytest.fixture
def liquidacion_porcentaje_detalle(
    db, liquidacion_porcentaje_obra, tarifa_porcentaje_obra_estructuras, especialidad_estructuras
):
    """LiquidacionPorcentajeObraDetalle matching the delegado's especialidad."""
    return LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=liquidacion_porcentaje_obra,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),  # imp_bruto = 1000.00
        igv=Decimal("180.00"),
        uit=Decimal("0.00"),
        total=Decimal("1180.00"),
    )


@pytest.fixture
def liquidacion_delegado_porcentaje(
    db, liquidacion_general_porcentaje, liquidacion_porcentaje_detalle, delegado, especialidad_estructuras
):
    """LiquidacionDelegado for PORCENTAJE type (EDIFICACION)."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_general_porcentaje,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
        periodo="2026-01",
    )


# ── M2-type fixtures (HABILITACION_URBANA) ─────────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_hu(db, tipo_habilitacion_urbana):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def derecho_metro_cuadrado_vigente(db):
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_hu(db, tarifa_liquidacion_base_hu):
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_liquidacion_base_hu,
        area_minima=Decimal("50.00"),
        area_maxima=Decimal("500.00"),
        costo_por_m2=Decimal("25.00"),
    )


@pytest.fixture
def liquidacion_general_m2(
    db, proyecto, municipalidad, tipo_habilitacion_urbana, usuario_liquidacion
):
    """LiquidacionGeneral for HABILITACION_URBANA (M2 type) — sub_total is imp_bruto source."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_habilitacion_urbana,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-E2E-M2-001",
        estado="REGISTRADO",
        sub_total=Decimal("3000.00"),
        total=Decimal("3540.00"),
        numero_revision=1,
    )


@pytest.fixture
def liquidacion_m2(db, liquidacion_general_m2, derecho_metro_cuadrado_vigente, tarifa_m2_hu):
    """LiquidacionPorMetroCuadrado for the M2 liquidacion."""
    return LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=liquidacion_general_m2,
        area_m2=Decimal("120.00"),
        costo_por_m2=Decimal("25.00"),
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        tarifa_aplicada=tarifa_m2_hu,
        derecho=derecho_metro_cuadrado_vigente,
    )


@pytest.fixture
def liquidacion_delegado_m2(
    db, liquidacion_general_m2, delegado, especialidad_estructuras
):
    """LiquidacionDelegado for M2 type (HABILITACION_URBANA)."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_general_m2,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
        periodo="2026-01",
    )


# ── VISITAS-type fixtures (INSPECCION_OBRA) ────────────────────────────────────

@pytest.fixture
def tipo_inspeccion_obra(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacion.INSPECCION_OBRA, defaults={"nombre": "Inspección de Obra"}
    )[0]


@pytest.fixture
def liquidacion_general_io(
    db, proyecto, municipalidad, tipo_inspeccion_obra, usuario_liquidacion
):
    """LiquidacionGeneral for INSPECCION_OBRA — sub_total is imp_bruto source."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_inspeccion_obra,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-E2E-IO-001",
        estado="REGISTRADO",
        sub_total=Decimal("2000.00"),
        total=Decimal("2360.00"),
        numero_revision=1,
    )


@pytest.fixture
def liquidacion_delegado_io(
    db, liquidacion_general_io, delegado, especialidad_estructuras
):
    """LiquidacionDelegado for VISITAS type (INSPECCION_OBRA)."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_general_io,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
        periodo="2026-01",
    )


# ── E2E Tests ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_e2e_post_recibo_porcentaje(api_client, liquidacion_delegado_porcentaje):
    """
    POST /finanzas/recibos-delegados with PORCENTAJE liquidacion_delegado_id.

    imp_bruto comes from LiquidacionPorcentajeObraDetalle.subtotal (1000.00).
    Honorarios: renta_cip=250, aporte_codemu=50, fondo_comun=100, neto=600.
    """
    imp_bruto = Decimal("1000.00")
    expected_renta = imp_bruto * TASA_RENTA_CIP
    expected_aporte = imp_bruto * TASA_APORTE_CODEMU
    expected_fondo = imp_bruto * TASA_FONDO_COMUN
    expected_neto = imp_bruto - expected_renta - expected_aporte - expected_fondo

    response = api_client.post(
        "/finanzas/recibos-delegados",
        json={"liquidacion_delegado_id": str(liquidacion_delegado_porcentaje.id)},
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()
    assert data["success"] is True

    recibo = data["data"]
    assert recibo["liquidacion_delegado_id"] == str(liquidacion_delegado_porcentaje.id)
    assert Decimal(recibo["calculo"]["imp_bruto"]) == imp_bruto
    assert Decimal(recibo["calculo"]["renta_cip"]) == expected_renta
    assert Decimal(recibo["calculo"]["aporte_codemu"]) == expected_aporte
    assert Decimal(recibo["calculo"]["fondo_comun"]) == expected_fondo
    assert Decimal(recibo["calculo"]["neto_honorario"]) == expected_neto
    assert Decimal(recibo["calculo"]["honorario"]) == expected_neto
    # sub_total is the LiquidacionGeneral.sub_total snapshot
    assert Decimal(recibo["calculo"]["sub_total"]) == Decimal("5000.00")

    # Homogéneo con el listado: trae los anidados liquidacion_general/delegado/especialidad
    assert "id" in recibo and recibo["id"]
    assert recibo["liquidacion_general"]["id"] == str(liquidacion_delegado_porcentaje.liquidacion.id)
    assert recibo["liquidacion_general"]["tipo_liquidacion"]["codigo"] == "EDIFICACION"
    assert recibo["delegado"]["id"] == str(liquidacion_delegado_porcentaje.delegado.id)
    assert recibo["especialidad"]["id"] == str(liquidacion_delegado_porcentaje.especialidad_revision.id)


@pytest.mark.django_db
def test_e2e_post_recibo_m2(api_client, liquidacion_delegado_m2):
    """
    POST /finanzas/recibos-delegados with M2-type liquidacion_delegado_id.

    imp_bruto = liquidacion.sub_total (3000.00).
    Honorarios: renta_cip=750, aporte_codemu=150, fondo_comun=300, neto=1800.
    """
    imp_bruto = Decimal("3000.00")
    expected_renta = imp_bruto * TASA_RENTA_CIP
    expected_aporte = imp_bruto * TASA_APORTE_CODEMU
    expected_fondo = imp_bruto * TASA_FONDO_COMUN
    expected_neto = imp_bruto - expected_renta - expected_aporte - expected_fondo

    response = api_client.post(
        "/finanzas/recibos-delegados",
        json={"liquidacion_delegado_id": str(liquidacion_delegado_m2.id)},
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()
    assert data["success"] is True

    recibo = data["data"]
    assert Decimal(recibo["calculo"]["imp_bruto"]) == imp_bruto
    assert Decimal(recibo["calculo"]["renta_cip"]) == expected_renta
    assert Decimal(recibo["calculo"]["aporte_codemu"]) == expected_aporte
    assert Decimal(recibo["calculo"]["fondo_comun"]) == expected_fondo
    assert Decimal(recibo["calculo"]["neto_honorario"]) == expected_neto
    assert Decimal(recibo["calculo"]["honorario"]) == expected_neto


@pytest.mark.django_db
def test_e2e_post_recibo_io_visitas(api_client, liquidacion_delegado_io):
    """
    POST /finanzas/recibos-delegados with INSPECCION_OBRA-type liquidacion_delegado_id.

    imp_bruto = liquidacion.sub_total (2000.00).
    Honorarios: renta_cip=500, aporte_codemu=100, fondo_comun=200, neto=1200.
    """
    imp_bruto = Decimal("2000.00")
    expected_renta = imp_bruto * TASA_RENTA_CIP
    expected_aporte = imp_bruto * TASA_APORTE_CODEMU
    expected_fondo = imp_bruto * TASA_FONDO_COMUN
    expected_neto = imp_bruto - expected_renta - expected_aporte - expected_fondo

    response = api_client.post(
        "/finanzas/recibos-delegados",
        json={"liquidacion_delegado_id": str(liquidacion_delegado_io.id)},
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()
    assert data["success"] is True

    recibo = data["data"]
    assert Decimal(recibo["calculo"]["imp_bruto"]) == imp_bruto
    assert Decimal(recibo["calculo"]["renta_cip"]) == expected_renta
    assert Decimal(recibo["calculo"]["neto_honorario"]) == expected_neto
    assert Decimal(recibo["calculo"]["honorario"]) == expected_neto


@pytest.mark.django_db
def test_e2e_post_recibo_404(api_client):
    """
    POST /finanzas/recibos-delegados with nonexistent liquidacion_delegado_id → 404.
    """
    fake_id = uuid.uuid4()
    response = api_client.post(
        "/finanzas/recibos-delegados",
        json={"liquidacion_delegado_id": str(fake_id)},
    )

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_e2e_get_recibos_paginated(
    api_client,
    liquidacion_delegado_porcentaje,
    liquidacion_delegado_m2,
    liquidacion_delegado_io,
):
    """
    After creating 3 recibos via POST, GET /finanzas/recibos-delegados?page=1&page_size=2
    returns PaginatedData with 2 items, total=3, total_pages=2.
    """
    # Create 3 receipts
    for ld in [liquidacion_delegado_porcentaje, liquidacion_delegado_m2, liquidacion_delegado_io]:
        api_client.post(
            "/finanzas/recibos-delegados",
            json={"liquidacion_delegado_id": str(ld.id)},
        )

    # Paginated GET
    response = api_client.get("/finanzas/recibos-delegados?page=1&page_size=2")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()
    assert data["success"] is True

    paginated = data["data"]
    assert len(paginated["items"]) == 2, f"Expected 2 items on page 1, got {len(paginated['items'])}"
    assert paginated["total"] == 3
    assert paginated["page"] == 1
    assert paginated["page_size"] == 2
    assert paginated["total_pages"] == 2

    # Page 2
    response2 = api_client.get("/finanzas/recibos-delegados?page=2&page_size=2")
    data2 = response2.json()
    assert len(data2["data"]["items"]) == 1
    assert data2["data"]["total"] == 3


@pytest.mark.django_db
def test_e2e_get_recibos_filters(
    api_client,
    liquidacion_delegado_porcentaje,
    liquidacion_delegado_m2,
):
    """
    GET with ?delegado_id= and ?liquidacion_id= returns filtered results.
    """
    # Create receipts for both liquidacion_delegados
    api_client.post(
        "/finanzas/recibos-delegados",
        json={"liquidacion_delegado_id": str(liquidacion_delegado_porcentaje.id)},
    )
    api_client.post(
        "/finanzas/recibos-delegados",
        json={"liquidacion_delegado_id": str(liquidacion_delegado_m2.id)},
    )

    # Filter by delegado_id
    deleg_id = liquidacion_delegado_porcentaje.delegado.id
    response = api_client.get(f"/finanzas/recibos-delegados?delegado_id={deleg_id}")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert all(str(item["delegado"]["id"]) == str(deleg_id) for item in items)

    # Filter by liquidacion_id
    liq_id = liquidacion_delegado_m2.liquidacion.id
    response2 = api_client.get(f"/finanzas/recibos-delegados?liquidacion_id={liq_id}")
    assert response2.status_code == 200
    items2 = response2.json()["data"]["items"]
    assert all(str(item["liquidacion_general"]["id"]) == str(liq_id) for item in items2)


@pytest.mark.django_db
def test_e2e_get_recibos_empty(api_client):
    """
    GET /finanzas/recibos-delegados with no data → items=[], total=0.
    """
    response = api_client.get("/finanzas/recibos-delegados?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0
    assert data["data"]["total_pages"] == 0
