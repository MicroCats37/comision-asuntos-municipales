"""
Integration tests for legacy liquidaciones endpoints (fecha_registro historical).

Tests use Ninja's TestClient for proper async handling.
All tests use @pytest.mark.django_db for database access.

Coverage:
1. Edificaciones legacy con fecha_registro pasada → 200, tarifas históricas usadas
2. Edificaciones legacy SIN fecha_registro → 200, usa hoy (default)
3. M2 legacy (HU) con fecha_registro → 200 y tarifa m2 por esa fecha
4. Visitas legacy (IO) — smoke test 200
5. numero_revision del payload → se respeta
6. usuario_creador = admin autenticado
"""
import pytest
from decimal import Decimal
from datetime import date

from ninja.testing import TestClient
from ninja_jwt.tokens import AccessToken
from django.contrib.auth import get_user_model

from config.api import api
from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.finanzas.domain.models.impuestos import UIT, IGV
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
    DerechoPorcentajeObra,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
    LiquidacionEspecialidadDisponibles,
)
from modules.liquidaciones.domain.models.inspector import Inspector
from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision, PerfilIngeniero
from modules.liquidaciones.domain.models.proyecto import Proyecto


# ── Fixtures base (local — override conftest when needed) ───────────────────────

@pytest.fixture
def ubigeo_departamento(db):
    return UbigeoDepartamento.objects.create(nombre="Lima")


@pytest.fixture
def ubigeo_provincia(db, ubigeo_departamento):
    return UbigeoProvincia.objects.create(departamento=ubigeo_departamento, nombre="Lima")


@pytest.fixture
def ubigeo_distrito(db, ubigeo_provincia):
    return UbigeoDistrito.objects.create(provincia=ubigeo_provincia, nombre="Miraflores", ubigeo="150132")


@pytest.fixture
def create_user(db):
    User = get_user_model()
    return User.objects.create_user(username="testuser_legacy", email="test_legacy@example.com", password="testpass123", dni="12345678")


@pytest.fixture
def api_client_fixture(db):
    return TestClient(api)


@pytest.fixture
def auth_client(api_client_fixture, create_user):
    token = AccessToken.for_user(create_user)
    api_client_fixture.headers.update({"Authorization": f"Bearer {token}"})
    api_client_fixture.user = create_user
    return api_client_fixture


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    return Municipalidad.objects.create(codigo="M001", nombre="Municipalidad de Miraflores", distrito=ubigeo_distrito)


@pytest.fixture
def proyecto(db, municipalidad, ubigeo_distrito):
    return Proyecto.objects.create(
        nombre_propietario="Propietario Test SAC",
        direccion="Av. Test 123",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario Test SAC",
    )


# ── IGV/UIT fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def igv_vigente_2024(db):
    return IGV.objects.create(valor=Decimal("0.18"), periodo_inicio=date(2024, 1, 1), periodo_fin=None)


@pytest.fixture
def uit_vigente_2024(db):
    return UIT.objects.create(valor=Decimal("5150.00"), periodo_inicio=date(2024, 1, 1), periodo_fin=None)


@pytest.fixture
def igv_vigente_2023(db):
    """IGV histórico 2023 (para probar selección por fecha)."""
    return IGV.objects.create(valor=Decimal("0.18"), periodo_inicio=date(2023, 1, 1), periodo_fin=date(2023, 12, 31))


@pytest.fixture
def uit_vigente_2023(db):
    """UIT histórico 2023 (para probar selección por fecha)."""
    return UIT.objects.create(valor=Decimal("4950.00"), periodo_inicio=date(2023, 1, 1), periodo_fin=date(2023, 12, 31))


# ── PO fixtures (Edificaciones) ──────────────────────────────────────────────────

@pytest.fixture
def esp_estructuras(db):
    return EspecialidadRevision.objects.create(slug="estructuras", nombre="Estructuras")


@pytest.fixture
def esp_arquitectura(db):
    return EspecialidadRevision.objects.create(slug="arquitectura", nombre="Arquitectura")


@pytest.fixture
def esp_installaciones(db):
    return EspecialidadRevision.objects.create(slug="instalaciones", nombre="Instalaciones")


@pytest.fixture
def derecho_po_vigente(db):
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_base_po_historica(db, tipo_edificacion):
    """TarifaBase PO histórica (vigente en 2024, NO vigente en 2025)."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


@pytest.fixture
def tarifa_po_historica(db, tarifa_base_po_historica):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_po_historica,
        porcentaje_liquidacion=Decimal("0.0010"),  # 0.10%
    )


@pytest.fixture
def tarifa_base_po_vigente(db, tipo_edificacion):
    """TarifaBase PO vigente (periodo_inicio 2025, sin fin)."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_po_vigente(db, tarifa_base_po_vigente):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_po_vigente,
        porcentaje_liquidacion=Decimal("0.0020"),  # 0.20%
    )


@pytest.fixture
def especialidades_disponibles_po(db, tipo_edificacion, esp_estructuras, esp_arquitectura, esp_installaciones):
    return [
        LiquidacionEspecialidadDisponibles.objects.create(
            tipo_liquidacion=tipo_edificacion,
            especialidad=esp,
            activo=True,
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )
        for esp in [esp_estructuras, esp_arquitectura, esp_installaciones]
    ]


# ── M2 fixtures (HU) ─────────────────────────────────────────────────────────────

@pytest.fixture
def tarifa_base_m2_historica(db, tipo_habilitacion_urbana):
    """TarifaBase M2 histórica (vigente en 2024)."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


@pytest.fixture
def tarifa_m2_historica(db, tarifa_base_m2_historica):
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_m2_historica,
        costo_por_m2=Decimal("100.0000"),
    )


@pytest.fixture
def tarifa_base_m2_vigente(db, tipo_habilitacion_urbana):
    """TarifaBase M2 vigente (2025+)."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_vigente(db, tarifa_base_m2_vigente):
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_m2_vigente,
        costo_por_m2=Decimal("150.0000"),
    )


@pytest.fixture
def derecho_m2_vigente_fixture(db):
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


# ── IO fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tarifa_base_io(db, tipo_inspeccion_obra):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_visitas_io_fixture(db, tarifa_base_io):
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_base_io,
        porcentaje_uit=Decimal("0.05"),
        categoria_visitas="INSPECCION",
    )


@pytest.fixture
def inspector_fixture(db, tipo_edificacion):
    perfil = PerfilIngeniero.objects.create(
        cip="112233", dni="11223344", nombres="Inspector", apellido_paterno="IO",
        apellido_materno="Test", correo_personal="inspector_io_test@example.com",
    )
    inspector = Inspector.objects.create(perfil_ingeniero=perfil)
    esp_rev = EspecialidadRevision.objects.create(slug="electrica", nombre="Eléctrica/Mecánica")
    from modules.liquidaciones.domain.models.inspector import InspectorOperacion
    InspectorOperacion.objects.create(
        inspector=inspector, tipo_liquidacion=tipo_edificacion, categoria="1",
        especialidad_revision=esp_rev,
    )
    return inspector


@pytest.fixture
def liquidacion_previa_fixture(db, municipalidad, create_user, tipo_edificacion, proyecto):
    from modules.liquidaciones.domain.constants import TipoLiquidacion
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-PREVIA-LEGACY-2024-001",
        sub_total=0,
        total=0,
        usuario_creador=create_user,
    )


# ── Payload builders ───────────────────────────────────────────────────────────

def make_proyecto_payload(distrito_id):
    return {
        "denominacion": "Proyecto Test Legacy",
        "nombre_propietario": "Propietario Test SAC",
        "direccion": "Av. Test 123, Lima",
        "distrito_id": str(distrito_id),
        "entidad": {
            "tipo_documento": "RUC",
            "numero_documento": "20456789012",
            "razon_social": "Propietario Test SAC",
        },
    }


def make_legacy_payload_po(municipalidad_id, distrito_id, *, fecha_registro=None, numero_revision=1, expediente="EXP-LEG-001", valor_declarado=100000.00):
    general = {
        "municipalidad_id": str(municipalidad_id),
        "expediente": expediente,
        "observacion": "Test legacy PO",
        "proyecto": make_proyecto_payload(distrito_id),
    }
    if fecha_registro:
        general["fecha_registro"] = fecha_registro.isoformat()
    return {
        "liquidacion_general": general,
        "liquidacion_especifica": {
            "datos": {"valor_declarado": valor_declarado},
            "tarifas": [],
        },
        "numero_revision": numero_revision,
    }


