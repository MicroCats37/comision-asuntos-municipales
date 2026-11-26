"""Focused tests for the non-legacy IO inspector/contact reconciliation command.

The tests materialize the exact state described by the closed manifest
(contaminated rows + their legitimate and legacy counterparts) with manageable
ORM fixtures. The real dump is never required.
"""

from __future__ import annotations

import ast
import csv
import itertools
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test.utils import CaptureQueriesContext
from django.db import connection

from modules.entidades.domain.models import Entidad
from modules.entidades.domain.models.contacto import Contacto
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    InspectorOperacion,
    LiquidacionInspector,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionContacto,
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.management.commands.correct_nonlegacy_io_inspector_collisions import (
    CONTACTO_COLLISIONS,
    INSPECTOR_COLLISIONS,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)

COMMAND = "correct_nonlegacy_io_inspector_collisions"


# ── Fixture that materializes the manifest state ───────────────────────────────


@pytest.fixture
def manifest_state(db, municipalidad, ubigeo_distrito, tipo_inspeccion_obra):
    """Build the contaminated / legitimate / legacy rows described by the manifest."""
    rucs = itertools.count(1)
    liquidaciones: dict[str, LiquidacionGeneral] = {}
    contactos: dict[str, Contacto] = {}
    inspectores: dict[str, Inspector] = {}
    operaciones: dict[str, InspectorOperacion] = {}
    legit_cip = itertools.count(900001)

    def make_proyecto():
        ruc = f"20{next(rucs):09d}"
        entidad = Entidad.objects.create(tipo_documento="RUC", numero_documento=ruc)
        return Proyecto.objects.create(
            entidad=entidad,
            nombre_propietario=f"Propietario {ruc}",
            direccion="Av. Test 123",
            distrito_id=ubigeo_distrito.id,
            entidad_tipo_documento="RUC",
            entidad_numero_documento=ruc,
            entidad_razon_social=f"Propietario {ruc}",
        )

    def get_liquidacion(liquidacion_id: str, legacy: bool, numero: int):
        if liquidacion_id in liquidaciones:
            return liquidaciones[liquidacion_id]
        liquidacion = LiquidacionGeneral.objects.create(
            id=liquidacion_id,
            proyecto=make_proyecto(),
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_inspeccion_obra,
            total=Decimal("1000.00"),
            sub_total=Decimal("1000.00"),
            legacy=legacy,
            numero_revision=1,
        )
        LiquidacionInspeccionObra.objects.create(liquidacion=liquidacion, numero=numero)
        liquidaciones[liquidacion_id] = liquidacion
        return liquidacion

    def get_contacto(contacto_id: str, nombres: str, apellidos: str, telefono: str):
        if contacto_id in contactos:
            return contactos[contacto_id]
        contacto = Contacto.objects.create(
            id=contacto_id,
            nombres=nombres,
            apellidos=apellidos,
            telefono=telefono,
        )
        contactos[contacto_id] = contacto
        return contacto

    def get_inspector(inspector_id: str, cip: str):
        if inspector_id in inspectores:
            return inspectores[inspector_id]
        perfil = PerfilIngeniero.objects.create(
            cip=cip,
            dni=f"8{cip}",
            nombres="Inspector",
            apellido_paterno="Perez",
            apellido_materno="Garcia",
            correo_personal=f"{cip}@test.com",
        )
        inspector = Inspector.objects.create(id=inspector_id, perfil_ingeniero=perfil)
        inspectores[inspector_id] = inspector
        return inspector

    especialidad = EspecialidadRevision.objects.create(
        id=INSPECTOR_COLLISIONS[0].especialidad_revision_id,
        slug="civil",
        nombre="Ingenieria Civil",
    )

    def get_operacion(operacion_id: str, inspector: Inspector):
        if operacion_id in operaciones:
            return operaciones[operacion_id]
        operacion = InspectorOperacion.objects.create(
            id=operacion_id,
            inspector=inspector,
            tipo_liquidacion=tipo_inspeccion_obra,
            categoria="A",
            especialidad_revision=especialidad,
        )
        operaciones[operacion_id] = operacion
        return operacion

    def force_times(model, pk, created_at):
        model.objects.filter(id=pk).update(created_at=created_at, updated_at=created_at)

    for item in INSPECTOR_COLLISIONS:
        inspector = get_inspector(item.inspector_id, item.cip)
        operacion = get_operacion(item.inspector_operacion_id, inspector)

        liquidacion = get_liquidacion(
            item.liquidacion_id, legacy=False, numero=item.numero
        )
        visitas = LiquidacionPorCategoriaVisitas.objects.create(
            id=item.visitas_id,
            liquidacion_general=liquidacion,
            cantidad_visitas=1,
            categoria="A",
        )

        legit_inspector = get_inspector(item.legit_inspector_id, str(next(legit_cip)))
        legit_operacion_id = str(
            uuid.uuid5(uuid.NAMESPACE_DNS, f"legit-operacion-{item.legit_inspector_id}")
        )
        legit_operacion = get_operacion(legit_operacion_id, legit_inspector)
        LiquidacionInspector.objects.create(
            id=item.legit_link_id,
            liquidacion=visitas,
            inspector=legit_inspector,
            inspector_operacion=legit_operacion,
            especialidad_revision=especialidad,
        )

        LiquidacionInspector.objects.create(
            id=item.link_id,
            liquidacion=visitas,
            inspector=inspector,
            inspector_operacion=operacion,
            especialidad_revision=especialidad,
        )
        force_times(LiquidacionInspector, item.link_id, item.created_at)

        legacy_liquidacion = get_liquidacion(
            item.legacy_liquidacion_id, legacy=True, numero=item.numero
        )
        legacy_visitas = LiquidacionPorCategoriaVisitas.objects.create(
            id=item.legacy_visitas_id,
            liquidacion_general=legacy_liquidacion,
            cantidad_visitas=1,
            categoria="A",
        )
        LiquidacionInspector.objects.create(
            id=item.legacy_link_id,
            liquidacion=legacy_visitas,
            inspector=inspector,
            inspector_operacion=operacion,
            especialidad_revision=especialidad,
        )

    for item in CONTACTO_COLLISIONS:
        liquidacion = get_liquidacion(
            item.liquidacion_id, legacy=False, numero=item.numero
        )

        if item.legit_contacto_id:
            get_contacto(item.legit_contacto_id, "Legitimo", "Contacto", "000000000")
            LiquidacionGeneral.objects.filter(id=item.liquidacion_id).update(
                contacto_id=item.legit_contacto_id
            )

        duplicado = get_contacto(
            item.contacto_id, item.nombres, item.apellidos, item.telefono
        )
        force_times(Contacto, item.contacto_id, item.contacto_created_at)

        LiquidacionContacto.objects.create(
            id=item.link_id,
            liquidacion=liquidacion,
            contacto=duplicado,
            principal=True,
        )
        force_times(LiquidacionContacto, item.link_id, item.created_at)

        legacy_liquidacion = get_liquidacion(
            item.legacy_liquidacion_id, legacy=True, numero=item.numero
        )
        legacy_contacto = get_contacto(
            item.legacy_contacto_id, item.nombres, item.apellidos, item.telefono
        )
        LiquidacionContacto.objects.create(
            id=item.legacy_link_id,
            liquidacion=legacy_liquidacion,
            contacto=legacy_contacto,
            principal=True,
        )

    return {
        "liquidaciones": liquidaciones,
        "contactos": contactos,
        "inspectores": inspectores,
        "especialidad": especialidad,
    }


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def run_command(csv_path, apply=False):
    args = [COMMAND, "--csv-output", str(csv_path)]
    if apply:
        args.append("--apply")
    call_command(*args)


