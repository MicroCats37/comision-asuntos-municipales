"""
Shared constraint primitives for validity-period ("vigencia") models.

This module is the single source of truth for:

- the **scope keys** that partition a validity table (``tipo_liquidacion`` or a
  global scope). Rows sharing a scope may not overlap in time; rows in
  different scopes are independent.
- the **inclusive date-range expression** used by the PostgreSQL exclusion
  constraints.
- the **exclusion constraint** itself ("no two overlapping validity periods").

Nothing here knows about a concrete business model: the scope is declared once
per model (``VigenciaModel.vigencia_scope_fields``) and consumed both by the
runtime validation (:mod:`core_application.vigencia.services`) and by the
database constraint, so the two can never disagree.
"""

from django.contrib.postgres.constraints import (
    ExclusionConstraint as DjangoExclusionConstraint,
)
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import DEFAULT_DB_ALIAS, models
from django.db.models import Func

# ── Scope keys ────────────────────────────────────────────────────────────────────
# A scope key is the tuple of fields that partitions a validity table.
# An empty tuple means the whole table is a single (global) scope.

SCOPE_GLOBAL: tuple[str, ...] = ()
SCOPE_TIPO_LIQUIDACION: tuple[str, ...] = ("tipo_liquidacion",)
SCOPE_TIPO_LIQUIDACION_ESPECIALIDAD: tuple[str, ...] = (
    "tipo_liquidacion",
    "especialidad",
)

# ── Overlap messages ─────────────────────────────────────────────────────────────
# Single source of truth so the Python validation and the database constraint
# report exactly the same thing to the user.

MENSAJE_SOLAPAMIENTO_GLOBAL = (
    "El período de vigencia se superpone con otro período vigente."
)
MENSAJE_SOLAPAMIENTO_TIPO_LIQUIDACION = (
    "El período de vigencia se superpone con otro período vigente del mismo "
    "tipo de liquidación."
)
MENSAJE_SOLAPAMIENTO_TIPO_LIQUIDACION_ESPECIALIDAD = (
    "El período de vigencia se superpone con otro período vigente de la misma "
    "especialidad y tipo de liquidación."
)
MENSAJE_SOLAPAMIENTO_OPERACION = (
    "El período de vigencia se superpone con otro período de esta operación."
)


def mensaje_de_solapamiento(scope_fields) -> str:
    """Return the overlap message that matches the given scope."""
    campos = tuple(scope_fields or ())
    if not campos:
        return MENSAJE_SOLAPAMIENTO_GLOBAL
    if campos == SCOPE_TIPO_LIQUIDACION:
        return MENSAJE_SOLAPAMIENTO_TIPO_LIQUIDACION
    if campos == SCOPE_TIPO_LIQUIDACION_ESPECIALIDAD:
        return MENSAJE_SOLAPAMIENTO_TIPO_LIQUIDACION_ESPECIALIDAD
    return MENSAJE_SOLAPAMIENTO_OPERACION


class InclusiveDateRange(Func):
    """
    ``DATERANGE(lower, upper, '[]')`` — inclusive on both bounds.

    The range boundary is part of this class' contract and is therefore NOT
    captured by Django's migration serializer (a custom ``Func`` only
    serializes its expression arguments). Changing the boundary below requires
    recreating every exclusion constraint that uses this expression.
    """

    function = "DATERANGE"
    output_field = DateRangeField()
    template = "DATERANGE(%(expressions)s, '[]')"


class ExclusionConstraint(DjangoExclusionConstraint):
    """
    PostgreSQL exclusion constraint that is inert on backends without range support.

    SQLite — used by the default test settings — has neither ``EXCLUDE USING gist``
    nor the ``daterange()``/``&&`` operators, so the constraint can neither be
    created nor evaluated with SQL there. On PostgreSQL the behaviour is
    identical to Django's own ``django.contrib.postgres.constraints.ExclusionConstraint``.

    The overlap invariant is *also* enforced in Python by
    :func:`core_application.vigencia.services.validar_periodo_sin_solapamiento`,
    which is what protects non-PostgreSQL backends and non-form writers.
    """

    @staticmethod
    def _soportado(connection) -> bool:
        """True when the connection can express PostgreSQL range exclusion."""
        return connection.vendor == "postgresql"

    def constraint_sql(self, model, schema_editor):
        if not self._soportado(schema_editor.connection):
            return ""
        return super().constraint_sql(model, schema_editor)

    def create_sql(self, model, schema_editor):
        if not self._soportado(schema_editor.connection):
            return ""
        return super().create_sql(model, schema_editor)

    def remove_sql(self, model, schema_editor):
        if not self._soportado(schema_editor.connection):
            return ""
        return super().remove_sql(model, schema_editor)

    def validate(self, model, instance, exclude=None, using=DEFAULT_DB_ALIAS):
        """
        Validate the no-overlap invariant for ``instance``.

        The portable Python check is used on every backend (instead of Django's
        PostgreSQL-only emulation) so the violation always surfaces as a
        field-level ``ValidationError`` — in the admin form as well as in
        ``Model.full_clean()`` — and never as a 500.
        """
        if exclude and {"periodo_inicio", "periodo_fin"} & set(exclude):
            return None

        from core_application.vigencia.services import validar_periodo_sin_solapamiento

        validar_periodo_sin_solapamiento(instance)
        return None


def exclusion_constraint_vigencia(scope_fields, *, name) -> ExclusionConstraint:
    """
    Build the "no overlapping validity periods" exclusion constraint.

    ``scope_fields`` partitions the table: rows with the same scope values may
    not overlap. An empty scope produces a single global exclusion over the
    whole table.
    """
    campos = tuple(scope_fields or ())
    expressions = [
        (models.F(campo), RangeOperators.EQUAL) for campo in campos
    ]
    expressions.append(
        (InclusiveDateRange("periodo_inicio", "periodo_fin"), RangeOperators.OVERLAPS)
    )
    return ExclusionConstraint(
        name=name,
        expressions=expressions,
        violation_error_message=mensaje_de_solapamiento(campos),
    )


def vigencia_rango_valido_constraint(suffix: str):
    """
    Check constraint: a validity period may not end before it starts.

    ``suffix`` identifies the model — Django requires constraint names to be
    unique across the whole project (``models.E032``).

    The comparison is inclusive (``periodo_inicio <= periodo_fin``) because the
    validity ranges are inclusive on both bounds — a single-day period is legal
    and is exactly what the rollover produces when the previous period is closed
    one day before the new one starts.
    """
    return models.CheckConstraint(
        condition=models.Q(periodo_fin__isnull=True)
        | models.Q(periodo_inicio__lte=models.F("periodo_fin")),
        name=f"vigencia_rango_valido_{suffix}",
    )
