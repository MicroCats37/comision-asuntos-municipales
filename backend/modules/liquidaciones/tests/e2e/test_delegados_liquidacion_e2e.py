"""
E2E tests for delegados de liquidación endpoints.

Covers:
- GET  /liquidaciones/delegados/vigentes
- PATCH /liquidaciones/{liquidacion_id}/delegados

Uses Ninja TestClient (same as integration tests) and shared conftest fixtures.
"""
import uuid
from datetime import date, timedelta

import pytest

from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoMunicipalidad,
    DelegadoMunicipalidadPeriodo,
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _crear_perfil(cip: str, dni: str) -> PerfilIngeniero:
    """Creates a PerfilIngeniero with unique identifiers."""
    return PerfilIngeniero.objects.create(
        cip=cip,
        dni=dni,
        nombres="Nombre",
        apellido_paterno="Apellido",
        apellido_materno="Materno",
        correo_personal=f"{cip}@test.com",
    )


def _crear_delegado(cip: str, dni: str, especialidad=None) -> Delegado:
    """Creates a Delegado with an optional EspecialidadRevision."""
    return Delegado.objects.create(
        perfil_ingeniero=_crear_perfil(cip, dni),
        especialidad_revision=especialidad,
    )


def _crear_asignacion_municipal(
    delegado: Delegado,
    municipalidad,
    tipo: str = "TITULAR",
    vigente: bool = True,
) -> DelegadoMunicipalidad:
    """Creates a DelegadoMunicipalidad with a vigente or pasado periodo."""
    dm = DelegadoMunicipalidad.objects.create(
        delegado=delegado,
        municipalidad=municipalidad,
        tipo=tipo,
    )
    if vigente:
        DelegadoMunicipalidadPeriodo.objects.create(
            delegado_municipalidad=dm,
            periodo_inicio=date.today() - timedelta(days=30),
            periodo_fin=None,
        )
    else:
        DelegadoMunicipalidadPeriodo.objects.create(
            delegado_municipalidad=dm,
            periodo_inicio=date.today() - timedelta(days=365),
            periodo_fin=date.today() - timedelta(days=30),
        )
    return dm


@pytest.fixture
def liquidacion(db, proyecto, municipalidad, tipo_edificacion, create_user):
    """Creates a LiquidacionGeneral (EDIFICACION) for testing."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        sub_total=0,
        total=0,
        usuario_creador=create_user,
    )


# ── GET /liquidaciones/delegados/vigentes ─────────────────────────────────────

@pytest.mark.django_db
def test_delegados_vigentes_retorna_solo_match(
    auth_client,
    municipalidad,
    tipo_edificacion,
    especialidad_estructuras,
    especialidad_arquitectura,
    especialidades_disponibles_edificacion,
):
    """
    GET /delegados/vigentes devuelve delegados cuyo especialidad_revision ∈
    especialidades vigentes del tipo + asignación municipal vigente.
    Excluye: especialidad no vigente, sin especialidad, periodo no vigente.
    """
    delegado_match = _crear_delegado("11111", "11111111", especialidad_estructuras)
    _crear_asignacion_municipal(delegado_match, municipalidad, tipo="TITULAR")

    delegado_match_2 = _crear_delegado("22222", "22222222", especialidad_arquitectura)
    _crear_asignacion_municipal(delegado_match_2, municipalidad, tipo="ALTERNO")

    delegado_periodo_pasado = _crear_delegado("33333", "33333333", especialidad_estructuras)
    _crear_asignacion_municipal(delegado_periodo_pasado, municipalidad, vigente=False)

    delegado_sin_especialidad = _crear_delegado("44444", "44444444")
    _crear_asignacion_municipal(delegado_sin_especialidad, municipalidad)

    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes?municipalidad_id={municipalidad.id}"
        f"&tipo_liquidacion=EDIFICACION&revision_id={uuid.uuid4()}",
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    data = response.json()
    result = data["data"]
    assert "delegados" in result

    ids = {item["id"] for item in result["delegados"]}
    assert str(delegado_match.id) in ids
    assert str(delegado_match_2.id) in ids
    assert str(delegado_periodo_pasado.id) not in ids
    assert str(delegado_sin_especialidad.id) not in ids

    by_id = {item["id"]: item for item in result["delegados"]}
    titular = by_id[str(delegado_match.id)]
    assert titular["nombre_completo"] == delegado_match.perfil_ingeniero.nombre_completo
    assert titular["cip"] == "11111"
    assert titular["especialidad"] == {
        "id": str(especialidad_estructuras.id),
        "nombre": especialidad_estructuras.nombre,
    }
    assert titular["tipo"] == "TITULAR"
    assert by_id[str(delegado_match_2.id)]["tipo"] == "ALTERNO"


@pytest.mark.django_db
def test_delegados_vigentes_tipo_sin_especialidades_vacio(
    auth_client,
    municipalidad,
    tipo_habilitacion_urbana,
    especialidad_estructuras,
):
    """
    GET /delegados/vigentes con un tipo sin LiquidacionEspecialidadDisponibles
    devuelve lista vacía.
    """
    delegado = _crear_delegado("55555", "55555555", especialidad_estructuras)
    _crear_asignacion_municipal(delegado, municipalidad)

    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes?municipalidad_id={municipalidad.id}"
        f"&tipo_liquidacion=HABILITACION_URBANA",
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    result = response.json()["data"]
    assert result["delegados"] == []


# ── PATCH /liquidaciones/{liquidacion_id}/delegados ───────────────────────────

@pytest.mark.django_db
def test_batch_create_200_y_asociacion_con_especialidad_correcta(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    PATCH create → 200 y la asociación existe con especialidad_revision correcta.
    """
    delegado = _crear_delegado("66666", "66666666", especialidad_estructuras)
    _crear_asignacion_municipal(delegado, municipalidad)

    response = auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={"create": [{"delegado_id": str(delegado.id)}]},
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"

    asociacion = LiquidacionDelegado.objects.get(liquidacion=liquidacion, delegado=delegado)
    assert asociacion.especialidad_revision_id == especialidad_estructuras.id

    result = response.json()["data"]
    assert len(result["created"]) == 1
    assert result["created"][0]["delegado_id"] == str(delegado.id)
    assert result["created"][0]["especialidad_revision"] == {
        "id": str(especialidad_estructuras.id),
        "nombre": especialidad_estructuras.nombre,
    }


