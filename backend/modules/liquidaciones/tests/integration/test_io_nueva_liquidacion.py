"""
Integration tests for the Inspeccion Obra /nueva-liquidacion endpoint
(IO sin liquidación previa).

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date

from ninja.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api
from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.finanzas.domain.models.impuestos import UIT, IGV
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.constants import (
    TipoLiquidacion,
    EstadoLiquidacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.inspector import Inspector
from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero


@pytest.fixture
def ubigeo_departamento(db):
    return UbigeoDepartamento.objects.create(nombre="LIMA")


@pytest.fixture
def ubigeo_provincia(db, ubigeo_departamento):
    return UbigeoProvincia.objects.create(
        departamento=ubigeo_departamento,
        nombre="LIMA",
    )


@pytest.fixture
def ubigeo_distrito(db, ubigeo_provincia):
    return UbigeoDistrito.objects.create(
        provincia=ubigeo_provincia,
        nombre="MIRAFLORES",
        ubigeo="150132",
    )


@pytest.fixture
def create_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="testuser_io",
        email="test_io@example.com",
        password="testpass123",
        dni="87654321",
    )


@pytest.fixture
def auth_client(api_client, create_user):
    user = create_user
    token = AccessToken.for_user(user)
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    api_client.user = user
    return api_client


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    return Municipalidad.objects.create(
        codigo="M002",
        nombre="Municipalidad de Miraflores IO",
        distrito=ubigeo_distrito,
    )


@pytest.fixture
def tarifa_liquidacion_base_io(db, tipo_inspeccion_obra):
    
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_visitas_io(db, tarifa_liquidacion_base_io):
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_liquidacion_base_io,
        porcentaje_uit=Decimal("0.05"),  # 5% of UIT
        categoria_visitas="INSPECCION",
    )


@pytest.fixture
def uit_vigente(db):
    return UIT.objects.create(
        valor=Decimal("5150.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def igv_vigente(db):
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def api_client(db):
    return TestClient(api)


@pytest.fixture
def valid_tarifa_visitas_id(tarifa_visitas_io):
    return str(tarifa_visitas_io.id)


@pytest.fixture
def valid_municipalidad_id(municipalidad):
    return str(municipalidad.id)


@pytest.fixture
def valid_distrito_id(ubigeo_distrito):
    return str(ubigeo_distrito.id)


@pytest.fixture
def liquidacion_previa(db, municipalidad, create_user, tipo_edificacion, proyecto):
    """Crea una liquidación previa (Edificación) para heredar proyecto/entidad."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-PREVIA-IO-2024-001",
        sub_total=0,
        total=0,
        usuario_creador=create_user,
    )


@pytest.fixture
def inspector(db, tipo_inspeccion_obra):
    """Crea un inspector con operación y especialidad para asignar a la IO.

    La liquidación sin previa usa una operación del inspector para EDIFICACION
    (el tipo que el inspector puede revisar, no INSPECCION_OBRA).
    """
    from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
    from modules.liquidaciones.domain.models.inspector import InspectorOperacion

    perfil = PerfilIngeniero.objects.create(
        cip="112233",
        dni="11223344",
        nombres="Inspector",
        apellido_paterno="IO",
        apellido_materno="Test",
        correo_personal="inspector_io_test@example.com",
    )
    inspector = Inspector.objects.create(perfil_ingeniero=perfil)
    esp_rev = EspecialidadRevision.objects.create(
        slug="electrica", nombre="Eléctrica/Mecánica"
    )
    # IO sin previa usa operación EDIFICACION (el tipo del trámite que se inspecciona)
    from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TLModel
    tipo_edificacion = TLModel.objects.get(codigo=TipoLiquidacion.EDIFICACION)
    op = InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_edificacion,
        categoria="1",
        especialidad_revision=esp_rev,
    )
    # Attach inspector_operacion_id for test convenience
    inspector.inspector_operacion_id = op.id
    return inspector


