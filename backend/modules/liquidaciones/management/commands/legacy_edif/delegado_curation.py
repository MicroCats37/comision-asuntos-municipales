"""
EDIF legacy helpers — LiquidacionDelegado field curation from EDIF_ALL.csv.

This module curates null/missing fields on LiquidacionDelegado records by
backfilling them from the corresponding DELEGADO1..4 slot columns in EDIF_ALL.csv.

Curation rules per field:
    - DB is null/empty and CSV has a valid parsed value -> action=FILLED (update if --fix passed)
    - DB has a value and CSV has a different value -> action=CONFLICT (do NOT overwrite)
    - DB has a value and CSV matches, or both are null -> action=SKIP

Matching key: LiquidacionDelegado (liquidacion, delegado, especialidad_revision)
"""

from datetime import date

from modules.liquidaciones.domain.models.delegado import LiquidacionDelegado

from .delegado_columns import (
    DELEGADO_SLOT_COLUMNS,
    SLOT_SPECIALTY_DB_MAP,
    VALID_DICTAMEN_VALUES,
)
from .parsers import coerce_int, coerce_month, _parse_date


def extract_slot_fields(raw: list[str], slot_num: int) -> dict[str, any]:
    """
    Extract all curatable DELEGADO slot fields from a split CSV row.

    Args:
        raw: Split CSV row (list[str]) from EDIF_ALL.csv
        slot_num: Slot number (1..4)

    Returns:
        dict with keys: slot_num, periodo, mes, fecha_presentacion, fecha_revision,
        numero_rh, dictamen_revision, especialidad_nombre
    """
    try:
        

        if slot_num == 1:
            col_fecha_pres, col_fecha_rev, col_nro_orden, col_dictamen, col_periodo, col_mes = 36, 37, 38, 55, 62, 66
        elif slot_num == 2:
            col_fecha_pres, col_fecha_rev, col_nro_orden, col_dictamen, col_periodo, col_mes = 39, 40, 41, 56, 63, 67
        elif slot_num == 3:
            col_fecha_pres, col_fecha_rev, col_nro_orden, col_dictamen, col_periodo, col_mes = 42, 43, 44, 57, 64, 68
        elif slot_num == 4:
            col_fecha_pres, col_fecha_rev, col_nro_orden, col_dictamen, col_periodo, col_mes = 45, 46, 47, 58, 65, 69


    except KeyError:
        return {}

    def _col(idx: int):
        return raw[idx] if len(raw) > idx else None

    especialidad_nombre = SLOT_SPECIALTY_DB_MAP.get(slot_num, "")

    return {
        "slot_num": slot_num,
        "periodo": coerce_int(_col(col_periodo)),
        "mes": coerce_month(_col(col_mes)),
        "fecha_presentacion": _parse_date(_col(col_fecha_pres)),
        "fecha_revision": _parse_date(_col(col_fecha_rev)),
        "numero_rh": _coerce_nro_rh(_col(col_nro_orden)),
        "dictamen_revision": _coerce_dictamen(_col(col_dictamen)),
        "especialidad_nombre": especialidad_nombre,
    }


