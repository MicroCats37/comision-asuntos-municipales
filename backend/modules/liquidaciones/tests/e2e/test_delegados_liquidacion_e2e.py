"""
E2E tests for delegados de liquidación endpoints.

Covers:
- GET  /liquidaciones/delegados/vigentes
- PATCH /liquidaciones/{liquidacion_id}/delegados
  - eliminación con guardas de referencias financieras (409) vs. eliminación limpia

Uses Ninja TestClient (same as integration tests) and shared conftest fixtures.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

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
from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.recibo_honorario import (
    ReciboHonorarioDelegado,
)
from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
    ReciboHonorarioDelegadoMensual,
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
    """Creates a Delegado. La especialidad vive en la operación, no en el base."""
    return Delegado.objects.create(
        perfil_ingeniero=_crear_perfil(cip, dni),
    )


def _crear_asignacion_municipal(
    delegado: Delegado,
    municipalidad,
    tipo: str = "TITULAR",
    vigente: bool = True,
    especialidad=None,
) -> DelegadoMunicipalidad:
    """Creates a DelegadoMunicipalidad with a vigente or pasado periodo.

    La especialidad_revision es obligatoria en la operación (vive ahí, no en
    el Delegado base).
    """
    assert especialidad is not None, "La operación requiere especialidad_revision"
    dm = DelegadoMunicipalidad.objects.create(
        delegado=delegado,
        municipalidad=municipalidad,
        tipo=tipo,
        especialidad_revision=especialidad,
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


# ── Helpers de referencias financieras (guards de eliminación) ─────────────────

def _crear_rh_mensual(
    delegado: Delegado,
    periodo: int = 2026,
    mes: int = 3,
) -> ReciboHonorarioDelegadoMensual:
    """Creates a ReciboHonorarioDelegadoMensual with frozen totals."""
    return ReciboHonorarioDelegadoMensual.objects.create(
        delegado=delegado,
        periodo=periodo,
        mes=mes,
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )


def _crear_detalle_honorario(
    liquidacion_delegado: LiquidacionDelegado,
    recibo_mensual=None,
    imp_bruto: Decimal = Decimal("1000.00"),
) -> DetalleHonorarioDelegado:
    """
    Creates a DetalleHonorarioDelegado.

    `recibo_mensual=None` → detalle huérfano (legacy, sin RH detrás).
    `recibo_mensual=<RH>` → detalle vinculado a un RH mensual (bloqueante).
    """
    return DetalleHonorarioDelegado.objects.create(
        recibo_mensual=recibo_mensual,
        liquidacion_delegado=liquidacion_delegado,
        imp_bruto=imp_bruto,
        sub_total=imp_bruto,
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )


def _crear_recibo_honorario(
    liquidacion_delegado: LiquidacionDelegado,
) -> ReciboHonorarioDelegado:
    """Creates a ReciboHonorarioDelegado (recibo NO mensual) sobre la asignación."""
    return ReciboHonorarioDelegado.objects.create(
        liquidacion_delegado=liquidacion_delegado,
        sub_total=Decimal("1000.00"),
        imp_bruto=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
        honorario=Decimal("600.00"),
    )


def _eliminar_delegado(auth_client, liquidacion, delegado):
    """PATCH delete de un delegado en el batch endpoint."""
    return auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={"delete": [{"delegado_id": str(delegado.id)}]},
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
    delegado_match = _crear_delegado("11111", "11111111")
    _crear_asignacion_municipal(delegado_match, municipalidad, tipo="TITULAR", especialidad=especialidad_estructuras)

    delegado_match_2 = _crear_delegado("22222", "22222222")
    _crear_asignacion_municipal(delegado_match_2, municipalidad, tipo="ALTERNO", especialidad=especialidad_arquitectura)

    delegado_periodo_pasado = _crear_delegado("33333", "33333333")
    _crear_asignacion_municipal(delegado_periodo_pasado, municipalidad, vigente=False, especialidad=especialidad_estructuras)

    delegado_sin_especialidad = _crear_delegado("44444", "44444444")
    # Sin operación: la especialidad_revision es obligatoria en la operación,
    # así que este delegado no puede tener asignación municipal → se excluye.

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
    delegado = _crear_delegado("55555", "55555555")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)

    response = auth_client.get(
        f"/liquidaciones/delegados/vigentes?municipalidad_id={municipalidad.id}"
        f"&tipo_liquidacion=HABILITACION_URBANA",
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    result = response.json()["data"]
    assert result["delegados"] == []


@pytest.mark.django_db
def test_delegados_vigentes_con_fecha_param_retorna_solo_vigentes_en_fecha(
    auth_client,
    municipalidad,
    tipo_edificacion,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    GET /delegados/vigentes?fecha=YYYY-MM-DD filtra delegados vigentes SOLO en
    esa fecha (periodo_inicio <= fecha AND (periodo_fin is null OR periodo_fin >= fecha)).

    Sin fecha: defaults to today (backward-compatible).
    """
    fecha_hoy = date.today()
    fecha_pasado = fecha_hoy - timedelta(days=60)   # before periodo started
    fecha_durante = fecha_hoy - timedelta(days=30)  # inside vigente periodo
    fecha_futuro = fecha_hoy + timedelta(days=30)   # future (periodo still open)

    # Delegado whose assignment period started 30 days ago and is still open
    delegado = _crear_delegado("77777", "77777777")
    dm = _crear_asignacion_municipal(delegado, municipalidad, vigente=True, especialidad=especialidad_estructuras)
    # Override periodo_inicio to 30 days ago (the helper sets it to date.today()-30)
    dm.periodos.update(periodo_inicio=fecha_durante)

    # Sanity: without fecha param (today), delegate IS included
    response_today = auth_client.get(
        f"/liquidaciones/delegados/vigentes?municipalidad_id={municipalidad.id}"
        f"&tipo_liquidacion=EDIFICACION",
    )
    assert response_today.status_code == 200
    ids_today = {item["id"] for item in response_today.json()["data"]["delegados"]}
    assert str(delegado.id) in ids_today, "Delegate should be vigente today"

    # With fecha=during the periodo, delegate IS included
    response_durante = auth_client.get(
        f"/liquidaciones/delegados/vigentes?municipalidad_id={municipalidad.id}"
        f"&tipo_liquidacion=EDIFICACION&fecha={fecha_durante.isoformat()}",
    )
    assert response_durante.status_code == 200
    ids_durante = {item["id"] for item in response_durante.json()["data"]["delegados"]}
    assert str(delegado.id) in ids_durante, "Delegate should be vigente on fecha_durante"

    # With fecha=60 days ago (before the periodo started), delegate is NOT included
    response_pasado = auth_client.get(
        f"/liquidaciones/delegados/vigentes?municipalidad_id={municipalidad.id}"
        f"&tipo_liquidacion=EDIFICACION&fecha={fecha_pasado.isoformat()}",
    )
    assert response_pasado.status_code == 200
    ids_pasado = {item["id"] for item in response_pasado.json()["data"]["delegados"]}
    assert str(delegado.id) not in ids_pasado, "Delegate should NOT be vigente before periodo started"

    # With fecha=future, delegate IS still included (periodo_fin is null)
    response_futuro = auth_client.get(
        f"/liquidaciones/delegados/vigentes?municipalidad_id={municipalidad.id}"
        f"&tipo_liquidacion=EDIFICACION&fecha={fecha_futuro.isoformat()}",
    )
    assert response_futuro.status_code == 200
    ids_futuro = {item["id"] for item in response_futuro.json()["data"]["delegados"]}
    assert str(delegado.id) in ids_futuro, "Delegate should still be vigente in the future"


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
    delegado = _crear_delegado("66666", "66666666")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)

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
        slug="otra-especialidad", nombre="Otra Especialidad"
    )
    delegado = _crear_delegado("88888", "88888888")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_otra)

    response = auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={"create": [{"delegado_id": str(delegado.id)}]},
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_batch_create_sin_operacion_vigente_400(
    auth_client,
    liquidacion,
    municipalidad,
    especialidades_disponibles_edificacion,
):
    """
    PATCH create con delegado sin operación vigente (sin especialidad_revision
    en la asignación municipal) → 400.

    La especialidad_revision ahora es obligatoria en la operación: un delegado
    sin operación no puede asignarse.
    """
    delegado = _crear_delegado("99999", "99999999")

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
    delegado = _crear_delegado("12345", "12345678")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)
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
    delegado = _crear_delegado("54321", "87654321")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)

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
    delegado = _crear_delegado("11112", "11112222")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)
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
    delegado = _crear_delegado("22221", "22221111")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)

    response = auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={"delete": [{"delegado_id": str(delegado.id)}]},
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_batch_create_en_liquidacion_io_400(
    auth_client,
    proyecto,
    municipalidad,
    tipo_inspeccion_obra,
    create_user,
):
    """
    PATCH create de delegados en una liquidación de Inspección de Obra → 400.

    La IO es una liquidación especial: no admite delegados (el inspector se
    asocia al tipo IO). El batch debe bloquearse sin importar el payload.
    """
    liquidacion_io = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        sub_total=0,
        total=0,
        usuario_creador=create_user,
    )

    response = auth_client.patch(
        f"/liquidaciones/{liquidacion_io.id}/delegados",
        json={"create": [{"delegado_id": str(uuid.uuid4())}]},
    )

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.content}"
    assert not LiquidacionDelegado.objects.filter(liquidacion=liquidacion_io).exists()


