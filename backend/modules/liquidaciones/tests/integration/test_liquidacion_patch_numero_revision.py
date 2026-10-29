"""
Integration tests for the editable revision number on the liquidacion PATCH paths.

`numero_revision` is an EDITABLE LABEL chosen by the client: the backend stores the
submitted value verbatim (never derives it, never recalculates it) and keeps the
`LiquidacionRelacionMiembro` row in sync with the SAME value inside the SAME
transaction.

Tests cover:
- PATCH /liquidaciones/generales/{id} edits the revision of a PENDIENTE liquidacion
- The header (LiquidacionGeneral) and the relation member are synchronized
- Omitting `numero_revision` preserves the stored value
- The contract rejects a revision outside {1, 3, 5} / MAX_REVISIONES
- PAGADA still blocks every edit (existing edit-state rule preserved)
- A liquidacion without a relation member updates ONLY the header (no invented lineage)
- Inspección de Obra stays revision-less (fixed at revision 1) and its own PATCH
  contract does not accept `numero_revision`

Fixtures are shared via conftest.py (tests/conftest.py).
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_grupo import (
    LiquidacionRelacionGrupo,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_miembro import (
    LiquidacionRelacionMiembro,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_patch_visitas_schemas import (
    LiquidacionPatchVisitasGeneralIn,
)
from modules.liquidaciones.tests.fixtures.factories import (
    make_patch_general_payload,
    make_patch_wrapper_general_payload,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def liquidacion_edificacion_con_miembro(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
    tipo_edificacion,
):
    """
    Edificaciones liquidacion in PENDIENTE at revision 1, WITH a relation member.

    Returns (liquidacion, miembro).
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-REV-EDITABLE-001",
        observacion="Test liquidacion con miembro de relacion",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )

    grupo = LiquidacionRelacionGrupo.objects.create(codigo="GRUPO-REV-EDITABLE-001")
    miembro = LiquidacionRelacionMiembro.objects.create(
        grupo=grupo,
        liquidacion=lg,
        relacion_key="EDIFICACION-OBRA_NUEVA",
        numero_revision=1,
    )

    return lg, miembro