@pytest.mark.django_db
def test_batch_create_sin_asignacion_municipal_400(
    auth_client,
    liquidacion,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    PATCH create con delegado sin asignación municipal vigente → 400.
    """
    delegado = _crear_delegado("77777", "77777777", especialidad_estructuras)

    response = auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={"create": [{"delegado_id": str(delegado.id)}]},
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_batch_create_especialidad_no_vigente_400(
    auth_client,
    liquidacion,
    municipalidad,
    especialidades_disponibles_edificacion,
):
    """
    PATCH create con delegado cuya especialidad no es vigente para el tipo → 400.
    """
    especialidad_otra = EspecialidadRevision.objects.create(
        codigo="X01", slug="otra-especialidad", nombre="Otra Especialidad"
    )
    delegado = _crear_delegado("88888", "88888888", especialidad_otra)
    _crear_asignacion_municipal(delegado, municipalidad)

    response = auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={"create": [{"delegado_id": str(delegado.id)}]},
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_batch_create_sin_especialidad_revision_400(
    auth_client,
    liquidacion,
    municipalidad,
    especialidades_disponibles_edificacion,
):
    """
    PATCH create con delegado sin especialidad_revision → 400.
    """
    delegado = _crear_delegado("99999", "99999999")
    _crear_asignacion_municipal(delegado, municipalidad)

    response = auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={"create": [{"delegado_id": str(delegado.id)}]},
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_batch_delete_200_y_asociacion_eliminada(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    PATCH delete → 200 y la asociación se elimina.
    """
    delegado = _crear_delegado("12345", "12345678", especialidad_estructuras)
    _crear_asignacion_municipal(delegado, municipalidad)
    LiquidacionDelegado.objects.create(
        liquidacion=liquidacion,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
    )

    response = auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={"delete": [{"delegado_id": str(delegado.id)}]},
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    assert not LiquidacionDelegado.objects.filter(
        liquidacion=liquidacion, delegado=delegado
    ).exists()
    result = response.json()["data"]
    assert result["deleted"] == [str(delegado.id)]


@pytest.mark.django_db
def test_batch_delegado_duplicado_en_payload_400(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    PATCH con delegado duplicado dentro del payload → 400.
    """
    delegado = _crear_delegado("54321", "87654321", especialidad_estructuras)
    _crear_asignacion_municipal(delegado, municipalidad)

    response = auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={
            "create": [
                {"delegado_id": str(delegado.id)},
                {"delegado_id": str(delegado.id)},
            ]
        },
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_batch_create_asociacion_existente_400(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    PATCH create de un delegado ya asociado a la liquidación → 400.
    """
    delegado = _crear_delegado("11112", "11112222", especialidad_estructuras)
    _crear_asignacion_municipal(delegado, municipalidad)
    LiquidacionDelegado.objects.create(
        liquidacion=liquidacion,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
    )

    response = auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={"create": [{"delegado_id": str(delegado.id)}]},
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_batch_liquidacion_no_encontrada_404(auth_client):
    """
    PATCH con liquidacion_id inexistente → 404.
    """
    fake_uuid = uuid.uuid4()
    response = auth_client.patch(
        f"/liquidaciones/{fake_uuid}/delegados",
        json={"create": [{"delegado_id": str(uuid.uuid4())}]},
    )

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_batch_delete_asociacion_inexistente_400(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    PATCH delete de un delegado sin asociación previa → 400.
    """
    delegado = _crear_delegado("22221", "22221111", especialidad_estructuras)
    _crear_asignacion_municipal(delegado, municipalidad)

    response = auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={"delete": [{"delegado_id": str(delegado.id)}]},
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.content}"
