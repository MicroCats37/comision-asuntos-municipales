"""
Schema and helpers for Peru's ubigeo data, backed by database models.

Provides validated, cached access to:
    DEPARTAMENTO > PROVINCIA > DISTRITO > {ubigeo, id, inei?}

When database models are populated (via load_ubigeo command), functions query DB.
When DB is empty, falls back to the UBIGEO constant for backward compatibility.

Usage:
    from utils.ubigeo_schema import (
        get_district_choices,        # -> [(label, value), ...]
        is_valid_district_choice,    # -> bool (full hierarchy string)
        get_valid_district_names,    # -> frozenset[str] (flat names, for Entidad)
        is_valid_district,           # -> bool (flat name check)
    )

Choices format:
    value  = "DEPARTAMENTO - PROVINCIA - DISTRITO"  (e.g. "LIMA - LIMA - MIRAFLORES")
    label  = same as value (Django Display uses value)
    Example: ("LIMA - LIMA - MIRAFLORES", "LIMA - LIMA - MIRAFLORES")

The UBIGEO constant is validated on import; if structure is corrupted a clear
ValueError is raised rather than failing silently.
"""

from __future__ import annotations

from functools import lru_cache

import django
from django.apps import apps
from django.db import connection

import pydantic

from utils.ubigeo_constants import UBIGEO


class DistrictData(pydantic.BaseModel):
    """Single district record from ubigeo constants."""

    ubigeo: str
    id: int
    inei: str | None = None

    model_config = pydantic.ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Validation (runs at module load time)
# ---------------------------------------------------------------------------

def _validate_structure() -> None:
    """
    Walk UBIGEO and validate the expected nested dict structure.
    Raises ValueError with a clear message if any level is malformed.
    Called at module import; raises early if the constant is corrupted.
    """
    if not isinstance(UBIGEO, dict):
        raise ValueError(
            f"UBIGEO must be a dict (DEPARTAMENTO -> PROVINCIA -> DISTRITO), "
            f"got {type(UBIGEO).__name__}."
        )
    for dept_name, dept_value in UBIGEO.items():
        if not isinstance(dept_value, dict):
            raise ValueError(
                f"Department '{dept_name}' must be a dict of provinces, "
                f"got {type(dept_value).__name__}."
            )
        for prov_name, prov_value in dept_value.items():
            if not isinstance(prov_value, dict):
                raise ValueError(
                    f"Province '{prov_name}' in department '{dept_name}' "
                    f"must be a dict of districts, "
                    f"got {type(prov_value).__name__}."
                )
            for dist_name, dist_value in prov_value.items():
                if not isinstance(dist_value, dict):
                    raise ValueError(
                        f"District '{dist_name}' in province '{prov_name}', "
                        f"department '{dept_name}' must be a dict "
                        f"(with 'ubigeo', 'id', optional 'inei'), "
                        f"got {type(dist_value).__name__}."
                    )
                try:
                    DistrictData.model_validate(dist_value)
                except pydantic.ValidationError as exc:
                    raise ValueError(
                        f"District '{dist_name}' in province '{prov_name}', "
                        f"department '{dept_name}' has invalid data: {exc}"
                    ) from exc


_validate_structure()


# ---------------------------------------------------------------------------
# Database availability check
# ---------------------------------------------------------------------------

def _db_has_ubigeo_data() -> bool:
    """Check if Ubigeo tables have data."""
    try:
        # Use raw SQL to avoid app registry issues during import
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM entidades_ubigeodistrito LIMIT 1"
            )
            return cursor.fetchone() is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Flat district name lookups (kept for Empresa.distrito compatibility)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_valid_district_names() -> frozenset[str]:
    """
    Return a frozen set of all valid district names (uppercase).
    Used for flat name validation (e.g. Entidad.distrito).

    First checks DB, falls back to UBIGEO constant if DB is empty.
    """
    if _db_has_ubigeo_data():
        try:
            from modules.entidades.domain.models import UbigeoDistrito
            names = set(
                UbigeoDistrito.objects.values_list("nombre", flat=True)
            )
            return frozenset(name.upper() for name in names)
        except Exception:
            pass

    # Fallback to constants
    names: set[str] = set()
    for dept in UBIGEO.values():
        for prov in dept.values():
            for dist_name in prov.keys():
                names.add(dist_name.upper())
    return frozenset(names)


def is_valid_district(name: str) -> bool:
    """Return True if `name` (case-insensitive) is a valid district."""
    return name.upper() in get_valid_district_names()


