"""
Compatibility shim for the vigencia primitives.

The canonical implementation now lives in :mod:`core_application.vigencia`, so
that ``finanzas`` and ``liquidaciones`` share one implementation without either
module importing the other.

This module is kept because migration
``liquidaciones/0004_delegadooperacionperiodo_...`` (already applied in the
databases) serializes ``InclusiveDateRange`` from this path.
"""

from core_application.vigencia.constraints import InclusiveDateRange  # noqa: F401
from core_application.vigencia.services import (  # noqa: F401
    validar_periodo_sin_solapamiento as _validar_periodo_sin_solapamiento,
)


def validate_periodo_sin_solapamiento(instance, parent_field=None):
    """
    Deprecated — use :func:`core_application.vigencia.services.validar_periodo_sin_solapamiento`.

    ``parent_field`` is ignored: the scope is read from the model's
    ``vigencia_scope_fields`` declaration.
    """
    _validar_periodo_sin_solapamiento(instance)