# ── PATCH delete con guardas de referencias financieras ───────────────────────

@pytest.mark.django_db
def test_batch_delete_sin_detalles_elimina_asignacion_y_conserva_liquidacion(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: una asignación de delegado SIN DetalleHonorarioDelegado.
    WHEN:  se quita el delegado de la liquidación.
    THEN:  la asignación se elimina y la LiquidacionGeneral sobrevive intacta.
    """
    delegado = _crear_delegado("30001", "30001001")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)
    LiquidacionDelegado.objects.create(
        liquidacion=liquidacion,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
    )

    response = _eliminar_delegado(auth_client, liquidacion, delegado)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    assert not LiquidacionDelegado.objects.filter(
        liquidacion=liquidacion, delegado=delegado
    ).exists()
    # La liquidación NO se toca.
    assert LiquidacionGeneral.objects.filter(id=liquidacion.id).exists()
    liquidacion.refresh_from_db()
    assert liquidacion.estado == EstadoLiquidacion.PENDIENTE
    assert liquidacion.numero_revision == 1


@pytest.mark.django_db
def test_batch_delete_detalles_huerfanos_elimina_detalle_y_asignacion(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: una asignación cuyos detalles NO tienen recibo_mensual (huérfanos).
    WHEN:  se quita el delegado de la liquidación.
    THEN:  el detalle huérfano se elimina primero y la asignación después.
    """
    delegado = _crear_delegado("30002", "30002002")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)
    asignacion = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
    )
    detalle_huerfano = _crear_detalle_honorario(
        liquidacion_delegado=asignacion,
        recibo_mensual=None,
    )

    response = _eliminar_delegado(auth_client, liquidacion, delegado)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    assert not DetalleHonorarioDelegado.objects.filter(id=detalle_huerfano.id).exists()
    assert not LiquidacionDelegado.objects.filter(id=asignacion.id).exists()
    assert response.json()["data"]["deleted"] == [str(delegado.id)]