# ---------------------------------------------------------------------------
# Hierarchical choice helpers (for Delegado.distrito)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_district_choices() -> tuple[tuple[str, str], ...]:
    """
    Return all district choices as a tuple of (value, label) tuples.

    Format: "DEPARTAMENTO - PROVINCIA - DISTRITO" for both value and label.
    Example: ("LIMA - LIMA - MIRAFLORES", "LIMA - LIMA - MIRAFLORES")

    Used as `choices=` on model CharField for Django admin/form dropdowns.
    Cached after first call.

    First checks DB, falls back to UBIGEO constant if DB is empty.
    """
    if _db_has_ubigeo_data():
        try:
            from modules.entidades.domain.models import UbigeoDistrito
            choices = [
                (d.hierarchical_label, d.hierarchical_label)
                for d in UbigeoDistrito.objects.select_related(
                    "provincia__departamento"
                ).order_by(
                    "provincia__departamento__nombre",
                    "provincia__nombre",
                    "nombre",
                )
            ]
            return tuple(choices)
        except Exception:
            pass

    # Fallback to constants
    choices: list[tuple[str, str]] = []
    for dept_name, provs in sorted(UBIGEO.items()):
        for prov_name, dists in sorted(provs.items()):
            for dist_name in sorted(dists.keys()):
                label = f"{dept_name} - {prov_name} - {dist_name}"
                choices.append((label, label))
    return tuple(choices)


def iter_district_choices():
    """
    Generator yielding district choices one at a time.
    Same format as get_district_choices() but lazy.

    First checks DB, falls back to UBIGEO constant if DB is empty.
    """
    if _db_has_ubigeo_data():
        try:
            from modules.entidades.domain.models import UbigeoDistrito
            for d in UbigeoDistrito.objects.select_related(
                "provincia__departamento"
            ).order_by(
                "provincia__departamento__nombre",
                "provincia__nombre",
                "nombre",
            ):
                label = d.hierarchical_label
                yield (label, label)
            return
        except Exception:
            pass

    # Fallback to constants
    for dept_name, provs in sorted(UBIGEO.items()):
        for prov_name, dists in sorted(provs.items()):
            for dist_name in sorted(dists.keys()):
                label = f"{dept_name} - {prov_name} - {dist_name}"
                yield (label, label)


def is_valid_district_choice(value: str) -> bool:
    """
    Return True if `value` exactly matches a generated district choice.

    Used to validate Delegado.distrito which stores the full hierarchical
    string (e.g. "LIMA - LIMA - MIRAFLORES") rather than just the district name.
    """
    choices = get_district_choices()
    return value in {c[0] for c in choices}


# ---------------------------------------------------------------------------
# Provincia and Distrito simple-name choice helpers (for Municipalidad)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_provincia_choices() -> tuple[tuple[str, str], ...]:
    """
    Return all unique provincia names as (value, label) tuples.

    Format: just the provincia name, e.g. ("LIMA", "LIMA")

    First checks DB, falls back to UBIGEO constant if DB is empty.
    """
    if _db_has_ubigeo_data():
        try:
            from modules.entidades.domain.models import UbigeoProvincia
            seen: set[str] = set()
            choices: list[tuple[str, str]] = []
            for prov in UbigeoProvincia.objects.select_related(
                "departamento"
            ).order_by("nombre"):
                if prov.nombre not in seen:
                    seen.add(prov.nombre)
                    choices.append((prov.nombre, prov.nombre))
            return tuple(choices)
        except Exception:
            pass

    # Fallback to constants
    seen: set[str] = set()
    choices: list[tuple[str, str]] = []
    for provs in UBIGEO.values():
        for prov_name in sorted(provs.keys()):
            if prov_name not in seen:
                seen.add(prov_name)
                choices.append((prov_name, prov_name))
    return tuple(choices)


@lru_cache(maxsize=1)
def get_distrito_flat_choices() -> tuple[tuple[str, str], ...]:
    """
    Return all unique distrito names as (value, label) tuples (flat names only).

    Format: just the distrito name, e.g. ("MIRAFLORES", "MIRAFLORES")

    First checks DB, falls back to UBIGEO constant if DB is empty.
    """
    if _db_has_ubigeo_data():
        try:
            from modules.entidades.domain.models import UbigeoDistrito
            seen: set[str] = set()
            choices: list[tuple[str, str]] = []
            for dist in UbigeoDistrito.objects.order_by("nombre"):
                if dist.nombre not in seen:
                    seen.add(dist.nombre)
                    choices.append((dist.nombre, dist.nombre))
            return tuple(choices)
        except Exception:
            pass

    # Fallback to constants
    seen: set[str] = set()
    choices: list[tuple[str, str]] = []
    for provs in UBIGEO.values():
        for dists in provs.values():
            for dist_name in sorted(dists.keys()):
                if dist_name not in seen:
                    seen.add(dist_name)
                    choices.append((dist_name, dist_name))
    return tuple(choices)


# ---------------------------------------------------------------------------
# Callable choices for Django model fields
# ---------------------------------------------------------------------------

def get_district_choices_callable():
    """
    Returns a callable that returns district choices.
    Use this for Django model field choices= parameter to avoid
    evaluation at module import time.

    Usage:
        class MyModel(models.Model):
            distrito = models.CharField(max_length=250, choices=get_district_choices_callable())
    """
    return get_district_choices


def get_provincia_choices_callable():
    """
    Returns a callable that returns provincia choices.
    Use this for Django model field choices= parameter to avoid
    evaluation at module import time.
    """
    return get_provincia_choices


def get_distrito_flat_choices_callable():
    """
    Returns a callable that returns distrito flat choices.
    Use this for Django model field choices= parameter to avoid
    evaluation at module import time.
    """
    return get_distrito_flat_choices