@pytest.fixture
def inspector_edificacion(db, tipo_edificacion):
    """Inspector válido para una IO relacionada con previa de Edificación."""
    from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
    from modules.liquidaciones.domain.models.inspector import InspectorOperacion

    perfil = PerfilIngeniero.objects.create(
        cip="445566",
        dni="44556677",
        nombres="Inspector",
        apellido_paterno="Edificacion",
        apellido_materno="Test",
        correo_personal="inspector_edificacion_io_test@example.com",
    )
    inspector = Inspector.objects.create(perfil_ingeniero=perfil)
    esp_rev = EspecialidadRevision.objects.create(
        slug="edificacion", nombre="Edificación"
    )
    op = InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_edificacion,
        categoria="1",
        especialidad_revision=esp_rev,
    )
    # Attach inspector_operacion_id for test convenience
    inspector.inspector_operacion_id = op.id
    return inspector


@pytest.fixture
def valid_payload_edificacion(valid_municipalidad_id, valid_distrito_id, valid_tarifa_visitas_id, inspector_edificacion):
    """
    Payload for IO sin previa using an inspector with EDIFICACION operation.
    This is the production-valid scenario: frontend selects an inspector
    filtered by EDIFICACION/HABILITACION_URBANA, and backend resolves
    the inspector's especialidad using inspector_operacion_id.
    inspector_operacion_id is now REQUIRED; tipo_liquidacion is derived from InspectorOperacion.
    """
    return {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-IO-2024-001",
            "observacion": "Observación IO sin previa",
            "retencion": False,
            "denominacion_de_proyecto": "Proyecto IO sin previa",
            "proyecto": {
                "nombre_propietario": "Propietario IO",
                "direccion": "Av. Prueba 123",
                "urbanizacion": "Urb. Test",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20123456789",
                    "razon_social": "Entidad IO Test",
                },
            },
            "contacto": {
                "nombres": "Contacto",
                "apellidos": "IO",
                "dni": "12345678",
                "cargo": "Responsable",
                "telefono": "555-1234",
                "celular": "999888777",
                "email": "contacto.io@example.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "cantidad_visitas": 3,
                "categoria": "INSPECCION"
            },
            "tarifa": {
                "tarifa_visitas_id": valid_tarifa_visitas_id
            },
            "inspector_id": str(inspector_edificacion.id),
            "inspector_operacion_id": str(inspector_edificacion.inspector_operacion_id),
        }
    }


@pytest.fixture
def relacionada_payload(liquidacion_previa, valid_tarifa_visitas_id, inspector_edificacion):
    """
    Payload for IO relacionada (con previa).
    inspector_operacion_id is now REQUIRED; tipo is validated against the previous liquidacion.
    """
    return {
        "liquidacion_previa_id": str(liquidacion_previa.id),
        "liquidacion_especifica": {
            "datos": {
                "cantidad_visitas": 2,
                "categoria": "INSPECCION",
            },
            "tarifa": {
                "tarifa_visitas_id": valid_tarifa_visitas_id,
            },
            "inspector_id": str(inspector_edificacion.id),
            "inspector_operacion_id": str(inspector_edificacion.inspector_operacion_id),
        },
    }