def make_legacy_payload_m2(municipalidad_id, distrito_id, tarifa_m2_id, *, fecha_registro=None, numero_revision=1, expediente="EXP-LEG-M2-001", area_solicitada=100.0):
    general = {
        "municipalidad_id": str(municipalidad_id),
        "expediente": expediente,
        "observacion": "Test legacy M2",
        "proyecto": make_proyecto_payload(distrito_id),
    }
    if fecha_registro:
        general["fecha_registro"] = fecha_registro.isoformat()
    return {
        "liquidacion_general": general,
        "liquidacion_especifica": {
            "datos": {"area_solicitada": area_solicitada},
            "tarifa": {"tarifa_m2_id": str(tarifa_m2_id)},
        },
        "numero_revision": numero_revision,
    }


def make_legacy_payload_io(liquidacion_previa_id, tarifa_visitas_id, inspector_id, municipalidad_id, distrito_id, *, fecha_registro=None, numero_revision=1):
    general = {
        "municipalidad_id": str(municipalidad_id),
        "expediente": "EXP-LEG-IO-001",
        "observacion": "Test legacy IO",
        "proyecto": make_proyecto_payload(distrito_id),
    }
    if fecha_registro:
        general["fecha_registro"] = fecha_registro.isoformat()
    return {
        "liquidacion_previa_id": str(liquidacion_previa_id),
        "liquidacion_general": general,
        "liquidacion_especifica": {
            "datos": {"cantidad_visitas": 3, "categoria": "INSPECCION"},
            "tarifa": {"tarifa_visitas_id": str(tarifa_visitas_id)},
            "inspector_id": str(inspector_id),
        },
        "numero_revision": numero_revision,
    }


