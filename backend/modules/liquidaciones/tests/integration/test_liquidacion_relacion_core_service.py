"""
Tests for LiquidacionRelacionCoreService.

Integration tests using Django DB — tests the service methods against the real ORM.

Covers:
- crear_grupo: unique codigo generation with retry on IntegrityError
- agregar_miembro: member creation and unique constraints
- crear_grupo_con_miembro: combined group+member creation for primera revision
- obtener_grupo_de_liquidacion: query by liquidacion
- agregar_miembro_a_grupo_de_previa: nueva revision path with backfill
"""

import pytest
from decimal import Decimal
from django.db import IntegrityError

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_grupo import (
    LiquidacionRelacionGrupo,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_miembro import (
    LiquidacionRelacionMiembro,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.entidades.domain.models import Entidad
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_core_service import (
    LiquidacionRelacionCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_key_helper import (
    generar_relacion_key,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion, TipoTramiteEdificaciones


@pytest.fixture
def relacion_service(db):
    """Service instance for tests."""
    return LiquidacionRelacionCoreService()


# Helper to create a new proyecto with a unique RUC (required because
# LiquidacionGeneral.proyecto is OneToOne — each proyecto = one liquidacion)


def _make_proyecto(ubigeo_distrito, seq):
    """Create a distinct Proyecto for each liquidation (OneToOne constraint)."""
    entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento=f"20{seq:08d}",
    )
    return Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario=f"Propietario Test {seq} SAC",
        direccion=f"Av. Test {seq}",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento=f"20{seq:08d}",
        entidad_razon_social=f"Propietario Test {seq} SAC",
    )


# ── crear_grupo ────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_crear_grupo_crea_grupo_valido(relacion_service):
    """
    WHEN: crear_grupo is called
    THEN: it returns a LiquidacionRelacionGrupo with a valid LQG-... codigo
    """
    grupo = relacion_service.crear_grupo()

    assert isinstance(grupo, LiquidacionRelacionGrupo)
    assert grupo.codigo.startswith("LQG-")
    parts = grupo.codigo.split("-")
    assert len(parts) == 4


@pytest.mark.django_db
def test_crear_grupo_guarda_en_db(relacion_service):
    """
    WHEN: crear_grupo is called
    THEN: the grupo is persisted in the database
    """
    grupo = relacion_service.crear_grupo()

    assert LiquidacionRelacionGrupo.objects.filter(id=grupo.id).exists()


@pytest.mark.django_db
def test_crear_grupo_codigo_es_unique(relacion_service):
    """
    WHEN: crear_grupo is called twice
    THEN: both grupos have unique codigos
    """
    grupo1 = relacion_service.crear_grupo()
    grupo2 = relacion_service.crear_grupo()

    assert grupo1.codigo != grupo2.codigo


# ── crear_grupo_con_reintento ──────────────────────────────────────────────


@pytest.mark.django_db
def test_crear_grupo_con_reintento_retorna_tupla(relacion_service):
    """
    WHEN: crear_grupo_con_reintento is called
    THEN: it returns (grupo, fue_reintentado) tuple
    """
    grupo, fue_reintentado = relacion_service.crear_grupo_con_reintento()

    assert isinstance(grupo, LiquidacionRelacionGrupo)
    assert isinstance(fue_reintentado, bool)


# ── agregar_miembro ───────────────────────────────────────────────────────


@pytest.mark.django_db
def test_agregar_miembro_crea_miembro(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: agregar_miembro is called with a grupo and liquidacion
    THEN: a LiquidacionRelacionMiembro is created and linked to the grupo
    """
    grupo = LiquidacionRelacionGrupo.objects.create(codigo="LQG-TEST-0001")
    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    miembro = relacion_service.agregar_miembro(
        grupo=grupo,
        liquidacion=lg,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=1,
    )

    assert isinstance(miembro, LiquidacionRelacionMiembro)
    assert miembro.grupo == grupo
    assert miembro.liquidacion == lg
    assert miembro.relacion_key == generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA)
    assert miembro.numero_revision == 1


@pytest.mark.django_db
def test_agregar_miembro_unique_constraint_grupo_key_revision(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: the same (grupo, relacion_key, numero_revision) combination is inserted twice
    THEN: IntegrityError is raised due to unique constraint
    """
    grupo = LiquidacionRelacionGrupo.objects.create(codigo="LQG-TEST-0002")
    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    relacion_service.agregar_miembro(
        grupo=grupo,
        liquidacion=lg,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=1,
    )

    # Different liquidacion but same (grupo, relacion_key, numero_revision) should fail
    lg2 = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=_make_proyecto(ubigeo_distrito, seq=2),
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    with pytest.raises(IntegrityError):
        relacion_service.agregar_miembro(
            grupo=grupo,
            liquidacion=lg2,
            relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
            numero_revision=1,
        )


@pytest.mark.django_db
def test_agregar_miembro_unique_constraint_liquidacion(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: a liquidacion that already has a group membership is added to another group
    THEN: IntegrityError is raised due to unique constraint on liquidacion
    """
    grupo1 = LiquidacionRelacionGrupo.objects.create(codigo="LQG-TEST-0003")
    grupo2 = LiquidacionRelacionGrupo.objects.create(codigo="LQG-TEST-0004")
    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    # First membership
    relacion_service.agregar_miembro(
        grupo=grupo1,
        liquidacion=lg,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=1,
    )

    # Same liquidacion in a different group should fail (unique_liquidacion_unico_grupo)
    with pytest.raises(IntegrityError):
        relacion_service.agregar_miembro(
            grupo=grupo2,
            liquidacion=lg,
            relacion_key="HU",
            numero_revision=1,
        )


# ── crear_grupo_con_miembro ───────────────────────────────────────────────


@pytest.mark.django_db
def test_crear_grupo_con_miembro_crea_ambos(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: crear_grupo_con_miembro is called
    THEN: both the grupo and the miembro are created
    """
    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    grupo, miembro = relacion_service.crear_grupo_con_miembro(
        liquidacion=lg,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=1,
    )

    assert isinstance(grupo, LiquidacionRelacionGrupo)
    assert isinstance(miembro, LiquidacionRelacionMiembro)
    assert miembro.grupo == grupo
    assert miembro.liquidacion == lg
    assert grupo.codigo.startswith("LQG-")


@pytest.mark.django_db
def test_crear_grupo_con_miembro_persisted(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: crear_grupo_con_miembro is called
    THEN: both grupo and miembro are persisted in DB
    """
    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    grupo, miembro = relacion_service.crear_grupo_con_miembro(
        liquidacion=lg,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=1,
    )

    assert LiquidacionRelacionGrupo.objects.filter(id=grupo.id).exists()
    assert LiquidacionRelacionMiembro.objects.filter(id=miembro.id).exists()


# ── obtener_grupo_de_liquidacion ─────────────────────────────────────────


@pytest.mark.django_db
def test_obtener_grupo_de_liquidacion_retorna_miembro(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: a liquidacion is a member of a group
    THEN: obtener_grupo_de_liquidacion returns the membership
    """
    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    grupo, _ = relacion_service.crear_grupo_con_miembro(
        liquidacion=lg,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=1,
    )

    miembro = relacion_service.obtener_grupo_de_liquidacion(lg)

    assert miembro is not None
    assert isinstance(miembro, LiquidacionRelacionMiembro)
    assert miembro.grupo == grupo
    assert miembro.relacion_key == generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA)


@pytest.mark.django_db
def test_obtener_grupo_de_liquidacion_retorna_none_cuando_no_existe(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: a liquidacion has no group membership
    THEN: obtener_grupo_de_liquidacion returns None
    """
    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    miembro = relacion_service.obtener_grupo_de_liquidacion(lg)

    assert miembro is None


# ── agregar_miembro_a_grupo_de_previa ──────────────────────────────────────


@pytest.mark.django_db
def test_agregar_miembro_a_grupo_de_previa_reutiliza_grupo_existente(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: liquidacion_previa has an existing group
    THEN: nueva liquidacion is added to the same group
    """
    lg_previa = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    lg_nueva = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=_make_proyecto(ubigeo_distrito, seq=2),
        tipo_liquidacion=tipo_edificacion,
        numero_revision=3,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    # Previa already has a group (primera revision)
    grupo, _ = relacion_service.crear_grupo_con_miembro(
        liquidacion=lg_previa,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=1,
    )

    # Nueva revision adds to same group
    miembro_nuevo, fue_backfill = relacion_service.agregar_miembro_a_grupo_de_previa(
        liquidacion_previa=lg_previa,
        liquidacion_nueva=lg_nueva,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=3,
    )

    assert fue_backfill is False
    assert miembro_nuevo.grupo == grupo
    assert miembro_nuevo.liquidacion == lg_nueva
    assert miembro_nuevo.numero_revision == 3

    # Previa member is still there
    assert LiquidacionRelacionMiembro.objects.filter(liquidacion=lg_previa).exists()


@pytest.mark.django_db
def test_agregar_miembro_a_grupo_de_previa_backfill_cuando_previa_sin_grupo(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: liquidacion_previa has no group (edge case — created before feature existed)
    THEN: a new group is created, previa is added as backfill, then nueva is added
    """
    lg_previa = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    lg_nueva = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=_make_proyecto(ubigeo_distrito, seq=2),
        tipo_liquidacion=tipo_edificacion,
        numero_revision=3,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    # Previa has NO group membership (simulating legacy data)
    assert relacion_service.obtener_grupo_de_liquidacion(lg_previa) is None

    # Nueva revision should create a new group, backfill previa, then add nueva
    miembro_nuevo, fue_backfill = relacion_service.agregar_miembro_a_grupo_de_previa(
        liquidacion_previa=lg_previa,
        liquidacion_nueva=lg_nueva,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=3,
    )

    assert fue_backfill is True
    # Nueva member is in the new group
    assert miembro_nuevo.grupo is not None
    assert miembro_nuevo.liquidacion == lg_nueva

    # Previa was backfilled — now has a member record too
    miembro_previa = LiquidacionRelacionMiembro.objects.get(liquidacion=lg_previa)
    assert miembro_previa.grupo == miembro_nuevo.grupo
    assert miembro_previa.relacion_key == generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA)
    assert miembro_previa.numero_revision == 1


@pytest.mark.django_db
def test_agregar_miembro_a_grupo_de_previa_multiple_revisiones(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    GIVEN: revision 1 has a group
    WHEN: revision 3 is added
    THEN: revision 5 can be added to the same group
    """
    lg_rev1 = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    lg_rev3 = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=_make_proyecto(ubigeo_distrito, seq=2),
        tipo_liquidacion=tipo_edificacion,
        numero_revision=3,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    lg_rev5 = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=_make_proyecto(ubigeo_distrito, seq=3),
        tipo_liquidacion=tipo_edificacion,
        numero_revision=5,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    # Rev1 creates group
    _, _ = relacion_service.crear_grupo_con_miembro(
        liquidacion=lg_rev1,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=1,
    )

    # Rev3 joins the group
    _, fue_b1 = relacion_service.agregar_miembro_a_grupo_de_previa(
        liquidacion_previa=lg_rev1,
        liquidacion_nueva=lg_rev3,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=3,
    )
    assert fue_b1 is False

    grupo_rev3 = LiquidacionRelacionMiembro.objects.get(liquidacion=lg_rev3).grupo

    # Rev5 joins the same group
    _, fue_b2 = relacion_service.agregar_miembro_a_grupo_de_previa(
        liquidacion_previa=lg_rev3,
        liquidacion_nueva=lg_rev5,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=5,
    )
    assert fue_b2 is False

    grupo_rev5 = LiquidacionRelacionMiembro.objects.get(liquidacion=lg_rev5).grupo
    assert grupo_rev5 == grupo_rev3  # Same group

    # All 3 members in same group
    miembros = LiquidacionRelacionMiembro.objects.filter(grupo=grupo_rev5)
    assert miembros.count() == 3


# ── eliminar_miembros_de_liquidacion ─────────────────────────────────────


@pytest.mark.django_db
def test_eliminar_miembros_de_liquidacion_elimina_miembros(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: eliminar_miembros_de_liquidacion is called for a liquidacion with a group membership
    THEN: all LiquidacionRelacionMiembro rows for that liquidacion are physically deleted
    """
    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    grupo, miembro = relacion_service.crear_grupo_con_miembro(
        liquidacion=lg,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=1,
    )

    # Verify member exists before deletion
    assert LiquidacionRelacionMiembro.objects.filter(id=miembro.id).exists()

    members_deleted, groups_deleted = relacion_service.eliminar_miembros_de_liquidacion(lg)

    assert members_deleted == 1
    assert groups_deleted == 1
    assert not LiquidacionRelacionMiembro.objects.filter(id=miembro.id).exists()
    # Group is deleted because it had only one member
    assert not LiquidacionRelacionGrupo.objects.filter(id=grupo.id).exists()


@pytest.mark.django_db
def test_eliminar_miembros_de_liquidacion_otros_miembros_permanecen(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: a liquidacion with multiple group members is soft-deleted
    THEN: only its own member row is deleted; other members in the same group remain
    """
    # Revision 1
    lg_rev1 = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    # Revision 3 — same group
    lg_rev3 = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=_make_proyecto(ubigeo_distrito, seq=2),
        tipo_liquidacion=tipo_edificacion,
        numero_revision=3,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    # Rev1 creates group
    grupo, _ = relacion_service.crear_grupo_con_miembro(
        liquidacion=lg_rev1,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=1,
    )
    # Rev3 joins same group
    miembro_rev3, _ = relacion_service.agregar_miembro_a_grupo_de_previa(
        liquidacion_previa=lg_rev1,
        liquidacion_nueva=lg_rev3,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=3,
    )

    # Verify both members exist
    assert LiquidacionRelacionMiembro.objects.filter(liquidacion=lg_rev1).exists()
    assert LiquidacionRelacionMiembro.objects.filter(liquidacion=lg_rev3).exists()

    # Soft-delete rev3 (via relation cleanup)
    members_deleted, groups_deleted = relacion_service.eliminar_miembros_de_liquidacion(lg_rev3)

    assert members_deleted == 1
    assert groups_deleted == 0  # Group still has rev1, so not deleted
    # rev3 member is gone
    assert not LiquidacionRelacionMiembro.objects.filter(id=miembro_rev3.id).exists()
    # rev1 member remains
    assert LiquidacionRelacionMiembro.objects.filter(liquidacion=lg_rev1).exists()
    # group still exists
    assert LiquidacionRelacionGrupo.objects.filter(id=grupo.id).exists()


@pytest.mark.django_db
def test_eliminar_miembros_de_liquidacion_sole_member_deletes_group(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: a sole member of a group is deleted via eliminar_miembros_de_liquidacion
    THEN: the group itself IS deleted (member was the last/only one)
    """
    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )
    grupo, _ = relacion_service.crear_grupo_con_miembro(
        liquidacion=lg,
        relacion_key=generar_relacion_key(TipoLiquidacion.EDIFICACION, TipoTramiteEdificaciones.OBRA_NUEVA),
        numero_revision=1,
    )
    grupo_id = grupo.id

    members_deleted, groups_deleted = relacion_service.eliminar_miembros_de_liquidacion(lg)

    assert members_deleted == 1
    assert groups_deleted == 1
    # Both member and group are gone
    assert not LiquidacionRelacionMiembro.objects.filter(grupo_id=grupo_id).exists()
    assert not LiquidacionRelacionGrupo.objects.filter(id=grupo_id).exists()


@pytest.mark.django_db
def test_eliminar_miembros_de_liquidacion_sin_grupo_retorna_cero(
    db,
    relacion_service,
    tipo_edificacion,
    municipalidad,
    ubigeo_distrito,
    proyecto,
):
    """
    WHEN: eliminar_miembros_de_liquidacion is called for a liquidacion with no group membership
    THEN: it returns 0 and does not error
    """
    lg = LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    # This liquidacion was never added to any group
    assert relacion_service.obtener_grupo_de_liquidacion(lg) is None

    members_deleted, groups_deleted = relacion_service.eliminar_miembros_de_liquidacion(lg)

    assert members_deleted == 0
    assert groups_deleted == 0
