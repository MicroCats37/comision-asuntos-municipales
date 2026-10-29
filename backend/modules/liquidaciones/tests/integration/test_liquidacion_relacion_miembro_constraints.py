"""
Migration-state tests for the LiquidacionRelacionMiembro constraints.

Covers:
- `unique_grupo_relacion_key_revision` was removed from the model Meta — the revision
  number is an editable classification, not a unique sequence identity, so several
  active liquidaciones may share the same (grupo, relacion_key, numero_revision).
- `unique_liquidacion_unico_grupo` (one group per liquidacion) is retained.
- Exactly one migration removes the constraint and no later migration re-adds it.

Model-level introspection only — the migration is NOT applied by these tests.
"""
import pathlib

import pytest
from django.apps import apps
from django.db import models

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_miembro import (
    LiquidacionRelacionMiembro,
)

CONSTRAINT_REMOVED = "unique_grupo_relacion_key_revision"
CONSTRAINT_RETAINED = "unique_liquidacion_unico_grupo"


def migrations_dir() -> pathlib.Path:
    """Return the migrations directory of the liquidaciones app."""
    return pathlib.Path(apps.get_app_config("liquidaciones").path) / "migrations"


def constraint_names() -> set:
    return {constraint.name for constraint in LiquidacionRelacionMiembro._meta.constraints}


# ── Model state ───────────────────────────────────────────────────────────────

def test_removed_constraint_is_absent_from_model_meta():
    """
    GIVEN: the LiquidacionRelacionMiembro model
    WHEN: its Meta constraints are inspected
    THEN: unique_grupo_relacion_key_revision is no longer declared
    """
    assert CONSTRAINT_REMOVED not in constraint_names()


def test_one_group_per_liquidacion_constraint_is_retained():
    """
    GIVEN: the LiquidacionRelacionMiembro model
    WHEN: its Meta constraints are inspected
    THEN: unique_liquidacion_unico_grupo is still declared over the liquidacion field
    """
    names = constraint_names()

    assert CONSTRAINT_RETAINED in names

    constraint = next(
        c for c in LiquidacionRelacionMiembro._meta.constraints if c.name == CONSTRAINT_RETAINED
    )
    assert isinstance(constraint, models.UniqueConstraint)
    assert list(constraint.fields) == ["liquidacion"]


def test_lookup_index_over_slot_is_retained():
    """
    GIVEN: the LiquidacionRelacionMiembro model
    WHEN: its Meta indexes are inspected
    THEN: the (grupo, relacion_key, numero_revision) lookup index is still declared
    """
    index_fields = [tuple(index.fields) for index in LiquidacionRelacionMiembro._meta.indexes]

    assert ("grupo", "relacion_key", "numero_revision") in index_fields


# ── Migration state ───────────────────────────────────────────────────────────

def test_exactly_one_migration_removes_the_constraint():
    """
    GIVEN: the liquidaciones migrations directory
    WHEN: migrations declaring a RemoveConstraint for the removed constraint are looked up
    THEN: exactly one exists — the generated 0007 migration
    """
    matches = [
        path
        for path in sorted(migrations_dir().glob("*.py"))
        if "RemoveConstraint" in path.read_text(encoding="utf-8")
        and f'name="{CONSTRAINT_REMOVED}"' in path.read_text(encoding="utf-8")
    ]

    assert len(matches) == 1
    assert matches[0].name.startswith("0007_")


def test_removal_migration_depends_on_the_previous_migration():
    """
    GIVEN: the generated removal migration
    WHEN: its dependencies are inspected
    THEN: it depends on migration 0006 (the previous state of the app)
    """
    matches = [
        path
        for path in sorted(migrations_dir().glob("*.py"))
        if "RemoveConstraint" in path.read_text(encoding="utf-8")
        and f'name="{CONSTRAINT_REMOVED}"' in path.read_text(encoding="utf-8")
    ]

    source = matches[0].read_text(encoding="utf-8")

    assert "0006_remove_historicalliquidaciongeneral_tipo_comprobante_previsto_and_more" in source


def test_no_later_migration_reintroduces_the_constraint():
    """
    GIVEN: the liquidaciones migrations directory
    WHEN: every migration after the removal one is inspected
    THEN: none re-adds the removed constraint
    """
    removal = [
        path
        for path in sorted(migrations_dir().glob("*.py"))
        if "RemoveConstraint" in path.read_text(encoding="utf-8")
        and f'name="{CONSTRAINT_REMOVED}"' in path.read_text(encoding="utf-8")
    ][0]

    for path in sorted(migrations_dir().glob("*.py")):
        if path.name <= removal.name:
            continue
        source = path.read_text(encoding="utf-8")
        if "AddConstraint" in source:
            assert CONSTRAINT_REMOVED not in source


@pytest.mark.parametrize("nombre", [CONSTRAINT_REMOVED])
def test_constraint_name_is_not_referenced_by_the_model(nombre):
    """
    GIVEN: the LiquidacionRelacionMiembro model
    WHEN: the constraint names are compared with the removed one
    THEN: the removed name is gone from the model state
    """
    assert nombre not in constraint_names()