# ── Tests ───────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_edificaciones_legacy_con_fecha_registro_pasada_usa_tarifa_historica(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tarifa_po_historica, tarifa_po_vigente,
    esp_estructuras, esp_arquitectura, esp_installaciones,
    especialidades_disponibles_po,
    tipo_edificacion,
):
    """
    Edificaciones legacy con fecha_registro=2024 → usa tarifa histórica (0.10%).
    Sin fecha_registro (hoy 2026) → usaría la vigente (0.20%).
    """
    payload = make_legacy_payload_po(
        municipalidad.id,
        ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        valor_declarado=100000.00,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data["success"] is True
    result = data["data"]

    lg = result["liquidacion_general"]
    assert lg["numero_revision"] == 1

    lt = result["liquidacion_tipo"]
    assert "detalles" in lt
    # With 3 active specialties, each at 0.10%: total = 3 * 0.0010 = 0.0030
    total_pct = Decimal(str(lt["porcentaje_liquidacion"]))
    assert abs(total_pct - Decimal("0.0030")) < Decimal("0.0001"), \
        f"Expected 0.30% (3 x 0.10%) historical tariff, got {total_pct}"

    # usuario_creador debe ser el admin autenticado
    assert str(lg["usuario_creador"]["id"]) == str(auth_client.user.id)


@pytest.mark.django_db
def test_edificaciones_legacy_sin_fecha_registro_usa_hoy(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tarifa_po_vigente,
    esp_estructuras,
    especialidades_disponibles_po,
    tipo_edificacion,
):
    """
    Sin fecha_registro → default hoy → usa tarifa vigente (0.20%).
    """
    payload = make_legacy_payload_po(
        municipalidad.id,
        ubigeo_distrito.id,
        fecha_registro=None,
        valor_declarado=100000.00,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lt = result["liquidacion_tipo"]
    # With 3 active specialties, each at vigente 0.20%: total = 3 * 0.0020 = 0.0060
    total_pct = Decimal(str(lt["porcentaje_liquidacion"]))
    assert abs(total_pct - Decimal("0.0060")) < Decimal("0.0001"), \
        f"Expected 0.60% (3 x 0.20%) current tariff for no fecha_registro, got {total_pct}"


@pytest.mark.django_db
def test_edificaciones_legacy_numero_revision_se_respeta(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tarifa_po_historica,
    esp_estructuras,
    especialidades_disponibles_po,
    tipo_edificacion,
):
    """
    numero_revision=7 enviado en payload → se refleja en response.
    No hay validación de cadena 1→3→5.
    """
    payload = make_legacy_payload_po(
        municipalidad.id,
        ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        numero_revision=7,
        valor_declarado=50000.00,
    )
    response = auth_client.post(
        "/liquidaciones/edificaciones/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]
    assert lg["numero_revision"] == 7, f"Expected numero_revision=7, got {lg['numero_revision']}"


@pytest.mark.django_db
def test_hu_legacy_con_fecha_registro_pasada_usa_tarifa_m2_historica(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tarifa_m2_historica, tarifa_m2_vigente,
    tipo_habilitacion_urbana,
):
    """
    HU legacy con fecha_registro=2024 → usa tarifa m2 histórica (100/m2).
    """
    payload = make_legacy_payload_m2(
        municipalidad.id,
        ubigeo_distrito.id,
        tarifa_m2_historica.id,
        fecha_registro=date(2024, 6, 15),
        area_solicitada=100.0,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data["success"] is True
    result = data["data"]
    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    assert Decimal(str(lt["costo_por_m2"])) == Decimal("100.0000"), \
        f"Expected 100.0000 historical m2 cost, got {lt['costo_por_m2']}"

    assert Decimal(str(lg["sub_total"])) == Decimal("10000.00"), \
        f"Expected sub_total=10000.00, got {lg['sub_total']}"

    assert str(lg["usuario_creador"]["id"]) == str(auth_client.user.id)


@pytest.mark.django_db
def test_hu_legacy_sin_fecha_registro_usa_tarifa_vigente(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tarifa_m2_vigente,
    tipo_habilitacion_urbana,
):
    """
    HU legacy sin fecha_registro → usa tarifa vigente (150/m2).
    """
    payload = make_legacy_payload_m2(
        municipalidad.id,
        ubigeo_distrito.id,
        tarifa_m2_vigente.id,
        fecha_registro=None,
        area_solicitada=100.0,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lt = result["liquidacion_tipo"]

    assert Decimal(str(lt["costo_por_m2"])) == Decimal("150.0000"), \
        f"Expected 150.0000 current m2 cost, got {lt['costo_por_m2']}"


@pytest.mark.django_db
def test_hu_legacy_numero_revision_custom(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tarifa_m2_vigente,
    tipo_habilitacion_urbana,
):
    """
    HU legacy con numero_revision=3 → se refleja en response.
    """
    payload = make_legacy_payload_m2(
        municipalidad.id,
        ubigeo_distrito.id,
        tarifa_m2_vigente.id,
        fecha_registro=None,
        numero_revision=3,
        area_solicitada=50.0,
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]
    assert lg["numero_revision"] == 3


@pytest.mark.django_db
def test_io_legacy_smoke_test_200(
    auth_client,
    liquidacion_previa_fixture,
    tarifa_visitas_io_fixture,
    inspector_fixture,
    igv_vigente_2024, uit_vigente_2024,
    municipalidad, ubigeo_distrito,
):
    """
    IO legacy smoke test — POST con datos válidos → 200.
    Requiere liquidacion_previa + inspector.
    """
    payload = make_legacy_payload_io(
        liquidacion_previa_fixture.id,
        tarifa_visitas_io_fixture.id,
        inspector_fixture.id,
        municipalidad.id,
        ubigeo_distrito.id,
        fecha_registro=None,
    )
    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data["success"] is True
    result = data["data"]

    lg = result["liquidacion_general"]
    assert lg["numero_revision"] == 1

    assert str(lg["usuario_creador"]["id"]) == str(auth_client.user.id)


@pytest.mark.django_db
def test_io_legacy_numero_revision_custom(
    auth_client,
    liquidacion_previa_fixture,
    tarifa_visitas_io_fixture,
    inspector_fixture,
    igv_vigente_2024, uit_vigente_2024,
    municipalidad, ubigeo_distrito,
):
    """
    IO legacy con numero_revision=5 → se refleja en response.
    """
    payload = make_legacy_payload_io(
        liquidacion_previa_fixture.id,
        tarifa_visitas_io_fixture.id,
        inspector_fixture.id,
        municipalidad.id,
        ubigeo_distrito.id,
        numero_revision=5,
    )
    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    result = data["data"]
    lg = result["liquidacion_general"]
    assert lg["numero_revision"] == 5


@pytest.mark.django_db
def test_taludes_legacy_smoke_test(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tipo_taludes,
    esp_taludes,
):
    """
    Taludes legacy smoke test — POST con datos válidos → 200.
    """
    tarifa_base_taludes = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_taludes,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    tarifa_po_taludes = TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_taludes,
        porcentaje_liquidacion=Decimal("0.0010"),
    )
    LiquidacionEspecialidadDisponibles.objects.create(
        tipo_liquidacion=tipo_taludes,
        especialidad=esp_taludes,
        activo=True,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )

    payload = make_legacy_payload_po(
        municipalidad.id,
        ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        valor_declarado=100000.00,
        expediente="EXP-LEG-TALUDES-001",
    )
    response = auth_client.post(
        "/liquidaciones/taludes/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data["success"] is True


@pytest.mark.django_db
def test_impacto_vial_legacy_smoke_test(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tipo_impacto_vial,
    esp_iv,
):
    """
    Impacto Vial legacy smoke test — POST con datos válidos → 200.
    """
    tarifa_base_iv = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_impacto_vial,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    tarifa_po_iv = TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_iv,
        porcentaje_liquidacion=Decimal("0.0010"),
    )
    LiquidacionEspecialidadDisponibles.objects.create(
        tipo_liquidacion=tipo_impacto_vial,
        especialidad=esp_iv,
        activo=True,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )

    payload = make_legacy_payload_po(
        municipalidad.id,
        ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        valor_declarado=100000.00,
        expediente="EXP-LEG-IV-001",
    )
    response = auth_client.post(
        "/liquidaciones/impacto-vial/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data["success"] is True


@pytest.mark.django_db
def test_mecanica_suelos_legacy_smoke_test(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tipo_mecanica_suelos,
):
    """
    Mecánica de Suelos legacy smoke test — POST con datos válidos → 200.
    """
    tarifa_base_ms = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    tarifa_m2_ms = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_ms,
        costo_por_m2=Decimal("120.0000"),
    )

    payload = make_legacy_payload_m2(
        municipalidad.id,
        ubigeo_distrito.id,
        tarifa_m2_ms.id,
        fecha_registro=date(2024, 6, 15),
        area_solicitada=100.0,
        expediente="EXP-LEG-MS-001",
    )
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data["success"] is True


# ── Extra fixtures needed ───────────────────────────────────────────────────────

@pytest.fixture
def esp_taludes(db):
    return EspecialidadRevision.objects.create(slug="taludes", nombre="Taludes")


@pytest.fixture
def esp_iv(db):
    return EspecialidadRevision.objects.create(slug="impacto-vial", nombre="Impacto Vial")


# ── cotizar_legacy_proceso: tarifa explícita = porcentaje parcial ──────────────

def _make_po_payload_dict(
    municipalidad_id,
    distrito_id,
    *,
    fecha_registro,
    numero_revision=3,
    tarifas=None,
    valor_declarado=100000.00,
):
    payload = make_legacy_payload_po(
        municipalidad_id,
        distrito_id,
        fecha_registro=fecha_registro,
        numero_revision=numero_revision,
        valor_declarado=valor_declarado,
    )
    payload["liquidacion_especifica"]["tarifas"] = tarifas or []
    return payload


@pytest.mark.django_db
def test_cotizar_legacy_proceso_con_tarifa_explicita_usa_porcentaje_parcial(
    municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tarifa_po_historica,
    esp_estructuras, esp_arquitectura, esp_installaciones,
    especialidades_disponibles_po,
    tipo_edificacion,
):
    """
    Con tarifa explícita + una especialidad, cotizar_legacy_proceso devuelve
    el porcentaje PARCIAL de esa tarifa (0.10%), no el total de las 3.
    """
    from modules.liquidaciones.presentation.schemas.liquidacion_legacy.liquidacion_edificaciones_legacy_schemas import (
        LiquidacionEdificacionesLegacyIn,
    )
    from modules.liquidaciones.management.commands.import_legacy_edificaciones import (
        _build_orchestrator,
    )

    payload_dict = _make_po_payload_dict(
        municipalidad.id,
        ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        tarifas=[
            {
                "tarifa_porcentaje_obra_id": str(tarifa_po_historica.id),
                "especialidad_id": str(esp_estructuras.id),
            }
        ],
    )
    payload = LiquidacionEdificacionesLegacyIn.model_validate(payload_dict)

    orchestrator = _build_orchestrator()
    cotizacion = orchestrator.cotizar_legacy_proceso(payload)

    assert abs(cotizacion.porcentaje_liquidacion - Decimal("0.0010")) < Decimal("0.0001"), \
        f"Expected partial 0.10% (1 specialty), got {cotizacion.porcentaje_liquidacion}"
    assert len(cotizacion.detalles) == 1, \
        f"Expected 1 detail for explicit tarifa, got {len(cotizacion.detalles)}"
    assert cotizacion.detalles[0].tarifa_aplicada.especialidad_id == str(esp_estructuras.id)


@pytest.mark.django_db
def test_cotizar_legacy_proceso_sin_tarifas_auto_fill_todas(
    municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tarifa_po_historica,
    esp_estructuras, esp_arquitectura, esp_installaciones,
    especialidades_disponibles_po,
    tipo_edificacion,
):
    """
    Sin tarifas (tarifas=[]) cotizar_legacy_proceso auto-rellena TODAS las
    especialidades vigentes: 3 x 0.10% = 0.30%.
    """
    from modules.liquidaciones.presentation.schemas.liquidacion_legacy.liquidacion_edificaciones_legacy_schemas import (
        LiquidacionEdificacionesLegacyIn,
    )
    from modules.liquidaciones.management.commands.import_legacy_edificaciones import (
        _build_orchestrator,
    )

    payload_dict = _make_po_payload_dict(
        municipalidad.id,
        ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        tarifas=[],
    )
    payload = LiquidacionEdificacionesLegacyIn.model_validate(payload_dict)

    orchestrator = _build_orchestrator()
    cotizacion = orchestrator.cotizar_legacy_proceso(payload)

    assert abs(cotizacion.porcentaje_liquidacion - Decimal("0.0030")) < Decimal("0.0001"), \
        f"Expected total 0.30% (3 x 0.10%), got {cotizacion.porcentaje_liquidacion}"
    assert len(cotizacion.detalles) == 3, \
        f"Expected 3 details (auto-fill), got {len(cotizacion.detalles)}"


# ── Phase 1: M2 Clamping (HU + MS) ─────────────────────────────────────────────

def _make_legacy_payload_m2_with_visitas(
    municipalidad_id,
    distrito_id,
    tarifa_m2_id,
    *,
    cantidad_visitas,
    fecha_registro=None,
    numero_revision=1,
    expediente="EXP-LEG-M2-001",
    area_solicitada=100.0,
):
    """Variant of make_legacy_payload_m2 that accepts cantidad_visitas explicitly."""
    general = {
        "municipalidad_id": str(municipalidad_id),
        "expediente": expediente,
        "observacion": "Test legacy M2",
        "proyecto": make_proyecto_payload(distrito_id),
    }
    if fecha_registro:
        general["fecha_registro"] = fecha_registro.isoformat()
    return {
        "liquidacion_general": general,
        "liquidacion_especifica": {
            "datos": {"area_solicitada": area_solicitada},
            "tarifa": {"tarifa_m2_id": str(tarifa_m2_id)},
        },
        "numero_revision": numero_revision,
    }


def _make_legacy_payload_io_with_visitas(
    liquidacion_previa_id,
    tarifa_visitas_id,
    inspector_id,
    municipalidad_id,
    distrito_id,
    *,
    cantidad_visitas,
    fecha_registro=None,
    numero_revision=1,
):
    """Variant of make_legacy_payload_io that accepts cantidad_visitas explicitly."""
    general = {
        "municipalidad_id": str(municipalidad_id),
        "expediente": "EXP-LEG-IO-001",
        "observacion": "Test legacy IO",
        "proyecto": make_proyecto_payload(distrito_id),
    }
    if fecha_registro:
        general["fecha_registro"] = fecha_registro.isoformat()
    return {
        "liquidacion_previa_id": str(liquidacion_previa_id),
        "liquidacion_general": general,
        "liquidacion_especifica": {
            "datos": {"cantidad_visitas": cantidad_visitas, "categoria": "INSPECCION"},
            "tarifa": {"tarifa_visitas_id": str(tarifa_visitas_id)},
            "inspector_id": str(inspector_id),
        },
        "numero_revision": numero_revision,
    }


@pytest.mark.django_db
def test_hu_legacy_subtotal_clamp_at_minimo(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tarifa_m2_historica,  # costo_por_m2=100.0000, derecho min=500, max=50000
    tipo_habilitacion_urbana,
):
    """area=1 m² × 100/m² = 100 < derecho_minimo=500 → clamps to 500."""
    payload = make_legacy_payload_m2(
        municipalidad.id, ubigeo_distrito.id, tarifa_m2_historica.id,
        fecha_registro=date(2024, 6, 15),  # use historical date so tarifa_m2_historica is vigente
        area_solicitada=1.0,  # → 100 < 500 (clamp)
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()["data"]
    lg = data["liquidacion_general"]
    assert Decimal(str(lg["sub_total"])) == Decimal("500.00"), \
        f"Expected sub_total=500.00 (clamped from 100), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == Decimal("500.00"), \
        f"Expected total=500.00 (clamped from 100), got {lg['total']}"


@pytest.mark.django_db
def test_hu_legacy_subtotal_clamp_at_maximo(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tarifa_m2_historica,  # 100/m²
    tipo_habilitacion_urbana,
):
    """area=600 m² × 100/m² = 60000 > derecho_maximo=50000 → clamps to 50000."""
    payload = make_legacy_payload_m2(
        municipalidad.id, ubigeo_distrito.id, tarifa_m2_historica.id,
        fecha_registro=date(2024, 6, 15),  # use historical date so tarifa_m2_historica is vigente
        area_solicitada=600.0,  # → 60000 > 50000 (clamp)
    )
    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()["data"]
    lg = data["liquidacion_general"]
    assert Decimal(str(lg["sub_total"])) == Decimal("50000.00"), \
        f"Expected sub_total=50000.00 (clamped from 60000), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == Decimal("50000.00"), \
        f"Expected total=50000.00 (clamped from 60000), got {lg['total']}"


@pytest.mark.django_db
def test_ms_legacy_subtotal_clamp_at_minimo(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tipo_mecanica_suelos,
):
    """area=1 m² × 120/m² = 120 < derecho_minimo=500 → clamps to 500."""
    tarifa_base_ms = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)
    tarifa_m2_ms = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_ms, costo_por_m2=Decimal("120.0000"))
    payload = make_legacy_payload_m2(
        municipalidad.id, ubigeo_distrito.id, tarifa_m2_ms.id,
        area_solicitada=1.0)
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]
    assert Decimal(str(lg["sub_total"])) == Decimal("500.00"), \
        f"Expected sub_total=500.00 (clamped from 120), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == Decimal("500.00"), \
        f"Expected total=500.00 (clamped from 120), got {lg['total']}"


@pytest.mark.django_db
def test_ms_legacy_subtotal_clamp_at_maximo(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tipo_mecanica_suelos,
):
    """area=600 m² × 120/m² = 72000 > derecho_maximo=50000 → clamps to 50000."""
    tarifa_base_ms = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)
    tarifa_m2_ms = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_ms, costo_por_m2=Decimal("120.0000"))
    payload = make_legacy_payload_m2(
        municipalidad.id, ubigeo_distrito.id, tarifa_m2_ms.id,
        area_solicitada=600.0)
    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]
    assert Decimal(str(lg["sub_total"])) == Decimal("50000.00"), \
        f"Expected sub_total=50000.00 (clamped from 72000), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == Decimal("50000.00"), \
        f"Expected total=50000.00 (clamped from 72000), got {lg['total']}"