# ── Manifest contract ──────────────────────────────────────────────────────────


def test_manifest_is_closed_and_covers_exactly_the_contaminated_rows():
    assert len(INSPECTOR_COLLISIONS) == 17
    assert len(CONTACTO_COLLISIONS) == 29
    assert sorted(item.numero for item in INSPECTOR_COLLISIONS) == [
        16,
        18,
        23,
        28,
        37,
        38,
        56,
        60,
        64,
        65,
        69,
        71,
        73,
        80,
        83,
        84,
        87,
    ]
    assert sorted(item.numero for item in CONTACTO_COLLISIONS) == [
        8,
        16,
        21,
        22,
        23,
        24,
        26,
        28,
        29,
        34,
        37,
        38,
        49,
        50,
        56,
        59,
        60,
        61,
        64,
        68,
        69,
        70,
        71,
        73,
        80,
        83,
        84,
        86,
        87,
    ]

    link_ids = [item.link_id for item in INSPECTOR_COLLISIONS] + [
        item.link_id for item in CONTACTO_COLLISIONS
    ]
    assert len(set(link_ids)) == 46


def test_manifest_never_keys_by_io_number_or_cip():
    """The delete key is always the link UUID, never the IO number nor the CIP."""
    assert all(item.link_id for item in INSPECTOR_COLLISIONS)
    assert all(item.link_id for item in CONTACTO_COLLISIONS)
    # Two different IOs share the same contaminated inspector/CIP: deleting by
    # number or CIP would be ambiguous, the UUID is not.
    shared_cip = [item for item in INSPECTOR_COLLISIONS if item.cip == "011470"]
    assert len(shared_cip) == 15