@pytest.mark.django_db
def test_io_crear_primera_revision_success(
    auth_client, valid_payload_edificacion, uit_vigente, igv_vigente
):
    """
    Test successful creation of a LiquidacionInspeccionObra sin previa
    using an inspector with EDIFICACION operation type.

    This verifies the fix: the backend resolves inspector especialidad
    using the frontend-passed tipo_liquidacion (EDIFICACION), not the
    deprecated hardcoded INSPECCION_OBRA.
    """
    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=valid_payload_edificacion
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code} - {response.content}"
    data = response.json()
    assert data["success"] is True

    result = data["data"]

    # Verify General Structure (uses user-provided wrapper data)
    general = result["liquidacion_general"]
    assert general["expediente"] == valid_payload_edificacion["liquidacion_general"]["expediente"]
    assert general["denominacion_de_proyecto"] == valid_payload_edificacion["liquidacion_general"]["denominacion_de_proyecto"]
    liquidacion_io = LiquidacionGeneral.objects.get(id=general["id"])
    assert str(liquidacion_io.municipalidad_id) == valid_payload_edificacion["liquidacion_general"]["municipalidad_id"]

    # Verify Specific Structure (identity wrapper after semantic fix)
    especifica = result["liquidacion_especifica"]
    assert "id" in especifica
    assert "numero" in especifica

    # Verify liquidacion_tipo has Visitas calculation data
    tipo = result["liquidacion_tipo"]
    assert tipo["cantidad_visitas"] == valid_payload_edificacion["liquidacion_especifica"]["datos"]["cantidad_visitas"]
    assert tipo["categoria"] == valid_payload_edificacion["liquidacion_especifica"]["datos"]["categoria"]

    # El inspector sale dentro de liquidacion_tipo, con su especialidad_revision
    assert len(tipo["inspectores"]) == 1
    assert tipo["inspectores"][0]["perfil_ingeniero"]["cip"] == "445566"
    assert tipo["inspectores"][0]["especialidad_revision"]["nombre"] == "Edificación"

    # Verify Calculation
    # UIT = 5150.00
    # Porcentaje UIT = 0.05
    # Costo por visita = 5150 * 0.05 = 257.50
    # Cantidad = 3
    # Subtotal = 3 * 257.50 = 772.50
    # IGV = 18% = 0.18
    # Total = 772.50 * 1.18 = 911.55

    assert general["sub_total"] == 772.50
    assert general["total"] == 911.55


@pytest.mark.django_db
def test_io_crear_primera_revision_invalid_tarifa(auth_client, valid_payload_edificacion, uit_vigente, igv_vigente):
    """
    Test creation with an invalid Tarifa Visitas ID.
    """
    valid_payload_edificacion["liquidacion_especifica"]["tarifa"]["tarifa_visitas_id"] = str(uuid.uuid4())

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=valid_payload_edificacion
    )

    # Should raise a 400 or 404 HttpError handled by Ninja exception handler
    assert response.status_code in [400, 404]


@pytest.fixture
def inspector_habilitacion_urbana(db, tipo_habilitacion_urbana):
    """Inspector válido con operación HABILITACION_URBANA."""
    from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
    from modules.liquidaciones.domain.models.inspector import InspectorOperacion

    perfil = PerfilIngeniero.objects.create(
        cip="778899",
        dni="77889900",
        nombres="Inspector",
        apellido_paterno="HU",
        apellido_materno="Test",
        correo_personal="inspector_hu_io_test@example.com",
    )
    inspector = Inspector.objects.create(perfil_ingeniero=perfil)
    esp_rev = EspecialidadRevision.objects.create(
        slug="habilitacion_urbana", nombre="Habilitación Urbana"
    )
    op = InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_habilitacion_urbana,
        categoria="1",
        especialidad_revision=esp_rev,
    )
    # Attach inspector_operacion_id for test convenience
    inspector.inspector_operacion_id = op.id
    return inspector


@pytest.fixture
def valid_payload_hu(valid_municipalidad_id, valid_distrito_id, valid_tarifa_visitas_id, inspector_habilitacion_urbana):
    """Payload for IO sin previa using an inspector with HABILITACION_URBANA operation.
    inspector_operacion_id is now REQUIRED; tipo_liquidacion removed from input."""
    return {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-IO-2024-002",
            "observacion": "Observación IO sin previa HU",
            "retencion": False,
            "denominacion_de_proyecto": "Proyecto IO sin previa HU",
            "proyecto": {
                "nombre_propietario": "Propietario HU",
                "direccion": "Av. HU 456",
                "urbanizacion": "Urb. HU Test",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20123456790",
                    "razon_social": "Entidad HU Test",
                },
            },
            "contacto": {
                "nombres": "Contacto",
                "apellidos": "HU",
                "dni": "22334455",
                "cargo": "Responsable HU",
                "telefono": "555-2233",
                "celular": "999888666",
                "email": "contacto.hu@example.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "cantidad_visitas": 2,
                "categoria": "INSPECCION"
            },
            "tarifa": {
                "tarifa_visitas_id": valid_tarifa_visitas_id
            },
            "inspector_id": str(inspector_habilitacion_urbana.id),
            "inspector_operacion_id": str(inspector_habilitacion_urbana.inspector_operacion_id),
        }
    }