def _coerce_nro_rh(raw) -> str | None:
    """
    Coerce NROORDEN to string suitable for LiquidacionDelegado.numero_rh.

    Stores as string since the field is CharField(max_length=50).
    Returns None if absent, null, or invalid.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.upper() == "NULL":
        return None
    try:
        val = int(float(text))
        return str(val)
    except (ValueError, TypeError):
        return None


def _coerce_dictamen(raw) -> str | None:
    """
    Coerce DICTAMEN value to a valid DictamenRevision choice.

    If the raw value maps directly to a valid choice, return it.
    If not a perfect match, return None (do not guess or store invalid values).
    """
    if raw is None:
        return None
    text = str(raw).strip().upper()
    if not text or text == "NULL":
        return None
    if text in VALID_DICTAMEN_VALUES:
        return text
    return None


# Fields on LiquidacionDelegado that can be curated from CSV slots.
# Tuple: (db_field_name, slot_fields_key, parser_callable)
DELEGADO_CURATION_FIELDS = [
    ("periodo", "periodo", coerce_int),
    ("mes", "mes", coerce_month),
    ("fecha_presentacion", "fecha_presentacion", _parse_date),
    ("fecha_revision", "fecha_revision", _parse_date),
    ("numero_rh", "numero_rh", coerce_int),
    ("dictamen_revision", "dictamen_revision", _coerce_dictamen),
]


def curate_record(
    detail: LiquidacionDelegado,
    slot_fields: dict[str, any],
    edificacion_numero: int,
    dry_run: bool = True,
) -> list[dict]:
    """
    Determine curation actions for a single LiquidacionDelegado record.

    Args:
        detail: LiquidacionDelegado model instance
        slot_fields: dict from extract_slot_fields()
        edificacion_numero: The LiquidacionEdificacion.numero (for the report)
        dry_run: If True, do not save changes

    Returns:
        List of curation result dicts, one per field that had an action:
        {
            "numero": edificacion_numero,
            "slot": slot_num,
            "delegado": delegado_nombre,
            "field": field_name,
            "db_value": str(db_val) or "",
            "source_value": str(source_val) or "",
            "action": "FILLED" | "CONFLICT" | "SKIP",
        }
    """
    results = []
    especialidad_nombre = slot_fields.get("especialidad_nombre", "")

    # Get the current DB values
    db_values = {
        "periodo": detail.periodo,
        "mes": detail.mes,
        "fecha_presentacion": detail.fecha_presentacion,
        "fecha_revision": detail.fecha_revision,
        "numero_rh": detail.numero_rh,
        "dictamen_revision": detail.dictamen_revision,
    }

    for field_name, slot_key, parser in DELEGADO_CURATION_FIELDS:
        source_val = slot_fields.get(slot_key, None)
        db_val = db_values[field_name]

        # Normalize source value for comparison
        source_str = _format_source_val(source_val, field_name)
        db_str = _format_db_val(db_val)

        action = _determine_action(db_val, source_val)
        results.append({
            "numero": edificacion_numero,
            "slot": slot_fields.get("slot_num", ""),
            "delegado": getattr(getattr(detail.delegado, "perfil_ingeniero", None), "nombre_completo", "") or str(detail.delegado),
            "field": field_name,
            "db_value": db_str,
            "source_value": source_str,
            "action": action,
        })

        # Apply fix if --fix passed and action is FILLED
        if not dry_run and action == "FILLED":
            setattr(detail, field_name, source_val)

    if not dry_run:
        # Only save if at least one field was filled
        filled_count = sum(1 for r in results if r["action"] == "FILLED")
        if filled_count > 0:
            detail.save()

    return results


def _determine_action(db_val, source_val) -> str:
    """
    Determine the curation action for a single field.

    Returns:
        FILLED  - DB is null/empty and source is valid
        CONFLICT - DB has value but source is different
        SKIP    - DB has value matching source, or both null/empty
    """
    # Check if DB is null/empty
    db_is_null = _is_null(db_val)
    source_is_null = _is_null(source_val)

    if db_is_null and source_is_null:
        return "SKIP"
    if db_is_null and not source_is_null:
        return "FILLED"
    if not db_is_null and source_is_null:
        return "SKIP"
    # Both have values — check if they match
    if _values_equal(db_val, source_val):
        return "SKIP"
    return "CONFLICT"


def _is_null(val) -> bool:
    """Check if a value is null/empty/sentinel for curation purposes."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip().upper() in ("", "NULL", "NONE"):
        return True
    if isinstance(val, date) and val.year < 1901:
        # Legacy sentinel: dates in 1900 (e.g. 1900-01-01) mean "no date"
        return True
    return False


def _values_equal(db_val, source_val) -> bool:
    """Check if DB value equals source value with type-aware comparison."""
    if isinstance(db_val, date) and isinstance(source_val, date):
        return db_val == source_val
    if isinstance(db_val, (int,)) and isinstance(source_val, int):
        return db_val == source_val
    # String comparison for numero_rh and dictamen
    return str(db_val).strip() == str(source_val).strip()


def _format_source_val(val, field_name: str) -> str:
    """Format a source value for the CSV report."""
    if val is None:
        return ""
    if isinstance(val, date):
        return val.isoformat()
    return str(val)


def _format_db_val(val) -> str:
    """Format a DB value for the CSV report."""
    if val is None:
        return ""
    if isinstance(val, date):
        return val.isoformat()
    return str(val)


def curation_report_header() -> list[str]:
    """Return the CSV header row for the curation report."""
    return ["numero", "slot", "delegado", "field", "db_value", "source_value", "action"]
