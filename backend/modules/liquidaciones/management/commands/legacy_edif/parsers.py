"""
EDIF legacy helpers — monetary parsing utilities and source CSV loading.
"""

import csv
import re
import unicodedata
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

CENT = Decimal("0.01")


def money(value) -> Decimal:
    """Parse a value as a money Decimal, returning Decimal('0.00') on failure."""
    if value is None:
        return Decimal("0.00")
    try:
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def round_money(value: Decimal) -> Decimal:
    """Quantize a Decimal to cents using ROUND_HALF_UP."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def money_diff(actual, expected) -> Decimal:
    """Absolute difference between two money values."""
    return abs(money(actual) - expected)


def load_source_csv(path: Path) -> dict[int, dict]:
    """
    Load an EDIF legacy CSV file (semicolon-delimited, BOM UTF-8).

    Returns:
        dict[int, dict]: mapping numero -> {"raw": list[str], "header": list[str]}
    """
    if not path.exists():
        raise FileNotFoundError(f"--source-csv not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file, delimiter=";")
        header = next(reader, None)
        if not header:
            raise ValueError(f"--source-csv has no header: {path}")
        rows = {}
        for raw in reader:
            if not raw:
                continue
            try:
                numero = int(float(str(raw[0]).strip()))
            except (ValueError, TypeError):
                continue
            rows[numero] = {"raw": raw, "header": header}
    return rows


def _parse_date(raw) -> date | None:
    """
    Parse a date value from EDIF CSV.

    Accepts datetime objects (returns .date()) or strings.
    Tries formats: "%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S".
    Returns None for absent, null, unparseable, or sentinel (1900-01-01 / "1/01/1900") values.
    """
    SENTINEL = date(1900, 1, 1)
    if raw is None:
        return None
    if isinstance(raw, datetime):
        d = raw.date()
        if d == SENTINEL:
            return None
        return d
    text = str(raw).strip()
    if not text or text.upper() == "NULL":
        return None
    if re.match(r"^1/\d{2}/1900", text):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            d = datetime.strptime(text, fmt).date()
            if d == SENTINEL:
                return None
            return d
        except ValueError:
            pass
    return None


def coerce_int(raw) -> int | None:
    """
    Coerce a raw cell value to int.

    Returns None if absent, null, or invalid.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.upper() == "NULL":
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


def coerce_month(raw) -> int | None:
    """
    Coerce MES cell value to int in range 1..12.

    Returns None if absent, null, or out of range.
    """
    val = coerce_int(raw)
    if val is None:
        return None
    if 1 <= val <= 12:
        return val
    return None


# ── Documento helpers ────────────────────────────────────────────────────────────


def resolve_tipo_documento(dni: str) -> tuple[str, str]:
    """
    Return (tipo_documento, numero_documento) based on DNI content.

    Rules:
        - empty/blank -> SIN_DOCUMENTO, 00000000
        - 8 chars (all digits) -> DNI, the value
        - otherwise -> RUC, the value
    """
    dni = str(dni).strip() if dni else ""
    if not dni:
        return "SIN_DOCUMENTO", "00000000"
    if len(dni) == 8 and dni.isdigit():
        return "DNI", dni
    return "RUC", dni


# ── Distrito normalization helpers ────────────────────────────────────────────────


# Mapeo regex → (nombre canónico de distrito, nombre de provincia) en UbigeoDistrito.
# Los nombres históricos del Excel no siempre coinciden con la BD de ubigeo.
# provincia=None cuando el nombre del distrito ya es único.
DISTRITO_SINONIMOS: list[tuple[str, tuple[str, str | None]]] = [
    (r"^CERCADO\s+DE\s+LIMA$", ("LIMA", None)),
    (r"^CENTRO\s+HIST[OÓ]RICO\s+DE\s+LIMA$", ("LIMA", None)),
    (r"^LIMA\s+CERCADO\s+Y\s+PROVINCIAL\s+LIMA$", ("LIMA", None)),
    (r"^ATE\s+VITARTE$", ("ATE", None)),
    (r"^LURIGANCHO\s*[-–]\s*CHOSICA$", ("LURIGANCHO", None)),
    (r"^BARRANCA\s*[-–]\s*NORTE$", ("BARRANCA", None)),
    # "SAN ANTONIO" es ambiguo (6 distritos homónimos). Acá es el de la provincia HUAROCHIRI.
    (r"^SAN\s+ANTONIO\s+DE\s+HUAROCHIRI$", ("SAN ANTONIO", "HUAROCHIRI")),
]


