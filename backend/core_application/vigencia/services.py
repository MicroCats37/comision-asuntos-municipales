"""
Domain services for validity periods ("vigencia").

These services are the server-side, reusable implementation of the validity
rules shared by ``liquidaciones`` and ``finanzas``:

- :func:`validar_periodo_sin_solapamiento` — rejects an overlapping validity
  range for the scope of the instance.
- :func:`cerrar_vigencias_previas` — closes the open validity period(s) of a
  scope at ``periodo_inicio - 1 day``.
- :func:`cerrar_actual_y_abrir_nuevo` — the atomic "close the open period and
  create its successor" operation.

They live in ``core_application`` (not in a business module) so that no module
has to import from another module: the dependency direction stays inverted.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Q

from core_application.vigencia.constraints import (
    SCOPE_TIPO_LIQUIDACION,
    mensaje_de_solapamiento,
)

MENSAJE_PERIODO_SIN_FIN = (
    "No se puede abrir una nueva vigencia porque ya existe una vigencia abierta "
    "que comienza en esa fecha o después."
)


def scope_de(instancia) -> dict:
    """
    Return the scope of ``instancia`` as a filter dict.

    The scope is declared once per model through
    ``VigenciaModel.vigencia_scope_fields``; an empty scope means the model is
    global (the whole table is one scope).
    """
    campos = tuple(getattr(instancia, "vigencia_scope_fields", ()) or ())
    return {campo: getattr(instancia, f"{campo}_id", None) for campo in campos}


def _scope_de_valores(modelo, valores: dict) -> dict:
    """Build the scope filter dict from raw field values."""
    campos = tuple(getattr(modelo, "vigencia_scope_fields", ()) or ())
    scope = {}
    for campo in campos:
        if f"{campo}_id" in valores:
            scope[f"{campo}_id"] = valores[f"{campo}_id"]
        elif campo in valores:
            valor = valores[campo]
            scope[f"{campo}_id"] = getattr(valor, "pk", valor)
    return scope


def hay_solapamiento(
    modelo,
    *,
    periodo_inicio,
    periodo_fin,
    scope: dict,
    excluir_pk=None,
) -> bool:
    """
    True when the inclusive range ``[periodo_inicio, periodo_fin]`` overlaps a
    sibling period of the same scope.

    A ``periodo_fin`` of ``None`` means "open ended" and is treated as
    infinite, exactly like the PostgreSQL range expression.
    """
    if periodo_inicio is None:
        return False

    hermanos = modelo.objects.all()
    if scope:
        hermanos = hermanos.filter(**scope)
    if excluir_pk is not None:
        hermanos = hermanos.exclude(pk=excluir_pk)

    if periodo_fin is not None:
        hermanos = hermanos.filter(periodo_inicio__lte=periodo_fin)

    return hermanos.filter(
        Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=periodo_inicio)
    ).exists()


def validar_periodo_sin_solapamiento(instancia) -> None:
    """
    Raise ``ValidationError`` when the validity range of ``instancia`` overlaps
    a sibling period of the same scope.
    """
    campos = tuple(getattr(instancia, "vigencia_scope_fields", ()) or ())
    if hay_solapamiento(
        instancia.__class__,
        periodo_inicio=instancia.periodo_inicio,
        periodo_fin=instancia.periodo_fin,
        scope=scope_de(instancia),
        excluir_pk=instancia.pk,
    ):
        raise ValidationError({"periodo_inicio": mensaje_de_solapamiento(campos)})


def cerrar_vigencias_previas(modelo, *, scope: dict, periodo_inicio) -> list:
    """
    Close every open validity period of ``scope`` at ``periodo_inicio - 1 day``.

    Returns the closed instances. The operation runs inside a transaction and
    locks the affected rows when the backend supports ``SELECT ... FOR UPDATE``.
    """
    if periodo_inicio is None:
        raise ValidationError(
            {"periodo_inicio": "La fecha de inicio de la vigencia es obligatoria."}
        )

    cerrados = []
    with transaction.atomic():
        abiertos = modelo.objects.filter(periodo_fin__isnull=True, **scope)
        if connection.features.has_select_for_update:
            abiertos = abiertos.select_for_update()

        for abierto in abiertos:
            if abierto.periodo_inicio >= periodo_inicio:
                raise ValidationError({"periodo_inicio": MENSAJE_PERIODO_SIN_FIN})
            abierto.periodo_fin = periodo_inicio - timedelta(days=1)
            abierto.save(update_fields=["periodo_fin", "updated_at"])
            cerrados.append(abierto)

    return cerrados


def cerrar_actual_y_abrir_nuevo(
    modelo,
    *,
    periodo_inicio,
    valores: dict,
    scope: dict | None = None,
):
    """
    Atomically close the open validity period of the scope and create its successor.

    The previous period is closed at ``periodo_inicio - 1 day`` and the new one
    starts at ``periodo_inicio``; if the creation fails, the close is rolled
    back so the scope is never left half-closed.

    Returns the newly created instance.
    """
    with transaction.atomic():
        scope_efectivo = scope if scope is not None else _scope_de_valores(modelo, valores)
        cerrar_vigencias_previas(
            modelo, scope=scope_efectivo, periodo_inicio=periodo_inicio
        )

        instancia = modelo(periodo_inicio=periodo_inicio, periodo_fin=None, **valores)
        instancia.full_clean()
        instancia.save()

    return instancia


def scope_es_tipo_liquidacion(instancia) -> bool:
    """True when the instance is scoped by ``tipo_liquidacion``."""
    return tuple(getattr(instancia, "vigencia_scope_fields", ()) or ()) == (
        SCOPE_TIPO_LIQUIDACION
    )