# ── Dry run ────────────────────────────────────────────────────────────────────


def test_dry_run_does_not_write_and_emits_one_row_per_manifest_item(
    manifest_state, tmp_path
):
    csv_path = tmp_path / "dry-run.csv"

    run_command(csv_path)

    rows = read_csv(csv_path)
    assert len(rows) == 46
    assert sum(row["status"] == "DELETE_LINK" for row in rows) == 17
    assert sum(row["status"] == "DELETE_LINK_AND_CONTACTO_ENTITY" for row in rows) == 29
    assert all(row["accion"] == "DELETE" for row in rows)
    assert all(row["evidencia"] for row in rows)

    # Nothing was deleted.
    assert (
        LiquidacionInspector.objects.filter(
            id__in=[item.link_id for item in INSPECTOR_COLLISIONS]
        ).count()
        == 17
    )
    assert (
        LiquidacionContacto.objects.filter(
            id__in=[item.link_id for item in CONTACTO_COLLISIONS]
        ).count()
        == 29
    )
    assert (
        Contacto.objects.filter(
            id__in=[item.contacto_id for item in CONTACTO_COLLISIONS]
        ).count()
        == 29
    )


def test_csv_output_is_required(manifest_state):
    with pytest.raises(CommandError):
        call_command(COMMAND)


# ── Apply ──────────────────────────────────────────────────────────────────────


def test_apply_deletes_exactly_the_manifest_rows(manifest_state, tmp_path):
    csv_path = tmp_path / "apply.csv"

    run_command(csv_path, apply=True)

    rows = read_csv(csv_path)
    assert len(rows) == 46
    assert sum(row["status"] == "DELETE_LINK" for row in rows) == 17
    assert sum(row["status"] == "DELETE_LINK_AND_CONTACTO_ENTITY" for row in rows) == 29

    # Contaminated rows are gone.
    assert not LiquidacionInspector.objects.filter(
        id__in=[item.link_id for item in INSPECTOR_COLLISIONS]
    ).exists()
    assert not LiquidacionContacto.objects.filter(
        id__in=[item.link_id for item in CONTACTO_COLLISIONS]
    ).exists()
    assert not Contacto.objects.filter(
        id__in=[item.contacto_id for item in CONTACTO_COLLISIONS]
    ).exists()

    # Legitimate and legacy rows survive untouched.
    assert (
        LiquidacionInspector.objects.filter(
            id__in=[item.legit_link_id for item in INSPECTOR_COLLISIONS]
        ).count()
        == 17
    )
    assert (
        LiquidacionInspector.objects.filter(
            id__in=[item.legacy_link_id for item in INSPECTOR_COLLISIONS]
        ).count()
        == 17
    )
    assert (
        LiquidacionContacto.objects.filter(
            id__in=[item.legacy_link_id for item in CONTACTO_COLLISIONS]
        ).count()
        == 29
    )
    assert (
        Contacto.objects.filter(
            id__in=[item.legacy_contacto_id for item in CONTACTO_COLLISIONS]
        ).count()
        == 29
    )
    assert (
        LiquidacionGeneral.objects.filter(
            id__in=[item.legacy_liquidacion_id for item in INSPECTOR_COLLISIONS]
            + [item.legacy_liquidacion_id for item in CONTACTO_COLLISIONS],
            legacy=True,
        ).count()
        == 31
    )