def normalizar_distrito(nombre: str) -> tuple[str, str | None]:
    """Normaliza un nombre histórico de distrito a (nombre canónico, provincia o None)."""
    if not nombre:
        return "", None
    nombre = nombre.strip().upper()
    for pattern, (canon, provincia) in DISTRITO_SINONIMOS:
        if re.match(pattern, nombre):
            return canon, provincia
    return nombre, None


# ── TPERSONA parsing ────────────────────────────────────────────────────────────


def parse_tpersona(raw) -> tuple[str | None, str | None]:
    """
    Parse TPERSONA value into (nombres, apellidos).

    Rules:
        - 1 part  -> nombres=part[0], apellidos=None
        - 2-3 parts -> nombres=part[0], apellidos=" ".join(rest)
        - 4+ parts -> nombres=" ".join(part[0:2]), apellidos=" ".join(part[2:])
        - empty/None -> (None, None)
    """
    if raw is None:
        return None, None
    text = str(raw).strip()
    if not text or text.upper() == "NULL":
        return None, None
    parts = text.split()
    if len(parts) == 1:
        return parts[0], None
    elif 2 <= len(parts) <= 3:
        return parts[0], " ".join(parts[1:])
    else:  # 4+
        return " ".join(parts[:2]), " ".join(parts[2:])


# ── Specialty normalization ─────────────────────────────────────────────────────


def normalize_specialty(value: str) -> str:
    """Normaliza acentos/case para lookup robusto de ESPECIALIDAD."""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return normalized.lower().strip()


# ── Comprobante, RH slot, monetary parsers (moved from import_legacy_edificaciones) ─


def parse_comprobante(row: list, col_nrofactura: int) -> dict:
    """
    Parse NROFACTURA into serie and numero.

    The legacy NROFACTURA format is typically '001-00001' (serie-numero).
    Split on the first '-' found; strip whitespace.

    Returns:
        {"serie": str, "numero": str} if parseable.
        {"serie": None, "numero": None, "raw": str} if empty/invalid.
    """
    raw = row[col_nrofactura] if len(row) > col_nrofactura else None
    if raw is None:
        return {"serie": None, "numero": None, "raw": None}
    text = str(raw).strip()
    if not text or text.upper() in ("NULL", ""):
        return {"serie": None, "numero": None, "raw": text}

    if "-" in text:
        parts = text.split("-", 1)
        return {"serie": parts[0].strip(), "numero": parts[1].strip(), "raw": text}

    return {"serie": None, "numero": text, "raw": text}


def tipo_comprobante_from_nrofactura(raw: str | None) -> str | None:
    """
    Map NROFACTURA prefix to TipoComprobante value.

    Returns:
        'FACTURA' if raw starts with 'FAC'
        'BOLETA' if raw starts with 'BOL'
        None otherwise
    """
    if not raw:
        return None
    upper = str(raw).strip().upper()
    if upper.startswith("FAC"):
        return "FACTURA"
    if upper.startswith("BOL"):
        return "BOLETA"
    return None


def parse_total(row: list, col_total: int) -> Decimal | None:
    """
    Parse TOTAL column from a legacy row into a Decimal.

    Returns None if absent/invalid/zero.
    """
    if len(row) <= col_total:
        return None
    raw = row[col_total]
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.upper() == "NULL":
        return None
    try:
        val = Decimal(text)
        return val if val != 0 else None
    except (InvalidOperation, ValueError):
        return None


