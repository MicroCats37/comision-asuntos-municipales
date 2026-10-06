"""
Integration tests for LiquidacionGeneral soft-delete with relation group cleanup.

Tests verify that when a LiquidacionGeneral is soft-deleted via
PATCH /liquidaciones/generales/{id}/eliminar:
1. The LiquidacionRelacionMiembro rows for that liquidacion are physically deleted
2. Other members in the same group remain
3. The group itself is retained (empty groups kept by design)

Uses Ninja TestClient (not Django Client) per test architecture contract.
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_grupo import (
    LiquidacionRelacionGrupo,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_miembro import (
    LiquidacionRelacionMiembro,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
    LiquidacionRelacionCoreService,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.entidades.domain.models import Entidad
from modules.liquidaciones.domain.models.proyecto import Proyecto


# Helper to create a distinct Proyecto per liquidation (OneToOne constraint)
def _make_proyecto(ubigeo_distrito, seq):
    entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento=f"20{seq:08d}",
    )
    return Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario=f"Propietario Batch4 {seq} SAC",
        direccion=f"Av. Batch4 {seq}",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento=f"20{seq:08d}",
        entidad_razon_social=f"Propietario Batch4 {seq} SAC",
    )


@pytest.fixture
def relacion_service(db):
    return LiquidacionRelacionCoreService()


@pytest.fixture
def liquidacion_con_grupo(
    db,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    create_user,
    relacion_service,
):
    """
    Create a LiquidacionGeneral with a relation group membership for testing.
    Returns (liquidacion, grupo_id, miembro_id).
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-DEL-001",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    grupo, miembro = relacion_service.crear_grupo_con_miembro(
        liquidacion=lg,
        relacion_key="PO-OBRA",
        numero_revision=1,
    )
    return lg, grupo.id, miembro.id


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_eliminar_liquidacion_quita_relacion_miembros(
    auth_client,
    liquidacion_con_grupo,
    relacion_service,
):
    """
    GIVEN: a LiquidacionGeneral with a group membership
    WHEN:  PATCH /liquidaciones/generales/{id}/eliminar is called (soft-delete)
    THEN:  LiquidacionRelacionMiembro rows for that liquidacion are physically deleted
           and the group is retained (empty)
    """
    lg, grupo_id, miembro_id = liquidacion_con_grupo

    # Verify membership exists before soft-delete
    assert LiquidacionRelacionMiembro.objects.filter(id=miembro_id).exists()
    assert LiquidacionRelacionGrupo.objects.filter(id=grupo_id).exists()

    # Soft-delete via HTTP endpoint
    response = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}/eliminar",
        json={"motivo": "Test batch 4 soft-delete cleanup"},
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    data = response.json()["data"]
    assert data["eliminado"] is True

    # Member row physically deleted
    assert not LiquidacionRelacionMiembro.objects.filter(id=miembro_id).exists()
    # Group also deleted (sole member was deleted)
    assert not LiquidacionRelacionGrupo.objects.filter(id=grupo_id).exists()


@pytest.mark.django_db
def test_eliminar_liquidacion_otros_miembros_permanecen(
    db,
    auth_client,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    create_user,
    relacion_service,
):
    """
    GIVEN: a group with two liquidacion members (rev1 and rev3)
    WHEN:  rev3 is soft-deleted via PATCH /eliminar
    THEN:  rev3's member row is deleted; rev1's member row remains; group stays
    """
    user = create_user

    lg_rev1 = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-DEL-002",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionEdificacion.objects.create(liquidacion=lg_rev1, numero=1)

    lg_rev3 = LiquidacionGeneral.objects.create(
        proyecto=_make_proyecto(ubigeo_distrito, seq=2),
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-DEL-003",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=3,
        sub_total=Decimal("0"),
        total=Decimal("0"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionEdificacion.objects.create(liquidacion=lg_rev3, numero=None)

    # Rev1 creates group
    grupo, miembro_rev1 = relacion_service.crear_grupo_con_miembro(
        liquidacion=lg_rev1,
        relacion_key="PO-OBRA",
        numero_revision=1,
    )
    # Rev3 joins the same group
    miembro_rev3, _ = relacion_service.agregar_miembro_a_grupo_de_previa(
        liquidacion_previa=lg_rev1,
        liquidacion_nueva=lg_rev3,
        relacion_key="PO-OBRA",
        numero_revision=3,
    )

    grupo_id = grupo.id

    # Soft-delete rev3 via HTTP
    response = auth_client.patch(
        f"/liquidaciones/generales/{lg_rev3.id}/eliminar",
        json={"motivo": "Test batch 4"},
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    assert response.json()["data"]["eliminado"] is True

    # rev3's member row is gone
    assert not LiquidacionRelacionMiembro.objects.filter(id=miembro_rev3.id).exists()
    # rev1's member row remains
    assert LiquidacionRelacionMiembro.objects.filter(id=miembro_rev1.id).exists()
    # group still exists
    assert LiquidacionRelacionGrupo.objects.filter(id=grupo_id).exists()


@pytest.mark.django_db
def test_eliminar_liquidacion_sin_grupo_exitoso(
    auth_client,
    tipo_edificacion,
    municipalidad,
    proyecto,
    igv_vigente,
    uit_vigente,
    create_user,
):
    """
    GIVEN: a LiquidacionGeneral with NO relation group membership
    WHEN:  PATCH /liquidaciones/generales/{id}/eliminar is called
    THEN:  soft-delete succeeds (no relation cleanup needed)
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-DEL-004",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    # Never added to any relation group
    response = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}/eliminar",
        json={"motivo": "Test soft-delete without group"},
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"
    assert response.json()["data"]["eliminado"] is True
