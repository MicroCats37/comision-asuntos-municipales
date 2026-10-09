"""
E2E flow tests for Inspección de Obra (IO).

Mimics the real frontend flow:
1. GET tarifas vigentes -> extract tarifa_id
2. POST crear liquidacion with extracted tarifa_id

Uses absolute imports with Django settings: config.settings.development
Uses ninja.testing.TestClient + JWT authentication.
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
from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def ubigeo_departamento(db):
    """Create a department for testing."""
    return UbigeoDepartamento.objects.create(nombre="LIMA")


@pytest.fixture
def ubigeo_provincia(db, ubigeo_departamento):
    """Create a province for testing."""
    return UbigeoProvincia.objects.create(
        departamento=ubigeo_departamento,
        nombre="LIMA",
    )


@pytest.fixture
def ubigeo_distrito(db, ubigeo_provincia):
    """Create a district for testing."""
    return UbigeoDistrito.objects.create(
        provincia=ubigeo_provincia,
        nombre="MIRAFLORES",
        ubigeo="150132",
    )


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    """Create a municipalidad for testing."""
    return Municipalidad.objects.create(
        codigo="M001",
        nombre="Municipalidad de Miraflores",
        distrito=ubigeo_distrito,
    )


@pytest.fixture
def igv_vigente(db):
    """Create an IGV vigente for testing."""
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def uit_vigente(db):
    """Create a UIT vigente for testing."""
    return UIT.objects.create(
        valor=Decimal("5150.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tipo_inspeccion_obra(db):
    """Get or create TipoLiquidacion for INSPECCION_OBRA."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="INSPECCION_OBRA", defaults={"nombre": "Inspección de Obra"})[0]