def parse_row_monetary(
    row: list,
    col_impbruto: int,
    col_rentacip: int,
    col_aporcodemu: int,
    col_fondocomun: int,
    col_netohonora: int,
    col_subtotal: int,
) -> dict:
    """
    Parse shared monetary fields from a row.

    These are fixed source values shared by all active slots in the same row:
        IMPBRUTO, RENTACIP, APORCODEMU, FONDOCOMUN, NETOHONORA, SUBTOTAL.

    Returns dict with Decimal values (or None if absent/invalid).
    """
    def _dec(raw):
        if raw is None:
            return None
        text = str(raw).strip()
        if not text or text.upper() == "NULL":
            return None
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            return None

    return {
        "imp_bruto": _dec(row[col_impbruto] if len(row) > col_impbruto else None),
        "renta_cip": _dec(row[col_rentacip] if len(row) > col_rentacip else None),
        "aporte_codemu": _dec(row[col_aporcodemu] if len(row) > col_aporcodemu else None),
        "fondo_comun": _dec(row[col_fondocomun] if len(row) > col_fondocomun else None),
        "neto_honorario": _dec(row[col_netohonora] if len(row) > col_netohonora else None),
        "subtotal": _dec(row[col_subtotal] if len(row) > col_subtotal else None),
    }


def parse_rh_slot(
    row: list,
    slot_num: int,
    rh_slot_columns: dict,
    cip_embedded_re,
    slot_specialty_map: dict,
) -> dict | None:
    """
    Parse a single RH slot (1..4) from a row.

    Returns None if the slot has no assigned delegate/CIP (skip signal).

    Otherwise returns a dict with all slot fields.

    Args:
        row: Split CSV row.
        slot_num: Slot number (1..4).
        rh_slot_columns: Mapping slot_num -> tuple of column indices (from package).
        cip_embedded_re: Compiled regex to extract embedded CIP from delegate name.
        slot_specialty_map: Mapping slot_num -> display name for the specialty.

    Skip reasons (returns None):
        - No CIP value present
        - No DELEGADO value present
    """
    slot_tuple = rh_slot_columns.get(slot_num)
    if slot_tuple is None:
        return None
    (
        col_delegado,
        col_cip,
        col_periodo,
        col_mes,
        col_fecha_pres,
        col_fecha_rev,
        col_nro_orden,
        col_dictamen,
        col_nro_rh,
        col_nro_mm,
    ) = slot_tuple

    def _col(idx: int):
        return row[idx] if len(row) > idx else None

    cip_raw = _col(col_cip)
    cip = coerce_int(cip_raw)

    delegado_raw = _col(col_delegado)
    delegado_text = (
        str(delegado_raw).strip()
        if delegado_raw is not None
        else None
    )
    if not delegado_text or delegado_text.upper() == "NULL":
        return None

    if cip is None:
        m = cip_embedded_re.search(delegado_text) if cip_embedded_re else None
        if m is not None:
            cip = coerce_int(m.group(1))

    if cip is None:
        return None

    periodo = coerce_int(_col(col_periodo))
    mes = coerce_month(_col(col_mes))

    return {
        "slot": slot_num,
        "specialty": slot_specialty_map.get(slot_num, ""),
        "delegado": delegado_text,
        "cip": cip,
        "periodo": periodo,
        "mes": mes,
        "fecha_presentacion": _parse_date(_col(col_fecha_pres)),
        "fecha_revision": _parse_date(_col(col_fecha_rev)),
        "nro_orden": coerce_int(_col(col_nro_orden)),
        "dictamen": str(_col(col_dictamen)).strip() if _col(col_dictamen) is not None else None,
        "nro_rh": coerce_int(_col(col_nro_rh)),
        "nro_mm": coerce_int(_col(col_nro_mm)),
        "skip_reason": None,
    }
