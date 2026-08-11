"""
Integration tests for the Inspeccion Obra /nueva-liquidacion/primera-revision endpoint.

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
from modules.liquidaciones.domain.constants import TipoLiquidacion


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
def valid_payload(valid_municipalidad_id, valid_tarifa_visitas_id, valid_distrito_id, uit_vigente, igv_vigente):
    return {
        "liquidacion_general": {
            "municipalidad_id": valid_municipalidad_id,
            "expediente": "EXP-2024-IO-001",
            "observacion": "Primera revisión Inspección Obra.",
            "proyecto": {
                "denominacion": "Proyecto IO Test",
                "nombre_propietario": "Juan Perez IO",
                "direccion": "Av. IO 123",
                "distrito_id": valid_distrito_id,
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20123456789",
                    "razon_social": "Constructora IO SAC"
                }
            }
        },
        "liquidacion_especifica": {
            "datos": {
                "cantidad_visitas": 3,
                "categoria": "INSPECCION"
            },
            "tarifa": {
                "tarifa_visitas_id": valid_tarifa_visitas_id
            }
        }
    }


@pytest.mark.django_db
def test_io_crear_primera_revision_success(auth_client, valid_payload):
    """
    Test successful creation of a LiquidacionInspeccionObra (primera-revision).
    """
    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion/primera-revision",
        json=valid_payload
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code} - {response.content}"
    data = response.json()
    assert data["success"] is True

    result = data["data"]

    # Verify General Structure
    general = result["liquidacion_general"]
    assert general["expediente"] == valid_payload["liquidacion_general"]["expediente"]
    assert general["observacion"] == valid_payload["liquidacion_general"]["observacion"]
    assert general["proyecto"]["denominacion"] == valid_payload["liquidacion_general"]["proyecto"]["denominacion"]

    # Verify Specific Structure (identity wrapper after semantic fix)
    especifica = result["liquidacion_especifica"]
    assert "id" in especifica
    assert "numero" in especifica

    # Verify liquidacion_tipo has Visitas calculation data
    tipo = result["liquidacion_tipo"]
    assert tipo["cantidad_visitas"] == valid_payload["liquidacion_especifica"]["datos"]["cantidad_visitas"]
    assert tipo["categoria"] == valid_payload["liquidacion_especifica"]["datos"]["categoria"]

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
def test_io_crear_primera_revision_invalid_tarifa(auth_client, valid_payload):
    """
    Test creation with an invalid Tarifa Visitas ID.
    """
    valid_payload["liquidacion_especifica"]["tarifa"]["tarifa_visitas_id"] = str(uuid.uuid4())

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion/primera-revision",
        json=valid_payload
    )

    # Should raise a 400 or 404 HttpError handled by Ninja exception handler
    assert response.status_code in [400, 404]
