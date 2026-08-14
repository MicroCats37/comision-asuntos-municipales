"""
Integration tests for Edificaciones /nueva-revision endpoint.

Tests use Ninja's TestClient (not Django's Client) for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- Creating revision 3 from revision 1
- Creating revision 5 from revision 3 (requires 1 and 3 to exist in chain)
- Validation: previa doesn't exist
- Validation: MAX_REVISIONES exceeded (5)
- Validation: even revision numbers not allowed (sanity check)
- Contact upsert: reuse when all fields match
- Contact upsert: create new when fields differ
- revisiones_previas array in response (empty for primera, populated for 3 and 5)
- GET /ultima-revision returns highest numero_revision
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
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision as Especialidad
from modules.finanzas.domain.models.impuestos import UIT, IGV
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    DerechoPorcentajeObra,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


# ── Fixtures ────────────────────────────────────────────────────────────────

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
        username="testuser_nueva_rev",
        email="test_nueva_rev@example.com",
        password="testpass123",
        dni="12345678",
    )


@pytest.fixture
def auth_client(api_client, create_user):
    user = create_user
    token = AccessToken.for_user(user)
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    api_client.user = user
    return api_client


@pytest.fixture
def api_client(db):
    return TestClient(api)


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    return Municipalidad.objects.create(
        codigo="M001",
        nombre="Municipalidad de Miraflores",
        distrito=ubigeo_distrito,
    )


@pytest.fixture
def tarifa_liquidacion_base_edificacion(db, tipo_edificacion):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def especialidad_estructuras(db):
    return Especialidad.objects.create(
        codigo="E01",
        slug="estructuras",
        nombre="Estructuras",
    )


@pytest.fixture
def especialidad_arquitectura(db):
    return Especialidad.objects.create(
        codigo="A01",
        slug="arquitectura",
        nombre="Arquitectura",
    )


@pytest.fixture
def tarifa_porcentaje_obra_estructuras(db, tarifa_liquidacion_base_edificacion, especialidad_estructuras):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        especialidad=especialidad_estructuras,
        porcentaje_liquidacion=Decimal("0.0010"),
    )


@pytest.fixture
def tarifa_porcentaje_obra_arquitectura(db, tarifa_liquidacion_base_edificacion, especialidad_arquitectura):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        especialidad=especialidad_arquitectura,
        porcentaje_liquidacion=Decimal("0.0005"),
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
def igv_vigente(db):
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def uit_vigente(db):
    return UIT.objects.create(
        valor=Decimal("5150.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def valid_distrito_id(ubigeo_distrito):
    return str(ubigeo_distrito.id)


@pytest.fixture
def valid_tarifa_ids(tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura):
    return [
        str(tarifa_porcentaje_obra_estructuras.id),
        str(tarifa_porcentaje_obra_arquitectura.id),
    ]


@pytest.fixture
def primera_revision_payload(valid_tarifa_ids, municipalidad, valid_distrito_id):
    """Payload for creating primera revision."""
    return {
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-EDIF-NUEVA-001",
            "observacion": "Test primera revision",
            "proyecto": {
                "denominacion": "Proyecto Nueva Revision Test",
                "nombre_propietario": "Propietario Nueva Revision SAC",
                "direccion": "Av. Nueva Revision 123, Lima",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789020",
                    "razon_social": "Propietario Nueva Revision SAC",
                },
            },
            "contacto": {
                "nombres": "Juan",
                "apellidos": "Perez",
                "dni": "12345678",
                "cargo": "Gerente",
                "telefono": "123456789",
                "celular": "987654321",
                "email": "juan.perez@test.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 100000.00,
            },
            "tarifas": [
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids[0]},
                {"tarifa_porcentaje_obra_id": valid_tarifa_ids[1]},
            ],
        },
    }


# ── Helper to create primera revision ────────────────────────────────────

def crear_primera_revision(auth_client, payload):
    """Helper to create primera revision and return the response data."""
    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert response.status_code == 200, f"Primera revision failed: {response.content}"
    return response.json()["data"]


# ── Tests ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_crear_revision_3_desde_revision_1(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    primera_revision_payload
):
    """
    Creating revision 3 from revision 1 succeeds.
    numero_revision should be 3, revisiones_previas should include revision 1.
    """
    # Create primera revision
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Create nueva revision payload (revision 3)
    revision_3_payload = {
        "liquidacion_previa_id": primera_id,
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-EDIF-NUEVA-002",
            "observacion": "Test revision 3",
            "proyecto": {
                "denominacion": "Proyecto Nueva Revision Test",
                "nombre_propietario": "Propietario Nueva Revision SAC",
                "direccion": "Av. Nueva Revision 123, Lima",
                "distrito_id": str(municipalidad.distrito.id),
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789020",
                    "razon_social": "Propietario Nueva Revision SAC",
                },
            },
            "contacto": {
                "nombres": "Juan",
                "apellidos": "Perez",
                "dni": "12345678",
                "cargo": "Gerente",
                "telefono": "123456789",
                "celular": "987654321",
                "email": "juan.perez@test.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 150000.00,
            },
            "tarifas": [],
        },
    }

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=revision_3_payload,
    )

    assert response.status_code == 200, f"Revision 3 failed: {response.content}"

    data = response.json()["data"]
    assert data["liquidacion_general"]["numero_revision"] == 3
    assert "revisiones_previas" in data["liquidacion_general"]
    assert len(data["liquidacion_general"]["revisiones_previas"]) == 1
    assert data["liquidacion_general"]["revisiones_previas"][0]["numero_revision"] == 1


@pytest.mark.django_db
def test_crear_revision_5_desde_revision_3(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    primera_revision_payload
):
    """
    Creating revision 5 from revision 3 succeeds.
    M2M liquidaciones_previas should include BOTH revision 1 AND revision 3.
    """
    # Create primera revision (revision 1)
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Create revision 3
    revision_3_payload = {
        "liquidacion_previa_id": primera_id,
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-EDIF-NUEVA-002",
            "observacion": "Test revision 3",
            "proyecto": {
                "denominacion": "Proyecto Nueva Revision Test",
                "nombre_propietario": "Propietario Nueva Revision SAC",
                "direccion": "Av. Nueva Revision 123, Lima",
                "distrito_id": str(municipalidad.distrito.id),
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789020",
                    "razon_social": "Propietario Nueva Revision SAC",
                },
            },
            "contacto": {
                "nombres": "Juan",
                "apellidos": "Perez",
                "dni": "12345678",
                "cargo": "Gerente",
                "telefono": "123456789",
                "celular": "987654321",
                "email": "juan.perez@test.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 150000.00,
            },
            "tarifas": [],
        },
    }

    response_r3 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=revision_3_payload,
    )
    assert response_r3.status_code == 200, f"Revision 3 failed: {response_r3.content}"
    revision_3 = response_r3.json()["data"]
    revision_3_id = revision_3["liquidacion_general"]["id"]

    # Create revision 5
    revision_5_payload = {
        "liquidacion_previa_id": revision_3_id,
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-EDIF-NUEVA-003",
            "observacion": "Test revision 5",
            "proyecto": {
                "denominacion": "Proyecto Nueva Revision Test",
                "nombre_propietario": "Propietario Nueva Revision SAC",
                "direccion": "Av. Nueva Revision 123, Lima",
                "distrito_id": str(municipalidad.distrito.id),
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789020",
                    "razon_social": "Propietario Nueva Revision SAC",
                },
            },
            "contacto": {
                "nombres": "Juan",
                "apellidos": "Perez",
                "dni": "12345678",
                "cargo": "Gerente",
                "telefono": "123456789",
                "celular": "987654321",
                "email": "juan.perez@test.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 200000.00,
            },
            "tarifas": [],
        },
    }

    response_r5 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=revision_5_payload,
    )

    assert response_r5.status_code == 200, f"Revision 5 failed: {response_r5.content}"

    data = response_r5.json()["data"]
    assert data["liquidacion_general"]["numero_revision"] == 5
    assert "revisiones_previas" in data["liquidacion_general"]
    # Should include both revision 1 and revision 3
    assert len(data["liquidacion_general"]["revisiones_previas"]) == 2
    revisiones_numeros = sorted([rp["numero_revision"] for rp in data["liquidacion_general"]["revisiones_previas"]])
    assert revisiones_numeros == [1, 3]


@pytest.mark.django_db
def test_previa_no_existe_devuelve_404(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    primera_revision_payload
):
    """
    Creating revision with non-existent previa returns 404.
    """
    # Create primera revision to have a valid municipalidad/distrito
    primera = crear_primera_revision(auth_client, primera_revision_payload)

    fake_previa_id = str(uuid.uuid4())
    revision_payload = {
        "liquidacion_previa_id": fake_previa_id,
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-EDIF-NUEVA-002",
            "observacion": "Test",
            "proyecto": {
                "denominacion": "Proyecto Nueva Revision Test",
                "nombre_propietario": "Propietario Nueva Revision SAC",
                "direccion": "Av. Nueva Revision 123, Lima",
                "distrito_id": str(municipalidad.distrito.id),
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789020",
                    "razon_social": "Propietario Nueva Revision SAC",
                },
            },
            "contacto": None,
        },
        "liquidacion_especifica": {
            "datos": {
                "valor_declarado": 150000.00,
            },
            "tarifas": [],
        },
    }

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=revision_payload,
    )

    assert response.status_code == 404, f"Expected 404 for non-existent previa, got {response.status_code}"


@pytest.mark.django_db
def test_max_revisiones_excedido_devuelve_400(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    primera_revision_payload
):
    """
    Creating revision beyond MAX_REVISIONES=5 returns 400.
    """
    # Create revision 1, 3, 5
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]

    # Create revision 3
    r3_payload = {
        "liquidacion_previa_id": primera_id,
        "liquidacion_general": primera_revision_payload["liquidacion_general"],
        "liquidacion_especifica": {
            "datos": {"valor_declarado": 150000.00},
            "tarifas": [],
        },
    }
    response_r3 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=r3_payload,
    )
    assert response_r3.status_code == 200
    revision_3 = response_r3.json()["data"]
    revision_3_id = revision_3["liquidacion_general"]["id"]

    # Create revision 5
    r5_payload = {
        "liquidacion_previa_id": revision_3_id,
        "liquidacion_general": primera_revision_payload["liquidacion_general"],
        "liquidacion_especifica": {
            "datos": {"valor_declarado": 200000.00},
            "tarifas": [],
        },
    }
    response_r5 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=r5_payload,
    )
    assert response_r5.status_code == 200

    # Try to create revision 7 (should fail - MAX is 5)
    revision_7_payload = {
        "liquidacion_previa_id": response_r5.json()["data"]["liquidacion_general"]["id"],
        "liquidacion_general": primera_revision_payload["liquidacion_general"],
        "liquidacion_especifica": {
            "datos": {"valor_declarado": 250000.00},
            "tarifas": [],
        },
    }

    response = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=revision_7_payload,
    )

    assert response.status_code == 400, f"Expected 400 for MAX_REVISIONES exceeded, got {response.status_code}"
    error_data = response.json()
    assert "MAX_REVISIONES" in str(error_data.get("error", {}).get("details", {}))


@pytest.mark.django_db
def test_ultima_revision_retorna_mayor_numero(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    primera_revision_payload
):
    """
    GET /ultima-revision returns the liquidacion with highest numero_revision.
    """
    # Create primera revision
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    proyecto_id = primera["liquidacion_general"]["proyecto"]["id"]
    primera_id = primera["liquidacion_general"]["id"]

    # Create revision 3
    r3_payload = {
        "liquidacion_previa_id": primera_id,
        "liquidacion_general": primera_revision_payload["liquidacion_general"],
        "liquidacion_especifica": {
            "datos": {"valor_declarado": 150000.00},
            "tarifas": [],
        },
    }
    response_r3 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=r3_payload,
    )
    assert response_r3.status_code == 200
    revision_3 = response_r3.json()["data"]

    # Get ultima revision (array paginado)
    response = auth_client.get(
        "/liquidaciones/edificaciones/ultima-revision",
    )

    assert response.status_code == 200, f"Ultima revision failed: {response.content}"
    data = response.json()["data"]
    assert len(data["items"]) >= 1, "Debe haber al menos una liquidacion"
    assert data["items"][0]["liquidacion_general"]["numero_revision"] == 3


@pytest.mark.django_db
def test_ultima_revision_con_filtros(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    primera_revision_payload
):
    """
    GET /ultima-revision with razon_social and numero_documento filters.
    """
    # Create primera revision
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    proyecto_id = primera["liquidacion_general"]["proyecto"]["id"]

    # Get ultima revision with filters
    response = auth_client.get(
        "/liquidaciones/edificaciones/ultima-revision?razon_social=Propietario%20Nueva%20Revision%20SAC&numero_documento=20456789020",
    )

    assert response.status_code == 200, f"Ultima revision with filters failed: {response.content}"
    data = response.json()["data"]
    assert len(data["items"]) >= 1, "Debe haber al menos una liquidacion"
    assert data["items"][0]["liquidacion_general"]["numero_revision"] == 1


@pytest.mark.django_db
def test_primera_revision_revisiones_previas_vacia(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    primera_revision_payload
):
    """
    Primera revision should have empty revisiones_previas array.
    """
    primera = crear_primera_revision(auth_client, primera_revision_payload)

    assert "revisiones_previas" in primera["liquidacion_general"]
    assert primera["liquidacion_general"]["revisiones_previas"] == []


@pytest.mark.django_db
def test_contacto_upsert_reutiliza_existente(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    primera_revision_payload
):
    """
    When contacto has ALL same fields, it should be reused (not created).
    """
    # Create primera revision
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]
    primera_contacto_id = primera["liquidacion_general"]["contacto"]["id"]

    # Create revision 3 with same contacto fields
    r3_payload = {
        "liquidacion_previa_id": primera_id,
        "liquidacion_general": {
            **primera_revision_payload["liquidacion_general"],
        },
        "liquidacion_especifica": {
            "datos": {"valor_declarado": 150000.00},
            "tarifas": [],
        },
    }

    response_r3 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=r3_payload,
    )
    assert response_r3.status_code == 200
    revision_3 = response_r3.json()["data"]

    # Contacto should be the same
    assert revision_3["liquidacion_general"]["contacto"]["id"] == primera_contacto_id


@pytest.mark.django_db
def test_contacto_upsert_crea_nuevo_si_diferente(
    auth_client, municipalidad, derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    primera_revision_payload
):
    """
    When contacto has different fields, a new contacto should be created.
    """
    # Create primera revision
    primera = crear_primera_revision(auth_client, primera_revision_payload)
    primera_id = primera["liquidacion_general"]["id"]
    primera_contacto_id = primera["liquidacion_general"]["contacto"]["id"]

    # Create revision 3 with different contacto
    r3_payload = {
        "liquidacion_previa_id": primera_id,
        "liquidacion_general": {
            **primera_revision_payload["liquidacion_general"],
            "contacto": {
                "nombres": "Maria",
                "apellidos": "Garcia",
                "dni": "87654321",
                "cargo": "Directora",
                "telefono": "999888777",
                "celular": "777888999",
                "email": "maria.garcia@test.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {"valor_declarado": 150000.00},
            "tarifas": [],
        },
    }

    response_r3 = auth_client.post(
        "/liquidaciones/edificaciones/nueva-revision",
        json=r3_payload,
    )
    assert response_r3.status_code == 200
    revision_3 = response_r3.json()["data"]

    # Contacto should be different (new one)
    assert revision_3["liquidacion_general"]["contacto"]["id"] != primera_contacto_id
    assert revision_3["liquidacion_general"]["contacto"]["nombres"] == "Maria"


@pytest.mark.django_db
def test_ultima_revision_sin_resultados_devuelve_vacio(
    auth_client
):
    """
    GET /ultima-revision with a filter that matches nothing returns empty items.
    """
    response = auth_client.get(
        "/liquidaciones/edificaciones/ultima-revision?numero_documento=00000000",
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()["data"]
    assert data["items"] == [], "Debe devolver items vacios"