@pytest.fixture
def tarifa_liquidacion_base_io(db, tipo_inspeccion_obra):
    """Create a TarifaLiquidacionBase for Inspección de Obra."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_visitas_io(db, tarifa_liquidacion_base_io):
    """Create a TarifaPorCategoriaVisitas for Inspección de Obra."""
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_liquidacion_base_io,
        porcentaje_uit=Decimal("0.05"),  # 5% of UIT
        categoria_visitas="INSPECCION",
    )


@pytest.fixture
def create_user(db):
    """Create a test user for JWT authentication."""
    User = get_user_model()
    return User.objects.create_user(
        username="testuser_e2e_io",
        email="test_e2e_io@example.com",
        password="testpass123",
        dni="12345678",
    )


@pytest.fixture
def api_client(db):
    """Ninja TestClient for testing Ninja endpoints."""
    return TestClient(api)


@pytest.fixture
def auth_client(api_client, create_user):
    """Authenticate the test client using JWT token."""
    user = create_user
    token = AccessToken.for_user(user)
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    api_client.user = user
    return api_client


# ── E2E Test ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_e2e_inspeccion_obra_desde_previa_con_inspector(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_visitas_io, ubigeo_distrito, tipo_edificacion, proyecto
):
    """
    E2E flow: IO primera-revision DESDE una liquidación previa (Edificación),
    con inspector asignado.

    Verifica que el inspector sale DENTRO de liquidacion_tipo (la IO asocia
    inspectores al tipo, no a la general).
    """
    from modules.liquidaciones.domain.models.inspector import (
        Inspector,
        LiquidacionInspector,
    )
    from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero

    # Crear la liquidación previa (Edificación) — requiere tarifa de edificacion?
    # Solo se necesita su proyecto/municipalidad, así que se crea directo.
    from modules.liquidaciones.domain.constants import EstadoLiquidacion

    # Especialidad + operación del inspector para que la especialidad_revision
    # de la LiquidacionInspector se resuelva desde su operación.
    from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
    from modules.liquidaciones.domain.models.inspector import InspectorOperacion

    esp_rev = EspecialidadRevision.objects.create(
        slug="sanitaria", nombre="Ingeniería Sanitaria"
    )
    inspector = None

    previa = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-PREVIA-IO-2024-001",
        sub_total=0,
        total=0,
        usuario_creador=auth_client.user,
    )

    # Crear inspector (perfil + Inspector)
    perfil = PerfilIngeniero.objects.create(
        cip="998877",
        dni="99887766",
        nombres="Inspector",
        apellido_paterno="Prueba",
        apellido_materno="IO",
        correo_personal="inspector_io@test.com",
    )
    inspector = Inspector.objects.create(perfil_ingeniero=perfil)
    InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_edificacion,
        categoria="1",
        especialidad_revision=esp_rev,
    )

    # Step 1: GET tarifas vigentes
    response = auth_client.get("/liquidaciones/inspeccion-obra/tarifas/vigentes")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    tarifa_id = response.json()["data"]["tarifas"][0]["id"]

    # Step 2: POST nueva-liquidacion/primera-revision-desde-previa
    payload = {
        "liquidacion_previa_id": str(previa.id),
        "liquidacion_especifica": {
            "datos": {
                "cantidad_visitas": 2,
                "categoria": "INSPECCION",
            },
            "tarifa": {
                "tarifa_visitas_id": str(tarifa_id),
            },
            "inspector_id": str(inspector.id),
        },
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    result = response.json()["data"]

    # El inspector debe salir DENTRO de liquidacion_tipo
    lt = result["liquidacion_tipo"]
    assert "inspectores" in lt, "liquidacion_tipo should have 'inspectores'"
    assert len(lt["inspectores"]) == 1, \
        f"Expected 1 inspector, got {len(lt['inspectores'])}"

    insp_out = lt["inspectores"][0]
    assert insp_out["inspector_id"] == str(inspector.id)
    assert insp_out["perfil_ingeniero"]["cip"] == "998877"
    assert insp_out["perfil_ingeniero"]["nombre_completo"] == perfil.nombre_completo
    assert insp_out["especialidad_revision"] == {
        "id": str(esp_rev.id),
        "nombre": esp_rev.nombre,
    }

    # No debe salir en liquidacion_general (ni delegados ni inspectores)
    lg = result["liquidacion_general"]
    assert "delegados" in lg
    assert lg["delegados"] == []

    # La asociación LiquidacionInspector apunta al TIPO (LiquidacionPorCategoriaVisitas),
    # que es lo que sale como liquidacion_tipo — no a la general ni a la extension.
    tipo_id = result["liquidacion_tipo"]["id"]
    assert LiquidacionInspector.objects.filter(
        liquidacion_id=tipo_id, inspector=inspector
    ).exists()


@pytest.mark.django_db
def test_e2e_inspeccion_obra_nueva_liquidacion_sin_previa_con_inspector_operacion(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_visitas_io, ubigeo_distrito, tipo_edificacion, proyecto
):
    """
    E2E flow: IO standalone /nueva-liquidacion (SIN liquidación previa)
    con inspector que tiene operación EDIFICACION (NO INSPECCION_OBRA).

    Este test prueba que el fix funciona: el endpoint YA NO requiere que el
    inspector tenga una operación de tipo INSPECCION_OBRA. En cambio, acepta
    inspector_operacion_id directamente (obtenido de /seleccionables) y deriva
    especialidad_revision desde esa operación.

    El inspector se registra con tipo EDIFICACION (típico en producción), y el
    endpoint debe aceptar ese inspector sin fallar con error 400.
    """
    from modules.liquidaciones.domain.models.inspector import (
        Inspector,
        LiquidacionInspector,
        InspectorOperacion,
    )
    from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero, EspecialidadRevision

    esp_rev = EspecialidadRevision.objects.create(
        slug="estructuras", nombre="Ingeniería de Estructuras"
    )
    tipo_hu = TipoLiquidacionModel.objects.get_or_create(
        codigo="HABILITACION_URBANA", defaults={"nombre": "Habilitación Urbana"}
    )[0]

    # Crear inspector con operación SOLO de EDIFICACION (no tiene INSPECCION_OBRA)
    perfil = PerfilIngeniero.objects.create(
        cip="554433",
        dni="55443322",
        nombres="Ingeniero",
        apellido_paterno="SinPrevia",
        apellido_materno="Test",
        correo_personal="sin_previa@test.com",
    )
    inspector = Inspector.objects.create(perfil_ingeniero=perfil)
    inspector_operacion = InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_edificacion,  # Solo EDIFICACION, NO INSPECCION_OBRA
        categoria="1",
        especialidad_revision=esp_rev,
    )

    # Step 1: GET tarifas vigentes
    response = auth_client.get("/liquidaciones/inspeccion-obra/tarifas/vigentes")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    tarifa_id = response.json()["data"]["tarifas"][0]["id"]

    # Step 2: POST /nueva-liquidacion (sin previa) con inspector_operacion_id
    # El endpoint debe aceptar el inspector aunque no tenga INSPECCION_OBRA
    payload = {
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-IO-SIN-PREVIA-2024-001",
            "denominacion_de_proyecto": "Proyecto Test Sin Previa",
            "proyecto": {
                "nombre_propietario": "Propietario Test",
                "direccion": "Av. Test 123",
                "distrito_id": str(ubigeo_distrito.id),
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789012",
                    "razon_social": "Empresa Test SAC",
                },
            },
            "observacion": "Test de IO sin previa",
        },
        "liquidacion_especifica": {
            "datos": {
                "cantidad_visitas": 3,
                "categoria": "INSPECCION",
            },
            "tarifa": {
                "tarifa_visitas_id": str(tarifa_id),
            },
            "inspector_id": str(inspector.id),
            "inspector_operacion_id": str(inspector_operacion.id),
        },
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload,
    )

    assert response.status_code == 200, \
        f"Expected 200 (inspector sin INSPECCION_OBRA fue rechazado). " \
        f"Status={response.status_code}: {response.content}"

    result = response.json()["data"]

    # El inspector debe salir DENTRO de liquidacion_tipo
    lt = result["liquidacion_tipo"]
    assert "inspectores" in lt, "liquidacion_tipo should have 'inspectores'"
    assert len(lt["inspectores"]) == 1, \
        f"Expected 1 inspector, got {len(lt['inspectores'])}"

    insp_out = lt["inspectores"][0]
    assert insp_out["inspector_id"] == str(inspector.id)
    assert insp_out["perfil_ingeniero"]["cip"] == "554433"
    assert insp_out["especialidad_revision"] == {
        "id": str(esp_rev.id),
        "nombre": esp_rev.nombre,
    }

    # Verificar que la LiquidacionInspector fue creada con la operación correcta
    tipo_id = result["liquidacion_tipo"]["id"]
    li = LiquidacionInspector.objects.filter(
        liquidacion_id=tipo_id, inspector=inspector
    ).first()
    assert li is not None, "LiquidacionInspector should be created"
    assert li.inspector_operacion_id == inspector_operacion.id
    assert li.especialidad_revision_id == esp_rev.id