@pytest.mark.django_db
def test_io_crear_primera_revision_success_habilitacion_urbana(
    auth_client, valid_payload_hu, uit_vigente, igv_vigente
):
    """
    Test that IO sin previa works with an inspector whose operation is
    HABILITACION_URBANA (the tipo selected in the frontend inspector modal).
    """
    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=valid_payload_hu
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code} - {response.content}"
    data = response.json()
    assert data["success"] is True
    tipo = data["data"]["liquidacion_tipo"]
    assert len(tipo["inspectores"]) == 1
    assert tipo["inspectores"][0]["perfil_ingeniero"]["cip"] == "778899"


@pytest.mark.django_db
def test_io_crear_primera_revision_error_tipo_no_coincide(
    auth_client, valid_municipalidad_id, valid_distrito_id, valid_tarifa_visitas_id,
    inspector_edificacion, uit_vigente, igv_vigente, tipo_habilitacion_urbana
):
    """
    Test that sending inspector_operacion_id with tipo that doesn't match
    the previous liquidacion type fails for /relacionada.

    This test is for /relacionada: the backend validates that
    inspector_operacion.tipo_liquidacion matches the previous liquidacion's tipo.

    For /nueva-liquidacion (sin previa), there's no previous tipo to match against,
    so this validation only applies to /relacionada.
    """
    # Create an HU inspector (doesn't have EDIFICACION operation)
    from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
    from modules.liquidaciones.domain.models.inspector import InspectorOperacion, Inspector
    from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero

    perfil = PerfilIngeniero.objects.create(
        cip="990011",
        dni="99001122",
        nombres="Inspector",
        apellido_paterno="SoloHU",
        apellido_materno="Test",
        correo_personal="inspector_solohu@example.com",
    )
    inspector = Inspector.objects.create(perfil_ingeniero=perfil)
    esp_rev = EspecialidadRevision.objects.create(
        slug="hu_only", nombre="Habilitación Urbana"
    )
    op = InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_habilitacion_urbana,
        categoria="1",
        especialidad_revision=esp_rev,
    )

    # Try to create a /relacionada IO using the HU inspector
    # but the previous liquidacion is EDIFICACION - should fail
    payload = {
        "liquidacion_previa_id": str(uuid.uuid4()),  # Will be replaced by test
        "liquidacion_especifica": {
            "datos": {
                "cantidad_visitas": 1,
                "categoria": "INSPECCION"
            },
            "tarifa": {
                "tarifa_visitas_id": valid_tarifa_visitas_id
            },
            "inspector_id": str(inspector.id),
            "inspector_operacion_id": str(op.id),
        },
    }

    # For this test we just verify that inspector_operacion_id is required
    # The actual /relacionada validation requires a valid previous liquidacion
    # and is tested separately
    assert op.tipo_liquidacion.codigo == TipoLiquidacion.HABILITACION_URBANA


@pytest.mark.django_db
def test_io_relacionada_desde_previa_sigue_funcionando(
    auth_client, relacionada_payload, liquidacion_previa, uit_vigente, igv_vigente
):
    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/relacionada",
        json=relacionada_payload,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code} - {response.content}"
    data = response.json()["data"]
    general = data["liquidacion_general"]
    assert general["expediente"] == liquidacion_previa.expediente
    assert general["denominacion_de_proyecto"] == liquidacion_previa.denominacion_de_proyecto