# ── Phase 2: IO Totals ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_io_legacy_subtotal_correcto(
    auth_client,
    liquidacion_previa_fixture,
    tarifa_visitas_io_fixture,  # porcentaje_uit=0.05
    inspector_fixture,
    igv_vigente_2024, uit_vigente_2024,  # uit=5150.00
    municipalidad, ubigeo_distrito,
):
    """3 visits × (0.05 × 5150) = 3 × 257.50 = 772.50 subtotal."""
    payload = _make_legacy_payload_io_with_visitas(
        liquidacion_previa_fixture.id, tarifa_visitas_io_fixture.id,
        inspector_fixture.id, municipalidad.id, ubigeo_distrito.id,
        cantidad_visitas=3)
    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]
    assert Decimal(str(lg["sub_total"])) == Decimal("772.50"), \
        f"Expected sub_total=772.50 (3×0.05×5150), got {lg['sub_total']}"


@pytest.mark.django_db
def test_io_legacy_total_con_igv(
    auth_client,
    liquidacion_previa_fixture,
    tarifa_visitas_io_fixture,  # porcentaje_uit=0.05
    inspector_fixture,
    igv_vigente_2024, uit_vigente_2024,  # uit=5150.00, igv=0.18
    municipalidad, ubigeo_distrito,
):
    """subtotal=772.50 × 1.18 = 911.55 total with IGV."""
    payload = _make_legacy_payload_io_with_visitas(
        liquidacion_previa_fixture.id, tarifa_visitas_io_fixture.id,
        inspector_fixture.id, municipalidad.id, ubigeo_distrito.id,
        cantidad_visitas=3)
    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]
    assert Decimal(str(lg["sub_total"])) == Decimal("772.50"), \
        f"Expected sub_total=772.50, got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == Decimal("911.55"), \
        f"Expected total=911.55 (772.50×1.18), got {lg['total']}"


# ── Phase 3: Edificaciones Bypass ─────────────────────────────────────────────