@pytest.mark.django_db
def test_batch_delete_con_detalle_rh_mensual_409_no_cambia_nada(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: una asignación referenciada por un DetalleHonorarioDelegado con recibo_mensual.
    WHEN:  se quita el delegado de la liquidación.
    THEN:  409; la asignación, el detalle, el RH mensual y la liquidación quedan intactos.
    """
    delegado = _crear_delegado("30003", "30003003")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)
    asignacion = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
    )
    rh = _crear_rh_mensual(delegado)
    detalle = _crear_detalle_honorario(
        liquidacion_delegado=asignacion,
        recibo_mensual=rh,
    )

    response = _eliminar_delegado(auth_client, liquidacion, delegado)

    assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.content}"
    body = response.json()
    assert body["error"]["code"] == "CONFLICT"
    assert body["success"] is False
    # El mensaje identifica al delegado sin filtrar el UUID crudo.
    assert "30003" in body["error"]["message"]
    assert str(delegado.id) not in body["error"]["message"]
    # Nada se escribe ni se borra.
    assert LiquidacionDelegado.objects.filter(id=asignacion.id).exists()
    assert DetalleHonorarioDelegado.objects.filter(id=detalle.id).exists()
    assert DetalleHonorarioDelegado.objects.filter(
        liquidacion_delegado_id=asignacion.id, recibo_mensual_id=rh.id
    ).exists()
    # El RH mensual no se recalcula ni se elimina.
    rh.refresh_from_db()
    assert rh.sub_total == Decimal("1000.00")
    assert rh.renta_cip == Decimal("250.00")
    assert rh.aporte_codemu == Decimal("50.00")
    assert rh.fondo_comun == Decimal("100.00")
    assert rh.neto_honorario == Decimal("600.00")
    assert ReciboHonorarioDelegadoMensual.objects.filter(id=rh.id).exists()
    # La liquidación sobrevive.
    assert LiquidacionGeneral.objects.filter(id=liquidacion.id).exists()


@pytest.mark.django_db
def test_batch_delete_con_recibo_honorario_no_mensual_409(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: una asignación referenciada por un ReciboHonorarioDelegado (no mensual).
    WHEN:  se quita el delegado de la liquidación.
    THEN:  409 (NUNCA 500); la asignación y el recibo quedan intactos.
    """
    delegado = _crear_delegado("30004", "30004004")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)
    asignacion = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
    )
    recibo = _crear_recibo_honorario(asignacion)

    response = _eliminar_delegado(auth_client, liquidacion, delegado)

    assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.content}"
    body = response.json()
    assert body["error"]["code"] == "CONFLICT"
    assert str(delegado.id) not in body["error"]["message"]
    # Nada se escribe ni se borra.
    assert LiquidacionDelegado.objects.filter(id=asignacion.id).exists()
    assert ReciboHonorarioDelegado.objects.filter(id=recibo.id).exists()
    assert LiquidacionGeneral.objects.filter(id=liquidacion.id).exists()


