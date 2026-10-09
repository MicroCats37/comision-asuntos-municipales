"""
Management command to import legacy Inspección de Obra (IO) data from a CSV file.

Usage (Batch 3 — parser + dry-run + reports only, NO database writes):
    python manage.py import_legacy_inspeccion_obra --dry-run --limit 100 \
        --settings=config.settings.development --traceback

Source file:
    backend/core_application/seeds/historico/IO_ALL.csv
    (63 columns, delimiter ';', BOM UTF-8)

Batch 3b scope (this correction):
    - Corrected: cantidad_visitas is NROREV (not SUBTOTAL/PORCENTAJE)
    - Parse/store NROREV, TASA, PORCENFINA, TASAIGV as raw source fields
    - Compute and report legacy unitario validation fields:
        subtotal_unitario_legacy  = SUBTOTAL / NROREV
        total_unitario_legacy     = TOTAL / NROREV
        subtotal_unitario_recalc  = TASA * UIT
        total_unitario_recalc     = subtotal_unitario_recalc * (1 + TASAIGV/100)
        diff_subtotal_unitario
        diff_total_unitario
        validation_status: OK | DIF_SUBTOTAL | DIF_TOTAL | SIN_DATOS
    - cantidad_visitas = NROREV (positive integer → 'from_nrorev')
    - Zero/missing/invalid NROREV → anomaly (not silently derived)

Column semantics (validated against supervisones.csv):
    NROREV    = cantidad de revisiones/visitas cobradas (integer)
    TASA      = effective UIT percentage for subtotal calculation
    PORCENFINA = nominal/rounded rate (informational only)
    PORCENTAJE = unit total with IGV (TOTAL / NROREV) — despite the column name
    SUBTOTAL  = historical source net amount (do NOT change)
    IGV       = historical source IGV (do NOT change)
    TOTAL     = historical source total (do NOT change)

Batches 4+ will implement the full DB creation chain.

Source file format (from supervisones.csv header):
    ID  NRO  RUC  NOMBRE  NROREV  DPTOPRDI  DIRECCION  DELEGADO  UIT
    PORCENTAJE  PORCENFINA  SUBTOTAL  IGV  TOTAL  FECHA  DNI  RAZONSOCIAL
    VALOROBRA  TASA  NROEXPDTE  CODPAGO  NROFACTURA  DLEY  IMPBRUTO
    APORCODEMU  FONDOCOMUN  HONORARIO  IMPUESRENTA  NETOHONORA  USUARIO
    IMPRESO  DOC  FECHAPRES  NROORDEN  FECHAREVI  MES  PERIODO  NRORECIBO
    FECHARECIBO  NROMEMO  OBSERVA  DICTAMEN  TDNI  TFONO  TPERSONA  TASAIGV
    FECOMPRO  NRONC  NROQRPLZA  RENTACIP  DSCTO  RUCDIRECC  RETENCION  CIP
    BLKDEL  NROCHEQUE  CONCEPTO  REINTEGRO  CATEGORIA  PENDIENTES  PAGADAS
    REALIZADAS  DIFERENCIA
"""

import csv
import io
import logging
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

# Default path to legacy IO data file (relative to backend/)
DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "core_application" / "seeds" / "historico" / "IO_ALL.csv"

# ── TSV column indices (0-indexed after splitting header by delimiter) ──────────
# Determined at runtime from the actual header row.
# Expected header order (tab-delimited):
# ID | NRO | RUC | NOMBRE | NROREV | DPTOPRDI | DIRECCION | DELEGADO | UIT |
# PORCENTAJE | PORCENFINA | SUBTOTAL | IGV | TOTAL | FECHA | DNI | RAZONSOCIAL |
# VALOROBRA | TASA | NROEXPDTE | CODPAGO | NROFACTURA | DLEY | IMPBRUTO |
# APORCODEMU | FONDOCOMUN | HONORARIO | IMPUESRENTA | NETOHONORA | USUARIO |
# IMPRESO | DOC | FECHAPRES | NROORDEN | FECHAREVI | MES | PERIODO | NRORECIBO |
# FECHARECIBO | NROMEMO | OBSERVA | DICTAMEN | TDNI | TFONO | TPERSONA | TASAIGV |
# FECOMPRO | NRONC | NROQRPLZA | RENTACIP | DSCTO | RUCDIRECC | RETENCION | CIP |
# BLKDEL | NROCHEQUE | CONCEPTO | REINTEGRO | CATEGORIA | PENDIENTES | PAGADAS |
# REALIZADAS | DIFERENCIA

_COL_ID = 0
_COL_NRO = 1
_COL_RUC = 2
_COL_NOMBRE = 3
_COL_NROREV = 4
_COL_DPTOPRDI = 5
_COL_DIRECCION = 6
_COL_DELEGADO = 7
_COL_UIT = 8
_COL_PORCENTAJE = 9
_COL_PORCENFINA = 10
_COL_SUBTOTAL = 11
_COL_IGV = 12
_COL_TOTAL = 13
_COL_FECHA = 14
_COL_DNI = 15
_COL_RAZONSOCIAL = 16
_COL_VALOROBRA = 17
_COL_TASA = 18
_COL_NROEXPDTE = 19
_COL_CODPAGO = 20
_COL_NROFACTURA = 21
_COL_DLEY = 22
_COL_IMPBRUTO = 23
_COL_APORCODEMU = 24
_COL_FONDOCOMUN = 25
_COL_HONORARIO = 26
_COL_IMPUESRENTA = 27
_COL_NETOHONORA = 28
_COL_USUARIO = 29
_COL_IMPRESO = 30
_COL_DOC = 31
_COL_FECHAPRES = 32
_COL_NROORDEN = 33
_COL_FECHAREVI = 34
_COL_MES = 35
_COL_PERIODO = 36
_COL_NRORECIBO = 37
_COL_FECHARECIBO = 38
_COL_NROMEMO = 39
_COL_OBSERVA = 40
_COL_DICTAMEN = 41
_COL_TDNI = 42
_COL_TFONO = 43
_COL_TPERSONA = 44
_COL_TASAIGV = 45
_COL_FECOMPRO = 46
_COL_NRONC = 47
_COL_NROQRPLZA = 48
_COL_RENTACIP = 49
_COL_DSCTO = 50
_COL_RUCDIRECC = 51
_COL_RETENCION = 52
_COL_CIP = 53
_COL_BLKDEL = 54
_COL_NROCHEQUE = 55
_COL_CONCEPTO = 56
_COL_REINTEGRO = 57
_COL_CATEGORIA = 58
_COL_PENDIENTES = 59
_COL_PAGADAS = 60
_COL_REALIZADAS = 61
_COL_DIFERENCIA = 62


# ── Sentinel date ────────────────────────────────────────────────────────────────
_SENTINEL_DATE = date(1900, 1, 1)


# ── Decimal helpers ──────────────────────────────────────────────────────────────

def _dec(raw, default=None) -> Decimal | None:
    """Parse a raw cell value to Decimal. Returns default if absent/invalid."""
    if raw is None:
        return default
    text = str(raw).strip()
    if not text or text.upper() in ("NULL", ""):
        return default
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return default


def _int(raw, default=None) -> int | None:
    """Parse a raw cell value to int. Returns default if absent/invalid."""
    if raw is None:
        return default
    text = str(raw).strip()
    if not text or text.upper() in ("NULL", ""):
        return default
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return default


# ── Date parsing ────────────────────────────────────────────────────────────────