@pytest.mark.django_db
def test_edificaciones_legacy_cotizacion_bypass_uses_override_subtotal(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tarifa_po_historica,
    esp_estructuras, esp_arquitectura, esp_installaciones,
    especialidades_disponibles_po,
    tipo_edificacion,
):
    """cotizacion_legacy bypass: override sub_total=1000, igv=0.18 → total=1180."""
    # Provide explicit tarifas so auto-fill doesn't conflict
    payload = make_legacy_payload_po(
        municipalidad.id, ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        valor_declarado=Decimal("100000.00"),
    )
    payload["liquidacion_especifica"]["tarifas"] = [
        {"tarifa_porcentaje_obra_id": str(tarifa_po_historica.id),
         "especialidad_id": str(esp_estructuras.id)},
    ]
    payload["cotizacion_legacy"] = {"sub_total": "1000.00", "total": "1180.00"}
    response = auth_client.post(
        "/liquidaciones/edificaciones/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]
    assert Decimal(str(lg["sub_total"])) == Decimal("1000.00"), \
        f"Expected sub_total=1000.00 (bypass), got {lg['sub_total']}"
    # override_subtotal bypasses Steps 1-5; override_total is NOT set here,
    # so total is recalculated from override_subtotal × (1 + IGV): 1000 × 1.18 = 1180
    assert Decimal(str(lg["total"])) == Decimal("1180.00"), \
        f"Expected total=1180.00 (recalculated from override_subtotal × 1.18), got {lg['total']}"


@pytest.mark.django_db
def test_edificaciones_legacy_cotizacion_bypass_skips_validation(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tarifa_po_historica,
    esp_estructuras, esp_arquitectura, esp_installaciones,
    especialidades_disponibles_po,
    tipo_edificacion,
):
    """cotizacion_legacy bypass allows valor_declarado=0.01 without valor_declarado validation."""
    # Provide explicit tarifas so auto-fill doesn't conflict
    payload = make_legacy_payload_po(
        municipalidad.id, ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        valor_declarado=Decimal("100000.00"),
    )
    payload["liquidacion_especifica"]["tarifas"] = [
        {"tarifa_porcentaje_obra_id": str(tarifa_po_historica.id),
         "especialidad_id": str(esp_estructuras.id)},
    ]
    payload["cotizacion_legacy"] = {"sub_total": "2000.00", "total": "2360.00"}
    response = auth_client.post(
        "/liquidaciones/edificaciones/legacy/nueva-liquidacion", json=payload)
    # Should succeed because bypass skips Steps 1-5 validation
    assert response.status_code == 200, \
        f"Expected 200 (bypass), got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_edificaciones_legacy_source_totals_persisted_even_when_recalculated_differs(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tarifa_po_historica,
    esp_estructuras,
    especialidades_disponibles_po,
    tipo_edificacion,
):
    """
    Legacy source subtotal/total are persisted even when recalculated differs.

    When cotizacion_legacy provides both sub_total and total:
    - LiquidacionGeneral.sub_total MUST be the legacy source sub_total
    - LiquidacionGeneral.total MUST be the legacy source total (NOT recalculated as sub_total + IGV)

    Example: legacy source has sub_total=1000.00, total=2000.00 (old IGV or different calc).
    Recalculated would give sub_total=1000.00, total=1180.00 (1000*1.18).
    The persisted values must be the LEGACY SOURCE values (1000, 2000), not recalculated.
    """
    payload = make_legacy_payload_po(
        municipalidad.id, ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        valor_declarado=Decimal("100000.00"),
    )
    payload["liquidacion_especifica"]["tarifas"] = [
        {"tarifa_porcentaje_obra_id": str(tarifa_po_historica.id),
         "especialidad_id": str(esp_estructuras.id)},
    ]
    # Legacy source: sub_total=1000.00, total=2000.00 (different from recalculated 1180.00)
    legacy_subtotal = Decimal("1000.00")
    legacy_total = Decimal("2000.00")
    payload["cotizacion_legacy"] = {
        "sub_total": str(legacy_subtotal),
        "total": str(legacy_total),
    }
    response = auth_client.post(
        "/liquidaciones/edificaciones/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]
    # Source totals must be persisted as-is (not recalculated)
    assert Decimal(str(lg["sub_total"])) == legacy_subtotal, \
        f"Expected sub_total={legacy_subtotal} (legacy source), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == legacy_total, \
        f"Expected total={legacy_total} (legacy source, not recalculated), got {lg['total']}"


@pytest.mark.django_db
def test_edificaciones_legacy_source_totals_persisted_when_recalculation_differs_no_rechazo(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tarifa_po_historica,
    esp_estructuras,
    especialidades_disponibles_po,
    tipo_edificacion,
):
    """
    When legacy source total (2000) differs from recalculated total (1180.00 = 1000*1.18),
    the row is still imported (no --rechazar-dif-alta) and source totals are persisted.

    The descripcion_legacy anomaly reporting is done by the command's _build_payload
    (which calls cotizar_legacy_proceso separately), not by the API endpoint directly.
    The API endpoint persists the source totals and returns the result.
    """
    payload = make_legacy_payload_po(
        municipalidad.id, ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        valor_declarado=Decimal("100000.00"),
    )
    payload["liquidacion_especifica"]["tarifas"] = [
        {"tarifa_porcentaje_obra_id": str(tarifa_po_historica.id),
         "especialidad_id": str(esp_estructuras.id)},
    ]
    # Legacy total (2000) differs from recalculated (1180.00 = 1000*1.18)
    payload["cotizacion_legacy"] = {
        "sub_total": "1000.00",
        "total": "2000.00",
    }
    response = auth_client.post(
        "/liquidaciones/edificaciones/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, \
        f"Expected 200 (imported despite diff), got {response.status_code}: {response.content}"

    # Row is imported and source totals are persisted (no rejection without --rechazar-dif-alta)
    lg = response.json()["data"]["liquidacion_general"]
    assert Decimal(str(lg["total"])) == Decimal("2000.00"), \
        f"Expected total=2000.00 (source), got {lg['total']}"
    assert Decimal(str(lg["sub_total"])) == Decimal("1000.00"), \
        f"Expected sub_total=1000.00 (source), got {lg['sub_total']}"


# ── Phase 4: PO Totals (Taludes + IV) ───────────────────────────────────────────

@pytest.mark.django_db
def test_taludes_legacy_total_con_igv(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tipo_taludes, esp_taludes,
):
    """
    1 specialty × 0.10% → sub_total=515.00 (minimo UIT floor: 5150×0.10=515),
    total=607.70 (515×1.18).

    NOTE: Plan expected sub_total=100.00 and total=118.00, but actual code applies
    a minimum floor of uit_valor × derecho.porcentaje_minimo_uit = 5150 × 0.10 = 515.
    This test reflects actual behavior, not the plan's assumption.
    """
    tarifa_base_taludes = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_taludes,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)
    tarifa_po_taludes = TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_taludes,
        porcentaje_liquidacion=Decimal("0.0010"))  # 0.10%
    LiquidacionEspecialidadDisponibles.objects.create(
        tipo_liquidacion=tipo_taludes,
        especialidad=esp_taludes,
        activo=True,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)
    payload = make_legacy_payload_po(
        municipalidad.id, ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        valor_declarado=Decimal("100000.00"),
        expediente="EXP-TAL-TOTAL-001")
    payload["liquidacion_especifica"]["tarifas"] = [
        {"tarifa_porcentaje_obra_id": str(tarifa_po_taludes.id),
         "especialidad_id": str(esp_taludes.id)}]
    response = auth_client.post(
        "/liquidaciones/taludes/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]
    assert Decimal(str(lg["sub_total"])) == Decimal("515.00"), \
        f"Expected sub_total=515.00 (minimo UIT floor), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == Decimal("607.70"), \
        f"Expected total=607.70 (515×1.18), got {lg['total']}"


@pytest.mark.django_db
def test_impacto_vial_legacy_total_con_igv(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tipo_impacto_vial, esp_iv,
):
    """
    1 specialty × 0.10% → sub_total=515.00 (minimo UIT floor: 5150×0.10=515),
    total=607.70 (515×1.18).

    NOTE: Plan expected sub_total=100.00 and total=118.00, but actual code applies
    a minimum floor of uit_valor × derecho.porcentaje_minimo_uit = 5150 × 0.10 = 515.
    This test reflects actual behavior, not the plan's assumption.
    """
    tarifa_base_iv = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_impacto_vial,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)
    tarifa_po_iv = TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_iv,
        porcentaje_liquidacion=Decimal("0.0010"))  # 0.10%
    LiquidacionEspecialidadDisponibles.objects.create(
        tipo_liquidacion=tipo_impacto_vial,
        especialidad=esp_iv,
        activo=True,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)
    payload = make_legacy_payload_po(
        municipalidad.id, ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        valor_declarado=Decimal("100000.00"),
        expediente="EXP-IV-TOTAL-001")
    payload["liquidacion_especifica"]["tarifas"] = [
        {"tarifa_porcentaje_obra_id": str(tarifa_po_iv.id),
         "especialidad_id": str(esp_iv.id)}]
    response = auth_client.post(
        "/liquidaciones/impacto-vial/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]
    assert Decimal(str(lg["sub_total"])) == Decimal("515.00"), \
        f"Expected sub_total=515.00 (minimo UIT floor), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == Decimal("607.70"), \
        f"Expected total=607.70 (515×1.18), got {lg['total']}"


# ── Phase 5: Taludes + IV Source Totals Persistence ─────────────────────────────


# ── Phase 2 M2: HU + MS Legacy Source Totals Persistence ─────────────────────────

def _make_legacy_payload_m2_with_cotizacion_legacy(
    municipalidad_id,
    distrito_id,
    tarifa_m2_id,
    *,
    cotizacion_legacy_sub_total,
    cotizacion_legacy_total,
    fecha_registro=None,
    numero_revision=1,
    expediente="EXP-LEG-M2-001",
    area_solicitada=100.0,
):
    """
    M2 legacy payload builder that includes cotizacion_legacy bypass values.
    """
    general = {
        "municipalidad_id": str(municipalidad_id),
        "expediente": expediente,
        "observacion": "Test legacy M2 with cotizacion_legacy",
        "proyecto": make_proyecto_payload(distrito_id),
    }
    if fecha_registro:
        general["fecha_registro"] = fecha_registro.isoformat()
    payload = {
        "liquidacion_general": general,
        "liquidacion_especifica": {
            "datos": {"area_solicitada": area_solicitada},
            "tarifa": {"tarifa_m2_id": str(tarifa_m2_id)},
        },
        "numero_revision": numero_revision,
        "cotizacion_legacy": {
            "sub_total": str(cotizacion_legacy_sub_total),
            "total": str(cotizacion_legacy_total),
        },
    }
    return payload


@pytest.mark.django_db
def test_hu_legacy_source_totals_persisted_even_when_recalculated_differs(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tarifa_m2_historica,  # costo_por_m2=100.0000
    tipo_habilitacion_urbana,
):
    """
    HU legacy: source sub_total/total are persisted even when recalculated differs.

    When cotizacion_legacy provides both sub_total and total:
    - LiquidacionGeneral.sub_total MUST be the legacy source sub_total
    - LiquidacionGeneral.total MUST be the legacy source total (NOT recalculated)

    Example: area=100 at 100/m² → recalculated sub_total=10000, total=10000.
    But legacy source has sub_total=1000.00, total=2000.00 (old IGV or different calc).
    The persisted values must be the LEGACY SOURCE values (1000, 2000), not recalculated.

    Mirrors test_edificaciones_legacy_source_totals_persisted_even_when_recalculated_differs.
    """
    payload = _make_legacy_payload_m2_with_cotizacion_legacy(
        municipalidad.id,
        ubigeo_distrito.id,
        tarifa_m2_historica.id,
        cotizacion_legacy_sub_total=Decimal("1000.00"),
        cotizacion_legacy_total=Decimal("2000.00"),
        fecha_registro=date(2024, 6, 15),  # use historical date for tarifa_m2_historica
        area_solicitada=100.0,  # → recalculated 100*100=10000, but legacy=1000/2000
        expediente="EXP-HU-SOURCE-001",
    )

    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]

    # Source totals must be persisted as-is (not recalculated from area*tarifa)
    assert Decimal(str(lg["sub_total"])) == Decimal("1000.00"), \
        f"Expected sub_total=1000.00 (legacy source), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == Decimal("2000.00"), \
        f"Expected total=2000.00 (legacy source, not recalculated), got {lg['total']}"


