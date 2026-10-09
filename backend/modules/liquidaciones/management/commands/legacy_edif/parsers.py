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