@pytest.fixture
def liquidacion_edificacion_sin_miembro(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
    tipo_edificacion,
):
    """
    Edificaciones liquidacion in PENDIENTE at revision 1 WITHOUT a relation member.
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-REV-SIN-MIEMBRO-001",
        observacion="Test liquidacion sin miembro de relacion",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )

    return lg


@pytest.fixture
def liquidacion_edificacion_pagada(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
    tipo_edificacion,
):
    """Edificaciones liquidacion already in PAGADA state (with a relation member)."""
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-REV-PAGADA-001",
        observacion="Test liquidacion pagada",
        estado=EstadoLiquidacion.PAGADA,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    grupo = LiquidacionRelacionGrupo.objects.create(codigo="GRUPO-REV-PAGADA-001")
    miembro = LiquidacionRelacionMiembro.objects.create(
        grupo=grupo,
        liquidacion=lg,
        relacion_key="EDIFICACION-OBRA_NUEVA",
        numero_revision=1,
    )

    return lg, miembro


@pytest.fixture
def liquidacion_io_revision_1(
    db,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tarifa_visitas_io,
    tipo_inspeccion_obra,
):
    """Inspeccion Obra liquidacion in PENDIENTE, fixed at revision 1."""
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-IO-REVISION-1",
        observacion="Test IO revisionless",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("1200.00"),
        total=Decimal("1416.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionInspeccionObra.objects.create(liquidacion=lg, numero=1)

    LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=5,
        porcentaje_uit=Decimal("0.05"),
        categoria="INSPECCION",
        tarifa_aplicada=tarifa_visitas_io,
    )

    return lg


# ── Tests: PATCH general edits the revision ────────────────────────────────────

@pytest.mark.django_db
def test_patch_general_actualiza_numero_revision_en_cabecera_y_miembro(
    auth_client,
    liquidacion_edificacion_con_miembro,
):
    """
    PATCH /liquidaciones/generales/{id} with numero_revision=3 stores 3 on the
    LiquidacionGeneral AND on its LiquidacionRelacionMiembro (same submitted value).
    """
    lg, miembro = liquidacion_edificacion_con_miembro

    response = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}",
        json=make_patch_general_payload(numero_revision=3),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg.refresh_from_db()
    miembro.refresh_from_db()

    assert lg.numero_revision == 3, "Header must store the submitted revision"
    assert miembro.numero_revision == 3, "Relation member must store the same revision"


@pytest.mark.django_db
def test_patch_general_actualiza_numero_revision_a_5(
    auth_client,
    liquidacion_edificacion_con_miembro,
):
    """
    The submitted revision is stored verbatim: 5 is accepted and stored as 5
    (no derivation from the previous value).
    """
    lg, miembro = liquidacion_edificacion_con_miembro

    response = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}",
        json=make_patch_general_payload(numero_revision=5),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg.refresh_from_db()
    miembro.refresh_from_db()

    assert lg.numero_revision == 5
    assert miembro.numero_revision == 5


@pytest.mark.django_db
def test_patch_general_sin_numero_revision_conserva_el_valor(
    auth_client,
    liquidacion_edificacion_con_miembro,
):
    """
    Omitting numero_revision preserves the stored revision on both the header
    and the relation member.
    """
    lg, miembro = liquidacion_edificacion_con_miembro

    response = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}",
        json=make_patch_general_payload(expediente="EXP-SIN-REV-001"),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg.refresh_from_db()
    miembro.refresh_from_db()

    assert lg.expediente == "EXP-SIN-REV-001"
    assert lg.numero_revision == 1, "Stored revision must be preserved"
    assert miembro.numero_revision == 1, "Member revision must be preserved"


@pytest.mark.django_db
@pytest.mark.parametrize("numero_revision", [0, 2, 4, 6, -1])
def test_patch_general_numero_revision_fuera_del_conjunto_permitido_es_rechazado(
    auth_client,
    liquidacion_edificacion_con_miembro,
    numero_revision,
):
    """
    The contract rejects a revision outside {1, 3, 5} (and above MAX_REVISIONES).
    Nothing is written.
    """
    lg, miembro = liquidacion_edificacion_con_miembro

    response = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}",
        json=make_patch_general_payload(numero_revision=numero_revision),
    )

    assert response.status_code == 422, \
        f"Expected 422 for numero_revision={numero_revision}, got {response.status_code}: {response.content}"

    lg.refresh_from_db()
    miembro.refresh_from_db()

    assert lg.numero_revision == 1, "Header revision must not change"
    assert miembro.numero_revision == 1, "Member revision must not change"


@pytest.mark.django_db
def test_patch_general_pagada_rechaza_edicion_de_numero_revision(
    auth_client,
    liquidacion_edificacion_pagada,
):
    """
    The existing edit-state rule is preserved: PAGADA blocks every edit,
    including the revision number.
    """
    lg, miembro = liquidacion_edificacion_pagada

    response = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}",
        json=make_patch_general_payload(numero_revision=3),
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA, got {response.status_code}: {response.content}"

    lg.refresh_from_db()
    miembro.refresh_from_db()

    assert lg.numero_revision == 1, "Header revision must not change"
    assert miembro.numero_revision == 1, "Member revision must not change"


@pytest.mark.django_db
def test_patch_general_sin_miembro_actualiza_solo_la_cabecera(
    auth_client,
    liquidacion_edificacion_sin_miembro,
):
    """
    A liquidacion without a relation member updates ONLY the header — no lineage
    is invented (no member row is created).
    """
    lg = liquidacion_edificacion_sin_miembro

    response = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}",
        json=make_patch_general_payload(numero_revision=5),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg.refresh_from_db()

    assert lg.numero_revision == 5, "Header must store the submitted revision"
    assert not LiquidacionRelacionMiembro.objects.filter(liquidacion=lg).exists(), \
        "No relation member may be invented for a liquidacion that had none"


@pytest.mark.django_db
def test_patch_general_actualiza_numero_revision_junto_con_campos_genericos(
    auth_client,
    liquidacion_edificacion_con_miembro,
):
    """
    numero_revision can be edited together with the other generic fields in a
    single PATCH request.
    """
    lg, miembro = liquidacion_edificacion_con_miembro

    response = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}",
        json=make_patch_general_payload(
            numero_revision=3,
            expediente="EXP-REV-EDITABLE-COMBO",
            observacion="Observacion combinada",
        ),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg.refresh_from_db()
    miembro.refresh_from_db()

    assert lg.expediente == "EXP-REV-EDITABLE-COMBO"
    assert lg.observacion == "Observacion combinada"
    assert lg.numero_revision == 3
    assert miembro.numero_revision == 3


# ── Tests: Inspección de Obra stays revision-less ──────────────────────────────

@pytest.mark.django_db
def test_patch_general_io_conserva_revision_1(
    auth_client,
    liquidacion_io_revision_1,
):
    """
    Inspección de Obra is revision-less: a general PATCH carrying numero_revision
    does NOT move it away from revision 1.
    """
    lg = liquidacion_io_revision_1

    response = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}",
        json=make_patch_general_payload(numero_revision=3),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg.refresh_from_db()

    assert lg.numero_revision == 1, \
        "Inspección de Obra must stay fixed at revision 1"


@pytest.mark.django_db
def test_patch_io_no_edita_el_numero_revision(
    auth_client,
    liquidacion_io_revision_1,
):
    """
    The Inspección de Obra PATCH contract does not expose numero_revision: the
    field is not part of the contract, so it is ignored and the revision stays
    fixed at 1.
    """
    lg = liquidacion_io_revision_1

    assert "numero_revision" not in LiquidacionPatchVisitasGeneralIn.model_fields, \
        "The IO PATCH contract must not expose numero_revision"

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{lg.id}",
        json=make_patch_wrapper_general_payload(numero_revision=3),
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg.refresh_from_db()

    assert lg.numero_revision == 1, \
        "Inspección de Obra must stay fixed at revision 1"


# ── Tests: delete after an editable revision ───────────────────────────────────

@pytest.mark.django_db
def test_eliminar_liquidacion_con_revision_editada_conserva_los_hermanos(
    auth_client,
    liquidacion_edificacion_con_miembro,
):
    """
    Deleting a liquidacion whose revision was edited removes ONLY its own
    relation member — the sibling member of the group survives.
    """
    from modules.entidades.domain.models import Entidad
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    lg, miembro = liquidacion_edificacion_con_miembro

    # A sibling liquidacion in the same group (same relacion_key, revision 1).
    entidad = Entidad.objects.create(tipo_documento="RUC", numero_documento="20456789088")
    proyecto_hermano = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Hermano SAC",
        direccion="Av. Hermano 789, Lima",
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789088",
        entidad_razon_social="Propietario Hermano SAC",
    )
    hermano = LiquidacionGeneral.objects.create(
        proyecto=proyecto_hermano,
        municipalidad=lg.municipalidad,
        usuario_creador=lg.usuario_creador,
        expediente="EXP-HERMANO-DELETE",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=lg.tipo_liquidacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
    )
    LiquidacionEdificacion.objects.create(liquidacion=hermano, numero=2)
    miembro_hermano = LiquidacionRelacionMiembro.objects.create(
        grupo=miembro.grupo,
        liquidacion=hermano,
        relacion_key="EDIFICACION-OBRA_NUEVA",
        numero_revision=1,
    )

    # Edit the revision of the liquidacion that will be deleted.
    response_patch = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}",
        json=make_patch_general_payload(numero_revision=5),
    )
    assert response_patch.status_code == 200, \
        f"Expected 200, got {response_patch.status_code}: {response_patch.content}"

    # Delete it (soft delete) — the member row is physically removed.
    response_delete = auth_client.patch(
        f"/liquidaciones/generales/{lg.id}/eliminar",
        json={"motivo": "Prueba de eliminacion tras editar la revision"},
    )
    assert response_delete.status_code == 200, \
        f"Expected 200, got {response_delete.status_code}: {response_delete.content}"

    assert not LiquidacionRelacionMiembro.objects.filter(id=miembro.id).exists(), \
        "The deleted liquidacion must not keep its relation member"
    assert LiquidacionRelacionMiembro.objects.filter(id=miembro_hermano.id).exists(), \
        "The sibling member must survive the deletion"