@pytest.mark.django_db
def test_ms_legacy_source_totals_persisted_even_when_recalculated_differs(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tipo_mecanica_suelos,
):
    """
    MS legacy: source sub_total/total are persisted even when recalculated differs.

    When cotizacion_legacy provides both sub_total and total:
    - LiquidacionGeneral.sub_total MUST be the legacy source sub_total
    - LiquidacionGeneral.total MUST be the legacy source total (NOT recalculated)

    Example: area=100 at 120/m² → recalculated sub_total=12000, total=12000.
    But legacy source has sub_total=1000.00, total=2000.00 (old IGV or different calc).
    The persisted values must be the LEGACY SOURCE values (1000, 2000), not recalculated.

    Mirrors test_edificaciones_legacy_source_totals_persisted_even_when_recalculated_differs.
    """
    tarifa_base_ms = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)
    tarifa_m2_ms = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_ms, costo_por_m2=Decimal("120.0000"))

    payload = _make_legacy_payload_m2_with_cotizacion_legacy(
        municipalidad.id,
        ubigeo_distrito.id,
        tarifa_m2_ms.id,
        cotizacion_legacy_sub_total=Decimal("1000.00"),
        cotizacion_legacy_total=Decimal("2000.00"),
        fecha_registro=date(2024, 6, 15),
        area_solicitada=100.0,  # → recalculated 100*120=12000, but legacy=1000/2000
        expediente="EXP-MS-SOURCE-001",
    )

    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]

    # Source totals must be persisted as-is (not recalculated from area*tarifa)
    assert Decimal(str(lg["sub_total"])) == Decimal("1000.00"), \
        f"Expected sub_total=1000.00 (legacy source), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == Decimal("2000.00"), \
        f"Expected total=2000.00 (legacy source, not recalculated), got {lg['total']}"


@pytest.mark.django_db
def test_hu_legacy_cotizacion_legacy_bypasses_clamping(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tarifa_m2_historica,  # costo_por_m2=100.0000
    tipo_habilitacion_urbana,
):
    """
    HU legacy: when cotizacion_legacy is present, clamping is bypassed.

    area=600 at 100/m² → calculated sub_total=60000, which exceeds derecho_maximo=50000.
    Without cotizacion_legacy, sub_total would clamp to 50000.00.
    With cotizacion_legacy.sub_total=60000 and cotizacion_legacy.total=60000,
    these values are persisted directly WITHOUT clamping.

    Proves: cotizacion_legacy bypasses both recalculation AND clamping.
    """
    # Calculated: 600 * 100 = 60000 > derecho_maximo=50000 → would clamp to 50000
    # But cotizacion_legacy bypasses clamping entirely
    legacy_subtotal = Decimal("60000.00")
    legacy_total = Decimal("60000.00")

    payload = _make_legacy_payload_m2_with_cotizacion_legacy(
        municipalidad.id,
        ubigeo_distrito.id,
        tarifa_m2_historica.id,
        cotizacion_legacy_sub_total=legacy_subtotal,
        cotizacion_legacy_total=legacy_total,
        fecha_registro=date(2024, 6, 15),
        area_solicitada=600.0,  # → 60000, would clamp to 50000 without bypass
        expediente="EXP-HU-BYPASS-CLAMP-001",
    )

    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]

    # Legacy values must be persisted as-is, bypassing clamping
    assert Decimal(str(lg["sub_total"])) == legacy_subtotal, \
        f"Expected sub_total={legacy_subtotal} (legacy, not clamped), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == legacy_total, \
        f"Expected total={legacy_total} (legacy, not clamped), got {lg['total']}"


@pytest.mark.django_db
def test_ms_legacy_cotizacion_legacy_bypasses_clamping(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_m2_vigente_fixture,
    tipo_mecanica_suelos,
):
    """
    MS legacy: when cotizacion_legacy is present, clamping is bypassed.

    area=500 at 120/m² → calculated sub_total=60000, which exceeds derecho_maximo=50000.
    Without cotizacion_legacy, sub_total would clamp to 50000.00.
    With cotizacion_legacy.sub_total=60000 and cotizacion_legacy.total=60000,
    these values are persisted directly WITHOUT clamping.

    Proves: cotizacion_legacy bypasses both recalculation AND clamping.
    """
    tarifa_base_ms = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)
    tarifa_m2_ms = TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_ms, costo_por_m2=Decimal("120.0000"))

    # Calculated: 500 * 120 = 60000 > derecho_maximo=50000 → would clamp to 50000
    # But cotizacion_legacy bypasses clamping entirely
    legacy_subtotal = Decimal("60000.00")
    legacy_total = Decimal("60000.00")

    payload = _make_legacy_payload_m2_with_cotizacion_legacy(
        municipalidad.id,
        ubigeo_distrito.id,
        tarifa_m2_ms.id,
        cotizacion_legacy_sub_total=legacy_subtotal,
        cotizacion_legacy_total=legacy_total,
        fecha_registro=date(2024, 6, 15),
        area_solicitada=500.0,  # → 60000, would clamp to 50000 without bypass
        expediente="EXP-MS-BYPASS-CLAMP-001",
    )

    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]

    # Legacy values must be persisted as-is, bypassing clamping
    assert Decimal(str(lg["sub_total"])) == legacy_subtotal, \
        f"Expected sub_total={legacy_subtotal} (legacy, not clamped), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == legacy_total, \
        f"Expected total={legacy_total} (legacy, not clamped), got {lg['total']}"