@pytest.mark.django_db
def test_batch_delete_evalua_todas_las_asignaciones_por_especialidad(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: un delegado con DOS asignaciones en la misma liquidación (dos especialidades).
    WHEN:  se quita el delegado.
    THEN:  todas las asignaciones del delegado se evaluan y se eliminan.
    """
    especialidad_otra = EspecialidadRevision.objects.create(
        slug="otra-especialidad-quitar", nombre="Otra Especialidad Quitar"
    )
    delegado = _crear_delegado("30005", "30005005")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)

    asignacion_a = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
    )
    asignacion_b = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion,
        delegado=delegado,
        especialidad_revision=especialidad_otra,
    )
    detalle_huerfano = _crear_detalle_honorario(
        liquidacion_delegado=asignacion_b,
        recibo_mensual=None,
    )

    response = _eliminar_delegado(auth_client, liquidacion, delegado)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.content}"
    assert not LiquidacionDelegado.objects.filter(
        liquidacion=liquidacion, delegado=delegado
    ).exists()
    assert not LiquidacionDelegado.objects.filter(id=asignacion_a.id).exists()
    assert not LiquidacionDelegado.objects.filter(id=asignacion_b.id).exists()
    assert not DetalleHonorarioDelegado.objects.filter(id=detalle_huerfano.id).exists()
    assert LiquidacionGeneral.objects.filter(id=liquidacion.id).exists()


@pytest.mark.django_db
def test_batch_delete_bloqueado_en_una_especialidad_conserva_todas(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: un delegado con dos asignaciones; solo una tiene un detalle de RH mensual.
    WHEN:  se quita el delegado.
    THEN:  409 y NINGUNA asignación se elimina (se evalúan todas antes de escribir).
    """
    especialidad_otra = EspecialidadRevision.objects.create(
        slug="otra-especialidad-bloqueo", nombre="Otra Especialidad Bloqueo"
    )
    delegado = _crear_delegado("30006", "30006006")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)

    asignacion_libre = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
    )
    asignacion_bloqueada = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion,
        delegado=delegado,
        especialidad_revision=especialidad_otra,
    )
    rh = _crear_rh_mensual(delegado)
    _crear_detalle_honorario(
        liquidacion_delegado=asignacion_bloqueada,
        recibo_mensual=rh,
    )

    response = _eliminar_delegado(auth_client, liquidacion, delegado)

    assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.content}"
    assert LiquidacionDelegado.objects.filter(id=asignacion_libre.id).exists()
    assert LiquidacionDelegado.objects.filter(id=asignacion_bloqueada.id).exists()
    assert DetalleHonorarioDelegado.objects.filter(recibo_mensual_id=rh.id).exists()


@pytest.mark.django_db
def test_batch_delete_atomicidad_detalles_mixtos_no_escribe_nada(
    auth_client,
    liquidacion,
    municipalidad,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: una asignación con un detalle huérfano Y un detalle de RH mensual.
    WHEN:  se quita el delegado (la operación se rechaza).
    THEN:  409 y ningún detalle ni asignación fue borrado (atomicidad).
    """
    delegado = _crear_delegado("30007", "30007007")
    _crear_asignacion_municipal(delegado, municipalidad, especialidad=especialidad_estructuras)
    asignacion = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
    )
    detalle_huerfano = _crear_detalle_honorario(
        liquidacion_delegado=asignacion,
        recibo_mensual=None,
    )
    rh = _crear_rh_mensual(delegado)
    detalle_rh = _crear_detalle_honorario(
        liquidacion_delegado=asignacion,
        recibo_mensual=rh,
    )

    response = _eliminar_delegado(auth_client, liquidacion, delegado)

    assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.content}"
    # El detalle huérfano NO se borra: la operación se evalúa antes de escribir.
    assert DetalleHonorarioDelegado.objects.filter(id=detalle_huerfano.id).exists()
    assert DetalleHonorarioDelegado.objects.filter(id=detalle_rh.id).exists()
    assert LiquidacionDelegado.objects.filter(id=asignacion.id).exists()
    assert ReciboHonorarioDelegadoMensual.objects.filter(id=rh.id).exists()


@pytest.mark.django_db
def test_batch_delete_delegado_inexistente_404(
    auth_client,
    liquidacion,
):
    """
    GIVEN: un payload de delete con un delegado_id que no existe.
    WHEN:  se envía el batch.
    THEN:  404 (semántica de validación preservada, no 409 ni 500).
    """
    response = auth_client.patch(
        f"/liquidaciones/{liquidacion.id}/delegados",
        json={"delete": [{"delegado_id": str(uuid.uuid4())}]},
    )

    assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.content}"