def _parse_fecha(raw) -> date | None:
    """
    Parse FECHA / FECHAPRES / FECHAREVI / FECOMPRO value to date.

    Returns None for sentinel date 1/01/1900.
    Raises ValueError for unparseable non-sentinel values.
    """
    if raw is None:
        return None
    if isinstance(raw, datetime):
        d = raw.date()
        if d == _SENTINEL_DATE:
            return None
        return d
    text = str(raw).strip()
    if not text or text.upper() in ("NULL", ""):
        return None
    # Check for sentinel
    if re.match(r"^1/\d{2}/1900", text):
        return None
    for fmt in (
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            d = datetime.strptime(text, fmt).date()
            if d == _SENTINEL_DATE:
                return None
            return d
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date: {raw!r}")


# ── DPTOPRDI parsing ───────────────────────────────────────────────────────────

def _parse_dptoprdri(raw) -> tuple[str, str]:
    """
    Parse DPTOPRDI value like 'LIMA/MAGDALENA DEL MAR' into (provincia, distrito).

    Returns (provincia, distrito). Both are upper-stripped.
    If no '/' present, returns ('', raw_upper).
    """
    if not raw:
        return "", ""
    text = str(raw).strip()
    if "/" in text:
        parts = text.split("/", 1)
        return parts[0].strip().upper(), parts[1].strip().upper()
    return "", text.strip().upper()


# ── Documento parsing ─────────────────────────────────────────────────────────

def _resolve_tipo_documento(dni_raw, ruc_raw) -> tuple[str, str]:
    """
    Return (tipo_documento, numero_documento) based on DNI/RUC content.

    Rules:
        - Both empty/blank -> SIN_DOCUMENTO, 00000000
        - 8 digits (DNI) -> DNI, the value
        - Otherwise -> RUC, the value (RUC or other)
    """
    dni = str(dni_raw).strip() if dni_raw else ""
    ruc = str(ruc_raw).strip() if ruc_raw else ""

    if not dni and not ruc:
        return "SIN_DOCUMENTO", "00000000"
    if len(dni) == 8 and dni.isdigit():
        return "DNI", dni
    if ruc:
        return "RUC", ruc
    if dni:
        return "DNI", dni
    return "SIN_DOCUMENTO", "00000000"


# ── DELEGADO parsing (IO specific) ────────────────────────────────────────────

_DELEGADO_RE = re.compile(r"^CIP\s+(\d+)\s*[-–—]\s*(.+)$", re.IGNORECASE)


def _parse_delegado_io(raw) -> tuple[int | None, str | None]:
    """
    Parse DELEGADO value from IO source.

    Format: "CIP 072900-CASTAÑEDA AMES VIVIANA PAOLA"

    Returns (cip_number, nombre_completo). cip_number is int (without leading zeros).
    Returns (None, None) if unparseable.
    """
    if not raw:
        return None, None
    text = str(raw).strip()
    if not text or text.upper() in ("NULL", ""):
        return None, None
    match = _DELEGADO_RE.match(text)
    if match:
        cip_str = match.group(1).lstrip("0")
        cip = int(cip_str) if cip_str else int(match.group(1))
        nombre = match.group(2).strip()
        return cip, nombre
    return None, text


# ── CATEGORIA mapping ──────────────────────────────────────────────────────────

def _map_categoria_io(categoria_raw) -> tuple[str | None, str]:
    """
    Map source CATEGORIA integer (0-4) to internal category.

    Returns (mapped_category, status) where:
        - CATEGORIA=0 -> (None, 'null_tariff')  — no corresponding tariff
        - CATEGORIA=1 -> ('C1', 'mapped')
        - CATEGORIA=2 -> ('C2', 'mapped')
        - CATEGORIA=3 -> ('C3', 'mapped')
        - CATEGORIA=4 -> ('C4', 'mapped')
        - invalid/other -> (str(value), 'anomaly')
    """
    val = _int(categoria_raw)
    if val is None:
        return None, "anomaly"
    if val == 0:
        return None, "null_tariff"
    if val == 1:
        return "C1", "mapped"
    if val == 2:
        return "C2", "mapped"
    if val == 3:
        return "C3", "mapped"
    if val == 4:
        return "C4", "mapped"
    return str(val), "anomaly"


# ── Cantidad visitas derivation (NROREV-based) ─────────────────────────────────

def _derive_cantidad_visitas(nrorev: int | None) -> tuple[float | None, str]:
    """
    Derive cantidad_visitas from NROREV (the actual visit/revision count).

    In supervisones.csv, NROREV is the number of IO review/visit units billed.
    cantidad_visitas = NROREV directly — NOT derived from SUBTOTAL/PORCENTAJE.

    Returns (cantidad_visitas, status) where status is:
        - 'from_nrorev'   — positive integer taken directly from NROREV
        - 'non_positive'   — NROREV is present but <= 0
        - 'missing'        — NROREV absent or unparseable
    """
    if nrorev is None:
        return None, "missing"
    if nrorev <= 0:
        return None, "non_positive"
    return float(nrorev), "from_nrorev"


def _compute_uit_implicita(
    subtotal: Decimal | None,
    nrorev: int | None,
    tasa: Decimal | None,
) -> Decimal | None:
    """
    Compute implied UIT from source amounts and rate.

    Formula: uit_implicita = (SUBTOTAL / NROREV) / TASA
    This inverts: SUBTOTAL = NROREV * TASA * UIT

    Returns uit_implicita as Decimal, or None if computation is not possible.
    """
    if subtotal is None or nrorev is None or nrorev <= 0 or tasa is None or tasa <= 0:
        return None

    try:
        unitario = subtotal / Decimal(nrorev)
        uit_implicita = unitario / tasa
    except (InvalidOperation, ZeroDivisionError, TypeError):
        return None

    return uit_implicita


def _build_uit_validacion_detalle(
    uit_archivo: Decimal | None,
    uit_implicita: Decimal | None,
    uit_implicita_status: str,
) -> str:
    """
    Build a human-readable UIT validation detail string.

    Returns:
        - OK_IGUAL_ARCHIVO:
            "La UIT del archivo explica el subtotal unitario."
        - DIF_UIT:
            "El subtotal unitario implica UIT=X, que difiere de la UIT del archivo (Y)."
        - SIN_UIT_ARCHIVO:
            "No hay UIT en el archivo; el subtotal unitario implica UIT=X."
        - SIN_DATOS:
            "No se pudo validar por NROREV, TASA, UIT o SUBTOTAL faltante/cero."
    """
    if uit_implicita_status == "SIN_DATOS":
        return "No se pudo validar por NROREV, TASA, UIT o SUBTOTAL faltante/cero."

    if uit_implicita_status == "OK_IGUAL_ARCHIVO":
        return "La UIT del archivo explica el subtotal unitario."

    if uit_implicita_status == "DIF_UIT":
        uit_archivo_val = int(uit_archivo) if uit_archivo is not None else None
        uit_impl_val = int(round(uit_implicita)) if uit_implicita is not None else None
        if uit_archivo_val is not None and uit_impl_val is not None:
            return (
                f"El subtotal unitario implica UIT={uit_impl_val}, "
                f"que difiere de la UIT del archivo ({uit_archivo_val})."
            )
        elif uit_impl_val is not None:
            return (
                f"El subtotal unitario implica UIT={uit_impl_val}, "
                f"que difiere de la UIT del archivo."
            )
        return "El subtotal unitario difiere de la UIT del archivo."

    if uit_implicita_status == "SIN_UIT_ARCHIVO":
        uit_impl_val = int(round(uit_implicita)) if uit_implicita is not None else None
        if uit_impl_val is not None:
            return (
                f"No hay UIT en el archivo; el subtotal unitario implica UIT={uit_impl_val}."
            )
        return "No hay UIT en el archivo y no se pudo calcular UIT implícita."

    return ""


# ── NROFACTURA parsing ─────────────────────────────────────────────────────────

def _parse_nrofactura(raw) -> tuple[str | None, str | None, str]:
    """
    Parse NROFACTURA into serie and numero.

    Returns (serie, numero, raw_original).
    If empty/invalid, returns (None, None, raw_original).
    """
    if raw is None:
        return None, None, ""
    text = str(raw).strip()
    if not text or text.upper() in ("NULL", ""):
        return None, None, text
    if "-" in text:
        parts = text.split("-", 1)
        return parts[0].strip(), parts[1].strip(), text
    return None, text, text


# ── TPERSONA parsing (shared pattern with EDIF/HU) ────────────────────────────

def _parse_tpersona(raw) -> tuple[str, str | None]:
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


# ── Serie normalization for legacy IO invoices ─────────────────────────────────

def _normalize_serie_factura(raw: str | None) -> str | None:
    """
    Normalize a numeric legacy invoice series to prefixed form.

    Rules:
        - Already prefixed (F003, F002, B001, etc.) -> uppercase, returned as-is
        - Pure numeric (003, 002) -> prefixed with 'F' (F003, F002)
        - Empty/invalid -> None
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.upper() in ("NULL", ""):
        return None
    upper = text.upper()
    # Already has F or B prefix
    if upper.startswith(("F", "B")):
        return upper
    # Pure numeric: 003 -> F003
    if text.isdigit():
        return f"F{text}"
    return upper


# ── LiquidacionComprobante helpers ───────────────────────────────────────────

def _tipo_comprobante_from_serie(raw: str | None) -> str | None:
    """
    Map NROFACTURA prefix to TipoComprobante value.

    Returns:
        'FACTURA' if raw starts with 'F'
        'BOLETA' if raw starts with 'B'
        None otherwise
    """
    if not raw:
        return None
    upper = str(raw).strip().upper()
    if upper.startswith("F"):
        return "FACTURA"
    if upper.startswith("B"):
        return "BOLETA"
    return None


def _upsert_liquidacion_comprobante(
    liquidacion: "LiquidacionGeneral",
    nro_factura_raw: str | None,
    fe_compro: "date | None",
    total: "Decimal | None",
    dry_run: bool = False,
) -> tuple["LiquidacionComprobante | None", str]:
    """
    Create or update a LiquidacionComprobante for a LiquidacionGeneral.

    Idempotency: finds existing active comprobante (activo=True) for this
    liquidation and updates it in-place rather than creating a duplicate.

    Args:
        liquidacion: LiquidacionGeneral instance (same-row).
        nro_factura_raw: Original NROFACTURA string from source.
        fe_compro: Parsed date from FECOMPRO column.
        total: Decimal total from legacy TOTAL column.
        dry_run: If True, do not write to DB.

    Returns:
        (comprobante, status) where status is:
            "CREADO"     - created new active comprobante
            "ACTUALIZADO" - updated existing active comprobante
            "OMITIDO"     - NROFACTURA blank/malformed; no comprobante created
            "ERROR"       - unexpected failure
    """
    raw_nrofactura = nro_factura_raw or ""
    # Parse into serie/numero
    if "-" in raw_nrofactura:
        parts = raw_nrofactura.split("-", 1)
        serie_raw, numero = parts[0].strip(), parts[1].strip()
    else:
        serie_raw, numero = None, raw_nrofactura.strip()

    # Normalize serie: numeric legacy series like 003 -> F003
    serie = _normalize_serie_factura(serie_raw)
    numero = numero.strip() if numero else None

    # Skip if no usable NROFACTURA
    if serie is None and numero is None:
        return None, "OMITIDO"

    if dry_run:
        existing = LiquidacionComprobante.objects.filter(
            liquidacion_general=liquidacion,
            activo=True,
        ).first()
        if existing:
            return existing, "ACTUALIZADO"
        return None, "CREADO"

    try:
        existing = LiquidacionComprobante.objects.filter(
            liquidacion_general=liquidacion,
            activo=True,
        ).first()

        tipo = _tipo_comprobante_from_serie(serie or nro_factura_raw)

        if existing:
            # Update existing active comprobante in-place
            existing.serie = serie
            existing.numero = numero
            existing.tipo_comprobante = tipo
            existing.fecha_emision = fe_compro
            existing.monto = total
            existing.save()
            return existing, "ACTUALIZADO"

        # Create new comprobante
        comp = LiquidacionComprobante.objects.create(
            liquidacion_general=liquidacion,
            tipo_comprobante=tipo,
            serie=serie,
            numero=numero,
            fecha_emision=fe_compro,
            monto=total,
            activo=True,
        )
        return comp, "CREADO"
    except Exception:  # noqa: BLE001
        return None, "ERROR"


# ── Contacto helpers ──────────────────────────────────────────────────────────

def _upsert_contacto(
    liquidacion: "LiquidacionGeneral",
    nombres: str | None,
    apellidos: str | None,
    dni: str | None,
    telefono: str | None,
    dry_run: bool = False,
) -> tuple["Contacto | None", str]:
    """
    Create or update a Contacto and attach it as principal to a LiquidacionGeneral.

    Idempotency: if the liquidation already has a principal contact, update
    missing fields only. If no principal contact exists, create and attach one.

    Args:
        liquidacion: LiquidacionGeneral instance.
        nombres: Parsed nombres from TPERSONA.
        apellidos: Parsed apellidos from TPERSONA.
        dni: DNI from TDNI column (may be None).
        telefono: Telefono from TFONO column (may be None).
        dry_run: If True, do not write to DB.

    Returns:
        (contacto, status) where status is:
            "CREADO"     - created new contacto and attached
            "ACTUALIZADO" - updated existing principal contacto
            "OMITIDO"    - no useful contact data (nombres and telefono both absent)
            "ERROR"      - unexpected failure
    """
    # Must have at least nombres or telefono to create contact
    has_nombres = nombres is not None and nombres != ""
    has_telefono = telefono is not None and telefono != ""
    if not has_nombres and not has_telefono:
        return None, "OMITIDO"

    if dry_run:
        existing_principal = LiquidacionContacto.objects.filter(
            liquidacion=liquidacion,
            principal=True,
        ).select_related("contacto").first()
        if existing_principal:
            return existing_principal.contacto, "ACTUALIZADO"
        return None, "CREADO"

    try:
        # Check for existing principal contact
        existing_lc = LiquidacionContacto.objects.filter(
            liquidacion=liquidacion,
            principal=True,
        ).select_related("contacto").first()

        if existing_lc:
            # Update missing fields only
            contacto = existing_lc.contacto
            updated = False
            if has_nombres and not contacto.nombres:
                contacto.nombres = nombres
                updated = True
            if has_telefono and not contacto.telefono:
                contacto.telefono = telefono
                updated = True
            if dni and not contacto.dni:
                contacto.dni = dni
                updated = True
            if updated:
                contacto.save()
            return contacto, "ACTUALIZADO"

        # Create new contacto
        contacto = Contacto.objects.create(
            nombres=nombres if has_nombres else None,
            apellidos=apellidos,
            dni=dni,
            telefono=telefono if has_telefono else None,
        )
        LiquidacionContacto.objects.create(
            liquidacion=liquidacion,
            contacto=contacto,
            principal=True,
        )
        return contacto, "CREADO"
    except Exception:  # noqa: BLE001
        return None, "ERROR"


# ── Username normalization ──────────────────────────────────────────────────────

def _normalize_usuario_to_username(usuario_raw) -> str | None:
    """
    Transform a USUARIO raw value into a normalized username slug.

    Same logic as Edificaciones import for consistency.
    """
    if usuario_raw is None:
        return None
    text = str(usuario_raw).strip()
    if not text or text.upper() == "NULL":
        return None
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", ".", normalized)
    normalized = re.sub(r"[^a-z0-9._-]", "", normalized)
    normalized = normalized.strip(".-_")
    if not normalized:
        return None
    return normalized


# ── File reading helpers ────────────────────────────────────────────────────────

def _detect_delimiter(first_line: str) -> str:
    """
    Detect the most likely delimiter in a text file by sampling the header row.

    Returns ';' for CSV with semicolon, '\t' for TSV, or ',' for CSV. Falls back to '\t'.
    """
    if ";" in first_line:
        return ";"
    if "\t" in first_line:
        return "\t"
    if "," in first_line:
        return ","
    return "\t"


def _is_xlsx(file_path: Path) -> bool:
    """Check if a file is an Excel .xlsx by its PK (ZIP) header signature."""
    try:
        with file_path.open("rb") as f:
            header = f.read(4)
        # PK signature for ZIP/XLSX
        return header[:2] == b"PK"
    except OSError:
        return False


def _read_tsv(file_path: Path) -> tuple[list[str], list[list[str]]]:
    """
    Read a TSV file with robust encoding handling.

    Tries UTF-8 first, then latin-1. Detects delimiter from first line.

    Returns (headers, rows) where headers is a list of column names and
    rows is a list of lists of cell string values.
    """
    # Try UTF-8 with BOM (utf-8-sig strips the BOM automatically)
    try:
        raw = file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raw = file_path.read_text(encoding="latin-1")

    # Normalize line endings
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")

    lines = raw.split("\n")
    if not lines:
        raise CommandError(f"Empty file: {file_path}")

    delimiter = _detect_delimiter(lines[0])
    reader = csv.reader(lines[1:], delimiter=delimiter)
    rows = [list(r) for r in reader if r]  # skip blank lines

    # Parse header
    header_line = lines[0].strip()
    if not header_line:
        raise CommandError("Cannot parse header from file")
    header_reader = csv.reader([header_line], delimiter=delimiter)
    headers = list(next(header_reader))

    return headers, rows


# ── Row-level parser ───────────────────────────────────────────────────────────

class ParsedRow:
    """
    Container for all parsed fields from a single source row.

    New fields added in batch 3b (NROREV correction):
        nrorev                          — raw NROREV from source
        tasa                            — TASA (effective UIT percentage)
        porcenfina                      — PORCENFINA (nominal/rounded rate, informational)
        nrorev_status                   — 'from_nrorev' | 'non_positive' | 'missing'
        subtotal_unitario_legacy         — SUBTOTAL / NROREV
        total_unitario_legacy            — TOTAL / NROREV
        subtotal_unitario_recalc_legacy  — TASA * UIT
        total_unitario_recalc_legacy     — (TASA * UIT) * (1 + TASAIGV/100)
        diff_subtotal_unitario_legacy    — abs(subtotal_unitario_legacy - subtotal_unitario_recalc_legacy)
        diff_total_unitario_legacy       — abs(total_unitario_legacy - total_unitario_recalc_legacy)
        validation_status                — OK | DIF_SUBTOTAL | DIF_TOTAL | SIN_DATOS
    """
    __slots__ = (
        "row_index", "raw", "id_val", "nro", "nroexpdte", "codpago", "dptoprdri",
        "direccion", "nombre", "ruc", "dni", "razon_social",
        "fecha", "uit", "porcentaje", "subtotal", "igv", "total", "tasa_igv",
        "imp_bruto", "aporte_codemu", "fondo_comun", "honorario", "impuesto_renta",
        "neto_honorario", "renta_cip", "dscto", "retencion",
        "delegado", "delegado_nombre", "cip",
        "categoria_raw", "categoria_mapped", "categoria_status",
        "pendientes", "pagadas", "realizadas", "diferencia",
        "nro_factura", "fe_factura", "fecha_pres", "fecha_revi",
        "nro_orden", "dictamen", "usuario",
        "cantidad_visitas", "visitas_status",
        "documento_tipo", "documento_numero",
        "modo_calculo", "rechazo_motivo", "anomalies",
        # Batch 3b: NROREV correction fields
        "nrorev", "tasa", "porcenfina", "nrorev_status",
        "subtotal_unitario_legacy", "total_unitario_legacy",
        "subtotal_unitario_recalc_legacy", "total_unitario_recalc_legacy",
        "diff_subtotal_unitario_legacy", "diff_total_unitario_legacy",
        "validation_status",
        # Batch 3c: UIT implied fields
        "uit_implicita", "uit_implicita_status",
        # Batch 3d: UIT validation human-readable detail
        "uit_validacion_detalle", "existing_liquidacion_general",
    )

    def __init__(self):
        self.row_index: int = 0
        self.raw: list = []
        self.id_val: int | None = None
        self.nro: int | None = None
        self.nroexpdte: str | None = None
        self.codpago: str = ""
        self.dptoprdri: str = ""
        self.direccion: str = ""
        self.nombre: str = ""
        self.ruc: str = ""
        self.dni: str = ""
        self.razon_social: str = ""
        self.fecha: date | None = None
        self.uit: Decimal | None = None
        self.porcentaje: Decimal | None = None
        self.subtotal: Decimal | None = None
        self.igv: Decimal | None = None
        self.total: Decimal | None = None
        self.tasa_igv: Decimal | None = None
        self.imp_bruto: Decimal | None = None
        self.aporte_codemu: Decimal | None = None
        self.fondo_comun: Decimal | None = None
        self.honorario: Decimal | None = None
        self.impuesto_renta: Decimal | None = None
        self.neto_honorario: Decimal | None = None
        self.renta_cip: Decimal | None = None
        self.dscto: Decimal | None = None
        self.retencion: Decimal | None = None
        self.delegado: str = ""
        self.delegado_nombre: str = ""
        self.cip: int | None = None
        self.categoria_raw: int | None = None
        self.categoria_mapped: str | None = None
        self.categoria_status: str = ""
        self.pendientes: int = 0
        self.pagadas: int = 0
        self.realizadas: int = 0
        self.diferencia: int = 0
        self.nro_factura: str | None = None
        self.fe_factura: date | None = None
        self.fecha_pres: date | None = None
        self.fecha_revi: date | None = None
        self.nro_orden: int = 0
        self.dictamen: str = ""
        self.usuario: str = ""
        self.cantidad_visitas: float | None = None
        self.visitas_status: str = ""
        self.documento_tipo: str = ""
        self.documento_numero: str = ""
        self.modo_calculo: str = "TARIFA"
        self.rechazo_motivo: str = ""
        self.anomalies: list[str] = []
        # Batch 3b: NROREV correction fields
        self.nrorev: int | None = None
        self.tasa: Decimal | None = None
        self.porcenfina: Decimal | None = None
        self.nrorev_status: str = ""
        self.subtotal_unitario_legacy: Decimal | None = None
        self.total_unitario_legacy: Decimal | None = None
        self.subtotal_unitario_recalc_legacy: Decimal | None = None
        self.total_unitario_recalc_legacy: Decimal | None = None
        self.diff_subtotal_unitario_legacy: Decimal | None = None
        self.diff_total_unitario_legacy: Decimal | None = None
        self.validation_status: str = ""
        # Batch 3c: UIT implied fields
        self.uit_implicita: Decimal | None = None
        self.uit_implicita_status: str = ""
        # Batch 3d: UIT validation human-readable detail
        self.uit_validacion_detalle: str = ""
        self.existing_liquidacion_general = None

    def to_report_row(self) -> list:
        """Return a row for the rechazo CSV report."""
        return [
            self.row_index,
            self.nroexpdte or "",
            self.rechazo_motivo or "",
            str(self.categoria_raw) if self.categoria_raw is not None else "",
            self.categoria_mapped or "",
            "",  # TARIFA_ID — not resolved in batch 3
            str(self.subtotal) if self.subtotal is not None else "",
            "",  # SUBTOTAL_RECALC — batch 4+
            "",  # DIF
            self.modo_calculo,
            "N/A",  # SUBIDO — batch 4+ creates actual records
        ]

    def to_detailed_report_row(self, headers: list[str]) -> list:
        """Return a row for the detailed CSV report matching all source + parsed fields."""
        return [
            self.row_index,          # FILA
            self.id_val,            # ID
            self.nro,               # NRO
            self.nroexpdte,         # NROEXPDTE
            self.codpago,           # CODPAGO
            self.dptoprdri,         # DPTOPRDI
            self.direccion,         # DIRECCION
            self.nombre,            # NOMBRE
            self.razon_social,      # RAZONSOCIAL
            self.ruc,               # RUC
            self.dni,               # DNI
            self.fecha.isoformat() if self.fecha else "",  # FECHA
            str(self.uit) if self.uit else "",            # UIT
            str(self.porcentaje) if self.porcentaje else "", # PORCENTAJE
            str(self.subtotal) if self.subtotal else "",   # SUBTOTAL
            str(self.igv) if self.igv else "",            # IGV
            str(self.total) if self.total else "",         # TOTAL
            str(self.tasa_igv) if self.tasa_igv else "",   # TASAIGV
            str(self.imp_bruto) if self.imp_bruto is not None else "",  # IMPBRUTO
            str(self.aporte_codemu) if self.aporte_codemu is not None else "",  # APORCODEMU
            str(self.fondo_comun) if self.fondo_comun is not None else "",  # FONDOCOMUN
            str(self.honorario) if self.honorario is not None else "",  # HONORARIO
            str(self.impuesto_renta) if self.impuesto_renta is not None else "",  # IMPUESRENTA
            str(self.neto_honorario) if self.neto_honorario is not None else "",  # NETOHONORA
            str(self.renta_cip) if self.renta_cip is not None else "",  # RENTACIP
            str(self.dscto) if self.dscto is not None else "",  # DSCTO
            str(self.retencion) if self.retencion is not None else "",  # RETENCION
            self.delegado,          # DELEGADO
            self.cip,               # CIP
            str(self.categoria_raw) if self.categoria_raw is not None else "",  # CATEGORIA
            self.categoria_mapped or "",  # CATEGORIA_MAPPED
            self.categoria_status,  # CATEGORIA_STATUS
            self.pendientes,        # PENDIENTES
            self.pagadas,           # PAGADAS
            self.realizadas,        # REALIZADAS
            self.diferencia,        # DIFERENCIA
            self.nro_factura or "", # NROFACTURA
            self.fe_factura.isoformat() if self.fe_factura else "",  # FECOMPRO
            self.fecha_pres.isoformat() if self.fecha_pres else "",  # FECHAPRES
            self.fecha_revi.isoformat() if self.fecha_revi else "", # FECHAREVI
            self.nro_orden,         # NROORDEN
            self.dictamen,          # DICTAMEN
            self.usuario,           # USUARIO
            str(self.cantidad_visitas) if self.cantidad_visitas is not None else "",  # cantidad_visitas
            self.visitas_status,    # VISITAS_STATUS
            self.documento_tipo,    # TIPO_DOCUMENTO
            self.documento_numero,  # NUMERO_DOCUMENTO
            self.delegado_nombre,  # DELEGADO_NOMBRE
            self.modo_calculo,     # MODO_CALCULO
            self.rechazo_motivo,   # RECHAZO_MOTIVO
            ", ".join(self.anomalies) if self.anomalies else "",  # ANOMALIES
            # Batch 3b: NROREV correction fields
            str(self.nrorev) if self.nrorev is not None else "",  # NROREV
            str(self.tasa) if self.tasa is not None else "",       # TASA
            str(self.porcenfina) if self.porcenfina is not None else "",  # PORCENFINA
            self.nrorev_status,     # NROREV_STATUS
            str(self.subtotal_unitario_legacy) if self.subtotal_unitario_legacy is not None else "",  # SUBTOTAL_UNITARIO_LEGACY
            str(self.total_unitario_legacy) if self.total_unitario_legacy is not None else "",        # TOTAL_UNITARIO_LEGACY
            str(self.subtotal_unitario_recalc_legacy) if self.subtotal_unitario_recalc_legacy is not None else "",  # SUBTOTAL_UNITARIO_RECALC
            str(self.total_unitario_recalc_legacy) if self.total_unitario_recalc_legacy is not None else "",          # TOTAL_UNITARIO_RECALC
            str(self.diff_subtotal_unitario_legacy) if self.diff_subtotal_unitario_legacy is not None else "",      # DIFF_SUBTOTAL_UNITARIO
            str(self.diff_total_unitario_legacy) if self.diff_total_unitario_legacy is not None else "",            # DIFF_TOTAL_UNITARIO
            self.validation_status,  # VALIDATION_STATUS
            # Batch 3c: UIT implied columns
            str(self.uit_implicita) if self.uit_implicita is not None else "",        # UIT_IMPLICITA
            self.uit_implicita_status,  # UIT_IMPLICITA_STATUS
            # Batch 3d: UIT validation human-readable detail
            self.uit_validacion_detalle,  # UIT_VALIDACION_DETALLE
        ]


def _parse_row(fields: list, row_idx: int) -> tuple[ParsedRow, str]:
    """
    Parse a raw TSV row (list of string values) into a ParsedRow.

    Returns (parsed_row, rechazo_motivo). rechazo_motivo is non-empty when the
    row should be rejected based on parse-time validation (not diff/umbral).

    Batch 3 does NOT reject CATEGORIA=0 or diff-high rows — it records them
    as anomalies but continues. Rejection reason is set for structural issues
    like empty DPTOPRDI or unparseable DELEGADO.
    """
    row = ParsedRow()
    row.row_index = row_idx
    row.raw = fields
    rechazo: list[str] = []

    def col(n: int, default=None):
        return fields[n] if len(fields) > n else default

    # ── ID ──────────────────────────────────────────────────────────────────
    row.id_val = _int(col(_COL_ID))

    # ── NRO ─────────────────────────────────────────────────────────────────
    row.nro = _int(col(_COL_NRO))

    # ── NROEXPDTE ───────────────────────────────────────────────────────────
    raw_expdte = col(_COL_NROEXPDTE)
    if raw_expdte:
        row.nroexpdte = str(raw_expdte).strip()
        if row.nroexpdte.upper() in ("NULL", ""):
            row.nroexpdte = None

    # ── CODPAGO (municipalidad legacy code) ──────────────────────────────────
    row.codpago = str(col(_COL_CODPAGO) or "").strip().upper()
    if row.codpago in ("NULL", ""):
        row.codpago = ""

    # ── DPTOPRDI (distrito/provincia) ────────────────────────────────────────
    row.dptoprdri = str(col(_COL_DPTOPRDI) or "").strip()
    if not row.dptoprdri or row.dptoprdri.upper() in ("NULL", ""):
        row.dptoprdri = ""
        rechazo.append("DPTOPRDI vacío (distrito requerido)")

    # ── DIRECCION ────────────────────────────────────────────────────────────
    row.direccion = str(col(_COL_DIRECCION) or "").strip()
    if row.direccion.upper() in ("NULL", ""):
        row.direccion = ""

    # ── ENTIDAD (NOMBRE, RAZONSOCIAL, RUC, DNI) ───────────────────────────────
    row.nombre = str(col(_COL_NOMBRE) or "").strip()
    row.razon_social = str(col(_COL_RAZONSOCIAL) or "").strip()
    row.ruc = str(col(_COL_RUC) or "").strip()
    row.dni = str(col(_COL_DNI) or "").strip()
    if row.nombre.upper() in ("NULL", ""):
        row.nombre = ""
    if row.razon_social.upper() in ("NULL", ""):
        row.razon_social = ""
    if row.ruc.upper() in ("NULL", ""):
        row.ruc = ""
    if row.dni.upper() in ("NULL", ""):
        row.dni = ""

    row.documento_tipo, row.documento_numero = _resolve_tipo_documento(
        col(_COL_DNI), col(_COL_RUC)
    )

    # ── FECHA ────────────────────────────────────────────────────────────────
    try:
        row.fecha = _parse_fecha(col(_COL_FECHA))
    except ValueError as exc:
        row.anomalies.append(f"FECHA inválida: {exc}")
        row.fecha = None

    # ── UIT ──────────────────────────────────────────────────────────────────
    row.uit = _dec(col(_COL_UIT))

    # ── PORCENTAJE (unit total with IGV — informational in batch 3b) ────────
    row.porcentaje = _dec(col(_COL_PORCENTAJE))

    # ── NROREV (cantidad de revisiones/visitas cobradas — batch 3b) ─────────
    row.nrorev = _int(col(_COL_NROREV))

    # ── TASA (effective UIT percentage for subtotal calculation) ───────────
    row.tasa = _dec(col(_COL_TASA))

    # ── PORCENFINA (nominal/rounded rate — informational only) ────────────────
    row.porcenfina = _dec(col(_COL_PORCENFINA))

    # ── SUBTOTAL / IGV / TOTAL ───────────────────────────────────────────────
    row.subtotal = _dec(col(_COL_SUBTOTAL))
    row.igv = _dec(col(_COL_IGV))
    row.total = _dec(col(_COL_TOTAL))
    row.tasa_igv = _dec(col(_COL_TASAIGV))
    row.imp_bruto = _dec(col(_COL_IMPBRUTO))
    row.aporte_codemu = _dec(col(_COL_APORCODEMU))
    row.fondo_comun = _dec(col(_COL_FONDOCOMUN))
    row.honorario = _dec(col(_COL_HONORARIO))
    row.impuesto_renta = _dec(col(_COL_IMPUESRENTA))
    row.neto_honorario = _dec(col(_COL_NETOHONORA))
    row.renta_cip = _dec(col(_COL_RENTACIP))
    row.dscto = _dec(col(_COL_DSCTO))
    row.retencion = _dec(col(_COL_RETENCION))

    # ── DELEGADO + CIP ───────────────────────────────────────────────────────
    raw_delegado = col(_COL_DELEGADO)
    row.delegado = str(raw_delegado).strip() if raw_delegado else ""
    if row.delegado.upper() in ("NULL", ""):
        row.delegado = ""

    raw_cip = col(_COL_CIP)
    row.cip = _int(raw_cip)

    if row.delegado:
        cip_from_delegado, nombre_from_delegado = _parse_delegado_io(raw_delegado)
        row.delegado_nombre = nombre_from_delegado or ""
        if cip_from_delegado is not None:
            # Prefer CIP extracted from DELEGADO over raw CIP column
            row.cip = cip_from_delegado
        elif row.cip is None:
            row.anomalies.append("DELEGADO presente pero CIP no extraíble")
    else:
        row.delegado_nombre = ""
        if raw_delegado:
            rechazo.append("DELEGADO presente pero no parseable")
        else:
            rechazo.append("DELEGADO vacío")

    # ── CATEGORIA ────────────────────────────────────────────────────────────
    row.categoria_raw = _int(col(_COL_CATEGORIA))
    row.categoria_mapped, row.categoria_status = _map_categoria_io(col(_COL_CATEGORIA))

    # ── Visitas columns ───────────────────────────────────────────────────────
    row.pendientes = _int(col(_COL_PENDIENTES), 0) or 0
    row.pagadas = _int(col(_COL_PAGADAS), 0) or 0
    row.realizadas = _int(col(_COL_REALIZADAS), 0) or 0
    row.diferencia = _int(col(_COL_DIFERENCIA), 0) or 0

    # ── Derived: cantidad_visitas from NROREV (batch 3b correction) ───────────
    row.cantidad_visitas, row.visitas_status = _derive_cantidad_visitas(row.nrorev)

    # ── Batch 3b: Legacy unitario validation ─────────────────────────────────
    # Compute legacy unitario values from source amounts / NROREV
    if (
        row.nrorev is not None
        and row.nrorev > 0
        and row.subtotal is not None
        and row.total is not None
    ):
        try:
            row.subtotal_unitario_legacy = row.subtotal / Decimal(row.nrorev)
            row.total_unitario_legacy = row.total / Decimal(row.nrorev)
        except (InvalidOperation, ZeroDivisionError, TypeError):
            row.subtotal_unitario_legacy = None
            row.total_unitario_legacy = None

    # Recalculated unitario from TASA * UIT
    if row.tasa is not None and row.tasa > 0 and row.uit is not None:
        try:
            row.subtotal_unitario_recalc_legacy = row.tasa * row.uit
        except (InvalidOperation, TypeError):
            row.subtotal_unitario_recalc_legacy = None
    else:
        row.subtotal_unitario_recalc_legacy = None

    if row.subtotal_unitario_recalc_legacy is not None and row.tasa_igv is not None:
        try:
            row.total_unitario_recalc_legacy = row.subtotal_unitario_recalc_legacy * (
                Decimal("1") + row.tasa_igv / Decimal("100")
            )
        except (InvalidOperation, TypeError):
            row.total_unitario_recalc_legacy = None
    else:
        row.total_unitario_recalc_legacy = None

    # Diff between legacy source and recalculated
    if row.subtotal_unitario_legacy is not None and row.subtotal_unitario_recalc_legacy is not None:
        try:
            row.diff_subtotal_unitario_legacy = abs(
                row.subtotal_unitario_legacy - row.subtotal_unitario_recalc_legacy
            )
        except InvalidOperation:
            row.diff_subtotal_unitario_legacy = None
    else:
        row.diff_subtotal_unitario_legacy = None

    if row.total_unitario_legacy is not None and row.total_unitario_recalc_legacy is not None:
        try:
            row.diff_total_unitario_legacy = abs(
                row.total_unitario_legacy - row.total_unitario_recalc_legacy
            )
        except InvalidOperation:
            row.diff_total_unitario_legacy = None
    else:
        row.diff_total_unitario_legacy = None

    # ── Batch 3c: UIT implied computation ────────────────────────────────────
    # uit_implicita = (SUBTOTAL / NROREV) / TASA — inverts: SUBTOTAL = NROREV * TASA * UIT
    row.uit_implicita = _compute_uit_implicita(row.subtotal, row.nrorev, row.tasa)

    # Determine uit_implicita_status by comparing against archivo UIT
    if row.uit_implicita is None or row.subtotal_unitario_recalc_legacy is None:
        row.uit_implicita_status = "SIN_DATOS"
    else:
        uit_archivo_val = row.uit  # UIT from source file column
        uit_implicita_int = int(round(row.uit_implicita))

        if uit_archivo_val is not None:
            archivo_int = int(uit_archivo_val)
            if uit_implicita_int == archivo_int:
                row.uit_implicita_status = "OK_IGUAL_ARCHIVO"
            else:
                row.uit_implicita_status = "DIF_UIT"
        else:
            row.uit_implicita_status = "SIN_UIT_ARCHIVO"

    # Batch 3d: UIT validation human-readable detail
    row.uit_validacion_detalle = _build_uit_validacion_detalle(
        row.uit, row.uit_implicita, row.uit_implicita_status
    )

    # Validation status (batch 3c):
    # When diff exists but UIT-implicita matches archivo UIT → OK_UIT_IMPLICITA
    if row.subtotal_unitario_recalc_legacy is None:
        row.validation_status = "SIN_DATOS"
    elif (
        row.diff_subtotal_unitario_legacy is not None
        and row.diff_total_unitario_legacy is not None
    ):
        if row.diff_subtotal_unitario_legacy > Decimal("0.01"):
            if row.uit_implicita_status == "OK_IGUAL_ARCHIVO":
                row.validation_status = "OK_UIT_IMPLICITA"
            else:
                row.validation_status = "DIF_SUBTOTAL"
        elif row.diff_total_unitario_legacy > Decimal("0.01"):
            if row.uit_implicita_status == "OK_IGUAL_ARCHIVO":
                row.validation_status = "OK_UIT_IMPLICITA"
            else:
                row.validation_status = "DIF_TOTAL"
        else:
            row.validation_status = "OK"
    else:
        row.validation_status = "SIN_DATOS"

    # Report NROREV anomaly when visits could not be determined from NROREV
    if row.visitas_status in ("missing", "non_positive"):
        row.anomalies.append(f"NROREV {row.visitas_status}: cantidad_visitas no determinable")

    # ── NROFACTURA + FECOMPRO ────────────────────────────────────────────────
    nro_fac_raw = col(_COL_NROFACTURA)
    serie, numero, raw_fac = _parse_nrofactura(nro_fac_raw)
    row.nro_factura = f"{serie}-{numero}" if serie or numero else None

    try:
        row.fe_factura = _parse_fecha(col(_COL_FECOMPRO))
    except ValueError:
        row.fe_factura = None

    # ── FECHAPRES / FECHAREVI ─────────────────────────────────────────────────
    try:
        row.fecha_pres = _parse_fecha(col(_COL_FECHAPRES))
    except ValueError:
        row.fecha_pres = None

    try:
        row.fecha_revi = _parse_fecha(col(_COL_FECHAREVI))
    except ValueError:
        row.fecha_revi = None

    # ── NROORDEN ─────────────────────────────────────────────────────────────
    row.nro_orden = _int(col(_COL_NROORDEN), 0) or 0

    # ── DICTAMEN ─────────────────────────────────────────────────────────────
    row.dictamen = str(col(_COL_DICTAMEN) or "").strip()
    if row.dictamen.upper() in ("NULL", ""):
        row.dictamen = ""

    # ── USUARIO ──────────────────────────────────────────────────────────────
    row.usuario = str(col(_COL_USUARIO) or "").strip()
    if row.usuario.upper() in ("NULL", ""):
        row.usuario = ""

    # ──modo_calculo (proposed) ───────────────────────────────────────────────
    if row.categoria_status == "null_tariff":
        row.modo_calculo = "MANUAL"
    elif row.categoria_status == "anomaly":
        row.modo_calculo = "ANOMALY"
    else:
        row.modo_calculo = "TARIFA"

    # ── Encode issues in text fields ─────────────────────────────────────────
    for field_name in ("nombre", "razon_social", "direccion", "delegado", "delegado_nombre"):
        val = getattr(row, field_name, "")
        if val and "�" in val:
            row.anomalies.append("Encoding issue en texto")

    # ── Structural rechazo ─────────────────────────────────────────────────────
    row.rechazo_motivo = "; ".join(rechazo)
    return row, row.rechazo_motivo


# ── Batch 4: Model imports for DB writes ──────────────────────────────────────
from datetime import date as date_type, datetime, time

from django.db import models, transaction
from django.utils import timezone

from modules.entidades.domain.models.entidad import Entidad
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.entidades.domain.models.ubigeo import UbigeoDistrito
from modules.entidades.domain.models.contacto import Contacto
from modules.finanzas.domain.models.detalle_honorario_inspector import (
    DetalleHonorarioInspector,
)
from modules.liquidaciones.domain.constants import (
    ModoCalculoLiquidacion,
    TipoLiquidacion as TipoLiquidacionConstants,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
    LiquidacionContacto,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    InspectorOperacion,
    LiquidacionInspector,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)
from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import (
    PerfilIngenieroCoreService,
)
# ── Report generation helpers ──────────────────────────────────────────────────

def _build_rechazo_headers() -> list[str]:
    return [
        "FILA", "EXPEDIENTE", "MOTIVO", "CATEGORIA_SOURCE",
        "CATEGORIA_TARGET", "TARIFA_ID", "SUBTOTAL_SOURCE",
        "SUBTOTAL_RECALC", "DIF", "MODO_CALCULO", "SUBIDO",
    ]


def _build_detailed_headers() -> list[str]:
    """Headers for the detailed report covering all source + parsed fields."""
    return [
        "FILA", "ID", "NRO", "NROEXPDTE", "CODPAGO", "DPTOPRDI", "DIRECCION",
        "NOMBRE", "RAZONSOCIAL", "RUC", "DNI",
        "FECHA", "UIT", "PORCENTAJE", "SUBTOTAL", "IGV", "TOTAL", "TASAIGV",
        "IMPBRUTO", "APORCODEMU", "FONDOCOMUN", "HONORARIO", "IMPUESRENTA",
        "NETOHONORA", "RENTACIP", "DSCTO", "RETENCION",
        "DELEGADO", "CIP",
        "CATEGORIA", "CATEGORIA_MAPPED", "CATEGORIA_STATUS",
        "PENDIENTES", "PAGADAS", "REALIZADAS", "DIFERENCIA",
        "NROFACTURA", "FECOMPRO", "FECHAPRES", "FECHAREVI", "NROORDEN",
        "DICTAMEN", "USUARIO",
        "cantidad_visitas", "VISITAS_STATUS",
        "TIPO_DOCUMENTO", "NUMERO_DOCUMENTO",
        "DELEGADO_NOMBRE", "MODO_CALCULO", "RECHAZO_MOTIVO", "ANOMALIES",
        # Batch 3b: NROREV correction fields
        "NROREV", "TASA", "PORCENFINA", "NROREV_STATUS",
        "SUBTOTAL_UNITARIO_LEGACY", "TOTAL_UNITARIO_LEGACY",
        "SUBTOTAL_UNITARIO_RECALC", "TOTAL_UNITARIO_RECALC",
        "DIFF_SUBTOTAL_UNITARIO", "DIFF_TOTAL_UNITARIO",
        "VALIDATION_STATUS",
        # Batch 3c: UIT implied headers
        "UIT_IMPLICITA", "UIT_IMPLICITA_STATUS",
        # Batch 3d: UIT validation human-readable detail
        "UIT_VALIDACION_DETALLE",
    ]


# ── Batch 4: DB Write Helpers ─────────────────────────────────────────────────

def _es_diff_alta(
    row: "ParsedRow",
    umbral: Decimal,
    tarifario: Decimal | None,
) -> bool:
    """Check if the row's diff exceeds threshold.

    Args:
        row: ParsedRow with recalculated values
        umbral: threshold in soles
        tarifario: recalculated subtotal (from tariff * visitas)

    Returns:
        True if abs(diff) > umbral
    """
    if tarifario is None:
        return False
    diff = abs(row.subtotal - tarifario)
    return diff > umbral


def _resolve_entidad_municipalidad_proyecto(
    row: "ParsedRow",
) -> tuple[Entidad | None, Municipalidad, Proyecto]:
    """Resolve/create Entidad, Municipalidad and Proyecto using real model fields."""
    _, distrito_nombre = _parse_dptoprdri(row.dptoprdri)
    municipalidad = None

    if row.codpago:
        municipalidad = Municipalidad.objects.filter(codigo=row.codpago).first()

    if municipalidad is None and distrito_nombre:
        municipalidad = Municipalidad.objects.filter(nombre__iexact=distrito_nombre).first()

    if municipalidad is None:
        lookup = f"CODPAGO={row.codpago or '-'} DPTOPRDI={distrito_nombre or '-'}"
        raise ValueError(f"Fila {row.row_index}: municipalidad no encontrada: {lookup}")

    distrito = municipalidad.distrito or (
        UbigeoDistrito.objects.filter(nombre__iexact=distrito_nombre)
        .select_related("provincia", "provincia__departamento")
        .first()
    )

    entidad: Entidad | None = None
    if row.documento_tipo in {"RUC", "DNI"} and row.documento_numero:
        numero_documento = row.documento_numero[:11]
        entidad = Entidad.objects.filter(numero_documento=numero_documento).first()
        if entidad is None:
            entidad = Entidad.objects.create(
                tipo_documento=row.documento_tipo,
                numero_documento=numero_documento,
            )

    razon_social = row.razon_social or row.nombre or row.documento_numero or "Legacy IO"
    nombre_propietario = row.nombre or row.razon_social or razon_social
    proyecto = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario=nombre_propietario[:255],
        entidad_razon_social=razon_social[:255],
        entidad_tipo_documento=(row.documento_tipo if row.documento_tipo != "SIN_DOCUMENTO" else None),
        entidad_numero_documento=(row.documento_numero if row.documento_tipo != "SIN_DOCUMENTO" else None),
        direccion=(row.direccion or None),
        distrito=distrito,
        descripcion=f"Legacy IO fila {row.row_index} ID {row.id_val or ''}".strip(),
    )

    return entidad, municipalidad, proyecto


def _lookup_tarifa_categoria_visitas(
    row: "ParsedRow",
    fecha_liquidacion: date_type,
) -> TarifaPorCategoriaVisitas | None:
    """Lookup a TarifaPorCategoriaVisitas for the row's CATEGORIA and date.

    Returns None for CATEGORIA=0 (manual/no-tariff) or when no tariff is found.
    """
    if row.categoria_raw in (None, 0):
        # CATEGORIA=0 means no tariff — MANUAL liquidation
        return None

    # Batch 4 keeps import safe: tariff matching is best-effort and never blocks
    # legacy writes. If an exact category/rate match is not found, row imports as MANUAL.
    categoria_candidates = [row.categoria_mapped, str(row.categoria_raw)]
    qs = TarifaPorCategoriaVisitas.objects.select_related("tarifa_base").filter(
        tarifa_base__tipo_liquidacion__codigo=TipoLiquidacionConstants.INSPECCION_OBRA,
        categoria_visitas__in=[c for c in categoria_candidates if c],
    )
    if row.fecha is not None:
        qs = qs.filter(tarifa_base__periodo_inicio__lte=row.fecha).filter(
            models.Q(tarifa_base__periodo_fin__isnull=True)
            | models.Q(tarifa_base__periodo_fin__gte=row.fecha)
        )
    if row.tasa is not None:
        qs = qs.filter(porcentaje_uit=row.tasa)
    return qs.order_by("-tarifa_base__periodo_inicio").first()


def _get_or_create_io_especialidad_revision() -> EspecialidadRevision:
    """Return fallback specialty for standalone legacy IO inspector details."""
    especialidad, _ = EspecialidadRevision.objects.get_or_create(
        slug="inspeccion-obra",
        defaults={"nombre": "Inspección de Obra"},
    )
    return especialidad


def _resolve_inspector_operacion_for_legacy_io(
    inspector: Inspector,
    row: "ParsedRow",
) -> InspectorOperacion:
    """Find an existing inspector operation or create an IO fallback operation."""
    preferred_codes = [
        TipoLiquidacionConstants.EDIFICACION,
        TipoLiquidacionConstants.HABILITACION_URBANA,
        TipoLiquidacionConstants.INSPECCION_OBRA,
    ]
    existing = (
        InspectorOperacion.objects.filter(
            inspector=inspector,
            tipo_liquidacion__codigo__in=preferred_codes,
        )
        .select_related("especialidad_revision", "tipo_liquidacion")
        .order_by("tipo_liquidacion__codigo", "categoria")
        .first()
    )
    if existing is not None:
        return existing

    tipo_io = TipoLiquidacion.objects.get(codigo=TipoLiquidacionConstants.INSPECCION_OBRA)
    categoria = row.categoria_mapped if row.categoria_mapped in {"1", "2", "3", "4"} else "1"
    especialidad = _get_or_create_io_especialidad_revision()
    existing_io = InspectorOperacion.objects.filter(
        inspector=inspector,
        tipo_liquidacion=tipo_io,
        categoria=categoria,
    ).first()
    if existing_io is not None:
        return existing_io
    return InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_io,
        categoria=categoria,
        especialidad_revision=especialidad,
    )


def _resolve_perfil_cip(
    cip: int | None,
    perfil_cache: dict[str, tuple[object | None, str]],
) -> tuple[object | None, str]:
    """
    Resolve PerfilIngeniero by CIP, using cache to avoid duplicate lookups.

    Returns (perfil, status) where status is the CIP resolution status
    (e.g., "SIN_COLEGIADO", "ERROR_CIP", "YA_EXISTE", etc.).
    """
    if cip is None:
        return None, "SIN_CIP"
    cip_key = _normalize_legacy_cip(cip)
    if cip_key in perfil_cache:
        return perfil_cache[cip_key]
    perfil, perfil_status = PerfilIngenieroCoreService().hydrate_perfil_from_cip(
        cip_key,
    )
    perfil_cache[cip_key] = (perfil, perfil_status)
    return perfil, perfil_status


def _normalize_legacy_cip(cip: int | str) -> str:
    digits = "".join(ch for ch in str(cip or "").strip() if ch.isdigit())
    if not digits:
        return ""
    return digits.zfill(6)


def _create_fallback_perfil_ingeniero(cip: int) -> PerfilIngeniero:
    """
    Create a temporary/permanent fallback PerfilIngeniero for legacy rows where
    the CIP lookup returned SIN_COLEGIADO (404) or ERROR_CIP.

    Fallback naming uses the CIP value itself so the record is searchable and
    remappable later without inventing a real identity.

    Args:
        cip: The CIP number from the source row.

    Returns:
        PerfilIngeniero instance (created or pre-existing).
    """
    normalized_cip = _normalize_legacy_cip(cip)
    perfil, created = PerfilIngeniero.objects.get_or_create(
        cip=normalized_cip,
        defaults={
            "nombres": f"CIP {normalized_cip}",
            "apellido_paterno": "CIP",
            "apellido_materno": normalized_cip,
        },
    )
    return perfil


def _legacy_io_has_rh_detail(liquidacion_general: LiquidacionGeneral) -> bool:
    return LiquidacionPorCategoriaVisitas.objects.filter(
        liquidacion_general=liquidacion_general,
        detalles_honorario__isnull=False,
    ).exists()


def _create_legacy_inspector_detail(
    command,
    row: "ParsedRow",
    liquidacion_visitas: LiquidacionPorCategoriaVisitas,
    perfil_cache: dict[str, tuple[object | None, str]],
    fallback_on_failure: bool = False,
) -> tuple[bool, str, bool]:
    """Create/reuse inspector and attach it to the legacy IO visit detail.

    Idempotent: if the DetalleHonorarioInspector already exists, update missing
    fields so re-runs repair incomplete data.

    Args:
        command: BaseCommand instance for logging.
        row: ParsedRow with source data.
        liquidacion_visitas: The LiquidacionPorCategoriaVisitas to attach to.
        perfil_cache: Shared cache of CIP -> (PerfilIngeniero, status).
        fallback_on_failure: If True, create a temporary/permanent fallback
            PerfilIngeniero when CIP lookup fails (SIN_COLEGIADO or ERROR_CIP).
            If False (default), skip inspector creation on lookup failure.

    Returns:
        (success, perfil_status, was_created) where was_created is True if
        a new DetalleHonorarioInspector was created.
    """
    if not row.delegado or row.cip is None:
        return False, "SIN_CIP", False

    perfil, perfil_status = _resolve_perfil_cip(row.cip, perfil_cache)
    if perfil is None:
        if fallback_on_failure and perfil_status in ("SIN_COLEGIADO", "ERROR_CIP"):
            # Fallback: create temporary/permanent profile from CIP for auditability
            perfil = _create_fallback_perfil_ingeniero(row.cip)
            perfil_status = f"FALLBACK_{perfil_status}"
            perfil_cache[_normalize_legacy_cip(row.cip)] = (perfil, perfil_status)
            command._log_warning(
                f"  Fila {row.row_index}: CIP {row.cip} no resuelto ({perfil_status}); "
                f"creando perfil fallback CIP {row.cip}."
            )
        else:
            command._log_warning(
                f"  Fila {row.row_index}: no se pudo resolver PerfilIngeniero para CIP {row.cip} ({perfil_status}); "
                "saltando inspector."
            )
            return False, perfil_status, False

    inspector, _ = Inspector.objects.get_or_create(perfil_ingeniero=perfil)
    inspector_operacion = _resolve_inspector_operacion_for_legacy_io(inspector, row)
    LiquidacionInspector.objects.get_or_create(
        liquidacion=liquidacion_visitas,
        inspector=inspector,
        defaults={
            "inspector_operacion": inspector_operacion,
            "especialidad_revision": inspector_operacion.especialidad_revision,
            "fecha_presentacion": row.fecha_pres,
            "fecha_revision": row.fecha_revi,
        },
    )

    # ── Compute all DetalleHonorarioInspector fields ──────────────────────────
    inspecciones_liquidadas = int(row.nrorev or 0)
    inspecciones_programadas = int(row.nrorev or 0)
    costo_por_inspeccion = row.subtotal_unitario_legacy or Decimal("0.00")
    importe_bruto = row.imp_bruto if row.imp_bruto is not None else (row.subtotal or Decimal("0.00"))
    monto_contribuido = row.subtotal or importe_bruto
    legacy_deducciones = sum(
        value or Decimal("0.00")
        for value in (
            row.aporte_codemu,
            row.fondo_comun,
            row.impuesto_renta,
            row.renta_cip,
            row.dscto,
            row.retencion,
        )
    )
    honorarios = row.neto_honorario if row.neto_honorario is not None else row.honorario
    if honorarios is None:
        honorarios = importe_bruto - legacy_deducciones
    descuento = importe_bruto - honorarios

    # tasa_descuento = descuento / imp_bruto when IMPBRUTO > 0
    tasa_descuento: Decimal | None = None
    if importe_bruto and importe_bruto > 0:
        try:
            tasa_descuento = descuento / importe_bruto
        except (InvalidOperation, ZeroDivisionError, TypeError):
            tasa_descuento = None

    # inspecciones_pagadas_hasta_mes_anterior: use PAGADAS when non-null in source
    inspecciones_pagadas: int | None = None
    pagadas_raw = row.pagadas  # _int already applied; 0 means absent
    if pagadas_raw is not None and pagadas_raw != 0:
        inspecciones_pagadas = int(pagadas_raw)

    # saldo_restante: use DIFERENCIA when non-null in source
    saldo_restante: Decimal | None = None
    diferencia_raw = row.diferencia
    if diferencia_raw is not None and diferencia_raw != 0:
        saldo_restante = Decimal(int(diferencia_raw))

    # ── Upsert DetalleHonorarioInspector (idempotent) ─────────────────────────
    detalle = DetalleHonorarioInspector.objects.filter(
        liquidacion_por_categoria_visitas=liquidacion_visitas,
    ).first()

    if detalle is None:
        detalle = DetalleHonorarioInspector.objects.create(
            liquidacion_por_categoria_visitas=liquidacion_visitas,
            recibo_mensual=None,
            inspecciones_liquidadas=inspecciones_liquidadas,
            inspecciones_programadas=inspecciones_programadas,
            costo_por_inspeccion=costo_por_inspeccion,
            monto_contribuido=monto_contribuido,
            sub_total=monto_contribuido,
            importe_bruto=importe_bruto,
            descuento=descuento,
            honorarios=honorarios,
            tasa_descuento=tasa_descuento,
            inspecciones_pagadas_hasta_mes_anterior=inspecciones_pagadas,
            saldo_restante=saldo_restante,
        )
        detalle_created = True
    else:
        # Update missing/outdated fields so re-runs repair incomplete data
        detalle_updated = False
        fields_to_update = {
            "inspecciones_liquidadas": inspecciones_liquidadas,
            "inspecciones_programadas": inspecciones_programadas,
            "costo_por_inspeccion": costo_por_inspeccion,
            "monto_contribuido": monto_contribuido,
            "sub_total": monto_contribuido,
            "importe_bruto": importe_bruto,
            "descuento": descuento,
            "honorarios": honorarios,
            "tasa_descuento": tasa_descuento,
        }
        for field, value in fields_to_update.items():
            if getattr(detalle, field, None) is None and value is not None:
                setattr(detalle, field, value)
                detalle_updated = True
        # Only update inspecciones_pagadas/saldo_restante if source is non-null
        if inspecciones_pagadas is not None and detalle.inspecciones_pagadas_hasta_mes_anterior is None:
            detalle.inspecciones_pagadas_hasta_mes_anterior = inspecciones_pagadas
            detalle_updated = True
        if saldo_restante is not None and detalle.saldo_restante is None:
            detalle.saldo_restante = saldo_restante
            detalle_updated = True
        if detalle_updated:
            detalle.save()
        detalle_created = False

    return True, perfil_status, detalle_created


def _create_legacy_liquidations(
    command,
    parsed_rows: list["ParsedRow"],
    umbral_dif: Decimal,
    rechazar_dif_alta: bool,
    rechazar_sin_tarifa: bool,
    reporte_writer,
    rejected_rows: list[dict],
    jw=None,
    joined_csv_file=None,
    ws_joined=None,
) -> dict:
    """Create DB records for valid parsed rows.

    Args:
        command: BaseCommand instance (for logging)
        parsed_rows: List of ParsedRow with full validation_status set
        umbral_dif: Threshold for diff rejection
        rechazar_dif_alta: Reject rows where diff > umbral
        rechazar_sin_tarifa: Reject rows with no matching tariff (CATEGORIA=0 or lookup fail)
        reporte_writer: csv.writer for rechazo INGESTA CSV
        rejected_rows: list to accumulate rejection dicts (for post-loop clean report)
        jw: csv.writer for joined rechazo CSV (writes live on rejection)
        ws_joined: openpyxl worksheet for joined rechazo XLSX (writes live on rejection)

    Returns:
        Dict with counters: created, rejected, errors
    """
    counters = {
        "created": 0,
        "liquidaciones_nuevas": 0,
        "liquidaciones_existentes": 0,
        "rechazadas_diff_alta": 0,
        "rechazadas_sin_tarifa": 0,
        "rechazadas_sin_datos": 0,
        "rechazadas_cip_no_resuelto": 0,
        "errors": 0,
        "error_details": [],
        "inspectores_asociados": 0,
        "inspectores_saltados": 0,
        "fallback_creados": 0,
        "rh_detalles_creados": 0,
        "rh_detalles_actualizados": 0,
        "comprobantes_creados": 0,
        "comprobantes_actualizados": 0,
        "comprobantes_omitidos": 0,
        "contactos_creados": 0,
        "contactos_actualizados": 0,
        "contactos_omitidos": 0,
    }
    perfil_cache: dict[str, tuple[object | None, str]] = {}

    # Filter rows that should be rejected structurally (already set by _parse_row)
    rows_to_process: list[ParsedRow] = []
    for row in parsed_rows:
        # Structural rechazo (from _parse_row)
        if row.rechazo_motivo:
            continue

        if row.subtotal is None or row.total is None or row.nrorev is None or row.nrorev <= 0:
            counters["rechazadas_sin_datos"] += 1
            continue

        # Check CATEGORIA=0 / null_tariff
        if row.categoria_status == "null_tariff":
            if rechazar_sin_tarifa and row.existing_liquidacion_general is None:
                counters["rechazadas_sin_tarifa"] += 1
                continue
            # CATEGORIA=0 without --rechazar-sin-tarifa → MANUAL (no tariff)
            # Existing rows are still processed so re-runs can repair inspector/RH detail.
            rows_to_process.append(row)
            continue

        # Check diff rejection (only for rows with valid tariff lookup)
        if row.validation_status in ("DIF_SUBTOTAL", "DIF_TOTAL"):
            if rechazar_dif_alta and row.existing_liquidacion_general is None:
                counters["rechazadas_diff_alta"] += 1
                continue
            # Existing rows are still processed so re-runs can repair inspector/RH detail.
            rows_to_process.append(row)
            continue

        rows_to_process.append(row)

    # Process rows in a transaction
    for row in rows_to_process:
        try:
            with transaction.atomic():
                # Lookup tariff if not CATEGORIA=0
                fecha_liq = row.fecha or date_type.today()
                fecha_registro = timezone.make_aware(datetime.combine(fecha_liq, time.min))
                tarifa = _lookup_tarifa_categoria_visitas(row, fecha_liq)

                # Determine modo_calculo. Batch 4 imports diff/no-tariff rows as MANUAL unless rejected by flags.
                if row.categoria_status == "null_tariff" or tarifa is None or row.validation_status in {"DIF_SUBTOTAL", "DIF_TOTAL", "OK_UIT_IMPLICITA"}:
                    modo_calculo = ModoCalculoLiquidacion.MANUAL
                else:
                    modo_calculo = ModoCalculoLiquidacion.TARIFA

                # Determine if CIP lookup fallback should be applied.
                # Fallback applies only when source row has both delegado and cip,
                # and the lookup returns SIN_COLEGIADO (CIP 404) or ERROR_CIP.
                # For rows with no CIP/delegado, keep PARCIAL behavior (no fallback).
                pre_check_perfil, pre_check_status = _resolve_perfil_cip(row.cip, perfil_cache)
                use_fallback = (
                    row.delegado
                    and row.cip is not None
                    and pre_check_perfil is None
                    and pre_check_status in ("SIN_COLEGIADO", "ERROR_CIP")
                )

                # Build descripcion_legacy (include fallback marker when applicable)
                desc_parts = [
                    "IMPORT_LEGACY_IO",
                    f"FILA={row.row_index}",
                    f"ID={row.id_val or ''}",
                    f"NROEXPDTE={row.nroexpdte or ''}",
                    f"CODPAGO={row.codpago or ''}",
                    f"FECHA={row.fecha.isoformat() if row.fecha else ''}",
                    f"NROREV={row.nrorev or ''}",
                    f"CATEGORIA={row.categoria_raw if row.categoria_raw is not None else ''}",
                    f"UIT_ARCHIVO={row.uit or ''}",
                    f"UIT_IMPLICITA={row.uit_implicita or ''}",
                    f"UIT_VALIDACION_STATUS={row.uit_implicita_status}",
                    f"VALIDATION_STATUS={row.validation_status}",
                    f"SUBTOTAL_LEGACY={row.subtotal or ''}",
                    f"TOTAL_LEGACY={row.total or ''}",
                    f"MODO_IMPORTACION={modo_calculo}",
                ]
                if row.uit_validacion_detalle:
                    desc_parts.append(f"UIT_VALIDACION_DETALLE={row.uit_validacion_detalle}")
                if modo_calculo == ModoCalculoLiquidacion.MANUAL:
                    desc_parts.append("Importado como MANUAL por legacy/diff/sin tarifa")
                if use_fallback:
                    desc_parts.append(f"FALLBACK_CIP={row.cip} ({pre_check_status})")
                descripcion = "\n".join(desc_parts)

                if row.existing_liquidacion_general is not None:
                    lg = row.existing_liquidacion_general
                    counters["liquidaciones_existentes"] += 1
                else:
                    # Resolve entity/project/municipalidad
                    entidad, municipalidad, proyecto = _resolve_entidad_municipalidad_proyecto(row)

                    # Create LiquidacionGeneral
                    lg = LiquidacionGeneral.objects.create(
                        proyecto=proyecto,
                        municipalidad=municipalidad,
                        tipo_liquidacion=TipoLiquidacion.objects.get(codigo=TipoLiquidacionConstants.INSPECCION_OBRA),
                        expediente=row.nroexpdte or "",
                        numero_revision=1,
                        fecha_registro=fecha_registro,
                        sub_total=row.subtotal,
                        total=row.total or Decimal("0"),
                        modo_calculo=modo_calculo,
                        descripcion_legacy=descripcion,
                        observacion=f"Legacy IO import fila {row.row_index} ID {row.id_val or ''}".strip(),
                        denominacion_de_proyecto=row.nombre or row.razon_social or None,
                        legacy=True,
                    )

                    # Create LiquidacionInspeccionObra
                    # numero=row.id_val preserves the historical legacy ID from source CSV col 0.
                    # AutoNumeroModel.save() respects a non-None numero (no auto-increment).
                    LiquidacionInspeccionObra.objects.create(liquidacion=lg, numero=row.id_val)
                    counters["liquidaciones_nuevas"] += 1

                # Create LiquidacionPorCategoriaVisitas (one per row)
                liquidacion_visitas = LiquidacionPorCategoriaVisitas.objects.filter(
                    liquidacion_general=lg,
                ).first()
                if liquidacion_visitas is None:
                    liquidacion_visitas = LiquidacionPorCategoriaVisitas.objects.create(
                        liquidacion_general=lg,
                        cantidad_visitas=int(row.nrorev),
                        porcentaje_uit=(tarifa.porcentaje_uit if tarifa is not None and modo_calculo == ModoCalculoLiquidacion.TARIFA else None),
                        categoria=(tarifa.categoria_visitas if tarifa is not None and modo_calculo == ModoCalculoLiquidacion.TARIFA else row.categoria_mapped),
                        tarifa_aplicada=(tarifa if modo_calculo == ModoCalculoLiquidacion.TARIFA else None),
                    )

                inspector_created, inspector_status, detalle_created = _create_legacy_inspector_detail(
                    command=command,
                    row=row,
                    liquidacion_visitas=liquidacion_visitas,
                    perfil_cache=perfil_cache,
                    fallback_on_failure=use_fallback,
                )
                if inspector_created:
                    counters["inspectores_asociados"] += 1
                    if detalle_created:
                        counters["rh_detalles_creados"] += 1
                        command._log_success(
                            f"  Fila {row.row_index}: RH detalle inspector CREADO para numero {row.id_val or ''}"
                        )
                    else:
                        counters["rh_detalles_actualizados"] += 1
                        command._log(
                            f"  Fila {row.row_index}: RH detalle inspector ACTUALIZADO para numero {row.id_val or ''}"
                        )
                    if inspector_status.startswith("FALLBACK_"):
                        counters["fallback_creados"] += 1
                        reporte_writer.writerow([
                            row.row_index,
                            row.nroexpdte or "",
                            f"FALLBACK ({inspector_status})",
                            "CREADO",
                        ])
                else:
                    counters["inspectores_saltados"] += 1
                    if inspector_status == "SIN_CIP":
                        motivo = "Sin inspector"
                    else:
                        motivo = f"CIP no resuelto: {inspector_status}"
                    reporte_writer.writerow([
                        row.row_index,
                        row.nroexpdte or "",
                        motivo,
                        "PARCIAL",
                    ])

                # ── Upsert LiquidacionComprobante ───────────────────────────────
                # Parse TPERSONA / TDNI / TFONO for contacto upsert below
                nombres, apellidos = _parse_tpersona(
                    row.raw[_COL_TPERSONA] if len(row.raw) > _COL_TPERSONA else None
                )
                dni_telefono_raw = row.raw[_COL_TDNI] if len(row.raw) > _COL_TDNI else None
                telefono_raw = row.raw[_COL_TFONO] if len(row.raw) > _COL_TFONO else None
                dni_val = str(dni_telefono_raw).strip() if dni_telefono_raw and str(dni_telefono_raw).strip().upper() not in ("NULL", "") else None
                telefono_val = str(telefono_raw).strip() if telefono_raw and str(telefono_raw).strip().upper() not in ("NULL", "") else None

                comp, comp_status = _upsert_liquidacion_comprobante(
                    liquidacion=lg,
                    nro_factura_raw=row.nro_factura,
                    fe_compro=row.fe_factura,
                    total=row.total,
                    dry_run=command.dry_run,
                )
                if comp_status == "CREADO":
                    counters["comprobantes_creados"] += 1
                elif comp_status == "ACTUALIZADO":
                    counters["comprobantes_actualizados"] += 1
                elif comp_status == "OMITIDO":
                    counters["comprobantes_omitidos"] += 1

                # ── Upsert Contacto ─────────────────────────────────────────────
                contacto, contacto_status = _upsert_contacto(
                    liquidacion=lg,
                    nombres=nombres,
                    apellidos=apellidos,
                    dni=dni_val,
                    telefono=telefono_val,
                    dry_run=command.dry_run,
                )
                if contacto_status == "CREADO":
                    counters["contactos_creados"] += 1
                elif contacto_status == "ACTUALIZADO":
                    counters["contactos_actualizados"] += 1
                elif contacto_status == "OMITIDO":
                    counters["contactos_omitidos"] += 1

        except Exception as exc:
            counters["errors"] += 1
            counters["error_details"].append(f"Fila {row.row_index}: {exc}")
            command._log_error(f"  ERROR creando liquidación fila {row.row_index}: {exc}")
        else:
            counters["created"] += 1

    return counters


def _reset_legacy_io(command) -> int:
    """Delete all legacy IO liquidations created by this import.

    Returns:
        Number of LiquidacionGeneral records deleted.
    """
    legacy_lgs = LiquidacionGeneral.objects.filter(
        legacy=True,
        tipo_liquidacion__codigo=TipoLiquidacionConstants.INSPECCION_OBRA,
        descripcion_legacy__startswith="IMPORT_LEGACY_IO",
    )
    count_lg = legacy_lgs.count()

    # DetalleHonorarioInspector protects LiquidacionPorCategoriaVisitas, so it
    # must be removed explicitly before deleting the legacy liquidations.
    detalle_count, _ = DetalleHonorarioInspector.objects.filter(
        liquidacion_por_categoria_visitas__liquidacion_general__in=legacy_lgs,
        recibo_mensual__isnull=True,
    ).delete()
    if detalle_count:
        command._log(f"  Eliminados {detalle_count} detalles RH inspector legacy IO.")

    legacy_lgs.delete()
    command._log(f"  Eliminadas {count_lg} liquidaciones legacy IO.")
    return count_lg


class Command(BaseCommand):
    help = "Import legacy Inspección de Obra (IO) data from TSV. Batch 4: DB writes for standalone legacy IO liquidation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-path",
            type=str,
            default=None,
            help=f"Ruta al archivo CSV (default: {DEFAULT_DATA_PATH})",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Procesar solo las primeras N filas del archivo (después del header)",
        )
        parser.add_argument(
            "--fecha-desde",
            type=str,
            default=None,
            help="Procesar solo filas con FECHA mayor o igual a esta fecha (dd/mm/yyyy o yyyy-mm-dd)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar filas sin escribir en la BD (reportes y consola únicamente)",
        )
        parser.add_argument(
            "--solo-reporte",
            action="store_true",
            help="Solo generar reportes CSV/XLSX sin importar ni tocar la BD",
        )
        parser.add_argument(
            "--rechazar-dif-alta",
            action="store_true",
            help="EnBatch 4+: rechazar filas donde diff recalculado > umbral",
        )
        parser.add_argument(
            "--umbral-dif",
            type=float,
            default=1.0,
            help="Umbral de diferencia S/. para --rechazar-dif-alta (default 1.0)",
        )
        parser.add_argument(
            "--rechazar-sin-tarifa",
            action="store_true",
            help="Rechazar filas sin tarifa (CATEGORIA=0 o lookup fallido) (Batch 4)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Eliminar liquidaciones legacy IO antes de importar (Batch 4)",
        )


    def _log(self, msg):
        """Write a message, handling Windows encoding quirks."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            safe = msg.encode("ascii", "replace").decode("ascii")
            self.stdout.write(safe)

    def _log_warning(self, msg):
        try:
            self.stdout.write(self.style.WARNING(msg))
        except UnicodeEncodeError:
            safe = msg.encode("ascii", "replace").decode("ascii")
            self.stdout.write(safe)

    def _log_success(self, msg):
        try:
            self.stdout.write(self.style.SUCCESS(msg))
        except UnicodeEncodeError:
            safe = msg.encode("ascii", "replace").decode("ascii")
            self.stdout.write(safe)

    def _log_error(self, msg):
        try:
            self.stdout.write(self.style.ERROR(msg))
        except UnicodeEncodeError:
            safe = msg.encode("ascii", "replace").decode("ascii")
            self.stdout.write(safe)

    def handle(self, *args, **options):
        # ── Resolve flags ────────────────────────────────────────────────────
        self.dry_run = bool(options.get("dry_run", False))
        self.solo_reporte = bool(options.get("solo_reporte", False))
        self.rechazar_dif_alta = bool(options.get("rechazar_dif_alta", False))
        self.umbral_dif = Decimal(str(options.get("umbral_dif", 1.0)))
        self.rechazar_sin_tarifa = bool(options.get("rechazar_sin_tarifa", False))
        self.reset = bool(options.get("reset", False))
        self.traceback = bool(options.get("traceback", False))
        fecha_desde_raw = options.get("fecha_desde")
        self.fecha_desde = None
        if fecha_desde_raw:
            try:
                self.fecha_desde = _parse_fecha(fecha_desde_raw)
            except ValueError as exc:
                raise CommandError(f"--fecha-desde inválida: {fecha_desde_raw!r}") from exc
            if self.fecha_desde is None:
                raise CommandError(f"--fecha-desde inválida: {fecha_desde_raw!r}")

        # Batch 4: write_mode when neither --dry-run nor --solo-reporte is given
        self.write_mode = not self.dry_run and not self.solo_reporte

        if self.write_mode:
            self._log("[BATCH 4] Modo ESCRITURA — se crearán registros en la BD.")
        else:
            self._log("[BATCH 4] Modo solo lectura (dry-run o solo-reporte).")

        data_path = Path(options["data_path"]) if options["data_path"] else DEFAULT_DATA_PATH
        if not data_path.exists():
            raise CommandError(f"Archivo de datos no encontrado: {data_path}")

        # ── XLSX guard ───────────────────────────────────────────────────────
        if _is_xlsx(data_path):
            raise CommandError(
                f"El archivo {data_path} parece ser un Excel .xlsx (signature PK detected). "
                "Este comando solo soporta archivos CSV con delimitador ';'. "
                "Si el archivo correcto es .xlsx, conviértalo a CSV primero."
            )

        self._log("\n[import_legacy_inspeccion_obra] Starting...")
        self._log(f"  Source: {data_path}")
        if self.fecha_desde is not None:
            self._log_warning(f"  --fecha-desde: procesando FECHA >= {self.fecha_desde}")

        # ── Read TSV ─────────────────────────────────────────────────────────
        self._log("  Leyendo archivo CSV...")
        headers, rows = _read_tsv(data_path)
        self._log(f"  Headers columns detected: {len(headers)}")
        self._log(f"  Data rows (approx): {len(rows)}")

        # Apply limit
        limit = options.get("limit")
        if limit is not None:
            if limit < 1:
                raise CommandError("--limit debe ser >= 1")
            rows = rows[:limit]
            self._log_warning(f"  --limit: procesando solo las primeras {limit} filas")
        total_rows = len(rows)

        # ── Output paths ──────────────────────────────────────────────────────
        out_dir = data_path.parent
        # Each run writes to its own folder so migration reports are auditable.
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = Path(__file__).resolve().parents[5] / "result" / "IO" / run_id
        result_dir.mkdir(parents=True, exist_ok=True)
        rechazo_csv_path = result_dir / "reporte_ingesta_legacy.csv"
        detalle_csv_path = result_dir / "reporte_legacy_io_detallado.csv"
        detalle_xlsx_path = result_dir / "reporte_legacy_io_detallado.xlsx"

        # ── Parse all rows ───────────────────────────────────────────────────
        self._log("\n  Procesando filas...")
        parsed_rows: list[ParsedRow] = []
        parse_errors = 0
        skipped = 0
        skipped_by_date = 0
        error_details: list[str] = []

        for idx, raw_row in enumerate(rows, start=2):  # start=2: row 1 is header
            try:
                # ── Always parse the row first ───────────────────────────────────
                parsed, rechazo_motivo = _parse_row(raw_row, idx)

                if self.fecha_desde is not None:
                    if parsed.fecha is None or parsed.fecha < self.fecha_desde:
                        skipped_by_date += 1
                        continue

                # ── Reusar liquidación existente y procesar inspector/RH ─────
                id_val = parsed.id_val
                existing_inspeccion = None
                if id_val is not None and not self.reset:
                    existing_inspeccion = (
                        LiquidacionInspeccionObra.objects.select_related("liquidacion")
                        .filter(numero=id_val)
                        .first()
                    )

                if existing_inspeccion is not None:
                    lg = existing_inspeccion.liquidacion
                    # ── Completeness check: skip only if ALL artifacts are complete ─
                    # RH detail must have inspecciones_liquidadas populated
                    rh_complete = DetalleHonorarioInspector.objects.filter(
                        liquidacion_por_categoria_visitas__liquidacion_general=lg,
                        inspecciones_liquidadas__isnull=False,
                        inspecciones_liquidadas__gt=0,
                    ).exists()
                    # Comprobante must exist (active)
                    has_comprobante = LiquidacionComprobante.objects.filter(
                        liquidacion_general=lg,
                        activo=True,
                    ).exists()
                    # Contacto principal must exist
                    has_contacto = LiquidacionContacto.objects.filter(
                        liquidacion=lg,
                        principal=True,
                    ).exists()

                    if rh_complete and has_comprobante and has_contacto:
                        skipped += 1
                        continue
                    # Row is incomplete — repair it
                    parsed.existing_liquidacion_general = lg
                    self._log_warning(
                        f"  INCOMPLETA row {idx}: numero {id_val} ya existe; "
                        f"reparando (rh={rh_complete} comp={has_comprobante} contacto={has_contacto})"
                    )

                parsed_rows.append(parsed)
            except Exception as exc:  # noqa: BLE001
                parse_errors += 1
                msg = f"Fila {idx}: {exc}"
                error_details.append(msg)
                self._log_error(f"  ERROR fila {idx}: {exc}")
                if self.traceback:
                    import traceback
                    self._log_error(traceback.format_exc())

        self._log(f"  Parseadas: {len(parsed_rows)} | Errores de parseo: {parse_errors}")

        # ── Read source header for clean report (needed before opening joined/clean files) ──
        source_header: list[str] = []
        try:
            with data_path.open("r", encoding="utf-8-sig") as hf:
                reader = csv.reader(hf, delimiter=";")
                for line_idx, line in enumerate(reader):
                    if line_idx == 0:
                        source_header = line
                        break
        except Exception as exc_hdr:
            self._log_warning(f"  No se pudo leer header del fuente: {exc_hdr}")

        # ── Batch 4: Reset existing legacy IO (optional) ─────────────────────────
        if self.reset:
            if not self.write_mode:
                self._log_warning("  --reset no tiene efecto en modo dry-run.")
            else:
                self._log("  --reset: eliminando liquidaciones legacy IO existentes...")
                _reset_legacy_io(self)

        # ── Open all report files BEFORE the loop (streaming + Ctrl+C protection) ─
        joined_csv_path = result_dir / "reporte_rechazadas.csv"
        joined_xlsx_path = result_dir / "reporte_rechazadas.xlsx"
        clean_csv_path = result_dir / "filas_rechazadas_para_corregir.csv"
        clean_xlsx_path = result_dir / "filas_rechazadas_para_corregir.xlsx"

        joined_csv_file = joined_csv_path.open("w", newline="", encoding="utf-8")
        jw = csv.writer(joined_csv_file)
        joined_headers = (
            ["FILA", "MOTIVO", "SUBIDO"]
            + (source_header if source_header else [f"col_{i}" for i in range(63)])
        )
        jw.writerow(joined_headers)
        joined_csv_file.flush()

        clean_csv_file = clean_csv_path.open("w", newline="", encoding="utf-8-sig")
        cw = csv.writer(clean_csv_file, delimiter=";")
        if source_header:
            cw.writerow(source_header)
            clean_csv_file.flush()

        wb_joined = openpyxl.Workbook()
        ws_joined = wb_joined.active
        ws_joined.title = "Rechazadas IO"
        ws_joined.append(joined_headers)

        wb_clean = openpyxl.Workbook()
        ws_clean = wb_clean.active
        ws_clean.title = "Para corregir IO"
        if source_header:
            ws_clean.append(source_header)

        self._log(f"\n  Abriendo rechazo CSV: {rechazo_csv_path}")
        rechazo_file = rechazo_csv_path.open("w", newline="", encoding="utf-8")
        rechazo_writer = csv.writer(rechazo_file)
        rechazo_writer.writerow(_build_rechazo_headers())
        rejected_rows: list[dict] = []

        # ── Main processing loop with Ctrl+C protection ────────────────────────────
        try:
            if self.write_mode:
                self._log("\n  Batch 4: Creando liquidaciones en la BD...")
                db_counters = _create_legacy_liquidations(
                    self,
                    parsed_rows,
                    self.umbral_dif,
                    self.rechazar_dif_alta,
                    self.rechazar_sin_tarifa,
                    rechazo_writer,
                    rejected_rows,
                    jw,
                    joined_csv_file,
                    ws_joined,
                )
                self._log(f"  Creadas: {db_counters['created']} | Errores: {db_counters['errors']}")
                if db_counters["rechazadas_diff_alta"]:
                    self._log(f"  Rechazadas por diff alta: {db_counters['rechazadas_diff_alta']}")
                if db_counters["rechazadas_sin_tarifa"]:
                    self._log(f"  Rechazadas por sin tarifa: {db_counters['rechazadas_sin_tarifa']}")
                if db_counters.get("rechazadas_cip_no_resuelto"):
                    self._log(f"  Rechazadas por CIP no resuelto: {db_counters['rechazadas_cip_no_resuelto']}")

            # ── Write structurally rejected rows LIVE to joined/clean reports ──────────
            for pr in parsed_rows:
                if pr.rechazo_motivo:  # structural rejection
                    # Write to rechazo INGESTA CSV
                    rechazo_writer.writerow(pr.to_report_row())
                    # Stream to joined CSV + XLSX
                    jw.writerow([pr.row_index, pr.rechazo_motivo, "N/A"] + pr.raw)
                    joined_csv_file.flush()
                    ws_joined.append([pr.row_index, pr.rechazo_motivo, "N/A"] + pr.raw)
                    # Stream to clean CSV + XLSX
                    cw.writerow(pr.raw)
                    clean_csv_file.flush()
                    ws_clean.append(pr.raw)
                    # Accumulate for clean report
                    rejected_rows.append({
                        "fila": pr.row_index,
                        "row": pr.raw,
                        "motivo": pr.rechazo_motivo,
                        "subido": "N/A",
                    })

            # ── Write detailed report CSV ─────────────────────────────────────────
            self._log(f"  Escribiendo reporte detallado CSV: {detalle_csv_path}")
            detalle_headers = _build_detailed_headers()
            detalle_file = detalle_csv_path.open("w", newline="", encoding="utf-8")
            detalle_writer = csv.writer(detalle_file)
            detalle_writer.writerow(detalle_headers)
            for pr in parsed_rows:
                detalle_writer.writerow(pr.to_detailed_report_row(detalle_headers))
            detalle_file.close()

            # ── Write detailed report XLSX ────────────────────────────────────────
            self._log(f"  Escribiendo reporte detallado XLSX: {detalle_xlsx_path}")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "IO Detalle"
            ws.append(detalle_headers)
            for pr in parsed_rows:
                ws.append(pr.to_detailed_report_row(detalle_headers))
            try:
                wb.save(str(detalle_xlsx_path))
            except PermissionError:
                self._log_warning(
                    f"  No se pudo escribir el XLSX porque el archivo está abierto o bloqueado: {detalle_xlsx_path}. "
                    "El reporte CSV detallado sí fue generado."
                )

            # ── Compute counters ───────────────────────────────────────────────────
            processed = len(parsed_rows)
            structurally_rejected = sum(1 for pr in parsed_rows if pr.rechazo_motivo)
            category_zero = sum(1 for pr in parsed_rows if pr.categoria_status == "null_tariff")
            categoria_anomaly = sum(1 for pr in parsed_rows if pr.categoria_status == "anomaly")
            inspector_candidates = sum(1 for pr in parsed_rows if pr.delegado and pr.cip is not None)
            factura_candidates = sum(
                1 for pr in parsed_rows
                if pr.nro_factura and pr.nro_factura.strip() not in ("NULL", "")
            )
            # Contacto candidates: TPERSONA or TFONO present in source
            contacto_candidates = sum(
                1 for pr in parsed_rows
                if (
                    (len(pr.raw) > _COL_TPERSONA and str(pr.raw[_COL_TPERSONA] or "").strip().upper() not in ("", "NULL"))
                    or (len(pr.raw) > _COL_TFONO and str(pr.raw[_COL_TFONO] or "").strip().upper() not in ("", "NULL"))
                )
            )
            encoding_issues = sum(
                1 for pr in parsed_rows
                if any("Encoding issue" in a for a in pr.anomalies)
            )
            validation_ok_exact = sum(1 for pr in parsed_rows if pr.validation_status == "OK")
            validation_ok_uit_implicita = sum(1 for pr in parsed_rows if pr.validation_status == "OK_UIT_IMPLICITA")
            validation_diff_unexplained = sum(
                1 for pr in parsed_rows
                if pr.validation_status in ("DIF_SUBTOTAL", "DIF_TOTAL")
            )
            validation_sin_datos = sum(1 for pr in parsed_rows if pr.validation_status == "SIN_DATOS")

            # ── Console summary ──────────────────────────────────────────────────
            self._log_success("\n=== REPORTE DE IMPORTACION LEGACY IO (BATCH 4) ===")
            self._log(f"  Saltadas (ya existentes):       {skipped}")
            if self.fecha_desde is not None:
                self._log(f"  Saltadas por fecha:             {skipped_by_date}")
            self._log(f"  Procesadas (total filas leídas): {processed}")
            if self.write_mode:
                self._log(f"  Filas procesadas en BD:          {db_counters.get('created', 0)}")
                self._log(f"  Liquidaciones nuevas creadas:    {db_counters.get('liquidaciones_nuevas', 0)}")
                self._log(f"  Liquidaciones existentes usadas: {db_counters.get('liquidaciones_existentes', 0)}")
                self._log(f"  Rechazadas (diff alta):          {db_counters.get('rechazadas_diff_alta', 0)}")
                self._log(f"  Rechazadas (sin tarifa):         {db_counters.get('rechazadas_sin_tarifa', 0)}")
                self._log(f"  Errores al crear:                {db_counters.get('errors', 0)}")
                self._log(f"  Inspectores asociados:           {db_counters.get('inspectores_asociados', 0)}")
                self._log(f"  Inspectores saltados:            {db_counters.get('inspectores_saltados', 0)}")
                self._log(f"  Fallback CIP creados:            {db_counters.get('fallback_creados', 0)}")
                self._log(f"  RH detalles creados:             {db_counters.get('rh_detalles_creados', 0)}")
                self._log(f"  RH detalles actualizados:       {db_counters.get('rh_detalles_actualizados', 0)}")
                self._log(f"  Comprobantes creados:           {db_counters.get('comprobantes_creados', 0)}")
                self._log(f"  Comprobantes actualizados:     {db_counters.get('comprobantes_actualizados', 0)}")
                self._log(f"  Comprobantes omitidos:         {db_counters.get('comprobantes_omitidos', 0)}")
                self._log(f"  Contactos creados:              {db_counters.get('contactos_creados', 0)}")
                self._log(f"  Contactos actualizados:        {db_counters.get('contactos_actualizados', 0)}")
                self._log(f"  Contactos omitidos:            {db_counters.get('contactos_omitidos', 0)}")
            else:
                self._log(f"  Importadas (creadas en BD):      0  ← modo dry-run")
            self._log(f"  Rechazadas (estructural):       {structurally_rejected}")
            self._log(f"  CATEGORIA=0 (null/manual):       {category_zero}")
            self._log(f"  CATEGORIA inválida (anomaly):    {categoria_anomaly}")
            self._log(f"  Errores de parseo:              {parse_errors}")
            self._log(f"  Inspector candidates (DELEGADO+CIP): {inspector_candidates}")
            self._log(f"  Factura candidates (NROFACTURA): {factura_candidates}")
            self._log(f"  Contacto candidates (TPERSONA/TFONO): {contacto_candidates}")
            self._log(f"  Encoding issues:                 {encoding_issues}")
            self._log(f"")
            self._log(f"  Validación unitaria (batch 3c):")
            self._log(f"    OK exact match:                {validation_ok_exact}")
            self._log(f"    Diff explicada por UIT implícita: {validation_ok_uit_implicita}")
            self._log(f"    Diff inexplicable:              {validation_diff_unexplained}")
            self._log(f"    Sin datos para validar:        {validation_sin_datos}")
            self._log(f"")
            self._log(f"  Flags activos:")
            self._log(f"    --rechazar-dif-alta:   {self.rechazar_dif_alta}")
            self._log(f"    --umbral-dif:          {self.umbral_dif}")
            self._log(f"    --rechazar-sin-tarifa: {self.rechazar_sin_tarifa}")
            self._log(f"    --reset:               {self.reset}")
            self._log(f"")
            self._log(f"  Archivos generados en {result_dir}:")
            self._log(f"    reporte_ingesta_legacy.csv")
            self._log(f"    reporte_rechazadas.csv + .xlsx  ← escrito en vivo (streaming)")
            self._log(f"    filas_rechazadas_para_corregir.csv + .xlsx  ← escrito en vivo (streaming)")
            self._log(f"    reporte_legacy_io_detallado.csv")
            self._log(f"    reporte_legacy_io_detallado.xlsx")

            if error_details:
                self._log_warning("\n  Detalle de errores de parseo (primeros 20):")
                for detail in error_details[:20]:
                    self._log(f"    {detail}")
                if len(error_details) > 20:
                    self._log(f"    ... y {len(error_details) - 20} errores más")

            if self.write_mode and db_counters.get("error_details"):
                self._log_warning("\n  Detalle de errores de creacion en BD (primeros 20):")
                for detail in db_counters["error_details"][:20]:
                    self._log(f"    {detail}")
                if len(db_counters["error_details"]) > 20:
                    self._log(f"    ... y {len(db_counters['error_details']) - 20} errores más")

            if self.write_mode:
                self._log_success("\n  Batch 4 completado — liquidaciones creadas en la BD.")
            else:
                self._log_success("\n  Batch 4 completado en modo solo lectura (dry-run).")

        except KeyboardInterrupt:
            self._log(self.style.WARNING(
                "\n[!] Proceso cancelado forzadamente por el usuario. "
                "Guardando archivos..."
            ))
        finally:
            # ── Close CSV files and save Excel workbooks (Ctrl+C safe) ─────────
            try:
                rechazo_file.close()
            except Exception:
                pass
            try:
                joined_csv_file.close()
            except Exception:
                pass
            try:
                clean_csv_file.close()
            except Exception:
                pass
            try:
                wb_joined.save(str(joined_xlsx_path))
                self._log(f"  Saved joined XLSX: {joined_xlsx_path}")
            except Exception as exc:
                self._log_warning(f"  Error saving joined XLSX: {exc}")
            try:
                wb_clean.save(str(clean_xlsx_path))
                self._log(f"  Saved clean XLSX: {clean_xlsx_path}")
            except Exception as exc:
                self._log_warning(f"  Error saving clean XLSX: {exc}")
            self._log(f"  Archivos de reporte guardados en {result_dir}.")
