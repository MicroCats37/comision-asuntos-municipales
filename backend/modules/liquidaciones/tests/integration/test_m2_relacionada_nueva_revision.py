"""
Integration tests for M2 /relacionada and /nueva-revision endpoints.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import uuid

import pytest
from ninja.testing import TestClient
from ninja_jwt.tokens import AccessToken

from config.api import api
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoDistrito, UbigeoProvincia
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_miembro import (
    LiquidacionRelacionMiembro,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorMetroCuadrado,
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_key_helper import (
    generar_relacion_key,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


@pytest.fixture
def api_client(db):
    return TestClient(api)


@pytest.fixture
def create_user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username="testuser_m2_rel",
        email="test_m2_rel@example.com",
        password="testpass123",
        dni="87654321",
    )


@pytest.fixture
def auth_client(api_client, create_user):
    token = AccessToken.for_user(create_user)
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    api_client.user = create_user
    return api_client


@pytest.fixture
def ubigeo_distrito(db):
    departamento = UbigeoDepartamento.objects.create(nombre="LIMA")
    provincia = UbigeoProvincia.objects.create(departamento=departamento, nombre="LIMA")
    return UbigeoDistrito.objects.create(
        provincia=provincia,
        nombre="MIRAFLORES",
        ubigeo="150132",
    )


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    return Municipalidad.objects.create(
        codigo="MREL",
        nombre="Municipalidad Relacion M2",
        distrito=ubigeo_distrito,
    )


@pytest.fixture
def derecho_m2_vigente(db):
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_hu(db, tipo_habilitacion_urbana):
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=base,
        costo_por_m2=Decimal("150.0000"),
    )


@pytest.fixture
def tarifa_m2_ms(db, tipo_mecanica_suelos):
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=base,
        costo_por_m2=Decimal("180.0000"),
    )


def _payload(municipalidad, ubigeo_distrito, tarifa_m2, expediente):
    return {
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": expediente,
            "observacion": "Test M2 relation",
            "proyecto": {
                "denominacion": f"Proyecto {expediente}",
                "nombre_propietario": "Propietario Test SAC",
                "direccion": "Av. Test 123, Lima",
                "distrito_id": str(ubigeo_distrito.id),
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789012",
                    "razon_social": "Propietario Test SAC",
                },
            },
            "contacto": {
                "nombres": "Contacto",
                "apellidos": "M2",
                "dni": "12345678",
                "cargo": "Responsable",
                "telefono": "123456789",
                "celular": "987654321",
                "email": "contacto.m2@test.com",
            },
        },
        "liquidacion_especifica": {
            "datos": {"area_solicitada": 100.0},
            "tarifa": {"tarifa_m2_id": str(tarifa_m2.id)},
        },
    }


def _crear_primera(auth_client, endpoint, payload):
    response = auth_client.post(endpoint, json=payload)
    assert response.status_code == 200, response.content
    return response.json()["data"]


def _with_previa(payload, previa_id, expediente):
    related = deepcopy(payload)
    related["liquidacion_previa_id"] = str(previa_id)
    related["liquidacion_general"]["expediente"] = expediente
    return related


@pytest.mark.django_db
def test_hu_nueva_revision_crea_rev3_y_mismo_grupo(
    auth_client,
    municipalidad,
    ubigeo_distrito,
    derecho_m2_vigente,
    igv_vigente,
    tarifa_m2_hu,
):
    primera_payload = _payload(municipalidad, ubigeo_distrito, tarifa_m2_hu, "EXP-HU-M2-001")
    primera = _crear_primera(
        auth_client,
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision",
        primera_payload,
    )
    primera_id = uuid.UUID(primera["liquidacion_general"]["id"])

    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/nueva-revision",
        json=_with_previa(primera_payload, primera_id, "EXP-HU-M2-REV3"),
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]
    nueva_id = uuid.UUID(data["liquidacion_general"]["id"])
    assert data["liquidacion_general"]["numero_revision"] == 3
    assert data["liquidacion_general"]["contacto"]["dni"] == "12345678"

    grupo_id = LiquidacionRelacionMiembro.objects.get(liquidacion_id=primera_id).grupo_id
    miembros = LiquidacionRelacionMiembro.objects.filter(grupo_id=grupo_id)
    assert miembros.count() == 2
    assert set(miembros.values_list("liquidacion_id", flat=True)) == {primera_id, nueva_id}
    assert set(miembros.values_list("relacion_key", flat=True)) == {generar_relacion_key(TipoLiquidacion.HABILITACION_URBANA)}
    assert set(miembros.values_list("numero_revision", flat=True)) == {1, 3}


@pytest.mark.django_db
def test_hu_relacionada_duplica_rev1_devuelve_409(
    auth_client,
    municipalidad,
    ubigeo_distrito,
    derecho_m2_vigente,
    igv_vigente,
    tarifa_m2_hu,
):
    primera_payload = _payload(municipalidad, ubigeo_distrito, tarifa_m2_hu, "EXP-HU-M2-002")
    primera = _crear_primera(
        auth_client,
        "/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision",
        primera_payload,
    )
    primera_id = uuid.UUID(primera["liquidacion_general"]["id"])

    response = auth_client.post(
        "/liquidaciones/habilitacion-urbana/relacionada",
        json=_with_previa(primera_payload, primera_id, "EXP-HU-M2-DUP"),
    )

    assert response.status_code == 409, response.content
    grupo_id = LiquidacionRelacionMiembro.objects.get(liquidacion_id=primera_id).grupo_id
    assert LiquidacionRelacionMiembro.objects.filter(grupo_id=grupo_id).count() == 1


@pytest.mark.django_db
def test_ms_nueva_revision_crea_rev3_y_mismo_grupo(
    auth_client,
    municipalidad,
    ubigeo_distrito,
    derecho_m2_vigente,
    igv_vigente,
    tarifa_m2_ms,
):
    primera_payload = _payload(municipalidad, ubigeo_distrito, tarifa_m2_ms, "EXP-MS-M2-001")
    primera = _crear_primera(
        auth_client,
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
        primera_payload,
    )
    primera_id = uuid.UUID(primera["liquidacion_general"]["id"])

    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/nueva-revision",
        json=_with_previa(primera_payload, primera_id, "EXP-MS-M2-REV3"),
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]
    nueva_id = uuid.UUID(data["liquidacion_general"]["id"])
    assert data["liquidacion_general"]["numero_revision"] == 3
    assert data["liquidacion_general"]["contacto"]["dni"] == "12345678"

    grupo_id = LiquidacionRelacionMiembro.objects.get(liquidacion_id=primera_id).grupo_id
    miembros = LiquidacionRelacionMiembro.objects.filter(grupo_id=grupo_id)
    assert miembros.count() == 2
    assert set(miembros.values_list("liquidacion_id", flat=True)) == {primera_id, nueva_id}
    assert set(miembros.values_list("relacion_key", flat=True)) == {generar_relacion_key(TipoLiquidacion.MECANICA_SUELOS)}
    assert set(miembros.values_list("numero_revision", flat=True)) == {1, 3}


@pytest.mark.django_db
def test_ms_relacionada_duplica_rev1_devuelve_409(
    auth_client,
    municipalidad,
    ubigeo_distrito,
    derecho_m2_vigente,
    igv_vigente,
    tarifa_m2_ms,
):
    primera_payload = _payload(municipalidad, ubigeo_distrito, tarifa_m2_ms, "EXP-MS-M2-002")
    primera = _crear_primera(
        auth_client,
        "/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision",
        primera_payload,
    )
    primera_id = uuid.UUID(primera["liquidacion_general"]["id"])

    response = auth_client.post(
        "/liquidaciones/mecanica-suelos/relacionada",
        json=_with_previa(primera_payload, primera_id, "EXP-MS-M2-DUP"),
    )

    assert response.status_code == 409, response.content
    grupo_id = LiquidacionRelacionMiembro.objects.get(liquidacion_id=primera_id).grupo_id
    assert LiquidacionRelacionMiembro.objects.filter(grupo_id=grupo_id).count() == 1