def test_apply_preserves_io23_legacy_and_current_inspector(manifest_state, tmp_path):
    io23_inspector = next(item for item in INSPECTOR_COLLISIONS if item.numero == 23)
    io23_contacto = next(item for item in CONTACTO_COLLISIONS if item.numero == 23)

    run_command(tmp_path / "apply.csv", apply=True)

    # Legacy side of IO 23 is intact.
    assert LiquidacionInspector.objects.filter(
        id=io23_inspector.legacy_link_id
    ).exists()
    assert LiquidacionContacto.objects.filter(id=io23_contacto.legacy_link_id).exists()
    assert Contacto.objects.filter(id=io23_contacto.legacy_contacto_id).exists()
    assert LiquidacionGeneral.objects.filter(
        id=io23_inspector.legacy_liquidacion_id, legacy=True
    ).exists()

    # Legitimate current inspector of IO 23 is intact.
    assert LiquidacionInspector.objects.filter(id=io23_inspector.legit_link_id).exists()
    assert (
        str(
            LiquidacionInspector.objects.filter(id=io23_inspector.legit_link_id)
            .first()
            .inspector_id
        )
        == io23_inspector.legit_inspector_id
    )

    # The legitimate contact of the current liquidacion is intact.
    assert (
        str(
            LiquidacionGeneral.objects.filter(id=io23_contacto.liquidacion_id)
            .first()
            .contacto_id
        )
        == io23_contacto.legit_contacto_id
    )

    # Only the contaminated rows were removed.
    assert not LiquidacionInspector.objects.filter(id=io23_inspector.link_id).exists()
    assert not LiquidacionContacto.objects.filter(id=io23_contacto.link_id).exists()
    assert not Contacto.objects.filter(id=io23_contacto.contacto_id).exists()


def test_second_apply_is_idempotent(manifest_state, tmp_path):
    run_command(tmp_path / "first.csv", apply=True)
    inspectors_after_first = LiquidacionInspector.objects.count()
    contactos_after_first = LiquidacionContacto.objects.count()
    entidades_after_first = Contacto.objects.count()

    run_command(tmp_path / "second.csv", apply=True)

    rows = read_csv(tmp_path / "second.csv")
    assert len(rows) == 46
    assert all(row["status"] == "ALREADY_CLEAN" for row in rows)
    assert all(row["accion"] == "NONE" for row in rows)

    assert LiquidacionInspector.objects.count() == inspectors_after_first
    assert LiquidacionContacto.objects.count() == contactos_after_first
    assert Contacto.objects.count() == entidades_after_first


# ── Drift and safety ───────────────────────────────────────────────────────────


def test_state_drift_is_reported_as_review_and_does_not_mutate(
    manifest_state, tmp_path
):
    item = next(item for item in INSPECTOR_COLLISIONS if item.numero == 23)
    link = LiquidacionInspector.objects.get(id=item.link_id)
    link.periodo = 2026
    link.save()  # simulates a manual edit after the contaminating import

    run_command(tmp_path / "drift.csv", apply=True)

    rows = {row["link_contaminado_id"]: row for row in read_csv(tmp_path / "drift.csv")}
    drifted = rows[item.link_id]
    assert drifted["status"] == "REVIEW_STATE_DRIFT"
    assert drifted["accion"] == "NONE"
    assert LiquidacionInspector.objects.filter(id=item.link_id).exists()


def test_resave_inside_the_contaminating_window_is_not_drift(manifest_state, tmp_path):
    """A re-save during the contaminating run is not a manual edit.

    The importer created the IO 56 contact link and saved it again a
    millisecond later (same payload). That must not block the cleanup.
    """
    item = next(item for item in CONTACTO_COLLISIONS if item.numero == 56)
    touched = item.created_at + timedelta(milliseconds=1)
    LiquidacionContacto.objects.filter(id=item.link_id).update(updated_at=touched)

    run_command(tmp_path / "resave.csv", apply=True)

    rows = {
        row["link_contaminado_id"]: row for row in read_csv(tmp_path / "resave.csv")
    }
    resaved = rows[item.link_id]
    assert resaved["status"] == "DELETE_LINK_AND_CONTACTO_ENTITY"
    assert not LiquidacionContacto.objects.filter(id=item.link_id).exists()
    assert not Contacto.objects.filter(id=item.contacto_id).exists()