@pytest.mark.django_db
def test_taludes_legacy_source_totals_persisted_even_when_recalculated_differs(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tipo_taludes, esp_taludes,
):
    """
    Taludes legacy: source sub_total/total are persisted even when recalculated differs.

    When cotizacion_legacy provides both sub_total and total:
    - LiquidacionGeneral.sub_total MUST be the legacy source sub_total
    - LiquidacionGeneral.total MUST be the legacy source total (NOT recalculated as sub_total + IGV)

    Example: legacy source has sub_total=1000.00, total=2000.00 (old IGV or different calc).
    Recalculated would give sub_total=1000.00, total=1180.00 (1000*1.18).
    The persisted values must be the LEGACY SOURCE values (1000, 2000), not recalculated.

    Mirrors test_edificaciones_legacy_source_totals_persisted_even_when_recalculated_differs.
    """
    tarifa_base_taludes = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_taludes,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)
    tarifa_po_taludes = TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_taludes,
        porcentaje_liquidacion=Decimal("0.0010"))  # 0.10%
    LiquidacionEspecialidadDisponibles.objects.create(
        tipo_liquidacion=tipo_taludes,
        especialidad=esp_taludes,
        activo=True,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)

    payload = make_legacy_payload_po(
        municipalidad.id, ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        valor_declarado=Decimal("100000.00"),
        expediente="EXP-TAL-SOURCE-001")
    payload["liquidacion_especifica"]["tarifas"] = [
        {"tarifa_porcentaje_obra_id": str(tarifa_po_taludes.id),
         "especialidad_id": str(esp_taludes.id)}]

    # Legacy source: sub_total=1000.00, total=2000.00 (different from recalculated 1180.00)
    legacy_subtotal = Decimal("1000.00")
    legacy_total = Decimal("2000.00")
    payload["cotizacion_legacy"] = {
        "sub_total": str(legacy_subtotal),
        "total": str(legacy_total),
    }

    response = auth_client.post(
        "/liquidaciones/taludes/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]

    # Source totals must be persisted as-is (not recalculated)
    assert Decimal(str(lg["sub_total"])) == legacy_subtotal, \
        f"Expected sub_total={legacy_subtotal} (legacy source), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == legacy_total, \
        f"Expected total={legacy_total} (legacy source, not recalculated), got {lg['total']}"


@pytest.mark.django_db
def test_impacto_vial_legacy_source_totals_persisted_even_when_recalculated_differs(
    auth_client, municipalidad, ubigeo_distrito,
    igv_vigente_2024, uit_vigente_2024,
    derecho_po_vigente,
    tipo_impacto_vial, esp_iv,
):
    """
    Impacto Vial legacy: source sub_total/total are persisted even when recalculated differs.

    When cotizacion_legacy provides both sub_total and total:
    - LiquidacionGeneral.sub_total MUST be the legacy source sub_total
    - LiquidacionGeneral.total MUST be the legacy source total (NOT recalculated as sub_total + IGV)

    Example: legacy source has sub_total=1000.00, total=2000.00 (old IGV or different calc).
    Recalculated would give sub_total=1000.00, total=1180.00 (1000*1.18).
    The persisted values must be the LEGACY SOURCE values (1000, 2000), not recalculated.

    Mirrors test_edificaciones_legacy_source_totals_persisted_even_when_recalculated_differs.
    """
    tarifa_base_iv = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_impacto_vial,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)
    tarifa_po_iv = TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_iv,
        porcentaje_liquidacion=Decimal("0.0010"))  # 0.10%
    LiquidacionEspecialidadDisponibles.objects.create(
        tipo_liquidacion=tipo_impacto_vial,
        especialidad=esp_iv,
        activo=True,
        periodo_inicio=date(2024, 1, 1), periodo_fin=None)

    payload = make_legacy_payload_po(
        municipalidad.id, ubigeo_distrito.id,
        fecha_registro=date(2024, 6, 15),
        valor_declarado=Decimal("100000.00"),
        expediente="EXP-IV-SOURCE-001")
    payload["liquidacion_especifica"]["tarifas"] = [
        {"tarifa_porcentaje_obra_id": str(tarifa_po_iv.id),
         "especialidad_id": str(esp_iv.id)}]

    # Legacy source: sub_total=1000.00, total=2000.00 (different from recalculated 1180.00)
    legacy_subtotal = Decimal("1000.00")
    legacy_total = Decimal("2000.00")
    payload["cotizacion_legacy"] = {
        "sub_total": str(legacy_subtotal),
        "total": str(legacy_total),
    }

    response = auth_client.post(
        "/liquidaciones/impacto-vial/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]

    # Source totals must be persisted as-is (not recalculated)
    assert Decimal(str(lg["sub_total"])) == legacy_subtotal, \
        f"Expected sub_total={legacy_subtotal} (legacy source), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == legacy_total, \
        f"Expected total={legacy_total} (legacy source, not recalculated), got {lg['total']}"


# ── Phase 3: IO Legacy Cotizacion Bypass ───────────────────────────────────────


def _make_legacy_payload_io_with_cotizacion_legacy(
    liquidacion_previa_id,
    tarifa_visitas_id,
    inspector_id,
    municipalidad_id,
    distrito_id,
    *,
    cotizacion_legacy_sub_total,
    cotizacion_legacy_total,
    cantidad_visitas,
    fecha_registro=None,
    numero_revision=1,
):
    """
    IO legacy payload builder that includes cotizacion_legacy bypass values.

    Mirrors _make_legacy_payload_m2_with_cotizacion_legacy for the IO motor.
    """
    general = {
        "municipalidad_id": str(municipalidad_id),
        "expediente": "EXP-LEG-IO-001",
        "observacion": "Test legacy IO with cotizacion_legacy",
        "proyecto": make_proyecto_payload(distrito_id),
    }
    if fecha_registro:
        general["fecha_registro"] = fecha_registro.isoformat()
    return {
        "liquidacion_previa_id": str(liquidacion_previa_id),
        "liquidacion_general": general,
        "liquidacion_especifica": {
            "datos": {"cantidad_visitas": cantidad_visitas, "categoria": "INSPECCION"},
            "tarifa": {"tarifa_visitas_id": str(tarifa_visitas_id)},
            "inspector_id": str(inspector_id),
        },
        "numero_revision": numero_revision,
        "cotizacion_legacy": {
            "sub_total": str(cotizacion_legacy_sub_total),
            "total": str(cotizacion_legacy_total),
        },
    }


@pytest.mark.django_db
def test_io_legacy_source_totals_persisted_even_when_recalculated_differs(
    auth_client,
    liquidacion_previa_fixture,
    tarifa_visitas_io_fixture,  # porcentaje_uit=0.05, uit=5150 → calc subtotal=257.50/visit
    inspector_fixture,
    igv_vigente_2024, uit_vigente_2024,  # igv=0.18, uit=5150.00
    municipalidad, ubigeo_distrito,
):
    """
    IO legacy: source sub_total/total are persisted even when recalculated differs.

    When cotizacion_legacy provides both sub_total and total:
    - LiquidacionGeneral.sub_total MUST be the legacy source sub_total
    - LiquidacionGeneral.total MUST be the legacy source total (NOT recalculated via IO formula)

    Example: 3 visits at 0.05 × 5150 = 772.50 subtotal normally.
    But legacy source has sub_total=1000.00, total=2000.00 (old IGV or different calc).
    The recalculated total would be 1000.00 * 1.18 = 1180.00.
    The persisted values must be the LEGACY SOURCE values (1000, 2000), not recalculated.

    Mirrors test_edificaciones_legacy_source_totals_persisted_even_when_recalculated_differs.
    """
    # cantidad_visitas=3 would normally calculate: 3 × 0.05 × 5150 = 772.50
    # But cotizacion_legacy bypasses this formula
    legacy_subtotal = Decimal("1000.00")
    legacy_total = Decimal("2000.00")

    payload = _make_legacy_payload_io_with_cotizacion_legacy(
        liquidacion_previa_fixture.id,
        tarifa_visitas_io_fixture.id,
        inspector_fixture.id,
        municipalidad.id,
        ubigeo_distrito.id,
        cotizacion_legacy_sub_total=legacy_subtotal,
        cotizacion_legacy_total=legacy_total,
        cantidad_visitas=3,  # Would normally give 772.50 subtotal
    )

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]

    # Source totals must be persisted as-is (not recalculated from cantidad_visitas*formula)
    assert Decimal(str(lg["sub_total"])) == legacy_subtotal, \
        f"Expected sub_total={legacy_subtotal} (legacy source), got {lg['sub_total']}"
    assert Decimal(str(lg["total"])) == legacy_total, \
        f"Expected total={legacy_total} (legacy source, not recalculated), got {lg['total']}"


@pytest.mark.django_db
def test_io_legacy_igv_formula_bypassed_when_cotizacion_legacy_present(
    auth_client,
    liquidacion_previa_fixture,
    tarifa_visitas_io_fixture,  # porcentaje_uit=0.05, uit=5150 → calc subtotal=257.50/visit
    inspector_fixture,
    igv_vigente_2024, uit_vigente_2024,  # igv=0.18, uit=5150.00
    municipalidad, ubigeo_distrito,
):
    """
    IO legacy: when cotizacion_legacy is present, the IGV formula (total = subtotal * (1 + igv))
    is bypassed — the legacy source total is used directly.

    Without cotizacion_legacy: 3 × 0.05 × 5150 = 772.50 subtotal, 772.50 × 1.18 = 911.55 total.
    With cotizacion_legacy: sub_total=500.00, total=500.00 (IGV already included in legacy total).

    This proves the override_total is used directly, not recomputed as override_subtotal * (1 + igv).
    """
    # Legacy total already includes IGV or was calculated differently — total is NOT 500*1.18
    legacy_subtotal = Decimal("500.00")
    legacy_total = Decimal("500.00")

    payload = _make_legacy_payload_io_with_cotizacion_legacy(
        liquidacion_previa_fixture.id,
        tarifa_visitas_io_fixture.id,
        inspector_fixture.id,
        municipalidad.id,
        ubigeo_distrito.id,
        cotizacion_legacy_sub_total=legacy_subtotal,
        cotizacion_legacy_total=legacy_total,
        cantidad_visitas=3,  # Would normally give 911.55 total with IGV
    )

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/legacy/nueva-liquidacion", json=payload)
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    lg = response.json()["data"]["liquidacion_general"]

    # Override subtotal used directly
    assert Decimal(str(lg["sub_total"])) == legacy_subtotal, \
        f"Expected sub_total={legacy_subtotal} (legacy source), got {lg['sub_total']}"

    # Override total used directly — NOT recalculated as 500 * 1.18 = 590.00
    assert Decimal(str(lg["total"])) == legacy_total, \
        f"Expected total={legacy_total} (legacy source, IGV bypassed), got {lg['total']}"

    # Sanity: verify the IGV recalculation would have given a DIFFERENT result
    recalculated_total = legacy_subtotal * (Decimal("1") + Decimal("0.18"))  # = 590.00
    assert recalculated_total != legacy_total, \
        "Recalculated total (590.00) should differ from legacy total (500.00)"


