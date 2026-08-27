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
        denominacion="Proyecto Test Legacy",
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