def test_identity_drift_is_reported_as_review(manifest_state, tmp_path):
    item = next(item for item in INSPECTOR_COLLISIONS if item.numero == 23)
    other = next(
        candidate
        for candidate in INSPECTOR_COLLISIONS
        if candidate.inspector_operacion_id != item.inspector_operacion_id
    )
    LiquidacionInspector.objects.filter(id=item.link_id).update(
        inspector_operacion_id=other.inspector_operacion_id
    )

    run_command(tmp_path / "identity.csv", apply=True)

    rows = {
        row["link_contaminado_id"]: row for row in read_csv(tmp_path / "identity.csv")
    }
    drifted = rows[item.link_id]
    assert drifted["status"] == "REVIEW_STATE_DRIFT"
    assert LiquidacionInspector.objects.filter(id=item.link_id).exists()


def test_referenced_contact_is_never_deleted(manifest_state, tmp_path):
    item = next(item for item in CONTACTO_COLLISIONS if item.numero == 23)
    # The duplicated entity gains a second live reference.
    LiquidacionGeneral.objects.filter(id=item.liquidacion_id).update(
        contacto_id=item.contacto_id
    )

    run_command(tmp_path / "referenced.csv", apply=True)

    rows = {
        row["link_contaminado_id"]: row for row in read_csv(tmp_path / "referenced.csv")
    }
    referenced = rows[item.link_id]
    assert referenced["status"] == "REVIEW_REFERENCED_CONTACTO"
    assert referenced["accion"] == "NONE"
    assert LiquidacionContacto.objects.filter(id=item.link_id).exists()
    assert Contacto.objects.filter(id=item.contacto_id).exists()


def test_missing_legacy_counterpart_is_reported_as_review(manifest_state, tmp_path):
    item = next(item for item in INSPECTOR_COLLISIONS if item.numero == 23)
    LiquidacionInspector.objects.filter(id=item.legacy_link_id).delete()

    run_command(tmp_path / "legacy-missing.csv", apply=True)

    rows = {
        row["link_contaminado_id"]: row
        for row in read_csv(tmp_path / "legacy-missing.csv")
    }
    missing = rows[item.link_id]
    assert missing["status"] == "REVIEW_LEGACY_COUNTERPART_MISSING"
    assert LiquidacionInspector.objects.filter(id=item.link_id).exists()


def test_legacy_parent_is_never_touched(manifest_state, tmp_path):
    item = next(item for item in CONTACTO_COLLISIONS if item.numero == 23)
    # Move the contaminated link to the legacy liquidacion: it must be preserved.
    LiquidacionContacto.objects.filter(id=item.link_id).update(
        liquidacion_id=item.legacy_liquidacion_id
    )

    run_command(tmp_path / "legacy-parent.csv", apply=True)

    rows = {
        row["link_contaminado_id"]: row
        for row in read_csv(tmp_path / "legacy-parent.csv")
    }
    moved = rows[item.link_id]
    assert moved["status"] == "REVIEW_PARENT_MISMATCH"
    assert LiquidacionContacto.objects.filter(id=item.link_id).exists()
    assert Contacto.objects.filter(id=item.contacto_id).exists()


# ── Comprobantes are out of scope ─────────────────────────────────────────────


def test_command_never_imports_or_queries_liquidacion_comprobante(
    manifest_state, tmp_path
):
    from modules.liquidaciones.management.commands import (
        correct_nonlegacy_io_inspector_collisions as command_module,
    )

    source = open(command_module.__file__, encoding="utf-8").read()
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert not any("Comprobante" in name for name in imported)
    assert not hasattr(command_module, "LiquidacionComprobante")

    with CaptureQueriesContext(connection) as captured:
        run_command(tmp_path / "no-comprobante.csv", apply=True)

    assert captured.captured_queries
    for query in captured.captured_queries:
        assert "comprobante" not in query["sql"].lower()