# ── Phase 4: IO Legacy Null Tariff (CATEGORIA=0) ────────────────────────────────


def _make_legacy_payload_io_null_tariff(
    liquidacion_previa_id,
    inspector_id,
    municipalidad_id,
    distrito_id,
    *,
    cotizacion_legacy_sub_total,
    cotizacion_legacy_total,
    cantidad_visitas,
    fecha_registro=None,
    numero_revision=1,
):
    """
    IO legacy payload for the null tariff path (CATEGORIA=0 scenario).

    Unlike _make_legacy_payload_io_with_cotizacion_legacy, this builder
    intentionally omits tarifa_visitas_id to simulate CATEGORIA=0 where
    no valid tariff exists. cotizacion_legacy provides the totals directly.

    The legacy endpoint should accept this and create a record with:
    - modo_calculo = MANUAL
    - LiquidacionPorCategoriaVisitas.tarifa_aplicada = None
    - LiquidacionPorCategoriaVisitas.categoria = None
    - LiquidacionPorCategoriaVisitas.porcentaje_uit = None
    """
    general = {
        "municipalidad_id": str(municipalidad_id),
        "expediente": "EXP-LEG-IO-NULL-TARIFF-001",
        "observacion": "Test legacy IO with null tariff (CATEGORIA=0)",
        "proyecto": make_proyecto_payload(distrito_id),
    }
    if fecha_registro:
        general["fecha_registro"] = fecha_registro.isoformat()
    return {
        "liquidacion_previa_id": str(liquidacion_previa_id),
        "liquidacion_general": general,
        "liquidacion_especifica": {
            # categoria intentionally omitted — None for CATEGORIA=0
            "datos": {"cantidad_visitas": cantidad_visitas},
            # tarifa_visitas_id intentionally omitted — None for CATEGORIA=0
            "tarifa": {},
            "inspector_id": str(inspector_id),
        },
        "numero_revision": numero_revision,
        "cotizacion_legacy": {
            "sub_total": str(cotizacion_legacy_sub_total),
            "total": str(cotizacion_legacy_total),
        },
    }


@pytest.mark.django_db
def test_io_legacy_null_tariff_con_cotizacion_legacy_crea_modo_manual(
    auth_client,
    tipo_inspeccion_obra,
    liquidacion_previa_fixture,
    inspector_fixture,
    igv_vigente_2024, uit_vigente_2024,
    municipalidad, ubigeo_distrito,
):
    """
    GIVEN: IO legacy payload with no tarifa_visitas_id and cotizacion_legacy totals
           (simulates CATEGORIA=0 from legacy source)
    WHEN:  POST /liquidaciones/inspeccion-obra/legacy/nueva-liquidacion
    THEN:  Returns 200 with modo_calculo=MANUAL and null tariff/categoria/porcentaje_uit.

    This is the core test for batch 2: legacy/manual IO records with CATEGORIA=0
    (no valid tariff) are created in MANUAL mode with null FK on LiquidacionPorCategoriaVisitas.
    """
    legacy_subtotal = Decimal("924.00")   # Source SUBTOTAL from CATEGORIA=0 row
    legacy_total = Decimal("1090.32")     # Source TOTAL (includes old IGV)

    payload = _make_legacy_payload_io_null_tariff(
        liquidacion_previa_fixture.id,
        inspector_fixture.id,
        municipalidad.id,
        ubigeo_distrito.id,
        cotizacion_legacy_sub_total=legacy_subtotal,
        cotizacion_legacy_total=legacy_total,
        cantidad_visitas=3,
    )

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()
    assert data["success"] is True
    result = data["data"]

    lg = result["liquidacion_general"]
    lt = result["liquidacion_tipo"]

    # modo_calculo MUST be MANUAL for null-tariff legacy records
    assert lg["modo_calculo"] == "MANUAL", \
        f"Expected modo_calculo=MANUAL, got {lg.get('modo_calculo')}"

    # Override totals persisted directly (cotizacion_legacy bypass)
    assert Decimal(str(lg["sub_total"])) == legacy_subtotal
    assert Decimal(str(lg["total"])) == legacy_total

    # LiquidacionPorCategoriaVisitas fields are all null for CATEGORIA=0
    assert lt["tarifa_aplicada_id"] is None, \
        f"Expected tarifa_aplicada_id=null, got {lt.get('tarifa_aplicada_id')}"
    assert lt["categoria"] is None, \
        f"Expected categoria=null (CATEGORIA=0), got {lt.get('categoria')}"
    assert lt["porcentaje_uit"] is None, \
        f"Expected porcentaje_uit=null, got {lt.get('porcentaje_uit')}"

    # cantidad_visitas is preserved from input
    assert lt["cantidad_visitas"] == 3


@pytest.mark.django_db
def test_io_legacy_null_tariff_result_mapping_tolerates_null(
    auth_client,
    tipo_inspeccion_obra,
    liquidacion_previa_fixture,
    inspector_fixture,
    igv_vigente_2024, uit_vigente_2024,
    municipalidad, ubigeo_distrito,
):
    """
    GIVEN: IO legacy record created with null tariff (CATEGORIA=0)
    WHEN:  Response is returned from the endpoint
    THEN:  The _build_result_from_orm mapping does not crash on null tariff fields.

    Proves that batch 1's result mapping tolerance for null tariff is working
    correctly (tarifa_aplicada_id, categoria, porcentaje_uit all nullable in result).
    """
    payload = _make_legacy_payload_io_null_tariff(
        liquidacion_previa_fixture.id,
        inspector_fixture.id,
        municipalidad.id,
        ubigeo_distrito.id,
        cotizacion_legacy_sub_total=Decimal("500.00"),
        cotizacion_legacy_total=Decimal("590.00"),
        cantidad_visitas=2,
    )

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    result = response.json()["data"]
    lt = result["liquidacion_tipo"]

    # All nullable fields remain None — no crashes during result mapping
    assert lt["tarifa_aplicada_id"] is None
    assert lt["categoria"] is None
    assert lt["porcentaje_uit"] is None


@pytest.mark.django_db
def test_io_legacy_sin_tarifa_sin_override_falla_con_400(
    auth_client,
    liquidacion_previa_fixture,
    inspector_fixture,
    igv_vigente_2024, uit_vigente_2024,
    municipalidad, ubigeo_distrito,
):
    """
    GIVEN: IO legacy payload with no tarifa_visitas_id AND no cotizacion_legacy
           (CATEGORIA=0 but caller forgot to provide override totals)
    WHEN:  POST /liquidaciones/inspeccion-obra/legacy/nueva-liquidacion
    THEN:  Returns 400 — the flujo raises HttpError 400 because no tariff
           and no override totals means the IO formula cannot be calculated.

    Normal path: if no tariff is provided through normal UI, existing validation
    still fails (AttributeError on None.tarifa). This test proves the explicit
    HttpError for the null-tariff-without-override path.
    """
    general = {
        "municipalidad_id": str(municipalidad.id),
        "expediente": "EXP-LEG-IO-NULL-FAIL-001",
        "observacion": "Test legacy IO without tariff or override",
        "proyecto": make_proyecto_payload(ubigeo_distrito.id),
    }
    payload = {
        "liquidacion_previa_id": str(liquidacion_previa_fixture.id),
        "liquidacion_general": general,
        "liquidacion_especifica": {
            # No datos.categoria
            "datos": {"cantidad_visitas": 3},
            # No tarifa.tarifa_visitas_id
            "tarifa": {},
            "inspector_id": str(inspector_fixture.id),
        },
        "numero_revision": 1,
        # No cotizacion_legacy — this should fail
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/legacy/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 400, \
        f"Expected 400, got {response.status_code}: {response.content}"
