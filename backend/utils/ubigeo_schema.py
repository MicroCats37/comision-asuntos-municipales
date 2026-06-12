"""
Schema and helpers for Peru's ubigeo data, backed by ubigeo_constants.py.

Provides validated, cached access to:
    DEPARTAMENTO > PROVINCIA > DISTRITO > {ubigeo, id, inei?}

Usage:
    from utils.ubigeo_schema import (
        get_district_choices,        # -> [(label, value), ...]
        is_valid_district_choice,    # -> bool (full hierarchy string)
        get_valid_district_names,    # -> frozenset[str] (flat names, for Empresa)
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
# Flat district name lookups (kept for Empresa.distrito compatibility)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_valid_district_names() -> frozenset[str]:
    """
    Return a frozen set of all valid district names (uppercase).
    Used for flat name validation (e.g. Empresa.distrito).
    """
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
    """
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
    """
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
    """
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
    """
    seen: set[str] = set()
    choices: list[tuple[str, str]] = []
    for provs in UBIGEO.values():
        for dists in provs.values():
            for dist_name in sorted(dists.keys()):
                if dist_name not in seen:
                    seen.add(dist_name)
                    choices.append((dist_name, dist_name))
    return tuple(choices)